#include <algorithm>
#include <cctype>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

using namespace std;

class UniqueViolation : public runtime_error {
public:
    explicit UniqueViolation(const string& message)
        : runtime_error(message) {}
};

class ValidationError : public runtime_error {
public:
    explicit ValidationError(const string& message)
        : runtime_error(message) {}
};

string normalize(const string& input) {
    string result;

    for (unsigned char ch : input) {
        result.push_back(static_cast<char>(tolower(ch)));
    }

    auto first = result.find_first_not_of(" \t\n\r");
    auto last = result.find_last_not_of(" \t\n\r");

    if (first == string::npos) {
        throw ValidationError("Empty value is not allowed");
    }

    return result.substr(first, last - first + 1);
}

struct Account {
    int id;
    int tenantId;
    string email;
    string username;
    bool active;
};

struct CompositeKey {
    int tenantId;
    string username;

    bool operator<(const CompositeKey& other) const {
        return tie(tenantId, username) <
               tie(other.tenantId, other.username);
    }
};

class AccountRepository {
private:
    unordered_map<int, Account> accounts;

    // Global unique index.
    unordered_map<string, int> emailIndex;

    // Composite unique index.
    map<CompositeKey, int> tenantUsernameIndex;

    // Partial unique index: active accounts only.
    unordered_map<string, int> activeEmailIndex;

    int nextId = 1;

    void validate(const Account& account) const {
        if (account.id <= 0 || account.tenantId <= 0) {
            throw ValidationError("Identifiers must be positive");
        }

        if (account.email.find('@') == string::npos) {
            throw ValidationError("Invalid email address");
        }

        if (account.username.empty()) {
            throw ValidationError("Username cannot be empty");
        }
    }

    void validateIndexes(const Account& candidate,
                         optional<int> ignoredId = nullopt) const {
        const string email = normalize(candidate.email);
        const string username = normalize(candidate.username);

        auto checkOwner = [&](const auto& index,
                              const auto& key,
                              const string& indexName) {
            auto it = index.find(key);

            if (it != index.end() &&
                (!ignoredId || it->second != *ignoredId)) {
                throw UniqueViolation(
                    indexName + " rejects duplicate key"
                );
            }
        };

        checkOwner(emailIndex, email, "uq_accounts_email");

        checkOwner(
            tenantUsernameIndex,
            CompositeKey{candidate.tenantId, username},
            "uq_accounts_tenant_username"
        );

        if (candidate.active) {
            checkOwner(
                activeEmailIndex,
                email,
                "uq_active_accounts_email"
            );
        }
    }

    void addIndexes(const Account& account) {
        const string email = normalize(account.email);
        const string username = normalize(account.username);

        emailIndex[email] = account.id;

        tenantUsernameIndex[
            CompositeKey{account.tenantId, username}
        ] = account.id;

        if (account.active) {
            activeEmailIndex[email] = account.id;
        }
    }

    void removeIndexes(const Account& account) {
        const string email = normalize(account.email);
        const string username = normalize(account.username);

        emailIndex.erase(email);

        tenantUsernameIndex.erase(
            CompositeKey{account.tenantId, username}
        );

        if (account.active) {
            activeEmailIndex.erase(email);
        }
    }

public:
    Account insert(int tenantId,
                   string email,
                   string username,
                   bool active = true) {
        Account candidate{
            nextId,
            tenantId,
            move(email),
            move(username),
            active
        };

        validate(candidate);
        validateIndexes(candidate);

        // State changes happen only after all indexes pass validation.
        accounts.emplace(candidate.id, candidate);
        addIndexes(candidate);

        ++nextId;

        return candidate;
    }

    void update(int id,
                const string& newEmail,
                const string& newUsername,
                bool active) {
        auto it = accounts.find(id);

        if (it == accounts.end()) {
            throw ValidationError("Account not found");
        }

        Account candidate = it->second;
        candidate.email = newEmail;
        candidate.username = newUsername;
        candidate.active = active;

        validate(candidate);
        validateIndexes(candidate, id);

        removeIndexes(it->second);

        it->second = candidate;
        addIndexes(candidate);
    }

    optional<Account> findByEmail(const string& email) const {
        auto it = emailIndex.find(normalize(email));

        if (it == emailIndex.end()) {
            return nullopt;
        }

        return accounts.at(it->second);
    }

    bool audit() const {
        unordered_map<string, int> rebuiltEmails;
        map<CompositeKey, int> rebuiltUsernames;
        unordered_map<string, int> rebuiltActive;

        for (const auto& [id, account] : accounts) {
            string email = normalize(account.email);
            string username = normalize(account.username);

            if (!rebuiltEmails.emplace(email, id).second) {
                return false;
            }

            if (!rebuiltUsernames.emplace(
                    CompositeKey{account.tenantId, username}, id
                ).second) {
                return false;
            }

            if (account.active &&
                !rebuiltActive.emplace(email, id).second) {
                return false;
            }
        }

        return rebuiltEmails == emailIndex &&
               rebuiltUsernames.size() == tenantUsernameIndex.size() &&
               rebuiltActive == activeEmailIndex;
    }

    void report() const {
        cout << "\nAccount records:\n";

        for (const auto& [id, account] : accounts) {
            cout << "ID: " << id
                 << ", Tenant: " << account.tenantId
                 << ", Email: " << account.email
                 << ", Username: " << account.username
                 << ", Active: " << boolalpha << account.active
                 << '\n';
        }

        cout << "Email index entries: " << emailIndex.size() << '\n';
        cout << "Composite index entries: "
             << tenantUsernameIndex.size() << '\n';
        cout << "Partial index entries: "
             << activeEmailIndex.size() << '\n';
    }
};

int main() {
    try {
        AccountRepository repository;

        repository.insert(
            1, "alice@example.com", "alice"
        );

        repository.insert(
            2, "bob@example.com", "alice"
        );

        repository.insert(
            1, "archive@example.com", "archive", false
        );

        cout << "Initial registration completed.\n";

        try {
            repository.insert(
                3, "ALICE@example.com", "alice_new"
            );
        } catch (const UniqueViolation& error) {
            cout << "Expected conflict: " << error.what() << '\n';
        }

        repository.insert(
            3, "charlie@example.com", "charlie"
        );

        repository.update(
            3,
            "charlie@example.com",
            "charlie",
            false
        );

        // Inactive accounts are excluded from the partial index.
        repository.insert(
            4, "charlie@example.com", "charlie_archive", false
        );

        auto result = repository.findByEmail("ALICE@example.com");

        if (result) {
            cout << "\nFound account ID: " << result->id << '\n';
        }

        cout << "Index integrity: "
             << boolalpha << repository.audit() << '\n';

        repository.report();

        try {
            repository.insert(
                5, "invalid", "invalid"
            );
        } catch (const ValidationError& error) {
            cout << "\nExpected validation error: "
                 << error.what() << '\n';
        }

    } catch (const exception& error) {
        cerr << "Execution failure: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
