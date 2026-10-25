# NTILE: Bucketing Records, Quartiles, Deciles, and Segmentation

## Purpose

`NTILE` is a SQL window function used to divide an ordered result set into a specified number of approximately equal-sized buckets.

For a requested bucket count of `N`, `NTILE(N)` assigns each row an integer from `1` through `N`.

The ordering is fundamental. `NTILE` does not decide which records belong together from the raw data alone. The `ORDER BY` expression inside the window determines the sequence that is divided into buckets.

A typical analytical workflow is:

Plain-text model:

    Records
       |
       v
    Filter valid observations
       |
       v
    Define deterministic ordering
       |
       v
    NTILE(N)
       |
       +------------------+
       |                  |
       v                  v
    Bucket 1 ...       Bucket N
       |                  |
       +---------+--------+
                 |
                 v
          Segment / analyze

The implementations in this project use customer scores as the ordered measure. Higher scores are placed earlier in the ordered sequence, so bucket `1` represents the highest-scoring group.

## NTILE Mechanics

For `R` rows and `N` buckets:

- Each bucket receives either `floor(R / N)` rows or `ceil(R / N)` rows.
- The difference between the largest and smallest bucket is at most one row.
- When the division is not exact, earlier buckets receive the extra rows.
- Bucket numbering begins at `1`.
- If `N` is greater than the number of rows, the populated buckets receive one row each and the remaining buckets are empty.
- The ordering expression determines which rows enter earlier buckets.

For example, with `10` rows and `4` buckets:

    Bucket 1 -> 3 rows
    Bucket 2 -> 3 rows
    Bucket 3 -> 2 rows
    Bucket 4 -> 2 rows

With `12` rows and `4` buckets:

    Bucket 1 -> 3 rows
    Bucket 2 -> 3 rows
    Bucket 3 -> 3 rows
    Bucket 4 -> 3 rows

This behavior makes `NTILE(4)` useful for quartile-style segmentation and `NTILE(10)` useful for decile-style segmentation.

## Ordering and Ties

A deterministic ordering is important when multiple records have the same measure.

The project uses:

`ORDER BY score DESC, customer_id`

The score determines the analytical ranking. The customer identifier acts as a stable tie-breaker.

Without a deterministic tie-breaker, records with equal scores may not have a stable relative order. That matters when a bucket boundary falls between tied records.

`NTILE` distributes rows, not distinct score values. Therefore, equal scores can be separated across different buckets.

This is an important distinction from methods that define groups by score thresholds.

## Quartiles

A quartile divides the ordered records into four approximately equal groups.

With:

`NTILE(4) OVER (ORDER BY score DESC, customer_id)`

the interpretation is:

| Bucket | Interpretation |
|---|---|
| 1 | Highest-scoring quarter |
| 2 | Upper-middle quarter |
| 3 | Lower-middle quarter |
| 4 | Lowest-scoring quarter |

The exact score ranges are data-dependent. Quartiles should not be interpreted as fixed score intervals.

For example, a quartile boundary may occur between scores `84` and `82` in one dataset and between `95` and `70` in another.

## Deciles

A decile divides the ordered records into ten approximately equal groups.

With:

`NTILE(10) OVER (ORDER BY score DESC, customer_id)`

bucket `1` contains the highest approximately ten percent of records and bucket `10` contains the lowest approximately ten percent.

A practical segmentation model can map deciles to business categories:

| Deciles | Segment |
|---|---|
| 1 | Top 10% |
| 2-3 | High |
| 4-5 | Upper-Middle |
| 6-7 | Lower-Middle |
| 8-9 | Low |
| 10 | Bottom 10% |

The segment labels are business rules layered on top of the analytical bucket. `NTILE` itself does not know what "High" or "Low" means.

## NTILE Versus Percentiles

`NTILE` and percentile-oriented functions are related but not interchangeable.

| Technique | Primary question |
|---|---|
| `NTILE(N)` | Which approximately equal-sized group contains this row? |
| `PERCENT_RANK()` | What is this row's relative rank between 0 and 1? |
| `CUME_DIST()` | What fraction of rows are at or below the current value? |
| `RANK()` | What rank does this value receive while preserving ties? |
| `DENSE_RANK()` | What rank does this distinct value receive? |

`NTILE` guarantees balanced row counts as closely as possible. It does not guarantee equal-width score intervals.

This distinction matters when the data distribution is skewed.

## Python Implementation

The Python implementation models the analytical process explicitly.

The `Record` dataclass represents an input observation:

- `record_id` identifies the record.
- `customer` identifies the subject.
- `score` provides the ordering measure.

`BucketedRecord` represents the derived NTILE assignment without modifying the source record.

The `ntile()` function:

1. Validates the bucket count.
2. Copies and sorts the records.
3. Uses integer division to determine the base bucket size.
4. Uses the remainder to determine how many early buckets receive one additional record.
5. Assigns bucket numbers in order.

The implementation therefore models the underlying distribution algorithm rather than relying on an external database.

The Python program also calculates:

- bucket counts
- minimum values
- maximum values
- averages
- quartiles
- deciles
- business segmentation

Assertions verify important invariants:

- no records disappear
- no records are duplicated
- bucket sizes differ by at most one
- records remain correctly ordered
- empty inputs are accepted
- invalid bucket counts are rejected

The implementation has sorting complexity of `O(R log R)` for `R` records and `O(R)` additional storage for the ordered and bucketed collections.

## JavaScript Implementation

The JavaScript implementation uses a different execution model from the Python version.

The `Record` class performs constructor-level validation. This prevents invalid identifiers, empty customer names, and non-finite scores from entering the workflow.

The NTILE engine uses:

- arrays for ordered records
- `Map` for grouped buckets
- classes for validation errors
- asynchronous processing through `Promise`
- explicit invariant checks

The asynchronous `processBuckets()` function demonstrates how the analytical operation can be placed inside an event-driven application without requiring an external package.

The implementation preserves the same core NTILE semantics but presents them through JavaScript's object and event-oriented model.

The `summarize()` function aggregates each bucket into:

- count
- minimum
- maximum
- average

This is useful when a downstream application needs both the individual bucket assignments and bucket-level statistics.

## C++17 Implementation

The C++ implementation treats NTILE as part of a compact analytical engine.

The main domain structures are:

- `Record`
- `BucketedRecord`

`std::vector` stores ordered observations, `std::map` groups bucket contents, and `std::unordered_map` provides direct customer-to-segment lookup.

The implementation explicitly computes:

`baseSize = total / bucketCount`

and:

`remainder = total % bucketCount`

For bucket numbers from `1` through `remainder`, one extra row is assigned.

This is the key arithmetic behind the balancing behavior of `NTILE`.

The C++ implementation also validates:

- total record preservation
- bucket-size balance
- ordering correctness
- empty input
- invalid bucket counts

The standard library is sufficient, so no external dependencies are required.

The dominant operation is sorting, giving `O(R log R)` time complexity. Bucket assignment itself is `O(R)`.

## Java 17 Implementation

The Java implementation models NTILE as an enterprise-oriented service.

The `Record` type is an immutable Java record with validation performed during construction.

`BucketedRecord` and `BucketStatistics` are also immutable records. This prevents accidental mutation of analytical results after they have been produced.

`SegmentationType` expresses predefined analytical policies:

| Type | Bucket count |
|---|---:|
| `QUARTILE` | 4 |
| `DECILE` | 10 |

The `BucketPolicy` interface separates bucket assignment from business interpretation.

`DecilePolicy` maps decile numbers to domain labels such as `Top 10%`, `High`, and `Bottom 10%`.

`NtileService` owns the computational behavior:

- ordering
- bucket assignment
- statistics
- segmentation

This separation prevents business labels from being mixed into the fundamental NTILE algorithm.

Java streams are used for bucket statistics, while collections provide efficient storage and lookup.

The design makes it possible to introduce another segmentation policy without rewriting the bucket assignment algorithm.

## PostgreSQL Data Model

The PostgreSQL implementation models both source observations and derived analytical runs.

The principal relationships are:

    customers
        |
        v
    customer_scores
        |
        v
    ntile_runs
        |
        v
    score_buckets

`customers` stores the entities being analyzed.

`customer_scores` stores dated observations and validates that scores are between `0` and `100`.

`ntile_runs` records the analytical configuration:

- run name
- bucket count
- score date
- creation timestamp

`score_buckets` stores the resulting assignment for each customer within a run.

This structure is useful when analytical results must be reproducible or audited rather than calculated only during a temporary query.

## PostgreSQL Constraints

The database enforces important rules directly.

Examples include:

- primary keys
- foreign keys
- non-empty customer names
- valid score ranges
- controlled score statuses
- positive bucket counts
- valid bucket numbers
- unique customer/date observations

The `score_buckets` trigger provides an additional database-level validation check to ensure a bucket number is within the declared bucket count.

Database constraints are important because application validation alone does not protect data from every insertion path.

## PostgreSQL Window Function

The core operation is:

`NTILE(4) OVER (ORDER BY score DESC, customer_id)`

or:

`NTILE(10) OVER (ORDER BY score DESC, customer_id)`

The window function does not collapse rows. Every source row remains present while receiving an additional analytical value.

This differs from `GROUP BY`, where multiple rows become one aggregate row.

For example:

| Customer | Score | Quartile |
|---|---:|---:|
| Asha | 96 | 1 |
| Kiran | 95 | 1 |
| Chirag | 91 | 1 |
| Gita | 91 | 2 |

The equal score of `91` does not prevent the two records from being placed into different quartiles because NTILE assigns buckets to ordered rows.

## Partitioned NTILE

`NTILE` can operate independently within partitions.

The PostgreSQL implementation demonstrates:

`NTILE(10) OVER (PARTITION BY score_date ORDER BY score DESC, customer_id)`

This creates separate decile calculations for each date.

That distinction is important for time-based analytics.

A global decile compares all rows together. A partitioned decile compares records within each partition.

For example:

    All customers
         |
         +--> 2026-10-24 -> independent deciles
         |
         +--> 2026-10-25 -> independent deciles
         |
         +--> 2026-10-26 -> independent deciles

A customer in the top decile on one date is therefore in the top decile relative to that date's population.

## Bucket Counts Greater Than the Number of Rows

Suppose there are three records and the query requests five buckets.

The conceptual result is:

| Bucket | Rows |
|---|---:|
| 1 | 1 |
| 2 | 1 |
| 3 | 1 |
| 4 | 0 |
| 5 | 0 |

This behavior should be considered when building downstream reports.

An application should not assume every requested bucket contains a row.

The Python, JavaScript, C++ and Java implementations explicitly handle this case.

## Empty Inputs

An empty input relation produces no bucketed rows.

This is different from invalid configuration.

A valid request such as `NTILE(4)` over zero rows is an empty result. A bucket count of zero is invalid.

The distinction is important for robust analytical systems:

| Condition | Treatment |
|---|---|
| Zero records | Valid empty result |
| Positive bucket count | Valid configuration |
| Zero bucket count | Invalid |
| Negative bucket count | Invalid |
| Non-deterministic ordering | Poor analytical practice |
| Invalid source score | Reject at validation boundary |

## Segmentation Semantics

A bucket is an analytical position, not automatically a business category.

For example:

`NTILE(10)` produces decile `1`.

A separate rule may interpret decile `1` as `Top 10%`.

This separation is deliberate:

    Measurement
        |
        v
    Ordering
        |
        v
    NTILE
        |
        v
    Decile number
        |
        v
    Business policy
        |
        v
    Segment label

Changing the business policy should not require changing the NTILE calculation.

## Performance Considerations

The primary computational cost is ordering.

For `R` rows, sorting generally requires `O(R log R)` time.

The bucket assignment after sorting is linear, `O(R)`.

For PostgreSQL, the optimizer may need to sort rows for the window function when a suitable ordering cannot be obtained efficiently from existing data.

The demonstration includes an index on:

`(score_date, score DESC, customer_id)`

This supports the common date-filtered, score-ordered workload, although the optimizer remains responsible for determining whether the index is beneficial for a particular table size and query plan.

Indexes should support actual access patterns rather than being created indiscriminately.

## Security and Data Integrity

The implementations do not require external packages or network access.

The PostgreSQL design uses database constraints and foreign keys to reduce invalid state.

Important controls include:

- validated numeric ranges
- controlled status values
- foreign-key enforcement
- unique observations
- positive bucket counts
- valid bucket-number constraints
- transactional insertion of analytical runs

The transaction example ensures that creating a new analytical run and populating its bucket assignments can succeed or fail as one logical operation.

This prevents a partially populated segmentation run from being committed.

## Failure Modes

Several failure conditions are deliberately represented.

### Invalid configuration

A non-positive bucket count is rejected.

### Invalid source data

Scores outside the permitted range are rejected by PostgreSQL.

The application implementations reject non-finite scores.

### Empty data

An empty dataset produces an empty result rather than an exception.

### Non-deterministic ties

Equal values can cross bucket boundaries. A stable secondary ordering column reduces ambiguity.

### Business interpretation errors

Treating deciles as fixed score thresholds is incorrect. Deciles represent approximately equal row populations, not equal numerical score intervals.

### Small populations

When the number of records is smaller than the requested number of buckets, some buckets contain no rows.

## Relationship Between the Five Implementations

| Implementation | Primary perspective | Main mechanism |
|---|---|---|
| Python | Analytical model | Dataclasses, sorting, validation, assertions |
| JavaScript | Event-driven processing | Classes, Maps, Promises, validation |
| C++17 | Computational engine | STL containers, explicit bucket arithmetic, invariants |
| Java 17 | Enterprise domain model | Records, policies, service class, streams |
| PostgreSQL | Relational analytics | Window functions, constraints, indexes, transactions |

All five implementations preserve the same analytical principle while using language-specific structures.

## Practical Analytical Workflow

A robust NTILE workflow can be represented as:

    1. Select the population
           |
           v
    2. Validate source values
           |
           v
    3. Choose the ordering metric
           |
           v
    4. Add a deterministic tie-breaker
           |
           v
    5. Select bucket count
           |
           v
    6. Apply NTILE
           |
           v
    7. Inspect bucket sizes and ranges
           |
           v
    8. Apply domain-specific segment labels
           |
           v
    9. Validate the result
           |
           v
    10. Store or report the derived segmentation

This workflow separates source-data quality, analytical ranking, bucket assignment, and business interpretation.

## Important Limitations

`NTILE` does not produce fixed-width numeric ranges.

If scores are highly concentrated, two adjacent buckets can have very similar score values. Conversely, a bucket boundary can cross a large numerical gap.

`NTILE` also distributes rows rather than unique values. Tied values may therefore be separated.

For applications where equal values must always belong to the same group, a different analytical method may be more appropriate.

For applications requiring fixed score thresholds, explicit `CASE` ranges may be preferable.

For applications requiring a continuous percentile position, `PERCENT_RANK()` or `CUME_DIST()` may provide a better representation.

The appropriate function depends on whether the requirement is equal-sized groups, relative rank, cumulative distribution, or fixed thresholds.
