# Running Calculations

## Scope

Running calculations update a metric as observations arrive instead of waiting for the complete dataset.

The central relationship is:

    input observation
          |
          v
    current state
          |
          +----> running total
          |
          +----> cumulative average
          |
          +----> running minimum
          |
          +----> running maximum
          |
          v
    current analytical state

A running total stores the accumulated value. A cumulative average divides that accumulated value by the number of observations received so far. Running minimum and maximum retain the extreme values encountered in the stream.

These calculations are distinct from a final aggregate because the intermediate states are meaningful. For a sequence `10, 20, 30`, the cumulative averages are `10, 15, 20`, not only the final average of `20`.

## Core Concepts

| Calculation | State required | Update rule | Time per value |
|---|---:|---|---:|
| Running total | Total | `total = total + value` | O(1) |
| Cumulative average | Total and count | `average = total / count` | O(1) |
| Running minimum | Minimum | `min(previous, value)` | O(1) |
| Running maximum | Maximum | `max(previous, value)` | O(1) |
| Full historical analysis | Historical values | Store observations | O(1) update, O(n) storage |

The important design decision is whether historical observations are actually required. Totals, averages, minimums, and maximums can be maintained with constant-size aggregate state. A percentile, median, replay operation, or arbitrary historical query requires additional state.

## Incremental State

For values `10, 20, 30, 40`:

| Position | Value | Running total | Cumulative average | Minimum | Maximum |
|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 10 | 10 | 10 | 10 |
| 2 | 20 | 30 | 15 | 10 | 20 |
| 3 | 30 | 60 | 20 | 10 | 30 |
| 4 | 40 | 100 | 25 | 10 | 40 |

The state after each observation is sufficient to continue the calculation. Reprocessing the complete input is unnecessary when only these metrics are required.

## Python Implementation

The Python implementation uses `RunningMetrics` as the constant-space aggregation object.

It provides:

- Numeric and finite-value validation.
- Running total.
- Cumulative average.
- Running minimum.
- Running maximum.
- A snapshot representation of current state.
- A pre-insertion cumulative-average calculation.
- Transaction-like sales processing with identifiers.
- Assertions for important edge cases.
- A separate `RunningSeries` when historical values are intentionally required.

`dataclass` is used for the mutable metric state because the state consists of closely related fields. `Enum` defines metric categories without relying on arbitrary string values.

The sales workflow demonstrates the difference between an observation and the state derived from it. Each transaction remains an individual input while the aggregate state changes after successful validation.

The Python implementation rejects `NaN`, positive infinity, negative infinity, booleans used as numeric values, and malformed records.

## JavaScript Implementation

The JavaScript implementation uses private class fields for aggregate state and `Object.freeze` for emitted snapshots.

`MetricsStream` extends `EventEmitter`, making the calculation model suitable for event-driven processing. Every accepted observation emits an immutable metric event containing:

- Sequence number.
- Stream name.
- Current value.
- Running total.
- Cumulative average.
- Running minimum.
- Running maximum.
- Optional metadata.

The asynchronous `process` method demonstrates ordered stream processing using `Promise`-based delays without changing the aggregation rules.

Threshold evaluation is deliberately separated from calculation. The running calculation determines state; the threshold policy determines whether that state crosses an operational boundary.

This separation prevents business policy from becoming embedded inside the arithmetic.

## C++17 Implementation

The C++ implementation treats running calculations as an aggregate engine used by a transaction-oriented sales component.

`RunningMetricEngine` owns the mathematical state. `SalesAggregator` adds identity management and rejects duplicate transaction IDs.

`std::optional<double>` represents the absence of a minimum or maximum before the first observation. This is preferable to using an artificial sentinel such as zero because zero can itself be a valid measurement.

The C++ implementation uses:

- `struct` for immutable-style data transfer objects.
- `class` for stateful services.
- `std::vector` for ordered sequences.
- `std::unordered_map` for transaction identity tracking.
- `std::optional` for uninitialized extrema.
- Exceptions for invalid state transitions.
- Assertions for deterministic checks.

The aggregation itself requires O(1) additional state. The duplicate-transaction index requires O(n) memory because transaction identity must be retained.

## Java 17 Implementation

The Java implementation models running calculations as an enterprise service.

`Transaction` is a record representing validated immutable input. `RunningSnapshot` is another record representing immutable calculated state.

`RunningMetrics` owns the numerical state, while `RevenueService` coordinates:

1. Transaction identity validation.
2. Duplicate detection.
3. Metric calculation.
4. Policy evaluation.
5. Historical snapshot recording.

`MetricPolicy` separates mathematical calculation from business constraints. `RevenueLimitPolicy` evaluates the cumulative total against a configured maximum.

The service also exposes a custom `DuplicateTransactionException`, making an identity conflict distinguishable from a numerical validation failure.

The design demonstrates explicit domain boundaries rather than putting all behavior into a single procedural method.

## PostgreSQL Implementation

The PostgreSQL implementation treats measurements as relational events and derives cumulative metrics using window functions.

The principal tables are:

- `metric_streams`: identifies independent metric streams.
- `measurements`: stores ordered observations.
- `cumulative_policies`: stores stream-specific policy limits.

The `running_metrics` view uses window functions:

- `SUM(...) OVER` for running totals.
- `AVG(...) OVER` for cumulative averages.
- `MIN(...) OVER` for running minimums.
- `MAX(...) OVER` for running maximums.

The ordering is based on `sequence_no`, making the meaning of cumulative state explicit.

The schema uses primary keys, foreign keys, unique constraints, check constraints, indexes, a trigger for sequence management, a validation trigger, a stored insertion function, and transactional examples.

The `metric_stream_status` view combines the latest cumulative state with policy information. It distinguishes an empty stream, a total-limit violation, an average requirement failure, and an eligible state.

## Relational Workflow

    metric_stream
          |
          v
    measurements
          |
          v
    ordered sequence
          |
          v
    window calculations
          |
          +----> running total
          +----> cumulative average
          +----> running minimum
          +----> running maximum
          |
          v
    cumulative policy evaluation
          |
          v
    current stream status

The database does not need to store a mutable running-total column for every row. The cumulative state can be derived from the ordered measurements. This reduces the risk of inconsistent duplicated state.

For high-volume systems, materialized aggregates, partitioning, incremental aggregation tables, or streaming systems may be appropriate, but those choices introduce additional consistency and operational complexity.

## Validation and Failure Handling

The implementations reject invalid numerical input rather than allowing invalid values to contaminate subsequent calculations.

Important failure cases include:

- Empty input.
- Non-numeric input.
- Non-finite floating-point values.
- Duplicate transaction identifiers.
- Missing measurement sources.
- Invalid database sequence numbers.
- Cumulative policy violations.
- Empty metric streams.

An empty metric stream has no meaningful minimum or maximum. The implementations therefore represent these states explicitly instead of assigning arbitrary numeric defaults.

## Numerical Considerations

Floating-point arithmetic is appropriate for many analytical measurements, but it can introduce rounding error.

Financial systems should normally use decimal arithmetic or fixed-precision database types. The PostgreSQL implementation uses `NUMERIC(18, 4)` for this reason.

A running average should not be maintained by repeatedly averaging the previous average with the next value. The correct update is based on accumulated total and count:

`average = total / count`

For very large streams or values with substantially different magnitudes, numerical error can become significant. Specialized compensated summation techniques can be used when the application's accuracy requirements justify the additional state and computation.

## Performance

For a stream containing `n` observations:

| Operation | Time | Additional state |
|---|---:|---:|
| Running total | O(n) | O(1) |
| Cumulative average | O(n) | O(1) |
| Running minimum | O(n) | O(1) |
| Running maximum | O(n) | O(1) |
| Historical percentile analysis | Depends on structure | At least O(n) in the simple implementation |
| PostgreSQL window calculation | Data and index dependent | Query-managed |

The key performance property is that each scalar metric update is constant time. The system does not need to scan all previous values for each new observation.

## Practical Distinction

A running calculation answers a time-ordered question:

"What is the metric after the observations received so far?"

A final aggregate answers a complete-dataset question:

"What is the metric after all observations have been processed?"

The distinction matters in monitoring, dashboards, transaction processing, operational analytics, telemetry, and incremental reporting because intermediate states can trigger decisions before the complete dataset exists.

## Security and Integrity

Running calculations can be corrupted if untrusted or duplicated observations are accepted without validation.

The implementations address this through:

- Finite-value validation.
- Identifier validation.
- Duplicate detection.
- Database constraints.
- Foreign keys.
- Transaction boundaries.
- Explicit policy evaluation.
- Controlled state transitions.

For production financial or operational systems, the input source should also be authenticated, authorization should be enforced at the service boundary, and audit records should preserve who or what submitted each observation.

The calculation itself should remain deterministic: the same ordered sequence of valid observations should produce the same cumulative states.
