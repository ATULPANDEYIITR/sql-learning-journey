import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class RecursiveCTEOrganization {

    record Employee(
        int id,
        String name,
        String title,
        Integer managerId
    ) {}

    record TraversalNode(
        Employee employee,
        int depth,
        List<Integer> path
    ) {}

    static final class OrganizationService {
        private final Map<Integer, Employee> employees;
        private final Map<Integer, List<Integer>> children;

        OrganizationService(List<Employee> source) {
            this.employees = new HashMap<>();
            this.children = new HashMap<>();

            for (Employee employee : source) {
                if (employees.putIfAbsent(employee.id(), employee) != null) {
                    throw new IllegalArgumentException(
                        "Duplicate employee ID: " + employee.id()
                    );
                }
            }

            for (Employee employee : employees.values()) {
                if (employee.managerId() != null &&
                    !employees.containsKey(employee.managerId())) {
                    throw new IllegalArgumentException(
                        "Missing manager for employee " + employee.id()
                    );
                }

                if (employee.managerId() != null &&
                    employee.managerId() == employee.id()) {
                    throw new IllegalArgumentException(
                        "Self-management is not permitted"
                    );
                }

                children
                    .computeIfAbsent(employee.managerId(), ignored -> new ArrayList<>())
                    .add(employee.id());
            }

            children.values().forEach(list -> list.sort(Comparator.naturalOrder()));
            validateAcyclic();
        }

        private void validateAcyclic() {
            Map<Integer, VisitState> states = new HashMap<>();

            for (Integer employeeId : employees.keySet()) {
                visitForCycleCheck(employeeId, states);
            }
        }

        private void visitForCycleCheck(
            int employeeId,
            Map<Integer, VisitState> states
        ) {
            VisitState state = states.getOrDefault(employeeId, VisitState.UNVISITED);

            if (state == VisitState.ACTIVE) {
                throw new IllegalArgumentException(
                    "Management cycle detected at employee " + employeeId
                );
            }

            if (state == VisitState.COMPLETE) {
                return;
            }

            states.put(employeeId, VisitState.ACTIVE);

            Integer managerId = employees.get(employeeId).managerId();
            if (managerId != null) {
                visitForCycleCheck(managerId, states);
            }

            states.put(employeeId, VisitState.COMPLETE);
        }

        List<TraversalNode> recursiveTraversal(Integer rootId) {
            ArrayDeque<TraversalNode> queue = new ArrayDeque<>();
            List<TraversalNode> result = new ArrayList<>();

            if (rootId == null) {
                for (Integer root : children.getOrDefault(null, List.of())) {
                    queue.add(new TraversalNode(
                        employees.get(root),
                        0,
                        List.of(root)
                    ));
                }
            } else {
                Employee root = employees.get(rootId);
                if (root == null) {
                    throw new IllegalArgumentException("Unknown root employee");
                }

                queue.add(new TraversalNode(
                    root,
                    0,
                    List.of(rootId)
                ));
            }

            while (!queue.isEmpty()) {
                TraversalNode current = queue.removeFirst();
                result.add(current);

                for (Integer childId :
                    children.getOrDefault(current.employee().id(), List.of())) {

                    if (current.path().contains(childId)) {
                        throw new IllegalStateException(
                            "Cycle encountered during recursive traversal"
                        );
                    }

                    List<Integer> nextPath =
                        new ArrayList<>(current.path());
                    nextPath.add(childId);

                    queue.addLast(new TraversalNode(
                        employees.get(childId),
                        current.depth() + 1,
                        List.copyOf(nextPath)
                    ));
                }
            }

            return List.copyOf(result);
        }

        List<Employee> ancestors(int employeeId) {
            Employee current = employees.get(employeeId);
            if (current == null) {
                throw new IllegalArgumentException("Unknown employee");
            }

            List<Employee> result = new ArrayList<>();
            Integer managerId = current.managerId();

            while (managerId != null) {
                Employee manager = employees.get(managerId);
                result.add(manager);
                managerId = manager.managerId();
            }

            return List.copyOf(result);
        }

        Map<Integer, Long> subtreeSizes() {
            List<TraversalNode> nodes = recursiveTraversal(null);
            Map<Integer, Long> sizes = new HashMap<>();

            for (Integer id : employees.keySet()) {
                sizes.put(id, 1L);
            }

            /*
             * A reverse traversal lets each descendant contribute its
             * completed subtree size to its parent.
             */
            for (int index = nodes.size() - 1; index >= 0; index--) {
                Employee employee = nodes.get(index).employee();
                Integer managerId = employee.managerId();

                if (managerId != null) {
                    sizes.merge(
                        managerId,
                        sizes.get(employee.id()),
                        Long::sum
                    );
                }
            }

            return Map.copyOf(sizes);
        }

        void printTree() {
            for (TraversalNode node : recursiveTraversal(null)) {
                System.out.printf(
                    "%s%s [%s] depth=%d path=%s%n",
                    "  ".repeat(node.depth()),
                    node.employee().name(),
                    node.employee().title(),
                    node.depth(),
                    node.path()
                );
            }
        }
    }

    enum VisitState {
        UNVISITED,
        ACTIVE,
        COMPLETE
    }

    public static void main(String[] args) {
        OrganizationService organization = new OrganizationService(List.of(
            new Employee(1, "Maya", "CEO", null),
            new Employee(2, "Arjun", "CTO", 1),
            new Employee(3, "Neha", "CFO", 1),
            new Employee(4, "Ravi", "Engineering Director", 2),
            new Employee(5, "Sara", "Security Director", 2),
            new Employee(6, "Asha", "Backend Engineer", 4),
            new Employee(7, "Dev", "Backend Engineer", 4),
            new Employee(8, "Meera", "Security Engineer", 5)
        ));

        System.out.println("ORGANIZATION");
        organization.printTree();

        System.out.println("\nANCESTORS OF ASHA");
        organization.ancestors(6)
            .stream()
            .map(Employee::name)
            .forEach(System.out::println);

        System.out.println("\nSUBTREE SIZES");
        organization.subtreeSizes()
            .entrySet()
            .stream()
            .sorted(Map.Entry.comparingByKey())
            .forEach(entry ->
                System.out.println(entry.getKey() + " -> " + entry.getValue())
            );

        System.out.println("\nINVALID CYCLE");
        try {
            new OrganizationService(List.of(
                new Employee(10, "Alpha", "Manager", 11),
                new Employee(11, "Beta", "Manager", 10)
            ));
        } catch (IllegalArgumentException error) {
            System.out.println("Rejected: " + error.getMessage());
        }
    }
}
