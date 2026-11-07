#include <algorithm>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

using namespace std;

enum class KeyStrategy {
    Identity,
    UUID,
    Natural
};

enum class RecordStatus {
    Active,
    Suspended,
    Deleted
};

class ValidationError : public runtime_error {
public:
    using runtime_error::runtime_error;
};

class DuplicateKeyError : public runtime_error {
public:
    using runtime_error::runtime_error;
};

class NotFoundError : public runtime_error {
public:
    using runtime_error::runtime_error;
};

struct UUID {
    string value;

    bool operator==(const UUID& other) const {
        return value == other.value;
    }
};

class UUIDGenerator {
private:
    mt19937_64 engine;
    uniform_int_distribution<uint64_t> distribution;

public:
    UUIDGenerator()
        : engine(random_device{}()),
          distribution(0, UINT64_MAX) {}

    UUID generate() {
        uint64_t first = distribution(engine);
        uint64_t second = distribution(engine);

        // Set UUID version 4 and RFC-compatible variant bits.
        second = (second & 0x3FFFFFFFFFFFFFFFULL)
               | 0x8000000000000000ULL;

        first = (first & 0xFFFFFFFFFFFF0FFFULL)
              | 0x0000000000004000ULL;

        ostringstream output;
        output << hex << setfill('0')
               << setw(8) << static_cast<uint32_t>(first >> 32)
               << "-"
               << setw(4) << static_cast<uint16_t>(first >> 16)
               << "-"
               << setw(4) << static_cast<uint16_t>(first)
               << "-"
               << setw(4) << static_cast<uint16_t>(second >> 48)
               << "-"
               << setw(12) << (second & 0x0000FFFFFFFFFFFFULL);

        return {output.str()};
    }
};

struct Customer {
    uint64_t id;
    UUID publicId;
    string email;
    string name;
    string country;
    RecordStatus status;
};

struct Order {
    uint64_t id;
    uint64_t customerId;
    double amount;
};

struct NaturalKey {
    string country;
    string identifier;

    bool operator<(const NaturalKey& other) const {
        return tie(country, identifier)
             < tie(other.country, other.identifier);
    }
};

class CustomerRepository {
private:
    uint64_t nextId = 1;
    UUIDGenerator uuidGenerator;

    map<uint64_t, Customer> customers;
    unordered_map<string, uint64_t> emailIndex;
    unordered_map<string, uint64_t> uuidIndex;

    static string normalizeEmail(const string& email) {
        string normalized = email;

        auto start = normalized.find_first_not_of(" \t\r\n");
        auto end = normalized.find_last_not_of(" \t\r\n");

        if (start == string::npos) {
            throw ValidationError("Email cannot be empty.");
        }

        normalized = normalized.substr(start, end - start + 1);

        transform(
            normalized.begin(),
            normalized.end(),
            normalized.begin(),
            [](unsigned char c) {
                return static_cast<char>(tolower(c));
            }
        );

        auto at = normalized.find('@');

        if (at == string::npos ||
            at == 0 ||
            at != normalized.rfind('@') ||
            normalized.find('.', at) == string::npos) {
            throw ValidationError("Invalid email.");
        }

        return normalized;
    }

    static string normalizeCountry(const string& country) {
        if (country.size() != 2) {
            throw ValidationError("Country must contain two letters.");
        }

        string result = country;

        for (char& character : result) {
            unsigned char c = static_cast<unsigned char>(character);

            if (!isalpha(c)) {
                throw ValidationError("Invalid country code.");
            }

            character = static_cast<char>(toupper(c));
        }

        return result;
    }

public:
    Customer create(
        string email,
        string name,
        string country
    ) {
        email = normalizeEmail(email);
        country = normalizeCountry(country);

        if (name.find_first_not_of(" \t\r\n") == string::npos) {
            throw ValidationError("Customer name is required.");
        }

        if (emailIndex.count(email)) {
            throw DuplicateKeyError("Email already exists.");
        }

        UUID generated = uuidGenerator.generate();

        Customer customer{
            nextId,
            generated,
            email,
            name,
            country,
            RecordStatus::Active
        };

        // Integer and UUID identifiers remain immutable.
        customers.emplace(nextId, customer);
        emailIndex.emplace(email, nextId);
        uuidIndex.emplace(generated.value, nextId);

        ++nextId;

        return customer;
    }

    const Customer& findById(uint64_t id) const {
        auto iterator = customers.find(id);

        if (iterator == customers.end()) {
            throw NotFoundError("Customer ID not found.");
        }

        return iterator->second;
    }

    const Customer& findByUUID(const UUID& uuid) const {
        auto iterator = uuidIndex.find(uuid.value);

        if (iterator == uuidIndex.end()) {
            throw NotFoundError("UUID not found.");
        }

        return findById(iterator->second);
    }

    const Customer& findByEmail(const string& email) const {
        string normalized = normalizeEmail(email);

        auto iterator = emailIndex.find(normalized);

        if (iterator == emailIndex.end()) {
            throw NotFoundError("Email not found.");
        }

        return findById(iterator->second);
    }

    void updateEmail(uint64_t id, string newEmail) {
        auto customerIterator = customers.find(id);

        if (customerIterator == customers.end()) {
            throw NotFoundError("Customer not found.");
        }

        newEmail = normalizeEmail(newEmail);

        auto existing = emailIndex.find(newEmail);

        if (existing != emailIndex.end() && existing->second != id) {
            throw DuplicateKeyError("Email belongs to another customer.");
        }

        Customer& customer = customerIterator->second;

        emailIndex.erase(customer.email);
        customer.email = newEmail;
        emailIndex.emplace(newEmail, id);
    }

    void changeStatus(uint64_t id, RecordStatus status) {
        auto iterator = customers.find(id);

        if (iterator == customers.end()) {
            throw NotFoundError("Customer not found.");
        }

        iterator->second.status = status;
    }

    size_t size() const {
        return customers.size();
    }

    vector<Customer> getAll() const {
        vector<Customer> result;

        for (const auto& entry : customers) {
            result.push_back(entry.second);
        }

        return result;
    }
};

class NaturalKeyRegistry {
private:
    map<NaturalKey, string> records;

public:
    void registerEntity(
        const string& country,
        const string& identifier,
        const string& name
    ) {
        if (country.size() != 2 ||
            identifier.size() < 4 ||
            identifier.size() > 40 ||
            name.empty()) {
            throw ValidationError("Invalid natural key data.");
        }

        NaturalKey key{country, identifier};

        auto result = records.emplace(key, name);

        if (!result.second) {
            throw DuplicateKeyError("Natural key already registered.");
        }
    }

    string find(
        const string& country,
        const string& identifier
    ) const {
        NaturalKey key{country, identifier};

        auto iterator = records.find(key);

        if (iterator == records.end()) {
            throw NotFoundError("Natural key not found.");
        }

        return iterator->second;
    }

    size_t size() const {
        return records.size();
    }
};

class OrderRepository {
private:
    uint64_t nextOrderId = 1;
    map<uint64_t, Order> orders;
    const CustomerRepository& customers;

public:
    explicit OrderRepository(const CustomerRepository& repository)
        : customers(repository) {}

    Order create(uint64_t customerId, double amount) {
        const Customer& customer = customers.findById(customerId);

        if (customer.status != RecordStatus::Active) {
            throw ValidationError("Inactive customer cannot place orders.");
        }

        if (amount <= 0 || !isfinite(amount)) {
            throw ValidationError("Invalid order amount.");
        }

        Order order{
            nextOrderId++,
            customer.id,
            amount
        };

        orders.emplace(order.id, order);
        return order;
    }

    vector<Order> findByCustomer(uint64_t customerId) const {
        customers.findById(customerId);

        vector<Order> result;

        for (const auto& entry : orders) {
            if (entry.second.customerId == customerId) {
                result.push_back(entry.second);
            }
        }

        return result;
    }
};

class KeyDesignReport {
public:
    static void print() {
        cout << "\nKEY STRATEGY COMPARISON\n";

        cout << left
             << setw(20) << "Strategy"
             << setw(25) << "Generation"
             << setw(25) << "Primary consideration"
             << "\n";

        cout << string(70, '-') << "\n";

        cout << setw(20) << "IDENTITY"
             << setw(25) << "Database sequence"
             << setw(25) << "Compact storage" << "\n";

        cout << setw(20) << "UUID"
             << setw(25) << "Distributed generator"
             << setw(25) << "Global uniqueness" << "\n";

        cout << setw(20) << "NATURAL"
             << setw(25) << "Business attributes"
             << setw(25) << "Business uniqueness" << "\n";
    }
};

int main() {
    try {
        cout << "SURROGATE VS NATURAL KEYS\n";
        cout << string(65, '=') << "\n";

        CustomerRepository customers;

        Customer alice = customers.create(
            "alice@example.com",
            "Alice Sharma",
            "IN"
        );

        Customer bob = customers.create(
            "bob@example.com",
            "Bob Verma",
            "IN"
        );

        cout << "\n1. Generated surrogate identifiers\n";

        for (const Customer& customer : customers.getAll()) {
            cout << "ID: " << customer.id
                 << " | UUID: " << customer.publicId.value
                 << " | Email: " << customer.email
                 << "\n";
        }

        cout << "\n2. UUID lookup\n";

        const Customer& retrieved =
            customers.findByUUID(alice.publicId);

        cout << "Retrieved: " << retrieved.name << "\n";

        cout << "\n3. Natural identifier modification\n";

        uint64_t oldId = alice.id;
        string oldUUID = alice.publicId.value;

        customers.updateEmail(
            alice.id,
            "alice.sharma@example.com"
        );

        const Customer& updated = customers.findById(alice.id);

        cout << "New email: " << updated.email << "\n";
        cout << "Identity unchanged: "
             << (updated.id == oldId) << "\n";
        cout << "UUID unchanged: "
             << (updated.publicId.value == oldUUID) << "\n";

        cout << "\n4. Composite natural key\n";

        NaturalKeyRegistry registry;

        registry.registerEntity("IN", "TAX-1001", "Indian Enterprise");
        registry.registerEntity("US", "TAX-1001", "US Enterprise");

        cout << "Composite records: " << registry.size() << "\n";

        cout << "Natural key lookup: "
             << registry.find("IN", "TAX-1001") << "\n";

        cout << "\n5. Referential integrity simulation\n";

        OrderRepository orders(customers);

        Order first = orders.create(alice.id, 25000.00);
        Order second = orders.create(bob.id, 45000.00);

        cout << "Order " << first.id
             << " references customer " << first.customerId << "\n";

        cout << "Order " << second.id
             << " references customer " << second.customerId << "\n";

        cout << "\n6. Duplicate natural key handling\n";

        try {
            registry.registerEntity(
                "IN",
                "TAX-1001",
                "Duplicate Enterprise"
            );
        } catch (const DuplicateKeyError& error) {
            cout << "Rejected: " << error.what() << "\n";
        }

        cout << "\n7. Invalid order handling\n";

        try {
            orders.create(alice.id, -500.00);
        } catch (const ValidationError& error) {
            cout << "Rejected: " << error.what() << "\n";
        }

        cout << "\n8. Inactive customer handling\n";

        customers.changeStatus(bob.id, RecordStatus::Suspended);

        try {
            orders.create(bob.id, 1000.00);
        } catch (const ValidationError& error) {
            cout << "Rejected: " << error.what() << "\n";
        }

        cout << "\n9. Performance-oriented access\n";

        cout << "Customer records: " << customers.size() << "\n";
        cout << "UUID and email indexes provide average O(1) lookup.\n";
        cout << "Ordered identity map provides O(log n) lookup.\n";
        cout << "Composite natural map provides O(log n) lookup.\n";

        KeyDesignReport::print();

        cout << "\nExecution completed successfully.\n";

    } catch (const exception& error) {
        cerr << "Application error: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
