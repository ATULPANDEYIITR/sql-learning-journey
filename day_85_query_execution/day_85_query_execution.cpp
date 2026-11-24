#include <algorithm>
#include <chrono>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <variant>
#include <vector>

using namespace std;

using Value = variant<monostate, int64_t, double, string, bool>;
using Row = unordered_map<string, Value>;

class QueryException : public runtime_error {
public:
    using runtime_error::runtime_error;
};

enum class Comparison {
    EQ, NE, GT, LT, GE, LE
};

enum class AccessPath {
    SEQUENTIAL_SCAN,
    INDEX_SCAN
};

string valueToString(const Value& value) {
    if (holds_alternative<monostate>(value)) return "NULL";
    if (holds_alternative<int64_t>(value))
        return to_string(get<int64_t>(value));
    if (holds_alternative<double>(value)) {
        return to_string(get<double>(value));
    }
    if (holds_alternative<string>(value))
        return get<string>(value);
    return get<bool>(value) ? "TRUE" : "FALSE";
}

bool isNull(const Value& value) {
    return holds_alternative<monostate>(value);
}

bool compareValues(
    const Value& left,
    const Value& right,
    Comparison operation
) {
    if (isNull(left) || isNull(right)) {
        return false;
    }

    if (left.index() != right.index()) {
        if (
            (holds_alternative<int64_t>(left) ||
             holds_alternative<double>(left)) &&
            (holds_alternative<int64_t>(right) ||
             holds_alternative<double>(right))
        ) {
            double a = holds_alternative<int64_t>(left)
                ? static_cast<double>(get<int64_t>(left))
                : get<double>(left);

            double b = holds_alternative<int64_t>(right)
                ? static_cast<double>(get<int64_t>(right))
                : get<double>(right);

            switch (operation) {
                case Comparison::EQ: return a == b;
                case Comparison::NE: return a != b;
                case Comparison::GT: return a > b;
                case Comparison::LT: return a < b;
                case Comparison::GE: return a >= b;
                case Comparison::LE: return a <= b;
            }
        }

        throw QueryException("Incompatible comparison types.");
    }

    if (holds_alternative<int64_t>(left)) {
        auto a = get<int64_t>(left);
        auto b = get<int64_t>(right);

        switch (operation) {
            case Comparison::EQ: return a == b;
            case Comparison::NE: return a != b;
            case Comparison::GT: return a > b;
            case Comparison::LT: return a < b;
            case Comparison::GE: return a >= b;
            case Comparison::LE: return a <= b;
        }
    }

    if (holds_alternative<double>(left)) {
        auto a = get<double>(left);
        auto b = get<double>(right);

        switch (operation) {
            case Comparison::EQ: return a == b;
            case Comparison::NE: return a != b;
            case Comparison::GT: return a > b;
            case Comparison::LT: return a < b;
            case Comparison::GE: return a >= b;
            case Comparison::LE: return a <= b;
        }
    }

    if (holds_alternative<string>(left)) {
        const auto& a = get<string>(left);
        const auto& b = get<string>(right);

        switch (operation) {
            case Comparison::EQ: return a == b;
            case Comparison::NE: return a != b;
            case Comparison::GT: return a > b;
            case Comparison::LT: return a < b;
            case Comparison::GE: return a >= b;
            case Comparison::LE: return a <= b;
        }
    }

    if (holds_alternative<bool>(left)) {
        bool a = get<bool>(left);
        bool b = get<bool>(right);

        switch (operation) {
            case Comparison::EQ: return a == b;
            case Comparison::NE: return a != b;
            default:
                throw QueryException(
                    "Ordering comparisons on BOOLEAN are unsupported."
                );
        }
    }

    return false;
}


struct Predicate {
    string column;
    Comparison operation;
    Value expected;

    bool evaluate(const Row& row) const {
        auto iterator = row.find(column);

        if (iterator == row.end()) {
            throw QueryException("Unknown column: " + column);
        }

        return compareValues(
            iterator->second,
            expected,
            operation
        );
    }
};


class Table {
private:
    string name;
    vector<string> columns;
    vector<Row> rows;

    unordered_map<
        string,
        map<string, vector<size_t>>
    > indexes;

public:
    Table(
        string tableName,
        vector<string> schema,
        vector<Row> records
    ) : name(move(tableName)),
        columns(move(schema)),
        rows(move(records)) {

        set<string> uniqueColumns(
            columns.begin(), columns.end()
        );

        if (uniqueColumns.size() != columns.size()) {
            throw QueryException("Duplicate column names.");
        }

        for (const auto& row : rows) {
            if (row.size() != columns.size()) {
                throw QueryException("Invalid row schema.");
            }

            for (const auto& column : columns) {
                if (!row.count(column)) {
                    throw QueryException(
                        "Missing field: " + column
                    );
                }
            }
        }
    }

    const string& getName() const {
        return name;
    }

    const vector<string>& getColumns() const {
        return columns;
    }

    const vector<Row>& getRows() const {
        return rows;
    }

    bool hasColumn(const string& column) const {
        return find(
            columns.begin(), columns.end(), column
        ) != columns.end();
    }

    void buildIndex(const string& column) {
        if (!hasColumn(column)) {
            throw QueryException("Unknown index column.");
        }

        auto& index = indexes[column];

        for (size_t i = 0; i < rows.size(); ++i) {
            index[valueToString(rows[i].at(column))].push_back(i);
        }
    }

    bool hasIndex(const string& column) const {
        return indexes.count(column) > 0;
    }

    vector<size_t> lookup(
        const string& column,
        const Value& value
    ) const {
        auto iterator = indexes.find(column);

        if (iterator == indexes.end()) {
            return {};
        }

        auto found = iterator->second.find(
            valueToString(value)
        );

        if (found == iterator->second.end()) {
            return {};
        }

        return found->second;
    }
};


struct Query {
    string table;
    vector<string> projection;
    optional<Predicate> predicate;
    string sortColumn;
    bool descending = false;
    optional<size_t> limit;
};


struct ExecutionStats {
    size_t rowsScanned = 0;
    size_t rowsMatched = 0;
    size_t rowsReturned = 0;
    double estimatedCost = 0;
    double executionMilliseconds = 0;
    AccessPath accessPath = AccessPath::SEQUENTIAL_SCAN;
};


struct ExecutionResult {
    vector<Row> rows;
    ExecutionStats statistics;
};


class QueryOptimizer {
public:
    AccessPath chooseAccessPath(
        const Table& table,
        const Query& query,
        double& estimatedCost
    ) const {
        const double scanCost =
            static_cast<double>(table.getRows().size());

        estimatedCost = scanCost;

        if (
            query.predicate &&
            query.predicate->operation == Comparison::EQ &&
            table.hasIndex(query.predicate->column)
        ) {
            auto positions = table.lookup(
                query.predicate->column,
                query.predicate->expected
            );

            const double indexCost =
                2.0 + positions.size() * 0.2;

            if (indexCost < scanCost) {
                estimatedCost = indexCost;
                return AccessPath::INDEX_SCAN;
            }
        }

        return AccessPath::SEQUENTIAL_SCAN;
    }
};


class QueryExecutor {
private:
    QueryOptimizer optimizer;

    static void validate(const Table& table, const Query& query) {
        if (query.projection.empty()) {
            throw QueryException("Projection cannot be empty.");
        }

        for (const auto& column : query.projection) {
            if (column != "*" && !table.hasColumn(column)) {
                throw QueryException(
                    "Unknown projected column: " + column
                );
            }
        }

        if (
            query.predicate &&
            !table.hasColumn(query.predicate->column)
        ) {
            throw QueryException(
                "Unknown predicate column."
            );
        }

        if (
            !query.sortColumn.empty() &&
            !table.hasColumn(query.sortColumn)
        ) {
            throw QueryException("Unknown sorting column.");
        }
    }

public:
    ExecutionResult execute(
        const Table& table,
        const Query& query
    ) const {
        validate(table, query);

        auto start = chrono::steady_clock::now();

        ExecutionResult result;

        double estimatedCost = 0;

        result.statistics.accessPath =
            optimizer.chooseAccessPath(
                table, query, estimatedCost
            );

        result.statistics.estimatedCost = estimatedCost;

        vector<size_t> candidates;

        if (
            result.statistics.accessPath ==
            AccessPath::INDEX_SCAN
        ) {
            candidates = table.lookup(
                query.predicate->column,
                query.predicate->expected
            );
        } else {
            candidates.resize(table.getRows().size());

            for (size_t i = 0; i < candidates.size(); ++i) {
                candidates[i] = i;
            }
        }

        result.statistics.rowsScanned = candidates.size();

        vector<Row> matched;

        for (size_t position : candidates) {
            const Row& row = table.getRows().at(position);

            if (
                !query.predicate ||
                query.predicate->evaluate(row)
            ) {
                matched.push_back(row);
            }
        }

        result.statistics.rowsMatched = matched.size();

        // Sort before projection because ORDER BY may require
        // a column not included in the SELECT list.
        if (!query.sortColumn.empty()) {
            const string key = query.sortColumn;

            sort(
                matched.begin(),
                matched.end(),
                [&](const Row& a, const Row& b) {
                    const Value& left = a.at(key);
                    const Value& right = b.at(key);

                    bool comparison = compareValues(
                        left,
                        right,
                        Comparison::LT
                    );

                    return query.descending
                        ? !comparison &&
                          !compareValues(
                              left, right, Comparison::EQ
                          )
                        : comparison;
                }
            );
        }

        if (query.limit) {
            matched.resize(
                min(*query.limit, matched.size())
            );
        }

        const bool selectAll =
            query.projection.size() == 1 &&
            query.projection.front() == "*";

        for (const Row& row : matched) {
            Row projected;

            if (selectAll) {
                projected = row;
            } else {
                for (const auto& column : query.projection) {
                    projected[column] = row.at(column);
                }
            }

            result.rows.push_back(move(projected));
        }

        result.statistics.rowsReturned =
            result.rows.size();

        auto end = chrono::steady_clock::now();

        result.statistics.executionMilliseconds =
            chrono::duration<double, milli>(
                end - start
            ).count();

        return result;
    }
};


void printResult(const ExecutionResult& result) {
    cout << "\nACCESS PATH: "
         << (
             result.statistics.accessPath ==
             AccessPath::INDEX_SCAN
             ? "INDEX SCAN"
             : "SEQUENTIAL SCAN"
         ) << '\n';

    cout << "ESTIMATED COST: "
         << result.statistics.estimatedCost << '\n';

    cout << "ROWS SCANNED: "
         << result.statistics.rowsScanned << '\n';

    cout << "ROWS MATCHED: "
         << result.statistics.rowsMatched << '\n';

    cout << "ROWS RETURNED: "
         << result.statistics.rowsReturned << '\n';

    cout << "EXECUTION TIME: "
         << fixed << setprecision(4)
         << result.statistics.executionMilliseconds
         << " ms\n";

    for (const auto& row : result.rows) {
        cout << "{ ";

        for (const auto& [column, value] : row) {
            cout << column << ": "
                 << valueToString(value) << " ";
        }

        cout << "}\n";
    }
}


int main() {
    try {
        vector<Row> employees = {
            {
                {"id", int64_t(1)},
                {"name", string("Asha")},
                {"department", string("Engineering")},
                {"salary", int64_t(95000)}
            },
            {
                {"id", int64_t(2)},
                {"name", string("Rahul")},
                {"department", string("Finance")},
                {"salary", int64_t(72000)}
            },
            {
                {"id", int64_t(3)},
                {"name", string("Neha")},
                {"department", string("Engineering")},
                {"salary", int64_t(110000)}
            },
            {
                {"id", int64_t(4)},
                {"name", string("Arjun")},
                {"department", string("Operations")},
                {"salary", int64_t(68000)}
            },
            {
                {"id", int64_t(5)},
                {"name", string("Meera")},
                {"department", string("Engineering")},
                {"salary", int64_t(88000)}
            }
        };

        Table table(
            "employees",
            {"id", "name", "department", "salary"},
            employees
        );

        table.buildIndex("department");
        table.buildIndex("id");

        QueryExecutor executor;

        Query query{
            "employees",
            {"name", "salary"},
            Predicate{
                "department",
                Comparison::EQ,
                string("Engineering")
            },
            "salary",
            true,
            2
        };

        auto result = executor.execute(table, query);

        cout << "QUERY EXECUTION ENGINE\n";
        printResult(result);

        // Test indexed lookup.
        if (
            result.statistics.accessPath !=
            AccessPath::INDEX_SCAN
        ) {
            throw QueryException(
                "Expected index scan for selective predicate."
            );
        }

        if (result.rows.size() != 2) {
            throw QueryException("Unexpected result count.");
        }

        // Test empty result.
        Query emptyQuery{
            "employees",
            {"id"},
            Predicate{
                "department",
                Comparison::EQ,
                string("Legal")
            },
            "",
            false,
            nullopt
        };

        auto emptyResult =
            executor.execute(table, emptyQuery);

        if (!emptyResult.rows.empty()) {
            throw QueryException("Empty-result test failed.");
        }

        // Test zero LIMIT.
        Query zeroLimit{
            "employees",
            {"id"},
            nullopt,
            "",
            false,
            0
        };

        if (
            !executor.execute(table, zeroLimit).rows.empty()
        ) {
            throw QueryException("LIMIT 0 test failed.");
        }

        // Test validation.
        try {
            Query invalid{
                "employees",
                {"unknown_column"},
                nullopt,
                "",
                false,
                nullopt
            };

            executor.execute(table, invalid);

            throw QueryException(
                "Invalid-column test failed."
            );
        } catch (const QueryException& error) {
            if (
                string(error.what()) ==
                "Invalid-column test failed."
            ) {
                throw;
            }
        }

        cout << "\nAll governance and execution tests passed.\n";

    } catch (const exception& error) {
        cerr << "Execution error: "
             << error.what() << '\n';

        return 1;
    }

    return 0;
}
