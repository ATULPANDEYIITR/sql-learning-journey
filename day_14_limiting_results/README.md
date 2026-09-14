# Limiting results: LIMIT, OFFSET, FETCH, and pagination fundamentals

## Introduction

Database queries often return more rows than an application should display or transfer at one time. Limiting results solves this problem by restricting the number of rows returned by a query.

The main concepts covered by the accompanying Python script are:

- `LIMIT`
- `OFFSET`
- `FETCH FIRST`
- `FETCH NEXT`
- page-number pagination
- offset-based pagination
- keyset pagination
- cursor-based pagination
- deterministic ordering
- top-N queries
- pagination metadata
- total-count pagination
- filtering and pagination
- aggregation and pagination
- joins and pagination
- edge cases
- indexing
- performance
- consistency
- security
- production design

The Python implementation uses SQLite through Python's built-in `sqlite3` module. This makes the examples executable without installing an external database driver.

## Why limiting results matters

A database table can contain thousands, millions, or billions of records. Returning every matching record to an application can cause unnecessary database work, network traffic, memory consumption, and application latency.

For example, an employee table might contain 5 million rows, while an administrative screen only displays 25 employees at a time.

A query that retrieves all 5 million records is inappropriate for such a screen. A limited query can retrieve only the required subset.

Limiting results is useful for:

- web tables
- mobile applications
- dashboards
- search results
- product catalogs
- administrative systems
- reporting interfaces
- APIs
- feeds
- autocomplete systems
- leaderboards
- top-N reports

The important distinction is that limiting the number of rows returned does not automatically mean the database performs only that amount of work. The execution strategy depends on filtering, ordering, indexes, database engine behavior, and query structure.

## Fundamental terminology

### Result set

A result set is the collection of rows produced by a SQL query.

For example, a query against an employee table might produce 20 employee rows.

### LIMIT

`LIMIT` restricts the maximum number of rows returned.

The conceptual form is:

`SELECT ... FROM ... ORDER BY ... LIMIT number`

A limit of 5 means the query returns no more than five rows.

### OFFSET

`OFFSET` specifies how many rows should be skipped before returning rows.

The conceptual form is:

`SELECT ... FROM ... ORDER BY ... LIMIT page_size OFFSET number_to_skip`

If the ordered result contains 100 rows and the query uses `OFFSET 20`, the first 20 rows are skipped.

### FETCH FIRST

`FETCH FIRST` expresses the concept of returning a limited number of rows using SQL-standard-style syntax supported by several database systems.

The conceptual form is:

`FETCH FIRST 10 ROWS ONLY`

### FETCH NEXT

`FETCH NEXT` expresses the concept of retrieving a specific number of rows after an offset.

The conceptual form is:

`OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY`

Database dialects differ. SQLite uses `LIMIT` and `OFFSET`, while other database systems may support variations of `FETCH FIRST` and `FETCH NEXT`.

## LIMIT

The simplest form of result limiting is `LIMIT`.

A query ordered by employee ID with a limit of 5 returns at most five employees.

The script demonstrates several forms of limiting:

- returning five rows
- returning one row
- returning the highest-paid five employees
- returning the lowest-priced products
- returning the most recently hired employees

`LIMIT 1` is especially useful when the application needs only one row from an ordered result.

For example, selecting the employee with the highest salary can be expressed conceptually as:

`ORDER BY salary DESC LIMIT 1`

The ordering determines which row becomes the first row, and `LIMIT 1` retains that row.

## ORDER BY and deterministic results

`LIMIT` and `ORDER BY` solve different problems.

`ORDER BY` determines the order of the result.

`LIMIT` determines how many rows are returned.

For pagination, meaningful ordering is essential.

A query that simply asks for a limited number of rows without an explicit ordering should not be interpreted as requesting a stable logical subset such as "the first five employees."

Database systems may return rows according to their execution plan, storage layout, indexes, or other implementation details.

For reliable pagination, define an explicit ordering.

A stronger ordering often includes a unique tie-breaker.

For example:

`ORDER BY salary DESC, employee_id ASC`

Salary may not be unique, but employee ID is unique. This produces a deterministic ordering among employees with equal salaries.

A common production pattern is:

`ORDER BY created_at DESC, id DESC`

The timestamp determines the primary order, while the unique ID resolves ties.

## OFFSET

`OFFSET` skips rows from an ordered result.

Consider a page size of 5.

Page 1 uses:

`LIMIT 5 OFFSET 0`

Page 2 uses:

`LIMIT 5 OFFSET 5`

Page 3 uses:

`LIMIT 5 OFFSET 10`

Page 4 uses:

`LIMIT 5 OFFSET 15`

The offset therefore represents a number of rows rather than a page number.

## Page-number pagination

Applications often expose a page number to users.

For example:

- page = 1
- page = 2
- page = 3

The database normally needs an offset instead.

The conversion is:

`OFFSET = (page - 1) × page_size`

For a page size of 10:

- page 1 has offset 0
- page 2 has offset 10
- page 3 has offset 20
- page 10 has offset 90

This formula is fundamental to offset-based pagination.

## Page size

Page size is the number of rows returned per page.

A reasonable application might allow values such as:

- 10
- 20
- 50
- 100

Applications should normally enforce a maximum page size.

Without a maximum, a client could request an extremely large result set, causing unnecessary database, network, and application resource consumption.

The Python script uses validation to reject page sizes larger than a configured maximum.

## Empty pages

An offset can be larger than the number of available rows.

For example, a table containing 20 rows can be queried with a large offset.

The result is simply an empty result set.

Applications should treat an empty page as a normal condition rather than assuming it represents a database failure.

An empty result can occur when:

- the requested page is beyond the final page
- filters eliminate all matching records
- records were deleted
- the requested page size is valid but no records remain

## LIMIT 0

A limit of zero requests no rows.

This can be useful when an application intentionally needs to inspect query behavior or metadata without returning records, although exact behavior and practical usefulness depend on the database system and application.

## Filtering before limiting

Filtering and limiting should not be conceptually confused.

Suppose a query requests the first three Engineering employees.

The database first establishes the relevant filtered result and then applies the requested ordering and limit according to the query semantics.

Conceptually:

`WHERE department = 'Engineering'`

followed by ordering and limiting.

Therefore, `LIMIT 3` in this query means three rows from the Engineering result set, not three rows from the entire employee table.

This distinction becomes important when combining:

- `WHERE`
- `ORDER BY`
- `LIMIT`
- `OFFSET`

## DISTINCT and LIMIT

`DISTINCT` removes duplicate result values.

When `DISTINCT` and `LIMIT` are combined, the limited result is based on the distinct result set.

For example, selecting distinct departments and limiting the result to two departments produces two distinct department values rather than two arbitrary employee rows.

## GROUP BY and LIMIT

`LIMIT` can also be applied to aggregated results.

Consider a query that groups employees by department and calculates average salary.

The result might contain one row per department.

Applying `LIMIT 3` then restricts the number of department groups returned.

This is different from limiting the number of employee rows before aggregation.

The order and structure of SQL operations therefore matter when working with aggregation.

## JOIN and LIMIT

A query involving a `JOIN` can also use `LIMIT`.

The join produces a combined result according to its join condition, and the final query can order and limit that result.

This is particularly useful for displaying a fixed number of records from a relational query involving multiple tables.

The important consideration is what constitutes one result row. A join can multiply rows when relationships are one-to-many or many-to-many, so applying a limit to a joined result may produce fewer primary entities than expected.

## Top-N queries

A top-N query retrieves the best or worst N records according to some ordering.

Examples include:

- five highest salaries
- ten most expensive products
- three newest employees
- ten highest-scoring students
- twenty most recent transactions

The general pattern is:

`ORDER BY <metric> DESC LIMIT <N>`

For lowest values, ascending order is generally used.

The tie-breaking issue remains important. If several rows have identical values, adding a unique secondary ordering column makes the result deterministic.

## FETCH FIRST and FETCH NEXT

`FETCH FIRST` and `FETCH NEXT` provide SQL-standard-style ways of expressing limited result retrieval.

Conceptually:

`FETCH FIRST 10 ROWS ONLY`

means return at most ten rows.

A paginated form can be expressed as:

`OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY`

The exact syntax and feature support varies between database engines.

SQLite uses `LIMIT` and `OFFSET`, so the executable examples use those constructs.

When developing database-independent applications, SQL dialect differences should be considered explicitly.

## Offset-based pagination

Offset-based pagination is the traditional page-number model.

The client requests a page and page size.

For example:

`page = 4`

`page_size = 25`

The application calculates:

`offset = (4 - 1) × 25 = 75`

The SQL query then requests 25 rows after skipping 75 rows.

### Advantages

Offset pagination is:

- easy to understand
- easy to implement
- natural for page-number interfaces
- convenient when users need page 1, page 2, page 3, and so on
- compatible with total-page calculations

### Limitations

Offset pagination can become less attractive when:

- the dataset is extremely large
- clients request very deep pages
- rows are frequently inserted or deleted
- the application mainly needs Next and Previous navigation
- query latency becomes sensitive to large offsets

## Determining whether another page exists

An API does not always need the exact total number of records.

Sometimes it only needs to know whether another page exists.

A common technique is to request one more row than the requested page size.

For a page size of 10, retrieve 11 rows.

If 11 rows are found:

- return the first 10
- set `has_next` to true

If 10 or fewer are found:

- return all available rows
- set `has_next` to false

This can avoid an additional `COUNT(*)` query when the application does not need a total record count.

## Total-count pagination

Some interfaces need information such as:

- total records
- total pages
- current page
- page size
- whether a previous page exists
- whether a next page exists

For example:

`total_pages = ceil(total_records / page_size)`

In integer arithmetic, this can be calculated as:

`(total_records + page_size - 1) // page_size`

The Python script demonstrates this calculation.

The trade-off is that obtaining an exact total may require a separate count operation. The cost depends on the database engine, indexes, filtering, table size, query complexity, and other factors.

## Keyset pagination

Keyset pagination is an alternative to offset pagination.

Instead of saying:

"Skip 10,000 rows and give me the next 20."

the client says:

"Give me the next 20 rows after this last-seen key."

Suppose the ordering is:

`ORDER BY employee_id ASC`

If the last returned employee has ID 5000, the next query can conceptually use:

`WHERE employee_id > 5000`

followed by:

`ORDER BY employee_id ASC`

and a limit.

This approach is called keyset pagination, and it is also commonly associated with cursor pagination.

## Why keyset pagination can be faster

Offset pagination may require the database to locate and skip a large number of preceding rows.

A keyset query instead identifies the position through a comparison against an indexed ordering key.

For example:

`WHERE employee_id > 100000`

can be efficient when `employee_id` is appropriately indexed.

The actual performance depends on the database engine and execution plan, but keyset pagination is often a strong choice for large datasets and sequential navigation.

## Keyset pagination and composite ordering

A keyset cursor must represent the complete ordering when the ordering contains multiple columns.

Suppose the ordering is:

`ORDER BY salary DESC, employee_id ASC`

Salary is not unique, so a cursor containing only salary is insufficient.

The cursor needs both:

- the last salary
- the last employee ID

The next-page condition becomes conceptually:

`salary < last_salary`

or, when salaries are equal:

`salary = last_salary AND employee_id > last_employee_id`

This preserves the same ordering logic across pages.

## Descending keyset pagination

The comparison operator depends on the sort direction.

For:

`ORDER BY salary DESC`

the next rows have smaller salaries.

Therefore:

`salary < last_salary`

For:

`ORDER BY employee_id ASC`

the next rows have larger IDs.

Therefore:

`employee_id > last_employee_id`

When multiple columns are involved, every comparison must respect its corresponding direction.

This is one of the most important details in implementing correct cursor pagination.

## OFFSET versus keyset pagination

| Characteristic | OFFSET pagination | Keyset pagination |
|---|---|---|
| Page numbers | Natural | Not natural |
| Next-page navigation | Good | Excellent |
| Simple implementation | Excellent | Moderate |
| Deep pagination | Can become expensive | Usually better |
| Stable traversal | Can shift when data changes | Usually more stable |
| Arbitrary page jumps | Easy | Difficult |
| Exact total pages | Straightforward with count | Usually separate |
| Cursor management | Not required | Required |
| Complex ordering | Relatively flexible | Requires careful cursor design |

Neither strategy is universally superior.

The correct choice depends on the application.

## Pagination consistency

Pagination requests are commonly separate database queries.

For example:

Request 1:

`LIMIT 10 OFFSET 0`

Request 2:

`LIMIT 10 OFFSET 10`

If records are inserted, deleted, or modified between these requests, the second query may observe a different dataset.

This can cause:

- duplicate records
- skipped records
- records appearing on a different page
- changing total counts

A deterministic `ORDER BY` is necessary but does not solve every concurrency problem.

Keyset pagination often provides better traversal behavior for continuously changing datasets because the next query is anchored to a specific position in the ordered data.

For applications with strict consistency requirements, transaction isolation, snapshots, or other database-specific consistency mechanisms may be appropriate.

## Indexing and pagination

Indexes can have a major effect on pagination performance.

Suppose a common query filters by department and orders by employee ID:

`WHERE department = ? ORDER BY employee_id`

An index such as:

`(department, employee_id)`

may be useful because it corresponds to both filtering and ordering requirements.

The best index depends on actual query patterns.

Indexes have costs as well:

- additional storage
- additional maintenance
- slower writes in some workloads
- more complex database design

Index decisions should therefore be based on real queries and execution plans rather than assumptions.

## Large OFFSET values

Deep offset pagination is an important performance consideration.

A request such as:

`OFFSET 0`

is usually much simpler than a request such as:

`OFFSET 1,000,000`

The database may need to process or traverse many preceding rows to reach the desired position.

The exact behavior depends on:

- database engine
- index structure
- filtering
- ordering
- query optimizer
- table size
- data distribution
- execution plan

A query returning only 20 rows can still require substantial database work if it must determine which 20 rows occur after a very large offset.

## Query plans

Performance should be investigated using the database's query-plan facilities.

SQLite provides `EXPLAIN QUERY PLAN`.

Other database systems provide their own execution-plan mechanisms.

Useful information includes:

- indexes used
- table scans
- index scans
- sorting
- estimated rows
- actual rows where available
- join strategies
- filtering behavior
- memory usage
- disk operations

A production pagination query should be benchmarked using realistic data rather than a tiny development table.

## Pagination and dynamic sorting

Many APIs allow users to choose a sort field.

Examples include:

- name
- salary
- creation date
- price

SQL parameter placeholders are intended for values. They should not be treated as a general-purpose mechanism for arbitrary SQL identifiers.

If an API allows a user to choose a sort column, the server should map a safe external value to a predefined SQL identifier.

For example:

- `salary` maps to the database column `salary`
- `name` maps to the database column `name`
- `hire_year` maps to the database column `hire_year`

Unsupported values should be rejected.

Sort directions should also be restricted to known values such as `ASC` and `DESC`.

The Python script demonstrates this allowlist approach.

## SQL injection considerations

Pagination parameters are often supplied by HTTP requests, query parameters, or other untrusted sources.

Potentially unsafe values include:

- page
- page size
- sort field
- sort direction
- filters

Page and page-size values should be validated.

SQL values should be passed through parameter binding where supported.

Dynamic SQL identifiers should be selected from server-side allowlists.

A particularly important distinction is that user input should not be allowed to become arbitrary SQL syntax.

A secure pagination implementation therefore combines:

- input validation
- maximum page sizes
- parameterized SQL
- allowlisted sort columns
- allowlisted sort directions
- authorization checks
- careful filtering

## Authorization and pagination

Pagination does not replace authorization.

Security filters must be applied before exposing records to a client.

For example, an employee API might only permit a user to see employees belonging to authorized departments.

The application must not retrieve unauthorized records and rely on pagination to hide them.

The query itself should apply the appropriate authorization constraints.

Pagination can also expose indirect information through counts, page availability, or timing, so sensitive systems should consider whether metadata reveals information that the user is not authorized to know.

## Search and pagination

Search results can be paginated in the same way as ordinary queries.

The general structure is:

`WHERE search_condition`

followed by:

`ORDER BY`

then:

`LIMIT`

and:

`OFFSET`

The search filter should be parameterized.

The ordering should remain deterministic.

If search results change rapidly, keyset or cursor-based pagination may be preferable depending on the application's behavior.

## NULL ordering

Ordering columns may contain `NULL`.

The exact default placement of `NULL` values differs across database systems and sort directions.

If NULL placement matters to application behavior, it should be explicitly controlled.

The Python script demonstrates using a `CASE` expression to make NULL placement explicit.

This is especially important when pagination depends on the exact ordering because changing NULL ordering can change which records appear on each page.

## Edge cases

A robust pagination implementation should handle:

### Page number below one

A page number of zero or a negative value is usually invalid for a page-number API.

### Page size below one

A page size of zero or a negative value should normally be rejected by application validation.

### Excessively large page size

Large page sizes can cause unnecessary resource consumption and should normally be capped.

### Page beyond the final page

The query should return an empty result rather than failing unexpectedly.

### Empty dataset

The first page of an empty dataset should contain zero items and appropriate pagination metadata.

### Duplicate ordering values

A unique tie-breaker should be added where necessary.

### Data changes between requests

The application should define its consistency expectations and choose an appropriate pagination strategy.

### Changing sort order

A client should not assume that pages from different sort orders represent one continuous result sequence.

## Common mistakes

### Using LIMIT without ORDER BY

This can produce a non-deterministic subset.

### Treating page number as OFFSET

A page number must be converted using:

`(page - 1) * page_size`

### Allowing unlimited page sizes

This can create excessive database and application workload.

### Using a non-unique ordering column alone

Duplicate values can produce ambiguous pagination boundaries.

### Using only the primary ordering column for a cursor

Composite ordering requires a cursor containing the relevant ordering components.

### Ignoring database dialect differences

`LIMIT`, `OFFSET`, and `FETCH` syntax varies between database systems.

### Building SQL through string concatenation

This can create SQL injection vulnerabilities.

### Assuming LIMIT guarantees low database cost

The database may still need to process many rows to satisfy filtering, ordering, and offset requirements.

### Performing COUNT(*) unnecessarily

An exact total is useful when required, but some APIs only need `has_next`.

### Ignoring execution plans

Pagination performance should be measured rather than inferred solely from the number of rows returned.

## API pagination design

A page-number API commonly exposes metadata such as:

- current page
- page size
- total records
- total pages
- has previous
- has next

A cursor-based API commonly exposes:

- returned data
- page size
- has next
- next cursor

Cursor values should be treated as opaque API data when exposed to clients. The internal representation may contain one or more database ordering values.

## Total pages

If a total record count is available, total pages can be calculated as:

`ceil(total_records / page_size)`

For integer arithmetic:

`(total_records + page_size - 1) // page_size`

For example, 101 records with a page size of 20 require six pages:

- page 1: records 1–20
- page 2: records 21–40
- page 3: records 41–60
- page 4: records 61–80
- page 5: records 81–100
- page 6: record 101

The final page can contain fewer records than the configured page size.

## Performance benchmarking

Pagination performance should be tested at realistic scale.

Useful offset values include:

- 0
- 1,000
- 10,000
- 100,000
- 1,000,000

Equivalent traversal should also be tested using keyset pagination.

Measurements can include:

- query execution time
- database CPU
- rows examined
- rows returned
- logical reads
- physical reads
- memory usage
- sorting operations
- index usage
- application response latency

A benchmark on 20 rows cannot reliably predict performance on 20 million rows.

## Production considerations

A production pagination design should explicitly establish:

- default page size
- maximum page size
- allowed sort fields
- allowed sort directions
- deterministic ordering
- filtering rules
- authorization requirements
- empty-page behavior
- total-count requirements
- cursor format when applicable
- consistency expectations
- index strategy
- query-plan behavior
- monitoring requirements

For simple administrative tables, page-number pagination with `LIMIT` and `OFFSET` is often a practical design.

For very large datasets or continuously changing feeds, keyset or cursor pagination can provide a more scalable traversal model.

## Practical decision framework

### Use LIMIT/OFFSET when

- users need explicit page numbers
- the dataset is moderate
- arbitrary page jumps are important
- implementation simplicity matters
- exact total pages are required

### Consider keyset/cursor pagination when

- the dataset is very large
- users primarily move forward or backward
- deep pagination is common
- records change frequently
- stable sequential traversal is important
- the ordering can be represented by a suitable cursor

### Use both when appropriate

A system can expose page-number pagination for one interface and cursor pagination for another.

For example, an administrative reporting screen may use page numbers, while a high-volume activity feed may use cursors.

## Relationship between LIMIT, OFFSET, and pagination

These concepts are related but not identical.

`LIMIT` answers:

"How many rows should be returned?"

`OFFSET` answers:

"How many ordered rows should be skipped?"

Page-number pagination answers:

"Which numbered page does the client want?"

Keyset pagination answers:

"Which rows come after the last row already received?"

`FETCH FIRST` and `FETCH NEXT` express similar result-limiting concepts using syntax supported by particular SQL dialects.

Understanding these distinctions makes it easier to select the appropriate technique for an application.

## What the Python script demonstrates

The script builds a complete SQLite environment and progressively demonstrates:

- database and table creation
- sample data insertion
- `LIMIT`
- `OFFSET`
- deterministic `ORDER BY`
- page-number calculations
- `FETCH` syntax concepts
- top-N queries
- filtering
- `DISTINCT`
- aggregation
- joins
- empty results
- page validation
- `has_next` detection
- total counts
- filtered pagination
- keyset pagination
- composite cursors
- descending cursor pagination
- offset consistency problems
- API-style pagination responses
- parameterized queries
- SQL injection prevention
- indexing
- query plans
- page-size restrictions
- NULL ordering
- pagination tests
- safe dynamic sorting
- production pagination checklists

The examples are designed to expose both the basic SQL mechanics and the engineering decisions required when pagination becomes part of a real application.
