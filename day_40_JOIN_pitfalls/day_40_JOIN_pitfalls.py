"""
JOIN Pitfalls: duplicate rows, accidental Cartesian products, NULL behavior,
and incorrect joins.

This executable script builds an in-memory relational-style dataset and uses
only the Python standard library to demonstrate why joins produce unexpected
results and how to diagnose and prevent them.

The examples deliberately distinguish:
- duplicate rows caused by legitimate one-to-many relationships
- accidental Cartesian products caused by missing join predicates
- NULL semantics and why NULL does not equal NULL
- incomplete or incorrect join predicates
- outer-join filtering mistakes
- pre-aggregation as a way to control cardinality
- validation of expected join cardinality
- diagnostic techniques useful before writing production SQL
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Customer:
    customer_id: int
    name: str
    region: Optional[str]


@dataclass(frozen=True)
class Order:
    order_id: int
    customer_id: Optional[int]
    salesperson_id: Optional[int]
    amount: float
    status: str


@dataclass(frozen=True)
class Salesperson:
    salesperson_id: int
    name: str
    region: Optional[str]


@dataclass(frozen=True)
class OrderLine:
    order_id: int
    product_id: int
    quantity: int


@dataclass(frozen=True)
class Product:
    product_id: int
    product_name: str
    category: str


def inner_join(
    left: Iterable[dict],
    right: Iterable[dict],
    left_key,
    right_key,
) -> list[dict]:
    """Simple equality inner join.

    This implementation deliberately does not deduplicate rows. If multiple
    right-side records share the same key, every matching pair is produced.
    That behavior is the central reason one-to-many joins increase row count.
    """
    index = defaultdict(list)

    for right_row in right:
        index[right_key(right_row)].append(right_row)

    result = []

    for left_row in left:
        key = left_key(left_row)
        for right_row in index.get(key, []):
            merged = dict(left_row)
            for column, value in right_row.items():
                if column in merged:
                    merged[f"right_{column}"] = value
                else:
                    merged[column] = value
            result.append(merged)

    return result


def left_join(
    left: Iterable[dict],
    right: Iterable[dict],
    left_key,
    right_key,
) -> list[dict]:
    """Equality left join with None representing SQL-style NULL output."""
    index = defaultdict(list)

    for right_row in right:
        index[right_key(right_row)].append(right_row)

    right_columns = set()

    right_rows = list(right)
    for row in right_rows:
        right_columns.update(row)

    result = []

    for left_row in left:
        matches = index.get(left_key(left_row), [])

        if not matches:
            merged = dict(left_row)
            for column in right_columns:
                if column in merged:
                    merged[f"right_{column}"] = None
                else:
                    merged[column] = None
            result.append(merged)
            continue

        for right_row in matches:
            merged = dict(left_row)
            for column, value in right_row.items():
                if column in merged:
                    merged[f"right_{column}"] = value
                else:
                    merged[column] = value
            result.append(merged)

    return result


def cross_join(left: Iterable[dict], right: Iterable[dict]) -> list[dict]:
    """Produce every possible left/right pair.

    This is what a missing join predicate can effectively produce. For m rows
    on the left and n rows on the right, the result has m*n rows.
    """
    result = []

    for left_row in left:
        for right_row in right:
            merged = dict(left_row)
            for column, value in right_row.items():
                if column in merged:
                    merged[f"right_{column}"] = value
                else:
                    merged[column] = value
            result.append(merged)

    return result


def print_rows(title: str, rows: list[dict], limit: int = 12) -> None:
    print(f"\n=== {title} ===")
    print(f"Rows: {len(rows)}")

    for row in rows[:limit]:
        print(row)

    if len(rows) > limit:
        print(f"... {len(rows) - limit} additional rows omitted")


def sql_equals(left: object, right: object) -> bool:
    """Approximate SQL equality for ordinary join keys.

    SQL NULL never equals SQL NULL. Python's None would normally compare equal
    to itself, so this helper explicitly models SQL's three-valued behavior
    for equality joins.
    """
    if left is None or right is None:
        return False

    return left == right


def sql_inner_join(
    left: Iterable[dict],
    right: Iterable[dict],
    left_key,
    right_key,
) -> list[dict]:
    """Nested-loop equality join that explicitly models SQL NULL behavior."""
    result = []

    for left_row in left:
        for right_row in right:
            if sql_equals(left_key(left_row), right_key(right_row)):
                merged = dict(left_row)

                for column, value in right_row.items():
                    if column in merged:
                        merged[f"right_{column}"] = value
                    else:
                        merged[column] = value

                result.append(merged)

    return result


def group_count(rows: Iterable[dict], key_name: str) -> Counter:
    return Counter(row[key_name] for row in rows)


def demonstrate_basic_one_to_many() -> None:
    customers = [
        {"customer_id": 1, "name": "Asha"},
        {"customer_id": 2, "name": "Ravi"},
        {"customer_id": 3, "name": "Meera"},
    ]

    orders = [
        {"order_id": 101, "customer_id": 1, "amount": 250.00},
        {"order_id": 102, "customer_id": 1, "amount": 125.00},
        {"order_id": 103, "customer_id": 2, "amount": 500.00},
    ]

    joined = inner_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    print_rows("Legitimate one-to-many join", joined)

    counts = group_count(joined, "customer_id")
    print("Joined rows by customer:", dict(counts))

    print(
        "\nA customer with two orders legitimately appears twice. "
        "The duplicate-looking customer row is not necessarily bad data."
    )


def demonstrate_accidental_cartesian_product() -> None:
    employees = [
        {"employee_id": 1, "employee": "Asha"},
        {"employee_id": 2, "employee": "Ravi"},
        {"employee_id": 3, "employee": "Meera"},
    ]

    departments = [
        {"department_id": 10, "department": "Finance"},
        {"department_id": 20, "department": "Technology"},
        {"department_id": 30, "department": "Operations"},
        {"department_id": 40, "department": "Procurement"},
    ]

    result = cross_join(employees, departments)

    print_rows("Accidental Cartesian product", result)

    expected = len(employees) * len(departments)
    print(f"Expected Cartesian cardinality: {expected}")
    print(
        "If a query unexpectedly produces this multiplication, inspect the "
        "FROM/JOIN predicates before attempting DISTINCT."
    )


def demonstrate_missing_join_condition() -> None:
    customers = [
        {"customer_id": 1, "region": "North"},
        {"customer_id": 2, "region": "South"},
    ]

    orders = [
        {"order_id": 101, "customer_id": 1, "region": "North"},
        {"order_id": 102, "customer_id": 2, "region": "South"},
        {"order_id": 103, "customer_id": 1, "region": "North"},
    ]

    correct = inner_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    wrong = inner_join(
        customers,
        orders,
        lambda row: row["region"],
        lambda row: row["region"],
    )

    print_rows("Correct customer_id join", correct)
    print_rows(
        "Join using a non-key attribute instead of customer_id",
        wrong,
    )

    print(
        "\nJoining on a column that is not sufficiently unique can create "
        "many-to-many matches even when the column values look meaningful."
    )


def demonstrate_incomplete_composite_join() -> None:
    employees = [
        {"employee_id": 1, "assignment": "A", "hours": 8},
        {"employee_id": 1, "assignment": "B", "hours": 7},
        {"employee_id": 2, "assignment": "A", "hours": 6},
    ]

    rates = [
        {"employee_id": 1, "assignment": "A", "rate": 100},
        {"employee_id": 1, "assignment": "B", "rate": 150},
        {"employee_id": 2, "assignment": "A", "rate": 120},
    ]

    incomplete = inner_join(
        employees,
        rates,
        lambda row: row["employee_id"],
        lambda row: row["employee_id"],
    )

    correct = [
        {
            **employee,
            "rate": rate["rate"],
        }
        for employee in employees
        for rate in rates
        if employee["employee_id"] == rate["employee_id"]
        and employee["assignment"] == rate["assignment"]
    ]

    print_rows("Incomplete composite join", incomplete)
    print_rows("Correct composite join", correct)

    print(
        "\nWhen identity is defined by multiple columns, every identifying "
        "column belongs in the join predicate."
    )


def demonstrate_null_behavior() -> None:
    left = [
        {"customer_id": 1, "name": "Asha"},
        {"customer_id": None, "name": "Unknown Customer"},
        {"customer_id": 2, "name": "Ravi"},
    ]

    right = [
        {"customer_id": 1, "segment": "Enterprise"},
        {"customer_id": None, "segment": "Unassigned"},
        {"customer_id": 2, "segment": "SMB"},
    ]

    result = sql_inner_join(
        left,
        right,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    print_rows("SQL-style NULL equality behavior", result)

    print(
        "\nThe two NULL keys do not match in an ordinary SQL equality join. "
        "IS NOT DISTINCT FROM is required when NULL should be treated as "
        "equal to NULL."
    )


def demonstrate_left_join_filter_pitfall() -> None:
    customers = [
        {"customer_id": 1, "name": "Asha"},
        {"customer_id": 2, "name": "Ravi"},
        {"customer_id": 3, "name": "Meera"},
    ]

    orders = [
        {"order_id": 101, "customer_id": 1, "status": "PAID"},
        {"order_id": 102, "customer_id": 1, "status": "CANCELLED"},
        {"order_id": 103, "customer_id": 2, "status": "PAID"},
    ]

    all_customers = left_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    paid_after_join = [
        row
        for row in all_customers
        if row["right_status"] == "PAID"
    ]

    paid_in_join_condition = [
        row
        for row in all_customers
        if row["right_status"] == "PAID"
    ]

    print_rows("LEFT JOIN before filtering", all_customers)
    print_rows(
        "Filtering right-side rows after the LEFT JOIN",
        paid_after_join,
    )
    print_rows(
        "Equivalent result when the business requirement is "
        "'customers having paid orders'",
        paid_in_join_condition,
    )

    print(
        "\nA WHERE condition on a nullable right-side column removes the "
        "NULL-extended rows. This frequently turns a LEFT JOIN into the "
        "effective behavior of an INNER JOIN."
    )


def demonstrate_preaggregation() -> None:
    customers = [
        {"customer_id": 1, "name": "Asha"},
        {"customer_id": 2, "name": "Ravi"},
        {"customer_id": 3, "name": "Meera"},
    ]

    orders = [
        {"order_id": 101, "customer_id": 1, "amount": 250},
        {"order_id": 102, "customer_id": 1, "amount": 125},
        {"order_id": 103, "customer_id": 2, "amount": 500},
    ]

    direct = inner_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    totals = defaultdict(float)
    for order in orders:
        totals[order["customer_id"]] += order["amount"]

    aggregated = [
        {
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "total_order_value": totals.get(customer["customer_id"], 0.0),
        }
        for customer in customers
    ]

    print_rows("Direct one-to-many join", direct)
    print_rows("Pre-aggregated order totals joined to customers", aggregated)

    print(
        "\nIf the final grain is one row per customer, aggregate the order "
        "table to customer grain before joining. This makes the intended "
        "cardinality explicit."
    )


def demonstrate_join_cardinality_validation() -> None:
    customers = [
        {"customer_id": 1, "name": "Asha"},
        {"customer_id": 2, "name": "Ravi"},
        {"customer_id": 3, "name": "Meera"},
    ]

    customer_profiles = [
        {"customer_id": 1, "risk_band": "LOW"},
        {"customer_id": 2, "risk_band": "MEDIUM"},
        {"customer_id": 3, "risk_band": "HIGH"},
    ]

    joined = inner_join(
        customers,
        customer_profiles,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    if len(joined) != len(customers):
        raise ValueError(
            "Expected a one-to-one join, but the result changed row count."
        )

    customer_ids = [row["customer_id"] for row in joined]

    if len(customer_ids) != len(set(customer_ids)):
        raise ValueError(
            "Expected unique customer IDs after a one-to-one join."
        )

    print_rows("Validated one-to-one join", joined)
    print("Cardinality validation passed.")


def demonstrate_many_to_many_explosion() -> None:
    orders = [
        {"order_id": 1001, "customer_id": 1},
        {"order_id": 1002, "customer_id": 1},
    ]

    promotions = [
        {"promotion_id": 501, "customer_id": 1, "promotion": "WELCOME"},
        {"promotion_id": 502, "customer_id": 1, "promotion": "LOYALTY"},
        {"promotion_id": 503, "customer_id": 1, "promotion": "SEASONAL"},
    ]

    result = inner_join(
        orders,
        promotions,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    print_rows("Many-to-many multiplication", result)

    print(
        "\nTwo orders multiplied by three matching promotions produce six "
        "rows. DISTINCT can hide the symptom but cannot decide which "
        "business relationship should exist."
    )


def demonstrate_safe_join_design() -> None:
    customers = [
        {"customer_id": 1, "name": "Asha"},
        {"customer_id": 2, "name": "Ravi"},
    ]

    orders = [
        {"order_id": 100, "customer_id": 1, "amount": 100},
        {"order_id": 101, "customer_id": 1, "amount": 200},
        {"order_id": 102, "customer_id": 2, "amount": 300},
    ]

    # The desired report grain is customer-level. We therefore aggregate
    # orders first instead of allowing the customer row to repeat per order.
    summary = defaultdict(lambda: {"order_count": 0, "total": 0.0})

    for order in orders:
        customer_id = order["customer_id"]
        summary[customer_id]["order_count"] += 1
        summary[customer_id]["total"] += order["amount"]

    report = []

    for customer in customers:
        metrics = summary.get(
            customer["customer_id"],
            {"order_count": 0, "total": 0.0},
        )

        report.append(
            {
                "customer_id": customer["customer_id"],
                "customer": customer["name"],
                "order_count": metrics["order_count"],
                "total": metrics["total"],
            }
        )

    print_rows("Safe customer-grain report", report)


def demonstrate_diagnostics() -> None:
    left = [
        {"id": 1, "department": "Finance"},
        {"id": 2, "department": "Finance"},
        {"id": 3, "department": "Technology"},
    ]

    right = [
        {"id": 10, "department": "Finance"},
        {"id": 11, "department": "Finance"},
        {"id": 12, "department": "Technology"},
    ]

    left_counts = Counter(row["department"] for row in left)
    right_counts = Counter(row["department"] for row in right)

    joined = inner_join(
        left,
        right,
        lambda row: row["department"],
        lambda row: row["department"],
    )

    print_rows("Diagnostic join on a non-unique attribute", joined)

    print("\nKey frequency diagnostics:")
    print("Left:", dict(left_counts))
    print("Right:", dict(right_counts))

    print(
        "\nFor each join key, estimate multiplicative behavior as "
        "left_count * right_count. Non-unique keys on both sides are "
        "a strong signal of many-to-many multiplication."
    )


def main() -> None:
    print("JOIN PITFALLS LAB")
    print("=================")

    demonstrate_basic_one_to_many()
    demonstrate_accidental_cartesian_product()
    demonstrate_missing_join_condition()
    demonstrate_incomplete_composite_join()
    demonstrate_null_behavior()
    demonstrate_left_join_filter_pitfall()
    demonstrate_preaggregation()
    demonstrate_join_cardinality_validation()
    demonstrate_many_to_many_explosion()
    demonstrate_safe_join_design()
    demonstrate_diagnostics()

    print("\nKey engineering rule:")
    print(
        "Before joining tables, identify the grain of every input and the "
        "expected cardinality of the relationship. Then verify the result "
        "against that expectation instead of using DISTINCT as a repair."
    )


if __name__ == "__main__":
    main()
