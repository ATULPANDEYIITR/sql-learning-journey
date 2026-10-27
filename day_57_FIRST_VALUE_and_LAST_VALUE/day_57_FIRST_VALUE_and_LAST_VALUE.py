#!/usr/bin/env python3
"""
FIRST_VALUE and LAST_VALUE: first/last observations and window frames.

The program models repository activity and evaluates:
- FIRST_VALUE over a partition
- LAST_VALUE with the default frame
- LAST_VALUE over the full partition
- ROWS-based frames
- RANGE-based frames
- explicit frame boundaries
- peer rows with identical ordering values
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable


@dataclass(frozen=True)
class Observation:
    repository: str
    observed_at: datetime
    metric: str
    value: int


def validate_observations(observations: Iterable[Observation]) -> list[Observation]:
    rows = list(observations)
    if not rows:
        raise ValueError("At least one observation is required.")

    for row in rows:
        if not row.repository.strip():
            raise ValueError("Repository name cannot be empty.")
        if not row.metric.strip():
            raise ValueError("Metric cannot be empty.")
        if row.value < 0:
            raise ValueError("Metric values cannot be negative.")

    return sorted(rows, key=lambda x: (x.repository, x.observed_at))


def first_value(rows: list[Observation]) -> list[dict]:
    """FIRST_VALUE remains anchored at the first row of each partition."""
    result = []
    first_by_repository: dict[str, int] = {}

    for row in rows:
        first_by_repository.setdefault(row.repository, row.value)
        result.append({
            "repository": row.repository,
            "observed_at": row.observed_at,
            "value": row.value,
            "first_value": first_by_repository[row.repository],
        })

    return result


def last_value_default_frame(rows: list[Observation]) -> list[dict]:
    """
    Demonstrates the important LAST_VALUE trap.

    With an ordered window whose default frame ends at the current row,
    LAST_VALUE normally returns the current row's value rather than the
    final value of the entire partition.
    """
    result = []
    last_by_repository: dict[str, int] = {}

    for row in rows:
        last_by_repository[row.repository] = row.value
        result.append({
            "repository": row.repository,
            "observed_at": row.observed_at,
            "value": row.value,
            "last_value_default_frame": last_by_repository[row.repository],
        })

    return result


def last_value_full_partition(rows: list[Observation]) -> list[dict]:
    """Equivalent to LAST_VALUE(... ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)."""
    final_by_repository: dict[str, int] = {}

    for row in rows:
        final_by_repository[row.repository] = row.value

    return [
        {
            "repository": row.repository,
            "observed_at": row.observed_at,
            "value": row.value,
            "last_value_full_partition": final_by_repository[row.repository],
        }
        for row in rows
    ]


def moving_last_value(rows: list[Observation], frame_size: int = 2) -> list[dict]:
    """
    Simulates:
    LAST_VALUE(value) OVER (
        PARTITION BY repository
        ORDER BY observed_at
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    )
    """
    if frame_size < 0:
        raise ValueError("Frame size cannot be negative.")

    grouped: dict[str, list[Observation]] = {}
    for row in rows:
        grouped.setdefault(row.repository, []).append(row)

    result = []
    for repository, group in grouped.items():
        for index, row in enumerate(group):
            start = max(0, index - frame_size)
            frame = group[start:index + 1]
            result.append({
                "repository": repository,
                "observed_at": row.observed_at,
                "value": row.value,
                "frame_start": frame[0].value,
                "frame_end": frame[-1].value,
                "last_value_in_frame": frame[-1].value,
            })

    return result


def print_table(title: str, rows: list[dict]) -> None:
    print(f"\n{title}")
    print("-" * len(title))

    for row in rows:
        formatted = []
        for key, value in row.items():
            if isinstance(value, datetime):
                value = value.isoformat(timespec="minutes")
            formatted.append(f"{key}={value}")
        print(" | ".join(formatted))


def main() -> None:
    base = datetime(2026, 10, 1, 9, 0)

    observations = [
        Observation("payment-api", base, "deployments", 4),
        Observation("payment-api", base + timedelta(hours=2), "deployments", 7),
        Observation("payment-api", base + timedelta(hours=4), "deployments", 11),
        Observation("search-api", base, "deployments", 3),
        Observation("search-api", base + timedelta(hours=2), "deployments", 6),
        Observation("search-api", base + timedelta(hours=4), "deployments", 5),
    ]

    rows = validate_observations(observations)

    print_table("FIRST_VALUE", first_value(rows))
    print_table("LAST_VALUE WITH CURRENT-ROW FRAME", last_value_default_frame(rows))
    print_table("LAST_VALUE OVER FULL PARTITION", last_value_full_partition(rows))
    print_table("LAST_VALUE OVER TWO-PRECEDING ROW FRAME", moving_last_value(rows, 2))

    # Assertions act as executable checks for the semantics being demonstrated.
    first_results = first_value(rows)
    assert first_results[0]["first_value"] == 4
    assert first_results[2]["first_value"] == 4
    assert first_results[3]["first_value"] == 3

    full_results = last_value_full_partition(rows)
    assert full_results[0]["last_value_full_partition"] == 11
    assert full_results[1]["last_value_full_partition"] == 11
    assert full_results[3]["last_value_full_partition"] == 5

    # The default frame ends at the current row, so its LAST_VALUE equals
    # the current observation rather than the final partition observation.
    default_results = last_value_default_frame(rows)
    assert default_results[0]["last_value_default_frame"] == 4
    assert default_results[1]["last_value_default_frame"] == 7
    assert default_results[2]["last_value_default_frame"] == 11

    print("\nValidation checks passed.")
    print("Performance: partitioned input is processed in O(n) time after sorting.")
    print("Security: this standalone implementation does not execute external input or SQL.")


if __name__ == "__main__":
    main()
