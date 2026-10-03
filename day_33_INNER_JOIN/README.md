# INNER JOIN

## Scope

An `INNER JOIN` combines rows from two relations when a specified join condition evaluates to true. Its defining property is that unmatched rows are not included in the result.

This topic focuses on three closely related ideas:

- **Join fundamentals** explain what a join does to two relations and why matching rows can produce zero, one, or many output rows.
- **Matching rows** explains how equality and other predicates determine which row combinations survive.
- **Join conditions** define the relationship between the participating relations and can contain one or several predicates.

The three implementations use different perspectives. Python exposes the relational mechanics with reusable join functions and an indexed equality join. JavaScript models the same relational ideas through callbacks, `Map`, validation, and an event-driven workflow. C++ places INNER JOIN behavior inside a repository-governance case study involving repositories, pull requests, developers, branch policies, checks, and reviews.

---

## Core INNER JOIN semantics

Consider two relations:

`repositories`

| repository_id | name |
|---:|---|
| 101 | market-prism |
| 102 | asset-logistics |
| 103 | research-tracker |

and:

`pull_requests`

| pull_request_id | repository_id | title |
|---:|---:|---|
| 501 | 101 | Add risk dashboard |
| 502 | 101 | Fix validation |
| 503 | 999 | Unknown repository |

An equality INNER JOIN using `repository_id` compares:

`repositories.repository_id = pull_requests.repository_id`

The resulting relationship is:

| repository | pull request | title |
|---|---:|---|
| market-prism | 501 | Add risk dashboard |
| market-prism | 502 | Fix validation |

Repository IDs `102` and `103` have no matching pull request, so they do not appear. Pull request `503` references repository `999`, which has no matching repository row, so it also does not appear.

This is the fundamental distinction between an INNER JOIN and an outer join: an INNER JOIN retains only successful matches.

---

## Join conditions

A join condition specifies the rule used to determine whether a left-side row and a right-side row form a valid result combination.

The simplest form is an equality condition:

`left.repository_id = right.repository_id`

A condition can also contain multiple predicates:

`policy.repository_id = pull_request.repository_id AND policy.branch = pull_request.base_branch`

Here the two relations are related only when both attributes agree.

A join condition can also contain a relationship plus a restriction. For example:

`repository.repository_id = deployment.repository_id AND deployment.environment = 'production'`

The first predicate identifies the relationship. The second limits the matching combinations to production deployments.

This distinction matters because a join condition is not merely a textual comparison. It represents the business relationship being modeled between two relations.

---

## Matching rows and cardinality

INNER JOIN does not require the join key to be unique on either side.

Suppose a team relation contains one row for `Platform`, while the developer relation contains three developers assigned to that team. Joining on `team_id` produces three result rows for that team.

If a left relation contains `m` rows with a particular key and the right relation contains `n` rows with that key, the equality join can produce `m × n` combinations for that key.

This is why duplicate keys can cause a result set to grow unexpectedly.

A common mistake is assuming that a join automatically preserves the number of rows from one input. It does not. The output cardinality depends on the number of compatible row pairs.

---

## Equality joins and indexed matching

A direct implementation can test every possible pair:

`for each left row -> for each right row -> test condition`

For `L` left rows and `R` right rows, this requires up to `L × R` condition evaluations.

The Python implementation calls this a nested-loop INNER JOIN. It is valuable for understanding the actual relational operation because every candidate pair is considered explicitly.

For equality conditions, an index can avoid scanning the entire right relation for every left row.

The Python and JavaScript implementations build an index keyed by the right-side join attribute. The C++ implementation uses `std::unordered_multimap`.

The conceptual workflow is:

- Build an index from right-side key to matching right-side rows.
- Read one left-side row.
- Extract its join key.
- Look up that key in the index.
- Emit one result for every matching right-side row.

For equality joins this is approximately `O(L + R + M)`, where `M` is the number of generated result rows, subject to hash-table behavior and implementation details.

The important qualification is that the output itself can be large. A fast lookup does not make a many-to-many relationship cheap if millions of matching pairs must still be constructed.

---

## Composite join conditions

Some relationships require more than one attribute.

The C++ case study contains branch policies identified by:

`repository_id + branch_name`

A pull request targeting `main` in repository `301` should match the policy for repository `301` and branch `main`, but not a policy for repository `301` and branch `develop`.

The effective condition is:

`policy.repository_id = pull_request.repository_id AND policy.branch_name = pull_request.base_branch`

This is different from joining on `repository_id` alone. A repository can legitimately have several branch-specific policy rows.

Composite conditions are useful when one attribute identifies a broader entity while another identifies the specific relationship within that entity.

---

## Join condition versus filtering

The Python implementation deliberately separates relationship matching from filtering.

The relationship can be established with:

`repository.repository_id = pull_request.repository_id`

A subsequent filter can restrict the result to:

`pull_request.state = 'open'`

Conceptually:

`FROM repositories AS r INNER JOIN pull_requests AS pr ON r.repository_id = pr.repository_id WHERE pr.state = 'open'`

The distinction improves reasoning and diagnostics.

The `ON` condition describes which rows belong together. A later `WHERE` condition determines which already-related results should remain in the query result.

For INNER JOINs, some predicates can sometimes be moved between `ON` and `WHERE` without changing the final result, but the two clauses communicate different intent and become materially different when outer joins are involved.

---

## Joining more than two relations

An INNER JOIN can be composed into a chain.

The Python implementation uses:

`repositories -> pull_requests -> developers`

The first relationship is:

`repository.repository_id = pull_request.repository_id`

The second is:

`pull_request.author_id = developer.developer_id`

A pull request therefore appears in the final result only if both relationships succeed.

This creates an important property: every additional INNER JOIN can remove rows that fail the new relationship.

In the example, a pull request can have a valid repository but still disappear from the final three-relation result because its author ID does not match any developer.

The C++ case study uses this behavior deliberately when constructing a governance dataset.

---

## Python implementation

The Python file provides a reusable relational model rather than connecting to a database.

### General nested-loop implementation

`inner_join()` accepts two collections and a callable join condition.

The callback receives a left row and a right row and returns a Boolean value. A result row is created only when the callback returns `True`.

This makes the function capable of expressing:

- equality relationships,
- multiple predicates,
- environment restrictions,
- branch-specific matching,
- and other row-to-row conditions.

The implementation prefixes columns with `left.` and `right.` to avoid collisions when both relations contain a column with the same name.

### Indexed equality implementation

`equality_inner_join()` builds a dictionary whose values are lists of right-side rows.

The list is important. A normal dictionary value containing only one row would incorrectly discard duplicate right-side keys.

For example, if two right-side records have `repository_id = 101`, both must be available to every compatible left-side record.

### Validation

The Python implementation checks that required join columns exist before performing an equality join.

Missing columns produce a `ValueError` rather than silently generating incorrect output.

This is particularly useful when relational data comes from CSV files, JSON documents, APIs, or dynamically constructed dictionaries where schema mistakes might otherwise remain hidden.

### Projection and filtering

`select_columns()` demonstrates projection after the join. It chooses the fields needed by the final result.

`filter_rows()` represents a later selection operation.

Keeping projection, filtering, and joining as separate functions makes the relational stages easier to inspect and test.

### Nullable values

The Python example explicitly points out an important SQL distinction.

Python's `None == None` evaluates to `True`.

SQL's `NULL = NULL` does not evaluate to `TRUE`; SQL uses three-valued logic, where comparisons involving an unknown `NULL` value can produce `UNKNOWN`.

Therefore a Python simulation must not be assumed to have identical semantics to a SQL database merely because both implementations use equality syntax.

---

## JavaScript implementation

The JavaScript file uses arrays of objects as relations.

### Callback-based join conditions

`innerJoin()` accepts a JavaScript function as the relationship predicate.

For example, the callback can express:

`repository.repositoryId === deployment.repositoryId && deployment.environment === "production"`

This demonstrates a JavaScript-specific strength: the relationship rule is passed as executable behavior.

The same join engine can therefore support different relationship conditions without creating separate join functions for every scenario.

### Map-based equality join

`equalityInnerJoin()` uses JavaScript's `Map`.

The right relation is indexed by the join key, and each key maps to an array of matching rows.

The use of an array per key is essential for correct duplicate-key behavior.

### Validation and runtime errors

The JavaScript implementation checks that relations are arrays, that rows are objects, and that required join columns exist.

Errors are propagated to the asynchronous `main()` function and ultimately produce a non-zero process exit code.

This models a useful production principle: invalid relational input should be observable rather than converted into silently incomplete results.

### Event-driven demonstration

The program also demonstrates an event-driven representation of a completed join.

A small event registry emits `join-complete` after the asynchronous microtask executes the join.

This is not required for the mathematical definition of INNER JOIN. It demonstrates how a join operation can fit into JavaScript's event-oriented execution model when its output triggers later processing.

### SQL-style nullable comparison

JavaScript normally evaluates `null === null` as `true`.

The example therefore provides `sqlLikeEquality()` to demonstrate SQL-style nullable equality for the specific teaching case. It refuses to treat two `null` values as a successful join condition.

This distinction prevents a common error when translating SQL reasoning directly into JavaScript.

---

## C++ repository-governance case study

The C++ program models a repository-management system in which pull requests reference repositories and developers.

The principal relations are:

| Relation | Important attributes |
|---|---|
| `Repository` | `repositoryId`, `name`, `owner` |
| `PullRequest` | `pullRequestId`, `repositoryId`, `authorId`, `title`, `state` |
| `Developer` | `developerId`, `username`, `team` |
| `BranchPolicy` | `repositoryId`, `branchName`, policy requirements |
| `StatusCheck` | `pullRequestId`, check name, pass state |
| `Review` | `pullRequestId`, reviewer ID, review state |

The primary INNER JOIN relationships are:

`Repository.repositoryId = PullRequest.repositoryId`

and:

`PullRequest.authorId = Developer.developerId`

The resulting `GovernanceRecord` exists only when both relationships can be resolved.

### Why the case study uses two different join implementations

`equalityInnerJoin()` uses `std::unordered_multimap` and is appropriate for a direct equality relationship.

The multimap preserves duplicate keys. If several right-side rows share the same key, all are returned.

`nestedLoopInnerJoin()` accepts an arbitrary predicate. It is used for composite conditions where both repository and branch must match.

This distinction mirrors a practical database concern: equality relationships are particularly suitable for indexed or hash-based access, while arbitrary predicates can require broader evaluation strategies.

### Branch policy relationship

A branch policy is identified by both repository and branch.

The program therefore searches for a policy where:

`policy.repositoryId == pullRequest.repositoryId`

and:

`policy.branchName == targetBranch`

A policy for the same repository but a different branch is not a valid match.

### Governance checks after relationship matching

The program intentionally separates INNER JOIN semantics from merge-policy evaluation.

The join answers whether the pull request has corresponding repository and developer records.

The governance engine then checks:

- whether a matching branch policy exists,
- whether recorded required checks pass,
- whether enough eligible reviewers have active approvals.

This separation makes failures diagnosable. A missing author is a relationship problem, while a failed security scan is a status-check problem.

### Approval counting

The approval evaluator counts distinct eligible reviewers.

A review is counted only when:

- it belongs to the current pull request,
- its state is `APPROVED`,
- it has not been dismissed,
- and its reviewer belongs to the eligible reviewer set.

An `unordered_set` prevents multiple records from the same reviewer from inflating the approval count.

This logic is downstream from the INNER JOIN itself. The join identifies related records; the approval rule evaluates their business meaning.

---

## Failure and edge cases

### No matching row

An INNER JOIN returns no result for a row when no row on the other side satisfies the join condition.

This is expected behavior rather than an exception.

### Duplicate keys

Duplicate keys can produce multiple result rows. This is not automatically an error.

The application must understand whether the underlying relationship is:

- one-to-one,
- one-to-many,
- or many-to-many.

Unexpected row multiplication often indicates either a misunderstood relationship or a missing predicate.

### Missing join attributes

A missing join attribute is different from a legitimate non-match.

The Python and JavaScript implementations treat a missing required join field as invalid input. A row containing a valid field value that has no counterpart is simply unmatched and therefore excluded.

### Nullable values

`NULL` requires special handling in SQL because it represents an unknown value.

A condition such as `a.key = b.key` does not consider two SQL `NULL` values equal.

Applications that need NULL-safe matching must explicitly choose the desired semantics rather than assuming ordinary equality is sufficient.

### Composite keys

Joining on only part of a composite relationship can create false matches.

For example, matching branch policies only by repository ID could associate a pull request targeting `develop` with the policy intended for `main`.

### Empty relations

If either side of an INNER JOIN is empty, the result is empty.

There is no unmatched-row preservation behavior in an INNER JOIN.

### Large output cardinality

Even an indexed join can become expensive when a key has many duplicates. Index lookup can be efficient while result construction remains expensive because every valid pair must still be produced.

---

## Common mistakes

### Joining on the wrong attribute

A join should use attributes that represent an actual relationship.

Matching `repository.name` to `developer.username` because both happen to be strings is not meaningful merely because the data types are compatible.

### Assuming key uniqueness

A column being called `id` does not guarantee uniqueness in every in-memory dataset or every relational design.

The expected cardinality should come from the data model and constraints, not from the column name.

### Forgetting qualification

When both relations contain a column named `id`, `name`, or `state`, an unqualified reference can be ambiguous.

The implementations qualify joined fields with prefixes to make the source explicit.

### Treating a join as filtering

An INNER JOIN establishes row relationships. Filtering is a separate operation.

Combining the concepts mentally can make it difficult to understand why rows disappeared from a query.

### Ignoring data quality

A missing foreign-key-like reference can cause an INNER JOIN to silently remove a record from the result.

For analytical queries this may be acceptable. For data-quality auditing it can hide the very records that need investigation. In such cases, an outer join or an explicit anti-join-style diagnostic query may be more appropriate.

---

## Performance considerations

A nested-loop implementation has worst-case complexity of `O(L × R)` candidate comparisons.

An equality join backed by a hash index is approximately `O(L + R + M)`, where `M` is the number of emitted matching pairs, assuming average constant-time hash operations.

Actual database systems can choose among several execution strategies, including nested-loop joins, hash joins, merge joins, and index-assisted plans.

The selected strategy depends on factors such as:

- estimated relation sizes,
- available indexes,
- key distribution,
- sortedness,
- memory,
- predicate selectivity,
- expected output cardinality,
- and database optimizer statistics.

An index is not automatically beneficial for every query. Indexes consume storage and introduce maintenance work during inserts, updates, and deletes.

The most important performance consideration is often cardinality. A relationship that unexpectedly becomes many-to-many can produce a huge intermediate result even when individual key lookups are fast.

---

## Practical SQL form

A typical equality INNER JOIN can be expressed as:

`SELECT r.name, pr.pull_request_id, pr.title FROM repositories AS r INNER JOIN pull_requests AS pr ON r.repository_id = pr.repository_id;`

Adding a result restriction can produce:

`SELECT r.name, pr.pull_request_id, pr.title FROM repositories AS r INNER JOIN pull_requests AS pr ON r.repository_id = pr.repository_id WHERE pr.state = 'open';`

A composite relationship can be expressed as:

`SELECT pr.pull_request_id, p.required_reviews FROM pull_requests AS pr INNER JOIN branch_policies AS p ON p.repository_id = pr.repository_id AND p.branch_name = pr.base_branch;`

These examples show the central separation:

`INNER JOIN` determines matching row combinations, while the join condition precisely defines what constitutes a match.

---

## Relationship between the three implementations

The implementations intentionally do not reproduce one another line by line.

| Implementation | Primary technical perspective |
|---|---|
| Python | General relational mechanics, validation, hash-indexed equality joins, filtering, and executable assertions |
| JavaScript | Callback-based predicates, `Map` indexing, runtime validation, nullable comparison, and event-driven processing |
| C++ | Repository-governance case study, generic typed joins, composite policy matching, approval evaluation, and performance-oriented data structures |

All three implement the same relational principle:

> A result row exists only when the selected left-side and right-side rows satisfy the INNER JOIN condition.

The surrounding architecture differs because the purpose of each implementation is different. The Python program makes the relational operation explicit, the JavaScript program demonstrates how the operation fits naturally into a dynamic event-oriented language, and the C++ program embeds the join inside a typed system with a realistic governance workflow.
