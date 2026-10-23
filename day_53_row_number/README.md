# Ranking Rows, Deduplication, and Top-N Problems

## Scope

This project develops a practical model for three closely related analytical problems:

- assigning deterministic positions to rows,
- removing duplicate business records while selecting the preferred row,
- retrieving the highest or lowest N rows globally or within groups.

The central distinction is between **row identity**, **ranking position**, **business uniqueness**, and **group-relative selection**.

The five implementations use the same repository-development style dataset of customers, products, categories, and sales, but each implementation emphasizes a different technical mechanism.

| File | Primary perspective | Main implementation |
|---|---|---|
| Python | Analytical simulation | Partitioning, sorting, deterministic row numbering, dictionary-based deduplication |
| JavaScript | Event-driven processing | Classes, validation events, asynchronous entry point, policy-style analysis |
| C++17 | Algorithmic engine | Explicit data structures, partitioning, hash-based deduplication, sorting |
| Java 17 | Enterprise domain model | Records, interfaces, enums, immutable results, validation and ranking policies |
| PostgreSQL | Relational analytics | Window functions, CTEs, views, constraints, indexes, and transactions |

## Core Analytical Model

A ranking operation normally has four components:

    Source rows
        |
        +-- Partition key
        |
        +-- Ordering expression
        |
        +-- Ranking function
        |
        +-- Selection condition
        |
        v
    Ranked result

For example, a query that ranks sales by customer partitions the data by `customer_id` and orders each partition by `sale_amount DESC`.

A deterministic ordering also includes a unique tie-breaker such as `sale_id`.

Without a tie-breaker, two rows having the same amount are equivalent under the declared ordering. Their relative order can change when execution plans, input order, or physical storage change.

## ROW_NUMBER

`ROW_NUMBER()` assigns a distinct sequential number to every row inside its partition.

For a customer with three sales:

| Sale | Amount | ROW_NUMBER |
|---:|---:|---:|
| 3 | 1250.00 | 1 |
| 1 | 1200.00 | 2 |
| 2 | 800.00 | 3 |

The ranking is unique even when amounts are equal.

This makes `ROW_NUMBER` appropriate for:

- selecting one preferred record from duplicates,
- retrieving exactly one latest record per entity,
- retrieving exactly N rows from each group,
- creating deterministic pagination positions,
- selecting the first record according to a business-defined ordering.

The SQL implementation uses:

`ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`

The Python, JavaScript, C++, and Java implementations reproduce the same partition-and-sort behavior through native collections and sorting operations.

## Ranking Is Not Deduplication

Ranking does not automatically remove rows.

Suppose two records represent the same customer and product:

| Customer | Product | Amount |
|---:|---|---:|
| 101 | LAPTOP | 1200 |
| 101 | LAPTOP | 1250 |

The two rows may be legitimate historical transactions. `ROW_NUMBER` merely establishes an order.

Deduplication introduces a separate business rule:

> For each `(customer_id, product_id)` key, retain the highest-value record.

The Python implementation uses a dictionary keyed by the business identity. The JavaScript implementation uses a `Map`. C++ uses an `unordered_map`, and Java uses `Map.merge`.

The PostgreSQL implementation uses a window partition:

`PARTITION BY customer_id, product_id`

and retains the row whose duplicate position is `1`.

The choice of retained row is itself important. A production system should define whether the preferred row is:

- the newest record,
- the highest amount,
- the earliest authoritative record,
- the record with the strongest status,
- or another business-defined winner.

A ranking expression must reflect that rule explicitly.

## ROW_NUMBER Versus RANK and DENSE_RANK

The SQL implementation provides a direct comparison of three ranking functions.

Consider values:

| Amount | ROW_NUMBER | RANK | DENSE_RANK |
|---:|---:|---:|---:|
| 1000 | 1 | 1 | 1 |
| 900 | 2 | 2 | 2 |
| 900 | 3 | 2 | 2 |
| 800 | 4 | 4 | 3 |

`ROW_NUMBER` assigns every row a different position.

`RANK` gives equal values the same rank and leaves gaps after ties.

`DENSE_RANK` gives equal values the same rank without leaving gaps.

This distinction matters for top-N requirements.

If the requirement is:

> Return exactly two rows per category.

`ROW_NUMBER <= 2` is appropriate.

If the requirement is:

> Return everyone whose score is among the top two distinct scores.

`DENSE_RANK <= 2` is usually more appropriate.

The two requirements can return different numbers of rows.

## Top-N Globally

A global top-N problem ranks the complete dataset:

    All sales
        |
        v
    ORDER BY amount DESC
        |
        v
    First N rows

The implementations use `sale_id` as a secondary ordering key so that ties are deterministic.

The global query in PostgreSQL creates a CTE containing a global `ROW_NUMBER` and then filters that result.

The application implementations sort a copy of the source collection and retain the first N elements.

This distinction is important because global top-N and group-relative top-N answer different questions.

## Top-N Per Group

A top-N-per-group query first creates independent partitions.

For categories:

    Electronics
        -> ordered sales
        -> first N

    Furniture
        -> ordered sales
        -> first N

The PostgreSQL implementation uses:

`PARTITION BY p.category`

and then filters on the generated row number.

The application implementations build category partitions before sorting them.

This pattern is useful for questions such as:

- top three products per category,
- highest-value transaction per customer,
- latest two events per account,
- top five employees per department,
- highest-ranked records per region.

## Python Implementation

The Python program treats the analytical workflow as an in-memory data-processing system.

`Sale` is a frozen dataclass, which prevents accidental mutation after records enter the analysis.

`validate_sales()` verifies:

- positive identifiers,
- unique sale identifiers,
- non-empty business keys,
- non-negative amounts.

`row_number_by_customer()` creates customer partitions with `defaultdict(list)`, sorts each partition, and assigns positions.

`deduplicate_latest_product()` uses a dictionary whose key is `(customer_id, product_id)`. The record with the greater amount is retained, with `sale_id` resolving equal amounts.

`top_n_per_category()` applies the same partition-and-order concept to categories.

The implementation also exposes the distinction between `ROW_NUMBER` and `DENSE_RANK` through a compact ranking function.

The main performance characteristics are:

| Operation | Typical complexity |
|---|---|
| Validation | O(n) |
| Dictionary deduplication | Expected O(n) |
| Partitioned sorting | O(Σ k log k) |
| Global sorting | O(n log n) |

For very large datasets, database-side window functions or specialized top-N algorithms may be preferable to loading every row into application memory.

## JavaScript Implementation

The JavaScript implementation models ranking as an event-driven analysis pipeline.

`AnalysisPipeline` owns the input collection and exposes event listeners for:

- validation completion,
- ranking completion,
- deduplication completion.

This separates computation from operational observation.

JavaScript `Map` objects provide natural support for partitions and business-key deduplication.

The top-N methods validate the requested N before processing. Invalid values, malformed identifiers, empty keys, and non-finite amounts are rejected.

The asynchronous `run()` entry point allows the same analytical service to be integrated into a larger Node.js event-driven workflow without introducing external dependencies.

The implementation deliberately uses deterministic secondary ordering by `saleId`.

That is important when JavaScript sorting receives rows with equal amounts because the analytical requirement is not simply "sort by amount"; it is "produce a stable, reproducible ranking."

## C++17 Implementation

The C++ implementation presents the problem as a strongly typed analytical engine.

`Sale` contains the immutable conceptual fields required by the scenario.

`GovernanceAnalytics` validates the dataset during construction, preventing the object from operating on structurally invalid input.

Customer partitions use `std::map`, which provides ordered partition keys.

Deduplication uses `std::unordered_map`, providing expected constant-time key lookup.

Sorting uses explicit comparator functions:

    amount descending
            |
            v
    sale_id ascending

The secondary comparison is not cosmetic. It makes equal-valued rows deterministic.

The class also uses exceptions for invalid N values and malformed source records.

C++ is particularly useful for demonstrating the memory and algorithmic cost of the workflow because the implementation exposes the actual containers used for partitions and lookup.

## Java 17 Implementation

The Java implementation models ranking as an enterprise-oriented service.

The `Sale` record provides a compact immutable domain representation.

`RankedSale` separates the original domain record from its analytical position.

`RankingPolicy` represents the ordering decision explicitly rather than hiding it in a comparator scattered through the program.

`RankingService` defines the service contract, while `RepositoryRankingService` provides the implementation.

Validation rejects:

- null records,
- invalid identifiers,
- blank business fields,
- negative values,
- NaN and infinite amounts,
- duplicate sale identifiers.

Java streams are used for partition creation and global top-N selection, while explicit loops remain where they make stateful ranking behavior clearer.

This separation is useful in larger systems because ranking policy can become a domain rule rather than an incidental sorting detail.

## PostgreSQL Implementation

The PostgreSQL script represents the same analytical concepts relationally.

The schema contains:

- `customers`,
- `products`,
- `sales`.

Foreign keys enforce relationships between sales, customers, and products.

Check constraints prevent invalid monetary values and blank required names.

Indexes support common access paths involving customer ranking and product/category analysis.

The principal analytical views are:

- `customer_sale_row_numbers`
- `deduplicated_customer_products`
- `top_two_per_category`
- `category_rank_comparison`

The database uses window functions because they preserve individual rows while calculating analytical positions.

This is fundamentally different from a `GROUP BY` aggregation.

`GROUP BY` collapses rows into groups.

A window function calculates information across related rows while retaining the original rows in the result.

## CTEs and Analytical Pipelines

The SQL script uses common table expressions to separate stages of analysis.

A typical pattern is:

    source rows
        |
        v
    JOIN descriptive data
        |
        v
    calculate ROW_NUMBER
        |
        v
    filter selected ranks

This is particularly useful for top-N-per-group queries because filtering must occur after the window calculation.

A window-function alias cannot simply be treated like a normal source column during the same logical query stage. A CTE or derived relation makes the ranking result available to an outer query.

## Transactional Integrity

The PostgreSQL script includes a transaction that inserts a new sale and validates its presence before committing.

A second transaction performs an integrity check and rolls back.

Transactions are relevant even to analytical workflows because ranking results can become inconsistent when source data changes halfway through a multi-step business operation.

The transaction boundary belongs to the data mutation workflow, while the ranking functions determine how the committed data is subsequently ordered.

## Failure Modes and Edge Cases

### Ties

Equal ranking values require an explicit policy.

A deterministic `ROW_NUMBER` normally needs a unique secondary ordering column.

### Empty partitions

A group with no rows produces no ranking rows. This is expected behavior for relational partitioning and collection-based grouping.

### N larger than the group

Top-N operations should return all available rows rather than failing when a group contains fewer than N records.

The implementations use the equivalent of `min(N, group_size)`.

### Invalid N

Zero and negative N values are rejected because they do not describe a meaningful top-N request.

### Duplicate identifiers

A duplicate physical identifier is treated as invalid input. Business-key duplication is handled separately through the deduplication workflow.

### Negative amounts

The examples treat negative sale amounts as invalid. PostgreSQL enforces this rule with a `CHECK` constraint, while application implementations validate it before analysis.

### Equal amounts

The examples resolve equal amounts with `sale_id`. This creates a deterministic ordering without changing the primary business ranking criterion.

## Performance Considerations

Sorting is the dominant operation in most straightforward ranking implementations.

For N rows, a full sort generally costs O(n log n).

Partitioned ranking sorts each group independently, producing a cost based on the sum of the group sorting costs.

Dictionary or hash-based deduplication is expected O(n), provided the hash function distributes keys effectively.

For database workloads, indexes can reduce the amount of data that must be scanned for common predicates, but window-function queries may still require substantial sorting or partition processing.

A production system should examine the actual execution plan rather than assuming that an index will automatically accelerate every ranking query.

For very large top-N workloads, specialized query plans, indexes aligned with filtering and ordering, partition pruning, or incremental processing may be appropriate.

## Security and Data Integrity

Ranking itself does not create a security boundary, but the data being ranked may contain commercially sensitive information.

The database model therefore enforces basic integrity at the storage layer instead of relying exclusively on application validation.

Foreign keys prevent orphaned sales.

Check constraints prevent invalid amounts.

Unique identifiers prevent ambiguous physical records.

Production systems should also apply least-privilege database permissions and restrict access to sensitive customer or transaction data according to the application's authorization model.

The ranking expressions themselves should be treated as data-processing rules rather than authorization mechanisms. A row being ranked first does not imply that the current user is authorized to view it.

## Relationship Between the Implementations

The implementations intentionally solve the same analytical class of problems through different computational models.

    Ranking Problem
          |
          +----------------+----------------+
          |                |                |
        Python         JavaScript          C++17
          |                |                |
     dictionaries       Map/events       hash/maps
     lists/sort         pipeline         explicit types
          |                |                |
          +----------------+----------------+
                           |
                         Java 17
                           |
                   domain service model
                           |
                           v
                       PostgreSQL
                           |
                  relational execution
                           |
             +-------------+-------------+
             |             |             |
        ROW_NUMBER   RANK/DENSE_RANK    Top-N
             |
       partition + order
             |
       deterministic selection

The shared conceptual rule is:

> Partition when the ranking must restart for each group; order according to the business criterion; use an explicit tie-breaker when deterministic row identity matters; filter the resulting position when solving a top-N or first-row problem.

Deduplication is a related but distinct operation. It uses ranking as a mechanism for choosing a preferred representative, but the business key determines which rows are considered duplicates.

This separation prevents a common analytical error: treating every repeated value as a duplicate or treating every ranking operation as a deduplication operation.
