# Basic Data Modification: UPDATE, DELETE, Conditional Updates, and Safe Deletion

## 1. Topic Introduction

Data modification is the part of SQL used to change existing database state. The two fundamental modification commands covered here are:

- `UPDATE`, which changes values in existing rows.
- `DELETE`, which removes existing rows.

The central safety principle is that a modification statement should be deliberate about **which rows it is allowed to affect**.

A typical update has this structure:

`UPDATE table_name SET column_name = value WHERE condition;`

A typical deletion has this structure:

`DELETE FROM table_name WHERE condition;`

The `WHERE` clause determines the target rows. Omitting it from an `UPDATE` or `DELETE` can cause every row in the table to be modified or deleted.

The three implementations in this study approach the same subject from different perspectives:

- Python demonstrates practical SQL execution with SQLite, transactions, constraints, parameterized statements, auditing, and testing.
- JavaScript demonstrates the application layer that commonly sits between a user interface and a database, including validation, asynchronous repository patterns, optimistic updates, and transaction-style rollback.
- C++ presents an industry-style employee-management case study with domain models, repository design, validation, auditing, bulk modification, optimistic updates, and deletion safeguards.

---

## 2. Fundamental Terminology

### Row

A row is one record in a relational table.

For an `employees` table, one row can represent one employee.

### Column

A column stores one type of attribute for each row.

Examples include:

- `employee_id`
- `full_name`
- `salary`
- `status`
- `performance_score`

### Primary Key

A primary key uniquely identifies a row.

Example:

`employee_id INTEGER PRIMARY KEY`

A primary key is commonly used in targeted updates and deletes because it identifies one specific record.

### Predicate

A predicate is a condition that evaluates whether a row qualifies for an operation.

Example:

`employee_id = 10`

Another example:

`status = 'ACTIVE' AND salary > 50000`

### Affected Rows

The affected-row count tells the application how many records were changed or deleted.

This is useful for detecting unexpected behavior.

If an operation was expected to modify one employee but affected 5,000 rows, the application should treat that as a serious warning.

### Transaction

A transaction groups multiple database changes into one logical operation.

The basic properties are commonly described using ACID:

- Atomicity: changes are treated as one unit.
- Consistency: database rules remain valid.
- Isolation: concurrent transactions are controlled according to the database isolation model.
- Durability: committed changes survive according to the database's durability guarantees.

---

## 3. UPDATE

The `UPDATE` statement changes values in existing rows.

General structure:

`UPDATE table_name SET column1 = value1, column2 = value2 WHERE condition;`

Example:

`UPDATE employees SET salary = 80000 WHERE employee_id = 1;`

This changes the salary of employee 1.

Multiple columns can be changed:

`UPDATE employees SET salary = 80000, status = 'ACTIVE' WHERE employee_id = 1;`

The same `WHERE` condition controls both changes.

### Why WHERE Matters

Consider:

`UPDATE employees SET status = 'INACTIVE';`

This does not mean "update one employee." It means "update every employee."

The absence of `WHERE` is therefore a potentially destructive operation.

---

## 4. Updating From Existing Values

An update does not have to assign a fixed value.

A database can calculate the new value from the existing value.

Example:

`UPDATE employees SET salary = salary * 1.05 WHERE department_id = 1;`

This increases salaries by 5 percent for qualifying rows.

The Python implementation demonstrates this pattern using SQLite.

The advantage of performing the calculation in SQL is that the database can process the operation as a set rather than requiring the application to retrieve every row, calculate a value, and send separate updates.

---

## 5. Conditional Updates

A conditional update modifies only rows satisfying a business rule.

Example:

`UPDATE employees SET status = 'INACTIVE' WHERE status = 'ACTIVE' AND performance_score < 70;`

This has several logical components:

- `status = 'ACTIVE'` restricts the initial population.
- `performance_score < 70` applies the business condition.
- `SET status = 'INACTIVE'` specifies the modification.

Combining conditions is often safer than updating based on one broad criterion.

Common operators include:

- `=`
- `<>`
- `>`
- `<`
- `>=`
- `<=`
- `AND`
- `OR`
- `IN`
- `BETWEEN`
- `LIKE`
- `IS NULL`
- `IS NOT NULL`

---

## 6. CASE-Based Updates

SQL `CASE` expressions are useful when different qualifying rows need different values.

A conceptual example is:

`UPDATE employees SET salary = CASE WHEN performance_score >= 90 THEN salary * 1.10 WHEN performance_score >= 80 THEN salary * 1.07 WHEN performance_score >= 70 THEN salary * 1.04 ELSE salary END WHERE status = 'ACTIVE';`

This expresses multiple business rules in one statement.

The order of conditions matters.

For example, a score of 95 satisfies:

- `performance_score >= 90`
- `performance_score >= 80`
- `performance_score >= 70`

The first matching `WHEN` branch is selected.

---

## 7. DELETE

`DELETE` removes rows from a table.

General structure:

`DELETE FROM table_name WHERE condition;`

Example:

`DELETE FROM employees WHERE employee_id = 5;`

Only employee 5 qualifies.

A conditional deletion might be:

`DELETE FROM employees WHERE status = 'INACTIVE' AND department_id = 4;`

This is substantially narrower than deleting all inactive employees.

---

## 8. The Most Dangerous DELETE Pattern

The statement:

`DELETE FROM employees;`

has no `WHERE` clause.

Every employee qualifies.

This can permanently remove the entire table contents.

The same principle applies to:

`UPDATE employees SET salary = 0;`

It changes every row.

The Python, JavaScript, and C++ implementations deliberately discuss these patterns without executing the destructive form.

---

## 9. Safe Deletion Workflow

A practical deletion workflow is:

1. Define the intended condition.
2. Run a `SELECT` using the same condition.
3. Inspect the candidate rows.
4. Confirm the number of expected rows.
5. Perform the `DELETE`.
6. Check the affected-row count.
7. Use a transaction when the deletion is part of a larger operation.
8. Maintain an audit trail when business or regulatory requirements require it.

For example, first preview:

`SELECT employee_id, full_name FROM employees WHERE status = 'INACTIVE' AND performance_score < 65;`

Then, after confirming the candidates:

`DELETE FROM employees WHERE status = 'INACTIVE' AND performance_score < 65;`

The Python `preview_then_update()` function demonstrates the same safety principle for updates.

---

## 10. Parameterized Statements

Application code should not normally construct SQL by concatenating user-controlled values.

Unsafe conceptual pattern:

`"UPDATE employees SET status = '" + userStatus + "' WHERE employee_id = " + userId`

A malicious or malformed value can change the meaning of the SQL statement.

The safer pattern is parameter binding.

Python demonstrates this with SQLite placeholders:

`UPDATE employees SET status = ? WHERE employee_code = ?`

The values are supplied separately.

Parameterization provides two important benefits:

1. It separates SQL structure from data values.
2. It significantly reduces SQL injection risk when used correctly.

Parameterized values should be used for values such as names, IDs, dates, salaries, statuses, and search terms.

Database identifiers such as table names generally cannot be bound as ordinary values. If dynamic identifiers are required, they should come from a trusted allowlist rather than direct user input.

---

## 11. Row Counts as a Safety Mechanism

Suppose an application expects exactly one employee to be changed.

It can execute an update and inspect the affected-row count.

Expected result:

`1`

Potential results:

`0` means that no row satisfied the condition.

A value greater than `1` may indicate that the condition was broader than intended.

This simple check is especially useful for:

- administrative tools
- financial systems
- inventory systems
- account management
- workflow systems
- record lifecycle operations

The Python and JavaScript implementations use this technique.

---

## 12. Optimistic Conditional Updates

An ordinary update may look like:

`UPDATE employees SET salary = ? WHERE employee_id = ?;`

A more defensive form can include the expected previous value:

`UPDATE employees SET salary = ? WHERE employee_id = ? AND salary = ?;`

The third parameter represents the salary that the application believes is currently stored.

If another transaction changed the salary first, the condition may no longer match.

The result can be zero affected rows.

This is a form of optimistic concurrency control.

It does not replace appropriate database transaction and isolation mechanisms, but it can detect stale application state.

The Python, JavaScript, and C++ examples demonstrate this concept.

---

## 13. Soft Delete Versus Hard Delete

A hard delete physically removes the row:

`DELETE FROM employees WHERE employee_id = 10;`

A soft delete changes the state of the row:

`UPDATE employees SET status = 'INACTIVE' WHERE employee_id = 10;`

Soft deletion can be useful when historical records must remain available.

Advantages include:

- easier recovery
- historical reporting
- auditability
- preservation of relationships
- regulatory retention support

Potential disadvantages include:

- every query may need to exclude inactive rows
- database size continues to grow
- developers can accidentally expose deleted-looking records
- uniqueness rules may become more complicated

The correct approach depends on the application's data-retention requirements.

---

## 14. Transactions

A transaction is important when multiple modifications must succeed or fail together.

Conceptually:

`BEGIN`

perform operation A

perform operation B

`COMMIT`

If an error occurs:

`ROLLBACK`

For example, imagine a salary transfer system that modifies two employee records. Changing one employee and failing before changing the other could leave the system inconsistent.

The Python implementation uses SQLite transactions and explicitly demonstrates rollback after a constraint failure.

The JavaScript implementation models transaction behavior with snapshots because it deliberately avoids requiring an external database driver.

The C++ case study models the same architectural principle at the repository level.

---

## 15. Constraints and UPDATE Safety

Database constraints are an important second line of defense.

The Python database defines:

`CHECK (salary >= 0)`

This prevents negative salaries.

It also defines:

`CHECK (status IN ('ACTIVE', 'INACTIVE'))`

This prevents unsupported status values.

A foreign key connects employees to departments.

These constraints mean the database itself rejects invalid state.

Application validation is still valuable, but application validation should not be considered a replacement for database constraints.

A robust design generally validates at multiple layers.

---

## 16. NULL and Conditional Modification

SQL `NULL` means the absence of a known value. It is not equivalent to zero, an empty string, or false.

Incorrect:

`WHERE performance_score = NULL`

Correct:

`WHERE performance_score IS NULL`

To find values that are present:

`WHERE performance_score IS NOT NULL`

The Python implementation explicitly demonstrates setting a performance score to `NULL` and retrieving the resulting record using `IS NULL`.

---

## 17. Auditing Updates

Some systems need to know:

- who changed a record
- what was changed
- when it changed
- what the previous value was
- what the new value became
- why the change occurred

A separate audit table can preserve this information.

The Python implementation uses `employee_audit`.

The JavaScript implementation maintains an audit collection.

The C++ case study stores `AuditRecord` objects.

A production audit design may contain additional fields such as:

- actor ID
- source application
- IP address where appropriate
- request ID
- reason
- timestamp
- transaction ID
- old values
- new values

Audit requirements vary by system and jurisdiction.

---

## 18. Python Implementation

The Python file uses SQLite through the standard-library `sqlite3` module.

Important demonstrated concepts include:

- database connection
- table creation
- primary keys
- foreign keys
- `CHECK` constraints
- indexes
- `UPDATE`
- calculated updates
- conditional updates
- `CASE`
- parameterized queries
- `DELETE`
- conditional deletion
- affected-row counts
- preview-before-modification
- transactions
- rollback
- soft deletion
- audit records
- `NULL`
- query-plan inspection
- application validation
- lightweight tests

### Why SQLite Is Used

SQLite is part of Python's standard library.

This makes the study implementation self-contained while still using genuine SQL syntax and genuine database behavior.

The database is created in memory using `:memory:`. Consequently, the demonstration does not require a separate database server or external package.

---

## 19. JavaScript Implementation

The JavaScript file focuses on the application layer.

The `EmployeeStore` class models operations that a real database repository could expose.

Its methods correspond conceptually to:

- selecting records
- updating records
- deleting records
- taking a transaction snapshot
- restoring a previous state

The implementation demonstrates:

- object-oriented design
- predicates
- validation
- bulk modification
- conditional updates
- optimistic updates
- previewing candidate records
- safe deletion
- soft deletion
- audit logging
- transaction-style rollback
- asynchronous repository methods
- error propagation
- tests

### Why JavaScript Is Useful Here

JavaScript is frequently used in web applications that receive user input and invoke backend database operations.

The critical architectural boundary is:

user input → validation → application logic → parameterized database operation

The JavaScript implementation emphasizes this boundary without requiring an external npm database package.

---

## 20. C++ Case Study

### Problem Being Modeled

The C++ program models an employee compensation and lifecycle management system.

The system needs to support:

- employee creation
- salary modification
- performance-based raises
- employee status changes
- safe deletion
- soft deletion
- optimistic updates
- auditing
- validation
- bulk operations
- transaction-style recovery

The central concern is controlled modification of business records.

### Major Components

`Employee`

Represents an employee domain object.

`EmployeeRepository`

Provides controlled access to employee records and contains generic update and deletion operations.

`AuditRecord`

Represents historical information about a salary change.

`RepositoryTransaction`

Models the concept of transaction boundaries.

Validation functions enforce domain rules before modifications are accepted.

---

## 21. C++ Generic UPDATE Mechanism

The repository uses a predicate and modifier:

`updateWhere(predicate, modifier)`

The predicate decides whether a row qualifies.

The modifier determines how the qualifying object changes.

This mirrors the conceptual SQL structure:

`UPDATE ... SET ... WHERE ...`

The separation between selection and modification is useful because it makes business rules explicit in application code.

---

## 22. C++ Generic DELETE Mechanism

The repository provides:

`deleteWhere(predicate)`

The predicate decides which records should be removed.

The method then erases matching records.

The case study uses this to remove inactive low-performing employees.

This is conceptually equivalent to:

`DELETE FROM employees WHERE status = 'INACTIVE' AND performance_score < 65;`

---

## 23. C++ Validation

The C++ implementation validates:

- positive employee IDs
- non-empty employee codes
- non-empty names
- non-negative salaries
- performance scores between 0 and 100
- duplicate employee IDs
- duplicate employee codes

This prevents invalid domain objects from entering the repository.

Validation is particularly important before executing a modification because bad input can otherwise propagate into later operations.

---

## 24. C++ Business-Rule Guard

The `guardedPermanentDelete()` function only permits permanent deletion when the employee is already inactive.

This demonstrates an important design principle:

> A destructive operation can be protected by explicit business rules.

Instead of allowing any caller to delete any employee, the repository-facing application function establishes a narrower policy.

---

## 25. Bulk Updates

Bulk updates are efficient because one operation can affect many rows.

Example:

`UPDATE employees SET status = 'INACTIVE' WHERE performance_score < 70 AND status = 'ACTIVE';`

Advantages:

- fewer round trips
- set-based database processing
- simpler SQL for many uniform changes
- potentially better performance

Risks:

- an incorrect predicate can affect many rows
- a large update can lock or otherwise heavily affect database resources
- transaction logs can grow
- indexes may need maintenance
- application assumptions about row counts may become invalid

Large production updates may need batching, scheduling, maintenance windows, or carefully controlled transactions depending on the database and workload.

---

## 26. Performance Considerations

The database must first locate the rows that qualify for an update or delete.

A predicate such as:

`WHERE employee_id = ?`

is especially suitable for a primary-key lookup.

A predicate such as:

`WHERE department_id = ?`

can benefit from an index on `department_id`.

The Python implementation creates:

`CREATE INDEX idx_employees_department ON employees(department_id);`

and:

`CREATE INDEX idx_employees_status ON employees(status);`

Indexes can improve lookup performance, but they also have costs.

Every relevant modification may need to update affected indexes.

Therefore, adding indexes indiscriminately is not automatically beneficial.

The correct index strategy depends on:

- query patterns
- table size
- selectivity
- write volume
- storage
- database engine
- workload characteristics

---

## 27. Query Planning

Before a large modification, developers should understand how the database intends to locate rows.

For example, SQLite supports `EXPLAIN QUERY PLAN`.

The Python implementation demonstrates this with a department lookup.

In production environments, database-specific execution-plan tools can be used to investigate:

- full table scans
- index usage
- inefficient predicates
- joins
- sorting
- locking behavior
- estimated versus actual workload

---

## 28. Security Considerations

The most important security concern associated with application-generated modification SQL is SQL injection.

Do not combine untrusted strings directly into SQL.

Unsafe conceptual construction:

`"DELETE FROM employees WHERE employee_id = " + userInput`

Safer approach:

`DELETE FROM employees WHERE employee_id = ?`

with `userInput` supplied through a parameter-binding mechanism.

Security also involves authorization.

A technically valid update is not automatically an authorized update.

For example, an employee-management system may need to distinguish between:

- ordinary employee
- manager
- HR administrator
- system administrator

The authorization decision should occur before executing a sensitive modification.

Other considerations include:

- database credentials
- least-privilege database accounts
- encrypted connections for remote databases
- audit logging
- secrets management
- input validation
- transaction integrity
- backup and recovery procedures

---

## 29. Common Mistakes

### Mistake 1: Forgetting WHERE

Dangerous:

`UPDATE employees SET salary = 50000;`

Potential effect: every employee receives the new salary.

### Mistake 2: Deleting Without Preview

A broad delete should normally be preceded by a `SELECT` using the same predicate when operational safety requires review.

### Mistake 3: Trusting Application Validation Alone

Applications can contain bugs or can be bypassed.

Database constraints provide an additional integrity boundary.

### Mistake 4: Ignoring Affected Rows

An operation that unexpectedly modifies zero or thousands of rows should not automatically be treated as successful.

### Mistake 5: String-Building SQL

Direct string interpolation of untrusted values can create SQL injection vulnerabilities.

### Mistake 6: Ignoring NULL Semantics

`NULL` should be tested with `IS NULL` or `IS NOT NULL`.

### Mistake 7: Using Hard Delete When History Is Required

A permanent deletion may destroy information needed for reporting, audits, recovery, or compliance.

### Mistake 8: Updating Multiple Records Without a Transaction

Related changes may leave the database in an inconsistent state if one operation succeeds and another fails.

### Mistake 9: Using an Overly Broad Predicate

A condition such as `WHERE department_id = 1` may affect thousands of employees.

The predicate should match the actual business requirement.

### Mistake 10: Assuming an UPDATE Always Changes a Row

A valid SQL statement may affect zero rows because no record satisfies the condition.

---

## 30. Edge Cases

Important edge cases include:

- nonexistent employee ID
- duplicate employee ID
- duplicate business key
- negative salary
- invalid status
- `NULL` values
- zero affected rows
- unexpectedly large affected-row count
- stale data during concurrent modification
- foreign-key dependencies
- empty tables
- repeated deletion
- repeated updates
- failed transaction
- partially completed multi-step operation
- large bulk modification
- incorrect date or timestamp handling

The implementations deliberately exercise several of these cases.

---

## 31. Safe Modification Checklist

Before an important `UPDATE`:

- Confirm the target table.
- Confirm the target columns.
- Write the intended `WHERE` condition.
- Run a matching `SELECT`.
- Check candidate row count.
- Validate input values.
- Use parameterized statements.
- Consider transaction boundaries.
- Consider audit requirements.
- Execute the update.
- Check affected-row count.
- Verify the resulting state.

Before an important `DELETE`:

- Confirm that deletion is actually required.
- Determine whether soft deletion is more appropriate.
- Run a matching `SELECT`.
- Review candidate records.
- Check expected row count.
- Use a narrow predicate.
- Use a transaction where appropriate.
- Check affected-row count.
- Verify related foreign-key behavior.
- Confirm that required audit information has been preserved.

---

## 32. UPDATE Versus DELETE

| Aspect | UPDATE | DELETE |
|---|---|---|
| Primary purpose | Change existing data | Remove rows |
| Existing row remains | Yes | No |
| Can be conditional | Yes | Yes |
| Can affect many rows | Yes | Yes |
| Can be rolled back in a transaction | Yes | Yes |
| Can support soft deletion | Yes | No |
| Risk without WHERE | Changes all rows | Removes all rows |
| Common safety control | WHERE and row-count validation | WHERE, preview, row-count validation |
| Historical preservation | Usually possible | Requires audit or backup mechanisms |

---

## 33. Hard Delete Versus Soft Delete

| Property | Hard Delete | Soft Delete |
|---|---|---|
| Physical row removal | Yes | No |
| Easy recovery | Usually no without backup/audit | Usually yes |
| Storage usage | Lower after deletion | Higher |
| Historical reporting | More difficult | Easier |
| Query complexity | Lower | Higher because inactive rows must often be filtered |
| Audit requirements | Often important | Still important |
| Suitable for retention-sensitive data | Depends on requirements | Often useful |

Neither technique is universally correct. The appropriate choice depends on data lifecycle, legal requirements, business rules, recovery requirements, and system architecture.

---

## 34. Python, JavaScript, and C++ Comparison

### Python

Python provides concise database code and direct SQLite support through its standard library.

It is particularly effective for demonstrating:

- actual SQL execution
- database constraints
- parameter binding
- transactions
- rapid testing
- data-processing workflows

### JavaScript

JavaScript is useful for demonstrating application-layer behavior.

The implementation focuses on:

- validation
- repository abstraction
- asynchronous APIs
- predicates
- UI/backend-style data flow
- error handling
- transaction-style recovery

### C++

C++ provides explicit control over application architecture and data structures.

The case study focuses on:

- domain modeling
- repository design
- templates
- validation
- algorithmic complexity
- controlled mutation
- explicit error handling
- industry-style system structure

The languages therefore demonstrate different layers of the same general problem rather than merely reproducing identical examples.

---

## 35. Implementation Design Principles

A reliable modification system should separate several responsibilities.

### Validation

Determines whether input is structurally and semantically valid.

### Authorization

Determines whether the caller is permitted to perform the operation.

### Selection

Determines which records qualify.

### Modification

Defines what changes.

### Transaction Management

Determines whether multiple operations should succeed or fail together.

### Integrity Constraints

Protect database-level invariants.

### Auditing

Preserves information about important changes.

### Observability

Records useful operational information such as affected-row counts, failures, and transaction outcomes.

Keeping these responsibilities distinct makes the system easier to test and maintain.

---

## 36. Production Considerations

A production database modification workflow may require:

- parameterized queries
- connection pooling
- transaction management
- authorization
- database constraints
- migration management
- audit logging
- monitoring
- structured error handling
- backup and recovery
- concurrency control
- indexing
- query-plan analysis
- operational safeguards
- change management
- data-retention policies

Large destructive operations should receive additional controls because mistakes in `UPDATE` and `DELETE` statements can affect large portions of a production database very quickly.

For high-impact administrative systems, a preview-and-confirm workflow can provide another safety barrier.

---

## 37. Practical Applications

The same concepts appear in many systems.

### Banking

Changing account status, updating customer information, or correcting transaction metadata.

### E-Commerce

Updating inventory, product prices, order status, and customer records.

### Human Resources

Changing employee salaries, departments, employment status, and records.

### Healthcare

Updating administrative records while maintaining strong auditing and access controls.

### Education

Updating enrollment status, grades, student records, and course assignments.

### Logistics

Changing shipment status, inventory quantities, warehouse assignments, and delivery records.

### Cybersecurity

Updating asset status, revoking access, changing incident state, and maintaining security audit records.

---

## 38. Core Principles

The most important technical principles demonstrated by all three implementations are:

1. `UPDATE` changes existing rows.
2. `DELETE` removes rows.
3. `WHERE` controls which rows qualify.
4. A missing `WHERE` can affect every row.
5. Parameterized queries separate SQL from values.
6. Affected-row counts provide useful operational validation.
7. Previewing records before destructive modification reduces operational risk.
8. Transactions allow related changes to succeed or fail as one logical unit.
9. Database constraints protect data integrity.
10. Soft deletion can preserve historical records.
11. Optimistic conditions can detect stale application state.
12. Indexes can improve row-location performance.
13. Auditing can preserve important modification history.
14. Application validation and database constraints serve different but complementary purposes.
15. Security requires both safe SQL construction and proper authorization.
16. Bulk modification requires careful predicates because one statement can affect many records.

The Python implementation demonstrates genuine SQL modification through SQLite, the JavaScript implementation emphasizes application-level repository behavior, and the C++ implementation models a structured production-style domain system around safe data modification.
