import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/*
 * JOIN vs Subquery
 *
 * Enterprise scenario:
 * An analytics service evaluates employee and project information stored in
 * relational tables. The domain model represents the relationships explicitly
 * and exposes services corresponding to common SQL design choices.
 *
 * The Java implementation deliberately emphasizes domain types, immutable
 * records, validation, service boundaries, and explicit query semantics
 * instead of reproducing SQL syntax line by line.
 */
public class JoinVsSubquery {

    enum QueryStrategy {
        JOIN,
        EXISTS,
        CORRELATED_SUBQUERY,
        PRE_AGGREGATED_RELATION
    }

    record Department(int id, String name) {
        Department {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new IllegalArgumentException(
                    "A department requires a positive id and name"
                );
            }
        }
    }

    record Employee(
        int id,
        String name,
        int departmentId,
        double salary
    ) {
        Employee {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new IllegalArgumentException(
                    "Employee identity is invalid"
                );
            }

            if (departmentId <= 0) {
                throw new IllegalArgumentException(
                    "Employee must reference a valid department"
                );
            }

            if (salary <= 0) {
                throw new IllegalArgumentException(
                    "Employee salary must be positive"
                );
            }
        }
    }

    record Project(
        int id,
        String name,
        int departmentId,
        double budget
    ) {
        Project {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new IllegalArgumentException(
                    "Project identity is invalid"
                );
            }

            if (departmentId <= 0 || budget < 0) {
                throw new IllegalArgumentException(
                    "Project department or budget is invalid"
                );
            }
        }
    }

    record Assignment(
        int employeeId,
        int projectId,
        int monthlyHours
    ) {
        Assignment {
            if (employeeId <= 0 || projectId <= 0) {
                throw new IllegalArgumentException(
                    "Assignment references are invalid"
                );
            }

            if (monthlyHours <= 0) {
                throw new IllegalArgumentException(
                    "Monthly project hours must be positive"
                );
            }
        }
    }

    record EmployeeDepartment(
        Employee employee,
        Department department
    ) {}

    record EmployeeProject(
        Employee employee,
        Project project,
        int monthlyHours
    ) {}

    record DepartmentAverage(
        Department department,
        double averageSalary
    ) {}

    static final class Repository {
        private final Map<Integer, Department> departments;
        private final Map<Integer, Employee> employees;
        private final Map<Integer, Project> projects;
        private final List<Assignment> assignments;

        Repository() {
            departments = new LinkedHashMap<>();
            employees = new LinkedHashMap<>();
            projects = new LinkedHashMap<>();
            assignments = new ArrayList<>();

            seed();
            validateReferences();
        }

        private void seed() {
            addDepartment(new Department(1, "Engineering"));
            addDepartment(new Department(2, "Finance"));
            addDepartment(new Department(3, "Operations"));
            addDepartment(new Department(4, "Research"));

            addEmployee(new Employee(1, "Asha", 1, 125000));
            addEmployee(new Employee(2, "Ravi", 1, 98000));
            addEmployee(new Employee(3, "Meera", 1, 112000));
            addEmployee(new Employee(4, "Kabir", 2, 87000));
            addEmployee(new Employee(5, "Neha", 2, 92000));
            addEmployee(new Employee(6, "Arjun", 3, 76000));
            addEmployee(new Employee(7, "Isha", 3, 81000));
            addEmployee(new Employee(8, "Sara", 4, 130000));
            addEmployee(new Employee(9, "Dev", 4, 105000));

            addProject(new Project(
                101, "Cloud Migration", 1, 500000
            ));
            addProject(new Project(
                102, "Fraud Analytics", 2, 350000
            ));
            addProject(new Project(
                103, "Warehouse Automation", 3, 275000
            ));
            addProject(new Project(
                104, "Quantum Research", 4, 600000
            ));

            assignments.add(new Assignment(1, 101, 80));
            assignments.add(new Assignment(2, 101, 120));
            assignments.add(new Assignment(3, 101, 90));
            assignments.add(new Assignment(3, 104, 40));
            assignments.add(new Assignment(4, 102, 70));
            assignments.add(new Assignment(5, 102, 110));
            assignments.add(new Assignment(6, 103, 100));
            assignments.add(new Assignment(7, 103, 120));
            assignments.add(new Assignment(8, 104, 130));
            assignments.add(new Assignment(9, 104, 100));
        }

        private void addDepartment(Department department) {
            departments.put(department.id(), department);
        }

        private void addEmployee(Employee employee) {
            employees.put(employee.id(), employee);
        }

        private void addProject(Project project) {
            projects.put(project.id(), project);
        }

        private void validateReferences() {
            for (Employee employee : employees.values()) {
                requireDepartment(employee.departmentId());
            }

            for (Assignment assignment : assignments) {
                if (!employees.containsKey(assignment.employeeId())) {
                    throw new IllegalStateException(
                        "Assignment references unknown employee"
                    );
                }

                if (!projects.containsKey(assignment.projectId())) {
                    throw new IllegalStateException(
                        "Assignment references unknown project"
                    );
                }
            }
        }

        Department requireDepartment(int id) {
            Department department = departments.get(id);

            if (department == null) {
                throw new IllegalArgumentException(
                    "Unknown department: " + id
                );
            }

            return department;
        }

        Employee requireEmployee(int id) {
            Employee employee = employees.get(id);

            if (employee == null) {
                throw new IllegalArgumentException(
                    "Unknown employee: " + id
                );
            }

            return employee;
        }

        Project requireProject(int id) {
            Project project = projects.get(id);

            if (project == null) {
                throw new IllegalArgumentException(
                    "Unknown project: " + id
                );
            }

            return project;
        }

        List<Department> departments() {
            return List.copyOf(departments.values());
        }

        List<Employee> employees() {
            return List.copyOf(employees.values());
        }

        List<Project> projects() {
            return List.copyOf(projects.values());
        }

        List<Assignment> assignments() {
            return List.copyOf(assignments);
        }
    }

    static final class QueryService {
        private final Repository repository;

        QueryService(Repository repository) {
            this.repository = Objects.requireNonNull(repository);
        }

        /*
         * JOIN-like operation:
         * the result deliberately contains attributes from both domain
         * entities because the relationship itself is part of the report.
         */
        List<EmployeeDepartment> employeeDepartmentJoin() {
            return repository.employees()
                .stream()
                .map(employee -> new EmployeeDepartment(
                    employee,
                    repository.requireDepartment(employee.departmentId())
                ))
                .toList();
        }

        /*
         * EXISTS-like operation:
         * anyMatch models a semi-join. The employee remains one result even
         * if several projects satisfy the condition.
         */
        List<Employee> employeesWithProjectBudgetAtLeast(
            double minimumBudget
        ) {
            if (minimumBudget < 0) {
                throw new IllegalArgumentException(
                    "Budget threshold cannot be negative"
                );
            }

            return repository.employees()
                .stream()
                .filter(employee ->
                    repository.assignments()
                        .stream()
                        .filter(a ->
                            a.employeeId() == employee.id()
                        )
                        .map(a ->
                            repository.requireProject(a.projectId())
                        )
                        .anyMatch(project ->
                            project.budget() >= minimumBudget
                        )
                )
                .toList();
        }

        /*
         * JOIN-style project report. Every matching assignment creates an
         * output row because project attributes and assignment hours are
         * needed by the consumer.
         */
        List<EmployeeProject> projectJoin(
            double minimumBudget
        ) {
            if (minimumBudget < 0) {
                throw new IllegalArgumentException(
                    "Budget threshold cannot be negative"
                );
            }

            return repository.assignments()
                .stream()
                .map(assignment -> new EmployeeProject(
                    repository.requireEmployee(assignment.employeeId()),
                    repository.requireProject(assignment.projectId()),
                    assignment.monthlyHours()
                ))
                .filter(row ->
                    row.project().budget() >= minimumBudget
                )
                .sorted(
                    Comparator.comparing(
                        row -> row.employee().name()
                    )
                )
                .toList();
        }

        /*
         * Correlated-subquery-style calculation:
         * for every employee, the service independently calculates the
         * average salary of that employee's department.
         */
        List<Employee> aboveDepartmentAverageCorrelated() {
            return repository.employees()
                .stream()
                .filter(employee -> {
                    List<Employee> departmentEmployees =
                        repository.employees()
                            .stream()
                            .filter(candidate ->
                                candidate.departmentId()
                                    == employee.departmentId()
                            )
                            .toList();

                    double average =
                        departmentEmployees.stream()
                            .mapToDouble(Employee::salary)
                            .average()
                            .orElseThrow(() ->
                                new IllegalStateException(
                                    "Department has no employees"
                                )
                            );

                    return employee.salary() > average;
                })
                .toList();
        }

        /*
         * Pre-aggregation corresponds to a derived table or CTE followed by
         * a JOIN. The aggregate is computed once per department and then
         * reused for each employee in that department.
         */
        List<Employee> aboveDepartmentAveragePreAggregated() {
            Map<Integer, Double> averages = new HashMap<>();

            for (Department department : repository.departments()) {
                double average = repository.employees()
                    .stream()
                    .filter(employee ->
                        employee.departmentId() == department.id()
                    )
                    .mapToDouble(Employee::salary)
                    .average()
                    .orElse(0.0);

                averages.put(department.id(), average);
            }

            return repository.employees()
                .stream()
                .filter(employee ->
                    employee.salary()
                        > averages.get(employee.departmentId())
                )
                .toList();
        }

        /*
         * This representation makes the aggregate itself a domain object.
         * It is useful when the aggregate is reused by several reports.
         */
        List<DepartmentAverage> departmentAverages() {
            return repository.departments()
                .stream()
                .map(department -> new DepartmentAverage(
                    department,
                    repository.employees()
                        .stream()
                        .filter(employee ->
                            employee.departmentId()
                                == department.id()
                        )
                        .mapToDouble(Employee::salary)
                        .average()
                        .orElse(0.0)
                ))
                .toList();
        }

        Map<QueryStrategy, String> strategyDescriptions() {
            Map<QueryStrategy, String> descriptions =
                new LinkedHashMap<>();

            descriptions.put(
                QueryStrategy.JOIN,
                "Combine related rows when columns from both sides belong in the result."
            );

            descriptions.put(
                QueryStrategy.EXISTS,
                "Test whether a qualifying related row exists without expanding the result."
            );

            descriptions.put(
                QueryStrategy.CORRELATED_SUBQUERY,
                "Calculate a value that depends on the current outer row."
            );

            descriptions.put(
                QueryStrategy.PRE_AGGREGATED_RELATION,
                "Compute a reusable relation first, then combine it with the outer relation."
            );

            return descriptions;
        }
    }

    static void printJoinRows(List<EmployeeDepartment> rows) {
        System.out.println("\n=== JOIN result ===");

        rows.forEach(row ->
            System.out.printf(
                "%-8s | %-12s | %.2f%n",
                row.employee().name(),
                row.department().name(),
                row.employee().salary()
            )
        );
    }

    static void printEmployees(
        String title,
        List<Employee> employees
    ) {
        System.out.println("\n=== " + title + " ===");

        employees.forEach(employee ->
            System.out.printf(
                "%-8s | department=%d | salary=%.2f%n",
                employee.name(),
                employee.departmentId(),
                employee.salary()
            )
        );
    }

    static void printProjectRows(List<EmployeeProject> rows) {
        System.out.println("\n=== Project JOIN result ===");

        rows.forEach(row ->
            System.out.printf(
                "%-8s | %-22s | budget=%.2f | hours=%d%n",
                row.employee().name(),
                row.project().name(),
                row.project().budget(),
                row.monthlyHours()
            )
        );
    }

    static void compareLogicalResults(
        List<Employee> first,
        List<Employee> second
    ) {
        Set<Integer> firstIds = first.stream()
            .map(Employee::id)
            .collect(Collectors.toSet());

        Set<Integer> secondIds = second.stream()
            .map(Employee::id)
            .collect(Collectors.toSet());

        if (!firstIds.equals(secondIds)) {
            throw new IllegalStateException(
                "Equivalent query strategies returned different logical results"
            );
        }

        System.out.println(
            "\nEquivalent-result validation passed."
        );
    }

    static void demonstratePredicateReuse(
        QueryService service
    ) {
        Predicate<Employee> highValueEmployee =
            employee -> employee.salary() >= 100000;

        List<Employee> result = service.employeeDepartmentJoin()
            .stream()
            .map(EmployeeDepartment::employee)
            .filter(highValueEmployee)
            .distinct()
            .toList();

        printEmployees(
            "Domain predicate applied after relationship expansion",
            result
        );
    }

    public static void main(String[] args) {
        Repository repository = new Repository();
        QueryService service = new QueryService(repository);

        printJoinRows(service.employeeDepartmentJoin());

        printProjectRows(
            service.projectJoin(500000)
        );

        printEmployees(
            "EXISTS-style project test",
            service.employeesWithProjectBudgetAtLeast(500000)
        );

        List<Employee> correlated =
            service.aboveDepartmentAverageCorrelated();

        List<Employee> preAggregated =
            service.aboveDepartmentAveragePreAggregated();

        printEmployees(
            "Correlated subquery-style calculation",
            correlated
        );

        printEmployees(
            "Pre-aggregated relation calculation",
            preAggregated
        );

        compareLogicalResults(correlated, preAggregated);

        System.out.println(
            "\n=== Reusable department aggregates ==="
        );

        service.departmentAverages().forEach(average ->
            System.out.printf(
                "%-12s | average salary=%.2f%n",
                average.department().name(),
                average.averageSalary()
            )
        );

        demonstratePredicateReuse(service);

        System.out.println("\n=== Strategy model ===");

        service.strategyDescriptions().forEach(
            (strategy, description) ->
                System.out.printf(
                    "%-28s | %s%n",
                    strategy,
                    description
                )
        );

        System.out.println(
            "\nEnterprise design rule: choose the relational form that "
            + "expresses the business relationship clearly, then validate "
            + "the generated SQL with execution plans and representative "
            + "production-scale data. Logical equivalence does not guarantee "
            + "identical physical execution."
        );
    }
}
