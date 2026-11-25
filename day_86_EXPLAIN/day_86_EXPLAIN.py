#!/usr/bin/env python3
"""
SQL EXPLAIN: Execution Plans, Cost Estimates, and Scan Types

Demonstrates:
- SQL execution-plan inspection
- Sequential scans and index scans
- Selectivity and cardinality estimates
- Estimated versus actual execution behavior
- Query-plan comparison before and after indexing
- SQLite EXPLAIN QUERY PLAN
- Basic cost modeling
- Plan diagnostics and validation

Requires Python 3.10+.
Uses only the Python standard library.
"""

from __future__ import annotations

import json
import math
import sqlite3
import statistics
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any


DATABASE = ":memory:"
OUTPUT_FILE = Path("execution_plan_report.json")


class ScanType(Enum):
    SEQUENTIAL = "Sequential Scan"
    INDEX = "Index Scan"
    INDEX_ONLY = "Index Only Scan"
    BITMAP = "Bitmap Heap Scan"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class TableStatistics:
    table_name: str
    rows: int
    pages: int
    average_row_width: int
    distinct_values: int


@dataclass(frozen=True)
class CostEstimate:
    startup_cost: float
    total_cost: float
    estimated_rows: int
    scan_type: ScanType


@dataclass
class QueryMeasurement:
    query_name: str
    execution_time_ms: float
    returned_rows: int
    plan: list[str]


class DatabaseLab:

    def __init__(self) -> None:
        self.connection = sqlite3.connect(DATABASE)
        self.connection.row_factory = sqlite3.Row

    def create_schema(self) -> None:
        self.connection.execute("""
            CREATE TABLE employees (
                employee_id INTEGER PRIMARY KEY,
                employee_name TEXT NOT NULL,
                department TEXT NOT NULL,
                salary REAL NOT NULL CHECK (salary >= 0),
                location TEXT NOT NULL,
                active INTEGER NOT NULL CHECK (active IN (0, 1))
            )
        """)

        self.connection.execute("""
            CREATE TABLE departments (
                department_id INTEGER PRIMARY KEY,
                department_name TEXT NOT NULL UNIQUE,
                budget REAL NOT NULL CHECK (budget >= 0)
            )
        """)

        self.connection.execute("""
            CREATE TABLE employee_audit (
                audit_id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                operation TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.connection.executemany(
            """
            INSERT INTO departments
                (department_id, department_name, budget)
            VALUES (?, ?, ?)
            """,
            [
                (1, "Engineering", 500000),
                (2, "Security", 250000),
                (3, "Research", 400000),
                (4, "Operations", 300000),
            ],
        )

        departments = [
            "Engineering",
            "Security",
            "Research",
            "Operations",
        ]

        locations = ["Lucknow", "Delhi", "Mumbai", "Pune"]

        employees = [
            (
                employee_id,
                f"Employee_{employee_id}",
                departments[employee_id % len(departments)],
                30000 + (employee_id % 20) * 5000,
                locations[employee_id % len(locations)],
                1 if employee_id % 5 else 0,
            )
            for employee_id in range(1, 10001)
        ]

        self.connection.executemany(
            """
            INSERT INTO employees
                (employee_id, employee_name, department,
                 salary, location, active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            employees,
        )

        self.connection.commit()

    def create_indexes(self) -> None:
        self.connection.execute("""
            CREATE INDEX idx_employees_department
            ON employees(department)
        """)

        self.connection.execute("""
            CREATE INDEX idx_employees_salary
            ON employees(salary)
        """)

        self.connection.execute("""
            CREATE INDEX idx_employees_department_salary
            ON employees(department, salary)
        """)

        self.connection.execute("""
            CREATE INDEX idx_employees_active_location
            ON employees(active, location)
        """)

        self.connection.commit()

    def drop_indexes(self) -> None:
        for index in [
            "idx_employees_department",
            "idx_employees_salary",
            "idx_employees_department_salary",
            "idx_employees_active_location",
        ]:
            self.connection.execute(f"DROP INDEX IF EXISTS {index}")

        self.connection.commit()

    def explain(self, query: str, parameters: tuple = ()) -> list[str]:
        if not query.lstrip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are permitted.")

        cursor = self.connection.execute(
            "EXPLAIN QUERY PLAN " + query,
            parameters,
        )

        return [
            f"{row['detail']}"
            for row in cursor.fetchall()
        ]

    def execute_measured(
        self,
        name: str,
        query: str,
        parameters: tuple = (),
    ) -> QueryMeasurement:
        plan = self.explain(query, parameters)

        start = time.perf_counter()

        cursor = self.connection.execute(query, parameters)
        results = cursor.fetchall()

        elapsed = (time.perf_counter() - start) * 1000

        return QueryMeasurement(
            query_name=name,
            execution_time_ms=round(elapsed, 4),
            returned_rows=len(results),
            plan=plan,
        )

    def get_statistics(self) -> TableStatistics:
        rows = self.connection.execute(
            "SELECT COUNT(*) FROM employees"
        ).fetchone()[0]

        distinct_departments = self.connection.execute(
            "SELECT COUNT(DISTINCT department) FROM employees"
        ).fetchone()[0]

        # SQLite does not expose PostgreSQL's physical page statistics
        # through this interface. This is an illustrative page estimate.
        average_width = 80
        page_size = 4096
        estimated_pages = math.ceil(
            rows * average_width / page_size
        )

        return TableStatistics(
            table_name="employees",
            rows=rows,
            pages=estimated_pages,
            average_row_width=average_width,
            distinct_values=distinct_departments,
        )

    def close(self) -> None:
        self.connection.close()


class CostModel:
    """
    Simplified educational cost model.

    These values are illustrative, not PostgreSQL planner costs.
    """

    SEQUENTIAL_PAGE_COST = 1.0
    RANDOM_PAGE_COST = 4.0
    CPU_TUPLE_COST = 0.01
    INDEX_ENTRY_COST = 0.02

    @classmethod
    def estimate(
        cls,
        statistics: TableStatistics,
        selectivity: float,
        scan_type: ScanType,
    ) -> CostEstimate:

        if not 0 <= selectivity <= 1:
            raise ValueError("Selectivity must be between 0 and 1.")

        estimated_rows = round(
            statistics.rows * selectivity
        )

        if scan_type == ScanType.SEQUENTIAL:
            startup = 0.0
            total = (
                statistics.pages * cls.SEQUENTIAL_PAGE_COST
                + statistics.rows * cls.CPU_TUPLE_COST
            )

        elif scan_type in (ScanType.INDEX, ScanType.INDEX_ONLY):
            startup = 1.0

            total = (
                math.log2(max(statistics.rows, 2))
                + estimated_rows * cls.INDEX_ENTRY_COST
                + estimated_rows * cls.RANDOM_PAGE_COST
            )

            if scan_type == ScanType.INDEX_ONLY:
                total *= 0.35

        elif scan_type == ScanType.BITMAP:
            startup = 2.0
            total = (
                statistics.pages * selectivity
                + estimated_rows * cls.RANDOM_PAGE_COST * 0.4
            )

        else:
            raise ValueError("Unsupported scan type.")

        return CostEstimate(
            startup_cost=round(startup, 2),
            total_cost=round(total, 2),
            estimated_rows=estimated_rows,
            scan_type=scan_type,
        )

    @classmethod
    def choose_plan(
        cls,
        statistics: TableStatistics,
        selectivity: float,
    ) -> CostEstimate:

        candidates = [
            cls.estimate(
                statistics,
                selectivity,
                scan_type,
            )
            for scan_type in (
                ScanType.SEQUENTIAL,
                ScanType.INDEX,
                ScanType.BITMAP,
            )
        ]

        return min(candidates, key=lambda item: item.total_cost)


class PlanAnalyzer:

    @staticmethod
    def classify(plan: list[str]) -> set[ScanType]:
        detected = set()

        for line in plan:
            normalized = line.upper()

            if "SCAN" in normalized and "USING INDEX" not in normalized:
                detected.add(ScanType.SEQUENTIAL)

            if "USING INDEX" in normalized:
                detected.add(ScanType.INDEX)

            if "USING COVERING INDEX" in normalized:
                detected.add(ScanType.INDEX_ONLY)

        return detected or {ScanType.UNKNOWN}

    @staticmethod
    def print_measurement(measurement: QueryMeasurement) -> None:
        print(f"\nQuery: {measurement.query_name}")
        print(f"Execution time: {measurement.execution_time_ms} ms")
        print(f"Returned rows: {measurement.returned_rows}")
        print("Execution plan:")

        for step in measurement.plan:
            print(f"  {step}")

        print(
            "Detected scan types:",
            ", ".join(
                scan.value
                for scan in PlanAnalyzer.classify(
                    measurement.plan
                )
            ),
        )


def demonstrate() -> None:
    database = DatabaseLab()

    try:
        database.create_schema()

        statistics = database.get_statistics()

        print("=" * 65)
        print("SQL EXECUTION PLAN ANALYSIS")
        print("=" * 65)

        print("\nTable statistics:")
        print(json.dumps(asdict(statistics), indent=2))

        queries = [
            (
                "Department filtering",
                """
                SELECT employee_id, employee_name
                FROM employees
                WHERE department = ?
                """,
                ("Engineering",),
            ),
            (
                "Salary range",
                """
                SELECT employee_id, salary
                FROM employees
                WHERE salary BETWEEN ? AND ?
                """,
                (50000, 80000),
            ),
            (
                "Multiple predicates",
                """
                SELECT employee_id, employee_name
                FROM employees
                WHERE active = ?
                  AND location = ?
                """,
                (1, "Lucknow"),
            ),
            (
                "Full table retrieval",
                """
                SELECT employee_id, employee_name
                FROM employees
                """,
                (),
            ),
        ]

        print("\n--- Plans before indexing ---")

        before = []

        for name, query, parameters in queries:
            result = database.execute_measured(
                name,
                query,
                parameters,
            )
            before.append(result)
            PlanAnalyzer.print_measurement(result)

        database.create_indexes()

        print("\n--- Plans after indexing ---")

        after = []

        for name, query, parameters in queries:
            result = database.execute_measured(
                name,
                query,
                parameters,
            )
            after.append(result)
            PlanAnalyzer.print_measurement(result)

        print("\n--- Illustrative cost estimates ---")

        for selectivity in (0.001, 0.05, 0.25, 0.75, 1.0):
            selected = CostModel.choose_plan(
                statistics,
                selectivity,
            )

            print(
                f"Selectivity={selectivity:.1%}, "
                f"Rows={selected.estimated_rows}, "
                f"Selected={selected.scan_type.value}, "
                f"Cost={selected.total_cost}"
            )

        report = {
            "statistics": asdict(statistics),
            "before_indexing": [
                asdict(item) for item in before
            ],
            "after_indexing": [
                asdict(item) for item in after
            ],
        }

        OUTPUT_FILE.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        print(f"\nReport saved to: {OUTPUT_FILE.resolve()}")

        assert statistics.rows == 10000
        assert len(before) == len(after) == 4

        print("\nAll validation checks passed.")

    finally:
        database.close()


if __name__ == "__main__":
    demonstrate()
