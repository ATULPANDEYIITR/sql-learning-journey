"""
Basic Data Modification with SQL:
UPDATE, DELETE, Conditional Updates, and Safe Deletion

This standalone study script teaches the principles of modifying relational
data. It uses Python's standard library sqlite3 module so every example can
run without installing an external package.

The examples progress from beginner concepts to transaction safety,
conditional updates, optimistic safety checks, bulk modifications,
constraints, rollback, auditing, and production-oriented patterns.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional


DATABASE = ":memory:"


# ---------------------------------------------------------------------------
# 1. DATABASE SETUP
# ---------------------------------------------------------------------------

def connect_database() -> sqlite3.Connection:
    """Create a SQLite database connection with useful safety settings."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    # Foreign keys are disabled by default in some SQLite configurations.
    # Enabling them makes referential-integrity rules active.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Create a small business database used throughout the demonstrations."""
    connection.executescript(
        """
        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            employee_code TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            salary REAL NOT NULL CHECK (salary >= 0),
            status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
            performance_score REAL CHECK (
                performance_score IS NULL
                OR performance_score BETWEEN 0 AND 100
            ),
            last_modified TEXT NOT NULL,
            FOREIGN KEY (department_id)
                REFERENCES departments(department_id)
        );

        CREATE TABLE employee_audit (
            audit_id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_salary REAL,
            new_salary REAL,
            old_status TEXT,
            new_status TEXT,
            changed_at TEXT NOT NULL
        );

        CREATE INDEX idx_employees_department
            ON employees(department_id);

        CREATE INDEX idx_employees_status
            ON employees(status);
        """
    )


def seed_data(connection: sqlite3.Connection) -> None:
    """Insert representative records for the examples."""
    departments = [
        (1, "Engineering"),
        (2, "Finance"),
        (3, "Human Resources"),
        (4, "Operations"),
    ]

    connection.executemany(
        """
        INSERT INTO departments (department_id, department_name)
        VALUES (?, ?)
        """,
        departments,
    )

    employees = [
        (1, "EMP001", "Aarav Sharma", 1, 75000, "ACTIVE", 91),
        (2, "EMP002", "Meera Singh", 1, 68000, "ACTIVE", 84),
        (3, "EMP003", "Kabir Verma", 2, 62000, "ACTIVE", 76),
        (4, "EMP004", "Isha Gupta", 3, 58000, "ACTIVE", 88),
        (5, "EMP005", "Rohan Das", 4, 52000, "INACTIVE", 61),
        (6, "EMP006", "Ananya Rao", 1, 71000, "ACTIVE", 95),
        (7, "EMP007", "Vikram Jain", 4, 48000, "ACTIVE", 69),
        (8, "EMP008", "Neha Kapoor", 2, 90000, "ACTIVE", 97),
    ]

    now = datetime.now().isoformat(timespec="seconds")

    connection.executemany(
        """
        INSERT INTO employees (
            employee_id,
            employee_code,
            full_name,
            department_id,
            salary,
            status,
            performance_score,
            last_modified
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            employee[:-1] + (employee[-1], now)
            for employee in employees
        ],
    )

    connection.commit()


# ---------------------------------------------------------------------------
# 2. DISPLAY HELPERS
# ---------------------------------------------------------------------------

def print_rows(
    connection: sqlite3.Connection,
    query: str,
    parameters: tuple = (),
    title: str = "",
) -> None:
    """Execute a SELECT statement and display its rows."""
    if title:
        print(f"\n--- {title} ---")

    rows = connection.execute(query, parameters).fetchall()

    if not rows:
        print("(no rows)")
        return

    for row in rows:
        print(dict(row))


def show_employees(connection: sqlite3.Connection, title: str) -> None:
    print_rows(
        connection,
        """
        SELECT
            employee_id,
            employee_code,
            full_name,
            department_id,
            salary,
            status,
            performance_score
        FROM employees
        ORDER BY employee_id
        """,
        title=title,
    )


# ---------------------------------------------------------------------------
# 3. BASIC UPDATE
# ---------------------------------------------------------------------------

def basic_update(connection: sqlite3.Connection) -> None:
    """
    UPDATE changes values in existing rows.

    General SQL form:

        UPDATE table_name
        SET column_name = new_value
        WHERE condition;

    The WHERE clause is critical when only selected rows should change.
    """
    connection.execute(
        """
        UPDATE employees
        SET salary = 78000,
            last_modified = ?
        WHERE employee_id = ?
        """,
        (datetime.now().isoformat(timespec="seconds"), 1),
    )

    connection.commit()


# ---------------------------------------------------------------------------
# 4. UPDATE USING A CALCULATION
# ---------------------------------------------------------------------------

def percentage_raise(connection: sqlite3.Connection) -> None:
    """
    SQL can calculate the new value from the old value.

    A 5% raise can be expressed as:

        salary = salary * 1.05

    The calculation happens inside the database.
    """
    connection.execute(
        """
        UPDATE employees
        SET salary = ROUND(salary * 1.05, 2),
            last_modified = ?
        WHERE department_id = ?
          AND status = 'ACTIVE'
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            1,
        ),
    )

    connection.commit()


# ---------------------------------------------------------------------------
# 5. CONDITIONAL UPDATE
# ---------------------------------------------------------------------------

def conditional_update(connection: sqlite3.Connection) -> None:
    """
    Conditional updates combine WHERE conditions.

    Multiple conditions are especially important for safe business rules.
    """
    connection.execute(
        """
        UPDATE employees
        SET status = 'INACTIVE',
            last_modified = ?
        WHERE status = 'ACTIVE'
          AND performance_score < ?
          AND department_id = ?
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            70,
            4,
        ),
    )

    connection.commit()


# ---------------------------------------------------------------------------
# 6. UPDATE WITH CASE
# ---------------------------------------------------------------------------

def update_with_case(connection: sqlite3.Connection) -> None:
    """
    CASE allows different modifications based on different conditions.

    This is useful for policy-driven bulk updates.
    """
    connection.execute(
        """
        UPDATE employees
        SET salary = CASE
            WHEN performance_score >= 90 THEN ROUND(salary * 1.10, 2)
            WHEN performance_score >= 80 THEN ROUND(salary * 1.07, 2)
            WHEN performance_score >= 70 THEN ROUND(salary * 1.04, 2)
            ELSE salary
        END,
        last_modified = ?
        WHERE status = 'ACTIVE'
        """,
        (datetime.now().isoformat(timespec="seconds"),),
    )

    connection.commit()


# ---------------------------------------------------------------------------
# 7. SAFE PARAMETERIZED UPDATE
# ---------------------------------------------------------------------------

def safe_update_by_employee_code(
    connection: sqlite3.Connection,
    employee_code: str,
    new_status: str,
) -> int:
    """
    Parameterized SQL prevents user-controlled values from being interpreted
    as SQL syntax.

    Never construct SQL using string concatenation such as:

        f"UPDATE employees SET status = '{new_status}' ..."

    Instead, pass values through parameters.
    """
    allowed_statuses = {"ACTIVE", "INACTIVE"}

    if new_status not in allowed_statuses:
        raise ValueError("Invalid employee status")

    cursor = connection.execute(
        """
        UPDATE employees
        SET status = ?,
            last_modified = ?
        WHERE employee_code = ?
        """,
        (
            new_status,
            datetime.now().isoformat(timespec="seconds"),
            employee_code,
        ),
    )

    connection.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# 8. CHECKING ROWCOUNT
# ---------------------------------------------------------------------------

def update_with_expected_row_count(
    connection: sqlite3.Connection,
    employee_id: int,
    expected_status: str,
    new_status: str,
) -> bool:
    """
    Checking affected-row count provides a simple safety mechanism.

    If zero rows changed, the expected state may no longer exist.
    This can detect stale application assumptions.
    """
    cursor = connection.execute(
        """
        UPDATE employees
        SET status = ?,
            last_modified = ?
        WHERE employee_id = ?
          AND status = ?
        """,
        (
            new_status,
            datetime.now().isoformat(timespec="seconds"),
            employee_id,
            expected_status,
        ),
    )

    connection.commit()

    return cursor.rowcount == 1


# ---------------------------------------------------------------------------
# 9. BASIC DELETE
# ---------------------------------------------------------------------------

def basic_delete(connection: sqlite3.Connection) -> None:
    """
    DELETE permanently removes rows.

    Always ask:
      1. Which table?
      2. Which rows?
      3. Is the WHERE condition correct?
      4. Can the operation be rolled back?
      5. Are related rows affected by foreign-key rules?
    """
    connection.execute(
        """
        DELETE FROM employees
        WHERE employee_id = ?
        """,
        (7,),
    )

    connection.commit()


# ---------------------------------------------------------------------------
# 10. SAFE CONDITIONAL DELETE
# ---------------------------------------------------------------------------

def safe_conditional_delete(connection: sqlite3.Connection) -> int:
    """
    Delete only inactive employees from a specific department.

    Narrow predicates are safer than broad predicates.
    """
    cursor = connection.execute(
        """
        DELETE FROM employees
        WHERE status = 'INACTIVE'
          AND department_id = ?
        """,
        (4,),
    )

    connection.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# 11. THE DANGEROUS DELETE WITHOUT WHERE
# ---------------------------------------------------------------------------

def explain_dangerous_delete() -> None:
    """
    Do not execute this statement:

        DELETE FROM employees;

    It deletes every row.

    The function only prints the statement to make the danger explicit.
    """
    print(
        "\nDangerous statement (NOT EXECUTED): "
        "DELETE FROM employees;"
    )


# ---------------------------------------------------------------------------
# 12. PREVIEW BEFORE MODIFYING
# ---------------------------------------------------------------------------

def preview_then_update(connection: sqlite3.Connection) -> int:
    """
    A production workflow can preview candidate rows before modification.

    First run SELECT with the same WHERE clause.
    Then perform UPDATE using exactly that predicate.
    """
    candidates = connection.execute(
        """
        SELECT employee_id
        FROM employees
        WHERE status = 'ACTIVE'
          AND performance_score >= 90
        """
    ).fetchall()

    print(
        "\nRows that would receive the high-performance update:",
        [row["employee_id"] for row in candidates],
    )

    cursor = connection.execute(
        """
        UPDATE employees
        SET salary = ROUND(salary * 1.02, 2),
            last_modified = ?
        WHERE status = 'ACTIVE'
          AND performance_score >= 90
        """,
        (datetime.now().isoformat(timespec="seconds"),),
    )

    connection.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# 13. TRANSACTIONS AND ROLLBACK
# ---------------------------------------------------------------------------

@contextmanager
def transaction(connection: sqlite3.Connection):
    """
    Group several modifications into one atomic unit.

    If an exception occurs, rollback restores the previous state.
    """
    try:
        connection.execute("BEGIN")
        yield
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def demonstrate_rollback(connection: sqlite3.Connection) -> None:
    """Demonstrate that failed multi-step changes can be rolled back."""
    original_salary = connection.execute(
        """
        SELECT salary
        FROM employees
        WHERE employee_id = 1
        """
    ).fetchone()["salary"]

    try:
        with transaction(connection):
            connection.execute(
                """
                UPDATE employees
                SET salary = ?
                WHERE employee_id = ?
                """,
                (original_salary + 10000, 1),
            )

            # This violates the CHECK constraint on salary.
            connection.execute(
                """
                UPDATE employees
                SET salary = ?
                WHERE employee_id = ?
                """,
                (-5000, 2),
            )
    except sqlite3.IntegrityError:
        print("\nTransaction failed; changes were rolled back.")

    final_salary = connection.execute(
        """
        SELECT salary
        FROM employees
        WHERE employee_id = 1
        """
    ).fetchone()["salary"]

    print(
        "Salary before transaction:",
        original_salary,
        "| Salary after rollback:",
        final_salary,
    )


# ---------------------------------------------------------------------------
# 14. SOFT DELETE
# ---------------------------------------------------------------------------

def explain_soft_delete() -> None:
    """
    Hard delete:
        DELETE FROM table WHERE ...;

    Soft delete:
        UPDATE table
        SET status = 'INACTIVE'
        WHERE ...;

    Soft deletion preserves historical data and can support recovery,
    auditing, reporting, and regulatory retention requirements.
    """
    print(
        "\nSoft deletion example: UPDATE employees "
        "SET status = 'INACTIVE' WHERE employee_id = 3;"
    )


# ---------------------------------------------------------------------------
# 15. AUDITING CHANGES
# ---------------------------------------------------------------------------

def update_with_audit(
    connection: sqlite3.Connection,
    employee_id: int,
    new_salary: float,
) -> None:
    """Record old and new values in an audit table."""
    row = connection.execute(
        """
        SELECT salary, status
        FROM employees
        WHERE employee_id = ?
        """,
        (employee_id,),
    ).fetchone()

    if row is None:
        raise ValueError("Employee does not exist")

    old_salary = row["salary"]
    old_status = row["status"]
    timestamp = datetime.now().isoformat(timespec="seconds")

    with transaction(connection):
        connection.execute(
            """
            UPDATE employees
            SET salary = ?,
                last_modified = ?
            WHERE employee_id = ?
            """,
            (new_salary, timestamp, employee_id),
        )

        connection.execute(
            """
            INSERT INTO employee_audit (
                employee_id,
                action,
                old_salary,
                new_salary,
                old_status,
                new_status,
                changed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                employee_id,
                "UPDATE",
                old_salary,
                new_salary,
                old_status,
                old_status,
                timestamp,
            ),
        )


# ---------------------------------------------------------------------------
# 16. BULK DELETE WITH A RETENTION RULE
# ---------------------------------------------------------------------------

def retention_delete(connection: sqlite3.Connection) -> int:
    """
    Demonstrates a retention rule.

    The example uses a deterministic ID condition rather than system time,
    so the study file produces repeatable results.
    """
    cursor = connection.execute(
        """
        DELETE FROM employees
        WHERE status = 'INACTIVE'
          AND employee_id < ?
        """,
        (5,),
    )

    connection.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# 17. FOREIGN-KEY SAFETY
# ---------------------------------------------------------------------------

def demonstrate_foreign_key_protection(connection: sqlite3.Connection) -> None:
    """
    A department cannot be deleted while employees still reference it.

    This prevents orphaned employee records.
    """
    try:
        connection.execute(
            """
            DELETE FROM departments
            WHERE department_id = ?
            """,
            (1,),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        print(
            "\nForeign-key protection prevented deletion of a "
            "department that still has employees."
        )


# ---------------------------------------------------------------------------
# 18. DATACLASS FOR APPLICATION-LEVEL VALIDATION
# ---------------------------------------------------------------------------

@dataclass
class SalaryChange:
    employee_id: int
    new_salary: float

    def validate(self) -> None:
        if self.employee_id <= 0:
            raise ValueError("Employee ID must be positive")

        if self.new_salary < 0:
            raise ValueError("Salary cannot be negative")


def apply_salary_change(
    connection: sqlite3.Connection,
    change: SalaryChange,
) -> bool:
    """Validate application input before sending it to SQL."""
    change.validate()

    cursor = connection.execute(
        """
        UPDATE employees
        SET salary = ?,
            last_modified = ?
        WHERE employee_id = ?
        """,
        (
            change.new_salary,
            datetime.now().isoformat(timespec="seconds"),
            change.employee_id,
        ),
    )

    connection.commit()
    return cursor.rowcount == 1


# ---------------------------------------------------------------------------
# 19. COMPARING UPDATE STRATEGIES
# ---------------------------------------------------------------------------

def demonstrate_update_strategies(connection: sqlite3.Connection) -> None:
    """
    Three common strategies:

    1. Direct update by primary key.
    2. Conditional update using business state.
    3. Optimistic update using both identity and expected old state.
    """
    connection.execute(
        """
        UPDATE employees
        SET salary = salary + 500
        WHERE employee_id = ?
        """,
        (2,),
    )

    connection.execute(
        """
        UPDATE employees
        SET status = 'INACTIVE'
        WHERE performance_score < 60
          AND status = 'ACTIVE'
        """
    )

    connection.execute(
        """
        UPDATE employees
        SET salary = salary + 1000
        WHERE employee_id = ?
          AND salary = ?
        """,
        (3, 62000),
    )

    connection.commit()


# ---------------------------------------------------------------------------
# 20. SQL NULL AND CONDITIONAL MODIFICATION
# ---------------------------------------------------------------------------

def demonstrate_null_condition(connection: sqlite3.Connection) -> None:
    """
    SQL NULL requires IS NULL or IS NOT NULL.

    The expression:
        performance_score = NULL

    is not the correct way to test for NULL.
    """
    connection.execute(
        """
        UPDATE employees
        SET performance_score = NULL
        WHERE employee_id = ?
        """,
        (6,),
    )

    connection.commit()

    print_rows(
        connection,
        """
        SELECT employee_id, full_name, performance_score
        FROM employees
        WHERE performance_score IS NULL
        """,
        title="Rows containing NULL performance scores",
    )


# ---------------------------------------------------------------------------
# 21. PERFORMANCE: INDEXED PREDICATES
# ---------------------------------------------------------------------------

def demonstrate_query_plan(connection: sqlite3.Connection) -> None:
    """
    UPDATE and DELETE first need to locate rows.

    Indexes can make locating rows substantially faster for large tables.
    The exact plan depends on the database engine and data distribution.
    """
    rows = connection.execute(
        """
        EXPLAIN QUERY PLAN
        SELECT employee_id
        FROM employees
        WHERE department_id = ?
        """,
        (1,),
    ).fetchall()

    print("\nQuery plan for indexed department lookup:")
    for row in rows:
        print(tuple(row))


# ---------------------------------------------------------------------------
# 22. COMMON APPLICATION-SIDE SAFETY CHECKS
# ---------------------------------------------------------------------------

def validate_modification_request(
    table_name: str,
    where_clause_present: bool,
    expected_rows: Optional[int],
) -> None:
    """
    Basic application policy checks.

    Identifiers such as table names cannot be safely supplied as ordinary
    parameter values. They should come from trusted, predefined choices.
    """
    trusted_tables = {"employees"}

    if table_name not in trusted_tables:
        raise ValueError("Untrusted table name")

    if not where_clause_present:
        raise ValueError("Refusing modification without a WHERE clause")

    if expected_rows is not None and expected_rows < 0:
        raise ValueError("Expected row count cannot be negative")


def guarded_delete(
    connection: sqlite3.Connection,
    employee_id: int,
) -> bool:
    """
    A deliberately narrow deletion function.

    The function does not accept arbitrary SQL and therefore limits accidental
    destructive operations.
    """
    validate_modification_request(
        table_name="employees",
        where_clause_present=True,
        expected_rows=1,
    )

    cursor = connection.execute(
        """
        DELETE FROM employees
        WHERE employee_id = ?
          AND status = 'INACTIVE'
        """,
        (employee_id,),
    )

    connection.commit()
    return cursor.rowcount == 1


# ---------------------------------------------------------------------------
# 23. TESTING MODIFICATION BEHAVIOR
# ---------------------------------------------------------------------------

def test_update_changes_one_row() -> None:
    connection = connect_database()
    create_schema(connection)
    seed_data(connection)

    before = connection.execute(
        "SELECT salary FROM employees WHERE employee_id = 1"
    ).fetchone()["salary"]

    changed = connection.execute(
        """
        UPDATE employees
        SET salary = ?
        WHERE employee_id = ?
        """,
        (before + 1000, 1),
    ).rowcount

    assert changed == 1

    after = connection.execute(
        "SELECT salary FROM employees WHERE employee_id = 1"
    ).fetchone()["salary"]

    assert after == before + 1000
    connection.close()


def test_delete_requires_matching_condition() -> None:
    connection = connect_database()
    create_schema(connection)
    seed_data(connection)

    changed = connection.execute(
        """
        DELETE FROM employees
        WHERE employee_id = ?
          AND status = 'INACTIVE'
        """,
        (1,),
    ).rowcount

    assert changed == 0

    exists = connection.execute(
        """
        SELECT 1
        FROM employees
        WHERE employee_id = 1
        """
    ).fetchone()

    assert exists is not None
    connection.close()


def test_transaction_rolls_back() -> None:
    connection = connect_database()
    create_schema(connection)
    seed_data(connection)

    original = connection.execute(
        "SELECT salary FROM employees WHERE employee_id = 1"
    ).fetchone()["salary"]

    try:
        with transaction(connection):
            connection.execute(
                "UPDATE employees SET salary = ? WHERE employee_id = 1",
                (original + 5000,),
            )
            connection.execute(
                "UPDATE employees SET salary = -1 WHERE employee_id = 2"
            )
    except sqlite3.IntegrityError:
        pass

    final = connection.execute(
        "SELECT salary FROM employees WHERE employee_id = 1"
    ).fetchone()["salary"]

    assert final == original
    connection.close()


def run_tests() -> None:
    """Run lightweight built-in tests without external testing packages."""
    tests = [
        test_update_changes_one_row,
        test_delete_requires_matching_condition,
        test_transaction_rolls_back,
    ]

    for test in tests:
        test()

    print("\nAll built-in tests passed.")


# ---------------------------------------------------------------------------
# 24. COMPLETE DEMONSTRATION
# ---------------------------------------------------------------------------

def main() -> None:
    connection = connect_database()
    create_schema(connection)
    seed_data(connection)

    show_employees(connection, "Initial data")

    basic_update(connection)
    show_employees(connection, "After basic UPDATE")

    percentage_raise(connection)
    show_employees(connection, "After conditional percentage raise")

    conditional_update(connection)
    show_employees(connection, "After conditional status update")

    update_with_case(connection)
    show_employees(connection, "After CASE-based update")

    changed = safe_update_by_employee_code(
        connection,
        "EMP004",
        "INACTIVE",
    )
    print(f"\nParameterized update changed {changed} row(s).")

    succeeded = update_with_expected_row_count(
        connection,
        employee_id=2,
        expected_status="ACTIVE",
        new_status="INACTIVE",
    )
    print("Optimistic state update succeeded:", succeeded)

    preview_count = preview_then_update(connection)
    print(f"Preview-based update changed {preview_count} row(s).")

    demonstrate_rollback(connection)

    explain_soft_delete()

    update_with_audit(
        connection,
        employee_id=3,
        new_salary=65000,
    )

    print_rows(
        connection,
        """
        SELECT *
        FROM employee_audit
        ORDER BY audit_id
        """,
        title="Audit records",
    )

    explain_dangerous_delete()

    deleted = basic_delete_and_report(connection)
    print(f"\nBasic DELETE removed {deleted} row(s).")

    deleted = safe_conditional_delete(connection)
    print(f"Conditional DELETE removed {deleted} row(s).")

    retention_deleted = retention_delete(connection)
    print(
        f"Retention DELETE removed {retention_deleted} row(s)."
    )

    demonstrate_foreign_key_protection(connection)

    explain_soft_delete()

    change = SalaryChange(employee_id=4, new_salary=60000)
    print(
        "\nValidated salary change applied:",
        apply_salary_change(connection, change),
    )

    demonstrate_update_strategies(connection)

    demonstrate_null_condition(connection)

    demonstrate_query_plan(connection)

    guarded_result = guarded_delete(connection, employee_id=5)
    print("\nGuarded deletion result:", guarded_result)

    show_employees(connection, "Final data")

    run_tests()

    connection.close()


def basic_delete_and_report(connection: sqlite3.Connection) -> int:
    """Delete one specific employee and return the affected-row count."""
    cursor = connection.execute(
        """
        DELETE FROM employees
        WHERE employee_id = ?
        """,
        (7,),
    )
    connection.commit()
    return cursor.rowcount


if __name__ == "__main__":
    main()
