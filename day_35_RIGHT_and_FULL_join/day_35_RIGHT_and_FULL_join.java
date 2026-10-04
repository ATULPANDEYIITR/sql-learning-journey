import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

public class JoinGovernanceDemo {

    enum Relationship {
        MATCHED,
        EMPLOYEE_WITHOUT_DEPARTMENT,
        DEPARTMENT_WITHOUT_EMPLOYEE
    }

    record Employee(
        int employeeId,
        String name,
        Optional<Integer> departmentId
    ) {
        Employee {
            if (employeeId <= 0) {
                throw new IllegalArgumentException("Employee ID must be positive.");
            }
            Objects.requireNonNull(name, "Employee name cannot be null.");
            Objects.requireNonNull(departmentId, "departmentId wrapper cannot be null.");
        }
    }

    record Department(
        int departmentId,
        String name,
        Optional<Integer> managerId
    ) {
        Department {
            if (departmentId <= 0) {
                throw new IllegalArgumentException(
                    "Department ID must be positive."
                );
            }
            Objects.requireNonNull(name, "Department name cannot be null.");
            Objects.requireNonNull(managerId, "managerId wrapper cannot be null.");
        }
    }

    record JoinResult(
        Optional<Employee> employee,
        Optional<Department> department,
        Relationship relationship
    ) {}

    interface JoinPolicy<L, R> {
        List<JoinResult> execute(List<L> left, List<R> right);
    }

    static final class FullOuterJoinPolicy
        implements JoinPolicy<Employee, Department> {

        @Override
        public List<JoinResult> execute(
            List<Employee> employees,
            List<Department> departments
        ) {
            /*
             * Java's Map provides the hash-index needed for efficient equality
             * matching. A list is stored for each key because many employees
             * can belong to one department.
             */
            Map<Integer, List<Department>> departmentsById = new HashMap<>();

            for (Department department : departments) {
                departmentsById
                    .computeIfAbsent(
                        department.departmentId(),
                        ignored -> new ArrayList<>()
                    )
                    .add(department);
            }

            Set<Integer> matchedDepartmentIds = new HashSet<>();
            List<JoinResult> results = new ArrayList<>();

            for (Employee employee : employees) {
                Optional<Integer> departmentId = employee.departmentId();

                if (departmentId.isEmpty()) {
                    /*
                     * Optional.empty() represents SQL NULL for this model.
                     * It must not match another empty value through equality.
                     */
                    results.add(
                        new JoinResult(
                            Optional.of(employee),
                            Optional.empty(),
                            Relationship.EMPLOYEE_WITHOUT_DEPARTMENT
                        )
                    );
                    continue;
                }

                List<Department> matches =
                    departmentsById.getOrDefault(
                        departmentId.get(),
                        List.of()
                    );

                if (matches.isEmpty()) {
                    results.add(
                        new JoinResult(
                            Optional.of(employee),
                            Optional.empty(),
                            Relationship.EMPLOYEE_WITHOUT_DEPARTMENT
                        )
                    );
                    continue;
                }

                for (Department department : matches) {
                    matchedDepartmentIds.add(department.departmentId());

                    results.add(
                        new JoinResult(
                            Optional.of(employee),
                            Optional.of(department),
                            Relationship.MATCHED
                        )
                    );
                }
            }

            /*
             * The second pass supplies the right-side preservation rule of a
             * FULL OUTER JOIN. Departments never encountered during matching
             * must still appear.
             */
            for (Department department : departments) {
                if (!matchedDepartmentIds.contains(department.departmentId())) {
                    results.add(
                        new JoinResult(
                            Optional.empty(),
                            Optional.of(department),
                            Relationship.DEPARTMENT_WITHOUT_EMPLOYEE
                        )
                    );
                }
            }

            return List.copyOf(results);
        }
    }

    static final class RightJoinPolicy
        implements JoinPolicy<Employee, Department> {

        @Override
        public List<JoinResult> execute(
            List<Employee> employees,
            List<Department> departments
        ) {
            Map<Integer, List<Employee>> employeesByDepartment =
                new HashMap<>();

            for (Employee employee : employees) {
                employee.departmentId().ifPresent(
                    id -> employeesByDepartment
                        .computeIfAbsent(id, ignored -> new ArrayList<>())
                        .add(employee)
                );
            }

            List<JoinResult> results = new ArrayList<>();

            /*
             * Iterating over departments first expresses RIGHT JOIN's key
             * semantic: every row from the right relation survives.
             */
            for (Department department : departments) {
                List<Employee> matches =
                    employeesByDepartment.getOrDefault(
                        department.departmentId(),
                        List.of()
                    );

                if (matches.isEmpty()) {
                    results.add(
                        new JoinResult(
                            Optional.empty(),
                            Optional.of(department),
                            Relationship.DEPARTMENT_WITHOUT_EMPLOYEE
                        )
                    );
                } else {
                    for (Employee employee : matches) {
                        results.add(
                            new JoinResult(
                                Optional.of(employee),
                                Optional.of(department),
                                Relationship.MATCHED
                            )
                        );
                    }
                }
            }

            return List.copyOf(results);
        }
    }

    static final class JoinReportService {
        private final JoinPolicy<Employee, Department> policy;

        JoinReportService(JoinPolicy<Employee, Department> policy) {
            this.policy = Objects.requireNonNull(policy);
        }

        List<JoinResult> generate(
            List<Employee> employees,
            List<Department> departments
        ) {
            validateUniqueDepartmentIds(departments);
            return policy.execute(
                List.copyOf(employees),
                List.copyOf(departments)
            );
        }

        private void validateUniqueDepartmentIds(
            List<Department> departments
        ) {
            Set<Integer> ids = new HashSet<>();

            for (Department department : departments) {
                if (!ids.add(department.departmentId())) {
                    throw new IllegalStateException(
                        "Department master contains duplicate ID: "
                            + department.departmentId()
                    );
                }
            }
        }
    }

    static void printReport(
        String title,
        List<JoinResult> results
    ) {
        System.out.println("\n=== " + title + " ===");
        System.out.println(
            "employeeId | employeeName | departmentId | departmentName | relationship"
        );

        for (JoinResult result : results) {
            String employeeId = result.employee()
                .map(employee -> Integer.toString(employee.employeeId()))
                .orElse("NULL");

            String employeeName = result.employee()
                .map(Employee::name)
                .orElse("NULL");

            String departmentId = result.department()
                .map(department -> Integer.toString(department.departmentId()))
                .orElse("NULL");

            String departmentName = result.department()
                .map(Department::name)
                .orElse("NULL");

            System.out.printf(
                "%-10s | %-13s | %-12s | %-15s | %s%n",
                employeeId,
                employeeName,
                departmentId,
                departmentName,
                result.relationship()
            );
        }
    }

    static void printMetrics(List<JoinResult> results) {
        Map<Relationship, Long> counts = new HashMap<>();

        for (JoinResult result : results) {
            counts.merge(
                result.relationship(),
                1L,
                Long::sum
            );
        }

        System.out.println("\n=== Reconciliation metrics ===");
        System.out.println(
            "Matched: "
                + counts.getOrDefault(Relationship.MATCHED, 0L)
        );
        System.out.println(
            "Employees without departments: "
                + counts.getOrDefault(
                    Relationship.EMPLOYEE_WITHOUT_DEPARTMENT,
                    0L
                )
        );
        System.out.println(
            "Departments without employees: "
                + counts.getOrDefault(
                    Relationship.DEPARTMENT_WITHOUT_EMPLOYEE,
                    0L
                )
        );
    }

    public static void main(String[] args) {
        List<Employee> employees = List.of(
            new Employee(101, "Aarav", Optional.of(10)),
            new Employee(102, "Meera", Optional.of(20)),
            new Employee(103, "Kabir", Optional.of(20)),
            new Employee(104, "Isha", Optional.of(40)),
            new Employee(105, "Rohan", Optional.empty())
        );

        List<Department> departments = List.of(
            new Department(10, "Engineering", Optional.of(9001)),
            new Department(20, "Finance", Optional.of(9002)),
            new Department(30, "Research", Optional.of(9003)),
            new Department(40, "Operations", Optional.empty()),
            new Department(50, "Legal", Optional.of(9005))
        );

        JoinReportService rightJoinService =
            new JoinReportService(new RightJoinPolicy());

        JoinReportService fullJoinService =
            new JoinReportService(new FullOuterJoinPolicy());

        List<JoinResult> rightResults =
            rightJoinService.generate(employees, departments);

        printReport(
            "RIGHT JOIN: department-centered enterprise report",
            rightResults
        );

        List<JoinResult> fullResults =
            fullJoinService.generate(employees, departments);

        printReport(
            "FULL OUTER JOIN: master-data reconciliation",
            fullResults
        );

        printMetrics(fullResults);

        /*
         * A second employee in the same department illustrates one-to-many
         * matching without changing the join policy itself.
         */
        List<Employee> expandedEmployees = new ArrayList<>(employees);
        expandedEmployees.add(
            new Employee(106, "Nadia", Optional.of(20))
        );

        List<JoinResult> expandedResults =
            fullJoinService.generate(expandedEmployees, departments);

        printReport(
            "FULL JOIN with one-to-many department membership",
            expandedResults
        );

        /*
         * The service returns immutable result lists. This prevents a caller
         * from accidentally changing the generated reconciliation state.
         */
        try {
            fullResults.add(
                new JoinResult(
                    Optional.empty(),
                    Optional.empty(),
                    Relationship.MATCHED
                )
            );
        } catch (UnsupportedOperationException expected) {
            System.out.println(
                "\nImmutable result protection: modification rejected."
            );
        }

        System.out.println("\nEnterprise join model completed.");
    }
}
