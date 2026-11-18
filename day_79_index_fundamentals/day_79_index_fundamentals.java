import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/**
 * INDEX FUNDAMENTALS
 *
 * Enterprise-oriented index management system.
 *
 * Covers:
 * - Table scans and index lookups
 * - B-tree fundamentals
 * - Unique and composite indexes
 * - Index maintenance
 * - Range queries
 * - Index selection policies
 * - Concurrent query execution
 * - Validation and consistency
 *
 * Java 17
 * No third-party dependencies.
 */
public class IndexFundamentals {

    enum IndexType {
        BTREE,
        HASH,
        COMPOSITE
    }

    enum QueryType {
        POINT_LOOKUP,
        RANGE_LOOKUP,
        FULL_SCAN
    }

    record Employee(
        int id,
        String name,
        String department,
        double salary
    ) {
        Employee {
            if (id <= 0) {
                throw new IllegalArgumentException("Invalid employee ID.");
            }

            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException("Invalid name.");
            }

            if (department == null || department.isBlank()) {
                throw new IllegalArgumentException("Invalid department.");
            }

            if (!Double.isFinite(salary) || salary < 0) {
                throw new IllegalArgumentException("Invalid salary.");
            }
        }
    }

    record QueryPlan(
        QueryType type,
        IndexType indexType,
        String accessMethod,
        String reason
    ) {}

    record QueryResult<T>(
        T value,
        QueryPlan plan,
        long durationNanos
    ) {}

    static class RepositoryException extends RuntimeException {
        RepositoryException(String message) {
            super(message);
        }
    }

    /**
     * A B-tree node stores multiple ordered keys.
     * Each internal node directs a search to one child.
     */
    static final class BTree {
        private static final class Node {
            boolean leaf;
            List<Integer> keys = new ArrayList<>();
            List<Node> children = new ArrayList<>();

            Node(boolean leaf) {
                this.leaf = leaf;
            }
        }

        private final int degree;
        private Node root;

        BTree(int degree) {
            if (degree < 2) {
                throw new IllegalArgumentException(
                    "Degree must be at least 2."
                );
            }

            this.degree = degree;
            this.root = new Node(true);
        }

        boolean contains(int key) {
            return search(root, key);
        }

        private boolean search(Node node, int key) {
            int index = Collections.binarySearch(node.keys, key);

            if (index >= 0) {
                return true;
            }

            index = -index - 1;

            if (node.leaf) {
                return false;
            }

            return search(node.children.get(index), key);
        }

        void insert(int key) {
            if (contains(key)) {
                throw new RepositoryException("Duplicate index key.");
            }

            if (root.keys.size() == 2 * degree - 1) {
                Node newRoot = new Node(false);
                newRoot.children.add(root);

                root = newRoot;
                splitChild(newRoot, 0);
            }

            insertNonFull(root, key);
        }

        private void splitChild(Node parent, int index) {
            Node child = parent.children.get(index);
            Node sibling = new Node(child.leaf);

            int median = child.keys.get(degree - 1);

            sibling.keys.addAll(
                child.keys.subList(degree, child.keys.size())
            );

            child.keys = new ArrayList<>(
                child.keys.subList(0, degree - 1)
            );

            if (!child.leaf) {
                sibling.children.addAll(
                    child.children.subList(
                        degree,
                        child.children.size()
                    )
                );

                child.children = new ArrayList<>(
                    child.children.subList(0, degree)
                );
            }

            parent.keys.add(index, median);
            parent.children.add(index + 1, sibling);
        }

        private void insertNonFull(Node node, int key) {
            int index = node.keys.size() - 1;

            if (node.leaf) {
                node.keys.add(key);

                while (index >= 0 && node.keys.get(index) > key) {
                    node.keys.set(
                        index + 1,
                        node.keys.get(index)
                    );

                    index--;
                }

                node.keys.set(index + 1, key);
                return;
            }

            while (index >= 0 && key < node.keys.get(index)) {
                index--;
            }

            index++;

            if (
                node.children.get(index).keys.size()
                == 2 * degree - 1
            ) {
                splitChild(node, index);

                if (key > node.keys.get(index)) {
                    index++;
                }
            }

            insertNonFull(node.children.get(index), key);
        }

        List<Integer> rangeSearch(int lower, int upper) {
            if (lower > upper) {
                throw new IllegalArgumentException("Invalid range.");
            }

            List<Integer> result = new ArrayList<>();
            traverseRange(root, lower, upper, result);

            return result;
        }

        private void traverseRange(
            Node node,
            int lower,
            int upper,
            List<Integer> result
        ) {
            for (int i = 0; i < node.keys.size(); i++) {
                int key = node.keys.get(i);

                if (!node.leaf && key >= lower) {
                    traverseRange(
                        node.children.get(i),
                        lower,
                        upper,
                        result
                    );
                }

                if (key >= lower && key <= upper) {
                    result.add(key);
                }
            }

            if (!node.leaf) {
                traverseRange(
                    node.children.get(node.keys.size()),
                    lower,
                    upper,
                    result
                );
            }
        }

        List<Integer> allKeys() {
            return rangeSearch(
                Integer.MIN_VALUE,
                Integer.MAX_VALUE
            );
        }

        boolean validate() {
            validateNode(
                root,
                Integer.MIN_VALUE,
                Integer.MAX_VALUE,
                true
            );

            return true;
        }

        private int validateNode(
            Node node,
            int lower,
            int upper,
            boolean isRoot
        ) {
            if (!node.keys.equals(
                node.keys.stream().sorted().toList()
            )) {
                throw new RepositoryException("Unsorted B-tree node.");
            }

            if (node.keys.size() > 2 * degree - 1) {
                throw new RepositoryException("Node capacity exceeded.");
            }

            if (
                !isRoot &&
                node.keys.size() < degree - 1
            ) {
                throw new RepositoryException("Minimum occupancy violated.");
            }

            for (int key : node.keys) {
                if (key <= lower || key >= upper) {
                    throw new RepositoryException("Ordering violation.");
                }
            }

            if (node.leaf) {
                if (!node.children.isEmpty()) {
                    throw new RepositoryException("Invalid leaf.");
                }

                return 1;
            }

            if (node.children.size() != node.keys.size() + 1) {
                throw new RepositoryException("Invalid child count.");
            }

            int expectedHeight = -1;

            for (int i = 0; i < node.children.size(); i++) {
                int childLower = i == 0
                    ? lower
                    : node.keys.get(i - 1);

                int childUpper = i == node.keys.size()
                    ? upper
                    : node.keys.get(i);

                int height = validateNode(
                    node.children.get(i),
                    childLower,
                    childUpper,
                    false
                );

                if (expectedHeight == -1) {
                    expectedHeight = height;
                } else if (expectedHeight != height) {
                    throw new RepositoryException(
                        "Unequal leaf depths."
                    );
                }
            }

            return expectedHeight + 1;
        }
    }

    interface IndexPolicy {
        QueryPlan choose(
            QueryType queryType,
            String indexedColumn
        );
    }

    static final class DefaultIndexPolicy implements IndexPolicy {

        @Override
        public QueryPlan choose(
            QueryType queryType,
            String indexedColumn
        ) {
            return switch (queryType) {
                case POINT_LOOKUP -> new QueryPlan(
                    queryType,
                    IndexType.BTREE,
                    "B-tree index scan",
                    "Equality predicate uses an ordered index."
                );

                case RANGE_LOOKUP -> new QueryPlan(
                    queryType,
                    IndexType.BTREE,
                    "B-tree range scan",
                    "Ordered keys support range retrieval."
                );

                case FULL_SCAN -> new QueryPlan(
                    queryType,
                    null,
                    "Sequential scan",
                    "All records are required."
                );
            };
        }
    }

    static final class EmployeeRepository {

        private final NavigableMap<Integer, Employee> records =
            new TreeMap<>();

        private final BTree primaryIndex = new BTree(4);

        private final Map<String, Set<Integer>> departmentIndex =
            new HashMap<>();

        private final IndexPolicy policy =
            new DefaultIndexPolicy();

        private final AtomicLong queryCounter =
            new AtomicLong();

        synchronized void insert(Employee employee) {
            Objects.requireNonNull(employee);

            if (records.containsKey(employee.id())) {
                throw new RepositoryException("Duplicate employee.");
            }

            primaryIndex.insert(employee.id());

            records.put(employee.id(), employee);

            departmentIndex
                .computeIfAbsent(
                    employee.department(),
                    ignored -> new HashSet<>()
                )
                .add(employee.id());
        }

        synchronized Employee indexedLookup(int id) {
            if (!primaryIndex.contains(id)) {
                return null;
            }

            return records.get(id);
        }

        synchronized Employee sequentialLookup(int id) {
            for (Employee employee : records.values()) {
                if (employee.id() == id) {
                    return employee;
                }
            }

            return null;
        }

        synchronized List<Employee> rangeLookup(
            int lower,
            int upper
        ) {
            if (lower > upper) {
                throw new IllegalArgumentException("Invalid range.");
            }

            return records
                .subMap(lower, true, upper, true)
                .values()
                .stream()
                .toList();
        }

        synchronized List<Employee> departmentLookup(
            String department
        ) {
            return departmentIndex
                .getOrDefault(department, Set.of())
                .stream()
                .map(records::get)
                .filter(Objects::nonNull)
                .sorted(Comparator.comparingInt(Employee::id))
                .toList();
        }

        synchronized void updateSalary(int id, double salary) {
            Employee existing = indexedLookup(id);

            if (existing == null) {
                throw new RepositoryException("Employee not found.");
            }

            Employee updated = new Employee(
                existing.id(),
                existing.name(),
                existing.department(),
                salary
            );

            // The primary index does not change because ID is unchanged.
            records.put(id, updated);
        }

        synchronized void delete(int id) {
            Employee existing = records.get(id);

            if (existing == null) {
                throw new RepositoryException("Employee not found.");
            }

            /*
             * The teaching B-tree does not implement deletion.
             * Reject the operation rather than corrupt index consistency.
             */
            throw new UnsupportedOperationException(
                "Deletion requires a deletion-capable B-tree."
            );
        }

        QueryResult<Employee> executePointQuery(int id) {
            long start = System.nanoTime();

            Employee employee = indexedLookup(id);

            long duration = System.nanoTime() - start;

            queryCounter.incrementAndGet();

            QueryPlan plan = policy.choose(
                QueryType.POINT_LOOKUP,
                "employee_id"
            );

            return new QueryResult<>(
                employee,
                plan,
                duration
            );
        }

        synchronized boolean verifyIntegrity() {
            primaryIndex.validate();

            List<Integer> indexed = primaryIndex.allKeys();

            if (!indexed.equals(new ArrayList<>(records.keySet()))) {
                throw new RepositoryException(
                    "Primary index and table differ."
                );
            }

            for (Employee employee : records.values()) {
                if (
                    !departmentIndex
                        .getOrDefault(employee.department(), Set.of())
                        .contains(employee.id())
                ) {
                    throw new RepositoryException(
                        "Department index inconsistency."
                    );
                }
            }

            return true;
        }

        long queryCount() {
            return queryCounter.get();
        }

        synchronized int size() {
            return records.size();
        }
    }

    static void benchmark(
        EmployeeRepository repository,
        int repetitions
    ) {
        Random random = new Random(42);

        List<Integer> targets = new ArrayList<>();

        for (int i = 0; i < repetitions; i++) {
            targets.add(random.nextInt(10000) + 1);
        }

        long start = System.nanoTime();

        for (int id : targets) {
            repository.sequentialLookup(id);
        }

        long sequentialDuration =
            System.nanoTime() - start;

        start = System.nanoTime();

        for (int id : targets) {
            repository.indexedLookup(id);
        }

        long indexedDuration =
            System.nanoTime() - start;

        System.out.printf(
            "Sequential scan: %.3f ms%n",
            sequentialDuration / 1_000_000.0
        );

        System.out.printf(
            "Indexed lookup: %.3f ms%n",
            indexedDuration / 1_000_000.0
        );

        if (indexedDuration > 0) {
            System.out.printf(
                "Observed ratio: %.2fx%n",
                (double) sequentialDuration / indexedDuration
            );
        }
    }

    public static void main(String[] args)
        throws InterruptedException, ExecutionException {

        EmployeeRepository repository =
            new EmployeeRepository();

        String[] departments = {
            "Engineering",
            "Security",
            "Research",
            "Operations",
            "Finance"
        };

        Random random = new Random(42);

        for (int id = 1; id <= 10000; id++) {
            repository.insert(
                new Employee(
                    id,
                    "Employee " + id,
                    departments[id % departments.length],
                    40000 + random.nextInt(110001)
                )
            );
        }

        System.out.println("INDEX FUNDAMENTALS");
        System.out.println("==============================");

        System.out.println(
            "Total records: " + repository.size()
        );

        System.out.println("\n1. INDEXED LOOKUP");

        QueryResult<Employee> result =
            repository.executePointQuery(7500);

        System.out.println(result.value());
        System.out.println(result.plan());
        System.out.println(
            "Execution time: " + result.durationNanos() + " ns"
        );

        System.out.println("\n2. SEQUENTIAL LOOKUP");
        System.out.println(repository.sequentialLookup(7500));

        System.out.println("\n3. RANGE LOOKUP");

        repository.rangeLookup(100, 110)
            .forEach(System.out::println);

        System.out.println("\n4. DEPARTMENT LOOKUP");

        System.out.println(
            "Security employees: " +
            repository.departmentLookup("Security").size()
        );

        System.out.println("\n5. UPDATE");

        repository.updateSalary(7500, 180000);

        System.out.println(repository.indexedLookup(7500));

        System.out.println("\n6. CONCURRENT READS");

        ExecutorService executor =
            Executors.newFixedThreadPool(4);

        List<Callable<Employee>> tasks = new ArrayList<>();

        for (int i = 1; i <= 20; i++) {
            int id = i * 100;

            tasks.add(() -> repository.indexedLookup(id));
        }

        for (Future<Employee> future : executor.invokeAll(tasks)) {
            if (future.get() == null) {
                throw new RepositoryException(
                    "Concurrent lookup failed."
                );
            }
        }

        executor.shutdown();

        if (!executor.awaitTermination(10, TimeUnit.SECONDS)) {
            executor.shutdownNow();
        }

        System.out.println("Concurrent reads completed.");

        System.out.println("\n7. INTEGRITY");
        System.out.println(repository.verifyIntegrity());

        System.out.println("\n8. BENCHMARK");
        benchmark(repository, 3000);

        System.out.println(
            "\nExecuted point queries: " +
            repository.queryCount()
        );

        System.out.println("\n9. VALIDATION");

        try {
            repository.insert(
                new Employee(
                    7500,
                    "Duplicate",
                    "Research",
                    50000
                )
            );
        } catch (RepositoryException error) {
            System.out.println("Rejected: " + error.getMessage());
        }

        try {
            repository.rangeLookup(500, 100);
        } catch (IllegalArgumentException error) {
            System.out.println("Rejected: " + error.getMessage());
        }

        System.out.println("\nExecution completed.");
    }
}
