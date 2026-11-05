import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

/*
 * ER Modeling: Enterprise Human Resources Information System.
 *
 * Java 17 implementation.
 *
 * Covers:
 * - Entities and attributes
 * - Primary and candidate keys
 * - Relationship definitions
 * - Cardinality and participation
 * - Relationship attributes
 * - Immutable domain records
 * - Enterprise validation services
 * - Referential integrity
 * - Relational mapping
 * - Exception handling
 *
 * Compile:
 * javac ERModeling.java
 *
 * Run:
 * java ERModeling
 */

public class ERModeling {

    enum DataType {
        INTEGER,
        VARCHAR,
        DECIMAL,
        DATE,
        BOOLEAN
    }

    enum Cardinality {
        ONE_TO_ONE("1:1"),
        ONE_TO_MANY("1:N"),
        MANY_TO_ONE("N:1"),
        MANY_TO_MANY("M:N");

        private final String symbol;

        Cardinality(String symbol) {
            this.symbol = symbol;
        }

        public String symbol() {
            return symbol;
        }
    }

    enum Participation {
        TOTAL,
        PARTIAL
    }

    enum DepartmentStatus {
        ACTIVE,
        INACTIVE
    }

    enum EmployeeStatus {
        ACTIVE,
        ON_LEAVE,
        TERMINATED
    }

    static class ModelingException extends RuntimeException {
        ModelingException(String message) {
            super(message);
        }
    }

    record Attribute(
        String name,
        DataType type,
        boolean primaryKey,
        boolean unique,
        boolean nullable
    ) {
        Attribute {
            if (name == null || !name.matches("[A-Za-z][A-Za-z0-9_]*")) {
                throw new ModelingException("Invalid attribute name.");
            }

            Objects.requireNonNull(type);

            if (primaryKey && nullable) {
                throw new ModelingException(
                    "Primary keys cannot be nullable."
                );
            }
        }
    }

    record EntityDefinition(
        String name,
        List<Attribute> attributes
    ) {
        EntityDefinition {
            if (name == null || name.isBlank()) {
                throw new ModelingException("Entity name is required.");
            }

            attributes = List.copyOf(attributes);

            Set<String> names = new HashSet<>();

            for (Attribute attribute : attributes) {
                if (!names.add(attribute.name())) {
                    throw new ModelingException(
                        "Duplicate attribute: " + attribute.name()
                    );
                }
            }

            if (attributes.stream().noneMatch(Attribute::primaryKey)) {
                throw new ModelingException(
                    "Entity must define a primary key: " + name
                );
            }
        }

        List<String> primaryKeys() {
            return attributes.stream()
                .filter(Attribute::primaryKey)
                .map(Attribute::name)
                .toList();
        }

        Optional<Attribute> findAttribute(String name) {
            return attributes.stream()
                .filter(a -> a.name().equals(name))
                .findFirst();
        }
    }

    record RelationshipEnd(
        String entity,
        int minimum,
        Integer maximum,
        Participation participation
    ) {
        RelationshipEnd {
            if (entity == null || entity.isBlank()) {
                throw new ModelingException("Entity reference is required.");
            }

            if (minimum != 0 && minimum != 1) {
                throw new ModelingException(
                    "Minimum cardinality must be 0 or 1."
                );
            }

            if (maximum != null && maximum != 1) {
                throw new ModelingException(
                    "Maximum cardinality must be 1 or N."
                );
            }

            Participation expected = minimum == 1
                ? Participation.TOTAL
                : Participation.PARTIAL;

            if (participation != expected) {
                throw new ModelingException(
                    "Participation conflicts with minimum cardinality."
                );
            }
        }

        boolean many() {
            return maximum == null;
        }
    }

    record RelationshipDefinition(
        String name,
        RelationshipEnd left,
        RelationshipEnd right,
        List<Attribute> attributes
    ) {
        RelationshipDefinition {
            if (name == null || name.isBlank()) {
                throw new ModelingException(
                    "Relationship name is required."
                );
            }

            Objects.requireNonNull(left);
            Objects.requireNonNull(right);

            attributes = List.copyOf(attributes);

            Set<String> names = new HashSet<>();

            for (Attribute attribute : attributes) {
                if (!names.add(attribute.name())) {
                    throw new ModelingException(
                        "Duplicate relationship attribute."
                    );
                }
            }
        }

        Cardinality cardinality() {
            boolean leftMany = left.many();
            boolean rightMany = right.many();

            if (leftMany && rightMany) {
                return Cardinality.MANY_TO_MANY;
            }

            if (leftMany) {
                return Cardinality.ONE_TO_MANY;
            }

            if (rightMany) {
                return Cardinality.MANY_TO_ONE;
            }

            return Cardinality.ONE_TO_ONE;
        }
    }

    record Department(
        int departmentId,
        String name,
        String location,
        DepartmentStatus status
    ) {
        Department {
            if (departmentId <= 0 || name == null || name.isBlank()) {
                throw new ModelingException("Invalid department.");
            }

            Objects.requireNonNull(status);
        }
    }

    record Employee(
        int employeeId,
        String name,
        String email,
        int departmentId,
        BigDecimal salary,
        EmployeeStatus status
    ) {
        Employee {
            if (employeeId <= 0 || departmentId <= 0) {
                throw new ModelingException("Invalid employee identifiers.");
            }

            if (name == null || name.isBlank()) {
                throw new ModelingException("Employee name is required.");
            }

            if (
                email == null ||
                !email.matches("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")
            ) {
                throw new ModelingException("Invalid employee email.");
            }

            if (salary == null || salary.signum() < 0) {
                throw new ModelingException("Invalid employee salary.");
            }

            Objects.requireNonNull(status);
        }
    }

    record Project(
        int projectId,
        String name,
        LocalDate startDate,
        LocalDate endDate
    ) {
        Project {
            if (projectId <= 0 || name == null || name.isBlank()) {
                throw new ModelingException("Invalid project.");
            }

            Objects.requireNonNull(startDate);

            if (endDate != null && endDate.isBefore(startDate)) {
                throw new ModelingException(
                    "Project end date precedes start date."
                );
            }
        }
    }

    /*
     * Assignment is an associative entity.
     * It resolves the Employee-Project M:N relationship and
     * stores relationship-specific attributes.
     */
    record Assignment(
        int employeeId,
        int projectId,
        LocalDate assignedDate,
        String role,
        BigDecimal allocation
    ) {
        Assignment {
            if (employeeId <= 0 || projectId <= 0) {
                throw new ModelingException("Invalid assignment keys.");
            }

            Objects.requireNonNull(assignedDate);

            if (role == null || role.isBlank()) {
                throw new ModelingException("Assignment role is required.");
            }

            if (
                allocation == null ||
                allocation.signum() <= 0 ||
                allocation.compareTo(new BigDecimal("100")) > 0
            ) {
                throw new ModelingException(
                    "Allocation must be greater than 0 and at most 100."
                );
            }
        }
    }

    static class ERModel {
        private final String name;

        private final Map<String, EntityDefinition> entities =
            new HashMap<>();

        private final Map<String, RelationshipDefinition> relationships =
            new HashMap<>();

        ERModel(String name) {
            this.name = Objects.requireNonNull(name);
        }

        void addEntity(EntityDefinition entity) {
            if (entities.putIfAbsent(entity.name(), entity) != null) {
                throw new ModelingException(
                    "Duplicate entity: " + entity.name()
                );
            }
        }

        void addRelationship(RelationshipDefinition relationship) {
            if (
                relationships.containsKey(relationship.name()) ||
                !entities.containsKey(relationship.left().entity()) ||
                !entities.containsKey(relationship.right().entity())
            ) {
                throw new ModelingException(
                    "Invalid or duplicate relationship."
                );
            }

            relationships.put(relationship.name(), relationship);
        }

        void validate() {
            for (RelationshipDefinition relationship :
                relationships.values()) {

                if (
                    !entities.containsKey(relationship.left().entity()) ||
                    !entities.containsKey(relationship.right().entity())
                ) {
                    throw new ModelingException(
                        "Relationship references missing entity."
                    );
                }
            }
        }

        void print() {
            System.out.println("\nER MODEL: " + name);

            System.out.println("\nENTITIES");

            entities.values().stream()
                .sorted((a, b) -> a.name().compareTo(b.name()))
                .forEach(entity -> {
                    System.out.println("\n" + entity.name());

                    entity.attributes().forEach(attribute -> {
                        System.out.printf(
                            "  %-20s %-10s PK=%s UNIQUE=%s NULLABLE=%s%n",
                            attribute.name(),
                            attribute.type(),
                            attribute.primaryKey(),
                            attribute.unique(),
                            attribute.nullable()
                        );
                    });
                });

            System.out.println("\nRELATIONSHIPS");

            relationships.values().stream()
                .sorted((a, b) -> a.name().compareTo(b.name()))
                .forEach(relationship -> {
                    System.out.printf(
                        "%s: %s <-> %s | %s%n",
                        relationship.name(),
                        relationship.left().entity(),
                        relationship.right().entity(),
                        relationship.cardinality().symbol()
                    );

                    System.out.println(
                        "  Left participation: " +
                        relationship.left().participation()
                    );

                    System.out.println(
                        "  Right participation: " +
                        relationship.right().participation()
                    );
                });
        }

        void printRelationalMapping() {
            System.out.println("\nRELATIONAL MAPPING");

            relationships.values().forEach(relationship -> {
                String implementation = switch (
                    relationship.cardinality()
                ) {
                    case MANY_TO_MANY -> "JUNCTION TABLE";
                    case ONE_TO_ONE -> "UNIQUE FOREIGN KEY";
                    case ONE_TO_MANY, MANY_TO_ONE ->
                        "FOREIGN KEY ON MANY SIDE";
                };

                System.out.println(
                    relationship.name() + " -> " + implementation
                );

                if (!relationship.attributes().isEmpty()) {
                    System.out.println(
                        "  Relationship attributes: " +
                        relationship.attributes().stream()
                            .map(Attribute::name)
                            .collect(Collectors.joining(", "))
                    );
                }
            });
        }
    }

    static class HRService {
        private final Map<Integer, Department> departments =
            new HashMap<>();

        private final Map<Integer, Employee> employees =
            new HashMap<>();

        private final Map<Integer, Project> projects =
            new HashMap<>();

        private final Map<String, Assignment> assignments =
            new HashMap<>();

        private final Set<String> employeeEmails = new HashSet<>();

        void addDepartment(Department department) {
            if (departments.putIfAbsent(
                department.departmentId(),
                department
            ) != null) {
                throw new ModelingException("Duplicate department ID.");
            }
        }

        void addEmployee(Employee employee) {
            if (!departments.containsKey(employee.departmentId())) {
                throw new ModelingException(
                    "Employee references unknown department."
                );
            }

            if (employeeEmails.contains(employee.email())) {
                throw new ModelingException(
                    "Employee email must be unique."
                );
            }

            if (employees.putIfAbsent(
                employee.employeeId(),
                employee
            ) != null) {
                throw new ModelingException("Duplicate employee ID.");
            }

            employeeEmails.add(employee.email());
        }

        void addProject(Project project) {
            if (projects.putIfAbsent(
                project.projectId(),
                project
            ) != null) {
                throw new ModelingException("Duplicate project ID.");
            }
        }

        void assign(Assignment assignment) {
            if (!employees.containsKey(assignment.employeeId())) {
                throw new ModelingException("Employee does not exist.");
            }

            if (!projects.containsKey(assignment.projectId())) {
                throw new ModelingException("Project does not exist.");
            }

            Employee employee = employees.get(assignment.employeeId());

            if (employee.status() != EmployeeStatus.ACTIVE) {
                throw new ModelingException(
                    "Only active employees can receive assignments."
                );
            }

            Project project = projects.get(assignment.projectId());

            if (
                project.endDate() != null &&
                assignment.assignedDate().isAfter(project.endDate())
            ) {
                throw new ModelingException(
                    "Assignment occurs after project completion."
                );
            }

            String key = assignment.employeeId() + ":" +
                assignment.projectId();

            if (assignments.putIfAbsent(key, assignment) != null) {
                throw new ModelingException(
                    "Duplicate employee-project assignment."
                );
            }
        }

        void validateTotalParticipation() {
            // Each employee must belong to exactly one department.
            for (Employee employee : employees.values()) {
                if (!departments.containsKey(employee.departmentId())) {
                    throw new ModelingException(
                        "Employee department participation violated."
                    );
                }
            }

            // Every active project must have at least one assignment.
            for (Project project : projects.values()) {
                boolean hasAssignment = assignments.values().stream()
                    .anyMatch(a -> a.projectId() == project.projectId());

                if (!hasAssignment) {
                    throw new ModelingException(
                        "Project has no employee assignment: " +
                        project.projectId()
                    );
                }
            }
        }

        void report() {
            System.out.println("\nHR REPORT");

            for (Department department : departments.values()) {
                List<Employee> departmentEmployees = employees.values()
                    .stream()
                    .filter(e ->
                        e.departmentId() == department.departmentId()
                    )
                    .toList();

                BigDecimal payroll = departmentEmployees.stream()
                    .filter(e -> e.status() != EmployeeStatus.TERMINATED)
                    .map(Employee::salary)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

                System.out.println(
                    department.name() +
                    " | Employees: " + departmentEmployees.size() +
                    " | Payroll: " + payroll
                );
            }

            System.out.println(
                "Projects: " + projects.size() +
                " | Assignments: " + assignments.size()
            );
        }

        int employeeCount() {
            return employees.size();
        }

        int assignmentCount() {
            return assignments.size();
        }
    }

    static RelationshipEnd end(
        String entity,
        int minimum,
        Integer maximum
    ) {
        return new RelationshipEnd(
            entity,
            minimum,
            maximum,
            minimum == 1
                ? Participation.TOTAL
                : Participation.PARTIAL
        );
    }

    static ERModel buildModel() {
        ERModel model = new ERModel("Enterprise HR Information System");

        model.addEntity(new EntityDefinition("Department", List.of(
            new Attribute(
                "department_id", DataType.INTEGER, true, true, false
            ),
            new Attribute(
                "department_name", DataType.VARCHAR, false, true, false
            ),
            new Attribute(
                "location", DataType.VARCHAR, false, false, true
            )
        )));

        model.addEntity(new EntityDefinition("Employee", List.of(
            new Attribute(
                "employee_id", DataType.INTEGER, true, true, false
            ),
            new Attribute(
                "employee_name", DataType.VARCHAR, false, false, false
            ),
            new Attribute(
                "email", DataType.VARCHAR, false, true, false
            ),
            new Attribute(
                "salary", DataType.DECIMAL, false, false, false
            )
        )));

        model.addEntity(new EntityDefinition("Project", List.of(
            new Attribute(
                "project_id", DataType.INTEGER, true, true, false
            ),
            new Attribute(
                "project_name", DataType.VARCHAR, false, false, false
            ),
            new Attribute(
                "start_date", DataType.DATE, false, false, false
            )
        )));

        model.addEntity(new EntityDefinition("Assignment", List.of(
            new Attribute(
                "employee_id", DataType.INTEGER, true, false, false
            ),
            new Attribute(
                "project_id", DataType.INTEGER, true, false, false
            ),
            new Attribute(
                "assigned_date", DataType.DATE, false, false, false
            ),
            new Attribute(
                "role", DataType.VARCHAR, false, false, false
            )
        )));

        model.addRelationship(new RelationshipDefinition(
            "DepartmentEmployee",
            end("Department", 0, null),
            end("Employee", 1, 1),
            List.of()
        ));

        model.addRelationship(new RelationshipDefinition(
            "EmployeeProject",
            end("Employee", 0, null),
            end("Project", 1, null),
            List.of(
                new Attribute(
                    "assigned_date",
                    DataType.DATE,
                    false,
                    false,
                    false
                ),
                new Attribute(
                    "role",
                    DataType.VARCHAR,
                    false,
                    false,
                    false
                )
            )
        ));

        return model;
    }

    static void runTests() {
        HRService service = new HRService();

        service.addDepartment(new Department(
            10,
            "Technology",
            "Lucknow",
            DepartmentStatus.ACTIVE
        ));

        service.addDepartment(new Department(
            20,
            "Research",
            "Patna",
            DepartmentStatus.ACTIVE
        ));

        service.addEmployee(new Employee(
            101,
            "Aarav Sharma",
            "aarav@example.com",
            10,
            new BigDecimal("85000.00"),
            EmployeeStatus.ACTIVE
        ));

        service.addEmployee(new Employee(
            102,
            "Diya Verma",
            "diya@example.com",
            10,
            new BigDecimal("92000.00"),
            EmployeeStatus.ACTIVE
        ));

        service.addEmployee(new Employee(
            103,
            "Kabir Singh",
            "kabir@example.com",
            20,
            new BigDecimal("78000.00"),
            EmployeeStatus.ACTIVE
        ));

        service.addProject(new Project(
            501,
            "Database Modernization",
            LocalDate.of(2026, 10, 1),
            LocalDate.of(2027, 3, 31)
        ));

        service.addProject(new Project(
            502,
            "Enterprise Analytics",
            LocalDate.of(2026, 11, 1),
            LocalDate.of(2027, 6, 30)
        ));

        service.assign(new Assignment(
            101,
            501,
            LocalDate.of(2026, 10, 5),
            "Database Engineer",
            new BigDecimal("60")
        ));

        service.assign(new Assignment(
            102,
            501,
            LocalDate.of(2026, 10, 6),
            "Project Manager",
            new BigDecimal("40")
        ));

        service.assign(new Assignment(
            103,
            502,
            LocalDate.of(2026, 11, 2),
            "Data Analyst",
            new BigDecimal("80")
        ));

        service.assign(new Assignment(
            101,
            502,
            LocalDate.of(2026, 11, 3),
            "Technical Lead",
            new BigDecimal("40")
        ));

        service.validateTotalParticipation();

        if (service.employeeCount() != 3) {
            throw new ModelingException("Employee count test failed.");
        }

        if (service.assignmentCount() != 4) {
            throw new ModelingException("Assignment count test failed.");
        }

        boolean rejected = false;

        try {
            service.addEmployee(new Employee(
                104,
                "Duplicate Email",
                "aarav@example.com",
                10,
                new BigDecimal("50000"),
                EmployeeStatus.ACTIVE
            ));
        } catch (ModelingException exception) {
            rejected = true;
        }

        if (!rejected) {
            throw new ModelingException(
                "Duplicate email validation failed."
            );
        }

        rejected = false;

        try {
            service.addEmployee(new Employee(
                105,
                "Unknown Department",
                "unknown@example.com",
                999,
                new BigDecimal("50000"),
                EmployeeStatus.ACTIVE
            ));
        } catch (ModelingException exception) {
            rejected = true;
        }

        if (!rejected) {
            throw new ModelingException(
                "Foreign key validation failed."
            );
        }

        System.out.println("\nVALIDATION TESTS");
        System.out.println("PASS: Department entity validation");
        System.out.println("PASS: Employee entity validation");
        System.out.println("PASS: Project entity validation");
        System.out.println("PASS: Assignment associative entity");
        System.out.println("PASS: M:N relationship resolution");
        System.out.println("PASS: Primary and candidate key rules");
        System.out.println("PASS: Referential integrity");
        System.out.println("PASS: Participation validation");
        System.out.println("PASS: Duplicate email rejection");
        System.out.println("PASS: Invalid department rejection");

        service.report();
    }

    public static void main(String[] args) {
        try {
            ERModel model = buildModel();

            model.validate();
            model.print();
            model.printRelationalMapping();

            runTests();

            System.out.println("\nER modeling execution completed.");

        } catch (ModelingException exception) {
            System.err.println(
                "MODELING ERROR: " + exception.getMessage()
            );
            System.exit(1);
        }
    }
}
