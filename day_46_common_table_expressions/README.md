# Common Table Expressions: WITH Clause and Readable Query Architecture

## Scope

A Common Table Expression (CTE) is a named intermediate relation defined with the `WITH` clause and consumed by the SQL statement that follows it. CTEs are particularly useful when a query contains several logically distinct transformations such as filtering, aggregation, qualification, ranking, validation, or hierarchical traversal.

The central architectural idea is to make a complex relational operation readable as a sequence of named transformations rather than forcing every transformation into one deeply nested query.

The implementations in this learning artifact deliberately use different perspectives:

- Python models CTE-style relational transformations as executable data-processing stages and includes a recursive hierarchy analogue.
- JavaScript represents staged query processing through immutable data, `Map`, validation, asynchronous execution, and an event-driven pipeline.
- C++ implements a repository-governance case study to demonstrate how intermediate query-style stages can support a non-trivial decision engine.
- Java models enterprise governance with explicit domain types, immutable records, validation, review states, and a merge-eligibility service.
- PostgreSQL represents the topic directly through CTEs, multi-CTE pipelines, aggregation, window functions, recursive traversal, indexes, constraints, and a transactional workflow.

## The `WITH` Clause

The basic CTE structure is:

    WITH named_relation AS (
        SELECT ...
    )
    SELECT ...
    FROM named_relation;

The CTE is not a permanent table. Its name exists for the duration of the statement. This makes it appropriate for defining an intermediate relational result that is needed by later parts of the same query.

A simple filtering CTE can separate source-row selection from subsequent business logic:

    WITH completed_orders AS (
        SELECT order_id, customer_id, amount
        FROM orders
        WHERE status = 'completed'
    )
    SELECT customer_id, SUM(amount)
    FROM completed_orders
    GROUP BY customer_id;

The important distinction is architectural rather than syntactic. `completed_orders` communicates the meaning of the intermediate relation, while the final query can focus on aggregation.

## CTEs as Relational Pipeline Stages

A complex query can contain several CTEs:

    WITH filtered_data AS (...),
    aggregated_data AS (...),
    qualified_data AS (...)
    SELECT ...
    FROM qualified_data;

The later CTE can reference earlier CTEs. This creates a dependency graph:

    base tables
         |
         v
    filtered_data
         |
         v
    aggregated_data
         |
         v
    qualified_data
         |
         v
    final SELECT

Each stage should have a meaningful relational responsibility. A filtering CTE should perform filtering rather than becoming a container for unrelated calculations. An aggregation CTE should expose the aggregated relation needed by the next stage.

This separation makes complex SQL easier to inspect, debug, modify, and validate.

## CTE Fundamentals

A CTE is defined before the main query using `WITH`. Multiple CTEs are separated by commas.

    WITH first_stage AS (...),
         second_stage AS (...)
    SELECT ...
    FROM second_stage;

The second CTE can reference `first_stage`.

CTEs can use joins, aggregates, window functions, expressions, grouping, filtering, and other normal SQL operations. A CTE is therefore not a restricted query fragment. It is a named query relation whose scope is the containing statement.

A CTE can also be consumed more than once within the statement when the query structure requires it.

## Why Naming Intermediate Relations Matters

Consider a query that must identify open pull requests, calculate distinct approvals, evaluate status checks, and determine merge eligibility.

Putting all operations into one large `SELECT` can make the logical dependencies difficult to identify.

A staged design can instead expose:

- `protected_targets` for open pull requests associated with branch policies.
- `approval_state` for the current approval count.
- `check_state` for aggregate status-check state.
- `unresolved_conversations` for outstanding review discussions.

The final query then combines those relations to calculate merge eligibility.

The name of an intermediate relation becomes part of the query's documentation. Good CTE names describe the relation rather than merely describing an implementation step.

## CTEs and Subqueries

A subquery can express the same relational transformation in many cases:

    SELECT ...
    FROM (
        SELECT ...
        FROM ...
    ) AS derived_data;

A CTE separates the intermediate query from the main query visually:

    WITH derived_data AS (
        SELECT ...
        FROM ...
    )
    SELECT ...
    FROM derived_data;

The choice should be based on clarity and query requirements rather than the assumption that a CTE is automatically faster.

CTEs are primarily a query-organization mechanism. PostgreSQL's optimizer may inline or materialize CTEs depending on the query and PostgreSQL version, explicit materialization directives, and optimization requirements.

## The Python Implementation

The Python program models CTE architecture without pretending that Python list processing is literally SQL execution.

`completed_orders()` represents the filtering stage. It removes cancelled orders before later calculations.

`aggregate_customer_sales()` represents an aggregation relation. It produces customer-level totals from the filtered data.

`customer_sales_report()` composes those intermediate results and applies a qualification threshold. This demonstrates the architectural relationship between filtering, aggregation, and final selection.

`monthly_sales()` introduces a second analytical pipeline in which completed orders are transformed into monthly revenue.

The `recursive_date_series()` function provides an executable analogue for the idea behind a recursive SQL CTE. It uses iteration because a Python loop is more appropriate than artificial recursion for generating a sequence.

`hierarchy_with_cte_style()` models the anchor-and-recursive-member pattern found in hierarchical recursive CTEs. The root employee forms the initial frontier, and each frontier row produces child rows for the next traversal stage.

The Python implementation also validates input and handles empty input, threshold conditions, invalid status values, and invalid numeric thresholds.

## The JavaScript Implementation

The JavaScript implementation takes a different architectural approach.

JavaScript's `Map` is used for grouped totals because customer identifiers naturally map to accumulated revenue. Array operations provide a concise representation of filtering and projection stages.

`QueryPipeline` introduces an event-driven representation of intermediate query stages. The pipeline emits `completed_orders`, `customer_totals`, and `qualified_customers` independently.

This does not replace database-side CTEs. The database should still perform relational work when the source data resides in the database. The JavaScript design demonstrates how an application can consume and process named intermediate results while preserving clear boundaries between stages.

The asynchronous report function reflects a realistic Node.js application boundary where data retrieval or report execution may be asynchronous.

The hierarchy implementation uses a queue to model breadth-first traversal, which corresponds naturally to the recursive relationship represented by a recursive SQL CTE.

## Recursive CTEs

A recursive CTE extends the `WITH` mechanism with `RECURSIVE`.

A typical recursive structure has an anchor member and a recursive member:

    WITH RECURSIVE hierarchy AS (
        SELECT ...
        FROM employees
        WHERE manager_id IS NULL

        UNION ALL

        SELECT ...
        FROM employees
        JOIN hierarchy
          ON employees.manager_id = hierarchy.employee_id
    )
    SELECT *
    FROM hierarchy;

The anchor establishes the initial rows. The recursive member derives additional rows from rows already discovered.

Recursive CTEs are useful for organizational hierarchies, category trees, dependency graphs, graph-like relationships, and path construction.

The PostgreSQL script creates a branch relationship table and uses a recursive CTE to produce a path such as `main -> feature/customer-ctes`.

Recursive queries require careful termination conditions. A cyclic relationship can cause repeated traversal or an unbounded recursive operation unless the data model or query explicitly prevents or handles cycles.

## CTEs with Aggregation

A common analytical pattern is to aggregate an intermediate relation and then query the aggregate.

The PostgreSQL implementation uses:

    WITH contributor_changes AS (
        SELECT
            contributor_id,
            SUM(additions) AS additions,
            SUM(deletions) AS deletions
        FROM commits
        GROUP BY contributor_id
    )
    SELECT ...
    FROM contributor_changes;

The aggregate stage creates one row per contributor. A later query can calculate net change and apply a window function without repeating the aggregation expression.

This separation is particularly useful when the aggregate result is conceptually meaningful on its own.

## CTEs and Window Functions

A CTE can establish the relation that a window function operates over.

In the SQL implementation, `contributor_changes` calculates additions and deletions first. The outer query applies `RANK()` to the resulting contributor-level rows.

This creates a useful distinction:

- Aggregation changes the number of rows by grouping them.
- A window function calculates across related rows while retaining the rows being ranked or analyzed.

Using a CTE between these operations can make that semantic boundary explicit.

## CTEs for Policy Evaluation

The repository-governance query demonstrates a realistic multi-stage decision model.

`protected_targets` identifies open pull requests whose target branches have branch protection policies.

`approval_state` counts distinct reviewers whose current review state is approved.

`check_state` aggregates status checks using `BOOL_AND`.

`unresolved_conversations` counts unresolved review comments.

The final query combines these relations to determine `merge_eligible`.

This is a useful example of readable query architecture because merge eligibility is not a single primitive fact. It is derived from several independent pieces of repository state.

The policy relation defines the required conditions. Review state provides approval information. Status checks provide automated validation. Review comments provide conversation state. The final relational expression combines them without placing every operation into one monolithic subquery.

## PostgreSQL CTE Semantics

The SQL artifact uses PostgreSQL syntax.

A normal CTE has statement scope. Defining:

    WITH current_state AS (...)
    SELECT ...

does not create a permanent relation named `current_state`.

The CTE disappears after the statement finishes.

This is fundamentally different from creating a table or view.

A view persists as a database object and can be referenced by later statements. A temporary table persists for the applicable temporary-table lifetime. A CTE is normally scoped only to its statement.

PostgreSQL also supports explicit materialization controls:

    WITH data AS MATERIALIZED (...)
    ...

and:

    WITH data AS NOT MATERIALIZED (...)
    ...

These options can affect how PostgreSQL handles the intermediate result. They should be used when their execution consequences are understood rather than as a general performance rule.

## CTEs and Readability

A readable CTE query should have a clear progression.

For example:

    WITH protected_targets AS (...),
    approval_state AS (...),
    check_state AS (...),
    unresolved_conversations AS (...)
    SELECT ...
    FROM protected_targets
    LEFT JOIN approval_state ...
    LEFT JOIN check_state ...
    LEFT JOIN unresolved_conversations ...;

The query can be read almost as a data-flow diagram.

The benefit comes from meaningful boundaries. If every two-line expression becomes its own CTE, the query can become unnecessarily fragmented. CTEs should reduce cognitive load, not increase it.

## The C++ Case Study

The C++ program presents a repository governance engine rather than translating the Python sales example.

`PullRequest`, `Review`, and `BranchPolicy` represent distinct domain records.

`GovernanceEngine` maintains repository policy and review state. `approvedReviews()` isolates approval records, while `mergeEligible()` combines approval requirements and status-check requirements.

The implementation uses a `std::map` to ensure that repeated approvals by the same reviewer do not artificially satisfy a distinct-reviewer requirement.

This case study demonstrates the conceptual role of intermediate query stages in a system that needs to evaluate merge eligibility. The actual database implementation in the SQL artifact performs the relational work with CTEs.

## The Java Enterprise Model

The Java implementation represents the governance domain using records and enums.

`ReviewState` explicitly distinguishes `COMMENTED`, `CHANGES_REQUESTED`, `APPROVED`, and `DISMISSED`. This is more reliable than representing review state with arbitrary strings.

`CheckState` models automated validation independently from human review.

`PullRequestState` prevents the governance service from treating a draft or closed pull request as equivalent to an open one.

`BranchProtection` stores policy requirements as immutable domain data.

`RepositoryGovernanceService` evaluates those policies and returns a `MergeDecision` containing both the eligibility result and specific blockers.

The implementation also uses a `HashSet` to count distinct approving reviewers. This prevents duplicate review records from incorrectly increasing the effective approval count.

## SQL Constraints and CTEs Work Together

A CTE organizes a query, while constraints protect stored data.

The SQL schema uses primary keys for identity, foreign keys for relationships, unique constraints for uniqueness, and check constraints for allowed states and non-negative numeric values.

For example, `reviews.review_state` is constrained to the supported review states. This means the application does not need to be the only enforcement point for valid review-state values.

The CTE then operates over data whose basic structural validity has already been enforced by the database.

This distinction is important:

- Constraints protect data integrity.
- CTEs organize query computation.
- Indexes support access paths for important queries.
- Transactions control groups of data changes.

These mechanisms solve different problems even though they can appear in the same SQL workflow.

## CTEs and Transactions

A CTE itself is not a transaction.

The SQL artifact uses `BEGIN` and `COMMIT` around a correction to a failed status check. CTEs are used inside the transactional statements to identify the rows involved.

Transaction boundaries determine atomicity. CTEs determine the structure of individual statements.

A transaction can contain statements with CTEs, but `WITH` does not replace transaction management.

## Performance Considerations

A CTE should not automatically be assumed to improve performance.

A readable query can still perform poorly if intermediate operations process unnecessarily large relations, joins lack appropriate indexes, filters are applied too late, or aggregation is performed over excessive data.

The SQL artifact indexes pull-request target/state access, review state by pull request, and status checks by pull request/state.

These indexes correspond to actual access patterns in the governance queries.

For performance-sensitive PostgreSQL queries, execution plans should be examined with `EXPLAIN` and `EXPLAIN ANALYZE`. Query architecture should be evaluated together with cardinality, join strategy, selectivity, indexes, and the optimizer's treatment of CTEs.

## Materialization and Optimization

Historically, CTEs could act as optimization fences in PostgreSQL versions where CTE materialization behavior differed from current behavior. Modern PostgreSQL can inline eligible CTEs, while `MATERIALIZED` and `NOT MATERIALIZED` can explicitly influence this decision.

Materialization can be useful when an intermediate result should be computed once and reused, especially when recomputation would be expensive.

Inlining can be preferable when pushing predicates into the underlying relations enables a better execution plan.

The correct choice depends on the actual query and data distribution.

## Common Mistakes

### Treating every CTE as a performance optimization

A CTE primarily improves query structure. It does not guarantee a faster execution plan.

### Creating CTEs without meaningful boundaries

A query with many trivial CTEs can become harder to follow. Each CTE should represent a meaningful relation or transformation.

### Hiding incorrect aggregation inside a CTE

A named relation can make a query easier to read while still producing incorrect results. Grouping keys and join cardinality must still be validated.

### Confusing review state with approval count

In the governance example, an approval is derived from review state and reviewer identity. A historical approval should not automatically be counted if later state changes invalidate it.

### Ignoring recursive termination

Recursive CTEs require a well-defined relationship and termination behavior. Cyclic data can create problematic traversal.

### Assuming CTE scope is permanent

A CTE does not create a persistent database object. A later SQL statement cannot normally reference the CTE name.

## Debugging Strategy

A staged CTE query is easier to debug when each intermediate relation can be inspected independently.

For a multi-stage query, temporarily execute the CTE chain while selecting from an intermediate stage:

    WITH protected_targets AS (...),
    approval_state AS (...)
    SELECT *
    FROM approval_state;

This reveals whether the problem originates in filtering, joining, aggregation, or the final decision logic.

The same principle appears in the Python, JavaScript, C++, and Java implementations: intermediate state is represented explicitly rather than hiding every operation inside one large procedure.

## Practical Architectural Distinction

The relationship between the concepts in this artifact can be expressed as:

    Source relations
          |
          v
    Named relational stages
          |
          v
    Aggregation / validation / enrichment
          |
          v
    Final relation

A CTE provides the SQL mechanism for naming the intermediate stages.

The surrounding database mechanisms determine how the data is stored and protected. Constraints protect integrity, indexes support access, transactions control atomicity, and the final query consumes the relations produced by the CTE pipeline.

The main value of the `WITH` clause is that it lets the SQL author express those transformations in a structure that exposes the logical architecture of the query.
