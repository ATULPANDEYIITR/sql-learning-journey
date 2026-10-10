# JOIN Pitfalls: Duplicate Rows, Cartesian Products, NULL Behavior, and Incorrect Joins

## Scope

JOIN errors are often not syntax errors. The SQL statement can execute successfully while producing a result whose meaning is wrong.

The central issue is **cardinality**: the number of rows on each side of a relationship and the grain of the desired result. A customer-to-order relationship can legitimately produce several rows for one customer. Two independent one-to-many relationships can multiply each other. A missing predicate can produce a Cartesian product. A nullable key can behave differently from an ordinary value. A predicate placed in the wrong part of an outer join can remove rows that the query was intended to preserve.

This learning artifact treats these behaviors as separate technical problems:

- **Duplicate rows** focus on legitimate one-to-many and many-to-many relationships whose multiplicity may be mistaken for duplication.
- **Accidental Cartesian products** focus on missing or overly broad join predicates.
- **NULL behavior** focuses on SQL's three-valued logic and the fact that ordinary equality does not match NULL to NULL.
- **Incorrect joins** focus on using the wrong key, incomplete composite predicates, incorrect relationship scope, and failure to establish the intended result grain.

The implementations use a repository-development governance domain because pull requests, reviews, status checks, and branch policies naturally contain multiple one-to-many relationships. The same relational patterns occur in customer orders, financial transactions, inventory systems, audit records, and operational reporting.

## The Central Concept: Result Grain

Before writing a JOIN, define what one output row represents.

A report may be:

| Intended grain | One row represents |
| --- | --- |
| Customer | One customer |
| Customer-order | One customer and one order |
| Pull request | One pull request |
| Pull request-review | One pull request and one review |
| Pull request-status check | One pull request and one status check |
| Pull request-review-comment | One review comment attached to one review |

A JOIN does not automatically preserve the grain of the left table.

Suppose one customer has three orders. A customer-to-order JOIN naturally produces three rows for that customer. The repeated customer attributes are not necessarily duplicate records. They are repeated because the output grain has changed from customer to customer-order.

The first question should therefore be:

> What does one row in the final result mean?

The second question should be:

> Is every joined table at a compatible grain for that result?

The code examples repeatedly make this distinction explicit.

## Why One-to-Many JOINs Produce Repeated Parent Rows

Consider:

    customers
    customer_id | name
    1           | Asha
    2           | Ravi

and:

    orders
    order_id | customer_id | amount
    101      | 1           | 250
    102      | 1           | 125
    103      | 2           | 500

The relationship is:

    Customer 1
       |
       +--- Order 101
       |
       +--- Order 102

A correct JOIN on `customer_id` returns two rows for Asha.

That is not a JOIN bug. It is the relational representation of the one-to-many relationship.

The problem appears when the report is expected to remain at customer grain.

For example, this calculation is dangerous if the result is later interpreted as one row per customer:

    SELECT c.customer_id, c.name, o.amount
    FROM customer c
    JOIN orders o
      ON o.customer_id = c.customer_id;

If the intended result is customer-level, the order table should usually be reduced to customer grain first:

    SELECT
        customer_id,
        SUM(amount) AS total_amount
    FROM orders
    GROUP BY customer_id;

The Python, JavaScript, C++, Java, and SQL artifacts all demonstrate variations of this principle.

## Independent One-to-Many Relationships Cause Multiplication

The most important advanced JOIN pitfall occurs when two independent child tables are joined directly to the same parent.

The repository governance model contains:

    PullRequest
        |
        +--- Review
        |
        +--- StatusCheck

Suppose pull request 101 has:

- two reviews
- three status checks

A direct JOIN between the pull request, reviews, and status checks can produce:

    2 reviews × 3 checks = 6 rows

The six rows do not mean the pull request has six reviews or six checks.

They represent all possible review/check combinations associated with that pull request.

This distinction is critical.

A query such as:

    SELECT
        pr.pull_request_id,
        r.review_id,
        sc.check_name
    FROM pull_request pr
    JOIN review r
      ON r.pull_request_id = pr.pull_request_id
    JOIN status_check sc
      ON sc.pull_request_id = pr.pull_request_id;

is structurally valid.

It becomes logically wrong when the application expects one row per pull request.

The correct approach is usually to aggregate each independent child relationship first:

    reviews -> one row per pull request
    checks  -> one row per pull request

and then join those summaries to the pull request.

This is the purpose of the SQL `review_summary` and `check_summary` CTEs.

## Accidental Cartesian Products

A Cartesian product pairs every row from the left relation with every row from the right relation.

For:

    left = 3 rows
    right = 4 rows

the result contains:

    3 × 4 = 12 rows

A deliberate `CROSS JOIN` can be useful. For example, a planning system may intentionally generate every combination of regions and sales channels.

The problem occurs when the same multiplication happens accidentally.

A missing predicate is a common cause:

    SELECT *
    FROM employees e
    JOIN departments d;

The intended relationship might have been something such as:

    ON e.department_id = d.department_id

A JOIN should not be considered correct merely because it executes.

The result cardinality must be checked against the expected relationship.

The Python and JavaScript implementations explicitly calculate Cartesian products so that the multiplication can be observed rather than hidden behind an abstract explanation.

## Overly Broad Join Predicates

A JOIN can contain a predicate and still be incorrect.

Suppose accounts and invoices both contain a `region` column.

Joining on:

    account.region = invoice.region

may appear reasonable, but region is not necessarily an identifier.

If two accounts belong to the same region and two invoices belong to that region, the relationship becomes:

    2 accounts × 2 invoices = 4 matches

The JOIN should normally use the business key that identifies the actual relationship, such as `customer_id`.

A useful diagnostic question is:

> Is the JOIN column actually unique at the required grain?

The SQL artifact provides queries that count matching keys. The C++ and Java implementations also make relationship scope explicit rather than relying on a convenient descriptive attribute.

## Composite Keys and Incomplete JOIN Conditions

Some entities are identified by more than one attribute.

Suppose an employee's assignment rate is identified by:

    employee_id + assignment

Joining only on `employee_id` is incomplete.

An employee with two assignments could match both rate records.

The intended relationship requires both predicates:

    employee.employee_id = rate.employee_id
    AND employee.assignment = rate.assignment

This is not merely a style preference. Omitting one component changes the mathematical relationship represented by the query.

Composite-key mistakes are particularly dangerous because the query may return plausible values. The wrong rows are often harder to detect than an obvious empty result.

## NULL Behavior

SQL NULL is not an ordinary value.

With ordinary equality:

    NULL = NULL

does not evaluate to `TRUE`.

It evaluates to `UNKNOWN`.

Therefore:

    SELECT *
    FROM left_table l
    JOIN right_table r
      ON l.key = r.key;

does not match two rows where both `key` values are NULL.

This differs from many application-language equality models.

The SQL implementation demonstrates the distinction using:

    ON l.key = r.key

and:

    ON l.key IS NOT DISTINCT FROM r.key

`IS NOT DISTINCT FROM` deliberately treats two NULL values as equivalent for comparison purposes.

That operation should only be used when the business meaning really requires NULL-to-NULL matching. It is not a general replacement for `=`.

The JavaScript implementation highlights an important integration risk: JavaScript `Map` can use `null` as a key, so an in-memory join can accidentally behave differently from the SQL JOIN that produced the data.

Database semantics and application semantics therefore need to be considered together.

## LEFT JOIN and the WHERE-Clause Trap

A LEFT JOIN preserves rows from the left relation even when there is no matching right-side record.

For example:

    SELECT
        c.customer_id,
        o.order_id
    FROM customer c
    LEFT JOIN orders o
      ON o.customer_id = c.customer_id;

A customer without orders remains in the result, with NULL values for the order columns.

A common mistake is then to write:

    WHERE o.status = 'PAID'

The NULL-extended row has no `o.status`, so the predicate is not TRUE for that row. It is removed.

The effective behavior becomes similar to an INNER JOIN for that condition.

When the business rule is "retain every customer, but attach only paid orders", the right-side condition can instead belong in the JOIN predicate:

    LEFT JOIN orders o
      ON o.customer_id = c.customer_id
     AND o.status = 'PAID'

The SQL implementation demonstrates both forms.

The distinction is:

- a condition in `ON` controls which right-side records participate in the match;
- a condition in `WHERE` filters the completed result.

That difference is especially important with outer joins.

## DISTINCT Is Not a General JOIN Repair

When a JOIN produces unexpected duplicates, adding:

    SELECT DISTINCT ...

may reduce the visible number of rows.

It does not establish the correct relationship.

If two orders legitimately match one customer, `DISTINCT` cannot determine which order should represent the customer.

If two independent child collections multiply each other, `DISTINCT` may hide the multiplication only when the selected columns happen to become identical.

If a wrong key connects unrelated records, `DISTINCT` does not repair the relationship.

The correct solution is to identify:

- the intended grain;
- the relationship key;
- the expected cardinality;
- the multiplicity of each participating table;
- whether child records should be aggregated before joining.

## Python Implementation

The Python program implements relational-style JOIN behavior with standard-library data structures.

`inner_join()` builds an index over the right-hand collection. A dictionary-like index maps each key to all matching rows. This is important because the implementation deliberately preserves multiplicity.

If three right-side rows share a key, a matching left row produces three output rows.

`left_join()` adds NULL-like `None` values when no right-side record exists. The function demonstrates the structural behavior of an outer join.

`cross_join()` explicitly creates every left/right combination. Its output size is the product of the input sizes, making Cartesian multiplication visible.

The `sql_equals()` function intentionally differs from ordinary Python equality. It treats `None` as non-equal to another `None`, reflecting ordinary SQL equality semantics for NULL.

The script also demonstrates pre-aggregation. Instead of attaching every order directly to a customer, it first computes customer-level totals. This allows the final result to remain at customer grain.

Cardinality validation is another important feature. The script checks whether a supposedly one-to-one relationship has changed the number of parent rows or introduced duplicate identifiers.

The diagnostic examples use key-frequency analysis to identify non-unique join attributes.

## JavaScript Implementation

The JavaScript program uses a hash-based join represented by `Map`.

`hashJoin()` indexes the right-hand dataset by the join key. This provides a practical application-level representation of how a hash join can operate.

The implementation also emits JOIN audit events using Node.js `EventEmitter`.

The audit event records:

    left row count
    right row count
    result row count

This is useful in data-processing services where unexpected cardinality changes should be observable.

`leftHashJoin()` models outer-join behavior by producing NULL-like `null` fields for unmatched right-side attributes.

The JavaScript implementation intentionally compares two NULL handling modes. This exposes an important boundary between database semantics and application semantics: JavaScript data structures may treat `null` as a normal key while SQL equality does not match NULL to NULL.

The asynchronous audit demonstration uses `setImmediate()` to show how a JOIN operation can participate in an event-driven Node.js processing flow without turning the example into a generic asynchronous programming tutorial.

## C++ Governance Case Study

The C++ program models a repository governance engine.

Its entities are:

    PullRequest
    Review
    StatusCheck
    BranchPolicy

The domain is useful for JOIN analysis because a pull request can have many reviews and many status checks.

The naive demonstration directly combines the two child collections. For pull request 101, two reviews and three checks create six combinations.

The governance engine then takes a different approach. It summarizes reviews and status checks independently before evaluating the pull request.

`ApprovalSummary` contains:

    approvals
    changeRequests

`CheckSummary` contains:

    requiredChecks
    passedChecks
    failedChecks
    pendingChecks

These summaries have pull-request grain. The merge decision can therefore be evaluated without multiplying the underlying child records.

The case study also demonstrates an overly broad relationship. A review and status check should be related through `pullRequestId`, not merely through repository identity. Multiple pull requests belong to the same repository, so repository-level matching is insufficient.

The C++ program uses explicit data structures and exception handling. It also uses `std::optional` to represent a missing relationship rather than converting absence into an arbitrary textual value.

## Java Enterprise Model

The Java implementation represents the same general domain from an enterprise service-design perspective.

Records provide immutable domain values for:

    PullRequest
    Review
    StatusCheck
    BranchProtection
    ReviewSummary
    CheckSummary
    MergeDecision

Enums model meaningful state values rather than relying on unrestricted strings.

`ReviewState` distinguishes `COMMENTED`, `CHANGES_REQUESTED`, `APPROVED`, and `DISMISSED`.

`CheckState` distinguishes `PENDING`, `PASSED`, and `FAILED`.

The service computes review and check summaries independently.

A particularly important design choice is the use of a `Set<String>` for approving reviewers. Counting raw review events can be incorrect if the same reviewer has multiple approval records. The actual business policy must define whether approval is event-based or reviewer-based.

The `evaluate()` method then applies the branch-protection policy to the already-aggregated facts.

The implementation therefore separates:

    raw child records
        |
        +-- review summary
        |
        +-- status-check summary
        |
        +-- merge decision

This is a safer domain model than combining every review and every check into one large intermediate collection.

## SQL Data Model

The PostgreSQL schema represents the repository governance relationships explicitly.

The principal relationships are:

    repository
        |
        +-- branch
              |
              +-- branch_protection

    pull_request
        |
        +-- commit_record
        |
        +-- review
        |     |
        |     +-- review_comment
        |
        +-- status_check

The foreign keys prevent child records from referencing nonexistent parent entities.

The `UNIQUE` constraints on repository names, branch identity, commit identity, and status-check identity protect relationships that should not contain arbitrary duplicates.

The status columns use `CHECK` constraints so invalid state strings cannot enter the database.

Indexes are placed on common relationship and filtering columns such as:

    pull_request.target_branch_id
    review.pull_request_id
    review.review_state
    status_check.pull_request_id
    status_check.check_state

These indexes support common governance queries without pretending that every possible query automatically needs an index.

## SQL Demonstrations of JOIN Multiplication

The direct review/check query intentionally produces the multiplication effect.

For a pull request with:

    2 reviews
    3 status checks

the direct combination contains:

    6 rows

The diagnostic aggregation reports:

    review_count
    check_count
    multiplied_rows
    expected_multiplication

This makes it possible to compare the observed output against the relationship's mathematical expectation.

The controlled approach uses two CTEs:

    review_summary
    check_summary

Each CTE reduces its source to one row per pull request.

The parent table is then joined to those summaries.

This is the correct pattern when the final report is intended to have pull-request grain.

## Incorrect Relationship Scope

The SQL script deliberately demonstrates a repository-level relationship that is too broad.

A repository can contain many pull requests.

Therefore:

    review.repository_id = status_check.repository_id

does not establish that the review and status check belong to the same pull request.

The correct relationship is:

    review.pull_request_id = status_check.pull_request_id

A relationship should be defined by the entity identity required by the business rule, not by the broadest common attribute.

## NULL and `IS NOT DISTINCT FROM`

The SQL script includes two equivalent-looking but semantically different comparisons.

Ordinary equality:

    l.key_value = r.key_value

does not match NULL to NULL.

PostgreSQL's:

    l.key_value IS NOT DISTINCT FROM r.key_value

does.

This distinction is valuable when a NULL value itself carries business meaning and two NULLs are deliberately intended to represent the same logical state.

It should not be applied automatically. Treating missing identifiers as equal can create relationships between records that are both simply missing the same information.

## Outer-Join Filtering

The SQL examples distinguish:

    LEFT JOIN ... ON ...

from:

    LEFT JOIN ...
    WHERE right_table.column = ...

A LEFT JOIN creates a NULL-extended row when no match exists.

A WHERE predicate requiring a right-side value removes that row.

This is a common source of reports that unexpectedly lose parent records.

The intended business question determines where the predicate belongs.

For example:

- "Show every pull request and attach passed checks" can place the passed condition in the JOIN.
- "Show only pull requests that have a passed check" can use a filtering condition after the relationship has been established.

These are different requirements and should not be treated as interchangeable query styles.

## Many-to-Many Relationships

A many-to-many relationship naturally requires an associative entity.

For example:

    PullRequest
        |
        +-- PullRequestReviewer
                 |
                 +-- Reviewer

or:

    Order
        |
        +-- OrderPromotion
                 |
                 +-- Promotion

When two many-side collections are joined without representing their intended relationship, row multiplication is expected.

A query should not assume that two entities sharing the same parent automatically have a direct relationship with each other.

This is one reason relational modeling and JOIN design must be considered together.

## Practical Cardinality Diagnostics

Before trusting a JOIN, inspect key frequencies.

For a supposed one-to-one relationship, a diagnostic query can group by the key and search for:

    HAVING COUNT(*) > 1

For a one-to-many relationship, the multiplicity may be expected, but its size should still be understood.

For two independent child tables, compare:

    left_child_count
    right_child_count
    left_child_count * right_child_count

Unexpected multiplication is often visible immediately.

A useful development practice is to test row counts at intermediate stages:

    source rows
        |
        v
    after first JOIN
        |
        v
    after second JOIN
        |
        v
    final result

A sudden increase should have an explicit relational explanation.

## Common Failure Patterns

### Using a descriptive column as an identifier

Columns such as region, department name, status, category, or date may be useful attributes but may not uniquely identify a relationship.

Joining on them can create many-to-many matches.

### Joining independent child tables directly

A parent with multiple reviews and multiple status checks can produce review-count multiplied by check-count rows.

Aggregate each child relationship first when the desired output is at parent grain.

### Joining only part of a composite identity

If the relationship is identified by multiple columns, every required component must participate in the JOIN predicate.

### Assuming NULL equals NULL

SQL's ordinary equality operator does not match NULL to NULL.

Use `IS NOT DISTINCT FROM` only when NULL equivalence is an intentional business rule.

### Using DISTINCT to hide a bad JOIN

DISTINCT removes duplicate output values. It does not establish whether the underlying relationships were correct.

### Filtering an outer join incorrectly

A WHERE condition on a nullable right-side column can eliminate rows preserved by a LEFT JOIN.

### Joining on the broadest common key

Two records sharing a repository, customer, organization, or region are not necessarily directly related.

The predicate must identify the intended relationship.

## Performance Considerations

JOIN correctness comes before JOIN optimization.

A fast incorrect query is still incorrect.

Once the relationship is correct, performance depends on factors such as:

- index availability on join keys;
- table cardinality;
- uniqueness and selectivity of join keys;
- join algorithm selected by the database optimizer;
- amount of data transferred between stages;
- whether aggregation occurs before or after multiplication;
- filtering selectivity;
- statistics quality.

Pre-aggregation can improve both correctness and performance when only parent-level metrics are required. It reduces the number of rows participating in later JOIN operations.

Indexes should support real access patterns rather than being added indiscriminately.

## Security and Data Integrity

JOIN mistakes can become security problems when authorization data is involved.

For example, an overly broad relationship between users and permissions could associate a user with permissions belonging to another organizational scope.

Database foreign keys help prevent invalid references, but they cannot determine whether an application chose the correct JOIN predicate.

Row-level authorization logic should therefore be explicit about its entity scope.

Sensitive reports should also avoid assuming that duplicate rows are harmless. A duplicated transaction, permission, approval, or financial amount can change the meaning of an aggregate.

## Debugging Strategy

When a JOIN produces too many rows, inspect the relationship rather than immediately modifying the SELECT list.

Useful checks include:

    SELECT COUNT(*)

before and after the JOIN.

Then inspect key uniqueness:

    SELECT join_key, COUNT(*)
    FROM table_name
    GROUP BY join_key
    HAVING COUNT(*) > 1;

For multiple child relationships, calculate the expected multiplication.

For nullable keys, inspect the number of NULL values separately.

For composite relationships, compare the full key against the subset used in the JOIN.

For outer joins, temporarily remove WHERE predicates involving right-side columns and observe whether previously missing parent rows return.

## Production Design Principle

A reliable JOIN starts with a relational question rather than a syntax pattern.

The implementation sequence should be conceptually:

    define result grain
        |
        v
    identify entity relationship
        |
        v
    identify actual key
        |
        v
    determine cardinality
        |
        v
    account for NULL semantics
        |
        v
    aggregate independent child relationships when required
        |
        v
    validate output cardinality
        |
        v
    optimize the correct query

The Python implementation makes JOIN behavior executable in memory. The JavaScript implementation models hash-based processing and event-driven diagnostics. The C++ implementation applies cardinality reasoning to a repository governance engine. The Java implementation expresses the same concerns through enterprise domain types and policy evaluation. The PostgreSQL implementation enforces relational integrity and demonstrates the behavior directly through executable DDL, DML, diagnostic queries, CTEs, constraints, indexes, transactions, and merge-eligibility calculations.

The common principle is precise: a JOIN should represent an intended relationship at a known grain. Unexpected row multiplication is a signal to investigate that relationship, not merely a reason to add `DISTINCT`.
