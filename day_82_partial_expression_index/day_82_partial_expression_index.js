"use strict";

/*
 * PARTIAL AND EXPRESSION INDEXES
 *
 * Event-driven index catalog and query eligibility evaluator.
 *
 * Features:
 * - Index metadata and lifecycle management
 * - Conditional index membership
 * - Expression evaluation
 * - Unique partial indexes
 * - Query predicate implication
 * - Event-driven index maintenance
 * - Asynchronous query simulation
 * - Workload-based index recommendations
 * - Validation and failure handling
 *
 * Runtime: Node.js 18+
 */

const { EventEmitter } = require("node:events");
const { randomUUID } = require("node:crypto");

// ============================================================
// 1. DOMAIN TYPES
// ============================================================

const IndexKind = Object.freeze({
    FULL: "FULL",
    PARTIAL: "PARTIAL",
    EXPRESSION: "EXPRESSION",
    PARTIAL_EXPRESSION: "PARTIAL_EXPRESSION"
});

const IndexState = Object.freeze({
    BUILDING: "BUILDING",
    READY: "READY",
    INVALID: "INVALID",
    DROPPED: "DROPPED"
});

const OrderStatus = Object.freeze({
    OPEN: "OPEN",
    PAID: "PAID",
    CANCELLED: "CANCELLED",
    ARCHIVED: "ARCHIVED"
});

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

class UniqueViolationError extends Error {
    constructor(message) {
        super(message);
        this.name = "UniqueViolationError";
    }
}

// ============================================================
// 2. EXPRESSION REGISTRY
// ============================================================

class ExpressionRegistry {
    constructor() {
        this.expressions = new Map();
    }

    register(name, evaluator) {
        if (typeof name !== "string" || !name.trim()) {
            throw new ValidationError("Expression name is required.");
        }

        if (typeof evaluator !== "function") {
            throw new ValidationError("Evaluator must be a function.");
        }

        if (this.expressions.has(name)) {
            throw new ValidationError(
                `Expression already registered: ${name}`
            );
        }

        this.expressions.set(name, evaluator);
    }

    evaluate(name, row) {
        const evaluator = this.expressions.get(name);

        if (!evaluator) {
            throw new ValidationError(
                `Unknown expression: ${name}`
            );
        }

        return evaluator(row);
    }

    has(name) {
        return this.expressions.has(name);
    }
}

const expressions = new ExpressionRegistry();

expressions.register(
    "lower(customer_email)",
    row => row.customer_email.toLowerCase()
);

expressions.register(
    "upper(region)",
    row => row.region.toUpperCase()
);

expressions.register(
    "amount",
    row => row.amount
);

expressions.register(
    "order_id",
    row => row.order_id
);

// ============================================================
// 3. PREDICATE REGISTRY
// ============================================================

class PredicateRegistry {
    constructor() {
        this.predicates = new Map();
    }

    register(name, evaluator) {
        if (this.predicates.has(name)) {
            throw new ValidationError(
                `Predicate already exists: ${name}`
            );
        }

        if (typeof evaluator !== "function") {
            throw new ValidationError("Invalid predicate evaluator.");
        }

        this.predicates.set(name, evaluator);
    }

    evaluate(name, row) {
        const evaluator = this.predicates.get(name);

        if (!evaluator) {
            throw new ValidationError(
                `Unknown predicate: ${name}`
            );
        }

        return evaluator(row);
    }

    has(name) {
        return this.predicates.has(name);
    }
}

const predicates = new PredicateRegistry();

predicates.register(
    "status = OPEN",
    row => row.status === OrderStatus.OPEN
);

predicates.register(
    "status = PAID",
    row => row.status === OrderStatus.PAID
);

predicates.register(
    "amount > 500",
    row => row.amount > 500
);

predicates.register(
    "status = OPEN AND amount > 300",
    row => row.status === OrderStatus.OPEN && row.amount > 300
);

// ============================================================
// 4. ORDER VALIDATION
// ============================================================

function validateOrder(order) {
    if (!Number.isSafeInteger(order.order_id) || order.order_id <= 0) {
        throw new ValidationError("Invalid order ID.");
    }

    if (
        typeof order.customer_email !== "string" ||
        !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(order.customer_email)
    ) {
        throw new ValidationError("Invalid email address.");
    }

    if (!Object.values(OrderStatus).includes(order.status)) {
        throw new ValidationError("Invalid order status.");
    }

    if (!Number.isFinite(order.amount) || order.amount < 0) {
        throw new ValidationError("Invalid order amount.");
    }

    if (typeof order.region !== "string" || !order.region.trim()) {
        throw new ValidationError("Invalid region.");
    }
}

// ============================================================
// 5. INDEX DEFINITION
// ============================================================

class IndexDefinition {
    constructor({
        name,
        kind,
        expression,
        predicate = null,
        unique = false
    }) {
        this.id = randomUUID();
        this.name = name;
        this.kind = kind;
        this.expression = expression;
        this.predicate = predicate;
        this.unique = unique;
        this.state = IndexState.BUILDING;
        this.entries = new Map();
        this.createdAt = new Date();

        this.validate();
    }

    validate() {
        if (!this.name || !/^[a-z][a-z0-9_]*$/.test(this.name)) {
            throw new ValidationError("Invalid index name.");
        }

        if (!Object.values(IndexKind).includes(this.kind)) {
            throw new ValidationError("Invalid index kind.");
        }

        if (!expressions.has(this.expression)) {
            throw new ValidationError("Unregistered index expression.");
        }

        if (this.predicate && !predicates.has(this.predicate)) {
            throw new ValidationError("Unregistered predicate.");
        }

        const requiresPredicate = [
            IndexKind.PARTIAL,
            IndexKind.PARTIAL_EXPRESSION
        ].includes(this.kind);

        if (requiresPredicate !== Boolean(this.predicate)) {
            throw new ValidationError(
                "Index kind and predicate are inconsistent."
            );
        }

        if (
            this.kind === IndexKind.FULL ||
            this.kind === IndexKind.PARTIAL
        ) {
            if (this.expression.includes("(")) {
                throw new ValidationError(
                    "Expression not allowed for this index kind."
                );
            }
        }
    }
}

// ============================================================
// 6. INDEX CATALOG
// ============================================================

class IndexCatalog extends EventEmitter {
    constructor() {
        super();
        this.indexes = new Map();
        this.rows = new Map();
    }

    addIndex(definition) {
        if (!(definition instanceof IndexDefinition)) {
            throw new ValidationError("Invalid index definition.");
        }

        if (this.indexes.has(definition.name)) {
            throw new ValidationError("Duplicate index name.");
        }

        this.indexes.set(definition.name, definition);

        try {
            for (const row of this.rows.values()) {
                this.insertEntry(definition, row);
            }

            definition.state = IndexState.READY;

            this.emit("indexReady", {
                name: definition.name,
                entries: definition.entries.size
            });

        } catch (error) {
            definition.state = IndexState.INVALID;
            this.indexes.delete(definition.name);
            definition.entries.clear();
            throw error;
        }

        return definition;
    }

    insertEntry(index, row) {
        if (
            index.predicate &&
            !predicates.evaluate(index.predicate, row)
        ) {
            return;
        }

        const key = expressions.evaluate(index.expression, row);

        if (key === null || key === undefined) {
            return;
        }

        if (index.unique) {
            for (const [existingKey, ids] of index.entries) {
                if (
                    existingKey === key &&
                    !ids.has(row.order_id)
                ) {
                    throw new UniqueViolationError(
                        `Unique index violation: ${index.name}`
                    );
                }
            }
        }

        if (!index.entries.has(key)) {
            index.entries.set(key, new Set());
        }

        index.entries.get(key).add(row.order_id);
    }

    removeEntry(index, row) {
        const key = expressions.evaluate(index.expression, row);
        const ids = index.entries.get(key);

        if (!ids) return;

        ids.delete(row.order_id);

        if (ids.size === 0) {
            index.entries.delete(key);
        }
    }

    insertRow(row) {
        validateOrder(row);

        if (this.rows.has(row.order_id)) {
            throw new ValidationError("Duplicate order ID.");
        }

        // Check all indexes before publishing the new row.
        const completed = [];

        try {
            for (const index of this.indexes.values()) {
                this.insertEntry(index, row);
                completed.push(index);
            }

            this.rows.set(row.order_id, Object.freeze({ ...row }));

        } catch (error) {
            for (const index of completed) {
                this.removeEntry(index, row);
            }

            throw error;
        }

        this.emit("rowInserted", { id: row.order_id });
    }

    updateRow(id, changes) {
        const current = this.rows.get(id);

        if (!current) {
            throw new ValidationError("Order does not exist.");
        }

        const updated = { ...current, ...changes };

        validateOrder(updated);

        const oldEntries = new Map();

        for (const index of this.indexes.values()) {
            oldEntries.set(index.name, new Map(
                [...index.entries].map(([key, ids]) => [
                    key,
                    new Set(ids)
                ])
            ));
        }

        try {
            for (const index of this.indexes.values()) {
                this.removeEntry(index, current);
                this.insertEntry(index, updated);
            }

            this.rows.set(id, Object.freeze(updated));

        } catch (error) {
            for (const index of this.indexes.values()) {
                index.entries = oldEntries.get(index.name);
            }

            throw error;
        }

        this.emit("rowUpdated", { id });
    }

    dropIndex(name) {
        const index = this.indexes.get(name);

        if (!index) {
            throw new ValidationError("Index not found.");
        }

        index.entries.clear();
        index.state = IndexState.DROPPED;
        this.indexes.delete(name);

        this.emit("indexDropped", { name });
    }

    getIndex(name) {
        return this.indexes.get(name) ?? null;
    }
}

// ============================================================
// 7. QUERY POLICY
// ============================================================

class QueryPolicy {
    constructor({ expression, predicate = null, value }) {
        this.expression = expression;
        this.predicate = predicate;
        this.value = value;
    }

    validate() {
        if (!expressions.has(this.expression)) {
            throw new ValidationError("Unknown query expression.");
        }

        if (this.predicate && !predicates.has(this.predicate)) {
            throw new ValidationError("Unknown query predicate.");
        }
    }
}

class IndexAdvisor {
    constructor(catalog) {
        this.catalog = catalog;
    }

    eligible(index, query) {
        if (index.state !== IndexState.READY) {
            return false;
        }

        if (index.expression !== query.expression) {
            return false;
        }

        if (!index.predicate) {
            return true;
        }

        // Conservative predicate implication:
        // only an identical registered predicate is accepted.
        return index.predicate === query.predicate;
    }

    explain(query) {
        query.validate();

        const candidates = [];

        for (const index of this.catalog.indexes.values()) {
            if (this.eligible(index, query)) {
                candidates.push({
                    index: index.name,
                    expression: index.expression,
                    predicate: index.predicate,
                    entries: index.entries.size
                });
            }
        }

        return {
            query,
            candidates,
            indexAvailable: candidates.length > 0,
            strategy: candidates.length > 0
                ? "INDEX_CANDIDATE"
                : "TABLE_SCAN_OR_OTHER_PLAN"
        };
    }
}

// ============================================================
// 8. ASYNCHRONOUS QUERY SERVICE
// ============================================================

class QueryService {
    constructor(catalog, advisor) {
        this.catalog = catalog;
        this.advisor = advisor;
    }

    async execute(query) {
        // Simulates an asynchronous database request.
        await Promise.resolve();

        const plan = this.advisor.explain(query);

        const result = [];

        for (const row of this.catalog.rows.values()) {
            const key = expressions.evaluate(
                query.expression,
                row
            );

            const predicateMatches = !query.predicate ||
                predicates.evaluate(query.predicate, row);

            if (key === query.value && predicateMatches) {
                result.push(row);
            }
        }

        return {
            plan,
            rows: result,
            count: result.length
        };
    }
}

// ============================================================
// 9. WORKLOAD-BASED INDEX ADVISOR
// ============================================================

class WorkloadAnalyzer {
    constructor() {
        this.frequency = new Map();
    }

    record(expression, predicate = null) {
        const signature = `${expression}|${predicate ?? "NONE"}`;

        this.frequency.set(
            signature,
            (this.frequency.get(signature) ?? 0) + 1
        );
    }

    recommendations() {
        return [...this.frequency.entries()]
            .sort((a, b) => b[1] - a[1])
            .map(([signature, executions]) => ({
                signature,
                executions
            }));
    }
}

// ============================================================
// 10. EXECUTION
// ============================================================

async function main() {
    const catalog = new IndexCatalog();

    catalog.on("indexReady", event => {
        console.log("INDEX READY:", event);
    });

    catalog.on("rowUpdated", event => {
        console.log("ROW UPDATED:", event);
    });

    const sampleOrders = [
        {
            order_id: 1,
            customer_email: "alice@example.com",
            status: OrderStatus.OPEN,
            amount: 450,
            region: "NORTH"
        },
        {
            order_id: 2,
            customer_email: "bob@example.com",
            status: OrderStatus.PAID,
            amount: 900,
            region: "SOUTH"
        },
        {
            order_id: 3,
            customer_email: "carol@example.com",
            status: OrderStatus.OPEN,
            amount: 250,
            region: "NORTH"
        },
        {
            order_id: 4,
            customer_email: "david@example.com",
            status: OrderStatus.CANCELLED,
            amount: 120,
            region: "WEST"
        },
        {
            order_id: 5,
            customer_email: "eve@example.com",
            status: OrderStatus.ARCHIVED,
            amount: 300,
            region: "EAST"
        },
        {
            order_id: 6,
            customer_email: "frank@example.com",
            status: OrderStatus.OPEN,
            amount: 780,
            region: "SOUTH"
        }
    ];

    for (const order of sampleOrders) {
        catalog.insertRow(order);
    }

    const definitions = [
        new IndexDefinition({
            name: "idx_open_orders",
            kind: IndexKind.PARTIAL,
            expression: "order_id",
            predicate: "status = OPEN"
        }),

        new IndexDefinition({
            name: "idx_lower_email",
            kind: IndexKind.EXPRESSION,
            expression: "lower(customer_email)"
        }),

        new IndexDefinition({
            name: "idx_open_high_value",
            kind: IndexKind.PARTIAL_EXPRESSION,
            expression: "amount",
            predicate: "status = OPEN AND amount > 300"
        }),

        new IndexDefinition({
            name: "idx_upper_region",
            kind: IndexKind.EXPRESSION,
            expression: "upper(region)"
        })
    ];

    for (const definition of definitions) {
        catalog.addIndex(definition);
    }

    const advisor = new IndexAdvisor(catalog);
    const service = new QueryService(catalog, advisor);

    console.log("\nPARTIAL INDEX QUERY");

    const openQuery = new QueryPolicy({
        expression: "order_id",
        predicate: "status = OPEN",
        value: 1
    });

    console.log(
        JSON.stringify(advisor.explain(openQuery), null, 2)
    );

    console.log("\nEXPRESSION INDEX QUERY");

    const emailQuery = new QueryPolicy({
        expression: "lower(customer_email)",
        value: "alice@example.com"
    });

    const emailResult = await service.execute(emailQuery);

    console.log("Matched rows:", emailResult.count);
    console.log(emailResult.rows);

    console.log("\nPARTIAL EXPRESSION QUERY");

    const amountQuery = new QueryPolicy({
        expression: "amount",
        predicate: "status = OPEN AND amount > 300",
        value: 780
    });

    const amountResult = await service.execute(amountQuery);

    console.log(amountResult);

    console.log("\nINDEX MAINTENANCE");

    catalog.updateRow(1, {
        status: OrderStatus.PAID
    });

    console.log(
        "Open-order index entries:",
        catalog.getIndex("idx_open_orders").entries.size
    );

    console.log("\nWORKLOAD ANALYSIS");

    const workload = new WorkloadAnalyzer();

    for (let i = 0; i < 100; i++) {
        workload.record("lower(customer_email)");
    }

    for (let i = 0; i < 40; i++) {
        workload.record(
            "amount",
            "status = OPEN AND amount > 300"
        );
    }

    console.log(workload.recommendations());

    console.log("\nVALIDATION");

    try {
        catalog.insertRow({
            order_id: 7,
            customer_email: "invalid-email",
            status: OrderStatus.OPEN,
            amount: 200,
            region: "NORTH"
        });

        throw new Error("Invalid record was accepted.");

    } catch (error) {
        if (!(error instanceof ValidationError)) {
            throw error;
        }

        console.log("Invalid record rejected.");
    }

    if (emailResult.count !== 1) {
        throw new Error("Email lookup assertion failed.");
    }

    if (amountResult.count !== 1) {
        throw new Error("Partial expression assertion failed.");
    }

    console.log("\nAll demonstrations completed.");
}

main().catch(error => {
    console.error("Execution failed:", error);
    process.exitCode = 1;
});
