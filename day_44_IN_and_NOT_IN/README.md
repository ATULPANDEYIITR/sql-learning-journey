# IN and NOT IN: Membership Tests, NULL Pitfalls, and Alternatives

## Scope

This learning artifact examines SQL membership predicates through the behavior of `IN` and `NOT IN`, with particular attention to SQL `NULL`, three-valued logic, `WHERE` filtering, relational alternatives, and database-level policy evaluation.

The central distinction is that membership predicates are not simply equivalent to ordinary programming-language collection membership. SQL comparisons can produce `TRUE`, `FALSE`, or `UNKNOWN`. That third result is responsible for one of the most important practical SQL mistakes: a `NOT IN` predicate can unexpectedly return no rows when its candidate set contains `NULL`.

The six implementations approach the subject from different technical perspectives:

- The Python program explicitly models SQL's three-valued logic and contrasts it with Python set membership.
- The JavaScript program models SQL membership while also demonstrating the difference between SQL predicates and JavaScript `Array.includes()`.
- The C++ program uses `std::optional` to represent SQL-like nullable values and builds a repository-governance case study around membership and policy evaluation.
- The Java program uses explicit domain types and immutable records to connect nullable membership semantics with enterprise review-policy decisions.
- The PostgreSQL script demonstrates the actual database behavior of `IN`, `NOT IN`, `NULL`, `NOT EXISTS`, constraints, indexes, transactions, and merge-eligibility queries.
- This README explains how the mechanisms relate and where each approach is appropriate.

## Core Membership Semantics

An expression such as:

`department IN ('Engineering', 'Security')`

asks whether `department` equals at least one candidate value.

Conceptually, SQL evaluates the expression through equality comparisons. If one comparison is `TRUE`, the `IN` expression is `TRUE`. If all comparisons are `FALSE`, the result is `FALSE`. If no comparison is `TRUE` and at least one comparison is `UNKNOWN`, the result is `UNKNOWN`.

`NULL` does not mean an ordinary missing string. It represents an unknown or absent value. SQL does not consider:

`department = NULL`

to be `TRUE`. The result is `UNKNOWN`.

The null-aware comparison can therefore be understood as:

| Comparison | SQL result |
|---|---|
| `'Finance' = 'Finance'` | `TRUE` |
| `'Finance' = 'Engineering'` | `FALSE` |
| `'Finance' = NULL` | `UNKNOWN` |
| `NULL = NULL` | `UNKNOWN` |

This behavior is different from many application-language equality operations.

## Three-Valued Logic

SQL predicates operate with three logical states.

`TRUE` means the predicate is satisfied.

`FALSE` means the predicate is disproved.

`UNKNOWN` means the database cannot establish that the predicate is true because a comparison depends on `NULL`.

A critical consequence is that a `WHERE` clause retains only rows for which the predicate evaluates to `TRUE`.

For example:

`WHERE employee.department NOT IN ('Finance', NULL)`

does not mean "return every department except Finance."

For `Engineering`, SQL must consider both the fact that it is not `Finance` and the comparison with `NULL`. The `NULL` comparison produces `UNKNOWN`, so the complete predicate can become `UNKNOWN`. `WHERE` removes that row because `UNKNOWN` is not `TRUE`.

## Why NOT IN Is Dangerous with NULL

The practical trap is easiest to see with:

`department NOT IN ('Finance', NULL)`

The logical structure of `NOT IN` is closely related to the negation of membership.

For a non-null value such as `Engineering`, the comparisons include:

`Engineering = Finance` → `FALSE`

`Engineering = NULL` → `UNKNOWN`

The corresponding `IN` expression therefore becomes `UNKNOWN`, and negating `UNKNOWN` still produces `UNKNOWN`.

The important property is:

`NOT UNKNOWN` → `UNKNOWN`

It does not become `TRUE`.

This means the presence of `NULL` in an exclusion set can invalidate the intended meaning of a `NOT IN` condition.

The problem also occurs when the subquery supplying the values contains nullable data:

`WHERE employee_id NOT IN (SELECT employee_id FROM blocked_employees)`

If `blocked_employees.employee_id` can contain `NULL`, the query can behave very differently from the intended "exclude matching employees" rule.

## IN Versus NOT IN

`IN` is naturally useful when the candidate set is known and its null behavior is understood.

Examples include:

`status IN ('ACTIVE', 'PENDING')`

`region IN ('APAC', 'EMEA', 'AMER')`

`review_state IN ('APPROVED', 'COMMENTED')`

`NOT IN` expresses exclusion:

`status NOT IN ('DELETED', 'SUSPENDED')`

The exclusion form requires more care because the presence of `NULL` changes the logical result.

A static list whose values are guaranteed to be non-null is normally straightforward:

`username NOT IN ('security-reviewer', 'platform-reviewer')`

The danger appears when `NULL` can enter the list directly or through a subquery.

## NOT EXISTS as a Relational Alternative

When the candidate values come from another table, `NOT EXISTS` is often a clearer representation of relational absence.

Instead of asking:

`employee_id NOT IN (SELECT employee_id FROM blocked_employees)`

the query can ask:

`NOT EXISTS (SELECT 1 FROM blocked_employees b WHERE b.employee_id = e.employee_id)`

The second form asks whether a matching blocking row exists.

This is conceptually different from negating a potentially unknown membership result.

The PostgreSQL implementation uses `NOT EXISTS` for queries such as identifying reviewers without matching open Pull Requests and Pull Requests without blocking reviews. The subquery expresses absence directly and does not suffer from the same `NOT IN` null-poisoning behavior.

## NULL-Safe Equality

PostgreSQL provides:

`IS NOT DISTINCT FROM`

for comparisons where `NULL` should be treated as a comparable value.

For example:

`NULL IS NOT DISTINCT FROM NULL`

returns `TRUE`.

By contrast:

`NULL = NULL`

returns `UNKNOWN`.

This distinction matters when `NULL` is part of the actual business meaning rather than merely an unknown value.

`IS DISTINCT FROM` provides the corresponding null-safe inequality operation.

These operators should be selected deliberately. They are not general replacements for ordinary equality.

## Python Implementation

The Python implementation does not pretend that Python's native `in` operator has SQL semantics.

Python normally gives a Boolean result for:

`value in candidates`

The program instead defines `sqlEqual`, `membership`, `sql_not`, and `sql_where` behavior so that `None` can represent SQL-style `UNKNOWN`.

The `membership` function returns:

- `True` when a definite match exists.
- `False` when every comparison is definitely false.
- `None` when no match exists but at least one candidate comparison is unknown.

This gives a direct executable model of the SQL rule.

The program also compares this model with Python sets. Python sets are useful for application-side membership checks, but their behavior should not be mistaken for SQL predicate evaluation.

The parameterized query example addresses a related production concern. Membership values must be supplied as parameters rather than concatenated into SQL source text. The Python implementation constructs placeholders while keeping values separate from SQL syntax.

The performance demonstration also distinguishes application-side set membership from database query planning. A Python set normally provides average constant-time membership lookup, while SQL performance depends on indexes, statistics, cardinality, query shape, and the database optimizer.

## JavaScript Implementation

The JavaScript program deliberately models SQL's three-valued logic with:

- `true` for `TRUE`
- `false` for `FALSE`
- `null` for `UNKNOWN`

This makes an important language distinction visible.

JavaScript:

`array.includes(value)`

returns a normal Boolean.

SQL:

`value IN (...)`

can return `TRUE`, `FALSE`, or `UNKNOWN`.

The `sqlEqual`, `sqlIn`, `sqlNot`, and `passesWhere` functions model this difference.

The event-driven section adds a JavaScript-specific perspective by representing review events and evaluating approval state asynchronously. This is useful when SQL membership logic is part of a larger application that receives review events, status updates, or policy decisions.

The parameterized query builder demonstrates that application code should keep values separate from SQL syntax. It also validates the SQL identifier because parameter placeholders generally apply to values, not arbitrary SQL identifiers.

## C++ Case Study

The C++ program uses `std::optional<std::string>` to represent values that may be absent.

This is a useful representation for modeling SQL `NULL` because an ordinary C++ `std::string` cannot distinguish between an empty string and an absent value.

The program implements:

`sqlEqual`

`sqlIn`

`sqlNot`

and `passesWhere`

to model SQL-style three-valued logic.

The case study then moves into repository governance. A Pull Request contains source and target branch information, an optional author, and draft state. Reviews contain reviewer identity, approval state, and eligibility. Status checks provide required validation signals. Branch protection specifies the number of required approvals and whether passing checks are mandatory.

The merge engine evaluates these independent conditions and records failure reasons instead of returning only a Boolean. This is important in real governance systems because a blocked merge should explain whether the cause is insufficient approval, a failed status check, draft state, an invalid target branch, or another policy violation.

The C++ implementation therefore treats membership semantics as part of a larger decision engine rather than as an isolated collection operation.

## Java Implementation

The Java implementation uses records and enums to model repository governance as explicit domain objects.

`PullRequest` captures the proposed change and its synchronization state.

`Review` captures reviewer identity, review state, and reviewer eligibility.

`StatusCheck` distinguishes required checks from informational checks.

`BranchProtection` defines merge policy.

`MergeDecision` returns both eligibility and the reasons that caused rejection.

The approval calculation filters reviews by both reviewer eligibility and approval state. This is intentionally different from simply counting every review with `APPROVED` status. A review from an ineligible reviewer should not automatically satisfy a protected-branch approval requirement.

The Java membership implementation uses `null` as the representation of an SQL-like unknown value. The program then demonstrates why ordinary collection membership and SQL membership should be treated as different semantic systems.

## PostgreSQL Data Model

The SQL script creates a relational model containing:

- `repositories` for repository identity.
- `branches` for source and target branches.
- `pull_requests` for proposed changes.
- `commits` for Pull Request changesets.
- `reviewers` for repository participants.
- `reviews` for review decisions.
- `review_comments` for file-level discussion.
- `status_checks` for automated validation.
- `branch_protection` for protected-branch governance.

Foreign keys establish relationships between these entities.

`CHECK` constraints enforce valid review states and non-negative approval requirements.

Indexes support common access paths such as Pull Request target branches, review state lookup, and status-check evaluation.

The model therefore keeps relational membership questions in the database instead of forcing every rule into application code.

## SQL Demonstration of the NULL Trap

The script intentionally executes:

`username NOT IN ('security-reviewer', NULL)`

to expose the problematic semantics.

The result is not equivalent to:

"username is not security-reviewer."

The presence of `NULL` introduces `UNKNOWN`, which prevents the `WHERE` predicate from becoming `TRUE` for otherwise non-matching values.

The script then contrasts that behavior with a non-null exclusion list.

This difference should be tested explicitly whenever a `NOT IN` list is generated from a query or external dataset.

## Membership Through a Subquery

A common production form is:

`column IN (SELECT ...)`

or:

`column NOT IN (SELECT ...)`

The second form requires particular attention to nullability.

If the subquery can return `NULL`, `NOT IN` can produce unexpected filtering.

`NOT EXISTS` is frequently a better expression when the real requirement is:

"Return rows for which no matching row exists in the related table."

The SQL implementation uses this approach for repository governance queries.

## Approval Membership and Eligibility

The repository model contains multiple concepts that must not be collapsed into one membership condition.

A reviewer can exist in the `reviewers` table without being eligible to satisfy an approval requirement.

A review can have `APPROVED` state while being stale.

A reviewer can submit comments without approving.

A status check can exist while being optional rather than required.

The merge-eligibility view therefore combines membership-like filtering with policy state.

Eligible approvals require:

- an `APPROVED` review,
- a non-stale review,
- an active reviewer.

Required checks must pass when branch protection requires them.

The Pull Request must also be open, non-draft, and synchronized with its base branch.

This illustrates why a production query often needs more than a simple `IN` predicate.

## Review Comments and Membership

Review comments have a different role from approvals.

An unresolved comment does not automatically mean that the reviewer's state is `CHANGES_REQUESTED`. The database model keeps these concepts separate.

When branch protection requires conversation resolution, unresolved comments become another merge condition.

This distinction prevents review discussion state from being incorrectly treated as approval state.

## Approval Semantics

Approval should not be treated as a permanent Boolean attached to a Pull Request.

The SQL model includes a `stale` flag so that an approval can become invalid after relevant changes.

A valid approval therefore depends on multiple predicates rather than a single membership test.

Conceptually:

`review_state = 'APPROVED'`

is necessary but not sufficient.

The reviewer must also be eligible, the review must not be stale, and the branch policy must require and recognize that approval.

The database query expresses those conditions explicitly.

## Branch Protection

Branch protection determines which repository-level conditions are enforced before a change can reach a sensitive branch.

The SQL model represents:

- required approval count,
- required status checks,
- required conversation resolution,
- linear-history requirements,
- force-push restrictions,
- deletion restrictions,
- direct-push restrictions.

These policies are distinct from the Pull Request itself.

A Pull Request is the proposed change.

A review evaluates the proposed change.

An approval records a review decision.

Branch protection determines which conditions must be satisfied before the repository accepts the merge.

## Transactional Behavior

The SQL script uses a transaction around a review-state change.

The review is temporarily changed to `CHANGES_REQUESTED`, the merge-eligibility view is inspected, and the transaction is rolled back.

The example demonstrates that related policy decisions should be evaluated consistently with the state being modified.

In a production workflow, a transaction can protect a multi-step state transition from partial updates.

The appropriate transaction boundary depends on the application architecture and database isolation requirements.

## Empty Membership Sets

An empty `IN` set requires deliberate handling.

Some application query builders generate invalid SQL if they blindly create:

`column IN ()`

A robust application should represent an empty membership request explicitly.

The Python and JavaScript implementations demonstrate returning `FALSE` when there are no candidate values. This corresponds to the common application requirement that no requested IDs means no matching rows.

For exclusion logic, the business meaning must be defined separately. An empty exclusion set can logically mean that nothing is excluded, but the application should encode that meaning explicitly rather than relying on malformed SQL.

## Common Mistakes

### Treating NULL as an ordinary value

`NULL` is not a normal string or numeric value. Ordinary equality does not establish equality with `NULL`.

Use `IS NULL` or `IS NOT NULL` for ordinary null tests.

Use `IS DISTINCT FROM` or `IS NOT DISTINCT FROM` in PostgreSQL when null-aware equality semantics are specifically required.

### Using NOT IN against nullable subquery data

A query such as:

`WHERE id NOT IN (SELECT id FROM blocked_items)`

is unsafe when `blocked_items.id` can contain `NULL`.

Prefer `NOT EXISTS` when the requirement is relational absence.

### Assuming WHERE keeps FALSE and UNKNOWN

`WHERE` keeps only `TRUE`.

Both `FALSE` and `UNKNOWN` filter out the row.

This is why a query can appear logically correct when examined as informal English but return unexpectedly few rows.

### Counting every approval

An `APPROVED` row is not automatically a valid approval.

Eligibility, stale state, reviewer role, and branch policy can affect whether an approval satisfies merge requirements.

### Building IN lists through string concatenation

Application-generated SQL should not directly concatenate untrusted values into SQL syntax.

Use parameterized queries.

The membership values should remain data rather than becoming part of executable SQL text.

## Performance Considerations

`IN` with a small static list is generally straightforward for a database optimizer.

Large dynamically generated lists can become harder to manage. For large relational sets, storing the values in a table, temporary table, parameterized relation, or other database-supported structure can produce a better query shape.

Indexes matter when membership predicates operate against indexed columns.

For relational exclusion, `NOT EXISTS` can be particularly natural because the database can use indexes on the correlated lookup.

Performance should be evaluated with the actual query plan rather than assumed from the textual appearance of `IN`, `NOT IN`, or `NOT EXISTS`.

The relevant PostgreSQL tools include `EXPLAIN` and `EXPLAIN ANALYZE`, especially when membership predicates operate over large relations.

## Security Considerations

Membership predicates themselves are not an SQL-injection vulnerability.

The vulnerability appears when application code turns membership values into SQL source text through unsafe string construction.

For example, constructing a SQL string by concatenating user-supplied values mixes data and code.

Parameterized SQL separates those concerns.

Identifier validation is a separate issue because standard SQL parameters generally represent values, not arbitrary table or column identifiers. The application must therefore validate or select identifiers from a trusted allowlist when dynamic identifiers are required.

## Conceptual Relationship

The mechanisms in this artifact form a clear progression:

`IN` expresses membership.

`NOT IN` expresses exclusion through negated membership.

`NULL` introduces `UNKNOWN` into equality-based membership evaluation.

`WHERE` keeps only `TRUE`.

`NOT EXISTS` expresses relational absence directly.

`IS DISTINCT FROM` provides PostgreSQL-specific null-aware comparison semantics.

Application languages such as Python, JavaScript, C++, and Java may provide their own collection and null semantics, but those semantics should not be assumed to match SQL.

The PostgreSQL implementation is therefore the authoritative demonstration of database behavior, while the other implementations model and explain that behavior in application-level systems.

## Practical Decision Guide

Use `IN` when the candidate set is well-defined and its `NULL` behavior is understood.

Use `NOT IN` when the candidate set is guaranteed to contain no `NULL` values or when its null semantics have been deliberately handled.

Use `NOT EXISTS` when the actual requirement is the absence of a related row, especially when the candidate values originate from another table.

Use `IS NULL` or `IS NOT NULL` when the requirement specifically concerns nullability.

Use `IS DISTINCT FROM` or `IS NOT DISTINCT FROM` in PostgreSQL when `NULL` must participate in equality semantics as a meaningful comparable state.

Use parameterized queries whenever membership values originate outside trusted SQL source code.

## Production Perspective

A reliable membership query is not defined only by whether its syntax is valid.

Its correctness depends on the meaning of `NULL`, the nullability of candidate data, the behavior of `WHERE`, the source of the membership set, the required business rule, and the database execution plan.

In repository governance, this becomes particularly important because approval eligibility, reviewer membership, required checks, protected branches, and merge conditions are related but separate policies.

The implementations deliberately keep those concepts distinct so that a membership test does not accidentally become an approval rule, an approval does not automatically become merge eligibility, and a branch-protection policy does not become confused with Pull Request state.
