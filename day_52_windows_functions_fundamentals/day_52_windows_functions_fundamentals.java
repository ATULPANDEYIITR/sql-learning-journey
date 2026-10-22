import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class WindowFunctionsIntroduction {

    enum Metric {
        ROW_NUMBER,
        RANK,
        RUNNING_TOTAL,
        MOVING_AVERAGE,
        LAG,
        LEAD
    }

    record Sale(
            int id,
            String employee,
            String department,
            LocalDate date,
            double amount
    ) {
        Sale {
            if (id <= 0) {
                throw new IllegalArgumentException("Sale ID must be positive");
            }
            if (employee == null || employee.isBlank()) {
                throw new IllegalArgumentException("Employee is required");
            }
            if (department == null || department.isBlank()) {
                throw new IllegalArgumentException("Department is required");
            }
            if (date == null) {
                throw new IllegalArgumentException("Date is required");
            }
            if (amount < 0) {
                throw new IllegalArgumentException("Amount cannot be negative");
            }
        }
    }

    record WindowResult(
            Sale sale,
            int rowNumber,
            int rank,
            double runningTotal,
            double movingAverage,
            Double lag,
            Double lead
    ) {}

    interface WindowPolicy {
        List<WindowResult> evaluate(List<Sale> sales);
    }

    static final class DepartmentWindowPolicy implements WindowPolicy {
        private static final Comparator<Sale> DATE_ORDER =
                Comparator.comparing(Sale::date)
                          .thenComparingInt(Sale::id);

        @Override
        public List<WindowResult> evaluate(List<Sale> sales) {
            validateInput(sales);

            Map<String, List<Sale>> partitions = sales.stream()
                    .collect(java.util.stream.Collectors.groupingBy(
                            Sale::department
                    ));

            List<WindowResult> results = new ArrayList<>();

            for (List<Sale> partition : partitions.values()) {
                partition.sort(DATE_ORDER);

                double runningTotal = 0.0;

                for (int index = 0; index < partition.size(); index++) {
                    Sale current = partition.get(index);

                    // Equivalent conceptually to:
                    // ROW_NUMBER() OVER (
                    //   PARTITION BY department
                    //   ORDER BY date, id
                    // )
                    int rowNumber = index + 1;

                    runningTotal += current.amount();

                    // Two-row frame:
                    // ROWS BETWEEN 1 PRECEDING AND CURRENT ROW.
                    int start = Math.max(0, index - 1);
                    double frameTotal = 0.0;

                    for (int i = start; i <= index; i++) {
                        frameTotal += partition.get(i).amount();
                    }

                    double movingAverage =
                            frameTotal / (index - start + 1);

                    Double lag = index == 0
                            ? null
                            : partition.get(index - 1).amount();

                    Double lead = index + 1 >= partition.size()
                            ? null
                            : partition.get(index + 1).amount();

                    results.add(new WindowResult(
                            current,
                            rowNumber,
                            0,
                            runningTotal,
                            movingAverage,
                            lag,
                            lead
                    ));
                }

                assignRanks(results, partition);
            }

            return results.stream()
                    .sorted(Comparator
                            .comparing((WindowResult r) ->
                                    r.sale().department())
                            .thenComparing(r -> r.sale().date())
                            .thenComparingInt(r -> r.sale().id()))
                    .toList();
        }

        private static void assignRanks(
                List<WindowResult> allResults,
                List<Sale> partition
        ) {
            List<Sale> ranked = partition.stream()
                    .sorted(Comparator
                            .comparingDouble(Sale::amount)
                            .reversed()
                            .thenComparingInt(Sale::id))
                    .toList();

            Map<Integer, Integer> ranks = new HashMap<>();
            double previousAmount = Double.NaN;
            int rank = 0;

            for (int index = 0; index < ranked.size(); index++) {
                Sale sale = ranked.get(index);

                if (index == 0 || sale.amount() != previousAmount) {
                    rank = index + 1;
                    previousAmount = sale.amount();
                }

                ranks.put(sale.id(), rank);
            }

            for (int i = 0; i < allResults.size(); i++) {
                WindowResult result = allResults.get(i);

                if (result.sale().department().equals(
                        partition.get(0).department())) {
                    allResults.set(
                            i,
                            new WindowResult(
                                    result.sale(),
                                    result.rowNumber(),
                                    ranks.get(result.sale().id()),
                                    result.runningTotal(),
                                    result.movingAverage(),
                                    result.lag(),
                                    result.lead()
                            )
                    );
                }
            }
        }

        private static void validateInput(List<Sale> sales) {
            if (sales == null || sales.isEmpty()) {
                throw new IllegalArgumentException(
                        "At least one sale is required"
                );
            }

            Set<Integer> ids = new HashSet<>();

            for (Sale sale : sales) {
                if (!ids.add(sale.id())) {
                    throw new IllegalArgumentException(
                            "Duplicate sale ID: " + sale.id()
                    );
                }
            }
        }
    }

    private static void printResults(List<WindowResult> results) {
        System.out.printf(
                "%-13s %-10s %10s %6s %6s %13s %13s %10s %10s%n",
                "Department",
                "Employee",
                "Amount",
                "ROW#",
                "RANK",
                "Running",
                "Avg2",
                "LAG",
                "LEAD"
        );

        System.out.println("-".repeat(105));

        for (WindowResult result : results) {
            System.out.printf(
                    "%-13s %-10s %10.2f %6d %6d %13.2f %13.2f %10s %10s%n",
                    result.sale().department(),
                    result.sale().employee(),
                    result.sale().amount(),
                    result.rowNumber(),
                    result.rank(),
                    result.runningTotal(),
                    result.movingAverage(),
                    formatNullable(result.lag()),
                    formatNullable(result.lead())
            );
        }
    }

    private static String formatNullable(Double value) {
        return value == null ? "-" : String.format("%.2f", value);
    }

    public static void main(String[] args) {
        List<Sale> sales = List.of(
                new Sale(1, "Asha", "Technology",
                        LocalDate.of(2026, 1, 5), 12000),
                new Sale(2, "Ravi", "Technology",
                        LocalDate.of(2026, 1, 12), 18000),
                new Sale(3, "Asha", "Technology",
                        LocalDate.of(2026, 2, 3), 15000),
                new Sale(4, "Ravi", "Technology",
                        LocalDate.of(2026, 2, 17), 22000),
                new Sale(5, "Neha", "Finance",
                        LocalDate.of(2026, 1, 8), 9000),
                new Sale(6, "Vikram", "Finance",
                        LocalDate.of(2026, 1, 22), 14000),
                new Sale(7, "Neha", "Finance",
                        LocalDate.of(2026, 2, 6), 11000),
                new Sale(8, "Vikram", "Finance",
                        LocalDate.of(2026, 2, 20), 17000),
                new Sale(9, "Meera", "Operations",
                        LocalDate.of(2026, 1, 10), 7000),
                new Sale(10, "Meera", "Operations",
                        LocalDate.of(2026, 2, 14), 13000)
        );

        try {
            WindowPolicy policy = new DepartmentWindowPolicy();
            List<WindowResult> results = policy.evaluate(sales);

            printResults(results);

            System.out.println();
            System.out.println(
                    "Metrics: " +
                    EnumSet.allOf(Metric.class)
            );
        } catch (IllegalArgumentException error) {
            System.err.println("Window evaluation failed: "
                    + error.getMessage());
            System.exit(1);
        }
    }
}
