import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

public class MembershipPolicyDemo {

    enum SqlTruth {
        TRUE,
        FALSE,
        UNKNOWN
    }

    enum ReviewState {
        APPROVED,
        CHANGES_REQUESTED,
        COMMENTED
    }

    record Review(
        String reviewer,
        ReviewState state,
        boolean eligible
    ) {}

    record StatusCheck(
        String name,
        boolean passed,
        boolean required
    ) {}

    record BranchProtection(
        String branch,
        int requiredApprovals,
        boolean requirePassingChecks,
        boolean blockDirectPush,
        boolean preventForcePush
    ) {
        BranchProtection {
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "requiredApprovals cannot be negative"
                );
            }
        }
    }

    record PullRequest(
        long id,
        String sourceBranch,
        String targetBranch,
        Optional<String> author,
        boolean draft,
        boolean synchronizedWithBase
    ) {}

    record MergeDecision(
        boolean eligible,
        List<String> reasons
    ) {}

    static SqlTruth sqlEqual(
        String left,
        String right
    ) {
        if (left == null || right == null) {
            return SqlTruth.UNKNOWN;
        }

        return left.equals(right)
            ? SqlTruth.TRUE
            : SqlTruth.FALSE;
    }

    static SqlTruth sqlIn(
        String value,
        List<String> candidates
    ) {
        boolean unknownEncountered = false;

        for (String candidate : candidates) {
            SqlTruth comparison = sqlEqual(value, candidate);

            if (comparison == SqlTruth.TRUE) {
                return SqlTruth.TRUE;
            }

            if (comparison == SqlTruth.UNKNOWN) {
                unknownEncountered = true;
            }
        }

        return unknownEncountered
            ? SqlTruth.UNKNOWN
            : SqlTruth.FALSE;
    }

    static SqlTruth sqlNot(SqlTruth value) {
        if (value == SqlTruth.UNKNOWN) {
            return SqlTruth.UNKNOWN;
        }

        return value == SqlTruth.TRUE
            ? SqlTruth.FALSE
            : SqlTruth.TRUE;
    }

    static boolean passesWhere(SqlTruth value) {
        return value == SqlTruth.TRUE;
    }

    static MergeDecision evaluateMerge(
        PullRequest pullRequest,
        List<Review> reviews,
        List<StatusCheck> checks,
        BranchProtection protection
    ) {
        List<String> reasons = new ArrayList<>();

        if (!Objects.equals(
            pullRequest.targetBranch(),
            protection.branch()
        )) {
            reasons.add("Pull Request targets a branch outside this policy.");
        }

        if (pullRequest.draft()) {
            reasons.add("Draft Pull Request is not mergeable.");
        }

        if (pullRequest.author().isEmpty()) {
            reasons.add("Pull Request has no author.");
        }

        if (!pullRequest.synchronizedWithBase()) {
            reasons.add("Pull Request must be synchronized with the base branch.");
        }

        long approvals = reviews.stream()
            .filter(Review::eligible)
            .filter(review -> review.state() == ReviewState.APPROVED)
            .count();

        if (approvals < protection.requiredApprovals()) {
            reasons.add(
                "The required number of eligible approvals has not been reached."
            );
        }

        if (protection.requirePassingChecks()) {
            checks.stream()
                .filter(StatusCheck::required)
                .filter(check -> !check.passed())
                .map(check ->
                    "Required status check failed: " + check.name()
                )
                .forEach(reasons::add);
        }

        return new MergeDecision(
            reasons.isEmpty(),
            List.copyOf(reasons)
        );
    }

    static void demonstrateNullSemantics() {
        System.out.println("SQL membership and NULL");

        List<String> departments = List.of(
            "Finance",
            null
        );
    }

    static void demonstrateMembership() {
        System.out.println("SQL-style IN evaluation");

        List<String> candidates = new ArrayList<>();
        candidates.add("Finance");
        candidates.add(null);

        List<String> values = new ArrayList<>();
        values.add("Engineering");
        values.add("Finance");
        values.add("Security");
        values.add(null);

        for (String value : values) {
            SqlTruth inResult = sqlIn(value, candidates);
            SqlTruth notInResult = sqlNot(inResult);

            System.out.printf(
                "value=%s IN=%s NOT IN=%s WHERE=%s%n",
                value == null ? "NULL" : value,
                inResult,
                notInResult,
                passesWhere(notInResult)
            );
        }

        System.out.println();
    }

    static void demonstrateGovernanceModel() {
        System.out.println("Enterprise merge policy");

        PullRequest pullRequest = new PullRequest(
            842L,
            "feature/security-policy",
            "main",
            Optional.of("atul"),
            false,
            true
        );

        List<Review> reviews = List.of(
            new Review(
                "security-reviewer",
                ReviewState.APPROVED,
                true
            ),
            new Review(
                "platform-reviewer",
                ReviewState.APPROVED,
                true
            ),
            new Review(
                "external-contributor",
                ReviewState.APPROVED,
                false
            )
        );

        List<StatusCheck> checks = List.of(
            new StatusCheck("unit-tests", true, true),
            new StatusCheck("security-scan", true, true),
            new StatusCheck("documentation-preview", false, false)
        );

        BranchProtection protection = new BranchProtection(
            "main",
            2,
            true,
            true,
            true
        );

        MergeDecision decision = evaluateMerge(
            pullRequest,
            reviews,
            checks,
            protection
        );

        System.out.println(
            "Pull Request #" + pullRequest.id()
            + " -> "
            + (decision.eligible() ? "MERGE ELIGIBLE" : "BLOCKED")
        );

        decision.reasons().forEach(
            reason -> System.out.println("  " + reason)
        );

        System.out.println();
    }

    static void demonstrateReviewStatePolicy() {
        System.out.println("Review-state policy");

        EnumSet<ReviewState> blockingStates = EnumSet.of(
            ReviewState.CHANGES_REQUESTED
        );

        ReviewState currentState = ReviewState.CHANGES_REQUESTED;

        boolean blocked = blockingStates.contains(currentState);

        System.out.println(
            "Current review state: " + currentState
        );
        System.out.println(
            "Merge blocked: " + blocked
        );
        System.out.println();
    }

    public static void main(String[] args) {
        demonstrateMembership();
        demonstrateGovernanceModel();
        demonstrateReviewStatePolicy();

        System.out.println("Java demonstration complete.");
    }
}
