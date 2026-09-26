# Constraints Introduction: Constraints, Data Integrity, and Constraint Enforcement

## Topic

**Constraints, data integrity, and constraint enforcement**

This study material examines how data constraints protect the correctness, consistency, and reliability of structured data. The implementations use Python with SQLite, JavaScript with an explicit in-memory relational model, and C++ with an industry-style order-management case study.

The central principle is that important data invariants should be enforced as close as possible to the authoritative data store. Application validation remains useful for user feedback and early error detection, but it should not be the only protection for important integrity rules.

---

## 1. What Is a Constraint?

A database constraint is a rule imposed on stored data. The database evaluates the rule when data is inserted, updated, or deleted and rejects an operation that would violate the rule.

Typical constraints include:

- `NOT NULL`
- `PRIMARY KEY`
- `UNIQUE`
- `CHECK`
- `DEFAULT`
- `FOREIGN KEY`

Constraints convert assumptions about valid data into enforceable rules.

For example, if a customer must have a unique email address, the requirement should be represented as a database-level uniqueness rule rather than relying only on application code.

Conceptually:

`customer.email` must be unique.

The application may check the email before insertion, but another application, API endpoint, worker, script, or administrative process could bypass that check. A database constraint provides a common enforcement boundary.

---

## 2. Data Integrity

Data integrity means maintaining the correctness and consistency of data throughout its lifecycle.

Several integrity categories are particularly important.

### 2.1 Entity integrity

Entity integrity ensures that each row can be uniquely identified.

A primary key normally provides this property.

Example:

`customer_id` identifies a customer.

The database must not allow two customers to have the same primary-key value.

### 2.2 Domain integrity

Domain integrity restricts values to an acceptable domain.

Examples:

- age must be at least 18
- price must not be negative
- order quantity must be greater than zero
- status must be one of a defined set of values

A `CHECK` constraint is frequently used for these rules.

### 2.3 Referential integrity

Referential integrity ensures that relationships between tables remain valid.

If an order contains `customer_id = 25`, the referenced customer should exist unless the schema explicitly allows a nullable relationship.

A foreign key provides this protection.

### 2.4 Business integrity

Business integrity represents rules specific to the application.

Examples:

- only active accounts may have a particular unique identifier
- an order must contain at least one product
- an account balance cannot become negative
- a reservation must have an end time after its start time

Some business rules fit directly into database constraints. More complicated rules may require transactions, triggers, specialized database features, or application workflows.

---

## 3. `NOT NULL`

`NOT NULL` requires a column to contain a value rather than SQL `NULL`.

Example:

`email TEXT NOT NULL`

This prevents an explicitly missing value.

The Python implementation demonstrates this through the `customers` table.

The JavaScript implementation models the same rule using `ColumnDefinition`.

The C++ case study treats required customer and product fields as invalid when they are empty.

### Important distinction

`NULL` is not the same thing as:

- an empty string
- zero
- `false`
- a missing business concept

SQL `NULL` represents the absence or unknown nature of a value.

Whether an application should allow `NULL` is a schema-design decision.

---

## 4. `PRIMARY KEY`

A primary key identifies rows uniquely.

Example:

`customer_id INTEGER PRIMARY KEY`

A primary key provides entity identity and prevents duplicate identifiers.

The Python implementation uses SQLite's primary-key enforcement.

The JavaScript implementation uses a `primaryKey` definition and checks existing rows before insertion.

The C++ implementation uses `unordered_map<int, Customer>` and explicitly rejects duplicate IDs.

### Primary key versus `UNIQUE`

A primary key and a unique constraint are related but serve different semantic purposes.

A primary key is the principal identity of a row.

A table may have multiple unique constraints but normally has one primary-key definition.

For example:

- `customer_id` can be the primary key.
- `email` can have a unique constraint.

---

## 5. `UNIQUE`

A `UNIQUE` constraint prevents duplicate values for a column or combination of columns.

Example:

`email TEXT NOT NULL UNIQUE`

This means two customers cannot have the same email value under the database engine's uniqueness semantics.

The Python example intentionally attempts a duplicate email and demonstrates that SQLite rejects it.

The JavaScript model maintains uniqueness explicitly.

The C++ application maintains a hash-based email index.

### Why database-level uniqueness matters

Consider this sequence:

1. Application checks whether an email exists.
2. Application sees that it does not exist.
3. Another request inserts the same email.
4. First request attempts its insertion.

The application-level check did not protect against the race.

A database-level unique constraint is the authoritative rule.

---

## 6. Composite Constraints

A constraint can involve multiple columns.

Example:

`PRIMARY KEY (student_id, course_id)`

This means the pair must be unique.

The same student can enroll in many courses.

The same course can contain many students.

The combination of student and course identifies a particular enrollment.

The JavaScript implementation demonstrates a composite key using:

`["studentId", "courseId"]`

The C++ case study applies the same concept to order items:

`(order_id, product_id)`

This prevents the same product from appearing twice within one order.

### Composite uniqueness

A composite `UNIQUE` rule works similarly.

For example:

`UNIQUE (room_id, booking_date, start_time)`

The complete combination must be unique.

This does not mean each individual column must be unique.

---

## 7. `CHECK`

A `CHECK` constraint expresses a logical condition.

Examples:

`age >= 18`

`price_cents >= 0`

`amount_cents > 0`

`status IN ('active', 'inactive')`

`start_time < end_time`

The Python implementation uses `CHECK` constraints extensively.

The JavaScript implementation represents checks as functions.

The C++ case study explicitly enforces:

- non-negative prices
- non-negative inventory
- positive quantities
- quantities within available stock
- non-empty order contents
- valid relationships

### Row-local rules

`CHECK` is particularly effective for row-local rules.

For example:

`price_cents >= 0`

depends only on the current row.

A much more complicated rule such as:

"the total exposure of all accounts belonging to a customer must remain below a limit"

is not naturally represented by a simple row-level check.

---

## 8. `DEFAULT`

A default supplies a value when an insert does not provide one.

Example:

`status TEXT NOT NULL DEFAULT 'active'`

If the application omits `status`, the database supplies `active`.

Defaults are useful for:

- status fields
- timestamps
- boolean flags
- counters
- lifecycle states

A default does not necessarily mean the application should omit validation. The resulting value still needs to satisfy all applicable constraints.

---

## 9. Foreign Keys

A foreign key establishes a relationship between a child table and a parent table.

For example:

`orders.customer_id`

can reference:

`customers.customer_id`

The parent customer must exist before a valid order can reference that customer.

The Python implementation explicitly enables SQLite foreign-key enforcement using:

`PRAGMA foreign_keys = ON`

This is an important SQLite-specific detail. A foreign-key definition alone should not be assumed to provide the desired enforcement unless the database configuration enables it.

The JavaScript implementation validates every defined foreign-key relationship.

The C++ case study rejects order creation when the requested customer does not exist.

---

## 10. Referential Actions

Foreign keys can define what happens when a referenced parent row changes.

Common actions include:

- `RESTRICT`
- `CASCADE`
- `SET NULL`
- `SET DEFAULT`

### `RESTRICT`

A parent cannot be deleted while dependent rows reference it.

The C++ case study uses this concept for customers and orders.

This is appropriate when historical orders must remain associated with an existing customer record.

### `CASCADE`

A parent operation can propagate to dependent rows.

This can be useful when dependent data has no independent meaning.

It must be used carefully because deleting a parent can remove a large amount of dependent data.

### `SET NULL`

The child foreign-key value becomes `NULL`.

This requires the child foreign-key column to allow `NULL`.

The Python and JavaScript demonstrations include a department and employee relationship in which deleting a department sets the employee's department reference to `NULL`.

---

## 11. NULL and Three-Valued Logic

SQL logic differs from ordinary two-valued Boolean logic.

SQL commonly works with:

- `TRUE`
- `FALSE`
- `UNKNOWN`

Comparisons involving `NULL` often produce `UNKNOWN`.

For example:

`NULL > 0`

does not evaluate as ordinary `TRUE` or `FALSE`.

This creates subtle behavior for constraints.

The Python implementation demonstrates that a nullable column with a `CHECK` expression can behave differently from a column that combines the same `CHECK` with `NOT NULL`.

This is why a rule such as:

`score BETWEEN 0 AND 100`

may need:

`score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100)`

when a score is required.

### NULL and UNIQUE

NULL handling under uniqueness is database-engine-specific in important details. Schema designers should verify the target DBMS behavior instead of assuming every database treats multiple NULL values identically.

The JavaScript example explicitly documents the chosen educational behavior.

---

## 12. Conditional Uniqueness

Sometimes uniqueness should apply only to a subset of rows.

Example requirement:

"Only active accounts must have unique phone numbers."

A standard unique constraint on `phone` may be too restrictive if historical inactive records are allowed to share the value.

SQLite supports partial indexes, so the Python implementation creates a partial unique index with a condition equivalent to:

`WHERE is_active = 1`

The JavaScript implementation models the same idea through a `partialUniqueIndexes` definition.

This demonstrates an important schema-design principle:

**The constraint should express the actual business rule rather than a simpler approximation of it.**

---

## 13. Transactions and Atomicity

A transaction groups related database operations into one logical unit.

Atomicity means that a transaction should not leave behind only part of a business operation.

The Python implementation demonstrates transaction boundaries and savepoints.

The JavaScript implementation creates a database snapshot before a transaction and restores it after failure.

The C++ case study uses a snapshot-based transaction model.

### Order example

Suppose an order requires:

1. validating customer identity
2. validating products
3. checking inventory
4. creating the order
5. reducing inventory
6. creating order-item records

If step 6 fails but steps 4 and 5 remain committed, the system can become inconsistent.

The complete business operation should be atomic.

---

## 14. C++ Case Study: Order Management System

The C++ program models a small commerce system containing:

- customers
- products
- orders
- order items
- product inventory

### Problem being solved

The system must prevent invalid orders and protect the relationships between business entities.

Examples of invalid states include:

- duplicate customer IDs
- duplicate customer emails
- duplicate product SKUs
- negative product prices
- negative inventory
- orders referencing nonexistent customers
- order items referencing nonexistent products
- zero or negative quantities
- quantities greater than available stock
- duplicate products within one order
- deletion of customers whose orders still exist

### Architecture

The major component is:

`OrderDatabase`

It maintains:

- customer records
- product records
- order records
- order-item records
- uniqueness indexes
- transaction snapshots

The program uses standard-library containers rather than an external database library.

---

## 15. C++ Data Structures

The case study uses `unordered_map` for primary-key-based storage.

Conceptually:

`customer_id -> Customer`

and:

`product_id -> Product`

This gives average constant-time lookup under typical hash-table assumptions.

The program also uses:

`unordered_map<string, int>`

for unique email and SKU indexes.

Order items use a composite key:

`(order_id, product_id)`

The C++ implementation supplies a custom hash function for this composite key.

This illustrates how relational uniqueness concepts map to in-memory data structures.

---

## 16. C++ Constraint Enforcement

### Primary key

`addCustomer()` rejects an existing customer ID.

`addProduct()` rejects an existing product ID.

### NOT NULL

Required strings are checked before storage.

### UNIQUE

Customer email and product SKU are indexed and checked for duplicates.

### CHECK

The implementation rejects:

- negative prices
- negative stock
- zero quantity
- negative quantity
- orders exceeding available stock
- empty orders

### FOREIGN KEY

An order cannot reference a nonexistent customer.

An order item cannot reference a nonexistent product.

### Referential integrity

Customer deletion is restricted if an order references that customer.

This models `ON DELETE RESTRICT`.

---

## 17. Composite Key Enforcement in the C++ Case Study

An order item is conceptually identified by:

`order_id + product_id`

Therefore, one product cannot be inserted twice into the same order.

The C++ program checks duplicate product IDs before creating the order.

This corresponds to the relational concept:

`PRIMARY KEY (order_id, product_id)`

The same product can still appear in different orders because the complete composite key is different.

---

## 18. Inventory Integrity

Inventory introduces a useful business invariant:

`remaining_stock >= 0`

Before creating an order, the C++ implementation checks:

`requested_quantity <= available_stock`

Only after validation succeeds does it reduce inventory.

This prevents a negative-stock state.

The boundary case where the requested quantity equals available stock is accepted, leaving stock at zero.

The case where the requested quantity exceeds available stock is rejected.

---

## 19. Monetary Values

The C++ case study stores money as integer cents:

`int64_t priceCents`

This avoids many floating-point representation problems associated with using binary floating-point values for currency.

For example:

`4999`

represents:

`49.99`

when the currency unit is cents.

The program also checks for integer overflow before calculating order totals.

This is an implementation consideration rather than a constraint syntax issue, but it is important when integrity rules depend on financial calculations.

---

## 20. Transaction Rollback in the C++ Case Study

The transaction demonstration performs two order operations.

The first operation is valid.

The second operation deliberately requests excessive stock.

The transaction fails and the database restores its previous snapshot.

The expected invariant is:

- no partial order remains
- inventory returns to its original value

This demonstrates atomicity at the application-model level.

A real database provides transaction durability, isolation, concurrency control, recovery, and other properties that a simple C++ snapshot does not reproduce.

---

## 21. Python Implementation

The Python implementation uses SQLite through Python's built-in `sqlite3` module.

This makes it possible to demonstrate actual database constraint behavior without an external package.

The schema includes:

- customers
- orders
- products
- course enrollments
- room bookings
- departments
- employees
- accounts
- user accounts
- audit events

### Python demonstrates actual database enforcement

The Python code intentionally executes invalid statements and catches `sqlite3.IntegrityError`.

Examples include:

- duplicate primary keys
- duplicate unique values
- NULL in required columns
- invalid CHECK values
- invalid foreign keys
- invalid monetary amounts

It also demonstrates schema inspection with SQLite metadata queries.

---

## 22. JavaScript Implementation

The JavaScript file builds an in-memory relational-style engine.

The main classes are:

- `ConstraintError`
- `TransactionError`
- `ColumnDefinition`
- `Table`
- `ForeignKeyDefinition`
- `Database`

### Why use an in-memory implementation?

The objective is to expose the mechanics of constraint enforcement.

A relational database normally performs these operations internally. The JavaScript implementation makes the process visible:

1. build a candidate row
2. apply defaults
3. check required fields
4. check primary-key uniqueness
5. check unique constraints
6. evaluate checks
7. evaluate conditional uniqueness
8. validate foreign keys
9. store the row

This complements the Python implementation, where the database engine itself performs the enforcement.

---

## 23. Python and JavaScript Comparison

| Aspect | Python + SQLite | JavaScript Model |
|---|---|---|
| Constraint enforcement | Actual SQLite engine | Explicit application model |
| Foreign keys | SQLite | Custom implementation |
| CHECK | SQL expressions | JavaScript functions |
| UNIQUE | Database constraint/index | Explicit row/index checks |
| Transactions | SQLite transaction mechanisms | Snapshot rollback |
| Persistence | SQLite database | In-memory only |
| SQL semantics | Actual SQL semantics | Simplified educational model |
| Best demonstration | Real database behavior | Internal enforcement mechanics |

The Python implementation is closer to actual relational database behavior.

The JavaScript implementation is useful for understanding what the database is conceptually enforcing.

---

## 24. Validation Layers

A robust application commonly has multiple validation layers.

### Client validation

Useful for immediate feedback.

### Application/service validation

Useful for:

- business workflows
- input normalization
- detailed error messages
- request-level rules

### Database constraints

Useful for authoritative persisted-data integrity.

These layers have different responsibilities.

Application validation should not be treated as a replacement for database constraints when the database is shared by multiple clients.

---

## 25. Constraint Errors

Constraint violations should be handled deliberately.

The Python implementation demonstrates `sqlite3.IntegrityError`.

The JavaScript implementation defines `ConstraintError` and stores the constraint category.

The C++ implementation defines `ConstraintViolation` with a `ConstraintType` enumeration.

The categories include:

- `NOT NULL`
- `PRIMARY KEY`
- `UNIQUE`
- `CHECK`
- `FOREIGN KEY`
- `TRANSACTION`

Applications can translate these failures into appropriate user-facing or API-level responses.

Raw database error text should not automatically become the public API contract because wording varies between database engines and versions.

---

## 26. Edge Cases

Important edge cases include:

### NULL

A nullable value may behave differently from an ordinary value under comparison and uniqueness rules.

### Boundary values

Examples:

- age exactly 18
- price exactly zero
- stock exactly zero
- quantity exactly equal to available stock

Boundary behavior should be deliberately defined and tested.

### Duplicate composite values

The complete combination matters.

### Missing parent rows

Foreign keys reject dangling relationships.

### Parent deletion

The schema must explicitly determine whether deletion should:

- fail
- cascade
- set a reference to NULL
- use a default value

### Empty collections

Rules such as "an order must contain at least one product" are not automatically implied by ordinary row-level foreign keys.

---

## 27. Cross-Row Constraints

Simple constraints are excellent for local invariants.

Examples:

`price >= 0`

`age >= 18`

`status IN (...)`

Cross-row rules are more complicated.

Examples:

- no overlapping reservations
- aggregate account exposure below a limit
- total allocation across child rows cannot exceed a parent limit

These rules may require:

- transactions
- locking
- database-specific constraints
- triggers
- stored procedures
- carefully designed application logic
- serialization mechanisms

The exact solution depends on the DBMS and consistency requirements.

---

## 28. Constraints Versus Indexes

A constraint represents a data-integrity rule.

An index primarily supports efficient access.

A `UNIQUE` constraint often requires an index or an equivalent internal structure to efficiently identify duplicates.

Indexes have costs:

- additional storage
- additional write work
- maintenance during inserts
- maintenance during updates
- possible memory pressure

Therefore, indexes should be designed according to both integrity and query requirements.

---

## 29. Performance Considerations

Constraint enforcement itself has a cost.

A database may need to:

- inspect an index for duplicate values
- locate a parent row for a foreign-key check
- evaluate a `CHECK` expression
- maintain indexes during writes

Good indexing can make these operations efficient.

The C++ program illustrates average O(1) hash-based lookups for its in-memory primary-key and unique-value structures.

Actual database systems frequently use B-tree or similar index structures, where lookup characteristics differ from hash tables.

Performance should therefore be evaluated against the specific DBMS and workload.

---

## 30. Concurrency Considerations

Concurrency creates a major reason to enforce important integrity rules in the database.

A naive application sequence might be:

1. query whether email exists
2. receive "not found"
3. wait
4. insert email

Two concurrent requests can both observe "not found."

A database-level unique constraint prevents both from becoming valid duplicate rows.

Similarly, inventory operations need transaction and concurrency control when multiple customers can purchase the same limited stock simultaneously.

The C++ program demonstrates atomic rollback but does not simulate multiple concurrent threads or database isolation levels.

A production database is responsible for stronger concurrency guarantees.

---

## 31. Security Considerations

Constraints improve data correctness but are not a replacement for security controls.

Constraints do not provide:

- authentication
- authorization
- role management
- session security
- encryption
- SQL injection protection
- auditing

When an actual SQL database is used, applications should use parameterized queries rather than constructing SQL by concatenating untrusted input.

Database accounts should follow least-privilege principles.

Sensitive operations may also require audit logging.

---

## 32. Migration Considerations

Adding a constraint to an existing database can fail if existing data violates the proposed rule.

For example, adding:

`UNIQUE(email)`

requires existing duplicate emails to be addressed.

Adding:

`NOT NULL`

requires existing NULL values to be handled.

Adding a foreign key requires existing child records to have valid parents.

A safe migration process generally requires:

1. inspect existing data
2. identify violations
3. determine the intended correction
4. repair or migrate incompatible data
5. introduce the constraint
6. verify the resulting schema

The exact migration strategy depends on database engine capabilities and production requirements.

---

## 33. Common Mistakes

### Mistake 1: Only validating in the UI

A user interface is not an authoritative data-integrity boundary.

### Mistake 2: Ignoring NULL semantics

NULL is not equivalent to zero or an empty string.

### Mistake 3: Forgetting foreign-key enforcement

A schema may declare a relationship but still require database-specific configuration to enforce it.

### Mistake 4: Using overly broad cascading deletes

A cascade can delete large amounts of dependent data.

### Mistake 5: Performing check-then-insert uniqueness logic without a database constraint

This creates race-condition risk.

### Mistake 6: Ignoring transactions

Multi-step operations can leave partial state when one step fails.

### Mistake 7: Treating all business rules as row-level CHECK constraints

Cross-row and temporal rules often require stronger mechanisms.

### Mistake 8: Creating unnecessary indexes

Indexes improve access and constraint checking but increase storage and write costs.

### Mistake 9: Assuming database engines behave identically

SQL standards and DBMS implementations have differences in constraint behavior, NULL semantics, indexes, transaction behavior, and supported features.

### Mistake 10: Treating constraints as security controls

Integrity and authorization are separate concerns.

---

## 34. Best Practices

1. Define important invariants explicitly.
2. Use primary keys for entity identity.
3. Use `NOT NULL` when a value is genuinely required.
4. Use `UNIQUE` for authoritative uniqueness rules.
5. Use `CHECK` for appropriate domain and row-level business rules.
6. Use foreign keys for relational integrity.
7. Select referential actions according to business meaning.
8. Use composite constraints when uniqueness depends on multiple attributes.
9. Understand NULL semantics before designing nullable constraints.
10. Use transactions for multi-step atomic business operations.
11. Keep application validation for early feedback.
12. Keep authoritative integrity rules at the database boundary.
13. Test both valid and invalid operations.
14. Consider index maintenance costs.
15. Plan constraint changes as database migrations.
16. Use parameterized SQL in applications.
17. Separate integrity rules from authorization rules.
18. Document non-obvious business constraints.
19. Verify behavior against the actual DBMS used in production.
20. Consider concurrency when designing rules involving multiple operations.

---

## 35. Implementation Mapping

### Python

The Python implementation demonstrates actual SQLite behavior.

Important functions include:

- `connect_database()`
- `create_basic_schema()`
- `demonstrate_basic_constraints()`
- `demonstrate_null_semantics()`
- `demonstrate_referential_actions()`
- `demonstrate_transactions()`
- `demonstrate_partial_unique_index()`
- `demonstrate_deferred_foreign_key()`
- `run_constraint_tests()`

### JavaScript

The JavaScript implementation demonstrates the internal mechanics of constraint enforcement.

Important classes include:

- `ColumnDefinition`
- `Table`
- `ForeignKeyDefinition`
- `Database`
- `ConstraintError`

Important mechanisms include:

- row construction
- default application
- primary-key checks
- unique checks
- check functions
- foreign-key validation
- referential actions
- transaction snapshots
- conditional uniqueness

### C++

The C++ implementation models a realistic order-management system.

Important components include:

- `OrderDatabase`
- `Customer`
- `Product`
- `Order`
- `OrderItem`
- `ConstraintViolation`
- `ConstraintType`

The case study demonstrates how constraints interact with inventory, customer relationships, orders, composite keys, financial calculations, and transaction rollback.

---

## 36. Important Distinctions

| Concept | Main Purpose |
|---|---|
| `NOT NULL` | Prevent missing values |
| `PRIMARY KEY` | Identify rows uniquely |
| `UNIQUE` | Prevent duplicate values or combinations |
| `CHECK` | Enforce logical/domain conditions |
| `DEFAULT` | Supply an omitted value |
| `FOREIGN KEY` | Protect relationships between tables |
| `RESTRICT` | Prevent a destructive parent operation |
| `CASCADE` | Propagate a parent operation |
| `SET NULL` | Remove the child reference |
| Transaction | Group changes atomically |
| Index | Improve access and often support efficient constraint enforcement |
| Application validation | Improve early feedback and workflow validation |

---

## 37. Production Perspective

A production schema should treat integrity rules as part of the system architecture rather than as incidental validation code.

For a commerce system, representative invariants include:

- every customer has a unique identifier
- every customer email is unique when required
- every product has a unique SKU
- prices cannot be negative
- inventory cannot become negative
- every order references an existing customer
- every order item references an existing product
- an order item cannot be duplicated within the same order
- an order and its inventory changes are atomic
- deletion behavior for historical entities is explicitly defined

The Python implementation shows how a database engine can enforce these rules directly.

The JavaScript implementation exposes the mechanics behind the rules.

The C++ implementation shows how the same concepts influence architecture, data structures, algorithms, error handling, transactions, and business logic in a realistic system.

---

## 38. Practical Relevance

Constraints are fundamental to reliable data systems because application logic changes over time while stored data often persists for years.

A database may be accessed by:

- web applications
- mobile applications
- administrative tools
- background workers
- analytics processes
- scheduled jobs
- integration services
- command-line programs

If integrity depends only on one application path, another path can accidentally create invalid state.

Database constraints establish a common protection boundary.

The strongest designs combine:

- clear schema modeling
- appropriate constraints
- transactions
- suitable indexes
- application validation
- concurrency control
- error handling
- migration discipline
- security controls
- comprehensive testing

These mechanisms work together to preserve data integrity rather than treating constraint enforcement as a single isolated feature.
