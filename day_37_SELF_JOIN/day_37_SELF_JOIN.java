import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/*
 * Enterprise employee hierarchy model.
 *
 * The central domain relationship is:
 *
 * Employee.managerId -> Employee.id
 *
 * In SQL this becomes a SELF JOIN when the same employee table is given
 * two logical roles: employee and manager.
 *
 * This Java implementation emphasizes explicit domain types, validation,
 * immutable reporting views, state-safe manager changes, and service methods.
 */

public class EmployeeHierarchyDemo {

    public record Employee(
            int id,
            String name,
            String title,
            Integer managerId,
            String department,
            double salary,
            boolean active
    ) {
        public Employee {
            if (id <= 0) {
                throw new IllegalArgumentException("Employee ID must be positive.");
            }

            Objects.requireNonNull(name, "Employee name is required.");
            Objects.requireNonNull(title, "Employee title is required.");
            Objects.requireNonNull(department, "Department is required.");

            if (name.isBlank() || title.isBlank() || department.isBlank()) {
                throw new IllegalArgumentException(
                        "Employee name, title, and department cannot be blank."
                );
            }

            if (salary < 0) {
                throw new IllegalArgumentException("Salary cannot be negative.");
            }
        }

        public Employee withManager(Integer newManagerId) {
            return new Employee(
                    id,
                    name,
                    title,
                    newManagerId,
                    department,
                    salary,
                    active
            );
        }
    }

    public record EmployeeManagerView(
            Employee employee,
            Employee manager
    ) {}

    public record DepartmentReport(
            String employeeName,
            String employeeTitle,
            String managerName
    ) {}

    public static final class OrganizationRepository {
        private final Map<Integer, Employee> employees = new HashMap<>();

        public OrganizationRepository(List<Employee> initialEmployees) {
            for (Employee employee : initialEmployees) {
                if (employees.putIfAbsent(employee.id(), employee) != null) {
                    throw new IllegalArgumentException(
                            "Duplicate employee ID: " + employee.id()
                    );
                }
            }

            validate();
        }

        public Employee findById(int id) {
            Employee employee = employees.get(id);

            if (employee == null) {
                throw new IllegalArgumentException(
                        "Unknown employee ID: " + id
                );
            }

            return employee;
        }

        public Optional<Employee> findManager(int employeeId) {
            Employee employee = findById(employeeId);

            if (employee.managerId() == null) {
                return Optional.empty();
            }

            return Optional.of(findById(employee.managerId()));
        }

        public List<Employee> findDirectReports(int managerId) {
            findById(managerId);

            return employees.values()
                    .stream()
                    .filter(employee ->
                            employee.active()
                                    && Objects.equals(
                                            employee.managerId(),
                                            managerId
                                    ))
                    .sorted(Comparator.comparing(Employee::name))
                    .toList();
        }

        public List<EmployeeManagerView> selfJoinView() {
            return employees.values()
                    .stream()
                    .filter(employee -> employee.managerId() != null)
                    .map(employee ->
                            new EmployeeManagerView(
                                    employee,
                                    findManager(employee.id()).orElseThrow()
                            ))
                    .sorted(
                            Comparator.comparing(
                                    view -> view.employee().id()
                            )
                    )
                    .toList();
        }

        public List<Employee> managementChain(int employeeId) {
            List<Employee> chain = new ArrayList<>();
            Set<Integer> visited = new HashSet<>();

            Employee current = findById(employeeId);

            while (current != null) {
                if (!visited.add(current.id())) {
                    throw new IllegalStateException(
                            "Cycle encountered while traversing hierarchy."
                    );
                }

                chain.add(current);

                current = current.managerId() == null
                        ? null
                        : findById(current.managerId());
            }

            return List.copyOf(chain);
        }

        public int hierarchyDepth(int employeeId) {
            return managementChain(employeeId).size() - 1;
        }

        public Optional<Employee> nearestCommonManager(
                int firstEmployeeId,
                int secondEmployeeId
        ) {
            Set<Integer> secondAncestors = managementChain(secondEmployeeId)
                    .stream()
                    .map(Employee::id)
                    .collect(java.util.stream.Collectors.toSet());

            return managementChain(firstEmployeeId)
                    .stream()
                    .filter(employee -> secondAncestors.contains(employee.id()))
                    .findFirst();
        }

        public List<Employee> descendants(int employeeId) {
            findById(employeeId);

            List<Employee> descendants = new ArrayList<>();
            Deque<Integer> queue = new ArrayDeque<>();
            queue.add(employeeId);

            while (!queue.isEmpty()) {
                int managerId = queue.removeFirst();

                for (Employee report : findDirectReports(managerId)) {
                    descendants.add(report);
                    queue.addLast(report.id());
                }
            }

            return List.copyOf(descendants);
        }

        public void changeManager(int employeeId, Integer newManagerId) {
            Employee employee = findById(employeeId);

            if (newManagerId != null) {
                Employee newManager = findById(newManagerId);

                if (newManager.id() == employee.id()) {
                    throw new IllegalStateException(
                            "An employee cannot become their own manager."
                    );
                }

                boolean newManagerIsDescendant = descendants(employeeId)
                        .stream()
                        .anyMatch(descendant ->
                                descendant.id() == newManager.id());

                if (newManagerIsDescendant) {
                    throw new IllegalStateException(
                            "A descendant cannot become a manager because "
                                    + "that would create a cycle."
                    );
                }
            }

            employees.put(
                    employeeId,
                    employee.withManager(newManagerId)
            );

            try {
                validate();
            } catch (RuntimeException error) {
                employees.put(employeeId, employee);
                throw error;
            }
        }

        public List<DepartmentReport> departmentReport(String department) {
            return employees.values()
                    .stream()
                    .filter(employee ->
                            employee.active()
                                    && employee.department().equals(department))
                    .map(employee ->
                            new DepartmentReport(
                                    employee.name(),
                                    employee.title(),
                                    findManager(employee.id())
                                            .map(Employee::name)
                                            .orElse("Organization Root")
                            ))
                    .sorted(
                            Comparator.comparing(
                                    DepartmentReport::employeeName
                            )
                    )
                    .toList();
        }

        private void validate() {
            for (Employee employee : employees.values()) {
                if (employee.managerId() == null) {
                    continue;
                }

                if (employee.managerId() == employee.id()) {
                    throw new IllegalStateException(
                            "Employee " + employee.id()
                                    + " cannot manage themselves."
                    );
                }

                if (!employees.containsKey(employee.managerId())) {
                    throw new IllegalStateException(
                            "Employee " + employee.id()
                                    + " references missing manager "
                                    + employee.managerId()
                    );
                }
            }

            validateCycles();
        }

        private void validateCycles() {
            for (Employee employee : employees.values()) {
                Set<Integer> visited = new HashSet<>();
                Integer currentId = employee.id();

                while (currentId != null) {
                    if (!visited.add(currentId)) {
                        throw new IllegalStateException(
                                "Management cycle detected at employee "
                                        + currentId
                        );
                    }

                    Employee current = findById(currentId);
                    currentId = current.managerId();
                }
            }
        }

        public String renderOrganizationChart() {
            Map<Integer, List<Employee>> children = new HashMap<>();
            List<Employee> roots = new ArrayList<>();

            for (Employee employee : employees.values()) {
                if (employee.managerId() == null) {
                    roots.add(employee);
                } else {
                    children
                            .computeIfAbsent(
                                    employee.managerId(),
                                    ignored -> new ArrayList<>()
                            )
                            .add(employee);
                }
            }

            Comparator<Employee> byName =
                    Comparator.comparing(Employee::name);

            roots.sort(byName);
            children.values().forEach(list -> list.sort(byName));

            StringBuilder output = new StringBuilder();

            for (Employee root : roots) {
                renderEmployee(
                        root,
                        0,
                        children,
                        output
                );
            }

            return output.toString();
        }

        private void renderEmployee(
                Employee employee,
                int depth,
                Map<Integer, List<Employee>> children,
                StringBuilder output
        ) {
            output.append("  ".repeat(depth))
                    .append("- ")
                    .append(employee.name())
                    .append(" (")
                    .append(employee.title())
                    .append(", ")
                    .append(employee.department())
                    .append(")")
                    .append(System.lineSeparator());

            for (Employee child :
                    children.getOrDefault(employee.id(), List.of())) {
                renderEmployee(
                        child,
                        depth + 1,
                        children,
                        output
                );
            }
        }
    }

    public static final class HierarchyService {
        private final OrganizationRepository repository;

        public HierarchyService(OrganizationRepository repository) {
            this.repository = repository;
        }

        public void printSelfJoinView() {
            System.out.println("Employee -> Immediate Manager");

            for (EmployeeManagerView view :
                    repository.selfJoinView()) {
                System.out.printf(
                        "%-12s -> %-12s (%s)%n",
                        view.employee().name(),
                        view.manager().name(),
                        view.manager().title()
                );
            }
        }

        public void printDepartmentReport(String department) {
            System.out.println(
                    System.lineSeparator()
                            + "Department: "
                            + department
            );

            for (DepartmentReport report :
                    repository.departmentReport(department)) {
                System.out.printf(
                        "%-12s | %-24s | Manager: %s%n",
                        report.employeeName(),
                        report.employeeTitle(),
                        report.managerName()
                );
            }
        }

        public void printCommonManager(
                int firstEmployeeId,
                int secondEmployeeId
        ) {
            Employee first = repository.findById(firstEmployeeId);
            Employee second = repository.findById(secondEmployeeId);

            String manager = repository
                    .nearestCommonManager(
                            firstEmployeeId,
                            secondEmployeeId
                    )
                    .map(Employee::name)
                    .orElse("None");

            System.out.printf(
                    "%nNearest common manager of %s and %s: %s%n",
                    first.name(),
                    second.name(),
                    manager
            );
        }
    }

    private static List<Employee> sampleEmployees() {
        return List.of(
                new Employee(
                        1, "Anita", "Chief Executive Officer",
                        null, "Executive", 220000, true
                ),
                new Employee(
                        2, "Rahul", "VP Engineering",
                        1, "Engineering", 170000, true
                ),
                new Employee(
                        3, "Meera", "VP Operations",
                        1, "Operations", 165000, true
                ),
                new Employee(
                        4, "Vikram", "Engineering Manager",
                        2, "Engineering", 125000, true
                ),
                new Employee(
                        5, "Priya", "Engineering Manager",
                        2, "Engineering", 128000, true
                ),
                new Employee(
                        6, "Daniel", "Operations Manager",
                        3, "Operations", 120000, true
                ),
                new Employee(
                        7, "Arjun", "Senior Engineer",
                        4, "Engineering", 105000, true
                ),
                new Employee(
                        8, "Sana", "Software Engineer",
                        4, "Engineering", 90000, true
                ),
                new Employee(
                        9, "Karan", "Software Engineer",
                        5, "Engineering", 92000, true
                ),
                new Employee(
                        10, "Leena", "Software Engineer",
                        5, "Engineering", 94000, true
                ),
                new Employee(
                        11, "Rohit", "Operations Analyst",
                        6, "Operations", 76000, true
                ),
                new Employee(
                        12, "Neha", "Operations Analyst",
                        6, "Operations", 78000, true
                ),
                new Employee(
                        13, "Ishaan", "Intern",
                        7, "Engineering", 30000, true
                )
        );
    }

    public static void main(String[] args) {
        OrganizationRepository repository =
                new OrganizationRepository(sampleEmployees());

        HierarchyService service =
                new HierarchyService(repository);

        System.out.println("EMPLOYEE SELF JOIN ENTERPRISE MODEL");
        System.out.println("===================================");

        System.out.println("\nOrganization chart");
        System.out.println(repository.renderOrganizationChart());

        System.out.println("\nSelf-join view");
        service.printSelfJoinView();

        System.out.println("\nDirect reports of Priya");

        for (Employee employee :
                repository.findDirectReports(5)) {
            System.out.printf(
                    "%s - %s%n",
                    employee.name(),
                    employee.title()
            );
        }

        System.out.println("\nHierarchy depths");

        for (int employeeId : List.of(1, 5, 7, 13)) {
            Employee employee = repository.findById(employeeId);

            System.out.printf(
                    "%s: depth %d%n",
                    employee.name(),
                    repository.hierarchyDepth(employeeId)
            );
        }

        service.printCommonManager(7, 9);
        service.printDepartmentReport("Engineering");

        System.out.println("\nChanging Sana's manager");
        repository.changeManager(8, 5);
        System.out.println(repository.renderOrganizationChart());

        System.out.println("\nAttempting invalid cycle");

        try {
            repository.changeManager(2, 7);
        } catch (IllegalStateException error) {
            System.out.println(
                    "Rejected: " + error.getMessage()
            );
        }

        System.out.println("\nAttempting self-management");

        try {
            repository.changeManager(5, 5);
        } catch (IllegalStateException error) {
            System.out.println(
                    "Rejected: " + error.getMessage()
            );
        }

        System.out.println("\nJava-specific design");
        System.out.println(
                "Records provide immutable reporting projections, while the "
                        + "repository controls hierarchy mutations and validates "
                        + "manager references before accepting state changes."
        );
    }
}
