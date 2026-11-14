# Transaction Isolation and Concurrency Control

## Technical Scope

Transaction isolation defines how concurrent database transactions observe and modify shared data.

A database transaction groups operations into a logical unit. The ACID properties describe the expected behavior:

| Property | Meaning |
|---|---|
| Atomicity | All transaction operations succeed or are rolled back. |
| Consistency | Database constraints and business invariants remain valid. |
| Isolation | Concurrent transactions follow defined visibility and concurrency rules. |
| Durability | Committed changes survive system failures according to database guarantees. |

Isolation is particularly important when multiple users modify the same records, transfer funds, update inventory, or execute transactions based on shared aggregate values.

The implementations in this repository model transaction visibility, version management, concurrent updates, conflict detection, rollback, and serial execution guarantees.

## 1. Transaction Isolation Fundamentals

A database may execute several transactions concurrently to improve throughput.

Consider two transactions operating on the same bank account:

- Transaction A reads a balance of 5,000.
- Transaction B changes the balance to 4,000.
- Transaction B commits.
- Transaction A reads the account again.

The result depends on the isolation level.

A database must determine:

- Which committed versions are visible.
- Whether repeated reads return the same values.
- Whether newly inserted rows become visible.
- Whether concurrent updates are allowed.
- Whether conflicts cause blocking or transaction failure.
- Whether the resulting execution is equivalent to a serial execution.

### Transaction anomalies

| Anomaly | Description |
|---|---|
| Dirty read | A transaction reads another transaction's uncommitted changes. |
| Non-repeatable read | Repeated reads of the same row return different committed values. |
| Phantom read | Repeating a predicate query produces a different set of rows. |
| Lost update | A concurrent modification overwrites another transaction's update. |
| Write skew | Concurrent transactions modify different rows based on a shared condition, violating a business invariant. |
| Serialization anomaly | The combined outcome cannot be explained by any valid serial execution. |

These anomalies are related but not interchangeable. Preventing non-repeatable reads does not automatically prevent write skew.

## 2. Read Uncommitted

Read Uncommitted is the weakest standard SQL isolation level.

A transaction may theoretically observe modifications made by another transaction before those modifications are committed.

### Dirty-read example

Initial balance: 5,000.

| Operation | Transaction A | Transaction B |
|---|---|---|
| 1 | | Begin |
| 2 | | Update balance to 2,000 |
| 3 | Read balance | |
| 4 | | Rollback |

If Transaction A observes 2,000, it has read a value that never became a committed database state.

This is a dirty read.

### Practical behavior

Read Uncommitted is supported conceptually by SQL isolation standards, but implementations differ.

PostgreSQL accepts the isolation-level declaration but internally treats it as Read Committed. It does not permit dirty reads.

The Python, JavaScript, C++17, Java 17, and PostgreSQL implementations demonstrate that uncommitted modifications remain invisible to other transactions.

### Important distinction

Read Uncommitted does not mean that a database disables transaction management. Atomicity and transaction boundaries remain relevant.

It describes a permitted visibility level, not an instruction to ignore database integrity.

## 3. Read Committed

Read Committed ensures that a statement reads data committed before its snapshot is established.

A transaction cannot read another transaction's uncommitted modifications.

In PostgreSQL, each statement obtains a new snapshot.

### Non-repeatable read

Initial balance: 5,000.

| Operation | Transaction A | Transaction B |
|---|---|---|
| 1 | BEGIN | |
| 2 | Read balance: 5,000 | |
| 3 | | BEGIN |
| 4 | | Update balance to 4,000 |
| 5 | | COMMIT |
| 6 | Read balance: 4,000 | |
| 7 | COMMIT | |

The two reads return different values because Transaction B committed between the statements.

### Characteristics

- Dirty reads are prevented.
- A later statement can observe newly committed changes.
- Non-repeatable reads are possible.
- Predicate queries can return different row sets.
- Concurrent writes may require locking or conflict resolution.
- The database does not guarantee a transaction-wide consistent snapshot.

### Appropriate applications

Read Committed is suitable for many ordinary application workflows:

- Reading customer account details.
- Retrieving order information.
- Updating individual records.
- Processing independent application requests.
- Reading operational dashboards where a transaction-wide snapshot is unnecessary.

For operations involving business invariants, explicit locking, atomic updates, constraints, or stronger isolation may be necessary.

## 4. Repeatable Read

Repeatable Read provides a stable transaction-level view of committed data.

A transaction continues reading from its established snapshot even when another transaction commits modifications.

### Example

Initial balance: 5,000.

| Operation | Transaction A | Transaction B |
|---|---|---|
| 1 | BEGIN REPEATABLE READ | |
| 2 | Read balance: 5,000 | |
| 3 | | BEGIN |
| 4 | | Update balance to 4,000 |
| 5 | | COMMIT |
| 6 | Read balance: 5,000 | |
| 7 | COMMIT | |

Transaction A continues to observe its original snapshot.

### Snapshot isolation

Many modern database systems implement Repeatable Read using Multi-Version Concurrency Control.

MVCC retains multiple versions of records.

A transaction selects versions according to its visibility rules instead of requiring every reader to block every writer.

This improves concurrency because readers can often continue while other transactions modify records.

### Phantom-read distinction

The precise behavior of Repeatable Read depends on the database implementation.

PostgreSQL's Repeatable Read implementation prevents phantom reads through its transaction-wide snapshot.

The SQL standard's Repeatable Read definition does not universally guarantee phantom prevention.

### Write conflicts

A transaction that attempts to update a row modified by another transaction after its snapshot may fail.

PostgreSQL can report SQLSTATE `40001` when a concurrent update makes the transaction unable to proceed.

The application should:

1. Roll back the failed transaction.
2. Start a new transaction.
3. Read the latest committed state.
4. Recalculate the operation.
5. Retry within a bounded retry policy.

### Write skew limitation

Snapshot isolation does not necessarily guarantee serializability.

Consider a hospital scheduling system with two doctors on duty.

The invariant requires at least one doctor to remain available.

Two concurrent transactions read the same state:

- Transaction A sees both doctors available and marks Doctor A unavailable.
- Transaction B sees both doctors available and marks Doctor B unavailable.

They modify separate rows.

Both transactions may commit under snapshot isolation, leaving no doctor available.

This is write skew.

The example demonstrates why a stable snapshot is not equivalent to serial execution.

## 5. Serializable

Serializable is the strongest standard SQL isolation level.

The database must ensure that concurrent transactions produce an outcome equivalent to some valid serial ordering.

A serial execution processes transactions one after another.

Serializable concurrency control permits overlapping execution when the resulting behavior remains equivalent to serial execution.

### Example

Two transactions attempt to withdraw money from accounts subject to a shared business rule.

A transaction reads the relevant records and calculates whether its operation is valid.

If concurrent execution creates an unsafe dependency, the database may reject one transaction.

The rejected transaction must be retried from a new transaction boundary.

### PostgreSQL Serializable Snapshot Isolation

PostgreSQL uses Serializable Snapshot Isolation (SSI).

SSI detects dangerous read-write dependency structures and aborts transactions when necessary to preserve serializability.

It does not simply lock every row read by every serializable transaction.

Consequently:

- Readers can often proceed concurrently with writers.
- Some transactions are aborted even when their individual SQL statements are valid.
- Applications must handle serialization failures.
- Long-running transactions can increase conflict exposure.
- Predicate dependencies are important for detecting anomalies.

### Serialization failure

PostgreSQL commonly reports serialization failures using SQLSTATE `40001`.

The correct response is to retry the complete transaction, including its reads and business calculations.

Retrying only the final failed statement is insufficient because the original decision may have been based on an obsolete snapshot.

## 6. Comparison of Isolation Levels

| Property | Read Uncommitted | Read Committed | Repeatable Read | Serializable |
|---|---|---|---|---|
| Dirty reads | Permitted by standard | Prevented | Prevented | Prevented |
| Non-repeatable reads | Possible | Possible | Prevented | Prevented |
| Phantom reads | Possible | Possible | Database-dependent | Prevented |
| Write skew | Possible | Possible | Possible | Prevented |
| Stable transaction snapshot | Not guaranteed | No | Yes in PostgreSQL | Yes in PostgreSQL |
| Serialization guarantee | No | No | Not generally | Yes |
| Conflict handling | Implementation-dependent | Implementation-dependent | Conflict detection | Serialization validation |

PostgreSQL-specific interpretation:

| Declared level | PostgreSQL behavior |
|---|---|
| READ UNCOMMITTED | READ COMMITTED |
| READ COMMITTED | Statement-level snapshots |
| REPEATABLE READ | Transaction-level snapshot isolation |
| SERIALIZABLE | Serializable Snapshot Isolation |

The comparison should not be interpreted as a universal implementation specification for every database product.

## 7. Multi-Version Concurrency Control

MVCC maintains multiple versions of database records.

A transaction determines which versions it can observe using transaction visibility information.

A simplified model is:

    Account 101
       |
       +-- Version 1: Balance 5,000
       |
       +-- Version 2: Balance 4,500
       |
       +-- Version 3: Balance 4,000

    Transaction A: Snapshot revision 1
       -> Reads Version 1

    Transaction B: Snapshot revision 3
       -> Reads Version 3

The older version may remain available while an active transaction still requires it.

### Benefits

- Readers and writers can often operate concurrently.
- Consistent snapshots are possible.
- Many read operations avoid blocking on ordinary writes.
- Historical versions support transaction visibility.

### Costs

- Additional storage for row versions.
- Vacuum or equivalent cleanup requirements.
- Longer-lived transactions retain old snapshots.
- Version management introduces implementation complexity.
- Write conflicts still require handling.

The Python, JavaScript, C++17, and Java implementations use revision numbers to model version visibility.

The PostgreSQL implementation relies on PostgreSQL's native MVCC mechanisms rather than recreating version management in application tables.

## 8. Distinguishing Visibility, Locking, and Validation

Three mechanisms must be considered separately.

| Mechanism | Responsibility |
|---|---|
| Snapshot visibility | Determines which record versions a transaction can read. |
| Locking | Coordinates conflicting access to shared database records. |
| Validation | Determines whether a transaction can safely commit. |

A snapshot does not automatically prevent all concurrent modifications.

A row lock does not automatically provide serializable execution for every business rule.

Validation does not necessarily require every concurrent transaction to be blocked before it executes.

### Pessimistic concurrency control

Pessimistic concurrency control acquires locks before performing operations that could conflict.

PostgreSQL provides `SELECT ... FOR UPDATE`.

Example workflow:

1. Identify the source and destination accounts.
2. Lock both account rows.
3. Read their current balances.
4. Validate the transfer.
5. Update both balances.
6. Commit.

Consistent lock ordering reduces deadlock risk.

### Optimistic concurrency control

Optimistic concurrency control allows operations to proceed without acquiring all required locks in advance.

Before committing, the system checks whether relevant records have changed.

The PostgreSQL script implements this approach using account version numbers.

An update succeeds only when the supplied version matches the current version.

This is useful when conflicts are relatively uncommon and long-duration locks would be undesirable.

## 9. Python Implementation

The Python file implements an MVCC-inspired database simulator.

### Main components

| Component | Responsibility |
|---|---|
| `Database` | Maintains tables, revisions, transactions, and committed versions. |
| `Transaction` | Stores isolation level, snapshot, reads, writes, and state. |
| `Version` | Represents a committed record version. |
| `IsolationLevel` | Defines the four isolation levels. |
| `TransactionState` | Tracks transaction lifecycle. |
| `WriteConflict` | Represents conflicting modifications. |
| `SerializationFailure` | Represents serializability validation failure. |

### Transaction lifecycle

    BEGIN
      |
      v
    Read / Scan
      |
      v
    Stage Writes
      |
      v
    Validate
      |
      +------ Conflict ------> ABORT
      |
      v
    COMMIT

Rollback discards the transaction's private write set.

The implementation includes demonstrations of:

- Read Committed non-repeatable reads.
- Repeatable Read snapshot visibility.
- Prevention of dirty reads.
- Concurrent write conflicts.
- Serializable validation.
- Transaction rollback.
- Automated assertions.

### Design limitation

The Python simulator is a simplified optimistic model.

Its table-wide predicate validation is intentionally conservative. It may reject transactions that a more sophisticated database engine could safely serialize.

It does not implement physical storage, durable recovery, real thread scheduling, lock management, or PostgreSQL-compatible transaction internals.

The simulator illustrates the logical mechanisms rather than claiming production database equivalence.

## 10. JavaScript Implementation

The JavaScript file adopts an event-driven transaction model.

### Main components

| Component | Responsibility |
|---|---|
| `VersionedStore` | Manages versioned records and transaction operations. |
| `EventEmitter` | Publishes transaction lifecycle events. |
| `RetryPolicy` | Retries retryable transaction failures. |
| `Map` | Stores tables, versions, reads, and writes. |
| `Set` | Tracks predicate scans. |
| `TransactionError` | Represents transaction-related failures. |

### Event-driven lifecycle

The store emits:

- `transactionStarted`
- `writeStaged`
- `transactionCommitted`
- `transactionAborted`
- `transactionRolledBack`

These events separate transaction execution from monitoring and logging.

### Asynchronous retry

The retry policy uses bounded attempts and increasing delays.

A retry must begin a new transaction.

This prevents a failed transaction from reusing an invalid snapshot.

The implementation also uses Node.js cryptographic random-number generation for retry jitter.

### Engineering considerations

The implementation uses `structuredClone` to isolate stored values from accidental mutation by callers.

A production implementation would require stronger transaction coordination, durable persistence, bounded memory usage, and real database integration.

The in-memory model is not a replacement for database-level isolation.

## 11. C++17 Implementation

The C++17 program models transaction management through domain-oriented structures.

### Main components

| Component | Responsibility |
|---|---|
| `Database` | Controls transaction execution and committed versions. |
| `Transaction` | Contains isolation state and staged modifications. |
| `Account` | Represents a financial account. |
| `Version` | Represents a committed account version. |
| `RecordKey` | Identifies a table and record pair. |
| `WriteConflict` | Reports concurrent write conflicts. |
| `SerializationFailure` | Reports serializability violations. |

### Implementation decisions

- `std::map` provides ordered record management.
- `std::vector` retains record versions.
- `std::set` records predicate scans.
- `std::optional` represents potentially unavailable versions.
- Exceptions distinguish transaction failure conditions.
- Explicit state transitions prevent repeated commits and invalid rollbacks.

### Atomic transfer

The banking example performs the following logical operations:

1. Read both accounts.
2. Validate the transfer amount.
3. Verify sufficient funds.
4. Stage the debit.
5. Stage the credit.
6. Validate transaction conflicts.
7. Commit both changes together.

If validation fails, the transaction is aborted.

The implementation demonstrates domain modeling and state management without external libraries.

It is an educational engine rather than a multithreaded database. Its transaction coordination is logical and does not implement physical concurrency control.

## 12. Java 17 Implementation

The Java implementation adopts an enterprise-oriented service architecture.

### Domain model

The `Account` record is immutable.

Changes produce new account instances instead of modifying existing objects.

The `Transaction` class maintains transaction-specific state.

The `IsolationPolicy` interface separates isolation rules from database operations.

`StandardIsolationPolicy` supplies the policy implementation.

### Service architecture

    BankingService
         |
         v
    Database
         |
         +-- Transaction Management
         |
         +-- Snapshot Visibility
         |
         +-- Conflict Validation
         |
         +-- Audit Events
         |
         v
    Committed Account Versions

### Important mechanisms

- Immutable records reduce unintended mutation.
- Records express domain values.
- Collections maintain transaction state.
- Custom exceptions represent distinct failure categories.
- `TransactionExecutor` manages bounded retries.
- `BankingService` enforces financial business rules.
- Audit events record transaction lifecycle operations.

### Enterprise implications

Business operations and concurrency policies are separate responsibilities.

The banking service decides whether a transfer is valid.

The database decides whether the transaction can commit under the selected isolation policy.

This separation is important because a valid business operation can still fail due to a concurrent transaction.

## 13. PostgreSQL Implementation

The SQL file implements a relational banking workflow.

### Database relationship

    Customers
       |
       v
    Accounts
       |
       +------------------+
       |                  |
       v                  v
    Transfers       Account Events
       |
       v
    Transaction Audit

### Tables

| Table | Purpose |
|---|---|
| `customers` | Stores customer information. |
| `accounts` | Stores balances, account status, and version numbers. |
| `transfers` | Records financial transfers. |
| `transaction_audit` | Records transfer-related transaction events. |
| `account_events` | Tracks balance and version changes. |

### Constraints

The schema uses:

- Primary keys.
- Foreign keys.
- Unique account numbers.
- Unique customer email addresses.
- Unique idempotency keys.
- Positive transfer amounts.
- Non-negative balances.
- Valid account statuses.
- Different source and destination accounts.

These constraints protect database integrity independently of application validation.

### Account version trigger

The `maintain_account_version()` trigger increments the account version when its balance changes.

The trigger also records the previous and new balances.

This supports optimistic concurrency control.

### Atomic transfer function

The `execute_transfer()` function:

- Validates transfer parameters.
- Checks the idempotency key.
- Locks account rows.
- Acquires locks in a consistent order.
- Checks account status.
- Checks available funds.
- Creates a transfer record.
- Updates both balances.
- Records the transaction event.

The caller controls the transaction boundary.

If any operation fails, the caller must roll back the transaction.

### Idempotency

An idempotency key identifies a logical transfer request.

The unique constraint prevents the same key from being inserted more than once.

The function returns an existing transfer identifier when it finds a previously committed request with that key.

A production implementation should also validate that a reused key has the same original request parameters. A key should not silently authorize a different transfer.

### Transaction isolation demonstrations

The SQL script demonstrates:

- `BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED`
- `BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED`
- `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ`
- `BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE`
- `COMMIT`
- `ROLLBACK`
- `SELECT ... FOR UPDATE`

The two-session experiments explain how concurrent operations affect transaction visibility and commit eligibility.

The demonstrations must be executed in separate PostgreSQL sessions to observe genuine concurrent behavior.

Sequential statements in one session cannot independently reproduce every concurrency anomaly.

## 14. Isolation-Level Selection in Business Systems

Isolation should be selected according to business invariants, not simply by choosing the strongest available level for every query.

| Business operation | Typical approach |
|---|---|
| Product catalogue retrieval | Read Committed |
| Customer profile retrieval | Read Committed |
| Financial balance transfer | Explicit row locking or Serializable |
| Inventory reservation | Atomic conditional update, locking, or Serializable |
| Multi-record financial calculation | Repeatable Read or Serializable, depending on invariants |
| Regulatory reporting snapshot | Repeatable Read |
| Concurrent quota enforcement | Serializable or explicit locking |
| High-contention counter update | Atomic database update |

These are starting points, not universal prescriptions. Schema constraints, query design, contention, and database-specific behavior affect the correct choice.

## 15. Failure Handling and Retry Strategy

Transaction failures should be classified before retrying.

| Failure | Appropriate handling |
|---|---|
| Insufficient funds | Reject the business operation. |
| Invalid account | Reject the request. |
| Duplicate idempotency key | Return or reconcile the existing request. |
| Write conflict | Start a fresh transaction and recalculate. |
| Serialization failure | Retry the complete transaction. |
| Deadlock | Roll back and retry where safe. |
| Constraint violation | Correct or reject the underlying operation. |
| Connection failure during commit | Reconcile using the idempotency key before retrying. |

### Safe retry workflow

    Begin transaction
          |
          v
    Read current data
          |
          v
    Apply business rules
          |
          v
    Stage modifications
          |
          v
    Commit
          |
       Failure?
          |
       Yes
          |
          v
    Rollback / Abort
          |
          v
    Retry from fresh snapshot
          |
          v
    Stop after retry limit

Retries should be bounded and use backoff.

External side effects, such as sending payment notifications, should not be performed as though a database commit has already succeeded. A transactional outbox pattern can be used when reliable coordination between database commits and message delivery is required.

## 16. Security and Performance Considerations

### Security

- Validate transaction parameters.
- Use parameterized SQL.
- Apply least-privilege database roles.
- Restrict access to audit information.
- Avoid exposing internal transaction details to unauthorized clients.
- Validate idempotency keys and request ownership.
- Enforce account authorization independently of transaction isolation.
- Protect sensitive information in application logs.

Isolation does not replace authorization or access control.

### Performance

- Keep transactions short.
- Avoid unnecessary serializable transactions.
- Index frequently queried predicate columns.
- Acquire multiple row locks in a consistent order.
- Use atomic conditional updates for simple counters and inventory operations.
- Limit transaction retries.
- Monitor deadlocks and serialization failures.
- Avoid long-lived snapshots that retain obsolete row versions.
- Evaluate contention before introducing additional locking.

### Operational monitoring

Useful transaction metrics include:

| Metric | Operational value |
|---|---|
| Commit rate | Measures successful transaction throughput. |
| Rollback rate | Identifies unsuccessful operations. |
| Serialization failures | Identifies concurrent dependency conflicts. |
| Deadlock count | Identifies conflicting lock acquisition. |
| Transaction duration | Identifies long-running transactions. |
| Retry count | Measures contention and retry overhead. |
| Lock wait time | Identifies blocking. |
| Version cleanup activity | Helps assess MVCC maintenance pressure. |

## 17. Running the Implementations

| Deliverable | Runtime | Execution |
|---|---|---|
| Python | Python 3.10+ | `python transaction_isolation.py` |
| JavaScript | Node.js 18+ | `node transaction_isolation.js` |
| C++17 | C++ compiler | Compile with `-std=c++17` |
| Java | Java 17 | `javac TransactionIsolationEnterprise.java` followed by `java TransactionIsolationEnterprise` |
| PostgreSQL | PostgreSQL 14+ | Execute the SQL script using `psql` |

The Python program includes automated tests for snapshot visibility, Read Committed behavior, write conflicts, and rollback.

The remaining programs execute independent demonstrations of transaction behavior.

The PostgreSQL script creates the schema, tables, indexes, trigger, functions, sample records, reports, and transaction demonstrations.

## 18. Technical Limitations

The implementations intentionally use different approaches.

| Implementation | Primary perspective | Limitation |
|---|---|---|
| Python | MVCC simulation and validation | No physical concurrency or durable storage |
| JavaScript | Event-driven transaction lifecycle | In-memory execution without database-backed coordination |
| C++17 | Domain modeling and conflict engine | No multithreaded lock manager or persistent storage |
| Java 17 | Enterprise service and policy separation | Simplified transaction execution |
| PostgreSQL | Relational integrity and native isolation | Concurrent experiments require multiple database sessions |

The four application-language programs use simplified revision-based transaction models. Their behavior is intended to explain isolation concepts, not to reproduce the exact semantics of a particular production database.

PostgreSQL provides the actual database-level transaction and concurrency mechanisms used by the SQL implementation.
