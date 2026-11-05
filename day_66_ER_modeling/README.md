# ER Modeling: Entities, Attributes, Relationships, Cardinality and Participation

## 1. Introduction

Entity-Relationship (ER) modeling is a conceptual database design technique used to represent real-world objects, their properties, and the associations between them.

An ER model describes the logical structure of information before its implementation in a relational database.

It provides a structured representation of:

- Entities and their attributes.
- Primary keys and candidate keys.
- Relationships between entities.
- Relationship cardinality.
- Entity participation constraints.
- Associative entities.
- Mapping conceptual structures into relational tables.

The five implementations use different application domains to demonstrate the same database modeling principles.

| Implementation | Application domain | Main engineering perspective |
|---|---|---|
| Python | University management | ER schema construction and validation |
| JavaScript | Hospital management | Event-driven schema registry |
| C++17 | Retail order management | Referential integrity and relationship enforcement |
| Java 17 | Enterprise HR | Immutable domain models and service validation |
| PostgreSQL | University management | Relational implementation and database constraints |

---

## 2. Fundamental ER Modeling Concepts

### 2.1 Entity

An entity is an identifiable real-world object or concept about which information must be stored.

Examples include:

- Student
- Department
- Employee
- Product
- Customer
- Course
- Project

An entity type represents a category of objects. An entity instance represents one specific object belonging to that category.

For example:

| Student ID | Student name | Email |
|---|---|---|
| 101 | Aarav Sharma | aarav@example.com |
| 102 | Diya Verma | diya@example.com |

Here, `Student` is the entity type, while each row represents an entity instance.

In relational implementation, entity types normally become tables and their instances become rows.

### 2.2 Attributes

Attributes describe the properties of an entity or relationship.

For a Student entity:

- Student ID
- Student name
- Email
- Enrollment date
- Date of birth

For a Product entity:

- Product ID
- Product name
- Unit price
- Product category

Attributes can be classified into several categories.

| Attribute category | Meaning | Example |
|---|---|---|
| Simple | Cannot be meaningfully subdivided | Age |
| Composite | Contains multiple components | Address |
| Single-valued | One value per entity instance | Date of birth |
| Multivalued | Multiple values per entity instance | Phone numbers |
| Derived | Calculated from other attributes | Age from date of birth |
| Key | Identifies an entity instance | Student ID |
| Optional | May have no value | Middle name |

The implementations use data types and validation rules to restrict attribute values.

### 2.3 Keys

Keys establish entity identity and uniqueness.

**Super key**

A set of one or more attributes that uniquely identifies an entity instance.

**Candidate key**

A minimal super key. Removing any attribute would cause it to lose its uniqueness property.

**Primary key**

The candidate key selected as the principal identifier.

**Alternate key**

A candidate key that was not selected as the primary key.

**Composite key**

A key containing multiple attributes.

**Foreign key**

An attribute or set of attributes referencing a candidate key, usually the primary key, in another relation.

Example:

| Student ID | Email |
|---|---|
| 101 | aarav@example.com |
| 102 | diya@example.com |

Both attributes may uniquely identify students. If Student ID is selected as the primary key, Email becomes an alternate candidate key.

In PostgreSQL, the primary key and unique constraints enforce these rules.

### 2.4 Relationships

A relationship represents an association between entity types.

Examples:

- A student enrolls in a course.
- An instructor teaches a course.
- An employee works for a department.
- A customer places an order.
- An employee participates in a project.

A relationship can have its own attributes.

For example, the relationship between Student and Course may have:

- Enrollment date
- Grade
- Enrollment status

These attributes describe the enrollment association rather than the student or course independently.

When a relationship has important independent properties or participates in additional relationships, it can be modeled as an associative entity.

---

## 3. Cardinality

Cardinality describes the maximum number of entity instances that can participate in a relationship.

The main binary relationship types are 1:1, 1:N, N:1 and M:N.

### 3.1 One-to-One (1:1)

One instance of an entity is associated with at most one instance of another entity.

Example:

A person has one passport, and each passport belongs to one person.

Conceptual representation:

`Person 1 -------- 1 Passport`

Relational implementation:

- Create a foreign key in one table.
- Apply a UNIQUE constraint to the foreign key.
- Apply NOT NULL when participation is mandatory.

A unique foreign key enforces the maximum cardinality of one. It does not automatically enforce mandatory participation from the referenced entity's perspective.

### 3.2 One-to-Many (1:N)

One instance of an entity can be associated with multiple instances of another entity.

Example:

One department employs several instructors.

`Department 1 -------- N Instructor`

The relational implementation normally places the foreign key in the many-side table.

For example:

- Department has `department_id` as its primary key.
- Instructor has `department_id` as a foreign key.

This design avoids storing repeated instructor information inside Department records.

### 3.3 Many-to-One (N:1)

Many-to-one is the reverse perspective of one-to-many.

Example:

Several courses may belong to one department.

`Course N -------- 1 Department`

The foreign key is stored in Course.

### 3.4 Many-to-Many (M:N)

Multiple instances of one entity can be associated with multiple instances of another entity.

Example:

- A student can enroll in multiple courses.
- A course can contain multiple students.

`Student M -------- N Course`

A conventional relational database does not implement this conceptual relationship using a direct many-to-many foreign key.

It introduces an associative table:

`Student 1 ---- N Enrollment N ---- 1 Course`

The Enrollment table contains:

- Student ID
- Course ID
- Enrollment date
- Grade
- Status

A composite primary key consisting of Student ID and Course ID prevents duplicate enrollment records for the same student-course combination.

---

## 4. Participation Constraints

Participation describes whether an entity instance must participate in a relationship.

Unlike cardinality, which addresses maximum participation, participation constraints address minimum participation.

### 4.1 Total Participation

Total participation means every instance of an entity must participate in the specified relationship.

Example:

Every student must belong to a department.

`Student (1,1) -------- (0,N) Department`

The Student side has mandatory participation.

In relational databases, a NOT NULL foreign key enforces this requirement for the referencing row, together with a valid foreign-key reference.

### 4.2 Partial Participation

Partial participation means an entity instance may exist without participating in a particular relationship.

Example:

A student may not have enrolled in any course yet.

`Student (0,N) -------- (0,N) Course`

A student can therefore exist without an Enrollment record.

Partial participation normally does not require a relationship row for every entity instance.

### 4.3 Minimum and Maximum Cardinality

The minimum and maximum values can be represented together.

| Constraint | Meaning |
|---|---|
| 0..1 | Optional participation, at most one |
| 1..1 | Mandatory participation, exactly one |
| 0..N | Optional participation, potentially many |
| 1..N | Mandatory participation, one or more |

A relationship endpoint can therefore be represented using a pair:

`(minimum cardinality, maximum cardinality)`

For example:

`Student (0,N) -------- (1,1) Course`

This means:

- A student can participate in zero or many instances of the relationship.
- Every course must participate in exactly one instance.

The exact meaning depends on which entity is being described at each endpoint.

### 4.4 Important Database Distinction

Foreign keys and NOT NULL constraints do not enforce every participation rule.

For example:

- NOT NULL on `course.instructor_id` requires each course to reference an instructor.
- The foreign key prevents references to nonexistent instructors.
- Neither constraint requires every instructor to teach at least one course.

The last requirement is a parent-side participation constraint. It requires an additional mechanism, such as a deferred constraint trigger or a controlled transactional workflow.

The PostgreSQL implementation demonstrates this distinction.

---

## 5. ER Modeling Workflow

A typical conceptual database design follows this sequence:

`Business Requirements`

`        |`

`        v`

`Identify Entities`

`        |`

`        v`

`Identify Attributes`

`        |`

`        v`

`Select Candidate and Primary Keys`

`        |`

`        v`

`Identify Relationships`

`        |`

`        v`

`Determine Cardinality`

`        |`

`        v`

`Determine Participation`

`        |`

`        v`

`Resolve M:N Relationships`

`        |`

`        v`

`Map ER Model to Relational Tables`

`        |`

`        v`

`Implement Constraints and Validate`

Each stage contributes a different type of information to the final schema.

An incorrect entity definition can produce unnecessary duplication. An incorrect cardinality can produce an unsuitable relational structure. Missing participation constraints can allow records that violate business rules.

---

## 6. Python Implementation

**File perspective:** A conceptual ER schema builder and validation engine.

The Python program models an ER design independently of an actual database.

### 6.1 Domain classes

The implementation uses:

| Class | Responsibility |
|---|---|
| Attribute | Stores attribute metadata |
| Entity | Defines an entity and its attributes |
| RelationshipEnd | Defines minimum, maximum and participation |
| Relationship | Defines an association between two entities |
| ERModel | Maintains and validates the complete model |

Enumerations separate cardinality, participation and attribute data types.

Dataclasses reduce unnecessary object-construction code and provide structured immutable attribute definitions.

### 6.2 University model

The example contains four entity types:

- Department
- Student
- Instructor
- Course

It defines five relationships:

| Relationship | Cardinality |
|---|---|
| StudentDepartment | 1:N |
| DepartmentInstructor | 1:N |
| DepartmentCourse | 1:N |
| Enrollment | M:N |
| Teaching | 1:N |

The Enrollment relationship contains its own attributes:

- Enrollment date
- Grade

### 6.3 Validation

The program checks:

- Entity name validity.
- Duplicate entity names.
- Duplicate attribute names.
- Presence of primary keys.
- Valid relationship endpoints.
- Cardinality bounds.
- Participation consistency.
- Record attribute validity.
- Data types.
- NULL restrictions.
- Duplicate primary keys.

The `validate_entity_instances()` method performs record-level validation without requiring a database.

### 6.4 Relational mapping

The `relational_mapping()` method evaluates each relationship and identifies an appropriate relational implementation.

| ER relationship | Mapping |
|---|---|
| 1:1 | UNIQUE foreign key |
| 1:N | Foreign key on the many side |
| N:1 | Foreign key on the many side |
| M:N | Junction table |

The JSON export stores the model's entities, attributes, relationships and participation metadata.

### 6.5 Complexity considerations

Let:

- E represent the number of entity types.
- R represent the number of relationships.
- A represent the total number of attributes.

Model registration and inspection use dictionary-based lookups.

Average entity and relationship lookup is O(1). Full model inspection is O(E + R + A).

Record validation is approximately O(A) per record, excluding the cost of checking duplicate keys across multiple records.

For large datasets, indexed key sets would provide more efficient duplicate detection.

---

## 7. JavaScript Implementation

**File perspective:** An event-driven hospital ER schema registry.

The JavaScript implementation emphasizes dynamic schema registration, events, runtime validation and asynchronous file export.

### 7.1 Domain design

The hospital model contains:

| Entity | Main attributes |
|---|---|
| Patient | Patient ID, name, email, date of birth |
| Doctor | Doctor ID, name, specialization |
| Appointment | Appointment ID, date, status |

Relationships include:

- PatientAppointment
- DoctorAppointment
- PatientDoctor

PatientAppointment and DoctorAppointment demonstrate mandatory appointment participation.

PatientDoctor represents a many-to-many association that can contain relationship-specific information.

### 7.2 Event-driven architecture

The `ERRegistry` extends Node.js `EventEmitter`.

It publishes events when:

- An entity is registered.
- A relationship is registered.
- An entity record is inserted.

This separates schema-management operations from event consumers.

The event payloads contain relevant model information rather than exposing the registry's internal state.

### 7.3 Maps and Sets

The implementation uses:

- `Map` for entity definitions.
- `Map` for relationship definitions.
- `Map` for entity instances.
- Sets indirectly through primary-key and uniqueness checks.

Maps provide efficient lookup by entity or relationship name.

### 7.4 Referential integrity

The relationship validation method checks:

1. Both referenced entity instances exist.
2. Maximum cardinality is not exceeded.
3. Total participation is satisfied.
4. Relationship records do not contain orphan references.

A failed validation throws a specific modeling error.

The implementation uses immutable record snapshots to prevent callers from modifying stored records through their original object references.

### 7.5 Asynchronous export

Node.js filesystem operations export the schema as JSON.

The export uses asynchronous file handling, allowing the application to avoid blocking the event loop during ordinary file operations.

The implementation uses no external npm packages.

---

## 8. C++17 Implementation

**File perspective:** A retail order management system with a relationship integrity engine.

The C++ program demonstrates how conceptual ER structures translate into strongly typed application data structures.

### 8.1 Retail entities

The model contains:

- Customer
- Product
- Order
- OrderLine

OrderLine acts as an associative entity connecting Order and Product.

### 8.2 Relationship design

The primary relationships are:

| Relationship | Cardinality | Implementation |
|---|---|---|
| CustomerOrder | 1:N | Customer ID in Order |
| OrderOrderLine | 1:N | Order ID in OrderLine |
| ProductOrderLine | 1:N | Product ID in OrderLine |
| OrderProduct | M:N | OrderLine junction entity |

An order can contain several products. A product can appear in several orders.

OrderLine stores the quantity associated with a particular order-product combination.

### 8.3 Data structures

The implementation uses:

| Data structure | Purpose |
|---|---|
| `unordered_map` | Fast entity lookup |
| `map` | Composite relationship keys |
| `vector` | Attribute collections |
| `unordered_set` | Attribute-name uniqueness |
| `optional` | Representing an unbounded maximum cardinality |

The OrderLine collection uses a composite key:

`(order_id, product_id)`

This prevents the same product from being inserted twice into one order.

### 8.4 Validation mechanisms

The retail database validates:

- Positive identifiers.
- Customer uniqueness.
- Product prices.
- Order status.
- Existing foreign-key references.
- Positive order quantities.
- Duplicate order lines.
- Total participation of Order in OrderLine.

The `validateParticipation()` method checks that every order contains at least one line item.

### 8.5 Performance

Hash-based entity lookups provide average O(1) lookup performance.

The ordered composite-key map provides O(log N) lookup and insertion.

The demonstration's order-total calculation scans the order-line collection, giving O(L) complexity for L stored order lines.

For a high-volume implementation, a secondary index organized by order ID would reduce the cost of retrieving individual order lines.

---

## 9. Java 17 Implementation

**File perspective:** Enterprise HR information system.

The Java implementation focuses on strongly typed enterprise domain models, immutable records, service-level validation and business rules.

### 9.1 Enterprise entities

The model includes:

- Department
- Employee
- Project
- Assignment

Assignment is an associative entity connecting Employee and Project.

### 9.2 Employee-department relationship

Each employee belongs to exactly one department.

A department can contain multiple employees.

`Department (0,N) -------- (1,1) Employee`

The department reference is stored in the Employee entity.

### 9.3 Employee-project relationship

An employee can participate in multiple projects.

A project can involve multiple employees.

`Employee (0,N) -------- (1,N) Project`

The Assignment record resolves this M:N relationship.

Its attributes include:

- Assigned date
- Role
- Allocation percentage

The allocation field is validated to remain greater than zero and at most 100.

### 9.4 Java records

Java 17 records provide concise immutable data carriers.

The implementation uses records for:

- Attribute
- EntityDefinition
- RelationshipEnd
- RelationshipDefinition
- Department
- Employee
- Project
- Assignment

Record constructors validate their values when instances are created.

This prevents invalid domain objects from entering the service layer.

### 9.5 Service-layer responsibilities

The `HRService` class manages the application data.

It enforces:

- Department existence before employee registration.
- Unique employee email addresses.
- Unique entity identifiers.
- Existing employee and project references.
- Assignment eligibility.
- Valid project dates.
- Unique employee-project assignments.
- Project participation requirements.

The service also generates department-level employee and payroll reports.

### 9.6 Enterprise modeling distinction

An ER model describes structural relationships.

An enterprise service adds operational rules.

For example, an Employee-to-Project M:N relationship is a structural property. Requiring only active employees to receive new project assignments is an application policy.

These rules should remain distinct because structural validity and operational eligibility answer different questions.

---

## 10. PostgreSQL Implementation

**File perspective:** A relational implementation of the University Information Management System.

The SQL script creates a dedicated schema named `university_er`.

### 10.1 Relational schema

| Table | Primary key | Main foreign keys |
|---|---|---|
| department | department_id | None |
| student | student_id | department_id |
| instructor | instructor_id | department_id |
| course | course_id | department_id, instructor_id |
| enrollment | student_id, course_id | student_id, course_id |

### 10.2 Primary and candidate keys

The schema uses generated identity columns for entity identifiers.

Candidate keys are represented using unique constraints.

Examples:

- Department code
- Department name
- Student enrollment number
- Student email
- Instructor employee number
- Instructor email
- Course code

Enrollment uses a composite primary key consisting of Student ID and Course ID.

### 10.3 Foreign-key relationships

The database implements four principal one-to-many relationships:

- Department to Student.
- Department to Instructor.
- Department to Course.
- Instructor to Course.

The Student-Course M:N relationship is implemented using Enrollment.

Foreign keys prevent the creation of dependent records that reference nonexistent parent entities.

### 10.4 Check constraints

Check constraints validate domain-specific attribute values.

Examples include:

- Positive course-credit ranges.
- Valid semester values.
- Nonnegative instructor salaries.
- Valid enrollment statuses.
- Accepted grade values.

These restrictions are enforced inside PostgreSQL rather than relying exclusively on application validation.

### 10.5 Participation enforcement

The SQL implementation distinguishes between two cases.

**Referencing-side participation**

For example, every Student must have a Department.

This is enforced through:

- `department_id NOT NULL`
- A foreign key referencing Department.

**Referenced-side participation**

For example, every Course may be required to have at least one Enrollment.

A conventional foreign key does not enforce this condition.

The script demonstrates deferred constraint triggers for selected total-participation rules.

These triggers evaluate the state at transaction commit, allowing related records to be inserted within one transaction.

The rules represent explicit university business policies. They are not universal requirements of ER modeling.

### 10.6 Views

The implementation provides:

- `er_relationship_catalog`
- `student_course_details`
- `department_statistics`

The first view documents the conceptual relationship structure.

The second provides a joined representation of students and their courses.

The third aggregates department-level entity counts.

### 10.7 Functions and procedures

`validate_er_relationships()` checks selected participation and referential integrity conditions.

`enroll_student()` implements a controlled enrollment workflow.

The procedure checks student and course eligibility before inserting an Enrollment record.

A duplicate enrollment is rejected through the composite primary key.

### 10.8 Transactions

The SQL script uses transactions to group related operations.

Deferred constraint triggers permit temporarily incomplete relationship states inside a transaction when the final committed state satisfies the configured constraints.

A failed operation can be rolled back without retaining partial changes.

### 10.9 Indexing

Indexes support common relationship traversal paths.

Examples:

- Student to Department.
- Instructor to Department.
- Course to Instructor.
- Enrollment to Course.

The primary and unique constraints also create indexes where required by PostgreSQL.

Index selection should reflect actual query patterns and write workloads. Additional indexes impose storage and update costs.

---

## 11. Conceptual ER Model Versus Relational Model

An ER diagram and a relational schema describe related but different levels of database design.

| Aspect | ER model | Relational model |
|---|---|---|
| Primary purpose | Conceptual representation | Logical data structure |
| Main components | Entities, attributes, relationships | Relations, attributes, keys |
| Relationship representation | Explicit relationship | Foreign keys and junction tables |
| Cardinality | Expressed at relationship endpoints | Enforced using constraints |
| Participation | Total or partial | NOT NULL, foreign keys and additional enforcement |
| M:N relationships | Direct conceptual relationship | Associative relation |
| Design focus | Business structure | Data organization and integrity |

An ER model is not simply a drawing of database tables.

It captures business meaning before the implementation decisions are made.

For example, an ER diagram can represent a many-to-many relationship directly. Its relational implementation requires an additional table.

---

## 12. Important Modeling Decisions

### 12.1 When to introduce an associative entity

An associative entity is appropriate when:

- An M:N relationship must be represented relationally.
- The relationship has its own attributes.
- The relationship needs an independent identifier.
- Other entities must reference the relationship itself.

Enrollment and Assignment demonstrate these situations.

### 12.2 When to use composite keys

Composite keys are useful when the identity of a record depends on multiple attributes.

Examples:

- Student ID and Course ID.
- Order ID and Product ID.
- Employee ID and Project ID.

A composite key can prevent duplicate associations without requiring an artificial identifier.

An artificial identifier can still be appropriate when the association must be referenced independently by other entities.

### 12.3 When to use UNIQUE foreign keys

A foreign key normally permits multiple referencing records.

A UNIQUE constraint changes this behavior by restricting the number of referencing records to at most one for each referenced key.

This is useful when implementing the maximum cardinality of one in a 1:1 relationship.

### 12.4 When triggers are required

Triggers are useful when an integrity rule cannot be expressed adequately using ordinary declarative constraints.

Examples include:

- Requiring every parent to have at least one child.
- Enforcing cross-row participation rules.
- Applying transaction-level validation.

Triggers must be designed carefully to handle concurrency, transaction ordering and concurrent changes to related rows.

Where possible, declarative constraints are preferable because they are simpler and easier for the database to optimize.

---

## 13. Edge Cases and Failure Conditions

| Failure condition | Relevant mechanism |
|---|---|
| Duplicate entity identifier | Primary key |
| Duplicate candidate key | UNIQUE constraint |
| Missing mandatory attribute | NOT NULL |
| Invalid attribute value | Type and CHECK constraint |
| Unknown referenced entity | Foreign key |
| Duplicate M:N association | Composite primary key |
| Excessive relationship cardinality | UNIQUE constraint or validation |
| Missing mandatory participation | NOT NULL or additional trigger |
| Invalid relationship endpoint | ER schema validation |
| Invalid entity definition | Model constructor validation |
| Invalid business operation | Application service validation |

A correctly designed model should distinguish between invalid data and valid states that are incomplete only temporarily during a transaction.

---

## 14. Security and Production Considerations

ER modeling contributes to database integrity but does not independently provide application security.

A production implementation should consider:

- Least-privilege database roles.
- Restricted schema ownership.
- Parameterized SQL operations.
- Validation of external input.
- Appropriate access control for sensitive attributes.
- Encryption in transit and at rest.
- Auditing of important data modifications.
- Transaction isolation.
- Referential integrity.
- Backup and recovery procedures.
- Index monitoring and query analysis.

Sensitive attributes such as employee salaries and student personal information should have access restrictions independent of their presence in the ER model.

Database constraints should remain authoritative for integrity rules that must hold regardless of which application accesses the database.

---

## 15. Performance and Scalability

The choice of keys and relationship structures affects database performance.

Primary keys provide efficient entity identification.

Foreign-key indexes support joins and relationship traversal.

Composite indexes should follow actual query predicates and ordering requirements.

For M:N relationships, junction tables can grow significantly as the number of associations increases.

For example, if 10,000 students each enroll in 8 courses, the Enrollment table may contain approximately 80,000 records.

The number of relationships is therefore not necessarily small merely because the number of entity types is small.

Performance analysis should consider:

- Number of entity instances.
- Number of relationship instances.
- Index selectivity.
- Join frequency.
- Update and deletion frequency.
- Transaction contention.
- Query execution plans.

The conceptual model should preserve business correctness. Physical optimization should be applied without changing the intended relationship semantics.

---

## 16. Implementation Execution

### Python

- Runtime: Python 3.10 or later.
- External dependencies: None.
- Main output: Model description, relational mappings, validation results and JSON export.
- Export: `university_er_model.json`.

### JavaScript

- Runtime: Node.js 18 or later.
- External dependencies: None.
- Main output: Event notifications, relational mapping and validation results.
- Export: `hospital_er_model.json`.

### C++17

- Compiler: GCC or another C++17-compatible compiler.
- External dependencies: None.
- Main output: Retail model description, order calculations and integrity tests.

### Java 17

- Runtime: JDK 17.
- External dependencies: None.
- Main output: Enterprise HR model, payroll report and validation results.

### PostgreSQL

- Database: PostgreSQL 14 or later.
- Main output: University schema, sample data, relationship views, constraints, validation functions and reports.
- Schema: `university_er`.

---

## 17. Technical Coverage

| Learning area | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Entity modeling | Yes | Yes | Yes | Yes | Yes |
| Attribute modeling | Yes | Yes | Yes | Yes | Yes |
| Primary keys | Yes | Yes | Yes | Yes | Yes |
| Candidate keys | Yes | Yes | Yes | Yes | Yes |
| Relationships | Yes | Yes | Yes | Yes | Yes |
| 1:1 cardinality | Yes | Yes | Yes | Yes | Explained |
| 1:N cardinality | Yes | Yes | Yes | Yes | Yes |
| M:N cardinality | Yes | Yes | Yes | Yes | Yes |
| Total participation | Yes | Yes | Yes | Yes | Yes |
| Partial participation | Yes | Yes | Yes | Yes | Yes |
| Relationship attributes | Yes | Yes | Yes | Yes | Yes |
| Associative entities | Mapping | Mapping | Yes | Yes | Yes |
| Referential integrity | Record validation | Runtime validation | Application validation | Service validation | Foreign keys |
| Schema export | JSON | JSON | Console | Console | SQL views |
| Automated checks | Yes | Yes | Yes | Yes | Yes |

The implementations demonstrate the progression from conceptual ER definitions to application-level validation and database-level integrity enforcement.
