# PostgreSQL Index Types: B-tree, Hash, GiST, SP-GiST, GIN and BRIN

## 1. Technical Scope

PostgreSQL provides six principal index access methods:

1. B-tree
2. Hash
3. Generalized Search Tree (GiST)
4. Space-Partitioned Generalized Search Tree (SP-GiST)
5. Generalized Inverted Index (GIN)
6. Block Range Index (BRIN)

Each index method organizes information differently and supports different operator classes, comparison operations, data structures and query patterns.

The choice of index affects:

- Query execution time
- Disk consumption
- Memory utilization
- Insert and update performance
- Vacuum and maintenance requirements
- Concurrency
- Database scalability

An index is a separate database structure that helps PostgreSQL locate qualifying table rows. It does not replace the underlying table or automatically guarantee faster execution.

The PostgreSQL query planner determines whether an available index is appropriate for a particular execution plan.

## 2. Understanding Index Fundamentals

A database table normally stores rows in heap storage. Without a suitable index, PostgreSQL may need to examine many or all table pages to find matching records.

An index maintains additional information that helps identify relevant rows.

For example, consider a customer table:

| customer_id | email | city |
|---:|---|---|
| 101 | alice@example.com | Lucknow |
| 102 | bob@example.com | Delhi |
| 103 | carol@example.com | Mumbai |

A query such as:

`SELECT * FROM customers WHERE email = 'alice@example.com';`

can use an appropriate index on `email` to locate the matching tuple without scanning the entire table.

The index stores references to table tuples. PostgreSQL may still need to access the heap to retrieve columns that are not available directly from the index.

### Important terminology

| Term | Meaning |
|---|---|
| Index access method | Algorithm used to organize and search index entries |
| Operator class | Defines supported operators and comparison semantics |
| Operator family | Groups related operator classes |
| Heap | Main table storage |
| Index tuple | Entry stored in an index |
| Selectivity | Fraction of rows expected to match a condition |
| Cardinality | Number of distinct values or possible outcomes, depending on context |
| Correlation | Relationship between logical column order and physical heap order |
| Recheck | Verification of candidate rows against the original condition |
| Index-only scan | Scan that can obtain required values from the index, subject to visibility-map conditions |
| Bitmap index scan | Index scan that constructs a bitmap of matching heap locations |

## 3. Comparison of the Six Index Types

| Property | B-tree | Hash | GiST | SP-GiST | GIN | BRIN |
|---|---|---|---|---|---|---|
| Main structure | Balanced tree | Hash buckets | Generalized search tree | Partitioned search tree | Inverted structure | Block summaries |
| Equality | Yes | Yes | Operator-class dependent | Operator-class dependent | Operator-class dependent | Operator-class dependent |
| Range | Yes | No | Supported by suitable operator classes | Operator-class dependent | Not general-purpose | Supported by suitable operator classes |
| Ordering | Yes | No | Not general-purpose | Not general-purpose | No | No |
| Arrays | Limited | No | Specialized | Specialized | Yes | Specialized |
| JSONB containment | No general support | No | Specialized alternatives | Specialized alternatives | Yes | No general support |
| Full-text search | No general support | No | No general support | No general support | Yes | No general support |
| Spatial operations | Not general-purpose | No | Yes, with suitable operator classes | Yes, with suitable operator classes | Specialized alternatives | No general support |
| Large correlated tables | Possible | Limited | Workload dependent | Workload dependent | Workload dependent | Particularly suitable |

The table describes general capabilities. Actual operator support depends on the data type, operator class and PostgreSQL implementation.

---

## 4. B-tree Index

### Concept

B-tree is PostgreSQL's default index access method.

It maintains keys in an ordered tree structure and supports efficient navigation through key values.

Its primary use cases include:

- Equality comparisons
- Range conditions
- Sorting
- Minimum and maximum operations
- Unique constraints
- Composite indexes
- Prefix matching under suitable collation and operator-class conditions

### Common operators

| Operator | Meaning |
|---|---|
| `=` | Equality |
| `<` | Less than |
| `<=` | Less than or equal |
| `>` | Greater than |
| `>=` | Greater than or equal |
| `BETWEEN` | Range condition |

### Implementation

The Python implementation models B-tree as the general-purpose ordered index.

The JavaScript implementation evaluates its suitability for equality, range, ordering and prefix workloads.

The C++ implementation ranks it using selectivity and ordering requirements.

The Java implementation includes a policy that gives B-tree additional suitability when ordered retrieval is required.

The PostgreSQL implementation creates:

- A unique customer email index through a table constraint.
- A timestamp index on orders.
- An amount index.
- A composite customer and timestamp index.
- A partial index for active customers.

### Composite indexes

Consider:

`CREATE INDEX idx_orders_customer_date ON orders (customer_id, created_at DESC);`

This index is particularly useful for queries that constrain `customer_id` and then retrieve orders by `created_at`.

The leading-column principle is important.

An index on `(customer_id, created_at)` is not generally equivalent to an independent index on `created_at`.

PostgreSQL can sometimes use skip-scan optimizations, depending on the version, statistics and workload, but composite indexes should still be designed around actual query patterns.

### Partial indexes

A partial index stores entries only for rows satisfying a predicate.

For example:

`CREATE INDEX idx_customers_city_active ON customers (city) WHERE active = TRUE;`

This reduces index size when inactive customers form a substantial part of the table.

The query predicate must be compatible with the partial-index predicate for PostgreSQL to use the index.

### Limitations

- Index maintenance adds write overhead.
- Large indexes consume storage.
- Random access can increase I/O.
- A low-selectivity condition may be faster through a sequential scan.
- Composite-column ordering affects usefulness.

---

## 5. Hash Index

### Concept

A Hash index uses a hash function to organize key values into hash-based structures.

It is designed for equality comparisons.

Typical use case:

`SELECT * FROM network_logs WHERE message = 'Connection rejected';`

### Characteristics

- Supports equality lookup.
- Does not support general range scans.
- Does not provide ordered output.
- Cannot enforce uniqueness.
- Does not replace B-tree for general-purpose indexing.

PostgreSQL hash indexes are crash-safe and WAL-logged.

### Implementation

The PostgreSQL script creates:

`CREATE INDEX idx_network_message_hash ON network_logs USING HASH (message);`

The JavaScript and Python models distinguish equality workloads from range and ordering workloads.

The C++ implementation rejects Hash as a candidate for unsupported access patterns.

### Practical decision

Hash is worth evaluating when equality lookup dominates and measurements demonstrate an advantage.

B-tree is generally the more flexible starting point because it supports equality as well as ordering and range operations.

---

## 6. GiST Index

### Concept

GiST stands for Generalized Search Tree.

It is an extensible indexing framework rather than one fixed data structure designed for a single data type.

GiST uses operator classes to define how values are represented, compared, split and searched.

It is useful for data types where ordinary scalar ordering is insufficient.

### Important applications

- Geometric data
- Spatial searches
- Range values
- Overlap detection
- Specialized similarity searches
- Exclusion constraints

### Range operators

| Operator | Meaning |
|---|---|
| `&&` | Overlap |
| `@>` | Contains |
| `<@` | Is contained by |
| `<<` | Strictly left of |
| `>>` | Strictly right of |
| `&<` | Does not extend to the right |
| `&>` | Does not extend to the left |

Operator availability depends on the indexed type and operator class.

### Implementation

The SQL implementation uses a timestamp range:

`CREATE INDEX idx_spatial_location_gist ON spatial_events USING GIST (location);`

A query can locate overlapping intervals:

`WHERE location && tsrange('2025-01-02 09:00', '2025-01-02 12:00', '[)')`

The implementation also demonstrates an exclusion constraint for room reservations.

An exclusion constraint prevents conflicting reservations for the same room when their time ranges overlap.

The constraint uses GiST to enforce a rule that a normal B-tree index cannot directly express.

### Limitations

- Performance depends on the operator class.
- Index behavior depends on data distribution.
- Some searches require rechecking candidate rows.
- It is not a general replacement for B-tree ordering.

---

## 7. SP-GiST Index

### Concept

SP-GiST means Space-Partitioned Generalized Search Tree.

Unlike GiST, which uses generalized search-tree structures, SP-GiST supports partitioning search spaces into smaller, potentially non-overlapping regions.

It is particularly useful for data structures such as:

- Radix trees
- Quadtrees
- k-d trees
- Partitioned spatial representations

### Core distinction

GiST generally supports generalized tree navigation using operator-class-defined summaries and predicates.

SP-GiST partitions the search space according to its operator class.

The two approaches solve related but different indexing problems.

### PostgreSQL implementation

The SQL script creates:

`CREATE INDEX idx_network_client_ip_spgist ON network_logs USING SPGIST (client_ip);`

The `inet` data type has a built-in SP-GiST operator class.

A subnet lookup is demonstrated using:

`WHERE client_ip <<= INET '192.168.1.0/24'`

This is a network containment comparison.

### Applications

- IP address and network prefix searches
- Text prefix operations with suitable operator classes
- Partitioned geometric searches
- Other operator-class-supported partitioning problems

### Limitations

- Operator-class support is essential.
- It does not provide general B-tree ordering.
- It is not automatically faster than GiST.
- Data characteristics determine whether partitioning is effective.

---

## 8. GIN Index

### Concept

GIN stands for Generalized Inverted Index.

It reverses the traditional relationship between indexed values and searchable components.

Instead of treating an entire document or array as one indivisible key, GIN indexes individual components and maps them to matching table rows.

### Example

Consider:

`tags = ARRAY['security', 'database', 'postgresql']`

GIN can maintain entries for individual array elements.

A search for `security` can retrieve rows associated with that component.

### Main applications

- PostgreSQL arrays
- JSONB containment
- Full-text search
- Other composite or component-based data types

### Important JSONB operator classes

| Operator class | Characteristics |
|---|---|
| `jsonb_ops` | General-purpose JSONB GIN indexing |
| `jsonb_path_ops` | More specialized containment-oriented indexing |

The default JSONB GIN operator class is `jsonb_ops`.

`jsonb_path_ops` generally supports fewer operators but can provide a smaller and more efficient index for supported containment workloads.

It does not support every JSONB operator supported by `jsonb_ops`.

### Array indexing

The PostgreSQL implementation creates:

`CREATE INDEX idx_events_tags_gin ON events USING GIN (tags);`

Example:

`WHERE tags @> ARRAY['security']`

### JSONB indexing

The implementation creates:

`CREATE INDEX idx_events_payload_gin ON events USING GIN (payload);`

Example:

`WHERE payload @> '{"department": "engineering"}'::jsonb`

### Full-text indexing

PostgreSQL provides `tsvector` and `tsquery` for full-text search.

The example table creates a stored generated `tsvector` column.

The GIN index is:

`CREATE INDEX idx_documents_search_gin ON documents USING GIN (search_vector);`

A query uses:

`search_vector @@ plainto_tsquery('english', 'database indexing')`

### Write-performance considerations

GIN can require substantial maintenance because one row may contribute multiple index entries.

Important considerations include:

- Pending-list behavior
- `fastupdate`
- Autovacuum
- Bulk loading
- Index build duration
- Update frequency
- Index size

GIN is often a strong choice for read-heavy component searches, but its write costs must be evaluated.

---

## 9. BRIN Index

### Concept

BRIN stands for Block Range Index.

It stores summaries of values across groups of consecutive heap pages rather than storing an individual index entry for every row.

The index identifies page ranges that may contain matching values.

PostgreSQL then examines the relevant heap pages.

BRIN is therefore a lossy index method.

A matching block range does not necessarily mean every row in that range satisfies the query.

### Physical correlation

BRIN is particularly effective when physical row order is correlated with the indexed column.

For example, consider a large event table in which records are inserted chronologically.

Rows with similar timestamps are likely to occupy nearby heap pages.

BRIN can summarize the minimum and maximum timestamp values for each page range.

A date-range query can eliminate page ranges that cannot contain matching records.

### Implementation

The PostgreSQL implementation creates:

`CREATE INDEX idx_events_occurred_brin ON events USING BRIN (occurred_at);`

It also demonstrates:

- `pages_per_range`
- `autosummarize`

### Important configuration

| Parameter | Purpose |
|---|---|
| `pages_per_range` | Number of heap pages represented by each summary |
| `autosummarize` | Requests automatic summarization of suitable ranges |

A smaller `pages_per_range` can improve filtering precision but increases index size.

A larger value reduces index size but can cause more heap pages to be scanned.

### Applications

- Large event tables
- Time-series workloads
- Append-oriented transaction histories
- Naturally ordered telemetry
- Large archival tables

### Limitations

- Poor physical correlation reduces effectiveness.
- Candidate pages must be rechecked.
- Randomly distributed values may produce weak summaries.
- It is not a substitute for a selective B-tree index on small or randomly ordered tables.

---

## 10. Physical Correlation and Selectivity

Two important workload characteristics influence index selection.

### Selectivity

Selectivity describes the fraction of rows expected to match a condition.

For example:

- A query returning 10 rows from 1,000,000 has high selectivity in the database sense of a small matching fraction.
- A query returning 900,000 rows from 1,000,000 has low filtering effectiveness.

A highly selective query often benefits from an appropriate index.

A query matching most of a table may be faster with a sequential scan.

### Physical correlation

Physical correlation measures how closely the logical ordering of a column corresponds to the physical ordering of table rows.

PostgreSQL exposes column statistics through `pg_stats`.

The `correlation` field is particularly relevant to BRIN evaluation.

| Correlation | Interpretation |
|---|---|
| Near +1 | Strong positive physical correlation |
| Near -1 | Strong reverse physical correlation |
| Near 0 | Weak physical correlation |

The absolute magnitude is generally more relevant to BRIN effectiveness than the sign.

A column can have a high absolute correlation while being stored in reverse order.

The Python, JavaScript, C++ and Java implementations include correlation as a workload input.

Their recommendation scores are illustrative, not estimates produced by PostgreSQL.

---

## 11. Repository Structure and Implementation Responsibilities

The six deliverables are independent executable artifacts.

| File | Primary responsibility |
|---|---|
| Python script | Index capability model, workload simulation, recommendation engine and DDL generation |
| JavaScript file | Event-driven workload analysis, registry and asynchronous policy evaluation |
| C++17 program | Efficient index ranking, domain validation and index registry |
| Java 17 program | Enterprise index governance, immutable domain objects and lifecycle management |
| PostgreSQL SQL file | Actual database tables, index access methods, constraints, queries and reporting |
| README.md | Technical reference and explanation of the implementations |

### Python architecture

The Python script contains:

- `IndexType`: Enumerates the six index methods.
- `AccessPattern`: Defines workload categories.
- `IndexCapability`: Stores supported patterns and characteristics.
- `QueryWorkload`: Validates workload input.
- `IndexAdvisor`: Calculates heuristic suitability scores.
- `IndexDefinition`: Represents an index definition.
- `IndexCatalog`: Maintains a registry of index definitions.

The recommendation engine uses dictionaries, enumerations, frozen dataclasses, type annotations and standard-library exceptions.

Its DDL generator validates SQL identifiers and restricts unsafe condition input.

The validation examples demonstrate invalid selectivity, malformed identifiers and unsupported uniqueness configurations.

### JavaScript architecture

The JavaScript implementation uses:

- `Map` for capability and index registries.
- `Set` for supported access patterns.
- `EventEmitter` for event-driven reporting.
- `Promise` and asynchronous functions for workload evaluation.
- Private class fields for registry encapsulation.
- Frozen objects for immutable workload definitions.

The `QueryMonitor` emits an `evaluated` event after each workload has been assessed.

The governance service listens to these events and maintains execution counts.

This separates workload submission from monitoring and reporting.

### C++17 architecture

The C++ implementation uses:

- Enumerations for index methods and workload types.
- Structures for workload and recommendation data.
- Classes for catalog and advisor behavior.
- STL containers for capability storage.
- STL algorithms for ranking recommendations.
- Exceptions for invalid domain data.

The advisor uses `stable_sort` to rank suitable index methods.

The registry uses `std::map` to maintain index definitions and prevent duplicate names.

The implementation avoids third-party dependencies.

### Java 17 architecture

The Java implementation introduces enterprise-oriented separation of responsibilities.

Its main domain types are:

- `IndexCapability`
- `DatabaseWorkload`
- `IndexDefinition`
- `Recommendation`
- `IndexStatus`
- `RiskLevel`

The `WorkloadPolicy` interface separates recommendation policy from assessment services.

`DefaultWorkloadPolicy` implements the scoring rules.

`IndexAssessmentService` evaluates workloads.

`IndexLifecycleService` manages index state transitions.

The lifecycle is:

`PROPOSED → APPROVED → ACTIVE`

An active index can be disabled, and an index can be retired.

Invalid transitions raise a `GovernanceException`.

Java records provide immutable data structures, while synchronized lifecycle operations protect the in-memory registry from concurrent state changes.

---

## 12. PostgreSQL Database Architecture

The SQL implementation uses the `index_lab` schema.

### Entity relationships

The main relationships are:

- `customers` to `orders`: one-to-many.
- `events`: independent JSONB and array workload.
- `documents`: full-text search workload.
- `network_logs`: IP address and equality workloads.
- `spatial_events`: timestamp-range workload.
- `room_reservations`: GiST exclusion-constraint workload.
- `index_maintenance_log`: maintenance audit records.
- `index_maintenance_events`: maintenance event input.

### Database integrity

The schema uses:

- Primary keys
- Foreign keys
- Unique constraints
- Check constraints
- Generated identity columns
- Generated stored columns
- Range-type validation

The reservation table demonstrates a GiST exclusion constraint.

This prevents overlapping reservations for the same room.

### Database functions

`fn_index_eligibility` evaluates a requested workload pattern and reports which index methods are applicable.

It validates:

- Query pattern
- Row count
- Physical correlation
- Update rate

`fn_log_index_maintenance` records maintenance operations.

### Database procedure

`sp_record_index_review` validates an index name and inserts a review event.

The procedure uses the index inventory view to verify that the requested index exists.

### Reporting views

`v_index_inventory` provides:

- Schema name
- Table name
- Index name
- Access method
- Index size
- Index definition
- Uniqueness
- Primary-key status
- Index validity
- Index readiness

`v_index_usage` exposes usage statistics.

The `pg_stat_user_indexes` view supplies index scan and tuple statistics.

These statistics must be interpreted carefully because they are cumulative and can be reset.

---

## 13. Query Planning and Execution

Creating an index does not guarantee its use.

PostgreSQL evaluates available execution strategies using planner statistics and cost estimates.

Important factors include:

- Estimated row counts
- Column statistics
- Selectivity
- Physical correlation
- Heap page count
- Random page cost
- Sequential page cost
- Cache assumptions
- Index size
- Join strategy
- Available memory

### EXPLAIN

`EXPLAIN` displays the planned execution strategy.

### EXPLAIN ANALYZE

`EXPLAIN ANALYZE` executes the query and reports actual execution information.

### BUFFERS

`BUFFERS` reports buffer activity, helping distinguish cache hits, reads and other buffer operations.

The SQL implementation demonstrates:

- Customer equality lookup
- Array containment
- Full-text search
- Range overlap

Small demonstration tables may produce sequential scans even when indexes exist.

This is normal because index traversal and heap access can cost more than scanning a small table.

The correct approach is to examine actual execution plans and representative production workloads.

---

## 14. Index Maintenance and Operational Management

Indexes introduce ongoing operational costs.

### Insert operations

A new row may require corresponding changes to one or more indexes.

GIN can be particularly expensive when a row contributes many indexed components.

### Update operations

Updates to indexed columns may require index maintenance.

An update that changes indexed values generally requires new index entries.

### Delete operations

Deleted rows can leave dead index entries that require cleanup through normal maintenance processes.

### VACUUM and ANALYZE

`VACUUM` helps reclaim reusable space and maintain database health.

`ANALYZE` updates planner statistics.

The SQL implementation explicitly runs `ANALYZE` on the sample tables.

### REINDEX

`REINDEX` rebuilds an index.

Possible reasons include:

- Index corruption recovery
- Index bloat management
- Maintenance after significant changes
- Rebuilding an index with changed storage requirements

Reindexing must be planned according to locking and availability requirements.

`REINDEX CONCURRENTLY` can reduce write-blocking impact where supported, subject to its operational restrictions.

### Concurrent index creation

For production tables that must remain available for writes, `CREATE INDEX CONCURRENTLY` can reduce blocking.

It has additional execution phases and restrictions.

It cannot run inside an ordinary transaction block.

The SQL laboratory uses ordinary transactional index creation for reproducibility.

---

## 15. Index Selection Decision Framework

The following table provides a practical starting point.

| Workload | Preferred candidate | Important consideration |
|---|---|---|
| Customer identifier lookup | B-tree | Equality and uniqueness |
| Date-range filtering | B-tree | Ordered retrieval and selectivity |
| Equality-only comparison | Hash or B-tree | Compare actual execution plans |
| Geometric search | GiST or SP-GiST | Operator-class support |
| Timestamp interval overlap | GiST | Range operators |
| IP network prefix search | SP-GiST or another suitable method | Supported `inet` operator class |
| JSONB containment | GIN | Choose the correct JSONB operator class |
| Array membership | GIN | Component-based lookup |
| Full-text search | GIN | `tsvector` and `tsquery` |
| Large chronological event table | BRIN | Physical correlation |
| Large randomly ordered table | B-tree or another suitable method | BRIN may become ineffective |

This is an initial selection framework, not a universal ranking.

A final choice should consider actual query frequency, table size, write volume, storage cost and execution plans.

---

## 16. Performance and Complexity Considerations

The six index methods have different structural costs.

| Index type | Main performance consideration |
|---|---|
| B-tree | Tree navigation, page access and maintenance |
| Hash | Equality lookup and bucket management |
| GiST | Operator-class-specific tree navigation |
| SP-GiST | Partitioning efficiency and search-space structure |
| GIN | Component extraction, posting lists and write amplification |
| BRIN | Summary size, page-range precision and heap rechecks |

The Python, JavaScript, C++ and Java recommendation systems use a bounded scoring model.

Their scores are intended to compare workload characteristics rather than reproduce PostgreSQL's internal cost model.

For example:

- B-tree receives a benefit for ordered retrieval.
- GIN receives a benefit for component-based lookups.
- GIN receives a maintenance penalty for frequent updates.
- BRIN receives a benefit for large tables with high physical correlation.
- BRIN receives a penalty when physical correlation is weak.

The SQL implementation provides actual PostgreSQL index definitions and query-plan inspection.

---

## 17. Security and Reliability Considerations

Index administration is a database privilege and availability concern.

Important controls include:

- Restricting index creation and removal privileges.
- Validating identifiers before constructing DDL.
- Avoiding unrestricted dynamic SQL.
- Reviewing storage consumption.
- Monitoring index validity.
- Monitoring failed concurrent builds.
- Planning reindex operations.
- Maintaining database backups.
- Reviewing extension requirements.
- Testing operator-class compatibility.
- Measuring production workloads before changing indexes.

The source implementations validate SQL identifiers rather than accepting arbitrary identifier strings.

The SQL implementation relies on PostgreSQL constraints and database-native operations.

Its eligibility function rejects unsupported workload patterns and invalid numeric inputs.

The sample scripts are educational environments, not substitutes for production access-control policies or operational change management.

---

## 18. Limitations of the Implementations

The Python, JavaScript, C++ and Java programs are workload simulators.

They do not connect to a live PostgreSQL server or inspect real index statistics.

Their recommendation scores are deterministic teaching heuristics.

They do not model:

- PostgreSQL planner cost formulas
- Buffer cache residency
- Actual index page splits
- WAL volume
- Concurrent transactions
- Real heap visibility
- Dead tuples
- Vacuum activity
- Parallel execution
- Actual disk latency
- Real operator-class selectivity
- Database-specific configuration

The PostgreSQL script performs actual database operations and exposes PostgreSQL's catalog and statistics views.

The small sample datasets are not sufficient for reliable benchmarking.

For meaningful BRIN evaluation, a much larger table with representative physical ordering is required.

The same principle applies to other index types: representative data distributions and realistic concurrent workloads are necessary for performance conclusions.

---

## 19. Execution and Validation

### Python

Requirements:

- Python 3.10 or later.
- Standard library only.

Execute the Python file directly.

It performs workload evaluation, DDL generation, validation tests and an in-memory catalog benchmark.

### JavaScript

Requirements:

- Node.js 18 or later.
- Standard library only.

Execute the JavaScript file with Node.js.

The program evaluates workloads asynchronously and prints event-driven reports.

### C++17

Requirements:

- C++17-compatible compiler.

Compilation should enable the C++17 standard.

The program performs workload ranking, SQL identifier validation, registry management and assertions.

### Java 17

Requirements:

- JDK 17.

Compile the source as `PostgreSQLIndexGovernance.java` and execute its public class.

The program evaluates workloads and demonstrates index lifecycle transitions.

### PostgreSQL

Requirements:

- PostgreSQL 14 or later recommended.
- Permission to create schemas, tables, indexes, functions and procedures.

Execute the SQL file using `psql`.

The script drops and recreates the `index_lab` schema, so it must not be executed against an existing schema containing data that must be retained.

The script includes:

- DDL
- Sample DML
- Six index access methods
- Query examples
- Reporting views
- A trigger
- A stored procedure
- An eligibility function
- CTE-based reporting
- Execution-plan inspection
- Maintenance operations
- Transaction and savepoint demonstrations

### Validation checklist

- [ ] All six index methods are represented.
- [ ] Equality and range behavior are distinguished.
- [ ] B-tree ordering is demonstrated.
- [ ] Hash equality behavior is demonstrated.
- [ ] GiST range overlap is demonstrated.
- [ ] SP-GiST IP network lookup is demonstrated.
- [ ] GIN JSONB containment is demonstrated.
- [ ] GIN array membership is demonstrated.
- [ ] GIN full-text search is demonstrated.
- [ ] BRIN physical-correlation considerations are represented.
- [ ] Composite and partial B-tree indexes are demonstrated.
- [ ] Exclusion constraints are implemented.
- [ ] Index inventory and usage reporting are implemented.
- [ ] Query plans are inspected.
- [ ] Validation and maintenance operations are demonstrated.
- [ ] All four programming-language implementations execute their validation tests.

## 20. Core Technical Distinctions

The six PostgreSQL index methods are complementary structures rather than interchangeable alternatives.

Their central differences can be expressed as follows:

- **B-tree:** Organizes keys in ordered search structures.
- **Hash:** Organizes keys for equality-based lookup.
- **GiST:** Provides an extensible generalized search-tree framework.
- **SP-GiST:** Partitions search spaces into smaller structures.
- **GIN:** Maps individual components to matching records.
- **BRIN:** Summarizes values across physical ranges of table pages.

A sound indexing strategy begins with the operators used by the application, the structure and distribution of the underlying data, the frequency of reads and writes, and the actual execution plans produced by PostgreSQL.
