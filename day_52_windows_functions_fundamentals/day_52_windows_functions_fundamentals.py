from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class Sale:
    sale_id: int
    employee: str
    department: str
    sale_date: date
    amount: float


SALES = [
    Sale(1, "Asha", "Technology", date(2026, 1, 5), 12000.00),
    Sale(2, "Ravi", "Technology", date(2026, 1, 12), 18000.00),
    Sale(3, "Asha", "Technology", date(2026, 2, 3), 15000.00),
    Sale(4, "Ravi", "Technology", date(2026, 2, 17), 22000.00),
    Sale(5, "Neha", "Finance", date(2026, 1, 8), 9000.00),
    Sale(6, "Vikram", "Finance", date(2026, 1, 22), 14000.00),
    Sale(7, "Neha", "Finance", date(2026, 2, 6), 11000.00),
    Sale(8, "Vikram", "Finance", date(2026, 2, 20), 17000.00),
    Sale(9, "Meera", "Operations", date(2026, 1, 10), 7000.00),
    Sale(10, "Meera", "Operations", date(2026, 2, 14), 13000.00),
]


def validate_sales(rows: Iterable[Sale]) -> list[Sale]:
    result = list(rows)
    seen_ids: set[int] = set()

    for row in result:
        if row.sale_id <= 0:
            raise ValueError("sale_id must be positive")
        if row.sale_id in seen_ids:
            raise ValueError(f"duplicate sale_id: {row.sale_id}")
        seen_ids.add(row.sale_id)

        if not row.employee.strip() or not row.department.strip():
            raise ValueError("employee and department are required")
        if row.amount < 0:
            raise ValueError("sale amount cannot be negative")

    return sorted(result, key=lambda x: (x.department, x.sale_date, x.sale_id))


def row_number_by_partition(rows: list[Sale]) -> dict[int, int]:
    counters: dict[str, int] = {}
    result: dict[int, int] = {}

    for row in rows:
        counters[row.department] = counters.get(row.department, 0) + 1
        result[row.sale_id] = counters[row.department]

    return result


def rank_by_amount(rows: list[Sale]) -> dict[int, int]:
    result: dict[int, int] = {}

    for department in sorted({row.department for row in rows}):
        group = sorted(
            (row for row in rows if row.department == department),
            key=lambda row: (-row.amount, row.sale_id),
        )

        previous_amount = None
        rank = 0

        for position, row in enumerate(group, start=1):
            if row.amount != previous_amount:
                rank = position
                previous_amount = row.amount
            result[row.sale_id] = rank

    return result


def running_total(rows: list[Sale]) -> dict[int, float]:
    totals: dict[str, float] = {}
    result: dict[int, float] = {}

    for row in rows:
        totals[row.department] = totals.get(row.department, 0.0) + row.amount
        result[row.sale_id] = totals[row.department]

    return result


def moving_average(rows: list[Sale], window_size: int = 2) -> dict[int, float]:
    if window_size <= 0:
        raise ValueError("window_size must be positive")

    history: dict[str, list[float]] = {}
    result: dict[int, float] = {}

    for row in rows:
        values = history.setdefault(row.department, [])
        values.append(row.amount)

        recent = values[-window_size:]
        result[row.sale_id] = sum(recent) / len(recent)

    return result


def lag_amount(rows: list[Sale]) -> dict[int, float | None]:
    previous: dict[str, float] = {}
    result: dict[int, float | None] = {}

    for row in rows:
        result[row.sale_id] = previous.get(row.department)
        previous[row.department] = row.amount

    return result


def lead_amount(rows: list[Sale]) -> dict[int, float | None]:
    result: dict[int, float | None] = {}

    for department in sorted({row.department for row in rows}):
        group = [row for row in rows if row.department == department]

        for index, row in enumerate(group):
            result[row.sale_id] = (
                group[index + 1].amount if index + 1 < len(group) else None
            )

    return result


def print_report(rows: list[Sale]) -> None:
    row_numbers = row_number_by_partition(rows)
    ranks = rank_by_amount(rows)
    totals = running_total(rows)
    averages = moving_average(rows)
    lags = lag_amount(rows)
    leads = lead_amount(rows)

    header = (
        f"{'ID':>3} {'Department':<12} {'Employee':<10} "
        f"{'Amount':>10} {'ROW#':>5} {'RANK':>5} "
        f"{'Running':>12} {'Avg2':>10} {'LAG':>10} {'LEAD':>10}"
    )
    print(header)
    print("-" * len(header))

    for row in rows:
        lag = "-" if lags[row.sale_id] is None else f"{lags[row.sale_id]:.2f}"
        lead = "-" if leads[row.sale_id] is None else f"{leads[row.sale_id]:.2f}"

        print(
            f"{row.sale_id:>3} {row.department:<12} {row.employee:<10} "
            f"{row.amount:>10.2f} {row_numbers[row.sale_id]:>5} "
            f"{ranks[row.sale_id]:>5} {totals[row.sale_id]:>12.2f} "
            f"{averages[row.sale_id]:>10.2f} {lag:>10} {lead:>10}"
        )


def demonstrate_window_concepts(rows: list[Sale]) -> None:
    print("\nWindow-function concepts represented by the Python model:")
    print("1. Partition: rows are independently processed within each department.")
    print("2. Order: calculations follow sale_date and sale_id.")
    print("3. ROW_NUMBER: assigns a unique position inside each partition.")
    print("4. RANK: assigns equal ranks to equal values and leaves rank gaps.")
    print("5. Running total: aggregates rows while retaining every source row.")
    print("6. Moving average: calculates a bounded frame over recent rows.")
    print("7. LAG/LEAD: accesses neighboring rows without collapsing the result set.")


def main() -> None:
    try:
        rows = validate_sales(SALES)
        print("Window Function Introduction")
        print("============================")
        print_report(rows)
        demonstrate_window_concepts(rows)
    except (ValueError, TypeError) as exc:
        print(f"Data validation failure: {exc}")


if __name__ == "__main__":
    main()
