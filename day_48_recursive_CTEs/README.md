# Recursive CTEs and Hierarchical Organizational Trees

## Scope

This repository models hierarchical organizational data with PostgreSQL `WITH RECURSIVE` and complementary implementations in Python, JavaScript, C++17, and Java 17.

The central data structure is an adjacency list:

`employee_id -> manager_id`

A manager relationship identifies the immediate parent. Recursive processing derives information that is not stored directly, including hierarchy depth, complete management paths, descendants, ancestors, and subtree sizes.

The four important ideas are closely connected:

- `WITH RECURSIVE` provides the SQL mechanism for repeatedly applying a relationship.
- The recursive query has an anchor member that establishes the starting rows and a recursive member that expands already discovered rows.
- Hierarchical data uses those repeated parent-child relationships to represent organizational trees without storing every possible ancestor relationship.
- Organizational trees are a practical example because an employee can have one manager while a manager can have many direct reports.

The implementations deliberately approach the same domain from different technical perspectives rather than translating one program line by line into another language.

## Recursive CTE Mechanics

A recursive CTE has a self-referencing query structure. Conceptually, the execution begins with an anchor result:

`root employees`

The recursive member then finds children of those rows:

`current employee -> employees whose manager_id equals current employee_id`

The newly discovered rows become input to another recursive iteration until no new rows satisfy the recursive condition.

The SQL implementation uses this pattern:

`WITH RECURSIVE organization_tree AS (...)`

The anchor selects employees whose `manager_id IS NULL`. Those employees form the organizational roots.

The recursive member joins `organization_tree` back to `employees` using:

`child.manager_id = parent.employee_id`

This relationship is the defining operation of the organizational traversal.

The recursive result also carries state that is not stored directly in the employee table:

- `depth` records the distance from the anchor.
- `id_path` records every employee ID encountered along the route.
- `name_path` produces a human-readable management chain.

The path is useful for both presentation and cycle protection.

## Anchor and Recursive Members

The anchor query determines where recursion begins.

For the complete organization, the natural anchor is:

`WHERE manager_id IS NULL`

For a department-specific query, the anchor can instead identify one manager. The engineering query in the SQL file starts at the employee whose code is `ENG-DIR`.

This distinction matters because the same recursive relationship can answer different questions.

A company-wide hierarchy requires all roots. A department hierarchy requires a selected root. An upward management query starts from an employee and follows `manager_id` toward the executive level.

The recursive member is different for downward and upward traversal.

Downward traversal joins a discovered employee to children:

`child.manager_id = parent.employee_id`

Upward traversal joins the current employee's `manager_id` to another employee's `employee_id`.

This makes recursive CTEs useful for both directions of an adjacency-list hierarchy.

## Organizational Trees

The employee table intentionally stores only the immediate manager:

| Column | Purpose |
|---|---|
| `employee_id` | Stable relational identifier |
| `employee_code` | Business identifier |
| `employee_name` | Person represented by the node |
| `job_title` | Organizational role |
| `manager_id` | Immediate parent in the hierarchy |
| `hired_on` | Domain attribute independent of the tree |
| `active` | Current employment state |

An employee does not need separate columns for CEO, director, manager, and team lead. Those relationships can be derived recursively from `manager_id`.

For example:

`Asha -> Ravi -> Arjun -> Maya`

represents Asha's upward management chain.

The same structure can produce a downward hierarchy:

`Maya -> Arjun -> Ravi -> Asha`

This is the main advantage of an adjacency-list representation when organizational relationships change regularly.

## Depth

Depth measures how far a row is from the recursive anchor.

A root has depth `0`.

A direct report has depth `1`.

A report of that direct report has depth `2`.

The recursive member increments depth:

`parent.depth + 1`

Depth supports practical queries such as identifying seniority levels within a selected subtree, displaying an indented organization chart, or determining how deeply nested a reporting structure has become.

Depth is not the same as organizational seniority. It is a structural distance within the selected recursive traversal.

## Paths

The SQL implementation uses PostgreSQL integer arrays:

`ARRAY[employee_id]`

Each recursive expansion appends the child ID:

`parent.path || child.employee_id`

A path such as:

`{1,2,4,6}`

represents a route from an organizational root through several managers to an employee.

Path data has three important uses.

It makes hierarchy ordering deterministic when results are ordered by the path.

It allows a query to reconstruct the complete ancestry of a row.

It provides a cycle-detection mechanism by preventing an employee already present in the path from being visited again.

The Python, C++, and Java implementations use the same conceptual state but represent the path with language-specific collections.

## Cycle Detection

A valid organizational tree should not contain:

`A -> B -> A`

or a longer loop such as:

`A -> B -> C -> A`

The SQL queries use path membership checks such as:

`NOT child.employee_id = ANY(parent.path)`

This prevents recursive expansion from repeatedly entering a node already encountered on the current route.

The application implementations also validate the hierarchy before traversal. They use explicit visitation states or ancestry paths to identify cycles.

Cycle prevention is important because recursion without a termination condition can produce an invalid result or consume excessive resources.

A foreign key alone does not prevent a cycle. A foreign key proves that a referenced manager exists, but it does not prove that the manager relationship eventually reaches a root.

## Recursive Aggregation

Recursive traversal can be combined with ordinary SQL aggregation.

The subtree-size query generates pairs of:

`root_id -> member_id`

Every employee becomes the root of a recursive subtree, and descendants are repeatedly added to that root.

The outer aggregation then counts members for each root.

This produces information such as:

`Arjun -> number of employees under Arjun`

without storing a permanent descendant count.

This pattern is useful when the hierarchy changes frequently because the result is derived from current parent relationships.

The trade-off is that recursive aggregation can be substantially more expensive than reading a precomputed hierarchy representation for very large or frequently queried trees.

## Python Implementation

The Python program uses an `Employee` dataclass and an `Organization` class.

The `children` dictionary converts the adjacency-list representation into an efficient parent-to-children lookup structure. This allows traversal to locate direct reports without repeatedly scanning every employee.

`recursive_cte_style()` intentionally models the state carried by a recursive SQL query. Each traversal item contains:

- employee ID
- depth
- path
- readable path text

The implementation uses a queue to perform breadth-first traversal. This makes the resulting hierarchy naturally ordered by depth.

`ancestors()` demonstrates the reverse direction by repeatedly following `manager_id`.

`subtree_sizes()` uses reverse traversal so descendants are processed before their managers. Each employee initially contributes one node to its own subtree, then its accumulated size is transferred to its parent.

The validation logic checks missing managers, self-management, and cycles before traversal.

The generator-based `recursive_query_equivalent()` demonstrates a separate design choice: hierarchical results can be consumed lazily instead of materializing the complete result immediately.

## JavaScript Implementation

The JavaScript implementation emphasizes asynchronous and event-driven processing.

`OrganizationTree` stores employees in a `Map` and direct reports in another `Map`. This mirrors the relationship between a relational adjacency list and an application-level lookup structure.

The `walk()` method is an asynchronous generator.

A caller can consume it with:

`for await (const node of organization.descendants(4))`

This is useful when a hierarchy is large or when traversal results need to be streamed into another asynchronous operation.

The implementation also supports early termination. The demonstration stops after two streamed descendants without constructing the remaining subtree.

This differs from the Python implementation's emphasis on recursive-state simulation. The JavaScript version focuses on asynchronous consumption and event-driven processing of hierarchical results.

## C++ Case Study

The C++ program models an organizational hierarchy as a governance-oriented in-memory system.

`GovernanceHierarchy` owns the employee records and an index from manager IDs to child IDs.

The constructor performs structural validation before the hierarchy can be queried. Missing managers, duplicate identifiers, and self-management are rejected.

Cycle detection uses three visitation states:

`UNVISITED`

`ACTIVE`

`COMPLETE`

An `ACTIVE` node encountered again indicates that the current management chain has returned to an ancestor.

The traversal state is represented by `HierarchyNode`, containing the employee ID, depth, and complete path.

The program uses `std::queue` for breadth-first hierarchy traversal. The path is copied when a child is added so that each traversal node retains its own ancestry.

The subtree-size calculation reverses the traversal and accumulates each employee's completed subtree into its manager. This demonstrates a post-order dependency even though the initial traversal is breadth-first.

The case study therefore separates three concerns: validating the tree, traversing it, and deriving aggregate structural information.

## Java Enterprise-Oriented Model

The Java implementation models the hierarchy as a small domain service.

`Employee` is a Java record, which is appropriate because an employee hierarchy node is primarily immutable domain data in this example.

`TraversalNode` represents recursive state independently from the employee itself. This prevents calculated depth and path information from being mixed into the stored employee record.

`OrganizationService` owns the relationship indexes and exposes operations for traversal, ancestor lookup, and subtree-size calculation.

The `VisitState` enum makes cycle detection explicit rather than representing it with arbitrary numeric flags.

The Java implementation uses `List.copyOf()` when returning paths and results. This prevents callers from accidentally modifying traversal state after it has been produced.

This design reflects an enterprise application concern: domain state and derived traversal state should remain separate.

## PostgreSQL Data Model

The SQL schema uses a self-referencing foreign key:

`employees.manager_id -> employees.employee_id`

The foreign key ensures referential integrity. A manager must exist before an employee can reference that manager.

The `employees_not_self_managed` check constraint prevents the simplest invalid cycle.

The `employees_manager_idx` index supports the recursive join because recursive expansion repeatedly searches for rows whose `manager_id` equals the current employee.

The database therefore enforces basic structural integrity while recursive queries derive the higher-level hierarchy.

## Database-Level Cycle Validation

The SQL script also defines `validate_manager_chain()`.

The trigger executes when a manager relationship is inserted or changed. It walks upward from the proposed manager and records visited IDs.

If it encounters the employee being modified, the proposed relationship creates a cycle.

This is important because the self-reference foreign key cannot detect multi-row cycles.

A database design that allows arbitrary organizational reassignment should consider whether hierarchy validation belongs exclusively in application code or must also be enforced at the database boundary.

The trigger demonstrates the latter approach.

## Transactions and Hierarchy Changes

Manager reassignment is a structural mutation. A partially completed reassignment could leave application-level operations inconsistent if several related updates are expected to succeed together.

The SQL script therefore demonstrates transactional control with `BEGIN`, `COMMIT`, `SAVEPOINT`, and `ROLLBACK`.

The principle is that a hierarchy mutation and its integrity checks should be treated as one atomic operation when the surrounding business operation requires atomicity.

## Recursive CTEs Versus Ordinary Joins

An ordinary self-join can retrieve a fixed number of levels.

For example, joining employees once can retrieve direct reports. Joining twice can retrieve two levels of reports.

That approach becomes cumbersome when the depth is unknown.

A recursive CTE expresses the repeated relationship once and allows PostgreSQL to continue expanding the hierarchy until the recursive member produces no additional rows.

The distinction is especially important for organizations where one department might contain three levels while another contains seven.

## Recursive CTEs Versus Stored Hierarchy Columns

A hierarchy can be represented using alternatives such as materialized paths, nested sets, closure tables, or database-specific hierarchical features.

An adjacency list with a recursive CTE is particularly straightforward when each entity has one parent and relationships change regularly.

Its main cost is recursive computation during queries.

A materialized path can make ancestor and descendant lookups faster in some workloads but introduces maintenance requirements when a subtree is moved.

A closure table stores every ancestor-descendant relationship explicitly and can make hierarchical queries very fast, at the cost of additional storage and more complicated mutation logic.

The implementations in this repository specifically demonstrate the adjacency-list plus recursive-CTE approach.

## Edge Cases

A hierarchy implementation must account for malformed data rather than assuming every parent relationship is valid.

A missing manager is a referential-integrity violation.

An employee managing itself is a direct cycle.

Two employees managing each other form a two-node cycle.

A longer loop can be harder to notice because every referenced manager may exist even though the hierarchy never reaches a root.

An empty organization has no recursive rows.

Multiple root employees represent a forest rather than a single tree. The SQL anchor naturally supports this by selecting every row whose `manager_id` is null.

A selected root that does not exist should be rejected by application-level traversal functions rather than silently producing an empty result.

## Performance Considerations

For an adjacency-list organization with `n` employees and a tree traversal that visits every reachable employee, the logical traversal work is approximately `O(n)` when child lookup is indexed or represented by an efficient in-memory map.

The database needs efficient access to `manager_id`, which is why the SQL implementation creates `employees_manager_idx`.

Path construction introduces additional memory proportional to the depth of each path. Very deep hierarchies can therefore produce more work than shallow trees with the same number of nodes.

Recursive aggregation can also multiply work because a query that calculates the subtree for every employee may revisit many descendant relationships.

For large organizations with heavy reporting workloads, query plans should be examined rather than assuming that recursive SQL is automatically inexpensive.

## Security and Integrity

Hierarchical data can encode sensitive organizational information.

Access to a recursive query should therefore follow the same authorization rules as the underlying employee data. A recursive query should not become an unintended mechanism for exposing managers or subordinates that the requesting user cannot normally view.

Database constraints are important because application validation alone can be bypassed by another database client, administrative operation, migration, or integration service.

The schema therefore combines foreign-key enforcement, a self-management check, trigger-based cycle detection, and transactions.

## Debugging Recursive Queries

When debugging a recursive CTE, inspect the anchor independently before inspecting recursion.

If the anchor returns no rows, the recursive member cannot produce anything.

If the anchor returns too many rows, every branch of the resulting hierarchy may be duplicated.

If depth grows unexpectedly, inspect the parent-child join and cycle condition.

Path arrays are particularly useful during debugging because they expose the exact traversal route that produced a row.

A practical diagnostic query can expose:

`employee_name`, `manager_id`, `depth`, and `path`

instead of immediately applying aggregation.

This makes incorrect relationships visible before they are hidden by counts or grouped results.

## Practical Relationship Between the Implementations

The five executable implementations represent the same domain while emphasizing different mechanisms.

| Implementation | Primary technical emphasis |
|---|---|
| Python | Explicit recursive-query state, validation, traversal, ancestors, and subtree aggregation |
| JavaScript | Async generators, streaming traversal, early termination, and event-style processing |
| C++ | A validated hierarchy engine with explicit traversal state, paths, and post-order aggregation |
| Java | Immutable domain records, typed traversal state, service-oriented modeling, and validation |
| PostgreSQL | Self-referencing relational design, `WITH RECURSIVE`, recursive aggregation, constraints, triggers, and transactions |

The shared concept is not the programming syntax. It is the repeated traversal of a parent-child relationship while carrying state from one level to the next.

That is the core mechanism that makes recursive CTEs effective for organizational trees.
