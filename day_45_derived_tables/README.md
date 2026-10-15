# Derived Tables: Subqueries in `FROM` and Intermediate Result Sets

## Scope

A derived table is a result set produced by a subquery in the `FROM` clause and then consumed by an outer query as though it were a table. Its main value is logical decomposition: a complicated query can first produce a well-defined intermediate relation and then let an outer query filter, join, aggregate, or otherwise transform that relation.

This implementation set uses repository governance as the domain. Pull Requests, reviews, approvals, status checks, and protected branches create realistic relational data with several layers of derived information. The central distinction is between the original stored facts and the intermediate relations calculated from those facts.

The six artifacts approach the subject from different technical perspectives:

| Artifact | Primary role |
|---|---|
| Python | Executable data-processing model of intermediate relations and policy evaluation |
| JavaScript | Functional and event-oriented transformation of derived result sets |
| C++ | Repository governance and merge-eligibility case study |
| Java | Enterprise-oriented domain model with explicit intermediate domain types |
| SQL | PostgreSQL relational implementation using derived tables, CTEs, joins, aggregation, constraints, and indexes |
| README | Conceptual and implementation-level explanation of the complete model |

## What a Derived Table Represents

Consider a base relation containing Pull Requests:

```text
pull_request_id | additions | deletions
101             | 340       | 90
102             | 80        | 25
