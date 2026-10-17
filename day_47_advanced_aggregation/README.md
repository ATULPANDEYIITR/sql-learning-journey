# Advanced Aggregation

Advanced aggregation is the process of deriving several meaningful measures from a collection of records while preserving the distinction between the population being measured, the grouping dimensions, and the conditions applied to individual records.

This artifact treats aggregation as an engineering problem rather than as a collection of isolated `sum`, `count`, or `average` examples. The implementations model repository-development activity so that aggregation can answer questions such as:

- How many Pull Requests belong to each repository?
- How much code changed in each repository?
- How many changes were merged, left open, or closed?
- Which changes were security-related?
- How frequently did large changes occur?
- How much of the review population received approvals?
- Which repositories satisfy aggregate governance thresholds?

The central distinction is between **multiple aggregation**, **conditional aggregation**, and **aggregation strategy**.

## Conceptual Model

A raw record contains attributes describing one event. An aggregate compresses many such records into measurements that support analysis or decisions.

For a collection of Pull Requests, the following relationship is useful:

`raw Pull Requests -> filtering conditions -> grouping dimensions -> aggregate measures -> policy or analytical decision`

The grouping dimension determines which records belong together. The aggregate function determines what is calculated for each group.

For example, repository-level aggregation can calculate:

`COUNT(Pull Requests)`

`COUNT(merged Pull Requests)`

`SUM(additions + deletions)`

`AVG(additions + deletions)`

`MIN(additions + deletions)`

`MAX(additions + deletions)`

These measures describe different properties of the same grouped population. They should not be confused with conditional aggregation, where an aggregate is calculated only for records satisfying a specific predicate.

## Multiple Aggregations

Multiple aggregation means calculating several measures for the same grouping population.

Consider the repository `platform-api`. A single grouped operation can produce its Pull Request count, merged count, open count, total changed lines, average change size, and failed-check count.

The measures answer different questions:

| Measure | Interpretation |
| --- | --- |
| `COUNT` | How many Pull Requests are represented? |
| `SUM` | How much total code changed? |
| `AVG` | What is the typical change size? |
| `MIN` | What was the smallest change? |
| `MAX` | What was the largest change? |

A common analytical mistake is to calculate an average over the wrong population. An average of all Pull Requests is different from an average of only merged Pull Requests. The filtering decision therefore has to be explicit.

## Conditional Aggregation

Conditional aggregation evaluates an aggregate over a subset of records without necessarily discarding the other records from the surrounding group.

For example, repository reporting can contain all of these measures simultaneously:

`COUNT(*)`

`COUNT(*) FILTER (WHERE state = 'merged')`

`COUNT(*) FILTER (WHERE category = 'security')`

`COUNT(*) FILTER (WHERE additions + deletions >= 500)`

The result is one repository row containing several independently defined measurements.

The SQL implementation uses PostgreSQL's `FILTER` clause because it expresses conditional aggregation directly. This is different from placing the condition in a `WHERE` clause.

A `WHERE` condition changes the rows entering the entire aggregation.

A conditional aggregate changes only the population used by that particular measure.

That distinction matters when a report needs both total Pull Requests and security Pull Requests in the same result.

The Python and JavaScript implementations express the same conceptual distinction through predicates applied inside accumulator logic. The Java implementation uses stream filtering for separate conditional measures. The C++ case study maintains several conditional counters in a single aggregation pass.

## Filtering Before and After Aggregation

There are two fundamentally different operations.

Filtering raw records before grouping answers a question about which records should participate in the aggregation.

Filtering an aggregate after grouping answers a question about which groups satisfy a calculated condition.

For example:

`WHERE state = 'merged'`

selects individual Pull Requests before aggregation.

A condition such as:

`SUM(additions + deletions) > 1000`

evaluates a property of an already formed group.

This distinction corresponds to the difference between row-level predicates and group-level predicates. In SQL, the former normally belongs in `WHERE`, while aggregate-based group filtering normally belongs in `HAVING`.

The Python implementation demonstrates the same distinction through completed-only aggregation and post-aggregation customer threshold evaluation.

## Aggregation Dimensions

Aggregation is not limited to one grouping field.

A repository grouping produces repository-level measures.

A category grouping produces feature, bugfix, security, and performance measures.

A compound grouping such as:

`category, state`

creates separate populations such as:

`security + merged`

`security + open`

`bugfix + merged`

This changes the granularity of the result. Choosing the grouping dimension is therefore an analytical decision rather than merely a syntactic operation.

The SQL implementation also demonstrates `GROUPING SETS`, which can calculate detailed repository results and a grand total in the same query.

## Python Implementation

The Python program models transaction-style operational records with multiple dimensions including region, category, status, customer, amount, and timestamp.

The `aggregate_by_region` function maintains several measures in a dictionary accumulator. A single pass updates count, total, minimum, and maximum. The average is derived after the grouped totals are known.

`conditional_aggregation_by_region` keeps completed, failed, and refunded measures separate. This prevents completed revenue from being confused with failed or refunded transaction volume.

`aggregate_by_category_and_status` uses a compound tuple key. This represents the same conceptual structure as SQL grouping by multiple columns.

`aggregate_customers` demonstrates a richer accumulator. It simultaneously tracks total transactions, total amount, successful amount, failed amount, successful count, and failed count. Derived values such as success rate and average transaction size are exposed as properties.

The percentile implementation demonstrates a more advanced form of aggregation where the result is not simply a sum or count. Percentiles require ordering and interpolation, which makes them materially different from ordinary additive aggregates.

The strategy selector distinguishes between hash-style grouping and ordered processing. Dictionary-based grouping is appropriate when direct key lookup is more important than sorted output. Ordered grouping becomes useful when deterministic ordering or ordered downstream processing is required.

The script also validates duplicate identifiers, negative amounts, invalid statuses, and invalid categories before aggregation.

## JavaScript Implementation

The JavaScript implementation models Pull Request activity and uses `Map` as the primary grouping structure.

`aggregateBy` accepts a key-selection function. This allows the same aggregation engine to group by repository or team without duplicating the accumulator mechanism.

The accumulator maintains:

- total records
- merged records
- open records
- closed records
- approved records
- failed checks
- additions
- deletions
- review-coverage information

`conditionalAggregation` intentionally evaluates multiple independent predicates against the same record collection. It can identify security changes, large changes, merged changes with passing checks, open changes lacking enough approvals, and failed checks.

The `AggregationEngine` separates validation, grouping, conditional metrics, and governance evaluation. This makes the aggregate results reusable by the policy layer.

The asynchronous event-processing function provides a complementary view of aggregation. A production event-driven system may receive records continuously instead of receiving a complete dataset in one batch. Maintaining an accumulator as events arrive avoids repeatedly rebuilding the entire aggregate.

The JavaScript strategy decision therefore recognizes both batch aggregation and incremental aggregation.

## C++ Case Study

The C++ program implements a repository governance and merge-eligibility engine.

Each Pull Request contains repository, team, category, state, additions, deletions, reviewer count, approval count, and status-check information.

The `Aggregate` structure is deliberately broader than a single metric. It stores state counts, changed-line totals, approval coverage, and failed-check counts.

The generic `groupBy` function accepts a key function. This supports repository and category aggregation while keeping the accumulator implementation shared.

The conditional metrics engine separately calculates security changes, large changes, merged changes with passing checks, open changes without enough approvals, and merged additions associated with passing checks.

The governance layer consumes aggregate results instead of raw Pull Requests. A repository is considered eligible only when its aggregate metrics satisfy minimum merged-change, approval-coverage, and check-pass-rate thresholds.

This separation is important architecturally. Aggregation creates evidence about repository activity. Governance logic interprets that evidence according to policy.

The implementation uses `std::map` so grouped output is deterministic. A hash-based `std::unordered_map` would usually offer expected constant-time key lookup when ordering is not required.

## Java Enterprise-Oriented Model

The Java implementation uses records for immutable domain objects and enumerations for Pull Request states and change categories.

The `PullRequest` record performs constructor-level validation so invalid domain objects cannot be created silently. Its `approvalCoverage` method defines a domain calculation directly on the record.

`RepositoryMetrics` represents an immutable aggregate result. It provides derived measures such as merge rate, check pass rate, and average changed-line count.

The aggregation methods use Java Streams and collectors. `groupingBy` creates the repository or category partitions, while `collectingAndThen` converts each partition into the immutable `RepositoryMetrics` value.

An `EnumMap` is used for category and state dimensions because the keys are enum values. This is more precise than representing known domain states as arbitrary strings.

The governance service evaluates aggregate repository metrics against a `GovernancePolicy`. It distinguishes insufficient merged changes, insufficient approval coverage, and insufficient check health rather than returning a single generic failure.

This makes the aggregation result usable as a domain input rather than merely as formatted reporting data.

## SQL Data Model

The PostgreSQL implementation models a repository governance environment with separate relations for:

- repositories
- branches
- Pull Requests
- reviewers
- reviews
- review comments
- status checks
- branch protection policies

Foreign keys preserve relationships between those entities.

Check constraints prevent invalid values such as negative additions or deletions and approvals exceeding the number of reviewers.

Indexes target recurring access paths such as repository/state lookups, Pull Request categories, review states, status-check relationships, and unresolved review comments.

The schema therefore keeps raw operational facts separate from derived aggregate results.

## SQL Multiple Aggregation

The `repository_aggregation` view calculates several measures per repository in one grouped query.

It combines:

`COUNT`

`COUNT ... FILTER`

`SUM`

`AVG`

`MIN`

`MAX`

This gives one analytical row per repository without requiring separate queries for each measure.

The category query changes the grouping dimension. The resulting measures answer category-level questions rather than repository-level questions.

## SQL Conditional Aggregation

PostgreSQL's `FILTER` syntax makes the conditional population explicit.

For example:

`COUNT(*) FILTER (WHERE state = 'merged')`

counts only merged Pull Requests while leaving the total Pull Request population available to another aggregate in the same result.

Security-specific aggregation uses conditions on both category and state. Large-change aggregation uses a derived expression:

`additions + deletions >= 500`

This is more meaningful than merely counting all Pull Requests because it identifies the subset that crosses a change-size threshold.

## Review and Approval Aggregation

The review aggregation separates review events from Pull Request records.

A Pull Request may have several review events. Therefore, joining Pull Requests directly to reviews can change row cardinality and can cause unrelated aggregates to be multiplied if several one-to-many relationships are joined at once.

The SQL script avoids this problem in the merge-eligibility query by aggregating review counts and status-check counts separately in CTEs before joining those results to the Pull Request.

This is an important aggregation design rule: when several independent one-to-many relationships are joined together, aggregate each relationship at the appropriate grain before combining them.

## Branch Protection and Aggregate Policy Evaluation

Branch protection policies define required approvals, required status checks, direct-push restrictions, force-push restrictions, linear-history requirements, and conversation-resolution requirements.

The policy itself is not an aggregate. Aggregation supplies the evidence needed to evaluate the policy.

For example:

`approval count >= required approvals`

is an aggregate-derived condition.

Likewise, determining whether every status check passed requires examining the collection of checks associated with a Pull Request.

The final policy query combines these measurements into a boolean `satisfies_protection_policy` result.

This preserves the distinction between raw review events, aggregate measurements, and governance decisions.

## Aggregation Strategies

Aggregation strategy determines how the system organizes records while calculating grouped results.

A hash aggregation stores an accumulator for each grouping key. Expected lookup cost is typically constant time, making this attractive when the number of groups is manageable and ordered output is not required.

A sort-based strategy orders records by grouping key first. Once records are ordered, consecutive records belonging to the same group can be processed together. Sorting introduces an `O(n log n)` component but can be useful when ordered output or other ordered processing is already required.

A streaming or incremental strategy updates an existing accumulator as records arrive. This is particularly useful for event-driven systems because the application does not need to repeatedly scan historical records to rebuild every metric.

The correct strategy depends on data volume, cardinality, memory constraints, ordering requirements, update frequency, and downstream operations.

## Performance Considerations

For a dataset with `n` records and `g` groups, hash-based grouping generally requires `O(n)` expected processing time and approximately `O(g)` additional accumulator storage.

Sorting-based grouping generally requires `O(n log n)` time for the sorting phase and storage appropriate to the sorting implementation.

Multiple measures should usually be accumulated together when they share the same grouping population. Repeatedly scanning the same records for every metric can increase CPU cost unnecessarily.

The SQL planner may choose hash aggregation, sort-based aggregation, parallel aggregation, or another execution strategy depending on statistics, indexes, available memory, query shape, and PostgreSQL configuration.

An index does not automatically make an aggregate fast. Index usefulness depends on filtering, grouping, cardinality, table size, and whether the query can avoid reading a large proportion of the base table.

## Cardinality and Correctness

Aggregation correctness depends heavily on row grain.

A Pull Request has one row in the Pull Request table, while a Pull Request can have many reviews and many status checks.

Joining those child tables directly can produce a multiplicative row count. For example, three reviews combined with two status checks can create six joined rows for one Pull Request.

If a query then calculates `SUM(additions)`, the Pull Request's additions can be counted six times.

Pre-aggregation through CTEs or derived tables prevents this multiplication.

This issue is more fundamental than choosing `COUNT` versus `SUM`. The aggregate function can be mathematically correct while the input relation has already been transformed into an incorrect grain.

## Edge Cases

Empty groups must not produce misleading averages. The implementations guard against division by zero.

A group containing no records has no meaningful average or success rate. SQL uses `NULLIF` where division could otherwise produce a division-by-zero error.

A reviewer count of zero makes approval coverage undefined rather than automatically equivalent to complete approval.

A failed status check must not be treated as equivalent to a missing status check. These are different operational states and may require different policy treatment.

Dismissed reviews also require separate handling. A historical approval event does not necessarily mean that an approval is currently valid for merge eligibility.

Large-change thresholds are another example of a conditional boundary. A threshold such as `>= 500` has different semantics from `> 500`, so the boundary must be deliberately defined.

## Common Aggregation Errors

A frequent error is applying a row-level filter when the requirement is to retain the complete population and calculate a conditional metric beside it.

Another error is calculating an average after joining a one-to-many relation without restoring the intended grain.

A third error is mixing additive and non-additive measures. Counts and sums can often be safely combined across partitions, while averages require their underlying counts and sums if they are to be recomputed correctly.

For example, averaging two subgroup averages without weighting them by subgroup size can produce an incorrect overall average.

A fourth error is treating a derived ratio as if it were directly additive. Approval coverage and merge rate should generally be recomputed from their numerators and denominators rather than summed across groups.

## Security and Governance Considerations

Aggregated metrics can influence governance decisions, so the source records and aggregation definitions need to be auditable.

A repository reporting system should distinguish raw review events from derived approval counts. This prevents an aggregate report from becoming the authoritative record of an event that should instead remain traceable to its source.

Sensitive operational information should also be exposed according to authorization rules. Aggregate metrics can reveal engineering activity, review behavior, security workload, and team-level operational patterns even when individual comments are hidden.

Policy thresholds should be explicit and versioned when they affect merge eligibility. A result such as `eligible = true` is meaningful only when the policy used to produce that result is known.

## Practical Interpretation

The implementations deliberately use the same conceptual domain from different technical perspectives.

Python emphasizes explicit accumulators, validation, conditional calculations, distribution statistics, and strategy selection.

JavaScript emphasizes reusable grouping functions, event-driven incremental aggregation, `Map`-based accumulators, and policy evaluation.

C++ models a performance-oriented governance engine where aggregation feeds a repository-level decision process.

Java models immutable enterprise domain types, stream collectors, enum-aware grouping, and explicit policy decisions.

PostgreSQL represents aggregation at the relational layer, where grouping, conditional measures, relational cardinality, constraints, indexes, transactions, and policy queries operate together.

The important design boundary is that aggregation is not merely the act of calculating a number. It is the controlled transformation of records at a defined grain into measurements whose semantics are precise enough to support analysis and operational decisions.
