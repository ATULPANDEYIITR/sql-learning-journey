# JOIN vs Subquery

## Topic Scope

`JOIN` and `subquery` are both relational query techniques, but they express different forms of query composition.

A `JOIN` explicitly combines rows from two or more relations. It is usually the clearest choice when columns from related tables are part of the result or when the relationship itself is central to the query.

A subquery creates an inner query whose result is consumed by an outer query. The inner result may be a set used by `IN`, a Boolean existence test used by `EXISTS`, a scalar value used in a comparison, or a derived relation used as a table expression.

The important design question is not whether JOINs are universally faster than subqueries. Modern database optimizers can transform logically equivalent SQL into similar physical execution plans. Query quality depends on the required result, cardinality, predicates, indexes, constraints, statistics, data distribution, and database engine.

This project demonstrates these distinctions through Python, JavaScript, C++, Java, and PostgreSQL implementations.

## Core Relational Distinction

Consider an employee and department relationship.

A JOIN represents the relationship directly:

`employees JOIN departments ON employees.department_id = departments.department_id`

This is appropriate when the result needs employee attributes and department attributes together.

A subquery can instead produce a department identifier first:

`WHERE department_id IN (SELECT department_id FROM departments ...)`

The outer query consumes the result of the inner query without necessarily exposing department columns in the final result.

These forms may be logically equivalent for a particular requirement, but their readability can differ. The best form should communicate the actual relationship being expressed.

## JOIN Semantics

An `INNER JOIN` returns rows for which the join condition matches on both sides.

For example, the SQL implementation joins `employees` to `departments` through `department_id`. The result contains employee names, department names, and salaries.

A `LEFT JOIN` preserves every row from the left relation even when no matching row exists on the right. This becomes particularly useful for reports such as department summaries where a department with zero employees must still appear.

The SQL implementation uses a `LEFT JOIN` for department-level employee counts. `COUNT(e.employee_id)` is important because counting a nullable right-side column allows departments without employees to produce a count of zero.

Many-to-many relationships introduce another important JOIN behavior. The `employee_projects` relation connects employees and projects. A JOIN through this table creates one result row per qualifying relationship. If an employee has several qualifying projects, that employee can therefore appear several times.

That multiplicity is correct when project-level information is required. It is unnecessary when the actual question is only whether at least one qualifying project exists.

## Subquery Forms

Subqueries are not one single mechanism. Their behavior depends on how the outer query consumes them.

### Set subqueries

`IN` compares an outer value against a set produced by an inner query.

The Python and SQL implementations use this approach to identify employees whose department belongs to a selected group.

This is readable when the inner query naturally represents a set of allowed values.

### Scalar subqueries

A scalar subquery must produce at most one value in the context where it is used.

The SQL implementation looks up a department identifier from a unique department name and compares an employee's `department_id` with that value.

A uniqueness constraint on `department_name` makes the scalar assumption valid. Without such a guarantee, a scalar subquery could fail because the inner query returns multiple rows.

### Correlated subqueries

A correlated subquery refers to a column from the current outer row.

The employee salary example uses this relationship:

`e.salary > (SELECT AVG(e2.salary) ... WHERE e2.department_id = e.department_id)`

The inner aggregate depends on the department of the current employee.

This expresses the business rule directly: compare each employee with the average salary of that employee's department.

The conceptual simplicity of this form does not imply a particular physical execution strategy. The optimizer may rewrite or optimize the query.

### EXISTS

`EXISTS` answers an existence question.

The project example asks whether an employee has at least one project whose budget meets a threshold.

The result is employee-level rather than project-level. Therefore, `EXISTS` communicates the requirement more accurately than a JOIN followed by `DISTINCT`.

This distinction matters because `DISTINCT` can hide an unnecessary row multiplication problem instead of expressing the underlying business requirement directly.

## Aggregation: Correlated Subquery vs Pre-Aggregation

The project contains two approaches to comparing employees with departmental averages.

The correlated form calculates an average for the current employee's department.

The derived-table form calculates departmental averages as a relation and then joins employees to those aggregate rows.

A CTE can make the same multi-stage design easier to read:

`WITH department_salary AS (...) SELECT ...`

Pre-aggregation becomes particularly useful when the aggregate contains several metrics, such as average, minimum, maximum, employee count, and total salary. Computing those metrics as one relational result gives subsequent parts of the query a stable structure to consume.

The choice should still be validated with an execution plan for large datasets.

## Readability and Query Intent

Readability should describe the business question rather than the author's preferred SQL construct.

A JOIN is generally expressive when the question is:

- Which employee belongs to which department?
- Which project assignments belong to each employee?
- Which department attributes should appear beside employee attributes?
- How should related rows be aggregated together?

A subquery is often expressive when the question is:

- Is this value contained in a calculated set?
- Does a related row exist?
- What aggregate value belongs to the current outer row?
- What derived relation should be used as an intermediate result?

A poorly chosen JOIN can produce unnecessary duplicates. A poorly structured subquery can hide important relationships or make a complex dependency difficult to follow.

The correct criterion is semantic clarity first, followed by correctness and measured performance.

## Python Implementation

The Python program uses the standard-library `sqlite3` module, so it can run without an external database package.

Its relational dataset contains departments, employees, projects, and employee-project assignments.

The program demonstrates:

- direct INNER JOIN retrieval;
- filtering through `IN` subqueries;
- scalar subqueries;
- JOIN-based aggregation;
- correlated aggregate subqueries;
- a window-function alternative;
- `EXISTS` for relationship testing;
- duplicate-row behavior caused by JOIN multiplicity;
- anti-joins and `NOT EXISTS`;
- NULL-related `NOT IN` considerations;
- CTE-based query composition;
- parameterized SQL;
- SQLite query-plan inspection;
- multi-stage reporting.

The Python program also validates that two logically equivalent strategies for the departmental-average problem return the same employee set.

The use of parameter binding in `dynamic_query_builder` demonstrates an important production practice. User-controlled values remain data parameters rather than being concatenated into SQL syntax.

## JavaScript Implementation

The JavaScript implementation uses Node.js built-in modules and treats query definitions as application-level objects.

`QueryCatalog` provides a small event-driven registry. Query registration emits an event, which demonstrates a JavaScript-specific approach to observing application state without requiring an external framework.

The SQL builders return an object containing:

- `text`, representing parameterized SQL;
- `values`, representing bound values.

The employee search validates input before constructing the query. The implementation deliberately avoids interpolating user-provided values into SQL text.

The project comparison illustrates the distinction between a JOIN that returns project details and `EXISTS` that returns each employee once when a qualifying project exists.

The asynchronous `inspectQuery` function represents the boundary between application logic and a database driver. A PostgreSQL client can replace the mock executor while preserving the same parameterized query structure.

## C++ Case Study

The C++ program models a relational analytics engine without an external database dependency.

The `GovernanceData` class represents departments, employees, projects, and assignments. `QueryEngine` then implements several relational strategies.

The JOIN-style employee-department operation returns objects containing both the employee and department.

The project JOIN creates one output row per qualifying employee-project assignment. This deliberately preserves relationship multiplicity.

The EXISTS-style method searches assignments for each employee and stops as soon as one qualifying project is found. The early termination reflects the semantics of an existence test.

The correlated departmental-average implementation calculates the average separately for each outer employee. Its straightforward algorithm has a potential `O(E²)` cost for `E` employees.

The pre-aggregated implementation first calculates one average per department and then looks up that aggregate for each employee. With hash-based lookup, the modeled work is approximately linear in the number of employee rows.

These are algorithmic models, not claims about what a SQL optimizer will actually do. A database can use indexes, hash joins, merge joins, materialization, parallelism, or other physical strategies.

The program validates that the correlated and pre-aggregated approaches produce the same logical employee set.

## Java Enterprise Model

The Java implementation represents the same relational problem through domain-oriented abstractions.

The records `Department`, `Employee`, `Project`, and `Assignment` provide immutable domain values with constructor validation.

`Repository` owns the relational entities and validates references after the dataset is created. This mirrors the referential-integrity role of database foreign keys.

`QueryService` separates query-oriented operations from data storage.

The JOIN operation creates `EmployeeDepartment` records because both sides of the relationship are part of the result.

The project operation creates `EmployeeProject` records because assignment hours and project information are required.

The existence operation uses Java Stream `anyMatch`. This is conceptually close to SQL `EXISTS`: once a qualifying project is found, the existence condition is satisfied.

The departmental-average comparison is represented in two ways. The correlated version calculates the relevant department average for each employee. The pre-aggregated version creates a department-to-average map first and then evaluates employee salaries against it.

The Java model therefore demonstrates how relational query decisions can influence application-layer architecture without pretending that Java collection operations are a replacement for database optimization.

## PostgreSQL Data Model

The SQL implementation creates the `join_subquery_lab` schema with four related tables.

`departments` stores organizational units and enforces unique department names.

`employees` references departments through a foreign key and validates positive salaries.

`projects` references departments and validates non-negative budgets.

`employee_projects` represents the many-to-many employee-project relationship. Its composite primary key prevents duplicate employee-project assignments.

The foreign keys enforce relational integrity at the database layer rather than depending exclusively on application validation.

Indexes are created on common relationship and filtering columns, including employee department, employee salary, project department, and project references.

These indexes are not automatically proof of better performance. Their value depends on workload, selectivity, table size, query shape, statistics, and the optimizer's chosen plan.

## JOIN Multiplicity

One of the most important practical differences between JOIN and existence-oriented subqueries is row multiplicity.

Suppose one employee is assigned to three projects whose budgets exceed the threshold.

A JOIN that returns project information can produce three rows for that employee.

An `EXISTS` predicate returns the employee once because it asks only whether a matching project exists.

Using `SELECT DISTINCT employee_id` after the JOIN can produce the desired unique employee result, but it introduces another operation and can conceal the fact that the original requirement was an existence test.

The SQL implementation intentionally shows both approaches so that the row-multiplication behavior is visible.

## Anti-Join and NOT EXISTS

Finding records with no related rows is another important query-design case.

The SQL script uses:

`LEFT JOIN ... WHERE right_table.id IS NULL`

and:

`WHERE NOT EXISTS (...)`

Both can represent an anti-matching requirement.

The anti-join makes the outer-join mechanism explicit. `NOT EXISTS` states the absence condition directly.

For complicated predicates, `NOT EXISTS` can be easier to reason about because the inner query describes exactly what would constitute a forbidden match.

## NULL and NOT IN

`NULL` introduces three-valued SQL logic.

A common mistake is to use `NOT IN` without considering whether the subquery can return NULL.

For an anti-matching requirement, `NOT EXISTS` is often easier to reason about because the predicate evaluates the relationship row by row rather than comparing against a set containing an unknown value.

Schema constraints that prevent unnecessary NULLs can simplify this problem, but query design should still account for nullable expressions and outer joins.

## Performance Considerations

There is no universal rule that JOIN is faster than a subquery.

A database optimizer may transform a subquery into a semi-join, anti-join, hash operation, or another physical strategy. A JOIN may likewise be reordered or optimized into a different execution plan.

Performance should therefore be investigated through the database's plan tools.

The PostgreSQL script uses `EXPLAIN` and `EXPLAIN (ANALYZE, BUFFERS)`.

`EXPLAIN` provides the optimizer's estimated plan.

`EXPLAIN ANALYZE` executes the query and reports actual execution behavior. It is particularly useful for identifying discrepancies between estimated and actual row counts.

Important plan-level factors include:

- join method;
- estimated and actual cardinality;
- index scans versus sequential scans;
- filter selectivity;
- aggregation strategy;
- sorting;
- memory usage;
- repeated correlated work;
- data distribution;
- statistics quality.

Small test datasets can produce misleading conclusions. A query that looks equally fast in a ten-row demonstration may behave very differently across millions of rows.

## Indexing Considerations

JOIN predicates commonly benefit from indexes on foreign-key columns and frequently filtered attributes.

The SQL implementation indexes `employees.department_id`, `projects.department_id`, and `employee_projects.project_id`.

Indexes can reduce lookup work, but they also consume storage and add write overhead. An index should therefore support an actual access pattern rather than being added simply because a column appears in a query.

A selective predicate may benefit strongly from an index. A low-selectivity column may still lead the optimizer toward a sequential scan.

Execution plans should be evaluated after representative data and statistics are available.

## Common Query-Design Mistakes

A JOIN can accidentally multiply rows when the relationship is one-to-many or many-to-many.

A scalar subquery can fail when the inner query unexpectedly returns multiple rows.

A correlated subquery can hide repeated work when a calculation could be expressed as a reusable aggregate relation.

`NOT IN` can produce surprising results when NULL enters the subquery result.

A `LEFT JOIN` can unintentionally become an INNER JOIN when a condition on the nullable right-side table is placed in the `WHERE` clause rather than carefully considered in the join predicate.

`DISTINCT` can hide duplicate-row problems instead of fixing the relational design.

A query can be logically correct but operationally expensive because it processes a much larger intermediate result than necessary.

Assuming that a particular SQL form is faster without inspecting the execution plan is another common mistake.

## Query-Design Decision Framework

A useful decision process is to start with the required result rather than the SQL keyword.

If attributes from related relations must appear together, a JOIN is usually the most direct expression.

If the requirement is whether at least one related row exists, `EXISTS` often expresses the intent more accurately.

If an outer row must be compared with a value calculated specifically for that row, a correlated subquery can be clear.

If a calculated relation will be reused by several parts of a query, a derived table or CTE can make the relational stages explicit.

If records with no matches must be found, an anti-join or `NOT EXISTS` can express the absence relationship.

After choosing a logically clear formulation, examine its execution plan and test it against representative data.

## Practical Relationship Between Readability and Performance

Readability and performance are related but distinct concerns.

A readable query is easier to verify, maintain, modify, and troubleshoot.

A performant query minimizes unnecessary work at execution time.

The two goals can conflict. A compact correlated subquery may communicate a business rule very clearly while a pre-aggregated design may provide a more efficient or reusable intermediate result.

The solution is not to reject readable SQL in favor of complicated SQL. It is to begin with the clearest correct relational expression and measure the resulting execution behavior before introducing complexity.

## Security Considerations

JOIN versus subquery selection does not by itself determine SQL security.

The major application-level concern demonstrated by the Python and JavaScript implementations is separation of SQL structure from user data.

Parameterized queries prevent user-controlled values from being interpreted as SQL syntax.

Dynamic SQL should not be constructed by concatenating untrusted input into JOIN conditions, WHERE predicates, table names, or other SQL fragments.

Database constraints provide another security and correctness boundary. Foreign keys prevent orphaned relationships, unique constraints prevent duplicate identifiers, and check constraints reject invalid values before they enter downstream queries.

## Testing and Debugging

Equivalent query formulations should be tested for both result correctness and performance.

The implementations deliberately compare correlated and pre-aggregated departmental-average calculations and validate that their result sets agree.

Tests should include:

- departments with many employees;
- departments with no employees;
- employees with several projects;
- employees with no projects;
- projects above and below threshold values;
- duplicate relationship attempts;
- NULL-capable expressions;
- empty result sets;
- scalar subqueries that could accidentally return multiple rows.

For performance testing, correctness tests are not enough. Representative row counts and data distributions are necessary.

When a query becomes unexpectedly slow, inspect the actual execution plan rather than changing JOINs into subqueries or vice versa without evidence.

## Final Technical Principle

JOIN and subquery are not competing keywords where one is inherently superior.

They are different ways of expressing relational relationships.

A JOIN emphasizes row combination.

A subquery emphasizes an intermediate result or dependency.

`EXISTS` emphasizes relationship existence.

A correlated subquery emphasizes a calculation dependent on an outer row.

A derived table or CTE emphasizes a reusable relational stage.

Good query design preserves the meaning of the business requirement, avoids accidental row multiplication, maintains readable relational structure, and uses execution-plan evidence to guide performance decisions.
