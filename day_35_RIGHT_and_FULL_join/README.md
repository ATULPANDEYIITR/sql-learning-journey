# RIGHT JOIN and FULL OUTER JOIN

## Scope

This module focuses on two SQL outer-join operations:

- `RIGHT JOIN`
- `FULL OUTER JOIN`

They solve different preservation problems even though both can expose unmatched records.

The central distinction is simple:

- `RIGHT JOIN` preserves **every row from the right relation**.
- `FULL OUTER JOIN` preserves **every row from both relations**.

The implementations use an employee-and-department domain because it makes the preservation rules observable. Employees may belong to departments, departments may exist without employees, and an employee may have no department assignment.

The six deliverables deliberately approach the same relational topic from different technical perspectives. Python implements join algorithms directly over collections. JavaScript models joins as reusable application-level operations and adds asynchronous consumption. C++ builds a hash-indexed reconciliation engine. Java represents join policies as enterprise-oriented domain abstractions. PostgreSQL demonstrates the operations using native relational semantics, constraints, views, transactions, and query planning.

## Relational model

The primary relationship is:

`employee.department_id -> department.department_id`

The `department` table is the master relation. The `employee` table is the dependent relation.

The sample data contains three important situations:

| Situation | Example | Why it matters |
|---|---|---|
| Matching relationship | Meera → Finance | Both sides contain a matching key |
| Right-side orphan | Research | The department exists without an employee |
| Left-side orphan | Rohan | The employee has no department assignment |

Operations such as `INNER JOIN`, `RIGHT JOIN`, and `FULL OUTER JOIN` differ mainly in which rows they preserve when the join predicate finds no match.

## RIGHT JOIN

A `RIGHT JOIN` returns matching rows and guarantees that every row from the right-hand relation remains in the result.

The basic form is:

`FROM employee AS e RIGHT JOIN department AS d ON e.department_id = d.department_id`

Here `department` is on the right. Therefore every department must remain visible.

Research and Legal appear even though no employee references either department.

For an unmatched department, columns belonging to `employee` become `NULL`. The department's own columns remain populated because that row originated from the preserved side.

### Why RIGHT JOIN is useful

A right join is appropriate when the right relation represents the population that must not disappear from a report.

Typical relational situations include:

- A department directory where departments with zero employees must still be reported.
- A product catalog where products without current transactions must remain visible.
- A service inventory where every registered service must appear even if there are no current monitoring events.
- A policy table where every policy must be reported even when no current entity references it.

A `RIGHT JOIN` is logically equivalent to reversing the table order and using a `LEFT JOIN`.

For example:

`employee RIGHT JOIN department`

and

`department LEFT JOIN employee`

produce the same relational preservation behavior when their join predicates are equivalent.

Many teams prefer `LEFT JOIN` because it keeps the primary or preserved relation on the left, but `RIGHT JOIN` is still a valid SQL operation and is useful when the query naturally expresses the preserved relation on the right.

## FULL OUTER JOIN

A `FULL OUTER JOIN` combines the preservation behavior of both sides.

It returns:

- matching employee-and-department pairs;
- employees that have no matching department;
- departments that have no matching employee.

The PostgreSQL form used in the SQL deliverable is:

`FROM employee AS e FULL OUTER JOIN department AS d ON e.department_id = d.department_id`

Rohan therefore remains in the result with department columns set to `NULL`.

Research and Legal also remain in the result, this time with employee columns set to `NULL`.

This makes `FULL OUTER JOIN` particularly useful for reconciliation.

## RIGHT JOIN versus FULL OUTER JOIN

| Property | RIGHT JOIN | FULL OUTER JOIN |
|---|---|---|
| Preserves all left rows | No | Yes |
| Preserves all right rows | Yes | Yes |
| Shows unmatched right records | Yes | Yes |
| Shows unmatched left records | No | Yes |
| Useful for master-data reporting | Yes | Sometimes |
| Useful for bidirectional reconciliation | Limited | Strong |
| Equivalent reordered LEFT JOIN | Yes | No single LEFT JOIN equivalent |

The key design question is not whether an outer join is needed. It is **which side must be preserved**.

If only the right relation must remain complete, `RIGHT JOIN` is sufficient.

If neither relation may lose unmatched records, `FULL OUTER JOIN` is required.

## Join matching and NULL

A major source of confusion is `NULL`.

SQL does not treat `NULL = NULL` as true. `NULL` represents an unknown or absent value, so an equality predicate such as:

`e.department_id = d.department_id`

does not produce a match when both values are `NULL`.

The Python, JavaScript, C++, and Java implementations explicitly reproduce this behavior instead of allowing their native collection semantics to accidentally treat two null-like values as an ordinary equal key.

This matters for reconciliation. Two records with missing keys are not automatically considered the same entity.

If a business rule requires missing values to be considered equivalent, that must be expressed deliberately through SQL logic rather than assumed from ordinary equality semantics.

## RIGHT JOIN implementation in Python

The Python implementation treats each relation as a list of dictionaries.

`right_join()` builds a hash index over the left relation. Each join key maps to all matching left rows.

The right relation is then scanned. For every right row:

- matching left rows generate joined pairs;
- no matching left row generates a result containing `None` for the left-side columns.

This reproduces the defining preservation rule of a `RIGHT JOIN`.

The implementation also handles duplicate keys. Two employees assigned to Finance both match the Finance department row, producing two result rows.

The Python program therefore demonstrates an important property of relational joins: output cardinality depends on the number of matching pairs, not merely on the number of source rows.

The `full_outer_join()` function adds a matched-right-row set. After processing the left relation, it emits right-side rows that were never matched.

That second phase is necessary because a full outer join must preserve unmatched rows from the right side as well as unmatched rows from the left.

## JavaScript implementation

The JavaScript implementation treats relations as arrays of objects and uses `Map` as a hash index.

`rightJoin()` indexes the left relation and iterates over the right relation. This makes the preservation direction explicit in application code.

`fullOuterJoin()` maintains a set of right-side positions that have participated in a match. Unmatched right records are emitted after the left-side scan.

The implementation deliberately separates relational processing from asynchronous application behavior. `simulateAsynchronousReviewOfJoin()` demonstrates how a joined result can be consumed through a Promise without pretending that asynchronous execution is itself part of the relational operation.

The JavaScript implementation also uses explicit projection after the join. This is important because object-spread operations can silently overwrite properties when two relations contain identically named fields. Real applications should select and rename output fields deliberately.

## C++ case study

The C++ program models an employee and department reconciliation engine.

`Employee` and `Department` use `std::optional<int>` for values that may be absent. This makes the distinction between a known integer key and a missing key explicit.

The `rightJoin()` implementation creates an `unordered_map<int, vector<size_t>>`. The vector is necessary because a department can have multiple employees.

The `fullOuterJoin()` implementation adds an `unordered_set` containing matched department positions. After all employees have been processed, departments not present in that set are emitted as unmatched right-side records.

The result is represented by `MergeDecision`, which includes an explicit relationship classification:

- `MATCHED`
- `EMPLOYEE_WITHOUT_DEPARTMENT`
- `DEPARTMENT_WITHOUT_EMPLOYEE`

This turns a raw join result into a reconciliation model that downstream system code could inspect.

The C++ program also calculates counts for each relationship state. This is useful when the result is consumed as a data-quality report rather than merely displayed as rows.

### C++ performance characteristics

For equality joins, the hash-index strategy has expected complexity close to `O(E + D)` for employees and departments, excluding the cost of producing the output.

The output itself can be larger than either input. If many employees share the same department key, one department can produce many joined rows.

For example, if 10,000 employees match one department, that department participates in 10,000 output pairs.

A database optimizer is not required to use the same strategy. PostgreSQL may choose a hash join, merge join, or nested-loop join depending on relation size, statistics, indexes, predicates, and cost estimates.

## Java enterprise model

The Java implementation separates join behavior behind `JoinPolicy`.

`RightJoinPolicy` represents the preservation rule of a right join.

`FullOuterJoinPolicy` represents bidirectional preservation.

`JoinReportService` provides a service boundary where domain validation can occur before executing the selected policy.

Java records provide compact immutable domain objects for `Employee`, `Department`, and `JoinResult`.

`Optional<Integer>` represents an absent department or manager without using a magic numeric value.

The result lists are copied with `List.copyOf()`, preventing callers from modifying the generated reconciliation state accidentally.

The explicit `Relationship` enum is important because an enterprise application often needs to distinguish a successful relationship from different classes of missing data. Treating every `NULL` merely as a display concern would lose information that can drive validation, reporting, or remediation workflows.

## PostgreSQL data model

The SQL deliverable creates a dedicated `join_lab` schema and defines:

- `employee`
- `department`
- `department_snapshot`

`department.department_id` is the primary key.

`employee.department_id` references `department.department_id`.

The foreign key prevents an employee from referencing a department that does not exist.

This integrity rule is intentionally demonstrated separately from outer-join behavior. A `FULL OUTER JOIN` can reveal missing relationships between independently maintained datasets, but a foreign key can prevent certain invalid relationships from being stored in the first place.

The SQL script attempts an invalid employee insert inside a transaction and rolls the transaction back after the constraint violation.

## SQL constraints and outer joins

Constraints and joins solve different problems.

A foreign key establishes an integrity rule for stored data.

A `RIGHT JOIN` or `FULL OUTER JOIN` determines how existing rows are combined for a query.

A database may therefore have:

- strong referential integrity between two tables;
- nullable relationship columns representing genuinely optional associations;
- separate historical or external datasets that require full reconciliation.

The presence of constraints does not make outer joins unnecessary. Outer joins are often used to inspect optional relationships, compare snapshots, find missing records, and report master data with no dependent activity.

## FULL OUTER JOIN for reconciliation

The `department_snapshot` table demonstrates a different use case.

The current department table contains departments 10, 20, 30, 40, and 50.

The snapshot contains 10, 20, 30, and 60.

A full outer join exposes the differences:

- 10, 20, and 30 exist on both sides;
- 40 and 50 exist only in the current table;
- 60 exists only in the snapshot.

The query classifies these states as:

`UNCHANGED`

`NEW_IN_CURRENT`

`MISSING_FROM_CURRENT`

The same pattern applies to independently maintained exports, configuration inventories, reference datasets, and reconciliation processes.

## RIGHT JOIN for complete master populations

The SQL view `department_employee_report` demonstrates a department-centric report.

The aggregation uses a `RIGHT JOIN` so that a department with zero employees still contributes a row.

`COUNT(e.employee_id)` is important because `COUNT(column)` ignores `NULL`. An unmatched department therefore receives an employee count of zero rather than one.

This is different from `COUNT(*)`, which would count the preserved department row itself.

That distinction is a practical consequence of combining outer-join null extension with SQL aggregation.

## Duplicate keys and cardinality

Joins do not assume that every key is unique unless the data model enforces uniqueness.

If one department matches three employee rows, the department participates in three joined rows.

If both sides contain duplicate values for the same join key, the number of matching pairs can grow multiplicatively.

For example, two left rows and three right rows sharing the same key produce six matching pairs.

This affects:

- result size;
- aggregation correctness;
- query cost;
- memory consumption;
- application response size.

When a relationship is intended to be one-to-one, primary keys and unique constraints should express that rule at the database layer rather than relying on developers to remember it.

## Filtering after an outer join

A common source of incorrect results is applying a `WHERE` predicate to the nullable side of an outer join without considering its effect.

For example, after a `RIGHT JOIN`, a predicate such as:

`WHERE e.department_id = 20`

removes rows where `e.department_id` is `NULL`.

That can eliminate the unmatched rows that the outer join was intended to preserve.

Predicates that define which rows participate in matching often belong in the `ON` condition when preservation must be retained.

This distinction should be evaluated carefully for every outer-join query because moving a condition between `ON` and `WHERE` can change the result from an outer-join behavior into something closer to an inner join.

## Common mistakes

### Using INNER JOIN when unmatched rows matter

An `INNER JOIN` discards unmatched rows from both sides. It is therefore unsuitable when the report must expose departments with no employees or employees without departments.

### Choosing the wrong preserved side

A `RIGHT JOIN` preserves the right relation. If the complete population is on the left, a `LEFT JOIN` may be clearer.

### Assuming NULL matches NULL

It does not under normal SQL equality semantics. Missing values require deliberate handling.

### Assuming joins are one-to-one

A shared key can produce multiple matching rows. Constraints should enforce uniqueness when uniqueness is a real business rule.

### Counting the wrong expression

With outer joins, `COUNT(*)` and `COUNT(nullable_column)` can produce different results. The employee-count report intentionally uses `COUNT(e.employee_id)` so unmatched departments receive zero.

### Ignoring output cardinality

A join can produce significantly more rows than either input. Large many-to-many joins can create substantial memory, network, and processing costs.

## Performance considerations

Equality joins are commonly optimized using hash-based or indexed strategies, but the database optimizer decides the actual execution plan.

The SQL script creates an index on `employee.department_id` because it is the foreign-key join column used repeatedly by the demonstrations.

The usefulness of an index depends on relation size, data distribution, query predicates, statistics, and the optimizer's cost model.

`EXPLAIN` is included to inspect the PostgreSQL execution plan.

For application-level implementations, hash maps provide expected constant-time key lookup, but they require additional memory and do not eliminate output-cardinality costs.

For very large relations, a database engine can perform joins without materializing entire application-level datasets in memory. This is one reason relational joins should normally be delegated to the database when the source data already resides there.

## Practical distinction

`RIGHT JOIN` answers a preservation question:

> Which right-side records must remain visible even when no left-side relationship exists?

`FULL OUTER JOIN` answers a reconciliation question:

> Which records match, which exist only on the left, and which exist only on the right?

That distinction determines the correct operator.

A department inventory with mandatory visibility for every department naturally fits a `RIGHT JOIN` when departments are placed on the right.

A comparison between two independently maintained inventories naturally fits a `FULL OUTER JOIN` because discrepancies can exist in either direction.

## Implementation relationship

The five executable implementations preserve the same relational semantics while emphasizing different engineering concerns.

| Implementation | Primary technical emphasis |
|---|---|
| Python | Direct hash-indexed join algorithms, NULL behavior, classification, and executable data processing |
| JavaScript | Array-based relational operations, `Map`, asynchronous consumption, validation, and explicit projection |
| C++ | Hash-based reconciliation engine, `std::optional`, output cardinality, and complexity |
| Java | Immutable domain records, policy abstractions, validation services, enums, and enterprise modeling |
| PostgreSQL | Native outer joins, aggregation, constraints, indexes, views, transactions, reconciliation queries, and execution plans |

The implementations are therefore not simple translations of one another. Each language exposes a different layer of the same relational problem.

## Production considerations

Outer joins should be designed around an explicit business question about row preservation.

Before implementing a query, identify which relation represents the complete population and whether unmatched records from the opposite relation are meaningful.

For reconciliation workloads, classify unmatched rows rather than merely displaying `NULL` values. A missing relationship can represent a legitimate optional association, stale data, a synchronization failure, or an integrity problem.

For high-volume queries, inspect execution plans and estimate output cardinality before deploying the query to production.

Use database constraints to prevent invalid states that should never be stored, while using outer joins to analyze legitimate optional relationships and differences between datasets.

When application code reproduces join behavior outside a database, it must explicitly define null semantics, duplicate-key behavior, output projection, memory usage, and validation rules. Silent differences between application collection semantics and SQL semantics can produce inconsistent results.
