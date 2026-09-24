"use strict";

/*
 * GROUP BY: Grouping Rows, Grouped Calculations, and Grouping Multiple Columns
 *
 * This self-contained JavaScript program demonstrates SQL-style GROUP BY
 * concepts using ordinary JavaScript data structures.
 *
 * The examples cover:
 * - grouping rows
 * - COUNT(*)
 * - COUNT(column)
 * - SUM
 * - AVG
 * - MIN and MAX
 * - multiple grouping columns
 * - WHERE versus HAVING
 * - conditional aggregation
 * - DISTINCT counts
 * - NULL behavior
 * - sorting grouped results
 * - Top-N groups
 * - rollup-style totals
 * - reusable aggregation functions
 * - asynchronous grouped analysis
 * - validation
 * - performance considerations
 * - SQL generation
 *
 * The program can run directly in Node.js without external packages.
 */


// -----------------------------------------------------------------------------
// Section 1: Sample data
// -----------------------------------------------------------------------------

const sales = [
    {
        orderId: 1001,
        customer: "Asha",
        region: "North",
        city: "Delhi",
        category: "Electronics",
        product: "Laptop",
        salesperson: "Ravi",
        quantity: 2,
        unitPrice: 75000,
        discount: 0.05,
        status: "Completed"
    },
    {
        orderId: 1002,
        customer: "Bharat",
        region: "North",
        city: "Lucknow",
        category: "Furniture",
        product: "Chair",
        salesperson: "Neha",
        quantity: 5,
        unitPrice: 4500,
        discount: 0.10,
        status: "Completed"
    },
    {
        orderId: 1003,
        customer: "Charu",
        region: "South",
        city: "Bengaluru",
        category: "Electronics",
        product: "Phone",
        salesperson: "Ravi",
        quantity: 3,
        unitPrice: 30000,
        discount: 0,
        status: "Completed"
    },
    {
        orderId: 1004,
        customer: "Dev",
        region: "West",
        city: "Mumbai",
        category: "Office",
        product: "Desk",
        salesperson: "Meera",
        quantity: 4,
        unitPrice: 12000,
        discount: 0.15,
        status: "Cancelled"
    },
    {
        orderId: 1005,
        customer: "Esha",
        region: "North",
        city: "Delhi",
        category: "Electronics",
        product: "Monitor",
        salesperson: "Ravi",
        quantity: 4,
        unitPrice: 18000,
        discount: 0.08,
        status: "Completed"
    },
    {
        orderId: 1006,
        customer: "Farhan",
        region: "East",
        city: "Kolkata",
        category: "Furniture",
        product: "Table",
        salesperson: "Neha",
        quantity: 2,
        unitPrice: 16000,
        discount: 0.05,
        status: "Completed"
    },
    {
        orderId: 1007,
        customer: "Gita",
        region: "South",
        city: "Chennai",
        category: "Office",
        product: "Printer",
        salesperson: "Meera",
        quantity: 2,
        unitPrice: 22000,
        discount: 0.12,
        status: "Completed"
    },
    {
        orderId: 1008,
        customer: "Hari",
        region: "West",
        city: "Pune",
        category: "Electronics",
        product: "Tablet",
        salesperson: "Ravi",
        quantity: 6,
        unitPrice: 25000,
        discount: 0.07,
        status: "Completed"
    },
    {
        orderId: 1009,
        customer: "Isha",
        region: "North",
        city: "Lucknow",
        category: "Office",
        product: "Printer",
        salesperson: "Neha",
        quantity: 1,
        unitPrice: 22000,
        discount: 0,
        status: "Completed"
    },
    {
        orderId: 1010,
        customer: "Jai",
        region: "South",
        city: "Hyderabad",
        category: "Furniture",
        product: "Chair",
        salesperson: "Meera",
        quantity: 10,
        unitPrice: 4500,
        discount: 0.20,
        status: "Completed"
    },
    {
        orderId: 1011,
        customer: "Kiran",
        region: null,
        city: "Jaipur",
        category: "Electronics",
        product: "Keyboard",
        salesperson: "Ravi",
        quantity: 8,
        unitPrice: 2500,
        discount: 0.03,
        status: "Completed"
    },
    {
        orderId: 1012,
        customer: "Lata",
        region: "East",
        city: "Patna",
        category: null,
        product: "Desk",
        salesperson: "Neha",
        quantity: 3,
        unitPrice: 12000,
        discount: 0.10,
        status: "Completed"
    }
];


// -----------------------------------------------------------------------------
// Section 2: Utility functions
// -----------------------------------------------------------------------------

function printTitle(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}


function money(value) {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}


function netSales(row) {
    return row.quantity * row.unitPrice * (1 - row.discount);
}


function normalizeGroupValue(value) {
    /*
     * JavaScript Map supports null as a key, so it can naturally represent
     * the SQL idea that NULL values belong to one grouping category.
     */
    return value === null || value === undefined ? "NULL" : value;
}


function printObjects(rows) {
    if (rows.length === 0) {
        console.log("(no rows)");
        return;
    }

    console.table(rows);
}


// -----------------------------------------------------------------------------
// Section 3: Basic filtering
// -----------------------------------------------------------------------------

function where(rows, predicate) {
    /*
     * WHERE operates on individual rows before grouping.
     */
    return rows.filter(predicate);
}


// -----------------------------------------------------------------------------
// Section 4: Generic grouping
// -----------------------------------------------------------------------------

function groupBy(rows, keyFunction) {
    /*
     * Map is an efficient general-purpose representation for grouped data.
     *
     * Each unique key maps to an array containing all rows in that group.
     */
    const groups = new Map();

    for (const row of rows) {
        const key = keyFunction(row);

        if (!groups.has(key)) {
            groups.set(key, []);
        }

        groups.get(key).push(row);
    }

    return groups;
}


function groupByColumn(rows, column) {
    return groupBy(rows, row => normalizeGroupValue(row[column]));
}


function compositeKey(values) {
    /*
     * JSON.stringify creates an unambiguous representation for simple
     * primitive grouping values and avoids accidental delimiter collisions.
     */
    return JSON.stringify(values);
}


function groupByColumns(rows, columns) {
    const groups = new Map();

    for (const row of rows) {
        const values = columns.map(column =>
            normalizeGroupValue(row[column])
        );

        const key = compositeKey(values);

        if (!groups.has(key)) {
            groups.set(key, {
                values,
                rows: []
            });
        }

        groups.get(key).rows.push(row);
    }

    return groups;
}


// -----------------------------------------------------------------------------
// Section 5: Aggregate functions
// -----------------------------------------------------------------------------

function countStar(rows) {
    /*
     * COUNT(*) counts every row.
     */
    return rows.length;
}


function countColumn(rows, column) {
    /*
     * COUNT(column) ignores null and undefined values.
     */
    return rows.filter(row =>
        row[column] !== null &&
        row[column] !== undefined
    ).length;
}


function sum(rows, column) {
    const values = rows
        .map(row => row[column])
        .filter(value => value !== null && value !== undefined);

    if (values.length === 0) {
        return null;
    }

    return values.reduce((total, value) => total + value, 0);
}


function average(rows, column) {
    const values = rows
        .map(row => row[column])
        .filter(value => value !== null && value !== undefined);

    if (values.length === 0) {
        return null;
    }

    return values.reduce((total, value) => total + value, 0) / values.length;
}


function minimum(rows, column) {
    const values = rows
        .map(row => row[column])
        .filter(value => value !== null && value !== undefined);

    return values.length === 0 ? null : Math.min(...values);
}


function maximum(rows, column) {
    const values = rows
        .map(row => row[column])
        .filter(value => value !== null && value !== undefined);

    return values.length === 0 ? null : Math.max(...values);
}


// -----------------------------------------------------------------------------
// Section 6: Simple GROUP BY
// -----------------------------------------------------------------------------

function demonstrateSingleColumnGrouping() {
    printTitle("GROUP BY one column");

    const groups = groupByColumn(sales, "region");
    const results = [];

    for (const [region, rows] of groups) {
        results.push({
            region,
            orders: countStar(rows),
            customersWithValue: countColumn(rows, "customer"),
            totalQuantity: sum(rows, "quantity"),
            averageQuantity: average(rows, "quantity"),
            minimumQuantity: minimum(rows, "quantity"),
            maximumQuantity: maximum(rows, "quantity")
        });
    }

    results.sort((a, b) =>
        String(a.region).localeCompare(String(b.region))
    );

    printObjects(results);
}


// -----------------------------------------------------------------------------
// Section 7: Multiple-column GROUP BY
// -----------------------------------------------------------------------------

function demonstrateMultipleColumnGrouping() {
    printTitle("GROUP BY multiple columns");

    const groups = groupByColumns(
        sales,
        ["region", "category"]
    );

    const results = [];

    for (const { values, rows } of groups.values()) {
        const [region, category] = values;

        results.push({
            region,
            category,
            orders: countStar(rows),
            totalQuantity: sum(rows, "quantity"),
            totalSales: rows.reduce(
                (total, row) => total + netSales(row),
                0
            )
        });
    }

    results.sort((a, b) =>
        String(a.region).localeCompare(String(b.region)) ||
        String(a.category).localeCompare(String(b.category))
    );

    printObjects(
        results.map(row => ({
            ...row,
            totalSales: money(row.totalSales)
        }))
    );

    console.log("\nComposite grouping means that the pair");
    console.log("(region, category) identifies the group.");
}


// -----------------------------------------------------------------------------
// Section 8: WHERE versus HAVING
// -----------------------------------------------------------------------------

function having(rows, predicate) {
    /*
     * HAVING operates on grouped/aggregated rows.
     */
    return rows.filter(predicate);
}


function demonstrateWhereAndHaving() {
    printTitle("WHERE versus HAVING");

    const completed = where(
        sales,
        row => row.status === "Completed"
    );

    const groups = groupByColumn(completed, "region");

    const aggregates = [];

    for (const [region, rows] of groups) {
        aggregates.push({
            region,
            orders: rows.length,
            totalQuantity: sum(rows, "quantity"),
            totalSales: rows.reduce(
                (total, row) => total + netSales(row),
                0
            )
        });
    }

    const qualified = having(
        aggregates,
        result => result.totalQuantity >= 5
    );

    qualified.sort(
        (a, b) => b.totalQuantity - a.totalQuantity
    );

    printObjects(
        qualified.map(row => ({
            ...row,
            totalSales: money(row.totalSales)
        }))
    );

    console.log("\nProcessing model:");
    console.log("1. WHERE filters source rows.");
    console.log("2. GROUP BY creates groups.");
    console.log("3. Aggregates calculate group values.");
    console.log("4. HAVING filters those groups.");
    console.log("5. ORDER BY sorts the resulting groups.");
}


// -----------------------------------------------------------------------------
// Section 9: COUNT(*) versus COUNT(column)
// -----------------------------------------------------------------------------

function demonstrateCountDifference() {
    printTitle("COUNT(*) versus COUNT(column)");

    const groups = groupByColumn(sales, "region");
    const results = [];

    for (const [region, rows] of groups) {
        results.push({
            region,
            countStar: countStar(rows),
            countCategory: countColumn(rows, "category"),
            countCity: countColumn(rows, "city")
        });
    }

    printObjects(results);
}


// -----------------------------------------------------------------------------
// Section 10: Conditional aggregation
// -----------------------------------------------------------------------------

function demonstrateConditionalAggregation() {
    printTitle("Conditional aggregation");

    const groups = groupByColumn(sales, "region");
    const results = [];

    for (const [region, rows] of groups) {
        const completed = rows.filter(
            row => row.status === "Completed"
        );

        const cancelled = rows.filter(
            row => row.status === "Cancelled"
        );

        const completedSales = completed.reduce(
            (total, row) => total + netSales(row),
            0
        );

        results.push({
            region,
            completedOrders: completed.length,
            cancelledOrders: cancelled.length,
            completedSales: money(completedSales)
        });
    }

    printObjects(results);

    console.log(
        "\nThis models SQL expressions such as "
        "SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END)."
    );
}


// -----------------------------------------------------------------------------
// Section 11: DISTINCT counts
// -----------------------------------------------------------------------------

function demonstrateDistinctCounts() {
    printTitle("COUNT(DISTINCT ...)");

    const groups = groupByColumn(sales, "region");
    const results = [];

    for (const [region, rows] of groups) {
        const customers = new Set(
            rows
                .map(row => row.customer)
                .filter(value => value !== null && value !== undefined)
        );

        const products = new Set(
            rows
                .map(row => row.product)
                .filter(value => value !== null && value !== undefined)
        );

        results.push({
            region,
            uniqueCustomers: customers.size,
            uniqueProducts: products.size
        });
    }

    printObjects(results);
}


// -----------------------------------------------------------------------------
// Section 12: Top-N grouped results
// -----------------------------------------------------------------------------

function demonstrateTopGroups() {
    printTitle("Top-N groups");

    const completed = where(
        sales,
        row => row.status === "Completed"
    );

    const groups = groupByColumn(
        completed,
        "category"
    );

    const results = [];

    for (const [category, rows] of groups) {
        results.push({
            category,
            orders: rows.length,
            sales: rows.reduce(
                (total, row) => total + netSales(row),
                0
            )
        });
    }

    results.sort((a, b) => b.sales - a.sales);

    printObjects(
        results.slice(0, 2).map(row => ({
            category: row.category,
            orders: row.orders,
            sales: money(row.sales)
        }))
    );
}


// -----------------------------------------------------------------------------
// Section 13: Weighted averages
// -----------------------------------------------------------------------------

function demonstrateAveragePitfall() {
    printTitle("Ordinary average versus weighted average");

    const groups = groupByColumn(sales, "region");
    const results = [];

    for (const [region, rows] of groups) {
        const ordinaryAverage = average(rows, "unitPrice");

        const totalQuantity = rows.reduce(
            (total, row) => total + row.quantity,
            0
        );

        const weightedAverage = totalQuantity === 0
            ? null
            : rows.reduce(
                (total, row) =>
                    total + row.quantity * row.unitPrice,
                0
            ) / totalQuantity;

        results.push({
            region,
            ordinaryAverage:
                ordinaryAverage === null
                    ? null
                    : money(ordinaryAverage),
            weightedAverage:
                weightedAverage === null
                    ? null
                    : money(weightedAverage)
        });
    }

    printObjects(results);
}


// -----------------------------------------------------------------------------
// Section 14: Rollup-style analysis
// -----------------------------------------------------------------------------

function demonstrateRollup() {
    printTitle("ROLLUP-style totals");

    const completed = where(
        sales,
        row => row.status === "Completed"
    );

    const detailGroups = groupByColumns(
        completed,
        ["region", "category"]
    );

    const output = [];

    for (const { values, rows } of detailGroups.values()) {
        const [region, category] = values;

        output.push({
            level: "region + category",
            region,
            category,
            orders: rows.length,
            sales: rows.reduce(
                (total, row) => total + netSales(row),
                0
            )
        });
    }

    const regionGroups = groupByColumn(
        completed,
        "region"
    );

    for (const [region, rows] of regionGroups) {
        output.push({
            level: "region total",
            region,
            category: null,
            orders: rows.length,
            sales: rows.reduce(
                (total, row) => total + netSales(row),
                0
            )
        });
    }

    output.push({
        level: "grand total",
        region: null,
        category: null,
        orders: completed.length,
        sales: completed.reduce(
            (total, row) => total + netSales(row),
            0
        )
    });

    printObjects(
        output.map(row => ({
            ...row,
            sales: money(row.sales)
        }))
    );

    console.log(
        "\nThis manually represents the hierarchical totals produced "
        + "by concepts such as SQL ROLLUP."
    );
}


// -----------------------------------------------------------------------------
// Section 15: Reusable aggregation engine
// -----------------------------------------------------------------------------

function aggregateQuery({
    rows,
    groupColumns,
    aggregates,
    rowFilter = null,
    groupFilter = null
}) {
    if (!Array.isArray(rows)) {
        throw new TypeError("rows must be an array.");
    }

    if (!Array.isArray(groupColumns) || groupColumns.length === 0) {
        throw new Error("At least one group column is required.");
    }

    for (const column of groupColumns) {
        if (rows.length > 0 && !(column in rows[0])) {
            throw new Error(`Unknown grouping column: ${column}`);
        }
    }

    const filteredRows = rowFilter
        ? rows.filter(rowFilter)
        : rows;

    const groups = groupByColumns(
        filteredRows,
        groupColumns
    );

    const results = [];

    for (const { values, rows: groupedRows } of groups.values()) {
        const result = {};

        groupColumns.forEach(
            (column, index) => {
                result[column] = values[index];
            }
        );

        for (const aggregate of aggregates) {
            result[aggregate.name] =
                aggregate.calculate(groupedRows);
        }

        results.push(result);
    }

    return groupFilter
        ? results.filter(groupFilter)
        : results;
}


function demonstrateReusableEngine() {
    printTitle("Reusable aggregation engine");

    const results = aggregateQuery({
        rows: sales,
        groupColumns: ["region", "salesperson"],
        rowFilter: row => row.status === "Completed",
        aggregates: [
            {
                name: "orders",
                calculate: rows => rows.length
            },
            {
                name: "units",
                calculate: rows =>
                    rows.reduce(
                        (total, row) => total + row.quantity,
                        0
                    )
            },
            {
                name: "sales",
                calculate: rows =>
                    rows.reduce(
                        (total, row) => total + netSales(row),
                        0
                    )
            }
        ],
        groupFilter: result => result.sales >= 10000
    });

    results.sort((a, b) => b.sales - a.sales);

    printObjects(
        results.map(row => ({
            ...row,
            sales: money(row.sales)
        }))
    );
}


// -----------------------------------------------------------------------------
// Section 16: NULL behavior
// -----------------------------------------------------------------------------

function demonstrateNullBehavior() {
    printTitle("NULL behavior");

    const rows = [
        { department: "IT", salary: 100 },
        { department: "IT", salary: 200 },
        { department: null, salary: 300 },
        { department: null, salary: 400 },
        { department: "HR", salary: null }
    ];

    const groups = groupByColumn(
        rows,
        "department"
    );

    const results = [];

    for (const [department, groupedRows] of groups) {
        results.push({
            department,
            countStar: countStar(groupedRows),
            countSalary: countColumn(groupedRows, "salary"),
            sumSalary: sum(groupedRows, "salary"),
            averageSalary: average(groupedRows, "salary")
        });
    }

    printObjects(results);

    console.log("\nKey behavior:");
    console.log("- NULL grouping values are treated as one group.");
    console.log("- COUNT(*) counts rows.");
    console.log("- COUNT(salary) ignores NULL salaries.");
    console.log("- SUM and AVG ignore NULL salary values.");
}


// -----------------------------------------------------------------------------
// Section 17: Join multiplication
// -----------------------------------------------------------------------------

function demonstrateJoinMultiplication() {
    printTitle("Join multiplication and incorrect grouped totals");

    const orders = [
        { orderId: 1, customerId: 10, amount: 100 },
        { orderId: 2, customerId: 20, amount: 200 }
    ];

    const customerTags = [
        { customerId: 10, tag: "VIP" },
        { customerId: 10, tag: "Wholesale" },
        { customerId: 20, tag: "Retail" }
    ];

    const joined = [];

    for (const order of orders) {
        for (const tag of customerTags) {
            if (order.customerId === tag.customerId) {
                joined.push({
                    ...order,
                    tag: tag.tag
                });
            }
        }
    }

    const originalTotal = orders.reduce(
        (total, row) => total + row.amount,
        0
    );

    const joinedTotal = joined.reduce(
        (total, row) => total + row.amount,
        0
    );

    console.log("Original rows:", orders.length);
    console.log("Joined rows:", joined.length);
    console.log("Original total:", money(originalTotal));
    console.log("Naively aggregated joined total:", money(joinedTotal));

    console.log(
        "\nThe one-to-many relationship duplicates the first order. "
        + "A grouped financial query must account for join cardinality."
    );
}


// -----------------------------------------------------------------------------
// Section 18: SQL generation
// -----------------------------------------------------------------------------

function buildGroupBySQL({
    table,
    groupColumns,
    aggregateExpressions,
    whereClause = null,
    havingClause = null,
    orderByClause = null
}) {
    if (!table) {
        throw new Error("Table name cannot be empty.");
    }

    if (!Array.isArray(groupColumns) || groupColumns.length === 0) {
        throw new Error("At least one group column is required.");
    }

    let sql =
        "SELECT " +
        [...groupColumns, ...aggregateExpressions].join(", ") +
        ` FROM ${table}`;

    if (whereClause) {
        sql += ` WHERE ${whereClause}`;
    }

    sql += ` GROUP BY ${groupColumns.join(", ")}`;

    if (havingClause) {
        sql += ` HAVING ${havingClause}`;
    }

    if (orderByClause) {
        sql += ` ORDER BY ${orderByClause}`;
    }

    return sql + ";";
}


function demonstrateSQLGeneration() {
    printTitle("SQL generation");

    const query = buildGroupBySQL({
        table: "sales",
        groupColumns: ["region", "category"],
        aggregateExpressions: [
            "COUNT(*) AS orders",
            "SUM(quantity) AS units",
            "SUM(quantity * unit_price * (1 - discount)) AS net_sales"
        ],
        whereClause: "status = 'Completed'",
        havingClause:
            "SUM(quantity * unit_price * (1 - discount)) >= 10000",
        orderByClause: "net_sales DESC"
    });

    console.log(query);

    console.log(
        "\nProduction rule: user-provided values should be parameterized. "
        + "Identifiers should be validated against trusted allowlists."
    );
}


// -----------------------------------------------------------------------------
// Section 19: Asynchronous grouped processing
// -----------------------------------------------------------------------------

async function loadSalesData() {
    /*
     * A real application could fetch data from an API or database.
     * Here, Promise.resolve models asynchronous I/O without requiring
     * an external service.
     */
    return Promise.resolve(sales);
}


async function demonstrateAsyncGrouping() {
    printTitle("Asynchronous grouped analysis");

    const rows = await loadSalesData();

    const completed = rows.filter(
        row => row.status === "Completed"
    );

    const groups = groupByColumn(
        completed,
        "salesperson"
    );

    const results = [];

    for (const [salesperson, groupedRows] of groups) {
        results.push({
            salesperson,
            orders: groupedRows.length,
            sales: groupedRows.reduce(
                (total, row) => total + netSales(row),
                0
            )
        });
    }

    results.sort((a, b) => b.sales - a.sales);

    printObjects(
        results.map(row => ({
            salesperson: row.salesperson,
            orders: row.orders,
            sales: money(row.sales)
        }))
    );
}


// -----------------------------------------------------------------------------
// Section 20: Performance demonstration
// -----------------------------------------------------------------------------

function performanceDemonstration() {
    printTitle("Performance considerations");

    const rows = Array.from(
        { length: 100000 },
        (_, index) => ({
            id: index,
            region: `Region-${index % 10}`,
            amount: (index % 1000) + 1
        })
    );

    const start = performance.now();

    const groups = groupByColumn(
        rows,
        "region"
    );

    const aggregates = [];

    for (const [region, groupedRows] of groups) {
        aggregates.push({
            region,
            rows: groupedRows.length,
            amount: groupedRows.reduce(
                (total, row) => total + row.amount,
                0
            )
        });
    }

    const elapsed = performance.now() - start;

    console.log("Input rows:", rows.length);
    console.log("Number of groups:", groups.size);
    console.log(
        `Grouping and aggregation time: ${elapsed.toFixed(2)} ms`
    );

    console.log(
        "\nThis implementation uses hash-style grouping with Map. "
        + "Expected grouping work is approximately O(n), while memory "
        + "usage grows with the number of stored rows and groups."
    );
}


// -----------------------------------------------------------------------------
// Section 21: Advanced sales case study
// -----------------------------------------------------------------------------

function runSalesCaseStudy() {
    printTitle("Advanced sales analysis");

    const results = aggregateQuery({
        rows: sales,
        groupColumns: ["region", "category"],
        rowFilter: row => row.status === "Completed",
        aggregates: [
            {
                name: "orders",
                calculate: rows => rows.length
            },
            {
                name: "units",
                calculate: rows =>
                    rows.reduce(
                        (total, row) => total + row.quantity,
                        0
                    )
            },
            {
                name: "grossSales",
                calculate: rows =>
                    rows.reduce(
                        (total, row) =>
                            total + row.quantity * row.unitPrice,
                        0
                    )
            },
            {
                name: "netSales",
                calculate: rows =>
                    rows.reduce(
                        (total, row) => total + netSales(row),
                        0
                    )
            },
            {
                name: "averageOrderValue",
                calculate: rows => {
                    const total = rows.reduce(
                        (sumValue, row) =>
                            sumValue + netSales(row),
                        0
                    );

                    return total / rows.length;
                }
            },
            {
                name: "uniqueCustomers",
                calculate: rows =>
                    new Set(
                        rows
                            .map(row => row.customer)
                            .filter(
                                value =>
                                    value !== null &&
                                    value !== undefined
                            )
                    ).size
            }
        ],
        groupFilter: result => result.netSales >= 10000
    });

    results.sort(
        (a, b) => b.netSales - a.netSales
    );

    printObjects(
        results.map(row => ({
            region: row.region,
            category: row.category,
            orders: row.orders,
            units: row.units,
            grossSales: money(row.grossSales),
            netSales: money(row.netSales),
            averageOrderValue: money(row.averageOrderValue),
            uniqueCustomers: row.uniqueCustomers
        }))
    );
}


// -----------------------------------------------------------------------------
// Section 22: Main asynchronous program
// -----------------------------------------------------------------------------

async function main() {
    printTitle("GROUP BY: JavaScript study program");

    console.log(
        "JavaScript models GROUP BY with Map, arrays, Set, "
        + "filtering, reduction, sorting, and reusable functions."
    );

    demonstrateSingleColumnGrouping();
    demonstrateMultipleColumnGrouping();
    demonstrateCountDifference();
    demonstrateWhereAndHaving();
    demonstrateConditionalAggregation();
    demonstrateDistinctCounts();
    demonstrateTopGroups();
    demonstrateAveragePitfall();
    demonstrateRollup();
    demonstrateReusableEngine();
    demonstrateNullBehavior();
    demonstrateJoinMultiplication();
    demonstrateSQLGeneration();
    await demonstrateAsyncGrouping();
    performanceDemonstration();
    runSalesCaseStudy();

    printTitle("Study checklist");

    const checklist = [
        "GROUP BY partitions rows according to one or more grouping keys.",
        "COUNT(*) counts rows, while COUNT(column) ignores NULL values.",
        "SUM and AVG calculate values inside each group.",
        "Multiple columns form a composite group key.",
        "WHERE filters rows before grouping.",
        "HAVING filters groups after aggregation.",
        "COUNT(DISTINCT column) counts unique non-NULL values.",
        "Conditional aggregation creates multiple metrics from one grouped scan.",
        "Join multiplication can cause incorrect totals.",
        "ORDER BY is required when deterministic grouped ordering matters.",
        "Map is a natural JavaScript structure for hash-style grouping.",
        "Set is useful for DISTINCT-style calculations.",
        "Large grouped datasets require attention to memory and execution time."
    ];

    checklist.forEach(
        (item, index) =>
            console.log(`${String(index + 1).padStart(2, "0")}. ${item}`)
    );

    printTitle("Program completed");
}


main().catch(error => {
    console.error("Program failed:", error.message);
    process.exitCode = 1;
});
