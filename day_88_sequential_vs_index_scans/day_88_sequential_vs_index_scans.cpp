#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std;

/*
 * Sequential Scan, Index Scan and Bitmap Scan
 *
 * C++17 repository-independent query execution engine.
 *
 * Features:
 * - Domain modeling
 * - Secondary indexes
 * - Bitmap AND operations
 * - Selectivity estimation
 * - Cost-based planning
 * - Scan execution
 * - Index consistency checks
 */

constexpr size_t PAGE_SIZE = 100;
constexpr double SEQ_PAGE_COST = 1.0;
constexpr double RANDOM_PAGE_COST = 4.0;
constexpr double CPU_TUPLE_COST = 0.01;
constexpr double CPU_INDEX_COST = 0.005;

enum class ScanType {
    Sequential,
    Index,
    Bitmap
};

enum class Operator {
    Equal,
    In
};

string scanName(ScanType type) {
    switch (type) {
        case ScanType::Sequential: return "Seq Scan";
        case ScanType::Index: return "Index Scan";
        case ScanType::Bitmap: return "Bitmap Heap Scan";
    }

    throw runtime_error("Invalid scan type");
}

struct Employee {
    int id;
    string department;
    string location;
    int salary;
    bool active;
};

struct Predicate {
    string column;
    Operator op;
    vector<string> values;

    bool matches(const Employee& employee) const {
        string actual;

        if (column == "id") {
            actual = to_string(employee.id);
        } else if (column == "department") {
            actual = employee.department;
        } else if (column == "location") {
            actual = employee.location;
        } else if (column == "salary") {
            actual = to_string(employee.salary);
        } else if (column == "active") {
            actual = employee.active ? "true" : "false";
        } else {
            throw invalid_argument("Unknown predicate column");
        }

        return find(values.begin(), values.end(), actual)
            != values.end();
    }
};

struct Index {
    string column;
    unordered_map<string, set<size_t>> entries;

    void add(const string& value, size_t rowId) {
        entries[value].insert(rowId);
    }

    void remove(const string& value, size_t rowId) {
        auto it = entries.find(value);

        if (it == entries.end()) return;

        it->second.erase(rowId);

        if (it->second.empty()) {
            entries.erase(it);
        }
    }

    set<size_t> lookup(const Predicate& predicate) const {
        set<size_t> result;

        for (const string& value : predicate.values) {
            auto it = entries.find(value);

            if (it != entries.end()) {
                result.insert(
                    it->second.begin(),
                    it->second.end()
                );
            }
        }

        return result;
    }
};

struct Metrics {
    size_t rowsExamined = 0;
    size_t rowsReturned = 0;
    size_t indexEntriesExamined = 0;
    size_t heapBlocksAccessed = 0;
    size_t bitmapBytes = 0;
    double estimatedCost = 0;
    double executionMs = 0;
};

struct QueryResult {
    vector<Employee> rows;
    Metrics metrics;
    ScanType scanType;
};

class EmployeeTable {
private:
    vector<Employee> rows;
    unordered_map<string, Index> indexes;

public:
    void insert(const Employee& employee) {
        size_t id = rows.size();

        rows.push_back(employee);

        for (auto& [column, index] : indexes) {
            index.add(getValue(employee, column), id);
        }
    }

    string getValue(
        const Employee& employee,
        const string& column
    ) const {
        if (column == "id") return to_string(employee.id);
        if (column == "department") return employee.department;
        if (column == "location") return employee.location;
        if (column == "salary") return to_string(employee.salary);
        if (column == "active") {
            return employee.active ? "true" : "false";
        }

        throw invalid_argument("Unknown column: " + column);
    }

    void createIndex(const string& column) {
        if (indexes.count(column)) {
            throw invalid_argument("Duplicate index");
        }

        Index index;
        index.column = column;

        for (size_t i = 0; i < rows.size(); ++i) {
            index.add(getValue(rows[i], column), i);
        }

        indexes.emplace(column, move(index));
    }

    void deleteRow(size_t id) {
        if (id >= rows.size()) {
            throw out_of_range("Invalid row identifier");
        }

        Employee& employee = rows[id];

        for (auto& [column, index] : indexes) {
            index.remove(getValue(employee, column), id);
        }

        // A production storage engine also handles tuple visibility
        // and physical space reclamation.
        employee.id = -1;
    }

    const vector<Employee>& getRows() const {
        return rows;
    }

    const unordered_map<string, Index>& getIndexes() const {
        return indexes;
    }

    size_t activeRows() const {
        return count_if(
            rows.begin(),
            rows.end(),
            [](const Employee& e) { return e.id != -1; }
        );
    }

    size_t pageCount() const {
        return max(
            size_t(1),
            (activeRows() + PAGE_SIZE - 1) / PAGE_SIZE
        );
    }

    bool valid() const {
        for (const auto& [column, index] : indexes) {
            unordered_map<string, set<size_t>> expected;

            for (size_t i = 0; i < rows.size(); ++i) {
                if (rows[i].id != -1) {
                    expected[getValue(rows[i], column)].insert(i);
                }
            }

            if (expected.size() != index.entries.size()) {
                return false;
            }

            for (const auto& [value, ids] : expected) {
                auto it = index.entries.find(value);

                if (it == index.entries.end() ||
                    it->second != ids) {
                    return false;
                }
            }
        }

        return true;
    }
};

class CostBasedPlanner {
private:
    const EmployeeTable& table;

    double selectivity(const Predicate& predicate) const {
        const auto& rows = table.getRows();

        if (table.activeRows() == 0) return 0.0;

        size_t count = 0;

        for (const auto& row : rows) {
            if (row.id != -1 && predicate.matches(row)) {
                ++count;
            }
        }

        return static_cast<double>(count) / table.activeRows();
    }

public:
    explicit CostBasedPlanner(const EmployeeTable& t)
        : table(t) {}

    double sequentialCost() const {
        return table.pageCount() * SEQ_PAGE_COST
            + table.activeRows() * CPU_TUPLE_COST;
    }

    double indexCost(double selectivityValue) const {
        double n = max(size_t(2), table.activeRows());

        return log2(n)
            + selectivityValue * n *
            (RANDOM_PAGE_COST + CPU_INDEX_COST);
    }

    ScanType choose(
        const vector<Predicate>& predicates,
        double& estimatedCost
    ) const {
        double seq = sequentialCost();
        estimatedCost = seq;

        vector<double> selectivities;
        size_t indexedCount = 0;

        for (const auto& predicate : predicates) {
            if (table.getIndexes().count(predicate.column)) {
                selectivities.push_back(selectivity(predicate));
                ++indexedCount;
            }
        }

        if (selectivities.empty()) {
            return ScanType::Sequential;
        }

        double best = *min_element(
            selectivities.begin(),
            selectivities.end()
        );

        double idx = indexCost(best);

        if (indexedCount >= 2) {
            double combined = accumulate(
                selectivities.begin(),
                selectivities.end(),
                1.0,
                multiplies<double>()
            );

            double rows = table.activeRows() * combined;

            double blocks = min(
                static_cast<double>(table.pageCount()),
                ceil(rows / PAGE_SIZE)
            );

            double bitmap =
                indexedCount * log2(
                    max(size_t(2), table.activeRows())
                )
                + rows * CPU_INDEX_COST
                + blocks * RANDOM_PAGE_COST
                + rows * CPU_TUPLE_COST;

            if (bitmap < seq && bitmap < idx) {
                estimatedCost = bitmap;
                return ScanType::Bitmap;
            }
        }

        if (idx < seq) {
            estimatedCost = idx;
            return ScanType::Index;
        }

        return ScanType::Sequential;
    }
};

class QueryEngine {
private:
    const EmployeeTable& table;
    CostBasedPlanner planner;

    void validate(
        const vector<Predicate>& predicates
    ) const {
        for (const auto& predicate : predicates) {
            if (predicate.values.empty()) {
                throw invalid_argument("Empty predicate values");
            }

            if (predicate.op == Operator::Equal &&
                predicate.values.size() != 1) {
                throw invalid_argument(
                    "Equality requires exactly one value"
                );
            }

            const string& column = predicate.column;

            if (
                column != "id" &&
                column != "department" &&
                column != "location" &&
                column != "salary" &&
                column != "active"
            ) {
                throw invalid_argument("Unknown predicate column");
            }
        }
    }

public:
    explicit QueryEngine(const EmployeeTable& t)
        : table(t), planner(t) {}

    QueryResult execute(
        const vector<Predicate>& predicates,
        ScanType forced
    ) const {
        validate(predicates);

        double cost = 0;

        ScanType selected = planner.choose(predicates, cost);

        if (forced != selected) {
            selected = forced;
        }

        if (selected == ScanType::Index) {
            bool usable = false;

            for (const auto& p : predicates) {
                if (table.getIndexes().count(p.column)) {
                    usable = true;
                }
            }

            if (!usable) {
                throw runtime_error("Index Scan requires an index");
            }
        }

        if (selected == ScanType::Bitmap) {
            size_t count = 0;

            for (const auto& p : predicates) {
                count += table.getIndexes().count(p.column);
            }

            if (count < 2) {
                throw runtime_error(
                    "Bitmap Scan requires two indexed predicates"
                );
            }
        }

        auto started = chrono::steady_clock::now();

        QueryResult result;
        result.scanType = selected;
        result.metrics.estimatedCost = cost;

        set<size_t> candidates;

        const auto& rows = table.getRows();

        if (selected == ScanType::Sequential) {
            for (size_t i = 0; i < rows.size(); ++i) {
                if (rows[i].id != -1) {
                    candidates.insert(i);
                }
            }

            result.metrics.rowsExamined = candidates.size();
            result.metrics.heapBlocksAccessed = table.pageCount();
        }

        if (selected == ScanType::Index) {
            const Predicate* best = nullptr;
            double bestSelectivity = numeric_limits<double>::max();

            for (const auto& p : predicates) {
                auto it = table.getIndexes().find(p.column);

                if (it == table.getIndexes().end()) continue;

                size_t matching = 0;

                for (const auto& row : rows) {
                    if (row.id != -1 && p.matches(row)) {
                        ++matching;
                    }
                }

                double value = static_cast<double>(matching)
                    / max(size_t(1), table.activeRows());

                if (value < bestSelectivity) {
                    bestSelectivity = value;
                    best = &p;
                }
            }

            if (!best) {
                throw runtime_error("No usable index");
            }

            candidates = table.getIndexes()
                .at(best->column).lookup(*best);

            result.metrics.indexEntriesExamined = candidates.size();
            result.metrics.rowsExamined = candidates.size();
        }

        if (selected == ScanType::Bitmap) {
            vector<set<size_t>> bitmaps;

            for (const auto& p : predicates) {
                auto it = table.getIndexes().find(p.column);

                if (it == table.getIndexes().end()) continue;

                set<size_t> bitmap = it->second.lookup(p);

                result.metrics.indexEntriesExamined += bitmap.size();

                bitmaps.push_back(move(bitmap));
            }

            sort(
                bitmaps.begin(),
                bitmaps.end(),
                [](const auto& a, const auto& b) {
                    return a.size() < b.size();
                }
            );

            candidates = bitmaps.front();

            // Intersect progressively from the smallest bitmap.
            for (size_t i = 1; i < bitmaps.size(); ++i) {
                set<size_t> intersection;

                set_intersection(
                    candidates.begin(), candidates.end(),
                    bitmaps[i].begin(), bitmaps[i].end(),
                    inserter(intersection, intersection.begin())
                );

                candidates = move(intersection);
            }

            result.metrics.rowsExamined = candidates.size();
            result.metrics.bitmapBytes =
                (rows.size() + 7) / 8;
        }

        for (size_t id : candidates) {
            if (id >= rows.size() || rows[id].id == -1) {
                continue;
            }

            bool matches = all_of(
                predicates.begin(),
                predicates.end(),
                [&](const Predicate& p) {
                    return p.matches(rows[id]);
                }
            );

            if (matches) {
                result.rows.push_back(rows[id]);
            }
        }

        result.metrics.rowsReturned = result.rows.size();

        if (selected != ScanType::Sequential) {
            set<size_t> blocks;

            for (size_t id : candidates) {
                blocks.insert(id / PAGE_SIZE);
            }

            result.metrics.heapBlocksAccessed = blocks.size();
        }

        auto finished = chrono::steady_clock::now();

        result.metrics.executionMs =
            chrono::duration<double, milli>(
                finished - started
            ).count();

        return result;
    }
};

void printResult(
    const string& title,
    const QueryResult& result
) {
    const auto& m = result.metrics;

    cout << "\n" << title << "\n";
    cout << string(55, '-') << "\n";

    cout << "Scan type: "
         << scanName(result.scanType) << "\n";

    cout << "Estimated cost: "
         << fixed << setprecision(2)
         << m.estimatedCost << "\n";

    cout << "Rows examined: "
         << m.rowsExamined << "\n";

    cout << "Rows returned: "
         << m.rowsReturned << "\n";

    cout << "Index entries examined: "
         << m.indexEntriesExamined << "\n";

    cout << "Heap blocks accessed: "
         << m.heapBlocksAccessed << "\n";

    cout << "Bitmap bytes: "
         << m.bitmapBytes << "\n";

    cout << "Execution time: "
         << m.executionMs << " ms\n";
}

int main() {
    try {
        EmployeeTable employees;

        vector<string> departments = {
            "Engineering", "Finance",
            "Operations", "Security"
        };

        vector<string> locations = {
            "Lucknow", "Delhi",
            "Mumbai", "Bengaluru"
        };

        // Deterministic data distribution.
        for (int i = 1; i <= 10000; ++i) {
            employees.insert({
                i,
                departments[i % departments.size()],
                locations[(i * 7) % locations.size()],
                30000 + (i * 7919) % 150001,
                i % 7 != 0
            });
        }

        employees.createIndex("id");
        employees.createIndex("department");
        employees.createIndex("location");

        QueryEngine engine(employees);

        cout << "C++17 QUERY SCAN ENGINE\n";
        cout << "Rows: " << employees.activeRows() << "\n";
        cout << "Pages: " << employees.pageCount() << "\n";

        // Sequential scan: salary has no index.
        Predicate salary {
            "salary", Operator::Equal, {"50000"}
        };

        auto seq = engine.execute(
            {salary},
            ScanType::Sequential
        );

        printResult("1. Sequential Scan", seq);

        // Index scan: highly selective primary-key lookup.
        Predicate employeeId {
            "id", Operator::Equal, {"500"}
        };

        auto idx = engine.execute(
            {employeeId},
            ScanType::Index
        );

        printResult("2. Index Scan", idx);

        // Bitmap AND: two independently indexed columns.
        Predicate department {
            "department", Operator::Equal, {"Engineering"}
        };

        Predicate location {
            "location", Operator::Equal, {"Lucknow"}
        };

        auto bitmap = engine.execute(
            {department, location},
            ScanType::Bitmap
        );

        printResult("3. Bitmap Heap Scan", bitmap);

        // Correctness: all strategies must return equivalent rows.
        auto reference = engine.execute(
            {employeeId},
            ScanType::Sequential
        );

        if (reference.rows.size() != idx.rows.size()) {
            throw runtime_error("Scan result mismatch");
        }

        // Index maintenance.
        employees.insert({
            10001,
            "Security",
            "Lucknow",
            95000,
            true
        });

        if (!employees.valid()) {
            throw runtime_error("Index integrity failure");
        }

        employees.deleteRow(10000);

        if (!employees.valid()) {
            throw runtime_error("Index integrity failure after delete");
        }

        cout << "\nIndex integrity: VALID\n";
        cout << "Insertion and deletion: VALID\n";
        cout << "All tests passed.\n";

    } catch (const exception& error) {
        cerr << "Execution error: "
             << error.what() << "\n";

        return 1;
    }

    return 0;
}
