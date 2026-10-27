# FIRST_VALUE and LAST_VALUE: First and Last Observations with Window Frames

## Scope

This project implements SQL window-value semantics across Python, JavaScript, C++17, Java 17, and PostgreSQL.

The central subject is the distinction between:

- `FIRST_VALUE`
- `LAST_VALUE`
- the current-row window frame
- the full-partition frame
- bounded `ROWS` frames
- partitioning
- ordering
- deterministic first and last observations

The examples use repository deployment observations. Each repository has a chronological sequence of deployment counts. The repository is the partition, observation time is the ordering key, and deployment count is the value evaluated by the window functions.

The five implementations intentionally use different engineering approaches while representing the same core semantics.

## Conceptual Model

A window function evaluates rows without collapsing them into one aggregate row.

For a partition ordered by time:

`Repository → ordered observations → window frame → FIRST_VALUE / LAST_VALUE`

For example:

`payment-api: 4 → 7 → 11`

`FIRST_VALUE` returns `4` for every row when the frame includes the first observation.

`LAST_VALUE` requires more care. If the ordered frame ends at `CURRENT ROW`, its last value is the current observation:

`4 → 7 → 11`

To obtain `11` for every row, the frame must extend to `UNBOUNDED FOLLOWING`.

## FIRST_VALUE

`FIRST_VALUE(value)` returns the value from the first row in the window frame according to the window's `ORDER BY` clause.

For a repository partition ordered by `observed_at`:

| Observation | Value | FIRST_VALUE |
|---|---:|---:|
| 09:00 | 4 | 4 |
| 11:00 | 7 | 4 |
| 13:00 | 11 | 4 |

The first observation remains stable as later rows are evaluated.

The ordering expression is important. Without a meaningful order, "first" has no useful business interpretation.

## LAST_VALUE

`LAST_VALUE` is strongly affected by the frame definition.

With an ordered window whose frame terminates at the current row, the current row is the last row in the frame.

| Observation | Value | LAST_VALUE with current-row frame |
|---|---:|---:|
| 09:00 | 4 | 4 |
| 11:00 | 7 | 7 |
| 13:00 | 11 | 11 |

This differs from the common requirement of finding the final observation of the complete partition.

A full-partition frame explicitly includes rows through the end:

`ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`

The result then becomes:

| Observation | Value | LAST_VALUE over full partition |
|---|---:|---:|
| 09:00 | 4 | 11 |
| 11:00 | 7 | 11 |
| 13:00 | 11 | 11 |

The distinction between function and frame is the central technical issue represented by this project.

## Bounded Window Frames

A bounded frame can describe a local observation history.

The implementations use the equivalent conceptual frame:

`ROWS BETWEEN 2 PRECEDING AND CURRENT ROW`

For the sequence `4, 7, 11`, the frames are:

`4`

`4, 7`

`4, 7, 11`

The last value in each frame is therefore the current observation. The bounded frame becomes more useful when the frame is combined with functions whose result depends on preceding rows, but it is still valuable here for showing exactly what `LAST_VALUE` considers its frame.

## ROWS Versus Partition

A partition defines which rows belong to the same analytical group.

A frame defines which subset of that partition is visible for the current row.

These concepts should not be treated as interchangeable.

For the example:

`PARTITION BY repository`

creates one logical sequence per repository.

`ORDER BY observed_at`

defines chronological position.

`ROWS BETWEEN ...`

defines the rows visible to the current calculation.

This produces a hierarchy:

`Partition → Ordering → Frame → Window-value evaluation`

## Python Implementation

The Python script uses:

- `dataclass` for immutable observation records
- dictionaries for repository partitioning
- lists for ordered observations
- explicit validation
- exceptions for invalid values
- assertions as executable semantic checks
- bounded-frame evaluation
- separate functions for different `LAST_VALUE` semantics

The script models the default current-row behavior separately from the full-partition behavior so the distinction is observable rather than hidden.

`first_value()` stores the first value encountered for each repository.

`last_value_default_frame()` models an ordered frame ending at the current row.

`last_value_full_partition()` determines the final value of each repository and associates it with every row.

`moving_last_value()` models a bounded preceding-row frame.

The implementation has no external dependencies.

## JavaScript Implementation

The JavaScript implementation uses Node.js standard-library functionality and a deliberately event-driven reporting layer.

The domain model is represented by an immutable `Observation` class. Validation rejects invalid repository names, metrics, dates, and negative values.

`Map` objects represent repository partitions.

The implementation separates:

- validation and ordering
- partition construction
- first-value evaluation
- default-frame last-value evaluation
- full-partition last-value evaluation
- bounded-frame evaluation

`WorkflowReporter` extends `EventEmitter` and emits structured reports asynchronously. This provides a complementary event-driven perspective rather than reproducing the Python structure mechanically.

No npm packages are required.

## C++17 Implementation

The C++ program models repository observations using a struct and evaluates the window semantics through explicit partition indexes.

The implementation uses:

- `std::vector` for observations and results
- `std::map` for repository partitions
- STL sorting
- exception handling
- immutable-style result construction
- explicit invariant checks

The partition index map allows the evaluator to identify the first and final row of each repository efficiently after ordering.

The program reports four values:

- `FIRST_VALUE`
- default-frame `LAST_VALUE`
- full-partition `LAST_VALUE`
- bounded-frame `LAST_VALUE`

The implementation also validates that the expected first and final values remain stable.

## Java 17 Implementation

The Java implementation models the problem as a small enterprise-style domain service.

`Observation` is a Java record with constructor validation.

`MetricType` is an enum that constrains the metric domain.

`WindowPolicy` defines the evaluation contract.

`RepositoryWindowPolicy` performs ordering, partitioning, frame evaluation, and result construction.

`WindowEvaluationException` represents domain-level evaluation failures.

`MergeEligibilityReport` is used as the reporting boundary for validation and presentation. Its responsibility is deliberately limited to consuming evaluated results rather than implementing the window algorithm itself.

The implementation uses Java streams for ordering and immutable `List` results where appropriate.

## PostgreSQL Relational Model

The PostgreSQL implementation models:

`repositories → observations`

Each observation contains:

- repository
- timestamp
- metric name
- metric value

Database constraints enforce:

- primary keys
- foreign-key integrity
- unique repository names
- unique observation identity for a repository, timestamp, and metric
- non-negative metric values

The composite index on `(repository_id, observed_at)` supports the common partition-and-order access pattern.

## PostgreSQL FIRST_VALUE

The PostgreSQL implementation uses:

`FIRST_VALUE(metric_value) OVER (PARTITION BY repository_id ORDER BY observed_at)`

This produces the earliest ordered observation for each repository.

The query retains every observation row instead of collapsing the data.

## PostgreSQL LAST_VALUE

The script explicitly demonstrates both forms.

The first form uses the ordered window without an explicit full-partition frame. Its frame ends at the current row, so the result is the current observation.

The second form uses:

`ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`

This makes the final row of the complete partition visible to every row.

This explicit frame is the reliable expression when the requirement is "the final observation in this entire ordered partition."

## Transactional Validation

The PostgreSQL script also demonstrates transactional behavior.

A valid insertion is committed.

A separate transaction deliberately detects an invalid negative metric and raises an exception before the transaction is committed. The transaction is rolled back.

The table-level `CHECK` constraint independently prevents negative metric values from becoming valid database state.

This illustrates the difference between application-level validation and database-level enforcement.

## Query and Performance Considerations

Window evaluation requires an ordering operation when suitable ordering data is not already available.

The source implementations therefore use approximately:

`O(n log n)` time for ordering

`O(n)` time for the subsequent window evaluation

Memory consumption is generally `O(n)` for materialized partitions and result sets.

The PostgreSQL index on `(repository_id, observed_at)` is specifically aligned with the partitioning and ordering pattern. Indexes should be selected based on actual query patterns rather than added indiscriminately.

A full-partition `LAST_VALUE` can require access to the end of the ordered partition. This is one reason explicit frame semantics should be considered together with data volume and execution plans.

## Edge Cases

The implementations address several important edge cases:

- empty observation collections
- empty repository names
- empty metric names
- invalid timestamps
- negative metric values
- negative frame sizes
- repositories containing only one observation
- multiple independent repository partitions
- bounded frames at the beginning of a partition
- explicit full-partition frames
- deterministic ordering by observation timestamp

A single-row partition has the same value for both its first and final observation.

## Ordering and Determinism

`FIRST_VALUE` and `LAST_VALUE` depend on ordering.

If multiple observations have identical ordering keys, peer-row behavior can affect results, especially when the frame type is `RANGE` rather than `ROWS`.

For production analytical queries, an ordering key should normally be deterministic. If timestamps are not unique, a unique observation identifier can be added as a secondary ordering expression.

For example, a robust conceptual ordering is:

`ORDER BY observed_at, observation_id`

This removes ambiguity when two observations share the same timestamp.

## ROWS and RANGE

`ROWS` counts physical rows relative to the current row.

A bounded `ROWS` frame such as:

`ROWS BETWEEN 2 PRECEDING AND CURRENT ROW`

means that at most two physical preceding rows plus the current row participate.

`RANGE` is value-oriented and groups peer rows according to the ordering expression.

The distinction matters when ordering values are duplicated. A query that requires exact row positions should use `ROWS` deliberately rather than relying on peer-sensitive behavior.

## Relationship Between the Implementations

| Implementation | Primary perspective | Key mechanism |
|---|---|---|
| Python | Analytical simulation | Dictionaries and explicit frame evaluation |
| JavaScript | Event-driven processing | Maps, immutable records, events |
| C++17 | Algorithmic engine | STL containers and indexed partitions |
| Java 17 | Domain service | Records, policy interface, immutable results |
| PostgreSQL | Relational execution | Window functions, frames, constraints, indexes |

All five implementations represent the same semantic distinction but do not mechanically translate the same source structure.

## Security Considerations

The examples operate entirely on controlled in-memory data or fixed SQL statements.

The source implementations do not:

- execute shell commands
- dynamically evaluate source code
- load untrusted modules
- construct dynamic SQL from user input
- disable validation
- bypass database constraints

The PostgreSQL schema uses database constraints as a second enforcement layer rather than relying solely on application validation.

For a production system accepting external observations, input validation, authorization, parameterized SQL, audit logging, and access controls would remain separate application responsibilities.

## Practical Interpretation

For repository activity data, the functions can answer different questions:

`FIRST_VALUE`:

"What was the first recorded deployment count in this repository partition?"

`LAST_VALUE` with a current-row frame:

"What is the last value visible in the frame ending at this observation?"

`LAST_VALUE` with a full-partition frame:

"What is the final recorded deployment count for this repository?"

A bounded frame:

"What is the last observation inside this explicitly bounded frame?"

These questions are similar in wording but have different analytical meanings.

## Implemented Workflow

The complete workflow represented by the project is:

`Repository`
→ `Chronological Observations`
→ `PARTITION BY`
→ `ORDER BY`
→ `Window Frame`
→ `FIRST_VALUE / LAST_VALUE`
→ `Validation`
→ `Reporting`

The key design principle is that the function and the frame must be considered together. `LAST_VALUE` does not inherently mean "last row of the entire partition." It means the value from the last row of the current window frame.

## Limitations

The examples use deployment observations as a realistic analytical domain rather than connecting to a live repository platform.

The Python, JavaScript, C++17, and Java 17 implementations simulate database window semantics in application code. Their frame behavior is intentionally explicit so that the underlying concepts remain visible.

The PostgreSQL implementation is the authoritative relational representation because PostgreSQL performs the actual SQL window-function evaluation.

The examples focus on `FIRST_VALUE`, `LAST_VALUE`, ordering, and frames. They do not attempt to implement every SQL window function or every possible frame type.
