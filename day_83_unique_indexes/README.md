# Unique Indexes: Enforcing Uniqueness and Index-Backed Constraints

## 1. Introduction

A unique index is a database structure that prevents multiple rows from having the same indexed key.

It combines two important database responsibilities:

- **Data integrity:** Prevents duplicate values according to a defined uniqueness rule.
- **Data access:** Maintains an ordered or searchable index structure that can accelerate qualifying queries.

A unique index is not merely a performance optimization. It is an enforcement mechanism that protects data integrity during concurrent transactions.

Consider an account-management system in which users register with email addresses. Two accounts must not use the same normalized email address, even if one address contains uppercase characters.

A database-level unique index can enforce this requirement consistently across applications, services, administrative operations and concurrent transactions.

## 2. Unique Index Fundamentals

A conventional index maintains relationships between indexed keys and the corresponding table rows.

A unique index adds a restriction: two indexed rows cannot have the same key under the index's comparison rules.

For example:

| Account ID | Email |
|---:|---|
| 101 | alice@example.com |
| 102 | bob@example.com |
| 103 | charlie@example.com |

A unique index on `email` permits these records because each indexed value is different.

An attempted insertion of another `alice@example.com` violates the index.

### 2.1 How uniqueness is enforced

A simplified representation of an index is:

    Index Key                 Table Row
    -----------------------------------
    alice@example.com         101
    bob@example.com           102
    charlie@example.com       103

When a new row is inserted, the database:

1. Computes the indexed key.
2. Locates the appropriate index position.
3. Determines whether an equivalent key already exists.
4. Rejects the operation if uniqueness would be violated.
5. Inserts the new index entry if the key is available.
6. Completes the transaction according to its transactional rules.

PostgreSQL commonly uses B-tree indexes for unique enforcement.

B-tree structures maintain keys in an ordered arrangement, supporting efficient searches and insertions.

For a balanced B-tree, lookup and insertion generally have logarithmic complexity relative to the number of indexed entries.

The exact cost depends on tree height, page access, cache behavior, concurrency and storage characteristics.

## 3. Unique Constraints and Unique Indexes

PostgreSQL supports both unique constraints and standalone unique indexes.

They are closely related but represent different database objects.

| Characteristic | Unique constraint | Unique index |
|---|---|---|
| Primary purpose | Expresses a relational integrity rule | Enforces uniqueness through an index |
| Database object | Constraint | Index |
| Enforcement | Uses a supporting unique index | Enforced directly by the index |
| Composite keys | Supported | Supported |
| Expression keys | Not directly supported as constraint columns | Supported |
| Partial uniqueness | Not directly supported | Supported |
| Deferrable enforcement | Supported | Standalone unique indexes are immediate |
| Catalog inspection | Constraint metadata | Index metadata |

A PostgreSQL unique constraint automatically creates a supporting unique index.

For example, the following constraint:

- `UNIQUE (tenant_id, username)`

creates an index-backed restriction on the combination of those columns.

A standalone unique index can express more specialized rules, such as uniqueness over a normalized expression or only a selected subset of rows.

### 3.1 Primary keys versus unique indexes

A primary key identifies each row and requires non-null values.

A table can have only one primary key, although that primary key can contain multiple columns.

A table can have multiple unique constraints and unique indexes.

For example:

- `account_id` identifies the account.
- `email` identifies the email address.
- `(tenant_id, username)` identifies a username within a tenant.

These are separate integrity rules serving different purposes.

## 4. Single-Column Unique Indexes

A single-column unique index restricts duplicate values in one indexed column.

Example:

    CREATE UNIQUE INDEX uq_employee_email
    ON employees (email);

The index prevents two rows from having the same non-null email value under the applicable comparison rules.

Typical applications include:

- Employee email addresses.
- Product serial numbers.
- Customer reference numbers.
- External transaction identifiers.
- Organization registration numbers.

A unique index should represent a genuine business rule rather than an arbitrary assumption that a column must be unique.

## 5. Composite Unique Indexes

A composite unique index enforces uniqueness across multiple columns.

Example:

    CREATE UNIQUE INDEX uq_tenant_username
    ON accounts (tenant_id, username);

The combination must be unique, but individual values do not need to be globally unique.

| Tenant ID | Username | Result |
|---:|---|---|
| 10 | alice | Accepted |
| 20 | alice | Accepted |
| 10 | bob | Accepted |
| 10 | alice | Rejected |

The first two records are valid because their tenant identifiers differ.

This is particularly useful in multi-tenant systems.

### 5.1 Column ordering

For a composite B-tree index on `(tenant_id, username)`, the index is particularly useful for:

- Filtering by `tenant_id`.
- Filtering by both `tenant_id` and `username`.
- Ordering qualifying records by the indexed key sequence.

It is generally less suitable for queries filtering only on `username`.

Index column order should reflect the expected query workload as well as the uniqueness requirement.

A unique index on `(tenant_id, username)` does not enforce uniqueness of `username` across the entire table.

## 6. Expression-Based Unique Indexes

Expression-based unique indexes enforce uniqueness over computed values rather than directly over the original column representation.

This is useful when different textual representations should be treated as equivalent.

Consider:

- `Alice@example.com`
- `alice@example.com`
- ` ALICE@example.com `

A conventional case-sensitive index can treat these values as different.

An expression-based index can normalize the values before enforcing uniqueness.

PostgreSQL example:

    CREATE UNIQUE INDEX uq_normalized_email
    ON accounts (lower(btrim(email)));

The indexed expression:

- Removes surrounding whitespace.
- Converts characters to lowercase.
- Produces a normalized value for uniqueness comparison.

The database rejects records that produce the same normalized result.

### 6.1 Why expression indexes matter

Without normalization, applications may enforce inconsistent rules.

One application might lowercase email addresses before insertion, while another might preserve their original case.

A database expression index centralizes the rule.

Expression indexes can also support:

- Normalized telephone numbers.
- Case-insensitive identifiers.
- Standardized product codes.
- Derived business keys.
- Domain-specific canonical representations.

Expression definitions must be deterministic and compatible with PostgreSQL's index requirements.

Collation and locale rules can affect comparisons. Unicode normalization and case conversion require particular care when applications operate across different languages.

## 7. Case-Insensitive Uniqueness

Case-insensitive uniqueness is a common requirement for usernames, email addresses and other identifiers.

There are several implementation approaches:

| Approach | Mechanism |
|---|---|
| `lower()` expression index | Stores and compares normalized expression keys |
| `citext` | Provides a case-insensitive text type |
| Appropriate collation | Uses configured comparison behavior |
| Application normalization | Transforms values before insertion |

For example:

    CREATE UNIQUE INDEX uq_username_lower
    ON users (lower(username));

This enforces uniqueness according to the indexed lowercase expression.

A normalization strategy should be consistent across insertion, updates, lookup and application validation.

Case-insensitive comparison does not automatically solve every Unicode-equivalence problem.

## 8. Partial Unique Indexes

A partial unique index includes only rows satisfying a specified predicate.

Example:

    CREATE UNIQUE INDEX uq_active_email
    ON accounts (lower(email))
    WHERE status = 'ACTIVE';

This enforces email uniqueness only among active accounts.

Consider:

| Account | Email | Status |
|---|---|---|
| 1 | alice@example.com | ACTIVE |
| 2 | alice@example.com | INACTIVE |
| 3 | bob@example.com | ACTIVE |

The records are permitted because only one account with the normalized email is active.

The inactive account is not represented in the partial index.

### 8.1 Practical applications

Partial unique indexes are useful for:

- Active user registrations.
- Current subscriptions.
- Unexpired reservations.
- Current assignments.
- Non-deleted business records.
- One active configuration per organization.

They can reduce index size when only a subset of records participates in uniqueness enforcement.

A critical distinction is that a partial unique index does not enforce global uniqueness outside its predicate.

Changing a row's status can add or remove its index entry.

Consequently, state transitions can cause uniqueness violations.

## 9. NULL Semantics

NULL represents an unknown or absent value.

It does not behave like an ordinary value in SQL comparisons.

PostgreSQL supports two important uniqueness behaviors.

### 9.1 NULLS DISTINCT

By default, PostgreSQL unique constraints and indexes use `NULLS DISTINCT` behavior.

Multiple NULL values are permitted because NULL values are considered distinct for this uniqueness rule.

Example:

    CREATE TABLE contacts (
        contact_id BIGINT PRIMARY KEY,
        external_reference TEXT UNIQUE
    );

Multiple records can contain NULL in `external_reference`.

### 9.2 NULLS NOT DISTINCT

PostgreSQL also supports `NULLS NOT DISTINCT`.

Example:

    CREATE TABLE identifiers (
        identifier_id BIGINT PRIMARY KEY,
        identifier_code TEXT,
        CONSTRAINT uq_identifier
            UNIQUE NULLS NOT DISTINCT (identifier_code)
    );

Only one NULL value is permitted.

This behavior is useful when the business rule treats missing values as one shared unique state.

### 9.3 Important distinction

A NULL-handling decision must be explicit.

It should reflect whether the absence of a value represents:

- An independent unknown value for each record.
- A single shared missing-value category.

The appropriate rule depends on the domain.

## 10. Index-Backed Constraint Enforcement

A unique constraint is not normally implemented as a repeated full-table scan.

PostgreSQL uses an associated unique index to enforce the restriction.

This provides an efficient mechanism for checking duplicate keys.

For example:

    ALTER TABLE accounts
    ADD CONSTRAINT uq_account_reference
    UNIQUE (account_reference);

PostgreSQL creates the supporting unique index.

The index participates in insert and update operations.

When a transaction attempts to introduce a conflicting key, PostgreSQL coordinates the uniqueness check with concurrent transactions.

This is essential because two transactions might simultaneously attempt to insert the same value.

### 10.1 Why application-level checks are insufficient

Consider this application workflow:

1. Application A checks whether an email exists.
2. Application B checks whether the same email exists.
3. Both queries report that the email is available.
4. Application A inserts the email.
5. Application B attempts the same insertion.

Both applications can pass the preliminary availability check.

Only database-level uniqueness enforcement reliably protects the invariant across concurrent transactions.

An application-level precheck improves user experience, but it must not replace the unique index.

## 11. Concurrent Transactions and Uniqueness

A unique index must remain correct when multiple transactions modify the same indexed key.

Consider two transactions attempting to register the same email.

    Transaction A              Transaction B
    ------------------------------------------------
    INSERT email=X
                               INSERT email=X
    Unique key acquired
                               Waits or encounters conflict
    COMMIT
                               Duplicate rejected

The exact locking and waiting behavior depends on transaction state and execution timing.

PostgreSQL coordinates index-level uniqueness checks so that conflicting committed records cannot coexist.

Applications must handle SQLSTATE `23505`, which identifies a unique-violation error.

Possible application responses include:

- Returning a duplicate-registration error.
- Asking the user to choose another identifier.
- Updating an existing record through an appropriate upsert.
- Retrying only when the operation's semantics make retrying valid.

Blindly retrying a permanent uniqueness violation does not solve the conflict.

## 12. Deferrable Unique Constraints

Some workflows temporarily create duplicate keys while transforming data into a valid final state.

PostgreSQL supports deferrable unique constraints.

Example:

    CONSTRAINT uq_item_position
        UNIQUE (list_id, position)
        DEFERRABLE INITIALLY IMMEDIATE

A transaction can defer the constraint:

    SET CONSTRAINTS uq_item_position DEFERRED;

This postpones enforcement until the relevant constraint-checking point, normally transaction commit.

### 12.1 Position swapping

Suppose a list contains:

| Item | Position |
|---|---:|
| A | 1 |
| B | 2 |
| C | 3 |

Swapping positions directly may temporarily produce duplicate positions.

A deferred unique constraint allows temporary duplicates inside the transaction if the final transaction state is valid.

The constraint must still be satisfied when it is checked.

Standalone unique indexes do not provide the same deferrable behavior.

## 13. Index Maintenance During Data Changes

Unique indexes are maintained during relevant table modifications.

### INSERT

The database checks the proposed key before accepting the new row.

### UPDATE

If an indexed value changes, the database checks the new key and maintains the relevant index entries.

Updating an unrelated column might not require a new logical index key, although physical storage and MVCC maintenance still apply.

### DELETE

The deleted row's index entry becomes obsolete and is cleaned up according to PostgreSQL's MVCC and vacuum mechanisms.

### Partial index transitions

When a record enters or leaves a partial-index predicate, its membership changes.

For example:

    UPDATE accounts
    SET status = 'INACTIVE'
    WHERE account_id = 101;

The record no longer participates in an index defined with `WHERE status = 'ACTIVE'`.

Changing it back to ACTIVE can fail if another active record already owns the same indexed key.

## 14. Handling Conflicts with ON CONFLICT

PostgreSQL provides `INSERT ... ON CONFLICT` for conflict-aware insertion.

### 14.1 Ignore conflicts

    INSERT INTO accounts (email)
    VALUES ('alice@example.com')
    ON CONFLICT DO NOTHING;

This skips insertion when a relevant unique or exclusion conflict occurs.

### 14.2 Update existing records

    INSERT INTO accounts (email, username)
    VALUES ('alice@example.com', 'alice')
    ON CONFLICT (email)
    DO UPDATE
    SET username = EXCLUDED.username;

The `EXCLUDED` reference identifies the proposed insertion row.

For expression-based indexes, PostgreSQL supports index inference using the corresponding expression.

For partial indexes, the inference predicate must be compatible with the index definition.

Conflict handling must preserve the intended business semantics. Ignoring every conflict can conceal unrelated data-quality problems.

## 15. PostgreSQL Implementation

The PostgreSQL deliverable creates the `unique_index_lab` schema.

Its principal entities are:

| Table | Purpose |
|---|---|
| `tenants` | Stores organizations or tenant boundaries |
| `accounts` | Stores account information and status |
| `contact_methods` | Demonstrates nullable unique references |
| `optional_identifiers` | Demonstrates NULLS NOT DISTINCT |
| `ordered_items` | Demonstrates deferrable uniqueness |
| `employee_directory` | Demonstrates expression-based uniqueness |

The database implements:

- Primary keys.
- Foreign keys.
- Composite unique constraints.
- Standalone unique expression indexes.
- Partial unique indexes.
- Supporting retrieval indexes.
- NULL uniqueness rules.
- Deferrable constraints.
- Conflict-aware inserts.
- Stored functions.
- A stored procedure.
- A reporting view.
- Query-plan inspection.
- Transactional failure handling.

### 15.1 Index inspection

PostgreSQL exposes index information through system catalogs.

The script uses:

- `pg_index` for index metadata.
- `pg_class` for index and table relations.
- `pg_namespace` for schema information.
- `pg_indexes` for index definitions.
- `information_schema.table_constraints` for relational constraints.

These catalogs help administrators distinguish constraint-backed indexes from standalone indexes and inspect their validity.

## 16. Python Implementation

The Python implementation presents two complementary models.

### 16.1 In-memory unique-index simulation

The `UniqueIndex` class maintains a dictionary mapping indexed keys to record identifiers.

The `UserRegistry` class coordinates three uniqueness rules:

| Index | Indexed key | Rule |
|---|---|---|
| `uq_users_email` | Normalized email | Globally unique |
| `uq_users_tenant_username` | Tenant and normalized username | Unique within a tenant |
| `uq_active_users_email` | Normalized email | Unique among active users |

The registry validates every index before modifying its state.

This prevents a failed insertion from partially updating the in-memory indexes.

The `audit()` operation reconstructs the indexes and compares their contents with the existing structures.

### 16.2 SQLite implementation

The second implementation uses an actual relational database.

It creates:

- A global case-insensitive email index.
- A composite tenant-username index.
- A partial active-email index.
- A normalized email expression index.

It also demonstrates expected integrity errors and state transitions.

The SQLite implementation provides an executable example of real database-enforced uniqueness rather than relying exclusively on an application-level simulation.

## 17. JavaScript Implementation

The JavaScript implementation uses Node.js event-driven programming.

Its principal components are:

| Component | Responsibility |
|---|---|
| `UniqueIndex` | Maintains indexed keys using `Map` |
| `Repository` | Coordinates records and index updates |
| `UniqueViolation` | Represents duplicate-key failures |
| `ValidationError` | Represents invalid input |
| `EventEmitter` | Publishes insertion, update and conflict events |

The implementation uses JSON serialization to create unambiguous composite keys.

The repository performs validation before modifying its maps.

Its asynchronous demonstration uses `Promise.all()` to submit competing insertion attempts.

JavaScript's synchronous execution between asynchronous suspension points makes each insertion operation atomic within this single-process in-memory model.

This is not a substitute for database concurrency control in a distributed or multi-process application.

A production service must delegate cross-process uniqueness enforcement to a shared transactional database.

## 18. C++17 Implementation

The C++ implementation uses STL containers to demonstrate different index structures.

| Structure | Purpose |
|---|---|
| `unordered_map` | Global email index |
| `map` | Composite tenant-username index |
| `unordered_map` | Partial active-email index |
| `unordered_map` | Primary record storage |

The `CompositeKey` structure defines lexicographic ordering for the composite index.

The repository validates all index keys before inserting a record.

It also supports updates that change an account's active status.

This demonstrates how partial-index membership is affected by record-state transitions.

The implementation uses exception-based failure handling to distinguish duplicate keys from invalid input.

Its `audit()` method reconstructs the index contents and checks whether the maintained structures match the stored records.

The implementation is an in-memory model. It does not provide the transactional isolation or concurrency guarantees of a production database.

## 19. Java 17 Implementation

The Java implementation models uniqueness as an enterprise repository service.

It introduces:

- Immutable account records.
- An `IndexKind` enumeration.
- Immutable composite index keys.
- Configurable index key extractors.
- Predicate-based partial-index membership.
- Explicit validation.
- Custom domain exceptions.
- Index snapshots and integrity auditing.

The `UniqueIndex` abstraction separates key extraction from membership rules.

This allows different uniqueness policies to use a common enforcement mechanism.

The repository maintains independent indexes for:

1. Normalized email addresses.
2. Tenant-specific usernames.
3. Active-account email addresses.

The implementation distinguishes domain validation from uniqueness violations.

This is important in enterprise applications because invalid input and business-key conflicts require different handling.

The immutable record model also makes state transitions explicit.

As with the other in-memory implementations, a production Java service must use database-backed uniqueness to coordinate multiple application instances.

## 20. Performance Considerations

Unique indexes improve lookup performance but introduce write and storage overhead.

| Operation | Typical indexed behavior |
|---|---|
| Equality lookup | Approximately O(log n) for a B-tree |
| B-tree insertion | Approximately O(log n), excluding concurrency and maintenance costs |
| Duplicate detection | Performed through index lookup |
| Index deletion maintenance | Requires index maintenance and MVCC cleanup |
| Full index audit | Generally O(n), depending on implementation |
| Hash-map lookup | Expected O(1) in the in-memory examples |

These are general complexity descriptions, not guaranteed execution times.

Actual performance depends on:

- Index size.
- Tree height.
- Cache hit rate.
- Data distribution.
- Row width.
- Page splits.
- Transaction contention.
- Storage characteristics.
- Vacuum activity.
- Write volume.

### 20.1 Write amplification

Every maintained index introduces additional write work.

An INSERT may need to update several indexes.

An UPDATE that changes indexed values can require removal or insertion of index entries.

Excessive indexes increase:

- Storage consumption.
- Write latency.
- WAL generation.
- Maintenance requirements.
- Vacuum workload.

Indexes should be justified by integrity requirements or measured query workloads.

### 20.2 Composite index selection

A composite index should be designed around both the uniqueness rule and the application's query patterns.

For example, `(tenant_id, username)` supports tenant-scoped lookups efficiently.

An additional index on `username` should only be created if independent username searches justify its maintenance cost.

## 21. Security and Data Integrity

Unique indexes protect business identifiers against accidental or concurrent duplication.

They do not replace other security mechanisms.

Important considerations include:

- Restricting permission to modify database schemas.
- Preventing untrusted users from creating or dropping indexes.
- Using parameterized SQL statements.
- Validating user input.
- Restricting administrative privileges.
- Avoiding disclosure of sensitive existing records through duplicate-error messages.
- Applying tenant authorization independently of tenant-scoped uniqueness.
- Auditing schema changes.
- Monitoring index validity and database health.

A tenant-scoped unique index does not prevent an unauthorized user from reading another tenant's records.

Uniqueness and access control solve different problems.

## 22. Deployment and Operational Considerations

Creating a unique index on an existing table requires the existing data to satisfy the proposed uniqueness rule.

If duplicate records already exist, index creation can fail.

A practical deployment sequence is:

1. Define the intended normalization and NULL rules.
2. Identify existing duplicate groups.
3. Resolve conflicting records.
4. Create the unique constraint or index.
5. Validate its definition and validity.
6. Deploy application handling for SQLSTATE `23505`.
7. Monitor write performance and index growth.

### 22.1 Concurrent index creation

PostgreSQL supports concurrent index creation:

    CREATE UNIQUE INDEX CONCURRENTLY uq_customer_email
    ON customers (lower(btrim(email)));

This can reduce the impact of index construction on normal table writes.

It has operational restrictions:

- It cannot execute inside a transaction block.
- It performs multiple phases.
- Concurrent modifications must be considered.
- A failed build can leave an invalid index requiring inspection and cleanup.

A failed concurrent unique-index build must not be assumed to have created a usable integrity guarantee.

### 22.2 Existing duplicate data

Before deploying uniqueness enforcement, identify duplicate groups.

For a normalized email:

    SELECT lower(btrim(email)), COUNT(*)
    FROM accounts
    GROUP BY lower(btrim(email))
    HAVING COUNT(*) > 1;

The query identifies conflicting values according to the intended normalization expression.

The cleanup process must preserve legitimate business records and should not arbitrarily delete duplicates.

## 23. Limitations and Design Trade-offs

| Mechanism | Limitation |
|---|---|
| Single-column unique index | Cannot enforce multi-column business identity |
| Composite unique index | Uniqueness applies to the complete key |
| Expression index | Queries must use compatible expressions for effective index use |
| Partial unique index | Enforces uniqueness only for qualifying rows |
| NULLS DISTINCT | Permits multiple NULL values |
| NULLS NOT DISTINCT | Treats NULL as one shared unique value |
| Application precheck | Cannot independently prevent concurrent duplicate insertion |
| Multiple indexes | Increase write and storage overhead |
| In-memory simulation | Does not provide database transaction isolation |

A uniqueness rule must be designed from the underlying business invariant.

Choosing an index merely because it improves query speed can lead to incorrect data restrictions.

Likewise, an application-level uniqueness check cannot replace a database-level constraint when the invariant must hold across concurrent writers.

## 24. Practical Distinctions

The following distinctions are central to designing reliable database systems:

| Concept | Meaning |
|---|---|
| Primary key | Identifies a row and requires non-null values |
| Unique constraint | Declares a relational uniqueness rule |
| Unique index | Enforces uniqueness through an index structure |
| Composite uniqueness | Enforces uniqueness across a combination of values |
| Expression uniqueness | Enforces uniqueness over computed values |
| Partial uniqueness | Enforces uniqueness over rows satisfying a predicate |
| NULLS DISTINCT | Permits multiple NULL values |
| NULLS NOT DISTINCT | Permits at most one NULL value for the unique key |
| Deferrable uniqueness | Allows checking to be postponed within a transaction |
| ON CONFLICT | Provides explicit handling for supported uniqueness conflicts |

A reliable database design separates business identity, query optimization, transactional correctness and application-level validation.

Unique indexes provide the database-level mechanism that makes critical uniqueness rules enforceable even when several independent application processes operate on the same data.
