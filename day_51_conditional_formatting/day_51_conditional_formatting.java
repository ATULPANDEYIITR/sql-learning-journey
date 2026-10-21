import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Predicate;

public class ConditionalAggregationEnterprise {

    enum OrderStatus {
        COMPLETED,
        CANCELLED,
        PENDING
    }

    enum SalesChannel {
        WEB,
        MOBILE,
        STORE
    }

    record Order(
        int id,
        int customerId,
        String region,
        OrderStatus status,
        SalesChannel channel,
        BigDecimal amount,
        boolean returned
    ) {
        Order {
            if (id <= 0 || customerId <= 0) {
                throw new IllegalArgumentException("IDs must be positive");
            }
            if (region == null || region.isBlank()) {
                throw new IllegalArgumentException("Region is required");
            }
            Objects.requireNonNull(status, "Status is required");
            Objects.requireNonNull(channel, "Channel is required");
            Objects.requireNonNull(amount, "Amount is required");

            if (amount.signum() < 0) {
                throw new IllegalArgumentException(
                    "Amount cannot be negative"
                );
            }

            amount = amount.setScale(2, RoundingMode.HALF_UP);
        }
    }

    record KpiReport(
        long totalOrders,
        long completedOrders,
        long cancelledOrders,
        long pendingOrders,
        BigDecimal completedRevenue,
        BigDecimal cancelledValue,
        BigDecimal webRevenue,
        BigDecimal mobileRevenue,
        long returnedCompletedOrders,
        BigDecimal averageCompletedOrder,
        BigDecimal completionRate,
        BigDecimal cancellationRate
    ) {}

    record RegionalKpi(
        String region,
        long orders,
        long completed,
        long cancelled,
        BigDecimal revenue,
        BigDecimal webRevenue,
        long returnedCompleted,
        BigDecimal completionRate
    ) {}

    static final class Aggregator {
        private static final BigDecimal ZERO = BigDecimal.ZERO.setScale(2);

        private Aggregator() {}

        static BigDecimal sum(
            List<Order> orders,
            Predicate<Order> condition
        ) {
            return orders.stream()
                .filter(condition)
                .map(Order::amount)
                .reduce(ZERO, BigDecimal::add)
                .setScale(2, RoundingMode.HALF_UP);
        }

        static long count(
            List<Order> orders,
            Predicate<Order> condition
        ) {
            return orders.stream()
                .filter(condition)
                .count();
        }

        static BigDecimal average(
            List<Order> orders,
            Predicate<Order> condition
        ) {
            List<BigDecimal> values = orders.stream()
                .filter(condition)
                .map(Order::amount)
                .toList();

            if (values.isEmpty()) {
                return ZERO;
            }

            BigDecimal total = values.stream()
                .reduce(ZERO, BigDecimal::add);

            return total.divide(
                BigDecimal.valueOf(values.size()),
                2,
                RoundingMode.HALF_UP
            );
        }

        static BigDecimal percentage(long numerator, long denominator) {
            if (denominator == 0) {
                return ZERO;
            }

            return BigDecimal.valueOf(numerator)
                .multiply(BigDecimal.valueOf(100))
                .divide(
                    BigDecimal.valueOf(denominator),
                    2,
                    RoundingMode.HALF_UP
                );
        }
    }

    static final class GovernancePolicy {
        private final long minimumCompletedOrders;
        private final BigDecimal minimumCompletionRate;

        GovernancePolicy(
            long minimumCompletedOrders,
            BigDecimal minimumCompletionRate
        ) {
            if (minimumCompletedOrders < 0) {
                throw new IllegalArgumentException(
                    "Minimum completed orders cannot be negative"
                );
            }

            if (minimumCompletionRate.signum() < 0 ||
                minimumCompletionRate.compareTo(BigDecimal.valueOf(100)) > 0) {
                throw new IllegalArgumentException(
                    "Completion rate must be between 0 and 100"
                );
            }

            this.minimumCompletedOrders = minimumCompletedOrders;
            this.minimumCompletionRate = minimumCompletionRate;
        }

        boolean accepts(KpiReport report) {
            return report.completedOrders() >= minimumCompletedOrders
                && report.completionRate()
                    .compareTo(minimumCompletionRate) >= 0;
        }
    }

    static final class RevenueAnalyticsService {
        private final List<Order> orders;

        RevenueAnalyticsService(List<Order> orders) {
            this.orders = List.copyOf(orders);
        }

        KpiReport generateReport() {
            Predicate<Order> completed =
                order -> order.status() == OrderStatus.COMPLETED;

            Predicate<Order> cancelled =
                order -> order.status() == OrderStatus.CANCELLED;

            Predicate<Order> pending =
                order -> order.status() == OrderStatus.PENDING;

            long completedCount =
                Aggregator.count(orders, completed);

            long cancelledCount =
                Aggregator.count(orders, cancelled);

            long pendingCount =
                Aggregator.count(orders, pending);

            return new KpiReport(
                orders.size(),
                completedCount,
                cancelledCount,
                pendingCount,
                Aggregator.sum(orders, completed),
                Aggregator.sum(orders, cancelled),
                Aggregator.sum(
                    orders,
                    order -> order.status() == OrderStatus.COMPLETED
                        && order.channel() == SalesChannel.WEB
                ),
                Aggregator.sum(
                    orders,
                    order -> order.status() == OrderStatus.COMPLETED
                        && order.channel() == SalesChannel.MOBILE
                ),
                Aggregator.count(
                    orders,
                    order -> order.status() == OrderStatus.COMPLETED
                        && order.returned()
                ),
                Aggregator.average(orders, completed),
                Aggregator.percentage(
                    completedCount,
                    orders.size()
                ),
                Aggregator.percentage(
                    cancelledCount,
                    orders.size()
                )
            );
        }

        List<RegionalKpi> generateRegionalReport() {
            Map<String, List<Order>> grouped = new java.util.TreeMap<>();

            for (Order order : orders) {
                grouped
                    .computeIfAbsent(
                        order.region(),
                        ignored -> new ArrayList<>()
                    )
                    .add(order);
            }

            return grouped.entrySet().stream()
                .map(entry -> {
                    String region = entry.getKey();
                    List<Order> rows = entry.getValue();

                    long completed = Aggregator.count(
                        rows,
                        order ->
                            order.status() == OrderStatus.COMPLETED
                    );

                    return new RegionalKpi(
                        region,
                        rows.size(),
                        completed,
                        Aggregator.count(
                            rows,
                            order ->
                                order.status() == OrderStatus.CANCELLED
                        ),
                        Aggregator.sum(
                            rows,
                            order ->
                                order.status() == OrderStatus.COMPLETED
                        ),
                        Aggregator.sum(
                            rows,
                            order ->
                                order.status() == OrderStatus.COMPLETED
                                    && order.channel() == SalesChannel.WEB
                        ),
                        Aggregator.count(
                            rows,
                            order ->
                                order.status() == OrderStatus.COMPLETED
                                    && order.returned()
                        ),
                        Aggregator.percentage(completed, rows.size())
                    );
                })
                .toList();
        }

        void validate(KpiReport report) {
            if (report.completedOrders()
                    + report.cancelledOrders()
                    + report.pendingOrders()
                    != report.totalOrders()) {
                throw new IllegalStateException(
                    "Status counts do not partition the dataset"
                );
            }

            BigDecimal impossibleRevenue = Aggregator.sum(
                orders,
                order -> order.amount()
                    .compareTo(BigDecimal.valueOf(1_000_000)) > 0
            );

            if (impossibleRevenue.signum() != 0) {
                throw new IllegalStateException(
                    "Unexpected empty-condition aggregation result"
                );
            }
        }
    }

    static List<Order> sampleOrders() {
        return List.of(
            new Order(
                1, 101, "North", OrderStatus.COMPLETED,
                SalesChannel.WEB, new BigDecimal("1250.00"), false
            ),
            new Order(
                2, 102, "North", OrderStatus.CANCELLED,
                SalesChannel.MOBILE, new BigDecimal("800.00"), false
            ),
            new Order(
                3, 103, "South", OrderStatus.COMPLETED,
                SalesChannel.MOBILE, new BigDecimal("2100.00"), false
            ),
            new Order(
                4, 104, "South", OrderStatus.COMPLETED,
                SalesChannel.WEB, new BigDecimal("1750.00"), true
            ),
            new Order(
                5, 105, "East", OrderStatus.PENDING,
                SalesChannel.WEB, new BigDecimal("900.00"), false
            ),
            new Order(
                6, 106, "East", OrderStatus.COMPLETED,
                SalesChannel.STORE, new BigDecimal("3200.00"), false
            ),
            new Order(
                7, 107, "West", OrderStatus.CANCELLED,
                SalesChannel.WEB, new BigDecimal("600.00"), false
            ),
            new Order(
                8, 108, "West", OrderStatus.COMPLETED,
                SalesChannel.MOBILE, new BigDecimal("1450.00"), false
            ),
            new Order(
                9, 109, "North", OrderStatus.COMPLETED,
                SalesChannel.WEB, new BigDecimal("2800.00"), false
            ),
            new Order(
                10, 110, "South", OrderStatus.PENDING,
                SalesChannel.MOBILE, new BigDecimal("1100.00"), false
            )
        );
    }

    static void printReport(KpiReport report) {
        System.out.println("Enterprise KPI Report");
        System.out.println("---------------------");
        System.out.println("Total orders:            " + report.totalOrders());
        System.out.println("Completed orders:        " + report.completedOrders());
        System.out.println("Cancelled orders:        " + report.cancelledOrders());
        System.out.println("Pending orders:          " + report.pendingOrders());
        System.out.println("Completed revenue:       " + report.completedRevenue());
        System.out.println("Cancelled value:         " + report.cancelledValue());
        System.out.println("Web revenue:             " + report.webRevenue());
        System.out.println("Mobile revenue:          " + report.mobileRevenue());
        System.out.println(
            "Returned completed:      "
                + report.returnedCompletedOrders()
        );
        System.out.println(
            "Average completed:       "
                + report.averageCompletedOrder()
        );
        System.out.println(
            "Completion rate:         "
                + report.completionRate()
                + "%"
        );
        System.out.println(
            "Cancellation rate:       "
                + report.cancellationRate()
                + "%"
        );
    }

    public static void main(String[] args) {
        try {
            RevenueAnalyticsService service =
                new RevenueAnalyticsService(sampleOrders());

            KpiReport report = service.generateReport();

            service.validate(report);
            printReport(report);

            System.out.println("\nRegional KPI Report");
            System.out.println("-------------------");

            for (RegionalKpi metric : service.generateRegionalReport()) {
                System.out.printf(
                    "%-8s orders=%2d completed=%2d cancelled=%2d "
                        + "revenue=%8s web=%8s returned=%2d rate=%s%%%n",
                    metric.region(),
                    metric.orders(),
                    metric.completed(),
                    metric.cancelled(),
                    metric.revenue(),
                    metric.webRevenue(),
                    metric.returnedCompleted(),
                    metric.completionRate()
                );
            }

            GovernancePolicy policy = new GovernancePolicy(
                5,
                new BigDecimal("50.00")
            );

            System.out.println(
                "\nKPI policy accepted: " + policy.accepts(report)
            );

            System.out.println("Aggregation validation: passed");
        } catch (RuntimeException error) {
            System.err.println(
                "Analytics failure: " + error.getMessage()
            );
            System.exit(1);
        }
    }
}
