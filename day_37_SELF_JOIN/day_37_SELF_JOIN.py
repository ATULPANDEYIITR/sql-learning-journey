from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import Optional


@dataclass
class Employee:
    employee_id: int
    name: str
    title: str
    manager_id: Optional[int]
    department: str
    salary: float
    active: bool = True


class Organization:
    """
    In-memory demonstration of hierarchical employee-manager relationships.

    The central relationship is a self-reference:
        employee.manager_id -> another employee.employee_id

    A database SELF JOIN represents this relationship by joining the employee
    table to itself. The Python model below makes the same relationship explicit.
    """

    def __init__(self, employees: list[Employee]):
        self.employees = {employee.employee_id: employee for employee in employees}
        self._validate()

    def _validate(self) -> None:
        """Validate references and reject malformed hierarchy data."""
        for employee in self.employees.values():
            if employee.manager_id is None:
                continue

            if employee.manager_id == employee.employee_id:
                raise ValueError(
                    f"Employee {employee.employee_id} cannot manage themselves."
                )

            if employee.manager_id not in self.employees:
                raise ValueError(
                    f"Employee {employee.employee_id} references "
                    f"missing manager {employee.manager_id}."
                )

        self._validate_no_cycles()

    def _validate_no_cycles(self) -> None:
        """Detect cycles such as A -> B -> C -> A."""
        for employee in self.employees.values():
            visited: set[int] = set()
            current_id: Optional[int] = employee.employee_id

            while current_id is not None:
                if current_id in visited:
                    raise ValueError(
                        f"Management cycle detected involving employee {current_id}."
                    )

                visited.add(current_id)
                current = self.employees[current_id]
                current_id = current.manager_id

    def direct_reports(self, manager_id: int) -> list[Employee]:
        """Return employees whose manager_id equals manager_id."""
        if manager_id not in self.employees:
            raise KeyError(f"Unknown manager ID: {manager_id}")

        return sorted(
            (
                employee
                for employee in self.employees.values()
                if employee.manager_id == manager_id and employee.active
            ),
            key=lambda employee: employee.name,
        )

    def manager(self, employee_id: int) -> Optional[Employee]:
        """Return the immediate manager of an employee."""
        employee = self._get_employee(employee_id)

        if employee.manager_id is None:
            return None

        return self.employees[employee.manager_id]

    def _get_employee(self, employee_id: int) -> Employee:
        try:
            return self.employees[employee_id]
        except KeyError as exc:
            raise KeyError(f"Unknown employee ID: {employee_id}") from exc

    def manager_employee_pairs(self) -> list[tuple[Employee, Employee]]:
        """
        Produce the logical equivalent of:

        SELECT e.name AS employee, m.name AS manager
        FROM employees e
        JOIN employees m ON e.manager_id = m.employee_id;
        """
        pairs = []

        for employee in self.employees.values():
            manager = self.manager(employee.employee_id)
            if manager is not None:
                pairs.append((employee, manager))

        return sorted(pairs, key=lambda pair: pair[0].employee_id)

    def hierarchy_levels(self) -> dict[int, int]:
        """
        Calculate distance from the organization root.

        CEO/root employees have level 0.
        Their direct reports have level 1, and so on.
        """
        levels: dict[int, int] = {}

        roots = [
            employee.employee_id
            for employee in self.employees.values()
            if employee.manager_id is None
        ]

        queue = deque((root_id, 0) for root_id in roots)

        while queue:
            employee_id, level = queue.popleft()
            levels[employee_id] = level

            for report in self.direct_reports(employee_id):
                queue.append((report.employee_id, level + 1))

        return levels

    def organization_chart(self) -> str:
        """Render the hierarchy using indentation."""
        children: dict[Optional[int], list[Employee]] = defaultdict(list)

        for employee in self.employees.values():
            children[employee.manager_id].append(employee)

        for reports in children.values():
            reports.sort(key=lambda employee: employee.name)

        lines: list[str] = []

        def render(manager_id: Optional[int], depth: int) -> None:
            for employee in children.get(manager_id, []):
                status = "" if employee.active else " [INACTIVE]"
                lines.append(
                    f"{'  ' * depth}- {employee.name} "
                    f"({employee.title}, {employee.department}){status}"
                )
                render(employee.employee_id, depth + 1)

        render(None, 0)
        return "\n".join(lines)

    def chain_to_root(self, employee_id: int) -> list[Employee]:
        """Return employee -> manager -> manager's manager -> root."""
        chain: list[Employee] = []
        current = self._get_employee(employee_id)

        while True:
            chain.append(current)

            if current.manager_id is None:
                break

            current = self.employees[current.manager_id]

        return chain

    def common_manager(
        self, first_employee_id: int, second_employee_id: int
    ) -> Optional[Employee]:
        """
        Find the nearest common manager using ancestor chains.

        This is useful for questions such as:
        'Which manager is the closest shared supervisor of two employees?'
        """
        first_chain = self.chain_to_root(first_employee_id)
        second_chain = self.chain_to_root(second_employee_id)

        first_ancestors = {employee.employee_id: employee for employee in first_chain}

        for employee in second_chain:
            if employee.employee_id in first_ancestors:
                return employee

        return None

    def count_direct_reports(self) -> dict[int, int]:
        """Count direct reports for every employee."""
        counts = {employee_id: 0 for employee_id in self.employees}

        for employee in self.employees.values():
            if employee.manager_id is not None:
                counts[employee.manager_id] += 1

        return counts

    def management_span(self, employee_id: int) -> int:
        """Return number of management relationships between employee and root."""
        return len(self.chain_to_root(employee_id)) - 1

    def move_employee(self, employee_id: int, new_manager_id: Optional[int]) -> None:
        """
        Change an employee's manager while preserving hierarchy integrity.

        A new manager cannot be the employee themselves or one of their
        descendants, because either case would create a cycle.
        """
        employee = self._get_employee(employee_id)

        if new_manager_id == employee_id:
            raise ValueError("An employee cannot become their own manager.")

        if new_manager_id is not None:
            new_manager = self._get_employee(new_manager_id)

            descendant_ids = self._descendant_ids(employee_id)

            if new_manager.employee_id in descendant_ids:
                raise ValueError(
                    "Cannot assign a descendant as manager because it would "
                    "create a management cycle."
                )

        old_manager_id = employee.manager_id
        employee.manager_id = new_manager_id

        try:
            self._validate()
        except ValueError:
            employee.manager_id = old_manager_id
            raise

    def _descendant_ids(self, employee_id: int) -> set[int]:
        descendants: set[int] = set()
        queue = deque([employee_id])

        while queue:
            current_id = queue.popleft()

            for report in self.direct_reports(current_id):
                if report.employee_id not in descendants:
                    descendants.add(report.employee_id)
                    queue.append(report.employee_id)

        return descendants

    def department_manager_report(self, department: str) -> list[dict[str, object]]:
        """
        Demonstrate a practical reporting pattern:
        employee information combined with immediate manager information.
        """
        result = []

        for employee in self.employees.values():
            if not employee.active or employee.department != department:
                continue

            manager = self.manager(employee.employee_id)

            result.append(
                {
                    "employee": employee.name,
                    "title": employee.title,
                    "manager": manager.name if manager else None,
                    "manager_title": manager.title if manager else None,
                }
            )

        return sorted(result, key=lambda row: str(row["employee"]))

    def salary_gap_to_manager(self, employee_id: int) -> Optional[float]:
        """Calculate manager salary minus employee salary."""
        employee = self._get_employee(employee_id)
        manager = self.manager(employee_id)

        if manager is None:
            return None

        return manager.salary - employee.salary


def print_manager_pairs(org: Organization) -> None:
    print("\nImmediate employee-manager relationships")
    print("-" * 50)

    for employee, manager in org.manager_employee_pairs():
        print(f"{employee.name:20} -> {manager.name}")


def print_levels(org: Organization) -> None:
    print("\nHierarchy depth")
    print("-" * 50)

    levels = org.hierarchy_levels()

    for employee_id, level in sorted(levels.items(), key=lambda item: (item[1], item[0])):
        employee = org.employees[employee_id]
        print(f"Level {level}: {employee.name}")


def print_common_manager_example(org: Organization) -> None:
    print("\nNearest common manager")
    print("-" * 50)

    first = "Priya"
    second = "Daniel"

    first_id = next(
        employee.employee_id
        for employee in org.employees.values()
        if employee.name == first
    )
    second_id = next(
        employee.employee_id
        for employee in org.employees.values()
        if employee.name == second
    )

    common = org.common_manager(first_id, second_id)

    print(
        f"Nearest common manager of {first} and {second}: "
        f"{common.name if common else 'None'}"
    )


def main() -> None:
    employees = [
        Employee(1, "Anita", "Chief Executive Officer", None, "Executive", 220000),
        Employee(2, "Rahul", "VP Engineering", 1, "Engineering", 170000),
        Employee(3, "Meera", "VP Operations", 1, "Operations", 165000),
        Employee(4, "Vikram", "Engineering Manager", 2, "Engineering", 125000),
        Employee(5, "Priya", "Engineering Manager", 2, "Engineering", 128000),
        Employee(6, "Daniel", "Operations Manager", 3, "Operations", 120000),
        Employee(7, "Arjun", "Senior Engineer", 4, "Engineering", 105000),
        Employee(8, "Sana", "Software Engineer", 4, "Engineering", 90000),
        Employee(9, "Karan", "Software Engineer", 5, "Engineering", 92000),
        Employee(10, "Leena", "Software Engineer", 5, "Engineering", 94000),
        Employee(11, "Rohit", "Operations Analyst", 6, "Operations", 76000),
        Employee(12, "Neha", "Operations Analyst", 6, "Operations", 78000),
        Employee(13, "Ishaan", "Intern", 7, "Engineering", 30000),
    ]

    organization = Organization(employees)

    print("SELF-JOIN EMPLOYEE-MANAGER HIERARCHY")
    print("=" * 50)

    print("\nOrganization chart")
    print("-" * 50)
    print(organization.organization_chart())

    print_manager_pairs(organization)
    print_levels(organization)

    print("\nDirect reports of Priya")
    print("-" * 50)

    priya_id = 5
    for employee in organization.direct_reports(priya_id):
        print(f"{employee.name} - {employee.title}")

    print_common_manager_example(organization)

    print("\nEngineering manager report")
    print("-" * 50)

    for row in organization.department_manager_report("Engineering"):
        print(
            f"{row['employee']:10} | "
            f"{row['title']:22} | "
            f"Manager: {row['manager']}"
        )

    print("\nManagement depth and salary relationship")
    print("-" * 50)

    for employee_id in [1, 5, 7, 13]:
        employee = organization.employees[employee_id]
        gap = organization.salary_gap_to_manager(employee_id)
        gap_text = "root employee" if gap is None else f"${gap:,.0f} manager salary gap"

        print(
            f"{employee.name:10} | depth={organization.management_span(employee_id)} "
            f"| {gap_text}"
        )

    print("\nDirect-report counts")
    print("-" * 50)

    report_counts = organization.count_direct_reports()

    for employee_id, count in sorted(report_counts.items()):
        employee = organization.employees[employee_id]

        if count:
            print(f"{employee.name:10} -> {count} direct report(s)")

    print("\nMoving an employee")
    print("-" * 50)

    organization.move_employee(8, 5)
    print("Sana moved from Vikram to Priya.")
    print(organization.organization_chart())

    print("\nCycle-protection demonstration")
    print("-" * 50)

    try:
        organization.move_employee(2, 7)
    except ValueError as exc:
        print(f"Rejected invalid hierarchy change: {exc}")

    print("\nMissing-manager validation demonstration")
    print("-" * 50)

    try:
        Organization(
            [
                Employee(
                    100,
                    "Invalid Employee",
                    "Developer",
                    999,
                    "Engineering",
                    50000,
                )
            ]
        )
    except ValueError as exc:
        print(f"Rejected invalid data: {exc}")

    print("\nSelf-management validation demonstration")
    print("-" * 50)

    try:
        Organization(
            [
                Employee(
                    101,
                    "Self Manager",
                    "Developer",
                    101,
                    "Engineering",
                    50000,
                )
            ]
        )
    except ValueError as exc:
        print(f"Rejected invalid data: {exc}")

    print("\nKey relational idea")
    print("-" * 50)
    print(
        "A SELF JOIN treats the employee table as two logical roles: "
        "one row represents the employee and another row represents that "
        "employee's manager. The relationship is established by matching "
        "employee.manager_id with manager.employee_id."
    )


if __name__ == "__main__":
    main()
