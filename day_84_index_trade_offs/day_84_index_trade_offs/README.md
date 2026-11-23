# Index Trade-offs: Write Overhead, Storage, Maintenance and Over-Indexing

## 1. Technical Scope

Database indexes improve data retrieval by providing access paths that avoid scanning every row of a table. They also introduce additional work during data modification, consume storage, require maintenance and increase the operational complexity of database systems.

The central engineering decision is not whether indexes improve query performance. It is whether the improvement in read performance justifies their combined write, storage and maintenance costs.

This project implements a workload-oriented index analysis system using Python, JavaScript, C++17, Java 17 and PostgreSQL.

The five implementations examine different aspects of index management:

| Implementation | Engineering perspective |
|---|---|
| Python | Index simulation, workload analysis and recommendations |
| JavaScript | Event-driven workload processing and policy evaluation |
| C++17 | Index governance and computational cost evaluation |
| Java 17 | Enterprise index lifecycle and governance services |
| PostgreSQL | Relational workload records, reporting and maintenance workflows |

The examples use a commerce database containing an `orders` table.

Its representative columns are:

- `order_id`
- `customer_id`
- `status`
- `created_at`
- `region`
- `total_amount`
- `description`

The simulated table begins with 100,000 records.

## 2. Database Index Fundamentals

An index is a separate data structure that maintains searchable information about one or more table columns.

A typical B-tree index stores ordered key values and references to corresponding table rows.

Without an appropriate index, a database may need to inspect a large proportion of the table.

With an appropriate index, it can locate qualifying records through the index structure.

Conceptually:

**Without an index**

Query → Table scan → Examine rows → Return matching records

**With an index**

Query → Index traversal → Locate matching entries → Retrieve rows → Return results

The index does not eliminate all data access costs. A query returning many rows can still require substantial table access.

An index can also be ignored by the query planner when a sequential scan is estimated to be cheaper.

### 2.1 B-tree indexes

B-tree indexes maintain ordered keys and support:

- Equality searches.
- Range conditions.
- Ordered retrieval.
- Prefix searches on composite keys.
- Minimum and maximum operations.

They are suitable for many transactional workloads.

### 2.2 Hash indexes

Hash indexes organize entries using hash values.

They are primarily useful for equality comparisons.

They do not provide the same ordered traversal and range-search capabilities as B-tree indexes.

### 2.3 Composite indexes

A composite index contains multiple key columns.

For example:

`(status, created_at)`

This index is particularly useful for queries that constrain `status`, or constrain `status` followed by `created_at`.

The ordering of the columns matters.

An index on `(status, created_at)` does not generally provide the same access path for a query filtering only on `created_at`.

This is known as the leftmost-prefix consideration.

### 2.4 Covering indexes

A covering index contains the columns needed to satisfy a query without retrieving additional table columns.

For example:

`(region) INCLUDE (total_amount)`

The key column supports searching by region. The included column provides additional information for eligible queries.

Included columns are not equivalent to key columns. They do not contribute to the index's search ordering.

Covering indexes can reduce table access but increase index size and maintenance work.

## 3. Write Overhead

An index is not a free read optimization.

Whenever a table changes, the database must determine whether corresponding index entries must also change.

The cost depends on the operation and the indexed columns.

### 3.1 INSERT overhead

An INSERT creates a new table row and generally requires a corresponding entry in every applicable index.

For a table with five maintained indexes, one inserted row can require:

- One table insertion.
- Up to five index-entry insertions.
- Additional page modifications.
- Possible page splits.
- WAL generation and associated durability work.

The exact cost depends on the index structure, database implementation and inserted key distribution.

### 3.2 UPDATE overhead

An UPDATE does not necessarily modify every index.

Consider three indexes:

| Index | Indexed columns |
|---|---|
| `idx_customer` | customer_id |
| `idx_status_date` | status, created_at |
| `idx_region_covering` | region, with total_amount included |

An update to `status` can affect `idx_status_date`.

An update to `total_amount` can affect the covering index because the included column must remain current.

An update to an unrelated non-indexed column does not ordinarily require a change to these index entries.

PostgreSQL may use HOT updates when the relevant conditions are satisfied, reducing index maintenance for certain updates.

### 3.3 DELETE overhead

Deleting a row also requires the database to account for its index entries.

In PostgreSQL, dead tuples and index cleanup are handled through MVCC and maintenance mechanisms.

Physical removal is not necessarily immediate.

VACUUM and related maintenance processes help reclaim reusable space.

### 3.4 Write amplification

Write amplification describes the additional physical work caused by maintaining indexes and other database structures.

A simplified educational model is:

`Total write work = Table modification + Index maintenance + Related storage work`

For a table with N maintained indexes:

`Approximate index modifications per inserted row = N`

This is an approximation rather than a universal physical-I/O count.

Page splits, WAL, buffering, batching and storage behavior affect actual costs.

## 4. Index Storage Costs

Indexes consume storage independently of the underlying table.

The amount depends on:

- Number of indexed columns.
- Data types and key widths.
- Number of table rows.
- Included columns.
- Index structure.
- Page utilization.
- Duplicate values.
- Internal tree pages.
- Fill factor and fragmentation.

The educational implementations estimate index storage using:

`Estimated storage = Row count × Entry size / Page utilization`

The model assumes:

- 24 bytes per key column.
- 16 bytes per included column.
- 8 bytes for an entry reference.
- 85% effective page utilization.

These are simulation assumptions, not PostgreSQL's actual physical storage format.

Actual PostgreSQL index sizes should be measured using:

- `pg_relation_size()`
- `pg_indexes_size()`
- `pg_total_relation_size()`

### 4.1 Total storage overhead

The index-to-table storage ratio can be calculated as:

`Index storage ratio = Total index storage / Table storage`

A ratio greater than 1 means the estimated or measured index storage exceeds the table's storage.

This is not automatically a design failure. Some read-intensive analytical workloads legitimately require substantial indexing.

The ratio should be interpreted alongside query performance, write volume and storage constraints.

## 5. Index Maintenance

Indexes require ongoing maintenance as data changes.

The maintenance workload depends on the database engine, access patterns, storage behavior and index structure.

Important maintenance activities include:

| Activity | Purpose |
|---|---|
| VACUUM | Reclaim reusable space and support MVCC cleanup |
| ANALYZE | Refresh planner statistics |
| REINDEX | Rebuild index structures |
| REINDEX CONCURRENTLY | Rebuild eligible indexes with reduced write blocking |
| Fill-factor management | Influence page utilization and page-split behavior |
| Bloat investigation | Identify excessive physical storage |
| Index usage analysis | Identify ineffective or unused indexes |

### 5.1 Fragmentation and bloat

Fragmentation and bloat describe different physical conditions.

Fragmentation can refer to scattered or inefficiently organized index pages.

Bloat generally refers to unnecessary physical space occupied by obsolete or inefficiently maintained structures.

A high number of writes does not automatically establish that an index requires rebuilding.

The implementations use a simulated fragmentation percentage to demonstrate maintenance policies.

Production PostgreSQL systems should use actual database measurements rather than the simulated percentage.

### 5.2 Rebuilding indexes

Rebuilding creates a replacement index structure.

Potential benefits include:

- Recovering inefficiently used space.
- Reorganizing index pages.
- Addressing certain forms of bloat.
- Refreshing the physical structure.

Potential costs include:

- Additional I/O.
- CPU consumption.
- Temporary storage requirements.
- WAL generation.
- Locking or concurrency implications.
- Longer maintenance windows.

The appropriate maintenance strategy depends on the database engine and operational requirements.

## 6. Over-Indexing

Over-indexing occurs when a database maintains more indexes than the workload justifies.

It can result from:

- Creating indexes for every frequently queried column.
- Adding redundant composite indexes.
- Maintaining indexes that are no longer used.
- Creating covering indexes with unnecessarily wide included columns.
- Retaining indexes after application requirements change.
- Failing to review indexes after workload changes.

### 6.1 Unused indexes

An index with no recorded usage may appear unnecessary.

This does not prove that it is safe to remove.

Possible explanations include:

- A monitoring window that is too short.
- Infrequent reporting operations.
- Seasonal queries.
- Recently deployed features.
- Queries that execute only during exceptional conditions.
- Indexes supporting unique or primary-key constraints.

An index may also be required for integrity enforcement even if it is not frequently selected by application queries.

PostgreSQL's `pg_stat_user_indexes` provides useful usage statistics, but statistics must be interpreted in the context of database restarts, statistics resets and workload observation periods.

### 6.2 Redundant indexes

Consider these definitions:

- Index A: `(customer_id)`
- Index B: `(customer_id, created_at)`

Index B has the leading key of Index A.

Some queries can use Index B without Index A.

This creates a possible redundancy opportunity.

It does not prove that Index A should be removed.

The shorter index may be smaller, cheaper to scan, useful for specific ordering or filtering patterns, or required for a distinct uniqueness constraint.

### 6.3 Index proliferation

A large number of indexes can cause:

- Increased INSERT latency.
- Increased UPDATE latency.
- Increased DELETE work.
- Greater storage consumption.
- More expensive backup and restore operations.
- More complicated deployment procedures.
- Greater maintenance requirements.
- Increased operational monitoring effort.

Index removal should be evidence-based and reversible.

## 7. Read Performance Versus Write Performance

Index selection is a workload optimization problem.

A read-heavy workload can benefit substantially from additional indexes.

A write-heavy workload may experience significant degradation when too many indexes are maintained.

Consider two representative applications.

| Characteristic | Read-heavy analytics | Write-heavy transactions |
|---|---|---|
| SELECT frequency | High | Moderate |
| INSERT frequency | Low | High |
| UPDATE frequency | Low | High |
| Index strategy | Selective additional indexes | Minimal justified indexes |
| Storage sensitivity | Workload dependent | Often important |
| Maintenance priority | Query performance | Write throughput and availability |

The objective is not to maximize the number of indexes.

It is to find an index configuration that satisfies the application's performance and operational requirements.

A simplified workload ratio is:

`Read/write ratio = Read operations / Write operations`

A higher ratio can justify investing more in read optimization, but this ratio alone is insufficient.

The importance of individual queries, their selectivity, execution frequency and latency requirements must also be considered.

## 8. Index Selection and Evaluation

A disciplined index evaluation process should include:

1. Identify expensive queries.
2. Collect representative execution plans.
3. Measure query frequency.
4. Determine filtering and joining columns.
5. Estimate result-set cardinality.
6. Evaluate existing indexes.
7. Identify composite-index opportunities.
8. Estimate storage requirements.
9. Measure write overhead.
10. Test changes under representative workloads.

### 8.1 Query selectivity

Selectivity describes how effectively a condition reduces the number of qualifying rows.

A highly selective condition may identify a small subset of records.

A low-selectivity condition may return a large portion of a table.

For example:

`customer_id = 5012`

may identify a small number of orders.

A condition such as:

`status = 'COMPLETED'`

might identify a substantial proportion of the table.

The second condition may still benefit from an index when combined with other selective conditions, but an index on the status column alone is not necessarily beneficial.

### 8.2 Query frequency

A query executed 50,000 times per day may justify indexing even when each execution produces a modest improvement.

A query executed once per month may not justify substantial write and storage overhead.

The expected cumulative benefit should be considered.

### 8.3 Execution plans

PostgreSQL provides execution-plan analysis through:

- `EXPLAIN`
- `EXPLAIN ANALYZE`
- `BUFFERS`
- `pg_stat_statements`, when installed and configured

Execution plans help determine whether an index is being used and whether its use actually improves execution.

An index scan is not automatically faster than a sequential scan.

The planner considers estimated costs, statistics, row counts and other execution factors.

## 9. Python Implementation

File: `index_tradeoffs.py`

The Python program models a database table and its associated indexes.

### 9.1 Domain model

The primary classes are:

| Class | Responsibility |
|---|---|
| `DatabaseTable` | Table state and index registration |
| `Index` | Index definition, storage and metrics |
| `IndexStatistics` | Read, write and maintenance counters |
| `Query` | Query workload representation |
| `Workload` | Daily read and write volume |
| `IndexAdvisor` | Candidate index recommendations |

Enums distinguish index types, operations and lifecycle states.

Dataclasses provide structured storage for domain information.

### 9.2 Workload simulation

The program executes:

- 100,000 initial rows.
- 25,000 customer-history lookups.
- 12,000 pending-order lookups.
- 8,000 regional lookups.
- 2,000 description-search operations.
- 500 insert operations.
- 100 updates.
- 50 deletes.

The final row count is 100,450.

The implementation tracks which indexes are affected by changes to indexed or included columns.

### 9.3 Index advisor

`IndexAdvisor` examines query patterns and identifies missing index candidates.

Its recommendation score considers estimated read benefit relative to estimated storage.

The advisor does not execute DDL automatically.

This separation prevents an estimated improvement from being treated as a proven production optimization.

### 9.4 Limitations

The Python implementation uses a simplified in-memory model.

It does not implement a physical B-tree, transactional concurrency control, PostgreSQL MVCC or an actual query optimizer.

Its storage and cost estimates are educational approximations.

## 10. JavaScript Implementation

File: `index_tradeoffs.js`

The JavaScript implementation emphasizes asynchronous operations and event-driven observability.

### 10.1 Event-driven architecture

`DatabaseModel` extends Node.js `EventEmitter`.

It emits events for:

- Index creation.
- Index removal.
- Query execution.
- Write queuing.
- Write application.
- Index rebuilding.

These events separate database-state changes from reporting and monitoring logic.

### 10.2 Asynchronous write processing

Writes are placed in a queue.

`processWrites()` processes the queued operations asynchronously.

The implementation yields to the event loop between batches using `setImmediate()`.

This demonstrates an event-driven workload-processing pattern.

It does not represent a real database transaction manager.

### 10.3 Policy evaluation

`IndexPolicy` evaluates three conditions:

- Insufficient read usage.
- Excessive write-to-read ratio.
- High simulated fragmentation.

The output distinguishes between `REVIEW` and `RETAIN`.

An index is not automatically deleted because a policy identifies it as potentially inefficient.

### 10.4 State management

The implementation uses:

- `Map` for index registration.
- `Set` for table-column validation.
- `EventEmitter` for operational events.
- Promises for asynchronous workload processing.
- Private class fields for internal state.

The design separates index definitions, execution behavior and governance decisions.

### 10.5 Limitations

The queue is an educational single-process model.

It does not provide durable event delivery, distributed locking or database-level atomic transactions.

The storage calculations are estimates rather than actual storage measurements.

## 11. C++17 Implementation

File: `index_tradeoffs.cpp`

The C++ implementation emphasizes computational efficiency and explicit domain modeling.

### 11.1 Data structures

The program uses:

| Structure | Purpose |
|---|---|
| `vector` | Ordered key columns and query patterns |
| `set` | Unique table-column validation |
| `map` | Index registration |
| `IndexMetrics` | Performance statistics |
| `IndexDefinition` | Index configuration |
| `QueryPattern` | Read workload representation |
| `GovernanceEngine` | Index-retention evaluation |

### 11.2 Index selection

The `selectIndex()` method identifies indexes that support a query's leftmost key-column pattern.

It chooses a candidate based on key width and estimated storage.

The selection algorithm provides a simplified model of query access-path selection.

It does not replace PostgreSQL's cost-based optimizer.

### 11.3 Governance engine

`GovernanceEngine` evaluates:

- Indexes with substantial writes but no reads.
- Excessive write-to-read ratios.
- High simulated fragmentation.
- Index storage exceeding table storage.

It produces retention and review decisions.

### 11.4 Prefix-overlap analysis

The implementation identifies active indexes where the key columns of one index form a prefix of another.

This highlights potential redundancy.

A prefix overlap is a review signal, not an instruction to delete an index.

### 11.5 Limitations

The implementation uses a simplified index representation and does not maintain actual tree nodes, page layouts, locks, transactions or physical disk structures.

Its complexity and storage estimates describe the simulation rather than a production database engine.

## 12. Java 17 Implementation

File: `IndexTradeoffs.java`

The Java implementation uses enterprise-oriented service boundaries and explicit domain types.

### 12.1 Domain records

Java records represent immutable data:

- `IndexDefinition`
- `QueryPattern`
- `Workload`
- `IndexReport`
- `GovernanceResult`
- `QueryResult`

This reduces accidental modification of index definitions and workload descriptions.

### 12.2 Index lifecycle

The lifecycle uses:

- `ACTIVE`
- `DISABLED`
- `NEEDS_REBUILD`

These states distinguish operational availability from maintenance requirements.

A rebuild transitions an eligible index through its maintenance state before returning it to active service.

### 12.3 Enterprise governance service

`IndexGovernanceService` evaluates:

- Minimum write activity.
- Maximum write-to-read ratio.
- Storage budgets.
- Fragmentation thresholds.

The service returns structured governance results with explicit reasons.

### 12.4 Concurrency considerations

The implementation uses:

- `ConcurrentHashMap` for index registration.
- `AtomicLong` for workload counters.
- Synchronized methods for coordinated table operations.
- Immutable records for reporting.

These choices illustrate different concurrency-control mechanisms.

They do not establish full transactional consistency equivalent to a database engine.

### 12.5 Service separation

The database table owns index and workload state.

The governance service evaluates that state.

The reporting functions expose structured measurements.

This separation supports independent testing and policy evolution.

## 13. PostgreSQL Implementation

File: `index_tradeoffs.sql`

The SQL implementation models index governance as a relational workflow.

It uses the `index_lab` schema.

### 13.1 Relational structure

The principal relationships are:

Repository → Database Tables → Index Definitions → Usage Metrics

Additional relationships connect:

- Workload events to database tables.
- Maintenance history to indexes.
- Recommendations to database tables.

Foreign keys maintain referential integrity.

Unique constraints prevent duplicate index names within a table and duplicate metric records for an index.

Check constraints restrict index types, lifecycle states and invalid numeric values.

### 13.2 Workload tracking

`workload_events` records:

- SELECT operations.
- INSERT operations.
- UPDATE operations.
- DELETE operations.
- Affected row counts.
- Modified columns.
- Execution times.
- Event timestamps.

This provides the foundation for workload aggregation and historical evaluation.

### 13.3 Index usage metrics

`index_usage_metrics` stores:

- Read counts.
- Insert counts.
- Update counts.
- Delete counts.
- Fragmentation estimates.
- Last-use timestamps.

These values are simulated application-level observations.

They must not be confused with PostgreSQL's native statistics.

### 13.4 Storage estimation

The `estimate_index_storage()` function calculates an estimated storage requirement from:

- Row count.
- Number of key columns.
- Number of included columns.

The function provides a consistent estimation model for recommendations and reporting.

Actual physical sizes should be obtained from PostgreSQL system functions.

### 13.5 Governance evaluation

`evaluate_index_governance()` evaluates index usage against configurable thresholds.

Its results distinguish:

- Retained indexes.
- Indexes requiring review.
- Indexes requiring rebuild investigation.

The evaluation does not automatically remove indexes.

### 13.6 Maintenance workflow

`rebuild_index_metadata()` demonstrates a transaction-controlled metadata maintenance workflow.

It:

1. Locks the relevant index and usage records.
2. Captures the previous fragmentation value.
3. Marks the index as requiring rebuilding.
4. Resets the simulated fragmentation metric.
5. Records the maintenance event.
6. Restores the active state.

This procedure models governance metadata rather than executing PostgreSQL's physical `REINDEX` command.

A production rebuild requires actual index DDL and appropriate locking and availability planning.

### 13.7 Native PostgreSQL statistics

The SQL file includes views based on:

- `pg_stat_user_indexes`
- `pg_relation_size()`

These expose actual database index usage and physical storage measurements.

The native statistics should be used for production decisions.

### 13.8 Transaction management

The sample workflow runs inside a transaction.

This ensures that the metadata operations are committed together or rolled back when the transaction fails.

Database transactions do not make every operational maintenance command transactional. Some PostgreSQL commands, including certain concurrent index operations, have transaction restrictions.

## 14. Index Governance Workflow

A practical index lifecycle should use evidence before making structural changes.

The following workflow separates measurement, recommendation and execution.

**Stage 1: Workload collection**

Capture query frequency, execution latency, affected rows and read/write distribution.

**Stage 2: Index inventory**

Record existing indexes, column definitions, constraints and storage consumption.

**Stage 3: Query analysis**

Inspect query plans, selectivity, filtering conditions and join patterns.

**Stage 4: Candidate evaluation**

Identify missing indexes, duplicate structures and possible composite-index opportunities.

**Stage 5: Cost evaluation**

Estimate read improvement against additional write, storage and maintenance costs.

**Stage 6: Controlled implementation**

Deploy the index change using an appropriate maintenance and availability strategy.

**Stage 7: Measurement**

Compare execution plans, latency, throughput, storage and write performance before and after deployment.

**Stage 8: Retention review**

Retain, modify, rebuild or remove indexes according to measured evidence and application requirements.

## 15. Performance Considerations

### 15.1 Time complexity

For an illustrative balanced B-tree:

| Operation | Approximate complexity |
|---|---|
| Point lookup | O(log N) |
| Insert | O(log N) |
| Delete | O(log N) |
| Range retrieval | O(log N + K) |
| Full table scan | O(N) |

Here:

- N represents the number of indexed records.
- K represents the number of qualifying records returned.

These are simplified algorithmic descriptions.

Actual database performance also depends on page access, caching, concurrency, row visibility, selectivity and storage latency.

### 15.2 Index count

If a table has N independently maintained indexes, inserting a row may require updating each applicable index.

Consequently, the maintenance cost generally increases as the number of maintained indexes increases.

The actual cost is not necessarily linear in elapsed time because indexes differ in size, key width, page locality and update behavior.

### 15.3 Composite indexes

A carefully designed composite index can support multiple query patterns.

This can reduce the need for several single-column indexes.

The trade-off is that a wider index can consume more storage and require more maintenance.

### 15.4 Covering indexes

Covering indexes can reduce table access for suitable queries.

Their additional columns increase entry width.

They should be designed around frequently executed queries rather than used indiscriminately.

## 16. Security and Operational Considerations

Index governance is also an operational security concern.

Important controls include:

- Restricting permission to create and drop indexes.
- Reviewing production DDL changes.
- Recording maintenance operations.
- Protecting workload telemetry.
- Avoiding unnecessary sensitive values in monitoring logs.
- Monitoring disk-space consumption.
- Testing index changes in representative environments.
- Maintaining backup and recovery procedures.
- Controlling concurrent maintenance operations.
- Reviewing performance regressions after deployments.

Index statistics may reveal application usage patterns and workload characteristics.

Access to operational monitoring information should therefore follow the database's access-control policy.

Index removal should also account for primary-key and unique constraints.

A unique index may enforce data integrity even when its query usage is low.

## 17. Testing and Validation

The implementations include validation for:

- Empty table definitions.
- Duplicate columns.
- Invalid index types.
- Invalid composite index configurations.
- Unknown indexed columns.
- Invalid query patterns.
- Negative workload values.
- Invalid insert and delete counts.
- Duplicate index definitions.
- Invalid maintenance operations.
- Missing indexes.
- Invalid governance thresholds.

The Python, JavaScript, C++17 and Java 17 programs verify that the final simulated row count is 100,450.

The PostgreSQL script uses relational constraints, functions, procedures and transactions to validate and manage index metadata.

## 18. Running the Implementations

### Python

File: `index_tradeoffs.py`

Run with Python 3:

`python index_tradeoffs.py`

No external packages are required.

### JavaScript

File: `index_tradeoffs.js`

Run with Node.js 18 or later:

`node index_tradeoffs.js`

No npm dependencies are required.

### C++17

File: `index_tradeoffs.cpp`

Compile:

`g++ -std=c++17 -O2 -Wall -Wextra -pedantic index_tradeoffs.cpp -o index_tradeoffs`

Execute:

`./index_tradeoffs`

On Windows:

`g++ -std=c++17 -O2 -Wall -Wextra -pedantic index_tradeoffs.cpp -o index_tradeoffs.exe`

`.\index_tradeoffs.exe`

### Java 17

File: `IndexTradeoffs.java`

Compile:

`javac IndexTradeoffs.java`

Execute:

`java IndexTradeoffs`

No third-party dependencies are required.

### PostgreSQL

File: `index_tradeoffs.sql`

Execute using:

`psql -U postgres -d your_database -f index_tradeoffs.sql`

The script creates the `index_lab` schema and its demonstration records.

The native PostgreSQL statistics views expose database-level information and depend on the permissions and availability of the underlying system views.

The script targets PostgreSQL 14 or later.

## 19. Limitations and Interpretation

The five implementations are deliberately designed as educational index-governance models.

They do not all implement a physical database index.

Their simulated cost values, fragmentation metrics and storage estimates are intended to illustrate relationships between workload characteristics and index-management decisions.

The PostgreSQL implementation provides access to native PostgreSQL index statistics and physical storage measurements.

Production index decisions should be based on actual execution plans, representative workload measurements, constraint requirements, concurrency behavior and operational availability.

The key engineering distinction is that an index provides a potential read-performance benefit while creating an ongoing obligation to maintain another database structure. Its value must therefore be evaluated across the complete database workload, not from SELECT performance alone.
