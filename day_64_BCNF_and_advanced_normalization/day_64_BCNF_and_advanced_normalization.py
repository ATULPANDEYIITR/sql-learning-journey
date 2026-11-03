from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Tuple


class PullRequestState(Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class ReviewState(Enum):
    COMMENTED = "commented"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    DISMISSED = "dismissed"


class MergeStrategy(Enum):
    MERGE_COMMIT = "merge_commit"
    SQUASH = "squash"
    REBASE = "rebase"


@dataclass
class Commit:
    sha: str
    message: str
    author: str


@dataclass
class Review:
    reviewer: str
    state: ReviewState
    commit_sha: str
    comments: List[str] = field(default_factory=list)
    submitted_at: int = 0


@dataclass
class StatusCheck:
    name: str
    passed: bool
    required: bool
    commit_sha: str


@dataclass
class BranchProtection:
    required_reviews: int = 2
    required_status_checks: Set[str] = field(default_factory=set)
    restrict_direct_push: bool = True
    restrict_force_push: bool = True
    restrict_deletion: bool = True
    require_conversations_resolved: bool = True
    require_linear_history: bool = False


@dataclass
class Branch:
    name: str
    protected: bool = False
    commits: List[Commit] = field(default_factory=list)


@dataclass
class Repository:
    name: str
    branches: Dict[str, Branch]
    reviewers: Set[str]
    protection: Dict[str, BranchProtection]


@dataclass
class PullRequest:
    number: int
    source_branch: str
    target_branch: str
    author: str
    commits: List[Commit]
    state: PullRequestState = PullRequestState.OPEN
    draft: bool = False
    reviews: List[Review] = field(default_factory=list)
    checks: List[StatusCheck] = field(default_factory=list)
    unresolved_conversations: int = 0
    merge_strategy: MergeStrategy = MergeStrategy.SQUASH
    base_sync_required: bool = False

    @property
    def head_sha(self) -> str:
        if not self.commits:
            raise ValueError("Pull Request must contain at least one commit")
        return self.commits[-1].sha


class WorkflowError(Exception):
    pass


class RepositoryWorkflow:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self.pull_requests: Dict[int, PullRequest] = {}
        self.next_number = 1

    def create_pull_request(
        self,
        source: str,
        target: str,
        author: str,
        commits: List[Commit],
        draft: bool = False,
    ) -> PullRequest:
        if source not in self.repository.branches:
            raise WorkflowError(f"Unknown source branch: {source}")
        if target not in self.repository.branches:
            raise WorkflowError(f"Unknown target branch: {target}")
        if source == target:
            raise WorkflowError("Source and target branches must differ")
        if not commits:
            raise WorkflowError("A Pull Request requires a non-empty changeset")

        pr = PullRequest(
            number=self.next_number,
            source_branch=source,
            target_branch=target,
            author=author,
            commits=commits,
            draft=draft,
        )
        self.pull_requests[pr.number] = pr
        self.next_number += 1
        return pr

    def request_review(self, pr_number: int, reviewer: str) -> None:
        pr = self._get_pr(pr_number)
        if pr.state != PullRequestState.OPEN:
            raise WorkflowError("Reviews can only be requested on an open Pull Request")
        if reviewer == pr.author:
            raise WorkflowError("Authors cannot be their own required reviewer")
        if reviewer not in self.repository.reviewers:
            raise WorkflowError("Reviewer is not eligible")

    def submit_review(
        self,
        pr_number: int,
        reviewer: str,
        state: ReviewState,
        comments: List[str] | None = None,
    ) -> None:
        pr = self._get_pr(pr_number)
        if reviewer not in self.repository.reviewers:
            raise WorkflowError("Reviewer is not eligible")
        if reviewer == pr.author:
            raise WorkflowError("Author cannot approve their own Pull Request")

        comments = comments or []

        if state == ReviewState.CHANGES_REQUESTED and not comments:
            raise WorkflowError("A changes-requested review requires a review comment")

        pr.reviews.append(
            Review(
                reviewer=reviewer,
                state=state,
                commit_sha=pr.head_sha,
                comments=comments,
                submitted_at=len(pr.reviews) + 1,
            )
        )

    def add_status_check(
        self,
        pr_number: int,
        name: str,
        passed: bool,
        required: bool = True,
    ) -> None:
        pr = self._get_pr(pr_number)
        pr.checks.append(
            StatusCheck(
                name=name,
                passed=passed,
                required=required,
                commit_sha=pr.head_sha,
            )
        )

    def add_conversation(self, pr_number: int) -> None:
        self._get_pr(pr_number).unresolved_conversations += 1

    def resolve_conversation(self, pr_number: int) -> None:
        pr = self._get_pr(pr_number)
        if pr.unresolved_conversations == 0:
            raise WorkflowError("No unresolved conversation exists")
        pr.unresolved_conversations -= 1

    def synchronize_base(self, pr_number: int, new_commit: Commit) -> None:
        pr = self._get_pr(pr_number)
        pr.commits.append(new_commit)
        pr.base_sync_required = False

        # Reviews attached to the old head become stale.
        for review in pr.reviews:
            if review.commit_sha != pr.head_sha:
                review.state = ReviewState.DISMISSED

    def mark_base_sync_required(self, pr_number: int) -> None:
        self._get_pr(pr_number).base_sync_required = True

    def set_draft(self, pr_number: int, draft: bool) -> None:
        self._get_pr(pr_number).draft = draft

    def close(self, pr_number: int) -> None:
        pr = self._get_pr(pr_number)
        if pr.state == PullRequestState.MERGED:
            raise WorkflowError("Merged Pull Requests cannot be closed")
        pr.state = PullRequestState.CLOSED

    def reopen(self, pr_number: int) -> None:
        pr = self._get_pr(pr_number)
        if pr.state != PullRequestState.CLOSED:
            raise WorkflowError("Only closed Pull Requests can be reopened")
        pr.state = PullRequestState.OPEN

    def merge_eligibility(self, pr_number: int) -> Tuple[bool, List[str]]:
        pr = self._get_pr(pr_number)
        target = self.repository.branches[pr.target_branch]
        policy = self.repository.protection.get(
            pr.target_branch, BranchProtection()
        )

        failures: List[str] = []

        if pr.state != PullRequestState.OPEN:
            failures.append("Pull Request is not open")
        if pr.draft:
            failures.append("Pull Request is still a draft")
        if pr.base_sync_required:
            failures.append("Pull Request must synchronize with the base branch")

        approved_reviewers = {
            review.reviewer
            for review in pr.reviews
            if review.state == ReviewState.APPROVED
            and review.commit_sha == pr.head_sha
            and review.reviewer != pr.author
        }

        if len(approved_reviewers) < policy.required_reviews:
            failures.append(
                f"At least {policy.required_reviews} current approval(s) required"
            )

        latest_checks: Dict[str, StatusCheck] = {}
        for check in pr.checks:
            if check.commit_sha == pr.head_sha:
                latest_checks[check.name] = check

        for required_check in policy.required_status_checks:
            check = latest_checks.get(required_check)
            if check is None:
                failures.append(f"Missing required status check: {required_check}")
            elif not check.passed:
                failures.append(f"Required status check failed: {required_check}")

        if policy.require_conversations_resolved and pr.unresolved_conversations:
            failures.append("Unresolved review conversations remain")

        if policy.require_linear_history and pr.merge_strategy == MergeStrategy.MERGE_COMMIT:
            failures.append("Merge commits are prohibited by linear-history policy")

        if target.protected and pr.source_branch == target.name:
            failures.append("Protected branch cannot be used as its own source")

        return not failures, failures

    def merge(self, pr_number: int) -> None:
        pr = self._get_pr(pr_number)
        eligible, failures = self.merge_eligibility(pr_number)

        if not eligible:
            raise WorkflowError(
                "Merge blocked: " + "; ".join(failures)
            )

        target = self.repository.branches[pr.target_branch]

        if pr.merge_strategy == MergeStrategy.MERGE_COMMIT:
            merge_commit = Commit(
                sha=f"merge-{pr.number}",
                message=f"Merge PR #{pr.number}",
                author=pr.author,
            )
            target.commits.append(merge_commit)
        elif pr.merge_strategy == MergeStrategy.SQUASH:
            target.commits.append(
                Commit(
                    sha=f"squash-{pr.number}",
                    message=f"Squash PR #{pr.number}",
                    author=pr.author,
                )
            )
        elif pr.merge_strategy == MergeStrategy.REBASE:
            target.commits.extend(pr.commits)

        pr.state = PullRequestState.MERGED

    def _get_pr(self, number: int) -> PullRequest:
        if number not in self.pull_requests:
            raise WorkflowError(f"Pull Request #{number} does not exist")
        return self.pull_requests[number]


def build_demo_repository() -> Repository:
    return Repository(
        name="payments-platform",
        branches={
            "main": Branch(
                "main",
                protected=True,
                commits=[
                    Commit("a1", "Initial release", "alice"),
                    Commit("b2", "Add payment API", "alice"),
                ],
            ),
            "feature/fraud-rules": Branch("feature/fraud-rules"),
        },
        reviewers={"bob", "carol", "diana"},
        protection={
            "main": BranchProtection(
                required_reviews=2,
                required_status_checks={"unit-tests", "security-scan"},
                restrict_direct_push=True,
                restrict_force_push=True,
                restrict_deletion=True,
                require_conversations_resolved=True,
                require_linear_history=True,
            )
        },
    )


def main() -> None:
    repository = build_demo_repository()
    workflow = RepositoryWorkflow(repository)

    commits = [
        Commit("c101", "Add fraud rule model", "alice"),
        Commit("c102", "Add rule evaluation", "alice"),
    ]

    pr = workflow.create_pull_request(
        source="feature/fraud-rules",
        target="main",
        author="alice",
        commits=commits,
        draft=False,
    )

    workflow.request_review(pr.number, "bob")
    workflow.request_review(pr.number, "carol")

    workflow.submit_review(pr.number, "bob", ReviewState.APPROVED)
    workflow.submit_review(
        pr.number,
        "carol",
        ReviewState.CHANGES_REQUESTED,
        ["Add validation for duplicate rules"],
    )

    workflow.add_conversation(pr.number)
    workflow.add_status_check(pr.number, "unit-tests", True)
    workflow.add_status_check(pr.number, "security-scan", True)

    eligible, failures = workflow.merge_eligibility(pr.number)
    print("Eligible before correction:", eligible)
    print("Blocking conditions:", failures)

    workflow.resolve_conversation(pr.number)
    workflow.submit_review(pr.number, "carol", ReviewState.APPROVED)

    eligible, failures = workflow.merge_eligibility(pr.number)
    print("\nEligible after correction:", eligible)
    print("Blocking conditions:", failures)

    if eligible:
        workflow.merge(pr.number)
        print("Pull Request merged using:", pr.merge_strategy.value)

    try:
        workflow.merge(pr.number)
    except WorkflowError as exc:
        print("Expected failure:", exc)


if __name__ == "__main__":
    main()
