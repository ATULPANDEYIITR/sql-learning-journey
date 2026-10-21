from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


CENT = Decimal("0.01")


def money(value: Decimal | int | float | str) -> Decimal:
    """Normalize monetary values to two decimal places."""
    amount = Decimal(str(value))
    if amount < Decimal("0"):
        raise ValueError("Amount cannot be negative.")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Order:
    order_id: int
    customer_id: int
    region: str
    status: str
    channel: str
    order_date: date
    amount: Decimal
    returned: bool = False

    def __post_init__(self) -> None:
        if self.order_id <= 0 or self.customer_id <= 0:
            raise ValueError("IDs must be positive.")
        if not self.region.strip():
            raise ValueError("Region is required.")
        if self.status not in {"completed", "cancelled", "pending"}:
            raise ValueError(f"Unsupported status: {self.status}")
        if self.channel not in {"web", "mobile", "store"}:
            raise ValueError(f"Unsupported channel: {self.channel}")
        if self.amount < Decimal("0"):
            raise ValueError("Order amount cannot be negative.")


def conditional_sum(
    orders: Iterable[Order],
    predicate,
) -> Decimal:
    """Equivalent to SUM(CASE WHEN predicate THEN amount ELSE 0 END)."""
    total = Decimal("0")
    for order in orders:
        if predicate(order):
            total += order.amount
    return total.quantize(CENT)


def conditional_count(
    orders: Iterable[Order],
    predicate,
) -> int:
    """Equivalent to COUNT(CASE WHEN predicate THEN 1 END)."""
    return sum(1 for order in orders if predicate(order))


def filtered_count(
    orders: Iterable[Order],
    predicate,
) -> int:
    """Models a filtered aggregate such as COUNT(*) FILTER (WHERE ...)."""
    return sum(1 for order in orders if predicate(order))


def average_if(
    orders: Iterable[Order],
    predicate,
) -> Decimal:
    """Calculate an average only over rows satisfying the condition."""
    matching = [order.amount for order in orders if predicate(order)]
    if not matching:
        return Decimal("0.00")
    return (sum(matching) / Decimal(len(matching))).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def calculate_kpis(orders: list[Order]) -> dict[str, object]:
    """Calculate business KPIs using conditional aggregation semantics."""
    completed = lambda o: o.status == "completed"
    cancelled = lambda o: o.status == "cancelled"
    web_completed = lambda o: o.status == "completed" and o.channel == "web"
    mobile_completed = lambda o: o.status == "completed" and o.channel == "mobile"
    returned_completed = lambda o: o.status == "completed" and o.returned

    completed_revenue = conditional_sum(orders, completed)
    cancelled_value = conditional_sum(orders, cancelled)
    web_revenue = conditional_sum(orders, web_completed)
    mobile_revenue = conditional_sum(orders, mobile_completed)

    completed_count = conditional_count(orders, completed)
    cancelled_count = filtered_count(orders, cancelled)
    returned_count = conditional_count(orders, returned_completed)

    total_value = sum((o.amount for o in orders), Decimal("0"))
    total_value = total_value.quantize(CENT)

    cancellation_rate = (
        Decimal(cancelled_count) / Decimal(len(orders)) * Decimal("100")
        if orders
        else Decimal("0")
    ).quantize(CENT)

    completion_rate = (
        Decimal(completed_count) / Decimal(len(orders)) * Decimal("100")
        if orders
        else Decimal("0")
    ).quantize(CENT)

    average_completed_order = average_if(orders, completed)

    return {
        "total_orders": len(orders),
        "completed_orders": completed_count,
        "cancelled_orders": cancelled_count,
        "returned_completed_orders": returned_count,
        "total_order_value": total_value,
        "completed_revenue": completed_revenue,
        "cancelled_value": cancelled_value,
        "web_revenue": web_revenue,
        "mobile_revenue": mobile_revenue,
        "average_completed_order": average_completed_order,
        "completion_rate_percent": completion_rate,
        "cancellation_rate_percent": cancellation_rate,
    }


def regional_kpis(orders: list[Order]) -> dict[str, dict[str, object]]:
    """Group records first, then apply conditional metrics inside each group."""
    regions = sorted({order.region for order in orders})
    result: dict[str, dict[str, object]] = {}

    for region in regions:
        region_orders = [o for o in orders if o.region == region]
        completed = [o for o in region_orders if o.status == "completed"]

        result[region] = {
            "orders": len(region_orders),
            "completed": len(completed),
            "revenue": conditional_sum(
                region_orders, lambda o: o.status == "completed"
            ),
            "cancelled": conditional_count(
                region_orders, lambda o: o.status == "cancelled"
            ),
            "returned_completed": conditional_count(
                region_orders,
                lambda o: o.status == "completed" and o.returned,
            ),
            "web_revenue": conditional_sum(
                region_orders,
                lambda o: o.status == "completed" and o.channel == "web",
            ),
            "completion_rate": (
                Decimal(len(completed)) / Decimal(len(region_orders)) * 100
                if region_orders
                else Decimal("0")
            ).quantize(CENT),
        }

    return result


def print_kpis(title: str, metrics: dict[str, object]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for key, value in metrics.items():
        print(f"{key:30}: {value}")


def main() -> None:
    orders = [
        Order(1, 101, "North", "completed", "web", date(2026, 10, 1), money("1250")),
        Order(2, 102, "North", "cancelled", "mobile", date(2026, 10, 1), money("800")),
        Order(3, 103, "South", "completed", "mobile", date(2026, 10, 2), money("2100")),
        Order(4, 104, "South", "completed", "web", date(2026, 10, 3), money("1750"), True),
        Order(5, 105, "East", "pending", "web", date(2026, 10, 4), money("900")),
        Order(6, 106, "East", "completed", "store", date(2026, 10, 5), money("3200")),
        Order(7, 107, "West", "cancelled", "web", date(2026, 10, 5), money("600")),
        Order(8, 108, "West", "completed", "mobile", date(2026, 10, 6), money("1450")),
        Order(9, 109, "North", "completed", "web", date(2026, 10, 7), money("2800")),
        Order(10, 110, "South", "pending", "mobile", date(2026, 10, 8), money("1100")),
    ]

    overall = calculate_kpis(orders)
    print_kpis("Overall KPI Metrics", overall)

    print("\nRegional Conditional Metrics")
    print("----------------------------")
    for region, metrics in regional_kpis(orders).items():
        print(
            f"{region:8} "
            f"orders={metrics['orders']:2} "
            f"completed={metrics['completed']:2} "
            f"revenue={metrics['revenue']:8} "
            f"cancelled={metrics['cancelled']:2} "
            f"returned={metrics['returned_completed']:2} "
            f"web_revenue={metrics['web_revenue']:8} "
            f"completion_rate={metrics['completion_rate']}%"
        )

    # A zero-matching condition must produce zero rather than divide by zero.
    no_refunds = conditional_sum(
        orders,
        lambda o: o.status == "completed" and o.amount > Decimal("100000"),
    )
    print(f"\nHigh-value conditional sum with no matches: {no_refunds}")

    # Validate a KPI invariant useful when debugging aggregation logic.
    status_count = (
        conditional_count(orders, lambda o: o.status == "completed")
        + conditional_count(orders, lambda o: o.status == "cancelled")
        + conditional_count(orders, lambda o: o.status == "pending")
    )
    assert status_count == len(orders), "Status aggregation lost a row."

    print("\nAggregation validation: passed")


if __name__ == "__main__":
    main()
