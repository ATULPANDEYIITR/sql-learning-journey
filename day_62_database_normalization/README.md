# Database Normalization: Functional Dependencies, Normalization Goals, and Anomalies

## Scope

This learning artifact models relational database normalization through a university enrollment domain. The central relation begins as a conceptual enrollment record containing student, course, instructor, and grade facts:

`EnrollmentRecord(student_id, student_name, course_id, course_name, instructor_id, instructor_name, grade)`

The implementation identifies functional dependencies, determines candidate-key behavior, detects partial and transitive dependencies, and decomposes the relation into smaller relations with clear ownership of facts.

The five source files use the same domain from different engineering perspectives:

| File | Primary perspective | Main implementation |
|---|---|---|
| Python | Dependency analysis and anomaly simulation | Closures, candidate keys, dependency diagnostics, normalized storage |
| JavaScript | Event-driven schema evaluation | Event bus, policy evaluation, validation, structured state |
| C++17 | Governance and merge-eligibility style engine | Normalization governance, dependency evaluation, repository-like storage discipline |
| Java 17 | Enterprise domain model | Records, interfaces, policies, services, explicit validation |
| PostgreSQL | Relational implementation | Tables, constraints, indexes, views, CTEs, transactions, foreign keys |

The examples deliberately distinguish the logical problem of normalization from the physical implementation of a database.

---

## Core Domain

The domain contains four major entity types:

- `Student`
- `Instructor`
- `Course`
- `Enrollment`

Their relationships are:

```text
Student
   |
   | 1-to-many
   v
Enrollment
   ^
   |
   | many-to-1
Course
   |
   | many-to-1
   v
Instructor
```

The enrollment relation represents the association between a student and a course. Its natural key is the combination of `student_id` and `course_id`.

The normalized relational structure is:

```text
students
  student_id -> student_name, email

instructors
  instructor_id -> instructor_name, email

courses
  course_id -> course_name, instructor_id, credits

enrollments
  (student_id, course_id) -> grade, enrolled_at
```

This structure gives each fact an appropriate determinant and reduces repeated storage.

---

## Functional Dependencies

A functional dependency describes a constraint in which one set of attributes determines another set of attributes.

The notation:

`X -> Y`

means that whenever two rows have the same value of `X`, they must also have the same value of `Y`.

In the enrollment domain:

| Functional dependency | Meaning |
|---|---|
| `student_id -> student_name` | A student identifier determines the student's name |
| `course_id -> course_name, instructor_id` | A course identifier determines its name and assigned instructor |
| `instructor_id -> instructor_name` | An instructor identifier determines the instructor name |
| `(student_id, course_id) -> grade` | A student-course pair determines its grade |

The dependencies describe business rules, not merely column relationships.

For example, the statement `course_id -> instructor_id` assumes that each course has one assigned instructor in the modeled system. If the real business rule allowed several instructors per course, that dependency would no longer be valid and the schema would need a different relationship model.

---

## Candidate Keys and Attribute Closure

A candidate key is a minimal attribute set capable of determining every attribute in a relation.

For the original enrollment relation:

`{student_id, course_id}`

is the candidate key.

Its closure is the set of attributes that can be derived from it using the known functional dependencies.

The dependency chain is:

```text
student_id
    |
    +----> student_name

course_id
    |
    +----> course_name
    |
    +----> instructor_id
                |
                +----> instructor_name

(student_id, course_id)
    |
    +----> grade
```

Therefore:

`{student_id, course_id}+`

contains every attribute in the original relation.

The Python, JavaScript, C++17, and Java 17 implementations calculate this closure programmatically rather than treating the key as a hard-coded fact.

---

## Why Normalization Is Needed

Normalization organizes relational data so that each fact is stored in an appropriate relation and unnecessary dependency problems are reduced.

The primary goals represented here are:

- reducing redundant storage
- preserving meaningful dependencies
- preventing inconsistent copies of the same fact
- preventing insertion anomalies
- preventing update anomalies
- preventing deletion anomalies
- making integrity rules explicit
- improving maintainability of relational data

Normalization is not simply a process of creating many tables. A decomposition must preserve the intended meaning of the data and should not arbitrarily split related attributes.

---

## First Normal Form

First Normal Form requires attributes to contain atomic values rather than repeating groups or nested collections.

The source model treats values such as:

- `student_id`
- `student_name`
- `course_id`
- `course_name`
- `instructor_id`
- `instructor_name`
- `grade`

as individual scalar attributes.

A problematic design would place multiple courses into one student row as a list such as:

`S001 | Asha Singh | C101,C102,C103`

That representation makes individual course relationships harder to constrain and query.

The normalized design instead stores separate enrollment rows:

| student_id | course_id | grade |
|---|---|---|
| S001 | C101 | A |
| S001 | C102 | B+ |

Each row represents one student-course association.

---

## Second Normal Form

Second Normal Form addresses partial dependencies on a composite candidate key.

The original candidate key is:

`(student_id, course_id)`

The following dependency exists:

`student_id -> student_name`

The determinant `student_id` is only part of the composite key. Therefore `student_name` does not depend on the complete key.

Similarly:

`course_id -> course_name, instructor_id`

contains attributes determined by only one component of the composite enrollment key.

These are partial dependencies.

The decomposition separates them:

```text
Student
  student_id -> student_name

Course
  course_id -> course_name, instructor_id

Enrollment
  (student_id, course_id) -> grade
```

After decomposition, student and course facts no longer have to be repeated for every enrollment.

---

## Third Normal Form

Third Normal Form removes relevant transitive dependencies.

The original relation contains:

`course_id -> instructor_id`

and:

`instructor_id -> instructor_name`

Therefore:

`course_id -> instructor_name`

can be derived transitively.

The instructor name does not directly belong to the course fact if the instructor is independently identified by `instructor_id`.

The normalized structure therefore separates instructor data:

```text
Instructor
  instructor_id -> instructor_name

Course
  course_id -> course_name, instructor_id
```

The relationship remains available through the foreign key from `courses.instructor_id` to `instructors.instructor_id`.

---

## Anomalies

### Update Anomaly

Suppose the original enrollment relation contains:

| student_id | course_id | course_name | instructor_id | instructor_name |
|---|---|---|---|---|
| S001 | C101 | Database Systems | I001 | Dr. Mehta |
| S002 | C101 | Database Systems | I001 | Dr. Mehta |
| S003 | C103 | Data Structures | I001 | Dr. Mehta |

Changing the instructor's name requires multiple rows to be updated.

If only some rows are changed, the database contains contradictory versions of the same fact.

In the normalized design, `instructors` contains one authoritative row for `I001`.

The update is therefore applied once.

---

### Insertion Anomaly

In a heavily denormalized enrollment relation, creating a course before any student enrolls can be difficult because the course information is tied to an enrollment row.

The normalized design permits:

```text
courses
C104 | Distributed Systems | I002
```

without requiring an enrollment.

This separates the existence of a course from the existence of a student-course relationship.

---

### Deletion Anomaly

Suppose the only student enrolled in a course is removed from the enrollment table.

In a denormalized structure, deleting that row could accidentally remove the only stored copy of the course and instructor information.

In the normalized design:

```text
Enrollment
    |
    +-- association removed

Course
    |
    +-- remains

Instructor
    |
    +-- remains
```

The independent facts survive because they have their own relations.

---

## Python Implementation

The Python implementation focuses on dependency reasoning.

### Functional dependency model

`FunctionalDependency` stores determinant and dependent attribute sets.

`Relation` stores:

- relation attributes
- candidate keys
- functional dependencies

The implementation validates that keys and dependencies reference known attributes.

### Attribute closure

The `closure()` method repeatedly applies functional dependencies while new attributes can be derived.

The algorithm starts with the supplied attributes:

```text
closure = initial attributes
```

It then checks each dependency:

```text
if determinant is contained in closure:
    add dependent attributes
```

The process stops when no new attributes can be added.

This directly models the standard closure procedure.

### Candidate-key reasoning

`is_superkey()` checks whether the closure of a determinant contains the complete relation.

The Python implementation also distinguishes candidate keys from arbitrary superkeys by checking minimality.

### Dependency diagnostics

The script identifies:

- partial dependencies
- transitive dependencies
- highest detected normal form

It then models normalized storage using separate student, course, and enrollment structures.

### Anomaly simulation

The `EnrollmentSystem` stores students, courses, and enrollments separately. It validates references and detects consistency problems.

This shows the operational consequence of normalization rather than treating normalization only as a theoretical exercise.

---

## JavaScript Implementation

The JavaScript implementation uses an event-driven schema review model.

### Event-driven evaluation

`NormalizationEventBus` allows analysis events to be emitted when:

- normalization analysis completes
- a partial dependency is detected
- a transitive dependency is detected

This separates dependency analysis from reporting behavior.

The architecture is:

```text
RelationSchema
      |
      v
SchemaReviewService
      |
      v
NormalizationEventBus
      |
      +---- analysis.completed
      |
      +---- anomaly.detected
```

This is useful when a schema-review service needs to trigger multiple independent actions such as logging, policy reporting, or deployment blocking.

### Map and Set usage

JavaScript `Map` objects represent entity collections.

`Set` objects represent:

- attributes
- determinants
- dependent attributes
- candidate keys
- attribute closures

This matches the mathematical structure of functional dependency analysis.

### Policy behavior

The JavaScript model evaluates the schema before accepting it as a valid normalized design.

Validation rejects:

- unknown attributes
- empty dependency sides
- missing keys
- duplicate enrollments
- unknown instructors
- invalid grades

The normalized enrollment store keeps student, instructor, course, and enrollment information separate.

---

## C++17 Implementation

The C++ implementation treats normalization as a governance decision.

The `Relation` class owns:

- relation attributes
- candidate keys
- functional dependencies
- closure calculation
- superkey evaluation
- partial-dependency detection
- transitive-dependency detection

`NormalizationGovernanceEngine` evaluates the relation and returns an explicit decision:

```text
ACCEPT
```

or:

```text
REQUIRES DECOMPOSITION
```

This design separates the mathematical analysis from the business decision that consumes the analysis.

### Data structures

The implementation uses:

- `std::set` for attribute sets
- `std::vector` for ordered dependency collections
- `std::map` for entity storage
- `std::pair` for the composite enrollment key

The composite map key:

`(student_id, course_id)`

enforces uniqueness at the application level.

### Performance

Attribute closure repeatedly scans the functional dependencies. For a small dependency set this is straightforward and predictable.

The entity repository uses ordered maps. Lookup is logarithmic, while the clarity of composite-key handling makes the model suitable for a compact governance case study.

A production implementation could select hash-based containers when ordered traversal is unnecessary.

---

## Java 17 Implementation

The Java implementation uses an enterprise-oriented domain model.

### Records

Java records represent immutable domain values:

- `FunctionalDependency`
- `Student`
- `Instructor`
- `Course`
- `Enrollment`

This prevents accidental mutation of domain facts after construction.

### Policy interface

`NormalizationPolicy` defines the contract for normalization rules.

`ThirdNormalFormPolicy` implements that contract by rejecting partial and transitive dependencies.

The policy is injected into `NormalizationService`.

This separates:

```text
domain model
      |
      v
policy
      |
      v
service
```

from the storage model.

### Validation

Domain constructors validate essential invariants immediately.

The enrollment service validates:

- student existence
- course existence
- instructor existence
- duplicate enrollment keys
- grade format

This means invalid domain state is rejected close to its source.

### Stream processing

The enrollment service uses Java streams to aggregate enrollments by course.

The resulting count is a reporting operation over normalized relationship data.

---

## PostgreSQL Implementation

The PostgreSQL script is the executable relational representation.

The schema contains:

- `students`
- `instructors`
- `courses`
- `enrollments`

### Primary keys

Each entity has a stable primary key.

The enrollment relation uses a composite primary key:

`(student_id, course_id)`

This directly represents the rule that a student cannot be enrolled in the same course more than once.

### Foreign keys

The database enforces:

```sql
courses.instructor_id -> instructors.instructor_id

enrollments.student_id -> students.student_id

enrollments.course_id -> courses.course_id
```

These constraints prevent orphaned relationships.

### Check constraints

The database validates:

- non-empty names
- course credit ranges
- allowed grade values

The database therefore enforces important integrity rules independently of application code.

### Indexes

The script creates indexes for common relationship lookups:

- courses by instructor
- enrollments by course

The primary keys already provide indexes for their key columns, so redundant indexes are avoided.

---

## Views and Reporting

The `student_course_facts` view reconstructs the business-level picture by joining normalized relations.

The view provides:

- student identity
- course identity
- instructor identity
- grade
- enrollment timestamp

This demonstrates an important property of normalization:

**Normalization does not mean information becomes inaccessible.**

Facts are stored separately, then reconstructed through joins when required.

The storage model and reporting model can therefore have different shapes.

---

## Transactions and Failure Handling

The PostgreSQL implementation includes transactional behavior.

An instructor update is performed inside a transaction:

```sql
BEGIN;

UPDATE instructors
SET instructor_name = 'Dr. Mehta'
WHERE instructor_id = 'I001';

COMMIT;
```

A failed enrollment reference is handled with a savepoint so that the invalid operation can be isolated.

This demonstrates the distinction between:

- relational integrity
- transaction control
- application validation

Foreign keys remain the authoritative database-level protection for referenced entities.

---

## Relationship Between the Five Implementations

The implementations intentionally use different responsibilities.

| Implementation | Main responsibility |
|---|---|
| Python | Analyze dependencies and demonstrate normalization consequences |
| JavaScript | Evaluate schemas through asynchronous events and policies |
| C++17 | Treat normalization as a governance decision |
| Java 17 | Model normalization rules as enterprise domain policies and services |
| PostgreSQL | Enforce the normalized structure at the database level |

The same dependency rules appear across the implementations, but their engineering roles differ.

The source files therefore complement one another rather than representing five mechanical translations of the same program.

---

## Normalization Workflow

The complete workflow can be represented as:

```text
Identify attributes
       |
       v
Identify business rules
       |
       v
Determine functional dependencies
       |
       v
Find candidate keys
       |
       v
Calculate attribute closures
       |
       v
Check 1NF
       |
       v
Check partial dependencies
       |
       v
Check 2NF
       |
       v
Check transitive dependencies
       |
       v
Check 3NF
       |
       v
Decompose relations
       |
       v
Add primary and foreign keys
       |
       v
Validate anomalies and queries
```

The sequence matters because normalization depends on the actual functional dependencies of the domain.

---

## Distinguishing the Main Concepts

### Functional Dependencies

Functional dependencies express facts about determination between attributes.

Example:

`student_id -> student_name`

### Candidate Keys

Candidate keys identify the minimum attributes needed to uniquely identify a tuple.

Example:

`(student_id, course_id)`

### Normal Forms

Normal forms provide structured conditions for reducing problematic dependency patterns.

The artifact focuses on:

- 1NF
- 2NF
- 3NF

### Anomalies

Anomalies describe practical consequences of poor relational design.

The three central cases are:

- update anomaly
- insertion anomaly
- deletion anomaly

### Decomposition

Decomposition splits a relation into smaller relations according to the dependency structure.

The target design is:

```text
Student(student_id, student_name, email)

Instructor(instructor_id, instructor_name, email)

Course(course_id, course_name, instructor_id, credits)

Enrollment(student_id, course_id, grade, enrolled_at)
```

---

## Edge Cases

The implementations explicitly handle several invalid or difficult conditions.

### Unknown entity

An enrollment referencing a nonexistent student or course is rejected.

### Duplicate relationship

The same student-course pair cannot be inserted twice.

### Invalid grade

The application and database reject unsupported grade values.

### Invalid dependency

A dependency referencing an attribute outside the relation is rejected.

### Empty determinant

A functional dependency cannot use an empty determinant in these implementations.

### Missing candidate key

A relation without a candidate key is rejected by the dependency-analysis models.

### Inconsistent redundant data

The Python model can detect cases where duplicated student or course facts disagree with their canonical records.

---

## Practical Design Implications

Normalization should be based on actual business rules rather than a mechanical desire to create more tables.

For example, the dependency:

`course_id -> instructor_id`

is valid only if the business rule says each course has one instructor.

If the system permits multiple instructors per course, the correct design changes to an associative relationship such as:

```text
Course
  |
  +---- CourseInstructor ---- Instructor
```

Similarly, if course names can change independently of course identity, the course identifier remains the determinant while the current name is stored as an attribute of the course relation.

Normalization therefore depends on correctly identifying the semantics of the domain.

---

## Limitations of the Model

The examples focus on functional dependencies and normal forms through 3NF.

They do not attempt to model every normalization issue found in advanced relational design.

The model does not provide a complete automated inference engine for every possible dependency implication. The dependency analysis is intentionally constrained to the supplied functional dependencies.

The examples also do not claim that every database should be decomposed to the maximum possible degree. Real systems may deliberately introduce controlled redundancy for reporting, caching, performance, historical snapshots, or analytical workloads.

Such denormalization should be an explicit design decision supported by measured requirements rather than an accidental consequence of duplicated data.

---

## Integrity Boundary

A robust relational design places critical invariants at the appropriate boundary.

```text
Application
    |
    | validation and domain policies
    v
Service Layer
    |
    | transactions and workflow
    v
PostgreSQL
    |
    +-- PRIMARY KEY
    +-- FOREIGN KEY
    +-- UNIQUE
    +-- CHECK
    +-- transaction isolation
```

Application validation improves usability and error reporting.

Database constraints provide authoritative protection against invalid persistent state.

Both layers are represented in the source files, with PostgreSQL providing the strongest persistence-level enforcement.

---

## Security and Reliability Considerations

Normalization itself is not a security mechanism, but a well-defined relational structure improves control over data ownership and integrity.

The implementations avoid embedding redundant identity facts across unrelated records.

Database-level foreign keys prevent invalid references.

Unique constraints prevent duplicate identities and duplicate relationships.

Check constraints prevent invalid domain values.

Transactions protect multi-step database operations from partial completion.

Application-level validation provides early rejection of malformed input.

In a production system, these mechanisms should be combined with authentication, authorization, encrypted connections, parameterized queries, auditing, backup procedures, and appropriate transaction isolation. Those concerns are outside the normalization algorithms themselves.

---

## Educational Mapping

| Concept | Concrete implementation |
|---|---|
| Attribute | Set members in dependency models |
| Functional dependency | `FunctionalDependency` objects or SQL relationship rules |
| Attribute closure | Iterative closure algorithms |
| Candidate key | Composite student-course key |
| Partial dependency | Student or course facts depending on one component of the enrollment key |
| Transitive dependency | `course_id -> instructor_id -> instructor_name` |
| 1NF | Atomic student-course enrollment rows |
| 2NF | Removal of partial dependencies |
| 3NF | Separation of instructor facts |
| Update anomaly | Repeated instructor information |
| Insertion anomaly | Course requiring an enrollment to exist |
| Deletion anomaly | Course information disappearing with the last enrollment |
| Decomposition | Student, Instructor, Course, Enrollment relations |
| Referential integrity | PostgreSQL foreign keys |
| Entity uniqueness | Primary and unique constraints |
| Relationship uniqueness | Composite enrollment primary key |
| Transactional integrity | PostgreSQL transactions and savepoints |

## File Relationship

The five executable artifacts form one coherent learning system:

```text
Functional Dependencies
        |
        v
Candidate Keys and Closures
        |
        v
Normalization Analysis
        |
        +------------------+
        |                  |
        v                  v
Anomaly Detection     Policy Evaluation
        |                  |
        +--------+---------+
                 |
                 v
        Relational Decomposition
                 |
                 v
      PostgreSQL Integrity Rules
```

The final database structure is not merely a collection of separate tables. It is the relational consequence of the functional dependencies identified at the beginning of the analysis.
