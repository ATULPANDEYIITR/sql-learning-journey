# 1NF, 2NF and 3NF: Atomicity, Partial Dependency and Transitive Dependency

## Domain

This project models relational database normalization through a student-course enrollment domain.

The central denormalized relation contains:

| Attribute | Meaning | Functional determinant |
|---|---|---|
| `student_id` | Student identifier | Student |
| `student_name` | Student name | `student_id` |
| `course_id` | Course identifier | Course |
| `course_name` | Course name | `course_id` |
| `instructor_id` | Instructor identifier | Course |
| `instructor_name` | Instructor name | `instructor_id` |
| `grade` | Student's result in a course | `(student_id, course_id)` |

The composite key is `(student_id, course_id)` because one student can take many courses and one course can contain many students.

The important dependencies are:

- `student_id -> student_name`
- `course_id -> course_name, instructor_id`
- `instructor_id -> instructor_name`
- `(student_id, course_id) -> grade`

These dependencies expose the difference between 1NF, 2NF and 3NF.

## Normalization Model

The progression is:

    Unnormalized
        |
        | remove repeating or non-atomic values
        v
       1NF
        |
        | remove partial dependencies
        v
       2NF
        |
        | remove transitive dependencies
        v
       3NF

The three forms address different problems.

| Normal form | Main condition | Problem addressed |
|---|---|---|
| 1NF | Each attribute contains atomic values | Repeating groups and multi-valued cells |
| 2NF | 1NF plus no non-key attribute depends on part of a composite key | Partial dependency |
| 3NF | 2NF plus no non-key attribute depends on another non-key attribute | Transitive dependency |

## 1NF and Atomicity

First Normal Form requires each relation cell to contain one atomic value for the intended relational model.

An example of a problematic representation is:

| student_id | student_name | phone_numbers |
|---:|---|---|
| 1 | Asha | `9000000001,9000000002` |

The `phone_numbers` value contains multiple phone numbers. Searching, updating, validating and constraining individual numbers becomes difficult.

The Python and JavaScript implementations explicitly detect collection-like values. The PostgreSQL implementation includes `one_nf_violation_example` to show the non-atomic design before the normalized model is introduced.

Atomicity is a property of how attributes are modeled for their intended use. A long text value is not automatically non-atomic merely because it contains many characters. The relevant question is whether the value represents one attribute value or an unmodeled collection of independent values.

## 2NF and Partial Dependency

Second Normal Form matters when the candidate key contains multiple attributes.

The enrollment key is:

`(student_id, course_id)`

The following dependencies exist:

`student_id -> student_name`

and

`course_id -> course_name, instructor_id`

Each determinant is only part of the composite enrollment key. Student name does not require the course identifier, and course information does not require the student identifier.

These are partial dependencies.

The `grade` attribute is different:

`(student_id, course_id) -> grade`

A grade describes the relationship between a particular student and a particular course, so it depends on the complete composite key.

The decomposition therefore separates:

- student facts
- course facts
- enrollment facts

This removes repeated student and course information from every enrollment row.

## 3NF and Transitive Dependency

After partial dependencies are removed, the course relation still contains:

`course_id -> instructor_id`

and:

`instructor_id -> instructor_name`

Therefore:

`course_id -> instructor_name`

through `instructor_id`.

`instructor_name` does not directly describe the course identifier. It describes the instructor identifier. This is a transitive dependency.

The 3NF design separates instructors from courses:

    instructor
        |
        | instructor_id
        v
      course
        |
        | course_id
        v
    enrollment

The course table stores `instructor_id` as a foreign key rather than duplicating `instructor_name`.

## Anomalies Prevented

### Update anomaly

In the denormalized relation, an instructor's name may occur in many enrollment rows.

Changing `Dr Rao` to `Dr A. Rao` requires every affected row to be updated. Missing one row produces contradictory data.

In the normalized design, the instructor name is stored once in `instructor`.

### Insertion anomaly

A new instructor cannot be represented cleanly in the denormalized enrollment relation if no enrollment exists yet.

The normalized design permits an instructor to exist independently of course enrollment.

### Deletion anomaly

Deleting the last enrollment for a course from the denormalized table can accidentally remove the only stored copy of course or instructor information.

The normalized design stores those facts independently.

## Python Implementation

The Python file provides a dependency-oriented normalization model.

`FunctionalDependency` represents a determinant and its dependent attributes. `Relation` validates primary keys and rows and evaluates partial and transitive dependency patterns.

The `NormalizedDatabase` class then implements the resulting 3NF structure with separate dictionaries for:

- students
- instructors
- courses
- enrollments

Validation rejects:

- empty names
- missing referenced entities
- duplicate enrollment relationships
- invalid grades
- duplicate enrollment identifiers

The transcript operation reconstructs the required reporting view by joining normalized structures at runtime.

Assertions verify that an appropriately modeled relation is classified as 3NF.

## JavaScript Implementation

The JavaScript file uses `Set` and `Map` to represent relation metadata and normalized entities.

The normalization analyzer distinguishes:

- atomic values
- composite keys
- partial dependencies
- transitive dependency candidates

The domain service uses event-driven behavior. Entity creation and enrollment emit events that are collected into an audit structure.

The implementation also writes the resulting domain audit events to `normalization-audit.json` using Node.js standard-library file handling.

The audit data intentionally contains domain events rather than credentials or other sensitive information.

Asynchronous file handling uses `async`/`await`, while validation errors are represented by a dedicated `ValidationError` class.

## C++17 Implementation

The C++ program treats normalization as a relation-analysis case study.

`Relation` stores:

- relation columns
- primary key
- rows
- functional dependencies

`std::set` is used for attribute sets, while `std::map` represents row attributes. This makes dependency comparisons explicit and deterministic.

The second part uses a strongly typed normalized domain model:

- `Student`
- `Instructor`
- `Course`
- `Enrollment`

`GovernanceDatabase` maintains the relationships using hash maps and validates references before insertion.

The implementation demonstrates how normalization can be enforced at the domain layer rather than relying exclusively on database constraints.

## Java 17 Implementation

The Java implementation uses records for immutable domain values:

- `Student`
- `Instructor`
- `Course`
- `Enrollment`
- `FunctionalDependency`
- `TranscriptEntry`

`EnrollmentRepository` separates persistence behavior from the service layer. The provided in-memory repository enforces uniqueness of both enrollment identifiers and student-course relationships.

`EnrollmentService` performs domain validation before persistence.

The model uses explicit `Grade` and `NormalForm` enums, custom domain exceptions, immutable collections where appropriate, and stream-based transcript construction.

This separates structural normalization analysis from application-level domain rules.

## PostgreSQL Implementation

The SQL file provides both the problematic source relation and the normalized schema.

The normalized tables are:

| Table | Primary key | Main dependency |
|---|---|---|
| `student` | `student_id` | `student_id -> student_name` |
| `instructor` | `instructor_id` | `instructor_id -> instructor_name` |
| `course` | `course_id` | `course_id -> course_name, instructor_id` |
| `enrollment` | `(student_id, course_id)` | `(student_id, course_id) -> grade` |

Foreign keys enforce the relationships between these relations.

The database also contains:

- primary-key constraints
- check constraints
- foreign keys
- indexes
- a reporting view
- a validation trigger
- common reporting queries
- CTE-based aggregation
- transactional examples
- deletion behavior
- dependency inspection queries

`ON DELETE CASCADE` is used for student-to-enrollment relationships because enrollment is dependent on the existence of its student.

`ON DELETE RESTRICT` is used where removing the referenced course or instructor while dependent business objects remain would violate the domain model.

## Integrity and Transactions

Normalization does not replace integrity constraints.

The PostgreSQL implementation therefore enforces rules at the database level.

Examples include:

- duplicate student-course pairs are rejected by the composite primary key
- invalid grades are rejected by a `CHECK` constraint
- unknown students cannot be referenced
- unknown courses cannot be referenced
- courses cannot reference nonexistent instructors
- blank student names are rejected
- related writes can be committed atomically

The transaction examples show that atomicity at the transaction level is separate from atomicity in 1NF.

These two uses of the word "atomicity" should not be confused:

| Term | Meaning |
|---|---|
| Atomic attribute value | A 1NF modeling property |
| Atomic transaction | A transaction either commits as a unit or does not |

## Design Distinctions

Normalization is not simply splitting every table into smaller tables.

The decomposition is based on functional dependencies and keys.

The key questions are:

1. What fact is being represented?
2. What attribute or combination of attributes determines that fact?
3. Is that determinant a complete candidate key?
4. If the key is composite, does the fact depend on only part of it?
5. Does a non-key attribute determine another non-key attribute?

For this domain:

`student_id` determines student facts.

`course_id` determines course facts.

`instructor_id` determines instructor facts.

`(student_id, course_id)` determines enrollment-specific facts.

That dependency structure determines the decomposition.

## Edge Cases

The implementations explicitly address:

- empty identifiers
- duplicate identifiers
- duplicate student-course enrollment
- missing foreign references
- invalid grades
- empty names
- non-atomic values
- partial dependencies
- transitive dependencies
- failed transactional operations
- deletion behavior
- reconstruction of reporting data through joins

A normalized schema does not guarantee correct business semantics by itself. Domain-specific constraints still need to be modeled.

## Performance Considerations

Normalization can increase the number of joins required for read queries.

The normalized design accepts this cost to avoid redundant facts and inconsistent updates.

The PostgreSQL implementation adds indexes for common relationship lookups:

- `enrollment(course_id)`
- `course(instructor_id)`

The application implementations use maps keyed by identifiers to make direct entity lookup efficient.

The trade-off is therefore:

| Approach | Benefit | Cost |
|---|---|---|
| Denormalized | Fewer joins for some reads | Redundancy and anomalies |
| Normalized | Consistency and clear dependency ownership | More joins for reconstructed views |

Indexes should follow actual query patterns rather than being added indiscriminately.

## Security and Integrity Considerations

Normalization is primarily a data-modeling technique, not a security control.

The implementations still apply integrity protections relevant to the domain:

- foreign-key enforcement
- constrained enumerated values
- validation before writes
- duplicate prevention
- controlled deletion semantics
- restricted instructor deletion
- avoidance of duplicated sensitive or operational facts
- audit events that do not contain credentials

In production database applications, SQL statements should also use parameterized queries rather than constructing SQL from untrusted input.

## Relationship Between the Three Forms

The dependency chain can be represented as:

    Student
      |
      | student_id -> student_name
      v

    Enrollment
      |
      | (student_id, course_id) -> grade
      |
      +---- Course
      |       |
      |       | course_id -> course_name, instructor_id
      |       v
      |    Instructor
      |       |
      |       | instructor_id -> instructor_name

1NF establishes atomic attribute values.

2NF removes facts that depend on only part of a composite key.

3NF removes non-key-to-non-key dependency chains.

The resulting schema stores each major fact according to the determinant that actually identifies it.
