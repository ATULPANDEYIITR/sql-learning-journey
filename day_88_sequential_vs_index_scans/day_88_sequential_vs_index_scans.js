"use strict";

/**
 * Sequential Scan, Index Scan and Bitmap Scan
 *
 * Node.js implementation using:
 * - Map-based secondary indexes
 * - Set-based bitmap operations
 * - Asynchronous query execution
 * - Event-driven execution monitoring
 * - Cost-based scan selection
 *
 * Run:
 * node scan_engine.js
 */

const { EventEmitter } = require("node:events");
const { performance } = require("node:perf_hooks");

const PAGE_SIZE = 100;

const ScanType = Object.freeze({
    SEQUENTIAL: "Seq Scan",
    INDEX: "Index Scan",
    BITMAP: "Bitmap Heap Scan"
});

class QueryError extends Error {
    constructor(message) {
        super(message);
        this.name = "QueryError";
    }
}

class Predicate {
    constructor(column, operator, value) {
        if (typeof column !== "string" || !column.trim()) {
            throw new QueryError("Invalid predicate column");
        }

        if (!["=", "IN"].includes(operator)) {
            throw new QueryError("Unsupported predicate operator");
        }

        if (operator === "IN" && !Array.isArray(value)) {
            throw new QueryError("IN requires an array");
        }

        this.column = column;
        this.operator = operator;
        this.value = value;
    }

    matches(row) {
        if (this.operator === "=") {
            return row[this.column] === this.value;
        }

        return this.value.includes(row[this.column]);
    }
}

class SecondaryIndex {
    constructor(column) {
        this.column = column;
        this.entries = new Map();
    }

    add(value, rowId) {
        if (!this.entries.has(value)) {
            this.entries.set(value, new Set());
        }

        this.entries.get(value).add(rowId);
    }

    remove(value, rowId) {
        const bucket = this.entries.get(value);

        if (!bucket) return;

        bucket.delete(rowId);

        if (bucket.size === 0) {
            this.entries.delete(value);
        }
    }

    lookup(predicate) {
        const values = predicate.operator === "="
            ? [predicate.value]
            : predicate.value;

        const result = new Set();

        for (const value of values) {
            const matches = this.entries.get(value);

            if (matches) {
                for (const id of matches) {
                    result.add(id);
                }
            }
        }

        return result;
    }
}

class Relation {
    constructor(name, rows) {
        this.name = name;
        this.rows = [];
        this.columns = new Set();
        this.indexes = new Map();

        if (!Array.isArray(rows)) {
            throw new TypeError("Rows must be an array");
        }

        for (const row of rows) {
            this.insert(row);
        }
    }

    insert(row) {
        if (!row || typeof row !== "object" || Array.isArray(row)) {
            throw new QueryError("Invalid row");
        }

        const columns = Object.keys(row);

        if (columns.length === 0) {
            throw new QueryError("Empty rows are not allowed");
        }

        if (this.columns.size === 0) {
            this.columns = new Set(columns);
        }

        if (
            columns.length !== this.columns.size ||
            columns.some(column => !this.columns.has(column))
        ) {
            throw new QueryError("Inconsistent row structure");
        }

        const id = this.rows.length;
        const stored = Object.freeze({ ...row });

        this.rows.push(stored);

        for (const index of this.indexes.values()) {
            index.add(stored[index.column], id);
        }

        return id;
    }

    createIndex(column) {
        if (!this.columns.has(column)) {
            throw new QueryError(`Unknown column: ${column}`);
        }

        if (this.indexes.has(column)) {
            throw new QueryError(`Index already exists: ${column}`);
        }

        const index = new SecondaryIndex(column);

        this.rows.forEach((row, id) => {
            index.add(row[column], id);
        });

        this.indexes.set(column, index);
    }

    delete(id) {
        if (!Number.isInteger(id) || !this.rows[id]) {
            throw new QueryError("Invalid row identifier");
        }

        const row = this.rows[id];

        for (const index of this.indexes.values()) {
            index.remove(row[index.column], id);
        }

        // Null slots preserve stable tuple identifiers.
        this.rows[id] = null;
    }

    get activeRows() {
        return this.rows.reduce(
            (count, row) => count + (row !== null ? 1 : 0),
            0
        );
    }

    get pageCount() {
        return Math.max(1, Math.ceil(this.activeRows / PAGE_SIZE));
    }
}

class CostModel {
    constructor(relation) {
        this.relation = relation;
        this.seqPageCost = 1;
        this.randomPageCost = 4;
        this.cpuTupleCost = 0.01;
        this.cpuIndexCost = 0.005;
    }

    selectivity(predicate) {
        let matches = 0;

        for (const row of this.relation.rows) {
            if (row && predicate.matches(row)) {
                matches++;
            }
        }

        return matches / Math.max(1, this.relation.activeRows);
    }

    sequentialCost() {
        return (
            this.relation.pageCount * this.seqPageCost +
            this.relation.activeRows * this.cpuTupleCost
        );
    }

    indexCost(selectivity) {
        const n = Math.max(2, this.relation.activeRows);

        return (
            Math.log2(n) +
            selectivity * n *
            (this.randomPageCost + this.cpuIndexCost)
        );
    }

    bitmapCost(selectivities, predicateCount) {
        const combined = selectivities.reduce(
            (a, b) => a * b,
            1
        );

        const n = this.relation.activeRows;
        const rows = n * combined;
        const blocks = Math.min(
            this.relation.pageCount,
            Math.ceil(rows / PAGE_SIZE)
        );

        return (
            predicateCount * Math.log2(Math.max(2, n)) +
            rows * this.cpuIndexCost +
            blocks * this.randomPageCost +
            rows * this.cpuTupleCost
        );
    }

    choose(predicates) {
        const sequential = this.sequentialCost();

        const indexed = predicates
            .filter(p => this.relation.indexes.has(p.column))
            .map(p => ({
                predicate: p,
                selectivity: this.selectivity(p)
            }));

        if (indexed.length === 0) {
            return {
                type: ScanType.SEQUENTIAL,
                cost: sequential
            };
        }

        const best = indexed.reduce((a, b) =>
            a.selectivity <= b.selectivity ? a : b
        );

        const indexCost = this.indexCost(best.selectivity);

        if (indexed.length >= 2) {
            const bitmapCost = this.bitmapCost(
                indexed.map(item => item.selectivity),
                indexed.length
            );

            if (bitmapCost < sequential && bitmapCost < indexCost) {
                return {
                    type: ScanType.BITMAP,
                    cost: bitmapCost
                };
            }
        }

        if (indexCost < sequential) {
            return {
                type: ScanType.INDEX,
                cost: indexCost
            };
        }

        return {
            type: ScanType.SEQUENTIAL,
            cost: sequential
        };
    }
}

class QueryEngine extends EventEmitter {
    constructor(relation) {
        super();

        this.relation = relation;
        this.costModel = new CostModel(relation);
        this.activeQueries = 0;
    }

    validate(predicates) {
        if (!Array.isArray(predicates)) {
            throw new QueryError("Predicates must be an array");
        }

        for (const predicate of predicates) {
            if (!(predicate instanceof Predicate)) {
                throw new QueryError("Invalid predicate object");
            }

            if (!this.relation.columns.has(predicate.column)) {
                throw new QueryError(
                    `Unknown column: ${predicate.column}`
                );
            }
        }
    }

    async execute(predicates, forcedScan = null) {
        this.validate(predicates);

        const plan = this.costModel.choose(predicates);
        const scanType = forcedScan || plan.type;

        if (!Object.values(ScanType).includes(scanType)) {
            throw new QueryError("Unknown scan strategy");
        }

        if (scanType === ScanType.INDEX &&
            !predicates.some(p => this.relation.indexes.has(p.column))) {
            throw new QueryError("Index Scan requires an index");
        }

        if (scanType === ScanType.BITMAP &&
            predicates.filter(p => this.relation.indexes.has(p.column)).length < 2) {
            throw new QueryError("Bitmap Scan requires two indexes");
        }

        const queryId = `Q-${Date.now()}-${++this.activeQueries}`;

        this.emit("query:start", {
            queryId,
            scanType,
            estimatedCost: plan.cost
        });

        const started = performance.now();

        // Yield control to the Node.js event loop.
        await new Promise(resolve => setImmediate(resolve));

        const metrics = {
            scanType,
            estimatedCost: plan.cost,
            rowsExamined: 0,
            rowsReturned: 0,
            indexEntriesExamined: 0,
            heapBlocksAccessed: 0,
            bitmapMemoryBytes: 0
        };

        let candidates = [];

        if (scanType === ScanType.SEQUENTIAL) {
            candidates = this.relation.rows
                .map((row, id) => row ? id : -1)
                .filter(id => id >= 0);

            metrics.rowsExamined = candidates.length;
            metrics.heapBlocksAccessed = this.relation.pageCount;
        }

        if (scanType === ScanType.INDEX) {
            const indexed = predicates
                .filter(p => this.relation.indexes.has(p.column))
                .sort((a, b) =>
                    this.costModel.selectivity(a) -
                    this.costModel.selectivity(b)
                );

            const index = this.relation.indexes.get(indexed[0].column);

            candidates = [...index.lookup(indexed[0])];

            metrics.indexEntriesExamined = candidates.length;
            metrics.rowsExamined = candidates.length;
        }

        if (scanType === ScanType.BITMAP) {
            const bitmaps = predicates
                .filter(p => this.relation.indexes.has(p.column))
                .map(predicate => {
                    const ids = this.relation.indexes
                        .get(predicate.column)
                        .lookup(predicate);

                    metrics.indexEntriesExamined += ids.size;
                    return ids;
                });

            // Intersect candidate tuple IDs using Set operations.
            bitmaps.sort((a, b) => a.size - b.size);

            let intersection = new Set(bitmaps[0]);

            for (let i = 1; i < bitmaps.length; i++) {
                intersection = new Set(
                    [...intersection].filter(id => bitmaps[i].has(id))
                );
            }

            candidates = [...intersection];

            metrics.rowsExamined = candidates.length;
            metrics.bitmapMemoryBytes =
                Math.ceil(this.relation.rows.length / 8);
        }

        const result = [];

        for (const id of candidates) {
            const row = this.relation.rows[id];

            if (row && predicates.every(p => p.matches(row))) {
                result.push(row);
            }
        }

        metrics.rowsReturned = result.length;

        if (scanType === ScanType.INDEX) {
            metrics.heapBlocksAccessed = new Set(
                candidates.map(id => Math.floor(id / PAGE_SIZE))
            ).size;
        }

        if (scanType === ScanType.BITMAP) {
            metrics.heapBlocksAccessed = new Set(
                candidates.map(id => Math.floor(id / PAGE_SIZE))
            ).size;
        }

        metrics.executionTimeMs = performance.now() - started;

        this.emit("query:complete", {
            queryId,
            ...metrics
        });

        return {
            rows: result,
            metrics
        };
    }
}

function generateEmployees(count) {
    let seed = 42;

    function random() {
        seed = (seed * 1664525 + 1013904223) % 4294967296;
        return seed / 4294967296;
    }

    const departments = [
        "Engineering",
        "Finance",
        "Operations",
        "Security"
    ];

    const locations = [
        "Lucknow",
        "Delhi",
        "Mumbai",
        "Bengaluru"
    ];

    return Array.from({ length: count }, (_, i) => ({
        employeeId: i + 1,
        department: departments[
            Math.floor(random() * departments.length)
        ],
        location: locations[
            Math.floor(random() * locations.length)
        ],
        salary: 30000 + Math.floor(random() * 150001),
        active: random() > 0.15
    }));
}

function printResult(title, result) {
    console.log(`\n${title}`);
    console.table(result.metrics);
    console.log("Returned rows:", result.rows.length);
}

async function main() {
    const employees = generateEmployees(10000);

    const relation = new Relation("employees", employees);

    relation.createIndex("employeeId");
    relation.createIndex("department");
    relation.createIndex("location");

    const engine = new QueryEngine(relation);

    engine.on("query:start", event => {
        console.log(
            `\nStarted ${event.queryId}: ${event.scanType}`
        );
    });

    engine.on("query:complete", event => {
        console.log(
            `Completed ${event.queryId}: ${event.rowsReturned} rows`
        );
    });

    const sequential = await engine.execute([
        new Predicate("salary", "=", 50000)
    ]);

    printResult("1. Sequential Scan", sequential);

    const indexed = await engine.execute([
        new Predicate("employeeId", "=", 500)
    ]);

    printResult("2. Index Scan", indexed);

    const bitmap = await engine.execute([
        new Predicate("department", "=", "Engineering"),
        new Predicate("location", "=", "Lucknow")
    ], ScanType.BITMAP);

    printResult("3. Bitmap Heap Scan", bitmap);

    // Compare scan strategies using identical query conditions.
    const test = [
        new Predicate("employeeId", "=", 500)
    ];

    const seq = await engine.execute(test, ScanType.SEQUENTIAL);
    const idx = await engine.execute(test, ScanType.INDEX);

    if (
        JSON.stringify(seq.rows) !== JSON.stringify(idx.rows)
    ) {
        throw new Error("Scan strategies returned different results");
    }

    // Validate index maintenance after insertion and deletion.
    const insertedId = relation.insert({
        employeeId: 10001,
        department: "Security",
        location: "Lucknow",
        salary: 90000,
        active: true
    });

    const inserted = await engine.execute([
        new Predicate("employeeId", "=", 10001)
    ]);

    if (inserted.rows.length !== 1) {
        throw new Error("Insert index maintenance failed");
    }

    relation.delete(insertedId);

    const deleted = await engine.execute([
        new Predicate("employeeId", "=", 10001)
    ]);

    if (deleted.rows.length !== 0) {
        throw new Error("Delete index maintenance failed");
    }

    console.log("\nAll execution and integrity tests passed.");
}

main().catch(error => {
    console.error("Execution failed:", error.message);
    process.exitCode = 1;
});
