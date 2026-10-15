import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/*
 * Enterprise Repository Governance Model
 *
 * The program demonstrates derived-table reasoning through domain-specific
 * intermediate collections. Each intermediate collection represents a logical
 * result set that a later service consumes.
 *
 * Java 17+.
 */

public class DerivedTableGovernance {

    enum PullRequestState {
        OPEN,
        CLOSED,
        MERGED
    }

    enum ReviewState {
        APPROVED,
        CHANGES_REQUESTED,
        COMMENTED
    }

    enum CheckState {
        SUCCESS,
        FAILURE,
        PENDING
    }

    record PullRequest(
        int id,
        String repository,
        String sourceBranch,
        String targetBranch,
        String author,
        PullRequestState state,
        int additions,
        int deletions
    ) {
        PullRequest {
            if (id <= 0) {
                throw new IllegalArgumentException("Pull Request ID must be positive");
            }
            if (repository == null || repository.isBlank()) {
                throw new IllegalArgumentException("Repository is required");
            }
            if (sourceBranch == null || sourceBranch.isBlank()) {
                throw new IllegalArgumentException("Source branch is required");
            }
            if (targetBranch == null || targetBranch.isBlank()) {
                throw new IllegalArgumentException("Target branch is required");
            }
            if (additions < 0 || deletions < 0) {
                throw new IllegalArgumentException("Change counts cannot be negative");
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
                throw new IllegalArgumentException("Identifiers must be positive");
            }
            if (reviewer == null || reviewer.isBlank()) {
                throw new IllegalArgumentException("Reviewer is required");
            }
        }
    }

    record StatusCheck(
        int pullRequestId,
        String name,
        CheckState state
    ) {
        StatusCheck {
            if (pullRequestId <= 0) {
                throw new IllegalArgumentException("Pull Request ID must be positive");
            }
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException("Check name is required");
            }
        }
    }

    record BranchProtectionPolicy(
        String repository,
        String branch,
        int requiredApprovals,
        Set<String> requiredChecks,
        boolean requireLinearHistory
    ) {
        BranchProtectionPolicy {
            if (repository == null || repository.isBlank()) {
                throw new IllegalArgumentException("Repository is required");
            }
            if (branch == null || branch.isBlank()) {
                throw new IllegalArgumentException("Protected branch is required");
            }
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "Required approval count cannot be negative"
                );
            }
            requiredChecks = Set.copyOf(requiredChecks);
        }
    }

    record ChangeMetrics(
        int pullRequestId,
        String repository,
        int totalChange,
        double deletionRatio
    ) {}

    record ApprovalSummary(
        int pullRequestId,
        Set<String> approvingReviewers
    ) {
        int approvalCount() {
            return approvingReviewers.size();
        }
    }

    record CheckSummary(
        int pullRequestId,
        Set<String> passingChecks
    ) {}

    record PolicyMatch(
        PullRequest pullRequest,
        BranchProtectionPolicy policy
    ) {}

    record MergeDecision(
        int pullRequestId,
        String repository,
        String targetBranch,
        int approvalCount,
        boolean approvalsSatisfied,
        boolean checksSatisfied,
        boolean stateSatisfied,
        boolean mergeEligible,
        String reason
    ) {}

    /*
     * This service is intentionally separated from the domain records. The
     * records model facts; the service creates derived facts and evaluates
     * policies against them.
     */
    static final class DerivedTableService {

        List<ChangeMetrics> createChangeMetrics(
            List<PullRequest> pullRequests
        ) {
            return pullRequests.stream()
                .map(pr -> {
                    int total = pr.additions() + pr.deletions();

                    double deletionRatio = total == 0
                        ? 0.0
                        : (double) pr.deletions() / total;

                    return new ChangeMetrics(
                        pr.id(),
                        pr.repository(),
                        total,
                        deletionRatio
                    );
                })
                .toList();
        }

        List<ChangeMetrics> createLargeChangeRelation(
            List<ChangeMetrics> metrics,
            int threshold
        ) {
            return metrics.stream()
                .filter(metric -> metric.totalChange() >= threshold)
                .toList();
        }

        Map<String, Long> aggregateLargeChanges(
            List<ChangeMetrics> largeChanges
        ) {
            return largeChanges.stream()
                .collect(
                    java.util.stream.Collectors.groupingBy(
                        ChangeMetrics::repository,
                        java.util.stream.Collectors.counting()
                    )
                );
        }

        List<ApprovalSummary> createApprovalRelation(
            List<Review> reviews
        ) {
            Map<Integer, Set<String>> reviewersByPr =
                new HashMap<>();

            for (Review review : reviews) {
                if (review.state() == ReviewState.APPROVED) {
                    reviewersByPr
                        .computeIfAbsent(
                            review.pullRequestId(),
                            ignored -> new HashSet<>()
                        )
                        .add(review.reviewer());
                }
            }

            return reviewersByPr.entrySet()
                .stream()
                .map(entry ->
                    new ApprovalSummary(
                        entry.getKey(),
                        Set.copyOf(entry.getValue())
                    )
                )
                .toList();
        }

        List<CheckSummary> createCheckRelation(
            List<StatusCheck> checks
        ) {
            Map<Integer, Set<String>> passingChecks =
                new HashMap<>();

            for (StatusCheck check : checks) {
                if (check.state() == CheckState.SUCCESS) {
                    passingChecks
                        .computeIfAbsent(
                            check.pullRequestId(),
                            ignored -> new HashSet<>()
                        )
                        .add(check.name());
                }
            }

            return passingChecks.entrySet()
                .stream()
                .map(entry ->
                    new CheckSummary(
                        entry.getKey(),
                        Set.copyOf(entry.getValue())
                    )
                )
                .toList();
        }

        List<PolicyMatch> createPolicyRelation(
            List<PullRequest> pullRequests,
            List<BranchProtectionPolicy> policies
        ) {
            List<PolicyMatch> result = new ArrayList<>();

            for (PullRequest pr : pullRequests) {
                for (BranchProtectionPolicy policy : policies) {
                    if (
                        Objects.equals(
                            pr.repository(),
                            policy.repository()
                        )
                        &&
                        Objects.equals(
                            pr.targetBranch(),
                            policy.branch()
                        )
                    ) {
                        result.add(new PolicyMatch(pr, policy));
                    }
                }
            }

            return List.copyOf(result);
        }

        MergeDecision evaluate(
            PolicyMatch match,
            List<ApprovalSummary> approvals,
            List<CheckSummary> checks
        ) {
            ApprovalSummary approvalSummary =
                approvals.stream()
                    .filter(
                        summary ->
                            summary.pullRequestId()
                                == match.pullRequest().id()
                    )
                    .findFirst()
                    .orElse(
                        new ApprovalSummary(
                            match.pullRequest().id(),
                            Set.of()
                        )
                    );

            CheckSummary checkSummary =
                checks.stream()
                    .filter(
                        summary ->
                            summary.pullRequestId()
                                == match.pullRequest().id()
                    )
                    .findFirst()
                    .orElse(
                        new CheckSummary(
                            match.pullRequest().id(),
                            Set.of()
                        )
                    );

            boolean approvalsSatisfied =
                approvalSummary.approvalCount()
                    >= match.policy().requiredApprovals();

            boolean checksSatisfied =
                checkSummary.passingChecks()
                    .containsAll(match.policy().requiredChecks());

            boolean stateSatisfied =
                match.pullRequest().state()
                    == PullRequestState.OPEN;

            boolean eligible =
                approvalsSatisfied
                    && checksSatisfied
                    && stateSatisfied;

            String reason;

            if (!stateSatisfied) {
                reason = "Pull Request is not open";
            } else if (!approvalsSatisfied) {
                reason = "Required approvals are missing";
            } else if (!checksSatisfied) {
                reason = "Required status checks are incomplete";
            } else {
                reason = "All policy predicates are satisfied";
            }

            return new MergeDecision(
                match.pullRequest().id(),
                match.pullRequest().repository(),
                match.pullRequest().targetBranch(),
                approvalSummary.approvalCount(),
                approvalsSatisfied,
                checksSatisfied,
                stateSatisfied,
                eligible,
                reason
            );
        }
    }

    static void printChangeRelation(
        List<ChangeMetrics> metrics
    ) {
        System.out.println("\nDerived change relation:");

        for (ChangeMetrics metric : metrics) {
            System.out.printf(
                "PR=%d repository=%s totalChange=%d deletionRatio=%.2f%n",
                metric.pullRequestId(),
                metric.repository(),
                metric.totalChange(),
                metric.deletionRatio()
            );
        }
    }

    static void printDecisions(
        List<MergeDecision> decisions
    ) {
        System.out.println("\nMerge eligibility relation:");

        for (MergeDecision decision : decisions) {
            System.out.printf(
                "PR=%d repository=%s target=%s approvals=%d "
                    + "approvalsOK=%s checksOK=%s stateOK=%s "
                    + "eligible=%s reason=%s%n",
                decision.pullRequestId(),
                decision.repository(),
                decision.targetBranch(),
                decision.approvalCount(),
                decision.approvalsSatisfied(),
                decision.checksSatisfied(),
                decision.stateSatisfied(),
                decision.mergeEligible(),
                decision.reason()
            );
        }
    }

    public static void main(String[] args) {
        List<PullRequest> pullRequests = List.of(
            new PullRequest(
                101,
                "payment-platform",
                "feature/checkout-validation",
                "main",
                "atul",
                PullRequestState.OPEN,
                340,
                90
            ),
            new PullRequest(
                102,
                "payment-platform",
                "fix/token-expiry",
                "main",
                "neha",
                PullRequestState.OPEN,
                80,
                25
            ),
            new PullRequest(
                103,
                "payment-platform",
                "release/2026-10",
                "release",
                "rahul",
                PullRequestState.OPEN,
                510,
                180
            ),
            new PullRequest(
                104,
                "identity-service",
                "feature/session-hardening",
                "main",
                "meera",
                PullRequestState.OPEN,
                210,
                60
            )
        );

        List<Review> reviews = List.of(
            new Review(1, 101, "neha", ReviewState.APPROVED),
            new Review(2, 101, "rahul", ReviewState.APPROVED),
            new Review(3, 102, "meera", ReviewState.APPROVED),
            new Review(4, 103, "neha", ReviewState.APPROVED),
            new Review(5, 103, "vikas", ReviewState.CHANGES_REQUESTED),
            new Review(6, 104, "rahul", ReviewState.APPROVED)
        );

        List<StatusCheck> checks = List.of(
            new StatusCheck(
                101, "unit-tests", CheckState.SUCCESS
            ),
            new StatusCheck(
                101, "security-scan", CheckState.SUCCESS
            ),
            new StatusCheck(
                102, "unit-tests", CheckState.SUCCESS
            ),
            new StatusCheck(
                102, "security-scan", CheckState.FAILURE
            ),
            new StatusCheck(
                103, "unit-tests", CheckState.SUCCESS
            ),
            new StatusCheck(
                103, "security-scan", CheckState.SUCCESS
            ),
            new StatusCheck(
                104, "unit-tests", CheckState.SUCCESS
            ),
            new StatusCheck(
                104, "security-scan", CheckState.SUCCESS
            )
        );

        List<BranchProtectionPolicy> policies = List.of(
            new BranchProtectionPolicy(
                "payment-platform",
                "main",
                2,
                Set.of("unit-tests", "security-scan"),
                true
            ),
            new BranchProtectionPolicy(
                "payment-platform",
                "release",
                2,
                Set.of("unit-tests", "security-scan"),
                true
            ),
            new BranchProtectionPolicy(
                "identity-service",
                "main",
                2,
                Set.of("unit-tests", "security-scan"),
                false
            )
        );

        DerivedTableService service =
            new DerivedTableService();

        List<ChangeMetrics> changeMetrics =
            service.createChangeMetrics(pullRequests);

        List<ChangeMetrics> largeChanges =
            service.createLargeChangeRelation(
                changeMetrics,
                100
            );

        printChangeRelation(largeChanges);

        Map<String, Long> repositoryCounts =
            service.aggregateLargeChanges(largeChanges);

        System.out.println(
            "\nLarge-change aggregation: "
                + repositoryCounts
        );

        List<ApprovalSummary> approvalRelation =
            service.createApprovalRelation(reviews);

        List<CheckSummary> checkRelation =
            service.createCheckRelation(checks);

        List<PolicyMatch> policyRelation =
            service.createPolicyRelation(
                pullRequests,
                policies
            );

        List<MergeDecision> decisions =
            policyRelation.stream()
                .map(
                    match ->
                        service.evaluate(
                            match,
                            approvalRelation,
                            checkRelation
                        )
                )
                .toList();

        printDecisions(decisions);

        /*
         * The empty approval relation is intentionally handled as a valid
         * intermediate state. A missing row means zero approvals rather than
         * an application crash, which mirrors the distinction between a
         * missing aggregate row and a malformed database record.
         */
        MergeDecision missingApprovalScenario =
            service.evaluate(
                new PolicyMatch(
                    new PullRequest(
                        999,
                        "payment-platform",
                        "feature/unreviewed",
                        "main",
                        "developer",
                        PullRequestState.OPEN,
                        20,
                        5
                    ),
                    policies.get(0)
                ),
                List.of(),
                List.of()
            );

        System.out.println(
            "\nMissing intermediate rows: "
                + missingApprovalScenario
        );
    }
}
