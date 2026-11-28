from __future__ import annotations

import random
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Employee:
    employee_id: int
    name: str
    department_id: int
    salary: float
    active: bool


@dataclass(frozen=True)
class Department:
    department_id: int
    name: str
    location: str


@dataclass
class QueryMetrics:
    rows_scanned: int = 0
    rows_returned: int = 0
    predicate_evaluations: int = 0
    join_comparisons: int = 0
    elapsed_ms: float = 0.0


class QueryEngine:
    """A small relational query engine demonstrating optimization techniques."""

    def __init__(self, employees: list[Employee],
                 departments: list[Department]):
        self.employees = employees
        self.departments = departments
        self.metrics = QueryMetrics()

        # Hash indexes reduce repeated linear searches.
        self.department_index = {
            department.department_id: department
            for department in departments
        }

        self.employee_department_index: dict[int, list[Employee]] = {}
        for employee in employees:
            self.employee_department_index.setdefault(
                employee.department_id, []
            ).append(employee)

    def reset_metrics(self):
        self.metrics = QueryMetrics()

    def execute(self, operation: Callable[[], list[Any]]) -> list[Any]:
        self.reset_metrics()
        start = time.perf_counter()
        result = operation()
        self.metrics.rows_returned = len(result)
        self.metrics.elapsed_ms = (
            time.perf_counter() - start
        ) * 1000
        return result

    def scan(self, predicate=None):
        result = []
        for employee in self.employees:
            self.metrics.rows_scanned += 1
            if predicate is not None:
                self.metrics.predicate_evaluations += 1
                if not predicate(employee):
                    continue
            result.append(employee)
        return result

    def unoptimized_query(self, minimum_salary: float,
                          location: str):
        """Filter after constructing the complete join."""
        joined = []

        for employee in self.employees:
            for department in self.departments:
                self.metrics.join_comparisons += 1
                if employee.department_id == department.department_id:
                    joined.append((employee, department))

        result = []
        for employee, department in joined:
            self.metrics.predicate_evaluations += 1
            if (
                employee.active
                and employee.salary >= minimum_salary
                and department.location == location
            ):
                result.append((employee, department))

        self.metrics.rows_scanned = (
            len(self.employees) + len(self.departments)
        )
        return result

    def optimized_query(self, minimum_salary: float,
                        location: str):
        """Push selective predicates before joining and use a hash join."""
        filtered_employees = []

        for employee in self.employees:
            self.metrics.rows_scanned += 1
            self.metrics.predicate_evaluations += 1

            if not employee.active:
                continue
            if employee.salary < minimum_salary:
                continue

            filtered_employees.append(employee)

        filtered_departments = [
            department
            for department in self.departments
            if department.location == location
        ]

        department_lookup = {
            department.department_id: department
            for department in filtered_departments
        }

        result = []

        for employee in filtered_employees:
            self.metrics.join_comparisons += 1
            department = department_lookup.get(employee.department_id)

            if department is not None:
                result.append((employee, department))

        return result

    def indexed_query(self, minimum_salary: float, location: str):
        """Use prebuilt indexes to avoid scanning unrelated departments."""
        matching_department_ids = {
            department.department_id
            for department in self.departments
            if department.location == location
        }

        result = []

        for department_id in matching_department_ids:
            for employee in self.employee_department_index.get(
                department_id, []
            ):
                self.metrics.rows_scanned += 1
                self.metrics.predicate_evaluations += 1

                if employee.active and employee.salary >= minimum_salary:
                    result.append(
                        (employee, self.department_index[department_id])
                    )

        return result


def demonstrate_query_optimization():
    random.seed(42)

    locations = ["Lucknow", "Delhi", "Mumbai", "Pune", "Bengaluru"]

    departments = [
        Department(i, f"Department-{i}", locations[i % len(locations)])
        for i in range(1, 101)
    ]

    employees = [
        Employee(
            employee_id=i,
            name=f"Employee-{i}",
            department_id=random.randint(1, 100),
            salary=random.uniform(20000, 150000),
            active=random.random() > 0.2
        )
        for i in range(1, 10001)
    ]

    engine = QueryEngine(employees, departments)

    queries = [
        ("Unoptimized", engine.unoptimized_query),
        ("Predicate Pushdown", engine.optimized_query),
        ("Indexed Join", engine.indexed_query),
    ]

    expected = None

    for name, query in queries:
        result = engine.execute(
            lambda: query(75000, "Lucknow")
        )

        # Sorting ensures execution-plan differences do not affect comparison.
        result_ids = sorted(
            employee.employee_id for employee, _ in result
        )

        if expected is None:
            expected = result_ids
        else:
            assert result_ids == expected, (
                f"Incorrect results from {name}"
            )

        print(f"\n{name}")
        print(f"Returned rows: {engine.metrics.rows_returned}")
        print(f"Rows scanned: {engine.metrics.rows_scanned}")
        print(
            "Predicate evaluations:",
            engine.metrics.predicate_evaluations
        )
        print("Join operations:", engine.metrics.join_comparisons)
        print(f"Execution time: {engine.metrics.elapsed_ms:.3f} ms")


def demonstrate_sqlite_optimization():
    """Use SQLite's query planner to inspect real relational optimization."""
    connection = sqlite3.connect(":memory:")

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executescript("""
            CREATE TABLE departments (
                department_id INTEGER PRIMARY KEY,
                department_name TEXT NOT NULL,
                location TEXT NOT NULL
            );

            CREATE TABLE employees (
                employee_id INTEGER PRIMARY KEY,
                employee_name TEXT NOT NULL,
                department_id INTEGER NOT NULL,
                salary REAL NOT NULL CHECK (salary >= 0),
                active INTEGER NOT NULL CHECK (active IN (0, 1)),
                FOREIGN KEY (department_id)
                    REFERENCES departments(department_id)
            );

            CREATE INDEX idx_employees_department
                ON employees(department_id);

            CREATE INDEX idx_employees_active_salary
                ON employees(active, salary);

            CREATE INDEX idx_departments_location
                ON departments(location);
        """)

        with connection:
            connection.executemany(
                "INSERT INTO departments VALUES (?, ?, ?)",
                [
                    (1, "Engineering", "Lucknow"),
                    (2, "Research", "Delhi"),
                    (3, "Security", "Lucknow"),
                    (4, "Finance", "Mumbai")
                ]
            )

            connection.executemany(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                [
                    (1, "Amit", 1, 95000, 1),
                    (2, "Neha", 2, 85000, 1),
                    (3, "Ravi", 3, 60000, 1),
                    (4, "Priya", 1, 110000, 0),
                    (5, "Karan", 4, 125000, 1),
                    (6, "Meera", 3, 90000, 1)
                ]
            )

        sql = """
            SELECT e.employee_id,
                   e.employee_name,
                   e.salary,
                   d.department_name
            FROM employees AS e
            JOIN departments AS d
              ON d.department_id = e.department_id
            WHERE e.active = 1
              AND e.salary >= ?
              AND d.location = ?
            ORDER BY e.salary DESC;
        """

        print("\nOptimized SQL results:")
        for row in connection.execute(sql, (75000, "Lucknow")):
            print(row)

        print("\nSQLite execution plan:")
        for row in connection.execute(
            "EXPLAIN QUERY PLAN " + sql,
            (75000, "Lucknow")
        ):
            print(row)

    finally:
        connection.close()


def demonstrate_predicate_selectivity():
    """Estimate how predicate order affects intermediate result sizes."""
    total_rows = 1_000_000

    predicates = {
        "active = true": 0.80,
        "salary >= 100000": 0.10,
        "location = Lucknow": 0.05
    }

    current = total_rows
    print("\nPredicate selectivity:")

    # Applying the most selective predicate first minimizes
    # intermediate rows in a materialized filtering pipeline.
    for name, selectivity in sorted(
        predicates.items(), key=lambda item: item[1]
    ):
        current = int(current * selectivity)
        print(f"{name}: approximately {current:,} rows")


if __name__ == "__main__":
    demonstrate_query_optimization()
    demonstrate_sqlite_optimization()
    demonstrate_predicate_selectivity()
