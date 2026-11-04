# Denormalization: Performance-Driven Database Design

## 1. Concept and Purpose

Denormalization is the deliberate introduction of redundant data into a database to reduce the computational cost of frequently executed queries.

A normalized relational database stores each logical fact in an appropriate location. Relationships between entities are represented through primary keys and foreign keys. Queries retrieve related information through joins, filtering, and aggregation.

Denormalization changes the physical representation of selected information without necessarily changing its logical meaning.

For example, a customer order report may require:

- Customer information.
- The number of orders.
- The number of completed orders.
- Total completed-order spending.

A normalized implementation obtains these values by joining customers and orders and calculating aggregates. A denormalized implementation stores the calculated values in a customer summary table.

The central engineering decision is whether the reduction in read cost justifies the additional storage, update processing, consistency management, and operational complexity.

## 2. Normalization and Denormalization

| Characteristic | Normalization | Denormalization |
|---|---|---|
| Data representation | Facts stored in appropriate relations | Selected facts duplicated |
| Read operations | May require joins and aggregation | Frequently accessed values are precomputed |
| Write operations | Usually fewer duplicated updates | May require several additional updates |
| Storage | Generally lower redundancy | Higher storage consumption |
| Consistency | Enforced through relational constraints | Requires synchronization mechanisms |
| Query complexity | May involve multiple joins | Often simpler read queries |
| Typical application | Transaction processing | Reporting and read-intensive workloads |

Normalization and denormalization are not mutually exclusive database architectures.

A practical design retains normalized authoritative records and introduces selected denormalized structures for performance-sensitive access patterns.

## 3. Performance-Driven Denormalization

Denormalization should follow workload measurement rather than assumptions about query performance.

### 3.1 Read-intensive workloads

A read-intensive workload repeatedly retrieves the same calculated information.

Consider a customer dashboard displaying order count and completed-order spending.

The normalized query performs:

1. Customer retrieval.
2. Order relationship lookup.
3. Status filtering.
4. Aggregation.
5. Result construction.

A denormalized summary retrieves the calculated values directly.

The primary benefit is reduced repeated computation and potentially fewer joins.

### 3.2 Write-intensive workloads

Write-intensive applications frequently insert, update, or delete records.

When an order changes, every affected denormalized representation must be considered.

For example:

- Inserting a completed order increases the order count.
- It increases the completed-order count.
- It increases total spending.
- Cancelling a completed order decreases the completed-order count and spending.
- Changing the customer relationship affects both the previous and new customer summaries.

These additional operations create write amplification.

### 3.3 Workload evaluation

A simplified decision model is:

\[
C_{\text{normalized}} =
R \times C_r + W \times C_w
\]

\[
C_{\text{denormalized}} =
R \times C'_r + W \times C'_w + C_s
\]

Where:

- \(R\): number of read operations.
- \(W\): number of write operations.
- \(C_r\): normalized read cost.
- \(C'_r\): denormalized read cost.
- \(C_w\): normalized write cost.
- \(C'_w\): denormalized write cost.
- \(C_s\): synchronization and maintenance cost.

Denormalization is economically useful when:

\[
C_{\text{denormalized}} <
C_{\text{normalized}}
\]

These expressions are simplified workload models. Real evaluation should include storage, locking, cache behavior, network transfer, indexing, concurrency, and operational costs.

## 4. Forms of Denormalization

### 4.1 Duplicated columns

A value from one relation is copied into another relation to avoid repeatedly joining tables.

Example:

- Authoritative customer name: `customers.customer_name`
- Duplicated customer name: `customer_order_summary.customer_name`

When the original name changes, the copied value must be refreshed.

This technique is useful when a frequently displayed attribute is relatively stable.

### 4.2 Summary tables

A summary table stores calculated information derived from multiple source records.

The implementation uses:

`customer_order_summary`

Its attributes include:

| Attribute | Meaning |
|---|---|
| `customer_id` | Customer identifier |
| `customer_name` | Duplicated customer name |
| `order_count` | Number of associated orders |
| `completed_order_count` | Number of completed orders |
| `total_spending` | Completed-order revenue |
| `projection_version` | Version of the generated projection |
| `generated_at` | Last successful generation time |

A summary table is particularly useful for dashboards, business intelligence, and frequently executed analytical queries.

### 4.3 Precomputed aggregates

Precomputed aggregates store values such as:

- Total sales.
- Average transaction amount.
- Completed transaction count.
- Inventory quantities.
- Customer activity statistics.

These calculations are performed during refresh or source-data processing rather than during every read.

### 4.4 Materialized views

A materialized view stores the result of a database query physically.

Unlike an ordinary view, which evaluates its query when accessed, a materialized view retains previously calculated results until refreshed.

PostgreSQL supports materialized views and concurrent refresh operations when the required unique index exists.

Materialized views are appropriate for repeatable analytical queries where refresh frequency can be controlled.

The PostgreSQL implementation uses a summary table instead because it demonstrates targeted invalidation, per-customer refresh, version tracking, and transactional maintenance.

## 5. Redundancy and Data Integrity

Redundancy means storing the same logical information in multiple physical locations.

It can improve retrieval performance but introduces several anomalies.

### 5.1 Update anomaly

If a customer name changes in the authoritative table but not in the summary table, different queries return different names.

### 5.2 Insert anomaly

A newly inserted order may not appear in the customer summary until the projection is refreshed.

### 5.3 Delete anomaly

Deleting an order without recalculating the corresponding summary may leave incorrect order counts and revenue.

### 5.4 Aggregation anomaly

Incorrect handling of order statuses can produce inaccurate totals.

For example, pending and cancelled orders must not contribute to completed-order spending.

### 5.5 Referential integrity

Duplicated attributes do not eliminate the need for relationships.

The implementations retain customer identifiers and validate that every order references an existing customer.

The PostgreSQL implementation uses primary keys, foreign keys, unique constraints, and check constraints to protect authoritative data.

## 6. Synchronization Strategies

The most important operational challenge is maintaining the relationship between authoritative records and their duplicated representations.

### 6.1 Synchronous maintenance

The source write and projection update occur within the same transaction.

Characteristics:

- Immediate visibility of updated summaries after commit.
- Stronger consistency guarantees.
- Additional write latency.
- Greater transaction and locking complexity.

The PostgreSQL transactional example inserts an order and refreshes the corresponding customer summary before committing.

### 6.2 Asynchronous maintenance

A source transaction records that a projection requires refreshing.

A separate process performs the refresh.

Characteristics:

- Lower source-write overhead.
- Better opportunities for batching.
- Temporary stale reads.
- Additional monitoring and recovery requirements.

The PostgreSQL implementation uses `projection_refresh_queue` to identify affected customers.

The Python, JavaScript, C++17, and Java implementations maintain corresponding dirty-record collections or projection states.

### 6.3 Eventual consistency

Eventual consistency allows a denormalized representation to remain temporarily different from its authoritative source.

It assumes that successful synchronization will eventually make the representations consistent.

For a customer dashboard, a small delay may be acceptable.

For financial settlement or inventory reservation, stale values may cause serious business errors. Such operations should use authoritative records and appropriate transactional controls.

### 6.4 Strict and eventual reads

The implementations distinguish two read modes:

| Mode | Behavior |
|---|---|
| Strict | Refresh an invalidated summary before returning it |
| Eventual | Return the currently stored summary, even if potentially stale |

Strict reads provide fresher results at the cost of additional computation or waiting.

Eventual reads reduce synchronization overhead but expose the application to temporary inconsistencies.

## 7. Incremental Refresh and Full Rebuilding

### Incremental refresh

An incremental refresh updates only the affected customer summary.

If customer 1 receives a new order, only customer 1 needs recalculation.

This avoids rebuilding every summary after every transaction.

For a targeted aggregate, the update can also be calculated arithmetically. Such an approach requires careful handling of status transitions, deletes, customer transfers, retries, and duplicate event delivery.

### Full rebuilding

A full rebuild recalculates every customer summary from authoritative data.

It is useful for:

- Recovery after projection corruption.
- Periodic reconciliation.
- Changes to aggregate calculation rules.
- Initial projection population.
- Repair after missed synchronization events.

The implementations provide full rebuild operations as a recovery mechanism.

For large databases, full rebuilding should be scheduled and executed in controlled batches to avoid excessive resource consumption.

## 8. Python Implementation

The Python program models a normalized customer and order repository alongside a denormalized summary projection.

### Main components

| Component | Responsibility |
|---|---|
| `Customer` | Customer entity |
| `Order` | Order entity |
| `CustomerSummary` | Precomputed customer aggregate |
| `NormalizedDatabase` | Authoritative data storage |
| `DenormalizedDatabase` | Summary generation and maintenance |
| `PerformanceResult` | Query timing information |

### Implemented mechanisms

- Dataclasses for structured domain records.
- Dictionaries for efficient identifier-based lookup.
- Sets for tracking dirty customer projections.
- Enumerations for denormalization strategies.
- Input validation and custom exceptions.
- Strict and non-strict summary retrieval.
- Full and individual projection rebuilding.
- Consistency comparison against normalized records.
- Query timing using `time.perf_counter()`.
- JSON-formatted reporting.

The program also demonstrates customer-name propagation and rejection of orders referencing nonexistent customers.

The implementation uses an in-memory repository. It illustrates projection behavior but does not provide database-level transaction isolation or concurrent access protection.

## 9. JavaScript Implementation

The JavaScript program provides an event-driven read-model architecture.

### Main components

| Component | Responsibility |
|---|---|
| `OrderRepository` | Validated authoritative storage |
| `SummaryProjection` | Denormalized customer read model |
| `DenormalizationPolicy` | Workload-based design evaluation |
| `benchmark()` | Asynchronous query measurement |

### Implemented mechanisms

- Private class fields for encapsulated repository state.
- `Map` for identifier-based storage.
- `Set` for projection invalidation.
- `Object.freeze()` for immutable stored records.
- `EventEmitter` for projection lifecycle notifications.
- Promises and asynchronous refresh operations.
- Structured policy evaluation.
- Strict and eventual read modes.
- Projection consistency validation.

Events distinguish invalidation from successful refresh.

This is useful when a production application has multiple consumers that need to respond to projection changes.

The implementation uses an in-memory event emitter. It does not provide durable message delivery, distributed locking, or crash recovery.

## 10. C++17 Implementation

The C++ program models denormalization as a repository-level read optimization.

### Main components

| Component | Responsibility |
|---|---|
| `Repository` | Authoritative customer and order storage |
| `DenormalizationEngine` | Aggregate computation and refresh |
| `CustomerAggregate` | Read-optimized customer record |
| `GovernancePolicy` | Workload suitability evaluation |
| `ConsistencyMode` | Strict or eventual retrieval |

### Implementation decisions

- `unordered_map` supports average constant-time identifier lookup.
- `unordered_set` tracks invalidated customer records.
- `vector` provides ordered reporting.
- `insert_or_assign` replaces calculated projections.
- Exceptions reject invalid records.
- Version numbers identify projection generations.
- Full rebuild uses a temporary map before replacing the existing projection.

The aggregate calculation scans source orders. For \(C\) customers and \(O\) orders, a complete rebuild can require \(O(C \times O)\) work in this implementation.

A production implementation would group orders by customer in one pass, reducing aggregation work to approximately \(O(C+O)\) with suitable hash-based structures.

The program uses floating-point amounts for demonstration. Financial production systems should use integer minor currency units or an exact decimal representation.

## 11. Java 17 Implementation

The Java program represents an enterprise-oriented projection service with explicit domain types and lifecycle states.

### Domain model

- `Customer`: immutable customer entity.
- `Order`: validated transaction entity.
- `CustomerSnapshot`: immutable denormalized representation.
- `WorkloadMetrics`: workload characteristics.
- `PolicyDecision`: projection eligibility result.

### Projection lifecycle

The `ProjectionState` enumeration defines:

| State | Meaning |
|---|---|
| `CLEAN` | Projection matches the latest known source state |
| `DIRTY` | Source changes require recalculation |
| `REBUILDING` | A refresh is executing |
| `FAILED` | The last refresh attempt failed |

The `ProjectionService` manages state transitions and publishes changes through listeners.

The `ProjectionPolicy` evaluates read-to-write ratios, duplicated copies, expected staleness, and consistency requirements.

The implementation also uses:

- Java records for immutable domain structures.
- Streams for filtering and ordering.
- Generics through standard collections.
- `CompletableFuture` for asynchronous refresh.
- `AtomicLong` for projection version generation.
- Synchronized methods for in-process state protection.
- Custom domain exceptions for validation failures.

The example is a single-process model. A distributed enterprise implementation requires database transactions, durable messaging, cross-instance coordination, and explicit retry policies.

## 12. PostgreSQL Implementation

The SQL script creates an independent schema named `denorm_demo`.

### Relational architecture

The authoritative relations are:

- `customers`
- `orders`

The denormalized relation is:

- `customer_order_summary`

Operational tables include:

- `projection_refresh_queue`
- `projection_refresh_log`

### Database integrity

The implementation uses:

- Identity-generated primary keys.
- Foreign-key relationships.
- Unique customer email addresses.
- Nonnegative monetary constraints.
- Valid order-status constraints.
- Nonnegative aggregate constraints.
- Partial indexes for completed orders.
- Covering index columns for relevant retrieval operations.

### Trigger-based invalidation

The `orders_invalidate_projection` trigger marks the relevant customer summary as dirty after order insertion, modification, or deletion.

The customer-name trigger performs equivalent invalidation when the authoritative customer name changes.

Invalidation is separated from recalculation. This prevents every source transaction from necessarily performing expensive aggregation work.

### Projection refresh function

`refresh_customer_summary()`:

1. Validates the customer.
2. Reads the authoritative customer name.
3. Aggregates associated orders.
4. Calculates completed-order revenue.
5. Inserts or updates the summary.
6. Increments the projection version.
7. Removes the processed invalidation record.
8. Records the refresh operation.

### Batch processing

`refresh_dirty_summaries()` processes a bounded set of invalidated customers.

This provides a basic pattern for background workers and controlled refresh operations.

The example uses a sequential procedure. A multi-worker production queue would require appropriate row locking, commonly using `FOR UPDATE SKIP LOCKED`, together with durable retry and failure handling.

### Reporting and evaluation

The SQL script includes:

- Normalized aggregation queries.
- Direct denormalized retrieval.
- A reporting view.
- Customer-segment aggregation.
- Source-to-projection reconciliation.
- Transactional refresh.
- Eventual-consistency processing.
- Staleness monitoring.
- `EXPLAIN (ANALYZE, BUFFERS)` comparisons.
- Refresh-operation monitoring.

The failure example demonstrates a negative order amount rejected by a check constraint.

## 13. Performance Considerations

Denormalization changes the distribution of computational work.

| Operation | Normalized design | Denormalized design |
|---|---|---|
| Customer dashboard read | Join and aggregate | Read summary |
| Order insertion | Insert source record | Insert and invalidate or update projection |
| Customer-name update | Update customer | Update customer and refresh copies |
| Revenue reporting | Aggregate transaction data | Read precomputed revenue |
| Recovery | Recalculate source-derived values | Rebuild projection |
| Storage | Lower duplication | Higher duplication |

### Index selection

Indexes should reflect actual access patterns.

The SQL implementation includes:

- A customer identifier index on orders.
- A partial index for completed orders.
- A descending spending index on the summary table.
- An index on completed-order counts.
- A timestamp index for order retrieval.

Indexes improve selected reads but increase storage requirements and write maintenance costs.

Too many indexes can make a write-heavy workload slower.

### Cache behavior

A denormalized table can reduce repeated calculations and improve data locality.

Frequently accessed summaries may also remain in database or application caches.

Caching introduces another consistency boundary. Updating the database projection does not automatically guarantee that every application cache has been invalidated.

### Storage cost

If a duplicated attribute is stored in many records, the additional storage can become significant.

The storage impact should include:

- Data pages.
- Index pages.
- Replication traffic.
- Backup volume.
- Cache memory.
- Projection history and audit records.

## 14. Security and Reliability

Denormalized structures can expose information through duplicated copies even when the original relation has restricted access.

Security controls should consider every representation of sensitive information.

Important controls include:

- Restricting direct writes to projection tables.
- Applying role-based access control.
- Validating source records before projection updates.
- Protecting audit records from unauthorized modification.
- Avoiding sensitive information in application logs.
- Applying retention policies to duplicated records.
- Using parameterized SQL in application integrations.
- Monitoring failed refresh operations.

Projection maintenance should be idempotent.

A repeated refresh should produce the same calculated values from the same authoritative data rather than accumulating duplicate effects.

In distributed systems, change events should carry identifiers or versions that allow consumers to detect duplicate, delayed, or out-of-order processing.

## 15. Limitations and Production Trade-offs

The five implementations demonstrate core denormalization mechanisms but use simplified in-memory or single-database environments.

Important production concerns include:

| Concern | Required engineering consideration |
|---|---|
| Concurrent updates | Transaction isolation and locking |
| Multiple application instances | Distributed coordination |
| Event delivery | Durable queues and retries |
| Duplicate events | Idempotent processing |
| Out-of-order changes | Version checks or ordered processing |
| Large projections | Incremental and partitioned refresh |
| Full rebuilds | Staged replacement and resource limits |
| Financial accuracy | Exact decimal arithmetic |
| Stale reads | Explicit consistency contracts |
| Projection failures | Monitoring, recovery, and reconciliation |

A projection should not silently become a second independent source of truth.

The normalized records remain authoritative, while denormalized structures serve explicitly defined read and reporting requirements.

## 16. Complexity Analysis

Let:

- \(C\) represent the number of customers.
- \(O\) represent the number of orders.
- \(D\) represent the number of duplicated summary records.
- \(K\) represent the number of orders belonging to one customer.

| Operation | Demonstration implementation | Optimized approach |
|---|---|---|
| Customer lookup | Average \(O(1)\) with hash maps | Average \(O(1)\) |
| Order insertion | Average \(O(1)\) | Average \(O(1)\) |
| Single-customer aggregation | \(O(O)\) | \(O(K)\) with customer indexing |
| Full projection rebuild | \(O(C \times O)\) | \(O(C+O)\) |
| Dirty-record tracking | Average \(O(1)\) | Average \(O(1)\) |
| Summary retrieval | Average \(O(1)\) | Average \(O(1)\) |
| Sorted reporting | \(O(C\log C)\) | \(O(C\log C)\) |

These complexities describe the principal in-memory operations. Actual database performance also depends on index selectivity, query plans, disk I/O, memory, concurrency, and transaction behavior.

## 17. Practical Decision Criteria

A denormalization decision should be justified by measurable workload characteristics.

| Decision factor | Favor denormalization when | Retain normalized access when |
|---|---|---|
| Read frequency | Repeated expensive reads | Reads are infrequent |
| Write frequency | Writes are comparatively low | Writes are frequent |
| Aggregation cost | Repeated aggregation is expensive | Aggregation is inexpensive |
| Data freshness | Small delays are acceptable | Immediate consistency is mandatory |
| Storage | Extra storage is affordable | Storage duplication is costly |
| Maintenance | Synchronization is manageable | Update propagation is complex |
| Reporting | Repeated summaries are required | Queries are irregular |

The most suitable architecture often combines normalized transactional storage with carefully selected denormalized projections.

The decision must account for read performance, write amplification, storage, data freshness, operational complexity, and the consequences of stale information.
