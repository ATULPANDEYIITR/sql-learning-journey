#include <algorithm>
#include <atomic>
#include <cstdint>
#include <exception>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Concurrency, Locks, Concurrent Transactions, and Race Conditions.
 *
 * C++17 implementation:
 * - Mutex and shared_mutex
 * - Atomic operations
 * - RAII-based lock management
 * - Deadlock prevention
 * - Concurrent banking transactions
 * - Optimistic version checking
 * - Idempotency
 * - Invariant validation
 */

enum class TransactionStatus {
    Committed,
    Rejected,
    RolledBack
};

struct TransactionResult {
    std::string id;
    TransactionStatus status;
    std::string message;
};

class TransactionException : public std::runtime_error {
public:
    explicit TransactionException(const std::string& message)
        : std::runtime_error(message) {}
};


class Account {
private:
    std::string id_;
    std::int64_t balance_;
    std::uint64_t version_ = 0;

    mutable std::mutex mutex_;

    friend class BankingEngine;

public:
    Account(std::string id, std::int64_t balance)
        : id_(std::move(id)), balance_(balance) {

        if (id_.empty()) {
            throw std::invalid_argument("Account ID cannot be empty");
        }

        if (balance_ < 0) {
            throw std::invalid_argument("Negative initial balance");
        }
    }

    Account(const Account&) = delete;
    Account& operator=(const Account&) = delete;

    std::string id() const {
        return id_;
    }

    std::int64_t balance() const {
        std::lock_guard<std::mutex> guard(mutex_);
        return balance_;
    }

    std::uint64_t version() const {
        std::lock_guard<std::mutex> guard(mutex_);
        return version_;
    }
};


class BankingEngine {
private:
    std::unordered_map<std::string, std::shared_ptr<Account>> accounts_;

    mutable std::shared_mutex registry_mutex_;
    std::mutex transaction_mutex_;

    std::unordered_map<std::string, TransactionResult> processed_;

    std::atomic<std::uint64_t> sequence_{0};

    std::shared_ptr<Account> findAccount(const std::string& id) const {
        std::shared_lock<std::shared_mutex> guard(registry_mutex_);

        auto it = accounts_.find(id);

        if (it == accounts_.end()) {
            throw TransactionException("Account not found: " + id);
        }

        return it->second;
    }

public:
    void addAccount(
        const std::string& id,
        std::int64_t balance
    ) {
        auto account = std::make_shared<Account>(id, balance);

        std::unique_lock<std::shared_mutex> guard(registry_mutex_);

        if (accounts_.count(id)) {
            throw TransactionException("Duplicate account");
        }

        accounts_.emplace(id, std::move(account));
    }

    TransactionResult transfer(
        const std::string& sourceId,
        const std::string& destinationId,
        std::int64_t amount,
        const std::string& idempotencyKey
    ) {
        if (sourceId == destinationId) {
            throw std::invalid_argument(
                "Source and destination must differ"
            );
        }

        if (amount <= 0) {
            throw std::invalid_argument("Amount must be positive");
        }

        if (idempotencyKey.empty()) {
            throw std::invalid_argument(
                "Idempotency key cannot be empty"
            );
        }

        // The transaction registry serializes duplicate-key handling.
        std::lock_guard<std::mutex> transactionGuard(
            transaction_mutex_
        );

        auto previous = processed_.find(idempotencyKey);

        if (previous != processed_.end()) {
            return previous->second;
        }

        auto source = findAccount(sourceId);
        auto destination = findAccount(destinationId);

        // std::scoped_lock uses deadlock-avoidance locking.
        std::scoped_lock accountGuard(
            source->mutex_,
            destination->mutex_
        );

        if (source->balance_ < amount) {
            TransactionResult result{
                "TX-" + std::to_string(++sequence_),
                TransactionStatus::Rejected,
                "Insufficient funds"
            };

            processed_.emplace(idempotencyKey, result);

            return result;
        }

        // Prevent signed integer overflow before performing updates.
        if (
            destination->balance_ >
            INT64_MAX - amount
        ) {
            throw TransactionException(
                "Destination balance overflow"
            );
        }

        const auto oldSource = source->balance_;
        const auto oldDestination = destination->balance_;

        try {
            source->balance_ -= amount;
            destination->balance_ += amount;

            ++source->version_;
            ++destination->version_;

            if (source->balance_ < 0) {
                throw TransactionException(
                    "Balance invariant violated"
                );
            }

        } catch (...) {
            source->balance_ = oldSource;
            destination->balance_ = oldDestination;
            throw;
        }

        TransactionResult result{
            "TX-" + std::to_string(++sequence_),
            TransactionStatus::Committed,
            "Transfer committed"
        };

        processed_.emplace(idempotencyKey, result);

        return result;
    }

    std::int64_t totalBalance() const {
        std::vector<std::shared_ptr<Account>> snapshot;

        {
            std::shared_lock<std::shared_mutex> guard(
                registry_mutex_
            );

            for (const auto& entry : accounts_) {
                snapshot.push_back(entry.second);
            }
        }

        // Lock every account using a single deadlock-safe operation.
        std::vector<std::unique_lock<std::mutex>> locks;

        locks.reserve(snapshot.size());

        // Sorting provides predictable lock acquisition order.
        std::sort(
            snapshot.begin(),
            snapshot.end(),
            [](const auto& a, const auto& b) {
                return a->id_ < b->id_;
            }
        );

        for (const auto& account : snapshot) {
            locks.emplace_back(account->mutex_);
        }

        std::int64_t total = 0;

        for (const auto& account : snapshot) {
            if (account->balance_ > INT64_MAX - total) {
                throw TransactionException(
                    "Total balance overflow"
                );
            }

            total += account->balance_;
        }

        return total;
    }

    std::int64_t getBalance(const std::string& id) const {
        return findAccount(id)->balance();
    }
};


/*
 * Optimistic concurrency:
 * updates are accepted only when the version has not changed.
 */
class VersionedBalance {
private:
    mutable std::mutex mutex_;
    std::int64_t balance_;
    std::uint64_t version_ = 0;

public:
    explicit VersionedBalance(std::int64_t balance)
        : balance_(balance) {

        if (balance < 0) {
            throw std::invalid_argument("Invalid balance");
        }
    }

    std::pair<std::int64_t, std::uint64_t> read() const {
        std::lock_guard<std::mutex> guard(mutex_);

        return {balance_, version_};
    }

    void compareAndSet(
        std::uint64_t expectedVersion,
        std::int64_t newBalance
    ) {
        if (newBalance < 0) {
            throw std::invalid_argument("Invalid new balance");
        }

        std::lock_guard<std::mutex> guard(mutex_);

        if (version_ != expectedVersion) {
            throw TransactionException(
                "Optimistic concurrency conflict"
            );
        }

        balance_ = newBalance;
        ++version_;
    }
};


/*
 * Demonstrates the difference between atomic and unsynchronized
 * shared-state updates.
 */
void demonstrateCounters() {
    std::cout << "\n--- Atomic Counter ---\n";

    std::atomic<int> counter{0};

    constexpr int THREADS = 8;
    constexpr int ITERATIONS = 10000;

    std::vector<std::thread> workers;

    for (int i = 0; i < THREADS; ++i) {
        workers.emplace_back([&counter]() {
            for (int j = 0; j < ITERATIONS; ++j) {
                counter.fetch_add(1, std::memory_order_relaxed);
            }
        });
    }

    for (auto& worker : workers) {
        worker.join();
    }

    std::cout << "Expected: "
              << THREADS * ITERATIONS << '\n';

    std::cout << "Actual: "
              << counter.load() << '\n';

    if (counter != THREADS * ITERATIONS) {
        throw TransactionException("Atomic counter failed");
    }
}


void demonstrateConcurrentTransfers() {
    std::cout << "\n--- Concurrent Banking Transactions ---\n";

    BankingEngine bank;

    bank.addAccount("A", 100000);
    bank.addAccount("B", 100000);
    bank.addAccount("C", 50000);

    const auto initial = bank.totalBalance();

    constexpr int TRANSACTIONS = 1000;

    std::atomic<int> committed{0};

    std::vector<std::thread> workers;

    for (int i = 0; i < TRANSACTIONS; ++i) {
        workers.emplace_back([&bank, &committed, i]() {
            try {
                TransactionResult result;

                if (i % 2 == 0) {
                    result = bank.transfer(
                        "A",
                        "B",
                        10,
                        "TX-" + std::to_string(i)
                    );
                } else {
                    result = bank.transfer(
                        "B",
                        "A",
                        10,
                        "TX-" + std::to_string(i)
                    );
                }

                if (result.status == TransactionStatus::Committed) {
                    committed.fetch_add(
                        1,
                        std::memory_order_relaxed
                    );
                }

            } catch (const std::exception& error) {
                std::cerr << "Transaction failure: "
                          << error.what() << '\n';
            }
        });
    }

    for (auto& worker : workers) {
        worker.join();
    }

    const auto finalBalance = bank.totalBalance();

    std::cout << "Committed: " << committed << '\n';
    std::cout << "Initial total: " << initial << '\n';
    std::cout << "Final total: " << finalBalance << '\n';

    std::cout << "A: " << bank.getBalance("A") << '\n';
    std::cout << "B: " << bank.getBalance("B") << '\n';
    std::cout << "C: " << bank.getBalance("C") << '\n';

    if (initial != finalBalance) {
        throw TransactionException(
            "Balance conservation violated"
        );
    }

    if (
        bank.getBalance("A") < 0 ||
        bank.getBalance("B") < 0 ||
        bank.getBalance("C") < 0
    ) {
        throw TransactionException(
            "Negative account balance detected"
        );
    }
}


void demonstrateIdempotency() {
    std::cout << "\n--- Idempotency ---\n";

    BankingEngine bank;

    bank.addAccount("SOURCE", 1000);
    bank.addAccount("TARGET", 500);

    auto first = bank.transfer(
        "SOURCE",
        "TARGET",
        100,
        "PAYMENT-001"
    );

    auto second = bank.transfer(
        "SOURCE",
        "TARGET",
        100,
        "PAYMENT-001"
    );

    std::cout << "First: " << first.id << '\n';
    std::cout << "Second: " << second.id << '\n';

    if (first.id != second.id) {
        throw TransactionException("Idempotency failed");
    }

    std::cout << "Source: "
              << bank.getBalance("SOURCE") << '\n';

    std::cout << "Target: "
              << bank.getBalance("TARGET") << '\n';
}


void demonstrateOptimisticLocking() {
    std::cout << "\n--- Optimistic Locking ---\n";

    VersionedBalance account(1000);

    auto firstRead = account.read();
    auto secondRead = account.read();

    account.compareAndSet(firstRead.second, 1200);

    try {
        account.compareAndSet(secondRead.second, 1500);
    } catch (const TransactionException& error) {
        std::cout << "Stale update rejected: "
                  << error.what() << '\n';
    }

    auto current = account.read();

    std::cout << "Balance: " << current.first << '\n';
    std::cout << "Version: " << current.second << '\n';
}


void demonstrateSharedMutex() {
    std::cout << "\n--- Shared Read Access ---\n";

    std::shared_mutex mutex;
    int sharedValue = 100;

    auto reader = [&]() {
        std::shared_lock<std::shared_mutex> guard(mutex);

        std::cout << "Read value: "
                  << sharedValue << '\n';
    };

    auto writer = [&]() {
        std::unique_lock<std::shared_mutex> guard(mutex);

        sharedValue = 200;
    };

    std::thread first(reader);
    std::thread second(reader);
    std::thread third(writer);

    first.join();
    second.join();
    third.join();

    std::cout << "Final value: " << sharedValue << '\n';
}


int main() {
    try {
        std::cout << "CONCURRENCY AND TRANSACTION ENGINE\n";

        demonstrateCounters();
        demonstrateConcurrentTransfers();
        demonstrateIdempotency();
        demonstrateOptimisticLocking();
        demonstrateSharedMutex();

        std::cout << "\nAll concurrency invariants verified.\n";

    } catch (const std::exception& error) {
        std::cerr << "Fatal error: "
                  << error.what() << '\n';

        return 1;
    }

    return 0;
}
