"use strict";

/*
 * Composite Index Workload Analyzer
 *
 * Runtime: Node.js 18+
 *
 * Implements:
 * - Composite B-tree index models.
 * - Column ordering analysis.
 * - Equality/range predicate evaluation.
 * - Selectivity estimation.
 * - Query workload weighting.
 * - Index recommendation and redundancy analysis.
 * - Asynchronous workload evaluation.
 * - Event-driven index maintenance tracking.
 */

const { EventEmitter } = require("node:events");
const crypto = require("node:crypto");

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

const PredicateKind = Object.freeze({
    EQUALITY: "equality",
    RANGE: "range",
    ORDER: "order"
});

class Column {
    constructor(name, distinctValues, rowCount, options = {}) {
        if (!name || typeof name !== "string") {
            throw new ValidationError("Invalid column name.");
        }

        if (!Number.isInteger(distinctValues) ||
            !Number.isInteger(rowCount) ||
            distinctValues < 1 ||
            rowCount < distinctValues) {
            throw new ValidationError("Invalid column statistics.");
        }

        this.name = name;
        this.distinctValues = distinctValues;
        this.rowCount = rowCount;
        this.nullFraction = options.nullFraction ?? 0;
    }

    get equalitySelectivity() {
        return (1 - this.nullFraction) / this.distinctValues;
    }
}

class CompositeIndex {
    constructor(name, columns, options = {}) {
        if (!name || !Array.isArray(columns) || columns.length === 0) {
            throw new ValidationError("Index requires a name and columns.");
        }

        if (new Set(columns).size !== columns.length) {
            throw new ValidationError("Duplicate index columns.");
        }

        this.name = name;
        this.columns = Object.freeze([...columns]);
        this.unique = Boolean(options.unique);
        this.active = options.active ?? true;
    }

    supportsPrefix(columns) {
        if (columns.length > this.columns.length) {
            return false;
        }

        return columns.every(
            (column, index) => column === this.columns[index]
        );
    }

    coversColumns(columns) {
        return columns.every(
            column => this.columns.includes(column)
        );
    }
}

class WorkloadQuery {
    constructor({
        name,
        predicates = [],
        ordering = [],
        projection = [],
        frequency = 1
    }) {
        if (!name || !Number.isFinite(frequency) || frequency <= 0) {
            throw new ValidationError("Invalid workload query.");
        }

        this.name = name;
        this.predicates = Object.freeze(predicates.map(p => {
            if (!p.column || !Object.values(PredicateKind).includes(p.kind)) {
                throw new ValidationError("Invalid predicate.");
            }

            if (p.kind === PredicateKind.RANGE &&
                p.fraction !== undefined &&
                (p.fraction <= 0 || p.fraction > 1)) {
                throw new ValidationError("Invalid range fraction.");
            }

            return Object.freeze({ ...p });
        }));

        this.ordering = Object.freeze([...ordering]);
        this.projection = Object.freeze([...projection]);
        this.frequency = frequency;
    }
}

class IndexAdvisor {
    constructor(columns) {
        this.columns = new Map();

        for (const column of columns) {
            if (this.columns.has(column.name)) {
                throw new ValidationError("Duplicate column metadata.");
            }

            this.columns.set(column.name, column);
        }
    }

    validateColumns(names) {
        for (const name of names) {
            if (!this.columns.has(name)) {
                throw new ValidationError(`Unknown column: ${name}`);
            }
        }
    }

    estimateSelectivity(query) {
        let fraction = 1;

        for (const predicate of query.predicates) {
            const column = this.columns.get(predicate.column);

            if (!column) {
                throw new ValidationError(
                    `Unknown column: ${predicate.column}`
                );
            }

            if (predicate.kind === PredicateKind.EQUALITY) {
                fraction *= column.equalitySelectivity;
            } else if (predicate.kind === PredicateKind.RANGE) {
                fraction *= predicate.fraction ?? 0.25;
            }
        }

        return Math.max(fraction, 1 / Math.max(
            ...Array.from(this.columns.values(), c => c.rowCount)
        ));
    }

    evaluate(index, query) {
        this.validateColumns(index.columns);

        let prefixLength = 0;
        let encounteredRange = false;

        const predicates = new Map();

        for (const predicate of query.predicates) {
            const existing = predicates.get(predicate.column) ?? new Set();
            existing.add(predicate.kind);
            predicates.set(predicate.column, existing);
        }

        for (const column of index.columns) {
            const kinds = predicates.get(column);

            if (!kinds) break;

            if (kinds.has(PredicateKind.EQUALITY) && !encounteredRange) {
                prefixLength++;
                continue;
            }

            if (kinds.has(PredicateKind.RANGE) && !encounteredRange) {
                prefixLength++;
                encounteredRange = true;
                break;
            }

            break;
        }

        const orderingCovered = query.ordering.length > 0 &&
            query.ordering.every(
                (column, indexPosition) =>
                    index.columns[indexPosition] === column
            );

        const coveringColumns = new Set([
            ...query.predicates.map(p => p.column),
            ...query.projection,
            ...query.ordering
        ]);

        return {
            index: index.name,
            query: query.name,
            prefixLength,
            selectivity: this.estimateSelectivity(query),
            orderingCovered,
            coveringCandidate: index.coversColumns(
                [...coveringColumns]
            ),
            usable: prefixLength > 0
        };
    }

    rank(query, indexes) {
        return indexes
            .filter(index => index.active)
            .map(index => this.evaluate(index, query))
            .sort((a, b) => {
                const scoreA =
                    a.prefixLength * 10 +
                    Number(a.orderingCovered) * 4 +
                    Number(a.coveringCandidate) * 2;

                const scoreB =
                    b.prefixLength * 10 +
                    Number(b.orderingCovered) * 4 +
                    Number(b.coveringCandidate) * 2;

                return scoreB - scoreA;
            });
    }

    suggestOrder(query) {
        const equality = new Set(
            query.predicates
                .filter(p => p.kind === PredicateKind.EQUALITY)
                .map(p => p.column)
        );

        const ranges = new Set(
            query.predicates
                .filter(p => p.kind === PredicateKind.RANGE)
                .map(p => p.column)
        );

        this.validateColumns([...equality, ...ranges, ...query.ordering]);

        const equalityOrder = [...equality].sort(
            (a, b) =>
                this.columns.get(b).distinctValues -
                this.columns.get(a).distinctValues
        );

        const result = [...equalityOrder];

        for (const column of [...ranges, ...query.ordering]) {
            if (!result.includes(column)) result.push(column);
        }

        return result;
    }

    findRedundant(indexes) {
        const redundant = [];

        for (const candidate of indexes) {
            const parent = indexes.find(other =>
                other.name !== candidate.name &&
                other.active &&
                other.columns.length >= candidate.columns.length &&
                candidate.supportsPrefix(other.columns.slice(
                    0, candidate.columns.length
                ))
            );

            if (parent) {
                redundant.push({
                    index: candidate.name,
                    possibleReplacement: parent.name
                });
            }
        }

        return redundant;
    }

    workloadReport(queries, indexes) {
        return queries.map(query => ({
            query: query.name,
            frequency: query.frequency,
            estimatedSelectivity: this.estimateSelectivity(query),
            candidates: this.rank(query, indexes)
        }));
    }
}

class IndexMaintenanceMonitor extends EventEmitter {
    constructor() {
        super();
        this.events = [];
    }

    record(operation, indexName, durationMs) {
        if (!["INSERT", "UPDATE", "DELETE", "REINDEX"].includes(operation)) {
            throw new ValidationError("Unsupported operation.");
        }

        if (!indexName || !Number.isFinite(durationMs) || durationMs < 0) {
            throw new ValidationError("Invalid maintenance event.");
        }

        const event = Object.freeze({
            id: crypto.randomUUID(),
            operation,
            indexName,
            durationMs,
            timestamp: new Date().toISOString()
        });

        this.events.push(event);
        this.emit("maintenance", event);

        return event;
    }

    report() {
        const summary = new Map();

        for (const event of this.events) {
            const entry = summary.get(event.indexName) ?? {
                indexName: event.indexName,
                operations: 0,
                totalDurationMs: 0
            };

            entry.operations++;
            entry.totalDurationMs += event.durationMs;
            summary.set(event.indexName, entry);
        }

        return [...summary.values()].map(item => ({
            ...item,
            averageDurationMs:
                item.totalDurationMs / item.operations
        }));
    }
}

async function evaluateWorkload(advisor, queries, indexes) {
    const results = [];

    // Independent query evaluations can run concurrently.
    await Promise.all(
        queries.map(async query => {
            await Promise.resolve();

            results.push({
                query: query.name,
                ranking: advisor.rank(query, indexes)
            });
        })
    );

    return results.sort(
        (a, b) => a.query.localeCompare(b.query)
    );
}

async function main() {
    const columns = [
        new Column("customer_id", 10000, 1000000),
        new Column("status", 5, 1000000),
        new Column("region", 4, 1000000),
        new Column("created_at", 900000, 1000000),
        new Column("total_amount", 500000, 1000000),
        new Column("payment_method", 6, 1000000)
    ];

    const advisor = new IndexAdvisor(columns);

    const indexes = [
        new CompositeIndex(
            "idx_customer_status_date",
            ["customer_id", "status", "created_at"]
        ),
        new CompositeIndex(
            "idx_status_date",
            ["status", "created_at"]
        ),
        new CompositeIndex(
            "idx_region_amount",
            ["region", "total_amount"]
        ),
        new CompositeIndex(
            "idx_status_customer_date",
            ["status", "customer_id", "created_at"]
        )
    ];

    const queries = [
        new WorkloadQuery({
            name: "Customer order history",
            predicates: [
                { column: "customer_id", kind: "equality" },
                { column: "status", kind: "equality" },
                { column: "created_at", kind: "range", fraction: 0.2 }
            ],
            ordering: ["created_at"],
            projection: ["total_amount"],
            frequency: 150
        }),

        new WorkloadQuery({
            name: "Recent paid orders",
            predicates: [
                { column: "status", kind: "equality" },
                { column: "created_at", kind: "range", fraction: 0.1 }
            ],
            ordering: ["created_at"],
            projection: ["customer_id"],
            frequency: 300
        }),

        new WorkloadQuery({
            name: "Regional sales",
            predicates: [
                { column: "region", kind: "equality" },
                { column: "total_amount", kind: "range", fraction: 0.15 }
            ],
            frequency: 40
        }),

        new WorkloadQuery({
            name: "Payment method analysis",
            predicates: [
                { column: "payment_method", kind: "equality" }
            ],
            frequency: 10
        })
    ];

    console.log("\nCOMPOSITE INDEX WORKLOAD ANALYSIS");
    console.log("=".repeat(55));

    const reports = await evaluateWorkload(
        advisor,
        queries,
        indexes
    );

    for (const report of reports) {
        console.log(`\nQuery: ${report.query}`);

        for (const candidate of report.ranking) {
            console.log({
                index: candidate.index,
                prefixLength: candidate.prefixLength,
                selectivity: candidate.selectivity.toFixed(6),
                orderingCovered: candidate.orderingCovered,
                coveringCandidate: candidate.coveringCandidate
            });
        }
    }

    console.log("\nSUGGESTED COLUMN ORDER");

    console.log(
        advisor.suggestOrder(queries[0])
    );

    console.log("\nREDUNDANCY ANALYSIS");

    console.log(advisor.findRedundant(indexes));

    console.log("\nINDEX MAINTENANCE EVENTS");

    const monitor = new IndexMaintenanceMonitor();

    monitor.on("maintenance", event => {
        console.log(
            `${event.operation}: ${event.indexName}, ` +
            `${event.durationMs} ms`
        );
    });

    monitor.record(
        "INSERT",
        "idx_customer_status_date",
        2.4
    );

    monitor.record(
        "UPDATE",
        "idx_status_date",
        1.8
    );

    console.log(monitor.report());

    console.log("\nINVALID QUERY TEST");

    try {
        advisor.validateColumns(["unknown_column"]);
    } catch (error) {
        console.log(`${error.name}: ${error.message}`);
    }

    console.log("\nANALYSIS COMPLETE");
}

main().catch(error => {
    console.error("Workload analysis failed:", error.message);
    process.exitCode = 1;
});
