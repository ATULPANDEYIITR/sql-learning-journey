"use strict";

/*
 * Set Operations in JavaScript
 *
 * JavaScript has Set for distinct membership, but it does not provide SQL's
 * UNION, INTERSECT, and EXCEPT as built-in methods. The functions below make
 * the semantics explicit while retaining JavaScript-specific patterns such as
 * event-driven processing, iterators, Maps, async functions, and validation.
 */

const heading = (title) => {
    console.log(`\n${"=".repeat(72)}\n${title}\n${"=".repeat(72)}`);
};

const sorted = (set) => [...set].sort();

function union(left, right) {
    return new Set([...left, ...right]);
}

function intersect(left, right) {
    const result = new Set();

    for (const value of left) {
        if (right.has(value)) {
            result.add(value);
        }
    }

    return result;
}

function except(left, right) {
    const result = new Set();

    for (const value of left) {
        if (!right.has(value)) {
            result.add(value);
        }
    }

    return result;
}

function unionAll(left, right) {
    // Unlike Set-based UNION, this intentionally preserves duplicate rows.
    return [...left, ...right];
}

function normalizeEmail(value) {
    if (typeof value !== "string") {
        throw new TypeError("Email must be a string");
    }

    const email = value.trim().toLowerCase();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        throw new Error(`Invalid email: ${value}`);
    }

    return email;
}

function toEmailSet(values) {
    const result = new Set();

    for (const value of values) {
        result.add(normalizeEmail(value));
    }

    return result;
}

function demonstrateCoreOperations() {
    heading("Core Set operations");

    const engineering = new Set([
        "alice@example.com",
        "bob@example.com",
        "carol@example.com"
    ]);

    const security = new Set([
        "carol@example.com",
        "david@example.com",
        "erin@example.com"
    ]);

    console.log("UNION:", sorted(union(engineering, security)));
    console.log("INTERSECT:", sorted(intersect(engineering, security)));
    console.log("EXCEPT:", sorted(except(engineering, security)));
    console.log("Reverse EXCEPT:", sorted(except(security, engineering)));
}

function demonstrateUnionAll() {
    heading("UNION versus UNION ALL");

    const first = [
        "alice@example.com",
        "alice@example.com",
        "bob@example.com"
    ];

    const second = [
        "bob@example.com",
        "carol@example.com"
    ];

    console.log("UNION:", [...new Set([...first, ...second])]);
    console.log("UNION ALL:", unionAll(first, second));
}

function demonstrateObjectProjection() {
    heading("Set operations on object data");

    const records = [
        { email: "alice@example.com", source: "crm" },
        { email: "bob@example.com", source: "crm" },
        { email: "bob@example.com", source: "mobile" }
    ];

    // JavaScript Set compares objects by identity, not by their field values.
    // For relational-style distinctness, project the actual comparison key.
    const emailSet = new Set(records.map((record) => record.email));

    console.log("Distinct email projection:", sorted(emailSet));
    console.log(
        "Object identity comparison:",
        new Set(records).size,
        "objects remain because each object has a distinct identity."
    );
}

class AudienceEngine {
    constructor() {
        this.sources = new Map();
    }

    registerSource(name, emails) {
        if (!name || this.sources.has(name)) {
            throw new Error(`Source name is missing or already exists: ${name}`);
        }

        this.sources.set(name, toEmailSet(emails));
    }

    source(name) {
        const value = this.sources.get(name);

        if (!value) {
            throw new Error(`Unknown audience source: ${name}`);
        }

        return value;
    }

    allAudience() {
        return union(...this.sources.values());
    }

    commonAudience() {
        const sets = [...this.sources.values()];

        if (sets.length === 0) {
            return new Set();
        }

        return sets.reduce((result, current) => intersect(result, current));
    }

    exclusiveTo(sourceName) {
        const target = this.source(sourceName);
        const otherSets = [...this.sources.entries()]
            .filter(([name]) => name !== sourceName)
            .map(([, values]) => values);

        if (otherSets.length === 0) {
            return new Set(target);
        }

        const allOthers = otherSets.reduce(
            (result, current) => union(result, current),
            new Set()
        );

        return except(target, allOthers);
    }

    coverage() {
        const counts = new Map();

        for (const values of this.sources.values()) {
            for (const email of values) {
                counts.set(email, (counts.get(email) ?? 0) + 1);
            }
        }

        return counts;
    }
}

function demonstrateAudienceEngine() {
    heading("Multi-source audience reconciliation");

    const engine = new AudienceEngine();

    engine.registerSource("crm", [
        "alice@example.com",
        "bob@example.com",
        "carol@example.com",
        "david@example.com"
    ]);

    engine.registerSource("product", [
        "bob@example.com",
        "carol@example.com",
        "erin@example.com"
    ]);

    engine.registerSource("support", [
        "carol@example.com",
        "david@example.com",
        "frank@example.com"
    ]);

    console.log("All audience:", sorted(engine.allAudience()));
    console.log("Present in every source:", sorted(engine.commonAudience()));
    console.log("CRM-only:", sorted(engine.exclusiveTo("crm")));

    const coverage = [...engine.coverage().entries()]
        .sort(([a], [b]) => a.localeCompare(b));

    console.log("Source coverage:");
    for (const [email, count] of coverage) {
        console.log(`  ${email}: ${count}`);
    }
}

class SetWorkflow extends EventTarget {
    constructor(engine) {
        super();
        this.engine = engine;
    }

    run() {
        const detail = {
            audience: this.engine.allAudience(),
            common: this.engine.commonAudience()
        };

        this.dispatchEvent(new CustomEvent("audienceComputed", { detail }));
    }
}

async function demonstrateEventDrivenProcessing() {
    heading("Event-driven set processing");

    const engine = new AudienceEngine();

    engine.registerSource("marketing", [
        "alice@example.com",
        "bob@example.com",
        "carol@example.com"
    ]);

    engine.registerSource("sales", [
        "bob@example.com",
        "carol@example.com",
        "david@example.com"
    ]);

    const workflow = new SetWorkflow(engine);

    workflow.addEventListener("audienceComputed", (event) => {
        console.log("Event received.");
        console.log("Combined audience:", sorted(event.detail.audience));
        console.log("Shared audience:", sorted(event.detail.common));
    });

    await Promise.resolve();
    workflow.run();
}

function demonstrateValidation() {
    heading("Validation and failure handling");

    const input = [
        " Alice@example.com ",
        "BOB@example.com",
        "not-an-email",
        "alice@example.com"
    ];

    const valid = new Set();
    const rejected = [];

    for (const value of input) {
        try {
            valid.add(normalizeEmail(value));
        } catch (error) {
            rejected.push({
                value,
                reason: error.message
            });
        }
    }

    console.log("Valid distinct values:", sorted(valid));
    console.log("Rejected values:", rejected);
}

function demonstratePerformance() {
    heading("Performance characteristics");

    const left = new Set();
    const right = new Set();

    for (let i = 0; i < 20000; i++) {
        left.add(`user${i}@example.com`);
    }

    for (let i = 10000; i < 30000; i++) {
        right.add(`user${i}@example.com`);
    }

    console.log("UNION size:", union(left, right).size);
    console.log("INTERSECT size:", intersect(left, right).size);
    console.log("EXCEPT size:", except(left, right).size);
    console.log(
        "Set membership is expected O(1), making these hash-based operations "
        + "well suited to distinct membership comparisons."
    );
}

async function main() {
    demonstrateCoreOperations();
    demonstrateUnionAll();
    demonstrateObjectProjection();
    demonstrateAudienceEngine();
    demonstrateValidation();
    demonstratePerformance();
    await demonstrateEventDrivenProcessing();
}

main().catch((error) => {
    console.error("Workflow failed:", error.message);
    process.exitCode = 1;
});
