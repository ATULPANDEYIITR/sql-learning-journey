# Primary Keys: Uniqueness, Entity Identification, and Composite Primary Keys

## 1. Topic Introduction

A **primary key** is a relational database constraint that identifies each row in a table uniquely.

A primary key establishes the identity of a row. It prevents two rows from sharing the same primary-key value and does not permit an absent identity.

For example, a student table may contain:

`student(student_id, name, email)`

If `student_id` is the primary key, values such as `101`, `102`, and `103` identify different student rows.

The important distinction is that a primary key identifies an entity, while other columns describe attributes of that entity.

For example:

- `student_id` identifies the student.
- `name` describes the student.
- `email` describes a contact attribute.
- `date_of_birth` describes another attribute.

A well-designed database treats identity and descriptive information as separate concepts.

---

## 2. Fundamental Properties of a Primary Key

A primary key has two central relational properties:

1. **Uniqueness**
2. **Non-null identity**

If a table contains:

| student_id | name |
|---:|---|
| 101 | Asha |
| 102 | Ravi |
| 103 | Anita |

then `student_id` uniquely identifies every row.

The following would violate the primary-key constraint:

| student_id | name |
|---:|---|
| 101 | Asha |
| 101 | Ravi |

Both rows claim the same identity.

Likewise, a missing identifier cannot serve as a valid primary-key identity.

The Python implementation demonstrates this behavior through the `Table` class. Its internal dictionary models the conceptual relationship:

`primary_key -> row`

The JavaScript implementation uses `Map` for a similar educational demonstration.

The C++ implementation uses `std::unordered_map` to represent a key-indexed collection.

These language-level structures are not database engines, but they make the identity concept visible.

---

## 3. Entity Identification

Entity identification is the fundamental purpose of a primary key.

Consider a customer table:

`customer(customer_id, name, email)`

A customer might change:

- name
- email
- phone number
- address

Those changes should normally not create a new customer identity.

For example:

`customer_id = 501`

can remain the identity of the same customer even when:

`old@example.com`

changes to:

`new@example.com`

This is one reason a stable identifier is valuable.

The Python and JavaScript examples explicitly demonstrate retrieving an entity through its identifier.

The C++ case study uses:

`customerId`

as the identity of the `Customer` structure.

---

## 4. Candidate Keys

A **candidate key** is a minimal set of attributes that can uniquely identify a row.

Suppose a university has:

`student(student_id, registration_number, email, name)`

Potential candidate keys might be:

- `student_id`
- `registration_number`
- `email`

provided the institution guarantees that each is unique and non-null for every student.

One candidate key is selected as the primary key.

The remaining candidate keys are often called **alternate keys**.

For example:

- `student_id` → primary key
- `registration_number` → alternate unique key
- `email` → alternate unique key

The fact that an attribute is unique does not automatically make it the primary key.

A database can have multiple unique constraints but normally has one declared primary-key constraint for a table.

---

## 5. Primary Key vs UNIQUE Constraint

A primary key and a unique constraint both enforce uniqueness, but they have different logical roles.

A primary key answers:

> Which attribute or attributes represent the official identity of this row?

A `UNIQUE` constraint answers:

> Which values must not be duplicated?

For example:

`customer(customer_id PRIMARY KEY, email UNIQUE, name)`

means:

- `customer_id` identifies the customer.
- `email` must not be duplicated.
- Email is not necessarily the identity chosen for the table.

This distinction is important when business attributes can change.

---

## 6. Natural Keys

A **natural key** is an identifier that already exists in the business or application domain.

Examples can include:

- country code
- ISBN
- employee number
- externally assigned registration number

Natural keys can be attractive because they have meaning outside the database.

For example:

`country_code = "IN"`

has an obvious business interpretation.

A natural key can be appropriate when the identifier is:

- genuinely unique
- stable
- sufficiently small
- available consistently
- not sensitive
- unlikely to be redefined by changing business rules

The main concern is that business data can change.

If a value that looked permanent later changes, using it as the primary identity can create significant dependency-management problems.

---

## 7. Surrogate Keys

A **surrogate key** is an identifier created specifically for database identity.

Common examples include:

- integer identity values
- sequences
- UUIDs
- other generated identifiers

For example:

`customer_id = 5001`

may have no business meaning at all. Its purpose is simply to identify one customer.

A common design is:

`customer_id PRIMARY KEY`

and:

`email UNIQUE`

This separates stable database identity from business-level uniqueness.

The Python, JavaScript, and C++ implementations demonstrate this model extensively.

---

## 8. Natural Key vs Surrogate Key

| Characteristic | Natural Key | Surrogate Key |
|---|---|---|
| Business meaning | Usually has meaning | Usually none |
| Stability | Depends on business rules | Usually easier to keep stable |
| Size | Can be large | Often compact |
| Generation | Comes from business data | Generated by system |
| Human readability | Often better | Often worse |
| Business-rule changes | Can be disruptive | Usually less disruptive |
| Distributed generation | Depends on source | UUIDs work well |
| Need for business uniqueness | Built into key | Often requires separate UNIQUE constraint |

Neither strategy is universally correct.

The appropriate choice depends on the domain, lifecycle of the data, integration requirements, indexing characteristics, and relationship structure.

---

## 9. Composite Primary Keys

A **composite primary key** contains multiple columns.

Consider an enrollment relationship:

`enrollment(student_id, course_id, enrolled_on)`

Suppose:

- one student can enroll in many courses
- one course can contain many students

Then neither column is individually unique.

For example:

`student_id = 101`

can occur many times.

Likewise:

`course_id = 501`

can occur many times.

But the combination:

`(student_id, course_id)`

can uniquely identify one enrollment.

The primary key can therefore be:

`PRIMARY KEY (student_id, course_id)`

The Python implementation models this using tuples.

The JavaScript implementation creates a serialized composite-key representation.

The C++ implementation creates a dedicated `OrderLineKey` structure with:

- `orderId`
- `productId`

and supplies a custom hash function so it can be used in `std::unordered_map`.

---

## 10. Why Composite Keys Matter

Composite keys are particularly common in relationship tables.

Examples include:

### Student and course

`enrollment(student_id, course_id)`

Primary key:

`(student_id, course_id)`

### Order and product

`order_line(order_id, product_id)`

Primary key:

`(order_id, product_id)`

### User and role

`user_role(user_id, role_id)`

Primary key:

`(user_id, role_id)`

### Product and warehouse

`warehouse_product(warehouse_id, product_id)`

Primary key:

`(warehouse_id, product_id)`

The combination represents the identity of the relationship.

---

## 11. Composite Key Column Order

The logical uniqueness of:

`PRIMARY KEY (customer_id, order_id)`

does not mean that index behavior is identical to:

`PRIMARY KEY (order_id, customer_id)`

Index column order matters.

A composite index beginning with:

`customer_id`

can often efficiently support access patterns that constrain `customer_id`.

A query filtering only on:

`order_id`

may not receive the same benefit from that index.

This distinction is important:

- **Logical key definition** determines uniqueness.
- **Physical index organization** influences query performance.

The database engine determines the exact implementation.

---

## 12. Foreign Keys and Primary Keys

Primary keys commonly participate in relationships with foreign keys.

Consider:

`customer(customer_id PRIMARY KEY)`

and:

`orders(order_id PRIMARY KEY, customer_id FOREIGN KEY)`

The child table's `customer_id` refers to the parent's primary-key value.

The relationship can be represented conceptually as:

`orders.customer_id -> customer.customer_id`

The Python implementation explicitly validates that a referenced student exists before inserting an enrollment.

The JavaScript implementation performs the same validation using `Map`.

The C++ order-management system verifies that an order line's `productId` exists before accepting the line.

This is **referential integrity**.

---

## 13. Referential Integrity

Referential integrity prevents a child record from referencing an entity that does not exist.

For example, if:

`product_id = 101`

does not exist in `product`, then this order line should not normally be accepted:

`order_line(order_id = 9001, product_id = 101)`

if `101` is not present in the product table.

Without referential integrity, the database could contain relationships pointing to nonexistent entities.

That produces orphaned references and inconsistent data.

---

## 14. Primary Keys and NULL

A primary key represents identity.

An absent value cannot provide identity.

Therefore, primary-key columns have non-null semantics.

This is especially important because SQL's treatment of `NULL` differs from ordinary values.

`NULL` does not mean:

`0`

and it does not mean:

`""`

It represents an unknown or absent value.

SQL also uses three-valued logic involving:

- `TRUE`
- `FALSE`
- `UNKNOWN`

A primary key avoids identity ambiguity by requiring an actual value.

---

## 15. JavaScript Missing Values

JavaScript has several values that can be confused during careless validation:

- `null`
- `undefined`
- `""`
- `0`
- `false`
- `NaN`

A check such as:

`if (!id)`

may be too broad for a database-style identifier.

Explicit validation is preferable.

For example, if an application requires a positive integer:

`Number.isInteger(id)`

and:

`id > 0`

express the rule more precisely.

The JavaScript implementation demonstrates explicit validation.

---

## 16. Immutable Keys

A primary key should normally remain stable.

The Python implementation demonstrates this with:

`@dataclass(frozen=True)`

for `OrderLineKey`.

The JavaScript implementation uses:

`Object.freeze()`

for its composite key object.

The C++ implementation demonstrates an immutable-style identifier using a private `const` data member.

The underlying principle is more important than the language feature:

> Do not allow identity values to change accidentally while dependent records still refer to them.

Changing a primary key can affect:

- foreign keys
- indexes
- cached references
- audit records
- external integrations
- URLs
- application logic
- synchronization processes

---

## 17. Mutable Natural Identifiers

Suppose a system uses email as the primary key:

`customer(email PRIMARY KEY, name)`

A customer changes:

`old@example.com`

to:

`new@example.com`

Any dependent table that references the email must deal with that change.

With:

`customer(customer_id PRIMARY KEY, email UNIQUE, name)`

the customer identity remains stable.

The email can change while the primary key remains unchanged.

This is one of the main practical reasons for separating database identity from mutable business attributes.

---

## 18. UUID Primary Keys

A **UUID**, or Universally Unique Identifier, can be used as a surrogate key.

A UUID is much larger than a small integer.

Example:

`550e8400-e29b-41d4-a716-446655440000`

Advantages include:

- independent generation
- suitability for distributed systems
- extremely low collision probability when generated correctly
- reduced dependence on a central sequence

Trade-offs include:

- greater storage requirements
- larger indexes
- poorer human readability
- potentially different index locality characteristics
- more expensive display and transmission than small integers

The Python implementation uses `uuid4()`.

The JavaScript implementation generates UUID-style identifiers and uses the Web Crypto API when available.

---

## 19. Hashes Are Not Automatically Primary Keys

A hash produces a digest from input data.

For example, SHA-256 can produce a fixed-size digest.

A hash can be useful for:

- content addressing
- integrity verification
- deduplication strategies
- deterministic identifiers in controlled systems

But a hash is not automatically a primary key.

The database still needs an explicit uniqueness rule.

Cryptographic hash collisions are theoretically possible.

The choice between a hash and a conventional identifier should be based on the actual domain requirement.

The Python implementation demonstrates SHA-256 using the standard library.

The JavaScript implementation demonstrates SHA-256 through the Web Crypto API when supported by the runtime.

---

## 20. SQL Primary-Key Syntax

A simple primary key can be declared as:

`CREATE TABLE students ( student_id INTEGER PRIMARY KEY, name TEXT NOT NULL );`

A composite primary key can be declared as:

`PRIMARY KEY (student_id, course_id)`

For example:

`CREATE TABLE enrollments ( student_id INTEGER NOT NULL, course_id INTEGER NOT NULL, PRIMARY KEY (student_id, course_id) );`

A business attribute can be independently protected with:

`email TEXT NOT NULL UNIQUE`

The Python implementation also contains executable SQLite examples using the standard-library `sqlite3` module.

---

## 21. SQLite Demonstration

The Python script creates an in-memory SQLite database with:

- `customer`
- `product`
- `order_item`

The `order_item` table uses:

`PRIMARY KEY (order_id, product_id)`

and:

`FOREIGN KEY (product_id) REFERENCES product(product_id)`

It also demonstrates a check constraint:

`CHECK (quantity > 0)`

The program then intentionally attempts:

1. A duplicate composite key.
2. A nonexistent foreign-key reference.

SQLite rejects the invalid operations.

This demonstrates an important production principle:

> Critical data-integrity rules should be enforced by the database, not only by application code.

---

## 22. Python Implementation

The Python implementation progresses from simple identity concepts to an executable order-management model.

### `Table`

The generic `Table` class uses a dictionary keyed by the primary key.

It demonstrates:

- insertion
- lookup
- existence checking
- deletion
- duplicate-key detection
- missing-key detection

The dictionary is an educational abstraction for indexed access.

### `CandidateKey`

The `CandidateKey` dataclass models the concept of candidate and alternate keys.

### `OrderLineKey`

The immutable `OrderLineKey` dataclass models:

`(order_id, product_id)`

as a composite identity.

### `OrderManagementSystem`

The case study contains:

- customers
- products
- order lines
- validation
- foreign-key checks
- unique email enforcement
- duplicate composite-key detection
- order-total calculation

### SQLite

The SQLite section moves from conceptual modeling to an actual relational database engine.

This is important because an in-memory Python dictionary does not reproduce the full behavior of a database.

---

## 23. JavaScript Implementation

The JavaScript implementation complements the Python implementation.

It demonstrates primary-key concepts using JavaScript-specific mechanisms.

### `Map`

JavaScript's `Map` provides key-based storage and makes the relationship between:

`key -> entity`

easy to observe.

### Custom Errors

The implementation defines:

- `DuplicateKeyError`
- `MissingKeyError`
- `ForeignKeyError`
- `ValidationError`

This makes failures explicit.

### UUID Handling

The JavaScript implementation demonstrates UUID generation and validation.

### `Object.freeze`

`OrderLineKey` uses `Object.freeze()` to demonstrate immutable-style identity objects.

### Order Management

The order-management model contains:

- `Customer`
- `Product`
- `OrderLine`
- `OrderManagementSystem`

The system enforces primary-key uniqueness, business-key uniqueness, foreign-key existence, and composite order-line identity.

### Asynchronous Hashing

The hash demonstration uses the Web Crypto API where supported.

This also illustrates a JavaScript-specific difference: some cryptographic APIs are asynchronous.

---

## 24. C++ Case Study

The C++ program models a more strongly typed order-management system.

The scenario contains three major entities:

### Customer

Primary key:

`customerId`

Alternate unique attribute:

`email`

### Product

Primary key:

`productId`

### OrderLine

Composite primary key:

`(orderId, productId)`

Foreign key:

`productId -> Product.productId`

---

## 25. C++ Data Structures

The C++ case study uses:

`std::unordered_map`

for key-based lookup.

This illustrates the concept of an index-like structure.

For the composite key, the program defines:

`OrderLineKey`

with:

- `orderId`
- `productId`

A custom:

`OrderLineKeyHash`

allows the composite key to be used with:

`std::unordered_map<OrderLineKey, ...>`

This demonstrates an important systems-level concept:

> Composite identity must have a representation suitable for the data structure used by the implementation.

---

## 26. C++ Validation

The program validates:

- positive identifiers
- nonempty names
- valid email structure
- nonnegative prices
- positive quantities
- existing foreign-key targets
- duplicate primary keys
- duplicate composite keys
- duplicate business emails

The validation functions are separated from the main entity structures to make the design easier to maintain.

---

## 27. C++ Order-Management Architecture

The main system is:

`OrderManagementSystem`

It contains three logical tables:

`customers_`

`products_`

`orderLines_`

Each table has a distinct identity strategy.

### Customers

`customerId`

is the primary key.

### Products

`productId`

is the primary key.

### Order lines

`OrderLineKey{orderId, productId}`

is the composite primary key.

This reflects a common relational pattern:

- entities have their own identity
- relationship records can use composite identity
- foreign keys connect those entities

---

## 28. Order-Line Uniqueness

Suppose order `9001` contains product `101`.

The following key identifies the line:

`(9001, 101)`

Trying to add another row with:

`(9001, 101)`

violates the composite primary key.

The same product can appear in another order:

`(9002, 101)`

because the complete composite key is different.

Likewise, order `9001` can contain another product:

`(9001, 102)`

because that composite key is also different.

This is exactly why composite keys are useful for relationship tables.

---

## 29. Primary Keys and Performance

A primary key is a logical constraint, but databases normally need an efficient physical mechanism to enforce it.

Common index structures include:

- B-trees
- hash indexes in systems that support them
- clustered storage structures in some database engines

Conceptually:

| Access approach | Typical conceptual complexity |
|---|---:|
| Full table scan | O(n) |
| Balanced tree lookup | O(log n) |
| Hash lookup | O(1) average |

These are conceptual complexity models, not guarantees for every database query.

Real performance depends on:

- database engine
- index type
- cache state
- disk or storage system
- query planner
- table size
- data distribution
- concurrency
- memory
- query selectivity

The Python, JavaScript, and C++ performance demonstrations use in-memory structures to illustrate the key lookup concept.

---

## 30. Primary-Key Width

Key size matters.

An integer key might require only a small number of bytes.

A UUID is considerably larger.

A composite key containing several large columns can be larger still.

Large keys can increase:

- table storage
- index storage
- foreign-key storage
- memory consumption
- network payload size
- cache pressure

This does not mean that small integers are always the correct choice.

The identifier strategy must satisfy the system's identity and distribution requirements.

---

## 31. Composite Keys and Foreign Keys

A composite primary key affects referencing tables.

If a parent table has:

`PRIMARY KEY (student_id, course_id)`

then a child table referencing that identity generally needs the corresponding components:

`student_id`

and:

`course_id`

The relationship therefore has multiple columns.

Composite keys can be very natural for associative entities, but they can also make downstream schemas more verbose.

A surrogate key can simplify references:

`enrollment_id PRIMARY KEY`

while preserving a separate uniqueness rule:

`UNIQUE(student_id, course_id)`

This is a design choice rather than a universal rule.

---

## 32. Composite Primary Key vs Surrogate Key Plus UNIQUE

Consider two possible designs.

### Design A

`enrollment(student_id, course_id, grade)`

Primary key:

`(student_id, course_id)`

### Design B

`enrollment(enrollment_id, student_id, course_id, grade)`

Primary key:

`enrollment_id`

Unique constraint:

`UNIQUE(student_id, course_id)`

Design A makes the relationship identity explicit.

Design B provides a single-column identifier while separately enforcing the business rule that a student cannot have duplicate enrollment in the same course.

The appropriate choice depends on how the entity is referenced and used.

---

## 33. Deletion and Referential Actions

Suppose:

`customer(customer_id PRIMARY KEY)`

is referenced by:

`order(customer_id FOREIGN KEY)`

Deleting a customer requires a policy for dependent orders.

Common relational actions include:

### RESTRICT / NO ACTION

Prevent deletion while dependent records exist.

### CASCADE

Delete dependent rows automatically.

### SET NULL

Remove the reference by setting the foreign key to `NULL`, if the schema permits it.

The choice must reflect the meaning of the data.

For financial, audit, historical, or legally relevant records, automatic cascading deletion can have significant consequences.

---

## 34. Transactions and Primary-Key Integrity

A transaction groups database operations into an atomic unit.

Suppose a transaction performs:

1. Insert account 2.
2. Insert account 1.
3. Account 1 already exists.

If the second operation violates the primary-key constraint, the transaction can be rolled back.

The Python implementation demonstrates this behavior directly with SQLite.

The C++ implementation provides a simplified in-memory rollback example by restoring the previous state.

A production database provides much more sophisticated transaction management, concurrency control, logging, recovery, and isolation.

---

## 35. Security Considerations

A primary key is not an authentication mechanism.

It is also not an authorization mechanism.

Suppose an API provides:

`GET /customers/1001`

Knowing `1001` must not be sufficient to retrieve the customer.

Authorization must determine whether the caller is permitted to access that record.

Sequential identifiers can also make enumeration easier.

For example:

`1001`

`1002`

`1003`

can reveal that identifiers are sequential.

Security controls can include:

- authorization checks
- rate limiting
- audit logging
- access controls
- careful exposure of internal identifiers
- separate public identifiers where appropriate

A UUID can make casual guessing harder, but a UUID does not provide authorization.

---

## 36. Privacy and Sensitive Identifiers

A primary key should not unnecessarily contain sensitive information.

Using a person's:

- national identification number
- phone number
- email address
- financial account number

as a public identifier can expose sensitive information.

Even if such an attribute is unique, that does not automatically make it a good primary key.

Identity design should consider:

- privacy
- security
- external exposure
- regulatory requirements
- data lifecycle
- integration requirements

---

## 37. Common Primary-Key Mistakes

### Mistake 1: Allowing duplicate identifiers

Two rows cannot share the same primary-key value.

### Mistake 2: Treating NULL as an identity

An absent value cannot uniquely identify an entity.

### Mistake 3: Assuming UNIQUE means PRIMARY KEY

A unique attribute and the table's selected primary identity have different roles.

### Mistake 4: Using mutable business data without considering changes

An email address or business code may change.

### Mistake 5: Ignoring composite identity

If uniqueness depends on multiple attributes, using only one attribute can produce incorrect duplicates.

### Mistake 6: Treating a surrogate key as sufficient business validation

A surrogate key identifies the row but does not replace business-level unique constraints.

### Mistake 7: Performing uniqueness checks only in application code

Concurrent application processes can still create duplicates unless the database constraint enforces the invariant.

### Mistake 8: Exposing sequential identifiers without authorization

Predictable identifiers can make resource enumeration easier.

### Mistake 9: Ignoring foreign-key relationships

Deleting or changing primary-key values can affect dependent records.

### Mistake 10: Selecting a key without considering its physical cost

Very large or wide keys can increase index and storage overhead.

---

## 38. Application Validation vs Database Constraints

Application validation is useful because it can provide clear error messages before a database operation is attempted.

For example:

`if customer_id <= 0`

can reject obviously invalid input.

But application validation alone is not enough for important uniqueness rules.

Two processes could execute simultaneously:

Process A checks whether ID 100 exists.

Process B checks whether ID 100 exists.

Both see that it does not exist.

Both attempt insertion.

Only a database-level uniqueness constraint can reliably arbitrate the concurrent write.

Therefore:

- application validation improves usability
- database constraints protect integrity

Both have useful roles.

---

## 39. Production Considerations

Primary-key design should be considered across the entire data lifecycle.

Important questions include:

### Creation

How is the identifier generated?

### Uniqueness

Where is uniqueness enforced?

### Updates

Can the identifier ever change?

### Relationships

Which foreign keys reference it?

### Integration

Will external systems need to store it?

### Replication

Can multiple systems generate identifiers independently?

### Migration

Will existing data need to be imported?

### Deletion

What happens to dependent records?

### Exposure

Will the identifier appear in URLs, logs, APIs, or user interfaces?

### Performance

How large is the identifier and how frequently is it indexed?

### Privacy

Does the identifier expose sensitive information?

These questions often matter more than simply choosing between an integer and a UUID.

---

## 40. Edge Cases

Important primary-key edge cases include:

- duplicate values
- missing values
- negative identifiers
- zero identifiers
- malformed UUIDs
- duplicate composite keys
- foreign keys pointing to missing rows
- changing natural identifiers
- deleting referenced parent rows
- importing duplicate records
- concurrent inserts
- distributed identifier generation
- very large tables
- index growth
- composite-key ordering
- migration from one identifier strategy to another

The three implementations intentionally exercise several of these conditions.

---

## 41. Testing Strategy

A primary-key implementation should test both valid and invalid cases.

Important tests include:

1. Insert a valid row.
2. Retrieve it by primary key.
3. Insert another distinct key.
4. Reject a duplicate key.
5. Reject a missing key.
6. Reject an invalid key format.
7. Reject an invalid foreign-key reference.
8. Reject a duplicate composite key.
9. Accept distinct composite-key combinations.
10. Verify business-level uniqueness.
11. Verify deletion behavior.
12. Verify transaction rollback where applicable.

The Python, JavaScript, and C++ files contain executable tests or assertions for these principles.

---

## 42. Real-World Applications

Primary keys appear throughout relational systems.

### Banking

`account_id`

identifies an account.

### E-commerce

`product_id`

identifies a product.

`order_id`

identifies an order.

`(order_id, product_id)`

can identify an order-line relationship.

### Education

`student_id`

identifies a student.

`(student_id, course_id)`

can identify enrollment.

### Healthcare

A system can use internal generated identifiers for patients and encounters, with separate controls for sensitive information.

### Human resources

`employee_id`

can identify an employee while email and other business attributes remain separately constrained.

### Inventory

`warehouse_id` and `product_id` can form a composite relationship identifying a product's inventory record at a particular warehouse.

---

## 43. Python, JavaScript, and C++ Comparison

| Language | Primary Demonstration |
|---|---|
| Python | Relational concepts, SQLite, validation, UUIDs, data modeling |
| JavaScript | `Map`, validation, immutable objects, UUID handling, Web Crypto |
| C++ | Strongly typed domain model, hashing, composite-key structures, performance |

### Python

Python is useful for quickly modeling relational concepts and executing a real SQLite database through its standard library.

### JavaScript

JavaScript demonstrates how database identity concepts interact with application-level data structures and runtime validation.

### C++

C++ makes memory representation, hashing, value objects, type safety, and performance considerations more explicit.

The same relational concept can therefore be understood at several implementation levels.

---

## 44. Design Principles

A robust primary-key design generally follows these principles:

1. Define entity identity explicitly.
2. Choose a candidate key that is genuinely unique.
3. Prefer stable identity.
4. Keep business uniqueness separate when appropriate.
5. Use composite keys when the combination itself represents identity.
6. Enforce critical constraints at the database level.
7. Validate foreign-key relationships.
8. Consider key width and index costs.
9. Consider distributed generation requirements.
10. Treat identifiers as identifiers, not authorization credentials.
11. Consider privacy before exposing identifiers.
12. Test duplicate and invalid cases.
13. Consider the entire lifecycle of referenced records.
14. Choose key structure based on domain requirements rather than habit.

---

## 45. Key Concepts Demonstrated by the Three Implementations

The complete implementations collectively demonstrate:

- primary-key uniqueness
- non-null identity
- entity identification
- candidate keys
- alternate keys
- natural keys
- surrogate keys
- integer identifiers
- UUID identifiers
- composite primary keys
- foreign keys
- referential integrity
- validation
- immutable identity objects
- hash-based data structures
- database constraints
- SQLite
- transactions
- rollback concepts
- indexing
- lookup complexity
- security considerations
- realistic order-management modeling
- testing
- edge cases
- production-oriented design considerations

The central principle is that a primary key is not simply an arbitrary column containing unique numbers. It is the database's declared mechanism for identifying each row as a distinct entity or relationship instance.
