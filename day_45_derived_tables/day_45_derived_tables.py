"""
Derived Tables: Subqueries in FROM and Intermediate Result Sets

A self-contained learning and demonstration program that models derived-table
thinking with Python data-processing pipelines. The examples mirror the
relational idea of producing an intermediate result set and then querying,
filtering, aggregating, or joining that result as a new logical relation.

The domain is repository governance because derived tables are particularly
useful when analyzing Pull Requests, review activity, approvals, status checks,
and protected-branch policies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Callable, Iterable, Sequence


@dataclass(frozen=True)
class PullRequest:
    pr_id: int
    repository: str
    source_branch: str
    target_branch: str
    author: str
    additions: int
    deletions: int
    state: str
    merged: bool
    created_at: datetime


@dataclass(frozen=True)
class Review:
    review_id: int
    pr_id: int
    reviewer: str
    state: str
    submitted_at: datetime


@dataclass(frozen=True)
class StatusCheck:
    check_id: int
    pr_id: int
    name: str
    state: str
    completed_at: datetime


@dataclass(frozen=True)
class BranchPolicy:
    repository: str
    branch: str
    required_approvals: int
    required_checks: tuple[str, ...]
    require_linear_history: bool


def derived_table(
    rows: Iterable[object],
    projection: Callable[[object], dict],
) -> list[dict]:
    """
    Generic derived-table operation.

    In SQL, a subquery in FROM produces a temporary logical result set.
    This function performs the analogous transformation by projecting source
    records into a new collection of rows.
    """
    return [projection(row) for row in rows]


def where(
    rows: Iterable[dict],
    predicate: Callable[[dict], bool],
) -> list[dict]:
    """Filter an intermediate result set."""
    return [row for row in rows if predicate(row)]


def group_count(rows: Iterable[dict], key: str) -> list[dict]:
    """Create an aggregated intermediate result set."""
    counts: dict[object, int] = {}
    for row in rows:
        value = row[key]
        counts[value] = counts.get(value, 0) + 1

    return [
        {key: group_value, "row_count": count}
        for group_value, count in counts.items()
    ]


def sort_rows(
    rows: Iterable[dict],
    key: str,
    reverse: bool = False,
) -> list[dict]:
    """Order a derived result without modifying its input."""
    return sorted(rows, key=lambda row: row[key], reverse=reverse)


def inner_join(
    left_rows: Iterable[dict],
    right_rows: Iterable[dict],
    left_key: str,
    right_key: str,
) -> list[dict]:
    """
    Join two intermediate result sets.

    A dictionary index is used for the right side so the demonstration also
    exposes why materialized intermediate results can be useful.
    """
    right_index: dict[object, list[dict]] = {}

    for row in right_rows:
        right_index.setdefault(row[right_key], []).append(row)

    joined: list[dict] = []

    for left in left_rows:
        matches = right_index.get(left[left_key], [])
        for right in matches:
            combined = dict(left)
            for key, value in right.items():
                if key in combined:
                    combined[f"right_{key}"] = value
                else:
                    combined[key] = value
            joined.append(combined)

    return joined


def demonstrate_basic_derived_table(prs: Sequence[PullRequest]) -> None:
    print("\n=== Basic derived table ===")

    change_metrics = derived_table(
        prs,
        lambda pr: {
            "pr_id": pr.pr_id,
            "repository": pr.repository,
            "author": pr.author,
            "target_branch": pr.target_branch,
            "change_size": pr.additions + pr.deletions,
        },
    )

    large_changes = where(
        change_metrics,
        lambda row: row["change_size"] >= 200,
    )

    for row in large_changes:
        print(row)


def demonstrate_derived_table_filtering(prs: Sequence[PullRequest]) -> None:
    print("\n=== Filter an intermediate result ===")

    open_prs = derived_table(
        prs,
        lambda pr: {
            "pr_id": pr.pr_id,
            "repository": pr.repository,
            "target_branch": pr.target_branch,
            "state": pr.state,
            "merged": pr.merged,
        },
    )

    protected_branch_candidates = where(
        open_prs,
        lambda row: (
            row["state"] == "OPEN"
            and row["target_branch"] in {"main", "release"}
        ),
    )

    for row in protected_branch_candidates:
        print(row)


def demonstrate_nested_derived_tables(prs: Sequence[PullRequest]) -> None:
    print("\n=== Nested intermediate result sets ===")

    first_layer = derived_table(
        prs,
        lambda pr: {
            "pr_id": pr.pr_id,
            "repository": pr.repository,
            "change_size": pr.additions + pr.deletions,
        },
    )

    second_layer = where(
        first_layer,
        lambda row: row["change_size"] > 100,
    )

    third_layer = derived_table(
        second_layer,
        lambda row: {
            "repository": row["repository"],
            "large_change": row["change_size"] > 500,
        },
    )

    repository_counts = group_count(third_layer, "repository")

    for row in repository_counts:
        print(row)


def demonstrate_aggregation_over_derived_table(
    prs: Sequence[PullRequest],
) -> None:
    print("\n=== Aggregation over a derived result ===")

    metrics = derived_table(
        prs,
        lambda pr: {
            "repository": pr.repository,
            "pr_id": pr.pr_id,
            "change_size": pr.additions + pr.deletions,
        },
    )

    repository_groups: dict[str, list[int]] = {}

    for row in metrics:
        repository_groups.setdefault(row["repository"], []).append(
            row["change_size"]
        )

    result = [
        {
            "repository": repository,
            "average_change_size": round(mean(sizes), 2),
            "largest_change": max(sizes),
        }
        for repository, sizes in repository_groups.items()
    ]

    for row in sort_rows(result, "average_change_size", reverse=True):
        print(row)


def demonstrate_joined_intermediate_results(
    prs: Sequence[PullRequest],
    reviews: Sequence[Review],
) -> None:
    print("\n=== Join derived review statistics to Pull Requests ===")

    review_projection = derived_table(
        reviews,
        lambda review: {
            "pr_id": review.pr_id,
            "reviewer": review.reviewer,
            "review_state": review.state,
        },
    )

    approval_counts: dict[int, int] = {}

    for row in review_projection:
        if row["review_state"] == "APPROVED":
            approval_counts[row["pr_id"]] = (
                approval_counts.get(row["pr_id"], 0) + 1
            )

    approval_summary = [
        {
            "pr_id": pr_id,
            "approval_count": count,
        }
        for pr_id, count in approval_counts.items()
    ]

    pr_projection = derived_table(
        prs,
        lambda pr: {
            "pr_id": pr.pr_id,
            "repository": pr.repository,
            "target_branch": pr.target_branch,
        },
    )

    result = inner_join(
        pr_projection,
        approval_summary,
        "pr_id",
        "pr_id",
    )

    for row in result:
        print(row)


def demonstrate_correlated_style_logic(
    prs: Sequence[PullRequest],
    reviews: Sequence[Review],
) -> None:
    print("\n=== Per-row intermediate evaluation ===")

    for pr in prs:
        pr_reviews = [
            review
            for review in reviews
            if review.pr_id == pr.pr_id
        ]

        approval_rows = derived_table(
            pr_reviews,
            lambda review: {
                "reviewer": review.reviewer,
                "approved": review.state == "APPROVED",
            },
        )

        approval_count = sum(
            row["approved"] for row in approval_rows
        )

        if approval_count >= 2:
            print(
                {
                    "pr_id": pr.pr_id,
                    "repository": pr.repository,
                    "approval_count": approval_count,
                }
            )


def evaluate_merge_eligibility(
    prs: Sequence[PullRequest],
    reviews: Sequence[Review],
    checks: Sequence[StatusCheck],
    policies: Sequence[BranchPolicy],
) -> list[dict]:
    """
    Build several intermediate relations before producing final eligibility.

    This mirrors a multi-level SQL design where each FROM-subquery isolates
    one logical calculation before another query consumes it.
    """

    pr_relation = derived_table(
        prs,
        lambda pr: {
            "pr_id": pr.pr_id,
            "repository": pr.repository,
            "target_branch": pr.target_branch,
            "state": pr.state,
            "merged": pr.merged,
        },
    )

    approval_relation = derived_table(
        reviews,
        lambda review: {
            "pr_id": review.pr_id,
            "reviewer": review.reviewer,
            "approved": review.state == "APPROVED",
        },
    )

    approval_counts: dict[int, set[str]] = {}

    for row in approval_relation:
        if row["approved"]:
            approval_counts.setdefault(row["pr_id"], set()).add(
                row["reviewer"]
            )

    approval_summary = [
        {
            "pr_id": pr_id,
            "approval_count": len(reviewers),
        }
        for pr_id, reviewers in approval_counts.items()
    ]

    check_relation = derived_table(
        checks,
        lambda check: {
            "pr_id": check.pr_id,
            "check_name": check.name,
            "passing": check.state == "SUCCESS",
        },
    )

    passing_checks: dict[int, set[str]] = {}

    for row in check_relation:
        if row["passing"]:
            passing_checks.setdefault(row["pr_id"], set()).add(
                row["check_name"]
            )

    policy_relation = derived_table(
        policies,
        lambda policy: {
            "repository": policy.repository,
            "branch": policy.branch,
            "required_approvals": policy.required_approvals,
            "required_checks": set(policy.required_checks),
        },
    )

    eligibility_base = inner_join(
        pr_relation,
        policy_relation,
        "target_branch",
        "branch",
    )

    # Repository must also match. The preceding join intentionally illustrates
    # why a join condition may need more than one key in a real relational
    # implementation.
    eligibility_base = [
        row
        for row in eligibility_base
        if row["repository"] == row["right_repository"]
    ]

    eligibility_with_approvals = inner_join(
        eligibility_base,
        approval_summary,
        "pr_id",
        "pr_id",
    )

    final_rows: list[dict] = []

    for row in eligibility_with_approvals:
        required_checks = row["required_checks"]
        actual_checks = passing_checks.get(row["pr_id"], set())

        approvals_ok = (
            row["approval_count"] >= row["required_approvals"]
        )
        checks_ok = required_checks.issubset(actual_checks)
        state_ok = row["state"] == "OPEN"
        merge_ok = approvals_ok and checks_ok and state_ok

        final_rows.append(
            {
                "pr_id": row["pr_id"],
                "repository": row["repository"],
                "target_branch": row["target_branch"],
                "approval_count": row["approval_count"],
                "required_approvals": row["required_approvals"],
                "passing_required_checks": sorted(
                    actual_checks.intersection(required_checks)
                ),
                "required_checks": sorted(required_checks),
                "merge_eligible": merge_ok,
            }
        )

    return final_rows


def demonstrate_reusable_pipeline(prs: Sequence[PullRequest]) -> None:
    print("\n=== Reusable derived-table pipeline ===")

    pipeline = derived_table(
        prs,
        lambda pr: {
            "pr_id": pr.pr_id,
            "repository": pr.repository,
            "author": pr.author,
            "target_branch": pr.target_branch,
            "net_change": pr.additions - pr.deletions,
            "total_change": pr.additions + pr.deletions,
        },
    )

    pipeline = where(
        pipeline,
        lambda row: row["target_branch"] == "main",
    )

    pipeline = where(
        pipeline,
        lambda row: row["total_change"] >= 100,
    )

    pipeline = sort_rows(
        pipeline,
        "total_change",
        reverse=True,
    )

    for row in pipeline:
        print(row)


def demonstrate_edge_cases() -> None:
    print("\n=== Edge cases ===")

    empty_result = derived_table([], lambda row: {"value": row})
    print("Empty derived result:", empty_result)

    rows_with_zero = [
        {"pr_id": 10, "change_size": 0},
        {"pr_id": 11, "change_size": 250},
    ]

    filtered = where(
        rows_with_zero,
        lambda row: row["change_size"] >= 0,
    )
    print("Zero-sized change retained:", filtered)

    missing_policy = []
    eligible = where(
        [{"pr_id": 99, "policy_found": False}],
        lambda row: row["policy_found"],
    )
    print("Missing policy produces no eligible rows:", eligible)
    print("Explicit empty policy relation:", missing_policy)


def build_sample_data() -> tuple[
    list[PullRequest],
    list[Review],
    list[StatusCheck],
    list[BranchPolicy],
]:
    base = datetime(2026, 10, 1, 9, 0)

    prs = [
        PullRequest(
            101,
            "payment-platform",
            "feature/checkout-validation",
            "main",
            "atul",
            340,
            90,
            "OPEN",
            False,
            base,
        ),
        PullRequest(
            102,
            "payment-platform",
            "fix/token-expiry",
            "main",
            "neha",
            80,
            25,
            "OPEN",
            False,
            base + timedelta(days=1),
        ),
        PullRequest(
            103,
            "payment-platform",
            "release/2026-10",
            "release",
            "rahul",
            510,
            180,
            "OPEN",
            False,
            base + timedelta(days=2),
        ),
        PullRequest(
            104,
            "identity-service",
            "feature/session-hardening",
            "main",
            "meera",
            210,
            60,
            "OPEN",
            False,
            base + timedelta(days=3),
        ),
        PullRequest(
            105,
            "identity-service",
            "fix/audit-event",
            "main",
            "vikas",
            35,
            15,
            "CLOSED",
            False,
            base + timedelta(days=4),
        ),
    ]

    reviews = [
        Review(1, 101, "neha", "APPROVED", base + timedelta(days=1)),
        Review(2, 101, "rahul", "APPROVED", base + timedelta(days=1)),
        Review(3, 102, "meera", "APPROVED", base + timedelta(days=2)),
        Review(4, 103, "neha", "APPROVED", base + timedelta(days=3)),
        Review(5, 103, "vikas", "CHANGES_REQUESTED", base + timedelta(days=3)),
        Review(6, 104, "rahul", "APPROVED", base + timedelta(days=4)),
        Review(7, 104, "neha", "COMMENTED", base + timedelta(days=4)),
    ]

    checks = [
        StatusCheck(1, 101, "unit-tests", "SUCCESS", base),
        StatusCheck(2, 101, "security-scan", "SUCCESS", base),
        StatusCheck(3, 102, "unit-tests", "SUCCESS", base),
        StatusCheck(4, 102, "security-scan", "FAILURE", base),
        StatusCheck(5, 103, "unit-tests", "SUCCESS", base),
        StatusCheck(6, 103, "security-scan", "SUCCESS", base),
        StatusCheck(7, 104, "unit-tests", "SUCCESS", base),
        StatusCheck(8, 104, "security-scan", "SUCCESS", base),
    ]

    policies = [
        BranchPolicy(
            "payment-platform",
            "main",
            2,
            ("unit-tests", "security-scan"),
            True,
        ),
        BranchPolicy(
            "payment-platform",
            "release",
            2,
            ("unit-tests", "security-scan"),
            True,
        ),
        BranchPolicy(
            "identity-service",
            "main",
            2,
            ("unit-tests", "security-scan"),
            False,
        ),
    ]

    return prs, reviews, checks, policies


def main() -> None:
    prs, reviews, checks, policies = build_sample_data()

    demonstrate_basic_derived_table(prs)
    demonstrate_derived_table_filtering(prs)
    demonstrate_nested_derived_tables(prs)
    demonstrate_aggregation_over_derived_table(prs)
    demonstrate_joined_intermediate_results(prs, reviews)
    demonstrate_correlated_style_logic(prs, reviews)
    demonstrate_reusable_pipeline(prs)
    demonstrate_edge_cases()

    print("\n=== Merge eligibility derived relation ===")
    eligibility = evaluate_merge_eligibility(
        prs,
        reviews,
        checks,
        policies,
    )

    for row in eligibility:
        print(row)


if __name__ == "__main__":
    main()
