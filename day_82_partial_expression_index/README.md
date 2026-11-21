# Partial and Expression Indexes

## Conditional Indexes and Function-Based Indexing

## 1. Introduction

Database indexes improve data retrieval by providing access structures that allow the database engine to locate records without examining every row in a table.

A conventional index generally maintains entries for all applicable table rows. As tables grow, maintaining indexes on frequently changing or rarely queried data can introduce unnecessary storage consumption and write overhead.

Two specialized indexing techniques address different optimization requirements:

- **Partial indexes** restrict index membership to rows satisfying a specified condition.
- **Expression indexes** index the result of an expression or function applied to one or more columns.

These mechanisms can also be combined. A partial expression index stores computed keys only for rows satisfying a specified predicate.

The implementations in this project demonstrate index construction, conditional membership, expression evaluation, query eligibility, uniqueness enforcement, index maintenance, and workload analysis.

## 2. Fundamental Indexing Concepts

### 2.1 Conventional indexes

A conventional index maintains searchable keys associated with table records.

For example, an index on `customer_email` supports searches using that column.

The conceptual relationship is:

`Table rows → Indexed keys → Matching record locations`

A B-tree is a commonly used PostgreSQL index structure. Its ordered keys support equality searches, range conditions, and ordering operations.

The index does not automatically improve every query. PostgreSQL evaluates available access paths and selects a plan based on estimated costs and statistics.

### 2.2 Index keys

An index key is the value maintained by the index.

For a conventional index:

`customer_email`

The indexed key corresponds directly to a table column.

For an expression index:

`lower(customer_email)`

The indexed key represents the computed result.

### 2.3 Index predicates

A predicate is a Boolean condition evaluated against table rows.

Examples include:

- `status = 'OPEN'`
- `amount > 500`
- `status = 'OPEN' AND amount > 300`

A partial index includes only records for which its predicate evaluates to TRUE.

Rows evaluating to FALSE or NULL are not included.

This distinction is important because partial indexing changes the index's membership rather than changing the underlying table.

## 3. Partial Indexes

### 3.1 Definition

A partial index is an index containing entries for only a subset of table rows.

The subset is defined by a `WHERE` condition in the index definition.

For example:

`CREATE INDEX idx_open_orders ON orders (order_id) WHERE status = 'OPEN';`

The index contains only open orders.

Consider the following records:

| Order ID | Status | Amount | Included in partial index |
|---:|---|---:|---|
| 1 | OPEN | 450 | Yes |
| 2 | PAID | 900 | No |
| 3 | OPEN | 250 | Yes |
| 4 | CANCELLED | 120 | No |
| 5 | ARCHIVED | 300 | No |
| 6 | OPEN | 780 | Yes |

The index excludes records that do not satisfy its predicate.

### 3.2 Conditional index membership

A partial index is particularly useful when:

- Queries repeatedly access a specific status.
- Only a small proportion of records require frequent retrieval.
- Historical records are rarely accessed.
- The application has clearly defined active and inactive states.
- A subset requires a uniqueness constraint.

For example, an order-processing application may frequently retrieve open orders while completed and archived orders are accessed less frequently.

A partial index can reduce the number of indexed entries compared with an equivalent full index.

### 3.3 Predicate implication

A query can use a partial index when the query condition implies the index predicate.

Consider an index defined by:

`WHERE status = 'OPEN'`

The following query is compatible:

`SELECT order_id FROM orders WHERE status = 'OPEN' AND amount > 500;`

Every qualifying query row satisfies the index predicate.

The following query cannot use that partial index for its general result set:

`SELECT order_id FROM orders WHERE status = 'PAID';`

Paid orders are not represented in the index.

PostgreSQL uses planner-recognizable predicate implication rules. It does not perform unrestricted mathematical theorem proving.

Complex expressions, parameterized conditions, and differences in expression structure can prevent an otherwise logically related query from using a partial index.

For parameterized queries, a generic prepared plan may be unable to establish that a parameter always satisfies a partial-index predicate. A custom plan can sometimes make a more specific determination.

### 3.4 Selectivity

Selectivity describes how much of a table satisfies a condition.

For example:

- 10,000 total orders.
- 1,000 open orders.
- 9,000 non-open orders.

An index containing only open orders has fewer entries than a full index on the same key.

The benefit depends on the number of qualifying records and the actual workload.

A predicate matching nearly every row may provide little storage advantage.

## 4. Expression Indexes

### 4.1 Definition

An expression index stores the result of an expression evaluated against table columns.

Example:

`CREATE INDEX idx_lower_email ON orders (lower(customer_email));`

The indexed key is the lowercase representation of the email address.

This is useful when an application performs case-insensitive searches.

Without a matching expression index, the database may need to evaluate the function for many rows.

With the expression index, PostgreSQL can potentially locate the computed value through the index.

### 4.2 Function-based indexing

Function-based indexing is another name commonly used for indexing expressions involving functions.

Examples:

| Indexed expression | Application |
|---|---|
| `lower(email)` | Case-insensitive email lookup |
| `upper(region)` | Normalized region lookup |
| `date_trunc('day', created_at)` | Date-based grouping or filtering |
| `abs(balance)` | Searches involving absolute values |
| `coalesce(reference_code, '')` | Searches using a normalized NULL representation |

The expression must be suitable for indexing.

PostgreSQL requires functions and operators used in index expressions to be immutable. Their results must depend only on their arguments and remain stable for the same inputs.

A function depending on the current time or mutable external state is unsuitable for an immutable expression index.

### 4.3 Expression matching

An expression index is not a universal replacement for an ordinary column index.

For example:

`CREATE INDEX idx_lower_email ON orders (lower(customer_email));`

A query using:

`WHERE lower(customer_email) = 'alice@example.com'`

can use the expression index when the planner determines it is beneficial.

A query using:

`WHERE customer_email = 'alice@example.com'`

requests a direct comparison. The expression index is not necessarily applicable.

The query expression must be compatible with the indexed expression.

### 4.4 Expression evaluation and maintenance

The database maintains expression-index values when the underlying indexed columns change.

For example, changing `customer_email` requires maintaining the corresponding `lower(customer_email)` index entry.

This reduces lookup computation but introduces additional write-processing costs.

## 5. Partial Expression Indexes

### 5.1 Combined mechanism

A partial expression index combines conditional membership and expression-based key generation.

Example:

`CREATE INDEX idx_open_lower_email ON orders (lower(customer_email)) WHERE status = 'OPEN';`

Two separate decisions determine the index contents:

1. The predicate determines whether a row belongs to the index.
2. The expression determines the key stored for an included row.

Conceptually:

`Table row → Predicate evaluation → Expression evaluation → Index entry`

Only open orders contribute lowercase email keys.

### 5.2 Example

| Email | Status | Indexed key |
|---|---|---|
| Alice@example.com | OPEN | alice@example.com |
| Bob@example.com | PAID | Not indexed |
| Carol@example.com | OPEN | carol@example.com |
| David@example.com | CANCELLED | Not indexed |

This index is appropriate for frequent case-insensitive searches restricted to open orders.

### 5.3 Conditional composite indexing

A partial index can also contain multiple indexed columns.

Example:

`CREATE INDEX idx_open_region_created ON orders (region, created_at DESC) WHERE status = 'OPEN';`

The index is restricted to open orders and orders its keys by region and creation time.

This can support regional retrieval and ordering patterns.

Column order matters in multicolumn B-tree indexes. Queries filtering by the leading key generally have the strongest direct access opportunities.

## 6. Unique Partial Indexes

### 6.1 Conditional uniqueness

A unique partial index enforces uniqueness only among rows included in the index.

Example:

`CREATE UNIQUE INDEX idx_active_email ON user_accounts (lower(email)) WHERE account_status = 'ACTIVE';`

This enforces case-insensitive uniqueness for active accounts.

It permits multiple inactive accounts to have the same email address.

| Account | Email | Status | Allowed |
|---|---|---|---|
| 1 | admin@example.com | ACTIVE | Yes |
| 2 | old@example.com | INACTIVE | Yes |
| 3 | ADMIN@example.com | ACTIVE | No |
| 4 | ADMIN@example.com | INACTIVE | Yes |

This mechanism is useful when uniqueness depends on lifecycle state.

It differs from a conventional unique constraint, which generally applies to all rows covered by that constraint.

## 7. Index Maintenance and Database Operations

### 7.1 INSERT operations

When a new record is inserted:

- PostgreSQL evaluates partial-index predicates.
- Qualifying rows receive corresponding index entries.
- Expression values are calculated for expression indexes.
- Unique indexes validate key conflicts.

An insertion violating a unique partial index is rejected.

### 7.2 UPDATE operations

Updating an indexed source column may require recalculating its expression key.

Updating a predicate column can change index membership.

For example:

`OPEN → PAID`

The row stops satisfying an open-order partial-index predicate.

Conversely:

`PAID → OPEN`

The row becomes eligible for inclusion.

PostgreSQL maintains these changes automatically.

### 7.3 DELETE operations

Deleting a table row also removes the corresponding index entries through normal database maintenance.

Applications should not manually maintain PostgreSQL index contents.

### 7.4 Storage and write overhead

Each index consumes storage and requires maintenance.

Adding indexes can increase:

- INSERT latency.
- UPDATE latency.
- DELETE processing.
- WAL generation.
- Storage requirements.
- Vacuum and maintenance activity.

A smaller partial index can reduce some of these costs, but the benefits depend on predicate selectivity and the workload.

## 8. Query Planning and Performance

### 8.1 Cost-based optimization

PostgreSQL uses a cost-based query optimizer.

It considers factors such as:

- Table and index statistics.
- Estimated row counts.
- Predicate selectivity.
- Available access paths.
- Sequential I/O.
- Random I/O.
- Memory and caching assumptions.
- Ordering requirements.
- Join operations.

An available index is not necessarily the selected index.

For a small table, a sequential scan may be cheaper than traversing an index and retrieving table rows.

### 8.2 EXPLAIN

`EXPLAIN` displays the planned execution strategy.

`EXPLAIN ANALYZE` executes the query and reports actual execution measurements.

`EXPLAIN (ANALYZE, BUFFERS)` also reports buffer activity.

Useful plan information includes:

| Plan information | Meaning |
|---|---|
| Seq Scan | Sequential table scan |
| Index Scan | Index lookup followed by row retrieval |
| Index Only Scan | Index supplies the required values where visibility permits |
| Bitmap Index Scan | Index entries collected into a bitmap |
| Bitmap Heap Scan | Heap rows retrieved using a bitmap |
| Index Cond | Conditions applied through the index |
| Filter | Conditions evaluated after row retrieval |
| Rows Removed by Filter | Rows discarded by filtering |
| Buffers | Buffer access information |

The demonstration dataset is intentionally small. PostgreSQL may select sequential scans even when suitable indexes exist.

### 8.3 Index-only scans

An index-only scan can avoid heap access when the index contains the required columns and visibility-map conditions permit it.

A suitable covering index may use `INCLUDE` to store additional non-key columns.

For example:

`CREATE INDEX idx_open_order_covering ON orders (region) INCLUDE (amount) WHERE status = 'OPEN';`

Included columns are payload values rather than additional search keys.

### 8.4 Index statistics

PostgreSQL exposes index usage information through `pg_stat_user_indexes`.

Important fields include:

- `idx_scan`: Number of index scans.
- `idx_tup_read`: Index entries returned.
- `idx_tup_fetch`: Live table rows fetched through index scans.

These statistics should be interpreted over a meaningful observation period.

A low scan count alone is insufficient justification for dropping an index.

## 9. Python Implementation

The Python implementation uses the standard-library SQLite module.

It models orders through dataclasses and enumerations.

The `IndexDefinition` class describes index metadata, including:

- Index name.
- Index type.
- Expression.
- Predicate.
- Uniqueness.

The `IndexManager` validates definitions and creates actual SQLite indexes.

### Implemented mechanisms

| Mechanism | Implementation |
|---|---|
| Database management | `OrderDatabase` |
| Domain validation | `Order.validate()` |
| Index metadata | `IndexDefinition` |
| Index creation | `IndexManager` |
| Conditional indexing | Partial `WHERE` predicates |
| Expression indexing | `lower()` and `upper()` |
| Query inspection | `EXPLAIN QUERY PLAN` |
| Eligibility simulation | `IndexEligibility` |
| Conditional uniqueness | Unique partial index |
| Testing | Assertions and exception checks |

The script demonstrates index creation, query execution, membership changes, and basic performance measurements.

Its eligibility evaluator intentionally uses conservative exact predicate matching. It is not a replacement for PostgreSQL's planner.

SQLite and PostgreSQL have different planner rules, data types, execution strategies, and index capabilities. The Python implementation is an executable educational demonstration rather than a PostgreSQL performance benchmark.

## 10. JavaScript Implementation

The JavaScript implementation adopts an event-driven architecture.

It separates expression evaluation, predicate evaluation, index metadata, storage, query eligibility, and workload analysis.

### Core components

| Component | Responsibility |
|---|---|
| `ExpressionRegistry` | Evaluates registered index expressions |
| `PredicateRegistry` | Evaluates conditional membership |
| `IndexDefinition` | Validates index metadata |
| `IndexCatalog` | Maintains rows and index entries |
| `QueryPolicy` | Describes a query's index requirements |
| `IndexAdvisor` | Evaluates candidate indexes |
| `QueryService` | Executes asynchronous query simulations |
| `WorkloadAnalyzer` | Ranks frequently executed query patterns |

### Event-driven behavior

The catalog emits events when indexes become ready, records are inserted, records are updated, or indexes are removed.

This separates state changes from reporting and monitoring.

### Transaction-like updates

Before an update, the implementation snapshots index entries.

If an index operation fails, the previous index state is restored.

This illustrates consistency management within an in-memory model. It does not provide the full isolation, durability, concurrency control, or crash recovery of a relational database transaction.

### Workload analysis

The workload analyzer records query signatures and execution frequencies.

Frequently executed expressions can be examined as possible index candidates.

Execution frequency alone does not establish that an index is beneficial. Selectivity, write volume, table size, query latency, and storage costs must also be evaluated.

## 11. C++17 Implementation

The C++17 implementation emphasizes domain modeling and an explicit query eligibility engine.

It uses standard-library containers and value-oriented structures.

### Core components

| Component | Responsibility |
|---|---|
| `Order` | Represents an order record |
| `ExpressionEngine` | Calculates expression keys |
| `Predicate` | Represents conditional index membership |
| `IndexDefinition` | Defines index characteristics |
| `DatabaseIndex` | Maintains indexed key mappings |
| `OrderDatabase` | Manages rows and indexes |
| `PredicateLogic` | Evaluates predicate implication |
| `QueryPlanner` | Identifies eligible index candidates |
| `PlanCandidate` | Represents estimated index cost |

### Index representation

The implementation uses a map from expression keys to sets of order identifiers.

Conceptually:

`Indexed key → {matching record identifiers}`

This permits demonstration of:

- Key generation.
- Duplicate-key handling.
- Conditional membership.
- Unique-key enforcement.
- Record updates.
- Candidate selection.

### Predicate implication

The C++ model handles status conditions and numeric minimum-amount conditions.

It demonstrates why a more restrictive query can use a partial index.

For example, an index containing open orders above 300 can support a query requesting open orders above 500.

The predicate engine is deliberately limited to its defined domain. It does not implement PostgreSQL's complete expression parser or optimizer.

### Complexity considerations

For an in-memory ordered map:

- Key lookup is typically \(O(\log n)\).
- Insertion is typically \(O(\log n)\).
- Removal is typically \(O(\log n)\).
- Iterating over all records is \(O(n)\).
- Unique-key checks in the illustrative implementation depend on the number of distinct indexed keys.

The implementation favors clarity and explicit consistency handling rather than production database performance.

## 12. Java 17 Implementation

The Java implementation presents an enterprise-oriented indexing service.

It uses records, interfaces, immutable domain objects, collections, and explicit service boundaries.

### Architecture

`OrderRepository → ManagedIndex → IndexDefinition → KeyExpression`

The query execution path is:

`QuerySpecification → IndexEligibilityService → Candidate indexes → QueryExecutionService`

### Domain types

`Order` is an immutable record.

Its constructor validates identifiers, email addresses, amounts, and required fields.

`IndexDefinition` describes the indexing strategy and validates whether its predicate configuration matches the declared index type.

### Expression policies

The `KeyExpression` interface separates expression definitions from index storage.

Registered expressions include:

- Direct email.
- Lowercase email.
- Uppercase region.
- Amount.
- Order identifier.

This approach allows the index engine to evaluate multiple expressions through a consistent interface.

### Enterprise controls

The implementation provides:

- Index lifecycle states.
- Unique constraint enforcement.
- Predicate implication.
- Index snapshots.
- Transaction-like rollback during failed updates.
- Query eligibility evaluation.
- Workload frequency reporting.
- Domain-specific exceptions.

The Java application models index eligibility and query execution in memory. It does not claim to reproduce PostgreSQL's physical optimizer or transaction manager.

## 13. PostgreSQL Implementation

The SQL implementation provides the actual relational and indexing mechanisms.

It creates a dedicated `indexing_lab` schema containing:

| Table | Purpose |
|---|---|
| `customers` | Customer information |
| `orders` | Transactional order records |
| `user_accounts` | Account lifecycle and uniqueness |
| `index_catalog` | Index metadata |
| `query_workload` | Query frequency and latency information |

### Implemented index definitions

| Index | Type | Purpose |
|---|---|---|
| `idx_orders_status` | Full | General status filtering |
| `idx_orders_open` | Partial | Open-order retrieval |
| `idx_orders_lower_email` | Expression | Case-insensitive email search |
| `idx_orders_upper_region` | Expression | Normalized region search |
| `idx_open_orders_lower_email` | Partial expression | Case-insensitive open-order search |
| `idx_open_high_value` | Partial | High-value open-order retrieval |
| `idx_open_region_created` | Composite partial | Regional open-order retrieval |
| `idx_unique_active_email` | Unique partial expression | Active-account uniqueness |

### Constraints and triggers

The relational schema uses primary keys, foreign keys, check constraints, and a trigger-based validation function.

The unique partial index provides conditional uniqueness without requiring every account to have a globally unique email.

The trigger maintains update timestamps and validates order state.

### Reporting

The SQL script includes:

- Index metadata retrieval.
- Query workload aggregation.
- Index size inspection.
- Index usage statistics.
- Table statistics.
- Predicate eligibility examples.
- Query-plan inspection.
- Transactional validation.
- Conditional uniqueness testing.

## 14. Distinguishing the Four Indexing Strategies

These indexing mechanisms solve different problems.

| Strategy | What determines index membership? | What determines the indexed key? |
|---|---|---|
| Full index | All applicable rows | Column values |
| Partial index | Predicate | Column values |
| Expression index | All applicable rows | Computed expression |
| Partial expression index | Predicate | Computed expression |

A partial index reduces membership.

An expression index changes key representation.

A partial expression index applies both decisions.

A composite index introduces multiple ordered keys and can be combined with a partial predicate.

## 15. Design Considerations

### 15.1 When partial indexes are appropriate

Use a partial index when:

- A query repeatedly accesses a selective subset.
- The predicate is stable and well-defined.
- Excluded rows do not need to participate in the indexed access path.
- The index can substantially reduce storage or maintenance.

Avoid creating partial indexes for conditions that match nearly the entire table unless another benefit justifies them.

### 15.2 When expression indexes are appropriate

Use an expression index when:

- Queries repeatedly apply the same function to a column.
- The expression is compatible with the indexed expression.
- Recomputing the expression across large datasets is expensive.
- The function satisfies the database's immutability requirements.

Avoid indexing expressions that are rarely queried or whose maintenance cost exceeds their retrieval benefit.

### 15.3 When combined indexes are appropriate

A partial expression index is suitable when a frequently queried expression is needed only for a selective subset.

For example:

`lower(customer_email)` restricted to `status = 'OPEN'`.

A partial composite index is appropriate when a workload requires multiple ordered keys while restricting membership to a specific record category.

### 15.4 When an index should be reconsidered

Review indexes when:

- They have very low usage.
- Their storage cost is substantial.
- They duplicate other indexes.
- Their predicates are rarely satisfied.
- Their maintenance cost affects write performance.
- Query patterns have changed.
- Planner statistics are inaccurate.

Index removal should follow workload analysis rather than a single statistics snapshot.

## 16. Limitations and Practical Implications

The Python implementation uses SQLite, while the SQL implementation uses PostgreSQL. Their indexing and query-planning behavior is not identical.

The JavaScript, C++, and Java programs simulate index storage and eligibility. Their estimated plans are educational models, not substitutes for an actual database optimizer.

The SQL script uses a small demonstration dataset. Its execution plans may therefore prefer sequential scans.

Additional production considerations include:

- Data distribution and skew.
- Concurrent transactions.
- Index build duration.
- Write amplification.
- WAL volume.
- Vacuum activity.
- Statistics freshness.
- Collation and locale behavior.
- NULL semantics.
- Prepared statement planning.
- Index bloat.
- Concurrent index creation and removal.

For large production tables, PostgreSQL supports `CREATE INDEX CONCURRENTLY` and `DROP INDEX CONCURRENTLY` under their respective transaction restrictions. These operations have different locking and operational characteristics from ordinary index creation.

## 17. Integrated Conceptual Model

The relationship between records, expressions, predicates, and index entries can be represented as follows:

    Database Table
          |
          v
    Retrieve Candidate Row
          |
          v
    Evaluate Partial Predicate
          |
          +---- FALSE / NULL ----> Exclude from Partial Index
          |
          v
    Evaluate Indexed Expression
          |
          v
    Generate Index Key
          |
          v
    Maintain Index Entry
          |
          v
    Query Planner Evaluates Eligibility
          |
          v
    Compare Estimated Execution Costs
          |
          v
    Select Index Scan or Alternative Plan

The central distinction is that index availability, index eligibility, and index selection are separate decisions.

An index may exist but be ineligible for a query. An eligible index may still be rejected because another execution plan is estimated to be cheaper.

Effective index design therefore requires understanding both the data distribution and the application's actual query workload.
