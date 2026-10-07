# SELF JOIN: Hierarchical Employee-Manager Relationships

## Topic Scope

A self join is a relational operation in which a table is joined to itself. The technique is especially useful when rows in a table represent entities that can relate to other rows of the same entity type.

Employee-manager data is a classic example. An employee row contains a `manager_id` that points to another row in the same `employee` table. The employee and manager are therefore not stored in separate entity tables. They are two roles played by rows from the same table.

The central relationship is:

`employee.manager_id -> employee.employee_id`

A direct employee-manager query can then use two aliases of the same table:

`employee AS e JOIN employee AS m ON e.manager_id = m.employee_id`

The two aliases are important because the database needs to distinguish the row representing the employee from the row representing that employee's manager.

The six implementations approach this relationship from different technical perspectives. Python builds a validated hierarchy model, JavaScript adds event-driven hierarchy changes, C++ implements a technical hierarchy engine, Java models an enterprise-oriented domain service, SQL implements the relational design directly, and this README connects the mechanisms without treating them as interchangeable.

## Core Relational Model

A compact employee table can contain fields such as:

| Column | Role |
|---|---|
| `employee_id` | Unique identifier for the employee |
| `employee_name` | Employee's name |
| `job_title` | Current organizational role |
| `manager_id` | Identifier of another employee who manages this employee |
| `department` | Organizational department |
| `annual_salary` | Compensation used by reporting examples |
| `is_active` | Whether the employee is currently active |

The important column is `manager_id`.

For a normal employee, `manager_id` contains another employee's `employee_id`. For a root employee such as a chief executive, `manager_id` can be `NULL`.

This makes the table a directed hierarchy. Each non-root employee points upward to one immediate manager.

A simplified representation is:

`Anita -> Rahul -> Vikram -> Arjun -> Ishaan`

Here each arrow follows the `manager_id` relationship upward from employee to manager.

## Why a SELF JOIN Is Required

Suppose employee 8 belongs to manager 4.

A normal query can retrieve employee 8:

`SELECT * FROM employee WHERE employee_id = 8;`

That does not yet provide the manager's name because the manager is stored as another row in the same table.

A self join resolves that relationship:

`SELECT e.employee_name, m.employee_name AS manager FROM employee AS e JOIN employee AS m ON e.manager_id = m.employee_id;`

The alias `e` means "employee role" and `m` means "manager role."

The database therefore evaluates two logical copies of the same table:

- `e` supplies the employee.
- `m` supplies the manager.
- `e.manager_id` identifies the matching `m.employee_id`.

This is fundamentally different from joining an employee table to a separate manager table because there is only one entity table.

## Immediate Relationships Versus the Full Hierarchy

A self join is particularly natural for an immediate relationship.

For example:

`Sana -> Vikram`

can be obtained with one self join.

But a complete management chain may contain several levels:

`Sana -> Vikram -> Rahul -> Anita`

A single self join does not automatically traverse all four levels. Each additional fixed level would require another join.

For arbitrary hierarchy depth, recursive techniques are more appropriate. PostgreSQL supports recursive common table expressions, which are demonstrated in the SQL implementation.

This distinction is important:

| Requirement | Appropriate mechanism |
|---|---|
| Employee and immediate manager | SELF JOIN |
| Employees directly reporting to one manager | Filter on `manager_id` |
| Managers with direct-report counts | SELF JOIN with aggregation |
| Complete hierarchy of arbitrary depth | Recursive CTE |
| Management path | Recursive traversal |
| Nearest common manager | Ancestor traversal |
| Preventing invalid references | Foreign key |
| Preventing direct self-management | `CHECK` constraint |
| Preventing longer cycles | Application or specialized database validation |

## Employee-Manager SELF JOIN Semantics

The Python, C++, JavaScript, and Java programs represent the same fundamental relationship with an employee object containing a manager identifier.

The conceptual operation is:

`employee.manager_id == manager.employee_id`

This is the in-memory equivalent of the SQL join predicate.

An inner self join excludes root employees because a root has no manager row to match.

A left self join preserves root employees:

`FROM employee AS e LEFT JOIN employee AS m ON e.manager_id = m.employee_id`

For a root, the manager-side columns are `NULL`.

This difference matters in organizational reporting. A report showing every employee normally needs a left self join, while a report showing only employees who have managers can use an inner self join.

## Python Implementation

The Python implementation uses an `Employee` dataclass and an `Organization` class.

The `Organization` stores employees by ID, allowing manager references to be resolved efficiently in memory. The `manager_id` field has the same semantic role as the database foreign key.

The `manager_employee_pairs()` method explicitly models the immediate self join. For every employee with a manager, it resolves the manager through the same employee collection and produces an employee-manager pair.

The `direct_reports()` method performs the inverse relationship. Instead of following an employee's manager upward, it searches for employees whose `manager_id` equals the selected manager's ID.

The hierarchy implementation goes beyond the immediate relationship. `chain_to_root()` follows:

`employee -> manager -> manager's manager -> root`

The `common_manager()` method uses ancestor chains to find a shared manager.

The Python model also demonstrates an important integrity problem. A foreign-key-like reference alone is not enough to guarantee an acyclic hierarchy. A relationship such as:

`A -> B -> C -> A`

contains valid-looking identifiers but does not represent a tree.

The Python implementation therefore validates both missing managers and cycles.

The `move_employee()` operation also performs rollback-style behavior. It changes the manager temporarily, validates the resulting hierarchy, and restores the old manager if the new relationship would create an invalid structure.

This is useful when modeling organizational changes in application code because a manager change should not leave the in-memory structure partially invalid.

## JavaScript Implementation

The JavaScript implementation represents employees with an `Employee` class and the organization with an `Organization` class.

Its `selfJoinRows()` method constructs employee-manager projections by resolving each employee's `managerId` through the same `Map` that contains every employee.

The implementation also demonstrates JavaScript-specific event-driven behavior.

`HierarchyEventProcessor` emits an `employee.managerChanged` event after a successful manager change. This represents a realistic application boundary where an organizational change could trigger downstream processing such as cache refreshes, audit records, notification handling, or reporting updates.

The event mechanism is intentionally separate from the relational relationship itself. The SELF JOIN identifies who the manager is. The event mechanism represents what an application might do after that relationship changes.

The JavaScript implementation also uses optional chaining when constructing reports so that a root employee can be represented without an artificial manager object.

Cycle prevention remains an explicit responsibility because changing a manager can create an invalid graph even when every individual manager identifier exists.

## C++ Hierarchy Engine

The C++ program treats the organization as a technical hierarchy engine.

`Organization` stores employees in an `unordered_map<int, Employee>`, making employee lookup by identifier efficient.

The `selfJoin()` method directly models the relational operation by returning pairs of employee and manager objects.

The implementation separates several hierarchy operations:

- `directReports()` finds immediate children.
- `managementChain()` follows manager references toward the root.
- `hierarchyDepth()` calculates the number of management relationships above an employee.
- `nearestCommonManager()` finds a shared ancestor.
- `descendants()` traverses downward through direct reports.
- `moveEmployee()` changes a relationship while preserving hierarchy integrity.
- `renderChart()` converts the parent-child structure into an organization chart.

The C++ case study uses both upward and downward traversal because hierarchical applications frequently need both directions.

The upward direction is natural from the row representation:

`employee -> manager`

The downward direction requires discovering rows whose `manager_id` points to the current employee:

`manager -> direct reports`

The C++ implementation explicitly checks for cycles during manager traversal. It also prevents assigning a descendant as a manager because that would introduce a loop.

The implementation uses C++17 features such as `std::optional`, structured bindings, `unordered_map`, `unordered_set`, and lambda expressions. These features support the domain model without requiring external libraries.

## Java Enterprise Domain Model

The Java implementation emphasizes explicit domain modeling.

The `Employee` record represents immutable employee data. Its constructor performs basic domain validation such as positive identifiers, non-empty names, and non-negative salaries.

The `OrganizationRepository` owns the employee collection and controls hierarchy changes. This separation is useful in an enterprise application because callers should not directly mutate relationships without validation.

`EmployeeManagerView` is a projection representing the result of the self join. It contains an employee and the corresponding manager.

`DepartmentReport` represents another reporting projection. It does not expose the entire employee entity when the report only requires employee name, title, and manager name.

The `changeManager()` method validates several conditions:

- The employee must exist.
- A new manager must exist.
- An employee cannot manage themselves.
- A descendant cannot become the employee's manager.
- The resulting hierarchy must remain acyclic.

Java's `Optional` is used when an employee may not have a manager. This maps naturally to the database concept of a nullable `manager_id`.

The `HierarchyService` provides reporting operations over the repository. This separates domain storage and validation from application-level reporting behavior.

The design demonstrates why a self-referencing relationship should not be treated as merely a query trick. In enterprise software, the same relationship affects validation, state transitions, reporting, traversal, and data integrity.

## SQL Data Model

The PostgreSQL implementation creates an `organization.employee` table with a self-referencing foreign key:

`FOREIGN KEY (manager_id) REFERENCES employee(employee_id)`

This enforces referential integrity. A manager ID cannot reference an employee that does not exist.

The database also uses:

`CHECK (manager_id IS NULL OR manager_id <> employee_id)`

This prevents direct self-management.

The `idx_employee_manager_id` index supports queries that search for direct reports:

`WHERE manager_id = 5`

This is important because a hierarchy application frequently performs the inverse of the employee-to-manager lookup.

For example, finding Priya's direct reports requires locating rows whose `manager_id` equals Priya's employee ID.

The composite index on `(department, manager_id)` supports combined department and manager filtering patterns demonstrated by the reporting queries.

## SQL SELF JOIN Queries

The primary immediate relationship query is:

`FROM employee AS e JOIN employee AS m ON e.manager_id = m.employee_id`

The query can expose fields from both roles:

`e.employee_name AS employee`

and:

`m.employee_name AS manager`

The same table is therefore used twice without duplicating the underlying data.

A left self join is used when root employees must remain visible.

The SQL implementation also demonstrates salary comparison between employee and manager. Because both rows come from the same table, values such as employee salary and manager salary can be compared directly.

Manager workload can be measured with aggregation:

`COUNT(e.employee_id)`

where `m` is the manager-side alias and `e` is the employee-side alias.

This produces useful organizational metrics such as the number of direct reports for each manager.

## Recursive Hierarchy Queries

A SELF JOIN is ideal for one level of hierarchy.

When the requirement becomes "show every employee under the CEO regardless of depth," recursive traversal is required.

The PostgreSQL script uses:

`WITH RECURSIVE hierarchy AS (...)`

The initial query selects root employees.

The recursive part joins employees to the already discovered hierarchy rows:

`child.manager_id = parent.employee_id`

The recursive query then calculates depth.

For example:

`Anita` has depth `0`.

`Rahul` has depth `1`.

`Vikram` has depth `2`.

`Arjun` has depth `3`.

`Ishaan` has depth `4`.

The same mechanism can construct a management path such as:

`Anita -> Rahul -> Vikram -> Arjun -> Ishaan`

This illustrates the boundary between a normal self join and recursive hierarchy processing.

## Referential Integrity and Hierarchy Integrity

These are related but different concerns.

A foreign key answers:

"Does this manager ID identify an existing employee?"

It does not necessarily answer:

"Does the complete graph remain acyclic?"

For example, these references could all point to existing rows:

`A.manager_id = B`

`B.manager_id = C`

`C.manager_id = A`

Every reference exists, but the structure contains a cycle.

The Python, JavaScript, C++, and Java implementations therefore perform explicit cycle detection.

The SQL design prevents missing managers and direct self-management at the database layer. Longer cycle detection is more complex and generally requires additional application or database logic when arbitrary hierarchy changes are allowed.

This distinction is important for production systems because referential integrity and graph integrity solve different problems.

## Root Employees

A root employee has:

`manager_id IS NULL`

The SQL left self join makes this visible by returning `NULL` for the manager-side columns.

The organization chart implementations use the same rule to identify roots.

A hierarchy normally expects one or more roots depending on the business model. A single-company structure may require exactly one root, while a group of independent business units may legitimately contain multiple roots.

Whether multiple roots are valid is a business constraint rather than an inherent property of the SELF JOIN technique.

## Direct Reports Versus Descendants

A direct report has exactly one relationship to the manager:

`employee.manager_id = manager.employee_id`

A descendant can be several levels below the manager.

If Anita manages Rahul, Rahul manages Vikram, and Vikram manages Arjun, then:

- Rahul is Anita's direct report.
- Vikram is Anita's descendant.
- Arjun is Anita's descendant.
- Arjun is not Anita's direct report.

This distinction affects SQL queries, application APIs, performance expectations, and organizational reporting.

A direct-report query can use one self join or a simple `WHERE manager_id = ...`.

A descendant query requires recursive traversal or repeated hierarchy processing.

## Finding a Common Manager

Two employees may belong to different branches of the same organization.

For example:

`Arjun -> Vikram -> Rahul -> Anita`

and:

`Karan -> Priya -> Rahul -> Anita`

The nearest common manager is Rahul.

The implementations determine this by constructing ancestor chains and finding the closest shared employee.

This is useful for organizational reporting, escalation routing, authorization scopes, and determining the smallest organizational unit containing two employees.

The operation is conceptually a lowest-common-ancestor problem on a hierarchy.

## Manager Changes

Changing an employee's manager is more than a simple update.

The basic database operation is:

`UPDATE employee SET manager_id = ... WHERE employee_id = ...`

but a production system must consider whether the new relationship is valid.

The implementations protect against:

- assigning an employee to themselves,
- assigning a non-existent manager,
- assigning a descendant as manager,
- creating a longer management cycle,
- leaving application state inconsistent after a failed change.

The SQL transaction demonstrates how a manager change can be grouped with verification.

The application implementations use a similar rollback idea by restoring the old manager when validation fails.

## Performance Considerations

A direct self join is generally efficient when the relevant identifiers are indexed.

The primary key index on `employee_id` supports manager-side lookup.

An index on `manager_id` supports finding direct reports.

Without a suitable `manager_id` index, a query repeatedly searching for all employees under a manager may need to scan many employee rows.

Hierarchy depth also matters.

Following a manager chain from one employee is proportional to the number of management levels above that employee. If the hierarchy becomes unusually deep, repeated traversal can become expensive.

Recursive database queries should therefore be tested against realistic organizational sizes and depth.

For frequently requested complete hierarchies, systems may use cached paths, materialized structures, closure tables, or other specialized hierarchical representations. Those are alternative modeling strategies rather than requirements for a basic SELF JOIN.

## Edge Cases

### Root employee

A root has no manager, so `manager_id` is `NULL`. An inner self join omits the root, while a left self join retains it.

### Missing manager

An employee references an identifier that does not exist. The PostgreSQL foreign key rejects this state.

### Direct self-management

An employee's `manager_id` equals their own `employee_id`. The database `CHECK` constraint rejects this state.

### Longer management cycle

Employees form a cycle through multiple manager references. Individual foreign keys can still be valid, so explicit cycle detection is required.

### Inactive employee

An inactive employee can remain in historical relationships while application reports may exclude inactive employees. The Python, JavaScript, and Java implementations distinguish stored relationships from active reporting.

### Multiple organizational roots

Multiple `NULL` manager references may be valid for a group containing separate organizational trees. A single-root requirement must be enforced separately if the business requires it.

### Manager change to a descendant

This is one of the most important hierarchy mutation failures. It converts a tree into a cycle and is explicitly rejected by the application implementations.

## Common Modeling Mistakes

### Treating manager as a separate entity table

If managers are employees, creating a duplicate manager table creates unnecessary duplication and makes employee identity harder to maintain.

A self-referencing foreign key keeps the employee identity in one place.

### Using employee names as relationships

Names are not stable identifiers. Two employees can share a name, and an employee's name can change.

The relationship should use a stable key such as `employee_id`.

### Assuming a foreign key prevents all hierarchy cycles

A foreign key validates reference existence. It does not automatically prove that a graph is acyclic.

### Confusing direct reports with all descendants

One self join identifies an immediate relationship. It does not automatically return every person below a manager.

### Using repeated fixed-depth joins for arbitrary organizations

A query containing one join for manager, another for manager's manager, and another for the next level is difficult to maintain when hierarchy depth changes.

Recursive traversal is more appropriate for arbitrary depth.

## Security and Data Integrity

Employee-manager relationships can influence authorization, approvals, access boundaries, reporting, and escalation. Incorrect hierarchy data can therefore have consequences beyond inaccurate reporting.

Database constraints should enforce basic structural integrity.

Application-level authorization should determine who is allowed to change a manager relationship.

A user who can view employee records should not automatically be assumed to have permission to modify reporting relationships.

Manager changes should be auditable in systems where organizational structure affects access, compensation, approvals, or compliance.

Sensitive employee attributes should also be exposed only to users and services that require them. The self join itself does not provide authorization; it only resolves a relational relationship.

## Practical Applications

The same employee-manager relationship supports many organizational queries:

- identifying an employee's immediate manager,
- listing all direct reports,
- constructing organization charts,
- calculating management depth,
- finding management chains,
- locating common managers,
- comparing employees with their managers,
- aggregating direct-report counts,
- generating department reports,
- determining escalation paths,
- analyzing organizational span of control.

The SQL SELF JOIN is the fundamental mechanism for immediate relationships, while recursive processing handles arbitrary hierarchy depth.

## Relationship Between the Six Implementations

| Implementation | Primary technical perspective |
|---|---|
| Python | Validated in-memory hierarchy, traversal, cycle prevention, and manager changes |
| JavaScript | Hierarchy model combined with event-driven manager-change processing |
| C++ | Technical hierarchy engine with explicit traversal, graph validation, and performance discussion |
| Java | Enterprise-oriented domain model with records, repository boundaries, projections, and validation |
| PostgreSQL | Self-referencing relational schema, constraints, indexes, SELF JOIN queries, transactions, and recursive CTEs |
| README | Conceptual relationship between the implementations and the underlying relational model |

The implementations intentionally do not perform identical work. The SQL script demonstrates the relational operation directly, while the application implementations show what the same relationship looks like when it becomes part of a software system.

## Production Considerations

A production employee hierarchy should treat `employee_id` as a stable identifier and `manager_id` as a controlled relationship.

The database should enforce basic reference integrity. Application services should validate organizational rules that cannot be represented by a simple foreign key.

Manager changes should normally be transactional and auditable.

Queries for direct reports should be supported by an index on `manager_id`.

Queries that traverse arbitrary hierarchy depth should be tested with realistic data volumes and hierarchy shapes.

If the hierarchy is used for authorization, organizational reporting alone should not be treated as sufficient security enforcement. Authorization rules must explicitly define which users can view or modify data.

The key design principle remains simple: one employee table can represent both employees and managers, and a SELF JOIN resolves the immediate relationship by matching the employee's `manager_id` with another row's `employee_id`.
