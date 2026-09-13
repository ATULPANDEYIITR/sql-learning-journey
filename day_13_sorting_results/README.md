# SQL sorting results

## Topic introduction

SQL returns rows from a query, but a relational table does not inherently represent a business-defined sequence. If an application requires employees to appear from highest salary to lowest salary, customers to appear alphabetically, transactions to appear newest first, or missing values to appear at the end, the required ordering must be expressed explicitly.

The primary SQL clause for this purpose is `ORDER BY`.

This study script uses Python's built-in `sqlite3` module to execute real SQL statements against an in-memory SQLite database. No external database server or third-party Python package is required.

The material progresses from basic `ORDER BY` syntax to multi-column ordering, deterministic tie-breaking, `NULL` placement, custom business ordering, pagination, aggregation, window functions, indexes, query planning, security, and production design.

## Fundamental concept of ORDER BY

The basic structure is:

    SELECT column1, column2
    FROM table_name
    ORDER BY column1;

`ORDER BY` specifies the expressions used to arrange rows in the result.

For example:

    SELECT employee_name, salary
    FROM employees
    ORDER BY salary;

The default direction in SQLite is ascending order.

An explicit form is clearer:

    SELECT employee_name, salary
    FROM employees
    ORDER BY salary ASC;

Ordering is applied to the result produced by the query. It does not permanently rearrange the physical table.

This distinction is important. An `ORDER BY` query determines the order of that particular result set. It does not redefine the intrinsic identity or storage order of the rows.

## Why ORDER BY is necessary

A common mistake is to assume that rows will always appear in insertion order.

A query such as:

    SELECT employee_id, employee_name
    FROM employees;

does not express a business requirement such as "oldest employee first" or "alphabetical order."

If a particular order matters, it should be stated:

    SELECT employee_id, employee_name
    FROM employees
    ORDER BY employee_name ASC;

The database optimizer is free to choose execution strategies. Applications should never depend on an unspecified row order.

## ASC and DESC

`ASC` means ascending.

For numeric values, this normally means:

    smallest -> largest

For dates:

    earliest -> latest

For text, the result depends on the active collation.

`DESC` means descending:

    largest -> smallest

For example:

    SELECT employee_name, salary
    FROM employees
    ORDER BY salary DESC;

returns the highest salaries first.

The following are equivalent in intent when ascending order is the default:

    ORDER BY salary

and:

    ORDER BY salary ASC

Writing `ASC` explicitly can improve readability because the intended direction is visible.

## Sorting numbers

Numeric sorting follows the database's numeric comparison rules.

For example:

    ORDER BY salary ASC

places lower salaries before higher salaries.

The reverse is:

    ORDER BY salary DESC

A major data-modeling issue occurs when numbers are stored as text. Text sorting follows text comparison rules rather than numeric comparison rules. Values such as `"100"`, `"20"`, and `"3"` can therefore produce an ordering that differs from numerical ordering.

Numeric data should normally be stored using an appropriate numeric type.

## Sorting text

Text can be ordered using:

    ORDER BY employee_name ASC

or:

    ORDER BY employee_name DESC

The exact ordering depends on collation.

Collation determines how text values are compared. Case sensitivity, accent handling, and language-specific rules can differ between database systems and configurations.

The Python script demonstrates SQLite's `NOCASE` collation:

    ORDER BY name COLLATE NOCASE ASC

This produces case-insensitive ordering for the demonstrated data.

For internationalized systems, text ordering should be treated as a deliberate application requirement rather than assuming that simple byte-level or default ordering will always match user expectations.

## Sorting dates

The script stores dates using ISO format:

    YYYY-MM-DD

For consistently formatted ISO dates, lexicographic ordering corresponds to chronological ordering.

For example:

    2020-01-20
    2021-04-12
    2024-01-05

sort correctly from earliest to latest as text because the year, month, and day components occur from the largest time unit to the smallest.

More complicated timestamp requirements may involve time zones, fractional seconds, daylight-saving transitions, or database-specific temporal types. Those issues should be handled according to the database system and application requirements.

## Multiple-column sorting

`ORDER BY` can contain multiple expressions:

    ORDER BY department ASC, salary DESC

The expressions are evaluated from left to right.

The first expression has the highest priority.

If two rows have the same department, the database uses salary to order those rows.

For example:

    SELECT employee_name, department, salary
    FROM employees
    ORDER BY department ASC, salary DESC;

means:

1. Sort departments alphabetically.
2. Within each department, put the highest salary first.

A third expression can be added:

    ORDER BY department ASC, salary DESC, employee_name ASC

This creates a three-level ordering hierarchy.

## Tie-breaking

A tie occurs when two or more rows have the same value for the current sorting expression.

Suppose two employees have a salary of `88000`:

    ORDER BY salary DESC

does not fully distinguish those rows.

If an application needs deterministic ordering, add another expression:

    ORDER BY salary DESC, employee_id ASC

The database first compares salary. If salary is equal, it compares `employee_id`.

A unique identifier is an effective final tie-breaker because it prevents two rows from remaining equal after every sorting expression has been evaluated.

This is especially important for pagination, exports, reports, ranking interfaces, and APIs.

## Deterministic ordering

Deterministic ordering means that the sorting expressions define a complete ordering for the rows relevant to the query.

A useful pattern is:

    ORDER BY business_metric DESC, primary_key ASC

For example:

    ORDER BY salary DESC, employee_id ASC

The salary is the business-relevant ordering criterion, while the employee ID provides deterministic tie-breaking.

Without a final unique tie-breaker, applications should not treat the relative order of tied rows as guaranteed.

## ORDER BY aliases

A calculated expression can be given an alias:

    SELECT
        employee_name,
        salary,
        salary * 0.10 AS estimated_bonus
    FROM employees
    ORDER BY estimated_bonus DESC;

The alias makes the query easier to read than repeating the entire expression.

Aliases are particularly useful for calculated business metrics such as:

    salary + bonus
    revenue - cost
    quantity * unit_price
    conversion_rate
    total_compensation

When an expression can produce `NULL`, its semantics should also be considered.

## Expressions in ORDER BY

`ORDER BY` can sort by expressions rather than only physical table columns.

For example:

    ORDER BY salary + COALESCE(bonus, 0) DESC

can sort employees according to total compensation.

The script demonstrates this pattern with:

    salary + COALESCE(bonus, 0)

where a missing bonus is treated as zero for the calculated value.

This is appropriate only when the business interpretation supports that assumption.

## Understanding NULL

`NULL` is one of the most important concepts in SQL sorting.

`NULL` does not mean:

- zero
- an empty string
- false
- the literal text `"NULL"`

`NULL` represents the absence of a known value.

For example, an employee's performance score may be `NULL` because the employee has not yet been evaluated.

SQL therefore provides special predicates:

    column IS NULL

and:

    column IS NOT NULL

The following is incorrect:

    WHERE performance_score = NULL

The correct form is:

    WHERE performance_score IS NULL

## SQL's three-valued logic

SQL comparisons can produce three logical states:

- TRUE
- FALSE
- UNKNOWN

A comparison involving `NULL` generally produces `UNKNOWN`.

For example:

    performance_score = NULL

does not produce TRUE for rows containing NULL.

This is why SQL provides `IS NULL` and `IS NOT NULL`.

Understanding this behavior is essential when designing sorting and filtering rules involving missing values.

## Default NULL ordering

Different database systems can have different default behavior for where `NULL` appears during sorting.

In SQLite, the demonstrated behavior is:

    ASC  -> NULL values before non-NULL values
    DESC -> NULL values after non-NULL values

The important production lesson is not to assume that every SQL database uses the same default behavior.

If the location of `NULL` values matters to an application, make the requirement explicit.

## NULLS FIRST and NULLS LAST

Where supported, SQL can explicitly request NULL placement:

    ORDER BY performance_score ASC NULLS FIRST

or:

    ORDER BY performance_score ASC NULLS LAST

`NULLS FIRST` places missing values before non-NULL values.

`NULLS LAST` places missing values after non-NULL values.

These options can be combined with ascending or descending ordering.

Examples include:

    ORDER BY performance_score DESC NULLS LAST

and:

    ORDER BY performance_score ASC NULLS FIRST

Explicit NULL ordering communicates the business rule directly.

## Portable NULL ordering with CASE

A `CASE` expression can be used when explicit `NULLS FIRST` or `NULLS LAST` syntax is unavailable or when more complex ordering rules are required.

A common NULLS LAST pattern is:

    ORDER BY
        CASE WHEN score IS NULL THEN 1 ELSE 0 END,
        score ASC

The first expression assigns:

    non-NULL -> 0
    NULL     -> 1

Ascending order therefore puts non-NULL values first.

A NULLS FIRST pattern can use:

    ORDER BY
        CASE WHEN score IS NULL THEN 0 ELSE 1 END,
        score ASC

The important idea is that the first expression creates a NULL-status sorting group, while the second expression sorts the actual values.

## NULL ordering in multi-column queries

NULL handling can be incorporated into a larger sorting hierarchy.

For example:

    ORDER BY
        department ASC,
        CASE WHEN performance_score IS NULL THEN 1 ELSE 0 END,
        performance_score DESC,
        employee_id ASC

This means:

- department is the primary ordering criterion
- employees with known performance scores come before unknown scores
- known scores are ranked from highest to lowest
- employee ID resolves remaining ties

This illustrates why the order of expressions in `ORDER BY` matters.

## COALESCE and sorting

`COALESCE` returns the first non-NULL value from its arguments.

A common example is:

    COALESCE(bonus, 0)

This can be useful when the business rule explicitly says that a missing bonus should be treated as zero for a calculation.

For example:

    ORDER BY COALESCE(bonus, 0) DESC

But NULL and zero do not necessarily have the same meaning.

A NULL bonus could mean:

- not yet calculated
- not eligible
- unavailable
- not applicable

A zero bonus could mean:

- calculated and equal to zero

Replacing NULL with zero can therefore destroy useful business semantics if the distinction matters.

## LIMIT and ORDER BY

`LIMIT` restricts how many rows are returned.

For example:

    SELECT employee_name, salary
    FROM employees
    ORDER BY salary DESC
    LIMIT 5;

means "return the five highest salaries."

Without `ORDER BY`, the following:

    SELECT employee_name, salary
    FROM employees
    LIMIT 5;

does not mean "the five highest salaries."

It simply requests five rows without defining which business-ranked rows should be selected.

The combination of `ORDER BY` and `LIMIT` is fundamental for top-N queries.

## OFFSET and pagination

A simple pagination pattern is:

    ORDER BY salary DESC, employee_id ASC
    LIMIT 10 OFFSET 20

This requests ten rows after skipping twenty rows from the ordered result.

The script demonstrates several pages using this technique.

A deterministic `ORDER BY` is especially important here. If multiple rows tie and there is no unique tie-breaker, page boundaries can become unreliable.

## Offset pagination trade-offs

`OFFSET` is convenient but can become inefficient for very large offsets.

For example:

    LIMIT 20 OFFSET 100000

may require the database to identify and skip a large number of rows before producing the requested page.

This is one reason large-scale applications may use keyset pagination, also called cursor pagination.

## Keyset pagination

Keyset pagination uses the values from the final row of the current page as the starting point for the next page.

For:

    ORDER BY salary DESC, employee_id ASC

a conceptual next-page condition is:

    WHERE
        salary < previous_salary
        OR (
            salary = previous_salary
            AND employee_id > previous_employee_id
        )

followed by:

    ORDER BY salary DESC, employee_id ASC
    LIMIT 20

This approach avoids relying on a large numeric offset.

Keyset pagination requires careful construction because the filtering condition must correspond exactly to the ordering hierarchy.

A suitable index can make this strategy particularly effective for large datasets.

## GROUP BY and ORDER BY

`ORDER BY` also applies to grouped results.

For example:

    SELECT
        department,
        COUNT(*) AS employee_count,
        AVG(salary) AS average_salary
    FROM employees
    GROUP BY department
    ORDER BY average_salary DESC;

The result is not individual employees. It is one row per department.

The departments are then sorted according to their calculated average salary.

This demonstrates that `ORDER BY` can operate on aggregate results.

## HAVING and ORDER BY

A grouped query can combine:

- `WHERE`
- `GROUP BY`
- `HAVING`
- `ORDER BY`

For example:

    SELECT
        department,
        COUNT(*) AS employee_count,
        AVG(salary) AS average_salary
    FROM employees
    WHERE employment_status = 'Active'
    GROUP BY department
    HAVING AVG(salary) >= 75000
    ORDER BY average_salary DESC;

Conceptually:

`WHERE` filters individual source rows.

`GROUP BY` creates groups.

`HAVING` filters groups.

`ORDER BY` determines the presentation order of the resulting groups.

## Logical query processing

A useful conceptual model for SQL query processing is:

    FROM
    WHERE
    GROUP BY
    HAVING
    SELECT
    ORDER BY
    LIMIT / OFFSET

This is a logical model rather than a literal description of every internal database execution step. Query optimizers may rearrange operations internally while preserving the required result.

The model is useful for understanding why `ORDER BY` can work with calculated output expressions and aggregate aliases.

## Custom business ordering

Alphabetical order is not always the required order.

An application might define:

    High
    Medium
    Low

instead of alphabetical order.

A `CASE` expression can implement that:

    ORDER BY
        CASE priority
            WHEN 'High' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 3
            ELSE 4
        END

The numeric values establish the desired business priority.

The same approach can be used for:

- employment status
- workflow stages
- customer priority
- ticket severity
- product categories
- approval states
- shipping status

The order should represent an explicit domain rule.

## Sorting by SELECT-list position

Some SQL systems allow:

    ORDER BY 3 DESC

to mean "sort by the third expression in the SELECT list."

The script demonstrates this syntax.

Although compact, ordinal ordering can reduce maintainability.

If the SELECT list changes, `ORDER BY 3` may silently refer to a different expression.

Named columns and aliases are generally clearer:

    ORDER BY salary DESC

or:

    ORDER BY total_compensation DESC

## DISTINCT and ORDER BY

`DISTINCT` removes duplicate result rows.

For example:

    SELECT DISTINCT department
    FROM employees
    ORDER BY department ASC;

returns each department once and sorts the resulting department values alphabetically.

`DISTINCT` and `ORDER BY` should be understood as separate concepts:

`DISTINCT` controls duplicate elimination.

`ORDER BY` controls result ordering.

## Top-N queries

A top-N query usually combines descending order with `LIMIT`:

    SELECT employee_name, salary
    FROM employees
    ORDER BY salary DESC, employee_id ASC
    LIMIT 3;

A bottom-N query reverses the direction:

    SELECT employee_name, salary
    FROM employees
    ORDER BY salary ASC, employee_id ASC
    LIMIT 3;

The unique identifier provides deterministic tie-breaking.

## Window functions and ORDER BY

Window functions introduce another important use of `ORDER BY`.

For example:

    RANK() OVER (
        PARTITION BY department
        ORDER BY salary DESC
    )

The `ORDER BY` inside `OVER` determines how the window function evaluates rows.

The script also uses an outer:

    ORDER BY department, salary_rank

These are different operations.

The window `ORDER BY` determines the analytical ordering.

The outer `ORDER BY` determines the order of the final result set.

Confusing these two levels can lead to incorrect analytical queries.

## ROW_NUMBER, RANK, and DENSE_RANK

The script compares three ranking functions.

`ROW_NUMBER()` assigns a unique sequential number to every row.

If two employees have the same salary, they still receive different row numbers.

`RANK()` assigns the same rank to tied values and leaves gaps after ties.

For example, a sequence might conceptually be:

    1
    2
    2
    4

`DENSE_RANK()` also assigns the same rank to ties but does not leave gaps:

    1
    2
    2
    3

The `ORDER BY` expression inside each window function determines what constitutes an equal ranking value.

## Conditional ranking

The script combines `CASE` with window functions to rank known performance scores ahead of unknown scores.

A pattern such as:

    ORDER BY
        CASE WHEN performance_score IS NULL THEN 1 ELSE 0 END,
        performance_score DESC

first separates known and unknown values, then sorts known scores from highest to lowest.

This is a general technique for implementing explicit data-quality or business-priority rules.

## Collation and international text

Text sorting is affected by collation.

A database may distinguish between:

    A
    a

or treat them as equivalent for a particular collation.

International applications can also require language-specific ordering.

Therefore, requirements such as "alphabetical order" are incomplete unless the expected collation behavior is understood.

This is particularly relevant when data contains:

- mixed capitalization
- accented characters
- non-Latin scripts
- locale-specific alphabetical conventions

The correct solution depends on the database engine and its available collations.

## Performance considerations

Sorting can require substantial computational resources for large result sets.

A database may need to:

- read qualifying rows
- calculate sorting expressions
- compare values
- allocate memory for sorting
- perform a sort operation
- return rows in the required order

An appropriate index can sometimes allow the database to read rows in an order compatible with the requested `ORDER BY`.

The script creates indexes such as:

    CREATE INDEX idx_employees_salary
    ON employees (salary);

and:

    CREATE INDEX idx_employees_department_salary
    ON employees (department, salary DESC);

The actual usefulness of an index depends on the complete query.

Important factors include:

- table size
- WHERE conditions
- ORDER BY expressions
- index column order
- selectivity
- requested columns
- database optimizer
- result-set size

An index is not automatically beneficial for every sorting query.

## Composite indexes

The order of columns in a composite index matters.

An index conceptually beginning with:

    (department, salary)

is naturally aligned with access patterns beginning with `department`.

It can be useful for queries involving:

    ORDER BY department

and:

    ORDER BY department, salary

It should not be treated as equivalent to a separate index beginning with `salary`.

The leading-column principle is important when designing indexes for multi-column filtering and sorting.

## Query plans

The script uses SQLite's:

    EXPLAIN QUERY PLAN

to inspect how the database intends to execute a query.

Query plans can help identify whether the database is:

- using an index
- scanning a table
- performing additional sorting work
- applying other operations that affect performance

Query plans should be evaluated with realistic data volumes. A plan that looks acceptable for twelve rows may behave very differently for millions of rows.

## Dynamic sorting

Applications frequently allow users to select sorting options such as:

- name
- salary
- date
- department

and:

- ascending
- descending

Ordinary SQL value parameters are intended for data values, not arbitrary SQL identifiers or syntax fragments.

Therefore, an application should not directly concatenate untrusted user input into:

    ORDER BY <user input>

A safe approach is to map approved external choices to predefined SQL fragments.

For example, an application can define an allow-list:

    name -> employee_name
    salary -> salary
    department -> department
    hire_date -> hire_date

and:

    asc -> ASC
    desc -> DESC

Only values present in those allow-lists should be accepted.

## SQL injection considerations

Sorting options can become a security issue when an application dynamically constructs SQL.

This is unsafe in principle:

    ORDER BY <raw external input>

The problem is that SQL identifiers and syntax are not generally substituted through ordinary value parameters.

The safe architecture is:

    external input
        |
        v
    validation
        |
        v
    allow-listed SQL identifier
        |
        v
    fixed query structure

For ordinary values, use parameterized SQL:

    WHERE salary >= ?

For dynamic identifiers or directions, use strict allow-lists.

The script demonstrates this distinction explicitly.

## Security and authorization

`ORDER BY` controls ordering, not authorization.

For example, allowing a user to sort by salary does not mean the user should necessarily be permitted to see salary.

Access control should be applied independently.

A secure application should determine:

- which rows the user may access
- which columns the user may access
- which sorting options are allowed
- whether sensitive values may appear in the result

Sorting should never be used as a substitute for authorization.

## Common mistakes

### Assuming insertion order

Incorrect assumption:

    SELECT *
    FROM employees;

will always return rows in insertion order.

Correct approach:

    SELECT *
    FROM employees
    ORDER BY employee_id ASC;

when employee ID order is actually the intended requirement.

### Using LIMIT without ORDER BY for top-N logic

Incorrect:

    SELECT *
    FROM employees
    LIMIT 5;

This does not mean the five highest-paid employees.

Correct:

    SELECT *
    FROM employees
    ORDER BY salary DESC, employee_id ASC
    LIMIT 5;

### Comparing NULL with equals

Incorrect:

    WHERE bonus = NULL

Correct:

    WHERE bonus IS NULL

### Assuming NULL equals zero

NULL and zero can have completely different business meanings.

Use `COALESCE` only when the business rule explicitly supports converting the missing value for that calculation.

### Ignoring ties

Using:

    ORDER BY salary DESC

may leave multiple employees tied.

For deterministic output:

    ORDER BY salary DESC, employee_id ASC

### Assuming all databases sort NULL identically

Default NULL ordering can differ between database systems.

Explicitly specify the desired placement where possible.

### Building dynamic SQL from raw input

Never treat arbitrary user input as a trusted SQL identifier.

Use allow-lists for dynamic sort columns and directions.

### Overusing ordinal ORDER BY positions

Although:

    ORDER BY 3 DESC

can be valid, it is less self-documenting than:

    ORDER BY salary DESC

## Edge cases

Sorting logic should account for several edge cases.

### All values are equal

A unique tie-breaker becomes important.

### Many NULL values

The application should explicitly define whether missing values belong first or last.

### Empty result set

`ORDER BY` still works when no rows satisfy the query, but there is nothing to display.

### One-row result

Sorting has no visible effect, but the query remains valid.

### Mixed data quality

Values that look numeric but are stored as text may not sort numerically.

### Locale-sensitive text

Alphabetical order can vary according to collation.

### Changing data during pagination

Rows inserted, deleted, or updated between page requests can change OFFSET-based page boundaries.

### Non-unique sort criteria

Rows tied on all specified expressions do not have a meaningful application-defined relative order.

## Real-world applications

Sorting is used throughout data-driven systems.

Common examples include:

### Financial systems

    ORDER BY transaction_date DESC

can show the newest transactions first.

    ORDER BY amount DESC

can identify the largest transactions.

### E-commerce

    ORDER BY price ASC

can show the cheapest products first.

    ORDER BY rating DESC, review_count DESC

can prioritize highly rated products while using review volume as a tie-breaker.

### Human resources

    ORDER BY salary DESC, employee_id ASC

can rank compensation deterministically.

### Customer management

    ORDER BY customer_priority ASC, last_activity DESC

can combine business priority with recency.

### Analytics

    ORDER BY conversion_rate DESC

can rank campaigns or products according to performance.

### Operations

Custom `CASE` ordering can place urgent workflow states before routine states.

### Reporting

Grouped results can be ordered by:

- employee count
- average revenue
- total revenue
- profitability
- performance metrics

## Production design principles

A production sorting requirement should answer several questions.

### What does "first" mean?

It might mean:

- highest
- lowest
- newest
- oldest
- highest priority
- alphabetical
- custom business order

The query should encode the actual requirement.

### What should happen to NULL?

Determine whether missing values should be:

- first
- last
- treated specially
- excluded entirely

### Is the result deterministic?

If pagination or stable reporting is required, add a unique final tie-breaker.

### Is the query large?

Large sorts may require significant CPU and memory.

### Can an index support the access pattern?

Inspect the actual query plan and benchmark realistic workloads.

### Is sorting user-controlled?

Use an allow-list for columns and directions.

### Is the order locale-sensitive?

Select an appropriate collation.

### Is pagination deep?

Consider keyset pagination for large offsets.

### Does NULL have business meaning?

Do not casually replace NULL with zero or another value.

## Important distinction: physical storage versus logical result order

`ORDER BY` determines the order in which rows are returned by a query.

It does not mean:

    "store this table permanently in this order."

Database systems use storage structures, indexes, pages, and execution strategies that are independent of an application's desired presentation order.

The application should request the required order every time it matters.

## Important distinction: ORDER BY versus window ORDER BY

These are different:

    RANK() OVER (
        ORDER BY salary DESC
    )

and:

    ORDER BY salary DESC

The first determines the ordering used by the window function.

The second determines the final result-set ordering.

A query can therefore calculate rankings using one ordering and display the rows using another.

## Important distinction: ORDER BY versus GROUP BY

`GROUP BY` organizes rows into groups for aggregation or grouped processing.

`ORDER BY` organizes the resulting rows for output.

For example:

    GROUP BY department

creates one group per department.

Then:

    ORDER BY average_salary DESC

orders those grouped results.

They solve different problems.

## Important distinction: ORDER BY versus WHERE

`WHERE` determines which rows remain.

`ORDER BY` determines how the remaining rows are arranged.

For example:

    WHERE salary >= 80000

filters employees.

    ORDER BY salary DESC

then sorts the qualifying employees.

A row can therefore be excluded before sorting because it does not satisfy the filter.

## Script structure

The Python script is organized as a progressive practical lesson.

It includes:

- database creation
- sample relational data
- basic `ORDER BY`
- explicit `ASC`
- `DESC`
- text sorting
- multiple-column sorting
- tie-breaking
- aliases
- calculated expressions
- NULL identification
- default NULL behavior
- `NULLS FIRST`
- `NULLS LAST`
- CASE-based NULL ordering
- `COALESCE`
- `LIMIT`
- `OFFSET`
- pagination
- aggregate sorting
- `HAVING`
- custom business ordering
- collation
- date sorting
- ordinal ordering
- `DISTINCT`
- top-N queries
- window functions
- ranking functions
- safe dynamic sorting
- SQL injection considerations
- indexes
- query plans
- keyset pagination
- edge cases
- tests
- production design considerations

The database is created in memory, so running the script does not create or modify an external database file.

## Testing considerations

Sorting logic should be tested rather than assumed.

The script uses assertions to verify:

- ascending salary order
- descending salary order
- deterministic tie-breaking
- explicit NULLS LAST behavior

For production applications, additional tests should reflect actual business requirements.

Examples include:

- all values equal
- all values NULL
- one NULL among many values
- negative values
- duplicate values
- empty result sets
- pagination boundaries
- changes between pagination requests
- different collations
- invalid dynamic sort options

The tests should verify the required business ordering rather than merely checking that a query executes successfully.

## Reference syntax

Basic ascending order:

    ORDER BY column ASC

Basic descending order:

    ORDER BY column DESC

Multiple columns:

    ORDER BY column_a ASC, column_b DESC

Explicit NULLS FIRST:

    ORDER BY column ASC NULLS FIRST

Explicit NULLS LAST:

    ORDER BY column ASC NULLS LAST

CASE-based NULLS LAST:

    ORDER BY
        CASE WHEN column IS NULL THEN 1 ELSE 0 END,
        column ASC

Deterministic ordering:

    ORDER BY score DESC, id ASC

Top-N:

    ORDER BY score DESC, id ASC
    LIMIT 10

Offset pagination:

    ORDER BY score DESC, id ASC
    LIMIT 10 OFFSET 20

Custom business ordering:

    ORDER BY
        CASE status
            WHEN 'High' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 3
            ELSE 4
        END

Aggregate ordering:

    GROUP BY department
    ORDER BY AVG(salary) DESC

Window-function ordering:

    RANK() OVER (
        PARTITION BY department
        ORDER BY salary DESC
    )

## Core principles demonstrated by the script

The most important technical rules represented in the implementation are:

`ORDER BY` explicitly defines result ordering.

`ASC` specifies ascending order.

`DESC` specifies descending order.

Multiple expressions are evaluated from left to right according to their sorting priority.

A unique final tie-breaker makes ordering deterministic.

`NULL` is not equivalent to zero, an empty string, or false.

Use `IS NULL` and `IS NOT NULL` to test for NULL.

Default NULL ordering can differ across database systems.

Use explicit NULL ordering or CASE-based logic when NULL placement matters.

`LIMIT` should normally be combined with a meaningful `ORDER BY` when selecting top-N rows.

Pagination benefits from deterministic ordering.

Large OFFSET values can become inefficient.

Keyset pagination can reduce deep-offset costs when implemented with a compatible ordering and index.

`ORDER BY` can sort calculated expressions, aliases, aggregates, and window-function results.

Collation affects text ordering.

Indexes can sometimes reduce sorting work, but index usefulness depends on the complete query and database optimizer.

Dynamic sorting requires validation and allow-listing of identifiers and directions.

Sorting is a presentation and query-processing requirement, not an authorization mechanism.
