#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

enum class OrderStatus {
    Completed,
    Cancelled,
    Pending
};

enum class Channel {
    Web,
    Mobile,
    Store
};

struct Order {
    int id;
    int customerId;
    std::string region;
    OrderStatus status;
    Channel channel;
    double amount;
    bool returned;

    Order(
        int id_,
        int customerId_,
        std::string region_,
        OrderStatus status_,
        Channel channel_,
        double amount_,
        bool returned_ = false
    )
        : id(id_),
          customerId(customerId_),
          region(std::move(region_)),
          status(status_),
          channel(channel_),
          amount(amount_),
          returned(returned_) {
        if (id <= 0 || customerId <= 0) {
            throw std::invalid_argument("IDs must be positive");
        }
        if (region.empty()) {
            throw std::invalid_argument("Region cannot be empty");
        }
        if (!std::isfinite(amount) || amount < 0.0) {
            throw std::invalid_argument("Amount must be finite and non-negative");
        }
    }
};

template <typename Predicate>
double conditionalSum(
    const std::vector<Order>& orders,
    Predicate predicate
) {
    return std::accumulate(
        orders.begin(),
        orders.end(),
        0.0,
        [&](double total, const Order& order) {
            return total + (predicate(order) ? order.amount : 0.0);
        }
    );
}

template <typename Predicate>
std::size_t conditionalCount(
    const std::vector<Order>& orders,
    Predicate predicate
) {
    return static_cast<std::size_t>(
        std::count_if(orders.begin(), orders.end(), predicate)
    );
}

template <typename Predicate>
double conditionalAverage(
    const std::vector<Order>& orders,
    Predicate predicate
) {
    double total = conditionalSum(orders, predicate);
    std::size_t count = conditionalCount(orders, predicate);

    return count == 0 ? 0.0 : total / static_cast<double>(count);
}

std::string statusName(OrderStatus status) {
    switch (status) {
        case OrderStatus::Completed:
            return "completed";
        case OrderStatus::Cancelled:
            return "cancelled";
        case OrderStatus::Pending:
            return "pending";
    }
    throw std::logic_error("Unknown status");
}

double percentage(std::size_t numerator, std::size_t denominator) {
    if (denominator == 0) {
        return 0.0;
    }

    return static_cast<double>(numerator) * 100.0 /
           static_cast<double>(denominator);
}

struct RegionalMetrics {
    std::size_t orders{};
    std::size_t completed{};
    std::size_t cancelled{};
    std::size_t returnedCompleted{};
    double revenue{};
    double webRevenue{};
};

class RevenueAnalytics {
public:
    explicit RevenueAnalytics(std::vector<Order> orders)
        : orders_(std::move(orders)) {}

    void printOverall() const {
        const auto completed = [](const Order& order) {
            return order.status == OrderStatus::Completed;
        };

        const auto cancelled = [](const Order& order) {
            return order.status == OrderStatus::Cancelled;
        };

        const auto completedCount =
            conditionalCount(orders_, completed);

        const auto cancelledCount =
            conditionalCount(orders_, cancelled);

        const auto pendingCount = conditionalCount(
            orders_,
            [](const Order& order) {
                return order.status == OrderStatus::Pending;
            }
        );

        const double completedRevenue =
            conditionalSum(orders_, completed);

        const double cancelledValue =
            conditionalSum(orders_, cancelled);

        const double webRevenue = conditionalSum(
            orders_,
            [](const Order& order) {
                return order.status == OrderStatus::Completed &&
                       order.channel == Channel::Web;
            }
        );

        const double mobileRevenue = conditionalSum(
            orders_,
            [](const Order& order) {
                return order.status == OrderStatus::Completed &&
                       order.channel == Channel::Mobile;
            }
        );

        const auto returnedCompleted = conditionalCount(
            orders_,
            [](const Order& order) {
                return order.status == OrderStatus::Completed &&
                       order.returned;
            }
        );

        const double averageCompleted =
            conditionalAverage(orders_, completed);

        std::cout << "\nOverall KPI Metrics\n";
        std::cout << "-------------------\n";
        std::cout << "Orders:                 " << orders_.size() << '\n';
        std::cout << "Completed:              " << completedCount << '\n';
        std::cout << "Cancelled:              " << cancelledCount << '\n';
        std::cout << "Pending:                " << pendingCount << '\n';
        std::cout << "Completed revenue:      " << completedRevenue << '\n';
        std::cout << "Cancelled value:        " << cancelledValue << '\n';
        std::cout << "Web revenue:            " << webRevenue << '\n';
        std::cout << "Mobile revenue:         " << mobileRevenue << '\n';
        std::cout << "Returned completed:     " << returnedCompleted << '\n';
        std::cout << "Average completed:      " << averageCompleted << '\n';
        std::cout << "Completion rate:        "
                  << percentage(completedCount, orders_.size())
                  << "%\n";
        std::cout << "Cancellation rate:      "
                  << percentage(cancelledCount, orders_.size())
                  << "%\n";
    }

    std::map<std::string, RegionalMetrics> regionalMetrics() const {
        std::map<std::string, RegionalMetrics> result;

        for (const auto& order : orders_) {
            auto& metrics = result[order.region];
            ++metrics.orders;

            if (order.status == OrderStatus::Completed) {
                ++metrics.completed;
                metrics.revenue += order.amount;

                if (order.channel == Channel::Web) {
                    metrics.webRevenue += order.amount;
                }

                if (order.returned) {
                    ++metrics.returnedCompleted;
                }
            }

            if (order.status == OrderStatus::Cancelled) {
                ++metrics.cancelled;
            }
        }

        return result;
    }

    void printRegional() const {
        const auto metrics = regionalMetrics();

        std::cout << "\nRegional Metrics\n";
        std::cout << "----------------\n";
        std::cout << std::left
                  << std::setw(10) << "Region"
                  << std::setw(10) << "Orders"
                  << std::setw(12) << "Completed"
                  << std::setw(12) << "Cancelled"
                  << std::setw(14) << "Revenue"
                  << std::setw(14) << "Web Revenue"
                  << "Completion Rate\n";

        for (const auto& [region, data] : metrics) {
            std::cout << std::left
                      << std::setw(10) << region
                      << std::setw(10) << data.orders
                      << std::setw(12) << data.completed
                      << std::setw(12) << data.cancelled
                      << std::setw(14) << data.revenue
                      << std::setw(14) << data.webRevenue
                      << percentage(data.completed, data.orders)
                      << "%\n";
        }
    }

    void validate() const {
        const auto completed = conditionalCount(
            orders_,
            [](const Order& order) {
                return order.status == OrderStatus::Completed;
            }
        );

        const auto cancelled = conditionalCount(
            orders_,
            [](const Order& order) {
                return order.status == OrderStatus::Cancelled;
            }
        );

        const auto pending = conditionalCount(
            orders_,
            [](const Order& order) {
                return order.status == OrderStatus::Pending;
            }
        );

        if (completed + cancelled + pending != orders_.size()) {
            throw std::logic_error("Conditional status counts do not partition orders");
        }

        const double emptySum = conditionalSum(
            orders_,
            [](const Order& order) {
                return order.amount > 1000000.0;
            }
        );

        if (emptySum != 0.0) {
            throw std::logic_error("Empty conditional sum must be zero");
        }
    }

private:
    std::vector<Order> orders_;
};

int main() {
    try {
        std::vector<Order> orders{
            {1, 101, "North", OrderStatus::Completed, Channel::Web, 1250.00},
            {2, 102, "North", OrderStatus::Cancelled, Channel::Mobile, 800.00},
            {3, 103, "South", OrderStatus::Completed, Channel::Mobile, 2100.00},
            {4, 104, "South", OrderStatus::Completed, Channel::Web, 1750.00, true},
            {5, 105, "East", OrderStatus::Pending, Channel::Web, 900.00},
            {6, 106, "East", OrderStatus::Completed, Channel::Store, 3200.00},
            {7, 107, "West", OrderStatus::Cancelled, Channel::Web, 600.00},
            {8, 108, "West", OrderStatus::Completed, Channel::Mobile, 1450.00},
            {9, 109, "North", OrderStatus::Completed, Channel::Web, 2800.00},
            {10, 110, "South", OrderStatus::Pending, Channel::Mobile, 1100.00}
        };

        RevenueAnalytics analytics(std::move(orders));

        analytics.validate();
        analytics.printOverall();
        analytics.printRegional();

        std::cout << "\nAggregation validation: passed\n";
    }
    catch (const std::exception& error) {
        std::cerr << "Analytics failure: "
                  << error.what() << '\n';
        return 1;
    }

    return 0;
}
