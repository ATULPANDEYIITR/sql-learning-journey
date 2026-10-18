from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict, deque
from typing import Iterable, Iterator


@dataclass(frozen=True)
class Employee:
    employee_id: int
    name: str
    title: str
    manager_id: int | None


class Organization:
    """In-memory hierarchy supporting recursive-tree operations."""

    def __init__(self, employees: Iterable[Employee]) -> None:
        self.employees = {employee.employee_id: employee for employee in employees}
        self.children: dict[int | None, list[int]] = defaultdict(list)

        for employee in self.employees.values():
            if employee.manager_id is not None and employee.manager_id not in self.employees:
                raise ValueError(
                    f"Employee {employee.employee_id} references "
                    f"missing manager {employee.manager_id}"
                )
            if employee.manager_id == employee.employee_id:
                raise ValueError(
                    f"Employee {employee.employee_id} cannot manage itself"
                )
            self.children[employee.manager_id].append(employee.employee_id)

        self._validate_acyclic()
        for child_list in self.children.values():
            child_list.sort()

    def _validate_acyclic(self) -> None:
        """Detect cycles before performing recursive traversal."""
        state: dict[int, int] = {}

        def visit(employee_id: int) -> None:
            current = state.get(employee_id, 0)
            if current == 1:
                raise ValueError(f"Management cycle detected at employee {employee_id}")
            if current == 2:
                return

            state[employee_id] = 1
            manager_id = self.employees[employee_id].manager_id
            if manager_id is not None:
                visit(manager_id)
            state[employee_id] = 2

        for employee_id in self.employees:
            visit(employee_id)

    def roots(self) -> list[Employee]:
        return [
            self.employees[employee_id]
            for employee_id in self.children[None]
        ]

    def recursive_cte_style(self, root_id: int | None = None) -> list[dict]:
        """
        Mirrors a SQL WITH RECURSIVE traversal.

        The recursive state contains the current node, depth, path and
        accumulated reporting count. Each generated row represents one
        reachable employee from the anchor employee.
        """
        if root_id is None:
            frontier = [
                (employee.employee_id, 0, [employee.employee_id])
                for employee in self.roots()
            ]
        else:
            if root_id not in self.employees:
                raise KeyError(f"Unknown employee: {root_id}")
            frontier = [(root_id, 0, [root_id])]

        result: list[dict] = []

        while frontier:
            employee_id, depth, path = frontier.pop(0)
            employee = self.employees[employee_id]

            result.append(
                {
                    "employee_id": employee.employee_id,
                    "name": employee.name,
                    "title": employee.title,
                    "manager_id": employee.manager_id,
                    "depth": depth,
                    "path": path,
                    "path_text": " > ".join(
                        self.employees[item].name for item in path
                    ),
                }
            )

            for child_id in self.children[employee_id]:
                # The path check is defensive. Validated data cannot cycle,
                # but this mirrors the cycle-protection technique commonly
                # used inside recursive SQL queries.
                if child_id in path:
                    raise RuntimeError("Cycle encountered during traversal")
                frontier.append((child_id, depth + 1, path + [child_id]))

        return result

    def descendants(self, employee_id: int) -> list[dict]:
        rows = self.recursive_cte_style(employee_id)
        return [row for row in rows if row["employee_id"] != employee_id]

    def ancestors(self, employee_id: int) -> list[Employee]:
        if employee_id not in self.employees:
            raise KeyError(f"Unknown employee: {employee_id}")

        result = []
        current = self.employees[employee_id].manager_id

        while current is not None:
            manager = self.employees[current]
            result.append(manager)
            current = manager.manager_id

        return result

    def subtree_sizes(self) -> dict[int, int]:
        """Calculate subtree sizes using post-order dynamic programming."""
        sizes = {employee_id: 1 for employee_id in self.employees}

        ordered = self.recursive_cte_style()
        for row in reversed(ordered):
            employee_id = row["employee_id"]
            manager_id = row["manager_id"]
            if manager_id is not None:
                sizes[manager_id] += sizes[employee_id]

        return sizes

    def print_tree(self) -> None:
        for row in self.recursive_cte_style():
            print(
                f'{"  " * row["depth"]}'
                f'{row["name"]} [{row["title"]}] '
                f'(depth={row["depth"]})'
            )

    def shortest_management_distance(self, source_id: int, target_id: int) -> int | None:
        """
        Find an undirected management distance using breadth-first search.

        This is deliberately different from a recursive tree walk: it
        demonstrates that recursive hierarchy queries can be adapted to
        graph-like questions when parent/child relationships are materialized.
        """
        if source_id not in self.employees or target_id not in self.employees:
            raise KeyError("Both employees must exist")

        if source_id == target_id:
            return 0

        adjacency: dict[int, list[int]] = defaultdict(list)
        for employee in self.employees.values():
            if employee.manager_id is not None:
                adjacency[employee.employee_id].append(employee.manager_id)
                adjacency[employee.manager_id].append(employee.employee_id)

        queue = deque([(source_id, 0)])
        visited = {source_id}

        while queue:
            current, distance = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor == target_id:
                    return distance + 1
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, distance + 1))

        return None


def demonstrate_basic_recursion() -> None:
    organization = Organization(
        [
            Employee(1, "Maya", "Chief Executive Officer", None),
            Employee(2, "Arjun", "CTO", 1),
            Employee(3, "Neha", "CFO", 1),
            Employee(4, "Ravi", "Engineering Director", 2),
            Employee(5, "Sara", "Security Director", 2),
            Employee(6, "Ishaan", "Finance Manager", 3),
            Employee(7, "Kiran", "Backend Lead", 4),
            Employee(8, "Asha", "Backend Engineer", 7),
            Employee(9, "Dev", "Backend Engineer", 7),
            Employee(10, "Meera", "Security Engineer", 5),
            Employee(11, "Vikram", "Security Analyst", 5),
        ]
    )

    print("ORGANIZATIONAL TREE")
    organization.print_tree()

    print("\nDESCENDANTS OF ARJUN")
    for row in organization.descendants(2):
        print(row["path_text"])

    print("\nANCESTORS OF ASHA")
    print(" -> ".join(employee.name for employee in organization.ancestors(8)))

    print("\nSUBTREE SIZES")
    for employee_id, size in sorted(organization.subtree_sizes().items()):
        print(organization.employees[employee_id].name, size)

    print("\nMANAGEMENT DISTANCE")
    print(
        "Asha to Neha:",
        organization.shortest_management_distance(8, 3),
    )


def demonstrate_validation() -> None:
    print("\nVALIDATION EXAMPLE")

    try:
        Organization(
            [
                Employee(1, "Alice", "CEO", None),
                Employee(2, "Bob", "Manager", 3),
                Employee(3, "Carol", "Manager", 2),
            ]
        )
    except ValueError as exc:
        print("Rejected:", exc)

    try:
        Organization(
            [
                Employee(1, "Alice", "CEO", None),
                Employee(2, "Bob", "Manager", 99),
            ]
        )
    except ValueError as exc:
        print("Rejected:", exc)


def recursive_query_equivalent(rows: list[dict], employee_id: int) -> Iterator[dict]:
    """
    A generator equivalent to a recursive query over adjacency-list data.

    Generators avoid constructing the entire result at once, which is useful
    when a hierarchy is large and callers only need a prefix of the result.
    """
    by_manager: dict[int | None, list[dict]] = defaultdict(list)
    for row in rows:
        by_manager[row["manager_id"]].append(row)

    queue = deque()
    for row in by_manager[employee_id]:
        queue.append((row, 1))

    while queue:
        row, depth = queue.popleft()
        enriched = dict(row)
        enriched["depth"] = depth
        yield enriched

        for child in by_manager[row["employee_id"]]:
            queue.append((child, depth + 1))


if __name__ == "__main__":
    demonstrate_basic_recursion()
    demonstrate_validation()

    # This small dataset demonstrates lazy traversal over a pre-existing
    # adjacency-list representation.
    sample_rows = [
        {"employee_id": 10, "name": "Engineering", "manager_id": 1},
        {"employee_id": 11, "name": "Platform", "manager_id": 10},
        {"employee_id": 12, "name": "API", "manager_id": 11},
        {"employee_id": 13, "name": "Frontend", "manager_id": 10},
    ]

    print("\nLAZY RECURSIVE TRAVERSAL")
    for row in recursive_query_equivalent(sample_rows, 1):
        print(row)
