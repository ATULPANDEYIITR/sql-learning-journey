# Subqueries Fundamentals

Subqueries are queries embedded inside another SQL statement. They allow one relational operation to supply values, rows, sets, or derived tables to another operation.

This implementation set treats four closely related ideas as distinct:

- **Scalar subqueries** return one value and are commonly used as thresholds or calculated values.
- **Single-row subqueries** return one row and are appropriate when the database rule guarantees one matching entity.
- **Multi-row subqueries** return a set of rows and work naturally with `IN`, `ANY`, `ALL`, `EXISTS`, and related predicates.
- **Table subqueries** produce a relational result that can be consumed by an outer query as a derived table.

The distinction is important because the outer query determines what cardinality it expects from the inner query. A scalar comparison such as `salary > (subquery)` cannot safely consume several unrelated rows, while `IN (subquery)` is explicitly designed to consume multiple values.

## Relational model used by the implementations

The examples use a small organizational data model containing departments, employees, projects, and employee-project assignments.

The relationships are:

- An employee belongs to one department.
- A department can contain many employees.
- A project belongs to one department.
- An employee can be assigned to multiple projects.
- An assignment records the amount of allocated project time.

This model supports meaningful subquery questions such as:

- Which employees earn more than the company-wide average?
- Which employees belong to departments selected by another query?
- Which employees have at least one heavy project assignment?
- Which employees earn more than the average for their own department?
- Which departments have no projects?
- Which departments satisfy both an employee-performance condition and a project-existence condition?
- Which departments have aggregate metrics meeting an outer filtering rule?

## Scalar subqueries

A scalar subquery produces one value.

The SQL implementation uses:

`salary > (SELECT AVG(salary) FROM employees)`

The inner aggregate calculates one company-wide average. The outer query then compares every employee salary against that value.

Aggregate functions such as `AVG`, `MAX`, `MIN`, `SUM`, and `COUNT` commonly produce scalar results. A scalar subquery can also select a single column from a row that is known to be unique.

The Python implementation executes the same relational operation through SQLite. Its `scalar_subquery()` example demonstrates the conceptual contract that the inner operation produces one value.

The JavaScript implementation makes the cardinality contract explicit through `scalarSubquery()`. Instead of silently accepting an unexpected number of rows, it throws an error when the result contains anything other than one row.

The Java implementation represents the same idea through a generic `scalar()` method. This makes cardinality part of the application-level domain behavior rather than leaving it implicit.

The C++ implementation calculates the company-wide average before evaluating the outer employee collection. The empty-input condition is treated as an explicit failure rather than allowing an invalid average to propagate.

## Single-row subqueries

A single-row subquery returns one row.

For example:

`SELECT department_id FROM departments WHERE department_name = 'Security'`

can be used by an outer query to find employees belonging to Security.

The important property is not simply that the query currently returns one row. The data model should support the assumption. The `departments.department_name` column is declared `UNIQUE`, which prevents two departments from having the same name.

This gives the outer equality predicate a reliable single-row source:

`department_id = (subquery)`

If uniqueness were not guaranteed and the inner query returned multiple department IDs, the scalar-style equality would no longer express a valid single-value relationship.

The Java implementation explicitly checks this condition through `QueryCardinalityException`. The C++ implementation uses `std::optional<int>` to distinguish a missing department from a successful lookup. The JavaScript implementation has both strict and optional scalar helpers.

## Multi-row subqueries

A multi-row subquery produces several values.

A typical pattern is:

`department_id IN (SELECT department_id FROM departments ...)`

The outer query does not expect one department ID. It expects a collection of acceptable IDs.

The SQL example selects employees from Engineering, Security, and Research by obtaining their department IDs through an inner query. The `IN` predicate then tests whether each outer employee belongs to one of those returned departments.

The JavaScript implementation converts the returned department IDs into a `Set`. This is particularly appropriate for membership testing because `Set.has()` expresses the intent directly.

The C++ implementation uses `std::unordered_set<int>` for the same membership-oriented role. The Java implementation uses a `Set<Integer>` generated from the inner department selection.

The important distinction is cardinality:

`=` expects one value.

`IN` expects a collection of values.

Using the wrong form can turn a valid relational question into a cardinality error or an incorrectly expressed business rule.

## EXISTS subqueries

`EXISTS` asks whether at least one matching row exists.

The SQL implementation checks whether an employee has an assignment with at least 180 allocated hours:

`WHERE EXISTS (SELECT 1 FROM employee_projects ...)`

The actual value selected by the inner query is irrelevant. The outer query only needs to know whether a qualifying row exists.

This makes `SELECT 1` conventional inside an `EXISTS` predicate.

The Python SQLite example uses the same relational condition.

The JavaScript implementation maps the idea to `Array.some()`. The C++ implementation uses `std::any_of()`. Both are conceptually appropriate because they can stop as soon as a qualifying element is found.

This is different from collecting all matching rows. When the requirement is existence, the existence predicate should be represented directly.

## NOT EXISTS

`NOT EXISTS` is the inverse existence test.

The SQL implementation identifies departments that do not own any projects:

`WHERE NOT EXISTS (SELECT 1 FROM projects WHERE projects.department_id = departments.department_id)`

The inner query is correlated because it uses the current department from the outer query.

The condition is evaluated for each department:

- If at least one matching project exists, the department is rejected.
- If no matching project exists, the department is retained.

`NOT EXISTS` is especially useful when nullable values could make `NOT IN` difficult to reason about.

## Correlated subqueries

A correlated subquery references a value from the current outer row.

The employee salary example compares each employee with the average salary of that employee's own department:

`WHERE e.salary > (SELECT AVG(other.salary) FROM employees AS other WHERE other.department_id = e.department_id)`

The inner query cannot be evaluated once for the whole table because its result depends on `e.department_id`.

The Python implementation demonstrates this directly with an inner average filtered by the current employee's department.

The JavaScript implementation uses `correlatedDepartmentAverage(employee)`, where the employee object provides the correlation value.

The C++ implementation passes each employee's department ID into `departmentAverage()`.

The Java implementation applies a department-specific stream calculation while processing each employee.

A correlated subquery is therefore more than a nested query. Its defining property is the dependency between the inner operation and the current outer row.

## Table subqueries

A table subquery, commonly called a derived table when used in `FROM`, produces a result set that the outer query treats as a temporary relational table.

The SQL implementation creates department metrics:

- department name
- employee count
- average salary

The outer query then filters those derived rows using `employee_count >= 2`.

Conceptually:

`outer query -> derived department metrics -> base tables`

The derived table has its own columns and rows. It is not simply one scalar value.

The Python implementation builds the same structure through a nested `SELECT` in the `FROM` clause.

The JavaScript implementation creates `derivedDepartmentMetrics` as a new collection before filtering it. This mirrors the separation between producing a relational result and consuming it.

The Java implementation uses a `DepartmentMetric` record to give the derived result a defined domain type.

The C++ implementation uses `DepartmentMetric` objects to represent the intermediate relational result.

## Nested subqueries

Subqueries can be nested when one inner operation depends on the result of another.

The SQL example asks for employees whose salaries exceed the average salary of Engineering.

The innermost query finds the Engineering department ID.

The next query calculates the average salary for that department.

The outer query compares every employee salary with that scalar result.

This creates a dependency chain:

`employee -> Engineering average -> Engineering department`

Nested subqueries should express real relational dependencies. Deep nesting without a clear relationship makes queries harder to understand and may make optimization more difficult.

## ANY and ALL

PostgreSQL provides quantified comparison operators such as `ANY` and `ALL`.

`salary > ALL (subquery)` means the salary must be greater than every value returned by the subquery.

The Finance example therefore finds employees whose salary exceeds every Finance salary.

`salary = ANY (subquery)` means the value must match at least one value returned by the subquery.

The Engineering salary example demonstrates that behavior.

The language implementations represent these semantics with their native collection operations:

- JavaScript uses `some()` for ANY-like behavior and `every()` for ALL-like behavior.
- C++ uses `std::any_of()` and `std::all_of()`.
- Java uses stream `anyMatch()` and `allMatch()`.

These are semantic equivalents for the examples, not replacements for SQL execution against a relational database.

## Subqueries in SELECT

A scalar subquery can appear in the `SELECT` list.

The SQL example adds each employee's department average beside the employee's salary:

`SELECT employee_name, salary, (subquery) AS department_average`

Because the inner result depends on the current employee's department, this is a correlated scalar subquery.

This pattern can be useful for reporting when a calculated relational metric needs to accompany each base row.

It should be evaluated carefully on large datasets because a correlated expression can represent repeated work. A query optimizer may transform it, but application developers should still inspect execution plans for important production queries.

## Subqueries in DML

Subqueries are not restricted to `SELECT`.

The SQL implementation demonstrates a subquery in `UPDATE` by increasing project budgets for departments whose payroll exceeds a threshold.

It also demonstrates a subquery in `DELETE` by identifying departments with no employees.

Both examples run inside transactions and are rolled back so that later examples continue with the original dataset.

This illustrates an important design principle: subqueries can participate in data modification while still deriving their conditions from relational data.

## NULL and NOT IN

SQL uses three-valued logic involving `TRUE`, `FALSE`, and `UNKNOWN`.

This becomes important with `NOT IN`.

If the subquery returns a `NULL`, a comparison that would otherwise appear false can become `UNKNOWN`. The SQL implementation deliberately demonstrates this behavior with:

`5 NOT IN (1, 2, NULL)`

For existence questions, `NOT EXISTS` is often easier to reason about because the condition is based on whether a matching row exists rather than comparing against a nullable list.

The JavaScript implementation explicitly warns about this distinction because JavaScript's `null` and `undefined` behavior is not identical to SQL's `NULL` semantics.

## Subqueries versus joins

Some subqueries can be rewritten as joins.

For example, selecting employees whose department name belongs to a set can be expressed through either a multi-row subquery or a join.

These forms can be logically equivalent, but they are not automatically identical in every execution context.

The database optimizer may transform one form into another. Performance depends on:

- table cardinality
- indexes
- filtering selectivity
- correlation
- database optimizer behavior
- statistics
- available execution strategies
- the exact query shape

The Python implementation compares a subquery result with an equivalent join result and verifies that they contain the same employee names.

The purpose is to distinguish logical equivalence from assumptions about runtime performance.

## Data integrity and subquery correctness

A subquery's correctness can depend on database constraints.

The SQL model uses:

- primary keys for entity identity
- foreign keys for relationships
- a unique department name
- positive salary checks
- positive project budgets
- non-negative project hours
- composite uniqueness for employee-project assignments

These constraints reduce ambiguity for subqueries.

For example, a single-row lookup by department name is safer when the name is declared unique. Without the constraint, application code might assume one row while the database contains several.

The SQL script also demonstrates a failed salary insertion inside a transaction. The database rejects the invalid value through its `CHECK` constraint.

## Performance considerations

Subquery syntax alone does not determine performance.

A scalar aggregate such as company-wide `AVG(salary)` may require scanning many rows. An indexed lookup for a unique department can be much cheaper.

Correlated subqueries deserve particular attention because their logical form can resemble repeated inner work for each outer row. Modern optimizers can decorrelate some queries, but this should be verified rather than assumed.

The SQL script includes indexes on:

- employee department
- employee salary
- project department
- assignment employee
- assignment project

The script also includes `EXPLAIN` for a scalar-subquery query. Execution plans should be inspected with realistic production-sized data before changing a query merely because it contains a subquery.

## Cardinality is a correctness constraint

The most important distinction among subquery types is the expected cardinality.

A scalar expression expects one value.

A single-row lookup expects one row.

A multi-row predicate expects a set.

A table subquery produces rows and columns for an outer relational operation.

Examples:

`salary > (subquery)`

expects a scalar result.

`department_id = (subquery)`

expects one department ID.

`department_id IN (subquery)`

accepts multiple department IDs.

`FROM (subquery) AS metrics`

expects a table-shaped result.

Confusing these contracts is a common source of SQL errors.

## Common implementation mistakes

### Assuming uniqueness without enforcing it

A query that assumes one department for a department name should be backed by a unique constraint when the business rule requires uniqueness.

### Using `=` for a multi-row result

If an inner query can return several values, `=` is not the appropriate relational operator. `IN`, `ANY`, `ALL`, or `EXISTS` may express the intended relationship.

### Ignoring NULL behavior

`NOT IN` can behave unexpectedly when the inner result contains `NULL`. `NOT EXISTS` is often a clearer choice for non-existence tests.

### Treating correlated subqueries as automatically efficient

A correlated expression may represent substantial repeated work. The execution plan matters more than the visual appearance of the SQL.

### Returning unnecessary inner columns

`EXISTS` does not need the full matching row. The examples use `SELECT 1` because only existence matters.

### Moving relational logic into application code unnecessarily

The JavaScript, C++, and Java examples intentionally model subquery semantics for educational purposes. In a real database application, large relational operations should generally remain in the database when that is where the relevant data resides.

## Implementation roles

| Deliverable | Primary technical perspective |
|---|---|
| Python | Executable SQLite demonstrations of subquery forms, transactions, NULL behavior, query plans, and Python object mapping |
| JavaScript | Collection-based relational simulation using `Set`, `some`, `every`, closures, asynchronous processing, and an event-driven query workflow |
| C++ | A typed analytics engine using STL algorithms, `optional`, hash sets, derived metrics, and explicit cardinality handling |
| Java | Enterprise-style domain modeling with records, enums, streams, validation, optional results, generic scalar handling, and domain-specific services |
| SQL | PostgreSQL relational implementation with DDL, DML, constraints, indexes, derived tables, quantified predicates, transactions, and execution-plan inspection |

## Practical relationship between the categories

The categories are related but should not be collapsed into one concept.

A **scalar subquery** supplies one value.

A **single-row subquery** supplies one row under a cardinality assumption.

A **multi-row subquery** supplies a collection of candidate values.

A **correlated subquery** adds dependency on the current outer row.

A **table subquery** supplies an entire relational result to another query layer.

`EXISTS` and `NOT EXISTS` focus specifically on whether matching rows exist rather than on retrieving a value.

These distinctions determine which operators, validation rules, and execution strategies are appropriate.

## Production considerations

Production subqueries should be designed around the actual data model and business rule rather than around syntax alone.

Uniqueness assumptions should be represented by constraints. Foreign-key relationships should be enforced by the database. Nullable fields should be considered when using `NOT IN`. Correlated queries should be examined with realistic data volumes. Important queries should be tested with `EXPLAIN` or the database's equivalent plan-analysis facility.

The application implementations also demonstrate an important boundary: application code can model relational concepts, validate returned cardinality, and process results, but a database engine provides the actual relational execution, indexing, transaction handling, statistics, and optimizer behavior.
