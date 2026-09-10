# SELECT fundamentals

## Topic overview

SQL `SELECT` is the primary statement used to retrieve data from relational databases. It defines the values and expressions that should appear in a result set and commonly works with `FROM`, `WHERE`, `ORDER BY`, `GROUP BY`, `HAVING`, `DISTINCT`, `LIMIT`, joins, functions, and expressions.

The accompanying Python script uses Python's built-in `sqlite3` module to create an in-memory relational database and execute practical SQL examples. No external package is required.

The database contains employees, departments, and projects so that the examples can progress from simple single-table queries to calculated results, joins, aggregation, aliases, NULL handling, query debugging, security, and performance considerations.

## Fundamental SELECT structure

The basic form of a SELECT statement is:

    SELECT column_name
    FROM table_name;

The `SELECT` clause specifies the requested output values.

The `FROM` clause identifies the source of those values.

For example:

    SELECT first_name
    FROM employees;

This returns the `first_name` value for each row in the `employees` table.

A SELECT query normally returns a result set containing rows and columns. The result set does not automatically modify the underlying data.

## Selecting a single column

A single column can be selected by writing its name after `SELECT`.

    SELECT salary
    FROM employees;

Only the `salary` column appears in the result. Other columns remain in the source table but are not included in this particular result.

This distinction is fundamental: selecting a column does not mean selecting the complete database record.

## Selecting multiple columns

Multiple columns are separated by commas.

    SELECT first_name, last_name, job_title
    FROM employees;

The order in which columns appear in the SELECT list determines the order of columns in the result.

For example:

    SELECT job_title, first_name, salary
    FROM employees;

returns the same underlying information as a different column order, but the result structure is different.

Column order therefore matters to applications, exports, reports, and other systems consuming the result.

## SELECT *

The asterisk is a wildcard representing all columns from the selected source.

    SELECT *
    FROM employees;

This is convenient for exploration and inspection, especially when learning an unfamiliar table.

It is less desirable when the exact result structure matters.

Potential problems with `SELECT *` include:

- unnecessary columns may be transferred;
- sensitive columns may be exposed unintentionally;
- schema changes can change the result;
- applications can become dependent on column order;
- queries communicate less clearly what data is actually required;
- wide tables can increase data transfer and processing requirements.

For an application that requires only an employee identifier, name, and role, an explicit projection is clearer:

    SELECT employee_id, first_name, job_title
    FROM employees;

`SELECT *` is not inherently incorrect. It is primarily a question of intent, maintainability, security, and data volume.

## Expressions

A SELECT list is not limited to stored column names.

An expression is something SQL evaluates to produce a value.

Examples include:

    salary * 12
    salary + bonus
    first_name || ' ' || last_name
    UPPER(first_name)
    COALESCE(bonus, 0)

A query can therefore transform stored information into a calculated result without modifying the source data.

For example:

    SELECT salary, salary * 12
    FROM employees;

The second value is calculated when the query runs. It does not create or permanently store a new `annual_salary` column.

## Arithmetic expressions

SQL supports arithmetic operations. Common operators include:

- `+` for addition
- `-` for subtraction
- `*` for multiplication
- `/` for division
- `%` for modulo in SQLite

An example of a calculated annual salary is:

    SELECT salary * 12 AS annual_salary
    FROM employees;

A percentage calculation can be written as:

    SELECT salary * 1.10 AS projected_salary
    FROM employees;

These calculations are useful for reporting, financial analysis, projections, ratios, and derived metrics.

Arithmetic behavior can differ between database systems, especially regarding numeric types, integer division, precision, and division by zero. Financial calculations should therefore be designed with the numeric semantics of the target database in mind.

## String expressions

SQL can manipulate text values directly within SELECT expressions.

The SQLite concatenation operator is `||`.

    SELECT first_name || ' ' || last_name AS full_name
    FROM employees;

The result combines two stored columns into a new output value.

The script also demonstrates functions such as:

    UPPER(first_name)
    LOWER(last_name)
    LENGTH(first_name)

These expressions are useful when preparing database results for reports, exports, dashboards, and applications.

## Literal values

A SELECT expression can contain values that are not stored in the table.

For example:

    SELECT 100;

or:

    SELECT 'SQL';

SQLite allows a SELECT without a FROM clause, which makes it convenient for demonstrating constants and expressions.

A query can also return multiple literals:

    SELECT 2026 AS current_year, 'SQL' AS subject, 100 AS score;

Literal values can be useful for labels, fixed calculations, testing expressions, and constructing structured outputs.

## Column aliases

An alias gives a result column a temporary output name.

The common syntax is:

    SELECT expression AS alias_name
    FROM table_name;

For example:

    SELECT salary * 12 AS annual_salary
    FROM employees;

The alias `annual_salary` describes the calculated result.

An alias does not rename the underlying database column. It exists for the result of the query.

Aliases are especially valuable for expressions because expressions can otherwise produce difficult-to-read result names.

A descriptive alias such as `total_compensation` is preferable to an unclear name such as `x`.

## AS is optional in many SQL systems

Many SQL dialects allow an alias without the `AS` keyword.

For example:

    SELECT salary * 12 annual_salary
    FROM employees;

Although this is valid in many systems, explicitly writing `AS` often improves readability:

    SELECT salary * 12 AS annual_salary
    FROM employees;

SQL dialects differ in their exact alias and identifier rules, so database-specific syntax should be considered when writing portable SQL.

## Aliases are not general-purpose variables

A SELECT alias is a name for a result column. It should not automatically be treated as a variable that can be reused throughout the same SELECT list.

A pattern such as:

    SELECT salary * 12 AS annual_salary,
           annual_salary * 0.10 AS estimated_tax
    FROM employees;

is not portable and is not generally valid because the second expression may not be able to reference the first expression's alias.

A derived table or common table expression can make the calculation reusable:

    SELECT annual_salary,
           annual_salary * 0.10 AS estimated_tax
    FROM (
        SELECT salary * 12 AS annual_salary
        FROM employees
    ) AS employee_pay;

This separates the calculation into a logical intermediate result.

## DISTINCT

`DISTINCT` removes duplicate result rows.

For example:

    SELECT DISTINCT department_id
    FROM employees;

If several employees belong to the same department, the department identifier appears once in the distinct result.

An important detail is that DISTINCT applies to the complete selected combination.

For example:

    SELECT DISTINCT department_id, active
    FROM employees;

uniquely considers the combination of `department_id` and `active`. It does not independently deduplicate each column.

NULL values are also relevant to DISTINCT. Multiple NULL values can result in a single distinct NULL value.

## SELECT and WHERE

`SELECT` and `WHERE` solve different problems.

`SELECT` determines which values appear in the result.

`WHERE` determines which rows qualify.

For example:

    SELECT first_name, salary
    FROM employees
    WHERE salary > 80000;

The SELECT list requests `first_name` and `salary`.

The WHERE clause filters the employees before those values are returned.

A query can filter using a column that is not included in the SELECT list:

    SELECT first_name
    FROM employees
    WHERE salary > 80000;

The salary is used to determine which rows qualify, but salary does not have to appear in the final result.

## ORDER BY

`ORDER BY` controls the ordering of the result.

Ascending order can be specified with `ASC`, while descending order uses `DESC`.

Examples:

    SELECT first_name, salary
    FROM employees
    ORDER BY salary ASC;

and:

    SELECT first_name, salary
    FROM employees
    ORDER BY salary DESC;

Multiple ordering expressions can be specified:

    SELECT first_name, salary
    FROM employees
    ORDER BY salary DESC, first_name ASC;

The first expression determines the primary order. The second expression breaks ties.

Without an explicit ORDER BY, an application should not depend on a particular row ordering.

## ORDER BY and aliases

Aliases can often be referenced by ORDER BY.

For example:

    SELECT salary * 12 AS annual_salary
    FROM employees
    ORDER BY annual_salary DESC;

This can improve readability because the calculated expression does not have to be repeated in the ORDER BY clause.

Exact alias visibility rules differ across SQL clauses and database products. SQL should therefore not be treated as if every clause has access to every SELECT alias.

## LIMIT and OFFSET

SQLite supports `LIMIT` for restricting the number of returned rows.

For example:

    SELECT first_name, salary
    FROM employees
    ORDER BY salary DESC
    LIMIT 3;

This returns the three highest salaries.

`OFFSET` skips a number of rows before returning the requested result:

    SELECT first_name, salary
    FROM employees
    ORDER BY employee_id
    LIMIT 3 OFFSET 3;

LIMIT and OFFSET are useful for previews and simple pagination.

Pagination should normally use a deterministic ORDER BY. Otherwise, the database has no guaranteed business ordering from which a stable page sequence can be derived.

## NULL

NULL represents missing, unknown, or unavailable information.

NULL is not the same as:

- zero;
- an empty string;
- the text value `NULL`.

Arithmetic involving NULL generally produces NULL.

For example:

    SELECT salary + bonus AS total_compensation
    FROM employees;

If an employee has a NULL bonus, the expression can produce NULL.

## COALESCE

`COALESCE` returns the first non-NULL expression.

For example:

    COALESCE(bonus, 0)

can treat a missing bonus as zero.

A total compensation calculation can therefore be written as:

    SELECT salary + COALESCE(bonus, 0) AS total_compensation
    FROM employees;

The decision to treat NULL as zero is a business interpretation. Missing information does not universally mean zero, so the choice should be intentional.

## NULL comparisons

NULL cannot be tested using ordinary equality.

This is incorrect:

    WHERE email = NULL

The appropriate syntax is:

    WHERE email IS NULL

or:

    WHERE email IS NOT NULL

SQL uses three-valued logic involving TRUE, FALSE, and UNKNOWN. Comparisons involving NULL frequently produce UNKNOWN rather than ordinary TRUE or FALSE.

This behavior is one of the most important differences between SQL and ordinary programming-language comparisons.

## CASE expressions

`CASE` provides conditional logic inside SQL expressions.

A searched CASE expression has the general structure:

    CASE
        WHEN condition THEN result
        WHEN condition THEN result
        ELSE result
    END

For example:

    SELECT
        salary,
        CASE
            WHEN salary >= 100000 THEN 'High'
            WHEN salary >= 70000 THEN 'Medium'
            ELSE 'Standard'
        END AS salary_band
    FROM employees;

CASE is useful for:

- classification;
- business rules;
- status labels;
- conditional calculations;
- reporting categories;
- data quality indicators.

The script also demonstrates CASE for active status and NULL bonus classification.

## Date expressions

SQLite does not use a dedicated DATE storage type in the same way as some enterprise database systems.

Dates are commonly represented using ISO-formatted text, Julian day values, or Unix timestamps.

The sample database stores dates such as:

    2022-04-15

SQLite provides date and time functions including `date`, `datetime`, and `strftime`.

For example:

    SELECT
        first_name,
        strftime('%Y', hire_date) AS hire_year
    FROM employees;

This extracts the year from the stored date representation.

Date behavior is database-specific, so production applications should use consistent date representations and understand the capabilities of their chosen database.

## Boolean-style expressions

SQL dialects differ in how they represent Boolean values.

SQLite commonly represents Boolean-style results using integers:

- `0` means false;
- `1` means true.

The script demonstrates expressions such as:

    salary >= 100000 AS earns_at_least_100k

This produces a calculated flag that can be useful in analytical results.

## CAST

`CAST` explicitly converts an expression to a requested type.

The general form is:

    CAST(expression AS type)

Examples include:

    CAST(salary AS INTEGER)

and:

    CAST('123.45' AS REAL)

Explicit type conversion can make the intended behavior of an expression clearer and can affect arithmetic and comparison semantics.

Type systems and supported target types differ between database products.

## Qualified column names

When multiple tables participate in a query, columns should often be qualified using the table name or table alias.

For example:

    SELECT employees.first_name, departments.department_name
    FROM employees
    JOIN departments
        ON employees.department_id = departments.department_id;

Qualification makes the source of each column explicit.

This becomes particularly important when two tables contain columns with the same name.

## Table aliases

A table alias provides a shorter temporary name for a table.

For example:

    SELECT e.first_name
    FROM employees AS e;

The alias `e` can then be used throughout the query.

Aliases are particularly useful with joins:

    SELECT
        e.first_name,
        d.department_name
    FROM employees AS e
    JOIN departments AS d
        ON e.department_id = d.department_id;

Good table aliases improve readability when several tables are involved.

## Ambiguous column names

Suppose two joined tables both contain `department_id`.

A reference such as:

    SELECT department_id

may be ambiguous.

Using:

    SELECT e.department_id

or:

    SELECT d.department_id

makes the intended source explicit.

The script demonstrates qualification in joined employee and department queries.

## SELECT with JOIN

A SELECT list can return columns from multiple tables.

For example:

    SELECT
        e.first_name,
        e.job_title,
        d.department_name,
        d.location
    FROM employees AS e
    LEFT JOIN departments AS d
        ON e.department_id = d.department_id;

The JOIN establishes relationships between rows.

The SELECT list determines which values from that combined relational result are returned.

This distinction is useful when learning SQL: JOIN determines how sources are combined, while SELECT determines which values from the resulting source are projected.

## SELECT * with JOIN

Using `SELECT *` after a join can produce every column from every joined source.

For example:

    SELECT *
    FROM employees AS e
    JOIN departments AS d
        ON e.department_id = d.department_id;

This can produce a wide result containing identifiers, names, locations, compensation information, and other fields.

An explicit projection is usually easier to understand:

    SELECT
        e.employee_id,
        e.first_name,
        e.job_title,
        d.department_name,
        d.location
    FROM employees AS e
    JOIN departments AS d
        ON e.department_id = d.department_id;

This also establishes a clearer result contract for downstream applications.

## Aggregate expressions

Aggregate functions calculate values across multiple rows.

Common aggregate functions include:

- `COUNT`
- `SUM`
- `AVG`
- `MIN`
- `MAX`

For example:

    SELECT COUNT(*) AS employee_count
    FROM employees;

This returns one result row containing the number of employees.

Another example is:

    SELECT
        AVG(salary) AS average_salary,
        MIN(salary) AS minimum_salary,
        MAX(salary) AS maximum_salary
    FROM employees;

Aggregate SELECT statements therefore operate at a different level from ordinary row-by-row projection.

## COUNT(*) versus COUNT(column)

`COUNT(*)` counts rows.

`COUNT(column)` counts non-NULL values in the specified column.

For example:

    SELECT
        COUNT(*) AS all_employees,
        COUNT(email) AS employees_with_email
    FROM employees;

If an employee's email is NULL, that employee is included in COUNT(*) but not in COUNT(email).

This distinction is important when interpreting completeness metrics.

## GROUP BY

`GROUP BY` divides rows into groups before aggregate calculations are returned.

For example:

    SELECT
        department_id,
        AVG(salary) AS average_salary
    FROM employees
    GROUP BY department_id;

The result contains one row per department identifier represented in the grouped input.

The script combines GROUP BY with COUNT and AVG to calculate department-level metrics.

## WHERE versus HAVING

WHERE filters individual rows.

HAVING filters groups after aggregation.

For example:

    SELECT
        department_id,
        AVG(salary) AS average_salary
    FROM employees
    WHERE active = 1
    GROUP BY department_id
    HAVING AVG(salary) > 70000;

The WHERE clause removes inactive employees before grouping.

The HAVING clause then removes departments whose calculated average salary does not meet the specified condition.

This distinction is fundamental in aggregate queries.

## Subqueries

A SELECT statement can use another SELECT statement as an input.

For example:

    SELECT
        first_name,
        annual_salary
    FROM (
        SELECT
            first_name,
            salary * 12 AS annual_salary
        FROM employees
    ) AS employee_pay
    WHERE annual_salary > 1000000;

The inner query calculates `annual_salary`.

The outer query can then treat that calculated result as a column in a derived table.

Subqueries are useful when a calculated value needs to be reused by a surrounding query.

## Common table expressions

A common table expression, or CTE, uses a `WITH` clause to give an intermediate result a temporary name.

The general structure is:

    WITH name AS (
        SELECT ...
    )
    SELECT ...
    FROM name;

CTEs can improve readability in complex analytical SQL because intermediate transformations receive descriptive names.

The script uses a CTE to calculate annual salaries and then filter the result.

## Logical processing order

SQL is written in an order that differs from its simplified logical processing order.

A useful conceptual model is:

1. FROM and JOIN identify the input source.
2. WHERE filters input rows.
3. GROUP BY creates groups.
4. HAVING filters groups.
5. SELECT produces requested expressions.
6. DISTINCT removes duplicate result rows when requested.
7. ORDER BY sorts the result.
8. LIMIT and OFFSET restrict the final result.

This is a logical model rather than a literal description of the physical execution performed by a database engine.

Database optimizers can rearrange physical operations as long as the required result is preserved.

Understanding logical processing order helps explain why some aliases are available in certain clauses and unavailable in others.

## Result metadata

Applications do not receive only values. They also need to know the structure of the result.

Python's `sqlite3` cursor exposes SELECT result metadata through `cursor.description`.

The script demonstrates how column names and related metadata can be inspected programmatically.

This is particularly relevant when SQL results are consumed by reporting systems, APIs, data-processing programs, or other applications.

## Performance considerations

SELECT performance depends on many factors:

- number of rows;
- number of columns;
- row width;
- indexes;
- join structure;
- filtering conditions;
- aggregation;
- sorting;
- database statistics;
- storage architecture;
- query optimizer;
- network transfer;
- application-side processing.

Selecting only required columns can reduce unnecessary data transfer.

For example:

    SELECT employee_id, first_name
    FROM employees;

may be preferable to:

    SELECT *
    FROM employees;

when an application needs only two values.

This does not mean `SELECT *` is automatically slow. The impact depends on table size, column widths, workload, database engine, and execution plan.

## Query plans

Query plans provide information about how a database intends to execute a statement.

SQLite supports `EXPLAIN QUERY PLAN`.

The script uses it to inspect queries involving `department_id`.

Query-plan analysis is more reliable than assuming that a particular query is fast based solely on its written appearance.

Performance should be measured against realistic data volumes and workloads.

## Indexes

Indexes can help databases locate matching rows efficiently.

An index is not automatically required for every column appearing in a SELECT list.

Indexes are generally designed around access patterns, such as:

- frequent filtering;
- joins;
- ordering;
- uniqueness requirements.

The script creates an index on `employees.department_id` and uses `EXPLAIN QUERY PLAN` to demonstrate how execution planning can change.

Indexes also have costs. They consume storage and can increase the work required for INSERT, UPDATE, and DELETE operations.

## Security considerations

SELECT statements can expose sensitive information if the projection is too broad.

This is one reason explicit column selection is important for application-facing queries.

For example:

    SELECT employee_id, first_name, job_title
    FROM employees;

can be safer than returning every column when the consumer does not need compensation, contact, or internal fields.

SQL security also depends on database privileges, authentication, authorization, views, row-level restrictions where supported, encryption, auditing, and application architecture.

## Parameterized SELECT queries

Applications frequently place user-provided values into WHERE conditions.

String concatenation should not be used to construct SQL from untrusted input.

A safer application pattern is parameter binding.

The Python script demonstrates:

    SELECT employee_id, first_name, job_title
    FROM employees
    WHERE first_name = ?;

The user-supplied value is passed separately as a parameter.

Parameterized queries help prevent SQL injection because the database driver treats the parameter as data rather than as part of the SQL command structure.

Parameterization does not replace authorization. A properly parameterized query can still expose information that the application should not allow a user to access.

## Debugging SELECT queries

A practical debugging approach is to build the query incrementally.

Start with a small inspection:

    SELECT *
    FROM employees
    LIMIT 3;

Then reduce the projection:

    SELECT employee_id, first_name, salary
    FROM employees
    LIMIT 3;

Then add filtering:

    SELECT employee_id, first_name, salary
    FROM employees
    WHERE salary >= 80000
    LIMIT 3;

For more complex queries, introduce JOIN, expressions, grouping, ordering, and pagination one stage at a time.

This helps identify whether an unexpected result originates from:

- the source table;
- the selected columns;
- an expression;
- NULL handling;
- a filter;
- a join;
- aggregation;
- sorting;
- pagination.

## Empty result sets

A SELECT query can execute successfully and return zero rows.

For example:

    SELECT employee_id, first_name
    FROM employees
    WHERE salary > 1000000;

An empty result is not necessarily an error.

Application code should distinguish between:

- a SQL execution failure;
- a successful query with no matching rows.

This distinction is important in APIs, reports, dashboards, and data-processing systems.

## Common SELECT mistakes

### Missing commas

Multiple selected columns require commas.

Correct:

    SELECT first_name, last_name
    FROM employees;

### Confusing columns and text literals

This references a column:

    SELECT first_name
    FROM employees;

This references a text literal:

    SELECT 'first_name'
    FROM employees;

Quoting changes the meaning.

### Incorrect NULL comparison

Do not use:

    WHERE email = NULL

Use:

    WHERE email IS NULL

### Assuming row order

Do not assume rows are returned in a meaningful order unless ORDER BY explicitly specifies the required ordering.

### Overusing SELECT *

Returning all columns can create unnecessary dependencies and expose information that the consumer does not require.

### Unclear aliases

An alias should communicate the meaning of the result.

Prefer:

    salary * 12 AS annual_salary

over:

    salary * 12 AS x

### Unqualified columns in joins

When multiple tables contain the same column name, qualify the reference with the table name or alias.

## Edge cases

Important SELECT edge cases include:

- NULL values;
- empty result sets;
- duplicate rows;
- duplicate combinations under DISTINCT;
- missing foreign-key relationships;
- integer versus decimal arithmetic;
- division involving NULL;
- division by zero;
- ambiguous column names;
- aliases that are not available in every clause;
- changes to table schema when using SELECT *;
- date representation differences;
- database-specific function behavior.

The script intentionally includes NULL values, an employee without a department, an inactive employee, and an employee without an email address so that these cases are visible in executable examples.

## Practical reporting example

The script builds an employee report containing:

- employee identifier;
- employee full name;
- department;
- job title;
- base salary;
- normalized bonus;
- total compensation;
- salary category;
- hire year.

The result is produced using a combination of explicit projection, string concatenation, aliases, COALESCE, arithmetic, CASE, JOIN, WHERE, and ORDER BY.

This demonstrates how SELECT can act as a data presentation layer. Stored database fields do not have to match the exact shape required by a report or application.

## SELECT and data integrity

A normal SELECT statement reads data.

It does not permanently rename columns, calculate new stored columns, or modify source rows merely because expressions appear in the SELECT list.

For example:

    SELECT salary * 12 AS annual_salary
    FROM employees;

does not update `salary` and does not create a permanent `annual_salary` field.

This distinction separates querying from data modification.

## Readability and maintainability

Readable SQL should make its intent apparent.

Useful practices include:

- explicitly list required columns;
- place complex expressions on separate lines;
- use meaningful aliases;
- use consistent indentation;
- qualify columns when multiple tables are involved;
- use table aliases consistently;
- make filtering conditions clear;
- use parentheses where they improve expression clarity;
- avoid unnecessary duplication of complicated expressions;
- use derived tables or CTEs when intermediate calculations need names.

Readable SQL is easier to review, test, debug, maintain, and integrate with other systems.

## Important distinctions

| Concept | Purpose |
|---|---|
| SELECT | Defines result values and columns |
| FROM | Defines the source relation |
| SELECT * | Requests all source columns |
| Explicit column list | Requests only specified columns |
| Expression | Calculates or transforms a value |
| Alias | Gives a result column a temporary name |
| DISTINCT | Removes duplicate result rows |
| WHERE | Filters input rows |
| ORDER BY | Controls result ordering |
| LIMIT | Restricts returned rows |
| OFFSET | Skips rows before returning results |
| GROUP BY | Creates groups for aggregation |
| HAVING | Filters aggregated groups |
| JOIN | Combines related data sources |
| CASE | Performs conditional result logic |
| COALESCE | Handles NULL by choosing the first non-NULL value |
| CAST | Explicitly converts a value to another SQL type |
| Aggregate function | Calculates across multiple rows |

## Real-world relevance

SELECT is used throughout database-driven systems.

Typical applications include:

- employee reports;
- financial statements;
- sales dashboards;
- customer search;
- inventory systems;
- business intelligence;
- data analysis;
- APIs;
- operational reporting;
- audit queries;
- management reporting;
- application data retrieval;
- data exports;
- machine-learning data preparation.

The SELECT list is often the point where raw relational data is shaped into a form suitable for another system.

## Implementation considerations

The accompanying Python script uses:

- `sqlite3` for an embedded relational database;
- an in-memory database so no external database server is required;
- explicit table definitions;
- realistic sample records;
- NULL values;
- joins;
- aggregate functions;
- indexes;
- parameterized queries;
- assertions for basic query testing;
- exception handling for SQL errors.

The Python code is an execution and demonstration environment. The educational subject is SQL SELECT rather than Python database programming.

## Scope of the examples

The script progresses through:

- basic SELECT syntax;
- individual columns;
- multiple columns;
- SELECT *;
- literals;
- expressions;
- arithmetic;
- NULL;
- COALESCE;
- aliases;
- DISTINCT;
- WHERE;
- ORDER BY;
- LIMIT and OFFSET;
- string functions;
- CASE;
- dates;
- Boolean-style expressions;
- qualified columns;
- table aliases;
- joins;
- aggregates;
- GROUP BY;
- HAVING;
- subqueries;
- CTEs;
- logical processing order;
- type conversion;
- debugging;
- testing;
- performance;
- indexes;
- security;
- production-oriented query design.

The examples are intentionally executable so that the relationship between SQL syntax and returned data can be observed directly.
