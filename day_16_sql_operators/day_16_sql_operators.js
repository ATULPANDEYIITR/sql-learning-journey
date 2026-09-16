/*
 * SQL Operators: Arithmetic, comparison, logical, BETWEEN, IN, NOT, LIKE
 *
 * This self-contained JavaScript file complements the SQL-focused Python
 * study by demonstrating:
 *
 * - SQL operator syntax as executable query strings
 * - JavaScript equivalents of common SQL expressions
 * - parameterized-query construction
 * - dynamic filter construction
 * - SQL three-valued-logic concepts
 * - LIKE pattern matching through a small JavaScript evaluator
 * - realistic reporting/query generation
 *
 * No external npm package is required.
 *
 * Run with:
 *     node sql_operators.js
 *
 * The file intentionally does not depend on an external database driver.
 * The Python implementation uses SQLite for actual SQL execution, while this
 * JavaScript implementation concentrates on application-side SQL construction
 * and on making operator semantics explicit.
 */

"use strict";


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

    const columns = Object.keys(rows[0]);
    console.log(columns.join(" | "));
    console.log("-".repeat(78));

    for (const row of rows) {
        console.log(
            columns
                .map((column) => row[column] === null ? "NULL" : String(row[column]))
                .join(" | ")
        );
    }
}


/*
 * A small employee dataset allows us to demonstrate the meaning of SQL
 * operators using ordinary JavaScript expressions.
 */
const employees = [
    {
        id: 1,
        name: "Aarav Sharma",
        department: "Engineering",
        salary: 85000,
        bonus: 7000,
        age: 29,
        city: "Lucknow",
        title: "Software Engineer",
        performance: 91.5,
        active: true
    },
    {
        id: 2,
        name: "Priya Singh",
        department: "Engineering",
        salary: 112000,
        bonus: 12000,
        age: 34,
        city: "Delhi",
        title: "Senior Software Engineer",
        performance: 96,
        active: true
    },
    {
        id: 3,
        name: "Rohan Verma",
        department: "Finance",
        salary: 78000,
        bonus: null,
        age: 41,
        city: "Mumbai",
        title: "Financial Analyst",
        performance: 82,
        active: true
    },
    {
        id: 4,
        name: "Neha Gupta",
        department: "Human Resources",
        salary: 68000,
        bonus: 5000,
        age: 31,
        city: "Lucknow",
        title: "HR Manager",
        performance: 88,
        active: true
    },
    {
        id: 5,
        name: "Kabir Khan",
        department: "Security",
        salary: 99000,
        bonus: 9000,
        age: 38,
        city: "Hyderabad",
        title: "Security Engineer",
        performance: 93,
        active: true
    },
    {
        id: 6,
        name: "Ananya Rao",
        department: "Sales",
        salary: 72000,
        bonus: 4000,
        age: 26,
        city: "Bengaluru",
        title: "Sales Executive",
        performance: 79.5,
        active: true
    },
    {
        id: 7,
        name: "Vikram Patel",
        department: "Research",
        salary: 125000,
        bonus: 18000,
        age: 45,
        city: "Pune",
        title: "Research Scientist",
        performance: 97,
        active: true
    },
    {
        id: 8,
        name: "Meera Joshi",
        department: "Engineering",
        salary: 64000,
        bonus: null,
        age: 24,
        city: "Lucknow",
        title: "Junior Developer",
        performance: 74,
        active: true
    },
    {
        id: 9,
        name: "Arjun Mehta",
        department: "Sales",
        salary: 91000,
        bonus: 6000,
        age: 36,
        city: "Delhi",
        title: "Sales Manager",
        performance: 89,
        active: true
    },
    {
        id: 10,
        name: "Sara Ali",
        department: "Security",
        salary: 105000,
        bonus: 11000,
        age: 33,
        city: "Mumbai",
        title: "Cybersecurity Analyst",
        performance: 94.5,
        active: true
    },
    {
        id: 11,
        name: "Dev Malhotra",
        department: "Finance",
        salary: 88000,
        bonus: null,
        age: 39,
        city: "Pune",
        title: "Risk Analyst",
        performance: 86,
        active: false
    },
    {
        id: 12,
        name: "Ishita Kapoor",
        department: "Research",
        salary: 118000,
        bonus: 15000,
        age: 30,
        city: "Delhi",
        title: "Data Scientist",
        performance: 95.5,
        active: true
    }
];


function arithmeticExamples() {
    printTitle("1. Arithmetic operators");

    const rows = employees.slice(0, 6).map((employee) => ({
        name: employee.name,
        salary: employee.salary,
        bonus: employee.bonus,
        totalCompensation: employee.salary + (employee.bonus ?? 0),
        monthlySalary: employee.salary / 12,
        tenPercentRaise: employee.salary * 1.10,
        ageNextYear: employee.age + 1
    }));

    printRows(rows);

    console.log("\nSQL equivalents include:");
    console.log("salary + COALESCE(bonus, 0)");
    console.log("salary / 12");
    console.log("salary * 1.10");
    console.log("age + 1");
}


function comparisonExamples() {
    printTitle("2. Comparison operators");

    const highSalary = employees
        .filter((employee) => employee.salary > 100000)
        .map((employee) => ({
            name: employee.name,
            salary: employee.salary
        }));

    console.log("\nJavaScript equivalent of SQL salary > 100000:");
    printRows(highSalary);

    const exactlyThirty = employees
        .filter((employee) => employee.age === 30)
        .map((employee) => ({
            name: employee.name,
            age: employee.age
        }));

    console.log("\nJavaScript equivalent of SQL age = 30:");
    printRows(exactlyThirty);

    /*
     * SQL commonly uses "=" for equality.
     * JavaScript uses "===" for strict equality.
     *
     * "==" performs coercion and is generally less explicit.
     */
    console.log("\nStrict equality:");
    console.log("30 === '30' ->", 30 === "30");
    console.log("30 == '30'  ->", 30 == "30");
}


function logicalExamples() {
    printTitle("3. Logical operators");

    const result = employees
        .filter(
            (employee) =>
                employee.salary > 90000 &&
                employee.age < 40
        )
        .map((employee) => ({
            name: employee.name,
            salary: employee.salary,
            age: employee.age
        }));

    console.log("\nSQL-style AND represented by JavaScript &&:");
    printRows(result);

    const cities = employees
        .filter(
            (employee) =>
                employee.city === "Delhi" ||
                employee.city === "Lucknow"
        )
        .map((employee) => ({
            name: employee.name,
            city: employee.city
        }));

    console.log("\nSQL-style OR represented by JavaScript ||:");
    printRows(cities);

    const inactive = employees
        .filter((employee) => !employee.active)
        .map((employee) => ({
            name: employee.name,
            active: employee.active
        }));

    console.log("\nSQL-style NOT represented by JavaScript !:");
    printRows(inactive);

    /*
     * Parentheses explicitly control grouping.
     */
    const grouped = employees.filter(
        (employee) =>
            (employee.city === "Delhi" || employee.city === "Lucknow") &&
            employee.salary >= 90000
    );

    console.log("\nExplicit grouping:");
    printRows(grouped.map((employee) => ({
        name: employee.name,
        city: employee.city,
        salary: employee.salary
    })));
}


function between(value, lower, upper) {
    /*
     * SQL BETWEEN is inclusive:
     *
     * value BETWEEN lower AND upper
     *
     * means:
     *
     * value >= lower AND value <= upper
     */
    return value >= lower && value <= upper;
}


function betweenExamples() {
    printTitle("4. BETWEEN and NOT BETWEEN");

    const salaryRange = employees
        .filter((employee) => between(employee.salary, 80000, 100000))
        .map((employee) => ({
            name: employee.name,
            salary: employee.salary
        }));

    console.log("\nInclusive salary range 80000 through 100000:");
    printRows(salaryRange);

    const outsideAgeRange = employees
        .filter((employee) => !between(employee.age, 30, 40))
        .map((employee) => ({
            name: employee.name,
            age: employee.age
        }));

    console.log("\nNOT BETWEEN 30 and 40:");
    printRows(outsideAgeRange);
}


function inExamples() {
    printTitle("5. IN and NOT IN");

    const selectedCities = new Set(["Delhi", "Lucknow", "Mumbai"]);

    const selected = employees
        .filter((employee) => selectedCities.has(employee.city))
        .map((employee) => ({
            name: employee.name,
            city: employee.city
        }));

    console.log("\nMembership using Set.has():");
    printRows(selected);

    const excludedDepartments = new Set(["Finance", "Human Resources"]);

    const notSelected = employees
        .filter((employee) => !excludedDepartments.has(employee.department))
        .map((employee) => ({
            name: employee.name,
            department: employee.department
        }));

    console.log("\nNon-membership using !Set.has():");
    printRows(notSelected);

    /*
     * Set.has() provides average O(1) membership lookup in typical
     * implementations, whereas repeatedly searching an array with
     * includes() is O(n).
     */
}


function likeToRegExp(pattern) {
    /*
     * Convert the common SQL LIKE wildcards into a regular expression.
     *
     * % -> zero or more characters
     * _ -> exactly one character
     *
     * Literal regular-expression characters are escaped first.
     */
    let regexSource = "";

    for (const character of pattern) {
        if (character === "%") {
            regexSource += ".*";
        } else if (character === "_") {
            regexSource += ".";
        } else {
            regexSource += character.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        }
    }

    return new RegExp(`^${regexSource}$`, "i");
}


function sqlLike(value, pattern) {
    if (value === null || value === undefined) {
        return false;
    }

    return likeToRegExp(pattern).test(String(value));
}


function likeExamples() {
    printTitle("6. LIKE pattern matching");

    const startsWithA = employees
        .filter((employee) => sqlLike(employee.name, "A%"))
        .map((employee) => ({
            name: employee.name
        }));

    console.log("\nLIKE 'A%':");
    printRows(startsWithA);

    const containsEngineer = employees
        .filter((employee) => sqlLike(employee.title, "%Engineer%"))
        .map((employee) => ({
            name: employee.name,
            title: employee.title
        }));

    console.log("\nLIKE '%Engineer%':");
    printRows(containsEngineer);

    const emailPattern = employees
        .filter((employee) => sqlLike(`${employee.name.replaceAll(" ", ".").toLowerCase()}@example.com`, "%@example.com"))
        .map((employee) => ({
            name: employee.name
        }));

    console.log("\nPattern ending with @example.com:");
    printRows(emailPattern);

    const secondCharacterA = employees
        .filter((employee) => sqlLike(employee.name, "_a%"))
        .map((employee) => ({
            name: employee.name
        }));

    console.log("\nLIKE '_a%':");
    printRows(secondCharacterA);
}


function nullExamples() {
    printTitle("7. NULL and three-valued logic");

    /*
     * SQL NULL is not equivalent to JavaScript null in every semantic detail.
     * SQL comparisons with NULL produce UNKNOWN, while JavaScript's strict
     * comparison to null produces true or false.
     *
     * For SQL:
     *
     *     bonus = NULL
     *
     * is not the correct missing-value test.
     *
     * Use:
     *
     *     bonus IS NULL
     */
    const missingBonus = employees
        .filter((employee) => employee.bonus === null)
        .map((employee) => ({
            name: employee.name,
            bonus: employee.bonus
        }));

    console.log("\nJavaScript explicit null test:");
    printRows(missingBonus);

    console.log("\nSQL-style rule:");
    console.log("Use IS NULL rather than = NULL.");
    console.log("Use IS NOT NULL rather than <> NULL.");

    console.log("\nJavaScript null arithmetic:");
    console.log("null + 1000 ->", null + 1000);
    console.log("null ?? 0   ->", null ?? 0);

    /*
     * SQL's COALESCE(bonus, 0) corresponds closely to the practical intent
     * of JavaScript's nullish-coalescing operator:
     */
    const compensation = employees.slice(0, 4).map((employee) => ({
        name: employee.name,
        bonus: employee.bonus,
        totalCompensation: employee.salary + (employee.bonus ?? 0)
    }));

    printRows(compensation);
}


function generateParameterizedQuery(options) {
    printTitle("8. Parameterized SQL query construction");

    const conditions = [];
    const parameters = [];

    /*
     * The SQL fragments below are controlled by application code.
     * User-supplied values are represented by ? placeholders.
     */
    if (options.minimumSalary !== undefined) {
        conditions.push("salary >= ?");
        parameters.push(options.minimumSalary);
    }

    if (options.maximumSalary !== undefined) {
        conditions.push("salary <= ?");
        parameters.push(options.maximumSalary);
    }

    if (options.activeOnly) {
        conditions.push("active = ?");
        parameters.push(1);
    }

    if (options.namePattern !== undefined) {
        conditions.push("employee_name LIKE ?");
        parameters.push(options.namePattern);
    }

    if (options.cities?.length > 0) {
        const placeholders = options.cities.map(() => "?").join(", ");
        conditions.push(`city IN (${placeholders})`);
        parameters.push(...options.cities);
    }

    const whereClause = conditions.length > 0
        ? conditions.join(" AND ")
        : "1 = 1";

    const sql = `
        SELECT employee_name, salary, city, active
        FROM employees
        WHERE ${whereClause}
        ORDER BY salary DESC;
    `.trim();

    console.log("SQL:");
    console.log(sql);
    console.log("\nParameters:");
    console.log(parameters);

    return { sql, parameters };
}


function applyEquivalentFilter(options) {
    /*
     * This function evaluates the same logical rules locally against the
     * in-memory dataset. It is useful for understanding what the SQL query
     * is intended to retrieve.
     */
    return employees.filter((employee) => {
        if (
            options.minimumSalary !== undefined &&
            employee.salary < options.minimumSalary
        ) {
            return false;
        }

        if (
            options.maximumSalary !== undefined &&
            employee.salary > options.maximumSalary
        ) {
            return false;
        }

        if (
            options.activeOnly &&
            employee.active !== true
        ) {
            return false;
        }

        if (
            options.namePattern !== undefined &&
            !sqlLike(employee.name, options.namePattern)
        ) {
            return false;
        }

        if (
            options.cities?.length > 0 &&
            !options.cities.includes(employee.city)
        ) {
            return false;
        }

        return true;
    });
}


function dynamicFilterExample() {
    printTitle("9. Dynamic filtering");

    const options = {
        minimumSalary: 85000,
        maximumSalary: 120000,
        activeOnly: true,
        namePattern: "%a%",
        cities: ["Delhi", "Lucknow", "Mumbai"]
    };

    const generated = generateParameterizedQuery(options);

    console.log("\nEquivalent local evaluation:");
    const results = applyEquivalentFilter(options).map((employee) => ({
        name: employee.name,
        salary: employee.salary,
        city: employee.city,
        active: employee.active
    }));

    printRows(results);

    return generated;
}


function demonstrateSqlInQueries() {
    printTitle("10. IN query construction");

    const cities = ["Delhi", "Lucknow", "Pune"];

    if (cities.length === 0) {
        /*
         * An empty IN list is awkward in many SQL dialects. Application code
         * should decide explicitly whether an empty list means "match none"
         * or "do not apply this filter".
         */
        console.log("Empty city list: filter policy must be defined explicitly.");
        return;
    }

    const placeholders = cities.map(() => "?").join(", ");

    const sql = `
        SELECT employee_name, city
        FROM employees
        WHERE city IN (${placeholders});
    `.trim();

    console.log(sql);
    console.log("Parameters:", cities);
}


function operatorPrecedenceExample() {
    printTitle("11. Operator precedence");

    /*
     * SQL:
     *
     * WHERE city = 'Delhi'
     *    OR city = 'Lucknow'
     *   AND salary >= 90000
     *
     * is commonly interpreted as:
     *
     * city = 'Delhi'
     * OR (city = 'Lucknow' AND salary >= 90000)
     *
     * JavaScript's && also binds more tightly than ||.
     */
    const implicitGrouping = employees.filter(
        (employee) =>
            employee.city === "Delhi" ||
            employee.city === "Lucknow" &&
            employee.salary >= 90000
    );

    console.log("\nImplicit grouping:");
    printRows(implicitGrouping.map((employee) => ({
        name: employee.name,
        city: employee.city,
        salary: employee.salary
    })));

    const explicitGrouping = employees.filter(
        (employee) =>
            (employee.city === "Delhi" || employee.city === "Lucknow") &&
            employee.salary >= 90000
    );

    console.log("\nExplicit grouping:");
    printRows(explicitGrouping.map((employee) => ({
        name: employee.name,
        city: employee.city,
        salary: employee.salary
    })));
}


function businessMetricExample() {
    printTitle("12. Business metric using multiple operators");

    const results = employees
        .filter(
            (employee) =>
                employee.active &&
                between(employee.salary, 70000, 130000) &&
                employee.performance >= 80
        )
        .map((employee) => {
            const totalCompensation =
                employee.salary + (employee.bonus ?? 0);

            const compensationIndex =
                (totalCompensation / employee.salary) * 100;

            return {
                name: employee.name,
                salary: employee.salary,
                totalCompensation: Number(totalCompensation.toFixed(2)),
                performance: employee.performance,
                compensationIndex: Number(compensationIndex.toFixed(2))
            };
        })
        .sort((a, b) => b.compensationIndex - a.compensationIndex);

    printRows(results);
}


function performanceComparison() {
    printTitle("13. Performance consideration: Set membership");

    const largeExample = Array.from({ length: 10000 }, (_, index) => ({
        id: index + 1,
        city: ["Delhi", "Lucknow", "Mumbai", "Pune", "Jaipur"][index % 5]
    }));

    const allowedArray = ["Delhi", "Lucknow", "Mumbai"];
    const allowedSet = new Set(allowedArray);

    console.time("Array.includes");
    const arrayCount = largeExample.filter(
        (employee) => allowedArray.includes(employee.city)
    ).length;
    console.timeEnd("Array.includes");

    console.time("Set.has");
    const setCount = largeExample.filter(
        (employee) => allowedSet.has(employee.city)
    ).length;
    console.timeEnd("Set.has");

    console.log("Array membership count:", arrayCount);
    console.log("Set membership count:", setCount);

    /*
     * This demonstrates JavaScript-side collection lookup, not database
     * query performance. Database IN performance depends on indexes,
     * cardinality, optimizer behavior, statistics, and the database engine.
     */
}


function securityExample() {
    printTitle("14. SQL injection prevention");

    const userCity = "Delhi";
    const minimumSalary = 90000;

    /*
     * Unsafe conceptual construction:
     *
     * const sql = "... WHERE city = '" + userCity + "'";
     *
     * This mixes SQL syntax with data.
     *
     * Safe construction keeps values separate:
     */
    const safeSql = `
        SELECT employee_name, salary, city
        FROM employees
        WHERE city = ?
          AND salary >= ?;
    `.trim();

    const parameters = [userCity, minimumSalary];

    console.log("Safe SQL:");
    console.log(safeSql);
    console.log("Parameters:", parameters);

    /*
     * Parameterization should be implemented by the actual database driver.
     * Merely writing ? in a string is not sufficient unless the driver binds
     * those values separately.
     */
}


function validationExamples() {
    printTitle("15. Validation and edge cases");

    const tests = [
        {
            description: "BETWEEN lower boundary",
            actual: between(80000, 80000, 100000),
            expected: true
        },
        {
            description: "BETWEEN upper boundary",
            actual: between(100000, 80000, 100000),
            expected: true
        },
        {
            description: "BETWEEN outside range",
            actual: between(100001, 80000, 100000),
            expected: false
        },
        {
            description: "IN membership",
            actual: ["Delhi", "Pune"].includes("Delhi"),
            expected: true
        },
        {
            description: "NOT membership",
            actual: !["Delhi", "Pune"].includes("Mumbai"),
            expected: true
        },
        {
            description: "LIKE prefix",
            actual: sqlLike("Aarav Sharma", "A%"),
            expected: true
        },
        {
            description: "LIKE contains",
            actual: sqlLike("Software Engineer", "%Engineer%"),
            expected: true
        },
        {
            description: "LIKE single-character wildcard",
            actual: sqlLike("Sara Ali", "_a%"),
            expected: true
        }
    ];

    for (const test of tests) {
        if (test.actual !== test.expected) {
            throw new Error(`Failed test: ${test.description}`);
        }

        console.log(`PASS: ${test.description}`);
    }

    console.log("All JavaScript validation tests passed.");
}


function main() {
    printTitle("SQL Operators: JavaScript Companion Study");

    console.log(`
Topics:
- Arithmetic
- Comparison
- AND, OR, NOT
- BETWEEN
- IN
- LIKE
- NULL handling
- Parameterized SQL
- Dynamic filtering
- Operator precedence
- Performance considerations
- Security
`);

    arithmeticExamples();
    comparisonExamples();
    logicalExamples();
    betweenExamples();
    inExamples();
    likeExamples();
    nullExamples();
    generateParameterizedQuery({
        minimumSalary: 80000,
        maximumSalary: 120000,
        activeOnly: true,
        namePattern: "%a%",
        cities: ["Delhi", "Lucknow"]
    });
    dynamicFilterExample();
    demonstrateSqlInQueries();
    operatorPrecedenceExample();
    businessMetricExample();
    performanceComparison();
    securityExample();
    validationExamples();

    printTitle("16. Important SQL versus JavaScript distinctions");

    console.log(`
SQL                              JavaScript
---------------------------------------------------------------
=                                ===
<> / !=                          !==
AND                              &&
OR                               ||
NOT                              !
IN (...)                         Array.includes / Set.has
BETWEEN a AND b                  value >= a && value <= b
LIKE 'A%'                        pattern matching implementation
IS NULL                          value === null
COALESCE(value, 0)               value ?? 0

These are conceptual correspondences, not interchangeable syntax.
SQL is declarative and operates within a database engine, while JavaScript
expressions execute in the JavaScript runtime.
`);

    printTitle("17. End of study");
    console.log("The examples are complete and require only a modern Node.js runtime.");
}


main();
