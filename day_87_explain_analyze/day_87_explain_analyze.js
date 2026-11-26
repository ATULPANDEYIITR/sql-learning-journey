"use strict";

/*
 * EXPLAIN ANALYZE: Event-driven PostgreSQL execution plan verification.
 *
 * Capabilities:
 * - JSON execution-plan parsing
 * - Actual execution time and row analysis
 * - Loop-aware statistics
 * - Cardinality estimation diagnostics
 * - Buffer analysis
 * - Policy-based plan verification
 * - Repeated benchmark aggregation
 * - Asynchronous plan processing
 *
 * Runtime: Node.js 18+
 * Dependencies: Node.js standard library only.
 */

const { EventEmitter } = require("node:events");
const { readFile } = require("node:fs/promises");

class PlanValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "PlanValidationError";
    }
}

class PerformancePolicy {
    constructor({
        maxExecutionTimeMs = 100,
        maxPlanningTimeMs = 50,
        maxRowEstimationRatio = 20,
        maxNodeTimeMs = 50,
        requireActualRows = true
    } = {}) {
        const values = [
            maxExecutionTimeMs,
            maxPlanningTimeMs,
            maxRowEstimationRatio,
            maxNodeTimeMs
        ];

        if (values.some(
            value => !Number.isFinite(value) || value < 0
        )) {
            throw new RangeError("Policy thresholds must be non-negative");
        }

        if (maxRowEstimationRatio < 1) {
            throw new RangeError("Row estimation ratio must be at least 1");
        }

        this.maxExecutionTimeMs = maxExecutionTimeMs;
        this.maxPlanningTimeMs = maxPlanningTimeMs;
        this.maxRowEstimationRatio = maxRowEstimationRatio;
        this.maxNodeTimeMs = maxNodeTimeMs;
        this.requireActualRows = requireActualRows;

        Object.freeze(this);
    }
}

class ExecutionNode {
    constructor(raw, depth = 0) {
        if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
            throw new PlanValidationError("Invalid execution plan node");
        }

        if (typeof raw["Node Type"] !== "string") {
            throw new PlanValidationError("Node Type is required");
        }

        this.type = raw["Node Type"];
        this.relation = raw["Relation Name"] ?? null;
        this.index = raw["Index Name"] ?? null;
        this.depth = depth;

        this.estimatedRows = ExecutionNode.number(
            raw["Plan Rows"] ?? 0,
            "Plan Rows"
        );

        this.actualRows = ExecutionNode.number(
            raw["Actual Rows"] ?? 0,
            "Actual Rows"
        );

        this.loops = raw["Actual Loops"] ?? 0;

        if (
            !Number.isInteger(this.loops) ||
            this.loops < 0
        ) {
            throw new PlanValidationError("Invalid Actual Loops");
        }

        this.totalCost = ExecutionNode.number(
            raw["Total Cost"] ?? 0,
            "Total Cost"
        );

        this.actualStartupTime = ExecutionNode.number(
            raw["Actual Startup Time"] ?? 0,
            "Actual Startup Time"
        );

        this.actualTotalTime = ExecutionNode.number(
            raw["Actual Total Time"] ?? 0,
            "Actual Total Time"
        );

        this.sharedHitBlocks = ExecutionNode.number(
            raw["Shared Hit Blocks"] ?? 0,
            "Shared Hit Blocks"
        );

        this.sharedReadBlocks = ExecutionNode.number(
            raw["Shared Read Blocks"] ?? 0,
            "Shared Read Blocks"
        );

        const plans = raw.Plans ?? [];

        if (!Array.isArray(plans)) {
            throw new PlanValidationError("Plans must be an array");
        }

        this.children = plans.map(
            child => new ExecutionNode(child, depth + 1)
        );

        Object.freeze(this.children);
        Object.freeze(this);
    }

    static number(value, field) {
        if (
            typeof value !== "number" ||
            !Number.isFinite(value) ||
            value < 0
        ) {
            throw new PlanValidationError(`Invalid ${field}`);
        }

        return value;
    }

    get totalRowsAcrossLoops() {
        return this.actualRows * this.loops;
    }

    get accumulatedNodeTimeMs() {
        return this.actualTotalTime * this.loops;
    }

    get estimationRatio() {
        if (this.estimatedRows === 0) {
            return this.actualRows === 0 ? 1 : Infinity;
        }

        return Math.max(
            this.actualRows / this.estimatedRows,
            this.estimatedRows / Math.max(this.actualRows, 0.000001)
        );
    }
}

class ExecutionPlan {
    constructor(document) {
        let data;

        try {
            data = typeof document === "string"
                ? JSON.parse(document)
                : document;
        } catch (error) {
            throw new PlanValidationError(
                `Invalid JSON: ${error.message}`
            );
        }

        if (!Array.isArray(data) || data.length === 0) {
            throw new PlanValidationError(
                "Expected a non-empty PostgreSQL JSON plan"
            );
        }

        const entry = data[0];

        if (!entry || !entry.Plan) {
            throw new PlanValidationError("Missing root Plan");
        }

        this.planningTimeMs = ExecutionNode.number(
            entry["Planning Time"] ?? 0,
            "Planning Time"
        );

        this.executionTimeMs = ExecutionNode.number(
            entry["Execution Time"] ?? 0,
            "Execution Time"
        );

        this.root = new ExecutionNode(entry.Plan);
        Object.freeze(this);
    }

    nodes() {
        const result = [];
        const stack = [this.root];

        while (stack.length) {
            const node = stack.pop();
            result.push(node);

            for (let i = node.children.length - 1; i >= 0; i--) {
                stack.push(node.children[i]);
            }
        }

        return result;
    }
}

class PlanVerifier extends EventEmitter {
    constructor(policy = new PerformancePolicy()) {
        super();
        this.policy = policy;
    }

    evaluate(plan) {
        const failures = [];
        const warnings = [];

        if (
            plan.executionTimeMs >
            this.policy.maxExecutionTimeMs
        ) {
            failures.push("Execution time exceeded policy.");
        }

        if (
            plan.planningTimeMs >
            this.policy.maxPlanningTimeMs
        ) {
            warnings.push("Planning time exceeded policy.");
        }

        for (const node of plan.nodes()) {
            if (
                this.policy.requireActualRows &&
                node.loops === 0
            ) {
                warnings.push(
                    `${node.type}: node was never executed.`
                );
            }

            if (
                node.estimationRatio >
                this.policy.maxRowEstimationRatio
            ) {
                warnings.push(
                    `${node.type}: significant row estimation error.`
                );
            }

            if (
                node.accumulatedNodeTimeMs >
                this.policy.maxNodeTimeMs
            ) {
                warnings.push(
                    `${node.type}: high accumulated node time.`
                );
            }

            if (node.sharedReadBlocks > 0) {
                this.emit("diskRead", {
                    node: node.type,
                    blocks: node.sharedReadBlocks
                });
            }
        }

        const result = Object.freeze({
            passed: failures.length === 0,
            failures: Object.freeze(failures),
            warnings: Object.freeze(warnings),
            executionTimeMs: plan.executionTimeMs,
            planningTimeMs: plan.planningTimeMs
        });

        this.emit("evaluated", result);
        return result;
    }

    async evaluateFile(filePath) {
        // Read the entire file asynchronously. The path must be supplied
        // by a trusted caller, not constructed from untrusted input.
        const document = await readFile(filePath, "utf8");
        const plan = new ExecutionPlan(document);
        return this.evaluate(plan);
    }
}

class BenchmarkCollector {
    #measurements = [];

    record(value) {
        if (
            typeof value !== "number" ||
            !Number.isFinite(value) ||
            value < 0
        ) {
            throw new RangeError("Invalid benchmark measurement");
        }

        this.#measurements.push(value);
    }

    report() {
        if (!this.#measurements.length) {
            throw new Error("No measurements available");
        }

        const sorted = [...this.#measurements].sort(
            (a, b) => a - b
        );

        const middle = Math.floor(sorted.length / 2);

        const median = sorted.length % 2
            ? sorted[middle]
            : (sorted[middle - 1] + sorted[middle]) / 2;

        const average = sorted.reduce(
            (sum, value) => sum + value,
            0
        ) / sorted.length;

        return Object.freeze({
            runs: sorted.length,
            minimumMs: sorted[0],
            maximumMs: sorted.at(-1),
            medianMs: median,
            averageMs: average
        });
    }
}

function createDemonstrationPlan() {
    return [
        {
            "Plan": {
                "Node Type": "Hash Join",
                "Plan Rows": 100,
                "Actual Rows": 100,
                "Actual Loops": 1,
                "Total Cost": 120,
                "Actual Startup Time": 0.1,
                "Actual Total Time": 4.5,
                "Shared Hit Blocks": 35,
                "Shared Read Blocks": 2,
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "customers",
                        "Plan Rows": 100,
                        "Actual Rows": 100,
                        "Actual Loops": 1,
                        "Total Cost": 20,
                        "Actual Startup Time": 0.01,
                        "Actual Total Time": 0.4
                    },
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "orders",
                        "Index Name": "orders_customer_id_idx",
                        "Plan Rows": 100,
                        "Actual Rows": 100,
                        "Actual Loops": 1,
                        "Total Cost": 80,
                        "Actual Startup Time": 0.02,
                        "Actual Total Time": 2.1
                    }
                ]
            },
            "Planning Time": 0.6,
            "Execution Time": 4.9
        }
    ];
}

async function main() {
    const verifier = new PlanVerifier(
        new PerformancePolicy({
            maxExecutionTimeMs: 50,
            maxPlanningTimeMs: 10,
            maxRowEstimationRatio: 10,
            maxNodeTimeMs: 30
        })
    );

    verifier.on("evaluated", result => {
        console.log("\nPLAN EVALUATION EVENT");
        console.log(result);
    });

    verifier.on("diskRead", event => {
        console.log(
            `Disk read: ${event.blocks} blocks in ${event.node}`
        );
    });

    const plan = new ExecutionPlan(createDemonstrationPlan());
    const result = verifier.evaluate(plan);

    console.log("\nEXECUTION PLAN NODES");

    for (const node of plan.nodes()) {
        console.log({
            type: node.type,
            relation: node.relation,
            estimatedRows: node.estimatedRows,
            actualRowsPerLoop: node.actualRows,
            loops: node.loops,
            totalRowsAcrossLoops: node.totalRowsAcrossLoops,
            accumulatedNodeTimeMs: node.accumulatedNodeTimeMs
        });
    }

    console.log("\nQUERY TIMING");
    console.log({
        planningTimeMs: plan.planningTimeMs,
        executionTimeMs: plan.executionTimeMs
    });

    const benchmark = new BenchmarkCollector();

    [4.9, 5.1, 4.7, 4.8, 5.0].forEach(
        value => benchmark.record(value)
    );

    console.log("\nBENCHMARK");
    console.log(benchmark.report());

    console.log("\nMERGE-GATE STYLE PLAN CHECK");
    console.log(result.passed ? "PASS" : "FAIL");

    if (!result.passed) {
        process.exitCode = 1;
    }
}

main().catch(error => {
    console.error("Plan analysis failed:", error.message);
    process.exitCode = 1;
});
