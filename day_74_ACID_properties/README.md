# ACID Properties in Database Management Systems

## 1. Technical Overview

ACID represents four fundamental properties that define reliable database transactions:

- **Atomicity:** A transaction is completed entirely or not applied.
- **Consistency:** Every committed transaction preserves database rules and invariants.
- **Isolation:** Concurrent transactions behave according to their selected isolation guarantees.
- **Durability:** Committed changes survive subsequent failures, subject to the database's durability configuration.

These properties address different failure categories. They work together to ensure that database operations remain correct when applications encounter errors, multiple users access shared data, or systems experience unexpected interruptions.

The implementations in this project use a financial account-transfer workflow. Transferring money between two accounts provides a practical example because both account balances must change consistently.

## 2. Transaction Fundamentals

A transaction is a logical unit of database work.

Consider a transfer of ₹2,000 from Alice's account to Bob's account.

Initial state:

| Account | Initial balance |
|---|---:|
| Alice | ₹10,000 |
| Bob | ₹5,000 |
| Total | ₹15,000 |

Expected committed state:

| Account | Final balance |
|---|---:|
| Alice | ₹8,000 |
| Bob | ₹7,000 |
| Total | ₹15,000 |

Two database operations are required:

1. Debit Alice's account by ₹2,000.
2. Credit Bob's account by ₹2,000.

If the debit succeeds but the credit fails, the database must not retain the partial operation.

The required transaction boundary is:

`BEGIN → VALIDATE → UPDATE SOURCE → UPDATE TARGET → COMMIT`

If an operation fails:

`BEGIN → VALIDATE → UPDATE SOURCE → FAILURE → ROLLBACK`

The transaction boundary separates temporary changes from committed database state.

### Transaction lifecycle

| State | Meaning |
|---|---|
| Active | Transaction operations are being executed |
| Committed | All permitted changes have been accepted |
| Rolled back | Changes have been discarded |
| Failed | Transaction execution or commit has failed |

A failed transaction must not be treated as successfully committed.

---

## 3. Atomicity

### Definition

Atomicity guarantees that all operations belonging to a transaction succeed together or that none of their changes become committed.

It is commonly described as the all-or-nothing property.

### Problem addressed

Consider the following sequence:

1. Alice has ₹10,000.
2. Bob has ₹5,000.
3. Alice is debited by ₹2,000.
4. The application crashes before Bob is credited.

Without atomicity, the resulting balances would be incorrect.

Atomicity prevents this partial state from becoming a committed result.

### Mechanisms

Relational databases implement atomicity through transaction management.

Important mechanisms include:

- `BEGIN`
- `COMMIT`
- `ROLLBACK`
- Transaction logs
- Undo information
- Savepoints
- Subtransactions

A rollback discards uncommitted changes within the relevant transaction boundary.

A savepoint provides an intermediate rollback position without necessarily abandoning the entire transaction.

### Implementation

The Python implementation stages account changes in a write set before committing them.

The C++ implementation uses a projected account state and applies updates only after validation.

The Java implementation coordinates staged writes through a transaction service.

The JavaScript implementation uses a Promise-based commit operation and a shared commit mutex.

PostgreSQL provides native transactional execution. The transfer function updates both accounts, inserts ledger entries, and changes the transaction status within one database transaction.

### Failure scenario

| Operation | Result |
|---|---|
| Debit Alice | Executed |
| Credit Bob | Fails |
| Transaction | Rolled back |
| Alice's committed balance | Unchanged |
| Bob's committed balance | Unchanged |

### Savepoints

Savepoints are useful when an application performs several optional operations.

Example workflow:

`BEGIN → UPDATE A → SAVEPOINT S1 → UPDATE B → ROLLBACK TO S1 → COMMIT`

The changes before the savepoint remain eligible for commitment.

Savepoints do not create independently durable transactions.

### Important distinction

Atomicity concerns the outcome of one transaction. It does not automatically guarantee that multiple separate transactions succeed together.

For example, two independent database transactions require an additional coordination mechanism if they must behave as one business operation.

---

## 4. Consistency

### Definition

Consistency ensures that every committed transaction preserves defined database constraints and business invariants.

A database moves from one valid state to another valid state.

Consistency is not simply the absence of SQL errors. It depends on correctly defined rules.

### Database constraints

The PostgreSQL implementation defines several integrity mechanisms.

| Mechanism | Purpose |
|---|---|
| PRIMARY KEY | Uniquely identifies each record |
| FOREIGN KEY | Enforces valid relationships |
| UNIQUE | Prevents duplicate identifiers |
| NOT NULL | Requires a value |
| CHECK | Enforces permitted values |
| TRIGGER | Applies additional validation or auditing |

Examples include:

- An account balance cannot be negative.
- An account must reference an existing customer.
- A transaction amount must be positive.
- A transaction identifier must be unique.
- A transfer cannot use the same source and destination account.

### Business invariants

A financial transaction may require more than structural database constraints.

The following invariant is used in the implementations:

`Total funds before transfer = Total funds after transfer`

For a transfer:

\[
B_{source}^{new}=B_{source}^{old}-A
\]

\[
B_{target}^{new}=B_{target}^{old}+A
\]

Therefore:

\[
B_{source}^{new}+B_{target}^{new}
=
B_{source}^{old}+B_{target}^{old}
\]

Where:

- \(B\) represents an account balance.
- \(A\) represents the transfer amount.

Additional invariants include:

- Both accounts must be active.
- Both accounts must use the same currency.
- The source account must have sufficient funds.
- The destination balance must not exceed its permitted precision.
- Each transaction must have a valid identity and status.

### Double-entry accounting

The PostgreSQL implementation uses transaction entries to record debit and credit movements.

For a transfer of ₹2,000:

| Account | Entry | Amount |
|---|---|---:|
| Alice | Debit | ₹2,000 |
| Bob | Credit | ₹2,000 |

The net movement is:

\[
\sum Credits-\sum Debits=0
\]

This provides a useful accounting consistency check.

### Implementation decisions

Python uses `Decimal` to avoid binary floating-point errors in monetary calculations.

JavaScript uses safe integer amounts rather than unrestricted floating-point arithmetic.

C++ uses fixed-width integer values.

Java uses `long` values with arithmetic overflow checks.

PostgreSQL uses `NUMERIC(18,2)` for monetary values.

These choices prevent avoidable precision errors in financial operations.

### Limitations

A database cannot automatically enforce every business rule merely because ACID is enabled.

Rules must be explicitly represented through constraints, transactional procedures, triggers, application validation, or a combination of these mechanisms.

Cross-system business invariants may require distributed transaction coordination.

---

## 5. Isolation

### Definition

Isolation controls how concurrent transactions interact.

When multiple users access the same records, the database must prevent unacceptable interference.

Isolation is particularly important when multiple transactions attempt to modify the same account, inventory item, reservation, or financial record.

### Concurrency problems

#### Dirty read

A transaction reads another transaction's uncommitted changes.

Example:

1. Transaction A changes Alice's balance from ₹10,000 to ₹8,000.
2. Transaction B reads ₹8,000.
3. Transaction A rolls back.
4. Transaction B has read a value that was never committed.

#### Non-repeatable read

A transaction reads the same row twice and obtains different committed values.

Example:

1. Transaction A reads ₹10,000.
2. Transaction B updates the balance to ₹8,000 and commits.
3. Transaction A reads the balance again.
4. Transaction A obtains ₹8,000.

#### Phantom read

A transaction repeats a query and obtains a different set of matching rows because another transaction inserted or deleted qualifying records.

Example:

1. Transaction A counts active accounts with balances above ₹5,000.
2. Transaction B inserts another qualifying account.
3. Transaction B commits.
4. Transaction A repeats its query and obtains a different count.

#### Lost update

Two transactions read the same initial value and independently calculate replacements.

Example:

1. Initial balance: ₹10,000.
2. Transaction A calculates ₹9,000.
3. Transaction B calculates ₹8,000.
4. Both attempt to write their results.

If concurrency is not controlled correctly, one update can overwrite the other.

### Isolation levels

| Isolation level | Dirty reads | Non-repeatable reads | Phantom reads |
|---|---|---|---|
| Read Uncommitted | Possible in some DBMS implementations | Possible | Possible |
| Read Committed | Prevented | Possible | Possible |
| Repeatable Read | Prevented | Prevented | DBMS-dependent |
| Serializable | Prevented | Prevented | Prevented through serializable execution guarantees |

PostgreSQL implements Read Uncommitted with behavior equivalent to Read Committed.

PostgreSQL Repeatable Read uses a transaction-level snapshot and prevents ordinary non-repeatable reads and phantom reads. Serialization anomalies may still be possible.

Serializable provides the strongest standard isolation guarantee, although transactions can be aborted when concurrent execution cannot be serialized safely.

### Concurrency control mechanisms

**Pessimistic locking**

The database locks records to prevent conflicting modifications.

PostgreSQL supports:

- `SELECT FOR UPDATE`
- `SELECT FOR NO KEY UPDATE`
- `LOCK TABLE`

The PostgreSQL transfer function locks affected account rows in ascending account-ID order.

This reduces the risk of deadlocks caused by inconsistent lock acquisition order.

**Optimistic concurrency control**

Transactions proceed using observed record versions.

Before committing, the application checks whether the records have changed.

If a version differs from the version originally observed, the transaction is rejected.

Python, C++, Java, and JavaScript implement version-based conflict detection.

**MVCC**

Multi-Version Concurrency Control maintains multiple versions of records.

Readers can access an appropriate snapshot while writers create new versions.

PostgreSQL uses MVCC as a central component of its concurrency architecture.

### Deadlocks

A deadlock occurs when transactions wait for resources held by one another.

Example:

- Transaction A locks account 1 and waits for account 2.
- Transaction B locks account 2 and waits for account 1.

The database may detect and abort one transaction.

Practical prevention techniques include:

- Acquiring locks in a consistent order.
- Keeping transactions short.
- Avoiding unnecessary locks.
- Using appropriate indexes.
- Retrying recoverable transaction failures.

### Implementation distinctions

| Implementation | Isolation mechanism |
|---|---|
| Python | Account locks and version validation |
| JavaScript | Serialized commit coordination and optimistic validation |
| C++17 | Mutex-protected commit and version validation |
| Java 17 | Fair commit lock and version-based validation |
| PostgreSQL | MVCC, row-level locking and transaction isolation |

The programming-language implementations are educational transaction simulators. Their isolation behavior is not a complete replacement for a production database's concurrency-control implementation.

---

## 6. Durability

### Definition

Durability guarantees that successfully committed changes survive subsequent failures.

Once a database confirms a durable commit, the transaction should not disappear because the application terminates or the database process restarts.

### Failure scenarios

Durability addresses situations such as:

- Application crashes.
- Database process termination.
- Operating-system failures.
- Unexpected server restarts.
- Power interruptions.
- Storage failures, subject to the configured redundancy and recovery mechanisms.

### Write-Ahead Logging

PostgreSQL uses Write-Ahead Logging (WAL).

The central principle is that relevant log records must be written to durable storage before modified data pages are required to be persisted.

The WAL allows PostgreSQL to recover committed changes following a crash.

Simplified workflow:

`TRANSACTION → WAL RECORDS → WAL FLUSH → COMMIT CONFIRMATION`

Data pages can be written later because the WAL provides the recovery information.

### Commit configuration

PostgreSQL durability behavior depends on configuration.

Important settings include:

| Setting | Purpose |
|---|---|
| `fsync` | Requests synchronization of database files to durable storage |
| `synchronous_commit` | Controls when commit acknowledgment waits for WAL flushing |
| `full_page_writes` | Helps protect against partial page writes |
| `wal_level` | Determines the amount of information written to WAL |

For local durable commits, `fsync` and an appropriate `synchronous_commit` setting are important.

Synchronous replication can provide stronger guarantees against primary-server loss, depending on its configuration and acknowledgment requirements.

### Recovery

The Python implementation maintains a journal and reconstructs committed account changes when the application restarts.

The JavaScript implementation uses an append-only JSON journal with atomic file replacement.

The C++ implementation maintains an in-memory commit journal to demonstrate transaction-record creation. It does not provide crash-resistant storage.

The Java implementation defines a journal interface and an in-memory implementation to demonstrate separation between transaction processing and persistence.

PostgreSQL uses its actual database recovery infrastructure rather than the application's business audit table.

### Durability limitations

An in-memory list is not durable storage.

A successful file write is not automatically equivalent to a production-grade database commit.

Atomic file replacement does not, by itself, guarantee protection against every storage failure.

Production systems require appropriate synchronization, storage guarantees, recovery procedures, backups, and monitoring.

---

## 7. ACID Properties: How They Work Together

The four properties address separate but related responsibilities.

| Property | Main question | Primary mechanism |
|---|---|---|
| Atomicity | Did every operation succeed together? | Commit and rollback |
| Consistency | Are database rules preserved? | Constraints and validation |
| Isolation | Can concurrent work interfere incorrectly? | MVCC, locks and conflict detection |
| Durability | Will committed changes survive failure? | WAL and durable storage |

Consider two users transferring funds simultaneously.

1. Atomicity ensures that neither transfer publishes partial account changes.
2. Consistency ensures that balances remain valid and funds are conserved.
3. Isolation controls conflicting updates and concurrent observations.
4. Durability preserves transactions after successful commitment.

A transaction can satisfy three properties while still failing the fourth. For example, a transaction may execute correctly and preserve its invariants but lose its changes if the storage system does not provide the required durability guarantees.

ACID is therefore a combined reliability model, not four interchangeable names for transaction processing.

---

## 8. Implementation Architecture

The five source files use a common account-transfer domain while demonstrating different engineering approaches.

### Python

**File:** `acid_properties.py`

The Python implementation uses:

- Dataclasses for account and journal records.
- Enumerations for transaction states and isolation levels.
- Decimal arithmetic for financial values.
- Dictionaries for account storage and transaction write sets.
- Context managers for transaction lifecycle handling.
- Reentrant locks for account synchronization.
- Exceptions for constraint and concurrency failures.
- JSON-based journal persistence.

The `Database` class manages accounts and transaction creation.

The `Transaction` class maintains staged writes and observed versions.

The `DurableJournal` class records committed transactions.

The context-manager interface makes successful execution and rollback behavior explicit.

The script also verifies the total balance using an assertion.

**Important limitation:** The Python recovery demonstration does not persist initial account creation. The journal reconstructs updates only when the required base account state already exists. It is a transaction-mechanism demonstration, not a complete persistent banking database.

### JavaScript

**File:** `acid_properties.js`

The JavaScript implementation emphasizes asynchronous execution and event-driven transaction processing.

Its main components are:

| Component | Responsibility |
|---|---|
| `AsyncMutex` | Serializes commit operations |
| `DurableJournal` | Persists transaction records |
| `AccountLedger` | Maintains accounts and observers |
| `LedgerTransaction` | Stages and commits changes |

Promises provide asynchronous commit coordination.

A `Map` maintains account and idempotency-key state.

A `Set` maintains event listeners.

The commit event is emitted after the transaction has been persisted and published.

Listener errors are isolated from transaction success. A notification failure must not reverse an already committed transaction.

Idempotency keys prevent duplicate processing within the running ledger.

The JavaScript journal is an educational local-file implementation. Production systems should use transactional storage with atomic business-state updates and durable idempotency records.

### C++17

**File:** `acid_properties.cpp`

The C++ implementation emphasizes explicit domain modeling and controlled state publication.

Its main types are:

- `Account`
- `Operation`
- `JournalRecord`
- `Transaction`
- `GovernanceEngine`

The engine uses:

- `std::map` for account state.
- `std::vector` for journal entries.
- `std::mutex` for commit coordination.
- Fixed-width integer values for financial calculations.
- Custom exceptions for business and concurrency failures.

A transaction stages its changes before calling the engine's commit method.

The engine validates observed versions, checks projected balances, verifies the global invariant, records the transaction, and publishes the updated state.

The demonstration includes an optimistic concurrency conflict involving two transactions that read the same account version.

**Important limitation:** The journal is in memory and does not survive process termination. The mutex protects operations performed through the engine's controlled interface. The example is not a complete multithreaded database implementation.

### Java 17

**File:** `AcidProperties.java`

The Java implementation models enterprise transaction services.

It uses:

- Records for immutable snapshots and transaction commands.
- Interfaces for journal and account-policy contracts.
- Enums for transaction state, operation types and isolation levels.
- Collections for staged writes and account management.
- A fair `ReentrantLock` for commit coordination.
- Custom exceptions for business, persistence and concurrency failures.

`TransactionService` is responsible for validating and coordinating commits.

`AccountPolicy` separates account validation from transaction processing.

`Journal` separates persistence behavior from the business service.

This structure allows transaction processing to use different journal implementations without changing the core transaction model.

The demonstration covers successful transactions, insufficient funds, concurrent modifications and journal failure.

**Important limitation:** The provided journal is an in-memory implementation. Its interface demonstrates an enterprise-oriented persistence boundary rather than actual disk durability.

---

## 9. PostgreSQL Database Architecture

**File:** `acid_properties.sql`

The PostgreSQL implementation provides a relational transaction workflow.

### Entity relationships

`Customers → Accounts → Transactions → Transaction Entries`

Supporting entities:

- Application users
- Application roles
- Transaction audit records
- Idempotency registry
- Isolation test records

### Table responsibilities

| Table | Responsibility |
|---|---|
| `customers` | Customer identity and contact information |
| `accounts` | Account balances and version numbers |
| `app_roles` | Application role definitions |
| `application_users` | Authorized application identities |
| `transactions` | Business transaction lifecycle |
| `transaction_entries` | Debit and credit movements |
| `transaction_audit` | Transaction status history |
| `idempotency_registry` | Duplicate-request prevention |
| `isolation_test_records` | Isolation experiments |
| `database_settings` | Transaction and savepoint demonstrations |

### Transaction execution

The `execute_transfer` function performs the following operations:

1. Validates the transfer amount.
2. Validates the idempotency key.
3. Registers the request key.
4. Acquires account row locks in a consistent order.
5. Retrieves the latest committed account state.
6. Checks account status and currency.
7. Verifies sufficient funds.
8. Inserts a pending transaction.
9. Updates both account balances.
10. Inserts debit and credit entries.
11. Marks the transaction committed.
12. Associates the idempotency key with the transaction.

The entire operation executes within the caller's PostgreSQL transaction.

If an exception occurs, the affected transaction changes are rolled back.

### Idempotency

An idempotency key uniquely identifies a business request.

If an application retries a request after an uncertain network response, it should not create a second transfer.

The implementation uses a unique registry key to serialize competing requests and return the existing transaction identifier for repeated requests.

Idempotency is particularly important in payment processing, API retries and distributed application workflows.

### Auditability

The status-audit trigger records transaction state transitions.

The transaction-entry table preserves account-level movements.

These records support operational investigation and financial reconciliation.

The audit table is a business audit mechanism. It is separate from PostgreSQL's internal WAL.

### Access control

The SQL script creates two database roles:

- `acid_application`
- `acid_auditor`

The application role receives permission to execute the controlled transfer function and procedure.

The auditor receives read-only access to reporting views.

In production, the database owner should restrict direct modifications to account balances and ledger records. Application access should be provided through appropriately secured database functions and narrowly scoped permissions.

---

## 10. Failure Handling and Edge Cases

A transaction system must handle more than successful requests.

| Failure condition | Expected handling |
|---|---|
| Negative transfer amount | Reject before committing |
| Zero transfer amount | Reject |
| Unknown account | Reject |
| Inactive account | Reject |
| Insufficient funds | Reject and preserve existing balances |
| Same source and target | Reject |
| Currency mismatch | Reject |
| Arithmetic overflow | Reject |
| Concurrent modification | Abort or retry transaction |
| Duplicate request | Return existing transaction result |
| Persistence failure | Do not publish new committed state |
| Invalid account balance | Reject through database or application validation |
| Deadlock | Abort a participant and retry when safe |

### Retry behavior

Serialization failures and deadlocks can be temporary.

A production application should:

1. Identify recoverable database error codes.
2. Roll back the failed transaction.
3. Apply a bounded retry policy.
4. Use exponential backoff with jitter.
5. Re-execute the entire transaction.
6. Preserve the same business idempotency key.

PostgreSQL commonly reports serialization failures using SQLSTATE `40001` and deadlocks using `40P01`.

Not every error should be retried. Invalid business input, insufficient funds and constraint violations require correction rather than automatic repetition.

---

## 11. Performance Considerations

ACID guarantees have operational costs.

| Mechanism | Performance consideration |
|---|---|
| Atomic transactions | Long transactions retain resources longer |
| Constraints | Require validation during writes |
| Indexes | Improve retrieval but increase write overhead |
| Row locks | Can reduce concurrency |
| Serializable isolation | Can introduce transaction retries |
| WAL | Requires additional sequential write activity |
| Audit records | Increase storage and write volume |
| Version checks | Require validation before publication |

### Practical optimization

- Keep transactions short.
- Use appropriate indexes for common filters.
- Avoid unnecessary full-table locking.
- Acquire multiple row locks in a consistent order.
- Use numeric monetary representations.
- Avoid unnecessary updates to frequently modified rows.
- Monitor transaction duration and lock waits.
- Use bounded retry logic.
- Review execution plans with `EXPLAIN ANALYZE`.
- Maintain regular database statistics and vacuum operations.

The PostgreSQL implementation creates indexes for account lookup, transaction status, transaction history and ledger retrieval.

Indexes should be selected according to actual query patterns. Creating unnecessary indexes can increase the cost of inserts, updates and deletes.

---

## 12. ACID and Distributed Systems

Traditional ACID transactions generally operate within a single transactional database boundary.

A business workflow involving several independent services or databases introduces additional coordination problems.

For example:

`Payment Service → Inventory Service → Shipping Service`

A successful payment followed by an inventory failure cannot always be reversed using one ordinary local database rollback.

Distributed systems may use:

- Two-phase commit.
- Distributed transaction coordinators.
- Transactional outbox patterns.
- Sagas.
- Compensating transactions.
- Idempotent message processing.

These mechanisms address coordination across separate transaction boundaries.

A compensating transaction is not the same as a database rollback. It is a new business operation that attempts to reverse the effects of an earlier committed operation.

Similarly, eventual consistency does not provide the same guarantees as a single ACID transaction.

---

## 13. Execution

### Python

- Save the source as `acid_properties.py`.
- Execute `python acid_properties.py`.
- The script creates a local JSON transaction journal.

### JavaScript

- Save the source as `acid_properties.js`.
- Execute `node acid_properties.js`.
- The script uses Node.js standard-library modules and creates a local JSON journal.

### C++17

- Save the source as `acid_properties.cpp`.
- Compile using a C++17 compiler.
- Execute the resulting program.

### Java 17

- Save the source as `AcidProperties.java`.
- Compile using `javac AcidProperties.java`.
- Execute using `java AcidProperties`.

### PostgreSQL

- Execute `acid_properties.sql` against a PostgreSQL database.
- The script creates the `acid` schema.
- The sample workflow creates customers, accounts, transactions and audit records.
- The isolation experiment requires separate database sessions.

The PostgreSQL script uses `gen_random_uuid()` for transaction references and assumes a PostgreSQL version providing that function.

---

## 14. Technical Comparison

| Capability | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Atomic staged writes | Yes | Yes | Yes | Yes | Native transactions |
| Consistency validation | Yes | Yes | Yes | Yes | Constraints and triggers |
| Optimistic version checking | Yes | Yes | Yes | Yes | Available through application logic |
| Commit coordination | Account locks | Async mutex | Mutex | ReentrantLock | Database transaction manager |
| Savepoint demonstration | Yes | No | No | No | Yes |
| Idempotency | Not implemented | Yes | No | Yes | Yes |
| Durable persistence | JSON journal | JSON journal | In-memory only | In-memory only | WAL |
| Audit records | Journal | Commit events | Commit journal | Commit journal | Audit table and trigger |
| Concurrency simulation | Yes | Yes | Yes | Yes | Native MVCC and locking |

The language implementations emphasize transaction-state management and application-side validation. PostgreSQL demonstrates actual relational transaction processing and database-level enforcement.

The comparison also highlights why an application-level transaction simulator should not be treated as a replacement for a production database.

---

## 15. Practical Applications

ACID properties are essential in systems where incorrect partial updates, inconsistent data or lost committed records have significant consequences.

| Application | Atomicity requirement | Consistency requirement | Isolation requirement | Durability requirement |
|---|---|---|---|---|
| Banking | Complete debit and credit | Valid balances | Concurrent payment control | Permanent committed records |
| E-commerce | Complete order updates | Valid inventory and totals | Concurrent stock allocation | Order persistence |
| Healthcare | Complete clinical updates | Valid patient records | Concurrent record access | Reliable clinical history |
| Inventory | Complete stock movement | Nonnegative quantities | Prevent overselling | Persistent stock changes |
| Enterprise ERP | Complete business workflows | Financial and operational rules | Shared resource coordination | Recoverable transactions |
| Reservation systems | Complete booking operation | Capacity constraints | Prevent duplicate allocation | Persistent booking records |

The most important architectural decision is to define the transaction boundary correctly. ACID can protect operations inside that boundary, but it cannot automatically make unrelated operations in external services atomic.

---

## 16. Core Terminology

| Term | Meaning |
|---|---|
| Transaction | Logical unit of database work |
| Commit | Final acceptance of transactional changes |
| Rollback | Discarding uncommitted changes |
| Savepoint | Intermediate rollback position |
| Constraint | Database rule governing valid data |
| Invariant | Condition that must remain true |
| MVCC | Multi-Version Concurrency Control |
| Dirty read | Reading uncommitted changes |
| Non-repeatable read | Different results from repeated reads of one row |
| Phantom read | Different result sets from repeated queries |
| Deadlock | Circular waiting between transactions |
| WAL | Write-Ahead Logging |
| Idempotency | Repeated execution of a request produces no additional business effect |
| Optimistic concurrency | Detecting conflicting updates through version validation |
| Pessimistic locking | Preventing conflicting operations through locks |
| Serialization failure | Rejection of a transaction that cannot be safely serialized |
| Double-entry ledger | Accounting model recording corresponding debit and credit movements |

## 17. Engineering Principles

A reliable transaction implementation should establish the following boundaries:

- Transaction processing determines which operations belong together.
- Atomicity determines whether those operations are accepted together.
- Consistency determines whether the resulting database state is valid.
- Isolation determines how concurrent transactions interact.
- Durability determines whether successful commitments survive failures.
- Application validation improves error handling but does not replace database constraints.
- Database constraints protect integrity even when multiple applications access the same database.
- Idempotency protects business operations against duplicate requests.
- Recovery mechanisms must distinguish committed transactions from incomplete operations.
- Distributed workflows require coordination beyond ordinary single-database ACID transactions.

These distinctions form the basis for designing reliable financial, enterprise and transactional database applications.
