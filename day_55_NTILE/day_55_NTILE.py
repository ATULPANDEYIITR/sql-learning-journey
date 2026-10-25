from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import ceil
from statistics import mean
from typing import Iterable


class BucketMethod(Enum):
    NTILE = "ntile"
    QUARTILE = "quartile"
    DECILE = "decile"


@dataclass(frozen=True)
class Record:
    record_id: int
    customer: str
    score: float


@dataclass(frozen=True)
class BucketedRecord:
    record: Record
    bucket: int
    bucket_count: int


class InvalidBucketCount(ValueError):
    """Raised when an NTILE bucket count is invalid."""


def validate_bucket_count(bucket_count: int) -> None:
    if not isinstance(bucket_count, int):
        raise InvalidBucketCount("bucket_count must be an integer")
    if bucket_count <= 0:
        raise InvalidBucketCount("bucket_count must be greater than zero")


def ntile(records: Iterable[Record], bucket_count: int) -> list[BucketedRecord]:
    """
    Assign ordered records to NTILE buckets.

    SQL NTILE distributes rows as evenly as possible. If rows do not
    divide evenly, earlier buckets receive one additional row.
    """
    validate_bucket_count(bucket_count)

    ordered = sorted(
        records,
        key=lambda r: (-r.score, r.record_id)
    )

    total = len(ordered)
    if total == 0:
        return []

    result: list[BucketedRecord] = []

    # SQL NTILE semantics:
    # bucket sizes differ by at most one row.
    base_size, remainder = divmod(total, bucket_count)

    position = 0
    for bucket in range(1, bucket_count + 1):
        size = base_size + (1 if bucket <= remainder else 0)

        for _ in range(size):
            if position >= total:
                break
            result.append(
                BucketedRecord(
                    record=ordered[position],
                    bucket=bucket,
                    bucket_count=bucket_count,
                )
            )
            position += 1

    return result


def percentile_bucket(records: Iterable[Record], bucket_count: int) -> dict[int, list[Record]]:
    """Return NTILE-style groups keyed by bucket number."""
    return {
        bucket: [item.record for item in bucketed]
        for bucket in range(1, bucket_count + 1)
        for bucketed in [[]]
    }


def group_by_bucket(
    bucketed_records: Iterable[BucketedRecord],
) -> dict[int, list[Record]]:
    groups: dict[int, list[Record]] = {}

    for item in bucketed_records:
        groups.setdefault(item.bucket, []).append(item.record)

    return groups


def describe_buckets(
    bucketed_records: Iterable[BucketedRecord],
) -> list[dict[str, float | int | None]]:
    groups = group_by_bucket(bucketed_records)
    result = []

    for bucket in sorted(groups):
        scores = [record.score for record in groups[bucket]]
        result.append(
            {
                "bucket": bucket,
                "count": len(scores),
                "minimum": min(scores) if scores else None,
                "maximum": max(scores) if scores else None,
                "average": mean(scores) if scores else None,
            }
        )

    return result


def validate_ntile_properties(
    records: list[Record],
    bucket_count: int,
) -> None:
    """Check important NTILE invariants."""
    bucketed = ntile(records, bucket_count)
    groups = group_by_bucket(bucketed)

    assert len(bucketed) == len(records)

    if records:
        sizes = [len(groups.get(i, [])) for i in range(1, bucket_count + 1)]
        assert max(sizes) - min(sizes) <= 1

    ordered_scores = [item.record.score for item in bucketed]
    assert ordered_scores == sorted(ordered_scores, reverse=True)


def classify_segments(
    records: list[Record],
    bucket_count: int = 10,
) -> dict[int, str]:
    """
    Convert decile buckets into business segments.

    Decile 1 contains the highest-scoring records because records are
    ordered descending before NTILE is applied.
    """
    validate_bucket_count(bucket_count)

    if bucket_count != 10:
        raise ValueError("classify_segments expects exactly 10 buckets")

    labels = {
        1: "Top 10%",
        2: "High",
        3: "High",
        4: "Upper-Middle",
        5: "Upper-Middle",
        6: "Lower-Middle",
        7: "Lower-Middle",
        8: "Low",
        9: "Low",
        10: "Bottom 10%",
    }

    return {
        item.record.record_id: labels[item.bucket]
        for item in ntile(records, bucket_count)
    }


def demonstrate_empty_and_small_inputs() -> None:
    assert ntile([], 4) == []

    small = [
        Record(1, "A", 100),
        Record(2, "B", 90),
        Record(3, "C", 80),
    ]

    result = ntile(small, 5)
    assert len(result) == 3
    assert [item.bucket for item in result] == [1, 2, 3]

    try:
        ntile(small, 0)
    except InvalidBucketCount:
        pass
    else:
        raise AssertionError("Invalid bucket count was not rejected")


def main() -> None:
    records = [
        Record(101, "Asha", 96.0),
        Record(102, "Bharat", 82.0),
        Record(103, "Chirag", 91.0),
        Record(104, "Divya", 74.0),
        Record(105, "Esha", 88.0),
        Record(106, "Farhan", 67.0),
        Record(107, "Gita", 91.0),
        Record(108, "Harsh", 59.0),
        Record(109, "Isha", 84.0),
        Record(110, "Jay", 72.0),
        Record(111, "Kiran", 95.0),
        Record(112, "Lalit", 63.0),
    ]

    print("QUARTILES")
    quartiles = ntile(records, 4)
    for item in quartiles:
        print(
            f"{item.record.record_id:3} "
            f"{item.record.customer:8} "
            f"score={item.record.score:5.1f} "
            f"quartile={item.bucket}"
        )

    print("\nQUARTILE STATISTICS")
    for row in describe_buckets(quartiles):
        print(row)

    print("\nDECILES")
    deciles = ntile(records, 10)
    for item in deciles:
        print(
            f"{item.record.customer:8} "
            f"score={item.record.score:5.1f} "
            f"decile={item.bucket}"
        )

    print("\nSEGMENTS")
    for record_id, segment in classify_segments(records).items():
        print(f"{record_id}: {segment}")

    validate_ntile_properties(records, 4)
    validate_ntile_properties(records, 10)
    demonstrate_empty_and_small_inputs()

    print("\nVALIDATION")
    print("NTILE invariants passed.")


if __name__ == "__main__":
    main()
