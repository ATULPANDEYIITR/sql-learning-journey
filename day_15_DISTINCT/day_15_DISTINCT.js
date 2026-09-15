"use strict";

/*
PostgreSQL DISTINCT, duplicate elimination, and DISTINCT ON
============================================================

This JavaScript study file complements the Python implementation.

It demonstrates the logical behavior of:

    SELECT DISTINCT
    SELECT DISTINCT ON (...)
    ORDER BY
    NULL handling
    composite uniqueness
    latest-row-per-group logic
    window-function alternatives
    query construction
    validation
    performance-oriented reasoning

The program runs with a normal modern JavaScript runtime such as Node.js.
It does not require npm packages or a live PostgreSQL connection.

The SQL strings shown in this file are PostgreSQL syntax. The in-memory
functions demonstrate their logical behavior without pretending that
JavaScript is executing PostgreSQL's internal query planner.
*/


// ---------------------------------------------------------------------------
// Section 1: Utility functions
// ---------------------------------------------------------------------------

function printTitle(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}

function printRows(rows, title = null) {
    if (title) {
        console.log(`\n${title}`);
    }

    if (rows.length === 0) {
        console.log("(no rows)");
        return;
    }

    rows.forEach((row, index) => {
        console.log(`${String(index + 1).padStart(3)}:`, row);
    });
}


// ---------------------------------------------------------------------------
// Section 2: SELECT DISTINCT concept
// ---------------------------------------------------------------------------

function distinctRows(rows) {
    /*
    JavaScript Set uses SameValueZero equality.

    For primitive values this gives useful educational behavior for a
    PostgreSQL-like DISTINCT demonstration, including repeated null values.

    For complete database rows we serialize values into a stable key.
    A real PostgreSQL engine has type-aware database equality semantics,
    so this is a conceptual simulation rather than an implementation of
    PostgreSQL's executor.
    */
    const seen = new Set();
    const result = [];

    for (const row of rows) {
        const key = JSON.stringify(row);

        if (!seen.has(key)) {
            seen.add(key);
            result.push(row);
        }
    }

    return result;
}

function demoBasicDistinct() {
    printTitle("1. Basic SELECT DISTINCT");

    const cities = [
        ["Delhi"],
        ["Mumbai"],
        ["Delhi"],
        ["Lucknow"],
        ["Mumbai"],
    ];

    printRows(cities, "Without duplicate elimination:");
    printRows(distinctRows(cities), "Conceptual SELECT DISTINCT city:");
}


// ---------------------------------------------------------------------------
// Section 3: Multiple selected columns
// ---------------------------------------------------------------------------

function demoCompositeDistinct() {
    printTitle("2. DISTINCT across multiple columns");

    const rows = [
        ["Alice", "Delhi"],
        ["Alice", "Delhi"],
        ["Alice", "Mumbai"],
        ["Bob", "Delhi"],
        ["Bob", "Delhi"],
        ["Bob", "Mumbai"],
    ];

    printRows(
        distinctRows(rows),
        "Unique (name, city) combinations:"
    );

    console.log(`
PostgreSQL:

SELECT DISTINCT name, city
FROM customers;

Uniqueness applies to the complete selected row. Adding a selected column
can change which rows are considered duplicates.
`);
}


// ---------------------------------------------------------------------------
// Section 4: NULL
// ---------------------------------------------------------------------------

function demoNullDistinct() {
    printTitle("3. NULL and duplicate elimination");

    const rows = [
        [null],
        ["Delhi"],
        [null],
        ["Mumbai"],
        ["Delhi"],
        [null],
    ];

    printRows(
        distinctRows(rows),
        "Conceptual DISTINCT result:"
    );

    console.log(`
Multiple NULL occurrences collapse into one DISTINCT result value.

This is different from ordinary SQL comparison semantics. In PostgreSQL,
NULL does not compare equal to NULL using the normal equality operator.
Duplicate elimination has its own semantics for grouping duplicate result
values.
`);
}


// ---------------------------------------------------------------------------
// Section 5: DISTINCT and expressions
// ---------------------------------------------------------------------------

function demoExpressionDistinct() {
    printTitle("4. DISTINCT on an expression");

    const names = [
        "Alice",
        "alice",
        "ALICE",
        "Bob",
        "bob",
    ];

    const normalized = names.map(name => [name.toLowerCase()]);

    printRows(
        distinctRows(normalized),
        "Conceptual SELECT DISTINCT LOWER(name):"
    );

    console.log(`
The expression is evaluated before duplicate elimination.

PostgreSQL:

SELECT DISTINCT LOWER(name)
FROM customers;

Therefore different source spellings can collapse into the same result.
`);
}


// ---------------------------------------------------------------------------
// Section 6: DISTINCT versus GROUP BY
// ---------------------------------------------------------------------------

function countBy(rows, keyIndex) {
    const counts = new Map();

    for (const row of rows) {
        const key = row[keyIndex];
        counts.set(key, (counts.get(key) ?? 0) + 1);
    }

    return [...counts.entries()].map(([key, count]) => [key, count]);
}

function demoDistinctVsGroupBy() {
    printTitle("5. DISTINCT versus GROUP BY");

    const orders = [
        [101, "Delhi", 500],
        [102, "Delhi", 700],
        [103, "Mumbai", 900],
        [104, "Delhi", 300],
        [105, "Mumbai", 400],
    ];

    const uniqueCities = distinctRows(
        orders.map(order => [order[1]])
    );

    const counts = countBy(orders, 1);

    printRows(uniqueCities, "Unique cities:");
    printRows(counts, "GROUP BY city with COUNT:");

    console.log(`
DISTINCT asks for unique projected values.

GROUP BY partitions rows into groups, commonly so that aggregate functions
such as COUNT, SUM, AVG, MIN, or MAX can operate on each group.
`);
}


// ---------------------------------------------------------------------------
// Section 7: DISTINCT ON simulation
// ---------------------------------------------------------------------------

function distinctOn(rows, keyFunction) {
    /*
    PostgreSQL's DISTINCT ON keeps the first row encountered for each key.

    Therefore the input must already be ordered according to the intended
    PostgreSQL ORDER BY semantics before this function is called.
    */
    const seen = new Set();
    const result = [];

    for (const row of rows) {
        const key = JSON.stringify(keyFunction(row));

        if (!seen.has(key)) {
            seen.add(key);
            result.push(row);
        }
    }

    return result;
}

function demoDistinctOn() {
    printTitle("6. PostgreSQL DISTINCT ON");

    const logins = [
        [101, 1, "2026-09-15 08:10:00", "10.0.0.1"],
        [102, 1, "2026-09-15 09:20:00", "10.0.0.2"],
        [103, 2, "2026-09-15 07:15:00", "10.0.0.3"],
        [104, 2, "2026-09-15 11:40:00", "10.0.0.4"],
        [105, 3, "2026-09-15 10:00:00", "10.0.0.5"],
    ];

    /*
    Equivalent conceptual ordering:

    ORDER BY customer_id, event_time
    */
    const ordered = [...logins].sort((a, b) => {
        const customerComparison = a[1] - b[1];

        if (customerComparison !== 0) {
            return customerComparison;
        }

        return a[2].localeCompare(b[2]);
    });

    const firstLoginPerCustomer = distinctOn(
        ordered,
        row => row[1]
    );

    printRows(
        firstLoginPerCustomer,
        "First login per customer:"
    );

    console.log(`
PostgreSQL:

SELECT DISTINCT ON (customer_id)
       customer_id,
       event_id,
       event_time,
       ip_address
FROM login_events
ORDER BY customer_id, event_time;

DISTINCT ON is PostgreSQL-specific.
`);
}


// ---------------------------------------------------------------------------
// Section 8: Latest row per group
// ---------------------------------------------------------------------------

function demoLatestPerGroup() {
    printTitle("7. Latest row per group");

    const orders = [
        [1, 1001, "2026-09-10", 1500],
        [1, 1002, "2026-09-14", 2400],
        [2, 2001, "2026-09-12", 900],
        [2, 2002, "2026-09-15", 1200],
        [3, 3001, "2026-09-13", 1800],
    ];

    const ordered = [...orders].sort((a, b) => {
        const customerComparison = a[0] - b[0];

        if (customerComparison !== 0) {
            return customerComparison;
        }

        const dateComparison = b[2].localeCompare(a[2]);

        if (dateComparison !== 0) {
            return dateComparison;
        }

        return b[1] - a[1];
    });

    const latest = distinctOn(
        ordered,
        row => row[0]
    );

    printRows(latest, "Latest order for every customer:");

    console.log(`
PostgreSQL:

SELECT DISTINCT ON (customer_id)
       customer_id,
       order_id,
       order_date,
       total_amount
FROM orders
ORDER BY customer_id, order_date DESC, order_id DESC;

The final order_id creates a deterministic tie-breaker.
`);
}


// ---------------------------------------------------------------------------
// Section 9: DISTINCT ON composite key
// ---------------------------------------------------------------------------

function demoCompositeDistinctOn() {
    printTitle("8. DISTINCT ON with multiple expressions");

    const prices = [
        ["Delhi", "Laptop", 70000, "2026-09-10"],
        ["Delhi", "Laptop", 68000, "2026-09-14"],
        ["Delhi", "Phone", 30000, "2026-09-12"],
        ["Mumbai", "Laptop", 72000, "2026-09-11"],
        ["Mumbai", "Laptop", 69000, "2026-09-15"],
    ];

    const ordered = [...prices].sort((a, b) => {
        const city = a[0].localeCompare(b[0]);

        if (city !== 0) {
            return city;
        }

        const product = a[1].localeCompare(b[1]);

        if (product !== 0) {
            return product;
        }

        return b[3].localeCompare(a[3]);
    });

    const latest = distinctOn(
        ordered,
        row => [row[0], row[1]]
    );

    printRows(
        latest,
        "Latest price for every (city, product) combination:"
    );

    console.log(`
PostgreSQL:

SELECT DISTINCT ON (city, product)
       city,
       product,
       price,
       observed_at
FROM product_prices
ORDER BY city, product, observed_at DESC;
`);
}


// ---------------------------------------------------------------------------
// Section 10: Tie-breaking
// ---------------------------------------------------------------------------

function demoTieBreaking() {
    printTitle("9. Deterministic tie-breaking");

    const events = [
        [1, "2026-09-15 10:00:00", 900],
        [1, "2026-09-15 10:00:00", 901],
        [1, "2026-09-15 09:00:00", 899],
        [2, "2026-09-15 12:00:00", 700],
        [2, "2026-09-15 12:00:00", 701],
    ];

    const ordered = [...events].sort((a, b) => {
        const group = a[0] - b[0];

        if (group !== 0) {
            return group;
        }

        const timestamp = b[1].localeCompare(a[1]);

        if (timestamp !== 0) {
            return timestamp;
        }

        return b[2] - a[2];
    });

    const winners = distinctOn(ordered, row => row[0]);

    printRows(winners, "Selected rows:");

    console.log(`
If event_time ties, use a deterministic secondary ordering:

ORDER BY customer_id,
         event_time DESC,
         event_id DESC;

This prevents arbitrary tie selection when the business rule says which
record should win.
`);
}


// ---------------------------------------------------------------------------
// Section 11: Window-function alternative
// ---------------------------------------------------------------------------

function rowNumberPerGroup(rows, groupIndex, comparator) {
    const groups = new Map();

    for (const row of rows) {
        const key = row[groupIndex];

        if (!groups.has(key)) {
            groups.set(key, []);
        }

        groups.get(key).push(row);
    }

    const result = [];

    for (const groupRows of groups.values()) {
        const ordered = [...groupRows].sort(comparator);

        ordered.forEach((row, index) => {
            result.push({
                row,
                rowNumber: index + 1
            });
        });
    }

    return result;
}

function demoWindowAlternative() {
    printTitle("10. DISTINCT ON versus ROW_NUMBER()");

    const events = [
        [1, "Alice", "2026-09-10", 500],
        [1, "Alice", "2026-09-15", 700],
        [2, "Bob", "2026-09-12", 600],
        [2, "Bob", "2026-09-14", 800],
    ];

    const ranked = rowNumberPerGroup(
        events,
        0,
        (a, b) => b[2].localeCompare(a[2])
    );

    const winners = ranked
        .filter(item => item.rowNumber === 1)
        .map(item => item.row);

    printRows(winners, "Rows where ROW_NUMBER() = 1:");

    console.log(`
PostgreSQL alternative:

SELECT *
FROM (
    SELECT e.*,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id
               ORDER BY event_date DESC
           ) AS rn
    FROM events AS e
) ranked
WHERE rn = 1;

ROW_NUMBER() is more general because it can retain rank information and select
multiple ranked rows.
`);
}


// ---------------------------------------------------------------------------
// Section 12: Query generation with validation
// ---------------------------------------------------------------------------

function quoteIdentifier(identifier) {
    /*
    PostgreSQL identifiers can be quoted with double quotes.

    This helper is intentionally strict. It accepts ordinary SQL identifiers
    rather than arbitrary expressions. Data values should not be inserted
    through string concatenation; they should be parameterized by the
    PostgreSQL client library.
    */
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(identifier)) {
        throw new Error(`Unsafe identifier: ${identifier}`);
    }

    return `"${identifier}"`;
}

function buildDistinctOnQuery({
    table,
    groupColumns,
    selectedColumns,
    orderColumns
}) {
    if (!table || groupColumns.length === 0) {
        throw new Error("Table and at least one DISTINCT ON column are required.");
    }

    if (selectedColumns.length === 0) {
        throw new Error("At least one selected column is required.");
    }

    const group = groupColumns.map(quoteIdentifier);
    const selected = selectedColumns.map(quoteIdentifier);
    const ordering = orderColumns.map(({ column, direction = "ASC" }) => {
        const normalizedDirection = direction.toUpperCase();

        if (!["ASC", "DESC"].includes(normalizedDirection)) {
            throw new Error(`Invalid order direction: ${direction}`);
        }

        return `${quoteIdentifier(column)} ${normalizedDirection}`;
    });

    /*
    PostgreSQL requires the DISTINCT ON expressions to match the leftmost
    ORDER BY expressions. This function validates that structural rule.
    */
    if (orderColumns.length < groupColumns.length) {
        throw new Error(
            "ORDER BY must contain all DISTINCT ON expressions first."
        );
    }

    for (let index = 0; index < groupColumns.length; index += 1) {
        if (orderColumns[index].column !== groupColumns[index]) {
            throw new Error(
                "DISTINCT ON columns must form the leftmost ORDER BY prefix."
            );
        }
    }

    return [
        `SELECT DISTINCT ON (${group.join(", ")})`,
        `       ${selected.join(", ")}`,
        `FROM ${quoteIdentifier(table)}`,
        `ORDER BY ${ordering.join(", ")};`
    ].join("\n");
}

function demoQueryBuilder() {
    printTitle("11. Safe structural construction of a DISTINCT ON query");

    const query = buildDistinctOnQuery({
        table: "orders",
        groupColumns: ["customer_id"],
        selectedColumns: [
            "customer_id",
            "order_id",
            "order_date",
            "total_amount"
        ],
        orderColumns: [
            { column: "customer_id", direction: "ASC" },
            { column: "order_date", direction: "DESC" },
            { column: "order_id", direction: "DESC" }
        ]
    });

    console.log(query);

    console.log(`
This example validates identifiers and ordering structure.

In a real application, data values such as customer IDs, dates, or search
terms should be passed through PostgreSQL parameters rather than interpolated
into SQL text.
`);
}


// ---------------------------------------------------------------------------
// Section 13: Invalid DISTINCT ON structure
// ---------------------------------------------------------------------------

function demoInvalidOrdering() {
    printTitle("12. Detecting an invalid DISTINCT ON ordering");

    try {
        buildDistinctOnQuery({
            table: "events",
            groupColumns: ["customer_id"],
            selectedColumns: ["customer_id", "event_id"],
            orderColumns: [
                { column: "event_time", direction: "DESC" },
                { column: "customer_id", direction: "ASC" }
            ]
        });
    } catch (error) {
        console.log("Validation correctly rejected the query:");
        console.log(error.message);
    }
}


// ---------------------------------------------------------------------------
// Section 14: DISTINCT and joins
// ---------------------------------------------------------------------------

function demoJoinMultiplicity() {
    printTitle("13. DISTINCT does not automatically fix a JOIN");

    const customerOrders = [
        ["Alice", 1001],
        ["Alice", 1002],
        ["Bob", 2001],
    ];

    printRows(customerOrders, "One-to-many result:");

    const customersOnly = distinctRows(
        customerOrders.map(row => [row[0]])
    );

    printRows(
        customersOnly,
        "Unique customers after projection:"
    );

    console.log(`
If the requirement is to list customers once, DISTINCT is appropriate.

If the requirement is to list every order, applying DISTINCT would remove
legitimate information.

A duplicate-producing JOIN should first be investigated for cardinality,
relationship design, and join predicates.
`);
}


// ---------------------------------------------------------------------------
// Section 15: Performance concepts
// ---------------------------------------------------------------------------

function demoPerformance() {
    printTitle("14. Performance considerations");

    console.log(`
DISTINCT requires the database to determine which result rows are equivalent.

PostgreSQL may choose strategies involving sorting, hashing, indexes, or
other executor mechanisms.

Use:

EXPLAIN
SELECT DISTINCT city
FROM customers;

For actual execution information:

EXPLAIN (ANALYZE, BUFFERS)
SELECT DISTINCT city
FROM customers;

For a latest-row-per-customer query, an index such as:

CREATE INDEX ON orders (customer_id, order_date DESC, order_id DESC);

may be useful, depending on filters, table size, data distribution, selected
columns, PostgreSQL version, and the actual execution plan.

Do not assume that an index automatically makes every DISTINCT query faster.
Measure the real workload.
`);
}


// ---------------------------------------------------------------------------
// Section 16: Complexity
// ---------------------------------------------------------------------------

function demoComplexity() {
    printTitle("15. Complexity of the educational implementation");

    const rows = [
        ["A"],
        ["B"],
        ["A"],
        ["C"],
        ["B"]
    ];

    const result = distinctRows(rows);

    printRows(result);

    console.log(`
The Set-based educational implementation has approximately O(n) expected
membership behavior for n rows, with memory proportional to the number of
unique keys.

PostgreSQL has a query planner and executor that can use substantially more
complex strategies. The JavaScript implementation demonstrates logical
duplicate elimination rather than PostgreSQL internals.
`);
}


// ---------------------------------------------------------------------------
// Section 17: Edge cases
// ---------------------------------------------------------------------------

function demoEdgeCases() {
    printTitle("16. Edge cases");

    printRows(
        distinctRows([]),
        "Empty input:"
    );

    printRows(
        distinctRows([
            ["A", null],
            ["A", null],
            ["A", "X"]
        ]),
        "Composite values containing null:"
    );

    printRows(
        distinctRows([
            ["A", 1],
            ["A", 1],
            ["A", 2]
        ]),
        "Same first column but different second column:"
    );

    console.log(`
Important edge cases for PostgreSQL testing include:

- empty result sets
- NULL values
- duplicate rows
- composite duplicate keys
- tied ordering values
- missing ordering values
- very large groups
- duplicate-producing joins
- additional selected columns
`);
}


// ---------------------------------------------------------------------------
// Section 18: Practical query catalog
// ---------------------------------------------------------------------------

function showPostgreSQLQueries() {
    printTitle("17. PostgreSQL query catalog");

    const queries = {
        ordinaryDistinct: `
SELECT DISTINCT city
FROM customers;`,

        multiColumnDistinct: `
SELECT DISTINCT city, country
FROM customers;`,

        latestPerCustomer: `
SELECT DISTINCT ON (customer_id)
       customer_id,
       order_id,
       order_date,
       total_amount
FROM orders
ORDER BY customer_id,
         order_date DESC,
         order_id DESC;`,

        latestPricePerProduct: `
SELECT DISTINCT ON (product_id)
       product_id,
       product_name,
       price,
       observed_at
FROM product_prices
ORDER BY product_id,
         observed_at DESC;`,

        compositeDistinctOn: `
SELECT DISTINCT ON (customer_id, product_id)
       customer_id,
       product_id,
       price,
       observed_at
FROM product_prices
ORDER BY customer_id,
         product_id,
         observed_at DESC;`
    };

    for (const [name, query] of Object.entries(queries)) {
        console.log(`\n${name}:${query}`);
    }
}


// ---------------------------------------------------------------------------
// Section 19: Decision guide
// ---------------------------------------------------------------------------

function demoDecisionGuide() {
    printTitle("18. Construct selection guide");

    const decisions = [
        ["Unique result rows", "SELECT DISTINCT"],
        ["One preferred row per group", "SELECT DISTINCT ON"],
        ["Top N or ranked rows per group", "ROW_NUMBER() / ranking functions"],
        ["Aggregated group statistics", "GROUP BY + aggregate"],
        ["Maximum value only", "MAX()"],
        ["Maximum value plus associated row", "DISTINCT ON or ROW_NUMBER()"],
        ["Every original row", "Plain SELECT"]
    ];

    printRows(decisions);
}


// ---------------------------------------------------------------------------
// Section 20: Production checklist
// ---------------------------------------------------------------------------

function printChecklist() {
    printTitle("19. Production checklist");

    const checklist = [
        "Confirm whether duplicate rows are actually invalid.",
        "Inspect JOIN cardinality before adding DISTINCT.",
        "Use DISTINCT when the complete projected row must be unique.",
        "Use DISTINCT ON when PostgreSQL-specific one-row-per-group behavior is intended.",
        "Put DISTINCT ON expressions at the left edge of ORDER BY.",
        "Define the preferred row using DESC/ASC ordering.",
        "Add a deterministic tie-breaker when necessary.",
        "Use ROW_NUMBER() when ranking requirements are more complex.",
        "Use GROUP BY when aggregation is part of the requirement.",
        "Use EXPLAIN for performance analysis.",
        "Evaluate indexes against the complete workload.",
        "Never rely on row order without ORDER BY.",
        "Parameterize data values.",
        "Validate NULL and empty-result behavior.",
        "Test business correctness rather than only checking row counts."
    ];

    checklist.forEach(item => console.log(`[ ] ${item}`));
}


// ---------------------------------------------------------------------------
// Section 21: Main
// ---------------------------------------------------------------------------

function main() {
    printTitle("PostgreSQL DISTINCT Study Program");

    console.log(`
Core distinction:

SELECT DISTINCT
    Removes duplicate result rows.

SELECT DISTINCT ON (...)
    PostgreSQL-specific mechanism that keeps the first ordered row for each
    DISTINCT ON group.

The ORDER BY clause is therefore central to DISTINCT ON.
`);

    demoBasicDistinct();
    demoCompositeDistinct();
    demoNullDistinct();
    demoExpressionDistinct();
    demoDistinctVsGroupBy();
    demoDistinctOn();
    demoLatestPerGroup();
    demoCompositeDistinctOn();
    demoTieBreaking();
    demoWindowAlternative();
    demoQueryBuilder();
    demoInvalidOrdering();
    demoJoinMultiplicity();
    demoPerformance();
    demoComplexity();
    demoEdgeCases();
    showPostgreSQLQueries();
    demoDecisionGuide();
    printChecklist();

    printTitle("Study complete");
    console.log(
        "The program has demonstrated PostgreSQL DISTINCT and DISTINCT ON semantics."
    );
}

main();
