import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/*
 * Index Trade-offs: Write Overhead, Storage, Maintenance
 * and Over-Indexing.
 *
 * Enterprise-oriented Java 17 implementation.
 *
 * Models:
 * - Immutable index definitions
 * - Database table metadata
 * - Workload registration
 * - Index maintenance
 * - Composite and covering indexes
 * - Approval-based index lifecycle
 * - Storage budgets
 * - Write amplification
 * - Index governance
 * - Operational audit events
 */

public class IndexTradeoffs {

    enum IndexType {
        BTREE,
        HASH,
        COMPOSITE,
        COVERING
    }

    enum IndexStatus {
        ACTIVE,
        DISABLED,
        NEEDS_REBUILD
    }

    enum Operation {
        SELECT,
        INSERT,
        UPDATE,
        DELETE
    }

    enum Decision {
        RETAIN,
        REVIEW,
        REBUILD,
        DISABLE_CANDIDATE
    }

    record IndexDefinition(
        String name,
        List<String> keyColumns,
        List<String> includedColumns,
        IndexType type,
        boolean unique
    ) {
        IndexDefinition {
            Objects.requireNonNull(name);
            Objects.requireNonNull(keyColumns);
            Objects.requireNonNull(includedColumns);
            Objects.requireNonNull(type);

            if (name.isBlank() || keyColumns.isEmpty()) {
                throw new IllegalArgumentException(
                    "Index name and key columns are required"
                );
            }

            keyColumns = List.copyOf(keyColumns);
            includedColumns = List.copyOf(includedColumns);

            if (new HashSet<>(keyColumns).size()
                    != keyColumns.size()) {
                throw new IllegalArgumentException(
                    "Duplicate index key columns"
                );
            }

            if (includedColumns.stream()
                    .anyMatch(keyColumns::contains)) {
                throw new IllegalArgumentException(
                    "Included columns cannot repeat key columns"
                );
            }

            if (type == IndexType.COMPOSITE
                    && keyColumns.size() < 2) {
                throw new IllegalArgumentException(
                    "Composite index requires multiple columns"
                );
            }

            if (type == IndexType.HASH
                    && keyColumns.size() != 1) {
                throw new IllegalArgumentException(
                    "Hash index requires one column"
                );
            }
        }
    }

    record QueryPattern(
        String name,
        List<String> columns,
        long frequency,
        long estimatedRows
    ) {
        QueryPattern {
            Objects.requireNonNull(name);
            Objects.requireNonNull(columns);

            columns = List.copyOf(columns);

            if (
                name.isBlank() ||
                columns.isEmpty() ||
                frequency < 0 ||
                estimatedRows < 0
            ) {
                throw new IllegalArgumentException(
                    "Invalid query pattern"
                );
            }
        }
    }

    record Workload(
        long reads,
        long inserts,
        long updates,
        long deletes
    ) {
        Workload {
            if (
                reads < 0 ||
                inserts < 0 ||
                updates < 0 ||
                deletes < 0
            ) {
                throw new IllegalArgumentException(
                    "Negative workload"
                );
            }
        }

        long totalWrites() {
            return inserts + updates + deletes;
        }
    }

    record IndexReport(
        String name,
        IndexType type,
        long reads,
        long writes,
        long storageBytes,
        double fragmentation,
        IndexStatus status
    ) {}

    record GovernanceResult(
        String indexName,
        Decision decision,
        double writeReadRatio,
        List<String> reasons
    ) {
        GovernanceResult {
            reasons = List.copyOf(reasons);
        }
    }

    record QueryResult(
        String queryName,
        String accessMethod,
        String indexName,
        long estimatedCost
    ) {}

    static class IndexMetrics {
        private final AtomicLong reads = new AtomicLong();
        private final AtomicLong inserts = new AtomicLong();
        private final AtomicLong updates = new AtomicLong();
        private final AtomicLong deletes = new AtomicLong();
        private final AtomicLong maintenanceRuns =
            new AtomicLong();

        private volatile long storageBytes;
        private volatile double fragmentation;

        long writes() {
            return inserts.get() +
                updates.get() +
                deletes.get();
        }

        void record(Operation operation) {
            switch (operation) {
                case INSERT -> inserts.incrementAndGet();
                case UPDATE -> updates.incrementAndGet();
                case DELETE -> deletes.incrementAndGet();
                default -> throw new IllegalArgumentException(
                    "Invalid write operation"
                );
            }

            fragmentation = Math.min(
                100.0,
                fragmentation + 0.015
            );
        }
    }

    static class ManagedIndex {
        private final IndexDefinition definition;
        private final IndexMetrics metrics =
            new IndexMetrics();

        private volatile IndexStatus status =
            IndexStatus.ACTIVE;

        ManagedIndex(IndexDefinition definition) {
            this.definition = definition;
        }

        boolean supports(List<String> columns) {
            if (status != IndexStatus.ACTIVE) {
                return false;
            }

            List<String> keys =
                definition.keyColumns();

            if (definition.type() == IndexType.HASH) {
                return columns.equals(keys);
            }

            if (columns.size() > keys.size()) {
                return false;
            }

            return keys.subList(0, columns.size())
                .equals(columns);
        }

        long calculateStorage(long rowCount) {
            long entryBytes =
                definition.keyColumns().size() * 24L +
                definition.includedColumns().size() * 16L +
                8L;

            metrics.storageBytes = (long) Math.ceil(
                rowCount * (double) entryBytes / 0.85
            );

            return metrics.storageBytes;
        }

        IndexReport report() {
            return new IndexReport(
                definition.name(),
                definition.type(),
                metrics.reads.get(),
                metrics.writes(),
                metrics.storageBytes,
                metrics.fragmentation,
                status
            );
        }
    }

    static class DatabaseTable {
        private final String name;
        private final Set<String> columns;
        private final long rowSizeBytes;

        private final Map<String, ManagedIndex> indexes =
            new ConcurrentHashMap<>();

        private final List<QueryPattern> queries =
            Collections.synchronizedList(
                new ArrayList<>()
            );

        private long rowCount;

        DatabaseTable(
            String name,
            Set<String> columns,
            long rowCount,
            long rowSizeBytes
        ) {
            if (
                name == null ||
                name.isBlank() ||
                columns == null ||
                columns.isEmpty() ||
                rowCount < 0 ||
                rowSizeBytes <= 0
            ) {
                throw new IllegalArgumentException(
                    "Invalid table configuration"
                );
            }

            this.name = name;
            this.columns = Set.copyOf(columns);
            this.rowCount = rowCount;
            this.rowSizeBytes = rowSizeBytes;
        }

        synchronized void addIndex(
            IndexDefinition definition
        ) {
            if (indexes.containsKey(definition.name())) {
                throw new IllegalArgumentException(
                    "Duplicate index name"
                );
            }

            Set<String> allColumns = new HashSet<>(
                definition.keyColumns()
            );

            allColumns.addAll(
                definition.includedColumns()
            );

            if (!columns.containsAll(allColumns)) {
                throw new IllegalArgumentException(
                    "Index references unknown columns"
                );
            }

            for (ManagedIndex existing : indexes.values()) {
                if (
                    existing.definition.keyColumns()
                        .equals(definition.keyColumns()) &&
                    existing.definition.includedColumns()
                        .equals(definition.includedColumns()) &&
                    existing.definition.type() == definition.type() &&
                    existing.status != IndexStatus.DISABLED
                ) {
                    throw new IllegalArgumentException(
                        "Equivalent index already exists"
                    );
                }
            }

            ManagedIndex managed =
                new ManagedIndex(definition);

            managed.calculateStorage(rowCount);

            indexes.put(definition.name(), managed);
        }

        synchronized void registerQuery(
            QueryPattern query
        ) {
            if (!columns.containsAll(query.columns())) {
                throw new IllegalArgumentException(
                    "Query references unknown columns"
                );
            }

            queries.add(query);
        }

        synchronized void insert(long count) {
            if (count <= 0) {
                throw new IllegalArgumentException(
                    "Insert count must be positive"
                );
            }

            rowCount += count;

            for (ManagedIndex index : indexes.values()) {
                for (long i = 0; i < count; i++) {
                    index.metrics.record(Operation.INSERT);
                }

                index.calculateStorage(rowCount);
            }
        }

        synchronized void update(
            long count,
            Set<String> modifiedColumns
        ) {
            if (
                count <= 0 ||
                count > rowCount ||
                !columns.containsAll(modifiedColumns)
            ) {
                throw new IllegalArgumentException(
                    "Invalid update operation"
                );
            }

            for (ManagedIndex index : indexes.values()) {
                Set<String> indexedColumns =
                    new HashSet<>(
                        index.definition.keyColumns()
                    );

                indexedColumns.addAll(
                    index.definition.includedColumns()
                );

                boolean affected =
                    modifiedColumns.stream()
                        .anyMatch(indexedColumns::contains);

                if (affected) {
                    for (long i = 0; i < count; i++) {
                        index.metrics.record(Operation.UPDATE);
                    }
                }
            }
        }

        synchronized void delete(long count) {
            if (count <= 0 || count > rowCount) {
                throw new IllegalArgumentException(
                    "Invalid delete operation"
                );
            }

            rowCount -= count;

            for (ManagedIndex index : indexes.values()) {
                for (long i = 0; i < count; i++) {
                    index.metrics.record(Operation.DELETE);
                }

                index.calculateStorage(rowCount);
            }
        }

        synchronized QueryResult execute(
            QueryPattern query
        ) {
            ManagedIndex selected = indexes.values()
                .stream()
                .filter(index ->
                    index.supports(query.columns())
                )
                .min(
                    Comparator.comparingInt(
                        index -> index.definition
                            .keyColumns().size()
                    )
                )
                .orElse(null);

            if (selected == null) {
                return new QueryResult(
                    query.name(),
                    "TABLE_SCAN",
                    "NONE",
                    Math.max(1, rowCount)
                );
            }

            selected.metrics.reads.addAndGet(
                query.frequency()
            );

            long cost = (long) Math.ceil(
                Math.log(
                    Math.max(2, rowCount)
                ) / Math.log(2)
            ) + query.estimatedRows() + 2;

            return new QueryResult(
                query.name(),
                "INDEX_SCAN",
                selected.definition.name(),
                cost
            );
        }

        synchronized void executeRegisteredQueries() {
            List<QueryPattern> snapshot;

            synchronized (queries) {
                snapshot = List.copyOf(queries);
            }

            snapshot.stream()
                .map(this::execute)
                .forEach(System.out::println);
        }

        synchronized void rebuild(String indexName) {
            ManagedIndex index = indexes.get(indexName);

            if (index == null) {
                throw new IllegalArgumentException(
                    "Unknown index"
                );
            }

            if (index.status == IndexStatus.DISABLED) {
                throw new IllegalStateException(
                    "Disabled indexes cannot be rebuilt"
                );
            }

            index.status = IndexStatus.NEEDS_REBUILD;

            index.metrics.fragmentation = 0.0;
            index.metrics.maintenanceRuns.incrementAndGet();
            index.calculateStorage(rowCount);

            index.status = IndexStatus.ACTIVE;
        }

        synchronized long totalIndexStorage() {
            return indexes.values().stream()
                .filter(index ->
                    index.status != IndexStatus.DISABLED
                )
                .mapToLong(index ->
                    index.metrics.storageBytes
                )
                .sum();
        }

        synchronized long getRowCount() {
            return rowCount;
        }

        synchronized long tableStorage() {
            return rowCount * rowSizeBytes;
        }

        synchronized List<IndexReport> reports() {
            return indexes.values().stream()
                .map(ManagedIndex::report)
                .sorted(
                    Comparator.comparing(IndexReport::name)
                )
                .toList();
        }

        synchronized Collection<ManagedIndex> managedIndexes() {
            return List.copyOf(indexes.values());
        }
    }

    static class IndexGovernanceService {
        private final long minimumWrites;
        private final double maximumWriteReadRatio;
        private final long storageBudgetBytes;

        IndexGovernanceService(
            long minimumWrites,
            double maximumWriteReadRatio,
            long storageBudgetBytes
        ) {
            if (
                minimumWrites < 0 ||
                maximumWriteReadRatio < 0 ||
                storageBudgetBytes < 0
            ) {
                throw new IllegalArgumentException(
                    "Invalid governance policy"
                );
            }

            this.minimumWrites = minimumWrites;
            this.maximumWriteReadRatio =
                maximumWriteReadRatio;
            this.storageBudgetBytes = storageBudgetBytes;
        }

        List<GovernanceResult> evaluate(
            DatabaseTable table
        ) {
            List<GovernanceResult> results =
                new ArrayList<>();

            for (ManagedIndex index :
                    table.managedIndexes()) {

                IndexMetrics metrics = index.metrics;

                double ratio =
                    metrics.writes() /
                    (double) Math.max(
                        1L,
                        metrics.reads.get()
                    );

                List<String> reasons = new ArrayList<>();

                if (
                    metrics.writes() >= minimumWrites &&
                    metrics.reads.get() == 0
                ) {
                    reasons.add("NO_OBSERVED_READ_USAGE");
                }

                if (
                    metrics.writes() >= minimumWrites &&
                    ratio > maximumWriteReadRatio
                ) {
                    reasons.add("EXCESSIVE_WRITE_COST");
                }

                if (metrics.fragmentation > 30) {
                    reasons.add("REBUILD_REVIEW");
                }

                if (
                    metrics.storageBytes > storageBudgetBytes
                ) {
                    reasons.add("STORAGE_BUDGET_EXCEEDED");
                }

                Decision decision = reasons.isEmpty()
                    ? Decision.RETAIN
                    : (
                        metrics.fragmentation > 30
                            ? Decision.REBUILD
                            : Decision.REVIEW
                    );

                results.add(
                    new GovernanceResult(
                        index.definition.name(),
                        decision,
                        ratio,
                        reasons
                    )
                );
            }

            return results;
        }
    }

    static void printReports(DatabaseTable table) {
        System.out.println("\nTABLE: " + table.name);
        System.out.println("Rows: " + table.getRowCount());
        System.out.println(
            "Table storage: " + table.tableStorage()
        );
        System.out.println(
            "Index storage: " + table.totalIndexStorage()
        );

        for (IndexReport report : table.reports()) {
            System.out.println(report);
        }
    }

    public static void main(String[] args) {
        try {
            DatabaseTable orders = new DatabaseTable(
                "orders",
                Set.of(
                    "order_id",
                    "customer_id",
                    "status",
                    "created_at",
                    "region",
                    "amount",
                    "description"
                ),
                100000,
                320
            );

            orders.addIndex(
                new IndexDefinition(
                    "idx_customer",
                    List.of("customer_id"),
                    List.of(),
                    IndexType.BTREE,
                    false
                )
            );

            orders.addIndex(
                new IndexDefinition(
                    "idx_status_date",
                    List.of("status", "created_at"),
                    List.of(),
                    IndexType.COMPOSITE,
                    false
                )
            );

            orders.addIndex(
                new IndexDefinition(
                    "idx_region_covering",
                    List.of("region"),
                    List.of("amount"),
                    IndexType.COVERING,
                    false
                )
            );

            orders.registerQuery(
                new QueryPattern(
                    "customer_history",
                    List.of("customer_id"),
                    25000,
                    15
                )
            );

            orders.registerQuery(
                new QueryPattern(
                    "pending_orders",
                    List.of("status", "created_at"),
                    12000,
                    50
                )
            );

            orders.registerQuery(
                new QueryPattern(
                    "regional_orders",
                    List.of("region"),
                    8000,
                    100
                )
            );

            orders.registerQuery(
                new QueryPattern(
                    "description_search",
                    List.of("description"),
                    2000,
                    500
                )
            );

            System.out.println("QUERY EXECUTION");

            orders.executeRegisteredQueries();

            System.out.println("\nWRITE OPERATIONS");

            orders.insert(500);

            orders.update(
                100,
                Set.of("status", "amount")
            );

            orders.delete(50);

            printReports(orders);

            System.out.println("\nGOVERNANCE EVALUATION");

            IndexGovernanceService governance =
                new IndexGovernanceService(
                    100,
                    10.0,
                    50_000_000
                );

            governance.evaluate(orders)
                .forEach(System.out::println);

            System.out.println("\nMAINTENANCE");

            orders.rebuild("idx_customer");

            System.out.println(
                "Customer index rebuilt successfully"
            );

            System.out.println("\nVALIDATION");

            try {
                orders.addIndex(
                    new IndexDefinition(
                        "invalid_index",
                        List.of("unknown"),
                        List.of(),
                        IndexType.BTREE,
                        false
                    )
                );
            } catch (IllegalArgumentException error) {
                System.out.println(
                    "Expected validation error: " +
                    error.getMessage()
                );
            }

            if (orders.getRowCount() != 100450) {
                throw new IllegalStateException(
                    "Incorrect row count"
                );
            }

            if (orders.totalIndexStorage() <= 0) {
                throw new IllegalStateException(
                    "Invalid index storage"
                );
            }

            System.out.println(
                "\nAll enterprise validation checks passed."
            );

        } catch (Exception error) {
            System.err.println(
                "Execution failed: " + error.getMessage()
            );

            System.exit(1);
        }
    }
}
