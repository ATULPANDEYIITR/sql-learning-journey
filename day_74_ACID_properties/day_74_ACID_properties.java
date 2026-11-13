import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.locks.ReentrantLock;
import java.util.stream.Collectors;

/**
 * ACID Properties: Enterprise Transaction Management.
 *
 * Java 17 implementation featuring:
 * - Explicit domain records and interfaces.
 * - Immutable transaction commands.
 * - Account and transaction state management.
 * - Policy-based validation.
 * - Optimistic concurrency control.
 * - Atomic commit coordination.
 * - Durable journal abstraction.
 * - Idempotent transaction requests.
 * - Enterprise-style reporting.
 *
 * Run: javac AcidProperties.java && java AcidProperties
 */
public class AcidProperties {

    enum TransactionStatus {
        ACTIVE,
        COMMITTED,
        ROLLED_BACK,
        FAILED
    }

    enum IsolationLevel {
        READ_COMMITTED,
        REPEATABLE_READ,
        SERIALIZABLE
    }

    enum OperationType {
        DEPOSIT,
        WITHDRAWAL,
        TRANSFER
    }

    static class TransactionException extends RuntimeException {
        TransactionException(String message) {
            super(message);
        }
    }

    static class ConstraintException extends TransactionException {
        ConstraintException(String message) {
            super(message);
        }
    }

    static class ConcurrencyException extends TransactionException {
        ConcurrencyException(String message) {
            super(message);
        }
    }

    static class DurabilityException extends TransactionException {
        DurabilityException(String message) {
            super(message);
        }
    }

    record AccountSnapshot(
        int accountId,
        String owner,
        long balance,
        long version,
        boolean active
    ) {}

    record TransactionCommand(
        String transactionId,
        String idempotencyKey,
        OperationType type,
        int sourceId,
        int targetId,
        long amount
    ) {
        TransactionCommand {
            Objects.requireNonNull(transactionId);
            Objects.requireNonNull(type);

            if (amount <= 0) {
                throw new ConstraintException("Amount must be positive");
            }
        }
    }

    record CommitRecord(
        String transactionId,
        Map<Integer, Long> balances,
        String description
    ) {
        CommitRecord {
            balances = Collections.unmodifiableMap(
                new LinkedHashMap<>(balances)
            );
        }
    }

    interface Journal {
        void append(CommitRecord record);

        List<CommitRecord> records();
    }

    interface AccountPolicy {
        void validate(AccountSnapshot account);
    }

    static final class StandardAccountPolicy implements AccountPolicy {
        private static final long MAX_BALANCE = 9_000_000_000_000_000L;

        @Override
        public void validate(AccountSnapshot account) {
            if (account.accountId() <= 0) {
                throw new ConstraintException("Invalid account ID");
            }

            if (account.owner() == null || account.owner().isBlank()) {
                throw new ConstraintException("Owner is required");
            }

            if (
                account.balance() < 0 ||
                account.balance() > MAX_BALANCE
            ) {
                throw new ConstraintException("Invalid balance");
            }

            if (!account.active()) {
                throw new ConstraintException("Account is inactive");
            }
        }
    }

    static final class InMemoryJournal implements Journal {
        private final List<CommitRecord> records = new ArrayList<>();
        private boolean available = true;

        @Override
        public synchronized void append(CommitRecord record) {
            if (!available) {
                throw new DurabilityException(
                    "Durable journal is unavailable"
                );
            }

            records.add(record);
        }

        @Override
        public synchronized List<CommitRecord> records() {
            return List.copyOf(records);
        }

        void setAvailable(boolean available) {
            this.available = available;
        }
    }

    static final class Account {
        private final int id;
        private final String owner;
        private long balance;
        private long version;
        private boolean active;

        Account(int id, String owner, long balance) {
            this.id = id;
            this.owner = owner;
            this.balance = balance;
            this.version = 0;
            this.active = true;
        }

        AccountSnapshot snapshot() {
            return new AccountSnapshot(
                id, owner, balance, version, active
            );
        }
    }

    static final class Transaction {
        private final TransactionService service;
        private final String id;
        private final IsolationLevel isolation;

        private final Map<Integer, Long> stagedBalances =
            new LinkedHashMap<>();

        private final Map<Integer, Long> readVersions =
            new HashMap<>();

        private final Map<Integer, Long> writeVersions =
            new HashMap<>();

        private final List<TransactionCommand> commands =
            new ArrayList<>();

        private TransactionStatus status = TransactionStatus.ACTIVE;

        Transaction(
            TransactionService service,
            IsolationLevel isolation
        ) {
            this.service = service;
            this.id = UUID.randomUUID().toString();
            this.isolation = isolation;
        }

        private void requireActive() {
            if (status != TransactionStatus.ACTIVE) {
                throw new TransactionException(
                    "Transaction is " + status
                );
            }
        }

        public long read(int accountId) {
            requireActive();

            if (stagedBalances.containsKey(accountId)) {
                return stagedBalances.get(accountId);
            }

            Account account = service.getAccount(accountId);

            service.accountPolicy.validate(account.snapshot());

            readVersions.putIfAbsent(accountId, account.version);

            return account.balance;
        }

        public void transfer(
            int sourceId,
            int targetId,
            long amount,
            String idempotencyKey
        ) {
            requireActive();

            if (sourceId == targetId) {
                throw new ConstraintException(
                    "Source and target must differ"
                );
            }

            if (amount <= 0) {
                throw new ConstraintException(
                    "Transfer must be positive"
                );
            }

            Account source = service.getAccount(sourceId);
            Account target = service.getAccount(targetId);

            service.accountPolicy.validate(source.snapshot());
            service.accountPolicy.validate(target.snapshot());

            long sourceBalance = read(sourceId);
            long targetBalance = read(targetId);

            if (sourceBalance < amount) {
                throw new ConstraintException("Insufficient funds");
            }

            if (targetBalance > Long.MAX_VALUE - amount) {
                throw new ConstraintException("Balance overflow");
            }

            writeVersions.putIfAbsent(sourceId, source.version);
            writeVersions.putIfAbsent(targetId, target.version);

            stagedBalances.put(sourceId, sourceBalance - amount);
            stagedBalances.put(targetId, targetBalance + amount);

            commands.add(new TransactionCommand(
                id,
                idempotencyKey,
                OperationType.TRANSFER,
                sourceId,
                targetId,
                amount
            ));
        }

        public void commit() {
            requireActive();

            try {
                service.commit(this);
                status = TransactionStatus.COMMITTED;
            } catch (RuntimeException exception) {
                stagedBalances.clear();
                status = TransactionStatus.FAILED;
                throw exception;
            }
        }

        public void rollback() {
            requireActive();
            stagedBalances.clear();
            commands.clear();
            status = TransactionStatus.ROLLED_BACK;
        }

        public TransactionStatus status() {
            return status;
        }

        public String id() {
            return id;
        }
    }

    static final class TransactionService {
        private final Map<Integer, Account> accounts =
            new LinkedHashMap<>();

        private final Map<String, String> idempotencyResults =
            new HashMap<>();

        private final ReentrantLock commitLock =
            new ReentrantLock(true);

        private final Journal journal;
        private final AccountPolicy accountPolicy;

        private int nextId = 1;

        TransactionService(Journal journal, AccountPolicy accountPolicy) {
            this.journal = Objects.requireNonNull(journal);
            this.accountPolicy = Objects.requireNonNull(accountPolicy);
        }

        public synchronized int createAccount(
            String owner,
            long initialBalance
        ) {
            if (owner == null || owner.isBlank()) {
                throw new ConstraintException("Owner is required");
            }

            if (initialBalance < 0) {
                throw new ConstraintException(
                    "Initial balance cannot be negative"
                );
            }

            int id = nextId++;

            Account account = new Account(id, owner, initialBalance);

            accountPolicy.validate(account.snapshot());

            accounts.put(id, account);

            return id;
        }

        Account getAccount(int id) {
            Account account = accounts.get(id);

            if (account == null) {
                throw new ConstraintException(
                    "Unknown account: " + id
                );
            }

            return account;
        }

        public Transaction begin(IsolationLevel isolation) {
            return new Transaction(
                this,
                Objects.requireNonNull(isolation)
            );
        }

        void commit(Transaction transaction) {
            commitLock.lock();

            try {
                // Optimistic validation detects changes since observation.
                if (
                    transaction.isolation != IsolationLevel.READ_COMMITTED
                ) {
                    for (Map.Entry<Integer, Long> entry :
                         transaction.readVersions.entrySet()) {

                        Account account = getAccount(entry.getKey());

                        if (account.version != entry.getValue()) {
                            throw new ConcurrencyException(
                                "Read conflict on account " + account.id
                            );
                        }
                    }
                }

                for (Map.Entry<Integer, Long> entry :
                     transaction.writeVersions.entrySet()) {

                    Account account = getAccount(entry.getKey());

                    if (account.version != entry.getValue()) {
                        throw new ConcurrencyException(
                            "Write conflict on account " + account.id
                        );
                    }
                }

                long before = totalBalance();

                long after = before;

                for (Map.Entry<Integer, Long> entry :
                     transaction.stagedBalances.entrySet()) {

                    Account account = getAccount(entry.getKey());
                    long newBalance = entry.getValue();

                    if (newBalance < 0) {
                        throw new ConstraintException(
                            "Negative account balance"
                        );
                    }

                    after = Math.addExact(
                        after,
                        Math.subtractExact(newBalance, account.balance)
                    );
                }

                if (before != after) {
                    throw new ConstraintException(
                        "Global balance conservation failed"
                    );
                }

                // Idempotency prevents repeated business operations.
                for (TransactionCommand command : transaction.commands) {
                    String key = command.idempotencyKey();

                    if (
                        key != null &&
                        idempotencyResults.containsKey(key)
                    ) {
                        throw new ConstraintException(
                            "Duplicate idempotency key: " + key
                        );
                    }
                }

                Map<Integer, Long> changes = new LinkedHashMap<>(
                    transaction.stagedBalances
                );

                CommitRecord record = new CommitRecord(
                    transaction.id,
                    changes,
                    "Account ledger transaction"
                );

                // Journal persistence must succeed before state publication.
                journal.append(record);

                for (Map.Entry<Integer, Long> entry :
                     changes.entrySet()) {

                    Account account = getAccount(entry.getKey());
                    account.balance = entry.getValue();
                    account.version++;
                }

                for (TransactionCommand command : transaction.commands) {
                    if (command.idempotencyKey() != null) {
                        idempotencyResults.put(
                            command.idempotencyKey(),
                            transaction.id
                        );
                    }
                }

            } catch (ArithmeticException exception) {
                throw new ConstraintException(
                    "Arithmetic overflow detected"
                );
            } finally {
                commitLock.unlock();
            }
        }

        long totalBalance() {
            return accounts.values().stream()
                .filter(account -> account.active)
                .mapToLong(account -> account.balance)
                .sum();
        }

        List<AccountSnapshot> report() {
            return accounts.values().stream()
                .map(Account::snapshot)
                .collect(Collectors.toUnmodifiableList());
        }

        void printReport() {
            System.out.println("\nENTERPRISE ACCOUNT REPORT");

            report().forEach(account ->
                System.out.printf(
                    "%-5d %-15s %12d Version=%d%n",
                    account.accountId(),
                    account.owner(),
                    account.balance(),
                    account.version()
                )
            );
        }
    }

    public static void main(String[] args) {
        InMemoryJournal journal = new InMemoryJournal();

        TransactionService service = new TransactionService(
            journal,
            new StandardAccountPolicy()
        );

        int alice = service.createAccount("Alice", 100000);
        int bob = service.createAccount("Bob", 50000);
        int charlie = service.createAccount("Charlie", 25000);

        System.out.println("ACID ENTERPRISE TRANSACTION MODEL");

        service.printReport();

        // Successful atomic transaction.
        Transaction payment = service.begin(
            IsolationLevel.SERIALIZABLE
        );

        payment.transfer(
            alice,
            bob,
            20000,
            "PAYMENT-1001"
        );

        payment.commit();

        System.out.println("\nTransaction status: " + payment.status());

        // Constraint failure and rollback.
        Transaction rejected = service.begin(
            IsolationLevel.SERIALIZABLE
        );

        try {
            rejected.transfer(
                alice,
                charlie,
                999999,
                "PAYMENT-1002"
            );

            rejected.commit();

        } catch (TransactionException exception) {
            if (rejected.status() == TransactionStatus.ACTIVE) {
                rejected.rollback();
            }

            System.out.println(
                "\nRejected payment: " + exception.getMessage()
            );
        }

        // Isolation conflict.
        Transaction first = service.begin(
            IsolationLevel.SERIALIZABLE
        );

        Transaction second = service.begin(
            IsolationLevel.SERIALIZABLE
        );

        first.transfer(alice, charlie, 1000, "PAYMENT-1003");
        second.transfer(alice, bob, 2000, "PAYMENT-1004");

        first.commit();

        try {
            second.commit();
        } catch (ConcurrencyException exception) {
            System.out.println(
                "\nSerialization failure: " + exception.getMessage()
            );
        }

        // Durability failure: the transaction must not be published.
        journal.setAvailable(false);

        Transaction failedPersistence = service.begin(
            IsolationLevel.SERIALIZABLE
        );

        failedPersistence.transfer(
            bob,
            charlie,
            500,
            "PAYMENT-1005"
        );

        try {
            failedPersistence.commit();
        } catch (DurabilityException exception) {
            System.out.println(
                "\nPersistence failure: " + exception.getMessage()
            );
        }

        journal.setAvailable(true);

        service.printReport();

        System.out.println("\nCOMMIT JOURNAL");

        journal.records().forEach(System.out::println);

        if (service.totalBalance() != 175000) {
            throw new IllegalStateException(
                "Consistency verification failed"
            );
        }

        System.out.println(
            "\nVerified total balance: " + service.totalBalance()
        );

        System.out.println(
            "Durable records: " + journal.records().size()
        );
    }
}
