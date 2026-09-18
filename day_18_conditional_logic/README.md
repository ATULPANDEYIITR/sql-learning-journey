# Conditional Logic with SQL CASE, WHEN, THEN, ELSE, and Conditional Expressions

## Topic introduction

Conditional logic allows a program or query to choose a result according to one or more conditions.

In SQL, the primary mechanism for value-producing conditional logic is the `CASE` expression. It can classify rows, calculate derived values, create business categories, control custom sorting, support conditional aggregation, handle exceptional states, and express business rules directly inside a query.

The basic searched form is:

`CASE WHEN condition THEN result ELSE alternative_result END`

A simple form compares one expression against several possible values:

`CASE expression WHEN value1 THEN result1 WHEN value2 THEN result2 ELSE default_result END`

The three implementations in this repository approach the same subject from different perspectives:

- Python uses SQLite to demonstrate actual SQL `CASE` behavior.
- JavaScript models database-style conditional rules at the application layer and demonstrates JavaScript-specific conditional constructs.
- C++ develops an industry-style order-processing and customer-segmentation case study using native data structures, validation, rule evaluation, aggregation, and sorting.

## Fundamental concepts

### Conditional expression

A conditional expression evaluates one or more conditions and produces a value.

This distinction is important in SQL. `CASE` is an expression rather than a procedural `if` statement. Its result can therefore participate in other SQL expressions and clauses.

For example:

`CASE WHEN amount >= 1000 THEN 'Large' ELSE 'Small' END`

produces a value for every applicable row.

That value can be selected, grouped, sorted, aggregated, compared, or combined with other expressions.

### CASE

`CASE` begins a SQL conditional expression.

There are two principal forms:

- Simple `CASE`
- Searched `CASE`

### WHEN

`WHEN` introduces a condition or comparison that is evaluated by `CASE`.

### THEN

`THEN` specifies the value returned when its associated `WHEN` condition matches.

### ELSE

`ELSE` specifies the default value when none of the `WHEN` conditions matches.

`ELSE` is optional. If it is omitted and no condition matches, SQL generally returns `NULL`.

### END

`END` terminates the `CASE` expression.

A complete searched expression has this structure:

`CASE WHEN condition THEN result ELSE default_result END`

A complete simple expression has this structure:

`CASE expression WHEN value THEN result ELSE default_result END`

## Simple CASE

A simple `CASE` compares a single expression with several values.

The Python implementation demonstrates country classification:

`CASE country WHEN 'India' THEN 'Domestic' WHEN 'USA' THEN 'North America' WHEN 'UK' THEN 'United Kingdom' ELSE 'Other' END`

Conceptually, this is equivalent to asking:

- Is `country` equal to `India`?
- Otherwise, is it equal to `USA`?
- Otherwise, is it equal to `UK`?
- Otherwise, use `Other`.

Simple `CASE` is useful when all alternatives involve equality comparisons against one expression.

### When simple CASE is appropriate

Typical examples include:

- Status codes
- Country codes
- Product types
- Payment states
- Category identifiers
- Enumerated values
- Short classification lists

A simple `CASE` becomes less suitable when conditions involve ranges, multiple columns, compound Boolean expressions, or more complex predicates.

## Searched CASE

A searched `CASE` contains independent Boolean conditions.

Example:

`CASE WHEN loyalty_points >= 500 THEN 'Platinum' WHEN loyalty_points >= 200 THEN 'Gold' WHEN loyalty_points >= 100 THEN 'Silver' ELSE 'Standard' END`

Each `WHEN` represents a separate condition.

Searched `CASE` is appropriate for:

- Numeric ranges
- Date conditions
- Multiple-column conditions
- `AND` and `OR`
- Comparisons
- NULL checks
- Business rules
- Threshold-based classifications

The Python implementation uses searched `CASE` extensively for order and customer classification.

## First-match behavior

The order of `WHEN` clauses is part of the meaning of a searched `CASE`.

Consider:

`CASE WHEN amount >= 100 THEN 'Large' WHEN amount >= 1000 THEN 'Very large' ELSE 'Small' END`

The second condition is effectively unreachable for values of `1000` or more because `amount >= 100` has already matched.

The correct ordering for these ranges is:

`CASE WHEN amount >= 1000 THEN 'Very large' WHEN amount >= 100 THEN 'Large' ELSE 'Small' END`

The most restrictive applicable condition should generally appear before broader conditions.

This principle is demonstrated explicitly in all three implementations.

## ELSE and NULL

When no `WHEN` condition matches, `ELSE` supplies the result.

For example:

`CASE WHEN payment_status = 'PAID' THEN 'Completed' ELSE 'Not completed' END`

Without `ELSE`, a non-matching row produces `NULL`.

This difference matters because `NULL` represents an unknown or missing value rather than an ordinary string such as `'Unknown'`.

An explicit `ELSE` is usually preferable when the business meaning of the unmatched state is known.

## NULL and three-valued logic

SQL's treatment of `NULL` differs from ordinary two-valued Boolean logic.

The following is incorrect:

`payment_status = NULL`

The correct test is:

`payment_status IS NULL`

Similarly:

`payment_status IS NOT NULL`

should be used to test whether a value exists.

A comparison involving `NULL` does not normally evaluate to ordinary SQL `TRUE` or `FALSE`; SQL uses three-valued logic involving `TRUE`, `FALSE`, and `UNKNOWN`.

The Python SQLite implementation demonstrates explicit NULL handling.

The JavaScript and C++ programs also model nullable payment status. C++ uses `std::optional<std::string>` to represent a value that may be absent.

## CASE as a derived column

A common use of `CASE` is to derive a category from raw data.

Example:

`CASE WHEN amount = 0 THEN 'Zero-value order' WHEN amount < 100 THEN 'Small' WHEN amount < 1000 THEN 'Medium' WHEN amount < 3000 THEN 'Large' ELSE 'Very large' END`

This converts a numeric measure into a business classification.

The original `amount` remains unchanged while the query produces an additional calculated value.

This pattern is useful for:

- Reports
- Dashboards
- Customer segmentation
- Risk categories
- Revenue bands
- Inventory classifications
- Operational queues

## CASE in SELECT

The `SELECT` clause is one of the most common locations for `CASE`.

The Python implementation creates:

- Market classifications
- Loyalty tiers
- Order-size categories
- Payment descriptions
- Customer segments

The important design principle is that the result should represent a meaningful derived attribute rather than merely duplicate existing data.

## CASE in WHERE

`CASE` can be used to produce a value that is then used by a filter.

The Python implementation demonstrates a query where `CASE` returns `1` for rows satisfying different business conditions and `0` otherwise.

For example, different thresholds can be applied to different payment states.

Although valid, this style should not automatically be preferred. If a direct Boolean predicate expresses the requirement more clearly, a direct predicate may be easier to read and optimize.

For example, a condition such as:

`payment_status = 'PAID' AND amount >= 1000`

is often clearer than wrapping the same logic inside `CASE`.

## CASE in ORDER BY

`CASE` is especially useful for business-specific ordering.

Suppose an operational team wants:

- Pending payments first
- Failed payments second
- Paid payments third
- Missing or unexpected states last

A query can use:

`ORDER BY CASE payment_status WHEN 'PENDING' THEN 1 WHEN 'FAILED' THEN 2 WHEN 'PAID' THEN 3 ELSE 4 END`

The numeric values are priorities rather than business values.

The JavaScript implementation uses a priority map, while the C++ implementation defines an equivalent priority function.

## CASE in GROUP BY

`CASE` can create categories before aggregation.

For example:

`CASE WHEN amount < 100 THEN 'Small' WHEN amount < 1000 THEN 'Medium' ELSE 'Large' END`

can be used as a grouping expression.

The Python implementation calculates:

- Number of orders in each class
- Average order value in each class

This is a common analytical pattern.

## Conditional aggregation

Conditional aggregation combines `CASE` with aggregate functions.

A classic pattern is:

`SUM(CASE WHEN payment_status = 'PAID' THEN 1 ELSE 0 END)`

This counts rows meeting a condition.

Another example is:

`SUM(CASE WHEN payment_status = 'PAID' THEN amount ELSE 0 END)`

This sums only paid amounts.

Conditional aggregation is useful for:

- KPI calculations
- Financial reporting
- Operational dashboards
- Status counts
- Conversion measurements
- Exception monitoring
- Cohort analysis

The Python implementation produces paid, pending, and failed order counts and a paid-order percentage.

The JavaScript and C++ implementations reproduce the same analytical concept using filtering and accumulation.

## CASE with calculations

Conditional logic can control calculations.

For example:

`CASE WHEN order_count = 0 THEN 0 ELSE total_amount / order_count END`

prevents an invalid average calculation for an empty group.

The Python implementation demonstrates this idea with average order value.

In production systems, it is important to define the business meaning of exceptional conditions rather than merely preventing an arithmetic error.

## CASE with multiple columns

A condition can combine multiple fields.

Example:

`CASE WHEN total_spend >= 5000 AND loyalty_points >= 500 THEN 'Strategic customer' ... END`

This creates a classification based on both monetary behavior and loyalty activity.

The customer report in all three implementations uses this principle.

## AND and OR inside WHEN

`WHEN` can contain Boolean logic.

Examples include:

`WHEN amount >= 1000 AND payment_status = 'PAID' THEN 'High-value paid order'`

and:

`WHEN total_spend >= 2000 OR loyalty_points >= 300 THEN 'High-value customer'`

Parentheses should be used when they improve clarity or when operator precedence could make the intended logic ambiguous.

## Nested CASE

A `CASE` expression can contain another `CASE`.

The Python implementation demonstrates a nested payment-and-value classification.

Conceptually:

`CASE WHEN payment_status = 'PAID' THEN CASE WHEN amount >= 3000 THEN 'Paid - high value' ELSE 'Paid - lower value' END ELSE 'Not paid' END`

Nested expressions are useful when a business rule naturally has multiple levels.

Deep nesting can become difficult to review and test. When conditional logic becomes large, a reference table, view, generated attribute, or application-level rule engine may provide a cleaner design.

## COALESCE

`COALESCE` is related to conditional expressions but is specialized for selecting the first non-NULL expression.

Example:

`COALESCE(payment_status, 'UNKNOWN')`

returns the payment status when it exists and `'UNKNOWN'` when it is NULL.

The Python implementation demonstrates this directly.

`COALESCE` is often clearer than a `CASE` expression when the only requirement is NULL fallback.

## NULLIF

`NULLIF` returns `NULL` when its two expressions are equal.

Example:

`NULLIF(amount, 0)`

returns `NULL` for zero and otherwise returns the amount.

It is useful when zero has a special meaning or when a value should be transformed into NULL before further processing.

The Python implementation demonstrates `NULLIF` alongside `COALESCE`.

## Python implementation

The Python file uses the standard-library `sqlite3` module.

This makes it possible to execute real SQL without requiring a separate database server or third-party Python package.

The implementation creates:

- `customers`
- `orders`

The database includes realistic values for:

- Countries
- Loyalty points
- Order amounts
- Payment statuses
- Missing payment statuses
- Zero-value orders

### SQL examples demonstrated by Python

The Python implementation covers:

- Simple `CASE`
- Searched `CASE`
- `CASE` without `ELSE`
- `CASE` in `SELECT`
- `CASE` in `WHERE`
- `CASE` in `ORDER BY`
- `CASE` in `GROUP BY`
- Conditional aggregation
- Nested `CASE`
- NULL handling
- `COALESCE`
- `NULLIF`
- Guarded calculations
- Parameterized conditional logic
- Customer segmentation
- Boundary-value testing

### Python-level equivalent

The SQL expression:

`CASE WHEN amount >= 3000 THEN 'Very large' WHEN amount >= 1000 THEN 'Large' ELSE 'Small' END`

has a natural Python equivalent using:

`if`
`elif`
`else`

Python also provides a conditional expression:

`value_if_true if condition else value_if_false`

This is particularly appropriate for a short two-way choice.

## JavaScript implementation

The JavaScript implementation demonstrates how database-style conditional requirements are commonly reproduced at an application layer.

JavaScript does not provide SQL `CASE` syntax.

Instead, several native constructs are useful.

### if / else if / else

An `if` / `else if` chain closely models searched `CASE` semantics because conditions are evaluated in sequence and the first matching branch determines the result.

### switch

A `switch` statement is useful for simple value-based branching.

The JavaScript `simpleCaseLike` function uses `switch` to classify country values.

It provides a conceptual equivalent to:

`CASE country WHEN 'India' THEN ... WHEN 'USA' THEN ... ELSE ... END`

### Ternary operator

JavaScript's ternary operator is a conditional expression:

`condition ? valueIfTrue : valueIfFalse`

It is concise for a simple two-way choice.

Long nested ternaries should generally be avoided when they reduce readability.

### Nullish coalescing

JavaScript provides:

`value ?? fallback`

for selecting a fallback when the value is `null` or `undefined`.

This is related to SQL `COALESCE`, although the languages have different type systems and null semantics.

### Rule arrays

The JavaScript implementation also creates a data-driven discount rule array.

Each rule contains:

- A name
- A predicate
- A discount rate

The engine evaluates rules in order and stops at the first match.

This demonstrates how SQL `WHEN` clauses can inspire application-level rule-engine designs.

## C++ case study

The C++ implementation models an order-processing system.

The scenario includes:

- Customers
- Orders
- Payment status
- Order values
- Loyalty points
- Discounts
- Customer segmentation
- Operational payment prioritization

The implementation uses C++17 standard-library features only.

### Problem being solved

The system needs to convert raw transactional data into operational decisions.

For each order it determines:

- Order-size class
- Payment state
- Discount rule
- Processing priority

For each customer it determines:

- Total spend
- Paid spend
- Order count
- Customer segment
- Payment profile

### Data structures

The implementation defines:

`Order`

This contains the order identifier, customer identifier, amount, and nullable payment status.

`Customer`

This contains the customer identifier, name, country, and loyalty points.

`DiscountRule`

This stores a rule name, threshold, and discount rate.

`CustomerReport`

This represents calculated reporting data.

`std::optional<std::string>` is used for payment status because an order may have no status.

## C++ rule evaluation

The `calculateDiscount` function accepts a vector of discount rules.

The rules are ordered:

- Premium
- Large
- Standard

The first matching rule determines the result.

This is directly analogous to searched SQL `CASE`.

The implementation also explains the complexity:

- `R` rules require `O(R)` evaluation per input.
- A fixed number of conditions can behave effectively as constant-time logic.

## C++ customer segmentation

The customer segmentation function evaluates compound conditions.

The rules are:

- Strategic customer when spending and loyalty are both high.
- High-value customer when spending or loyalty reaches the second threshold.
- Growing customer when spending or loyalty reaches the lower threshold.
- Standard customer otherwise.

This demonstrates how SQL `AND` and `OR` conditions translate into C++ Boolean expressions.

## C++ conditional aggregation

The C++ program calculates:

- Total orders
- Paid orders
- Pending orders
- Failed orders
- Paid amount
- Paid percentage

The logic corresponds conceptually to SQL conditional aggregation using `SUM(CASE WHEN ...)`.

The implementation explicitly checks the optional payment state before comparing its value.

## C++ conditional sorting

The case study prioritizes payment states using a priority function.

The priority is:

- Pending
- Failed
- Paid
- Missing or unknown

The program then uses `std::stable_sort`.

This corresponds conceptually to SQL `ORDER BY CASE`.

The secondary ordering places larger amounts before smaller amounts within the same payment priority.

## Validation and error handling

Conditional logic should not be responsible for silently accepting invalid input.

The C++ program validates:

- Positive order IDs
- Positive customer IDs
- Finite, non-negative amounts
- Recognized payment states

Invalid data raises standard C++ exceptions.

The JavaScript implementation uses `TypeError` and `RangeError` for analogous validation failures.

The Python implementation relies on SQLite constraints for database structure and explicit logic for classification.

## Edge cases

Important conditional-logic edge cases include:

### Exact threshold

If a rule says:

`amount >= 1000`

then `1000` matches the rule.

If it says:

`amount > 1000`

then `1000` does not match.

### Values immediately around a threshold

A robust test set should include values such as:

- `99.99`
- `100.00`
- `100.01`

and:

- `999.99`
- `1000.00`
- `1000.01`

The implementations include these boundary tests.

### Zero

Zero may represent:

- A valid value
- A missing calculation
- A special transaction
- A denominator that must be protected

The correct treatment depends on the business rule.

### NULL

A NULL payment status is different from a literal status such as `'UNKNOWN'`.

The Python implementation explicitly distinguishes the missing state.

### Empty input

Aggregate calculations must define their behavior when no rows exist.

A system may need to return zero, NULL, or another explicitly defined value depending on the metric.

### Unexpected categories

An `ELSE` branch provides a controlled result for unexpected values when that is appropriate.

## Common mistakes

### Confusing simple and searched CASE

Incorrect conceptual structure:

`CASE country WHEN country = 'India' THEN 'Domestic' END`

The simple form compares `country` directly with values.

Correct simple structure:

`CASE country WHEN 'India' THEN 'Domestic' END`

Correct searched structure:

`CASE WHEN country = 'India' THEN 'Domestic' END`

### Comparing NULL with equals

Incorrect:

`payment_status = NULL`

Correct:

`payment_status IS NULL`

### Incorrect rule order

Incorrect:

`CASE WHEN amount >= 100 THEN 'Large' WHEN amount >= 1000 THEN 'Very large' ELSE 'Small' END`

The second condition is shadowed by the first.

Correct:

`CASE WHEN amount >= 1000 THEN 'Very large' WHEN amount >= 100 THEN 'Large' ELSE 'Small' END`

### Missing ELSE

Omitting `ELSE` can unintentionally introduce NULL values.

An explicit `ELSE` makes the default behavior visible.

### Overusing CASE

`CASE` is powerful, but not every conditional requirement should be expressed with it.

If a direct predicate is clearer, use the direct predicate.

If rules change frequently, consider a data-driven rule structure rather than embedding a long list of conditions in SQL.

### Excessive nesting

A deeply nested `CASE` expression can become difficult to test and maintain.

Breaking the logic into multiple derived columns, common table expressions, views, or reference tables can improve maintainability.

## Important distinctions and comparisons

| Concept | SQL | Python | JavaScript | C++ |
|---|---|---|---|---|
| Multi-condition branching | Searched `CASE` | `if` / `elif` | `if` / `else if` | `if` / `else if` |
| Value matching | Simple `CASE` | `if` / dictionary patterns | `switch` | `switch` for suitable scalar types or conditional comparisons |
| Short conditional expression | `CASE` | Conditional expression | Ternary operator | Ternary operator |
| NULL fallback | `COALESCE` | Explicit `None` handling | `??` | `std::optional` plus explicit handling |
| Custom sorting | `ORDER BY CASE` | `sorted(..., key=...)` | `Array.sort` comparator | `std::sort` / `std::stable_sort` comparator |
| Rule engine | `CASE` or reference table | Ordered rule functions | Ordered predicate objects | Ordered rule objects/functions |
| Conditional aggregation | `SUM(CASE...)` | loops or comprehensions | `filter` / `reduce` | loops or standard algorithms |

These constructs are conceptually related but are not identical.

SQL is declarative. The query describes the desired result.

Python, JavaScript, and C++ are general-purpose programming languages where conditional constructs participate in procedural or functional program execution.

## Business-rule design

Conditional logic is often a direct representation of business policy.

Examples include:

- Customer segmentation
- Pricing tiers
- Credit categories
- Tax brackets
- Shipping categories
- Fraud-review flags
- Payment states
- Service-level priorities
- Inventory status
- Employee classifications

The critical design question is whether the rule should remain embedded in code or become data.

### Stable rules

A small set of stable rules can be expressed clearly using `CASE`.

Example:

`CASE WHEN amount >= 3000 THEN 'Premium' WHEN amount >= 1000 THEN 'Large' ELSE 'Standard' END`

### Frequently changing rules

If business users frequently modify thresholds, categories, or conditions, a reference table may be more maintainable.

For example, a pricing-rule table can store:

- Minimum threshold
- Maximum threshold
- Category
- Rate
- Effective date
- Priority

This makes rules data rather than hard-coded expressions.

## Performance considerations

A simple `CASE` expression is usually inexpensive.

The more significant performance costs in analytical queries often come from:

- Large table scans
- Joins
- Aggregation
- Sorting
- Network transfer
- Repeated computation
- Poor indexing

A `CASE` expression can still affect optimization when it is applied to indexed columns in predicates.

For example, transforming an indexed column through a complex expression may make it harder for a database optimizer to use an index efficiently.

When a direct predicate expresses the same requirement, it is often preferable.

### Repeated CASE expressions

If the same large expression appears throughout many queries, maintenance becomes a concern.

Possible architectural alternatives include:

- Views
- Generated columns
- Reference tables
- Materialized data
- Centralized application rules

The appropriate option depends on database capabilities, update frequency, consistency requirements, and query workload.

## Rule precedence and maintainability

Rule order should be documented whenever conditions overlap.

A useful design approach is to identify:

- Most specific rules
- Broader rules
- Default state

Then test every boundary and overlapping region.

For a threshold system:

`>= 3000`

should generally be checked before:

`>= 1000`

which should generally be checked before:

`>= 500`

if the intended categories are mutually exclusive ranges.

## Testing conditional logic

Conditional logic should be tested with more than ordinary examples.

A strong test set includes:

- Minimum valid value
- Maximum valid value
- Zero
- Negative invalid values
- Exact thresholds
- Values immediately below thresholds
- Values immediately above thresholds
- NULL values
- Empty collections
- Unexpected categories
- Conflicting conditions

The three implementations include explicit boundary and failure tests.

## Security considerations

`CASE` itself is not an injection mechanism, but SQL containing conditional logic can still be vulnerable if application input is concatenated directly into SQL.

Parameterized queries should be used for external values.

The Python implementation demonstrates parameter binding when applying a dynamic threshold.

The safe pattern is to bind data as parameters rather than constructing SQL by concatenating untrusted strings.

Conditional rules can also affect authorization, pricing, or financial calculations. Such logic should be validated and tested because a logically incorrect condition can produce an incorrect business outcome even when there is no conventional security vulnerability.

## Implementation considerations

A reliable conditional implementation should have:

- Clearly defined conditions
- Explicit rule ordering
- Deliberate NULL behavior
- Meaningful defaults
- Boundary tests
- Validation
- Appropriate error handling
- Stable output types
- Readable expressions
- Performance awareness

For important business rules, the implementation should also make it possible to determine why a particular result was produced.

The JavaScript discount rule engine exposes the matching rule name, while the C++ case study reports the selected classification.

## Real-world relevance

Conditional SQL is central to analytical and operational systems.

A reporting query may use `CASE` to transform transactional data into management metrics.

A financial system may use it to classify accounts according to thresholds.

An e-commerce platform may use it to determine discounts, shipping categories, customer segments, or payment states.

A security or monitoring system may use it to assign severity levels.

A data-quality pipeline may use it to identify missing, invalid, or exceptional values.

The important skill is not simply memorizing the `CASE WHEN THEN ELSE END` syntax. It is designing conditions so that the complete set of business states is represented correctly, particularly where rules overlap, values are missing, and boundaries matter.

## Files and implementation roles

### Python

The Python implementation is the primary SQL demonstration.

It executes real SQLite queries and shows how `CASE` interacts with:

- `SELECT`
- `WHERE`
- `ORDER BY`
- `GROUP BY`
- Aggregate functions
- Common table expressions
- NULL handling
- Parameters

It is the most direct implementation for learning actual SQL behavior.

### JavaScript

The JavaScript implementation focuses on application-side equivalents.

It demonstrates:

- `switch`
- `if` / `else if` / `else`
- Ternary expressions
- Nullish coalescing
- Ordered rule functions
- Validation
- Custom sorting
- Filtering and aggregation

This is useful when a system must apply similar business rules after data has been retrieved from a database.

### C++

The C++ implementation presents the complete technical case study.

It demonstrates:

- Structured data modeling
- `std::optional`
- Validation
- Rule objects
- First-match evaluation
- Conditional aggregation
- Custom sorting
- Customer segmentation
- Exception handling
- Complexity analysis
- Boundary testing

The implementation shows how the same conceptual rule model can be built into a strongly typed, compiled application.

## Practical design checklist

When writing a `CASE` expression, verify:

- Is this a simple or searched `CASE`?
- Are the conditions mutually exclusive?
- If they overlap, is the order intentional?
- Does every expected state have a result?
- Is `ELSE` required?
- What should happen for NULL?
- What happens at exact boundaries?
- Are numeric comparisons using the intended `>`, `>=`, `<`, or `<=` operator?
- Are `AND` and `OR` grouped correctly?
- Could a lookup table express changing rules more cleanly?
- Could a direct predicate be clearer than `CASE`?
- Could the expression interfere with efficient filtering?
- Has the logic been tested against invalid and unexpected values?
- Is the result type appropriate for every branch?

## Execution

The Python file requires Python 3 and uses only the standard library.

The JavaScript file can be executed with a modern Node.js runtime.

The C++ case study is written for C++17 or later and uses only the standard library.

All three programs contain executable examples rather than placeholders and include boundary, validation, rule-precedence, and conditional-classification demonstrations.
