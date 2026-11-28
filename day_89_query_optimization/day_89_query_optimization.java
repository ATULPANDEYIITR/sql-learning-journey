import java.util.*;
import java.util.function.Predicate;

public class QueryOptimization {

    enum Strategy {
        NESTED_LOOP,
        HASH_JOIN,
        INDEXED_JOIN
    }

    record Department(
        int id,
        String name,
        String location
    ) {
        Department {
            if (id <= 0 || name == null || name.isBlank()
                    || location == null || location.isBlank()) {
                throw new IllegalArgumentException(
                    "Invalid department"
                );
            }
        }
    }

    record Employee(
        int id,
        String name,
        int departmentId,
        double salary,
        boolean active
    ) {
        Employee {
            if (id <= 0 || name == null || name.isBlank()
                    || !Double.isFinite(salary) || salary < 0
                    || departmentId <= 0) {
                throw new IllegalArgumentException(
                    "Invalid employee"
                );
            }
        }
    }

    record Query(
        double minimumSalary,
        String location,
        int limit
    ) {
        Query {
            if (!Double.isFinite(minimumSalary)
                    || minimumSalary < 0) {
                throw new IllegalArgumentException(
                    "Invalid minimum salary"
                );
            }

            if (location == null || location.isBlank()) {
                throw new IllegalArgumentException(
                    "Location is required"
                );
            }

            if (limit < 0) {
                throw new IllegalArgumentException(
                    "Limit cannot be negative"
                );
            }
        }
    }

    record EmployeeResult(
        int id,
        String name,
        double salary,
        String department
    ) {}

    record ExecutionMetrics(
        long rowsScanned,
        long predicatesEvaluated,
        long joinOperations,
        int rowsReturned,
        double elapsedMs
    ) {}

    record ExecutionResult(
        List<EmployeeResult> rows,
        ExecutionMetrics metrics,
        Strategy strategy
    ) {
        ExecutionResult {
            rows = List.copyOf(rows);
        }
    }

    static final class Repository {
        private final Map<Integer, Employee> employees;
        private final Map<Integer, Department> departments;
        private final Map<Integer, List<Employee>> employeeIndex;
        private final Map<String, List<Department>> locationIndex;

        Repository(
            Collection<Employee> employeeData,
            Collection<Department> departmentData
        ) {
            Map<Integer, Department> departmentMap = new HashMap<>();

            for (Department department : departmentData) {
                if (departmentMap.putIfAbsent(
                        department.id(), department) != null) {
                    throw new IllegalArgumentException(
                        "Duplicate department ID"
                    );
                }
            }

            Map<Integer, Employee> employeeMap = new HashMap<>();
            Map<Integer, List<Employee>> departmentEmployees =
                new HashMap<>();

            for (Employee employee : employeeData) {
                if (!departmentMap.containsKey(employee.departmentId())) {
                    throw new IllegalArgumentException(
                        "Employee references unknown department"
                    );
                }

                if (employeeMap.putIfAbsent(
                        employee.id(), employee) != null) {
                    throw new IllegalArgumentException(
                        "Duplicate employee ID"
                    );
                }

                departmentEmployees.computeIfAbsent(
                    employee.departmentId(),
                    key -> new ArrayList<>()
                ).add(employee);
            }

            Map<String, List<Department>> locations = new HashMap<>();

            for (Department department : departmentMap.values()) {
                locations.computeIfAbsent(
                    department.location(),
                    key -> new ArrayList<>()
                ).add(department);
            }

            this.employees = Map.copyOf(employeeMap);
            this.departments = Map.copyOf(departmentMap);

            Map<Integer, List<Employee>> immutableEmployeeIndex =
                new HashMap<>();

            departmentEmployees.forEach(
                (key, value) ->
                    immutableEmployeeIndex.put(key, List.copyOf(value))
            );

            Map<String, List<Department>> immutableLocationIndex =
                new HashMap<>();

            locations.forEach(
                (key, value) ->
                    immutableLocationIndex.put(key, List.copyOf(value))
            );

            this.employeeIndex = Map.copyOf(immutableEmployeeIndex);
            this.locationIndex = Map.copyOf(immutableLocationIndex);
        }

        Collection<Employee> employees() {
            return employees.values();
        }

        Collection<Department> departments() {
            return departments.values();
        }

        List<Employee> employeesInDepartment(int id) {
            return employeeIndex.getOrDefault(id, List.of());
        }

        List<Department> departmentsInLocation(String location) {
            return locationIndex.getOrDefault(location, List.of());
        }

        Department department(int id) {
            return departments.get(id);
        }
    }

    static final class QueryOptimizer {
        private final Repository repository;

        QueryOptimizer(Repository repository) {
            this.repository = Objects.requireNonNull(repository);
        }

        ExecutionResult execute(Query query, Strategy strategy) {
            Objects.requireNonNull(query);
            Objects.requireNonNull(strategy);

            long start = System.nanoTime();

            MutableMetrics metrics = new MutableMetrics();

            List<EmployeeResult> rows = switch (strategy) {
                case NESTED_LOOP -> nestedLoop(query, metrics);
                case HASH_JOIN -> hashJoin(query, metrics);
                case INDEXED_JOIN -> indexedJoin(query, metrics);
            };

            rows.sort(
                Comparator.comparingDouble(EmployeeResult::salary)
                    .reversed()
                    .thenComparingInt(EmployeeResult::id)
            );

            if (query.limit() > 0 && rows.size() > query.limit()) {
                rows = new ArrayList<>(
                    rows.subList(0, query.limit())
                );
            }

            double elapsedMs =
                (System.nanoTime() - start) / 1_000_000.0;

            ExecutionMetrics immutableMetrics = new ExecutionMetrics(
                metrics.scanned,
                metrics.predicates,
                metrics.joins,
                rows.size(),
                elapsedMs
            );

            return new ExecutionResult(rows, immutableMetrics, strategy);
        }

        private List<EmployeeResult> nestedLoop(
            Query query,
            MutableMetrics metrics
        ) {
            List<EmployeeResult> results = new ArrayList<>();

            for (Employee employee : repository.employees()) {
                for (Department department : repository.departments()) {
                    metrics.joins++;

                    if (employee.departmentId() != department.id()) {
                        continue;
                    }

                    metrics.scanned++;
                    metrics.predicates++;

                    if (matches(employee, department, query)) {
                        results.add(toResult(employee, department));
                    }
                }
            }

            return results;
        }

        private List<EmployeeResult> hashJoin(
            Query query,
            MutableMetrics metrics
        ) {
            List<EmployeeResult> results = new ArrayList<>();

            // Apply the department predicate before building the join input.
            Map<Integer, Department> filteredDepartments = new HashMap<>();

            for (Department department : repository.departments()) {
                if (department.location().equals(query.location())) {
                    filteredDepartments.put(department.id(), department);
                }
            }

            // Apply independent employee predicates before joining.
            for (Employee employee : repository.employees()) {
                metrics.scanned++;
                metrics.predicates++;

                if (!employee.active()
                        || employee.salary() < query.minimumSalary()) {
                    continue;
                }

                metrics.joins++;

                Department department =
                    filteredDepartments.get(employee.departmentId());

                if (department != null) {
                    results.add(toResult(employee, department));
                }
            }

            return results;
        }

        private List<EmployeeResult> indexedJoin(
            Query query,
            MutableMetrics metrics
        ) {
            List<EmployeeResult> results = new ArrayList<>();

            // Use location and department indexes to retrieve only relevant
            // employee groups.
            for (Department department :
                    repository.departmentsInLocation(query.location())) {

                for (Employee employee :
                        repository.employeesInDepartment(department.id())) {

                    metrics.scanned++;
                    metrics.predicates++;

                    if (!employee.active()
                            || employee.salary() < query.minimumSalary()) {
                        continue;
                    }

                    metrics.joins++;
                    results.add(toResult(employee, department));
                }
            }

            return results;
        }

        private boolean matches(
            Employee employee,
            Department department,
            Query query
        ) {
            return employee.active()
                && employee.salary() >= query.minimumSalary()
                && department.location().equals(query.location());
        }

        private EmployeeResult toResult(
            Employee employee,
            Department department
        ) {
            return new EmployeeResult(
                employee.id(),
                employee.name(),
                employee.salary(),
                department.name()
            );
        }
    }

    static final class MutableMetrics {
        long scanned;
        long predicates;
        long joins;
    }

    static final class PlanEstimator {
        private final Repository repository;

        PlanEstimator(Repository repository) {
            this.repository = repository;
        }

        String recommend(Query query) {
            long totalDepartments = repository.departments().size();
            long matchingDepartments =
                repository.departmentsInLocation(query.location()).size();

            if (totalDepartments == 0 || matchingDepartments == 0) {
                return "EMPTY_RESULT";
            }

            return matchingDepartments <= totalDepartments / 2
                ? "INDEXED_JOIN"
                : "HASH_JOIN";
        }
    }

    public static void main(String[] args) {
        try {
            List<Department> departments = new ArrayList<>();
            List<Employee> employees = new ArrayList<>();

            String[] locations = {
                "Lucknow", "Delhi", "Mumbai", "Pune", "Bengaluru"
            };

            for (int i = 1; i <= 100; i++) {
                departments.add(new Department(
                    i,
                    "Department-" + i,
                    locations[(i - 1) % locations.length]
                ));
            }

            Random random = new Random(42);

            for (int i = 1; i <= 10000; i++) {
                employees.add(new Employee(
                    i,
                    "Employee-" + i,
                    random.nextInt(100) + 1,
                    20000 + random.nextInt(130001),
                    random.nextDouble() > 0.2
                ));
            }

            Repository repository =
                new Repository(employees, departments);

            QueryOptimizer optimizer =
                new QueryOptimizer(repository);

            Query query = new Query(
                75000,
                "Lucknow",
                100
            );

            System.out.println(
                "Recommended plan: "
                + new PlanEstimator(repository).recommend(query)
            );

            Map<Strategy, ExecutionResult> executions =
                new EnumMap<>(Strategy.class);

            for (Strategy strategy : Strategy.values()) {
                ExecutionResult result = optimizer.execute(query, strategy);
                executions.put(strategy, result);

                System.out.println("\n" + strategy);
                System.out.println("Rows scanned: "
                    + result.metrics().rowsScanned());
                System.out.println("Predicates evaluated: "
                    + result.metrics().predicatesEvaluated());
                System.out.println("Join operations: "
                    + result.metrics().joinOperations());
                System.out.println("Rows returned: "
                    + result.metrics().rowsReturned());
                System.out.printf(
                    Locale.ROOT,
                    "Elapsed time: %.3f ms%n",
                    result.metrics().elapsedMs()
                );

                result.rows().stream()
                    .limit(5)
                    .forEach(System.out::println);
            }

            List<Integer> reference =
                executions.get(Strategy.NESTED_LOOP).rows()
                    .stream()
                    .map(EmployeeResult::id)
                    .toList();

            for (ExecutionResult result : executions.values()) {
                List<Integer> actual = result.rows().stream()
                    .map(EmployeeResult::id)
                    .toList();

                if (!reference.equals(actual)) {
                    throw new IllegalStateException(
                        "Execution strategies returned different results"
                    );
                }
            }

            System.out.println(
                "\nAll strategies returned identical results."
            );

            try {
                new Query(-1, "Lucknow", 0);
            } catch (IllegalArgumentException exception) {
                System.out.println(
                    "Expected validation failure: "
                    + exception.getMessage()
                );
            }

        } catch (RuntimeException exception) {
            System.err.println(
                "Query execution failed: " + exception.getMessage()
            );
            System.exit(1);
        }
    }
}
