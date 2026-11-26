#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

/*
 * EXPLAIN ANALYZE: PostgreSQL query performance verification engine.
 *
 * C++17 implementation:
 * - Execution-plan domain model
 * - Actual rows and execution loops
 * - Cardinality estimation comparison
 * - Buffer access accounting
 * - Recursive plan traversal
 * - Performance policy evaluation
 * - Benchmark aggregation
 * - Failure reporting
 *
 * Build:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic explain_analyze.cpp -o explain_analyze
 */

enum class NodeType {
    SequentialScan,
    IndexScan,
    IndexOnlyScan,
    NestedLoop,
    HashJoin,
    MergeJoin,
    Sort,
    Aggregate
};

std::string toString(NodeType type) {
    switch (type) {
        case NodeType::SequentialScan: return "Seq Scan";
        case NodeType::IndexScan: return "Index Scan";
        case NodeType::IndexOnlyScan: return "Index Only Scan";
        case NodeType::NestedLoop: return "Nested Loop";
        case NodeType::HashJoin: return "Hash Join";
        case NodeType::MergeJoin: return "Merge Join";
        case NodeType::Sort: return "Sort";
        case NodeType::Aggregate: return "Aggregate";
    }
    throw std::logic_error("Unknown node type");
}

struct BufferStats {
    std::uint64_t sharedHits = 0;
    std::uint64_t sharedReads = 0;
    std::uint64_t sharedDirtied = 0;

    std::uint64_t totalAccesses() const {
        return sharedHits + sharedReads;
    }
};

struct ExecutionNode {
    NodeType type;
    std::string relation;

    double estimatedRows;
    double actualRowsPerLoop;

    int loops;

    double startupCost;
    double totalCost;

    double startupTimeMs;
    double totalTimeMs;

    BufferStats buffers;

    std::vector<ExecutionNode> children;

    double totalActualRows() const {
        return actualRowsPerLoop * loops;
    }

    double accumulatedTimeMs() const {
        return totalTimeMs * loops;
    }

    double estimationRatio() const {
        if (estimatedRows == 0.0) {
            return actualRowsPerLoop == 0.0
                ? 1.0
                : std::numeric_limits<double>::infinity();
        }

        if (actualRowsPerLoop == 0.0) {
            return std::numeric_limits<double>::infinity();
        }

        return std::max(
            estimatedRows / actualRowsPerLoop,
            actualRowsPerLoop / estimatedRows
        );
    }

    void validate() const {
        const double values[] = {
            estimatedRows,
            actualRowsPerLoop,
            startupCost,
            totalCost,
            startupTimeMs,
            totalTimeMs
        };

        for (double value : values) {
            if (!std::isfinite(value) || value < 0.0) {
                throw std::invalid_argument(
                    "Execution metrics must be finite and non-negative"
                );
            }
        }

        if (loops < 0) {
            throw std::invalid_argument("Loops cannot be negative");
        }

        for (const auto& child : children) {
            child.validate();
        }
    }
};

struct QueryExecution {
    double planningTimeMs;
    double executionTimeMs;
    ExecutionNode root;

    void validate() const {
        if (
            !std::isfinite(planningTimeMs) ||
            !std::isfinite(executionTimeMs) ||
            planningTimeMs < 0.0 ||
            executionTimeMs < 0.0
        ) {
            throw std::invalid_argument("Invalid query timing");
        }

        root.validate();
    }
};

struct VerificationPolicy {
    double maximumExecutionTimeMs = 100.0;
    double maximumPlanningTimeMs = 50.0;
    double maximumEstimationRatio = 20.0;
    double maximumNodeTimeMs = 50.0;
    std::uint64_t maximumSharedReads = 100;

    void validate() const {
        if (
            maximumExecutionTimeMs < 0 ||
            maximumPlanningTimeMs < 0 ||
            maximumEstimationRatio < 1 ||
            maximumNodeTimeMs < 0
        ) {
            throw std::invalid_argument("Invalid verification policy");
        }
    }
};

struct Finding {
    std::string severity;
    std::string message;
};

class PlanAnalyzer {
private:
    VerificationPolicy policy;

    void inspectNode(
        const ExecutionNode& node,
        std::vector<Finding>& findings
    ) const {
        if (node.loops == 0) {
            findings.push_back({
                "INFO",
                toString(node.type) + " was never executed"
            });
        }

        if (
            node.estimationRatio() >
            policy.maximumEstimationRatio
        ) {
            findings.push_back({
                "WARNING",
                toString(node.type) +
                " has a significant cardinality estimation error"
            });
        }

        if (
            node.accumulatedTimeMs() >
            policy.maximumNodeTimeMs
        ) {
            findings.push_back({
                "WARNING",
                toString(node.type) +
                " has high accumulated node time"
            });
        }

        if (
            node.type == NodeType::SequentialScan &&
            node.totalTimeMs > 20.0
        ) {
            findings.push_back({
                "WARNING",
                "Expensive sequential scan on " + node.relation
            });
        }

        if (
            node.buffers.sharedReads >
            policy.maximumSharedReads
        ) {
            findings.push_back({
                "WARNING",
                "High shared-buffer read count in " +
                toString(node.type)
            });
        }

        for (const auto& child : node.children) {
            inspectNode(child, findings);
        }
    }

public:
    explicit PlanAnalyzer(VerificationPolicy p)
        : policy(std::move(p)) {
        policy.validate();
    }

    std::vector<Finding> analyze(
        const QueryExecution& execution
    ) const {
        execution.validate();

        std::vector<Finding> findings;

        if (
            execution.executionTimeMs >
            policy.maximumExecutionTimeMs
        ) {
            findings.push_back({
                "CRITICAL",
                "Query execution time exceeds policy"
            });
        }

        if (
            execution.planningTimeMs >
            policy.maximumPlanningTimeMs
        ) {
            findings.push_back({
                "WARNING",
                "Query planning time exceeds policy"
            });
        }

        inspectNode(execution.root, findings);

        if (findings.empty()) {
            findings.push_back({
                "INFO",
                "No configured performance issue detected"
            });
        }

        return findings;
    }

    bool verify(const QueryExecution& execution) const {
        execution.validate();

        if (
            execution.executionTimeMs >
            policy.maximumExecutionTimeMs
        ) {
            return false;
        }

        std::vector<const ExecutionNode*> stack = {
            &execution.root
        };

        while (!stack.empty()) {
            const ExecutionNode* node = stack.back();
            stack.pop_back();

            if (
                node->estimationRatio() >
                policy.maximumEstimationRatio
            ) {
                return false;
            }

            for (const auto& child : node->children) {
                stack.push_back(&child);
            }
        }

        return true;
    }
};

class Benchmark {
private:
    std::vector<double> samples;

public:
    void add(double milliseconds) {
        if (
            !std::isfinite(milliseconds) ||
            milliseconds < 0
        ) {
            throw std::invalid_argument(
                "Invalid benchmark measurement"
            );
        }

        samples.push_back(milliseconds);
    }

    std::map<std::string, double> statistics() const {
        if (samples.empty()) {
            throw std::runtime_error(
                "No benchmark samples available"
            );
        }

        std::vector<double> sorted = samples;
        std::sort(sorted.begin(), sorted.end());

        const double total = std::accumulate(
            sorted.begin(),
            sorted.end(),
            0.0
        );

        const std::size_t n = sorted.size();

        double median;

        if (n % 2 == 0) {
            median = (
                sorted[n / 2 - 1] + sorted[n / 2]
            ) / 2.0;
        } else {
            median = sorted[n / 2];
        }

        return {
            {"minimum_ms", sorted.front()},
            {"maximum_ms", sorted.back()},
            {"average_ms", total / n},
            {"median_ms", median},
            {"runs", static_cast<double>(n)}
        };
    }
};

void printNode(
    const ExecutionNode& node,
    int depth = 0
) {
    const std::string indent(depth * 2, ' ');

    std::cout
        << indent << toString(node.type);

    if (!node.relation.empty()) {
        std::cout << " [" << node.relation << "]";
    }

    std::cout
        << "\n" << indent
        << "  Estimated rows: "
        << node.estimatedRows
        << "\n" << indent
        << "  Actual rows per loop: "
        << node.actualRowsPerLoop
        << "\n" << indent
        << "  Loops: " << node.loops
        << "\n" << indent
        << "  Total actual rows: "
        << node.totalActualRows()
        << "\n" << indent
        << "  Actual total time per loop: "
        << node.totalTimeMs << " ms"
        << "\n" << indent
        << "  Accumulated node time: "
        << node.accumulatedTimeMs() << " ms"
        << "\n" << indent
        << "  Shared buffer hits: "
        << node.buffers.sharedHits
        << "\n" << indent
        << "  Shared buffer reads: "
        << node.buffers.sharedReads
        << "\n";

    for (const auto& child : node.children) {
        printNode(child, depth + 1);
    }
}

ExecutionNode createDemonstrationPlan() {
    ExecutionNode customerScan{
        NodeType::IndexScan,
        "customers",
        100,
        100,
        1,
        0.25,
        10.0,
        0.02,
        0.40,
        {15, 0, 0},
        {}
    };

    ExecutionNode orderScan{
        NodeType::IndexScan,
        "orders",
        1,
        2,
        100,
        0.20,
        2.0,
        0.01,
        0.025,
        {200, 3, 0},
        {}
    };

    return ExecutionNode{
        NodeType::NestedLoop,
        "",
        100,
        200,
        1,
        0.50,
        250.0,
        0.10,
        5.20,
        {215, 3, 0},
        {customerScan, orderScan}
    };
}

void runTests(const PlanAnalyzer& analyzer) {
    QueryExecution good{
        0.5,
        5.0,
        ExecutionNode{
            NodeType::IndexScan,
            "customers",
            10,
            10,
            1,
            0.1,
            2.0,
            0.01,
            0.5,
            {},
            {}
        }
    };

    if (!analyzer.verify(good)) {
        throw std::runtime_error("Valid plan test failed");
    }

    Benchmark benchmark;
    benchmark.add(2.0);
    benchmark.add(4.0);

    if (benchmark.statistics().at("median_ms") != 3.0) {
        throw std::runtime_error("Benchmark test failed");
    }

    bool rejected = false;

    try {
        ExecutionNode invalid{
            NodeType::IndexScan,
            "orders",
            -1,
            10,
            1,
            0,
            1,
            0,
            1,
            {},
            {}
        };
        invalid.validate();
    } catch (const std::invalid_argument&) {
        rejected = true;
    }

    if (!rejected) {
        throw std::runtime_error("Invalid plan was accepted");
    }

    std::cout << "\nAll C++ tests passed.\n";
}

int main() {
    try {
        VerificationPolicy policy{
            100.0,
            50.0,
            20.0,
            50.0,
            100
        };

        PlanAnalyzer analyzer(policy);

        QueryExecution execution{
            0.75,
            6.50,
            createDemonstrationPlan()
        };

        std::cout << std::fixed << std::setprecision(3);

        std::cout << "POSTGRESQL EXECUTION PLAN\n";
        std::cout << "=========================\n";

        printNode(execution.root);

        std::cout << "\nQUERY TIMING\n";
        std::cout << "Planning Time: "
                  << execution.planningTimeMs << " ms\n";
        std::cout << "Execution Time: "
                  << execution.executionTimeMs << " ms\n";

        std::cout << "\nPERFORMANCE FINDINGS\n";

        for (const auto& finding : analyzer.analyze(execution)) {
            std::cout
                << "[" << finding.severity << "] "
                << finding.message << "\n";
        }

        std::cout << "\nPLAN VERIFICATION: "
                  << (analyzer.verify(execution) ? "PASS" : "FAIL")
                  << "\n";

        Benchmark benchmark;

        for (double sample : {
            6.5, 6.2, 6.8, 6.4, 6.3
        }) {
            benchmark.add(sample);
        }

        std::cout << "\nBENCHMARK STATISTICS\n";

        for (const auto& [key, value] : benchmark.statistics()) {
            std::cout << key << ": " << value << "\n";
        }

        runTests(analyzer);

        return 0;

    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << "\n";
        return 1;
    }
}
