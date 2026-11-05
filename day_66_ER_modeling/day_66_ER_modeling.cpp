#include <algorithm>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <optional>

using namespace std;

/*
 * ER Modeling: Retail Order Management System.
 *
 * Implements:
 * - Entity definitions
 * - Attributes and keys
 * - Binary relationships
 * - Cardinality constraints
 * - Participation constraints
 * - Relationship attributes
 * - Record validation
 * - Referential integrity
 * - Relational mapping
 *
 * Compile:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic er_model.cpp -o er_model
 */

enum class DataType {
    INTEGER,
    VARCHAR,
    DECIMAL,
    BOOLEAN
};

enum class Participation {
    TOTAL,
    PARTIAL
};

enum class Cardinality {
    ONE_TO_ONE,
    ONE_TO_MANY,
    MANY_TO_ONE,
    MANY_TO_MANY
};

string toString(DataType type) {
    switch (type) {
        case DataType::INTEGER: return "INTEGER";
        case DataType::VARCHAR: return "VARCHAR";
        case DataType::DECIMAL: return "DECIMAL";
        case DataType::BOOLEAN: return "BOOLEAN";
    }

    throw logic_error("Unknown data type.");
}

string toString(Cardinality cardinality) {
    switch (cardinality) {
        case Cardinality::ONE_TO_ONE: return "1:1";
        case Cardinality::ONE_TO_MANY: return "1:N";
        case Cardinality::MANY_TO_ONE: return "N:1";
        case Cardinality::MANY_TO_MANY: return "M:N";
    }

    throw logic_error("Unknown cardinality.");
}

string toString(Participation participation) {
    return participation == Participation::TOTAL
        ? "TOTAL"
        : "PARTIAL";
}

struct Attribute {
    string name;
    DataType type;
    bool primaryKey = false;
    bool unique = false;
    bool nullable = true;
};

struct Entity {
    string name;
    vector<Attribute> attributes;

    Entity(string name, vector<Attribute> attributes)
        : name(move(name)), attributes(move(attributes)) {

        if (this->name.empty()) {
            throw invalid_argument("Entity name cannot be empty.");
        }

        unordered_set<string> names;
        int primaryKeys = 0;

        for (const auto& attribute : this->attributes) {
            if (attribute.name.empty()) {
                throw invalid_argument("Attribute name cannot be empty.");
            }

            if (!names.insert(attribute.name).second) {
                throw invalid_argument("Duplicate entity attribute.");
            }

            if (attribute.primaryKey) {
                ++primaryKeys;
            }
        }

        if (primaryKeys == 0) {
            throw invalid_argument(
                "Every entity requires a primary key."
            );
        }
    }

    const Attribute& getAttribute(const string& name) const {
        auto it = find_if(
            attributes.begin(),
            attributes.end(),
            [&](const Attribute& attribute) {
                return attribute.name == name;
            }
        );

        if (it == attributes.end()) {
            throw invalid_argument("Attribute not found: " + name);
        }

        return *it;
    }

    string primaryKey() const {
        for (const auto& attribute : attributes) {
            if (attribute.primaryKey) {
                return attribute.name;
            }
        }

        throw logic_error("Primary key missing.");
    }
};

struct RelationshipEnd {
    string entity;
    int minimum;
    optional<int> maximum;
    Participation participation;

    void validate() const {
        if (minimum != 0 && minimum != 1) {
            throw invalid_argument("Invalid minimum cardinality.");
        }

        if (maximum.has_value() && *maximum != 1) {
            throw invalid_argument("Maximum must be 1 or N.");
        }

        Participation expected = minimum == 1
            ? Participation::TOTAL
            : Participation::PARTIAL;

        if (participation != expected) {
            throw invalid_argument(
                "Participation conflicts with minimum cardinality."
            );
        }
    }

    bool isMany() const {
        return !maximum.has_value();
    }
};

struct Relationship {
    string name;
    RelationshipEnd left;
    RelationshipEnd right;
    vector<Attribute> attributes;

    Cardinality cardinality() const {
        bool leftMany = left.isMany();
        bool rightMany = right.isMany();

        if (leftMany && rightMany) {
            return Cardinality::MANY_TO_MANY;
        }

        if (leftMany) {
            return Cardinality::ONE_TO_MANY;
        }

        if (rightMany) {
            return Cardinality::MANY_TO_ONE;
        }

        return Cardinality::ONE_TO_ONE;
    }
};

class ERModel {
private:
    unordered_map<string, Entity> entities;
    unordered_map<string, Relationship> relationships;

public:
    string name;

    explicit ERModel(string name)
        : name(move(name)) {}

    void addEntity(Entity entity) {
        if (entities.count(entity.name)) {
            throw invalid_argument("Duplicate entity: " + entity.name);
        }

        entities.emplace(entity.name, move(entity));
    }

    void addRelationship(Relationship relationship) {
        if (relationships.count(relationship.name)) {
            throw invalid_argument("Duplicate relationship.");
        }

        relationship.left.validate();
        relationship.right.validate();

        if (
            !entities.count(relationship.left.entity) ||
            !entities.count(relationship.right.entity)
        ) {
            throw invalid_argument(
                "Relationship references an unknown entity."
            );
        }

        unordered_set<string> names;

        for (const auto& attribute : relationship.attributes) {
            if (!names.insert(attribute.name).second) {
                throw invalid_argument(
                    "Duplicate relationship attribute."
                );
            }
        }

        relationships.emplace(
            relationship.name,
            move(relationship)
        );
    }

    const Entity& getEntity(const string& name) const {
        auto it = entities.find(name);

        if (it == entities.end()) {
            throw invalid_argument("Unknown entity: " + name);
        }

        return it->second;
    }

    const Relationship& getRelationship(const string& name) const {
        auto it = relationships.find(name);

        if (it == relationships.end()) {
            throw invalid_argument("Unknown relationship: " + name);
        }

        return it->second;
    }

    void describe() const {
        cout << "\nER MODEL: " << name << "\n";

        cout << "\nENTITIES\n";

        for (const auto& [name, entity] : entities) {
            cout << "\n" << name << "\n";

            for (const auto& attribute : entity.attributes) {
                cout << "  " << attribute.name
                     << " : " << toString(attribute.type);

                if (attribute.primaryKey) {
                    cout << " [PK]";
                }

                if (attribute.unique) {
                    cout << " [UNIQUE]";
                }

                if (!attribute.nullable) {
                    cout << " [NOT NULL]";
                }

                cout << "\n";
            }
        }

        cout << "\nRELATIONSHIPS\n";

        for (const auto& [name, relationship] : relationships) {
            cout << name << ": "
                 << relationship.left.entity << " <-> "
                 << relationship.right.entity
                 << " | " << toString(relationship.cardinality())
                 << "\n";

            cout << "  Left participation: "
                 << toString(relationship.left.participation)
                 << "\n";

            cout << "  Right participation: "
                 << toString(relationship.right.participation)
                 << "\n";
        }
    }

    void printRelationalMapping() const {
        cout << "\nRELATIONAL MAPPING\n";

        for (const auto& [name, relationship] : relationships) {
            cout << name << ": ";

            switch (relationship.cardinality()) {
                case Cardinality::MANY_TO_MANY:
                    cout << "Create junction table with two foreign keys";
                    break;

                case Cardinality::ONE_TO_ONE:
                    cout << "Use a UNIQUE foreign key";
                    break;

                case Cardinality::ONE_TO_MANY:
                    cout << "Place foreign key on "
                         << relationship.left.entity;
                    break;

                case Cardinality::MANY_TO_ONE:
                    cout << "Place foreign key on "
                         << relationship.right.entity;
                    break;
            }

            cout << "\n";

            if (!relationship.attributes.empty()) {
                cout << "  Relationship attributes: ";

                for (const auto& attribute : relationship.attributes) {
                    cout << attribute.name << " ";
                }

                cout << "\n";
            }
        }
    }
};

struct CustomerRecord {
    int customerId;
    string name;
    string email;
};

struct ProductRecord {
    int productId;
    string name;
    double price;
};

struct OrderRecord {
    int orderId;
    int customerId;
    string status;
};

struct OrderLineRecord {
    int orderId;
    int productId;
    int quantity;
};

class RetailDatabase {
private:
    unordered_map<int, CustomerRecord> customers;
    unordered_map<int, ProductRecord> products;
    unordered_map<int, OrderRecord> orders;

    // Composite key represents the M:N junction table.
    map<pair<int, int>, OrderLineRecord> orderLines;

public:
    void addCustomer(CustomerRecord customer) {
        if (customer.customerId <= 0 || customer.name.empty()) {
            throw invalid_argument("Invalid customer.");
        }

        if (customer.email.empty()) {
            throw invalid_argument("Customer email is required.");
        }

        for (const auto& [id, existing] : customers) {
            if (existing.email == customer.email) {
                throw invalid_argument("Duplicate customer email.");
            }
        }

        if (!customers.emplace(
            customer.customerId,
            move(customer)
        ).second) {
            throw invalid_argument("Duplicate customer ID.");
        }
    }

    void addProduct(ProductRecord product) {
        if (
            product.productId <= 0 ||
            product.name.empty() ||
            product.price < 0
        ) {
            throw invalid_argument("Invalid product.");
        }

        if (!products.emplace(
            product.productId,
            move(product)
        ).second) {
            throw invalid_argument("Duplicate product ID.");
        }
    }

    void addOrder(OrderRecord order) {
        if (order.orderId <= 0) {
            throw invalid_argument("Invalid order ID.");
        }

        if (!customers.count(order.customerId)) {
            throw invalid_argument("Order has no valid customer.");
        }

        if (
            order.status != "PENDING" &&
            order.status != "CONFIRMED" &&
            order.status != "CANCELLED"
        ) {
            throw invalid_argument("Invalid order status.");
        }

        if (!orders.emplace(
            order.orderId,
            move(order)
        ).second) {
            throw invalid_argument("Duplicate order ID.");
        }
    }

    void addOrderLine(OrderLineRecord line) {
        if (!orders.count(line.orderId)) {
            throw invalid_argument("Order does not exist.");
        }

        if (!products.count(line.productId)) {
            throw invalid_argument("Product does not exist.");
        }

        if (line.quantity <= 0) {
            throw invalid_argument("Quantity must be positive.");
        }

        auto key = make_pair(line.orderId, line.productId);

        if (!orderLines.emplace(key, line).second) {
            throw invalid_argument(
                "Duplicate product within an order."
            );
        }
    }

    double orderTotal(int orderId) const {
        if (!orders.count(orderId)) {
            throw invalid_argument("Order not found.");
        }

        double total = 0;

        for (const auto& [key, line] : orderLines) {
            if (line.orderId == orderId) {
                total +=
                    products.at(line.productId).price *
                    line.quantity;
            }
        }

        return total;
    }

    void validateParticipation() const {
        // Every order must have at least one order line.
        for (const auto& [orderId, order] : orders) {
            bool found = false;

            for (const auto& [key, line] : orderLines) {
                if (line.orderId == orderId) {
                    found = true;
                    break;
                }
            }

            if (!found) {
                throw logic_error(
                    "Order " + to_string(orderId) +
                    " violates total participation."
                );
            }
        }
    }

    void report() const {
        cout << "\nRETAIL ORDER REPORT\n";

        for (const auto& [orderId, order] : orders) {
            const auto& customer = customers.at(order.customerId);

            cout << "Order " << orderId
                 << " | Customer: " << customer.name
                 << " | Status: " << order.status
                 << " | Total: " << orderTotal(orderId)
                 << "\n";
        }

        cout << "\nOrder lines: " << orderLines.size() << "\n";
    }

    size_t customerCount() const {
        return customers.size();
    }

    size_t productCount() const {
        return products.size();
    }

    size_t orderCount() const {
        return orders.size();
    }

    size_t orderLineCount() const {
        return orderLines.size();
    }
};

RelationshipEnd endpoint(
    const string& entity,
    int minimum,
    optional<int> maximum
) {
    return {
        entity,
        minimum,
        maximum,
        minimum == 1
            ? Participation::TOTAL
            : Participation::PARTIAL
    };
}

ERModel buildModel() {
    ERModel model("Retail Order Management");

    model.addEntity(Entity("Customer", {
        {"customer_id", DataType::INTEGER, true, true, false},
        {"name", DataType::VARCHAR, false, false, false},
        {"email", DataType::VARCHAR, false, true, false}
    }));

    model.addEntity(Entity("Product", {
        {"product_id", DataType::INTEGER, true, true, false},
        {"product_name", DataType::VARCHAR, false, false, false},
        {"unit_price", DataType::DECIMAL, false, false, false}
    }));

    model.addEntity(Entity("Order", {
        {"order_id", DataType::INTEGER, true, true, false},
        {"order_date", DataType::VARCHAR, false, false, false},
        {"status", DataType::VARCHAR, false, false, false}
    }));

    model.addEntity(Entity("OrderLine", {
        {"order_id", DataType::INTEGER, true, false, false},
        {"product_id", DataType::INTEGER, true, false, false},
        {"quantity", DataType::INTEGER, false, false, false}
    }));

    model.addRelationship({
        "CustomerOrder",
        endpoint("Customer", 0, nullopt),
        endpoint("Order", 1, 1),
        {}
    });

    model.addRelationship({
        "OrderOrderLine",
        endpoint("Order", 1, nullopt),
        endpoint("OrderLine", 1, 1),
        {}
    });

    model.addRelationship({
        "ProductOrderLine",
        endpoint("Product", 0, nullopt),
        endpoint("OrderLine", 1, 1),
        {}
    });

    model.addRelationship({
        "OrderProduct",
        endpoint("Order", 1, nullopt),
        endpoint("Product", 0, nullopt),
        {
            {"quantity", DataType::INTEGER, false, false, false}
        }
    });

    return model;
}

void runTests() {
    RetailDatabase database;

    database.addCustomer({
        1,
        "Aarav Sharma",
        "aarav@example.com"
    });

    database.addCustomer({
        2,
        "Diya Verma",
        "diya@example.com"
    });

    database.addProduct({
        101,
        "Laptop",
        65000.00
    });

    database.addProduct({
        102,
        "Wireless Mouse",
        1200.00
    });

    database.addProduct({
        103,
        "Keyboard",
        2500.00
    });

    database.addOrder({
        5001,
        1,
        "CONFIRMED"
    });

    database.addOrder({
        5002,
        2,
        "PENDING"
    });

    database.addOrderLine({
        5001,
        101,
        1
    });

    database.addOrderLine({
        5001,
        102,
        2
    });

    database.addOrderLine({
        5002,
        103,
        1
    });

    database.validateParticipation();

    const double expected = 67400.00;

    if (database.orderTotal(5001) != expected) {
        throw logic_error("Order total calculation failed.");
    }

    cout << "\nVALIDATION TESTS\n";
    cout << "PASS: Customer entity creation\n";
    cout << "PASS: Product entity creation\n";
    cout << "PASS: Order entity creation\n";
    cout << "PASS: M:N junction table\n";
    cout << "PASS: Referential integrity\n";
    cout << "PASS: Total participation\n";
    cout << "PASS: Order total calculation\n";

    bool rejected = false;

    try {
        database.addOrder({
            5003,
            999,
            "PENDING"
        });
    } catch (const invalid_argument&) {
        rejected = true;
    }

    if (!rejected) {
        throw logic_error("Invalid foreign key test failed.");
    }

    cout << "PASS: Invalid foreign key rejection\n";

    rejected = false;

    try {
        database.addOrderLine({
            5001,
            101,
            0
        });
    } catch (const invalid_argument&) {
        rejected = true;
    }

    if (!rejected) {
        throw logic_error("Quantity validation test failed.");
    }

    cout << "PASS: Quantity constraint\n";

    database.report();
}

int main() {
    try {
        ERModel model = buildModel();

        model.describe();
        model.printRelationalMapping();

        runTests();

        cout << "\nER modeling program completed.\n";
    } catch (const exception& error) {
        cerr << "ERROR: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
