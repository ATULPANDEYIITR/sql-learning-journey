from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable, Iterable, Optional


MAX_EVENTS = 1_000_000


@dataclass(frozen=True)
class SalesEvent:
    event_id: str
    store_id: str
    product_id: str
    sale_date: date
    units: int
    revenue: Decimal

    def __post_init__(self) -> None:
        if not self.event_id or not self.store_id or not self.product_id:
            raise ValueError("Event, store, and product identifiers are required.")
        if self.units <= 0:
            raise ValueError("Units must be positive.")
        if not self.revenue.is_finite() or self.revenue < 0:
            raise ValueError("Revenue must be a finite, non-negative amount.")
        if self.revenue.as_tuple().exponent < -2:
            raise ValueError("Revenue supports a maximum of two decimal places.")


@dataclass(frozen=True)
class AnalyticsPolicy:
    window_days: int = 7
    maximum_span_days: int = 3660
    revenue_weight: Decimal = Decimal("0.60")
    growth_weight: Decimal = Decimal("0.40")

    def __post_init__(self) -> None:
        if self.window_days < 1:
            raise ValueError("Window length must be positive.")
        if self.maximum_span_days < 2 * self.window_days:
            raise ValueError("Maximum span must support two complete windows.")
        if self.maximum_span_days > 3660:
            raise ValueError("Maximum permitted span is 3660 days.")
        if self.revenue_weight < 0 or self.growth_weight < 0:
            raise ValueError("Ranking weights cannot be negative.")
        if self.revenue_weight + self.growth_weight != Decimal("1"):
            raise ValueError("Ranking weights must add up to 1.")


@dataclass
class MetricWork:
    store_id: str
    product_id: str
    sale_date: date
    daily_revenue: Decimal
    daily_units: int
    rolling_revenue: Decimal
    rolling_units: int
    moving_average_revenue: Decimal
    previous_7d_revenue: Optional[Decimal]
    growth_rate: Optional[Decimal]
    previous_day_revenue: Optional[Decimal]
    cumulative_revenue: Decimal
    revenue_rank: Optional[int] = None
    growth_rank: Optional[int] = None
    composite_score: Optional[Decimal] = None
    composite_rank: Optional[int] = None


@dataclass(frozen=True)
class AnalyticsRow:
    store_id: str
    product_id: str
    sale_date: date
    daily_revenue: Decimal
    daily_units: int
    rolling_revenue_7d: Decimal
    rolling_units_7d: int
    moving_average_revenue_7d: Decimal
    previous_7d_revenue: Optional[Decimal]
    growth_rate: Optional[Decimal]
    previous_day_revenue: Optional[Decimal]
    cumulative_revenue: Decimal
    revenue_rank: Optional[int]
    growth_rank: Optional[int]
    composite_score: Optional[Decimal]
    composite_rank: Optional[int]
    ranking_eligible: bool


def safe_growth(current: Decimal, previous: Optional[Decimal]) -> Optional[Decimal]:
    """Return fractional growth; undefined growth is represented by None."""
    if previous is None or previous <= 0:
        return None
    return (current - previous) / previous


def competition_ranks(
    items: list[MetricWork],
    value_of: Callable[[MetricWork], Decimal],
) -> dict[str, int]:
    """
    Assign SQL-style RANK() values.

    Tied observations receive the same rank, and the following rank contains
    the corresponding gap. For example, 1, 1, 3.
    """
    ordered = sorted(items, key=value_of, reverse=True)
    ranks: dict[str, int] = {}
    previous_value: Optional[Decimal] = None
    current_rank = 0

    for position, item in enumerate(ordered, start=1):
        value = value_of(item)
        if position == 1 or value != previous_value:
            current_rank = position
        ranks[item.product_id] = current_rank
        previous_value = value

    return ranks


def normalized_rank_score(rank: int, population_size: int) -> Decimal:
    """
    Convert a competition rank into a score where 1 is best and 0 is worst.

    A one-member population receives 1 because it has no competing candidate.
    """
    if population_size <= 1:
        return Decimal("1")
    return Decimal(population_size - rank) / Decimal(population_size - 1)


class WindowAnalyticsEngine:
    def __init__(self, policy: AnalyticsPolicy | None = None) -> None:
        self.policy = policy or AnalyticsPolicy()

    def _validate_events(self, events: Iterable[SalesEvent]) -> list[SalesEvent]:
        validated = list(events)

        if not validated:
            raise ValueError("At least one sales event is required.")
        if len(validated) > MAX_EVENTS:
            raise ValueError(f"Event limit exceeded: {MAX_EVENTS}.")

        seen_ids: set[str] = set()

        for event in validated:
            if not isinstance(event, SalesEvent):
                raise TypeError("Every input item must be a SalesEvent.")
            if event.event_id in seen_ids:
                raise ValueError(f"Duplicate event identifier: {event.event_id}.")
            seen_ids.add(event.event_id)

        return validated

    def calculate(self, events: Iterable[SalesEvent]) -> list[AnalyticsRow]:
        """
        Execute the analytics pipeline:

        1. Validate transaction events.
        2. Aggregate transactions into daily product-store metrics.
        3. Fill missing calendar dates with zero activity.
        4. Calculate rolling windows and growth.
        5. Rank products and calculate the weighted ranking score.
        """
        validated = self._validate_events(events)

        # The first aggregation reduces transaction-level data to one row
        # per store, product, and calendar date.
        daily_totals: dict[tuple[str, str, date], list] = defaultdict(
            lambda: [Decimal("0"), 0]
        )

        for event in validated:
            key = (event.store_id, event.product_id, event.sale_date)
            daily_totals[key][0] += event.revenue
            daily_totals[key][1] += event.units

        # A separate calendar series is maintained for each store-product
        # combination. Missing dates are explicit zero-activity observations.
        series: dict[tuple[str, str], dict[date, list]] = defaultdict(dict)

        for (store_id, product_id, sale_date), totals in daily_totals.items():
            series[(store_id, product_id)][sale_date] = totals

        work_rows: list[MetricWork] = []
        window = self.policy.window_days

        for (store_id, product_id), observations in sorted(series.items()):
            first_day = min(observations)
            last_day = max(observations)
            span = (last_day - first_day).days + 1

            if span > self.policy.maximum_span_days:
                raise ValueError(
                    f"Date span for {store_id}/{product_id} exceeds "
                    f"{self.policy.maximum_span_days} days."
                )

            daily_revenue: list[Decimal] = []
            daily_units: list[int] = []
            calendar_dates: list[date] = []

            current = first_day
            while current <= last_day:
                totals = observations.get(current, [Decimal("0"), 0])
                calendar_dates.append(current)
                daily_revenue.append(totals[0])
                daily_units.append(totals[1])
                current += timedelta(days=1)

            # Prefix sums permit constant-time window sum calculations.
            revenue_prefix = [Decimal("0")]
            units_prefix = [0]

            for revenue, units in zip(daily_revenue, daily_units):
                revenue_prefix.append(revenue_prefix[-1] + revenue)
                units_prefix.append(units_prefix[-1] + units)

            for index, current_date in enumerate(calendar_dates):
                current_start = max(0, index - window + 1)

                rolling_revenue = (
                    revenue_prefix[index + 1] - revenue_prefix[current_start]
                )
                rolling_units = units_prefix[index + 1] - units_prefix[current_start]
                observed_days = index - current_start + 1
                moving_average = rolling_revenue / Decimal(observed_days)

                previous_7d_revenue: Optional[Decimal] = None
                growth_rate: Optional[Decimal] = None

                # Growth compares two non-overlapping, complete windows.
                # The first eligible observation occurs after 2 * window - 1
                # prior calendar positions, including the current position.
                if index >= (2 * window - 1):
                    previous_start = index - (2 * window) + 1
                    previous_end = index - window + 1
                    previous_7d_revenue = (
                        revenue_prefix[previous_end] - revenue_prefix[previous_start]
                    )
                    growth_rate = safe_growth(
                        rolling_revenue, previous_7d_revenue
                    )

                previous_day_revenue = (
                    daily_revenue[index - 1] if index > 0 else None
                )

                work_rows.append(
                    MetricWork(
                        store_id=store_id,
                        product_id=product_id,
                        sale_date=current_date,
                        daily_revenue=daily_revenue[index],
                        daily_units=daily_units[index],
                        rolling_revenue=rolling_revenue,
                        rolling_units=rolling_units,
                        moving_average_revenue=moving_average,
                        previous_7d_revenue=previous_7d_revenue,
                        growth_rate=growth_rate,
                        previous_day_revenue=previous_day_revenue,
                        cumulative_revenue=revenue_prefix[index + 1],
                    )
                )

        # Ranking populations are defined by store and date. A product is
        # compared with other products in that store on the same date.
        rankings_by_store_day: dict[tuple[str, date], list[MetricWork]] = defaultdict(list)

        for row in work_rows:
            rankings_by_store_day[(row.store_id, row.sale_date)].append(row)

        for candidates in rankings_by_store_day.values():
            revenue_ranks = competition_ranks(
                candidates, lambda item: item.rolling_revenue
            )

            for row in candidates:
                row.revenue_rank = revenue_ranks[row.product_id]

            eligible = [
                row
                for row in candidates
                if row.growth_rate is not None
                and row.previous_7d_revenue is not None
                and row.previous_7d_revenue > 0
            ]

            if not eligible:
                continue

            growth_ranks = competition_ranks(
                eligible, lambda item: item.growth_rate or Decimal("0")
            )

            population_size = len(eligible)

            for row in eligible:
                row.growth_rank = growth_ranks[row.product_id]

                revenue_score = normalized_rank_score(
                    row.revenue_rank or population_size, population_size
                )
                growth_score = normalized_rank_score(
                    row.growth_rank, population_size
                )

                row.composite_score = (
                    self.policy.revenue_weight * revenue_score
                    + self.policy.growth_weight * growth_score
                )

            composite_ranked = competition_ranks(
                eligible,
                lambda item: item.composite_score or Decimal("0"),
            )

            for row in eligible:
                row.composite_rank = composite_ranked[row.product_id]

        result = [
            AnalyticsRow(
                store_id=row.store_id,
                product_id=row.product_id,
                sale_date=row.sale_date,
                daily_revenue=row.daily_revenue,
                daily_units=row.daily_units,
                rolling_revenue_7d=row.rolling_revenue,
                rolling_units_7d=row.rolling_units,
                moving_average_revenue_7d=row.moving_average_revenue,
                previous_7d_revenue=row.previous_7d_revenue,
                growth_rate=row.growth_rate,
                previous_day_revenue=row.previous_day_revenue,
                cumulative_revenue=row.cumulative_revenue,
                revenue_rank=row.revenue_rank,
                growth_rank=row.growth_rank,
                composite_score=row.composite_score,
                composite_rank=row.composite_rank,
                ranking_eligible=row.composite_score is not None,
            )
            for row in work_rows
        ]

        return sorted(
            result,
            key=lambda row: (row.sale_date, row.store_id, row.product_id),
        )


def create_sample_events() -> list[SalesEvent]:
    """Generate reproducible retail data with aggregation and missing-day cases."""
    events: list[SalesEvent] = []
    start_date = date(2026, 10, 1)

    stores = ["LKO-01", "LKO-02"]
    products = ["P-A", "P-B", "P-C"]
    event_number = 1

    for store_index, store_id in enumerate(stores):
        for product_index, product_id in enumerate(products):
            for day_number in range(21):
                sale_date = start_date + timedelta(days=day_number)

                # One store-product combination has no sales on this date.
                if (
                    store_id == "LKO-02"
                    and product_id == "P-C"
                    and day_number == 5
                ):
                    continue

                revenue_cents = (
                    10000
                    + product_index * 1700
                    + store_index * 800
                    + day_number * (product_index * 220 + store_index * 90)
                )
                units = 5 + product_index + ((day_number + store_index) % 4)

                events.append(
                    SalesEvent(
                        event_id=f"EVT-{event_number:05d}",
                        store_id=store_id,
                        product_id=product_id,
                        sale_date=sale_date,
                        units=units,
                        revenue=Decimal(revenue_cents) / Decimal("100"),
                    )
                )
                event_number += 1

                # A second transaction on selected dates verifies daily
                # aggregation instead of assuming one transaction per day.
                if day_number % 5 == 0 and product_index == 0:
                    events.append(
                        SalesEvent(
                            event_id=f"EVT-{event_number:05d}",
                            store_id=store_id,
                            product_id=product_id,
                            sale_date=sale_date,
                            units=2,
                            revenue=Decimal(2500 + day_number * 10) / Decimal("100"),
                        )
                    )
                    event_number += 1

    return events


def export_csv(rows: list[AnalyticsRow], destination: Path) -> None:
    """Write computed rows without changing the analytical values."""
    if not destination.parent.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(AnalyticsRow.__dataclass_fields__)

    with destination.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            values = asdict(row)
            values["sale_date"] = row.sale_date.isoformat()

            for key, value in values.items():
                if isinstance(value, Decimal):
                    values[key] = format(value, "f")

            writer.writerow(values)


def run_checks(rows: list[AnalyticsRow]) -> None:
    """Verify important numerical and boundary conditions."""
    assert rows, "The analytics result cannot be empty."
    assert all(row.rolling_revenue_7d >= 0 for row in rows)
    assert all(row.rolling_units_7d >= 0 for row in rows)

    start = date(2026, 10, 1)

    missing_day = next(
        row
        for row in rows
        if row.store_id == "LKO-02"
        and row.product_id == "P-C"
        and row.sale_date == start + timedelta(days=5)
    )
    assert missing_day.daily_revenue == Decimal("0")
    assert missing_day.daily_units == 0

    first_day = next(
        row
        for row in rows
        if row.store_id == "LKO-01"
        and row.product_id == "P-A"
        and row.sale_date == start
    )
    assert first_day.moving_average_revenue_7d == first_day.daily_revenue
    assert first_day.previous_day_revenue is None
    assert not first_day.ranking_eligible

    first_eligible_day = start + timedelta(days=13)
    eligible = next(
        row
        for row in rows
        if row.store_id == "LKO-01"
        and row.product_id == "P-A"
        and row.sale_date == first_eligible_day
    )
    assert eligible.previous_7d_revenue is not None
    assert eligible.growth_rate is not None
    assert eligible.ranking_eligible

    assert safe_growth(Decimal("120"), Decimal("100")) == Decimal("0.2")
    assert safe_growth(Decimal("120"), Decimal("0")) is None
    assert safe_growth(Decimal("120"), None) is None


def print_report(rows: list[AnalyticsRow]) -> None:
    latest_date = max(row.sale_date for row in rows)
    latest_rows = [row for row in rows if row.sale_date == latest_date]

    print(f"Advanced Window Analytics | Reporting date: {latest_date}")
    print(
        f"{'Store':<10} {'Product':<8} {'Daily':>12} {'Rolling 7d':>12} "
        f"{'Growth %':>11} {'Score':>9} {'Rank':>6}"
    )
    print("-" * 78)

    for row in sorted(
        latest_rows,
        key=lambda item: (
            item.store_id,
            item.composite_rank if item.composite_rank is not None else 999999,
            item.product_id,
        ),
    ):
        growth = (
            f"{row.growth_rate * Decimal('100'):.2f}"
            if row.growth_rate is not None
            else "N/A"
        )
        score = (
            f"{row.composite_score:.4f}"
            if row.composite_score is not None
            else "N/A"
        )
        rank = str(row.composite_rank) if row.composite_rank is not None else "N/A"

        print(
            f"{row.store_id:<10} {row.product_id:<8} "
            f"{row.daily_revenue:>12.2f} {row.rolling_revenue_7d:>12.2f} "
            f"{growth:>11} {score:>9} {rank:>6}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate rolling metrics and combined product rankings."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Optional destination for the complete analytics result.",
    )
    args = parser.parse_args()

    try:
        events = create_sample_events()
        engine = WindowAnalyticsEngine()
        results = engine.calculate(events)

        run_checks(results)
        print_report(results)

        if args.csv:
            export_csv(results, args.csv)
            print(f"\nCSV exported to: {args.csv.resolve()}")

        print(f"\nTransactions processed: {len(events)}")
        print(f"Daily analytics rows: {len(results)}")
        print(f"Ranking-eligible rows: {sum(row.ranking_eligible for row in results)}")

    except (ValueError, TypeError, OSError, StopIteration) as exc:
        raise SystemExit(f"Analytics execution failed: {exc}") from exc


if __name__ == "__main__":
    main()
