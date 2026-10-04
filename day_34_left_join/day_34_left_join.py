#!/usr/bin/env python3
"""
LEFT JOIN | Left outer joins, unmatched rows, NULL results

A self-contained learning implementation of SQL LEFT JOIN concepts using
Python's standard library. The examples model customers, orders, products,
departments, and employees without requiring an external database.

The script demonstrates:
- Left outer join semantics
- Matching rows and unmatched left-side rows
- NULL-like results using Python's None
- Composite join keys
- One-to-many relationships
- Duplicate matches and row multiplication
- LEFT JOIN with additional conditions
- The difference between ON-style and WHERE-style filtering
- Aggregation after a LEFT JOIN
- Anti-join patterns for finding unmatched records
- Multi-table LEFT JOINs
- A small SQL-like relational engine
- Validation, edge cases, and complexity considerations
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional


NULL = None


def print_title(title: str) -> None:
    print("\n" + "=" * 82)
    print(title)
    print("=" * 82)


def print_rows(rows: Iterable[dict[str, Any]], columns: Optional[list[str]] = None) -> None:
    rows = list(rows)

    if not rows:
        print("(no rows)")
        return

    if columns is None:
        columns = list(dict.fromkeys(key for row in rows for key in row))

    widths = {
        column: max(
            len(column),
            *(len("NULL" if row.get(column) is None else str(row.get(column))) for row in rows),
        )
        for column in columns
    }

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)

    print(header)
    print(separator)

    for row in rows:
        values = [
            "NULL" if row.get(column) is None else str(row.get(column))
            for column in columns
        ]
        print(" | ".join(value.ljust(widths[column]) for column, value in zip(columns, values)))


def normalize_key(value: Any) -> Any:
    """
    Normalize values used by the in-memory join engine.

    None represents SQL NULL. It deliberately remains distinct from ordinary
    values because NULL does not equal another NULL in SQL join predicates.
    """
    return value


def sql_equals(left: Any, right: Any) -> bool:
    """
    Approximate SQL equality for join predicates.

    SQL NULL does not compare equal to NULL, so a join predicate involving
    None returns False.
    """
    if left is None or right is None:
        return False
    return left == right


def left_join(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    left_key: Callable[[dict[str, Any]], Any],
    right_key: Callable[[dict[str, Any]], Any],
    right_prefix: str = "right_",
    on_extra_condition: Optional[
        Callable[[dict[str, Any], dict[str, Any]], bool]
    ] = None,
) -> list[dict[str, Any]]:
    """
    Perform an in-memory LEFT JOIN.

    Every row from left_rows is preserved. Matching right rows are attached.
    If no right row qualifies, the result contains one row whose right-side
    fields are None.

    A hash index is used for the equality portion of the join, giving roughly
    O(L + R + M) behavior for L left rows, R right rows, and M output matches,
    rather than scanning the entire right table for every left row.
    """
    right_columns = list(dict.fromkeys(column for row in right_rows for column in row))

    index: dict[Any, list[dict[str, Any]]] = defaultdict(list)

    for right_row in right_rows:
        key = normalize_key(right_key(right_row))
        if key is not None:
            index[key].append(right_row)

    results: list[dict[str, Any]] = []

    for left_row in left_rows:
        key = normalize_key(left_key(left_row))
        candidates = index.get(key, []) if key is not None else []

        qualifying = []

        for right_row in candidates:
            if on_extra_condition is None or on_extra_condition(left_row, right_row):
                qualifying.append(right_row)

        if not qualifying:
            result = dict(left_row)

            for column in right_columns:
                output_name = column
                if output_name in result:
                    output_name = f"{right_prefix}{column}"

                result[output_name] = None

            results.append(result)
            continue

        for right_row in qualifying:
            result = dict(left_row)

            for column, value in right_row.items():
                output_name = column
                if output_name in result:
                    output_name = f"{right_prefix}{column}"

                result[output_name] = value

            results.append(result)

    return results


def inner_join(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    left_key: Callable[[dict[str, Any]], Any],
    right_key: Callable[[dict[str, Any]], Any],
) -> list[dict[str, Any]]:
    """Small comparison implementation showing what INNER JOIN would discard."""
    right_columns = list(dict.fromkeys(column for row in right_rows for column in row))
    index: dict[Any, list[dict[str, Any]]] = defaultdict(list)

    for row in right_rows:
        key = right_key(row)
        if key is not None:
            index[key].append(row)

    results = []

    for left_row in left_rows:
        key = left_key(left_row)
        if key is None:
            continue

        for right_row in index.get(key, []):
            result = dict(left_row)

            for column, value in right_row.items():
                output_name = column if column not in result else f"right_{column}"
                result[output_name] = value

            results.append(result)

    return results


def where(
    rows: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    """
    Apply a post-join WHERE-style filter.

    This is intentionally separate from the join's ON-style condition because
    moving a right-side condition from ON to WHERE can change a LEFT JOIN into
    behavior similar to an INNER JOIN.
    """
    return [row for row in rows if predicate(row)]


def sql_is_null(value: Any) -> bool:
    return value is None


def sql_is_not_null(value: Any) -> bool:
    return value is not None


def aggregate_count(
    rows: list[dict[str, Any]],
    group_key: Callable[[dict[str, Any]], Any],
    value_key: Optional[Callable[[dict[str, Any]], Any]] = None,
) -> list[dict[str, Any]]:
    """
    Demonstrate COUNT behavior after a LEFT JOIN.

    COUNT(*) counts the generated NULL-extended row.
    COUNT(value) ignores rows where value is None.
    """
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        groups[group_key(row)].append(row)

    output = []

    for key, group_rows in groups.items():
        count_star = len(group_rows)

        if value_key is None:
            count_value = count_star
        else:
            count_value = sum(value_key(row) is not None for row in group_rows)

        output.append(
            {
                "group": key,
                "count_star": count_star,
                "count_value": count_value,
            }
        )

    return output


def demo_basic_left_join() -> None:
    print_title("Basic LEFT JOIN: preserve every left-side row")

    customers = [
        {"customer_id": 1, "customer_name": "Aarav"},
        {"customer_id": 2, "customer_name": "Meera"},
        {"customer_id": 3, "customer_name": "Kabir"},
        {"customer_id": 4, "customer_name": "Diya"},
    ]

    orders = [
        {"order_id": 101, "customer_id": 1, "amount": 2500},
        {"order_id": 102, "customer_id": 1, "amount": 1800},
        {"order_id": 103, "customer_id": 3, "amount": 4200},
    ]

    joined = left_join(
        customers,
        orders,
        left_key=lambda row: row["customer_id"],
        right_key=lambda row: row["customer_id"],
    )

    print_rows(
        joined,
        ["customer_id", "customer_name", "order_id", "right_customer_id", "amount"],
    )

    print(
        "\nAarav produces two rows because two orders match. "
        "Meera and Diya remain present with NULL order fields."
    )


def demo_inner_vs_left() -> None:
    print_title("INNER JOIN versus LEFT JOIN")

    customers = [
        {"customer_id": 1, "customer_name": "Aarav"},
        {"customer_id": 2, "customer_name": "Meera"},
        {"customer_id": 3, "customer_name": "Kabir"},
    ]

    orders = [
        {"order_id": 501, "customer_id": 1},
        {"order_id": 502, "customer_id": 3},
    ]

    inner = inner_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    outer = left_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    print("INNER JOIN result:")
    print_rows(inner, ["customer_id", "customer_name", "order_id"])

    print("\nLEFT JOIN result:")
    print_rows(
        outer,
        ["customer_id", "customer_name", "order_id", "right_customer_id"],
    )


def demo_unmatched_rows_and_null() -> None:
    print_title("Unmatched rows and NULL results")

    departments = [
        {"department_id": 10, "department_name": "Engineering"},
        {"department_id": 20, "department_name": "Finance"},
        {"department_id": 30, "department_name": "Research"},
    ]

    employees = [
        {"employee_id": 1, "employee_name": "Ravi", "department_id": 10},
        {"employee_id": 2, "employee_name": "Nisha", "department_id": 10},
        {"employee_id": 3, "employee_name": "Omar", "department_id": 99},
    ]

    joined = left_join(
        departments,
        employees,
        lambda row: row["department_id"],
        lambda row: row["department_id"],
    )

    print_rows(
        joined,
        [
            "department_id",
            "department_name",
            "employee_id",
            "right_department_id",
            "employee_name",
        ],
    )

    print(
        "\nFinance and Research have no matching employee, so their employee "
        "columns are NULL-like None values."
    )


def demo_one_to_many() -> None:
    print_title("One-to-many LEFT JOIN and row multiplication")

    projects = [
        {"project_id": "P100", "project_name": "Payments"},
        {"project_id": "P200", "project_name": "Analytics"},
        {"project_id": "P300", "project_name": "Security"},
    ]

    contributors = [
        {"project_id": "P100", "person": "Anika"},
        {"project_id": "P100", "person": "Vikram"},
        {"project_id": "P100", "person": "Zoya"},
        {"project_id": "P300", "person": "Ishaan"},
    ]

    joined = left_join(
        projects,
        contributors,
        lambda row: row["project_id"],
        lambda row: row["project_id"],
    )

    print_rows(joined, ["project_id", "project_name", "right_project_id", "person"])

    print(
        "\nAnalytics remains present even without a contributor. "
        "Payments appears three times because three right-side rows match."
    )


def demo_composite_key() -> None:
    print_title("Composite-key LEFT JOIN")

    subscriptions = [
        {"account_id": 1, "region": "IN", "plan": "PRO"},
        {"account_id": 1, "region": "US", "plan": "PRO"},
        {"account_id": 2, "region": "IN", "plan": "BASIC"},
    ]

    invoices = [
        {"account_id": 1, "region": "IN", "invoice_id": "INV-1"},
        {"account_id": 2, "region": "IN", "invoice_id": "INV-2"},
    ]

    joined = left_join(
        subscriptions,
        invoices,
        left_key=lambda row: (row["account_id"], row["region"]),
        right_key=lambda row: (row["account_id"], row["region"]),
    )

    print_rows(
        joined,
        ["account_id", "region", "plan", "invoice_id", "right_account_id", "right_region"],
    )

    print(
        "\nThe US subscription does not match the IN invoice because both "
        "account_id and region participate in the equality predicate."
    )


def demo_on_condition_vs_where_condition() -> None:
    print_title("ON condition versus WHERE condition")

    customers = [
        {"customer_id": 1, "name": "Aarav"},
        {"customer_id": 2, "name": "Meera"},
        {"customer_id": 3, "name": "Kabir"},
    ]

    orders = [
        {"order_id": 1, "customer_id": 1, "status": "PAID", "amount": 900},
        {"order_id": 2, "customer_id": 1, "status": "CANCELLED", "amount": 300},
        {"order_id": 3, "customer_id": 2, "status": "PAID", "amount": 1200},
    ]

    paid_in_on = left_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
        on_extra_condition=lambda customer, order: order["status"] == "PAID",
    )

    print("Condition applied during the join, equivalent to putting it in ON:")
    print_rows(
        paid_in_on,
        ["customer_id", "name", "order_id", "right_customer_id", "status", "amount"],
    )

    joined_first = left_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    paid_in_where = where(
        joined_first,
        lambda row: row["status"] == "PAID",
    )

    print("\nCondition applied after the join, equivalent to WHERE:")
    print_rows(
        paid_in_where,
        ["customer_id", "name", "order_id", "right_customer_id", "status", "amount"],
    )

    print(
        "\nThe ON-style version preserves customers with no qualifying PAID order. "
        "The WHERE-style version removes NULL status rows."
    )


def demo_find_unmatched() -> None:
    print_title("Anti-join: find left-side rows without a match")

    customers = [
        {"customer_id": 1, "name": "Aarav"},
        {"customer_id": 2, "name": "Meera"},
        {"customer_id": 3, "name": "Kabir"},
        {"customer_id": 4, "name": "Diya"},
    ]

    orders = [
        {"order_id": 1001, "customer_id": 1},
        {"order_id": 1002, "customer_id": 3},
    ]

    joined = left_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    unmatched = where(joined, lambda row: row["order_id"] is None)

    print_rows(unmatched, ["customer_id", "name", "order_id"])

    print(
        "\nThis models the common SQL pattern LEFT JOIN ... WHERE right_table.key IS NULL."
    )


def demo_count_difference() -> None:
    print_title("COUNT(*) versus COUNT(right_column) after LEFT JOIN")

    teams = [
        {"team_id": "A", "team_name": "Platform"},
        {"team_id": "B", "team_name": "Data"},
        {"team_id": "C", "team_name": "Security"},
    ]

    incidents = [
        {"incident_id": 1, "team_id": "A"},
        {"incident_id": 2, "team_id": "A"},
    ]

    joined = left_join(
        teams,
        incidents,
        lambda row: row["team_id"],
        lambda row: row["team_id"],
    )

    counts = aggregate_count(
        joined,
        group_key=lambda row: row["team_id"],
        value_key=lambda row: row["incident_id"],
    )

    print_rows(counts, ["group", "count_star", "count_value"])

    print(
        "\nThe NULL-extended row for Security contributes to COUNT(*), "
        "but not to COUNT(incident_id)."
    )


def demo_multi_table_left_join() -> None:
    print_title("Chaining multiple LEFT JOINs")

    customers = [
        {"customer_id": 1, "customer_name": "Aarav"},
        {"customer_id": 2, "customer_name": "Meera"},
        {"customer_id": 3, "customer_name": "Kabir"},
    ]

    orders = [
        {"order_id": 101, "customer_id": 1, "product_id": "P1"},
        {"order_id": 102, "customer_id": 2, "product_id": "P2"},
    ]

    products = [
        {"product_id": "P1", "product_name": "Laptop"},
        {"product_id": "P3", "product_name": "Monitor"},
    ]

    customer_orders = left_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    customer_orders_products = left_join(
        customer_orders,
        products,
        lambda row: row["right_product_id"] if row.get("right_product_id") else None,
        lambda row: row["product_id"],
        right_prefix="product_",
    )

    print_rows(
        customer_orders_products,
        [
            "customer_id",
            "customer_name",
            "order_id",
            "right_product_id",
            "product_id",
            "product_name",
        ],
    )

    print(
        "\nLEFT JOIN chaining preserves customers even when an order or its "
        "referenced product is missing."
    )


def demo_null_join_key() -> None:
    print_title("NULL join keys")

    left_rows = [
        {"id": 1, "code": "A"},
        {"id": 2, "code": None},
    ]

    right_rows = [
        {"record_id": 10, "code": "A"},
        {"record_id": 11, "code": None},
    ]

    joined = left_join(
        left_rows,
        right_rows,
        lambda row: row["code"],
        lambda row: row["code"],
    )

    print_rows(joined, ["id", "code", "record_id", "right_code"])

    print(
        "\nThe two NULL codes do not match. This follows SQL equality semantics: "
        "NULL = NULL is not TRUE."
    )


def validate_join_inputs(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
) -> None:
    if not isinstance(left_rows, list) or not isinstance(right_rows, list):
        raise TypeError("Join inputs must be lists of dictionaries.")

    for table_name, rows in (("left", left_rows), ("right", right_rows)):
        for row in rows:
            if not isinstance(row, dict):
                raise TypeError(f"Every {table_name} row must be a dictionary.")


def demo_validation_and_edge_cases() -> None:
    print_title("Validation and edge cases")

    validate_join_inputs(
        [{"id": 1}],
        [{"id": 10}],
    )

    try:
        validate_join_inputs(
            [{"id": 1}],
            [{"id": 10}, "not a dictionary"],  # type: ignore[list-item]
        )
    except TypeError as exc:
        print(f"Validation correctly rejected invalid input: {exc}")

    empty_left = left_join(
        [],
        [{"id": 1}],
        lambda row: row["id"],
        lambda row: row["id"],
    )

    empty_right = left_join(
        [{"id": 1}, {"id": 2}],
        [],
        lambda row: row["id"],
        lambda row: row["id"],
    )

    print(f"Empty left table produces {len(empty_left)} rows.")
    print("Empty right table preserves every left row:")
    print_rows(empty_right, ["id"])


def demo_realistic_customer_report() -> None:
    print_title("Realistic case: customer order health report")

    customers = [
        {"customer_id": 100, "name": "Aarav", "segment": "Enterprise"},
        {"customer_id": 101, "name": "Meera", "segment": "SMB"},
        {"customer_id": 102, "name": "Kabir", "segment": "Enterprise"},
        {"customer_id": 103, "name": "Diya", "segment": "Startup"},
    ]

    orders = [
        {"order_id": 9001, "customer_id": 100, "status": "PAID", "amount": 25000},
        {"order_id": 9002, "customer_id": 100, "status": "PAID", "amount": 12000},
        {"order_id": 9003, "customer_id": 101, "status": "PENDING", "amount": 4500},
    ]

    report = left_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
    )

    print_rows(
        report,
        [
            "customer_id",
            "name",
            "segment",
            "order_id",
            "right_customer_id",
            "status",
            "amount",
        ],
    )

    print("\nCustomers with no order:")
    no_order = where(report, lambda row: row["order_id"] is None)
    print_rows(no_order, ["customer_id", "name", "segment"])

    print("\nCustomers with a PAID order, while preserving customers without one:")
    paid_or_none = left_join(
        customers,
        orders,
        lambda row: row["customer_id"],
        lambda row: row["customer_id"],
        on_extra_condition=lambda customer, order: order["status"] == "PAID",
    )
    print_rows(
        paid_or_none,
        ["customer_id", "name", "order_id", "status", "amount"],
    )


def demonstrate_complexity() -> None:
    print_title("Performance model")

    left_size = 100_000
    right_size = 500_000

    print(f"Illustrative left rows:  {left_size:,}")
    print(f"Illustrative right rows: {right_size:,}")
    print(
        "A hash-based equality LEFT JOIN builds an index for the right side, "
        "then probes it for each left row."
    )
    print(
        "Typical conceptual cost: O(L + R + M), where M is the number of "
        "matching output rows."
    )
    print(
        "A naive nested-loop implementation can approach O(L × R), which "
        "becomes expensive for large relations."
    )
    print(
        "Real database optimizers may choose hash joins, merge joins, or "
        "nested-loop joins based on indexes, cardinality estimates, sorting, "
        "memory, and predicate selectivity."
    )


def main() -> None:
    print_title("LEFT JOIN | Complete Python Demonstration")

    demo_basic_left_join()
    demo_inner_vs_left()
    demo_unmatched_rows_and_null()
    demo_one_to_many()
    demo_composite_key()
    demo_on_condition_vs_where_condition()
    demo_find_unmatched()
    demo_count_difference()
    demo_multi_table_left_join()
    demo_null_join_key()
    demo_validation_and_edge_cases()
    demo_realistic_customer_report()
    demonstrate_complexity()

    print_title("Execution complete")
    print(
        "The demonstrations model the central LEFT JOIN rule: every row from "
        "the left relation survives, while missing right-side attributes are "
        "represented by NULL-like values."
    )


if __name__ == "__main__":
    main()
