# BCNF and Advanced Normalization

## Scope

This implementation models repository-development governance through Pull Requests, Code Review, Approvals, and Branch Protection. The source files treat these mechanisms as distinct domain concepts that interact during merge eligibility.

The four mechanisms have different responsibilities:

| Mechanism | Primary responsibility |
|---|---|
| Pull Request | Proposes a changeset from a source branch toward a target branch |
| Code Review | Evaluates the proposed changeset |
| Approval | Records a reviewer's explicit review decision |
| Branch Protection | Enforces repository-level conditions before merge |

The implementations model these distinctions in Python, JavaScript, C++17, Java 17, and PostgreSQL.

## Domain Model

The central relationship is:

Repository
→ Branches
→ Commits
→ Pull Requests
→ Reviews
→ Review Comments
→ Conversations
→ Status Checks
→ Branch Protection Policies
→ Approval Requirements
→ Merge Eligibility
→ Merge

A Pull Request represents a proposed integration operation. It does not itself represent approval, branch protection, or a review decision.

The source branch contains the proposed changes. The target branch represents the integration destination. A Pull Request therefore connects two branch states rather than replacing either branch.

## Pull Request Lifecycle

A Pull Request can progress through several states:

`draft → open → merged`

or:

`draft → open → closed → open`

A closed Pull Request can be reopened when the proposed work needs to continue. A merged Pull Request is terminal for the modeled workflow.

A Pull Request contains a changeset represented by one or more commits. The latest commit is treated as the current head of the proposed changes.

The implementations validate:

- source branch existence
- target branch existence
- source and target branch distinction
- non-empty changesets
- valid Pull Request state
- valid reviewer participation
- current commit identity
- merge strategy
- synchronization state

Draft Pull Requests are intentionally prevented from merging. They can be used for early discussion while signaling that the changes are not yet ready for final integration.

## Branch State and Proposed Changes

A critical distinction is the difference between a Pull Request changeset and branch state.

The Pull Request describes proposed changes:

`source branch + commits → target branch`

The target branch can change while the Pull Request remains open. When that occurs, the proposed changes may need synchronization with the new base state.

The implementations therefore track `base_sync_required`.

A synchronization operation can change the Pull Request head commit. Reviews associated with an older commit are treated as stale or dismissed because the reviewer decision no longer corresponds to the current changeset.

This prevents an approval for one version of a changeset from automatically authorizing a materially different version.

## Code Review

Code Review evaluates proposed changes.

A review contains:

- reviewer identity
- review state
- reviewed commit
- review comments

The review states represented by the implementations are:

| State | Meaning |
|---|---|
| `commented` | Reviewer provided feedback without an approval decision |
| `changes_requested` | Reviewer identified required changes |
| `approved` | Reviewer accepts the current changeset |
| `dismissed` | Earlier review decision is no longer active |

Code Review is therefore an evaluation mechanism rather than a repository-enforcement mechanism.

A review can create a discussion that must be resolved before merging. This separates the act of commenting from the repository policy that determines whether unresolved discussions block integration.

The implementations reject a changes-requested review without a meaningful comment. This models a useful validation rule because a requested change should identify an actionable issue.

## Review Conversations

Review conversations represent discussions generated from review activity.

A conversation can be:

`open → resolved`

An unresolved conversation is not itself an approval or rejection. Its effect depends on branch governance.

When a branch policy requires all conversations to be resolved, unresolved conversations become a merge blocker.

This distinction avoids treating discussion state as equivalent to review state.

## Approvals

An approval is a specific review decision.

Approval eligibility is evaluated independently from the existence of a Pull Request.

The modeled approval rules include:

- reviewer must be eligible
- Pull Request author cannot approve their own Pull Request
- approval must correspond to the current Pull Request head
- required approval count must be satisfied
- stale or dismissed approvals do not count

For example, if a Pull Request requires two approvals and has one current approval, merge eligibility remains false.

If the Pull Request receives a new commit after approval, the earlier approval may no longer correspond to the current head. The implementations therefore compare review commit identity with the current Pull Request head.

This models the distinction between:

`approval exists`

and:

`current approval satisfies merge policy`.

## Approval Requirements

Approval requirements belong to repository governance rather than individual review records.

A repository may require:

- one approval
- two approvals
- multiple independent reviewers
- specific reviewer eligibility
- current approvals on the latest changeset

The PostgreSQL implementation stores the required approval count in `branch_protection_policies`.

The C++ implementation stores the policy as `BranchProtection`.

The Java implementation separates reviewer eligibility from merge eligibility using `ReviewPolicy` and `MergeEligibilityService`.

This separation prevents approval logic from becoming tightly coupled to Pull Request storage.

## Stale Approvals

A stale approval is an approval associated with an earlier version of the changeset.

The source files use the current commit identity as the comparison key.

The rule is:

`review.commit = current Pull Request head`

If this condition is false, the approval cannot satisfy the current merge requirement.

This is important when the source branch changes after review.

The workflow therefore distinguishes:

- reviewer identity
- review state
- reviewed commit
- current Pull Request commit
- merge policy

These values are related but not interchangeable.

## Branch Protection

Branch Protection operates at the repository or branch governance layer.

A protected branch can impose conditions such as:

- required reviews
- required status checks
- direct-push restrictions
- force-push restrictions
- deletion restrictions
- conversation-resolution requirements
- linear-history requirements

The implementation deliberately does not treat Branch Protection as Code Review.

Code Review produces review decisions.

Branch Protection determines which conditions must be satisfied before a merge is allowed.

The relationship is:

`Pull Request`
→ evaluated by `Code Review`
→ produces `Approvals`
→ evaluated against `Branch Protection`
→ produces `Merge Eligibility`

## Status Checks

Automated status checks provide machine-generated evidence about the current changeset.

The examples use:

- `unit-tests`
- `security-scan`

A status check is associated with a specific Pull Request head commit.

This matters because a successful test result for an earlier commit should not automatically authorize a later commit.

Required checks are stored in PostgreSQL through `required_status_checks`.

The merge evaluation verifies that every required check:

1. exists,
2. belongs to the current Pull Request head,
3. passed successfully.

## Merge Eligibility

Merge eligibility is a policy decision.

The Python, JavaScript, C++17, Java 17, and PostgreSQL implementations evaluate several conditions together.

Typical conditions include:

| Condition | Example failure |
|---|---|
| Pull Request state | Pull Request is closed |
| Draft state | Pull Request remains a draft |
| Current approvals | Required approvals are missing |
| Status checks | Required check failed |
| Current commit | Review or check belongs to an older head |
| Conversations | Required discussion remains unresolved |
| Base synchronization | Pull Request is behind required base state |
| History policy | Merge commit violates linear-history policy |

A useful conceptual model is:

`Merge Eligibility = Pull Request State × Reviews × Approvals × Checks × Conversations × Branch Policy`

The multiplication here represents conjunction of conditions rather than numeric multiplication.

A single failed mandatory condition can block the merge.

## Merge Strategies

The implementations model three common strategies:

| Strategy | Behavior |
|---|---|
| Merge commit | Creates a dedicated merge commit |
| Squash | Represents the changeset as one integrated commit |
| Rebase | Applies the source commits to the target history |

Linear-history protection can prohibit merge commits.

This demonstrates why merge strategy is not equivalent to review approval. A Pull Request may be fully approved while still being unable to use a prohibited merge strategy.

## Python Implementation

The Python implementation uses dataclasses to model:

- commits
- reviews
- status checks
- branches
- Pull Requests
- repository policies

`RepositoryWorkflow` provides state transitions and merge evaluation.

Sets are used for eligible reviewers and required status checks. This gives efficient membership tests and makes duplicate reviewer identities naturally collapse into one approval identity during eligibility evaluation.

The example deliberately demonstrates a blocked merge before correction and a successful merge after the required conversation is resolved and a second approval is submitted.

Exceptions represent invalid workflow operations such as reviewing a nonexistent Pull Request, approving one's own changes, or merging a Pull Request that fails governance.

## JavaScript Implementation

The JavaScript implementation uses Node.js standard-library `EventEmitter` behavior to model workflow events.

Events include:

- Pull Request opened
- review requested
- review submitted
- status updated
- Pull Request synchronized
- Pull Request merged

`Map` is used for Pull Request and branch registries, while `Set` is used for reviewer and policy membership.

This provides an event-driven perspective distinct from the Python state-oriented implementation.

The implementation also demonstrates asynchronous application structure through an `async` entry point while retaining a dependency-free design.

## C++17 Implementation

The C++ implementation uses explicit domain structures and a `Repository` governance engine.

STL containers model:

- branches with `std::map`
- reviewers with `std::set`
- Pull Requests with `std::map`
- required status checks with `std::set`
- review and commit collections with `std::vector`

The merge evaluator returns both a Boolean eligibility result and a collection of failure conditions.

This is useful for governance systems because an operator needs to know why a merge is blocked rather than receiving only a Boolean result.

The implementation also prevents duplicate branch definitions and validates reviewer eligibility before recording review decisions.

## Java 17 Implementation

The Java implementation uses records for immutable value-oriented domain objects such as:

- `Commit`
- `Review`
- `StatusCheck`
- `BranchProtection`

Domain state that requires transitions is represented by classes such as `PullRequest`.

`ReviewPolicy` separates reviewer eligibility and approval policy from the repository service.

`MergeEligibilityService` evaluates repository policy independently from Pull Request storage.

Custom exceptions represent validation and merge-blocking failures.

This design reflects enterprise service-layer separation where policy evaluation is isolated from persistence-oriented domain state.

## PostgreSQL Data Model

The PostgreSQL implementation provides a normalized relational representation of repository governance.

Major relations include:

| Relation | Purpose |
|---|---|
| `repositories` | Repository identity |
| `users` | Developers and reviewers |
| `branches` | Repository branches |
| `commits` | Commit identity and authorship |
| `branch_commits` | Branch-to-commit membership |
| `pull_requests` | Proposed changes |
| `pull_request_commits` | Pull Request changesets |
| `review_requests` | Requested reviewers |
| `reviews` | Review decisions |
| `review_comments` | Review feedback |
| `conversations` | Discussion state |
| `status_checks` | Automated validation |
| `branch_protection_policies` | Branch governance |
| `required_status_checks` | Required automated checks |
| `merges` | Completed integrations |

Foreign keys enforce relationships between these entities.

Unique constraints prevent duplicate repository names, branch names within repositories, commit SHAs within repositories, and repeated Pull Request numbers within a repository.

Check constraints enforce conditions such as positive Pull Request numbers and non-empty review comments.

## Database Integrity

The PostgreSQL implementation uses a trigger to prevent Pull Request authors from submitting reviews on their own Pull Requests.

Another trigger ensures that a merged Pull Request receives a merge timestamp.

These are database-level integrity rules rather than application-only checks.

This distinction is important because repository governance data may be written by multiple services. Database constraints and triggers provide a final integrity boundary.

## PostgreSQL Merge Evaluation

`get_merge_eligibility` evaluates a Pull Request against its target branch policy.

The function checks:

1. Pull Request existence
2. Pull Request state
3. draft status
4. base synchronization
5. current approval count
6. required status checks
7. unresolved conversations
8. linear-history restrictions

The function returns a row containing:

- `eligible`
- `failure_reason`

Returning failure reasons makes the function useful for operational reporting as well as enforcement.

## Transactions

The PostgreSQL workflow includes transactional merge processing.

The transaction locks the selected Pull Request, evaluates merge eligibility, updates the Pull Request state, and records the merge.

The intended invariant is:

`eligible Pull Request → merged Pull Request + merge record`

If eligibility fails, the transaction raises an exception instead of creating a partial merge state.

## Performance Considerations

The PostgreSQL implementation includes indexes for common governance queries.

Important indexed paths include:

- Pull Requests by target branch and state
- reviews by Pull Request, state, and commit
- status checks by Pull Request, commit, and name
- unresolved comments
- unresolved conversations
- branch commit ordering

The in-memory implementations use hash-based collections where membership tests are frequent.

Merge eligibility still requires scanning reviews and checks associated with the Pull Request. In a production repository platform, these collections would normally be indexed or maintained through specialized persistence structures.

## Security Considerations

Repository governance is security-sensitive because it determines which proposed changes can reach protected branches.

The implementations enforce several controls:

- reviewer eligibility
- self-review prevention
- protected-branch restrictions
- required approvals
- required status checks
- current-commit validation
- unresolved-conversation enforcement
- force-push restrictions
- direct-push restrictions
- deletion restrictions
- linear-history policy

The PostgreSQL schema uses foreign keys to reduce orphaned governance records.

Application code should also authenticate users and authorize every state-changing operation. The examples model authorization rules but do not implement an identity provider or cryptographic authentication system.

## Failure Modes

Representative failures include:

| Failure | Governance response |
|---|---|
| Unknown branch | Reject Pull Request creation |
| Empty changeset | Reject Pull Request |
| Self-review | Reject review |
| Ineligible reviewer | Reject review |
| Changes requested without explanation | Reject review |
| Stale approval | Do not count approval |
| Missing status check | Block merge |
| Failed status check | Block merge |
| Unresolved conversation | Block merge |
| Draft Pull Request | Block merge |
| Closed Pull Request | Block merge |
| Base synchronization required | Block merge |
| Prohibited merge strategy | Block merge |

These failures demonstrate that merge eligibility is not equivalent to the presence of a Pull Request or an approval.

## BCNF and Normalization Perspective

Although the executable domain is repository governance, the relational design also illustrates normalization principles.

A relation should avoid storing attributes that depend on only part of a composite identifier or on unrelated entities.

For example, Pull Request information belongs in `pull_requests`, while review decisions belong in `reviews`.

Reviewer information belongs in `users`, rather than being repeated as reviewer names inside every review record.

Branch protection belongs in `branch_protection_policies`, rather than being duplicated across every Pull Request targeting the branch.

Required status checks are separated into `required_status_checks` because a policy can contain multiple required check names.

This decomposition reduces update anomalies.

## BCNF Trade-Offs

Boyce-Codd Normal Form requires every determinant of a non-trivial functional dependency to be a candidate key.

Highly normalized designs can improve integrity by ensuring that facts are stored at their natural dependency level.

The repository model demonstrates this by separating:

`Repository → Branch`

`Pull Request → Review`

`Review → Review Comment`

`Branch Protection Policy → Required Status Check`

A practical system may still introduce carefully controlled denormalization for performance.

For example, a merge-eligibility cache could store the current approval count or latest successful checks. Such derived data creates additional consistency requirements.

The trade-off is therefore:

`Higher normalization → stronger update integrity`

versus:

`Controlled denormalization → potentially faster reads`

The implementation favors normalized source-of-truth data and computes eligibility from those facts.

## Higher Normal Forms

Higher normal forms address increasingly specific dependency structures.

BCNF focuses on functional dependencies and candidate-key determinants.

Fourth Normal Form addresses independent multi-valued dependencies.

Fifth Normal Form addresses decomposition involving join dependencies.

The repository model contains several naturally independent collections. Reviewers, status checks, comments, and required checks should not be stored as repeated combinations in a single wide relation because doing so can create unnecessary duplication and update anomalies.

For example, combining reviewers and required status checks into one wide Pull Request table would create repeated combinations such as:

`Pull Request × Reviewer × Required Check`

Separate relations preserve the independent facts.

## Practical Normalization Trade-Offs

Normalization is not a requirement to split every possible attribute into its own table.

A decomposition should preserve:

- data integrity
- meaningful dependencies
- lossless reconstruction
- manageable query complexity
- acceptable performance

The PostgreSQL implementation therefore uses separate relations where the concepts have independent identities and lifecycle rules.

The application implementations use domain objects that correspond to these conceptual boundaries.

## Distinct Responsibilities

The four governance mechanisms can be separated precisely:

| Mechanism | Question answered |
|---|---|
| Pull Request | What changes are proposed and where should they go? |
| Code Review | What do reviewers think about those changes? |
| Approval | Has an eligible reviewer explicitly accepted the current changeset? |
| Branch Protection | What repository conditions must be satisfied before integration? |

The final merge decision combines their outputs without treating them as the same object.

## End-to-End Workflow

A realistic workflow represented by the implementations is:

`Feature Branch`
→ `Commits`
→ `Pull Request`
→ `Review Requests`
→ `Code Review`
→ `Review Comments`
→ `Approval Decisions`
→ `Status Checks`
→ `Conversation Resolution`
→ `Branch Protection Evaluation`
→ `Merge Eligibility`
→ `Merge`

A change to the Pull Request head can invalidate earlier review and automated-check evidence.

A branch policy can block a fully reviewed Pull Request.

A Pull Request can exist without being mergeable.

An approval can exist without satisfying the current branch policy.

These distinctions are essential for reliable repository governance.

## Limitations

The implementations simulate repository governance rather than integrating with a hosted repository service.

They do not implement:

- Git object storage
- network authentication
- OAuth or SSO
- cryptographic commit verification
- actual merge conflict resolution
- distributed locking across multiple application servers
- webhook delivery guarantees
- repository replication
- external CI execution
- production identity management

The PostgreSQL model provides persistence and transactional enforcement but does not itself execute Git operations.

The source files therefore focus on domain behavior, validation, policy evaluation, and relational integrity.
