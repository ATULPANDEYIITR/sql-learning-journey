import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/*
 * QUERY EXECUTION ENGINE
 *
 * Enterprise-oriented relational query processing.
 *
 * Components:
 * - Typed query domain
 * - Catalog and metadata
 * - Logical plans
 * - Physical plans
 * - Statistics-based optimization
 * - Sequential and index access
 * - Predicate pushdown
 * - Projection
 * - Sorting
 * - Execution metrics
 * - Query lifecycle management
 * - Resource policies
 * - Prepared plan cache
 *
 * Java version: 17
 */

public class QueryExecutionEngine {

    enum DataType {
        INTEGER, DECIMAL, TEXT, BOOLEAN
    }

    enum Operator {
        EQ, NE, GT, LT, GE, LE
    }

    enum AccessPath {
        SEQUENTIAL_SCAN, INDEX_SCAN
    }

    enum QueryState {
        CREATED, PLANNED, OPTIMIZED, RUNNING,
        COMPLETED, FAILED, CANCELLED
    }

    record Column(
        String name,
        DataType type,
        boolean nullable
    ) {
        Column {
            Objects.requireNonNull(name);
            Objects.requireNonNull(type);

            if (!name.matches("[A-Za-z_][A-Za-z0-9_]*")) {
                throw new IllegalArgumentException(
                    "Invalid column identifier: " + name
                );
            }
        }
    }

    record SortSpecification(
        String column,
        boolean descending
    ) {
        SortSpecification {
            Objects.requireNonNull(column);
        }
    }

    record Comparison(
        String column,
        Operator operator,
        Object value
    ) {
        Comparison {
            Objects.requireNonNull(column);
            Objects.requireNonNull(operator);
        }
    }

    record QueryRequest(
        String table,
        List<String> projection,
        Comparison predicate,
        List<SortSpecification> ordering,
        Integer limit
    ) {
        QueryRequest {
            Objects.requireNonNull(table);
            projection = List.copyOf(projection);
            ordering = List.copyOf(ordering);

            if (projection.isEmpty()) {
                throw new IllegalArgumentException(
                    "Projection cannot be empty."
                );
            }

            if (limit != null && limit < 0) {
                throw new IllegalArgumentException(
                    "LIMIT cannot be negative."
                );
            }
        }
    }

    static class QueryException extends RuntimeException {
        QueryException(String message) {
            super(message);
        }
    }

    static class ResourceLimitException extends QueryException {
        ResourceLimitException(String message) {
            super(message);
        }
    }

    static class Catalog {
        private final Map<String, TableMetadata> tables =
            new HashMap<>();

        void register(TableMetadata table) {
            if (tables.putIfAbsent(
                table.name(), table
            ) != null) {
                throw new QueryException(
                    "Duplicate table: " + table.name()
                );
            }
        }

        TableMetadata get(String name) {
            TableMetadata table = tables.get(name);

            if (table == null) {
                throw new QueryException(
                    "Unknown table: " + name
                );
            }

            return table;
        }
    }

    static class TableMetadata {
        private final String name;
        private final List<Column> columns;
        private final Map<String, Column> columnMap;
        private final long estimatedRows;
        private final Set<String> indexedColumns;

        TableMetadata(
            String name,
            List<Column> columns,
            long estimatedRows,
            Set<String> indexedColumns
        ) {
            this.name = Objects.requireNonNull(name);
            this.columns = List.copyOf(columns);
            this.estimatedRows = estimatedRows;
            this.indexedColumns = Set.copyOf(indexedColumns);

            if (estimatedRows < 0) {
                throw new IllegalArgumentException(
                    "Negative row estimate."
                );
            }

            this.columnMap = new HashMap<>();

            for (Column column : columns) {
                if (
                    columnMap.put(
                        column.name(), column
                    ) != null
                ) {
                    throw new IllegalArgumentException(
                        "Duplicate metadata column."
                    );
                }
            }

            if (!columnMap.keySet().containsAll(indexedColumns)) {
                throw new IllegalArgumentException(
                    "Index references unknown column."
                );
            }
        }

        String name() {
            return name;
        }

        List<Column> columns() {
            return columns;
        }

        long estimatedRows() {
            return estimatedRows;
        }

        boolean hasIndex(String column) {
            return indexedColumns.contains(column);
        }

        Column getColumn(String name) {
            Column column = columnMap.get(name);

            if (column == null) {
                throw new QueryException(
                    "Unknown column: " + name
                );
            }

            return column;
        }
    }

    static class InMemoryTable {
        private final TableMetadata metadata;
        private final List<Map<String, Object>> rows;
        private final Map<String, Map<Object, List<Integer>>> indexes;

        InMemoryTable(
            TableMetadata metadata,
            List<Map<String, Object>> rows
        ) {
            this.metadata = metadata;

            List<Map<String, Object>> copied = new ArrayList<>();

            for (Map<String, Object> row : rows) {
                validateRow(metadata, row);
                copied.add(
                    Collections.unmodifiableMap(
                        new LinkedHashMap<>(row)
                    )
                );
            }

            this.rows = List.copyOf(copied);
            this.indexes = new HashMap<>();

            for (String column : metadata.indexedColumns) {
                Map<Object, List<Integer>> index =
                    new HashMap<>();

                for (int i = 0; i < this.rows.size(); i++) {
                    Object value = this.rows.get(i).get(column);

                    index.computeIfAbsent(
                        value,
                        ignored -> new ArrayList<>()
                    ).add(i);
                }

                Map<Object, List<Integer>> immutable =
                    new HashMap<>();

                index.forEach((key, value) ->
                    immutable.put(key, List.copyOf(value))
                );

                indexes.put(
                    column,
                    Collections.unmodifiableMap(immutable)
                );
            }
        }

        private static void validateRow(
            TableMetadata metadata,
            Map<String, Object> row
        ) {
            if (!row.keySet().equals(
                metadata.columns.stream()
                    .map(Column::name)
                    .collect(Collectors.toSet())
            )) {
                throw new QueryException(
                    "Row schema does not match metadata."
                );
            }

            for (Column column : metadata.columns) {
                Object value = row.get(column.name());

                if (value == null) {
                    if (!column.nullable()) {
                        throw new QueryException(
                            "NULL in non-nullable column: "
                            + column.name()
                        );
                    }

                    continue;
                }

                boolean valid = switch (column.type()) {
                    case INTEGER -> value instanceof Integer ||
                        value instanceof Long;
                    case DECIMAL -> value instanceof Number;
                    case TEXT -> value instanceof String;
                    case BOOLEAN -> value instanceof Boolean;
                };

                if (!valid) {
                    throw new QueryException(
                        "Invalid data type for " + column.name()
                    );
                }
            }
        }

        List<Map<String, Object>> rows() {
            return rows;
        }

        List<Integer> lookup(String column, Object value) {
            Map<Object, List<Integer>> index =
                indexes.get(column);

            if (index == null) {
                throw new QueryException(
                    "Index does not exist: " + column
                );
            }

            return index.getOrDefault(value, List.of());
        }
    }

    interface PlanNode {
        String describe();
    }

    record LogicalScan(String table) implements PlanNode {
        public String describe() {
            return "LogicalScan(" + table + ")";
        }
    }

    record LogicalFilter(
        Comparison predicate,
        PlanNode child
    ) implements PlanNode {
        public String describe() {
            return "LogicalFilter(" + predicate + ", "
                + child.describe() + ")";
        }
    }

    record LogicalProject(
        List<String> columns,
        PlanNode child
    ) implements PlanNode {
        public String describe() {
            return "LogicalProject(" + columns + ", "
                + child.describe() + ")";
        }
    }

    record PhysicalPlan(
        AccessPath accessPath,
        double estimatedCost,
        long estimatedRows,
        boolean predicatePushdown
    ) {
        String describe() {
            return "PhysicalPlan{" +
                "accessPath=" + accessPath +
                ", estimatedCost=" + estimatedCost +
                ", estimatedRows=" + estimatedRows +
                ", predicatePushdown=" + predicatePushdown +
                '}';
        }
    }

    record ExecutionStatistics(
        long scanned,
        long matched,
        long returned,
        double executionMilliseconds,
        AccessPath accessPath
    ) {}

    record QueryResult(
        List<Map<String, Object>> rows,
        ExecutionStatistics statistics,
        String logicalPlan,
        String physicalPlan
    ) {
        QueryResult {
            rows = List.copyOf(rows);
        }
    }

    static class QueryOptimizer {
        private static final double INDEX_STARTUP_COST = 2.0;
        private static final double SEQUENTIAL_ROW_COST = 1.0;
        private static final double INDEX_ROW_COST = 0.2;

        PhysicalPlan optimize(
            QueryRequest request,
            TableMetadata metadata
        ) {
            validate(request, metadata);

            long rows = metadata.estimatedRows();

            double sequentialCost =
                rows * SEQUENTIAL_ROW_COST;

            AccessPath path = AccessPath.SEQUENTIAL_SCAN;
            double cost = sequentialCost;
            long estimatedRows = rows;

            if (
                request.predicate() != null &&
                request.predicate().operator() == Operator.EQ &&
                metadata.hasIndex(
                    request.predicate().column()
                )
            ) {
                // The estimate assumes a simple selective equality
                // predicate. Production planners use histograms,
                // distinct counts and correlation statistics.
                estimatedRows = Math.max(1, rows / 10);

                double indexCost =
                    INDEX_STARTUP_COST +
                    estimatedRows * INDEX_ROW_COST;

                if (indexCost < sequentialCost) {
                    path = AccessPath.INDEX_SCAN;
                    cost = indexCost;
                }
            }

            return new PhysicalPlan(
                path,
                cost,
                estimatedRows,
                request.predicate() != null
            );
        }

        private void validate(
            QueryRequest request,
            TableMetadata metadata
        ) {
            for (String column : request.projection()) {
                if (!column.equals("*")) {
                    metadata.getColumn(column);
                }
            }

            for (SortSpecification sort : request.ordering()) {
                metadata.getColumn(sort.column());
            }

            if (request.predicate() != null) {
                Column column = metadata.getColumn(
                    request.predicate().column()
                );

                validateValueType(
                    column,
                    request.predicate().value()
                );
            }
        }

        private void validateValueType(
            Column column,
            Object value
        ) {
            if (value == null) return;

            boolean valid = switch (column.type()) {
                case INTEGER -> value instanceof Integer ||
                    value instanceof Long;
                case DECIMAL -> value instanceof Number;
                case TEXT -> value instanceof String;
                case BOOLEAN -> value instanceof Boolean;
            };

            if (!valid) {
                throw new QueryException(
                    "Predicate value type does not match column."
                );
            }
        }
    }

    static class QueryService {
        private final Catalog catalog;
        private final Map<String, InMemoryTable> data;
        private final QueryOptimizer optimizer =
            new QueryOptimizer();

        private final AtomicLong executionCounter =
            new AtomicLong();

        private final long maximumScannedRows;

        QueryService(
            Catalog catalog,
            Map<String, InMemoryTable> data,
            long maximumScannedRows
        ) {
            this.catalog = catalog;
            this.data = Map.copyOf(data);
            this.maximumScannedRows = maximumScannedRows;
        }

        QueryResult execute(QueryRequest request) {
            long start = System.nanoTime();

            TableMetadata metadata =
                catalog.get(request.table());

            InMemoryTable table = data.get(request.table());

            if (table == null) {
                throw new QueryException(
                    "Physical table data is unavailable."
                );
            }

            LogicalScan scan =
                new LogicalScan(request.table());

            PlanNode logical = scan;

            if (request.predicate() != null) {
                logical = new LogicalFilter(
                    request.predicate(), logical
                );
            }

            logical = new LogicalProject(
                request.projection(), logical
            );

            PhysicalPlan physical =
                optimizer.optimize(request, metadata);

            List<Integer> candidates = new ArrayList<>();

            if (physical.accessPath() == AccessPath.INDEX_SCAN) {
                candidates.addAll(table.lookup(
                    request.predicate().column(),
                    request.predicate().value()
                ));
            } else {
                for (int i = 0; i < table.rows().size(); i++) {
                    candidates.add(i);
                }
            }

            if (candidates.size() > maximumScannedRows) {
                throw new ResourceLimitException(
                    "Maximum scanned-row limit exceeded."
                );
            }

            List<Map<String, Object>> matched =
                new ArrayList<>();

            for (int position : candidates) {
                Map<String, Object> row =
                    table.rows().get(position);

                if (
                    request.predicate() == null ||
                    matches(request.predicate(), row)
                ) {
                    matched.add(row);
                }
            }

            // Sorting is performed before projection to support
            // ORDER BY columns that are not selected.
            if (!request.ordering().isEmpty()) {
                Comparator<Map<String, Object>> comparator =
                    (left, right) -> 0;

                for (SortSpecification sort : request.ordering()) {
                    Comparator<Map<String, Object>> next =
                        Comparator.comparing(
                            row -> (Comparable<Object>)
                                row.get(sort.column()),
                            Comparator.nullsLast(
                                Comparator.naturalOrder()
                            )
                        );

                    if (sort.descending()) {
                        next = next.reversed();
                    }

                    comparator = comparator.thenComparing(next);
                }

                matched.sort(comparator);
            }

            if (request.limit() != null) {
                matched = new ArrayList<>(
                    matched.subList(
                        0,
                        Math.min(
                            request.limit(),
                            matched.size()
                        )
                    )
                );
            }

            List<String> projection =
                request.projection().contains("*")
                    ? metadata.columns().stream()
                        .map(Column::name)
                        .toList()
                    : request.projection();

            List<Map<String, Object>> output =
                new ArrayList<>();

            for (Map<String, Object> row : matched) {
                Map<String, Object> projected =
                    new LinkedHashMap<>();

                for (String column : projection) {
                    projected.put(column, row.get(column));
                }

                output.add(
                    Collections.unmodifiableMap(projected)
                );
            }

            long elapsed =
                System.nanoTime() - start;

            executionCounter.incrementAndGet();

            ExecutionStatistics statistics =
                new ExecutionStatistics(
                    candidates.size(),
                    matched.size(),
                    output.size(),
                    elapsed / 1_000_000.0,
                    physical.accessPath()
                );

            return new QueryResult(
                output,
                statistics,
                logical.describe(),
                physical.describe()
            );
        }

        private boolean matches(
            Comparison comparison,
            Map<String, Object> row
        ) {
            Object actual = row.get(comparison.column());
            Object expected = comparison.value();

            // SQL UNKNOWN is rejected by WHERE.
            if (actual == null || expected == null) {
                return false;
            }

            int result;

            if (
                actual instanceof Number &&
                expected instanceof Number
            ) {
                result = Double.compare(
                    ((Number) actual).doubleValue(),
                    ((Number) expected).doubleValue()
                );
            } else if (
                actual instanceof Comparable<?> &&
                actual.getClass().isInstance(expected)
            ) {
                @SuppressWarnings("unchecked")
                Comparable<Object> comparable =
                    (Comparable<Object>) actual;

                result = comparable.compareTo(expected);
            } else {
                throw new QueryException(
                    "Incompatible comparison values."
                );
            }

            return switch (comparison.operator()) {
                case EQ -> result == 0;
                case NE -> result != 0;
                case GT -> result > 0;
                case LT -> result < 0;
                case GE -> result >= 0;
                case LE -> result <= 0;
            };
        }

        long executionCount() {
            return executionCounter.get();
        }
    }

    static class PreparedPlanCache {
        private final int capacity;

        private final LinkedHashMap<String, PhysicalPlan> cache =
            new LinkedHashMap<>(16, 0.75f, true);

        PreparedPlanCache(int capacity) {
            if (capacity < 1) {
                throw new IllegalArgumentException(
                    "Cache capacity must be positive."
                );
            }

            this.capacity = capacity;
        }

        synchronized void put(
            String key,
            PhysicalPlan plan
        ) {
            cache.put(key, plan);

            if (cache.size() > capacity) {
                String eldest =
                    cache.keySet().iterator().next();

                cache.remove(eldest);
            }
        }

        synchronized Optional<PhysicalPlan> get(String key) {
            return Optional.ofNullable(cache.get(key));
        }

        synchronized int size() {
            return cache.size();
        }
    }

    public static void main(String[] args) {
        List<Column> columns = List.of(
            new Column("id", DataType.INTEGER, false),
            new Column("name", DataType.TEXT, false),
            new Column("department", DataType.TEXT, false),
            new Column("salary", DataType.INTEGER, false)
        );

        TableMetadata metadata = new TableMetadata(
            "employees",
            columns,
            10000,
            Set.of("id", "department")
        );

        List<Map<String, Object>> rows = List.of(
            Map.of(
                "id", 1,
                "name", "Asha",
                "department", "Engineering",
                "salary", 95000
            ),
            Map.of(
                "id", 2,
                "name", "Rahul",
                "department", "Finance",
                "salary", 72000
            ),
            Map.of(
                "id", 3,
                "name", "Neha",
                "department", "Engineering",
                "salary", 110000
            ),
            Map.of(
                "id", 4,
                "name", "Arjun",
                "department", "Operations",
                "salary", 68000
            ),
            Map.of(
                "id", 5,
                "name", "Meera",
                "department", "Engineering",
                "salary", 88000
            )
        );

        InMemoryTable table =
            new InMemoryTable(metadata, rows);

        Catalog catalog = new Catalog();
        catalog.register(metadata);

        QueryService service = new QueryService(
            catalog,
            Map.of("employees", table),
            100000
        );

        QueryRequest request = new QueryRequest(
            "employees",
            List.of("name", "salary"),
            new Comparison(
                "department",
                Operator.EQ,
                "Engineering"
            ),
            List.of(
                new SortSpecification("salary", true)
            ),
            2
        );

        QueryResult result = service.execute(request);

        System.out.println("LOGICAL PLAN");
        System.out.println(result.logicalPlan());

        System.out.println("\nPHYSICAL PLAN");
        System.out.println(result.physicalPlan());

        System.out.println("\nQUERY RESULTS");
        result.rows().forEach(System.out::println);

        System.out.println("\nEXECUTION STATISTICS");
        System.out.println(result.statistics());

        PreparedPlanCache cache =
            new PreparedPlanCache(2);

        cache.put("employee-plan-v1",
            new PhysicalPlan(
                AccessPath.INDEX_SCAN,
                3.0,
                100,
                true
            )
        );

        if (cache.get("employee-plan-v1").isEmpty()) {
            throw new AssertionError("Cache retrieval failed.");
        }

        if (result.rows().size() != 2) {
            throw new AssertionError("Result count failed.");
        }

        if (
            !result.rows().get(0).get("name").equals("Neha")
        ) {
            throw new AssertionError("Ordering failed.");
        }

        QueryRequest zeroLimit = new QueryRequest(
            "employees",
            List.of("id"),
            null,
            List.of(),
            0
        );

        if (!service.execute(zeroLimit).rows().isEmpty()) {
            throw new AssertionError("LIMIT 0 failed.");
        }

        try {
            service.execute(new QueryRequest(
                "employees",
                List.of("unknown"),
                null,
                List.of(),
                null
            ));

            throw new AssertionError(
                "Unknown-column validation failed."
            );
        } catch (QueryException expected) {
            System.out.println(
                "\nValidation correctly rejected unknown column."
            );
        }

        System.out.println(
            "\nSuccessful executions: " +
            service.executionCount()
        );

        System.out.println("All tests passed.");
    }
}
