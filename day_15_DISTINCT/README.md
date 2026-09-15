# PostgreSQL DISTINCT, duplicate elimination, and DISTINCT ON

## Topic introduction

`DISTINCT` is a PostgreSQL and SQL query feature used to eliminate duplicate rows from a query result. It is important to distinguish ordinary `SELECT DISTINCT` from PostgreSQL's `DISTINCT ON`, because they solve related but different problems.

`SELECT DISTINCT` answers a question such as:

> Which unique values or unique combinations of values occur in this result?

`DISTINCT ON` answers a different question:

> Which one row should be retained for each group of rows, according to a specified ordering?

For example, if an `orders` table contains many orders for every customer, `SELECT DISTINCT customer_id` returns each customer identifier once. It does not select the latest order for each customer.

PostgreSQL's `DISTINCT ON (customer_id)` can select one complete order row for every customer when combined with an appropriate `ORDER BY`.

The three implementations in this project approach the subject from different perspectives:

- Python provides a structured educational implementation of duplicate elimination and one-row-per-group selection.
- JavaScript demonstrates the same logical concepts while also showing validation and dynamic query-structure construction.
- C++ develops an industry-style order-history case study using explicit data structures, sorting, validation, testing, and complexity analysis.

## Fundamental concepts

### Duplicate rows

SQL query results can contain duplicate rows. This is sometimes described using the concept of bag or multiset semantics.

Consider a table containing:

| customer_id | city |
|---:|---|
| 1 | Delhi |
| 2 | Delhi |
| 3 | Mumbai |

A query such as `SELECT city FROM customers` can return:

| city |
|---|
| Delhi |
| Delhi |
| Mumbai |

The repeated `Delhi` values are not necessarily an error. They correspond to different source rows.

`SELECT DISTINCT city FROM customers` changes the result to:

| city |
|---|
| Delhi |
| Mumbai |

The duplicate elimination is applied to the values in the selected result.

### DISTINCT

The basic syntax is:

`SELECT DISTINCT column_name FROM table_name;`

For multiple columns:

`SELECT DISTINCT column_a, column_b FROM table_name;`

The important rule is that `DISTINCT` applies to the complete selected row.

Suppose the source contains:

| name | city |
|---|---|
| Alice | Delhi |
| Alice | Delhi |
| Alice | Mumbai |

`SELECT DISTINCT name, city` returns:

| name | city |
|---|---|
| Alice | Delhi |
| Alice | Mumbai |

The two rows are different because their complete `(name, city)` combinations differ.

DISTINCT does not independently remove duplicates from every column.

### DISTINCT and SELECT

Without `DISTINCT`, PostgreSQL normally preserves the multiplicity of qualifying rows.

`SELECT city FROM customers`

can return the same city multiple times.

`SELECT DISTINCT city FROM customers`

requests duplicate elimination.

This distinction is essential when the repeated rows represent legitimate events, transactions, or relationships.

## DISTINCT and expressions

`DISTINCT` can operate on expressions rather than only stored columns.

For example:

`SELECT DISTINCT LOWER(name) FROM customers;`

The expression `LOWER(name)` is evaluated and duplicate elimination is applied to the resulting values.

Consequently, source values such as `Alice`, `alice`, and `ALICE` can produce the same normalized result.

This pattern is useful when the business definition of uniqueness depends on normalization, such as case normalization.

## DISTINCT over multiple columns

The following query:

`SELECT DISTINCT city, country FROM customers;`

returns unique combinations of `city` and `country`.

It does not mean:

- independently deduplicate `city`
- independently deduplicate `country`

Instead, PostgreSQL considers the entire selected combination.

This distinction becomes particularly important when a query adds another column.

For example, changing:

`SELECT DISTINCT customer_id, city`

to:

`SELECT DISTINCT customer_id, city, status`

can increase the number of result rows because different `status` values can make otherwise identical rows distinct.

## NULL and DISTINCT

SQL's treatment of `NULL` requires particular care.

In ordinary SQL comparison logic, `NULL = NULL` does not evaluate to true. `NULL` represents an unknown or missing value and participates in SQL's three-valued logic.

Duplicate elimination is a separate concept.

When multiple result rows contain `NULL` in the same selected position, `DISTINCT` treats those occurrences as belonging to the same duplicate-elimination group, so repeated `NULL` values do not produce repeated DISTINCT rows.

This should not be interpreted as saying that PostgreSQL changes the meaning of the equality operator.

The distinction is:

- normal comparison uses SQL's NULL semantics
- duplicate elimination determines equivalent result rows for the DISTINCT operation

NULL handling should therefore be explicitly tested when building production queries.

## DISTINCT and ORDER BY

`DISTINCT` determines which result rows are unique.

`ORDER BY` determines the order in which the final result is presented.

For example:

`SELECT DISTINCT city FROM customers ORDER BY city;`

first produces the distinct city values and then orders the result.

A query without `ORDER BY` should not be assumed to return rows in a particular order.

The apparent order produced during development can change because of:

- query-plan changes
- indexes
- table growth
- PostgreSQL version changes
- statistics changes
- parallel execution
- different access paths

If the application requires a particular order, specify it explicitly.

## DISTINCT versus GROUP BY

`DISTINCT` and `GROUP BY` can sometimes produce similar-looking results, but they express different intentions.

A query such as:

`SELECT DISTINCT city FROM orders;`

asks for unique cities.

A query such as:

`SELECT city, COUNT(*) FROM orders GROUP BY city;`

creates a group for every city and calculates a count for each group.

`GROUP BY` is particularly appropriate when aggregate calculations are required, such as:

- `COUNT`
- `SUM`
- `AVG`
- `MIN`
- `MAX`

A useful conceptual distinction is:

`DISTINCT` is primarily about duplicate elimination.

`GROUP BY` is primarily about forming groups for grouped computation.

## DISTINCT versus aggregation

A frequent mistake is assuming that `MAX()` automatically returns the complete row containing the maximum value.

Consider:

`SELECT product_id, MAX(observed_at) FROM product_prices GROUP BY product_id;`

This identifies the maximum observation timestamp for every product.

It does not, by itself, mean that PostgreSQL will return the `price`, `product_name`, and other columns from the same source row.

If the requirement is to retrieve the complete latest row, PostgreSQL's `DISTINCT ON` can be appropriate:

`SELECT DISTINCT ON (product_id) product_id, product_name, price, observed_at FROM product_prices ORDER BY product_id, observed_at DESC;`

A window-function solution using `ROW_NUMBER()` is another important alternative.

## DISTINCT ON

`DISTINCT ON` is a PostgreSQL-specific extension.

The general structure is:

`SELECT DISTINCT ON (group_column) ... FROM table_name ORDER BY group_column, preference_column DESC;`

Its purpose is to retain the first row from every `DISTINCT ON` group.

The critical concept is the relationship between `DISTINCT ON` and `ORDER BY`.

Consider:

`SELECT DISTINCT ON (customer_id) customer_id, order_id, order_date, total_amount FROM orders ORDER BY customer_id, order_date DESC, order_id DESC;`

The query means:

1. Divide rows according to `customer_id`.
2. Within each customer, place the newest order first.
3. If dates tie, place the largest `order_id` first.
4. Keep the first row for every customer.

The result contains a complete order row for each customer.

## Why ORDER BY matters with DISTINCT ON

`DISTINCT ON` keeps the first row in each group according to the query's ordering.

Therefore the ordering defines which row wins.

Suppose customer 1 has:

| order_id | order_date | amount |
|---:|---|---:|
| 1001 | 2026-09-10 | 1500 |
| 1002 | 2026-09-14 | 2400 |

With:

`ORDER BY customer_id, order_date DESC`

the row dated `2026-09-14` appears first and becomes the selected row.

If the requirement changes to the oldest order, the ordering can be changed to ascending date order.

The query should therefore express the business rule directly in its ordering.

## The DISTINCT ON ORDER BY prefix rule

One of the most important PostgreSQL-specific rules is that the expressions in `DISTINCT ON` must match the leftmost expressions in `ORDER BY`.

Valid:

`SELECT DISTINCT ON (customer_id) ... ORDER BY customer_id, order_date DESC;`

The first ordering expression is `customer_id`, matching the `DISTINCT ON` expression.

Another valid form is:

`SELECT DISTINCT ON (customer_id, product_id) ... ORDER BY customer_id, product_id, observed_at DESC;`

The first two ordering expressions correspond to the two DISTINCT ON expressions.

An invalid structural pattern is:

`SELECT DISTINCT ON (customer_id) ... ORDER BY order_date DESC, customer_id;`

Here `order_date` appears before `customer_id`, so the ordering does not satisfy the required leftmost-prefix relationship.

The Python, JavaScript, and C++ implementations include validation or demonstrations of this rule.

## Latest row per group

One of the most common applications of `DISTINCT ON` is finding the latest record for every entity.

For an order table:

`SELECT DISTINCT ON (customer_id) customer_id, order_id, order_date, total_amount FROM orders ORDER BY customer_id, order_date DESC, order_id DESC;`

This can be read as:

> For each customer, return the newest order, and use the order ID as a deterministic tie-breaker.

The pattern applies to many domains:

- latest customer order
- latest account status
- latest sensor reading
- latest product price
- latest login
- latest configuration
- latest transaction
- latest application event
- latest inventory observation

The selected row can contain columns that would be difficult to retrieve correctly using only a simple aggregate.

## Deterministic tie-breaking

Suppose two records have exactly the same timestamp.

For example:

| customer_id | order_id | order_date |
|---:|---:|---|
| 1 | 1001 | 2026-09-15 |
| 1 | 1002 | 2026-09-15 |

An ordering based only on:

`ORDER BY customer_id, order_date DESC`

does not completely specify which tied row should be preferred.

A deterministic query can add:

`ORDER BY customer_id, order_date DESC, order_id DESC`

The second order ID becomes the tie-breaker.

This is valuable for:

- audit reports
- APIs
- data synchronization
- reproducible testing
- ETL pipelines
- financial reporting
- operational dashboards

A good tie-breaker is normally unique or sufficiently specific to define one preferred row.

## DISTINCT ON with composite groups

`DISTINCT ON` can use multiple expressions.

For example:

`SELECT DISTINCT ON (customer_id, product_id) customer_id, product_id, price, observed_at FROM product_prices ORDER BY customer_id, product_id, observed_at DESC;`

This means that each `(customer_id, product_id)` combination receives one selected row.

The ordering first identifies the grouping dimensions and then applies the preference rule.

This is useful when the business entity is naturally identified by a composite key.

## DISTINCT ON versus ROW_NUMBER()

A major alternative is the window function `ROW_NUMBER()`.

A conceptual PostgreSQL query is:

`SELECT * FROM (SELECT o.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) AS rn FROM orders AS o) ranked WHERE rn = 1;`

The result can be equivalent to a simple `DISTINCT ON` query.

The difference is flexibility.

`DISTINCT ON` is concise when the requirement is:

> Keep one preferred row for every group.

`ROW_NUMBER()` is useful when the requirement is:

- rank every row
- retrieve the top three rows
- retrieve the second-ranked row
- expose the rank in the result
- perform more complex analytical processing

For example, selecting the top three orders per customer naturally fits a window-function approach:

`ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC)`

followed by filtering for a rank range.

## DISTINCT versus ROW_NUMBER() conceptually

The distinction can be viewed as:

| Requirement | Suitable construct |
|---|---|
| Unique projected values | `SELECT DISTINCT` |
| One preferred row per group | `SELECT DISTINCT ON` |
| Ranked rows per group | `ROW_NUMBER()` |
| Aggregated group metrics | `GROUP BY` |
| Maximum value only | `MAX()` |
| Maximum plus complete associated row | `DISTINCT ON` or `ROW_NUMBER()` |
| Preserve every source row | ordinary `SELECT` |

The correct construct depends on the information the result must preserve.

## DISTINCT and JOINs

`DISTINCT` is frequently added to queries after a JOIN produces more rows than expected.

This can be either correct or a serious mistake.

Suppose one customer has three orders. A customer-to-order JOIN naturally produces three rows for that customer.

If the application wants every order, those three rows are legitimate.

If the application only wants a list of unique customers, projecting customer data and applying `DISTINCT` may be correct.

The important question is:

> Are these rows duplicates that should be eliminated, or are they meaningful instances of a one-to-many relationship?

Using `DISTINCT` to hide an incorrect JOIN condition can conceal data-model or query problems.

Before adding `DISTINCT`, inspect:

- join keys
- relationship cardinality
- duplicate source records
- many-to-many relationships
- missing predicates
- accidental Cartesian products

## Python implementation

The Python program uses standard-library data structures to model the logical operations.

The `distinct_rows()` function maintains a set of previously encountered result rows. This demonstrates the fundamental operation of duplicate elimination.

The examples cover:

- duplicate scalar values
- multiple-column combinations
- NULL-like values represented by `None`
- expression normalization
- ordering
- DISTINCT versus GROUP BY
- DISTINCT ON semantics
- latest-row-per-group selection
- tie-breaking
- window-function comparison
- JOIN multiplicity
- composite DISTINCT ON keys
- performance concepts
- security concepts
- validation
- automated assertions
- production considerations

The Python `distinct_on()` function intentionally assumes that the input rows have already been ordered according to the desired preference.

That design mirrors the logical role of PostgreSQL's `ORDER BY` in a DISTINCT ON query.

For example, the program models:

`SELECT DISTINCT ON (customer_id) ... ORDER BY customer_id, event_time DESC;`

by first sorting the rows and then keeping the first row encountered for each customer.

The program also contains a complete order-history case study where the latest order per customer is selected.

## JavaScript implementation

The JavaScript program provides a second executable perspective.

The `distinctRows()` function uses JavaScript `Set` semantics to model duplicate elimination. The program explicitly distinguishes this educational model from PostgreSQL's actual type-aware database executor.

The JavaScript implementation demonstrates:

- ordinary DISTINCT
- composite DISTINCT
- NULL handling
- expression-based normalization
- GROUP BY comparison
- DISTINCT ON behavior
- latest row per group
- composite DISTINCT ON
- deterministic tie-breaking
- ROW_NUMBER-style ranking
- query construction
- validation of the DISTINCT ON ordering rule
- JOIN multiplicity
- edge cases
- performance concepts
- security considerations
- production checks

A particularly useful part of the JavaScript implementation is its query-structure builder.

The builder validates that:

- a table is supplied
- DISTINCT ON contains at least one expression
- selected columns exist
- order directions are restricted to `ASC` or `DESC`
- DISTINCT ON columns form the leftmost ORDER BY prefix

This demonstrates an important application-level principle: dynamic SQL should not be constructed by blindly concatenating arbitrary user input.

## C++ case study

The C++ implementation models an e-commerce order-history reporting system.

The primary problem is:

> For every customer, return the most recent order.

The domain model contains an `Order` structure with:

- `customerId`
- `orderId`
- `orderDate`
- `totalAmount`

The case study implements the conceptual equivalent of:

`SELECT DISTINCT ON (customer_id) customer_id, order_id, order_date, total_amount FROM orders ORDER BY customer_id, order_date DESC, order_id DESC;`

### C++ architecture

The program is organized around separate responsibilities.

The domain structures represent business records.

The sorting logic defines the preferred row within each customer group.

The `distinctOnOrdered()` template performs generic first-row-per-key selection after ordering.

The validation functions reject invalid orders.

The test section verifies expected behavior.

The SQL reference section connects the C++ implementation to actual PostgreSQL syntax.

The production checklist captures the database-level considerations that cannot be represented by the in-memory C++ model.

### C++ DISTINCT implementation

For ordinary distinct values, the program uses `std::set`.

This models the idea that only one instance of each unique value should remain.

The implementation uses sorted set output for deterministic display, but this should not be interpreted as a PostgreSQL guarantee.

PostgreSQL only guarantees result ordering when `ORDER BY` specifies it.

### C++ DISTINCT ON implementation

The C++ `distinctOnCustomer()` function first sorts the orders using:

1. customer ID ascending
2. order date descending
3. order ID descending

It then scans the sorted rows and keeps the first row for each customer.

The algorithm is conceptually:

`sort by group and preference -> keep first row per group`

This is the central idea behind the PostgreSQL DISTINCT ON case study.

### Why sorting is important

Consider:

| customer_id | order_id | date |
|---:|---:|---|
| 1 | 1001 | 2026-09-10 |
| 1 | 1002 | 2026-09-14 |

If the rows are ordered by customer and descending date, order `1002` appears first.

When the algorithm sees customer `1` for the first time, it keeps order `1002`.

The later order `1001` is ignored because the customer has already been encountered.

This is why the ordering rule is not an incidental detail. It defines the result.

## Algorithmic complexity

The exact complexity of a database query depends on PostgreSQL's selected execution plan.

The educational Python and C++ implementations demonstrate common algorithmic strategies.

A set-based implementation can require approximately:

- `O(n)` expected behavior with a hash set
- `O(u)` additional memory

where:

- `n` is the number of input rows
- `u` is the number of unique values

The C++ implementation using `std::set` has logarithmic insertion complexity:

- approximately `O(log u)` per insertion
- approximately `O(n log u)` for duplicate elimination
- `O(u)` storage

For a DISTINCT ON-style algorithm, if the rows must first be sorted:

- sorting requires approximately `O(n log n)`
- selecting the first row per group is approximately linear in the number of rows, with additional key-management cost depending on the data structure

These figures describe the educational implementations. They are not guarantees about PostgreSQL's internal executor.

## PostgreSQL performance considerations

Duplicate elimination can require significant processing for large result sets.

PostgreSQL can use different strategies depending on the query and execution environment.

Potential factors include:

- input row count
- number of unique values
- row width
- sort requirements
- available indexes
- table statistics
- memory configuration
- filtering predicates
- JOIN cardinality
- PostgreSQL version
- parallel execution
- data distribution

A query should be inspected with:

`EXPLAIN`

and, when appropriate:

`EXPLAIN (ANALYZE, BUFFERS)`

For example:

`EXPLAIN (ANALYZE, BUFFERS) SELECT DISTINCT city FROM customers;`

The purpose of `EXPLAIN ANALYZE` is to observe the actual execution rather than relying only on assumptions about how PostgreSQL will process the query.

## Index considerations for DISTINCT ON

Consider:

`SELECT DISTINCT ON (customer_id) customer_id, order_id, order_date, total_amount FROM orders ORDER BY customer_id, order_date DESC, order_id DESC;`

An index such as:

`CREATE INDEX ON orders (customer_id, order_date DESC, order_id DESC);`

may be relevant to this access pattern.

The usefulness of an index depends on the complete workload.

Factors include:

- WHERE conditions
- table size
- selectivity
- ordering
- selected columns
- index size
- statistics
- PostgreSQL version
- competing queries
- maintenance cost

An index should not be added solely because a query contains `DISTINCT ON`.

Performance decisions should be validated using real execution plans and representative data.

## Memory and sorting trade-offs

Duplicate elimination can require memory.

If a query must sort a large intermediate result, memory requirements can become significant.

If a query uses a hash-based strategy, the number and size of unique values can influence memory consumption.

The exact strategy is PostgreSQL's decision based on the query plan and environment.

The important application-level lesson is that `DISTINCT` is not free.

Reducing unnecessary input rows before expensive operations can sometimes improve query efficiency, provided that the rewritten query remains semantically correct.

## Pagination considerations

Pagination can become subtle when combined with duplicate elimination.

A query that uses `LIMIT` and `OFFSET` without a deterministic ordering should not be expected to produce stable pages.

For DISTINCT results, use an explicit ordering when stable presentation is required.

For one-row-per-group results using DISTINCT ON, the ordering should fully express the preferred row and the final presentation requirements.

For large production datasets, keyset or cursor-based pagination can sometimes be preferable to large OFFSET values, but the pagination design must be evaluated against the specific query and ordering requirements.

## Security considerations

`DISTINCT` itself is not a security vulnerability.

The common security problem is unsafe dynamic SQL construction.

An unsafe application might concatenate a user-provided value directly into SQL text.

Data values should normally be passed through PostgreSQL parameter binding.

For example, an application should conceptually use:

`SELECT DISTINCT city FROM customers WHERE country = $1`

and supply the country as a separate parameter.

SQL identifiers such as column names are different because ordinary value parameters are not intended to represent arbitrary identifiers.

Applications that permit dynamic columns should normally use strict allow-lists or safe identifier composition facilities provided by the database client library.

The JavaScript example demonstrates structural validation rather than pretending that arbitrary strings are safe SQL identifiers.

## Common mistakes

### Assuming DISTINCT selects the latest row

`SELECT DISTINCT customer_id, order_date FROM orders`

does not select the latest order for each customer.

It returns unique combinations of the selected values.

Use DISTINCT ON or a window function when one preferred complete row is required.

### Using DISTINCT ON without a meaningful ordering

A one-row-per-group query needs a clear rule for which row should be preferred.

For a latest-record requirement, use descending timestamp ordering.

### Forgetting the leftmost ORDER BY requirement

For:

`DISTINCT ON (customer_id)`

the ORDER BY must begin with `customer_id`.

The remaining ordering expressions define which row is preferred.

### Ignoring ties

If two records have the same ordering value, add a deterministic tie-breaker when the business logic requires one.

### Using DISTINCT to conceal a JOIN problem

If a JOIN unexpectedly produces ten rows instead of two, do not immediately add DISTINCT.

Determine why ten rows exist.

The repeated rows might represent valid one-to-many relationships.

### Assuming DISTINCT guarantees order

It does not.

Use `ORDER BY` when result order matters.

### Assuming MAX() returns the associated row

`MAX()` returns a maximum value. It does not automatically return all columns from the row containing that value.

Use DISTINCT ON or a window-function pattern when the complete associated row is required.

## Edge cases

A robust test suite should include:

- an empty input relation
- a result containing no duplicates
- a result where every row is identical
- multiple NULL values
- NULL combined with non-NULL values
- composite keys
- duplicate timestamps
- duplicate timestamps with different IDs
- missing timestamps
- large groups
- multiple groups
- duplicate-producing JOINs
- additional selected columns
- expressions such as `LOWER()`

The Python implementation includes assertions for several of these cases.

The C++ implementation also contains automated tests for:

- ordinary duplicate elimination
- latest-row selection
- tie-breaking
- empty input
- DISTINCT ON ordering validation

## Implementation considerations

A useful way to reason about DISTINCT ON is to separate the operation into two conceptual phases.

First, define the group:

`DISTINCT ON (customer_id)`

Second, define the preferred row:

`ORDER BY customer_id, order_date DESC, order_id DESC`

This makes the intent explicit.

For a composite group:

`DISTINCT ON (customer_id, product_id)`

the ordering must begin with:

`ORDER BY customer_id, product_id, ...`

The expressions after the DISTINCT ON prefix determine which member of each group appears first.

## Practical applications

### Latest customer order

`SELECT DISTINCT ON (customer_id) ... ORDER BY customer_id, order_date DESC, order_id DESC;`

Useful for customer dashboards and operational reports.

### Latest product price

`SELECT DISTINCT ON (product_id) ... ORDER BY product_id, observed_at DESC;`

Useful when a table stores price observations over time.

### Latest login event

`SELECT DISTINCT ON (customer_id) ... ORDER BY customer_id, event_time DESC, event_id DESC;`

Useful for account activity reporting.

### Latest configuration

A configuration-history table can use DISTINCT ON to select the current or latest configuration record for each entity.

### Latest status

A status-history table can use the same pattern to retrieve one current-looking row per business entity when "latest" is defined by an ordering column.

## Important distinctions

| Concept | Purpose |
|---|---|
| `SELECT` | Return qualifying rows |
| `SELECT DISTINCT` | Remove duplicate selected rows |
| `DISTINCT ON` | PostgreSQL-specific one-row-per-group selection |
| `ORDER BY` | Define result ordering and, with DISTINCT ON, row preference |
| `GROUP BY` | Form groups for grouped processing and aggregation |
| `ROW_NUMBER()` | Assign a rank to rows within partitions |
| `MAX()` | Return a maximum value |
| `MIN()` | Return a minimum value |
| `COUNT()` | Count rows or values |

The most important conceptual distinction is between duplicate elimination and row selection.

`DISTINCT` removes duplicate result rows.

`DISTINCT ON` selects one ordered row from each group.

Those are not interchangeable requirements.

## PostgreSQL query examples

### Unique cities

`SELECT DISTINCT city FROM customers;`

### Unique city and country combinations

`SELECT DISTINCT city, country FROM customers;`

### Alphabetically ordered unique cities

`SELECT DISTINCT city FROM customers ORDER BY city;`

### Latest order per customer

`SELECT DISTINCT ON (customer_id) customer_id, order_id, order_date, total_amount FROM orders ORDER BY customer_id, order_date DESC, order_id DESC;`

### Latest price per product

`SELECT DISTINCT ON (product_id) product_id, product_name, price, observed_at FROM product_prices ORDER BY product_id, observed_at DESC;`

### Latest row per composite key

`SELECT DISTINCT ON (customer_id, product_id) customer_id, product_id, price, observed_at FROM product_prices ORDER BY customer_id, product_id, observed_at DESC;`

### Window-function alternative

`SELECT * FROM (SELECT o.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) AS rn FROM orders AS o) ranked WHERE rn = 1;`

## Real-world relevance

The distinction between duplicate elimination and preferred-row selection appears frequently in production database systems.

Examples include:

- customer relationship management
- e-commerce
- banking transaction histories
- payment processing
- inventory systems
- audit logs
- application event stores
- user authentication systems
- sensor data
- pricing histories
- reporting platforms
- operational dashboards
- data warehousing
- ETL pipelines

A query that merely returns unique identifiers may require `DISTINCT`.

A query that needs the most recent complete record usually requires a different technique.

Choosing the construct according to the business requirement is more important than simply reducing the number of rows in the result.

## Best practices

Use `SELECT DISTINCT` when the complete selected result must contain unique rows.

Use `DISTINCT ON` when PostgreSQL-specific one-row-per-group selection expresses the requirement clearly.

Use `ORDER BY` to define the preferred row with `DISTINCT ON`.

Make the DISTINCT ON expressions the leftmost ORDER BY expressions.

Add deterministic tie-breakers when two or more rows can otherwise be equally preferred.

Use `GROUP BY` when aggregation is part of the requirement.

Use `ROW_NUMBER()` when the problem requires ranking or multiple selected rows per group.

Inspect JOIN cardinality before using DISTINCT to eliminate repeated rows.

Use `EXPLAIN` and `EXPLAIN (ANALYZE, BUFFERS)` when investigating performance.

Use parameterized queries for user-controlled data values.

Test NULLs, empty inputs, ties, and composite keys.

Do not depend on implicit result ordering.

## Implementation comparison

| Aspect | Python | JavaScript | C++ |
|---|---|---|---|
| Main purpose | Educational logical model | Executable application-oriented model | Industry-style case study |
| DISTINCT | Set-based implementation | `Set`-based implementation | `std::set` implementation |
| DISTINCT ON | Ordered rows plus first-key selection | Ordered rows plus first-key selection | Generic template plus domain-specific implementation |
| NULL discussion | `None` model | `null` model | `std::optional` |
| Composite keys | Tuples | Arrays serialized as keys | Structs and ordered containers |
| Validation | Assertions and validation examples | Query-structure validation | Exception-based validation |
| Ranking | Python grouping function | JavaScript ranking function | C++ ranking implementation |
| Performance | Complexity discussion | Runtime-oriented discussion | Explicit data-structure complexity |
| Case study | Order and price examples | Query-building and order examples | Full order-history system |

## Limitations of the implementations

The three programs are educational models and do not implement a PostgreSQL database engine.

They do not reproduce PostgreSQL's:

- parser
- optimizer
- planner
- executor
- index access methods
- memory management
- statistics system
- MVCC implementation
- parallel execution
- type system
- collation implementation
- actual NULL semantics in every detail

The programs demonstrate the logical behavior needed to understand the SQL constructs.

The SQL statements shown in the examples are actual PostgreSQL-oriented syntax, while the in-memory implementations illustrate their conceptual behavior.

The performance examples should therefore not be interpreted as measurements of PostgreSQL.

## Production query review checklist

Before deploying a query involving `DISTINCT` or `DISTINCT ON`, verify:

- Is duplicate elimination actually required?
- Are repeated rows legitimate?
- Is a JOIN producing unexpected multiplicity?
- Does DISTINCT apply to exactly the intended selected columns?
- If DISTINCT ON is used, are its expressions the leftmost ORDER BY expressions?
- Does ORDER BY express the desired preferred row?
- Are ties deterministic?
- Are NULL ordering rules relevant?
- Would `ROW_NUMBER()` be more expressive?
- Would `GROUP BY` better represent an aggregation requirement?
- Is the query plan acceptable?
- Are relevant indexes justified by actual workload measurements?
- Are user-controlled values parameterized?
- Are empty, duplicate, NULL, and tied cases tested?
- Does the result preserve all information required by the business process?

The central design principle is to distinguish between eliminating duplicate result rows and selecting a preferred row from a group. `SELECT DISTINCT` addresses the first problem, while PostgreSQL's `DISTINCT ON`, when combined with a deliberate `ORDER BY`, addresses the second.
