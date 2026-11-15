# Concurrency, Locks, Concurrent Transactions and Race Conditions

## 1. Project Overview

This project implements concurrency management across Python, JavaScript, C++17, Java 17 and PostgreSQL.

The central scenario is a financial transaction system in which multiple users and application processes attempt to update shared account balances simultaneously.

The system must preserve account integrity even when:

- Multiple transactions access the same account.
- Two transactions attempt to update the same balance.
- Several threads execute simultaneously.
- Asynchronous operations interleave.
- Transactions fail after acquiring locks.
- Two transactions acquire resources in conflicting orders.
- A client repeats a transaction request.
- A transaction reads outdated data and attempts to overwrite newer data.

The implementations distinguish synchronization mechanisms, transaction boundaries, consistency rules and concurrency-control strategies.

## 2. Fundamental Concepts

### 2.1 Concurrency

Concurrency describes the execution of multiple operations during overlapping periods.

Concurrent operations may execute on separate CPU cores, different threads, asynchronous event-loop tasks or independent database sessions.

Concurrency does not necessarily mean simultaneous execution.

For example, two bank transfers can overlap:

- Transaction A transfers money from account X to account Y.
- Transaction B transfers money from account X to account Z.

Both transactions depend on the balance of account X.

Without synchronization, both transactions could read the same initial balance and independently calculate their updates.

The resulting balance might not represent either the correct sequential execution or the intended combined result.

### 2.2 Parallelism

Parallelism means executing operations simultaneously on multiple processing resources.

| Property | Concurrency | Parallelism |
|---|---|---|
| Main objective | Coordinate overlapping operations | Execute operations simultaneously |
| Execution | May be interleaved | Uses multiple execution resources |
| Primary concern | Correct shared-state behavior | Correct execution and resource utilization |
| Example | Multiple asynchronous transactions | Multiple CPU workers |

A concurrent system may operate on a single processor. Parallel execution generally requires multiple execution resources.

### 2.3 Race Conditions

A race condition occurs when the correctness of a result depends on the timing or ordering of concurrent operations.

Consider an account with a balance of 1,000.

Two transactions independently read this balance:

| Operation | Transaction A | Transaction B |
|---|---:|---:|
| Read balance | 1,000 | 1,000 |
| Calculate withdrawal | 200 | 300 |
| Calculate new balance | 800 | 700 |
| Write balance | 800 | 700 |

The expected balance is 500.

The final balance may become 800 or 700 depending on which update occurs last.

This is a lost-update problem.

Other concurrency anomalies include:

- Dirty reads: observing uncommitted changes.
- Non-repeatable reads: obtaining different values when reading the same row twice within a transaction.
- Phantom reads: observing additional or missing rows when repeating a range query.
- Write skew: independently valid updates producing an invalid combined state.
- Stale writes: overwriting a newer value using an outdated version.
- Double execution: processing the same business request more than once.

### 2.4 Critical Sections

A critical section is a portion of code that accesses shared mutable state and requires synchronization.

For example, the following operations form one logical critical section:

1. Read the source balance.
2. Validate available funds.
3. Deduct the transfer amount.
4. Credit the destination.
5. Update transaction state.

Protecting only the deduction is insufficient. The entire business operation must preserve its consistency requirements.

## 3. Locks and Synchronization

### 3.1 Mutual Exclusion

Mutual exclusion ensures that only one execution context at a time can enter a protected critical section.

A mutex is commonly used for this purpose.

| Mechanism | Function |
|---|---|
| Mutex | Exclusive access to shared state |
| Recursive mutex | Allows the owning thread to acquire the same lock again |
| Read-write lock | Allows multiple readers or one writer |
| Atomic operation | Performs supported operations without an externally visible intermediate state |
| Semaphore | Controls access to a limited number of resources |
| Condition variable | Coordinates execution based on a condition |
| Advisory lock | Provides application-defined coordination in a database |

Locks protect shared state, but they do not automatically guarantee correct transaction design.

### 3.2 Lock Acquisition and Release

A safe locking workflow is:

1. Identify shared resources.
2. Acquire the necessary locks.
3. Validate the current state.
4. Execute the protected operation.
5. Restore the original state if an exception occurs.
6. Release locks.

Lock release must happen even when an operation fails.

The implementations use language-specific resource-management mechanisms:

| Language | Synchronization mechanism | Resource release |
|---|---|---|
| Python | `threading.Lock`, `threading.RLock` | `with` statement |
| JavaScript | Asynchronous mutex | `try/finally` |
| C++17 | `std::mutex`, `std::scoped_lock` | RAII |
| Java 17 | `ReentrantLock` | `try/finally` |
| PostgreSQL | Row-level locks | Transaction completion |

### 3.3 Deadlocks

A deadlock occurs when two or more transactions wait indefinitely for resources held by one another.

A classic example:

| Step | Transaction A | Transaction B |
|---|---|---|
| 1 | Locks account X | |
| 2 | | Locks account Y |
| 3 | Requests account Y | |
| 4 | | Requests account X |

Transaction A waits for B.

Transaction B waits for A.

Neither can continue.

Four necessary conditions are commonly associated with deadlocks:

- Mutual exclusion: a resource cannot be used simultaneously by conflicting operations.
- Hold and wait: a transaction retains one resource while requesting another.
- No preemption: resources cannot be forcibly removed from their owners.
- Circular wait: transactions form a circular dependency.

Breaking one of these conditions can prevent deadlocks.

### 3.4 Lock Ordering

This project primarily uses deterministic lock ordering.

Instead of acquiring account locks according to transfer direction, locks are acquired according to account identifiers.

For example:

- Transfer X to Y acquires X and then Y.
- Transfer Y to X also acquires X and then Y.

This removes the inconsistent acquisition order responsible for the circular-wait scenario.

C++17 additionally demonstrates `std::scoped_lock`, which provides deadlock-avoiding acquisition of multiple mutexes.

### 3.5 Lock Granularity

Lock granularity determines how much shared state is protected by one lock.

| Strategy | Advantage | Limitation |
|---|---|---|
| Global lock | Simple coordination | Restricts concurrency |
| Account-level lock | Independent accounts can be updated concurrently | Multiple resources require coordinated locking |
| Row-level database lock | Database-managed resource protection | Transactions may wait for conflicting updates |
| Fine-grained locking | Greater parallel execution | More complex lock management |

The implementations use account-level locking for balance changes.

Some examples retain a separate transaction registry lock for idempotency management. This simplifies the demonstration but limits throughput.

A production implementation can use a dedicated idempotency coordinator and database uniqueness constraints to reduce unnecessary global serialization.

## 4. Concurrent Transactions

### 4.1 Transaction Definition

A transaction is a logical unit of work that must satisfy defined consistency requirements.

For a bank transfer, the business operation contains two balance modifications:

- Debit the source account.
- Credit the destination account.

Both changes must succeed together.

If either change fails, the operation must not leave an inconsistent financial state.

### 4.2 ACID Properties

Database transactions are commonly described using four properties.

| Property | Meaning | Banking example |
|---|---|---|
| Atomicity | All operations succeed or fail together | Debit and credit occur together |
| Consistency | Valid states remain valid | Balances cannot become negative |
| Isolation | Concurrent operations are controlled | Conflicting updates cannot corrupt balances |
| Durability | Committed changes persist | Completed transfers survive process restarts |

These properties describe database transaction guarantees.

A mutex alone does not provide full ACID behavior. It does not automatically provide durable storage, database recovery or distributed transaction guarantees.

### 4.3 Transaction Lifecycle

The implemented workflow is:

    Request received
          |
          v
    Validate parameters
          |
          v
    Check idempotency
          |
          v
    Acquire resource locks
          |
          v
    Read current balances
          |
          v
    Validate business rules
          |
          v
    Update source and destination
          |
          v
    Record transaction
          |
          v
    Commit successful operation
          |
          v
    Release locks

A failed operation must either leave the previous state unchanged or produce an explicitly recorded rejection.

### 4.4 Concurrent Transfers

Consider three accounts:

| Account | Initial balance |
|---|---:|
| A | 100,000 |
| B | 100,000 |
| C | 50,000 |
| Total | 250,000 |

One thousand concurrent transfers may execute between A and B.

Each transfer must preserve the total:

\[
A+B+C=250000
\]

A successful transfer changes the distribution of funds but not their aggregate value.

The implementations verify:

- No account has a negative balance.
- All successful transactions preserve the total balance.
- Locks are released after execution.
- Repeated transaction requests do not cause additional transfers.

## 5. Pessimistic and Optimistic Concurrency Control

These approaches solve conflicting updates differently.

### 5.1 Pessimistic Locking

Pessimistic locking assumes that conflicting operations are sufficiently likely to justify acquiring locks before modification.

The transaction obtains exclusive access to the required resource.

In PostgreSQL:

`SELECT ... FOR UPDATE`

This locks selected rows against conflicting updates until the transaction completes.

Advantages:

- Prevents conflicting modifications during the protected transaction.
- Supports straightforward read-validate-update workflows.
- Suitable for highly contended financial records.

Limitations:

- Transactions may wait.
- Long-running transactions reduce throughput.
- Poor lock ordering can cause deadlocks.
- Excessive locking increases contention.

### 5.2 Optimistic Locking

Optimistic locking assumes that conflicting modifications are relatively uncommon.

Instead of holding a lock throughout the complete business workflow, the application checks whether the record changed before accepting an update.

The common mechanism uses a version column.

Example:

| Operation | Version |
|---|---:|
| Initial read | 4 |
| First successful update | 5 |
| Second update using version 4 | Rejected |

The logical update is:

`UPDATE accounts SET balance = ..., version = version + 1 WHERE account_id = ... AND version = ...`

If no row is updated, the version was stale or the record was unavailable.

The application must reload the latest state and determine whether the operation can safely be retried.

### 5.3 Comparison

| Characteristic | Pessimistic | Optimistic |
|---|---|---|
| Main mechanism | Locks | Version comparison |
| Conflict handling | Waiting or rejection | Conflict detection |
| Contention | Can create lock waits | Can create retries |
| Suitable workload | Frequent conflicts | Relatively infrequent conflicts |
| Implementation | Lock lifecycle | Version validation |
| Main risk | Deadlocks | Repeated failed updates |

The two approaches are complementary rather than interchangeable.

## 6. Idempotency and Duplicate Transactions

A transaction may be submitted more than once because of:

- Network timeouts.
- Browser retries.
- Mobile application retries.
- Message redelivery.
- Service restarts.
- Client uncertainty about whether a previous request succeeded.

Without idempotency, repeating a payment request could transfer money twice.

An idempotency key identifies a logical request.

For example:

`PAYMENT-001`

The service stores:

- The idempotency key.
- The request parameters.
- The original transaction identifier.
- The original transaction result.

When the same request arrives again, the original result is returned.

If the same key is reused with different transaction parameters, the request is rejected.

Database uniqueness constraints are especially important because multiple application instances can receive the same request simultaneously.

A process-local dictionary or map is not a substitute for a durable, shared idempotency store in a distributed application.

## 7. Python Implementation

The Python program models concurrency using the standard `threading` and `concurrent.futures` modules.

### Implemented mechanisms

| Component | Responsibility |
|---|---|
| `Account` | Holds account state and its lock |
| `Bank` | Coordinates account operations |
| `TransactionResult` | Represents an immutable transaction outcome |
| `TransactionStatus` | Defines transaction states |
| `UnsafeCounter` | Demonstrates a lost-update race |
| `SafeCounter` | Protects shared state |
| `OptimisticAccount` | Implements version checking |

### Important implementation decisions

**Context managers**

The `with` statement ensures that acquired locks are released even when exceptions occur.

**Reentrant locks**

`threading.RLock` allows the owning thread to acquire the same lock again.

**Ordered locking**

Account locks are acquired using sorted identifiers.

**Transaction rollback**

The previous balance values are preserved so that failed updates can restore the original state.

**Idempotency**

A transaction registry prevents duplicate execution within the lifetime of the process.

**Invariant validation**

The concurrent transfer test checks total balance conservation.

### Limitations

The implementation is an in-memory concurrency model.

Its idempotency registry and account state are not durable across process restarts.

The global transaction lock also serializes requests and is intended to demonstrate correctness rather than maximize production throughput.

## 8. JavaScript Implementation

The JavaScript program provides an asynchronous concurrency model based on Node.js.

JavaScript's event loop does not eliminate race conditions.

Operations can interleave whenever asynchronous execution yields control.

For example, two asynchronous functions can both read a shared value before either writes its updated value.

### Implemented mechanisms

| Component | Responsibility |
|---|---|
| `AsyncMutex` | FIFO asynchronous mutual exclusion |
| `Account` | Encapsulates account state |
| `TransactionService` | Coordinates transfers |
| `EventEmitter` | Publishes transaction events |
| `VersionedStore` | Detects stale updates |
| `Promise.all` | Coordinates concurrent requests |

### Asynchronous mutex

The mutex maintains a queue of waiting operations.

The next waiting operation receives access when the current owner releases the lock.

A `finally` block ensures release after successful or failed execution.

### Event-driven behavior

The transaction service publishes:

- `account:created`
- `transaction:committed`
- `transaction:rejected`

This separates transaction execution from monitoring and event consumption.

### Important distinction

A JavaScript mutex coordinates operations within one application process.

It does not coordinate separate Node.js processes, containers or servers.

A distributed deployment requires shared coordination, generally through database transactions or another appropriately designed distributed mechanism.

## 9. C++17 Implementation

The C++ implementation demonstrates lower-level synchronization and resource management.

### Implemented mechanisms

| Component | Responsibility |
|---|---|
| `Account` | Encapsulates financial state |
| `BankingEngine` | Coordinates transfers |
| `std::mutex` | Exclusive access |
| `std::scoped_lock` | Deadlock-avoiding multi-lock acquisition |
| `std::shared_mutex` | Shared reading and exclusive writing |
| `std::atomic` | Atomic counter operations |
| `VersionedBalance` | Optimistic concurrency |

### RAII

Resource Acquisition Is Initialization ties lock ownership to object lifetime.

When a lock-owning object leaves its scope, its destructor releases the lock.

This reduces the risk of forgotten unlock operations.

### Atomic operations

The counter uses `std::atomic` to perform safe increments.

The relaxed memory-order setting is sufficient for the counter demonstration because it only requires atomic modification of the counter itself.

It does not establish synchronization for unrelated shared data.

### Shared mutex

Multiple readers can hold shared access simultaneously.

A writer must obtain exclusive access.

This is useful when read operations significantly outnumber modifications.

### Performance considerations

- Atomic operations are suitable for simple shared counters.
- Mutexes are more appropriate for compound state transitions.
- Shared locks can improve read concurrency.
- Excessive lock acquisition can reduce throughput.
- Lock contention should be measured under realistic workloads.

## 10. Java 17 Implementation

The Java program provides an enterprise-oriented domain model.

### Implemented mechanisms

| Component | Responsibility |
|---|---|
| `Account` | Encapsulated account entity |
| `TransferRequest` | Validated immutable request |
| `TransactionResult` | Immutable result |
| `TransactionService` | Transaction coordination |
| `VersionedAccount` | Optimistic locking |
| `ReentrantLock` | Exclusive synchronization |
| `ConcurrentHashMap` | Concurrent account registry |
| `ExecutorService` | Worker management |

### Records

Java records provide compact immutable data structures for transaction requests, snapshots and results.

The compact constructor in `TransferRequest` validates business inputs when an object is created.

### Lock management

`ReentrantLock` provides explicit lock acquisition and release.

The implementation uses `try/finally` to guarantee release.

### Executor service

The executor manages concurrent transaction tasks.

The implementation collects their results through `Future` objects and verifies the resulting account state.

### Enterprise considerations

A production Java service would normally separate:

- Request validation.
- Business transaction processing.
- Persistence.
- Transaction event publishing.
- Retry handling.
- Authorization.
- Observability.

The in-memory implementation concentrates on concurrency correctness rather than distributed application infrastructure.

## 11. PostgreSQL Implementation

The PostgreSQL script models concurrency at the database level.

Unlike the application examples, PostgreSQL manages transaction isolation and database locks across independent sessions.

### Relational model

The database contains five principal tables.

| Table | Purpose |
|---|---|
| `accounts` | Account balances, versions and operational status |
| `transaction_requests` | Transfer requests and idempotency keys |
| `account_ledger` | Debit and credit records |
| `concurrency_audit` | Transaction event history |
| System catalog views | Operational session and lock diagnostics |

### Account integrity

The account table uses:

- Primary keys.
- Unique account numbers.
- Nonnegative balance constraints.
- Version validation.
- Account status validation.

### Transaction processing

The `transfer_funds` function performs:

1. Parameter validation.
2. Idempotency-key validation.
3. Request registration.
4. Duplicate-request detection.
5. Deterministic account lock acquisition.
6. Balance retrieval.
7. Account status validation.
8. Funds validation.
9. Balance modification.
10. Ledger insertion.
11. Transaction-state modification.
12. Audit recording.

The calling SQL transaction determines when these changes become committed.

### Row-level locking

The function uses `SELECT ... FOR UPDATE`.

This prevents conflicting sessions from modifying the selected account rows while the transaction holds the locks.

The account identifiers are ordered before lock acquisition to reduce deadlock risk.

### Optimistic updates

`update_balance_optimistic` accepts an update only when the expected version matches the current account version.

A return value of `FALSE` indicates that the update did not match an eligible row.

### Advisory locks

PostgreSQL advisory locks provide application-defined coordination.

The example uses transaction-scoped advisory locking.

Unlike row locks, advisory locks do not automatically protect a particular database row. Applications must consistently follow the advisory-lock protocol.

### Database transactions

The SQL script demonstrates:

- `BEGIN`
- `COMMIT`
- `ROLLBACK`
- `SELECT FOR UPDATE`
- `UPDATE`
- `INSERT`
- Transaction isolation
- Unique constraints
- Database-generated identifiers

### Important SQLSTATE values

| SQLSTATE | Meaning |
|---|---|
| `40001` | Serialization failure |
| `40P01` | Deadlock detected |
| `55P03` | Lock not available |

Applications should retry appropriate transient failures using bounded retries and randomized backoff.

A retry must execute the complete logical transaction, not merely repeat the final SQL statement.

## 12. Isolation Levels

Transaction isolation determines how concurrent transactions observe and modify database state.

| Isolation level | Important behavior |
|---|---|
| Read Uncommitted | PostgreSQL treats this as Read Committed |
| Read Committed | Each statement obtains a fresh committed snapshot |
| Repeatable Read | Transaction reads use a stable snapshot; PostgreSQL also detects certain serialization anomalies |
| Serializable | Transactions behave as though executed in a serial order, with possible serialization failures |

### Read Committed

This is PostgreSQL's default isolation level.

Each statement sees data committed before that statement begins.

A transaction can observe different committed values in separate statements.

### Repeatable Read

PostgreSQL provides snapshot isolation at this level.

Repeated reads of previously selected rows generally observe the same snapshot.

Write conflicts may result in transaction failures.

Write skew remains an important consideration.

### Serializable

Serializable isolation provides the strongest standard transaction-isolation guarantee.

PostgreSQL uses Serializable Snapshot Isolation to detect dangerous dependency patterns.

Some transactions must be aborted and retried.

Serializable execution does not eliminate the need for correct application-level business rules.

## 13. Concurrency Failure Scenarios

| Failure | Cause | Appropriate control |
|---|---|---|
| Lost update | Concurrent overwriting | Locks or version checking |
| Deadlock | Circular resource dependency | Consistent lock ordering |
| Double payment | Repeated request execution | Durable idempotency |
| Negative balance | Concurrent withdrawal validation | Atomic balance update and constraints |
| Stale update | Outdated version | Optimistic locking |
| Excessive waiting | Long-held locks | Short transactions |
| Serialization failure | Conflicting serializable operations | Full transaction retry |
| Partial transfer | Only one account updated | Atomic database transaction |
| Lock leak | Missing release operation | RAII, context managers or `finally` |
| Resource starvation | Unfair or prolonged locking | Workload-aware scheduling and monitoring |

## 14. Security and Production Considerations

Concurrency correctness is also a financial and operational security requirement.

Important controls include:

- Validate all transaction parameters before execution.
- Use fixed-precision decimal values for monetary operations.
- Do not use binary floating-point values for financial accounting.
- Enforce account ownership and authorization independently of locking.
- Apply least-privilege database permissions.
- Use parameterized database operations.
- Keep transactions short.
- Record transaction identifiers and audit events.
- Use durable idempotency keys.
- Define retention periods for idempotency records.
- Monitor long-running transactions.
- Monitor lock waits and deadlocks.
- Avoid exposing sensitive financial information in logs.
- Use bounded retry policies.
- Preserve consistent lock ordering.
- Validate database constraints independently of application checks.

The Python, JavaScript, C++17 and Java 17 examples use integer balances for demonstration. The PostgreSQL implementation uses `NUMERIC(18,2)` to represent decimal monetary values.

The in-memory programs are not distributed transaction coordinators. A real multi-instance service must enforce consistency through shared durable storage or an explicitly designed distributed protocol.

## 15. Testing and Verification

The five implementations use different techniques to verify concurrency correctness.

| Test | Expected behavior |
|---|---|
| Concurrent increments | Protected counter reaches the exact expected value |
| Concurrent transfers | Aggregate balances remain unchanged |
| Insufficient funds | Transaction is rejected |
| Repeated idempotency key | Original result is returned |
| Changed request with same key | Request is rejected |
| Stale version | Optimistic update fails |
| Opposite-direction transfers | Ordered locking prevents circular wait |
| Transaction rollback | Original state is restored |
| Database lock contention | Conflicting sessions wait or fail according to policy |
| Serializable conflict | Transaction can be retried |

A race-condition demonstration is timing-dependent. An unsafe counter may occasionally produce the expected value by chance. The important distinction is that it lacks a correctness guarantee.

For production testing, repeat concurrency tests under different worker counts, transaction volumes, lock durations and failure conditions.

Measure:

- Transaction throughput.
- Average latency.
- High-percentile latency.
- Lock wait duration.
- Deadlock frequency.
- Retry frequency.
- Rejected transaction count.
- Database connection utilization.

## 16. Complexity and Performance

Let:

- \(n\) represent the number of accounts.
- \(k\) represent the number of accounts involved in one transaction.
- \(t\) represent the number of concurrent transactions.

| Operation | Approximate complexity |
|---|---|
| Account lookup in a hash map | Expected O(1) |
| Account lookup in a PostgreSQL indexed key | O(log n) |
| Sorting transaction locks | O(k log k) |
| Acquiring k account locks | O(k) acquisition operations, excluding waiting |
| Balance validation | O(1) |
| Balance update | O(1) |
| Version comparison | O(1) |
| Aggregate balance calculation | O(n) |
| Idempotency lookup | Expected O(1) in hash-based storage; indexed lookup in PostgreSQL |

Actual execution time also depends on contention, storage access, scheduling, database isolation and transaction duration.

A high number of concurrent transactions does not necessarily produce higher throughput. Excessive contention can increase waiting time and reduce useful parallel execution.

## 17. Conceptual Architecture

    Client Request
          |
          v
    Request Validation
          |
          v
    Idempotency Verification
          |
          v
    Transaction Coordinator
          |
          v
    Concurrency Control
          |
          +--------------------+
          |                    |
          v                    v
    Source Account       Destination Account
          |                    |
          +---------+----------+
                    |
                    v
             Integrity Checks
                    |
                    v
             Ledger Recording
                    |
                    v
             Transaction Result
                    |
          +---------+----------+
          |                    |
          v                    v
       Commit               Rollback
          |                    |
          v                    v
    Durable State        Previous State

## 18. Key Technical Distinctions

The following mechanisms address different layers of the problem.

| Concept | Primary responsibility |
|---|---|
| Concurrency | Coordinates overlapping operations |
| Parallelism | Executes operations simultaneously |
| Race condition | Describes timing-dependent incorrect behavior |
| Mutex | Provides exclusive access |
| Deadlock prevention | Avoids circular resource dependencies |
| Transaction | Groups logically related operations |
| ACID | Defines database transaction guarantees |
| Pessimistic locking | Prevents conflicting updates through locks |
| Optimistic locking | Detects conflicting updates through versions |
| Atomic operation | Prevents partial observation of a supported operation |
| Idempotency | Prevents repeated logical requests from executing twice |
| Isolation level | Defines database visibility and conflict behavior |

The central engineering principle is that synchronization must protect the complete business invariant, not merely individual statements.

A correct concurrent system requires coordinated resource access, validated state transitions, reliable failure handling and clearly defined transaction boundaries.
