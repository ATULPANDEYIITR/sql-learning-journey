#!/usr/bin/env python3
"""
PARTIAL AND EXPRESSION INDEXES
Conditional indexes and function-based indexing.

Demonstrates:
1. Fundamental database indexing.
2. Partial indexes using conditional predicates.
3. Expression indexes using computed values.
4. Unique partial indexes.
5. Composite partial indexes.
6. Index eligibility and predicate matching.
7. Query-plan inspection using SQLite.
8. Index maintenance and performance trade-offs.
9. Validation, exception handling, and automated assertions.

Python's standard-library SQLite engine is used for executable
demonstrations. PostgreSQL-specific implementation is provided
separately in the SQL deliverable.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


# ============================================================
# 1. DOMAIN MODEL
# ============================================================

class OrderStatus(Enum):
    OPEN = "OPEN"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class Order:
    order_id: int
    customer_email: str
    status: OrderStatus
    amount: float
    region: str

    def validate(self) -> None:
        if self.order_id <= 0:
            raise ValueError("Order ID must be positive.")

        if not self.customer_email or "@" not in self.customer_email:
            raise ValueError("Invalid customer email.")

        if self.amount < 0:
            raise ValueError("Order amount cannot be negative.")

        if not self.region.strip():
            raise ValueError("Region cannot be empty.")


# ============================================================
# 2. INDEX DOMAIN MODEL
# ============================================================

class IndexType(Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    EXPRESSION = "EXPRESSION"
    PARTIAL_EXPRESSION = "PARTIAL_EXPRESSION"


@dataclass(frozen=True)
class IndexDefinition:
    name: str
    index_type: IndexType
    expression: str
    predicate: Optional[str] = None
    unique: bool = False

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Index name is required.")

        if not self.expression:
            raise ValueError("Index expression is required.")

        if self.index_type in (
            IndexType.PARTIAL,
            IndexType.PARTIAL_EXPRESSION
        ) and not self.predicate:
            raise ValueError("Partial indexes require a predicate.")


# ============================================================
# 3. DATABASE CONNECTION
# ============================================================

class OrderDatabase:

    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.create_schema()

    def create_schema(self) -> None:
        self.connection.executescript("""
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                region TEXT NOT NULL
            );

            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_email TEXT NOT NULL,
                status TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount >= 0),
                region TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE audit_log (
                audit_id INTEGER PRIMARY KEY,
                event TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def close(self) -> None:
        self.connection.close()


# ============================================================
# 4. SAMPLE DATA
# ============================================================

def insert_sample_data(db: OrderDatabase) -> None:
    records = [
        Order(1, "alice@example.com", OrderStatus.OPEN, 450, "NORTH"),
        Order(2, "bob@example.com", OrderStatus.PAID, 900, "SOUTH"),
        Order(3, "carol@example.com", OrderStatus.OPEN, 250, "NORTH"),
        Order(4, "david@example.com", OrderStatus.CANCELLED, 120, "WEST"),
        Order(5, "eve@example.com", OrderStatus.ARCHIVED, 300, "EAST"),
        Order(6, "frank@example.com", OrderStatus.OPEN, 780, "SOUTH"),
        Order(7, "grace@example.com", OrderStatus.PAID, 150, "NORTH"),
    ]

    with db.connection:
        for order in records:
            order.validate()

            db.connection.execute("""
                INSERT INTO orders (
                    order_id,
                    customer_email,
                    status,
                    amount,
                    region
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                order.order_id,
                order.customer_email,
                order.status.value,
                order.amount,
                order.region
            ))


# ============================================================
# 5. INDEX CREATION
# ============================================================

class IndexManager:

    def __init__(self, db: OrderDatabase):
        self.db = db
        self.definitions: dict[str, IndexDefinition] = {}

    def create_index(self, definition: IndexDefinition) -> None:
        definition.validate()

        if definition.name in self.definitions:
            raise ValueError(f"Index already registered: {definition.name}")

        allowed_expressions = {
            "order_id",
            "customer_email",
            "lower(customer_email)",
            "upper(region)",
            "amount",
            "region",
            "created_at"
        }

        if definition.expression not in allowed_expressions:
            raise ValueError("Unsupported index expression.")

        allowed_predicates = {
            None,
            "status = 'OPEN'",
            "status = 'PAID'",
            "amount > 500",
            "status = 'OPEN' AND amount > 300"
        }

        if definition.predicate not in allowed_predicates:
            raise ValueError("Unsupported partial-index predicate.")

        unique_sql = "UNIQUE " if definition.unique else ""

        sql = (
            f"CREATE {unique_sql}INDEX {definition.name} "
            f"ON orders ({definition.expression})"
        )

        if definition.predicate:
            sql += f" WHERE {definition.predicate}"

        try:
            with self.db.connection:
                self.db.connection.execute(sql)

            self.definitions[definition.name] = definition

            print(f"Created index: {definition.name}")

        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"Index creation violated uniqueness: {exc}"
            ) from exc

        except sqlite3.DatabaseError as exc:
            raise RuntimeError(
                f"Index creation failed: {exc}"
            ) from exc


# ============================================================
# 6. INDEX DEFINITIONS
# ============================================================

def configure_indexes(manager: IndexManager) -> None:

    manager.create_index(IndexDefinition(
        name="idx_orders_open",
        index_type=IndexType.PARTIAL,
        expression="order_id",
        predicate="status = 'OPEN'"
    ))

    manager.create_index(IndexDefinition(
        name="idx_orders_email_lower",
        index_type=IndexType.EXPRESSION,
        expression="lower(customer_email)"
    ))

    manager.create_index(IndexDefinition(
        name="idx_orders_open_amount",
        index_type=IndexType.PARTIAL,
        expression="amount",
        predicate="status = 'OPEN' AND amount > 300"
    ))

    manager.create_index(IndexDefinition(
        name="idx_orders_upper_region",
        index_type=IndexType.EXPRESSION,
        expression="upper(region)"
    ))


# ============================================================
# 7. PARTIAL INDEX OPERATIONS
# ============================================================

def demonstrate_partial_index(db: OrderDatabase) -> None:
    print("\nPARTIAL INDEX DEMONSTRATION")

    rows = db.connection.execute("""
        SELECT order_id, customer_email, amount
        FROM orders
        WHERE status = 'OPEN'
        ORDER BY order_id
    """).fetchall()

    for row in rows:
        print(dict(row))

    count = db.connection.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'OPEN'
    """).fetchone()[0]

    print(f"Open orders: {count}")

    print("""
A partial index stores entries only for rows satisfying
its WHERE predicate.

Rows with PAID, CANCELLED, or ARCHIVED status do not
belong to idx_orders_open.
""")


# ============================================================
# 8. EXPRESSION INDEX OPERATIONS
# ============================================================

def demonstrate_expression_index(db: OrderDatabase) -> None:
    print("\nEXPRESSION INDEX DEMONSTRATION")

    rows = db.connection.execute("""
        SELECT order_id, customer_email
        FROM orders
        WHERE lower(customer_email) = ?
    """, ("alice@example.com",)).fetchall()

    for row in rows:
        print(dict(row))

    print("""
The index stores the computed lower(customer_email) value.

The query must use a compatible expression to benefit
from this index.
""")


# ============================================================
# 9. PARTIAL EXPRESSION INDEX
# ============================================================

def demonstrate_partial_expression_index(
    db: OrderDatabase
) -> None:

    print("\nPARTIAL EXPRESSION INDEX DEMONSTRATION")

    rows = db.connection.execute("""
        SELECT order_id, customer_email, amount
        FROM orders
        WHERE status = 'OPEN'
          AND amount > 300
          AND lower(customer_email) = ?
    """, ("frank@example.com",)).fetchall()

    for row in rows:
        print(dict(row))

    print("""
A partial expression index combines two mechanisms:

1. A predicate limits which rows are indexed.
2. An expression determines the indexed key.
""")


# ============================================================
# 10. QUERY PLAN INSPECTION
# ============================================================

def inspect_query_plan(
    db: OrderDatabase,
    sql: str,
    parameters: tuple = ()
) -> list[str]:

    if not sql.lstrip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements can be inspected.")

    plan = db.connection.execute(
        "EXPLAIN QUERY PLAN " + sql,
        parameters
    ).fetchall()

    details = [row["detail"] for row in plan]

    for detail in details:
        print(detail)

    return details


def demonstrate_query_plans(db: OrderDatabase) -> None:
    print("\nQUERY PLAN: PARTIAL INDEX")

    inspect_query_plan(
        db,
        """
        SELECT order_id
        FROM orders
        WHERE status = 'OPEN'
        """
    )

    print("\nQUERY PLAN: EXPRESSION INDEX")

    inspect_query_plan(
        db,
        """
        SELECT order_id
        FROM orders
        WHERE lower(customer_email) = ?
        """,
        ("alice@example.com",)
    )


# ============================================================
# 11. INDEX ELIGIBILITY MODEL
# ============================================================

@dataclass(frozen=True)
class QueryCondition:
    expression: str
    predicate: Optional[str] = None


class IndexEligibility:

    @staticmethod
    def evaluate(
        index: IndexDefinition,
        query: QueryCondition
    ) -> bool:

        if index.expression != query.expression:
            return False

        if index.predicate is None:
            return True

        if query.predicate == index.predicate:
            return True

        # Exact predicate matching is deliberately conservative.
        # Real PostgreSQL planning uses predicate implication rules
        # and planner-specific expression normalization.
        return False


def demonstrate_eligibility(
    manager: IndexManager
) -> None:

    print("\nINDEX ELIGIBILITY")

    queries = [
        QueryCondition(
            "order_id",
            "status = 'OPEN'"
        ),
        QueryCondition(
            "order_id",
            "status = 'PAID'"
        ),
        QueryCondition(
            "lower(customer_email)"
        ),
        QueryCondition(
            "upper(region)"
        )
    ]

    for query in queries:
        print(f"\nQuery: {query}")

        for index in manager.definitions.values():
            eligible = IndexEligibility.evaluate(index, query)

            if eligible:
                print(f"  Eligible: {index.name}")


# ============================================================
# 12. UNIQUE PARTIAL INDEX
# ============================================================

def demonstrate_unique_partial_index(
    db: OrderDatabase
) -> None:

    print("\nUNIQUE PARTIAL INDEX")

    db.connection.execute("""
        CREATE TABLE user_accounts (
            account_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            active BOOLEAN NOT NULL
        )
    """)

    db.connection.execute("""
        CREATE UNIQUE INDEX idx_active_account_email
        ON user_accounts (lower(email))
        WHERE active = 1
    """)

    with db.connection:
        db.connection.execute("""
            INSERT INTO user_accounts VALUES
            (1, 'admin@example.com', 1),
            (2, 'old@example.com', 0)
        """)

    # Duplicate active email is rejected.
    try:
        with db.connection:
            db.connection.execute("""
                INSERT INTO user_accounts
                VALUES (3, 'ADMIN@example.com', 1)
            """)

    except sqlite3.IntegrityError:
        print("Duplicate active email correctly rejected.")

    # Inactive duplicates are allowed.
    with db.connection:
        db.connection.execute("""
            INSERT INTO user_accounts
            VALUES (4, 'ADMIN@example.com', 0)
        """)

    print("Inactive duplicate successfully inserted.")


# ============================================================
# 13. INDEX MAINTENANCE
# ============================================================

def demonstrate_index_maintenance(
    db: OrderDatabase
) -> None:

    print("\nINDEX MAINTENANCE")

    # Updating status changes membership in the partial index.
    with db.connection:
        db.connection.execute("""
            UPDATE orders
            SET status = 'PAID'
            WHERE order_id = 1
        """)

    remaining = db.connection.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'OPEN'
    """).fetchone()[0]

    print(f"Remaining open orders: {remaining}")

    # Expression-index keys must also be maintained when
    # the source column changes.
    with db.connection:
        db.connection.execute("""
            UPDATE orders
            SET customer_email = 'alice.new@example.com'
            WHERE order_id = 1
        """)

    print("Updated source columns and maintained indexes.")


# ============================================================
# 14. PERFORMANCE MEASUREMENT
# ============================================================

def benchmark(
    db: OrderDatabase,
    sql: str,
    parameters: tuple = (),
    repetitions: int = 1000
) -> float:

    if repetitions <= 0:
        raise ValueError("Repetitions must be positive.")

    start = time.perf_counter()

    for _ in range(repetitions):
        db.connection.execute(sql, parameters).fetchall()

    elapsed = time.perf_counter() - start

    return elapsed


def demonstrate_benchmark(db: OrderDatabase) -> None:
    print("\nQUERY EXECUTION MEASUREMENT")

    elapsed = benchmark(
        db,
        """
        SELECT order_id
        FROM orders
        WHERE lower(customer_email) = ?
        """,
        ("alice.new@example.com",)
    )

    print(f"1000 executions: {elapsed:.6f} seconds")

    print("""
Measurement is illustrative, not a PostgreSQL benchmark.
Real performance depends on data volume, cache state,
selectivity, storage, concurrency, and query planning.
""")


# ============================================================
# 15. VALIDATION TESTS
# ============================================================

def run_assertions(db: OrderDatabase) -> None:
    print("\nAUTOMATED ASSERTIONS")

    open_count = db.connection.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'OPEN'
    """).fetchone()[0]

    assert open_count == 2

    email_count = db.connection.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE lower(customer_email) = ?
    """, ("alice.new@example.com",)).fetchone()[0]

    assert email_count == 1

    active_count = db.connection.execute("""
        SELECT COUNT(*)
        FROM user_accounts
        WHERE active = 1
    """).fetchone()[0]

    assert active_count == 1

    try:
        IndexDefinition(
            name="invalid_index",
            index_type=IndexType.PARTIAL,
            expression="order_id"
        ).validate()

        raise AssertionError("Invalid definition was accepted.")

    except ValueError:
        pass

    try:
        Order(
            0,
            "invalid",
            OrderStatus.OPEN,
            -10,
            "NORTH"
        ).validate()

        raise AssertionError("Invalid order was accepted.")

    except ValueError:
        pass

    print("All assertions passed.")


# ============================================================
# 16. EXECUTION
# ============================================================

def main() -> None:
    database = OrderDatabase()

    try:
        insert_sample_data(database)

        manager = IndexManager(database)

        configure_indexes(manager)

        demonstrate_partial_index(database)

        demonstrate_expression_index(database)

        demonstrate_partial_expression_index(database)

        demonstrate_query_plans(database)

        demonstrate_eligibility(manager)

        demonstrate_unique_partial_index(database)

        demonstrate_index_maintenance(database)

        demonstrate_benchmark(database)

        run_assertions(database)

        print("\nExecution completed successfully.")

    except (ValueError, RuntimeError, sqlite3.DatabaseError) as exc:
        print(f"Execution failed: {exc}")
        raise

    finally:
        database.close()


if __name__ == "__main__":
    main()
