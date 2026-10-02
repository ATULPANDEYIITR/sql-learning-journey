# Relationships: One-to-One, One-to-Many, and Many-to-Many

## Introduction

A relationship describes how records in one entity set are associated with records in another entity set.

The three fundamental relationship patterns in this project are:

- **One-to-one:** one record on one side is associated with at most one record on the other side.
- **One-to-many:** one parent record can be associated with multiple child records.
- **Many-to-many:** multiple records on each side can be associated with multiple records on the opposite side.

The distinction is not merely conceptual. Each cardinality requires a different data-modeling strategy, different constraints, and different traversal behavior.

The implementations use a common domain model involving people, profiles, organizational groups, work items, and skills or capabilities. The entities are deliberately related in different ways so that the structural difference between the relationship types remains visible.

## Relationship Model

The core model can be represented as:

    Employee
       |
       | one-to-one
       v
    EmployeeProfile

    Employee
       |
       | one-to-many
       v
    Department
       |
       | one-to-many
       v
    WorkItem

    Employee
       |
       | many-to-many
       v
    Capability
       ^
       |
    EmployeeCapability

The one-to-one example uses an employee and an employee profile.

The one-to-many example uses a department and its work items. A department can contain many work items, while each work item belongs to one department.

The many-to-many example connects employees and capabilities. An employee can have many capabilities, and a capability can belong to many employees. The relationship is represented by the `EmployeeCapability` association.

## One-to-One Relationships

A one-to-one relationship means that a record on one side corresponds to no more than one record on the other side.

The Python implementation models this as `User` and `UserProfile`. The JavaScript implementation uses `Employee` and `EmployeeProfile`, while the C++ case study uses `Employee` and `EmployeeProfile`.

A foreign key by itself does not necessarily enforce one-to-one cardinality. If multiple profile records could contain the same `employee_id`, the relationship would actually be one-to-many from employee to profile.

The critical additional rule is uniqueness.

Conceptually, the profile structure is:

    profile_id       PRIMARY KEY
    employee_id      FOREIGN KEY -> employee.id
    employee_id      UNIQUE

The `UNIQUE` condition prevents two profiles from referencing the same employee.

The in-memory implementations represent this rule through mappings such as `profileByEmployee`. Before creating a profile, the program checks whether the employee already has a profile.

### Optional versus mandatory participation

The examples implement a common form of one-to-one cardinality in which a user may initially have no profile, but an existing user cannot have more than one profile.

This means the relationship is effectively:

    Employee 1 ---- 0..1 EmployeeProfile

The profile itself must reference an existing employee. That foreign-key direction is important because it prevents an orphan profile.

A different application could require every employee to have a profile. That would be a stronger participation constraint and normally requires additional database-level enforcement or controlled transaction logic.

### Why a unique foreign key matters

Consider two profile rows:

    profile_id | employee_id
    -----------+------------
    101        | 1
    102        | 1

The foreign-key requirement is satisfied because employee `1` exists, but the one-to-one requirement has been violated.

Adding uniqueness changes the valid state to:

    profile_id | employee_id
    -----------+------------
    101        | 1

A second row referencing employee `1` is rejected.

## One-to-Many Relationships

A one-to-many relationship allows one parent to have many children while each child belongs to one parent.

The project models:

    Department 1 ---- many WorkItem

The foreign key belongs on the many side:

    work_item.department_id -> department.id

Several work items can therefore contain the same department identifier:

    work_item_id | department_id
    -------------+--------------
    301          | 201
    302          | 201
    303          | 201

This is valid because there is no uniqueness constraint on `department_id`.

The parent can have zero children, one child, or many children.

### Why the foreign key belongs on the many side

If the parent stored one child identifier, it would not naturally represent an arbitrary number of children. The child-side foreign key provides a direct representation:

    Department 201
        |
        +-- WorkItem 301
        +-- WorkItem 302
        +-- WorkItem 303

Each work item stores the identity of its parent department.

This also makes child-to-parent lookup straightforward. Given work item `302`, the application reads its `department_id` and retrieves department `201`.

### Parent deletion

The implementations deliberately demonstrate a restrictive deletion policy.

A department containing work items cannot be deleted until its child records are removed.

This models behavior similar to a restrictive foreign-key policy:

    DELETE Department 201
        |
        +-- WorkItem 301 exists
        +-- WorkItem 302 exists
        |
        -> reject deletion

After the dependent work items have been removed, the department can be deleted.

This is different from cascading deletion. A cascading policy would automatically remove dependent children when the parent is deleted. The correct choice depends on the business meaning of the relationship and the consequences of losing child records.

## Many-to-Many Relationships

A many-to-many relationship occurs when both sides can participate in multiple relationships.

The project uses:

    Employee <----> Capability

An employee may have several capabilities:

    Atul -> SQL
    Atul -> Python
    Atul -> Cybersecurity

The same capability may belong to multiple employees:

    SQL -> Atul
    SQL -> Maya
    SQL -> Liam

A single foreign key cannot represent this structure cleanly.

The normal relational solution is an association table.

    EmployeeCapability

    employee_id
    capability_id
    proficiency

The association table converts the many-to-many relationship into two one-to-many relationships:

    Employee 1 ---- many EmployeeCapability
    Capability 1 ---- many EmployeeCapability

Each association row represents one employee-capability pair.

### Composite uniqueness

The pair:

    (employee_id, capability_id)

acts as the logical identity of an association.

For example:

    employee_id | capability_id | proficiency
    ------------+---------------+-------------
    1           | 401           | advanced
    2           | 401           | intermediate

Both rows are valid because they represent different employee-capability pairs.

This would be invalid:

    employee_id | capability_id | proficiency
    ------------+---------------+-------------
    1           | 401           | advanced
    1           | 401           | expert

unless the application explicitly models multiple independent assignments of the same capability.

The examples treat the pair as unique. The Python program uses `(user_id, skill_id)` as a dictionary key, the JavaScript program uses a composite string key, and the C++ program uses `std::pair<int, int>` with a custom hash.

### Attributes of the relationship

`proficiency` belongs to the association rather than to the employee or capability itself.

An employee does not have a universal proficiency value independent of a skill. Instead:

    Atul + SQL -> advanced
    Atul + Python -> expert

This illustrates an important reason for using an association entity rather than attempting to store a list of foreign keys directly in an employee record.

## Foreign Keys and Referential Integrity

A foreign key expresses that a value in one entity must reference an existing entity elsewhere.

For the one-to-many example:

    WorkItem.department_id
        ->
    Department.id

Creating a work item for department `999` is rejected when department `999` does not exist.

This prevents an orphan child record.

The same principle applies to association records:

    EmployeeCapability.employee_id
        ->
    Employee.id

    EmployeeCapability.capability_id
        ->
    Capability.id

Both referenced records must exist before the relationship can be created.

Referential integrity is different from cardinality.

A foreign key answers:

> Does this referenced record exist?

A uniqueness constraint or relationship-specific rule answers:

> How many records are allowed to reference it?

For example, a foreign key can ensure that a profile references a valid employee, while a unique foreign key can additionally ensure that the employee has at most one profile.

## Python Implementation

The Python program provides an in-memory relational model using standard-library data structures.

`Repository` provides primary-key-based entity storage. `RelationshipDatabase` then maintains the relationship-specific indexes.

The one-to-one implementation uses `profile_by_user`. The key is the user identifier and the value is the profile identifier. Before inserting a profile, the mapping is checked. This reproduces the essential behavior of a unique foreign key.

The one-to-many implementation uses `tasks_by_project`. Each project identifier maps to a set of task identifiers. The task itself stores `project_id`, which represents the foreign-key direction.

The many-to-many implementation uses `user_skills`, keyed by `(user_id, skill_id)`. Two additional indexes, `skills_by_user` and `users_by_skill`, support traversal in both directions.

The Python implementation also demonstrates restricted deletion. A project with dependent tasks cannot be deleted until its tasks have been removed.

Validation is performed before mutation where possible. This prevents invalid parent references, invalid statuses, duplicate relationships, and invalid proficiency values from entering the model.

## JavaScript Implementation

The JavaScript program uses a different perspective based on Node.js data structures and event-driven behavior.

`Map` is used for entity storage because it provides direct key-based access. `Set` is used for relationship membership because a relationship identifier should not appear twice in the same relationship index.

The one-to-one relationship uses `profileByEmployee`. The presence of an employee identifier in that map means that employee already has a profile.

The one-to-many relationship uses `workItemsByTeam`. A team identifier maps to a set of work-item identifiers. This makes parent-to-child traversal explicit.

The many-to-many relationship uses `employeeSkills`. Its key is formed from both identifiers:

    employeeId:skillId

The same relationship is indexed in both directions through `skillsByEmployee` and `employeesBySkill`.

The JavaScript implementation also uses `EventEmitter`. Relationship creation and removal emit events such as `profile.created`, `workitem.created`, and `skill.assigned`. This demonstrates how a relationship model can become part of an event-driven application without changing the underlying cardinality rules.

The asynchronous `validateRelationshipGraph()` method represents a realistic validation boundary where relationship consistency might be checked against an external persistence layer or another asynchronous service.

## C++ Case Study

The C++ implementation represents a repository-style governance system.

Employees belong to departments through management ownership, departments contain work items, and employees are associated with capabilities.

The one-to-one employee-profile relationship is enforced through `profileByEmployee`.

The one-to-many department-work-item relationship uses `workItemsByDepartment`. Multiple work items may contain the same department identifier, which preserves one-to-many cardinality.

The many-to-many employee-capability relationship is modeled with `EmployeeCapability`. The relationship stores `proficiency`, demonstrating that association records can contain attributes that describe the relationship itself.

The C++ implementation uses:

- `std::unordered_map` for primary-key-oriented entity storage.
- `std::unordered_set` for relationship membership and duplicate prevention.
- `std::pair<int, int>` as the composite identity of a many-to-many association.
- A custom `PairHash` so composite relationship keys can be stored in an unordered map.
- Explicit exception types for missing records and constraint violations.
- Separate forward and reverse indexes for relationship traversal.

The `validateRelationshipGraph()` operation checks that relationship indexes agree with the actual stored entities. This matters in systems that maintain derived indexes for performance because an index can become inconsistent even when the underlying entity records appear valid.

## Relationship Comparison

| Property | One-to-One | One-to-Many | Many-to-Many |
|---|---|---|---|
| Example | Employee → Profile | Department → WorkItem | Employee ↔ Capability |
| Maximum related records on child side | One | Many | Many |
| Typical foreign-key location | Dependent table | Many side | Association table |
| Unique foreign key required | Usually | No | Composite relationship key |
| Association table required | Usually no | No | Yes |
| Relationship attributes | Possible | Usually child attributes | Commonly stored in association |
| Traversal | Direct reference | Parent to child collection | Through association records |
| Duplicate relationship risk | Controlled by unique key | Controlled by child identity | Controlled by composite key |

The table describes cardinality rather than implementation preference. A physical database can implement the same logical relationship in different ways depending on optionality, historical requirements, inheritance, and other domain constraints.

## Optionality and Cardinality

Cardinality and optionality should not be confused.

A one-to-one relationship may be:

    1 : 1

when both entities must exist together, or:

    1 : 0..1

when the first entity may temporarily have no related record.

A one-to-many relationship can commonly be:

    1 : 0..many

because a parent may exist before its first child is created.

A many-to-many relationship can also have zero relationships on either side. An employee with no capabilities is still a valid employee, and a capability with no currently assigned employees may still be valid.

These distinctions matter when translating a conceptual data model into constraints.

## Association Tables

The many-to-many association table is not merely an implementation workaround. It represents a relationship as an entity that can carry its own attributes.

For example:

    EmployeeCapability
        employee_id
        capability_id
        proficiency

The `proficiency` value cannot naturally be assigned to the employee alone because an employee may have different proficiency levels for different capabilities.

Similarly, it cannot be assigned to the capability alone because different employees can have different proficiency levels for the same capability.

The relationship itself is therefore the correct location.

Other relationship-specific attributes might include assignment date, role in the relationship, priority, source, or status when those concepts are genuinely properties of the association.

## Traversal Patterns

The direction of a query influences the useful indexes.

For a one-to-many relationship:

    Department -> WorkItems

an index keyed by department identifier allows direct retrieval of child identifiers.

For a reverse lookup:

    WorkItem -> Department

the work item already contains the department foreign key.

For many-to-many relationships, both directions are common:

    Employee -> Capabilities

and:

    Capability -> Employees

The implementations maintain both relationship directions so that neither query requires scanning every association.

Without a suitable index, a naive many-to-many lookup may need to inspect every association row. With an index keyed by one endpoint, traversal can be proportional to the number of relationships associated with that endpoint.

## Integrity Failure Modes

### Orphan references

An orphan occurs when a child or association references an entity that does not exist.

The implementations reject these operations before creating the invalid relationship.

### Duplicate one-to-one association

A second profile for an employee violates the one-to-one rule.

A normal foreign key does not prevent this by itself. A unique constraint or equivalent application-level invariant is required.

### Duplicate many-to-many association

Repeatedly assigning the same capability to the same employee should not create duplicate relationship records when the pair is intended to be unique.

The composite key prevents this.

### Invalid parent deletion

Deleting a parent while dependent children remain creates a referential-integrity problem under restrictive deletion semantics.

The examples explicitly reject the deletion.

### Stale relationship indexes

The implementations maintain additional lookup structures. If an entity is removed without updating its relationship indexes, subsequent traversal can point toward nonexistent records.

The C++ consistency validator demonstrates how such corruption can be detected.

## Common Modeling Mistakes

### Treating one-to-many as many-to-many

If every work item belongs to exactly one department, an association table is unnecessary. The child can store the department foreign key directly.

Adding an association table without a domain requirement increases storage and query complexity.

### Omitting uniqueness in one-to-one relationships

A foreign key alone only establishes referential validity. It does not guarantee one-to-one cardinality.

The dependent foreign key needs an appropriate uniqueness rule when the database itself must enforce the cardinality.

### Storing repeated lists inside an entity

A field such as:

    skills = "Python, SQL, Security"

does not provide the same relational guarantees as a proper many-to-many association. It makes uniqueness, referential integrity, filtering, updates, and relationship-specific attributes harder to enforce.

### Duplicating relationship attributes

If proficiency belongs to the employee-capability relationship, placing one global `proficiency` field on the employee would lose information because the employee can have different proficiency levels across capabilities.

### Ignoring deletion semantics

The relationship model must define what happens when a referenced parent is deleted.

Possible policies include restricting the deletion, cascading dependent deletion, setting the foreign key to null where optionality permits it, or applying domain-specific archival behavior.

The correct behavior depends on the meaning and lifecycle of the data.

## Performance Considerations

Primary-key lookup and relationship traversal should be designed around expected query patterns.

The in-memory examples use hash maps and sets to provide average constant-time lookup for direct identifier access and relationship membership.

For one-to-many traversal, an index from parent identifier to child identifiers avoids scanning every child record.

For many-to-many traversal, maintaining indexes in both directions makes both endpoint queries efficient.

A relational database would normally use indexes on foreign-key columns and association-table keys. The exact indexing strategy should be based on actual query patterns, cardinality, update frequency, and storage costs.

Indexes improve reads but introduce write overhead because inserts, updates, and deletes must maintain the indexes.

## Security and Data Integrity

Relationship constraints also have security implications.

A system should not assume that receiving a valid identifier from a client makes the relationship authorized. Referential validity and authorization are separate concerns.

For example, an employee identifier may exist, but an application may still need to verify that the current operator is allowed to assign capabilities to that employee.

Similarly, relationship creation should validate both endpoints and the business operation permitted between them.

Database constraints are valuable because they protect data integrity even when application-level validation is accidentally bypassed. Application validation remains useful for clear error messages and business rules, while persistence-level constraints provide a second layer of protection.

## Debugging Relationship Problems

When a relationship query returns unexpected results, inspect the following separately:

- Verify that both endpoint records exist.
- Verify the foreign-key value or association pair.
- Check whether uniqueness constraints are being applied as intended.
- Check whether the relationship index contains stale identifiers.
- Check whether deletion logic updated all dependent indexes.
- Verify whether the query is traversing the relationship in the intended direction.
- Distinguish a missing relationship from a missing entity.

For many-to-many bugs, inspect the association table first. It is the actual set of relationships between the two entity types.

For one-to-many bugs, inspect the foreign-key values on the child records and then inspect the parent-to-child index if one is maintained.

For one-to-one bugs, inspect the unique mapping from the dependent record to its parent.

## Production Considerations

An in-memory model is useful for demonstrating relationship mechanics, but a production relational system normally delegates durable integrity enforcement to a database.

Important production constraints include primary keys, foreign keys, unique constraints, indexes, transactions, and appropriate delete behavior.

Relationship mutations that involve multiple records should be atomic when partial completion could create an invalid state. For example, inserting an association and updating a denormalized relationship index should not leave one operation committed while the other fails.

Schema migrations also need to preserve existing relationship data. Adding a foreign key or unique constraint to a populated table requires checking existing records for violations before the constraint can safely become mandatory.

The conceptual model should remain independent of a particular programming language. Python dictionaries, JavaScript maps, and C++ hash maps demonstrate the same relationship rules through different mechanisms, but a database schema provides the durable relational enforcement in a persistent application.
