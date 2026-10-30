import java.math.BigDecimal;
import java.math.MathContext;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.function.BiConsumer;
import java.util.function.Function;

public class WindowAnalyticsDemo {

    private static final MathContext MATH_CONTEXT = MathContext.DECIMAL128;
    private static final int MAX_EVENTS = 500_000;
    private static final int MAX_SPAN_DAYS = 3660;

    enum RunState {
        CREATED,
        VALIDATED,
        AGGREGATED,
        WINDOWED,
        RANKED,
        COMPLETED,
        FAILED
    }

    static final class AnalyticsException extends RuntimeException {
        AnalyticsException(String message) {
            super(message);
        }

        AnalyticsException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    record SalesEvent(
        String eventId,
        String storeId,
        String productId,
        LocalDate saleDate,
        int units,
        BigDecimal revenue
    ) {
        SalesEvent {
            requireIdentifier(eventId, "event identifier");
            requireIdentifier(storeId, "store identifier");
            requireIdentifier(productId, "product identifier");

            Objects.requireNonNull(saleDate, "Sale date is required.");
            Objects.requireNonNull(revenue, "Revenue is required.");

            if (units <= 0) {
                throw new AnalyticsException("Units must be positive.");
            }

            if (revenue.signum() < 0 ||
                revenue.scale() > 2 ||
                revenue.precision() > 16) {
                throw new AnalyticsException(
                    "Revenue must be non-negative with at most two decimal places."
                );
            }
        }
    }

    record WindowPolicy(
        int windowDays,
        int maximumSpanDays,
        BigDecimal revenueWeight,
        BigDecimal growthWeight
    ) {
        WindowPolicy {
            Objects.requireNonNull(revenueWeight);
            Objects.requireNonNull(growthWeight);

            if (windowDays < 1 ||
                maximumSpanDays < 2 * windowDays ||
                maximumSpanDays > MAX_SPAN_DAYS) {
                throw new AnalyticsException("Invalid window policy.");
            }

            if (revenueWeight.signum() < 0 ||
                growthWeight.signum() < 0 ||
                revenueWeight.add(growthWeight).compareTo(BigDecimal.ONE) != 0) {
                throw new AnalyticsException(
                    "Ranking weights must be non-negative and sum to one."
                );
            }
        }

        static WindowPolicy standard() {
            return new WindowPolicy(
                7,
                MAX_SPAN_DAYS,
                new BigDecimal("0.60"),
                new BigDecimal("0.40")
            );
        }
    }

    record SeriesKey(String storeId, String productId) {
    }

    record StoreDateKey(String storeId, LocalDate saleDate) {
    }

    record Aggregate(BigDecimal revenue, int units) {
        Aggregate add(SalesEvent event) {
            return new Aggregate(
                revenue.add(event.revenue()),
                Math.addExact(units, event.units())
            );
        }

        static Aggregate empty() {
            return new Aggregate(BigDecimal.ZERO, 0);
        }
    }

    record AnalyticsRow(
        String storeId,
        String productId,
        LocalDate saleDate,
        BigDecimal dailyRevenue,
        int dailyUnits,
        BigDecimal rollingRevenue7d,
        int rollingUnits7d,
        BigDecimal movingAverageRevenue7d,
        Optional<BigDecimal> previous7dRevenue,
        Optional<BigDecimal> growthRate,
        Optional<BigDecimal> previousDayRevenue,
        BigDecimal cumulativeRevenue,
        Optional<Integer> revenueRank,
        Optional<Integer> growthRank,
        Optional<BigDecimal> compositeScore,
        Optional<Integer> compositeRank
    ) {
        AnalyticsRow {
            Objects.requireNonNull(storeId);
            Objects.requireNonNull(productId);
            Objects.requireNonNull(saleDate);
            Objects.requireNonNull(dailyRevenue);
            Objects.requireNonNull(rollingRevenue7d);
            Objects.requireNonNull(movingAverageRevenue7d);
            Objects.requireNonNull(previous7dRevenue);
            Objects.requireNonNull(growthRate);
            Objects.requireNonNull(previousDayRevenue);
            Objects.requireNonNull(cumulativeRevenue);
            Objects.requireNonNull(revenueRank);
            Objects.requireNonNull(growthRank);
            Objects.requireNonNull(compositeScore);
            Objects.requireNonNull(compositeRank);
        }

        boolean rankingEligible() {
            return compositeScore.isPresent();
        }
    }

    record AnalyticsReport(
        RunState state,
        int transactionCount,
        List<AnalyticsRow> rows
    ) {
        AnalyticsReport {
            rows = List.copyOf(rows);
        }
    }

    static final class AnalyticsRun {
        private RunState state = RunState.CREATED;

        RunState state() {
            return state;
        }

        void advance(RunState expected, RunState next) {
            if (state != expected) {
                throw new AnalyticsException(
                    "Invalid run transition: " + state +
                    " cannot transition to " + next
                );
            }

            state = next;
        }

        void fail() {
            if (state != RunState.COMPLETED) {
                state = RunState.FAILED;
            }
        }
    }

    static final class MetricWork {
        final String storeId;
        final String productId;
        final LocalDate date;

        final BigDecimal dailyRevenue;
        final int dailyUnits;

        final BigDecimal rollingRevenue;
        final int rollingUnits;
        final BigDecimal movingAverageRevenue;

        final Optional<BigDecimal> previous7dRevenue;
        final Optional<BigDecimal> growthRate;
        final Optional<BigDecimal> previousDayRevenue;
        final BigDecimal cumulativeRevenue;

        Integer revenueRank;
        Integer growthRank;
        BigDecimal compositeScore;
        Integer compositeRank;

        MetricWork(
            String storeId,
            String productId,
            LocalDate date,
            BigDecimal dailyRevenue,
            int dailyUnits,
            BigDecimal rollingRevenue,
            int rollingUnits,
            BigDecimal movingAverageRevenue,
            Optional<BigDecimal> previous7dRevenue,
            Optional<BigDecimal> growthRate,
            Optional<BigDecimal> previousDayRevenue,
            BigDecimal cumulativeRevenue
        ) {
            this.storeId = storeId;
            this.productId = productId;
            this.date = date;
            this.dailyRevenue = dailyRevenue;
            this.dailyUnits = dailyUnits;
            this.rollingRevenue = rollingRevenue;
            this.rollingUnits = rollingUnits;
            this.movingAverageRevenue = movingAverageRevenue;
            this.previous7dRevenue = previous7dRevenue;
            this.growthRate = growthRate;
            this.previousDayRevenue = previousDayRevenue;
            this.cumulativeRevenue = cumulativeRevenue;
        }

        boolean eligible() {
            return growthRate.isPresent() &&
                   previous7dRevenue.isPresent() &&
                   previous7dRevenue.get().signum() > 0;
        }

        AnalyticsRow toRow() {
            return new AnalyticsRow(
                storeId,
                productId,
                date,
                dailyRevenue,
                dailyUnits,
                rollingRevenue,
                rollingUnits,
                movingAverageRevenue,
                previous7dRevenue,
                growthRate,
                previousDayRevenue,
                cumulativeRevenue,
                Optional.ofNullable(revenueRank),
                Optional.ofNullable(growthRank),
                Optional.ofNullable(compositeScore),
                Optional.ofNullable(compositeRank)
            );
        }
    }

    static final class WindowAnalyticsService {
        private final WindowPolicy policy;

        WindowAnalyticsService(WindowPolicy policy) {
            this.policy = Objects.requireNonNull(policy);
        }

        AnalyticsReport execute(List<SalesEvent> events) {
            AnalyticsRun run = new AnalyticsRun();

            try {
                validateEvents(events);
                run.advance(RunState.CREATED, RunState.VALIDATED);

                Map<SeriesKey, TreeMap<LocalDate, Aggregate>> aggregates =
                    aggregateEvents(events);

                run.advance(RunState.VALIDATED, RunState.AGGREGATED);

                List<MetricWork> metrics = buildWindowMetrics(aggregates);

                run.advance(RunState.AGGREGATED, RunState.WINDOWED);

                evaluateRankings(metrics);

                run.advance(RunState.WINDOWED, RunState.RANKED);

                List<AnalyticsRow> finalRows = metrics.stream()
                    .map(MetricWork::toRow)
                    .sorted(
                        Comparator.comparing(AnalyticsRow::saleDate)
                            .thenComparing(AnalyticsRow::storeId)
                            .thenComparing(AnalyticsRow::productId)
                    )
                    .toList();

                run.advance(RunState.RANKED, RunState.COMPLETED);

                return new AnalyticsReport(
                    run.state(),
                    events.size(),
                    finalRows
                );

            } catch (RuntimeException exception) {
                run.fail();

                if (exception instanceof AnalyticsException) {
                    throw exception;
                }

                throw new AnalyticsException(
                    "Analytics pipeline failed in state " + run.state(),
                    exception
                );
            }
        }

        private void validateEvents(List<SalesEvent> events) {
            if (events == null || events.isEmpty()) {
                throw new AnalyticsException("A non-empty event list is required.");
            }

            if (events.size() > MAX_EVENTS) {
                throw new AnalyticsException("Maximum event count exceeded.");
            }

            Set<String> eventIds = new HashSet<>();

            for (SalesEvent event : events) {
                Objects.requireNonNull(event, "Null sales event encountered.");

                if (!eventIds.add(event.eventId())) {
                    throw new AnalyticsException(
                        "Duplicate event identifier: " + event.eventId()
                    );
                }
            }
        }

        private Map<SeriesKey, TreeMap<LocalDate, Aggregate>> aggregateEvents(
            List<SalesEvent> events
        ) {
            Map<SeriesKey, TreeMap<LocalDate, Aggregate>> grouped =
                new HashMap<>();

            for (SalesEvent event : events) {
                SeriesKey key = new SeriesKey(event.storeId(), event.productId());

                TreeMap<LocalDate, Aggregate> daily =
                    grouped.computeIfAbsent(key, ignored -> new TreeMap<>());

                Aggregate current = daily.getOrDefault(
                    event.saleDate(),
                    Aggregate.empty()
                );

                try {
                    daily.put(event.saleDate(), current.add(event));
                } catch (ArithmeticException exception) {
                    throw new AnalyticsException(
                        "Daily unit aggregation overflow.",
                        exception
                    );
                }
            }

            return grouped;
        }

        private List<MetricWork> buildWindowMetrics(
            Map<SeriesKey, TreeMap<LocalDate, Aggregate>> grouped
        ) {
            List<MetricWork> result = new ArrayList<>();
            int window = policy.windowDays();

            for (Map.Entry<SeriesKey, TreeMap<LocalDate, Aggregate>> entry :
                grouped.entrySet()) {

                SeriesKey key = entry.getKey();
                TreeMap<LocalDate, Aggregate> observations = entry.getValue();

                LocalDate firstDate = observations.firstKey();
                LocalDate lastDate = observations.lastKey();

                long span = ChronoUnit.DAYS.between(firstDate, lastDate) + 1;

                if (span > policy.maximumSpanDays()) {
                    throw new AnalyticsException(
                        "Maximum date span exceeded for " +
                        key.storeId() + "/" + key.productId()
                    );
                }

                List<LocalDate> dates = new ArrayList<>();
                List<BigDecimal> revenues = new ArrayList<>();
                List<Integer> units = new ArrayList<>();

                LocalDate current = firstDate;

                while (!current.isAfter(lastDate)) {
                    Aggregate daily = observations.getOrDefault(
                        current,
                        Aggregate.empty()
                    );

                    dates.add(current);
                    revenues.add(daily.revenue());
                    units.add(daily.units());
                    current = current.plusDays(1);
                }

                List<BigDecimal> revenuePrefix = new ArrayList<>();
                List<Long> unitsPrefix = new ArrayList<>();

                revenuePrefix.add(BigDecimal.ZERO);
                unitsPrefix.add(0L);

                for (int index = 0; index < dates.size(); index++) {
                    revenuePrefix.add(
                        revenuePrefix.get(index).add(revenues.get(index))
                    );

                    unitsPrefix.add(
                        Math.addExact(unitsPrefix.get(index), units.get(index))
                    );
                }

                for (int index = 0; index < dates.size(); index++) {
                    int currentStart = Math.max(0, index - window + 1);

                    BigDecimal rollingRevenue =
                        revenuePrefix.get(index + 1)
                            .subtract(revenuePrefix.get(currentStart));

                    long rollingUnitsLong =
                        unitsPrefix.get(index + 1) -
                        unitsPrefix.get(currentStart);

                    if (rollingUnitsLong > Integer.MAX_VALUE) {
                        throw new AnalyticsException(
                            "Rolling unit total exceeds supported range."
                        );
                    }

                    int rollingUnits = (int) rollingUnitsLong;
                    int observedDays = index - currentStart + 1;

                    BigDecimal movingAverage = rollingRevenue.divide(
                        BigDecimal.valueOf(observedDays),
                        MATH_CONTEXT
                    );

                    Optional<BigDecimal> previous7d = Optional.empty();
                    Optional<BigDecimal> growth = Optional.empty();

                    if (index >= 2 * window - 1) {
                        int previousStart = index - 2 * window + 1;
                        int previousEnd = index - window + 1;

                        BigDecimal previousRevenue =
                            revenuePrefix.get(previousEnd)
                                .subtract(revenuePrefix.get(previousStart));

                        previous7d = Optional.of(previousRevenue);

                        if (previousRevenue.signum() > 0) {
                            growth = Optional.of(
                                rollingRevenue.subtract(previousRevenue)
                                    .divide(previousRevenue, MATH_CONTEXT)
                            );
                        }
                    }

                    Optional<BigDecimal> previousDay = index > 0
                        ? Optional.of(revenues.get(index - 1))
                        : Optional.empty();

                    result.add(
                        new MetricWork(
                            key.storeId(),
                            key.productId(),
                            dates.get(index),
                            revenues.get(index),
                            units.get(index),
                            rollingRevenue,
                            rollingUnits,
                            movingAverage,
                            previous7d,
                            growth,
                            previousDay,
                            revenuePrefix.get(index + 1)
                        )
                    );
                }
            }

            return result;
        }

        private void evaluateRankings(List<MetricWork> metrics) {
            Map<StoreDateKey, List<MetricWork>> populations = new HashMap<>();

            for (MetricWork metric : metrics) {
                StoreDateKey key = new StoreDateKey(
                    metric.storeId,
                    metric.date
                );

                populations.computeIfAbsent(
                    key,
                    ignored -> new ArrayList<>()
                ).add(metric);
            }

            for (List<MetricWork> population : populations.values()) {
                assignRanks(
                    population,
                    metric -> metric.rollingRevenue,
                    (metric, rank) -> metric.revenueRank = rank
                );

                List<MetricWork> eligible = population.stream()
                    .filter(MetricWork::eligible)
                    .toList();

                if (eligible.isEmpty()) {
                    continue;
                }

                assignRanks(
                    eligible,
                    metric -> metric.growthRate.orElseThrow(),
                    (metric, rank) -> metric.growthRank = rank
                );

                int populationSize = eligible.size();

                for (MetricWork metric : eligible) {
                    BigDecimal revenueScore = normalizedRankScore(
                        metric.revenueRank,
                        populationSize
                    );

                    BigDecimal growthScore = normalizedRankScore(
                        metric.growthRank,
                        populationSize
                    );

                    metric.compositeScore =
                        revenueScore.multiply(policy.revenueWeight())
                            .add(
                                growthScore.multiply(policy.growthWeight())
                            );
                }

                assignRanks(
                    eligible,
                    metric -> metric.compositeScore,
                    (metric, rank) -> metric.compositeRank = rank
                );
            }
        }

        private static void assignRanks(
            List<MetricWork> items,
            Function<MetricWork, BigDecimal> valueSelector,
            BiConsumer<MetricWork, Integer> rankSetter
        ) {
            List<MetricWork> ordered = new ArrayList<>(items);

            ordered.sort(
                Comparator.comparing(
                    valueSelector,
                    Comparator.reverseOrder()
                )
            );

            BigDecimal previousValue = null;
            int currentRank = 0;

            for (int index = 0; index < ordered.size(); index++) {
                MetricWork metric = ordered.get(index);
                BigDecimal currentValue = valueSelector.apply(metric);

                if (index == 0 ||
                    currentValue.compareTo(previousValue) != 0) {
                    currentRank = index + 1;
                }

                rankSetter.accept(metric, currentRank);
                previousValue = currentValue;
            }
        }

        private static BigDecimal normalizedRankScore(
            int rank,
            int populationSize
        ) {
            if (populationSize <= 1) {
                return BigDecimal.ONE;
            }

            return BigDecimal.valueOf(populationSize - rank)
                .divide(
                    BigDecimal.valueOf(populationSize - 1),
                    MATH_CONTEXT
                );
        }
    }

    private static void requireIdentifier(String value, String description) {
        if (value == null ||
            !value.matches("[A-Za-z0-9_-]{1,50}")) {
            throw new AnalyticsException("Invalid " + description + ".");
        }
    }

    private static List<SalesEvent> createSampleEvents() {
        List<SalesEvent> events = new ArrayList<>();

        List<String> stores = List.of("LKO-01", "LKO-02");
        List<String> products = List.of("P-A", "P-B", "P-C");

        LocalDate startDate = LocalDate.of(2026, 10, 1);
        int eventNumber = 1;

        for (int storeIndex = 0; storeIndex < stores.size(); storeIndex++) {
            for (int productIndex = 0;
                 productIndex < products.size();
                 productIndex++) {

                for (int dayNumber = 0; dayNumber < 21; dayNumber++) {
                    if (stores.get(storeIndex).equals("LKO-02") &&
                        products.get(productIndex).equals("P-C") &&
                        dayNumber == 5) {
                        continue;
                    }

                    int revenueCents =
                        10000 +
                        productIndex * 1700 +
                        storeIndex * 800 +
                        dayNumber * (productIndex * 220 + storeIndex * 90);

                    int quantity =
                        5 + productIndex +
                        ((dayNumber + storeIndex) % 4);

                    events.add(
                        new SalesEvent(
                            "EVT-" + String.format("%05d", eventNumber++),
                            stores.get(storeIndex),
                            products.get(productIndex),
                            startDate.plusDays(dayNumber),
                            quantity,
                            BigDecimal.valueOf(revenueCents, 2)
                        )
                    );

                    if (dayNumber % 5 == 0 && productIndex == 0) {
                        events.add(
                            new SalesEvent(
                                "EVT-" + String.format("%05d", eventNumber++),
                                stores.get(storeIndex),
                                products.get(productIndex),
                                startDate.plusDays(dayNumber),
                                2,
                                BigDecimal.valueOf(2500 + dayNumber * 10, 2)
                            )
                        );
                    }
                }
            }
        }

        return List.copyOf(events);
    }

    private static void verifyReport(AnalyticsReport report) {
        if (report.state() != RunState.COMPLETED) {
            throw new AnalyticsException("Analytics run did not complete.");
        }

        if (report.rows().size() != 126) {
            throw new AnalyticsException("Unexpected analytics row count.");
        }

        AnalyticsRow missingDate = report.rows().stream()
            .filter(row ->
                row.storeId().equals("LKO-02") &&
                row.productId().equals("P-C") &&
                row.saleDate().equals(LocalDate.of(2026, 10, 6))
            )
            .findFirst()
            .orElseThrow(() ->
                new AnalyticsException("Missing calendar date was not generated.")
            );

        if (missingDate.dailyRevenue().signum() != 0 ||
            missingDate.dailyUnits() != 0) {
            throw new AnalyticsException(
                "Missing-date zero-activity rule failed."
            );
        }

        AnalyticsRow firstEligible = report.rows().stream()
            .filter(row ->
                row.storeId().equals("LKO-01") &&
                row.productId().equals("P-A") &&
                row.saleDate().equals(LocalDate.of(2026, 10, 14))
            )
            .findFirst()
            .orElseThrow();

        if (!firstEligible.rankingEligible()) {
            throw new AnalyticsException(
                "First complete comparison window was not eligible."
            );
        }
    }

    private static void printReport(AnalyticsReport report) {
        LocalDate latestDate = report.rows().stream()
            .map(AnalyticsRow::saleDate)
            .max(LocalDate::compareTo)
            .orElseThrow();

        System.out.println(
            "Advanced Window Analytics | Reporting date: " + latestDate
        );

        System.out.printf(
            "%-10s %-8s %12s %12s %11s %9s %6s%n",
            "Store",
            "Product",
            "Daily",
            "Rolling 7d",
            "Growth %",
            "Score",
            "Rank"
        );

        report.rows().stream()
            .filter(row -> row.saleDate().equals(latestDate))
            .sorted(
                Comparator.comparing(AnalyticsRow::storeId)
                    .thenComparing(
                        row -> row.compositeRank().orElse(Integer.MAX_VALUE)
                    )
                    .thenComparing(AnalyticsRow::productId)
            )
            .forEach(row -> {
                String growth = row.growthRate()
                    .map(value -> value.multiply(BigDecimal.valueOf(100))
                        .setScale(2, java.math.RoundingMode.HALF_UP)
                        .toPlainString())
                    .orElse("N/A");

                String score = row.compositeScore()
                    .map(value -> value.setScale(
                        4,
                        java.math.RoundingMode.HALF_UP
                    ).toPlainString())
                    .orElse("N/A");

                String rank = row.compositeRank()
                    .map(String::valueOf)
                    .orElse("N/A");

                System.out.printf(
                    "%-10s %-8s %12s %12s %11s %9s %6s%n",
                    row.storeId(),
                    row.productId(),
                    row.dailyRevenue().toPlainString(),
                    row.rollingRevenue7d().toPlainString(),
                    growth,
                    score,
                    rank
                );
            });

        long eligibleCount = report.rows().stream()
            .filter(AnalyticsRow::rankingEligible)
            .count();

        System.out.println("\nTransactions processed: " + report.transactionCount());
        System.out.println("Daily analytics rows: " + report.rows().size());
        System.out.println("Ranking-eligible rows: " + eligibleCount);
        System.out.println("Run state: " + report.state());
    }

    public static void main(String[] args) {
        try {
            WindowAnalyticsService service =
                new WindowAnalyticsService(WindowPolicy.standard());

            List<SalesEvent> events = createSampleEvents();
            AnalyticsReport report = service.execute(events);

            verifyReport(report);
            printReport(report);

        } catch (AnalyticsException exception) {
            System.err.println(
                "Analytics execution failed: " + exception.getMessage()
            );
            System.exit(1);
        }
    }
}
