"use strict";

/*
 * FIRST_VALUE and LAST_VALUE with explicit window-frame semantics.
 *
 * This Node.js implementation uses Maps, immutable-style objects,
 * validation, asynchronous processing, and event-driven reporting.
 */

const { EventEmitter } = require("node:events");

class Observation {
    constructor(repository, observedAt, metric, value) {
        if (!repository || !repository.trim()) {
            throw new TypeError("Repository is required.");
        }
        if (!metric || !metric.trim()) {
            throw new TypeError("Metric is required.");
        }
        if (!(observedAt instanceof Date) || Number.isNaN(observedAt.getTime())) {
            throw new TypeError("A valid observation date is required.");
        }
        if (!Number.isInteger(value) || value < 0) {
            throw new RangeError("Observation value must be a non-negative integer.");
        }

        this.repository = repository;
        this.observedAt = new Date(observedAt.getTime());
        this.metric = metric;
        this.value = value;

        Object.freeze(this);
    }
}

function validateAndSort(observations) {
    if (!Array.isArray(observations) || observations.length === 0) {
        throw new TypeError("At least one observation is required.");
    }

    return [...observations].sort((a, b) => {
        const repositoryOrder = a.repository.localeCompare(b.repository);
        if (repositoryOrder !== 0) return repositoryOrder;
        return a.observedAt - b.observedAt;
    });
}

function groupByRepository(observations) {
    const groups = new Map();

    for (const observation of observations) {
        if (!groups.has(observation.repository)) {
            groups.set(observation.repository, []);
        }
        groups.get(observation.repository).push(observation);
    }

    return groups;
}

function firstValue(observations) {
    const groups = groupByRepository(observations);
    const result = [];

    for (const [repository, rows] of groups) {
        const first = rows[0].value;

        for (const row of rows) {
            result.push({
                repository,
                observedAt: row.observedAt.toISOString(),
                value: row.value,
                firstValue: first
            });
        }
    }

    return result;
}

function lastValueDefaultFrame(observations) {
    /*
     * The ordered default frame ends at the current row.
     * Therefore LAST_VALUE is the current row's value in this model.
     */
    return observations.map(row => ({
        repository: row.repository,
        observedAt: row.observedAt.toISOString(),
        value: row.value,
        lastValueDefaultFrame: row.value
    }));
}

function lastValueFullPartition(observations) {
    const groups = groupByRepository(observations);
    const result = [];

    for (const [repository, rows] of groups) {
        const finalValue = rows.at(-1).value;

        for (const row of rows) {
            result.push({
                repository,
                observedAt: row.observedAt.toISOString(),
                value: row.value,
                lastValueFullPartition: finalValue
            });
        }
    }

    return result;
}

function lastValueInFrame(observations, precedingRows) {
    if (!Number.isInteger(precedingRows) || precedingRows < 0) {
        throw new RangeError("precedingRows must be a non-negative integer.");
    }

    const groups = groupByRepository(observations);
    const result = [];

    for (const [repository, rows] of groups) {
        rows.forEach((row, index) => {
            const start = Math.max(0, index - precedingRows);
            const frame = rows.slice(start, index + 1);

            result.push({
                repository,
                observedAt: row.observedAt.toISOString(),
                value: row.value,
                frameFirst: frame[0].value,
                frameLast: frame.at(-1).value
            });
        });
    }

    return result;
}

class WorkflowReporter extends EventEmitter {
    constructor() {
        super();
        this.on("report", report => {
            console.log(`\n${report.title}`);
            console.log("-".repeat(report.title.length));

            for (const row of report.rows) {
                console.log(JSON.stringify(row));
            }
        });

        this.on("error", error => {
            console.error(`Workflow error: ${error.message}`);
        });
    }

    async publish(title, rows) {
        await Promise.resolve();
        this.emit("report", { title, rows });
    }
}

async function main() {
    const base = new Date("2026-10-01T09:00:00Z");

    const observations = [
        new Observation("payment-api", new Date(base.getTime()), "deployments", 4),
        new Observation("payment-api", new Date(base.getTime() + 7200000), "deployments", 7),
        new Observation("payment-api", new Date(base.getTime() + 14400000), "deployments", 11),
        new Observation("search-api", new Date(base.getTime()), "deployments", 3),
        new Observation("search-api", new Date(base.getTime() + 7200000), "deployments", 6),
        new Observation("search-api", new Date(base.getTime() + 14400000), "deployments", 5)
    ];

    const sorted = validateAndSort(observations);
    const reporter = new WorkflowReporter();

    await reporter.publish("FIRST_VALUE", firstValue(sorted));
    await reporter.publish(
        "LAST_VALUE WITH CURRENT-ROW FRAME",
        lastValueDefaultFrame(sorted)
    );
    await reporter.publish(
        "LAST_VALUE OVER FULL PARTITION",
        lastValueFullPartition(sorted)
    );
    await reporter.publish(
        "LAST_VALUE OVER TWO-PRECEDING ROWS",
        lastValueInFrame(sorted, 2)
    );

    const first = firstValue(sorted);
    const full = lastValueFullPartition(sorted);

    if (first[0].firstValue !== 4 || first[3].firstValue !== 3) {
        throw new Error("FIRST_VALUE validation failed.");
    }

    if (full[0].lastValueFullPartition !== 11 ||
        full[3].lastValueFullPartition !== 5) {
        throw new Error("Full-partition LAST_VALUE validation failed.");
    }

    console.log("\nValidation checks passed.");
    console.log("Complexity: O(n log n) including ordering; O(n) window evaluation.");
    console.log("Security: no dynamic code execution, shell execution, or external dependencies.");
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
