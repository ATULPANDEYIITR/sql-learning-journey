/*
 * Conditional Logic Case Study
 *
 * Modern C++17
 *
 * Scenario:
 * A commerce platform must classify orders, calculate discounts, determine
 * customer segments, prioritize payment states, and produce operational
 * reports. The design deliberately mirrors SQL CASE / WHEN / THEN / ELSE
 * semantics while using native C++ structures.
 *
 * Compile:
 *   g++ -std=c++17 -O2 conditional_logic_case_study.cpp -o conditional_logic_case_study
 *
 * Run:
 *   ./conditional_logic_case_study
 *
 * The implementation demonstrates:
 * - simple CASE-like value matching
 * - searched CASE-like predicate matching
 * - first-match rule precedence
 * - explicit default behavior
 * - nullable state representation
 * - validation
 * - rule engines
 * - custom sorting
 * - aggregation
 * - boundary testing
 * - complexity considerations
 */

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

struct Order {
    int id;
    int customerId;
    double amount;
    std::optional<std::string> paymentStatus;
};

struct Customer {
    int id;
    std::string name;
    std::string country;
    int loyaltyPoints;
};

struct DiscountRule {
    std::string name;
    double minimumAmount;
    double discountRate;
};

struct CustomerReport {
    std::string name;
    double totalSpend;
    double paidSpend;
    std::size_t orderCount;
    std::string segment;
    std::string paymentProfile;
};

void printTitle(const std::string& title) {
    std::cout << "\n" << std::string(78, '=')
              << "\n" << title
              << "\n" << std::string(78, '=')
              << "\n";
}

std::string paymentStatusText(const std::optional<std::string>& status) {
    return status.value_or("NULL");
}

/*
 * Simple CASE analogue.
 *
 * SQL:
 *   CASE country
 *       WHEN 'India' THEN 'Domestic'
 *       WHEN 'USA' THEN 'North America'
 *       ELSE 'Other'
 *   END
 *
 * C++ switch cannot directly switch on std::string, so an if/else chain
 * is used for the string value.
 */
std::string classifyCountry(const std::string& country) {
    if (country == "India") {
        return "Domestic";
    }

    if (country == "USA") {
        return "North America";
    }

    if (country == "UK") {
        return "United Kingdom";
    }

    return "Other";
}

/*
 * Searched CASE analogue.
 *
 * SQL:
 *   CASE
 *       WHEN amount >= 3000 THEN 'Very large'
 *       WHEN amount >= 1000 THEN 'Large'
 *       WHEN amount >= 100 THEN 'Medium'
 *       ELSE 'Small'
 *   END
 *
 * Conditions are evaluated in order and the first matching condition wins.
 */
std::string classifyOrderSize(double amount) {
    if (amount >= 3000.0) {
        return "Very large";
    }

    if (amount >= 1000.0) {
        return "Large";
    }

    if (amount >= 100.0) {
        return "Medium";
    }

    return "Small";
}

std::string classifyLoyalty(int points) {
    if (points < 0) {
        throw std::invalid_argument("Loyalty points cannot be negative.");
    }

    if (points >= 500) {
        return "Platinum";
    }

    if (points >= 200) {
        return "Gold";
    }

    if (points >= 100) {
        return "Silver";
    }

    return "Standard";
}

std::string classifyPayment(const Order& order) {
    if (!order.paymentStatus.has_value()) {
        return "Status missing";
    }

    const std::string& status = *order.paymentStatus;

    if (status == "PAID") {
        return "Completed";
    }

    if (status == "PENDING") {
        return "Awaiting payment";
    }

    if (status == "FAILED") {
        return "Failed";
    }

    return "Unknown state";
}

void validateOrder(const Order& order) {
    if (order.id <= 0) {
        throw std::invalid_argument("Order id must be positive.");
    }

    if (order.customerId <= 0) {
        throw std::invalid_argument("Customer id must be positive.");
    }

    if (!std::isfinite(order.amount) || order.amount < 0.0) {
        throw std::invalid_argument(
            "Order amount must be finite and non-negative."
        );
    }

    if (order.paymentStatus.has_value()) {
        const std::string& status = *order.paymentStatus;

        if (status != "PAID" &&
            status != "PENDING" &&
            status != "FAILED") {
            throw std::invalid_argument(
                "Payment status must be PAID, PENDING, or FAILED."
            );
        }
    }
}

void printOrders(const std::vector<Order>& orders) {
    std::cout << std::left
              << std::setw(10) << "Order"
              << std::setw(14) << "Amount"
              << std::setw(18) << "Size"
              << std::setw(18) << "Payment"
              << "State\n";

    std::cout << std::string(78, '-') << "\n";

    for (const auto& order : orders) {
        std::cout << std::left
                  << std::setw(10) << order.id
                  << std::setw(14) << std::fixed << std::setprecision(2)
                  << order.amount
                  << std::setw(18) << classifyOrderSize(order.amount)
                  << std::setw(18) << paymentStatusText(order.paymentStatus)
                  << classifyPayment(order)
                  << "\n";
    }
}

std::pair<std::string, double> calculateDiscount(
    double amount,
    const std::vector<DiscountRule>& rules
) {
    /*
     * The vector is ordered from the most restrictive rule to the broadest.
     * This reproduces SQL's first-matching WHEN behavior.
     *
     * Complexity: O(R), where R is the number of rules.
     */
    for (const auto& rule : rules) {
        if (amount >= rule.minimumAmount) {
            const double discount = amount * rule.discountRate;
            return {
                rule.name,
                std::round(discount * 100.0) / 100.0
            };
        }
    }

    return {"None", 0.0};
}

std::string determineCustomerSegment(
    double totalSpend,
    int loyaltyPoints
) {
    /*
     * Compound conditions correspond to AND and OR combinations inside
     * searched CASE WHEN predicates.
     */
    if (totalSpend >= 5000.0 && loyaltyPoints >= 500) {
        return "Strategic customer";
    }

    if (totalSpend >= 2000.0 || loyaltyPoints >= 300) {
        return "High-value customer";
    }

    if (totalSpend >= 500.0 || loyaltyPoints >= 100) {
        return "Growing customer";
    }

    return "Standard customer";
}

std::string determinePaymentProfile(
    const std::vector<Order>& customerOrders,
    double paidSpend,
    double totalSpend
) {
    if (customerOrders.empty()) {
        return "No orders";
    }

    if (std::abs(paidSpend - totalSpend) < 1e-9) {
        return "All orders paid";
    }

    if (paidSpend > 0.0) {
        return "Mixed payment state";
    }

    return "No paid orders";
}

std::vector<CustomerReport> buildCustomerReports(
    const std::vector<Customer>& customers,
    const std::vector<Order>& orders
) {
    std::vector<CustomerReport> reports;

    for (const auto& customer : customers) {
        double totalSpend = 0.0;
        double paidSpend = 0.0;
        std::vector<Order> customerOrders;

        for (const auto& order : orders) {
            if (order.customerId != customer.id) {
                continue;
            }

            customerOrders.push_back(order);
            totalSpend += order.amount;

            if (order.paymentStatus.has_value() &&
                *order.paymentStatus == "PAID") {
                paidSpend += order.amount;
            }
        }

        reports.push_back({
            customer.name,
            totalSpend,
            paidSpend,
            customerOrders.size(),
            determineCustomerSegment(
                totalSpend,
                customer.loyaltyPoints
            ),
            determinePaymentProfile(
                customerOrders,
                paidSpend,
                totalSpend
            )
        });
    }

    return reports;
}

void printCustomerReports(
    const std::vector<CustomerReport>& reports
) {
    std::cout << std::left
              << std::setw(12) << "Customer"
              << std::setw(14) << "Total Spend"
              << std::setw(14) << "Paid Spend"
              << std::setw(10) << "Orders"
              << std::setw(24) << "Segment"
              << "Payment Profile\n";

    std::cout << std::string(110, '-') << "\n";

    for (const auto& report : reports) {
        std::cout << std::left
                  << std::setw(12) << report.name
                  << std::setw(14) << std::fixed << std::setprecision(2)
                  << report.totalSpend
                  << std::setw(14) << report.paidSpend
                  << std::setw(10) << report.orderCount
                  << std::setw(24) << report.segment
                  << report.paymentProfile
                  << "\n";
    }
}

void conditionalAggregation(const std::vector<Order>& orders) {
    printTitle("Conditional aggregation");

    std::size_t paidCount = 0;
    std::size_t pendingCount = 0;
    std::size_t failedCount = 0;
    double paidAmount = 0.0;

    for (const auto& order : orders) {
        /*
         * These if statements perform the same conceptual task as:
         *
         * SUM(CASE WHEN payment_status = 'PAID' THEN 1 ELSE 0 END)
         *
         * and
         *
         * SUM(CASE WHEN payment_status = 'PAID' THEN amount ELSE 0 END)
         */
        if (order.paymentStatus.has_value()) {
            if (*order.paymentStatus == "PAID") {
                ++paidCount;
                paidAmount += order.amount;
            } else if (*order.paymentStatus == "PENDING") {
                ++pendingCount;
            } else if (*order.paymentStatus == "FAILED") {
                ++failedCount;
            }
        }
    }

    const std::size_t total = orders.size();

    const double paidPercentage =
        total == 0
            ? 0.0
            : 100.0 * static_cast<double>(paidCount) /
              static_cast<double>(total);

    std::cout << "Total orders: " << total << "\n";
    std::cout << "Paid orders: " << paidCount << "\n";
    std::cout << "Pending orders: " << pendingCount << "\n";
    std::cout << "Failed orders: " << failedCount << "\n";
    std::cout << "Paid amount: " << std::fixed << std::setprecision(2)
              << paidAmount << "\n";
    std::cout << "Paid percentage: " << paidPercentage << "%\n";
}

void conditionalSorting(std::vector<Order> orders) {
    printTitle("Conditional sorting by payment priority");

    /*
     * SQL:
     *
     * ORDER BY CASE payment_status
     *     WHEN 'PENDING' THEN 1
     *     WHEN 'FAILED' THEN 2
     *     WHEN 'PAID' THEN 3
     *     ELSE 4
     * END
     *
     * C++ implements the same idea with a priority function.
     */
    const auto priority = [](const Order& order) {
        if (!order.paymentStatus.has_value()) {
            return 4;
        }

        if (*order.paymentStatus == "PENDING") {
            return 1;
        }

        if (*order.paymentStatus == "FAILED") {
            return 2;
        }

        if (*order.paymentStatus == "PAID") {
            return 3;
        }

        return 4;
    };

    std::stable_sort(
        orders.begin(),
        orders.end(),
        [&](const Order& left, const Order& right) {
            const int leftPriority = priority(left);
            const int rightPriority = priority(right);

            if (leftPriority != rightPriority) {
                return leftPriority < rightPriority;
            }

            return left.amount > right.amount;
        }
    );

    printOrders(orders);
}

void boundaryTests() {
    printTitle("Boundary tests");

    const std::vector<double> values = {
        99.99,
        100.00,
        100.01,
        999.99,
        1000.00,
        1000.01,
        2999.99,
        3000.00
    };

    for (double amount : values) {
        std::cout << std::fixed << std::setprecision(2)
                  << amount << " -> "
                  << classifyOrderSize(amount) << "\n";
    }
}

void demonstrateRulePrecedence() {
    printTitle("Rule precedence");

    /*
     * Incorrect ordering:
     *
     * WHEN amount >= 100 THEN 'Large'
     * WHEN amount >= 1000 THEN 'Very large'
     *
     * The second rule is unreachable for values >= 1000 because the first
     * condition already matches.
     */
    const auto incorrect = [](double amount) {
        if (amount >= 100.0) {
            return std::string("Large");
        }

        if (amount >= 1000.0) {
            return std::string("Very large");
        }

        return std::string("Small");
    };

    const auto correct = [](double amount) {
        if (amount >= 1000.0) {
            return std::string("Very large");
        }

        if (amount >= 100.0) {
            return std::string("Large");
        }

        return std::string("Small");
    };

    for (double amount : {99.99, 100.0, 999.99, 1000.0, 3000.0}) {
        std::cout << std::fixed << std::setprecision(2)
                  << amount
                  << " | incorrect=" << incorrect(amount)
                  << " | correct=" << correct(amount)
                  << "\n";
    }
}

void demonstrateValidation() {
    printTitle("Validation and failure conditions");

    const std::vector<Order> invalidOrders = {
        {-1, 1, 100.0, std::string("PAID")},
        {2, -5, 100.0, std::string("PAID")},
        {3, 1, -50.0, std::string("PAID")},
        {4, 1, 100.0, std::string("UNKNOWN")}
    };

    for (const auto& order : invalidOrders) {
        try {
            validateOrder(order);
            std::cout << "Unexpectedly accepted order "
                      << order.id << "\n";
        } catch (const std::exception& error) {
            std::cout << "Rejected order " << order.id
                      << ": " << error.what() << "\n";
        }
    }
}

void complexityDiscussion() {
    printTitle("Implementation and complexity considerations");

    std::cout
        << "Direct if/else classification with a fixed number of rules: O(1)\n"
        << "Rule-vector evaluation with R rules: O(R) per input\n"
        << "Customer report using C customers and O orders: O(C * O)\n"
        << "Sorting O orders: O(O log O)\n"
        << "\n"
        << "The customer report intentionally uses a simple implementation for\n"
        << "clarity. A production system could pre-index orders by customer id,\n"
        << "reducing repeated scans and improving scalability.\n";
}

int main() {
    try {
        printTitle("Conditional Logic: CASE, WHEN, THEN, ELSE");

        const std::vector<Customer> customers = {
            {1, "Asha", "India", 120},
            {2, "Ravi", "India", 40},
            {3, "Maya", "USA", 800},
            {4, "Noah", "UK", 15},
            {5, "Iris", "India", 300}
        };

        const std::vector<Order> orders = {
            {101, 1, 1250.0, std::string("PAID")},
            {102, 1, 450.0, std::string("PAID")},
            {103, 2, 90.0, std::string("PENDING")},
            {104, 2, 700.0, std::string("PAID")},
            {105, 3, 4200.0, std::string("PAID")},
            {106, 3, 1500.0, std::string("FAILED")},
            {107, 4, 50.0, std::string("PAID")},
            {108, 5, 2200.0, std::string("PAID")},
            {109, 5, 300.0, std::nullopt},
            {110, 6, 0.0, std::string("PAID")}
        };

        printTitle("1. Basic order classification");

        for (const auto& order : orders) {
            validateOrder(order);

            std::cout << "Order " << order.id
                      << " | amount=" << std::fixed << std::setprecision(2)
                      << order.amount
                      << " | size=" << classifyOrderSize(order.amount)
                      << " | payment=" << classifyPayment(order)
                      << "\n";
        }

        printTitle("2. Simple CASE-like country classification");

        for (const auto& customer : customers) {
            std::cout << customer.name
                      << " | " << customer.country
                      << " | " << classifyCountry(customer.country)
                      << " | " << classifyLoyalty(customer.loyaltyPoints)
                      << "\n";
        }

        printTitle("3. Discount rule engine");

        const std::vector<DiscountRule> discountRules = {
            {"Premium", 3000.0, 0.15},
            {"Large", 1000.0, 0.10},
            {"Standard", 500.0, 0.05}
        };

        for (double amount : {50.0, 500.0, 750.0, 1000.0, 3000.0, 5000.0}) {
            const auto [ruleName, discount] =
                calculateDiscount(amount, discountRules);

            std::cout << "Amount " << std::fixed << std::setprecision(2)
                      << amount
                      << " | rule=" << ruleName
                      << " | discount=" << discount
                      << "\n";
        }

        conditionalAggregation(orders);
        conditionalSorting(orders);
        demonstrateRulePrecedence();
        demonstrateValidation();

        printTitle("4. Customer segmentation report");

        const std::vector<CustomerReport> reports =
            buildCustomerReports(customers, orders);

        printCustomerReports(reports);

        boundaryTests();
        complexityDiscussion();

        printTitle("5. Completed case study checks");

        bool boundaryCheck =
            classifyOrderSize(99.99) == "Small" &&
            classifyOrderSize(100.00) == "Medium" &&
            classifyOrderSize(1000.00) == "Large" &&
            classifyOrderSize(3000.00) == "Very large";

        bool nullCheck =
            classifyPayment(Order{999, 1, 10.0, std::nullopt})
            == "Status missing";

        bool countryCheck =
            classifyCountry("India") == "Domestic" &&
            classifyCountry("Canada") == "Other";

        std::cout << "Boundary classification: "
                  << (boundaryCheck ? "PASS" : "FAIL") << "\n";

        std::cout << "Nullable payment classification: "
                  << (nullCheck ? "PASS" : "FAIL") << "\n";

        std::cout << "Country classification: "
                  << (countryCheck ? "PASS" : "FAIL") << "\n";

        if (!boundaryCheck || !nullCheck || !countryCheck) {
            return 1;
        }

        std::cout << "\nAll executable checks passed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }
}
