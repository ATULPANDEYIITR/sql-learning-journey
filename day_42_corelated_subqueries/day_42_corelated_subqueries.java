import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.Predicate;
import java.util.stream.Collectors;

public class CorrelatedSubqueryGovernance {

    enum ReviewState {
        APPROVED,
        COMMENTED,
        CHANGES_REQUESTED
    }

    enum CheckState {
        SUCCESS,
        FAILURE,
        PENDING
    }

    record PullRequest(
        int id,
        int number,
        String title,
        String author,
        String sourceBranch,
        String targetBranch,
        boolean draft
    ) {}

    record Review(
        int id,
        int pullRequestId,
        String reviewer,
        ReviewState state
    ) {}

    record StatusCheck(
        int pullRequestId,
        String name,
        CheckState state
    ) {}

    record ReviewComment(
        int id,
        int pullRequestId,
        String reviewer,
        String body,
        boolean resolved
    ) {}

    record BranchProtection(
        String branch,
        int requiredApprovals,
        Set<String> requiredChecks,
        boolean requireResolvedConversations,
        boolean allowForcePush,
        boolean allowDeletion,
        boolean requireLinearHistory
    ) {
        BranchProtection {
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "Required approvals cannot be negative"
                );
            }

            requiredChecks = Set.copyOf(requiredChecks);
        }
    }

    record MergeDecision(
        boolean eligible,
        List<String> reasons
    ) {}


    /*
     * A correlated EXISTS operation.
     *
     * SQL equivalent:
     *
     * WHERE EXISTS (
     *     SELECT 1
     *     FROM reviews r
     *     WHERE r.pull_request_id = p.id
     *       AND r.state = 'APPROVED'
     * )
     *
     * The Java Predicate receives both the outer PR and the inner review,
     * making the outer reference explicit.
     */
    static List<PullRequest> correlatedExists(
        List<PullRequest> pullRequests,
        List<Review> reviews,
        java.util.function.BiPredicate<PullRequest, Review> condition
    ) {
        return pullRequests.stream()
            .filter(pr ->
                reviews.stream().anyMatch(review ->
                    condition.test(pr, review)
                )
            )
            .toList();
    }


    /*
     * Correlated NOT EXISTS.
     */
    static List<PullRequest> correlatedNotExists(
        List<PullRequest> pullRequests,
        List<ReviewComment> comments,
        java.util.function.BiPredicate<PullRequest, ReviewComment> condition
    ) {
        return pullRequests.stream()
            .filter(pr ->
                comments.stream().noneMatch(comment ->
                    condition.test(pr, comment)
                )
            )
            .toList();
    }


    /*
     * Correlated COUNT.
     *
     * The grouping key is deliberately derived from the outer row. This
     * models a scalar correlated aggregate without pretending that Java
     * streams are themselves SQL.
     */
    static Map<Integer, Long> correlatedReviewCounts(
        List<PullRequest> pullRequests,
        List<Review> reviews
    ) {
        Map<Integer, Long> counts = new HashMap<>();

        for (PullRequest pr : pullRequests) {
            long count = reviews.stream()
                .filter(review -> review.pullRequestId() == pr.id())
                .count();

            counts.put(pr.id(), count);
        }

        return counts;
    }


    /*
     * A domain service makes the relationship between approvals and
     * repository policy explicit.
     *
     * An approval is not merely a row with state APPROVED. The service also
     * excludes self-approval, because the current PR supplies the author
     * value used by the inner review evaluation.
     */
    static int countValidApprovals(
        PullRequest pr,
        List<Review> reviews
    ) {
        return (int) reviews.stream()
            .filter(review ->
                review.pullRequestId() == pr.id()
                    && review.state() == ReviewState.APPROVED
                    && !review.reviewer().equals(pr.author())
            )
            .count();
    }


    static boolean requiredCheckSucceeded(
        PullRequest pr,
        String requiredCheck,
        List<StatusCheck> checks
    ) {
        return checks.stream().anyMatch(check ->
            check.pullRequestId() == pr.id()
                && check.name().equals(requiredCheck)
                && check.state() == CheckState.SUCCESS
        );
    }


    static boolean hasUnresolvedConversation(
        PullRequest pr,
        List<ReviewComment> comments
    ) {
        return comments.stream().anyMatch(comment ->
            comment.pullRequestId() == pr.id()
                && !comment.resolved()
        );
    }


    /*
     * Enterprise merge-eligibility service.
     *
     * Pull Request state, review evaluation, approval semantics, and branch
     * protection are intentionally kept as separate domain concerns.
     */
    static MergeDecision evaluateMergeEligibility(
        PullRequest pr,
        List<Review> reviews,
        List<StatusCheck> checks,
        List<ReviewComment> comments,
        BranchProtection policy
    ) {
        Objects.requireNonNull(pr);
        Objects.requireNonNull(policy);

        List<String> reasons = new ArrayList<>();

        if (pr.draft()) {
            reasons.add("Pull Request is a draft.");
        }

        int approvals = countValidApprovals(pr, reviews);

        if (approvals < policy.requiredApprovals()) {
            reasons.add(
                "Requires "
                    + policy.requiredApprovals()
                    + " approval(s), but has "
                    + approvals
                    + "."
            );
        }

        for (String requiredCheck : policy.requiredChecks()) {
            if (!requiredCheckSucceeded(pr, requiredCheck, checks)) {
                reasons.add(
                    "Required status check is not successful: "
                        + requiredCheck
                );
            }
        }

        if (
            policy.requireResolvedConversations()
                && hasUnresolvedConversation(pr, comments)
        ) {
            reasons.add(
                "Unresolved review conversations remain."
            );
        }

        return new MergeDecision(
            reasons.isEmpty(),
            List.copyOf(reasons)
        );
    }


    /*
     * This method represents nested correlation:
     *
     * PR -> Review -> Reviewer directory entry
     *
     * The reviewer lookup depends on the review associated with the current
     * PR, and the review itself depends on the current PR.
     */
    static boolean hasEligibleReviewerApproval(
        PullRequest pr,
        List<Review> reviews,
        Set<String> eligibleReviewers
    ) {
        return reviews.stream().anyMatch(review ->
            review.pullRequestId() == pr.id()
                && review.state() == ReviewState.APPROVED
                && eligibleReviewers.contains(review.reviewer())
        );
    }


    /*
     * This Map is an application-level analogue of an index on
     * reviews.pull_request_id.
     *
     * It avoids scanning every review for every PR when the same relationship
     * is evaluated repeatedly.
     */
    static Map<Integer, List<Review>> buildReviewIndex(
        List<Review> reviews
    ) {
        return reviews.stream()
            .collect(Collectors.groupingBy(Review::pullRequestId));
    }


    static void demonstrateCorrelatedOperations(
        List<PullRequest> pullRequests,
        List<Review> reviews,
        List<ReviewComment> comments
    ) {
        System.out.println("=== Correlated EXISTS ===");

        List<PullRequest> approved =
            correlatedExists(
                pullRequests,
                reviews,
                (pr, review) ->
                    review.pullRequestId() == pr.id()
                        && review.state() == ReviewState.APPROVED
            );

        approved.forEach(pr ->
            System.out.println(
                "PR #" + pr.number() + ": " + pr.title()
            )
        );

        System.out.println("\n=== Correlated NOT EXISTS ===");

        correlatedNotExists(
            pullRequests,
            comments,
            (pr, comment) ->
                comment.pullRequestId() == pr.id()
                    && !comment.resolved()
        ).forEach(pr ->
            System.out.println(
                "PR #" + pr.number()
                    + ": no unresolved conversations"
            )
        );

        System.out.println("\n=== Correlated COUNT ===");

        Map<Integer, Long> counts =
            correlatedReviewCounts(pullRequests, reviews);

        pullRequests.forEach(pr ->
            System.out.println(
                "PR #" + pr.number()
                    + ": " + counts.get(pr.id())
                    + " review(s)"
            )
        );
    }


    static void demonstrateGovernance(
        List<PullRequest> pullRequests,
        List<Review> reviews,
        List<StatusCheck> checks,
        List<ReviewComment> comments,
        BranchProtection policy
    ) {
        System.out.println("\n=== Branch protection evaluation ===");

        for (PullRequest pr : pullRequests) {
            MergeDecision decision =
                evaluateMergeEligibility(
                    pr,
                    reviews,
                    checks,
                    comments,
                    policy
                );

            System.out.println(
                "PR #" + pr.number()
                    + ": "
                    + (decision.eligible()
                        ? "MERGE ELIGIBLE"
                        : "BLOCKED")
            );

            decision.reasons().forEach(reason ->
                System.out.println("  " + reason)
            );
        }
    }


    public static void main(String[] args) {
        List<PullRequest> pullRequests = List.of(
            new PullRequest(
                101,
                41,
                "Add transaction reconciliation",
                "david",
                "feature/reconciliation",
                "main",
                false
            ),
            new PullRequest(
                102,
                42,
                "Improve payment timeout handling",
                "alice",
                "fix/payment-timeout",
                "main",
                false
            ),
            new PullRequest(
                103,
                43,
                "Refactor settlement validation",
                "bob",
                "refactor/settlement",
                "main",
                true
            )
        );

        List<Review> reviews = List.of(
            new Review(
                1,
                101,
                "alice",
                ReviewState.APPROVED
            ),
            new Review(
                2,
                101,
                "bob",
                ReviewState.COMMENTED
            ),
            new Review(
                3,
                102,
                "carol",
                ReviewState.APPROVED
            ),
            new Review(
                4,
                103,
                "alice",
                ReviewState.CHANGES_REQUESTED
            )
        );

        List<StatusCheck> checks = List.of(
            new StatusCheck(
                101,
                "unit-tests",
                CheckState.SUCCESS
            ),
            new StatusCheck(
                101,
                "security-scan",
                CheckState.SUCCESS
            ),
            new StatusCheck(
                102,
                "unit-tests",
                CheckState.SUCCESS
            ),
            new StatusCheck(
                102,
                "security-scan",
                CheckState.FAILURE
            )
        );

        List<ReviewComment> comments = List.of(
            new ReviewComment(
                1,
                101,
                "bob",
                "Document the reconciliation fallback.",
                false
            ),
            new ReviewComment(
                2,
                102,
                "carol",
                "Timeout handling looks correct.",
                true
            )
        );

        BranchProtection mainProtection =
            new BranchProtection(
                "main",
                1,
                Set.of("unit-tests", "security-scan"),
                true,
                false,
                false,
                true
            );

        System.out.println(
            "Repository: payments-service"
        );
        System.out.println(
            "Correlated Subquery Governance Model\n"
        );

        demonstrateCorrelatedOperations(
            pullRequests,
            reviews,
            comments
        );

        demonstrateGovernance(
            pullRequests,
            reviews,
            checks,
            comments,
            mainProtection
        );

        Set<String> eligibleReviewers =
            Set.of("alice", "carol");

        System.out.println(
            "\n=== Nested correlated reviewer validation ==="
        );

        for (PullRequest pr : pullRequests) {
            System.out.println(
                "PR #" + pr.number()
                    + ": "
                    + (
                        hasEligibleReviewerApproval(
                            pr,
                            reviews,
                            eligibleReviewers
                        )
                            ? "eligible approval found"
                            : "no eligible approval"
                    )
            );
        }

        Map<Integer, List<Review>> reviewIndex =
            buildReviewIndex(reviews);

        System.out.println(
            "\n=== Indexed alternative ==="
        );

        for (PullRequest pr : pullRequests) {
            List<Review> related =
                reviewIndex.getOrDefault(
                    pr.id(),
                    Collections.emptyList()
                );

            long approvals = related.stream()
                .filter(review ->
                    review.state() == ReviewState.APPROVED
                )
                .count();

            System.out.println(
                "PR #" + pr.number()
                    + ": "
                    + approvals
                    + " approval(s) through indexed lookup"
            );
        }

        System.out.println(
            "\nThe logical correlated dependency is distinct from "
                + "the physical execution plan. A database may transform "
                + "a correlated query into a more efficient join or "
                + "semi-join when the transformation preserves semantics."
        );
    }
}
