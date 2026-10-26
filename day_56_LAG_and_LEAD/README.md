# LAG and LEAD: Previous and Next Row Analysis

## Scope

This project implements ordered-row analysis with `LAG` and `LEAD` across Python, JavaScript, C++17, Java 17, and PostgreSQL.

The central distinction is:

- `LAG` accesses an earlier row in an ordered sequence.
- `LEAD` accesses a later row in an ordered sequence.
- Both depend on a clearly defined ordering.
- The first row normally has no `LAG` value.
- The last row normally has no `LEAD` value.
- `LAG` and `LEAD` do not aggregate rows. They expose neighboring observations so that comparisons, changes, trends, event detection, and workflow decisions can be calculated.

The implementations use a daily repository-related metric as the main time-series scenario:

`2026-10-19 → 120 → 2026-10-20 → 126 → 2026-10-21 → 131 → 2026-10-22 → 127 → 2026-10-23 → 135 → 2026-10-24 → 135 → 2026-10-25 → 142`

This sequence contains increases, a decline, a repeated value, and boundary rows, making it useful for previous-row and next-row analysis.

## Conceptual Model

A time-series row can be represented as:

`Current Row ← LAG(Current Row)`

and

`Current Row → LEAD(Current Row)`

For a sequence such as `120, 126, 131, 127`:

| Position | Value | LAG | LEAD |
|---|---:|---:|---:|
| First | 120 | NULL | 126 |
| Second | 126 | 120 | 131 |
| Third | 131 | 126 | 127 |
| Fourth | 127 | 131 | NULL |

The neighboring values can then support derived measurements:

`current - LAG(current)`

and

`LEAD(current) - current`

A percentage comparison can use:

`(current - previous) / previous × 100`

The denominator must be protected against zero. A missing neighbor is also different from a numeric zero and must not be silently converted into zero.

## Ordering Is Fundamental

`LAG` and `LEAD` are meaningful only when the ordering column represents the intended sequence.

For time-series data, the ordering is usually chronological:

`ORDER BY metric_date`

For event streams, it may be an event timestamp plus a unique event identifier.

If two rows have the same timestamp and no deterministic tie-breaker exists, the database cannot provide a reliable logical sequence. Production queries should therefore use a deterministic ordering such as:

`ORDER BY event_time, event_id`

The PostgreSQL implementation uses `metric_date` because the sample table enforces uniqueness for each repository, date, and metric name.

## LAG

`LAG` retrieves a value from a preceding row.

Typical analytical uses include:

- day-over-day change
- month-over-month change
- previous transaction amount
- previous system state
- previous deployment
- previous inventory level
- previous customer event
- previous performance measurement

The PostgreSQL implementation uses:

`LAG(metric_value) OVER (PARTITION BY repository_id, metric_name ORDER BY metric_date)`

The partition prevents unrelated repositories or metric types from being compared with each other.

## LEAD

`LEAD` retrieves a value from a following row.

Typical uses include:

- next-event analysis
- time until the next event
- forward price comparison
- detecting local peaks and valleys
- identifying state transitions
- calculating the change expected between consecutive observations

The implementation uses:

`LEAD(metric_value) OVER (PARTITION BY repository_id, metric_name ORDER BY metric_date)`

For the final row, `LEAD` returns `NULL` because there is no following observation.

## LAG and LEAD Together

Using both functions exposes the local neighborhood of each row.

| Row | Previous | Current | Next |
|---|---:|---:|---:|
| 1 | NULL | 120 | 126 |
| 2 | 120 | 126 | 131 |
| 3 | 126 | 131 | 127 |
| 4 | 131 | 127 | 135 |
| 5 | 127 | 135 | 135 |
| 6 | 135 | 135 | 142 |
| 7 | 135 | 142 | NULL |

This enables local pattern detection without self-joining a table.

A local peak occurs when:

`current > previous AND current > next`

The sample therefore identifies `131` and `135` as local peaks under the strict greater-than rule.

A plateau such as `135, 135` is not classified as a strict peak because equality is deliberately treated as a separate condition.

## Python Implementation

The Python program models observations with the immutable `DailyMetric` dataclass.

The `validate_series` function:

- rejects an empty series
- rejects NaN values
- sorts observations chronologically
- rejects duplicate dates

The `analyze` function produces a structured comparison for every row. Each result contains:

- current value
- previous value
- next value
- change from the previous value
- change toward the next value
- backward trend
- forward trend

The `Trend` enumeration distinguishes `UP`, `DOWN`, `FLAT`, and `UNKNOWN`.

`UNKNOWN` is important for boundary rows because the absence of a neighbor is not the same as a flat numeric comparison.

The Python implementation also calculates percentage changes, detects local trend reversals, calculates historical rolling averages, and runs assertions covering boundary behavior and validation failures.

The rolling-average implementation intentionally uses historical observations rather than including the current observation. This makes it a genuine previous-period reference rather than a centered average.

## JavaScript Implementation

The JavaScript implementation uses Node.js-compatible standard language features without external packages.

`Metric` validates timestamps and numeric values before creating immutable observations.

`TimeSeriesAnalyzer`:

- validates observations
- orders them chronologically
- detects duplicate timestamps
- calculates `lag`
- calculates `lead`
- computes absolute differences
- computes percentage changes
- classifies trends
- detects reversals

The implementation also exposes `streamEvents`, an asynchronous event-style reporting mechanism. Each analytical row is delivered to a handler through an asynchronous loop, allowing the same model to feed logging, event processing, or downstream workflow code.

`MergePolicy` demonstrates how a time-series calculation can become a decision rule. The sample policy checks recent positive changes and a maximum permitted decline.

The program also captures invalid duplicate timestamps rather than allowing ambiguous ordering into the analytical pipeline.

## C++17 Implementation

The C++ program uses a technical case study combining time-series analysis with repository governance.

`TimeSeries` owns validated metric values and produces neighboring-row records using `std::optional<double>`.

`std::optional` represents the absence of a previous or next observation explicitly. This avoids using a sentinel such as `0`, which could be a legitimate metric value.

The program detects local peaks through indexed traversal and uses STL containers for the data model.

The second part introduces a repository governance model:

`PullRequest → Reviews → Status Checks → Branch Protection → Merge Decision`

The `GovernanceEngine` evaluates:

- target branch
- draft state
- presence of commits
- merge conflicts
- unresolved conversations
- eligible approvals
- required status checks

An approval from an ineligible reviewer does not satisfy the approval requirement. This is an important distinction between the existence of an approval record and a valid approval decision.

The implementation uses exceptions for invalid input and returns explicit merge reasons rather than a single unexplained boolean.

## Java 17 Implementation

The Java implementation uses immutable records and explicit service classes.

The main domain types are:

- `Metric`
- `NeighborComparison`
- `Review`
- `StatusCheck`
- `BranchPolicy`
- `PullRequest`
- `MergeDecision`

`TimeSeriesService` performs chronological validation, neighboring-row comparison, trend classification, and local-peak detection.

`GovernanceService` independently evaluates repository policy.

This separation prevents time-series analysis from being mixed with repository policy logic.

Java records provide compact immutable representations for observations and policy values. Collections are copied with `List.copyOf`, preventing callers from modifying the internal governance state after construction.

Review states are represented explicitly:

- `PENDING`
- `APPROVED`
- `CHANGES_REQUESTED`
- `DISMISSED`

Only an eligible reviewer with an `APPROVED` state contributes to the approval count.

The enterprise model therefore distinguishes:

`Review existence → Review state → Reviewer eligibility → Approval count → Policy evaluation`

That distinction is useful in systems where governance decisions must be auditable.

## PostgreSQL Implementation

The PostgreSQL script provides the most complete relational model.

The repository domain is represented through:

`repositories → branches → commits → pull_requests → reviews → review_comments → status_checks → branch_protection_policies`

The schema also includes:

`reviewers → approval_requirements`

and the analytical table:

`daily_metrics`

Primary keys and foreign keys preserve entity relationships. Unique constraints prevent duplicate repository names, branch names within a repository, commit hashes, metric observations, and status-check names for a Pull Request.

Check constraints validate controlled states such as review and Pull Request status.

The Pull Request trigger verifies that source and target branches belong to the same repository. This is a cross-row business rule that cannot be expressed cleanly with an ordinary column-level check constraint.

## PostgreSQL LAG and LEAD Queries

The basic query returns:

- current metric
- previous metric
- next metric

The previous-value query calculates:

`current_value - previous_value`

The forward-value query calculates:

`next_value - current_value`

The percentage query uses `NULLIF` to prevent division by zero.

This is important because a previous value of zero is a valid database value but cannot be used as a percentage denominator.

The local-peak query first creates a CTE containing both neighboring values and then filters for:

`current > previous AND current > next`

This separates window calculation from business filtering and keeps the analytical condition explicit.

## Repository Governance Workflow

The repository model is deliberately separate from the time-series model.

The governance relationship is:

`Repository`
`  ↓`
`Branches`
`  ↓`
`Commits`
`  ↓`
`Pull Request`
`  ↓`
`Reviews and Review Comments`
`  ↓`
`Status Checks`
`  ↓`
`Branch Protection Policy`
`  ↓`
`Merge Eligibility`
`  ↓`
`Merge`

A Pull Request proposes a changeset.

Code review evaluates the changeset.

An approval is a specific review decision that may or may not satisfy policy depending on reviewer eligibility and current policy state.

Branch protection defines repository-level conditions that must be satisfied before merging.

These concepts are related but are not interchangeable.

## Boundary Conditions

The first row has no previous row:

`LAG = NULL`

The last row has no next row:

`LEAD = NULL`

The implementations preserve these states rather than inventing values.

Other important edge cases include:

| Condition | Treatment |
|---|---|
| Empty series | Validation failure |
| Duplicate dates | Rejected |
| Duplicate timestamps | Rejected |
| NaN or non-finite values | Rejected |
| Previous value is zero | Percentage change becomes unavailable |
| Missing previous row | `NULL` or explicit unknown state |
| Missing next row | `NULL` or explicit unknown state |
| Equal neighboring values | `FLAT` |
| Ineligible approval | Excluded from approval count |
| Failed status check | Blocks merge eligibility |
| Merge conflict | Blocks merge eligibility |
| Unresolved review conversation | Blocks merge when policy requires resolution |

## Performance Considerations

For a PostgreSQL window query, the database must establish the requested partition and ordering. An index such as:

`(repository_id, metric_name, metric_date)`

can support common time-series access patterns when the workload is large and the query shape matches the index.

The sample schema keeps indexes targeted rather than indexing every column.

The Python, JavaScript, C++, and Java implementations perform neighboring-row analysis in linear time after ordering.

For an already ordered sequence:

`Time: O(n)`

`Additional space: O(n)` when materialized comparison records are retained.

If only a streaming previous-value calculation is required, storage can be reduced because only the immediately preceding observation is needed. A next-value calculation requires either look-ahead buffering or a representation where the complete sequence is already available.

## Security and Data Integrity

Analytical correctness depends on trustworthy input.

The implementations therefore validate:

- dates and timestamps
- numeric values
- duplicate observations
- repository relationships
- reviewer eligibility
- Pull Request states
- status-check states
- policy thresholds

The PostgreSQL schema uses foreign keys and constraints to prevent invalid relationships from entering the database.

Repository governance also treats authorization-related state separately from analytical state. A review marked `APPROVED` does not automatically become an eligible approval.

The database transaction demonstrates that a review-state change and its subsequent merge-eligibility evaluation can be executed atomically.

## Practical Interpretation

`LAG` is primarily useful when the question is:

“What changed compared with the previous observation?”

`LEAD` is primarily useful when the question is:

“What happens in the next observation?”

Using both answers:

“What is the local context around this observation?”

That local context supports trend analysis, event detection, transition analysis, anomaly detection, and time-series reporting while preserving the original row structure.
