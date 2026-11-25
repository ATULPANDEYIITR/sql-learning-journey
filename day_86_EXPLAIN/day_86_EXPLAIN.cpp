#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

/*
 * SQL EXPLAIN: Execution Plans, Cost Estimates, and Scan Types
 *
 * A simplified cost-based query planner.
 *
 * Models:
 * - Relation statistics
 * - Cardinality and selectivity
 * - Sequential scans
 * - Index scans
 * - Index-only scans
 * - Bitmap scans
 * - Nested loop joins
 * - Hash joins
 * - Merge joins
 * - Cost-based plan selection
 * - Execution-plan diagnostics
 *
 * Compile:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic explain_engine.cpp -o explain_engine
 */

enum class ScanType {
    Sequential,
    Index,
    IndexOnly,
    Bitmap
};

enum class JoinType {
    NestedLoop,
    HashJoin,
    MergeJoin
};

struct TableStatistics {
    std::string name;
    double rows;
    double pages;
    double averageRowWidth;
    double distinctValues;
};

struct CostParameters {
    double sequentialPageCost = 1.0;
    double randomPageCost = 4.0;
    double cpuTupleCost = 0.01;
    double indexTupleCost = 0.02;
    double hashBuildCost = 0.03;
    double sortCostFactor = 0.015;
};

struct ExecutionEstimate {
    ScanType type;
    double startupCost;
    double totalCost;
    double estimatedRows;
    double selectivity;
};

struct JoinEstimate {
    JoinType type;
    double startupCost;
    double totalCost;
    double estimatedRows;
};

class QueryPlanner {
private:
    CostParameters parameters;

    static void validateStatistics(
        const TableStatistics& table
    ) {
        if (
            table.name.empty() ||
            table.rows < 0 ||
            table.pages < 0 ||
            table.averageRowWidth <= 0 ||
            table.distinctValues < 0
        ) {
            throw std::invalid_argument(
                "Invalid table statistics."
            );
        }
    }

public:
    explicit QueryPlanner(
        CostParameters configuration = {}
    ) : parameters(configuration) {
        if (
            parameters.sequentialPageCost <= 0 ||
            parameters.randomPageCost <= 0 ||
            parameters.cpuTupleCost < 0 ||
            parameters.indexTupleCost < 0
        ) {
            throw std::invalid_argument(
                "Invalid planner cost parameters."
            );
        }
    }

    ExecutionEstimate estimateScan(
        const TableStatistics& table,
        double selectivity,
        ScanType type
    ) const {
        validateStatistics(table);

        if (
            !std::isfinite(selectivity) ||
            selectivity < 0 ||
            selectivity > 1
        ) {
            throw std::invalid_argument(
                "Selectivity must be between 0 and 1."
            );
        }

        const double estimatedRows =
            table.rows * selectivity;

        double startup = 0;
        double total = 0;

        switch (type) {
            case ScanType::Sequential:
                total =
                    table.pages *
                    parameters.sequentialPageCost +
                    table.rows *
                    parameters.cpuTupleCost;
                break;

            case ScanType::Index:
                startup = 1.0;
                total =
                    std::log2(std::max(table.rows, 2.0)) +
                    estimatedRows *
                    parameters.indexTupleCost +
                    estimatedRows *
                    parameters.randomPageCost;
                break;

            case ScanType::IndexOnly:
                startup = 1.0;
                total = (
                    std::log2(std::max(table.rows, 2.0)) +
                    estimatedRows *
                    parameters.indexTupleCost +
                    estimatedRows *
                    parameters.randomPageCost
                ) * 0.35;
                break;

            case ScanType::Bitmap:
                startup = 2.0;
                total =
                    table.pages * selectivity +
                    estimatedRows *
                    parameters.randomPageCost * 0.4;
                break;
        }

        return {
            type,
            startup,
            total,
            estimatedRows,
            selectivity
        };
    }

    ExecutionEstimate chooseScan(
        const TableStatistics& table,
        double selectivity
    ) const {
        const std::vector<ScanType> candidates = {
            ScanType::Sequential,
            ScanType::Index,
            ScanType::IndexOnly,
            ScanType::Bitmap
        };

        std::vector<ExecutionEstimate> estimates;

        for (ScanType type : candidates) {
            estimates.push_back(
                estimateScan(table, selectivity, type)
            );
        }

        return *std::min_element(
            estimates.begin(),
            estimates.end(),
            [](const auto& left, const auto& right) {
                return left.totalCost < right.totalCost;
            }
        );
    }

    JoinEstimate estimateJoin(
        JoinType type,
        const TableStatistics& outer,
        const TableStatistics& inner,
        double joinSelectivity
    ) const {
        validateStatistics(outer);
        validateStatistics(inner);

        if (
            joinSelectivity < 0 ||
            joinSelectivity > 1 ||
            !std::isfinite(joinSelectivity)
        ) {
            throw std::invalid_argument(
                "Invalid join selectivity."
            );
        }

        const double outputRows =
            outer.rows * inner.rows * joinSelectivity;

        double startup = 0;
        double total = 0;

        switch (type) {
            case JoinType::NestedLoop:
                total =
                    outer.rows *
                    (
                        std::log2(std::max(inner.rows, 2.0)) +
                        inner.rows * parameters.cpuTupleCost
                    );
                break;

            case JoinType::HashJoin:
                startup =
                    inner.rows * parameters.hashBuildCost;

                total =
                    startup +
                    (outer.rows + inner.rows) *
                    parameters.cpuTupleCost;
                break;

            case JoinType::MergeJoin: {
                const double outerSort =
                    outer.rows *
                    std::log2(std::max(outer.rows, 2.0)) *
                    parameters.sortCostFactor;

                const double innerSort =
                    inner.rows *
                    std::log2(std::max(inner.rows, 2.0)) *
                    parameters.sortCostFactor;

                startup = outerSort + innerSort;

                total =
                    startup +
                    (outer.rows + inner.rows) *
                    parameters.cpuTupleCost;
                break;
            }
        }

        return {
            type,
            startup,
            total,
            outputRows
        };
    }
};

class PlanDiagnostics {

public:
    static std::string scanName(ScanType type) {
        switch (type) {
            case ScanType::Sequential:
                return "Sequential Scan";

            case ScanType::Index:
                return "Index Scan";

            case ScanType::IndexOnly:
                return "Index Only Scan";

            case ScanType::Bitmap:
                return "Bitmap Scan";
        }

        return "Unknown";
    }

    static std::string joinName(JoinType type) {
        switch (type) {
            case JoinType::NestedLoop:
                return "Nested Loop";

            case JoinType::HashJoin:
                return "Hash Join";

            case JoinType::MergeJoin:
                return "Merge Join";
        }

        return "Unknown";
    }

    static void printScan(
        const TableStatistics& table,
        const ExecutionEstimate& estimate
    ) {
        std::cout
            << "\nRelation: " << table.name
            << "\nScan: " << scanName(estimate.type)
            << "\nEstimated rows: "
            << estimate.estimatedRows
            << "\nSelectivity: "
            << estimate.selectivity * 100 << "%"
            << "\nStartup Cost: "
            << estimate.startupCost
            << "\nTotal Cost: "
            << estimate.totalCost
            << '\n';

        if (
            estimate.type == ScanType::Sequential &&
            estimate.selectivity < 0.10
        ) {
            std::cout
                << "Diagnostic: Selective predicate with "
                << "sequential access. Inspect index availability, "
                << "statistics and actual costs.\n";
        }

        if (
            estimate.type == ScanType::Index &&
            estimate.selectivity > 0.50
        ) {
            std::cout
                << "Diagnostic: High index selectivity ratio. "
                << "A sequential scan may be competitive.\n";
        }
    }

    static void printJoin(
        const JoinEstimate& estimate
    ) {
        std::cout
            << "\nJoin: " << joinName(estimate.type)
            << "\nEstimated rows: "
            << estimate.estimatedRows
            << "\nStartup Cost: "
            << estimate.startupCost
            << "\nTotal Cost: "
            << estimate.totalCost
            << '\n';
    }
};

int main() {
    try {
        std::cout << std::fixed << std::setprecision(2);

        const CostParameters parameters;
        const QueryPlanner planner(parameters);

        const TableStatistics employees = {
            "employees",
            100000,
            2500,
            100,
            10000
        };

        const TableStatistics departments = {
            "departments",
            20,
            2,
            64,
            20
        };

        std::cout
            << "SQL EXECUTION PLAN COST ENGINE\n"
            << "================================\n";

        const std::vector<double> selectivities = {
            0.001,
            0.01,
            0.05,
            0.25,
            0.75,
            1.0
        };

        for (double selectivity : selectivities) {
            const auto selected =
                planner.chooseScan(employees, selectivity);

            std::cout
                << "\nSelectivity: "
                << selectivity * 100 << "%"
                << "\nSelected: "
                << PlanDiagnostics::scanName(selected.type)
                << "\nCost: "
                << selected.totalCost
                << '\n';
        }

        std::cout
            << "\n--- Detailed scan comparison ---\n";

        for (ScanType type : {
            ScanType::Sequential,
            ScanType::Index,
            ScanType::IndexOnly,
            ScanType::Bitmap
        }) {
            const auto estimate =
                planner.estimateScan(
                    employees,
                    0.02,
                    type
                );

            PlanDiagnostics::printScan(
                employees,
                estimate
            );
        }

        std::cout
            << "\n--- Join algorithm comparison ---\n";

        for (JoinType type : {
            JoinType::NestedLoop,
            JoinType::HashJoin,
            JoinType::MergeJoin
        }) {
            const auto estimate =
                planner.estimateJoin(
                    type,
                    departments,
                    employees,
                    0.01
                );

            PlanDiagnostics::printJoin(estimate);
        }

        const auto emptyResult =
            planner.chooseScan(employees, 0.0);

        std::cout
            << "\n--- Empty-result edge case ---\n"
            << "Estimated rows: "
            << emptyResult.estimatedRows
            << "\nSelected scan: "
            << PlanDiagnostics::scanName(
                emptyResult.type
            )
            << '\n';

        if (emptyResult.estimatedRows != 0) {
            throw std::runtime_error(
                "Empty-result estimation failed."
            );
        }

        std::cout
            << "\nValidation tests passed.\n";

    } catch (const std::exception& error) {
        std::cerr
            << "Planner error: "
            << error.what()
            << '\n';

        return 1;
    }

    return 0;
}
