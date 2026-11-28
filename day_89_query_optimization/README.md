# Query Optimization: Predicate Pushdown, Join Optimization and Reducing Unnecessary Work

## 1. Project Scope

Query optimization improves database execution by reducing unnecessary data access, intermediate results, comparisons, memory consumption and processing operations.

This project implements a relational employee-management scenario to demonstrate three important optimization techniques:

1. Predicate pushdown.
2. Join optimization.
3. Index-assisted data retrieval.

The implementations use Python, JavaScript, C++17, Java 17 and PostgreSQL.

The central objective is to retrieve active employees earning at least 75,000 from departments located in Lucknow without processing unrelated records unnecessarily.

## 2. Fundamental Concepts

### 2.1 Query Processing

A relational database transforms a declarative SQL statement into an executable physical plan.

The main stages are:

- Parsing: checks SQL syntax.
- Semantic analysis: validates tables, columns, types and references.
- Query rewriting: transforms equivalent expressions.
- Cost estimation: estimates cardinality and execution costs.
- Plan selection: selects physical operations.
- Execution: accesses data and produces results.

A SQL query specifies the required result, not necessarily the exact sequence of physical operations.

### 2.2 Logical and Physical Query Plans

A logical plan describes relational operations independently of their physical implementation.

For example:

    Employee
        |
    Filter active employees
        |
    Filter salary >= 75000
        |
    Join Department
        |
    Filter location = Lucknow
        |
    Projection

A physical plan specifies how these operations execute.

Examples include:

- Sequential scan.
- Index scan.
- Nested-loop join.
- Hash join.
- Merge join.
- Sort.
- Aggregation.

Different physical plans can produce identical logical results with substantially different execution costs.

### 2.3 Query Cost

Important performance measurements include:

| Measurement | Meaning |
|---|---|
| Rows scanned | Records examined during execution |
| Cardinality | Number of rows produced by an operation |
| Selectivity | Fraction of rows satisfying a predicate |
| CPU cost | Processing and comparison operations |
| I/O cost | Disk and buffer access |
| Memory usage | Space consumed by intermediate operations |
| Execution time | Time required to complete execution |
| Buffer hits | Data retrieved from PostgreSQL shared buffers |
| Temporary I/O | Disk activity caused by operations exceeding available memory |

A query returning a small result can still be expensive if it examines a large number of unrelated records.

## 3. Predicate Pushdown

### 3.1 Definition

Predicate pushdown moves applicable filtering conditions closer to the underlying data sources.

Instead of joining entire relations and filtering the resulting records, the system filters individual relations before performing the join whenever relational semantics permit.

Consider:

    SELECT e.employee_id,
           e.employee_name,
           d.department_name
    FROM employees e
    JOIN departments d
      ON e.department_id = d.department_id
    WHERE e.employment_status = 'ACTIVE'
      AND e.salary >= 75000
      AND d.location = 'Lucknow';

The employee predicates are:

- employment_status = ACTIVE
- salary >= 75000

The department predicate is:

- location = Lucknow

The optimizer can reduce both relations before joining them.

### 3.2 Relational Algebra

Let:

- E represent employees.
- D represent departments.
- σ represent selection.
- ⋈ represent join.
- π represent projection.

The original expression is:

    σ(E.employment_status = ACTIVE
      AND E.salary >= 75000
      AND D.location = Lucknow)
    (E ⋈ D)

The equivalent optimized expression is:

    σ(E.employment_status = ACTIVE
      AND E.salary >= 75000)(E)
    ⋈
    σ(D.location = Lucknow)(D)

The transformation reduces the number of tuples entering the join.

### 3.3 Selectivity

Selectivity is calculated as:

    Selectivity = Matching Rows / Total Rows

Suppose a relation contains 1,000,000 records.

| Predicate | Selectivity | Remaining rows |
|---|---:|---:|
| Active employees | 0.80 | 800,000 |
| Salary threshold | 0.10 | 80,000 |
| Specific location | 0.05 | 4,000 |

These estimates illustrate why selective predicates can substantially reduce intermediate processing.

The most selective predicate is not necessarily the first predicate PostgreSQL must execute. The optimizer considers available indexes, statistics, CPU cost, I/O cost and other plan alternatives.

### 3.4 Important Restrictions

Predicate pushdown must preserve query semantics.

Special care is required with:

- Outer joins.
- NULL values.
- Aggregate functions.
- Window functions.
- LIMIT and OFFSET.
- Volatile functions.
- Security-barrier views.
- Correlated subqueries.

For example, moving a condition from the WHERE clause into an outer join's filtering stage can change the treatment of unmatched rows.

A transformation is valid only when the resulting relational expression preserves the original query's meaning.

## 4. Join Optimization

### 4.1 Join Fundamentals

A join combines related records from two or more relations.

The employee and department relationship is:

    employees.department_id
        =
    departments.department_id

Join performance depends on:

- Relation cardinalities.
- Join-key distribution.
- Available indexes.
- Memory availability.
- Data ordering.
- Predicate selectivity.
- Statistics accuracy.

### 4.2 Nested-Loop Join

The nested-loop algorithm compares records from two relations.

Conceptually:

    for each employee:
        for each department:
            compare department IDs
            return matching records

For relations containing N and M records, the basic comparison complexity is:

    O(N × M)

Nested-loop joins are useful when one input is small, particularly when the inner relation can be accessed efficiently through an index.

They can be expensive when both inputs are large and no effective index is available.

### 4.3 Hash Join

A hash join builds a hash table using the join key of one relation.

The other relation probes that hash table to identify matching records.

Conceptually:

    Build:
        hash_table[department_id] = department

    Probe:
        for each employee:
            department = hash_table.get(employee.department_id)
            if department exists:
                return joined record

Expected complexity for an in-memory hash join is approximately:

    O(N + M)

Hash joins are effective for equality joins involving sufficiently large, unsorted inputs.

Important considerations include:

- Hash-table construction cost.
- Memory consumption.
- Hash collisions.
- Data skew.
- Batch processing when memory is insufficient.
- Temporary-file I/O.

A hash join is not automatically superior to every nested-loop join.

### 4.4 Merge Join

A merge join processes two inputs ordered by their join keys.

It advances through both inputs while identifying matching key values.

When sorting is already available, the merge phase can operate in approximately:

    O(N + M)

If sorting is necessary, additional sorting costs must be considered.

Merge joins are particularly useful when inputs are already ordered or when the required output benefits from that ordering.

### 4.5 Join Strategy Comparison

| Join algorithm | Main mechanism | Typical use |
|---|---|---|
| Nested loop | Repeated matching | Small outer relation or indexed inner lookup |
| Hash join | Hash table lookup | Equality joins with large unsorted relations |
| Merge join | Ordered input comparison | Sorted relations and suitable join conditions |

The database optimizer selects an appropriate physical strategy based on estimated costs.

## 5. Index-Assisted Optimization

### 5.1 Index Definition

An index is an additional data structure that helps locate records without scanning an entire table.

PostgreSQL supports several index types, including:

- B-tree.
- Hash.
- GiST.
- SP-GiST.
- GIN.
- BRIN.

The project uses B-tree indexes for common equality and range-based retrieval.

### 5.2 Composite Indexes

A composite index contains multiple columns.

For example:

    CREATE INDEX idx_employees_department_salary
    ON employees(department_id, salary DESC);

This can support queries that constrain department ID and salary.

Column order matters.

An index beginning with department_id is generally most useful when the query constrains department_id or uses an applicable leading-column access pattern.

### 5.3 Partial Indexes

A partial index stores entries only for records satisfying a specified predicate.

Example:

    CREATE INDEX idx_employees_active_salary
    ON employees(salary)
    WHERE employment_status = 'ACTIVE';

This avoids indexing inactive and suspended employee records.

Partial indexes can reduce index size and improve relevant query performance.

The query predicate must be compatible with the partial-index condition for PostgreSQL to use it.

### 5.4 Index Trade-offs

Indexes have costs:

- Additional disk space.
- Increased INSERT overhead.
- Increased UPDATE overhead.
- Increased DELETE overhead.
- Maintenance and vacuum requirements.
- Potentially lower cache efficiency.

Creating indexes on every column is not an effective optimization strategy.

Index selection should follow actual query patterns and execution-plan evidence.

## 6. Query Planning and Cost Estimation

PostgreSQL uses a cost-based optimizer.

Its decisions depend on estimated:

- Row counts.
- Column distributions.
- Distinct values.
- NULL frequencies.
- Data correlation.
- Available indexes.
- Join cardinalities.
- Memory and configuration settings.

### 6.1 EXPLAIN

EXPLAIN displays the planned execution strategy without executing the query.

Important plan nodes include:

| Plan node | Function |
|---|---|
| Seq Scan | Sequential table scanning |
| Index Scan | Index-assisted retrieval with heap access |
| Index Only Scan | Retrieval using index data when visibility conditions permit |
| Bitmap Heap Scan | Bitmap-based heap retrieval |
| Nested Loop | Nested-loop join |
| Hash Join | Hash-based join |
| Merge Join | Ordered merge join |
| Sort | Ordering records |
| Aggregate | Aggregation |

### 6.2 EXPLAIN ANALYZE

EXPLAIN ANALYZE executes the query and reports actual execution measurements.

The PostgreSQL implementation uses:

    EXPLAIN (ANALYZE, BUFFERS, VERBOSE)

Important measurements include:

- Estimated rows.
- Actual rows.
- Loops.
- Startup cost.
- Total cost.
- Planning time.
- Execution time.
- Shared buffer hits and reads.
- Temporary blocks.

Large differences between estimated and actual row counts can indicate inaccurate statistics or data-distribution problems.

EXPLAIN ANALYZE executes the statement. For write operations, use a transaction with appropriate rollback controls when testing changes.

### 6.3 Statistics

PostgreSQL collects table and column statistics through ANALYZE and VACUUM-related maintenance.

The optimizer uses these statistics to estimate selectivity and cardinality.

Outdated statistics can lead to poor execution plans.

For correlated columns, extended statistics can improve estimates when ordinary independent-column assumptions are insufficient.

## 7. Reducing Unnecessary Work

Query optimization extends beyond predicate pushdown and joins.

Other important techniques include:

### 7.1 Projection Pushdown

Retrieve only required columns.

Less efficient:

    SELECT *
    FROM employees;

More targeted:

    SELECT employee_id, employee_name, salary
    FROM employees;

Reducing projected columns can decrease data transfer, memory use and I/O.

### 7.2 Early LIMIT

LIMIT can reduce the number of returned rows.

However, LIMIT does not always mean the database examines only that number of records.

An ORDER BY operation may still require substantial processing before the top records can be identified.

### 7.3 Avoid Repeated Computation

Expensive expressions and repeated subqueries may perform unnecessary work.

Depending on semantics and query structure, common table expressions, subqueries, materialized views and appropriate indexes can reduce repeated operations.

### 7.4 Materialized Views

A materialized view stores the result of a query.

It is useful when:

- Aggregations are expensive.
- The underlying data changes less frequently than it is queried.
- Slightly stale results are acceptable.
- Refresh operations can be scheduled.

PostgreSQL materialized views do not automatically refresh when underlying tables change.

### 7.5 Partition Pruning

Partitioned tables can eliminate irrelevant partitions when predicates constrain partition keys.

This reduces the amount of data that must be accessed.

Partitioning is most beneficial when table size, retention patterns and query predicates justify its operational complexity.

## 8. Implementation Architecture

The five implementations provide different perspectives on the same relational workload.

### Python

The Python script models:

- Employee and department records.
- Dataclasses and validation.
- Nested-loop joining.
- Predicate pushdown.
- Hash-based lookup.
- Prebuilt department indexes.
- Execution metrics.
- Result-equivalence assertions.
- SQLite query execution and plan inspection.

The script demonstrates how filtering and lookup structures change computational work.

### JavaScript

The JavaScript implementation uses:

- Maps for entity storage.
- Sets for location-based lookup.
- Immutable stored records.
- Asynchronous batch processing.
- Promise-based execution.
- Query validation.
- A query-planning estimator.
- Event-loop-friendly processing.
- Execution metrics.

The asynchronous pushdown implementation yields between batches, reducing the risk of monopolizing the Node.js event loop.

### C++17

The C++ implementation provides a repository-level query execution engine.

It includes:

- Struct-based domain models.
- STL containers.
- Hash-based lookup.
- Location indexing.
- Three join strategies.
- Input validation.
- Exception handling.
- Deterministic result ordering.
- Runtime measurements.
- Result-equivalence verification.

Its data indexes use pointers into vectors whose contents remain unchanged during query execution.

### Java 17

The Java implementation uses an enterprise-oriented architecture.

It includes:

- Immutable records.
- Repository abstraction.
- Separate query and execution types.
- Explicit optimization strategies.
- Hash and location indexes.
- Query validation.
- Immutable result collections.
- Plan estimation.
- Execution metrics.
- Strategy consistency checks.

The separation between repository, optimizer, query and execution result makes the model easier to extend and maintain.

### PostgreSQL

The SQL implementation provides actual relational database operations.

It includes:

- Relational schema.
- Primary and foreign keys.
- Check and unique constraints.
- B-tree and partial indexes.
- Views.
- CTEs.
- Query functions.
- Stored procedures.
- Triggers.
- Materialized views.
- Transactions.
- EXPLAIN ANALYZE.
- Statistics and reporting.

PostgreSQL determines the actual physical execution plan. The SQL expressions do not guarantee that a particular join algorithm or predicate execution order will be selected.

## 9. Execution Workflow

The recommended execution order is:

    Data generation
          |
          v
    Domain validation
          |
          v
    Baseline query
          |
          v
    Predicate pushdown
          |
          v
    Join strategy selection
          |
          v
    Index-assisted retrieval
          |
          v
    Result sorting and limiting
          |
          v
    Metrics collection
          |
          v
    Result equivalence verification

The relational results must remain equivalent across valid execution strategies.

An optimization that changes the requested result is an incorrect transformation, regardless of its performance.

## 10. Running the Implementations

### Python

Requirements:

- Python 3.10 or later.
- Standard library only.

Run:

    python query_optimization.py

SQLite is included in Python's standard library.

### JavaScript

Requirements:

- Node.js 18 or later.
- No npm dependencies.

Run:

    node query_optimization.js

### C++17

Requirements:

- C++17-compatible compiler.

Compile:

    g++ -std=c++17 -O2 -Wall -Wextra -pedantic query_optimization.cpp -o query_optimization

Run:

    ./query_optimization

On Windows:

    query_optimization.exe

### Java 17

Requirements:

- JDK 17.

Compile:

    javac QueryOptimization.java

Run:

    java QueryOptimization

### PostgreSQL

Requirements:

- PostgreSQL 14 or later.
- A database role with schema and table creation privileges.

Execute:

    psql -U postgres -d your_database -f query_optimization.sql

The SQL script creates and replaces the dedicated query_optimization schema.

## 11. Performance Interpretation

The implementations compare three approaches.

| Strategy | Filtering | Join mechanism |
|---|---|---|
| Baseline | After matching records | Nested loop |
| Pushdown | Before joining | Hash lookup |
| Indexed | Targeted department retrieval | Prebuilt indexes |

The baseline implementation deliberately uses a nested-loop approach to demonstrate the cost of unnecessary comparisons.

The optimized implementations reduce the candidate records before joining.

The indexed strategy is particularly effective when the requested location identifies a small portion of departments.

Actual performance depends on data distribution, memory, hardware, index availability, caching and implementation overhead.

The in-memory implementations are educational execution models, not replacements for PostgreSQL's cost-based optimizer.

## 12. Edge Cases and Correctness

The implementations account for:

- Empty matching locations.
- No qualifying employees.
- Invalid salary thresholds.
- Invalid employee identifiers.
- Duplicate identifiers.
- Missing department references.
- Negative salaries.
- Invalid result limits.
- Inactive employees.
- Different join execution strategies.
- Consistent result ordering.

The PostgreSQL implementation adds relational integrity enforcement through constraints and foreign keys.

The SQL examples use actual database operations rather than simulated query-plan output.

## 13. Security and Production Considerations

Query optimization must preserve database security.

Important controls include:

- Parameterized SQL statements.
- Restricted database privileges.
- Appropriate row-level security.
- Safe dynamic SQL construction.
- Query execution timeouts.
- Connection pooling.
- Resource limits.
- Monitoring of expensive statements.
- Protection against unrestricted user-generated queries.

The Python and SQLite example uses bound parameters for user-supplied query values.

Production database applications should avoid constructing SQL statements by concatenating untrusted input.

Indexes and materialized views also require maintenance planning.

A query optimization should be evaluated using representative production-like data rather than relying exclusively on small test datasets.

## 14. Limitations

The in-memory engines simplify several database mechanisms.

They do not fully model:

- Disk-based execution.
- Concurrent transactions.
- MVCC visibility.
- Lock contention.
- Buffer management.
- Distributed joins.
- Parallel query execution.
- Disk-spilling hash joins.
- Advanced cardinality estimation.
- Adaptive execution.
- Network transfer costs.

Their execution metrics are algorithmic indicators, not directly comparable database cost estimates.

The PostgreSQL implementation provides the actual database execution-plan interface needed to investigate these additional factors.

## 15. Technical Distinctions

| Concept | Primary objective |
|---|---|
| Predicate pushdown | Filter records earlier |
| Projection pushdown | Retrieve fewer columns |
| Join optimization | Reduce join processing cost |
| Indexing | Locate relevant records efficiently |
| Cardinality estimation | Predict intermediate result sizes |
| Selectivity estimation | Predict predicate filtering effectiveness |
| Cost-based optimization | Select an economical execution plan |
| Materialization | Store reusable query results |
| Partition pruning | Eliminate irrelevant partitions |
| Query equivalence | Preserve the requested result |

These mechanisms complement one another but solve different performance problems.

A good execution plan minimizes unnecessary work while preserving relational correctness.
