from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable


@dataclass(frozen=True)
class Order:
    order_id: int
    customer_id: int
    order_date: date
    status: str
    amount: float


@dataclass(frozen=True)
class Customer:
    customer_id: int
    name: str
    region: str


CUSTOMERS = [
    Customer(1, "Asha", "North"),
    Customer(2, "Ravi", "South"),
    Customer(3, "Meera", "West"),
    Customer(4, "Kabir", "East"),
]

ORDERS = [
    Order(101, 1, date(2026, 1, 5), "completed", 1200.00),
    Order(102, 1, date(2026, 1, 20), "completed", 800.00),
    Order(103, 1, date(2026, 2, 3), "cancelled", 500.00),
    Order(104, 2, date(2026, 1, 8), "completed", 1500.00),
    Order(105, 2, date(2026, 2, 12), "completed", 2200.00),
    Order(106, 3, date(2026, 1, 10), "completed", 700.00),
    Order(107, 3, date(2026, 2, 18), "completed", 900.00),
    Order(108, 4, date(2026, 1, 12), "completed", 3000.00),
]


def completed_orders(orders: Iterable[Order]) -> list[Order]:
    """Equivalent to a filtering CTE such as WITH completed AS (...)."""
    return [order for order in orders if order.status == "completed"]


def aggregate_customer_sales(
    orders: Iterable[Order],
) -> dict[int, float]:
    """Equivalent to an aggregation CTE."""
    totals: dict[int, float] = {}

    for order in orders:
        totals[order.customer_id] = totals.get(order.customer_id, 0.0) + order.amount

    return totals


def customer_sales_report(
    customers: Iterable[Customer],
    orders: Iterable[Order],
    minimum_sales: float = 2000.0,
) -> list[dict]:
    """
    Model a multi-CTE analytical query:

        WITH completed_orders AS (...),
             customer_totals AS (...),
             qualified_customers AS (...)
        SELECT ...

    Each intermediate result has a single responsibility.
    """
    completed = completed_orders(orders)
    totals = aggregate_customer_sales(completed)

    qualified = [
        customer
        for customer in customers
        if totals.get(customer.customer_id, 0.0) >= minimum_sales
    ]

    return [
        {
            "customer_id": customer.customer_id,
            "customer": customer.name,
            "region": customer.region,
            "completed_sales": round(totals.get(customer.customer_id, 0.0), 2),
        }
        for customer in qualified
    ]


def monthly_sales(orders: Iterable[Order]) -> dict[str, float]:
    """
    Model a CTE that creates a reusable derived relation containing
    monthly revenue before a later aggregation.
    """
    completed = completed_orders(orders)
    result: dict[str, float] = {}

    for order in completed:
        month_key = order.order_date.strftime("%Y-%m")
        result[month_key] = result.get(month_key, 0.0) + order.amount

    return dict(sorted(result.items()))


def recursive_date_series(start: date, end: date) -> list[date]:
    """
    PostgreSQL's recursive CTEs can generate sequences. This Python
    implementation mirrors the recursive idea without pretending that
    Python recursion is equivalent to SQL recursion.
    """
    if start > end:
        return []

    dates: list[date] = []
    current = start

    while current <= end:
        dates.append(current)
        current += timedelta(days=1)

    return dates


def hierarchy_with_cte_style(
    employees: list[dict],
    root_id: int,
) -> list[dict]:
    """
    Model a recursive CTE over an employee hierarchy.

    A recursive SQL CTE normally contains:
      anchor query: find the root
      recursive query: find children of already discovered rows

    The iterative frontier here makes the same dependency explicit.
    """
    by_manager: dict[int | None, list[dict]] = {}

    for employee in employees:
        by_manager.setdefault(employee["manager_id"], []).append(employee)

    discovered: list[dict] = []
    frontier = [employee for employee in employees if employee["id"] == root_id]

    while frontier:
        next_frontier: list[dict] = []

        for employee in frontier:
            discovered.append(employee)
            children = by_manager.get(employee["id"], [])
            next_frontier.extend(children)

        frontier = next_frontier

    return discovered


def demonstrate_edge_cases() -> None:
    print("\nEdge cases")

    empty_result = customer_sales_report(
        CUSTOMERS,
        [],
        minimum_sales=1.0,
    )
    print("Empty source:", empty_result)

    no_threshold_matches = customer_sales_report(
        CUSTOMERS,
        ORDERS,
        minimum_sales=10_000.0,
    )
    print("No qualifying customers:", no_threshold_matches)

    try:
        if not isinstance(10, (int, float)):
            raise TypeError("Threshold must be numeric.")
        if 10 < 0:
            raise ValueError("Threshold cannot be negative.")
    except (TypeError, ValueError) as exc:
        print("Validation error:", exc)


def main() -> None:
    print("Common Table Expression Concepts")
    print("=" * 36)

    print("\nCTE-style customer sales pipeline")
    for row in customer_sales_report(CUSTOMERS, ORDERS):
        print(row)

    print("\nCTE-style monthly aggregation")
    for month, amount in monthly_sales(ORDERS).items():
        print(f"{month}: {amount:,.2f}")

    print("\nRecursive CTE-style hierarchy traversal")
    employees = [
        {"id": 1, "name": "Director", "manager_id": None},
        {"id": 2, "name": "Engineering Lead", "manager_id": 1},
        {"id": 3, "name": "Data Lead", "manager_id": 1},
        {"id": 4, "name": "Backend Engineer", "manager_id": 2},
        {"id": 5, "name": "Data Engineer", "manager_id": 3},
    ]

    for employee in hierarchy_with_cte_style(employees, 1):
        print(employee)

    print("\nGenerated date series")
    for generated_date in recursive_date_series(
        date(2026, 3, 1),
        date(2026, 3, 5),
    ):
        print(generated_date)

    demonstrate_edge_cases()

    print("\nImportant SQL design principle")
    print(
        "A CTE should name a meaningful intermediate relation so that "
        "a complex query can be read as a sequence of relational transformations."
    )


if __name__ == "__main__":
    main()
