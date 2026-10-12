# Correlated Subqueries for Repository Governance

## Scope

A correlated subquery is a subquery whose evaluation refers to a column from a row in an enclosing query. The defining feature is not simply that one query appears inside another query. The defining feature is the dependency between the inner query and the current outer row.

This distinction matters when evaluating repository workflows because the question is usually not "does any review exist?" but "does a review satisfying this condition exist for this particular Pull Request?"

The implementations use Pull Requests, Code Review, Approvals, and Branch Protection as a concrete relational domain. Correlated subqueries are the central SQL mechanism, while the other languages model the same dependency explicitly in application code.

The domain separates four related responsibilities:

- A Pull Request represents a proposed changeset moving from a source branch toward a target branch. Its draft state, author, source branch, target branch, and lifecycle state belong to Pull Request mechanics.
- Code Review represents evaluation of the changeset through review states and review conversations. Comments can remain unresolved even when a review exists.
- Approvals represent a specific review decision. An approval is not equivalent to the existence of a reviewer or a comment, and repository policy may impose eligibility and self-approval restrictions.
- Branch Protection represents repository governance. It can require approvals, successful status checks, resolved conversations, linear history, and restrictions on direct branch operations.

The relationship can be expressed conceptually as:

`Pull Request -> Code Review -> Approval`

while:

`Pull Request -> Target Branch -> Branch Protection`

Merge eligibility is therefore a policy decision that combines the current Pull Request with several related collections.

## Correlation and Outer References

Consider the SQL expression:

`WHERE EXISTS (SELECT 1 FROM reviews r WHERE r.pull_request_id = pr.pull_request_id)`

The `pr.pull_request_id` reference belongs to the outer query. The inner query uses that value while evaluating the current Pull Request.

For PR 41, the inner query searches for reviews belonging to PR 41.

For PR 42, the same logical subquery is evaluated in the context of PR 42.

This is the core distinction between an ordinary independent subquery and a correlated subquery.

An independent subquery can be evaluated without knowing which outer row is currently being processed. A correlated subquery cannot be understood independently when its predicate explicitly depends on an outer reference.

The Python and JavaScript implementations make this dependency visible by passing the outer Pull Request into an inner predicate. The C++ and Java implementations use lambdas and methods that capture or receive the current Pull Request. The SQL implementation expresses the relationship directly through outer-column references.

## Correlated EXISTS

`EXISTS` asks whether at least one related row satisfies a condition.

The repository example asks whether the current Pull Request has an approved review:

`EXISTS (SELECT 1 FROM reviews r WHERE r.pull_request_id = pr.pull_request_id AND r.review_state = 'APPROVED')`

The database does not need the actual number of matching approvals for this particular question. It needs to establish whether at least one qualifying row exists.

This makes `EXISTS` appropriate for questions such as whether a Pull Request has an approval, whether a required status check passed, whether an unresolved conversation exists, or whether an eligible reviewer participated.

The important relationship is the foreign-key correlation:

`reviews.pull_request_id = pull_requests.pull_request_id`

Without that relationship, the query could accidentally answer a repository-wide question instead of a Pull Request-specific question.

## Correlated NOT EXISTS

`NOT EXISTS` is the natural counterpart when the requirement is the absence of a related condition.

The SQL implementation uses it to find Pull Requests without unresolved review conversations.

The expression:

`NOT EXISTS (SELECT 1 FROM review_comments c WHERE c.pull_request_id = pr.pull_request_id AND c.resolved = FALSE)`

means that the current Pull Request has no related comment that remains unresolved.

This is different from testing whether the Pull Request has any comments. A Pull Request may contain many resolved comments and still satisfy the condition.

`NOT EXISTS` is especially useful for governance rules where the absence of a blocking relationship is the requirement.

## Correlated Scalar Aggregates

A correlated subquery can return a scalar value for each outer row.

The SQL implementation calculates the number of reviews for each Pull Request:

`SELECT COUNT(*) FROM reviews r WHERE r.pull_request_id = pr.pull_request_id`

The result is conceptually attached to the current Pull Request.

The same pattern is used for approval counts and the latest review timestamp through `MAX`.

An important SQL distinction is that `COUNT(*)` returns zero when no related rows exist, while an aggregate such as `MAX` produces `NULL` when there is no input value. The Python implementation models the distinction with an integer count and `None` for an absent maximum.

## Pull Request Mechanics

The Pull Request model contains source and target branches because correlation is meaningful only when the correct changeset and destination are associated.

The source branch identifies where the proposed changes originate. The target branch identifies the branch whose governance policy will determine merge eligibility.

Draft Pull Requests are treated as a separate lifecycle state. A draft can contain reviews and checks, but the governance engine still prevents it from being considered merge eligible until it leaves the draft state.

The examples do not treat a Pull Request as merely a row with a title. The model includes the relationships needed to evaluate its lifecycle and merge conditions.

Synchronization and conflict handling are operational Pull Request concerns. A status-check result belongs to the specific Pull Request, and a branch-protection decision is evaluated against the current state of that Pull Request rather than against the repository as a whole.

## Code Review Mechanics

Code Review is represented by the `reviews` and `review_comments` relations.

A review has a state such as `APPROVED`, `COMMENTED`, `CHANGES_REQUESTED`, or `DISMISSED`.

A comment is a separate object because review discussion and review state are not identical. A Pull Request can have an approved review while still containing an unresolved conversation.

The correlated queries preserve this distinction. Approval counting filters on review state, while conversation enforcement examines comments independently.

This separation prevents a common modeling error in which every review interaction is treated as an approval.

The review-specific queries also demonstrate reviewer eligibility. A nested correlated query can first locate an approval for the current Pull Request and then verify that the reviewer associated with that approval is active and eligible.

## Approval Semantics

An approval is a decision associated with a specific Pull Request and reviewer.

The examples exclude self-approval by comparing the reviewer identity with the current Pull Request author:

`reviewer.user_id <> pr.author_id`

This is a genuinely correlated condition because the valid-review calculation depends on the current outer Pull Request's author.

The approval count also filters for active and review-eligible users. This prevents a historical or otherwise ineligible review from automatically satisfying the current policy.

Approval requirements are therefore evaluated as a relationship between:

`current Pull Request -> qualifying reviews -> eligible reviewers`

rather than as a repository-wide count.

Stale approvals and approval dismissal are policy concerns that must be represented explicitly when implementing a production governance system. A production schema can extend the review model with commit or revision identifiers and use those values to determine whether an approval still applies to the current changeset.

## Branch Protection

Branch Protection operates at the target-branch level.

The SQL schema stores protection policy separately from Pull Requests. The current Pull Request identifies its target branch, and that target branch identifies the policy that applies.

This produces a two-stage relationship:

`pr.target_branch_id -> branch_protection_policies.branch_id`

and then:

`policy -> required checks / approval threshold / conversation requirement`

The branch-protection model includes required approvals, required status checks, conversation resolution, force-push restrictions, deletion restrictions, and linear-history requirements.

The SQL merge-eligibility query uses correlated expressions to evaluate those policy requirements for each current Pull Request.

A protected branch therefore does not simply mean "this branch is important." It means that repository governance imposes enforceable conditions on changes targeting that branch.

## Required Status Checks

Required checks are modeled separately because a branch can require multiple named checks.

The correlated query evaluates each required check in the context of the current Pull Request:

`required_check.branch_id = pr.target_branch_id`

followed by an inner `EXISTS` against `status_checks` using:

`actual_check.pull_request_id = pr.pull_request_id`

This demonstrates nested correlation.

The outer Pull Request establishes which branch policy applies. The required-check row establishes the name of a required check. The innermost lookup determines whether the current Pull Request has a successful result for that specific check.

This is substantially different from checking whether any successful `security-scan` exists somewhere in the repository.

## Nested Correlation

Nested correlation occurs when an inner query depends on values from an outer query, and another nested operation depends on the current inner row.

The SQL example:

`Pull Request -> Review -> User`

first selects a review belonging to the current Pull Request and then verifies the user associated with that review.

The same structure appears in the Java and C++ implementations.

Nested correlation is useful when a business rule crosses several related entities but the condition must remain anchored to the current outer entity.

It should not be used merely because nested syntax is possible. If a join or precomputed relation expresses the relationship more clearly and efficiently, that alternative may be preferable.

## Python Implementation

The Python program builds a small repository-governance model with dataclasses for Pull Requests, reviews, comments, status checks, and branch-protection policy.

`correlated_exists()` provides a reusable logical equivalent of a correlated `EXISTS`. Its predicate receives both the current outer object and an inner object.

`correlated_count()` models a correlated scalar `COUNT`, while `correlated_max()` models a scalar aggregate that can return no value.

The governance evaluator combines correlated approval counting, status-check lookup, and unresolved-comment detection. It therefore demonstrates how several correlated relationships can contribute to one merge decision.

The indexed lookup section addresses execution cost. A naive implementation scans all reviews for every Pull Request. Grouping reviews by `pull_request_id` creates an index-like structure and avoids repeatedly traversing unrelated reviews.

## JavaScript Implementation

The JavaScript program uses array methods and event-driven behavior rather than translating the Python program mechanically.

`correlatedExists()` uses `filter()` and `some()`. The callback receives the current outer row and inner row, making the correlation explicit.

The event processor demonstrates an application pattern in which a status-check event contains a Pull Request identifier. The event handler correlates that identifier with the repository's Pull Request state before evaluating governance.

JavaScript's `Map` is used as an application-level index keyed by Pull Request ID. This demonstrates why logical correlation does not dictate a particular physical execution strategy.

The implementation also uses immutable repository data through `Object.freeze()`, optional chaining for missing reviewer data, and explicit asynchronous event handling.

## C++ Case Study

The C++ program presents a repository governance engine.

The `PullRequest`, `Review`, `StatusCheck`, `ReviewComment`, and `BranchProtection` structures represent the domain independently.

The `approvedPullRequests()` function models correlated `EXISTS`. The lambda captures the current Pull Request and compares its identifier against the review's foreign key.

`reviewCounts()` demonstrates correlated aggregation.

`evaluateMergeEligibility()` is the central case study. It evaluates draft state, qualifying approvals, required status checks, and unresolved conversations against a protected branch policy.

The program also constructs an `unordered_map` indexed by Pull Request ID. This demonstrates an important execution concern: a logically correlated operation may be implemented with indexed access rather than repeated full scans.

The complexity of naive nested scanning is approximately `O(N*M)` for `N` outer rows and `M` inner rows. Real database engines may use indexes, hash-based strategies, joins, semi-joins, or decorrelation transformations to reduce the physical cost.

## Java Enterprise Model

The Java implementation uses records for immutable domain objects and a dedicated merge-eligibility service.

`BranchProtection` validates its own policy invariants, while `countValidApprovals()` encapsulates approval semantics.

The Java streams express correlated predicates using `anyMatch()`, `noneMatch()`, and `filter()`.

The implementation separates Pull Request state from review decisions and branch policy. This makes it possible to reason about invalid states and policy failures without reducing everything to one conditional statement.

The `MergeDecision` record provides an explicit representation of eligibility and blocking reasons, which is more useful for enterprise systems than returning a single boolean without context.

## SQL Data Model

The PostgreSQL schema contains repositories, users, branches, Pull Requests, commits, reviews, review comments, status checks, branch-protection policies, and required status checks.

Foreign keys preserve the relationships required by correlated queries.

The schema uses `CHECK` constraints for lifecycle states and review states. Unique constraints prevent duplicate repository branch names, Pull Request numbers within a repository, commit SHAs, and duplicate status-check names for the same Pull Request.

Indexes on `pull_request_id` support the relationships repeatedly accessed by correlated predicates.

The SQL script includes executable sample data and then evaluates the same governance domain through correlated `EXISTS`, `NOT EXISTS`, scalar aggregates, nested correlation, and policy queries.

The transaction section changes the required approval threshold and then demonstrates how the resulting policy affects the correlated approval calculation.

## Correlated Execution and Query Planning

A correlated SQL expression describes a logical dependency. It does not necessarily require the database to physically execute the inner query from scratch for every outer row.

For example, the logical form:

`SELECT ... WHERE EXISTS (...)`

may be transformed by a query planner into a semi-join or another equivalent strategy.

An index on the correlated column can also make repeated lookups efficient. In the governance schema, `reviews.pull_request_id`, `review_comments.pull_request_id`, and `status_checks.pull_request_id` are indexed because these relationships are repeatedly evaluated.

The difference between logical query structure and physical execution plan is essential when analyzing performance.

A correlated query that reads clearly can still produce an efficient plan. Conversely, a correlated query over a large unindexed relation can become expensive.

## When Correlated Subqueries Are Useful

Correlation is particularly expressive when the business question is naturally phrased as "for each current row, does a related condition exist?"

Examples in this domain include:

- determining whether each Pull Request has an approval;
- identifying Pull Requests with no unresolved conversations;
- counting reviews belonging to each Pull Request;
- finding the latest review for each Pull Request;
- checking whether every required status check has a successful result for the current Pull Request;
- verifying that an approval belongs to an active and eligible reviewer;
- comparing the current Pull Request's state against its target branch's policy.

These questions are row-contextual. The current Pull Request matters to the meaning of the inner operation.

## Correlated Subquery Versus Join

A correlated subquery and a join can often express related business logic, but they communicate different intent.

`EXISTS` naturally communicates existence. It avoids multiplying outer rows when multiple related records exist.

A join is often more appropriate when columns from both relations must be returned together or when a relational transformation naturally produces a set of combined rows.

A correlated scalar aggregate is useful when a single derived value belongs to each outer row.

The correct choice depends on semantics, cardinality, readability, and the execution plan rather than on a rule that one construct is universally faster.

## Common Failure Modes

A correlation can be accidentally removed when the inner predicate does not reference the outer row. The resulting query may answer a repository-wide question rather than a Pull Request-specific question.

A second failure occurs when a developer uses `COUNT(*) > 0` where `EXISTS` is sufficient. `EXISTS` communicates the intent directly and allows the database to stop looking once a qualifying row has been established.

A third failure occurs when approval state is confused with reviewer participation. A commented review is not an approval.

Another failure occurs when unresolved conversations are inferred from the existence of comments. Resolved comments must not block a Pull Request when the policy only requires unresolved conversations to be absent.

Self-approval is another policy-specific edge case. A simple `review_state = 'APPROVED'` condition does not automatically implement a rule that the author cannot approve their own Pull Request.

## NULL and Empty Results

Correlated aggregates have different behavior depending on the aggregate.

`COUNT(*)` returns zero when the current Pull Request has no matching reviews.

`MAX(submitted_at)` returns `NULL` when no review exists.

This distinction is important when correlated results are later compared or displayed.

A scalar correlated subquery that unexpectedly produces multiple rows is an error in SQL. The inner expression must be guaranteed to produce one scalar value, normally through an aggregate or a predicate that establishes uniqueness.

## Performance Considerations

The conceptual naive execution of a correlated lookup over `N` Pull Requests and `M` reviews can approach `O(N*M)` comparisons.

Indexes change the physical access pattern. An index on `reviews.pull_request_id` lets the database locate related reviews without scanning every review row for every Pull Request.

A query planner may also decorrelate a subquery. This means the SQL can retain a correlated formulation for clarity while the database executes an equivalent join-like strategy.

Performance analysis should therefore inspect the actual execution plan rather than assuming that textual correlation determines physical execution.

Large-scale systems should also consider selectivity, index width, stale statistics, cardinality estimates, repeated correlated aggregates, and whether a set-based rewrite would provide a simpler execution strategy.

## Security and Governance Boundaries

Repository governance is security-sensitive because an incorrect merge-eligibility query can allow an unreviewed or insufficiently reviewed change into a protected branch.

The database schema therefore enforces structural integrity through foreign keys and check constraints.

Application logic remains responsible for higher-level policy semantics such as reviewer eligibility, approval freshness, and lifecycle decisions that may depend on external repository events.

The safest design places invariant relationships at the database layer and evaluates dynamic governance rules against authoritative current state.

## Practical Relationship Between the Four Governance Areas

A Pull Request is the proposed change workflow.

Code Review evaluates the changeset and produces review states and conversations.

An Approval is a specific qualifying review decision. It is only one input into merge eligibility.

Branch Protection defines the repository-level policy that determines which conditions must be satisfied before the Pull Request can merge.

Correlated subqueries connect these layers without collapsing them into one concept. The outer Pull Request supplies the context, while inner queries evaluate reviews, approvals, comments, checks, and policies specifically for that Pull Request.
