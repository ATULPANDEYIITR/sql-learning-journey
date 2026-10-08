#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

/*
 * Multi-Table JOIN Case Study
 *
 * Scenario:
 * A logistics organization needs a repository-like relational reporting
 * engine for customers, orders, order lines, products, and sales regions.
 *
 * The program implements relational join operations in C++ rather than
 * depending on an external database library. This makes the mechanics of
 * joining several relations explicit while using C++ structures appropriate
 * for a high-performance service layer.
 *
 * Compile:
 *     g++ -std=c++17 -Wall -Wextra -pedantic multi_table_joins.cpp -o joins
 */

struct Region {
    int id;
    std::string name;
};

struct Customer {
    int id;
    std::string name;
    int regionId;
};

struct Product {
    int id;
    std::string name;
    std::string category;
    double price;
};

struct Order {
    int id;
    int customerId;
    std::string date;
    std::string status;
};

struct OrderItem {
    int orderId;
    int productId;
    int quantity;
    double unitPrice;
};

struct SalesLine {
    std::string region;
    std::string customer;
    int orderId;
    std::string product;
    int quantity;
    double value;
};

struct CustomerSummary {
    std::string customer;
    std::string region;
    int orders{};
    double revenue{};
};

class Repository {
private:
    std::vector<Region> regions;
    std::vector<Customer> customers;
    std::vector<Product> products;
    std::vector<Order> orders;
    std::vector<OrderItem> items;

public:
    Repository() {
        regions = {
            {1, "North"},
            {2, "South"},
            {3, "West"},
            {4, "East"}
        };

        customers = {
            {101, "Aarav Systems", 1},
            {102, "Bharat Logistics", 2},
            {103, "Civic Research Lab", 3},
            {104, "Delta Manufacturing", 1},
            {105, "Eastern Retail Group", 4}
        };

        products = {
            {201, "Edge Sensor", "IoT", 120.0},
            {202, "Gateway Pro", "Networking", 450.0},
            {203, "Analytics License", "Software", 800.0},
            {204, "Secure Router", "Networking", 600.0},
            {205, "Inspection Camera", "Vision", 950.0}
        };

        orders = {
            {1001, 101, "2026-09-01", "DELIVERED"},
            {1002, 101, "2026-09-14", "SHIPPED"},
            {1003, 102, "2026-09-18", "DELIVERED"},
            {1004, 103, "2026-09-20", "CANCELLED"},
            {1005, 104, "2026-09-22", "DELIVERED"},
            {1006, 105, "2026-09-24", "PLACED"}
        };

        items = {
            {1001, 201, 10, 120.0},
            {1001, 202, 2, 450.0},
            {1002, 203, 1, 800.0},
            {1002, 201, 5, 120.0},
            {1003, 204, 3, 600.0},
            {1003, 201, 20, 120.0},
            {1004, 205, 1, 950.0},
            {1005, 205, 4, 950.0},
            {1005, 203, 2, 800.0},
            {1006, 202, 1, 450.0}
        };
    }

    std::vector<SalesLine> fiveTableJoin() const {
        /*
         * This nested traversal corresponds to:
         * regions -> customers -> orders -> items -> products.
         *
         * The lookup maps avoid scanning every relation for every row.
         * That changes the implementation from repeated O(n*m) scans toward
         * indexed lookups for the foreign-key relationships.
         */
        std::unordered_map<int, Region> regionById;
        std::unordered_map<int, Customer> customerById;
        std::unordered_map<int, Product> productById;

        for (const auto& region : regions) {
            regionById.emplace(region.id, region);
        }

        for (const auto& customer : customers) {
            customerById.emplace(customer.id, customer);
        }

        for (const auto& product : products) {
            productById.emplace(product.id, product);
        }

        std::unordered_map<int, std::vector<const OrderItem*>> itemsByOrder;

        for (const auto& item : items) {
            itemsByOrder[item.orderId].push_back(&item);
        }

        std::vector<SalesLine> result;

        for (const auto& order : orders) {
            if (order.status == "CANCELLED") {
                continue;
            }

            auto customerIt = customerById.find(order.customerId);
            if (customerIt == customerById.end()) {
                throw std::logic_error("Order references missing customer");
            }

            auto regionIt = regionById.find(customerIt->second.regionId);
            if (regionIt == regionById.end()) {
                throw std::logic_error("Customer references missing region");
            }

            auto itemIt = itemsByOrder.find(order.id);
            if (itemIt == itemsByOrder.end()) {
                continue;
            }

            for (const OrderItem* item : itemIt->second) {
                auto productIt = productById.find(item->productId);

                if (productIt == productById.end()) {
                    throw std::logic_error("Order item references missing product");
                }

                result.push_back({
                    regionIt->second.name,
                    customerIt->second.name,
                    order.id,
                    productIt->second.name,
                    item->quantity,
                    item->quantity * item->unitPrice
                });
            }
        }

        std::sort(result.begin(), result.end(),
                  [](const SalesLine& a, const SalesLine& b) {
                      return std::tie(a.region, a.orderId, a.product) <
                             std::tie(b.region, b.orderId, b.product);
                  });

        return result;
    }

    std::vector<CustomerSummary> aggregateCustomerRevenue() const {
        /*
         * The aggregation intentionally happens after the relationships are
         * resolved. Summing before the order-to-item relationship is joined
         * would lose the line-level quantities needed for revenue.
         */
        std::unordered_map<int, Customer> customerById;
        std::unordered_map<int, Region> regionById;
        std::unordered_map<int, double> revenueByCustomer;
        std::unordered_map<int, std::set<int>> ordersByCustomer;

        for (const auto& c : customers) {
            customerById[c.id] = c;
        }

        for (const auto& r : regions) {
            regionById[r.id] = r;
        }

        std::unordered_map<int, std::vector<const OrderItem*>> itemsByOrder;
        for (const auto& item : items) {
            itemsByOrder[item.orderId].push_back(&item);
        }

        for (const auto& order : orders) {
            if (order.status != "DELIVERED") {
                continue;
            }

            const auto customerIt = customerById.find(order.customerId);
            if (customerIt == customerById.end()) {
                continue;
            }

            ordersByCustomer[order.customerId].insert(order.id);

            for (const OrderItem* item : itemsByOrder[order.id]) {
                revenueByCustomer[order.customerId] +=
                    item->quantity * item->unitPrice;
            }
        }

        std::vector<CustomerSummary> summaries;

        for (const auto& [customerId, customer] : customerById) {
            auto regionIt = regionById.find(customer.regionId);
            if (regionIt == regionById.end()) {
                continue;
            }

            summaries.push_back({
                customer.name,
                regionIt->second.name,
                static_cast<int>(ordersByCustomer[customerId].size()),
                revenueByCustomer[customerId]
            });
        }

        std::sort(summaries.begin(), summaries.end(),
                  [](const CustomerSummary& a, const CustomerSummary& b) {
                      return a.revenue > b.revenue;
                  });

        return summaries;
    }

    std::vector<CustomerSummary> leftJoinCustomerOrders() const {
        /*
         * LEFT JOIN semantics require every customer to survive the join,
         * including a customer with zero matching orders.
         */
        std::unordered_map<int, int> orderCount;

        for (const auto& order : orders) {
            ++orderCount[order.customerId];
        }

        std::unordered_map<int, std::string> regionNames;
        for (const auto& region : regions) {
            regionNames[region.id] = region.name;
        }

        std::vector<CustomerSummary> result;

        for (const auto& customer : customers) {
            result.push_back({
                customer.name,
                regionNames.at(customer.regionId),
                orderCount[customer.id],
                0.0
            });
        }

        return result;
    }

    void validateForeignKeys() const {
        std::set<int> regionIds;
        std::set<int> customerIds;
        std::set<int> productIds;
        std::set<int> orderIds;

        for (const auto& region : regions) {
            regionIds.insert(region.id);
        }

        for (const auto& customer : customers) {
            customerIds.insert(customer.id);
            if (!regionIds.contains(customer.regionId)) {
                throw std::logic_error("Invalid customer -> region relationship");
            }
        }

        for (const auto& product : products) {
            productIds.insert(product.id);
        }

        for (const auto& order : orders) {
            orderIds.insert(order.id);
            if (!customerIds.contains(order.customerId)) {
                throw std::logic_error("Invalid order -> customer relationship");
            }
        }

        for (const auto& item : items) {
            if (!orderIds.contains(item.orderId)) {
                throw std::logic_error("Invalid order item -> order relationship");
            }

            if (!productIds.contains(item.productId)) {
                throw std::logic_error("Invalid order item -> product relationship");
            }

            if (item.quantity <= 0 || item.unitPrice <= 0) {
                throw std::logic_error("Invalid order item values");
            }
        }
    }
};

void printLines(const std::vector<SalesLine>& lines) {
    std::cout << "\n=== Five-table join ===\n";
    std::cout << std::left
              << std::setw(10) << "Region"
              << std::setw(24) << "Customer"
              << std::setw(10) << "Order"
              << std::setw(22) << "Product"
              << std::setw(10) << "Qty"
              << "Value\n";

    for (const auto& line : lines) {
        std::cout << std::left
                  << std::setw(10) << line.region
                  << std::setw(24) << line.customer
                  << std::setw(10) << line.orderId
                  << std::setw(22) << line.product
                  << std::setw(10) << line.quantity
                  << std::fixed << std::setprecision(2)
                  << line.value << '\n';
    }
}

void printSummaries(const std::vector<CustomerSummary>& summaries,
                    const std::string& title) {
    std::cout << "\n=== " << title << " ===\n";

    for (const auto& summary : summaries) {
        std::cout << summary.customer
                  << " | " << summary.region
                  << " | orders=" << summary.orders
                  << " | revenue=" << std::fixed
                  << std::setprecision(2) << summary.revenue << '\n';
    }
}

int main() {
    try {
        Repository repository;

        repository.validateForeignKeys();

        const auto joinedLines = repository.fiveTableJoin();
        printLines(joinedLines);

        const auto summaries = repository.aggregateCustomerRevenue();
        printSummaries(summaries, "Delivered revenue after multi-table join");

        const auto leftJoin = repository.leftJoinCustomerOrders();
        printSummaries(leftJoin, "Customer-preserving LEFT JOIN model");

        std::cout << "\n=== Join design characteristics ===\n";
        std::cout << "Foreign-key relationships are resolved through hash maps.\n";
        std::cout << "Line-level values are calculated before customer aggregation.\n";
        std::cout << "LEFT JOIN behavior preserves customers with no matching orders.\n";
        std::cout << "Invalid relationships fail validation before reporting.\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Repository processing failed: "
                  << error.what() << '\n';
        return 1;
    }
}
