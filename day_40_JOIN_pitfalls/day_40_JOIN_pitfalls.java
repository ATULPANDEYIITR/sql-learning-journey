import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/*
 * Enterprise Repository Governance and JOIN Cardinality
 *
 * The domain model represents a governance service that evaluates pull
 * requests against reviews, status checks, and protected-branch policies.
 *
 * The key relational lesson is represented through explicit domain types:
 *
 * PullRequest -> Review       = one-to-many
 * PullRequest -> StatusCheck  = one-to-many
 * Repository  -> BranchPolicy = one-to-many
 *
 * A governance service must not combine all child collections into one
 * parent-level report without controlling their cardinality.
 */

public class JoinPitfallsGovernance {

    enum ReviewState {
        COMMENTED,
        CHANGES_REQUESTED,
        APPROVED,
        DISMISSED
    }

    enum CheckState {
        PENDING,
        PASSED,
        FAILED
    }

    enum PullRequestState {
        OPEN,
        CLOSED
    }

    record PullRequest(
            int id,
            String repository,
            String sourceBranch,
            String targetBranch,
            String author,
            boolean draft,
            PullRequestState state
    ) {
        PullRequest {
            if (id <= 0) {
                throw new IllegalArgumentException("Pull request ID must be positive.");
            }
            if (repository == null || repository.isBlank()) {
                throw new IllegalArgumentException("Repository is required.");
            }
            if (sourceBranch == null || sourceBranch.isBlank()) {
                throw new IllegalArgumentException("Source branch is required.");
            }
            if (targetBranch == null || targetBranch.isBlank()) {
                throw new IllegalArgumentException("Target branch is required.");
            }
        }
    }

    record Review(
            int id,
            int pullRequestId,
            String reviewer,
            ReviewState state
    ) {
        Review {
            if (id <= 0 || pullRequestId <= 0) {
                throw new IllegalArgumentException("Review identifiers must be positive.");
            }
            if (reviewer == null || reviewer.isBlank()) {
                throw new IllegalArgumentException("Reviewer is required.");
            }
            if (state == null) {
                throw new IllegalArgumentException("Review state is required.");
            }
        }
    }

    record StatusCheck(
            int id,
            int pullRequestId,
            String name,
            CheckState state
    ) {
        StatusCheck {
            if (id <= 0 || pullRequestId <= 0) {
                throw new IllegalArgumentException("Check identifiers must be positive.");
            }
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException("Check name is required.");
            }
            if (state == null) {
                throw new IllegalArgumentException("Check state is required.");
            }
        }
    }

    record BranchProtection(
            String repository,
            String branch,
            int requiredApprovals,
            boolean requiredChecks,
            boolean restrictDirectPush,
            boolean restrictForcePush
    ) {
        BranchProtection {
            if (repository == null || repository.isBlank()) {
                throw new IllegalArgumentException("Repository is required.");
            }
            if (branch == null || branch.isBlank()) {
                throw new IllegalArgumentException("Branch is required.");
            }
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException("Approval requirement cannot be negative.");
            }
        }
    }

    record ReviewSummary(
            long approvals,
            long changesRequested,
            Set<String> approvingReviewers
    ) {
        ReviewSummary {
            approvingReviewers =
                    Collections.unmodifiableSet(new HashSet<>(approvingReviewers));
        }
    }

    record CheckSummary(
            long passed,
            long failed,
            long pending,
            long total
    ) {}

    record MergeDecision(
            int pullRequestId,
            boolean approvalsSatisfied,
            boolean checksSatisfied,
            boolean mergeable,
            String reason
    ) {}

    private final List<PullRequest> pullRequests = new ArrayList<>();
    private final List<Review> reviews = new ArrayList<>();
    private final List<StatusCheck> checks = new ArrayList<>();
    private final List<BranchProtection> policies = new ArrayList<>();

    public void loadData() {
        pullRequests.add(new PullRequest(
                101,
                "payments-api",
                "feature/refund",
                "main",
                "atul",
                false,
                PullRequestState.OPEN
        ));

        pullRequests.add(new PullRequest(
                102,
                "payments-api",
                "feature/ledger",
                "main",
                "ravi",
                false,
                PullRequestState.OPEN
        ));

        pullRequests.add(new PullRequest(
                103,
                "payments-api",
                "feature/metrics",
                "main",
                "meera",
                true,
                PullRequestState.OPEN
        ));

        reviews.add(new Review(1, 101, "reviewer-a", ReviewState.APPROVED));
        reviews.add(new Review(2, 101, "reviewer-b", ReviewState.COMMENTED));

        reviews.add(new Review(3, 102, "reviewer-a", ReviewState.APPROVED));
        reviews.add(new Review(4, 102, "reviewer-b", ReviewState.CHANGES_REQUESTED));

        reviews.add(new Review(5, 103, "reviewer-c", ReviewState.APPROVED));

        checks.add(new StatusCheck(1, 101, "unit-tests", CheckState.PASSED));
        checks.add(new StatusCheck(2, 101, "security-scan", CheckState.PASSED));
        checks.add(new StatusCheck(3, 101, "integration-tests", CheckState.PASSED));

        checks.add(new StatusCheck(4, 102, "unit-tests", CheckState.PASSED));
        checks.add(new StatusCheck(5, 102, "security-scan", CheckState.FAILED));

        checks.add(new StatusCheck(6, 103, "unit-tests", CheckState.PENDING));

        policies.add(new BranchProtection(
                "payments-api",
                "main",
                1,
                true,
                true,
                true
        ));
    }

    private BranchProtection findPolicy(PullRequest pullRequest) {
        return policies.stream()
                .filter(policy ->
                        policy.repository().equals(pullRequest.repository()) &&
                        policy.branch().equals(pullRequest.targetBranch()))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException(
                        "No protection policy exists for "
                                + pullRequest.repository()
                                + "/"
                                + pullRequest.targetBranch()
                ));
    }

    private ReviewSummary summarizeReviews(int pullRequestId) {
        List<Review> matchingReviews = reviews.stream()
                .filter(review -> review.pullRequestId() == pullRequestId)
                .toList();

        long approvals = matchingReviews.stream()
                .filter(review -> review.state() == ReviewState.APPROVED)
                .count();

        long changesRequested = matchingReviews.stream()
                .filter(review -> review.state() == ReviewState.CHANGES_REQUESTED)
                .count();

        Set<String> approvingReviewers = matchingReviews.stream()
                .filter(review -> review.state() == ReviewState.APPROVED)
                .map(Review::reviewer)
                .collect(java.util.stream.Collectors.toSet());

        /*
         * A Set is important here. If a data pipeline accidentally stores
         * duplicate approval events for the same reviewer, counting raw rows
         * can overstate approval strength. The business rule should define
         * whether approvals are reviewer-based or event-based.
         */
        return new ReviewSummary(
                approvals,
                changesRequested,
                approvingReviewers
        );
    }

    private CheckSummary summarizeChecks(int pullRequestId) {
        List<StatusCheck> matchingChecks = checks.stream()
                .filter(check -> check.pullRequestId() == pullRequestId)
                .toList();

        long passed = matchingChecks.stream()
                .filter(check -> check.state() == CheckState.PASSED)
                .count();

        long failed = matchingChecks.stream()
                .filter(check -> check.state() == CheckState.FAILED)
                .count();

        long pending = matchingChecks.stream()
                .filter(check -> check.state() == CheckState.PENDING)
                .count();

        return new CheckSummary(
                passed,
                failed,
                pending,
                matchingChecks.size()
        );
    }

    private MergeDecision evaluate(PullRequest pullRequest) {
        BranchProtection policy = findPolicy(pullRequest);
        ReviewSummary reviewSummary = summarizeReviews(pullRequest.id());
        CheckSummary checkSummary = summarizeChecks(pullRequest.id());

        boolean approvalsSatisfied =
                reviewSummary.approvingReviewers().size()
                        >= policy.requiredApprovals()
                && reviewSummary.changesRequested() == 0;

        boolean checksSatisfied =
                !policy.requiredChecks()
                || (
                    checkSummary.total() > 0
                    && checkSummary.failed() == 0
                    && checkSummary.pending() == 0
                );

        if (pullRequest.draft()) {
            return new MergeDecision(
                    pullRequest.id(),
                    approvalsSatisfied,
                    checksSatisfied,
                    false,
                    "Draft pull requests are not mergeable."
            );
        }

        if (pullRequest.state() != PullRequestState.OPEN) {
            return new MergeDecision(
                    pullRequest.id(),
                    approvalsSatisfied,
                    checksSatisfied,
                    false,
                    "Pull request is not open."
            );
        }

        if (!approvalsSatisfied) {
            return new MergeDecision(
                    pullRequest.id(),
                    false,
                    checksSatisfied,
                    false,
                    "Approval requirement is not satisfied."
            );
        }

        if (!checksSatisfied) {
            return new MergeDecision(
                    pullRequest.id(),
                    true,
                    false,
                    false,
                    "Required status checks are not satisfied."
            );
        }

        return new MergeDecision(
                pullRequest.id(),
                true,
                true,
                true,
                "All evaluated merge conditions are satisfied."
        );
    }

    private void demonstrateJoinExplosion() {
        System.out.println("\n=== Direct Child Collection Combination ===");

        int pullRequestId = 101;

        List<Review> prReviews = reviews.stream()
                .filter(review -> review.pullRequestId() == pullRequestId)
                .toList();

        List<StatusCheck> prChecks = checks.stream()
                .filter(check -> check.pullRequestId() == pullRequestId)
                .toList();

        long combinations = 0;

        for (Review review : prReviews) {
            for (StatusCheck check : prChecks) {
                combinations++;
                System.out.printf(
                        "PR=%d review=%d check=%s%n",
                        pullRequestId,
                        review.id(),
                        check.name()
                );
            }
        }

        System.out.println(
                "Combinations produced: " + combinations
        );
        System.out.println(
                "The governance report should contain one PR-level decision, "
                        + "not one row for every review/check combination."
        );
    }

    private void demonstrateWrongRelationship() {
        System.out.println("\n=== Relationship Validation ===");

        long correctMatches = 0;
        long repositoryOnlyMatches = 0;

        for (Review review : reviews) {
            for (StatusCheck check : checks) {
                if (review.pullRequestId() == check.pullRequestId()) {
                    correctMatches++;
                }

                /*
                 * Repository-level equality is too broad. All these records
                 * happen to belong to one repository, so this comparison would
                 * connect unrelated pull requests.
                 */
                repositoryOnlyMatches++;
            }
        }

        System.out.println("Correct PR-level relationships: " + correctMatches);
        System.out.println("Repository-only combinations: " + repositoryOnlyMatches);
    }

    private void demonstrateMergeDecisions() {
        System.out.println("\n=== Enterprise Merge Decisions ===");

        for (PullRequest pullRequest : pullRequests) {
            MergeDecision decision = evaluate(pullRequest);

            System.out.printf(
                    "PR #%d | approvals=%s | checks=%s | mergeable=%s | %s%n",
                    decision.pullRequestId(),
                    decision.approvalsSatisfied(),
                    decision.checksSatisfied(),
                    decision.mergeable(),
                    decision.reason()
            );
        }
    }

    private void demonstrateCardinalityDiagnostics() {
        System.out.println("\n=== Cardinality Diagnostics ===");

        Map<Integer, Long> reviewCounts = reviews.stream()
                .collect(java.util.stream.Collectors.groupingBy(
                        Review::pullRequestId,
                        java.util.stream.Collectors.counting()
                ));

        Map<Integer, Long> checkCounts = checks.stream()
                .collect(java.util.stream.Collectors.groupingBy(
                        StatusCheck::pullRequestId,
                        java.util.stream.Collectors.counting()
                ));

        for (PullRequest pullRequest : pullRequests) {
            long reviewCount =
                    reviewCounts.getOrDefault(pullRequest.id(), 0L);

            long checkCount =
                    checkCounts.getOrDefault(pullRequest.id(), 0L);

            System.out.printf(
                    "PR #%d -> reviews=%d, checks=%d%n",
                    pullRequest.id(),
                    reviewCount,
                    checkCount
            );
        }

        System.out.println(
                "Independent child counts explain why a direct multi-child "
                        + "join can multiply rows."
        );
    }

    public static void main(String[] args) {
        try {
            JoinPitfallsGovernance application =
                    new JoinPitfallsGovernance();

            application.loadData();
            application.demonstrateJoinExplosion();
            application.demonstrateWrongRelationship();
            application.demonstrateCardinalityDiagnostics();
            application.demonstrateMergeDecisions();

            System.out.println("\n=== Design Principle ===");
            System.out.println(
                    "Evaluate independent one-to-many facts separately and "
                            + "combine their summaries at the intended parent "
                            + "grain. Do not use duplicate elimination as a "
                            + "substitute for a correct relationship."
            );
        } catch (RuntimeException error) {
            System.err.println(
                    "Governance evaluation failed: " + error.getMessage()
            );
            System.exit(1);
        }
    }
}
