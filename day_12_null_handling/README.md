# SQL NULL handling

## Topic introduction

SQL `NULL` represents the absence of a known value. It is one of the most important concepts in relational database programming because it does not behave like an ordinary value.

A `NULL` value can represent different business situations depending on the schema and application:

- A value has not been provided.
- A value is currently unknown.
- A value has not yet been determined.
- A relationship does not currently exist.
- A piece of information is unavailable.

The exact meaning should be defined by the data model. `NULL` should not automatically be interpreted as zero, an empty string, `FALSE`, or a literal string containing the word `NULL`.

The accompanying Python script uses SQLite through Python's built-in `sqlite3` module. The database contains employees, departments, customers, orders, and products so that NULL behavior can be examined through realistic queries rather than isolated expressions.

The central ideas are:

- SQL uses three-valued logic.
- Ordinary comparisons with `NULL` normally produce `UNKNOWN`.
- `IS NULL` tests for NULL.
- `IS NOT NULL` tests for a non-NULL value.
- `COALESCE` supplies the first non-NULL value.
- `NULLIF` converts a matching value into NULL.
- NULL affects filtering, joins, aggregation, grouping, ordering, constraints, subqueries, and reporting.

## Fundamental concept: NULL is not an ordinary value

Consider these different states:

- `salary = NULL`
- `salary = 0`
- `salary = ''`
- `salary = 'NULL'`

They have different meanings.

A salary of `0` is a known numerical value. An empty string is a known textual value. The text `'NULL'` is simply four characters. SQL `NULL` indicates that the value itself is absent or unknown.

This distinction has practical consequences. A payroll report should not automatically treat an unknown salary as zero unless the reporting requirement explicitly defines that interpretation.

The Python script creates employees with missing departments, salaries, bonuses, managers, and email addresses to demonstrate this distinction.

## SQL three-valued logic

Traditional Boolean logic has two states:

- `TRUE`
- `FALSE`

SQL introduces a third state:

- `UNKNOWN`

This occurs because comparisons involving NULL generally cannot establish whether the comparison is true or false.

For example:

- `NULL = NULL` produces `UNKNOWN`.
- `NULL <> NULL` produces `UNKNOWN`.
- `10 = NULL` produces `UNKNOWN`.
- `10 > NULL` produces `UNKNOWN`.

The critical point is that `NULL` does not mean "equal to nothing." Instead, it represents a value whose identity or existence is not known in the relevant context.

SQL therefore cannot conclude that two unknown values are equal merely because both are NULL.

## NULL and the WHERE clause

A `WHERE` clause retains rows when its predicate evaluates to `TRUE`.

Rows for which the predicate evaluates to `FALSE` are removed.

Rows for which the predicate evaluates to `UNKNOWN` are also removed.

This explains an important query:

`WHERE salary > 70000`

An employee with a salary of `90000` satisfies the condition.

An employee with a salary of `60000` does not.

An employee with `salary = NULL` does not satisfy the condition because SQL cannot establish that an unknown salary is greater than `70000`.

The condition is `UNKNOWN`, not `FALSE`.

This distinction becomes particularly important when negative conditions are used.

## Why `= NULL` is incorrect

A common beginner mistake is:

`WHERE department = NULL`

This does not correctly find rows where `department` is NULL.

The correct form is:

`WHERE department IS NULL`

Similarly, this is incorrect for finding non-NULL values:

`WHERE department <> NULL`

The correct expression is:

`WHERE department IS NOT NULL`

The reason is that equality and inequality are ordinary comparison operators. NULL requires explicit NULL-testing operators.

## IS NULL

`IS NULL` evaluates whether an expression is NULL.

Typical examples include:

`WHERE manager_id IS NULL`

`WHERE salary IS NULL`

`WHERE email IS NULL`

It is useful when a query needs to find incomplete, unavailable, or not-yet-recorded information.

A NULL test is a predicate about the state of a value rather than an ordinary comparison with another value.

## IS NOT NULL

`IS NOT NULL` identifies values that are present.

For example:

`WHERE salary IS NOT NULL`

returns employees whose salary has a stored value.

It does not imply that the value is valid for every business purpose. A non-NULL value could still be zero, negative, malformed, or otherwise invalid if the schema permits it.

NULL handling and data validation are related but separate concerns.

## AND with NULL

SQL's three-valued logic produces important results for `AND`.

The relevant rules include:

- `TRUE AND TRUE` → `TRUE`
- `TRUE AND FALSE` → `FALSE`
- `TRUE AND UNKNOWN` → `UNKNOWN`
- `FALSE AND UNKNOWN` → `FALSE`
- `UNKNOWN AND UNKNOWN` → `UNKNOWN`

The `FALSE AND UNKNOWN` case is particularly useful for understanding why some predicates eliminate rows even when another part contains NULL.

For example:

`salary > 70000 AND department = 'Engineering'`

If salary is NULL, the first condition is UNKNOWN. If the department condition is FALSE, the complete `AND` expression becomes FALSE.

If the department condition is TRUE, the complete result remains UNKNOWN.

Either way, a WHERE clause does not retain the row unless the complete predicate is TRUE.

## OR with NULL

Important `OR` rules include:

- `TRUE OR UNKNOWN` → `TRUE`
- `FALSE OR UNKNOWN` → `UNKNOWN`
- `UNKNOWN OR UNKNOWN` → `UNKNOWN`

This makes explicit NULL handling important.

For example:

`salary > 70000 OR salary IS NULL`

deliberately includes both employees with high salaries and employees whose salaries are missing.

Without the `salary IS NULL` branch, missing salaries would not be included.

## NOT and UNKNOWN

SQL does not turn UNKNOWN into TRUE through `NOT`.

The logical behavior is:

- `NOT TRUE` → `FALSE`
- `NOT FALSE` → `TRUE`
- `NOT UNKNOWN` → `UNKNOWN`

This explains why:

`WHERE NOT (salary > 70000)`

does not return employees whose salary is NULL.

For those employees, `salary > 70000` is UNKNOWN, and the negation remains UNKNOWN.

## COALESCE

`COALESCE` returns the first non-NULL expression.

The general structure is:

`COALESCE(expression1, expression2, expression3, ...)`

For example:

`COALESCE(bonus, 0)`

returns the bonus when it exists and `0` when the bonus is NULL.

Another example is:

`COALESCE(city, 'Unknown city')`

which provides a display value when the city is missing.

Multiple fallbacks are possible:

`COALESCE(phone, email, 'No contact information')`

The database evaluates the expressions from left to right and returns the first non-NULL value.

## COALESCE and business meaning

`COALESCE` is technically simple but conceptually important.

Replacing NULL with zero is not automatically correct.

Suppose an order has:

- amount = `1500`
- discount = `NULL`

There are at least two possible interpretations.

The NULL could mean:

- The customer received no discount.

Or it could mean:

- The discount information is missing.

If NULL means "no discount," then:

`amount - COALESCE(discount, 0)`

may be appropriate.

If NULL means "discount data is unavailable," treating it as zero can produce a misleading financial result.

The choice of fallback should therefore come from the business definition of the column.

## NULL propagation through arithmetic

Many arithmetic operations involving NULL produce NULL.

Examples include:

- `10 + NULL`
- `10 - NULL`
- `10 * NULL`
- `10 / NULL`

The result is generally unknown because one of the required inputs is unknown.

This is why:

`salary + bonus`

can return NULL when either salary or bonus is NULL.

If the business rule explicitly states that a missing bonus means zero, then:

`COALESCE(salary, 0) + COALESCE(bonus, 0)`

can produce a numeric result.

This does not make the original data non-NULL. It only changes the value produced by that particular expression.

## NULLIF

`NULLIF(a, b)` returns NULL when `a` and `b` are equal. Otherwise it returns `a`.

Conceptually:

`NULLIF(value, unwanted_value)`

converts a particular value into NULL.

For example:

`NULLIF('', '')`

converts an empty string into NULL.

This is useful in data cleaning when an application uses an empty string as a missing-value marker.

`NULLIF` is also commonly used to protect division:

`numerator / NULLIF(denominator, 0)`

If the denominator is zero, `NULLIF` changes it to NULL, allowing the expression to produce NULL rather than attempting division by zero.

The semantic meaning should still be considered. A mathematically undefined ratio is not the same thing as a valid zero ratio.

## COALESCE and NULLIF together

The two functions can form a useful data-cleaning pattern.

For example:

`COALESCE(NULLIF(TRIM(value), ''), 'Unknown')`

performs several conceptual steps:

- Remove surrounding whitespace.
- Convert an empty result into NULL.
- Replace NULL with a display fallback.

This pattern should be used deliberately because normalization rules are part of data modeling, not merely formatting.

## NULL and IN

NULL creates subtle behavior with `IN`.

Consider:

`30 IN (10, 20, NULL)`

There is no match with `10` or `20`, but the presence of NULL prevents SQL from proving that the complete condition is false. The result can therefore be UNKNOWN.

By contrast:

`20 IN (10, 20, NULL)`

is TRUE because a definite match exists.

This distinction becomes particularly dangerous with `NOT IN`.

## The NOT IN trap

A classic SQL bug occurs when `NOT IN` is used against a subquery that can return NULL.

Conceptually:

`WHERE customer_id NOT IN (subquery)`

If the subquery contains NULL, comparisons against values not otherwise found can become UNKNOWN.

As a result, rows that appear logically eligible may disappear from the result.

The Python script demonstrates this with a `blocked_customers` table containing both a real customer ID and NULL.

When nullable subquery values are possible, `NOT EXISTS` is often a safer and clearer anti-join pattern:

`WHERE NOT EXISTS (...)`

The inner condition compares actual candidate values and does not suffer from the same `NOT IN` NULL trap.

## EXISTS and NOT EXISTS

`EXISTS` asks whether a subquery returns at least one row.

`NOT EXISTS` asks whether the subquery returns no rows.

This makes them particularly useful for relationship-based filtering.

For example, finding customers with at least one order can use `EXISTS`.

Finding customers with no orders can use `NOT EXISTS`.

The decision is based on row existence rather than attempting to compare a value against a potentially NULL-containing list.

## NULL and DISTINCT

`DISTINCT` removes duplicate result values.

NULL participates in duplicate elimination as a grouping value for this purpose.

A query such as:

`SELECT DISTINCT department FROM employees`

therefore produces one NULL category even if multiple employees have NULL departments.

This should not be interpreted as saying that NULL equals NULL under ordinary comparison. Set and duplicate-elimination semantics are different from equality comparison semantics.

## NULL and GROUP BY

`GROUP BY` groups rows having NULL in the same grouping category.

For example:

`GROUP BY department`

produces a group representing employees whose department is NULL.

This is useful in data-quality reporting because missing values can be counted as a category.

A report can therefore show:

- Engineering
- Finance
- Marketing
- Human Resources
- NULL department

The presentation layer may rename the NULL category as "Unassigned" using `COALESCE`, but the underlying database value remains NULL.

## Aggregate functions and NULL

NULL has important aggregate behavior.

Common aggregate functions generally ignore NULL inputs:

- `SUM(column)`
- `AVG(column)`
- `MIN(column)`
- `MAX(column)`

`COUNT` requires special attention.

`COUNT(*)` counts rows.

`COUNT(column)` counts non-NULL values in that column.

Therefore:

`COUNT(*)`

and:

`COUNT(salary)`

answer different questions.

The first asks how many rows exist.

The second asks how many rows contain a non-NULL salary.

## AVG and missing values

`AVG(salary)` ignores NULL salaries.

This means it calculates the average among rows with known salaries.

It does not treat missing salaries as zero.

That differs from:

`AVG(COALESCE(salary, 0))`

The second expression explicitly introduces zero into the calculation for rows with missing salaries.

These expressions answer different analytical questions.

This distinction is especially important in financial, operational, HR, scientific, and statistical reporting.

## COUNT DISTINCT and NULL

`COUNT(DISTINCT column)` counts distinct non-NULL values.

A NULL value is not counted as a normal distinct value by `COUNT`.

Therefore, if a column contains:

- Engineering
- Engineering
- Finance
- NULL
- NULL

`COUNT(DISTINCT column)` returns two.

The NULL category can be counted separately when required.

## HAVING and NULL

`HAVING` filters groups after aggregation and follows SQL's logical treatment of predicates.

For example:

`HAVING AVG(salary) > 65000`

does not select a group merely because some salaries are known. If the aggregate result itself is NULL, the comparison becomes UNKNOWN.

This is important when a group contains no non-NULL values.

## NULL and ORDER BY

The position of NULL values in ordering can differ across database systems.

Applications should not assume that every database places NULL first or last by default.

If a particular order is required, it is safer to express that intention explicitly.

The script demonstrates patterns such as:

`ORDER BY salary IS NULL, salary`

to place known salaries before NULL salaries in SQLite.

Database-specific syntax may also provide explicit NULL ordering options.

## NULL and CASE

A searched `CASE` expression can test NULL explicitly:

`CASE
    WHEN salary IS NULL THEN 'Salary unavailable'
    WHEN salary = 0 THEN 'Zero salary'
    ELSE 'Salary available'
END`

This is preferable when the logic depends on NULL state.

A common mistake is attempting to use:

`CASE department
    WHEN NULL THEN ...
END`

as though NULL could be matched by ordinary equality.

A searched CASE with `department IS NULL` expresses the intended semantics correctly.

## NULL and joins

Ordinary joins commonly use equality:

`ON a.key = b.key`

If both keys are NULL, the equality comparison is UNKNOWN, so the rows do not match.

This is different from the intuitive statement "both values are missing, therefore they should match."

If the business requirement is that two NULLs should be treated as equivalent, a NULL-safe comparison must be used.

The exact syntax depends on the database system.

SQLite supports NULL-safe comparison through its `IS` operator.

PostgreSQL provides the standard-style:

`IS NOT DISTINCT FROM`

MySQL provides:

`<=>`

These are related concepts but should not be assumed to have identical syntax across all database engines.

## LEFT JOIN and generated NULL values

`LEFT JOIN` introduces an important source of NULL values.

When a row on the left has no matching row on the right, columns from the right side appear as NULL in the result.

For example, a customer without an order can still appear in a customer report, with order columns represented as NULL.

These are not necessarily NULL values stored in the underlying orders table. They can be NULLs introduced by the join operation itself.

This distinction is important when interpreting query results.

## ON versus WHERE with LEFT JOIN

Consider:

`LEFT JOIN orders AS o
 ON c.customer_id = o.customer_id`

followed by:

`WHERE o.shipped_date IS NOT NULL`

The WHERE clause removes rows where the joined order is absent or its shipment date is NULL.

This can make the result behave like a much more restrictive join.

If the requirement is to preserve every customer while joining only orders that have shipped, the condition can instead be placed in the `ON` clause.

This is one of the most important practical NULL-related join patterns.

## NULL and UNIQUE constraints

A nullable column with a UNIQUE constraint has behavior that surprises many beginners.

In SQLite, multiple NULL values can exist in a UNIQUE column.

The reason is connected to NULL semantics: NULL does not behave as an ordinary value that compares equal to another NULL under standard equality.

Database-specific constraint and indexing behavior should always be verified when portability matters.

If the business requirement is "at most one missing value," a simple UNIQUE constraint may not express that requirement in the desired way across all database systems.

## NOT NULL constraints

`NOT NULL` is a schema-level constraint that prevents a column from containing NULL.

It should be used when a value is genuinely mandatory.

For example:

`employee_name TEXT NOT NULL`

makes sense if every employee must have a name.

A nullable column is appropriate when the absence of a value is meaningful and expected.

Good database design does not mean eliminating every NULL. It means allowing NULL where its semantics are valid and preventing it where the value is mandatory.

## CHECK constraints and NULL

NULL requires careful thought when writing CHECK constraints.

A CHECK expression involving NULL can evaluate to UNKNOWN rather than FALSE. Database systems have specific rules for how CHECK constraints treat that result.

This means a constraint such as:

`CHECK (age >= 0)`

does not necessarily mean "age must be present and non-negative."

If age is mandatory, the schema should also use:

`age INTEGER NOT NULL CHECK (age >= 0)`

The two constraints solve different problems:

- `NOT NULL` controls presence.
- `CHECK` controls an allowed condition.

## NULL and foreign keys

A nullable foreign key can represent an optional relationship.

For example:

`manager_id NULL`

can mean that no manager is currently recorded for an employee.

This is generally preferable to inventing a fake manager ID such as `0` when no relationship exists.

A foreign key therefore can be nullable without being poorly designed. The decision depends on whether the relationship is mandatory or optional.

## NULL and dates

A missing date should normally be represented by NULL when the date is genuinely unknown or unavailable.

Inventing a date such as `1900-01-01` creates a sentinel value with an artificial meaning.

A query such as:

`WHERE shipped_date IS NULL`

can directly represent "not shipped or shipment date not recorded," depending on the application's business definition.

If the business requires distinguishing "not yet shipped" from "shipment date unknown," separate status information may be needed rather than overloading one nullable date column.

## NULL and calculations

Financial and operational calculations often expose NULL semantics.

For an order:

`amount - discount`

returns NULL when discount is NULL.

If NULL means "no discount," then:

`amount - COALESCE(discount, 0)`

may be appropriate.

If NULL means "discount information is missing," the fallback of zero is misleading.

The important principle is that NULL handling is not merely a technical transformation. It changes the meaning of the result.

## Safe ratios

Ratios require two separate considerations:

- NULL denominator
- Zero denominator

A NULL denominator means the denominator is unknown.

A zero denominator is known but mathematically unsuitable for division.

A common SQL pattern is:

`numerator / NULLIF(denominator, 0)`

This converts a zero denominator into NULL and prevents a division-by-zero condition.

The resulting NULL should then be interpreted according to the reporting requirements.

## NULL and string functions

Many SQL functions propagate NULL.

For example:

`LENGTH(NULL)`

returns NULL in SQLite.

If a display calculation requires a fallback:

`LENGTH(COALESCE(phone, ''))`

can provide a numeric length for missing phone values.

This does not mean the phone number exists. It only defines how the expression should behave.

## NULL and empty strings

NULL and empty strings are distinct concepts.

An empty string is a value with zero characters.

NULL means that the value is absent or unknown.

The distinction is especially important for data-quality processing.

Some database engines have behavior that differs from SQLite, so SQL portability requires attention to the target database's treatment of empty strings.

## Python None and SQL NULL

When Python communicates with SQLite through `sqlite3`, Python's `None` maps naturally to SQL NULL.

For example, a parameter tuple containing:

`None`

can insert a SQL NULL.

When a SQL NULL is retrieved, it is represented as Python `None`.

This makes Python-to-SQL integration straightforward, but the SQL semantics remain unchanged.

Passing `None` as a parameter does not make this predicate correct:

`WHERE department = ?`

with a parameter value of `None`.

The correct predicate is still:

`WHERE department IS NULL`

Application code may therefore need to choose between `IS NULL` and ordinary equality depending on the supplied parameter.

## Parameterized SQL

SQL values should be passed as parameters rather than inserted into query strings through string concatenation.

Parameterized queries provide safer and more predictable value handling.

For NULL specifically, the application should distinguish between:

- a normal parameter value
- a Python `None` value representing SQL NULL

The SQL predicate itself still needs to express the correct NULL semantics.

## Dynamic NULL filtering

Applications frequently have optional filters.

A search parameter can have two meanings:

- A real value means search for that value.
- `None` means search for rows where the database column is NULL.

The query structure should reflect that distinction.

The Python script demonstrates a function that selects an `IS NULL` predicate when the supplied Python value is `None`, while using a parameterized equality predicate for ordinary values.

This is preferable to attempting to force one equality expression to handle both cases.

## NULL and indexes

Nullable columns can be indexed.

Whether a particular `IS NULL` or `IS NOT NULL` predicate uses an index depends on the database engine, index structure, statistics, data distribution, query plan, and other optimizer decisions.

The script creates an index and examines SQLite's query plan.

The important performance principle is not to assume that every NULL query is either automatically fast or automatically slow.

Execution plans should be examined for important production queries.

## COALESCE in predicates and performance

A query such as:

`WHERE COALESCE(department, 'UNKNOWN') = 'Engineering'`

can be less optimizer-friendly than directly expressing:

`WHERE department = 'Engineering'`

because applying a function to a column can affect ordinary index usage in some database systems.

If NULL rows must also be included, explicit logic is often clearer:

`WHERE department = 'Engineering'
   OR department IS NULL`

The best formulation depends on the required semantics and database engine.

Functional or expression indexes can sometimes support function-based predicates, but they should be introduced based on measured workload requirements.

## NULL sentinels

Legacy systems sometimes represent missing data with sentinel values such as:

- `-1`
- `0`
- `'UNKNOWN'`
- `'N/A'`
- `'1900-01-01'`

Sentinels create problems when the sentinel is also a valid business value.

For example, if zero is a legitimate score, using zero to mean "score missing" makes the two states impossible to distinguish.

NULL is generally preferable when the relational meaning is genuinely "no known value."

Existing systems may still require sentinel handling, in which case `NULLIF` can help normalize the data.

## Data cleaning

A practical NULL-cleaning workflow can involve:

- trimming text
- identifying empty strings
- identifying legacy sentinel values
- converting those values to NULL
- preserving legitimate values
- applying display or calculation fallbacks only where appropriate

For example:

`NULLIF(TRIM(value), '')`

can turn blank text into NULL.

A later `COALESCE` can provide a presentation fallback.

This separates data normalization from display decisions.

## NULL and subqueries

A subquery can itself produce NULL.

For example, an aggregate over an empty logical set can produce NULL.

If that subquery participates in arithmetic or comparison, NULL semantics propagate into the outer query.

`COALESCE` can be applied around the subquery when a fallback is genuinely required.

This is another situation where developers must distinguish between:

- "there is no result"
- "the result is zero"
- "the result is unknown"

Those states are not inherently interchangeable.

## Window functions

Window functions can also encounter NULL.

For example:

`AVG(salary) OVER (PARTITION BY department)`

generally ignores NULL salary values when computing the average.

NULL ordering also matters inside window functions.

If employees are ranked by salary, the position of employees with NULL salary should be intentionally defined.

The script demonstrates explicit ordering so that the ranking policy does not depend solely on the database's default NULL ordering.

## Set operations

Set operations such as `UNION` and `UNION ALL` have their own duplicate-elimination semantics.

`UNION` removes duplicate result rows.

`UNION ALL` retains all rows.

NULL participates in duplicate elimination according to set-operation rules. This should not be confused with the ordinary equality expression `NULL = NULL`.

SQL contains several semantic layers, and NULL behavior must be understood in the context of the operation being performed.

## INSERT, defaults, and NULL

A column with a DEFAULT value behaves differently depending on whether the column is omitted or explicitly supplied as NULL.

For example, if:

`status TEXT DEFAULT 'Pending'`

the column can receive `'Pending'` when omitted from an INSERT.

Explicitly supplying NULL generally stores NULL instead of invoking the default.

This distinction is important when application code builds INSERT statements dynamically.

A default answers the question:

"What value should be used when the column is not supplied?"

It does not mean:

"What should happen whenever the column is NULL?"

## UPDATE and DELETE

NULL requires the same correct predicate syntax in data modification statements.

Incorrect:

`UPDATE employees
 SET bonus = 0
 WHERE bonus = NULL`

Correct:

`UPDATE employees
 SET bonus = 0
 WHERE bonus IS NULL`

The same rule applies to DELETE operations.

The script demonstrates these operations against controlled tables.

## Common mistakes

### Using `= NULL`

Incorrect:

`WHERE column = NULL`

Correct:

`WHERE column IS NULL`

### Using `<> NULL`

Incorrect:

`WHERE column <> NULL`

Correct:

`WHERE column IS NOT NULL`

### Assuming NULL equals zero

NULL means unknown or absent.

Zero is a known numeric value.

### Assuming NULL equals an empty string

NULL and empty string are separate states in SQLite and many other database systems.

### Treating NULL as FALSE

NULL is not FALSE.

It represents UNKNOWN in expressions that cannot determine a Boolean result.

### Assuming NOT UNKNOWN is TRUE

`NOT UNKNOWN` remains UNKNOWN.

### Using NOT IN against nullable data

A NULL in the comparison set can cause unexpected UNKNOWN results.

`NOT EXISTS` is often safer when nullable subquery values are possible.

### Replacing every NULL with zero

This can corrupt analytical meaning.

A missing salary is not necessarily a zero salary.

### Misusing COALESCE

`COALESCE` should express a deliberate business rule, not merely suppress NULL output.

### Filtering the right side of a LEFT JOIN in WHERE

This can remove NULL-extended rows and unintentionally change the effective result set.

### Ignoring COUNT semantics

`COUNT(*)` counts rows.

`COUNT(column)` excludes NULL values.

## Best practices

Use `IS NULL` and `IS NOT NULL` for NULL detection.

Treat NULL as a distinct semantic state rather than as zero, false, or an empty string.

Understand SQL's three-valued logic before designing complex predicates.

Remember that `WHERE` retains only predicates that evaluate to TRUE.

Use `COALESCE` when the fallback value has a clearly defined business meaning.

Use `NULLIF` when deliberately converting a particular value to NULL or protecting calculations such as ratios.

Use `NOT EXISTS` carefully when nullable subquery values make `NOT IN` unsafe.

Distinguish `COUNT(*)` from `COUNT(column)`.

Check whether aggregate functions ignore NULL before interpreting their results.

Define NULL ordering explicitly when result order matters.

Use `NOT NULL` when a value is genuinely mandatory.

Use nullable foreign keys when relationships are genuinely optional.

Avoid arbitrary sentinel values unless legacy requirements make them necessary.

Use parameterized SQL from application code.

Test NULL cases explicitly in database logic and application integration.

Review database-specific behavior when SQL portability is required.

## Advanced reporting patterns

NULL-aware reporting frequently combines several SQL features.

A customer report can use:

- `LEFT JOIN` to retain customers without orders.
- `COUNT` to count actual orders.
- `COALESCE` to display zero for an empty total when that interpretation is correct.
- `GROUP BY` to produce one result per customer.
- `IS NULL` when identifying missing information.

A data-quality report can use conditional aggregation:

`SUM(CASE WHEN salary IS NULL THEN 1 ELSE 0 END)`

This counts missing salaries.

A missing-value percentage can then be calculated by dividing the missing count by the total row count, with `NULLIF` protecting the denominator from zero.

These patterns are directly implemented in the Python script.

## Production considerations

NULL handling is partly a query-writing problem and partly a data-modeling problem.

A well-designed system should determine what NULL means for each nullable column.

For example, a nullable `shipped_date` might mean "the order has not shipped." If the system needs to distinguish "not shipped" from "shipment date unavailable," one nullable date column may not be sufficient.

The schema may instead require separate state information.

Similarly, a nullable salary might mean:

- salary has not been entered
- salary is confidential
- salary is not applicable
- salary is temporarily unavailable

Those meanings can require different modeling decisions.

NULL should therefore not be treated as a universal substitute for every type of missing information.

## Security considerations

NULL handling itself is not an injection vulnerability, but SQL statements containing NULL values still need safe application design.

Use parameterized queries instead of constructing SQL through string concatenation.

For example, application values should be bound as parameters rather than manually embedded into SQL text.

When an application needs to switch between `IS NULL` and an equality predicate, generate the appropriate trusted SQL structure while continuing to parameterize ordinary values.

Security and correctness reinforce each other here: explicit query construction makes NULL semantics easier to reason about and reduces injection risk.

## Performance considerations

NULL-aware queries can perform well when supported by appropriate indexes and query structures.

Performance depends on:

- database engine
- index design
- data distribution
- cardinality
- statistics
- optimizer behavior
- query shape
- functions applied to indexed columns
- join conditions
- filtering strategy

A predicate such as `column IS NULL` may be indexable.

A predicate that wraps a column inside `COALESCE` may behave differently depending on the database and available indexes.

Production optimization should therefore be based on actual execution plans and representative data rather than assumptions.

## Important distinctions

| Situation | Appropriate concept |
|---|---|
| Find missing values | `IS NULL` |
| Find present values | `IS NOT NULL` |
| Supply a fallback | `COALESCE` |
| Convert a specific value to NULL | `NULLIF` |
| Compare ordinary known values | `=`, `<>`, `<`, `>`, `<=`, `>=` |
| NULL-safe equality | Database-specific NULL-safe comparison |
| Count every row | `COUNT(*)` |
| Count non-NULL values | `COUNT(column)` |
| Avoid nullable `NOT IN` problems | Often `NOT EXISTS` |
| Prevent zero denominator | `NULLIF(denominator, 0)` |
| Identify missing data in reports | Conditional aggregation |
| Prevent mandatory values from being NULL | `NOT NULL` |
| Represent optional relationships | Nullable foreign key |

## Conceptual mental model

A useful way to reason about SQL NULL is:

1. Ask whether the value is known.
2. If the query needs to test missingness, use `IS NULL`.
3. If the query needs to test presence, use `IS NOT NULL`.
4. If an ordinary comparison involves NULL, expect UNKNOWN.
5. Remember that WHERE keeps TRUE and removes FALSE and UNKNOWN.
6. Use `COALESCE` only when replacing NULL has a valid business interpretation.
7. Check aggregate behavior before interpreting missing values.
8. Pay special attention to `NOT IN`, joins, and LEFT JOIN filtering.
9. Treat schema constraints and query-level NULL handling as separate responsibilities.
10. Verify database-specific behavior when writing portable SQL.

The accompanying script turns each of these principles into executable SQLite examples, including basic predicates, three-valued logic, arithmetic, aggregation, grouping, joins, subqueries, constraints, parameter binding, indexing, reporting, data cleaning, and production-oriented query patterns.
