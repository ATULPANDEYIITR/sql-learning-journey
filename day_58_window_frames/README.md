# Window Frames: ROWS, RANGE, and GROUPS

## Purpose

This project models SQL window-frame semantics through five independent implementations. The central distinction is:

- `ROWS` measures physical rows in the ordered result.
- `RANGE` measures distance in the `ORDER BY` value domain.
- `GROUPS` measures peer groups formed by equal `ORDER BY` values.

A window function has a partition, an ordering, and an optional frame. The frame determines which rows contribute to the calculation for the current row.

A useful conceptual model is:

Repository-style data processing is not required here. The domain is a sales stream where the same ordered data is evaluated under different frame definitions.

## Frame Model

The basic relationship is:

`Partition → ORDER BY → Peer Groups → Frame Boundary → Window Calculation`

For a current row, the frame may be interpreted in three different ways.

| Frame type | Boundary unit | Duplicate ORDER BY values | Typical use |
|---|---|---|---|
| `ROWS` | Physical rows | Each row is counted separately | Moving row totals |
| `RANGE` | ORDER BY value | Rows inside the value interval participate | Time/value windows |
| `GROUPS` | Peer groups | Equal ORDER BY values form one group | Period-based or category-based windows |

## ROWS

`ROWS` uses physical position after ordering.

For:

`ROWS BETWEEN 1 PRECEDING AND CURRENT ROW`

the frame contains the current row and at most one immediately preceding row.

With amounts:

| Row | Amount | Frame |
|---:|---:|---|
| 1 | 100 | 100 |
| 2 | 200 | 100 + 200 |
| 3 | 300 | 200 + 300 |
| 4 | 400 | 300 + 400 |

Duplicate ordering values do not automatically become a single peer group for `ROWS`.

This makes `ROWS` appropriate when the requirement is explicitly record-oriented, such as a rolling calculation over the previous three records.

A deterministic secondary ordering is important when physical row position affects the result. The PostgreSQL implementation therefore uses `sale_date, sale_id` for row-oriented examples.

## RANGE

`RANGE` evaluates the `ORDER BY` value itself.

A date-based expression such as:

`RANGE BETWEEN INTERVAL '2 days' PRECEDING AND CURRENT ROW`

includes rows whose ordering dates fall within the two-day interval ending at the current date.

For numeric ordering, a frame such as:

`RANGE BETWEEN 200 PRECEDING AND CURRENT ROW`

includes values from `current_value - 200` through `current_value`.

The important distinction is that `RANGE` does not mean "the previous 200 rows." It means an interval in the ordering domain.

This makes `RANGE` useful for time-based reporting, price bands, measurement windows, and other calculations where distance in the ordered value is meaningful.

## GROUPS

`GROUPS` uses peer groups.

A peer group contains rows with equal values for the relevant `ORDER BY` expression.

For example, if the ordering dates are:

`2026-10-01, 2026-10-02, 2026-10-02, 2026-10-04`

there are three peer groups:

`2026-10-01`

`2026-10-02`

`2026-10-04`

With:

`GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW`

both rows dated `2026-10-02` belong to the current peer group and the complete preceding date group participates.

`GROUPS` is therefore useful when business logic is group-oriented rather than row-oriented.

## Boundary Semantics

Common boundaries include:

| Boundary | Meaning |
|---|---|
| `UNBOUNDED PRECEDING` | Start of the partition |
| `n PRECEDING` | Previous rows, values, or peer groups depending on frame type |
| `CURRENT ROW` | Current row or current value/group according to frame semantics |
| `n FOLLOWING` | Subsequent rows, values, or peer groups |
| `UNBOUNDED FOLLOWING` | End of the partition |

The same boundary expression does not have the same interpretation across all three frame types.

For example:

`1 PRECEDING`

means one physical row for `ROWS`, a value interval for `RANGE`, and one peer group for `GROUPS`.

## Why Peer Groups Matter

Consider two rows with the same date:

| Date | Amount |
|---|---:|
| 2026-10-02 | 200 |
| 2026-10-02 | 300 |

Under `ROWS`, these are still two physical rows.

Under `GROUPS`, they belong to the same peer group.

Under `RANGE` with date ordering, both rows have the same ordering value and therefore participate together when the current date is inside the frame.

This distinction is especially important for financial, operational, and time-series reports where several events can share one timestamp or business date.

## Python Implementation

The Python implementation is a standalone simulation of the three frame models.

It uses:

- `dataclass` for immutable sale records
- validation for identifiers, employee names, and amounts
- lists for ordered physical rows
- sets for uniqueness checks and peer groups
- explicit functions for each frame type
- assertions for semantic verification
- exceptions for invalid input

`rows_frame()` calculates physical-row windows.

`range_frame()` scans an ordered numeric domain and includes values inside the specified interval.

`groups_frame()` constructs peer values and selects complete peer groups around the current group.

The implementation intentionally exposes the underlying mechanics instead of hiding them behind a database engine.

## JavaScript Implementation

The JavaScript implementation uses a class-oriented event-ready Node.js structure.

`Sale` validates domain records.

`WindowEngine` owns the ordered data and exposes:

- `rowsFrame()`
- `runningRows()`
- `rangeFrame()`
- `groupsFrame()`

JavaScript `Map` and `Set` semantics are represented through native collections where peer and identity tracking is required. The program also uses `async`/`await` at the application boundary so the processing model can be extended to asynchronous data sources without changing the frame algorithms.

The implementation separates validation from frame evaluation and reports failures using typed errors.

## C++17 Implementation

The C++ program treats window processing as a small analytical engine.

Its main domain types are:

- `Sale`
- `FrameType`
- `FrameSpec`
- `WindowEngine`

The service validates records before calculating frames.

The `ROWS` implementation works directly on the physical vector and calculates bounded indexes.

The `RANGE` implementation creates an ordered copy and evaluates numeric amount intervals.

The `GROUPS` implementation constructs unique peer-day values and translates a group boundary into a set of peer-group indexes.

The direct scanning approach is intentionally clear rather than pretending to be an optimized database engine.

For `n` rows, the direct `RANGE` and `GROUPS` implementations can require `O(n²)` work. A production analytical engine can reduce repeated scans using sorted structures, prefix sums, peer-group indexes, or specialized execution plans.

## Java 17 Implementation

The Java implementation uses an enterprise-style service boundary.

The domain is represented with the immutable `Sale` record.

`WindowService` provides explicit operations for:

- physical row frames
- numeric value frames
- peer-group frames

The service validates collection contents and duplicate identifiers before processing.

The `OrderKey` interface separates frame mechanics from the attribute used for ordering. This allows numeric amount ordering and other numeric ordering policies to use the same service.

Java collections provide immutable input snapshots through `List.copyOf`, while streams are used to construct distinct peer keys.

The custom `WindowFrameException` represents domain-level frame validation failures.

## PostgreSQL Implementation

The PostgreSQL script represents the same concepts in a relational analytical workflow.

The schema contains:

- `employees`
- `sales`
- indexes for employee/date and employee/amount access patterns
- a reporting view

The `sales` table uses primary keys, foreign keys, non-negative amount checks, and controlled status values.

The SQL examples deliberately use different ordering expressions so the distinction between frame types is visible.

### ROWS query

The `ROWS` example uses:

`ROWS BETWEEN 1 PRECEDING AND CURRENT ROW`

with `sale_date, sale_id` ordering.

The secondary identifier provides deterministic physical ordering when multiple sales share a date.

### RANGE query

The `RANGE` example uses a date interval:

`RANGE BETWEEN INTERVAL '2 days' PRECEDING AND CURRENT ROW`

This evaluates the date value rather than counting physical records.

### GROUPS query

The `GROUPS` example orders by `sale_date`.

Rows sharing a date form a peer group, so a boundary of one preceding group includes the entire previous date group.

### Explicit LAST_VALUE Frame

The script also demonstrates why explicit frame boundaries matter for `LAST_VALUE`.

A default frame can end at the current row or peer group depending on the ordering and frame semantics. Explicitly using:

`ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`

makes the intended partition-wide endpoint unambiguous.

## Realistic Example

The sample data contains multiple sales on the same date.

That is intentional.

If every date were unique, `GROUPS` would often appear to behave like a simple row-based window. Duplicate dates expose the peer-group distinction.

The data therefore contains:

- multiple sales on `2026-10-02`
- multiple sales on the same date for another employee
- a cancelled sale
- separate employees and departments
- different monetary values

The cancelled record is retained in the relational model but excluded from posted analytical windows.

## Validation and Failure Handling

All implementations reject invalid domain conditions such as:

- empty input
- duplicate identifiers
- negative monetary values
- invalid frame offsets
- invalid employee names
- non-finite numeric values

The database enforces important rules at the schema level with:

- primary keys
- foreign keys
- `CHECK` constraints
- `UNIQUE` constraints

Application-level validation complements database constraints but does not replace them.

## Transactional Behavior

The PostgreSQL script contains a transaction that changes a sale to `cancelled`, produces a reporting query, and then rolls the change back.

This demonstrates an important separation:

`Transaction → State Change → Analytical Read → COMMIT or ROLLBACK`

A window function calculates over the transaction's visible data. It does not itself provide transactional isolation or persistence.

## Performance Considerations

Frame semantics and execution performance are separate concerns.

`ROWS` with a small bounded frame can be implemented efficiently because the physical boundaries are directly related to row positions.

`RANGE` may require ordered-value comparisons and can become expensive when implemented through repeated scans.

`GROUPS` requires identification of peer groups before group-relative boundaries can be evaluated.

The educational Python, JavaScript, C++, and Java implementations intentionally use straightforward algorithms so the semantics remain visible.

The PostgreSQL implementation delegates execution planning and optimization to PostgreSQL.

Indexes are provided for:

- employee/date ordering
- employee/amount ordering

An index does not guarantee that every window query will use it. The planner chooses an execution strategy based on statistics, cardinality, ordering requirements, and query cost.

## Security Considerations

The examples use fixed data and do not construct SQL through string concatenation.

For real applications:

- parameterize dynamic SQL
- validate frame parameters before execution
- restrict access to sensitive analytical data
- avoid exposing unrestricted reporting views
- use least-privilege database roles
- treat imported ordering values as untrusted input
- enforce critical invariants at the database boundary

Window functions do not provide authorization. A correct frame calculation can still expose data if access controls are poorly designed.

## Practical Distinctions

The four central concepts should not be collapsed into one idea.

`ORDER BY` establishes the logical ordering used by the window.

`ROWS` asks how many physical records are in the frame.

`RANGE` asks which ordering values fall inside a value interval.

`GROUPS` asks which peer groups fall inside a group interval.

The resulting workflow is:

`Partition`
→ `ORDER BY`
→ `Peer Groups`
→ `Frame Boundaries`
→ `Rows Included`
→ `Aggregate / Ranking / Value Function`

Correct window-frame design starts by identifying the unit of movement: record, value, or peer group.
