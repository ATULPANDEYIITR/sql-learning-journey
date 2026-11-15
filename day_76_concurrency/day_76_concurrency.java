import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantLock;
import java.util.stream.IntStream;

/**
 * Enterprise Concurrency and Transaction Management.
 *
 * Java 17 implementation:
 * - ReentrantLock
 * - ConcurrentHashMap
 * - ExecutorService
 * - Immutable records
 * - Domain-specific exceptions
 * - Deadlock prevention
 * - Transaction rollback
 * - Idempotency
 * - Optimistic concurrency control
 * - Explicit merge-free transactional state transitions
 */
public class ConcurrencyManagement {

    enum TransactionStatus {
        COMMITTED,
        REJECTED,
        ROLLED_BACK
    }

    record TransactionResult(
        String transactionId,
        TransactionStatus status,
        String sourceId,
        String destinationId,
        long amount,
        String message
    ) {}

    record AccountSnapshot(
        String accountId,
        long balance,
        long version
    ) {}

    record TransferRequest(
        String sourceId,
        String destinationId,
        long amount,
        String idempotencyKey
    ) {
        TransferRequest {
            Objects.requireNonNull(sourceId);
            Objects.requireNonNull(destinationId);
            Objects.requireNonNull(idempotencyKey);

            if (sourceId.isBlank() || destinationId.isBlank()) {
                throw new IllegalArgumentException(
                    "Account identifiers cannot be blank"
                );
            }

            if (sourceId.equals(destinationId)) {
                throw new IllegalArgumentException(
                    "Source and destination must differ"
                );
            }

            if (amount <= 0) {
                throw new IllegalArgumentException(
                    "Transfer amount must be positive"
                );
            }

            if (idempotencyKey.isBlank()) {
                throw new IllegalArgumentException(
                    "Idempotency key cannot be blank"
                );
            }
        }
    }


    static class TransactionException extends RuntimeException {
        TransactionException(String message) {
            super(message);
        }
    }

    static class InsufficientFundsException
            extends TransactionException {

        InsufficientFundsException() {
            super("Insufficient funds");
        }
    }

    static class OptimisticLockException
            extends TransactionException {

        OptimisticLockException() {
            super("Concurrent modification detected");
        }
    }

    static class DuplicateRequestException
            extends TransactionException {

        DuplicateRequestException() {
            super("Idempotency key reused with different parameters");
        }
    }


    /**
     * Encapsulates account state and its exclusive lock.
     */
    static final class Account {
        private final String id;
        private final ReentrantLock lock = new ReentrantLock(true);

        private long balance;
        private long version;

        Account(String id, long balance) {
            if (id == null || id.isBlank()) {
                throw new IllegalArgumentException(
                    "Invalid account ID"
                );
            }

            if (balance < 0) {
                throw new IllegalArgumentException(
                    "Initial balance cannot be negative"
                );
            }

            this.id = id;
            this.balance = balance;
            this.version = 0;
        }

        AccountSnapshot snapshot() {
            lock.lock();

            try {
                return new AccountSnapshot(
                    id,
                    balance,
                    version
                );
            } finally {
                lock.unlock();
            }
        }
    }


    /**
     * Idempotency entries preserve the original request fingerprint.
     */
    record IdempotencyEntry(
        TransferRequest request,
        TransactionResult result
    ) {}


    static final class TransactionService {

        private final Map<String, Account> accounts =
            new ConcurrentHashMap<>();

        private final Map<String, IdempotencyEntry> processed =
            new HashMap<>();

        private final ReentrantLock transactionLock =
            new ReentrantLock(true);

        private final AtomicLong sequence = new AtomicLong();


        public void createAccount(String id, long balance) {
            Account account = new Account(id, balance);

            Account previous = accounts.putIfAbsent(id, account);

            if (previous != null) {
                throw new TransactionException(
                    "Account already exists: " + id
                );
            }
        }


        private Account getAccount(String id) {
            Account account = accounts.get(id);

            if (account == null) {
                throw new TransactionException(
                    "Account not found: " + id
                );
            }

            return account;
        }


        /**
         * All transaction locks are acquired in deterministic order.
         *
         * The global transaction lock protects idempotency records.
         * Account locks protect the actual balance changes.
         */
        public TransactionResult transfer(TransferRequest request) {

            Objects.requireNonNull(request);

            transactionLock.lock();

            try {
                IdempotencyEntry existing =
                    processed.get(request.idempotencyKey());

                if (existing != null) {
                    if (!existing.request().equals(request)) {
                        throw new DuplicateRequestException();
                    }

                    return existing.result();
                }

                Account source = getAccount(request.sourceId());
                Account destination =
                    getAccount(request.destinationId());

                List<Account> ordered = new ArrayList<>(
                    List.of(source, destination)
                );

                ordered.sort(
                    Comparator.comparing(account -> account.id)
                );

                ordered.get(0).lock.lock();
                ordered.get(1).lock.lock();

                try {
                    if (source.balance < request.amount()) {
                        TransactionResult rejected =
                            new TransactionResult(
                                UUID.randomUUID().toString(),
                                TransactionStatus.REJECTED,
                                source.id,
                                destination.id,
                                request.amount(),
                                "Insufficient funds"
                            );

                        processed.put(
                            request.idempotencyKey(),
                            new IdempotencyEntry(request, rejected)
                        );

                        return rejected;
                    }

                    if (
                        destination.balance >
                        Long.MAX_VALUE - request.amount()
                    ) {
                        throw new TransactionException(
                            "Destination balance overflow"
                        );
                    }

                    long oldSource = source.balance;
                    long oldDestination = destination.balance;

                    try {
                        source.balance -= request.amount();
                        destination.balance += request.amount();

                        source.version++;
                        destination.version++;

                        if (source.balance < 0) {
                            throw new TransactionException(
                                "Balance invariant violated"
                            );
                        }

                    } catch (RuntimeException error) {
                        source.balance = oldSource;
                        destination.balance = oldDestination;
                        throw error;
                    }

                    TransactionResult committed =
                        new TransactionResult(
                            UUID.randomUUID().toString(),
                            TransactionStatus.COMMITTED,
                            source.id,
                            destination.id,
                            request.amount(),
                            "Transaction committed"
                        );

                    processed.put(
                        request.idempotencyKey(),
                        new IdempotencyEntry(request, committed)
                    );

                    sequence.incrementAndGet();

                    return committed;

                } finally {
                    ordered.get(1).lock.unlock();
                    ordered.get(0).lock.unlock();
                }

            } finally {
                transactionLock.unlock();
            }
        }


        public AccountSnapshot getAccountSnapshot(String id) {
            return getAccount(id).snapshot();
        }


        public long totalBalance() {
            List<Account> ordered = accounts.values()
                .stream()
                .sorted(Comparator.comparing(account -> account.id))
                .toList();

            for (Account account : ordered) {
                account.lock.lock();
            }

            try {
                long total = 0;

                for (Account account : ordered) {
                    total = Math.addExact(total, account.balance);
                }

                return total;

            } finally {
                for (int i = ordered.size() - 1; i >= 0; i--) {
                    ordered.get(i).lock.unlock();
                }
            }
        }
    }


    /**
     * Optimistic locking uses a version number instead of
     * holding an exclusive lock throughout a longer workflow.
     */
    static final class VersionedAccount {

        private long balance;
        private long version;

        synchronized AccountSnapshot read() {
            return new AccountSnapshot(
                "VERSIONED",
                balance,
                version
            );
        }

        VersionedAccount(long initialBalance) {
            if (initialBalance < 0) {
                throw new IllegalArgumentException(
                    "Invalid initial balance"
                );
            }

            balance = initialBalance;
        }

        synchronized AccountSnapshot compareAndSet(
            long expectedVersion,
            long newBalance
        ) {
            if (newBalance < 0) {
                throw new IllegalArgumentException(
                    "Balance cannot be negative"
                );
            }

            if (version != expectedVersion) {
                throw new OptimisticLockException();
            }

            balance = newBalance;
            version++;

            return read();
        }
    }


    /**
     * Demonstrates the lost-update problem using concurrent tasks.
     */
    static void demonstrateRaceCondition() throws Exception {

        System.out.println("\n--- Race Condition ---");

        class UnsafeCounter {
            int value;

            void increment() {
                int current = value;

                Thread.yield();

                value = current + 1;
            }
        }

        UnsafeCounter unsafe = new UnsafeCounter();

        class SafeCounter {
            private int value;

            synchronized void increment() {
                value++;
            }

            synchronized int getValue() {
                return value;
            }
        }

        SafeCounter safe = new SafeCounter();

        ExecutorService executor =
            Executors.newFixedThreadPool(12);

        try {
            List<Callable<Void>> tasks = IntStream.range(0, 1000)
                .mapToObj(index -> (Callable<Void>) () -> {
                    unsafe.increment();
                    safe.increment();
                    return null;
                })
                .toList();

            List<Future<Void>> futures = executor.invokeAll(tasks);

            for (Future<Void> future : futures) {
                future.get();
            }

            System.out.println("Unsafe counter: " + unsafe.value);
            System.out.println("Safe counter: " + safe.getValue());

            if (safe.getValue() != 1000) {
                throw new TransactionException(
                    "Safe counter invariant failed"
                );
            }

        } finally {
            executor.shutdown();
        }
    }


    static void demonstrateConcurrentTransactions() throws Exception {

        System.out.println("\n--- Concurrent Transactions ---");

        TransactionService service = new TransactionService();

        service.createAccount("A", 100000);
        service.createAccount("B", 100000);
        service.createAccount("C", 50000);

        long initial = service.totalBalance();

        ExecutorService executor =
            Executors.newFixedThreadPool(20);

        try {
            List<Callable<TransactionResult>> tasks =
                IntStream.range(0, 500)
                    .mapToObj(index ->
                        (Callable<TransactionResult>) () -> {

                            TransferRequest request;

                            if (index % 2 == 0) {
                                request = new TransferRequest(
                                    "A",
                                    "B",
                                    10,
                                    "TX-" + index
                                );
                            } else {
                                request = new TransferRequest(
                                    "B",
                                    "A",
                                    10,
                                    "TX-" + index
                                );
                            }

                            return service.transfer(request);
                        }
                    )
                    .toList();

            List<Future<TransactionResult>> futures =
                executor.invokeAll(tasks);

            long committed = 0;

            for (Future<TransactionResult> future : futures) {
                if (
                    future.get().status() ==
                    TransactionStatus.COMMITTED
                ) {
                    committed++;
                }
            }

            long finalTotal = service.totalBalance();

            System.out.println("Committed: " + committed);
            System.out.println("Initial total: " + initial);
            System.out.println("Final total: " + finalTotal);

            System.out.println(service.getAccountSnapshot("A"));
            System.out.println(service.getAccountSnapshot("B"));
            System.out.println(service.getAccountSnapshot("C"));

            if (initial != finalTotal) {
                throw new TransactionException(
                    "Balance conservation violated"
                );
            }

        } finally {
            executor.shutdown();
        }
    }


    static void demonstrateIdempotency() {

        System.out.println("\n--- Idempotency ---");

        TransactionService service = new TransactionService();

        service.createAccount("SOURCE", 1000);
        service.createAccount("TARGET", 500);

        TransferRequest request = new TransferRequest(
            "SOURCE",
            "TARGET",
            100,
            "PAYMENT-001"
        );

        TransactionResult first = service.transfer(request);
        TransactionResult second = service.transfer(request);

        System.out.println("First: " + first.transactionId());
        System.out.println("Second: " + second.transactionId());

        if (
            !first.transactionId().equals(second.transactionId())
        ) {
            throw new TransactionException(
                "Duplicate transaction was executed"
            );
        }

        System.out.println(service.getAccountSnapshot("SOURCE"));
        System.out.println(service.getAccountSnapshot("TARGET"));

        try {
            service.transfer(
                new TransferRequest(
                    "SOURCE",
                    "TARGET",
                    200,
                    "PAYMENT-001"
                )
            );
        } catch (DuplicateRequestException error) {
            System.out.println("Key reuse rejected: " + error.getMessage());
        }
    }


    static void demonstrateOptimisticLocking() {

        System.out.println("\n--- Optimistic Locking ---");

        VersionedAccount account = new VersionedAccount(1000);

        AccountSnapshot first = account.read();
        AccountSnapshot second = account.read();

        account.compareAndSet(first.version(), 1200);

        try {
            account.compareAndSet(second.version(), 1500);
        } catch (OptimisticLockException error) {
            System.out.println("Stale write rejected: " + error.getMessage());
        }

        System.out.println(account.read());
    }


    static void demonstrateDeadlockPrevention() throws Exception {

        System.out.println("\n--- Deadlock Prevention ---");

        TransactionService service = new TransactionService();

        service.createAccount("LEFT", 10000);
        service.createAccount("RIGHT", 10000);

        ExecutorService executor =
            Executors.newFixedThreadPool(10);

        try {
            List<Callable<TransactionResult>> tasks =
                new ArrayList<>();

            for (int i = 0; i < 100; i++) {
                final int index = i;

                tasks.add(() -> service.transfer(
                    new TransferRequest(
                        "LEFT",
                        "RIGHT",
                        1,
                        "FORWARD-" + index
                    )
                ));

                tasks.add(() -> service.transfer(
                    new TransferRequest(
                        "RIGHT",
                        "LEFT",
                        1,
                        "REVERSE-" + index
                    )
                ));
            }

            List<Future<TransactionResult>> results =
                executor.invokeAll(tasks);

            for (Future<TransactionResult> result : results) {
                result.get();
            }

            System.out.println(
                service.getAccountSnapshot("LEFT")
            );

            System.out.println(
                service.getAccountSnapshot("RIGHT")
            );

            if (service.totalBalance() != 20000) {
                throw new TransactionException(
                    "Balance invariant violated"
                );
            }

        } finally {
            executor.shutdown();
        }
    }


    public static void main(String[] args) {

        System.out.println(
            "ENTERPRISE CONCURRENCY MANAGEMENT SYSTEM"
        );

        try {
            demonstrateRaceCondition();
            demonstrateConcurrentTransactions();
            demonstrateIdempotency();
            demonstrateOptimisticLocking();
            demonstrateDeadlockPrevention();

            System.out.println(
                "\nAll concurrency checks completed."
            );

        } catch (Exception error) {
            System.err.println(
                "Execution failed: " + error.getMessage()
            );

            error.printStackTrace();
            System.exit(1);
        }
    }
}
