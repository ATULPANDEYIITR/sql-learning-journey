/*
 * Aggregate Functions: COUNT, SUM, AVG, MIN, MAX
 *
 * C++17 technical case study:
 * A sales analytics engine that models a small retail business and computes
 * SQL-style aggregate metrics over transactional data.
 *
 * The implementation demonstrates:
 * - COUNT
 * - SUM
 * - AVG
 * - MIN
 * - MAX
 * - NULL-like optional values
 * - DISTINCT counting
 * - GROUP BY
 * - HAVING-style filtering
 * - conditional aggregation
 * - joins through indexed lookups
 * - customer and product analytics
 * - monthly aggregation
 * - running totals
 * - ranking
 * - validation
 * - financial representation using integer paise
 * - one-pass aggregation
 * - complexity considerations
 * - duplicate join hazards
 *
 * Compile:
 *     g++ -std=c++17 -O2 aggregate_functions.cpp -o aggregate_functions
 *
 * Run:
 *     ./aggregate_functions
 */

#include <algorithm>
#include <cassert>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;


// -----------------------------------------------------------------------------
// 1. Domain models
// -----------------------------------------------------------------------------

struct Customer {
    int id;
    string name;
    string city;
    string type;
};

struct Product {
    int id;
    string name;
    string category;
    long long pricePaise;
    int stock;
};

struct Sale {
    int id;
    int customerId;
    int productId;
    string date;
    int quantity;
    long long unitPricePaise;

    // std::optional models SQL-like NULL:
    // a missing discount is different from a discount of zero.
    optional<long long> discountPaise;

    string salesperson;
};

struct AggregateResult {
    long long count = 0;
    long long sum = 0;
    double average = 0.0;
    optional<long long> minimum;
    optional<long long> maximum;
};


// -----------------------------------------------------------------------------
// 2. Utility functions
// -----------------------------------------------------------------------------

string money(long long paise) {
    ostringstream output;
    output << "Rs "
           << paise / 100
           << '.'
           << setw(2)
           << setfill('0')
           << llabs(paise % 100);
    return output.str();
}

void printTitle(const string& title) {
    cout << "\n" << string(80, '=') << "\n";
    cout << title << "\n";
    cout << string(80, '=') << "\n";
}

template <typename T>
void printVector(const vector<T>& values) {
    for (const auto& value : values) {
        cout << value << ' ';
    }
    cout << '\n';
}


// -----------------------------------------------------------------------------
// 3. Generic aggregate functions
// -----------------------------------------------------------------------------

template <typename Container, typename Function>
long long countValues(const Container& rows, Function selector) {
    long long count = 0;

    for (const auto& row : rows) {
        if (selector(row).has_value()) {
            ++count;
        }
    }

    return count;
}

template <typename Container, typename Function>
long long sumValues(const Container& rows, Function selector) {
    long long total = 0;

    for (const auto& row : rows) {
        const auto value = selector(row);

        if (value.has_value()) {
            total += value.value();
        }
    }

    return total;
}

template <typename Container, typename Function>
optional<long long> minimumValue(
    const Container& rows,
    Function selector
) {
    optional<long long> result;

    for (const auto& row : rows) {
        const auto value = selector(row);

        if (!value.has_value()) {
            continue;
        }

        if (!result.has_value() || value.value() < result.value()) {
            result = value.value();
        }
    }

    return result;
}

template <typename Container, typename Function>
optional<long long> maximumValue(
    const Container& rows,
    Function selector
) {
    optional<long long> result;

    for (const auto& row : rows) {
        const auto value = selector(row);

        if (!value.has_value()) {
            continue;
        }

        if (!result.has_value() || value.value() > result.value()) {
            result = value.value();
        }
    }

    return result;
}

template <typename Container, typename Function>
optional<double> averageValue(
    const Container& rows,
    Function selector
) {
    long long total = 0;
    long long count = 0;

    for (const auto& row : rows) {
        const auto value = selector(row);

        if (!value.has_value()) {
            continue;
        }

        total += value.value();
        ++count;
    }

    if (count == 0) {
        return nullopt;
    }

    return static_cast<double>(total) /
           static_cast<double>(count);
}


// -----------------------------------------------------------------------------
// 4. Example data repository
// -----------------------------------------------------------------------------

class SalesRepository {
private:
    vector<Customer> customers;
    vector<Product> products;
    vector<Sale> sales;

public:
    SalesRepository() {
        customers = {
            {1, "Aarav Sharma", "Lucknow", "Retail"},
            {2, "Meera Singh", "Delhi", "Business"},
            {3, "Rohan Verma", "Mumbai", "Retail"},
            {4, "Ananya Gupta", "Lucknow", "Business"},
            {5, "Kabir Khan", "Pune", "Retail"},
            {6, "Isha Patel", "Ahmedabad", "Business"}
        };

        products = {
            {1, "Laptop Pro", "Computers", 7500000, 12},
            {2, "Wireless Mouse", "Accessories", 150000, 80},
            {3, "Mechanical Keyboard", "Accessories", 450000, 35},
            {4, "Monitor 27", "Displays", 2200000, 20},
            {5, "USB-C Hub", "Accessories", 350000, 50},
            {6, "Office Chair", "Furniture", 1800000, 8}
        };

        sales = {
            {1, 1, 1, "2026-01-05", 1, 7500000, 500000, "Neha"},
            {2, 1, 2, "2026-01-06", 2, 150000, nullopt, "Neha"},
            {3, 2, 3, "2026-01-07", 3, 450000, 100000, "Rahul"},
            {4, 2, 4, "2026-01-08", 2, 2200000, 200000, "Rahul"},
            {5, 3, 2, "2026-01-10", 1, 150000, nullopt, "Priya"},
            {6, 3, 5, "2026-01-12", 4, 350000, 50000, "Priya"},
            {7, 4, 1, "2026-02-01", 2, 7500000, 1000000, "Neha"},
            {8, 4, 6, "2026-02-03", 1, 1800000, nullopt, "Neha"},
            {9, 5, 3, "2026-02-05", 1, 450000, nullopt, "Rahul"},
            {10, 5, 2, "2026-02-06", 5, 150000, 25000, "Rahul"},
            {11, 6, 4, "2026-02-09", 3, 2200000, 300000, "Priya"},
            {12, 6, 5, "2026-02-11", 2, 350000, nullopt, "Priya"},
            {13, 1, 2, "2026-03-02", 3, 150000, nullopt, "Neha"},
            {14, 2, 5, "2026-03-04", 2, 350000, 50000, "Rahul"},
            {15, 3, 4, "2026-03-06", 1, 2200000, nullopt, "Priya"}
        };
    }

    const vector<Customer>& getCustomers() const {
        return customers;
    }

    const vector<Product>& getProducts() const {
        return products;
    }

    const vector<Sale>& getSales() const {
        return sales;
    }
};


// -----------------------------------------------------------------------------
// 5. Validation
// -----------------------------------------------------------------------------

void validateSale(const Sale& sale) {
    if (sale.quantity <= 0) {
        throw invalid_argument(
            "Sale quantity must be greater than zero."
        );
    }

    if (sale.unitPricePaise < 0) {
        throw invalid_argument(
            "Sale unit price cannot be negative."
        );
    }

    if (sale.discountPaise.has_value() &&
        sale.discountPaise.value() < 0) {
        throw invalid_argument(
            "Discount cannot be negative."
        );
    }

    if (sale.discountPaise.has_value() &&
        sale.discountPaise.value() >
            sale.unitPricePaise * sale.quantity) {
        throw invalid_argument(
            "Discount cannot exceed gross line value."
        );
    }
}

void validateRepository(const SalesRepository& repository) {
    for (const Sale& sale : repository.getSales()) {
        validateSale(sale);
    }
}


// -----------------------------------------------------------------------------
// 6. Basic aggregate demonstration
// -----------------------------------------------------------------------------

void demonstrateBasicAggregates(
    const vector<Sale>& sales
) {
    printTitle("1. COUNT, SUM, AVG, MIN and MAX");

    const long long count = static_cast<long long>(sales.size());

    const long long units = sumValues(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    const auto average = averageValue(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    const auto minimum = minimumValue(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    const auto maximum = maximumValue(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    cout << "COUNT(*): " << count << '\n';
    cout << "SUM(quantity): " << units << '\n';
    cout << "AVG(quantity): "
         << (average.has_value()
             ? to_string(average.value())
             : "NULL")
         << '\n';
    cout << "MIN(quantity): "
         << (minimum.has_value()
             ? to_string(minimum.value())
             : "NULL")
         << '\n';
    cout << "MAX(quantity): "
         << (maximum.has_value()
             ? to_string(maximum.value())
             : "NULL")
         << '\n';
}


// -----------------------------------------------------------------------------
// 7. NULL behavior demonstration
// -----------------------------------------------------------------------------

void demonstrateNullBehavior(
    const vector<Sale>& sales
) {
    printTitle("2. COUNT(column) and NULL");

    long long rowCount = static_cast<long long>(sales.size());

    long long nonNullDiscounts = countValues(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.discountPaise;
        }
    );

    long long totalDiscount = sumValues(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.discountPaise;
        }
    );

    const auto averageDiscount = averageValue(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.discountPaise;
        }
    );

    cout << "COUNT(*): " << rowCount << '\n';
    cout << "COUNT(discount): " << nonNullDiscounts << '\n';
    cout << "SUM(discount): " << money(totalDiscount) << '\n';

    if (averageDiscount.has_value()) {
        cout << "AVG(discount): "
             << money(
                    static_cast<long long>(
                        averageDiscount.value()
                    )
                )
             << '\n';
    } else {
        cout << "AVG(discount): NULL\n";
    }
}


// -----------------------------------------------------------------------------
// 8. Salesperson GROUP BY
// -----------------------------------------------------------------------------

struct GroupMetrics {
    long long count = 0;
    long long units = 0;
    long long revenuePaise = 0;
};

map<string, GroupMetrics> groupBySalesperson(
    const vector<Sale>& sales
) {
    map<string, GroupMetrics> groups;

    for (const Sale& sale : sales) {
        auto& group = groups[sale.salesperson];

        group.count += 1;
        group.units += sale.quantity;
        group.revenuePaise +=
            sale.quantity * sale.unitPricePaise;
    }

    return groups;
}

void printSalespersonGroups(
    const map<string, GroupMetrics>& groups
) {
    printTitle("3. GROUP BY Salesperson");

    cout << left
         << setw(15) << "Salesperson"
         << setw(12) << "COUNT"
         << setw(12) << "SUM Units"
         << setw(20) << "Revenue"
         << '\n';

    cout << string(59, '-') << '\n';

    for (const auto& [salesperson, metrics] : groups) {
        cout << left
             << setw(15) << salesperson
             << setw(12) << metrics.count
             << setw(12) << metrics.units
             << setw(20) << money(metrics.revenuePaise)
             << '\n';
    }
}


// -----------------------------------------------------------------------------
// 9. HAVING-style filtering
// -----------------------------------------------------------------------------

void demonstrateHaving(
    const map<string, GroupMetrics>& groups
) {
    printTitle("4. HAVING-Style Filtering");

    cout << "Salesperson groups with revenue above Rs 50,000:\n\n";

    for (const auto& [salesperson, metrics] : groups) {
        if (metrics.revenuePaise > 5000000) {
            cout << salesperson
                 << " -> "
                 << money(metrics.revenuePaise)
                 << '\n';
        }
    }

    cout << "\nThe filter is applied to already-aggregated groups.\n";
}


// -----------------------------------------------------------------------------
// 10. Conditional aggregation
// -----------------------------------------------------------------------------

void demonstrateConditionalAggregation(
    const vector<Sale>& sales
) {
    printTitle("5. Conditional Aggregation");

    long long highQuantityLines = 0;
    long long highQuantityUnits = 0;
    long long premiumRevenue = 0;
    long long discountedLines = 0;

    for (const Sale& sale : sales) {
        if (sale.quantity >= 3) {
            ++highQuantityLines;
            highQuantityUnits += sale.quantity;
        }

        if (sale.unitPricePaise >= 2000000) {
            premiumRevenue +=
                sale.quantity * sale.unitPricePaise;
        }

        if (sale.discountPaise.has_value()) {
            ++discountedLines;
        }
    }

    cout << "High-quantity lines: "
         << highQuantityLines << '\n';

    cout << "High-quantity units: "
         << highQuantityUnits << '\n';

    cout << "Premium revenue: "
         << money(premiumRevenue) << '\n';

    cout << "Discounted lines: "
         << discountedLines << '\n';
}


// -----------------------------------------------------------------------------
// 11. DISTINCT
// -----------------------------------------------------------------------------

void demonstrateDistinct(
    const vector<Sale>& sales
) {
    printTitle("6. DISTINCT Aggregation");

    set<int> customers;
    set<int> products;
    set<long long> prices;

    for (const Sale& sale : sales) {
        customers.insert(sale.customerId);
        products.insert(sale.productId);
        prices.insert(sale.unitPricePaise);
    }

    cout << "COUNT(DISTINCT customer_id): "
         << customers.size()
         << '\n';

    cout << "COUNT(DISTINCT product_id): "
         << products.size()
         << '\n';

    cout << "COUNT(DISTINCT unit_price): "
         << prices.size()
         << '\n';

    long long distinctPriceSum = 0;

    for (long long price : prices) {
        distinctPriceSum += price;
    }

    cout << "SUM(DISTINCT unit_price): "
         << money(distinctPriceSum)
         << '\n';
}


// -----------------------------------------------------------------------------
// 12. Indexed joins
// -----------------------------------------------------------------------------

unordered_map<int, Product> buildProductIndex(
    const vector<Product>& products
) {
    unordered_map<int, Product> index;

    for (const Product& product : products) {
        index.emplace(product.id, product);
    }

    return index;
}

unordered_map<int, Customer> buildCustomerIndex(
    const vector<Customer>& customers
) {
    unordered_map<int, Customer> index;

    for (const Customer& customer : customers) {
        index.emplace(customer.id, customer);
    }

    return index;
}


// -----------------------------------------------------------------------------
// 13. Category aggregation after a join
// -----------------------------------------------------------------------------

void demonstrateCategoryAggregation(
    const vector<Sale>& sales,
    const vector<Product>& products
) {
    printTitle("7. JOIN + GROUP BY Product Category");

    const auto productIndex = buildProductIndex(products);

    map<string, GroupMetrics> categories;

    for (const Sale& sale : sales) {
        auto iterator = productIndex.find(sale.productId);

        if (iterator == productIndex.end()) {
            throw runtime_error(
                "Sale references a product that does not exist."
            );
        }

        const string& category = iterator->second.category;
        auto& metrics = categories[category];

        metrics.count += 1;
        metrics.units += sale.quantity;
        metrics.revenuePaise +=
            sale.quantity * sale.unitPricePaise;
    }

    for (const auto& [category, metrics] : categories) {
        cout << category
             << " | lines=" << metrics.count
             << " | units=" << metrics.units
             << " | revenue=" << money(metrics.revenuePaise)
             << '\n';
    }
}


// -----------------------------------------------------------------------------
// 14. Customer analytics with LEFT JOIN semantics
// -----------------------------------------------------------------------------

void demonstrateCustomerAnalytics(
    const vector<Customer>& customers,
    const vector<Sale>& sales
) {
    printTitle("8. Customer Analytics");

    map<int, GroupMetrics> customerMetrics;

    for (const Sale& sale : sales) {
        auto& metrics = customerMetrics[sale.customerId];

        metrics.count += 1;
        metrics.units += sale.quantity;
        metrics.revenuePaise +=
            sale.quantity * sale.unitPricePaise;
    }

    for (const Customer& customer : customers) {
        const auto iterator =
            customerMetrics.find(customer.id);

        GroupMetrics metrics;

        if (iterator != customerMetrics.end()) {
            metrics = iterator->second;
        }

        cout << customer.name
             << " | city=" << customer.city
             << " | type=" << customer.type
             << " | lines=" << metrics.count
             << " | units=" << metrics.units
             << " | spend=" << money(metrics.revenuePaise)
             << '\n';
    }
}


// -----------------------------------------------------------------------------
// 15. Product analytics
// -----------------------------------------------------------------------------

void demonstrateProductAnalytics(
    const vector<Product>& products,
    const vector<Sale>& sales
) {
    printTitle("9. Product Analytics");

    map<int, GroupMetrics> productMetrics;

    for (const Sale& sale : sales) {
        auto& metrics = productMetrics[sale.productId];

        metrics.count += 1;
        metrics.units += sale.quantity;
        metrics.revenuePaise +=
            sale.quantity * sale.unitPricePaise;
    }

    for (const Product& product : products) {
        GroupMetrics metrics;

        auto iterator = productMetrics.find(product.id);

        if (iterator != productMetrics.end()) {
            metrics = iterator->second;
        }

        cout << product.name
             << " | category=" << product.category
             << " | stock=" << product.stock
             << " | sold=" << metrics.units
             << " | revenue=" << money(metrics.revenuePaise)
             << '\n';
    }
}


// -----------------------------------------------------------------------------
// 16. Monthly aggregation
// -----------------------------------------------------------------------------

void demonstrateMonthlyAggregation(
    const vector<Sale>& sales
) {
    printTitle("10. Monthly Aggregation");

    map<string, GroupMetrics> months;

    for (const Sale& sale : sales) {
        const string month = sale.date.substr(0, 7);

        auto& metrics = months[month];

        metrics.count += 1;
        metrics.units += sale.quantity;
        metrics.revenuePaise +=
            sale.quantity * sale.unitPricePaise;
    }

    for (const auto& [month, metrics] : months) {
        cout << month
             << " | lines=" << metrics.count
             << " | units=" << metrics.units
             << " | revenue="
             << money(metrics.revenuePaise)
             << '\n';
    }
}


// -----------------------------------------------------------------------------
// 17. Running aggregate
// -----------------------------------------------------------------------------

void demonstrateRunningRevenue(
    vector<Sale> sales
) {
    printTitle("11. Running Revenue");

    sort(
        sales.begin(),
        sales.end(),
        [](const Sale& first, const Sale& second) {
            if (first.date != second.date) {
                return first.date < second.date;
            }

            return first.id < second.id;
        }
    );

    long long cumulativeRevenue = 0;

    for (const Sale& sale : sales) {
        const long long lineRevenue =
            sale.quantity * sale.unitPricePaise;

        cumulativeRevenue += lineRevenue;

        cout << sale.date
             << " | sale=" << sale.id
             << " | line="
             << money(lineRevenue)
             << " | cumulative="
             << money(cumulativeRevenue)
             << '\n';
    }
}


// -----------------------------------------------------------------------------
// 18. Salesperson ranking
// -----------------------------------------------------------------------------

void demonstrateRanking(
    const map<string, GroupMetrics>& groups
) {
    printTitle("12. Ranking Aggregated Groups");

    vector<pair<string, GroupMetrics>> ranking(
        groups.begin(),
        groups.end()
    );

    sort(
        ranking.begin(),
        ranking.end(),
        [](const auto& first, const auto& second) {
            return first.second.revenuePaise >
                   second.second.revenuePaise;
        }
    );

    int rank = 1;

    for (const auto& [salesperson, metrics] : ranking) {
        cout << rank
             << ". "
             << salesperson
             << " -> "
             << money(metrics.revenuePaise)
             << '\n';

        ++rank;
    }
}


// -----------------------------------------------------------------------------
// 19. One-pass executive aggregation
// -----------------------------------------------------------------------------

struct ExecutiveReport {
    long long transactionLines = 0;
    long long activeCustomers = 0;
    long long uniqueProducts = 0;
    long long unitsSold = 0;
    long long grossRevenuePaise = 0;
    long long discountsPaise = 0;

    optional<long long> minimumQuantity;
    optional<long long> maximumQuantity;
    double averageQuantity = 0.0;
};

ExecutiveReport buildExecutiveReport(
    const vector<Sale>& sales
) {
    ExecutiveReport report;

    set<int> customerIds;
    set<int> productIds;

    long long quantityTotal = 0;

    for (const Sale& sale : sales) {
        ++report.transactionLines;

        customerIds.insert(sale.customerId);
        productIds.insert(sale.productId);

        report.unitsSold += sale.quantity;
        quantityTotal += sale.quantity;

        const long long lineRevenue =
            sale.quantity * sale.unitPricePaise;

        report.grossRevenuePaise += lineRevenue;

        if (sale.discountPaise.has_value()) {
            report.discountsPaise +=
                sale.discountPaise.value();
        }

        if (!report.minimumQuantity.has_value() ||
            sale.quantity < report.minimumQuantity.value()) {
            report.minimumQuantity = sale.quantity;
        }

        if (!report.maximumQuantity.has_value() ||
            sale.quantity > report.maximumQuantity.value()) {
            report.maximumQuantity = sale.quantity;
        }
    }

    report.activeCustomers =
        static_cast<long long>(customerIds.size());

    report.uniqueProducts =
        static_cast<long long>(productIds.size());

    if (report.transactionLines > 0) {
        report.averageQuantity =
            static_cast<double>(quantityTotal) /
            static_cast<double>(report.transactionLines);
    }

    return report;
}

void printExecutiveReport(
    const ExecutiveReport& report
) {
    printTitle("13. Executive Sales Dashboard");

    cout << "Transaction lines: "
         << report.transactionLines << '\n';

    cout << "Active customers: "
         << report.activeCustomers << '\n';

    cout << "Products sold: "
         << report.uniqueProducts << '\n';

    cout << "Units sold: "
         << report.unitsSold << '\n';

    cout << "Average units per line: "
         << fixed << setprecision(2)
         << report.averageQuantity
         << '\n';

    cout << "Minimum units per line: "
         << (report.minimumQuantity.has_value()
             ? to_string(report.minimumQuantity.value())
             : "NULL")
         << '\n';

    cout << "Maximum units per line: "
         << (report.maximumQuantity.has_value()
             ? to_string(report.maximumQuantity.value())
             : "NULL")
         << '\n';

    cout << "Gross revenue: "
         << money(report.grossRevenuePaise)
         << '\n';

    cout << "Discounts: "
         << money(report.discountsPaise)
         << '\n';

    cout << "Net revenue: "
         << money(
                report.grossRevenuePaise -
                report.discountsPaise
            )
         << '\n';
}


// -----------------------------------------------------------------------------
// 20. Date filtering
// -----------------------------------------------------------------------------

vector<Sale> filterByDateRange(
    const vector<Sale>& sales,
    const string& startDate,
    const string& endDate
) {
    if (startDate > endDate) {
        throw invalid_argument(
            "Start date cannot be after end date."
        );
    }

    vector<Sale> result;

    for (const Sale& sale : sales) {
        if (sale.date >= startDate &&
            sale.date <= endDate) {
            result.push_back(sale);
        }
    }

    return result;
}


// -----------------------------------------------------------------------------
// 21. Empty input behavior
// -----------------------------------------------------------------------------

void demonstrateEmptyInput() {
    printTitle("14. Empty Aggregate Input");

    const vector<Sale> emptySales;

    const auto minimum = minimumValue(
        emptySales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    const auto maximum = maximumValue(
        emptySales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    const auto average = averageValue(
        emptySales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    cout << "COUNT(*): " << emptySales.size() << '\n';
    cout << "AVG: "
         << (average.has_value() ? "value" : "NULL")
         << '\n';
    cout << "MIN: "
         << (minimum.has_value() ? "value" : "NULL")
         << '\n';
    cout << "MAX: "
         << (maximum.has_value() ? "value" : "NULL")
         << '\n';

    cout << "\nAn empty aggregate must be handled deliberately.\n";
}


// -----------------------------------------------------------------------------
// 22. Duplicate join demonstration
// -----------------------------------------------------------------------------

struct CustomerTag {
    int customerId;
    string tag;
};

void demonstrateDuplicateJoinProblem(
    const vector<Sale>& sales
) {
    printTitle("15. Duplicate Rows Caused by One-to-Many Joins");

    vector<CustomerTag> tags = {
        {1, "VIP"},
        {1, "Technology"},
        {2, "Enterprise"}
    };

    long long originalRevenue = 0;
    long long joinedRevenue = 0;

    for (const Sale& sale : sales) {
        if (sale.customerId == 1) {
            originalRevenue +=
                sale.quantity * sale.unitPricePaise;
        }
    }

    for (const Sale& sale : sales) {
        if (sale.customerId != 1) {
            continue;
        }

        int matchingTags = 0;

        for (const CustomerTag& tag : tags) {
            if (tag.customerId == sale.customerId) {
                ++matchingTags;
            }
        }

        joinedRevenue +=
            sale.quantity *
            sale.unitPricePaise *
            matchingTags;
    }

    cout << "Original customer revenue: "
         << money(originalRevenue)
         << '\n';

    cout << "Revenue after multiplied join: "
         << money(joinedRevenue)
         << '\n';

    cout << "\nThe second value is inflated because customer 1 has two tags.\n";
}


// -----------------------------------------------------------------------------
// 23. Performance measurement
// -----------------------------------------------------------------------------

void demonstratePerformance(
    const vector<Sale>& sales
) {
    printTitle("16. One-Pass Performance Model");

    const auto start =
        chrono::high_resolution_clock::now();

    volatile long long total = 0;

    for (const Sale& sale : sales) {
        total +=
            static_cast<long long>(sale.quantity) *
            sale.unitPricePaise;
    }

    const auto end =
        chrono::high_resolution_clock::now();

    const auto duration =
        chrono::duration_cast<
            chrono::nanoseconds
        >(end - start);

    cout << "Computed revenue: "
         << money(total)
         << '\n';

    cout << "Measured elapsed time for this small dataset: "
         << duration.count()
         << " ns\n";

    cout << R"(
For n rows, a simple one-pass SUM is O(n) time and O(1) additional space.

Real database engines may use hashing, sorting, indexes, parallel execution,
partitioning, vectorized execution, caching, or other implementation
strategies. The SQL expression does not dictate one physical algorithm.
)";
}


// -----------------------------------------------------------------------------
// 24. Financial representation
// -----------------------------------------------------------------------------

void demonstrateFinancialRepresentation() {
    printTitle("17. Exact Monetary Representation");

    // Monetary values are represented in integer paise rather than floating
    // point rupees. This avoids many binary floating-point representation
    // problems when the application requires exact minor-unit arithmetic.

    const vector<long long> valuesPaise = {
        1010,
        2020,
        3030
    };

    long long total = 0;

    for (long long value : valuesPaise) {
        total += value;
    }

    cout << "Total: " << money(total) << '\n';

    const double average =
        static_cast<double>(total) /
        static_cast<double>(valuesPaise.size());

    cout << "Average in paise: "
         << fixed << setprecision(2)
         << average
         << '\n';
}


// -----------------------------------------------------------------------------
// 25. Verification tests
// -----------------------------------------------------------------------------

void runTests(
    const vector<Sale>& sales
) {
    printTitle("18. Verification Tests");

    const long long count =
        static_cast<long long>(sales.size());

    assert(count == 15);

    const long long units = sumValues(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    assert(units == 34);

    const auto minimum = minimumValue(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    assert(minimum.has_value());
    assert(minimum.value() == 1);

    const auto maximum = maximumValue(
        sales,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    assert(maximum.has_value());
    assert(maximum.value() == 5);

    const vector<Sale> empty;

    const auto emptyAverage = averageValue(
        empty,
        [](const Sale& sale) -> optional<long long> {
            return sale.quantity;
        }
    );

    assert(!emptyAverage.has_value());

    cout << "All aggregate tests passed.\n";
}


// -----------------------------------------------------------------------------
// 26. Main application
// -----------------------------------------------------------------------------

int main() {
    try {
        printTitle("Aggregate Functions Technical Case Study");

        SalesRepository repository;

        validateRepository(repository);

        const auto& customers =
            repository.getCustomers();

        const auto& products =
            repository.getProducts();

        const auto& sales =
            repository.getSales();

        cout << "Customers: "
             << customers.size()
             << '\n';

        cout << "Products: "
             << products.size()
             << '\n';

        cout << "Sales lines: "
             << sales.size()
             << '\n';

        demonstrateBasicAggregates(sales);

        demonstrateNullBehavior(sales);

        const auto salespersonGroups =
            groupBySalesperson(sales);

        printSalespersonGroups(
            salespersonGroups
        );

        demonstrateHaving(
            salespersonGroups
        );

        demonstrateConditionalAggregation(
            sales
        );

        demonstrateDistinct(
            sales
        );

        demonstrateCategoryAggregation(
            sales,
            products
        );

        demonstrateCustomerAnalytics(
            customers,
            sales
        );

        demonstrateProductAnalytics(
            products,
            sales
        );

        demonstrateMonthlyAggregation(
            sales
        );

        demonstrateRunningRevenue(
            sales
        );

        demonstrateRanking(
            salespersonGroups
        );

        const ExecutiveReport report =
            buildExecutiveReport(sales);

        printExecutiveReport(report);

        demonstrateEmptyInput();

        demonstrateDuplicateJoinProblem(
            sales
        );

        demonstratePerformance(
            sales
        );

        demonstrateFinancialRepresentation();

        const vector<Sale> firstTwoMonths =
            filterByDateRange(
                sales,
                "2026-01-01",
                "2026-02-28"
            );

        printTitle("19. Date-Range Aggregate");

        const ExecutiveReport dateReport =
            buildExecutiveReport(firstTwoMonths);

        cout << "Date range: 2026-01-01 to 2026-02-28\n";
        cout << "Lines: "
             << dateReport.transactionLines
             << '\n';
        cout << "Units: "
             << dateReport.unitsSold
             << '\n';
        cout << "Revenue: "
             << money(dateReport.grossRevenuePaise)
             << '\n';

        runTests(sales);

        printTitle("20. Core Concepts Demonstrated");

        const vector<string> concepts = {
            "COUNT(*)",
            "COUNT(column)",
            "SUM(column)",
            "AVG(column)",
            "MIN(column)",
            "MAX(column)",
            "NULL handling",
            "DISTINCT aggregation",
            "GROUP BY",
            "HAVING",
            "Conditional aggregation",
            "JOIN before aggregation",
            "LEFT JOIN semantics",
            "Date aggregation",
            "Running aggregation",
            "Ranking",
            "One-pass aggregation",
            "Financial precision",
            "Validation",
            "Join cardinality",
            "Complexity analysis"
        };

        printVector(concepts);

        cout << "\nCase study completed successfully.\n";
    }
    catch (const exception& error) {
        cerr << "Application error: "
             << error.what()
             << '\n';

        return 1;
    }

    return 0;
}
