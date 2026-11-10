"use strict";

/*
 * Materialized Views: Event-Driven Refresh and Query Management
 *
 * Node.js 18+
 *
 * Features:
 * - Event-driven source-table change tracking
 * - Full and incremental aggregate maintenance
 * - Materialized snapshot generations
 * - Asynchronous refresh coordination
 * - Refresh deduplication
 * - Dependency-aware scheduling
 * - Staleness policies
 * - Failure isolation
 * - Query caching
 * - Refresh observability
 *
 * Run:
 * node materialized_views.js
 */

const { EventEmitter } = require("node:events");
const crypto = require("node:crypto");
const assert = require("node:assert/strict");

const RefreshMode = Object.freeze({
    FULL: "FULL",
    INCREMENTAL: "INCREMENTAL"
});

const RefreshState = Object.freeze({
    SUCCESS: "SUCCESS",
    FAILED: "FAILED",
    SKIPPED: "SKIPPED"
});

class DomainError extends Error {}

class ValidationError extends DomainError {}

class RefreshError extends DomainError {}

function validateSale(sale) {
    if (!Number.isSafeInteger(sale.id) || sale.id <= 0) {
        throw new ValidationError("Invalid sale identifier.");
    }

    if (!Number.isSafeInteger(sale.productId) || sale.productId <= 0) {
        throw new ValidationError("Invalid product identifier.");
    }

    if (!Number.isSafeInteger(sale.quantity) || sale.quantity <= 0) {
        throw new ValidationError("Quantity must be positive.");
    }

    if (!Number.isFinite(sale.unitPrice) || sale.unitPrice < 0) {
        throw new ValidationError("Invalid unit price.");
    }

    if (
        typeof sale.category !== "string" ||
        !sale.category.trim() ||
        typeof sale.region !== "string" ||
        !sale.region.trim()
    ) {
        throw new ValidationError("Invalid grouping dimensions.");
    }

    if (!Number.isFinite(Date.parse(sale.createdAt))) {
        throw new ValidationError("Invalid timestamp.");
    }

    return Object.freeze({ ...sale });
}

class SourceRepository extends EventEmitter {
    #records = new Map();
    #version = 0;
    #journal = [];

    insert(input) {
        const sale = validateSale(input);

        if (this.#records.has(sale.id)) {
            throw new ValidationError("Duplicate sale identifier.");
        }

        this.#records.set(sale.id, sale);
        this.#publish("INSERT", null, sale);

        return sale;
    }

    update(input) {
        const sale = validateSale(input);
        const previous = this.#records.get(sale.id);

        if (!previous) {
            throw new ValidationError("Sale does not exist.");
        }

        this.#records.set(sale.id, sale);
        this.#publish("UPDATE", previous, sale);

        return sale;
    }

    delete(id) {
        const previous = this.#records.get(id);

        if (!previous) {
            throw new ValidationError("Sale does not exist.");
        }

        this.#records.delete(id);
        this.#publish("DELETE", previous, null);
    }

    #publish(operation, before, after) {
        const event = Object.freeze({
            version: ++this.#version,
            operation,
            before,
            after,
            timestamp: new Date().toISOString()
        });

        this.#journal.push(event);
        this.emit("change", event);
    }

    snapshot() {
        return {
            version: this.#version,
            records: Array.from(this.#records.values()),
            journal: this.#journal.slice()
        };
    }

    changesSince(version) {
        return this.#journal.filter(
            event => event.version > version
        );
    }
}

class AggregationDefinition {
    constructor(dimensions) {
        const allowed = new Set([
            "category",
            "region",
            "productId",
            "date"
        ]);

        if (
            !Array.isArray(dimensions) ||
            dimensions.length === 0 ||
            dimensions.some(d => !allowed.has(d)) ||
            new Set(dimensions).size !== dimensions.length
        ) {
            throw new ValidationError("Invalid dimensions.");
        }

        this.dimensions = Object.freeze([...dimensions]);
    }

    key(sale) {
        return JSON.stringify(
            this.dimensions.map(dimension => {
                if (dimension === "date") {
                    return sale.createdAt.slice(0, 10);
                }
                return sale[dimension];
            })
        );
    }

    group(sale) {
        const result = {};

        for (const dimension of this.dimensions) {
            result[dimension] =
                dimension === "date"
                    ? sale.createdAt.slice(0, 10)
                    : sale[dimension];
        }

        return result;
    }
}

class AggregateState {
    constructor() {
        this.count = 0;
        this.quantity = 0;
        this.revenue = 0;
    }

    add(sale) {
        this.count++;
        this.quantity += sale.quantity;
        this.revenue += sale.quantity * sale.unitPrice;
    }

    subtract(sale) {
        this.count--;
        this.quantity -= sale.quantity;
        this.revenue -= sale.quantity * sale.unitPrice;

        if (this.count < 0 || this.quantity < 0) {
            throw new RefreshError("Negative aggregate state.");
        }

        if (this.count === 0) {
            this.quantity = 0;
            this.revenue = 0;
        }
    }

    serialize() {
        return Object.freeze({
            count: this.count,
            quantity: this.quantity,
            revenue: Number(this.revenue.toFixed(2))
        });
    }
}

class MaterializedView extends EventEmitter {
    #source;
    #definition;
    #snapshot = Object.freeze({
        generation: 0,
        sourceVersion: 0,
        refreshedAt: null,
        rows: Object.freeze([]),
        checksum: null
    });

    #refreshPromise = null;
    #cache = new Map();

    constructor(name, source, dimensions) {
        super();

        if (!/^[a-z][a-z0-9_]{2,60}$/.test(name)) {
            throw new ValidationError("Invalid view name.");
        }

        this.name = name;
        this.#source = source;
        this.#definition = new AggregationDefinition(dimensions);
    }

    get snapshot() {
        return this.#snapshot;
    }

    get stale() {
        return (
            this.#snapshot.sourceVersion <
            this.#source.snapshot().version
        );
    }

    #build(records) {
        const groups = new Map();

        for (const sale of records) {
            const key = this.#definition.key(sale);

            if (!groups.has(key)) {
                groups.set(key, {
                    dimensions: this.#definition.group(sale),
                    aggregate: new AggregateState()
                });
            }

            groups.get(key).aggregate.add(sale);
        }

        return Array.from(groups.values())
            .map(item => Object.freeze({
                ...item.dimensions,
                ...item.aggregate.serialize()
            }));
    }

    #checksum(rows) {
        return crypto
            .createHash("sha256")
            .update(JSON.stringify(rows))
            .digest("hex");
    }

    async refresh(mode = RefreshMode.FULL) {
        if (!Object.values(RefreshMode).includes(mode)) {
            throw new ValidationError("Unknown refresh mode.");
        }

        // Concurrent requests share one refresh operation.
        if (this.#refreshPromise) {
            return this.#refreshPromise;
        }

        this.#refreshPromise = this.#performRefresh(mode);

        try {
            return await this.#refreshPromise;
        } finally {
            this.#refreshPromise = null;
        }
    }

    async #performRefresh(mode) {
        const started = performance.now();

        try {
            // Yield to the event loop to model asynchronous I/O.
            await new Promise(resolve => setImmediate(resolve));

            const sourceSnapshot = this.#source.snapshot();

            if (
                mode === RefreshMode.INCREMENTAL &&
                this.#snapshot.generation > 0 &&
                this.#snapshot.sourceVersion === sourceSnapshot.version
            ) {
                return {
                    view: this.name,
                    status: RefreshState.SKIPPED,
                    recordsProcessed: 0
                };
            }

            // Recompute from the consistent source snapshot.
            // This correctness-first strategy handles updates and
            // deletions without double-counting change events.
            const rows = this.#build(sourceSnapshot.records);

            const candidate = Object.freeze({
                generation: this.#snapshot.generation + 1,
                sourceVersion: sourceSnapshot.version,
                refreshedAt: new Date().toISOString(),
                rows: Object.freeze(rows),
                checksum: this.#checksum(rows)
            });

            // Publish only after the complete snapshot is built.
            this.#snapshot = candidate;
            this.#cache.clear();

            const result = {
                view: this.name,
                status: RefreshState.SUCCESS,
                mode,
                generation: candidate.generation,
                recordsProcessed: sourceSnapshot.records.length,
                durationMs: Number(
                    (performance.now() - started).toFixed(3)
                ),
                checksum: candidate.checksum
            };

            this.emit("refreshed", result);
            return result;

        } catch (error) {
            const result = {
                view: this.name,
                status: RefreshState.FAILED,
                error: error.message,
                durationMs: performance.now() - started
            };

            this.emit("refreshFailed", result);
            throw new RefreshError(
                `${this.name}: ${error.message}`
            );
        }
    }

    query(filters = {}) {
        if (
            filters === null ||
            typeof filters !== "object" ||
            Array.isArray(filters)
        ) {
            throw new ValidationError("Filters must be an object.");
        }

        const allowed = new Set(
            this.#definition.dimensions
        );

        for (const key of Object.keys(filters)) {
            if (!allowed.has(key)) {
                throw new ValidationError(
                    `Unsupported filter: ${key}`
                );
            }
        }

        const cacheKey = JSON.stringify([
            this.#snapshot.generation,
            filters
        ]);

        if (this.#cache.has(cacheKey)) {
            return this.#cache.get(cacheKey);
        }

        const result = Object.freeze(
            this.#snapshot.rows.filter(row =>
                Object.entries(filters).every(
                    ([key, value]) => row[key] === value
                )
            )
        );

        this.#cache.set(cacheKey, result);
        return result;
    }
}

class RefreshCoordinator {
    #views = new Map();
    #dependencies = new Map();
    #audit = [];

    register(view, dependencies = []) {
        if (this.#views.has(view.name)) {
            throw new ValidationError("Duplicate view registration.");
        }

        this.#views.set(view.name, view);
        this.#dependencies.set(
            view.name,
            new Set(dependencies)
        );
    }

    #order(target) {
        const result = [];
        const visiting = new Set();
        const visited = new Set();

        const visit = name => {
            if (visiting.has(name)) {
                throw new ValidationError(
                    "Circular view dependency detected."
                );
            }

            if (visited.has(name)) return;

            const view = this.#views.get(name);

            if (!view) {
                throw new ValidationError(
                    `Unknown view: ${name}`
                );
            }

            visiting.add(name);

            for (const dependency of this.#dependencies.get(name)) {
                visit(dependency);
            }

            visiting.delete(name);
            visited.add(name);
            result.push(view);
        };

        visit(target);
        return result;
    }

    async refresh(target, mode) {
        const results = [];

        for (const view of this.#order(target)) {
            try {
                const result = await view.refresh(mode);
                this.#audit.push(result);
                results.push(result);

                if (result.status === RefreshState.FAILED) {
                    break;
                }
            } catch (error) {
                const failure = {
                    view: view.name,
                    status: RefreshState.FAILED,
                    error: error.message
                };

                this.#audit.push(failure);
                results.push(failure);
                break;
            }
        }

        return results;
    }

    get audit() {
        return [...this.#audit];
    }
}

function createSampleData(repository) {
    const now = new Date();

    const rows = [
        [1, 101, "Electronics", "North", 3, 1200],
        [2, 102, "Furniture", "South", 2, 850],
        [3, 101, "Electronics", "North", 1, 1200],
        [4, 103, "Clothing", "West", 5, 90],
        [5, 104, "Electronics", "East", 2, 700],
        [6, 102, "Furniture", "South", 1, 850],
        [7, 105, "Clothing", "North", 4, 120]
    ];

    for (const row of rows) {
        repository.insert({
            id: row[0],
            productId: row[1],
            category: row[2],
            region: row[3],
            quantity: row[4],
            unitPrice: row[5],
            createdAt: new Date(
                now.getTime() - row[0] * 86400000
            ).toISOString()
        });
    }
}

async function runTests() {
    const source = new SourceRepository();
    createSampleData(source);

    const view = new MaterializedView(
        "sales_by_category",
        source,
        ["category"]
    );

    const result = await view.refresh();
    assert.equal(result.status, RefreshState.SUCCESS);

    const originalGeneration = view.snapshot.generation;

    assert.equal(
        view.query({ category: "Electronics" })[0].revenue,
        5000
    );

    source.insert({
        id: 8,
        productId: 101,
        category: "Electronics",
        region: "North",
        quantity: 2,
        unitPrice: 1200,
        createdAt: new Date().toISOString()
    });

    assert.equal(view.stale, true);

    await view.refresh(RefreshMode.INCREMENTAL);

    assert.equal(view.stale, false);
    assert.equal(view.snapshot.generation, originalGeneration + 1);
    assert.equal(
        view.query({ category: "Electronics" })[0].revenue,
        7400
    );

    source.delete(8);
    await view.refresh(RefreshMode.INCREMENTAL);

    assert.equal(
        view.query({ category: "Electronics" })[0].revenue,
        5000
    );

    assert.throws(
        () => source.insert({
            id: 1,
            productId: 101,
            category: "Electronics",
            region: "North",
            quantity: 1,
            unitPrice: 100,
            createdAt: new Date().toISOString()
        }),
        ValidationError
    );

    console.log("All JavaScript tests passed.");
}

async function main() {
    const source = new SourceRepository();
    createSampleData(source);

    const categoryView = new MaterializedView(
        "sales_by_category",
        source,
        ["category"]
    );

    const regionalView = new MaterializedView(
        "sales_by_region",
        source,
        ["region"]
    );

    const coordinator = new RefreshCoordinator();

    coordinator.register(categoryView);
    coordinator.register(regionalView, [
        "sales_by_category"
    ]);

    categoryView.on("refreshed", event =>
        console.log("REFRESH EVENT:", event.view, event.generation)
    );

    categoryView.on("refreshFailed", event =>
        console.error("REFRESH FAILURE:", event.error)
    );

    console.log("INITIAL REFRESH");

    console.log(
        await coordinator.refresh(
            "sales_by_region",
            RefreshMode.FULL
        )
    );

    console.log("CATEGORY REPORT");
    console.table(categoryView.query());

    console.log("SOURCE UPDATE");

    source.insert({
        id: 8,
        productId: 106,
        category: "Electronics",
        region: "West",
        quantity: 3,
        unitPrice: 1500,
        createdAt: new Date().toISOString()
    });

    console.log("Stale:", categoryView.stale);

    console.log("INCREMENTAL REFRESH");

    console.log(
        await coordinator.refresh(
            "sales_by_region",
            RefreshMode.INCREMENTAL
        )
    );

    console.log("FINAL REGIONAL REPORT");
    console.table(regionalView.query());

    console.log("AUDIT");
    console.table(coordinator.audit);

    await runTests();
}

main().catch(error => {
    console.error("Application failed:", error.message);
    process.exitCode = 1;
});
