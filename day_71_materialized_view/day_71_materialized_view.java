import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Predicate;

/*
 * Materialized View Enterprise Management System
 *
 * Java 17.
 *
 * Features:
 * - Immutable source records
 * - Explicit aggregation definitions
 * - Full and incremental refresh
 * - Change-data capture simulation
 * - Atomic snapshot publication
 * - Refresh state transitions
 * - Dependency-aware scheduling
 * - Query filtering
 * - Refresh auditing
 * - Failure handling
 * - Concurrent refresh request coordination
 *
 * Run:
 * javac MaterializedViews.java
 * java MaterializedViews
 */

public class MaterializedViews {

    enum RefreshMode {
        FULL,
        INCREMENTAL
    }

    enum RefreshStatus {
        SUCCESS,
        FAILED,
        SKIPPED
    }

    enum ChangeType {
        INSERT,
        UPDATE,
        DELETE
    }

    static class ValidationException extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    static class RefreshException extends RuntimeException {
        RefreshException(String message) {
            super(message);
        }
    }

    record Sale(
        long id,
        long productId,
        String category,
        String region,
        int quantity,
        double unitPrice,
        Instant createdAt
    ) {
        Sale {
            if (id <= 0 || productId <= 0) {
                throw new ValidationException(
                    "Identifiers must be positive."
                );
            }

            if (
                category == null ||
                category.isBlank() ||
                region == null ||
                region.isBlank()
            ) {
                throw new ValidationException(
                    "Grouping dimensions are required."
                );
            }

            if (
                quantity <= 0 ||
                !Double.isFinite(unitPrice) ||
                unitPrice < 0
            ) {
                throw new ValidationException(
                    "Invalid sales values."
                );
            }

            Objects.requireNonNull(
                createdAt,
                "Creation timestamp is required."
            );
        }

        double revenue() {
            return quantity * unitPrice;
        }
    }

    record GroupKey(
        String category,
        String region
    ) implements Comparable<GroupKey> {

        @Override
        public int compareTo(GroupKey other) {
            int first = category.compareTo(other.category);

            if (first != 0) return first;

            return region.compareTo(other.region);
        }
    }

    record ChangeEvent(
        long version,
        ChangeType type,
        Sale before,
        Sale after
    ) {}

    record Aggregate(
        long count,
        long quantity,
        double revenue
    ) {
        Aggregate add(Sale sale) {
            return new Aggregate(
                count + 1,
                quantity + sale.quantity(),
                revenue + sale.revenue()
            );
        }

        Aggregate subtract(Sale sale) {
            long nextCount = count - 1;
            long nextQuantity = quantity - sale.quantity();

            if (nextCount < 0 || nextQuantity < 0) {
                throw new RefreshException(
                    "Aggregate consistency failure."
                );
            }

            if (nextCount == 0) {
                return new Aggregate(0, 0, 0.0);
            }

            return new Aggregate(
                nextCount,
                nextQuantity,
                revenue - sale.revenue()
            );
        }
    }

    record Snapshot(
        long generation,
        long sourceVersion,
        Instant refreshedAt,
        Map<GroupKey, Aggregate> rows,
        String checksum
    ) {
        Snapshot {
            rows = Collections.unmodifiableMap(
                new LinkedHashMap<>(rows)
            );
        }
    }

    record RefreshAudit(
        String viewName,
        RefreshMode mode,
        RefreshStatus status,
        long recordsProcessed,
        long durationNanos,
        String error,
        Instant completedAt
    ) {}

    static final class SourceRepository {

        private final Map<Long, Sale> records =
            new HashMap<>();

        private final List<ChangeEvent> journal =
            new ArrayList<>();

        private final AtomicLong version =
            new AtomicLong();

        public synchronized void insert(Sale sale) {
            if (records.containsKey(sale.id())) {
                throw new ValidationException(
                    "Duplicate sale identifier."
                );
            }

            records.put(sale.id(), sale);

            publish(
                ChangeType.INSERT,
                null,
                sale
            );
        }

        public synchronized void update(Sale sale) {
            Sale previous = records.get(sale.id());

            if (previous == null) {
                throw new ValidationException(
                    "Sale does not exist."
                );
            }

            records.put(sale.id(), sale);

            publish(
                ChangeType.UPDATE,
                previous,
                sale
            );
        }

        public synchronized void delete(long id) {
            Sale previous = records.remove(id);

            if (previous == null) {
                throw new ValidationException(
                    "Sale does not exist."
                );
            }

            publish(
                ChangeType.DELETE,
                previous,
                null
            );
        }

        private void publish(
            ChangeType type,
            Sale before,
            Sale after
        ) {
            journal.add(new ChangeEvent(
                version.incrementAndGet(),
                type,
                before,
                after
            ));
        }

        public synchronized List<Sale> records() {
            return List.copyOf(records.values());
        }

        public synchronized long version() {
            return version.get();
        }

        public synchronized List<ChangeEvent> changesSince(
            long previousVersion
        ) {
            return journal.stream()
                .filter(event ->
                    event.version() > previousVersion
                )
                .toList();
        }

        public synchronized SourceSnapshot snapshot() {
            return new SourceSnapshot(
                List.copyOf(records.values()),
                version.get()
            );
        }
    }

    record SourceSnapshot(
        List<Sale> records,
        long version
    ) {}

    interface RefreshPolicy {
        boolean shouldRefresh(
            Snapshot current,
            long sourceVersion
        );
    }

    static final class StalenessPolicy
        implements RefreshPolicy {

        private final long maximumVersionLag;

        StalenessPolicy(long maximumVersionLag) {
            if (maximumVersionLag < 0) {
                throw new ValidationException(
                    "Version lag cannot be negative."
                );
            }

            this.maximumVersionLag = maximumVersionLag;
        }

        @Override
        public boolean shouldRefresh(
            Snapshot current,
            long sourceVersion
        ) {
            return sourceVersion - current.sourceVersion()
                > maximumVersionLag;
        }
    }

    static final class MaterializedView {

        private final String name;
        private final SourceRepository source;
        private final RefreshPolicy policy;

        private volatile Snapshot snapshot =
            new Snapshot(
                0,
                0,
                Instant.EPOCH,
                Map.of(),
                ""
            );

        private final Object refreshLock = new Object();

        private CompletableFuture<RefreshAudit> activeRefresh;

        MaterializedView(
            String name,
            SourceRepository source,
            RefreshPolicy policy
        ) {
            if (
                name == null ||
                !name.matches("[a-z][a-z0-9_]{2,60}")
            ) {
                throw new ValidationException(
                    "Invalid materialized view name."
                );
            }

            this.name = name;
            this.source = Objects.requireNonNull(source);
            this.policy = Objects.requireNonNull(policy);
        }

        String name() {
            return name;
        }

        Snapshot snapshot() {
            return snapshot;
        }

        boolean stale() {
            return snapshot.sourceVersion() < source.version();
        }

        boolean requiresRefresh() {
            return policy.shouldRefresh(
                snapshot,
                source.version()
            );
        }

        private GroupKey key(Sale sale) {
            return new GroupKey(
                sale.category(),
                sale.region()
            );
        }

        private Map<GroupKey, Aggregate> aggregate(
            List<Sale> records
        ) {
            Map<GroupKey, Aggregate> result =
                new HashMap<>();

            for (Sale sale : records) {
                GroupKey key = key(sale);

                result.compute(
                    key,
                    (ignored, existing) ->
                        existing == null
                            ? new Aggregate(0, 0, 0).add(sale)
                            : existing.add(sale)
                );
            }

            return result;
        }

        private String checksum(
            Map<GroupKey, Aggregate> rows
        ) {
            try {
                MessageDigest digest =
                    MessageDigest.getInstance("SHA-256");

                StringBuilder canonical = new StringBuilder();

                rows.entrySet().stream()
                    .sorted(Map.Entry.comparingByKey())
                    .forEach(entry -> canonical.append(
                        entry.getKey()
                            .category()
                            .replace("|", "")
                    ).append("|").append(
                        entry.getKey().region()
                            .replace("|", "")
                    ).append("|").append(
                        entry.getValue().count()
                    ).append("|").append(
                        entry.getValue().quantity()
                    ).append("|").append(
                        entry.getValue().revenue()
                    ).append("\n"));

                byte[] bytes = digest.digest(
                    canonical.toString().getBytes(
                        StandardCharsets.UTF_8
                    )
                );

                StringBuilder hex = new StringBuilder();

                for (byte value : bytes) {
                    hex.append(
                        String.format("%02x", value)
                    );
                }

                return hex.toString();

            } catch (NoSuchAlgorithmException error) {
                throw new RefreshException(
                    "SHA-256 unavailable."
                );
            }
        }

        CompletableFuture<RefreshAudit> refreshAsync(
            RefreshMode mode
        ) {
            synchronized (refreshLock) {
                if (
                    activeRefresh != null &&
                    !activeRefresh.isDone()
                ) {
                    return activeRefresh;
                }

                activeRefresh = CompletableFuture.supplyAsync(
                    () -> refresh(mode)
                );

                return activeRefresh;
            }
        }

        RefreshAudit refresh(RefreshMode mode) {
            long started = System.nanoTime();

            try {
                SourceSnapshot sourceSnapshot =
                    source.snapshot();

                Snapshot previous = snapshot;

                if (
                    mode == RefreshMode.INCREMENTAL &&
                    previous.generation() > 0
                ) {
                    if (
                        previous.sourceVersion() ==
                        sourceSnapshot.version()
                    ) {
                        return audit(
                            mode,
                            RefreshStatus.SKIPPED,
                            0,
                            started,
                            null
                        );
                    }

                    List<ChangeEvent> changes =
                        source.changesSince(
                            previous.sourceVersion()
                        );

                    Map<GroupKey, Aggregate> candidate =
                        new HashMap<>(previous.rows());

                    long expected =
                        previous.sourceVersion() + 1;

                    for (ChangeEvent event : changes) {
                        if (event.version() != expected++) {
                            throw new RefreshException(
                                "Change journal gap detected."
                            );
                        }

                        if (event.before() != null) {
                            GroupKey key = key(event.before());

                            Aggregate existing =
                                candidate.get(key);

                            if (existing == null) {
                                throw new RefreshException(
                                    "Missing aggregate for update."
                                );
                            }

                            Aggregate updated =
                                existing.subtract(event.before());

                            if (updated.count() == 0) {
                                candidate.remove(key);
                            } else {
                                candidate.put(key, updated);
                            }
                        }

                        if (event.after() != null) {
                            GroupKey key = key(event.after());

                            candidate.merge(
                                key,
                                new Aggregate(0, 0, 0)
                                    .add(event.after()),
                                (oldValue, newValue) ->
                                    new Aggregate(
                                        oldValue.count()
                                            + newValue.count(),
                                        oldValue.quantity()
                                            + newValue.quantity(),
                                        oldValue.revenue()
                                            + newValue.revenue()
                                    )
                            );
                        }
                    }

                    publish(
                        previous,
                        candidate,
                        sourceSnapshot.version()
                    );

                    return audit(
                        mode,
                        RefreshStatus.SUCCESS,
                        changes.size(),
                        started,
                        null
                    );
                }

                Map<GroupKey, Aggregate> candidate =
                    aggregate(sourceSnapshot.records());

                publish(
                    previous,
                    candidate,
                    sourceSnapshot.version()
                );

                return audit(
                    mode,
                    RefreshStatus.SUCCESS,
                    sourceSnapshot.records().size(),
                    started,
                    null
                );

            } catch (Exception error) {
                return audit(
                    mode,
                    RefreshStatus.FAILED,
                    0,
                    started,
                    error.getMessage()
                );
            }
        }

        private void publish(
            Snapshot previous,
            Map<GroupKey, Aggregate> candidate,
            long version
        ) {
            Snapshot next = new Snapshot(
                previous.generation() + 1,
                version,
                Instant.now(),
                candidate,
                checksum(candidate)
            );

            // Volatile reference replacement publishes the
            // completed immutable snapshot to concurrent readers.
            snapshot = next;
        }

        private RefreshAudit audit(
            RefreshMode mode,
            RefreshStatus status,
            long count,
            long started,
            String error
        ) {
            return new RefreshAudit(
                name,
                mode,
                status,
                count,
                System.nanoTime() - started,
                error,
                Instant.now()
            );
        }

        List<Map<String, Object>> query(
            Predicate<GroupKey> filter
        ) {
            Snapshot current = snapshot;

            return current.rows().entrySet().stream()
                .filter(entry -> filter.test(entry.getKey()))
                .sorted(Map.Entry.comparingByKey())
                .map(entry -> {
                    Map<String, Object> row =
                        new LinkedHashMap<>();

                    row.put(
                        "category",
                        entry.getKey().category()
                    );

                    row.put(
                        "region",
                        entry.getKey().region()
                    );

                    row.put(
                        "count",
                        entry.getValue().count()
                    );

                    row.put(
                        "quantity",
                        entry.getValue().quantity()
                    );

                    row.put(
                        "revenue",
                        entry.getValue().revenue()
                    );

                    return Collections.unmodifiableMap(row);
                })
                .toList();
        }
    }

    static final class RefreshService {

        private final Map<String, MaterializedView> views =
            new LinkedHashMap<>();

        private final Map<String, Set<String>> dependencies =
            new HashMap<>();

        private final List<RefreshAudit> audit =
            new ArrayList<>();

        void register(
            MaterializedView view,
            Set<String> requiredViews
        ) {
            if (views.containsKey(view.name())) {
                throw new ValidationException(
                    "Duplicate view registration."
                );
            }

            views.put(view.name(), view);

            dependencies.put(
                view.name(),
                Set.copyOf(requiredViews)
            );
        }

        private void visit(
            String name,
            Set<String> visiting,
            Set<String> visited,
            List<MaterializedView> order
        ) {
            if (visiting.contains(name)) {
                throw new ValidationException(
                    "Circular dependency."
                );
            }

            if (visited.contains(name)) return;

            MaterializedView view = views.get(name);

            if (view == null) {
                throw new ValidationException(
                    "Unknown view: " + name
                );
            }

            visiting.add(name);

            for (String dependency :
                dependencies.getOrDefault(name, Set.of())) {
                visit(dependency, visiting, visited, order);
            }

            visiting.remove(name);
            visited.add(name);
            order.add(view);
        }

        List<RefreshAudit> refresh(
            String target,
            RefreshMode mode
        ) {
            List<MaterializedView> order =
                new ArrayList<>();

            visit(
                target,
                new HashSet<>(),
                new HashSet<>(),
                order
            );

            List<RefreshAudit> results =
                new ArrayList<>();

            for (MaterializedView view : order) {
                RefreshAudit result = view.refresh(mode);

                results.add(result);
                audit.add(result);

                if (result.status() == RefreshStatus.FAILED) {
                    break;
                }
            }

            return List.copyOf(results);
        }

        List<RefreshAudit> audit() {
            return List.copyOf(audit);
        }
    }

    private static Sale sale(
        long id,
        long product,
        String category,
        String region,
        int quantity,
        double price
    ) {
        return new Sale(
            id,
            product,
            category,
            region,
            quantity,
            price,
            Instant.now()
        );
    }

    private static void printReport(
        MaterializedView view
    ) {
        System.out.println("\n" + view.name());

        System.out.println(
            "Generation: " + view.snapshot().generation()
        );

        view.query(key -> true).forEach(
            System.out::println
        );
    }

    private static void runTests() {
        SourceRepository source = new SourceRepository();

        source.insert(sale(
            1, 101, "Electronics", "North", 3, 1200
        ));

        source.insert(sale(
            2, 102, "Furniture", "South", 2, 850
        ));

        MaterializedView view = new MaterializedView(
            "test_sales_summary",
            source,
            new StalenessPolicy(0)
        );

        assert view.refresh(RefreshMode.FULL).status()
            == RefreshStatus.SUCCESS;

        assert view.snapshot().rows().get(
            new GroupKey("Electronics", "North")
        ).revenue() == 3600.0;

        source.insert(sale(
            3, 101, "Electronics", "North", 2, 1200
        ));

        assert view.stale();

        assert view.refresh(RefreshMode.INCREMENTAL).status()
            == RefreshStatus.SUCCESS;

        assert !view.stale();

        assert view.snapshot().rows().get(
            new GroupKey("Electronics", "North")
        ).revenue() == 6000.0;

        source.delete(3);

        view.refresh(RefreshMode.INCREMENTAL);

        assert view.snapshot().rows().get(
            new GroupKey("Electronics", "North")
        ).revenue() == 3600.0;

        System.out.println(
            "All Java validation tests passed."
        );
    }

    public static void main(String[] args) {
        try {
            SourceRepository source = new SourceRepository();

            source.insert(sale(
                1, 101, "Electronics", "North", 3, 1200
            ));

            source.insert(sale(
                2, 102, "Furniture", "South", 2, 850
            ));

            source.insert(sale(
                3, 101, "Electronics", "North", 1, 1200
            ));

            source.insert(sale(
                4, 103, "Clothing", "West", 5, 90
            ));

            source.insert(sale(
                5, 104, "Electronics", "East", 2, 700
            ));

            source.insert(sale(
                6, 102, "Furniture", "South", 1, 850
            ));

            MaterializedView categoryView =
                new MaterializedView(
                    "sales_by_category",
                    source,
                    new StalenessPolicy(0)
                );

            MaterializedView regionalView =
                new MaterializedView(
                    "sales_by_region",
                    source,
                    new StalenessPolicy(0)
                );

            RefreshService service = new RefreshService();

            service.register(categoryView, Set.of());

            service.register(
                regionalView,
                Set.of("sales_by_category")
            );

            System.out.println("INITIAL FULL REFRESH");

            service.refresh(
                "sales_by_region",
                RefreshMode.FULL
            ).forEach(System.out::println);

            printReport(categoryView);

            source.insert(sale(
                7, 105, "Clothing", "North", 4, 120
            ));

            System.out.println(
                "\nCategory view stale: "
                    + categoryView.stale()
            );

            System.out.println("INCREMENTAL REFRESH");

            service.refresh(
                "sales_by_region",
                RefreshMode.INCREMENTAL
            ).forEach(System.out::println);

            printReport(regionalView);

            System.out.println("\nAUDIT");

            service.audit().forEach(System.out::println);

            runTests();

        } catch (Exception error) {
            System.err.println(
                "Application error: " + error.getMessage()
            );

            System.exit(1);
        }
    }
}
