/*
 * GROUP BY: Grouping Rows, Grouped Calculations, and Grouping Multiple Columns
 *
 * C++17 industry-style case study:
 * Sales Analytics Aggregation Engine
 *
 * The program models a small analytical system that:
 * - stores sales transactions
 * - validates input
 * - filters rows
 * - groups by one or more dimensions
 * - calculates COUNT, SUM, AVG, MIN, MAX
 * - performs DISTINCT-style calculations
 * - performs conditional aggregation
 * - applies HAVING-like filters
 * - sorts grouped results
 * - detects a common join-multiplication problem
 * - demonstrates hierarchical totals
 * - discusses algorithmic complexity
 *
 * Compile:
 *     g++ -std=c++17 -O2 group_by_case_study.cpp -o group_by_case_study
 *
 * Run:
 *     ./group_by_case_study
 */

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;


// -----------------------------------------------------------------------------
// Domain model
// -----------------------------------------------------------------------------

struct Sale {
    int orderId;
    string customer;
    optional<string> region;
    string city;
    optional<string> category;
    string product;
    string salesperson;
    int quantity;
    double unitPrice;
    double discount;
    string status;
};


// -----------------------------------------------------------------------------
// Aggregated result
// -----------------------------------------------------------------------------

struct GroupResult {
    string region;
    string category;
    size_t orders = 0;
    long long units = 0;
    double grossSales = 0.0;
    double netSales = 0.0;
    double averageOrderValue = 0.0;
    size_t uniqueCustomers = 0;
};


// -----------------------------------------------------------------------------
// Utility functions
// -----------------------------------------------------------------------------

string optionalValue(const optional<string>& value) {
    return value.has_value() ? value.value() : "NULL";
}


string money(double value) {
    ostringstream output;
    output << fixed << setprecision(2) << "Rs. " << value;
    return output.str();
}


double netSale(const Sale& sale) {
    return sale.quantity *
           sale.unitPrice *
           (1.0 - sale.discount);
}


void printLine(char character = '=') {
    cout << string(90, character) << '\n';
}


void printTitle(const string& title) {
    cout << '\n';
    printLine();
    cout << title << '\n';
    printLine();
}


// -----------------------------------------------------------------------------
// Sample data
// -----------------------------------------------------------------------------

vector<Sale> buildSalesData() {
    return {
        {1001, "Asha", "North", "Delhi", "Electronics", "Laptop",
         "Ravi", 2, 75000.00, 0.05, "Completed"},

        {1002, "Bharat", "North", "Lucknow", "Furniture", "Chair",
         "Neha", 5, 4500.00, 0.10, "Completed"},

        {1003, "Charu", "South", "Bengaluru", "Electronics", "Phone",
         "Ravi", 3, 30000.00, 0.00, "Completed"},

        {1004, "Dev", "West", "Mumbai", "Office", "Desk",
         "Meera", 4, 12000.00, 0.15, "Cancelled"},

        {1005, "Esha", "North", "Delhi", "Electronics", "Monitor",
         "Ravi", 4, 18000.00, 0.08, "Completed"},

        {1006, "Farhan", "East", "Kolkata", "Furniture", "Table",
         "Neha", 2, 16000.00, 0.05, "Completed"},

        {1007, "Gita", "South", "Chennai", "Office", "Printer",
         "Meera", 2, 22000.00, 0.12, "Completed"},

        {1008, "Hari", "West", "Pune", "Electronics", "Tablet",
         "Ravi", 6, 25000.00, 0.07, "Completed"},

        {1009, "Isha", "North", "Lucknow", "Office", "Printer",
         "Neha", 1, 22000.00, 0.00, "Completed"},

        {1010, "Jai", "South", "Hyderabad", "Furniture", "Chair",
         "Meera", 10, 4500.00, 0.20, "Completed"},

        {1011, "Kiran", "NULL-REGION", "Jaipur", "Electronics", "Keyboard",
         "Ravi", 8, 2500.00, 0.03, "Completed"},

        {1012, "Lata", "East", "Patna", nullopt, "Desk",
         "Neha", 3, 12000.00, 0.10, "Completed"}
    };
}


// -----------------------------------------------------------------------------
// Validation
// -----------------------------------------------------------------------------

void validateSale(const Sale& sale) {
    if (sale.orderId <= 0) {
        throw invalid_argument("Order ID must be positive.");
    }

    if (sale.quantity <= 0) {
        throw invalid_argument(
            "Quantity must be greater than zero for order " +
            to_string(sale.orderId)
        );
    }

    if (sale.unitPrice < 0.0) {
        throw invalid_argument(
            "Unit price cannot be negative for order " +
            to_string(sale.orderId)
        );
    }

    if (sale.discount < 0.0 || sale.discount > 1.0) {
        throw invalid_argument(
            "Discount must be between 0 and 1 for order " +
            to_string(sale.orderId)
        );
    }

    if (sale.customer.empty()) {
        throw invalid_argument(
            "Customer cannot be empty for order " +
            to_string(sale.orderId)
        );
    }

    if (sale.status != "Completed" &&
        sale.status != "Cancelled") {
        throw invalid_argument(
            "Unsupported order status for order " +
            to_string(sale.orderId)
        );
    }
}


void validateDataset(const vector<Sale>& sales) {
    set<int> orderIds;

    for (const Sale& sale : sales) {
        validateSale(sale);

        if (!orderIds.insert(sale.orderId).second) {
            throw invalid_argument(
                "Duplicate order ID: " +
                to_string(sale.orderId)
            );
        }
    }
}


// -----------------------------------------------------------------------------
// WHERE-like filtering
// -----------------------------------------------------------------------------

vector<Sale> filterRows(
    const vector<Sale>& sales,
    const string& status
) {
    vector<Sale> result;

    for (const Sale& sale : sales) {
        if (sale.status == status) {
            result.push_back(sale);
        }
    }

    return result;
}


// -----------------------------------------------------------------------------
// Grouping by one dimension
// -----------------------------------------------------------------------------

map<string, vector<Sale>> groupByRegion(
    const vector<Sale>& sales
) {
    map<string, vector<Sale>> groups;

    for (const Sale& sale : sales) {
        const string region =
            sale.region.has_value()
                ? sale.region.value()
                : "NULL";

        groups[region].push_back(sale);
    }

    return groups;
}


// -----------------------------------------------------------------------------
// Grouping by multiple dimensions
// -----------------------------------------------------------------------------

using CompositeKey = pair<string, string>;


map<CompositeKey, vector<Sale>> groupByRegionAndCategory(
    const vector<Sale>& sales
) {
    map<CompositeKey, vector<Sale>> groups;

    for (const Sale& sale : sales) {
        const string region =
            sale.region.has_value()
                ? sale.region.value()
                : "NULL";

        const string category =
            sale.category.has_value()
                ? sale.category.value()
                : "NULL";

        groups[{region, category}].push_back(sale);
    }

    return groups;
}


// -----------------------------------------------------------------------------
// Aggregate functions
// -----------------------------------------------------------------------------

long long countRows(const vector<Sale>& rows) {
    return static_cast<long long>(rows.size());
}


long long sumQuantity(const vector<Sale>& rows) {
    long long total = 0;

    for (const Sale& sale : rows) {
        total += sale.quantity;
    }

    return total;
}


double sumNetSales(const vector<Sale>& rows) {
    double total = 0.0;

    for (const Sale& sale : rows) {
        total += netSale(sale);
    }

    return total;
}


double sumGrossSales(const vector<Sale>& rows) {
    double total = 0.0;

    for (const Sale& sale : rows) {
        total +=
            static_cast<double>(sale.quantity) *
            sale.unitPrice;
    }

    return total;
}


double averageQuantity(const vector<Sale>& rows) {
    if (rows.empty()) {
        throw domain_error(
            "Cannot calculate average quantity for an empty group."
        );
    }

    return static_cast<double>(sumQuantity(rows)) /
           static_cast<double>(rows.size());
}


double minimumUnitPrice(const vector<Sale>& rows) {
    if (rows.empty()) {
        throw domain_error(
            "Cannot calculate minimum for an empty group."
        );
    }

    double result = numeric_limits<double>::max();

    for (const Sale& sale : rows) {
        result = min(result, sale.unitPrice);
    }

    return result;
}


double maximumUnitPrice(const vector<Sale>& rows) {
    if (rows.empty()) {
        throw domain_error(
            "Cannot calculate maximum for an empty group."
        );
    }

    double result = numeric_limits<double>::lowest();

    for (const Sale& sale : rows) {
        result = max(result, sale.unitPrice);
    }

    return result;
}


size_t distinctCustomerCount(
    const vector<Sale>& rows
) {
    set<string> customers;

    for (const Sale& sale : rows) {
        if (!sale.customer.empty()) {
            customers.insert(sale.customer);
        }
    }

    return customers.size();
}


// -----------------------------------------------------------------------------
// One-column grouped report
// -----------------------------------------------------------------------------

void reportByRegion(
    const vector<Sale>& sales
) {
    printTitle("Grouped report by region");

    const auto groups = groupByRegion(sales);

    cout
        << left
        << setw(18) << "Region"
        << setw(10) << "Orders"
        << setw(12) << "Units"
        << setw(18) << "Net Sales"
        << setw(18) << "Avg Units"
        << '\n';

    printLine('-');

    for (const auto& [region, rows] : groups) {
        cout
            << left
            << setw(18) << region
            << setw(10) << countRows(rows)
            << setw(12) << sumQuantity(rows)
            << setw(18) << money(sumNetSales(rows))
            << setw(18) << fixed << setprecision(2)
            << averageQuantity(rows)
            << '\n';
    }
}


// -----------------------------------------------------------------------------
// Multiple-column grouped report
// -----------------------------------------------------------------------------

vector<GroupResult> buildRegionCategoryReport(
    const vector<Sale>& sales
) {
    const auto groups =
        groupByRegionAndCategory(sales);

    vector<GroupResult> results;

    for (const auto& [key, rows] : groups) {
        const auto& [region, category] = key;

        const double totalNetSales =
            sumNetSales(rows);

        GroupResult result;
        result.region = region;
        result.category = category;
        result.orders = rows.size();
        result.units = sumQuantity(rows);
        result.grossSales = sumGrossSales(rows);
        result.netSales = totalNetSales;
        result.averageOrderValue =
            totalNetSales /
            static_cast<double>(rows.size());
        result.uniqueCustomers =
            distinctCustomerCount(rows);

        results.push_back(result);
    }

    return results;
}


void printRegionCategoryReport(
    vector<GroupResult> results
) {
    sort(
        results.begin(),
        results.end(),
        [](const GroupResult& left,
           const GroupResult& right) {
            if (left.netSales != right.netSales) {
                return left.netSales > right.netSales;
            }

            if (left.region != right.region) {
                return left.region < right.region;
            }

            return left.category < right.category;
        }
    );

    cout
        << left
        << setw(16) << "Region"
        << setw(18) << "Category"
        << setw(9) << "Orders"
        << setw(9) << "Units"
        << setw(18) << "Net Sales"
        << setw(12) << "Customers"
        << '\n';

    printLine('-');

    for (const GroupResult& result : results) {
        cout
            << left
            << setw(16) << result.region
            << setw(18) << result.category
            << setw(9) << result.orders
            << setw(9) << result.units
            << setw(18) << money(result.netSales)
            << setw(12) << result.uniqueCustomers
            << '\n';
    }
}


// -----------------------------------------------------------------------------
// HAVING-like filtering
// -----------------------------------------------------------------------------

vector<GroupResult> applyHaving(
    const vector<GroupResult>& results,
    double minimumSales
) {
    vector<GroupResult> filtered;

    for (const GroupResult& result : results) {
        if (result.netSales >= minimumSales) {
            filtered.push_back(result);
        }
    }

    return filtered;
}


// -----------------------------------------------------------------------------
// Conditional aggregation
// -----------------------------------------------------------------------------

struct RegionStatusResult {
    string region;
    size_t completedOrders = 0;
    size_t cancelledOrders = 0;
    double completedSales = 0.0;
};


vector<RegionStatusResult> buildStatusReport(
    const vector<Sale>& sales
) {
    const auto groups = groupByRegion(sales);
    vector<RegionStatusResult> results;

    for (const auto& [region, rows] : groups) {
        RegionStatusResult result;
        result.region = region;

        for (const Sale& sale : rows) {
            if (sale.status == "Completed") {
                ++result.completedOrders;
                result.completedSales += netSale(sale);
            } else if (sale.status == "Cancelled") {
                ++result.cancelledOrders;
            }
        }

        results.push_back(result);
    }

    return results;
}


void printStatusReport(
    const vector<RegionStatusResult>& results
) {
    printTitle("Conditional aggregation by region");

    for (const auto& result : results) {
        cout
            << result.region
            << " | completed orders = "
            << result.completedOrders
            << " | cancelled orders = "
            << result.cancelledOrders
            << " | completed sales = "
            << money(result.completedSales)
            << '\n';
    }
}


// -----------------------------------------------------------------------------
// Distinct grouped customers
// -----------------------------------------------------------------------------

void demonstrateDistinctCustomers(
    const vector<Sale>& sales
) {
    printTitle("Distinct customers within each region");

    const auto groups = groupByRegion(sales);

    for (const auto& [region, rows] : groups) {
        cout
            << region
            << " -> "
            << distinctCustomerCount(rows)
            << " unique customers\n";
    }
}


// -----------------------------------------------------------------------------
// Rollup-style hierarchy
// -----------------------------------------------------------------------------

void demonstrateRollup(
    const vector<Sale>& sales
) {
    printTitle("ROLLUP-style hierarchical totals");

    const vector<GroupResult> details =
        buildRegionCategoryReport(sales);

    cout << "Detailed groups:\n";

    for (const GroupResult& result : details) {
        cout
            << result.region
            << " / "
            << result.category
            << " -> "
            << money(result.netSales)
            << '\n';
    }

    const auto regionGroups =
        groupByRegion(sales);

    cout << "\nRegion totals:\n";

    for (const auto& [region, rows] : regionGroups) {
        cout
            << region
            << " / ALL CATEGORIES -> "
            << money(sumNetSales(rows))
            << '\n';
    }

    cout << "\nGrand total:\n";

    cout
        << "ALL REGIONS / ALL CATEGORIES -> "
        << money(sumNetSales(sales))
        << '\n';
}


// -----------------------------------------------------------------------------
// Join multiplication case study
// -----------------------------------------------------------------------------

struct Order {
    int orderId;
    int customerId;
    double amount;
};


struct CustomerTag {
    int customerId;
    string tag;
};


void demonstrateJoinMultiplication() {
    printTitle("Join multiplication: a critical GROUP BY pitfall");

    vector<Order> orders = {
        {1, 10, 100.0},
        {2, 20, 200.0}
    };

    vector<CustomerTag> tags = {
        {10, "VIP"},
        {10, "Wholesale"},
        {20, "Retail"}
    };

    double originalTotal = 0.0;

    for (const auto& order : orders) {
        originalTotal += order.amount;
    }

    struct JoinedRow {
        int orderId;
        int customerId;
        double amount;
        string tag;
    };

    vector<JoinedRow> joined;

    for (const auto& order : orders) {
        for (const auto& tag : tags) {
            if (order.customerId == tag.customerId) {
                joined.push_back({
                    order.orderId,
                    order.customerId,
                    order.amount,
                    tag.tag
                });
            }
        }
    }

    double joinedTotal = 0.0;

    for (const auto& row : joined) {
        joinedTotal += row.amount;
    }

    cout << "Original order rows: "
         << orders.size() << '\n';

    cout << "Joined rows: "
         << joined.size() << '\n';

    cout << "Original amount: "
         << money(originalTotal) << '\n';

    cout << "Naively summed joined amount: "
         << money(joinedTotal) << '\n';

    cout
        << "\nThe first order has two matching tags, so it appears twice "
        << "after the one-to-many join. Summing the repeated amount changes "
        << "the aggregate. Real analytical queries must account for join "
        << "cardinality before grouping.\n";
}


// -----------------------------------------------------------------------------
// Top-N groups
// -----------------------------------------------------------------------------

void demonstrateTopGroups(
    const vector<Sale>& sales
) {
    printTitle("Top groups by net sales");

    const vector<Sale> completed =
        filterRows(sales, "Completed");

    vector<GroupResult> results =
        buildRegionCategoryReport(completed);

    sort(
        results.begin(),
        results.end(),
        [](const GroupResult& left,
           const GroupResult& right) {
            return left.netSales > right.netSales;
        }
    );

    const size_t limit =
        min<size_t>(3, results.size());

    for (size_t index = 0; index < limit; ++index) {
        cout
            << index + 1
            << ". "
            << results[index].region
            << " / "
            << results[index].category
            << " -> "
            << money(results[index].netSales)
            << '\n';
    }
}


// -----------------------------------------------------------------------------
// Financial precision discussion
// -----------------------------------------------------------------------------

void demonstrateFinancialPrecision() {
    printTitle("Financial precision");

    const double a = 0.1;
    const double b = 0.2;
    const double result = a + b;

    cout << setprecision(17);
    cout << "0.1 + 0.2 represented as double: "
         << result << '\n';

    cout << setprecision(2);

    cout
        << "\nBinary floating-point is not a decimal currency representation. "
        << "Production financial systems commonly use fixed-point integers "
        << "or database DECIMAL/NUMERIC types for monetary calculations.\n";
}


// -----------------------------------------------------------------------------
// Complexity discussion
// -----------------------------------------------------------------------------

void explainComplexity() {
    printTitle("Algorithmic complexity");

    cout
        << "Hash-based GROUP BY:\n"
        << "  Expected time: O(n)\n"
        << "  Additional group-state memory: O(g)\n"
        << "  where n = number of rows and g = number of groups.\n\n";

    cout
        << "Sort-based grouping:\n"
        << "  Sorting time: O(n log n)\n"
        << "  Sequential group scan: O(n)\n\n";

    cout
        << "This program uses std::map for deterministic ordered groups, "
        << "which generally provides O(log g) lookup/insertion. A production "
        << "hash-based implementation can use std::unordered_map when ordered "
        << "iteration is not required.\n\n";

    cout
        << "Database engines may use hash aggregation, sort aggregation, "
        << "parallel aggregation, partial aggregation, indexes, or other "
        << "optimizer-selected strategies.\n";
}


// -----------------------------------------------------------------------------
// SQL equivalent
// -----------------------------------------------------------------------------

void printEquivalentSQL() {
    printTitle("SQL equivalent");

    cout
        << "SELECT\n"
        << "    region,\n"
        << "    category,\n"
        << "    COUNT(*) AS orders,\n"
        << "    SUM(quantity) AS units,\n"
        << "    SUM(quantity * unit_price * (1 - discount)) AS net_sales\n"
        << "FROM sales\n"
        << "WHERE status = 'Completed'\n"
        << "GROUP BY region, category\n"
        << "HAVING SUM(quantity * unit_price * (1 - discount)) >= 10000\n"
        << "ORDER BY net_sales DESC;\n";
}


// -----------------------------------------------------------------------------
// Interactive query demonstration
// -----------------------------------------------------------------------------

void interactiveRegionLookup(
    const vector<Sale>& sales
) {
    printTitle("Input processing: region lookup");

    cout << "Enter a region to inspect "
         << "(North, South, East, West, NULL): ";

    string requestedRegion;
    cin >> requestedRegion;

    const auto groups = groupByRegion(sales);

    const auto iterator =
        groups.find(requestedRegion);

    if (iterator == groups.end()) {
        cout << "No matching group exists.\n";
        return;
    }

    const auto& rows = iterator->second;

    cout << "Region: "
         << requestedRegion << '\n';

    cout << "Orders: "
         << rows.size() << '\n';

    cout << "Units: "
         << sumQuantity(rows) << '\n';

    cout << "Net sales: "
         << money(sumNetSales(rows)) << '\n';
}


// -----------------------------------------------------------------------------
// Complete analytical workflow
// -----------------------------------------------------------------------------

void runCompleteWorkflow(
    const vector<Sale>& allSales
) {
    printTitle("Complete analytical workflow");

    /*
     * Stage 1: WHERE.
     *
     * Cancelled orders are removed before aggregation because the business
     * question is concerned with completed sales.
     */
    const vector<Sale> completed =
        filterRows(allSales, "Completed");

    /*
     * Stage 2: GROUP BY.
     *
     * Each unique (region, category) pair becomes one group.
     */
    vector<GroupResult> groups =
        buildRegionCategoryReport(completed);

    /*
     * Stage 3: HAVING.
     *
     * The threshold is applied to aggregate values, not individual rows.
     */
    vector<GroupResult> qualified =
        applyHaving(groups, 10000.0);

    /*
     * Stage 4: ORDER BY.
     *
     * Grouped results are explicitly sorted by aggregate value.
     */
    sort(
        qualified.begin(),
        qualified.end(),
        [](const GroupResult& left,
           const GroupResult& right) {
            return left.netSales > right.netSales;
        }
    );

    printRegionCategoryReport(qualified);

    cout
        << "\nThe workflow models:\n"
        << "WHERE -> GROUP BY -> aggregate calculations -> HAVING -> ORDER BY\n";
}


// -----------------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------------

int main() {
    try {
        vector<Sale> sales = buildSalesData();

        validateDataset(sales);

        printTitle("C++ GROUP BY case study");

        cout
            << "Scenario: an analytical sales system needs to calculate "
            << "regional and category-level performance from transaction rows.\n";

        reportByRegion(sales);

        printTitle("Region + category analysis");
        const auto detailedReport =
            buildRegionCategoryReport(sales);

        printRegionCategoryReport(detailedReport);

        printStatusReport(
            buildStatusReport(sales)
        );

        demonstrateDistinctCustomers(sales);

        demonstrateTopGroups(sales);

        demonstrateRollup(sales);

        demonstrateJoinMultiplication();

        demonstrateFinancialPrecision();

        explainComplexity();

        printEquivalentSQL();

        runCompleteWorkflow(sales);

        printTitle("Important implementation decisions");

        cout
            << "1. std::map provides deterministic ordering for groups.\n"
            << "2. std::vector stores source rows and group members.\n"
            << "3. std::set implements DISTINCT-style customer counting.\n"
            << "4. std::optional represents nullable dimensions.\n"
            << "5. Validation prevents invalid quantities, prices, discounts, "
            << "and duplicate order IDs.\n"
            << "6. Separate filtering, grouping, aggregation, and HAVING-like "
            << "functions keep the analytical workflow modular.\n"
            << "7. Sorting is performed explicitly when ranking is required.\n";

        /*
         * The interactive function is intentionally not called by default.
         * This keeps the program convenient for automated execution while
         * retaining complete input-processing logic for manual experimentation.
         *
         * To use it in a terminal, uncomment:
         *
         * interactiveRegionLookup(sales);
         */
    }
    catch (const exception& error) {
        cerr
            << "Fatal error: "
            << error.what()
            << '\n';

        return 1;
    }

    printTitle("Program completed");
    cout << "GROUP BY case study executed successfully.\n";

    return 0;
}
