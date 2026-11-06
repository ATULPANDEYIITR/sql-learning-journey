#include <algorithm>
#include <cmath>
#include <cstdint>
#include <exception>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;

enum class DataType {
    Integer,
    Text,
    Decimal,
    Boolean
};

enum class DeleteAction {
    Restrict,
    Cascade,
    SetNull
};

struct ColumnDefinition {
    string name;
    DataType type;
    bool nullable = true;
    bool unique = false;
    bool primaryKey = false;
};

struct ForeignKeyDefinition {
    vector<string> columns;
    string referencedTable;
    vector<string> referencedColumns;
    DeleteAction onDelete = DeleteAction::Restrict;
};

struct TableDefinition {
    string name;
    vector<ColumnDefinition> columns;
    vector<string> primaryKey;
    vector<vector<string>> uniqueConstraints;
    vector<ForeignKeyDefinition> foreignKeys;
};

using Value = string;

using Record = map<string, Value>;

class SchemaException : public runtime_error {
public:
    explicit SchemaException(const string& message)
        : runtime_error(message) {}
};

class SchemaCatalog {
private:
    map<string, TableDefinition> tables;

    static bool validIdentifier(const string& name) {
        if (name.empty() || name[0] < 'a' || name[0] > 'z') {
            return false;
        }

        return all_of(name.begin(), name.end(), [](unsigned char c) {
            return (c >= 'a' && c <= 'z') ||
                   (c >= '0' && c <= '9') ||
                   c == '_';
        });
    }

public:
    void addTable(const TableDefinition& table) {
        if (!validIdentifier(table.name)) {
            throw SchemaException("Invalid table name.");
        }

        if (tables.count(table.name)) {
            throw SchemaException("Duplicate table.");
        }

        if (table.columns.empty()) {
            throw SchemaException("Table requires columns.");
        }

        set<string> columnNames;

        for (const auto& column : table.columns) {
            if (!validIdentifier(column.name)) {
                throw SchemaException("Invalid column name.");
            }

            if (!columnNames.insert(column.name).second) {
                throw SchemaException("Duplicate column.");
            }

            if (column.primaryKey && column.nullable) {
                throw SchemaException(
                    "Primary key cannot be nullable."
                );
            }
        }

        auto validateColumns = [&](const vector<string>& columns) {
            if (columns.empty()) {
                throw SchemaException("Empty key definition.");
            }

            set<string> uniqueNames;

            for (const auto& name : columns) {
                if (!columnNames.count(name)) {
                    throw SchemaException("Unknown key column.");
                }

                if (!uniqueNames.insert(name).second) {
                    throw SchemaException("Duplicate key column.");
                }
            }
        };

        validateColumns(table.primaryKey);

        for (const auto& uniqueKey : table.uniqueConstraints) {
            validateColumns(uniqueKey);
        }

        for (const auto& fk : table.foreignKeys) {
            validateColumns(fk.columns);

            if (fk.columns.size() != fk.referencedColumns.size()) {
                throw SchemaException("Foreign key size mismatch.");
            }
        }

        tables.emplace(table.name, table);
    }

    const TableDefinition& get(const string& name) const {
        auto iterator = tables.find(name);

        if (iterator == tables.end()) {
            throw SchemaException("Unknown table: " + name);
        }

        return iterator->second;
    }

    void validateRelationships() const {
        for (const auto& [name, table] : tables) {
            for (const auto& fk : table.foreignKeys) {
                const auto& parent = get(fk.referencedTable);

                bool found = false;

                if (parent.primaryKey == fk.referencedColumns) {
                    found = true;
                }

                for (const auto& uniqueKey : parent.uniqueConstraints) {
                    if (uniqueKey == fk.referencedColumns) {
                        found = true;
                    }
                }

                if (!found) {
                    throw SchemaException(
                        "Foreign key must reference a candidate key."
                    );
                }
            }
        }
    }

    vector<string> creationOrder() const {
        set<string> visited;
        set<string> active;
        vector<string> result;

        function<void(const string&)> visit =
            [&](const string& name) {
                if (active.count(name)) {
                    throw SchemaException(
                        "Circular table dependency detected."
                    );
                }

                if (visited.count(name)) return;

                active.insert(name);

                const auto& table = get(name);

                for (const auto& fk : table.foreignKeys) {
                    visit(fk.referencedTable);
                }

                active.erase(name);
                visited.insert(name);
                result.push_back(name);
            };

        for (const auto& [name, table] : tables) {
            visit(name);
        }

        return result;
    }

    void print() const {
        cout << "\nSCHEMA CATALOG\n";

        for (const auto& name : creationOrder()) {
            const auto& table = get(name);

            cout << "\n" << table.name << "\n";

            for (const auto& column : table.columns) {
                cout << "  " << column.name;

                if (column.primaryKey) cout << " PK";
                if (!column.nullable) cout << " NOT NULL";
                if (column.unique) cout << " UNIQUE";

                cout << "\n";
            }

            for (const auto& fk : table.foreignKeys) {
                cout << "  FK -> " << fk.referencedTable << "\n";
            }
        }
    }
};

class TransactionalDatabase {
private:
    const SchemaCatalog& catalog;
    map<string, vector<Record>> storage;

    static double parseDecimal(const string& value) {
        size_t processed = 0;
        double result = stod(value, &processed);

        if (processed != value.size() || !isfinite(result)) {
            throw SchemaException("Invalid numeric value.");
        }

        return result;
    }

    static string keyFor(
        const Record& record,
        const vector<string>& columns
    ) {
        stringstream stream;

        for (const auto& column : columns) {
            auto iterator = record.find(column);

            if (iterator == record.end()) {
                throw SchemaException("Missing key value.");
            }

            stream << iterator->second.size()
                   << ":" << iterator->second << "|";
        }

        return stream.str();
    }

    void validateRecord(
        const string& tableName,
        const Record& record
    ) const {
        const auto& table = catalog.get(tableName);

        set<string> allowed;

        for (const auto& column : table.columns) {
            allowed.insert(column.name);

            auto iterator = record.find(column.name);

            if (iterator == record.end()) {
                if (!column.nullable && !column.primaryKey) {
                    throw SchemaException(
                        "Missing required column: " + column.name
                    );
                }
            }
        }

        for (const auto& [name, value] : record) {
            if (!allowed.count(name)) {
                throw SchemaException("Unknown column: " + name);
            }
        }

        for (const auto& fk : table.foreignKeys) {
            bool allNull = true;
            bool partiallyNull = false;

            vector<string> values;

            for (const auto& column : fk.columns) {
                auto iterator = record.find(column);

                if (iterator == record.end() || iterator->second.empty()) {
                    partiallyNull = !allNull;
                    continue;
                }

                allNull = false;
                values.push_back(iterator->second);
            }

            if (allNull) continue;

            if (partiallyNull || values.size() != fk.columns.size()) {
                throw SchemaException(
                    "Composite foreign key is partially NULL."
                );
            }

            bool found = false;

            for (const auto& parent : storage.at(fk.referencedTable)) {
                bool matches = true;

                for (size_t i = 0; i < fk.columns.size(); ++i) {
                    if (
                        parent.at(fk.referencedColumns[i]) != values[i]
                    ) {
                        matches = false;
                        break;
                    }
                }

                if (matches) {
                    found = true;
                    break;
                }
            }

            if (!found) {
                throw SchemaException("Foreign key violation.");
            }
        }

        for (const auto& uniqueKey : table.uniqueConstraints) {
            bool hasNull = false;

            for (const auto& column : uniqueKey) {
                auto iterator = record.find(column);

                if (
                    iterator == record.end() ||
                    iterator->second.empty()
                ) {
                    hasNull = true;
                }
            }

            if (hasNull) continue;

            const string candidate = keyFor(record, uniqueKey);

            for (const auto& existing : storage.at(tableName)) {
                if (keyFor(existing, uniqueKey) == candidate) {
                    throw SchemaException("Unique constraint violation.");
                }
            }
        }

        for (const auto& column : table.columns) {
            auto iterator = record.find(column.name);

            if (iterator == record.end()) continue;

            if (
                column.type == DataType::Decimal &&
                parseDecimal(iterator->second) < 0 &&
                column.name == "unit_price"
            ) {
                throw SchemaException("Unit price cannot be negative.");
            }

            if (
                column.type == DataType::Integer &&
                column.name == "quantity"
            ) {
                double value = parseDecimal(iterator->second);

                if (
                    value <= 0 ||
                    floor(value) != value
                ) {
                    throw SchemaException(
                        "Quantity must be a positive integer."
                    );
                }
            }
        }
    }

public:
    explicit TransactionalDatabase(const SchemaCatalog& schema)
        : catalog(schema) {
        for (const auto& name : catalog.creationOrder()) {
            storage[name] = {};
        }
    }

    void insert(const string& tableName, const Record& record) {
        const auto& table = catalog.get(tableName);

        validateRecord(tableName, record);

        string primaryKey = keyFor(record, table.primaryKey);

        for (const auto& existing : storage.at(tableName)) {
            if (keyFor(existing, table.primaryKey) == primaryKey) {
                throw SchemaException("Duplicate primary key.");
            }
        }

        storage.at(tableName).push_back(record);
    }

    void insertAtomically(
        const vector<pair<string, Record>>& operations
    ) {
        // Snapshot provides rollback for this in-memory demonstration.
        auto snapshot = storage;

        try {
            for (const auto& [table, record] : operations) {
                insert(table, record);
            }
        } catch (...) {
            storage = move(snapshot);
            throw;
        }
    }

    const vector<Record>& rows(const string& table) const {
        catalog.get(table);
        return storage.at(table);
    }

    void printOrders() const {
        cout << "\nORDER REPORT\n";

        const auto& orders = rows("orders");
        const auto& customers = rows("customers");
        const auto& items = rows("order_items");

        for (const auto& order : orders) {
            string customerName = "Unknown";

            for (const auto& customer : customers) {
                if (
                    customer.at("customer_id") ==
                    order.at("customer_id")
                ) {
                    customerName = customer.at("full_name");
                    break;
                }
            }

            double total = 0;
            int count = 0;

            for (const auto& item : items) {
                if (item.at("order_id") == order.at("order_id")) {
                    total +=
                        parseDecimal(item.at("unit_price")) *
                        parseDecimal(item.at("quantity"));

                    count++;
                }
            }

            cout << "Order " << order.at("order_id")
                 << " | Customer: " << customerName
                 << " | Items: " << count
                 << " | Total: " << fixed << setprecision(2)
                 << total << "\n";
        }
    }
};

SchemaCatalog buildSchema() {
    SchemaCatalog schema;

    schema.addTable({
        "customers",
        {
            {"customer_id", DataType::Integer, false, false, true},
            {"email", DataType::Text, false, true, false},
            {"full_name", DataType::Text, false, false, false}
        },
        {"customer_id"},
        {{"email"}},
        {}
    });

    schema.addTable({
        "products",
        {
            {"product_id", DataType::Integer, false, false, true},
            {"sku", DataType::Text, false, true, false},
            {"product_name", DataType::Text, false, false, false},
            {"unit_price", DataType::Decimal, false, false, false}
        },
        {"product_id"},
        {{"sku"}},
        {}
    });

    schema.addTable({
        "orders",
        {
            {"order_id", DataType::Integer, false, false, true},
            {"customer_id", DataType::Integer, false, false, false},
            {"order_status", DataType::Text, false, false, false}
        },
        {"order_id"},
        {},
        {
            {
                {"customer_id"},
                "customers",
                {"customer_id"},
                DeleteAction::Restrict
            }
        }
    });

    schema.addTable({
        "order_items",
        {
            {"order_item_id", DataType::Integer, false, false, true},
            {"order_id", DataType::Integer, false, false, false},
            {"product_id", DataType::Integer, false, false, false},
            {"quantity", DataType::Integer, false, false, false},
            {"unit_price", DataType::Decimal, false, false, false}
        },
        {"order_item_id"},
        {{"order_id", "product_id"}},
        {
            {
                {"order_id"},
                "orders",
                {"order_id"},
                DeleteAction::Cascade
            },
            {
                {"product_id"},
                "products",
                {"product_id"},
                DeleteAction::Restrict
            }
        }
    });

    schema.validateRelationships();

    return schema;
}

int main() {
    try {
        SchemaCatalog schema = buildSchema();
        schema.print();

        TransactionalDatabase database(schema);

        database.insertAtomically({
            {
                "customers",
                {
                    {"customer_id", "1"},
                    {"email", "aarav@example.com"},
                    {"full_name", "Aarav Sharma"}
                }
            },
            {
                "products",
                {
                    {"product_id", "101"},
                    {"sku", "SKU-101"},
                    {"product_name", "Laptop"},
                    {"unit_price", "65000.00"}
                }
            },
            {
                "products",
                {
                    {"product_id", "102"},
                    {"sku", "SKU-102"},
                    {"product_name", "Keyboard"},
                    {"unit_price", "1500.00"}
                }
            },
            {
                "orders",
                {
                    {"order_id", "5001"},
                    {"customer_id", "1"},
                    {"order_status", "PENDING"}
                }
            },
            {
                "order_items",
                {
                    {"order_item_id", "9001"},
                    {"order_id", "5001"},
                    {"product_id", "101"},
                    {"quantity", "1"},
                    {"unit_price", "65000.00"}
                }
            },
            {
                "order_items",
                {
                    {"order_item_id", "9002"},
                    {"order_id", "5001"},
                    {"product_id", "102"},
                    {"quantity", "2"},
                    {"unit_price", "1500.00"}
                }
            }
        });

        database.printOrders();

        cout << "\nFAILURE TESTS\n";

        vector<pair<string, Record>> invalidOperations = {
            {
                "orders",
                {
                    {"order_id", "5002"},
                    {"customer_id", "999"},
                    {"order_status", "PENDING"}
                }
            }
        };

        try {
            database.insertAtomically(invalidOperations);
        } catch (const SchemaException& error) {
            cout << "Foreign key rejected: " << error.what() << "\n";
        }

        try {
            database.insert("order_items", {
                {"order_item_id", "9003"},
                {"order_id", "5001"},
                {"product_id", "101"},
                {"quantity", "0"},
                {"unit_price", "65000"}
            });
        } catch (const SchemaException& error) {
            cout << "CHECK constraint rejected: "
                 << error.what() << "\n";
        }

        try {
            database.insert("customers", {
                {"customer_id", "2"},
                {"email", "aarav@example.com"},
                {"full_name", "Duplicate Customer"}
            });
        } catch (const SchemaException& error) {
            cout << "UNIQUE constraint rejected: "
                 << error.what() << "\n";
        }

        cout << "\nFinal order count: "
             << database.rows("orders").size() << "\n";

        cout << "Schema and transaction tests completed.\n";
    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
