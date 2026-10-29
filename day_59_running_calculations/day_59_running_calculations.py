from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from statistics import mean
from typing import Iterable


class MetricKind(Enum):
    TOTAL = "total"
    AVERAGE = "average"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


@dataclass
class RunningMetrics:
    count: int = 0
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    values: list[float] = field(default_factory=list)

    def add(self, value: float) -> dict[str, float | int | None]:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("metric value must be numeric")

        if not float("-inf") < float(value) < float("inf"):
            raise ValueError("metric value must be finite")

        value = float(value)
        self.count += 1
        self.total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        self.values.append(value)

        return self.snapshot()

    @property
    def cumulative_average(self) -> float:
        return self.total / self.count if self.count else 0.0

    def cumulative_average_after(self, value: float) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("metric value must be numeric")
        return (self.total + float(value)) / (self.count + 1)

    def snapshot(self) -> dict[str, float | int | None]:
        return {
            "count": self.count,
            "running_total": self.total,
            "cumulative_average": self.cumulative_average,
            "running_minimum": self.minimum,
            "running_maximum": self.maximum,
        }


class RunningSeries:
    """Maintains multiple cumulative metrics over an ordered data stream."""

    def __init__(self, name: str) -> None:
        if not name.strip():
            raise ValueError("series name cannot be empty")
        self.name = name
        self.metrics = RunningMetrics()

    def process(self, values: Iterable[float]) -> list[dict[str, float | int | None]]:
        results = []
        for value in values:
            results.append(self.metrics.add(value))
        return results

    def percentile_rank(self, value: float) -> float:
        if not self.metrics.values:
            return 0.0

        ordered = sorted(self.metrics.values)
        less_or_equal = sum(item <= value for item in ordered)
        return less_or_equal / len(ordered)

    def summary(self) -> dict[str, object]:
        snapshot = self.metrics.snapshot()
        snapshot["series"] = self.name
        snapshot["median"] = mean(self.metrics.values) if self.metrics.values else None
        return snapshot


def calculate_running_totals(values: Iterable[float]) -> list[float]:
    total = 0.0
    result = []

    for value in values:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("all values must be numeric")
        total += float(value)
        result.append(total)

    return result


def calculate_cumulative_averages(values: Iterable[float]) -> list[float]:
    total = 0.0
    result = []

    for index, value in enumerate(values, start=1):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("all values must be numeric")
        total += float(value)
        result.append(total / index)

    return result


def calculate_running_metrics(values: Iterable[float]) -> list[dict[str, float | int | None]]:
    tracker = RunningMetrics()
    return [tracker.add(value) for value in values]


def process_sales_stream(records: list[dict[str, object]]) -> list[dict[str, object]]:
    tracker = RunningMetrics()
    output: list[dict[str, object]] = []

    for record in records:
        if "amount" not in record:
            raise ValueError("sales record requires an amount")

        amount = record["amount"]
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise TypeError("sales amount must be numeric")

        snapshot = tracker.add(float(amount))
        output.append(
            {
                "transaction_id": record.get("transaction_id"),
                "amount": float(amount),
                **snapshot,
            }
        )

    return output


def assert_expected() -> None:
    values = [10, 20, 30, 40]

    assert calculate_running_totals(values) == [10.0, 30.0, 60.0, 100.0]
    assert calculate_cumulative_averages(values) == [10.0, 15.0, 20.0, 25.0]

    metrics = calculate_running_metrics(values)
    assert metrics[-1]["running_total"] == 100.0
    assert metrics[-1]["cumulative_average"] == 25.0
    assert metrics[-1]["running_minimum"] == 10.0
    assert metrics[-1]["running_maximum"] == 40.0

    tracker = RunningMetrics()
    assert tracker.cumulative_average == 0.0
    assert tracker.add(5)["cumulative_average"] == 5.0
    assert tracker.cumulative_average_after(15) == 10.0

    try:
        tracker.add(float("nan"))
    except ValueError:
        pass
    else:
        raise AssertionError("non-finite values must be rejected")


def main() -> None:
    assert_expected()

    daily_sales = [
        {"transaction_id": "TX-001", "amount": 1250.00},
        {"transaction_id": "TX-002", "amount": 875.50},
        {"transaction_id": "TX-003", "amount": 1499.25},
        {"transaction_id": "TX-004", "amount": 650.00},
        {"transaction_id": "TX-005", "amount": 2100.75},
    ]

    print("Running sales metrics:")
    for row in process_sales_stream(daily_sales):
        print(
            f"{row['transaction_id']}: "
            f"amount={row['amount']:.2f}, "
            f"total={row['running_total']:.2f}, "
            f"average={row['cumulative_average']:.2f}, "
            f"min={row['running_minimum']:.2f}, "
            f"max={row['running_maximum']:.2f}"
        )

    tracker = RunningSeries("Daily Sales")
    tracker.process([1250, 875.50, 1499.25, 650, 2100.75])

    print("\nSeries summary:")
    for key, value in tracker.summary().items():
        print(f"{key}: {value}")

    print("\nPerformance note:")
    print("Running totals, averages, minimums, and maximums require O(1) work per value.")
    print("The RunningMetrics object uses O(1) state when historical values are not required.")
    print("RunningSeries retains values only because percentile-style analysis needs history.")


if __name__ == "__main__":
    main()
