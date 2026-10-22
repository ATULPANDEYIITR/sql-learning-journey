# Window Functions Introduction

## Scope

Window functions calculate values across a related set of rows while preserving the individual rows in the result.

The central SQL structure is:

`function(...) OVER (PARTITION BY ... ORDER BY ... frame)`

The three major components have different responsibilities:

| Component | Purpose |
|---|---|
| `OVER()` | Turns an aggregate or ranking operation into a window calculation |
| `PARTITION BY` | Separates rows into independent analytical groups |
| `ORDER BY` | Defines the logical sequence used by the window calculation |
| Window frame | Defines which ordered rows participate in the calculation |

A window query therefore differs from a traditional `GROUP BY`. `GROUP BY` normally reduces several source rows into one result row per group. A window function adds analytical information to each applicable source row.

The five implementations use a common sales-analysis scenario while emphasizing different programming models.

## Window model

The sample data contains sales made by employees in Technology, Finance, and Operations.

The analytical relationship can be represented as:

`Sales`
→ `PARTITION BY department`
→ `ORDER BY sale_date, sale_id`
→ `WINDOW FRAME`
→ `ROW_NUMBER / RANK / SUM / AVG / LAG / LEAD`

For example:

`SUM(amount) OVER (PARTITION BY department ORDER BY sale_date, sale_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`

produces a running department total.

The source rows remain present. The calculation is evaluated against the window associated with each row.

## `OVER()`

`OVER()` defines the window context.

A calculation such as:

`AVG(amount) OVER ()`

calculates an average over the complete result set while retaining every source row.

Adding a partition:

`AVG(amount) OVER (PARTITION BY department_name)`

creates a separate average for every department.

No grouping operation is required to obtain the department average alongside each sale.

This distinction is important when a report needs both detail and aggregate information.

## Partitions

`PARTITION BY` divides the result into independent analytical groups.

For the sample data:

`Technology`
- Asha
- Ravi
- Asha
- Ravi

`Finance`
- Neha
- Vikram
- Neha
- Vikram

`Operations`
- Meera
- Meera

A running total partitioned by department resets when the department changes.

Partitioning does not remove rows. It establishes the boundaries within which the window calculation operates.

## Ordering

`ORDER BY` determines the logical sequence of rows inside a window.

The implementations use:

`ORDER BY sale_date, sale_id`

The secondary `sale_id` provides deterministic ordering when two rows have the same date.

Ordering is essential for calculations such as:

- running totals
- row numbers
- previous and next values
- moving averages
- ordered rankings

A window function without an appropriate ordering clause can answer a different question from the one intended.

## Window frames

A frame restricts the rows visible to a calculation for the current row.

This expression:

`ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`

creates a running frame containing all earlier rows in the partition plus the current row.

A two-row moving average can use:

`ROWS BETWEEN 1 PRECEDING AND CURRENT ROW`

For a sequence of amounts:

`100, 200, 300`

the two-row averages become:

| Current amount | Frame | Average |
|---:|---|---:|
| 100 | 100 | 100 |
| 200 | 100, 200 | 150 |
| 300 | 200, 300 | 250 |

Explicit `ROWS` frames are useful when the requirement refers to physical ordered rows.

## Ranking functions

`ROW_NUMBER()` assigns a unique sequential number.

`RANK()` gives equal values the same rank and leaves gaps after ties.

`DENSE_RANK()` gives equal values the same rank without leaving gaps.

For values:

`22000, 22000, 15000`

the results are:

| Amount | `ROW_NUMBER()` | `RANK()` | `DENSE_RANK()` |
|---:|---:|---:|---:|
| 22000 | 1 | 1 | 1 |
| 22000 | 2 | 1 | 1 |
| 15000 | 3 | 3 | 2 |

The distinction matters when selecting top performers or creating ordered reports.

The SQL implementation uses `RANK()` and `DENSE_RANK()` to make the difference explicit.

## `LAG()` and `LEAD()`

`LAG()` accesses an earlier row in the ordered window.

`LEAD()` accesses a later row.

For monthly sales:

| Month | Amount | `LAG(amount)` | `LEAD(amount)` |
|---|---:|---:|---:|
| January | 10000 | NULL | 15000 |
| February | 15000 | 10000 | 12000 |
| March | 12000 | 15000 | NULL |

These functions are useful for period-over-period analysis, detecting changes, comparing neighboring events, and identifying transitions.

The first row has no previous row, so `LAG()` returns `NULL`.

The final row has no following row, so `LEAD()` returns `NULL`.

## Python implementation

The Python script models the window-processing mechanics explicitly.

The `Sale` dataclass provides immutable domain records. Input validation checks identifiers, employee and department names, duplicate IDs, and non-negative amounts.

The implementation separates window concepts into functions:

- `row_number_by_partition()` assigns sequential positions within departments.
- `rank_by_amount()` calculates ranking by amount.
- `running_total()` maintains a cumulative department total.
- `moving_average()` implements a bounded two-row frame.
- `lag_amount()` retrieves the preceding sale.
- `lead_amount()` retrieves the following sale.

Dictionaries provide efficient lookup of calculated values by sale ID. Lists preserve ordered rows, while sets enforce duplicate-ID validation.

The Python version demonstrates how the conceptual operations behind `OVER()`, partitioning, ordering, and frames can be reproduced without a database engine.

## JavaScript implementation

The JavaScript implementation uses Node.js-compatible standard language features.

`partitionAndOrder()` creates department partitions and sorts each partition by date and ID.

`addRowNumber()` models `ROW_NUMBER()`.

`addRunningTotal()` maintains cumulative totals.

`addLagAndLead()` accesses neighboring rows through array positions.

`addMovingAverage()` constructs an explicit bounded frame for every row.

`addRank()` sorts a partition by amount and assigns SQL-style ranking semantics.

The event stream demonstrates an event-driven reporting perspective. Each analyzed row produces a `SALE_ANALYZED` event that can be consumed asynchronously.

No npm dependency is required.

Validation checks array structure, unique IDs, required text fields, numeric amounts, and valid dates.

## C++ implementation

The C++17 program treats the analysis as a repository-style analytical engine.

`RepositoryAnalytics` owns the sales collection and validates domain constraints before analysis.

The `partitions()` method creates ordered department partitions using `std::map` and `std::vector`.

`analyze()` calculates:

- row number
- rank
- running total
- bounded moving average
- previous value
- next value

`std::unordered_map` stores computed metrics by sale ID for efficient retrieval.

The moving-average implementation explicitly constructs the two-row frame. This makes the relationship between a SQL `ROWS BETWEEN 1 PRECEDING AND CURRENT ROW` frame and an indexed in-memory algorithm visible.

The implementation uses deterministic secondary ordering by sale ID.

## Java implementation

The Java 17 program uses domain-oriented design.

`Sale` is a record representing an immutable sale.

`WindowResult` is a record containing the original sale and calculated analytical values.

`WindowPolicy` defines the evaluation contract, while `DepartmentWindowPolicy` implements the department-specific analytical behavior.

Java streams are used for partition construction, while ordinary indexed loops are used where direct access to preceding and following rows is important.

This combination illustrates a practical distinction: streams are convenient for declarative collection transformations, while indexed processing is often clearer for window-frame calculations.

Validation rejects empty input, duplicate identifiers, missing fields, invalid dates, and negative amounts.

## PostgreSQL implementation

The PostgreSQL script creates a relational model consisting of:

- `departments`
- `employees`
- `sales`

Foreign keys enforce relationships between these entities.

The `sales` table uses a numeric amount with a non-negative `CHECK` constraint.

The analytical view `sale_window_analysis` exposes several window calculations:

| Expression | Purpose |
|---|---|
| `ROW_NUMBER()` | Position within a department |
| `RANK()` | Ranking with gaps after ties |
| `DENSE_RANK()` | Ranking without gaps |
| `SUM()` | Running department total |
| `AVG()` | Two-row moving average |
| `LAG()` | Previous sale amount |
| `LEAD()` | Next sale amount |
| `FIRST_VALUE()` | First ordered value in the department |
| `LAST_VALUE()` | Last ordered value using an explicit full frame |

The `LAST_VALUE()` example deliberately specifies:

`ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`

This is important because the default frame can cause `LAST_VALUE()` to return the current row's value rather than the final value of the entire partition.

The script also demonstrates CTEs for filtering ranked results and comparing individual sales with department averages.

## Window functions versus `GROUP BY`

A `GROUP BY` query such as:

`GROUP BY department_name`

returns one row per department.

A window query such as:

`SUM(amount) OVER (PARTITION BY department_name)`

retains every sale and attaches the department total to each sale.

This difference can be represented as:

| Requirement | Appropriate mechanism |
|---|---|
| One result row per department | `GROUP BY` |
| Every sale plus department total | Window `SUM()` |
| Top N rows in each department | `ROW_NUMBER()` or ranking function |
| Previous sale | `LAG()` |
| Next sale | `LEAD()` |
| Running total | Ordered window `SUM()` |
| Moving average | Window `AVG()` with a frame |

Window functions are therefore analytical extensions to row-oriented queries rather than replacements for aggregation in every situation.

## Execution considerations

Window calculations require the database to establish the partition and ordering required by the window definition.

For large datasets, sorting can become a significant part of execution cost.

The SQL model therefore uses indexes that support common access patterns, including employee/date ordering and date retrieval. An index does not guarantee that PostgreSQL will avoid sorting, so `EXPLAIN` should be used against the actual workload.

Multiple window expressions that share compatible partitioning and ordering can often be evaluated efficiently by the database executor.

A window query can still be expensive when:

- partitions are very large
- ordering requires substantial sorting
- several incompatible window orderings are requested
- the query processes a much larger source relation than necessary

Filtering source rows before a window operation can change the analytical population and therefore must be done intentionally.

## Edge cases

The implementations account for several boundary conditions.

The first row of a partition has no preceding row, so `LAG()` produces `NULL`.

The last row has no following row, so `LEAD()` produces `NULL`.

A moving frame near the beginning of a partition contains fewer rows than the maximum frame size.

Equal ranking values produce ties.

A deterministic secondary ordering is used where unique row order is required.

Empty or invalid input is rejected by the application implementations.

The PostgreSQL model rejects negative sale amounts at the database layer rather than relying only on application validation.

## Performance characteristics

For an already partitioned and ordered sequence, many window calculations can be evaluated in linear time after ordering.

If sorting is required, ordering generally contributes approximately `O(n log n)` comparison complexity for `n` rows.

The Python, JavaScript, C++, and Java implementations explicitly build or sort partitions before evaluating their window calculations.

The SQL engine determines its physical execution strategy. Query plans should be inspected with `EXPLAIN` and `EXPLAIN ANALYZE` for production workloads.

The choice of frame also affects the implementation. A bounded frame such as the previous one row can be maintained efficiently, while a poorly designed implementation that repeatedly scans a large frame can introduce unnecessary work.

## Data and result interpretation

For a department ordered by date:

`12000 → 18000 → 15000 → 22000`

the running total becomes:

`12000 → 30000 → 45000 → 67000`

The two-row moving average becomes:

`12000 → 15000 → 16500 → 18500`

The values demonstrate that the current row participates in both calculations and that the frame changes as the current row moves through the ordered partition.

The analytical result retains the original sale while adding derived information.

## Practical query design

A window expression should answer a clearly defined row-relative question.

The following decisions should be explicit:

- What rows belong to the partition?
- What establishes their order?
- Is the order deterministic?
- Does the calculation require a frame?
- Should ties share a rank?
- Should rank gaps exist after ties?
- Is the result expected to preserve every source row?
- Should `NULL` occur at partition boundaries?

These decisions prevent common errors such as calculating a running total across unrelated departments, selecting an unstable top-N result, or misunderstanding the behavior of `LAST_VALUE()`.

## Implemented relationship

The five source files use different implementation perspectives but preserve the same conceptual structure:

`Source rows`
→ `Partition`
→ `Order`
→ `Frame`
→ `Window calculation`
→ `Enriched rows`

Python emphasizes explicit data structures and validation.

JavaScript emphasizes event-driven processing and asynchronous result handling.

C++ emphasizes a strongly structured analytical engine with explicit partition and frame processing.

Java emphasizes immutable domain types, policy interfaces, validation, and enterprise-style service boundaries.

PostgreSQL expresses the same analytical model directly through `OVER()`, partitions, orderings, frames, ranking functions, navigation functions, CTEs, constraints, views, and transactional operations.

The implementations therefore demonstrate window functions as a relational analytical mechanism while showing how the underlying concepts can be represented in general-purpose programming environments.
