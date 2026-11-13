#include <algorithm>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <map>
#include <mutex>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

/*
 * ACID Properties: Repository-independent transactional ledger.
 *
 * This C++17 implementation models a repository-style governance engine
 * for financial transactions:
 *
 * Atomicity: staged writes are applied only after successful validation.
 * Consistency: invariants are checked before commit.
 * Isolation: optimistic version validation rejects stale transactions.
 * Durability: committed records are retained in a simulated append-only log.
 *
 * The journal is an in-memory durability model, not persistent storage.
 */

enum class TransactionState {
    ACTIVE,
    COMMITTED,
    ROLLED_BACK,
    FAILED
};

enum class IsolationLevel {
    READ_COMMITTED,
    REPEATABLE_READ,
    SERIALIZABLE
};

enum class TransactionType {
    DEPOSIT,
    WITHDRAWAL,
    TRANSFER
};

struct Account {
    int id;
    string owner;
    int64_t balance;
    uint64_t version;
    bool active;
};

struct Operation {
    TransactionType type;
    int source;
    int target;
    int64_t amount;
};

struct JournalRecord {
    string transactionId;
    vector<pair<int, int64_t>> balances;
    string description;
};

class TransactionException : public runtime_error {
public:
    explicit TransactionException(const string& message)
        : runtime_error(message) {}
};

class ConstraintViolation : public TransactionException {
public:
    using TransactionException::TransactionException;
};

class SerializationFailure : public TransactionException {
public:
    using TransactionException::TransactionException;
};

class GovernanceEngine;

class Transaction {
private:
    GovernanceEngine& engine;
    string transactionId;
    IsolationLevel isolation;
    TransactionState state;

    map<int, int64_t> stagedBalances;
    map<int, uint64_t> readVersions;
    map<int, uint64_t> writeVersions;
    vector<Operation> operations;

    void requireActive() const {
        if (state != TransactionState::ACTIVE) {
            throw TransactionException("Transaction is not active");
        }
    }

public:
    Transaction(
        GovernanceEngine& engine,
        string id,
        IsolationLevel isolation
    );

    int64_t read(int accountId);

    void deposit(int accountId, int64_t amount);
    void withdraw(int accountId, int64_t amount);
    void transfer(int source, int target, int64_t amount);

    void commit();
    void rollback();

    TransactionState getState() const {
        return state;
    }

    friend class GovernanceEngine;
};

class GovernanceEngine {
private:
    map<int, Account> accounts;
    vector<JournalRecord> journal;
    mutable mutex engineMutex;
    int nextAccountId = 1;
    uint64_t transactionSequence = 1;

    static constexpr int64_t MAX_BALANCE = 9000000000000000LL;

    void validateAccount(const Account& account) const {
        if (account.id <= 0 || account.owner.empty()) {
            throw ConstraintViolation("Invalid account identity");
        }

        if (account.balance < 0 || account.balance > MAX_BALANCE) {
            throw ConstraintViolation("Account balance out of range");
        }
    }

public:
    int createAccount(const string& owner, int64_t balance) {
        lock_guard<mutex> guard(engineMutex);

        if (owner.empty()) {
            throw ConstraintViolation("Owner is required");
        }

        if (balance < 0 || balance > MAX_BALANCE) {
            throw ConstraintViolation("Invalid initial balance");
        }

        int id = nextAccountId++;

        accounts.emplace(
            id,
            Account{id, owner, balance, 0, true}
        );

        return id;
    }

    Transaction begin(
        IsolationLevel isolation = IsolationLevel::SERIALIZABLE
    ) {
        lock_guard<mutex> guard(engineMutex);

        return Transaction(
            *this,
            "TX-" + to_string(transactionSequence++),
            isolation
        );
    }

    const Account& getAccount(int id) const {
        auto it = accounts.find(id);

        if (it == accounts.end()) {
            throw ConstraintViolation("Unknown account");
        }

        return it->second;
    }

    void commit(Transaction& transaction) {
        lock_guard<mutex> guard(engineMutex);

        transaction.requireActive();

        // Validate all observed versions for repeatable and serializable reads.
        if (transaction.isolation != IsolationLevel::READ_COMMITTED) {
            for (const auto& [id, expectedVersion] :
                 transaction.readVersions) {
                auto it = accounts.find(id);

                if (
                    it == accounts.end() ||
                    it->second.version != expectedVersion
                ) {
                    throw SerializationFailure(
                        "Read-write serialization conflict"
                    );
                }
            }
        }

        int64_t totalBefore = 0;
        int64_t totalAfter = 0;

        for (const auto& [id, account] : accounts) {
            if (account.active) {
                totalBefore += account.balance;
            }
        }

        map<int, int64_t> projected;

        for (const auto& [id, account] : accounts) {
            projected[id] = account.balance;
        }

        for (const auto& [id, newBalance] :
             transaction.stagedBalances) {
            auto it = accounts.find(id);

            if (it == accounts.end()) {
                throw ConstraintViolation("Account disappeared");
            }

            if (it->second.version != transaction.writeVersions.at(id)) {
                throw SerializationFailure(
                    "Write-write conflict on account " + to_string(id)
                );
            }

            if (
                newBalance < 0 ||
                newBalance > MAX_BALANCE
            ) {
                throw ConstraintViolation("Balance constraint violated");
            }

            projected[id] = newBalance;
        }

        for (const auto& [id, account] : accounts) {
            if (account.active) {
                totalAfter += projected.at(id);
            }
        }

        // Money transfers conserve total funds.
        if (totalBefore != totalAfter) {
            throw ConstraintViolation("Global balance invariant violated");
        }

        // Construct the journal record before modifying committed state.
        JournalRecord record;
        record.transactionId = transaction.transactionId;
        record.description = "Atomic account transaction";

        for (const auto& [id, balance] :
             transaction.stagedBalances) {
            record.balances.emplace_back(id, balance);
        }

        journal.push_back(record);

        // Publish all changes as one critical section.
        for (const auto& [id, newBalance] :
             transaction.stagedBalances) {
            Account& account = accounts.at(id);
            account.balance = newBalance;
            ++account.version;
        }

        transaction.state = TransactionState::COMMITTED;
    }

    void printLedger() const {
        lock_guard<mutex> guard(engineMutex);

        cout << "\nACCOUNT LEDGER\n";
        cout << left << setw(8) << "ID"
             << setw(18) << "OWNER"
             << right << setw(16) << "BALANCE"
             << setw(12) << "VERSION" << '\n';

        for (const auto& [id, account] : accounts) {
            cout << left << setw(8) << id
                 << setw(18) << account.owner
                 << right << setw(16) << account.balance
                 << setw(12) << account.version << '\n';
        }
    }

    int64_t totalBalance() const {
        lock_guard<mutex> guard(engineMutex);

        int64_t total = 0;

        for (const auto& [id, account] : accounts) {
            if (account.active) {
                total += account.balance;
            }
        }

        return total;
    }

    void printJournal() const {
        lock_guard<mutex> guard(engineMutex);

        cout << "\nCOMMIT JOURNAL\n";

        for (const auto& record : journal) {
            cout << record.transactionId
                 << " | " << record.description << '\n';

            for (const auto& [id, balance] : record.balances) {
                cout << "  Account " << id
                     << " -> " << balance << '\n';
            }
        }
    }

    friend class Transaction;
};

Transaction::Transaction(
    GovernanceEngine& engine,
    string id,
    IsolationLevel isolation
)
    : engine(engine),
      transactionId(std::move(id)),
      isolation(isolation),
      state(TransactionState::ACTIVE) {}

int64_t Transaction::read(int accountId) {
    requireActive();

    const Account& account = engine.getAccount(accountId);

    if (!account.active) {
        throw ConstraintViolation("Account is inactive");
    }

    if (stagedBalances.count(accountId)) {
        return stagedBalances.at(accountId);
    }

    readVersions.emplace(accountId, account.version);

    return account.balance;
}

void Transaction::deposit(int accountId, int64_t amount) {
    requireActive();

    if (amount <= 0) {
        throw ConstraintViolation("Deposit must be positive");
    }

    const Account& account = engine.getAccount(accountId);

    int64_t balance = read(accountId);

    if (balance > 9000000000000000LL - amount) {
        throw ConstraintViolation("Balance overflow");
    }

    writeVersions.emplace(accountId, account.version);
    stagedBalances[accountId] = balance + amount;

    operations.push_back({
        TransactionType::DEPOSIT, accountId, accountId, amount
    });
}

void Transaction::withdraw(int accountId, int64_t amount) {
    requireActive();

    if (amount <= 0) {
        throw ConstraintViolation("Withdrawal must be positive");
    }

    const Account& account = engine.getAccount(accountId);
    int64_t balance = read(accountId);

    if (balance < amount) {
        throw ConstraintViolation("Insufficient funds");
    }

    writeVersions.emplace(accountId, account.version);
    stagedBalances[accountId] = balance - amount;

    operations.push_back({
        TransactionType::WITHDRAWAL, accountId, accountId, amount
    });
}

void Transaction::transfer(
    int source,
    int target,
    int64_t amount
) {
    requireActive();

    if (source == target) {
        throw ConstraintViolation("Accounts must differ");
    }

    if (amount <= 0) {
        throw ConstraintViolation("Transfer must be positive");
    }

    const Account& sourceAccount = engine.getAccount(source);
    const Account& targetAccount = engine.getAccount(target);

    if (!sourceAccount.active || !targetAccount.active) {
        throw ConstraintViolation("Inactive account");
    }

    int64_t sourceBalance = read(source);
    int64_t targetBalance = read(target);

    if (sourceBalance < amount) {
        throw ConstraintViolation("Insufficient funds");
    }

    if (targetBalance > 9000000000000000LL - amount) {
        throw ConstraintViolation("Target balance overflow");
    }

    writeVersions.emplace(source, sourceAccount.version);
    writeVersions.emplace(target, targetAccount.version);

    stagedBalances[source] = sourceBalance - amount;
    stagedBalances[target] = targetBalance + amount;

    operations.push_back({
        TransactionType::TRANSFER, source, target, amount
    });
}

void Transaction::commit() {
    requireActive();

    try {
        engine.commit(*this);
    } catch (...) {
        state = TransactionState::FAILED;
        stagedBalances.clear();
        throw;
    }
}

void Transaction::rollback() {
    requireActive();

    stagedBalances.clear();
    operations.clear();
    state = TransactionState::ROLLED_BACK;
}

int main() {
    try {
        GovernanceEngine engine;

        int alice = engine.createAccount("Alice", 100000);
        int bob = engine.createAccount("Bob", 50000);
        int charlie = engine.createAccount("Charlie", 25000);

        cout << "ACID TRANSACTION GOVERNANCE ENGINE\n";
        engine.printLedger();

        // Atomicity and consistency.
        {
            Transaction tx = engine.begin();
            tx.transfer(alice, bob, 20000);
            tx.commit();
        }

        cout << "\nSuccessful transfer completed.";
        engine.printLedger();

        // Failed transaction: no staged changes become committed.
        {
            Transaction tx = engine.begin();

            try {
                tx.transfer(alice, charlie, 999999);
                tx.commit();
            } catch (const TransactionException& error) {
                if (tx.getState() == TransactionState::ACTIVE) {
                    tx.rollback();
                }

                cout << "\nRejected: " << error.what() << '\n';
            }
        }

        // Optimistic concurrency: two transactions observe the same version.
        {
            Transaction first = engine.begin();
            Transaction second = engine.begin();

            first.deposit(alice, 1000);
            second.deposit(alice, 2000);

            first.commit();

            try {
                second.commit();
            } catch (const SerializationFailure& error) {
                cout << "\nIsolation conflict detected: "
                     << error.what() << '\n';
            }
        }

        // Withdrawal and rollback.
        {
            Transaction tx = engine.begin();
            tx.withdraw(bob, 5000);
            tx.rollback();

            cout << "\nExplicit rollback completed.\n";
        }

        engine.printLedger();
        engine.printJournal();

        const int64_t expectedTotal = 175000;

        if (engine.totalBalance() != expectedTotal + 1000) {
            throw runtime_error("Consistency assertion failed");
        }

        cout << "\nConsistency verified.";
        cout << "\nTotal funds: " << engine.totalBalance() << '\n';

    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
