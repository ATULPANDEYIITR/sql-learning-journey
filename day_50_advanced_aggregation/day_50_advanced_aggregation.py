from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Iterable


@dataclass(frozen=True)
class PullRequest:
    number: int
    repository: str
    author: str
    target_branch: str
    status: str
    additions: int
    deletions: int
    commits: int
    reviews: int
    approvals: int
    requested_changes: int
    merged: bool
    merge_strategy: str
    opened_at: datetime
    merged_at: datetime | None
    checks_passed: bool


PULL_REQUESTS = [
    PullRequest(101, "payments-api", "alice", "main", "merged", 420, 80, 6, 3, 2, 0,
                True, "squash", datetime(2026, 10, 1, 9), datetime(2026, 10, 2, 14), True),
    PullRequest(102, "payments-api", "bob", "main", "merged", 90, 20, 3, 2, 1, 0,
                True, "merge", datetime(2026, 10, 2, 10), datetime(2026, 10, 2, 17), True),
    PullRequest(103, "payments-api", "carol", "release", "closed", 700, 300, 12, 4, 0, 2,
                False, "none", datetime(2026, 10, 3, 8), None, False),
    PullRequest(104, "web-portal", "alice", "main", "merged", 130, 45, 4, 3, 2, 0,
                True, "rebase", datetime(2026, 10, 4, 11), datetime(2026, 10, 5, 10), True),
    PullRequest(105, "web-portal", "david", "main", "open", 35, 8, 2, 1, 0, 0,
                False, "none", datetime(2026, 10, 6, 13), None, True),
    PullRequest(106, "web-portal", "carol", "develop", "merged", 250, 120, 7, 4, 3, 0,
                True, "squash", datetime(2026, 10, 7, 9), datetime(2026, 10, 8, 15), True),
]


def aggregate(values: Iterable[int]) -> dict[str, float]:
    values = list(values)
    if not values:
        return {"count": 0, "sum": 0, "average": 0, "minimum": 0, "maximum": 0}
    return {
        "count": len(values),
        "sum": sum(values),
        "average": mean(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def group_by_repository(prs: Iterable[PullRequest]) -> dict[str, list[PullRequest]]:
    grouped: dict[str, list[PullRequest]] = defaultdict(list)
    for pr in prs:
        grouped[pr.repository].append(pr)
    return dict(grouped)


def repository_metrics(prs: Iterable[PullRequest]) -> dict[str, dict[str, object]]:
    result = {}

    for repository, items in group_by_repository(prs).items():
        additions = [pr.additions for pr in items]
        deletions = [pr.deletions for pr in items]
        cycle_hours = [
            (pr.merged_at - pr.opened_at).total_seconds() / 3600
            for pr in items
            if pr.merged_at is not None
        ]

        # Conditional aggregation counts only records satisfying a predicate.
        merged_count = sum(pr.merged for pr in items)
        passed_check_count = sum(pr.checks_passed for pr in items)
        large_pr_count = sum((pr.additions + pr.deletions) > 500 for pr in items)

        result[repository] = {
            "pull_requests": len(items),
            "merged": merged_count,
            "merge_rate": merged_count / len(items),
            "changes": aggregate([a + d for a, d in zip(additions, deletions)]),
            "reviews": aggregate(pr.reviews for pr in items),
            "approvals": aggregate(pr.approvals for pr in items),
            "cycle_hours": aggregate(cycle_hours),
            "checks_passed": passed_check_count,
            "large_prs": large_pr_count,
        }

    return result


def author_metrics(prs: Iterable[PullRequest]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[PullRequest]] = defaultdict(list)

    for pr in prs:
        grouped[pr.author].append(pr)

    output = {}
    for author, items in grouped.items():
        output[author] = {
            "prs": len(items),
            "merged": sum(pr.merged for pr in items),
            "total_changes": sum(pr.additions + pr.deletions for pr in items),
            "approval_average": mean(pr.approvals for pr in items),
            "review_average": mean(pr.reviews for pr in items),
            "failed_checks": sum(not pr.checks_passed for pr in items),
        }

    return output


def merge_strategy_distribution(prs: Iterable[PullRequest]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)

    for pr in prs:
        if pr.merged:
            counts[pr.merge_strategy] += 1

    return dict(sorted(counts.items()))


def conditional_aggregation(prs: Iterable[PullRequest]) -> dict[str, int]:
    return {
        "merged_with_two_or_more_approvals": sum(
            pr.merged and pr.approvals >= 2 for pr in prs
        ),
        "open_prs_with_passing_checks": sum(
            pr.status == "open" and pr.checks_passed for pr in prs
        ),
        "prs_requiring_changes": sum(pr.requested_changes > 0 for pr in prs),
        "large_merged_prs": sum(
            pr.merged and pr.additions + pr.deletions >= 500 for pr in prs
        ),
    }


def weighted_average_cycle_time(prs: Iterable[PullRequest]) -> float:
    # Weighted by PR count naturally through the numerator/denominator.
    durations = [
        (pr.merged_at - pr.opened_at).total_seconds() / 3600
        for pr in prs
        if pr.merged_at is not None
    ]
    return sum(durations) / len(durations) if durations else 0.0


def print_report(prs: list[PullRequest]) -> None:
    print("=== Advanced Aggregation: Repository Governance ===")

    print("\nRepository metrics")
    for repository, metrics in repository_metrics(prs).items():
        print(f"\n{repository}")
        print(f"  PRs: {metrics['pull_requests']}")
        print(f"  Merged: {metrics['merged']}")
        print(f"  Merge rate: {metrics['merge_rate']:.1%}")
        print(f"  Total changes: {metrics['changes']['sum']}")
        print(f"  Average reviews: {metrics['reviews']['average']:.2f}")
        print(f"  Average approvals: {metrics['approvals']['average']:.2f}")
        print(f"  Average cycle time: {metrics['cycle_hours']['average']:.2f} hours")
        print(f"  Large PRs: {metrics['large_prs']}")

    print("\nAuthor metrics")
    for author, metrics in author_metrics(prs).items():
        print(f"{author}: {metrics}")

    print("\nConditional aggregation")
    for key, value in conditional_aggregation(prs).items():
        print(f"{key}: {value}")

    print("\nMerged strategy distribution")
    for strategy, count in merge_strategy_distribution(prs).items():
        print(f"{strategy}: {count}")

    print(f"\nWeighted average merge cycle: {weighted_average_cycle_time(prs):.2f} hours")


def validate_data(prs: list[PullRequest]) -> None:
    seen = set()

    for pr in prs:
        if pr.number in seen:
            raise ValueError(f"Duplicate Pull Request number: {pr.number}")
        seen.add(pr.number)

        if min(pr.additions, pr.deletions, pr.commits, pr.reviews, pr.approvals) < 0:
            raise ValueError(f"Negative metric in PR #{pr.number}")

        if pr.merged and pr.merged_at is None:
            raise ValueError(f"Merged PR #{pr.number} has no merge timestamp")

        if pr.merged and not pr.checks_passed:
            raise ValueError(f"PR #{pr.number} violates merge-check integrity")

        if pr.status not in {"open", "merged", "closed"}:
            raise ValueError(f"Invalid state for PR #{pr.number}: {pr.status}")


if __name__ == "__main__":
    validate_data(PULL_REQUESTS)
    print_report(PULL_REQUESTS)
