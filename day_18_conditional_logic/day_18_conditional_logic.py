"""
Conditional Logic with SQL CASE, WHEN, THEN, ELSE, and Conditional Expressions

This standalone study file teaches SQL conditional logic from beginner concepts
through advanced patterns. SQLite is used because it is included in Python's
standard library and therefore requires no external package.

Topics demonstrated:
- CASE expressions
- Simple CASE
- Searched CASE
- WHEN / THEN / ELSE
- CASE without ELSE
- NULL behavior
- CASE inside SELECT, WHERE, ORDER BY, GROUP BY, and aggregate functions
- Conditional aggregation
- Nested CASE
- CASE with arithmetic and string expressions
- COALESCE and NULLIF as related conditional expressions
- Boolean conditions
- Date and numeric classification
- Conditional ordering
- Data-quality rules
- Rule precedence
- Common mistakes
- Performance considerations
- A realistic order-pricing and customer-segmentation case study
"""

import sqlite3
from dataclasses import dataclass
from typing import Iterable


def print_title(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_rows(cursor: sqlite3.Cursor) -> None:
    columns = [description[0] for description in cursor.description]
    print(" | ".join(columns))
    print("-" * max(20, len(" | ".join(columns))))
    for row in cursor.fetchall():
        print(" | ".join("NULL" if value is None else str(value) for value in row))


def run_query(connection: sqlite3.Connection, sql: str, parameters: tuple = ()) -> None:
    cursor = connection.execute(sql, parameters)
    print_rows(cursor)


def create_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            country TEXT NOT NULL,
            loyalty_points INTEGER NOT NULL DEFAULT 0,
            account_balance REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_status TEXT,
            shipping_country TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        INSERT INTO customers
            (customer_id, customer_name, country, loyalty_points, account_balance)
        VALUES
            (1, 'Asha', 'India', 120, 5000),
            (2, 'Ravi', 'India', 40, 1800),
            (3, 'Maya', 'USA', 800, 12000),
            (4, 'Noah', 'UK', 15, 500),
            (5, 'Iris', 'India', 300, 7500),
            (6, 'Omar', 'UAE', 0, 250);

        INSERT INTO orders
            (order_id, customer_id, order_date, amount, payment_status, shipping_country)
        VALUES
            (101, 1, '2026-01-05', 1250, 'PAID', 'India'),
            (102, 1, '2026-02-15', 450, 'PAID', 'India'),
            (103, 2, '2026-02-20', 90, 'PENDING', 'India'),
            (104, 2, '2026-03-01', 700, 'PAID', 'India'),
            (105, 3, '2026-03-03', 4200, 'PAID', 'USA'),
            (106, 3, '2026-03-18', 1500, 'FAILED', 'USA'),
            (107, 4, '2026-03-19', 50, 'PAID', 'UK'),
            (108, 5, '2026-03-20', 2200, 'PAID', 'India'),
            (109, 5, '2026-04-01', 300, NULL, 'India'),
            (110, 6, '2026-04-05', 0, 'PAID', 'UAE');
        """
    )
    return connection


def beginner_simple_case(connection: sqlite3.Connection) -> None:
    print_title("1. Simple CASE expression")

    sql = """
        SELECT
            customer_name,
            country,
            CASE country
                WHEN 'India' THEN 'Domestic'
                WHEN 'USA' THEN 'North America'
                WHEN 'UK' THEN 'United Kingdom'
                ELSE 'Other'
            END AS market
        FROM customers
        ORDER BY customer_id;
    """
    run_query(connection, sql)

    print("\nSimple CASE compares one expression against several values.")
    print("Conceptually: CASE expression WHEN value THEN result ... ELSE result END")


def searched_case(connection: sqlite3.Connection) -> None:
    print_title("2. Searched CASE expression")

    sql = """
        SELECT
            customer_name,
            loyalty_points,
            CASE
                WHEN loyalty_points >= 500 THEN 'Platinum'
                WHEN loyalty_points >= 200 THEN 'Gold'
                WHEN loyalty_points >= 100 THEN 'Silver'
                ELSE 'Standard'
            END AS loyalty_tier
        FROM customers
        ORDER BY loyalty_points DESC;
    """
    run_query(connection, sql)

    print("\nSearched CASE evaluates Boolean conditions.")
    print("The first matching WHEN condition determines the result.")


def case_without_else(connection: sqlite3.Connection) -> None:
    print_title("3. CASE without ELSE and the resulting NULL")

    sql = """
        SELECT
            order_id,
            payment_status,
            CASE
                WHEN payment_status = 'PAID' THEN 'Completed'
                WHEN payment_status = 'PENDING' THEN 'Awaiting payment'
            END AS payment_description
        FROM orders
        ORDER BY order_id;
    """
    run_query(connection, sql)

    print("\nIf no WHEN condition matches and ELSE is absent, CASE returns NULL.")


def case_in_select(connection: sqlite3.Connection) -> None:
    print_title("4. CASE in SELECT for derived values")

    sql = """
        SELECT
            order_id,
            amount,
            CASE
                WHEN amount = 0 THEN 'Zero-value order'
                WHEN amount < 100 THEN 'Small'
                WHEN amount < 1000 THEN 'Medium'
                WHEN amount < 3000 THEN 'Large'
                ELSE 'Very large'
            END AS order_size
        FROM orders
        ORDER BY amount;
    """
    run_query(connection, sql)


def case_in_where(connection: sqlite3.Connection) -> None:
    print_title("5. CASE in WHERE")

    sql = """
        SELECT order_id, amount, payment_status
        FROM orders
        WHERE CASE
            WHEN payment_status = 'PAID' AND amount >= 1000 THEN 1
            WHEN payment_status = 'PENDING' AND amount >= 500 THEN 1
            ELSE 0
        END = 1
        ORDER BY order_id;
    """
    run_query(connection, sql)

    print("\nCASE can produce a value used by another SQL clause.")
    print("For simple predicates, direct Boolean conditions are often clearer.")


def case_in_order_by(connection: sqlite3.Connection) -> None:
    print_title("6. CASE in ORDER BY")

    sql = """
        SELECT order_id, payment_status, amount
        FROM orders
        ORDER BY
            CASE payment_status
                WHEN 'PENDING' THEN 1
                WHEN 'FAILED' THEN 2
                WHEN 'PAID' THEN 3
                ELSE 4
            END,
            amount DESC;
    """
    run_query(connection, sql)

    print("\nCASE can implement business-specific sorting priorities.")


def case_in_group_by(connection: sqlite3.Connection) -> None:
    print_title("7. CASE in GROUP BY")

    sql = """
        SELECT
            CASE
                WHEN amount < 100 THEN 'Small'
                WHEN amount < 1000 THEN 'Medium'
                ELSE 'Large'
            END AS order_class,
            COUNT(*) AS order_count,
            ROUND(AVG(amount), 2) AS average_amount
        FROM orders
        GROUP BY
            CASE
                WHEN amount < 100 THEN 'Small'
                WHEN amount < 1000 THEN 'Medium'
                ELSE 'Large'
            END
        ORDER BY average_amount;
    """
    run_query(connection, sql)


def conditional_aggregation(connection: sqlite3.Connection) -> None:
    print_title("8. Conditional aggregation")

    sql = """
        SELECT
            COUNT(*) AS total_orders,
            SUM(CASE WHEN payment_status = 'PAID' THEN 1 ELSE 0 END) AS paid_orders,
            SUM(CASE WHEN payment_status = 'PENDING' THEN 1 ELSE 0 END) AS pending_orders,
            SUM(CASE WHEN payment_status = 'FAILED' THEN 1 ELSE 0 END) AS failed_orders,
            ROUND(
                100.0 * SUM(CASE WHEN payment_status = 'PAID' THEN 1 ELSE 0 END)
                / COUNT(*),
                2
            ) AS paid_percentage
        FROM orders;
    """
    run_query(connection, sql)

    print("\nConditional aggregation converts row-level conditions into metrics.")
    print("This pattern is widely used in dashboards and analytical SQL.")


def nested_case(connection: sqlite3.Connection) -> None:
    print_title("9. Nested CASE")

    sql = """
        SELECT
            order_id,
            amount,
            payment_status,
            CASE
                WHEN payment_status = 'PAID' THEN
                    CASE
                        WHEN amount >= 3000 THEN 'Paid - high value'
                        WHEN amount >= 1000 THEN 'Paid - medium value'
                        ELSE 'Paid - low value'
                    END
                WHEN payment_status = 'PENDING' THEN 'Payment pending'
                WHEN payment_status = 'FAILED' THEN 'Payment failed'
                ELSE 'Unknown payment state'
            END AS business_state
        FROM orders
        ORDER BY order_id;
    """
    run_query(connection, sql)

    print("\nNested CASE is useful when rules naturally have multiple levels.")
    print("Deep nesting can reduce readability and may justify a lookup table.")


def null_logic(connection: sqlite3.Connection) -> None:
    print_title("10. NULL and three-valued logic")

    sql = """
        SELECT
            order_id,
            payment_status,
            CASE
                WHEN payment_status IS NULL THEN 'Status missing'
                WHEN payment_status = 'PAID' THEN 'Paid'
                ELSE 'Known non-paid state'
            END AS interpreted_status
        FROM orders
        ORDER BY order_id;
    """
    run_query(connection, sql)

    print("\nNULL is not an ordinary value.")
    print("Use IS NULL or IS NOT NULL rather than '= NULL' or '<> NULL'.")


def coalesce_and_nullif(connection: sqlite3.Connection) -> None:
    print_title("11. Related conditional expressions: COALESCE and NULLIF")

    sql = """
        SELECT
            order_id,
            payment_status,
            COALESCE(payment_status, 'UNKNOWN') AS safe_status,
            NULLIF(amount, 0) AS nonzero_amount
        FROM orders
        ORDER BY order_id;
    """
    run_query(connection, sql)

    print("\nCOALESCE returns the first non-NULL expression.")
    print("NULLIF returns NULL when its two expressions are equal.")


def safe_ratio(connection: sqlite3.Connection) -> None:
    print_title("12. Protecting calculations with CASE")

    sql = """
        SELECT
            customer_id,
            SUM(amount) AS total_amount,
            COUNT(*) AS order_count,
            CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE ROUND(SUM(amount) / COUNT(*), 2)
            END AS average_order_value
        FROM orders
        GROUP BY customer_id
        ORDER BY customer_id;
    """
    run_query(connection, sql)

    print("\nCASE can guard calculations against business-specific invalid states.")


def parameterized_case(connection: sqlite3.Connection, minimum_amount: float) -> None:
    print_title("13. Parameterized conditional logic")

    sql = """
        SELECT
            order_id,
            amount,
            CASE
                WHEN amount >= ? THEN 'Meets threshold'
                ELSE 'Below threshold'
            END AS threshold_result
        FROM orders
        ORDER BY amount DESC;
    """
    run_query(connection, sql, (minimum_amount,))


def python_equivalent(amount: float) -> str:
    """
    This function mirrors a SQL searched CASE using Python's if/elif/else.

    SQL:
        CASE
            WHEN amount >= 3000 THEN 'Very large'
            WHEN amount >= 1000 THEN 'Large'
            WHEN amount >= 100 THEN 'Medium'
            ELSE 'Small'
        END
    """
    if amount >= 3000:
        return "Very large"
    elif amount >= 1000:
        return "Large"
    elif amount >= 100:
        return "Medium"
    else:
        return "Small"


def python_conditional_expression(amount: float) -> str:
    """Demonstrate Python's conditional expression, analogous to a simple CASE."""
    return "Non-zero" if amount != 0 else "Zero"


def python_examples() -> None:
    print_title("14. Python conditional expressions related to SQL CASE")

    amounts = [0, 50, 500, 1500, 5000]
    for amount in amounts:
        print(
            f"amount={amount:>5} -> "
            f"class={python_equivalent(amount):<10} | "
            f"zero_test={python_conditional_expression(amount)}"
        )

    print("\nPython uses if/elif/else for multi-condition logic.")
    print("Python's conditional expression has the form: value_if_true if condition else value_if_false.")


@dataclass(frozen=True)
class DiscountRule:
    minimum_amount: float
    discount_rate: float
    label: str


def calculate_discount(amount: float, rules: Iterable[DiscountRule]) -> tuple[float, str]:
    """
    Apply the first matching rule.

    The rules must be ordered from the most restrictive/highest threshold
    to the least restrictive threshold, just as WHEN clauses depend on order.
    """
    for rule in rules:
        if amount >= rule.minimum_amount:
            discount = amount * rule.discount_rate
            return round(discount, 2), rule.label

    return 0.0, "No discount"


def rule_engine_example() -> None:
    print_title("15. Application-style rule evaluation")

    rules = [
        DiscountRule(3000, 0.15, "Premium discount"),
        DiscountRule(1000, 0.10, "Large-order discount"),
        DiscountRule(500, 0.05, "Standard discount"),
    ]

    for amount in [50, 500, 750, 1200, 5000]:
        discount, label = calculate_discount(amount, rules)
        print(
            f"amount={amount:>5.2f} "
            f"discount={discount:>7.2f} "
            f"rule={label}"
        )

    print("\nRule ordering matters.")
    print("This is the same first-match principle used by searched CASE.")


def common_mistakes(connection: sqlite3.Connection) -> None:
    print_title("16. Common mistakes and their corrected forms")

    print("Mistake: CASE country WHEN country = 'India' THEN ...")
    print("Correct simple CASE: CASE country WHEN 'India' THEN ... END")
    print("Correct searched CASE: CASE WHEN country = 'India' THEN ... END")

    print("\nMistake: payment_status = NULL")
    print("Correct: payment_status IS NULL")

    print("\nMistake: overlapping rules in the wrong order")
    print("Example:")
    print("  WHEN amount >= 100 THEN 'Large'")
    print("  WHEN amount >= 1000 THEN 'Very large'")
    print("The second condition can never be reached for amounts >= 1000.")

    print("\nDemonstration of the ordering problem:")
    bad_sql = """
        SELECT
            order_id,
            amount,
            CASE
                WHEN amount >= 100 THEN 'Large'
                WHEN amount >= 1000 THEN 'Very large'
                ELSE 'Small'
            END AS incorrect_classification
        FROM orders
        WHERE amount >= 1000
        ORDER BY amount;
    """
    run_query(connection, bad_sql)

    print("\nCorrect ordering:")
    good_sql = """
        SELECT
            order_id,
            amount,
            CASE
                WHEN amount >= 1000 THEN 'Very large'
                WHEN amount >= 100 THEN 'Large'
                ELSE 'Small'
            END AS correct_classification
        FROM orders
        WHERE amount >= 1000
        ORDER BY amount;
    """
    run_query(connection, good_sql)


def realistic_customer_report(connection: sqlite3.Connection) -> None:
    print_title("17. Realistic customer classification report")

    sql = """
        WITH customer_metrics AS (
            SELECT
                c.customer_id,
                c.customer_name,
                c.country,
                c.loyalty_points,
                COALESCE(SUM(o.amount), 0) AS total_spend,
                COUNT(o.order_id) AS order_count,
                SUM(
                    CASE
                        WHEN o.payment_status = 'PAID' THEN o.amount
                        ELSE 0
                    END
                ) AS paid_spend
            FROM customers AS c
            LEFT JOIN orders AS o
                ON o.customer_id = c.customer_id
            GROUP BY
                c.customer_id,
                c.customer_name,
                c.country,
                c.loyalty_points
        )
        SELECT
            customer_name,
            country,
            loyalty_points,
            total_spend,
            order_count,
            ROUND(paid_spend, 2) AS paid_spend,
            CASE
                WHEN total_spend >= 5000 AND loyalty_points >= 500
                    THEN 'Strategic customer'
                WHEN total_spend >= 2000 OR loyalty_points >= 300
                    THEN 'High-value customer'
                WHEN total_spend >= 500 OR loyalty_points >= 100
                    THEN 'Growing customer'
                ELSE 'Standard customer'
            END AS customer_segment,
            CASE
                WHEN order_count = 0 THEN 'No orders'
                WHEN paid_spend = total_spend THEN 'All orders paid'
                WHEN paid_spend > 0 THEN 'Mixed payment state'
                ELSE 'No paid orders'
            END AS payment_profile
        FROM customer_metrics
        ORDER BY total_spend DESC;
    """
    run_query(connection, sql)


def explain_precedence() -> None:
    print_title("18. CASE rule precedence")

    print(
        """
CASE is generally evaluated from top to bottom.
For a searched CASE:

    CASE
        WHEN condition_1 THEN result_1
        WHEN condition_2 THEN result_2
        ELSE default_result
    END

The first condition that evaluates to true supplies the result.

Therefore:
- Put more specific rules before broad rules.
- Make overlapping conditions deliberate.
- Include ELSE when an explicit default is meaningful.
- Treat NULL deliberately.
- Test boundary values such as 99.99, 100, and 100.01.
"""
    )


def boundary_tests(connection: sqlite3.Connection) -> None:
    print_title("19. Boundary-value testing")

    sql = """
        WITH test_values(amount) AS (
            VALUES
                (99.99),
                (100.00),
                (100.01),
                (999.99),
                (1000.00),
                (1000.01)
        )
        SELECT
            amount,
            CASE
                WHEN amount >= 1000 THEN 'Large'
                WHEN amount >= 100 THEN 'Medium'
                ELSE 'Small'
            END AS classification
        FROM test_values
        ORDER BY amount;
    """
    run_query(connection, sql)

    print("\nBoundary tests expose errors in >= versus > and <= versus <.")


def performance_discussion() -> None:
    print_title("20. Performance and design considerations")

    print(
        """
1. CASE itself is usually inexpensive compared with large joins, scans, sorting,
   aggregation, or remote data access.

2. A CASE expression in SELECT is often a good way to derive display or business
   categories.

3. A CASE wrapped around an indexed column in a WHERE predicate can make index
   usage more difficult. Prefer a direct predicate when it expresses the same
   requirement clearly.

4. Repeating a large CASE expression in many queries can create maintenance risk.
   A reference table, view, generated column, or centralized business-rule layer
   may be more appropriate.

5. Rule order is part of the logic. Reordering WHEN clauses can change results.

6. CASE is an expression, not a procedural control-flow statement. It returns a
   value that participates in a SQL expression.

7. For a small stable set of categories, CASE is concise. For frequently changing
   business rules, data-driven rules stored in tables can be easier to maintain.
"""
    )


def run_all_examples() -> None:
    connection = create_database()

    try:
        beginner_simple_case(connection)
        searched_case(connection)
        case_without_else(connection)
        case_in_select(connection)
        case_in_where(connection)
        case_in_order_by(connection)
        case_in_group_by(connection)
        conditional_aggregation(connection)
        nested_case(connection)
        null_logic(connection)
        coalesce_and_nullif(connection)
        safe_ratio(connection)
        parameterized_case(connection, 1000)
        python_examples()
        rule_engine_example()
        common_mistakes(connection)
        realistic_customer_report(connection)
        explain_precedence()
        boundary_tests(connection)
        performance_discussion()

        print_title("21. Final executable checks")

        assertions = {
            "zero": python_equivalent(0) == "Small",
            "boundary_100": python_equivalent(100) == "Medium",
            "boundary_1000": python_equivalent(1000) == "Large",
            "boundary_3000": python_equivalent(3000) == "Very large",
        }

        for name, passed in assertions.items():
            print(f"{name}: {'PASS' if passed else 'FAIL'}")

        assert all(assertions.values())

    finally:
        connection.close()


if __name__ == "__main__":
    run_all_examples()
