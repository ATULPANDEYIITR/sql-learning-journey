"""
CROSS JOIN: Cartesian Products, Combination Generation, and Risk Control

A self-contained executable study of SQL-style CROSS JOIN behavior implemented
and simulated in Python.

The program demonstrates:
- Cartesian products
- Exact cardinality calculation
- Combination generation
- Empty-input behavior
- Duplicate values
- Filtering Cartesian products into meaningful combinations
- Resource-risk estimation
- Chunked generation
- Streaming generation
- A realistic repository-permission matrix example
- Validation and defensive controls
- Complexity and memory considerations
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import prod
from typing import Iterable, Iterator, Sequence, TypeVar


T = TypeVar("T")
U = TypeVar("U")


def heading(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def cross_join(left: Sequence[T], right: Sequence[U]) -> list[tuple[T, U]]:
    """Return the Cartesian product of two finite sequences."""
    return [(left_item, right_item) for left_item in left for right_item in right]


def cross_join_stream(
    left: Iterable[T],
    right: Sequence[U],
) -> Iterator[tuple[T, U]]:
    """
    Generate Cartesian-product rows lazily.

    The right side is materialized as a sequence because it must be traversed
    once for every left-side value. The produced combinations themselves are
    not retained in memory.
    """
    for left_item in left:
        for right_item in right:
            yield left_item, right_item


def cross_join_many(groups: Sequence[Sequence[T]]) -> list[tuple[T, ...]]:
    """Generate a Cartesian product across any number of groups."""
    if not groups:
        return [()]
    return list(product(*groups))


def expected_cartesian_size(*groups: Sequence[object]) -> int:
    """
    Calculate the exact number of rows a Cartesian product will contain.

    For n groups, the result is:
        len(group_1) * len(group_2) * ... * len(group_n)

    An empty group makes the result zero.
    """
    if not groups:
        return 1
    return prod(len(group) for group in groups)


def safe_expected_size(
    groups: Sequence[Sequence[object]],
    maximum_rows: int,
) -> int:
    """
    Calculate Cartesian-product size while enforcing an application limit.

    The multiplication is performed incrementally so an unexpectedly large
    product can be rejected before materializing combinations.
    """
    if maximum_rows < 0:
        raise ValueError("maximum_rows must not be negative")

    total = 1
    for group in groups:
        if not isinstance(group, Sequence):
            raise TypeError("Every group must be a sequence")

        size = len(group)

        if size == 0:
            return 0

        if total > maximum_rows // size:
            raise ValueError(
                f"Cartesian product exceeds the configured limit of "
                f"{maximum_rows:,} rows"
            )

        total *= size

    return total


def print_rows(rows: Sequence[tuple], limit: int = 20) -> None:
    """Print a bounded preview instead of accidentally dumping huge results."""
    if limit < 0:
        raise ValueError("limit must not be negative")

    for index, row in enumerate(rows[:limit], start=1):
        print(f"{index:>3}: {row}")

    if len(rows) > limit:
        print(f"... {len(rows) - limit:,} additional rows omitted")


def demo_two_table_cartesian_product() -> None:
    heading("Two-Input Cartesian Product")

    developers = ["Asha", "Ravi", "Maya"]
    environments = ["development", "staging", "production"]

    rows = cross_join(developers, environments)

    print(f"Developers:   {len(developers)}")
    print(f"Environments: {len(environments)}")
    print(f"Rows:         {len(rows)}")
    print()
    print_rows(rows)

    assert len(rows) == 3 * 3


def demo_many_input_product() -> None:
    heading("Multiple Dimensions")

    regions = ["India", "Europe"]
    environments = ["staging", "production"]
    deployment_windows = ["business-hours", "maintenance-window"]

    rows = cross_join_many(
        [regions, environments, deployment_windows]
    )

    print(
        f"{len(regions)} regions × "
        f"{len(environments)} environments × "
        f"{len(deployment_windows)} windows = "
        f"{len(rows)} combinations"
    )

    print_rows(rows)

    assert len(rows) == 2 * 2 * 2


def demo_duplicates() -> None:
    heading("Duplicate Values Are Not Automatically Removed")

    left = ["Python", "Python", "Java"]
    right = ["Linux", "Windows"]

    rows = cross_join(left, right)

    print("The first input contains Python twice.")
    print("A Cartesian product operates on rows/positions, not set semantics.")
    print_rows(rows)

    assert len(rows) == 3 * 2


def demo_empty_inputs() -> None:
    heading("Empty Input")

    print(
        "An empty input relation produces zero Cartesian-product rows "
        "when combined with a non-empty relation."
    )

    rows = cross_join(["A", "B"], [])
    print(f"Rows generated: {len(rows)}")

    assert rows == []


def demo_filter_after_cross_join() -> None:
    heading("Filtering a Cartesian Product")

    roles = ["developer", "reviewer", "admin"]
    repositories = ["api", "web", "database"]

    all_pairs = cross_join(roles, repositories)

    # The CROSS JOIN creates every role/repository pair. The predicate then
    # reduces that broad candidate space to combinations that make sense.
    allowed_pairs = [
        pair
        for pair in all_pairs
        if not (pair[0] == "admin" and pair[1] == "web")
    ]

    print(f"Candidate pairs: {len(all_pairs)}")
    print(f"Allowed pairs:   {len(allowed_pairs)}")
    print()
    print_rows(allowed_pairs)

    assert len(all_pairs) == 9
    assert ("admin", "web") not in allowed_pairs


@dataclass(frozen=True)
class PermissionCombination:
    role: str
    repository: str
    environment: str
    permission: str


def build_permission_matrix() -> list[PermissionCombination]:
    """
    Build a realistic configuration matrix.

    A CROSS JOIN is useful when every value from several independent
    dimensions must be considered before policy rules eliminate invalid
    combinations.
    """
    roles = ["developer", "reviewer", "release-manager"]
    repositories = ["payments-api", "customer-web"]
    environments = ["staging", "production"]
    permissions = ["read", "write", "deploy"]

    candidates = product(
        roles,
        repositories,
        environments,
        permissions,
    )

    result: list[PermissionCombination] = []

    for role, repository, environment, permission in candidates:
        # Policy rules are intentionally applied after candidate generation.
        if environment == "production" and permission == "deploy":
            if role != "release-manager":
                continue

        if permission == "write" and role == "reviewer":
            continue

        result.append(
            PermissionCombination(
                role=role,
                repository=repository,
                environment=environment,
                permission=permission,
            )
        )

    return result


def demo_realistic_matrix() -> None:
    heading("Repository Permission Matrix")

    combinations = build_permission_matrix()

    print(
        "The raw candidate space contains "
        "3 × 2 × 2 × 3 = 36 combinations."
    )
    print(f"Policy-compliant combinations: {len(combinations)}")
    print()

    for combination in combinations:
        print(
            f"{combination.role:<16} "
            f"{combination.repository:<18} "
            f"{combination.environment:<12} "
            f"{combination.permission}"
        )


def demo_lazy_generation() -> None:
    heading("Lazy Cartesian-Product Generation")

    left = range(1, 1_000_000)
    right = ["small", "medium", "large"]

    stream = cross_join_stream(left, right)

    print("The theoretical result contains:")
    print(f"{1_000_000:,} × {len(right)} = {1_000_000 * len(right):,} rows")
    print()
    print("Only the first five rows are consumed:")

    for index, row in zip(range(5), stream):
        print(f"{index + 1}: {row}")

    print(
        "\nA generator avoids storing the complete Cartesian product, "
        "which is important when the product is too large to fit comfortably "
        "in memory."
    )


def demo_chunked_generation(
    left: Sequence[T],
    right: Sequence[U],
    chunk_size: int = 100,
) -> Iterator[list[tuple[T, U]]]:
    """
    Yield Cartesian-product rows in bounded chunks.

    This pattern is useful when generated combinations must be sent to an
    external system or processed in batches.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    chunk: list[tuple[T, U]] = []

    for row in cross_join_stream(left, right):
        chunk.append(row)

        if len(chunk) == chunk_size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


def demo_chunking() -> None:
    heading("Chunked Cartesian Processing")

    users = [f"user-{number}" for number in range(1, 6)]
    services = ["api", "web", "worker", "scheduler"]

    total = expected_cartesian_size(users, services)
    print(f"Total combinations: {total}")

    for number, chunk in enumerate(
        demo_chunked_generation(users, services, chunk_size=6),
        start=1,
    ):
        print(f"Chunk {number}: {len(chunk)} rows -> {chunk}")


def demo_risk_detection() -> None:
    heading("Detecting Cartesian-Product Risk Before Execution")

    scenarios = {
        "small matrix": [
            list(range(10)),
            list(range(20)),
            list(range(5)),
        ],
        "large matrix": [
            list(range(1_000)),
            list(range(1_000)),
            list(range(100)),
        ],
    }

    for name, groups in scenarios.items():
        try:
            rows = safe_expected_size(groups, maximum_rows=5_000_000)
            print(f"{name}: {rows:,} rows")
        except ValueError as exc:
            print(f"{name}: REJECTED -> {exc}")


def demonstrate_common_mistake() -> None:
    heading("Common Mistake: Materializing Too Early")

    values_a = range(100)
    values_b = range(100)

    expected = expected_cartesian_size(values_a, values_b)

    print(
        f"A 100 × 100 Cartesian product contains {expected:,} rows."
    )
    print(
        "For small datasets, list(product(...)) is convenient. "
        "For large datasets, streaming or batching is safer."
    )

    preview = list(product(values_a, values_b))[:5]
    print(f"Preview: {preview}")


def run_validation_tests() -> None:
    heading("Executable Validation Checks")

    assert cross_join([1, 2], ["a", "b"]) == [
        (1, "a"),
        (1, "b"),
        (2, "a"),
        (2, "b"),
    ]

    assert expected_cartesian_size([1, 2], ["a", "b"], [True, False]) == 8
    assert expected_cartesian_size([], [1, 2, 3]) == 0
    assert cross_join_many([]) == [()]

    try:
        safe_expected_size([[1, 2, 3], [4, 5]], maximum_rows=4)
    except ValueError:
        pass
    else:
        raise AssertionError("Oversized Cartesian product was not rejected")

    try:
        safe_expected_size([[1]], maximum_rows=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("Negative limit was not rejected")

    print("All validation checks passed.")


def main() -> None:
    heading("CROSS JOIN Technical Demonstration")

    demo_two_table_cartesian_product()
    demo_many_input_product()
    demo_duplicates()
    demo_empty_inputs()
    demo_filter_after_cross_join()
    demo_realistic_matrix()
    demo_lazy_generation()
    demo_chunking()
    demo_risk_detection()
    demonstrate_common_mistake()
    run_validation_tests()

    heading("Key Operational Rule")
    print(
        "A CROSS JOIN intentionally creates every possible pair or tuple "
        "between its input rows. Before materializing the result, estimate "
        "the Cartesian cardinality and apply appropriate limits, filters, "
        "or streaming strategies."
    )


if __name__ == "__main__":
    main()
