"use strict";

/*
 * Temporary Tables: session scope and staging workflows.
 *
 * Node.js implementation using isolated session objects and
 * asynchronous batch processing.
 *
 * Run: node temporary_tables.js
 *
 * No external dependencies.
 */

const { EventEmitter } = require("node:events");
const crypto = require("node:crypto");

const Status = Object.freeze({
    PENDING: "PENDING",
    ACCEPTED: "ACCEPTED",
    REJECTED: "REJECTED"
});

const SessionState = Object.freeze({
    OPEN: "OPEN",
    CLOSED: "CLOSED"
});

class StagingError extends Error {
    constructor(message, cause) {
        super(message, { cause });
        this.name = "StagingError";
    }
}

class Repository {
    constructor() {
        this.products = new Map();
        this.audit = [];
    }

    find(id) {
        return this.products.get(id);
    }

    commitBatch(records) {
        // Check every key before changing permanent state.
        for (const record of records) {
            if (this.products.has(record.externalId)) {
                throw new StagingError(
                    `Permanent record already exists: ${record.externalId}`
                );
            }
        }

        const additions = records.map(record => ({
            ...record,
            totalValue: record.quantity * record.unitPrice,
            importedAt: new Date().toISOString()
        }));

        for (const record of additions) {
            this.products.set(record.externalId, record);
        }

        return additions.length;
    }

    recordAudit(results) {
        this.audit.push(...results.map(result => ({
            ...result,
            recordedAt: new Date().toISOString()
        })));
    }

    report() {
        const values = [...this.products.values()];

        return {
            recordCount: values.length,
            inventoryValue: values.reduce(
                (sum, item) => sum + item.totalValue,
                0
            ),
            auditCount: this.audit.length
        };
    }
}

class StagingSession extends EventEmitter {
    constructor(repository, options = {}) {
        super();

        this.id = crypto.randomUUID();
        this.repository = repository;
        this.state = SessionState.OPEN;
        this.maxBatchSize = options.maxBatchSize ?? 100000;

        // Maps provide efficient identifier-based lookup.
        this.staging = new Map();
        this.validation = new Map();
        this.rawRows = [];
    }

    ensureOpen() {
        if (this.state !== SessionState.OPEN) {
            throw new StagingError("Temporary session is closed");
        }
    }

    normalize(record) {
        if (!record || typeof record !== "object") {
            throw new StagingError("Record must be an object");
        }

        const externalId = String(record.externalId ?? "").trim();
        const product = String(record.product ?? "").trim();
        const quantity = Number(record.quantity);
        const unitPrice = Number(record.unitPrice);

        return {
            externalId,
            product,
            quantity,
            unitPrice
        };
    }

    async load(records) {
        this.ensureOpen();

        if (!Array.isArray(records) || records.length === 0) {
            throw new StagingError("A non-empty array is required");
        }

        if (records.length > this.maxBatchSize) {
            throw new StagingError("Batch size limit exceeded");
        }

        const batch = records.map(record => this.normalize(record));

        // Preserve original rows so duplicate identifiers can be detected.
        for (const record of batch) {
            this.rawRows.push(record);
        }

        this.emit("loaded", {
            sessionId: this.id,
            count: batch.length
        });

        return batch.length;
    }

    async validate() {
        this.ensureOpen();

        this.validation.clear();
        this.staging.clear();

        const seen = new Set();
        const results = [];

        for (const record of this.rawRows) {
            let reason = "Valid record";

            if (!record.externalId) {
                reason = "Missing external identifier";
            } else if (!record.product) {
                reason = "Missing product name";
            } else if (
                !Number.isSafeInteger(record.quantity) ||
                record.quantity <= 0
            ) {
                reason = "Quantity must be a positive integer";
            } else if (
                !Number.isFinite(record.unitPrice) ||
                record.unitPrice < 0
            ) {
                reason = "Unit price must be finite and non-negative";
            } else if (seen.has(record.externalId)) {
                reason = "Duplicate identifier in staging batch";
            } else if (this.repository.find(record.externalId)) {
                reason = "Identifier already exists";
            }

            if (record.externalId) {
                seen.add(record.externalId);
            }

            const status = reason === "Valid record"
                ? Status.ACCEPTED
                : Status.REJECTED;

            const result = {
                externalId: record.externalId,
                status,
                reason
            };

            results.push(result);

            // Keep each original row independent.
            this.staging.set(
                results.length - 1,
                Object.freeze({ ...record })
            );

            this.validation.set(results.length - 1, result);
        }

        this.emit("validated", {
            accepted: results.filter(
                result => result.status === Status.ACCEPTED
            ).length,
            rejected: results.filter(
                result => result.status === Status.REJECTED
            ).length
        });

        return results;
    }

    async promote() {
        this.ensureOpen();

        const accepted = [];

        for (const [index, result] of this.validation) {
            if (result.status === Status.ACCEPTED) {
                accepted.push(this.staging.get(index));
            }
        }

        try {
            // Repository checks all keys before modifying permanent state.
            const inserted = this.repository.commitBatch(accepted);

            this.repository.recordAudit(
                [...this.validation.values()]
            );

            this.emit("promoted", { inserted });

            return inserted;
        } catch (error) {
            this.emit("promotionFailed", {
                message: error.message
            });

            throw new StagingError(
                "Staging promotion was unsuccessful",
                error
            );
        }
    }

    report() {
        this.ensureOpen();

        const counts = {
            ACCEPTED: 0,
            REJECTED: 0,
            PENDING: 0
        };

        for (const result of this.validation.values()) {
            counts[result.status]++;
        }

        return {
            sessionId: this.id,
            stagingRows: this.rawRows.length,
            counts,
            permanent: this.repository.report()
        };
    }

    truncate() {
        this.ensureOpen();

        this.rawRows.length = 0;
        this.staging.clear();
        this.validation.clear();

        this.emit("truncated", { sessionId: this.id });
    }

    close() {
        if (this.state === SessionState.CLOSED) {
            return;
        }

        this.truncate();
        this.state = SessionState.CLOSED;
        this.emit("closed", { sessionId: this.id });
        this.removeAllListeners();
    }
}

async function runWorkflow() {
    const repository = new Repository();

    const session = new StagingSession(repository, {
        maxBatchSize: 10000
    });

    session.on("loaded", event => {
        console.log("Loaded:", event.count);
    });

    session.on("validated", event => {
        console.log("Validation:", event);
    });

    session.on("promoted", event => {
        console.log("Promoted:", event.inserted);
    });

    session.on("promotionFailed", event => {
        console.error("Promotion failed:", event.message);
    });

    const records = [
        {
            externalId: "INV-1001",
            product: "Laptop",
            quantity: 5,
            unitPrice: 75000
        },
        {
            externalId: "INV-1002",
            product: "Monitor",
            quantity: 10,
            unitPrice: 12000
        },
        {
            externalId: "INV-1003",
            product: "Keyboard",
            quantity: 20,
            unitPrice: 1500
        },
        {
            externalId: "INV-1001",
            product: "Duplicate Laptop",
            quantity: 2,
            unitPrice: 70000
        },
        {
            externalId: "INV-1004",
            product: "Invalid Mouse",
            quantity: 0,
            unitPrice: 800
        },
        {
            externalId: "INV-1005",
            product: "Invalid Price",
            quantity: 2,
            unitPrice: -10
        }
    ];

    try {
        await session.load(records);

        const validation = await session.validate();

        console.table(validation);

        const inserted = await session.promote();

        console.log("Inserted records:", inserted);
        console.log("Report:", session.report());

        if (inserted !== 3) {
            throw new StagingError("Unexpected promotion count");
        }

        // Independent sessions have independent temporary staging.
        const secondSession = new StagingSession(repository);

        await secondSession.load([{
            externalId: "INV-1006",
            product: "Mouse",
            quantity: 15,
            unitPrice: 800
        }]);

        await secondSession.validate();
        await secondSession.promote();

        console.log("Second session:", secondSession.report());

        secondSession.close();

        session.truncate();

        console.log(
            "First session staging after truncation:",
            session.rawRows.length
        );

    } finally {
        session.close();
    }

    console.log("Permanent repository:", repository.report());

    // Verify closed-session access is rejected.
    try {
        session.report();
        throw new Error("Closed-session validation failed");
    } catch (error) {
        if (!(error instanceof StagingError)) {
            throw error;
        }
        console.log("Closed-session protection: verified");
    }
}

runWorkflow().catch(error => {
    console.error("Workflow error:", error.message);
    process.exitCode = 1;
});
