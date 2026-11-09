import java.util.*;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/*
 * Database Views: CREATE VIEW, View Abstraction, and Reusable Queries.
 *
 * Java 17 enterprise implementation.
 *
 * Demonstrates:
 * - Immutable domain records.
 * - Repository and view service separation.
 * - Reusable logical views.
 * - Aggregation and relational joins.
 * - Role-based access policies.
 * - View dependency tracking.
 * - Materialized result caching.
 * - Cache invalidation.
 * - Validation and state management.
 */

public class DatabaseViewsEnterprise {

    enum Role {
        READER,
        ANALYST,
        ADMINISTRATOR
    }

    enum ViewType {
        SIMPLE,
        JOIN,
        AGGREGATE,
        MATERIALIZED
    }

    record Department(
        int id,
        String name,
        String location
    ) {
        Department {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new IllegalArgumentException(
                    "Invalid department."
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
            if (id <= 0 ||
                name == null ||
                name.isBlank() ||
                salary < 0 ||
                !Double.isFinite(salary)) {
                throw new IllegalArgumentException(
                    "Invalid employee."
                );
            }
        }

        Employee withName(String newName) {
            return new Employee(
                id,
                newName,
                departmentId,
                salary,
                active
            );
        }
    }

    record Project(
        int id,
        String name,
        double budget,
        int departmentId
    ) {
        Project {
            if (id <= 0 ||
                name == null ||
                name.isBlank() ||
                budget < 0 ||
                !Double.isFinite(budget)) {
                throw new IllegalArgumentException(
                    "Invalid project."
                );
            }
        }
    }

    record Assignment(
        int id,
        int employeeId,
        int projectId,
        double hours
    ) {
        Assignment {
            if (id <= 0 ||
                hours < 0 ||
                !Double.isFinite(hours)) {
                throw new IllegalArgumentException(
                    "Invalid assignment."
                );
            }
        }
    }

    record EmployeeDirectoryRow(
        int employeeId,
        String employeeName,
        int departmentId
    ) {}

    record DepartmentStatistics(
        int departmentId,
        String departmentName,
        long employeeCount,
        double averageSalary,
        double payroll
    ) {}

    record ProjectWorkload(
        int projectId,
        String projectName,
        String departmentName,
        long assignmentCount,
        double totalHours,
        double budget
    ) {}

    record ViewDefinition(
        String name,
        ViewType type,
        Set<String> dependencies,
        Set<Role> allowedRoles
    ) {
        ViewDefinition {
            Objects.requireNonNull(name);
            Objects.requireNonNull(type);
            dependencies = Set.copyOf(dependencies);
            allowedRoles = Set.copyOf(allowedRoles);

            if (dependencies.isEmpty() || allowedRoles.isEmpty()) {
                throw new IllegalArgumentException(
                    "View dependencies and roles are required."
                );
            }
        }
    }

    static class ViewException extends RuntimeException {
        ViewException(String message) {
            super(message);
        }
    }

    static class AccessDeniedException extends ViewException {
        AccessDeniedException(String message) {
            super(message);
        }
    }

    static class Repository {
        private final Map<Integer, Department> departments =
            new LinkedHashMap<>();

        private final Map<Integer, Employee> employees =
            new LinkedHashMap<>();

        private final Map<Integer, Project> projects =
            new LinkedHashMap<>();

        private final Map<Integer, Assignment> assignments =
            new LinkedHashMap<>();

        private long version = 0;

        Repository() {
            addDepartment(new Department(
                1, "Engineering", "Bangalore"
            ));

            addDepartment(new Department(
                2, "Finance", "Mumbai"
            ));

            addDepartment(new Department(
                3, "Research", "Hyderabad"
            ));

            addDepartment(new Department(
                4, "Operations", "Lucknow"
            ));

            addEmployee(new Employee(
                101, "Aarav", 1, 95000, true
            ));

            addEmployee(new Employee(
                102, "Meera", 1, 110000, true
            ));

            addEmployee(new Employee(
                103, "Kabir", 2, 85000, true
            ));

            addEmployee(new Employee(
                104, "Ananya", 3, 120000, true
            ));

            addEmployee(new Employee(
                105, "Rohan", 2, 75000, false
            ));

            addEmployee(new Employee(
                106, "Ishita", 4, 80000, true
            ));

            addProject(new Project(
                201, "Cloud Platform", 500000, 1
            ));

            addProject(new Project(
                202, "Financial Analytics", 250000, 2
            ));

            addProject(new Project(
                203, "Research Intelligence", 700000, 3
            ));

            addProject(new Project(
                204, "Process Automation", 180000, 4
            ));

            addAssignment(new Assignment(
                1, 101, 201, 120
            ));

            addAssignment(new Assignment(
                2, 102, 201, 160
            ));

            addAssignment(new Assignment(
                3, 103, 202, 90
            ));

            addAssignment(new Assignment(
                4, 104, 203, 180
            ));

            addAssignment(new Assignment(
                5, 106, 204, 110
            ));

            addAssignment(new Assignment(
                6, 101, 204, 40
            ));
        }

        private void addDepartment(Department department) {
            if (departments.containsKey(department.id())) {
                throw new ViewException(
                    "Duplicate department identifier."
                );
            }

            if (departments.values().stream().anyMatch(
                item -> item.name().equalsIgnoreCase(department.name())
            )) {
                throw new ViewException(
                    "Duplicate department name."
                );
            }

            departments.put(department.id(), department);
        }

        private void addEmployee(Employee employee) {
            if (!departments.containsKey(employee.departmentId())) {
                throw new ViewException(
                    "Employee department does not exist."
                );
            }

            if (employees.putIfAbsent(employee.id(), employee) != null) {
                throw new ViewException("Duplicate employee identifier.");
            }
        }

        private void addProject(Project project) {
            if (!departments.containsKey(project.departmentId())) {
                throw new ViewException(
                    "Project department does not exist."
                );
            }

            if (projects.values().stream().anyMatch(
                item -> item.name().equalsIgnoreCase(project.name())
            )) {
                throw new ViewException("Duplicate project name.");
            }

            projects.put(project.id(), project);
        }

        private void addAssignment(Assignment assignment) {
            if (!employees.containsKey(assignment.employeeId()) ||
                !projects.containsKey(assignment.projectId())) {
                throw new ViewException(
                    "Assignment references missing records."
                );
            }

            boolean duplicate = assignments.values().stream().anyMatch(
                item -> item.employeeId() == assignment.employeeId()
                    && item.projectId() == assignment.projectId()
            );

            if (duplicate) {
                throw new ViewException(
                    "Employee is already assigned to this project."
                );
            }

            assignments.put(assignment.id(), assignment);
        }

        Collection<Department> departments() {
            return List.copyOf(departments.values());
        }

        Collection<Employee> employees() {
            return List.copyOf(employees.values());
        }

        Collection<Project> projects() {
            return List.copyOf(projects.values());
        }

        Collection<Assignment> assignments() {
            return List.copyOf(assignments.values());
        }

        long version() {
            return version;
        }

        void updateEmployeeName(int employeeId, String newName) {
            if (newName == null || newName.isBlank()) {
                throw new ViewException(
                    "Employee name cannot be empty."
                );
            }

            Employee existing = employees.get(employeeId);

            if (existing == null) {
                throw new ViewException("Employee does not exist.");
            }

            employees.put(
                employeeId,
                existing.withName(newName.trim())
            );

            version++;
        }
    }


    static class ViewPolicy {

        void authorize(ViewDefinition definition, Role role) {
            if (!definition.allowedRoles().contains(role)) {
                throw new AccessDeniedException(
                    "Role " + role +
                    " cannot access view " + definition.name()
                );
            }
        }
    }


    static class ViewService {

        private final Repository repository;
        private final ViewPolicy policy;

        private final Map<String, ViewDefinition> definitions =
            new LinkedHashMap<>();

        private final Map<String, CacheEntry> cache =
            new HashMap<>();

        private record CacheEntry(
            long version,
            List<?> rows
        ) {}

        ViewService(Repository repository, ViewPolicy policy) {
            this.repository = repository;
            this.policy = policy;

            registerDefinitions();
        }

        private void registerDefinitions() {
            definitions.put(
                "employee_directory",
                new ViewDefinition(
                    "employee_directory",
                    ViewType.SIMPLE,
                    Set.of("employees"),
                    Set.of(
                        Role.READER,
                        Role.ANALYST,
                        Role.ADMINISTRATOR
                    )
                )
            );

            definitions.put(
                "department_statistics",
                new ViewDefinition(
                    "department_statistics",
                    ViewType.AGGREGATE,
                    Set.of("departments", "employees"),
                    Set.of(Role.ANALYST, Role.ADMINISTRATOR)
                )
            );

            definitions.put(
                "project_workload",
                new ViewDefinition(
                    "project_workload",
                    ViewType.JOIN,
                    Set.of("projects", "departments", "assignments"),
                    Set.of(
                        Role.READER,
                        Role.ANALYST,
                        Role.ADMINISTRATOR
                    )
                )
            );
        }

        private ViewDefinition authorize(
            String name,
            Role role
        ) {
            ViewDefinition definition = definitions.get(name);

            if (definition == null) {
                throw new ViewException(
                    "Unknown view: " + name
                );
            }

            policy.authorize(definition, role);

            return definition;
        }

        List<EmployeeDirectoryRow> employeeDirectory(Role role) {
            authorize("employee_directory", role);

            return repository.employees().stream()
                .filter(Employee::active)
                .map(employee -> new EmployeeDirectoryRow(
                    employee.id(),
                    employee.name(),
                    employee.departmentId()
                ))
                .toList();
        }

        List<DepartmentStatistics> departmentStatistics(Role role) {
            authorize("department_statistics", role);

            return repository.departments().stream()
                .map(department -> {
                    List<Employee> members =
                        repository.employees().stream()
                            .filter(Employee::active)
                            .filter(employee ->
                                employee.departmentId() == department.id()
                            )
                            .toList();

                    double payroll = members.stream()
                        .mapToDouble(Employee::salary)
                        .sum();

                    double average = members.isEmpty()
                        ? 0
                        : payroll / members.size();

                    return new DepartmentStatistics(
                        department.id(),
                        department.name(),
                        members.size(),
                        average,
                        payroll
                    );
                })
                .toList();
        }

        List<ProjectWorkload> projectWorkload(Role role) {
            authorize("project_workload", role);

            Map<Integer, Department> departmentIndex =
                repository.departments().stream()
                    .collect(Collectors.toMap(
                        Department::id,
                        department -> department
                    ));

            Map<Integer, List<Assignment>> assignmentsByProject =
                repository.assignments().stream()
                    .collect(Collectors.groupingBy(
                        Assignment::projectId
                    ));

            return repository.projects().stream()
                .map(project -> {
                    Department department =
                        departmentIndex.get(project.departmentId());

                    if (department == null) {
                        throw new ViewException(
                            "Project department missing."
                        );
                    }

                    List<Assignment> assigned =
                        assignmentsByProject.getOrDefault(
                            project.id(),
                            List.of()
                        );

                    double hours = assigned.stream()
                        .mapToDouble(Assignment::hours)
                        .sum();

                    return new ProjectWorkload(
                        project.id(),
                        project.name(),
                        department.name(),
                        assigned.size(),
                        hours,
                        project.budget()
                    );
                })
                .toList();
        }

        List<ProjectWorkload> filterProjects(
            Role role,
            Predicate<ProjectWorkload> predicate
        ) {
            Objects.requireNonNull(predicate);

            return projectWorkload(role).stream()
                .filter(predicate)
                .toList();
        }

        List<DepartmentStatistics> materializeDepartmentStatistics(
            Role role
        ) {
            authorize("department_statistics", role);

            CacheEntry existing = cache.get(
                "department_statistics"
            );

            if (existing != null &&
                existing.version() == repository.version()) {

                @SuppressWarnings("unchecked")
                List<DepartmentStatistics> rows =
                    (List<DepartmentStatistics>) existing.rows();

                return rows;
            }

            List<DepartmentStatistics> rows =
                departmentStatistics(role);

            cache.put(
                "department_statistics",
                new CacheEntry(
                    repository.version(),
                    List.copyOf(rows)
                )
            );

            return rows;
        }

        List<ViewDefinition> metadata(Role role) {
            return definitions.values().stream()
                .filter(definition ->
                    definition.allowedRoles().contains(role)
                )
                .toList();
        }

        void invalidateAll() {
            cache.clear();
        }
    }


    public static void main(String[] args) {
        try {
            Repository repository = new Repository();

            ViewPolicy policy = new ViewPolicy();

            ViewService views = new ViewService(
                repository,
                policy
            );

            System.out.println("\n1. Employee Directory");

            views.employeeDirectory(Role.READER)
                .forEach(System.out::println);

            System.out.println("\n2. Department Statistics");

            views.departmentStatistics(Role.ANALYST)
                .forEach(System.out::println);

            System.out.println("\n3. Project Workload");

            views.projectWorkload(Role.ANALYST)
                .forEach(System.out::println);

            System.out.println("\n4. Consumer-Specific Filtering");

            views.filterProjects(
                Role.ANALYST,
                project -> project.totalHours() > 100
            ).forEach(System.out::println);

            System.out.println("\n5. View Metadata");

            views.metadata(Role.ADMINISTRATOR)
                .forEach(System.out::println);

            System.out.println("\n6. Materialized View");

            views.materializeDepartmentStatistics(
                Role.ADMINISTRATOR
            ).forEach(System.out::println);

            System.out.println("\n7. Source Data Modification");

            repository.updateEmployeeName(
                101,
                "Aarav Sharma"
            );

            // The repository version changes, making the cache stale.
            views.materializeDepartmentStatistics(
                Role.ADMINISTRATOR
            ).forEach(System.out::println);

            System.out.println("\n8. Authorization Failure");

            try {
                views.departmentStatistics(Role.READER);
            } catch (AccessDeniedException exception) {
                System.out.println(exception.getMessage());
            }

            System.out.println("\n9. Unknown View");

            try {
                views.authorizeForTesting(
                    "missing_view",
                    Role.READER
                );
            } catch (ViewException exception) {
                System.out.println(exception.getMessage());
            }

            System.out.println("\n10. Assertions");

            List<DepartmentStatistics> statistics =
                views.departmentStatistics(Role.ANALYST);

            DepartmentStatistics engineering =
                statistics.stream()
                    .filter(item -> item.departmentId() == 1)
                    .findFirst()
                    .orElseThrow();

            if (engineering.employeeCount() != 2 ||
                Math.abs(engineering.payroll() - 205000) > 0.001) {
                throw new ViewException(
                    "Department statistics assertion failed."
                );
            }

            if (views.employeeDirectory(Role.READER).size() != 5) {
                throw new ViewException(
                    "Employee directory assertion failed."
                );
            }

            if (views.projectWorkload(Role.ANALYST).size() != 4) {
                throw new ViewException(
                    "Project workload assertion failed."
                );
            }

            System.out.println("All assertions passed.");

        } catch (Exception exception) {
            System.err.println(
                "Application failure: " + exception.getMessage()
            );

            System.exit(1);
        }
    }
}
