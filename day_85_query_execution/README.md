# Query Execution: SQL Parsing, Planning, Optimization and Execution

## 1. Technical Scope

Query execution is the database process that converts a declarative SQL statement into an executable sequence of operations and produces the requested result.

SQL describes the required result rather than prescribing the exact operations used to retrieve it. The database management system determines how to access data, apply conditions, combine relations, order records, and return results.

A relational query-processing pipeline can be represented as:

SQL Statement
    |
    v
Lexical Analysis
    |
    v
Parsing
    |
    v
Semantic Analysis
    |
    v
Logical Query Plan
    |
    v
Query Optimization
    |
    v
Physical Query Plan
    |
    v
Query Execution
    |
    v
Result Set and Execution Statistics

The five implementations examine different engineering perspectives of this pipeline. Python implements a compact SQL-processing simulator, JavaScript focuses on event-driven execution and access-path selection, C++17 implements an efficient typed execution engine, Java 17 models enterprise query-processing services, and PostgreSQL demonstrates actual database execution mechanisms.

## 2. SQL Parsing

### 2.1 Lexical Analysis

Lexical analysis converts a SQL statement into a sequence of tokens.

For example:

`SELECT employee_name, salary FROM employees WHERE salary > 90000`

The lexer identifies:

| Token | Classification |
|---|---|
| SELECT | Keyword |
| employee_name | Identifier |
| , | Separator |
| salary | Identifier |
| FROM | Keyword |
| employees | Identifier |
| WHERE | Keyword |
| salary | Identifier |
| > | Comparison operator |
| 90000 | Numeric literal |

Tokens provide the input to the parser.

The Python implementation uses a regular-expression-based lexer that recognizes keywords, identifiers, strings, numbers, operators, symbols, and comments. It reports invalid characters and their positions.

The implementation deliberately supports a restricted SQL grammar rather than attempting to parse the complete SQL language.

### 2.2 Parsing and Abstract Syntax Trees

Parsing determines whether a token sequence follows the grammar of the supported SQL language.

The Python parser uses recursive-descent methods to process:

- SELECT lists
- FROM clauses
- WHERE expressions
- AND and OR operators
- NOT expressions
- Parenthesized conditions
- Comparison operators
- ORDER BY
- LIMIT

Operator precedence is important.

For example:

`A OR B AND C`

is interpreted as:

`A OR (B AND C)`

because AND has higher precedence than OR.

The parser constructs an expression tree instead of directly executing conditions.

A comparison expression can be represented as:

COMPARE
    |
    +-- COLUMN: salary
    |
    +-- OPERATOR: >
    |
    +-- LITERAL: 90000

This representation separates SQL syntax from execution behavior.

### 2.3 Semantic Analysis

A syntactically valid query can still be invalid.

Consider:

`SELECT unknown_column FROM employees`

The SQL structure is valid, but the referenced column may not exist.

Semantic analysis resolves:

- Table names
- Column names
- Data types
- Operators
- Function references
- Expression compatibility

The Python optimizer validates table and column references before constructing the execution plan.

The Java implementation uses catalog metadata and typed column definitions to reject incompatible expressions.

PostgreSQL performs substantially more extensive semantic analysis, including relation resolution, operator resolution, type coercion, privileges, and function resolution.

## 3. Logical Query Planning

A logical query plan represents the relational operations required to produce a result without committing to specific physical access methods.

The main relational operators include:

| Operator | Purpose |
|---|---|
| Scan | Read records from a relation |
| Selection | Retain records satisfying a predicate |
| Projection | Select required attributes |
| Join | Combine related relations |
| Sort | Establish ordering |
| Aggregate | Calculate grouped results |
| Limit | Restrict the number of returned rows |

A query such as:

`SELECT employee_name, salary FROM employees WHERE department_id = 1`

can be represented as:

PROJECT(employee_name, salary)
    |
    v
FILTER(department_id = 1)
    |
    v
SCAN(employees)

The logical plan specifies what must happen. It does not necessarily specify how the database reads the underlying records.

The Python implementation represents logical operations through `PlanNode`, `Scan`, `Filter`, `Project`, `Sort`, and `Limit`.

The Java implementation introduces explicit logical plan types through records implementing the `PlanNode` interface.

The JavaScript implementation separates logical planning from physical access-path selection.

## 4. Query Optimization

Query optimization identifies an execution strategy expected to provide acceptable performance while preserving query semantics.

The optimizer evaluates alternative execution plans using database statistics and cost estimates.

### 4.1 Cost-Based Optimization

A cost-based optimizer estimates the resources required by candidate plans.

Common considerations include:

- Number of rows
- Number of distinct values
- Predicate selectivity
- Index availability
- Data distribution
- Table and index pages
- Join cardinality
- Sorting requirements
- Memory availability
- I/O operations
- CPU processing

A simplified cost model is:

`Total Cost = I/O Cost + CPU Cost + Startup Cost`

The model used in the JavaScript and C++ implementations is intentionally simplified:

| Operation | Illustrative cost |
|---|---:|
| Sequential scan startup | 0 |
| Sequential scan per row | 1.0 |
| Index scan startup | 2.0 |
| Index lookup per matching row | 0.2 |

These values are simulation parameters, not PostgreSQL cost constants.

The JavaScript optimizer compares sequential and indexed access costs. The C++ implementation performs a similar comparison using table indexes and candidate counts.

The Java implementation estimates selectivity using a simplified equality-predicate assumption.

Real database optimizers use substantially richer statistical information.

### 4.2 Predicate Pushdown

Predicate pushdown moves filtering operations closer to the data source.

An unoptimized conceptual plan might perform:

PROJECT
    |
    v
FILTER
    |
    v
TABLE SCAN

The optimizer attempts to evaluate applicable predicates during or near the scan.

Benefits include:

- Fewer records passed to subsequent operators
- Reduced memory consumption
- Lower processing overhead
- Less data transferred between execution stages
- Better opportunities for index access

Predicate pushdown must preserve semantics.

For example, moving a predicate across an outer join without accounting for NULL-extended rows can change the query result.

PostgreSQL can push restrictions into scans and other suitable plan nodes when the transformation is valid.

### 4.3 Projection Pushdown

Projection pushdown reduces the number of columns carried through the execution pipeline.

Consider:

`SELECT employee_name FROM employees`

Reading and processing every column is unnecessary if no other operation requires them.

Projection pushdown can reduce:

- Memory usage
- Tuple processing overhead
- Data movement
- Disk I/O in suitable access paths

The optimizer must retain columns needed by filters, joins, grouping, and sorting even when those columns are absent from the final SELECT list.

The Python and Java implementations perform sorting before the final projection for this reason.

### 4.4 Constant and Expression Simplification

Optimizers can simplify expressions before execution.

Examples include:

- Constant arithmetic evaluation
- Removal of redundant conditions
- Boolean simplification
- Elimination of unnecessary operations
- Simplification of equivalent predicates

Such transformations must account for SQL NULL semantics, data types, and potentially volatile functions.

The implementations keep expression evaluation explicit and reject unsupported expressions rather than silently changing their meaning.

## 5. Physical Query Planning

A physical plan selects concrete algorithms and access methods.

The same logical operation can have different physical implementations.

### 5.1 Sequential Scan

A sequential scan reads table pages and evaluates applicable conditions.

Its approximate processing complexity is:

`O(N)`

where N represents the number of scanned records.

Sequential scans can be efficient when:

- A substantial proportion of records is required.
- The table is relatively small.
- An appropriate index does not exist.
- Reading the table sequentially is cheaper than performing many index lookups.

An index is not automatically faster than a sequential scan.

### 5.2 Index Scan

An index scan uses an index to identify matching records.

For a selective equality condition:

`SELECT * FROM employees WHERE employee_id = 10`

a suitable index can identify a small number of candidate records without scanning the entire relation.

A simplified lookup model is:

`O(log N + K)`

where K is the number of matching records, assuming a suitable tree-based index.

Actual performance depends on index height, cache residency, page access, heap visibility, and the number of matching records.

The JavaScript implementation creates hash-based in-memory indexes for equality predicates. The C++ implementation uses ordered maps for indexed values.

These structures demonstrate access-path selection but are not substitutes for production B-tree indexes.

### 5.3 Index-Only Scans

An index-only scan retrieves required values from an index without fetching corresponding heap tuples when the index contains the required attributes and PostgreSQL's visibility information permits it.

This can reduce heap access.

PostgreSQL may still need heap visibility checks when the visibility map does not establish that relevant pages are all-visible.

### 5.4 Join Algorithms

Relational joins combine rows using matching conditions.

Three important physical join algorithms are:

| Algorithm | Typical application |
|---|---|
| Nested loop join | Small outer input with efficient inner lookup |
| Hash join | Equality joins over suitable input sizes |
| Merge join | Inputs available in compatible sorted order |

**Nested loop join**

For each row from the outer relation, the executor searches the inner relation.

Without an efficient inner access path, processing can approach `O(N × M)`.

**Hash join**

The executor builds a hash table from one input and probes it using the other input.

Its expected processing cost is approximately `O(N + M)` under suitable conditions.

Memory limitations can cause batching and temporary disk I/O.

**Merge join**

The executor processes compatible ordered inputs and advances through them while comparing join keys.

Its main advantage is efficient processing when useful ordering already exists or can be obtained economically.

PostgreSQL selects among these strategies using its cost model.

## 6. Query Execution

The execution engine runs the selected physical plan.

A typical execution sequence is:

1. Initialize plan nodes.
2. Open required relations and indexes.
3. Retrieve candidate tuples.
4. Apply applicable predicates.
5. Execute join operations.
6. Perform aggregation where required.
7. Sort rows when necessary.
8. Apply limits.
9. Return rows to the client.
10. Release execution resources.

Database execution is commonly implemented using iterator-style execution, also called the Volcano model.

A plan node requests tuples from its child node and processes them as required.

The Python implementation uses a simplified list-based execution model. Each node receives rows from its child and returns its own output.

The JavaScript implementation processes candidates asynchronously and periodically yields control to the Node.js event loop.

The C++ implementation uses typed values, STL containers, and direct candidate-position access.

The Java implementation models execution through service and plan objects with explicit metadata validation.

PostgreSQL uses a sophisticated executor with plan-node state, tuple slots, expression evaluation, memory contexts, and resource-management mechanisms.

## 7. SQL NULL Semantics

SQL uses three-valued logic:

- TRUE
- FALSE
- UNKNOWN

UNKNOWN commonly results from comparisons involving NULL.

For example:

`NULL = 10`

does not evaluate to TRUE or FALSE. It evaluates to UNKNOWN.

A WHERE clause retains only rows for which its condition evaluates to TRUE.

Consequently:

`SELECT * FROM employees WHERE department_id = NULL`

does not return records with NULL department identifiers.

The appropriate SQL condition is:

`department_id IS NULL`

The Python and JavaScript implementations explicitly handle NULL comparisons. The C++ implementation rejects NULL comparison candidates from matching, which is sufficient for its supported WHERE behavior but does not implement the complete three-valued Boolean expression system.

## 8. Sorting, LIMIT and Execution Ordering

Sorting is a potentially expensive operation.

For N records, comparison-based sorting typically requires:

`O(N log N)`

A query using ORDER BY may require the database to process and sort qualifying records before returning them.

LIMIT restricts the number of returned rows.

For example:

`SELECT employee_name FROM employees ORDER BY salary DESC LIMIT 5`

The database may use an appropriate ordered index, a top-N sorting strategy, or a complete sort depending on the physical plan.

LIMIT does not automatically eliminate the cost of scanning and sorting all qualifying records.

Ordering must also account for NULL placement and sort direction.

The Python implementation performs stable multi-column sorting. The JavaScript implementation supports multiple sort specifications. C++ and Java demonstrate ordered execution for their restricted query models.

## 9. PostgreSQL Query Execution

The PostgreSQL implementation uses actual database functionality rather than a simulated SQL engine.

Its primary objects are:

| Database object | Purpose |
|---|---|
| `departments` | Department master records |
| `employees` | Employee records and salary information |
| `projects` | Project information |
| `employee_projects` | Employee-project assignments |
| `query_execution_log` | Execution monitoring records |
| `query_plan_snapshots` | Stored plan documents |
| `department_execution_report` | Aggregated reporting view |

### 9.1 EXPLAIN

`EXPLAIN` displays the execution plan selected by PostgreSQL without executing the statement.

Important plan information includes:

- Node type
- Estimated startup cost
- Estimated total cost
- Estimated row count
- Estimated row width
- Scan and join methods

### 9.2 EXPLAIN ANALYZE

`EXPLAIN ANALYZE` executes the statement and reports actual execution measurements.

Important fields include:

| Field | Meaning |
|---|---|
| Cost | Planner-estimated resource cost |
| Rows | Estimated or actual row count |
| Width | Estimated average row width |
| Actual Time | Observed execution time |
| Loops | Number of node executions |
| Buffers | Buffer access information |
| Planning Time | Time spent generating the plan |
| Execution Time | Time spent executing the statement |

A difference between estimated and actual row counts can indicate inaccurate cardinality estimates.

Such discrepancies may lead to poor join or access-path choices.

`EXPLAIN ANALYZE` should be used carefully with statements that modify data because those statements are actually executed.

### 9.3 Database Statistics

PostgreSQL collects statistics used by its planner.

`ANALYZE` updates statistics for relations.

Statistics help estimate:

- Distinct-value counts
- Value distributions
- Most common values
- Histograms
- NULL fractions
- Data correlation

The planner's quality depends partly on the quality and freshness of these statistics.

### 9.4 Common Table Expressions

A Common Table Expression provides a named intermediate query expression.

PostgreSQL can inline suitable CTEs, allowing optimization across their boundaries.

A `MATERIALIZED` CTE creates an optimization boundary and stores an intermediate result for reuse within the statement.

Materialization can avoid repeated computation but may prevent beneficial predicate pushdown.

The PostgreSQL script compares ordinary and materialized CTE behavior through execution plans.

### 9.5 Prepared Statements

Prepared statements separate SQL structure from parameter values.

The example prepares a department-and-salary query and executes it with different parameters.

Benefits include:

- Reduced repeated parsing overhead
- Parameterized execution
- Better separation between SQL structure and input data
- Protection against SQL injection when values are bound correctly

PostgreSQL may choose custom or generic plans depending on the prepared statement and its execution history.

## 10. Implementation Architecture

### Python

The Python implementation provides a compact end-to-end query-processing pipeline.

| Component | Responsibility |
|---|---|
| `Lexer` | Token generation |
| `Parser` | SQL grammar processing |
| `Expression` | Expression tree |
| `Table` | In-memory relation |
| `Catalog` | Table registration |
| `Optimizer` | Schema validation and plan construction |
| `Scan` | Table retrieval |
| `Filter` | Predicate evaluation |
| `Sort` | Record ordering |
| `Limit` | Result restriction |
| `Project` | Column selection |
| `QueryEngine` | Execution orchestration |

Its primary educational contribution is the separation between parsing, logical representation, planning, and execution.

The grammar intentionally excludes joins, aliases, subqueries, aggregates, functions, and transaction processing.

### JavaScript

The JavaScript implementation emphasizes asynchronous execution and event-driven architecture.

Its principal components are:

| Component | Responsibility |
|---|---|
| `TableStore` | Relation storage and index construction |
| `Predicate` | SQL-style condition evaluation |
| `QueryRequest` | Validated query representation |
| `LogicalPlanner` | Logical plan construction |
| `CostOptimizer` | Access-path selection |
| `ExecutionEngine` | Asynchronous execution |
| `PreparedStatementCache` | LRU cache simulation |

Execution events expose different stages:

- `query:start`
- `plan:logical`
- `plan:physical`
- `execution:scan`
- `query:complete`
- `query:error`

The execution engine also demonstrates concurrency limits, cancellation signals, periodic event-loop yielding, and structured failure reporting.

The LRU cache is a simplified prepared-query representation cache. It does not implement PostgreSQL's complete prepared-statement planning or parameter-binding mechanisms.

### C++17

The C++ implementation focuses on typed data representation and efficient execution.

Its architecture includes:

- `Value` as a variant-based data type.
- `Row` as a column-value mapping.
- `Predicate` for comparison evaluation.
- `Table` for relational storage and index construction.
- `QueryOptimizer` for access-path selection.
- `QueryExecutor` for execution orchestration.
- `ExecutionStats` for performance measurements.

The implementation uses ordered maps for equality indexes and vectors for candidate positions.

The design provides direct access to indexed candidates without constructing a complete copy of the relation.

The supported query model is intentionally restricted to a single-table predicate, projection, ordering, and limit.

### Java 17

The Java implementation emphasizes enterprise-oriented separation of responsibilities.

It uses:

- Records for immutable domain values.
- Enums for data types, operators, access paths, and states.
- Interfaces for logical plan abstraction.
- Catalog metadata for schema validation.
- Dedicated optimization and execution services.
- Immutable result structures.
- An LRU prepared-plan cache.
- Atomic execution counters.
- Explicit resource-limit exceptions.

The architecture separates metadata from physical table data.

This is important because enterprise query processing must reason about schema, available indexes, estimated cardinality, permissions, and execution resources without treating all information as the same object.

The model uses a simplified single-column predicate and does not implement a complete relational optimizer.

### PostgreSQL

The PostgreSQL script demonstrates production database features.

It includes:

- Relational schema definitions
- Referential integrity
- Unique and check constraints
- B-tree indexes
- Partial indexes
- Covering indexes
- Reporting views
- Stored functions
- Stored procedures
- Triggers
- Common Table Expressions
- Prepared statements
- Transactions
- Query-plan snapshots
- Execution monitoring
- EXPLAIN diagnostics

Unlike the in-memory implementations, PostgreSQL uses its actual planner and executor.

## 11. Query Performance and Complexity

The following table describes simplified algorithmic characteristics.

| Operation | Typical complexity |
|---|---|
| Sequential scan | O(N) |
| Hash-based equality lookup | Expected O(1) |
| Balanced-tree index lookup | O(log N) |
| Projection | O(N × P) |
| Predicate evaluation | O(N × E) |
| Comparison sorting | O(N log N) |
| Nested loop join | O(N × M) without efficient lookup |
| Hash join | Expected O(N + M) |
| Merge join | O(N + M) for ordered inputs |
| LRU cache lookup | Expected O(1) |

N and M represent relation sizes, P represents projected columns, and E represents predicate evaluation complexity.

Actual database costs are influenced by physical storage, memory, caching, data distribution, concurrency, and execution-plan choices.

## 12. Correctness, Failure Handling and Security

Query processing must preserve the meaning of the SQL statement while operating within database resource and security constraints.

The implementations demonstrate several relevant controls.

### Validation

- Reject malformed SQL.
- Reject unknown tables.
- Reject unknown columns.
- Validate comparison operators.
- Validate projection definitions.
- Validate sort specifications.
- Validate numeric limits.
- Check row schemas and data types.

### Failure handling

- Report lexer and parser errors.
- Reject invalid execution plans.
- Detect missing tables.
- Reject invalid predicates.
- Handle empty result sets.
- Handle zero-row limits.
- Enforce execution resource limits.
- Report cancelled and failed queries.

### Security

Production query-processing systems must also enforce:

- Authentication
- Authorization
- Row-level security
- Schema-level permissions
- Parameterized query execution
- Safe identifier handling
- Resource quotas
- Statement timeouts
- Connection limits
- Audit logging

A syntactically valid query must not automatically be considered authorized.

The PostgreSQL schema demonstrates relational integrity and parameterized prepared statements. It does not replace PostgreSQL's built-in privilege system or a complete application authorization layer.

## 13. Important Limitations

The Python, JavaScript, C++17, and Java 17 programs are educational query-processing models, not complete SQL database servers.

They do not implement:

- Full SQL grammar
- Multiple-table joins across all supported query forms
- Subqueries
- Correlated expressions
- Aggregate execution engines
- Window-function execution engines
- Disk-based storage
- Buffer pools
- Write-ahead logging
- MVCC
- Lock management
- Distributed query execution
- Parallel query execution
- Full transaction processing
- Complete SQL type coercion
- Cost-based join-order enumeration

The PostgreSQL script demonstrates these capabilities through an actual relational database where supported by PostgreSQL.

The simplified cost models should not be used to predict real production database performance.

## 14. Engineering Distinctions

The following distinctions are essential when analyzing query execution:

| Concept | Meaning |
|---|---|
| Parsing | Determines SQL syntactic structure |
| Semantic analysis | Resolves names, types, operators, and validity |
| Logical planning | Represents required relational operations |
| Optimization | Selects a suitable execution strategy |
| Physical planning | Chooses concrete access and processing algorithms |
| Execution | Runs the physical plan |
| EXPLAIN | Displays a planned execution strategy |
| EXPLAIN ANALYZE | Executes the statement and measures actual behavior |
| Statistics | Describe data distributions and cardinality |
| Index | Provides an alternative data-access structure |
| Predicate pushdown | Moves applicable filtering closer to data access |
| Projection pushdown | Reduces unnecessary column processing |
| Prepared statement | Separates SQL structure from parameter values |
| Query cache | Reuses selected query-related information |

These are related stages and mechanisms, but they are not interchangeable.

A query can be parsed successfully and still fail semantic analysis. A valid logical plan can have multiple physical implementations. A physically valid plan can perform poorly because of inaccurate estimates or changing data distributions.

The quality of query execution therefore depends on the interaction between SQL semantics, catalog metadata, optimizer decisions, physical storage, execution algorithms, and runtime resource conditions.
