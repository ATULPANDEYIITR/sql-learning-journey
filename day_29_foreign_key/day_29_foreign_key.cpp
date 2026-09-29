/*
FOREIGN KEY CASE STUDY
Referential Integrity, Parent-Child Relationships, and Cascading Actions

C++17 industry-style case study:
A commerce order-management system models customers, orders, and payments.

The program demonstrates:
- Parent-child relationships
- Foreign-key validation
- Referential integrity
- RESTRICT
- CASCADE
- SET NULL
- ON UPDATE CASCADE
- Transactions and rollback
- Validation
- Index-like lookup structures
- Composite relationship concepts
- Self-referencing relationships
- Complexity and design trade-offs

Compile:
    g++ -std=c++17 -Wall -Wextra -pedantic foreign_key_case_study.cpp -o foreign_key_case_study

Run:
    ./foreign_key_case_study
*/

#include <algorithm>
#include <cassert>
#include <iomanip>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

class IntegrityError : public runtime_error {
public:
    explicit IntegrityError(const string& message)
        : runtime_error(message) {}
};

enum class DeleteAction {
    RESTRICT,
    NO_ACTION,
    CASCADE,
    SET_NULL
};

enum class UpdateAction {
    RESTRICT,
    NO_ACTION,
    CASCADE,
    SET_NULL
};

struct Customer {
    int id;
    string name;
};

struct Order {
    int id;
    int customerId;
    double total;
};

struct Payment {
    int id;
    int orderId;
    double amount;
};

struct Employee {
    int id;
    string name;
    optional<int> managerId;
};

class OrderSystem {
private:
    unordered_map<int, Customer> customers;
    unordered_map<int, Order> orders;
    unordered_map<int, Payment> payments;

    /*
     * This secondary index maps customer_id to child order IDs.
     *
     * In a production relational database, an index on the child
     * foreign-key column serves a similar purpose: locating dependent
     * rows efficiently.
     */
    unordered_map<int, unordered_set<int>> ordersByCustomer;

    unordered_map<int, unordered_set<int>> paymentsByOrder;

    /*
     * A small transaction log is used to demonstrate the principle of
     * atomic multi-step changes. Real databases implement transactions
     * with substantially more sophisticated logging and recovery.
     */
    struct Snapshot {
        unordered_map<int, Customer> customers;
        unordered_map<int, Order> orders;
        unordered_map<int, Payment> payments;
        unordered_map<int, unordered_set<int>> ordersByCustomer;
        unordered_map<int, unordered_set<int>> paymentsByOrder;
    };

    Snapshot createSnapshot() const {
        return {
            customers,
            orders,
            payments,
            ordersByCustomer,
            paymentsByOrder
        };
    }

    void restoreSnapshot(const Snapshot& snapshot) {
        customers = snapshot.customers;
        orders = snapshot.orders;
        payments = snapshot.payments;
        ordersByCustomer = snapshot.ordersByCustomer;
        paymentsByOrder = snapshot.paymentsByOrder;
    }

public:
    void insertCustomer(int id, const string& name) {
        if (customers.contains(id)) {
            throw IntegrityError("Duplicate customer primary key.");
        }

        if (name.empty()) {
            throw IntegrityError("Customer name cannot be empty.");
        }

        customers.emplace(id, Customer{id, name});
    }

    void insertOrder(int id, int customerId, double total) {
        if (orders.contains(id)) {
            throw IntegrityError("Duplicate order primary key.");
        }

        if (!customers.contains(customerId)) {
            throw IntegrityError(
                "Foreign-key violation: customer does not exist."
            );
        }

        if (total < 0) {
            throw IntegrityError("Order total cannot be negative.");
        }

        orders.emplace(id, Order{id, customerId, total});
        ordersByCustomer[customerId].insert(id);
    }

    void insertPayment(int id, int orderId, double amount) {
        if (payments.contains(id)) {
            throw IntegrityError("Duplicate payment primary key.");
        }

        if (!orders.contains(orderId)) {
            throw IntegrityError(
                "Foreign-key violation: order does not exist."
            );
        }

        if (amount < 0) {
            throw IntegrityError("Payment amount cannot be negative.");
        }

        payments.emplace(id, Payment{id, orderId, amount});
        paymentsByOrder[orderId].insert(id);
    }

    void deletePayment(int paymentId) {
        auto iterator = payments.find(paymentId);

        if (iterator == payments.end()) {
            return;
        }

        const int orderId = iterator->second.orderId;

        payments.erase(iterator);

        auto indexIterator = paymentsByOrder.find(orderId);

        if (indexIterator != paymentsByOrder.end()) {
            indexIterator->second.erase(paymentId);

            if (indexIterator->second.empty()) {
                paymentsByOrder.erase(indexIterator);
            }
        }
    }

    /*
     * CASCADE from order to payment.
     */
    void deleteOrderCascade(int orderId) {
        if (!orders.contains(orderId)) {
            return;
        }

        const auto paymentIndexIterator = paymentsByOrder.find(orderId);

        if (paymentIndexIterator != paymentsByOrder.end()) {
            /*
             * Copy IDs before deletion because the underlying index is
             * modified by deletePayment().
             */
            vector<int> paymentIds(
                paymentIndexIterator->second.begin(),
                paymentIndexIterator->second.end()
            );

            for (int paymentId : paymentIds) {
                deletePayment(paymentId);
            }
        }

        const int customerId = orders.at(orderId).customerId;

        orders.erase(orderId);

        auto customerIndexIterator = ordersByCustomer.find(customerId);

        if (customerIndexIterator != ordersByCustomer.end()) {
            customerIndexIterator->second.erase(orderId);

            if (customerIndexIterator->second.empty()) {
                ordersByCustomer.erase(customerIndexIterator);
            }
        }
    }

    /*
     * RESTRICT behavior:
     * A customer cannot be deleted while orders reference it.
     */
    void deleteCustomerRestrict(int customerId) {
        if (!customers.contains(customerId)) {
            return;
        }

        auto indexIterator = ordersByCustomer.find(customerId);

        if (indexIterator != ordersByCustomer.end() &&
            !indexIterator->second.empty()) {
            throw IntegrityError(
                "RESTRICT prevented customer deletion because orders exist."
            );
        }

        customers.erase(customerId);
    }

    /*
     * CASCADE behavior:
     * Deleting a customer deletes orders, which then deletes payments.
     */
    void deleteCustomerCascade(int customerId) {
        if (!customers.contains(customerId)) {
            return;
        }

        auto indexIterator = ordersByCustomer.find(customerId);

        if (indexIterator != ordersByCustomer.end()) {
            vector<int> orderIds(
                indexIterator->second.begin(),
                indexIterator->second.end()
            );

            for (int orderId : orderIds) {
                deleteOrderCascade(orderId);
            }
        }

        customers.erase(customerId);
    }

    /*
     * ON UPDATE CASCADE:
     * Changing the parent primary key propagates the new key into
     * dependent orders.
     *
     * Real schemas often use immutable surrogate keys, so changing
     * primary keys may be rare. This method demonstrates the mechanism.
     */
    void updateCustomerIdCascade(int oldId, int newId) {
        if (!customers.contains(oldId)) {
            throw IntegrityError("Original customer does not exist.");
        }

        if (customers.contains(newId)) {
            throw IntegrityError("New customer ID already exists.");
        }

        Snapshot snapshot = createSnapshot();

        try {
            Customer customer = customers.at(oldId);

            auto indexIterator = ordersByCustomer.find(oldId);

            vector<int> orderIds;

            if (indexIterator != ordersByCustomer.end()) {
                orderIds.assign(
                    indexIterator->second.begin(),
                    indexIterator->second.end()
                );
            }

            customers.erase(oldId);
            customers.emplace(
                newId,
                Customer{newId, customer.name}
            );

            if (indexIterator != ordersByCustomer.end()) {
                unordered_set<int> updatedOrderIds;

                for (int orderId : orderIds) {
                    auto orderIterator = orders.find(orderId);

                    if (orderIterator != orders.end()) {
                        orderIterator->second.customerId = newId;
                        updatedOrderIds.insert(orderId);
                    }
                }

                ordersByCustomer.erase(oldId);
                ordersByCustomer[newId] = updatedOrderIds;
            }
        } catch (...) {
            restoreSnapshot(snapshot);
            throw;
        }
    }

    /*
     * SET NULL is demonstrated by changing the relationship rather than
     * deleting the employee. This is a separate organizational model.
     */
    static void deleteManagerSetNull(
        unordered_map<int, Employee>& employees,
        int managerId
    ) {
        employees.erase(managerId);

        for (auto& [id, employee] : employees) {
            if (employee.managerId.has_value() &&
                employee.managerId.value() == managerId) {
                employee.managerId = nullopt;
            }
        }
    }

    void printCustomers() const {
        cout << "\nCustomers\n";
        cout << left
             << setw(12) << "ID"
             << setw(25) << "Name"
             << '\n';

        cout << string(37, '-') << '\n';

        vector<int> ids;

        for (const auto& [id, customer] : customers) {
            ids.push_back(id);
        }

        sort(ids.begin(), ids.end());

        for (int id : ids) {
            const Customer& customer = customers.at(id);

            cout << left
                 << setw(12) << customer.id
                 << setw(25) << customer.name
                 << '\n';
        }
    }

    void printOrders() const {
        cout << "\nOrders\n";
        cout << left
             << setw(12) << "ID"
             << setw(15) << "Customer"
             << setw(15) << "Total"
             << '\n';

        cout << string(42, '-') << '\n';

        vector<int> ids;

        for (const auto& [id, order] : orders) {
            ids.push_back(id);
        }

        sort(ids.begin(), ids.end());

        for (int id : ids) {
            const Order& order = orders.at(id);

            cout << left
                 << setw(12) << order.id
                 << setw(15) << order.customerId
                 << fixed << setprecision(2)
                 << setw(15) << order.total
                 << '\n';
        }
    }

    void printPayments() const {
        cout << "\nPayments\n";
        cout << left
             << setw(12) << "ID"
             << setw(15) << "Order"
             << setw(15) << "Amount"
             << '\n';

        cout << string(42, '-') << '\n';

        vector<int> ids;

        for (const auto& [id, payment] : payments) {
            ids.push_back(id);
        }

        sort(ids.begin(), ids.end());

        for (int id : ids) {
            const Payment& payment = payments.at(id);

            cout << left
                 << setw(12) << payment.id
                 << setw(15) << payment.orderId
                 << fixed << setprecision(2)
                 << setw(15) << payment.amount
                 << '\n';
        }
    }

    size_t customerCount() const {
        return customers.size();
    }

    size_t orderCount() const {
        return orders.size();
    }

    size_t paymentCount() const {
        return payments.size();
    }

    /*
     * Transaction wrapper.
     *
     * If the supplied operation throws, the original state is restored.
     */
    template <typename Operation>
    void transaction(Operation operation) {
        Snapshot snapshot = createSnapshot();

        try {
            operation();
        } catch (...) {
            restoreSnapshot(snapshot);
            throw;
        }
    }
};

void printSection(const string& title) {
    cout << "\n";
    cout << string(78, '=') << '\n';
    cout << title << '\n';
    cout << string(78, '=') << '\n';
}

void demonstrateParentChildRelationship(OrderSystem& system) {
    printSection("1. Parent-Child Relationship");

    system.insertCustomer(1, "Anika");
    system.insertCustomer(2, "Rahul");

    system.insertOrder(101, 1, 1250.00);
    system.insertOrder(102, 1, 800.00);
    system.insertOrder(103, 2, 450.00);

    system.insertPayment(1001, 101, 1250.00);
    system.insertPayment(1002, 102, 800.00);

    system.printCustomers();
    system.printOrders();
    system.printPayments();

    cout << "\nA customer is the parent entity. Orders reference the customer, "
            "and payments reference orders.\n";
}

void demonstrateInvalidReference(OrderSystem& system) {
    printSection("2. Referential Integrity");

    try {
        system.insertOrder(999, 5000, 100.00);
        assert(false && "Invalid foreign-key insert should fail.");
    } catch (const IntegrityError& error) {
        cout << "Expected failure: " << error.what() << '\n';
    }

    cout << "No orphan order was created.\n";
}

void demonstrateRestrict(OrderSystem& system) {
    printSection("3. ON DELETE RESTRICT");

    try {
        system.deleteCustomerRestrict(1);
        assert(false && "Referenced customer should not be deleted.");
    } catch (const IntegrityError& error) {
        cout << "Expected RESTRICT failure: " << error.what() << '\n';
    }

    cout << "The customer remains because dependent orders exist.\n";
}

void demonstrateCascade(OrderSystem& system) {
    printSection("4. ON DELETE CASCADE");

    cout << "Before deleting customer 2:\n";
    system.printCustomers();
    system.printOrders();
    system.printPayments();

    system.deleteCustomerCascade(2);

    cout << "\nAfter deleting customer 2:\n";
    system.printCustomers();
    system.printOrders();
    system.printPayments();

    cout << "\nCustomer 2's orders were deleted, and the payments belonging "
            "to those orders were also deleted.\n";
}

void demonstrateUpdateCascade(OrderSystem& system) {
    printSection("5. ON UPDATE CASCADE");

    cout << "Before changing customer 1 to customer 10:\n";
    system.printCustomers();
    system.printOrders();

    system.updateCustomerIdCascade(1, 10);

    cout << "\nAfter changing the parent key:\n";
    system.printCustomers();
    system.printOrders();

    cout << "\nThe child order foreign keys were updated with the parent key.\n";
}

void demonstrateSetNull() {
    printSection("6. ON DELETE SET NULL");

    unordered_map<int, Employee> employees;

    employees.emplace(
        1,
        Employee{1, "CEO", nullopt}
    );

    employees.emplace(
        2,
        Employee{2, "Engineering Manager", 1}
    );

    employees.emplace(
        3,
        Employee{3, "Developer", 2}
    );

    employees.emplace(
        4,
        Employee{4, "Analyst", 2}
    );

    cout << "Before deleting manager 2:\n";

    for (const auto& [id, employee] : employees) {
        cout << employee.id << " "
             << employee.name << " manager=";

        if (employee.managerId.has_value()) {
            cout << employee.managerId.value();
        } else {
            cout << "NULL";
        }

        cout << '\n';
    }

    OrderSystem::deleteManagerSetNull(employees, 2);

    cout << "\nAfter deleting manager 2:\n";

    for (const auto& [id, employee] : employees) {
        cout << employee.id << " "
             << employee.name << " manager=";

        if (employee.managerId.has_value()) {
            cout << employee.managerId.value();
        } else {
            cout << "NULL";
        }

        cout << '\n';
    }

    cout << "\nThe subordinate employees survive, but their manager relationship "
            "becomes NULL.\n";
}

void demonstrateTransactionRollback() {
    printSection("7. Transaction and Rollback");

    OrderSystem system;

    system.insertCustomer(1, "Transaction Customer");
    system.insertOrder(100, 1, 500.00);

    const size_t customersBefore = system.customerCount();
    const size_t ordersBefore = system.orderCount();

    try {
        system.transaction([&]() {
            system.insertCustomer(2, "Temporary Customer");
            system.insertOrder(200, 2, 900.00);

            // This operation intentionally fails.
            system.insertOrder(201, 999, 100.00);
        });

        assert(false && "Transaction should have failed.");
    } catch (const IntegrityError& error) {
        cout << "Transaction failed: " << error.what() << '\n';
    }

    assert(system.customerCount() == customersBefore);
    assert(system.orderCount() == ordersBefore);

    cout << "All changes from the failed transaction were rolled back.\n";
}

void demonstrateCompositeKeyConcept() {
    printSection("8. Composite Foreign Key Concept");

    struct CourseOffering {
        string courseCode;
        string semester;
        string instructor;
    };

    vector<CourseOffering> offerings = {
        {"CS101", "2026-FALL", "Dr. Rao"},
        {"DB201", "2026-FALL", "Dr. Singh"}
    };

    auto exists = [&](const string& courseCode, const string& semester) {
        return any_of(
            offerings.begin(),
            offerings.end(),
            [&](const CourseOffering& offering) {
                return offering.courseCode == courseCode &&
                       offering.semester == semester;
            }
        );
    };

    cout << boolalpha;

    cout << "CS101 + 2026-FALL exists: "
         << exists("CS101", "2026-FALL") << '\n';

    cout << "CS101 + 2027-SPRING exists: "
         << exists("CS101", "2027-SPRING") << '\n';

    cout << "\nA composite foreign key references multiple parent columns "
            "as one logical key.\n";
}

void demonstratePerformance() {
    printSection("9. Performance and Indexing");

    constexpr int NUMBER_OF_ORDERS = 100000;

    vector<Order> orders;

    orders.reserve(NUMBER_OF_ORDERS);

    for (int i = 1; i <= NUMBER_OF_ORDERS; ++i) {
        orders.push_back(
            Order{
                i,
                (i % 1000) + 1,
                100.0
            }
        );
    }

    const int targetCustomer = 500;

    auto start = chrono::steady_clock::now();

    size_t matchingRows = 0;

    for (const Order& order : orders) {
        if (order.customerId == targetCustomer) {
            ++matchingRows;
        }
    }

    auto end = chrono::steady_clock::now();

    const auto elapsed =
        chrono::duration_cast<chrono::microseconds>(
            end - start
        );

    cout << "Orders scanned: " << orders.size() << '\n';
    cout << "Matching orders: " << matchingRows << '\n';
    cout << "Linear scan time: " << elapsed.count()
         << " microseconds\n";

    /*
     * The vector scan is O(n).
     *
     * A database index can reduce lookup work substantially depending on
     * index structure, data distribution, query shape, and maintenance cost.
     *
     * Indexes also consume memory/storage and make INSERT/UPDATE/DELETE
     * operations more expensive because the index must be maintained.
     */
    cout << "A child foreign-key index trades storage and write overhead "
            "for faster relationship lookups.\n";
}

void demonstrateDesignTradeoffs() {
    printSection("10. Design Trade-offs");

    cout << "RESTRICT / NO ACTION:\n";
    cout << "  Protects parent records from accidental dependent deletion.\n";

    cout << "\nCASCADE:\n";
    cout << "  Convenient for true ownership relationships, but potentially "
            "destructive across a large dependency graph.\n";

    cout << "\nSET NULL:\n";
    cout << "  Useful when the child remains meaningful without its parent.\n";

    cout << "\nSET DEFAULT:\n";
    cout << "  Useful when a well-defined fallback parent exists.\n";

    cout << "\nON UPDATE CASCADE:\n";
    cout << "  Keeps references synchronized when parent keys change.\n";

    cout << "\nSurrogate keys:\n";
    cout << "  Often provide stable references that rarely need updates.\n";
}

void demonstrateCommonMistakes() {
    printSection("11. Common Mistakes");

    const vector<string> mistakes = {
        "Creating a child reference without a real parent.",
        "Disabling foreign-key enforcement.",
        "Using nullable foreign keys when the relationship is mandatory.",
        "Choosing CASCADE without analyzing deletion consequences.",
        "Forgetting indexes on large child tables.",
        "Assuming application validation is enough.",
        "Using unstable natural keys without considering update behavior.",
        "Ignoring transaction boundaries during multi-table changes.",
        "Failing to test invalid inserts and destructive parent operations."
    };

    for (size_t i = 0; i < mistakes.size(); ++i) {
        cout << i + 1 << ". " << mistakes[i] << '\n';
    }
}

void runAssertions() {
    printSection("12. Automated Assertions");

    OrderSystem system;

    system.insertCustomer(1, "Test Customer");
    system.insertOrder(1, 1, 100.00);
    system.insertPayment(1, 1, 100.00);

    assert(system.customerCount() == 1);
    assert(system.orderCount() == 1);
    assert(system.paymentCount() == 1);

    bool invalidReferenceFailed = false;

    try {
        system.insertOrder(2, 999, 50.00);
    } catch (const IntegrityError&) {
        invalidReferenceFailed = true;
    }

    assert(invalidReferenceFailed);

    system.deleteCustomerCascade(1);

    assert(system.customerCount() == 0);
    assert(system.orderCount() == 0);
    assert(system.paymentCount() == 0);

    cout << "All assertions passed.\n";
}

int main() {
    try {
        OrderSystem system;

        demonstrateParentChildRelationship(system);
        demonstrateInvalidReference(system);
        demonstrateRestrict(system);
        demonstrateCascade(system);
        demonstrateUpdateCascade(system);
        demonstrateSetNull();
        demonstrateTransactionRollback();
        demonstrateCompositeKeyConcept();
        demonstratePerformance();
        demonstrateDesignTradeoffs();
        demonstrateCommonMistakes();
        runAssertions();

        printSection("13. Case Study Completed");

        cout << "The commerce system demonstrated how foreign keys enforce "
                "relationships between customers, orders, and payments, "
                "and how different referential actions change the behavior "
                "of parent updates and deletions.\n";
    }
    catch (const exception& error) {
        cerr << "Unexpected application error: "
             << error.what() << '\n';
        return 1;
    }

    return 0;
}
