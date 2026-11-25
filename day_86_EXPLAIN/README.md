# SQL EXPLAIN: Execution Plans, Cost Estimates, and Scan Types

## 1. Technical Scope

SQL query execution involves more than interpreting the SQL statement. A database management system must determine how to retrieve records, access indexes, combine relations, evaluate predicates, sort results and produce the final output.

PostgreSQL uses a cost-based query optimizer to evaluate alternative execution strategies and select a plan according to estimated resource requirements.

`EXPLAIN` exposes the selected execution plan. It provides information about the operations PostgreSQL intends to perform, their estimated costs and expected row counts.

`EXPLAIN ANALYZE` executes the statement and reports observed execution information alongside the estimates.

This project implements execution-plan inspection through five complementary perspectives:

| Implementation | Technical perspective |
|---|---|
| Python | SQL plan inspection, SQLite execution-plan comparison and illustrative cost modeling |
| JavaScript | PostgreSQL JSON execution-plan analysis and event-driven diagnostics |
| C++17 | Cost-based scan and join selection engine |
| Java 17 | Enterprise execution-plan analysis and performance policies |
| PostgreSQL | Relational workload, indexing, statistics and actual execution-plan inspection |

The examples use employee and department data to demonstrate realistic database access patterns.

## 2. Understanding SQL EXPLAIN

### 2.1 Execution plans

An execution plan is a tree of operations describing how a database executes a query.

A typical plan can contain:

- Scan operations for retrieving table records.
- Index operations for locating matching records.
- Join operations for combining relations.
- Sort operations for ordering records.
- Aggregate operations for calculating grouped results.
- Filter operations for applying predicates.
- Materialization and other intermediate processing operations.

Each node represents an operation. Child nodes provide input to their parent nodes.

A simplified execution tree:

    Hash Join
    |
    +-- Sequential Scan: departments
    |
    +-- Bitmap Heap Scan: employees
        |
        +-- Bitmap Index Scan: department_index

The execution tree describes the database's chosen processing strategy, not the textual order of SQL clauses.

### 2.2 EXPLAIN versus EXPLAIN ANALYZE

| Property | EXPLAIN | EXPLAIN ANALYZE |
|---|---|---|
| Produces an execution plan | Yes | Yes |
| Executes the query | No | Yes |
| Reports estimated rows | Yes | Yes |
| Reports estimated costs | Yes | Yes |
| Reports actual rows | No | Yes |
| Reports actual execution time | No | Yes |
| Reports actual buffer activity when requested | No | Yes |

`EXPLAIN` is useful when inspecting the optimizer's decisions without executing the query.

`EXPLAIN ANALYZE` is necessary when investigating actual runtime behavior, cardinality-estimation errors and execution overhead.

An important operational distinction is that `EXPLAIN ANALYZE` executes the statement being inspected. An analyzed `UPDATE` or `DELETE` can modify data. Production investigations must account for transaction boundaries and external side effects.

## 3. Execution Costs and Estimates

### 3.1 Startup cost

Startup cost represents the estimated work required before a plan node can begin returning its first row.

This is particularly relevant to:

- Sorting.
- Hash-table construction.
- Materialization.
- Operations requiring substantial initial processing.

A plan with a comparatively low startup cost may be advantageous when a query retrieves only a small number of rows.

### 3.2 Total cost

Total cost represents the optimizer's estimated resource expenditure for completing the operation.

PostgreSQL displays costs in the form:

`cost=startup_cost..total_cost`

For example:

`cost=10.00..250.00`

The values are planner cost units, not milliseconds.

PostgreSQL considers configurable parameters such as:

- `seq_page_cost`
- `random_page_cost`
- `cpu_tuple_cost`
- `cpu_index_tuple_cost`
- `cpu_operator_cost`
- `effective_cache_size`

These parameters influence the relative attractiveness of execution strategies.

Changing cost parameters indiscriminately can produce worse plans. They should reflect the actual database environment and workload.

### 3.3 Estimated rows

The estimated row count indicates how many records the optimizer expects an operation to produce.

This estimate influences:

- Scan selection.
- Join algorithm selection.
- Join ordering.
- Sorting strategy.
- Memory requirements.
- Aggregation strategy.

Incorrect cardinality estimates can propagate through the execution tree and lead to poor downstream decisions.

### 3.4 Plan width

Plan width estimates the average size, in bytes, of records produced by an operation.

It influences memory and data-processing estimates, especially for sorting, hashing and intermediate results.

### 3.5 Actual execution time

`EXPLAIN ANALYZE` provides actual execution measurements.

Important fields include:

- Actual Startup Time.
- Actual Total Time.
- Actual Rows.
- Actual Loops.

Execution time is affected by caching, concurrent workloads, storage performance, system load and other environmental conditions.

Repeated measurements are preferable to conclusions based on a single execution.

## 4. Cardinality and Selectivity

Cardinality describes the number of records in a relation or intermediate result.

Selectivity describes the proportion of records expected to satisfy a predicate.

The basic estimation relationship is:

\[
\text{Estimated Rows}
=
\text{Total Rows}
\times
\text{Selectivity}
\]

For a table containing 100,000 records, a predicate with an estimated selectivity of 0.01 produces:

\[
100000 \times 0.01 = 1000
\]

The optimizer estimates approximately 1,000 qualifying records.

This estimation is important because a query returning ten records may benefit from index access, while a query returning most of a table may benefit from sequential access.

Actual selectivity depends on data distribution and predicate characteristics.

PostgreSQL maintains statistics through `ANALYZE` and automatic statistics collection.

Relevant statistical information includes:

- Estimated distinct values.
- Null fractions.
- Most common values.
- Most common value frequencies.
- Histograms.
- Extended statistics for relationships between columns.

Correlated predicates are particularly important.

For example, employee location and employment status may not be independent. Treating them as independent can produce inaccurate estimates.

PostgreSQL extended statistics can help with certain dependency and most-common-value relationships.

## 5. Scan Types

Scan selection is a central part of query optimization.

### 5.1 Sequential Scan

A sequential scan reads a relation through its table storage.

It is useful when:

- A large proportion of the relation must be retrieved.
- The relation is relatively small.
- Index access would cause excessive random I/O.
- No useful index exists.
- The query requires substantial portions of the table.

Advantages:

- Straightforward access pattern.
- Efficient for broad retrieval.
- Avoids individual index lookups.

Limitations:

- Can read many irrelevant records for highly selective queries.
- May consume substantial I/O on large relations.

A sequential scan is not automatically a bad execution plan.

### 5.2 Index Scan

An index scan uses an index to identify matching table records.

For example, an index on `department_id` can support:

`WHERE department_id = 2`

The index identifies matching tuple locations, after which PostgreSQL may retrieve the corresponding table records.

Advantages:

- Effective for selective predicates.
- Can avoid scanning unrelated records.
- Useful for indexed joins and range conditions.

Limitations:

- May require numerous random heap accesses.
- Performance depends on index selectivity and physical data distribution.
- Index maintenance introduces additional write overhead.

### 5.3 Index Only Scan

An index-only scan retrieves the required columns from an index without requiring ordinary heap access for every qualifying tuple.

It is most effective when:

- The index contains all required columns.
- The visibility map establishes that heap visibility checks can be avoided.

PostgreSQL may still perform heap fetches when visibility information is insufficient.

The `Heap Fetches` field is therefore important when assessing an index-only plan.

The PostgreSQL implementation demonstrates covering indexes with `INCLUDE` columns and visibility-map considerations.

### 5.4 Bitmap Index Scan

A bitmap index scan collects tuple locations matching an index condition into a bitmap.

It can combine results from multiple indexes using bitmap operations.

Relevant operations include:

- `Bitmap Index Scan`
- `BitmapAnd`
- `BitmapOr`

The bitmap is subsequently used by a bitmap heap scan.

### 5.5 Bitmap Heap Scan

A bitmap heap scan accesses table pages identified through the bitmap.

It groups matching tuple locations to reduce repeated heap-page access.

It can be beneficial when a query retrieves more rows than would be efficient through individual index lookups, but fewer rows than would justify scanning the entire relation.

Bitmap scans involve additional memory and processing overhead.

When bitmap memory is insufficient, PostgreSQL may use lossy bitmap pages, requiring additional tuple rechecks.

### 5.6 Scan comparison

| Scan type | Access method | Typical use |
|---|---|---|
| Sequential Scan | Reads table storage | Broad retrieval |
| Index Scan | Index followed by heap access | Selective predicates |
| Index Only Scan | Index provides required data | Covering queries |
| Bitmap Index Scan | Builds tuple-location bitmap | Indexed filtering |
| Bitmap Heap Scan | Reads identified heap pages | Intermediate selectivity |

These are different physical access strategies. Their performance depends on the workload, data distribution, available indexes and storage characteristics.

## 6. Join Execution Strategies

Join algorithms determine how PostgreSQL combines records from multiple relations.

### 6.1 Nested Loop Join

A nested loop processes rows from an outer relation and searches for matching rows in an inner relation.

Conceptually:

    For each outer row:
        Find matching inner rows
        Produce joined records

It is often effective when:

- The outer relation is small.
- The inner relation has a suitable index.
- The join produces a limited number of matches.

It can become expensive when both relations are large or the inner operation executes repeatedly.

The `Actual Loops` field helps identify repeated execution.

### 6.2 Hash Join

A hash join builds a hash table from one input and probes it using the other input.

It is frequently useful for equality joins involving substantial input relations.

Advantages:

- Efficient equality matching.
- Avoids repeatedly searching the inner relation.
- Often effective for larger joins.

Limitations:

- Requires memory for hash structures.
- Can involve temporary disk I/O when memory is insufficient.
- Depends on cardinality and memory estimates.

### 6.3 Merge Join

A merge join combines inputs ordered by their join keys.

Both inputs must provide suitable ordering, either through existing access paths or sorting.

Advantages:

- Efficient for appropriately ordered inputs.
- Useful for large compatible relations.
- Can support ordered processing.

Limitations:

- Sorting may be expensive.
- Performance depends on available ordering and input sizes.

### 6.4 Join comparison

| Algorithm | Main mechanism | Important consideration |
|---|---|---|
| Nested Loop | Repeated inner lookup | Number of loops |
| Hash Join | Hash construction and probing | Memory consumption |
| Merge Join | Ordered input traversal | Sorting and ordering |

PostgreSQL selects among available strategies using estimated costs. A particular join algorithm is not universally superior.

## 7. Sorting and Aggregation

Execution plans also contain processing operations beyond scans and joins.

### Sort

A sort operation orders records according to specified expressions.

It can be implemented using memory or temporary disk files, depending on workload size and available memory.

Important diagnostic fields include:

- Sort Method.
- Sort Space Used.
- Sort Space Type.

Temporary disk activity can indicate that a sort exceeded available working memory.

### Aggregation

Aggregation calculates results such as:

- `COUNT`
- `SUM`
- `AVG`
- `MIN`
- `MAX`

PostgreSQL can use different aggregation strategies, including hash aggregation and sorted aggregation.

Hash aggregation depends on memory availability. Sorted aggregation depends on appropriately ordered input.

## 8. Understanding EXPLAIN Output

A PostgreSQL execution-plan node commonly contains:

| Field | Meaning |
|---|---|
| Node Type | Execution operation |
| Startup Cost | Estimated initial cost |
| Total Cost | Estimated completion cost |
| Plan Rows | Estimated output cardinality |
| Plan Width | Estimated output row width |
| Actual Startup Time | Observed initial execution time |
| Actual Total Time | Observed completion time |
| Actual Rows | Observed output cardinality |
| Actual Loops | Number of node executions |
| Shared Hit Blocks | Shared-buffer blocks found in cache |
| Shared Read Blocks | Shared-buffer blocks read into cache |
| Temp Read Blocks | Temporary blocks read |
| Temp Written Blocks | Temporary blocks written |

Costs and times should not be interpreted interchangeably.

For nodes executed multiple times, actual row counts and execution measurements must be considered together with loop counts.

Buffer counters can also accumulate across repeated node execution. Parent and child node buffer figures should not be blindly summed when interpreting total physical I/O.

## 9. PostgreSQL Implementation

The PostgreSQL script creates the `explain_lab` schema.

### Relational model

    explain_lab
        |
        +-- departments
        |      |
        |      +-- department_id
        |      +-- department_name
        |      +-- location
        |      +-- annual_budget
        |
        +-- employees
        |      |
        |      +-- employee_id
        |      +-- department_id
        |      +-- salary
        |      +-- city
        |      +-- employment_status
        |
        +-- employee_transactions
               |
               +-- transaction_id
               +-- employee_id
               +-- transaction_type
               +-- transaction_amount

The employee table contains 100,000 generated records, distributed across five departments.

### Index implementation

The SQL file implements:

- Single-column B-tree indexes.
- Composite indexes.
- Covering indexes using `INCLUDE`.
- Partial indexes.
- Foreign-key access indexes.

The composite index on `(department_id, salary)` demonstrates how leading-column order affects multicolumn B-tree access.

The partial index on active employees demonstrates an index restricted to a defined subset of records.

Index design must account for query frequency, predicate selectivity, write overhead, storage requirements and maintenance costs.

### Statistics collection

`ANALYZE` collects table statistics used by the optimizer.

`pg_stats` provides access to collected column statistics.

`CREATE STATISTICS` demonstrates extended statistics for correlated columns.

The implementation also inspects relation-level counters through `pg_stat_user_tables`.

These monitoring counters represent accumulated activity and are not substitutes for an individual execution plan.

### JSON execution plans

The PostgreSQL script uses:

`EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS, FORMAT JSON)`

JSON output provides structured information suitable for application-level processing.

The JavaScript implementation consumes this structure and produces a diagnostic report.

## 10. Python Implementation

The Python script uses the standard-library `sqlite3` module.

It creates an in-memory relational database and demonstrates:

- Table creation.
- Data generation.
- Index creation and removal.
- Query-plan inspection.
- Query execution timing.
- Result cardinality.
- Scan classification.
- Cost estimation.
- JSON report generation.

SQLite's `EXPLAIN QUERY PLAN` provides a description of its query strategy. It does not expose PostgreSQL's numeric startup and total cost model.

The Python cost model is therefore explicitly illustrative rather than an implementation of PostgreSQL's optimizer.

The distinction prevents SQLite plan output from being incorrectly interpreted as PostgreSQL execution-plan output.

## 11. JavaScript Implementation

The JavaScript implementation is a PostgreSQL JSON plan analyzer.

It uses Node.js standard-library capabilities, including:

- `Map` for scan-frequency aggregation.
- `EventEmitter` for event-driven monitoring.
- Promises and asynchronous file operations.
- Structured objects for plan representation.
- Recursive traversal for plan-tree analysis.

The analyzer processes:

1. Root plan identification.
2. Recursive node discovery.
3. Scan-type classification.
4. Join algorithm identification.
5. Estimated versus actual cardinality comparison.
6. Buffer usage aggregation.
7. Diagnostic generation.
8. JSON report export.

It also detects substantial cardinality-estimation errors and temporary disk writes.

The implementation expects PostgreSQL JSON output rather than SQLite's textual execution-plan format.

## 12. C++17 Implementation

The C++ implementation models a simplified cost-based query planner.

It uses explicit domain structures:

- `TableStatistics`
- `CostParameters`
- `ExecutionEstimate`
- `JoinEstimate`

The `QueryPlanner` calculates estimated costs for alternative scan and join strategies.

The `chooseScan` operation evaluates candidate scan types and selects the one with the lowest modeled total cost.

The model includes sequential page access, random page access, CPU tuple processing and index-entry processing.

It also models nested loop, hash and merge join costs.

This is an educational cost model. It is not PostgreSQL's internal planner implementation and does not reproduce PostgreSQL's complete cost formulas, statistics machinery or physical storage behavior.

The implementation makes the trade-off between selectivity, relation size and access cost explicit.

## 13. Java 17 Implementation

The Java implementation provides an enterprise-oriented plan analysis architecture.

Its domain model uses immutable records for:

- Cost.
- Cardinality.
- Buffer usage.
- Plan nodes.
- Diagnostics.
- Plan reports.

`PlanPolicy` separates performance rules from plan traversal.

`EnterprisePlanPolicy` evaluates configurable thresholds for:

- Cardinality-estimation errors.
- Large sequential scans.
- Excessive nested-loop iterations.
- Temporary disk writes.
- Missing index metadata.

`PlanAnalyzer` recursively processes the execution tree and aggregates scan counts, join counts and buffer information.

`CostEstimator` independently evaluates alternative scan strategies.

This separation allows performance policies to evolve without changing the plan-node domain model.

## 14. Interpreting Estimated Versus Actual Rows

Cardinality-estimation accuracy is one of the most important execution-plan diagnostic areas.

Consider:

| Metric | Value |
|---|---:|
| Estimated rows | 100 |
| Actual rows | 10,000 |
| Difference | 9,900 |
| Actual-to-estimated ratio | 100 |

Such a discrepancy can influence join selection, memory allocation and access strategy.

Possible causes include:

- Stale statistics.
- Data skew.
- Correlated predicates.
- Unusual value distributions.
- Insufficient statistics detail.
- Parameter-sensitive workloads.

The appropriate response is to investigate the underlying data distribution and query conditions rather than automatically create another index.

## 15. Practical Query-Optimization Workflow

A structured investigation should follow this sequence:

    Identify slow SQL statement
             |
             v
    Capture EXPLAIN output
             |
             v
    Capture EXPLAIN ANALYZE
             |
             v
    Inspect execution-tree structure
             |
             v
    Compare estimated and actual rows
             |
             v
    Inspect scan and join strategies
             |
             v
    Examine buffer and temporary I/O
             |
             v
    Review statistics and indexes
             |
             v
    Test an optimization
             |
             v
    Compare execution plans and timings
             |
             v
    Validate correctness and workload impact

Optimization should preserve query results and application behavior.

A reduction in estimated cost does not necessarily guarantee improved real-world performance.

## 16. Performance and Security Considerations

### Performance

- Avoid indexing every column.
- Consider the selectivity of predicates.
- Review composite-index column ordering.
- Monitor index maintenance overhead.
- Keep planner statistics sufficiently current.
- Investigate inaccurate row estimates.
- Examine temporary disk operations.
- Consider cache state when comparing timings.
- Test representative parameter values.
- Measure concurrent workload effects.

### Security

Execution-plan output can expose:

- Table and index names.
- Schema structure.
- Query predicates.
- Application data relationships.
- Potentially sensitive query constants.

Production plan reports should be protected by appropriate access controls.

Avoid logging sensitive SQL parameters unnecessarily.

Use restricted database permissions when collecting diagnostic information.

`EXPLAIN ANALYZE` should be used carefully for statements that modify data or invoke functions with external side effects.

## 17. Limitations and Design Boundaries

The five implementations serve different purposes.

| Component | Important limitation |
|---|---|
| Python | SQLite does not reproduce PostgreSQL cost estimates |
| JavaScript | Analyzes supplied PostgreSQL JSON plans; does not execute SQL |
| C++17 | Uses simplified illustrative cost formulas |
| Java 17 | Analyzes modeled plan objects rather than connecting to PostgreSQL |
| PostgreSQL | Produces genuine optimizer plans for its own database environment |

The cost models are intended to explain the relationship between table statistics, selectivity and access strategies.

They should not be used as replacements for PostgreSQL's production optimizer or as substitutes for measurements on the target database.

The PostgreSQL execution-plan output remains the authoritative evidence for how PostgreSQL executes the demonstrated SQL workload.
