# Database Views: CREATE VIEW, View Abstraction, and Reusable Queries

## 1. Introduction

A database view is a named query that presents data from one or more underlying database objects as a virtual table.

Views provide a logical interface between database storage and application queries. They allow applications, analysts, and reporting systems to consume predefined data structures without repeatedly implementing the same joins, filters, and aggregations.

A regular view generally stores its query definition rather than an independent copy of its result. When queried, the database evaluates the view against its underlying relations, subject to the database optimizer and transaction visibility rules.

The central concepts covered in this project are:

- `CREATE VIEW` and view definitions.
- Simple and complex views.
- View abstraction and logical data independence.
- Reusable queries.
- Joins and aggregations.
- Nested views.
- Updatable views.
- Materialized views.
- View dependencies.
- Access control and security considerations.
- Query execution and performance.

## 2. Database View Fundamentals

### 2.1 What a View Represents

A database view presents the result of a query through a named database object.

Its definition can contain:

- Column selection.
- Row filtering.
- Joins.
- Aggregate functions.
- Grouping.
- Expressions.
- Subqueries.
- References to other views.

A view is queried using a `SELECT` statement in the same general manner as a table.

The distinction is that a regular view represents a stored query definition rather than independently maintained table data.

### 2.2 CREATE VIEW

The SQL statement `CREATE VIEW` defines a named query.

Conceptually, a view has three elements:

| Element | Purpose |
|---|---|
| View name | Identifies the reusable database object |
| Query definition | Describes how data is retrieved |
| Output columns | Define the interface exposed to consumers |

A view can expose selected columns while hiding unrelated columns from its consumers.

The view definition can also filter records before they become visible through that interface.

### 2.3 View Abstraction

View abstraction separates the logical representation of information from the underlying physical organization of database tables.

Consider an employee management database.

The underlying employee table contains:

- Employee identifier.
- Employee name.
- Department identifier.
- Salary.
- Employment status.
- Hiring date.

A public employee directory may expose only:

- Employee identifier.
- Employee name.
- Department identifier.

Consumers can retrieve directory information without understanding every column in the underlying employee table.

This reduces coupling between applications and database structures.

### 2.4 Logical Data Independence

Logical data independence concerns the ability to modify the logical database structure without unnecessarily changing dependent applications.

Views can provide a stable interface when underlying queries or table relationships change.

This protection is not absolute.

Changes to exposed column names, data types, relationships, or view semantics can still break dependent applications.

A view should therefore be treated as a database interface with an explicit compatibility contract.

## 3. Types of Database Views

### 3.1 Simple Views

A simple view normally references one base table and selects a subset of its columns or records.

Example from the PostgreSQL implementation:

`employee_directory`

It exposes active employee identifiers, names, and department identifiers.

Its purpose is to provide a restricted and reusable employee interface.

Simple views can often support automatic updates, depending on the database system and the view definition.

### 3.2 Complex Views

Complex views combine information from multiple relations.

They can include:

- Multiple-table joins.
- Aggregate functions.
- Grouping.
- Calculated columns.
- Nested queries.

The project implements two important complex views.

`employee_department_details` combines employees and departments.

`project_workload` combines projects, departments, and assignments.

These views provide a common reporting structure for consumers that would otherwise need to repeat the same relational operations.

### 3.3 Aggregate Views

Aggregate views summarize detailed records into higher-level information.

The `department_statistics` view calculates:

| Attribute | Calculation |
|---|---|
| Employee count | `COUNT()` |
| Average salary | `AVG()` |
| Total payroll | `SUM()` |
| Minimum salary | `MIN()` |
| Maximum salary | `MAX()` |

The view uses `LEFT JOIN` to preserve departments without active employees.

`COALESCE()` ensures that missing aggregate totals are represented as zero where appropriate.

A distinction is necessary between a missing value and a genuine zero. For example, the minimum salary of a department with no employees remains `NULL`, because there is no minimum salary to calculate.

### 3.4 Nested Views

A nested view references another view.

The project implements `high_workload_projects` using `project_workload`.

The relationship is:

`projects + departments + assignments`

↓

`project_workload`

↓

`high_workload_projects`

This design centralizes complex relational logic.

When multiple reporting objects require the same project workload calculation, they can reuse its definition rather than duplicate joins and aggregation expressions.

Nested views can increase dependency complexity, so their definitions should remain understandable and their execution plans should be inspected.

### 3.5 Filtered Views

Filtered views restrict the records exposed through a particular database interface.

The `active_project_report` view exposes only projects whose status is `ACTIVE`.

The `active_employee_public` view exposes active employees without exposing salary information.

These views demonstrate how database consumers can receive different logical representations of the same underlying data.

A filtered view is not automatically a complete authorization boundary. Access to base tables and other views must also be controlled through database privileges and appropriate security policies.

## 4. Regular Views and Materialized Views

A regular view and a materialized view have different storage and maintenance behavior.

| Characteristic | Regular View | Materialized View |
|---|---|---|
| Stores query definition | Yes | Yes |
| Stores query result | Normally no | Yes |
| Uses current underlying data when queried | Yes, subject to transaction visibility | Not necessarily |
| Requires explicit refresh | No | Yes |
| Storage requirement | Usually minimal | Requires storage for results |
| Typical use | Reusable queries | Expensive reporting queries |
| Maintenance | Evaluated during querying | Refreshed separately |

### 4.1 Regular View

A regular view is evaluated when a consumer queries it.

For example:

`SELECT * FROM department_statistics;`

The database processes the underlying query using its optimizer.

This approach avoids independently maintaining a second copy of the aggregate data.

Its performance depends on the underlying tables, indexes, joins, query complexity, and execution plan.

### 4.2 Materialized View

A materialized view stores the result of a query.

The PostgreSQL implementation creates:

`department_statistics_cache`

The stored result can be retrieved without recalculating the complete aggregate query for every request.

The materialized view must be refreshed when its underlying information changes.

The implementation provides:

- Materialized-view creation.
- A unique index.
- A refresh procedure.
- Retrieval queries.

PostgreSQL supports ordinary refresh operations and concurrent refresh operations. Concurrent refresh requires an appropriate qualifying unique index and has additional operational considerations.

A materialized view introduces a freshness-versus-performance trade-off.

## 5. Reusable Queries and View Consumption

Views separate query definition from query consumption.

A consumer can retrieve a complete view:

`SELECT * FROM employee_directory;`

It can also apply additional filtering:

`SELECT * FROM employee_directory WHERE department_id = 1;`

This distinction is important.

A regular view does not accept parameters in the manner of a function.

The consuming SQL statement supplies additional conditions.

When parameterized behavior is necessary, a database function can accept arguments and return filtered results.

The PostgreSQL implementation provides:

- `get_employees_by_department()`
- `get_department_payroll()`
- `evaluate_project_capacity()`

These functions demonstrate how views and reusable database routines can work together.

The Python implementation also uses parameterized queries to avoid constructing SQL statements from untrusted user input.

## 6. View Updatability

A view does not necessarily support direct modification.

Its ability to accept `INSERT`, `UPDATE`, or `DELETE` operations depends on its structure and the database system.

### 6.1 Automatically Updatable Views

A simple view based on a single table may be automatically updatable.

The PostgreSQL implementation defines `employee_edit_view` using a direct projection of the employee table.

An update through this view can modify the corresponding underlying employee record.

Underlying table constraints and permissions continue to apply.

### 6.2 Non-Updatable Views

Views involving operations such as aggregation, grouping, and complex joins generally cannot be updated automatically in a straightforward manner.

For example, updating a department's aggregate payroll does not identify which employee salary should change.

The database cannot infer the intended modification from the aggregate result.

### 6.3 INSTEAD OF Triggers

An `INSTEAD OF` trigger defines custom behavior when a modification is attempted through a view.

The PostgreSQL implementation uses an `INSTEAD OF UPDATE` trigger on `employee_department_edit`.

The trigger:

1. Receives the requested update.
2. Validates the new employee name.
3. Locates the underlying employee.
4. Updates the employee table.
5. Rejects unsupported operations.

The SQLite implementation uses a similar mechanism for its employee directory.

This demonstrates how controlled write operations can be introduced without exposing unrestricted direct table updates.

## 7. View Dependencies and Metadata

A view depends on the database objects referenced in its definition.

For example:

`high_workload_projects` depends on `project_workload`.

`project_workload` depends on:

- `projects`
- `departments`
- `assignments`

This creates a dependency graph.

Changes to an underlying object can affect dependent views.

Important dependency-management operations include:

- Identifying dependent views.
- Inspecting view definitions.
- Inspecting exposed columns.
- Detecting invalid dependencies.
- Managing object replacement.
- Evaluating the impact of schema modifications.

The PostgreSQL implementation uses system catalogs and `information_schema.views` to inspect database metadata.

The Python implementation uses SQLite's `sqlite_master` and `PRAGMA table_info`.

Metadata inspection is useful for database administration, documentation, automated validation, and migration planning.

## 8. Security and Access Control

Views can help implement controlled data access, but they do not automatically provide complete database security.

### 8.1 Column-Level Exposure

A view can expose selected columns without exposing unrelated information.

For example, `employee_directory` excludes employee salary.

This provides a restricted logical interface.

### 8.2 Row-Level Filtering

A view can filter records according to predefined conditions.

For example:

- Active employees only.
- Active projects only.
- Records belonging to a particular department.

Such filtering can support application-level data segregation.

### 8.3 Security Barrier

The PostgreSQL implementation defines `active_employee_public` with `security_barrier = TRUE`.

This option restricts certain optimizer transformations that could interfere with the intended evaluation of view conditions.

A security-barrier view does not replace privileges, row-level security, secure function design, or proper identity management.

### 8.4 Privilege Management

Production deployments should apply explicit privileges.

Important controls include:

- Restricting direct access to sensitive base tables.
- Granting only necessary view permissions.
- Separating reporting and administrative roles.
- Reviewing function execution privileges.
- Auditing access to sensitive information.
- Avoiding unsafe dynamic SQL.

The JavaScript and Java implementations also demonstrate role-based access evaluation at the application layer.

These simulations illustrate policy design rather than replacing database-native authorization.

## 9. Database View Execution and Performance

A regular view does not automatically make a query faster.

The database optimizer generally expands a regular view into its underlying query representation and evaluates the resulting plan.

Performance depends on the operations performed by that query.

### 9.1 Indexes

Indexes can improve access to underlying tables.

The PostgreSQL implementation creates indexes on:

- Employee department identifiers.
- Active employee department identifiers.
- Project department and status combinations.
- Assignment project identifiers.
- Assignment employee identifiers.
- Employee salary.

These indexes support common filtering and joining operations.

An index does not guarantee an improvement in every execution plan. Index selection depends on data distribution, query selectivity, statistics, and database cost estimates.

### 9.2 Query Plans

The SQL implementation uses:

`EXPLAIN (COSTS, VERBOSE)`

This reveals the planned operations used to execute a query.

Useful observations include:

- Sequential scans.
- Index scans.
- Join algorithms.
- Aggregation operations.
- Estimated row counts.
- Estimated execution costs.

Execution plans should be evaluated using representative data.

### 9.3 Nested View Performance

Nested views improve query reuse, but deep dependency chains can make queries harder to understand and maintain.

Repeated joins and aggregations may contribute to expensive execution plans.

View definitions should be designed around meaningful reusable interfaces rather than arbitrary layers of abstraction.

### 9.4 Materialized View Performance

Materialized views are useful when an expensive query is requested frequently and slightly delayed results are acceptable.

Typical applications include:

- Department payroll reports.
- Management dashboards.
- Project workload summaries.
- Historical reporting.
- Periodic analytical reports.

Refresh frequency should reflect business requirements and data freshness expectations.

## 10. Implementation Architecture

The five source files provide complementary implementations of view concepts.

| Deliverable | Implementation perspective | Main mechanisms |
|---|---|---|
| Python | Relational database simulation | SQLite, SQL views, metadata, transactions, triggers |
| JavaScript | Event-driven view registry | Maps, Sets, asynchronous evaluation, cache invalidation |
| C++17 | Domain-oriented reporting engine | STL containers, view evaluation, versioned caching |
| Java 17 | Enterprise service architecture | Records, repositories, policy objects, immutable results |
| PostgreSQL | Production-oriented relational implementation | Views, functions, triggers, materialized views, indexes |

### 10.1 Python Implementation

The Python implementation uses SQLite from the standard library.

Its `Database` class manages:

- Database connections.
- Table creation.
- Sample data.
- View definitions.
- Query execution.
- Transactions.
- View metadata.
- Execution-plan inspection.
- Controlled updates.

The script defines multiple actual SQLite views.

The `query_view()` method uses an explicit allowlist for view identifiers. This prevents arbitrary SQL identifiers from being supplied by consumers.

Values are passed through parameterized SQL statements.

The materialized-view demonstration uses a temporary table populated from a regular view. It is a simulation of cached query results, not a native SQLite materialized view.

### 10.2 JavaScript Implementation

The JavaScript implementation models a view registry over immutable in-memory relational datasets.

Its main components are:

- `DataStore`
- `ViewRegistry`
- View evaluator functions
- Dependency tracking
- Role-based access evaluation
- Asynchronous queries
- Cache refresh coordination

The registry uses `Map` to store definitions and cached results.

`Set` tracks dependencies and authorized roles.

When a base dataset changes, the store emits a `changed` event. Dependent cached views are invalidated.

The refresh mechanism shares an active promise for concurrent refresh requests.

This is an application-level model of view behavior. It does not execute PostgreSQL or SQLite statements.

### 10.3 C++17 Implementation

The C++ program models a repository of organizational data using strongly typed structures.

Its main classes are:

- `Repository`
- `ViewEngine`

The repository validates identifiers, relationships, duplicate assignments, and numerical constraints.

The view engine calculates:

- Active employee directories.
- Department statistics.
- Project workload.
- Filtered project results.
- Cached aggregate results.

The cache uses a repository version number.

A modification increments the version. The next materialized-view request detects the stale result and recomputes it.

The implementation demonstrates the relationship between source-data changes and cached reporting results.

### 10.4 Java 17 Implementation

The Java program follows an enterprise-oriented domain and service structure.

It uses:

- Records for immutable domain data.
- Enums for user roles and view classifications.
- A repository for base data.
- A policy object for access decisions.
- A service for view evaluation.
- Immutable collections for returned results.
- A version-based cache.

The `ViewService` separates view definitions from their consumption.

The `ViewPolicy` centralizes authorization decisions.

The repository performs validation before accepting domain records.

This separation makes the implementation easier to extend with persistence adapters, transaction boundaries, and enterprise authorization mechanisms.

## 11. Relational Data Model

The PostgreSQL implementation uses the following base relationships:

| Table | Primary key | Important relationships |
|---|---|---|
| departments | department_id | Parent of employees and projects |
| employees | employee_id | References departments |
| projects | project_id | References departments |
| assignments | assignment_id | References employees and projects |

The relationship structure is:

Departments
- Employees
- Projects

Projects
- Assignments

Employees
- Assignments

Assignments connect employees with projects through foreign keys.

The database applies primary keys, foreign keys, unique constraints, and check constraints to maintain relational integrity.

The views provide higher-level interfaces over this structure.

## 12. View Processing Workflow

The implemented database workflow can be represented as:

Base Tables
↓
CREATE VIEW
↓
View Definition
↓
View Dependencies
↓
Query Consumption
↓
Database Query Optimization
↓
Underlying Data Retrieval
↓
Result Set

For a materialized view:

Base Tables
↓
View Definition
↓
Initial Materialization
↓
Stored Query Results
↓
Subsequent Retrieval
↓
Explicit Refresh
↓
Updated Stored Results

The important distinction is that regular views evaluate their definitions when queried, while materialized views retrieve previously stored results until refreshed.

## 13. Validation and Failure Conditions

The implementations include representative validation and failure-handling mechanisms.

| Failure condition | Expected handling |
|---|---|
| Unknown view | Reject the request |
| Invalid dependency | Reject view registration |
| Missing department | Reject invalid relational references |
| Negative salary | Reject through validation or database constraint |
| Duplicate assignment | Reject through uniqueness enforcement |
| Unauthorized role | Reject access |
| Invalid query parameters | Raise validation errors |
| Invalid employee update | Reject modification |
| Stale materialized result | Recompute or refresh |
| Missing referenced record | Report a domain or integrity failure |

The PostgreSQL script demonstrates database-level constraints.

The Python implementation demonstrates exceptions and transactional rollback.

The JavaScript implementation demonstrates asynchronous failures and dependency invalidation.

The C++ implementation demonstrates exception-based validation.

The Java implementation separates repository validation from authorization policies.

## 14. Important Technical Distinctions

| Concept | Meaning |
|---|---|
| Base table | Stores underlying relational data |
| Regular view | Stores a reusable query definition |
| Materialized view | Stores the result of a query |
| Simple view | Presents a relatively direct table projection |
| Complex view | Combines joins, expressions, or aggregations |
| Nested view | References another view |
| Updatable view | Supports modification of underlying data under defined rules |
| INSTEAD OF trigger | Implements custom modification behavior through a view |
| View dependency | Relationship between a view and referenced objects |
| View abstraction | Separates consumers from underlying table complexity |
| View refresh | Recalculates stored materialized results |
| Security-barrier view | Restricts certain optimizer transformations to preserve security conditions |

These concepts are related but not interchangeable.

A view is a logical query interface. A materialized view is a stored query result. An updatable view provides a modification pathway. A security-barrier view addresses a particular class of query-optimization security concerns.

## 15. Limitations and Production Considerations

The implementations are educational, executable models of database-view behavior.

Several production considerations remain important.

- The Python example uses SQLite and does not reproduce every PostgreSQL feature.
- The JavaScript implementation evaluates in-memory datasets rather than executing database SQL.
- The C++ implementation uses vectors and repeated scans for clarity. Larger datasets would benefit from indexed lookup structures and grouped aggregation.
- The Java implementation uses an in-memory repository rather than a persistent database.
- The PostgreSQL materialized view requires an appropriate refresh strategy.
- Application-level role checks do not replace database permissions.
- Regular views can still produce expensive queries.
- Deeply nested views can increase maintenance complexity.
- Schema changes must account for dependent database objects.
- Materialized results require explicit freshness management.

For larger reporting workloads, indexes, query plans, materialized views, refresh policies, and access-control boundaries should be evaluated together.

## 16. Complexity and Performance Characteristics

The educational implementations use different strategies.

| Operation | Typical complexity |
|---|---|
| Direct view retrieval | Depends on the underlying query |
| Employee filtering | O(n) without an appropriate index |
| Department aggregation using repeated scans | O(d × e) |
| Project workload using repeated assignment scans | O(p × a) |
| Indexed lookup | Approximately O(log n) for a B-tree lookup |
| Hash-based grouping | Expected O(n) |
| Materialized result retrieval | Depends on result size and access path |
| Full materialized refresh | Depends on the underlying query |

Here:

- `n` represents the number of source records.
- `d` represents departments.
- `e` represents employees.
- `p` represents projects.
- `a` represents assignments.

The C++ and Java examples prioritize explicit domain logic. The JavaScript implementation demonstrates event-driven cache management. The PostgreSQL implementation delegates relational optimization to the database engine.

## 17. Practical Applications

Database views are useful in systems where multiple consumers need consistent representations of the same underlying data.

Representative applications include:

- Employee management systems.
- Financial reporting.
- Enterprise dashboards.
- Project management systems.
- Inventory reporting.
- Customer relationship management.
- Operational analytics.
- Data access abstraction.
- Business intelligence.
- Regulatory reporting.

Their value comes from reusable query definitions, controlled data exposure, simplified reporting interfaces, and separation between application consumption and relational storage.
