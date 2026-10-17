from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import mean, median
from typing import Iterable


@dataclass(frozen=True)
class Transaction:
    transaction_id: int
    customer_id: int
    region: str
    category: str
    amount: float
    status: str
    created_at: datetime


@dataclass
class CustomerAggregate:
    customer_id: int
    transaction_count: int = 0
    total_amount: float = 0.0
    successful_amount: float = 0.0
    failed_amount: float = 0.0
    successful_count: int = 0
    failed_count: int = 0

    @property
    def average_transaction(self) -> float:
        return (
            self.total_amount / self.transaction_count
            if self.transaction_count
            else 0.0
        )

    @property
    def success_rate(self) -> float:
        return (
            self.successful_count / self.transaction_count * 100
            if self.transaction_count
            else 0.0
        )


def sample_transactions() -> list[Transaction]:
    base = datetime(2026, 10, 1, 9, 0, 0)

    rows = [
        (1001, 101, "North", "Cloud", 1250.00, "completed", 0),
        (1002, 101, "North", "Security", 2400.00, "completed", 1),
        (1003, 101, "North", "Cloud", 800.00, "failed", 2),
        (1004, 102, "South", "Cloud", 1800.00, "completed", 3),
        (1005, 102, "South", "Analytics", 3200.00, "completed", 4),
        (1006, 102, "South", "Security", 700.00, "refunded", 5),
        (1007, 103, "East", "Analytics", 4100.00, "completed", 6),
        (1008, 103, "East", "Cloud", 900.00, "completed", 7),
        (1009, 103, "East", "Security", 1300.00, "failed", 8),
        (1010, 104, "West", "Cloud", 5200.00, "completed", 9),
        (1011, 104, "West", "Analytics", 2700.00, "completed", 10),
        (1012, 104, "West", "Security", 1100.00, "completed", 11),
        (1013, 105, "North", "Analytics", 1500.00, "failed", 12),
        (1014, 105, "North", "Cloud", 2300.00, "completed", 13),
        (1015, 105, "North", "Security", 900.00, "completed", 14),
        (1016, 101, "North", "Analytics", 6000.00, "completed", 15),
        (1017, 102, "South", "Cloud", 450.00, "failed", 16),
        (1018, 103, "East", "Analytics", 2100.00, "refunded", 17),
        (1019, 104, "West", "Cloud", 3600.00, "completed", 18),
        (1020, 105, "North", "Security", 2800.00, "completed", 19),
    ]

    return [
        Transaction(
            transaction_id=transaction_id,
            customer_id=customer_id,
            region=region,
            category=category,
            amount=amount,
            status=status,
            created_at=base + timedelta(days=offset),
        )
        for (
            transaction_id,
            customer_id,
            region,
            category,
            amount,
            status,
            offset,
        ) in rows
    ]


def validate_transactions(transactions: Iterable[Transaction]) -> list[Transaction]:
    valid_statuses = {"completed", "failed", "refunded"}
    valid_categories = {"Cloud", "Security", "Analytics"}
    validated: list[Transaction] = []
    seen_ids: set[int] = set()

    for transaction in transactions:
        if transaction.transaction_id in seen_ids:
            raise ValueError(
                f"Duplicate transaction ID: {transaction.transaction_id}"
            )

        if transaction.amount < 0:
            raise ValueError(
                f"Negative amount for transaction {transaction.transaction_id}"
            )

        if transaction.status not in valid_statuses:
            raise ValueError(
                f"Unknown status {transaction.status!r} for "
                f"transaction {transaction.transaction_id}"
            )

        if transaction.category not in valid_categories:
            raise ValueError(
                f"Unknown category {transaction.category!r} for "
                f"transaction {transaction.transaction_id}"
            )

        seen_ids.add(transaction.transaction_id)
        validated.append(transaction)

    return validated


def aggregate_by_region(
    transactions: Iterable[Transaction],
) -> dict[str, dict[str, float]]:
    """
    Multiple aggregation calculates count, total, average, minimum, and
    maximum in one grouped pass. This is analogous to SQL GROUP BY with
    several aggregate expressions.
    """
    result: dict[str, dict[str, float]] = {}

    for transaction in transactions:
        group = result.setdefault(
            transaction.region,
            {
                "count": 0,
                "total": 0.0,
                "minimum": float("inf"),
                "maximum": float("-inf"),
            },
        )

        group["count"] += 1
        group["total"] += transaction.amount
        group["minimum"] = min(group["minimum"], transaction.amount)
        group["maximum"] = max(group["maximum"], transaction.amount)

    for group in result.values():
        group["average"] = group["total"] / group["count"]

    return result


def conditional_aggregation_by_region(
    transactions: Iterable[Transaction],
) -> dict[str, dict[str, float]]:
    """
    Conditional aggregation counts and sums only records satisfying a
    condition. The conditions are explicit so that completed revenue is not
    accidentally confused with failed or refunded transaction volume.
    """
    result: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "transactions": 0,
            "completed_count": 0,
            "failed_count": 0,
            "refunded_count": 0,
            "completed_amount": 0.0,
            "failed_amount": 0.0,
            "refunded_amount": 0.0,
            "high_value_completed_count": 0,
        }
    )

    for transaction in transactions:
        group = result[transaction.region]
        group["transactions"] += 1

        if transaction.status == "completed":
            group["completed_count"] += 1
            group["completed_amount"] += transaction.amount

            if transaction.amount >= 2500:
                group["high_value_completed_count"] += 1

        elif transaction.status == "failed":
            group["failed_count"] += 1
            group["failed_amount"] += transaction.amount

        elif transaction.status == "refunded":
            group["refunded_count"] += 1
            group["refunded_amount"] += transaction.amount

    return dict(result)


def aggregate_by_category_and_status(
    transactions: Iterable[Transaction],
) -> dict[tuple[str, str], dict[str, float]]:
    """
    A compound grouping key models GROUP BY category, status.
    The same category can therefore have separate completed, failed, and
    refunded aggregates.
    """
    result: dict[tuple[str, str], dict[str, float]] = {}

    for transaction in transactions:
        key = (transaction.category, transaction.status)
        group = result.setdefault(
            key,
            {"count": 0, "total": 0.0, "average": 0.0},
        )

        group["count"] += 1
        group["total"] += transaction.amount

    for group in result.values():
        group["average"] = group["total"] / group["count"]

    return result


def aggregate_customers(
    transactions: Iterable[Transaction],
) -> dict[int, CustomerAggregate]:
    """
    Customer aggregation demonstrates how several conditional measures can
    be maintained in one accumulator rather than repeatedly scanning data.
    """
    result: dict[int, CustomerAggregate] = {}

    for transaction in transactions:
        aggregate = result.setdefault(
            transaction.customer_id,
            CustomerAggregate(customer_id=transaction.customer_id),
        )

        aggregate.transaction_count += 1
        aggregate.total_amount += transaction.amount

        if transaction.status == "completed":
            aggregate.successful_count += 1
            aggregate.successful_amount += transaction.amount
        elif transaction.status == "failed":
            aggregate.failed_count += 1
            aggregate.failed_amount += transaction.amount

    return result


def percentile(values: list[float], percentile_value: float) -> float:
    """
    A simple linear-interpolation percentile is useful when an aggregate
    requires distribution information rather than only count or sum.
    """
    if not values:
        raise ValueError("Cannot calculate a percentile of an empty dataset")

    if not 0 <= percentile_value <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * percentile_value / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower

    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def distribution_statistics(transactions: Iterable[Transaction]) -> dict[str, float]:
    amounts = [transaction.amount for transaction in transactions]

    if not amounts:
        return {}

    return {
        "count": len(amounts),
        "mean": mean(amounts),
        "median": median(amounts),
        "p90": percentile(amounts, 90),
        "p95": percentile(amounts, 95),
        "minimum": min(amounts),
        "maximum": max(amounts),
    }


def choose_strategy(
    transaction_count: int,
    number_of_groups: int,
    requires_multiple_metrics: bool,
) -> str:
    """
    Aggregation strategy is influenced by data shape and required measures.

    A hash-style dictionary is usually effective when grouping keys are
    discrete and the input does not need to be sorted. Sorting first can be
    useful when ordered output or streaming grouped processing is required.
    """
    if transaction_count >= 100_000 and number_of_groups < transaction_count // 10:
        return "Hash aggregation with dictionary-based accumulators"

    if requires_multiple_metrics:
        return "Single-pass accumulator aggregation"

    return "Simple grouped aggregation"


def top_customers(
    aggregates: dict[int, CustomerAggregate],
    minimum_completed_amount: float,
) -> list[CustomerAggregate]:
    qualifying = [
        aggregate
        for aggregate in aggregates.values()
        if aggregate.successful_amount >= minimum_completed_amount
    ]

    return sorted(
        qualifying,
        key=lambda aggregate: (
            aggregate.successful_amount,
            aggregate.success_rate,
        ),
        reverse=True,
    )


def print_region_report(
    region_totals: dict[str, dict[str, float]],
    conditional: dict[str, dict[str, float]],
) -> None:
    print("\nREGION AGGREGATION")
    print("-" * 82)
    print(
        f"{'Region':<10}{'Count':>8}{'Total':>14}"
        f"{'Average':>14}{'Minimum':>14}{'Maximum':>14}"
    )

    for region in sorted(region_totals):
        group = region_totals[region]
        print(
            f"{region:<10}"
            f"{int(group['count']):>8}"
            f"{group['total']:>14.2f}"
            f"{group['average']:>14.2f}"
            f"{group['minimum']:>14.2f}"
            f"{group['maximum']:>14.2f}"
        )

    print("\nCONDITIONAL REGION METRICS")
    print("-" * 100)
    print(
        f"{'Region':<10}{'Completed':>12}{'Failed':>10}{'Refunded':>12}"
        f"{'Completed Amount':>20}{'High Value':>14}"
    )

    for region in sorted(conditional):
        group = conditional[region]
        print(
            f"{region:<10}"
            f"{group['completed_count']:>12.0f}"
            f"{group['failed_count']:>10.0f}"
            f"{group['refunded_count']:>12.0f}"
            f"{group['completed_amount']:>20.2f}"
            f"{group['high_value_completed_count']:>14.0f}"
        )


def print_customer_report(aggregates: dict[int, CustomerAggregate]) -> None:
    print("\nCUSTOMER AGGREGATION")
    print("-" * 96)
    print(
        f"{'Customer':<12}{'Transactions':>14}{'Total':>14}"
        f"{'Completed':>14}{'Failed':>14}{'Success %':>12}"
    )

    for customer_id in sorted(aggregates):
        aggregate = aggregates[customer_id]
        print(
            f"{customer_id:<12}"
            f"{aggregate.transaction_count:>14}"
            f"{aggregate.total_amount:>14.2f}"
            f"{aggregate.successful_amount:>14.2f}"
            f"{aggregate.failed_amount:>14.2f}"
            f"{aggregate.success_rate:>11.1f}%"
        )


def demonstrate_filter_before_aggregation(
    transactions: list[Transaction],
) -> None:
    """
    Filtering before aggregation changes the population being aggregated.
    This is equivalent to a SQL WHERE condition before GROUP BY.
    """
    completed = [
        transaction
        for transaction in transactions
        if transaction.status == "completed"
    ]

    completed_by_category = defaultdict(float)

    for transaction in completed:
        completed_by_category[transaction.category] += transaction.amount

    print("\nCOMPLETED REVENUE BY CATEGORY")
    print("-" * 50)

    for category, amount in sorted(completed_by_category.items()):
        print(f"{category:<15}{amount:>15.2f}")


def demonstrate_post_aggregation_filter(
    aggregates: dict[int, CustomerAggregate],
) -> None:
    """
    Filtering on an aggregate is conceptually different from filtering raw
    transactions. A condition such as total successful amount > 4000 must be
    evaluated after customer grouping has taken place.
    """
    print("\nCUSTOMERS ABOVE COMPLETED-AMOUNT THRESHOLD")
    print("-" * 55)

    for aggregate in top_customers(aggregates, 4000):
        print(
            f"Customer {aggregate.customer_id}: "
            f"completed={aggregate.successful_amount:.2f}, "
            f"success_rate={aggregate.success_rate:.1f}%"
        )


def demonstrate_time_window_aggregation(
    transactions: list[Transaction],
) -> None:
    start = min(transaction.created_at for transaction in transactions)
    end = start + timedelta(days=10)

    window = [
        transaction
        for transaction in transactions
        if start <= transaction.created_at < end
    ]

    total = sum(transaction.amount for transaction in window)
    completed = sum(
        transaction.amount
        for transaction in window
        if transaction.status == "completed"
    )

    print("\nTIME-WINDOW AGGREGATION")
    print("-" * 50)
    print(f"Window start:       {start}")
    print(f"Window end:         {end}")
    print(f"Transactions:       {len(window)}")
    print(f"Transaction volume: {total:.2f}")
    print(f"Completed volume:   {completed:.2f}")


def demonstrate_validation_failure() -> None:
    invalid = Transaction(
        transaction_id=9999,
        customer_id=999,
        region="North",
        category="Cloud",
        amount=-25.0,
        status="completed",
        created_at=datetime.now(),
    )

    try:
        validate_transactions([invalid])
    except ValueError as exc:
        print("\nVALIDATION FAILURE")
        print("-" * 50)
        print(exc)


def main() -> None:
    transactions = validate_transactions(sample_transactions())

    print("ADVANCED AGGREGATION WORKFLOW")
    print("=" * 82)
    print(f"Validated transaction records: {len(transactions)}")

    region_totals = aggregate_by_region(transactions)
    conditional = conditional_aggregation_by_region(transactions)
    customer_totals = aggregate_customers(transactions)
    category_status = aggregate_by_category_and_status(transactions)

    print_region_report(region_totals, conditional)
    print_customer_report(customer_totals)

    print("\nCATEGORY / STATUS AGGREGATION")
    print("-" * 70)
    for (category, status), values in sorted(category_status.items()):
        print(
            f"{category:<15}{status:<12}"
            f"count={values['count']:<5.0f}"
            f"total={values['total']:>12.2f}"
            f"average={values['average']:>12.2f}"
        )

    demonstrate_filter_before_aggregation(transactions)
    demonstrate_post_aggregation_filter(customer_totals)
    demonstrate_time_window_aggregation(transactions)

    statistics = distribution_statistics(transactions)

    print("\nDISTRIBUTION AGGREGATES")
    print("-" * 50)
    for name, value in statistics.items():
        print(f"{name:<12}{value:>12.2f}")

    strategy = choose_strategy(
        transaction_count=len(transactions),
        number_of_groups=len(region_totals),
        requires_multiple_metrics=True,
    )

    print("\nAGGREGATION STRATEGY")
    print("-" * 50)
    print(strategy)

    print("\nHIGH-VALUE CUSTOMER RANKING")
    print("-" * 50)
    for aggregate in top_customers(customer_totals, 3000):
        print(
            f"Customer {aggregate.customer_id}: "
            f"{aggregate.successful_amount:.2f} completed volume"
        )

    demonstrate_validation_failure()


if __name__ == "__main__":
    main()
