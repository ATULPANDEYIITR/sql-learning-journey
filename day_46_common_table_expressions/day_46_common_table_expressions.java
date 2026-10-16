import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class CteGovernanceModel {

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
        DRAFT,
        OPEN,
        CLOSED,
        MERGED
    }

    record Review(
            String reviewer,
            ReviewState state,
            String comment
    ) {}

    record StatusCheck(
            String name,
            CheckState state
    ) {}

    record PullRequest(
            int id,
            String sourceBranch,
            String targetBranch,
            PullRequestState state,
            List<Review> reviews,
            List<StatusCheck> checks
    ) {}

    record BranchProtection(
            String branch,
            int requiredApprovals,
            boolean requirePassingChecks,
            boolean requireConversationResolution,
            boolean allowForcePush
    ) {
        BranchProtection {
            if (branch == null || branch.isBlank()) {
                throw new IllegalArgumentException("Protected branch is required.");
            }
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                        "Required approvals cannot be negative."
                );
            }
        }
    }

    static final class MergeDecision {
        private final boolean eligible;
        private final List<String> blockers;

        MergeDecision(boolean eligible, List<String> blockers) {
            this.eligible = eligible;
            this.blockers = List.copyOf(blockers);
        }

        boolean eligible() {
            return eligible;
        }

        List<String> blockers() {
            return blockers;
        }
    }

    static final class RepositoryGovernanceService {
        private final Map<String, BranchProtection> policies = new HashMap<>();

        void registerPolicy(BranchProtection policy) {
            policies.put(policy.branch(), policy);
        }

        MergeDecision evaluate(PullRequest pullRequest) {
            BranchProtection policy = policies.get(pullRequest.targetBranch());

            if (policy == null) {
                return new MergeDecision(true, List.of());
            }

            List<String> blockers = new ArrayList<>();

            if (pullRequest.state() != PullRequestState.OPEN) {
                blockers.add("Pull request is not open.");
            }

            Set<String> approvingReviewers = new HashSet<>();

            for (Review review : pullRequest.reviews()) {
                /*
                 * Approval is represented as a state belonging to a review.
                 * A later CHANGES_REQUESTED or DISMISSED review does not count
                 * as an approval merely because the reviewer approved earlier.
                 */
                if (review.state() == ReviewState.APPROVED) {
                    approvingReviewers.add(review.reviewer());
                }
            }

            if (approvingReviewers.size() < policy.requiredApprovals()) {
                blockers.add(
                        "Required approvals are not satisfied: "
                                + approvingReviewers.size()
                                + "/"
                                + policy.requiredApprovals()
                );
            }

            if (policy.requirePassingChecks()) {
                boolean checksPass = !pullRequest.checks().isEmpty()
                        && pullRequest.checks().stream()
                        .allMatch(check -> check.state() == CheckState.PASSED);

                if (!checksPass) {
                    blockers.add("Required status checks are not all passing.");
                }
            }

            return new MergeDecision(blockers.isEmpty(), blockers);
        }
    }

    static PullRequest pullRequest(
            int id,
            String source,
            String target,
            PullRequestState state,
            Review... reviews
    ) {
        List<StatusCheck> checks = List.of(
                new StatusCheck("build", CheckState.PASSED),
                new StatusCheck("unit-tests", CheckState.PASSED),
                new StatusCheck("security-scan", CheckState.PASSED)
        );

        return new PullRequest(
                id,
                source,
                target,
                state,
                List.of(reviews),
                checks
        );
    }

    static void printDecision(
            RepositoryGovernanceService service,
            PullRequest pullRequest
    ) {
        MergeDecision decision = service.evaluate(pullRequest);

        System.out.println(
                "PR #" + pullRequest.id()
                        + " " + pullRequest.sourceBranch()
                        + " -> " + pullRequest.targetBranch()
        );

        if (decision.eligible()) {
            System.out.println("  Merge eligibility: ALLOWED");
        } else {
            System.out.println("  Merge eligibility: BLOCKED");
            decision.blockers().forEach(blocker ->
                    System.out.println("  Blocker: " + blocker)
            );
        }
        System.out.println();
    }

    public static void main(String[] args) {
        RepositoryGovernanceService service =
                new RepositoryGovernanceService();

        service.registerPolicy(
                new BranchProtection(
                        "main",
                        2,
                        true,
                        true,
                        false
                )
        );

        PullRequest approvedRequest = pullRequest(
                7001,
                "feature/order-report",
                "main",
                PullRequestState.OPEN,
                new Review(
                        "alice",
                        ReviewState.APPROVED,
                        "Query structure and indexes reviewed."
                ),
                new Review(
                        "bob",
                        ReviewState.APPROVED,
                        "Application integration reviewed."
                )
        );

        PullRequest insufficientApprovalRequest = pullRequest(
                7002,
                "feature/payment-validation",
                "main",
                PullRequestState.OPEN,
                new Review(
                        "alice",
                        ReviewState.APPROVED,
                        "Validation logic reviewed."
                ),
                new Review(
                        "bob",
                        ReviewState.CHANGES_REQUESTED,
                        "Boundary case requires correction."
                )
        );

        PullRequest draftRequest = pullRequest(
                7003,
                "feature/experimental-query",
                "main",
                PullRequestState.DRAFT,
                new Review(
                        "alice",
                        ReviewState.APPROVED,
                        "Preliminary review only."
                ),
                new Review(
                        "bob",
                        ReviewState.APPROVED,
                        "Preliminary review only."
                )
        );

        System.out.println("Enterprise Repository Governance\n");
        printDecision(service, approvedRequest);
        printDecision(service, insufficientApprovalRequest);
        printDecision(service, draftRequest);

        /*
         * EnumSet is useful when an enterprise policy needs to describe
         * supported review states without accepting arbitrary strings.
         */
        EnumSet<ReviewState> reviewLifecycle =
                EnumSet.allOf(ReviewState.class);

        System.out.println("Supported review states: " + reviewLifecycle);
    }
}
