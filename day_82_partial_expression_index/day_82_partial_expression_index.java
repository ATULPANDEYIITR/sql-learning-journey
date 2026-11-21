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
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/*
 * PARTIAL AND EXPRESSION INDEXES
 *
 * Enterprise index governance and advisory application.
 *
 * Demonstrates:
 * - Immutable domain records
 * - Expression-based keys
 * - Partial index policies
 * - Unique constraints
 * - Index lifecycle
 * - Predicate implication
 * - Workload analysis
 * - Transaction-like index maintenance
 * - Query eligibility
 * - Enterprise validation and reporting
 *
 * Runtime: Java 17
 */

public class PartialExpressionIndexDemo {

    // ========================================================
    // 1. ENUMERATIONS
    // ========================================================

    enum OrderStatus {
        OPEN,
        PAID,
        CANCELLED,
        ARCHIVED
    }

    enum IndexKind {
        FULL,
        PARTIAL,
        EXPRESSION,
        PARTIAL_EXPRESSION
    }

    enum IndexState {
        BUILDING,
        READY,
        INVALID,
        DROPPED
    }

    // ========================================================
    // 2. CUSTOM EXCEPTIONS
    // ========================================================

    static class DomainException extends RuntimeException {
        DomainException(String message) {
            super(message);
        }
    }

    static class UniqueConstraintException
            extends DomainException {
        UniqueConstraintException(String message) {
            super(message);
        }
    }

    static class IndexNotReadyException
            extends DomainException {
        IndexNotReadyException(String message) {
            super(message);
        }
    }

    // ========================================================
    // 3. ORDER DOMAIN
    // ========================================================

    record Order(
        long id,
        String email,
        OrderStatus status,
        BigDecimal amount,
        String region
    ) {
        Order {
            if (id <= 0) {
                throw new DomainException("Invalid order ID.");
            }

            Objects.requireNonNull(email);
            Objects.requireNonNull(status);
            Objects.requireNonNull(amount);
            Objects.requireNonNull(region);

            if (!email.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")) {
                throw new DomainException("Invalid email.");
            }

            if (amount.signum() < 0) {
                throw new DomainException("Negative amount.");
            }

            if (region.isBlank()) {
                throw new DomainException("Region is required.");
            }
        }
    }

    // ========================================================
    // 4. EXPRESSION POLICY
    // ========================================================

    interface KeyExpression {
        String name();

        Object evaluate(Order order);
    }

    static final class Expressions {

        private Expressions() {}

        static final KeyExpression EMAIL =
            new KeyExpression() {
                @Override
                public String name() {
                    return "email";
                }

                @Override
                public Object evaluate(Order order) {
                    return order.email();
                }
            };

        static final KeyExpression LOWER_EMAIL =
            new KeyExpression() {
                @Override
                public String name() {
                    return "lower(email)";
                }

                @Override
                public Object evaluate(Order order) {
                    return order.email().toLowerCase(
                        java.util.Locale.ROOT
                    );
                }
            };

        static final KeyExpression UPPER_REGION =
            new KeyExpression() {
                @Override
                public String name() {
                    return "upper(region)";
                }

                @Override
                public Object evaluate(Order order) {
                    return order.region().toUpperCase(
                        java.util.Locale.ROOT
                    );
                }
            };

        static final KeyExpression AMOUNT =
            new KeyExpression() {
                @Override
                public String name() {
                    return "amount";
                }

                @Override
                public Object evaluate(Order order) {
                    return order.amount();
                }
            };

        static final KeyExpression ORDER_ID =
            new KeyExpression() {
                @Override
                public String name() {
                    return "id";
                }

                @Override
                public Object evaluate(Order order) {
                    return order.id();
                }
            };

        static final Map<String, KeyExpression> REGISTRY =
            Map.of(
                "email", EMAIL,
                "lower(email)", LOWER_EMAIL,
                "upper(region)", UPPER_REGION,
                "amount", AMOUNT,
                "id", ORDER_ID
            );

        static KeyExpression get(String name) {
            KeyExpression expression = REGISTRY.get(name);

            if (expression == null) {
                throw new DomainException(
                    "Unsupported expression: " + name
                );
            }

            return expression;
        }
    }

    // ========================================================
    // 5. PARTIAL INDEX PREDICATE
    // ========================================================

    record IndexPredicate(
        Optional<OrderStatus> status,
        Optional<BigDecimal> minimumAmount,
        boolean strictMinimum
    ) {
        IndexPredicate {
            Objects.requireNonNull(status);
            Objects.requireNonNull(minimumAmount);
        }

        boolean matches(Order order) {
            if (
                status.isPresent() &&
                order.status() != status.get()
            ) {
                return false;
            }

            if (minimumAmount.isPresent()) {
                int comparison = order.amount().compareTo(
                    minimumAmount.get()
                );

                if (
                    strictMinimum
                    ? comparison <= 0
                    : comparison < 0
                ) {
                    return false;
                }
            }

            return true;
        }

        String description() {
            List<String> parts = new ArrayList<>();

            status.ifPresent(
                value -> parts.add("status = " + value)
            );

            minimumAmount.ifPresent(
                value -> parts.add(
                    "amount " +
                    (strictMinimum ? "> " : ">= ") +
                    value
                )
            );

            return parts.isEmpty()
                ? "TRUE"
                : String.join(" AND ", parts);
        }
    }

    // ========================================================
    // 6. PREDICATE IMPLICATION
    // ========================================================

    static final class PredicateImplication {

        private PredicateImplication() {}

        static boolean implies(
            IndexPredicate query,
            IndexPredicate index
        ) {
            if (index.status().isPresent()) {
                if (
                    query.status().isEmpty() ||
                    query.status().get() != index.status().get()
                ) {
                    return false;
                }
            }

            if (index.minimumAmount().isPresent()) {
                if (query.minimumAmount().isEmpty()) {
                    return false;
                }

                int comparison = query.minimumAmount()
                    .get()
                    .compareTo(index.minimumAmount().get());

                if (index.strictMinimum()) {
                    if (
                        query.strictMinimum()
                        ? comparison < 0
                        : comparison <= 0
                    ) {
                        return false;
                    }
                } else if (comparison < 0) {
                    return false;
                }
            }

            return true;
        }
    }

    // ========================================================
    // 7. INDEX DEFINITION
    // ========================================================

    record IndexDefinition(
        String name,
        IndexKind kind,
        KeyExpression expression,
        Optional<IndexPredicate> predicate,
        boolean unique
    ) {
        IndexDefinition {
            if (name == null || !name.matches("[a-z][a-z0-9_]*")) {
                throw new DomainException("Invalid index name.");
            }

            Objects.requireNonNull(kind);
            Objects.requireNonNull(expression);
            Objects.requireNonNull(predicate);

            boolean requiresPredicate =
                kind == IndexKind.PARTIAL ||
                kind == IndexKind.PARTIAL_EXPRESSION;

            if (requiresPredicate != predicate.isPresent()) {
                throw new DomainException(
                    "Inconsistent index definition."
                );
            }
        }
    }

    // ========================================================
    // 8. INDEX STORAGE
    // ========================================================

    static final class ManagedIndex {

        private final IndexDefinition definition;

        private final Map<Object, Set<Long>> entries =
            new HashMap<>();

        private IndexState state = IndexState.BUILDING;

        ManagedIndex(IndexDefinition definition) {
            this.definition = definition;
        }

        IndexDefinition definition() {
            return definition;
        }

        IndexState state() {
            return state;
        }

        void markReady() {
            state = IndexState.READY;
        }

        void markInvalid() {
            state = IndexState.INVALID;
            entries.clear();
        }

        void markDropped() {
            state = IndexState.DROPPED;
            entries.clear();
        }

        Map<Object, Set<Long>> snapshot() {
            Map<Object, Set<Long>> copy = new HashMap<>();

            entries.forEach(
                (key, ids) -> copy.put(key, new HashSet<>(ids))
            );

            return copy;
        }

        void restore(Map<Object, Set<Long>> snapshot) {
            entries.clear();

            snapshot.forEach(
                (key, ids) -> entries.put(
                    key,
                    new HashSet<>(ids)
                )
            );
        }

        void insert(Order order) {
            if (
                definition.predicate().isPresent() &&
                !definition.predicate().get().matches(order)
            ) {
                return;
            }

            Object key = definition.expression().evaluate(order);

            Set<Long> ids = entries.computeIfAbsent(
                key,
                ignored -> new HashSet<>()
            );

            if (
                definition.unique() &&
                !ids.isEmpty() &&
                !ids.contains(order.id())
            ) {
                throw new UniqueConstraintException(
                    "Unique index violation: " +
                    definition.name()
                );
            }

            ids.add(order.id());
        }

        void remove(Order order) {
            Object key = definition.expression().evaluate(order);

            Set<Long> ids = entries.get(key);

            if (ids == null) {
                return;
            }

            ids.remove(order.id());

            if (ids.isEmpty()) {
                entries.remove(key);
            }
        }

        int distinctKeyCount() {
            return entries.size();
        }

        boolean contains(Object key, long id) {
            return entries.getOrDefault(
                key,
                Collections.emptySet()
            ).contains(id);
        }
    }

    // ========================================================
    // 9. REPOSITORY SERVICE
    // ========================================================

    static final class OrderRepository {

        private final Map<Long, Order> orders =
            new ConcurrentHashMap<>();

        private final Map<String, ManagedIndex> indexes =
            new HashMap<>();

        synchronized void addIndex(IndexDefinition definition) {
            if (indexes.containsKey(definition.name())) {
                throw new DomainException("Duplicate index.");
            }

            ManagedIndex index = new ManagedIndex(definition);

            try {
                for (Order order : orders.values()) {
                    index.insert(order);
                }

                index.markReady();
                indexes.put(definition.name(), index);

            } catch (RuntimeException exception) {
                index.markInvalid();
                throw exception;
            }
        }

        synchronized void insert(Order order) {
            if (orders.containsKey(order.id())) {
                throw new DomainException("Duplicate order ID.");
            }

            List<ManagedIndex> completed = new ArrayList<>();

            try {
                for (ManagedIndex index : indexes.values()) {
                    index.insert(order);
                    completed.add(index);
                }

                orders.put(order.id(), order);

            } catch (RuntimeException exception) {
                completed.forEach(index -> index.remove(order));
                throw exception;
            }
        }

        synchronized void update(long id, Order replacement) {
            Order previous = orders.get(id);

            if (previous == null) {
                throw new DomainException("Order not found.");
            }

            if (replacement.id() != id) {
                throw new DomainException("Order ID cannot change.");
            }

            Map<String, Map<Object, Set<Long>>> snapshots =
                new HashMap<>();

            indexes.forEach(
                (name, index) -> snapshots.put(
                    name,
                    index.snapshot()
                )
            );

            try {
                for (ManagedIndex index : indexes.values()) {
                    index.remove(previous);
                    index.insert(replacement);
                }

                orders.put(id, replacement);

            } catch (RuntimeException exception) {
                indexes.forEach(
                    (name, index) -> index.restore(
                        snapshots.get(name)
                    )
                );

                throw exception;
            }
        }

        synchronized Optional<ManagedIndex> index(String name) {
            return Optional.ofNullable(indexes.get(name));
        }

        synchronized List<Order> allOrders() {
            return List.copyOf(orders.values());
        }

        synchronized List<ManagedIndex> allIndexes() {
            return List.copyOf(indexes.values());
        }
    }

    // ========================================================
    // 10. QUERY MODEL
    // ========================================================

    record QuerySpecification(
        KeyExpression expression,
        Object value,
        Optional<IndexPredicate> predicate
    ) {
        QuerySpecification {
            Objects.requireNonNull(expression);
            Objects.requireNonNull(value);
            Objects.requireNonNull(predicate);
        }
    }

    // ========================================================
    // 11. ELIGIBILITY SERVICE
    // ========================================================

    static final class IndexEligibilityService {

        boolean isEligible(
            ManagedIndex index,
            QuerySpecification query
        ) {
            if (index.state() != IndexState.READY) {
                return false;
            }

            if (!index.definition().expression().name()
                    .equals(query.expression().name())) {
                return false;
            }

            if (index.definition().predicate().isEmpty()) {
                return true;
            }

            if (query.predicate().isEmpty()) {
                return false;
            }

            return PredicateImplication.implies(
                query.predicate().get(),
                index.definition().predicate().get()
            );
        }

        List<ManagedIndex> eligibleIndexes(
            OrderRepository repository,
            QuerySpecification query
        ) {
            return repository.allIndexes()
                .stream()
                .filter(index -> isEligible(index, query))
                .sorted(
                    Comparator.comparingInt(
                        ManagedIndex::distinctKeyCount
                    )
                )
                .toList();
        }
    }

    // ========================================================
    // 12. QUERY EXECUTION SERVICE
    // ========================================================

    static final class QueryExecutionService {

        private final OrderRepository repository;
        private final IndexEligibilityService eligibility;

        QueryExecutionService(OrderRepository repository) {
            this.repository = repository;
            this.eligibility = new IndexEligibilityService();
        }

        List<Order> execute(QuerySpecification query) {
            List<ManagedIndex> candidates =
                eligibility.eligibleIndexes(repository, query);

            if (!candidates.isEmpty()) {
                ManagedIndex selected = candidates.get(0);

                if (selected.state() != IndexState.READY) {
                    throw new IndexNotReadyException(
                        selected.definition().name()
                    );
                }
            }

            // This implementation executes against the in-memory
            // repository. Eligibility is advisory; a production
            // database performs physical query planning itself.
            return repository.allOrders()
                .stream()
                .filter(order ->
                    query.predicate().isEmpty() ||
                    query.predicate().get().matches(order)
                )
                .filter(order ->
                    query.expression().evaluate(order)
                        .equals(query.value())
                )
                .toList();
        }
    }

    // ========================================================
    // 13. WORKLOAD ANALYSIS
    // ========================================================

    static final class WorkloadAnalyzer {

        private final Map<String, Long> frequency =
            new HashMap<>();

        void record(QuerySpecification query) {
            String key = query.expression().name() +
                "|" +
                query.predicate()
                    .map(IndexPredicate::description)
                    .orElse("NONE");

            frequency.merge(key, 1L, Long::sum);
        }

        Map<String, Long> rankedWorkload() {
            return frequency.entrySet()
                .stream()
                .sorted(
                    Map.Entry.<String, Long>comparingByValue()
                        .reversed()
                )
                .collect(
                    Collectors.toMap(
                        Map.Entry::getKey,
                        Map.Entry::getValue,
                        (a, b) -> a,
                        java.util.LinkedHashMap::new
                    )
                );
        }
    }

    // ========================================================
    // 14. REPORTING
    // ========================================================

    static void report(
        OrderRepository repository,
        QuerySpecification query
    ) {
        IndexEligibilityService service =
            new IndexEligibilityService();

        List<ManagedIndex> eligible =
            service.eligibleIndexes(repository, query);

        System.out.println("\nExpression: " +
            query.expression().name());

        System.out.println("Value: " + query.value());

        System.out.println("Predicate: " +
            query.predicate()
                .map(IndexPredicate::description)
                .orElse("NONE"));

        if (eligible.isEmpty()) {
            System.out.println("No eligible index.");
        } else {
            System.out.println("Eligible indexes:");

            eligible.forEach(index ->
                System.out.println(
                    index.definition().name() +
                    " | distinct keys: " +
                    index.distinctKeyCount()
                )
            );
        }
    }

    // ========================================================
    // 15. APPLICATION ENTRY POINT
    // ========================================================

    public static void main(String[] args) {

        OrderRepository repository = new OrderRepository();

        repository.insert(new Order(
            1,
            "alice@example.com",
            OrderStatus.OPEN,
            new BigDecimal("450"),
            "NORTH"
        ));

        repository.insert(new Order(
            2,
            "bob@example.com",
            OrderStatus.PAID,
            new BigDecimal("900"),
            "SOUTH"
        ));

        repository.insert(new Order(
            3,
            "carol@example.com",
            OrderStatus.OPEN,
            new BigDecimal("250"),
            "NORTH"
        ));

        repository.insert(new Order(
            4,
            "david@example.com",
            OrderStatus.CANCELLED,
            new BigDecimal("120"),
            "WEST"
        ));

        repository.insert(new Order(
            5,
            "eve@example.com",
            OrderStatus.ARCHIVED,
            new BigDecimal("300"),
            "EAST"
        ));

        repository.insert(new Order(
            6,
            "frank@example.com",
            OrderStatus.OPEN,
            new BigDecimal("780"),
            "SOUTH"
        ));

        IndexPredicate openOnly = new IndexPredicate(
            Optional.of(OrderStatus.OPEN),
            Optional.empty(),
            true
        );

        IndexPredicate highValueOpen = new IndexPredicate(
            Optional.of(OrderStatus.OPEN),
            Optional.of(new BigDecimal("300")),
            true
        );

        repository.addIndex(new IndexDefinition(
            "idx_open_orders",
            IndexKind.PARTIAL,
            Expressions.ORDER_ID,
            Optional.of(openOnly),
            false
        ));

        repository.addIndex(new IndexDefinition(
            "idx_lower_email",
            IndexKind.EXPRESSION,
            Expressions.LOWER_EMAIL,
            Optional.empty(),
            false
        ));

        repository.addIndex(new IndexDefinition(
            "idx_open_high_value",
            IndexKind.PARTIAL_EXPRESSION,
            Expressions.AMOUNT,
            Optional.of(highValueOpen),
            false
        ));

        repository.addIndex(new IndexDefinition(
            "idx_upper_region",
            IndexKind.EXPRESSION,
            Expressions.UPPER_REGION,
            Optional.empty(),
            false
        ));

        QuerySpecification emailQuery = new QuerySpecification(
            Expressions.LOWER_EMAIL,
            "alice@example.com",
            Optional.empty()
        );

        QuerySpecification amountQuery = new QuerySpecification(
            Expressions.AMOUNT,
            new BigDecimal("780"),
            Optional.of(highValueOpen)
        );

        report(repository, emailQuery);
        report(repository, amountQuery);

        QueryExecutionService queryService =
            new QueryExecutionService(repository);

        List<Order> matching = queryService.execute(emailQuery);

        System.out.println("\nEmail query result count: " +
            matching.size());

        if (matching.size() != 1) {
            throw new DomainException("Email query assertion failed.");
        }

        System.out.println("\nINDEX MAINTENANCE");

        repository.update(
            1,
            new Order(
                1,
                "alice@example.com",
                OrderStatus.PAID,
                new BigDecimal("450"),
                "NORTH"
            )
        );

        repository.index("idx_open_orders")
            .ifPresent(index ->
                System.out.println(
                    "Open index keys after update: " +
                    index.distinctKeyCount()
                )
            );

        System.out.println("\nWORKLOAD ANALYSIS");

        WorkloadAnalyzer workload = new WorkloadAnalyzer();

        for (int i = 0; i < 100; i++) {
            workload.record(emailQuery);
        }

        for (int i = 0; i < 40; i++) {
            workload.record(amountQuery);
        }

        workload.rankedWorkload().forEach(
            (query, frequency) ->
                System.out.println(query + " = " + frequency)
        );

        System.out.println("\nVALIDATION");

        try {
            repository.insert(new Order(
                7,
                "invalid",
                OrderStatus.OPEN,
                new BigDecimal("100"),
                "NORTH"
            ));

            throw new DomainException(
                "Invalid record was accepted."
            );

        } catch (DomainException exception) {
            System.out.println(
                "Invalid record rejected: " +
                exception.getMessage()
            );
        }

        System.out.println("\nExecution completed successfully.");
    }
}
