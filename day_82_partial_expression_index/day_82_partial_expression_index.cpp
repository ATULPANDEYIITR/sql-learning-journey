#include <algorithm>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;

/*
 * PARTIAL AND EXPRESSION INDEXES
 *
 * C++17 repository-independent index eligibility engine.
 *
 * Models:
 * - Database rows
 * - Full indexes
 * - Partial indexes
 * - Expression indexes
 * - Partial expression indexes
 * - Index key generation
 * - Predicate implication
 * - Unique constraints
 * - Index maintenance
 * - Query-plan candidate selection
 * - Cost-based candidate ranking
 */

// ============================================================
// 1. DOMAIN MODEL
// ============================================================

enum class Status {
    OPEN,
    PAID,
    CANCELLED,
    ARCHIVED
};

enum class IndexKind {
    FULL,
    PARTIAL,
    EXPRESSION,
    PARTIAL_EXPRESSION
};

enum class Operator {
    EQUAL,
    GREATER_THAN,
    GREATER_THAN_OR_EQUAL,
    LESS_THAN,
    LESS_THAN_OR_EQUAL
};

struct Order {
    int id;
    string email;
    Status status;
    double amount;
    string region;
};

string statusName(Status status) {
    switch (status) {
        case Status::OPEN: return "OPEN";
        case Status::PAID: return "PAID";
        case Status::CANCELLED: return "CANCELLED";
        case Status::ARCHIVED: return "ARCHIVED";
    }

    throw invalid_argument("Unknown status.");
}

void validateOrder(const Order& order) {
    if (order.id <= 0) {
        throw invalid_argument("Order ID must be positive.");
    }

    if (
        order.email.empty() ||
        order.email.find('@') == string::npos
    ) {
        throw invalid_argument("Invalid email.");
    }

    if (!isfinite(order.amount) || order.amount < 0) {
        throw invalid_argument("Invalid amount.");
    }

    if (order.region.empty()) {
        throw invalid_argument("Region cannot be empty.");
    }
}

// ============================================================
// 2. EXPRESSION EVALUATION
// ============================================================

class ExpressionEngine {
public:
    static string normalize(const string& value) {
        string result = value;

        transform(
            result.begin(),
            result.end(),
            result.begin(),
            [](unsigned char c) {
                return static_cast<char>(tolower(c));
            }
        );

        return result;
    }

    static string uppercase(const string& value) {
        string result = value;

        transform(
            result.begin(),
            result.end(),
            result.begin(),
            [](unsigned char c) {
                return static_cast<char>(toupper(c));
            }
        );

        return result;
    }

    static string evaluate(
        const Order& order,
        const string& expression
    ) {
        if (expression == "email") {
            return order.email;
        }

        if (expression == "lower(email)") {
            return normalize(order.email);
        }

        if (expression == "upper(region)") {
            return uppercase(order.region);
        }

        if (expression == "status") {
            return statusName(order.status);
        }

        if (expression == "amount") {
            return to_string(order.amount);
        }

        if (expression == "id") {
            return to_string(order.id);
        }

        throw invalid_argument(
            "Unsupported expression: " + expression
        );
    }
};

// ============================================================
// 3. PREDICATE MODEL
// ============================================================

struct Predicate {
    optional<Status> status;
    optional<double> minimumAmount;
    bool strictMinimum = true;

    bool matches(const Order& order) const {
        if (status && order.status != *status) {
            return false;
        }

        if (minimumAmount) {
            if (
                strictMinimum &&
                !(order.amount > *minimumAmount)
            ) {
                return false;
            }

            if (
                !strictMinimum &&
                !(order.amount >= *minimumAmount)
            ) {
                return false;
            }
        }

        return true;
    }

    string describe() const {
        string result;

        if (status) {
            result += "status = " + statusName(*status);
        }

        if (minimumAmount) {
            if (!result.empty()) {
                result += " AND ";
            }

            result += "amount ";
            result += strictMinimum ? "> " : ">= ";
            result += to_string(*minimumAmount);
        }

        return result.empty() ? "TRUE" : result;
    }
};

// ============================================================
// 4. INDEX DEFINITION
// ============================================================

struct IndexDefinition {
    string name;
    IndexKind kind;
    string expression;
    optional<Predicate> predicate;
    bool unique = false;
};

void validateIndex(const IndexDefinition& index) {
    if (index.name.empty() || index.expression.empty()) {
        throw invalid_argument("Index name and expression required.");
    }

    bool needsPredicate =
        index.kind == IndexKind::PARTIAL ||
        index.kind == IndexKind::PARTIAL_EXPRESSION;

    if (needsPredicate != index.predicate.has_value()) {
        throw invalid_argument(
            "Index type and predicate are inconsistent."
        );
    }

    const set<string> supported = {
        "email",
        "lower(email)",
        "upper(region)",
        "status",
        "amount",
        "id"
    };

    if (!supported.count(index.expression)) {
        throw invalid_argument("Unsupported index expression.");
    }
}

// ============================================================
// 5. INDEX STORAGE
// ============================================================

class DatabaseIndex {
private:
    IndexDefinition definition;

    map<string, set<int>> entries;

public:
    explicit DatabaseIndex(IndexDefinition definition)
        : definition(std::move(definition)) {
        validateIndex(this->definition);
    }

    const string& name() const {
        return definition.name;
    }

    const string& expression() const {
        return definition.expression;
    }

    const optional<Predicate>& predicate() const {
        return definition.predicate;
    }

    bool unique() const {
        return definition.unique;
    }

    size_t entryCount() const {
        return entries.size();
    }

    bool contains(int id, const string& key) const {
        auto it = entries.find(key);

        return it != entries.end() &&
               it->second.count(id) > 0;
    }

    void insert(const Order& order) {
        if (
            definition.predicate &&
            !definition.predicate->matches(order)
        ) {
            return;
        }

        string key = ExpressionEngine::evaluate(
            order,
            definition.expression
        );

        auto& matchingIds = entries[key];

        if (definition.unique && !matchingIds.empty()) {
            if (!matchingIds.count(order.id)) {
                throw runtime_error(
                    "Unique index violation: " +
                    definition.name
                );
            }
        }

        matchingIds.insert(order.id);
    }

    void erase(const Order& order) {
        string key = ExpressionEngine::evaluate(
            order,
            definition.expression
        );

        auto it = entries.find(key);

        if (it == entries.end()) {
            return;
        }

        it->second.erase(order.id);

        if (it->second.empty()) {
            entries.erase(it);
        }
    }

    void restore(
        const map<string, set<int>>& snapshot
    ) {
        entries = snapshot;
    }

    map<string, set<int>> snapshot() const {
        return entries;
    }
};

// ============================================================
// 6. DATABASE
// ============================================================

class OrderDatabase {
private:
    map<int, Order> rows;
    vector<DatabaseIndex> indexes;

public:
    void addIndex(IndexDefinition definition) {
        for (const auto& index : indexes) {
            if (index.name() == definition.name) {
                throw invalid_argument("Duplicate index name.");
            }
        }

        DatabaseIndex candidate(std::move(definition));

        for (const auto& [id, row] : rows) {
            candidate.insert(row);
        }

        indexes.push_back(std::move(candidate));
    }

    void insert(Order order) {
        validateOrder(order);

        if (rows.count(order.id)) {
            throw invalid_argument("Duplicate order ID.");
        }

        size_t completed = 0;

        try {
            for (auto& index : indexes) {
                index.insert(order);
                ++completed;
            }

            rows.emplace(order.id, std::move(order));

        } catch (...) {
            for (size_t i = 0; i < completed; ++i) {
                indexes[i].erase(order);
            }

            throw;
        }
    }

    void update(int id, Order replacement) {
        auto it = rows.find(id);

        if (it == rows.end()) {
            throw invalid_argument("Order not found.");
        }

        if (replacement.id != id) {
            throw invalid_argument("Order ID cannot change.");
        }

        validateOrder(replacement);

        vector<map<string, set<int>>> snapshots;

        for (const auto& index : indexes) {
            snapshots.push_back(index.snapshot());
        }

        try {
            for (auto& index : indexes) {
                index.erase(it->second);
                index.insert(replacement);
            }

            it->second = std::move(replacement);

        } catch (...) {
            for (size_t i = 0; i < indexes.size(); ++i) {
                indexes[i].restore(snapshots[i]);
            }

            throw;
        }
    }

    const vector<DatabaseIndex>& getIndexes() const {
        return indexes;
    }

    const map<int, Order>& getRows() const {
        return rows;
    }

    const DatabaseIndex* findIndex(
        const string& name
    ) const {
        for (const auto& index : indexes) {
            if (index.name() == name) {
                return &index;
            }
        }

        return nullptr;
    }
};

// ============================================================
// 7. QUERY MODEL
// ============================================================

struct Query {
    string expression;
    string key;
    optional<Predicate> predicate;
};

struct PlanCandidate {
    string indexName;
    double estimatedCost;
    size_t indexedKeys;
};

// ============================================================
// 8. PREDICATE IMPLICATION
// ============================================================

class PredicateLogic {
public:
    static bool implies(
        const Predicate& query,
        const Predicate& index
    ) {
        if (
            index.status &&
            (!query.status || *query.status != *index.status)
        ) {
            return false;
        }

        if (index.minimumAmount) {
            if (!query.minimumAmount) {
                return false;
            }

            double q = *query.minimumAmount;
            double i = *index.minimumAmount;

            if (index.strictMinimum) {
                if (query.strictMinimum ? q < i : q <= i) {
                    return false;
                }
            } else {
                if (query.strictMinimum ? q < i : q < i) {
                    return false;
                }
            }
        }

        return true;
    }
};

// ============================================================
// 9. QUERY PLANNER
// ============================================================

class QueryPlanner {
private:
    const OrderDatabase& database;

public:
    explicit QueryPlanner(const OrderDatabase& database)
        : database(database) {}

    vector<PlanCandidate> candidates(
        const Query& query
    ) const {
        vector<PlanCandidate> result;

        for (const auto& index : database.getIndexes()) {
            if (index.expression() != query.expression) {
                continue;
            }

            if (index.predicate()) {
                if (!query.predicate) {
                    continue;
                }

                if (!PredicateLogic::implies(
                    *query.predicate,
                    *index.predicate()
                )) {
                    continue;
                }
            }

            // Illustrative ranking only. A real DBMS considers
            // cardinality, selectivity, I/O, cache, statistics,
            // table size, and competing access paths.
            double cost = 1.0 +
                static_cast<double>(index.entryCount()) * 0.1;

            result.push_back({
                index.name(),
                cost,
                index.entryCount()
            });
        }

        sort(
            result.begin(),
            result.end(),
            [](const PlanCandidate& a,
               const PlanCandidate& b) {
                return a.estimatedCost < b.estimatedCost;
            }
        );

        return result;
    }
};

// ============================================================
// 10. QUERY EXECUTION
// ============================================================

vector<Order> executeQuery(
    const OrderDatabase& database,
    const Query& query
) {
    vector<Order> result;

    for (const auto& [id, order] : database.getRows()) {
        if (
            query.predicate &&
            !query.predicate->matches(order)
        ) {
            continue;
        }

        string key = ExpressionEngine::evaluate(
            order,
            query.expression
        );

        if (key == query.key) {
            result.push_back(order);
        }
    }

    return result;
}

// ============================================================
// 11. REPORTING
// ============================================================

void printPlan(
    const QueryPlanner& planner,
    const Query& query
) {
    cout << "\nQUERY: " << query.expression
         << " = " << query.key << '\n';

    if (query.predicate) {
        cout << "PREDICATE: "
             << query.predicate->describe() << '\n';
    }

    auto candidates = planner.candidates(query);

    if (candidates.empty()) {
        cout << "No eligible index. Alternative scan required.\n";
        return;
    }

    cout << "Eligible indexes:\n";

    for (const auto& candidate : candidates) {
        cout << "  " << candidate.indexName
             << " | estimated cost: "
             << fixed << setprecision(2)
             << candidate.estimatedCost
             << " | distinct keys: "
             << candidate.indexedKeys << '\n';
    }
}

// ============================================================
// 12. SAMPLE EXECUTION
// ============================================================

int main() {
    try {
        OrderDatabase database;

        database.insert({
            1, "alice@example.com",
            Status::OPEN, 450, "NORTH"
        });

        database.insert({
            2, "bob@example.com",
            Status::PAID, 900, "SOUTH"
        });

        database.insert({
            3, "carol@example.com",
            Status::OPEN, 250, "NORTH"
        });

        database.insert({
            4, "david@example.com",
            Status::CANCELLED, 120, "WEST"
        });

        database.insert({
            5, "eve@example.com",
            Status::ARCHIVED, 300, "EAST"
        });

        database.insert({
            6, "frank@example.com",
            Status::OPEN, 780, "SOUTH"
        });

        // Partial index.
        Predicate openOnly;
        openOnly.status = Status::OPEN;

        database.addIndex({
            "idx_open_orders",
            IndexKind::PARTIAL,
            "id",
            openOnly,
            false
        });

        // Expression index.
        database.addIndex({
            "idx_lower_email",
            IndexKind::EXPRESSION,
            "lower(email)",
            nullopt,
            false
        });

        // Partial expression index.
        Predicate highValueOpen;
        highValueOpen.status = Status::OPEN;
        highValueOpen.minimumAmount = 300;
        highValueOpen.strictMinimum = true;

        database.addIndex({
            "idx_open_high_value",
            IndexKind::PARTIAL_EXPRESSION,
            "amount",
            highValueOpen,
            false
        });

        // Function-based region index.
        database.addIndex({
            "idx_upper_region",
            IndexKind::EXPRESSION,
            "upper(region)",
            nullopt,
            false
        });

        QueryPlanner planner(database);

        Query emailQuery{
            "lower(email)",
            "alice@example.com",
            nullopt
        };

        printPlan(planner, emailQuery);

        auto emailRows = executeQuery(
            database,
            emailQuery
        );

        cout << "Matched email rows: "
             << emailRows.size() << '\n';

        Query openQuery{
            "id",
            "1",
            openOnly
        };

        printPlan(planner, openQuery);

        Query incompatibleQuery{
            "id",
            "1",
            Predicate{
                Status::PAID,
                nullopt,
                true
            }
        };

        printPlan(planner, incompatibleQuery);

        Query highValueQuery{
            "amount",
            "780.000000",
            highValueOpen
        };

        printPlan(planner, highValueQuery);

        cout << "\nINDEX MEMBERSHIP BEFORE UPDATE\n";

        const auto* openIndex =
            database.findIndex("idx_open_orders");

        if (openIndex) {
            cout << "Distinct indexed keys: "
                 << openIndex->entryCount() << '\n';
        }

        // Changing status removes an entry from the partial index.
        database.update(1, {
            1,
            "alice@example.com",
            Status::PAID,
            450,
            "NORTH"
        });

        cout << "\nINDEX MEMBERSHIP AFTER UPDATE\n";

        openIndex = database.findIndex("idx_open_orders");

        if (openIndex) {
            cout << "Distinct indexed keys: "
                 << openIndex->entryCount() << '\n';
        }

        // Validate that invalid data is rejected.
        try {
            database.insert({
                7,
                "invalid",
                Status::OPEN,
                100,
                "NORTH"
            });

            throw runtime_error("Validation failed.");

        } catch (const invalid_argument& error) {
            cout << "\nInvalid order rejected: "
                 << error.what() << '\n';
        }

        // Check expected result.
        if (emailRows.size() != 1) {
            throw runtime_error("Email assertion failed.");
        }

        cout << "\nExecution completed successfully.\n";

    } catch (const exception& error) {
        cerr << "Execution error: "
             << error.what() << '\n';

        return 1;
    }

    return 0;
}
