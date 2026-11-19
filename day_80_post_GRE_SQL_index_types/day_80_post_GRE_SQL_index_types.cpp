#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

/*
 * PostgreSQL Index Selection Engine.
 *
 * Standard: C++17
 *
 * Evaluates B-tree, Hash, GiST, SP-GiST, GIN and BRIN
 * against repository-independent database workloads.
 *
 * Scores are educational heuristics, not PostgreSQL cost estimates.
 */

enum class IndexType {
    BTree,
    Hash,
    GiST,
    SPGiST,
    GIN,
    BRIN
};

enum class QueryPattern {
    Equality,
    Range,
    Ordering,
    ArrayMembership,
    Contains,
    Spatial,
    Prefix,
    FullText,
    LargeTableRange
};

std::string toString(IndexType type) {
    switch (type) {
        case IndexType::BTree: return "B-tree";
        case IndexType::Hash: return "Hash";
        case IndexType::GiST: return "GiST";
        case IndexType::SPGiST: return "SP-GiST";
        case IndexType::GIN: return "GIN";
        case IndexType::BRIN: return "BRIN";
    }

    throw std::invalid_argument("Unknown index type");
}

std::string toString(QueryPattern pattern) {
    switch (pattern) {
        case QueryPattern::Equality: return "Equality";
        case QueryPattern::Range: return "Range";
        case QueryPattern::Ordering: return "Ordering";
        case QueryPattern::ArrayMembership: return "Array membership";
        case QueryPattern::Contains: return "Containment";
        case QueryPattern::Spatial: return "Spatial";
        case QueryPattern::Prefix: return "Prefix";
        case QueryPattern::FullText: return "Full-text";
        case QueryPattern::LargeTableRange: return "Large table range";
    }

    throw std::invalid_argument("Unknown query pattern");
}

struct Workload {
    std::string name;
    QueryPattern pattern;
    long long rows;
    double selectivity;
    double updateRate;
    double correlation;
    bool orderedOutput;

    void validate() const {
        if (name.empty()) {
            throw std::invalid_argument("Workload name is required");
        }

        if (rows <= 0) {
            throw std::invalid_argument("Row count must be positive");
        }

        auto validRatio = [](double value) {
            return std::isfinite(value) && value >= 0.0 && value <= 1.0;
        };

        if (!validRatio(selectivity) ||
            !validRatio(updateRate) ||
            !validRatio(correlation)) {
            throw std::invalid_argument("Invalid workload ratio");
        }
    }
};

struct IndexCapability {
    IndexType type;
    std::set<QueryPattern> patterns;
    std::string description;
    double maintenanceCost;
};

class IndexCatalog {
private:
    std::vector<IndexCapability> capabilities;

public:
    IndexCatalog() {
        capabilities = {
            {
                IndexType::BTree,
                {
                    QueryPattern::Equality,
                    QueryPattern::Range,
                    QueryPattern::Ordering,
                    QueryPattern::Prefix
                },
                "Ordered balanced search tree",
                0.10
            },
            {
                IndexType::Hash,
                {QueryPattern::Equality},
                "Hash-based equality index",
                0.08
            },
            {
                IndexType::GiST,
                {
                    QueryPattern::Range,
                    QueryPattern::Spatial,
                    QueryPattern::Contains
                },
                "Generalized Search Tree",
                0.16
            },
            {
                IndexType::SPGiST,
                {
                    QueryPattern::Spatial,
                    QueryPattern::Prefix,
                    QueryPattern::Equality
                },
                "Space-partitioned search tree",
                0.12
            },
            {
                IndexType::GIN,
                {
                    QueryPattern::ArrayMembership,
                    QueryPattern::Contains,
                    QueryPattern::FullText
                },
                "Inverted component-value index",
                0.30
            },
            {
                IndexType::BRIN,
                {
                    QueryPattern::Range,
                    QueryPattern::LargeTableRange
                },
                "Block Range Index",
                0.02
            }
        };
    }

    const std::vector<IndexCapability>& all() const {
        return capabilities;
    }
};

struct Recommendation {
    IndexType type;
    double score;
    bool applicable;
    std::vector<std::string> reasons;
};

class IndexAdvisor {
private:
    const IndexCatalog& catalog;

    static double clamp(double value) {
        return std::max(0.0, std::min(100.0, value));
    }

public:
    explicit IndexAdvisor(const IndexCatalog& catalog)
        : catalog(catalog) {}

    std::vector<Recommendation> evaluate(
        const Workload& workload
    ) const {
        workload.validate();

        std::vector<Recommendation> results;

        for (const auto& capability : catalog.all()) {
            Recommendation result{
                capability.type,
                0.0,
                false,
                {}
            };

            if (capability.patterns.count(workload.pattern) == 0) {
                result.reasons.push_back(
                    "Unsupported access pattern"
                );

                results.push_back(result);
                continue;
            }

            result.applicable = true;
            result.score = 50.0;

            result.reasons.push_back(
                "Access pattern supported by index capability"
            );

            switch (capability.type) {
                case IndexType::BTree:
                    result.score += 15.0;

                    if (workload.orderedOutput) {
                        result.score += 20.0;
                        result.reasons.push_back(
                            "Supports ordered retrieval"
                        );
                    }

                    if (workload.selectivity < 0.05) {
                        result.score += 10.0;
                    }
                    break;

                case IndexType::Hash:
                    result.score += 12.0;
                    result.reasons.push_back(
                        "Optimized for equality comparisons"
                    );
                    break;

                case IndexType::GiST:
                    result.score += 20.0;
                    result.reasons.push_back(
                        "Supports specialized operator classes"
                    );
                    break;

                case IndexType::SPGiST:
                    result.score += 20.0;
                    result.reasons.push_back(
                        "Supports partitioned search spaces"
                    );
                    break;

                case IndexType::GIN:
                    result.score += 25.0;
                    result.reasons.push_back(
                        "Supports inverted component lookup"
                    );

                    if (workload.updateRate > 0.5) {
                        result.score -= 20.0;
                        result.reasons.push_back(
                            "Frequent updates increase maintenance cost"
                        );
                    }
                    break;

                case IndexType::BRIN:
                    result.score += 15.0;
                    result.score += workload.correlation * 30.0;

                    if (workload.rows >= 1'000'000) {
                        result.score += 15.0;
                        result.reasons.push_back(
                            "Large table benefits from compact summaries"
                        );
                    }

                    if (workload.correlation < 0.4) {
                        result.score -= 30.0;
                        result.reasons.push_back(
                            "Low physical correlation weakens BRIN"
                        );
                    }
                    break;
            }

            result.score -= workload.updateRate * 15.0;
            result.score = clamp(result.score);

            results.push_back(std::move(result));
        }

        std::stable_sort(
            results.begin(),
            results.end(),
            [](const Recommendation& a, const Recommendation& b) {
                return a.score > b.score;
            }
        );

        return results;
    }
};

struct IndexDefinition {
    std::string name;
    std::string table;
    std::string column;
    IndexType type;
    bool unique = false;
};

class IndexRegistry {
private:
    std::map<std::string, IndexDefinition> indexes;

    static bool validIdentifier(const std::string& value) {
        if (value.empty()) {
            return false;
        }

        auto validFirst = [](char c) {
            return (c >= 'a' && c <= 'z') ||
                   (c >= 'A' && c <= 'Z') ||
                   c == '_';
        };

        auto validRest = [&](char c) {
            return validFirst(c) || (c >= '0' && c <= '9');
        };

        if (!validFirst(value.front())) {
            return false;
        }

        return std::all_of(
            value.begin() + 1,
            value.end(),
            validRest
        );
    }

public:
    void add(const IndexDefinition& definition) {
        if (!validIdentifier(definition.name) ||
            !validIdentifier(definition.table) ||
            !validIdentifier(definition.column)) {
            throw std::invalid_argument("Invalid SQL identifier");
        }

        if (definition.unique && definition.type != IndexType::BTree) {
            throw std::invalid_argument(
                "Unique indexes require B-tree in this model"
            );
        }

        if (indexes.count(definition.name)) {
            throw std::invalid_argument("Duplicate index name");
        }

        indexes.emplace(definition.name, definition);
    }

    void print() const {
        for (const auto& entry : indexes) {
            const auto& index = entry.second;

            std::cout
                << "CREATE "
                << (index.unique ? "UNIQUE " : "")
                << "INDEX " << index.name
                << " ON " << index.table
                << " USING " << toString(index.type)
                << " (" << index.column << ");\n";
        }
    }

    std::size_t size() const {
        return indexes.size();
    }
};

void printRecommendations(
    const Workload& workload,
    const std::vector<Recommendation>& results
) {
    std::cout << "\nWorkload: " << workload.name << "\n";

    int displayed = 0;

    for (const auto& result : results) {
        if (!result.applicable || displayed == 3) {
            continue;
        }

        std::cout
            << "  " << std::left
            << std::setw(9) << toString(result.type)
            << " Score: " << std::fixed
            << std::setprecision(2)
            << result.score << "\n";

        for (const auto& reason : result.reasons) {
            std::cout << "      - " << reason << "\n";
        }

        ++displayed;
    }
}

void runTests(const IndexAdvisor& advisor) {
    Workload equality{
        "Customer lookup",
        QueryPattern::Equality,
        500'000,
        0.001,
        0.05,
        0.0,
        false
    };

    auto equalityResults = advisor.evaluate(equality);

    if (equalityResults.front().type != IndexType::BTree) {
        throw std::runtime_error("B-tree ranking test failed");
    }

    Workload fullText{
        "Document search",
        QueryPattern::FullText,
        2'000'000,
        0.005,
        0.10,
        0.0,
        false
    };

    auto fullTextResults = advisor.evaluate(fullText);

    if (fullTextResults.front().type != IndexType::GIN) {
        throw std::runtime_error("GIN ranking test failed");
    }

    Workload historical{
        "Historical events",
        QueryPattern::LargeTableRange,
        10'000'000,
        0.05,
        0.02,
        0.99,
        false
    };

    auto brinResults = advisor.evaluate(historical);

    if (brinResults.front().type != IndexType::BRIN) {
        throw std::runtime_error("BRIN ranking test failed");
    }

    bool rejected = false;

    try {
        Workload invalid{
            "Invalid workload",
            QueryPattern::Equality,
            -1,
            0.5,
            0.1,
            0.1,
            false
        };

        advisor.evaluate(invalid);
    } catch (const std::invalid_argument&) {
        rejected = true;
    }

    if (!rejected) {
        throw std::runtime_error("Validation test failed");
    }

    std::cout << "\nAll C++ tests passed.\n";
}

int main() {
    try {
        std::cout
            << "POSTGRESQL INDEX SELECTION ENGINE\n"
            << std::string(65, '=') << "\n";

        IndexCatalog catalog;
        IndexAdvisor advisor(catalog);

        std::vector<Workload> workloads = {
            {
                "Customer equality lookup",
                QueryPattern::Equality,
                500'000,
                0.001,
                0.05,
                0.0,
                false
            },
            {
                "Order date range",
                QueryPattern::Range,
                5'000'000,
                0.02,
                0.10,
                0.95,
                false
            },
            {
                "JSONB containment",
                QueryPattern::Contains,
                1'000'000,
                0.01,
                0.60,
                0.0,
                false
            },
            {
                "Array membership",
                QueryPattern::ArrayMembership,
                800'000,
                0.05,
                0.20,
                0.0,
                false
            },
            {
                "Spatial lookup",
                QueryPattern::Spatial,
                300'000,
                0.01,
                0.05,
                0.0,
                false
            },
            {
                "Full-text search",
                QueryPattern::FullText,
                2'000'000,
                0.005,
                0.10,
                0.0,
                false
            },
            {
                "Historical range",
                QueryPattern::LargeTableRange,
                10'000'000,
                0.05,
                0.02,
                0.99,
                false
            }
        };

        auto start = std::chrono::steady_clock::now();

        for (const auto& workload : workloads) {
            printRecommendations(
                workload,
                advisor.evaluate(workload)
            );
        }

        auto finish = std::chrono::steady_clock::now();

        auto elapsed =
            std::chrono::duration<double, std::milli>(
                finish - start
            ).count();

        std::cout << "\nINDEX REGISTRY\n";

        IndexRegistry registry;

        registry.add({
            "idx_customer_email",
            "customers",
            "email",
            IndexType::BTree,
            true
        });

        registry.add({
            "idx_event_payload",
            "events",
            "payload",
            IndexType::GIN,
            false
        });

        registry.add({
            "idx_order_created",
            "orders",
            "created_at",
            IndexType::BRIN,
            false
        });

        registry.add({
            "idx_network_ip",
            "network_logs",
            "client_ip",
            IndexType::SPGiST,
            false
        });

        registry.print();

        std::cout
            << "\nRegistered indexes: " << registry.size()
            << "\nAnalysis time: " << std::fixed
            << std::setprecision(4) << elapsed << " ms\n";

        runTests(advisor);

        std::cout << "\nExecution completed successfully.\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << "\n";
        return 1;
    }
}
