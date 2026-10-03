"use strict";

/*
 * INNER JOIN — matching rows and join conditions.
 *
 * This Node.js program models relational INNER JOIN behavior with ordinary
 * JavaScript arrays and objects. It deliberately does not depend on an npm
 * package so that the join mechanics remain visible.
 *
 * The implementation progresses from simple equality matching to:
 * - duplicate-key behavior,
 * - custom join predicates,
 * - composite conditions,
 * - post-join filtering,
 * - three-relation joins,
 * - event-driven workflow reporting,
 * - validation and failure handling,
 * - and an indexed equality join.
 *
 * Run with:
 *   node inner_join.js
 */

function printTitle(title) {
    console.log(`\n${"=".repeat(78)}`);
    console.log(title);
    console.log("=".repeat(78));
}

function printRows(rows, columns = null) {
    if (rows.length === 0) {
        console.log("(no rows)");
        return;
    }

    const selectedColumns = columns ?? Object.keys(rows[0]);

    const widths = Object.fromEntries(
        selectedColumns.map((column) => [
            column,
            Math.max(
                column.length,
                ...rows.map((row) => String(row[column] ?? "").length)
            )
        ])
    );

    console.log(
        selectedColumns
            .map((column) => column.padEnd(widths[column]))
            .join(" | ")
    );

    console.log(
        selectedColumns
            .map((column) => "-".repeat(widths[column]))
            .join("-+-")
    );

    for (const row of rows) {
        console.log(
            selectedColumns
                .map((column) => String(row[column] ?? "").padEnd(widths[column]))
                .join(" | ")
        );
    }
}

function validateRows(rows, requiredColumns) {
    if (!Array.isArray(rows)) {
        throw new TypeError("A relation must be represented by an array.");
    }

    rows.forEach((row, index) => {
        if (row === null || typeof row !== "object" || Array.isArray(row)) {
            throw new TypeError(`Row ${index} must be a plain object.`);
        }

        for (const column of requiredColumns) {
            if (!Object.prototype.hasOwnProperty.call(row, column)) {
                throw new Error(
                    `Row ${index} is missing required join column "${column}".`
                );
            }
        }
    });

    return rows;
}

/*
 * A general nested-loop INNER JOIN.
 *
 * JavaScript-specific detail:
 * predicate is a callback, allowing callers to supply a relationship rule
 * without changing the join engine itself.
 *
 * Only combinations for which predicate(leftRow, rightRow) returns true are
 * emitted. This is the defining behavior of an INNER JOIN.
 */
function innerJoin(leftRows, rightRows, predicate, options = {}) {
    const {
        leftPrefix = "left",
        rightPrefix = "right"
    } = options;

    if (typeof predicate !== "function") {
        throw new TypeError("The join condition must be a function.");
    }

    const result = [];

    for (const leftRow of leftRows) {
        for (const rightRow of rightRows) {
            if (predicate(leftRow, rightRow)) {
                const combined = {};

                for (const [key, value] of Object.entries(leftRow)) {
                    combined[`${leftPrefix}.${key}`] = value;
                }

                for (const [key, value] of Object.entries(rightRow)) {
                    combined[`${rightPrefix}.${key}`] = value;
                }

                result.push(combined);
            }
        }
    }

    return result;
}

/*
 * Equality INNER JOIN with an index.
 *
 * Map provides average constant-time key lookup. Duplicate right-side keys
 * are stored as arrays because one key can legitimately match many rows.
 *
 * This implementation is useful for showing why database engines do not
 * necessarily compare every possible pair for an equality join.
 */
function equalityInnerJoin(leftRows, rightRows, leftKey, rightKey) {
    validateRows(leftRows, [leftKey]);
    validateRows(rightRows, [rightKey]);

    const index = new Map();

    for (const row of rightRows) {
        const key = row[rightKey];

        if (!index.has(key)) {
            index.set(key, []);
        }

        index.get(key).push(row);
    }

    const result = [];

    for (const leftRow of leftRows) {
        const matches = index.get(leftRow[leftKey]) ?? [];

        for (const rightRow of matches) {
            result.push({
                ...Object.fromEntries(
                    Object.entries(leftRow).map(([key, value]) => [
                        `left.${key}`,
                        value
                    ])
                ),
                ...Object.fromEntries(
                    Object.entries(rightRow).map(([key, value]) => [
                        `right.${key}`,
                        value
                    ])
                )
            });
        }
    }

    return result;
}

function projectRows(rows, mappings) {
    return rows.map((row) => {
        const projected = {};

        for (const [outputName, sourceName] of Object.entries(mappings)) {
            projected[outputName] = row[sourceName];
        }

        return projected;
    });
}

function filterRows(rows, predicate) {
    if (typeof predicate !== "function") {
        throw new TypeError("The filter must be a function.");
    }

    return rows.filter(predicate);
}

function demonstrateBasicJoin() {
    printTitle("INNER JOIN fundamentals");

    const repositories = [
        { repositoryId: 101, name: "market-prism", owner: "atul" },
        { repositoryId: 102, name: "asset-logistics", owner: "atul" },
        { repositoryId: 103, name: "research-tracker", owner: "atul" }
    ];

    const pullRequests = [
        {
            pullRequestId: 501,
            repositoryId: 101,
            title: "Add risk dashboard",
            state: "open"
        },
        {
            pullRequestId: 502,
            repositoryId: 101,
            title: "Fix validation",
            state: "merged"
        },
        {
            pullRequestId: 503,
            repositoryId: 999,
            title: "Unknown repository",
            state: "open"
        }
    ];

    const joined = equalityInnerJoin(
        repositories,
        pullRequests,
        "repositoryId",
        "repositoryId"
    );

    const result = projectRows(joined, {
        repository: "left.name",
        pullRequest: "right.pullRequestId",
        title: "right.title",
        state: "right.state"
    });

    printRows(result);
}

function demonstrateDuplicateKeys() {
    printTitle("Duplicate join keys create multiple matching pairs");

    const teams = [
        { teamId: 1, name: "Platform" },
        { teamId: 2, name: "Security" }
    ];

    const developers = [
        { developerId: 10, username: "alice", teamId: 1 },
        { developerId: 11, username: "bob", teamId: 1 },
        { developerId: 12, username: "carol", teamId: 2 },
        { developerId: 13, username: "dave", teamId: 1 }
    ];

    const joined = equalityInnerJoin(
        teams,
        developers,
        "teamId",
        "teamId"
    );

    printRows(
        projectRows(joined, {
            team: "left.name",
            developer: "right.username"
        })
    );

    console.log(
        "\nThe Platform row appears three times because three developer rows " +
        "satisfy the same equality condition."
    );
}

function demonstrateCustomCondition() {
    printTitle("Custom join condition");

    const repositories = [
        { repositoryId: 201, name: "payments-api" },
        { repositoryId: 202, name: "identity-api" }
    ];

    const deployments = [
        { deploymentId: 601, repositoryId: 201, environment: "production" },
        { deploymentId: 602, repositoryId: 201, environment: "staging" },
        { deploymentId: 603, repositoryId: 202, environment: "production" }
    ];

    const joined = innerJoin(
        repositories,
        deployments,
        (repository, deployment) =>
            repository.repositoryId === deployment.repositoryId &&
            deployment.environment === "production"
    );

    printRows(
        projectRows(joined, {
            repository: "left.name",
            deployment: "right.deploymentId",
            environment: "right.environment"
        })
    );
}

function demonstrateCompositeCondition() {
    printTitle("Composite join condition");

    const branchPolicies = [
        {
            repositoryId: 301,
            branch: "main",
            requiredReviews: 2
        },
        {
            repositoryId: 301,
            branch: "develop",
            requiredReviews: 1
        },
        {
            repositoryId: 302,
            branch: "main",
            requiredReviews: 1
        }
    ];

    const pullRequests = [
        { id: 701, repositoryId: 301, baseBranch: "main" },
        { id: 702, repositoryId: 301, baseBranch: "develop" },
        { id: 703, repositoryId: 302, baseBranch: "main" },
        { id: 704, repositoryId: 301, baseBranch: "release" }
    ];

    const joined = innerJoin(
        branchPolicies,
        pullRequests,
        (policy, pullRequest) =>
            policy.repositoryId === pullRequest.repositoryId &&
            policy.branch === pullRequest.baseBranch
    );

    printRows(
        projectRows(joined, {
            pullRequest: "right.id",
            repository: "left.repositoryId",
            branch: "left.branch",
            requiredReviews: "left.requiredReviews"
        })
    );
}

function demonstratePostJoinFiltering() {
    printTitle("Relationship matching followed by result filtering");

    const repositories = [
        { repositoryId: 401, name: "analytics" },
        { repositoryId: 402, name: "billing" }
    ];

    const pullRequests = [
        { id: 801, repositoryId: 401, state: "open" },
        { id: 802, repositoryId: 401, state: "merged" },
        { id: 803, repositoryId: 402, state: "open" }
    ];

    const joined = equalityInnerJoin(
        repositories,
        pullRequests,
        "repositoryId",
        "repositoryId"
    );

    const openPullRequests = filterRows(
        joined,
        (row) => row["right.state"] === "open"
    );

    console.log("All repository/PR matches:");
    printRows(joined);

    console.log("\nOnly open PR matches:");
    printRows(openPullRequests);
}

function demonstrateThreeTableJoin() {
    printTitle("Three-table INNER JOIN chain");

    const repositories = [
        { repositoryId: 501, name: "market-engine" },
        { repositoryId: 502, name: "security-engine" }
    ];

    const pullRequests = [
        {
            id: 901,
            repositoryId: 501,
            authorId: 1001,
            title: "Improve risk calculation"
        },
        {
            id: 902,
            repositoryId: 502,
            authorId: 1002,
            title: "Rotate security policy"
        },
        {
            id: 903,
            repositoryId: 501,
            authorId: 9999,
            title: "Unknown author"
        }
    ];

    const developers = [
        { developerId: 1001, username: "maya", team: "quant" },
        { developerId: 1002, username: "rohan", team: "security" }
    ];

    const repositoryPullRequests = equalityInnerJoin(
        repositories,
        pullRequests,
        "repositoryId",
        "repositoryId"
    );

    const complete = innerJoin(
        repositoryPullRequests,
        developers,
        (repositoryAndPullRequest, developer) =>
            repositoryAndPullRequest["right.authorId"] ===
            developer.developerId,
        {
            leftPrefix: "repositoryPullRequest",
            rightPrefix: "developer"
        }
    );

    printRows(
        projectRows(complete, {
            repository: "repositoryPullRequest.left.name",
            pullRequest: "repositoryPullRequest.right.id",
            author: "developer.username",
            team: "developer.team"
        })
    );
}

/*
 * Event-driven demonstration.
 *
 * Node.js is event-oriented, so the join operation can be embedded in a
 * workflow where completion triggers validation and reporting.
 *
 * queueMicrotask is used instead of an artificial timer: the example shows
 * asynchronous scheduling without requiring network access.
 */
function demonstrateEventDrivenJoin() {
    printTitle("Event-driven join workflow");

    const repositories = [
        { repositoryId: 601, name: "payments" },
        { repositoryId: 602, name: "identity" }
    ];

    const pullRequests = [
        { id: 1001, repositoryId: 601, state: "open" },
        { id: 1002, repositoryId: 602, state: "merged" }
    ];

    const eventHandlers = new Map();

    function on(eventName, handler) {
        if (!eventHandlers.has(eventName)) {
            eventHandlers.set(eventName, []);
        }

        eventHandlers.get(eventName).push(handler);
    }

    function emit(eventName, payload) {
        for (const handler of eventHandlers.get(eventName) ?? []) {
            handler(payload);
        }
    }

    on("join-complete", (rows) => {
        console.log(`Join completed with ${rows.length} matching rows.`);
        printRows(rows);
    });

    on("join-error", (error) => {
        console.error(`Join failed: ${error.message}`);
    });

    queueMicrotask(() => {
        try {
            const rows = equalityInnerJoin(
                repositories,
                pullRequests,
                "repositoryId",
                "repositoryId"
            );

            emit("join-complete", rows);
        } catch (error) {
            emit("join-error", error);
        }
    });
}

/*
 * SQL NULL behavior differs from JavaScript's ordinary equality.
 *
 * JavaScript:
 *   null === null -> true
 *
 * SQL:
 *   NULL = NULL -> UNKNOWN, not TRUE
 *
 * This helper models SQL-style equality for nullable values by refusing to
 * treat two null values as a successful equality match.
 */
function sqlLikeEquality(leftValue, rightValue) {
    if (leftValue === null || rightValue === null) {
        return false;
    }

    return leftValue === rightValue;
}

function demonstrateNullableKeys() {
    printTitle("Nullable join keys and SQL-style three-valued behavior");

    const left = [
        { id: 1, externalKey: "A100" },
        { id: 2, externalKey: null }
    ];

    const right = [
        { sourceId: 10, externalKey: "A100" },
        { sourceId: 11, externalKey: null }
    ];

    const joined = innerJoin(
        left,
        right,
        (leftRow, rightRow) =>
            sqlLikeEquality(leftRow.externalKey, rightRow.externalKey)
    );

    printRows(joined);
}

function runAssertions() {
    printTitle("Executable correctness checks");

    const left = [
        { id: 1, key: "A" },
        { id: 2, key: "B" }
    ];

    const right = [
        { id: 10, key: "A" },
        { id: 11, key: "A" },
        { id: 12, key: "C" }
    ];

    const result = equalityInnerJoin(left, right, "key", "key");

    console.assert(
        result.length === 2,
        "Two right-side rows should match left key A."
    );

    console.assert(
        result.every((row) => row["left.key"] === row["right.key"]),
        "Every INNER JOIN output must satisfy the join condition."
    );

    console.assert(
        !result.some((row) => row["right.id"] === 12),
        "Unmatched key C must not appear."
    );

    try {
        equalityInnerJoin(
            [{ id: 1 }],
            [{ name: "x" }],
            "id",
            "id"
        );
    } catch (error) {
        console.assert(
            error instanceof Error,
            "Missing join columns must raise an error."
        );
    }
}

async function main() {
    demonstrateBasicJoin();
    demonstrateDuplicateKeys();
    demonstrateCustomCondition();
    demonstrateCompositeCondition();
    demonstratePostJoinFiltering();
    demonstrateThreeTableJoin();
    demonstrateNullableKeys();
    demonstrateEventDrivenJoin();

    // Allow the microtask used by the event-driven demonstration to run.
    await Promise.resolve();

    runAssertions();

    printTitle("Performance model");
    console.log(
        "A nested-loop join checks up to L × R candidate pairs. " +
        "The equality join builds a Map index on the right relation, " +
        "reducing equality lookup work to approximately O(L + R), " +
        "apart from output construction."
    );
}

main().catch((error) => {
    console.error(`Fatal error: ${error.message}`);
    process.exitCode = 1;
});
