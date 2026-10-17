import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;

public class AdvancedAggregationDemo {

    enum PullRequestState {
        OPEN,
        MERGED,
        CLOSED
    }

    enum ChangeCategory {
        FEATURE,
        BUGFIX,
        SECURITY,
        PERFORMANCE
    }

    record PullRequest(
        int id,
        String repository,
        String team,
        ChangeCategory category,
        PullRequestState state,
        int additions,
        int deletions,
        int reviewerCount,
        int approvalCount,
        boolean checksPassed
    ) {
        PullRequest {
            if (id <= 0) {
                throw new IllegalArgumentException("Pull Request ID must be positive");
            }

            Objects.requireNonNull(repository, "repository");
            Objects.requireNonNull(team, "team");
            Objects.requireNonNull(category, "category");
            Objects.requireNonNull(state, "state");

            if (additions < 0 || deletions < 0) {
                throw new IllegalArgumentException("Line counts cannot be negative");
            }

            if (reviewerCount < 0 || approvalCount < 0) {
                throw new IllegalArgumentException(
                    "Reviewer and approval counts cannot be negative"
                );
            }

            if (approvalCount > reviewerCount) {
                throw new IllegalArgumentException(
                    "Approval count cannot exceed reviewer count"
                );
            }
        }

        int changedLines() {
            return additions + deletions;
        }

        double approvalCoverage() {
            return reviewerCount == 0
                ? 0.0
                : (double) approvalCount / reviewerCount;
        }
    }

    record RepositoryMetrics(
        long count,
        long merged,
        long open,
        long closed,
        long failedChecks,
        long largeChanges,
        long totalAdditions,
        long totalDeletions,
        double approvalCoverage
    ) {
        double mergeRate() {
            return count == 0 ? 0.0 : (double) merged / count;
        }

        double checkPassRate() {
            return count == 0
                ? 0.0
                : 1.0 - ((double) failedChecks / count);
        }

        double averageChangedLines() {
            return count == 0
                ? 0.0
                : (double) (totalAdditions + totalDeletions) / count;
        }
    }

    record GovernancePolicy(
        long minimumMerged,
        double minimumApprovalCoverage,
        double minimumCheckPassRate
    ) {}

    record GovernanceDecision(
        String repository,
        boolean eligible,
        String reason
    ) {}

    static List<PullRequest> samplePullRequests() {
        return List.of(
            new PullRequest(
                1001, "platform-api", "Core",
                ChangeCategory.FEATURE, PullRequestState.MERGED,
                420, 90, 2, 2, true
            ),
            new PullRequest(
                1002, "platform-api", "Core",
                ChangeCategory.BUGFIX, PullRequestState.MERGED,
                80, 40, 1, 1, true
            ),
            new PullRequest(
                1003, "identity-service", "Security",
                ChangeCategory.SECURITY, PullRequestState.MERGED,
                260, 30, 3, 3, true
            ),
            new PullRequest(
                1004, "identity-service", "Security",
                ChangeCategory.BUGFIX, PullRequestState.OPEN,
                120, 70, 2, 1, true
            ),
            new PullRequest(
                1005, "data-pipeline", "Data",
                ChangeCategory.FEATURE, PullRequestState.MERGED,
                760, 210, 3, 2, true
            ),
            new PullRequest(
                1006, "data-pipeline", "Data",
                ChangeCategory.PERFORMANCE, PullRequestState.MERGED,
                310, 190, 2, 2, true
            ),
            new PullRequest(
                1007, "platform-api", "Core",
                ChangeCategory.FEATURE, PullRequestState.OPEN,
                900, 420, 4, 2, false
            ),
            new PullRequest(
                1008, "identity-service", "Security",
                ChangeCategory.SECURITY, PullRequestState.MERGED,
                180, 20, 3, 3, true
            ),
            new PullRequest(
                1009, "data-pipeline", "Data",
                ChangeCategory.BUGFIX, PullRequestState.CLOSED,
                95, 60, 1, 0, false
            ),
            new PullRequest(
                1010, "platform-api", "Core",
                ChangeCategory.PERFORMANCE, PullRequestState.MERGED,
                500, 150, 2, 2, true
            )
        );
    }

    static RepositoryMetrics aggregateRepository(
        List<PullRequest> pullRequests
    ) {
        long count = pullRequests.size();

        long merged = pullRequests.stream()
            .filter(pr -> pr.state() == PullRequestState.MERGED)
            .count();

        long open = pullRequests.stream()
            .filter(pr -> pr.state() == PullRequestState.OPEN)
            .count();

        long closed = pullRequests.stream()
            .filter(pr -> pr.state() == PullRequestState.CLOSED)
            .count();

        long failedChecks = pullRequests.stream()
            .filter(pr -> !pr.checksPassed())
            .count();

        long largeChanges = pullRequests.stream()
            .filter(pr -> pr.changedLines() >= 500)
            .count();

        long additions = pullRequests.stream()
            .mapToLong(PullRequest::additions)
            .sum();

        long deletions = pullRequests.stream()
            .mapToLong(PullRequest::deletions)
            .sum();

        /*
         * Stream aggregation is useful for declarative calculations, while
         * the final RepositoryMetrics record keeps the result immutable.
         */
        double approvalCoverage = pullRequests.stream()
            .mapToDouble(PullRequest::approvalCoverage)
            .average()
            .orElse(0.0);

        return new RepositoryMetrics(
            count,
            merged,
            open,
            closed,
            failedChecks,
            largeChanges,
            additions,
            deletions,
            approvalCoverage
        );
    }

    static Map<String, RepositoryMetrics> aggregateByRepository(
        List<PullRequest> pullRequests
    ) {
        return pullRequests.stream()
            .collect(Collectors.groupingBy(
                PullRequest::repository,
                java.util.TreeMap::new,
                Collectors.collectingAndThen(
                    Collectors.toList(),
                    AdvancedAggregationDemo::aggregateRepository
                )
            ));
    }

    static Map<ChangeCategory, RepositoryMetrics> aggregateByCategory(
        List<PullRequest> pullRequests
    ) {
        return pullRequests.stream()
            .collect(Collectors.groupingBy(
                PullRequest::category,
                () -> new EnumMap<>(ChangeCategory.class),
                Collectors.collectingAndThen(
                    Collectors.toList(),
                    AdvancedAggregationDemo::aggregateRepository
                )
            ));
    }

    static Map<PullRequestState, Long> conditionalStateCounts(
        List<PullRequest> pullRequests
    ) {
        return pullRequests.stream()
            .collect(Collectors.groupingBy(
                PullRequest::state,
                () -> new EnumMap<>(PullRequestState.class),
                Collectors.counting()
            ));
    }

    static Map<String, Long> conditionalSecurityMetrics(
        List<PullRequest> pullRequests
    ) {
        /*
         * This intentionally applies different predicates to the same
         * population. It represents conditional aggregation rather than
         * simply grouping every record by one field.
         */
        return Map.of(
            "securityChanges",
            pullRequests.stream()
                .filter(pr -> pr.category() == ChangeCategory.SECURITY)
                .count(),

            "largeSecurityChanges",
            pullRequests.stream()
                .filter(pr ->
                    pr.category() == ChangeCategory.SECURITY
                        && pr.changedLines() >= 500
                )
                .count(),

            "mergedSecurityChanges",
            pullRequests.stream()
                .filter(pr ->
                    pr.category() == ChangeCategory.SECURITY
                        && pr.state() == PullRequestState.MERGED
                )
                .count(),

            "failedSecurityChecks",
            pullRequests.stream()
                .filter(pr ->
                    pr.category() == ChangeCategory.SECURITY
                        && !pr.checksPassed()
                )
                .count()
        );
    }

    static List<GovernanceDecision> evaluateGovernance(
        Map<String, RepositoryMetrics> metrics,
        GovernancePolicy policy
    ) {
        List<GovernanceDecision> decisions = new ArrayList<>();

        for (Map.Entry<String, RepositoryMetrics> entry : metrics.entrySet()) {
            RepositoryMetrics metric = entry.getValue();

            boolean enoughMerged =
                metric.merged() >= policy.minimumMerged();

            boolean enoughApprovalCoverage =
                metric.approvalCoverage()
                    >= policy.minimumApprovalCoverage();

            boolean checksHealthy =
                metric.checkPassRate()
                    >= policy.minimumCheckPassRate();

            boolean eligible =
                enoughMerged
                    && enoughApprovalCoverage
                    && checksHealthy;

            String reason;

            if (eligible) {
                reason = "All aggregate governance thresholds are satisfied";
            } else if (!enoughMerged) {
                reason = "Insufficient merged changes";
            } else if (!enoughApprovalCoverage) {
                reason = "Approval coverage is below policy";
            } else {
                reason = "Required check pass rate is below policy";
            }

            decisions.add(
                new GovernanceDecision(
                    entry.getKey(),
                    eligible,
                    reason
                )
            );
        }

        return decisions;
    }

    static void printRepositoryMetrics(
        Map<String, RepositoryMetrics> metrics
    ) {
        System.out.println("\nRepository Aggregation");
        System.out.println("----------------------");

        metrics.forEach((repository, metric) -> {
            System.out.printf(
                "%-20s count=%d merged=%d open=%d failedChecks=%d "
                    + "avgChangedLines=%.2f approvalCoverage=%.2f%n",
                repository,
                metric.count(),
                metric.merged(),
                metric.open(),
                metric.failedChecks(),
                metric.averageChangedLines(),
                metric.approvalCoverage()
            );
        });
    }

    static void printCategoryMetrics(
        Map<ChangeCategory, RepositoryMetrics> metrics
    ) {
        System.out.println("\nCategory Aggregation");
        System.out.println("--------------------");

        metrics.forEach((category, metric) -> {
            System.out.printf(
                "%-15s count=%d merged=%d largeChanges=%d "
                    + "changedLines=%d%n",
                category,
                metric.count(),
                metric.merged(),
                metric.largeChanges(),
                metric.totalAdditions() + metric.totalDeletions()
            );
        });
    }

    public static void main(String[] args) {
        try {
            List<PullRequest> pullRequests = samplePullRequests();

            Map<String, RepositoryMetrics> repositoryMetrics =
                aggregateByRepository(pullRequests);

            Map<ChangeCategory, RepositoryMetrics> categoryMetrics =
                aggregateByCategory(pullRequests);

            printRepositoryMetrics(repositoryMetrics);
            printCategoryMetrics(categoryMetrics);

            System.out.println("\nConditional State Counts");
            System.out.println("------------------------");
            conditionalStateCounts(pullRequests)
                .forEach((state, count) ->
                    System.out.println(state + " = " + count)
                );

            System.out.println("\nSecurity Conditional Metrics");
            System.out.println("----------------------------");
            conditionalSecurityMetrics(pullRequests)
                .forEach((metric, value) ->
                    System.out.println(metric + " = " + value)
                );

            GovernancePolicy policy =
                new GovernancePolicy(2, 0.75, 0.80);

            System.out.println("\nGovernance Decisions");
            System.out.println("--------------------");

            evaluateGovernance(repositoryMetrics, policy)
                .forEach(decision ->
                    System.out.printf(
                        "%-20s eligible=%-5s reason=%s%n",
                        decision.repository(),
                        decision.eligible(),
                        decision.reason()
                    )
                );

        } catch (IllegalArgumentException error) {
            System.err.println(
                "Invalid aggregation input: " + error.getMessage()
            );
        }
    }
}
