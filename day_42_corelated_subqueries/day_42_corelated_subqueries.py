from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Iterable, Optional


# Correlated subqueries are queries whose inner operation depends on a value
# from the current row of the outer operation.
#
# SQL example:
#
# SELECT p.number
# FROM pull_requests AS p
# WHERE EXISTS (
#     SELECT 1
#     FROM reviews AS r
#     WHERE r.pull_request_id = p.id
#       AND r.state = 'APPROVED'
# );
#
# The important mechanism is r.pull_request_id = p.id.
# The inner query cannot be evaluated independently for the logical meaning
# expressed here because it needs the current outer pull-request row.


@dataclass(frozen=True)
class PullRequest:
    id: int
    number: int
    title: str
    author: str
    base_branch: str
    source_branch: str
    draft: bool = False
    merged: bool = False


@dataclass(frozen=True)
class Review:
    id: int
    pull_request_id: int
    reviewer: str
    state: str
    submitted_at: datetime


@dataclass(frozen=True)
class StatusCheck:
    id: int
    pull_request_id: int
    name: str
    state: str


@dataclass(frozen=True)
class BranchProtection:
    branch: str
    required_approvals: int
    required_checks: tuple[str, ...]
    require_conversation_resolution: bool = True
    allow_force_push: bool = False
    allow_deletion: bool = False
    require_linear_history: bool = False


@dataclass(frozen=True)
class Comment:
    id: int
    pull_request_id: int
    reviewer: str
    body: str
    resolved: bool


@dataclass
class Repository:
    name: str
    pull_requests: list[PullRequest] = field(default_factory=list)
    reviews: list[Review] = field(default_factory=list)
    checks: list[StatusCheck] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    protections: dict[str, BranchProtection] = field(default_factory=dict)


def correlated_exists(
    outer_rows: Iterable,
    inner_rows: Iterable,
    predicate: Callable[[object, object], bool],
) -> list:
    """
    Generic in-memory equivalent of a correlated EXISTS subquery.

    For every outer row, the inner collection is evaluated with the current
    outer row available to the predicate.
    """
    inner_rows = list(inner_rows)
    result = []

    for outer in outer_rows:
        if any(predicate(outer, inner) for inner in inner_rows):
            result.append(outer)

    return result


def correlated_count(
    outer_rows: Iterable,
    inner_rows: Iterable,
    predicate: Callable[[object, object], bool],
) -> dict[int, int]:
    """
    Equivalent to a correlated scalar aggregate such as:

        SELECT p.id,
               (
                   SELECT COUNT(*)
                   FROM reviews r
                   WHERE r.pull_request_id = p.id
               )
        FROM pull_requests p;
    """
    inner_rows = list(inner_rows)
    counts = {}

    for outer in outer_rows:
        counts[outer.id] = sum(
            1 for inner in inner_rows if predicate(outer, inner)
        )

    return counts


def correlated_max(
    outer_rows: Iterable,
    inner_rows: Iterable,
    key: Callable[[object], object],
    predicate: Callable[[object, object], bool],
) -> dict[int, Optional[object]]:
    """
    Equivalent to a correlated MAX subquery.

    A separate aggregate is evaluated in the context of every outer row.
    """
    inner_rows = list(inner_rows)
    result = {}

    for outer in outer_rows:
        matching = [inner for inner in inner_rows if predicate(outer, inner)]
        result[outer.id] = max((key(item) for item in matching), default=None)

    return result


def demonstrate_basic_correlated_exists(repo: Repository) -> None:
    print("\n=== Correlated EXISTS: pull requests with approvals ===")

    approved_prs = correlated_exists(
        repo.pull_requests,
        repo.reviews,
        lambda pr, review: (
            review.pull_request_id == pr.id
            and review.state == "APPROVED"
        ),
    )

    for pr in approved_prs:
        print(f"PR #{pr.number}: {pr.title}")


def demonstrate_correlated_not_exists(repo: Repository) -> None:
    print("\n=== Correlated NOT EXISTS: pull requests without unresolved comments ===")

    clean_prs = [
        pr
        for pr in repo.pull_requests
        if not any(
            comment.pull_request_id == pr.id and not comment.resolved
            for comment in repo.comments
        )
    ]

    for pr in clean_prs:
        print(f"PR #{pr.number}: no unresolved review conversations")


def demonstrate_correlated_count(repo: Repository) -> None:
    print("\n=== Correlated COUNT: review count per pull request ===")

    counts = correlated_count(
        repo.pull_requests,
        repo.reviews,
        lambda pr, review: review.pull_request_id == pr.id,
    )

    for pr in repo.pull_requests:
        print(f"PR #{pr.number}: {counts[pr.id]} review(s)")


def demonstrate_correlated_scalar_subquery(repo: Repository) -> None:
    print("\n=== Correlated scalar subquery: latest review timestamp ===")

    latest = correlated_max(
        repo.pull_requests,
        repo.reviews,
        key=lambda review: review.submitted_at,
        predicate=lambda pr, review: review.pull_request_id == pr.id,
    )

    for pr in repo.pull_requests:
        timestamp = latest[pr.id]
        print(f"PR #{pr.number}: latest review = {timestamp or 'none'}")


def approvals_from_independent_query(repo: Repository) -> set[int]:
    """
    This illustrates an important distinction.

    The result can be produced without a correlated operation by first
    collecting all approved PR identifiers. This is logically equivalent to
    a semi-join for this particular problem.
    """
    return {
        review.pull_request_id
        for review in repo.reviews
        if review.state == "APPROVED"
    }


def approvals_from_correlated_query(repo: Repository) -> set[int]:
    """
    Direct logical equivalent of:

        WHERE EXISTS (
            SELECT 1
            FROM reviews r
            WHERE r.pull_request_id = p.id
              AND r.state = 'APPROVED'
        )
    """
    return {
        pr.id
        for pr in correlated_exists(
            repo.pull_requests,
            repo.reviews,
            lambda pr, review: (
                review.pull_request_id == pr.id
                and review.state == "APPROVED"
            ),
        )
    }


def demonstrate_correlated_vs_set_logic(repo: Repository) -> None:
    print("\n=== Correlated logic versus equivalent set-based result ===")

    correlated = approvals_from_correlated_query(repo)
    set_based = approvals_from_independent_query(repo)

    print("Correlated result:", sorted(correlated))
    print("Set-based result: ", sorted(set_based))
    print("Equivalent:", correlated == set_based)


def evaluate_branch_protection(
    repo: Repository,
    pr: PullRequest,
    protection: BranchProtection,
) -> dict:
    """
    A correlated-query-style governance evaluator.

    Each policy decision is evaluated in the context of the current PR.
    This mirrors a SQL statement containing several correlated EXISTS,
    NOT EXISTS, and COUNT expressions.
    """

    approvals = sum(
        1
        for review in repo.reviews
        if (
            review.pull_request_id == pr.id
            and review.state == "APPROVED"
            and review.reviewer != pr.author
        )
    )

    failed_or_missing_checks = [
        check_name
        for check_name in protection.required_checks
        if not any(
            check.pull_request_id == pr.id
            and check.name == check_name
            and check.state == "SUCCESS"
            for check in repo.checks
        )
    ]

    unresolved = [
        comment
        for comment in repo.comments
        if comment.pull_request_id == pr.id and not comment.resolved
    ]

    reasons = []

    if pr.draft:
        reasons.append("Pull Request is still a draft")

    if approvals < protection.required_approvals:
        reasons.append(
            f"requires {protection.required_approvals} approval(s), "
            f"but has {approvals}"
        )

    if failed_or_missing_checks:
        reasons.append(
            "missing or unsuccessful required checks: "
            + ", ".join(failed_or_missing_checks)
        )

    if protection.require_conversation_resolution and unresolved:
        reasons.append(
            f"{len(unresolved)} unresolved review conversation(s)"
        )

    return {
        "pull_request": pr.number,
        "eligible": not reasons,
        "reasons": reasons,
    }


def demonstrate_governance(repo: Repository) -> None:
    print("\n=== Correlated governance evaluation ===")

    for pr in repo.pull_requests:
        protection = repo.protections.get(pr.base_branch)

        if protection is None:
            print(f"PR #{pr.number}: no protection policy configured")
            continue

        decision = evaluate_branch_protection(repo, pr, protection)

        if decision["eligible"]:
            print(f"PR #{pr.number}: MERGE ELIGIBLE")
        else:
            print(f"PR #{pr.number}: BLOCKED")
            for reason in decision["reasons"]:
                print(f"  - {reason}")


def demonstrate_nested_correlated_logic(repo: Repository) -> None:
    """
    Nested correlated logic corresponds to a query where an inner condition
    itself depends on the current outer row.

    Example SQL shape:

        SELECT p.number
        FROM pull_requests p
        WHERE EXISTS (
            SELECT 1
            FROM reviews r
            WHERE r.pull_request_id = p.id
              AND EXISTS (
                  SELECT 1
                  FROM repositories_users u
                  WHERE u.user_name = r.reviewer
                    AND u.repository_id = p.repository_id
                    AND u.active = true
              )
        );

    Here the inner-most predicate can depend on values established by
    multiple outer scopes.
    """
    print("\n=== Nested correlated evaluation ===")

    active_reviewers = {"alice", "bob", "carol"}

    for pr in repo.pull_requests:
        has_active_approval = any(
            review.pull_request_id == pr.id
            and review.state == "APPROVED"
            and review.reviewer in active_reviewers
            for review in repo.reviews
        )

        print(
            f"PR #{pr.number}: "
            f"{'active reviewer approval found' if has_active_approval else 'no active reviewer approval'}"
        )


def demonstrate_performance_concern(repo: Repository) -> None:
    """
    A naive correlated implementation can scan the inner relation for every
    outer row. If there are N pull requests and M reviews, the worst-case
    work is O(N*M).

    An index or hash structure changes the practical behavior dramatically.
    This dictionary acts like an index on reviews.pull_request_id.
    """
    print("\n=== Index-like optimization of correlated lookup ===")

    reviews_by_pr: dict[int, list[Review]] = {}

    for review in repo.reviews:
        reviews_by_pr.setdefault(review.pull_request_id, []).append(review)

    for pr in repo.pull_requests:
        related = reviews_by_pr.get(pr.id, [])
        approvals = [
            review
            for review in related
            if review.state == "APPROVED"
        ]

        print(
            f"PR #{pr.number}: "
            f"{len(approvals)} approval(s) using indexed lookup"
        )


def demonstrate_null_like_behavior(repo: Repository) -> None:
    """
    SQL NULL introduces three-valued logic. Python does not have identical
    SQL NULL semantics, so this example uses None explicitly and shows why
    application-level simulations must not silently treat missing values as
    ordinary values.

    A SQL scalar correlated subquery with no matching rows normally produces
    NULL, whereas COUNT(*) produces 0.
    """
    print("\n=== Scalar result versus aggregate result for no matches ===")

    latest = correlated_max(
        repo.pull_requests,
        repo.reviews,
        key=lambda review: review.submitted_at,
        predicate=lambda pr, review: review.pull_request_id == pr.id,
    )

    counts = correlated_count(
        repo.pull_requests,
        repo.reviews,
        lambda pr, review: review.pull_request_id == pr.id,
    )

    for pr in repo.pull_requests:
        print(
            f"PR #{pr.number}: "
            f"latest_review={latest[pr.id]!r}, "
            f"review_count={counts[pr.id]}"
        )


def build_demo_repository() -> Repository:
    now = datetime.now()

    return Repository(
        name="payments-service",
        pull_requests=[
            PullRequest(
                id=101,
                number=41,
                title="Add transaction reconciliation",
                author="david",
                base_branch="main",
                source_branch="feature/reconciliation",
            ),
            PullRequest(
                id=102,
                number=42,
                title="Improve payment timeout handling",
                author="alice",
                base_branch="main",
                source_branch="fix/payment-timeout",
            ),
            PullRequest(
                id=103,
                number=43,
                title="Refactor settlement validation",
                author="bob",
                base_branch="main",
                source_branch="refactor/settlement",
                draft=True,
            ),
        ],
        reviews=[
            Review(
                id=1,
                pull_request_id=101,
                reviewer="alice",
                state="APPROVED",
                submitted_at=now - timedelta(hours=5),
            ),
            Review(
                id=2,
                pull_request_id=101,
                reviewer="bob",
                state="COMMENTED",
                submitted_at=now - timedelta(hours=4),
            ),
            Review(
                id=3,
                pull_request_id=102,
                reviewer="carol",
                state="APPROVED",
                submitted_at=now - timedelta(hours=2),
            ),
            Review(
                id=4,
                pull_request_id=103,
                reviewer="alice",
                state="CHANGES_REQUESTED",
                submitted_at=now - timedelta(hours=1),
            ),
        ],
        checks=[
            StatusCheck(
                id=1,
                pull_request_id=101,
                name="unit-tests",
                state="SUCCESS",
            ),
            StatusCheck(
                id=2,
                pull_request_id=101,
                name="security-scan",
                state="SUCCESS",
            ),
            StatusCheck(
                id=3,
                pull_request_id=102,
                name="unit-tests",
                state="SUCCESS",
            ),
            StatusCheck(
                id=4,
                pull_request_id=102,
                name="security-scan",
                state="FAILURE",
            ),
        ],
        comments=[
            Comment(
                id=1,
                pull_request_id=101,
                reviewer="bob",
                body="Please document the reconciliation fallback.",
                resolved=False,
            ),
            Comment(
                id=2,
                pull_request_id=102,
                reviewer="carol",
                body="Timeout value looks reasonable.",
                resolved=True,
            ),
        ],
        protections={
            "main": BranchProtection(
                branch="main",
                required_approvals=1,
                required_checks=("unit-tests", "security-scan"),
                require_conversation_resolution=True,
                allow_force_push=False,
                allow_deletion=False,
                require_linear_history=True,
            )
        },
    )


def main() -> None:
    repo = build_demo_repository()

    print(f"Repository: {repo.name}")
    print("Topic: correlated subqueries applied to repository governance")

    demonstrate_basic_correlated_exists(repo)
    demonstrate_correlated_not_exists(repo)
    demonstrate_correlated_count(repo)
    demonstrate_correlated_scalar_subquery(repo)
    demonstrate_correlated_vs_set_logic(repo)
    demonstrate_governance(repo)
    demonstrate_nested_correlated_logic(repo)
    demonstrate_performance_concern(repo)
    demonstrate_null_like_behavior(repo)

    print("\n=== Key implementation boundary ===")
    print(
        "A correlated operation is characterized by dependence on the "
        "current outer row. It is not defined merely by nesting one query "
        "inside another."
    )


if __name__ == "__main__":
    main()
