import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/*
 * EXPLAIN ANALYZE: Enterprise PostgreSQL execution-plan governance.
 *
 * Java 17 implementation:
 * - Immutable execution-plan domain records
 * - Typed execution nodes
 * - Cardinality estimation analysis
 * - Loop-aware execution statistics
 * - Buffer monitoring
 * - Configurable performance policies
 * - Verification service
 * - Benchmark reporting
 * - Custom exceptions and validation
 *
 * Compile:
 * javac ExplainAnalyze.java
 *
 * Run:
 * java ExplainAnalyze
 */

public class ExplainAnalyze {

    enum NodeType {
        SEQ_SCAN,
        INDEX_SCAN,
        INDEX_ONLY_SCAN,
        NESTED_LOOP,
        HASH_JOIN,
        MERGE_JOIN,
        SORT,
        AGGREGATE
    }

    enum Severity {
        INFO,
        WARNING,
        CRITICAL
    }

    enum VerificationStatus {
        PASSED,
        FAILED
    }

    static class PlanException extends RuntimeException {
        PlanException(String message) {
            super(message);
        }
    }

    static class Validation {

        static double nonNegative(double value, String field) {
            if (!Double.isFinite(value) || value < 0) {
                throw new PlanException(
                    field + " must be finite and non-negative"
                );
            }
            return value;
        }

        static int nonNegative(int value, String field) {
            if (value < 0) {
                throw new PlanException(
                    field + " cannot be negative"
                );
            }
            return value;
        }
    }

    record BufferStats(
        long sharedHits,
        long sharedReads,
        long sharedDirtied
    ) {
        BufferStats {
            if (
                sharedHits < 0 ||
                sharedReads < 0 ||
                sharedDirtied < 0
            ) {
                throw new PlanException("Invalid buffer statistics");
            }
        }

        long totalAccesses() {
            return sharedHits + sharedReads;
        }
    }

    record ExecutionNode(
        NodeType type,
        String relation,
        double estimatedRows,
        double actualRowsPerLoop,
        int loops,
        double startupCost,
        double totalCost,
        double startupTimeMs,
        double totalTimeMs,
        BufferStats buffers,
        List<ExecutionNode> children
    ) {
        ExecutionNode {
            Objects.requireNonNull(type);
            Objects.requireNonNull(buffers);
            Objects.requireNonNull(children);

            relation = relation == null ? "" : relation;

            Validation.nonNegative(estimatedRows, "Estimated rows");
            Validation.nonNegative(actualRowsPerLoop, "Actual rows");
            Validation.nonNegative(loops, "Loops");
            Validation.nonNegative(startupCost, "Startup cost");
            Validation.nonNegative(totalCost, "Total cost");
            Validation.nonNegative(startupTimeMs, "Startup time");
            Validation.nonNegative(totalTimeMs, "Total time");

            children = List.copyOf(children);
        }

        double totalActualRows() {
            return actualRowsPerLoop * loops;
        }

        double accumulatedNodeTimeMs() {
            return totalTimeMs * loops;
        }

        double estimationRatio() {
            if (estimatedRows == 0) {
                return actualRowsPerLoop == 0
                    ? 1
                    : Double.POSITIVE_INFINITY;
            }

            if (actualRowsPerLoop == 0) {
                return Double.POSITIVE_INFINITY;
            }

            return Math.max(
                estimatedRows / actualRowsPerLoop,
                actualRowsPerLoop / estimatedRows
            );
        }
    }

    record QueryExecution(
        double planningTimeMs,
        double executionTimeMs,
        ExecutionNode root
    ) {
        QueryExecution {
            Validation.nonNegative(planningTimeMs, "Planning time");
            Validation.nonNegative(executionTimeMs, "Execution time");
            Objects.requireNonNull(root);
        }
    }

    record PerformancePolicy(
        double maxExecutionTimeMs,
        double maxPlanningTimeMs,
        double maxEstimationRatio,
        double maxNodeTimeMs,
        long maxSharedReads
    ) {
        PerformancePolicy {
            Validation.nonNegative(
                maxExecutionTimeMs, "Maximum execution time"
            );
            Validation.nonNegative(
                maxPlanningTimeMs, "Maximum planning time"
            );
            Validation.nonNegative(
                maxEstimationRatio, "Maximum estimation ratio"
            );
            Validation.nonNegative(
                maxNodeTimeMs, "Maximum node time"
            );
            if (maxEstimationRatio < 1) {
                throw new PlanException(
                    "Maximum estimation ratio must be at least 1"
                );
            }
            if (maxSharedReads < 0) {
                throw new PlanException("Invalid shared read limit");
            }
        }
    }

    record Finding(
        Severity severity,
        String component,
        String message
    ) {}

    record VerificationResult(
        VerificationStatus status,
        List<Finding> findings
    ) {
        VerificationResult {
            findings = List.copyOf(findings);
        }
    }

    static class PlanTraversal {

        static List<ExecutionNode> flatten(ExecutionNode root) {
            List<ExecutionNode> result = new ArrayList<>();
            Deque<ExecutionNode> stack = new ArrayDeque<>();

            stack.push(root);

            while (!stack.isEmpty()) {
                ExecutionNode node = stack.pop();
                result.add(node);

                List<ExecutionNode> children = node.children();

                for (int i = children.size() - 1; i >= 0; i--) {
                    stack.push(children.get(i));
                }
            }

            return result;
        }
    }

    static class PerformanceAnalyzer {

        private final PerformancePolicy policy;

        PerformanceAnalyzer(PerformancePolicy policy) {
            this.policy = Objects.requireNonNull(policy);
        }

        List<Finding> analyze(QueryExecution execution) {
            List<Finding> findings = new ArrayList<>();

            if (
                execution.executionTimeMs() >
                policy.maxExecutionTimeMs()
            ) {
                findings.add(new Finding(
                    Severity.CRITICAL,
                    "QUERY",
                    "Execution time exceeded the configured limit"
                ));
            }

            if (
                execution.planningTimeMs() >
                policy.maxPlanningTimeMs()
            ) {
                findings.add(new Finding(
                    Severity.WARNING,
                    "QUERY",
                    "Planning time exceeded the configured limit"
                ));
            }

            for (
                ExecutionNode node :
                PlanTraversal.flatten(execution.root())
            ) {
                inspect(node, findings);
            }

            if (findings.isEmpty()) {
                findings.add(new Finding(
                    Severity.INFO,
                    "QUERY",
                    "No configured performance issue detected"
                ));
            }

            return List.copyOf(findings);
        }

        private void inspect(
            ExecutionNode node,
            List<Finding> findings
        ) {
            if (node.loops() == 0) {
                findings.add(new Finding(
                    Severity.INFO,
                    node.type().name(),
                    "Node was not executed"
                ));
            }

            if (
                node.estimationRatio() >
                policy.maxEstimationRatio()
            ) {
                findings.add(new Finding(
                    Severity.WARNING,
                    node.type().name(),
                    "Significant estimated-versus-actual row difference"
                ));
            }

            if (
                node.accumulatedNodeTimeMs() >
                policy.maxNodeTimeMs()
            ) {
                findings.add(new Finding(
                    Severity.WARNING,
                    node.type().name(),
                    "High accumulated node execution time"
                ));
            }

            if (
                node.type() == NodeType.SEQ_SCAN &&
                node.totalTimeMs() > 20
            ) {
                findings.add(new Finding(
                    Severity.WARNING,
                    node.relation(),
                    "Expensive sequential scan"
                ));
            }

            if (
                node.buffers().sharedReads() >
                policy.maxSharedReads()
            ) {
                findings.add(new Finding(
                    Severity.WARNING,
                    node.type().name(),
                    "Shared block reads exceeded policy"
                ));
            }
        }

        VerificationResult verify(QueryExecution execution) {
            List<Finding> findings = analyze(execution);

            boolean passed = findings.stream().noneMatch(
                finding -> finding.severity() == Severity.CRITICAL
            );

            // Row estimation failures are also treated as merge-gate
            // failures in this stricter verification operation.
            boolean estimationPassed =
                PlanTraversal.flatten(execution.root())
                    .stream()
                    .allMatch(node ->
                        node.estimationRatio() <=
                        policy.maxEstimationRatio()
                    );

            return new VerificationResult(
                passed && estimationPassed
                    ? VerificationStatus.PASSED
                    : VerificationStatus.FAILED,
                findings
            );
        }
    }

    static class BenchmarkService {

        private final List<Double> measurements = new ArrayList<>();

        void record(double milliseconds) {
            measurements.add(
                Validation.nonNegative(milliseconds, "Measurement")
            );
        }

        Map<String, Double> summarize() {
            if (measurements.isEmpty()) {
                throw new PlanException("No benchmark samples");
            }

            List<Double> sorted = new ArrayList<>(measurements);
            Collections.sort(sorted);

            double sum = sorted.stream()
                .mapToDouble(Double::doubleValue)
                .sum();

            int n = sorted.size();

            double median = n % 2 == 0
                ? (sorted.get(n / 2 - 1) + sorted.get(n / 2)) / 2
                : sorted.get(n / 2);

            Map<String, Double> result = new TreeMap<>();

            result.put("runs", (double) n);
            result.put("minimum_ms", sorted.get(0));
            result.put("maximum_ms", sorted.get(n - 1));
            result.put("average_ms", sum / n);
            result.put("median_ms", median);

            return Collections.unmodifiableMap(result);
        }
    }

    static ExecutionNode samplePlan() {

        ExecutionNode customerScan = new ExecutionNode(
            NodeType.INDEX_SCAN,
            "customers",
            100,
            100,
            1,
            0.25,
            10,
            0.02,
            0.40,
            new BufferStats(20, 0, 0),
            List.of()
        );

        ExecutionNode orderScan = new ExecutionNode(
            NodeType.INDEX_SCAN,
            "orders",
            1,
            2,
            100,
            0.20,
            2,
            0.01,
            0.025,
            new BufferStats(200, 3, 0),
            List.of()
        );

        return new ExecutionNode(
            NodeType.NESTED_LOOP,
            "",
            100,
            200,
            1,
            0.50,
            250,
            0.10,
            5.20,
            new BufferStats(220, 3, 0),
            List.of(customerScan, orderScan)
        );
    }

    static void printNode(ExecutionNode node, int depth) {
        String indent = "  ".repeat(depth);

        System.out.println(
            indent + node.type() +
            (node.relation().isEmpty() ? "" : " [" + node.relation() + "]")
        );

        System.out.println(
            indent + "  Estimated rows: " + node.estimatedRows()
        );

        System.out.println(
            indent + "  Actual rows per loop: " +
            node.actualRowsPerLoop()
        );

        System.out.println(
            indent + "  Loops: " + node.loops()
        );

        System.out.println(
            indent + "  Total actual rows: " + node.totalActualRows()
        );

        System.out.println(
            indent + "  Actual time per loop: " +
            node.totalTimeMs() + " ms"
        );

        System.out.println(
            indent + "  Accumulated node time: " +
            node.accumulatedNodeTimeMs() + " ms"
        );

        for (ExecutionNode child : node.children()) {
            printNode(child, depth + 1);
        }
    }

    static void runTests(PerformanceAnalyzer analyzer) {
        ExecutionNode node = new ExecutionNode(
            NodeType.INDEX_SCAN,
            "customers",
            10,
            10,
            1,
            0,
            1,
            0,
            0.5,
            new BufferStats(2, 0, 0),
            List.of()
        );

        QueryExecution valid = new QueryExecution(
            0.1,
            1.0,
            node
        );

        if (
            analyzer.verify(valid).status() !=
            VerificationStatus.PASSED
        ) {
            throw new AssertionError("Valid plan test failed");
        }

        BenchmarkService benchmark = new BenchmarkService();
        benchmark.record(2);
        benchmark.record(4);

        if (benchmark.summarize().get("median_ms") != 3.0) {
            throw new AssertionError("Benchmark test failed");
        }

        try {
            new ExecutionNode(
                NodeType.INDEX_SCAN,
                "orders",
                -1,
                1,
                1,
                0,
                1,
                0,
                1,
                new BufferStats(0, 0, 0),
                List.of()
            );
            throw new AssertionError("Invalid node was accepted");
        } catch (PlanException expected) {
            // Expected validation failure.
        }

        System.out.println("All Java tests passed.");
    }

    public static void main(String[] args) {
        try {
            PerformancePolicy policy = new PerformancePolicy(
                100,
                50,
                20,
                50,
                100
            );

            PerformanceAnalyzer analyzer =
                new PerformanceAnalyzer(policy);

            QueryExecution execution = new QueryExecution(
                0.75,
                6.50,
                samplePlan()
            );

            System.out.println("POSTGRESQL EXECUTION PLAN");
            System.out.println("=========================");

            printNode(execution.root(), 0);

            System.out.println("\nQUERY TIMING");
            System.out.println(
                "Planning Time: " + execution.planningTimeMs() + " ms"
            );
            System.out.println(
                "Execution Time: " + execution.executionTimeMs() + " ms"
            );

            System.out.println("\nPERFORMANCE FINDINGS");

            for (Finding finding : analyzer.analyze(execution)) {
                System.out.printf(
                    "[%s] %s: %s%n",
                    finding.severity(),
                    finding.component(),
                    finding.message()
                );
            }

            VerificationResult result = analyzer.verify(execution);

            System.out.println(
                "\nPLAN VERIFICATION: " + result.status()
            );

            BenchmarkService benchmark = new BenchmarkService();

            for (double value : new double[]{
                6.5, 6.2, 6.8, 6.4, 6.3
            }) {
                benchmark.record(value);
            }

            System.out.println("\nBENCHMARK STATISTICS");

            benchmark.summarize().forEach(
                (key, value) -> System.out.println(key + ": " + value)
            );

            runTests(analyzer);

        } catch (PlanException | IllegalArgumentException error) {
            System.err.println("Execution failed: " + error.getMessage());
            System.exit(1);
        }
    }
}
