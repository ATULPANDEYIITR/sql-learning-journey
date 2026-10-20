# Advanced Aggregation: Pull Requests, Code Review, Approvals, and Branch Protection

## Scope

This artifact set studies advanced aggregation through repository-governance data. The four governance concepts remain distinct:

| Area | Role in the workflow |
|---|---|
| Pull Requests | Provide the workflow for proposing and merging a changeset |
| Code Review | Evaluates the proposed changes through reviews, comments, and review states |
| Approvals | Represent qualifying reviewer decisions that contribute to merge eligibility |
| Branch Protection | Enforces repository-level conditions before a protected branch can accept a merge |

The central analytical problem is not simply counting Pull Requests. A realistic repository dataset contains multiple dimensions that must be aggregated simultaneously: changesets, review activity, approvals, status checks, merge strategies, cycle time, branch policies, and merge eligibility.

## Advanced Aggregation Concepts

The implementations distinguish several aggregation strategies.

**Multiple aggregation** calculates several measures over the same grouping. A repository can simultaneously report Pull Request count, merged Pull Request count, total code changes, average reviews, average approvals, and average merge cycle time.

**Conditional aggregation** calculates a measure only when a predicate is satisfied. Examples include merged Pull Requests, Pull Requests with at least two active approvals, Pull Requests with failed status checks, large changesets, and Pull Requests satisfying branch-policy conditions.

**Categorical aggregation** groups records by a domain dimension such as repository, target branch, review state, or merge strategy.

**Policy aggregation** combines independent conditions into a governance result. Merge eligibility is therefore different from a simple count of approvals. A Pull Request can have sufficient approvals and still be blocked by failing status checks, unresolved discussions, an invalid state, or another protected-branch requirement.

A useful conceptual model is:

Repository data  
→ Pull Request grouping  
→ review and approval aggregation  
→ status-check aggregation  
→ branch-policy evaluation  
→ conditional merge-eligibility aggregation

## Pull Request Lifecycle

A Pull Request connects a source branch to a target branch and carries a changeset represented by commits, additions, and deletions.

Typical states represented by the implementations are:

`open → merged`

or

`open → closed`

A closed Pull Request is not equivalent to a merged Pull Request. Aggregations therefore use explicit state predicates rather than inferring state from the presence of reviews or commits.

Draft Pull Requests are conceptually part of the proposal workflow but should not automatically be interpreted as merge-eligible. Base-branch synchronization can change the effective changeset and may introduce merge conflicts. Reopening a closed Pull Request changes its workflow state and should not silently reuse stale analytical assumptions.

The Python model represents lifecycle state directly in the `PullRequest` object. The JavaScript model exposes state-aware policy evaluation. The C++ engine treats state as one of several independent merge conditions. The Java model uses an explicit `PullRequestState` enum. PostgreSQL enforces the state and merge-timestamp relationship through constraints.

## Code Review

Code Review is the evaluation layer applied to a Pull Request.

A review has a state such as:

| Review state | Meaning |
|---|---|
| `approved` | Reviewer accepts the changes for the review purpose |
| `changes_requested` | Reviewer identifies changes that must be addressed |
| `commented` | Reviewer provides feedback without producing an approval decision |

Inline comments are modeled separately from reviews in SQL. This distinction allows unresolved discussion counts to be aggregated without treating every comment as an approval or rejection.

Reviewer activity can be aggregated independently from Pull Request activity. For example, a repository can have a high average review count while still having insufficient qualifying approvals.

The Java implementation models reviews as immutable records and explicitly distinguishes reviewer eligibility and dismissed reviews. This prevents a historical approval from automatically becoming an active approval.

## Approvals

An approval is a specific review decision rather than a generic review event.

The implementations count an approval only when the relevant review is:

- in the approved state,
- associated with an eligible reviewer,
- not dismissed.

This prevents a raw count of review rows from being mistaken for an approval count.

For example, four reviews do not necessarily represent four usable approvals:

| Review | State | Eligible | Dismissed | Active approval |
|---|---|---:|---:|---:|
| Reviewer A | approved | yes | no | yes |
| Reviewer B | approved | yes | no | yes |
| Reviewer C | commented | yes | no | no |
| Reviewer D | approved | no | no | no |

Stale or dismissed approvals are therefore excluded from active approval aggregation.

Approval requirements belong to repository governance rather than to the basic Pull Request object. The SQL model stores required review counts in `branch_protection`, allowing different protected branches to use different policies.

## Branch Protection

Branch Protection is the enforcement layer.

A protected branch can require:

- a minimum number of qualifying reviews,
- passing status checks,
- resolved conversations,
- restrictions on direct pushes,
- restrictions on force pushes,
- restrictions on branch deletion,
- linear history.

The aggregation model evaluates these conditions independently before combining them into a final eligibility result.

This distinction is important:

`Pull Request → proposes`

`Code Review → evaluates`

`Approval → records a qualifying review decision`

`Branch Protection → enforces merge conditions`

An approval alone does not guarantee merge eligibility.

## Python Implementation

The Python script models repository-governance records using an immutable `PullRequest` dataclass.

It provides:

- grouped repository metrics,
- numeric aggregation,
- conditional aggregation,
- author-level aggregation,
- merge-strategy distribution,
- merge-cycle calculations,
- validation of workflow integrity,
- merge-eligibility statistics.

The `aggregate()` function calculates count, sum, average, minimum, and maximum for a numeric collection. This creates a reusable aggregation primitive rather than implementing every statistic independently.

Repository aggregation uses grouped records and then derives several measures from the same group. Conditional aggregation uses Boolean expressions such as whether a Pull Request is merged, has sufficient approvals, or exceeds a changeset threshold.

Validation occurs before reporting. Duplicate Pull Request numbers, negative metrics, invalid states, missing merge timestamps, and merged Pull Requests with failed checks are rejected.

The Python implementation is suitable for in-memory analytical processing where the repository dataset has already been loaded into application memory.

## JavaScript Implementation

The JavaScript implementation treats aggregation as an event-oriented reporting operation.

`Map.groupBy()` provides categorical grouping while array reductions provide conditional and numerical aggregation. The implementation separates repository aggregation from target-branch aggregation so that the same source data can support multiple analytical views.

The asynchronous `generateReport()` function represents an application boundary where the same reporting layer could consume repository information from an asynchronous API or database source.

The `evaluateMergeEligibility()` function demonstrates an important aggregation principle: policy evaluation can produce both a Boolean result and a collection of failure reasons. Aggregating these decisions provides counts of eligible and ineligible Pull Requests without losing the underlying governance logic.

Validation prevents malformed records from entering the reporting pipeline.

## C++ Implementation

The C++ implementation uses a repository-governance engine rather than reproducing the object model used by Python.

The `RepositoryMetrics` structure accumulates vectors of measures for each repository. A generic `aggregate()` function then calculates statistical properties over those measures.

The implementation also aggregates governance failure reasons:

- Pull Request not open,
- failed status checks,
- insufficient approvals,
- requested changes.

This gives a diagnostic distribution rather than reducing every blocked Pull Request to a single `false` value.

The C++ implementation demonstrates explicit ownership of aggregation state through STL containers. `std::map` provides deterministic grouped output, while `std::unordered_set` supports efficient duplicate-number validation.

For `n` Pull Requests, the primary aggregation passes are approximately O(n), excluding the cost of output ordering. The grouped structures require O(n) additional storage.

## Java Implementation

The Java implementation uses explicit enterprise domain types.

`PullRequest`, `Review`, and `StatusCheck` are immutable records. Enumerations represent controlled domain states, while `GovernancePolicy` represents repository-level policy independently from individual Pull Requests.

The `activeApprovals()` method demonstrates that an approval is derived from multiple attributes rather than from the review state alone.

The aggregation layer uses Java Streams for:

- grouping by repository,
- counting merged Pull Requests,
- summing changes,
- calculating averages,
- conditional counting,
- grouping review states.

The policy object makes governance requirements explicit. The same Pull Request data can therefore be evaluated under different branch-protection policies without changing the underlying domain records.

This separation is useful in enterprise systems where policy configuration changes independently from repository events.

## PostgreSQL Implementation

The PostgreSQL implementation models the domain relationally.

The principal relationships are:

`repositories → branches → pull_requests`

and

`pull_requests → reviews → review_comments`

with status checks attached directly to Pull Requests.

Branch protection is associated with a branch through a one-to-one policy record.

Database constraints enforce important integrity conditions. Negative additions, deletions, commits, and review requirements are rejected. A merged Pull Request must have a merge timestamp, and the timestamp cannot precede the opening timestamp.

The `pull_request_aggregation` view centralizes derived metrics such as:

- total changes,
- review count,
- active approvals,
- passed status checks,
- total status checks,
- unresolved comments,
- merge cycle time.

This avoids repeating complex joins in every analytical query.

### Multiple Aggregations

The repository report combines `COUNT`, `SUM`, and `AVG` in one grouped query.

The same grouping therefore produces operational measures such as Pull Request volume, merged volume, total changes, review activity, approval activity, and cycle time.

### Conditional Aggregation

PostgreSQL's `FILTER (WHERE ...)` syntax provides direct conditional aggregation.

For example, the reporting queries separately count:

- merged Pull Requests,
- large Pull Requests,
- Pull Requests with two or more approvals,
- Pull Requests with all checks passing,
- Pull Requests with resolved discussions.

This is clearer than creating separate queries for every condition.

### CTE-Based Policy Evaluation

The branch-policy CTE first evaluates each Pull Request against its target branch's policy.

The final aggregation then counts eligible and blocked Pull Requests per repository.

This separates row-level policy evaluation from group-level reporting.

### Transactional Integrity

The script includes a transaction demonstrating database-level validation. An attempted negative review requirement violates the `CHECK` constraint and is rolled back.

This illustrates the distinction between application-level aggregation and database-level integrity enforcement.

## Aggregation Strategy Comparison

| Strategy | Appropriate use | Example |
|---|---|---|
| Single-pass accumulation | Large in-memory datasets | Repository totals |
| Grouped aggregation | Repository or branch comparisons | Metrics by target branch |
| Conditional aggregation | Governance predicates | PRs with failed checks |
| Hierarchical aggregation | Multiple domain levels | Repository → branch → PR |
| Policy aggregation | Merge eligibility | Approvals + checks + discussions |
| SQL aggregation | Persistent relational data | `GROUP BY` with `FILTER` |
| Stream aggregation | Immutable Java domain data | Grouping and averages |
| Diagnostic aggregation | Failure analysis | Counts by blocking reason |

## Edge Cases and Failure Conditions

Aggregation can produce misleading results if the source records are not validated.

Important cases include:

- a merged Pull Request without a merge timestamp,
- a review from an ineligible reviewer,
- a dismissed approval,
- stale approval after a policy-relevant change,
- a Pull Request with failed status checks,
- unresolved review discussions,
- duplicate Pull Request numbers,
- negative change counts,
- empty aggregation groups,
- an open Pull Request with no approvals,
- a protected branch with a different policy from another branch,
- a large changeset that remains blocked despite having approvals.

Empty numeric groups should not produce division-by-zero errors. The implementations therefore provide zero-valued aggregate results or use safe averaging operations.

## Performance Considerations

For an in-memory collection containing `n` Pull Requests, most aggregation operations are O(n). Grouped aggregation generally requires O(n) additional memory.

Multiple independent passes are often acceptable for moderate repository datasets because they keep the implementation simple and auditable. For very large datasets, a single-pass accumulator can reduce traversal overhead.

Relational databases can perform aggregation efficiently when filtering and grouping are supported by appropriate indexes. The SQL implementation indexes repository/state combinations, Pull Request review relationships, and status-check relationships because these columns participate in common reporting and evaluation paths.

Indexes should not be added indiscriminately. Every index increases storage requirements and write overhead.

## Security and Governance Considerations

Aggregation should respect repository authorization boundaries. A reporting service must not expose private repository metrics to unauthorized users merely because those records exist in a shared analytical store.

Approval counts should be derived from authoritative review state rather than client-supplied totals. Branch-protection rules should be enforced independently of dashboard calculations.

A reporting result such as `merge_eligible = true` should not itself be treated as an authorization token. The actual merge operation must still be protected by repository-level controls and current state validation.

Historical aggregation also requires care. A dismissed approval should not be counted as a current approval merely because it was valid at an earlier point in time.

## Practical Analytical Questions

The implemented models can answer questions such as:

- Which repositories have the highest Pull Request volume?
- Which repositories have the largest aggregate changesets?
- What is the average review activity per Pull Request?
- How many Pull Requests have enough active approvals?
- How many are blocked by failed status checks?
- Which merge strategies are most common?
- Which repositories have unusually large Pull Requests?
- How many reviews resulted in requested changes?
- How many Pull Requests have unresolved discussions?
- How many Pull Requests satisfy the complete protected-branch policy?

These questions demonstrate why advanced aggregation is more useful than a single aggregate such as total Pull Requests. The meaningful result comes from combining measures, predicates, grouping dimensions, and governance rules without confusing the four distinct repository mechanisms.
