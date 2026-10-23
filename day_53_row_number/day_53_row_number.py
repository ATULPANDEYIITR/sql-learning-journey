from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Sale:
    sale_id: int
    customer_id: int
    product_id: str
    category: str
    amount: float


SALES: list[Sale] = [
    Sale(1, 101, "LAPTOP", "Electronics", 1200.00),
    Sale(2, 102, "PHONE", "Electronics", 800.00),
    Sale(3, 101, "LAPTOP", "Electronics", 1250.00),
    Sale(4, 103, "CHAIR", "Furniture", 300.00),
    Sale(5, 104, "PHONE", "Electronics", 950.00),
    Sale(6, 102, "MONITOR", "Electronics", 500.00),
    Sale(7, 105, "TABLE", "Furniture", 700.00),
    Sale(8, 103, "CHAIR", "Furniture", 320.00),
    Sale(9, 106, "PHONE", "Electronics", 1100.00),
    Sale(10, 107, "DESK", "Furniture", 900.00),
    Sale(11, 108, "PHONE", "Electronics", 780.00),
    Sale(12, 109, "TABLE", "Furniture", 650.00),
]


def validate_sales(rows: Iterable[Sale]) -> list[Sale]:
    """Reject malformed analytical input before ranking or deduplication."""
    validated = list(rows)

    if not validated:
        raise ValueError("At least one sale is required.")

    seen_ids: set[int] = set()

    for row in validated:
        if row.sale_id <= 0:
            raise ValueError(f"Invalid sale_id: {row.sale_id}")
        if row.sale_id in seen_ids:
            raise ValueError(f"Duplicate sale_id: {row.sale_id}")
        seen_ids.add(row.sale_id)

        if row.customer_id <= 0:
            raise ValueError(f"Invalid customer_id: {row.customer_id}")
        if not row.product_id.strip():
            raise ValueError("product_id cannot be empty.")
        if not row.category.strip():
            raise ValueError("category cannot be empty.")
        if row.amount < 0:
            raise ValueError(f"Negative amount for sale {row.sale_id}")

    return validated


def row_number_by_customer(rows: Sequence[Sale]) -> list[dict]:
    """
    ROW_NUMBER() gives every row a unique position inside its partition.
    Ties are deliberately broken by sale_id for deterministic output.
    """
    partitions: dict[int, list[Sale]] = defaultdict(list)

    for row in rows:
        partitions[row.customer_id].append(row)

    result = []

    for customer_id, customer_rows in partitions.items():
        ordered = sorted(
            customer_rows,
            key=lambda item: (-item.amount, item.sale_id),
        )

        for position, row in enumerate(ordered, start=1):
            result.append(
                {
                    "customer_id": customer_id,
                    "sale_id": row.sale_id,
                    "product_id": row.product_id,
                    "amount": row.amount,
                    "row_number": position,
                }
            )

    return sorted(result, key=lambda item: (item["customer_id"], item["row_number"]))


def deduplicate_latest_product(rows: Sequence[Sale]) -> list[Sale]:
    """
    Keep one deterministic row per (customer_id, product_id).
    The highest amount wins; sale_id resolves equal amounts.
    """
    best: dict[tuple[int, str], Sale] = {}

    for row in rows:
        key = (row.customer_id, row.product_id)
        current = best.get(key)

        if current is None or (row.amount, row.sale_id) > (
            current.amount,
            current.sale_id,
        ):
            best[key] = row

    return sorted(best.values(), key=lambda row: row.sale_id)


def top_n_per_category(rows: Sequence[Sale], n: int) -> list[dict]:
    """Solve the common 'top N within each group' problem."""
    if n <= 0:
        raise ValueError("n must be positive.")

    partitions: dict[str, list[Sale]] = defaultdict(list)

    for row in rows:
        partitions[row.category].append(row)

    result = []

    for category, category_rows in partitions.items():
        ordered = sorted(
            category_rows,
            key=lambda item: (-item.amount, item.sale_id),
        )

        for rank, row in enumerate(ordered[:n], start=1):
            result.append(
                {
                    "category": category,
                    "sale_id": row.sale_id,
                    "product_id": row.product_id,
                    "amount": row.amount,
                    "row_number": rank,
                }
            )

    return sorted(result, key=lambda item: (item["category"], item["row_number"]))


def dense_rank(values: Sequence[float]) -> list[int]:
    """
    Dense ranking differs from ROW_NUMBER:
    equal values receive the same rank and no rank is skipped.
    """
    ranks: dict[float, int] = {}
    current_rank = 0
    previous = object()

    for value in sorted(values, reverse=True):
        if value != previous:
            current_rank += 1
            ranks[value] = current_rank
            previous = value

    return [ranks[value] for value in values]


def global_top_n(rows: Sequence[Sale], n: int) -> list[Sale]:
    """Return exactly N rows, unlike a rank-based top-N which may include ties."""
    if n <= 0:
        raise ValueError("n must be positive.")

    return sorted(rows, key=lambda row: (-row.amount, row.sale_id))[:n]


def main() -> None:
    sales = validate_sales(SALES)

    print("ROW_NUMBER by customer")
    for item in row_number_by_customer(sales):
        print(item)

    print("\nDeduplicated customer/product rows")
    for row in deduplicate_latest_product(sales):
        print(row)

    print("\nTop 2 rows per category")
    for item in top_n_per_category(sales, 2):
        print(item)

    print("\nGlobal top 5 sales")
    for row in global_top_n(sales, 5):
        print(row)

    print("\nROW_NUMBER versus DENSE_RANK for repeated amounts")
    amounts = [1000.0, 900.0, 900.0, 800.0]
    print("Amounts:", amounts)
    print("ROW_NUMBER:", list(range(1, len(amounts) + 1)))
    print("DENSE_RANK:", dense_rank(amounts))

    print("\nComplexity")
    print(
        "Partitioned ranking uses sorting within groups: "
        "O(sum(k log k)), with O(n) partition storage."
    )
    print(
        "Deduplication uses a dictionary: expected O(n) time and O(n) space."
    )


if __name__ == "__main__":
    main()
