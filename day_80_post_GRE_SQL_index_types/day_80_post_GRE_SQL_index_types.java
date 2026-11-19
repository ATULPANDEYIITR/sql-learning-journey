import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/*
 * Enterprise PostgreSQL Index Governance System.
 *
 * Java 17, standard library only.
 *
 * Models:
 * - Index definitions and capabilities
 * - Workload registration
 * - Index recommendation policies
 * - Workload assessment
 * - Index lifecycle and validation
 * - Operational maintenance considerations
 */

public class PostgreSQLIndexGovernance {

    enum IndexType {
        BTREE,
        HASH,
        GIST,
        SPGIST,
        GIN,
        BRIN
    }

    enum QueryPattern {
        EQUALITY,
        RANGE,
        ORDERING,
        ARRAY_MEMBERSHIP,
        CONTAINS,
        SPATIAL,
        PREFIX,
        FULL_TEXT,
        LARGE_TABLE_RANGE
    }

    enum IndexStatus {
        PROPOSED,
        APPROVED,
        ACTIVE,
        DISABLED,
        RETIRED
    }

    enum RiskLevel {
        LOW,
        MEDIUM,
        HIGH
    }

    static class GovernanceException extends RuntimeException {
        GovernanceException(String message) {
            super(message);
        }
    }

    record IndexCapability(
        IndexType type,
        Set<QueryPattern> supportedPatterns,
        String description,
        double maintenanceFactor
    ) {
        IndexCapability {
            Objects.requireNonNull(type);
            Objects.requireNonNull(supportedPatterns);
            Objects.requireNonNull(description);

            if (maintenanceFactor < 0 || maintenanceFactor > 1) {
                throw new IllegalArgumentException(
                    "Maintenance factor must be between 0 and 1."
                );
            }

            supportedPatterns = Set.copyOf(supportedPatterns);
        }
    }

    record DatabaseWorkload(
        String name,
        QueryPattern pattern,
        long rowCount,
        double selectivity,
        double updateRate,
        double correlation,
        boolean requiresOrdering
    ) {
        DatabaseWorkload {
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException("Workload name required.");
            }

            Objects.requireNonNull(pattern);

            if (rowCount <= 0) {
                throw new IllegalArgumentException(
                    "Row count must be positive."
                );
            }

            validateRatio(selectivity, "selectivity");
            validateRatio(updateRate, "updateRate");
            validateRatio(correlation, "correlation");
        }

        private static void validateRatio(double value, String field) {
            if (!Double.isFinite(value) || value < 0 || value > 1) {
                throw new IllegalArgumentException(
                    field + " must be between 0 and 1."
                );
            }
        }
    }

    record IndexDefinition(
        String name,
        String table,
        String column,
        IndexType type,
        boolean unique,
        String operatorClass,
        IndexStatus status,
        Instant createdAt
    ) {
        IndexDefinition {
            validateIdentifier(name);
            validateIdentifier(table);
            validateIdentifier(column);

            Objects.requireNonNull(type);
            Objects.requireNonNull(status);
            Objects.requireNonNull(createdAt);

            if (unique && type != IndexType.BTREE) {
                throw new IllegalArgumentException(
                    "Unique indexes must use B-tree in this model."
                );
            }

            if (operatorClass != null &&
                !operatorClass.matches("[a-zA-Z_][a-zA-Z0-9_]*")) {
                throw new IllegalArgumentException(
                    "Invalid operator class identifier."
                );
            }
        }

        private static void validateIdentifier(String value) {
            if (value == null ||
                !value.matches("[a-zA-Z_][a-zA-Z0-9_]*")) {
                throw new IllegalArgumentException(
                    "Invalid SQL identifier: " + value
                );
            }
        }

        IndexDefinition withStatus(IndexStatus nextStatus) {
            return new IndexDefinition(
                name,
                table,
                column,
                type,
                unique,
                operatorClass,
                nextStatus,
                createdAt
            );
        }
    }

    record Recommendation(
        IndexType type,
        double score,
        boolean applicable,
        List<String> reasons,
        RiskLevel risk
    ) {
        Recommendation {
            reasons = List.copyOf(reasons);
        }
    }

    interface WorkloadPolicy {
        boolean supports(
            IndexCapability capability,
            DatabaseWorkload workload
        );

        double calculate(
            IndexCapability capability,
            DatabaseWorkload workload
        );

        RiskLevel risk(
            IndexCapability capability,
            DatabaseWorkload workload
        );
    }

    static class DefaultWorkloadPolicy implements WorkloadPolicy {

        @Override
        public boolean supports(
            IndexCapability capability,
            DatabaseWorkload workload
        ) {
            return capability.supportedPatterns().contains(
                workload.pattern()
            );
        }

        @Override
        public double calculate(
            IndexCapability capability,
            DatabaseWorkload workload
        ) {
            double score = 50;

            switch (capability.type()) {
                case BTREE -> {
                    score += 15;

                    if (workload.requiresOrdering()) {
                        score += 20;
                    }

                    if (workload.selectivity() < 0.05) {
                        score += 10;
                    }
                }

                case HASH -> score += 12;

                case GIST -> score += 20;

                case SPGIST -> score += 20;

                case GIN -> {
                    score += 25;

                    if (workload.updateRate() > 0.5) {
                        score -= 20;
                    }
                }

                case BRIN -> {
                    score += 15;
                    score += workload.correlation() * 30;

                    if (workload.rowCount() >= 1_000_000) {
                        score += 15;
                    }

                    if (workload.correlation() < 0.4) {
                        score -= 30;
                    }
                }
            }

            score -= workload.updateRate() * 15;
            score -= capability.maintenanceFactor() * 10;

            return Math.max(0, Math.min(100, score));
        }

        @Override
        public RiskLevel risk(
            IndexCapability capability,
            DatabaseWorkload workload
        ) {
            if (capability.type() == IndexType.GIN &&
                workload.updateRate() > 0.5) {
                return RiskLevel.HIGH;
            }

            if (capability.type() == IndexType.BRIN &&
                workload.correlation() < 0.4) {
                return RiskLevel.HIGH;
            }

            if (workload.updateRate() > 0.4) {
                return RiskLevel.MEDIUM;
            }

            return RiskLevel.LOW;
        }
    }

    static class IndexCatalog {

        private final Map<IndexType, IndexCapability> capabilities =
            new EnumMap<>(IndexType.class);

        IndexCatalog() {
            register(
                IndexType.BTREE,
                EnumSet.of(
                    QueryPattern.EQUALITY,
                    QueryPattern.RANGE,
                    QueryPattern.ORDERING,
                    QueryPattern.PREFIX
                ),
                "Ordered balanced search tree",
                0.10
            );

            register(
                IndexType.HASH,
                EnumSet.of(QueryPattern.EQUALITY),
                "Hash-based equality index",
                0.08
            );

            register(
                IndexType.GIST,
                EnumSet.of(
                    QueryPattern.RANGE,
                    QueryPattern.SPATIAL,
                    QueryPattern.CONTAINS
                ),
                "Generalized Search Tree",
                0.16
            );

            register(
                IndexType.SPGIST,
                EnumSet.of(
                    QueryPattern.SPATIAL,
                    QueryPattern.PREFIX,
                    QueryPattern.EQUALITY
                ),
                "Space-partitioned search tree",
                0.12
            );

            register(
                IndexType.GIN,
                EnumSet.of(
                    QueryPattern.ARRAY_MEMBERSHIP,
                    QueryPattern.CONTAINS,
                    QueryPattern.FULL_TEXT
                ),
                "Inverted index",
                0.30
            );

            register(
                IndexType.BRIN,
                EnumSet.of(
                    QueryPattern.RANGE,
                    QueryPattern.LARGE_TABLE_RANGE
                ),
                "Block Range Index",
                0.02
            );
        }

        private void register(
            IndexType type,
            Set<QueryPattern> patterns,
            String description,
            double maintenanceFactor
        ) {
            capabilities.put(
                type,
                new IndexCapability(
                    type,
                    patterns,
                    description,
                    maintenanceFactor
                )
            );
        }

        List<IndexCapability> all() {
            return List.copyOf(capabilities.values());
        }
    }

    static class IndexAssessmentService {

        private final IndexCatalog catalog;
        private final WorkloadPolicy policy;

        IndexAssessmentService(
            IndexCatalog catalog,
            WorkloadPolicy policy
        ) {
            this.catalog = Objects.requireNonNull(catalog);
            this.policy = Objects.requireNonNull(policy);
        }

        List<Recommendation> assess(DatabaseWorkload workload) {
            Objects.requireNonNull(workload);

            List<Recommendation> results = new ArrayList<>();

            for (IndexCapability capability : catalog.all()) {
                boolean applicable = policy.supports(
                    capability,
                    workload
                );

                if (!applicable) {
                    results.add(
                        new Recommendation(
                            capability.type(),
                            0,
                            false,
                            List.of("Unsupported access pattern."),
                            RiskLevel.LOW
                        )
                    );

                    continue;
                }

                double score = policy.calculate(
                    capability,
                    workload
                );

                List<String> reasons = new ArrayList<>();
                reasons.add("Index supports the workload operator pattern.");

                reasons.add(
                    "Maintenance factor: " +
                    capability.maintenanceFactor()
                );

                if (workload.requiresOrdering() &&
                    capability.type() == IndexType.BTREE) {
                    reasons.add("Can satisfy ordered retrieval.");
                }

                if (capability.type() == IndexType.BRIN) {
                    reasons.add(
                        "Effectiveness depends on physical correlation."
                    );
                }

                if (capability.type() == IndexType.GIN) {
                    reasons.add(
                        "Component-level lookup can increase write costs."
                    );
                }

                results.add(
                    new Recommendation(
                        capability.type(),
                        score,
                        true,
                        reasons,
                        policy.risk(capability, workload)
                    )
                );
            }

            return results.stream()
                .sorted(
                    Comparator.comparingDouble(
                        Recommendation::score
                    ).reversed()
                )
                .toList();
        }
    }

    static class IndexLifecycleService {

        private final Map<String, IndexDefinition> indexes =
            new HashMap<>();

        public synchronized void propose(IndexDefinition definition) {
            Objects.requireNonNull(definition);

            if (indexes.containsKey(definition.name())) {
                throw new GovernanceException(
                    "Index name already registered."
                );
            }

            if (definition.status() != IndexStatus.PROPOSED) {
                throw new GovernanceException(
                    "New indexes must begin in PROPOSED state."
                );
            }

            indexes.put(definition.name(), definition);
        }

        public synchronized void approve(String name) {
            transition(name, IndexStatus.PROPOSED, IndexStatus.APPROVED);
        }

        public synchronized void activate(String name) {
            transition(name, IndexStatus.APPROVED, IndexStatus.ACTIVE);
        }

        public synchronized void disable(String name) {
            IndexDefinition definition = require(name);

            if (definition.status() != IndexStatus.ACTIVE) {
                throw new GovernanceException(
                    "Only active indexes can be disabled."
                );
            }

            indexes.put(
                name,
                definition.withStatus(IndexStatus.DISABLED)
            );
        }

        public synchronized void retire(String name) {
            IndexDefinition definition = require(name);

            if (definition.status() == IndexStatus.RETIRED) {
                throw new GovernanceException("Already retired.");
            }

            indexes.put(
                name,
                definition.withStatus(IndexStatus.RETIRED)
            );
        }

        private void transition(
            String name,
            IndexStatus expected,
            IndexStatus next
        ) {
            IndexDefinition definition = require(name);

            if (definition.status() != expected) {
                throw new GovernanceException(
                    "Invalid transition: " +
                    definition.status() + " -> " + next
                );
            }

            indexes.put(name, definition.withStatus(next));
        }

        private IndexDefinition require(String name) {
            IndexDefinition definition = indexes.get(name);

            if (definition == null) {
                throw new GovernanceException(
                    "Unknown index: " + name
                );
            }

            return definition;
        }

        public synchronized List<IndexDefinition> activeIndexes() {
            return indexes.values().stream()
                .filter(index -> index.status() == IndexStatus.ACTIVE)
                .toList();
        }
    }

    private static void runTests(
        IndexAssessmentService service,
        IndexLifecycleService lifecycle
    ) {
        DatabaseWorkload equality = new DatabaseWorkload(
            "Customer lookup",
            QueryPattern.EQUALITY,
            500_000,
            0.001,
            0.05,
            0,
            false
        );

        if (service.assess(equality).get(0).type() != IndexType.BTREE) {
            throw new AssertionError("B-tree test failed.");
        }

        DatabaseWorkload text = new DatabaseWorkload(
            "Document search",
            QueryPattern.FULL_TEXT,
            2_000_000,
            0.005,
            0.10,
            0,
            false
        );

        if (service.assess(text).get(0).type() != IndexType.GIN) {
            throw new AssertionError("GIN test failed.");
        }

        DatabaseWorkload historical = new DatabaseWorkload(
            "Historical events",
            QueryPattern.LARGE_TABLE_RANGE,
            10_000_000,
            0.05,
            0.02,
            0.99,
            false
        );

        if (service.assess(historical).get(0).type() != IndexType.BRIN) {
            throw new AssertionError("BRIN test failed.");
        }

        IndexDefinition definition = new IndexDefinition(
            "idx_customer_email",
            "customers",
            "email",
            IndexType.BTREE,
            true,
            null,
            IndexStatus.PROPOSED,
            Instant.now()
        );

        lifecycle.propose(definition);
        lifecycle.approve(definition.name());
        lifecycle.activate(definition.name());

        if (lifecycle.activeIndexes().size() != 1) {
            throw new AssertionError("Lifecycle test failed.");
        }

        System.out.println("\nAll Java tests passed.");
    }

    private static void printAssessment(
        DatabaseWorkload workload,
        List<Recommendation> recommendations
    ) {
        System.out.println("\nWorkload: " + workload.name());

        recommendations.stream()
            .filter(Recommendation::applicable)
            .limit(3)
            .forEach(recommendation -> {
                System.out.printf(
                    "  %-8s Score: %5.2f Risk: %s%n",
                    recommendation.type(),
                    recommendation.score(),
                    recommendation.risk()
                );

                recommendation.reasons().forEach(
                    reason -> System.out.println("    - " + reason)
                );
            });
    }

    public static void main(String[] args) {
        try {
            System.out.println(
                "POSTGRESQL ENTERPRISE INDEX GOVERNANCE"
            );

            IndexCatalog catalog = new IndexCatalog();

            IndexAssessmentService assessmentService =
                new IndexAssessmentService(
                    catalog,
                    new DefaultWorkloadPolicy()
                );

            IndexLifecycleService lifecycle =
                new IndexLifecycleService();

            List<DatabaseWorkload> workloads = List.of(
                new DatabaseWorkload(
                    "Customer lookup",
                    QueryPattern.EQUALITY,
                    500_000,
                    0.001,
                    0.05,
                    0,
                    false
                ),
                new DatabaseWorkload(
                    "Order history",
                    QueryPattern.RANGE,
                    5_000_000,
                    0.02,
                    0.10,
                    0.95,
                    false
                ),
                new DatabaseWorkload(
                    "JSONB containment",
                    QueryPattern.CONTAINS,
                    1_000_000,
                    0.01,
                    0.60,
                    0,
                    false
                ),
                new DatabaseWorkload(
                    "Array membership",
                    QueryPattern.ARRAY_MEMBERSHIP,
                    800_000,
                    0.05,
                    0.20,
                    0,
                    false
                ),
                new DatabaseWorkload(
                    "Spatial lookup",
                    QueryPattern.SPATIAL,
                    300_000,
                    0.01,
                    0.05,
                    0,
                    false
                ),
                new DatabaseWorkload(
                    "Full-text search",
                    QueryPattern.FULL_TEXT,
                    2_000_000,
                    0.005,
                    0.10,
                    0,
                    false
                )
            );

            for (DatabaseWorkload workload : workloads) {
                printAssessment(
                    workload,
                    assessmentService.assess(workload)
                );
            }

            IndexDefinition customerIndex = new IndexDefinition(
                "idx_customer_email",
                "customers",
                "email",
                IndexType.BTREE,
                true,
                null,
                IndexStatus.PROPOSED,
                Instant.now()
            );

            lifecycle.propose(customerIndex);
            lifecycle.approve(customerIndex.name());
            lifecycle.activate(customerIndex.name());

            System.out.println("\nACTIVE INDEXES");

            lifecycle.activeIndexes().forEach(
                index -> System.out.println(
                    index.name() + " ON " +
                    index.table() + "(" + index.column() + ")"
                )
            );

            runTests(assessmentService, lifecycle);

        } catch (Exception exception) {
            System.err.println(
                "Governance failure: " + exception.getMessage()
            );

            System.exitCode = 1;
        }
    }
}
