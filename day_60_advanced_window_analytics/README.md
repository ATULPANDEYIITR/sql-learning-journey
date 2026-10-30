# Advanced Window Analytics

## Domain and analytical objective

This project implements an analytical pipeline for retail sales data. It converts transaction-level records into daily product-store metrics, calculates moving averages and rolling measurements, compares consecutive periods, and ranks products using a combination of revenue performance and growth.

The implementation treats the following operations as separate analytical stages:

1. Transaction aggregation establishes daily measurements.
2. Calendar densification creates a continuous date series.
3. Window calculations produce rolling and historical metrics.
4. Growth calculations compare non-overlapping periods.
5. Ranking functions establish relative product positions.
6. A weighted ranking policy combines independent performance dimensions.
7. Eligibility rules determine whether an observation can participate in the combined ranking.

The sample data contains two retail stores, three products, and 21 calendar days. It includes multiple transactions on selected dates and a deliberately missing store-product-date observation.

All five implementations use a seven-day window and a ranking policy that assigns 60% weight to revenue performance and 40% to growth performance.

## Analytical concepts

### Transaction aggregation

A transaction is an individual sales event containing a store, product, date, quantity, and revenue.

Multiple transactions can belong to the same store, product, and calendar date. Window calculations should not be applied directly to these records when the intended analytical unit is a daily product-store observation.

The aggregation stage calculates:

- Daily revenue using the sum of transaction revenue.
- Daily units using the sum of transaction quantities.
- One daily observation for each store-product-date combination.

The analytical grain is:

`store_id + product_id + sale_date`

This grain is maintained throughout the remaining calculations.

### Calendar densification

Transaction data does not necessarily contain a row for every calendar day. An absent observation can mean that no sale occurred, rather than that the underlying date is unavailable.

The implementations create a continuous daily series between the first and last recorded dates for each store-product combination.

Missing dates receive:

| Measurement | Assigned value |
|---|---:|
| Daily revenue | 0 |
| Daily units | 0 |

This distinction is essential for calendar-based windows. Without densification, a seven-row frame could represent seven transactions or seven observed dates rather than seven consecutive calendar days.

The sample includes an intentionally missing observation for product `P-C` at store `LKO-02` on 6 October 2026. Each implementation generates a zero-activity daily record for that date.

The date range is limited to a maximum of 3,660 days to control memory consumption and prevent unexpectedly large analytical workloads.

## Moving averages and rolling metrics

### Moving average

A moving average represents the mean of measurements within a specified observation window.

For daily revenue \(R_t\) and a window length \(w\), the trailing moving average is:

\[
MA_t =
\frac{\sum_{i=t-w+1}^{t}R_i}{w}
\]

The sample uses a seven-day window:

\[
MA_t =
\frac{R_{t-6}+R_{t-5}+\cdots+R_t}{7}
\]

For early observations, the implementations use the available history rather than returning an artificial zero or requiring the full window.

For example, the first observation uses one day, the second uses two days, and the seventh uses seven days.

This is a partial-window convention. It is important because an early moving average is not directly comparable with a fully populated seven-day moving average without considering the number of observations.

### Rolling sum

The seven-day rolling revenue measures the total revenue generated during the current date and the preceding six dates.

\[
RS_t =
\sum_{i=t-6}^{t}R_i
\]

The rolling unit total uses the same window:

\[
RU_t =
\sum_{i=t-6}^{t}U_i
\]

These two measurements describe different dimensions. Revenue represents monetary performance, while units represent sales volume.

A high rolling revenue total does not necessarily imply a high unit total. Different product prices and sales quantities can produce different rankings under these measurements.

### Rolling average versus rolling sum

A rolling sum answers how much activity occurred during the observation window.

A rolling average answers the average activity per calendar day within the window.

The distinction matters when a system compares products with different sales patterns. A product with one unusually large sales day may have a high rolling sum but a less stable daily average.

### Lag and cumulative measurements

The implementations also calculate:

- Previous-day revenue using the preceding calendar observation.
- Cumulative revenue from the beginning of the available product-store series.

The previous-day value is useful for short-term comparisons. Cumulative revenue provides a historical running total rather than a fixed-width measurement.

These metrics do not replace the seven-day measurements. They provide different temporal perspectives.

## Period-over-period growth

A growth calculation requires two comparable periods.

Comparing the current trailing seven-day window against the immediately preceding seven-day window produces two non-overlapping intervals.

Current period:

\[
C_t = \sum_{i=t-6}^{t}R_i
\]

Previous period:

\[
P_t = \sum_{i=t-13}^{t-7}R_i
\]

Fractional growth is:

\[
G_t = \frac{C_t-P_t}{P_t}
\]

Percentage growth is:

\[
G_{t,\%} = 100 \times G_t
\]

A positive result indicates growth, a negative result indicates a decline, and zero indicates no change.

The denominator must be positive. A zero or missing baseline makes the growth ratio undefined.

The implementations represent undefined growth as `None`, `null`, an empty optional value, or SQL `NULL`, depending on the language. They do not substitute zero because zero growth and undefined growth have different meanings.

### Why two complete windows are required

A current seven-day window and its preceding seven-day comparison require 14 calendar observations.

With data beginning on 1 October 2026:

- 1 October provides one observation.
- 7 October completes the first seven-day period.
- 13 October completes a second period's first six days.
- 14 October provides the first complete current seven-day window and a complete preceding seven-day baseline.

Consequently, 14 October is the first potentially eligible ranking date in the sample.

This rule avoids comparing a complete current window with an incomplete historical baseline.

## Ranking combinations

### Competition ranking

A ranking function assigns positions to observations according to a metric.

The implementations use competition ranking semantics equivalent to SQL `RANK()`.

For descending values:

| Product | Value | Rank |
|---|---:|---:|
| P-A | 950 | 1 |
| P-B | 950 | 1 |
| P-C | 800 | 3 |

Tied values receive the same rank. The next rank contains a gap.

This is different from dense ranking:

| Product | Value | Dense rank |
|---|---:|---:|
| P-A | 950 | 1 |
| P-B | 950 | 1 |
| P-C | 800 | 2 |

The PostgreSQL implementation includes `RANK()`, `DENSE_RANK()`, and `ROW_NUMBER()` so their separate behaviors can be inspected.

`ROW_NUMBER()` assigns a unique position, using product identity as a deterministic tie-breaker. It does not express the same equality semantics as `RANK()`.

### Ranking population

A product is compared with other products from the same store on the same date.

The ranking partition is therefore:

`store_id + sale_date`

Products from different stores are not compared in one ranking population. This prevents differences in store-level business scale from unintentionally influencing product positions.

Growth ranking uses only eligible observations. A product without two complete comparison periods or a positive previous-period revenue baseline does not participate in that ranking.

### Normalized ranking scores

Raw ranks are ordinal positions. Their numerical differences do not necessarily represent proportional differences in performance.

The implementations convert competition ranks into normalized scores:

\[
S_r = \frac{n-r}{n-1}
\]

Where:

- \(n\) is the population size.
- \(r\) is the competition rank.
- \(S_r\) is the normalized score.

The best rank receives a score of 1. The lowest rank receives a score of 0 when the population contains at least two distinct ranking positions.

A population containing only one product receives a score of 1. There is no competing observation against which that product could be ranked.

Tied products receive the same normalized score.

### Weighted composite ranking

The project combines revenue rank performance and growth rank performance.

\[
S_c =
0.60S_r + 0.40S_g
\]

Where:

- \(S_r\) is the normalized revenue ranking score.
- \(S_g\) is the normalized growth ranking score.
- \(S_c\) is the composite score.

The resulting score is ranked in descending order within each store-date population.

This policy provides a configurable balance between the size of recent sales performance and the rate of change.

The weights are policy parameters rather than fixed characteristics of window analytics. Different applications may choose other weights based on business objectives.

A composite score is not a statistical probability, market share, or absolute measure of business quality. It expresses relative performance under the configured ranking policy.

## Eligibility and missing information

An observation becomes eligible for the combined ranking when:

1. A complete current seven-day window exists.
2. A complete preceding seven-day window exists.
3. Previous-period revenue is greater than zero.
4. Growth can be calculated.

Ineligible observations remain available in the analytical output.

Their daily measurements, moving averages, rolling sums, and revenue ranks can still be inspected. Only metrics that depend on a complete growth comparison remain unavailable.

This separation prevents insufficient historical information from being interpreted as poor performance.

The pipeline uses distinct representations for:

| Condition | Interpretation |
|---|---|
| Zero revenue | A valid observation with no revenue |
| Missing daily transaction | A date requiring calendar densification |
| Incomplete window | Insufficient calendar history |
| Zero comparison baseline | Undefined percentage growth |
| Negative growth | Valid decline against a positive baseline |
| Ineligible ranking | Insufficient information for the combined score |

## Pipeline architecture

The analytical workflow follows this dependency structure:

    Transaction events
          |
          v
    Input validation
          |
          v
    Daily aggregation
          |
          v
    Calendar densification
          |
          v
    Rolling sums and moving averages
          |
          v
    Previous-period calculations
          |
          v
    Growth and eligibility evaluation
          |
          v
    Revenue and growth ranking
          |
          v
    Normalized ranking scores
          |
          v
    Weighted composite score
          |
          v
    Composite rank and reporting

Each stage consumes the output of the preceding stage. This makes the analytical dependencies explicit and avoids calculating rankings from partially constructed metrics.

## Python implementation

The Python file implements a complete batch analytics engine.

### Domain model

`SalesEvent` is an immutable dataclass containing the event identifier, store, product, date, units, and revenue.

`AnalyticsPolicy` holds the window length, maximum permitted date range, and ranking weights. Its validation prevents invalid window lengths and inconsistent weight totals.

`MetricWork` acts as the internal calculation structure. It retains intermediate metrics and ranking information while the pipeline is executing.

`AnalyticsRow` is an immutable output record containing the calculated measurements and eligibility decision.

### Aggregation and prefix sums

The implementation aggregates events using dictionaries keyed by store, product, and date.

A second grouping structure separates each product-store time series. It generates a daily sequence between the first and last recorded observations.

Revenue and units are converted into prefix sums.

For a prefix-sum array \(P\), the sum of an interval can be calculated as:

\[
\text{RangeSum}(a,b)=P_{b+1}-P_a
\]

This permits constant-time calculation of each window after prefix construction.

For a series of \(n\) daily observations, aggregation and prefix construction take \(O(n)\) time. Ranking introduces sorting costs within each store-date population.

### Ranking implementation

`competition_ranks()` implements competition ranking and supports ties.

`normalized_rank_score()` converts positions into scores between zero and one.

The engine creates ranking populations using store and date as the grouping dimensions. It evaluates revenue ranking first, then growth ranking among eligible products, and finally the weighted composite ranking.

### Validation and execution

The Python script validates identifiers, duplicate events, revenue, units, and date spans.

It also provides:

- Safe handling of zero comparison denominators.
- A maximum event count.
- Assertions for missing calendar dates and eligibility.
- Reproducible sample data.
- A reporting function for the latest available date.
- Optional CSV output through the `--csv` argument.

The standard-library implementation uses `Decimal` for financial measurements to avoid ordinary binary floating-point rounding behavior in revenue aggregation.

## JavaScript implementation

The JavaScript file uses an asynchronous, event-driven architecture.

### Event-oriented processing

`WindowAnalyticsEngine` extends Node.js `EventEmitter`.

The engine validates input, processes the transaction collection, calculates analytical results, and emits a `calculationCompleted` event containing execution statistics.

The asynchronous method yields to the Node.js event loop before beginning the main calculation. This makes the interface suitable for integration with asynchronous application workflows.

### Data structures

The implementation uses:

| Structure | Purpose |
|---|---|
| `Set` | Detect duplicate event identifiers |
| `Map` | Store daily aggregates and ranking populations |
| Arrays | Maintain ordered daily observations |
| Prefix arrays | Calculate rolling sums |
| EventEmitter | Publish completion statistics |

Revenue is represented as integer cents. This avoids binary floating-point representation for monetary aggregation.

Growth and normalized scores use JavaScript numbers because they represent ratios rather than currency.

### Validation and failure handling

The implementation validates identifiers, calendar dates, integer quantities, revenue amounts, and maximum date ranges.

It uses strict date parsing and UTC date calculations so that the sample results do not depend on the machine's local timezone.

The asynchronous entry point catches execution failures and reports them through the Node.js error stream.

## C++17 implementation

The C++ program focuses on a performance-oriented analytics engine with explicit data structures and numerical controls.

### Date representation

C++17 does not provide the C++20 calendar date library used by newer standard versions.

The implementation therefore provides Gregorian date conversion functions.

A validated date is converted into a serial day number. Calendar operations can then use integer arithmetic rather than repeatedly parsing date strings.

The program validates the year, month, day, and leap-year conditions.

### Aggregation and storage

The implementation uses ordered maps:

- `GroupKey` separates store-product time series.
- A date-indexed map stores daily aggregates.
- `StoreDateKey` defines ranking populations.
- Vectors retain the calculated metric records.

Revenue is stored as integer cents, providing exact monetary aggregation within the supported integer range.

Overflow checks are performed before relevant accumulation operations.

### Metric processing

The C++ engine uses prefix sums for rolling windows and previous-period comparisons.

After all result records have been created, ranking groups are constructed using pointers into the completed result vector.

This ordering is deliberate. Retaining pointers while a vector is still growing could cause invalidation when its storage is reallocated.

The generic `assignCompetitionRanks()` function performs the ranking operation while allowing different metrics and ranking destinations to be supplied.

The resulting architecture separates date processing, aggregation, metric calculation, and ranking.

### Complexity

For \(n\) daily observations:

- Aggregation is \(O(n \log n)\) with ordered maps.
- Prefix-sum construction is \(O(n)\).
- Each rolling sum is \(O(1)\) after prefix construction.
- Ranking a population of \(k\) products costs \(O(k \log k)\).

The implementation is bounded by event-count and date-span limits to reduce resource exhaustion risks.

## Java 17 implementation

The Java file models the analytics pipeline as an enterprise-oriented service with immutable domain types and controlled execution states.

### Domain records

The implementation uses Java records for:

- `SalesEvent`
- `WindowPolicy`
- `SeriesKey`
- `StoreDateKey`
- `Aggregate`
- `AnalyticsRow`
- `AnalyticsReport`

Compact record constructors enforce data validity when objects are created.

`AnalyticsRow` uses `Optional` values for metrics that may be undefined, including previous-period growth and ranking information.

### Explicit execution states

The `AnalyticsRun` model defines:

| State | Meaning |
|---|---|
| `CREATED` | Execution has been initialized |
| `VALIDATED` | Input records have passed validation |
| `AGGREGATED` | Transaction data has been grouped by date |
| `WINDOWED` | Rolling and historical measurements are calculated |
| `RANKED` | Ranking and composite scores are available |
| `COMPLETED` | A final immutable report is ready |
| `FAILED` | Processing has stopped because of an error |

The service permits only the expected state transition.

This prevents reporting a completed execution when an intermediate analytical stage has failed.

### Service responsibilities

`WindowAnalyticsService` owns input validation, event aggregation, calendar densification, rolling calculations, eligibility evaluation, and ranking.

`WindowPolicy` separates configurable ranking parameters from the calculation logic.

`AnalyticsReport` retains the final immutable output and transaction count.

The use of `BigDecimal` protects revenue calculations from ordinary binary floating-point representation errors. Division operations use an explicit mathematical context.

Java streams are used for output ordering, eligibility filtering, and reporting. The main aggregation and window calculations use collections and loops to retain control over date positions and prefix-sum operations.

## PostgreSQL implementation

The SQL file demonstrates how advanced window analytics can be represented through a relational database.

### Relational model

| Table | Purpose |
|---|---|
| `stores` | Store reference data |
| `products` | Product reference data |
| `sales_events` | Transaction-level revenue and quantity facts |
| `ranking_policy` | Configurable window and ranking weights |

Primary keys establish row identity. Foreign keys prevent transactions from referring to nonexistent stores or products.

Check constraints enforce positive quantities, non-negative revenue, valid window configuration, and valid ranking weights.

Unique identifiers prevent duplicate external transaction references.

### Daily aggregation

The `event_daily` CTE transforms transaction-level records into the analytical grain of store, product, and date.

`series_bounds` determines the first and last available dates for each series.

`generate_series()` produces the daily calendar. A `LEFT JOIN` connects existing daily observations to the generated dates.

`COALESCE()` assigns zero values where no transaction exists.

This approach creates the continuous observation series needed for calendar-based calculations.

### Window frames

PostgreSQL window functions provide direct implementations of the main analytical operations.

The rolling revenue calculation uses:

`ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`

The previous non-overlapping seven-day period uses:

`ROWS BETWEEN 13 PRECEDING AND 7 PRECEDING`

The moving average uses `AVG()` over the current trailing frame.

`LAG()` returns the previous daily revenue.

An unbounded preceding frame calculates cumulative revenue.

Because calendar densification occurs before these operations, the row positions correspond to consecutive calendar dates.

### Ranking functions

The SQL view distinguishes three ranking operations:

| Function | Result |
|---|---|
| `RANK()` | Competition ranking with gaps after ties |
| `DENSE_RANK()` | Ranking without gaps after ties |
| `ROW_NUMBER()` | Unique sequential ordering |

`PERCENT_RANK()` normalizes positions within the eligible store-date population.

The composite score is calculated in a separate query stage because a window-function result cannot be directly reused as the input to another window function at the same query level.

The staged CTE design makes these dependencies explicit.

### Views and functions

`safe_growth_pct()` implements denominator validation for period growth.

`daily_window_metrics` provides the detailed analytical result.

`store_daily_report` aggregates product-level outputs into a store-level daily report.

These database objects separate reusable calculations from individual reporting queries.

### Transactional integrity

The SQL script includes a failure-case demonstration.

A valid insert is attempted before an invalid insert that violates the positive-unit constraint. The exception block rolls back the work performed inside its subtransaction.

This demonstrates that constraint enforcement and transaction boundaries protect the consistency of the stored facts.

## Performance and operational considerations

### Processing cost

The most important optimization is to aggregate transactions before performing window calculations.

If the transaction table contains millions of records but only a small number of daily product-store combinations, aggregation significantly reduces the number of observations processed by the rolling engine.

Prefix sums provide constant-time interval queries after their construction.

Ranking remains dependent on the size of each comparison population because sorting is needed to establish relative positions.

### Database indexing

The SQL implementation creates indexes on:

- Store, product, and sale date.
- Sale date and store.

These indexes support the grouping and date-filtering workload represented in the reporting queries.

Index selection should be validated against real query plans and production data distribution. Every additional index increases storage requirements and the cost of data modifications.

### Financial precision

The implementations use exact representations for monetary inputs:

- Python uses `Decimal`.
- JavaScript uses integer cents for revenue.
- C++17 uses integer cents.
- Java uses `BigDecimal`.
- PostgreSQL uses `NUMERIC`.

Growth percentages and normalized scores are ratios. They require a separate numerical representation and a defined rounding policy for presentation.

### Date and calendar semantics

The implementations use calendar days rather than transaction counts.

This is important for a seven-day window. Seven transactions may span more or less than seven calendar days.

The SQL implementation creates rows for missing dates before applying `ROWS` frames. This makes the frame equivalent to a consecutive seven-day calendar interval for the generated series.

For more complex systems, the date model may need to account for business calendars, holidays, store operating days, timezone-specific transaction dates, and daylight-saving transitions.

### Ranking interpretation

A ranking is relative to its population.

A product ranked first in one store is not necessarily the highest-revenue product across every store. The partition definition must reflect the intended business question.

A weighted ranking can also hide disagreements between component metrics. A high revenue score and low growth score may produce a competitive combined position depending on the configured weights.

For this reason, the project exposes individual revenue rank, growth rank, normalized scores, and composite rank rather than publishing only the final score.

### Data quality and validation

The implementations reject duplicate event identifiers, invalid dates, invalid quantities, invalid revenue, and excessive processing ranges.

Additional production controls may include:

- Reconciliation between transaction-level totals and daily aggregates.
- Detection of unexpectedly large revenue changes.
- Checks for duplicate source-system deliveries.
- Audit records for ranking-policy changes.
- Explicit treatment of cancelled or returned transactions.
- Monitoring of late-arriving events and historical recalculation requirements.

A zero-activity date should not be confused with a missing source-data feed. The sample deliberately interprets an absent transaction as zero sales within an observed product-store date range. A production system may need independent source-completeness indicators before adopting that interpretation.

## Limitations and design boundaries

The sample uses a fixed seven-day window, static reference data, and a single weighted ranking policy.

It does not implement incremental updates, distributed aggregation, streaming state recovery, late-arriving event correction, or historical policy versioning.

The calendar series begins and ends at the first and last dates containing transactions for each product-store combination. It does not automatically create observations before the first transaction or after the last transaction.

The ranking comparison is store-specific and date-specific. A global cross-store ranking would require a different partition and potentially additional normalization for store scale.

The composite score is a configurable ordinal ranking measure, not a causal model or predictive forecast.

These boundaries keep the implementations focused on the mechanics of advanced window analytics, rolling metrics, and ranking combinations.
