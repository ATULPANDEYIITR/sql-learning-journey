import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Predicate;
import java.util.stream.Collectors;

public class RepositoryAggregation {

    enum PullRequestState {
        OPEN, MERGED, CLOSED
    }

    enum MergeStrategy {
        SQUASH, MERGE, REBASE, NONE
    }

    enum ReviewState {
        APPROVED, CHANGES_REQUESTED, COMMENTED
    }

    record Review(
        String reviewer,
        ReviewState state,
        boolean eligibleReviewer,
        boolean dismissed
    ) {
        Review {
            Objects.requireNonNull(reviewer);
            Objects.requireNonNull(state);

            if (reviewer.isBlank()) {
                throw new IllegalArgumentException("Reviewer is required");
            }
        }
    }

    record StatusCheck(String name, boolean passed) {
        StatusCheck {
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException("Check name is required");
            }
        }
    }

    record PullRequest(
        int number,
        String repository,
        String author,
        String targetBranch,
        PullRequestState state,
        int additions,
        int deletions,
        int commits,
        List<Review> reviews,
        List<StatusCheck> checks,
        MergeStrategy mergeStrategy,
        Instant openedAt,
        Instant mergedAt
    ) {
        PullRequest {
            if (number <= 0) {
                throw new IllegalArgumentException("PR number must be positive");
            }

            Objects.requireNonNull(repository);
            Objects.requireNonNull(author);
            Objects.requireNonNull(targetBranch);
            Objects.requireNonNull(state);
            Objects.requireNonNull(reviews);
            Objects.requireNonNull(checks);
            Objects.requireNonNull(mergeStrategy);
            Objects.requireNonNull(openedAt);

            if (additions < 0 || deletions < 0 || commits < 0) {
                throw new IllegalArgumentException(
                    "Change and commit counts cannot be negative"
                );
            }

            if (state == PullRequestState.MERGED && mergedAt == null) {
                throw new IllegalArgumentException(
                    "Merged PR requires a merge timestamp"
                );
            }

            if (mergedAt != null && mergedAt.isBefore(openedAt)) {
                throw new IllegalArgumentException(
                    "Merge timestamp cannot precede opening timestamp"
                );
            }

            reviews = List.copyOf(reviews);
            checks = List.copyOf(checks);
        }

        int changes() {
            return additions + deletions;
        }

        long reviewCount() {
            return reviews.size();
        }

        long activeApprovals() {
            return reviews.stream()
                .filter(review ->
                    review.state() == ReviewState.APPROVED
                    && review.eligibleReviewer()
                    && !review.dismissed()
                )
                .count();
        }

        boolean checksPassed() {
            return checks.stream().allMatch(StatusCheck::passed);
        }

        double cycleHours() {
            if (mergedAt == null) {
                return 0.0;
            }
            return Duration.between(openedAt, mergedAt).toSeconds() / 3600.0;
        }
    }

    record RepositoryAggregate(
        int pullRequests,
        long merged,
        long totalChanges,
        double averageReviews,
        double averageApprovals,
        double averageCycleHours,
        long largePullRequests
    ) {}

    record GovernancePolicy(
        int requiredApprovals,
        boolean requirePassingChecks,
        boolean requireNoRequestedChanges
    ) {
        GovernancePolicy {
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "Required approvals cannot be negative"
                );
            }
        }
    }

    static boolean mergeEligible(
        PullRequest pr,
        GovernancePolicy policy
    ) {
        if (pr.state() != PullRequestState.OPEN) {
            return false;
        }

        if (policy.requirePassingChecks() && !pr.checksPassed()) {
            return false;
        }

        if (pr.activeApprovals() < policy.requiredApprovals()) {
            return false;
        }

        if (policy.requireNoRequestedChanges()
            && pr.reviews().stream().anyMatch(review ->
                review.state() == ReviewState.CHANGES_REQUESTED
                && !review.dismissed())) {
            return false;
        }

        return true;
    }

    static Map<String, RepositoryAggregate> aggregateRepositories(
        List<PullRequest> pullRequests
    ) {
        return pullRequests.stream()
            .collect(Collectors.groupingBy(
                PullRequest::repository,
                Collectors.collectingAndThen(
                    Collectors.toList(),
                    RepositoryAggregation::calculateRepositoryAggregate
                )
            ));
    }

    static RepositoryAggregate calculateRepositoryAggregate(
        List<PullRequest> prs
    ) {
        long merged = prs.stream()
            .filter(pr -> pr.state() == PullRequestState.MERGED)
            .count();

        long totalChanges = prs.stream()
            .mapToLong(PullRequest::changes)
            .sum();

        double averageReviews = prs.stream()
            .mapToLong(PullRequest::reviewCount)
            .average()
            .orElse(0);

        double averageApprovals = prs.stream()
            .mapToLong(PullRequest::activeApprovals)
            .average()
            .orElse(0);

        double averageCycle = prs.stream()
            .filter(pr -> pr.mergedAt() != null)
            .mapToDouble(PullRequest::cycleHours)
            .average()
            .orElse(0);

        long largePullRequests = prs.stream()
            .filter(pr -> pr.changes() >= 500)
            .count();

        return new RepositoryAggregate(
            prs.size(),
            merged,
            totalChanges,
            averageReviews,
            averageApprovals,
            averageCycle,
            largePullRequests
        );
    }

    static <T> long conditionalCount(
        List<PullRequest> prs,
        Predicate<PullRequest> condition
    ) {
        return prs.stream().filter(condition).count();
    }

    static EnumMap<MergeStrategy, Long> strategyAggregation(
        List<PullRequest> prs
    ) {
        EnumMap<MergeStrategy, Long> result =
            new EnumMap<>(MergeStrategy.class);

        for (MergeStrategy strategy : MergeStrategy.values()) {
            long count = prs.stream()
                .filter(pr -> pr.state() == PullRequestState.MERGED)
                .filter(pr -> pr.mergeStrategy() == strategy)
                .count();

            if (count > 0) {
                result.put(strategy, count);
            }
        }

        return result;
    }

    static Map<String, Long> reviewStateAggregation(
        List<PullRequest> prs
    ) {
        return prs.stream()
            .flatMap(pr -> pr.reviews().stream())
            .collect(Collectors.groupingBy(
                review -> review.state().name(),
                Collectors.counting()
            ));
    }

    public static void main(String[] args) {
        Instant base = Instant.parse("2026-10-01T09:00:00Z");

        List<PullRequest> prs = new ArrayList<>();

        prs.add(new PullRequest(
            101, "payments-api", "alice", "main",
            PullRequestState.MERGED, 420, 80, 6,
            List.of(
                new Review("ravi", ReviewState.APPROVED, true, false),
                new Review("meera", ReviewState.APPROVED, true, false),
                new Review("sam", ReviewState.COMMENTED, true, false)
            ),
            List.of(
                new StatusCheck("tests", true),
                new StatusCheck("security", true)
            ),
            MergeStrategy.SQUASH,
            base,
            base.plus(Duration.ofHours(29))
        ));

        prs.add(new PullRequest(
            102, "payments-api", "bob", "main",
            PullRequestState.MERGED, 90, 20, 3,
            List.of(
                new Review("ravi", ReviewState.APPROVED, true, false),
                new Review("meera", ReviewState.COMMENTED, true, false)
            ),
            List.of(new StatusCheck("tests", true)),
            MergeStrategy.MERGE,
            base.plus(Duration.ofDays(1)),
            base.plus(Duration.ofDays(1)).plus(Duration.ofHours(7))
        ));

        prs.add(new PullRequest(
            103, "payments-api", "carol", "release",
            PullRequestState.CLOSED, 700, 300, 12,
            List.of(
                new Review("ravi", ReviewState.CHANGES_REQUESTED, true, false),
                new Review("sam", ReviewState.COMMENTED, true, false)
            ),
            List.of(new StatusCheck("tests", false)),
            MergeStrategy.NONE,
            base.plus(Duration.ofDays(2)),
            null
        ));

        prs.add(new PullRequest(
            104, "web-portal", "alice", "main",
            PullRequestState.MERGED, 130, 45, 4,
            List.of(
                new Review("ravi", ReviewState.APPROVED, true, false),
                new Review("meera", ReviewState.APPROVED, true, false),
                new Review("sam", ReviewState.COMMENTED, true, false)
            ),
            List.of(new StatusCheck("tests", true)),
            MergeStrategy.REBASE,
            base.plus(Duration.ofDays(3)),
            base.plus(Duration.ofDays(4)).plus(Duration.ofHours(23))
        ));

        prs.add(new PullRequest(
            105, "web-portal", "david", "main",
            PullRequestState.OPEN, 35, 8, 2,
            List.of(
                new Review("ravi", ReviewState.COMMENTED, true, false)
            ),
            List.of(new StatusCheck("tests", true)),
            MergeStrategy.NONE,
            base.plus(Duration.ofDays(5)),
            null
        ));

        prs.add(new PullRequest(
            106, "web-portal", "carol", "develop",
            PullRequestState.MERGED, 250, 120, 7,
            List.of(
                new Review("ravi", ReviewState.APPROVED, true, false),
                new Review("meera", ReviewState.APPROVED, true, false),
                new Review("sam", ReviewState.APPROVED, true, false),
                new Review("lee", ReviewState.COMMENTED, false, false)
            ),
            List.of(
                new StatusCheck("tests", true),
                new StatusCheck("lint", true)
            ),
            MergeStrategy.SQUASH,
            base.plus(Duration.ofDays(6)),
            base.plus(Duration.ofDays(7)).plus(Duration.ofHours(6))
        ));

        GovernancePolicy policy =
            new GovernancePolicy(2, true, true);

        Map<String, RepositoryAggregate> repositoryReport =
            aggregateRepositories(prs);

        System.out.println("Repository aggregation");

        repositoryReport.forEach((repository, metrics) -> {
            System.out.printf(
                "%n%s%n  PRs: %d%n  Merged: %d%n" +
                "  Total changes: %d%n" +
                "  Average reviews: %.2f%n" +
                "  Average active approvals: %.2f%n" +
                "  Average cycle hours: %.2f%n" +
                "  Large PRs: %d%n",
                repository,
                metrics.pullRequests(),
                metrics.merged(),
                metrics.totalChanges(),
                metrics.averageReviews(),
                metrics.averageApprovals(),
                metrics.averageCycleHours(),
                metrics.largePullRequests()
            );
        });

        System.out.println("\nConditional aggregation");

        long mergeEligible = conditionalCount(
            prs,
            pr -> mergeEligible(pr, policy)
        );

        long failedChecks = conditionalCount(
            prs,
            pr -> !pr.checksPassed()
        );

        long largeMerged = conditionalCount(
            prs,
            pr -> pr.state() == PullRequestState.MERGED
                && pr.changes() >= 500
        );

        System.out.println("Merge eligible: " + mergeEligible);
        System.out.println("Failed-check PRs: " + failedChecks);
        System.out.println("Large merged PRs: " + largeMerged);

        System.out.println("\nMerge strategy aggregation");
        strategyAggregation(prs).forEach(
            (strategy, count) ->
                System.out.println(strategy + ": " + count)
        );

        System.out.println("\nReview-state aggregation");
        reviewStateAggregation(prs).forEach(
            (state, count) ->
                System.out.println(state + ": " + count)
        );

        System.out.println("\nMerge eligibility");
        prs.forEach(pr ->
            System.out.printf(
                "PR #%d: %s%n",
                pr.number(),
                mergeEligible(pr, policy)
                    ? "eligible"
                    : "blocked"
            )
        );
    }
}
