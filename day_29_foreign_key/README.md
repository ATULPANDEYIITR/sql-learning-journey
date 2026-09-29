# Foreign Keys: Referential Integrity, Parent-Child Relationships, and Cascading Actions

## 1. Topic Introduction

A **foreign key** is a relational database constraint that connects rows in one table to rows in another table.

The table containing the foreign key is normally called the **child table**. The table containing the referenced primary key or candidate key is normally called the **parent table**.

A typical relationship is:

`customers` → `orders`

A customer can have many orders. Each order belongs to an existing customer.

The foreign key ensures that an order cannot reference a customer that does not exist.

This is the foundation of **referential integrity**.

The implementations in this study use three different perspectives:

- Python uses SQLite to demonstrate actual relational database behavior.
- JavaScript builds a small in-memory relational integrity model so the foreign-key mechanisms can be observed directly.
- C++ develops an industry-style commerce case study with customers, orders, payments, indexes, transactions, and cascading behavior.

---

## 2. Fundamental Terminology

### Primary Key

A **primary key** uniquely identifies a row.

Example:

`customer_id = 101`

A primary key should uniquely identify one customer.

A table can have only one primary-key constraint, although that primary key can contain multiple columns.

### Foreign Key

A **foreign key** contains values that refer to a key in another table.

Example:

`orders.customer_id` references `customers.customer_id`.

### Parent Table

The parent table contains the referenced key.

Example:

`customers` is the parent of `orders`.

### Child Table

The child table contains the foreign key.

Example:

`orders` is the child of `customers`.

### Referential Integrity

Referential integrity means that a foreign-key reference must remain valid according to the rules defined by the database.

For example, if an order contains `customer_id = 10`, customer 10 must exist unless the relationship is represented as `NULL` and the schema permits a nullable relationship.

### Orphan Row

An **orphan row** is a child row whose parent no longer exists.

For example:

`orders.customer_id = 10`

when no row exists in `customers` with `customer_id = 10`.

Foreign keys are designed to prevent this type of invalid state.

---

## 3. Basic Parent-Child Structure

A basic relationship can be represented as:

`customers(customer_id)`  
`orders(order_id, customer_id)`

The important relationship is:

`orders.customer_id → customers.customer_id`

The parent key must normally be unique. A primary key naturally satisfies this requirement.

A child row can then contain:

`customer_id = 5`

only when customer 5 is a valid referenced parent.

---

## 4. One-to-Many Relationships

Foreign keys are commonly used to represent one-to-many relationships.

For example:

`Customer 1 → Order 101`  
`Customer 1 → Order 102`  
`Customer 2 → Order 103`

One customer can have many orders.

Each order normally has one customer.

The foreign key does not by itself mean that every parent must have a child. A customer may exist without any orders.

The foreign key establishes the validity of the child-to-parent reference.

---

## 5. Referential Integrity

Suppose the parent table contains:

| customer_id | name |
| --- | --- |
| 1 | Anika |
| 2 | Rahul |

A valid child row is:

| order_id | customer_id |
| --- | --- |
| 101 | 1 |

An invalid child row is:

| order_id | customer_id |
| --- | --- |
| 102 | 999 |

because customer 999 does not exist.

The Python implementation deliberately attempts the invalid insertion and captures the resulting integrity error.

This demonstrates an important database principle:

**A constraint is enforced by the database, not merely by application code.**

---

## 6. Foreign-Key Enforcement

SQLite has an important implementation detail: foreign-key enforcement must be enabled for the connection.

The Python program executes:

`PRAGMA foreign_keys = ON`

This is important because writing a `FOREIGN KEY` declaration and actually enforcing the relationship are separate concerns in SQLite.

Applications using SQLite should ensure that foreign-key enforcement is enabled consistently for every relevant connection.

---

## 7. Foreign Key Syntax

A typical relational definition has the conceptual structure:

`FOREIGN KEY (customer_id) REFERENCES customers(customer_id)`

The child column is listed first.

The referenced parent table and column follow `REFERENCES`.

A complete relational design can also specify actions such as:

`ON DELETE CASCADE`

or:

`ON UPDATE CASCADE`

These actions define what happens when the referenced parent key is deleted or changed.

---

## 8. ON DELETE Actions

The major referential actions demonstrated by the implementations are:

- `RESTRICT`
- `NO ACTION`
- `CASCADE`
- `SET NULL`
- `SET DEFAULT`

The correct action depends on the meaning of the relationship.

---

## 9. ON DELETE RESTRICT

`RESTRICT` prevents deletion of a parent while dependent child rows exist.

Example:

`customers.customer_id = 1`

is referenced by:

`orders.customer_id = 1`

Deleting customer 1 is rejected.

This is useful when the parent must remain present while dependent records exist.

Typical examples include:

- A customer with legally required transaction records
- A product referenced by historical records
- A department that must remain available while employees reference it
- A category that cannot be removed while products still depend on it

The Python and C++ implementations demonstrate this behavior explicitly.

---

## 10. NO ACTION

`NO ACTION` also prevents the database from ending with an invalid foreign-key relationship.

The distinction between `RESTRICT` and `NO ACTION` can involve the timing of constraint checking, particularly in database systems that support deferred constraints.

For ordinary immediate constraints, both can appear to behave similarly because an invalid parent deletion is rejected.

The exact semantics should be verified for the database system being used.

---

## 11. ON DELETE CASCADE

`CASCADE` propagates a parent deletion to dependent child rows.

For example:

`customer → order → payment`

If the relationship is configured for cascading deletion:

`DELETE customer`

can cause:

`DELETE orders`

which can cause:

`DELETE payments`

This is useful when the child has no independent meaning without the parent.

Examples include:

- Shopping-cart items belonging to a deleted cart
- Temporary session records belonging to a deleted session
- Detail records owned exclusively by a master record
- Child configuration records that have no independent lifecycle

Cascade deletion must be used carefully.

A single parent deletion can affect many rows across several tables.

---

## 12. Cascading Through Multiple Levels

The Python example creates:

`cascade_customers`

then:

`cascade_orders`

then:

`payments`

The relationships are:

`cascade_customers → cascade_orders → payments`

Both child relationships use `ON DELETE CASCADE`.

Deleting a customer therefore removes its orders, and deleting those orders removes their payments.

This demonstrates that referential actions can form a dependency graph rather than a single parent-child pair.

---

## 13. ON DELETE SET NULL

`SET NULL` keeps the child row but removes its parent relationship.

Example:

Before:

`employee.department_id = 10`

After deleting department 10:

`employee.department_id = NULL`

This is appropriate when the child can still exist without its former parent.

The foreign-key column must allow `NULL`.

Therefore, a schema using `ON DELETE SET NULL` normally cannot declare that foreign-key column as `NOT NULL`.

Examples include:

- An employee whose department was removed
- A document whose optional owner account was deleted
- A support ticket whose assigned team was removed

The exact business meaning should determine whether `NULL` is appropriate.

---

## 14. ON DELETE SET DEFAULT

`SET DEFAULT` changes the child reference to a predefined default value.

For example:

`team_id = 10`

could become:

`team_id = 0`

after team 10 is deleted.

The default value must still satisfy the foreign-key relationship.

The Python example creates a special parent:

`team_id = 0`

with the name:

`Unassigned`

This makes `SET DEFAULT` meaningful because the fallback value points to an actual valid parent.

A default that does not reference a valid parent would still produce an integrity problem.

---

## 15. ON UPDATE CASCADE

`ON UPDATE CASCADE` propagates changes to the referenced parent key.

Suppose:

`customers.customer_id = 10`

and:

`orders.customer_id = 10`

If the customer key changes from 10 to 11, cascading update behavior changes the child references to 11.

The Python, JavaScript, and C++ implementations demonstrate this mechanism.

In practical database design, primary keys are often chosen to be stable and rarely changed. This reduces the need for primary-key updates.

---

## 16. NULL and Foreign Keys

A nullable foreign key can represent an optional relationship.

For example:

`employee.department_id = NULL`

can mean that the employee currently has no department.

This is different from:

`employee.department_id = 0`

unless 0 is a valid, deliberately defined parent.

`NULL` represents the absence of a value rather than a special numeric identifier.

If the relationship is mandatory, the foreign-key column can be declared `NOT NULL`.

For example:

`department_id INTEGER NOT NULL`

This creates two layers of validation:

1. `NOT NULL` prevents the relationship from being absent.
2. `FOREIGN KEY` prevents the relationship from pointing to a nonexistent parent.

---

## 17. Application Validation vs Database Constraints

Application code can check whether a parent exists before inserting a child.

For example:

`SELECT 1 FROM customers WHERE customer_id = ?`

can be used before an order is created.

This is useful for user-facing validation.

It is not a substitute for a database foreign key.

A database can be accessed by:

- Another application
- A background worker
- An administrative script
- An ETL process
- A migration
- A reporting process
- A separate service

The database constraint provides a centralized integrity boundary.

---

## 18. Multiple Child Tables

One parent can have several different child relationships.

For an account system:

`accounts`

may be referenced by:

`addresses`

and:

`reviews`

The JavaScript implementation models this pattern.

Deleting an account with `CASCADE` can therefore affect several child tables.

This illustrates why cascade actions must be analyzed across the entire dependency graph rather than one table at a time.

---

## 19. Self-Referencing Foreign Keys

A table can reference itself.

For example:

`employees(employee_id, manager_id)`

where:

`manager_id → employees.employee_id`

This models organizational hierarchies.

Example:

`CEO → Engineering Manager → Developer`

The same technique can model:

- Employee hierarchies
- Category trees
- Folder structures
- Comment replies
- Organizational reporting structures
- Parent-child geographic structures

The JavaScript and Python implementations demonstrate self-referencing relationships.

---

## 20. Composite Foreign Keys

A foreign key can contain multiple columns.

Suppose the parent key is:

`PRIMARY KEY (course_code, semester)`

A child can reference both:

`FOREIGN KEY (course_code, semester)`

This is useful when one column alone does not uniquely identify the parent relationship.

For example:

`CS101 + 2026-FALL`

can be a valid course offering while:

`CS101 + 2027-SPRING`

may not exist.

The Python, JavaScript, and C++ examples demonstrate the concept.

Composite foreign keys require careful consideration of:

- Column ordering
- Matching data types
- Parent uniqueness
- NULL semantics
- Index design
- Query patterns

---

## 21. Python Implementation

The Python implementation uses SQLite because SQLite is included in the Python standard library.

This provides real database-level constraint behavior without an external database server.

The main concepts demonstrated are:

- Creating parent tables
- Creating child tables
- Declaring foreign keys
- Enabling SQLite foreign-key enforcement
- Inserting valid relationships
- Rejecting invalid relationships
- `RESTRICT`
- `CASCADE`
- `SET NULL`
- `SET DEFAULT`
- `NO ACTION`
- `ON UPDATE CASCADE`
- Composite foreign keys
- Self-referencing foreign keys
- Multiple child tables
- Transactions
- Rollback
- Schema inspection
- Foreign-key indexing
- Automated assertions

The Python program is particularly useful for observing what an actual relational engine does when a constraint is violated.

---

## 22. Python Transaction Handling

The Python program defines a transaction context manager.

A transaction groups multiple operations into an atomic unit.

For example:

1. Insert a parent.
2. Insert a valid child.
3. Insert an invalid child.

If the third operation fails, the transaction is rolled back.

This prevents the first two operations from remaining as an unintended partial change.

Transactions are important whenever multiple related tables must be changed consistently.

---

## 23. Python Schema Inspection

SQLite provides:

`PRAGMA foreign_key_list(table_name)`

to inspect foreign-key definitions.

The Python implementation uses this capability to make the relationship definition visible at runtime.

Schema inspection is useful during:

- Debugging
- Migration verification
- Database administration
- Automated tests
- Development of database tooling

---

## 24. Python Indexing Demonstration

A foreign key does not automatically mean that the child column has the appropriate index for every workload.

For example:

`orders.customer_id`

may frequently be used to:

- Join orders to customers
- Find all orders for a customer
- Check dependent rows during parent deletion
- Process customer-level reporting

An index such as:

`CREATE INDEX idx_orders_customer_id ON orders(customer_id)`

can improve these operations.

The correct indexing strategy depends on workload and query plans.

---

## 25. JavaScript Implementation

The JavaScript implementation takes a different approach.

Instead of relying on an external database, it creates a small relational integrity engine.

The main components are:

- `Table`
- `ForeignKeyConstraint`
- `RelationalDatabaseDemo`
- `ForeignKeyError`

`Table` stores rows using a JavaScript `Map`.

`ForeignKeyConstraint` validates references and implements referential actions.

`RelationalDatabaseDemo` coordinates parent and child operations.

This design makes the mechanics visible without hiding them behind SQL syntax.

---

## 26. JavaScript Foreign-Key Validation

When a child row is inserted, the constraint checks whether the referenced parent exists.

For example:

`customerId = 999`

is rejected when no customer with ID 999 exists.

This models the essential rule of a foreign key:

**A non-null child reference must resolve to an appropriate parent key.**

The implementation also recognizes `null` as a possible optional relationship.

---

## 27. JavaScript Cascade Behavior

The JavaScript implementation demonstrates:

`RESTRICT`

`CASCADE`

`SET NULL`

and:

`ON UPDATE CASCADE`

The cascade implementation searches for dependent children and updates or removes them according to the configured action.

The code also demonstrates cascading through multiple levels:

`customer → order → payment`

This makes dependency propagation explicit.

---

## 28. JavaScript Transactions

The JavaScript program includes a conceptual transaction demonstration.

A real database transaction provides atomicity using database-level mechanisms.

The JavaScript example illustrates the same logical principle:

- Save the original state.
- Perform multiple operations.
- Detect an error.
- Restore the original state.

The implementation uses this as an educational model rather than claiming that an in-memory snapshot is equivalent to a production database transaction system.

Real databases must address concurrency, durability, crash recovery, locking, isolation, logging, and other concerns.

---

## 29. C++ Industry Case Study

The C++ program models a simplified commerce system.

The main entities are:

`Customer`

`Order`

`Payment`

The relationships are:

`Customer 1 → many Orders`

and:

`Order 1 → many Payments`

This resembles a real transactional system.

The design also introduces secondary lookup structures:

`ordersByCustomer`

and:

`paymentsByOrder`

These behave conceptually like application-side indexes.

---

## 30. C++ Customer-to-Order Relationship

An order contains:

`customerId`

The insertion method checks whether the customer exists before creating the order.

If the customer does not exist, an `IntegrityError` is thrown.

This represents the same logical constraint that a database foreign key enforces.

The C++ implementation also validates:

- Duplicate primary keys
- Empty required names
- Negative monetary values
- Missing parent records

---

## 31. C++ Cascade Case Study

The commerce system implements:

`customer → order → payment`

When a customer is deleted with cascading behavior:

1. The customer's orders are found.
2. Each order is deleted.
3. Payments belonging to those orders are deleted.
4. The order indexes are updated.
5. The customer is deleted.

This demonstrates a multi-level dependency graph.

The operation is more than a simple `erase` from one container. Referential integrity requires coordinated changes across dependent entities.

---

## 32. C++ RESTRICT Case Study

The C++ `deleteCustomerRestrict` method first checks the child index.

If orders exist for the customer, deletion fails.

This corresponds to the conceptual database operation:

`ON DELETE RESTRICT`

The parent remains intact.

This is appropriate when the application considers the parent record necessary while dependent records exist.

---

## 33. C++ SET NULL Case Study

The employee hierarchy demonstrates:

`employee.manager_id → employee.employee_id`

When a manager is deleted, subordinate employees remain.

Their `managerId` values become empty.

This represents:

`ON DELETE SET NULL`

The child records survive because their existence is not completely owned by the deleted manager.

---

## 34. C++ ON UPDATE CASCADE

The C++ commerce system includes a method that changes a customer ID.

The method:

1. Checks that the old parent exists.
2. Checks that the new key is not already used.
3. Locates dependent orders.
4. Changes their foreign-key values.
5. Rebuilds the corresponding lookup index.
6. Changes the parent key.

This demonstrates the implementation work required to preserve referential integrity during a parent-key update.

---

## 35. C++ Transaction and Rollback

The C++ case study uses a snapshot to demonstrate atomicity.

Before a transaction:

`customers`, `orders`, `payments`, and indexes are copied.

If an operation fails, the snapshot is restored.

This illustrates the desired transaction property:

**Either all related changes succeed, or none of them become part of the final state.**

A production database implements this through database transaction machinery rather than application-level object snapshots.

---

## 36. C++ Data Structures

The case study uses:

`unordered_map`

for primary-key lookup.

It uses:

`unordered_set`

for child-ID indexes.

The resulting structure allows direct lookup of a parent by ID and efficient retrieval of dependent child identifiers.

The conceptual complexity of average hash-table lookup is approximately O(1), although actual performance depends on hashing, load factor, collisions, memory locality, and implementation details.

---

## 37. Performance Considerations

Foreign keys have integrity benefits but can introduce work during writes.

When a parent is deleted, the database may need to determine whether child rows exist.

When a parent key is updated, dependent rows may need to be found and modified.

Indexes on child foreign-key columns can significantly reduce the cost of finding dependent rows.

For example:

`orders(customer_id)`

is often a useful index.

But indexes have costs:

- Additional storage
- Additional memory
- More expensive inserts
- More expensive updates
- More expensive deletes
- Index maintenance
- Potentially slower bulk-loading operations

Index decisions should be based on actual access patterns.

---

## 38. Referential Actions and Business Semantics

The choice of referential action should represent the business meaning of the relationship.

### RESTRICT

Use when the parent should not disappear while dependent data exists.

### NO ACTION

Use when the relationship must remain valid and the database's constraint-checking semantics make it appropriate.

### CASCADE

Use when the child is truly dependent on the parent's lifecycle.

### SET NULL

Use when the child can continue to exist without the parent.

### SET DEFAULT

Use when a valid fallback parent has a meaningful business interpretation.

There is no universal cascade action that is correct for every relationship.

---

## 39. Foreign Key vs Primary Key

A primary key answers:

**Which row is this?**

A foreign key answers:

**Which parent row does this child belong to or reference?**

Example:

`customers.customer_id`

is the primary key.

`orders.order_id`

is the primary key of orders.

`orders.customer_id`

is a foreign key referencing the customer.

A column can participate in multiple constraints, but primary-key and foreign-key roles are conceptually different.

---

## 40. Foreign Key vs Unique Constraint

A `UNIQUE` constraint prevents duplicate values.

A foreign key validates a relationship.

For example:

`customers.email UNIQUE`

means two customers cannot use the same email value.

By contrast:

`orders.customer_id REFERENCES customers(customer_id)`

means an order must reference a valid customer.

These constraints solve different problems and are often used together.

---

## 41. Natural Keys and Surrogate Keys

A **natural key** is based on meaningful business data.

Examples include:

- Government-issued identifiers
- Product codes
- Email addresses
- International codes

A **surrogate key** is an identifier created primarily for database identification.

Examples include:

`customer_id = 1001`

A stable surrogate key can reduce the need for cascading primary-key updates.

Natural keys can still be useful, particularly when the business identifier is stable, unique, and already meaningful.

The choice depends on the domain.

---

## 42. Common Mistakes

### Mistake 1: No Foreign Key

Storing parent identifiers without declaring the relationship allows invalid references.

### Mistake 2: Disabling Enforcement

A foreign-key declaration has little practical value if enforcement is disabled.

### Mistake 3: Incorrect NULL Handling

Using a nullable foreign key for a mandatory relationship permits missing relationships.

### Mistake 4: Blind CASCADE

A parent deletion can remove a large number of dependent rows.

### Mistake 5: Missing Indexes

Large child tables can become expensive to search when dependent rows must be located repeatedly.

### Mistake 6: Application-Only Validation

Application checks do not protect against every database client.

### Mistake 7: Unstable Referenced Keys

Frequently changing referenced keys can create unnecessary update propagation.

### Mistake 8: Ignoring Transactions

Multi-table operations can leave inconsistent application state if only part of the operation succeeds.

---

## 43. Edge Cases

Important edge cases include:

- Inserting a child before its parent
- Deleting a parent with many children
- Updating a referenced key
- Updating a parent key to an already-existing value
- Nullable foreign keys
- Composite foreign keys
- Self-referencing foreign keys
- Multiple children referencing one parent
- Multiple levels of cascading
- Circular dependencies
- Bulk deletes
- Bulk updates
- Concurrent modifications
- Failed transactions
- Missing indexes
- Invalid default values

These cases should be included in database tests.

---

## 44. Security Considerations

Foreign keys are primarily an integrity mechanism, but they contribute to application security by reducing inconsistent database states.

They do not replace:

- Authentication
- Authorization
- Encryption
- Input validation
- Parameterized queries
- Access control
- Audit logging

A foreign key does not determine whether a user is authorized to modify a parent or child row.

It determines whether the referenced relationship is valid.

Applications should still use parameterized SQL rather than constructing SQL statements through unsafe string concatenation.

---

## 45. Production Considerations

A production relational design should consider:

- Stable primary keys
- Correct foreign-key constraints
- Appropriate nullability
- Appropriate cascading actions
- Child-column indexes
- Transaction boundaries
- Concurrent access
- Migration strategy
- Backup and recovery
- Monitoring
- Query performance
- Data retention requirements
- Audit requirements
- Referential-action impact during bulk operations

The database schema should reflect actual business ownership and lifecycle rules.

---

## 46. Testing Strategy

Foreign-key tests should cover both successful and failed operations.

Important tests include:

1. Insert a valid parent.
2. Insert a valid child.
3. Reject a child referencing a nonexistent parent.
4. Reject a duplicate primary key.
5. Reject a mandatory NULL relationship.
6. Verify `RESTRICT`.
7. Verify `CASCADE`.
8. Verify `SET NULL`.
9. Verify `SET DEFAULT`.
10. Verify `ON UPDATE CASCADE`.
11. Verify composite references.
12. Verify self-referencing relationships.
13. Verify transaction rollback.
14. Verify indexes and query behavior for realistic workloads.

The Python and C++ implementations include executable assertions for several of these cases.

---

## 47. Implementation Comparison

| Aspect | Python | JavaScript | C++ |
| --- | --- | --- | --- |
| Primary purpose | Actual relational behavior | Mechanism simulation | Industry-style system case study |
| Storage model | SQLite | In-memory Maps | `unordered_map` and indexes |
| Foreign-key enforcement | Database engine | Custom implementation | Application-level implementation |
| Cascading | SQLite | Explicit constraint engine | Explicit system logic |
| Transactions | SQLite transaction | Conceptual rollback | Snapshot rollback |
| Schema inspection | SQLite PRAGMA | Custom objects | C++ structures |
| Performance demonstration | Database index concept | Linear lookup example | Hash lookup and linear-scan comparison |
| Best educational perspective | SQL/database behavior | Relationship mechanics | System architecture and implementation |

---

## 48. Why the Three Languages Are Different

Python is particularly useful here because SQLite provides a real relational database engine through the standard library. This allows foreign-key constraints and referential actions to be executed rather than merely simulated.

JavaScript makes the mechanisms explicit. The `ForeignKeyConstraint` class shows how a simplified relational system could check parent existence and apply referential actions.

C++ emphasizes system design. The commerce case study uses explicit data structures, indexes, exception-based error handling, transactions, and dependency propagation.

The implementations therefore complement one another rather than being identical translations.

---

## 49. Core Rules to Remember

A foreign key creates a relationship between child data and parent data.

A child reference should resolve to an appropriate parent key unless the relationship is legitimately `NULL`.

`NOT NULL` controls whether the relationship may be absent.

`RESTRICT` protects the parent from deletion while dependent rows exist.

`CASCADE` propagates parent deletion to dependent rows.

`SET NULL` preserves the child while removing its parent relationship.

`SET DEFAULT` moves the child to a valid predefined parent.

`ON UPDATE CASCADE` propagates parent-key changes.

Indexes on child foreign-key columns can improve relationship lookups.

Transactions protect multi-step changes from partial failure.

The correct foreign-key action is determined by the business lifecycle of the data.

---

## 50. Practical Relationship Model

The central commerce example can be represented conceptually as:

`Customer`

→ `Order`

→ `Payment`

The foreign keys establish:

`Order.customer_id → Customer.customer_id`

and:

`Payment.order_id → Order.order_id`

If orders are considered owned by customers, cascading deletion may be appropriate.

If historical orders must remain even after a customer account is removed, `RESTRICT`, anonymization, soft deletion, or a different lifecycle design may be more appropriate.

This distinction demonstrates an important database-design principle:

**A foreign-key action should represent a real business rule, not merely provide convenient cleanup.**

---

## 51. Final Technical Perspective

Foreign keys are one of the mechanisms that allow relational databases to enforce consistency at the data layer.

The fundamental relationship is simple:

`child foreign key → parent key`

The practical design is more complex because parent changes can affect entire dependency graphs.

Understanding foreign keys therefore requires understanding:

- Keys
- Relationships
- Nullability
- Constraints
- Referential integrity
- Cascading behavior
- Transactions
- Indexes
- Dependency graphs
- Business lifecycle rules
- Performance
- Failure handling
- Testing

The Python implementation demonstrates actual SQLite behavior, the JavaScript implementation exposes the mechanics of relationship enforcement, and the C++ implementation applies those ideas to a realistic commerce data model.
