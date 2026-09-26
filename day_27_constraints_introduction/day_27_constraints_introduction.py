"""
Constraints Introduction: Constraints, Data Integrity, and Constraint Enforcement

This standalone study script teaches database constraints from beginner to
advanced level using SQLite, which is included in Python's standard library.

Topics demonstrated:
- Data integrity
- Constraint enforcement
- NOT NULL
- UNIQUE
- PRIMARY KEY
- FOREIGN KEY
- CHECK
- DEFAULT
- Composite keys
- Composite UNIQUE constraints
- Referential actions
- Immediate constraint checking
- Transaction behavior
- Constraint violations
- NULL and three-valued SQL logic
- Partial indexes and advanced uniqueness rules
- Deferrable constraints
- Schema inspection
- Application-level validation versus database enforcement
- Concurrency and race-condition considerations
- Testing constraints
- Practical design and production considerations
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


# ---------------------------------------------------------------------------
# 1. FOUNDATIONS
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    """Print a clear heading for each learning section."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def subsection(title: str) -> None:
    print("\n" + "-" * 78)
    print(title)
    print("-" * 78)


def connect_database() -> sqlite3.Connection:
    """
    Create an in-memory SQLite database.

    Foreign keys are disabled by default in many SQLite configurations.
    PRAGMA foreign_keys = ON makes referential integrity an enforced
    database rule rather than merely an application convention.
    """
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def show_rows(connection: sqlite3.Connection, sql: str, parameters: tuple = ()) -> None:
    """Execute a SELECT and print the result."""
    rows = connection.execute(sql, parameters).fetchall()

    if not rows:
        print("(no rows)")
        return

    print(" | ".join(rows[0].keys()))
    print("-" * 78)

    for row in rows:
        print(" | ".join(str(row[column]) for column in row.keys()))


# ---------------------------------------------------------------------------
# 2. BASIC CONSTRAINTS
# ---------------------------------------------------------------------------

def create_basic_schema(connection: sqlite3.Connection) -> None:
    """
    Demonstrate the most common column and table constraints.

    PRIMARY KEY:
        Uniquely identifies a row.

    NOT NULL:
        Prevents NULL values.

    UNIQUE:
        Prevents duplicate values.

    DEFAULT:
        Supplies a value when the column is omitted.

    CHECK:
        Requires a Boolean SQL expression to pass.

    FOREIGN KEY:
        Connects rows between related tables.
    """
    connection.executescript(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            age INTEGER CHECK (age >= 18),
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive'))
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id)
                REFERENCES customers(customer_id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE
        );
        """
    )


def demonstrate_basic_constraints(connection: sqlite3.Connection) -> None:
    subsection("Basic constraint enforcement")

    connection.execute(
        """
        INSERT INTO customers (customer_id, email, full_name, age)
        VALUES (?, ?, ?, ?)
        """,
        (1, "alice@example.com", "Alice", 30),
    )

    connection.execute(
        """
        INSERT INTO orders (order_id, customer_id, amount_cents)
        VALUES (?, ?, ?)
        """,
        (1001, 1, 4999),
    )

    show_rows(
        connection,
        """
        SELECT customer_id, email, full_name, age, status
        FROM customers
        """,
    )

    show_rows(
        connection,
        """
        SELECT order_id, customer_id, amount_cents, created_at
        FROM orders
        """,
    )

    attempts = [
        (
            "Duplicate primary key",
            """
            INSERT INTO customers
                (customer_id, email, full_name, age)
            VALUES (1, 'bob@example.com', 'Bob', 25)
            """,
        ),
        (
            "Duplicate unique email",
            """
            INSERT INTO customers
                (customer_id, email, full_name, age)
            VALUES (2, 'alice@example.com', 'Another Alice', 25)
            """,
        ),
        (
            "NULL in NOT NULL column",
            """
            INSERT INTO customers
                (customer_id, email, full_name, age)
            VALUES (2, NULL, 'Bob', 25)
            """,
        ),
        (
            "CHECK violation",
            """
            INSERT INTO customers
                (customer_id, email, full_name, age)
            VALUES (2, 'bob@example.com', 'Bob', 17)
            """,
        ),
        (
            "Invalid CHECK enumeration",
            """
            INSERT INTO customers
                (customer_id, email, full_name, age, status)
            VALUES (2, 'bob@example.com', 'Bob', 25, 'deleted')
            """,
        ),
        (
            "Foreign-key violation",
            """
            INSERT INTO orders
                (order_id, customer_id, amount_cents)
            VALUES (1002, 9999, 1000)
            """,
        ),
        (
            "CHECK on positive amount",
            """
            INSERT INTO orders
                (order_id, customer_id, amount_cents)
            VALUES (1002, 1, 0)
            """,
        ),
    ]

    for description, sql in attempts:
        try:
            connection.execute(sql)
        except sqlite3.IntegrityError as error:
            print(f"{description}: rejected -> {error}")


# ---------------------------------------------------------------------------
# 3. DATA INTEGRITY
# ---------------------------------------------------------------------------

def demonstrate_integrity_dimensions(connection: sqlite3.Connection) -> None:
    subsection("Data integrity dimensions")

    """
    Entity integrity:
        Primary-key values identify entities and cannot be duplicated.

    Domain integrity:
        Values must satisfy type/domain rules such as CHECK expressions.

    Referential integrity:
        Foreign keys prevent references to nonexistent parent rows.

    User-defined/business integrity:
        Rules specific to an application, such as status values or positive
        transaction amounts.

    The database is strongest when important invariants are represented as
    declarative constraints instead of relying exclusively on application code.
    """

    connection.execute(
        """
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
            stock_quantity INTEGER NOT NULL DEFAULT 0
                CHECK (stock_quantity >= 0)
        )
        """
    )

    connection.execute(
        """
        INSERT INTO products (sku, name, price_cents, stock_quantity)
        VALUES ('SKU-001', 'Keyboard', 2999, 20)
        """
    )

    show_rows(connection, "SELECT * FROM products")


# ---------------------------------------------------------------------------
# 4. COMPOSITE CONSTRAINTS
# ---------------------------------------------------------------------------

def demonstrate_composite_constraints(connection: sqlite3.Connection) -> None:
    subsection("Composite primary keys and composite UNIQUE constraints")

    connection.executescript(
        """
        CREATE TABLE course_enrollments (
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            grade TEXT,
            PRIMARY KEY (student_id, course_id),
            CHECK (
                grade IS NULL OR
                grade IN ('A', 'B', 'C', 'D', 'F')
            )
        );

        CREATE TABLE room_bookings (
            booking_id INTEGER PRIMARY KEY,
            room_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            UNIQUE (room_id, booking_date, start_time),
            CHECK (start_time < end_time)
        );
        """
    )

    connection.execute(
        """
        INSERT INTO course_enrollments (student_id, course_id, grade)
        VALUES (10, 501, 'A')
        """
    )

    try:
        connection.execute(
            """
            INSERT INTO course_enrollments (student_id, course_id, grade)
            VALUES (10, 501, 'B')
            """
        )
    except sqlite3.IntegrityError as error:
        print(f"Composite primary-key violation: {error}")

    try:
        connection.execute(
            """
            INSERT INTO room_bookings
                (booking_id, room_id, booking_date, start_time, end_time)
            VALUES (1, 7, '2026-09-27', '10:00', '09:00')
            """
        )
    except sqlite3.IntegrityError as error:
        print(f"Time-range CHECK violation: {error}")


# ---------------------------------------------------------------------------
# 5. NULL AND THREE-VALUED LOGIC
# ---------------------------------------------------------------------------

def demonstrate_null_semantics(connection: sqlite3.Connection) -> None:
    subsection("NULL semantics and a subtle CHECK behavior")

    """
    SQL does not use only TRUE and FALSE. Comparisons involving NULL generally
    produce UNKNOWN.

    For example:
        NULL > 0

    is UNKNOWN, not FALSE.

    SQLite's CHECK constraint rejects a row when the expression evaluates to
    FALSE (zero). UNKNOWN can therefore behave differently from an explicit
    FALSE.

    If a value must be present, combine CHECK with NOT NULL.
    """

    connection.execute(
        """
        CREATE TABLE nullable_scores (
            score INTEGER CHECK (score BETWEEN 0 AND 100)
        )
        """
    )

    connection.execute("INSERT INTO nullable_scores (score) VALUES (NULL)")

    print("A NULL score was accepted because the column is nullable.")
    show_rows(connection, "SELECT score FROM nullable_scores")

    connection.execute(
        """
        CREATE TABLE required_scores (
            score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100)
        )
        """
    )

    try:
        connection.execute(
            "INSERT INTO required_scores (score) VALUES (NULL)"
        )
    except sqlite3.IntegrityError as error:
        print(f"NOT NULL correctly rejects NULL: {error}")


# ---------------------------------------------------------------------------
# 6. FOREIGN KEYS AND REFERENTIAL ACTIONS
# ---------------------------------------------------------------------------

def demonstrate_referential_actions(connection: sqlite3.Connection) -> None:
    subsection("Foreign keys and referential actions")

    """
    Common actions include:

    RESTRICT:
        Prevent deletion/update while dependent rows exist.

    CASCADE:
        Propagate a parent deletion/update to dependent rows.

    SET NULL:
        Replace the foreign key with NULL, requiring the column to permit NULL.

    SET DEFAULT:
        Replace the foreign key with its default value when valid.

    Choice depends on business semantics. CASCADE is not automatically better:
    deleting a customer should not necessarily delete legally required records.
    """

    connection.executescript(
        """
        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            department_id INTEGER,
            name TEXT NOT NULL,
            FOREIGN KEY (department_id)
                REFERENCES departments(department_id)
                ON DELETE SET NULL
                ON UPDATE CASCADE
        );
        """
    )

    connection.execute(
        "INSERT INTO departments (department_id, name) VALUES (1, 'Engineering')"
    )

    connection.execute(
        """
        INSERT INTO employees (employee_id, department_id, name)
        VALUES (1, 1, 'Priya')
        """
    )

    connection.execute("DELETE FROM departments WHERE department_id = 1")

    print("SET NULL behavior:")
    show_rows(connection, "SELECT * FROM employees")


# ---------------------------------------------------------------------------
# 7. TRANSACTIONS AND ATOMICITY
# ---------------------------------------------------------------------------

def demonstrate_transactions(connection: sqlite3.Connection) -> None:
    subsection("Constraint failures inside transactions")

    connection.execute(
        """
        CREATE TABLE accounts (
            account_id INTEGER PRIMARY KEY,
            owner TEXT NOT NULL,
            balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0)
        )
        """
    )

    connection.executemany(
        """
        INSERT INTO accounts (account_id, owner, balance_cents)
        VALUES (?, ?, ?)
        """,
        [
            (1, "Asha", 10000),
            (2, "Rahul", 5000),
        ],
    )

    """
    A transaction can group related changes. The database should not be left
    with a partially completed business operation.

    Here, the second UPDATE would violate the balance CHECK. The explicit
    SAVEPOINT gives the example a precise rollback boundary.
    """

    try:
        connection.execute("SAVEPOINT transfer")

        connection.execute(
            """
            UPDATE accounts
            SET balance_cents = balance_cents - 7000
            WHERE account_id = 1
            """
        )

        connection.execute(
            """
            UPDATE accounts
            SET balance_cents = balance_cents + 7000
            WHERE account_id = 2
            """
        )

        connection.execute("RELEASE SAVEPOINT transfer")
    except sqlite3.IntegrityError as error:
        connection.execute("ROLLBACK TO SAVEPOINT transfer")
        connection.execute("RELEASE SAVEPOINT transfer")
        print(f"Transaction rejected: {error}")

    show_rows(
        connection,
        "SELECT account_id, owner, balance_cents FROM accounts ORDER BY account_id",
    )


# ---------------------------------------------------------------------------
# 8. ADVANCED UNIQUENESS WITH INDEXES
# ---------------------------------------------------------------------------

def demonstrate_partial_unique_index(connection: sqlite3.Connection) -> None:
    subsection("Conditional uniqueness with a partial UNIQUE index")

    """
    A common requirement is:

        Only active accounts must have unique phone numbers.

    A normal UNIQUE constraint would make every historical record unique too.
    A partial unique index allows the rule to apply only to rows satisfying
    a condition.
    """

    connection.execute(
        """
        CREATE TABLE user_accounts (
            user_id INTEGER PRIMARY KEY,
            phone TEXT NOT NULL,
            is_active INTEGER NOT NULL
                CHECK (is_active IN (0, 1))
        )
        """
    )

    connection.execute(
        """
        CREATE UNIQUE INDEX uq_active_phone
        ON user_accounts(phone)
        WHERE is_active = 1
        """
    )

    connection.executemany(
        """
        INSERT INTO user_accounts (user_id, phone, is_active)
        VALUES (?, ?, ?)
        """,
        [
            (1, "+911111111111", 1),
            (2, "+922222222222", 0),
        ],
    )

    # Historical/inactive duplicates are allowed.
    connection.execute(
        """
        INSERT INTO user_accounts (user_id, phone, is_active)
        VALUES (3, '+911111111111', 0)
        """
    )

    try:
        connection.execute(
            """
            INSERT INTO user_accounts (user_id, phone, is_active)
            VALUES (4, '+911111111111', 1)
            """
        )
    except sqlite3.IntegrityError as error:
        print(f"Conditional uniqueness rejected: {error}")

    show_rows(connection, "SELECT * FROM user_accounts ORDER BY user_id")


# ---------------------------------------------------------------------------
# 9. DEFERRABLE FOREIGN KEYS
# ---------------------------------------------------------------------------

def demonstrate_deferred_foreign_key() -> None:
    subsection("Deferred foreign-key enforcement")

    connection = connect_database()

    """
    A DEFERRABLE INITIALLY DEFERRED foreign key can postpone validation until
    transaction commit.

    This can be useful when a transaction temporarily contains an incomplete
    relationship that becomes valid before COMMIT.

    This is different from ordinary immediate foreign-key checking.
    """

    connection.executescript(
        """
        CREATE TABLE parent (
            id INTEGER PRIMARY KEY
        );

        CREATE TABLE child (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER NOT NULL,
            FOREIGN KEY (parent_id)
                REFERENCES parent(id)
                DEFERRABLE INITIALLY DEFERRED
        );
        """
    )

    try:
        connection.execute("BEGIN")

        # At this point the parent does not yet exist.
        connection.execute(
            "INSERT INTO child (id, parent_id) VALUES (1, 10)"
        )

        # The parent is created before COMMIT.
        connection.execute(
            "INSERT INTO parent (id) VALUES (10)"
        )

        connection.commit()
        print("Deferred foreign key: transaction committed successfully.")
    except sqlite3.IntegrityError as error:
        connection.rollback()
        print(f"Deferred foreign key rejected transaction: {error}")

    show_rows(connection, "SELECT * FROM parent")
    show_rows(connection, "SELECT * FROM child")


# ---------------------------------------------------------------------------
# 10. SCHEMA INTROSPECTION
# ---------------------------------------------------------------------------

def demonstrate_schema_inspection(connection: sqlite3.Connection) -> None:
    subsection("Inspecting enforced schema rules")

    print("Tables:")
    show_rows(
        connection,
        """
        SELECT name, type
        FROM sqlite_master
        WHERE type IN ('table', 'index')
        ORDER BY type, name
        """,
    )

    print("\nForeign keys for orders:")
    show_rows(connection, "PRAGMA foreign_key_list(orders)")

    print("\nIndexes for customers:")
    show_rows(connection, "PRAGMA index_list(customers)")


# ---------------------------------------------------------------------------
# 11. APPLICATION VALIDATION VERSUS DATABASE ENFORCEMENT
# ---------------------------------------------------------------------------

@dataclass
class CustomerInput:
    email: str
    full_name: str
    age: int


def validate_customer_in_application(data: CustomerInput) -> list[str]:
    """
    Application validation improves user feedback.

    It is not a replacement for database constraints because another process,
    API endpoint, script, worker, or future version of the application can
    bypass this function.
    """
    errors: list[str] = []

    if not data.email.strip():
        errors.append("Email is required.")

    if "@" not in data.email:
        errors.append("Email must contain '@'.")

    if not data.full_name.strip():
        errors.append("Full name is required.")

    if data.age < 18:
        errors.append("Customer must be at least 18.")

    return errors


def demonstrate_validation_layers(connection: sqlite3.Connection) -> None:
    subsection("Application validation and database enforcement")

    candidate = CustomerInput(
        email="invalid-email",
        full_name="",
        age=15,
    )

    errors = validate_customer_in_application(candidate)
    print("Application validation errors:")
    for error in errors:
        print(" -", error)

    """
    Two validation layers serve different purposes:

    Application layer:
        Better error messages, formatting, user experience, early rejection.

    Database layer:
        Authoritative protection of stored data and enforcement across clients.

    Important business invariants should not exist only in UI or application
    validation.
    """

    valid_candidate = CustomerInput(
        email="diana@example.com",
        full_name="Diana",
        age=28,
    )

    connection.execute(
        """
        INSERT INTO customers (customer_id, email, full_name, age)
        VALUES (?, ?, ?, ?)
        """,
        (
            3,
            valid_candidate.email,
            valid_candidate.full_name,
            valid_candidate.age,
        ),
    )

    print("Valid customer inserted after application validation.")


# ---------------------------------------------------------------------------
# 12. ERROR HANDLING
# ---------------------------------------------------------------------------

def classify_integrity_error(error: sqlite3.IntegrityError) -> str:
    """
    SQLite's Python driver exposes the underlying database error text.
    More sophisticated applications can also inspect extended error codes
    where supported by the database driver/version.

    In portable applications, do not depend exclusively on error-message
    strings because exact wording can differ between database engines.
    """
    message = str(error).lower()

    if "unique" in message:
        return "UNIQUE constraint violation"
    if "not null" in message:
        return "NOT NULL constraint violation"
    if "check" in message:
        return "CHECK constraint violation"
    if "foreign key" in message:
        return "FOREIGN KEY constraint violation"
    if "primary key" in message:
        return "PRIMARY KEY constraint violation"

    return "Other integrity violation"


def demonstrate_error_classification(connection: sqlite3.Connection) -> None:
    subsection("Constraint-aware error handling")

    try:
        connection.execute(
            """
            INSERT INTO customers
                (customer_id, email, full_name, age)
            VALUES (1, 'duplicate@example.com', 'Duplicate', 30)
            """
        )
    except sqlite3.IntegrityError as error:
        print(classify_integrity_error(error))


# ---------------------------------------------------------------------------
# 13. TESTING CONSTRAINTS
# ---------------------------------------------------------------------------

def expect_integrity_error(
    connection: sqlite3.Connection,
    operation: Callable[[], Any],
    expected_description: str,
) -> None:
    """Small testing helper used to verify that an invalid operation fails."""
    try:
        operation()
    except sqlite3.IntegrityError:
        print(f"PASS: {expected_description}")
    else:
        print(f"FAIL: {expected_description}")


def run_constraint_tests() -> None:
    subsection("Executable constraint tests")

    connection = connect_database()
    create_basic_schema(connection)

    connection.execute(
        """
        INSERT INTO customers (customer_id, email, full_name, age)
        VALUES (1, 'test@example.com', 'Test User', 25)
        """
    )

    expect_integrity_error(
        connection,
        lambda: connection.execute(
            """
            INSERT INTO customers
                (customer_id, email, full_name, age)
            VALUES (2, 'test@example.com', 'Duplicate Email', 25)
            """
        ),
        "UNIQUE email rule rejects duplicate values",
    )

    expect_integrity_error(
        connection,
        lambda: connection.execute(
            """
            INSERT INTO customers
                (customer_id, email, full_name, age)
            VALUES (2, 'new@example.com', 'Underage', 17)
            """
        ),
        "CHECK rule rejects an invalid age",
    )

    expect_integrity_error(
        connection,
        lambda: connection.execute(
            """
            INSERT INTO orders (order_id, customer_id, amount_cents)
            VALUES (2, 999, 500)
            """
        ),
        "FOREIGN KEY rule rejects a nonexistent customer",
    )

    expect_integrity_error(
        connection,
        lambda: connection.execute(
            """
            INSERT INTO orders (order_id, customer_id, amount_cents)
            VALUES (2, 1, -1)
            """
        ),
        "CHECK rule rejects a negative order amount",
    )


# ---------------------------------------------------------------------------
# 14. CONSTRAINT DESIGN COMPARISONS
# ---------------------------------------------------------------------------

def print_design_comparisons() -> None:
    subsection("Important design comparisons")

    comparisons = {
        "NOT NULL vs CHECK":
            "NOT NULL specifically prevents NULL; CHECK expresses a logical rule.",
        "PRIMARY KEY vs UNIQUE":
            "A primary key identifies the row; UNIQUE enforces uniqueness for a column or column set.",
        "FOREIGN KEY vs application lookup":
            "A foreign key is authoritative database enforcement; an application lookup alone can race or be bypassed.",
        "CHECK vs application validation":
            "CHECK protects persisted data; application validation can provide richer user feedback.",
        "CASCADE vs RESTRICT":
            "CASCADE propagates changes; RESTRICT prevents changes when dependent data exists.",
        "Constraint vs index":
            "A constraint represents an integrity rule; an index primarily supports lookup and uniqueness enforcement.",
        "Immediate vs deferred":
            "Immediate constraints are checked during the modifying statement; deferred constraints can wait until transaction commit.",
    }

    for topic, explanation in comparisons.items():
        print(f"{topic}: {explanation}")


# ---------------------------------------------------------------------------
# 15. PERFORMANCE AND PRODUCTION CONSIDERATIONS
# ---------------------------------------------------------------------------

def demonstrate_query_plan(connection: sqlite3.Connection) -> None:
    subsection("Performance consideration: indexes supporting integrity")

    connection.execute(
        """
        CREATE TABLE audit_events (
            event_id INTEGER PRIMARY KEY,
            event_key TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL
                CHECK (event_type IN ('login', 'logout', 'payment'))
        )
        """
    )

    connection.executemany(
        """
        INSERT INTO audit_events (event_id, event_key, event_type)
        VALUES (?, ?, ?)
        """,
        [
            (1, "EVT-001", "login"),
            (2, "EVT-002", "payment"),
            (3, "EVT-003", "logout"),
        ],
    )

    show_rows(
        connection,
        "EXPLAIN QUERY PLAN SELECT * FROM audit_events WHERE event_key = 'EVT-002'",
    )

    """
    UNIQUE constraints commonly require an index internally. Indexes can make
    uniqueness checks efficient, but every additional index also increases
    write and storage costs.

    Production schema design should balance:
    - correctness
    - query performance
    - insert/update cost
    - storage
    - operational complexity
    """


# ---------------------------------------------------------------------------
# 16. COMMON MISTAKES
# ---------------------------------------------------------------------------

def print_common_mistakes() -> None:
    subsection("Common mistakes")

    mistakes = [
        "Treating client-side validation as the only integrity mechanism.",
        "Forgetting to enable SQLite foreign-key enforcement.",
        "Using nullable columns when a business invariant requires a value.",
        "Writing a CHECK expression without understanding NULL/UNKNOWN behavior.",
        "Using CASCADE without considering whether dependent historical data may need preservation.",
        "Assuming a UNIQUE constraint means only one NULL is always allowed across every database engine.",
        "Ignoring transaction boundaries around multi-step business operations.",
        "Creating too many indexes and increasing write cost unnecessarily.",
        "Relying on database error-message text as a portable API contract.",
        "Assuming constraints alone solve all business rules, especially rules involving multiple rows, external systems, or time.",
        "Failing to test invalid as well as valid inputs.",
        "Changing production constraints without considering existing data and migration strategy.",
    ]

    for number, mistake in enumerate(mistakes, start=1):
        print(f"{number}. {mistake}")


# ---------------------------------------------------------------------------
# 17. LIMITATIONS AND ADVANCED BUSINESS RULES
# ---------------------------------------------------------------------------

def explain_constraint_boundaries() -> None:
    subsection("Where constraints have boundaries")

    """
    Constraints are powerful but not universal.

    A simple CHECK is excellent for row-local invariants:

        price_cents >= 0

    A UNIQUE rule is excellent for uniqueness.

    A FOREIGN KEY is excellent for referential integrity.

    More complicated rules can require:
    - transactions
    - triggers
    - stored procedures
    - exclusion/range constraints in engines that support them
    - application workflows
    - serialization/locking
    - carefully designed schemas

    Example rule:
        "A room cannot have overlapping reservations."

    A simple UNIQUE(room_id, date, start_time) does not fully prevent overlap.
    Preventing overlap may require stronger database-specific mechanisms or
    transactional application logic.

    Another example:
        "A customer's total exposure across multiple accounts must not exceed
        a regulatory limit."

    This is a cross-row aggregate invariant and requires more than a simple
    row-level CHECK.
    """

    print("Row-level constraints are strongest for local, declarative invariants.")
    print("Cross-row and temporal rules often require transactions or advanced mechanisms.")


# ---------------------------------------------------------------------------
# 18. COMPLETE STUDY DEMONSTRATION
# ---------------------------------------------------------------------------

def main() -> None:
    print("CONSTRAINTS, DATA INTEGRITY, AND CONSTRAINT ENFORCEMENT")
    print("Python + SQLite standalone technical study")

    connection = connect_database()

    section("1. Fundamental constraint types")
    create_basic_schema(connection)
    demonstrate_basic_constraints(connection)

    section("2. Data integrity")
    demonstrate_integrity_dimensions(connection)

    section("3. Composite constraints")
    demonstrate_composite_constraints(connection)

    section("4. NULL and SQL three-valued logic")
    demonstrate_null_semantics(connection)

    section("5. Referential integrity")
    demonstrate_referential_actions(connection)

    section("6. Transactions and atomicity")
    demonstrate_transactions(connection)

    section("7. Conditional uniqueness")
    demonstrate_partial_unique_index(connection)

    section("8. Deferred enforcement")
    demonstrate_deferred_foreign_key()

    section("9. Schema introspection")
    demonstrate_schema_inspection(connection)

    section("10. Validation layers")
    demonstrate_validation_layers(connection)

    section("11. Error classification")
    demonstrate_error_classification(connection)

    section("12. Automated testing")
    run_constraint_tests()

    section("13. Design comparisons")
    print_design_comparisons()

    section("14. Performance")
    demonstrate_query_plan(connection)

    section("15. Common mistakes")
    print_common_mistakes()

    section("16. Constraint boundaries")
    explain_constraint_boundaries()

    connection.close()

    print("\nStudy execution completed successfully.")


if __name__ == "__main__":
    main()
