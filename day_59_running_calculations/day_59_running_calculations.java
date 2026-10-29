import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.HashSet;

public class RunningCalculationsEnterprise {

    enum MetricState {
        EMPTY,
        ACTIVE
    }

    record Transaction(String id, double amount) {
        Transaction {
            if (id == null || id.isBlank()) {
                throw new IllegalArgumentException("transaction id cannot be blank");
            }
            if (!Double.isFinite(amount)) {
                throw new IllegalArgumentException("amount must be finite");
            }
        }
    }

    record RunningSnapshot(
            long count,
            double total,
            double cumulativeAverage,
            Double minimum,
            Double maximum,
            MetricState state
    ) {}

    static final class DuplicateTransactionException extends RuntimeException {
        DuplicateTransactionException(String message) {
            super(message);
        }
    }

    static final class RunningMetrics {
        private long count;
        private double total;
        private Double minimum;
        private Double maximum;

        RunningSnapshot add(double value) {
            validate(value);

            count++;
            total += value;

            minimum = minimum == null ? value : Math.min(minimum, value);
            maximum = maximum == null ? value : Math.max(maximum, value);

            return snapshot();
        }

        RunningSnapshot snapshot() {
            return new RunningSnapshot(
                    count,
                    total,
                    count == 0 ? 0.0 : total / count,
                    minimum,
                    maximum,
                    count == 0 ? MetricState.EMPTY : MetricState.ACTIVE
            );
        }

        private static void validate(double value) {
            if (!Double.isFinite(value)) {
                throw new IllegalArgumentException("running calculation requires a finite value");
            }
        }
    }

    interface MetricPolicy {
        boolean permits(RunningSnapshot snapshot);
    }

    static final class RevenueLimitPolicy implements MetricPolicy {
        private final double limit;

        RevenueLimitPolicy(double limit) {
            if (!Double.isFinite(limit) || limit < 0) {
                throw new IllegalArgumentException("limit must be finite and non-negative");
            }
            this.limit = limit;
        }

        @Override
        public boolean permits(RunningSnapshot snapshot) {
            return snapshot.total() <= limit;
        }
    }

    static final class RevenueService {
        private final RunningMetrics metrics = new RunningMetrics();
        private final Set<String> processedIds = new HashSet<>();
        private final List<RunningSnapshot> history = new ArrayList<>();
        private final MetricPolicy policy;

        RevenueService(MetricPolicy policy) {
            this.policy = Objects.requireNonNull(policy);
        }

        RunningSnapshot process(Transaction transaction) {
            Objects.requireNonNull(transaction);

            if (!processedIds.add(transaction.id())) {
                throw new DuplicateTransactionException(
                        "transaction already processed: " + transaction.id()
                );
            }

            RunningSnapshot snapshot = metrics.add(transaction.amount());

            if (!policy.permits(snapshot)) {
                // Reverting a scalar aggregate is unsafe when the service grows in
                // complexity, so this example validates policy before persistence
                // through a transactional application boundary.
                processedIds.remove(transaction.id());
                throw new IllegalStateException(
                        "transaction would violate the cumulative revenue policy"
                );
            }

            history.add(snapshot);
            return snapshot;
        }

        List<RunningSnapshot> history() {
            return List.copyOf(history);
        }
    }

    static double[] runningTotals(List<Double> values) {
        double total = 0.0;
        double[] result = new double[values.size()];

        for (int i = 0; i < values.size(); i++) {
            double value = Objects.requireNonNull(values.get(i));
            validate(value);
            total += value;
            result[i] = total;
        }

        return result;
    }

    static double[] cumulativeAverages(List<Double> values) {
        double total = 0.0;
        double[] result = new double[values.size()];

        for (int i = 0; i < values.size(); i++) {
            double value = Objects.requireNonNull(values.get(i));
            validate(value);
            total += value;
            result[i] = total / (i + 1);
        }

        return result;
    }

    static void validate(double value) {
        if (!Double.isFinite(value)) {
            throw new IllegalArgumentException("value must be finite");
        }
    }

    static void runTests() {
        List<Double> values = List.of(10.0, 20.0, 30.0);

        assert java.util.Arrays.equals(
                runningTotals(values),
                new double[]{10.0, 30.0, 60.0}
        );

        assert java.util.Arrays.equals(
                cumulativeAverages(values),
                new double[]{10.0, 15.0, 20.0}
        );

        RevenueService service = new RevenueService(new RevenueLimitPolicy(5000));

        RunningSnapshot first = service.process(new Transaction("TX-1", 1000));
        RunningSnapshot second = service.process(new Transaction("TX-2", 2000));

        assert first.total() == 1000;
        assert second.total() == 3000;
        assert second.cumulativeAverage() == 1500;
        assert second.state() == MetricState.ACTIVE;

        try {
            service.process(new Transaction("TX-2", 500));
            throw new AssertionError("duplicate transaction should fail");
        } catch (DuplicateTransactionException expected) {
            // Expected.
        }

        try {
            service.process(new Transaction("TX-3", 3000));
            throw new AssertionError("policy violation should fail");
        } catch (IllegalStateException expected) {
            // Expected.
        }
    }

    public static void main(String[] args) {
        runTests();

        RevenueService service =
                new RevenueService(new RevenueLimitPolicy(10000));

        List<Transaction> transactions = List.of(
                new Transaction("TX-001", 1250.00),
                new Transaction("TX-002", 875.50),
                new Transaction("TX-003", 1499.25),
                new Transaction("TX-004", 650.00),
                new Transaction("TX-005", 2100.75)
        );

        System.out.println("Enterprise running revenue metrics");

        for (Transaction transaction : transactions) {
            RunningSnapshot snapshot = service.process(transaction);

            System.out.printf(
                    "%s -> total=%.2f, average=%.2f, min=%.2f, max=%.2f%n",
                    transaction.id(),
                    snapshot.total(),
                    snapshot.cumulativeAverage(),
                    snapshot.minimum(),
                    snapshot.maximum()
            );
        }

        System.out.println("\nHistory entries: " + service.history().size());
        System.out.println(
                "Each aggregate update is O(1); transaction identity tracking is O(1) "
                        + "average-case with a hash set."
        );
    }
}
