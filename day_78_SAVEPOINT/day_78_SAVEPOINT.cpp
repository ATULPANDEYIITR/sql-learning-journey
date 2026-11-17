#include <algorithm>
#include <cassert>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

/*
 * SAVEPOINT: Partial Rollback and Nested Transaction Patterns
 *
 * C++17 repository transaction and governance simulation.
 *
 * Features:
 * - Transaction-local state
 * - Savepoint stack
 * - Partial rollback
 * - Savepoint release
 * - Nested transactional operations
 * - Atomic commit
 * - Optimistic concurrency control
 * - Inventory and account validation
 *
 * Compile:
 * g++ -std=c++17 -Wall -Wextra -pedantic savepoint.cpp -o savepoint
 */

using Money = std::int64_t;

enum class TransactionStatus {
    Active,
    Committed,
    RolledBack
};

struct Product {
    int id;
    std::string name;
    int stock;
    Money price;
};

struct Account {
    int id;
    std::string owner;
    Money balance;
};

struct Order {
    int id;
    int accountId;
    int productId;
    int quantity;
    Money amount;
    std::string status;
};

struct DatabaseState {
    std::map<int, Product> products;
    std::map<int, Account> accounts;
    std::map<int, Order> orders;
    int nextOrderId = 1;
};

class TransactionError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class InsufficientInventory : public TransactionError {
public:
    using TransactionError::TransactionError;
};

class InsufficientFunds : public TransactionError {
public:
    using TransactionError::TransactionError;
};

class SavepointNotFound : public TransactionError {
public:
    using TransactionError::TransactionError;
};

class InvalidTransactionState : public TransactionError {
public:
    using TransactionError::TransactionError;
};

class ConcurrencyConflict : public TransactionError {
public:
    using TransactionError::TransactionError;
};

class Database;

class Transaction {
private:
    struct Savepoint {
        std::string name;
        DatabaseState snapshot;
    };

    Database& database;
    DatabaseState workingState;
    std::vector<Savepoint> savepoints;
    TransactionStatus status;
    std::uint64_t baseVersion;

    void ensureActive() const {
        if (status != TransactionStatus::Active) {
            throw InvalidTransactionState(
                "Transaction is not active."
            );
        }
    }

    std::size_t findSavepoint(const std::string& name) const {
        for (std::size_t i = savepoints.size(); i > 0; --i) {
            if (savepoints[i - 1].name == name) {
                return i - 1;
            }
        }

        throw SavepointNotFound(
            "Savepoint not found: " + name
        );
    }

public:
    explicit Transaction(Database& db);

    TransactionStatus getStatus() const {
        return status;
    }

    const DatabaseState& state() const {
        return workingState;
    }

    void createSavepoint(const std::string& name) {
        ensureActive();

        if (
            name.empty() ||
            name.size() > 63 ||
            !std::all_of(
                name.begin(),
                name.end(),
                [](unsigned char c) {
                    return std::isalnum(c) || c == '_';
                }
            )
        ) {
            throw std::invalid_argument(
                "Invalid savepoint identifier."
            );
        }

        savepoints.push_back({name, workingState});

        std::cout << "SAVEPOINT " << name << " created\n";
    }

    void rollbackTo(const std::string& name) {
        ensureActive();

        const std::size_t index = findSavepoint(name);

        workingState = savepoints[index].snapshot;

        // The named savepoint remains active.
        savepoints.erase(
            savepoints.begin() + index + 1,
            savepoints.end()
        );

        std::cout << "ROLLBACK TO SAVEPOINT "
                  << name << '\n';
    }

    void release(const std::string& name) {
        ensureActive();

        const std::size_t index = findSavepoint(name);

        // Releasing an outer savepoint also invalidates
        // savepoints created after it.
        savepoints.erase(
            savepoints.begin() + index,
            savepoints.end()
        );

        std::cout << "RELEASE SAVEPOINT "
                  << name << '\n';
    }

    Order createOrder(
        int accountId,
        int productId,
        int quantity
    ) {
        ensureActive();

        if (quantity <= 0) {
            throw std::invalid_argument(
                "Quantity must be positive."
            );
        }

        auto accountIt = workingState.accounts.find(accountId);
        auto productIt = workingState.products.find(productId);

        if (accountIt == workingState.accounts.end()) {
            throw TransactionError("Account not found.");
        }

        if (productIt == workingState.products.end()) {
            throw TransactionError("Product not found.");
        }

        Account& account = accountIt->second;
        Product& product = productIt->second;

        if (product.stock < quantity) {
            throw InsufficientInventory(
                "Insufficient product inventory."
            );
        }

        if (
            product.price >
            std::numeric_limits<Money>::max() / quantity
        ) {
            throw TransactionError(
                "Order amount overflow."
            );
        }

        const Money amount = product.price * quantity;

        if (account.balance < amount) {
            throw InsufficientFunds(
                "Insufficient account balance."
            );
        }

        product.stock -= quantity;
        account.balance -= amount;

        Order order{
            workingState.nextOrderId++,
            accountId,
            productId,
            quantity,
            amount,
            "CONFIRMED"
        };

        workingState.orders.emplace(order.id, order);

        return order;
    }

    void commit();

    void rollback() {
        ensureActive();

        savepoints.clear();
        status = TransactionStatus::RolledBack;

        std::cout << "FULL TRANSACTION ROLLBACK\n";
    }
};

class Database {
private:
    DatabaseState committedState;
    std::uint64_t version = 0;

    friend class Transaction;

public:
    Database() {
        committedState.products.emplace(
            101,
            Product{
                101, "Enterprise Laptop", 10, 7500000
            }
        );

        committedState.products.emplace(
            102,
            Product{
                102, "Wireless Keyboard", 20, 250000
            }
        );

        committedState.products.emplace(
            103,
            Product{
                103, "External SSD", 5, 650000
            }
        );

        committedState.accounts.emplace(
            1,
            Account{
                1, "Corporate Procurement", 20000000
            }
        );

        committedState.accounts.emplace(
            2,
            Account{
                2, "Regional Procurement", 1000000
            }
        );
    }

    Transaction begin() {
        return Transaction(*this);
    }

    void display() const {
        std::cout << "\nCOMMITTED DATABASE STATE\n";

        std::cout << "Version: " << version << '\n';

        for (const auto& [id, product] :
             committedState.products) {
            std::cout
                << "Product " << id
                << ": " << product.name
                << ", stock=" << product.stock
                << '\n';
        }

        for (const auto& [id, account] :
             committedState.accounts) {
            std::cout
                << "Account " << id
                << ": " << account.owner
                << ", balance="
                << std::fixed << std::setprecision(2)
                << static_cast<double>(account.balance) / 100
                << '\n';
        }

        for (const auto& [id, order] :
             committedState.orders) {
            std::cout
                << "Order " << id
                << ", quantity=" << order.quantity
                << ", amount=" << order.amount
                << ", status=" << order.status
                << '\n';
        }
    }

    std::size_t orderCount() const {
        return committedState.orders.size();
    }
};

Transaction::Transaction(Database& db)
    : database(db),
      workingState(db.committedState),
      status(TransactionStatus::Active),
      baseVersion(db.version) {}

void Transaction::commit() {
    ensureActive();

    if (database.version != baseVersion) {
        throw ConcurrencyConflict(
            "Database changed after transaction began."
        );
    }

    database.committedState = workingState;
    ++database.version;

    savepoints.clear();
    status = TransactionStatus::Committed;

    std::cout << "TRANSACTION COMMITTED\n";
}

void demonstratePartialRollback(Database& database) {
    std::cout << "\n1. PARTIAL ROLLBACK\n";

    Transaction tx = database.begin();

    tx.createSavepoint("initial");

    Order first = tx.createOrder(1, 101, 1);

    std::cout << "Order created: " << first.id << '\n';

    tx.createSavepoint("optional");

    try {
        tx.createOrder(1, 103, 100);
    } catch (const InsufficientInventory& error) {
        std::cout << "Optional operation failed: "
                  << error.what() << '\n';

        tx.rollbackTo("optional");
    }

    tx.commit();
}

void demonstrateNestedTransaction(Database& database) {
    std::cout << "\n2. NESTED TRANSACTION\n";

    Transaction tx = database.begin();

    tx.createSavepoint("outer");

    tx.createOrder(1, 102, 2);

    tx.createSavepoint("inner");

    try {
        tx.createOrder(2, 101, 1);
    } catch (const InsufficientFunds& error) {
        std::cout << "Inner operation failed: "
                  << error.what() << '\n';

        tx.rollbackTo("inner");
    }

    tx.release("inner");
    tx.commit();
}

void demonstrateFullRollback(Database& database) {
    std::cout << "\n3. FULL ROLLBACK\n";

    Transaction tx = database.begin();

    tx.createOrder(1, 102, 1);
    tx.rollback();

    std::cout << "Transaction status: "
              << (
                  tx.getStatus() ==
                  TransactionStatus::RolledBack
                  ? "ROLLED BACK"
                  : "OTHER"
              )
              << '\n';
}

void demonstrateConcurrency(Database& database) {
    std::cout << "\n4. CONCURRENCY CONFLICT\n";

    Transaction first = database.begin();
    Transaction second = database.begin();

    first.createOrder(1, 102, 1);
    second.createOrder(1, 102, 1);

    first.commit();

    try {
        second.commit();
    } catch (const ConcurrencyConflict& error) {
        std::cout << "Conflict detected: "
                  << error.what() << '\n';

        second.rollback();
    }
}

void demonstrateRelease(Database& database) {
    std::cout << "\n5. SAVEPOINT RELEASE\n";

    Transaction tx = database.begin();

    tx.createSavepoint("temporary");
    tx.release("temporary");

    try {
        tx.rollbackTo("temporary");
    } catch (const SavepointNotFound& error) {
        std::cout << "Expected failure: "
                  << error.what() << '\n';
    }

    tx.commit();
}

void runAssertions() {
    Database database;

    {
        Transaction tx = database.begin();

        tx.createSavepoint("before");

        tx.createOrder(1, 102, 1);

        tx.createSavepoint("after");

        tx.createOrder(1, 103, 1);

        tx.rollbackTo("after");

        assert(tx.state().orders.size() == 1);
        assert(tx.state().products.at(103).stock == 5);

        tx.commit();
    }

    assert(database.orderCount() == 1);

    {
        Transaction tx = database.begin();
        tx.createOrder(1, 102, 1);
        tx.rollback();
    }

    assert(database.orderCount() == 1);

    std::cout << "\nALL ASSERTIONS PASSED\n";
}

int main() {
    try {
        Database database;

        demonstratePartialRollback(database);
        demonstrateNestedTransaction(database);
        demonstrateFullRollback(database);
        demonstrateRelease(database);
        demonstrateConcurrency(database);

        database.display();

        runAssertions();

    } catch (const std::exception& error) {
        std::cerr << "Fatal error: "
                  << error.what() << '\n';

        return 1;
    }

    return 0;
}
