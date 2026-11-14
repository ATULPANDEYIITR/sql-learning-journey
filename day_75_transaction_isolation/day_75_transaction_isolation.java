import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/*
 * Enterprise Transaction Isolation and Governance Model
 *
 * Java 17
 * No third-party dependencies.
 *
 * Domain components:
 * - Transaction management
 * - MVCC version history
 * - Isolation policies
 * - Optimistic concurrency validation
 * - Serializable conflict detection
 * - Banking transaction service
 * - Audit events
 * - Transaction retry policy
 */

public class TransactionIsolationEnterprise {

    enum IsolationLevel {
        READ_UNCOMMITTED,
        READ_COMMITTED,
        REPEATABLE_READ,
        SERIALIZABLE
    }

    enum TransactionStatus {
        ACTIVE,
        COMMITTED,
        ROLLED_BACK,
        ABORTED
    }

    record Account(
        int id,
        String owner,
        BigDecimal balance
    ) {
        Account {
            if (id <= 0) {
                throw new IllegalArgumentException("Invalid account ID");
            }

            if (owner == null || owner.isBlank()) {
                throw new IllegalArgumentException("Account owner required");
            }

            Objects.requireNonNull(balance, "Balance required");

            if (balance.signum() < 0) {
                throw new IllegalArgumentException("Negative balance");
            }
        }

        Account debit(BigDecimal amount) {
            return new Account(
                id,
                owner,
                balance.subtract(amount)
            );
        }

        Account credit(BigDecimal amount) {
            return new Account(
                id,
                owner,
                balance.add(amount)
            );
        }
    }

    record AuditEvent(
        long transactionId,
        String event,
        Instant timestamp,
        String details
    ) {}

    record RecordKey(String table, int id) {}

    record Version<T>(
        T value,
        long revision,
        boolean committed
    ) {}

    static class TransactionException extends RuntimeException {
        TransactionException(String message) {
            super(message);
        }
    }

    static class WriteConflictException extends TransactionException {
        WriteConflictException(String message) {
            super(message);
        }
    }

    static class SerializationFailureException
        extends TransactionException {

        SerializationFailureException(String message) {
            super(message);
        }
    }

    static class InvalidTransactionException
        extends TransactionException {

        InvalidTransactionException(String message) {
            super(message);
        }
    }

    static class InsufficientFundsException
        extends TransactionException {

        InsufficientFundsException(String message) {
            super(message);
        }
    }

    interface IsolationPolicy {
        boolean useTransactionSnapshot(IsolationLevel level);

        boolean validateWriteConflicts(IsolationLevel level);

        boolean validateReadDependencies(IsolationLevel level);
    }

    static final class StandardIsolationPolicy
        implements IsolationPolicy {

        @Override
        public boolean useTransactionSnapshot(IsolationLevel level) {
            return level == IsolationLevel.REPEATABLE_READ
                || level == IsolationLevel.SERIALIZABLE;
        }

        @Override
        public boolean validateWriteConflicts(IsolationLevel level) {
            return level != IsolationLevel.READ_COMMITTED;
        }

        @Override
        public boolean validateReadDependencies(IsolationLevel level) {
            return level == IsolationLevel.SERIALIZABLE;
        }
    }

    static final class Transaction {

        private final long id;
        private final IsolationLevel isolation;
        private final long snapshot;

        private TransactionStatus status = TransactionStatus.ACTIVE;

        private final Map<RecordKey, Account> writes = new HashMap<>();
        private final Map<RecordKey, Long> reads = new HashMap<>();
        private final Set<String> scannedTables = new HashSet<>();

        Transaction(
            long id,
            IsolationLevel isolation,
            long snapshot
        ) {
            this.id = id;
            this.isolation = isolation;
            this.snapshot = snapshot;
        }

        long id() {
            return id;
        }

        TransactionStatus status() {
            return status;
        }

        IsolationLevel isolation() {
            return isolation;
        }
    }

    static final class Database {

        private final Map<String, Map<Integer, List<Version<Account>>>>
            tables = new HashMap<>();

        private final Map<Long, Transaction> active = new HashMap<>();

        private final List<AuditEvent> audit = new ArrayList<>();

        private final AtomicLong transactionSequence = new AtomicLong(1);

        private long revision = 0;

        private final IsolationPolicy policy =
            new StandardIsolationPolicy();

        void createTable(String name) {
            if (name == null || !name.matches("[a-zA-Z][a-zA-Z0-9_]*")) {
                throw new IllegalArgumentException("Invalid table name");
            }

            if (tables.putIfAbsent(name, new HashMap<>()) != null) {
                throw new IllegalArgumentException("Duplicate table");
            }
        }

        void seed(String table, Account account) {
            Map<Integer, List<Version<Account>>> records =
                requireTable(table);

            if (records.containsKey(account.id())) {
                throw new WriteConflictException("Duplicate account");
            }

            revision++;

            records.put(
                account.id(),
                new ArrayList<>(List.of(
                    new Version<>(account, revision, true)
                ))
            );
        }

        Transaction begin(IsolationLevel isolation) {
            Objects.requireNonNull(isolation);

            long id = transactionSequence.getAndIncrement();

            Transaction transaction = new Transaction(
                id,
                isolation,
                revision
            );

            active.put(id, transaction);

            record(
                transaction,
                "BEGIN",
                "Isolation: " + isolation
            );

            return transaction;
        }

        private Map<Integer, List<Version<Account>>> requireTable(
            String table
        ) {
            Map<Integer, List<Version<Account>>> records =
                tables.get(table);

            if (records == null) {
                throw new IllegalArgumentException(
                    "Unknown table: " + table
                );
            }

            return records;
        }

        private void requireActive(Transaction transaction) {
            if (
                transaction == null ||
                transaction.status != TransactionStatus.ACTIVE ||
                active.get(transaction.id) != transaction
            ) {
                throw new InvalidTransactionException(
                    "Transaction is not active"
                );
            }
        }

        private Optional<Version<Account>> visibleVersion(
            Transaction transaction,
            String table,
            int id
        ) {
            List<Version<Account>> versions =
                requireTable(table).get(id);

            if (versions == null) {
                return Optional.empty();
            }

            return versions.stream()
                .filter(Version::committed)
                .filter(version ->
                    !policy.useTransactionSnapshot(transaction.isolation)
                    || version.revision() <= transaction.snapshot
                )
                .max(Comparator.comparingLong(Version::revision));
        }

        Account read(
            Transaction transaction,
            String table,
            int id
        ) {
            requireActive(transaction);

            RecordKey key = new RecordKey(table, id);

            if (transaction.writes.containsKey(key)) {
                return transaction.writes.get(key);
            }

            Version<Account> version = visibleVersion(
                transaction,
                table,
                id
            ).orElseThrow(() ->
                new TransactionException("Account not found")
            );

            transaction.reads.put(key, version.revision());

            return version.value();
        }

        List<Account> scan(
            Transaction transaction,
            String table,
            BigDecimal minimumBalance
        ) {
            requireActive(transaction);

            transaction.scannedTables.add(table);

            Map<Integer, Account> result = new HashMap<>();

            for (Integer id : requireTable(table).keySet()) {
                try {
                    Account account = read(transaction, table, id);

                    if (
                        account.balance().compareTo(minimumBalance) >= 0
                    ) {
                        result.put(id, account);
                    }
                } catch (TransactionException ignored) {
                    // A record absent from the transaction snapshot is skipped.
                }
            }

            transaction.writes.forEach((key, account) -> {
                if (
                    key.table().equals(table) &&
                    account.balance().compareTo(minimumBalance) >= 0
                ) {
                    result.put(key.id(), account);
                }
            });

            return result.values().stream()
                .sorted(Comparator.comparingInt(Account::id))
                .toList();
        }

        void write(
            Transaction transaction,
            String table,
            Account account
        ) {
            requireActive(transaction);
            requireTable(table);

            transaction.writes.put(
                new RecordKey(table, account.id()),
                account
            );

            record(
                transaction,
                "WRITE_STAGED",
                "Account " + account.id()
            );
        }

        private long latestRevision(String table, int id) {
            List<Version<Account>> versions =
                requireTable(table).get(id);

            if (versions == null) {
                return 0;
            }

            return versions.stream()
                .filter(Version::committed)
                .mapToLong(Version::revision)
                .max()
                .orElse(0);
        }

        private void validate(Transaction transaction) {
            for (RecordKey key : transaction.writes.keySet()) {
                long latest = latestRevision(key.table(), key.id());

                if (
                    policy.validateWriteConflicts(transaction.isolation)
                    && latest > transaction.snapshot
                ) {
                    throw new WriteConflictException(
                        "Concurrent update of account " + key.id()
                    );
                }
            }

            if (
                !policy.validateReadDependencies(transaction.isolation)
            ) {
                return;
            }

            for (Map.Entry<RecordKey, Long> entry :
                transaction.reads.entrySet()) {

                RecordKey key = entry.getKey();

                if (
                    latestRevision(key.table(), key.id())
                    > transaction.snapshot
                ) {
                    throw new SerializationFailureException(
                        "Read-write conflict on account " + key.id()
                    );
                }
            }

            // Conservative predicate validation. A production engine
            // needs index-range or predicate-level dependency tracking.
            for (String table : transaction.scannedTables) {
                boolean changed = requireTable(table).values().stream()
                    .flatMap(List::stream)
                    .anyMatch(version ->
                        version.committed() &&
                        version.revision() > transaction.snapshot
                    );

                if (changed) {
                    throw new SerializationFailureException(
                        "Predicate conflict in " + table
                    );
                }
            }
        }

        void commit(Transaction transaction) {
            requireActive(transaction);

            try {
                validate(transaction);

                revision++;

                for (Map.Entry<RecordKey, Account> entry :
                    transaction.writes.entrySet()) {

                    RecordKey key = entry.getKey();

                    requireTable(key.table())
                        .computeIfAbsent(
                            key.id(),
                            ignored -> new ArrayList<>()
                        )
                        .add(new Version<>(
                            entry.getValue(),
                            revision,
                            true
                        ));
                }

                transaction.status = TransactionStatus.COMMITTED;
                active.remove(transaction.id);

                record(
                    transaction,
                    "COMMIT",
                    "Revision " + revision
                );

            } catch (TransactionException exception) {
                transaction.writes.clear();
                transaction.status = TransactionStatus.ABORTED;
                active.remove(transaction.id);

                record(
                    transaction,
                    "ABORT",
                    exception.getMessage()
                );

                throw exception;
            }
        }

        void rollback(Transaction transaction) {
            requireActive(transaction);

            transaction.writes.clear();
            transaction.status = TransactionStatus.ROLLED_BACK;
            active.remove(transaction.id);

            record(transaction, "ROLLBACK", "Changes discarded");
        }

        Account current(String table, int id) {
            List<Version<Account>> versions =
                requireTable(table).get(id);

            if (versions == null) {
                throw new TransactionException("Account not found");
            }

            return versions.stream()
                .filter(Version::committed)
                .max(Comparator.comparingLong(Version::revision))
                .orElseThrow()
                .value();
        }

        private void record(
            Transaction transaction,
            String event,
            String details
        ) {
            audit.add(new AuditEvent(
                transaction.id,
                event,
                Instant.now(),
                details
            ));
        }

        List<AuditEvent> auditTrail() {
            return Collections.unmodifiableList(audit);
        }
    }

    static final class BankingService {

        private final Database database;

        BankingService(Database database) {
            this.database = Objects.requireNonNull(database);
        }

        void transfer(
            Transaction transaction,
            int sourceId,
            int destinationId,
            BigDecimal amount
        ) {
            if (sourceId == destinationId) {
                throw new IllegalArgumentException(
                    "Source and destination must differ"
                );
            }

            if (amount == null || amount.signum() <= 0) {
                throw new IllegalArgumentException(
                    "Transfer amount must be positive"
                );
            }

            Account source = database.read(
                transaction,
                "accounts",
                sourceId
            );

            Account destination = database.read(
                transaction,
                "accounts",
                destinationId
            );

            if (source.balance().compareTo(amount) < 0) {
                throw new InsufficientFundsException(
                    "Insufficient available balance"
                );
            }

            database.write(
                transaction,
                "accounts",
                source.debit(amount)
            );

            database.write(
                transaction,
                "accounts",
                destination.credit(amount)
            );
        }
    }

    static final class TransactionExecutor {

        private final Database database;
        private final int maximumAttempts;

        TransactionExecutor(Database database, int maximumAttempts) {
            if (maximumAttempts < 1) {
                throw new IllegalArgumentException(
                    "At least one attempt is required"
                );
            }

            this.database = database;
            this.maximumAttempts = maximumAttempts;
        }

        void execute(
            IsolationLevel level,
            java.util.function.Consumer<Transaction> operation
        ) {
            for (int attempt = 1; attempt <= maximumAttempts; attempt++) {
                Transaction transaction = database.begin(level);

                try {
                    operation.accept(transaction);
                    database.commit(transaction);
                    return;

                } catch (WriteConflictException |
                         SerializationFailureException exception) {

                    if (transaction.status == TransactionStatus.ACTIVE) {
                        database.rollback(transaction);
                    }

                    if (attempt == maximumAttempts) {
                        throw exception;
                    }

                    try {
                        Thread.sleep(10L * attempt);
                    } catch (InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                        throw new TransactionException(
                            "Retry interrupted"
                        );
                    }

                } catch (RuntimeException exception) {
                    if (transaction.status == TransactionStatus.ACTIVE) {
                        database.rollback(transaction);
                    }
                    throw exception;
                }
            }
        }
    }

    private static void demonstrateReadCommitted() {
        System.out.println("\n1. READ COMMITTED");

        Database db = new Database();
        db.createTable("accounts");
        db.seed(
            "accounts",
            new Account(1, "Customer A", new BigDecimal("1000"))
        );

        Transaction reader = db.begin(IsolationLevel.READ_COMMITTED);
        Transaction writer = db.begin(IsolationLevel.READ_COMMITTED);

        System.out.println(
            "First read: " + db.read(reader, "accounts", 1).balance()
        );

        db.write(
            writer,
            "accounts",
            db.read(writer, "accounts", 1)
                .credit(new BigDecimal("200"))
        );

        db.commit(writer);

        System.out.println(
            "Second read: " + db.read(reader, "accounts", 1).balance()
        );

        db.rollback(reader);
    }

    private static void demonstrateRepeatableRead() {
        System.out.println("\n2. REPEATABLE READ");

        Database db = new Database();
        db.createTable("accounts");
        db.seed(
            "accounts",
            new Account(1, "Customer A", new BigDecimal("1000"))
        );

        Transaction reader = db.begin(IsolationLevel.REPEATABLE_READ);
        Transaction writer = db.begin(IsolationLevel.READ_COMMITTED);

        System.out.println(
            "First read: " + db.read(reader, "accounts", 1).balance()
        );

        db.write(
            writer,
            "accounts",
            db.read(writer, "accounts", 1)
                .credit(new BigDecimal("500"))
        );

        db.commit(writer);

        System.out.println(
            "Snapshot read: " + db.read(reader, "accounts", 1).balance()
        );

        db.rollback(reader);
    }

    private static void demonstrateReadUncommitted() {
        System.out.println("\n3. READ UNCOMMITTED CONCEPT");

        Database db = new Database();
        db.createTable("accounts");
        db.seed(
            "accounts",
            new Account(1, "Customer A", new BigDecimal("500"))
        );

        Transaction writer = db.begin(IsolationLevel.READ_COMMITTED);
        Transaction reader = db.begin(IsolationLevel.READ_UNCOMMITTED);

        db.write(
            writer,
            "accounts",
            db.read(writer, "accounts", 1)
                .debit(new BigDecimal("100"))
        );

        System.out.println(
            "Dirty read prevented: "
                + db.read(reader, "accounts", 1).balance()
        );

        db.rollback(writer);
        db.rollback(reader);
    }

    private static void demonstrateSerializable() {
        System.out.println("\n4. SERIALIZABLE");

        Database db = new Database();
        db.createTable("accounts");
        db.seed(
            "accounts",
            new Account(1, "Customer A", new BigDecimal("1000"))
        );

        Transaction first = db.begin(IsolationLevel.SERIALIZABLE);
        Transaction second = db.begin(IsolationLevel.READ_COMMITTED);

        db.read(first, "accounts", 1);

        db.write(
            second,
            "accounts",
            db.read(second, "accounts", 1)
                .credit(new BigDecimal("100"))
        );

        db.commit(second);

        try {
            db.commit(first);
        } catch (SerializationFailureException exception) {
            System.out.println(
                "Expected serialization failure: " + exception.getMessage()
            );
        }
    }

    private static void demonstrateBankingWorkflow() {
        System.out.println("\n5. ENTERPRISE BANKING WORKFLOW");

        Database db = new Database();
        db.createTable("accounts");

        db.seed(
            "accounts",
            new Account(101, "Customer A", new BigDecimal("5000"))
        );

        db.seed(
            "accounts",
            new Account(102, "Customer B", new BigDecimal("3000"))
        );

        BankingService service = new BankingService(db);

        TransactionExecutor executor =
            new TransactionExecutor(db, 3);

        executor.execute(
            IsolationLevel.SERIALIZABLE,
            transaction -> service.transfer(
                transaction,
                101,
                102,
                new BigDecimal("750")
            )
        );

        System.out.println("Source: " + db.current("accounts", 101));
        System.out.println("Destination: " + db.current("accounts", 102));

        System.out.println("\nAudit events:");

        db.auditTrail().forEach(event ->
            System.out.println(
                event.transactionId() + " | " +
                event.event() + " | " +
                event.details()
            )
        );
    }

    private static void demonstrateInsufficientFunds() {
        System.out.println("\n6. FAILURE HANDLING");

        Database db = new Database();
        db.createTable("accounts");

        db.seed(
            "accounts",
            new Account(1, "Customer A", new BigDecimal("100"))
        );

        db.seed(
            "accounts",
            new Account(2, "Customer B", new BigDecimal("100"))
        );

        BankingService service = new BankingService(db);
        Transaction transaction = db.begin(IsolationLevel.SERIALIZABLE);

        try {
            service.transfer(
                transaction,
                1,
                2,
                new BigDecimal("500")
            );

            db.commit(transaction);

        } catch (TransactionException exception) {
            if (transaction.status == TransactionStatus.ACTIVE) {
                db.rollback(transaction);
            }

            System.out.println("Rejected: " + exception.getMessage());
        }

        System.out.println(
            "Balance remains: " + db.current("accounts", 1).balance()
        );
    }

    public static void main(String[] args) {
        demonstrateReadCommitted();
        demonstrateRepeatableRead();
        demonstrateReadUncommitted();
        demonstrateSerializable();
        demonstrateBankingWorkflow();
        demonstrateInsufficientFunds();
    }
}
