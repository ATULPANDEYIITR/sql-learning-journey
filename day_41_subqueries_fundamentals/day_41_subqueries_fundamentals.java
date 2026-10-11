import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/*
 * Subqueries Fundamentals
 *
 * Enterprise-oriented Java model for scalar, single-row, multi-row,
 * correlated, EXISTS, NOT EXISTS, nested, and table-style subqueries.
 *
 * Java 17 or later.
 */

public class SubqueriesFundamentals {

    enum DepartmentType {
        ENGINEERING,
        FINANCE,
        OPERATIONS,
        SECURITY,
        RESEARCH
    }

    record Department(int id, String name, DepartmentType type) {
        Department {
            if (id <= 0 || name == null || name.isBlank() || type == null) {
                throw new IllegalArgumentException("Invalid department.");
            }
        }
    }

    record Employee(
            int id,
            String name,
            int departmentId,
            double salary) {
        Employee {
            if (id <= 0 || name == null || name.isBlank()
                    || departmentId <= 0 || salary <= 0) {
                throw new IllegalArgumentException("Invalid employee.");
            }
        }
    }

    record Project(
            int id,
            String name,
            int departmentId,
            double budget) {
        Project {
            if (id <= 0 || name == null || name.isBlank()
                    || departmentId <= 0 || budget <= 0) {
                throw new IllegalArgumentException("Invalid project.");
            }
        }
    }

    record Assignment(
            int employeeId,
            int projectId,
            double hours) {
        Assignment {
            if (employeeId <= 0 || projectId <= 0 || hours < 0) {
                throw new IllegalArgumentException("Invalid assignment.");
            }
        }
    }

    record DepartmentMetric(
            Department department,
            long employeeCount,
            double averageSalary) {
    }

    static final class QueryCardinalityException
            extends RuntimeException {
        QueryCardinalityException(String message) {
            super(message);
        }
    }

    static final class Repository {
        private final List<Department> departments;
        private final List<Employee> employees;
        private final List<Project> projects;
        private final List<Assignment> assignments;

        Repository() {
            departments = List.of(
                    new Department(10, "Engineering",
                            DepartmentType.ENGINEERING),
                    new Department(20, "Finance",
                            DepartmentType.FINANCE),
                    new Department(30, "Operations",
                            DepartmentType.OPERATIONS),
                    new Department(40, "Security",
                            DepartmentType.SECURITY),
                    new Department(50, "Research",
                            DepartmentType.RESEARCH)
            );

            employees = List.of(
                    new Employee(101, "Aarav", 10, 92000),
                    new Employee(102, "Diya", 10, 108000),
                    new Employee(103, "Kabir", 10, 125000),
                    new Employee(104, "Meera", 20, 85000),
                    new Employee(105, "Rohan", 20, 97000),
                    new Employee(106, "Ishita", 30, 76000),
                    new Employee(107, "Vihaan", 30, 89000),
                    new Employee(108, "Anaya", 40, 118000),
                    new Employee(109, "Arjun", 40, 131000),
                    new Employee(110, "Sara", 50, 112000)
            );

            projects = List.of(
                    new Project(201, "Payment Platform", 10, 900000),
                    new Project(202, "Cloud Migration", 10, 650000),
                    new Project(203, "Risk Analytics", 20, 480000),
                    new Project(204, "Supply Optimization", 30, 550000),
                    new Project(205, "Threat Detection", 40, 800000),
                    new Project(206, "Quantum Research", 50, 1200000)
            );

            assignments = List.of(
                    new Assignment(101, 201, 120),
                    new Assignment(101, 202, 80),
                    new Assignment(102, 201, 160),
                    new Assignment(103, 201, 180),
                    new Assignment(103, 202, 90),
                    new Assignment(104, 203, 150),
                    new Assignment(105, 203, 175),
                    new Assignment(106, 204, 120),
                    new Assignment(107, 204, 190),
                    new Assignment(108, 205, 170),
                    new Assignment(109, 205, 210),
                    new Assignment(110, 206, 200)
            );
        }

        List<Department> departments() {
            return departments;
        }

        List<Employee> employees() {
            return employees;
        }

        List<Project> projects() {
            return projects;
        }

        List<Assignment> assignments() {
            return assignments;
        }
    }

    static final class QueryService {
        private final Repository repository;

        QueryService(Repository repository) {
            this.repository = Objects.requireNonNull(repository);
        }

        /*
         * A scalar subquery has a one-value contract. Optional is used when
         * absence is legitimate, while the cardinality check rejects the
         * more dangerous case of multiple rows.
         */
        private <T> T scalar(
                List<T> values,
                String description) {
            if (values.size() != 1) {
                throw new QueryCardinalityException(
                        description + " expected exactly one row but received "
                                + values.size());
            }
            return values.get(0);
        }

        private Optional<Integer> singleDepartmentId(String name) {
            List<Integer> matches = repository.departments().stream()
                    .filter(d -> d.name().equals(name))
                    .map(Department::id)
                    .toList();

            if (matches.size() > 1) {
                throw new QueryCardinalityException(
                        "Department lookup returned multiple rows.");
            }

            return matches.stream().findFirst();
        }

        private double scalarCompanyAverageSalary() {
            return repository.employees().stream()
                    .mapToDouble(Employee::salary)
                    .average()
                    .orElseThrow(
                            () -> new IllegalStateException(
                                    "Cannot average an empty employee set."));
        }

        List<Employee> scalarSubquery() {
            double companyAverage = scalarCompanyAverageSalary();

            return repository.employees().stream()
                    .filter(e -> e.salary() > companyAverage)
                    .sorted(Comparator.comparingDouble(Employee::salary)
                            .reversed())
                    .toList();
        }

        List<Employee> multiRowSubquery() {
            Set<String> names = Set.of(
                    "Engineering",
                    "Security",
                    "Research");

            Set<Integer> departmentIds = repository.departments().stream()
                    .filter(d -> names.contains(d.name()))
                    .map(Department::id)
                    .collect(Collectors.toSet());

            return repository.employees().stream()
                    .filter(e -> departmentIds.contains(e.departmentId()))
                    .toList();
        }

        boolean exists(
                Predicate<Assignment> predicate) {
            return repository.assignments().stream().anyMatch(predicate);
        }

        List<Employee> existsSubquery() {
            return repository.employees().stream()
                    .filter(employee ->
                            exists(assignment ->
                                    assignment.employeeId()
                                            == employee.id()
                                            && assignment.hours() >= 180))
                    .toList();
        }

        boolean departmentHasProject(int departmentId) {
            return repository.projects().stream()
                    .anyMatch(project ->
                            project.departmentId() == departmentId);
        }

        List<Department> notExistsSubquery() {
            return repository.departments().stream()
                    .filter(department ->
                            !departmentHasProject(department.id()))
                    .toList();
        }

        double departmentAverage(int departmentId) {
            return repository.employees().stream()
                    .filter(employee ->
                            employee.departmentId() == departmentId)
                    .mapToDouble(Employee::salary)
                    .average()
                    .orElseThrow(
                            () -> new IllegalStateException(
                                    "Department has no employees."));
        }

        List<Employee> correlatedSubquery() {
            return repository.employees().stream()
                    .filter(employee ->
                            employee.salary()
                                    > departmentAverage(
                                            employee.departmentId()))
                    .toList();
        }

        List<DepartmentMetric> tableSubquery() {
            /*
             * The first stream creates a derived result set. The second
             * operation consumes it as a relationally meaningful table.
             */
            List<DepartmentMetric> derivedTable =
                    repository.departments().stream()
                            .map(department -> {
                                List<Employee> members =
                                        repository.employees().stream()
                                                .filter(employee ->
                                                        employee.departmentId()
                                                                == department.id())
                                                .toList();

                                double average = members.stream()
                                        .mapToDouble(Employee::salary)
                                        .average()
                                        .orElse(0.0);

                                return new DepartmentMetric(
                                        department,
                                        members.size(),
                                        average);
                            })
                            .toList();

            return derivedTable.stream()
                    .filter(metric -> metric.employeeCount() >= 2)
                    .sorted(Comparator.comparingDouble(
                                    DepartmentMetric::averageSalary)
                            .reversed())
                    .toList();
        }

        List<Employee> nestedSubquery() {
            int engineeringId = scalar(
                    singleDepartmentId("Engineering").stream().toList(),
                    "Engineering lookup");

            double engineeringAverage =
                    departmentAverage(engineeringId);

            return repository.employees().stream()
                    .filter(employee ->
                            employee.salary() > engineeringAverage)
                    .toList();
        }

        List<Employee> greaterThanEveryFinanceSalary() {
            int financeId = scalar(
                    singleDepartmentId("Finance").stream().toList(),
                    "Finance lookup");

            List<Double> financeSalaries =
                    repository.employees().stream()
                            .filter(e -> e.departmentId() == financeId)
                            .map(Employee::salary)
                            .toList();

            return repository.employees().stream()
                    .filter(employee ->
                            financeSalaries.stream()
                                    .allMatch(financeSalary ->
                                            employee.salary()
                                                    > financeSalary))
                    .toList();
        }

        List<Employee> equalToAnyEngineeringSalary() {
            int engineeringId = scalar(
                    singleDepartmentId("Engineering").stream().toList(),
                    "Engineering lookup");

            Set<Double> engineeringSalaries =
                    repository.employees().stream()
                            .filter(e ->
                                    e.departmentId() == engineeringId)
                            .map(Employee::salary)
                            .collect(Collectors.toSet());

            return repository.employees().stream()
                    .filter(e -> engineeringSalaries.contains(e.salary()))
                    .toList();
        }

        List<String> combinedBusinessRule() {
            /*
             * The outer department is retained only if:
             *   - an employee exists above that department's average, and
             *   - at least one project exists.
             *
             * The first condition is correlated; the second is EXISTS.
             */
            return repository.departments().stream()
                    .filter(department ->
                            repository.employees().stream()
                                    .filter(employee ->
                                            employee.departmentId()
                                                    == department.id())
                                    .anyMatch(employee ->
                                            employee.salary()
                                                    > departmentAverage(
                                                            department.id())))
                    .filter(department ->
                            repository.projects().stream()
                                    .anyMatch(project ->
                                            project.departmentId()
                                                    == department.id()))
                    .map(Department::name)
                    .toList();
        }
    }

    private static void printEmployees(
            String title,
            List<Employee> employees) {
        System.out.println("\n--- " + title + " ---");

        if (employees.isEmpty()) {
            System.out.println("(no rows)");
            return;
        }

        employees.forEach(employee ->
                System.out.printf(
                        "%s | department=%d | salary=%,.2f%n",
                        employee.name(),
                        employee.departmentId(),
                        employee.salary()));
    }

    private static void printDepartments(
            String title,
            List<Department> departments) {
        System.out.println("\n--- " + title + " ---");

        if (departments.isEmpty()) {
            System.out.println("(no rows)");
            return;
        }

        departments.forEach(department ->
                System.out.printf(
                        "%d | %s | %s%n",
                        department.id(),
                        department.name(),
                        department.type()));
    }

    private static void printMetrics(
            String title,
            List<DepartmentMetric> metrics) {
        System.out.println("\n--- " + title + " ---");

        metrics.forEach(metric ->
                System.out.printf(
                        "%s | employees=%d | average=%,.2f%n",
                        metric.department().name(),
                        metric.employeeCount(),
                        metric.averageSalary()));
    }

    public static void main(String[] args) {
        Repository repository = new Repository();
        QueryService queries = new QueryService(repository);

        System.out.println("SUBQUERIES FUNDAMENTALS");
        System.out.println(
                "Enterprise-oriented Java model for relational subquery semantics");

        printEmployees(
                "Scalar subquery: employees above company average",
                queries.scalarSubquery());

        printEmployees(
                "Multi-row subquery: employees in selected departments",
                queries.multiRowSubquery());

        printEmployees(
                "EXISTS subquery: employees with heavy assignments",
                queries.existsSubquery());

        printDepartments(
                "NOT EXISTS subquery: departments without projects",
                queries.notExistsSubquery());

        printEmployees(
                "Correlated subquery: employees above department average",
                queries.correlatedSubquery());

        printMetrics(
                "Table subquery: derived department metrics",
                queries.tableSubquery());

        printEmployees(
                "Nested subquery: employees above Engineering average",
                queries.nestedSubquery());

        printEmployees(
                "ALL semantics: greater than every Finance salary",
                queries.greaterThanEveryFinanceSalary());

        printEmployees(
                "ANY semantics: equal to any Engineering salary",
                queries.equalToAnyEngineeringSalary());

        System.out.println("\nCombined correlated + EXISTS rule:");
        queries.combinedBusinessRule().forEach(System.out::println);

        System.out.println("\nSingle-row lookup:");
        Optional<Integer> securityId =
                queries.singleDepartmentId("Security");
        System.out.println(
                "Security department ID = "
                        + securityId.orElseThrow());

        System.out.println("\nMissing-row behavior:");
        Optional<Integer> missing =
                queries.singleDepartmentId("Legal");
        System.out.println(
                "Legal department present = " + missing.isPresent());

        /*
         * EnumSet is included here to model explicit domain classification.
         * The set itself is not a substitute for SQL, but it shows how a
         * relational multi-value result can be represented safely in Java.
         */
        EnumSet<DepartmentType> controlledTypes =
                EnumSet.of(
                        DepartmentType.SECURITY,
                        DepartmentType.RESEARCH);

        System.out.println("\nControlled department types:");
        controlledTypes.forEach(System.out::println);
    }
}
