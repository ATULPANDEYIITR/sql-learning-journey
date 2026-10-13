# EXISTS and NOT EXISTS in Relational Queries

## Scope

`EXISTS` and `NOT EXISTS` answer questions about whether related records are present. They support semi-joins, anti-joins, correlated subqueries, nested policy checks, and relational-division queries.

The implementations use repository development as a shared technical domain. Pull requests have reviewers, review decisions, status checks, and repository-level requirements. The same patterns apply to orders and payments, users and permissions, students and enrollments, devices and telemetry, and other related data.

The central distinction is between retrieving matching records and testing whether a match exists. An ordinary join returns matching combinations of rows. A semi-join returns outer rows for which a match exists, without multiplying them. An anti-join returns outer rows for which no match exists.

## Core semantics

### EXISTS

`EXISTS (subquery)` evaluates to true when its subquery returns at least one row. The values selected by the subquery are not used to determine truth. Consequently, `SELECT 1` is a conventional choice.

For example, a repository dashboard might need every open pull request with an approval:

    SELECT p.pull_request_id, p.title
    FROM pull_requests AS p
    WHERE p.state = 'open'
      AND EXISTS (
          SELECT 1
          FROM reviews AS r
          WHERE r.pull_request_id = p.pull_request_id
            AND r.review_state = 'approved'
      );

The subquery references `p.pull_request_id`, which comes from the outer query. This makes it a correlated subquery. Conceptually, the database tests whether a matching review exists for each candidate pull request. An optimizer can transform this into a semi-join rather than literally executing a separate query for every outer row.

The predicate does not require the inner query to return every matching review. One qualifying row is enough. Nor does it require the outer query to select review columns.

### NOT EXISTS

`NOT EXISTS (subquery)` evaluates to true when the subquery returns no rows. It is useful when the absence of a related record is itself important.

A dashboard could identify open pull requests that have no approval:

    SELECT p.pull_request_id, p.title
    FROM pull_requests AS p
    WHERE p.state = 'open'
      AND NOT EXISTS (
          SELECT 1
          FROM reviews AS r
          WHERE r.pull_request_id = p.pull_request_id
            AND r.review_state = 'approved'
      );

This is an anti-join. The query preserves the outer pull-request row only when no matching approval exists.

The result does not necessarily identify every request that is ready for review. A request without an approval might still have a pending check, unresolved discussion, or an ineligible reviewer. An existence predicate proves only the condition explicitly expressed in its subquery.

### Semi-joins and anti-joins

| Operation | Meaning | Typical use |
|---|---|---|
| Semi-join | Keep an outer row if a matching inner row exists | Pull requests with approvals |
| Anti-join | Keep an outer row if no matching inner row exists | Pull requests missing approvals |
| Inner join | Return matching row combinations | Display each request and its reviewers |
| Left join | Preserve outer rows even when no match exists | Display all requests with optional review details |

These operations are related, but their output cardinality differs.

If a pull request has three matching reviews, an inner join can produce three rows for that request. An `EXISTS` predicate normally produces one outer row. Using `DISTINCT` after a join can remove duplicates, but it may require additional processing and can obscure the intended existence test.

A semi-join is particularly suitable when columns from the related table are needed only to establish whether a qualifying relationship exists.

## Correlated and uncorrelated subqueries

A correlated subquery refers to a column from its surrounding query. The relationship between the outer row and the inner search is explicit:

    SELECT p.pull_request_id
    FROM pull_requests AS p
    WHERE EXISTS (
        SELECT 1
        FROM status_checks AS s
        WHERE s.pull_request_id = p.pull_request_id
          AND s.check_state = 'failure'
    );

An uncorrelated subquery does not refer to the outer row:

    SELECT p.pull_request_id
    FROM pull_requests AS p
    WHERE EXISTS (
        SELECT 1
        FROM repositories AS r
        WHERE r.protected_branch = TRUE
    );

The second example returns all pull requests if any protected repository exists. It returns none if no such repository exists. It does not establish that a particular pull request belongs to a protected repository. That requires correlating the repository identifier.

This distinction is important in access-control checks and reporting. An uncorrelated existence condition can be valid, but accidentally omitting the correlation can produce a result that appears plausible while applying the wrong rule.

## EXISTS and NULL semantics

SQL uses three-valued logic: a predicate can be true, false, or unknown. A comparison with `NULL` generally produces unknown rather than true or false.

This matters when comparing `NOT EXISTS` with `NOT IN`.

    WHERE developer_id NOT IN (
        SELECT reviewer_id
        FROM reviewer_candidates
    )

If the candidate set contains `NULL`, `NOT IN` can evaluate to unknown for otherwise unmatched identifiers. Rows for which the predicate is unknown are not returned by the `WHERE` clause.

The corresponding anti-join can use:

    WHERE NOT EXISTS (
        SELECT 1
        FROM reviewer_candidates AS c
        WHERE c.reviewer_id = d.developer_id
    )

The equality comparison against a null candidate is unknown and does not count as a match. If no non-null candidate matches the developer, the subquery returns no rows and `NOT EXISTS` is true.

`NOT EXISTS` is often the safer expression for a missing-related-record test when nullable values might enter the subquery. The correct choice still depends on the intended business semantics, including how null outer keys should be treated.

## Nested NOT EXISTS and relational division

Nested existence predicates can express a universal condition: every required item must have a corresponding qualifying record.

Suppose a repository requires `unit-tests` and `security-scan`. A pull request must not have any required check for which no successful result exists.

    SELECT p.pull_request_id
    FROM pull_requests AS p
    WHERE NOT EXISTS (
        SELECT 1
        FROM required_checks AS requirement
        WHERE requirement.repository_id = p.repository_id
          AND NOT EXISTS (
              SELECT 1
              FROM status_checks AS actual
              WHERE actual.pull_request_id = p.pull_request_id
                AND actual.check_name = requirement.check_name
                AND actual.check_state = 'success'
          )
    );

The outer `NOT EXISTS` rejects a pull request if a missing or unsuccessful requirement is found. The inner `NOT EXISTS` determines whether a particular required check has a successful result.

This is closely related to relational division. Relational division identifies entities that are related to every member of a specified requirement set. It appears in compliance checks, course-completion queries, permission policies, and deployment readiness.

An empty requirement set requires a deliberate decision. The universal condition is mathematically true when there are no required items, a property called vacuous truth. Some business rules want this behavior; others require at least one requirement. The SQL implementation demonstrates how an additional `EXISTS` condition can require a nonempty policy.

## Python implementation

The Python script uses SQLite and the standard library. It creates a relational dataset containing developers, repositories, pull requests, reviews, status checks, permissions, and required checks.

The `demo_exists` function uses a correlated subquery to retrieve open pull requests with approvals. `demo_not_exists` identifies open requests without an approval. `demo_join_comparison` contrasts ordinary join output with semi-join output, making duplicate behavior visible.

`demo_nested_exists` combines approval eligibility with a nested anti-join over required status checks. A check that has not been recorded is not treated as successful. The review threshold example counts distinct active reviewers rather than raw review events.

The NULL demonstration inserts a null candidate and compares `NOT EXISTS` with `NOT IN`. The parameterized permission example separates input values from SQL text, reducing SQL-injection risk. The query-plan demonstration exposes SQLite's chosen access strategy, while unit tests verify result sets, validation, duplicate behavior, and foreign-key enforcement.

Run the script with Python 3.10 or later:

    python existence_queries.py

It requires no third-party package. The sample data is created in memory, so running the program does not alter a persistent database.

## JavaScript implementation

The JavaScript implementation models existence predicates using `Array.some()`. A call to `some()` returns as soon as a matching element is found, making it a natural in-memory counterpart to `EXISTS`. Negating the result represents `NOT EXISTS`.

The `semiJoin` function filters outer records using an existence predicate. The `antiJoin` function retains records for which no matching inner record exists. The separate `innerJoin` function emits matching pairs and illustrates why an ordinary join can produce more rows.

The required-check evaluator uses a nested anti-join to detect any required check without a successful result. Approval eligibility is based on distinct reviewer identifiers and the reviewed base version, rather than simply counting approval events.

`RepositoryWorkflow` introduces event-driven state changes. It validates transitions, increments a revision counter, and emits events when a pull request changes. The asynchronous repository adapter demonstrates existence checks behind an asynchronous interface without requiring a network connection.

The in-memory revision check is illustrative rather than a distributed concurrency guarantee. A production service must enforce state changes atomically in its persistent data store. Likewise, JavaScript's ordinary null comparisons do not automatically reproduce SQL's three-valued logic. The implementation calls out that distinction rather than assuming the two languages have identical predicate behavior.

Run with Node.js 18 or later:

    node existence_queries.js

## C++ governance case study

The C++ program implements a repository governance engine. Its domain records represent developers, repositories, pull requests, reviews, and status checks. The `RepositoryGovernance` class owns the state and evaluates merge eligibility.

The generic `semiJoin` and `antiJoin` functions make the cardinality distinction explicit. Both use `std::any_of` to test whether a matching inner record exists. The semi-join retains each qualifying outer element once, while the anti-join retains elements without a match.

The merge evaluator separates several independent conditions:

- The request must be open and not a draft.
- The target repository must have the required protection policy.
- The number of distinct active, eligible reviewers must satisfy the configured threshold.
- Stale approvals are ignored when the policy requires re-review after a base-version change.
- An active changes-requested review can block the merge.
- Every required check must have a successful matching result.
- Linear-history and resolved-conversation requirements must be satisfied.

The implementation also models repository permissions and an explicit administrator bypass. A bypass is a policy exception, not an ordinary approval. The program verifies administrator identity and whether the repository allows bypass.

The case study demonstrates state transitions and rejects an ineligible merge. It is an in-memory model, so it cannot guarantee consistency between concurrent processes. A production governance engine must re-evaluate the conditions within an atomic transaction and preserve an audit record of privileged overrides.

Compile and run with a C++17-compatible compiler:

    g++ -std=c++17 -O2 -Wall -Wextra -pedantic repository_governance.cpp -o repository_governance
    ./repository_governance

## Java enterprise model

The Java implementation separates repository policy from pull-request state. Records provide immutable representations of developers, repositories, pull requests, reviews, checks, and eligibility results. The service maintains the associations and validates identifiers before accepting related records.

`Stream.anyMatch()` implements an existence test, while filtered streams identify eligible approvals and active change requests. The approval count uses distinct reviewer identifiers, preventing repeated review events by one person from satisfying a multi-reviewer requirement.

The policy evaluator checks the current base version when stale approvals must be dismissed. It treats failed or missing required checks as blockers. Unresolved review discussions are evaluated separately from approval state because resolving a conversation does not itself mean the change has been approved.

`GovernanceException` represents policy violations during state transitions. The `merge` method refuses an ineligible request and replaces the immutable pull-request record with a merged version when the decision succeeds.

The model intentionally distinguishes policy evaluation from persistence. An application using this design would need database transactions, suitable locks or optimistic concurrency controls, and atomic policy re-evaluation to prevent a review or check from changing between validation and merge.

Compile and run with Java 17 or later:

    javac RepositoryGovernance.java
    java RepositoryGovernance

## PostgreSQL relational model

The SQL script creates an isolated `existence_lab` schema. Its tables capture the relationships that the queries need to test:

| Table | Role in existence queries |
|---|---|
| `developers` | Determines reviewer identity and active status |
| `repositories` | Stores target-branch governance policies |
| `repository_permissions` | Establishes repository-level access |
| `pull_requests` | Supplies the outer relation for lifecycle queries |
| `commits` | Records changes associated with a pull request |
| `reviews` | Supplies approval, comment, and changes-requested events |
| `review_comments` | Records discussion threads and their resolution state |
| `status_checks` | Stores test and security-check results |
| `required_checks` | Defines the checks that a repository requires |
| `branch_protection_events` | Records denied operations and policy events |

Primary keys identify individual records. Foreign keys prevent reviews and checks from referring to nonexistent pull requests. Check constraints restrict valid states and permission values. Unique constraints prevent duplicate repository names, commit hashes, and check names per pull request.

Indexes target the access patterns used by the existence predicates. The review index supports lookups by pull request and review state. The status-check index supports correlation by request, check name, and result. The partial index on unresolved review comments supports queries that search specifically for unresolved threads.

The SQL examples include semi-joins, anti-joins, nested anti-joins, a review-comment existence query, relational division, and a comparison between ordinary joins and `EXISTS`. A common table expression builds an explainable merge-eligibility report from independent approval, check, and conversation conditions.

The final transaction demonstrates a guarded state update. It is still a teaching example, not a universal implementation of a production merge service. Correct concurrency handling requires that all relevant policy inputs be revalidated consistently before the state transition is committed.

Execute with PostgreSQL and `psql`:

    psql -v ON_ERROR_STOP=1 -f existence_queries.sql

The script drops and recreates its dedicated schema. Use a disposable database when executing it.

## Performance and query planning

`EXISTS` does not guarantee that a query will be faster than an equivalent join. The optimizer considers available indexes, row counts, data distribution, join conditions, and the estimated cost of each plan.

An existence predicate can stop looking once a qualifying match has been established. A suitable index can make that lookup efficient. For example, an index beginning with `pull_request_id` and including the review state can support correlated approval checks.

An anti-join can be efficient when matching records are rare and the inner lookup is indexed. It can also become expensive when a large outer relation causes repeated scans of an unindexed inner relation.

The Python and C++ examples use straightforward in-memory scans. If there are \(n\) outer records and \(m\) inner records, a naive nested scan can take \(O(nm)\) time. Building a hash index on the inner relation generally takes \(O(m)\) time, followed by expected \(O(n)\) lookup work, assuming suitable hash behavior and enough memory.

The JavaScript benchmark contrasts a scan-based semi-join with a hash-based existence index. Its timings are illustrative and depend on the runtime, workload, hardware, and execution conditions. They should not be treated as database benchmark results.

For a relational database, inspect the actual execution plan. In PostgreSQL, `EXPLAIN` shows the planned operations, while `EXPLAIN (ANALYZE, BUFFERS)` executes the query and reports observed work. Use the latter carefully on production systems because it actually runs the query.

## Correctness and common failure modes

**Missing correlation.** An existence predicate that omits the relationship between outer and inner rows may return all outer rows whenever any qualifying inner row exists. Check that the correlation references the correct key.

**Duplicate multiplication.** A join used only to test existence can multiply outer rows. Use `EXISTS` when the inner columns are not needed in the result.

**NULL with NOT IN.** A null candidate can make an anti-membership predicate unknown. Consider `NOT EXISTS` when the business requirement is the absence of a matching related row.

**Counting events instead of people.** Multiple approvals from one reviewer are not equivalent to approvals from multiple reviewers. Count distinct eligible reviewer identifiers where the policy is based on independent reviewers.

**Treating missing checks as success.** A required check without a result must remain unsatisfied. Nested `NOT EXISTS` makes missing requirements visible.

**Ignoring stale state.** A review can become stale after the base branch changes. Compare the version associated with the review against the current version when the policy requires fresh approval.

**Conflating existence with eligibility.** The existence of an approval does not establish that the reviewer is active, independent of the author, authorized by policy, or reviewing the current changes.

**Racing state changes.** A query can establish eligibility at one moment while another transaction changes a review or status check. Merge services must coordinate policy evaluation and state updates with suitable transaction and concurrency controls.

**Assuming all governance rules are database constraints.** Relational constraints can enforce identities and valid stored states, but cross-table policy conditions often require transactional queries, triggers, or application-level services. The enforcement location must match the concurrency and integrity requirements of the system.

## Branch protection and governance boundaries

Branch protection is a repository policy layer rather than a synonym for review approval. A protected target branch can require approvals and successful status checks, restrict direct pushes, block force pushes, prevent deletion, require linear history, and require resolved conversations.

`EXISTS` and `NOT EXISTS` provide a relational way to evaluate many of these requirements. A required check is satisfied when a matching successful result exists. A required review threshold is met when enough distinct eligible reviewers exist. A conversation requirement is satisfied when no qualifying unresolved discussion remains.

These predicates help evaluate policy, but they do not themselves enforce access control against a Git server. Enforcement requires the repository host or a trusted server-side service to reject prohibited operations. Administrator bypass behavior must be governed explicitly, authenticated, authorized, and audited rather than inferred from the existence of a privileged account.
