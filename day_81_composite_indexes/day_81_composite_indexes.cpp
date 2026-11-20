#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std;

/*
 * Composite Index Governance and Query Optimization Model.
 *
 * C++17 implementation covering:
 * - Multi-column B-tree indexes.
 * - Leftmost-prefix matching.
 * - Equality and range predicates.
 * - Column selectivity.
 * - Ordering compatibility.
 * - Workload-based recommendations.
 * - Index redundancy.
 * - Cost estimation.
 */

enum class PredicateType {
    Equality,
    Range,
    Ordering
};

struct ColumnStats {
    string name;
    long long distinctValues;
    long long rowCount;

    double equalitySelectivity() const {
        if (distinctValues <= 0 || rowCount <= 0) {
            throw invalid_argument("Invalid column statistics.");
        }

        return 1.0 / static_cast<double>(distinctValues);
    }
};

struct Predicate {
    string column;
    PredicateType type;
    double estimatedFraction = 0.25;
};

struct Query {
    string name;
    vector<Predicate> predicates;
    vector<string> ordering;
    vector<string> projection;
    int frequency = 1;
};

struct Index {
    string name;
    vector<string> columns;
    bool active = true;
    bool unique = false;
};

struct Evaluation {
    string indexName;
    int matchedPrefix = 0;
    double selectivity = 1.0;
    bool orderingCovered = false;
    bool coveringCandidate = false;
    double estimatedCost = 0.0;
};

class IndexAdvisor {
private:
    unordered_map<string, ColumnStats> statistics;
    long long totalRows;

    void validateColumn(const string& name) const {
        if (statistics.find(name) == statistics.end()) {
            throw invalid_argument("Unknown column: " + name);
        }
    }

public:
    explicit IndexAdvisor(vector<ColumnStats> columns)
        : totalRows(0) {

        if (columns.empty()) {
            throw invalid_argument("Column statistics are required.");
        }

        for (const auto& column : columns) {
            if (column.distinctValues <= 0 ||
                column.rowCount < column.distinctValues) {
                throw invalid_argument("Invalid column statistics.");
            }

            if (!statistics.emplace(column.name, column).second) {
                throw invalid_argument("Duplicate column statistics.");
            }

            totalRows = max(totalRows, column.rowCount);
        }
    }

    double estimateSelectivity(const Query& query) const {
        double selectivity = 1.0;

        for (const auto& predicate : query.predicates) {
            validateColumn(predicate.column);

            const auto& stats = statistics.at(predicate.column);

            if (predicate.type == PredicateType::Equality) {
                selectivity *= stats.equalitySelectivity();
            } else if (predicate.type == PredicateType::Range) {
                if (predicate.estimatedFraction <= 0 ||
                    predicate.estimatedFraction > 1) {
                    throw invalid_argument("Invalid range fraction.");
                }

                selectivity *= predicate.estimatedFraction;
            }
        }

        return max(selectivity, 1.0 / totalRows);
    }

    int leftmostPrefix(
        const Index& index,
        const Query& query
    ) const {
        set<string> equality;
        set<string> range;

        for (const auto& predicate : query.predicates) {
            if (predicate.type == PredicateType::Equality) {
                equality.insert(predicate.column);
            } else if (predicate.type == PredicateType::Range) {
                range.insert(predicate.column);
            }
        }

        int matched = 0;
        bool encounteredRange = false;

        for (const auto& column : index.columns) {
            if (equality.count(column) && !encounteredRange) {
                matched++;
            } else if (range.count(column) && !encounteredRange) {
                matched++;
                encounteredRange = true;
                break;
            } else {
                break;
            }
        }

        return matched;
    }

    bool orderingCovered(
        const Index& index,
        const Query& query
    ) const {
        if (query.ordering.empty()) return false;

        if (query.ordering.size() > index.columns.size()) {
            return false;
        }

        /*
         * A complete database optimizer also considers equality-fixed
         * leading columns, sort direction and NULL ordering.
         * This model uses direct prefix compatibility.
         */
        return equal(
            query.ordering.begin(),
            query.ordering.end(),
            index.columns.begin()
        );
    }

    bool coveringCandidate(
        const Index& index,
        const Query& query
    ) const {
        set<string> required;

        for (const auto& predicate : query.predicates) {
            required.insert(predicate.column);
        }

        required.insert(
            query.projection.begin(),
            query.projection.end()
        );

        required.insert(
            query.ordering.begin(),
            query.ordering.end()
        );

        set<string> available(
            index.columns.begin(),
            index.columns.end()
        );

        for (const auto& column : required) {
            if (!available.count(column)) return false;
        }

        return true;
    }

    Evaluation evaluate(
        const Index& index,
        const Query& query
    ) const {
        for (const auto& column : index.columns) {
            validateColumn(column);
        }

        Evaluation result;

        result.indexName = index.name;
        result.matchedPrefix = leftmostPrefix(index, query);
        result.selectivity = estimateSelectivity(query);
        result.orderingCovered = orderingCovered(index, query);
        result.coveringCandidate = coveringCandidate(index, query);

        const double tableCost =
            static_cast<double>(totalRows) * 0.8;

        const double indexCost =
            log2(static_cast<double>(totalRows) + 1) +
            result.selectivity * totalRows * 0.12;

        if (result.matchedPrefix == 0) {
            result.estimatedCost = tableCost;
        } else {
            result.estimatedCost = indexCost;

            if (result.orderingCovered) {
                result.estimatedCost *= 0.85;
            }

            if (result.coveringCandidate) {
                result.estimatedCost *= 0.75;
            }
        }

        return result;
    }

    vector<Evaluation> recommend(
        const Query& query,
        const vector<Index>& indexes
    ) const {
        vector<Evaluation> results;

        for (const auto& index : indexes) {
            if (!index.active) continue;

            results.push_back(evaluate(index, query));
        }

        sort(
            results.begin(),
            results.end(),
            [](const Evaluation& a, const Evaluation& b) {
                return a.estimatedCost < b.estimatedCost;
            }
        );

        return results;
    }

    vector<string> suggestColumnOrder(
        const Query& query
    ) const {
        vector<string> equality;
        vector<string> ranges;
        vector<string> ordering;

        for (const auto& predicate : query.predicates) {
            validateColumn(predicate.column);

            if (predicate.type == PredicateType::Equality) {
                equality.push_back(predicate.column);
            } else if (predicate.type == PredicateType::Range) {
                ranges.push_back(predicate.column);
            }
        }

        sort(
            equality.begin(),
            equality.end(),
            [&](const string& a, const string& b) {
                return statistics.at(a).distinctValues >
                       statistics.at(b).distinctValues;
            }
        );

        vector<string> result;

        auto appendUnique = [&](const string& column) {
            if (find(result.begin(), result.end(), column)
                == result.end()) {
                result.push_back(column);
            }
        };

        for (const auto& column : equality) {
            appendUnique(column);
        }

        for (const auto& column : ranges) {
            appendUnique(column);
        }

        for (const auto& column : query.ordering) {
            validateColumn(column);
            appendUnique(column);
        }

        return result;
    }

    vector<pair<string, string>> findRedundant(
        const vector<Index>& indexes
    ) const {
        vector<pair<string, string>> redundant;

        for (const auto& candidate : indexes) {
            for (const auto& existing : indexes) {
                if (candidate.name == existing.name ||
                    !existing.active ||
                    existing.columns.size() < candidate.columns.size()) {
                    continue;
                }

                bool prefix = equal(
                    candidate.columns.begin(),
                    candidate.columns.end(),
                    existing.columns.begin()
                );

                if (prefix) {
                    redundant.emplace_back(
                        candidate.name,
                        existing.name
                    );

                    break;
                }
            }
        }

        return redundant;
    }
};

class RepositoryWorkload {
private:
    vector<Index> indexes;

public:
    void addIndex(const Index& index) {
        if (index.name.empty() || index.columns.empty()) {
            throw invalid_argument("Invalid index definition.");
        }

        set<string> uniqueColumns(
            index.columns.begin(),
            index.columns.end()
        );

        if (uniqueColumns.size() != index.columns.size()) {
            throw invalid_argument("Duplicate index columns.");
        }

        for (const auto& existing : indexes) {
            if (existing.name == index.name) {
                throw invalid_argument("Duplicate index name.");
            }
        }

        indexes.push_back(index);
    }

    const vector<Index>& getIndexes() const {
        return indexes;
    }
};

void printEvaluation(
    const Evaluation& result
) {
    cout << left
         << setw(35) << result.indexName
         << " Prefix: " << result.matchedPrefix
         << " Selectivity: "
         << fixed << setprecision(6)
         << result.selectivity
         << " Ordering: "
         << (result.orderingCovered ? "Yes" : "No")
         << " Covering: "
         << (result.coveringCandidate ? "Yes" : "No")
         << " Cost: "
         << result.estimatedCost
         << '\n';
}

int main() {
    try {
        IndexAdvisor advisor({
            {"customer_id", 10000, 1000000},
            {"status", 5, 1000000},
            {"region", 4, 1000000},
            {"created_at", 900000, 1000000},
            {"total_amount", 500000, 1000000},
            {"payment_method", 6, 1000000}
        });

        RepositoryWorkload workload;

        workload.addIndex({
            "idx_customer_status_date",
            {"customer_id", "status", "created_at"}
        });

        workload.addIndex({
            "idx_status_customer_date",
            {"status", "customer_id", "created_at"}
        });

        workload.addIndex({
            "idx_status_date",
            {"status", "created_at"}
        });

        workload.addIndex({
            "idx_region_amount",
            {"region", "total_amount"}
        });

        vector<Query> queries = {
            {
                "Customer order history",
                {
                    {"customer_id", PredicateType::Equality},
                    {"status", PredicateType::Equality},
                    {"created_at", PredicateType::Range, 0.20}
                },
                {"created_at"},
                {"total_amount"},
                150
            },
            {
                "Recent paid orders",
                {
                    {"status", PredicateType::Equality},
                    {"created_at", PredicateType::Range, 0.10}
                },
                {"created_at"},
                {"customer_id"},
                300
            },
            {
                "Regional sales",
                {
                    {"region", PredicateType::Equality},
                    {"total_amount", PredicateType::Range, 0.15}
                },
                {},
                {"total_amount"},
                40
            },
            {
                "Payment method analysis",
                {
                    {"payment_method", PredicateType::Equality}
                },
                {},
                {},
                10
            }
        };

        cout << "\nCOMPOSITE INDEX ANALYSIS\n";
        cout << string(100, '=') << '\n';

        for (const auto& query : queries) {
            cout << "\nQuery: " << query.name << '\n';
            cout << "Frequency: " << query.frequency << '\n';

            auto results = advisor.recommend(
                query,
                workload.getIndexes()
            );

            for (const auto& result : results) {
                printEvaluation(result);
            }
        }

        cout << "\nSUGGESTED COLUMN ORDER\n";

        auto suggested = advisor.suggestColumnOrder(queries[0]);

        for (const auto& column : suggested) {
            cout << column << ' ';
        }

        cout << "\n\nREDUNDANCY ANALYSIS\n";

        for (const auto& item :
             advisor.findRedundant(workload.getIndexes())) {
            cout << item.first
                 << " may be covered by "
                 << item.second << '\n';
        }

        cout << "\nEDGE CASE: NON-LEFTMOST COLUMN\n";

        Query nonLeftmost {
            "Date-only lookup",
            {
                {"created_at", PredicateType::Range, 0.10}
            },
            {},
            {},
            5
        };

        for (const auto& result :
             advisor.recommend(
                 nonLeftmost,
                 workload.getIndexes()
             )) {
            printEvaluation(result);
        }

        cout << "\nANALYSIS COMPLETED\n";

    } catch (const exception& error) {
        cerr << "Execution error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
