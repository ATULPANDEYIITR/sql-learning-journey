# Database Schema Design

## OLTP Schema Design, Naming Conventions, Keys and Constraints

## 1. Scope

This project implements a relational database design for an order-processing system. It demonstrates how to model transactional business operations using normalized tables, well-defined relationships, candidate keys, referential integrity, constraints, indexes and transaction boundaries.

The business domain contains:

- Customers
- Customer addresses
- Products
- Orders
- Order items
- Payments

The five implementations approach the same database-design subject from different engineering perspectives:

| Deliverable | Main implementation |
|---|---|
| Python | Schema catalog, dependency analysis and transactional SQLite operations |
| JavaScript | Event-driven schema registry and relational integrity evaluator |
| C++17 | Schema dependency engine and transactional in-memory database |
| Java 17 | Enterprise domain model and transactional order service |
| PostgreSQL | Executable relational schema, constraints, indexes, triggers, procedures and reporting |

## 2. OLTP Database Design

Online Transaction Processing (OLTP) databases support frequent, relatively small transactions that insert, update, retrieve and delete operational records.

Typical OLTP operations include:

- Registering a customer.
- Creating an order.
- Adding products to an order.
- Recording a payment.
- Updating an order status.
- Retrieving an individual customer's transaction history.

OLTP design prioritizes:

1. Data correctness.
2. Transaction consistency.
3. Referential integrity.
4. Predictable query performance.
5. Concurrent transaction handling.
6. Controlled updates and deletions.

An OLTP database generally uses normalized tables to reduce duplication and prevent inconsistent updates.

### 2.1 Transactional workflow

The implemented business workflow is:

Customer
  |
  +---- Customer Addresses
  |
  +---- Orders
           |
           +---- Order Items
           |       |
           |       +---- Products
           |
           +---- Payments

A customer can create multiple orders. Each order can contain multiple order items. Each order item references one product. An order can also have multiple payment attempts.

The relationships are enforced through foreign keys rather than application-level assumptions.

### 2.2 OLTP versus analytical databases

| Characteristic | OLTP | OLAP |
|---|---|---|
| Primary purpose | Operational transactions | Analytical processing |
| Data structure | Usually normalized | Often dimensional |
| Operations | INSERT, UPDATE, DELETE, SELECT | Aggregation and complex SELECT |
| Query scope | Individual records and small groups | Large datasets |
| Consistency | Strong transactional integrity | Depends on analytical architecture |
| Example | Order placement | Monthly sales analysis |

The PostgreSQL implementation uses normalized operational tables and reporting views. Analytical queries are included to demonstrate reporting without replacing the underlying transactional structure.

## 3. Naming Conventions

Consistent naming reduces ambiguity and makes schemas easier to maintain.

The implementations use lowercase snake_case for table and column names.

### 3.1 Naming rules

| Database object | Convention | Example |
|---|---|---|
| Table | Plural snake_case | `customers` |
| Column | Singular snake_case | `customer_id` |
| Primary key | `pk_<table>` | `pk_customers` |
| Foreign key | `fk_<table>_<reference>` | `fk_orders_customer` |
| Unique constraint | `uq_<table>_<column>` | `uq_customers_email` |
| Check constraint | `ck_<table>_<rule>` | `ck_order_items_quantity` |
| Index | `idx_<table>_<columns>` | `idx_orders_customer_created` |
| Trigger | `trg_<table>_<purpose>` | `trg_orders_updated_at` |
| View | `v_<purpose>` | `v_order_totals` |

### 3.2 Consistency rules

- Use descriptive names instead of unexplained abbreviations.
- Use the same identifier terminology across related tables.
- Avoid reserved SQL keywords as identifiers.
- Avoid unnecessary prefixes in column names.
- Use explicit constraint names.
- Keep names stable because application queries and database migrations depend on them.

For example, `customer_id` should be used consistently wherever a customer is referenced.

A column named `cust_no` in one table and `customer_ref` in another creates unnecessary ambiguity.

## 4. Relational Modeling

A relational database organizes information into tables consisting of rows and columns.

Each table represents an entity or a relationship.

### 4.1 Entities

| Entity | Responsibility |
|---|---|
| Customers | Stores customer identity and contact details |
| Customer Addresses | Stores multiple customer addresses |
| Products | Stores product descriptions and current prices |
| Orders | Stores order-level information |
| Order Items | Stores individual products purchased in an order |
| Payments | Stores payment attempts and payment status |

The distinction between `orders` and `order_items` is particularly important.

An order contains information that applies to the complete transaction, such as customer identity and order status.

Order items contain information specific to individual purchased products, including quantity and transaction price.

Combining these entities into a single table would repeat customer and order information for every product.

### 4.2 Cardinality

Cardinality describes how many records in one entity can be associated with records in another entity.

| Relationship | Cardinality |
|---|---|
| Customer to Orders | One-to-many |
| Customer to Addresses | One-to-many |
| Order to Order Items | One-to-many |
| Product to Order Items | One-to-many |
| Order to Payments | One-to-many |

The relationship between orders and products is many-to-many at the business level.

The `order_items` table resolves this relationship.

An order can contain several products, and a product can appear in several orders.

The intermediate table also stores relationship-specific attributes such as quantity and purchase price.

## 5. Keys and Their Roles

Keys identify records and establish relationships between tables.

### 5.1 Primary keys

A primary key uniquely identifies every row in a table.

The implementations use identifiers such as:

- `customer_id`
- `product_id`
- `order_id`
- `order_item_id`
- `payment_id`

Primary keys must be unique and cannot contain NULL values.

The PostgreSQL implementation uses identity columns for generated numeric identifiers.

Example:

`customer_id BIGINT GENERATED ALWAYS AS IDENTITY`

Identity columns provide database-managed identifier generation.

They do not guarantee gapless numbering. Sequence values can be consumed by transactions that subsequently roll back.

### 5.2 Natural keys

A natural key is derived from an attribute that has business meaning.

Examples include:

- Customer email address.
- Product SKU.
- External transaction reference.

The customer email and product SKU are implemented as unique candidate keys.

Natural keys can change, so they are not necessarily suitable as permanent internal references.

For example, a customer may change their email address. An internal customer identifier remains stable.

### 5.3 Surrogate keys

A surrogate key is an artificial identifier that has no direct business meaning.

The implementation uses surrogate primary keys for customers, products and orders.

Advantages include:

- Stable internal references.
- Smaller foreign-key values when numeric identifiers are used.
- Independence from changing business attributes.
- Simplified joins.

A surrogate primary key does not eliminate the need for natural-key uniqueness.

The database must still prevent duplicate customer emails and product SKUs when those attributes are required to be unique.

### 5.4 Candidate keys

A candidate key is a minimal set of attributes that uniquely identifies a record.

For the customer table:

- `customer_id`
- `email`

Both can uniquely identify a customer.

The database selects `customer_id` as the primary key. The email remains an alternate candidate key through a unique constraint.

### 5.5 Composite keys

A composite key consists of multiple columns.

The `order_items` table uses:

`UNIQUE (order_id, product_id)`

This prevents the same product from appearing twice as separate lines in the same order.

The constraint allows the database to enforce a business rule that application validation alone cannot reliably guarantee under concurrent requests.

A composite primary key is another possible design:

`PRIMARY KEY (order_id, product_id)`

The implementation instead uses a surrogate `order_item_id` as its primary key and preserves the composite business rule as a unique constraint.

This provides a simple row identifier while maintaining the required relationship uniqueness.

## 6. Constraints and Data Integrity

Constraints enforce business and structural rules at the database level.

They protect the database even when multiple applications, scripts or users access the same tables.

### 6.1 NOT NULL

A NOT NULL constraint prevents a column from containing NULL.

Examples:

- Customer email.
- Customer name.
- Product SKU.
- Order customer identifier.
- Order item quantity.

It is appropriate when a value is mandatory for a valid business record.

### 6.2 UNIQUE

A UNIQUE constraint prevents duplicate values or duplicate combinations of values.

Examples:

- Customer email.
- Product SKU.
- Order reference.
- Order and product combination.

PostgreSQL permits multiple NULL values in an ordinary unique constraint by default. A separate NOT NULL constraint is required when every row must contain the candidate-key value.

### 6.3 CHECK

A CHECK constraint enforces a condition on column values.

Examples:

| Column | Rule |
|---|---|
| `unit_price` | Must be greater than or equal to zero |
| `quantity` | Must be greater than zero |
| `payment_amount` | Must be greater than zero |
| `currency_code` | Must contain three uppercase letters |
| `address_type` | Must be BILLING or SHIPPING |

CHECK constraints are useful for row-level validation.

They should not be used as a replacement for foreign keys or cross-row transactional rules.

### 6.4 DEFAULT

DEFAULT supplies a value when an INSERT statement omits a column.

Examples:

- `is_active DEFAULT TRUE`
- `order_status DEFAULT 'PENDING'`
- `created_at DEFAULT CURRENT_TIMESTAMP`

A default does not override an explicitly supplied NULL value.

If NULL is forbidden, NOT NULL must also be defined.

### 6.5 Foreign keys

A foreign key ensures that a referenced record exists.

For example:

`orders.customer_id` references `customers.customer_id`.

An order cannot reference a customer who does not exist.

Foreign keys protect relationships even when records are inserted directly through SQL rather than through application services.

### 6.6 Referential actions

The PostgreSQL schema uses different deletion policies according to relationship ownership.

| Action | Meaning | Application |
|---|---|---|
| RESTRICT | Prevent deletion when dependent records exist | Customers and products |
| CASCADE | Delete dependent records when the parent is deleted | Order items belonging to an order |
| SET NULL | Clear the referencing value | Optional relationships where NULL is permitted |
| NO ACTION | Check referential integrity according to constraint timing | General referential integrity |

CASCADE must be used carefully.

Deleting a customer should not automatically erase financial and operational transaction history.

The implementation therefore restricts customer deletion when orders reference that customer.

## 7. Database Normalization

Normalization reduces unnecessary duplication and prevents update anomalies.

### 7.1 First Normal Form

First Normal Form (1NF) requires atomic column values and the absence of repeating groups.

A poorly designed order table might contain:

| order_id | customer_name | product_1 | product_2 |
|---|---|---|---|
| 5001 | Aarav Sharma | Laptop | Keyboard |

This design introduces a fixed number of product columns and makes queries difficult.

The implementation separates individual products into `order_items`.

Each row represents one product relationship within an order.

### 7.2 Second Normal Form

Second Normal Form (2NF) requires:

- Satisfaction of 1NF.
- No partial dependency of non-key attributes on part of a candidate key.

Consider an order-item relation with composite key `(order_id, product_id)`.

The product name depends on `product_id`, not on the complete composite key.

The product description therefore belongs in `products`.

The order-level status belongs in `orders`.

### 7.3 Third Normal Form

Third Normal Form (3NF) requires:

- Satisfaction of 2NF.
- No inappropriate transitive dependency of non-key attributes on candidate keys.

For example, storing customer address details repeatedly in the orders table can create duplication when customers place multiple orders.

The implementation separates customer addresses into `customer_addresses`.

This allows address information to be maintained independently.

### 7.4 Transaction price versus current product price

The `products` table stores the current selling price.

The `order_items` table stores the price agreed when the transaction occurred.

These values serve different purposes.

If a product price changes from INR 65,000 to INR 70,000, an earlier order must continue to reflect the original purchase price.

This is a deliberate preservation of historical transaction information, not accidental duplication.

## 8. Index Design and Query Performance

Indexes accelerate data retrieval by providing structures that help the database locate records without scanning every row.

Indexes also consume storage and increase the cost of INSERT, UPDATE and DELETE operations.

The PostgreSQL implementation creates indexes according to expected access patterns.

| Index | Columns | Purpose |
|---|---|---|
| `idx_addresses_customer` | `customer_id` | Retrieve customer addresses |
| `idx_orders_customer_created` | `customer_id, created_at` | Retrieve recent customer orders |
| `idx_orders_status_created` | `order_status, created_at` | Retrieve orders by status and time |
| `idx_order_items_product` | `product_id` | Retrieve order-item references for a product |
| `idx_payments_order` | `order_id` | Retrieve payment attempts for an order |
| `idx_products_active` | `product_id` | Support access to active products |

### 8.1 Composite index ordering

The index:

`(customer_id, created_at DESC)`

is designed for queries that filter by customer and retrieve recent orders.

The leading column matters.

An index on `(customer_id, created_at)` is not generally equivalent to an index on `(created_at, customer_id)` for the same query workload.

Index design should follow actual filtering, joining and sorting patterns.

### 8.2 Foreign-key indexing

PostgreSQL automatically indexes primary keys and unique constraints.

It does not automatically create an index on every referencing foreign-key column.

Indexes on referencing columns can improve joins and help parent-record deletion or update checks.

The implementation explicitly indexes frequently accessed foreign-key columns.

### 8.3 Query-plan analysis

The SQL script includes:

`EXPLAIN (ANALYZE, BUFFERS)`

This provides execution information, including actual execution time and buffer activity.

For production systems, query plans should be evaluated against representative data volumes and realistic query distributions.

A small demonstration dataset does not provide reliable evidence of production performance.

## 9. Transactions and ACID Properties

A transaction groups multiple database operations into one logical unit.

The order-processing workflow must not create an order header without its required line items.

The relevant ACID properties are:

| Property | Meaning |
|---|---|
| Atomicity | All operations succeed or the transaction is rolled back |
| Consistency | Database rules remain satisfied |
| Isolation | Concurrent transactions do not produce invalid intermediate results |
| Durability | Committed changes survive failures according to database durability guarantees |

### 9.1 Atomic order creation

The PostgreSQL procedure performs the following operations:

1. Validates the customer.
2. Validates the item collection.
3. Rejects duplicate product identifiers.
4. Creates the order header.
5. Retrieves trusted product prices.
6. Inserts order items.
7. Returns the generated order identifier.

The procedure executes within the caller's transaction.

If an item cannot be inserted, the exception aborts the current transaction unless handled by an appropriate savepoint or exception-handling structure.

The Python implementation uses SQLite transactions and rollback.

The C++ implementation uses a snapshot to simulate atomic in-memory changes.

The Java implementation validates all products before committing the order and its items to the in-memory service state.

The JavaScript implementation focuses on schema and record validation rather than implementing a durable database transaction.

## 10. Schema Dependency Management

Tables must be created in an order that respects foreign-key dependencies when references are created immediately.

The relationship graph is:

Customers
  |
  +---- Orders
  |       |
  |       +---- Order Items
  |       |
  |       +---- Payments
  |
  +---- Customer Addresses

Products
  |
  +---- Order Items

The Python, JavaScript, C++ and Java implementations perform dependency analysis using graph traversal.

A topological ordering places referenced tables before dependent tables.

A circular dependency produces a schema validation error.

For example:

Table A references Table B.

Table B references Table A.

A simple dependency ordering cannot resolve this cycle without a different creation strategy, such as creating the tables first and adding constraints afterward.

## 11. Python Implementation

The Python script uses SQLite and the standard library.

Its principal components are:

| Component | Responsibility |
|---|---|
| `Column` | Defines column properties |
| `ForeignKey` | Defines referential relationships |
| `Table` | Validates table-level structure |
| `SchemaCatalog` | Manages definitions and dependencies |
| `create_database()` | Creates executable SQLite tables |
| `place_order()` | Processes an atomic order |
| `get_order_report()` | Retrieves transaction information |

### 11.1 Schema catalog

The catalog validates:

- Identifier naming.
- Duplicate columns.
- Primary-key definitions.
- Foreign-key definitions.
- Referenced tables.
- Referenced candidate keys.

The dependency-ordering algorithm uses depth-first search.

Its expected complexity is O(V + E), where V is the number of tables and E is the number of foreign-key dependency edges.

### 11.2 Transaction processing

The order-processing function uses `BEGIN IMMEDIATE`.

This acquires a write reservation before processing the transaction, reducing the risk of competing writers entering conflicting write transactions.

The function reads prices from the database instead of trusting values supplied by callers.

SQL statements use parameterized queries to prevent SQL injection through data values.

### 11.3 Failure handling

The demonstration tests:

- Missing customer references.
- Duplicate product SKUs.
- Unavailable products.
- Duplicate order products.
- Invalid quantities.
- Transaction rollback.

The SQLite schema is an executable teaching implementation. Its database behavior should not be assumed to be identical to PostgreSQL in every detail.

## 12. JavaScript Implementation

The JavaScript implementation uses Node.js standard-library capabilities.

It focuses on event-driven schema registration and a relational integrity evaluator.

### 12.1 SchemaRegistry

The registry uses private class fields and Maps.

It manages:

- Table definitions.
- Column validation.
- Primary keys.
- Candidate keys.
- Foreign keys.
- Index definitions.
- Schema versions.

Events are emitted when tables and indexes are registered.

This separates schema changes from the code that observes those changes.

### 12.2 RelationalStore

The in-memory store validates records before inserting them.

It checks:

- Unknown columns.
- Missing mandatory values.
- Integer and numeric types.
- Unique constraints.
- Composite foreign keys.
- Candidate-key references.
- Duplicate primary keys.

The store uses Maps for record lookup.

The composite-key representation uses JSON serialization of the ordered key values.

This is an in-memory learning model and not a replacement for a database engine.

It does not provide durable storage, concurrent transaction isolation, full SQL semantics or database-level locking.

## 13. C++17 Implementation

The C++ program models database schema dependencies and an in-memory transactional store.

### 13.1 Domain structures

The principal structures are:

- `ColumnDefinition`
- `ForeignKeyDefinition`
- `TableDefinition`
- `SchemaCatalog`
- `TransactionalDatabase`

The program uses STL containers to represent table definitions and records.

The schema catalog validates candidate-key references and foreign-key relationships.

### 13.2 Transaction simulation

The in-memory database uses a snapshot of its storage before processing a batch.

If an operation fails, the original state is restored.

This illustrates atomicity at the application-model level.

It does not reproduce PostgreSQL transaction isolation or crash recovery.

### 13.3 Validation and complexity

The implementation validates:

- Table and column naming.
- Duplicate identifiers.
- Candidate keys.
- Foreign-key relationships.
- Duplicate records.
- Unique constraints.
- Positive quantities.
- Nonnegative unit prices.

The demonstration uses linear scans for some uniqueness and referential-integrity checks.

For N records in a table, these checks can require O(N) lookup time.

A production implementation would use hash-based or ordered indexes for frequently accessed keys.

## 14. Java 17 Implementation

The Java implementation adopts an enterprise-oriented domain model.

It uses records for immutable data structures, enums for controlled states and service classes for business operations.

### 14.1 Domain types

| Type | Responsibility |
|---|---|
| `Customer` | Customer identity |
| `Product` | Product information |
| `Order` | Order state |
| `OrderItem` | Individual transaction line |
| `OrderRequest` | Validated order input |
| `OrderReport` | Reporting projection |
| `SchemaRegistry` | Schema definition and validation |
| `OrderService` | Transactional business workflow |

### 14.2 Immutable structures

Records provide concise immutable data carriers.

For example, an order is represented using an identifier, customer identifier, status and creation timestamp.

Changing its status creates a new record through the `withStatus` method.

This prevents uncontrolled mutation of an existing order object.

### 14.3 Business-state transitions

The order model distinguishes terminal and nonterminal states.

A shipped or cancelled order cannot be changed through the implemented transition method.

The service also validates customer existence and product availability before changing order storage.

### 14.4 Concurrency considerations

The order service uses synchronized methods for the in-memory demonstration.

This serializes relevant operations within the service instance.

It is not a substitute for database transaction isolation, distributed locking or concurrency control across multiple application instances.

A production service should delegate durable transaction guarantees to the database and use appropriate isolation and locking strategies.

## 15. PostgreSQL Implementation

The PostgreSQL script provides the most complete relational implementation.

It uses the `commerce` schema to isolate the business objects.

### 15.1 Database objects

| Object | Purpose |
|---|---|
| `commerce` | Database namespace |
| `order_status` | Controlled order states |
| `customers` | Customer master |
| `products` | Product master |
| `customer_addresses` | Customer addresses |
| `orders` | Order headers |
| `order_items` | Transaction line items |
| `payments` | Payment attempts |
| `v_order_totals` | Order reporting view |

### 15.2 Domain-specific data types

The `order_status` enum restricts order status to:

- PENDING
- CONFIRMED
- SHIPPED
- CANCELLED

This provides database-level control over permitted values.

The implementation uses an enum because the set of statuses is controlled and relatively stable.

For systems requiring frequently configurable states, a lookup table may provide greater flexibility.

### 15.3 Triggers

The implementation uses triggers for two different responsibilities.

**Updated timestamp management**

The `set_updated_at()` trigger function maintains the `updated_at` column when customer or order records are updated.

**Order status transitions**

The `validate_order_status_transition()` function prevents invalid transitions and changes to terminal states.

The `validate_order_item_product()` function checks product availability and prevents modifying line items after an order leaves the pending state.

Triggers enforce rules for direct SQL operations as well as application-originated writes.

### 15.4 Stored procedure

The `create_order()` procedure accepts:

- A customer identifier.
- A JSONB array of requested products and quantities.
- An output order identifier.

It validates the input, rejects duplicate products and retrieves current product prices directly from the database.

The caller controls the transaction boundary.

The procedure does not independently commit the transaction, allowing it to participate in a larger transaction.

### 15.5 Views and reporting

The `v_order_totals` view combines:

- Order headers.
- Customer information.
- Order items.
- Item counts.
- Calculated order totals.

It provides a consistent reporting interface without storing a duplicated order total in the order header.

The script also includes CTEs, window functions, aggregation and eligibility queries.

## 16. Database Migration and Versioning

A schema changes as business requirements evolve.

Examples include:

- Adding a new customer attribute.
- Introducing payment methods.
- Adding a new order status.
- Changing a foreign-key relationship.
- Creating an index for a new query pattern.

A migration should be treated as a controlled, versioned database change.

A reliable migration workflow includes:

1. Review the current schema.
2. Define the intended change.
3. Validate compatibility with existing application code.
4. Apply the migration in a controlled environment.
5. Verify constraints and existing data.
6. Test affected transactions and queries.
7. Deploy compatible application changes.
8. Record the applied migration version.

Destructive migrations require special care.

Dropping a column or changing its type can break older application versions and dependent database objects.

For large OLTP tables, adding constraints or changing column definitions may require careful consideration of locking, table rewrites and deployment duration.

The JavaScript and Java implementations maintain schema version information in their in-memory registries. These are educational representations of version tracking, not durable migration-history systems.

## 17. Security and Reliability

Database schema design contributes directly to application security.

### 17.1 SQL injection prevention

Application code should use parameterized SQL statements.

Unsafe SQL construction concatenates untrusted values into SQL text.

Parameterized statements separate query structure from data values.

The Python implementation uses SQLite placeholders for database operations.

### 17.2 Least privilege

Production database accounts should receive only the permissions required for their responsibilities.

A typical separation is:

| Role | Responsibility |
|---|---|
| Application role | Required SELECT, INSERT and UPDATE operations |
| Reporting role | Read-only access to reporting objects |
| Migration role | Controlled schema changes |
| Administration role | Database administration |

Application accounts should not normally have unrestricted schema-management privileges.

### 17.3 Sensitive data

Customer contact details and payment references should be protected through appropriate access controls.

Sensitive payment credentials should not be stored as unrestricted plain-text values.

Database backups, connection credentials and operational logs also require protection.

### 17.4 Concurrent updates

Concurrent transactions can create conflicts when multiple sessions modify the same records.

PostgreSQL provides transaction isolation levels and row-locking mechanisms.

The procedure uses row-level locking when reading relevant product and order records.

The actual concurrency guarantees depend on the selected isolation level and transaction boundaries.

## 18. Important Edge Cases

| Condition | Expected behavior |
|---|---|
| Duplicate customer email | Reject through UNIQUE |
| Duplicate product SKU | Reject through UNIQUE |
| Missing customer | Reject through FOREIGN KEY |
| Negative unit price | Reject through CHECK |
| Zero or negative quantity | Reject through CHECK |
| Empty order | Reject through procedure validation |
| Duplicate product in one order | Reject through validation and UNIQUE |
| Inactive product | Reject during order processing |
| Delete customer with orders | Restrict deletion |
| Delete order with line items | Cascade dependent line items |
| Invalid order status transition | Reject through trigger |
| Unknown column | Reject through schema validation |
| Circular schema dependency | Reject during dependency analysis |
| Failed multi-item transaction | Roll back all transaction changes |

These conditions demonstrate why data integrity should be enforced at multiple appropriate layers.

Application validation improves error messages and user experience.

Database constraints provide the final integrity boundary.

## 19. Performance and Design Trade-offs

### 19.1 Normalization versus denormalization

Normalization reduces duplication and update anomalies.

Denormalization can reduce the cost of frequently repeated joins but introduces additional consistency responsibilities.

The implementation keeps operational entities normalized.

The order total is calculated through a view rather than stored redundantly.

For high-volume reporting, a separate analytical store or carefully maintained summary structure may be appropriate.

### 19.2 Surrogate versus natural keys

Surrogate identifiers provide stable internal references.

Natural keys preserve business uniqueness.

Using both is appropriate when business attributes can change but must remain unique.

### 19.3 Indexes versus write performance

Additional indexes improve some reads but increase write overhead.

Index selection must be based on query patterns rather than the assumption that every column should be indexed.

### 19.4 Cascading deletes versus historical retention

CASCADE is useful for dependent records that have no independent lifecycle.

Financial and operational records often require retention.

The implementation restricts customer and product deletion where historical transactions depend on those entities.

### 19.5 Computed versus stored values

Calculated order totals avoid duplicated values that can become inconsistent.

Stored historical prices are necessary because current product prices can change.

These two decisions illustrate the difference between a derived value and a historical transaction attribute.

## 20. Validation Checklist

A schema review should verify the following properties.

| Review area | Validation |
|---|---|
| Entity modeling | Tables represent distinct business entities |
| Naming | Consistent snake_case identifiers |
| Primary keys | Every operational table has a stable primary key |
| Candidate keys | Natural uniqueness is enforced |
| Foreign keys | Relationships reference valid candidate keys |
| Data types | Types match business meaning and value ranges |
| Nullability | Mandatory attributes use NOT NULL |
| Unique constraints | Duplicate business identifiers are rejected |
| Check constraints | Invalid row-level values are rejected |
| Normalization | Unnecessary duplication is minimized |
| Transactions | Related operations are atomic |
| Indexes | Frequent joins and filters have appropriate indexes |
| Security | Parameterized queries and restricted permissions are used |
| Historical accuracy | Transaction-specific values are preserved |
| Migrations | Schema changes are versioned and validated |
| Concurrency | Conflicting operations are handled safely |

## 21. Execution Requirements

| Deliverable | Runtime |
|---|---|
| Python | Python 3.10+ with standard library |
| JavaScript | Node.js 18+ |
| C++17 | Compiler supporting C++17 |
| Java | JDK 17 |
| PostgreSQL | PostgreSQL 15+ |

The Python, JavaScript, C++17 and Java programs use standard-library functionality without third-party dependencies.

The PostgreSQL script uses `gen_random_uuid()` for order and payment references. This function is available in modern PostgreSQL installations.

The PostgreSQL script is designed for a dedicated learning database because it creates a schema and its associated database objects.

## 22. Implementation Limitations

The implementations have different persistence and transaction capabilities.

| Implementation | Persistence | Transaction behavior |
|---|---|---|
| Python | SQLite in-memory database | Actual SQLite transaction |
| JavaScript | In-memory Maps | Record-level validation, no durable transaction |
| C++17 | In-memory STL containers | Snapshot-based rollback simulation |
| Java 17 | In-memory collections | Synchronized service operations with pre-validation |
| PostgreSQL | Relational database | Database-managed ACID transactions |

The in-memory implementations illustrate schema concepts and application-level integrity checks.

They do not replace database-managed concurrency, crash recovery, durable storage, query optimization or isolation.

The PostgreSQL implementation provides the actual relational enforcement mechanisms for the modeled OLTP workflow.
