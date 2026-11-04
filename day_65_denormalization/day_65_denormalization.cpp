#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

enum class OrderStatus {
    Pending,
    Completed,
    Cancelled
};

enum class ConsistencyMode {
    Strict,
    Eventual
};

enum class MergePolicy {
    Synchronous,
    Asynchronous
};

struct Customer {
    int id;
    string name;
    string email;
};

struct Order {
    int id;
    int customerId;
    double amount;
    OrderStatus status;
};

struct CustomerAggregate {
    int customerId;
    string customerName;
    size_t orderCount = 0;
    size_t completedCount = 0;
    double totalSpending = 0.0;
    unsigned long long version = 0;
};

class Repository {
private:
    unordered_map<int, Customer> customers;
    unordered_map<int, Order> orders;

public:
    void addCustomer(const Customer& customer) {
        if (customer.id <= 0 || customer.name.empty() ||
            customer.email.empty()) {
            throw invalid_argument("Invalid customer");
        }

        if (customers.count(customer.id)) {
            throw invalid_argument("Duplicate customer ID");
        }

        for (const auto& [id, existing] : customers) {
            if (existing.email == customer.email) {
                throw invalid_argument("Duplicate customer email");
            }
        }

        customers.emplace(customer.id, customer);
    }

    void addOrder(const Order& order) {
        if (order.id <= 0 || order.amount < 0 ||
            !isfinite(order.amount)) {
            throw invalid_argument("Invalid order");
        }

        if (!customers.count(order.customerId)) {
            throw invalid_argument("Unknown customer");
        }

        if (orders.count(order.id)) {
            throw invalid_argument("Duplicate order ID");
        }

        orders.emplace(order.id, order);
    }

    void updateCustomerName(int id, const string& name) {
        auto it = customers.find(id);

        if (it == customers.end() || name.empty()) {
            throw invalid_argument("Invalid customer update");
        }

        it->second.name = name;
    }

    const unordered_map<int, Customer>& getCustomers() const {
        return customers;
    }

    const unordered_map<int, Order>& getOrders() const {
        return orders;
    }
};

class DenormalizationEngine {
private:
    const Repository& repository;

    unordered_map<int, CustomerAggregate> aggregates;
    unordered_set<int> dirtyCustomers;

    unsigned long long nextVersion = 1;

    CustomerAggregate calculate(int customerId) const {
        auto customerIt = repository.getCustomers().find(customerId);

        if (customerIt == repository.getCustomers().end()) {
            throw invalid_argument("Customer does not exist");
        }

        CustomerAggregate result{};
        result.customerId = customerId;
        result.customerName = customerIt->second.name;

        for (const auto& [id, order] : repository.getOrders()) {
            if (order.customerId != customerId) {
                continue;
            }

            ++result.orderCount;

            if (order.status == OrderStatus::Completed) {
                ++result.completedCount;
                result.totalSpending += order.amount;
            }
        }

        return result;
    }

    void rebuildOne(int customerId) {
        CustomerAggregate next = calculate(customerId);
        next.version = nextVersion++;

        // The old aggregate is replaced only after calculation succeeds.
        aggregates.insert_or_assign(customerId, next);
        dirtyCustomers.erase(customerId);
    }

public:
    explicit DenormalizationEngine(const Repository& source)
        : repository(source) {
        rebuildAll();
    }

    void rebuildAll() {
        unordered_map<int, CustomerAggregate> next;

        for (const auto& [id, customer] : repository.getCustomers()) {
            CustomerAggregate aggregate = calculate(id);
            aggregate.version = nextVersion++;
            next.emplace(id, aggregate);
        }

        aggregates.swap(next);
        dirtyCustomers.clear();
    }

    void invalidate(int customerId) {
        if (!repository.getCustomers().count(customerId)) {
            throw invalid_argument("Cannot invalidate unknown customer");
        }

        dirtyCustomers.insert(customerId);
    }

    void refresh(int customerId) {
        rebuildOne(customerId);
    }

    void refreshDirty() {
        vector<int> pending(
            dirtyCustomers.begin(), dirtyCustomers.end()
        );

        sort(pending.begin(), pending.end());

        for (int customerId : pending) {
            rebuildOne(customerId);
        }
    }

    const CustomerAggregate& get(
        int customerId,
        ConsistencyMode mode = ConsistencyMode::Strict
    ) {
        if (mode == ConsistencyMode::Strict &&
            dirtyCustomers.count(customerId)) {
            rebuildOne(customerId);
        }

        auto it = aggregates.find(customerId);

        if (it == aggregates.end()) {
            throw invalid_argument("Aggregate not found");
        }

        return it->second;
    }

    vector<CustomerAggregate> getAll() const {
        vector<CustomerAggregate> result;

        for (const auto& [id, aggregate] : aggregates) {
            result.push_back(aggregate);
        }

        sort(result.begin(), result.end(),
             [](const auto& a, const auto& b) {
                 return a.customerId < b.customerId;
             });

        return result;
    }

    bool validate() const {
        for (const auto& [id, customer] : repository.getCustomers()) {
            auto expected = calculate(id);
            auto actual = aggregates.find(id);

            if (actual == aggregates.end()) {
                return false;
            }

            const auto& value = actual->second;

            if (value.customerName != expected.customerName ||
                value.orderCount != expected.orderCount ||
                value.completedCount != expected.completedCount ||
                abs(value.totalSpending - expected.totalSpending) > 0.000001) {
                return false;
            }
        }

        return dirtyCustomers.empty();
    }

    size_t dirtyCount() const {
        return dirtyCustomers.size();
    }
};

class GovernancePolicy {
private:
    size_t minimumReads;
    size_t maximumWriteAmplification;
    double maximumStalenessSeconds;
    bool eventualConsistencyAllowed;

public:
    GovernancePolicy(
        size_t reads,
        size_t writeAmplification,
        double staleness,
        bool eventualAllowed
    ) :
        minimumReads(reads),
        maximumWriteAmplification(writeAmplification),
        maximumStalenessSeconds(staleness),
        eventualConsistencyAllowed(eventualAllowed) {

        if (reads == 0 || writeAmplification == 0 ||
            staleness < 0 || !isfinite(staleness)) {
            throw invalid_argument("Invalid policy configuration");
        }
    }

    bool evaluate(
        size_t readQueries,
        size_t writeAmplification,
        double expectedStaleness,
        bool eventualConsistency
    ) const {
        return readQueries >= minimumReads &&
               writeAmplification <= maximumWriteAmplification &&
               expectedStaleness <= maximumStalenessSeconds &&
               (!eventualConsistency || eventualConsistencyAllowed);
    }
};

string statusName(OrderStatus status) {
    switch (status) {
        case OrderStatus::Pending: return "PENDING";
        case OrderStatus::Completed: return "COMPLETED";
        case OrderStatus::Cancelled: return "CANCELLED";
    }

    return "UNKNOWN";
}

void printAggregates(const vector<CustomerAggregate>& aggregates) {
    cout << left
         << setw(12) << "CUSTOMER"
         << setw(20) << "NAME"
         << setw(12) << "ORDERS"
         << setw(12) << "COMPLETED"
         << setw(15) << "SPENDING"
         << "VERSION\n";

    for (const auto& item : aggregates) {
        cout << left
             << setw(12) << item.customerId
             << setw(20) << item.customerName
             << setw(12) << item.orderCount
             << setw(12) << item.completedCount
             << setw(15) << fixed << setprecision(2)
             << item.totalSpending
             << item.version << '\n';
    }
}

int main() {
    try {
        Repository repository;

        repository.addCustomer({1, "Aarav Sharma", "aarav@example.com"});
        repository.addCustomer({2, "Diya Verma", "diya@example.com"});
        repository.addCustomer({3, "Kabir Singh", "kabir@example.com"});

        repository.addOrder({101, 1, 1200.0, OrderStatus::Completed});
        repository.addOrder({102, 1, 800.0, OrderStatus::Completed});
        repository.addOrder({103, 1, 500.0, OrderStatus::Pending});
        repository.addOrder({104, 2, 2500.0, OrderStatus::Completed});
        repository.addOrder({105, 2, 300.0, OrderStatus::Cancelled});

        DenormalizationEngine engine(repository);

        cout << "INITIAL DENORMALIZED DATA\n";
        printAggregates(engine.getAll());

        // Read optimization avoids repeatedly aggregating the order table.
        cout << "\nREAD-OPTIMIZED CUSTOMER RECORD\n";

        const auto& customer = engine.get(1);
        cout << customer.customerName
             << " | Orders: " << customer.orderCount
             << " | Spending: " << customer.totalSpending << '\n';

        // Source changes and projection invalidation are separate operations.
        repository.addOrder({106, 1, 400.0, OrderStatus::Completed});
        engine.invalidate(1);

        cout << "\nDIRTY AGGREGATES: " << engine.dirtyCount() << '\n';

        cout << "EVENTUAL READ:\n";
        printAggregates({engine.get(1, ConsistencyMode::Eventual)});

        cout << "STRICT READ:\n";
        printAggregates({engine.get(1, ConsistencyMode::Strict)});

        repository.updateCustomerName(2, "Diya Sharma");
        engine.invalidate(2);

        engine.refreshDirty();

        cout << "\nREFRESHED DATA\n";
        printAggregates(engine.getAll());

        GovernancePolicy policy(1000, 3, 5.0, true);

        cout << "\nPOLICY DECISION\n";
        cout << (policy.evaluate(5000, 2, 1.5, true)
                     ? "DENORMALIZATION APPROVED"
                     : "DENORMALIZATION REJECTED")
             << '\n';

        cout << "\nCONSISTENCY CHECK\n";
        cout << (engine.validate() ? "CONSISTENT" : "INCONSISTENT")
             << '\n';

        // Invalid foreign-key references are rejected.
        try {
            repository.addOrder({
                107, 999, 100.0, OrderStatus::Completed
            });
        } catch (const exception& error) {
            cout << "\nEXPECTED FAILURE: " << error.what() << '\n';
        }

        // Full rebuilding provides a recovery path for projection drift.
        engine.rebuildAll();

        cout << "\nFINAL CONSISTENCY: "
             << (engine.validate() ? "VALID" : "INVALID") << '\n';

    } catch (const exception& error) {
        cerr << "APPLICATION ERROR: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
