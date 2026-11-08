import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicLong;

/**
 * PostgreSQL Sequence Management
 *
 * Enterprise-oriented sequence and identity model.
 *
 * Demonstrates:
 * - Sequence lifecycle and configuration
 * - SERIAL and IDENTITY distinctions
 * - NEXTVAL, CURRVAL and SETVAL
 * - Sequence ownership
 * - Session isolation
 * - Transaction rollback gaps
 * - Boundary and cycle policies
 * - Concurrent identifier allocation
 * - Enterprise validation and reporting
 *
 * Java version: 17
 * Dependencies: Java standard library
 */

public class PostgreSQLSequenceDemo {

    enum IdentityMode {
        SERIAL,
        GENERATED_ALWAYS,
        GENERATED_BY_DEFAULT
    }

    enum SequenceStatus {
        READY,
        EXHAUSTED
    }

    static class SequenceException extends RuntimeException {
        SequenceException(String message) {
            super(message);
        }
    }

    static class SequenceLimitException extends SequenceException {
        SequenceLimitException(String message) {
            super(message);
        }
    }

    static class SequenceConfigurationException
            extends SequenceException {
        SequenceConfigurationException(String message) {
            super(message);
        }
    }

    record SequenceConfig(
            String name,
            long start,
            long increment,
            long minimum,
            long maximum,
            int cache,
            boolean cycle
    ) {
        SequenceConfig {
            if (name == null || name.isBlank()) {
                throw new SequenceConfigurationException(
                        "Sequence name is required."
                );
            }

            if (increment == 0) {
                throw new SequenceConfigurationException(
                        "Increment cannot be zero."
                );
            }

            if (minimum > maximum ||
                    start < minimum ||
                    start > maximum) {
                throw new SequenceConfigurationException(
                        "Invalid sequence boundaries."
                );
            }

            if (cache < 1) {
                throw new SequenceConfigurationException(
                        "Cache must be positive."
                );
            }
        }
    }

    record SequenceReport(
            String sequenceName,
            Long lastValue,
            boolean isCalled,
            long allocationCount,
            SequenceStatus status,
            Instant generatedAt
    ) {}

    record Customer(
            long id,
            String name,
            String email,
            Instant createdAt
    ) {}

    record AllocationEvent(
            String sequence,
            String session,
            long value,
            Instant timestamp
    ) {}

    interface SequenceObserver {
        void onAllocation(AllocationEvent event);
    }

    static class PostgreSQLSequence {

        private final SequenceConfig config;

        private Long lastValue;
        private boolean isCalled;
        private long allocations;

        private SequenceStatus status = SequenceStatus.READY;

        private final Map<String, Long> sessionValues =
                new HashMap<>();

        private final List<SequenceObserver> observers =
                new ArrayList<>();

        PostgreSQLSequence(SequenceConfig config) {
            this.config = config;
        }

        public synchronized void addObserver(
                SequenceObserver observer
        ) {
            observers.add(observer);
        }

        private long calculateNext() {
            if (!isCalled) {
                return config.start();
            }

            long current = lastValue;

            try {
                long candidate = Math.addExact(
                        current,
                        config.increment()
                );

                if (
                        candidate > config.maximum() ||
                        candidate < config.minimum()
                ) {
                    if (!config.cycle()) {
                        status = SequenceStatus.EXHAUSTED;

                        throw new SequenceLimitException(
                                "Sequence boundary reached."
                        );
                    }

                    return config.increment() > 0
                            ? config.minimum()
                            : config.maximum();
                }

                return candidate;

            } catch (ArithmeticException error) {
                if (!config.cycle()) {
                    status = SequenceStatus.EXHAUSTED;

                    throw new SequenceLimitException(
                            "Sequence arithmetic overflow."
                    );
                }

                return config.increment() > 0
                        ? config.minimum()
                        : config.maximum();
            }
        }

        public synchronized long nextval(String session) {
            if (session == null || session.isBlank()) {
                throw new SequenceException(
                        "Session identifier is required."
                );
            }

            long value = calculateNext();

            lastValue = value;
            isCalled = true;
            allocations++;

            sessionValues.put(session, value);

            AllocationEvent event = new AllocationEvent(
                    config.name(),
                    session,
                    value,
                    Instant.now()
            );

            for (SequenceObserver observer : observers) {
                observer.onAllocation(event);
            }

            return value;
        }

        public synchronized long currval(String session) {
            Long value = sessionValues.get(session);

            if (value == null) {
                throw new SequenceException(
                        "CURRVAL is undefined for this session."
                );
            }

            return value;
        }

        public synchronized long setval(
                long value,
                boolean called
        ) {
            if (
                    value < config.minimum() ||
                    value > config.maximum()
            ) {
                throw new SequenceLimitException(
                        "SETVAL outside sequence limits."
                );
            }

            lastValue = value;
            isCalled = called;
            status = SequenceStatus.READY;

            return value;
        }

        public synchronized void restart(long value) {
            if (
                    value < config.minimum() ||
                    value > config.maximum()
            ) {
                throw new SequenceLimitException(
                        "Invalid restart value."
                );
            }

            lastValue = value;
            isCalled = false;
            status = SequenceStatus.READY;

            sessionValues.clear();
        }

        public synchronized SequenceReport report() {
            return new SequenceReport(
                    config.name(),
                    lastValue,
                    isCalled,
                    allocations,
                    status,
                    Instant.now()
            );
        }

        public SequenceConfig getConfig() {
            return config;
        }
    }

    static class SequenceOwnershipRegistry {

        private final Map<String, String> owners =
                new HashMap<>();

        public synchronized void assign(
                String sequence,
                String table,
                String column
        ) {
            if (
                    sequence == null ||
                    table == null ||
                    column == null ||
                    sequence.isBlank() ||
                    table.isBlank() ||
                    column.isBlank()
            ) {
                throw new SequenceException(
                        "Invalid ownership definition."
                );
            }

            String owner = table + "." + column;

            if (
                    owners.containsKey(sequence) &&
                    !owners.get(sequence).equals(owner)
            ) {
                throw new SequenceException(
                        "Sequence already has another owner."
                );
            }

            owners.put(sequence, owner);
        }

        public synchronized String getOwner(
                String sequence
        ) {
            return owners.get(sequence);
        }
    }

    static class CustomerService {

        private final PostgreSQLSequence sequence;
        private final IdentityMode identityMode;

        private final Map<Long, Customer> customers =
                new HashMap<>();

        CustomerService(
                PostgreSQLSequence sequence,
                IdentityMode identityMode
        ) {
            this.sequence = sequence;
            this.identityMode = identityMode;
        }

        public synchronized Customer create(
                String name,
                String email,
                Long explicitId,
                boolean overridingSystemValue
        ) {
            validateCustomer(name, email);

            long id;

            if (explicitId != null) {
                if (
                        identityMode == IdentityMode.GENERATED_ALWAYS &&
                        !overridingSystemValue
                ) {
                    throw new SequenceException(
                            "Explicit identity value is prohibited."
                    );
                }

                id = explicitId;

            } else {
                id = sequence.nextval("customer-service");
            }

            if (id <= 0) {
                throw new SequenceException(
                        "Customer ID must be positive."
                );
            }

            if (customers.containsKey(id)) {
                throw new SequenceException(
                        "Duplicate customer ID: " + id
                );
            }

            Customer customer = new Customer(
                    id,
                    name.trim(),
                    email.trim().toLowerCase(),
                    Instant.now()
            );

            customers.put(id, customer);

            return customer;
        }

        private void validateCustomer(
                String name,
                String email
        ) {
            if (name == null || name.isBlank()) {
                throw new SequenceException(
                        "Customer name is required."
                );
            }

            if (
                    email == null ||
                    !email.matches(
                            "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$"
                    )
            ) {
                throw new SequenceException(
                        "Invalid email address."
                );
            }
        }

        public synchronized long maximumId() {
            return customers.keySet()
                    .stream()
                    .mapToLong(Long::longValue)
                    .max()
                    .orElse(0L);
        }

        public synchronized void synchronizeSequence() {
            long maximum = maximumId();

            SequenceReport report = sequence.report();

            if (
                    report.lastValue() == null ||
                    maximum > report.lastValue()
            ) {
                sequence.setval(maximum, true);
            }
        }

        public synchronized List<Customer> allCustomers() {
            return List.copyOf(customers.values());
        }
    }

    static class TransactionSimulator {

        private final PostgreSQLSequence sequence;

        TransactionSimulator(PostgreSQLSequence sequence) {
            this.sequence = sequence;
        }

        public void executeFailureScenario() {
            long allocated = sequence.nextval(
                    "transaction-service"
            );

            System.out.println(
                    "Allocated before failure: " + allocated
            );

            // A real database rollback does not reverse NEXTVAL.
            throw new SequenceException(
                    "Simulated transaction failure."
            );
        }
    }

    static class SequenceMonitoringService {

        private final List<SequenceReport> reports =
                new ArrayList<>();

        public void record(SequenceReport report) {
            reports.add(report);
        }

        public void printReports() {
            reports.forEach(System.out::println);
        }
    }

    static void demonstrateBasicSequence() {
        System.out.println("\n1. BASIC SEQUENCE");

        PostgreSQLSequence sequence =
                new PostgreSQLSequence(
                        new SequenceConfig(
                                "orders_order_id_seq",
                                1000,
                                1,
                                1000,
                                1100,
                                1,
                                false
                        )
                );

        sequence.addObserver(event ->
                System.out.println(
                        "[EVENT] " +
                        event.sequence() +
                        " allocated " +
                        event.value()
                )
        );

        System.out.println(
                "NEXTVAL: " + sequence.nextval("session-a")
        );

        System.out.println(
                "NEXTVAL: " + sequence.nextval("session-a")
        );

        System.out.println(
                "CURRVAL: " + sequence.currval("session-a")
        );
    }

    static void demonstrateIdentity() {
        System.out.println("\n2. IDENTITY MANAGEMENT");

        PostgreSQLSequence sequence =
                new PostgreSQLSequence(
                        new SequenceConfig(
                                "customers_customer_id_seq",
                                1,
                                1,
                                1,
                                Long.MAX_VALUE,
                                1,
                                false
                        )
                );

        CustomerService service = new CustomerService(
                sequence,
                IdentityMode.GENERATED_ALWAYS
        );

        Customer first = service.create(
                "Aarav Sharma",
                "aarav@example.com",
                null,
                false
        );

        System.out.println("Created: " + first);

        try {
            service.create(
                    "Manual Customer",
                    "manual@example.com",
                    500L,
                    false
            );
        } catch (SequenceException error) {
            System.out.println(
                    "Expected restriction: " + error.getMessage()
            );
        }

        service.create(
                "Imported Customer",
                "import@example.com",
                500L,
                true
        );

        service.synchronizeSequence();

        Customer next = service.create(
                "Next Customer",
                "next@example.com",
                null,
                false
        );

        System.out.println(
                "Next generated ID: " + next.id()
        );

        service.allCustomers().forEach(System.out::println);
    }

    static void demonstrateSetval() {
        System.out.println("\n3. SETVAL");

        PostgreSQLSequence sequence =
                new PostgreSQLSequence(
                        new SequenceConfig(
                                "shipment_sequence",
                                1,
                                1,
                                1,
                                10000,
                                1,
                                false
                        )
                );

        sequence.setval(500, true);

        System.out.println(
                "SETVAL(500, true): " +
                sequence.nextval("session-a")
        );

        sequence.setval(900, false);

        System.out.println(
                "SETVAL(900, false): " +
                sequence.nextval("session-a")
        );
    }

    static void demonstrateSessionIsolation() {
        System.out.println("\n4. SESSION ISOLATION");

        PostgreSQLSequence sequence =
                new PostgreSQLSequence(
                        new SequenceConfig(
                                "invoice_sequence",
                                1,
                                1,
                                1,
                                1000,
                                1,
                                false
                        )
                );

        sequence.nextval("connection-a");

        try {
            sequence.currval("connection-b");
        } catch (SequenceException error) {
            System.out.println(
                    "Expected error: " + error.getMessage()
            );
        }

        sequence.nextval("connection-b");

        System.out.println(
                "Connection A: " +
                sequence.currval("connection-a")
        );

        System.out.println(
                "Connection B: " +
                sequence.currval("connection-b")
        );
    }

    static void demonstrateRollback() {
        System.out.println("\n5. TRANSACTION ROLLBACK");

        PostgreSQLSequence sequence =
                new PostgreSQLSequence(
                        new SequenceConfig(
                                "payment_sequence",
                                1,
                                1,
                                1,
                                10000,
                                1,
                                false
                        )
                );

        TransactionSimulator transaction =
                new TransactionSimulator(sequence);

        try {
            transaction.executeFailureScenario();
        } catch (SequenceException error) {
            System.out.println(
                    "Transaction failed: " + error.getMessage()
            );
        }

        System.out.println(
                "Next value after failure: " +
                sequence.nextval("application")
        );
    }

    static void demonstrateConcurrency() throws Exception {
        System.out.println("\n6. CONCURRENT ALLOCATION");

        PostgreSQLSequence sequence =
                new PostgreSQLSequence(
                        new SequenceConfig(
                                "concurrent_sequence",
                                1,
                                1,
                                1,
                                Long.MAX_VALUE,
                                1,
                                false
                        )
                );

        ExecutorService executor =
                Executors.newFixedThreadPool(8);

        try {
            List<Callable<List<Long>>> tasks =
                    new ArrayList<>();

            for (int worker = 0; worker < 8; worker++) {
                final int workerId = worker;

                tasks.add(() -> {
                    List<Long> local = new ArrayList<>();

                    for (int i = 0; i < 100; i++) {
                        local.add(
                                sequence.nextval(
                                        "worker-" + workerId
                                )
                        );
                    }

                    return local;
                });
            }

            List<Future<List<Long>>> futures =
                    executor.invokeAll(tasks);

            Set<Long> unique = new HashSet<>();

            for (Future<List<Long>> future : futures) {
                unique.addAll(future.get());
            }

            if (unique.size() != 800) {
                throw new SequenceException(
                        "Concurrent allocation produced duplicates."
                );
            }

            System.out.println("Unique allocations: " + unique.size());

        } finally {
            executor.shutdown();
        }
    }

    static void demonstrateOwnership() {
        System.out.println("\n7. SEQUENCE OWNERSHIP");

        SequenceOwnershipRegistry registry =
                new SequenceOwnershipRegistry();

        registry.assign(
                "customers_customer_id_seq",
                "customers",
                "customer_id"
        );

        System.out.println(
                "Owner: " +
                registry.getOwner("customers_customer_id_seq")
        );

        try {
            registry.assign(
                    "customers_customer_id_seq",
                    "invoices",
                    "invoice_id"
            );
        } catch (SequenceException error) {
            System.out.println(
                    "Expected ownership error: " +
                    error.getMessage()
            );
        }
    }

    static void runTests() {
        System.out.println("\n8. AUTOMATED TESTS");

        PostgreSQLSequence sequence =
                new PostgreSQLSequence(
                        new SequenceConfig(
                                "test_sequence",
                                10,
                                5,
                                10,
                                30,
                                1,
                                false
                        )
                );

        if (sequence.nextval("test") != 10) {
            throw new AssertionError("Initial value test failed.");
        }

        if (sequence.nextval("test") != 15) {
            throw new AssertionError("Increment test failed.");
        }

        sequence.setval(20, false);

        if (sequence.nextval("test") != 20) {
            throw new AssertionError("SETVAL test failed.");
        }

        sequence.setval(30, true);

        try {
            sequence.nextval("test");

            throw new AssertionError(
                    "Expected sequence boundary error."
            );

        } catch (SequenceLimitException expected) {
            // Expected result.
        }

        try {
            new SequenceConfig(
                    "invalid_sequence",
                    1,
                    0,
                    1,
                    100,
                    1,
                    false
            );

            throw new AssertionError(
                    "Expected configuration error."
            );

        } catch (SequenceConfigurationException expected) {
            // Expected result.
        }

        System.out.println("All tests passed.");
    }

    public static void main(String[] args) {
        try {
            System.out.println(
                    "========================================"
            );

            System.out.println(
                    "POSTGRESQL SEQUENCE MANAGEMENT"
            );

            System.out.println(
                    "========================================"
            );

            demonstrateBasicSequence();
            demonstrateIdentity();
            demonstrateSetval();
            demonstrateSessionIsolation();
            demonstrateRollback();
            demonstrateConcurrency();
            demonstrateOwnership();
            runTests();

            System.out.println("\nSEQUENCE MONITORING");

            PostgreSQLSequence monitored =
                    new PostgreSQLSequence(
                            new SequenceConfig(
                                    "monitor_sequence",
                                    1,
                                    1,
                                    1,
                                    1000,
                                    1,
                                    false
                            )
                    );

            monitored.nextval("monitoring");

            SequenceMonitoringService monitoring =
                    new SequenceMonitoringService();

            monitoring.record(monitored.report());
            monitoring.printReports();

            System.out.println(
                    "\nExecution completed successfully."
            );

        } catch (Exception error) {
            System.err.println(
                    "Execution failed: " + error.getMessage()
            );

            System.exit(1);
        }
    }
}
