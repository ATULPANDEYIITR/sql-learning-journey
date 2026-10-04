"use strict";

/*
 * LEFT JOIN | Left outer joins, unmatched rows, NULL results
 *
 * This Node.js-compatible file builds an event-driven relational workflow.
 * JavaScript's null value represents SQL-style NULL-like output for a missing
 * right-side row.
 *
 * The implementation emphasizes JavaScript-specific patterns:
 * - Map-based hash indexing
 * - Immutable result construction
 * - EventEmitter-driven workflow events
 * - asynchronous policy evaluation
 * - predicate functions
 * - optional chaining for NULL-sensitive access
 * - aggregation with Map
 * - explicit validation
 */

const { EventEmitter } = require("node:events");

const SQL_NULL = null;

function printTitle(title) {
    console.log(`\n${"=".repeat(82)}\n${title}\n${"=".repeat(82)}`);
}

function printRows(rows, columns) {
    if (rows.length === 0) {
        console.log("(no rows)");
        return;
    }

    const widths = Object.fromEntries(
        columns.map((column) => [
            column,
            Math.max(
                column.length,
                ...rows.map((row) => String(row[column] ?? "NULL").length)
            ),
        ])
    );

    console.log(columns.map((column) => column.padEnd(widths[column])).join(" | "));
    console.log(columns.map((column) => "-".repeat(widths[column])).join("-+-"));

    for (const row of rows) {
        console.log(
            columns
                .map((column) => String(row[column] ?? "NULL").padEnd(widths[column]))
                .join(" | ")
        );
    }
}

function sqlEquals(left, right) {
    /*
     * JavaScript's === would consider null === null true, but SQL does not.
     * Explicitly handling null avoids accidentally changing SQL NULL semantics.
     */
    return left !== null && right !== null && left !== undefined && right !== undefined && left === right;
}

function validateTable(table, tableName) {
    if (!Array.isArray(table)) {
        throw new TypeError(`${tableName} must be an array.`);
    }

    for (const row of table) {
        if (row === null || typeof row !== "object" || Array.isArray(row)) {
            throw new TypeError(`Every ${tableName} row must be an object.`);
        }
    }
}

function collectColumns(rows) {
    const columns = new Set();

    for (const row of rows) {
        for (const column of Object.keys(row)) {
            columns.add(column);
        }
    }

    return [...columns];
}

function mergeRows(leftRow, rightRow, rightColumns) {
    const result = { ...leftRow };

    for (const column of rightColumns) {
        /*
         * Prefix collisions so that a column called "id" on each side does not
         * silently overwrite the left-side value.
         */
        const outputColumn = Object.hasOwn(result, column)
            ? `right_${column}`
            : column;

        result[outputColumn] = rightRow ? rightRow[column] : SQL_NULL;
    }

    return result;
}

function leftJoin({
    left,
    right,
    leftKey,
    rightKey,
    on = () => true,
}) {
    validateTable(left, "left");
    validateTable(right, "right");

    if (typeof leftKey !== "function" || typeof rightKey !== "function") {
        throw new TypeError("leftKey and rightKey must be functions.");
    }

    const rightColumns = collectColumns(right);
    const index = new Map();

    for (const rightRow of right) {
        const key = rightKey(rightRow);

        /*
         * A Map can index null, but SQL NULL must not participate in ordinary
         * equality matching, so NULL keys are intentionally excluded.
         */
        if (key === null || key === undefined) {
            continue;
        }

        if (!index.has(key)) {
            index.set(key, []);
        }

        index.get(key).push(rightRow);
    }

    const output = [];

    for (const leftRow of left) {
        const key = leftKey(leftRow);
        const candidates =
            key === null || key === undefined ? [] : index.get(key) ?? [];

        const matches = candidates.filter((rightRow) => on(leftRow, rightRow));

        if (matches.length === 0) {
            output.push(mergeRows(leftRow, null, rightColumns));
            continue;
        }

        for (const rightRow of matches) {
            output.push(mergeRows(leftRow, rightRow, rightColumns));
        }
    }

    return output;
}

function innerJoin({ left, right, leftKey, rightKey }) {
    const rightColumns = collectColumns(right);
    const index = new Map();

    for (const rightRow of right) {
        const key = rightKey(rightRow);

        if (key === null || key === undefined) {
            continue;
        }

        if (!index.has(key)) {
            index.set(key, []);
        }

        index.get(key).push(rightRow);
    }

    const output = [];

    for (const leftRow of left) {
        const key = leftKey(leftRow);

        if (key === null || key === undefined) {
            continue;
        }

        for (const rightRow of index.get(key) ?? []) {
            output.push(mergeRows(leftRow, rightRow, rightColumns));
        }
    }

    return output;
}

function where(rows, predicate) {
    return rows.filter(predicate);
}

function countBy(rows, keySelector, valueSelector = null) {
    const result = new Map();

    for (const row of rows) {
        const key = keySelector(row);

        if (!result.has(key)) {
            result.set(key, {
                countStar: 0,
                countValue: 0,
            });
        }

        const group = result.get(key);
        group.countStar += 1;

        if (valueSelector !== null && valueSelector(row) !== null && valueSelector(row) !== undefined) {
            group.countValue += 1;
        }
    }

    return [...result.entries()].map(([group, counts]) => ({
        group,
        ...counts,
    }));
}

class JoinWorkflow extends EventEmitter {
    constructor(name) {
        super();
        this.name = name;
        this.history = [];
    }

    emitStep(eventName, payload) {
        const event = {
            eventName,
            timestamp: new Date().toISOString(),
            payload,
        };

        this.history.push(event);
        this.emit(eventName, event);
    }

    async execute(config) {
        this.emitStep("started", {
            workflow: this.name,
            leftRows: config.left.length,
            rightRows: config.right.length,
        });

        await new Promise((resolve) => setTimeout(resolve, 10));

        const joined = leftJoin(config);

        this.emitStep("joined", {
            outputRows: joined.length,
        });

        await new Promise((resolve) => setTimeout(resolve, 10));

        this.emitStep("completed", {
            unmatchedLeftRows: joined.filter((row) => row[config.rightIndicator] === null).length,
        });

        return joined;
    }
}

function demoBasicJoin() {
    printTitle("Basic LEFT JOIN with one-to-many matching");

    const customers = [
        { customerId: 1, name: "Aarav" },
        { customerId: 2, name: "Meera" },
        { customerId: 3, name: "Kabir" },
    ];

    const orders = [
        { orderId: 5001, customerId: 1, amount: 2200 },
        { orderId: 5002, customerId: 1, amount: 4100 },
        { orderId: 5003, customerId: 3, amount: 900 },
    ];

    const result = leftJoin({
        left: customers,
        right: orders,
        leftKey: (row) => row.customerId,
        rightKey: (row) => row.customerId,
    });

    printRows(result, [
        "customerId",
        "name",
        "orderId",
        "right_customerId",
        "amount",
    ]);
}

function demoOnVsWhere() {
    printTitle("ON predicate versus WHERE predicate");

    const accounts = [
        { accountId: "A1", owner: "Aarav" },
        { accountId: "A2", owner: "Meera" },
        { accountId: "A3", owner: "Kabir" },
    ];

    const transactions = [
        { transactionId: "T1", accountId: "A1", status: "SETTLED", amount: 5000 },
        { transactionId: "T2", accountId: "A1", status: "FAILED", amount: 7000 },
        { transactionId: "T3", accountId: "A2", status: "SETTLED", amount: 1200 },
    ];

    const settledInJoin = leftJoin({
        left: accounts,
        right: transactions,
        leftKey: (row) => row.accountId,
        rightKey: (row) => row.accountId,
        on: (_, transaction) => transaction.status === "SETTLED",
    });

    console.log("Settlement condition evaluated as part of the join:");
    printRows(settledInJoin, [
        "accountId",
        "owner",
        "transactionId",
        "right_accountId",
        "status",
        "amount",
    ]);

    const joinedFirst = leftJoin({
        left: accounts,
        right: transactions,
        leftKey: (row) => row.accountId,
        rightKey: (row) => row.accountId,
    });

    const settledInWhere = where(
        joinedFirst,
        (row) => row.status === "SETTLED"
    );

    console.log("\nSettlement condition evaluated after the join:");
    printRows(settledInWhere, [
        "accountId",
        "owner",
        "transactionId",
        "right_accountId",
        "status",
        "amount",
    ]);
}

function demoNullAndAntiJoin() {
    printTitle("NULL results and finding unmatched rows");

    const departments = [
        { departmentId: 10, departmentName: "Engineering" },
        { departmentId: 20, departmentName: "Finance" },
        { departmentId: 30, departmentName: "Research" },
    ];

    const employees = [
        { employeeId: 1, departmentId: 10, employeeName: "Ravi" },
        { employeeId: 2, departmentId: 10, employeeName: "Nisha" },
    ];

    const result = leftJoin({
        left: departments,
        right: employees,
        leftKey: (row) => row.departmentId,
        rightKey: (row) => row.departmentId,
    });

    printRows(result, [
        "departmentId",
        "departmentName",
        "employeeId",
        "right_departmentId",
        "employeeName",
    ]);

    const unmatched = where(result, (row) => row.employeeId === null);

    console.log("\nDepartments without employees:");
    printRows(unmatched, ["departmentId", "departmentName", "employeeId"]);
}

function demoAggregation() {
    printTitle("COUNT(*) versus COUNT(right-side value)");

    const teams = [
        { teamId: "PLATFORM" },
        { teamId: "DATA" },
        { teamId: "SECURITY" },
    ];

    const incidents = [
        { incidentId: 101, teamId: "PLATFORM" },
        { incidentId: 102, teamId: "PLATFORM" },
    ];

    const joined = leftJoin({
        left: teams,
        right: incidents,
        leftKey: (row) => row.teamId,
        rightKey: (row) => row.teamId,
    });

    const counts = countBy(
        joined,
        (row) => row.teamId,
        (row) => row.incidentId
    );

    printRows(counts, ["group", "countStar", "countValue"]);

    console.log(
        "\nThe NULL-extended SECURITY row exists for COUNT(*), but its NULL incidentId is excluded from COUNT(incidentId)."
    );
}

function demoCompositeKey() {
    printTitle("Composite key represented by a JavaScript Map key");

    const subscriptions = [
        { accountId: 1, region: "IN", plan: "PRO" },
        { accountId: 1, region: "US", plan: "PRO" },
        { accountId: 2, region: "IN", plan: "BASIC" },
    ];

    const invoices = [
        { accountId: 1, region: "IN", invoiceId: "INV-1" },
        { accountId: 2, region: "IN", invoiceId: "INV-2" },
    ];

    /*
     * Arrays are not value-equal in JavaScript, so a stable serialized
     * composite key is used here instead of a fresh array object per lookup.
     */
    const compositeKey = (row) =>
        JSON.stringify([row.accountId, row.region]);

    const result = leftJoin({
        left: subscriptions,
        right: invoices,
        leftKey: compositeKey,
        rightKey: compositeKey,
    });

    printRows(result, [
        "accountId",
        "region",
        "plan",
        "invoiceId",
        "right_accountId",
        "right_region",
    ]);
}

async function demoEventDrivenWorkflow() {
    printTitle("Event-driven LEFT JOIN workflow");

    const workflow = new JoinWorkflow("Customer Order Enrichment");

    workflow.on("started", (event) => {
        console.log(
            `EVENT started: ${event.payload.leftRows} left rows, ${event.payload.rightRows} right rows`
        );
    });

    workflow.on("joined", (event) => {
        console.log(`EVENT joined: ${event.payload.outputRows} output rows`);
    });

    workflow.on("completed", (event) => {
        console.log(
            `EVENT completed: ${event.payload.unmatchedLeftRows} left rows had no qualifying match`
        );
    });

    const customers = [
        { customerId: 1, name: "Aarav" },
        { customerId: 2, name: "Meera" },
        { customerId: 3, name: "Kabir" },
    ];

    const orders = [
        { orderId: 1, customerId: 1, state: "PAID" },
        { orderId: 2, customerId: 3, state: "PAID" },
    ];

    const result = await workflow.execute({
        left: customers,
        right: orders,
        leftKey: (row) => row.customerId,
        rightKey: (row) => row.customerId,
        rightIndicator: "orderId",
    });

    printRows(result, [
        "customerId",
        "name",
        "orderId",
        "right_customerId",
        "state",
    ]);
}

function demoOptionalChaining() {
    printTitle("JavaScript NULL-safe access after a LEFT JOIN");

    const users = [
        { id: 1, name: "Aarav" },
        { id: 2, name: "Meera" },
    ];

    const profiles = [
        { userId: 1, city: "Lucknow" },
    ];

    const joined = leftJoin({
        left: users,
        right: profiles,
        leftKey: (row) => row.id,
        rightKey: (row) => row.userId,
    });

    for (const row of joined) {
        /*
         * Optional chaining is useful when later application code needs to
         * safely inspect a potentially missing nested object. The join itself
         * already represents missing right-side attributes as null.
         */
        const city = row.city ?? "No profile city";
        console.log(`${row.name}: ${city}`);
    }
}

function demonstrateComplexity() {
    printTitle("Performance and correctness considerations");

    console.log(
        "The implementation indexes the right table with Map, making equality joins approximately O(L + R + M)."
    );
    console.log(
        "M is the number of matching output combinations, which can exceed the input row counts in one-to-many joins."
    );
    console.log(
        "A nested-loop implementation can approach O(L × R), so repeated full scans should be avoided for large in-memory datasets."
    );
    console.log(
        "JavaScript Map keys use JavaScript equality semantics, so composite keys need a stable representation such as JSON.stringify or a dedicated key object."
    );
    console.log(
        "Production database systems can select different join algorithms using statistics, indexes, memory availability, and predicate selectivity."
    );
}

async function main() {
    printTitle("LEFT JOIN | JavaScript Demonstration");

    demoBasicJoin();
    demoOnVsWhere();
    demoNullAndAntiJoin();
    demoAggregation();
    demoCompositeKey();
    demoOptionalChaining();
    await demoEventDrivenWorkflow();
    demonstrateComplexity();

    printTitle("Execution complete");
    console.log(
        "Every left-side row is preserved; matching right-side rows expand the result, while missing right-side attributes become null."
    );
}

main().catch((error) => {
    console.error("LEFT JOIN demonstration failed:", error.message);
    process.exitCode = 1;
});
