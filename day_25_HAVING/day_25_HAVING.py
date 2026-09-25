"""
HAVING: Filtering Aggregated Results, WHERE vs HAVING
======================================================

This standalone study script teaches SQL HAVING from beginner to advanced level.

The demonstrations use Python's built-in sqlite3 module, so no external package
is required. SQLite supports the SQL concepts demonstrated here, including
WHERE, GROUP BY, aggregate functions, HAVING, ORDER BY, aliases in practical
querying, subqueries, conditional aggregation, joins, NULL behavior, and
window functions.

Core distinction:

    WHERE
        Filters individual rows before grouping and aggregation.

    GROUP BY
        Combines remaining rows into groups.

    HAVING
        Filters groups after aggregation.

Typical logical processing order:

    FROM / JOIN
        -> WHERE
        -> GROUP BY
        -> HAVING
        -> SELECT
        -> ORDER BY
        -> LIMIT

Example:

    SELECT department, COUNT(*) AS employee_count
    FROM employees
    WHERE active = 1
    GROUP BY department
    HAVING COUNT(*) >= 5
    ORDER BY employee_count DESC;

The WHERE clause decides which employee rows participate.
The GROUP BY clause creates department groups.
The HAVING clause decides which department groups survive.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def print_title(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def print_rows(rows: Iterable[sqlite3.Row]) -> None:
    rows = list(rows)

    if not rows:
        print("(no rows)")
        return

    column_names = rows[0].keys()
    widths = {
        column: max(
            len(column),
            max(len(str(row[column])) for row in rows)
        )
        for column in column_names
    }

    header = " | ".join(
        f"{column:<{widths[column]}}"
        for column in column_names
    )
    separator = "-+-".join("-" * widths[column] for column in column_names)

    print(header)
    print(separator)

    for row in rows:
        print(
            " | ".join(
                f"{str(row[column]):<{widths[column]}}"
                for column in column_names
            )
        )


def run_query(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> list[sqlite3.Row]:
    print("\nSQL:")
    print(sql.strip())

    rows = connection.execute(sql, parameters).fetchall()
    print("\nResult:")
    print_rows(rows)
    return rows


# ---------------------------------------------------------------------------
# Database construction
# ---------------------------------------------------------------------------

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
            department_id INTEGER NOT NULL,
            salary REAL NOT NULL CHECK (salary >= 0),
            active INTEGER NOT NULL CHECK (active IN (0, 1)),
            FOREIGN KEY (department_id)
                REFERENCES departments(department_id)
        );

        CREATE TABLE sales (
            sale_id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL,
            sale_date TEXT NOT NULL,
            product TEXT NOT NULL,
            region TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price REAL NOT NULL CHECK (unit_price >= 0),
            discount REAL NOT NULL DEFAULT 0
                CHECK (discount >= 0 AND discount <= 1),
            FOREIGN KEY (employee_id)
                REFERENCES employees(employee_id)
        );

        INSERT INTO departments VALUES
            (1, 'Engineering'),
            (2, 'Sales'),
            (3, 'Marketing'),
            (4, 'Finance'),
            (5, 'Operations');

        INSERT INTO employees VALUES
            (1, 'Asha',   1, 90000, 1),
            (2, 'Ben',    1, 82000, 1),
            (3, 'Chen',   1, 78000, 0),
            (4, 'Diana',  2, 70000, 1),
            (5, 'Evan',   2, 68000, 1),
            (6, 'Fatima', 2, 65000, 1),
            (7, 'George', 2, 62000, 0),
            (8, 'Helen',  3, 60000, 1),
            (9, 'Ivan',   3, 58000, 1),
            (10, 'Julia', 4, 75000, 1),
            (11, 'Karan',  5, 55000, 1);

        INSERT INTO sales VALUES
            (1,  4, '2026-01-05', 'Laptop',     'North',  4, 1000, 0.05),
            (2,  4, '2026-01-07', 'Monitor',    'North',  6,  400, 0.00),
            (3,  5, '2026-01-10', 'Laptop',     'South',  3, 1000, 0.10),
            (4,  5, '2026-01-12', 'Keyboard',   'South', 10,  100, 0.05),
            (5,  6, '2026-01-15', 'Laptop',     'East',   8, 1000, 0.15),
            (6,  6, '2026-01-18', 'Monitor',    'East',  12,  400, 0.10),
            (7,  4, '2026-02-02', 'Laptop',     'North',  2, 1000, 0.00),
            (8,  5, '2026-02-04', 'Monitor',    'South',  8,  400, 0.05),
            (9,  6, '2026-02-08', 'Keyboard',   'East',  15,  100, 0.00),
            (10, 4, '2026-02-10', 'Headset',    'North', 20,  80,  0.10),
            (11, 5, '2026-02-15', 'Laptop',     'South',  1, 1000, 0.00),
            (12, 6, '2026-02-20', 'Monitor',    'East',   5,  400, 0.20),
            (13, 4, '2026-03-01', 'Laptop',     'North', 10, 1000, 0.05),
            (14, 5, '2026-03-03', 'Monitor',    'South',  2,  400, 0.00),
            (15, 6, '2026-03-05', 'Keyboard',   'East',   5,  100, 0.00),
            (16, 4, '2026-03-10', 'Headset',    'North', 30,  80,  0.05),
            (17, 5, '2026-03-12', 'Laptop',     'South',  7, 1000, 0.10),
            (18, 6, '2026-03-15', 'Monitor',    'East',   4,  400, 0.00);
        """
    )

    return connection


# ---------------------------------------------------------------------------
# 1. Basic aggregation
# ---------------------------------------------------------------------------

def demonstrate_basic_grouping(connection: sqlite3.Connection) -> None:
    print_title("1. GROUP BY creates groups before HAVING can filter them")

    run_query(
        connection,
        """
        SELECT
            region,
            COUNT(*) AS transaction_count,
            SUM(quantity) AS units_sold,
            ROUND(SUM(quantity * unit_price * (1 - discount)), 2)
                AS revenue
        FROM sales
        GROUP BY region
        ORDER BY revenue DESC;
        """,
    )

    print(
        """
GROUP BY does not filter individual rows.
It partitions rows into groups.

COUNT(), SUM(), AVG(), MIN(), and MAX() then calculate values for each group.

HAVING becomes useful when a condition depends on one of those group-level
calculations.
"""
    )


# ---------------------------------------------------------------------------
# 2. WHERE filters rows
# ---------------------------------------------------------------------------

def demonstrate_where(connection: sqlite3.Connection) -> None:
    print_title("2. WHERE filters rows before aggregation")

    run_query(
        connection,
        """
        SELECT
            region,
            COUNT(*) AS transaction_count,
            SUM(quantity) AS units_sold
        FROM sales
        WHERE sale_date >= '2026-02-01'
        GROUP BY region
        ORDER BY region;
        """,
    )

    print(
        """
The WHERE predicate examines individual sales rows.

It is evaluated before GROUP BY, so January rows do not participate in the
February-and-March aggregation.
"""
    )


# ---------------------------------------------------------------------------
# 3. HAVING filters groups
# ---------------------------------------------------------------------------

def demonstrate_having(connection: sqlite3.Connection) -> None:
    print_title("3. HAVING filters groups after aggregation")

    run_query(
        connection,
        """
        SELECT
            region,
            COUNT(*) AS transaction_count,
            SUM(quantity) AS units_sold
        FROM sales
        GROUP BY region
        HAVING SUM(quantity) >= 40
        ORDER BY units_sold DESC;
        """,
    )

    print(
        """
SUM(quantity) is a group-level value.

Therefore:

    HAVING SUM(quantity) >= 40

means:

    "Keep only regions whose total units sold are at least 40."

This is fundamentally different from:

    WHERE quantity >= 40

which would mean:

    "Keep individual sale rows whose quantity is at least 40."
"""
    )


# ---------------------------------------------------------------------------
# 4. WHERE and HAVING together
# ---------------------------------------------------------------------------

def demonstrate_where_and_having(connection: sqlite3.Connection) -> None:
    print_title("4. WHERE and HAVING working together")

    run_query(
        connection,
        """
        SELECT
            region,
            COUNT(*) AS transaction_count,
            ROUND(
                SUM(quantity * unit_price * (1 - discount)),
                2
            ) AS revenue
        FROM sales
        WHERE sale_date >= '2026-02-01'
        GROUP BY region
        HAVING SUM(quantity * unit_price * (1 - discount)) >= 5000
        ORDER BY revenue DESC;
        """,
    )

    print(
        """
The two filters operate at different levels.

WHERE:
    Removes individual rows before groups are created.

HAVING:
    Removes completed groups after aggregate values are calculated.

This is one of the most important patterns in analytical SQL.
"""
    )


# ---------------------------------------------------------------------------
# 5. HAVING with COUNT
# ---------------------------------------------------------------------------

def demonstrate_count_having(connection: sqlite3.Connection) -> None:
    print_title("5. HAVING with COUNT")

    run_query(
        connection,
        """
        SELECT
            employee_id,
            COUNT(*) AS number_of_sales
        FROM sales
        GROUP BY employee_id
        HAVING COUNT(*) >= 5
        ORDER BY number_of_sales DESC;
        """,
    )

    print(
        """
COUNT(*) counts rows in each employee group.

HAVING COUNT(*) >= 5 therefore identifies employees with at least five
transactions.
"""
    )


# ---------------------------------------------------------------------------
# 6. HAVING with AVG
# ---------------------------------------------------------------------------

def demonstrate_avg_having(connection: sqlite3.Connection) -> None:
    print_title("6. HAVING with AVG")

    run_query(
        connection,
        """
        SELECT
            employee_id,
            ROUND(AVG(unit_price), 2) AS average_unit_price
        FROM sales
        GROUP BY employee_id
        HAVING AVG(unit_price) > 400
        ORDER BY average_unit_price DESC;
        """,
    )

    print(
        """
AVG() produces one value per group.

The condition belongs in HAVING because the average does not exist until
the employee's rows have been grouped.
"""
    )


# ---------------------------------------------------------------------------
# 7. HAVING with multiple conditions
# ---------------------------------------------------------------------------

def demonstrate_multiple_having_conditions(
    connection: sqlite3.Connection,
) -> None:
    print_title("7. Multiple HAVING conditions")

    run_query(
        connection,
        """
        SELECT
            region,
            COUNT(*) AS transactions,
            SUM(quantity) AS units,
            ROUND(SUM(quantity * unit_price * (1 - discount)), 2)
                AS revenue
        FROM sales
        GROUP BY region
        HAVING COUNT(*) >= 4
           AND SUM(quantity) >= 30
           AND SUM(quantity * unit_price * (1 - discount)) >= 5000
        ORDER BY revenue DESC;
        """,
    )

    print(
        """
HAVING can contain compound Boolean expressions using AND, OR, and NOT.

Each condition is evaluated against the grouped result.
"""
    )


# ---------------------------------------------------------------------------
# 8. WHERE versus HAVING: intentionally different questions
# ---------------------------------------------------------------------------

def demonstrate_difference(connection: sqlite3.Connection) -> None:
    print_title("8. WHERE versus HAVING: different questions")

    print("\nQuestion A: Which individual sales contain at least 10 units?")
    run_query(
        connection,
        """
        SELECT sale_id, region, quantity
        FROM sales
        WHERE quantity >= 10
        ORDER BY quantity DESC;
        """,
    )

    print("\nQuestion B: Which regions sold at least 10 units in total?")
    run_query(
        connection,
        """
        SELECT region, SUM(quantity) AS total_units
        FROM sales
        GROUP BY region
        HAVING SUM(quantity) >= 10
        ORDER BY total_units DESC;
        """,
    )


# ---------------------------------------------------------------------------
# 9. WHERE cannot normally contain an aggregate
# ---------------------------------------------------------------------------

def demonstrate_aggregate_restriction(connection: sqlite3.Connection) -> None:
    print_title("9. Why aggregate conditions belong in HAVING")

    invalid_sql = """
        SELECT region, SUM(quantity) AS total_units
        FROM sales
        WHERE SUM(quantity) >= 40
        GROUP BY region;
    """

    print("Invalid query:")
    print(invalid_sql.strip())

    try:
        connection.execute(invalid_sql).fetchall()
    except sqlite3.Error as error:
        print("\nSQLite error:")
        print(error)

    print(
        """
The problem is logical timing.

WHERE operates on rows before grouping.
SUM(quantity) requires a group to exist.

The correct form is:

    SELECT region, SUM(quantity) AS total_units
    FROM sales
    GROUP BY region
    HAVING SUM(quantity) >= 40;
"""
    )


# ---------------------------------------------------------------------------
# 10. HAVING without GROUP BY
# ---------------------------------------------------------------------------

def demonstrate_having_without_group_by(connection: sqlite3.Connection) -> None:
    print_title("10. HAVING without an explicit GROUP BY")

    run_query(
        connection,
        """
        SELECT
            COUNT(*) AS total_transactions,
            SUM(quantity) AS total_units
        FROM sales
        HAVING SUM(quantity) >= 100;
        """,
    )

    print(
        """
Without GROUP BY, the aggregate query can be treated as one overall group.

HAVING can therefore filter that single aggregate result.

This pattern is useful for checks such as:

    "Return the report only when total revenue exceeds a threshold."

Support and exact behavior can vary between SQL dialects, so portable
queries should be written with the target database in mind.
"""
    )


# ---------------------------------------------------------------------------
# 11. DISTINCT and COUNT
# ---------------------------------------------------------------------------

def demonstrate_distinct_count(connection: sqlite3.Connection) -> None:
    print_title("11. COUNT(DISTINCT ...) with HAVING")

    run_query(
        connection,
        """
        SELECT
            employee_id,
            COUNT(DISTINCT product) AS different_products
        FROM sales
        GROUP BY employee_id
        HAVING COUNT(DISTINCT product) >= 3
        ORDER BY different_products DESC;
        """,
    )

    print(
        """
COUNT(DISTINCT expression) counts unique non-NULL values.

This is different from COUNT(*) and COUNT(column).
"""
    )


# ---------------------------------------------------------------------------
# 12. Conditional aggregation
# ---------------------------------------------------------------------------

def demonstrate_conditional_aggregation(
    connection: sqlite3.Connection,
) -> None:
    print_title("12. Conditional aggregation plus HAVING")

    run_query(
        connection,
        """
        SELECT
            region,
            SUM(
                CASE
                    WHEN product = 'Laptop' THEN quantity
                    ELSE 0
                END
            ) AS laptop_units,
            SUM(
                CASE
                    WHEN product = 'Monitor' THEN quantity
                    ELSE 0
                END
            ) AS monitor_units
        FROM sales
        GROUP BY region
        HAVING SUM(
            CASE
                WHEN product = 'Laptop' THEN quantity
                ELSE 0
            END
        ) >= 5
        ORDER BY laptop_units DESC;
        """,
    )

    print(
        """
Conditional aggregation lets one grouped query calculate multiple business
metrics.

CASE creates a conditional value for each input row.
SUM then adds those values within each group.
HAVING filters the resulting group-level metric.
"""
    )


# ---------------------------------------------------------------------------
# 13. HAVING with JOIN
# ---------------------------------------------------------------------------

def demonstrate_join_and_having(connection: sqlite3.Connection) -> None:
    print_title("13. JOIN + WHERE + GROUP BY + HAVING")

    run_query(
        connection,
        """
        SELECT
            d.department_name,
            COUNT(e.employee_id) AS active_employee_count,
            ROUND(AVG(e.salary), 2) AS average_salary
        FROM departments AS d
        JOIN employees AS e
            ON e.department_id = d.department_id
        WHERE e.active = 1
        GROUP BY d.department_id, d.department_name
        HAVING COUNT(e.employee_id) >= 2
        ORDER BY active_employee_count DESC;
        """,
    )

    print(
        """
This query demonstrates a complete analytical pipeline:

FROM/JOIN:
    Connect departments and employees.

WHERE:
    Keep only active employees.

GROUP BY:
    Build one group per department.

HAVING:
    Keep departments with at least two active employees.

SELECT:
    Return aggregate information.

ORDER BY:
    Sort the completed groups.
"""
    )


# ---------------------------------------------------------------------------
# 14. HAVING versus filtering an aggregate in a subquery
# ---------------------------------------------------------------------------

def demonstrate_subquery_equivalent(connection: sqlite3.Connection) -> None:
    print_title("14. HAVING versus an outer query on an aggregate subquery")

    print("Direct HAVING:")
    run_query(
        connection,
        """
        SELECT
            region,
            SUM(quantity) AS total_units
        FROM sales
        GROUP BY region
        HAVING SUM(quantity) >= 40
        ORDER BY total_units DESC;
        """,
    )

    print("\nEquivalent derived-table approach:")
    run_query(
        connection,
        """
        SELECT region, total_units
        FROM (
            SELECT
                region,
                SUM(quantity) AS total_units
            FROM sales
            GROUP BY region
        ) AS regional_totals
        WHERE total_units >= 40
        ORDER BY total_units DESC;
        """,
    )

    print(
        """
The subquery first materializes the aggregate result conceptually.

The outer WHERE then filters those already-aggregated rows.

This demonstrates why HAVING is naturally described as a group-level filter.
"""
    )


# ---------------------------------------------------------------------------
# 15. NULL behavior
# ---------------------------------------------------------------------------

def demonstrate_null_behavior(connection: sqlite3.Connection) -> None:
    print_title("15. NULL and aggregate behavior")

    connection.execute(
        """
        CREATE TABLE nullable_sales (
            sale_id INTEGER PRIMARY KEY,
            region TEXT,
            amount REAL
        );
        """
    )

    connection.executemany(
        """
        INSERT INTO nullable_sales(sale_id, region, amount)
        VALUES (?, ?, ?);
        """,
        [
            (1, "North", 100.0),
            (2, "North", None),
            (3, "North", 200.0),
            (4, "South", None),
            (5, "South", None),
            (6, "East", 50.0),
        ],
    )

    run_query(
        connection,
        """
        SELECT
            region,
            COUNT(*) AS row_count,
            COUNT(amount) AS non_null_amount_count,
            SUM(amount) AS total_amount,
            AVG(amount) AS average_amount
        FROM nullable_sales
        GROUP BY region
        ORDER BY region;
        """,
    )

    run_query(
        connection,
        """
        SELECT
            region,
            SUM(amount) AS total_amount
        FROM nullable_sales
        GROUP BY region
        HAVING SUM(amount) >= 100
        ORDER BY region;
        """,
    )

    print(
        """
COUNT(*) counts rows.
COUNT(column) ignores NULL values.
SUM(column) and AVG(column) generally ignore NULL values.

For a group containing only NULL amounts, SUM(amount) is NULL in SQLite.
The comparison:

    NULL >= 100

does not evaluate to TRUE, so the group is removed by HAVING.

NULL is not equivalent to zero.
"""
    )


# ---------------------------------------------------------------------------
# 16. Date filtering
# ---------------------------------------------------------------------------

def demonstrate_date_filtering(connection: sqlite3.Connection) -> None:
    print_title("16. Date filtering with WHERE and HAVING")

    run_query(
        connection,
        """
        SELECT
            region,
            SUM(quantity) AS units
        FROM sales
        WHERE sale_date BETWEEN '2026-02-01' AND '2026-02-28'
        GROUP BY region
        HAVING SUM(quantity) >= 10
        ORDER BY units DESC;
        """,
    )

    print(
        """
The date restriction belongs in WHERE because it describes which input rows
are included.

The minimum units requirement belongs in HAVING because it describes the
result of aggregation.
"""
    )


# ---------------------------------------------------------------------------
# 17. HAVING and ORDER BY
# ---------------------------------------------------------------------------

def demonstrate_order_and_limit(connection: sqlite3.Connection) -> None:
    print_title("17. HAVING + ORDER BY + LIMIT")

    run_query(
        connection,
        """
        SELECT
            employee_id,
            ROUND(SUM(quantity * unit_price * (1 - discount)), 2)
                AS revenue
        FROM sales
        GROUP BY employee_id
        HAVING SUM(quantity * unit_price * (1 - discount)) >= 3000
        ORDER BY revenue DESC
        LIMIT 3;
        """,
    )

    print(
        """
HAVING removes groups that do not satisfy the business threshold.
ORDER BY sorts the remaining groups.
LIMIT returns only the requested number of rows.

This pattern is common in leaderboards and top-performer reports.
"""
    )


# ---------------------------------------------------------------------------
# 18. Query design patterns
# ---------------------------------------------------------------------------

def demonstrate_design_patterns(connection: sqlite3.Connection) -> None:
    print_title("18. Practical HAVING design patterns")

    patterns = {
        "Customers with at least N orders":
            """
            SELECT customer_id, COUNT(*) AS order_count
            FROM orders
            GROUP BY customer_id
            HAVING COUNT(*) >= 5;
            """,

        "Departments with high payroll":
            """
            SELECT department_id, SUM(salary) AS payroll
            FROM employees
            GROUP BY department_id
            HAVING SUM(salary) > 500000;
            """,

        "Products with sufficient sales":
            """
            SELECT product_id, SUM(quantity) AS units
            FROM order_items
            GROUP BY product_id
            HAVING SUM(quantity) >= 100;
            """,

        "Regions with strong average order value":
            """
            SELECT region, AVG(order_value) AS average_value
            FROM orders
            GROUP BY region
            HAVING AVG(order_value) >= 1000;
            """,
    }

    for name, example in patterns.items():
        print(f"\n{name}")
        print(example.strip())

    print(
        """
The recurring pattern is:

    SELECT grouping_columns, aggregate_expression
    FROM source
    WHERE row_conditions
    GROUP BY grouping_columns
    HAVING aggregate_conditions
    ORDER BY ...

Ask:

    1. Is the condition about one input row?
       -> WHERE

    2. Is the condition about a group or aggregate?
       -> HAVING
"""
    )


# ---------------------------------------------------------------------------
# 19. Performance considerations
# ---------------------------------------------------------------------------

def demonstrate_performance_principles() -> None:
    print_title("19. Performance principles")

    print(
        """
1. Filter early when the condition genuinely belongs in WHERE.

   WHERE sale_date >= '2026-01-01'

   can reduce the number of rows that must be grouped.

2. Do not move an aggregate condition into WHERE merely for performance.
   That changes the meaning and is generally invalid.

3. Index columns commonly used in selective WHERE predicates, JOIN
   predicates, and grouping patterns according to the database workload.

4. Avoid applying functions to indexed columns in predicates when that
   prevents efficient index usage.

5. Aggregate only the columns and rows required by the report.

6. Examine the database's execution plan for large production datasets.

7. HAVING may require the database to perform grouping before it can decide
   whether a group survives.

8. A semantically equivalent rewrite using a subquery is not automatically
   faster. Query planners may transform both forms.

9. Performance depends on the database engine, statistics, indexes, data
   distribution, cardinality, memory, and query plan.

10. Measure production queries rather than assuming that one formulation is
    universally faster.
"""
    )


# ---------------------------------------------------------------------------
# 20. Security considerations
# ---------------------------------------------------------------------------

def demonstrate_parameterized_sql(connection: sqlite3.Connection) -> None:
    print_title("20. SQL security: parameterized values")

    minimum_units = 20

    run_query(
        connection,
        """
        SELECT
            region,
            SUM(quantity) AS total_units
        FROM sales
        GROUP BY region
        HAVING SUM(quantity) >= ?
        ORDER BY total_units DESC;
        """,
        (minimum_units,),
    )

    print(
        """
Parameterized SQL keeps user-supplied values separate from SQL syntax.

Avoid constructing SQL like:

    "... HAVING SUM(quantity) >= " + user_input

when user_input comes from an untrusted source.

Parameterization is a fundamental defense against SQL injection.

Column names, table names, and SQL keywords cannot normally be supplied as
ordinary value parameters. Dynamic identifiers require controlled validation
or a trusted mapping.
"""
    )


# ---------------------------------------------------------------------------
# 21. Testing SQL logic
# ---------------------------------------------------------------------------

def demonstrate_testing(connection: sqlite3.Connection) -> None:
    print_title("21. Testing aggregate filters")

    query = """
        SELECT region, SUM(quantity) AS total_units
        FROM sales
        GROUP BY region
        HAVING SUM(quantity) >= ?
        ORDER BY region;
    """

    rows = connection.execute(query, (40,)).fetchall()
    result = [(row["region"], row["total_units"]) for row in rows]

    assert all(units >= 40 for _, units in result)
    assert result == [("East", 61), ("North", 66), ("South", 41)]

    print("Test 1 passed: every returned region meets the HAVING threshold.")

    rows = connection.execute(query, (10_000,)).fetchall()
    assert rows == []

    print("Test 2 passed: an impossible threshold returns no groups.")

    rows = connection.execute(query, (0,)).fetchall()
    assert len(rows) == 3

    print("Test 3 passed: threshold zero includes all three regions.")


# ---------------------------------------------------------------------------
# 22. Common mistakes
# ---------------------------------------------------------------------------

def demonstrate_common_mistakes() -> None:
    print_title("22. Common mistakes")

    mistakes = [
        (
            "Using WHERE for aggregate conditions",
            "WHERE SUM(amount) > 10000",
            "Use HAVING SUM(amount) > 10000."
        ),
        (
            "Confusing row count with group count",
            "WHERE COUNT(*) >= 5",
            "Use GROUP BY ... HAVING COUNT(*) >= 5."
        ),
        (
            "Filtering before aggregation when the business rule is after aggregation",
            "WHERE quantity >= 10",
            "Use HAVING SUM(quantity) >= 10 when the requirement concerns total units."
        ),
        (
            "Treating NULL as zero",
            "HAVING SUM(amount) >= 0",
            "Decide explicitly whether NULL should be ignored, converted with COALESCE, or treated differently."
        ),
        (
            "Forgetting GROUP BY columns",
            "SELECT region, SUM(amount) FROM sales",
            "Use GROUP BY region when a separate result is required per region."
        ),
    ]

    for title, bad, correction in mistakes:
        print(f"\n{title}")
        print(f"Incorrect or misleading pattern: {bad}")
        print(f"Better approach: {correction}")


# ---------------------------------------------------------------------------
# 23. Advanced reporting query
# ---------------------------------------------------------------------------

def demonstrate_advanced_report(connection: sqlite3.Connection) -> None:
    print_title("23. Advanced report: profitable sales regions")

    run_query(
        connection,
        """
        SELECT
            s.region,
            COUNT(DISTINCT s.employee_id) AS active_sellers,
            COUNT(*) AS transactions,
            SUM(s.quantity) AS units_sold,
            ROUND(
                SUM(s.quantity * s.unit_price * (1 - s.discount)),
                2
            ) AS revenue,
            ROUND(
                AVG(s.quantity * s.unit_price * (1 - s.discount)),
                2
            ) AS average_transaction_value
        FROM sales AS s
        JOIN employees AS e
            ON e.employee_id = s.employee_id
        WHERE e.active = 1
          AND s.sale_date >= '2026-01-01'
        GROUP BY s.region
        HAVING COUNT(*) >= 4
           AND SUM(s.quantity) >= 30
           AND SUM(
                s.quantity * s.unit_price * (1 - s.discount)
           ) >= 5000
        ORDER BY revenue DESC;
        """,
    )

    print(
        """
This is a realistic analytical query.

The row-level restrictions are handled by WHERE.
The group-level business rules are handled by HAVING.

The query calculates several metrics simultaneously without requiring
multiple separate aggregation passes at the SQL-language level.
"""
    )


# ---------------------------------------------------------------------------
# 24. Logical processing demonstration
# ---------------------------------------------------------------------------

def demonstrate_logical_order() -> None:
    print_title("24. SQL logical processing order")

    stages = [
        ("1. FROM / JOIN", "Determine the source rows and combine related tables."),
        ("2. WHERE", "Remove individual rows that do not satisfy row-level predicates."),
        ("3. GROUP BY", "Partition the remaining rows into groups."),
        ("4. Aggregate functions", "Conceptually calculate COUNT, SUM, AVG, MIN, MAX, etc."),
        ("5. HAVING", "Remove groups that do not satisfy group-level predicates."),
        ("6. SELECT", "Produce the requested output expressions."),
        ("7. ORDER BY", "Sort the resulting rows."),
        ("8. LIMIT / OFFSET", "Restrict the final result set."),
    ]

    for stage, explanation in stages:
        print(f"{stage:<25} {explanation}")

    print(
        """
SQL syntax order and logical processing order are not identical.

A query is written with SELECT near the beginning:

    SELECT ...
    FROM ...
    WHERE ...
    GROUP BY ...
    HAVING ...
    ORDER BY ...

but its logical processing is commonly understood with FROM/WHERE/GROUP BY/
HAVING preceding SELECT and ORDER BY.
"""
    )


# ---------------------------------------------------------------------------
# 25. Mini interactive example
# ---------------------------------------------------------------------------

def interactive_report(connection: sqlite3.Connection) -> None:
    print_title("25. Interactive HAVING threshold")

    raw_value = input(
        "Enter a minimum total-unit threshold, or press Enter for 40: "
    ).strip()

    if not raw_value:
        threshold = 40
    else:
        try:
            threshold = int(raw_value)
        except ValueError:
            print("Invalid integer. Using 40.")
            threshold = 40

    if threshold < 0:
        print("Negative thresholds are not useful for this report. Using 0.")
        threshold = 0

    run_query(
        connection,
        """
        SELECT
            region,
            SUM(quantity) AS total_units,
            ROUND(
                SUM(quantity * unit_price * (1 - discount)),
                2
            ) AS revenue
        FROM sales
        GROUP BY region
        HAVING SUM(quantity) >= ?
        ORDER BY total_units DESC;
        """,
        (threshold,),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print_title("HAVING: Filtering Aggregated Results")
    print(
        """
This program uses a small sales database to demonstrate the difference
between row-level filtering and group-level filtering.

Key rule:

    WHERE  -> rows
    GROUP BY -> groups
    HAVING -> groups after aggregation
"""
    )

    connection = create_database()

    try:
        demonstrate_basic_grouping(connection)
        demonstrate_where(connection)
        demonstrate_having(connection)
        demonstrate_where_and_having(connection)
        demonstrate_count_having(connection)
        demonstrate_avg_having(connection)
        demonstrate_multiple_having_conditions(connection)
        demonstrate_difference(connection)
        demonstrate_aggregate_restriction(connection)
        demonstrate_having_without_group_by(connection)
        demonstrate_distinct_count(connection)
        demonstrate_conditional_aggregation(connection)
        demonstrate_join_and_having(connection)
        demonstrate_subquery_equivalent(connection)
        demonstrate_null_behavior(connection)
        demonstrate_date_filtering(connection)
        demonstrate_order_and_limit(connection)
        demonstrate_design_patterns()
        demonstrate_performance_principles()
        demonstrate_parameterized_sql(connection)
        demonstrate_testing(connection)
        demonstrate_common_mistakes()
        demonstrate_advanced_report(connection)
        demonstrate_logical_order()

        # The interactive section is deliberately last so the study material
        # can be run non-interactively until the final demonstration.
        interactive_report(connection)

    finally:
        connection.close()

    print_title("Study program completed")


if __name__ == "__main__":
    main()
