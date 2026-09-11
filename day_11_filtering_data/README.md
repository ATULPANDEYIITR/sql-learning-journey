# SQL filtering data

## Topic introduction

Filtering is one of the central operations in SQL. It determines which rows from a table should participate in a query result.

The primary SQL mechanism for row filtering is the `WHERE` clause. A `WHERE` condition can compare values, combine several conditions, test ranges, search text patterns, handle missing values, and use subqueries or related tables.

This study script uses Python's built-in `sqlite3` module to execute SQL against an in-memory SQLite database. The database contains employees, departments, customers, orders, products, and sales so that filtering concepts can be demonstrated with realistic data.

The examples progress from basic comparisons to complex business rules, subqueries, joins, aggregation, window functions, performance analysis, and security considerations.

## Fundamental concept of filtering

A basic SQL query has the following conceptual structure:

    SELECT columns
    FROM table
    WHERE condition;

`SELECT` determines which columns are returned.

`FROM` identifies the source table or tables.

`WHERE` determines which rows qualify.

For example, a condition such as:

    WHERE salary > 100000

means that only rows for which the salary is greater than `100000` are retained.

Filtering is performed at the row level. A row either satisfies the condition or does not satisfy it. SQL also has a third logical result, `UNKNOWN`, which is especially important when `NULL` values are involved.

## WHERE clause

The `WHERE` clause contains a Boolean-style search condition.

A simple filter can compare a column with a constant:

    WHERE city = 'Lucknow'

A filter can also compare numeric values:

    WHERE salary >= 100000

A query can contain several predicates:

    WHERE salary >= 90000
      AND age < 40

A predicate is an expression that produces a logical result for filtering.

Common predicates include:

- equality comparisons
- inequality comparisons
- range comparisons
- membership tests
- pattern matching
- NULL tests
- existence tests
- subquery-based conditions

## Comparison operators

The main comparison operators demonstrated in the script are:

| Operator | Meaning |
|---|---|
| `=` | Equal to |
| `<>` | Not equal to |
| `!=` | Not equal to in systems that support it |
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal to |
| `<=` | Less than or equal to |

Examples:

    WHERE salary = 105000

    WHERE salary <> 100000

    WHERE age > 40

    WHERE age < 30

    WHERE salary >= 100000

    WHERE salary <= 80000

`<>` is the standard SQL notation for inequality. `!=` is widely supported but is not necessary when portable SQL is the priority.

## Text comparisons

Text values are normally represented using quoted string literals.

Example:

    WHERE city = 'Lucknow'

Text comparisons can be exact or pattern-based.

An exact comparison asks whether two values match according to the database's comparison rules.

Pattern matching uses `LIKE`.

## AND

`AND` requires all combined conditions to be true.

Example:

    WHERE salary > 90000
      AND age < 40

A row must satisfy both predicates.

`AND` is useful when a filter progressively narrows a population.

A business rule such as:

- employee must be active
- salary must be at least 90000
- age must be below 40

can be represented as:

    WHERE employment_status = 'Active'
      AND salary >= 90000
      AND age < 40

## OR

`OR` requires at least one condition to be true.

Example:

    WHERE city = 'Lucknow'
       OR city = 'Mumbai'

This includes rows from either city.

`OR` normally broadens a result compared with an equivalent `AND` condition.

For a list of alternatives, `IN` is often more readable than a long sequence of `OR` expressions.

## NOT

`NOT` negates a condition.

Example:

    WHERE NOT employment_status = 'Inactive'

It can also be applied to a grouped expression:

    WHERE NOT (city = 'Lucknow' OR city = 'Mumbai')

Negation must be considered carefully when `NULL` is possible because SQL uses three-valued logic rather than simple two-valued Boolean logic.

## Operator precedence

Logical operators have precedence rules.

A commonly used order is:

1. `NOT`
2. `AND`
3. `OR`

Therefore:

    WHERE department_id = 1
       OR department_id = 2
      AND salary > 100000

is generally interpreted as:

    WHERE department_id = 1
       OR (department_id = 2 AND salary > 100000)

It is not interpreted as:

    WHERE (department_id = 1 OR department_id = 2)
      AND salary > 100000

Parentheses should be used whenever the intended logic could be misunderstood.

Explicit grouping is especially important for production queries containing several `AND` and `OR` conditions.

## IN

`IN` checks whether a value belongs to a specified set.

Example:

    WHERE city IN ('Lucknow', 'Mumbai', 'Delhi')

This is usually clearer than:

    WHERE city = 'Lucknow'
       OR city = 'Mumbai'
       OR city = 'Delhi'

`NOT IN` performs the inverse membership test:

    WHERE department_id NOT IN (1, 3)

A significant edge case occurs when `NULL` appears in the values involved in `NOT IN`. Because of SQL's three-valued logic, a `NOT IN` expression containing `NULL` can produce unexpected results.

For relationship-based exclusion, `NOT EXISTS` is often a safer and clearer alternative when nullable values are possible.

## BETWEEN

`BETWEEN` tests whether a value is within an inclusive range.

Example:

    WHERE salary BETWEEN 80000 AND 110000

This is equivalent to:

    WHERE salary >= 80000
      AND salary <= 110000

The lower and upper boundaries are included.

This distinction is important. A value of exactly `80000` satisfies the first example.

## Exclusive and half-open ranges

Some requirements are easier to express with explicit comparison operators.

For example:

    WHERE salary >= 90000
      AND salary < 100000

represents the interval `[90000, 100000)`.

Half-open intervals are especially useful for date and time filtering.

For example:

    WHERE order_date >= '2025-02-01'
      AND order_date < '2025-03-01'

represents all of February without needing to calculate the last possible time of February.

This pattern is useful for adjacent reporting periods because one period can end exactly where the next begins without overlap.

## LIKE

`LIKE` performs pattern matching.

The two important wildcard characters demonstrated are:

| Pattern | Meaning |
|---|---|
| `%` | Zero or more characters |
| `_` | Exactly one character |

Examples:

    WHERE employee_name LIKE 'A%'

matches names beginning with `A`.

    WHERE email LIKE '%@example.com'

matches email addresses ending with `@example.com`.

    WHERE employee_name LIKE '%a%'

matches names containing `a`.

    WHERE employee_name LIKE 'P____'

matches a five-character value beginning with `P`.

Text matching behavior, including case sensitivity and collation, can differ between database systems. SQLite also has behavior that should not automatically be assumed to be identical to PostgreSQL, MySQL, SQL Server, or Oracle.

## NULL

`NULL` represents a missing, unknown, or not-applicable value.

It is not equivalent to:

- zero
- an empty string
- the text `'NULL'`
- `False`

The following is not the correct way to test for NULL:

    WHERE city = NULL

The correct test is:

    WHERE city IS NULL

For non-NULL values:

    WHERE city IS NOT NULL

This distinction is fundamental to SQL filtering.

## Three-valued logic

Traditional Boolean logic has two values:

- TRUE
- FALSE

SQL introduces a third logical state:

- UNKNOWN

Comparisons involving `NULL` frequently produce `UNKNOWN`.

For example:

    NULL = 5

does not evaluate to TRUE or ordinary FALSE. It evaluates to UNKNOWN.

Similarly:

    NULL > 5

is UNKNOWN.

`IS NULL` is specifically designed to test for the NULL state.

A `WHERE` clause returns rows only when its search condition evaluates to TRUE. Rows producing FALSE or UNKNOWN are excluded.

This explains why:

    WHERE city <> 'Lucknow'

does not automatically include rows where `city` is NULL.

## NULL and NOT

Consider:

    WHERE NOT (credit_limit >= 60000)

If `credit_limit` is NULL, the comparison `credit_limit >= 60000` is UNKNOWN.

Negating UNKNOWN does not make it TRUE. It remains UNKNOWN.

Therefore, NULL rows are still excluded.

When the business rule explicitly needs missing values, they should be handled:

    WHERE credit_limit >= 60000
       OR credit_limit IS NULL

## COALESCE

`COALESCE` can provide a replacement value when an expression is NULL.

Example:

    COALESCE(credit_limit, 0)

If `credit_limit` is known, its value is returned.

If it is NULL, `0` is returned.

This can be useful when a business rule explicitly defines how missing values should behave.

It should not be used blindly. Replacing NULL with zero changes the meaning of the data and should reflect an intentional business rule.

## Date filtering

Dates can be filtered using comparison operators.

For ISO-formatted dates:

    YYYY-MM-DD

lexicographical ordering corresponds to chronological ordering when the format is used consistently.

Example:

    WHERE hire_date >= '2020-01-01'

A date range can be written:

    WHERE hire_date >= '2020-01-01'
      AND hire_date < '2024-01-01'

For time-series data, half-open intervals are often preferable to inclusive end dates.

Date storage and filtering behavior depend on the database system and data type. Production systems should use appropriate native date or timestamp types when available rather than relying on text representations without a clear data model.

## Numeric expressions in WHERE

A filter does not have to compare a column directly with a constant.

Expressions can be calculated first.

Example:

    WHERE price * stock_quantity > 100000

This allows a query to filter products according to calculated inventory value.

Another example is a projected salary:

    WHERE salary * 1.10 >= 120000

Expressions are useful for analytical and business calculations, but calculations applied to columns can affect index usage depending on the database engine and available indexes.

## Functions in WHERE

Functions can be used inside filtering expressions.

Examples from the script include:

    WHERE LOWER(city) = 'lucknow'

and:

    WHERE LENGTH(employee_name) > 12

Functions are useful when the filtering requirement genuinely depends on a transformed value.

There is a performance consideration: applying a function to an indexed column may prevent a simple index seek unless the database supports an appropriate functional or expression index.

## CASE expressions

`CASE` provides conditional expression logic.

Example:

    CASE
        WHEN salary >= 120000 THEN 'High'
        WHEN salary >= 90000 THEN 'Medium'
        ELSE 'Standard'
    END

This can classify rows into categories.

A derived `CASE` expression can be filtered by wrapping the query in a subquery or CTE.

This is useful when a business rule is expressed as a classification rather than a direct column comparison.

## Parameterized filtering

Applications should not insert user-controlled values directly into SQL text.

Unsafe construction conceptually resembles:

    SELECT ...
    WHERE city = '<user input>';

If user input is concatenated into SQL, malicious input can potentially alter the SQL statement.

The safer approach uses parameters:

    WHERE salary >= ?
      AND city = ?

The values are passed separately from the SQL statement.

The Python script demonstrates parameterized queries using SQLite placeholders.

Parameterized queries are important for:

- security
- correctness
- escaping
- maintainability
- safe application/database interaction

Parameterized queries should be the standard approach for externally supplied values.

## Dynamic IN lists

A common application requirement is filtering against a variable number of values.

For example, an application might receive:

- Lucknow
- Mumbai
- Delhi

The number of values may change at runtime.

The script creates one parameter placeholder per value rather than inserting the values directly into SQL text.

This maintains parameterization while supporting a dynamic `IN` condition.

## EXISTS

`EXISTS` tests whether a subquery returns at least one row.

Example:

    WHERE EXISTS (
        SELECT 1
        FROM orders AS o
        WHERE o.customer_id = c.customer_id
    )

This asks whether the current customer has at least one matching order.

`EXISTS` is useful for relationship-based filtering.

`NOT EXISTS` asks whether no matching row exists.

For example:

    WHERE NOT EXISTS (
        SELECT 1
        FROM orders AS o
        WHERE o.customer_id = c.customer_id
    )

can identify customers with no orders.

The value returned by `SELECT 1` inside `EXISTS` is not important. The existence of at least one matching row is what matters.

## IN versus EXISTS

Both `IN` and `EXISTS` can express membership relationships, but they communicate different ideas.

`IN` naturally expresses:

"Does this value belong to this set?"

`EXISTS` naturally expresses:

"Does at least one related row exist?"

The optimizer may transform these expressions depending on the database engine.

The choice should consider:

- readability
- NULL behavior
- relationship semantics
- data size
- database optimizer behavior

## Subqueries in WHERE

A subquery can calculate a value used by an outer filter.

Example:

    WHERE salary > (
        SELECT AVG(salary)
        FROM employees
    )

This finds employees earning more than the overall average.

A correlated subquery can reference a value from the outer query.

The script demonstrates:

    WHERE e.salary > (
        SELECT AVG(e2.salary)
        FROM employees AS e2
        WHERE e2.department_id = e.department_id
    )

This compares an employee's salary with the average salary of that employee's department.

Correlated queries are powerful but may be computationally expensive depending on the database engine and data volume. Modern optimizers can sometimes transform them efficiently, but execution plans should be inspected for important production workloads.

## Common table expressions

A Common Table Expression, or CTE, is introduced using `WITH`.

Example:

    WITH active_employees AS (
        SELECT ...
        FROM employees
        WHERE employment_status = 'Active'
    )
    SELECT ...
    FROM active_employees
    WHERE salary >= 100000;

CTEs are useful for breaking complex logic into named stages.

They improve readability and make multi-stage filtering easier to reason about.

A CTE does not automatically mean that the database materializes the intermediate result. Materialization and optimization behavior depend on the database system and query.

## Filtering JOIN results

Filtering becomes more important when multiple tables are involved.

Example:

    SELECT ...
    FROM employees AS e
    INNER JOIN departments AS d
        ON e.department_id = d.department_id
    WHERE d.department_name = 'Engineering'
      AND e.salary >= 100000;

The `JOIN` establishes relationships.

The `WHERE` clause then filters the joined rows.

## WHERE versus ON in LEFT JOIN

This is an important distinction.

Consider:

    FROM customers AS c
    LEFT JOIN orders AS o
        ON c.customer_id = o.customer_id
    WHERE o.status = 'Completed'

The `WHERE` condition removes rows where `o.status` is NULL. As a result, customers without completed orders can disappear.

Compare this with:

    FROM customers AS c
    LEFT JOIN orders AS o
        ON c.customer_id = o.customer_id
       AND o.status = 'Completed'

The condition is part of the matching rule. Customers can still remain even if no completed order exists.

This distinction is essential when preserving unmatched rows is part of the requirement.

## WHERE versus HAVING

`WHERE` and `HAVING` serve different purposes.

`WHERE` filters rows before grouping.

`HAVING` filters groups after aggregation.

Example:

    SELECT customer_id, SUM(amount)
    FROM orders
    WHERE status = 'Completed'
    GROUP BY customer_id
    HAVING SUM(amount) >= 30000;

Here:

- `WHERE status = 'Completed'` removes non-completed order rows.
- `GROUP BY customer_id` forms customer groups.
- `SUM(amount)` calculates group-level spending.
- `HAVING SUM(amount) >= 30000` removes groups whose total is too small.

A common mistake is attempting to use `WHERE` where an aggregate condition belongs in `HAVING`.

## FILTER with aggregates

Some SQL systems support the `FILTER` clause for conditional aggregation.

The script demonstrates:

    COUNT(*) FILTER (WHERE status = 'Completed')

This allows multiple conditional aggregate calculations to be expressed within the same grouped query.

For systems without this feature, equivalent logic can often be implemented with conditional expressions such as `CASE`.

## Conditional aggregation

Conditional aggregation combines aggregate functions with conditional logic.

Example:

    SUM(
        CASE
            WHEN quantity >= 10
            THEN quantity * unit_price
            ELSE 0
        END
    )

This allows different subsets of data to contribute to different metrics within a single grouped query.

Conditional aggregation is common in:

- financial reporting
- sales analysis
- operational dashboards
- customer segmentation
- performance measurement

## Window functions and filtering

Window functions calculate values across related rows while retaining individual rows.

For example:

    RANK() OVER (
        PARTITION BY department_id
        ORDER BY salary DESC
    )

can rank employees within each department.

A window function result generally cannot be referenced directly by `WHERE` at the same query level because the logical processing order places `WHERE` before the window calculation.

The script solves this by calculating the rank in a CTE and filtering the resulting column in the outer query.

This pattern is useful for requirements such as:

- top N employees per department
- top products per category
- highest-value transactions
- ranked customer segments

## Logical query processing

A useful conceptual model for a SELECT query is:

1. `FROM` and `JOIN`
2. `WHERE`
3. `GROUP BY`
4. `HAVING`
5. `SELECT`
6. `ORDER BY`
7. `LIMIT`

This is a logical processing model rather than a guarantee of the physical execution order.

Database optimizers can rearrange operations when doing so preserves the result and improves performance.

The distinction matters because SQL syntax order and logical evaluation order are not always identical to the physical execution plan.

## DISTINCT and filtering

`DISTINCT` removes duplicate result rows after the selected expressions have been considered.

Example:

    SELECT DISTINCT city
    FROM employees
    WHERE city IS NOT NULL;

The `WHERE` clause first restricts the rows to known cities, then `DISTINCT` returns unique city values.

## LIMIT and filtering

`LIMIT` restricts how many final rows are returned.

Example:

    SELECT employee_name, salary
    FROM employees
    WHERE employment_status = 'Active'
    ORDER BY salary DESC
    LIMIT 3;

The filtering determines eligible rows, ordering determines their ranking, and `LIMIT` selects the first three rows from the ordered result.

Without a deterministic `ORDER BY`, a `LIMIT` query should not be interpreted as a reliable top-N result.

## Practical filtering patterns

The script demonstrates filtering for realistic scenarios such as:

- active employees
- salary bands
- employees by department
- customers by country
- customers by credit limit
- completed orders
- large orders
- products by category
- products by price
- products with stock
- discontinued products
- customers with or without orders
- customers above a spending threshold
- top employees within departments

These examples illustrate that SQL filtering is fundamentally about converting a business rule into precise predicates.

## Complex business conditions

A complex requirement should be translated into smaller logical units.

For example:

"Find active employees who either work in Engineering and earn at least 100000, or work in Finance and are at least 35 years old."

The corresponding structure is:

    WHERE employment_status = 'Active'
      AND (
            (department_id = 1 AND salary >= 100000)
            OR
            (department_id = 2 AND age >= 35)
          )

The parentheses represent the business rule explicitly.

Complex conditions should be written so that another developer can verify the logic without mentally reconstructing operator precedence.

## Debugging complex filters

When a filter returns unexpected results, adding every condition at once makes debugging difficult.

The script demonstrates incremental debugging:

1. Start with the broad population.
2. Add the first condition.
3. Inspect the row count.
4. Add another condition.
5. Inspect the result again.
6. Add grouped conditions last.
7. Verify the final result.

This approach helps identify the exact predicate responsible for an unexpected result.

A useful debugging technique is also to select the columns used by the filter so the reason for inclusion or exclusion can be inspected directly.

## Performance and indexes

A database may use an index to locate rows satisfying a filter efficiently.

The script creates indexes on frequently filtered columns such as:

- employee salary
- employee department
- customer country
- order customer
- order date
- product category and price

The `EXPLAIN QUERY PLAN` statement is used to inspect how SQLite intends to execute particular filters.

Indexes can improve read performance, but they have costs:

- additional storage
- additional maintenance during INSERT
- additional maintenance during UPDATE
- additional maintenance during DELETE
- possible optimizer trade-offs

An index should not be added to every column automatically.

## Selectivity

A selective predicate matches relatively few rows.

For example:

    WHERE employee_id = 12345

is usually highly selective when employee IDs are unique.

A condition such as:

    WHERE employment_status = 'Active'

may be less selective if nearly every employee is active.

Index usefulness depends on many factors, including:

- data distribution
- table size
- cardinality
- available indexes
- query shape
- database optimizer
- statistics
- storage engine

## Sargability

A predicate is often described as sargable when the database can use an index efficiently to search for qualifying values.

A direct range condition is generally easier to optimize:

    WHERE hire_date >= '2023-01-01'
      AND hire_date < '2024-01-01'

than a function applied directly to the indexed column:

    WHERE strftime('%Y', hire_date) = '2023'

The exact result depends on the database and its indexes. Functional indexes or expression indexes can change the situation.

For performance-sensitive queries, execution plans should be measured rather than assumed.

## LIKE and performance

Pattern matching can have significant performance implications.

A pattern beginning with a wildcard:

    LIKE '%abc%'

often cannot use a normal B-tree index for a simple prefix seek.

A prefix pattern:

    LIKE 'abc%'

can be more index-friendly in database systems that support the relevant optimization and collation requirements.

Text-search requirements may require specialized indexing or search mechanisms at large scale.

## NULL and indexes

NULL behavior varies in details across database engines and index implementations.

The important SQL-level principle is that NULL is not an ordinary value.

Queries should explicitly state whether missing values should:

- be excluded
- be included
- be converted
- be treated as a separate category

## Data type considerations

Filtering works best when data types represent their actual meaning.

Examples:

- salaries should be numeric
- quantities should be numeric
- dates should use an appropriate date representation
- status values should use controlled values
- identifiers should use appropriate key types

Storing numeric values as strings can produce incorrect ordering and comparison behavior.

Inconsistent date formats can make lexical filtering unreliable.

Data modeling therefore directly affects filtering correctness.

## Security considerations

The most important security issue demonstrated in the script is SQL injection.

Unsafe query construction can allow user input to alter SQL syntax.

The safe pattern is parameterized SQL.

Instead of constructing:

    WHERE city = '<input>'

the application should use a parameter placeholder and provide the value separately.

Parameterized queries should be used for:

- search fields
- IDs
- dates
- numeric thresholds
- status values
- user-entered text
- dynamic application filters

SQL identifiers such as table names and column names usually cannot be supplied as ordinary query parameters. When dynamic identifiers are required, applications should use strict allowlists rather than accepting arbitrary user input.

## UPDATE and DELETE safety

`WHERE` is not limited to `SELECT`.

It is also used by:

- `UPDATE`
- `DELETE`

For example, an incorrect or missing `WHERE` clause in an `UPDATE` can modify every row.

An incorrect `DELETE` can remove every matching row.

A reliable operational practice is to first run the intended condition with `SELECT` and inspect the candidate rows.

The script demonstrates this principle without modifying the source dataset.

For important production changes, transactions, backups, auditing, permissions, and controlled deployment procedures are also relevant.

## Common mistakes

### Using `= NULL`

Incorrect:

    WHERE city = NULL

Correct:

    WHERE city IS NULL

### Using `<>` when NULL rows should also be included

This condition:

    WHERE city <> 'Lucknow'

does not include NULL cities.

If the business rule requires NULL cities as well:

    WHERE city <> 'Lucknow'
       OR city IS NULL

### Forgetting BETWEEN is inclusive

`BETWEEN 10 AND 20` includes both 10 and 20.

### Misunderstanding AND and OR precedence

This:

    A OR B AND C

normally means:

    A OR (B AND C)

Use parentheses when the intended rule is:

    (A OR B) AND C

### Overusing OR

Long chains of equality checks can often be expressed more clearly with `IN`.

### Ignoring NULL in NOT IN

`NOT IN` can produce surprising results when NULL values are present.

`NOT EXISTS` can often express the intended relationship more safely.

### Applying functions unnecessarily

A function such as `LOWER(column)` or `DATE(column)` may affect index usage.

### Confusing WHERE and HAVING

`WHERE` filters rows.

`HAVING` filters groups.

### Filtering the right side of a LEFT JOIN in WHERE unintentionally

A condition on the right-side table in `WHERE` can eliminate unmatched rows.

The condition may need to belong in the `ON` clause instead.

### Building SQL with string concatenation

Directly embedding external input into SQL creates security risks.

Use parameters.

## Important comparisons

| Concept | Purpose |
|---|---|
| `WHERE` | Filter individual rows |
| `HAVING` | Filter groups after aggregation |
| `AND` | Require all conditions |
| `OR` | Require at least one condition |
| `NOT` | Negate a condition |
| `IN` | Test membership in a set |
| `NOT IN` | Test non-membership, with NULL caveats |
| `BETWEEN` | Test an inclusive range |
| `LIKE` | Match text patterns |
| `IS NULL` | Test for NULL |
| `IS NOT NULL` | Test for non-NULL |
| `EXISTS` | Test whether a matching row exists |
| `CASE` | Produce conditional values |
| `COALESCE` | Replace NULL with a chosen alternative |

## Filtering versus aggregation

Filtering individual records and filtering aggregated results are different operations.

For example:

    WHERE status = 'Completed'

can remove individual orders before they are grouped.

After grouping:

    HAVING SUM(amount) >= 30000

can remove customer groups whose total spending does not meet the requirement.

The distinction becomes essential in reporting queries.

## Filtering versus joining

A join establishes relationships between rows.

Filtering determines which rows from that relationship should remain.

The two operations are closely related but have different semantic purposes.

For an `INNER JOIN`, many filters can appear in either the join condition or the `WHERE` clause without changing the result under certain circumstances.

For an `OUTER JOIN`, especially `LEFT JOIN`, moving conditions between `ON` and `WHERE` can materially change the result.

## Limitations

SQL filtering is constrained by the quality and structure of the underlying data.

Common limitations include:

- inconsistent data types
- missing values
- incorrect NULL interpretation
- inconsistent text casing
- duplicated records
- poor indexing
- low-selectivity predicates
- inefficient expressions
- complicated joins
- large intermediate result sets
- database-specific syntax differences

A logically correct `WHERE` clause does not guarantee efficient execution.

## Implementation considerations

The Python script uses SQLite because it is available through Python's standard library.

The database is created in memory, so no external database server or external package is required.

The examples use:

    sqlite3.connect(":memory:")

Rows are configured to behave like mappings so columns can be referenced by name.

The script also creates indexes and uses `EXPLAIN QUERY PLAN` to demonstrate that filtering is both a logical and a performance consideration.

## Production considerations

Production filtering requires more than syntactically correct SQL.

Important considerations include:

- correct data types
- appropriate indexes
- parameterized queries
- predictable NULL handling
- explicit business rules
- query plan inspection
- testing with realistic data volumes
- transaction safety
- access control
- auditing for destructive operations
- database-specific behavior
- deterministic ordering when using `LIMIT`
- monitoring of expensive queries

Queries should be evaluated against realistic data distributions rather than only small development datasets.

## Practical applications

SQL filtering is used extensively in:

- customer segmentation
- financial analysis
- sales reporting
- employee analytics
- inventory management
- fraud detection
- operational dashboards
- marketing analysis
- order processing
- compliance reporting
- risk analysis
- business intelligence
- application search
- data quality analysis

Typical requirements can often be translated directly into predicates.

For example:

"Show active Indian customers with credit limits above 50000."

becomes:

    WHERE country = 'India'
      AND status = 'Active'
      AND credit_limit >= 50000

A more complex requirement may combine row filtering, grouping, and aggregate filtering:

    WHERE status = 'Completed'
    GROUP BY customer_id
    HAVING SUM(amount) >= 20000

The important skill is not memorizing isolated operators. It is converting a precise business requirement into correct logical conditions while accounting for NULLs, data types, relationships, and performance.
