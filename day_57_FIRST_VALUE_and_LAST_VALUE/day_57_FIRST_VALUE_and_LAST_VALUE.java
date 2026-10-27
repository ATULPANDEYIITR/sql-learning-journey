import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class WindowValueDemo {

    enum MetricType {
        DEPLOYMENTS
    }

    record Observation(
            String repository,
            Instant observedAt,
            MetricType metric,
            long value) {

        Observation {
            if (repository == null || repository.isBlank()) {
                throw new IllegalArgumentException("Repository is required.");
            }
            if (observedAt == null) {
                throw new IllegalArgumentException("Observation time is required.");
            }
            if (metric == null) {
                throw new IllegalArgumentException("Metric is required.");
            }
            if (value < 0) {
                throw new IllegalArgumentException("Metric value cannot be negative.");
            }
        }
    }

    record WindowResult(
            Observation observation,
            long firstValue,
            long defaultLastValue,
            long fullPartitionLastValue,
            long framedLastValue) {
    }

    interface WindowPolicy {
        List<WindowResult> evaluate(List<Observation> observations);
    }

    static final class WindowEvaluationException extends RuntimeException {
        WindowEvaluationException(String message) {
            super(message);
        }
    }

    static final class RepositoryWindowPolicy implements WindowPolicy {
        private final int precedingRows;

        RepositoryWindowPolicy(int precedingRows) {
            if (precedingRows < 0) {
                throw new IllegalArgumentException("precedingRows cannot be negative.");
            }
            this.precedingRows = precedingRows;
        }

        @Override
        public List<WindowResult> evaluate(List<Observation> observations) {
            if (observations == null || observations.isEmpty()) {
                throw new WindowEvaluationException("At least one observation is required.");
            }

            List<Observation> sorted = observations.stream()
                    .sorted(Comparator
                            .comparing(Observation::repository)
                            .thenComparing(Observation::observedAt))
                    .toList();

            Map<String, List<Observation>> partitions = new HashMap<>();

            for (Observation observation : sorted) {
                partitions.computeIfAbsent(
                        observation.repository(),
                        ignored -> new ArrayList<>()
                ).add(observation);
            }

            List<WindowResult> results = new ArrayList<>(sorted.size());

            for (List<Observation> partition : partitions.values()) {
                long first = partition.getFirst().value();
                long finalValue = partition.getLast().value();

                for (int index = 0; index < partition.size(); index++) {
                    Observation current = partition.get(index);

                    // The ordered default frame ends at CURRENT ROW.
                    long defaultLast = current.value();

                    int frameStart = Math.max(0, index - precedingRows);
                    long framedLast = partition
                            .subList(frameStart, index + 1)
                            .getLast()
                            .value();

                    results.add(new WindowResult(
                            current,
                            first,
                            defaultLast,
                            finalValue,
                            framedLast
                    ));
                }
            }

            results.sort(Comparator
                    .comparing((WindowResult r) -> r.observation().repository())
                    .thenComparing(r -> r.observation().observedAt()));

            return List.copyOf(results);
        }
    }

    static final class MergeEligibilityReport {
        private final List<WindowResult> rows;

        MergeEligibilityReport(List<WindowResult> rows) {
            this.rows = List.copyOf(rows);
        }

        void validate() {
            if (rows.isEmpty()) {
                throw new WindowEvaluationException("No evaluated rows exist.");
            }

            WindowResult paymentFirst = rows.stream()
                    .filter(r -> r.observation().repository().equals("payment-api"))
                    .findFirst()
                    .orElseThrow();

            if (paymentFirst.firstValue() != 4) {
                throw new WindowEvaluationException("FIRST_VALUE invariant failed.");
            }

            long paymentFinal = rows.stream()
                    .filter(r -> r.observation().repository().equals("payment-api"))
                    .mapToLong(WindowResult::fullPartitionLastValue)
                    .distinct()
                    .findFirst()
                    .orElseThrow();

            if (paymentFinal != 11) {
                throw new WindowEvaluationException(
                        "Full-partition LAST_VALUE invariant failed."
                );
            }
        }

        void print() {
            System.out.printf(
                    "%-15s %-28s %-8s %-12s %-14s %-14s %-14s%n",
                    "Repository",
                    "Observed At",
                    "Value",
                    "FIRST",
                    "DEFAULT LAST",
                    "FULL LAST",
                    "FRAME LAST"
            );

            System.out.println("-".repeat(120));

            for (WindowResult row : rows) {
                System.out.printf(
                        "%-15s %-28s %-8d %-12d %-14d %-14d %-14d%n",
                        row.observation().repository(),
                        row.observation().observedAt(),
                        row.observation().value(),
                        row.firstValue(),
                        row.defaultLastValue(),
                        row.fullPartitionLastValue(),
                        row.framedLastValue()
                );
            }
        }
    }

    public static void main(String[] args) {
        Instant base = Instant.parse("2026-10-01T09:00:00Z");

        List<Observation> observations = List.of(
                new Observation("payment-api", base,
                        MetricType.DEPLOYMENTS, 4),
                new Observation("payment-api", base.plusSeconds(7200),
                        MetricType.DEPLOYMENTS, 7),
                new Observation("payment-api", base.plusSeconds(14400),
                        MetricType.DEPLOYMENTS, 11),
                new Observation("search-api", base,
                        MetricType.DEPLOYMENTS, 3),
                new Observation("search-api", base.plusSeconds(7200),
                        MetricType.DEPLOYMENTS, 6),
                new Observation("search-api", base.plusSeconds(14400),
                        MetricType.DEPLOYMENTS, 5)
        );

        WindowPolicy policy = new RepositoryWindowPolicy(2);
        List<WindowResult> results = policy.evaluate(observations);

        MergeEligibilityReport report = new MergeEligibilityReport(results);
        report.validate();
        report.print();

        System.out.println();
        System.out.println("Window-value validation passed.");
        System.out.println("Complexity: O(n log n) for ordering and O(n) for evaluation.");
        System.out.println("Domain design: immutable records represent observations and results.");
        System.out.println("Security: no dynamic SQL, shell execution, or mutable external state.");
    }
}
