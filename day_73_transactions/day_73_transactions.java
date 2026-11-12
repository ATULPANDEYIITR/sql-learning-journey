import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.locks.ReentrantLock;

public class Main {

    enum TransactionState {
        ACTIVE,
        COMMITTED,
        ROLLED_BACK
    }

    enum OperationType {
        TRANSFER,
        DEPOSIT,
        WITHDRAWAL
    }

    enum IsolationLevel {
        READ_COMMITTED,
        SERIALIZABLE
    }

    static class TransactionException extends RuntimeException {
        TransactionException(String message) {
            super(message);
        }
    }

    static class InsufficientFundsException
            extends TransactionException {
        InsufficientFundsException(String message) {
            super(message);
        }
    }

    static class SerializationException
            extends TransactionException {
        SerializationException(String message) {
            super(message);
        }
    }

    static class Account {
        private final String id;
        private final String owner;
        private final String currency;
        private long balance;
        private long version;

        Account(
                String id,
                String owner,
                long balance,
                String currency
        ) {
            if (id == null || id.isBlank()
                    || owner == null || owner.isBlank()) {
                throw new IllegalArgumentException(
                        "Account ID and owner are required"
                );
            }

            if (balance < 0) {
                throw new IllegalArgumentException(
                        "Opening balance cannot be negative"
                );
            }

            this.id = id;
            this.owner = owner;
            this.balance = balance;
            this.currency = currency;
        }

        public String getId() {
            return id;
        }

        public String getOwner() {
            return owner;
        }

        public long getBalance() {
            return balance;
        }
    }

    record Operation(
            OperationType type,
            String source,
            String destination,
            long amount
    ) {
        Operation {
            if (amount <= 0) {
                throw new IllegalArgumentException(
                        "Operation amount must be positive"
                );
            }
        }
    }

    record LedgerEntry(
            String transactionId,
            String accountId,
            long amount,
            String type
    ) {}

    static final class Transaction {
        private final String id = UUID.randomUUID().toString();
        private final long baseVersion;
        private final List<Operation> operations = new ArrayList<>();
        private TransactionState state = TransactionState.ACTIVE;

        Transaction(long baseVersion) {
            this.baseVersion = baseVersion;
        }

        void addOperation(Operation operation) {
            requireActive();
            operations.add(operation);
        }

        void requireActive() {
            if (state != TransactionState.ACTIVE) {
                throw new TransactionException(
                        "Transaction is not active"
                );
            }
        }

        String getId() {
            return id;
        }

        long getBaseVersion() {
            return baseVersion;
        }

        List<Operation> getOperations() {
            return Collections.unmodifiableList(operations);
        }

        TransactionState getState() {
            return state;
        }

        void setState(TransactionState state) {
            this.state = state;
        }

        void clearOperations() {
            operations.clear();
        }
    }

    interface TransactionPolicy {
        void validate(
                Transaction transaction,
                long currentVersion
        );
    }

    static final class SerializablePolicy
            implements TransactionPolicy {

        @Override
        public void validate(
                Transaction transaction,
                long currentVersion
        ) {
            if (transaction.getBaseVersion() != currentVersion) {
                throw new SerializationException(
                        "Concurrent update detected"
                );
            }
        }
    }

    static final class ReadCommittedPolicy
            implements TransactionPolicy {

        @Override
        public void validate(
                Transaction transaction,
                long currentVersion
        ) {
            // The commit service validates operations against the
            // latest committed balances while holding its lock.
        }
    }

    static final class TransactionService {
        private final Map<String, Account> accounts = new HashMap<>();
        private final List<LedgerEntry> ledger = new ArrayList<>();

        private final ReentrantLock commitLock =
                new ReentrantLock(true);

        private long databaseVersion;

        public void createAccount(
                String id,
                String owner,
                long balance,
                String currency
        ) {
            commitLock.lock();

            try {
                if (accounts.containsKey(id)) {
                    throw new TransactionException(
                            "Duplicate account"
                    );
                }

                accounts.put(
                        id,
                        new Account(id, owner, balance, currency)
                );

                databaseVersion++;

            } finally {
                commitLock.unlock();
            }
        }

        public Transaction begin() {
            commitLock.lock();

            try {
                return new Transaction(databaseVersion);
            } finally {
                commitLock.unlock();
            }
        }

        private Account requireAccount(String id) {
            Account account = accounts.get(id);

            if (account == null) {
                throw new TransactionException(
                        "Unknown account: " + id
                );
            }

            return account;
        }

        public void transfer(
                Transaction transaction,
                String source,
                String destination,
                long amount
        ) {
            transaction.requireActive();

            Account from = requireAccount(source);
            Account to = requireAccount(destination);

            if (source.equals(destination)) {
                throw new IllegalArgumentException(
                        "Source and destination must differ"
                );
            }

            if (!from.currency.equals(to.currency)) {
                throw new IllegalArgumentException(
                        "Currency mismatch"
                );
            }

            transaction.addOperation(
                    new Operation(
                            OperationType.TRANSFER,
                            source,
                            destination,
                            amount
                    )
            );
        }

        public void deposit(
                Transaction transaction,
                String accountId,
                long amount
        ) {
            transaction.requireActive();
            requireAccount(accountId);

            transaction.addOperation(
                    new Operation(
                            OperationType.DEPOSIT,
                            accountId,
                            "",
                            amount
                    )
            );
        }

        public void withdraw(
                Transaction transaction,
                String accountId,
                long amount
        ) {
            transaction.requireActive();
            requireAccount(accountId);

            transaction.addOperation(
                    new Operation(
                            OperationType.WITHDRAWAL,
                            accountId,
                            "",
                            amount
                    )
            );
        }

        public void commit(
                Transaction transaction,
                IsolationLevel isolation
        ) {
            transaction.requireActive();

            commitLock.lock();

            try {
                TransactionPolicy policy =
                        isolation == IsolationLevel.SERIALIZABLE
                                ? new SerializablePolicy()
                                : new ReadCommittedPolicy();

                policy.validate(transaction, databaseVersion);

                // The working state is private until every operation
                // and every constraint has passed.
                Map<String, Long> balances = new HashMap<>();

                for (Account account : accounts.values()) {
                    balances.put(
                            account.id,
                            account.balance
                    );
                }

                List<LedgerEntry> pendingLedger =
                        new ArrayList<>();

                try {
                    for (Operation operation :
                            transaction.getOperations()) {

                        if (operation.type() == OperationType.TRANSFER) {
                            long sourceBalance =
                                    balances.get(operation.source());

                            long destinationBalance =
                                    balances.get(operation.destination());

                            if (sourceBalance < operation.amount()) {
                                throw new InsufficientFundsException(
                                        "Insufficient funds in "
                                                + operation.source()
                                );
                            }

                            long updatedDestination =
                                    Math.addExact(
                                            destinationBalance,
                                            operation.amount()
                                    );

                            balances.put(
                                    operation.source(),
                                    sourceBalance - operation.amount()
                            );

                            balances.put(
                                    operation.destination(),
                                    updatedDestination
                            );

                            pendingLedger.add(
                                    new LedgerEntry(
                                            transaction.id,
                                            operation.source(),
                                            -operation.amount(),
                                            "TRANSFER_OUT"
                                    )
                            );

                            pendingLedger.add(
                                    new LedgerEntry(
                                            transaction.id,
                                            operation.destination(),
                                            operation.amount(),
                                            "TRANSFER_IN"
                                    )
                            );

                        } else if (
                                operation.type() == OperationType.DEPOSIT
                        ) {
                            long updated = Math.addExact(
                                    balances.get(operation.source()),
                                    operation.amount()
                            );

                            balances.put(operation.source(), updated);

                            pendingLedger.add(
                                    new LedgerEntry(
                                            transaction.id,
                                            operation.source(),
                                            operation.amount(),
                                            "DEPOSIT"
                                    )
                            );

                        } else if (
                                operation.type() == OperationType.WITHDRAWAL
                        ) {
                            long current =
                                    balances.get(operation.source());

                            if (current < operation.amount()) {
                                throw new InsufficientFundsException(
                                        "Insufficient funds in "
                                                + operation.source()
                                );
                            }

                            balances.put(
                                    operation.source(),
                                    current - operation.amount()
                            );

                            pendingLedger.add(
                                    new LedgerEntry(
                                            transaction.id,
                                            operation.source(),
                                            -operation.amount(),
                                            "WITHDRAWAL"
                                    )
                            );
                        }
                    }

                    for (long balance : balances.values()) {
                        if (balance < 0) {
                            throw new TransactionException(
                                    "Negative balance constraint"
                            );
                        }
                    }

                    // Publication takes place after complete validation.
                    for (Account account : accounts.values()) {
                        long updated = balances.get(account.id);

                        if (updated != account.balance) {
                            account.balance = updated;
                            account.version++;
                        }
                    }

                    ledger.addAll(pendingLedger);
                    databaseVersion++;

                    transaction.setState(
                            TransactionState.COMMITTED
                    );

                    System.out.println(
                            "COMMIT " + transaction.getId()
                    );

                } catch (RuntimeException exception) {
                    transaction.setState(
                            TransactionState.ROLLED_BACK
                    );

                    System.out.println(
                            "ROLLBACK " + transaction.getId()
                    );

                    throw exception;
                }

            } catch (RuntimeException exception) {
                if (transaction.getState() == TransactionState.ACTIVE) {
                    transaction.setState(
                            TransactionState.ROLLED_BACK
                    );
                }

                throw exception;

            } finally {
                commitLock.unlock();
            }
        }

        public void rollback(Transaction transaction) {
            transaction.requireActive();

            transaction.clearOperations();

            transaction.setState(
                    TransactionState.ROLLED_BACK
            );

            System.out.println(
                    "ROLLBACK " + transaction.getId()
            );
        }

        public long getBalance(String accountId) {
            commitLock.lock();

            try {
                return requireAccount(accountId).balance;
            } finally {
                commitLock.unlock();
            }
        }

        public long getTotalBalance() {
            commitLock.lock();

            try {
                long total = 0;

                for (Account account : accounts.values()) {
                    total = Math.addExact(total, account.balance);
                }

                return total;

            } finally {
                commitLock.unlock();
            }
        }

        public void printReport() {
            commitLock.lock();

            try {
                System.out.println("\nACCOUNT REPORT");

                accounts.values().stream()
                        .sorted(
                                java.util.Comparator.comparing(
                                        Account::getId
                                )
                        )
                        .forEach(account ->
                                System.out.printf(
                                        "%-10s %-15s %d%n",
                                        account.id,
                                        account.owner,
                                        account.balance
                                )
                        );

                System.out.println(
                        "Ledger entries: " + ledger.size()
                );

                System.out.println(
                        "Database version: " + databaseVersion
                );

            } finally {
                commitLock.unlock();
            }
        }

        public void printLedger() {
            commitLock.lock();

            try {
                ledger.forEach(entry ->
                        System.out.printf(
                                "%s | %s | %d | %s%n",
                                entry.transactionId(),
                                entry.accountId(),
                                entry.amount(),
                                entry.type()
                        )
                );

            } finally {
                commitLock.unlock();
            }
        }
    }

    public static void main(String[] args) {
        TransactionService service = new TransactionService();

        service.createAccount("A100", "Alice", 1000000, "INR");
        service.createAccount("A200", "Bob", 500000, "INR");
        service.createAccount("A300", "Charlie", 200000, "INR");

        System.out.println("1. Successful transaction");

        Transaction first = service.begin();

        service.transfer(first, "A100", "A200", 150000);
        service.deposit(first, "A300", 50000);

        service.commit(
                first,
                IsolationLevel.SERIALIZABLE
        );

        service.printReport();

        System.out.println("\n2. Explicit rollback");

        Transaction second = service.begin();

        service.withdraw(second, "A100", 100000);
        service.rollback(second);

        service.printReport();

        System.out.println("\n3. Insufficient funds");

        Transaction third = service.begin();

        service.withdraw(third, "A200", 99999999);

        try {
            service.commit(
                    third,
                    IsolationLevel.SERIALIZABLE
            );
        } catch (TransactionException exception) {
            System.out.println(
                    "Expected failure: " + exception.getMessage()
            );
        }

        service.printReport();

        System.out.println("\n4. Serialization conflict");

        Transaction stale = service.begin();

        service.deposit(stale, "A100", 10000);

        Transaction concurrent = service.begin();

        service.deposit(concurrent, "A200", 20000);

        service.commit(
                concurrent,
                IsolationLevel.SERIALIZABLE
        );

        try {
            service.commit(
                    stale,
                    IsolationLevel.SERIALIZABLE
            );
        } catch (TransactionException exception) {
            System.out.println(
                    "Expected conflict: " + exception.getMessage()
            );
        }

        System.out.println("\n5. Multiple account operations");

        Transaction fifth = service.begin();

        service.deposit(fifth, "A100", 25000);
        service.withdraw(fifth, "A300", 10000);

        service.commit(
                fifth,
                IsolationLevel.READ_COMMITTED
        );

        service.printReport();

        System.out.println("\n6. Ledger and accounting validation");

        service.printLedger();

        long expectedTotal = 1775000;
        long actualTotal = service.getTotalBalance();

        if (actualTotal != expectedTotal) {
            throw new IllegalStateException(
                    "Accounting invariant failed: " + actualTotal
            );
        }

        System.out.println("Total balance: " + actualTotal);
        System.out.println("All transaction checks passed.");
    }
}
