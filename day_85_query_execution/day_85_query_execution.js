"use strict";

/*
 * QUERY EXECUTION AND OPTIMIZATION MODEL
 *
 * Event-driven query execution simulator.
 *
 * Focus:
 * - Query lifecycle events
 * - Logical and physical plan separation
 * - Cost-based access-path selection
 * - Index and sequential scans
 * - Predicate evaluation
 * - Projection and ordering
 * - Execution cancellation
 * - Prepared statement caching
 * - Concurrent query execution
 * - Resource limits and error handling
 *
 * Runtime: Node.js 18+
 */

const { EventEmitter } = require("node:events");
const { performance } = require("node:perf_hooks");
const crypto = require("node:crypto");


class QueryError extends Error {
    constructor(message, code = "QUERY_ERROR") {
        super(message);
        this.name = "QueryError";
        this.code = code;
    }
}


const OPERATORS = new Set([
    "=", "!=", "<>", ">", "<", ">=", "<="
]);


class TableStore {
    constructor() {
        this.tables = new Map();
    }

    createTable(name, columns, rows, indexes = []) {
        if (this.tables.has(name)) {
            throw new QueryError(
                `Table already exists: ${name}`,
                "TABLE_EXISTS"
            );
        }

        if (!Array.isArray(columns) || columns.length === 0) {
            throw new QueryError("A table requires columns.");
        }

        if (new Set(columns).size !== columns.length) {
            throw new QueryError("Duplicate column names.");
        }

        for (const row of rows) {
            if (
                Object.keys(row).length !== columns.length ||
                !columns.every(column =>
                    Object.hasOwn(row, column)
                )
            ) {
                throw new QueryError(
                    "Row structure does not match table schema."
                );
            }
        }

        const indexMap = new Map();

        for (const column of indexes) {
            if (!columns.includes(column)) {
                throw new QueryError(
                    `Cannot index unknown column: ${column}`
                );
            }

            const index = new Map();

            for (let i = 0; i < rows.length; i++) {
                const value = rows[i][column];

                if (!index.has(value)) {
                    index.set(value, []);
                }

                index.get(value).push(i);
            }

            indexMap.set(column, index);
        }

        this.tables.set(name, {
            name,
            columns: Object.freeze([...columns]),
            rows: Object.freeze(rows.map(row =>
                Object.freeze({ ...row })
            )),
            indexes: indexMap,
            estimatedRows: rows.length,
            version: 1
        });
    }

    get(name) {
        const table = this.tables.get(name);

        if (!table) {
            throw new QueryError(
                `Table not found: ${name}`,
                "TABLE_NOT_FOUND"
            );
        }

        return table;
    }
}


class Predicate {
    static compare(actual, operator, expected) {
        if (!OPERATORS.has(operator)) {
            throw new QueryError("Unsupported comparison operator.");
        }

        if (actual === null || actual === undefined ||
            expected === null || expected === undefined) {
            return null;
        }

        switch (operator) {
            case "=":
                return actual === expected;
            case "!=":
            case "<>":
                return actual !== expected;
            case ">":
                return actual > expected;
            case "<":
                return actual < expected;
            case ">=":
                return actual >= expected;
            case "<=":
                return actual <= expected;
            default:
                return false;
        }
    }

    static evaluate(condition, row) {
        if (condition.type === "AND") {
            const left = this.evaluate(condition.left, row);
            const right = this.evaluate(condition.right, row);

            if (left === false || right === false) return false;
            if (left === null || right === null) return null;

            return Boolean(left && right);
        }

        if (condition.type === "OR") {
            const left = this.evaluate(condition.left, row);
            const right = this.evaluate(condition.right, row);

            if (left === true || right === true) return true;
            if (left === null || right === null) return null;

            return Boolean(left || right);
        }

        if (condition.type === "NOT") {
            const value = this.evaluate(condition.condition, row);
            return value === null ? null : !value;
        }

        if (condition.type === "COMPARE") {
            if (!Object.hasOwn(row, condition.column)) {
                throw new QueryError(
                    `Unknown column: ${condition.column}`
                );
            }

            return this.compare(
                row[condition.column],
                condition.operator,
                condition.value
            );
        }

        throw new QueryError(
            `Invalid predicate type: ${condition.type}`
        );
    }
}


class QueryRequest {
    constructor({
        table,
        columns = ["*"],
        predicate = null,
        orderBy = [],
        limit = null
    }) {
        this.table = table;
        this.columns = columns;
        this.predicate = predicate;
        this.orderBy = orderBy;
        this.limit = limit;

        if (typeof table !== "string" || !table.trim()) {
            throw new QueryError("Invalid table name.");
        }

        if (!Array.isArray(columns) || columns.length === 0) {
            throw new QueryError("Invalid projection.");
        }

        if (
            limit !== null &&
            (!Number.isSafeInteger(limit) || limit < 0)
        ) {
            throw new QueryError("LIMIT must be non-negative.");
        }

        for (const item of orderBy) {
            if (
                typeof item.column !== "string" ||
                !["ASC", "DESC"].includes(item.direction)
            ) {
                throw new QueryError("Invalid sort specification.");
            }
        }
    }
}


class LogicalPlanner {
    build(request, table) {
        const columns = request.columns.includes("*")
            ? table.columns
            : request.columns;

        for (const column of columns) {
            if (!table.columns.includes(column)) {
                throw new QueryError(
                    `Unknown projected column: ${column}`
                );
            }
        }

        for (const item of request.orderBy) {
            if (!table.columns.includes(item.column)) {
                throw new QueryError(
                    `Unknown ordering column: ${item.column}`
                );
            }
        }

        this.validatePredicate(request.predicate, table.columns);

        return {
            type: "PROJECT",
            columns,
            child: {
                type: "LIMIT",
                count: request.limit,
                child: {
                    type: "SORT",
                    orderBy: request.orderBy,
                    child: {
                        type: "FILTER",
                        predicate: request.predicate,
                        child: {
                            type: "SCAN",
                            table: request.table
                        }
                    }
                }
            }
        };
    }

    validatePredicate(predicate, columns) {
        if (!predicate) return;

        if (predicate.type === "COMPARE") {
            if (!columns.includes(predicate.column)) {
                throw new QueryError(
                    `Unknown predicate column: ${predicate.column}`
                );
            }

            if (!OPERATORS.has(predicate.operator)) {
                throw new QueryError("Invalid predicate operator.");
            }

            return;
        }

        if (predicate.type === "NOT") {
            this.validatePredicate(predicate.condition, columns);
            return;
        }

        if (predicate.type === "AND" || predicate.type === "OR") {
            this.validatePredicate(predicate.left, columns);
            this.validatePredicate(predicate.right, columns);
            return;
        }

        throw new QueryError("Invalid predicate structure.");
    }
}


class CostOptimizer {
    constructor(options = {}) {
        this.indexStartupCost = options.indexStartupCost ?? 2;
        this.rowScanCost = options.rowScanCost ?? 1;
        this.indexRowCost = options.indexRowCost ?? 0.2;
    }

    optimize(request, table) {
        const predicate = request.predicate;

        let accessPath = "SEQUENTIAL_SCAN";
        let estimatedRows = table.estimatedRows;
        let estimatedCost =
            table.estimatedRows * this.rowScanCost;

        // Equality predicates on indexed columns can use an index.
        if (
            predicate &&
            predicate.type === "COMPARE" &&
            predicate.operator === "=" &&
            table.indexes.has(predicate.column)
        ) {
            const index = table.indexes.get(predicate.column);
            const matches = index.get(predicate.value) || [];

            const indexCost =
                this.indexStartupCost +
                matches.length * this.indexRowCost;

            if (indexCost < estimatedCost) {
                accessPath = "INDEX_SCAN";
                estimatedRows = matches.length;
                estimatedCost = indexCost;
            }
        }

        const plan = {
            accessPath,
            estimatedRows,
            estimatedCost: Number(estimatedCost.toFixed(3)),
            predicatePushdown: Boolean(predicate),
            projectionPushdown: true,
            table: table.name
        };

        return Object.freeze(plan);
    }
}


class ExecutionEngine extends EventEmitter {
    constructor(store, options = {}) {
        super();

        this.store = store;
        this.logicalPlanner = new LogicalPlanner();
        this.optimizer = new CostOptimizer();
        this.maxRows = options.maxRows ?? 100000;
        this.maxConcurrent = options.maxConcurrent ?? 4;
        this.activeQueries = 0;
    }

    async execute(request, options = {}) {
        if (this.activeQueries >= this.maxConcurrent) {
            throw new QueryError(
                "Concurrent query limit exceeded.",
                "RESOURCE_LIMIT"
            );
        }

        this.activeQueries++;

        const queryId = crypto.randomUUID();
        const start = performance.now();
        const signal = options.signal;

        const statistics = {
            scanned: 0,
            filtered: 0,
            returned: 0,
            accessPath: null
        };

        const emit = (event, data = {}) => {
            this.emit(event, {
                queryId,
                timestamp: new Date().toISOString(),
                ...data
            });
        };

        try {
            if (signal?.aborted) {
                throw new QueryError("Query cancelled.", "CANCELLED");
            }

            emit("query:start");

            const table = this.store.get(request.table);

            const logicalPlan =
                this.logicalPlanner.build(request, table);

            emit("plan:logical", { logicalPlan });

            const physicalPlan =
                this.optimizer.optimize(request, table);

            statistics.accessPath = physicalPlan.accessPath;

            emit("plan:physical", { physicalPlan });

            let candidates = table.rows;

            if (physicalPlan.accessPath === "INDEX_SCAN") {
                const predicate = request.predicate;
                const index = table.indexes.get(predicate.column);
                const positions = index.get(predicate.value) || [];

                candidates = positions.map(position =>
                    table.rows[position]
                );
            }

            statistics.scanned = candidates.length;

            if (statistics.scanned > this.maxRows) {
                throw new QueryError(
                    "Query row limit exceeded.",
                    "RESOURCE_LIMIT"
                );
            }

            emit("execution:scan", {
                scanned: statistics.scanned
            });

            const filtered = [];

            for (let i = 0; i < candidates.length; i++) {
                if (signal?.aborted) {
                    throw new QueryError(
                        "Query cancelled.",
                        "CANCELLED"
                    );
                }

                const row = candidates[i];

                if (
                    !request.predicate ||
                    Predicate.evaluate(request.predicate, row) === true
                ) {
                    filtered.push(row);
                }

                // Yield periodically so cancellation and other tasks
                // can be processed by the event loop.
                if (i > 0 && i % 5000 === 0) {
                    await new Promise(resolve => setImmediate(resolve));
                }
            }

            statistics.filtered =
                candidates.length - filtered.length;

            let result = [...filtered];

            if (request.orderBy.length) {
                result.sort((a, b) => {
                    for (const item of request.orderBy) {
                        const left = a[item.column];
                        const right = b[item.column];

                        let comparison = 0;

                        if (left === null || left === undefined) {
                            comparison =
                                right === null || right === undefined ? 0 : 1;
                        } else if (
                            right === null ||
                            right === undefined
                        ) {
                            comparison = -1;
                        } else if (left < right) {
                            comparison = -1;
                        } else if (left > right) {
                            comparison = 1;
                        }

                        if (comparison !== 0) {
                            return item.direction === "DESC"
                                ? -comparison
                                : comparison;
                        }
                    }

                    return 0;
                });
            }

            if (request.limit !== null) {
                result = result.slice(0, request.limit);
            }

            const projectedColumns = request.columns.includes("*")
                ? table.columns
                : request.columns;

            result = result.map(row => {
                const projected = {};

                for (const column of projectedColumns) {
                    projected[column] = row[column];
                }

                return Object.freeze(projected);
            });

            statistics.returned = result.length;

            const response = {
                queryId,
                rows: result,
                statistics,
                logicalPlan,
                physicalPlan,
                executionMs: Number(
                    (performance.now() - start).toFixed(3)
                )
            };

            emit("query:complete", {
                statistics,
                executionMs: response.executionMs
            });

            return response;

        } catch (error) {
            emit("query:error", {
                message: error.message,
                code: error.code || "INTERNAL_ERROR"
            });

            throw error;

        } finally {
            this.activeQueries--;
        }
    }
}


class PreparedStatementCache {
    constructor(capacity = 100) {
        this.capacity = capacity;
        this.cache = new Map();
        this.hits = 0;
        this.misses = 0;
    }

    get(key) {
        if (!this.cache.has(key)) {
            this.misses++;
            return null;
        }

        this.hits++;

        const value = this.cache.get(key);

        // Move accessed entry to the end for LRU behavior.
        this.cache.delete(key);
        this.cache.set(key, value);

        return value;
    }

    set(key, value) {
        if (this.cache.has(key)) {
            this.cache.delete(key);
        }

        this.cache.set(key, value);

        if (this.cache.size > this.capacity) {
            const oldest = this.cache.keys().next().value;
            this.cache.delete(oldest);
        }
    }

    getStatistics() {
        return {
            entries: this.cache.size,
            hits: this.hits,
            misses: this.misses
        };
    }
}


async function main() {
    const store = new TableStore();

    store.createTable(
        "employees",
        ["id", "name", "department", "salary", "active"],
        [
            { id: 1, name: "Asha", department: "Engineering", salary: 95000, active: true },
            { id: 2, name: "Rahul", department: "Finance", salary: 72000, active: true },
            { id: 3, name: "Neha", department: "Engineering", salary: 110000, active: true },
            { id: 4, name: "Arjun", department: "Operations", salary: 68000, active: false },
            { id: 5, name: "Meera", department: "Engineering", salary: 88000, active: true }
        ],
        ["id", "department"]
    );

    const engine = new ExecutionEngine(store);

    for (const event of [
        "query:start",
        "plan:logical",
        "plan:physical",
        "execution:scan",
        "query:complete",
        "query:error"
    ]) {
        engine.on(event, data => {
            console.log(`[EVENT] ${event}`, data.queryId);
        });
    }

    const request = new QueryRequest({
        table: "employees",
        columns: ["name", "salary"],
        predicate: {
            type: "AND",
            left: {
                type: "COMPARE",
                column: "department",
                operator: "=",
                value: "Engineering"
            },
            right: {
                type: "COMPARE",
                column: "salary",
                operator: ">=",
                value: 90000
            }
        },
        orderBy: [
            { column: "salary", direction: "DESC" }
        ],
        limit: 10
    });

    const response = await engine.execute(request);

    console.log("\nQUERY RESULTS");
    console.table(response.rows);

    console.log("PHYSICAL PLAN");
    console.log(response.physicalPlan);

    console.log("STATISTICS");
    console.log(response.statistics);

    const cache = new PreparedStatementCache(2);

    cache.set("employee-query-v1", request);
    cache.get("employee-query-v1");
    cache.get("employee-query-v2");

    console.log("CACHE");
    console.log(cache.getStatistics());

    // Validate NULL comparison and empty results.
    const nullResult = Predicate.compare(null, "=", 10);
    if (nullResult !== null) {
        throw new Error("SQL NULL comparison failed.");
    }

    const emptyRequest = new QueryRequest({
        table: "employees",
        columns: ["id"],
        predicate: {
            type: "COMPARE",
            column: "salary",
            operator: ">",
            value: 1000000
        }
    });

    const empty = await engine.execute(emptyRequest);

    if (empty.rows.length !== 0) {
        throw new Error("Empty-result test failed.");
    }

    // Validate invalid columns.
    try {
        await engine.execute(new QueryRequest({
            table: "employees",
            columns: ["password"]
        }));

        throw new Error("Invalid-column validation failed.");
    } catch (error) {
        if (!(error instanceof QueryError)) throw error;
    }

    console.log("\nAll execution tests passed.");
}


main().catch(error => {
    console.error("Execution failure:", error.message);
    process.exitCode = 1;
});
