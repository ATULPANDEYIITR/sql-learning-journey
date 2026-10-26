from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from statistics import mean
from typing import Iterable


class Trend(Enum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DailyMetric:
    day: date
    value: float


@dataclass(frozen=True)
class Comparison:
    day: date
    value: float
    previous_value: float | None
    next_value: float | None
    change_from_previous: float | None
    change_to_next: float | None
    trend_from_previous: Trend
    trend_to_next: Trend


def validate_series(series: Iterable[DailyMetric]) -> list[DailyMetric]:
    data = list(series)

    if not data:
        raise ValueError("The time series cannot be empty.")

    if any(item.value != item.value for item in data):
        raise ValueError("NaN values are not permitted.")

    ordered = sorted(data, key=lambda item: item.day)

    if len({item.day for item in ordered}) != len(ordered):
        raise ValueError("Duplicate dates are not permitted.")

    return ordered


def safe_change(current: float, reference: float | None) -> float | None:
    if reference is None:
        return None
    if reference == 0:
        return None
    return current - reference


def percentage_change(current: float, reference: float | None) -> float | None:
    if reference is None or reference == 0:
        return None
    return ((current - reference) / reference) * 100.0


def classify(current: float, reference: float | None) -> Trend:
    if reference is None:
        return Trend.UNKNOWN

    if current > reference:
        return Trend.UP
    if current < reference:
        return Trend.DOWN
    return Trend.FLAT


def analyze(series: Iterable[DailyMetric]) -> list[Comparison]:
    data = validate_series(series)
    result: list[Comparison] = []

    for index, item in enumerate(data):
        previous = data[index - 1].value if index > 0 else None
        following = data[index + 1].value if index + 1 < len(data) else None

        result.append(
            Comparison(
                day=item.day,
                value=item.value,
                previous_value=previous,
                next_value=following,
                change_from_previous=safe_change(item.value, previous),
                change_to_next=safe_change(following, item.value)
                if following is not None
                else None,
                trend_from_previous=classify(item.value, previous),
                trend_to_next=classify(following, item.value)
                if following is not None
                else Trend.UNKNOWN,
            )
        )

    return result


def rolling_lag_average(series: Iterable[DailyMetric], periods: int = 1) -> list[tuple[date, float | None]]:
    data = validate_series(series)

    if periods < 1:
        raise ValueError("periods must be at least 1.")

    output: list[tuple[date, float | None]] = []

    for index, item in enumerate(data):
        if index < periods:
            output.append((item.day, None))
        else:
            historical = [data[i].value for i in range(index - periods, index)]
            output.append((item.day, mean(historical)))

    return output


def detect_reversals(series: Iterable[DailyMetric]) -> list[DailyMetric]:
    data = validate_series(series)

    if len(data) < 3:
        return []

    reversals: list[DailyMetric] = []

    for index in range(1, len(data) - 1):
        previous = data[index - 1].value
        current = data[index].value
        following = data[index + 1].value

        rising_before = current > previous
        falling_after = following < current

        falling_before = current < previous
        rising_after = following > current

        if (rising_before and falling_after) or (falling_before and rising_after):
            reversals.append(data[index])

    return reversals


def print_report(series: Iterable[DailyMetric]) -> None:
    data = validate_series(series)
    comparisons = analyze(data)

    print("DATE       VALUE   LAG       LEAD      LAG Δ     LEAD Δ   LAG TREND  LEAD TREND")
    print("-" * 82)

    for item in comparisons:
        print(
            f"{item.day} "
            f"{item.value:7.2f} "
            f"{item.previous_value if item.previous_value is not None else '-':>7} "
            f"{item.next_value if item.next_value is not None else '-':>9} "
            f"{item.change_from_previous if item.change_from_previous is not None else '-':>8} "
            f"{item.change_to_next if item.change_to_next is not None else '-':>9} "
            f"{item.trend_from_previous.value:>10} "
            f"{item.trend_to_next.value:>10}"
        )

    print("\nPercentage changes:")
    for index, item in enumerate(data):
        previous = data[index - 1].value if index > 0 else None
        next_value = data[index + 1].value if index + 1 < len(data) else None

        print(
            f"{item.day}: "
            f"vs previous={percentage_change(item.value, previous)}, "
            f"vs next={percentage_change(next_value, item.value) if next_value is not None else None}"
        )

    reversals = detect_reversals(data)
    print("\nTrend reversals:")
    if reversals:
        for item in reversals:
            print(f"{item.day}: {item.value:.2f}")
    else:
        print("None")


def build_demo_data() -> list[DailyMetric]:
    start = date(2026, 10, 19)
    values = [120.0, 126.0, 131.0, 127.0, 135.0, 135.0, 142.0]

    return [
        DailyMetric(start + timedelta(days=index), value)
        for index, value in enumerate(values)
    ]


def run_self_checks() -> None:
    sample = [
        DailyMetric(date(2026, 1, 1), 100),
        DailyMetric(date(2026, 1, 2), 110),
        DailyMetric(date(2026, 1, 3), 105),
    ]

    result = analyze(sample)

    assert result[0].previous_value is None
    assert result[0].next_value == 110
    assert result[1].previous_value == 100
    assert result[1].next_value == 105
    assert result[1].change_from_previous == 10
    assert result[1].change_to_next == -5
    assert percentage_change(110, 100) == 10
    assert detect_reversals(sample) == [sample[1]]

    try:
        validate_series(
            [
                DailyMetric(date(2026, 1, 1), 10),
                DailyMetric(date(2026, 1, 1), 20),
            ]
        )
        raise AssertionError("Duplicate-date validation failed.")
    except ValueError:
        pass

    try:
        rolling_lag_average(sample, 0)
        raise AssertionError("Period validation failed.")
    except ValueError:
        pass


if __name__ == "__main__":
    run_self_checks()

    metrics = build_demo_data()
    print_report(metrics)

    print("\nTwo-period historical average:")
    for day, value in rolling_lag_average(metrics, periods=2):
        print(f"{day}: {value if value is not None else '-'}")
