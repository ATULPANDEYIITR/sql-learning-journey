#!/usr/bin/env python3
"""
INDEX FUNDAMENTALS
Why indexes exist, B-tree concepts, and index lookup.

Demonstrates:
- Sequential table scanning
- B-tree insertion and lookup
- Index construction
- Indexed record retrieval
- Range queries
- Duplicate-key handling
- Index maintenance after updates
- Performance comparison
- Validation and integrity checks

Python 3.10+
No external dependencies.
"""

from __future__ import annotations

import random
import time
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True)
class Employee:
    employee_id: int
    name: str
    department: str
    salary: float


class BTreeNode:
    def __init__(self, leaf: bool = True):
        self.leaf = leaf
        self.keys: list[int] = []
        self.children: list[BTreeNode] = []


class BTree:
    """B-tree supporting unique integer keys and point lookup."""

    def __init__(self, minimum_degree: int = 3):
        if minimum_degree < 2:
            raise ValueError("Minimum degree must be at least 2.")

        self.degree = minimum_degree
        self.root = BTreeNode()

    def search(self, key: int) -> bool:
        if not isinstance(key, int) or isinstance(key, bool):
            raise TypeError("B-tree keys must be integers.")

        node = self.root

        while True:
            i = bisect_left(node.keys, key)

            if i < len(node.keys) and node.keys[i] == key:
                return True

            if node.leaf:
                return False

            node = node.children[i]

    def insert(self, key: int) -> None:
        if not isinstance(key, int) or isinstance(key, bool):
            raise TypeError("B-tree keys must be integers.")

        if self.search(key):
            raise ValueError(f"Duplicate key: {key}")

        root = self.root

        if len(root.keys) == 2 * self.degree - 1:
            new_root = BTreeNode(leaf=False)
            new_root.children.append(root)
            self.root = new_root
            self._split_child(new_root, 0)
            self._insert_non_full(new_root, key)
        else:
            self._insert_non_full(root, key)

    def _split_child(self, parent: BTreeNode, index: int) -> None:
        degree = self.degree
        child = parent.children[index]
        sibling = BTreeNode(leaf=child.leaf)

        median = child.keys[degree - 1]

        sibling.keys = child.keys[degree:]
        child.keys = child.keys[:degree - 1]

        if not child.leaf:
            sibling.children = child.children[degree:]
            child.children = child.children[:degree]

        parent.keys.insert(index, median)
        parent.children.insert(index + 1, sibling)

    def _insert_non_full(self, node: BTreeNode, key: int) -> None:
        i = len(node.keys) - 1

        if node.leaf:
            node.keys.append(key)

            while i >= 0 and node.keys[i] > key:
                node.keys[i + 1] = node.keys[i]
                i -= 1

            node.keys[i + 1] = key
            return

        while i >= 0 and key < node.keys[i]:
            i -= 1

        i += 1

        if len(node.children[i].keys) == 2 * self.degree - 1:
            self._split_child(node, i)

            if key > node.keys[i]:
                i += 1

        self._insert_non_full(node.children[i], key)

    def traverse(self) -> list[int]:
        result: list[int] = []

        def visit(node: BTreeNode) -> None:
            for i, key in enumerate(node.keys):
                if not node.leaf:
                    visit(node.children[i])

                result.append(key)

            if not node.leaf:
                visit(node.children[-1])

        visit(self.root)
        return result

    def range_search(self, lower: int, upper: int) -> list[int]:
        if lower > upper:
            raise ValueError("Lower bound cannot exceed upper bound.")

        return [
            key for key in self.traverse()
            if lower <= key <= upper
        ]

    def validate(self) -> bool:
        """Check ordering, child counts, and B-tree occupancy."""

        def check(
            node: BTreeNode,
            lower: int | None,
            upper: int | None,
            is_root: bool
        ) -> int:

            if node.keys != sorted(node.keys):
                raise AssertionError("Node keys are not sorted.")

            if len(node.keys) != len(set(node.keys)):
                raise AssertionError("Duplicate keys in a node.")

            if len(node.keys) > 2 * self.degree - 1:
                raise AssertionError("Node exceeds maximum capacity.")

            if not is_root and len(node.keys) < self.degree - 1:
                raise AssertionError("Node has insufficient keys.")

            if is_root and not node.leaf and len(node.keys) < 1:
                raise AssertionError("Invalid empty internal root.")

            for key in node.keys:
                if lower is not None and key <= lower:
                    raise AssertionError("Lower ordering violation.")

                if upper is not None and key >= upper:
                    raise AssertionError("Upper ordering violation.")

            if node.leaf:
                if node.children:
                    raise AssertionError("Leaf cannot have children.")
                return 1

            if len(node.children) != len(node.keys) + 1:
                raise AssertionError("Invalid child count.")

            heights = []

            for i, child in enumerate(node.children):
                child_lower = lower if i == 0 else node.keys[i - 1]
                child_upper = upper if i == len(node.keys) else node.keys[i]

                heights.append(
                    check(child, child_lower, child_upper, False)
                )

            if len(set(heights)) != 1:
                raise AssertionError("Leaves have unequal depths.")

            return heights[0] + 1

        check(self.root, None, None, True)
        return True


class EmployeeTable:
    """Simulates a table and a separately maintained B-tree index."""

    def __init__(self):
        self.rows: dict[int, Employee] = {}
        self.primary_index = BTree(minimum_degree=4)

    def insert(self, employee: Employee) -> None:
        self._validate(employee)

        if employee.employee_id in self.rows:
            raise ValueError("Employee already exists.")

        self.primary_index.insert(employee.employee_id)
        self.rows[employee.employee_id] = employee

    def _validate(self, employee: Employee) -> None:
        if employee.employee_id <= 0:
            raise ValueError("Employee ID must be positive.")

        if not employee.name.strip():
            raise ValueError("Employee name cannot be empty.")

        if not employee.department.strip():
            raise ValueError("Department cannot be empty.")

        if employee.salary < 0:
            raise ValueError("Salary cannot be negative.")

    def sequential_lookup(self, employee_id: int) -> Employee | None:
        for employee in self.rows.values():
            if employee.employee_id == employee_id:
                return employee

        return None

    def indexed_lookup(self, employee_id: int) -> Employee | None:
        if not self.primary_index.search(employee_id):
            return None

        return self.rows.get(employee_id)

    def update_salary(self, employee_id: int, salary: float) -> None:
        if salary < 0:
            raise ValueError("Salary cannot be negative.")

        employee = self.indexed_lookup(employee_id)

        if employee is None:
            raise KeyError("Employee does not exist.")

        self.rows[employee_id] = Employee(
            employee.employee_id,
            employee.name,
            employee.department,
            salary
        )

    def delete(self, employee_id: int) -> None:
        """
        This demonstration keeps the index append-only.
        Deletion is deliberately rejected rather than leaving
        a stale index entry.
        """
        raise NotImplementedError(
            "Use a deletion-capable production index implementation."
        )

    def range_lookup(self, lower: int, upper: int) -> list[Employee]:
        keys = self.primary_index.range_search(lower, upper)
        return [self.rows[key] for key in keys]

    def verify_integrity(self) -> bool:
        indexed_keys = self.primary_index.traverse()
        table_keys = sorted(self.rows)

        if indexed_keys != table_keys:
            raise AssertionError("Table and index are inconsistent.")

        return self.primary_index.validate()


def benchmark(table: EmployeeTable, repetitions: int = 5000) -> None:
    """Compare lookup strategies using the same existing records."""

    if not table.rows:
        raise ValueError("Cannot benchmark an empty table.")

    if repetitions <= 0:
        raise ValueError("Repetitions must be positive.")

    targets = [
        random.choice(list(table.rows))
        for _ in range(repetitions)
    ]

    start = time.perf_counter()

    for key in targets:
        table.sequential_lookup(key)

    sequential_time = time.perf_counter() - start

    start = time.perf_counter()

    for key in targets:
        table.indexed_lookup(key)

    indexed_time = time.perf_counter() - start

    print("\nPERFORMANCE COMPARISON")
    print(f"Sequential scan: {sequential_time:.6f} seconds")
    print(f"B-tree index:    {indexed_time:.6f} seconds")

    if indexed_time > 0:
        print(f"Observed speed ratio: {sequential_time / indexed_time:.2f}x")


def main() -> None:
    random.seed(42)

    table = EmployeeTable()

    departments = [
        "Engineering",
        "Security",
        "Research",
        "Operations",
        "Finance"
    ]

    # Create realistic employee records.
    for employee_id in range(1, 10001):
        table.insert(
            Employee(
                employee_id=employee_id,
                name=f"Employee {employee_id}",
                department=random.choice(departments),
                salary=40000 + random.randint(0, 100000)
            )
        )

    print("INDEX FUNDAMENTALS")
    print("=" * 55)

    print(f"Total records: {len(table.rows)}")
    print(f"Index entries: {len(table.primary_index.traverse())}")

    # Sequential lookup.
    print("\n1. SEQUENTIAL LOOKUP")
    employee = table.sequential_lookup(7500)
    print(employee)

    # B-tree indexed lookup.
    print("\n2. INDEXED LOOKUP")
    employee = table.indexed_lookup(7500)
    print(employee)

    # Missing record.
    print("\n3. MISSING RECORD")
    print(table.indexed_lookup(20000))

    # Range query.
    print("\n4. RANGE LOOKUP")
    employees = table.range_lookup(100, 110)

    for employee in employees:
        print(employee.employee_id, employee.department)

    # Update a non-indexed column.
    print("\n5. UPDATE")
    table.update_salary(7500, 125000.0)
    print(table.indexed_lookup(7500))

    # Duplicate insertion.
    print("\n6. DUPLICATE KEY VALIDATION")

    try:
        table.insert(
            Employee(7500, "Duplicate", "Research", 50000)
        )
    except ValueError as error:
        print("Rejected:", error)

    # Integrity validation.
    print("\n7. INDEX INTEGRITY")
    print("Valid:", table.verify_integrity())

    # B-tree ordering.
    print("\n8. B-TREE ORDERING")
    keys = table.primary_index.traverse()
    print("First five keys:", keys[:5])
    print("Last five keys:", keys[-5:])

    # Performance comparison.
    benchmark(table)

    # Edge cases.
    print("\n9. EDGE CASES")

    try:
        table.primary_index.insert(0)
        print("Zero inserted.")
    except (TypeError, ValueError) as error:
        print("Error:", error)

    try:
        table.range_lookup(200, 100)
    except ValueError as error:
        print("Invalid range:", error)

    print("\nExecution completed successfully.")


if __name__ == "__main__":
    main()
