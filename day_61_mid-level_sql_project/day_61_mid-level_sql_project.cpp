#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

enum class OrderStatus {
    Pending,
    Paid,
    Shipped,
    Cancelled
};

struct Customer {
    int id;
    std::string name;
    std::string email;
    std::string city;
    double creditLimit;
};

struct Product {
    int id;
    std::string name;
    std::string category;
    double unitPrice;
    int stock;
};

struct OrderLine {
    int productId;
    int quantity;
    double unitPrice;
};

struct Order {
    int id;
    int customerId;
    std::string orderDate;
    OrderStatus status;
    std::vector<OrderLine> lines;
};

struct CategoryRevenue {
    std::string category;
    double revenue;
};

class SalesException : public std::runtime_error {
public:
    explicit SalesException(const std::string& message)
        : std::runtime_error(message) {}
};

class SalesEngine {
private:
    std::unordered_map<int, Customer> customers_;
    std::unordered_map<int, Product> products_;
    std::unordered_map<int, Order> orders_;

    static double roundMoney(double value) {
        return std::round(value * 100.0) / 100.0;
    }

    static bool validTransition(OrderStatus from, OrderStatus to) {
        switch (from) {
            case OrderStatus::Pending:
                return to == OrderStatus::Paid || to == OrderStatus::Cancelled;
            case OrderStatus::Paid:
                return to == OrderStatus::Shipped || to == OrderStatus::Cancelled;
            case OrderStatus::Shipped:
            case OrderStatus::Cancelled:
                return false;
        }
        return false;
    }

public:
    void addCustomer(Customer customer) {
        if (customer.id <= 0 || customer.name.empty() ||
            customer.email.find('@') == std::string::npos ||
            customer.creditLimit < 0) {
            throw SalesException("Invalid customer.");
        }

        if (customers_.contains(customer.id)) {
            throw SalesException("Duplicate customer ID.");
        }

        customers_.emplace(customer.id, std::move(customer));
    }

    void addProduct(Product product) {
        if (product.id <= 0 || product.name.empty() ||
            product.category.empty() || product.unitPrice <= 0 ||
            product.stock < 0) {
            throw SalesException("Invalid product.");
        }

        if (products_.contains(product.id)) {
            throw SalesException("Duplicate product ID.");
        }

        products_.emplace(product.id, std::move(product));
    }

    void createOrder(
        int orderId,
        int customerId,
        const std::string& orderDate,
        const std::vector<std::pair<int, int>>& requestedLines
    ) {
        if (orderId <= 0 || orders_.contains(orderId)) {
            throw SalesException("Invalid or duplicate order ID.");
        }

        if (!customers_.contains(customerId)) {
            throw SalesException("Customer does not exist.");
        }

        if (requestedLines.empty()) {
            throw SalesException("Order cannot be empty.");
        }

        // Validate every line before changing any inventory.
        std::unordered_map<int, int> requestedTotals;
        std::vector<OrderLine> lines;

        for (const auto& [productId, quantity] : requestedLines) {
            if (quantity <= 0) {
                throw SalesException("Quantity must be positive.");
            }

            auto productIt = products_.find(productId);
            if (productIt == products_.end()) {
                throw SalesException("Product does not exist.");
            }

            requestedTotals[productId] += quantity;

            if (requestedTotals[productId] > productIt->second.stock) {
                throw SalesException(
                    "Requested quantity exceeds available stock."
                );
            }

            lines.push_back({
                productId,
                quantity,
                productIt->second.unitPrice
            });
        }

        for (const auto& [productId, quantity] : requestedTotals) {
            products_.at(productId).stock -= quantity;
        }

        orders_.emplace(
            orderId,
            Order{
                orderId,
                customerId,
                orderDate,
                OrderStatus::Pending,
                std::move(lines)
            }
        );
    }

    double orderTotal(const Order& order) const {
        double total = 0.0;
        for (const auto& line : order.lines) {
            total += line.quantity * line.unitPrice;
        }
        return roundMoney(total);
    }

    void transitionOrder(int orderId, OrderStatus newStatus) {
        auto orderIt = orders_.find(orderId);
        if (orderIt == orders_.end()) {
            throw SalesException("Order does not exist.");
        }

        Order& order = orderIt->second;

        if (!validTransition(order.status, newStatus)) {
            throw SalesException("Invalid order status transition.");
        }

        if (newStatus == OrderStatus::Cancelled) {
            for (const auto& line : order.lines) {
                products_.at(line.productId).stock += line.quantity;
            }
        }

        order.status = newStatus;
    }

    std::vector<const Order*> completedOrders() const {
        std::vector<const Order*> result;

        for (const auto& [id, order] : orders_) {
            if (order.status == OrderStatus::Paid ||
                order.status == OrderStatus::Shipped) {
                result.push_back(&order);
            }
        }

        return result;
    }

    std::vector<CategoryRevenue> revenueByCategory() const {
        std::map<std::string, double> totals;

        for (const Order* order : completedOrders()) {
            for (const auto& line : order->lines) {
                const auto& product = products_.at(line.productId);
                totals[product.category] += line.quantity * line.unitPrice;
            }
        }

        std::vector<CategoryRevenue> result;
        for (auto& [category, revenue] : totals) {
            result.push_back({category, roundMoney(revenue)});
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const auto& a, const auto& b) {
                return a.revenue > b.revenue;
            }
        );

        return result;
    }

    std::vector<std::pair<std::string, double>> customerRevenue() const {
        std::map<int, double> totals;

        for (const Order* order : completedOrders()) {
            totals[order->customerId] += orderTotal(*order);
        }

        std::vector<std::pair<std::string, double>> result;

        for (const auto& [customerId, revenue] : totals) {
            result.emplace_back(
                customers_.at(customerId).name,
                roundMoney(revenue)
            );
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const auto& a, const auto& b) {
                return a.second > b.second;
            }
        );

        return result;
    }

    double totalRevenue() const {
        double total = 0.0;
        for (const Order* order : completedOrders()) {
            total += orderTotal(*order);
        }
        return roundMoney(total);
    }

    int stock(int productId) const {
        return products_.at(productId).stock;
    }
};

static void printMoney(double value) {
    std::cout << std::fixed << std::setprecision(2) << value;
}

int main() {
    try {
        SalesEngine engine;

        engine.addCustomer({
            1, "Apex Retail", "sales@apex.example", "Delhi", 15000.00
        });
        engine.addCustomer({
            2, "Northstar Foods", "orders@northstar.example", "Lucknow", 10000.00
        });
        engine.addCustomer({
            3, "Greenline Stores", "procurement@greenline.example", "Pune", 12000.00
        });

        engine.addProduct({
            101, "Business Laptop", "Computers", 85000.00, 20
        });
        engine.addProduct({
            102, "Wireless Keyboard", "Accessories", 2500.00, 100
        });
        engine.addProduct({
            103, "USB-C Dock", "Accessories", 6500.00, 50
        });
        engine.addProduct({
            104, "Network Switch", "Networking", 12000.00, 30
        });

        engine.createOrder(
            1001,
            1,
            "2026-01-10",
            {{101, 2}, {102, 5}}
        );
        engine.transitionOrder(1001, OrderStatus::Paid);
        engine.transitionOrder(1001, OrderStatus::Shipped);

        engine.createOrder(
            1002,
            2,
            "2026-02-12",
            {{104, 2}, {103, 3}}
        );
        engine.transitionOrder(1002, OrderStatus::Paid);

        engine.createOrder(
            1003,
            3,
            "2026-03-05",
            {{102, 10}, {103, 4}}
        );
        engine.transitionOrder(1003, OrderStatus::Paid);

        // Verify that invalid demand does not modify inventory.
        const int stockBefore = engine.stock(101);

        try {
            engine.createOrder(
                1004,
                1,
                "2026-03-10",
                {{101, 999}}
            );
        } catch (const SalesException& error) {
            std::cout << "Rejected order: " << error.what() << '\n';
        }

        if (engine.stock(101) != stockBefore) {
            throw SalesException("Inventory changed after rejected order.");
        }

        std::cout << "\nSALES ANALYSIS\n";
        std::cout << "===============\n";
        std::cout << "Total revenue: ";
        printMoney(engine.totalRevenue());
        std::cout << "\n";

        std::cout << "\nRevenue by category:\n";
        for (const auto& row : engine.revenueByCategory()) {
            std::cout << "  " << row.category << ": ";
            printMoney(row.revenue);
            std::cout << '\n';
        }

        std::cout << "\nRevenue by customer:\n";
        for (const auto& [customer, revenue] : engine.customerRevenue()) {
            std::cout << "  " << customer << ": ";
            printMoney(revenue);
            std::cout << '\n';
        }

        // The engine keeps indexes by ID using hash maps, while analytical
        // aggregation uses ordered maps where deterministic output is useful.
        // Order creation is O(L), status changes are O(L), and revenue
        // aggregation is O(L) over completed order lines.
    } catch (const SalesException& error) {
        std::cerr << "Sales error: " << error.what() << '\n';
        return 1;
    } catch (const std::exception& error) {
        std::cerr << "Unexpected error: " << error.what() << '\n';
        return 2;
    }

    return 0;
}
