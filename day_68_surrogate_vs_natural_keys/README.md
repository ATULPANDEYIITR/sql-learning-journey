# Surrogate vs Natural Keys

## 1. Introduction

Database keys identify records and establish relationships between relational tables. Choosing an appropriate key affects data integrity, indexing, storage, application architecture, distributed processing, and long-term database maintenance.

Two fundamental identification approaches are:

- **Surrogate keys:** Artificial identifiers created specifically for database identification.
- **Natural keys:** Existing business attributes that independently identify an entity.

A third important consideration is how surrogate identifiers are generated. PostgreSQL supports identity columns, sequences, and UUID generation, each serving different architectural requirements.

The implementations demonstrate these mechanisms through customer registration, business identification, email changes, and order processing.

## 2. Surrogate Keys

A surrogate key is an artificial identifier without direct business meaning.

For example:

| customer_id | public_id | email |
|---:|---|---|
| 1 | UUID-A | alice@example.com |
| 2 | UUID-B | bob@example.com |
| 3 | UUID-C | charlie@example.com |

The integer identifier and UUID identify the same customer through different representations.

### Characteristics

- Generated independently of business attributes.
- Usually immutable after record creation.
- Suitable for primary-key relationships.
- Independent of changes to names, email addresses, and business details.
- Can be generated centrally or independently, depending on the identifier strategy.

A surrogate identifier should not be confused with an authentication credential. Knowing a customer's UUID must not automatically grant access to the customer's information.

## 3. Natural Keys

A natural key consists of one or more meaningful business attributes that uniquely identify an entity.

Examples include:

- Country code and business registration number.
- Product SKU within a defined product catalogue.
- An externally assigned account reference.
- A government-issued identifier within an appropriate legal and operational context.

A natural key may consist of one attribute or multiple attributes.

### Composite natural keys

Consider:

| country_code | registration_number | business_name |
|---|---|---|
| IN | TAX-1001 | Indian Enterprise |
| US | TAX-1001 | American Enterprise |
| IN | TAX-1002 | Second Indian Enterprise |

The registration number alone does not identify the business globally. The combination of country code and registration number does.

The resulting primary-key definition is:

`PRIMARY KEY (country_code, registration_number)`

This prevents duplicate combinations while allowing the same registration number in different countries.

### Natural key limitations

Natural identifiers may:

- Change when business information is corrected.
- Be reused under certain business rules.
- Be incorrectly entered.
- Depend on external organizations.
- Contain personally identifiable information.
- Require multiple columns for uniqueness.

A business attribute should not be assumed to be unique merely because it appears unique in a small sample.

## 4. Surrogate Key Generation Strategies

### 4.1 Identity columns

An identity column is a database-managed numeric identifier.

PostgreSQL example:

`customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`

Important characteristics:

- PostgreSQL manages value allocation.
- The underlying sequence generates identifiers.
- `GENERATED ALWAYS` prevents ordinary explicit value insertion.
- Values generally increase as records are inserted.
- Sequence values are not guaranteed to be consecutive.

Identity columns are appropriate for internal relational identifiers when the database is responsible for record creation.

### 4.2 Explicit sequences

A sequence is an independent database object that generates numeric values.

The PostgreSQL implementation creates:

`customer_reference_seq`

Its configuration includes:

| Property | Configuration |
|---|---|
| Starting value | 10001 |
| Increment | 1 |
| Cache | 50 |
| Cycle | Disabled |

Sequence values can be obtained using `nextval()`.

Sequences can support:

- Order references.
- Invoice numbers.
- Internal identifiers.
- Independent numbering systems.

A sequence is not automatically a primary key. The table must enforce uniqueness when the generated value is used as a unique identifier.

Identity columns also use sequences internally, but identity columns provide a more integrated table-column definition.

### 4.3 UUID identifiers

A UUID is a 128-bit identifier.

The implementations use UUID version 4 for independently generated identifiers.

Example:

`550e8400-e29b-41d4-a716-446655440000`

UUID characteristics:

- Can be generated without obtaining the next integer from a central database.
- Suitable for distributed record creation.
- Useful for public-facing resource references.
- Require more storage than a BIGINT identifier.
- Random UUIDv4 values do not provide chronological ordering.

PostgreSQL implementation:

`public_id UUID NOT NULL DEFAULT gen_random_uuid()`

UUID collisions are extremely unlikely with correctly generated UUIDv4 identifiers, but uniqueness constraints should still be enforced.

UUIDv7 is another option when time-oriented ordering and distributed generation are desirable. Its ordering properties differ from UUIDv4.

## 5. Technical Comparison

| Property | Identity / BIGINT | UUIDv4 | Natural key |
|---|---|---|---|
| Meaning | Artificial | Artificial | Business-derived |
| Size | 8 bytes | 16 bytes | Variable |
| Generation | Database sequence | UUID generator | Business system |
| Central coordination | Usually required for allocation | Not required for generation | Depends on business rules |
| Mutability | Normally immutable | Normally immutable | May change |
| Guessability | Sequential values are predictable | UUIDv4 is difficult to predict | Depends on attributes |
| Distributed creation | Requires allocation strategy | Well suited | Requires uniqueness coordination |
| Index locality | Generally good | Random inserts can reduce locality | Depends on values |
| Foreign-key usage | Excellent for internal relationships | Suitable | Can increase relationship complexity |

The choice depends on workload, distribution architecture, business rules, and the lifetime of the identifier.

## 6. Hybrid Key Architecture

A practical relational design can combine surrogate and natural keys.

The customer table uses:

- `customer_id`: Internal BIGINT primary key.
- `public_id`: UUID for external resource identification.
- `email`: Unique natural business attribute.
- `external_reference`: Optional identifier assigned by another system.

The architecture separates internal identity from externally meaningful attributes.

### Relationship diagram

    Customer
       |
       | customer_id (BIGINT)
       |
       +--------------------+
       |                    |
       v                    v
    Orders          Customer Registrations
                            |
                            | country_code
                            | registration_number
                            v
                    Business Registrations
                            |
                            + Composite Natural PK

This design provides compact internal relationships while preserving natural business identifiers.

### Why use two surrogate identifiers?

An internal numeric identifier provides efficient relational joins.

A UUID can provide a globally unique reference for APIs and distributed systems.

For example:

- Internal database queries use `customer_id`.
- External API resources expose `public_id`.
- Business integrations use `external_reference`.
- Business validation uses natural identifiers.

The identifiers have separate responsibilities and should not be treated as interchangeable.

## 7. Python Implementation

The Python file implements an in-memory customer repository.

### Main components

| Component | Responsibility |
|---|---|
| `Customer` | Stores customer attributes and identifiers |
| `CustomerRepository` | Manages records and surrogate indexes |
| `NaturalKeyRegistry` | Maintains composite natural identifiers |
| `KeyStatistics` | Reports identifier counts |
| `KeyDesignAnalyzer` | Compares identification strategies |
| `TestKeyDesign` | Validates expected behavior |

### Implementation mechanisms

The repository uses dictionaries for:

- Integer identity lookup.
- UUID lookup.
- Email lookup.
- External-reference lookup.

These indexes provide average constant-time lookup under normal hash-table behavior.

Email normalization is performed before indexing. This prevents differently capitalized versions of the same email from bypassing application-level duplicate detection.

The email update operation changes the email index without modifying the customer's integer identity or UUID.

The test suite covers:

- UUID generation.
- Natural identifier uniqueness.
- Email modification.
- Duplicate email rejection.
- Composite natural keys.
- Invalid country codes.
- Missing records.
- Index cleanup after deletion.

The repository is an educational in-memory model. It does not provide durable storage or transaction isolation equivalent to PostgreSQL.

## 8. JavaScript Implementation

The JavaScript file uses an event-driven service architecture.

### Main components

| Component | Responsibility |
|---|---|
| `CustomerService` | Customer lifecycle and identifier management |
| `Customer` | Customer domain object |
| `NaturalKeyRegistry` | Composite natural key management |
| `OrderService` | Order creation and customer references |
| `IdentifierValidator` | Attribute normalization and validation |
| `KeyPolicy` | Identifier strategy descriptions |

### JavaScript-specific mechanisms

The implementation uses:

- `Map` for indexed record storage.
- `EventEmitter` for customer lifecycle events.
- `randomUUID()` for UUID generation.
- `Object.freeze()` for immutable order and natural-key records.
- `Object.seal()` for customer object structure.
- Promises for asynchronous operations.
- Private class fields for encapsulating repository state.

Customer creation emits a `customerCreated` event.

Email modifications emit a `customerEmailChanged` event.

This event-driven approach separates customer state changes from other application components that may need to respond to them.

The order service references customers using stable internal identifiers. Email changes therefore do not invalidate existing orders.

The retry implementation demonstrates asynchronous failure handling. In a production system, retries should be restricted to transient failures and operations should use idempotency controls when repeated execution could create duplicate records.

## 9. C++17 Implementation

The C++ program models a customer and order management system.

### Main domain types

| Type | Purpose |
|---|---|
| `UUID` | Public identifier |
| `Customer` | Customer entity |
| `Order` | Order entity |
| `NaturalKey` | Composite business identifier |
| `CustomerRepository` | Customer storage and indexing |
| `NaturalKeyRegistry` | Natural identifier management |
| `OrderRepository` | Referential relationship management |

### Implementation decisions

The program uses:

- `std::map` for ordered identity-based storage.
- `std::unordered_map` for UUID and email indexes.
- `std::set`-style uniqueness principles through ordered key structures.
- `std::tuple` for composite-key comparison.
- `std::optional`-compatible design considerations for optional references.
- Exceptions for invalid operations.
- STL algorithms for normalization.

The UUID generator uses random 64-bit values and applies UUID version 4 and variant bits.

The order repository validates the referenced customer before creating an order.

It also checks the customer's state, preventing suspended customers from placing new orders.

### Complexity

| Operation | Expected complexity |
|---|---|
| Identity lookup using `std::map` | O(log n) |
| UUID lookup using `std::unordered_map` | Average O(1) |
| Email lookup using `std::unordered_map` | Average O(1) |
| Composite-key lookup using `std::map` | O(log n) |
| Customer listing | O(n) |
| Order filtering by customer | O(n) |

The UUID generator is a demonstration implementation. Production systems should use a thoroughly tested UUID implementation and suitable operating-system randomness.

## 10. Java 17 Implementation

The Java implementation presents an enterprise-oriented domain model.

### Domain types

- `CustomerId`: Strongly typed internal identifier.
- `PublicCustomerId`: Strongly typed UUID.
- `NaturalCustomerKey`: Composite business identifier.
- `Customer`: Immutable customer record.
- `Order`: Immutable order record.
- `CustomerStatus`: Customer lifecycle state.
- `OrderStatus`: Order lifecycle state.

Java records provide concise immutable data structures for identifiers and domain values.

The `KeyGenerator` interface separates identifier generation from customer management.

`IdentityGenerator` handles internal numeric identifiers.

`UUIDGenerator` uses `SecureRandom` to construct UUIDv4 values.

### Service architecture

`CustomerRepository` manages customer records and indexes.

`CustomerService` provides customer registration and email modification operations.

`NaturalKeyRepository` enforces natural-key uniqueness.

`OrderService` creates orders and validates customer references.

### Enterprise controls

The implementation includes:

- Strongly typed identifiers.
- Immutable record-based domain objects.
- Explicit validation.
- Custom exception types.
- Synchronized repository operations.
- Customer status enforcement.
- Referential integrity checks.
- Unmodifiable policy descriptions.

Synchronization protects the example's in-memory repository operations within one JVM. It does not replace database transactions or distributed concurrency controls.

## 11. PostgreSQL Implementation

The SQL file provides a relational implementation using PostgreSQL.

### Database objects

| Object | Purpose |
|---|---|
| `key_design.customers` | Customer records |
| `key_design.business_registrations` | Natural business identifiers |
| `key_design.customer_business_registrations` | Customer-to-business relationships |
| `key_design.orders` | Order records |
| `key_design.customer_identifier_audit` | Email change history |
| `customer_reference_seq` | Independent sequence |
| `customer_key_report` | Customer reporting view |
| `natural_identifier_report` | Natural-key reporting view |

### Constraints

The database enforces:

- Primary-key uniqueness.
- UUID uniqueness.
- Email uniqueness.
- External-reference uniqueness.
- Composite natural-key uniqueness.
- Foreign-key integrity.
- Valid customer states.
- Valid monetary amounts.
- Valid country codes.

These constraints protect the data even when records are inserted outside the application.

### Trigger operations

Two triggers demonstrate automated database behavior.

`trg_customer_timestamp` updates the customer's modification timestamp.

`trg_customer_email_audit` records old and new email values whenever an email changes.

The audit table references the stable internal customer identifier.

### Functions and procedures

`register_customer()` creates a customer and returns both surrogate identifiers.

`create_customer_order()` validates customer existence, checks customer status, and creates an order.

The procedure uses a row-level lock with `FOR UPDATE` while validating the customer. This helps coordinate concurrent operations involving that customer's state.

### Query mechanisms

The SQL script demonstrates:

- Direct retrieval by identity.
- UUID retrieval.
- Natural-key retrieval.
- Composite-key aggregation.
- Surrogate foreign-key joins.
- Natural-key relationships.
- Duplicate detection.
- Referential integrity validation.
- CTE-based eligibility evaluation.
- Customer activity reporting.
- Sequence inspection.
- Audit retrieval.

## 12. Choosing an Appropriate Key

Key selection should follow the identity requirements of the entity.

| Requirement | Suitable approach |
|---|---|
| Internal transactional database | BIGINT identity |
| Distributed record creation | UUID |
| Public resource references | UUID |
| Business registration uniqueness | Natural or composite natural key |
| Human-readable sequential reference | Explicit sequence |
| High-volume relational joins | BIGINT surrogate |
| External system integration | Dedicated external reference |
| Multi-country business registration | Composite natural key |

A hybrid architecture is often appropriate because internal relational identity and business identity solve different problems.

## 13. Important Design Risks

### Mutable natural identifiers

Changing a natural identifier that is referenced by multiple tables can require extensive updates.

Using surrogate foreign keys avoids propagating changes to every dependent relationship.

Natural identifiers should still have appropriate uniqueness constraints.

### UUID index overhead

UUID values occupy more storage than BIGINT values.

Random UUIDv4 insertion patterns can also reduce B-tree index locality and increase page fragmentation.

For high-volume databases, benchmark UUIDv4 and UUIDv7 against the actual insertion and retrieval workload.

### Sequence gaps

Sequences are not gapless numbering systems.

A transaction can obtain a sequence value and subsequently roll back. Cached values can also produce gaps.

If legal or business requirements demand gapless document numbering, a separately controlled transactional numbering mechanism may be required.

### Natural identifier privacy

Natural identifiers may contain confidential or personally identifiable information.

Exposing them in URLs, application logs, or analytics systems can create privacy and security risks.

Public UUIDs can reduce direct exposure of internal numeric identifiers, but they do not replace authentication or authorization.

### Identifier collisions

All identifier strategies require appropriate uniqueness enforcement.

For UUIDs, the database unique constraint protects against accidental collisions.

For natural identifiers, the uniqueness definition must accurately reflect business rules, including normalization and relevant organizational scope.

## 14. Practical Design Principles

- Prefer immutable surrogate keys for internal relational relationships.
- Use identity columns when database-managed numeric allocation is appropriate.
- Use explicit sequences when independent number generation is required.
- Use UUIDs when distributed generation or public resource identification is important.
- Preserve natural identifiers as business attributes with explicit uniqueness constraints.
- Use composite natural keys when uniqueness depends on multiple business attributes.
- Avoid assuming that email addresses, names, or phone numbers are permanent identifiers.
- Apply database-level constraints rather than relying exclusively on application validation.
- Maintain audit history when important business identifiers change.
- Evaluate index size, insertion behavior, and query performance using actual workloads.

The central distinction is that a surrogate key identifies a database entity, while a natural key identifies that entity through business-defined attributes. A well-designed relational system can maintain both without confusing their responsibilities.
