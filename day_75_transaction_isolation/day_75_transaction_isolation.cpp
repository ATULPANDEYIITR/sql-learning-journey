#include <algorithm>
#include <cstdint>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

/*
 * Transaction Isolation and Concurrency Control Engine
 *
 * C++17 implementation of an optimistic transaction manager.
 *
 * Demonstrates:
 * - Read Uncommitted conceptual semantics
 * - Read Committed
 * - Repeatable Read
 * - Serializable
 * - MVCC snapshots
 * - Write conflict detection
 * - Predicate conflict detection
 * - Transaction rollback
 * - Atomic account transfers
 *
 * This is an educational concurrency-control model.
 */

enum class IsolationLevel {
    ReadUncommitted,
    ReadCommitted,
    RepeatableRead,
    Serializable
};

enum class TransactionState {
    Active,
    Committed,
    RolledBack,
    Aborted
};

struct Account {
    int id;
    long long balance;
};

struct Version {
    Account value;
    std::uint64_t revision;
    bool committed;
};

struct RecordKey {
    std::string table;
    int id;

    bool operator<(const RecordKey& other) const {
        return std::tie(table, id) <
               std::tie(other.table, other.id);
    }
};

class TransactionError : public std::runtime_error {
public:
    explicit TransactionError(const std::string& message)
        : std::runtime_error(message) {}
};

class WriteConflict : public TransactionError {
public:
    using TransactionError::TransactionError;
};

class SerializationFailure : public TransactionError {
public:
    using TransactionError::TransactionError;
};

class InvalidTransaction : public TransactionError {
public:
    using TransactionError::TransactionError;
};

class Database {
public:
    struct Transaction {
        int id;
        IsolationLevel isolation;
        std::uint64_t snapshot;
        TransactionState state = TransactionState::Active;

        std::map<RecordKey, Account> writes;
        std::map<RecordKey, std::uint64_t> reads;
        std::set<std::string> scannedTables;
    };

private:
    std::map<std::string, std::map<int, std::vector<Version>>> tables;
    std::map<int, Transaction> activeTransactions;

    std::uint64_t revision = 0;
    int nextTransactionId = 1;

    void requireActive(const Transaction& transaction) const {
        auto found = activeTransactions.find(transaction.id);

        if (transaction.state != TransactionState::Active ||
            found == activeTransactions.end()) {
            throw InvalidTransaction("Transaction is not active");
        }
    }

    std::optional<Version> visibleVersion(
        const Transaction& transaction,
        const std::string& table,
        int id
    ) const {
        auto tableIt = tables.find(table);

        if (tableIt == tables.end()) {
            return std::nullopt;
        }

        auto recordIt = tableIt->second.find(id);

        if (recordIt == tableIt->second.end()) {
            return std::nullopt;
        }

        std::optional<Version> selected;

        for (const auto& version : recordIt->second) {
            if (!version.committed) {
                continue;
            }

            if (
                transaction.isolation != IsolationLevel::ReadCommitted &&
                version.revision > transaction.snapshot
            ) {
                continue;
            }

            if (!selected || version.revision > selected->revision) {
                selected = version;
            }
        }

        return selected;
    }

    void abort(Transaction& transaction) {
        transaction.writes.clear();
        transaction.state = TransactionState::Aborted;
        activeTransactions.erase(transaction.id);
    }

public:
    void createTable(const std::string& name) {
        if (name.empty() || tables.count(name)) {
            throw std::invalid_argument("Invalid or duplicate table");
        }

        tables.emplace(name, std::map<int, std::vector<Version>>{});
    }

    void seed(
        const std::string& table,
        const Account& account
    ) {
        if (!tables.count(table)) {
            throw std::invalid_argument("Unknown table");
        }

        auto& records = tables.at(table);

        if (records.count(account.id)) {
            throw WriteConflict("Duplicate account identifier");
        }

        ++revision;

        records[account.id].push_back({
            account,
            revision,
            true
        });
    }

    Transaction begin(IsolationLevel level) {
        Transaction transaction;
        transaction.id = nextTransactionId++;
        transaction.isolation = level;
        transaction.snapshot = revision;

        activeTransactions.emplace(
            transaction.id,
            transaction
        );

        std::cout
            << "BEGIN transaction " << transaction.id
            << " at revision " << revision << '\n';

        return transaction;
    }

    Account read(
        Transaction& transaction,
        const std::string& table,
        int id
    ) {
        requireActive(transaction);

        if (!tables.count(table)) {
            throw std::invalid_argument("Unknown table");
        }

        RecordKey key{table, id};

        auto staged = transaction.writes.find(key);

        if (staged != transaction.writes.end()) {
            return staged->second;
        }

        auto version = visibleVersion(transaction, table, id);

        if (!version) {
            throw std::out_of_range("Record does not exist");
        }

        transaction.reads[key] = version->revision;

        return version->value;
    }

    void write(
        Transaction& transaction,
        const std::string& table,
        const Account& account
    ) {
        requireActive(transaction);

        if (!tables.count(table)) {
            throw std::invalid_argument("Unknown table");
        }

        if (account.id <= 0 || account.balance < 0) {
            throw std::invalid_argument("Invalid account data");
        }

        RecordKey key{table, account.id};

        transaction.writes[key] = account;
    }

    std::vector<Account> scan(
        Transaction& transaction,
        const std::string& table,
        long long minimumBalance = 0
    ) {
        requireActive(transaction);

        if (!tables.count(table)) {
            throw std::invalid_argument("Unknown table");
        }

        transaction.scannedTables.insert(table);

        std::map<int, Account> result;

        for (const auto& [id, versions] : tables.at(table)) {
            try {
                Account account = read(transaction, table, id);

                if (account.balance >= minimumBalance) {
                    result[id] = account;
                }
            } catch (const std::out_of_range&) {
                continue;
            }
        }

        for (const auto& [key, account] : transaction.writes) {
            if (
                key.table == table &&
                account.balance >= minimumBalance
            ) {
                result[key.id] = account;
            }
        }

        std::vector<Account> output;

        for (const auto& [id, account] : result) {
            output.push_back(account);
        }

        return output;
    }

    void commit(Transaction& transaction) {
        requireActive(transaction);

        try {
            // Validate write-write conflicts.
            for (const auto& [key, account] : transaction.writes) {
                auto tableIt = tables.find(key.table);

                auto recordIt = tableIt->second.find(key.id);

                std::uint64_t latest = 0;

                if (recordIt != tableIt->second.end()) {
                    for (const auto& version : recordIt->second) {
                        if (version.committed) {
                            latest = std::max(
                                latest,
                                version.revision
                            );
                        }
                    }
                }

                if (
                    transaction.isolation !=
                        IsolationLevel::ReadCommitted &&
                    latest > transaction.snapshot
                ) {
                    throw WriteConflict(
                        "Concurrent modification of account " +
                        std::to_string(key.id)
                    );
                }
            }

            if (transaction.isolation == IsolationLevel::Serializable) {
                // Validate previously read records.
                for (const auto& [key, observed] : transaction.reads) {
                    std::uint64_t latest = 0;

                    const auto& versions =
                        tables.at(key.table).at(key.id);

                    for (const auto& version : versions) {
                        if (version.committed) {
                            latest = std::max(
                                latest,
                                version.revision
                            );
                        }
                    }

                    if (
                        latest > transaction.snapshot &&
                        latest != observed
                    ) {
                        throw SerializationFailure(
                            "Read-write dependency detected"
                        );
                    }
                }

                // Conservative predicate validation.
                for (const auto& table : transaction.scannedTables) {
                    for (const auto& [id, versions] : tables.at(table)) {
                        for (const auto& version : versions) {
                            if (
                                version.committed &&
                                version.revision > transaction.snapshot
                            ) {
                                throw SerializationFailure(
                                    "Predicate conflict in table " + table
                                );
                            }
                        }
                    }
                }
            }

            ++revision;

            for (const auto& [key, account] : transaction.writes) {
                tables[key.table][key.id].push_back({
                    account,
                    revision,
                    true
                });
            }

            transaction.state = TransactionState::Committed;
            activeTransactions.erase(transaction.id);

            std::cout
                << "COMMIT transaction " << transaction.id
                << " at revision " << revision << '\n';

        } catch (...) {
            abort(transaction);
            throw;
        }
    }

    void rollback(Transaction& transaction) {
        requireActive(transaction);

        transaction.writes.clear();
        transaction.state = TransactionState::RolledBack;

        activeTransactions.erase(transaction.id);

        std::cout
            << "ROLLBACK transaction " << transaction.id << '\n';
    }

    Account current(const std::string& table, int id) const {
        if (!tables.count(table) || !tables.at(table).count(id)) {
            throw std::out_of_range("Account not found");
        }

        const auto& versions = tables.at(table).at(id);

        const Version* selected = nullptr;

        for (const auto& version : versions) {
            if (
                version.committed &&
                (!selected || version.revision > selected->revision)
            ) {
                selected = &version;
            }
        }

        if (!selected) {
            throw std::out_of_range("No committed account version");
        }

        return selected->value;
    }

    void transfer(
        Transaction& transaction,
        int sourceId,
        int destinationId,
        long long amount
    ) {
        if (amount <= 0 || sourceId == destinationId) {
            throw std::invalid_argument("Invalid transfer parameters");
        }

        Account source = read(transaction, "accounts", sourceId);
        Account destination = read(
            transaction,
            "accounts",
            destinationId
        );

        if (source.balance < amount) {
            throw TransactionError("Insufficient funds");
        }

        source.balance -= amount;
        destination.balance += amount;

        write(transaction, "accounts", source);
        write(transaction, "accounts", destination);
    }
};

std::string isolationName(IsolationLevel level) {
    switch (level) {
        case IsolationLevel::ReadUncommitted:
            return "READ UNCOMMITTED";
        case IsolationLevel::ReadCommitted:
            return "READ COMMITTED";
        case IsolationLevel::RepeatableRead:
            return "REPEATABLE READ";
        case IsolationLevel::Serializable:
            return "SERIALIZABLE";
    }

    return "UNKNOWN";
}

void demonstrateReadCommitted() {
    std::cout << "\n1. READ COMMITTED\n";

    Database db;
    db.createTable("accounts");
    db.seed("accounts", {1, 1000});

    auto reader = db.begin(IsolationLevel::ReadCommitted);
    auto writer = db.begin(IsolationLevel::ReadCommitted);

    std::cout
        << "First read: "
        << db.read(reader, "accounts", 1).balance << '\n';

    auto account = db.read(writer, "accounts", 1);
    account.balance = 800;

    db.write(writer, "accounts", account);
    db.commit(writer);

    std::cout
        << "Second read: "
        << db.read(reader, "accounts", 1).balance << '\n';

    db.rollback(reader);
}

void demonstrateRepeatableRead() {
    std::cout << "\n2. REPEATABLE READ\n";

    Database db;
    db.createTable("accounts");
    db.seed("accounts", {1, 1000});

    auto reader = db.begin(IsolationLevel::RepeatableRead);
    auto writer = db.begin(IsolationLevel::ReadCommitted);

    std::cout
        << "First read: "
        << db.read(reader, "accounts", 1).balance << '\n';

    auto account = db.read(writer, "accounts", 1);
    account.balance = 700;

    db.write(writer, "accounts", account);
    db.commit(writer);

    std::cout
        << "Snapshot read: "
        << db.read(reader, "accounts", 1).balance << '\n';

    db.rollback(reader);
}

void demonstrateReadUncommitted() {
    std::cout << "\n3. READ UNCOMMITTED CONCEPT\n";

    Database db;
    db.createTable("accounts");
    db.seed("accounts", {1, 500});

    auto writer = db.begin(IsolationLevel::ReadCommitted);
    auto reader = db.begin(IsolationLevel::ReadUncommitted);

    auto account = db.read(writer, "accounts", 1);
    account.balance = 50;

    db.write(writer, "accounts", account);

    std::cout
        << "Reader sees committed balance: "
        << db.read(reader, "accounts", 1).balance << '\n';

    db.rollback(writer);
    db.rollback(reader);
}

void demonstrateSerializableConflict() {
    std::cout << "\n4. SERIALIZABLE\n";

    Database db;
    db.createTable("accounts");
    db.seed("accounts", {1, 1000});

    auto first = db.begin(IsolationLevel::Serializable);
    auto second = db.begin(IsolationLevel::ReadCommitted);

    db.read(first, "accounts", 1);

    auto account = db.read(second, "accounts", 1);
    account.balance = 900;

    db.write(second, "accounts", account);
    db.commit(second);

    try {
        db.commit(first);
    } catch (const SerializationFailure& error) {
        std::cout << "Expected failure: " << error.what() << '\n';
    }
}

void demonstrateWriteConflict() {
    std::cout << "\n5. REPEATABLE READ WRITE CONFLICT\n";

    Database db;
    db.createTable("accounts");
    db.seed("accounts", {1, 1000});

    auto first = db.begin(IsolationLevel::RepeatableRead);
    auto second = db.begin(IsolationLevel::RepeatableRead);

    Account a = db.read(first, "accounts", 1);
    Account b = db.read(second, "accounts", 1);

    a.balance -= 100;
    b.balance -= 200;

    db.write(first, "accounts", a);
    db.write(second, "accounts", b);

    db.commit(first);

    try {
        db.commit(second);
    } catch (const WriteConflict& error) {
        std::cout << "Conflict: " << error.what() << '\n';
    }

    std::cout
        << "Final balance: "
        << db.current("accounts", 1).balance << '\n';
}

void demonstrateBankTransfer() {
    std::cout << "\n6. ATOMIC BANK TRANSFER\n";

    Database db;
    db.createTable("accounts");

    db.seed("accounts", {101, 5000});
    db.seed("accounts", {102, 3000});

    auto transaction = db.begin(IsolationLevel::Serializable);

    try {
        db.transfer(transaction, 101, 102, 750);
        db.commit(transaction);
    } catch (const TransactionError& error) {
        if (transaction.state == TransactionState::Active) {
            db.rollback(transaction);
        }

        std::cout << "Transfer failed: " << error.what() << '\n';
    }

    std::cout
        << "Account 101: "
        << db.current("accounts", 101).balance << '\n';

    std::cout
        << "Account 102: "
        << db.current("accounts", 102).balance << '\n';
}

int main() {
    try {
        demonstrateReadCommitted();
        demonstrateRepeatableRead();
        demonstrateReadUncommitted();
        demonstrateSerializableConflict();
        demonstrateWriteConflict();
        demonstrateBankTransfer();

    } catch (const std::exception& error) {
        std::cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
