import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.stream.IntStream;

public class LagLeadEnterpriseAnalysis {

    enum Trend {
        UP, DOWN, FLAT, UNKNOWN
    }

    enum ReviewState {
        PENDING, APPROVED, CHANGES_REQUESTED, DISMISSED
    }

    enum PullRequestState {
        DRAFT, OPEN, MERGED, CLOSED
    }

    record Metric(LocalDate date, double value) {
        Metric {
            Objects.requireNonNull(date, "date cannot be null");

            if (!Double.isFinite(value)) {
                throw new IllegalArgumentException("value must be finite");
            }
        }
    }

    record NeighborComparison(
        LocalDate date,
        double value,
        Double lag,
        Double lead,
        Double lagDifference,
        Double leadDifference,
        Trend lagTrend,
        Trend leadTrend
    ) {}

    record Review(
        String reviewer,
        ReviewState state,
        boolean eligible
    ) {
        Review {
            Objects.requireNonNull(reviewer);
            Objects.requireNonNull(state);

            if (reviewer.isBlank()) {
                throw new IllegalArgumentException("reviewer cannot be blank");
            }
        }
    }

    record StatusCheck(String name, boolean passed) {}

    record BranchPolicy(
        String protectedBranch,
        int requiredApprovals,
        boolean requirePassingChecks,
        boolean requireResolvedConversations,
        boolean requireLinearHistory,
        boolean blockDirectPush,
        boolean blockForcePush
    ) {
        BranchPolicy {
            if (protectedBranch == null || protectedBranch.isBlank()) {
                throw new IllegalArgumentException("protectedBranch is required");
            }

            if (requiredApprovals < 0) {
                throw new IllegalArgumentException("requiredApprovals cannot be negative");
            }
        }
    }

    static final class PullRequest {
        private final int id;
        private final String sourceBranch;
        private final String targetBranch;
        private final PullRequestState state;
        private final List<Review> reviews;
        private final List<StatusCheck> statusChecks;
        private final boolean conversationsResolved;
        private final boolean mergeConflict;

        PullRequest(
            int id,
            String sourceBranch,
            String targetBranch,
            PullRequestState state,
            List<Review> reviews,
            List<StatusCheck> statusChecks,
            boolean conversationsResolved,
            boolean mergeConflict
        ) {
            if (id <= 0) {
                throw new IllegalArgumentException("Pull Request id must be positive");
            }

            this.id = id;
            this.sourceBranch = Objects.requireNonNull(sourceBranch);
            this.targetBranch = Objects.requireNonNull(targetBranch);
            this.state = Objects.requireNonNull(state);
            this.reviews = List.copyOf(reviews);
            this.statusChecks = List.copyOf(statusChecks);
            this.conversationsResolved = conversationsResolved;
            this.mergeConflict = mergeConflict;
        }

        int id() {
            return id;
        }

        String targetBranch() {
            return targetBranch;
        }

        PullRequestState state() {
            return state;
        }

        List<Review> reviews() {
            return reviews;
        }

        List<StatusCheck> statusChecks() {
            return statusChecks;
        }

        boolean conversationsResolved() {
            return conversationsResolved;
        }

        boolean mergeConflict() {
            return mergeConflict;
        }
    }

    record MergeDecision(boolean eligible, List<String> reasons) {
        MergeDecision {
            reasons = List.copyOf(reasons);
        }
    }

    static final class TimeSeriesService {

        List<NeighborComparison> compare(List<Metric> input) {
            validate(input);

            return IntStream.range(0, input.size())
                .mapToObj(index -> {
                    Metric current = input.get(index);

                    Double lag = index > 0
                        ? input.get(index - 1).value()
                        : null;

                    Double lead = index + 1 < input.size()
                        ? input.get(index + 1).value()
                        : null;

                    return new NeighborComparison(
                        current.date(),
                        current.value(),
                        lag,
                        lead,
                        lag == null ? null : current.value() - lag,
                        lead == null ? null : lead - current.value(),
                        classify(current.value(), lag),
                        classify(lead, current.value())
                    );
                })
                .toList();
        }

        List<Metric> localPeaks(List<Metric> metrics) {
            validate(metrics);

            if (metrics.size() < 3) {
                return List.of();
            }

            List<Metric> peaks = new ArrayList<>();

            for (int index = 1; index < metrics.size() - 1; index++) {
                double previous = metrics.get(index - 1).value();
                double current = metrics.get(index).value();
                double next = metrics.get(index + 1).value();

                if (current > previous && current > next) {
                    peaks.add(metrics.get(index));
                }
            }

            return List.copyOf(peaks);
        }

        private void validate(List<Metric> metrics) {
            if (metrics == null || metrics.isEmpty()) {
                throw new IllegalArgumentException("Metrics cannot be empty");
            }

            Set<LocalDate> dates = new HashSet<>();

            for (Metric metric : metrics) {
                Objects.requireNonNull(metric);

                if (!dates.add(metric.date())) {
                    throw new IllegalArgumentException(
                        "Duplicate date: " + metric.date()
                    );
                }
            }

            for (int i = 1; i < metrics.size(); i++) {
                if (metrics.get(i - 1).date().isAfter(metrics.get(i).date())) {
                    throw new IllegalArgumentException(
                        "Metrics must be ordered chronologically"
                    );
                }
            }
        }

        private static Trend classify(Double current, Double reference) {
            if (current == null || reference == null) {
                return Trend.UNKNOWN;
            }

            return current > reference
                ? Trend.UP
                : current < reference
                    ? Trend.DOWN
                    : Trend.FLAT;
        }
    }

    static final class GovernanceService {

        MergeDecision evaluate(PullRequest pr, BranchPolicy policy) {
            List<String> reasons = new ArrayList<>();

            if (!pr.targetBranch().equals(policy.protectedBranch())) {
                reasons.add("Pull Request does not target the protected branch");
            }

            if (pr.state() != PullRequestState.OPEN) {
                reasons.add("Pull Request is not open");
            }

            if (pr.mergeConflict()) {
                reasons.add("Merge conflict exists");
            }

            if (policy.requireResolvedConversations()
                && !pr.conversationsResolved()) {
                reasons.add("Review conversations are unresolved");
            }

            long approvals = pr.reviews()
                .stream()
                .filter(review ->
                    review.eligible()
                    && review.state() == ReviewState.APPROVED
                )
                .count();

            if (approvals < policy.requiredApprovals()) {
                reasons.add(
                    "Eligible approvals: " + approvals
                    + ", required: " + policy.requiredApprovals()
                );
            }

            if (policy.requirePassingChecks()) {
                boolean allPassed = !pr.statusChecks().isEmpty()
                    && pr.statusChecks().stream().allMatch(StatusCheck::passed);

                if (!allPassed) {
                    reasons.add("One or more required status checks are not passing");
                }
            }

            return new MergeDecision(reasons.isEmpty(), reasons);
        }
    }

    public static void main(String[] args) {
        List<Metric> metrics = List.of(
            new Metric(LocalDate.of(2026, 10, 19), 120),
            new Metric(LocalDate.of(2026, 10, 20), 126),
            new Metric(LocalDate.of(2026, 10, 21), 131),
            new Metric(LocalDate.of(2026, 10, 22), 127),
            new Metric(LocalDate.of(2026, 10, 23), 135),
            new Metric(LocalDate.of(2026, 10, 24), 135),
            new Metric(LocalDate.of(2026, 10, 25), 142)
        );

        TimeSeriesService timeSeriesService = new TimeSeriesService();

        List<NeighborComparison> comparisons =
            timeSeriesService.compare(metrics);

        System.out.println("DATE        VALUE   LAG       LEAD      LAG TREND  LEAD TREND");
        System.out.println("---------------------------------------------------------------");

        comparisons.forEach(row -> System.out.printf(
            "%s  %6.2f  %7s  %8s  %9s  %10s%n",
            row.date(),
            row.value(),
            row.lag() == null ? "-" : String.format("%.2f", row.lag()),
            row.lead() == null ? "-" : String.format("%.2f", row.lead()),
            row.lagTrend(),
            row.leadTrend()
        ));

        System.out.println("\nLocal peaks:");
        timeSeriesService.localPeaks(metrics)
            .forEach(metric ->
                System.out.printf("%s -> %.2f%n", metric.date(), metric.value())
            );

        PullRequest pullRequest = new PullRequest(
            7001,
            "feature/revenue-model",
            "main",
            PullRequestState.OPEN,
            List.of(
                new Review("alice", ReviewState.APPROVED, true),
                new Review("bob", ReviewState.APPROVED, true),
                new Review("contractor", ReviewState.APPROVED, false),
                new Review("carol", ReviewState.DISMISSED, true)
            ),
            List.of(
                new StatusCheck("unit-tests", true),
                new StatusCheck("integration-tests", true),
                new StatusCheck("security-scan", true)
            ),
            true,
            false
        );

        BranchPolicy policy = new BranchPolicy(
            "main",
            2,
            true,
            true,
            true,
            true,
            true
        );

        GovernanceService governanceService = new GovernanceService();
        MergeDecision decision =
            governanceService.evaluate(pullRequest, policy);

        System.out.println("\nMerge eligibility: "
            + (decision.eligible() ? "ELIGIBLE" : "BLOCKED"));

        decision.reasons().forEach(reason ->
            System.out.println("- " + reason)
        );

        /*
         * EnumSet is suitable for compact policy-state sets when a policy
         * evolves into multiple independent flags. The explicit records above
         * keep persisted domain values immutable and auditable.
         */
        System.out.println(
            "\nSupported review states: "
            + EnumSet.allOf(ReviewState.class)
        );

        // The immutable collections prevent callers from changing governance state.
        System.out.println(
            "Protected branch: " + policy.protectedBranch()
        );
    }
}
