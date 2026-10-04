"use strict";

/*
 * RIGHT JOIN and FULL OUTER JOIN workflow model.
 *
 * JavaScript does not provide relational JOIN operators for ordinary arrays,
 * so this file implements them as reusable collection operations. The
 * implementation follows SQL equality semantics, including the rule that
 * null does not equal null during a join.
 */

const employeeRecords = [
    { employeeId: 101, employeeName: "Aarav", departmentId: 10 },
    { employeeId: 102, employeeName: "Meera", departmentId: 20 },
    { employeeId: 103, employeeName: "Kabir", departmentId: 20 },
    { employeeId: 104, employeeName: "Isha", departmentId: 40 },
    { employeeId: 105, employeeName: "Rohan", departmentId: null }
];

const departmentRecords = [
    { departmentId: 10, departmentName: "Engineering", managerId: 9001 },
    { departmentId: 20, departmentName: "Finance", managerId: 9002 },
    { departmentId: 30, departmentName: "Research", managerId: 9003 },
    { departmentId: 40, departmentName: "Operations", managerId: null },
    { departmentId: 50, departmentName: "Legal", managerId: 9005 }
];

function validateRows(rows, requiredFields, datasetName) {
    if (!Array.isArray(rows)) {
        throw new TypeError(`${datasetName} must be an array.`);
    }

    for (const row of rows) {
        if (row === null || typeof row !== "object") {
            throw new TypeError(`${datasetName} contains a non-object row.`);
        }

        for (const field of requiredFields) {
            if (!(field in row)) {
                throw new Error(
                    `${datasetName} row is missing required field "${field}".`
                );
            }
        }
    }
}

function joinKey(value) {
    /*
     * JavaScript's Map can distinguish undefined and null, but SQL JOIN
     * semantics require NULL to be non-matchable. Returning undefined for
     * null makes that rule explicit.
     */
    return value === null || value === undefined ? undefined : value;
}

function rightJoin(leftRows, rightRows, leftKey, rightKey) {
    validateRows(leftRows, [leftKey], "Left relation");
    validateRows(rightRows, [rightKey], "Right relation");

    const index = new Map();

    for (const leftRow of leftRows) {
        const key = joinKey(leftRow[leftKey]);

        if (key === undefined) {
            continue;
        }

        if (!index.has(key)) {
            index.set(key, []);
        }

        index.get(key).push(leftRow);
    }

    const output = [];

    for (const rightRow of rightRows) {
        const key = joinKey(rightRow[rightKey]);
        const matches = key === undefined ? [] : (index.get(key) ?? []);

        if (matches.length === 0) {
            output.push({
                ...nullColumns(leftRows),
                ...rightRow
            });
            continue;
        }

        for (const leftRow of matches) {
            output.push({
                ...leftRow,
                ...rightRow
            });
        }
    }

    return output;
}

function fullOuterJoin(leftRows, rightRows, leftKey, rightKey) {
    validateRows(leftRows, [leftKey], "Left relation");
    validateRows(rightRows, [rightKey], "Right relation");

    const rightIndex = new Map();
    const matchedRightRows = new Set();

    for (let index = 0; index < rightRows.length; index++) {
        const rightRow = rightRows[index];
        const key = joinKey(rightRow[rightKey]);

        if (key === undefined) {
            continue;
        }

        if (!rightIndex.has(key)) {
            rightIndex.set(key, []);
        }

        rightIndex.get(key).push({ index, row: rightRow });
    }

    const output = [];

    for (const leftRow of leftRows) {
        const key = joinKey(leftRow[leftKey]);
        const matches = key === undefined ? [] : (rightIndex.get(key) ?? []);

        if (matches.length === 0) {
            output.push({
                ...leftRow,
                ...nullColumns(rightRows)
            });
            continue;
        }

        for (const match of matches) {
            matchedRightRows.add(match.index);

            output.push({
                ...leftRow,
                ...match.row
            });
        }
    }

    for (let index = 0; index < rightRows.length; index++) {
        if (!matchedRightRows.has(index)) {
            output.push({
                ...nullColumns(leftRows),
                ...rightRows[index]
            });
        }
    }

    return output;
}

function nullColumns(rows) {
    if (rows.length === 0) {
        return {};
    }

    return Object.fromEntries(
        Object.keys(rows[0]).map((key) => [key, null])
    );
}

function classifyFullJoin(rows) {
    return rows.map((row) => {
        const employeeExists = row.employeeId !== null;
        const departmentExists = row.departmentName !== null;

        let relationship;

        if (employeeExists && departmentExists) {
            relationship = "MATCHED";
        } else if (employeeExists) {
            relationship = "EMPLOYEE_WITHOUT_DEPARTMENT";
        } else {
            relationship = "DEPARTMENT_WITHOUT_EMPLOYEE";
        }

        return {
            employee: row.employeeName,
            department: row.departmentName,
            relationship
        };
    });
}

function printTable(title, rows) {
    console.log(`\n=== ${title} ===`);

    if (rows.length === 0) {
        console.log("(no rows)");
        return;
    }

    console.table(rows);
}

async function simulateAsynchronousReviewOfJoin() {
    /*
     * The asynchronous layer is intentionally separate from the relational
     * operation. In a Node.js application, joined records might be consumed
     * after asynchronous data retrieval or validation.
     */
    const result = await Promise.resolve(
        fullOuterJoin(
            employeeRecords,
            departmentRecords,
            "departmentId",
            "departmentId"
        )
    );

    return classifyFullJoin(result);
}

async function main() {
    validateRows(
        employeeRecords,
        ["employeeId", "employeeName", "departmentId"],
        "Employees"
    );

    validateRows(
        departmentRecords,
        ["departmentId", "departmentName", "managerId"],
        "Departments"
    );

    /*
     * The department relation is on the right. Every department therefore
     * survives the RIGHT JOIN, including Research and Legal, which have no
     * employees.
     */
    const rightJoinResult = rightJoin(
        employeeRecords,
        departmentRecords,
        "departmentId",
        "departmentId"
    );

    printTable(
        "RIGHT JOIN: preserve every department",
        rightJoinResult
    );

    /*
     * FULL OUTER JOIN preserves both sides. Rohan survives even though his
     * departmentId is null, while Research and Legal survive despite having
     * no matching employee.
     */
    const fullJoinResult = fullOuterJoin(
        employeeRecords,
        departmentRecords,
        "departmentId",
        "departmentId"
    );

    printTable(
        "FULL OUTER JOIN: preserve both relations",
        fullJoinResult
    );

    printTable(
        "FULL JOIN relationship classification",
        classifyFullJoin(fullJoinResult)
    );

    /*
     * Duplicate keys demonstrate that a join is not automatically one-to-one.
     * Two employees in Finance match the same department row, producing two
     * joined rows.
     */
    const financeEmployees = employeeRecords.filter(
        employee => employee.departmentId === 20
    );

    const financeDepartments = departmentRecords.filter(
        department => department.departmentId === 20
    );

    printTable(
        "Multiple rows sharing the same join key",
        fullOuterJoin(
            financeEmployees,
            financeDepartments,
            "departmentId",
            "departmentId"
        )
    );

    /*
     * null values intentionally do not match one another.
     */
    printTable(
        "NULL does not match NULL",
        fullOuterJoin(
            [{ id: 1, groupId: null }],
            [{ groupId: null, label: "Unassigned" }],
            "groupId",
            "groupId"
        )
    );

    const asyncClassification = await simulateAsynchronousReviewOfJoin();

    printTable(
        "Asynchronously consumed FULL JOIN result",
        asyncClassification
    );

    /*
     * A production system should not rely on object spread alone when two
     * relations contain identically named non-key columns. Explicit column
     * projection avoids silent overwrites. This example deliberately uses
     * unique field names so that the mechanics remain visible.
     */
    const safelyProjected = fullJoinResult.map(row => ({
        employeeId: row.employeeId,
        employeeName: row.employeeName,
        employeeDepartmentId: row.departmentId,
        departmentName: row.departmentName,
        managerId: row.managerId
    }));

    printTable(
        "Explicit projection for application output",
        safelyProjected
    );

    console.log("\nOperational considerations:");
    console.log("- RIGHT JOIN preserves every row from the right relation.");
    console.log("- FULL OUTER JOIN preserves unmatched rows from both relations.");
    console.log("- NULL join keys are deliberately excluded from equality matches.");
    console.log("- Duplicate keys can multiply output rows.");
    console.log("- Explicit projection prevents accidental field overwrites.");
    console.log("- Hash indexing reduces repeated scans for equality joins.");

    console.log("\nJavaScript implementation completed.");
}

main().catch(error => {
    console.error("Join demonstration failed:", error.message);
    process.exitCode = 1;
});
