"""
JOIN vs Subquery
----------------
A self-contained progression from basic relational query design to advanced
query-selection analysis using an in-memory SQLite database.

The examples deliberately compare:
- INNER and LEFT JOINs
- correlated and uncorrelated subqueries
- IN, EXISTS, scalar subqueries
- aggregation with JOIN versus aggregation with subqueries
- anti-joins versus NOT EXISTS
- readability and performance trade-offs
- NULL and duplicate-row behavior
- query-plan inspection
- reusable query-building patterns

SQLite is used because it is included in Python's standard library.
The SQL concepts demonstrated are broadly applicable to PostgreSQL,
MySQL, SQL Server, and other relational systems, although query-plan
output is SQLite-specific.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class QueryExample:
    name: str
    purpose: str
    sql: str


def create_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            department_id INTEGER,
            salary NUMERIC NOT NULL CHECK (salary > 0),
            manager_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES departments(department_id),
            FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
        );

        CREATE TABLE projects (
            project_id INTEGER PRIMARY KEY,
            project_name TEXT NOT NULL UNIQUE,
            department_id INTEGER NOT NULL,
            budget NUMERIC NOT NULL CHECK (budget >= 0),
            FOREIGN KEY (department_id) REFERENCES departments(department_id)
        );

        CREATE TABLE employee_projects (
            employee_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            hours_per_month INTEGER NOT NULL CHECK (hours_per_month > 0),
            PRIMARY KEY (employee_id, project_id),
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        );

        CREATE INDEX idx_employees_department
            ON employees(department_id);

        CREATE INDEX idx_employees_salary
            ON employees(salary);

        CREATE INDEX idx_employee_projects_project
            ON employee_projects(project_id);

        INSERT INTO departments VALUES
            (1, 'Engineering'),
            (2, 'Finance'),
            (3, 'Operations'),
            (4, 'Human Resources'),
            (5, 'Research');

        INSERT INTO employees
            (employee_id, employee_name, department_id, salary, manager_id)
        VALUES
            (1, 'Asha', 1, 125000, NULL),
            (2, 'Ravi', 1, 98000, 1),
            (3, 'Meera', 1, 112000, 1),
            (4, 'Kabir', 2, 87000, NULL),
            (5, 'Neha', 2, 92000, 4),
            (6, 'Arjun', 3, 76000, NULL),
            (7, 'Isha', 3, 81000, 6),
            (8, 'Vikram', 4, 72000, NULL),
            (9, 'Sara', 5, 130000, NULL),
            (10, 'Dev', 5, 105000, 9);

        INSERT INTO projects
            (project_id, project_name, department_id, budget)
        VALUES
            (101, 'Cloud Migration', 1, 500000),
            (102, 'Fraud Analytics', 2, 350000),
            (103, 'Warehouse Automation', 3, 275000),
            (104, 'Recruitment Portal', 4, 90000),
            (105, 'Quantum Research', 5, 600000),
            (106, 'Internal Audit', 2, 120000);

        INSERT INTO employee_projects VALUES
            (1, 101, 80),
            (2, 101, 120),
            (3, 101, 90),
            (3, 105, 40),
            (4, 102, 70),
            (5, 102, 110),
            (6, 103, 100),
            (7, 103, 120),
            (8, 104, 100),
            (9, 105, 130),
            (10, 105, 100),
            (5, 106, 50);
        """
    )
    return connection


def print_rows(title: str, rows: Iterable[sqlite3.Row]) -> None:
    print(f"\n--- {title} ---")
    rows = list(rows)

    if not rows:
        print("(no rows)")
        return

    columns = rows[0].keys()
    print(" | ".join(columns))
    print("-" * (len(" | ".join(columns)) + 10))

    for row in rows:
        print(" | ".join(str(row[column]) for column in columns))


def execute_and_show(
    connection: sqlite3.Connection,
    title: str,
    sql: str,
    parameters: tuple = (),
) -> list[sqlite3.Row]:
    rows = connection.execute(sql, parameters).fetchall()
    print_rows(title, rows)
    return rows


def basic_join(connection: sqlite3.Connection) -> None:
    sql = """
        SELECT
            e.employee_name,
            d.department_name,
            e.salary
        FROM employees AS e
        INNER JOIN departments AS d
            ON d.department_id = e.department_id
        ORDER BY e.employee_id;
    """
    execute_and_show(
        connection,
        "INNER JOIN: combine related rows directly",
        sql,
    )


def equivalent_uncorrelated_subquery(connection: sqlite3.Connection) -> None:
    sql = """
        SELECT
            employee_name,
            salary
        FROM employees
        WHERE department_id IN (
            SELECT department_id
            FROM departments
            WHERE department_name IN ('Engineering', 'Research')
        )
        ORDER BY employee_id;
    """
    execute_and_show(
        connection,
        "Subquery: filter employees by a derived department set",
        sql,
    )


def compare_join_and_subquery_for_lookup(
    connection: sqlite3.Connection,
) -> None:
    join_sql = """
        SELECT e.employee_name, e.salary
        FROM employees AS e
        JOIN departments AS d
            ON d.department_id = e.department_id
        WHERE d.department_name = ?
        ORDER BY e.salary DESC;
    """

    subquery_sql = """
        SELECT employee_name, salary
        FROM employees
        WHERE department_id = (
            SELECT department_id
            FROM departments
            WHERE department_name = ?
        )
        ORDER BY salary DESC;
    """

    execute_and_show(
        connection,
        "JOIN lookup",
        join_sql,
        ("Engineering",),
    )

    execute_and_show(
        connection,
        "Scalar subquery lookup",
        subquery_sql,
        ("Engineering",),
    )

    print(
        "\nDesign observation: the JOIN exposes the relationship explicitly, "
        "while the scalar subquery reads naturally when the department lookup "
        "is conceptually a single prerequisite value."
    )


def aggregation_with_join(connection: sqlite3.Connection) -> None:
    sql = """
        SELECT
            d.department_name,
            COUNT(e.employee_id) AS employee_count,
            ROUND(AVG(e.salary), 2) AS average_salary
        FROM departments AS d
        LEFT JOIN employees AS e
            ON e.department_id = d.department_id
        GROUP BY d.department_id, d.department_name
        ORDER BY d.department_id;
    """
    execute_and_show(
        connection,
        "Aggregation with LEFT JOIN",
        sql,
    )


def aggregation_with_correlated_subqueries(
    connection: sqlite3.Connection,
) -> None:
    sql = """
        SELECT
            d.department_name,
            (
                SELECT COUNT(*)
                FROM employees AS e
                WHERE e.department_id = d.department_id
            ) AS employee_count,
            (
                SELECT ROUND(AVG(e.salary), 2)
                FROM employees AS e
                WHERE e.department_id = d.department_id
            ) AS average_salary
        FROM departments AS d
        ORDER BY d.department_id;
    """
    execute_and_show(
        connection,
        "Correlated subqueries for per-department aggregates",
        sql,
    )

    print(
        "\nDesign observation: correlated subqueries can be very readable "
        "when each scalar value answers a separate question about the outer "
        "row. A JOIN with GROUP BY is often easier to extend when many "
        "aggregates or relationships must be processed together."
    )


def employees_above_department_average(
    connection: sqlite3.Connection,
) -> None:
    sql = """
        SELECT
            e.employee_name,
            d.department_name,
            e.salary
        FROM employees AS e
        JOIN departments AS d
            ON d.department_id = e.department_id
        WHERE e.salary > (
            SELECT AVG(e2.salary)
            FROM employees AS e2
            WHERE e2.department_id = e.department_id
        )
        ORDER BY d.department_name, e.salary DESC;
    """
    execute_and_show(
        connection,
        "Correlated subquery: employee earns above department average",
        sql,
    )


def same_problem_with_window_function(
    connection: sqlite3.Connection,
) -> None:
    sql = """
        SELECT employee_name, department_name, salary
        FROM (
            SELECT
                e.employee_name,
                d.department_name,
                e.salary,
                AVG(e.salary) OVER (
                    PARTITION BY e.department_id
                ) AS department_average
            FROM employees AS e
            JOIN departments AS d
                ON d.department_id = e.department_id
        )
        WHERE salary > department_average
        ORDER BY department_name, salary DESC;
    """
    execute_and_show(
        connection,
        "Alternative: JOIN plus window function",
        sql,
    )


def exists_for_relationship_testing(
    connection: sqlite3.Connection,
) -> None:
    sql = """
        SELECT
            e.employee_name,
            e.salary
        FROM employees AS e
        WHERE EXISTS (
            SELECT 1
            FROM employee_projects AS ep
            JOIN projects AS p
                ON p.project_id = ep.project_id
            WHERE ep.employee_id = e.employee_id
              AND p.budget >= 500000
        )
        ORDER BY e.employee_id;
    """
    execute_and_show(
        connection,
        "EXISTS: test whether a qualifying relationship exists",
        sql,
    )

    print(
        "\nEXISTS is useful when the required result is a yes/no relationship "
        "rather than columns from the matching child rows. It also avoids "
        "the duplicate-row risk that a plain JOIN can introduce when one "
        "employee has several qualifying projects."
    )


def duplicate_row_problem(connection: sqlite3.Connection) -> None:
    join_sql = """
        SELECT
            e.employee_name,
            p.project_name
        FROM employees AS e
        JOIN employee_projects AS ep
            ON ep.employee_id = e.employee_id
        JOIN projects AS p
            ON p.project_id = ep.project_id
        WHERE p.budget >= 500000
        ORDER BY e.employee_id, p.project_id;
    """

    exists_sql = """
        SELECT e.employee_name
        FROM employees AS e
        WHERE EXISTS (
            SELECT 1
            FROM employee_projects AS ep
            JOIN projects AS p
                ON p.project_id = ep.project_id
            WHERE ep.employee_id = e.employee_id
              AND p.budget >= 500000
        )
        ORDER BY e.employee_id;
    """

    execute_and_show(
        connection,
        "JOIN returns one row per qualifying relationship",
        join_sql,
    )

    execute_and_show(
        connection,
        "EXISTS returns each employee once",
        exists_sql,
    )


def anti_join_vs_not_exists(connection: sqlite3.Connection) -> None:
    left_join_sql = """
        SELECT d.department_name
        FROM departments AS d
        LEFT JOIN employees AS e
            ON e.department_id = d.department_id
        WHERE e.employee_id IS NULL
        ORDER BY d.department_id;
    """

    not_exists_sql = """
        SELECT d.department_name
        FROM departments AS d
        WHERE NOT EXISTS (
            SELECT 1
            FROM employees AS e
            WHERE e.department_id = d.department_id
        )
        ORDER BY d.department_id;
    """

    execute_and_show(
        connection,
        "Anti-join: departments with no employees",
        left_join_sql,
    )

    execute_and_show(
        connection,
        "NOT EXISTS: departments with no employees",
        not_exists_sql,
    )


def null_semantics(connection: sqlite3.Connection) -> None:
    sql = """
        SELECT
            employee_name,
            department_id
        FROM employees
        WHERE department_id NOT IN (
            SELECT department_id
            FROM departments
            WHERE department_name = 'Nonexistent'
        )
        ORDER BY employee_id;
    """

    execute_and_show(
        connection,
        "NOT IN with a non-null subquery",
        sql,
    )

    print(
        "\nNULL warning: NOT IN becomes problematic when its subquery can "
        "produce NULL. NOT EXISTS is generally safer for anti-matching "
        "logic because its predicate is evaluated row by row."
    )


def cte_as_a_readability_tool(connection: sqlite3.Connection) -> None:
    sql = """
        WITH department_pay AS (
            SELECT
                department_id,
                AVG(salary) AS average_salary
            FROM employees
            GROUP BY department_id
        )
        SELECT
            e.employee_name,
            d.department_name,
            e.salary,
            ROUND(dp.average_salary, 2) AS department_average
        FROM employees AS e
        JOIN departments AS d
            ON d.department_id = e.department_id
        JOIN department_pay AS dp
            ON dp.department_id = e.department_id
        WHERE e.salary > dp.average_salary
        ORDER BY d.department_name, e.salary DESC;
    """
    execute_and_show(
        connection,
        "CTE: make a multi-stage comparison explicit",
        sql,
    )


def dynamic_query_builder(connection: sqlite3.Connection) -> None:
    """
    Build a safe query by keeping values in parameter bindings.
    User-controlled values are never concatenated into SQL syntax.
    """

    filters = {
        "department_name": "Engineering",
        "minimum_salary": 90000,
    }

    sql = """
        SELECT
            e.employee_name,
            d.department_name,
            e.salary
        FROM employees AS e
        JOIN departments AS d
            ON d.department_id = e.department_id
        WHERE d.department_name = ?
          AND e.salary >= ?
        ORDER BY e.salary DESC;
    """

    execute_and_show(
        connection,
        "Parameterized JOIN query",
        sql,
        (
            filters["department_name"],
            filters["minimum_salary"],
        ),
    )


def show_query_plan(
    connection: sqlite3.Connection,
    title: str,
    sql: str,
    parameters: tuple = (),
) -> None:
    print(f"\n--- Query plan: {title} ---")
    plan = connection.execute(
        "EXPLAIN QUERY PLAN " + sql,
        parameters,
    ).fetchall()

    for row in plan:
        print(" | ".join(str(value) for value in row))


def compare_query_plans(connection: sqlite3.Connection) -> None:
    join_sql = """
        SELECT e.employee_name
        FROM employees AS e
        JOIN departments AS d
            ON d.department_id = e.department_id
        WHERE d.department_name = ?
    """

    subquery_sql = """
        SELECT employee_name
        FROM employees
        WHERE department_id = (
            SELECT department_id
            FROM departments
            WHERE department_name = ?
        )
    """

    show_query_plan(
        connection,
        "JOIN",
        join_sql,
        ("Engineering",),
    )

    show_query_plan(
        connection,
        "scalar subquery",
        subquery_sql,
        ("Engineering",),
    )

    print(
        "\nA query plan is more informative than assuming that JOINs are "
        "always faster or subqueries are always slower. Modern optimizers "
        "can transform logically equivalent SQL into similar execution "
        "strategies. Actual performance depends on data volume, indexes, "
        "cardinality, statistics, predicates, and the database engine."
    )


def realistic_project_report(connection: sqlite3.Connection) -> None:
    sql = """
        WITH project_hours AS (
            SELECT
                p.project_id,
                p.project_name,
                p.budget,
                SUM(ep.hours_per_month) AS monthly_hours,
                COUNT(DISTINCT ep.employee_id) AS assigned_employees
            FROM projects AS p
            LEFT JOIN employee_projects AS ep
                ON ep.project_id = p.project_id
            GROUP BY p.project_id, p.project_name, p.budget
        ),
        department_average_budget AS (
            SELECT
                department_id,
                AVG(budget) AS average_budget
            FROM projects
            GROUP BY department_id
        )
        SELECT
            p.project_name,
            d.department_name,
            p.budget,
            p.monthly_hours,
            p.assigned_employees,
            ROUND(dab.average_budget, 2) AS department_average_budget
        FROM project_hours AS p
        JOIN projects AS original
            ON original.project_id = p.project_id
        JOIN departments AS d
            ON d.department_id = original.department_id
        JOIN department_average_budget AS dab
            ON dab.department_id = original.department_id
        WHERE p.budget > dab.average_budget
        ORDER BY p.budget DESC;
    """

    execute_and_show(
        connection,
        "Multi-stage project report using CTEs and JOINs",
        sql,
    )


def run_query_examples(connection: sqlite3.Connection) -> None:
    examples = [
        QueryExample(
            "Direct relationship",
            "Retrieve employee and department attributes",
            """
            SELECT e.employee_name, d.department_name
            FROM employees e
            JOIN departments d
              ON d.department_id = e.department_id;
            """,
        ),
        QueryExample(
            "Set filtering",
            "Find employees in selected departments",
            """
            SELECT employee_name
            FROM employees
            WHERE department_id IN (
                SELECT department_id
                FROM departments
                WHERE department_name IN ('Finance', 'Research')
            );
            """,
        ),
    ]

    print("\n--- Compact query-design catalog ---")
    for example in examples:
        print(f"\n{example.name}: {example.purpose}")
        print("SQL:")
        print(example.sql.strip())


def main() -> None:
    connection = create_database()

    try:
        print("JOIN vs Subquery: executable query-design laboratory")

        basic_join(connection)
        equivalent_uncorrelated_subquery(connection)
        compare_join_and_subquery_for_lookup(connection)

        aggregation_with_join(connection)
        aggregation_with_correlated_subqueries(connection)

        employees_above_department_average(connection)
        same_problem_with_window_function(connection)

        exists_for_relationship_testing(connection)
        duplicate_row_problem(connection)

        anti_join_vs_not_exists(connection)
        null_semantics(connection)

        cte_as_a_readability_tool(connection)
        dynamic_query_builder(connection)

        compare_query_plans(connection)
        realistic_project_report(connection)
        run_query_examples(connection)

        print(
            "\nDecision rule: use the construct that best expresses the "
            "relationship being queried, then verify performance with the "
            "database's execution plan and representative data."
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
