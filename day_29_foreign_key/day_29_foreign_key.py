"""
FOREIGN KEY: Referential Integrity, Parent-Child Relationships, and Cascading Actions

A self-contained educational Python program using SQLite to demonstrate:
- Primary keys and foreign keys
- Parent-child relationships
- Referential integrity
- Foreign-key enforcement
- INSERT, UPDATE, and DELETE behavior
- ON DELETE and ON UPDATE actions
- CASCADE, RESTRICT, NO ACTION, SET NULL, and SET DEFAULT
- Composite foreign keys
- Multiple child tables
- Optional relationships
- Self-referencing foreign keys
- Transaction handling
- Constraint failures and rollback
- Schema inspection
- Validation and testing
- Practical database design and performance considerations

SQLite is part of Python's standard library, so no external package is required.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


DATABASE_NAME = ":memory:"


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def subsection(title: str) -> None:
    print(f"\n--- {title} ---")


def show_rows(connection: sqlite3.Connection, query: str, parameters: tuple = ()) -> None:
    cursor = connection.execute(query, parameters)
    rows = cursor.fetchall()

    if not rows:
        print("(no rows)")
        return

    print(" | ".join(row.keys() for row in [])) if False else None
    print(" | ".join(rows[0].keys()))
    print("-" * 78)

    for row in rows:
        print(" | ".join(str(value) if value is not None else "NULL" for value in row))


def explain_constraint_error(operation: str, error: sqlite3.IntegrityError) -> None:
    print(f"{operation} failed as expected.")
    print(f"SQLite reported: {error}")


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """
    A transaction groups multiple changes into one atomic operation.

    If an exception occurs, the changes are rolled back. Otherwise they
    are committed. This is particularly important when a parent change
    triggers multiple child-row changes through cascading actions.
    """
    try:
        connection.execute("BEGIN")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def create_connection() -> sqlite3.Connection:
    """
    Create a SQLite connection and explicitly enable foreign-key enforcement.

    SQLite accepts FOREIGN KEY syntax in table definitions, but enforcement
    must be enabled for each connection with PRAGMA foreign_keys = ON.
    """
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_basic_schema(connection: sqlite3.Connection) -> None:
    """
    Basic one-to-many relationship:

        customers (parent)
            |
            +---- orders (children)

    ON DELETE RESTRICT means a customer cannot be deleted while orders
    still reference that customer.
    """
    connection.executescript(
        """
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_total REAL NOT NULL CHECK (order_total >= 0),

            FOREIGN KEY (customer_id)
                REFERENCES customers(customer_id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE
        );
        """
    )


def demonstrate_basic_relationship(connection: sqlite3.Connection) -> None:
    section("1. Basic Parent-Child Relationship")

    create_basic_schema(connection)

    connection.executemany(
        "INSERT INTO customers(customer_id, name) VALUES (?, ?)",
        [
            (1, "Anika"),
            (2, "Rahul"),
        ],
    )

    connection.executemany(
        """
        INSERT INTO orders(order_id, customer_id, order_total)
        VALUES (?, ?, ?)
        """,
        [
            (101, 1, 1250.00),
            (102, 1, 800.00),
            (103, 2, 450.00),
        ],
    )

    subsection("Parent table")
    show_rows(connection, "SELECT * FROM customers ORDER BY customer_id")

    subsection("Child table")
    show_rows(connection, "SELECT * FROM orders ORDER BY order_id")

    subsection("Joining parent and child")
    show_rows(
        connection,
        """
        SELECT
            c.customer_id,
            c.name,
            o.order_id,
            o.order_total
        FROM customers AS c
        JOIN orders AS o
            ON o.customer_id = c.customer_id
        ORDER BY c.customer_id, o.order_id
        """,
    )


def demonstrate_invalid_child(connection: sqlite3.Connection) -> None:
    section("2. Referential Integrity: Invalid Child Reference")

    try:
        connection.execute(
            """
            INSERT INTO orders(order_id, customer_id, order_total)
            VALUES (?, ?, ?)
            """,
            (104, 999, 100.00),
        )
    except sqlite3.IntegrityError as error:
        explain_constraint_error("Inserting an order for customer_id=999", error)

    print(
        "Reason: the referenced parent row does not exist. "
        "The foreign key prevents an orphan child row."
    )


def demonstrate_restrict_delete(connection: sqlite3.Connection) -> None:
    section("3. ON DELETE RESTRICT")

    try:
        connection.execute(
            "DELETE FROM customers WHERE customer_id = ?",
            (1,),
        )
    except sqlite3.IntegrityError as error:
        explain_constraint_error(
            "Deleting customer 1 while orders still reference it",
            error,
        )

    print("The parent remains because dependent child rows still exist.")

    subsection("Delete the children first")
    connection.execute("DELETE FROM orders WHERE customer_id = ?", (1,))
    connection.execute("DELETE FROM customers WHERE customer_id = ?", (1,))

    show_rows(connection, "SELECT * FROM customers ORDER BY customer_id")
    show_rows(connection, "SELECT * FROM orders ORDER BY order_id")


def demonstrate_update_cascade(connection: sqlite3.Connection) -> None:
    section("4. ON UPDATE CASCADE")

    connection.execute(
        "INSERT INTO customers(customer_id, name) VALUES (?, ?)",
        (10, "Meera"),
    )
    connection.execute(
        """
        INSERT INTO orders(order_id, customer_id, order_total)
        VALUES (?, ?, ?)
        """,
        (200, 10, 900.00),
    )

    subsection("Before parent-key update")
    show_rows(
        connection,
        """
        SELECT c.customer_id, c.name, o.order_id, o.customer_id AS order_customer_id
        FROM customers c
        JOIN orders o ON o.customer_id = c.customer_id
        WHERE c.customer_id = 10
        """,
    )

    connection.execute(
        "UPDATE customers SET customer_id = ? WHERE customer_id = ?",
        (11, 10),
    )

    subsection("After parent-key update")
    show_rows(
        connection,
        """
        SELECT c.customer_id, c.name, o.order_id, o.customer_id AS order_customer_id
        FROM customers c
        JOIN orders o ON o.customer_id = c.customer_id
        WHERE c.customer_id = 11
        """,
    )

    print(
        "ON UPDATE CASCADE propagated the changed parent key into the child row."
    )


def create_cascade_schema(connection: sqlite3.Connection) -> None:
    section("5. ON DELETE CASCADE")

    connection.executescript(
        """
        DROP TABLE IF EXISTS payments;
        DROP TABLE IF EXISTS cascade_orders;
        DROP TABLE IF EXISTS cascade_customers;

        CREATE TABLE cascade_customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE cascade_orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,

            FOREIGN KEY (customer_id)
                REFERENCES cascade_customers(customer_id)
                ON DELETE CASCADE
        );

        CREATE TABLE payments (
            payment_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            amount REAL NOT NULL CHECK (amount >= 0),

            FOREIGN KEY (order_id)
                REFERENCES cascade_orders(order_id)
                ON DELETE CASCADE
        );
        """
    )

    connection.execute(
        "INSERT INTO cascade_customers(customer_id, name) VALUES (?, ?)",
        (1, "Cascade Customer"),
    )

    connection.execute(
        "INSERT INTO cascade_orders(order_id, customer_id) VALUES (?, ?)",
        (500, 1),
    )

    connection.execute(
        """
        INSERT INTO payments(payment_id, order_id, amount)
        VALUES (?, ?, ?)
        """,
        (900, 500, 500.00),
    )

    subsection("Before deleting the parent")
    show_rows(connection, "SELECT * FROM cascade_customers")
    show_rows(connection, "SELECT * FROM cascade_orders")
    show_rows(connection, "SELECT * FROM payments")

    connection.execute(
        "DELETE FROM cascade_customers WHERE customer_id = ?",
        (1,),
    )

    subsection("After deleting the parent")
    show_rows(connection, "SELECT * FROM cascade_customers")
    show_rows(connection, "SELECT * FROM cascade_orders")
    show_rows(connection, "SELECT * FROM payments")

    print(
        "The deletion propagated through both child levels because both "
        "foreign keys use ON DELETE CASCADE."
    )


def demonstrate_set_null(connection: sqlite3.Connection) -> None:
    section("6. ON DELETE SET NULL")

    connection.executescript(
        """
        DROP TABLE IF EXISTS employees;
        DROP TABLE IF EXISTS departments;

        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL
        );

        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            department_id INTEGER,

            FOREIGN KEY (department_id)
                REFERENCES departments(department_id)
                ON DELETE SET NULL
        );
        """
    )

    connection.execute(
        "INSERT INTO departments(department_id, department_name) VALUES (?, ?)",
        (1, "Research"),
    )

    connection.execute(
        """
        INSERT INTO employees(employee_id, employee_name, department_id)
        VALUES (?, ?, ?)
        """,
        (1, "Dev", 1),
    )

    print("Before department deletion:")
    show_rows(connection, "SELECT * FROM employees")

    connection.execute("DELETE FROM departments WHERE department_id = ?", (1,))

    print("After department deletion:")
    show_rows(connection, "SELECT * FROM employees")

    print(
        "The employee survives, but department_id becomes NULL. "
        "This is appropriate when the relationship is optional."
    )


def demonstrate_set_default(connection: sqlite3.Connection) -> None:
    section("7. ON DELETE SET DEFAULT")

    connection.executescript(
        """
        DROP TABLE IF EXISTS tickets;
        DROP TABLE IF EXISTS support_teams;

        CREATE TABLE support_teams (
            team_id INTEGER PRIMARY KEY,
            team_name TEXT NOT NULL
        );

        INSERT INTO support_teams(team_id, team_name)
        VALUES (0, 'Unassigned');

        CREATE TABLE tickets (
            ticket_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            team_id INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (team_id)
                REFERENCES support_teams(team_id)
                ON DELETE SET DEFAULT
        );
        """
    )

    connection.execute(
        "INSERT INTO support_teams(team_id, team_name) VALUES (?, ?)",
        (10, "Platform"),
    )

    connection.execute(
        "INSERT INTO tickets(ticket_id, title, team_id) VALUES (?, ?, ?)",
        (1, "Database incident", 10),
    )

    connection.execute("DELETE FROM support_teams WHERE team_id = ?", (10,))

    show_rows(connection, "SELECT * FROM tickets")

    print(
        "The child points to the valid default parent instead of becoming NULL."
    )


def demonstrate_no_action(connection: sqlite3.Connection) -> None:
    section("8. NO ACTION and RESTRICT")

    print(
        "NO ACTION and RESTRICT both prevent an invalid final database state, "
        "but their timing semantics can differ in databases that support "
        "deferred constraint checking. SQLite commonly reports the violation "
        "at the end of the relevant statement for immediate constraints."
    )

    connection.executescript(
        """
        DROP TABLE IF EXISTS no_action_child;
        DROP TABLE IF EXISTS no_action_parent;

        CREATE TABLE no_action_parent (
            parent_id INTEGER PRIMARY KEY
        );

        CREATE TABLE no_action_child (
            child_id INTEGER PRIMARY KEY,
            parent_id INTEGER NOT NULL,

            FOREIGN KEY (parent_id)
                REFERENCES no_action_parent(parent_id)
                ON DELETE NO ACTION
        );
        """
    )

    connection.execute(
        "INSERT INTO no_action_parent(parent_id) VALUES (?)",
        (1,),
    )
    connection.execute(
        "INSERT INTO no_action_child(child_id, parent_id) VALUES (?, ?)",
        (1, 1),
    )

    try:
        connection.execute(
            "DELETE FROM no_action_parent WHERE parent_id = ?",
            (1,),
        )
    except sqlite3.IntegrityError as error:
        explain_constraint_error("Deleting a referenced parent", error)


def demonstrate_composite_foreign_key(connection: sqlite3.Connection) -> None:
    section("9. Composite Foreign Keys")

    connection.executescript(
        """
        DROP TABLE IF EXISTS enrollment;
        DROP TABLE IF EXISTS course_offering;

        CREATE TABLE course_offering (
            course_code TEXT NOT NULL,
            semester TEXT NOT NULL,
            instructor TEXT NOT NULL,

            PRIMARY KEY (course_code, semester)
        );

        CREATE TABLE enrollment (
            enrollment_id INTEGER PRIMARY KEY,
            student_name TEXT NOT NULL,
            course_code TEXT NOT NULL,
            semester TEXT NOT NULL,

            FOREIGN KEY (course_code, semester)
                REFERENCES course_offering(course_code, semester)
        );
        """
    )

    connection.execute(
        """
        INSERT INTO course_offering(course_code, semester, instructor)
        VALUES (?, ?, ?)
        """,
        ("CS101", "2026-FALL", "Dr. Rao"),
    )

    connection.execute(
        """
        INSERT INTO enrollment(
            enrollment_id,
            student_name,
            course_code,
            semester
        )
        VALUES (?, ?, ?, ?)
        """,
        (1, "Arjun", "CS101", "2026-FALL"),
    )

    print("Valid composite reference:")
    show_rows(connection, "SELECT * FROM enrollment")

    try:
        connection.execute(
            """
            INSERT INTO enrollment(
                enrollment_id,
                student_name,
                course_code,
                semester
            )
            VALUES (?, ?, ?, ?)
            """,
            (2, "Nisha", "CS101", "2027-SPRING"),
        )
    except sqlite3.IntegrityError as error:
        explain_constraint_error(
            "Inserting an enrollment for a nonexistent course/semester pair",
            error,
        )


def demonstrate_self_reference(connection: sqlite3.Connection) -> None:
    section("10. Self-Referencing Foreign Key")

    connection.executescript(
        """
        DROP TABLE IF EXISTS organization;

        CREATE TABLE organization (
            employee_id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            manager_id INTEGER,

            FOREIGN KEY (manager_id)
                REFERENCES organization(employee_id)
                ON DELETE SET NULL
        );
        """
    )

    connection.executemany(
        """
        INSERT INTO organization(employee_id, employee_name, manager_id)
        VALUES (?, ?, ?)
        """,
        [
            (1, "CEO", None),
            (2, "Engineering Manager", 1),
            (3, "Developer", 2),
            (4, "Analyst", 2),
        ],
    )

    show_rows(
        connection,
        """
        SELECT
            employee.employee_name AS employee,
            manager.employee_name AS manager
        FROM organization AS employee
        LEFT JOIN organization AS manager
            ON employee.manager_id = manager.employee_id
        ORDER BY employee.employee_id
        """,
    )

    connection.execute(
        "DELETE FROM organization WHERE employee_id = ?",
        (2,),
    )

    print("After deleting the manager:")
    show_rows(connection, "SELECT * FROM organization ORDER BY employee_id")

    print(
        "Employees previously managed by employee 2 now have NULL manager_id."
    )


def demonstrate_multiple_children(connection: sqlite3.Connection) -> None:
    section("11. One Parent With Multiple Child Tables")

    connection.executescript(
        """
        DROP TABLE IF EXISTS reviews;
        DROP TABLE IF EXISTS addresses;
        DROP TABLE IF EXISTS accounts;

        CREATE TABLE accounts (
            account_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE
        );

        CREATE TABLE addresses (
            address_id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL,
            city TEXT NOT NULL,

            FOREIGN KEY (account_id)
                REFERENCES accounts(account_id)
                ON DELETE CASCADE
        );

        CREATE TABLE reviews (
            review_id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),

            FOREIGN KEY (account_id)
                REFERENCES accounts(account_id)
                ON DELETE CASCADE
        );
        """
    )

    connection.execute(
        "INSERT INTO accounts(account_id, username) VALUES (?, ?)",
        (1, "user001"),
    )
    connection.execute(
        "INSERT INTO addresses(address_id, account_id, city) VALUES (?, ?, ?)",
        (1, 1, "Lucknow"),
    )
    connection.execute(
        "INSERT INTO reviews(review_id, account_id, rating) VALUES (?, ?, ?)",
        (1, 1, 5),
    )

    print("All dependent records:")
    show_rows(connection, "SELECT * FROM addresses")
    show_rows(connection, "SELECT * FROM reviews")

    connection.execute("DELETE FROM accounts WHERE account_id = ?", (1,))

    print("After parent deletion:")
    show_rows(connection, "SELECT * FROM addresses")
    show_rows(connection, "SELECT * FROM reviews")


def demonstrate_schema_introspection(connection: sqlite3.Connection) -> None:
    section("12. Inspecting Foreign-Key Definitions")

    subsection("orders foreign keys")
    show_rows(connection, "PRAGMA foreign_key_list(orders)")

    subsection("Current foreign-key enforcement")
    show_rows(connection, "PRAGMA foreign_keys")


def demonstrate_transaction(connection: sqlite3.Connection) -> None:
    section("13. Transactions and Rollback")

    connection.executescript(
        """
        DROP TABLE IF EXISTS transaction_child;
        DROP TABLE IF EXISTS transaction_parent;

        CREATE TABLE transaction_parent (
            parent_id INTEGER PRIMARY KEY
        );

        CREATE TABLE transaction_child (
            child_id INTEGER PRIMARY KEY,
            parent_id INTEGER NOT NULL,

            FOREIGN KEY (parent_id)
                REFERENCES transaction_parent(parent_id)
        );
        """
    )

    try:
        with transaction(connection):
            connection.execute(
                "INSERT INTO transaction_parent(parent_id) VALUES (?)",
                (1,),
            )

            connection.execute(
                "INSERT INTO transaction_child(child_id, parent_id) VALUES (?, ?)",
                (1, 1),
            )

            # This statement fails because parent_id=999 does not exist.
            connection.execute(
                "INSERT INTO transaction_child(child_id, parent_id) VALUES (?, ?)",
                (2, 999),
            )
    except sqlite3.IntegrityError as error:
        print(f"Transaction failed: {error}")
        print("The entire transaction was rolled back.")

    show_rows(connection, "SELECT * FROM transaction_parent")
    show_rows(connection, "SELECT * FROM transaction_child")


def demonstrate_validation(connection: sqlite3.Connection) -> None:
    section("14. Application Validation vs Database Enforcement")

    print(
        "Application validation can improve user experience, but it should "
        "not replace database constraints."
    )

    connection.executescript(
        """
        DROP TABLE IF EXISTS validation_child;
        DROP TABLE IF EXISTS validation_parent;

        CREATE TABLE validation_parent (
            id INTEGER PRIMARY KEY
        );

        CREATE TABLE validation_child (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES validation_parent(id)
        );
        """
    )

    requested_parent_id = 42

    parent_exists = connection.execute(
        "SELECT 1 FROM validation_parent WHERE id = ?",
        (requested_parent_id,),
    ).fetchone()

    if parent_exists is None:
        print(
            f"Application-level validation rejected parent_id={requested_parent_id} "
            "before attempting the INSERT."
        )

    print(
        "The database constraint remains necessary because another client, "
        "process, transaction, or concurrent operation could bypass "
        "application-level validation."
    )


def demonstrate_indexing(connection: sqlite3.Connection) -> None:
    section("15. Indexing Foreign-Key Columns")

    connection.executescript(
        """
        DROP TABLE IF EXISTS indexed_orders;
        DROP TABLE IF EXISTS indexed_customers;

        CREATE TABLE indexed_customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE indexed_orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            amount REAL NOT NULL,

            FOREIGN KEY (customer_id)
                REFERENCES indexed_customers(customer_id)
                ON DELETE CASCADE
        );

        CREATE INDEX idx_indexed_orders_customer_id
            ON indexed_orders(customer_id);
        """
    )

    print(
        "The parent primary key is indexed automatically in typical relational "
        "designs. The child foreign-key column should often be indexed because "
        "joins, parent deletion checks, and parent updates may need to locate "
        "dependent child rows efficiently."
    )

    show_rows(
        connection,
        "PRAGMA index_list(indexed_orders)",
    )


def demonstrate_edge_cases(connection: sqlite3.Connection) -> None:
    section("16. Important Edge Cases")

    subsection("NULL foreign-key value")

    connection.executescript(
        """
        DROP TABLE IF EXISTS nullable_child;
        DROP TABLE IF EXISTS nullable_parent;

        CREATE TABLE nullable_parent (
            id INTEGER PRIMARY KEY
        );

        CREATE TABLE nullable_child (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER,

            FOREIGN KEY (parent_id)
                REFERENCES nullable_parent(id)
        );
        """
    )

    connection.execute(
        "INSERT INTO nullable_child(id, parent_id) VALUES (?, NULL)",
        (1,),
    )

    show_rows(connection, "SELECT * FROM nullable_child")

    print(
        "A NULL foreign-key value normally represents no relationship. "
        "It does not need to match a parent row."
    )

    subsection("NOT NULL changes the meaning")

    connection.executescript(
        """
        DROP TABLE IF EXISTS required_child;

        CREATE TABLE required_child (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER NOT NULL,

            FOREIGN KEY (parent_id)
                REFERENCES nullable_parent(id)
        );
        """
    )

    try:
        connection.execute(
            "INSERT INTO required_child(id, parent_id) VALUES (?, NULL)",
            (1,),
        )
    except sqlite3.IntegrityError as error:
        explain_constraint_error(
            "Inserting NULL into a NOT NULL foreign-key column",
            error,
        )


def demonstrate_bad_designs() -> None:
    section("17. Common Design Mistakes")

    mistakes = [
        (
            "Storing a parent name instead of its stable identifier",
            "Names can change and may not be unique.",
        ),
        (
            "Disabling foreign-key enforcement",
            "Orphaned child records can enter the database.",
        ),
        (
            "Using CASCADE without understanding business consequences",
            "Deleting one parent can remove a large dependent data graph.",
        ),
        (
            "Forgetting NOT NULL for mandatory relationships",
            "Rows may contain NULL when the business relationship is required.",
        ),
        (
            "Failing to index frequently used child foreign keys",
            "Joins and referential actions can become unnecessarily expensive.",
        ),
        (
            "Relying only on application validation",
            "Other clients can still violate the intended relationship.",
        ),
        (
            "Using natural keys without considering stability",
            "Changing a referenced key can require broader updates.",
        ),
    ]

    for mistake, consequence in mistakes:
        print(f"* {mistake}: {consequence}")


def run_tests() -> None:
    section("18. Automated Assertions")

    connection = create_connection()

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
                ON DELETE CASCADE
        );

        INSERT INTO parent(id) VALUES (1);
        INSERT INTO child(id, parent_id) VALUES (1, 1);
        """
    )

    child_count = connection.execute(
        "SELECT COUNT(*) FROM child WHERE parent_id = 1"
    ).fetchone()[0]

    assert child_count == 1

    try:
        connection.execute(
            "INSERT INTO child(id, parent_id) VALUES (?, ?)",
            (2, 999),
        )
        raise AssertionError("Invalid foreign-key insert unexpectedly succeeded.")
    except sqlite3.IntegrityError:
        pass

    connection.execute("DELETE FROM parent WHERE id = 1")

    remaining_children = connection.execute(
        "SELECT COUNT(*) FROM child"
    ).fetchone()[0]

    assert remaining_children == 0

    print("All foreign-key assertions passed.")

    connection.close()


def print_design_rules() -> None:
    section("19. Practical Foreign-Key Design Rules")

    rules = [
        "Create a stable primary key for the parent entity.",
        "Store the parent's key in the child table.",
        "Declare the relationship with FOREIGN KEY.",
        "Use NOT NULL when the relationship is mandatory.",
        "Use NULL when the relationship is genuinely optional.",
        "Choose ON DELETE behavior according to business semantics.",
        "Use CASCADE only when deleting children is truly intended.",
        "Use SET NULL when the child can validly survive without the parent.",
        "Use RESTRICT or NO ACTION when the parent must not disappear while referenced.",
        "Use SET DEFAULT only when the default parent is meaningful and valid.",
        "Consider ON UPDATE CASCADE when referenced keys are intentionally mutable.",
        "Index child foreign-key columns when they participate in joins or referential checks.",
        "Keep database constraints enabled in every production connection.",
        "Use transactions for multi-step operations.",
        "Test failure paths, not only successful operations.",
        "Inspect execution plans and actual workloads before making performance decisions.",
    ]

    for index, rule in enumerate(rules, start=1):
        print(f"{index:02d}. {rule}")


def main() -> None:
    connection = create_connection()

    try:
        demonstrate_basic_relationship(connection)
        demonstrate_invalid_child(connection)
        demonstrate_restrict_delete(connection)
        demonstrate_update_cascade(connection)
        demonstrate_cascade_schema = create_cascade_schema(connection)
        demonstrate_set_null(connection)
        demonstrate_set_default(connection)
        demonstrate_no_action(connection)
        demonstrate_composite_foreign_key(connection)
        demonstrate_self_reference(connection)
        demonstrate_multiple_children(connection)
        demonstrate_schema_introspection(connection)
        demonstrate_transaction(connection)
        demonstrate_validation(connection)
        demonstrate_indexing(connection)
        demonstrate_edge_cases(connection)
        demonstrate_bad_designs()
        print_design_rules()
    finally:
        connection.close()

    run_tests()

    section("20. Program Finished")
    print(
        "The examples demonstrated how foreign keys preserve relationships "
        "between parent and child rows and how cascading actions determine "
        "what happens when referenced parent rows change."
    )


if __name__ == "__main__":
    main()
