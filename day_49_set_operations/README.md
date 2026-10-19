# SQL Set Operations: UNION, UNION ALL, INTERSECT, and EXCEPT

## Scope

Set operations combine the results of compatible queries according to membership and duplicate semantics. The four central SQL operators in this implementation are:

| Operator | Meaning | Duplicate handling |
|---|---|---|
| `UNION` | Rows present in either query result | Removes duplicate rows |
| `UNION ALL` | Rows from both query results | Preserves duplicates |
| `INTERSECT` | Rows present in both query results | Returns distinct matching rows |
| `EXCEPT` | Rows present in the first result but absent from the second | Directional and distinct |

The important distinction is that SQL set operations operate on **query result rows**, not merely on individual scalar values. The selected columns therefore determine what constitutes a comparable row.

For example, `SELECT email FROM crm UNION SELECT email FROM billing` compares only email values. If `source_system` is included in the projection, the source becomes part of the row identity.

The implementations use a customer-audience reconciliation domain because independent operational sources naturally produce populations that must be combined, compared, and reconciled.

## Core Semantics

### UNION

`UNION` combines two compatible query results and removes duplicate rows.

Conceptually:

`A UNION B`

means membership in `A`, membership in `B`, or membership in both.

If CRM contains Alice and Bob while Billing contains Bob and Carol, the result contains Alice, Bob, and Carol once each.

The SQL implementation deliberately uses:

`SELECT email FROM customers WHERE source_system = 'crm' UNION SELECT email FROM customers WHERE source_system = 'billing'`

The projection contains one column in both branches, so the results are structurally compatible.

`UNION` is appropriate when the question is about a distinct population rather than the number of source occurrences.

### UNION ALL

`UNION ALL` concatenates result rows without duplicate elimination.

This distinction matters when frequency represents meaningful information. If Bob occurs in both source populations, `UNION ALL` retains both occurrences.

The SQL script demonstrates this using CRM and Billing records. The Python and JavaScript implementations similarly use sequence structures for `UNION ALL`, rather than pretending that a set can retain duplicate multiplicity.

A `Set` is therefore not a substitute for `UNION ALL` when duplicate frequency is part of the required result.

### INTERSECT

`INTERSECT` returns rows that occur in both query results.

For customer reconciliation, CRM `INTERSECT` Billing identifies customers represented by both source systems.

This is useful for questions such as:

- Which customers exist in both operational systems?
- Which accounts occur in both independently generated populations?
- Which identities are shared by two source datasets?

The result concerns membership in both populations rather than the origin of either row.

### EXCEPT

`EXCEPT` is directional.

`A EXCEPT B` means:

> rows in A that are not present in B.

It is therefore different from an undirected notion of difference.

The SQL script explicitly demonstrates both:

`CRM EXCEPT Billing`

and:

`Billing EXCEPT CRM`

These can produce different populations. This directional property is particularly important in reconciliation work where one source is treated as the authoritative or reference population.

## Compatibility of Query Results

Set operations require compatible result structures.

The simplest case is:

`SELECT email FROM crm`

combined with:

`SELECT email FROM billing`.

Both return one comparable column.

For multi-column operations, the projected rows must have corresponding column positions with compatible data types. The values across the complete projection participate in duplicate and membership comparison.

Consequently:

`SELECT email, source_system ...`

has different set semantics from:

`SELECT email ...`

because the second selected attribute changes the row being compared.

The SQL implementation includes a composite projection to make this distinction observable.

## Distinctness and Row Identity

A major source of errors is confusing entity identity with row identity.

Suppose a customer appears in CRM and Billing:

| email | source_system |
|---|---|
| bob@example.com | crm |
| bob@example.com | billing |

A query projecting only `email` treats these as the same set member.

A query projecting both columns treats them as different rows because the complete projected values differ.

This means the projection should be designed around the business question.

If the question is "which distinct customers exist?", email may be the intended comparison key.

If the question is "which source-specific records exist?", source information belongs in the projection.

## Python Implementation

The Python program models SQL set semantics with native `set` operations.

`|` represents union, `&` represents intersection, and `-` represents directional difference.

The script also introduces `union_all()` as a list operation because Python sets intentionally discard duplicate occurrences.

The customer campaign example separates:

- the population known to the customer system;
- webinar registrants;
- customers who purchased;
- registrants without purchases;
- purchasers who were absent from the webinar;
- enterprise customers within an intersected population.

The CSV example demonstrates how external tabular data can be normalized into sets before comparison. Email normalization is deliberately performed before set construction so values such as `BOB@example.com` and `bob@example.com` do not accidentally become different members.

The multi-source reconciliation model goes beyond two sets. It calculates the union of all populations, the intersection common to every source, source-exclusive populations, and source coverage counts.

The Python performance example uses large sets to make the practical cost of hash-based membership operations visible.

## JavaScript Implementation

The JavaScript implementation focuses on how set operations can be modeled without relying on a nonexistent built-in SQL-style `Set.union()` API.

`Set` is used for distinct membership, while arrays are deliberately retained for `UNION ALL`.

The `AudienceEngine` class stores source populations in a `Map`. This is a JavaScript-specific representation of multiple named datasets.

Its operations include:

- combining source populations;
- finding common members;
- identifying members exclusive to a particular source;
- calculating source coverage.

The object-projection example addresses an important JavaScript behavior: `Set` compares objects by identity rather than by structural equality.

Two separately created objects with identical properties are still different `Set` members. For relational-style distinctness, the implementation therefore projects objects onto an explicit comparison key such as email.

The event-driven portion uses `EventTarget` and `CustomEvent`. Set computation produces an event containing the resulting populations, showing how set-based processing can participate in an asynchronous JavaScript workflow.

## C++ Case Study

The C++ program presents repository governance as a technical case study.

Maintainer populations from application, security, identity, and other service areas are represented as `std::set<std::string>`.

The implementation uses the standard library algorithms:

- `std::set_union`;
- `std::set_intersection`;
- `std::set_difference`.

The sets are sorted containers, which satisfies the requirements of these standard algorithms and provides deterministic output.

A `RepositoryGovernanceCaseStudy` class maintains named repository teams in a map. Its operations answer practical questions such as which maintainers are shared across services and which maintainers are exclusive to one repository.

The program also computes cross-repository coverage. This is deliberately different from a simple set union because coverage counts how many source populations contain each member.

The `UNION ALL` analogue uses `std::vector`, preserving duplicate reviewer occurrences. The separate `std::set` representation then provides the distinct reviewer population.

This distinction demonstrates why the container choice should follow the semantics of the required operation.

For sorted ranges of sizes `n` and `m`, the standard set algorithms operate in linear time relative to the two input ranges, approximately `O(n + m)`. The memory required by the explicit result depends on the number of returned elements.

## Java Enterprise Model

The Java implementation represents source systems with the `SourceSystem` enum:

`CRM`, `BILLING`, `SUPPORT`, and `PRODUCT`.

The `AudienceRepository` stores source-specific email sets in an `EnumMap`. This creates an explicit relationship between a business source and its population.

The repository exposes separate methods for union, intersection, and directional difference. Each method creates a new result rather than modifying the stored source population.

`Set.copyOf()` provides an immutable stored representation. This prevents callers from silently changing an audience after it has been registered.

`TreeSet` is used for deterministic ordering in displayed results.

The `commonToEverySource()` operation demonstrates repeated intersection across multiple populations. This is different from a two-source `INTERSECT` because the result must survive intersection with every registered source.

The source-coverage operation uses Java Streams and `groupingBy()` to count how many source populations contain each email.

The domain `Customer` record adds validation at object construction time. It demonstrates how domain constraints can prevent malformed records before they participate in set operations.

## PostgreSQL Data Model

The SQL implementation uses the `set_operations_demo` schema.

The main `customers` table contains:

- a generated customer identifier;
- an email;
- a source-system identifier;
- a creation timestamp.

The unique constraint on `(email, source_system)` prevents duplicate representations of the same customer within one source while still allowing the same customer to appear in multiple source systems.

The `source_system` check constraint limits source values to the defined operational populations.

The email check constraint provides basic structural validation, while the indexes on email and source-plus-email support common reconciliation access patterns.

Additional tables model campaign registrations and purchases. These provide populations that can be compared with `INTERSECT` and `EXCEPT`.

## Database-Level Enforcement

Constraints are important because set operations should not be expected to repair invalid source data.

The unique constraint prevents duplicate source-specific customer rows.

The source check constraint prevents an unsupported source from entering the model.

The purchase amount check constraint prevents non-positive purchase amounts.

The campaign uniqueness constraint prevents duplicate registration of the same email for the same campaign.

The transaction section demonstrates that an invalid source value is rejected by the database constraint and the transaction can be rolled back.

This keeps domain integrity at the database layer rather than relying entirely on application validation.

## CTE-Based Set Processing

Common table expressions make complex set logic easier to reason about.

The SQL implementation defines CRM, Product, and Support populations independently and then intersects them.

This makes the source boundaries visible before the final set operation.

CTEs are especially useful when the individual populations require filters, joins, normalization, or other preparation before being combined.

The important principle is that the CTEs should establish the correct populations first. The final set operator should then express the relationship between those populations.

## Set Operations Versus Aggregation

Set operators and aggregation answer different questions.

`UNION` asks which distinct rows exist across multiple result sources.

`COUNT(*) GROUP BY email` asks how many rows contribute to each email.

The SQL script deliberately includes both approaches.

For example, if Bob appears once in CRM and once in Billing:

`UNION`

produces one Bob.

An aggregate count over the underlying source rows can report two contributing records.

Neither result is inherently more correct. The appropriate operation depends on whether the business question concerns distinct membership or multiplicity.

## Set Operations Versus Joins

A set operation combines compatible query results vertically.

A join combines related columns horizontally according to a matching condition.

For example, `INTERSECT` can identify emails common to two independently projected populations without exposing columns from both sources.

A join would be more appropriate when the result must contain attributes from both sides, such as CRM customer metadata alongside Billing account metadata.

This distinction helps prevent using joins merely because two datasets need to be compared.

## Common Mistakes

### Using UNION when duplicates matter

If the number of source occurrences has business meaning, `UNION` silently removes those duplicates.

`UNION ALL` is appropriate when every contributing row must remain visible.

### Forgetting that EXCEPT is directional

`A EXCEPT B` and `B EXCEPT A` normally produce different results.

The first query represents members exclusive to A relative to B. The reverse query represents members exclusive to B relative to A.

### Comparing the wrong projection

If email is the intended identity but the query also selects source metadata, the set comparison changes from customer-level membership to source-specific row membership.

### Treating Set as structural object equality in JavaScript

JavaScript `Set` uses object identity for objects.

Two objects containing the same fields do not automatically collapse into one set member.

Projection onto a stable business key is required when relational-style distinctness is intended.

### Assuming Python and SQL NULL behavior are identical

Python `None` is an ordinary hashable object.

SQL `NULL` follows SQL's three-valued logic and database-specific set-operation rules. Translation between application-level set processing and SQL therefore requires explicit testing of null-containing data.

## Performance Considerations

Set operations normally require processing the participating populations.

For in-memory hash-based structures such as Python `set` and JavaScript `Set`, membership checks are expected to be constant time on average, while constructing a result requires processing the relevant input members.

C++ ordered `std::set` uses logarithmic membership operations, while the standard sorted-range set algorithms process sorted inputs in linear time with respect to their combined range sizes.

PostgreSQL can choose different physical strategies for set operations based on table statistics, indexes, memory settings, and query structure. `EXPLAIN` should be used against realistic data when performance matters.

Indexes are useful for locating filtered source populations efficiently, but an index does not guarantee a particular final set-operation strategy.

## Security and Data Quality

Set operations themselves are not a security boundary.

A system comparing customer populations should control access to the underlying data and avoid exposing sensitive identifiers unnecessarily.

Normalization should occur before comparison when equivalent representations can otherwise produce false differences. Email case and whitespace are examples addressed by the application implementations.

Audit requirements may also require retaining source provenance instead of collapsing everything into one anonymous set. `UNION` is useful for distinct population analysis, but source-specific tables should remain available when lineage matters.

## Practical Relationship Between the Four Operators

The operators answer four different membership questions:

| Business question | SQL operation |
|---|---|
| Which records exist in either population? | `UNION` |
| Which records from both inputs must remain, including duplicates? | `UNION ALL` |
| Which records are shared by both populations? | `INTERSECT` |
| Which records exist in the first population but not the second? | `EXCEPT` |

The distinction between these operations is primarily semantic. Correct implementation begins by identifying whether the requirement concerns distinct membership, occurrence frequency, shared membership, or directional exclusion.
