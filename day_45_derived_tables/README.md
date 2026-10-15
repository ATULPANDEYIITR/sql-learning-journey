# Derived Tables and Subqueries in FROM

## Concept and purpose

A derived table is a result set produced by a subquery in the `FROM` clause of an SQL statement. The enclosing query treats that result set as a table, assigns it an alias, and selects, filters, joins, or aggregates its rows.

Derived tables are useful when a query needs to separate a calculation or aggregation from the operations that consume its result. For example, a repository analytics query can calculate the total number of changed lines for each pull request in an inner query, then filter those calculated totals in the outer query.

A typical structure is:

    SELECT derived.column_name
    FROM (
        SELECT source_column, expression AS column_name
        FROM source_table
    ) AS derived
    WHERE derived.column_name >= 100;

The inner query establishes the intermediate result set. The outer query operates on the columns exposed by that result set.

## Derived tables versus permanent tables and views

A derived table exists only within the statement that defines it. It does not independently persist rows or require a separate schema object.

A permanent table stores data beyond the lifetime of a query. A view stores a query definition and provides a reusable database interface, but ordinarily does not store its result rows. A common table expression, introduced with `WITH`, provides a named query expression scoped to a statement.

These constructs address different needs:

| Construct | Scope and purpose |
|---|---|
| Derived table | Defines an intermediate result directly inside `FROM`. |
| Common table expression | Names an intermediate query using `WITH`, often improving readability for multi-stage analysis. |
| View | Exposes a reusable query definition to multiple consumers. |
| Temporary table | Materializes intermediate rows in a session or transaction, depending on its configuration. |
| Materialized view | Persists query results and requires a refresh strategy to reflect source changes. |

A derived table is especially useful when an intermediate result is needed once and naming it locally makes the outer query easier to understand.

## Relational workflow for repository analytics

The SQL implementation models repositories, branches, pull requests, review decisions, and automated status checks. Pull-request records contain additions, deletions, changed-file counts, and lifecycle state. Review records capture approval, requested changes, comments, or dismissed decisions. Check records capture pending, passed, or failed validation jobs.

The derived queries build intermediate results for separate analytical purposes:

- **Change metrics:** The inner query calculates `additions + deletions` as `total_changed_lines`. The outer query selects requests above a threshold.
- **Check summaries:** A grouped subquery counts passed, failed, and pending checks for each request before the results are joined to pull-request records.
- **Review summaries:** An inner query aggregates review states by request. The outer query filters for requests with approvals and no active change requests.
- **Basic merge-policy evaluation:** Independently derived review and check summaries are joined to the request data to produce a preliminary eligibility result.

Separating these calculations reduces repeated expressions and makes each stage's purpose explicit.

## Python implementation

The Python script represents pull requests as immutable dataclass instances. `derive_change_metrics` transforms the source records into dictionaries containing calculated change totals, change density, review state, and check state.

The dictionaries act as intermediate result sets. `summarize_by_author` groups those rows and computes per-author totals, while the final filter selects requests meeting both a size threshold and basic merge-eligibility conditions.

The implementation validates change counts before deriving metrics. It treats a request with zero changed files as having zero change density, avoiding division by zero. This is an explicit reporting convention; another application might instead represent the density as unavailable.

The separation between derivation and aggregation makes each function testable independently. It also illustrates a practical distinction: a Python list of dictionaries resembles the output of a query, but it does not provide the relational optimizer, transactional consistency, or database constraints of a real SQL engine.

## JavaScript implementation

The JavaScript program uses array transformations to construct intermediate result sets. `deriveMetrics` maps source pull requests to calculated records. `deriveBranchSummary` groups the derived records by target branch, and `deriveAuthorSummary` groups them by author.

The `loadAndAnalyze` function demonstrates how asynchronous input retrieval can precede a sequence of dependent transformations. Its input loader returns a promise, allowing the analysis to work with data retrieved asynchronously without blocking the JavaScript event loop.

The resulting metrics can be filtered without recalculating source fields. This resembles an outer SQL query consuming a derived table, although JavaScript array operations and SQL query planning have different execution models.

The program validates numeric fields and distinguishes a zero-file request by returning `null` for its lines-per-file metric. This differs intentionally from the Python example's zero-density convention: a zero-file request has no meaningful per-file denominator.

## C++ case study: deployment-change reporting

The C++ program analyzes deployment changes across production and staging environments. It uses separate structures for source records, calculated metrics, and environment-level summaries.

`calculateMetrics` validates change counts and derives the total number of changed lines, average lines per file, and basic merge eligibility. `deriveMetrics` constructs a vector of these intermediate records. `summarizeEnvironments` groups the records using a map keyed by environment.

This design separates source facts from calculated metrics. The final eligibility filter consumes the calculated records rather than repeatedly recomputing line totals from the original deployment data.

The implementation uses standard-library containers and avoids unnecessary dependencies. Deriving metrics requires linear time in the number of source records. Grouping through a map adds logarithmic lookup overhead per record, giving approximately \(O(n \log g)\) grouping time for \(n\) records and \(g\) distinct environments.

The eligibility flag is intentionally basic. A real deployment or repository governance system must consider the complete policy state, including required approvals, dismissed or stale reviews, status-check freshness, protected-branch rules, and concurrent changes to the target branch.

## Java implementation: immutable analytical records

The Java program uses records to model source pull requests, derived change metrics, and branch reports. Records provide compact data carriers with generated accessors and value-oriented behavior.

`deriveMetric` centralizes validation and calculates each request's metrics. `deriveMetrics` uses a stream pipeline to produce a list of derived records. `deriveBranchReports` groups those records by branch, calculates counts and totals, and sorts the final reports.

The implementation uses `Math.addExact` for the line-count calculation. This makes integer overflow explicit rather than silently accepting a wrapped result. Immutable records and `List.copyOf` make the resulting reporting data suitable for read-only analysis.

The model keeps derivation separate from aggregation. That separation allows the branch-reporting method to consume calculated metrics without depending on the original pull-request representation.

The program uses Java 17-compatible records and standard-library collection operations. Its in-memory results illustrate the structure of an analytical pipeline, but database-backed reporting remains preferable when source data must be queried consistently across many repositories or users.

## SQL data model and derived queries

The PostgreSQL script defines five relational tables:

- `repositories` stores repository identity.
- `repository_branches` records branch names and whether they are protected.
- `pull_requests` stores the source branch, target branch, author, change counts, and lifecycle state.
- `pull_request_checks` stores named automated check results.
- `pull_request_reviews` records reviewer decisions and submission times.

Primary keys identify records. Foreign keys preserve repository and pull-request relationships. Unique constraints prevent duplicate repository names, duplicate branch names within a repository, and duplicate check names for a request. Check constraints reject negative change counts and invalid lifecycle or review states.

The index on `(repository_id, state)` supports repository-specific lifecycle filtering. The review index on `(pull_request_id, submitted_at DESC)` supports request-specific review retrieval ordered by submission time.

The script uses PostgreSQL's aggregate `FILTER` clause to count distinct check or review outcomes within one grouped subquery. This is more precise than treating every review or check as equivalent. `COALESCE` handles requests that have no corresponding aggregate row when left joins are used.

The reporting view `pull_request_change_report` exposes reusable change metrics. Unlike the earlier derived tables, the view's definition can be referenced by later statements without repeating the join and calculation.

## Why query boundaries matter

A derived table can make a complex statement easier to reason about by separating intermediate calculations from final filtering. It also provides a local column namespace, which helps avoid ambiguous names when multiple tables expose similarly named fields.

A derived table does not automatically guarantee that the database physically materializes its rows. PostgreSQL may inline or otherwise optimize subqueries when semantics permit. Developers should therefore distinguish the logical intermediate result from a physical temporary storage structure.

The alias after a subquery in `FROM` is required in PostgreSQL. The outer query can reference only the columns exposed by the derived table. If the outer query needs an expression, the inner query must expose that expression as a column.

## Edge cases and correctness

A zero changed-file count makes a per-file ratio undefined. The examples deliberately choose a safe convention for each language: Python returns zero density, JavaScript returns `null`, C++ returns zero, and Java returns zero. These conventions are not mathematically interchangeable. Production reporting should define one domain policy and apply it consistently.

Negative additions, deletions, or file counts are rejected before calculation. PostgreSQL check constraints enforce the corresponding rules at the data layer, where they protect against invalid records regardless of which application writes them.

A derived summary must also distinguish missing data from a genuine count of zero. In SQL, a left join can produce `NULL` for a request without any check or review records. `COALESCE` can convert those missing aggregate values to zero when that interpretation is appropriate.

The sample merge-policy query is not a complete implementation of GitHub branch protection. It does not enforce reviewer eligibility, minimum review counts beyond the demonstrated threshold, stale-approval dismissal, conversation resolution, required linear history, force-push restrictions, deletion restrictions, or administrative bypass policies. Its Boolean result is a reporting estimate rather than an authorization decision.

## Performance and production considerations

Derived tables are most useful when their boundaries clarify calculations or aggregation. They are not automatically faster than equivalent joins, views, or common table expressions. Query performance depends on cardinality, indexes, predicates, statistics, and the database optimizer's selected execution plan.

For large repositories, filter source records as early as semantics permit and aggregate at the level needed by the outer query. Indexes should support demonstrated access patterns rather than be added indiscriminately. Use PostgreSQL's `EXPLAIN` or `EXPLAIN ANALYZE` to inspect plans and measure execution behavior against realistic data volumes.

Repository governance decisions require stronger consistency guarantees than analytical summaries alone. A production merge service should evaluate the current target branch, active reviews, required status checks, and branch protection policy close to the merge operation. A previously computed derived result can become stale as reviews, checks, or branch contents change.

Derived tables provide a clean logical structure for such evaluations, but correctness ultimately depends on defining the policy precisely and ensuring that the data used by the evaluation remains current.












Convert to PDF
