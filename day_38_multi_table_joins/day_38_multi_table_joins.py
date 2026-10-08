"""
Multi-Table JOINs in Python with SQLite

This executable example uses Python's standard-library sqlite3 module to
demonstrate relational joins across three or more tables. The examples move
from a simple three-table relationship to join ordering, one-to-many
relationships, outer joins, many-to-many relationships, aggregation,
subqueries, CTEs, validation, query plans, transactions, and practical
failure cases.

Run with:
    python multi_table_joins.py
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import Iterable


SCHEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS sales_regions;

CREATE TABLE sales_regions (
    region_id INTEGER PRIMARY KEY,
    region_name TEXT NOT NULL UNIQUE
);

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    region_id INTEGER NOT NULL,
    FOREIGN KEY (region_id) REFERENCES sales_regions(region_id)
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL CHECK (unit_price > 0)
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED')
    ),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price > 0),
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE INDEX idx_customers_region ON customers(region_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_order_items_product ON order_items(product_id);
"""

DATA = """
INSERT INTO sales_regions(region_id, region_name) VALUES
    (1, 'North'),
    (2, 'South'),
    (3, 'West'),
    (4, 'East');

INSERT INTO customers(customer_id, customer_name, region_id) VALUES
    (101, 'Aarav Systems', 1),
    (102, 'Bharat Logistics', 2),
    (103, 'Civic Research Lab', 3),
    (104, 'Delta Manufacturing', 1),
    (105, 'Eastern Retail Group', 4);

INSERT INTO products(product_id, product_name, category, unit_price) VALUES
    (201, 'Edge Sensor', 'IoT', 120.00),
    (202, 'Gateway Pro', 'Networking', 450.00),
    (203, 'Analytics License', 'Software', 800.00),
    (204, 'Secure Router', 'Networking', 600.00),
    (205, 'Inspection Camera', 'Vision', 950.00);

INSERT INTO orders(order_id, customer_id, order_date, status) VALUES
    (1001, 101, '2026-09-01', 'DELIVERED'),
    (1002, 101, '2026-09-14', 'SHIPPED'),
    (1003, 102, '2026-09-18', 'DELIVERED'),
    (1004, 103, '2026-09-20', 'CANCELLED'),
    (1005, 104, '2026-09-22', 'DELIVERED'),
    (1006, 105, '2026-09-24', 'PLACED');

INSERT INTO order_items(order_id, product_id, quantity, unit_price) VALUES
    (1001, 201, 10, 120.00),
    (1001, 202, 2, 450.00),
    (1002, 203, 1, 800.00),
    (1002, 201, 5, 120.00),
    (1003, 204, 3, 600.00),
    (1003, 201, 20, 120.00),
    (1004, 205, 1, 950.00),
    (1005, 205, 4, 950.00),
    (1005, 203, 2, 800.00),
    (1006, 202, 1, 450.00);
"""


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[tuple]


def execute_query(
    connection: sqlite3.Connection,
    sql: str,
    parameters: Iterable = (),
) -> QueryResult:
    """Execute a SELECT-style statement and return structured results."""
    try:
        cursor = connection.execute(sql, tuple(parameters))
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return QueryResult(columns, rows)
    except sqlite3.Error as exc:
        raise RuntimeError(f"SQL execution failed: {exc}") from exc


def print_result(title: str, result: QueryResult) -> None:
    print(f"\n=== {title} ===")
    if not result.rows:
        print("(no rows)")
        return

    print(" | ".join(result.columns))
    print("-" * (len(" | ".join(result.columns)) + 2))
    for row in result.rows:
        print(" | ".join(str(value) for value in row))


def create_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = None
    connection.executescript(SCHEMA)
    connection.executescript(DATA)
    return connection


def basic_three_table_join(connection: sqlite3.Connection) -> None:
    """
    customers -> orders -> order_items is a three-table one-to-many chain.
    Each JOIN follows an actual foreign-key relationship.
    """
    sql = """
        SELECT
            c.customer_name,
            o.order_id,
            o.order_date,
            oi.product_id,
            oi.quantity
        FROM customers AS c
        INNER JOIN orders AS o
            ON o.customer_id = c.customer_id
        INNER JOIN order_items AS oi
            ON oi.order_id = o.order_id
        ORDER BY c.customer_name, o.order_id, oi.product_id;
    """
    print_result("Three-table join", execute_query(connection, sql))


def five_table_join(connection: sqlite3.Connection) -> None:
    """
    A five-table join follows:
        region -> customer -> order -> item -> product

    The SELECT list uses attributes from every participating table.
    """
    sql = """
        SELECT
            r.region_name,
            c.customer_name,
            o.order_id,
            p.product_name,
            oi.quantity,
            ROUND(oi.quantity * oi.unit_price, 2) AS line_value
        FROM sales_regions AS r
        JOIN customers AS c
            ON c.region_id = r.region_id
        JOIN orders AS o
            ON o.customer_id = c.customer_id
        JOIN order_items AS oi
            ON oi.order_id = o.order_id
        JOIN products AS p
            ON p.product_id = oi.product_id
        WHERE o.status <> 'CANCELLED'
        ORDER BY r.region_name, o.order_id, p.product_name;
    """
    print_result("Five-table relationship", execute_query(connection, sql))


def join_order_and_logical_equivalence(connection: sqlite3.Connection) -> None:
    """
    For inner joins, a different written order can often produce the same
    relational result because inner join is associative and commutative.

    The optimizer may still choose its own physical execution order.
    """
    first = """
        SELECT c.customer_name, o.order_id, p.product_name
        FROM customers AS c
        JOIN orders AS o ON o.customer_id = c.customer_id
        JOIN order_items AS oi ON oi.order_id = o.order_id
        JOIN products AS p ON p.product_id = oi.product_id
        ORDER BY c.customer_name, o.order_id, p.product_name;
    """

    second = """
        SELECT c.customer_name, o.order_id, p.product_name
        FROM products AS p
        JOIN order_items AS oi ON oi.product_id = p.product_id
        JOIN orders AS o ON o.order_id = oi.order_id
        JOIN customers AS c ON c.customer_id = o.customer_id
        ORDER BY c.customer_name, o.order_id, p.product_name;
    """

    result_a = execute_query(connection, first)
    result_b = execute_query(connection, second)

    print("\n=== Join-order equivalence ===")
    print(f"Same columns: {result_a.columns == result_b.columns}")
    print(f"Same rows:    {result_a.rows == result_b.rows}")


def left_join_preserves_unmatched_rows(connection: sqlite3.Connection) -> None:
    """
    LEFT JOIN keeps the row from the left relation even when no matching
    child row exists. This is important for customers without orders.
    """
    sql = """
        SELECT
            c.customer_name,
            COUNT(o.order_id) AS order_count
        FROM customers AS c
        LEFT JOIN orders AS o
            ON o.customer_id = c.customer_id
        GROUP BY c.customer_id, c.customer_name
        ORDER BY c.customer_id;
    """
    print_result("LEFT JOIN with aggregation", execute_query(connection, sql))


def avoid_accidental_inner_join(connection: sqlite3.Connection) -> None:
    """
    A condition on the right-side table in WHERE can remove NULL rows from
    a LEFT JOIN and effectively turn it into an inner join.

    Moving the predicate into ON preserves customers with no qualifying
    orders.
    """
    incorrect = """
        SELECT c.customer_name, o.order_id
        FROM customers AS c
        LEFT JOIN orders AS o
            ON o.customer_id = c.customer_id
        WHERE o.status = 'DELIVERED'
        ORDER BY c.customer_id;
    """

    correct = """
        SELECT c.customer_name, o.order_id
        FROM customers AS c
        LEFT JOIN orders AS o
            ON o.customer_id = c.customer_id
           AND o.status = 'DELIVERED'
        ORDER BY c.customer_id;
    """

    print_result(
        "LEFT JOIN changed by WHERE predicate",
        execute_query(connection, incorrect),
    )
    print_result(
        "LEFT JOIN with predicate in ON",
        execute_query(connection, correct),
    )


def many_to_many_style_relationship(connection: sqlite3.Connection) -> None:
    """
    order_items is an associative table. It resolves the many-to-many
    relationship between orders and products:
        order -> order_items -> product
    """
    sql = """
        SELECT
            p.product_name,
            COUNT(DISTINCT o.order_id) AS distinct_orders,
            SUM(oi.quantity) AS units_sold,
            ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM products AS p
        JOIN order_items AS oi
            ON oi.product_id = p.product_id
        JOIN orders AS o
            ON o.order_id = oi.order_id
        WHERE o.status <> 'CANCELLED'
        GROUP BY p.product_id, p.product_name
        ORDER BY revenue DESC;
    """
    print_result("Many-to-many bridge analysis", execute_query(connection, sql))


def cte_for_complex_join(connection: sqlite3.Connection) -> None:
    """
    A CTE isolates order-level calculations before they are joined to
    customer and region data. This reduces repeated expressions and makes
    the analytical stages explicit.
    """
    sql = """
        WITH order_totals AS (
            SELECT
                o.order_id,
                o.customer_id,
                o.status,
                SUM(oi.quantity * oi.unit_price) AS order_value
            FROM orders AS o
            JOIN order_items AS oi
                ON oi.order_id = o.order_id
            GROUP BY o.order_id, o.customer_id, o.status
        )
        SELECT
            r.region_name,
            c.customer_name,
            ot.order_id,
            ROUND(ot.order_value, 2) AS order_value
        FROM order_totals AS ot
        JOIN customers AS c
            ON c.customer_id = ot.customer_id
        JOIN sales_regions AS r
            ON r.region_id = c.region_id
        WHERE ot.status = 'DELIVERED'
          AND ot.order_value >= 1000
        ORDER BY ot.order_value DESC;
    """
    print_result("CTE followed by multi-table joins", execute_query(connection, sql))


def correlated_subquery_with_join(connection: sqlite3.Connection) -> None:
    """
    A subquery can be combined with joins when the business rule requires a
    comparison against an entity-specific aggregate.
    """
    sql = """
        SELECT
            c.customer_name,
            r.region_name,
            ROUND(SUM(oi.quantity * oi.unit_price), 2) AS customer_revenue
        FROM customers AS c
        JOIN sales_regions AS r
            ON r.region_id = c.region_id
        JOIN orders AS o
            ON o.customer_id = c.customer_id
        JOIN order_items AS oi
            ON oi.order_id = o.order_id
        WHERE o.status = 'DELIVERED'
        GROUP BY c.customer_id, c.customer_name, r.region_name
        HAVING SUM(oi.quantity * oi.unit_price) >
            (
                SELECT AVG(customer_total)
                FROM (
                    SELECT
                        SUM(oi2.quantity * oi2.unit_price) AS customer_total
                    FROM customers AS c2
                    JOIN orders AS o2
                        ON o2.customer_id = c2.customer_id
                    JOIN order_items AS oi2
                        ON oi2.order_id = o2.order_id
                    WHERE o2.status = 'DELIVERED'
                    GROUP BY c2.customer_id
                ) AS customer_totals
            )
        ORDER BY customer_revenue DESC;
    """
    print_result(
        "Customers above the average delivered-customer revenue",
        execute_query(connection, sql),
    )


def inspect_query_plan(connection: sqlite3.Connection) -> None:
    """
    EXPLAIN QUERY PLAN shows SQLite's selected access strategy. The textual
    join order is not necessarily the physical execution order.
    """
    sql = """
        EXPLAIN QUERY PLAN
        SELECT
            c.customer_name,
            p.product_name
        FROM customers AS c
        JOIN orders AS o ON o.customer_id = c.customer_id
        JOIN order_items AS oi ON oi.order_id = o.order_id
        JOIN products AS p ON p.product_id = oi.product_id
        WHERE c.region_id = ?;
    """

    result = execute_query(connection, sql, (1,))
    print_result("SQLite query plan", result)


def transaction_and_integrity_demo(connection: sqlite3.Connection) -> None:
    """
    Foreign-key enforcement prevents an order item from referring to a
    nonexistent order. The transaction is rolled back after the deliberate
    failure so the database remains unchanged.
    """
    print("\n=== Transaction and referential-integrity failure ===")
    try:
        connection.execute("BEGIN")
        connection.execute(
            """
            INSERT INTO order_items(order_id, product_id, quantity, unit_price)
            VALUES (?, ?, ?, ?)
            """,
            (9999, 201, 1, 120.00),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        print(f"Rejected invalid multi-table relationship: {exc}")


def parameterized_filter(connection: sqlite3.Connection) -> None:
    """
    Values must be passed as parameters rather than concatenated into SQL.
    This prevents SQL injection when filters originate from external input.
    """
    customer_id = 101
    sql = """
        SELECT
            c.customer_name,
            o.order_id,
            o.status,
            p.product_name,
            oi.quantity
        FROM customers AS c
        JOIN orders AS o ON o.customer_id = c.customer_id
        JOIN order_items AS oi ON oi.order_id = o.order_id
        JOIN products AS p ON p.product_id = oi.product_id
        WHERE c.customer_id = ?
        ORDER BY o.order_id;
    """
    print_result(
        "Parameterized multi-table lookup",
        execute_query(connection, sql, (customer_id,)),
    )


def main() -> None:
    with closing(create_database()) as connection:
        basic_three_table_join(connection)
        five_table_join(connection)
        join_order_and_logical_equivalence(connection)
        left_join_preserves_unmatched_rows(connection)
        avoid_accidental_inner_join(connection)
        many_to_many_style_relationship(connection)
        cte_for_complex_join(connection)
        correlated_subquery_with_join(connection)
        inspect_query_plan(connection)
        transaction_and_integrity_demo(connection)
        parameterized_filter(connection)


if __name__ == "__main__":
    main()
