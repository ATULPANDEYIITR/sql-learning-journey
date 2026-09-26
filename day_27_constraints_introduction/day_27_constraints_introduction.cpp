/*
 * Constraints Introduction: Constraints, Data Integrity, and Constraint Enforcement
 *
 * C++17 industry-style case study:
 *
 * A small order-management system uses explicit constraint enforcement to
 * protect customer, product, inventory, and order data.
 *
 * The program demonstrates:
 * - Entity integrity
 * - Domain integrity
 * - Referential integrity
 * - PRIMARY KEY semantics
 * - UNIQUE semantics
 * - NOT NULL semantics
 * - CHECK semantics
 * - Composite uniqueness
 * - Foreign-key enforcement
 * - Transaction-like rollback
 * - Validation layers
 * - Inventory constraints
 * - Duplicate order protection
 * - Error classification
 * - Complexity and design trade-offs
 *
 * Compile:
 *     g++ -std=c++17 -O2 constraints_case_study.cpp -o constraints_case_study
 */

#include <algorithm>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

using namespace std;


// =============================================================================
// 1. ERROR TYPES
// =============================================================================

enum class ConstraintType {
    NotNull,
    PrimaryKey,
    Unique,
    Check,
    ForeignKey,
    Transaction
};

string constraintTypeToString(ConstraintType type) {
    switch (type) {
        case ConstraintType::NotNull:
            return "NOT NULL";
        case ConstraintType::PrimaryKey:
            return "PRIMARY KEY";
        case ConstraintType::Unique:
            return "UNIQUE";
        case ConstraintType::Check:
            return "CHECK";
        case ConstraintType::ForeignKey:
            return "FOREIGN KEY";
        case ConstraintType::Transaction:
            return "TRANSACTION";
    }

    return "UNKNOWN";
}

class ConstraintViolation : public runtime_error {
private:
    ConstraintType type_;

public:
    ConstraintViolation(
        ConstraintType type,
        const string& message
    )
        : runtime_error(message), type_(type) {}

    ConstraintType type() const {
        return type_;
    }
};


// =============================================================================
// 2. BASIC DOMAIN OBJECTS
// =============================================================================

struct Customer {
    int id;
    string email;
    string name;
};

struct Product {
    int id;
    string sku;
    string name;
    int64_t priceCents;
    int stockQuantity;
};

struct Order {
    int id;
    int customerId;
    string status;
    int64_t totalCents;
};

struct OrderItem {
    int orderId;
    int productId;
    int quantity;
    int64_t unitPriceCents;
};


// =============================================================================
// 3. APPLICATION-LEVEL VALIDATION
// =============================================================================

vector<string> validateCustomerInput(
    const string& email,
    const string& name
) {
    vector<string> errors;

    if (email.empty()) {
        errors.push_back("Email is required.");
    } else if (email.find('@') == string::npos) {
        errors.push_back("Email must contain '@'.");
    }

    if (name.empty()) {
        errors.push_back("Name is required.");
    }

    return errors;
}

vector<string> validateProductInput(
    const string& sku,
    const string& name,
    int64_t priceCents,
    int stockQuantity
) {
    vector<string> errors;

    if (sku.empty()) {
        errors.push_back("SKU is required.");
    }

    if (name.empty()) {
        errors.push_back("Product name is required.");
    }

    if (priceCents < 0) {
        errors.push_back("Price cannot be negative.");
    }

    if (stockQuantity < 0) {
        errors.push_back("Stock cannot be negative.");
    }

    return errors;
}


// =============================================================================
// 4. ORDER DATABASE
// =============================================================================

class OrderDatabase {
private:
    unordered_map<int, Customer> customers_;
    unordered_map<int, Product> products_;
    unordered_map<int, Order> orders_;

    /*
     * A pair of integers represents the composite key:
     *
     *     (order_id, product_id)
     *
     * This models a composite PRIMARY KEY on order_items.
     */
    struct ItemKey {
        int orderId;
        int productId;

        bool operator==(const ItemKey& other) const {
            return orderId == other.orderId &&
                   productId == other.productId;
        }
    };

    struct ItemKeyHash {
        size_t operator()(const ItemKey& key) const {
            const size_t first =
                hash<int>{}(key.orderId);

            const size_t second =
                hash<int>{}(key.productId);

            return first ^
                   (second + 0x9e3779b9 +
                    (first << 6) +
                    (first >> 2));
        }
    };

    unordered_map<ItemKey, OrderItem, ItemKeyHash> orderItems_;

    /*
     * UNIQUE indexes are represented explicitly.
     *
     * In a real relational database, an index can provide efficient
     * enforcement. Here we maintain hash sets to demonstrate the same
     * conceptual invariant.
     */
    unordered_map<string, int> customerEmailIndex_;
    unordered_map<string, int> productSkuIndex_;

    int nextOrderId_ = 1000;

    /*
     * The transaction snapshot provides an educational simulation of
     * atomicity. A production database provides stronger transactional
     * guarantees, durability, isolation, and concurrency control.
     */
    struct Snapshot {
        unordered_map<int, Customer> customers;
        unordered_map<int, Product> products;
        unordered_map<int, Order> orders;
        unordered_map<ItemKey, OrderItem, ItemKeyHash> orderItems;
        unordered_map<string, int> customerEmailIndex;
        unordered_map<string, int> productSkuIndex;
        int nextOrderId;
    };

    optional<Snapshot> snapshot_;

public:
    // -------------------------------------------------------------------------
    // Customer constraints
    // -------------------------------------------------------------------------

    void addCustomer(
        int id,
        const string& email,
        const string& name
    ) {
        /*
         * PRIMARY KEY:
         * id must identify exactly one customer.
         */
        if (customers_.find(id) != customers_.end()) {
            throw ConstraintViolation(
                ConstraintType::PrimaryKey,
                "Customer ID already exists."
            );
        }

        /*
         * NOT NULL:
         * Empty strings are treated as invalid required values in this
         * application model.
         */
        if (email.empty() || name.empty()) {
            throw ConstraintViolation(
                ConstraintType::NotNull,
                "Customer email and name are required."
            );
        }

        /*
         * UNIQUE:
         * Two customers cannot share the same email.
         */
        if (customerEmailIndex_.find(email) !=
            customerEmailIndex_.end()) {
            throw ConstraintViolation(
                ConstraintType::Unique,
                "Customer email must be unique."
            );
        }

        customers_.emplace(
            id,
            Customer{id, email, name}
        );

        customerEmailIndex_[email] = id;
    }

    // -------------------------------------------------------------------------
    // Product constraints
    // -------------------------------------------------------------------------

    void addProduct(
        int id,
        const string& sku,
        const string& name,
        int64_t priceCents,
        int stockQuantity
    ) {
        if (products_.find(id) != products_.end()) {
            throw ConstraintViolation(
                ConstraintType::PrimaryKey,
                "Product ID already exists."
            );
        }

        if (sku.empty() || name.empty()) {
            throw ConstraintViolation(
                ConstraintType::NotNull,
                "Product SKU and name are required."
            );
        }

        if (productSkuIndex_.find(sku) !=
            productSkuIndex_.end()) {
            throw ConstraintViolation(
                ConstraintType::Unique,
                "Product SKU must be unique."
            );
        }

        /*
         * CHECK:
         *
         * price >= 0
         * stock >= 0
         */
        if (priceCents < 0 || stockQuantity < 0) {
            throw ConstraintViolation(
                ConstraintType::Check,
                "Product price and stock cannot be negative."
            );
        }

        products_.emplace(
            id,
            Product{
                id,
                sku,
                name,
                priceCents,
                stockQuantity
            }
        );

        productSkuIndex_[sku] = id;
    }

    // -------------------------------------------------------------------------
    // Order creation
    // -------------------------------------------------------------------------

    int createOrder(
        int customerId,
        const vector<pair<int, int>>& requestedItems
    ) {
        /*
         * FOREIGN KEY:
         * An order cannot reference a nonexistent customer.
         */
        if (customers_.find(customerId) == customers_.end()) {
            throw ConstraintViolation(
                ConstraintType::ForeignKey,
                "Order references a nonexistent customer."
            );
        }

        if (requestedItems.empty()) {
            throw ConstraintViolation(
                ConstraintType::Check,
                "An order must contain at least one product."
            );
        }

        /*
         * Composite business rule:
         * The same product should not appear twice in the same order.
         *
         * This can be modeled as:
         *
         *     PRIMARY KEY (order_id, product_id)
         */
        unordered_set<int> productIdsInOrder;

        for (const auto& [productId, quantity] : requestedItems) {
            if (!productIdsInOrder.insert(productId).second) {
                throw ConstraintViolation(
                    ConstraintType::Unique,
                    "The same product cannot appear twice in one order."
                );
            }

            if (products_.find(productId) == products_.end()) {
                throw ConstraintViolation(
                    ConstraintType::ForeignKey,
                    "Order item references a nonexistent product."
                );
            }

            /*
             * CHECK:
             * Quantity must be positive.
             */
            if (quantity <= 0) {
                throw ConstraintViolation(
                    ConstraintType::Check,
                    "Order quantity must be greater than zero."
                );
            }

            /*
             * Inventory invariant:
             *
             * stockQuantity - requestedQuantity >= 0
             *
             * The check occurs before any stock is modified.
             */
            const Product& product = products_.at(productId);

            if (quantity > product.stockQuantity) {
                throw ConstraintViolation(
                    ConstraintType::Check,
                    "Requested quantity exceeds available stock."
                );
            }
        }

        const int orderId = nextOrderId_++;

        int64_t totalCents = 0;

        for (const auto& [productId, quantity] : requestedItems) {
            const Product& product = products_.at(productId);

            /*
             * Overflow protection is relevant when monetary values are
             * represented using integers.
             */
            if (quantity >
                numeric_limits<int64_t>::max() /
                    max<int64_t>(1, product.priceCents)) {
                throw ConstraintViolation(
                    ConstraintType::Check,
                    "Order total would overflow int64_t."
                );
            }

            const int64_t lineTotal =
                product.priceCents * quantity;

            if (totalCents >
                numeric_limits<int64_t>::max() - lineTotal) {
                throw ConstraintViolation(
                    ConstraintType::Check,
                    "Order total would overflow int64_t."
                );
            }

            totalCents += lineTotal;
        }

        orders_.emplace(
            orderId,
            Order{
                orderId,
                customerId,
                "confirmed",
                totalCents
            }
        );

        /*
         * Once all validation succeeds, stock is reduced and order items
         * are inserted. This entire operation should occur atomically.
         */
        for (const auto& [productId, quantity] : requestedItems) {
            Product& product = products_.at(productId);

            product.stockQuantity -= quantity;

            ItemKey key{orderId, productId};

            orderItems_.emplace(
                key,
                OrderItem{
                    orderId,
                    productId,
                    quantity,
                    product.priceCents
                }
            );
        }

        return orderId;
    }

    // -------------------------------------------------------------------------
    // Transaction handling
    // -------------------------------------------------------------------------

    void beginTransaction() {
        if (snapshot_.has_value()) {
            throw runtime_error(
                "A transaction is already active."
            );
        }

        snapshot_ = Snapshot{
            customers_,
            products_,
            orders_,
            orderItems_,
            customerEmailIndex_,
            productSkuIndex_,
            nextOrderId_
        };
    }

    void commit() {
        if (!snapshot_.has_value()) {
            throw runtime_error(
                "No transaction is active."
            );
        }

        snapshot_.reset();
    }

    void rollback() {
        if (!snapshot_.has_value()) {
            throw runtime_error(
                "No transaction is active."
            );
        }

        customers_ = snapshot_->customers;
        products_ = snapshot_->products;
        orders_ = snapshot_->orders;
        orderItems_ = snapshot_->orderItems;
        customerEmailIndex_ = snapshot_->customerEmailIndex;
        productSkuIndex_ = snapshot_->productSkuIndex;
        nextOrderId_ = snapshot_->nextOrderId;

        snapshot_.reset();
    }

    template <typename Function>
    void transaction(Function&& function) {
        beginTransaction();

        try {
            function();
            commit();
        } catch (...) {
            rollback();
            throw;
        }
    }

    // -------------------------------------------------------------------------
    // Delete customer
    // -------------------------------------------------------------------------

    void deleteCustomer(int customerId) {
        auto customerIterator = customers_.find(customerId);

        if (customerIterator == customers_.end()) {
            return;
        }

        /*
         * ON DELETE RESTRICT:
         *
         * A customer with orders cannot be deleted. This preserves historical
         * order data and prevents dangling foreign-key references.
         */
        for (const auto& [orderId, order] : orders_) {
            if (order.customerId == customerId) {
                throw ConstraintViolation(
                    ConstraintType::ForeignKey,
                    "Customer cannot be deleted while orders reference it."
                );
            }
        }

        customerEmailIndex_.erase(
            customerIterator->second.email
        );

        customers_.erase(customerIterator);
    }

    // -------------------------------------------------------------------------
    // Reporting
    // -------------------------------------------------------------------------

    void printCustomers() const {
        cout << "\nCustomers\n";
        cout << left
             << setw(8) << "ID"
             << setw(30) << "Email"
             << setw(20) << "Name"
             << '\n';

        cout << string(58, '-') << '\n';

        for (const auto& [id, customer] : customers_) {
            cout << left
                 << setw(8) << customer.id
                 << setw(30) << customer.email
                 << setw(20) << customer.name
                 << '\n';
        }
    }

    void printProducts() const {
        cout << "\nProducts\n";
        cout << left
             << setw(8) << "ID"
             << setw(15) << "SKU"
             << setw(22) << "Name"
             << setw(15) << "Price"
             << setw(10) << "Stock"
             << '\n';

        cout << string(70, '-') << '\n';

        for (const auto& [id, product] : products_) {
            cout << left
                 << setw(8) << product.id
                 << setw(15) << product.sku
                 << setw(22) << product.name
                 << setw(15) << product.priceCents
                 << setw(10) << product.stockQuantity
                 << '\n';
        }
    }

    void printOrders() const {
        cout << "\nOrders\n";
        cout << left
             << setw(10) << "Order"
             << setw(12) << "Customer"
             << setw(15) << "Status"
             << setw(15) << "Total"
             << '\n';

        cout << string(52, '-') << '\n';

        for (const auto& [id, order] : orders_) {
            cout << left
                 << setw(10) << order.id
                 << setw(12) << order.customerId
                 << setw(15) << order.status
                 << setw(15) << order.totalCents
                 << '\n';
        }
    }

    size_t customerCount() const {
        return customers_.size();
    }

    size_t orderCount() const {
        return orders_.size();
    }

    int stockFor(int productId) const {
        return products_.at(productId).stockQuantity;
    }
};


// =============================================================================
// 5. TESTING UTILITIES
// =============================================================================

void expectConstraintViolation(
    const string& description,
    const function<void()>& operation
) {
    try {
        operation();

        cout << "FAIL: "
             << description
             << " -> operation unexpectedly succeeded\n";
    } catch (const ConstraintViolation& error) {
        cout << "PASS: "
             << description
             << " -> "
             << constraintTypeToString(error.type())
             << '\n';
    } catch (const exception& error) {
        cout << "FAIL: "
             << description
             << " -> unexpected error: "
             << error.what()
             << '\n';
    }
}


// =============================================================================
// 6. CASE STUDY SETUP
// =============================================================================

OrderDatabase createCaseStudyDatabase() {
    OrderDatabase database;

    database.addCustomer(
        1,
        "alice@example.com",
        "Alice"
    );

    database.addCustomer(
        2,
        "bob@example.com",
        "Bob"
    );

    database.addProduct(
        101,
        "KB-001",
        "Mechanical Keyboard",
        4999,
        10
    );

    database.addProduct(
        102,
        "MS-001",
        "Wireless Mouse",
        2499,
        20
    );

    database.addProduct(
        103,
        "MN-001",
        "Monitor",
        18999,
        5
    );

    return database;
}


// =============================================================================
// 7. DEMONSTRATIONS
// =============================================================================

void demonstrateBasicConstraints() {
    cout << "\n"
         << string(78, '=')
         << "\n1. Basic constraint enforcement\n"
         << string(78, '=')
         << '\n';

    OrderDatabase database = createCaseStudyDatabase();

    expectConstraintViolation(
        "Duplicate customer primary key",
        [&]() {
            database.addCustomer(
                1,
                "new@example.com",
                "Duplicate"
            );
        }
    );

    expectConstraintViolation(
        "Duplicate customer email",
        [&]() {
            database.addCustomer(
                3,
                "alice@example.com",
                "Another Alice"
            );
        }
    );

    expectConstraintViolation(
        "Negative product price",
        [&]() {
            database.addProduct(
                104,
                "BAD-001",
                "Invalid Product",
                -1,
                5
            );
        }
    );

    expectConstraintViolation(
        "Duplicate product SKU",
        [&]() {
            database.addProduct(
                105,
                "KB-001",
                "Duplicate SKU",
                1000,
                5
            );
        }
    );

    database.printCustomers();
    database.printProducts();
}


// =============================================================================
// 8. FOREIGN KEY CASE
// =============================================================================

void demonstrateForeignKeys() {
    cout << "\n"
         << string(78, '=')
         << "\n2. Foreign-key and referential integrity\n"
         << string(78, '=')
         << '\n';

    OrderDatabase database = createCaseStudyDatabase();

    expectConstraintViolation(
        "Order references nonexistent customer",
        [&]() {
            database.createOrder(
                999,
                {{101, 1}}
            );
        }
    );

    const int orderId =
        database.createOrder(
            1,
            {
                {101, 2},
                {102, 1}
            }
        );

    cout << "Created valid order: "
         << orderId
         << '\n';

    database.printOrders();
    database.printProducts();

    expectConstraintViolation(
        "Customer deletion restricted by existing order",
        [&]() {
            database.deleteCustomer(1);
        }
    );
}


// =============================================================================
// 9. COMPOSITE CONSTRAINT
// =============================================================================

void demonstrateCompositeConstraint() {
    cout << "\n"
         << string(78, '=')
         << "\n3. Composite primary-key behavior\n"
         << string(78, '='
         )
         << '\n';

    OrderDatabase database = createCaseStudyDatabase();

    expectConstraintViolation(
        "Same product cannot occur twice in one order",
        [&]() {
            database.createOrder(
                1,
                {
                    {101, 1},
                    {101, 2}
                }
            );
        }
    );

    /*
     * The conceptual relational rule is:
     *
     *     PRIMARY KEY (order_id, product_id)
     *
     * The pair is unique, even though each component can repeat across
     * different orders.
     */
}


// =============================================================================
// 10. CHECK CONSTRAINTS AND EDGE CASES
// =============================================================================

void demonstrateCheckConstraints() {
    cout << "\n"
         << string(78, '=')
         << "\n4. CHECK constraints and edge cases\n"
         << string(78, '='
         )
         << '\n';

    OrderDatabase database = createCaseStudyDatabase();

    expectConstraintViolation(
        "Zero quantity",
        [&]() {
            database.createOrder(
                1,
                {{101, 0}}
            );
        }
    );

    expectConstraintViolation(
        "Negative quantity",
        [&]() {
            database.createOrder(
                1,
                {{101, -2}}
            );
        }
    );

    expectConstraintViolation(
        "Quantity greater than stock",
        [&]() {
            database.createOrder(
                1,
                {{101, 11}}
            );
        }
    );

    const int validOrder =
        database.createOrder(
            1,
            {{101, 10}}
        );

    cout << "Boundary case accepted: order "
         << validOrder
         << " consumes exactly all available keyboard stock.\n";

    cout << "Remaining keyboard stock: "
         << database.stockFor(101)
         << '\n';
}


// =============================================================================
// 11. TRANSACTION ROLLBACK
// =============================================================================

void demonstrateTransactionRollback() {
    cout << "\n"
         << string(78, '='
         )
         << "\n5. Atomicity and rollback\n"
         << string(78, '='
         )
         << '\n';

    OrderDatabase database = createCaseStudyDatabase();

    const int originalStock =
        database.stockFor(101);

    const size_t originalOrders =
        database.orderCount();

    try {
        database.transaction([&]() {
            database.createOrder(
                1,
                {{101, 2}}
            );

            /*
             * This second operation fails because the same transaction
             * attempts to purchase more stock than remains.
             */
            database.createOrder(
                2,
                {{101, 100}}
            );
        });
    } catch (const ConstraintViolation& error) {
        cout << "Transaction failed with "
             << constraintTypeToString(error.type())
             << ": "
             << error.what()
             << '\n';
    }

    /*
     * The first order must also disappear because the transaction is atomic.
     */
    cout << "Orders before transaction: "
         << originalOrders
         << '\n';

    cout << "Orders after rollback: "
         << database.orderCount()
         << '\n';

    cout << "Original stock: "
         << originalStock
         << '\n';

    cout << "Stock after rollback: "
         << database.stockFor(101)
         << '\n';

    if (
        database.orderCount() == originalOrders &&
        database.stockFor(101) == originalStock
    ) {
        cout << "PASS: atomic rollback preserved the original state.\n";
    } else {
        cout << "FAIL: rollback did not restore the original state.\n";
    }
}


// =============================================================================
// 12. SUCCESSFUL TRANSACTION
// =============================================================================

void demonstrateSuccessfulTransaction() {
    cout << "\n"
         << string(78, '='
         )
         << "\n6. Successful transaction\n"
         << string(78, '='
         )
         << '\n';

    OrderDatabase database = createCaseStudyDatabase();

    try {
        database.transaction([&]() {
            database.createOrder(
                1,
                {
                    {101, 1},
                    {103, 1}
                }
            );
        });

        cout << "Transaction committed successfully.\n";
    } catch (const exception& error) {
        cout << "Unexpected failure: "
             << error.what()
             << '\n';
    }

    database.printOrders();
    database.printProducts();
}


// =============================================================================
// 13. APPLICATION VALIDATION
// =============================================================================

void demonstrateValidationLayer() {
    cout << "\n"
         << string(78, '='
         )
         << "\n7. Application validation versus database constraints\n"
         << string(78, '='
         )
         << '\n';

    const auto errors =
        validateCustomerInput(
            "invalid-email",
            ""
        );

    cout << "Application validation errors:\n";

    for (const string& error : errors) {
        cout << " - "
             << error
             << '\n';
    }

    /*
     * Application validation gives users immediate and understandable
     * feedback. It cannot replace authoritative database constraints because
     * other clients, scripts, services, or future application versions may
     * write to the same database.
     */
}


// =============================================================================
// 14. SECURITY AND CONCURRENCY CONSIDERATIONS
// =============================================================================

void explainSecurityAndConcurrency() {
    cout << "\n"
         << string(78, '='
         )
         << "\n8. Security and concurrency considerations\n"
         << string(78, '='
         )
         << '\n';

    const vector<pair<string, string>> points = {
        {
            "Integrity is not authorization",
            "A CHECK or FOREIGN KEY does not determine who may perform an operation."
        },
        {
            "Race conditions",
            "A check-then-insert sequence can race when multiple clients act concurrently."
        },
        {
            "Database UNIQUE constraint",
            "A database-level UNIQUE rule provides authoritative duplicate prevention."
        },
        {
            "Transactions",
            "Related changes should be atomic when partial completion is invalid."
        },
        {
            "Parameterized SQL",
            "When using an actual SQL database, parameterized statements should be used to prevent SQL injection."
        },
        {
            "Least privilege",
            "Applications should receive only the database permissions required for their work."
        },
        {
            "Auditability",
            "Sensitive business systems may require audit records in addition to constraints."
        }
    };

    for (const auto& [topic, explanation] : points) {
        cout << topic
             << ": "
             << explanation
             << '\n';
    }
}


// =============================================================================
// 15. COMPLEXITY ANALYSIS
// =============================================================================

void explainComplexity() {
    cout << "\n"
         << string(78, '='
         )
         << "\n9. Complexity considerations\n"
         << string(78, '='
         )
         << '\n';

    cout << "Customer primary-key lookup: average O(1) with unordered_map.\n";
    cout << "Customer email uniqueness lookup: average O(1) with hash index.\n";
    cout << "Product SKU uniqueness lookup: average O(1) with hash index.\n";
    cout << "Order-item composite-key lookup: average O(1) with hash indexing.\n";
    cout << "A naive full-table constraint scan would be O(n).\n";
    cout << "Real database indexes reduce many uniqueness and lookup operations "
            "to logarithmic or near-constant behavior depending on index type.\n";

    /*
     * Complexity is only one part of database design. Indexes consume memory
     * and storage and make writes more expensive because each affected index
     * must be maintained.
     */
}


// =============================================================================
// 16. COMMON MISTAKES
// =============================================================================

void printCommonMistakes() {
    cout << "\n"
         << string(78, '='
         )
         << "\n10. Common implementation mistakes\n"
         << string(78, '='
         )
         << '\n';

    const vector<string> mistakes = {
        "Checking uniqueness in application code without a database constraint.",
        "Allowing negative monetary values or quantities.",
        "Allowing an order to reference a nonexistent customer.",
        "Deleting parent rows without deciding what should happen to child rows.",
        "Updating inventory outside the same atomic operation as order creation.",
        "Failing to protect against integer overflow in monetary calculations.",
        "Treating empty strings, zero, and NULL as interchangeable.",
        "Assuming one database engine has exactly the same constraint semantics as another.",
        "Adding constraints to existing data without first checking incompatible rows.",
        "Using constraints as a replacement for authentication and authorization."
    };

    for (size_t i = 0; i < mistakes.size(); ++i) {
        cout << i + 1
             << ". "
             << mistakes[i]
             << '\n';
    }
}


// =============================================================================
// 17. MAIN PROGRAM
// =============================================================================

int main() {
    try {
        cout << "CONSTRAINTS, DATA INTEGRITY, AND CONSTRAINT ENFORCEMENT\n";
        cout << "C++17 industry-style order-management case study\n";

        demonstrateBasicConstraints();
        demonstrateForeignKeys();
        demonstrateCompositeConstraint();
        demonstrateCheckConstraints();
        demonstrateTransactionRollback();
        demonstrateSuccessfulTransaction();
        demonstrateValidationLayer();
        explainSecurityAndConcurrency();
        explainComplexity();
        printCommonMistakes();

        cout << "\nCase study completed successfully.\n";
        return 0;
    } catch (const exception& error) {
        cerr << "Fatal error: "
             << error.what()
             << '\n';

        return 1;
    }
}
