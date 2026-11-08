#include <algorithm>
#include <cstdint>
#include <exception>
#include <iostream>
#include <limits>
#include <mutex>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

/*
 * PostgreSQL Sequence and Identity Management
 *
 * C++17 implementation covering:
 * - Sequence configuration
 * - Ascending and descending sequences
 * - NEXTVAL and CURRVAL
 * - SETVAL and restart semantics
 * - Cycle and non-cycle behavior
 * - SERIAL and IDENTITY modeling
 * - Concurrent allocation
 * - Transaction rollback gaps
 * - Validation and reporting
 */

enum class IdentityMode {
    Serial,
    GeneratedAlways,
    GeneratedByDefault
};

class SequenceException : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class SequenceLimitException : public SequenceException {
public:
    using SequenceException::SequenceException;
};

struct SequenceConfig {
    std::string name;
    std::int64_t start = 1;
    std::int64_t increment = 1;
    std::int64_t minimum = 1;
    std::int64_t maximum =
        std::numeric_limits<std::int64_t>::max();
    std::uint64_t cache = 1;
    bool cycle = false;

    void validate() const {
        if (name.empty()) {
            throw SequenceException(
                "Sequence name cannot be empty."
            );
        }

        if (increment == 0) {
            throw SequenceException(
                "Sequence increment cannot be zero."
            );
        }

        if (minimum > maximum) {
            throw SequenceException(
                "Minimum exceeds maximum."
            );
        }

        if (start < minimum || start > maximum) {
            throw SequenceException(
                "Start value is outside sequence boundaries."
            );
        }

        if (cache == 0) {
            throw SequenceException(
                "Cache must be positive."
            );
        }
    }
};

class PostgreSQLSequence {
private:
    SequenceConfig config;
    std::int64_t lastValue = 0;
    bool isCalled = false;
    std::uint64_t allocations = 0;

    std::unordered_map<std::string, std::int64_t>
        sessionValues;

    mutable std::mutex mutex;

    std::int64_t calculateNext() const {
        if (!isCalled) {
            return config.start;
        }

        const std::int64_t current = lastValue;

        if (
            config.increment > 0 &&
            current > config.maximum - config.increment
        ) {
            if (!config.cycle) {
                throw SequenceLimitException(
                    "Sequence reached maximum."
                );
            }

            return config.minimum;
        }

        if (
            config.increment < 0 &&
            current < config.minimum - config.increment
        ) {
            if (!config.cycle) {
                throw SequenceLimitException(
                    "Sequence reached minimum."
                );
            }

            return config.maximum;
        }

        const std::int64_t candidate =
            current + config.increment;

        if (
            candidate < config.minimum ||
            candidate > config.maximum
        ) {
            if (!config.cycle) {
                throw SequenceLimitException(
                    "Sequence boundary reached."
                );
            }

            return config.increment > 0
                ? config.minimum
                : config.maximum;
        }

        return candidate;
    }

public:
    explicit PostgreSQLSequence(SequenceConfig sequenceConfig)
        : config(std::move(sequenceConfig)) {
        config.validate();
    }

    std::int64_t nextval(
        const std::string& session = "default"
    ) {
        if (session.empty()) {
            throw SequenceException(
                "Session name cannot be empty."
            );
        }

        std::lock_guard<std::mutex> lock(mutex);

        const std::int64_t value = calculateNext();

        lastValue = value;
        isCalled = true;
        ++allocations;

        sessionValues[session] = value;

        return value;
    }

    std::int64_t currval(
        const std::string& session = "default"
    ) const {
        std::lock_guard<std::mutex> lock(mutex);

        auto iterator = sessionValues.find(session);

        if (iterator == sessionValues.end()) {
            throw SequenceException(
                "NEXTVAL has not been called in this session."
            );
        }

        return iterator->second;
    }

    std::int64_t setval(
        std::int64_t value,
        bool called = true
    ) {
        std::lock_guard<std::mutex> lock(mutex);

        if (
            value < config.minimum ||
            value > config.maximum
        ) {
            throw SequenceLimitException(
                "SETVAL value outside configured limits."
            );
        }

        lastValue = value;
        isCalled = called;

        return value;
    }

    void restart(
        std::int64_t value = 0
    ) {
        std::lock_guard<std::mutex> lock(mutex);

        const std::int64_t restartValue =
            value == 0 ? config.start : value;

        if (
            restartValue < config.minimum ||
            restartValue > config.maximum
        ) {
            throw SequenceLimitException(
                "Restart value outside configured limits."
            );
        }

        lastValue = restartValue;
        isCalled = false;
        sessionValues.clear();
    }

    std::int64_t getLastValue() const {
        std::lock_guard<std::mutex> lock(mutex);
        return isCalled ? lastValue : config.start;
    }

    std::uint64_t getAllocations() const {
        std::lock_guard<std::mutex> lock(mutex);
        return allocations;
    }

    const SequenceConfig& getConfig() const {
        return config;
    }
};

struct Customer {
    std::int64_t id;
    std::string name;
    std::string email;
};

class CustomerTable {
private:
    PostgreSQLSequence& sequence;
    IdentityMode mode;

    std::unordered_map<std::int64_t, Customer> customers;
    mutable std::mutex mutex;

public:
    CustomerTable(
        PostgreSQLSequence& sequenceReference,
        IdentityMode identityMode
    )
        : sequence(sequenceReference),
          mode(identityMode) {}

    Customer insert(
        const std::string& name,
        const std::string& email,
        bool hasExplicitId = false,
        std::int64_t explicitId = 0,
        bool overridingSystemValue = false
    ) {
        if (name.empty() || email.find('@') == std::string::npos) {
            throw SequenceException(
                "Invalid customer information."
            );
        }

        std::int64_t id;

        if (hasExplicitId) {
            if (
                mode == IdentityMode::GeneratedAlways &&
                !overridingSystemValue
            ) {
                throw SequenceException(
                    "GENERATED ALWAYS rejects explicit IDs."
                );
            }

            id = explicitId;
        } else {
            id = sequence.nextval("customer-session");
        }

        if (id <= 0) {
            throw SequenceException(
                "Customer ID must be positive."
            );
        }

        std::lock_guard<std::mutex> lock(mutex);

        if (customers.count(id)) {
            throw SequenceException(
                "Duplicate customer primary key."
            );
        }

        Customer customer{id, name, email};

        customers.emplace(id, customer);

        return customer;
    }

    std::size_t size() const {
        std::lock_guard<std::mutex> lock(mutex);
        return customers.size();
    }

    std::int64_t maximumId() const {
        std::lock_guard<std::mutex> lock(mutex);

        std::int64_t maximum = 0;

        for (const auto& entry : customers) {
            maximum = std::max(maximum, entry.first);
        }

        return maximum;
    }

    void synchronizeSequence() {
        const std::int64_t maximum = maximumId();
        const std::int64_t current = sequence.getLastValue();

        if (maximum > current) {
            sequence.setval(maximum, true);
        }
    }
};

class TransactionSimulator {
private:
    PostgreSQLSequence& sequence;

public:
    explicit TransactionSimulator(
        PostgreSQLSequence& sequenceReference
    )
        : sequence(sequenceReference) {}

    void demonstrateRollback() {
        const auto allocated =
            sequence.nextval("transaction-session");

        std::cout
            << "Allocated before rollback: "
            << allocated << '\n';

        std::cout
            << "Rollback removes transactional data, "
            << "not the consumed sequence value.\n";
    }
};

void demonstrateBasicSequence() {
    std::cout << "\n1. BASIC SEQUENCE\n";

    SequenceConfig config{
        "orders_order_id_seq",
        1000,
        1,
        1000,
        1100,
        1,
        false
    };

    PostgreSQLSequence sequence(config);

    std::cout << "NEXTVAL: "
              << sequence.nextval("session-a") << '\n';

    std::cout << "NEXTVAL: "
              << sequence.nextval("session-a") << '\n';

    std::cout << "CURRVAL: "
              << sequence.currval("session-a") << '\n';
}

void demonstrateIdentity() {
    std::cout << "\n2. IDENTITY COLUMNS\n";

    SequenceConfig config{
        "customers_customer_id_seq"
    };

    PostgreSQLSequence sequence(config);

    CustomerTable customers(
        sequence,
        IdentityMode::GeneratedAlways
    );

    Customer first = customers.insert(
        "Aarav Sharma",
        "aarav@example.com"
    );

    std::cout << "Customer ID: "
              << first.id << '\n';

    try {
        customers.insert(
            "Manual Customer",
            "manual@example.com",
            true,
            500
        );
    } catch (const SequenceException& error) {
        std::cout << "Expected error: "
                  << error.what() << '\n';
    }

    customers.insert(
        "Imported Customer",
        "import@example.com",
        true,
        500,
        true
    );

    customers.synchronizeSequence();

    Customer next = customers.insert(
        "Next Customer",
        "next@example.com"
    );

    std::cout << "Next generated ID: "
              << next.id << '\n';
}

void demonstrateSetval() {
    std::cout << "\n3. SETVAL BEHAVIOR\n";

    PostgreSQLSequence sequence(
        SequenceConfig{"shipment_sequence"}
    );

    sequence.setval(500, true);

    std::cout << "SETVAL(500, true): "
              << sequence.nextval() << '\n';

    sequence.setval(900, false);

    std::cout << "SETVAL(900, false): "
              << sequence.nextval() << '\n';
}

void demonstrateSessions() {
    std::cout << "\n4. SESSION-SPECIFIC CURRVAL\n";

    PostgreSQLSequence sequence(
        SequenceConfig{"invoice_sequence"}
    );

    sequence.nextval("session-a");

    try {
        sequence.currval("session-b");
    } catch (const SequenceException& error) {
        std::cout << "Expected error: "
                  << error.what() << '\n';
    }

    sequence.nextval("session-b");

    std::cout << "Session A: "
              << sequence.currval("session-a") << '\n';

    std::cout << "Session B: "
              << sequence.currval("session-b") << '\n';
}

void demonstrateConcurrency() {
    std::cout << "\n5. CONCURRENT ALLOCATION\n";

    PostgreSQLSequence sequence(
        SequenceConfig{"concurrent_sequence"}
    );

    std::vector<std::int64_t> results;
    std::mutex resultMutex;

    std::vector<std::thread> workers;

    constexpr int workerCount = 8;
    constexpr int allocationsPerWorker = 100;

    for (int worker = 0; worker < workerCount; ++worker) {
        workers.emplace_back([&, worker]() {
            std::vector<std::int64_t> local;

            for (int i = 0; i < allocationsPerWorker; ++i) {
                local.push_back(
                    sequence.nextval(
                        "worker-" + std::to_string(worker)
                    )
                );
            }

            std::lock_guard<std::mutex> lock(resultMutex);

            results.insert(
                results.end(),
                local.begin(),
                local.end()
            );
        });
    }

    for (auto& worker : workers) {
        worker.join();
    }

    std::set<std::int64_t> unique(
        results.begin(),
        results.end()
    );

    if (unique.size() != results.size()) {
        throw SequenceException(
            "Duplicate concurrent allocation."
        );
    }

    std::cout << "Allocations: "
              << results.size() << '\n';

    std::cout << "Unique IDs: "
              << unique.size() << '\n';
}

void demonstrateRollback() {
    std::cout << "\n6. ROLLBACK BEHAVIOR\n";

    PostgreSQLSequence sequence(
        SequenceConfig{"payment_sequence"}
    );

    TransactionSimulator transaction(sequence);

    transaction.demonstrateRollback();

    std::cout << "Next value: "
              << sequence.nextval() << '\n';
}

void demonstrateCycle() {
    std::cout << "\n7. CYCLING SEQUENCE\n";

    SequenceConfig config{
        "temporary_code_sequence",
        1,
        1,
        1,
        3,
        1,
        true
    };

    PostgreSQLSequence sequence(config);

    for (int i = 0; i < 7; ++i) {
        std::cout << sequence.nextval() << ' ';
    }

    std::cout << '\n';
}

void runTests() {
    std::cout << "\n8. AUTOMATED TESTS\n";

    PostgreSQLSequence sequence(
        SequenceConfig{
            "test_sequence",
            10,
            5,
            10,
            30,
            1,
            false
        }
    );

    if (sequence.nextval() != 10) {
        throw SequenceException("Test failed.");
    }

    if (sequence.nextval() != 15) {
        throw SequenceException("Test failed.");
    }

    sequence.setval(20, false);

    if (sequence.nextval() != 20) {
        throw SequenceException("SETVAL test failed.");
    }

    sequence.setval(30, true);

    try {
        sequence.nextval();
        throw SequenceException(
            "Expected boundary exception."
        );
    } catch (const SequenceLimitException&) {
        // Expected failure.
    }

    std::cout << "All tests passed.\n";
}

int main() {
    try {
        std::cout
            << "========================================\n"
            << "POSTGRESQL SEQUENCE MANAGEMENT\n"
            << "========================================\n";

        demonstrateBasicSequence();
        demonstrateIdentity();
        demonstrateSetval();
        demonstrateSessions();
        demonstrateConcurrency();
        demonstrateRollback();
        demonstrateCycle();
        runTests();

        std::cout
            << "\nExecution completed successfully.\n";

        return 0;

    } catch (const std::exception& error) {
        std::cerr
            << "Execution failed: "
            << error.what() << '\n';

        return 1;
    }
}
