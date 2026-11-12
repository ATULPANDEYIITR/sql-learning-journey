#include <algorithm>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

enum class TransactionState {
    ACTIVE,
    COMMITTED,
    ROLLED_BACK
};

enum class OperationType {
    TRANSFER,
    DEPOSIT,
    WITHDRAWAL
};

enum class IsolationLevel {
    READ_COMMITTED,
    SERIALIZABLE
};

struct Account {
    string id;
    string owner;
    int64_t balance;
    string currency;
    uint64_t version = 0;
};

struct Operation {
    OperationType type;
    string source;
    string destination;
    int64_t amount;
};

struct LedgerEntry {
    string transactionId;
    string accountId;
    int64_t amount;
    string type;
};

class TransactionException : public runtime_error {
public:
    explicit TransactionException(const string& message)
        : runtime_error(message) {}
};

class Transaction {
private:
    string id;
    TransactionState state;
    uint64_t baseVersion;
    vector<Operation> operations;

public:
    Transaction(const string& transactionId, uint64_t version)
        : id(transactionId),
          state(TransactionState::ACTIVE),
          baseVersion(version) {}

    const string& getId() const {
        return id;
    }

    TransactionState getState() const {
        return state;
    }

    uint64_t getBaseVersion() const {
        return baseVersion;
    }

    const vector<Operation>& getOperations() const {
        return operations;
    }

    void addOperation(const Operation& operation) {
        if (state != TransactionState::ACTIVE) {
            throw TransactionException("Transaction is not active");
        }

        if (operation.amount <= 0) {
            throw TransactionException("Amount must be positive");
        }

        operations.push_back(operation);
    }

    void setState(TransactionState newState) {
        state = newState;
    }

    void clearOperations() {
        operations.clear();
    }
};

class RepositoryGovernanceEngine {
private:
    map<string, Account> accounts;
    vector<LedgerEntry> ledger;
    uint64_t databaseVersion = 0;
    uint64_t nextTransactionId = 1;

    void validateAccount(const string& id) const {
        if (accounts.find(id) == accounts.end()) {
            throw TransactionException("Account does not exist: " + id);
        }
    }

public:
    void createAccount(
        const string& id,
        const string& owner,
        int64_t balance,
        const string& currency = "INR"
    ) {
        if (id.empty() || owner.empty()) {
            throw TransactionException("Account data is incomplete");
        }

        if (balance < 0) {
            throw TransactionException("Negative opening balance");
        }

        if (accounts.count(id)) {
            throw TransactionException("Duplicate account");
        }

        accounts.emplace(
            id,
            Account{id, owner, balance, currency, 0}
        );

        ++databaseVersion;
    }

    Transaction begin() {
        return Transaction(
            "TXN-" + to_string(nextTransactionId++),
            databaseVersion
        );
    }

    void transfer(
        Transaction& transaction,
        const string& source,
        const string& destination,
        int64_t amount
    ) {
        if (source == destination) {
            throw TransactionException(
                "Source and destination must differ"
            );
        }

        validateAccount(source);
        validateAccount(destination);

        if (accounts.at(source).currency != accounts.at(destination).currency) {
            throw TransactionException("Currency mismatch");
        }

        transaction.addOperation({
            OperationType::TRANSFER,
            source,
            destination,
            amount
        });
    }

    void deposit(
        Transaction& transaction,
        const string& account,
        int64_t amount
    ) {
        validateAccount(account);

        transaction.addOperation({
            OperationType::DEPOSIT,
            account,
            "",
            amount
        });
    }

    void withdraw(
        Transaction& transaction,
        const string& account,
        int64_t amount
    ) {
        validateAccount(account);

        transaction.addOperation({
            OperationType::WITHDRAWAL,
            account,
            "",
            amount
        });
    }

    void commit(Transaction& transaction, IsolationLevel isolation) {
        if (transaction.getState() != TransactionState::ACTIVE) {
            throw TransactionException("Transaction is not active");
        }

        if (
            isolation == IsolationLevel::SERIALIZABLE &&
            transaction.getBaseVersion() != databaseVersion
        ) {
            transaction.setState(TransactionState::ROLLED_BACK);
            throw TransactionException(
                "Serialization conflict: retry the transaction"
            );
        }

        // A private working copy protects published balances from
        // partially applied operations.
        map<string, int64_t> workingBalances;

        for (const auto& [id, account] : accounts) {
            workingBalances[id] = account.balance;
        }

        vector<LedgerEntry> pendingLedger;

        try {
            for (const Operation& operation : transaction.getOperations()) {
                if (operation.type == OperationType::TRANSFER) {
                    int64_t& source = workingBalances.at(operation.source);
                    int64_t& destination =
                        workingBalances.at(operation.destination);

                    if (source < operation.amount) {
                        throw TransactionException(
                            "Insufficient funds in " + operation.source
                        );
                    }

                    if (
                        destination >
                        INT64_MAX - operation.amount
                    ) {
                        throw TransactionException(
                            "Destination balance overflow"
                        );
                    }

                    source -= operation.amount;
                    destination += operation.amount;

                    pendingLedger.push_back({
                        transaction.getId(),
                        operation.source,
                        -operation.amount,
                        "TRANSFER_OUT"
                    });

                    pendingLedger.push_back({
                        transaction.getId(),
                        operation.destination,
                        operation.amount,
                        "TRANSFER_IN"
                    });

                } else if (operation.type == OperationType::DEPOSIT) {
                    int64_t& balance =
                        workingBalances.at(operation.source);

                    if (balance > INT64_MAX - operation.amount) {
                        throw TransactionException("Balance overflow");
                    }

                    balance += operation.amount;

                    pendingLedger.push_back({
                        transaction.getId(),
                        operation.source,
                        operation.amount,
                        "DEPOSIT"
                    });

                } else if (operation.type == OperationType::WITHDRAWAL) {
                    int64_t& balance =
                        workingBalances.at(operation.source);

                    if (balance < operation.amount) {
                        throw TransactionException(
                            "Insufficient funds in " + operation.source
                        );
                    }

                    balance -= operation.amount;

                    pendingLedger.push_back({
                        transaction.getId(),
                        operation.source,
                        -operation.amount,
                        "WITHDRAWAL"
                    });
                }
            }

            // Validate the complete resulting state before publication.
            for (const auto& [id, balance] : workingBalances) {
                if (balance < 0) {
                    throw TransactionException(
                        "Negative balance constraint violated"
                    );
                }
            }

            for (auto& [id, account] : accounts) {
                if (workingBalances.at(id) != account.balance) {
                    account.balance = workingBalances.at(id);
                    ++account.version;
                }
            }

            ledger.insert(
                ledger.end(),
                pendingLedger.begin(),
                pendingLedger.end()
            );

            ++databaseVersion;
            transaction.setState(TransactionState::COMMITTED);

            cout << "COMMIT " << transaction.getId() << '\n';

        } catch (...) {
            transaction.setState(TransactionState::ROLLED_BACK);
            cout << "ROLLBACK " << transaction.getId() << '\n';
            throw;
        }
    }

    void rollback(Transaction& transaction) {
        if (transaction.getState() != TransactionState::ACTIVE) {
            throw TransactionException("Transaction is not active");
        }

        transaction.clearOperations();
        transaction.setState(TransactionState::ROLLED_BACK);

        cout << "ROLLBACK " << transaction.getId() << '\n';
    }

    int64_t balanceOf(const string& accountId) const {
        validateAccount(accountId);
        return accounts.at(accountId).balance;
    }

    int64_t totalBalance() const {
        int64_t total = 0;

        for (const auto& [id, account] : accounts) {
            if (total > INT64_MAX - account.balance) {
                throw TransactionException("Total balance overflow");
            }

            total += account.balance;
        }

        return total;
    }

    void display() const {
        cout << "\nACCOUNT STATEMENT\n";

        for (const auto& [id, account] : accounts) {
            cout << left << setw(10) << id
                 << setw(15) << account.owner
                 << setw(12) << account.balance
                 << account.currency << '\n';
        }

        cout << "Ledger entries: " << ledger.size() << '\n';
        cout << "Database version: " << databaseVersion << '\n';
    }

    void displayLedger() const {
        cout << "\nTRANSACTION LEDGER\n";

        for (const auto& entry : ledger) {
            cout << entry.transactionId << " | "
                 << entry.accountId << " | "
                 << entry.amount << " | "
                 << entry.type << '\n';
        }
    }
};

int main() {
    try {
        RepositoryGovernanceEngine engine;

        engine.createAccount("A100", "Alice", 1000000);
        engine.createAccount("A200", "Bob", 500000);
        engine.createAccount("A300", "Charlie", 200000);

        cout << "1. Successful atomic transaction\n";

        Transaction first = engine.begin();

        engine.transfer(first, "A100", "A200", 150000);
        engine.deposit(first, "A300", 50000);

        engine.commit(first, IsolationLevel::SERIALIZABLE);

        engine.display();

        cout << "\n2. Explicit rollback\n";

        Transaction second = engine.begin();

        engine.withdraw(second, "A100", 100000);
        engine.rollback(second);

        engine.display();

        cout << "\n3. Insufficient funds\n";

        Transaction third = engine.begin();

        engine.withdraw(third, "A200", 99999999);

        try {
            engine.commit(third, IsolationLevel::SERIALIZABLE);
        } catch (const TransactionException& error) {
            cout << "Expected failure: " << error.what() << '\n';
        }

        engine.display();

        cout << "\n4. Multiple operations\n";

        Transaction fourth = engine.begin();

        engine.deposit(fourth, "A100", 25000);
        engine.withdraw(fourth, "A300", 10000);

        engine.commit(fourth, IsolationLevel::SERIALIZABLE);

        engine.displayLedger();

        cout << "\n5. Serialization conflict\n";

        Transaction stale = engine.begin();

        engine.deposit(stale, "A100", 10000);

        Transaction concurrent = engine.begin();

        engine.deposit(concurrent, "A200", 20000);

        engine.commit(concurrent, IsolationLevel::SERIALIZABLE);

        try {
            engine.commit(stale, IsolationLevel::SERIALIZABLE);
        } catch (const TransactionException& error) {
            cout << "Expected conflict: " << error.what() << '\n';
        }

        cout << "\n6. Final verification\n";

        engine.display();

        const int64_t expectedTotal = 1775000;

        if (engine.totalBalance() != expectedTotal) {
            throw TransactionException("Accounting invariant failed");
        }

        cout << "Total balance: " << engine.totalBalance() << '\n';
        cout << "All checks passed.\n";

    } catch (const exception& error) {
        cerr << "Application error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
