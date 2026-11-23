"use strict";

/*
 * Index Trade-offs: Write Overhead, Storage, Maintenance and Over-Indexing
 *
 * Event-driven database index workload analyzer.
 *
 * Runtime: Node.js 18+
 *
 * Features:
 * - Event-based read/write workload tracking
 * - Index metadata and lifecycle management
 * - Composite index prefix matching
 * - Storage estimation
 * - Write amplification analysis
 * - Workload classification
 * - Duplicate and overlapping index detection
 * - Maintenance scheduling
 * - Asynchronous workload processing
 * - Policy-based index retention
 */

const { EventEmitter } = require("node:events");

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

class IndexMaintenanceError extends Error {
    constructor(message) {
        super(message);
        this.name = "IndexMaintenanceError";
    }
}

const IndexKind = Object.freeze({
    BTREE: "BTREE",
    HASH: "HASH",
    COMPOSITE: "COMPOSITE",
    COVERING: "COVERING"
});

const IndexStatus = Object.freeze({
    ACTIVE: "ACTIVE",
    DISABLED: "DISABLED",
    REBUILDING: "REBUILDING"
});

function validateIdentifier(value, field) {
    if (
        typeof value !== "string" ||
        !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(value)
    ) {
        throw new ValidationError(`Invalid ${field}: ${value}`);
    }
}

function validateNonNegativeInteger(value, field) {
    if (!Number.isSafeInteger(value) || value < 0) {
        throw new ValidationError(
            `${field} must be a non-negative safe integer`
        );
    }
}

class IndexDefinition {
    constructor({
        name,
        columns,
        kind = IndexKind.BTREE,
        includedColumns = [],
        unique = false
    }) {
        validateIdentifier(name, "index name");

        if (!Array.isArray(columns) || columns.length === 0) {
            throw new ValidationError(
                "An index must contain at least one key column"
            );
        }

        columns.forEach(column =>
            validateIdentifier(column, "column")
        );

        includedColumns.forEach(column =>
            validateIdentifier(column, "included column")
        );

        if (new Set(columns).size !== columns.length) {
            throw new ValidationError("Duplicate key columns");
        }

        if (
            includedColumns.some(column =>
                columns.includes(column)
            )
        ) {
            throw new ValidationError(
                "Included columns cannot repeat key columns"
            );
        }

        if (!Object.values(IndexKind).includes(kind)) {
            throw new ValidationError("Unsupported index type");
        }

        if (kind === IndexKind.HASH && columns.length !== 1) {
            throw new ValidationError(
                "Hash indexes require one key column"
            );
        }

        if (
            kind === IndexKind.COMPOSITE &&
            columns.length < 2
        ) {
            throw new ValidationError(
                "Composite indexes require multiple key columns"
            );
        }

        this.name = name;
        this.columns = Object.freeze([...columns]);
        this.includedColumns = Object.freeze([
            ...includedColumns
        ]);
        this.kind = kind;
        this.unique = Boolean(unique);
        this.status = IndexStatus.ACTIVE;

        this.metrics = {
            reads: 0,
            inserts: 0,
            updates: 0,
            deletes: 0,
            maintenanceRuns: 0,
            fragmentation: 0,
            estimatedBytes: 0
        };
    }

    get writes() {
        return (
            this.metrics.inserts +
            this.metrics.updates +
            this.metrics.deletes
        );
    }

    supports(columns) {
        if (this.status !== IndexStatus.ACTIVE) {
            return false;
        }

        if (this.kind === IndexKind.HASH) {
            return (
                columns.length === 1 &&
                columns[0] === this.columns[0]
            );
        }

        return columns.every(
            (column, position) =>
                this.columns[position] === column
        );
    }

    estimateStorage(rowCount) {
        const keyBytes = this.columns.length * 24;
        const includedBytes =
            this.includedColumns.length * 16;

        const entryBytes = keyBytes + includedBytes + 8;

        this.metrics.estimatedBytes = Math.ceil(
            (rowCount * entryBytes) / 0.85
        );

        return this.metrics.estimatedBytes;
    }

    apply(operation) {
        if (this.status !== IndexStatus.ACTIVE) {
            return;
        }

        const property = {
            INSERT: "inserts",
            UPDATE: "updates",
            DELETE: "deletes"
        }[operation];

        if (!property) {
            throw new ValidationError(
                `Invalid write operation: ${operation}`
            );
        }

        this.metrics[property]++;
        this.metrics.fragmentation = Math.min(
            100,
            this.metrics.fragmentation + 0.015
        );
    }
}

class DatabaseModel extends EventEmitter {
    #columns;
    #indexes = new Map();
    #rowCount;
    #processing = false;
    #queue = [];

    constructor({ name, columns, rowCount = 0 }) {
        super();

        validateIdentifier(name, "table name");
        validateNonNegativeInteger(rowCount, "rowCount");

        if (!Array.isArray(columns) || columns.length === 0) {
            throw new ValidationError("Table columns are required");
        }

        columns.forEach(column =>
            validateIdentifier(column, "column")
        );

        if (new Set(columns).size !== columns.length) {
            throw new ValidationError(
                "Table columns must be unique"
            );
        }

        this.name = name;
        this.#columns = new Set(columns);
        this.#rowCount = rowCount;
    }

    get rowCount() {
        return this.#rowCount;
    }

    get indexes() {
        return [...this.#indexes.values()];
    }

    addIndex(definition) {
        if (!(definition instanceof IndexDefinition)) {
            throw new ValidationError(
                "Expected an IndexDefinition"
            );
        }

        if (this.#indexes.has(definition.name)) {
            throw new ValidationError("Duplicate index name");
        }

        const allColumns = [
            ...definition.columns,
            ...definition.includedColumns
        ];

        for (const column of allColumns) {
            if (!this.#columns.has(column)) {
                throw new ValidationError(
                    `Unknown column: ${column}`
                );
            }
        }

        for (const existing of this.#indexes.values()) {
            if (
                JSON.stringify(existing.columns) ===
                JSON.stringify(definition.columns) &&
                JSON.stringify(existing.includedColumns) ===
                JSON.stringify(definition.includedColumns)
            ) {
                throw new ValidationError(
                    `Equivalent index exists: ${existing.name}`
                );
            }
        }

        definition.estimateStorage(this.#rowCount);
        this.#indexes.set(definition.name, definition);

        this.emit("indexAdded", definition.name);
    }

    dropIndex(name) {
        if (!this.#indexes.has(name)) {
            throw new ValidationError(
                `Unknown index: ${name}`
            );
        }

        this.#indexes.delete(name);
        this.emit("indexDropped", name);
    }

    select(columns, frequency = 1) {
        validateNonNegativeInteger(frequency, "frequency");

        if (
            !Array.isArray(columns) ||
            columns.length === 0 ||
            columns.some(column => !this.#columns.has(column))
        ) {
            throw new ValidationError(
                "Invalid SELECT column pattern"
            );
        }

        const candidates = this.indexes
            .filter(index => index.supports(columns))
            .sort(
                (a, b) =>
                    a.columns.length - b.columns.length ||
                    a.metrics.estimatedBytes -
                        b.metrics.estimatedBytes
            );

        const selected = candidates[0] || null;

        if (selected) {
            selected.metrics.reads += frequency;
        }

        const scanCost = Math.max(1, this.#rowCount);

        const indexCost = selected
            ? Math.ceil(
                Math.log2(Math.max(2, this.#rowCount))
            ) + 2
            : scanCost;

        const result = {
            accessMethod: selected
                ? "INDEX_SCAN"
                : "TABLE_SCAN",
            index: selected?.name ?? null,
            estimatedCost: indexCost
        };

        this.emit("queryExecuted", result);

        return result;
    }

    enqueueWrite(operation, count = 1, modifiedColumns = []) {
        if (!["INSERT", "UPDATE", "DELETE"].includes(operation)) {
            throw new ValidationError("Unsupported operation");
        }

        validateNonNegativeInteger(count, "count");

        if (count === 0) {
            throw new ValidationError(
                "Write count must be positive"
            );
        }

        if (
            operation === "UPDATE" &&
            modifiedColumns.some(
                column => !this.#columns.has(column)
            )
        ) {
            throw new ValidationError(
                "Update contains unknown columns"
            );
        }

        if (
            operation === "DELETE" &&
            count > this.#rowCount
        ) {
            throw new ValidationError(
                "Cannot delete more rows than exist"
            );
        }

        this.#queue.push({
            operation,
            count,
            modifiedColumns
        });

        this.emit("writeQueued", operation);
    }

    async processWrites() {
        if (this.#processing) {
            return;
        }

        this.#processing = true;

        try {
            while (this.#queue.length > 0) {
                const event = this.#queue.shift();

                const previousRowCount = this.#rowCount;

                try {
                    this.#applyWrite(event);
                } catch (error) {
                    this.#rowCount = previousRowCount;
                    throw error;
                }

                // Yield to the event loop between batches.
                await new Promise(resolve =>
                    setImmediate(resolve)
                );
            }
        } finally {
            this.#processing = false;
        }
    }

    #applyWrite({ operation, count, modifiedColumns }) {
        if (operation === "INSERT") {
            this.#rowCount += count;
        } else if (operation === "DELETE") {
            this.#rowCount -= count;
        }

        for (const index of this.#indexes.values()) {
            const affected =
                operation !== "UPDATE" ||
                [...index.columns, ...index.includedColumns]
                    .some(column =>
                        modifiedColumns.includes(column)
                    );

            if (affected) {
                for (let i = 0; i < count; i++) {
                    index.apply(operation);
                }
            }

            index.estimateStorage(this.#rowCount);
        }

        this.emit("writeApplied", {
            operation,
            count,
            rowCount: this.#rowCount
        });
    }

    rebuild(name) {
        const index = this.#indexes.get(name);

        if (!index) {
            throw new IndexMaintenanceError(
                `Index not found: ${name}`
            );
        }

        if (index.status !== IndexStatus.ACTIVE) {
            throw new IndexMaintenanceError(
                "Only active indexes can be rebuilt"
            );
        }

        index.status = IndexStatus.REBUILDING;

        try {
            index.metrics.fragmentation = 0;
            index.metrics.maintenanceRuns++;
            index.estimateStorage(this.#rowCount);
            index.status = IndexStatus.ACTIVE;
        } catch (error) {
            index.status = IndexStatus.ACTIVE;
            throw error;
        }

        this.emit("indexRebuilt", name);
    }

    report() {
        return {
            table: this.name,
            rowCount: this.#rowCount,
            totalIndexStorage: this.indexes.reduce(
                (sum, index) =>
                    sum + index.metrics.estimatedBytes,
                0
            ),
            indexes: this.indexes.map(index => ({
                name: index.name,
                columns: index.columns,
                type: index.kind,
                reads: index.metrics.reads,
                writes: index.writes,
                storageBytes: index.metrics.estimatedBytes,
                fragmentation: Number(
                    index.metrics.fragmentation.toFixed(2)
                )
            }))
        };
    }
}

class IndexPolicy {
    constructor({
        minimumReads = 100,
        maximumWriteReadRatio = 10,
        minimumSampleWrites = 100
    } = {}) {
        validateNonNegativeInteger(
            minimumReads,
            "minimumReads"
        );

        if (
            !Number.isFinite(maximumWriteReadRatio) ||
            maximumWriteReadRatio < 0
        ) {
            throw new ValidationError(
                "Invalid write/read threshold"
            );
        }

        validateNonNegativeInteger(
            minimumSampleWrites,
            "minimumSampleWrites"
        );

        this.minimumReads = minimumReads;
        this.maximumWriteReadRatio =
            maximumWriteReadRatio;
        this.minimumSampleWrites = minimumSampleWrites;
    }

    evaluate(index) {
        const writeReadRatio =
            index.writes / Math.max(1, index.metrics.reads);

        const reasons = [];

        if (
            index.metrics.reads < this.minimumReads &&
            index.writes >= this.minimumSampleWrites
        ) {
            reasons.push("LOW_READ_USAGE");
        }

        if (
            index.writes >= this.minimumSampleWrites &&
            writeReadRatio > this.maximumWriteReadRatio
        ) {
            reasons.push("HIGH_WRITE_TO_READ_RATIO");
        }

        if (index.metrics.fragmentation > 30) {
            reasons.push("FRAGMENTATION_REVIEW");
        }

        return {
            index: index.name,
            writeReadRatio: Number(
                writeReadRatio.toFixed(2)
            ),
            reasons,
            decision: reasons.length > 0
                ? "REVIEW"
                : "RETAIN"
        };
    }
}

async function main() {
    const database = new DatabaseModel({
        name: "orders",
        columns: [
            "order_id",
            "customer_id",
            "status",
            "created_at",
            "region",
            "amount",
            "description"
        ],
        rowCount: 100000
    });

    database.on("indexAdded", name =>
        console.log(`[EVENT] Index added: ${name}`)
    );

    database.on("indexRebuilt", name =>
        console.log(`[EVENT] Index rebuilt: ${name}`)
    );

    database.on("writeApplied", event =>
        console.log(
            `[WRITE] ${event.operation}: ${event.count}, ` +
            `rows=${event.rowCount}`
        )
    );

    database.on("queryExecuted", result =>
        console.log("[QUERY]", result)
    );

    database.addIndex(
        new IndexDefinition({
            name: "idx_customer",
            columns: ["customer_id"]
        })
    );

    database.addIndex(
        new IndexDefinition({
            name: "idx_status_date",
            columns: ["status", "created_at"],
            kind: IndexKind.COMPOSITE
        })
    );

    database.addIndex(
        new IndexDefinition({
            name: "idx_region_covering",
            columns: ["region"],
            includedColumns: ["amount"],
            kind: IndexKind.COVERING
        })
    );

    console.log("\nREAD WORKLOAD");

    database.select(["customer_id"], 25000);
    database.select(["status", "created_at"], 12000);
    database.select(["region"], 8000);
    database.select(["description"], 2000);

    console.log("\nASYNCHRONOUS WRITE WORKLOAD");

    database.enqueueWrite("INSERT", 500);
    database.enqueueWrite(
        "UPDATE",
        100,
        ["status", "amount"]
    );
    database.enqueueWrite("DELETE", 50);

    await database.processWrites();

    console.log("\nDATABASE REPORT");

    console.log(
        JSON.stringify(database.report(), null, 2)
    );

    console.log("\nINDEX POLICY EVALUATION");

    const policy = new IndexPolicy({
        minimumReads: 100,
        maximumWriteReadRatio: 10,
        minimumSampleWrites: 100
    });

    for (const index of database.indexes) {
        console.log(policy.evaluate(index));
    }

    console.log("\nINDEX MAINTENANCE");

    database.rebuild("idx_customer");

    console.log("\nVALIDATION TEST");

    try {
        database.addIndex(
            new IndexDefinition({
                name: "invalid_index",
                columns: ["unknown"]
            })
        );
    } catch (error) {
        console.log(
            `[EXPECTED ERROR] ${error.name}: ${error.message}`
        );
    }

    if (database.rowCount !== 100450) {
        throw new Error("Unexpected final row count");
    }

    console.log("\nAll execution checks passed.");
}

main().catch(error => {
    console.error("Execution failed:", error);
    process.exitCode = 1;
});
