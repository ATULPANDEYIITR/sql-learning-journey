#!/usr/bin/env python3
"""
Database Views: CREATE VIEW, View Abstraction, and Reusable Queries.

Demonstrates:
- Creating and querying database views.
- Simple and complex views.
- Joins, aggregation, filtering, and subqueries.
- View abstraction and logical data independence.
- View metadata and dependency inspection.
- Updating simple views through INSTEAD OF triggers.
- Materialized-view concepts using cached query results.
- Validation, transactions, and error handling.

Runtime: Python 3.10+
Dependencies: Python standard library only.
"""

from __future__ import annotations

import sqlite3
import logging
from dataclasses import dataclass
from typing import Any, Optional
from contextlib import contextmanager


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

logger = logging.getLogger("database_views")


@dataclass(frozen=True)
class Employee:
    employee_id: int
    name: str
    department_id: int
    salary: float
    active: bool = True


@dataclass(frozen=True)
class Department:
    department_id: int
    name: str
    location: str


class ViewError(Exception):
    """Raised when a requested database view is unavailable."""


class ValidationError(Exception):
    """Raised when input violates domain rules."""


class Database:
    """Manages a relational database and reusable views."""

    def __init__(self, database: str = ":memory:"):
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.create_schema()

    @contextmanager
    def transaction(self):
        """Commit successful operations and roll back failures."""
        try:
            self.connection.execute("BEGIN")
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def create_schema(self) -> None:
        with self.transaction() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS departments (
                    department_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    location TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS employees (
                    employee_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    department_id INTEGER NOT NULL,
                    salary REAL NOT NULL CHECK (salary >= 0),
                    active INTEGER NOT NULL DEFAULT 1
                        CHECK (active IN (0, 1)),
                    FOREIGN KEY (department_id)
                        REFERENCES departments(department_id)
                );

                CREATE TABLE IF NOT EXISTS projects (
                    project_id INTEGER PRIMARY KEY,
                    project_name TEXT NOT NULL UNIQUE,
                    budget REAL NOT NULL CHECK (budget >= 0),
                    department_id INTEGER NOT NULL,
                    FOREIGN KEY (department_id)
                        REFERENCES departments(department_id)
                );

                CREATE TABLE IF NOT EXISTS assignments (
                    assignment_id INTEGER PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    hours REAL NOT NULL CHECK (hours >= 0),
                    FOREIGN KEY (employee_id)
                        REFERENCES employees(employee_id),
                    FOREIGN KEY (project_id)
                        REFERENCES projects(project_id),
                    UNIQUE(employee_id, project_id)
                );

                CREATE INDEX IF NOT EXISTS idx_employee_department
                    ON employees(department_id);

                CREATE INDEX IF NOT EXISTS idx_employee_active
                    ON employees(active);

                CREATE INDEX IF NOT EXISTS idx_assignment_project
                    ON assignments(project_id);
            """)

    def seed_data(self) -> None:
        """Insert representative organizational data."""
        with self.transaction() as conn:
            conn.executemany("""
                INSERT INTO departments
                    (department_id, name, location)
                VALUES (?, ?, ?)
            """, [
                (1, "Engineering", "Bangalore"),
                (2, "Finance", "Mumbai"),
                (3, "Research", "Hyderabad"),
                (4, "Operations", "Lucknow"),
            ])

            conn.executemany("""
                INSERT INTO employees
                    (employee_id, name, department_id, salary, active)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (101, "Aarav", 1, 95000, 1),
                (102, "Meera", 1, 110000, 1),
                (103, "Kabir", 2, 85000, 1),
                (104, "Ananya", 3, 120000, 1),
                (105, "Rohan", 2, 75000, 0),
                (106, "Ishita", 4, 80000, 1),
            ])

            conn.executemany("""
                INSERT INTO projects
                    (project_id, project_name, budget, department_id)
                VALUES (?, ?, ?, ?)
            """, [
                (201, "Cloud Platform", 500000, 1),
                (202, "Financial Analytics", 250000, 2),
                (203, "Research Intelligence", 700000, 3),
                (204, "Process Automation", 180000, 4),
            ])

            conn.executemany("""
                INSERT INTO assignments
                    (assignment_id, employee_id, project_id, hours)
                VALUES (?, ?, ?, ?)
            """, [
                (1, 101, 201, 120),
                (2, 102, 201, 160),
                (3, 103, 202, 90),
                (4, 104, 203, 180),
                (5, 106, 204, 110),
                (6, 101, 204, 40),
            ])

    def create_views(self) -> None:
        """Define reusable queries at the database level."""
        with self.transaction() as conn:
            conn.executescript("""
                DROP VIEW IF EXISTS employee_directory;
                DROP VIEW IF EXISTS department_statistics;
                DROP VIEW IF EXISTS project_workload;
                DROP VIEW IF EXISTS active_project_summary;
                DROP VIEW IF EXISTS employee_salary_view;

                -- Simple view: exposes selected employee attributes.
                CREATE VIEW employee_directory AS
                SELECT
                    employee_id,
                    name,
                    department_id
                FROM employees
                WHERE active = 1;

                -- Aggregation view: summarizes each department.
                CREATE VIEW department_statistics AS
                SELECT
                    d.department_id,
                    d.name AS department_name,
                    COUNT(e.employee_id) AS employee_count,
                    COALESCE(ROUND(AVG(e.salary), 2), 0)
                        AS average_salary,
                    COALESCE(SUM(e.salary), 0) AS payroll
                FROM departments d
                LEFT JOIN employees e
                    ON d.department_id = e.department_id
                    AND e.active = 1
                GROUP BY d.department_id, d.name;

                -- Join view: combines project and assignment information.
                CREATE VIEW project_workload AS
                SELECT
                    p.project_id,
                    p.project_name,
                    d.name AS department_name,
                    COUNT(a.assignment_id) AS assignment_count,
                    COALESCE(SUM(a.hours), 0) AS total_hours,
                    p.budget
                FROM projects p
                JOIN departments d
                    ON p.department_id = d.department_id
                LEFT JOIN assignments a
                    ON p.project_id = a.project_id
                GROUP BY
                    p.project_id,
                    p.project_name,
                    d.name,
                    p.budget;

                -- Multi-condition view.
                CREATE VIEW active_project_summary AS
                SELECT
                    project_id,
                    project_name,
                    department_name,
                    total_hours,
                    budget
                FROM project_workload
                WHERE total_hours > 100;

                -- Sensitive information is isolated in a separate view.
                CREATE VIEW employee_salary_view AS
                SELECT
                    employee_id,
                    name,
                    salary,
                    department_id
                FROM employees;
            """)

        logger.info("Database views created successfully.")

    def query_view(
        self,
        view_name: str,
        limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Read a registered view without exposing arbitrary SQL input."""
        allowed_views = {
            "employee_directory",
            "department_statistics",
            "project_workload",
            "active_project_summary",
            "employee_salary_view",
        }

        if view_name not in allowed_views:
            raise ViewError(f"View is not registered: {view_name}")

        if limit is not None and limit < 1:
            raise ValidationError("Limit must be positive.")

        sql = f"SELECT * FROM {view_name}"

        if limit is not None:
            sql += " LIMIT ?"
            cursor = self.connection.execute(sql, (limit,))
        else:
            cursor = self.connection.execute(sql)

        return [dict(row) for row in cursor.fetchall()]

    def search_employees(
        self,
        department_id: int,
        minimum_salary: float = 0
    ) -> list[dict[str, Any]]:
        """
        Reuse a view with additional parameterized filtering.

        Views themselves do not accept parameters. Filters are applied
        by the consuming SELECT statement.
        """
        if department_id <= 0 or minimum_salary < 0:
            raise ValidationError("Invalid search criteria.")

        cursor = self.connection.execute("""
            SELECT *
            FROM employee_salary_view
            WHERE department_id = ?
              AND salary >= ?
            ORDER BY salary DESC
        """, (department_id, minimum_salary))

        return [dict(row) for row in cursor.fetchall()]

    def create_updatable_view(self) -> None:
        """
        SQLite views are generally read-only.

        An INSTEAD OF trigger implements controlled updates.
        """
        with self.transaction() as conn:
            conn.executescript("""
                DROP TRIGGER IF EXISTS update_employee_directory;

                CREATE TRIGGER update_employee_directory
                INSTEAD OF UPDATE ON employee_directory
                BEGIN
                    UPDATE employees
                    SET
                        name = NEW.name,
                        department_id = NEW.department_id
                    WHERE employee_id = OLD.employee_id
                      AND active = 1;
                END;
            """)

    def update_employee_through_view(
        self,
        employee_id: int,
        new_name: str
    ) -> None:
        if not new_name.strip():
            raise ValidationError("Employee name cannot be empty.")

        with self.transaction() as conn:
            cursor = conn.execute("""
                UPDATE employee_directory
                SET name = ?
                WHERE employee_id = ?
            """, (new_name.strip(), employee_id))

            if cursor.rowcount == 0:
                raise ValidationError(
                    "Employee not found or not eligible for update."
                )

    def inspect_views(self) -> list[dict[str, Any]]:
        """Inspect SQLite catalog metadata."""
        cursor = self.connection.execute("""
            SELECT name, sql
            FROM sqlite_master
            WHERE type = 'view'
            ORDER BY name
        """)

        return [dict(row) for row in cursor.fetchall()]

    def inspect_view_columns(
        self,
        view_name: str
    ) -> list[dict[str, Any]]:
        allowed_views = {
            "employee_directory",
            "department_statistics",
            "project_workload",
            "active_project_summary",
            "employee_salary_view",
        }

        if view_name not in allowed_views:
            raise ViewError("Unknown view.")

        cursor = self.connection.execute(
            f"PRAGMA table_info({view_name})"
        )

        return [dict(row) for row in cursor.fetchall()]

    def explain_query(self, view_name: str) -> list[str]:
        """Inspect the execution plan for a view query."""
        if view_name not in {
            "employee_directory",
            "department_statistics",
            "project_workload",
            "active_project_summary",
            "employee_salary_view",
        }:
            raise ViewError("Unknown view.")

        cursor = self.connection.execute(
            f"EXPLAIN QUERY PLAN SELECT * FROM {view_name}"
        )

        return [str(tuple(row)) for row in cursor.fetchall()]

    def materialize_department_statistics(self) -> list[dict[str, Any]]:
        """
        Simulate a materialized view using a temporary result table.

        Unlike a regular view, the cached result does not automatically
        reflect subsequent changes to the underlying tables.
        """
        with self.transaction() as conn:
            conn.execute("""
                CREATE TEMP TABLE IF NOT EXISTS department_cache (
                    department_id INTEGER PRIMARY KEY,
                    department_name TEXT NOT NULL,
                    employee_count INTEGER NOT NULL,
                    average_salary REAL NOT NULL,
                    payroll REAL NOT NULL
                )
            """)

            conn.execute("DELETE FROM department_cache")

            conn.execute("""
                INSERT INTO department_cache
                SELECT
                    department_id,
                    department_name,
                    employee_count,
                    average_salary,
                    payroll
                FROM department_statistics
            """)

            cursor = conn.execute("""
                SELECT *
                FROM department_cache
                ORDER BY department_id
            """)

            return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        self.connection.close()


def demonstrate() -> None:
    database = Database()

    try:
        database.seed_data()
        database.create_views()

        print("\n1. Employee Directory")
        for employee in database.query_view("employee_directory"):
            print(employee)

        print("\n2. Department Statistics")
        for department in database.query_view(
            "department_statistics"
        ):
            print(department)

        print("\n3. Project Workload")
        for project in database.query_view("project_workload"):
            print(project)

        print("\n4. Filtered View")
        for project in database.query_view(
            "active_project_summary"
        ):
            print(project)

        print("\n5. Parameterized View Consumption")
        for employee in database.search_employees(1, 100000):
            print(employee)

        print("\n6. View Metadata")
        for view in database.inspect_views():
            print(view["name"])

        print("\n7. View Column Metadata")
        for column in database.inspect_view_columns(
            "department_statistics"
        ):
            print(column["name"], column["type"])

        print("\n8. Execution Plan")
        for line in database.explain_query("project_workload"):
            print(line)

        print("\n9. Controlled Update Through View")
        database.create_updatable_view()
        database.update_employee_through_view(101, "Aarav Sharma")
        print(database.query_view("employee_directory", limit=2))

        print("\n10. Materialized Result Simulation")
        for row in database.materialize_department_statistics():
            print(row)

        print("\n11. Validation")
        try:
            database.query_view("unknown_view")
        except ViewError as error:
            print("Expected error:", error)

        try:
            database.search_employees(-1, 50000)
        except ValidationError as error:
            print("Expected error:", error)

        # Basic correctness assertions.
        departments = database.query_view("department_statistics")
        assert len(departments) == 4

        engineering = next(
            item for item in departments
            if item["department_id"] == 1
        )

        assert engineering["employee_count"] == 2
        assert engineering["payroll"] == 205000

        assert len(database.query_view("employee_directory")) == 5

        logger.info("All validation assertions passed.")

    except sqlite3.Error:
        logger.exception("Database operation failed.")
        raise

    finally:
        database.close()


if __name__ == "__main__":
    demonstrate()
