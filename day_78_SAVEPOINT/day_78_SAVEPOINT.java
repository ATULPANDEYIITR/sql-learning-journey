import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.function.Function;

/*
 * SAVEPOINT: Partial Rollback and Nested Transaction Patterns
 *
 * Java 17 enterprise transaction-management simulation.
 *
 * Demonstrates:
 * - Explicit transaction lifecycle
 * - Savepoint-based partial rollback
 * - Nested transaction scopes
 * - Transaction policy objects
 * - Domain validation
 * - Immutable audit events
 * - Optimistic concurrency control
 * - Commit and rollback services
 *
 * Compile:
 * javac SavepointDemo.java
 *
 * Run:
 * java SavepointDemo
 */

public class SavepointDemo {

    enum TransactionStatus {
        ACTIVE,
        COMMITTED,
        ROLLED_BACK
    }

    enum OrderStatus {
        CONFIRMED,
        CANCELLED
    }

    static class TransactionException extends RuntimeException {
        TransactionException(String message) {
            super(message);
        }
    }

    static class SavepointNotFoundException
            extends TransactionException {
        SavepointNotFoundException(String name) {
            super("Savepoint not found: " + name);
        }
    }

    static class InsufficientInventoryException
            extends TransactionException {
        InsufficientInventoryException() {
            super("Insufficient inventory.");
        }
    }

    static class InsufficientFundsException
            extends TransactionException {
        InsufficientFundsException() {
            super("Insufficient account balance.");
        }
    }

    static class ConcurrencyConflictException
            extends TransactionException {
        ConcurrencyConflictException() {
            super("Concurrent transaction modified the repository.");
        }
    }

    record Product(
            int id,
            String name,
            int stock,
            BigDecimal price
    ) {
        Product {
            if (id <= 0 || stock < 0) {
                throw new IllegalArgumentException(
                        "Invalid product identity or stock."
                );
            }

            Objects.requireNonNull(name);
            Objects.requireNonNull(price);

            if (name.isBlank() || price.signum() <= 0) {
                throw new IllegalArgumentException(
                        "Invalid product attributes."
                );
            }

            price = price.setScale(2, RoundingMode.UNNECESSARY);
        }

        Product withStock(int newStock) {
            return new Product(id, name, newStock, price);
        }
    }

    record Account(
            int id,
            String owner,
            BigDecimal balance
    ) {
        Account {
            if (id <= 0) {
                throw new IllegalArgumentException(
                        "Invalid account ID."
                );
            }

            Objects.requireNonNull(owner);
            Objects.requireNonNull(balance);

            if (owner.isBlank() || balance.signum() < 0) {
                throw new IllegalArgumentException(
                        "Invalid account details."
                );
            }

            balance = balance.setScale(
                    2, RoundingMode.UNNECESSARY
            );
        }

        Account debit(BigDecimal amount) {
            return new Account(
                    id,
                    owner,
                    balance.subtract(amount)
            );
        }
    }

    record Order(
            int id,
            int accountId,
            int productId,
            int quantity,
            BigDecimal amount,
            OrderStatus status
    ) {
        Order {
            if (id <= 0 || accountId <= 0 ||
                    productId <= 0 || quantity <= 0) {
                throw new IllegalArgumentException(
                        "Invalid order attributes."
                );
            }

            Objects.requireNonNull(amount);
            Objects.requireNonNull(status);
        }
    }

    record AuditEvent(
            UUID eventId,
            UUID transactionId,
            String operation,
            String details,
            Instant timestamp
    ) {}

    record TransactionPolicy(
            boolean allowNestedScopes,
            int maximumSavepoints,
            boolean requireOptimisticVersion
    ) {
        TransactionPolicy {
            if (maximumSavepoints < 1 ||
                    maximumSavepoints > 1000) {
                throw new IllegalArgumentException(
                        "Invalid savepoint limit."
                );
            }
        }

        static TransactionPolicy enterpriseDefault() {
            return new TransactionPolicy(true, 100, true);
        }
    }

    static final class DatabaseState {
        final Map<Integer, Product> products;
        final Map<Integer, Account> accounts;
        final Map<Integer, Order> orders;
        int nextOrderId;

        DatabaseState(
                Map<Integer, Product> products,
                Map<Integer, Account> accounts,
                Map<Integer, Order> orders,
                int nextOrderId
        ) {
            this.products = new HashMap<>(products);
            this.accounts = new HashMap<>(accounts);
            this.orders = new HashMap<>(orders);
            this.nextOrderId = nextOrderId;
        }

        DatabaseState copy() {
            return new DatabaseState(
                    products,
                    accounts,
                    orders,
                    nextOrderId
            );
        }
    }

    static final class Repository {
        private DatabaseState committed;
        private long version;

        Repository() {
            Map<Integer, Product> products = Map.of(
                    101, new Product(
                            101,
                            "Enterprise Laptop",
                            10,
                            new BigDecimal("75000.00")
                    ),
                    102, new Product(
                            102,
                            "Wireless Keyboard",
                            20,
                            new BigDecimal("2500.00")
                    ),
                    103, new Product(
                            103,
                            "External SSD",
                            5,
                            new BigDecimal("6500.00")
                    )
            );

            Map<Integer, Account> accounts = Map.of(
                    1, new Account(
                            1,
                            "Corporate Procurement",
                            new BigDecimal("200000.00")
                    ),
                    2, new Account(
                            2,
                            "Regional Procurement",
                            new BigDecimal("10000.00")
                    )
            );

            committed = new DatabaseState(
                    products,
                    accounts,
                    Map.of(),
                    1
            );
        }

        synchronized Snapshot snapshot() {
            return new Snapshot(version, committed.copy());
        }

        synchronized void commit(
                long expectedVersion,
                DatabaseState newState
        ) {
            if (version != expectedVersion) {
                throw new ConcurrencyConflictException();
            }

            committed = newState.copy();
            version++;
        }

        synchronized DatabaseState read() {
            return committed.copy();
        }

        synchronized long version() {
            return version;
        }
    }

    record Snapshot(long version, DatabaseState state) {}

    static final class Savepoint {
        private final String name;
        private final DatabaseState snapshot;

        Savepoint(String name, DatabaseState snapshot) {
            this.name = name;
            this.snapshot = snapshot.copy();
        }
    }

    static final class Transaction {
        private final Repository repository;
        private final TransactionPolicy policy;
        private final UUID id = UUID.randomUUID();
        private final long baseVersion;

        private DatabaseState workingState;
        private final List<Savepoint> savepoints =
                new ArrayList<>();

        private final List<AuditEvent> auditEvents =
                new ArrayList<>();

        private TransactionStatus status =
                TransactionStatus.ACTIVE;

        Transaction(
                Repository repository,
                TransactionPolicy policy
        ) {
            this.repository = repository;
            this.policy = policy;

            Snapshot snapshot = repository.snapshot();

            this.baseVersion = snapshot.version();
            this.workingState = snapshot.state();
        }

        private void ensureActive() {
            if (status != TransactionStatus.ACTIVE) {
                throw new TransactionException(
                        "Transaction is " + status
                );
            }
        }

        private void record(String operation, String details) {
            auditEvents.add(new AuditEvent(
                    UUID.randomUUID(),
                    id,
                    operation,
                    details,
                    Instant.now()
            ));
        }

        void createSavepoint(String name) {
            ensureActive();

            if (name == null ||
                    !name.matches("[A-Za-z_][A-Za-z0-9_]{0,62}")) {
                throw new IllegalArgumentException(
                        "Invalid savepoint name."
                );
            }

            if (savepoints.size() >= policy.maximumSavepoints()) {
                throw new TransactionException(
                        "Savepoint limit exceeded."
                );
            }

            savepoints.add(
                    new Savepoint(name, workingState)
            );

            record("SAVEPOINT", name);
        }

        private int findSavepoint(String name) {
            for (int i = savepoints.size() - 1; i >= 0; i--) {
                if (savepoints.get(i).name.equals(name)) {
                    return i;
                }
            }

            throw new SavepointNotFoundException(name);
        }

        void rollbackTo(String name) {
            ensureActive();

            int index = findSavepoint(name);

            workingState = savepoints.get(index).snapshot.copy();

            savepoints.subList(
                    index + 1,
                    savepoints.size()
            ).clear();

            record("ROLLBACK_TO", name);
        }

        void release(String name) {
            ensureActive();

            int index = findSavepoint(name);

            savepoints.subList(
                    index,
                    savepoints.size()
            ).clear();

            record("RELEASE", name);
        }

        Order createOrder(
                int accountId,
                int productId,
                int quantity
        ) {
            ensureActive();

            if (quantity <= 0) {
                throw new IllegalArgumentException(
                        "Quantity must be positive."
                );
            }

            Account account =
                    workingState.accounts.get(accountId);

            Product product =
                    workingState.products.get(productId);

            if (account == null || product == null) {
                throw new TransactionException(
                        "Account or product does not exist."
                );
            }

            if (product.stock() < quantity) {
                throw new InsufficientInventoryException();
            }

            BigDecimal amount = product.price().multiply(
                    BigDecimal.valueOf(quantity)
            );

            if (account.balance().compareTo(amount) < 0) {
                throw new InsufficientFundsException();
            }

            workingState.products.put(
                    productId,
                    product.withStock(product.stock() - quantity)
            );

            workingState.accounts.put(
                    accountId,
                    account.debit(amount)
            );

            Order order = new Order(
                    workingState.nextOrderId++,
                    accountId,
                    productId,
                    quantity,
                    amount,
                    OrderStatus.CONFIRMED
            );

            workingState.orders.put(order.id(), order);

            record(
                    "ORDER_CREATED",
                    "Order " + order.id()
            );

            return order;
        }

        void commit() {
            ensureActive();

            repository.commit(
                    baseVersion,
                    workingState
            );

            savepoints.clear();
            status = TransactionStatus.COMMITTED;

            record("COMMIT", "Transaction committed");
        }

        void rollback() {
            ensureActive();

            savepoints.clear();
            status = TransactionStatus.ROLLED_BACK;

            record("ROLLBACK", "Transaction rolled back");
        }

        TransactionStatus status() {
            return status;
        }

        List<AuditEvent> auditEvents() {
            return Collections.unmodifiableList(
                    auditEvents
            );
        }

        DatabaseState view() {
            return workingState.copy();
        }
    }

    static final class TransactionService {
        private final Repository repository;
        private final TransactionPolicy policy;

        TransactionService(
                Repository repository,
                TransactionPolicy policy
        ) {
            this.repository = repository;
            this.policy = policy;
        }

        <T> T execute(
                Function<Transaction, T> operation
        ) {
            Transaction transaction =
                    new Transaction(repository, policy);

            try {
                T result = operation.apply(transaction);
                transaction.commit();
                return result;
            } catch (RuntimeException exception) {
                if (transaction.status() ==
                        TransactionStatus.ACTIVE) {
                    transaction.rollback();
                }

                throw exception;
            }
        }

        <T> T executeNested(
                Transaction transaction,
                String savepoint,
                Function<Transaction, T> operation
        ) {
            if (!policy.allowNestedScopes()) {
                throw new TransactionException(
                        "Nested scopes are disabled."
                );
            }

            transaction.createSavepoint(savepoint);

            try {
                T result = operation.apply(transaction);
                transaction.release(savepoint);
                return result;
            } catch (RuntimeException exception) {
                transaction.rollbackTo(savepoint);
                throw exception;
            }
        }
    }

    private static void demonstratePartialRollback(
            TransactionService service
    ) {
        System.out.println("\n1. PARTIAL ROLLBACK");

        service.execute(tx -> {
            tx.createSavepoint("optional_phase");

            Order first = tx.createOrder(1, 101, 1);

            System.out.println("Confirmed order: " + first.id());

            try {
                service.executeNested(
                        tx,
                        "optional_items",
                        inner -> {
                            inner.createOrder(1, 103, 1);
                            inner.createOrder(1, 103, 100);
                            return null;
                        }
                );
            } catch (InsufficientInventoryException error) {
                System.out.println(
                        "Optional phase rejected: " +
                        error.getMessage()
                );
            }

            System.out.println(
                    "Retained orders: " +
                    tx.view().orders.size()
            );

            return null;
        });
    }

    private static void demonstrateNestedSuccess(
            TransactionService service
    ) {
        System.out.println("\n2. SUCCESSFUL NESTED SCOPE");

        service.execute(tx -> {
            tx.createOrder(1, 102, 2);

            service.executeNested(
                    tx,
                    "optional_service",
                    inner -> inner.createOrder(1, 103, 1)
            );

            return null;
        });
    }

    private static void demonstrateFullRollback(
            Repository repository,
            TransactionPolicy policy
    ) {
        System.out.println("\n3. FULL ROLLBACK");

        Transaction tx = new Transaction(repository, policy);

        tx.createOrder(1, 102, 1);
        tx.rollback();

        System.out.println("Status: " + tx.status());
    }

    private static void demonstrateConcurrency(
            Repository repository,
            TransactionPolicy policy
    ) {
        System.out.println("\n4. CONCURRENCY CONTROL");

        Transaction first = new Transaction(repository, policy);
        Transaction second = new Transaction(repository, policy);

        first.createOrder(1, 102, 1);
        second.createOrder(1, 102, 1);

        first.commit();

        try {
            second.commit();
        } catch (ConcurrencyConflictException error) {
            System.out.println(
                    "Conflict detected: " + error.getMessage()
            );

            second.rollback();
        }
    }

    public static void main(String[] args) {
        Repository repository = new Repository();

        TransactionPolicy policy =
                TransactionPolicy.enterpriseDefault();

        TransactionService service =
                new TransactionService(repository, policy);

        demonstratePartialRollback(service);
        demonstrateNestedSuccess(service);

        demonstrateFullRollback(repository, policy);
        demonstrateConcurrency(repository, policy);

        DatabaseState finalState = repository.read();

        System.out.println("\nFINAL REPOSITORY STATE");

        System.out.println(
                "Version: " + repository.version()
        );

        finalState.products.values().forEach(product ->
                System.out.println(
                        product.name() +
                        " | stock=" + product.stock()
                )
        );

        finalState.accounts.values().forEach(account ->
                System.out.println(
                        account.owner() +
                        " | balance=" + account.balance()
                )
        );

        System.out.println(
                "Committed orders: " + finalState.orders.size()
        );

        System.out.println("\nALL OPERATIONS COMPLETED");
    }
}
