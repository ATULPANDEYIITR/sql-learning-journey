"use strict";

/*
 * SQL EXPLAIN: Execution Plans, Cost Estimates, and Scan Types
 *
 * PostgreSQL JSON execution-plan analyzer.
 *
 * Features:
 * - Sequential, index, index-only and bitmap scans
 * - Nested loop, hash join and merge join analysis
 * - Estimated versus actual rows
 * - Cardinality estimation errors
 * - Startup and total cost analysis
 * - Buffer and I/O diagnostics
 * - Asynchronous file processing
 * - Event-driven plan reporting
 *
 * Runtime: Node.js 18+
 * Dependencies: Node.js standard library only.
 */

const fs = require("node:fs/promises");
const path = require("node:path");
const EventEmitter = require("node:events");

const SAMPLE_PLAN = [
    {
        "Plan": {
            "Node Type": "Hash Join",
            "Startup Cost": 25.50,
            "Total Cost": 180.75,
            "Plan Rows": 250,
            "Plan Width": 48,
            "Actual Startup Time": 0.25,
            "Actual Total Time": 2.85,
            "Actual Rows": 250,
            "Actual Loops": 1,
            "Shared Hit Blocks": 120,
            "Shared Read Blocks": 15,
            "Plans": [
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "departments",
                    "Startup Cost": 0,
                    "Total Cost": 20,
                    "Plan Rows": 4,
                    "Actual Startup Time": 0.01,
                    "Actual Total Time": 0.04,
                    "Actual Rows": 4,
                    "Actual Loops": 1
                },
                {
                    "Node Type": "Bitmap Heap Scan",
                    "Relation Name": "employees",
                    "Startup Cost": 10,
                    "Total Cost": 100,
                    "Plan Rows": 250,
                    "Actual Startup Time": 0.15,
                    "Actual Total Time": 1.50,
                    "Actual Rows": 250,
                    "Actual Loops": 1,
                    "Shared Hit Blocks": 80,
                    "Plans": [
                        {
                            "Node Type": "Bitmap Index Scan",
                            "Index Name": "idx_employees_department",
                            "Startup Cost": 0,
                            "Total Cost": 8,
                            "Plan Rows": 250,
                            "Actual Startup Time": 0.05,
                            "Actual Total Time": 0.20,
                            "Actual Rows": 250,
                            "Actual Loops": 1
                        }
                    ]
                }
            ]
        },
        "Planning Time": 0.45,
        "Execution Time": 3.10
    }
];

const NODE_TYPES = Object.freeze({
    SEQUENTIAL: "Seq Scan",
    INDEX: "Index Scan",
    INDEX_ONLY: "Index Only Scan",
    BITMAP_HEAP: "Bitmap Heap Scan",
    BITMAP_INDEX: "Bitmap Index Scan",
    NESTED_LOOP: "Nested Loop",
    HASH_JOIN: "Hash Join",
    MERGE_JOIN: "Merge Join",
    SORT: "Sort",
    AGGREGATE: "Aggregate"
});

class PlanValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "PlanValidationError";
    }
}

function finiteNumber(value, field, fallback = 0) {
    if (value === undefined || value === null) {
        return fallback;
    }

    if (
        typeof value !== "number" ||
        !Number.isFinite(value) ||
        value < 0
    ) {
        throw new PlanValidationError(
            `Invalid numeric field: ${field}`
        );
    }

    return value;
}

function validateNode(node, depth = 0) {
    if (depth > 100) {
        throw new PlanValidationError(
            "Execution plan exceeds maximum nesting depth."
        );
    }

    if (
        node === null ||
        typeof node !== "object" ||
        Array.isArray(node)
    ) {
        throw new PlanValidationError(
            "Plan node must be an object."
        );
    }

    if (
        typeof node["Node Type"] !== "string" ||
        node["Node Type"].length === 0
    ) {
        throw new PlanValidationError(
            "Every plan node requires a Node Type."
        );
    }

    for (const field of [
        "Startup Cost",
        "Total Cost",
        "Plan Rows",
        "Plan Width",
        "Actual Startup Time",
        "Actual Total Time",
        "Actual Rows",
        "Actual Loops",
        "Shared Hit Blocks",
        "Shared Read Blocks"
    ]) {
        finiteNumber(node[field], field);
    }

    if (
        node["Total Cost"] !== undefined &&
        node["Startup Cost"] !== undefined &&
        node["Total Cost"] < node["Startup Cost"]
    ) {
        throw new PlanValidationError(
            "Total Cost cannot be lower than Startup Cost."
        );
    }

    const children = node.Plans ?? [];

    if (!Array.isArray(children)) {
        throw new PlanValidationError(
            "Plans must be an array."
        );
    }

    for (const child of children) {
        validateNode(child, depth + 1);
    }

    return node;
}

class PlanAnalyzer {

    constructor(planDocument) {
        if (
            !Array.isArray(planDocument) ||
            planDocument.length === 0
        ) {
            throw new PlanValidationError(
                "Expected a non-empty PostgreSQL JSON plan."
            );
        }

        const entry = planDocument[0];

        if (
            !entry ||
            !entry.Plan ||
            typeof entry.Plan !== "object"
        ) {
            throw new PlanValidationError(
                "Missing root Plan object."
            );
        }

        validateNode(entry.Plan);

        this.document = entry;
        this.root = entry.Plan;
        this.nodes = [];
        this.visit(this.root);
    }

    visit(node, depth = 0) {
        this.nodes.push({ node, depth });

        for (const child of node.Plans ?? []) {
            this.visit(child, depth + 1);
        }
    }

    classifyScan(nodeType) {
        const mapping = {
            "Seq Scan": "Sequential Scan",
            "Index Scan": "Index Scan",
            "Index Only Scan": "Index Only Scan",
            "Bitmap Heap Scan": "Bitmap Heap Scan",
            "Bitmap Index Scan": "Bitmap Index Scan"
        };

        return mapping[nodeType] ?? null;
    }

    scanSummary() {
        const counts = new Map();

        for (const { node } of this.nodes) {
            const scan = this.classifyScan(node["Node Type"]);

            if (scan) {
                counts.set(
                    scan,
                    (counts.get(scan) ?? 0) + 1
                );
            }
        }

        return Object.fromEntries(counts);
    }

    estimateErrors() {
        return this.nodes
            .filter(({ node }) =>
                node["Actual Rows"] !== undefined &&
                node["Plan Rows"] !== undefined
            )
            .map(({ node }) => {
                const estimated = node["Plan Rows"];
                const actual = node["Actual Rows"];

                const ratio = Math.max(estimated, actual) /
                    Math.max(1, Math.min(estimated, actual));

                return {
                    nodeType: node["Node Type"],
                    relation: node["Relation Name"] ?? null,
                    estimatedRows: estimated,
                    actualRows: actual,
                    difference: actual - estimated,
                    errorFactor: Number(ratio.toFixed(2)),
                    inaccurate: ratio >= 2
                };
            });
    }

    joinSummary() {
        return this.nodes
            .filter(({ node }) =>
                [
                    NODE_TYPES.NESTED_LOOP,
                    NODE_TYPES.HASH_JOIN,
                    NODE_TYPES.MERGE_JOIN
                ].includes(node["Node Type"])
            )
            .map(({ node }) => ({
                algorithm: node["Node Type"],
                estimatedRows: node["Plan Rows"],
                actualRows: node["Actual Rows"],
                estimatedCost: node["Total Cost"]
            }));
    }

    bufferSummary() {
        return this.nodes.reduce(
            (result, { node }) => {
                result.sharedHits +=
                    node["Shared Hit Blocks"] ?? 0;

                result.sharedReads +=
                    node["Shared Read Blocks"] ?? 0;

                result.tempReads +=
                    node["Temp Read Blocks"] ?? 0;

                result.tempWrites +=
                    node["Temp Written Blocks"] ?? 0;

                return result;
            },
            {
                sharedHits: 0,
                sharedReads: 0,
                tempReads: 0,
                tempWrites: 0
            }
        );
    }

    diagnostics() {
        const findings = [];

        for (const { node } of this.nodes) {
            const type = node["Node Type"];
            const errors = this.estimateErrors();

            const mismatch = errors.find(
                item =>
                    item.nodeType === type &&
                    item.relation === (
                        node["Relation Name"] ?? null
                    ) &&
                    item.inaccurate
            );

            if (mismatch) {
                findings.push({
                    severity: "WARNING",
                    message:
                        `${type}: estimated ${mismatch.estimatedRows} ` +
                        `rows but observed ${mismatch.actualRows}. ` +
                        "Inspect statistics and predicate selectivity."
                });
            }

            if (
                type === "Seq Scan" &&
                node["Plan Rows"] > 1000
            ) {
                findings.push({
                    severity: "INFO",
                    message:
                        `Sequential scan on ${node["Relation Name"] ?? "relation"}. ` +
                        "Evaluate whether a selective indexed predicate exists."
                });
            }

            if (
                node["Node Type"] === "Nested Loop" &&
                (node["Actual Loops"] ?? 0) > 1000
            ) {
                findings.push({
                    severity: "WARNING",
                    message:
                        "High nested-loop iteration count. Inspect inner-side access."
                });
            }

            if (
                (node["Temp Written Blocks"] ?? 0) > 0
            ) {
                findings.push({
                    severity: "WARNING",
                    message:
                        "Temporary disk writes detected. Inspect sorting, hashing, and memory settings."
                });
            }
        }

        return findings;
    }

    report() {
        return {
            rootNode: this.root["Node Type"],
            estimatedTotalCost: this.root["Total Cost"],
            estimatedRows: this.root["Plan Rows"],
            actualRows: this.root["Actual Rows"] ?? null,
            planningTimeMs: this.document["Planning Time"] ?? null,
            executionTimeMs: this.document["Execution Time"] ?? null,
            nodeCount: this.nodes.length,
            scanTypes: this.scanSummary(),
            joins: this.joinSummary(),
            rowEstimation: this.estimateErrors(),
            buffers: this.bufferSummary(),
            diagnostics: this.diagnostics()
        };
    }
}

class PlanMonitor extends EventEmitter {

    constructor() {
        super();
        this.history = [];
    }

    analyze(document) {
        const analyzer = new PlanAnalyzer(document);
        const report = analyzer.report();

        this.history.push(report);

        this.emit("plan:analyzed", report);

        for (const diagnostic of report.diagnostics) {
            this.emit("plan:diagnostic", diagnostic);
        }

        return report;
    }

    getHistory() {
        return [...this.history];
    }
}

async function loadPlan(filePath) {
    const absolutePath = path.resolve(filePath);

    const content = await fs.readFile(
        absolutePath,
        "utf8"
    );

    try {
        return JSON.parse(content);
    } catch {
        throw new PlanValidationError(
            "The supplied file contains invalid JSON."
        );
    }
}

async function main() {
    const monitor = new PlanMonitor();

    monitor.on("plan:analyzed", report => {
        console.log("\nExecution plan analyzed.");
        console.log("Root:", report.rootNode);
        console.log("Estimated cost:", report.estimatedTotalCost);
        console.log("Execution time:", report.executionTimeMs, "ms");
    });

    monitor.on("plan:diagnostic", diagnostic => {
        console.log(
            `[${diagnostic.severity}] ${diagnostic.message}`
        );
    });

    try {
        const inputPath = process.argv[2];

        const plan = inputPath
            ? await loadPlan(inputPath)
            : SAMPLE_PLAN;

        const report = monitor.analyze(plan);

        console.log("\nDetailed report:");
        console.log(JSON.stringify(report, null, 2));

        const outputPath = path.resolve(
            "execution_plan_analysis.json"
        );

        await fs.writeFile(
            outputPath,
            JSON.stringify(report, null, 2),
            { encoding: "utf8", mode: 0o600 }
        );

        console.log("\nReport saved:", outputPath);

        if (monitor.getHistory().length !== 1) {
            throw new Error("Unexpected monitoring history.");
        }

    } catch (error) {
        console.error(
            `${error.name}: ${error.message}`
        );

        process.exitCode = 1;
    }
}

main();
