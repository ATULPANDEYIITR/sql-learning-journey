from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class FrameMode(Enum):
    ROWS = "ROWS"
    RANGE = "RANGE"
    GROUPS = "GROUPS"


@dataclass(frozen=True)
class Sale:
    sale_id: int
    employee: str
    department: str
    sale_date: str
    amount: float


def validate_sales(sales: Iterable[Sale]) -> list[Sale]:
    result = list(sales)
    if not result:
        raise ValueError("At least one sale is required")

    seen = set()
    for sale in result:
        if sale.sale_id in seen:
            raise ValueError(f"Duplicate sale_id: {sale.sale_id}")
        if sale.amount < 0:
            raise ValueError(f"Negative amount for sale {sale.sale_id}")
        if not sale.employee.strip():
            raise ValueError("Employee name cannot be empty")
        seen.add(sale.sale_id)

    return result


def rows_frame(values: list[float], start: int, end: int) -> list[float]:
    """ROWS uses physical row offsets."""
    result = []
    for i in range(len(values)):
        left = max(0, i + start)
        right = min(len(values) - 1, i + end)
        result.append(sum(values[left:right + 1]))
    return result


def range_frame(
    ordered: list[tuple[float, float]],
    preceding: float,
    following: float = 0,
) -> list[float]:
    """RANGE uses values in the ORDER BY domain, not physical positions."""
    result = []
    for current_value, _ in ordered:
        low = current_value - preceding
        high = current_value + following
        total = sum(
            amount
            for order_value, amount in ordered
            if low <= order_value <= high
        )
        result.append(total)
    return result


def groups_frame(
    ordered: list[tuple[float, float]],
    preceding_groups: int,
    following_groups: int = 0,
) -> list[float]:
    """GROUPS moves across peer groups sharing the same ORDER BY value."""
    peer_values = sorted({order_value for order_value, _ in ordered})
    result = []

    for current_value, _ in ordered:
        group_index = peer_values.index(current_value)
        first_group = max(0, group_index - preceding_groups)
        last_group = min(
            len(peer_values) - 1,
            group_index + following_groups,
        )
        selected = set(peer_values[first_group:last_group + 1])
        result.append(
            sum(amount for order_value, amount in ordered if order_value in selected)
        )

    return result


def sql_style_running_sum_rows(amounts: list[float]) -> list[float]:
    return rows_frame(amounts, -10**9, 0)


def demonstrate() -> None:
    sales = validate_sales(
        [
            Sale(1, "Asha", "Engineering", "2026-10-01", 100.0),
            Sale(2, "Asha", "Engineering", "2026-10-02", 200.0),
            Sale(3, "Asha", "Engineering", "2026-10-02", 300.0),
            Sale(4, "Asha", "Engineering", "2026-10-04", 400.0),
            Sale(5, "Asha", "Engineering", "2026-10-07", 500.0),
        ]
    )

    amounts = [sale.amount for sale in sales]

    print("Window Frames")
    print("=" * 70)

    print("\n1. ROWS BETWEEN 1 PRECEDING AND CURRENT ROW")
    rows_result = rows_frame(amounts, -1, 0)
    for sale, total in zip(sales, rows_result):
        print(f"{sale.sale_id}: {sale.amount:7.2f} -> {total:7.2f}")

    print("\n2. ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW")
    running = sql_style_running_sum_rows(amounts)
    for sale, total in zip(sales, running):
        print(f"{sale.sale_id}: {sale.amount:7.2f} -> {total:7.2f}")

    # ORDER BY amount creates a numeric ordering domain.
    ordered_amounts = [(sale.amount, sale.amount) for sale in sales]

    print("\n3. RANGE BETWEEN 200 PRECEDING AND CURRENT ROW")
    range_result = range_frame(ordered_amounts, 200)
    for sale, total in zip(sales, range_result):
        print(f"{sale.amount:7.2f} -> {total:7.2f}")

    # Duplicate ORDER BY values form one peer group for GROUPS.
    ordered_dates = [(float(sale.sale_date[-2:]), sale.amount) for sale in sales]

    print("\n4. GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW")
    groups_result = groups_frame(ordered_dates, 1)
    for sale, total in zip(sales, groups_result):
        print(f"{sale.sale_date}: {sale.amount:7.2f} -> {total:7.2f}")

    print("\nFrame semantics")
    print("ROWS   = physical rows")
    print("RANGE  = ORDER BY value interval")
    print("GROUPS = peer groups of equal ORDER BY values")

    print("\nEdge-case checks")
    assert rows_frame([10, 20, 30], -1, 0) == [10, 30, 50]
    assert range_frame([(10, 10), (10, 20), (20, 30)], 0) == [30, 30, 30]
    assert groups_frame([(1, 10), (1, 20), (2, 30)], 1) == [30, 30, 60]
    print("All assertions passed.")


if __name__ == "__main__":
    demonstrate()
