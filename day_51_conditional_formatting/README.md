# Conditional Aggregation: SUM(CASE), COUNT(CASE), Filtered Metrics, and KPI Calculations

## Scope

Conditional aggregation calculates an aggregate only for rows satisfying a condition.

The central pattern is:

`SUM(CASE WHEN condition THEN value ELSE 0 END)`

It can also be expressed as:

`COUNT(CASE WHEN condition THEN 1 END)`

PostgreSQL provides a direct form:

`SUM(value) FILTER (WHERE condition)`

These mechanisms are useful when one dataset must produce several metrics with different eligibility rules. A sales dataset, for example, can produce completed revenue, cancelled value, web revenue, returned-order counts, and completion rates without creating separate datasets for every metric.

The implementations use the same business scenario while emphasizing different programming models:

| File | Primary perspective | Main implementation |
|---|---|---|
| Python | Data-oriented simulation | Predicate-based conditional aggregation and regional KPIs |
| JavaScript | Event-driven reporting | Asynchronous KPI service and functional reducers |
| C++17 | Algorithmic analytics engine | Generic predicates, aggregation algorithms, and regional metrics |
| Java 17 | Enterprise domain model | Records, enums, immutable collections, policies, and validation |
| PostgreSQL | Relational analytics | `CASE`, `COUNT`, `FILTER`, grouped metrics, CTEs, views, constraints, and transactions |

## Conditional Aggregation Model

A conventional aggregate treats every row alike.

A conditional aggregate introduces an eligibility predicate:

`aggregate(value WHERE condition)`

For example, completed revenue is conceptually:

`SUM(amount WHERE status = completed)`

Using portable SQL syntax, this becomes:

`SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END)`

The condition determines whether the row contributes to the aggregate. The row itself remains part of the source relation.

This distinction is important. Conditional aggregation does not necessarily remove rows from the query result. It changes which rows contribute to a particular metric.

## SUM(CASE)

`SUM(CASE)` is useful when the metric requires a numeric contribution.

For completed revenue, each completed order contributes its amount and every other order contributes zero:

`SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END)`

Multiple business measures can therefore be calculated from the same rows:

| Metric | Condition | Contribution |
|---|---|---|
| Completed revenue | Status is completed | Amount |
| Cancelled value | Status is cancelled | Amount |
| Web revenue | Completed and web | Amount |
| Mobile revenue | Completed and mobile | Amount |
| Returned completed value | Completed and returned | Amount |

The Python, C++, and SQL implementations use this concept directly.

## COUNT(CASE)

`COUNT(CASE WHEN condition THEN 1 END)` counts rows satisfying the condition.

For example:

`COUNT(CASE WHEN status = 'completed' THEN 1 END)`

The `CASE` expression returns `1` for eligible rows and `NULL` for other rows. `COUNT(expression)` counts non-null results.

This makes it suitable for metrics such as:

- Completed orders
- Cancelled orders
- Pending orders
- Returned completed orders
- Orders belonging to a particular channel

A conditional count should not be confused with `COUNT(*)`. `COUNT(*)` counts every input row, while `COUNT(CASE ...)` counts only rows producing a non-null conditional result.

## Filtered Aggregates

PostgreSQL supports a more direct syntax:

`COUNT(*) FILTER (WHERE status = 'completed')`

and:

`SUM(amount) FILTER (WHERE status = 'completed')`

The SQL implementation deliberately includes both forms.

`CASE` is broadly portable SQL and makes the conditional contribution explicit. `FILTER` expresses the aggregate condition separately from the value being aggregated and is particularly readable when a query contains many metrics.

The two approaches should produce equivalent results when their null-handling rules are equivalent.

## KPI Construction

A KPI normally combines conditional counts or sums into a business measure.

The example dataset contains:

- Completed orders
- Cancelled orders
- Pending orders
- Sales channels
- Regions
- Monetary order values
- Completed orders that were returned

A completion rate is calculated as:

`completed_orders / total_orders × 100`

A cancellation rate is:

`cancelled_orders / total_orders × 100`

Division by zero must be handled explicitly. The SQL implementation uses `NULLIF(total_orders, 0)`, while the application implementations check for an empty denominator before calculating the percentage.

The result is a business-safe KPI rather than an unguarded arithmetic expression.

## Data Model

The relational implementation separates customers, orders, KPI policies, and KPI evaluations.

    customers
        |
        | 1-to-many
        v
      orders
        |
        | conditional aggregation
        v
    KPI reports
        |
        v
    KPI policy evaluation
        |
        v
    kpi_evaluations

`customers` provides the grouping dimension.

`orders` provides the transactional facts.

`kpi_policies` defines thresholds.

`kpi_evaluations` stores calculated KPI results and the outcome of policy evaluation.

This separation prevents a policy threshold from being embedded permanently inside a reporting query.

## Python Implementation

The Python file models each order with a validated immutable `dataclass`.

The `Order` object validates:

- Positive identifiers
- Non-empty regions
- Supported statuses
- Supported sales channels
- Non-negative amounts

`conditional_sum()` represents the numeric form of conditional aggregation.

`conditional_count()` represents a conditional count.

`filtered_count()` provides a separate count implementation to emphasize that the business operation is the same even when the implementation mechanism differs.

`average_if()` calculates an average only over rows satisfying a predicate and returns zero when no row qualifies.

The KPI calculation combines these functions to produce:

- Total orders
- Completed orders
- Cancelled orders
- Returned completed orders
- Completed revenue
- Cancelled value
- Web revenue
- Mobile revenue
- Average completed order value
- Completion rate
- Cancellation rate

The regional report first groups orders by region and then evaluates conditions inside each group.

An explicit invariant verifies that completed, cancelled, and pending counts partition the complete dataset.

## JavaScript Implementation

The JavaScript file uses classes and array operations to provide a functional aggregation model.

`ConditionalAggregator` contains reusable operations:

- `sum()`
- `count()`
- `average()`
- `percentage()`

Each operation accepts a predicate rather than embedding a specific business rule.

This makes conditions such as:

`status === "completed"`

and:

`status === "completed" && channel === "web"`

first-class parts of the reporting logic.

`KPIReportService` provides an asynchronous interface. The example uses a resolved promise to model the asynchronous boundary that would normally surround a database or HTTP operation.

The regional report demonstrates grouping followed by conditional aggregation.

The implementation also validates the partition of order statuses and checks that a condition with no matches returns zero.

## C++17 Implementation

The C++ implementation treats conditional aggregation as a generic algorithmic operation.

`conditionalSum()` accepts a predicate and accumulates values only when that predicate returns true.

`conditionalCount()` uses `std::count_if`.

`conditionalAverage()` composes the sum and count operations and explicitly handles an empty matching set.

The use of predicates avoids coupling the aggregation engine to one particular metric.

The domain uses strongly typed enums for order status and sales channel. This prevents arbitrary strings from representing these controlled values inside the aggregation engine.

`RevenueAnalytics` owns the order collection and exposes overall and regional metrics.

The regional implementation accumulates metrics into a `std::map`, making region-specific calculations independent from the global report.

The validation routine checks that the three mutually exclusive statuses account for every order.

## Java 17 Implementation

The Java implementation uses an enterprise-oriented domain structure.

`Order` is a Java record, making its transactional state immutable after construction.

`OrderStatus` and `SalesChannel` are enums, preventing unsupported domain values.

`KpiReport` and `RegionalKpi` are also records, representing immutable reporting results.

`Aggregator` centralizes conditional sum, count, average, and percentage operations.

Java streams provide declarative filtering and aggregation without sacrificing explicit predicates.

`RevenueAnalyticsService` owns an immutable copy of the supplied order list. It generates both global and regional reports.

`GovernancePolicy` separates KPI calculation from policy evaluation. A report can therefore be evaluated against a threshold without modifying the aggregation logic.

This distinction is useful in enterprise systems where reporting rules and governance policies frequently change independently.

## PostgreSQL Implementation

The PostgreSQL script creates a dedicated schema named `conditional_aggregation_demo`.

The database constraints enforce important invariants before aggregation occurs.

The `orders` table requires:

- A valid customer reference
- An approved status
- An approved channel
- A non-negative amount
- Returned orders to be completed

This prevents invalid source data from silently corrupting KPI calculations.

### Portable Conditional Aggregation

`order_kpi_report` demonstrates:

`SUM(CASE ...)`

and:

`COUNT(CASE ...)`

The view calculates several KPIs in a single scan of the orders relation.

### PostgreSQL FILTER

`channel_kpi_report` uses PostgreSQL's `FILTER` clause.

This is particularly useful when several aggregates operate over different subsets of the same input relation.

For example, web, mobile, and store revenue can be expressed as separate filtered sums.

### Grouped Conditional Aggregation

`regional_kpi_report` joins customers to orders and groups by region.

The use of a `LEFT JOIN` preserves regions even when there are no orders. `COUNT(o.order_id)` therefore avoids counting the null-extended join row as an order.

`COALESCE()` converts an empty revenue result into zero where appropriate.

### CTE-Based KPI Evaluation

The policy evaluation query uses two CTEs.

The first CTE calculates base KPI values.

The second derives the completion rate.

The final query compares the resulting KPI against each configured policy.

This separates metric construction from policy evaluation and makes the calculation easier to validate.

### Historical KPI Storage

The `kpi_evaluations` table stores the calculated KPI values and policy outcome.

The transaction creates the evaluation as one atomic operation.

This matters when a KPI snapshot must represent a consistent point in time rather than a collection of independently calculated values.

## Edge Cases

Conditional aggregation has several important edge cases.

### No Matching Rows

A conditional sum may have no qualifying rows.

Using:

`SUM(CASE WHEN condition THEN amount ELSE 0 END)`

normally produces zero because every row contributes zero.

A filtered `SUM()` can return `NULL` when no rows satisfy its filter. The SQL implementation therefore uses `COALESCE()` where a business metric requires an explicit zero.

### Empty Dataset

A percentage with zero rows must not divide by zero.

The application implementations explicitly check the denominator.

PostgreSQL uses `NULLIF()` to turn a zero denominator into `NULL`, preventing a database error.

### NULL Values

`COUNT(expression)` ignores null values.

This is why:

`COUNT(CASE WHEN condition THEN 1 END)`

works as a conditional count.

`COUNT(*)` has different semantics because it counts rows regardless of expression nullability.

### Overlapping Conditions

Conditions do not have to be mutually exclusive.

For example, an order can contribute simultaneously to:

- Completed revenue
- Web revenue
- Returned completed orders

This is correct when the metrics represent different dimensions.

Mutually exclusive categories require different validation. The example explicitly verifies that completed, cancelled, and pending statuses partition all orders.

## Performance

Conditional aggregation is generally efficient because multiple metrics can be computed during the same grouped aggregation operation.

A query containing several conditional aggregates can often process the same input relation once rather than issuing separate queries for each KPI.

Useful database indexes depend on the surrounding workload.

The example indexes:

- Customer references
- Order date and status
- Customer region relationships

Indexes should support filtering, joining, or grouping patterns that occur frequently. Creating an index for every conditional metric is usually unnecessary because an aggregate condition does not automatically imply that a separate index will improve the aggregate.

For very large analytical workloads, partitioning, materialized aggregates, column-oriented systems, or precomputed reporting tables may become appropriate depending on data volume and query frequency.

## Accuracy and Monetary Values

The application implementations use decimal arithmetic where practical.

The Java implementation uses `BigDecimal`.

The Python implementation uses `Decimal`.

The PostgreSQL implementation uses `NUMERIC`.

The C++ example uses `double` for a compact executable analytics case study. Production financial systems should normally use a fixed-point or decimal representation rather than binary floating-point arithmetic when exact monetary representation is required.

## Security and Data Integrity

Conditional aggregation itself is not an authorization mechanism.

A report should only aggregate rows the requesting principal is allowed to see.

Database constraints protect data integrity but do not replace authorization.

The SQL model uses foreign keys and checks to prevent invalid relationships and invalid business states.

Application-level aggregation should validate incoming records before they enter the calculation pipeline. This prevents malformed status values, negative amounts, and invalid categories from producing misleading KPIs.

When conditional metrics are built from user-selected dimensions or filters, parameterized queries should be used rather than constructing SQL predicates through string concatenation.

## Distinguishing the Four Core Aggregation Patterns

| Pattern | Purpose | Example |
|---|---|---|
| `SUM(CASE ...)` | Conditional numeric contribution | Completed revenue |
| `COUNT(CASE ...)` | Conditional row count | Completed orders |
| `FILTER (WHERE ...)` | PostgreSQL conditional aggregate | Web revenue |
| KPI calculation | Derived business measure | Completion rate |

These mechanisms are related but are not interchangeable in every situation.

A conditional sum answers how much qualifying rows contribute.

A conditional count answers how many rows qualify.

A filtered aggregate specifies the qualifying rows directly in PostgreSQL.

A KPI may combine several aggregates into a derived measure and may therefore require explicit handling of denominator, rounding, thresholds, and empty datasets.

## Practical Workflow

A robust conditional KPI workflow follows this structure:

    Transactional rows
           |
           v
    Validate domain values
           |
           v
    Define metric conditions
           |
           +----> conditional counts
           |
           +----> conditional sums
           |
           +----> filtered aggregates
           |
           v
    Group by required dimensions
           |
           v
    Calculate derived KPIs
           |
           v
    Handle zero/empty conditions
           |
           v
    Validate metric invariants
           |
           v
    Evaluate business thresholds
           |
           v
    Store or present KPI results

The implementations maintain this separation so that the condition defining a metric is distinct from the mechanism used to calculate it and from the policy that interprets the resulting KPI.
