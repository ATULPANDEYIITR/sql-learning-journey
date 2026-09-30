#!/usr/bin/env python3
"""
UNIQUE and CHECK Constraints
============================

A self-contained executable study of:
- UNIQUE constraints
- CHECK constraints
- database-style business rules
- composite uniqueness
- nullable uniqueness semantics
- validation ordering
- constraint violations
- transaction-like validation
- schema introspection
- concurrency-oriented considerations
- migration and production design

The implementation uses only the Python standard library. SQLite is used
because it provides real UNIQUE and CHECK constraint enforcement without
requiring an external database server.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable


DATABASE_FILE = Path("unique_check_demo.sqlite3")


def heading(title: str) -> None:
    print(f"\n{'=' * 78}")
    print(title)
    print("=" * 78)


def show_rows(connection: sqlite3.Connection, sql: str, parameters: tuple[Any, ...] = ()) -> None:
    cursor = connection.execute(sql, parameters)
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    print(" | ".join(columns))
    print("-" * max(20, len(" | ".join(columns))))

    for row in rows:
        print(" | ".join(str(value) for value in row))


def create_database(connection: sqlite3.Connection) -> None:
    """
    Create a small commerce schema.

    UNIQUE handles identity-like duplication:
      - email must be unique
      - SKU must be unique
      - a product name is unique within a category

    CHECK handles value validity:
      - price cannot be negative
      - stock cannot be negative
      - status must be one of the supported values
      - discount percentage must be within its valid range
      - an order total must be non-negative
    """
    connection.execute("PRAGMA foreign_keys = ON")

    connection.executescript(
        """
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL CHECK (length(trim(display_name)) >= 2),
            account_status TEXT NOT NULL
                CHECK (account_status IN ('active', 'suspended', 'closed')),
            credit_limit NUMERIC NOT NULL
                CHECK (credit_limit >= 0),
            created_at TEXT NOT NULL
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            category TEXT NOT NULL,
            sku TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            price NUMERIC NOT NULL CHECK (price >= 0),
            stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
            discount_percent NUMERIC NOT NULL DEFAULT 0
                CHECK (discount_percent >= 0 AND discount_percent <= 100),
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive')),
            UNIQUE (category, product_name)
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_reference TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL
                CHECK (status IN ('pending', 'paid', 'cancelled', 'fulfilled')),
            total_amount NUMERIC NOT NULL
                CHECK (total_amount >= 0),
            created_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price NUMERIC NOT NULL CHECK (unit_price >= 0),
            UNIQUE (order_id, product_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """
    )


def demonstrate_basic_unique(connection: sqlite3.Connection) -> None:
    heading("UNIQUE: preventing duplicate identity values")

    timestamp = datetime.now().isoformat(timespec="seconds")

    connection.execute(
        """
        INSERT INTO customers
            (email, display_name, account_status, credit_limit, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("alice@example.com", "Alice", "active", 5000, timestamp),
    )

    try:
        connection.execute(
            """
            INSERT INTO customers
                (email, display_name, account_status, credit_limit, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("alice@example.com", "Alice Duplicate", "active", 3000, timestamp),
        )
    except sqlite3.IntegrityError as exc:
        print(f"Duplicate email rejected by UNIQUE: {exc}")

    show_rows(
        connection,
        """
        SELECT customer_id, email, display_name, account_status
        FROM customers
        """,
    )


def demonstrate_composite_unique(connection: sqlite3.Connection) -> None:
    heading("COMPOSITE UNIQUE: uniqueness across a combination of columns")

    connection.executemany(
        """
        INSERT INTO products
            (category, sku, product_name, price, stock_quantity, discount_percent)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("Laptop", "LAP-001", "Pro 14", 129999, 8, 5),
            ("Laptop", "LAP-002", "Air 13", 89999, 15, 0),
            ("Phone", "PHN-001", "Pro 14", 79999, 20, 10),
        ],
    )

    print("The same product name is allowed in different categories.")
    show_rows(
        connection,
        """
        SELECT category, product_name, sku
        FROM products
        ORDER BY category
        """,
    )

    try:
        connection.execute(
            """
            INSERT INTO products
                (category, sku, product_name, price, stock_quantity, discount_percent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Laptop", "LAP-003", "Pro 14", 139999, 5, 0),
        )
    except sqlite3.IntegrityError as exc:
        print(f"Duplicate category/product-name pair rejected: {exc}")


def demonstrate_check_constraints(connection: sqlite3.Connection) -> None:
    heading("CHECK: enforcing valid value domains")

    invalid_products = [
        (
            "Monitor",
            "MON-001",
            "UltraView",
            -500,
            10,
            0,
        ),
        (
            "Keyboard",
            "KEY-001",
            "Mechanical",
            5000,
            -2,
            0,
        ),
        (
            "Mouse",
            "MOU-001",
            "Precision",
            2500,
            10,
            101,
        ),
    ]

    for product in invalid_products:
        try:
            connection.execute(
                """
                INSERT INTO products
                    (category, sku, product_name, price, stock_quantity, discount_percent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                product,
            )
        except sqlite3.IntegrityError as exc:
            print(f"CHECK rejected {product[2]!r}: {exc}")


def demonstrate_status_check(connection: sqlite3.Connection) -> None:
    heading("CHECK: enumerated business states")

    timestamp = datetime.now().isoformat(timespec="seconds")

    try:
        connection.execute(
            """
            INSERT INTO customers
                (email, display_name, account_status, credit_limit, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("bob@example.com", "Bob", "pending-review", 1000, timestamp),
        )
    except sqlite3.IntegrityError as exc:
        print(f"Unsupported account status rejected: {exc}")

    connection.execute(
        """
        INSERT INTO customers
            (email, display_name, account_status, credit_limit, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("bob@example.com", "Bob", "active", 1000, timestamp),
    )


def demonstrate_application_validation(connection: sqlite3.Connection) -> None:
    heading("APPLICATION VALIDATION VS DATABASE ENFORCEMENT")

    """
    Application validation improves user experience, but it is not a
    substitute for database constraints.

    Two application processes can both validate an email as available and
    then race to insert it. The database UNIQUE constraint is the final
    concurrency-safe authority.
    """

    def normalize_email(email: str) -> str:
        return email.strip().lower()

    def application_validate_customer(email: str, name: str) -> list[str]:
        errors: list[str] = []

        normalized_email = normalize_email(email)

        if "@" not in normalized_email:
            errors.append("email must contain @")

        if len(name.strip()) < 2:
            errors.append("display name must contain at least two characters")

        existing = connection.execute(
            "SELECT 1 FROM customers WHERE email = ?",
            (normalized_email,),
        ).fetchone()

        if existing:
            errors.append("email already exists")

        return errors

    email = " charlie@example.com "
    name = "Charlie"

    errors = application_validate_customer(email, name)
    print(f"Application validation result: {errors or 'valid'}")

    if not errors:
        timestamp = datetime.now().isoformat(timespec="seconds")
        try:
            connection.execute(
                """
                INSERT INTO customers
                    (email, display_name, account_status, credit_limit, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (normalize_email(email), name.strip(), "active", 2500, timestamp),
            )
        except sqlite3.IntegrityError as exc:
            print(f"Database remained authoritative: {exc}")


def demonstrate_transaction(connection: sqlite3.Connection) -> None:
    heading("TRANSACTIONS: validating a group of related constraints")

    timestamp = datetime.now().isoformat(timespec="seconds")

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO customers
                    (email, display_name, account_status, credit_limit, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("transaction@example.com", "Transaction User", "active", 5000, timestamp),
            )

            customer_id = connection.execute(
                "SELECT customer_id FROM customers WHERE email = ?",
                ("transaction@example.com",),
            ).fetchone()[0]

            connection.execute(
                """
                INSERT INTO orders
                    (customer_id, order_reference, status, total_amount, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (customer_id, "ORD-1001", "pending", 1500, timestamp),
            )

            # This violates CHECK(total_amount >= 0), so the transaction
            # is rolled back rather than leaving half-created business data.
            connection.execute(
                """
                INSERT INTO orders
                    (customer_id, order_reference, status, total_amount, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (customer_id, "ORD-1002", "pending", -100, timestamp),
            )
    except sqlite3.IntegrityError as exc:
        print(f"Transaction rejected and rolled back: {exc}")

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE order_reference IN ('ORD-1001', 'ORD-1002')
        """
    ).fetchone()[0]

    print(f"Orders remaining after rollback: {count}")


def demonstrate_order_item_rules(connection: sqlite3.Connection) -> None:
    heading("BUSINESS RULES ACROSS ORDER ITEMS")

    timestamp = datetime.now().isoformat(timespec="seconds")

    customer_id = connection.execute(
        "SELECT customer_id FROM customers WHERE email = ?",
        ("alice@example.com",),
    ).fetchone()[0]

    product_id = connection.execute(
        "SELECT product_id FROM products WHERE sku = ?",
        ("LAP-001",),
    ).fetchone()[0]

    connection.execute(
        """
        INSERT INTO orders
            (customer_id, order_reference, status, total_amount, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (customer_id, "ORD-2001", "pending", 259998, timestamp),
    )

    order_id = connection.execute(
        "SELECT order_id FROM orders WHERE order_reference = ?",
        ("ORD-2001",),
    ).fetchone()[0]

    connection.execute(
        """
        INSERT INTO order_items
            (order_id, product_id, quantity, unit_price)
        VALUES (?, ?, ?, ?)
        """,
        (order_id, product_id, 2, 129999),
    )

    try:
        connection.execute(
            """
            INSERT INTO order_items
                (order_id, product_id, quantity, unit_price)
            VALUES (?, ?, ?, ?)
            """,
            (order_id, product_id, 1, 129999),
        )
    except sqlite3.IntegrityError as exc:
        print(f"Duplicate product within the same order rejected: {exc}")

    try:
        connection.execute(
            """
            INSERT INTO order_items
                (order_id, product_id, quantity, unit_price)
            VALUES (?, ?, ?, ?)
            """,
            (order_id, product_id, 0, 129999),
        )
    except sqlite3.IntegrityError as exc:
        print(f"Invalid quantity rejected: {exc}")


def inspect_constraints(connection: sqlite3.Connection) -> None:
    heading("SCHEMA INTROSPECTION")

    tables = ["customers", "products", "orders", "order_items"]

    for table in tables:
        print(f"\n{table}")
        columns = connection.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        for column in columns:
            print(
                f"  column={column[1]!r}, "
                f"type={column[2]!r}, "
                f"not_null={bool(column[3])}, "
                f"default={column[4]!r}"
            )

        indexes = connection.execute(
            f"PRAGMA index_list({table})"
        ).fetchall()

        for index in indexes:
            index_name = index[1]
            unique = bool(index[2])
            print(f"  index={index_name!r}, unique={unique}")

            index_columns = connection.execute(
                f"PRAGMA index_info('{index_name}')"
            ).fetchall()

            print(
                "    columns="
                + ", ".join(str(item[2]) for item in index_columns)
            )


def demonstrate_edge_cases(connection: sqlite3.Connection) -> None:
    heading("EDGE CASES AND SEMANTIC DETAILS")

    print(
        "SQLite allows multiple NULL values in a UNIQUE column because NULL "
        "represents an unknown value rather than a duplicate concrete value."
    )

    connection.execute("DROP TABLE IF EXISTS nullable_demo")

    connection.execute(
        """
        CREATE TABLE nullable_demo (
            id INTEGER PRIMARY KEY,
            external_reference TEXT UNIQUE
        )
        """
    )

    connection.executemany(
        "INSERT INTO nullable_demo (external_reference) VALUES (?)",
        [(None,), (None,), ("REF-001",)],
    )

    show_rows(
        connection,
        "SELECT id, external_reference FROM nullable_demo ORDER BY id",
    )

    try:
        connection.execute(
            """
            INSERT INTO nullable_demo (external_reference)
            VALUES (?)
            """,
            ("REF-001",),
        )
    except sqlite3.IntegrityError as exc:
        print(f"Duplicate non-NULL reference rejected: {exc}")

    print(
        "\nIf a business rule requires every record to have a unique reference, "
        "combine NOT NULL with UNIQUE."
    )


def demonstrate_partial_index(connection: sqlite3.Connection) -> None:
    heading("CONDITIONAL UNIQUENESS WITH A PARTIAL UNIQUE INDEX")

    connection.execute("DROP TABLE IF EXISTS user_aliases")

    connection.execute(
        """
        CREATE TABLE user_aliases (
            alias_id INTEGER PRIMARY KEY,
            alias TEXT NOT NULL,
            active INTEGER NOT NULL CHECK (active IN (0, 1))
        )
        """
    )

    connection.execute(
        """
        CREATE UNIQUE INDEX ux_active_alias
        ON user_aliases(alias)
        WHERE active = 1
        """
    )

    connection.executemany(
        "INSERT INTO user_aliases (alias, active) VALUES (?, ?)",
        [
            ("alpha", 0),
            ("alpha", 0),
            ("beta", 1),
        ],
    )

    print("Inactive aliases may repeat because the uniqueness rule applies only to active rows.")

    try:
        connection.execute(
            "INSERT INTO user_aliases (alias, active) VALUES (?, ?)",
            ("beta", 1),
        )
    except sqlite3.IntegrityError as exc:
        print(f"Active alias collision rejected: {exc}")

    show_rows(
        connection,
        "SELECT alias_id, alias, active FROM user_aliases ORDER BY alias_id",
    )


def demonstrate_business_rule_boundaries(connection: sqlite3.Connection) -> None:
    heading("WHERE CHECK CONSTRAINTS STOP")

    """
    A CHECK constraint is excellent for rules involving the current row.

    Examples:
      price >= 0
      quantity > 0
      discount_percent BETWEEN 0 AND 100

    More complex rules may depend on another row, aggregation, external
    systems, or changing state. Those usually require a transaction,
    trigger, application service, or another database mechanism.

    The example below computes order totals from order items in application
    code and then persists the resulting value inside one transaction.
    """

    order_id = connection.execute(
        "SELECT order_id FROM orders WHERE order_reference = ?",
        ("ORD-2001",),
    ).fetchone()[0]

    calculated_total = connection.execute(
        """
        SELECT COALESCE(SUM(quantity * unit_price), 0)
        FROM order_items
        WHERE order_id = ?
        """,
        (order_id,),
    ).fetchone()[0]

    stored_total = connection.execute(
        """
        SELECT total_amount
        FROM orders
        WHERE order_id = ?
        """,
        (order_id,),
    ).fetchone()[0]

    print(f"Calculated item total: {calculated_total}")
    print(f"Stored order total:    {stored_total}")
    print(
        "A row-level CHECK can guarantee that total_amount is non-negative, "
        "but it does not by itself calculate SUM(order_items)."
    )


def demonstrate_safe_dynamic_sql() -> None:
    heading("SECURITY: CONSTRAINTS DO NOT REPLACE PARAMETERIZED SQL")

    print(
        "UNIQUE and CHECK protect database invariants, but SQL injection "
        "prevention still requires parameterized statements."
    )

    print(
        "Use connection.execute('... WHERE email = ?', (email,)) rather than "
        "concatenating untrusted values into SQL."
    )


@dataclass(frozen=True)
class ProductInput:
    category: str
    sku: str
    name: str
    price: Decimal
    stock: int
    discount_percent: Decimal


def validate_product_before_database(product: ProductInput) -> list[str]:
    """
    Application-level validation provides fast and readable feedback before
    attempting the database write. It intentionally mirrors, but does not
    replace, database constraints.
    """
    errors: list[str] = []

    if not product.category.strip():
        errors.append("category is required")

    if not product.sku.strip():
        errors.append("SKU is required")

    if not product.name.strip():
        errors.append("product name is required")

    if product.price < Decimal("0"):
        errors.append("price cannot be negative")

    if product.stock < 0:
        errors.append("stock cannot be negative")

    if not Decimal("0") <= product.discount_percent <= Decimal("100"):
        errors.append("discount must be between 0 and 100")

    return errors


def demonstrate_layered_validation() -> None:
    heading("LAYERED VALIDATION")

    candidates = [
        ProductInput(
            "Storage",
            "SSD-001",
            "1 TB SSD",
            Decimal("6499"),
            20,
            Decimal("10"),
        ),
        ProductInput(
            "Storage",
            "",
            "Invalid SSD",
            Decimal("-50"),
            -1,
            Decimal("120"),
        ),
    ]

    for candidate in candidates:
        errors = validate_product_before_database(candidate)
        if errors:
            print(f"{candidate.name!r}: rejected before database write")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"{candidate.name!r}: application validation passed")


def demonstrate_constraint_error_classification(connection: sqlite3.Connection) -> None:
    heading("ERROR HANDLING: CONSTRAINT VIOLATIONS ARE DATA EVENTS")

    cases = [
        (
            "duplicate email",
            """
            INSERT INTO customers
                (email, display_name, account_status, credit_limit, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "alice@example.com",
                "Another Alice",
                "active",
                1000,
                datetime.now().isoformat(timespec="seconds"),
            ),
        ),
        (
            "negative credit limit",
            """
            INSERT INTO customers
                (email, display_name, account_status, credit_limit, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "constraint@example.com",
                "Constraint User",
                "active",
                -1,
                datetime.now().isoformat(timespec="seconds"),
            ),
        ),
    ]

    for description, sql, parameters in cases:
        try:
            connection.execute(sql, parameters)
        except sqlite3.IntegrityError as exc:
            print(f"{description}: IntegrityError -> {exc}")


def build_in_memory_demo() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    create_database(connection)
    return connection


def main() -> None:
    print("UNIQUE and CHECK Constraint Laboratory")
    print("Database:", DATABASE_FILE.resolve())

    connection = build_in_memory_demo()

    try:
        demonstrate_basic_unique(connection)
        demonstrate_composite_unique(connection)
        demonstrate_check_constraints(connection)
        demonstrate_status_check(connection)
        demonstrate_application_validation(connection)
        demonstrate_transaction(connection)
        demonstrate_order_item_rules(connection)
        inspect_constraints(connection)
        demonstrate_edge_cases(connection)
        demonstrate_partial_index(connection)
        demonstrate_business_rule_boundaries(connection)
        demonstrate_safe_dynamic_sql()
        demonstrate_layered_validation()
        demonstrate_constraint_error_classification(connection)

        heading("FINAL DATA SNAPSHOT")

        show_rows(
            connection,
            """
            SELECT customer_id, email, account_status, credit_limit
            FROM customers
            ORDER BY customer_id
            """,
        )

        print("\nProducts:")
        show_rows(
            connection,
            """
            SELECT category, sku, product_name, price, stock_quantity,
                   discount_percent, status
            FROM products
            ORDER BY category, product_name
            """,
        )

        print(
            "\nThe central design principle demonstrated by this program is "
            "defense in depth: application validation improves feedback, "
            "while database constraints enforce durable data invariants."
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
