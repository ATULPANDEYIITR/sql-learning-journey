# Database Transactions and Atomic Operations

## 1. Domain and Technical Scope

A database transaction is a logical unit of work containing one or more database operations. The operations are treated as a single unit for purposes of successful completion or failure.

The transaction model prevents incomplete business operations from becoming permanent database state.

A banking transfer provides a practical example:

- Debit the source account.
- Credit the destination account.
- Record the debit in the ledger.
- Record the credit in the ledger.
- Record the transaction outcome.

These operations must succeed together. If the destination credit fails after the source debit, the source debit must not remain committed.

The implementations use account transfers, deposits, withdrawals, transaction histories, and accounting invariants to demonstrate this requirement.

## 2. Fundamental Transaction Commands

| Command | Purpose | Database effect |
|---|---|---|
| `BEGIN` | Starts a transaction | Establishes a transactional unit |
| `COMMIT` | Completes a transaction | Makes its changes permanent |
| `ROLLBACK` | Cancels a transaction | Discards uncommitted changes |
| `SAVEPOINT` | Establishes an intermediate recovery point | Allows partial rollback |
| `ROLLBACK TO SAVEPOINT` | Reverts operations after a savepoint | Preserves earlier operations |
| `RELEASE SAVEPOINT` | Removes a savepoint | Retains changes already made |

A transaction begins with `BEGIN` and normally ends with either `COMMIT` or `ROLLBACK`.

Example workflow:

    BEGIN
       |
       v
    Execute database operations
       |
       v
    Validate constraints
       |
       +------ All operations succeed ------> COMMIT
       |
       +------ An operation fails ----------> ROLLBACK

A transaction that has committed cannot be reversed using an ordinary SQL `ROLLBACK`. A new compensating transaction is required to reverse a previously committed business operation.

## 3. ACID Properties

ACID describes four properties that provide reliable transaction processing.

### Atomicity

Atomicity means that all operations in a transaction succeed together or none of their changes become committed.

Consider a transfer of INR 1,500 from Alice to Bob.

Initial balances:

| Account | Balance |
|---|---:|
| Alice | 10,000 |
| Bob | 5,000 |

Expected balances:

| Account | Balance |
|---|---:|
| Alice | 8,500 |
| Bob | 6,500 |

If the debit succeeds but the credit fails, atomicity prevents the incomplete transfer from becoming permanent.

The implementations demonstrate atomicity through private working states, transaction locks, and database transaction boundaries.

### Consistency

Consistency means that a successful transaction preserves the database's declared integrity rules.

Examples include:

- Account balances cannot become negative.
- Transaction amounts must be positive.
- Source and destination accounts must differ.
- Account currencies must match.
- Every transfer must contain corresponding debit and credit entries.
- Account identifiers must remain unique.

Consistency is enforced through validation, database constraints, and transaction-processing logic.

### Isolation

Isolation controls how concurrent transactions interact.

Suppose two withdrawal requests attempt to withdraw INR 8,000 from an account containing INR 10,000.

Without appropriate concurrency control, both transactions could read the same initial balance and incorrectly proceed.

Database locking, transaction isolation levels, and optimistic concurrency checks prevent conflicting updates from producing invalid results.

### Durability

Durability means that committed changes survive subsequent failures within the guarantees of the database system.

PostgreSQL uses write-ahead logging (WAL) and recovery mechanisms to support durability.

A successful commit indicates that the database has accepted the transaction according to its configured durability guarantees.

The in-memory Python, JavaScript, C++17, and Java 17 simulations demonstrate transaction behavior but do not provide database-grade crash durability. Their account states exist in application memory. The Python and JavaScript implementations also demonstrate report export, which is not equivalent to a durable transactional database.

## 4. Transaction Lifecycle

A transaction moves through a defined lifecycle.

| State | Meaning |
|---|---|
| `ACTIVE` | Operations can be staged or executed |
| `COMMITTED` | Changes have been successfully published |
| `ROLLED_BACK` | Changes have been discarded |

The lifecycle is:

    ACTIVE
      |
      +----> COMMITTED
      |
      +----> ROLLED_BACK

A committed or rolled-back transaction cannot be reused as an active transaction.

### Transaction boundaries

Transaction boundaries determine which operations belong to the same logical unit.

For example:

    BEGIN
       |
       +-- Debit Alice
       |
       +-- Credit Bob
       |
       +-- Insert debit ledger entry
       |
       +-- Insert credit ledger entry
       |
    COMMIT

All four operations belong to the same transaction.

If an operation fails, the transaction must be rolled back.

### Transaction failures

Common failure conditions include:

- Insufficient funds.
- Missing account records.
- Invalid transaction amounts.
- Currency mismatches.
- Duplicate requests.
- Concurrent modifications.
- Constraint violations.
- Database connection failures.
- Deadlocks.
- Serialization failures.

A transaction-processing system must distinguish validation failures from concurrency failures and infrastructure failures.

A concurrency failure may justify retrying the complete transaction. A validation failure generally requires correcting the underlying request.

## 5. Savepoints and Partial Rollback

A savepoint creates an intermediate recovery point inside a transaction.

Example:

    BEGIN

    Deposit 10,000

    SAVEPOINT before_withdrawal

    Withdraw 5,000

    ROLLBACK TO SAVEPOINT before_withdrawal

    COMMIT

The deposit survives, while the withdrawal is undone.

This differs from a complete rollback, which discards all changes made within the transaction.

Savepoints are useful when a workflow contains optional operations or when a particular processing stage can fail without requiring the entire transaction to be discarded.

They do not create independent transactions. Their changes remain subject to the outer transaction's final commit or rollback.

## 6. Python Implementation

The Python implementation provides an in-memory transaction simulator.

### Domain model

The primary classes are:

| Class | Responsibility |
|---|---|
| `Account` | Stores account identity, ownership, balance, and currency |
| `Transaction` | Tracks operations and transaction state |
| `LedgerEntry` | Records financial movements |
| `TransactionalBank` | Coordinates transaction execution |

`Decimal` is used for monetary values to avoid the precision problems associated with binary floating-point arithmetic.

### Atomic publication

The transaction engine uses a private balance dictionary during commit processing.

The mechanism is:

1. Copy the existing account balances.
2. Apply all staged operations to the copy.
3. Validate every resulting balance.
4. Construct the pending ledger entries.
5. Publish all account balances.
6. Append ledger entries.
7. Change the transaction state to `COMMITTED`.

If validation fails before publication, the original account balances remain unchanged.

The `RLock` protects shared state during account operations and publication.

### Transaction operations

The implementation supports:

- `begin()`
- `transfer()`
- `deposit()`
- `withdraw()`
- `commit()`
- `rollback()`
- `execute()`

The `execute()` method coordinates a sequence of operations and automatically rolls back an active transaction after an exception.

### Validation and failure handling

The implementation checks:

- Account existence.
- Unique account identifiers.
- Positive transaction amounts.
- Currency compatibility.
- Different source and destination accounts.
- Sufficient funds.
- Non-negative final balances.
- Valid transaction states.

Custom exceptions distinguish insufficient funds, transaction-state errors, and constraint violations.

### Reporting

The report-export operation writes account balances and ledger entries to JSON.

It writes to a temporary file and replaces the target file after serialization.

This reduces the likelihood of exposing a partially written report. It does not make the report export and the in-memory transaction commit one atomic operation.

### Limitations

The simulator is designed for transaction learning. Its global lock serializes commits, and it does not provide a persistent database, recovery log, distributed transaction protocol, or full isolation-level implementation.

Its snapshot mechanism should not be interpreted as a substitute for database concurrency control.

## 7. JavaScript Implementation

The JavaScript implementation uses an event-driven transaction engine.

### Architecture

| Component | Responsibility |
|---|---|
| `Account` | Validated account state |
| `Transaction` | Transaction identity, state, and staged operations |
| `Mutex` | Serializes asynchronous commit operations |
| `TransactionEngine` | Transaction processing and event publication |
| `EventEmitter` | Publishes transaction lifecycle events |

JavaScript stores money in integer minor units rather than floating-point currency values.

For example, INR 10,000.00 is represented as 1,000,000 paise.

This avoids common floating-point representation errors for ordinary monetary amounts within the safe integer range.

### Event-driven processing

The engine publishes events such as:

- `transactionStarted`
- `operationStaged`
- `transactionCommitted`
- `transactionRolledBack`
- `transactionConflict`

This separates transaction execution from monitoring and reporting components.

A monitoring component can subscribe to lifecycle events without changing the transaction engine's internal processing logic.

### Asynchronous commit

The `commit()` method returns a Promise.

It acquires an exclusive mutex before validating and publishing changes.

The engine creates a private balance map and applies staged operations to it.

Only after all operations pass validation are balances and ledger entries published.

### Optimistic concurrency

Each transaction records the database version observed when it begins.

During commit, the engine compares the recorded version with the current version.

If they differ, the transaction is rejected as stale.

The `executeWithRetry()` method demonstrates retrying a complete transaction after a concurrency conflict.

A retry must reconstruct the transaction from current state. Reusing stale staged operations without revalidation would be unsafe.

### Practical considerations

The implementation uses Node.js standard-library features, including:

- `EventEmitter`
- `crypto.randomUUID()`
- `fs/promises`
- `Map`
- `Promise`

The mutex protects commits within one JavaScript process. It does not coordinate multiple application instances or independently running processes.

## 8. C++17 Implementation

The C++17 implementation emphasizes explicit domain modeling and controlled state transitions.

### Core data structures

| Structure | Purpose |
|---|---|
| `Account` | Represents an account |
| `Operation` | Represents a staged financial operation |
| `LedgerEntry` | Records a committed movement |
| `Transaction` | Maintains operations and state |
| `RepositoryGovernanceEngine` | Coordinates the transaction workflow |

The implementation uses:

- `std::map` for account storage.
- `std::vector` for operations and ledger entries.
- `std::string` for identifiers.
- `enum class` for strongly typed states and operations.
- `std::int64_t` for integer monetary units.

### State management

The `Transaction` class owns its state and operation collection.

Only active transactions accept new operations.

The transaction engine validates the entire working balance map before publishing changes.

This approach prevents partial balance updates when an operation fails.

### Isolation demonstration

The engine provides two simplified isolation policies:

| Policy | Behavior |
|---|---|
| `READ_COMMITTED` | Applies operations against the latest state during a serialized commit |
| `SERIALIZABLE` | Rejects transactions based on an outdated global version |

The serializable demonstration is an optimistic concurrency simulation, not a complete implementation of PostgreSQL serializable isolation.

The version check provides a simple mechanism for detecting stale transactions.

### Performance considerations

Account lookups in `std::map` take logarithmic time.

For a transaction containing `m` operations and an account collection containing `n` accounts, copying the complete account balance map costs approximately O(n log n), while applying operations costs O(m log n).

This approach favors clarity and failure safety over optimal performance for very large account collections.

A production engine would use more selective locking, persistent storage, and a carefully designed transaction log.

## 9. Java 17 Implementation

The Java implementation models transaction processing as an enterprise-oriented service.

### Domain types

The implementation uses:

- `Account` for account state.
- `Transaction` for transaction lifecycle management.
- `Operation` as an immutable record.
- `LedgerEntry` as an immutable record.
- `TransactionPolicy` as an isolation-policy interface.
- `TransactionService` as the processing service.

The enums `TransactionState`, `OperationType`, and `IsolationLevel` restrict domain values to recognized states and operations.

### Policy-based transaction validation

The `TransactionPolicy` interface separates transaction validation from the commit service.

Two policy implementations are provided:

- `SerializablePolicy`
- `ReadCommittedPolicy`

The serializable policy rejects a transaction when its starting version does not match the current database version.

The read-committed simulation validates operations against the latest committed balances while the commit lock is held.

These are educational policy models rather than implementations of all database isolation guarantees.

### Enterprise transaction workflow

The service:

1. Creates a transaction.
2. Validates requested operations.
3. Acquires a fair `ReentrantLock`.
4. Applies operations to a private balance map.
5. Checks constraints.
6. Publishes account changes.
7. Appends ledger entries.
8. Updates transaction state.

`Math.addExact()` detects integer overflow rather than silently allowing a corrupted monetary balance.

### Service-layer separation

The transaction service centralizes commit behavior.

This is important because application components should not independently modify account balances or append financial ledger entries.

Centralized transaction processing makes validation and business rules easier to audit.

### Limitations

The Java implementation is an in-memory model.

The lock coordinates threads within one process. It does not replace database transactions or distributed concurrency control.

A real enterprise application should persist transaction state and financial records in a transactional database.

## 10. PostgreSQL Implementation

The PostgreSQL script models transaction processing using relational tables, constraints, triggers, functions, procedures, and SQL transaction commands.

### Relational schema

The database contains six principal tables.

| Table | Responsibility |
|---|---|
| `accounts` | Stores account identity, status, currency, and balance |
| `bank_transactions` | Stores transaction metadata and lifecycle status |
| `transaction_ledger` | Stores debit and credit movements |
| `transaction_audit` | Records transaction status changes |
| `idempotency_keys` | Prevents repeated processing of the same request |

The schema separates transaction metadata from individual financial ledger movements.

A transfer has one transaction record and two corresponding ledger entries.

### Referential integrity

Primary keys identify records.

Foreign keys enforce relationships between:

- Transactions and accounts.
- Ledger entries and transactions.
- Ledger entries and accounts.
- Idempotency keys and transaction records.

Unique constraints prevent duplicate account numbers and transaction references.

Check constraints enforce:

- Positive transaction amounts.
- Valid account statuses.
- Valid transaction types.
- Non-negative balances.
- Correct debit and credit signs.
- Valid source and destination account combinations.

### Atomic transfer function

The `transfer_funds()` function performs a transfer within the transaction context of its calling SQL statement.

Its operations include:

1. Validate the amount and account identifiers.
2. Register an idempotency key.
3. Lock both account rows.
4. Validate account status.
5. Validate currency compatibility.
6. Check source balance.
7. Insert transaction metadata.
8. Debit the source account.
9. Credit the destination account.
10. Insert debit and credit ledger entries.
11. Mark the transaction committed.
12. Associate the idempotency key with the transaction.

The function does not issue its own `COMMIT`.

The surrounding SQL transaction controls whether its database changes become permanent.

If an unhandled exception occurs, the statement's changes are rolled back.

### Row locking

The function uses `SELECT ... FOR UPDATE`.

This obtains row-level locks on the participating accounts.

Concurrent transactions attempting to update the same rows must wait for the relevant locks to be released.

Rows are locked in account-ID order to reduce the likelihood of deadlocks between transfers involving the same accounts.

Deadlocks can still occur in more complicated workflows and must be handled by retrying an appropriate transaction.

### Idempotency

An idempotency key identifies a particular business request.

For example:

`REQUEST-TRANSFER-001`

If the same key is submitted again after successful processing, the function returns the original transaction ID rather than executing the transfer again.

The unique primary key on `idempotency_keys` protects against duplicate request registration.

A request that has not yet acquired a transaction ID is treated as an in-progress or incomplete request and is not silently executed again.

The example demonstrates successful-request deduplication. Production APIs should also verify that a reused idempotency key has the same request parameters.

### Stored procedures and functions

The script provides two distinct database routines.

| Routine | Purpose |
|---|---|
| `transfer_funds()` | Executes a complete account-to-account transfer |
| `process_account_operation()` | Processes an individual deposit or withdrawal |

The transfer function returns a transaction ID.

The procedure executes a database operation using the transaction context established by the caller.

### Triggers

The account validation trigger prevents:

- Negative balances.
- Currency changes after account creation.
- Closing accounts that have non-zero balances.

It also maintains the account version when the balance changes.

The transaction audit trigger records changes in transaction status.

These triggers enforce database-level behavior independently of the application that submits the SQL statements.

### Savepoint demonstration

The script demonstrates a transaction that:

- Deposits funds.
- Creates a savepoint.
- Attempts a withdrawal.
- Rolls back to the savepoint.
- Commits the remaining transaction.

The earlier deposit remains, while the later withdrawal is discarded.

### Exception handling

The script uses PL/pgSQL exception blocks to demonstrate controlled failure handling.

A PL/pgSQL exception block establishes a subtransaction. When an error is caught, changes made inside the failed block are rolled back.

The outer block can then continue processing.

A normal failed SQL statement outside a recovery mechanism leaves the surrounding PostgreSQL transaction in an aborted state until rollback or savepoint recovery.

### Reporting and validation

The SQL implementation includes:

- An account transaction summary view.
- Transaction-status aggregation.
- Ledger movement aggregation.
- Missing-ledger detection.
- Unbalanced transfer detection.
- Account eligibility evaluation.
- Transaction audit reporting.
- Final account balance reporting.

These queries distinguish the transaction's recorded status from the integrity of its associated financial movements.

## 11. Distinctions Between Transaction Concepts

| Concept | Meaning | Example |
|---|---|---|
| Transaction | A logical unit of database work | Account transfer |
| Atomic operation | An operation whose effects are indivisible | Debit and credit together |
| Transaction boundary | Defines the operations included in a transaction | `BEGIN` and `COMMIT` |
| Commit | Makes transaction changes permanent | Successful transfer |
| Rollback | Discards uncommitted changes | Failed withdrawal |
| Savepoint | Creates an intermediate recovery point | Optional workflow stage |
| Isolation | Controls interaction between concurrent transactions | Concurrent withdrawals |
| Locking | Controls access to shared records | `SELECT FOR UPDATE` |
| Idempotency | Prevents duplicate execution of a request | Repeated payment request |
| Ledger | Records financial movements | Debit and credit entries |

These mechanisms solve related but different problems.

Atomicity concerns the all-or-nothing outcome of a transaction.

Isolation concerns the interaction between concurrent transactions.

Idempotency concerns repeated requests, including requests made after uncertain network outcomes.

A database transaction alone does not automatically provide business-level idempotency.

## 12. Transaction Isolation Levels

Database systems offer different isolation guarantees.

| Isolation level | Principal behavior | Important limitation |
|---|---|---|
| Read Uncommitted | Allows the weakest isolation model | PostgreSQL treats it as Read Committed |
| Read Committed | Each statement observes an appropriate committed snapshot | Non-repeatable reads may occur |
| Repeatable Read | Maintains a transaction-level snapshot in PostgreSQL | Serialization anomalies can still be possible |
| Serializable | Provides serializable transaction execution | Transactions may fail with serialization errors |

### Read Committed

Under PostgreSQL Read Committed, each statement normally receives a new snapshot of committed data.

A later statement in the same transaction can therefore observe changes committed by another transaction after the earlier statement.

### Repeatable Read

PostgreSQL Repeatable Read maintains a stable transaction snapshot.

It prevents ordinary non-repeatable reads, but it does not provide the complete serializable guarantee.

### Serializable

Serializable isolation ensures that successfully committed concurrent transactions have results equivalent to some serial execution order.

The database may abort transactions when it detects a serialization conflict.

The application should retry the complete transaction when a retry is appropriate.

A retry must repeat the complete business operation using fresh database state rather than merely repeating the final SQL statement.

## 13. Concurrency Control

Concurrency control prevents simultaneous operations from violating business rules.

### Pessimistic locking

Pessimistic locking acquires locks before modifying shared records.

PostgreSQL example:

`SELECT * FROM accounts WHERE account_id = 1 FOR UPDATE;`

The transaction obtains a row-level lock and prevents conflicting updates while the transaction remains active.

Advantages:

- Straightforward control of conflicting writes.
- Suitable for critical account updates.
- Reduces the risk of lost updates.

Limitations:

- Transactions may wait.
- Locks consume database resources.
- Incorrect lock ordering can cause deadlocks.

### Optimistic concurrency

Optimistic concurrency allows operations to proceed using a recorded version.

Before publishing changes, the system verifies that the version has not changed.

A version mismatch indicates that the transaction may have been based on stale state.

The Python, JavaScript, C++17, and Java 17 implementations demonstrate simplified versions of this approach.

### Deadlocks

A deadlock occurs when transactions hold locks that the other transactions need.

For example:

    Transaction A locks Account 1
    Transaction B locks Account 2
    Transaction A requests Account 2
    Transaction B requests Account 1

Neither transaction can proceed.

Database systems detect deadlocks and abort one transaction.

Practical prevention measures include:

- Consistent lock ordering.
- Short transaction duration.
- Avoiding unnecessary locks.
- Keeping network requests outside locked transaction sections.
- Retrying transactions that fail with appropriate concurrency errors.

## 14. Financial Integrity and Ledger Design

A ledger records individual financial movements rather than only the latest account balance.

For a transfer of INR 1,500:

| Account | Entry | Amount |
|---|---|---:|
| Alice | Debit | -1,500 |
| Bob | Credit | +1,500 |

The sum of these entries is zero.

This provides an important accounting invariant for transfers.

The balance stored in an account is a current-state representation. The ledger records the historical movements that explain changes to that state.

These are related but distinct responsibilities.

A production financial system should normally preserve committed ledger entries as immutable records and use separate correcting entries rather than silently rewriting historical financial movements.

The supplied PostgreSQL script demonstrates balanced ledger movements and validation queries, but does not implement a complete immutable double-entry accounting platform.

## 15. Transaction Security

Transaction processing requires controls beyond basic atomicity.

Important controls include:

- Authentication of the requesting principal.
- Authorization for each source and destination account.
- Validation of account ownership and permitted operations.
- Positive amount validation.
- Currency compatibility.
- Idempotency-key validation.
- Protection against duplicate requests.
- Parameterized SQL.
- Database constraints.
- Least-privilege database permissions.
- Audit logging.
- Secure handling of transaction identifiers.
- Encryption of sensitive communications and stored information.

A transaction identifier is not an authorization credential.

An application must not allow a caller to transfer money merely because the caller knows an account ID.

The examples concentrate on transaction mechanics and financial integrity. They do not implement authentication, authorization, encryption, or a production payment gateway.

## 16. Performance Considerations

Transaction performance depends on transaction duration, lock contention, data access patterns, indexes, and database workload.

| Mechanism | Performance implication |
|---|---|
| Short transactions | Reduce lock duration |
| Row-level locking | Limits conflicts to relevant records |
| Deterministic lock ordering | Reduces avoidable deadlocks |
| Appropriate indexes | Accelerate account and transaction lookups |
| Batch processing | Can reduce repeated database round trips |
| Smaller working sets | Reduce memory and copying costs |
| Optimistic version checks | Avoid unnecessary locks when conflicts are uncommon |
| Excessive savepoints | Add transaction-management overhead |
| Long-running transactions | Can delay cleanup and retain database resources |

The PostgreSQL implementation indexes account references, transaction statuses, timestamps, ledger entries, and audit records.

The application-language implementations use in-memory data structures to make transaction mechanisms observable without requiring external libraries.

Their copying strategies are intentionally simple and should not be interpreted as optimal implementations for large financial systems.

## 17. Practical Transaction Failure Scenarios

| Scenario | Expected behavior |
|---|---|
| Successful transfer | Debit and credit are committed together |
| Insufficient funds | Transfer is rejected without balance changes |
| Missing destination | Transaction is rejected |
| Currency mismatch | Transfer is rejected |
| Duplicate request | Existing result is returned when the idempotency key matches |
| Invalid amount | Validation prevents processing |
| Concurrent modification | Transaction is rejected or serialized |
| Deadlock | Database aborts one transaction |
| Serialization conflict | Complete transaction is retried when appropriate |
| Explicit rollback | All uncommitted changes are discarded |
| Savepoint rollback | Only operations after the savepoint are discarded |
| Connection loss before commit | Transaction outcome depends on whether the database committed |
| Connection loss after commit | Client may not know whether the operation succeeded; idempotency is needed |

An important production concern is an uncertain commit outcome.

A client can lose its connection after the database commits but before the response reaches the client.

The client must not assume that the operation failed and submit an entirely new payment request.

A stable idempotency key allows the application to determine whether the original request has already been processed.

## 18. Comparative Implementation Design

| Dimension | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Main perspective | Transaction simulation | Event-driven processing | Explicit state and data modeling | Enterprise service and policy separation | Persistent relational transaction processing |
| Primary storage | Dictionaries | Maps | STL maps | Collections | Relational tables |
| Transaction state | Enum | Object state | Strongly typed enum | Enum | Status column |
| Atomic publication | Working snapshot | Working map and mutex | Working balance map | Working balance map and lock | Database transaction |
| Concurrency mechanism | Reentrant lock | Async mutex and version check | Simplified version check | Reentrant lock and version check | Row locks and isolation |
| Failure handling | Custom exceptions | Promise rejection and events | Exceptions | Custom exceptions | SQL exceptions and rollback |
| Audit mechanism | Ledger entries | Event notifications and ledger | Ledger entries | Ledger entries | Audit trigger and ledger |
| Persistence | JSON report | JSON report | In-memory | In-memory | Relational database |

## 19. Execution and Verification

### Python

- Save the first implementation as `transactions.py`.
- Run `python transactions.py`.
- Inspect `transaction_report.json`.
- Verify that committed transfers affect both accounts.
- Verify that explicit rollback does not alter balances.

### JavaScript

- Save the second implementation as `transactions.js`.
- Run `node transactions.js`.
- Inspect `transaction_report.json`.
- Observe transaction lifecycle events and the serialization-conflict demonstration.

### C++17

- Save the third implementation as `transactions.cpp`.
- Compile using `g++ -std=c++17 -O2 -Wall -Wextra -pedantic transactions.cpp -o transactions`.
- Run `./transactions` on Linux or `transactions.exe` on Windows.

### Java 17

- Save the fourth implementation as `Main.java`.
- Compile using `javac Main.java`.
- Run using `java Main`.

### PostgreSQL

- Save the SQL implementation as `transactions.sql`.
- Execute using `psql -d your_database -f transactions.sql`.
- The script creates the `transaction_lab` schema.
- The script removes an existing schema with that name before recreating it.
- Inspect the account, transaction, ledger, and audit tables after execution.

The SQL implementation uses `gen_random_uuid()`, available in modern PostgreSQL releases.

The script is intended for a dedicated learning database because its initial schema reset removes an existing `transaction_lab` schema.

## 20. Implementation Boundaries

The five implementations demonstrate transaction processing from different engineering perspectives.

The four application-language implementations use simplified in-memory transaction models. Their locks and version checks illustrate concurrency-control principles but do not reproduce all database isolation guarantees.

The PostgreSQL implementation provides actual transactional database behavior, including SQL transaction boundaries, row-level locking, savepoints, constraints, and database-managed rollback.

None of the examples implements distributed atomic transactions across independent databases or external payment systems.

For operations spanning external services, ordinary database transactions are insufficient. A distributed workflow generally requires mechanisms such as transactional outbox processing, idempotent consumers, compensating operations, or a saga pattern.

The central engineering requirement remains the same: business operations must preserve their integrity when individual steps fail, when requests are repeated, and when multiple operations execute concurrently.
