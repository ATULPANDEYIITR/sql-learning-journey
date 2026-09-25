# HAVING: Filtering Aggregated Results, WHERE vs HAVING

## 1. Topic Introduction

`HAVING` is a SQL clause used to filter groups produced by `GROUP BY`. It is especially important in analytical queries because many business questions are not about individual rows. They are about properties of a collection of rows.

Examples include:

- departments containing at least five employees
- customers with at least ten orders
- products selling more than 1,000 units
- regions generating more than a specified amount of revenue
- employees whose average transaction value exceeds a threshold
- months whose total sales exceed a target

The central distinction is:

| SQL construct | Primary purpose | Operates conceptually on |
|---|---|---|
| `WHERE` | Filters source rows | Individual rows |
| `GROUP BY` | Creates groups | Rows grouped by key |
| Aggregate functions | Calculate group metrics | Groups |
| `HAVING` | Filters aggregated groups | Groups |
| `ORDER BY` | Sorts the result | Result rows |
| `LIMIT` | Restricts the result count | Final result |

A useful mental model is:

`WHERE` asks, "Which rows should participate?"

`GROUP BY` asks, "How should those rows be grouped?"

`HAVING` asks, "Which completed groups should remain?"

---

## 2. Fundamental Concepts

### 2.1 Row-level filtering

Suppose a sales table contains:

- transaction ID
- region
- quantity
- unit price
- transaction date

A query such as:

`WHERE quantity >= 10`

examines each transaction independently.

A transaction containing 12 units qualifies.

A transaction containing 5 units does not qualify.

The database has not yet calculated the total quantity for a region.

### 2.2 Group-level filtering

Consider:

`GROUP BY region`

The database conceptually creates one group for each region.

An aggregate expression such as:

`SUM(quantity)`

then produces one total for each region.

A condition such as:

`HAVING SUM(quantity) >= 40`

examines those regional totals.

This is a group-level condition.

### 2.3 The key distinction

These two expressions are not equivalent:

`WHERE quantity >= 40`

and:

`HAVING SUM(quantity) >= 40`

The first means that individual rows must contain at least 40 units.

The second means that the total quantity across the group must be at least 40.

This distinction is one of the most important ideas in SQL aggregation.

---

## 3. Aggregate Functions

`HAVING` is frequently used with aggregate functions.

### `COUNT(*)`

Counts rows in a group.

Example:

`HAVING COUNT(*) >= 5`

This keeps groups containing at least five rows.

### `COUNT(column)`

Counts non-`NULL` values in a column.

Example:

`HAVING COUNT(customer_email) >= 10`

This is not necessarily the same as `COUNT(*) >= 10`.

### `COUNT(DISTINCT column)`

Counts distinct non-`NULL` values.

Example:

`HAVING COUNT(DISTINCT product_id) >= 3`

This can identify groups associated with at least three different products.

### `SUM(column)`

Calculates the total of a numeric expression.

Example:

`HAVING SUM(quantity) >= 100`

### `AVG(column)`

Calculates an average.

Example:

`HAVING AVG(order_value) >= 1000`

### `MIN(column)`

Finds the smallest value in a group.

### `MAX(column)`

Finds the largest value in a group.

---

## 4. SQL Logical Processing Order

SQL syntax is normally written approximately as:

`SELECT`
`FROM`
`WHERE`
`GROUP BY`
`HAVING`
`ORDER BY`
`LIMIT`

The commonly used logical processing model is:

1. `FROM` and `JOIN`
2. `WHERE`
3. `GROUP BY`
4. Aggregate calculations
5. `HAVING`
6. `SELECT`
7. `ORDER BY`
8. `LIMIT` or `OFFSET`

This explains why `WHERE` and `HAVING` have different responsibilities.

### Step 1: FROM

The database determines the source relation.

### Step 2: WHERE

Individual source rows are filtered.

### Step 3: GROUP BY

Remaining rows are divided into groups.

### Step 4: Aggregation

Functions such as `COUNT`, `SUM`, and `AVG` calculate group-level values.

### Step 5: HAVING

Groups that do not satisfy the aggregate condition are removed.

### Step 6: SELECT

The requested expressions become the result columns.

### Step 7: ORDER BY

The resulting rows are sorted.

### Step 8: LIMIT

The final result may be restricted.

---

## 5. Basic SQL Structure

A standard aggregation query has this structure:

`SELECT grouping_column, aggregate_expression`
`FROM table_name`
`WHERE row_condition`
`GROUP BY grouping_column`
`HAVING aggregate_condition`
`ORDER BY aggregate_expression DESC;`

For example:

`SELECT region, SUM(quantity) AS total_units`
`FROM sales`
`WHERE sale_date >= '2026-01-01'`
`GROUP BY region`
`HAVING SUM(quantity) >= 100`
`ORDER BY total_units DESC;`

The query performs two different types of filtering.

The `WHERE` condition determines which sales participate.

The `HAVING` condition determines which regional groups remain.

---

## 6. Python Implementation

The Python implementation uses the standard-library `sqlite3` module.

No third-party package is required.

The program creates an in-memory relational database containing:

- departments
- employees
- sales

It demonstrates:

- `WHERE`
- `GROUP BY`
- `HAVING`
- `COUNT`
- `SUM`
- `AVG`
- `COUNT(DISTINCT ...)`
- conditional aggregation
- joins
- subqueries
- `NULL`
- date filtering
- ordering
- limits
- parameterized SQL
- correctness tests
- performance considerations
- security considerations

### 6.1 Basic grouping

The Python program executes a query equivalent to:

`SELECT region, COUNT(*) AS transaction_count, SUM(quantity) AS units_sold FROM sales GROUP BY region;`

The result contains one row per region.

### 6.2 WHERE demonstration

The program demonstrates:

`WHERE sale_date >= '2026-02-01'`

This removes January transactions before aggregation.

The resulting groups therefore represent only February and March activity.

### 6.3 HAVING demonstration

The program then demonstrates:

`GROUP BY region`
`HAVING SUM(quantity) >= 40`

The database first calculates the regional totals.

Only after those totals exist can the database determine which regions satisfy the threshold.

### 6.4 WHERE and HAVING together

The most important combined pattern is:

`WHERE sale_date >= '2026-02-01'`

followed by:

`GROUP BY region`

and then:

`HAVING SUM(quantity) >= 30`

The date condition applies to rows.

The quantity condition applies to groups.

### 6.5 Invalid aggregate filtering in WHERE

The Python implementation intentionally attempts:

`WHERE SUM(quantity) >= 40`

This demonstrates why aggregate conditions generally belong in `HAVING`.

`SUM(quantity)` requires a group-level calculation, while `WHERE` operates before grouping.

The correct form is:

`GROUP BY region`
`HAVING SUM(quantity) >= 40`

---

## 7. JavaScript Implementation

The JavaScript implementation deliberately complements the Python implementation.

JavaScript does not provide a SQL database engine as part of the language itself, so the file implements the logical aggregation pipeline with standard JavaScript data structures.

The pipeline is:

1. filter source rows
2. group rows
3. calculate aggregate metrics
4. filter groups
5. sort the resulting groups

This is conceptually equivalent to:

`WHERE -> GROUP BY -> aggregate -> HAVING -> ORDER BY`

### 7.1 `Array.filter()`

JavaScript's `filter()` is used to demonstrate row-level filtering.

For example:

`sales.filter(sale => sale.quantity >= 10)`

is conceptually similar to a SQL `WHERE quantity >= 10` predicate.

### 7.2 `Map`

The JavaScript implementation uses `Map` to construct groups.

A region becomes a grouping key.

Each region maps to an array of sales belonging to that region.

### 7.3 `reduce()`

`reduce()` is used to calculate aggregate values.

For example, a quantity total can be calculated with a reduction equivalent to:

`sales.reduce((sum, sale) => sum + sale.quantity, 0)`

This models the conceptual role of SQL `SUM()`.

### 7.4 Group filtering

Once the aggregate objects exist, JavaScript `filter()` is applied again.

For example:

`groups.filter(group => group.unitsSold >= 40)`

This represents the conceptual role of SQL `HAVING`.

### 7.5 Conditional aggregation

The JavaScript implementation calculates product-specific totals.

For example, laptop quantity is accumulated only when:

`sale.product === "Laptop"`

This corresponds conceptually to SQL conditional aggregation such as:

`SUM(CASE WHEN product = 'Laptop' THEN quantity ELSE 0 END)`

### 7.6 Distinct aggregation

A JavaScript `Set` is used to model distinct values.

This corresponds conceptually to:

`COUNT(DISTINCT product)`

The number of unique values in the `Set` represents the distinct count.

---

## 8. C++ Industry-Style Case Study

The C++ program implements a small sales analytics engine.

The scenario is a regional sales reporting system.

The input consists of transactions containing:

- transaction ID
- employee ID
- date
- product
- region
- quantity
- unit price
- discount

Employees contain:

- employee ID
- name
- department
- salary
- active status

The system produces regional reports containing:

- transaction count
- units sold
- revenue
- active seller count
- average transaction value

### 8.1 Problem being solved

A business wants to identify sales regions that satisfy multiple aggregate requirements.

For example:

- at least four transactions
- at least 30 units sold
- at least 5,000 units of revenue

These requirements are group-level requirements.

They should therefore be applied after aggregation.

### 8.2 Architecture

The C++ implementation separates the analytical pipeline into functions.

`whereFilter()`

Handles row-level filtering.

`groupAndAggregate()`

Creates groups and calculates aggregate metrics.

`havingFilter()`

Filters completed groups.

`orderByRevenueDescending()`

Sorts the final result.

`createReport()`

Coordinates the complete pipeline.

This separation mirrors the conceptual stages of an analytical SQL query.

---

## 9. C++ Data Structures

### `struct Sale`

Represents an individual transaction.

It also provides a `revenue()` member function.

### `struct Employee`

Represents an employee who may be associated with transactions.

### `struct RegionalReport`

Represents the result of grouping sales by region.

### `ReportThresholds`

Contains business-level aggregate thresholds.

### `std::map`

The grouping implementation uses `std::map`.

This provides deterministic ordering of region keys.

### `std::unordered_map`

Employee lookup uses `std::unordered_map`.

This provides efficient average-case lookup by employee ID.

### `std::set`

Distinct sellers and distinct products are represented using sets.

---

## 10. C++ WHERE Stage

The `whereFilter()` function accepts a predicate.

A predicate examines one `Sale` at a time.

For example, the case study can retain only transactions dated on or after February 1, 2026.

This is equivalent conceptually to:

`WHERE sale_date >= '2026-02-01'`

The important point is that the predicate receives an individual transaction rather than a regional report.

---

## 11. C++ GROUP BY Stage

The `groupAndAggregate()` function creates one `RegionalReport` per region.

For each sale, it updates:

- transaction count
- total units
- revenue
- active seller set

The implementation therefore converts many individual records into a smaller collection of aggregate groups.

This is the same conceptual transformation performed by SQL `GROUP BY`.

---

## 12. C++ HAVING Stage

The `havingFilter()` function receives completed `RegionalReport` objects.

It checks:

- transaction count
- total units
- total revenue

For example:

`report.transactionCount >= thresholds.minimumTransactions`

and:

`report.unitsSold >= thresholds.minimumUnits`

and:

`report.revenue >= thresholds.minimumRevenue`

These are group-level conditions.

This is the C++ equivalent of SQL `HAVING`.

---

## 13. WHERE vs HAVING Comparison

| Requirement | Appropriate clause |
|---|---|
| Sale quantity is at least 10 | `WHERE quantity >= 10` |
| Sale occurred after a particular date | `WHERE sale_date >= ...` |
| Employee is active | `WHERE active = 1` |
| Region sold at least 100 units | `HAVING SUM(quantity) >= 100` |
| Region has at least 20 transactions | `HAVING COUNT(*) >= 20` |
| Region's average order exceeds 1,000 | `HAVING AVG(order_value) > 1000` |
| Customer purchased at least five distinct products | `HAVING COUNT(DISTINCT product_id) >= 5` |

The deciding question is whether the condition describes an individual input row or an aggregate group.

---

## 14. HAVING with Multiple Conditions

`HAVING` can contain multiple Boolean conditions.

Example:

`HAVING COUNT(*) >= 4`
`AND SUM(quantity) >= 30`
`AND SUM(revenue) >= 5000`

All conditions must be satisfied when `AND` is used.

`OR` can be used when either condition is sufficient.

Parentheses should be used when complex Boolean expressions require explicit precedence.

---

## 15. HAVING Without GROUP BY

Some SQL dialects allow an aggregate query without an explicit `GROUP BY` to represent a single aggregate result.

For example:

`SELECT COUNT(*) AS transaction_count`
`FROM sales`
`HAVING COUNT(*) >= 100;`

Conceptually, the entire source becomes one aggregate group.

This can be useful for threshold checks.

Exact behavior and portability should be checked against the target database system when writing cross-database SQL.

---

## 16. HAVING and Subqueries

A group-level filter can sometimes be expressed by aggregating inside a subquery and filtering the resulting rows outside.

Example structure:

`SELECT region, total_units`
`FROM (`
`    SELECT region, SUM(quantity) AS total_units`
`    FROM sales`
`    GROUP BY region`
`) AS regional_totals`
`WHERE total_units >= 40;`

The inner query creates the aggregate result.

The outer query treats those aggregates as ordinary rows.

The direct `HAVING` formulation is:

`SELECT region, SUM(quantity) AS total_units`
`FROM sales`
`GROUP BY region`
`HAVING SUM(quantity) >= 40;`

Both express the same conceptual group-level filtering requirement.

A query planner may optimize equivalent formulations differently depending on the database engine.

---

## 17. NULL Behavior

`NULL` requires special attention in aggregate queries.

Important distinctions include:

`COUNT(*)`

Counts rows, including rows where individual columns contain `NULL`.

`COUNT(column)`

Counts only non-`NULL` values.

`SUM(column)`

Normally ignores `NULL` values.

`AVG(column)`

Normally ignores `NULL` values.

A group containing only `NULL` values may produce `NULL` rather than zero for `SUM()`.

A comparison such as:

`SUM(amount) >= 100`

does not become true when the sum is `NULL`.

`NULL` should not automatically be treated as zero.

If a business rule requires a missing aggregate to become zero, an expression such as `COALESCE` may be appropriate:

`COALESCE(SUM(amount), 0)`

The exact behavior should be verified against the database system being used.

---

## 18. Conditional Aggregation

Conditional aggregation combines conditional expressions with aggregate functions.

A common pattern is:

`SUM(CASE WHEN product = 'Laptop' THEN quantity ELSE 0 END)`

This calculates laptop units for each group.

Another condition can calculate monitor units.

The same technique can be used for:

- completed orders
- failed transactions
- high-value transactions
- refunds
- regional sales
- product categories
- customer segments

`HAVING` can then filter groups based on the resulting conditional metric.

---

## 19. JOIN + WHERE + GROUP BY + HAVING

Real analytical queries frequently combine joins and aggregation.

Example:

`SELECT`
`    d.department_name,`
`    COUNT(e.employee_id) AS active_employee_count`
`FROM departments AS d`
`JOIN employees AS e`
`    ON e.department_id = d.department_id`
`WHERE e.active = 1`
`GROUP BY d.department_id, d.department_name`
`HAVING COUNT(e.employee_id) >= 2;`

The stages have different responsibilities.

`JOIN`

Connects related entities.

`WHERE`

Restricts individual joined rows.

`GROUP BY`

Creates department groups.

`HAVING`

Keeps departments satisfying the aggregate requirement.

---

## 20. Common Mistakes

### Mistake 1: Using WHERE for an aggregate

Incorrect concept:

`WHERE SUM(quantity) >= 100`

The aggregate has not yet been produced at the row-filtering stage.

Use:

`HAVING SUM(quantity) >= 100`

### Mistake 2: Confusing a row condition with a total condition

`WHERE quantity >= 10`

does not mean:

"the region sold at least 10 units."

It means:

"retain individual transactions containing at least 10 units."

For the regional total, use:

`HAVING SUM(quantity) >= 10`

### Mistake 3: Forgetting GROUP BY

If separate results are required for each region, the query normally needs:

`GROUP BY region`

### Mistake 4: Misunderstanding COUNT

`COUNT(*)` and `COUNT(column)` have different behavior when `NULL` values are present.

### Mistake 5: Treating NULL as zero

`NULL` represents an unknown or missing value rather than numerical zero.

### Mistake 6: Applying an aggregate condition too early

A business rule concerning a total, average, or count should be evaluated after the relevant aggregation.

---

## 21. Performance Considerations

`WHERE` can reduce the number of source rows before grouping.

This can be important for large datasets.

For example:

`WHERE sale_date >= '2026-01-01'`

may eliminate historical rows that are irrelevant to the report.

The database then has fewer rows to group and aggregate.

Indexes can improve selective row filtering and joins.

Typical candidates may include:

- date columns
- foreign keys
- frequently filtered categorical columns

The actual usefulness of an index depends on:

- data volume
- selectivity
- data distribution
- existing indexes
- database engine
- query plan
- table statistics

`HAVING` generally cannot eliminate a group until the database has enough information to calculate the relevant aggregate.

This is why row-level predicates and aggregate predicates have different optimization opportunities.

Execution plans should be examined for large production queries.

Performance should be measured rather than assumed.

---

## 22. Complexity of the C++ Case Study

Let:

- `n` = number of source sales
- `g` = number of groups

The row-filtering stage is approximately:

`O(n)`

With an ordered `std::map`, grouping is approximately:

`O(n log g)`

Filtering completed groups is:

`O(g)`

Sorting the groups by revenue is:

`O(g log g)`

Therefore, the overall implementation is approximately:

`O(n log g + g log g)`

The report itself requires:

`O(g)`

space.

Distinct-value calculations may require additional memory proportional to the number of unique values retained.

A hash-based grouping structure can provide average-case `O(n)` grouping behavior, but it does not automatically provide sorted output.

The choice between ordered and hash-based grouping is therefore a trade-off involving:

- lookup speed
- ordering requirements
- memory behavior
- determinism
- implementation complexity

---

## 23. Security Considerations

`HAVING` itself is not a security boundary.

A correctly written aggregate condition does not determine whether a user is authorized to view the underlying business information.

Applications should separately enforce:

- authentication
- authorization
- tenant isolation
- row-level access restrictions
- sensitive-data policies

SQL values supplied by users should be passed through parameterized queries.

Avoid constructing SQL by concatenating untrusted values.

Unsafe conceptual pattern:

`"... HAVING SUM(amount) >= " + userInput`

Preferred pattern:

`HAVING SUM(amount) >= ?`

with the value supplied through the database driver's parameter-binding API.

Dynamic table names and column names require a different approach because ordinary value parameters generally cannot represent SQL identifiers.

A trusted allowlist is often appropriate for dynamic identifiers.

---

## 24. Aggregate Reports and Privacy

Aggregate results can sometimes reveal information about individual records.

For example, a report containing only one transaction in a group may indirectly expose information about that transaction.

This matters in:

- employee reporting
- healthcare analytics
- financial systems
- customer analytics
- multi-tenant SaaS applications

Minimum group-size rules can sometimes reduce this risk.

Authorization and data-access policies remain necessary because aggregate filtering alone is not a complete privacy control.

---

## 25. Testing Strategy

Aggregate queries should be tested with cases such as:

1. Empty input
2. One input row
3. One group
4. Multiple groups
5. Exactly-at-threshold values
6. Values just below the threshold
7. Values just above the threshold
8. `NULL` values
9. Duplicate values
10. Multiple distinct values
11. Groups containing no qualifying rows after `WHERE`
12. Impossible `HAVING` thresholds

The Python implementation includes assertions for:

- expected group counts
- threshold filtering
- impossible thresholds
- minimum-unit behavior

The C++ implementation uses `assert()` for the same type of aggregate correctness checks.

The JavaScript implementation uses `console.assert()`.

---

## 26. Edge Cases

### Empty source

An empty input may produce no groups.

### One row

One row can form one group.

### Exact threshold

A condition such as:

`HAVING SUM(quantity) >= 40`

includes a group whose sum is exactly 40.

### Below threshold

A group with 39 units is excluded.

### Above threshold

A group with 41 units is included.

### NULL aggregate

A group with no non-`NULL` numeric values may produce a `NULL` aggregate depending on the function and database behavior.

### Duplicate values

Duplicates are included by ordinary `SUM()` and `COUNT(*)`.

Use `DISTINCT` when uniqueness is part of the business requirement.

---

## 27. Important Distinction: Filtering Rows vs Filtering Groups

Consider these sales:

| Region | Quantity |
|---|---:|
| North | 5 |
| North | 7 |
| North | 9 |
| South | 50 |

Query A:

`WHERE quantity >= 10`

keeps only the South row.

North disappears because none of its individual rows reaches 10.

Query B:

`GROUP BY region`
`HAVING SUM(quantity) >= 10`

keeps North because:

`5 + 7 + 9 = 21`

and also keeps South because:

`50 >= 10`

This simple example demonstrates why moving a condition between `WHERE` and `HAVING` can change the business meaning of a report.

---

## 28. Python, JavaScript, and C++ Roles

The three implementations intentionally demonstrate different perspectives.

### Python

Python is used for direct SQL execution through `sqlite3`.

It demonstrates the actual database behavior of:

- `WHERE`
- `GROUP BY`
- `HAVING`
- aggregate functions
- joins
- subqueries
- `NULL`
- parameterized queries
- SQL errors

This makes Python the database-focused implementation.

### JavaScript

JavaScript demonstrates the conceptual aggregation pipeline using:

- arrays
- `filter()`
- `reduce()`
- `Map`
- `Set`
- classes
- query construction

This makes the row-versus-group distinction visible at the application-data level.

It also demonstrates how application code can construct parameterized SQL rather than mixing untrusted values directly into query text.

### C++

C++ provides a more explicit systems-style implementation.

The program models:

- domain objects
- validation
- lookup structures
- row filtering
- grouping
- aggregation
- group filtering
- ordering
- complexity
- error handling
- correctness tests

The C++ implementation therefore makes the internal mechanics of the analytical pipeline explicit.

---

## 29. Practical Applications

`HAVING` is widely useful in analytical and reporting systems.

### Sales

Find regions whose revenue exceeds a target.

### E-commerce

Find customers with at least five completed orders.

### Finance

Find accounts whose aggregate transaction volume exceeds a threshold.

### Human resources

Find departments containing at least a specified number of employees.

### Operations

Find warehouses processing more than a specified number of shipments.

### Marketing

Find campaigns generating at least a target number of conversions.

### Cybersecurity analytics

Find IP addresses associated with at least a specified number of events.

### Data engineering

Filter aggregated pipeline metrics before downstream reporting.

### Product analytics

Find user cohorts whose average activity exceeds a threshold.

---

## 30. HAVING and Window Functions

`HAVING` and window functions solve different problems.

`HAVING` reduces groups.

A window function calculates a value while retaining the individual rows.

For example, a window expression can calculate a regional total for every transaction without collapsing all transactions into one row per region.

This distinction is important:

- `GROUP BY` generally changes row granularity.
- Window functions generally preserve row granularity.
- `HAVING` filters grouped results.

If a report needs both individual transaction detail and a regional aggregate on every row, a window function may be more appropriate than `GROUP BY` followed by `HAVING`.

---

## 31. HAVING and WHERE in a Single Query

A strong analytical query often follows this structure:

`SELECT grouping_columns, aggregate_metrics`
`FROM source`
`JOIN related_table`
`WHERE row_level_conditions`
`GROUP BY grouping_columns`
`HAVING aggregate_level_conditions`
`ORDER BY aggregate_metrics DESC`

For example:

`SELECT`
`    region,`
`    COUNT(*) AS transactions,`
`    SUM(quantity) AS units,`
`    SUM(quantity * unit_price * (1 - discount)) AS revenue`
`FROM sales`
`WHERE sale_date >= '2026-02-01'`
`GROUP BY region`
`HAVING COUNT(*) >= 4`
`   AND SUM(quantity) >= 30`
`   AND SUM(quantity * unit_price * (1 - discount)) >= 5000`
`ORDER BY revenue DESC;`

The separation is clear:

- date condition: row level
- transaction count: group level
- unit total: group level
- revenue total: group level

---

## 32. Practical Decision Rule

When writing a query, classify each condition before writing SQL.

Ask:

### Question 1

Does the condition describe an individual source record?

Examples:

- sale date
- quantity of one transaction
- employee active status
- individual product category

Use `WHERE`.

### Question 2

Does the condition depend on an aggregate across multiple records?

Examples:

- total sales
- average salary
- number of orders
- number of distinct products
- maximum transaction value

Use `HAVING`.

### Question 3

Does the report need one result per category?

Use `GROUP BY`.

### Question 4

Does the report need individual rows plus aggregate context without collapsing the rows?

Consider a window function.

This classification method prevents many common SQL errors.

---

## 33. Best Practices

1. Use `WHERE` for row-level predicates.
2. Use `HAVING` for aggregate group-level predicates.
3. Keep row filtering separate from aggregate filtering.
4. Use meaningful aggregate aliases.
5. Use explicit grouping columns.
6. Be deliberate about `NULL` behavior.
7. Use `COUNT(*)` when counting rows rather than non-`NULL` column values.
8. Use `COUNT(DISTINCT ...)` when uniqueness matters.
9. Parameterize user-supplied SQL values.
10. Validate dynamic SQL identifiers separately.
11. Test threshold boundaries.
12. Test empty and `NULL` cases.
13. Use execution plans for performance analysis.
14. Avoid unnecessary aggregation.
15. Select only required columns.
16. Apply legitimate selective `WHERE` predicates before grouping.
17. Do not change `WHERE` to `HAVING` merely as a performance experiment because their semantics differ.
18. Use appropriate numeric types for financial calculations.
19. Separate authorization from reporting logic.
20. Document important business thresholds.

---

## 34. Core Concepts Demonstrated by the Three Programs

The Python program demonstrates actual relational database behavior.

The JavaScript program demonstrates the same conceptual pipeline using application-level data structures.

The C++ program demonstrates how a complete analytical reporting system can be implemented explicitly using typed domain models and standard-library algorithms.

Across all three implementations, the central model remains:

`Rows -> WHERE -> Groups -> Aggregate -> HAVING -> Ordered Result`

The most important technical distinction is:

`WHERE` filters before aggregation.

`HAVING` filters after aggregation.

A condition belongs in `HAVING` when the condition depends on the aggregate result of a group.

A condition belongs in `WHERE` when it can be evaluated against an individual input row independently of the group to which that row will eventually belong.
