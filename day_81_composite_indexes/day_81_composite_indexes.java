import java.util.*;
import java.util.stream.Collectors;

/**
 * Composite Index Enterprise Governance Engine.
 *
 * Java 17.
 *
 * Models:
 * - Composite index definitions.
 * - Column cardinality and selectivity.
 * - Equality and range predicates.
 * - Leftmost-prefix matching.
 * - Ordering and covering candidates.
 * - Workload frequency.
 * - Index redundancy.
 * - Recommendation services.
 * - Validation and failure handling.
 */
public class CompositeIndexEngine {

    enum PredicateType {
        EQUALITY,
        RANGE,
        ORDERING
    }

    record ColumnStatistics(
            String name,
            long distinctValues,
            long rowCount,
            double nullFraction
    ) {
        ColumnStatistics {
            Objects.requireNonNull(name);

            if (name.isBlank() ||
                distinctValues < 1 ||
                rowCount < distinctValues ||
                nullFraction < 0 ||
                nullFraction >= 1) {
                throw new IllegalArgumentException(
                    "Invalid column statistics."
                );
            }
        }

        double equalitySelectivity() {
            return (1.0 - nullFraction) / distinctValues;
        }
    }

    record Predicate(
            String column,
            PredicateType type,
            double estimatedFraction
    ) {
        Predicate {
            Objects.requireNonNull(column);
            Objects.requireNonNull(type);

            if (column.isBlank()) {
                throw new IllegalArgumentException(
                    "Predicate column is required."
                );
            }

            if (type == PredicateType.RANGE &&
                (estimatedFraction <= 0 ||
                 estimatedFraction > 1)) {
                throw new IllegalArgumentException(
                    "Invalid range selectivity."
                );
            }
        }

        static Predicate equality(String column) {
            return new Predicate(
                column,
                PredicateType.EQUALITY,
                0.0
            );
        }

        static Predicate range(String column, double fraction) {
            return new Predicate(
                column,
                PredicateType.RANGE,
                fraction
            );
        }
    }

    record CompositeIndex(
            String name,
            List<String> columns,
            boolean unique,
            boolean active
    ) {
        CompositeIndex {
            Objects.requireNonNull(name);
            Objects.requireNonNull(columns);

            if (name.isBlank() || columns.isEmpty()) {
                throw new IllegalArgumentException(
                    "Invalid index definition."
                );
            }

            columns = List.copyOf(columns);

            if (new HashSet<>(columns).size() != columns.size()) {
                throw new IllegalArgumentException(
                    "Index columns must be unique."
                );
            }
        }
    }

    record QueryWorkload(
            String name,
            List<Predicate> predicates,
            List<String> ordering,
            List<String> projection,
            int frequency
    ) {
        QueryWorkload {
            Objects.requireNonNull(name);

            if (name.isBlank() || frequency <= 0) {
                throw new IllegalArgumentException(
                    "Invalid workload definition."
                );
            }

            predicates = List.copyOf(predicates);
            ordering = List.copyOf(ordering);
            projection = List.copyOf(projection);
        }
    }

    record IndexEvaluation(
            String indexName,
            int prefixLength,
            double selectivity,
            boolean orderingCovered,
            boolean coveringCandidate,
            double estimatedCost
    ) {}

    static class IndexPolicyException extends RuntimeException {
        IndexPolicyException(String message) {
            super(message);
        }
    }

    interface IndexEvaluationPolicy {
        IndexEvaluation evaluate(
            CompositeIndex index,
            QueryWorkload query
        );
    }

    static class IndexCatalog {
        private final Map<String, CompositeIndex> indexes =
            new LinkedHashMap<>();

        public void register(CompositeIndex index) {
            if (indexes.containsKey(index.name())) {
                throw new IndexPolicyException(
                    "Index already exists: " + index.name()
                );
            }

            indexes.put(index.name(), index);
        }

        public List<CompositeIndex> activeIndexes() {
            return indexes.values()
                .stream()
                .filter(CompositeIndex::active)
                .toList();
        }
    }

    static class IndexAdvisor implements IndexEvaluationPolicy {

        private final Map<String, ColumnStatistics> statistics;
        private final long totalRows;

        IndexAdvisor(List<ColumnStatistics> columns) {
            if (columns.isEmpty()) {
                throw new IllegalArgumentException(
                    "Column statistics are required."
                );
            }

            Map<String, ColumnStatistics> map =
                new LinkedHashMap<>();

            long maximumRows = 0;

            for (ColumnStatistics column : columns) {
                if (map.putIfAbsent(column.name(), column) != null) {
                    throw new IllegalArgumentException(
                        "Duplicate column: " + column.name()
                    );
                }

                maximumRows = Math.max(
                    maximumRows,
                    column.rowCount()
                );
            }

            this.statistics = Collections.unmodifiableMap(map);
            this.totalRows = maximumRows;
        }

        private void validateColumn(String column) {
            if (!statistics.containsKey(column)) {
                throw new IndexPolicyException(
                    "Unknown column: " + column
                );
            }
        }

        double estimateSelectivity(QueryWorkload query) {
            double fraction = 1.0;

            for (Predicate predicate : query.predicates()) {
                validateColumn(predicate.column());

                ColumnStatistics stats =
                    statistics.get(predicate.column());

                if (predicate.type() == PredicateType.EQUALITY) {
                    fraction *= stats.equalitySelectivity();
                } else if (predicate.type() == PredicateType.RANGE) {
                    fraction *= predicate.estimatedFraction();
                }
            }

            return Math.max(fraction, 1.0 / totalRows);
        }

        int prefixLength(
                CompositeIndex index,
                QueryWorkload query
        ) {
            Set<String> equality = new HashSet<>();
            Set<String> ranges = new HashSet<>();

            for (Predicate predicate : query.predicates()) {
                if (predicate.type() == PredicateType.EQUALITY) {
                    equality.add(predicate.column());
                } else if (predicate.type() == PredicateType.RANGE) {
                    ranges.add(predicate.column());
                }
            }

            int matched = 0;
            boolean rangeEncountered = false;

            for (String column : index.columns()) {
                if (equality.contains(column) && !rangeEncountered) {
                    matched++;
                } else if (ranges.contains(column) &&
                           !rangeEncountered) {
                    matched++;
                    rangeEncountered = true;
                    break;
                } else {
                    break;
                }
            }

            return matched;
        }

        boolean orderingCovered(
                CompositeIndex index,
                QueryWorkload query
        ) {
            if (query.ordering().isEmpty() ||
                query.ordering().size() > index.columns().size()) {
                return false;
            }

            return index.columns()
                .subList(0, query.ordering().size())
                .equals(query.ordering());
        }

        boolean coveringCandidate(
                CompositeIndex index,
                QueryWorkload query
        ) {
            Set<String> required = new HashSet<>(
                query.projection()
            );

            required.addAll(query.ordering());

            query.predicates().forEach(
                predicate -> required.add(predicate.column())
            );

            return index.columns().containsAll(required);
        }

        @Override
        public IndexEvaluation evaluate(
                CompositeIndex index,
                QueryWorkload query
        ) {
            index.columns().forEach(this::validateColumn);

            int prefix = prefixLength(index, query);
            double selectivity = estimateSelectivity(query);

            boolean ordered = orderingCovered(index, query);
            boolean covering = coveringCandidate(index, query);

            double cost;

            if (prefix == 0) {
                cost = totalRows * 0.8;
            } else {
                cost = Math.log(totalRows + 1.0) +
                    selectivity * totalRows * 0.12;

                if (ordered) cost *= 0.85;
                if (covering) cost *= 0.75;
            }

            return new IndexEvaluation(
                index.name(),
                prefix,
                selectivity,
                ordered,
                covering,
                cost
            );
        }

        List<IndexEvaluation> recommend(
                QueryWorkload query,
                List<CompositeIndex> indexes
        ) {
            return indexes.stream()
                .filter(CompositeIndex::active)
                .map(index -> evaluate(index, query))
                .sorted(
                    Comparator.comparingDouble(
                        IndexEvaluation::estimatedCost
                    )
                )
                .toList();
        }

        List<String> suggestColumnOrder(QueryWorkload query) {
            List<String> equality = query.predicates()
                .stream()
                .filter(p -> p.type() == PredicateType.EQUALITY)
                .map(Predicate::column)
                .distinct()
                .collect(Collectors.toCollection(ArrayList::new));

            List<String> ranges = query.predicates()
                .stream()
                .filter(p -> p.type() == PredicateType.RANGE)
                .map(Predicate::column)
                .distinct()
                .toList();

            equality.forEach(this::validateColumn);
            ranges.forEach(this::validateColumn);
            query.ordering().forEach(this::validateColumn);

            equality.sort(
                Comparator.comparingLong(
                    (String column) ->
                        statistics.get(column).distinctValues()
                ).reversed()
            );

            LinkedHashSet<String> result = new LinkedHashSet<>();

            result.addAll(equality);
            result.addAll(ranges);
            result.addAll(query.ordering());

            return List.copyOf(result);
        }

        Map<String, String> findRedundant(
                List<CompositeIndex> indexes
        ) {
            Map<String, String> redundant = new LinkedHashMap<>();

            for (CompositeIndex candidate : indexes) {
                for (CompositeIndex existing : indexes) {
                    if (candidate.name().equals(existing.name()) ||
                        !existing.active() ||
                        existing.columns().size() <
                            candidate.columns().size()) {
                        continue;
                    }

                    List<String> prefix = existing.columns()
                        .subList(0, candidate.columns().size());

                    if (prefix.equals(candidate.columns())) {
                        redundant.put(
                            candidate.name(),
                            existing.name()
                        );

                        break;
                    }
                }
            }

            return redundant;
        }
    }

    static class WorkloadService {
        private final IndexCatalog catalog;
        private final IndexAdvisor advisor;

        WorkloadService(
                IndexCatalog catalog,
                IndexAdvisor advisor
        ) {
            this.catalog = catalog;
            this.advisor = advisor;
        }

        Map<String, List<IndexEvaluation>> evaluate(
                List<QueryWorkload> queries
        ) {
            Map<String, List<IndexEvaluation>> report =
                new LinkedHashMap<>();

            for (QueryWorkload query : queries) {
                report.put(
                    query.name(),
                    advisor.recommend(
                        query,
                        catalog.activeIndexes()
                    )
                );
            }

            return Collections.unmodifiableMap(report);
        }
    }

    public static void main(String[] args) {

        try {
            IndexAdvisor advisor = new IndexAdvisor(List.of(
                new ColumnStatistics(
                    "customer_id", 10000, 1000000, 0.0
                ),
                new ColumnStatistics(
                    "status", 5, 1000000, 0.0
                ),
                new ColumnStatistics(
                    "region", 4, 1000000, 0.0
                ),
                new ColumnStatistics(
                    "created_at", 900000, 1000000, 0.0
                ),
                new ColumnStatistics(
                    "total_amount", 500000, 1000000, 0.0
                ),
                new ColumnStatistics(
                    "payment_method", 6, 1000000, 0.0
                )
            ));

            IndexCatalog catalog = new IndexCatalog();

            catalog.register(new CompositeIndex(
                "idx_customer_status_date",
                List.of("customer_id", "status", "created_at"),
                false,
                true
            ));

            catalog.register(new CompositeIndex(
                "idx_status_customer_date",
                List.of("status", "customer_id", "created_at"),
                false,
                true
            ));

            catalog.register(new CompositeIndex(
                "idx_status_date",
                List.of("status", "created_at"),
                false,
                true
            ));

            catalog.register(new CompositeIndex(
                "idx_region_amount",
                List.of("region", "total_amount"),
                false,
                true
            ));

            List<QueryWorkload> queries = List.of(
                new QueryWorkload(
                    "Customer order history",
                    List.of(
                        Predicate.equality("customer_id"),
                        Predicate.equality("status"),
                        Predicate.range("created_at", 0.20)
                    ),
                    List.of("created_at"),
                    List.of("total_amount"),
                    150
                ),
                new QueryWorkload(
                    "Recent paid orders",
                    List.of(
                        Predicate.equality("status"),
                        Predicate.range("created_at", 0.10)
                    ),
                    List.of("created_at"),
                    List.of("customer_id"),
                    300
                ),
                new QueryWorkload(
                    "Regional sales",
                    List.of(
                        Predicate.equality("region"),
                        Predicate.range("total_amount", 0.15)
                    ),
                    List.of(),
                    List.of("total_amount"),
                    40
                )
            );

            WorkloadService service = new WorkloadService(
                catalog,
                advisor
            );

            System.out.println(
                "\nENTERPRISE COMPOSITE INDEX EVALUATION"
            );

            Map<String, List<IndexEvaluation>> report =
                service.evaluate(queries);

            report.forEach((query, evaluations) -> {
                System.out.println("\nQuery: " + query);

                evaluations.forEach(result ->
                    System.out.printf(
                        Locale.ROOT,
                        "%-35s Prefix=%d Selectivity=%.6f " +
                        "Ordering=%s Covering=%s Cost=%.2f%n",
                        result.indexName(),
                        result.prefixLength(),
                        result.selectivity(),
                        result.orderingCovered(),
                        result.coveringCandidate(),
                        result.estimatedCost()
                    )
                );
            });

            System.out.println("\nSUGGESTED INDEX ORDER");

            System.out.println(
                advisor.suggestColumnOrder(queries.get(0))
            );

            System.out.println("\nREDUNDANCY REVIEW");

            System.out.println(
                advisor.findRedundant(catalog.activeIndexes())
            );

            System.out.println("\nINVALID COLUMN TEST");

            try {
                QueryWorkload invalid = new QueryWorkload(
                    "Invalid query",
                    List.of(Predicate.equality("missing_column")),
                    List.of(),
                    List.of(),
                    1
                );

                advisor.estimateSelectivity(invalid);

            } catch (IndexPolicyException exception) {
                System.out.println(exception.getMessage());
            }

            System.out.println("\nEVALUATION COMPLETED");

        } catch (RuntimeException exception) {
            System.err.println(
                "Index evaluation failed: " + exception.getMessage()
            );

            System.exitCode = 1;
        }
    }
}
