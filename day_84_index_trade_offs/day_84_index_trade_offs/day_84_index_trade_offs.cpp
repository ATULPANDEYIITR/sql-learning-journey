#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

using namespace std;

/*
 * Index Trade-offs: Write Overhead, Storage, Maintenance
 * and Over-Indexing.
 *
 * C++17 repository-independent index governance simulator.
 *
 * Models:
 * - Database tables and indexes
 * - Query access patterns
 * - Read benefit and write amplification
 * - Index storage
 * - Composite index matching
 * - Index maintenance
 * - Merge-like workload consolidation through index selection
 * - Index retention and removal recommendations
 */

enum class IndexType {
    BTREE,
    HASH,
    COMPOSITE,
    COVERING
};

enum class IndexState {
    ACTIVE,
    DISABLED,
    NEEDS_REBUILD
};

enum class WriteOperation {
    INSERT,
    UPDATE,
    DELETE
};

string toString(IndexType type) {
    switch (type) {
        case IndexType::BTREE: return "BTREE";
        case IndexType::HASH: return "HASH";
        case IndexType::COMPOSITE: return "COMPOSITE";
        case IndexType::COVERING: return "COVERING";
    }

    throw logic_error("Invalid index type");
}

struct IndexMetrics {
    long long reads = 0;
    long long inserts = 0;
    long long updates = 0;
    long long deletes = 0;
    long long maintenanceRuns = 0;
    long long storageBytes = 0;
    double fragmentation = 0.0;

    long long writes() const {
        return inserts + updates + deletes;
    }
};

class IndexDefinition {
public:
    string name;
    vector<string> columns;
    vector<string> includedColumns;
    IndexType type;
    IndexState state = IndexState::ACTIVE;
    bool unique = false;
    IndexMetrics metrics;

    IndexDefinition(
        string indexName,
        vector<string> keys,
        IndexType indexType = IndexType::BTREE,
        vector<string> included = {},
        bool isUnique = false
    ) :
        name(move(indexName)),
        columns(move(keys)),
        includedColumns(move(included)),
        type(indexType),
        unique(isUnique) {

        if (name.empty() || columns.empty()) {
            throw invalid_argument(
                "Index name and key columns are required"
            );
        }

        set<string> uniqueKeys(
            columns.begin(), columns.end()
        );

        if (uniqueKeys.size() != columns.size()) {
            throw invalid_argument(
                "Duplicate index key columns"
            );
        }

        for (const auto& column : includedColumns) {
            if (uniqueKeys.count(column)) {
                throw invalid_argument(
                    "Included column duplicates a key column"
                );
            }
        }

        if (
            type == IndexType::COMPOSITE &&
            columns.size() < 2
        ) {
            throw invalid_argument(
                "Composite index requires multiple columns"
            );
        }

        if (
            type == IndexType::HASH &&
            columns.size() != 1
        ) {
            throw invalid_argument(
                "Hash index requires one column"
            );
        }
    }

    bool supports(
        const vector<string>& queryColumns
    ) const {
        if (
            state != IndexState::ACTIVE ||
            queryColumns.empty() ||
            queryColumns.size() > columns.size()
        ) {
            return false;
        }

        if (type == IndexType::HASH) {
            return queryColumns == columns;
        }

        return equal(
            queryColumns.begin(),
            queryColumns.end(),
            columns.begin()
        );
    }

    long long estimateStorage(long long rows) {
        if (rows < 0) {
            throw invalid_argument("Negative row count");
        }

        const long long entryBytes =
            static_cast<long long>(
                columns.size() * 24 +
                includedColumns.size() * 16 + 8
            );

        metrics.storageBytes = static_cast<long long>(
            ceil(rows * entryBytes / 0.85)
        );

        return metrics.storageBytes;
    }

    void recordWrite(WriteOperation operation) {
        if (state != IndexState::ACTIVE) {
            return;
        }

        switch (operation) {
            case WriteOperation::INSERT:
                ++metrics.inserts;
                break;

            case WriteOperation::UPDATE:
                ++metrics.updates;
                break;

            case WriteOperation::DELETE:
                ++metrics.deletes;
                break;
        }

        metrics.fragmentation = min(
            100.0,
            metrics.fragmentation + 0.015
        );
    }
};

struct QueryPattern {
    string name;
    vector<string> columns;
    long long frequency;
    long long estimatedRows;
};

struct Workload {
    long long reads;
    long long inserts;
    long long updates;
    long long deletes;

    void validate() const {
        if (
            reads < 0 || inserts < 0 ||
            updates < 0 || deletes < 0
        ) {
            throw invalid_argument(
                "Workload values cannot be negative"
            );
        }
    }

    long long totalWrites() const {
        return inserts + updates + deletes;
    }
};

struct QueryResult {
    string queryName;
    string accessMethod;
    string indexName;
    long long estimatedCost;
};

class DatabaseTable {
private:
    string name;
    set<string> columns;
    long long rowCount;
    long long rowSizeBytes;
    map<string, IndexDefinition> indexes;
    vector<QueryPattern> queries;

public:
    DatabaseTable(
        string tableName,
        set<string> tableColumns,
        long long rows,
        long long rowSize = 320
    ) :
        name(move(tableName)),
        columns(move(tableColumns)),
        rowCount(rows),
        rowSizeBytes(rowSize) {

        if (
            name.empty() ||
            columns.empty() ||
            rows < 0 ||
            rowSize <= 0
        ) {
            throw invalid_argument(
                "Invalid table configuration"
            );
        }
    }

    void addIndex(IndexDefinition index) {
        if (indexes.count(index.name)) {
            throw invalid_argument(
                "Duplicate index name"
            );
        }

        for (const auto& column : index.columns) {
            if (!columns.count(column)) {
                throw invalid_argument(
                    "Unknown index column: " + column
                );
            }
        }

        for (const auto& column : index.includedColumns) {
            if (!columns.count(column)) {
                throw invalid_argument(
                    "Unknown included column: " + column
                );
            }
        }

        for (const auto& item : indexes) {
            const auto& existing = item.second;

            if (
                existing.columns == index.columns &&
                existing.includedColumns ==
                    index.includedColumns &&
                existing.type == index.type &&
                existing.state != IndexState::DISABLED
            ) {
                throw invalid_argument(
                    "Equivalent index already exists"
                );
            }
        }

        index.estimateStorage(rowCount);
        indexes.emplace(index.name, move(index));
    }

    void addQuery(QueryPattern query) {
        if (
            query.frequency < 0 ||
            query.estimatedRows < 0 ||
            query.columns.empty()
        ) {
            throw invalid_argument("Invalid query pattern");
        }

        for (const auto& column : query.columns) {
            if (!columns.count(column)) {
                throw invalid_argument(
                    "Unknown query column: " + column
                );
            }
        }

        queries.push_back(move(query));
    }

    void insert(long long count) {
        if (count <= 0) {
            throw invalid_argument(
                "Insert count must be positive"
            );
        }

        rowCount += count;

        for (auto& item : indexes) {
            auto& index = item.second;

            for (long long i = 0; i < count; ++i) {
                index.recordWrite(WriteOperation::INSERT);
            }

            index.estimateStorage(rowCount);
        }
    }

    void update(
        long long count,
        const set<string>& modifiedColumns
    ) {
        if (count <= 0 || count > rowCount) {
            throw invalid_argument("Invalid update count");
        }

        for (const auto& column : modifiedColumns) {
            if (!columns.count(column)) {
                throw invalid_argument(
                    "Unknown updated column"
                );
            }
        }

        for (auto& item : indexes) {
            auto& index = item.second;

            vector<string> indexedColumns =
                index.columns;

            indexedColumns.insert(
                indexedColumns.end(),
                index.includedColumns.begin(),
                index.includedColumns.end()
            );

            bool affected = any_of(
                indexedColumns.begin(),
                indexedColumns.end(),
                [&](const string& column) {
                    return modifiedColumns.count(column) > 0;
                }
            );

            if (affected) {
                for (long long i = 0; i < count; ++i) {
                    index.recordWrite(WriteOperation::UPDATE);
                }
            }
        }
    }

    void remove(long long count) {
        if (count <= 0 || count > rowCount) {
            throw invalid_argument("Invalid delete count");
        }

        rowCount -= count;

        for (auto& item : indexes) {
            auto& index = item.second;

            for (long long i = 0; i < count; ++i) {
                index.recordWrite(WriteOperation::DELETE);
            }

            index.estimateStorage(rowCount);
        }
    }

    IndexDefinition* selectIndex(
        const vector<string>& queryColumns
    ) {
        IndexDefinition* best = nullptr;

        for (auto& item : indexes) {
            auto& candidate = item.second;

            if (!candidate.supports(queryColumns)) {
                continue;
            }

            if (
                best == nullptr ||
                candidate.columns.size() <
                    best->columns.size() ||
                (
                    candidate.columns.size() ==
                        best->columns.size() &&
                    candidate.metrics.storageBytes <
                        best->metrics.storageBytes
                )
            ) {
                best = &candidate;
            }
        }

        return best;
    }

    vector<QueryResult> executeReads() {
        vector<QueryResult> results;

        for (const auto& query : queries) {
            IndexDefinition* index =
                selectIndex(query.columns);

            long long cost;

            if (index) {
                index->metrics.reads += query.frequency;

                cost = static_cast<long long>(
                    ceil(log2(max(2LL, rowCount)))
                ) + query.estimatedRows + 2;
            } else {
                cost = max(1LL, rowCount);
            }

            results.push_back({
                query.name,
                index ? "INDEX_SCAN" : "TABLE_SCAN",
                index ? index->name : "NONE",
                cost
            });
        }

        return results;
    }

    void rebuild(const string& name) {
        auto it = indexes.find(name);

        if (it == indexes.end()) {
            throw invalid_argument("Index not found");
        }

        auto& index = it->second;

        if (index.state == IndexState::DISABLED) {
            throw invalid_argument(
                "Cannot rebuild disabled index"
            );
        }

        index.metrics.fragmentation = 0;
        ++index.metrics.maintenanceRuns;
        index.state = IndexState::ACTIVE;
        index.estimateStorage(rowCount);
    }

    long long totalIndexStorage() const {
        long long total = 0;

        for (const auto& item : indexes) {
            if (item.second.state != IndexState::DISABLED) {
                total += item.second.metrics.storageBytes;
            }
        }

        return total;
    }

    const map<string, IndexDefinition>&
    getIndexes() const {
        return indexes;
    }

    long long getRowCount() const {
        return rowCount;
    }

    long long getTableStorage() const {
        return rowCount * rowSizeBytes;
    }

    void printReport() const {
        cout << "\nTABLE: " << name << '\n';
        cout << "Rows: " << rowCount << '\n';
        cout << "Table storage: "
             << getTableStorage() << " bytes\n";
        cout << "Index storage: "
             << totalIndexStorage() << " bytes\n";

        cout << "\nINDEX METRICS\n";

        for (const auto& item : indexes) {
            const auto& index = item.second;
            const auto& metrics = index.metrics;

            cout << "\n" << index.name << '\n';
            cout << "Type: " << toString(index.type) << '\n';
            cout << "Storage: " << metrics.storageBytes << '\n';
            cout << "Reads: " << metrics.reads << '\n';
            cout << "Writes: " << metrics.writes() << '\n';
            cout << "Fragmentation: "
                 << fixed << setprecision(2)
                 << metrics.fragmentation << "%\n";
        }
    }
};

struct IndexDecision {
    string indexName;
    double writeReadRatio;
    string recommendation;
    vector<string> reasons;
};

class GovernanceEngine {
private:
    double maximumWriteReadRatio;
    long long minimumWriteSample;

public:
    GovernanceEngine(
        double ratio = 10.0,
        long long sample = 100
    ) :
        maximumWriteReadRatio(ratio),
        minimumWriteSample(sample) {

        if (
            ratio < 0 ||
            !isfinite(ratio) ||
            sample < 0
        ) {
            throw invalid_argument(
                "Invalid governance thresholds"
            );
        }
    }

    vector<IndexDecision> evaluate(
        const DatabaseTable& table
    ) const {
        vector<IndexDecision> decisions;

        for (const auto& item : table.getIndexes()) {
            const auto& index = item.second;
            const auto& metrics = index.metrics;

            double ratio =
                static_cast<double>(metrics.writes()) /
                max(1LL, metrics.reads);

            vector<string> reasons;

            if (
                metrics.writes() >= minimumWriteSample &&
                metrics.reads == 0
            ) {
                reasons.push_back("UNUSED_INDEX");
            }

            if (
                metrics.writes() >= minimumWriteSample &&
                ratio > maximumWriteReadRatio
            ) {
                reasons.push_back(
                    "HIGH_WRITE_TO_READ_RATIO"
                );
            }

            if (metrics.fragmentation > 30.0) {
                reasons.push_back("HIGH_FRAGMENTATION");
            }

            if (metrics.storageBytes >
                table.getTableStorage()) {
                reasons.push_back(
                    "INDEX_STORAGE_EXCEEDS_TABLE_STORAGE"
                );
            }

            decisions.push_back({
                index.name,
                ratio,
                reasons.empty() ? "RETAIN" : "REVIEW",
                reasons
            });
        }

        return decisions;
    }

    static vector<pair<string, string>>
    findPrefixOverlaps(const DatabaseTable& table) {
        vector<pair<string, string>> overlaps;

        const auto& indexes = table.getIndexes();

        for (
            auto first = indexes.begin();
            first != indexes.end();
            ++first
        ) {
            auto second = first;
            ++second;

            for (; second != indexes.end(); ++second) {
                const auto& a = first->second;
                const auto& b = second->second;

                if (
                    a.state == IndexState::ACTIVE &&
                    b.state == IndexState::ACTIVE &&
                    a.columns.size() < b.columns.size() &&
                    equal(
                        a.columns.begin(),
                        a.columns.end(),
                        b.columns.begin()
                    )
                ) {
                    overlaps.push_back({
                        a.name,
                        b.name
                    });
                }
            }
        }

        return overlaps;
    }
};

int main() {
    try {
        DatabaseTable table(
            "orders",
            {
                "order_id",
                "customer_id",
                "status",
                "created_at",
                "region",
                "amount",
                "description"
            },
            100000,
            320
        );

        table.addIndex(
            IndexDefinition(
                "idx_customer",
                {"customer_id"}
            )
        );

        table.addIndex(
            IndexDefinition(
                "idx_status_date",
                {"status", "created_at"},
                IndexType::COMPOSITE
            )
        );

        table.addIndex(
            IndexDefinition(
                "idx_region_covering",
                {"region"},
                IndexType::COVERING,
                {"amount"}
            )
        );

        table.addQuery({
            "customer_history",
            {"customer_id"},
            25000,
            15
        });

        table.addQuery({
            "pending_orders",
            {"status", "created_at"},
            12000,
            50
        });

        table.addQuery({
            "regional_orders",
            {"region"},
            8000,
            100
        });

        table.addQuery({
            "description_search",
            {"description"},
            2000,
            500
        });

        cout << "INDEX ACCESS RESULTS\n";

        for (const auto& result : table.executeReads()) {
            cout << result.queryName
                 << " | " << result.accessMethod
                 << " | " << result.indexName
                 << " | Cost: " << result.estimatedCost
                 << '\n';
        }

        cout << "\nWRITE WORKLOAD\n";

        table.insert(500);

        table.update(
            100,
            {"status", "amount"}
        );

        table.remove(50);

        table.printReport();

        cout << "\nGOVERNANCE DECISIONS\n";

        GovernanceEngine engine(10.0, 100);

        for (const auto& decision : engine.evaluate(table)) {
            cout << decision.indexName
                 << " | " << decision.recommendation
                 << " | Write/read ratio: "
                 << fixed << setprecision(2)
                 << decision.writeReadRatio
                 << '\n';

            for (const auto& reason : decision.reasons) {
                cout << "  - " << reason << '\n';
            }
        }

        cout << "\nPREFIX OVERLAP ANALYSIS\n";

        for (
            const auto& overlap :
            GovernanceEngine::findPrefixOverlaps(table)
        ) {
            cout << overlap.first
                 << " overlaps with "
                 << overlap.second << '\n';
        }

        cout << "\nINDEX MAINTENANCE\n";

        table.rebuild("idx_customer");

        cout << "Customer index rebuilt successfully.\n";

        cout << "\nEDGE CASE VALIDATION\n";

        try {
            table.insert(-5);
        } catch (const invalid_argument& error) {
            cout << "Expected error: "
                 << error.what() << '\n';
        }

        if (table.getRowCount() != 100450) {
            throw logic_error("Incorrect final row count");
        }

        if (table.totalIndexStorage() <= 0) {
            throw logic_error("Invalid index storage");
        }

        cout << "\nAll validation checks passed.\n";

    } catch (const exception& error) {
        cerr << "Execution error: "
             << error.what() << '\n';

        return 1;
    }

    return 0;
}
