#!/usr/bin/env python3
"""
Subqueries Fundamentals

A self-contained progression from basic subquery concepts to practical,
correlated, scalar, single-row, multi-row, and table-subquery operations.

The executable examples use Python's standard-library sqlite3 module so that
the SQL statements demonstrate real database behavior without external
dependencies.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Employee:
    employee_id: int
    name: str
    department_id: int
    salary: float


def create_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            salary REAL NOT NULL CHECK (salary > 0),
            FOREIGN KEY (department_id) REFERENCES departments(department_id)
        );

        CREATE TABLE projects (
            project_id INTEGER PRIMARY KEY,
            project_name TEXT NOT NULL UNIQUE,
            department_id INTEGER NOT NULL,
            budget REAL NOT NULL CHECK (budget > 0),
            FOREIGN KEY (department_id) REFERENCES departments(department_id)
        );

        CREATE TABLE employee_projects (
            employee_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            hours REAL NOT NULL CHECK (hours >= 0),
            PRIMARY KEY (employee_id, project_id),
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        );
        """
    )


def seed_data(connection: sqlite3.Connection) -> None:
    departments = [
        (10, "Engineering"),
        (20, "Finance"),
        (30, "Operations"),
        (40, "Security"),
        (50, "Research"),
    ]

    employees = [
        (101, "Aarav", 10, 92000),
        (102, "Diya", 10, 108000),
        (103, "Kabir", 10, 125000),
        (104, "Meera", 20, 85000),
        (105, "Rohan", 20, 97000),
        (106, "Ishita", 30, 76000),
        (107, "Vihaan", 30, 89000),
        (108, "Anaya", 40, 118000),
        (109, "Arjun", 40, 131000),
        (110, "Sara", 50, 112000),
    ]

    projects = [
        (201, "Payment Platform", 10, 900000),
        (202, "Cloud Migration", 10, 650000),
        (203, "Risk Analytics", 20, 480000),
        (204, "Supply Optimization", 30, 550000),
        (205, "Threat Detection", 40, 800000),
        (206, "Quantum Research", 50, 1200000),
    ]

    employee_projects = [
        (101, 201, 120),
        (101, 202, 80),
        (102, 201, 160),
        (103, 201, 180),
        (103, 202, 90),
        (104, 203, 150),
        (105, 203, 175),
        (106, 204, 120),
        (107, 204, 190),
        (108, 205, 170),
        (109, 205, 210),
        (110, 206, 200),
    ]

    connection.executemany(
        "INSERT INTO departments VALUES (?, ?)", departments
    )
    connection.executemany(
        "INSERT INTO employees VALUES (?, ?, ?, ?)", employees
    )
    connection.executemany(
        "INSERT INTO projects VALUES (?, ?, ?, ?)", projects
    )
    connection.executemany(
        "INSERT INTO employee_projects VALUES (?, ?, ?)",
        employee_projects,
    )


def print_rows(title: str, rows: Iterable[sqlite3.Row]) -> None:
    print(f"\n--- {title} ---")
    rows = list(rows)

    if not rows:
        print("(no rows)")
        return

    print(" | ".join(rows[0].keys()))
    for row in rows:
        print(" | ".join(str(value) for value in row))


def fundamental_subquery(connection: sqlite3.Connection) -> None:
    """
    A subquery is a query nested inside another SQL statement.

    The inner query determines the departments whose average salary exceeds
    100,000. The outer query then retrieves employees belonging to those
    departments.
    """
    rows = connection.execute(
        """
        SELECT employee_id, name, department_id, salary
        FROM employees
        WHERE department_id IN (
            SELECT department_id
            FROM employees
            GROUP BY department_id
            HAVING AVG(salary) > 100000
        )
        ORDER BY department_id, salary DESC
        """
    )
    print_rows("Employees in departments with average salary above 100,000", rows)


def scalar_subquery(connection: sqlite3.Connection) -> None:
    """
    A scalar subquery returns exactly one value.

    The inner SELECT computes the company-wide average salary. Every outer
    employee row can compare its salary against that single value.
    """
    rows = connection.execute(
        """
        SELECT name, salary
        FROM employees
        WHERE salary > (
            SELECT AVG(salary)
            FROM employees
        )
        ORDER BY salary DESC
        """
    )
    print_rows("Employees above the company-wide average", rows)


def single_row_subquery(connection: sqlite3.Connection) -> None:
    """
    A single-row subquery returns one row, usually because its predicate
    identifies a unique entity. SQLite supports comparing individual columns
    directly with the returned value.
    """
    rows = connection.execute(
        """
        SELECT name, salary
        FROM employees
        WHERE department_id = (
            SELECT department_id
            FROM departments
            WHERE department_name = 'Security'
        )
        ORDER BY salary DESC
        """
    )
    print_rows("Employees in the Security department", rows)


def multi_row_subquery(connection: sqlite3.Connection) -> None:
    """
    A multi-row subquery returns a set of values.

    IN is appropriate when the outer expression may match any value returned
    by the inner query.
    """
    rows = connection.execute(
        """
        SELECT name, salary
        FROM employees
        WHERE department_id IN (
            SELECT department_id
            FROM departments
            WHERE department_name IN ('Engineering', 'Security', 'Research')
        )
        ORDER BY salary DESC
        """
    )
    print_rows("Employees in selected departments", rows)


def exists_subquery(connection: sqlite3.Connection) -> None:
    """
    EXISTS tests whether the correlated inner query can find at least one
    matching row. The database can stop searching after finding a qualifying
    match, making EXISTS useful for existence predicates.
    """
    rows = connection.execute(
        """
        SELECT e.employee_id, e.name
        FROM employees AS e
        WHERE EXISTS (
            SELECT 1
            FROM employee_projects AS ep
            WHERE ep.employee_id = e.employee_id
              AND ep.hours >= 180
        )
        ORDER BY e.employee_id
        """
    )
    print_rows("Employees assigned at least 180 hours to one project", rows)


def not_exists_subquery(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT d.department_name
        FROM departments AS d
        WHERE NOT EXISTS (
            SELECT 1
            FROM projects AS p
            WHERE p.department_id = d.department_id
        )
        ORDER BY d.department_name
        """
    )
    print_rows("Departments without projects", rows)


def correlated_subquery(connection: sqlite3.Connection) -> None:
    """
    A correlated subquery refers to a value from the current outer row.

    The inner AVG is therefore calculated separately for the department
    associated with each employee.
    """
    rows = connection.execute(
        """
        SELECT
            e.name,
            e.department_id,
            e.salary
        FROM employees AS e
        WHERE e.salary > (
            SELECT AVG(other.salary)
            FROM employees AS other
            WHERE other.department_id = e.department_id
        )
        ORDER BY e.department_id, e.salary DESC
        """
    )
    print_rows("Employees above their own department average", rows)


def comparison_with_any_and_all(connection: sqlite3.Connection) -> None:
    """
    SQLite does not implement PostgreSQL's ANY/ALL comparison syntax.

    Equivalent relational logic can be expressed with IN, EXISTS, and NOT
    EXISTS. The first query finds salaries equal to any Engineering salary.
    The second finds employees whose salary is greater than every Finance
    salary by proving that no Finance salary is greater than or equal to it.
    """
    any_rows = connection.execute(
        """
        SELECT name, salary
        FROM employees
        WHERE salary IN (
            SELECT salary
            FROM employees
            WHERE department_id = (
                SELECT department_id
                FROM departments
                WHERE department_name = 'Engineering'
            )
        )
        ORDER BY salary
        """
    )

    all_rows = connection.execute(
        """
        SELECT name, salary
        FROM employees AS e
        WHERE NOT EXISTS (
            SELECT 1
            FROM employees AS finance
            WHERE finance.department_id = (
                SELECT department_id
                FROM departments
                WHERE department_name = 'Finance'
            )
            AND finance.salary >= e.salary
        )
        ORDER BY salary DESC
        """
    )

    print_rows("Salaries matching any Engineering salary", any_rows)
    print_rows("Employees earning more than every Finance employee", all_rows)


def subquery_in_from_clause(connection: sqlite3.Connection) -> None:
    """
    A table subquery in FROM creates a derived table.

    The inner query produces one aggregate row per department. The outer query
    treats that result like a temporary relational table.
    """
    rows = connection.execute(
        """
        SELECT
            department_name,
            employee_count,
            average_salary
        FROM (
            SELECT
                d.department_name,
                COUNT(e.employee_id) AS employee_count,
                ROUND(AVG(e.salary), 2) AS average_salary
            FROM departments AS d
            LEFT JOIN employees AS e
                ON e.department_id = d.department_id
            GROUP BY d.department_id, d.department_name
        ) AS department_metrics
        WHERE employee_count >= 2
        ORDER BY average_salary DESC
        """
    )
    print_rows("Derived department metrics", rows)


def subquery_in_select_clause(connection: sqlite3.Connection) -> None:
    """
    A scalar subquery in SELECT adds a calculated value to every outer row.
    """
    rows = connection.execute(
        """
        SELECT
            e.name,
            e.salary,
            (
                SELECT ROUND(AVG(x.salary), 2)
                FROM employees AS x
                WHERE x.department_id = e.department_id
            ) AS department_average
        FROM employees AS e
        ORDER BY e.department_id, e.salary DESC
        """
    )
    print_rows("Employee salary compared with department metric", rows)


def nested_subqueries(connection: sqlite3.Connection) -> None:
    """
    Nested subqueries can express layered business logic.

    Here the innermost query identifies Engineering, the middle query finds
    its average salary, and the outer query finds employees above that value.
    """
    rows = connection.execute(
        """
        SELECT name, salary
        FROM employees
        WHERE salary > (
            SELECT AVG(salary)
            FROM employees
            WHERE department_id = (
                SELECT department_id
                FROM departments
                WHERE department_name = 'Engineering'
            )
        )
        ORDER BY salary DESC
        """
    )
    print_rows("Employees above Engineering's average salary", rows)


def subquery_with_update(connection: sqlite3.Connection) -> None:
    """
    Subqueries can participate in DML.

    This transaction marks project records for departments whose total payroll
    exceeds a threshold. The demonstration rolls back so that the teaching
    dataset remains unchanged for later examples.
    """
    connection.execute("BEGIN")

    try:
        connection.execute(
            """
            UPDATE projects
            SET budget = budget * 1.05
            WHERE department_id IN (
                SELECT department_id
                FROM employees
                GROUP BY department_id
                HAVING SUM(salary) > 200000
            )
            """
        )

        rows = connection.execute(
            """
            SELECT project_name, budget
            FROM projects
            ORDER BY project_id
            """
        )
        print_rows("DML using a subquery before rollback", rows)

        connection.rollback()
    except sqlite3.Error:
        connection.rollback()
        raise


def subquery_with_delete(connection: sqlite3.Connection) -> None:
    """
    DELETE can also use subqueries. This example identifies departments with
    no employee records. The current dataset has none, so no rows are removed.
    """
    connection.execute("BEGIN")

    try:
        cursor = connection.execute(
            """
            DELETE FROM departments
            WHERE NOT EXISTS (
                SELECT 1
                FROM employees
                WHERE employees.department_id = departments.department_id
            )
            """
        )
        print(f"\nDELETE using NOT EXISTS affected {cursor.rowcount} row(s).")
        connection.rollback()
    except sqlite3.Error:
        connection.rollback()
        raise


def demonstrate_single_value_contract(connection: sqlite3.Connection) -> None:
    """
    A scalar comparison expects one value.

    The query below is intentionally guarded by a UNIQUE department-name
    predicate. This illustrates an important production rule: never assume a
    scalar subquery returns one row unless its predicate or schema guarantees it.
    """
    row = connection.execute(
        """
        SELECT (
            SELECT department_id
            FROM departments
            WHERE department_name = 'Security'
        ) AS security_department_id
        """
    ).fetchone()

    print("\nScalar value contract:")
    print(f"Security department ID = {row['security_department_id']}")


def demonstrate_null_behavior(connection: sqlite3.Connection) -> None:
    """
    NOT IN has subtle NULL semantics. EXISTS/NOT EXISTS is often safer when
    the inner expression can contain NULL values.

    This isolated query uses a literal NULL to make the three-valued-logic
    behavior observable without changing the main schema.
    """
    row = connection.execute(
        """
        SELECT
            5 IN (1, 2, NULL) AS in_result,
            5 NOT IN (1, 2, NULL) AS not_in_result,
            EXISTS (
                SELECT 1
                WHERE 5 = 1
            ) AS exists_result
        """
    ).fetchone()

    print("\nNULL and NOT IN behavior:")
    print(f"5 IN (1, 2, NULL)      -> {row['in_result']}")
    print(f"5 NOT IN (1, 2, NULL)  -> {row['not_in_result']}")
    print(f"EXISTS matching 5      -> {row['exists_result']}")


def compare_subquery_and_join(connection: sqlite3.Connection) -> None:
    """
    Subqueries and joins can often express the same relational question.

    This comparison uses a derived table instead of claiming that one style is
    universally faster. Query planners, indexes, data volume, and predicates
    determine the actual execution plan.
    """
    subquery_rows = connection.execute(
        """
        SELECT name
        FROM employees
        WHERE department_id IN (
            SELECT department_id
            FROM departments
            WHERE department_name IN ('Security', 'Research')
        )
        ORDER BY name
        """
    ).fetchall()

    join_rows = connection.execute(
        """
        SELECT e.name
        FROM employees AS e
        JOIN departments AS d
            ON d.department_id = e.department_id
        WHERE d.department_name IN ('Security', 'Research')
        ORDER BY e.name
        """
    ).fetchall()

    subquery_names = [row["name"] for row in subquery_rows]
    join_names = [row["name"] for row in join_rows]

    print("\nSubquery versus JOIN equivalence:")
    print(f"Subquery result: {subquery_names}")
    print(f"JOIN result:     {join_names}")
    print(f"Equivalent:      {subquery_names == join_names}")


def inspect_query_plan(connection: sqlite3.Connection) -> None:
    """
    EXPLAIN QUERY PLAN makes optimizer behavior visible.

    The demonstration is intentionally small. In production, performance
    conclusions should be based on realistic data volume and measured plans.
    """
    plan = connection.execute(
        """
        EXPLAIN QUERY PLAN
        SELECT name
        FROM employees
        WHERE salary > (
            SELECT AVG(salary)
            FROM employees
        )
        """
    ).fetchall()

    print("\nQuery plan for scalar-subquery example:")
    for row in plan:
        print(" | ".join(str(value) for value in row))


def validate_business_rules(connection: sqlite3.Connection) -> None:
    """
    A practical validation query can combine several subquery forms.

    The result identifies departments where at least one employee earns more
    than the department's average and where that department owns a project.
    """
    rows = connection.execute(
        """
        SELECT d.department_name
        FROM departments AS d
        WHERE EXISTS (
            SELECT 1
            FROM employees AS e
            WHERE e.department_id = d.department_id
              AND e.salary > (
                  SELECT AVG(e2.salary)
                  FROM employees AS e2
                  WHERE e2.department_id = d.department_id
              )
        )
        AND EXISTS (
            SELECT 1
            FROM projects AS p
            WHERE p.department_id = d.department_id
        )
        ORDER BY d.department_name
        """
    )
    print_rows("Departments satisfying combined subquery rules", rows)


def extract_employee_objects(connection: sqlite3.Connection) -> list[Employee]:
    """
    The SQL results can be mapped into typed Python objects after the database
    performs the relational filtering.
    """
    rows = connection.execute(
        """
        SELECT employee_id, name, department_id, salary
        FROM employees
        WHERE salary > (
            SELECT AVG(salary)
            FROM employees
        )
        ORDER BY salary DESC
        """
    )

    return [
        Employee(
            employee_id=row["employee_id"],
            name=row["name"],
            department_id=row["department_id"],
            salary=row["salary"],
        )
        for row in rows
    ]


def run_demo() -> None:
    connection = create_connection()

    try:
        create_schema(connection)
        seed_data(connection)

        print("SUBQUERIES FUNDAMENTALS")
        print("Scalar, single-row, multi-row, correlated, and table subqueries")

        fundamental_subquery(connection)
        scalar_subquery(connection)
        single_row_subquery(connection)
        multi_row_subquery(connection)
        exists_subquery(connection)
        not_exists_subquery(connection)
        correlated_subquery(connection)
        comparison_with_any_and_all(connection)
        subquery_in_from_clause(connection)
        subquery_in_select_clause(connection)
        nested_subqueries(connection)
        subquery_with_update(connection)
        subquery_with_delete(connection)
        demonstrate_single_value_contract(connection)
        demonstrate_null_behavior(connection)
        compare_subquery_and_join(connection)
        inspect_query_plan(connection)
        validate_business_rules(connection)

        employees = extract_employee_objects(connection)
        print("\nPython objects produced from a subquery result:")
        for employee in employees:
            print(
                f"{employee.name}: "
                f"department={employee.department_id}, "
                f"salary={employee.salary:,.2f}"
            )

    finally:
        connection.close()


if __name__ == "__main__":
    run_demo()
