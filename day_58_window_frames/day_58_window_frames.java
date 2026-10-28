import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class WindowFramesDemo {

    enum FrameType {
        ROWS,
        RANGE,
        GROUPS
    }

    record Sale(
            int id,
            String employee,
            int day,
            double amount
    ) {
        Sale {
            if (id <= 0) {
                throw new IllegalArgumentException("id must be positive");
            }
            if (employee == null || employee.isBlank()) {
                throw new IllegalArgumentException("employee is required");
            }
            if (!Double.isFinite(amount) || amount < 0) {
                throw new IllegalArgumentException(
                        "amount must be finite and non-negative"
                );
            }
        }
    }

    static final class WindowFrameException extends RuntimeException {
        WindowFrameException(String message) {
            super(message);
        }
    }

    interface OrderKey<T> {
        double value(T row);
    }

    static final class WindowService {

        private final List<Sale> source;

        WindowService(List<Sale> source) {
            if (source == null || source.isEmpty()) {
                throw new WindowFrameException("Input cannot be empty");
            }

            Set<Integer> ids = new HashSet<>();
            for (Sale sale : source) {
                if (!ids.add(sale.id())) {
                    throw new WindowFrameException(
                            "Duplicate sale id: " + sale.id()
                    );
                }
            }

            this.source = List.copyOf(source);
        }

        List<Double> rows(int preceding, int following) {
            validateOffsets(preceding, following);

            List<Double> result = new ArrayList<>();

            for (int i = 0; i < source.size(); i++) {
                int start = Math.max(0, i - preceding);
                int end = Math.min(
                        source.size() - 1,
                        i + following
                );

                double total = 0;
                for (int j = start; j <= end; j++) {
                    total += source.get(j).amount();
                }
                result.add(total);
            }

            return List.copyOf(result);
        }

        List<Double> range(
                OrderKey<Sale> key,
                double preceding,
                double following
        ) {
            if (preceding < 0 || following < 0) {
                throw new WindowFrameException(
                        "RANGE boundaries cannot be negative"
                );
            }

            List<Sale> ordered = new ArrayList<>(source);
            ordered.sort(
                    Comparator.comparingDouble(key::value)
                            .thenComparingInt(Sale::id)
            );

            List<Double> result = new ArrayList<>();

            for (Sale current : ordered) {
                double currentValue = key.value(current);
                double low = currentValue - preceding;
                double high = currentValue + following;

                double total = 0;
                for (Sale candidate : ordered) {
                    double candidateValue = key.value(candidate);
                    if (candidateValue >= low &&
                            candidateValue <= high) {
                        total += candidate.amount();
                    }
                }

                result.add(total);
            }

            return List.copyOf(result);
        }

        List<Double> groups(
                java.util.function.ToIntFunction<Sale> key,
                int precedingGroups,
                int followingGroups
        ) {
            validateOffsets(precedingGroups, followingGroups);

            List<Sale> ordered = new ArrayList<>(source);
            ordered.sort(
                    Comparator.comparingInt(key)
                            .thenComparingInt(Sale::id)
            );

            List<Integer> peerKeys = ordered.stream()
                    .map(key::applyAsInt)
                    .distinct()
                    .toList();

            List<Double> result = new ArrayList<>();

            for (Sale current : ordered) {
                int currentKey = key.applyAsInt(current);
                int groupIndex = peerKeys.indexOf(currentKey);

                int first = Math.max(
                        0,
                        groupIndex - precedingGroups
                );
                int last = Math.min(
                        peerKeys.size() - 1,
                        groupIndex + followingGroups
                );

                double total = 0;

                for (Sale candidate : ordered) {
                    int candidateGroup =
                            peerKeys.indexOf(key.applyAsInt(candidate));

                    if (candidateGroup >= first &&
                            candidateGroup <= last) {
                        total += candidate.amount();
                    }
                }

                result.add(total);
            }

            return List.copyOf(result);
        }

        private static void validateOffsets(
                int preceding,
                int following
        ) {
            if (preceding < 0 || following < 0) {
                throw new WindowFrameException(
                        "Frame offsets cannot be negative"
                );
            }
        }
    }

    private static void print(
            String title,
            List<Double> values
    ) {
        System.out.println("\n" + title);
        for (int i = 0; i < values.size(); i++) {
            System.out.printf(
                    "row %d -> %.2f%n",
                    i + 1,
                    values.get(i)
            );
        }
    }

    public static void main(String[] args) {
        try {
            List<Sale> sales = List.of(
                    new Sale(1, "Asha", 1, 100),
                    new Sale(2, "Asha", 2, 200),
                    new Sale(3, "Asha", 2, 300),
                    new Sale(4, "Asha", 4, 400),
                    new Sale(5, "Asha", 7, 500)
            );

            WindowService service = new WindowService(sales);

            List<Double> rows = service.rows(1, 0);
            List<Double> range = service.range(
                    Sale::amount,
                    200,
                    0
            );
            List<Double> groups = service.groups(
                    Sale::day,
                    1,
                    0
            );

            print(
                    "ROWS BETWEEN 1 PRECEDING AND CURRENT ROW",
                    rows
            );

            print(
                    "RANGE BETWEEN 200 PRECEDING AND CURRENT ROW",
                    range
            );

            print(
                    "GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW",
                    groups
            );

            if (rows.get(0) != 100 ||
                    rows.get(4) != 900) {
                throw new WindowFrameException(
                        "ROWS validation failed"
                );
            }

            if (groups.get(0) != 600 ||
                    groups.get(1) != 600) {
                throw new WindowFrameException(
                        "GROUPS peer-group validation failed"
                );
            }

            System.out.println("\nAll domain checks passed.");
            System.out.println(
                    "ROWS counts physical rows; RANGE evaluates " +
                    "ORDER BY values; GROUPS counts peer groups."
            );

        } catch (RuntimeException ex) {
            System.err.println(
                    "Window processing failed: " + ex.getMessage()
            );
            System.exit(1);
        }
    }
}
