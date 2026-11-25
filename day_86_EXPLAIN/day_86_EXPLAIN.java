import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.stream.Collectors;

/*
 * SQL EXPLAIN: Execution Plans, Cost Estimates, and Scan Types
 *
 * Enterprise execution-plan analysis and cost estimation.
 *
 * Features:
 * - Immutable plan-node domain model
 * - Scan and join classifications
 * - Estimated and actual cardinalities
 * - Cost validation
 * - Recursive plan inspection
 * - Buffer analysis
 * - Cardinality estimation diagnostics
 * - Policy-based performance thresholds
 * - Enterprise reporting
 *
 * Java 17, no third-party dependencies.
 *
 * Compile:
 * javac ExplainEnterprise.java
 *
 * Run:
 * java ExplainEnterprise
 */

public class ExplainEnterprise {

    enum ScanType {
        SEQUENTIAL,
        INDEX,
        INDEX_ONLY,
        BITMAP_HEAP,
        BITMAP_INDEX,
        NONE
    }

    enum JoinType {
        NESTED_LOOP,
        HASH_JOIN,
        MERGE_JOIN,
        NONE
    }

    enum Severity {
        INFO,
        WARNING,
        CRITICAL
    }

    record Cost(
        double startup,
        double total
    ) {
        Cost {
            if (
                !Double.isFinite(startup) ||
                !Double.isFinite(total) ||
                startup < 0 ||
                total < startup
            ) {
                throw new IllegalArgumentException(
                    "Invalid execution cost."
                );
            }
        }
    }

    record Cardinality(
        long estimatedRows,
        long actualRows
    ) {
        Cardinality {
            if (estimatedRows < 0 || actualRows < 0) {
                throw new IllegalArgumentException(
                    "Cardinality cannot be negative."
                );
            }
        }

        double errorFactor() {
            return Math.max(
                Math.max(estimatedRows, actualRows),
                1
            ) / (double) Math.max(
                Math.min(estimatedRows, actualRows),
                1
            );
        }

        long difference() {
            return actualRows - estimatedRows;
        }

        boolean inaccurate(double threshold) {
            return errorFactor() >= threshold;
        }
    }

    record BufferUsage(
        long sharedHits,
        long sharedReads,
        long temporaryReads,
        long temporaryWrites
    ) {
        BufferUsage {
            if (
                sharedHits < 0 ||
                sharedReads < 0 ||
                temporaryReads < 0 ||
                temporaryWrites < 0
            ) {
                throw new IllegalArgumentException(
                    "Buffer counts cannot be negative."
                );
            }
        }

        long totalSharedBlocks() {
            return sharedHits + sharedReads;
        }
    }

    record PlanNode(
        String nodeType,
        String relation,
        String indexName,
        Cost cost,
        Cardinality cardinality,
        BufferUsage buffers,
        double actualTimeMs,
        int loops,
        List<PlanNode> children
    ) {
        PlanNode {
            Objects.requireNonNull(nodeType);
            Objects.requireNonNull(cost);
            Objects.requireNonNull(cardinality);
            Objects.requireNonNull(buffers);

            if (
                nodeType.isBlank() ||
                actualTimeMs < 0 ||
                !Double.isFinite(actualTimeMs) ||
                loops < 0
            ) {
                throw new IllegalArgumentException(
                    "Invalid execution-plan node."
                );
            }

            children = List.copyOf(
                Objects.requireNonNull(children)
            );
        }

        ScanType scanType() {
            return switch (nodeType) {
                case "Seq Scan" ->
                    ScanType.SEQUENTIAL;

                case "Index Scan" ->
                    ScanType.INDEX;

                case "Index Only Scan" ->
                    ScanType.INDEX_ONLY;

                case "Bitmap Heap Scan" ->
                    ScanType.BITMAP_HEAP;

                case "Bitmap Index Scan" ->
                    ScanType.BITMAP_INDEX;

                default ->
                    ScanType.NONE;
            };
        }

        JoinType joinType() {
            return switch (nodeType) {
                case "Nested Loop" ->
                    JoinType.NESTED_LOOP;

                case "Hash Join" ->
                    JoinType.HASH_JOIN;

                case "Merge Join" ->
                    JoinType.MERGE_JOIN;

                default ->
                    JoinType.NONE;
            };
        }
    }

    record Diagnostic(
        Severity severity,
        String component,
        String message
    ) {}

    record PlanReport(
        String rootNode,
        double totalEstimatedCost,
        long estimatedRows,
        long actualRows,
        double executionTimeMs,
        int nodeCount,
        Map<ScanType, Long> scanCounts,
        Map<JoinType, Long> joinCounts,
        long sharedHits,
        long sharedReads,
        long temporaryWrites,
        List<Diagnostic> diagnostics
    ) {
        PlanReport {
            scanCounts = Map.copyOf(scanCounts);
            joinCounts = Map.copyOf(joinCounts);
            diagnostics = List.copyOf(diagnostics);
        }
    }

    interface PlanPolicy {
        List<Diagnostic> evaluate(PlanNode node);
    }

    static final class EnterprisePlanPolicy
            implements PlanPolicy {

        private final double maximumEstimationError;
        private final long sequentialScanWarningRows;
        private final int nestedLoopWarningCount;

        EnterprisePlanPolicy(
            double maximumEstimationError,
            long sequentialScanWarningRows,
            int nestedLoopWarningCount
        ) {
            if (
                maximumEstimationError < 1 ||
                sequentialScanWarningRows < 0 ||
                nestedLoopWarningCount < 1
            ) {
                throw new IllegalArgumentException(
                    "Invalid performance policy."
                );
            }

            this.maximumEstimationError =
                maximumEstimationError;

            this.sequentialScanWarningRows =
                sequentialScanWarningRows;

            this.nestedLoopWarningCount =
                nestedLoopWarningCount;
        }

        @Override
        public List<Diagnostic> evaluate(PlanNode node) {
            List<Diagnostic> results = new ArrayList<>();

            if (
                node.cardinality().inaccurate(
                    maximumEstimationError
                )
            ) {
                results.add(
                    new Diagnostic(
                        Severity.WARNING,
                        node.nodeType(),
                        "Estimated and actual cardinalities differ significantly."
                    )
                );
            }

            if (
                node.scanType() == ScanType.SEQUENTIAL &&
                node.cardinality().estimatedRows() >
                    sequentialScanWarningRows
            ) {
                results.add(
                    new Diagnostic(
                        Severity.INFO,
                        node.nodeType(),
                        "Large sequential scan detected. Assess filtering requirements and index usefulness."
                    )
                );
            }

            if (
                node.joinType() == JoinType.NESTED_LOOP &&
                node.loops() > nestedLoopWarningCount
            ) {
                results.add(
                    new Diagnostic(
                        Severity.WARNING,
                        node.nodeType(),
                        "Nested-loop execution has a high iteration count."
                    )
                );
            }

            if (node.buffers().temporaryWrites() > 0) {
                results.add(
                    new Diagnostic(
                        Severity.WARNING,
                        node.nodeType(),
                        "Temporary disk writes detected."
                    )
                );
            }

            if (
                node.scanType() == ScanType.INDEX &&
                node.indexName() == null
            ) {
                results.add(
                    new Diagnostic(
                        Severity.CRITICAL,
                        node.nodeType(),
                        "Index scan is missing index metadata."
                    )
                );
            }

            return results;
        }
    }

    static final class PlanAnalyzer {

        private final PlanPolicy policy;

        PlanAnalyzer(PlanPolicy policy) {
            this.policy = Objects.requireNonNull(policy);
        }

        PlanReport analyze(
            PlanNode root,
            double executionTimeMs
        ) {
            Objects.requireNonNull(root);

            if (
                executionTimeMs < 0 ||
                !Double.isFinite(executionTimeMs)
            ) {
                throw new IllegalArgumentException(
                    "Invalid execution time."
                );
            }

            EnumMap<ScanType, Long> scans =
                new EnumMap<>(ScanType.class);

            EnumMap<JoinType, Long> joins =
                new EnumMap<>(JoinType.class);

            List<Diagnostic> diagnostics =
                new ArrayList<>();

            long[] totals = new long[4];

            int nodeCount = traverse(
                root,
                scans,
                joins,
                diagnostics,
                totals
            );

            return new PlanReport(
                root.nodeType(),
                root.cost().total(),
                root.cardinality().estimatedRows(),
                root.cardinality().actualRows(),
                executionTimeMs,
                nodeCount,
                scans,
                joins,
                totals[0],
                totals[1],
                totals[2],
                diagnostics
            );
        }

        private int traverse(
            PlanNode node,
            Map<ScanType, Long> scans,
            Map<JoinType, Long> joins,
            List<Diagnostic> diagnostics,
            long[] totals
        ) {
            if (node.scanType() != ScanType.NONE) {
                scans.merge(
                    node.scanType(),
                    1L,
                    Long::sum
                );
            }

            if (node.joinType() != JoinType.NONE) {
                joins.merge(
                    node.joinType(),
                    1L,
                    Long::sum
                );
            }

            totals[0] += node.buffers().sharedHits();
            totals[1] += node.buffers().sharedReads();
            totals[2] += node.buffers().temporaryWrites();

            diagnostics.addAll(policy.evaluate(node));

            int count = 1;

            for (PlanNode child : node.children()) {
                count += traverse(
                    child,
                    scans,
                    joins,
                    diagnostics,
                    totals
                );
            }

            return count;
        }
    }

    static final class CostEstimator {

        private final double sequentialPageCost;
        private final double randomPageCost;
        private final double cpuTupleCost;
        private final double indexTupleCost;

        CostEstimator(
            double sequentialPageCost,
            double randomPageCost,
            double cpuTupleCost,
            double indexTupleCost
        ) {
            if (
                sequentialPageCost <= 0 ||
                randomPageCost <= 0 ||
                cpuTupleCost < 0 ||
                indexTupleCost < 0
            ) {
                throw new IllegalArgumentException(
                    "Invalid cost configuration."
                );
            }

            this.sequentialPageCost = sequentialPageCost;
            this.randomPageCost = randomPageCost;
            this.cpuTupleCost = cpuTupleCost;
            this.indexTupleCost = indexTupleCost;
        }

        Cost estimate(
            long rows,
            long pages,
            double selectivity,
            ScanType type
        ) {
            if (
                rows < 0 ||
                pages < 0 ||
                selectivity < 0 ||
                selectivity > 1
            ) {
                throw new IllegalArgumentException(
                    "Invalid relation statistics."
                );
            }

            double selectedRows = rows * selectivity;

            double total = switch (type) {
                case SEQUENTIAL ->
                    pages * sequentialPageCost +
                    rows * cpuTupleCost;

                case INDEX ->
                    Math.log(
                        Math.max(rows, 2)
                    ) / Math.log(2) +
                    selectedRows * (
                        indexTupleCost + randomPageCost
                    );

                case INDEX_ONLY ->
                    0.35 * (
                        Math.log(Math.max(rows, 2)) /
                        Math.log(2) +
                        selectedRows * (
                            indexTupleCost + randomPageCost
                        )
                    );

                case BITMAP_HEAP ->
                    pages * selectivity +
                    selectedRows * randomPageCost * 0.4;

                default ->
                    throw new IllegalArgumentException(
                        "Unsupported scan type."
                    );
            };

            double startup =
                type == ScanType.SEQUENTIAL ? 0 : 1;

            return new Cost(startup, Math.max(startup, total));
        }

        Optional<ScanType> choose(
            long rows,
            long pages,
            double selectivity
        ) {
            return List.of(
                ScanType.SEQUENTIAL,
                ScanType.INDEX,
                ScanType.INDEX_ONLY,
                ScanType.BITMAP_HEAP
            ).stream()
                .min(
                    java.util.Comparator.comparingDouble(
                        type -> estimate(
                            rows,
                            pages,
                            selectivity,
                            type
                        ).total()
                    )
                );
        }
    }

    static PlanNode samplePlan() {
        PlanNode departmentScan = new PlanNode(
            "Seq Scan",
            "departments",
            null,
            new Cost(0, 20),
            new Cardinality(4, 4),
            new BufferUsage(10, 0, 0, 0),
            0.04,
            1,
            List.of()
        );

        PlanNode indexScan = new PlanNode(
            "Bitmap Index Scan",
            "employees",
            "idx_employees_department",
            new Cost(0, 8),
            new Cardinality(250, 250),
            new BufferUsage(20, 2, 0, 0),
            0.20,
            1,
            List.of()
        );

        PlanNode bitmapHeapScan = new PlanNode(
            "Bitmap Heap Scan",
            "employees",
            null,
            new Cost(10, 100),
            new Cardinality(250, 250),
            new BufferUsage(80, 5, 0, 0),
            1.50,
            1,
            List.of(indexScan)
        );

        return new PlanNode(
            "Hash Join",
            null,
            null,
            new Cost(25.5, 180.75),
            new Cardinality(250, 250),
            new BufferUsage(120, 15, 0, 0),
            2.85,
            1,
            List.of(
                departmentScan,
                bitmapHeapScan
            )
        );
    }

    static void printReport(PlanReport report) {
        System.out.println("\nENTERPRISE EXECUTION REPORT");
        System.out.println("===========================");

        System.out.println(
            "Root node: " + report.rootNode()
        );

        System.out.println(
            "Estimated cost: " +
            report.totalEstimatedCost()
        );

        System.out.println(
            "Estimated rows: " + report.estimatedRows()
        );

        System.out.println(
            "Actual rows: " + report.actualRows()
        );

        System.out.println(
            "Execution time: " +
            report.executionTimeMs() + " ms"
        );

        System.out.println(
            "Plan nodes: " + report.nodeCount()
        );

        System.out.println("\nScan counts:");

        report.scanCounts().forEach(
            (type, count) ->
                System.out.println(type + ": " + count)
        );

        System.out.println("\nJoin counts:");

        report.joinCounts().forEach(
            (type, count) ->
                System.out.println(type + ": " + count)
        );

        System.out.println("\nBuffer usage:");

        System.out.println(
            "Shared hits: " + report.sharedHits()
        );

        System.out.println(
            "Shared reads: " + report.sharedReads()
        );

        System.out.println(
            "Temporary writes: " +
            report.temporaryWrites()
        );

        System.out.println("\nDiagnostics:");

        report.diagnostics().forEach(
            diagnostic -> System.out.println(
                diagnostic.severity() +
                " | " +
                diagnostic.component() +
                " | " +
                diagnostic.message()
            )
        );
    }

    public static void main(String[] args) {
        PlanPolicy policy = new EnterprisePlanPolicy(
            2.0,
            10000,
            1000
        );

        PlanAnalyzer analyzer = new PlanAnalyzer(policy);

        PlanReport report = analyzer.analyze(
            samplePlan(),
            3.10
        );

        printReport(report);

        CostEstimator estimator = new CostEstimator(
            1.0,
            4.0,
            0.01,
            0.02
        );

        System.out.println("\nCOST-BASED SCAN SELECTION");
        System.out.println("=========================");

        for (double selectivity : List.of(
            0.001,
            0.01,
            0.05,
            0.25,
            0.75,
            1.0
        )) {
            ScanType selected = estimator.choose(
                100000,
                2500,
                selectivity
            ).orElseThrow();

            System.out.println(
                "Selectivity: " +
                selectivity * 100 +
                "% | Selected: " + selected
            );
        }

        System.out.println(
            "\nEnterprise plan validation completed."
        );
    }
}
