/*
 * HAVING: Filtering Aggregated Results, WHERE vs HAVING
 * ======================================================
 *
 * C++17 case study:
 *
 * A sales analytics engine receives transaction records and produces regional
 * performance reports. The implementation models the same conceptual stages
 * used by SQL:
 *
 *     FROM
 *       -> WHERE
 *       -> GROUP BY
 *       -> aggregate functions
 *       -> HAVING
 *       -> ORDER BY
 *
 * The program does not depend on an external database library. It implements
 * the analytical pipeline with C++ standard-library data structures.
 *
 * The final report identifies regions satisfying business-level aggregate
 * conditions, such as:
 *
 *     - minimum number of transactions
 *     - minimum units sold
 *     - minimum revenue
 *
 * This makes the distinction between row filtering and aggregate filtering
 * concrete in an industry-style reporting scenario.
 */

#include <algorithm>
#include <cassert>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;

// -----------------------------------------------------------------------------
// Domain model
// -----------------------------------------------------------------------------

struct Sale {
    int id;
    int employeeId;
    string date;
    string product;
    string region;
    int quantity;
    double unitPrice;
    double discount;

    double revenue() const {
        return quantity * unitPrice * (1.0 - discount);
    }
};

struct Employee {
    int id;
    string name;
    int departmentId;
    double salary;
    bool active;
};

struct Department {
    int id;
    string name;
};

struct RegionalReport {
    string region;
    size_t transactionCount = 0;
    int unitsSold = 0;
    double revenue = 0.0;
    size_t activeSellers = 0;
    double averageTransactionValue = 0.0;
};

struct ReportThresholds {
    size_t minimumTransactions = 0;
    int minimumUnits = 0;
    double minimumRevenue = 0.0;
};

// -----------------------------------------------------------------------------
// Formatting utilities
// -----------------------------------------------------------------------------

void printTitle(const string& title) {
    cout << "\n" << string(78, '=') << "\n";
    cout << title << "\n";
    cout << string(78, '=') << "\n";
}

void printMoney(double value) {
    cout << fixed << setprecision(2) << value;
}

void printReports(const vector<RegionalReport>& reports) {
    if (reports.empty()) {
        cout << "(no qualifying groups)\n";
        return;
    }

    cout
        << left
        << setw(12) << "Region"
        << setw(14) << "Transactions"
        << setw(12) << "Units"
        << setw(15) << "Revenue"
        << setw(14) << "Sellers"
        << setw(16) << "Avg Transaction"
        << "\n";

    cout << string(83, '-') << "\n";

    for (const auto& report : reports) {
        cout
            << left
            << setw(12) << report.region
            << setw(14) << report.transactionCount
            << setw(12) << report.unitsSold
            << setw(15);

        printMoney(report.revenue);

        cout
            << setw(14) << report.activeSellers
            << setw(16);

        printMoney(report.averageTransactionValue);

        cout << "\n";
    }
}

// -----------------------------------------------------------------------------
// Input validation
// -----------------------------------------------------------------------------

void validateSale(const Sale& sale) {
    if (sale.id <= 0) {
        throw invalid_argument("Sale ID must be positive.");
    }

    if (sale.employeeId <= 0) {
        throw invalid_argument("Employee ID must be positive.");
    }

    if (sale.quantity <= 0) {
        throw invalid_argument("Sale quantity must be positive.");
    }

    if (sale.unitPrice < 0.0) {
        throw invalid_argument("Unit price cannot be negative.");
    }

    if (sale.discount < 0.0 || sale.discount > 1.0) {
        throw invalid_argument("Discount must be between 0 and 1.");
    }

    if (sale.region.empty()) {
        throw invalid_argument("Region cannot be empty.");
    }

    if (sale.product.empty()) {
        throw invalid_argument("Product cannot be empty.");
    }
}

// -----------------------------------------------------------------------------
// Sample database
// -----------------------------------------------------------------------------

vector<Employee> buildEmployees() {
    return {
        {4, "Diana", 2, 70000, true},
        {5, "Evan", 2, 68000, true},
        {6, "Fatima", 2, 65000, true},
        {7, "George", 2, 62000, false}
    };
}

vector<Sale> buildSales() {
    vector<Sale> sales = {
        {1,  4, "2026-01-05", "Laptop",   "North",  4, 1000, 0.05},
        {2,  4, "2026-01-07", "Monitor",  "North",  6,  400, 0.00},
        {3,  5, "2026-01-10", "Laptop",   "South",  3, 1000, 0.10},
        {4,  5, "2026-01-12", "Keyboard", "South", 10,  100, 0.05},
        {5,  6, "2026-01-15", "Laptop",   "East",   8, 1000, 0.15},
        {6,  6, "2026-01-18", "Monitor",  "East",  12,  400, 0.10},
        {7,  4, "2026-02-02", "Laptop",   "North",  2, 1000, 0.00},
        {8,  5, "2026-02-04", "Monitor",  "South",  8,  400, 0.05},
        {9,  6, "2026-02-08", "Keyboard", "East",  15,  100, 0.00},
        {10, 4, "2026-02-10", "Headset",  "North", 20,   80, 0.10},
        {11, 5, "2026-02-15", "Laptop",   "South",  1, 1000, 0.00},
        {12, 6, "2026-02-20", "Monitor",  "East",   5,  400, 0.20},
        {13, 4, "2026-03-01", "Laptop",   "North", 10, 1000, 0.05},
        {14, 5, "2026-03-03", "Monitor",  "South",  2,  400, 0.00},
        {15, 6, "2026-03-05", "Keyboard", "East",   5,  100, 0.00},
        {16, 4, "2026-03-10", "Headset",  "North", 30,   80, 0.05},
        {17, 5, "2026-03-12", "Laptop",   "South",  7, 1000, 0.10},
        {18, 6, "2026-03-15", "Monitor",  "East",   4,  400, 0.00}
    };

    for (const auto& sale : sales) {
        validateSale(sale);
    }

    return sales;
}

// -----------------------------------------------------------------------------
// Employee lookup
// -----------------------------------------------------------------------------

unordered_map<int, Employee> buildEmployeeIndex(
    const vector<Employee>& employees
) {
    unordered_map<int, Employee> index;

    for (const auto& employee : employees) {
        if (employee.id <= 0) {
            throw invalid_argument("Employee ID must be positive.");
        }

        if (!index.emplace(employee.id, employee).second) {
            throw invalid_argument("Duplicate employee ID.");
        }
    }

    return index;
}

// -----------------------------------------------------------------------------
// WHERE stage
// -----------------------------------------------------------------------------

vector<Sale> whereFilter(
    const vector<Sale>& sales,
    const function<bool(const Sale&)>& predicate
) {
    vector<Sale> filtered;

    filtered.reserve(sales.size());

    for (const auto& sale : sales) {
        if (predicate(sale)) {
            filtered.push_back(sale);
        }
    }

    return filtered;
}

// -----------------------------------------------------------------------------
// GROUP BY + aggregate stage
// -----------------------------------------------------------------------------

vector<RegionalReport> groupAndAggregate(
    const vector<Sale>& sales,
    const unordered_map<int, Employee>& employees
) {
    /*
     * std::map is intentionally used here because it provides deterministic
     * region ordering. A hash map could provide average O(1) group lookup but
     * would not preserve sorted group order.
     */
    map<string, RegionalReport> groups;

    unordered_map<string, set<int>> sellerSets;

    for (const auto& sale : sales) {
        auto employeeIt = employees.find(sale.employeeId);

        if (employeeIt == employees.end()) {
            throw runtime_error(
                "Sale references an employee that does not exist."
            );
        }

        RegionalReport& report = groups[sale.region];

        report.region = sale.region;
        report.transactionCount++;
        report.unitsSold += sale.quantity;
        report.revenue += sale.revenue();

        if (employeeIt->second.active) {
            sellerSets[sale.region].insert(sale.employeeId);
        }
    }

    vector<RegionalReport> reports;
    reports.reserve(groups.size());

    for (auto& [region, report] : groups) {
        report.activeSellers = sellerSets[region].size();

        if (report.transactionCount > 0) {
            report.averageTransactionValue =
                report.revenue /
                static_cast<double>(report.transactionCount);
        }

        reports.push_back(report);
    }

    return reports;
}

// -----------------------------------------------------------------------------
// HAVING stage
// -----------------------------------------------------------------------------

vector<RegionalReport> havingFilter(
    const vector<RegionalReport>& reports,
    const ReportThresholds& thresholds
) {
    vector<RegionalReport> filtered;

    for (const auto& report : reports) {
        /*
         * This is the C++ equivalent of:
         *
         * HAVING COUNT(*) >= ?
         *    AND SUM(quantity) >= ?
         *    AND SUM(revenue_expression) >= ?
         *
         * The values already represent complete groups.
         */
        if (report.transactionCount >= thresholds.minimumTransactions &&
            report.unitsSold >= thresholds.minimumUnits &&
            report.revenue >= thresholds.minimumRevenue) {

            filtered.push_back(report);
        }
    }

    return filtered;
}

// -----------------------------------------------------------------------------
// ORDER BY stage
// -----------------------------------------------------------------------------

void orderByRevenueDescending(vector<RegionalReport>& reports) {
    sort(
        reports.begin(),
        reports.end(),
        [](const RegionalReport& left, const RegionalReport& right) {
            if (fabs(left.revenue - right.revenue) < 1e-9) {
                return left.region < right.region;
            }

            return left.revenue > right.revenue;
        }
    );
}

// -----------------------------------------------------------------------------
// Complete analytical pipeline
// -----------------------------------------------------------------------------

vector<RegionalReport> createReport(
    const vector<Sale>& sales,
    const unordered_map<int, Employee>& employeeIndex,
    const function<bool(const Sale&)>& wherePredicate,
    const ReportThresholds& thresholds
) {
    // WHERE: filter individual records.
    vector<Sale> filteredRows =
        whereFilter(sales, wherePredicate);

    // GROUP BY + aggregate: construct one report per region.
    vector<RegionalReport> grouped =
        groupAndAggregate(filteredRows, employeeIndex);

    // HAVING: filter complete groups.
    vector<RegionalReport> qualified =
        havingFilter(grouped, thresholds);

    // ORDER BY: sort final groups.
    orderByRevenueDescending(qualified);

    return qualified;
}

// -----------------------------------------------------------------------------
// Scenario 1: no WHERE, HAVING only
// -----------------------------------------------------------------------------

void demonstrateHavingOnly(
    const vector<Sale>& sales,
    const unordered_map<int, Employee>& employeeIndex
) {
    printTitle("1. HAVING-only regional report");

    ReportThresholds thresholds{
        0,
        40,
        0.0
    };

    auto report = createReport(
        sales,
        employeeIndex,
        [](const Sale&) {
            return true;
        },
        thresholds
    );

    printReports(report);

    cout << "\nBusiness rule: retain regions with at least 40 units.\n";
}

// -----------------------------------------------------------------------------
// Scenario 2: WHERE only
// -----------------------------------------------------------------------------

void demonstrateWhereOnly(
    const vector<Sale>& sales,
    const unordered_map<int, Employee>& employeeIndex
) {
    printTitle("2. WHERE-only row filtering");

    /*
     * This answers:
     *
     * "Which regions sold units in individual transactions containing at
     *  least 10 units?"
     *
     * It does NOT mean that the region's total units are at least 10.
     */
    auto report = createReport(
        sales,
        employeeIndex,
        [](const Sale& sale) {
            return sale.quantity >= 10;
        },
        ReportThresholds{0, 0, 0.0}
    );

    printReports(report);

    cout
        << "\nThe predicate examines each Sale before grouping.\n";
}

// -----------------------------------------------------------------------------
// Scenario 3: WHERE + HAVING
// -----------------------------------------------------------------------------

void demonstrateWhereAndHaving(
    const vector<Sale>& sales,
    const unordered_map<int, Employee>& employeeIndex
) {
    printTitle("3. WHERE + GROUP BY + HAVING");

    auto report = createReport(
        sales,
        employeeIndex,

        // WHERE: only February and March sales participate.
        [](const Sale& sale) {
            return sale.date >= "2026-02-01";
        },

        // HAVING: then filter the resulting regional groups.
        ReportThresholds{
            4,
            30,
            5000.0
        }
    );

    printReports(report);

    cout
        << "\nRow filter: date >= 2026-02-01\n"
        << "Group filters: transactions >= 4, units >= 30, revenue >= 5000\n";
}

// -----------------------------------------------------------------------------
// Scenario 4: active employees
// -----------------------------------------------------------------------------

void demonstrateActiveEmployees(
    const vector<Sale>& sales,
    const unordered_map<int, Employee>& employeeIndex
) {
    printTitle("4. WHERE based on joined entity state");

    /*
     * In SQL, this would resemble:
     *
     * FROM sales
     * JOIN employees ON employees.id = sales.employee_id
     * WHERE employees.active = 1
     * GROUP BY region
     * HAVING COUNT(*) >= 4
     *
     * The lookup below models the JOIN.
     */
    auto report = createReport(
        sales,
        employeeIndex,

        [&employeeIndex](const Sale& sale) {
            auto it = employeeIndex.find(sale.employeeId);

            return it != employeeIndex.end() &&
                   it->second.active;
        },

        ReportThresholds{
            4,
            0,
            0.0
        }
    );

    printReports(report);
}

// -----------------------------------------------------------------------------
// Distinct products per region
// -----------------------------------------------------------------------------

void demonstrateDistinctProducts(
    const vector<Sale>& sales
) {
    printTitle("5. COUNT(DISTINCT product) + HAVING");

    map<string, set<string>> productsByRegion;

    for (const auto& sale : sales) {
        productsByRegion[sale.region].insert(sale.product);
    }

    cout
        << left
        << setw(12) << "Region"
        << setw(20) << "Distinct Products"
        << "\n";

    cout << string(32, '-') << "\n";

    for (const auto& [region, products] : productsByRegion) {
        if (products.size() >= 3) {
            cout
                << left
                << setw(12) << region
                << setw(20) << products.size()
                << "\n";
        }
    }

    cout
        << "\nHAVING-like condition: distinct product count >= 3.\n";
}

// -----------------------------------------------------------------------------
// Conditional aggregation
// -----------------------------------------------------------------------------

void demonstrateConditionalAggregation(
    const vector<Sale>& sales
) {
    printTitle("6. Conditional aggregation");

    struct ProductMetrics {
        int laptopUnits = 0;
        int monitorUnits = 0;
    };

    map<string, ProductMetrics> metrics;

    for (const auto& sale : sales) {
        if (sale.product == "Laptop") {
            metrics[sale.region].laptopUnits += sale.quantity;
        }

        if (sale.product == "Monitor") {
            metrics[sale.region].monitorUnits += sale.quantity;
        }
    }

    for (const auto& [region, metric] : metrics) {
        // Equivalent to a HAVING condition on the conditional SUM.
        if (metric.laptopUnits >= 5) {
            cout
                << region
                << ": laptop units = "
                << metric.laptopUnits
                << ", monitor units = "
                << metric.monitorUnits
                << "\n";
        }
    }
}

// -----------------------------------------------------------------------------
// Threshold validation
// -----------------------------------------------------------------------------

void validateThresholds(const ReportThresholds& thresholds) {
    if (thresholds.minimumRevenue < 0.0) {
        throw invalid_argument(
            "Minimum revenue cannot be negative."
        );
    }
}

// -----------------------------------------------------------------------------
// Complexity discussion
// -----------------------------------------------------------------------------

void printComplexityAnalysis() {
    printTitle("7. Complexity and implementation trade-offs");

    cout
        << R"(
WHERE filtering:
    A single scan is typically O(n).

GROUP BY:
    With an ordered map, grouping is approximately O(n log g),
    where g is the number of groups.

    With a hash map, average grouping can approach O(n), but ordering
    then requires additional work.

HAVING:
    Filtering g completed groups is O(g).

Sorting:
    Ordering g groups by revenue is O(g log g).

Total:
    Approximately O(n log g + g log g) with ordered grouping and sorting.

Memory:
    The report stores O(g) aggregate groups.
    The distinct-product calculation additionally stores unique products.

Trade-off:
    Hash-based grouping can be faster for very large datasets when ordered
    output is not immediately required. Ordered grouping provides deterministic
    ordering and predictable traversal.
)";
}

// -----------------------------------------------------------------------------
// Security and reliability
// -----------------------------------------------------------------------------

void printSecurityConsiderations() {
    printTitle("8. Security and reliability considerations");

    cout
        << R"(
1. Validate imported transaction data before aggregation.

2. Do not trust quantities, prices, discounts, IDs, or dates simply because
   they originated outside the current process.

3. In real SQL applications, use parameterized queries rather than string
   concatenation for user-controlled values.

4. Validate dynamic SQL identifiers separately. Parameter binding normally
   applies to values, not arbitrary table or column names.

5. Apply authorization before exposing aggregated business information.
   A correct HAVING clause does not itself enforce application-level access
   control.

6. Be careful with aggregate reports that can reveal sensitive information.
   Very small groups can sometimes expose individual-level information.

7. Treat floating-point money calculations carefully. Production financial
   systems commonly use fixed-precision decimal representations or integer
   minor units instead of binary floating-point arithmetic.
)";
}

// -----------------------------------------------------------------------------
// Edge cases
// -----------------------------------------------------------------------------

void demonstrateEdgeCases(
    const vector<Sale>& sales,
    const unordered_map<int, Employee>& employeeIndex
) {
    printTitle("9. Edge cases");

    auto impossible = createReport(
        sales,
        employeeIndex,
        [](const Sale&) {
            return true;
        },
        ReportThresholds{
            0,
            1'000'000,
            0.0
        }
    );

    cout << "Impossible HAVING threshold:\n";
    printReports(impossible);

    auto emptyInput = createReport(
        {},
        employeeIndex,
        [](const Sale&) {
            return true;
        },
        ReportThresholds{0, 0, 0.0}
    );

    cout << "\nEmpty source data:\n";
    printReports(emptyInput);

    auto singleRow = createReport(
        {sales.front()},
        employeeIndex,
        [](const Sale&) {
            return true;
        },
        ReportThresholds{1, 1, 0.0}
    );

    cout << "\nSingle-row source data:\n";
    printReports(singleRow);
}

// -----------------------------------------------------------------------------
// Correctness tests
// -----------------------------------------------------------------------------

void runTests(
    const vector<Sale>& sales,
    const unordered_map<int, Employee>& employeeIndex
) {
    printTitle("10. Correctness tests");

    auto allGroups = createReport(
        sales,
        employeeIndex,
        [](const Sale&) {
            return true;
        },
        ReportThresholds{0, 0, 0.0}
    );

    assert(allGroups.size() == 3);

    auto qualified = createReport(
        sales,
        employeeIndex,
        [](const Sale&) {
            return true;
        },
        ReportThresholds{0, 40, 0.0}
    );

    assert(qualified.size() == 2);

    for (const auto& report : qualified) {
        assert(report.unitsSold >= 40);
    }

    auto impossible = createReport(
        sales,
        employeeIndex,
        [](const Sale&) {
            return true;
        },
        ReportThresholds{0, 1'000'000, 0.0}
    );

    assert(impossible.empty());

    cout << "All tests passed.\n";
}

// -----------------------------------------------------------------------------
// Explain SQL equivalent
// -----------------------------------------------------------------------------

void printSqlEquivalent() {
    printTitle("11. SQL equivalent of the C++ pipeline");

    cout
        << R"(
SELECT
    region,
    COUNT(*) AS transaction_count,
    SUM(quantity) AS units_sold,
    SUM(quantity * unit_price * (1 - discount)) AS revenue
FROM sales
WHERE sale_date >= '2026-02-01'
GROUP BY region
HAVING COUNT(*) >= 4
   AND SUM(quantity) >= 30
   AND SUM(quantity * unit_price * (1 - discount)) >= 5000
ORDER BY revenue DESC;

Mapping:

    C++ whereFilter()
        -> SQL WHERE

    groupAndAggregate()
        -> SQL GROUP BY + aggregate functions

    havingFilter()
        -> SQL HAVING

    orderByRevenueDescending()
        -> SQL ORDER BY
)";
}

// -----------------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------------

int main() {
    try {
        printTitle("HAVING: Filtering Aggregated Results");

        vector<Employee> employees = buildEmployees();
        vector<Sale> sales = buildSales();

        auto employeeIndex = buildEmployeeIndex(employees);

        demonstrateHavingOnly(sales, employeeIndex);
        demonstrateWhereOnly(sales, employeeIndex);
        demonstrateWhereAndHaving(sales, employeeIndex);
        demonstrateActiveEmployees(sales, employeeIndex);
        demonstrateDistinctProducts(sales);
        demonstrateConditionalAggregation(sales);

        printComplexityAnalysis();
        printSecurityConsiderations();

        demonstrateEdgeCases(sales, employeeIndex);
        runTests(sales, employeeIndex);
        printSqlEquivalent();

        printTitle("Case study completed");
    }
    catch (const exception& error) {
        cerr << "Application error: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
