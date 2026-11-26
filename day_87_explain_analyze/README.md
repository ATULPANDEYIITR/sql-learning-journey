# PostgreSQL EXPLAIN ANALYZE: Actual Execution Time, Rows, Loops and Plan Verification

## 1. Technical Scope

`EXPLAIN ANALYZE` is a PostgreSQL command for examining the execution plan of a SQL statement and measuring its actual execution.

It connects two different perspectives:

- **Estimated execution:** What PostgreSQL's planner predicts before executing the query.
- **Actual execution:** What PostgreSQL observes while executing the query.

This distinction is essential for diagnosing slow SQL, understanding access methods, investigating inaccurate row estimates, and evaluating the effectiveness of indexes.

The five implementations approach the subject from different engineering perspectives.

| Implementation | Main purpose |
|---|---|
| Python | Parse and evaluate PostgreSQL JSON execution plans |
| JavaScript | Event-driven performance policy evaluation |
| C++17 | Efficient execution-plan analysis and verification |
| Java 17 | Enterprise-oriented performance governance |
| PostgreSQL | Relational benchmarking, JSON plan extraction, and verification |

The sample execution measurements in the programming-language implementations are illustrative. They are not presented as measurements obtained from a live PostgreSQL server.

The PostgreSQL script executes real SQL statements and obtains actual execution measurements when run against a database.

## 2. Understanding EXPLAIN and EXPLAIN ANALYZE

### EXPLAIN

`EXPLAIN` requests a query execution plan without executing the query.

For example, PostgreSQL can return:

- Selected scan method.
- Join algorithm.
- Estimated number of rows.
- Estimated startup cost.
- Estimated total cost.
- Index selection.
- Sort and aggregation operations.

The planner uses table statistics, available indexes, query structure, and configuration parameters to choose a plan.

The estimates are predictions rather than measurements.

### EXPLAIN ANALYZE

`EXPLAIN ANALYZE` executes the statement and reports observed execution information.

For example:

| Metric | Meaning |
|---|---|
| Planning Time | Time spent planning the query |
| Execution Time | Total measured query execution time |
| Actual Startup Time | Time before the node produces its first row |
| Actual Total Time | Time until the node finishes producing its rows |
| Actual Rows | Average rows produced per loop |
| Actual Loops | Number of times the plan node executes |
| Shared Hit Blocks | Shared-buffer blocks found in memory |
| Shared Read Blocks | Shared-buffer blocks read into memory |

Actual timing and row information are particularly useful because estimated costs alone cannot establish how a query performs under actual execution conditions.

## 3. Actual Execution Time

Execution time is the measured duration of the executed query.

A PostgreSQL plan can include:

- Planning Time: 0.450 ms
- Execution Time: 2.750 ms

These values represent different activities.

Planning Time measures the planning phase. Execution Time measures the execution phase.

The execution time is not necessarily equal to the sum of the displayed node times.

### Inclusive node timing

PostgreSQL plan-node times are inclusive of the execution of their children.

For example, a nested-loop node may report 5 ms while its child nodes report 1 ms and 3 ms.

Adding all three values would double-count work because the parent includes child execution.

Therefore:

- Use node timing to investigate where execution time is spent.
- Use Execution Time to evaluate the complete statement.
- Do not add parent and child node times to calculate total query execution time.

### Timing overhead

`EXPLAIN ANALYZE` introduces measurement overhead.

Instrumentation can affect execution, particularly for queries containing many small plan operations.

The measured duration should therefore be interpreted as an instrumented execution measurement rather than an exact representation of every ordinary production execution.

Repeated measurements are more useful than a single observation.

## 4. Actual Rows and Estimated Rows

PostgreSQL estimates the number of rows each plan node will produce.

The execution engine measures the number of rows actually produced.

Consider the following example:

| Metric | Value |
|---|---:|
| Estimated Rows | 100 |
| Actual Rows | 1,000 |
| Actual Loops | 1 |

The planner expected 100 rows but observed 1,000.

The actual cardinality was ten times the estimate.

A large difference can indicate:

- Outdated table statistics.
- Correlated columns.
- Highly selective predicates.
- Data skew.
- Inadequate statistical information.
- Parameter-sensitive query behavior.

### Cardinality estimation ratio

A useful diagnostic ratio is:

\[
R = \max\left(
\frac{ActualRows}{EstimatedRows},
\frac{EstimatedRows}{ActualRows}
\right)
\]

When both values are positive:

| Ratio | Interpretation |
|---|---|
| 1 | Exact estimate |
| 2 | Twofold estimation difference |
| 5 | Fivefold estimation difference |
| 10 | Significant estimation difference |
| 20+ | Potentially serious estimation problem |

A ratio is a diagnostic measure, not a universal PostgreSQL performance threshold.

Zero-row cases require separate handling because division by zero is undefined.

An estimated zero with positive actual rows represents an important estimation failure.

An actual zero with a positive estimate also indicates a mismatch.

## 5. Understanding Actual Loops

`Actual Loops` represents the number of times a plan node executes.

This is particularly important for nested-loop joins and parameterized scans.

Consider:

| Metric | Value |
|---|---:|
| Estimated Rows | 1 |
| Actual Rows | 2 |
| Actual Loops | 100 |

The node produces an average of two rows per execution and executes 100 times.

The approximate total number of rows produced is:

\[
TotalRows = ActualRows \times ActualLoops
\]

\[
TotalRows = 2 \times 100 = 200
\]

PostgreSQL generally reports actual row counts and node times as averages per loop when a node executes multiple times.

The Python, JavaScript, C++17, and Java implementations explicitly calculate:

- Actual rows per loop.
- Total rows across loops.
- Actual time per loop.
- Accumulated node time.

Accumulated node time is useful for investigating repeated work.

It is not a substitute for the query's overall Execution Time.

### Why loops matter

A nested-loop join can execute an inner index scan once for every matching outer row.

An individual inner scan might be inexpensive, but repeated execution can become expensive.

This is why a plan should not be evaluated using individual node timing without examining its loop count.

## 6. PostgreSQL Execution Plan Nodes

An execution plan is a tree of operations.

A simplified representation is:

    Nested Loop
    |
    |-- Index Scan: customers
    |
    |-- Index Scan: orders

The parent node combines the results produced by its children.

### Important plan-node types

| Node | Function |
|---|---|
| Seq Scan | Reads a table sequentially |
| Index Scan | Uses an index to locate table rows |
| Index Only Scan | Attempts to retrieve required values from an index |
| Bitmap Index Scan | Identifies matching tuple locations through an index |
| Bitmap Heap Scan | Retrieves matching heap tuples using a bitmap |
| Nested Loop | Joins records using repeated inner execution |
| Hash Join | Uses a hash table to perform a join |
| Merge Join | Joins inputs ordered on their join keys |
| Sort | Orders rows |
| Aggregate | Performs aggregation |

### Sequential Scan

A sequential scan reads the table's heap pages.

It is not automatically inefficient.

For small tables or queries returning a large proportion of the table, a sequential scan may be more efficient than an index scan.

### Index Scan

An index scan uses an index to locate matching rows.

It can be useful when the query selects a relatively small portion of a large relation.

Its performance depends on selectivity, index structure, heap access, cache behavior, and the number of matching rows.

### Nested Loop

A nested-loop join processes one input and repeatedly evaluates the other input.

It can perform well when the outer relation is small and the inner relation has an effective index.

It can perform poorly when the inner operation executes many times.

### Hash Join

A hash join builds a hash table from one input and probes it using the other input.

It is useful for many equality joins.

Its performance depends on memory availability, input size, hash-table construction, and possible disk spilling.

### Merge Join

A merge join processes ordered inputs.

It can be efficient when suitable ordering already exists or can be obtained economically.

Sorting requirements can increase execution time.

## 7. Buffer Statistics

`EXPLAIN (ANALYZE, BUFFERS)` reports buffer activity.

Important shared-buffer measurements include:

- Shared Hit Blocks.
- Shared Read Blocks.
- Shared Dirtied Blocks.
- Shared Written Blocks.

### Shared Hit Blocks

A shared hit indicates that the requested block was already available in PostgreSQL shared buffers.

It does not mean that the operation was free.

CPU processing and tuple access still consume resources.

### Shared Read Blocks

A shared read indicates that a block had to be brought into shared buffers.

It does not necessarily prove that a physical disk operation occurred because the operating system may have cached the underlying data.

### Buffer interpretation

A high number of shared hits may indicate repeated access to the same pages.

A high number of shared reads may indicate substantial data access or insufficient cache residency.

Neither measurement should be interpreted independently of query size, execution time, and workload characteristics.

## 8. Planning Cost Versus Actual Time

PostgreSQL displays:

- Startup Cost.
- Total Cost.

These are planner cost estimates, not milliseconds.

The planner uses internal cost units to compare alternative execution plans.

Consequently:

| Planner Metric | Actual Metric |
|---|---|
| Startup Cost | Actual Startup Time |
| Total Cost | Actual Total Time |
| Plan Rows | Actual Rows |
| Estimated operation | Observed operation |

A cost of 100 does not mean 100 milliseconds.

Cost estimates are useful for understanding planner decisions and comparing alternatives. Actual execution time is needed to assess measured runtime.

## 9. Statistics and Cardinality Estimation

PostgreSQL uses table statistics to estimate query cardinality.

The `ANALYZE` command collects statistics used by the planner.

For example:

    ANALYZE orders;

The planner uses the collected information to estimate the distribution of values and the selectivity of conditions.

### Statistics problems

Estimates can become inaccurate when:

- Data distributions change.
- Large batches of records are inserted.
- Values are highly skewed.
- Multiple columns are correlated.
- Statistics are insufficient for the query's filtering conditions.

### Extended statistics

PostgreSQL supports extended statistics for relationships between columns.

The SQL implementation creates extended statistics using:

- `dependencies`
- `mcv`

Dependencies help represent relationships between column values.

Most-common-value statistics can help the planner understand frequently occurring combinations.

These mechanisms can improve estimates for correlated predicates.

They do not guarantee an optimal plan.

## 10. Plan Verification

Execution-plan verification compares observed query behavior with defined performance requirements.

The programming-language implementations introduce policy-based verification.

The PostgreSQL implementation provides the `verify_execution_plan` function.

### Example policy

| Rule | Threshold |
|---|---:|
| Maximum execution time | 100 ms |
| Maximum row estimation ratio | 20 |
| Maximum planning time | 50 ms |

The verification process evaluates:

1. Whether the execution time satisfies the configured limit.
2. Whether estimated and actual row counts remain within the permitted ratio.
3. Whether the plan contains significant estimation problems.
4. Whether the observations require further investigation.

A failed verification does not necessarily mean the SQL statement is incorrect.

It means the observed execution did not satisfy the selected performance policy.

### Performance verification versus correctness verification

These are different objectives.

Performance verification evaluates execution characteristics.

Correctness verification evaluates whether a statement produces the intended results.

A fast query can return incorrect results. A correct query can execute slowly.

Both dimensions require independent testing.

## 11. Python Implementation

The Python script implements a structured execution-plan analysis workflow.

### Domain model

`PlanMetrics` represents an individual plan node.

It stores:

- Node type.
- Relation name.
- Estimated rows.
- Actual rows.
- Loops.
- Estimated costs.
- Actual timing.
- Buffer measurements.
- Child nodes.

`ExecutionReport` stores the complete execution report, including planning and execution time.

### JSON plan parsing

`PlanParser` converts PostgreSQL JSON EXPLAIN output into typed Python objects.

It validates:

- JSON structure.
- Required node types.
- Numeric values.
- Loop counts.
- Child-node arrays.
- Timing values.

Invalid plans produce `PlanError`.

### Analysis

`PlanAnalyzer` evaluates row estimation differences, expensive sequential scans, repeated execution, and buffer reads.

The `verify()` method compares the observed plan against configurable thresholds.

### Benchmarking

`Benchmark` records multiple measurements and calculates:

- Minimum.
- Maximum.
- Average.
- Median.

This supports basic performance comparison across repeated runs.

### Design consideration

The script parses JSON plans rather than relying on fragile text-based plan parsing.

The demonstration uses a representative JSON structure. A real PostgreSQL JSON document can be supplied to `PlanParser.parse()`.

## 12. JavaScript Implementation

The JavaScript implementation uses an event-driven design.

### ExecutionNode

`ExecutionNode` represents an immutable execution-plan node.

It exposes calculated properties for:

- Total rows across loops.
- Accumulated node time.
- Cardinality estimation ratio.

### ExecutionPlan

`ExecutionPlan` validates and constructs the complete plan tree.

Its `nodes()` method performs iterative traversal using a stack.

This avoids relying on recursive traversal for reporting large execution trees.

### PerformancePolicy

`PerformancePolicy` contains configurable limits.

It evaluates the execution against:

- Maximum execution time.
- Maximum planning time.
- Maximum estimation ratio.
- Maximum accumulated node time.

### Event-driven processing

`PlanVerifier` extends Node.js `EventEmitter`.

It emits:

- `evaluated` when verification finishes.
- `diskRead` when a plan node reports shared-buffer reads.

This allows other application components to respond to performance observations without tightly coupling them to the verification implementation.

### Asynchronous processing

`evaluateFile()` reads a JSON execution-plan file asynchronously.

The implementation uses Node.js standard-library file handling and requires no external packages.

## 13. C++17 Implementation

The C++ implementation focuses on efficient domain modeling and predictable plan traversal.

### Domain structures

The program defines:

- `ExecutionNode`
- `QueryExecution`
- `BufferStats`
- `VerificationPolicy`
- `Finding`

An execution node owns its child nodes through STL containers.

This provides a natural representation of the execution-plan tree.

### Performance analysis

`PlanAnalyzer` traverses the plan and evaluates:

- Cardinality estimation errors.
- Repeated node execution.
- Accumulated node time.
- Sequential scan cost.
- Shared-buffer reads.

### Verification

The verification engine applies the configured performance policy.

The implementation distinguishes critical execution-time violations from diagnostic warnings.

### Benchmark processing

The `Benchmark` class calculates statistical measurements using STL algorithms.

It also validates measurements before adding them to the benchmark collection.

### Complexity

For a plan containing \(N\) nodes:

| Operation | Complexity |
|---|---|
| Plan traversal | \(O(N)\) |
| Node verification | \(O(N)\) |
| Benchmark sorting | \(O(R \log R)\) |
| Benchmark aggregation | \(O(R)\) |

Here, \(R\) represents the number of benchmark measurements.

## 14. Java 17 Implementation

The Java implementation models execution-plan analysis as an enterprise performance-governance service.

### Immutable domain records

The implementation uses Java records for:

- `BufferStats`
- `ExecutionNode`
- `QueryExecution`
- `PerformancePolicy`
- `Finding`
- `VerificationResult`

Records provide compact immutable domain objects.

Child-node collections are defensively copied using `List.copyOf()`.

### PerformanceAnalyzer

The service evaluates a query against a configured policy.

It distinguishes:

- Critical performance violations.
- Estimation warnings.
- Unexecuted plan nodes.
- Buffer-read warnings.
- Informational observations.

### PlanTraversal

An iterative traversal uses `ArrayDeque`.

This is suitable for processing execution-plan trees without depending on recursive traversal depth.

### BenchmarkService

The benchmark service maintains execution measurements and produces statistical summaries.

The implementation returns an immutable summary map.

### Enterprise applicability

The domain structure can be extended into an application-level performance monitoring service.

A service can collect PostgreSQL execution-plan observations, evaluate them against environment-specific policies, and retain the resulting verification records.

The supplied program demonstrates the analysis and policy layer rather than implementing a database connection.

## 15. PostgreSQL Implementation

The SQL script models a realistic customer-order workload.

### Relational schema

The main relations are:

| Table | Responsibility |
|---|---|
| `customers` | Customer and account information |
| `orders` | Order transactions and amounts |
| `query_benchmarks` | Execution measurements and JSON plans |
| `plan_verification_policies` | Performance thresholds |

Primary keys, foreign keys, unique constraints, and check constraints maintain relational integrity.

### Indexes

The script creates indexes for:

- Customer region and account status.
- Order customer references.
- Order dates.
- Order status and date.
- Benchmark retrieval.
- JSON execution-plan inspection.

The index definitions are workload-oriented examples.

An index should be retained only when its benefits justify its storage, maintenance, and write overhead.

### JSON execution-plan extraction

The function `extract_plan_metrics()` uses a recursive CTE.

It traverses the JSON execution-plan tree and extracts individual plan-node measurements.

It returns:

- Node type.
- Relation name.
- Estimated rows.
- Actual rows.
- Actual loops.
- Actual total time.
- Accumulated node time.
- Cardinality estimation ratio.

The function supports stored plan inspection and reporting.

### Verification function

`verify_execution_plan()` evaluates a JSON plan against two configurable requirements:

- Maximum execution time.
- Maximum row estimation ratio.

It returns separate verification results for the two checks.

The demonstration includes valid and invalid performance observations.

### Reporting

The `v_query_performance` view provides:

- Execution count.
- Average execution time.
- Average planning time.
- Median execution time.
- Worst execution time.

These measurements support basic historical performance analysis.

## 16. Safe Use of EXPLAIN ANALYZE

A critical distinction exists between analyzing a SELECT statement and analyzing a statement that changes data.

`EXPLAIN ANALYZE` executes the supplied statement.

Therefore, the following commands have different operational consequences:

| Statement | Execution consequence |
|---|---|
| EXPLAIN SELECT | Does not execute the SELECT |
| EXPLAIN ANALYZE SELECT | Executes the SELECT |
| EXPLAIN ANALYZE INSERT | Executes the INSERT |
| EXPLAIN ANALYZE UPDATE | Executes the UPDATE |
| EXPLAIN ANALYZE DELETE | Executes the DELETE |

For DML performance investigation, a transaction followed by `ROLLBACK` can prevent transactional modifications from being committed.

The SQL implementation demonstrates this approach with an UPDATE statement.

External side effects, nontransactional operations, and certain sequence-related effects require separate consideration. A rollback is not a universal mechanism for reversing every possible side effect.

Production analysis should use appropriate database permissions and a controlled environment.

## 17. Performance Investigation Workflow

A practical investigation follows this sequence:

    SQL Statement
         |
         v
    EXPLAIN
         |
         v
    Inspect Estimated Plan
         |
         v
    EXPLAIN ANALYZE
         |
         v
    Compare Estimated and Actual Rows
         |
         v
    Inspect Loops and Node Timing
         |
         v
    Examine Buffer Statistics
         |
         v
    Investigate Statistics and Indexes
         |
         v
    Apply a Controlled Change
         |
         v
    Execute Again
         |
         v
    Compare Measurements
         |
         v
    Verify Performance Requirements

The sequence avoids assuming that an index is always the correct solution.

It also encourages investigation of the actual bottleneck rather than modification based only on estimated costs.

## 18. Common Performance Problems

| Observation | Possible cause | Investigation |
|---|---|---|
| Actual rows far exceed estimated rows | Inaccurate cardinality estimation | Review statistics and data distribution |
| Actual rows far below estimated rows | Incorrect selectivity assumptions | Review predicates and statistics |
| High loops | Repeated inner-node execution | Inspect join strategy |
| Expensive sequential scan | Large table access or poor selectivity | Evaluate filtering and indexing |
| High shared reads | Significant buffer loading | Examine working set and data access |
| High planning time | Complex query or planning overhead | Examine query structure and planning behavior |
| High sort time | Large sorting workload | Examine ordering requirements and available indexes |
| Hash operation spills | Insufficient memory for the operation | Inspect memory settings and input cardinality |
| High execution time despite low estimated cost | Planner assumptions differ from actual workload | Examine estimates, runtime conditions, and plan structure |

These observations identify possible causes, not definitive diagnoses.

## 19. Benchmarking and Regression Detection

A single execution measurement is insufficient for reliable performance comparison.

Execution times can vary because of:

- Cache state.
- Concurrent database activity.
- Operating-system scheduling.
- Data volume.
- Storage latency.
- Query parameter values.
- PostgreSQL configuration.
- Background maintenance.

Repeated measurements provide a more useful picture.

The implementations calculate minimum, maximum, average, and median execution times.

For more rigorous benchmarking, measurements should use consistent data, query parameters, configuration, and concurrency conditions.

Cold-cache and warm-cache measurements should be identified separately when both matter.

A regression threshold should reflect the workload's actual performance requirements rather than an arbitrary universal limit.

## 20. Important Technical Distinctions

| Concept | What it measures |
|---|---|
| EXPLAIN | Estimated execution plan |
| EXPLAIN ANALYZE | Executed plan with actual measurements |
| Planning Time | Planning duration |
| Execution Time | Total measured execution duration |
| Actual Rows | Observed rows per loop |
| Actual Loops | Number of node executions |
| Total Actual Rows | Approximate rows across loops |
| Planner Cost | Estimated relative execution cost |
| Actual Node Time | Measured node execution timing |
| ANALYZE | Collects table statistics |
| Plan Verification | Evaluates observations against configured requirements |
| Benchmarking | Compares measurements across executions |

Two distinctions deserve particular attention.

First, `EXPLAIN ANALYZE` and `ANALYZE` are not interchangeable. The former executes a statement and reports its plan and runtime. The latter collects database statistics.

Second, a good-looking execution plan is not automatically proof of good application performance. Real workload conditions, result-transfer costs, concurrency, and repeated execution patterns also matter.

## 21. Limitations

The implementations deliberately separate execution-plan analysis from live database connectivity.

- Python demonstrates JSON plan parsing and rule-based evaluation.
- JavaScript demonstrates event-driven policy evaluation.
- C++17 demonstrates a typed plan-analysis engine.
- Java 17 demonstrates enterprise-oriented domain modeling.
- PostgreSQL provides actual execution-plan commands and relational storage for observations.

The demonstration plans in the programming-language files are representative data.

Their execution times should not be interpreted as PostgreSQL benchmark results.

The SQL verification function uses stored JSON measurements. It does not automatically execute arbitrary SQL statements or guarantee that a stored plan corresponds to the current database state.

A production monitoring system should associate each observation with query identity, execution environment, PostgreSQL version, relevant parameters, and observation time.

Performance policies should also account for workload-specific requirements.

## 22. Practical Applications

EXPLAIN ANALYZE is useful in:

- Database performance troubleshooting.
- SQL query optimization.
- Index effectiveness evaluation.
- Join-strategy investigation.
- Cardinality estimation analysis.
- Database migration validation.
- Performance regression testing.
- Application query monitoring.
- Data-intensive reporting systems.
- Database capacity planning.

The central engineering principle is to distinguish what PostgreSQL predicted from what it actually executed, interpret measurements in the context of the complete plan tree, and verify improvements using repeatable execution evidence.
