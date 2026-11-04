import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.atomic.AtomicLong;

public class DenormalizationEnterprise {

    enum OrderStatus {
        PENDING,
        COMPLETED,
        CANCELLED
    }

    enum ConsistencyMode {
        STRICT,
        EVENTUAL
    }

    enum ProjectionState {
        CLEAN,
        DIRTY,
        REBUILDING,
        FAILED
    }

    static class DomainException extends RuntimeException {
        DomainException(String message) {
            super(message);
        }
    }

    record Customer(
        long id,
        String name,
        String email
    ) {
        Customer {
            if (id <= 0 || name == null || name.isBlank()
                    || email == null || email.isBlank()) {
                throw new DomainException("Invalid customer data");
            }
        }
    }

    record Order(
        long id,
        long customerId,
        double amount,
        OrderStatus status
    ) {
        Order {
            if (id <= 0 || customerId <= 0 ||
                    !Double.isFinite(amount) || amount < 0) {
                throw new DomainException("Invalid order data");
            }

            Objects.requireNonNull(status, "Order status is required");
        }
    }

    record CustomerSnapshot(
        long customerId,
        String customerName,
        long orderCount,
        long completedCount,
        double totalSpending,
        long version,
        Instant generatedAt
    ) {}

    record WorkloadMetrics(
        long readsPerHour,
        long writesPerHour,
        int duplicatedCopies,
        long expectedStalenessMillis,
        boolean eventualConsistencyRequired
    ) {}

    record PolicyDecision(
        boolean approved,
        List<String> reasons
    ) {
        PolicyDecision {
            reasons = List.copyOf(reasons);
        }
    }

    interface ProjectionListener {
        void onProjectionChanged(
            long customerId,
            ProjectionState state
        );
    }

    static final class Repository {
        private final Map<Long, Customer> customers = new HashMap<>();
        private final Map<Long, Order> orders = new HashMap<>();

        public synchronized void addCustomer(Customer customer) {
            Objects.requireNonNull(customer);

            if (customers.containsKey(customer.id())) {
                throw new DomainException("Duplicate customer");
            }

            boolean emailExists = customers.values().stream()
                .anyMatch(existing ->
                    existing.email().equalsIgnoreCase(customer.email()));

            if (emailExists) {
                throw new DomainException("Duplicate email");
            }

            customers.put(customer.id(), customer);
        }

        public synchronized void addOrder(Order order) {
            Objects.requireNonNull(order);

            if (!customers.containsKey(order.customerId())) {
                throw new DomainException("Unknown customer");
            }

            if (orders.containsKey(order.id())) {
                throw new DomainException("Duplicate order");
            }

            orders.put(order.id(), order);
        }

        public synchronized void updateCustomerName(
            long customerId,
            String name
        ) {
            Customer existing = customers.get(customerId);

            if (existing == null || name == null || name.isBlank()) {
                throw new DomainException("Invalid customer update");
            }

            customers.put(
                customerId,
                new Customer(customerId, name, existing.email())
            );
        }

        public synchronized Customer getCustomer(long id) {
            return customers.get(id);
        }

        public synchronized List<Customer> getCustomers() {
            return List.copyOf(customers.values());
        }

        public synchronized List<Order> getOrders() {
            return List.copyOf(orders.values());
        }

        public synchronized Map<Long, List<Order>> ordersByCustomer() {
            Map<Long, List<Order>> grouped = new HashMap<>();

            for (Order order : orders.values()) {
                grouped.computeIfAbsent(
                    order.customerId(),
                    ignored -> new ArrayList<>()
                ).add(order);
            }

            return grouped;
        }
    }

    static final class ProjectionPolicy {
        private final long minimumReadToWriteRatio;
        private final int maximumCopies;
        private final long maximumStalenessMillis;
        private final boolean allowEventualConsistency;

        ProjectionPolicy(
            long minimumReadToWriteRatio,
            int maximumCopies,
            long maximumStalenessMillis,
            boolean allowEventualConsistency
        ) {
            if (minimumReadToWriteRatio < 1 ||
                    maximumCopies < 1 ||
                    maximumStalenessMillis < 0) {
                throw new DomainException("Invalid projection policy");
            }

            this.minimumReadToWriteRatio = minimumReadToWriteRatio;
            this.maximumCopies = maximumCopies;
            this.maximumStalenessMillis = maximumStalenessMillis;
            this.allowEventualConsistency = allowEventualConsistency;
        }

        PolicyDecision evaluate(WorkloadMetrics metrics) {
            List<String> reasons = new ArrayList<>();

            if (metrics.readsPerHour() < 0 ||
                    metrics.writesPerHour() < 0 ||
                    metrics.duplicatedCopies() < 1 ||
                    metrics.expectedStalenessMillis() < 0) {
                throw new DomainException("Invalid workload metrics");
            }

            if (metrics.writesPerHour() == 0) {
                if (metrics.readsPerHour() == 0) {
                    reasons.add("No measurable workload");
                }
            } else if (metrics.readsPerHour() /
                    metrics.writesPerHour() < minimumReadToWriteRatio) {
                reasons.add("Read-to-write ratio is too low");
            }

            if (metrics.duplicatedCopies() > maximumCopies) {
                reasons.add("Too many duplicated copies");
            }

            if (metrics.expectedStalenessMillis() >
                    maximumStalenessMillis) {
                reasons.add("Staleness exceeds policy");
            }

            if (metrics.eventualConsistencyRequired() &&
                    !allowEventualConsistency) {
                reasons.add("Eventual consistency is prohibited");
            }

            return new PolicyDecision(reasons.isEmpty(), reasons);
        }
    }

    static final class ProjectionService {
        private final Repository repository;
        private final Map<Long, CustomerSnapshot> snapshots =
            new HashMap<>();
        private final Map<Long, ProjectionState> states =
            new HashMap<>();
        private final List<ProjectionListener> listeners =
            new ArrayList<>();
        private final AtomicLong version = new AtomicLong();

        ProjectionService(Repository repository) {
            this.repository = repository;
            rebuildAll();
        }

        synchronized void addListener(ProjectionListener listener) {
            listeners.add(Objects.requireNonNull(listener));
        }

        private void notifyListeners(
            long customerId,
            ProjectionState state
        ) {
            listeners.forEach(
                listener -> listener.onProjectionChanged(customerId, state)
            );
        }

        private CustomerSnapshot calculate(long customerId) {
            Customer customer = repository.getCustomer(customerId);

            if (customer == null) {
                throw new DomainException("Customer not found");
            }

            List<Order> orders = repository.ordersByCustomer()
                .getOrDefault(customerId, Collections.emptyList());

            long completedCount = 0;
            double total = 0;

            for (Order order : orders) {
                if (order.status() == OrderStatus.COMPLETED) {
                    completedCount++;
                    total += order.amount();
                }
            }

            return new CustomerSnapshot(
                customerId,
                customer.name(),
                orders.size(),
                completedCount,
                Math.round(total * 100.0) / 100.0,
                version.incrementAndGet(),
                Instant.now()
            );
        }

        synchronized void rebuildAll() {
            Map<Long, CustomerSnapshot> next = new HashMap<>();

            for (Customer customer : repository.getCustomers()) {
                next.put(customer.id(), calculate(customer.id()));
            }

            snapshots.clear();
            snapshots.putAll(next);

            for (Customer customer : repository.getCustomers()) {
                states.put(customer.id(), ProjectionState.CLEAN);
            }
        }

        synchronized void invalidate(long customerId) {
            if (repository.getCustomer(customerId) == null) {
                throw new DomainException("Unknown customer");
            }

            states.put(customerId, ProjectionState.DIRTY);
            notifyListeners(customerId, ProjectionState.DIRTY);
        }

        synchronized CustomerSnapshot refresh(long customerId) {
            states.put(customerId, ProjectionState.REBUILDING);
            notifyListeners(customerId, ProjectionState.REBUILDING);

            try {
                CustomerSnapshot updated = calculate(customerId);
                snapshots.put(customerId, updated);
                states.put(customerId, ProjectionState.CLEAN);
                notifyListeners(customerId, ProjectionState.CLEAN);
                return updated;
            } catch (RuntimeException exception) {
                states.put(customerId, ProjectionState.FAILED);
                notifyListeners(customerId, ProjectionState.FAILED);
                throw exception;
            }
        }

        CompletableFuture<CustomerSnapshot> refreshAsync(long customerId) {
            return CompletableFuture.supplyAsync(() -> {
                synchronized (this) {
                    return refresh(customerId);
                }
            });
        }

        synchronized CustomerSnapshot get(
            long customerId,
            ConsistencyMode mode
        ) {
            if (mode == ConsistencyMode.STRICT &&
                    states.get(customerId) != ProjectionState.CLEAN) {
                return refresh(customerId);
            }

            CustomerSnapshot snapshot = snapshots.get(customerId);

            if (snapshot == null) {
                throw new DomainException("Snapshot does not exist");
            }

            return snapshot;
        }

        synchronized List<CustomerSnapshot> getAll() {
            return snapshots.values().stream()
                .sorted(Comparator.comparingLong(
                    CustomerSnapshot::customerId
                ))
                .toList();
        }

        synchronized boolean validate() {
            if (states.values().stream().anyMatch(
                    state -> state != ProjectionState.CLEAN)) {
                return false;
            }

            for (Customer customer : repository.getCustomers()) {
                CustomerSnapshot expected = calculate(customer.id());
                CustomerSnapshot actual = snapshots.get(customer.id());

                if (actual == null ||
                        !actual.customerName().equals(expected.customerName()) ||
                        actual.orderCount() != expected.orderCount() ||
                        actual.completedCount() != expected.completedCount() ||
                        Math.abs(
                            actual.totalSpending() - expected.totalSpending()
                        ) > 0.000001) {
                    return false;
                }
            }

            return true;
        }

        synchronized Map<Long, ProjectionState> getStates() {
            return Map.copyOf(states);
        }
    }

    static final class ReadModelService {
        private final ProjectionService projection;

        ReadModelService(ProjectionService projection) {
            this.projection = projection;
        }

        CustomerSnapshot customerDashboard(long customerId) {
            return projection.get(customerId, ConsistencyMode.STRICT);
        }
    }

    public static void main(String[] args) {
        Repository repository = new Repository();

        repository.addCustomer(
            new Customer(1, "Aarav Sharma", "aarav@example.com")
        );

        repository.addCustomer(
            new Customer(2, "Diya Verma", "diya@example.com")
        );

        repository.addCustomer(
            new Customer(3, "Kabir Singh", "kabir@example.com")
        );

        repository.addOrder(
            new Order(101, 1, 1200, OrderStatus.COMPLETED)
        );

        repository.addOrder(
            new Order(102, 1, 800, OrderStatus.COMPLETED)
        );

        repository.addOrder(
            new Order(103, 1, 500, OrderStatus.PENDING)
        );

        repository.addOrder(
            new Order(104, 2, 2500, OrderStatus.COMPLETED)
        );

        repository.addOrder(
            new Order(105, 2, 300, OrderStatus.CANCELLED)
        );

        ProjectionService projection = new ProjectionService(repository);

        projection.addListener((id, state) ->
            System.out.println(
                "Customer " + id + " projection state: " + state
            )
        );

        ReadModelService dashboard = new ReadModelService(projection);

        System.out.println("INITIAL CUSTOMER DASHBOARDS");
        dashboard.customerDashboard(1);
        projection.getAll().forEach(System.out::println);

        // Source data remains authoritative.
        repository.addOrder(
            new Order(106, 1, 400, OrderStatus.COMPLETED)
        );

        projection.invalidate(1);

        System.out.println("\nEVENTUAL CONSISTENCY");
        System.out.println(
            projection.get(1, ConsistencyMode.EVENTUAL)
        );

        System.out.println("\nSTRICT CONSISTENCY");
        System.out.println(
            dashboard.customerDashboard(1)
        );

        repository.updateCustomerName(2, "Diya Sharma");
        projection.invalidate(2);

        try {
            projection.refreshAsync(2).join();
        } catch (CompletionException exception) {
            System.err.println("Refresh failed: " + exception.getCause());
        }

        ProjectionPolicy policy = new ProjectionPolicy(
            10, 3, 5000, true
        );

        PolicyDecision decision = policy.evaluate(
            new WorkloadMetrics(10000, 500, 2, 1000, true)
        );

        System.out.println("\nPOLICY DECISION");
        System.out.println(decision);

        System.out.println("\nPROJECTION STATES");
        System.out.println(projection.getStates());

        System.out.println("\nCONSISTENCY VALIDATION");
        System.out.println(projection.validate());

        try {
            repository.addOrder(
                new Order(107, 999, 100, OrderStatus.COMPLETED)
            );
        } catch (DomainException exception) {
            System.out.println(
                "EXPECTED VALIDATION FAILURE: " + exception.getMessage()
            );
        }

        projection.rebuildAll();

        System.out.println("\nFINAL VALIDATION");
        System.out.println(projection.validate());
    }
}
