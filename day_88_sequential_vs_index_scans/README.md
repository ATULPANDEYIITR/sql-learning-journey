# Sequential Scan vs Index Scan vs Bitmap Scan in PostgreSQL

## 1. Introduction

PostgreSQL uses a cost-based query planner to determine how database records should be accessed. Three important heap-table access strategies are:

- Sequential Scan (`Seq Scan`)
- Index Scan (`Index Scan`)
- Bitmap Heap Scan (`Bitmap Heap Scan`)

These strategies determine how PostgreSQL locates qualifying records and retrieves their corresponding table data.

The selection depends on estimated query cost, table size, index availability, data distribution, predicate selectivity, page access patterns, and database statistics.

An index does not guarantee that PostgreSQL will use it. A sequential scan can be the optimal strategy even when appropriate indexes exist.

The implementations in this project demonstrate these mechanisms through executable simulations in Python, JavaScript, C++17, and Java 17, supported by a PostgreSQL relational database experiment.

## 2. Fundamental Database Concepts

### 2.1 Heap table

A PostgreSQL table stores records in physical storage pages. PostgreSQL commonly refers to the table's underlying storage as its heap.

A heap tuple contains the record's values and associated tuple metadata.

A query that retrieves records must identify qualifying tuples and ensure that they are visible under the transaction's snapshot.

The heap and an index serve different purposes:

| Component | Responsibility |
|---|---|
| Heap | Stores actual table records |
| Index | Provides an alternative way to locate tuples |
| Query planner | Estimates and selects an execution plan |
| Executor | Performs the operations described by the plan |
| Statistics | Help estimate row counts and predicate selectivity |
| Buffer manager | Manages database pages in memory |

An index generally stores search keys and tuple identifiers rather than a complete copy of every table record.

### 2.2 Database pages

PostgreSQL normally uses 8 KB database pages in standard builds.

A table consists of multiple heap pages. A sequential scan reads relevant pages in physical storage order.

An index scan may access heap pages in a less predictable order because index entries identify tuples distributed across the table.

A bitmap heap scan groups tuple identifiers by heap page to reduce repeated random page access.

The number of qualifying records and the number of heap pages containing those records are different measurements.

A query returning 1,000 records might require fewer than 1,000 heap-page accesses because several records can occupy the same page.

### 2.3 Tuple identifiers

PostgreSQL uses tuple identifiers, commonly called TIDs, to identify physical tuple locations.

A TID contains:

- Block number
- Offset number within the block

An index entry can identify a heap tuple using its TID.

Bitmap-based execution uses these locations to construct candidate sets of tuples and organize heap-page access.

## 3. Sequential Scan

<AsyncImage query="PostgreSQL sequential scan database heap pages sequential reading technical diagram" aspectRatio="16:9" width="100%" />

### 3.1 Definition

A Sequential Scan reads the table's heap pages and examines visible tuples to determine whether they satisfy the query's filtering conditions.

It does not require a secondary index to locate records.

Example:

    SELECT *
    FROM employees
    WHERE salary > 100000;

If the salary column does not have a suitable index, a sequential scan is a natural execution strategy.

PostgreSQL reads table pages and evaluates the salary condition against qualifying visible tuples.

### 3.2 Execution mechanism

The general workflow is:

    Query
      |
      v
    Sequential Scan
      |
      v
    Read heap pages
      |
      v
    Examine visible tuples
      |
      v
    Evaluate WHERE conditions
      |
      v
    Return qualifying records

The executor processes the table's pages without first locating individual records through a secondary index.

### 3.3 Cost characteristics

A simplified sequential scan cost is:

\[
C_{seq}=P \times C_{seqpage}+N \times C_{tuple}
\]

Where:

- \(P\) represents the number of heap pages.
- \(N\) represents the number of tuples.
- \(C_{seqpage}\) represents sequential page-access cost.
- \(C_{tuple}\) represents tuple-processing cost.

PostgreSQL's actual cost model also accounts for parallel execution, caching, visibility checks, tuple width, and other execution characteristics.

### 3.4 When sequential scans are useful

- The query retrieves a large percentage of table records.
- The table is relatively small.
- No useful index exists.
- An index would require extensive random heap access.
- The query needs most columns and most records.
- Sequential page access is cheaper than repeated indexed lookups.

### 3.5 Limitations

A sequential scan may perform unnecessary tuple processing when a query needs only a small number of highly selective records.

For a very large table with a selective predicate and a suitable index, another access strategy may be cheaper.

## 4. Index Scan

<AsyncImage query="PostgreSQL B-tree index scan root internal leaf pages heap tuple lookup database diagram" aspectRatio="16:9" width="100%" />

### 4.1 Definition

An Index Scan uses an index to locate candidate tuple identifiers and then accesses the corresponding heap records.

PostgreSQL supports multiple index access methods. B-tree is a commonly used method for equality, range, and ordered retrieval.

Example:

    CREATE INDEX idx_employees_salary
    ON employees(salary);

    SELECT *
    FROM employees
    WHERE salary = 250000;

The planner can consider the salary index when evaluating this query.

### 4.2 B-tree mechanism

A B-tree index organizes search keys into a hierarchical structure.

Its general structure is:

    Root Page
        |
        v
    Internal Pages
        |
        v
    Leaf Pages
        |
        v
    Matching TIDs
        |
        v
    Heap Tuple Retrieval

The tree structure reduces the number of index pages that need to be examined when locating matching keys.

A typical lookup has logarithmic search complexity with respect to the number of index entries, although actual performance also depends on caching, page layout, and the number of matching records.

### 4.3 Index scan execution

The general workflow is:

1. Identify a suitable index.
2. Navigate the index structure.
3. Locate matching index entries.
4. Retrieve associated tuple identifiers.
5. Access the relevant heap tuples.
6. Check tuple visibility and remaining predicates.
7. Return qualifying records.

### 4.4 Cost characteristics

A simplified index scan cost is:

\[
C_{index}=C_{traversal}+R \times C_{heap}
\]

Where:

- \(C_{traversal}\) is the index traversal cost.
- \(R\) is the number of matching index entries.
- \(C_{heap}\) represents the cost of accessing corresponding heap tuples.

An important consideration is that heap-page accesses may be random rather than sequential.

If matching records are scattered across many pages, index access can become expensive.

### 4.5 Selectivity

Selectivity describes the fraction of records satisfying a predicate.

\[
S=\frac{\text{Matching Rows}}{\text{Total Rows}}
\]

For example, if a table contains 100,000 employees and a condition returns 100 records:

\[
S=\frac{100}{100000}=0.001
\]

The selectivity is 0.1%.

A highly selective condition often makes an index scan attractive.

A condition returning 80% of the table may favor a sequential scan, depending on physical data distribution and other costs.

### 4.6 Index-only scans

An Index Only Scan is different from an ordinary Index Scan.

It can obtain the requested column values from the index without retrieving every corresponding heap tuple.

Two important conditions are:

- The index contains all required columns.
- PostgreSQL can establish tuple visibility using the visibility map without requiring heap visibility checks for those pages.

Example:

    CREATE INDEX idx_employee_covering
    ON employees(department_id, salary)
    INCLUDE (employee_name);

    SELECT department_id, salary, employee_name
    FROM employees
    WHERE department_id = 1;

The `INCLUDE` clause stores additional non-key columns in the index.

This can support an index-only execution strategy.

## 5. Bitmap Scan

<AsyncImage query="PostgreSQL bitmap index scan bitmap AND bitmap heap scan heap blocks technical architecture diagram" aspectRatio="16:9" width="100%" />

### 5.1 Definition

A Bitmap Heap Scan uses one or more indexes to identify candidate tuple locations and then accesses the corresponding heap pages.

It is particularly useful when a query matches more records than a typical highly selective index lookup but still benefits from avoiding a complete table scan.

Bitmap execution separates index-based candidate identification from heap-page retrieval.

### 5.2 Bitmap Index Scan

A Bitmap Index Scan obtains tuple-location information from an index.

For example:

    SELECT *
    FROM employees
    WHERE department_id = 1;

An index on `department_id` can generate a bitmap containing candidate tuple locations.

### 5.3 Bitmap AND

When multiple indexed predicates are present, PostgreSQL can combine their candidate bitmaps using Bitmap AND.

Example:

    SELECT *
    FROM employees
    WHERE department_id = 1
      AND location_id = 1;

Suppose:

- The department index identifies 20,000 candidate tuples.
- The location index identifies 25,000 candidate tuples.
- Their intersection contains 5,000 candidates.

The bitmap intersection eliminates tuples that cannot satisfy both indexed conditions.

Conceptually:

    Department Bitmap
           |
           v
       Bitmap AND
           ^
           |
       Location Bitmap
           |
           v
      Candidate TIDs
           |
           v
      Bitmap Heap Scan

The executor still evaluates the complete query conditions against candidate tuples.

### 5.4 Bitmap OR

Bitmap OR combines candidate tuple locations from multiple indexes.

Example:

    SELECT *
    FROM employees
    WHERE department_id = 1
       OR location_id = 2;

The resulting candidate set contains tuple locations identified by either index.

### 5.5 Bitmap Heap Scan

After candidate tuple locations are generated, the Bitmap Heap Scan accesses the relevant heap pages.

Its principal advantages include:

- Grouping tuple locations by heap page.
- Reducing repeated random page accesses.
- Supporting combined index conditions.
- Improving access when multiple matching records are distributed across the table.

### 5.6 Lossy and exact bitmaps

PostgreSQL may represent bitmap information using exact tuple locations or lossy page-level information.

An exact bitmap identifies individual candidate tuple locations.

A lossy bitmap identifies pages that may contain qualifying tuples without retaining every individual tuple location.

When a bitmap becomes lossy, PostgreSQL must recheck conditions against tuples on the relevant pages.

This can increase the number of tuples examined.

The `EXPLAIN ANALYZE` output can report information such as:

- Exact Heap Blocks
- Lossy Heap Blocks
- Rows Removed by Index Recheck

Bitmap memory availability therefore influences execution behavior.

## 6. Comparison of the Three Scan Strategies

| Property | Sequential Scan | Index Scan | Bitmap Scan |
|---|---|---|---|
| Main access path | Heap pages | Index followed by heap | Index bitmap followed by heap |
| Index required | No | Yes | Yes |
| Heap access pattern | Generally sequential | Potentially random | Grouped by page |
| Typical use | Broad retrieval | Selective retrieval | Multiple or moderately selective matches |
| Multiple indexes combined | No | Usually one selected index path | Bitmap AND/OR |
| Candidate identification | Direct tuple examination | Index entries | Bitmap of tuple locations |
| Heap access avoided | No | Not normally | No |
| Index-only possibility | No | Separate Index Only Scan | Not the same as Index Only Scan |

### 6.1 Practical selection

| Query characteristics | Possible preferred strategy |
|---|---|
| Very small table | Sequential Scan |
| Highly selective primary-key lookup | Index Scan |
| Multiple indexed equality conditions | Bitmap Scan |
| Broad retrieval of most records | Sequential Scan |
| Covering index with suitable visibility information | Index Only Scan |
| Index matches many scattered heap records | Bitmap Scan or Sequential Scan |

These are tendencies, not guaranteed planner decisions.

## 7. Cost-Based Query Planning

PostgreSQL uses a cost-based optimizer.

It evaluates possible execution plans and estimates their relative costs.

The planner does not simply select an index whenever one exists.

### 7.1 Important cost parameters

| Parameter | Purpose |
|---|---|
| `seq_page_cost` | Estimated cost of sequential page access |
| `random_page_cost` | Estimated cost of random page access |
| `cpu_tuple_cost` | Estimated tuple-processing cost |
| `cpu_index_tuple_cost` | Estimated index tuple-processing cost |
| `cpu_operator_cost` | Estimated operator-processing cost |
| `effective_cache_size` | Planner estimate of available caching capacity |

The cost values are estimates rather than actual execution times.

### 7.2 Cost comparison

A simplified comparison is:

\[
C_{seq}=P \times S + N \times T
\]

\[
C_{index}=I + R \times H
\]

\[
C_{bitmap}=B + Q \times H + R \times T
\]

Where:

- \(P\) represents table pages.
- \(N\) represents table tuples.
- \(S\) represents sequential page cost.
- \(T\) represents tuple-processing cost.
- \(I\) represents index traversal cost.
- \(R\) represents matching tuples.
- \(H\) represents heap-page access cost.
- \(B\) represents bitmap construction cost.
- \(Q\) represents relevant heap pages.

These equations are educational approximations. PostgreSQL's actual formulas are more detailed.

### 7.3 Statistics and ANALYZE

PostgreSQL maintains statistics describing table and column distributions.

The `ANALYZE` command collects statistics used by the planner.

Example:

    ANALYZE employees;

Statistics include:

- Null fraction
- Number of distinct values
- Most common values
- Most common value frequencies
- Histograms
- Physical correlation

Inaccurate or outdated statistics can produce poor cardinality estimates.

Autovacuum and autoanalyze help maintain database statistics during normal operation.

### 7.4 Correlation

Physical correlation measures the relationship between the logical ordering of a column and the physical ordering of table records.

A high absolute correlation can make indexed heap access more efficient because related index entries may refer to nearby heap pages.

Low correlation can increase random heap access.

This helps explain why two tables with identical row counts and indexes can exhibit different scan performance.

## 8. PostgreSQL EXPLAIN and EXPLAIN ANALYZE

`EXPLAIN` displays the estimated execution plan without executing the query.

Example:

    EXPLAIN
    SELECT *
    FROM employees
    WHERE employee_id = 1000;

`EXPLAIN ANALYZE` executes the query and reports actual execution measurements.

Example:

    EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
    SELECT *
    FROM employees
    WHERE employee_id = 1000;

### 8.1 Important plan fields

| Field | Meaning |
|---|---|
| `Seq Scan` | Sequential heap access |
| `Index Scan` | Index-based tuple retrieval |
| `Bitmap Index Scan` | Index-generated candidate bitmap |
| `Bitmap Heap Scan` | Heap access using bitmap information |
| `Index Only Scan` | Retrieval using index data where visibility permits |
| `cost` | Estimated startup and total cost |
| `rows` | Estimated output row count |
| `width` | Estimated average output row width |
| `actual time` | Observed execution timing |
| `actual rows` | Actual output row count |
| `loops` | Number of node executions |
| `Buffers` | Buffer activity associated with execution |

### 8.2 Estimated versus actual rows

A major query optimization diagnostic is the difference between estimated and actual cardinality.

For example:

| Measurement | Value |
|---|---:|
| Estimated rows | 100 |
| Actual rows | 20,000 |

A large discrepancy can lead to an inappropriate access strategy.

Potential causes include:

- Outdated statistics.
- Skewed value distributions.
- Correlated predicates.
- Insufficient column statistics.
- Parameter-sensitive data distributions.

PostgreSQL extended statistics can help with certain cross-column estimation problems.

## 9. Implementation Architecture

The five source files use the same central database concepts but different engineering approaches.

| File | Implementation focus |
|---|---|
| Python | Simulation, data structures, validation and cost estimation |
| JavaScript | Event-driven execution, asynchronous processing and policy evaluation |
| C++17 | Efficient tuple-location structures and bitmap intersection |
| Java 17 | Enterprise domain modeling and controlled query lifecycle |
| PostgreSQL | Actual relational storage, indexes, planner and executor |

### 9.1 Python implementation

The Python implementation uses:

- `Table` for relation storage.
- `Index` for secondary index structures.
- `Predicate` for query conditions.
- `QueryPlanner` for estimated scan selection.
- `QueryExecutor` for execution.
- `ExecutionMetrics` for instrumentation.

The index is represented as a dictionary mapping column values to sets of row identifiers.

For example:

    department = {
        "Engineering": {0, 4, 8},
        "Finance": {1, 5, 9}
    }

Bitmap AND is implemented through set intersection.

The implementation also validates index consistency after insertions and deletions.

Its cost model is educational rather than a reproduction of PostgreSQL's internal planner.

### 9.2 JavaScript implementation

The JavaScript implementation emphasizes asynchronous and event-driven execution.

Its main components are:

- `Relation`
- `SecondaryIndex`
- `Predicate`
- `CostModel`
- `QueryEngine`

The engine emits query lifecycle events:

- `query:start`
- `query:complete`

`Map` provides value-to-index-entry mappings, while `Set` supports candidate tuple identification and bitmap intersections.

The asynchronous execution method yields to the Node.js event loop.

This implementation illustrates how a query execution service can expose observable execution events without introducing an external package.

### 9.3 C++17 implementation

The C++ implementation emphasizes data structures and execution efficiency.

It uses:

- `vector` for tuple storage.
- `unordered_map` for index lookup.
- `set` for ordered tuple identifiers.
- STL algorithms for intersection and filtering.
- Exceptions for invalid operations.

The bitmap AND operation uses `set_intersection`.

The implementation uses stable tuple identifiers and inactive tuple slots after deletion.

This preserves index references and avoids renumbering all subsequent tuples.

A production storage engine would require additional concurrency, transaction visibility, page management, and recovery mechanisms.

### 9.4 Java 17 implementation

The Java implementation uses explicit domain types and enterprise service boundaries.

Its important components include:

- `Employee`
- `Predicate`
- `ScanPlan`
- `Metrics`
- `QueryContext`
- `EmployeeRepository`
- `CostBasedPlanner`
- `QueryService`

Records provide immutable representations of employee data, predicates, execution plans, and results.

The query lifecycle uses explicit states:

    CREATED
       |
       v
    VALIDATED
       |
       v
    PLANNED
       |
       v
    EXECUTING
       |
       v
    COMPLETED

A failed query transitions to `FAILED`.

Invalid transitions are rejected.

The repository synchronizes data operations to provide a simple thread-safe in-memory model. This does not constitute a complete transactional database engine.

## 10. PostgreSQL Implementation

The PostgreSQL script creates a complete experimental environment in the `scan_lab` schema.

### 10.1 Relational model

The domain contains:

    Departments
         |
         v
       Employees
         |
         v
      Locations

The employee table contains:

- Employee identifier.
- Employee name.
- Department identifier.
- Location identifier.
- Salary.
- Active status.
- Hiring date.
- Creation timestamp.

The model uses primary keys, foreign keys, uniqueness constraints, and salary validation.

### 10.2 Index configurations

The script demonstrates:

| Index | Purpose |
|---|---|
| Primary-key index | Unique employee identification |
| Department index | Department-based filtering |
| Location index | Location-based filtering |
| Salary index | Salary-based filtering |
| Boolean index | Active-status filtering |
| Covering index | Supporting index-only retrieval |
| Partial index | Indexing active employees |
| Composite index | Combined department and location filtering |

### 10.3 Controlled execution experiments

The script uses transaction-scoped planner settings to inspect alternative access strategies.

For example:

- `enable_seqscan` discourages sequential scans.
- `enable_indexscan` discourages ordinary index scans.
- `enable_bitmapscan` discourages bitmap scans.
- `enable_indexonlyscan` discourages index-only scans.

These settings are intended for controlled experiments.

They should not be treated as routine production tuning recommendations.

### 10.4 Index maintenance

PostgreSQL automatically maintains indexes during supported data modifications.

The script also implements a trigger-based audit table that records employee insertion, update, and deletion operations.

The audit table illustrates logical data modification history, while the database's storage engine performs the actual index maintenance.

## 11. Performance Analysis and Complexity

Let:

- \(N\) be the number of table records.
- \(P\) be the number of heap pages.
- \(R\) be the number of matching records.
- \(I\) be the number of matching index entries.
- \(B\) be the number of bitmap candidates.

| Operation | Approximate complexity |
|---|---|
| Sequential examination | \(O(N)\) |
| Hash-based index lookup | Expected \(O(1)\) per key lookup |
| B-tree index lookup | \(O(\log N)\) |
| Candidate filtering | \(O(R)\) |
| Bitmap intersection using hash sets | Expected \(O(B)\) per additional bitmap |
| Ordered set intersection | \(O(B_1+B_2)\) |

These complexities describe the educational implementations or abstract data-structure operations. They are not exact PostgreSQL execution guarantees.

### 11.1 Sequential scan performance

Sequential scans benefit from predictable page access and efficient bulk reading.

They can also take advantage of operating-system and database caching.

### 11.2 Index scan performance

Index scans can minimize the number of records examined.

Their performance may decline when matching records are distributed across many heap pages.

The number of heap-page accesses can be more important than the number of matching index entries alone.

### 11.3 Bitmap scan performance

Bitmap scans can reduce repeated heap-page accesses.

They introduce additional work to build, combine, and process bitmap structures.

They also require memory.

When bitmap memory is insufficient, PostgreSQL can use lossy representations that require additional tuple rechecks.

## 12. Security and Operational Considerations

Database performance optimization must not weaken data integrity or access controls.

Important considerations include:

- Use parameterized SQL queries instead of dynamically concatenating untrusted input.
- Apply appropriate database roles and privileges.
- Avoid granting unnecessary index-management permissions.
- Validate query inputs and column identifiers.
- Monitor index storage overhead.
- Evaluate index maintenance costs during updates and inserts.
- Monitor table and index bloat.
- Maintain accurate statistics.
- Use transaction boundaries for related changes.
- Avoid disabling planner features globally without measured evidence.

Indexes can increase write costs because insertions, updates, and deletions may require index maintenance.

A large number of unnecessary indexes can increase storage requirements and reduce write throughput.

## 13. Practical Limitations

The Python, JavaScript, C++17, and Java 17 implementations are educational query-engine simulations.

They do not reproduce all PostgreSQL storage and execution mechanisms.

Specifically, they do not implement:

- MVCC transaction visibility.
- WAL-based crash recovery.
- Real disk-page management.
- Concurrent index modification.
- PostgreSQL buffer management.
- Full B-tree page splitting.
- Real lossy bitmap representations.
- Parallel query execution.
- PostgreSQL's complete selectivity estimation.
- Join planning and advanced predicate optimization.

The PostgreSQL script demonstrates actual database execution plans and should be used to observe the behavior of a real PostgreSQL server.

The simplified cost functions in the other implementations are useful for understanding the relationship between selectivity, index traversal, heap access, and sequential reading. They should not be used to predict exact PostgreSQL execution costs.

## 14. Key Technical Distinctions

| Concept | Core responsibility |
|---|---|
| Sequential Scan | Examines heap records directly |
| Index Scan | Locates tuples through an index |
| Bitmap Index Scan | Produces candidate tuple locations |
| Bitmap AND | Intersects candidate locations |
| Bitmap OR | Unions candidate locations |
| Bitmap Heap Scan | Retrieves candidate tuples from heap pages |
| Index Only Scan | Retrieves qualifying values from an index when visibility permits |
| Query Planner | Selects an estimated low-cost execution plan |
| Query Executor | Executes the selected plan |
| ANALYZE | Collects statistics for planning |
| EXPLAIN | Displays estimated execution plans |
| EXPLAIN ANALYZE | Executes and measures the actual query plan |

The central distinction is that sequential scans prioritize bulk heap reading, index scans prioritize direct tuple identification, and bitmap scans organize multiple index results before retrieving heap records.
