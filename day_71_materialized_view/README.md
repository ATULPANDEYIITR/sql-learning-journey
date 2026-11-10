# Materialized Views: Refresh Strategies and Performance Optimization

## 1. Materialized Views

A materialized view is a database object that stores the result of a query as persisted data. Unlike an ordinary database view, which evaluates its defining query when accessed, a materialized view retains a previously computed result.

Materialized views are useful when analytical queries repeatedly perform expensive operations involving:

- Large table scans.
- Multiple joins.
- Aggregations.
- Grouping and sorting.
- Window calculations.
- Complex expressions.
- Historical reporting.

The principal trade-off is between query performance and data freshness. Reading a materialized view can be substantially faster than recomputing its underlying query, but its contents may not reflect the latest source-table changes.

### Ordinary views versus materialized views

| Characteristic | Ordinary view | Materialized view |
|---|---|---|
| Data storage | Query definition | Persisted query result |
| Query execution | Evaluated when queried | Reads stored results |
| Data freshness | Reflects current committed source data under the query's transaction snapshot | Depends on the latest successful refresh |
| Refresh required | No | Yes |
| Storage consumption | Normally minimal | Requires storage for result data and indexes |
| Indexing result columns | Not directly | Supported |
| Expensive aggregation | Recomputed when queried | Can be computed during refresh |
| Appropriate workloads | Operational queries | Repeated analytical queries |

A materialized view does not automatically maintain itself when its source tables change.

## 2. Materialized View Architecture

The implementations use a sales analytics domain.

The source system maintains products, regions and sales transactions. Analytical consumers need repeated reports by category, region and transaction date.

The materialized views store precomputed aggregates instead of requiring every reporting request to scan and aggregate the complete transaction table.

### Domain relationship

    Products ───────┐
                    |
    Regions ────────┼── Sales Transactions
                    |
                    v
             Source Tables
                    |
                    v
             Aggregation Query
                    |
                    v
           Materialized View
                    |
          ┌─────────┴─────────┐
          v                   v
      Indexes             Refresh Metadata
          |                   |
          v                   v
     Analytical          Refresh Scheduler
       Queries                 |
                               v
                         Refresh Audit

The source tables remain authoritative. The materialized view is a derived representation and must be recoverable from the source data.

### Example aggregation

The sales data contains:

| Sale | Category | Region | Quantity | Unit price |
|---|---|---|---:|---:|
| 1 | Electronics | North | 3 | 1,200 |
| 2 | Furniture | South | 2 | 850 |
| 3 | Electronics | North | 1 | 1,200 |
| 4 | Clothing | West | 5 | 90 |
| 5 | Electronics | East | 2 | 700 |

Revenue is calculated as:

\[
Revenue = Quantity \times UnitPrice
\]

The materialized result groups transactions by category and region.

| Category | Region | Transactions | Quantity | Revenue |
|---|---|---:|---:|---:|
| Electronics | North | 2 | 4 | 4,800 |
| Furniture | South | 1 | 2 | 1,700 |
| Clothing | West | 1 | 5 | 450 |
| Electronics | East | 1 | 2 | 1,400 |

The result can be reused by dashboards and analytical queries.

## 3. Materialized View Creation and Storage

A materialized view is defined using a query that returns the required analytical result.

In PostgreSQL, `CREATE MATERIALIZED VIEW` executes the defining query and stores its output.

The SQL implementation creates two materialized views:

| Materialized view | Purpose | Grouping |
|---|---|---|
| `mv_daily_sales` | Daily sales analysis | Date, category, region |
| `mv_product_performance` | Product performance reporting | Product |

The first view supports time-series and regional reporting. The second supports product-level performance analysis.

### Materialized view storage

A materialized view contains persisted rows representing the result of its defining query.

It can have indexes independent of the source-table indexes.

This is important because the best indexing strategy for analytical results may differ from the best indexing strategy for transaction processing.

For example:

- The source sales table benefits from indexes on transaction dates and foreign keys.
- The daily sales materialized view benefits from indexes on category, region and date.
- The product performance view benefits from an index on revenue for ranking operations.

Materialized view indexes must be designed around actual query patterns.

### Unique indexes

PostgreSQL requires an appropriate unique index for `REFRESH MATERIALIZED VIEW CONCURRENTLY`.

The index must use ordinary columns, cover all rows, and satisfy the documented restrictions for concurrent refresh.

The SQL implementation creates:

- `uq_mv_daily_sales`
- `uq_mv_product_performance`

The unique index on the daily view identifies each date, category and region combination.

The product view uses `product_id` as its unique key.

## 4. Refresh Strategies

Refresh operations synchronize a materialized view with its underlying source query.

The refresh strategy affects:

- Query availability.
- Refresh duration.
- Storage activity.
- Locking behavior.
- Data freshness.
- Resource consumption.

Three important approaches are full refresh, concurrent refresh and incremental maintenance.

### 4.1 Full refresh

A full refresh recomputes the complete materialized view from its defining query.

PostgreSQL syntax:

`REFRESH MATERIALIZED VIEW mv_daily_sales;`

The database rebuilds the stored result using the current source data visible to the refresh operation.

**Characteristics**

- Recalculates the complete result.
- Handles source inserts, updates and deletes.
- Does not require a change-tracking mechanism.
- Can consume substantial CPU, memory and I/O.
- Blocks concurrent readers of the materialized view while refreshing.

**Suitable use cases**

- Small analytical datasets.
- Periodic reporting.
- Nightly warehouse processing.
- Views with complicated aggregation logic.
- Situations where correctness is more important than uninterrupted reads.

The Python implementation uses `full_refresh()` to aggregate the complete source snapshot and publish a new generation.

The C++ implementation constructs a new aggregate map before replacing the previous snapshot.

The Java implementation uses immutable snapshot objects and publishes the completed result through a volatile reference.

### 4.2 Concurrent refresh

PostgreSQL supports:

`REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales;`

Concurrent refresh allows ordinary readers to continue accessing the previously populated materialized view while PostgreSQL calculates and applies the refreshed result.

The previous result remains available until the refresh operation completes.

**Requirements**

- The materialized view must already be populated.
- A qualifying unique index must exist.
- The unique index must use ordinary columns and cover all rows.
- The operation cannot execute inside an explicit transaction block.

Concurrent refresh is not equivalent to incremental refresh.

PostgreSQL still executes the defining query to obtain the new result. It uses the unique index to reconcile the new contents with the existing materialized view.

**Advantages**

- Readers are not blocked by the same access-exclusive lock required by ordinary refresh.
- Existing reports remain available during refresh.
- Useful for frequently queried analytical datasets.

**Trade-offs**

- Can require more work and temporary storage.
- Requires a suitable unique index.
- Competes with normal workloads for resources.
- Does not eliminate refresh latency.

### 4.3 Incremental refresh

Incremental refresh maintains the materialized result by processing only changes since the previous successful refresh.

Instead of rebuilding the entire result, the system identifies affected groups and applies the corresponding changes.

PostgreSQL's ordinary materialized view implementation does not automatically provide general incremental maintenance through `REFRESH MATERIALIZED VIEW`.

Incremental maintenance must therefore be implemented using an appropriate mechanism, such as:

- Change-data capture.
- Transaction logs.
- Change-event tables.
- Signed aggregation deltas.
- Incrementally maintained summary tables.
- Specialized database extensions.

The SQL implementation demonstrates a change-log and summary-table architecture.

The Python, JavaScript, C++ and Java programs simulate incremental processing using versioned change events.

### Example of incremental aggregation

Suppose an existing group contains:

| Measure | Existing value |
|---|---:|
| Transactions | 10 |
| Quantity | 35 |
| Revenue | 25,000 |

A new transaction contributes:

| Measure | Change |
|---|---:|
| Transactions | +1 |
| Quantity | +3 |
| Revenue | +3,600 |

The updated aggregate becomes:

| Measure | New value |
|---|---:|
| Transactions | 11 |
| Quantity | 38 |
| Revenue | 28,600 |

An update must be represented as the removal of the old contribution followed by the addition of the new contribution.

A deletion must subtract the deleted transaction's original contribution.

This distinction is essential when a transaction changes category, region, date or product.

### Refresh strategy comparison

| Factor | Full | Concurrent | Incremental |
|---|---|---|---|
| Recalculates complete query | Yes | Yes | No, when implemented correctly |
| Reader availability during refresh | Restricted | Preserved for ordinary readers | Depends on implementation |
| Change tracking | Not required | Not required | Required |
| Update handling | Automatic through recomputation | Automatic through recomputation | Explicit |
| Delete handling | Automatic through recomputation | Automatic through recomputation | Explicit |
| Implementation complexity | Low | Moderate | High |
| Best suited for | Periodic complete rebuilds | Frequently queried views | High-volume change-driven workloads |

## 5. Refresh Scheduling and Dependency Management

A refresh schedule determines when a materialized view should be updated.

A refresh policy should consider:

- Source transaction volume.
- Query frequency.
- Maximum acceptable data age.
- Refresh execution time.
- Database workload.
- Business reporting deadlines.
- Dependencies between materialized views.

### Time-based refresh

A time-based strategy refreshes a view at predetermined intervals.

Examples include:

| Materialized view | Illustrative interval |
|---|---|
| Daily sales | 5 minutes |
| Product performance | 10 minutes |
| Historical monthly report | 24 hours |

The SQL registry stores the configured interval and maximum acceptable staleness.

These values are configuration metadata. Actual scheduling requires an external scheduler or a controlled database worker.

### Change-based refresh

A change-based strategy evaluates source activity.

For example, a materialized view may be refreshed when:

- A minimum number of transactions have changed.
- A high-priority business event occurs.
- The source change log reaches a threshold.
- The current snapshot exceeds its allowed staleness.

### Dependency-aware refresh

Materialized views may depend on other derived objects.

A dependency graph determines the correct refresh sequence.

    Source Tables
          |
          v
    Daily Aggregates
          |
          v
    Regional Summary
          |
          v
    Executive Dashboard

The underlying daily aggregate must be refreshed before the dependent regional summary.

All four program implementations contain dependency-aware refresh planning using graph traversal.

A depth-first traversal identifies dependencies and produces a topological execution order.

Cycle detection prevents invalid dependency definitions.

For a graph containing \(V\) views and \(E\) dependency relationships, the traversal requires:

\[
O(V+E)
\]

time, excluding the cost of the actual refresh operations.

## 6. Incremental Maintenance and Change Data Capture

Incremental maintenance is more complicated than identifying recently inserted rows.

A correct implementation must account for all operations affecting the source data.

### Insert

A new source transaction increases the relevant aggregate.

\[
NewAggregate = OldAggregate + Contribution
\]

### Update

An update may change multiple grouping dimensions.

The old contribution must be removed from the previous group, and the new contribution must be added to the new group.

\[
NewAggregate =
OldAggregate - OldContribution + NewContribution
\]

### Delete

A deletion subtracts the original transaction contribution.

\[
NewAggregate = OldAggregate - DeletedContribution
\]

### Change-event structure

The programs represent source modifications using:

| Field | Purpose |
|---|---|
| Version | Identifies change order |
| Operation | Insert, update or delete |
| Before | Previous source record |
| After | New source record |
| Timestamp | Records change time |

A monotonically increasing version provides a processing watermark.

The refresh worker records the last successfully processed version.

A subsequent refresh processes changes after that watermark.

### Watermark management

A watermark identifies the boundary between processed and unprocessed changes.

    Change Log
        |
        v
    Last Successful Version
        |
        v
    New Change Events
        |
        v
    Validate Event Sequence
        |
        v
    Apply Aggregate Deltas
        |
        v
    Commit Aggregate Changes
        |
        v
    Advance Watermark

The watermark and aggregate modifications must be committed atomically.

Otherwise, a failure between aggregate updates and watermark advancement can cause missing or duplicate contributions.

Production implementations should also address:

- Concurrent change producers.
- Transaction ordering.
- Change-log retention.
- Duplicate event processing.
- Recovery after partial failure.
- Source snapshot consistency.
- Changes occurring during refresh.

The SQL procedure illustrates the operational structure of incremental maintenance. Its simplified change-log example is not a complete production implementation for updates and deletes: exact old transaction dates and grouping keys must be captured, and signed deltas must be applied atomically.

## 7. Data Freshness and Staleness

A materialized view is stale when its stored contents do not represent the latest relevant source state.

Staleness can be measured using:

1. Time since the last successful refresh.
2. Number of unprocessed source changes.
3. Difference between the source version and snapshot version.
4. Business-specific freshness requirements.

### Version-based staleness

The program implementations compare source and snapshot versions.

\[
VersionLag = SourceVersion - SnapshotVersion
\]

A nonzero version lag indicates that source changes have occurred after the snapshot was generated.

This is a useful simulation, but real database implementations must also account for transaction snapshots, change-log watermarks and concurrent source activity.

### Time-based staleness

The SQL implementation uses a maximum staleness threshold.

For example, if a reporting view has a maximum permitted age of 600 seconds, a snapshot older than that threshold is considered stale.

Freshness requirements depend on the business workload.

| Workload | Possible freshness requirement |
|---|---|
| Executive dashboard | 5 to 15 minutes |
| Operational monitoring | Seconds to minutes |
| Daily financial reporting | Defined reporting cutoff |
| Historical analysis | Daily or weekly |

These intervals are illustrative, not universal requirements.

## 8. Query Performance Optimization

Materialized views improve performance when repeated queries can reuse precomputed results.

The main optimization opportunities involve aggregation, indexing, partitioning, query selection and refresh scheduling.

### Precomputation

Without a materialized view, an analytical query may repeatedly join sales, products and regions before aggregating the results.

A materialized view performs this work during refresh.

The reporting query can then read the smaller aggregated result.

### Indexing

Indexes should support the actual filtering and ordering patterns.

Examples in the SQL implementation include:

| Index | Purpose |
|---|---|
| `idx_sales_sold_at` | Source-table date filtering |
| `idx_sales_product_date` | Product and time-based analysis |
| `idx_sales_region_date` | Regional transaction retrieval |
| `idx_mv_daily_sales_category_date` | Category reporting |
| `idx_mv_daily_sales_region_date` | Regional reporting |
| `idx_mv_product_revenue` | Product revenue ranking |

An index is not automatically beneficial.

Indexes increase storage requirements and maintenance costs. They can also increase refresh-related write activity.

### Covering indexes

PostgreSQL supports `INCLUDE` columns in suitable indexes.

A covering index can contain additional columns required by a query, potentially allowing index-only scans when visibility conditions permit.

The SQL implementation demonstrates this on the source sales table.

### Query-plan analysis

The SQL script uses:

`EXPLAIN (ANALYZE, BUFFERS)`

This provides execution information including:

- Actual execution time.
- Estimated versus actual row counts.
- Scan types.
- Join operations.
- Buffer activity.
- Index usage.

Performance comparisons should use representative data volumes and realistic query patterns.

A materialized view should not be assumed to be faster for every query.

## 9. Python Implementation

The Python file implements a repository-style simulation of materialized view management.

### Core classes

| Class | Responsibility |
|---|---|
| `SalesRecord` | Immutable and validated source transaction |
| `Aggregate` | Maintains transaction, quantity and revenue totals |
| `SalesDatabase` | Manages source records and versions |
| `MaterializedView` | Builds, stores and queries aggregate snapshots |
| `RefreshScheduler` | Coordinates dependency-aware refresh operations |
| `RefreshAudit` | Records execution outcomes |

### Important mechanisms

**Dataclasses and enums**

Dataclasses provide structured domain objects. Enums distinguish refresh strategies and outcomes.

**Thread synchronization**

The source repository uses a reentrant lock to coordinate concurrent modifications.

The materialized view uses a lock to publish completed snapshots.

**Atomic snapshot publication**

A candidate result is built before replacing the active snapshot. Readers therefore receive a complete old or new snapshot rather than partially constructed aggregate data.

**Validation**

The program rejects invalid identifiers, duplicate sales, negative prices, invalid quantities and unsupported grouping dimensions.

**Testing**

The `--test` option executes assertions for:

- Full refresh.
- Incremental refresh.
- Version-based staleness.
- Deletion handling.
- Duplicate identifier rejection.
- Snapshot generation changes.

The Python incremental implementation is deliberately correctness-first. It rebuilds the aggregate from the latest source snapshot instead of applying individual deltas. This demonstrates incremental refresh coordination and state management, but it does not achieve the computational savings of true delta-based maintenance.

## 10. JavaScript Implementation

The JavaScript implementation uses Node.js event-driven programming.

It models source changes as events and exposes refresh operations through asynchronous methods.

### Core classes

| Class | Responsibility |
|---|---|
| `SourceRepository` | Maintains source records and emits change events |
| `AggregationDefinition` | Defines grouping dimensions |
| `AggregateState` | Maintains aggregate values |
| `MaterializedView` | Manages snapshot publication and queries |
| `RefreshCoordinator` | Executes dependency-aware refreshes |

### Event-driven behavior

The source repository extends `EventEmitter`.

Successful insert, update and delete operations publish structured events.

This separates source-table modification from refresh coordination.

### Asynchronous refresh

The materialized view uses `async` functions and promises.

Concurrent requests for the same active refresh share a promise instead of unnecessarily starting duplicate operations.

### Query caching

Queries are cached using a key containing:

- Snapshot generation.
- Filter parameters.

When a new snapshot is published, the cache is cleared.

This prevents queries from returning results associated with an older generation.

The JavaScript implementation uses full recomputation when processing its incremental refresh request. It correctly handles deletions and updates, but its incremental label describes the refresh trigger rather than an optimized delta-processing algorithm.

## 11. C++17 Implementation

The C++ program focuses on explicit domain modeling, change-event processing and computational efficiency.

### Core components

| Component | Responsibility |
|---|---|
| `Sale` | Source transaction |
| `ChangeEvent` | Versioned source modification |
| `Aggregate` | Incremental aggregate calculations |
| `SourceTable` | Source records and change journal |
| `MaterializedView` | Stored aggregate snapshots |
| `RefreshPlanner` | Dependency ordering |

### Data structures

The implementation uses:

- `unordered_map` for source records.
- `map` for ordered aggregate groups.
- `vector` for change events.
- `set` for dependency and cycle detection.
- `optional` for absent before-and-after records.

The incremental implementation applies actual insert, update and delete deltas.

This differs from the Python and JavaScript correctness-first rebuild approaches.

### Concurrency and consistency

Mutexes protect source-table operations and snapshot access.

The implementation copies the previous snapshot before calculating a candidate result.

A generation check prevents publication if another refresh has already replaced the snapshot.

The implementation is a single-process simulation. It does not provide database-level transaction isolation or durable change-event storage.

## 12. Java 17 Implementation

The Java implementation presents an enterprise-oriented design.

It separates domain records, refresh policies, source management and orchestration.

### Domain types

| Type | Responsibility |
|---|---|
| `Sale` | Validated immutable source record |
| `GroupKey` | Aggregate grouping identity |
| `Aggregate` | Immutable aggregate values |
| `ChangeEvent` | Source modification record |
| `Snapshot` | Immutable materialized result |
| `RefreshAudit` | Refresh execution record |

### Refresh policies

The `RefreshPolicy` interface separates freshness requirements from refresh execution.

`StalenessPolicy` evaluates version lag against a configured threshold.

This permits different views to have different refresh requirements without embedding those requirements inside the aggregation algorithm.

### State management

A snapshot contains:

- Generation number.
- Source version.
- Refresh timestamp.
- Aggregated rows.
- SHA-256 checksum.

The snapshot is immutable.

A volatile reference publishes the completed snapshot to readers.

The implementation also provides asynchronous refresh requests through `CompletableFuture`.

### Dependency service

`RefreshService` coordinates refresh order and maintains an audit collection.

Its graph traversal rejects unknown dependencies and circular relationships.

## 13. PostgreSQL Implementation

The SQL file provides the relational implementation and database workflow.

### Source tables

| Table | Purpose |
|---|---|
| `products` | Product master data |
| `regions` | Regional master data |
| `sales` | Transaction records |
| `sales_change_log` | Source modification events |

Foreign keys preserve relationships between sales and their master records.

Check constraints reject invalid quantities and prices.

### Materialized views

| Object | Purpose |
|---|---|
| `mv_daily_sales` | Date, category and region aggregates |
| `mv_product_performance` | Product performance aggregates |

### Operational tables

| Table | Purpose |
|---|---|
| `daily_sales_summary` | Incrementally maintained aggregate storage |
| `materialized_view_registry` | Refresh configuration and watermarks |
| `refresh_audit` | Execution history and failures |

### Functions and procedures

| Database object | Responsibility |
|---|---|
| `capture_sales_change()` | Records insert, update and delete operations |
| `refresh_daily_sales_full()` | Performs and audits a full refresh |
| `record_refresh_success()` | Records a successful refresh |
| `refresh_daily_sales_incremental()` | Demonstrates change-driven summary maintenance |
| `is_view_stale()` | Evaluates snapshot freshness |
| `refresh_eligibility()` | Determines whether a view requires refresh |

The SQL also includes reporting views, query-plan analysis, source-data transactions and aggregation queries.

### Transactional integrity

Source-table modifications and their trigger-generated change records participate in the same database transaction.

If a transaction rolls back, the associated change-log entries also roll back.

Incremental aggregate changes and watermark advancement must similarly occur in one transaction.

A production implementation must preserve exact old grouping dimensions and timestamps, use signed deltas, and make event processing idempotent.

The included incremental procedure is an educational workflow rather than a complete general-purpose CDC implementation.

## 14. Refresh Failure Handling

Refresh operations can fail for several reasons:

- Insufficient disk space.
- Database connection interruption.
- Query execution timeout.
- Invalid source records.
- Constraint violations.
- Missing dependencies.
- Concurrent refresh conflicts.
- Incomplete change logs.
- Incorrect watermarks.
- Insufficient privileges.

A reliable system must preserve the previous successful snapshot when a candidate refresh fails.

### Failure-handling workflow

    Refresh Requested
          |
          v
    Validate Configuration
          |
          v
    Read Consistent Source State
          |
          v
    Build Candidate Result
          |
          v
    Validate Candidate
          |
          v
    Publish Snapshot
          |
          v
    Record Successful Audit

If any operation fails before publication:

    Refresh Failure
          |
          v
    Preserve Previous Snapshot
          |
          v
    Record Error
          |
          v
    Alert or Retry
          |
          v
    Reconcile Source Changes

Retries should use bounded attempts and appropriate backoff. A failed refresh must not advance an incremental processing watermark.

## 15. Performance and Complexity Considerations

Let:

- \(N\) represent the number of source records.
- \(G\) represent the number of aggregate groups.
- \(D\) represent the number of changed records.
- \(V\) represent the number of materialized views.
- \(E\) represent the number of view dependencies.

| Operation | Typical complexity |
|---|---|
| Full aggregation using hash grouping | \(O(N)\) expected |
| Full aggregation using ordered grouping | \(O(N \log G)\) |
| Incremental delta application | \(O(D)\) expected with hash-based groups |
| Ordered aggregate update | \(O(D \log G)\) |
| Reading a snapshot | Depends on result size and query filters |
| Dependency traversal | \(O(V+E)\) |
| Query filtering without an index | \(O(G)\) |

These estimates describe the application-level algorithms. Actual database performance also depends on disk I/O, indexes, join plans, memory availability, concurrency and transaction overhead.

### Storage considerations

Materialized views consume storage independently of their source tables.

Indexes consume additional storage.

Multiple overlapping materialized views can duplicate substantial amounts of derived data.

Before creating a materialized view, evaluate whether the expected reduction in query cost justifies:

- Storage requirements.
- Refresh workload.
- Index maintenance.
- Operational complexity.
- Freshness limitations.

## 16. Security and Operational Governance

Materialized views can contain sensitive or aggregated business information.

Their security requirements should be evaluated independently of the source tables.

Important controls include:

- Restricting view creation and refresh privileges.
- Separating application and reporting roles.
- Limiting access to sensitive dimensions.
- Avoiding unrestricted execution of dynamic SQL.
- Validating query filters.
- Protecting refresh audit information.
- Monitoring resource consumption.
- Restricting access to source change logs.
- Applying appropriate retention policies.
- Avoiding unnecessary exposure of detailed transaction records.

A materialized view should not be treated as automatically safe merely because it contains aggregated data. Small groups and detailed dimensions can still expose confidential information.

## 17. Practical Selection Guidelines

| Situation | Suitable approach |
|---|---|
| Small dataset and infrequent reporting | Full refresh |
| Frequently queried view with readers that must remain available | Concurrent refresh |
| Large dataset with frequent small changes | Incremental maintenance |
| Strict reporting freshness requirements | Frequent controlled refresh |
| Complex dependent analytical views | Dependency-aware scheduling |
| Expensive historical reporting | Precomputed daily or monthly aggregates |
| Unreliable change tracking | Full refresh and reconciliation |

The correct strategy depends on the relationship between source-change volume, query frequency, acceptable staleness and refresh cost.

## 18. Execution and Validation

### Python

- Requires Python 3.10 or newer.
- Uses only the standard library.
- Execute the normal demonstration using `python materialized_views.py`.
- Execute validation tests using `python materialized_views.py --test`.

### JavaScript

- Requires Node.js 18 or newer.
- Uses built-in Node.js modules.
- Execute using `node materialized_views.js`.

### C++17

- Requires a C++17 compiler.
- Compile using `g++ -std=c++17 -O2 -Wall -Wextra -pedantic materialized_views.cpp -o materialized_views`.
- Execute using `./materialized_views` or `.\materialized_views.exe` on Windows.

### Java 17

- Requires JDK 17.
- Compile using `javac MaterializedViews.java`.
- Execute using `java MaterializedViews`.
- Enable assertions using `java -ea MaterializedViews` when running assertion-based tests.

### PostgreSQL

- Requires PostgreSQL 15 or newer.
- Execute the SQL script using a role with the required database privileges.
- The script recreates the dedicated `analytics_mv` schema.
- Concurrent refresh statements must execute outside explicit transaction blocks.

## 19. Technical Distinctions

The following distinctions are important when designing a production analytical system:

| Concept | Meaning |
|---|---|
| Materialized view | Persisted result of a query |
| Full refresh | Complete recomputation of the result |
| Concurrent refresh | Refresh that preserves ordinary reader access to the previous result |
| Incremental refresh | Maintenance based on source changes |
| Change-data capture | Mechanism for identifying source modifications |
| Watermark | Boundary identifying processed changes |
| Snapshot | Consistent published version of derived data |
| Staleness | Difference between the stored result and required freshness |
| Refresh dependency | Relationship requiring one derived object to be refreshed before another |
| Refresh audit | Record of refresh execution and outcome |
| Unique index | Uniqueness enforcement and a requirement for PostgreSQL concurrent refresh |
| Query optimization | Reduction of execution cost through suitable storage, indexes and query plans |

The central engineering decision is not simply whether to create a materialized view. It is how to maintain a correct, sufficiently fresh and efficiently accessible representation of changing source data without imposing unacceptable costs on the operational database.
