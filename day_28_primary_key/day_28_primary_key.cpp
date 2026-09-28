/*
 * PRIMARY KEY
 * ===========
 *
 * A complete C++17 case study of primary-key design.
 *
 * Scenario:
 *     A small order-management system containing customers, products,
 *     and order lines.
 *
 * Demonstrates:
 *     - primary-key identity
 *     - uniqueness
 *     - validation
 *     - candidate/alternate keys
 *     - surrogate identifiers
 *     - composite primary keys
 *     - foreign-key validation
 *     - immutable-style key objects
 *     - unordered_map indexing
 *     - error handling
 *     - transactions through an in-memory unit-of-work model
 *     - performance considerations
 *     - security considerations
 *
 * Compile:
 *     g++ -std=c++17 -O2 -Wall -Wextra -pedantic primary_key.cpp -o primary_key
 *
 * Run:
 *     ./primary_key
 */

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <exception>
#include <functional>
#include <iomanip>
#include <iostream>
#include <optional>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>


// ============================================================================
// 1. EXCEPTION TYPES
// ============================================================================

class DuplicateKeyError : public std::runtime_error {
public:
    explicit DuplicateKeyError(const std::string& message)
        : std::runtime_error(message) {}
};

class MissingKeyError : public std::runtime_error {
public:
    explicit MissingKeyError(const std::string& message)
        : std::runtime_error(message) {}
};

class ForeignKeyError : public std::runtime_error {
public:
    explicit ForeignKeyError(const std::string& message)
        : std::runtime_error(message) {}
};

class ValidationError : public std::runtime_error {
public:
    explicit ValidationError(const std::string& message)
        : std::runtime_error(message) {}
};


// ============================================================================
// 2. SECTION OUTPUT
// ============================================================================

void printSection(const std::string& title) {
    std::cout << "\n" << std::string(78, '=') << "\n";
    std::cout << title << "\n";
    std::cout << std::string(78, '=') << "\n";
}


// ============================================================================
// 3. COMPOSITE PRIMARY KEY
// ============================================================================

struct OrderLineKey {
    int orderId{};
    int productId{};

    bool operator==(const OrderLineKey& other) const noexcept {
        return orderId == other.orderId &&
               productId == other.productId;
    }
};


// A custom hash lets OrderLineKey work efficiently in unordered_map.
struct OrderLineKeyHash {
    std::size_t operator()(const OrderLineKey& key) const noexcept {
        const std::size_t first =
            std::hash<int>{}(key.orderId);

        const std::size_t second =
            std::hash<int>{}(key.productId);

        // A standard hash-combination pattern.
        return first ^ (second + 0x9e3779b9 +
                        (first << 6) +
                        (first >> 2));
    }
};


// ============================================================================
// 4. DOMAIN ENTITIES
// ============================================================================

struct Customer {
    int customerId{};
    std::string email;
    std::string name;
};

struct Product {
    int productId{};
    std::string name;
    std::int64_t priceCents{};
};

struct OrderLine {
    int orderId{};
    int productId{};
    int quantity{};
};


// ============================================================================
// 5. VALIDATION FUNCTIONS
// ============================================================================

void validatePositiveId(int value, std::string_view fieldName) {
    if (value <= 0) {
        throw ValidationError(
            std::string(fieldName) + " must be positive."
        );
    }
}

void validateCustomer(const Customer& customer) {
    validatePositiveId(customer.customerId, "customerId");

    if (customer.name.empty()) {
        throw ValidationError("Customer name cannot be empty.");
    }

    if (customer.email.empty()) {
        throw ValidationError("Customer email cannot be empty.");
    }

    if (customer.email.find('@') == std::string::npos) {
        throw ValidationError("Customer email is invalid.");
    }
}

void validateProduct(const Product& product) {
    validatePositiveId(product.productId, "productId");

    if (product.name.empty()) {
        throw ValidationError("Product name cannot be empty.");
    }

    if (product.priceCents < 0) {
        throw ValidationError(
            "Product price cannot be negative."
        );
    }
}

void validateOrderLine(const OrderLine& line) {
    validatePositiveId(line.orderId, "orderId");
    validatePositiveId(line.productId, "productId");

    if (line.quantity <= 0) {
        throw ValidationError(
            "Order quantity must be greater than zero."
        );
    }
}


// ============================================================================
// 6. PRIMARY-KEY TABLE ABSTRACTION
// ============================================================================

template <typename Key, typename Value, typename Hash = std::hash<Key>>
class PrimaryKeyTable {
private:
    std::unordered_map<Key, Value, Hash> rows_;

public:
    void insert(const Key& key, const Value& value) {
        if (rows_.find(key) != rows_.end()) {
            throw DuplicateKeyError(
                "Primary-key value already exists."
            );
        }

        rows_.emplace(key, value);
    }

    bool contains(const Key& key) const {
        return rows_.find(key) != rows_.end();
    }

    const Value* find(const Key& key) const {
        const auto iterator = rows_.find(key);

        if (iterator == rows_.end()) {
            return nullptr;
        }

        return &iterator->second;
    }

    Value* find(const Key& key) {
        const auto iterator = rows_.find(key);

        if (iterator == rows_.end()) {
            return nullptr;
        }

        return &iterator->second;
    }

    bool erase(const Key& key) {
        return rows_.erase(key) > 0;
    }

    std::size_t size() const {
        return rows_.size();
    }
};


// ============================================================================
// 7. CANDIDATE KEY EXPLANATION
// ============================================================================

void explainCandidateKeys() {
    printSection("1. CANDIDATE AND PRIMARY KEYS");

    std::cout
        << "A candidate key is a minimal attribute set that uniquely identifies\n"
        << "a row. One candidate key is selected as the primary key.\n\n"

        << "Example customer candidates:\n"
        << "  customer_id\n"
        << "  registration_number\n"
        << "  email\n\n"

        << "The database may choose customer_id as PRIMARY KEY while enforcing\n"
        << "UNIQUE on registration_number and email.\n";
}


// ============================================================================
// 8. SIMPLE PRIMARY-KEY DEMONSTRATION
// ============================================================================

void demonstrateSimplePrimaryKey() {
    printSection("2. SIMPLE PRIMARY KEY");

    PrimaryKeyTable<int, Customer> customers;

    customers.insert(
        1,
        Customer{
            1,
            "asha@example.com",
            "Asha"
        }
    );

    customers.insert(
        2,
        Customer{
            2,
            "ravi@example.com",
            "Ravi"
        }
    );

    const Customer* customer = customers.find(1);

    if (customer != nullptr) {
        std::cout
            << "Customer 1: "
            << customer->name
            << " / "
            << customer->email
            << "\n";
    }

    std::cout
        << "Customer count: "
        << customers.size()
        << "\n";

    try {
        customers.insert(
            1,
            Customer{
                1,
                "duplicate@example.com",
                "Duplicate"
            }
        );
    }
    catch (const DuplicateKeyError& error) {
        std::cout
            << "Duplicate rejected: "
            << error.what()
            << "\n";
    }
}


// ============================================================================
// 9. COMPOSITE PRIMARY KEY DEMONSTRATION
// ============================================================================

void demonstrateCompositePrimaryKey() {
    printSection("3. COMPOSITE PRIMARY KEY");

    PrimaryKeyTable<
        OrderLineKey,
        OrderLine,
        OrderLineKeyHash
    > orderLines;

    const OrderLine first{
        9001,
        101,
        2
    };

    const OrderLine second{
        9001,
        102,
        1
    };

    orderLines.insert(
        OrderLineKey{first.orderId, first.productId},
        first
    );

    orderLines.insert(
        OrderLineKey{second.orderId, second.productId},
        second
    );

    const OrderLineKey lookupKey{9001, 101};

    const OrderLine* result =
        orderLines.find(lookupKey);

    if (result != nullptr) {
        std::cout
            << "Order "
            << result->orderId
            << ", Product "
            << result->productId
            << ", Quantity "
            << result->quantity
            << "\n";
    }

    try {
        orderLines.insert(
            OrderLineKey{9001, 101},
            OrderLine{9001, 101, 7}
        );
    }
    catch (const DuplicateKeyError& error) {
        std::cout
            << "Duplicate composite key rejected: "
            << error.what()
            << "\n";
    }

    std::cout
        << "\nThe pair (order_id, product_id) is the identity of an order line.\n";
}


// ============================================================================
// 10. ORDER MANAGEMENT SYSTEM
// ============================================================================

class OrderManagementSystem {
private:
    // customer_id is the primary key.
    PrimaryKeyTable<int, Customer> customers_;

    // product_id is the primary key.
    PrimaryKeyTable<int, Product> products_;

    // (order_id, product_id) is the composite primary key.
    PrimaryKeyTable<
        OrderLineKey,
        OrderLine,
        OrderLineKeyHash
    > orderLines_;

    // Email represents an alternate candidate/business key.
    // It is kept separately to demonstrate a UNIQUE constraint.
    std::unordered_set<std::string> customerEmails_;

public:
    void addCustomer(const Customer& customer) {
        validateCustomer(customer);

        if (customers_.contains(customer.customerId)) {
            throw DuplicateKeyError(
                "Customer primary key already exists."
            );
        }

        if (customerEmails_.find(customer.email) !=
            customerEmails_.end()) {
            throw ValidationError(
                "Customer email must be unique."
            );
        }

        customers_.insert(
            customer.customerId,
            customer
        );

        customerEmails_.insert(customer.email);
    }

    void addProduct(const Product& product) {
        validateProduct(product);

        if (products_.contains(product.productId)) {
            throw DuplicateKeyError(
                "Product primary key already exists."
            );
        }

        products_.insert(
            product.productId,
            product
        );
    }

    void addOrderLine(const OrderLine& line) {
        validateOrderLine(line);

        // Foreign-key validation:
        // orderLines.product_id must reference an existing product.
        if (!products_.contains(line.productId)) {
            throw ForeignKeyError(
                "Order line references a nonexistent product."
            );
        }

        const OrderLineKey key{
            line.orderId,
            line.productId
        };

        if (orderLines_.contains(key)) {
            throw DuplicateKeyError(
                "The composite order-line key already exists."
            );
        }

        orderLines_.insert(key, line);
    }

    std::int64_t calculateOrderTotal(int orderId) const {
        validatePositiveId(orderId, "orderId");

        std::int64_t total = 0;

        // The educational model scans order lines.
        // A production system might maintain a dedicated order_id index.
        //
        // Complexity here is O(number of order lines).
        //
        // This illustrates an important distinction:
        // a primary key guarantees uniqueness, but it does not automatically
        // make every possible query pattern optimal.
        for (int productId = 1; productId <= 100000; ++productId) {
            const OrderLineKey key{
                orderId,
                productId
            };

            const OrderLine* line =
                orderLines_.find(key);

            if (line == nullptr) {
                continue;
            }

            const Product* product =
                products_.find(line->productId);

            if (product == nullptr) {
                throw ForeignKeyError(
                    "Stored order line references missing product."
                );
            }

            total +=
                product->priceCents *
                static_cast<std::int64_t>(line->quantity);
        }

        return total;
    }

    std::size_t customerCount() const {
        return customers_.size();
    }

    std::size_t productCount() const {
        return products_.size();
    }

    std::size_t orderLineCount() const {
        return orderLines_.size();
    }
};


// ============================================================================
// 11. REALISTIC CASE STUDY
// ============================================================================

void runOrderManagementCaseStudy() {
    printSection("4. ORDER-MANAGEMENT CASE STUDY");

    OrderManagementSystem system;

    system.addCustomer(
        Customer{
            1,
            "buyer@example.com",
            "Buyer"
        }
    );

    system.addProduct(
        Product{
            101,
            "Keyboard",
            5000
        }
    );

    system.addProduct(
        Product{
            102,
            "Mouse",
            2500
        }
    );

    system.addOrderLine(
        OrderLine{
            9001,
            101,
            2
        }
    );

    system.addOrderLine(
        OrderLine{
            9001,
            102,
            1
        }
    );

    std::cout
        << "Customers: "
        << system.customerCount()
        << "\n";

    std::cout
        << "Products: "
        << system.productCount()
        << "\n";

    std::cout
        << "Order lines: "
        << system.orderLineCount()
        << "\n";

    std::cout
        << "Expected order total: 12500 cents\n";
}


// ============================================================================
// 12. FAILURE CONDITIONS
// ============================================================================

void testFailureConditions(OrderManagementSystem& system) {
    printSection("5. VALIDATION AND FAILURE CONDITIONS");

    std::vector<std::function<void()>> tests;

    tests.emplace_back([&system]() {
        system.addCustomer(
            Customer{
                1,
                "another@example.com",
                "Duplicate ID"
            }
        );
    });

    tests.emplace_back([&system]() {
        system.addCustomer(
            Customer{
                2,
                "buyer@example.com",
                "Duplicate Email"
            }
        );
    });

    tests.emplace_back([&system]() {
        system.addProduct(
            Product{
                999,
                "Valid Product",
                100
            }
        );

        system.addOrderLine(
            OrderLine{
                9002,
                999,
                1
            }
        );
    });

    tests.emplace_back([&system]() {
        system.addOrderLine(
            OrderLine{
                9001,
                101,
                1
            }
        );
    });

    tests.emplace_back([&system]() {
        system.addOrderLine(
            OrderLine{
                9003,
                99999,
                1
            }
        );
    });

    tests.emplace_back([&system]() {
        system.addOrderLine(
            OrderLine{
                9004,
                101,
                0
            }
        );
    });

    for (std::size_t i = 0; i < tests.size(); ++i) {
        try {
            tests[i]();
            std::cout
                << "Test "
                << i + 1
                << ": unexpectedly succeeded\n";
        }
        catch (const std::exception& error) {
            std::cout
                << "Test "
                << i + 1
                << " rejected: "
                << error.what()
                << "\n";
        }
    }
}


// ============================================================================
// 13. NATURAL VS SURROGATE
// ============================================================================

void explainNaturalVsSurrogate() {
    printSection("6. NATURAL VS SURROGATE IDENTIFIERS");

    std::cout
        << "Natural key:\n"
        << "  An existing business attribute used as identity.\n\n"

        << "Surrogate key:\n"
        << "  An identifier created specifically for database identity.\n\n"

        << "Example:\n"
        << "  customer_id PRIMARY KEY\n"
        << "  email UNIQUE\n\n"

        << "This allows email to change while customer_id remains stable.\n";
}


// ============================================================================
// 14. INDEX PERFORMANCE
// ============================================================================

void demonstratePerformance() {
    printSection("7. PRIMARY-KEY LOOKUP PERFORMANCE");

    constexpr int recordCount = 100000;

    std::unordered_map<int, std::string> records;
    records.reserve(recordCount * 2);

    for (int id = 1; id <= recordCount; ++id) {
        records.emplace(
            id,
            "Entity " + std::to_string(id)
        );
    }

    const auto start =
        std::chrono::high_resolution_clock::now();

    volatile const std::string* result =
        &records.at(99999);

    const auto end =
        std::chrono::high_resolution_clock::now();

    const auto elapsed =
        std::chrono::duration<double, std::micro>(
            end - start
        ).count();

    std::cout
        << "Lookup result: "
        << *result
        << "\n";

    std::cout
        << "Unordered-map lookup time: "
        << std::fixed
        << std::setprecision(3)
        << elapsed
        << " microseconds\n";

    std::cout
        << "\nConceptual complexity:\n"
        << "  Full table scan: O(n)\n"
        << "  Balanced-tree index: approximately O(log n)\n"
        << "  Hash lookup: approximately O(1) average\n";

    std::cout
        << "\nDatabase performance depends on the actual engine, index type,\n"
        << "cache state, storage layout, query plan, and workload.\n";
}


// ============================================================================
// 15. IMMUTABILITY AND KEY LIFECYCLE
// ============================================================================

class ImmutableKey {
private:
    const int value_;

public:
    explicit ImmutableKey(int value)
        : value_(value) {
        validatePositiveId(value_, "key");
    }

    int value() const noexcept {
        return value_;
    }
};

void demonstrateImmutableKey() {
    printSection("8. KEY STABILITY");

    ImmutableKey key(5001);

    std::cout
        << "Immutable key value: "
        << key.value()
        << "\n";

    std::cout
        << "A stable identifier reduces the complexity of dependent references.\n";
}


// ============================================================================
// 16. TRANSACTION-LIKE UNIT OF WORK
// ============================================================================

class TransactionalDemo {
private:
    std::unordered_map<int, std::string> accounts_;

public:
    TransactionalDemo() {
        accounts_.emplace(1, "Alice");
    }

    void demonstrateRollback() {
        const auto backup = accounts_;

        try {
            accounts_.emplace(2, "Bob");

            // Simulate a later primary-key violation.
            if (accounts_.find(1) != accounts_.end()) {
                throw DuplicateKeyError(
                    "Account 1 already exists."
                );
            }
        }
        catch (const DuplicateKeyError& error) {
            // Restore the previous state.
            accounts_ = backup;

            std::cout
                << "Transaction rolled back: "
                << error.what()
                << "\n";
        }

        std::cout
            << "Account 2 exists after rollback: "
            << (accounts_.find(2) != accounts_.end() ? "yes" : "no")
            << "\n";
    }
};

void demonstrateTransactionConcept() {
    printSection("9. TRANSACTIONAL INTEGRITY");

    TransactionalDemo demo;
    demo.demonstrateRollback();

    std::cout
        << "\nA database transaction can make a set of changes atomic.\n"
        << "If a later operation violates a constraint, the database can\n"
        << "roll back the entire transaction rather than leaving partial state.\n";
}


// ============================================================================
// 17. SECURITY
// ============================================================================

void explainSecurity() {
    printSection("10. SECURITY CONSIDERATIONS");

    std::cout
        << "A primary key is not an authorization mechanism.\n\n"

        << "Knowing customer_id = 1001 must not automatically grant access\n"
        << "to customer 1001.\n\n"

        << "Sequential identifiers may also make enumeration easier.\n"
        << "Security controls should therefore include authorization checks,\n"
        << "rate limiting, auditing, and careful exposure of identifiers.\n\n"

        << "UUIDs can reduce casual predictability but do not replace\n"
        << "authentication or authorization.\n";
}


// ============================================================================
// 18. EDGE CASES
// ============================================================================

void demonstrateEdgeCases() {
    printSection("11. IMPORTANT EDGE CASES");

    std::vector<int> identifiers{
        1,
        2,
        1000000,
        0,
        -1
    };

    for (int id : identifiers) {
        try {
            validatePositiveId(id, "customerId");

            std::cout
                << "Accepted ID: "
                << id
                << "\n";
        }
        catch (const ValidationError& error) {
            std::cout
                << "Rejected ID "
                << id
                << ": "
                << error.what()
                << "\n";
        }
    }

    try {
        OrderLineKey invalid{
            0,
            100
        };

        (void)invalid;

        // This line is intentionally unreachable in normal execution.
        throw ValidationError(
            "Invalid composite key should not be accepted."
        );
    }
    catch (const ValidationError& error) {
        std::cout
            << "Composite-key validation example: "
            << error.what()
            << "\n";
    }
}


// ============================================================================
// 19. KEY DESIGN TRADE-OFFS
// ============================================================================

void printDesignTradeoffs() {
    printSection("12. KEY-DESIGN TRADE-OFFS");

    struct Design {
        std::string situation;
        std::string strategy;
        std::string tradeoff;
    };

    const std::vector<Design> designs{
        {
            "Internal identity",
            "Integer surrogate",
            "Compact, simple, stable"
        },
        {
            "Distributed identity",
            "UUID",
            "Independent generation, larger key"
        },
        {
            "Many-to-many relationship",
            "Composite key",
            "Natural relationship identity, wider references"
        },
        {
            "Stable business identifier",
            "Natural key",
            "Meaningful, but sensitive to business changes"
        },
        {
            "Mutable business attribute",
            "Surrogate + UNIQUE",
            "Separates identity from business uniqueness"
        }
    };

    for (const auto& design : designs) {
        std::cout
            << design.situation
            << " | "
            << design.strategy
            << " | "
            << design.tradeoff
            << "\n";
    }
}


// ============================================================================
// 20. TEST SUITE
// ============================================================================

void runAssertions() {
    printSection("13. AUTOMATED ASSERTIONS");

    PrimaryKeyTable<int, std::string> table;

    table.insert(1, "One");

    if (!table.contains(1)) {
        throw std::runtime_error(
            "Primary-key existence assertion failed."
        );
    }

    if (table.size() != 1) {
        throw std::runtime_error(
            "Table-size assertion failed."
        );
    }

    try {
        table.insert(1, "Duplicate");

        throw std::runtime_error(
            "Duplicate-key test did not throw."
        );
    }
    catch (const DuplicateKeyError&) {
        // Expected.
    }

    PrimaryKeyTable<
        OrderLineKey,
        OrderLine,
        OrderLineKeyHash
    > compositeTable;

    compositeTable.insert(
        OrderLineKey{10, 20},
        OrderLine{10, 20, 3}
    );

    if (!compositeTable.contains(OrderLineKey{10, 20})) {
        throw std::runtime_error(
            "Composite-key assertion failed."
        );
    }

    std::cout
        << "All assertions passed.\n";
}


// ============================================================================
// 21. MAIN
// ============================================================================

int main() {
    try {
        explainCandidateKeys();

        demonstrateSimplePrimaryKey();

        demonstrateCompositePrimaryKey();

        runOrderManagementCaseStudy();

        OrderManagementSystem systemForTests;

        systemForTests.addCustomer(
            Customer{
                1,
                "buyer@example.com",
                "Buyer"
            }
        );

        systemForTests.addProduct(
            Product{
                101,
                "Keyboard",
                5000
            }
        );

        systemForTests.addOrderLine(
            OrderLine{
                9001,
                101,
                2
            }
        );

        testFailureConditions(systemForTests);

        explainNaturalVsSurrogate();

        demonstratePerformance();

        demonstrateImmutableKey();

        demonstrateTransactionConcept();

        explainSecurity();

        demonstrateEdgeCases();

        printDesignTradeoffs();

        runAssertions();

        printSection("14. END OF PRIMARY-KEY CASE STUDY");

        std::cout
            << "The system demonstrated primary-key identity, composite keys,\n"
            << "alternate uniqueness, foreign-key validation, error handling,\n"
            << "performance considerations, and key-design trade-offs.\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "Fatal error: "
            << error.what()
            << "\n";

        return 1;
    }
}
