#!/usr/bin/env python3
"""
INNER JOIN — Join fundamentals, matching rows, and join conditions.

This self-contained program teaches INNER JOIN behavior by building a small
relational dataset in memory and executing join operations without requiring
an external database package.

The examples model realistic repository-development data:
repositories, pull requests, and authors. The central operation is the
relational INNER JOIN: only rows for which the join condition evaluates to
true appear in the result.

The script progresses from:
- understanding matching keys,
- implementing a basic equality INNER JOIN,
- handling duplicate keys,
- using composite join conditions,
- applying additional filters,
- joining more than two relations,
- identifying unmatched rows by comparison,
- and validating join behavior with executable tests.

Run:
    python inner_join.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence


Row = dict[str, Any]
JoinCondition = Callable[[Row, Row], bool]


def print_title(title: str) -> None:
    """Print a readable heading without changing the data being demonstrated."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def print_rows(rows: Sequence[Row], columns: Sequence[str] | None = None) -> None:
    """Display relational rows in a compact table."""
    if not rows:
        print("(no rows)")
        return

    if columns is None:
        columns = list(rows[0].keys())

    widths = {
        column: max(
            len(column),
            *(len(str(row.get(column, ""))) for row in rows),
        )
        for column in columns
    }

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)

    print(header)
    print(separator)

    for row in rows:
        print(" | ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))


def validate_rows(rows: Iterable[Row], required_columns: set[str]) -> list[Row]:
    """
    Validate a relation before it participates in a join.

    An INNER JOIN can technically operate on arbitrary dictionaries, but
    explicit validation makes missing join columns a visible data-quality
    problem instead of silently producing incorrect matches.
    """
    materialized = list(rows)

    for index, row in enumerate(materialized):
        missing = required_columns - row.keys()
        if missing:
            raise ValueError(
                f"Row {index} is missing required columns: {sorted(missing)}"
            )

    return materialized


def inner_join(
    left_rows: Iterable[Row],
    right_rows: Iterable[Row],
    condition: JoinCondition,
    *,
    left_prefix: str = "left",
    right_prefix: str = "right",
) -> list[Row]:
    """
    Execute a general INNER JOIN using a nested-loop strategy.

    For every left row, every right row is tested against the join condition.
    A result is emitted only when the condition returns True.

    Prefixing protects against ambiguous column names. In a real SQL query,
    aliases such as pr.id and repo.id serve a similar disambiguation purpose.

    Complexity:
        O(L * R) comparisons for L left rows and R right rows.

    This implementation intentionally uses the general condition form before
    introducing an indexed equality join, because it makes the definition of
    INNER JOIN explicit.
    """
    left = list(left_rows)
    right = list(right_rows)

    output: list[Row] = []

    for left_row in left:
        for right_row in right:
            if condition(left_row, right_row):
                combined: Row = {}

                for key, value in left_row.items():
                    combined[f"{left_prefix}.{key}"] = value

                for key, value in right_row.items():
                    combined[f"{right_prefix}.{key}"] = value

                output.append(combined)

    return output


def equality_inner_join(
    left_rows: Iterable[Row],
    right_rows: Iterable[Row],
    left_key: str,
    right_key: str,
) -> list[Row]:
    """
    Perform an equality INNER JOIN using a hash index.

    The right relation is indexed by its join key. For each left row, only
    matching right rows are visited.

    This changes the typical equality-join lookup cost from repeatedly
    scanning the complete right relation to approximately O(L + R), excluding
    output construction and hash-table behavior.

    Duplicate keys are important: if three right rows have the same key and
    two left rows have that key, six result rows are produced. This is the
    relational consequence of matching every compatible row.
    """
    left = validate_rows(left_rows, {left_key})
    right = validate_rows(right_rows, {right_key})

    index: dict[Any, list[Row]] = {}

    for row in right:
        index.setdefault(row[right_key], []).append(row)

    output: list[Row] = []

    for left_row in left:
        matching_rows = index.get(left_row[left_key], [])

        for right_row in matching_rows:
            combined: Row = {}

            for key, value in left_row.items():
                combined[f"left.{key}"] = value

            for key, value in right_row.items():
                combined[f"right.{key}"] = value

            output.append(combined)

    return output


def select_columns(
    rows: Iterable[Row],
    mappings: dict[str, str],
) -> list[Row]:
    """
    Project selected columns after a join.

    mappings maps output column names to existing qualified input names.
    """
    result: list[Row] = []

    for row in rows:
        result.append(
            {
                output_name: row[source_name]
                for output_name, source_name in mappings.items()
            }
        )

    return result


def filter_rows(rows: Iterable[Row], predicate: Callable[[Row], bool]) -> list[Row]:
    """Apply a relational selection after the join."""
    return [row for row in rows if predicate(row)]


def distinct_rows(rows: Iterable[Row]) -> list[Row]:
    """
    Remove exact duplicate rows while preserving first-seen order.

    DISTINCT is not part of INNER JOIN itself. It is an additional relational
    operation and is shown separately so duplicate join results are not
    incorrectly attributed to the join.
    """
    result: list[Row] = []
    seen: set[tuple[tuple[str, Any], ...]] = set()

    for row in rows:
        try:
            signature = tuple(sorted(row.items()))
            hash(signature)
        except TypeError as exc:
            raise TypeError(
                "distinct_rows requires hashable column values"
            ) from exc

        if signature not in seen:
            seen.add(signature)
            result.append(row)

    return result


@dataclass(frozen=True)
class Repository:
    repository_id: int
    name: str
    owner: str


@dataclass(frozen=True)
class PullRequest:
    pull_request_id: int
    repository_id: int
    title: str
    author_id: int
    state: str


@dataclass(frozen=True)
class Developer:
    developer_id: int
    username: str
    team: str


def dataclass_records(objects: Iterable[Any]) -> list[Row]:
    """Convert domain objects into simple relational rows."""
    return [vars(obj).copy() for obj in objects]


def demonstrate_basic_matching() -> None:
    print_title("INNER JOIN fundamentals: only matching keys survive")

    repositories = [
        {"repository_id": 101, "name": "market-prism", "owner": "atul"},
        {"repository_id": 102, "name": "asset-logistics", "owner": "atul"},
        {"repository_id": 103, "name": "research-tracker", "owner": "atul"},
    ]

    pull_requests = [
        {
            "pull_request_id": 501,
            "repository_id": 101,
            "title": "Add risk dashboard",
            "author_id": 11,
            "state": "open",
        },
        {
            "pull_request_id": 502,
            "repository_id": 101,
            "title": "Fix portfolio validation",
            "author_id": 12,
            "state": "merged",
        },
        {
            "pull_request_id": 503,
            "repository_id": 999,
            "title": "Unknown repository change",
            "author_id": 13,
            "state": "open",
        },
    ]

    result = equality_inner_join(
        repositories,
        pull_requests,
        "repository_id",
        "repository_id",
    )

    selected = select_columns(
        result,
        {
            "repository": "left.name",
            "pull_request": "right.pull_request_id",
            "title": "right.title",
            "state": "right.state",
        },
    )

    print_rows(selected)

    print(
        "\nThe repository with ID 102 and 103 disappear because no pull request "
        "contains those IDs. Pull request 503 disappears because repository 999 "
        "has no matching repository row."
    )


def demonstrate_duplicate_keys() -> None:
    print_title("Matching is pairwise: duplicate keys create multiple result rows")

    teams = [
        {"team_id": 1, "team_name": "Platform"},
        {"team_id": 2, "team_name": "Security"},
    ]

    developers = [
        {"developer_id": 10, "username": "alice", "team_id": 1},
        {"developer_id": 11, "username": "bob", "team_id": 1},
        {"developer_id": 12, "username": "carol", "team_id": 2},
        {"developer_id": 13, "username": "dave", "team_id": 1},
    ]

    result = equality_inner_join(
        teams,
        developers,
        "team_id",
        "team_id",
    )

    print_rows(
        select_columns(
            result,
            {
                "team": "left.team_name",
                "developer": "right.username",
            },
        )
    )

    print(
        "\nTeam 1 has three matching developers, so the team row participates "
        "in three output combinations. INNER JOIN does not assume one-to-one "
        "relationships."
    )


def demonstrate_custom_join_condition() -> None:
    print_title("Join conditions can contain more than simple equality")

    repositories = [
        {"repository_id": 201, "name": "payments-api", "owner": "finance"},
        {"repository_id": 202, "name": "identity-api", "owner": "security"},
    ]

    pull_requests = [
        {
            "pull_request_id": 601,
            "repository_id": 201,
            "target_environment": "production",
        },
        {
            "pull_request_id": 602,
            "repository_id": 201,
            "target_environment": "staging",
        },
        {
            "pull_request_id": 603,
            "repository_id": 202,
            "target_environment": "production",
        },
    ]

    result = inner_join(
        repositories,
        pull_requests,
        lambda repo, pr: (
            repo["repository_id"] == pr["repository_id"]
            and pr["target_environment"] == "production"
        ),
    )

    print_rows(
        select_columns(
            result,
            {
                "repository": "left.name",
                "pull_request": "right.pull_request_id",
                "environment": "right.target_environment",
            },
        )
    )

    print(
        "\nThe repository ID is the relationship key, while the environment "
        "predicate restricts which matching combinations are retained."
    )


def demonstrate_composite_condition() -> None:
    print_title("Composite join conditions: matching more than one attribute")

    branch_policies = [
        {"repository_id": 301, "branch_name": "main", "required_reviews": 2},
        {"repository_id": 301, "branch_name": "develop", "required_reviews": 1},
        {"repository_id": 302, "branch_name": "main", "required_reviews": 1},
    ]

    pull_requests = [
        {"pull_request_id": 701, "repository_id": 301, "base_branch": "main"},
        {"pull_request_id": 702, "repository_id": 301, "base_branch": "develop"},
        {"pull_request_id": 703, "repository_id": 302, "base_branch": "main"},
        {"pull_request_id": 704, "repository_id": 301, "base_branch": "release"},
    ]

    result = inner_join(
        branch_policies,
        pull_requests,
        lambda policy, pr: (
            policy["repository_id"] == pr["repository_id"]
            and policy["branch_name"] == pr["base_branch"]
        ),
    )

    print_rows(
        select_columns(
            result,
            {
                "pull_request": "right.pull_request_id",
                "repository": "left.repository_id",
                "branch": "left.branch_name",
                "required_reviews": "left.required_reviews",
            },
        )
    )

    print(
        "\nBoth repository_id and branch name must match. PR 704 has a valid "
        "repository ID but no matching branch-policy row."
    )


def demonstrate_post_join_filter() -> None:
    print_title("Join condition versus filtering after the join")

    repositories = [
        {"repository_id": 401, "name": "analytics", "owner": "atul"},
        {"repository_id": 402, "name": "billing", "owner": "atul"},
    ]

    pull_requests = [
        {"pull_request_id": 801, "repository_id": 401, "state": "open"},
        {"pull_request_id": 802, "repository_id": 401, "state": "merged"},
        {"pull_request_id": 803, "repository_id": 402, "state": "open"},
    ]

    joined = equality_inner_join(
        repositories,
        pull_requests,
        "repository_id",
        "repository_id",
    )

    open_only = filter_rows(
        joined,
        lambda row: row["right.state"] == "open",
    )

    print("All matching repository/PR pairs:")
    print_rows(joined)

    print("\nAfter filtering to open PRs:")
    print_rows(open_only)

    print(
        "\nThe INNER JOIN establishes which repository and pull-request rows "
        "are related. The later filter decides which joined results are kept "
        "based on PR state."
    )


def demonstrate_three_table_join() -> None:
    print_title("Joining three relations: repository -> pull request -> developer")

    repositories = [
        {"repository_id": 501, "name": "market-engine"},
        {"repository_id": 502, "name": "security-engine"},
    ]

    pull_requests = [
        {
            "pull_request_id": 901,
            "repository_id": 501,
            "author_id": 1001,
            "title": "Improve risk calculation",
        },
        {
            "pull_request_id": 902,
            "repository_id": 502,
            "author_id": 1002,
            "title": "Rotate security policy",
        },
        {
            "pull_request_id": 903,
            "repository_id": 501,
            "author_id": 9999,
            "title": "Unknown author",
        },
    ]

    developers = [
        {"developer_id": 1001, "username": "maya", "team": "quant"},
        {"developer_id": 1002, "username": "rohan", "team": "security"},
    ]

    repository_prs = equality_inner_join(
        repositories,
        pull_requests,
        "repository_id",
        "repository_id",
    )

    full_join = inner_join(
        repository_prs,
        developers,
        lambda row, developer: (
            row["right.author_id"] == developer["developer_id"]
        ),
        left_prefix="repo_pr",
        right_prefix="developer",
    )

    print_rows(
        select_columns(
            full_join,
            {
                "repository": "repo_pr.left.name",
                "pull_request": "repo_pr.right.pull_request_id",
                "author": "developer.username",
                "team": "developer.team",
            },
        )
    )

    print(
        "\nPR 903 disappears at the second join because its author has no "
        "matching developer record. Each INNER JOIN can therefore reduce the "
        "result set further."
    )


def demonstrate_missing_data_and_null_like_values() -> None:
    print_title("Missing values: equality does not automatically match absent values")

    left = [
        {"record_id": 1, "external_key": "A100"},
        {"record_id": 2, "external_key": None},
    ]

    right = [
        {"source_id": 10, "external_key": "A100"},
        {"source_id": 11, "external_key": None},
    ]

    result = equality_inner_join(left, right, "external_key", "external_key")

    print_rows(result)

    print(
        "\nThis Python equality implementation treats None == None as true. "
        "SQL is different: NULL represents an unknown value, and NULL = NULL "
        "does not evaluate to TRUE. A SQL INNER JOIN normally requires explicit "
        "NULL-safe logic when two NULL values should be considered equivalent."
    )


def demonstrate_sql_semantics() -> None:
    print_title("Equivalent SQL reasoning")

    print(
        """
SELECT
    r.name,
    pr.pull_request_id,
    pr.title
FROM repositories AS r
INNER JOIN pull_requests AS pr
    ON r.repository_id = pr.repository_id
WHERE pr.state = 'open';

The ON expression defines which rows are related.
The WHERE expression filters the rows produced by that relationship.

For an INNER JOIN, unmatched rows from either input relation are absent from
the final result. This differs from OUTER JOIN behavior, where unmatched rows
can be preserved.
""".strip()
    )


def run_assertions() -> None:
    print_title("Executable correctness checks")

    repositories = [
        {"repository_id": 1, "name": "alpha"},
        {"repository_id": 2, "name": "beta"},
    ]

    pull_requests = [
        {"pull_request_id": 10, "repository_id": 1},
        {"pull_request_id": 11, "repository_id": 1},
        {"pull_request_id": 12, "repository_id": 3},
    ]

    result = equality_inner_join(
        repositories,
        pull_requests,
        "repository_id",
        "repository_id",
    )

    assert len(result) == 2
    assert {
        row["right.pull_request_id"] for row in result
    } == {10, 11}
    assert all(row["left.repository_id"] == row["right.repository_id"] for row in result)

    duplicate_left = [{"key": "X", "value": "left"}]
    duplicate_right = [
        {"key": "X", "value": "right-a"},
        {"key": "X", "value": "right-b"},
    ]

    duplicate_result = equality_inner_join(
        duplicate_left,
        duplicate_right,
        "key",
        "key",
    )

    assert len(duplicate_result) == 2

    try:
        equality_inner_join(
            [{"id": 1}],
            [{"name": "missing-id"}],
            "id",
            "id",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Missing join keys must raise ValueError")

    assert distinct_rows(
        [
            {"id": 1, "name": "same"},
            {"id": 1, "name": "same"},
        ]
    ) == [{"id": 1, "name": "same"}]

    print("All INNER JOIN assertions passed.")


def performance_note() -> None:
    print_title("Performance and design considerations")

    print(
        """
Nested-loop joins are useful for teaching the mechanics because every
candidate pair is visible. Their worst-case comparison count is L × R.

Equality joins can usually be accelerated with an index or hash structure.
The equality_inner_join implementation builds a hash index on the right-side
key, then performs constant-average-time lookups for left-side keys.

Database query optimizers can choose among nested-loop, hash-join, merge-join,
and indexed access strategies based on statistics, indexes, ordering, data
distribution, memory, and estimated result size.

A join key should have compatible semantics on both sides. Joining a repository
ID to an unrelated textual field is syntactically possible in some systems
after implicit conversion, but it is a data-modeling error.

Many-to-many relationships can multiply rows dramatically. Before joining,
inspect the cardinality of both sides and confirm whether duplicates represent
real business relationships.

Indexes can improve equality joins but consume storage and create write
maintenance costs. An index on a frequently joined foreign-key column is
often useful, but actual query plans should be measured rather than assumed.
""".strip()
    )


def main() -> None:
    demonstrate_basic_matching()
    demonstrate_duplicate_keys()
    demonstrate_custom_join_condition()
    demonstrate_composite_condition()
    demonstrate_post_join_filter()
    demonstrate_three_table_join()
    demonstrate_missing_data_and_null_like_values()
    demonstrate_sql_semantics()
    run_assertions()
    performance_note()


if __name__ == "__main__":
    main()
