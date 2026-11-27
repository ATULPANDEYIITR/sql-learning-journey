import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/**
 * Sequential Scan, Index Scan and Bitmap Scan
 *
 * Enterprise-oriented Java 17 query execution model.
 *
 * Compile:
 * javac ScanEngine.java
 *
 * Run:
 * java ScanEngine
 */
public class ScanEngine {

    private static final int PAGE_SIZE = 100;

    private static final double SEQ_PAGE_COST = 1.0;
    private static final double RANDOM_PAGE_COST = 4.0;
    private static final double CPU_TUPLE_COST = 0.01;
    private static final double CPU_INDEX_COST = 0.005;

    enum ScanType {
        SEQUENTIAL,
        INDEX,
        BITMAP
    }

    enum Operator {
        EQUAL,
        IN
    }

    enum QueryState {
        CREATED,
        VALIDATED,
        PLANNED,
        EXECUTING,
        COMPLETED,
        FAILED
    }

    record Employee(
        int id,
        String department,
        String location,
        int salary,
        boolean active
    ) {}

    record Predicate(
        String column,
        Operator operator,
        Set<Object> values
    ) {
        Predicate {
            Objects.requireNonNull(column);
            Objects.requireNonNull(operator);
            Objects.requireNonNull(values);

            if (column.isBlank() || values.isEmpty()) {
                throw new IllegalArgumentException(
                    "Invalid predicate"
                );
            }

            values = Set.copyOf(values);

            if (operator == Operator.EQUAL && values.size() != 1) {
                throw new IllegalArgumentException(
                    "Equality requires exactly one value"
                );
            }
        }

        boolean matches(Employee employee) {
            Object actual = switch (column) {
                case "id" -> employee.id();
                case "department" -> employee.department();
                case "location" -> employee.location();
                case "salary" -> employee.salary();
                case "active" -> employee.active();
                default -> throw new IllegalArgumentException(
                    "Unknown column: " + column
                );
            };

            return values.contains(actual);
        }
    }

    record ScanPlan(
        ScanType scanType,
        double estimatedCost,
        double estimatedRows
    ) {}

    record Metrics(
        ScanType scanType,
        double estimatedCost,
        int rowsExamined,
        int rowsReturned,
        int indexEntriesExamined,
        int heapBlocksAccessed,
        int bitmapBytes,
        double executionTimeMs
    ) {}

    record QueryResult(
        List<Employee> rows,
        Metrics metrics
    ) {
        QueryResult {
            rows = List.copyOf(rows);
        }
    }

    static class QueryException extends RuntimeException {
        QueryException(String message) {
            super(message);
        }
    }

    /**
     * Query state transitions are explicit.
     * A completed or failed query cannot be executed again.
     */
    static class QueryContext {
        private final AtomicLong sequence;
        private final long queryId;
        private QueryState state = QueryState.CREATED;

        QueryContext(AtomicLong sequence) {
            this.sequence = sequence;
            this.queryId = sequence.incrementAndGet();
        }

        synchronized void transition(QueryState next) {
            boolean valid = switch (state) {
                case CREATED -> next == QueryState.VALIDATED
                    || next == QueryState.FAILED;

                case VALIDATED -> next == QueryState.PLANNED
                    || next == QueryState.FAILED;

                case PLANNED -> next == QueryState.EXECUTING
                    || next == QueryState.FAILED;

                case EXECUTING -> next == QueryState.COMPLETED
                    || next == QueryState.FAILED;

                case COMPLETED, FAILED -> false;
            };

            if (!valid) {
                throw new QueryException(
                    "Invalid query state transition: "
                    + state + " -> " + next
                );
            }

            state = next;
        }

        long queryId() {
            return queryId;
        }

        QueryState state() {
            return state;
        }
    }

    /**
     * In-memory relation with maintained secondary indexes.
     */
    static class EmployeeRepository {
        private final List<Employee> rows = new ArrayList<>();

        private final Map<String, Map<Object, Set<Integer>>>
            indexes = new HashMap<>();

        private static final Set<String> COLUMNS = Set.of(
            "id", "department", "location", "salary", "active"
        );

        synchronized int insert(Employee employee) {
            Objects.requireNonNull(employee);

            if (employee.id() <= 0 || employee.salary() < 0) {
                throw new IllegalArgumentException(
                    "Invalid employee data"
                );
            }

            if (rows.stream().anyMatch(
                e -> e.id() == employee.id()
            )) {
                throw new IllegalArgumentException(
                    "Duplicate employee identifier"
                );
            }

            int rowId = rows.size();

            rows.add(employee);

            indexes.forEach((column, entries) ->
                entries.computeIfAbsent(
                    value(employee, column),
                    key -> new HashSet<>()
                ).add(rowId)
            );

            return rowId;
        }

        synchronized void createIndex(String column) {
            if (!COLUMNS.contains(column)) {
                throw new IllegalArgumentException(
                    "Unknown index column"
                );
            }

            if (indexes.containsKey(column)) {
                throw new IllegalArgumentException(
                    "Index already exists"
                );
            }

            Map<Object, Set<Integer>> entries = new HashMap<>();

            for (int i = 0; i < rows.size(); i++) {
                entries.computeIfAbsent(
                    value(rows.get(i), column),
                    key -> new HashSet<>()
                ).add(i);
            }

            indexes.put(column, entries);
        }

        synchronized void delete(int rowId) {
            if (rowId < 0 || rowId >= rows.size()) {
                throw new IndexOutOfBoundsException(
                    "Invalid row identifier"
                );
            }

            Employee employee = rows.get(rowId);

            if (employee == null) {
                throw new QueryException("Row already deleted");
            }

            indexes.forEach((column, entries) -> {
                Object key = value(employee, column);
                Set<Integer> ids = entries.get(key);

                if (ids != null) {
                    ids.remove(rowId);

                    if (ids.isEmpty()) {
                        entries.remove(key);
                    }
                }
            });

            // Null slots preserve stable tuple identifiers.
            rows.set(rowId, null);
        }

        private Object value(Employee e, String column) {
            return switch (column) {
                case "id" -> e.id();
                case "department" -> e.department();
                case "location" -> e.location();
                case "salary" -> e.salary();
                case "active" -> e.active();
                default -> throw new IllegalArgumentException(
                    "Unknown column"
                );
            };
        }

        synchronized List<Employee> snapshot() {
            return new ArrayList<>(rows);
        }

        synchronized Map<Object, Set<Integer>> getIndex(
            String column
        ) {
            Map<Object, Set<Integer>> index = indexes.get(column);

            if (index == null) {
                throw new QueryException("Index unavailable");
            }

            Map<Object, Set<Integer>> copy = new HashMap<>();

            index.forEach((key, ids) ->
                copy.put(key, new HashSet<>(ids))
            );

            return copy;
        }

        synchronized boolean hasIndex(String column) {
            return indexes.containsKey(column);
        }

        synchronized int activeRows() {
            return (int) rows.stream()
                .filter(Objects::nonNull)
                .count();
        }

        synchronized int pageCount() {
            return Math.max(
                1,
                (activeRows() + PAGE_SIZE - 1) / PAGE_SIZE
            );
        }

        synchronized boolean validateIndexes() {
            for (String column : indexes.keySet()) {
                Map<Object, Set<Integer>> expected =
                    new HashMap<>();

                for (int i = 0; i < rows.size(); i++) {
                    Employee employee = rows.get(i);

                    if (employee != null) {
                        expected.computeIfAbsent(
                            value(employee, column),
                            key -> new HashSet<>()
                        ).add(i);
                    }
                }

                if (!expected.equals(indexes.get(column))) {
                    return false;
                }
            }

            return true;
        }
    }

    /**
     * Cost model separates planning from physical execution.
     */
    static class CostBasedPlanner {
        private final EmployeeRepository repository;

        CostBasedPlanner(EmployeeRepository repository) {
            this.repository = repository;
        }

        double selectivity(Predicate predicate) {
            List<Employee> rows = repository.snapshot();

            long matches = rows.stream()
                .filter(Objects::nonNull)
                .filter(predicate::matches)
                .count();

            return (double) matches /
                Math.max(1, repository.activeRows());
        }

        double sequentialCost() {
            return repository.pageCount() * SEQ_PAGE_COST
                + repository.activeRows() * CPU_TUPLE_COST;
        }

        double indexCost(double selectivity) {
            double n = Math.max(2, repository.activeRows());

            return Math.log(n) / Math.log(2)
                + selectivity * n *
                (RANDOM_PAGE_COST + CPU_INDEX_COST);
        }

        ScanPlan plan(List<Predicate> predicates) {
            double sequential = sequentialCost();

            List<Double> selectivities = predicates.stream()
                .filter(p -> repository.hasIndex(p.column()))
                .map(this::selectivity)
                .toList();

            if (selectivities.isEmpty()) {
                return new ScanPlan(
                    ScanType.SEQUENTIAL,
                    sequential,
                    repository.activeRows()
                );
            }

            double best = Collections.min(selectivities);
            double index = indexCost(best);

            if (selectivities.size() >= 2) {
                double combined = selectivities.stream()
                    .reduce(1.0, (a, b) -> a * b);

                double estimatedRows =
                    repository.activeRows() * combined;

                double blocks = Math.min(
                    repository.pageCount(),
                    Math.ceil(estimatedRows / PAGE_SIZE)
                );

                double bitmap =
                    selectivities.size() *
                    Math.log(
                        Math.max(2, repository.activeRows())
                    ) / Math.log(2)
                    + estimatedRows * CPU_INDEX_COST
                    + blocks * RANDOM_PAGE_COST
                    + estimatedRows * CPU_TUPLE_COST;

                if (bitmap < sequential && bitmap < index) {
                    return new ScanPlan(
                        ScanType.BITMAP,
                        bitmap,
                        estimatedRows
                    );
                }
            }

            if (index < sequential) {
                return new ScanPlan(
                    ScanType.INDEX,
                    index,
                    repository.activeRows() * best
                );
            }

            return new ScanPlan(
                ScanType.SEQUENTIAL,
                sequential,
                repository.activeRows()
            );
        }
    }

    /**
     * Enterprise service coordinating validation,
     * planning, execution and instrumentation.
     */
    static class QueryService {
        private final EmployeeRepository repository;
        private final CostBasedPlanner planner;
        private final AtomicLong sequence = new AtomicLong();

        QueryService(EmployeeRepository repository) {
            this.repository = repository;
            this.planner = new CostBasedPlanner(repository);
        }

        void validate(List<Predicate> predicates) {
            Objects.requireNonNull(predicates);

            for (Predicate predicate : predicates) {
                if (!EmployeeRepository.COLUMNS
                    .contains(predicate.column())) {
                    throw new QueryException(
                        "Unsupported column"
                    );
                }
            }
        }

        QueryResult execute(List<Predicate> predicates) {
            QueryContext context = new QueryContext(sequence);

            long started = System.nanoTime();

            try {
                validate(predicates);
                context.transition(QueryState.VALIDATED);

                ScanPlan plan = planner.plan(predicates);
                context.transition(QueryState.PLANNED);

                context.transition(QueryState.EXECUTING);

                QueryResult result = executePlan(
                    predicates,
                    plan
                );

                context.transition(QueryState.COMPLETED);

                System.out.println(
                    "Query " + context.queryId()
                    + " state: " + context.state()
                );

                return result;

            } catch (RuntimeException exception) {
                if (context.state() != QueryState.FAILED &&
                    context.state() != QueryState.COMPLETED) {
                    context.transition(QueryState.FAILED);
                }

                throw exception;
            }
        }

        private QueryResult executePlan(
            List<Predicate> predicates,
            ScanPlan plan
        ) {
            List<Employee> rows = repository.snapshot();

            Set<Integer> candidates = new HashSet<>();

            int indexEntries = 0;
            int bitmapBytes = 0;
            int rowsExamined = 0;
            int heapBlocks = 0;

            if (plan.scanType() == ScanType.SEQUENTIAL) {
                for (int i = 0; i < rows.size(); i++) {
                    if (rows.get(i) != null) {
                        candidates.add(i);
                    }
                }

                rowsExamined = candidates.size();
                heapBlocks = repository.pageCount();
            }

            if (plan.scanType() == ScanType.INDEX) {
                Predicate best = predicates.stream()
                    .filter(p -> repository.hasIndex(p.column()))
                    .min(Comparator.comparingDouble(
                        planner::selectivity
                    ))
                    .orElseThrow(() ->
                        new QueryException("No usable index")
                    );

                Set<Integer> ids = lookup(best);

                candidates.addAll(ids);
                indexEntries = ids.size();
                rowsExamined = ids.size();
            }

            if (plan.scanType() == ScanType.BITMAP) {
                List<Set<Integer>> bitmaps = predicates.stream()
                    .filter(p -> repository.hasIndex(p.column()))
                    .map(this::lookup)
                    .sorted(Comparator.comparingInt(Set::size))
                    .toList();

                if (bitmaps.size() < 2) {
                    throw new QueryException(
                        "Bitmap Scan requires two indexes"
                    );
                }

                candidates.addAll(bitmaps.get(0));

                for (int i = 1; i < bitmaps.size(); i++) {
                    candidates.retainAll(bitmaps.get(i));
                }

                indexEntries = bitmaps.stream()
                    .mapToInt(Set::size)
                    .sum();

                rowsExamined = candidates.size();
                bitmapBytes = (rows.size() + 7) / 8;
            }

            List<Employee> result = new ArrayList<>();

            for (int id : candidates) {
                Employee employee = rows.get(id);

                if (employee != null &&
                    predicates.stream().allMatch(
                        p -> p.matches(employee)
                    )) {
                    result.add(employee);
                }
            }

            if (plan.scanType() != ScanType.SEQUENTIAL) {
                heapBlocks = (int) candidates.stream()
                    .map(id -> id / PAGE_SIZE)
                    .distinct()
                    .count();
            }

            Metrics metrics = new Metrics(
                plan.scanType(),
                plan.estimatedCost(),
                rowsExamined,
                result.size(),
                indexEntries,
                heapBlocks,
                bitmapBytes,
                0.0
            );

            return new QueryResult(result, metrics);
        }

        private Set<Integer> lookup(Predicate predicate) {
            Map<Object, Set<Integer>> index =
                repository.getIndex(predicate.column());

            return predicate.values().stream()
                .flatMap(value -> index.getOrDefault(
                    value,
                    Set.of()
                ).stream())
                .collect(Collectors.toSet());
        }
    }

    private static List<Employee> generateEmployees(int count) {
        Random random = new Random(42);

        List<String> departments = List.of(
            "Engineering", "Finance",
            "Operations", "Security"
        );

        List<String> locations = List.of(
            "Lucknow", "Delhi",
            "Mumbai", "Bengaluru"
        );

        List<Employee> employees = new ArrayList<>();

        for (int i = 1; i <= count; i++) {
            employees.add(new Employee(
                i,
                departments.get(random.nextInt(4)),
                locations.get(random.nextInt(4)),
                30000 + random.nextInt(150001),
                random.nextDouble() > 0.15
            ));
        }

        return employees;
    }

    private static Predicate equal(
        String column,
        Object value
    ) {
        return new Predicate(
            column,
            Operator.EQUAL,
            Set.of(value)
        );
    }

    private static void display(
        String title,
        QueryResult result
    ) {
        System.out.println("\n" + title);

        Metrics m = result.metrics();

        System.out.println("Scan: " + m.scanType());
        System.out.printf(
            "Estimated cost: %.2f%n",
            m.estimatedCost()
        );

        System.out.println("Rows examined: " + m.rowsExamined());
        System.out.println("Rows returned: " + m.rowsReturned());

        System.out.println(
            "Index entries: " + m.indexEntriesExamined()
        );

        System.out.println(
            "Heap blocks: " + m.heapBlocksAccessed()
        );

        System.out.println(
            "Bitmap bytes: " + m.bitmapBytes()
        );
    }

    public static void main(String[] args) {
        EmployeeRepository repository =
            new EmployeeRepository();

        generateEmployees(10000).forEach(repository::insert);

        repository.createIndex("id");
        repository.createIndex("department");
        repository.createIndex("location");

        QueryService service = new QueryService(repository);

        // Non-indexed predicate.
        QueryResult sequential = service.execute(
            List.of(equal("salary", 50000))
        );

        display("1. Sequential Scan", sequential);

        // Highly selective predicate.
        QueryResult indexed = service.execute(
            List.of(equal("id", 500))
        );

        display("2. Index Scan", indexed);

        // Multiple indexed predicates.
        QueryResult bitmap = service.execute(
            List.of(
                equal("department", "Engineering"),
                equal("location", "Lucknow")
            )
        );

        display("3. Cost-Based Scan Selection", bitmap);

        // Verify index maintenance.
        int newId = repository.insert(
            new Employee(
                10001,
                "Security",
                "Lucknow",
                90000,
                true
            )
        );

        if (!repository.validateIndexes()) {
            throw new QueryException("Index integrity failure");
        }

        QueryResult inserted = service.execute(
            List.of(equal("id", 10001))
        );

        if (inserted.rows().size() != 1) {
            throw new QueryException("Insertion verification failed");
        }

        repository.delete(newId);

        if (!repository.validateIndexes()) {
            throw new QueryException(
                "Index integrity failure after deletion"
            );
        }

        QueryResult deleted = service.execute(
            List.of(equal("id", 10001))
        );

        if (!deleted.rows().isEmpty()) {
            throw new QueryException("Deletion verification failed");
        }

        System.out.println("\nIndex integrity: VALID");
        System.out.println("Query lifecycle: VALID");
        System.out.println("All enterprise validation tests passed.");
    }
}
