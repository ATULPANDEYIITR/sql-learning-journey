# Composite Indexes: Multi-column Indexes, Column Ordering, and Selectivity

## 1. Introduction

A composite index is an index containing two or more columns in a defined order. It allows a database management system to locate records using combinations of search conditions, support certain ordering operations, and reduce the number of rows examined.

Composite indexes are particularly useful when applications repeatedly execute queries involving multiple predicates.

Consider an order-management table:

| order_id | customer_id | status | created_at | total_amount |
|---|---:|---|---|---:|
| 101 | 25 | PAID | 2025-02-10 | 1500 |
| 102 | 25 | PENDING | 2025-02-11 | 900 |
| 103 | 42 | PAID | 2025-02-12 | 2400 |
| 104 | 42 | SHIPPED | 2025-02-13 | 1200 |

A frequently executed query might retrieve paid orders belonging to a particular customer:

- Identify a customer.
- Filter by order status.
- Restrict the order creation date.
- Return the newest matching records.

An appropriate composite index is:

`(customer_id, status, created_at DESC)`

The order of these columns determines how the index can support queries.

## 2. Fundamental Concepts

### 2.1 Single-column indexes

A single-column index organizes entries using one column.

For example:

`CREATE INDEX idx_orders_customer ON orders(customer_id);`

This supports searches using `customer_id`.

It does not directly provide the same access path as a composite index containing customer, status, and creation date.

### 2.2 Composite indexes

A composite index organizes entries using multiple columns in a specified sequence.

For example:

`CREATE INDEX idx_customer_status_date ON orders(customer_id, status, created_at);`

The logical key order is:

`customer_id → status → created_at`

The database organizes index entries according to the ordered combination of these values.

For a B-tree, the first key determines the primary ordering. Subsequent keys distinguish entries sharing earlier key values.

### 2.3 B-tree structure

A B-tree index maintains ordered search keys using a balanced tree structure.

Its main components are:

- Root page: The entry point for searching.
- Internal pages: Direct searches toward appropriate leaf pages.
- Leaf pages: Store ordered index entries and references to table rows.

B-tree indexes support equality comparisons, range comparisons, and ordered retrieval for compatible operators and sort directions.

Typical lookup complexity is approximately \(O(\log N)\), although actual query cost also depends on matching rows, table access, cache behavior, and page distribution.

## 3. Column Ordering

Column ordering determines which query patterns can efficiently use a composite index.

Consider:

`(customer_id, status, created_at)`

The following access patterns have different compatibility.

| Query conditions | Leading-prefix compatibility |
|---|---|
| customer_id | Yes |
| customer_id, status | Yes |
| customer_id, status, created_at | Yes |
| customer_id, created_at | Partial |
| status only | No |
| created_at only | No |
| status, created_at | No |

The database can use the leading customer column independently or combine it with subsequent index columns.

A query filtering only on `created_at` cannot normally use the preceding index keys as an efficient direct search path.

Modern PostgreSQL can sometimes use techniques such as B-tree skip scans when appropriate, but this does not eliminate the importance of leading-column design.

### 3.1 Leftmost-prefix principle

The leftmost-prefix principle describes how leading columns determine the primary search capability of a composite B-tree index.

For an index:

`(A, B, C)`

Commonly supported search prefixes include:

- `(A)`
- `(A, B)`
- `(A, B, C)`

A query on `(B, C)` does not provide the same contiguous leading search prefix.

This distinction is fundamental when selecting column order.

### 3.2 Equality and range predicates

Equality predicates identify a specific value.

Example:

`WHERE customer_id = 42`

Range predicates identify an interval.

Example:

`WHERE created_at >= TIMESTAMP '2025-02-01 00:00:00'`

A common index arrangement is:

`(equality columns, range column)`

For example:

`(customer_id, status, created_at)`

It supports equality filtering on the first two columns, followed by a range condition on the third.

Once a range condition is applied to an index key, subsequent keys generally cannot extend the same contiguous range-search boundary. They can still contribute to index filtering, ordering, or covering behavior.

### 3.3 Column ordering is workload-dependent

The rule that the most selective column must always come first is incorrect.

Consider:

| Column | Distinct values | Approximate equality selectivity |
|---|---:|---:|
| customer_id | 10,000 | 0.0001 |
| status | 5 | 0.20 |
| region | 4 | 0.25 |
| payment_method | 6 | 0.1667 |

For equality predicates on both customer and status, the following indexes can support the same fully specified equality combination:

- `(customer_id, status, created_at)`
- `(status, customer_id, created_at)`

Their usefulness differs for queries that filter only on the leading column.

The correct decision depends on:

- Query frequency.
- Predicate combinations.
- Column distributions.
- Range conditions.
- Sorting requirements.
- Write volume.
- Existing indexes.
- Query execution plans.

## 4. Selectivity and Cardinality

### 4.1 Cardinality

Cardinality describes the number of distinct values in a column.

For example, a customer identifier may have 10,000 distinct values, while an order status may have only five.

Higher cardinality often indicates greater potential selectivity for equality predicates.

### 4.2 Selectivity

Selectivity represents the fraction of records satisfying a predicate.

A basic estimate for equality selection under a uniform distribution is:

\[
S(A)=\frac{1}{D(A)}
\]

Where:

- \(S(A)\) is the estimated equality selectivity.
- \(D(A)\) is the number of distinct values.

For a column containing 10,000 distinct values:

\[
S(A)=\frac{1}{10000}=0.0001
\]

The estimated matching fraction is 0.01%.

### 4.3 Combined selectivity

If two predicates are statistically independent:

\[
S(A,B)=S(A)\times S(B)
\]

For example:

\[
S(customer,status)=0.0001\times0.20
\]

\[
S(customer,status)=0.00002
\]

This corresponds to an estimated matching fraction of 0.002%.

The independence assumption is important. Real datasets frequently contain correlated attributes.

For example, certain customer groups may use specific payment methods more frequently. Multiplying individual selectivities can therefore produce inaccurate estimates.

PostgreSQL supports extended statistics for selected multi-column distributions and dependencies.

### 4.4 Range selectivity

Range selectivity estimates the proportion of records falling inside a specified interval.

For example:

\[
S(created\_at \geq T)=0.15
\]

This means approximately 15% of records satisfy the date condition.

The estimate depends on data distribution, histogram statistics, most-common-value information, and the requested range.

## 5. Composite Index Query Design

Consider this query:

`SELECT order_id, created_at FROM orders WHERE customer_id = 42 AND status = 'PAID' AND created_at >= TIMESTAMP '2025-02-01 00:00:00' ORDER BY created_at DESC LIMIT 20;`

A suitable index is:

`(customer_id, status, created_at DESC)`

The index provides:

1. An equality search on customer.
2. An equality search on status.
3. A range restriction on creation date.
4. An ordering compatible with descending creation date.

This can reduce the amount of sorting and row retrieval required.

The actual execution plan remains the optimizer's decision.

A sequential scan can be preferable when a query returns a large proportion of the table or when index access would require extensive random page retrieval.

## 6. Covering Indexes

A covering index contains the information required to satisfy a query without retrieving additional table columns.

Consider:

`CREATE INDEX idx_customer_covering ON orders(customer_id, status, created_at DESC) INCLUDE (total_amount);`

The search-key columns are:

- customer_id
- status
- created_at

The included column is:

- total_amount

An `INCLUDE` column is stored in index leaf tuples but does not participate in B-tree search ordering.

A suitable query might retrieve:

`customer_id, status, created_at, total_amount`

PostgreSQL can potentially execute an index-only scan.

An index-only scan still depends on visibility-map information. If relevant heap pages are not marked all-visible, additional heap access may be necessary.

Covering indexes have trade-offs:

- Larger index storage.
- Increased write overhead.
- Additional maintenance.
- Potentially reduced heap access.
- More efficient read-only access patterns.

## 7. Composite Indexes and Ordering

An index can support an `ORDER BY` operation when its ordering is compatible with the query.

For example:

`CREATE INDEX idx_status_date ON orders(status, created_at DESC);`

This can support:

`WHERE status = 'PAID' ORDER BY created_at DESC`

The equality predicate fixes the leading status key, allowing the subsequent creation-date ordering to be useful.

Sort direction matters.

PostgreSQL can scan B-tree indexes in forward or backward directions. Mixed ascending and descending requirements may require a correspondingly defined index.

NULL ordering and collation can also affect compatibility.

## 8. Distinguishing Composite Indexes from Related Techniques

| Technique | Primary purpose |
|---|---|
| Single-column index | Accelerate access using one key |
| Composite index | Accelerate access using ordered combinations of keys |
| Covering index | Provide additional query columns from index storage |
| Partial index | Index only rows satisfying a predicate |
| Unique composite index | Enforce uniqueness across multiple columns |
| Bitmap index combination | Combine compatible index results where supported |
| Expression index | Index the result of an expression |

A composite index is not equivalent to creating several independent indexes.

For example:

`(customer_id, status)`

is not structurally identical to:

- An index on `customer_id`.
- An index on `status`.

The composite index provides an ordered combination of both keys.

The query optimizer can sometimes combine independent indexes using bitmap operations, but that is a different execution strategy.

## 9. Python Implementation

The Python implementation provides two complementary mechanisms.

### CompositeIndexAdvisor

The advisor models:

- Column statistics.
- Distinct-value counts.
- Equality selectivity.
- Range selectivity.
- Leftmost-prefix matching.
- Ordering compatibility.
- Redundancy detection.
- Candidate index recommendations.

Its selectivity estimator assumes independent predicates. This is a simplified educational model rather than a replacement for database statistics.

### OrderDatabase

The database implementation uses SQLite and its standard-library `sqlite3` module.

It creates an in-memory order-management database containing:

- Customers.
- Orders.
- Status values.
- Regions.
- Amounts.
- Creation timestamps.

The implementation creates several composite indexes and executes representative queries.

`EXPLAIN QUERY PLAN` provides evidence of the access paths selected by SQLite.

The non-leftmost query demonstrates why an index beginning with customer and status does not automatically provide an efficient direct date-only lookup.

The Python example uses SQLite rather than PostgreSQL, so its optimizer behavior and plan output are not identical to those of the PostgreSQL implementation.

## 10. JavaScript Implementation

The JavaScript implementation models a query workload as structured objects.

### Main components

| Component | Responsibility |
|---|---|
| Column | Stores column statistics |
| CompositeIndex | Defines ordered index keys |
| WorkloadQuery | Represents query predicates and access requirements |
| IndexAdvisor | Evaluates index compatibility |
| IndexMaintenanceMonitor | Records index maintenance events |
| Workload evaluation | Processes independent query evaluations asynchronously |

The advisor uses `Map` for column metadata and `Set` for predicate classification and duplicate detection.

The workload evaluator uses asynchronous operations to evaluate independent queries.

The maintenance monitor extends Node.js `EventEmitter`.

It records operations such as:

- INSERT.
- UPDATE.
- DELETE.
- REINDEX.

This provides a basic operational perspective on index maintenance.

The recommendation score is a heuristic, not a measured database cost. Actual database execution plans must be inspected before applying index changes.

## 11. C++17 Implementation

The C++17 implementation emphasizes domain modeling and computational evaluation.

Its principal structures include:

- `ColumnStats`
- `Predicate`
- `Query`
- `Index`
- `Evaluation`

The `IndexAdvisor` class calculates estimated selectivity and checks the ordered index keys against the query workload.

It uses:

- `unordered_map` for column statistics.
- `set` for unique predicate classification.
- `vector` for index and workload collections.
- STL sorting algorithms for candidate ranking.

The cost estimator provides a simplified comparison between an index-access candidate and a table scan.

It incorporates:

- Estimated selectivity.
- Index prefix compatibility.
- Ordering compatibility.
- Covering potential.

The cost values are illustrative rather than PostgreSQL execution-cost units.

The implementation also identifies possible redundant indexes by comparing their leading key sequences.

## 12. Java 17 Enterprise Implementation

The Java implementation uses explicit domain types and service boundaries.

### Domain model

| Type | Purpose |
|---|---|
| ColumnStatistics | Stores cardinality and distribution information |
| Predicate | Represents an equality or range condition |
| CompositeIndex | Defines an ordered index |
| QueryWorkload | Stores workload requirements |
| IndexEvaluation | Stores evaluation results |
| IndexCatalog | Maintains registered indexes |
| IndexAdvisor | Implements evaluation policies |
| WorkloadService | Processes a collection of queries |

Java records provide immutable representations of the main domain objects.

The `IndexEvaluationPolicy` interface separates evaluation behavior from workload processing.

The `IndexCatalog` prevents duplicate index registration.

The `WorkloadService` evaluates each query against active indexes and produces a structured report.

Validation occurs at the domain and service boundaries.

This design is useful for larger enterprise systems in which index evaluation must be separated from workload collection, policy enforcement, and reporting.

## 13. PostgreSQL Implementation

The PostgreSQL script creates an isolated `index_lab` schema.

### Relational structure

The main entities are:

- `customers`
- `orders`
- `query_workload`

The orders table contains customer identifiers, status, creation dates, payment methods, regions, and amounts.

Constraints enforce valid domain values.

### Index definitions

| Index | Ordered columns | Main workload |
|---|---|---|
| Customer-status-date | customer_id, status, created_at | Customer order history |
| Status-date | status, created_at | Recent orders by status |
| Region-amount | region, total_amount | Regional amount filtering |
| Customer-covering | customer_id, status, created_at | Customer queries retrieving amount |
| Customer-only | customer_id | Redundancy investigation |

The additional customer-only index demonstrates why a shorter index can be potentially redundant when a larger index has the same leading key.

Redundancy is not determined solely by column prefixes. Uniqueness, constraints, included columns, predicates, operator classes, ordering, and actual workload must also be evaluated.

### Query-plan inspection

The SQL script uses:

`EXPLAIN (ANALYZE, BUFFERS)`

This reports:

- Selected execution plan.
- Actual execution time.
- Actual row counts.
- Buffer activity.
- Index and table access operations.

`EXPLAIN ANALYZE` executes the query, unlike ordinary `EXPLAIN`.

### Database statistics

The `pg_stats` view provides column statistics such as:

- `n_distinct`
- `null_frac`
- `most_common_vals`
- `most_common_freqs`
- `correlation`

These statistics help PostgreSQL estimate query cardinality and choose execution plans.

### Index usage statistics

`pg_stat_user_indexes` provides information about:

- Index scans.
- Index tuples read.
- Heap tuples fetched.
- Index storage size.

A low scan count does not automatically mean an index should be removed. Statistics collection periods, infrequent workloads, constraint enforcement, and application requirements must be considered.

### Partial indexes

The pending-order index contains only records satisfying:

`WHERE status = 'PENDING'`

This reduces the indexed population when the predicate matches a relatively small and frequently queried subset of the table.

### Transactions

The SQL implementation demonstrates transactional index creation.

Regular `CREATE INDEX` participates in transactions.

`CREATE INDEX CONCURRENTLY` is different because it cannot run inside a transaction block. It is useful when reducing write-blocking during index creation on production tables.

## 14. Index Selection Workflow

A practical index-design process can be represented as:

Query workload
    |
    v
Identify frequent predicates
    |
    v
Determine equality and range conditions
    |
    v
Inspect column cardinality and distribution
    |
    v
Determine required ordering
    |
    v
Select candidate column sequence
    |
    v
Evaluate existing indexes
    |
    v
Create candidate composite index
    |
    v
Inspect execution plans
    |
    v
Measure read and write performance
    |
    v
Retain, modify, or remove the index

### Decision criteria

| Consideration | Design implication |
|---|---|
| Frequent equality predicates | Consider leading index keys |
| Range predicate | Usually place after equality search keys |
| High-cardinality column | May offer greater equality selectivity |
| Frequent sorting | Consider compatible key ordering |
| Repeated query patterns | Prioritize recurring workloads |
| Heavy insert operations | Limit unnecessary indexes |
| Large included columns | Evaluate storage and write overhead |
| Correlated attributes | Inspect multi-column statistics |
| Existing prefix indexes | Investigate redundancy |

## 15. Common Failure Modes

### Incorrect column ordering

An index beginning with `status` may be less suitable for queries frequently filtering only by customer.

The index may still be useful for status-based queries.

### Excessive indexing

Every additional index requires storage and maintenance.

INSERT, UPDATE, and DELETE operations can become more expensive because affected index entries must also be maintained.

### Assuming selectivity is independent

Multiplying individual selectivities can produce inaccurate estimates when columns are correlated.

### Ignoring data distribution

Two columns with identical cardinality can have different distributions.

Most-common values and data skew can materially affect query planning.

### Ignoring range predicates

Columns after the first range condition generally cannot extend the same contiguous B-tree search boundary.

### Treating covering indexes as free optimizations

Including more columns increases index size and write costs.

### Removing indexes based only on scan counts

A low scan count does not establish that an index is unnecessary.

An index may enforce a uniqueness requirement or support an infrequent but important operation.

## 16. Performance and Security Considerations

Composite indexes are primarily performance structures, not security controls.

They do not replace:

- Authentication.
- Authorization.
- Row-level security.
- Constraints.
- Input validation.
- Transaction isolation.

From a performance perspective, index design must balance read optimization with write overhead and storage consumption.

Production evaluation should consider:

- Query latency distributions.
- Rows examined versus rows returned.
- Index size.
- Buffer-cache behavior.
- Sequential scans.
- Heap fetches.
- Index maintenance costs.
- Concurrent workload activity.
- Statistics freshness.

Database query execution plans should be compared using representative data and realistic parameter distributions.

A plan that performs well on a small development dataset may behave differently at production scale.

## 17. Complexity and Engineering Trade-offs

| Operation | General consideration |
|---|---|
| B-tree lookup | Approximately logarithmic tree traversal |
| Equality lookup | Depends on key selectivity and matching rows |
| Range scan | Depends on interval size and matching entries |
| Ordered retrieval | Can avoid a separate sorting operation |
| Index insertion | Requires index traversal and page maintenance |
| Index update | May modify multiple index entries |
| Index deletion | Requires removal of corresponding entries |
| Index construction | Requires processing and organizing indexed data |
| Covering retrieval | May reduce heap access |
| Additional index | Increases storage and write-maintenance costs |

These are general characteristics, not guaranteed execution times. Physical page access, caching, data distribution, concurrency, and optimizer decisions influence actual performance.

## 18. Implementation Coverage

| Requirement | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Composite index model | Yes | Yes | Yes | Yes | Yes |
| Column ordering | Yes | Yes | Yes | Yes | Yes |
| Leftmost-prefix evaluation | Yes | Yes | Yes | Yes | Yes |
| Selectivity estimation | Yes | Yes | Yes | Yes | Yes |
| Range predicates | Yes | Yes | Yes | Yes | Yes |
| Workload evaluation | Yes | Yes | Yes | Yes | Yes |
| Redundancy investigation | Yes | Yes | Yes | Yes | Yes |
| Query-plan inspection | SQLite | Model | Model | Model | Native |
| Covering index concepts | Candidate model | Candidate model | Candidate model | Candidate model | INCLUDE |
| Partial index | - | - | - | - | Yes |
| Maintenance analysis | - | Event-driven | - | - | Statistics |
| Validation | Yes | Yes | Yes | Yes | Constraints |

The five implementations approach composite index design from different engineering perspectives: Python provides executable database experiments, JavaScript provides workload and event analysis, C++17 implements a cost-oriented evaluation engine, Java 17 models enterprise domain services, and PostgreSQL demonstrates actual relational index definitions and query-plan behavior.
