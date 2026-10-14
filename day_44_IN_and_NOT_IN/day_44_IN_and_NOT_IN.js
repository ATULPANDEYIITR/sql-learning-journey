"use strict";

/*
 * IN and NOT IN are SQL membership predicates.
 *
 * JavaScript does not implement SQL's three-valued logic, so this program
 * deliberately models SQL UNKNOWN with the value null. This makes the
 * difference between ordinary JavaScript membership and SQL membership
 * explicit rather than hiding it behind language-specific behavior.
 */

const SQL = Object.freeze({
    TRUE: true,
    FALSE: false,
    UNKNOWN: null
});

function sqlEqual(left, right) {
    // SQL equality involving NULL is UNKNOWN.
    if (left === null || right === null) {
        return SQL.UNKNOWN;
    }

    return left === right;
}

function sqlIn(value, candidates) {
    let encounteredUnknown = false;

    for (const candidate of candidates) {
        const comparison = sqlEqual(value, candidate);

        if (comparison === SQL.TRUE) {
            return SQL.TRUE;
        }

        if (comparison === SQL.UNKNOWN) {
            encounteredUnknown = true;
        }
    }

    return encounteredUnknown ? SQL.UNKNOWN : SQL.FALSE;
}

function sqlNot(value) {
    if (value === SQL.UNKNOWN) {
        return SQL.UNKNOWN;
    }

    return !value;
}

function passesWhere(predicateResult) {
    // SQL WHERE returns rows only when the predicate is TRUE.
    return predicateResult === SQL.TRUE;
}

function demonstrateIn() {
    console.log("Basic IN behavior");

    const departments = ["Engineering", "Security", "Research"];

    for (const department of [
        "Engineering",
        "Finance",
        "Security",
        null
    ]) {
        console.log(
            department,
            "IN",
            departments,
            "=>",
            sqlIn(department, departments)
        );
    }
}

function demonstrateNotInNull() {
    console.log("\nNOT IN with NULL");

    const blockedDepartments = ["Finance", null];

    for (const department of [
        "Engineering",
        "Finance",
        "Security",
        null
    ]) {
        const inResult = sqlIn(department, blockedDepartments);
        const notInResult = sqlNot(inResult);

        console.log({
            department,
            inResult,
            notInResult,
            returnedByWhere: passesWhere(notInResult)
        });
    }

    /*
     * Engineering is not Finance, but the list also contains NULL.
     * SQL evaluates:
     *
     * Engineering <> Finance  -> TRUE
     * Engineering <> NULL     -> UNKNOWN
     * TRUE AND UNKNOWN        -> UNKNOWN
     *
     * Therefore NOT IN does not become TRUE.
     */
}

function demonstrateExists() {
    console.log("\nNOT EXISTS-style exclusion");

    const employees = [
        { id: 101, name: "Asha", department: "Engineering" },
        { id: 102, name: "Ravi", department: "Finance" },
        { id: 103, name: "Mira", department: "Security" },
        { id: 104, name: "Noor", department: null }
    ];

    const blocked = ["Finance", null];

    /*
     * EXISTS asks whether a matching row exists.
     * A NULL blocked department is not itself a match for a non-NULL
     * employee department because SQL equality with NULL is UNKNOWN.
     */
    for (const employee of employees) {
        const matchingBlockedDepartment = blocked.some(
            blockedDepartment =>
                blockedDepartment !== null &&
                employee.department !== null &&
                employee.department === blockedDepartment
        );

        const allowed = !matchingBlockedDepartment;

        console.log(
            `${employee.name}: ${allowed ? "allowed" : "blocked"}`
        );
    }
}

function demonstrateJavaScriptDifference() {
    console.log("\nJavaScript membership is not SQL membership");

    const values = ["Engineering", null];

    console.log(
        "Array.includes(null):",
        values.includes(null)
    );

    console.log(
        "Array.includes('Finance'):",
        values.includes("Finance")
    );

    console.log(
        "SQL IN model for Finance:",
        sqlIn("Finance", values)
    );

    console.log(
        "SQL IN model for NULL:",
        sqlIn(null, values)
    );

    /*
     * JavaScript Array.includes() returns an ordinary Boolean.
     * SQL IN can return TRUE, FALSE, or UNKNOWN.
     */
}

function buildInPredicate(column, values) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(column)) {
        throw new Error("Unsafe SQL identifier");
    }

    if (!Array.isArray(values)) {
        throw new TypeError("values must be an array");
    }

    if (values.length === 0) {
        return {
            text: "FALSE",
            parameters: []
        };
    }

    const placeholders = values.map((_, index) => `$${index + 1}`);

    return {
        text: `${column} IN (${placeholders.join(", ")})`,
        parameters: values
    };
}

function demonstrateParameterizedQueryConstruction() {
    console.log("\nParameterized IN predicate");

    const query = buildInPredicate(
        "employee_id",
        [101, 103, 104]
    );

    console.log(query);

    /*
     * Values are represented as parameters rather than interpolated into
     * SQL source text. This is the correct boundary between application
     * data and SQL syntax.
     */
}

function evaluateApprovalPolicy(reviewers, requiredApprovals) {
    if (!Number.isInteger(requiredApprovals) || requiredApprovals < 0) {
        throw new RangeError("requiredApprovals must be a non-negative integer");
    }

    const validStatuses = new Set(["APPROVED", "CHANGES_REQUESTED", "COMMENTED"]);

    for (const reviewer of reviewers) {
        if (!validStatuses.has(reviewer.status)) {
            throw new Error(`Invalid review status: ${reviewer.status}`);
        }
    }

    const approvals = reviewers.filter(
        reviewer => reviewer.status === "APPROVED"
    );

    return {
        approvalCount: approvals.length,
        eligible: approvals.length >= requiredApprovals
    };
}

async function simulateEventDrivenReview() {
    console.log("\nEvent-driven review evaluation");

    const reviewEvents = [
        { reviewer: "Asha", status: "APPROVED" },
        { reviewer: "Ravi", status: "COMMENTED" },
        { reviewer: "Mira", status: "APPROVED" }
    ];

    await new Promise(resolve => setTimeout(resolve, 20));

    const result = evaluateApprovalPolicy(reviewEvents, 2);

    console.log(result);
}

async function main() {
    demonstrateIn();
    demonstrateNotInNull();
    demonstrateExists();
    demonstrateJavaScriptDifference();
    demonstrateParameterizedQueryConstruction();
    await simulateEventDrivenReview();

    console.log("\nJavaScript membership demonstration complete.");
}

main().catch(error => {
    console.error("Execution failed:", error.message);
    process.exitCode = 1;
});
