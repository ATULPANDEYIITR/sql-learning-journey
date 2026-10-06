import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/*
 * CROSS JOIN ENTERPRISE COMBINATION ENGINE
 *
 * Java 17+
 *
 * Scenario:
 * An enterprise platform evaluates combinations of repositories, deployment
 * environments, test suites, and release policies. The Cartesian product
 * establishes the complete candidate space, while explicit domain rules
 * determine which combinations are operationally valid.
 */
public class CrossJoinEnterpriseDemo {

    enum Environment {
        STAGING,
        PRODUCTION
    }

    enum TestSuite {
        UNIT,
        INTEGRATION,
        SECURITY
    }

    enum ReleasePolicy {
        STANDARD,
        REGULATED
    }

    record DeploymentCandidate(
            String repository,
            Environment environment,
            TestSuite testSuite,
            ReleasePolicy releasePolicy
    ) {
        DeploymentCandidate {
            if (repository == null || repository.isBlank()) {
                throw new IllegalArgumentException(
                        "Repository name must not be blank."
                );
            }

            Objects.requireNonNull(environment);
            Objects.requireNonNull(testSuite);
            Objects.requireNonNull(releasePolicy);
        }
    }

    interface CandidatePolicy {
        boolean accepts(DeploymentCandidate candidate);

        String description();
    }

    static final class ProductionSecurityPolicy implements CandidatePolicy {

        @Override
        public boolean accepts(DeploymentCandidate candidate) {
            /*
             * Security testing in production requires the regulated release
             * policy. This is a domain rule applied after candidate generation.
             */
            return candidate.environment() != Environment.PRODUCTION
                    || candidate.testSuite() != TestSuite.SECURITY
                    || candidate.releasePolicy() == ReleasePolicy.REGULATED;
        }

        @Override
        public String description() {
            return "Production security candidates require REGULATED policy";
        }
    }

    static final class RegulatedPolicyScope implements CandidatePolicy {

        @Override
        public boolean accepts(DeploymentCandidate candidate) {
            /*
             * A regulated policy is meaningful only for production deployments.
             * This prevents semantically invalid combinations.
             */
            return candidate.releasePolicy() != ReleasePolicy.REGULATED
                    || candidate.environment() == Environment.PRODUCTION;
        }

        @Override
        public String description() {
            return "REGULATED policy is restricted to production";
        }
    }

    static final class CartesianCombinationEngine {
        private final long maximumCandidates;
        private final List<CandidatePolicy> policies;

        CartesianCombinationEngine(
                long maximumCandidates,
                List<CandidatePolicy> policies
        ) {
            if (maximumCandidates <= 0) {
                throw new IllegalArgumentException(
                        "maximumCandidates must be positive."
                );
            }

            this.maximumCandidates = maximumCandidates;
            this.policies = List.copyOf(policies);
        }

        long calculateCardinality(List<? extends List<?>> dimensions) {
            long result = 1;

            for (List<?> dimension : dimensions) {
                Objects.requireNonNull(dimension);

                if (dimension.isEmpty()) {
                    return 0;
                }

                if (result > maximumCandidates / dimension.size()) {
                    throw new IllegalStateException(
                            "Cartesian product exceeds configured safety limit."
                    );
                }

                result *= dimension.size();
            }

            return result;
        }

        List<DeploymentCandidate> generate(
                List<String> repositories,
                List<Environment> environments,
                List<TestSuite> testSuites,
                List<ReleasePolicy> releasePolicies
        ) {
            List<List<?>> dimensions = List.of(
                    repositories,
                    environments,
                    testSuites,
                    releasePolicies
            );

            long cardinality = calculateCardinality(dimensions);

            if (cardinality == 0) {
                return List.of();
            }

            /*
             * The capacity is bounded by the known Cartesian cardinality.
             * The application still filters candidates as they are created.
             */
            List<DeploymentCandidate> accepted =
                    new ArrayList<>((int) Math.min(cardinality, Integer.MAX_VALUE));

            for (String repository : repositories) {
                for (Environment environment : environments) {
                    for (TestSuite testSuite : testSuites) {
                        for (ReleasePolicy releasePolicy : releasePolicies) {
                            DeploymentCandidate candidate =
                                    new DeploymentCandidate(
                                            repository,
                                            environment,
                                            testSuite,
                                            releasePolicy
                                    );

                            if (policies.stream().allMatch(
                                    policy -> policy.accepts(candidate)
                            )) {
                                accepted.add(candidate);
                            }
                        }
                    }
                }
            }

            return accepted;
        }
    }

    static final class CombinationStatistics {
        private final long candidateCount;
        private final long acceptedCount;
        private final long rejectedCount;

        CombinationStatistics(
                long candidateCount,
                long acceptedCount,
                long rejectedCount
        ) {
            this.candidateCount = candidateCount;
            this.acceptedCount = acceptedCount;
            this.rejectedCount = rejectedCount;
        }

        void print() {
            System.out.println("Candidate combinations: " + candidateCount);
            System.out.println("Accepted combinations:  " + acceptedCount);
            System.out.println("Rejected combinations:  " + rejectedCount);
        }
    }

    private static void heading(String title) {
        System.out.println();
        System.out.println("=".repeat(78));
        System.out.println(title);
        System.out.println("=".repeat(78));
    }

    private static void demonstrateBasicCartesianProduct() {
        heading("Basic Cartesian Product");

        List<String> repositories = List.of("payments-api", "customer-web");
        List<Environment> environments = List.of(
                Environment.STAGING,
                Environment.PRODUCTION
        );

        long rows = (long) repositories.size() * environments.size();

        System.out.println(
                repositories.size() + " repositories × "
                        + environments.size() + " environments = "
                        + rows + " combinations"
        );

        for (String repository : repositories) {
            for (Environment environment : environments) {
                System.out.println(repository + " -> " + environment);
            }
        }
    }

    private static void demonstrateEnterpriseModel() {
        heading("Enterprise Deployment Candidate Model");

        List<String> repositories = List.of(
                "payments-api",
                "customer-web",
                "analytics-worker"
        );

        List<Environment> environments = List.of(
                Environment.STAGING,
                Environment.PRODUCTION
        );

        List<TestSuite> testSuites = List.of(
                TestSuite.UNIT,
                TestSuite.INTEGRATION,
                TestSuite.SECURITY
        );

        List<ReleasePolicy> releasePolicies = List.of(
                ReleasePolicy.STANDARD,
                ReleasePolicy.REGULATED
        );

        List<CandidatePolicy> policies = List.of(
                new ProductionSecurityPolicy(),
                new RegulatedPolicyScope()
        );

        CartesianCombinationEngine engine =
                new CartesianCombinationEngine(10_000, policies);

        List<List<?>> dimensions = List.of(
                repositories,
                environments,
                testSuites,
                releasePolicies
        );

        long candidateCount = engine.calculateCardinality(dimensions);

        List<DeploymentCandidate> accepted = engine.generate(
                repositories,
                environments,
                testSuites,
                releasePolicies
        );

        CombinationStatistics statistics =
                new CombinationStatistics(
                        candidateCount,
                        accepted.size(),
                        candidateCount - accepted.size()
                );

        statistics.print();

        System.out.println("\nAccepted candidate preview:");

        accepted.stream()
                .limit(12)
                .forEach(System.out::println);
    }

    private static void demonstrateEmptyDimension() {
        heading("Empty Dimension");

        List<String> repositories = List.of("api", "web");
        List<Environment> environments = Collections.emptyList();

        long rows = (long) repositories.size() * environments.size();

        System.out.println("Rows produced: " + rows);
        System.out.println(
                "An empty dimension causes the Cartesian product to contain no rows."
        );
    }

    private static void demonstrateDuplicateInputs() {
        heading("Duplicate Inputs");

        List<String> teams = Arrays.asList(
                "platform",
                "platform",
                "security"
        );

        List<String> environments = List.of("staging", "production");

        List<String> rawPairs = new ArrayList<>();

        for (String team : teams) {
            for (String environment : environments) {
                rawPairs.add(team + ":" + environment);
            }
        }

        Set<String> uniquePairs = new HashSet<>(rawPairs);

        System.out.println("Raw Cartesian rows: " + rawPairs.size());
        System.out.println("Unique value pairs: " + uniquePairs.size());
        System.out.println(
                "Uniqueness is a separate concern from Cartesian-product generation."
        );
    }

    private static void demonstrateRiskControl() {
        heading("Cartesian Explosion Protection");

        List<List<Integer>> safeDimensions = List.of(
                List.of(1, 2, 3, 4, 5),
                List.of(1, 2, 3),
                List.of(1, 2)
        );

        CartesianCombinationEngine engine =
                new CartesianCombinationEngine(
                        5_000,
                        List.of()
                );

        System.out.println(
                "Safe cardinality: "
                        + engine.calculateCardinality(
                                new ArrayList<>(safeDimensions)
                        )
        );

        List<Integer> thousand = new ArrayList<>();
        for (int i = 0; i < 1_000; i++) {
            thousand.add(i);
        }

        try {
            engine.calculateCardinality(
                    List.of(thousand, thousand, thousand)
            );

            throw new IllegalStateException(
                    "Expected large Cartesian product to be rejected."
            );
        } catch (IllegalStateException expected) {
            System.out.println(
                    "Large Cartesian product rejected before materialization."
            );
        }
    }

    private static void runValidation() {
        heading("Validation");

        CartesianCombinationEngine engine =
                new CartesianCombinationEngine(100, List.of());

        long expected = engine.calculateCardinality(
                List.of(
                        List.of("a", "b"),
                        List.of("x", "y"),
                        List.of(1, 2)
                )
        );

        if (expected != 8) {
            throw new AssertionError("Cardinality calculation failed.");
        }

        long empty = engine.calculateCardinality(
                List.of(
                        List.of("a", "b"),
                        List.of()
                )
        );

        if (empty != 0) {
            throw new AssertionError("Empty-dimension calculation failed.");
        }

        System.out.println("Validation checks passed.");
    }

    public static void main(String[] args) {
        demonstrateBasicCartesianProduct();
        demonstrateEnterpriseModel();
        demonstrateEmptyDimension();
        demonstrateDuplicateInputs();
        demonstrateRiskControl();
        runValidation();

        heading("Operational Rule");

        System.out.println(
                "A CROSS JOIN represents an intentional Cartesian expansion. "
                        + "Estimate the product cardinality before materializing "
                        + "large result sets, and apply domain filtering or bounded "
                        + "processing when the candidate space is large."
        );
    }
}
