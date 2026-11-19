"use strict";

/*
 * PostgreSQL Index Types: B-tree, Hash, GiST, SP-GiST, GIN, BRIN.
 *
 * Node.js 18+.
 * Uses an event-driven workload analyzer and index policy engine.
 * No external dependencies.
 */

const { EventEmitter } = require("node:events");
const { performance } = require("node:perf_hooks");

const IndexType = Object.freeze({
    BTREE: "B-tree",
    HASH: "Hash",
    GIST: "GiST",
    SPGIST: "SP-GiST",
    GIN: "GIN",
    BRIN: "BRIN"
});

const Pattern = Object.freeze({
    EQUALITY: "equality",
    RANGE: "range",
    ORDERING: "ordering",
    ARRAY: "array_membership",
    CONTAINS: "contains",
    SPATIAL: "spatial",
    PREFIX: "prefix",
    FULLTEXT: "full_text",
    LARGE_RANGE: "large_table_range"
});

const CAPABILITIES = new Map([
    [IndexType.BTREE, {
        patterns: new Set([
            Pattern.EQUALITY,
            Pattern.RANGE,
            Pattern.ORDERING,
            Pattern.PREFIX
        ]),
        description: "Ordered balanced search tree",
        maintenance: 0.10
    }],
    [IndexType.HASH, {
        patterns: new Set([Pattern.EQUALITY]),
        description: "Hash-based equality lookup",
        maintenance: 0.08
    }],
    [IndexType.GIST, {
        patterns: new Set([
            Pattern.RANGE,
            Pattern.SPATIAL,
            Pattern.CONTAINS
        ]),
        description: "Generalized Search Tree",
        maintenance: 0.16
    }],
    [IndexType.SPGIST, {
        patterns: new Set([
            Pattern.SPATIAL,
            Pattern.PREFIX,
            Pattern.EQUALITY
        ]),
        description: "Space-partitioned search tree",
        maintenance: 0.12
    }],
    [IndexType.GIN, {
        patterns: new Set([
            Pattern.ARRAY,
            Pattern.CONTAINS,
            Pattern.FULLTEXT
        ]),
        description: "Inverted index of component values",
        maintenance: 0.30
    }],
    [IndexType.BRIN, {
        patterns: new Set([
            Pattern.RANGE,
            Pattern.LARGE_RANGE
        ]),
        description: "Block-range summaries",
        maintenance: 0.02
    }]
]);

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

class Workload {
    constructor({
        id,
        pattern,
        rows,
        selectivity,
        updateRate = 0,
        correlation = 0,
        needsOrdering = false
    }) {
        if (typeof id !== "string" || id.trim() === "") {
            throw new ValidationError("Workload ID is required.");
        }

        if (!Object.values(Pattern).includes(pattern)) {
            throw new ValidationError("Unsupported query pattern.");
        }

        if (!Number.isSafeInteger(rows) || rows <= 0) {
            throw new ValidationError("Rows must be a positive safe integer.");
        }

        for (const [name, value] of [
            ["selectivity", selectivity],
            ["updateRate", updateRate],
            ["correlation", correlation]
        ]) {
            if (!Number.isFinite(value) || value < 0 || value > 1) {
                throw new ValidationError(`${name} must be between 0 and 1.`);
            }
        }

        this.id = id;
        this.pattern = pattern;
        this.rows = rows;
        this.selectivity = selectivity;
        this.updateRate = updateRate;
        this.correlation = correlation;
        this.needsOrdering = Boolean(needsOrdering);

        Object.freeze(this);
    }
}

class IndexPolicyEngine {
    evaluate(workload) {
        const candidates = [];

        for (const [type, capability] of CAPABILITIES) {
            const applicable = capability.patterns.has(workload.pattern);

            if (!applicable) {
                candidates.push({
                    type,
                    score: 0,
                    applicable: false,
                    reasons: ["Unsupported access pattern."]
                });
                continue;
            }

            let score = 50;
            const reasons = ["Operator-class capability matches workload."];

            switch (type) {
                case IndexType.BTREE:
                    score += 15;

                    if (workload.needsOrdering) {
                        score += 20;
                        reasons.push("Supports ordered retrieval.");
                    }

                    if (workload.selectivity < 0.05) {
                        score += 10;
                    }
                    break;

                case IndexType.HASH:
                    score += 12;
                    reasons.push("Suitable for equality comparisons.");
                    break;

                case IndexType.GIST:
                    score += 20;
                    reasons.push("Supports specialized spatial and range operators.");
                    break;

                case IndexType.SPGIST:
                    score += 20;
                    reasons.push("Suitable for partitioned search spaces.");
                    break;

                case IndexType.GIN:
                    score += 25;
                    reasons.push("Supports component-based inverted lookups.");

                    if (workload.updateRate > 0.5) {
                        score -= 20;
                        reasons.push("Frequent updates increase maintenance cost.");
                    }
                    break;

                case IndexType.BRIN:
                    score += 15 + workload.correlation * 30;

                    if (workload.rows >= 1_000_000) {
                        score += 15;
                        reasons.push("Large table benefits from compact summaries.");
                    }

                    if (workload.correlation < 0.4) {
                        score -= 30;
                        reasons.push("Low physical correlation reduces effectiveness.");
                    }
                    break;
            }

            score -= workload.updateRate * 15;
            score = Math.max(0, Math.min(100, score));

            candidates.push({
                type,
                score: Number(score.toFixed(2)),
                applicable: true,
                reasons
            });
        }

        return candidates.sort((a, b) => b.score - a.score);
    }
}

class IndexRegistry {
    #indexes = new Map();

    register(definition) {
        const identifier = /^[a-zA-Z_][a-zA-Z0-9_]*$/;

        for (const key of ["name", "table", "column"]) {
            if (
                typeof definition[key] !== "string" ||
                !identifier.test(definition[key])
            ) {
                throw new ValidationError(`Invalid ${key}.`);
            }
        }

        if (!Object.values(IndexType).includes(definition.type)) {
            throw new ValidationError("Invalid index type.");
        }

        if (this.#indexes.has(definition.name)) {
            throw new ValidationError("Duplicate index name.");
        }

        if (definition.unique && definition.type !== IndexType.BTREE) {
            throw new ValidationError(
                "Unique indexes in this model must use B-tree."
            );
        }

        const record = Object.freeze({ ...definition });
        this.#indexes.set(record.name, record);

        return record;
    }

    get(name) {
        return this.#indexes.get(name) ?? null;
    }

    remove(name) {
        return this.#indexes.delete(name);
    }

    list() {
        return Array.from(this.#indexes.values());
    }

    get size() {
        return this.#indexes.size;
    }
}

class QueryMonitor extends EventEmitter {
    constructor(policyEngine) {
        super();

        this.policyEngine = policyEngine;
        this.metrics = new Map();
    }

    async submit(workload) {
        const started = performance.now();

        // Simulated asynchronous workload evaluation.
        await new Promise(resolve => setImmediate(resolve));

        const recommendations = this.policyEngine.evaluate(workload);
        const elapsed = performance.now() - started;

        const result = {
            workloadId: workload.id,
            recommendations,
            analysisTimeMs: Number(elapsed.toFixed(4))
        };

        const previous = this.metrics.get(workload.id) ?? 0;
        this.metrics.set(workload.id, previous + 1);

        this.emit("evaluated", result);

        return result;
    }

    getMetrics() {
        return Object.fromEntries(this.metrics);
    }
}

class GovernanceService {
    constructor() {
        this.engine = new IndexPolicyEngine();
        this.registry = new IndexRegistry();
        this.monitor = new QueryMonitor(this.engine);

        this.monitor.on("evaluated", result => {
            console.log(
                `EVENT workload=${result.workloadId} ` +
                `analysis=${result.analysisTimeMs}ms`
            );
        });
    }

    async analyze(workload) {
        return this.monitor.submit(workload);
    }

    registerExamples() {
        const definitions = [
            {
                name: "idx_customer_email",
                table: "customers",
                column: "email",
                type: IndexType.BTREE,
                unique: true
            },
            {
                name: "idx_event_payload",
                table: "events",
                column: "payload",
                type: IndexType.GIN,
                operatorClass: "jsonb_path_ops"
            },
            {
                name: "idx_order_timestamp",
                table: "orders",
                column: "created_at",
                type: IndexType.BRIN
            },
            {
                name: "idx_ip_address",
                table: "network_logs",
                column: "client_ip",
                type: IndexType.SPGIST
            }
        ];

        for (const definition of definitions) {
            this.registry.register(definition);
        }
    }
}

function printReport(result) {
    console.log(`\nWorkload: ${result.workloadId}`);

    for (const item of result.recommendations.slice(0, 3)) {
        if (item.applicable) {
            console.log(
                `  ${item.type.padEnd(8)} Score: ${item.score}`
            );

            for (const reason of item.reasons) {
                console.log(`    - ${reason}`);
            }
        }
    }
}

async function runTests(service) {
    const equality = new Workload({
        id: "customer-lookup",
        pattern: Pattern.EQUALITY,
        rows: 500000,
        selectivity: 0.001
    });

    const equalityResult = await service.analyze(equality);

    if (equalityResult.recommendations[0].type !== IndexType.BTREE) {
        throw new Error("Unexpected equality recommendation.");
    }

    const fullText = new Workload({
        id: "document-search",
        pattern: Pattern.FULLTEXT,
        rows: 2000000,
        selectivity: 0.005
    });

    const textResult = await service.analyze(fullText);

    if (textResult.recommendations[0].type !== IndexType.GIN) {
        throw new Error("Unexpected full-text recommendation.");
    }

    const largeRange = new Workload({
        id: "historical-events",
        pattern: Pattern.LARGE_RANGE,
        rows: 10000000,
        selectivity: 0.05,
        correlation: 0.99
    });

    const rangeResult = await service.analyze(largeRange);

    if (rangeResult.recommendations[0].type !== IndexType.BRIN) {
        throw new Error("Unexpected BRIN recommendation.");
    }

    console.log("\nAll automated tests passed.");
}

async function main() {
    console.log("POSTGRESQL INDEX TYPES: EVENT-DRIVEN ANALYZER");
    console.log("=".repeat(65));

    const service = new GovernanceService();

    service.registerExamples();

    const workloads = [
        new Workload({
            id: "customer-email",
            pattern: Pattern.EQUALITY,
            rows: 500000,
            selectivity: 0.001
        }),
        new Workload({
            id: "order-history",
            pattern: Pattern.RANGE,
            rows: 5000000,
            selectivity: 0.02,
            correlation: 0.95
        }),
        new Workload({
            id: "json-containment",
            pattern: Pattern.CONTAINS,
            rows: 1000000,
            selectivity: 0.01,
            updateRate: 0.60
        }),
        new Workload({
            id: "array-tags",
            pattern: Pattern.ARRAY,
            rows: 800000,
            selectivity: 0.05
        }),
        new Workload({
            id: "spatial-lookup",
            pattern: Pattern.SPATIAL,
            rows: 300000,
            selectivity: 0.01
        }),
        new Workload({
            id: "text-search",
            pattern: Pattern.FULLTEXT,
            rows: 2000000,
            selectivity: 0.005
        })
    ];

    for (const workload of workloads) {
        const result = await service.analyze(workload);
        printReport(result);
    }

    await runTests(service);

    console.log("\nREGISTERED INDEXES");

    for (const index of service.registry.list()) {
        console.log(
            `${index.name}: ${index.type} ON ${index.table}(${index.column})`
        );
    }

    console.log("\nWORKLOAD METRICS");
    console.log(JSON.stringify(service.monitor.getMetrics(), null, 2));
}

main().catch(error => {
    console.error("Execution failed:", error.message);
    process.exitCode = 1;
});
