'use strict';

/*
 * JOIN vs Subquery
 *
 * This Node.js program focuses on query design rather than translating the
 * Python examples line by line. It builds SQL statements dynamically,
 * validates query intent, compares relationship-oriented query forms, and
 * uses an event-driven execution model.
 *
 * The program uses only built-in Node.js capabilities. The actual SQL strings
 * are PostgreSQL-oriented examples intended for inspection and execution in
 * a PostgreSQL environment.
 */

const EventEmitter = require('node:events');

class QueryExecutionError extends Error {
    constructor(message, cause = null) {
        super(message);
        this.name = 'QueryExecutionError';
        this.cause = cause;
    }
}

class QueryCatalog extends EventEmitter {
    constructor() {
        super();
        this.queries = new Map();
    }

    register(name, category, sql) {
        if (!name || !category || !sql.trim()) {
            throw new TypeError('A query requires a name, category, and SQL.');
        }

        if (this.queries.has(name)) {
            throw new Error(`Query '${name}' is already registered.`);
        }

        this.queries.set(name, {
            name,
            category,
            sql: sql.trim()
        });

        this.emit('registered', this.queries.get(name));
    }

    get(name) {
        const query = this.queries.get(name);

        if (!query) {
            throw new Error(`Unknown query: ${name}`);
        }

        return query;
    }

    all() {
        return [...this.queries.values()];
    }
}

function buildEmployeeSearch({ department, minimumSalary }) {
    if (typeof department !== 'string' || department.trim() === '') {
        throw new TypeError('department must be a non-empty string');
    }

    if (!Number.isFinite(minimumSalary) || minimumSalary < 0) {
        throw new TypeError('minimumSalary must be a non-negative number');
    }

    /*
     * Values are represented by PostgreSQL positional parameters rather than
     * string interpolation. This keeps SQL structure separate from data and
     * avoids injection vulnerabilities.
     */
    return {
        text: `
            SELECT
                e.employee_id,
                e.employee_name,
                d.department_name,
                e.salary
            FROM employees AS e
            JOIN departments AS d
              ON d.department_id = e.department_id
            WHERE d.department_name = $1
              AND e.salary >= $2
            ORDER BY e.salary DESC;
        `,
        values: [department.trim(), minimumSalary]
    };
}

function buildEmployeesWithProjects() {
    /*
     * The JOIN intentionally produces one row per employee-project
     * relationship. That multiplicity is useful when project-level columns
     * are needed, but it is undesirable if the caller only needs a yes/no
     * answer about project participation.
     */
    return {
        text: `
            SELECT
                e.employee_name,
                p.project_name,
                p.budget
            FROM employees AS e
            JOIN employee_projects AS ep
              ON ep.employee_id = e.employee_id
            JOIN projects AS p
              ON p.project_id = ep.project_id
            WHERE p.budget >= $1
            ORDER BY e.employee_name, p.project_name;
        `,
        values: [500000]
    };
}

function buildEmployeesHavingQualifyingProject() {
    /*
     * EXISTS communicates semi-join semantics: the outer employee is
     * returned once when at least one qualifying project exists.
     */
    return {
        text: `
            SELECT
                e.employee_id,
                e.employee_name
            FROM employees AS e
            WHERE EXISTS (
                SELECT 1
                FROM employee_projects AS ep
                JOIN projects AS p
                  ON p.project_id = ep.project_id
                WHERE ep.employee_id = e.employee_id
                  AND p.budget >= $1
            )
            ORDER BY e.employee_name;
        `,
        values: [500000]
    };
}

function buildAboveDepartmentAverage() {
    /*
     * This correlated subquery compares each employee with the average of
     * employees belonging to that employee's own department.
     */
    return {
        text: `
            SELECT
                e.employee_name,
                d.department_name,
                e.salary
            FROM employees AS e
            JOIN departments AS d
              ON d.department_id = e.department_id
            WHERE e.salary > (
                SELECT AVG(e2.salary)
                FROM employees AS e2
                WHERE e2.department_id = e.department_id
            )
            ORDER BY d.department_name, e.salary DESC;
        `,
        values: []
    };
}

function buildAboveDepartmentAverageWithDerivedTable() {
    /*
     * The derived table computes each department's aggregate once as a
     * relational result and then joins that result to employee rows.
     * This can be easier to extend when additional department metrics are
     * required.
     */
    return {
        text: `
            SELECT
                e.employee_name,
                d.department_name,
                e.salary,
                averages.average_salary
            FROM employees AS e
            JOIN departments AS d
              ON d.department_id = e.department_id
            JOIN (
                SELECT
                    department_id,
                    AVG(salary) AS average_salary
                FROM employees
                GROUP BY department_id
            ) AS averages
              ON averages.department_id = e.department_id
            WHERE e.salary > averages.average_salary
            ORDER BY d.department_name, e.salary DESC;
        `,
        values: []
    };
}

function buildDepartmentsWithoutEmployees() {
    /*
     * LEFT JOIN plus IS NULL is an anti-join. It exposes the absence of a
     * matching child row through the nullable side of the outer join.
     */
    return {
        text: `
            SELECT d.department_name
            FROM departments AS d
            LEFT JOIN employees AS e
              ON e.department_id = d.department_id
            WHERE e.employee_id IS NULL
            ORDER BY d.department_name;
        `,
        values: []
    };
}

function buildDepartmentsWithoutEmployeesUsingNotExists() {
    /*
     * NOT EXISTS expresses the same business condition directly as an
     * absence test and avoids selecting child columns entirely.
     */
    return {
        text: `
            SELECT d.department_name
            FROM departments AS d
            WHERE NOT EXISTS (
                SELECT 1
                FROM employees AS e
                WHERE e.department_id = d.department_id
            )
            ORDER BY d.department_name;
        `,
        values: []
    };
}

function explainDesignChoice(name, joinQuery, subqueryQuery) {
    console.log(`\n=== ${name} ===`);
    console.log('\nJOIN-oriented form:');
    console.log(joinQuery.text.trim());

    if (joinQuery.values.length > 0) {
        console.log(`Parameters: ${JSON.stringify(joinQuery.values)}`);
    }

    console.log('\nSubquery-oriented form:');
    console.log(subqueryQuery.text.trim());

    if (subqueryQuery.values.length > 0) {
        console.log(`Parameters: ${JSON.stringify(subqueryQuery.values)}`);
    }
}

function classifyQuery(query) {
    const normalized = query.text.toLowerCase();

    const characteristics = {
        hasJoin: /\bjoin\b/.test(normalized),
        hasSubquery: /\bselect\b[\s\S]*\bselect\b/.test(normalized),
        usesExists: /\bexists\b/.test(normalized),
        usesAggregation: /\b(avg|count|sum|min|max)\s*\(/.test(normalized),
        usesOuterJoin: /\bleft\s+join\b/.test(normalized)
    };

    return characteristics;
}

async function inspectQuery(
    name,
    query,
    execute = async () => ({ rows: [], rowCount: 0 })
) {
    try {
        const metadata = classifyQuery(query);

        console.log(`\n--- ${name} ---`);
        console.log(JSON.stringify(metadata, null, 2));

        /*
         * The injected executor makes this file testable without requiring a
         * live database connection. A real application can pass a PostgreSQL
         * client's query function here.
         */
        const result = await execute(query.text, query.values);

        console.log(
            `Execution result: ${result.rowCount ?? result.rows?.length ?? 0} row(s)`
        );

        return result;
    } catch (error) {
        throw new QueryExecutionError(
            `Failed to inspect or execute query '${name}'.`,
            error
        );
    }
}

async function main() {
    const catalog = new QueryCatalog();

    catalog.on('registered', query => {
        console.log(`Registered: ${query.name} [${query.category}]`);
    });

    const employeeSearch = buildEmployeeSearch({
        department: 'Engineering',
        minimumSalary: 90000
    });

    const projectJoin = buildEmployeesWithProjects();
    const projectExists = buildEmployeesHavingQualifyingProject();
    const correlatedAverage = buildAboveDepartmentAverage();
    const derivedAverage = buildAboveDepartmentAverageWithDerivedTable();
    const antiJoin = buildDepartmentsWithoutEmployees();
    const notExists = buildDepartmentsWithoutEmployeesUsingNotExists();

    catalog.register(
        'employee-search-join',
        'direct relationship',
        employeeSearch.text
    );

    catalog.register(
        'employees-with-project-details',
        'relationship expansion',
        projectJoin.text
    );

    catalog.register(
        'employees-with-qualifying-project',
        'existence test',
        projectExists.text
    );

    catalog.register(
        'above-department-average-correlated',
        'correlated comparison',
        correlatedAverage.text
    );

    catalog.register(
        'above-department-average-derived',
        'derived-table comparison',
        derivedAverage.text
    );

    catalog.register(
        'departments-anti-join',
        'absence test',
        antiJoin.text
    );

    catalog.register(
        'departments-not-exists',
        'absence test',
        notExists.text
    );

    explainDesignChoice(
        'Relationship retrieval versus existence testing',
        projectJoin,
        projectExists
    );

    explainDesignChoice(
        'Correlated aggregate versus derived-table aggregate',
        correlatedAverage,
        derivedAverage
    );

    explainDesignChoice(
        'Anti-join versus NOT EXISTS',
        antiJoin,
        notExists
    );

    console.log('\n=== Parameterized employee search ===');
    console.log(employeeSearch.text.trim());
    console.log(`Parameters: ${JSON.stringify(employeeSearch.values)}`);

    console.log('\n=== Query catalog ===');
    for (const query of catalog.all()) {
        console.log(`${query.name}: ${query.category}`);
    }

    /*
     * This mock execution demonstrates asynchronous application behavior
     * without requiring a database. In production, replace it with:
     *
     * const { rows, rowCount } = await pool.query(text, values);
     *
     * The SQL remains parameterized in both cases.
     */
    await inspectQuery(
        'employee-search-join',
        employeeSearch,
        async (text, values) => ({
            rows: [
                {
                    employee_id: 1,
                    employee_name: 'Asha',
                    department_name: values[0],
                    salary: 125000
                }
            ],
            rowCount: 1
        })
    );

    console.log('\n=== Query-design observations ===');
    console.log(
        'Use JOIN when related columns form the result or when the query is naturally relational.'
    );
    console.log(
        'Use EXISTS when the requirement is whether a related row exists.'
    );
    console.log(
        'Use a correlated subquery when a value depends directly on the current outer row.'
    );
    console.log(
        'Use a derived table or CTE when a computed relation is useful to the rest of the query.'
    );
    console.log(
        'Measure performance with the database execution plan rather than assuming one form is universally faster.'
    );
}

main().catch(error => {
    console.error(error.message);

    if (error.cause) {
        console.error(`Cause: ${error.cause.message}`);
    }

    process.exitCode = 1;
});
