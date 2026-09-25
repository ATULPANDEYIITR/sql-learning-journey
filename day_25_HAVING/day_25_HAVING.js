/*
 * HAVING: Filtering Aggregated Results, WHERE vs HAVING
 * ======================================================
 *
 * This file complements the SQL/Python implementation by showing the same
 * ideas through JavaScript data processing and executable SQL construction.
 *
 * JavaScript itself does not have a built-in SQL engine. To keep this file
 * completely self-contained, the first sections implement the conceptual
 * pipeline:
 *
 *     source rows
 *         -> WHERE
 *         -> GROUP BY
 *         -> aggregate
 *         -> HAVING
 *         -> ORDER BY
 *
 * The SQL examples are represented as strings so the exact SQL distinction
 * can also be studied without requiring an external npm package.
 *
 * In a browser or Node.js application, the generated SQL could be sent to a
 * database through an appropriate database driver.
 */

"use strict";

// -----------------------------------------------------------------------------
// Utility functions
// -----------------------------------------------------------------------------

function printTitle(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}

function printRows(rows) {
    if (rows.length === 0) {
        console.log("(no rows)");
        return;
    }

    console.table(rows);
}

// -----------------------------------------------------------------------------
// Sample data
// -----------------------------------------------------------------------------

const sales = [
    { id: 1, employeeId: 4, region: "North", product: "Laptop", quantity: 4, unitPrice: 1000, discount: 0.05, date: "2026-01-05" },
    { id: 2, employeeId: 4, region: "North", product: "Monitor", quantity: 6, unitPrice: 400, discount: 0, date: "2026-01-07" },
    { id: 3, employeeId: 5, region: "South", product: "Laptop", quantity: 3, unitPrice: 1000, discount: 0.10, date: "2026-01-10" },
    { id: 4, employeeId: 5, region: "South", product: "Keyboard", quantity: 10, unitPrice: 100, discount: 0.05, date: "2026-01-12" },
    { id: 5, employeeId: 6, region: "East", product: "Laptop", quantity: 8, unitPrice: 1000, discount: 0.15, date: "2026-01-15" },
    { id: 6, employeeId: 6, region: "East", product: "Monitor", quantity: 12, unitPrice: 400, discount: 0.10, date: "2026-01-18" },
    { id: 7, employeeId: 4, region: "North", product: "Laptop", quantity: 2, unitPrice: 1000, discount: 0, date: "2026-02-02" },
    { id: 8, employeeId: 5, region: "South", product: "Monitor", quantity: 8, unitPrice: 400, discount: 0.05, date: "2026-02-04" },
    { id: 9, employeeId: 6, region: "East", product: "Keyboard", quantity: 15, unitPrice: 100, discount: 0, date: "2026-02-08" },
    { id: 10, employeeId: 4, region: "North", product: "Headset", quantity: 20, unitPrice: 80, discount: 0.10, date: "2026-02-10" },
    { id: 11, employeeId: 5, region: "South", product: "Laptop", quantity: 1, unitPrice: 1000, discount: 0, date: "2026-02-15" },
    { id: 12, employeeId: 6, region: "East", product: "Monitor", quantity: 5, unitPrice: 400, discount: 0.20, date: "2026-02-20" },
    { id: 13, employeeId: 4, region: "North", product: "Laptop", quantity: 10, unitPrice: 1000, discount: 0.05, date: "2026-03-01" },
    { id: 14, employeeId: 5, region: "South", product: "Monitor", quantity: 2, unitPrice: 400, discount: 0, date: "2026-03-03" },
    { id: 15, employeeId: 6, region: "East", product: "Keyboard", quantity: 5, unitPrice: 100, discount: 0, date: "2026-03-05" },
    { id: 16, employeeId: 4, region: "North", product: "Headset", quantity: 30, unitPrice: 80, discount: 0.05, date: "2026-03-10" },
    { id: 17, employeeId: 5, region: "South", product: "Laptop", quantity: 7, unitPrice: 1000, discount: 0.10, date: "2026-03-12" },
    { id: 18, employeeId: 6, region: "East", product: "Monitor", quantity: 4, unitPrice: 400, discount: 0, date: "2026-03-15" }
];

// -----------------------------------------------------------------------------
// Basic aggregate helpers
// -----------------------------------------------------------------------------

function revenueOf(sale) {
    return sale.quantity * sale.unitPrice * (1 - sale.discount);
}

function groupBy(rows, keyFunction) {
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

function aggregateGroups(rows) {
    const groups = groupBy(rows, row => row.region);
    const result = [];

    for (const [region, group] of groups) {
        const totalUnits = group.reduce(
            (sum, sale) => sum + sale.quantity,
            0
        );

        const revenue = group.reduce(
            (sum, sale) => sum + revenueOf(sale),
            0
        );

        result.push({
            region,
            transactionCount: group.length,
            unitsSold: totalUnits,
            revenue: Number(revenue.toFixed(2))
        });
    }

    return result;
}

// -----------------------------------------------------------------------------
// WHERE equivalent: filter individual rows
// -----------------------------------------------------------------------------

function where(rows, predicate) {
    return rows.filter(predicate);
}

// -----------------------------------------------------------------------------
// HAVING equivalent: filter already aggregated groups
// -----------------------------------------------------------------------------

function having(groups, predicate) {
    return groups.filter(predicate);
}

// -----------------------------------------------------------------------------
// SQL-like reporting pipeline
// -----------------------------------------------------------------------------

function buildRegionalReport({
    inputRows,
    rowPredicate = () => true,
    groupPredicate = () => true
}) {
    // Step 1: WHERE-like filtering.
    const filteredRows = where(inputRows, rowPredicate);

    // Step 2: GROUP BY + aggregate functions.
    const aggregatedGroups = aggregateGroups(filteredRows);

    // Step 3: HAVING-like filtering.
    const filteredGroups = having(aggregatedGroups, groupPredicate);

    // Step 4: ORDER BY.
    return filteredGroups.sort((a, b) => b.revenue - a.revenue);
}

// -----------------------------------------------------------------------------
// Beginner example
// -----------------------------------------------------------------------------

function beginnerExample() {
    printTitle("1. Basic GROUP BY and aggregation");

    const report = aggregateGroups(sales);

    printRows(report);

    console.log(
        "\nEach object represents one group, similar to one SQL GROUP BY result."
    );
}

// -----------------------------------------------------------------------------
// WHERE example
// -----------------------------------------------------------------------------

function whereExample() {
    printTitle("2. WHERE filters individual rows before grouping");

    const report = buildRegionalReport({
        inputRows: sales,
        rowPredicate: sale => sale.quantity >= 10
    });

    printRows(report);

    console.log(
        "\nThe condition quantity >= 10 is evaluated against each sale."
    );
}

// -----------------------------------------------------------------------------
// HAVING example
// -----------------------------------------------------------------------------

function havingExample() {
    printTitle("3. HAVING filters aggregated groups");

    const report = buildRegionalReport({
        inputRows: sales,
        groupPredicate: group => group.unitsSold >= 40
    });

    printRows(report);

    console.log(
        "\nThe condition unitsSold >= 40 is evaluated after grouping."
    );
}

// -----------------------------------------------------------------------------
// WHERE + HAVING
// -----------------------------------------------------------------------------

function combinedExample() {
    printTitle("4. WHERE and HAVING together");

    const report = buildRegionalReport({
        inputRows: sales,

        // Row-level condition: equivalent conceptually to WHERE.
        rowPredicate: sale => sale.date >= "2026-02-01",

        // Group-level condition: equivalent conceptually to HAVING.
        groupPredicate: group => group.revenue >= 5000
    });

    printRows(report);
}

// -----------------------------------------------------------------------------
// Multiple HAVING conditions
// -----------------------------------------------------------------------------

function multipleHavingExample() {
    printTitle("5. Multiple HAVING conditions");

    const report = buildRegionalReport({
        inputRows: sales,
        groupPredicate: group =>
            group.transactionCount >= 4 &&
            group.unitsSold >= 30 &&
            group.revenue >= 5000
    });

    printRows(report);
}

// -----------------------------------------------------------------------------
// COUNT(DISTINCT) demonstration
// -----------------------------------------------------------------------------

function distinctProductReport() {
    printTitle("6. COUNT(DISTINCT product) equivalent");

    const groups = groupBy(sales, sale => sale.employeeId);

    const report = [];

    for (const [employeeId, employeeSales] of groups) {
        const products = new Set(
            employeeSales.map(sale => sale.product)
        );

        report.push({
            employeeId,
            differentProducts: products.size
        });
    }

    const filtered = report
        .filter(row => row.differentProducts >= 3)
        .sort((a, b) => b.differentProducts - a.differentProducts);

    printRows(filtered);
}

// -----------------------------------------------------------------------------
// Conditional aggregation
// -----------------------------------------------------------------------------

function conditionalAggregationExample() {
    printTitle("7. Conditional aggregation");

    const groups = groupBy(sales, sale => sale.region);
    const report = [];

    for (const [region, regionSales] of groups) {
        const laptopUnits = regionSales.reduce(
            (sum, sale) =>
                sum + (sale.product === "Laptop" ? sale.quantity : 0),
            0
        );

        const monitorUnits = regionSales.reduce(
            (sum, sale) =>
                sum + (sale.product === "Monitor" ? sale.quantity : 0),
            0
        );

        report.push({
            region,
            laptopUnits,
            monitorUnits
        });
    }

    const filtered = report
        .filter(row => row.laptopUnits >= 5)
        .sort((a, b) => b.laptopUnits - a.laptopUnits);

    printRows(filtered);
}

// -----------------------------------------------------------------------------
// Null semantics
// -----------------------------------------------------------------------------

function nullAggregationExample() {
    printTitle("8. JavaScript null versus SQL NULL");

    const values = [100, null, 200, null];

    const nonNullValues = values.filter(value => value !== null);

    const sum = nonNullValues.reduce(
        (total, value) => total + value,
        0
    );

    console.log({
        originalValues: values,
        nonNullCount: nonNullValues.length,
        sumIgnoringNull: sum
    });

    console.log(
        "\nJavaScript does not automatically reproduce every SQL NULL rule."
    );
    console.log(
        "Database applications should let the SQL engine perform SQL aggregation."
    );
}

// -----------------------------------------------------------------------------
// SQL examples
// -----------------------------------------------------------------------------

const sqlExamples = {
    whereFiltersRows: `
SELECT region, SUM(quantity) AS total_units
FROM sales
WHERE quantity >= 10
GROUP BY region;
`,

    havingFiltersGroups: `
SELECT region, SUM(quantity) AS total_units
FROM sales
GROUP BY region
HAVING SUM(quantity) >= 40;
`,

    whereAndHaving: `
SELECT
    region,
    COUNT(*) AS transaction_count,
    SUM(quantity) AS total_units
FROM sales
WHERE sale_date >= '2026-02-01'
GROUP BY region
HAVING SUM(quantity) >= 30;
`,

    joinWhereHaving: `
SELECT
    d.department_name,
    COUNT(e.employee_id) AS active_employee_count,
    AVG(e.salary) AS average_salary
FROM departments AS d
JOIN employees AS e
    ON e.department_id = d.department_id
WHERE e.active = 1
GROUP BY d.department_id, d.department_name
HAVING COUNT(e.employee_id) >= 2
ORDER BY active_employee_count DESC;
`
};

function showSqlExamples() {
    printTitle("9. SQL syntax represented in JavaScript");

    for (const [name, sql] of Object.entries(sqlExamples)) {
        console.log(`\n${name}:`);
        console.log(sql.trim());
    }
}

// -----------------------------------------------------------------------------
// Parameterized SQL
// -----------------------------------------------------------------------------

function demonstrateParameterizedSql() {
    printTitle("10. Parameterized SQL design");

    const minimumUnits = 40;

    const sql = `
SELECT
    region,
    SUM(quantity) AS total_units
FROM sales
GROUP BY region
HAVING SUM(quantity) >= ?
ORDER BY total_units DESC;
`.trim();

    console.log(sql);
    console.log("\nParameter value:", minimumUnits);

    console.log(
        "\nUse a database driver's parameter-binding mechanism rather than"
        + " concatenating untrusted values into SQL."
    );
}

// -----------------------------------------------------------------------------
// Query builder case study
// -----------------------------------------------------------------------------

class SalesQueryBuilder {
    constructor() {
        this.conditions = [];
        this.parameters = [];
        this.havingConditions = [];
        this.havingParameters = [];
    }

    where(condition, parameter) {
        this.conditions.push(condition);

        if (parameter !== undefined) {
            this.parameters.push(parameter);
        }

        return this;
    }

    having(condition, parameter) {
        this.havingConditions.push(condition);

        if (parameter !== undefined) {
            this.havingParameters.push(parameter);
        }

        return this;
    }

    build() {
        const whereClause =
            this.conditions.length > 0
                ? `WHERE ${this.conditions.join(" AND ")}`
                : "";

        const havingClause =
            this.havingConditions.length > 0
                ? `HAVING ${this.havingConditions.join(" AND ")}`
                : "";

        return {
            sql: `
SELECT
    region,
    COUNT(*) AS transaction_count,
    SUM(quantity) AS total_units,
    SUM(quantity * unit_price * (1 - discount)) AS revenue
FROM sales
${whereClause}
GROUP BY region
${havingClause}
ORDER BY revenue DESC;
`.trim(),

            parameters: [
                ...this.parameters,
                ...this.havingParameters
            ]
        };
    }
}

function demonstrateQueryBuilder() {
    printTitle("11. Building a parameterized analytical query");

    const query = new SalesQueryBuilder()
        .where("sale_date >= ?", "2026-02-01")
        .having(
            "SUM(quantity * unit_price * (1 - discount)) >= ?",
            5000
        )
        .build();

    console.log(query.sql);
    console.log("\nBound parameters:", query.parameters);

    console.log(
        "\nThe builder keeps row-level predicates and group-level predicates"
        + " conceptually separate."
    );
}

// -----------------------------------------------------------------------------
// Performance discussion through an executable comparison
// -----------------------------------------------------------------------------

function performanceConsideration() {
    printTitle("12. Performance consideration");

    const threshold = 10;

    console.time("Filter before grouping");

    const filteredFirst = sales.filter(
        sale => sale.quantity >= threshold
    );

    const groupedAfterFilter = aggregateGroups(filteredFirst);

    console.timeEnd("Filter before grouping");

    console.time("Group before filtering");

    const allGroups = aggregateGroups(sales);
    const filteredGroups = allGroups.filter(
        group => group.unitsSold >= threshold
    );

    console.timeEnd("Group before filtering");

    console.log({
        whereStyleResult: groupedAfterFilter.length,
        havingStyleResult: filteredGroups.length
    });

    console.log(
        "\nThese operations answer different questions and should not be"
        + " treated as interchangeable performance rewrites."
    );
}

// -----------------------------------------------------------------------------
// Edge cases
// -----------------------------------------------------------------------------

function edgeCases() {
    printTitle("13. Edge cases");

    const empty = [];

    const emptyGroups = aggregateGroups(empty);

    console.log("Empty input:", emptyGroups);

    const oneSale = [
        {
            id: 999,
            employeeId: 1,
            region: "West",
            product: "Laptop",
            quantity: 1,
            unitPrice: 1000,
            discount: 0,
            date: "2026-04-01"
        }
    ];

    console.log("\nOne-row input:");
    printRows(aggregateGroups(oneSale));

    console.log("\nImpossible HAVING threshold:");
    printRows(
        having(
            aggregateGroups(sales),
            group => group.unitsSold >= 1000000
        )
    );
}

// -----------------------------------------------------------------------------
// Assertions
// -----------------------------------------------------------------------------

function runAssertions() {
    printTitle("14. Executable correctness checks");

    const groups = aggregateGroups(sales);

    const north = groups.find(group => group.region === "North");
    const south = groups.find(group => group.region === "South");
    const east = groups.find(group => group.region === "East");

    console.assert(north.unitsSold === 72);
    console.assert(south.unitsSold === 31);
    console.assert(east.unitsSold === 49);

    const qualified = groups.filter(group => group.unitsSold >= 40);

    console.assert(qualified.length === 2);
    console.assert(
        qualified.every(group => group.unitsSold >= 40)
    );

    console.log("All JavaScript assertions passed.");
}

// -----------------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------------

function main() {
    printTitle("HAVING: Filtering Aggregated Results");

    console.log(
        "Core distinction: WHERE filters rows; HAVING filters groups."
    );

    beginnerExample();
    whereExample();
    havingExample();
    combinedExample();
    multipleHavingExample();
    distinctProductReport();
    conditionalAggregationExample();
    nullAggregationExample();
    showSqlExamples();
    demonstrateParameterizedSql();
    demonstrateQueryBuilder();
    performanceConsideration();
    edgeCases();
    runAssertions();

    printTitle("Study program completed");
}

main();
