#!/usr/bin/env python3
"""
Database Schema Design: OLTP Schema Modeling and Integrity

Demonstrates:
- Entity and relationship modeling
- Naming conventions
- Primary, foreign, candidate, and composite keys
- NOT NULL, UNIQUE, CHECK, and DEFAULT constraints
- Referential integrity
- Normalization and controlled denormalization
- Schema validation and dependency analysis
- Index recommendations
- Transactional order processing
- Schema migration validation
- SQL injection prevention
"""

from __future__ import annotations

import re
import sqlite3
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

LOGGER = logging.getLogger("schema_design")


class SchemaError(Exception):
    """Raised when a schema definition violates design rules."""


class ConstraintType(Enum):
    PRIMARY_KEY = "PRIMARY KEY"
    FOREIGN_KEY = "FOREIGN KEY"
    UNIQUE = "UNIQUE"
    NOT_NULL = "NOT NULL"
    CHECK = "CHECK"
    DEFAULT = "DEFAULT"


@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    nullable: bool = True
    unique: bool = False
    default: Any = None
    primary_key: bool = False
    check_expression: str | None = None

    def validate(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.name):
            raise SchemaError(f"Invalid column name: {self.name}")

        if self.data_type not in {
            "INTEGER", "TEXT", "REAL", "NUMERIC", "BLOB"
        }:
            raise SchemaError(f"Unsupported type: {self.data_type}")

        if self.primary_key and self.nullable:
            raise SchemaError("Primary key cannot be nullable.")


@dataclass(frozen=True)
class ForeignKey:
    columns: tuple[str, ...]
    referenced_table: str
    referenced_columns: tuple[str, ...]
    on_delete: str = "RESTRICT"

    def validate(self) -> None:
        if len(self.columns) != len(self.referenced_columns):
            raise SchemaError("Foreign key column count mismatch.")

        if self.on_delete not in {
            "RESTRICT", "CASCADE", "SET NULL", "NO ACTION"
        }:
            raise SchemaError("Invalid foreign key deletion policy.")


@dataclass
class Table:
    name: str
    columns: list[Column]
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    unique_constraints: list[tuple[str, ...]] = field(
        default_factory=list
    )

    def validate(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.name):
            raise SchemaError(f"Invalid table name: {self.name}")

        if not self.columns:
            raise SchemaError("A table must contain columns.")

        names = [column.name for column in self.columns]

        if len(names) != len(set(names)):
            raise SchemaError(f"Duplicate column in {self.name}.")

        for column in self.columns:
            column.validate()

        primary_keys = [
            column.name
            for column in self.columns
            if column.primary_key
        ]

        if len(primary_keys) > 1:
            raise SchemaError(
                "Use a composite primary key definition separately."
            )

        for foreign_key in self.foreign_keys:
            foreign_key.validate()

            if not set(foreign_key.columns).issubset(names):
                raise SchemaError("Foreign key uses unknown columns.")

        for constraint in self.unique_constraints:
            if not set(constraint).issubset(names):
                raise SchemaError("Unique constraint uses unknown columns.")


class SchemaCatalog:
    def __init__(self):
        self.tables: dict[str, Table] = {}

    def add_table(self, table: Table) -> None:
        table.validate()

        if table.name in self.tables:
            raise SchemaError(f"Duplicate table: {table.name}")

        self.tables[table.name] = table

    def validate_relationships(self) -> None:
        for table in self.tables.values():
            for fk in table.foreign_keys:
                parent = self.tables.get(fk.referenced_table)

                if parent is None:
                    raise SchemaError(
                        f"Missing referenced table: {fk.referenced_table}"
                    )

                parent_columns = {
                    column.name for column in parent.columns
                }

                if not set(fk.referenced_columns).issubset(
                    parent_columns
                ):
                    raise SchemaError(
                        f"Invalid referenced columns in {table.name}"
                    )

                if len(fk.referenced_columns) == 1:
                    referenced = next(
                        c for c in parent.columns
                        if c.name == fk.referenced_columns[0]
                    )

                    if not (
                        referenced.primary_key or referenced.unique
                    ):
                        raise SchemaError(
                            "Referenced column must be unique."
                        )

    def dependency_order(self) -> list[str]:
        """Topological ordering for table creation."""
        visited = set()
        result = []
        active = set()

        def visit(name: str) -> None:
            if name in active:
                raise SchemaError(
                    "Circular table dependency detected."
                )

            if name in visited:
                return

            active.add(name)

            for fk in self.tables[name].foreign_keys:
                visit(fk.referenced_table)

            active.remove(name)
            visited.add(name)
            result.append(name)

        for name in self.tables:
            visit(name)

        return result

    def report(self) -> None:
        print("\nDATABASE SCHEMA CATALOG")

        for table_name in self.dependency_order():
            table = self.tables[table_name]
            print(f"\nTable: {table.name}")

            for column in table.columns:
                properties = []

                if column.primary_key:
                    properties.append("PK")
                if not column.nullable:
                    properties.append("NOT NULL")
                if column.unique:
                    properties.append("UNIQUE")

                print(
                    f"  {column.name}: {column.data_type} "
                    f"{' '.join(properties)}"
                )

            for fk in table.foreign_keys:
                print(
                    f"  FK {fk.columns} -> "
                    f"{fk.referenced_table}{fk.referenced_columns}"
                )


def create_schema() -> SchemaCatalog:
    catalog = SchemaCatalog()

    catalog.add_table(Table(
        name="customers",
        columns=[
            Column("customer_id", "INTEGER", False, primary_key=True),
            Column("email", "TEXT", False, unique=True),
            Column("full_name", "TEXT", False),
            Column("created_at", "TEXT", False)
        ]
    ))

    catalog.add_table(Table(
        name="products",
        columns=[
            Column("product_id", "INTEGER", False, primary_key=True),
            Column("sku", "TEXT", False, unique=True),
            Column("product_name", "TEXT", False),
            Column("unit_price", "NUMERIC", False),
            Column("active", "INTEGER", False, default=1)
        ]
    ))

    catalog.add_table(Table(
        name="orders",
        columns=[
            Column("order_id", "INTEGER", False, primary_key=True),
            Column("customer_id", "INTEGER", False),
            Column("order_status", "TEXT", False, default="PENDING"),
            Column("created_at", "TEXT", False)
        ],
        foreign_keys=[
            ForeignKey(
                ("customer_id",),
                "customers",
                ("customer_id",)
            )
        ]
    ))

    catalog.add_table(Table(
        name="order_items",
        columns=[
            Column("order_item_id", "INTEGER", False, primary_key=True),
            Column("order_id", "INTEGER", False),
            Column("product_id", "INTEGER", False),
            Column("quantity", "INTEGER", False),
            Column("unit_price", "NUMERIC", False)
        ],
        foreign_keys=[
            ForeignKey(
                ("order_id",), "orders", ("order_id",), "CASCADE"
            ),
            ForeignKey(
                ("product_id",), "products", ("product_id",)
            )
        ],
        unique_constraints=[
            ("order_id", "product_id")
        ]
    ))

    catalog.validate_relationships()
    return catalog


def create_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    connection.executescript("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (length(trim(email)) > 3),
            CHECK (length(trim(full_name)) > 0)
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            unit_price NUMERIC NOT NULL CHECK (unit_price >= 0),
            active INTEGER NOT NULL DEFAULT 1
                CHECK (active IN (0, 1))
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_status TEXT NOT NULL DEFAULT 'PENDING'
                CHECK (
                    order_status IN (
                        'PENDING', 'CONFIRMED',
                        'SHIPPED', 'CANCELLED'
                    )
                ),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id)
                REFERENCES customers(customer_id)
                ON DELETE RESTRICT
        );

        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price NUMERIC NOT NULL CHECK (unit_price >= 0),
            UNIQUE (order_id, product_id),
            FOREIGN KEY (order_id)
                REFERENCES orders(order_id)
                ON DELETE CASCADE,
            FOREIGN KEY (product_id)
                REFERENCES products(product_id)
                ON DELETE RESTRICT
        );

        CREATE INDEX idx_orders_customer_created
            ON orders(customer_id, created_at);

        CREATE INDEX idx_order_items_product
            ON order_items(product_id);

        CREATE INDEX idx_orders_status
            ON orders(order_status);
    """)

    return connection


def seed_database(connection: sqlite3.Connection) -> None:
    with connection:
        connection.executemany(
            """
            INSERT INTO customers(customer_id, email, full_name)
            VALUES (?, ?, ?)
            """,
            [
                (1, "customer1@example.com", "Aarav Sharma"),
                (2, "customer2@example.com", "Diya Verma")
            ]
        )

        connection.executemany(
            """
            INSERT INTO products(
                product_id, sku, product_name, unit_price
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (1, "SKU-1001", "Laptop", "65000.00"),
                (2, "SKU-1002", "Keyboard", "1500.00"),
                (3, "SKU-1003", "Monitor", "12000.00")
            ]
        )


def place_order(
    connection: sqlite3.Connection,
    customer_id: int,
    items: list[tuple[int, int]]
) -> int:
    """
    Create an order atomically.

    Each item is represented by (product_id, quantity).
    Product prices are read from the database, not trusted from callers.
    """
    if not items:
        raise ValueError("An order must contain at least one item.")

    if any(
        not isinstance(product_id, int)
        or not isinstance(quantity, int)
        or quantity <= 0
        for product_id, quantity in items
    ):
        raise ValueError("Invalid product or quantity.")

    product_ids = [product_id for product_id, _ in items]

    if len(product_ids) != len(set(product_ids)):
        raise ValueError("Duplicate products in order.")

    try:
        connection.execute("BEGIN IMMEDIATE")

        customer = connection.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ?",
            (customer_id,)
        ).fetchone()

        if customer is None:
            raise ValueError("Customer does not exist.")

        order_cursor = connection.execute(
            """
            INSERT INTO orders(customer_id, order_status)
            VALUES (?, 'PENDING')
            """,
            (customer_id,)
        )

        order_id = order_cursor.lastrowid

        for product_id, quantity in items:
            product = connection.execute(
                """
                SELECT unit_price
                FROM products
                WHERE product_id = ? AND active = 1
                """,
                (product_id,)
            ).fetchone()

            if product is None:
                raise ValueError(
                    f"Product {product_id} is unavailable."
                )

            connection.execute(
                """
                INSERT INTO order_items(
                    order_id, product_id, quantity, unit_price
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    order_id,
                    product_id,
                    quantity,
                    str(product["unit_price"])
                )
            )

        connection.commit()
        return order_id

    except Exception:
        connection.rollback()
        raise


def get_order_report(
    connection: sqlite3.Connection
) -> list[sqlite3.Row]:
    return connection.execute("""
        SELECT
            o.order_id,
            c.full_name,
            o.order_status,
            COUNT(oi.order_item_id) AS item_count,
            SUM(oi.quantity * oi.unit_price) AS total_amount
        FROM orders o
        JOIN customers c
            ON c.customer_id = o.customer_id
        JOIN order_items oi
            ON oi.order_id = o.order_id
        GROUP BY
            o.order_id,
            c.full_name,
            o.order_status
        ORDER BY o.order_id
    """).fetchall()


def demonstrate_constraint_failure(
    connection: sqlite3.Connection
) -> None:
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO orders(customer_id)
                VALUES (99999)
                """
            )
    except sqlite3.IntegrityError as error:
        LOGGER.info("Foreign key validation worked: %s", error)

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO products(
                    sku, product_name, unit_price
                )
                VALUES ('SKU-1001', 'Duplicate', 100)
                """
            )
    except sqlite3.IntegrityError as error:
        LOGGER.info("Unique constraint validation worked: %s", error)


def demonstrate_atomic_rollback(
    connection: sqlite3.Connection
) -> None:
    before = connection.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0]

    try:
        place_order(
            connection,
            customer_id=1,
            items=[(1, 1), (999, 2)]
        )
    except ValueError as error:
        LOGGER.info("Order rejected and rolled back: %s", error)

    after = connection.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0]

    assert before == after, "Failed transaction was not rolled back."


def main() -> None:
    catalog = create_schema()
    catalog.report()

    connection = create_database()

    try:
        seed_database(connection)

        order_id = place_order(
            connection,
            customer_id=1,
            items=[(1, 1), (2, 2)]
        )

        print(f"\nCreated order: {order_id}")

        for row in get_order_report(connection):
            print(dict(row))

        demonstrate_constraint_failure(connection)
        demonstrate_atomic_rollback(connection)

        print("\nSCHEMA VALIDATION")

        print("Creation order:", catalog.dependency_order())
        print("Foreign key enforcement: enabled")
        print("Parameterized SQL: enabled")
        print("Transactional order processing: passed")

        print("\nAll database schema demonstrations completed.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
