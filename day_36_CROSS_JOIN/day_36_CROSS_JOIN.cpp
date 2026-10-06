#include <algorithm>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

/*
 * CROSS JOIN GOVERNANCE CASE STUDY
 *
 * Scenario:
 * A platform team needs to evaluate combinations of repositories, deployment
 * environments, test suites, and release policies.
 *
 * A CROSS JOIN-like operation creates every candidate combination. The engine
 * then applies domain rules and protects itself against accidental Cartesian
 * explosions.
 *
 * C++17 compatible.
 */

struct PullRequestCandidate {
    string repository;
    string environment;
    string testSuite;
    string releasePolicy;
};

struct EvaluationResult {
    size_t candidates = 0;
    size_t accepted = 0;
    size_t rejected = 0;
};

size_t checkedMultiply(size_t left, size_t right, size_t limit) {
    if (left == 0 || right == 0) {
        return 0;
    }

    if (left > limit / right) {
        throw overflow_error("Cartesian product exceeds configured limit");
    }

    return left * right;
}

size_t cartesianSize(
    const vector<size_t>& dimensions,
    size_t limit
) {
    size_t result = 1;

    for (size_t dimension : dimensions) {
        if (dimension == 0) {
            return 0;
        }

        result = checkedMultiply(result, dimension, limit);
    }

    return result;
}

template <typename Left, typename Right, typename Callback>
void crossJoin(
    const vector<Left>& left,
    const vector<Right>& right,
    Callback callback
) {
    /*
     * This function does not store the complete Cartesian product.
     * Each pair is delivered directly to the callback.
     */
    for (const auto& leftValue : left) {
        for (const auto& rightValue : right) {
            callback(leftValue, rightValue);
        }
    }
}

class RepositoryGovernanceEngine {
private:
    vector<string> repositories{
        "payments-api",
        "customer-web",
        "analytics-worker"
    };

    vector<string> environments{
        "staging",
        "production"
    };

    vector<string> testSuites{
        "unit",
        "integration",
        "security"
    };

    vector<string> policies{
        "standard",
        "regulated-release"
    };

    size_t maximumCandidates;

    bool isValid(const PullRequestCandidate& candidate) const {
        /*
         * Production combinations must use the regulated release policy when
         * security testing is part of the candidate's test suite.
         */
        if (
            candidate.environment == "production" &&
            candidate.testSuite == "security" &&
            candidate.releasePolicy != "regulated-release"
        ) {
            return false;
        }

        /*
         * The regulated policy is intentionally reserved for production.
         * This prevents meaningless policy/environment combinations.
         */
        if (
            candidate.releasePolicy == "regulated-release" &&
            candidate.environment != "production"
        ) {
            return false;
        }

        return true;
    }

public:
    explicit RepositoryGovernanceEngine(size_t limit)
        : maximumCandidates(limit) {}

    EvaluationResult evaluate() const {
        const size_t candidateCount = cartesianSize(
            {
                repositories.size(),
                environments.size(),
                testSuites.size(),
                policies.size()
            },
            maximumCandidates
        );

        EvaluationResult result;
        result.candidates = candidateCount;

        /*
         * The candidate count is checked before enumeration. This protects the
         * process from an unexpectedly large Cartesian product.
         */
        for (const auto& repository : repositories) {
            for (const auto& environment : environments) {
                for (const auto& testSuite : testSuites) {
                    for (const auto& policy : policies) {
                        PullRequestCandidate candidate{
                            repository,
                            environment,
                            testSuite,
                            policy
                        };

                        if (isValid(candidate)) {
                            ++result.accepted;
                        } else {
                            ++result.rejected;
                        }
                    }
                }
            }
        }

        return result;
    }

    vector<PullRequestCandidate> generateAccepted(size_t outputLimit) const {
        vector<PullRequestCandidate> accepted;

        if (outputLimit == 0) {
            return accepted;
        }

        const size_t candidateCount = cartesianSize(
            {
                repositories.size(),
                environments.size(),
                testSuites.size(),
                policies.size()
            },
            maximumCandidates
        );

        if (candidateCount == 0) {
            return accepted;
        }

        accepted.reserve(min(candidateCount, outputLimit));

        for (const auto& repository : repositories) {
            for (const auto& environment : environments) {
                for (const auto& testSuite : testSuites) {
                    for (const auto& policy : policies) {
                        if (accepted.size() >= outputLimit) {
                            return accepted;
                        }

                        PullRequestCandidate candidate{
                            repository,
                            environment,
                            testSuite,
                            policy
                        };

                        if (isValid(candidate)) {
                            accepted.push_back(candidate);
                        }
                    }
                }
            }
        }

        return accepted;
    }
};

void demonstrateTwoDimensionCrossJoin() {
    cout << "\n" << string(78, '=') << "\n";
    cout << "TWO-DIMENSION CROSS JOIN\n";
    cout << string(78, '=') << "\n";

    vector<string> roles{"developer", "reviewer", "release-manager"};
    vector<string> environments{"staging", "production"};

    size_t count = 0;

    crossJoin(
        roles,
        environments,
        [&](const string& role, const string& environment) {
            ++count;
            cout << setw(3) << count
                 << "  " << setw(18) << left << role
                 << "  " << environment << "\n";
        }
    );

    cout << "Expected rows: " << roles.size() * environments.size() << "\n";
}

void demonstrateEmptyDimension() {
    cout << "\n" << string(78, '=') << "\n";
    cout << "EMPTY DIMENSION\n";
    cout << string(78, '=') << "\n";

    vector<string> repositories{"api", "web"};
    vector<string> environments;

    size_t count = 0;

    crossJoin(
        repositories,
        environments,
        [&](const string&, const string&) {
            ++count;
        }
    );

    cout << "Rows generated: " << count << "\n";
    cout << "An empty input produces no Cartesian combinations.\n";
}

void demonstrateRiskDetection() {
    cout << "\n" << string(78, '=') << "\n";
    cout << "CARTESIAN RISK DETECTION\n";
    cout << string(78, '=') << "\n";

    try {
        size_t safe = cartesianSize(
            {10, 20, 5},
            5000
        );

        cout << "Safe product: " << safe << "\n";
    } catch (const exception& error) {
        cout << "Rejected: " << error.what() << "\n";
    }

    try {
        size_t dangerous = cartesianSize(
            {1000, 1000, 100},
            5'000'000
        );

        cout << "Product: " << dangerous << "\n";
    } catch (const exception& error) {
        cout << "Large product rejected: " << error.what() << "\n";
    }
}

void demonstrateDuplicates() {
    cout << "\n" << string(78, '=') << "\n";
    cout << "DUPLICATE INPUT ROWS\n";
    cout << string(78, '=') << "\n";

    vector<string> teams{"platform", "platform", "security"};
    vector<string> repositories{"api", "web"};

    vector<string> rawPairs;

    crossJoin(
        teams,
        repositories,
        [&](const string& team, const string& repository) {
            rawPairs.push_back(team + ":" + repository);
        }
    );

    cout << "Raw Cartesian rows: " << rawPairs.size() << "\n";

    /*
     * A CROSS JOIN does not imply DISTINCT. Deduplication is a separate
     * operation and can change the meaning of the result.
     */
    unordered_set<string> uniquePairs(
        rawPairs.begin(),
        rawPairs.end()
    );

    cout << "Unique value pairs after explicit deduplication: "
         << uniquePairs.size() << "\n";
}

void demonstrateGovernanceEngine() {
    cout << "\n" << string(78, '=') << "\n";
    cout << "REPOSITORY GOVERNANCE CASE STUDY\n";
    cout << string(78, '=') << "\n";

    RepositoryGovernanceEngine engine(10'000);

    EvaluationResult result = engine.evaluate();

    cout << "Candidate combinations: " << result.candidates << "\n";
    cout << "Accepted combinations:  " << result.accepted << "\n";
    cout << "Rejected combinations:  " << result.rejected << "\n";

    auto accepted = engine.generateAccepted(10);

    cout << "\nFirst accepted combinations:\n";

    for (const auto& candidate : accepted) {
        cout << "Repository=" << candidate.repository
             << ", Environment=" << candidate.environment
             << ", TestSuite=" << candidate.testSuite
             << ", Policy=" << candidate.releasePolicy
             << "\n";
    }
}

void demonstrateComplexity() {
    cout << "\n" << string(78, '=') << "\n";
    cout << "COMPLEXITY CHARACTERISTICS\n";
    cout << string(78, '=') << "\n";

    cout << "For dimensions n1, n2, ..., nk, the Cartesian cardinality is:\n";
    cout << "n1 * n2 * ... * nk\n";
    cout << "\n";

    cout << "Generating every row requires time proportional to the output size.\n";
    cout << "Storing every generated row requires memory proportional to the output size.\n";
    cout << "Streaming can reduce result-storage memory but cannot reduce the number\n";
    cout << "of combinations that must actually be processed.\n";
}

int main() {
    try {
        cout << "CROSS JOIN TECHNICAL CASE STUDY\n";

        demonstrateTwoDimensionCrossJoin();
        demonstrateEmptyDimension();
        demonstrateRiskDetection();
        demonstrateDuplicates();
        demonstrateGovernanceEngine();
        demonstrateComplexity();

        cout << "\n" << string(78, '=') << "\n";
        cout << "DESIGN RULE\n";
        cout << string(78, '=') << "\n";
        cout << "A Cartesian product should be deliberate. Estimate its cardinality,\n";
        cout << "validate the expected dimensions, and avoid materialization when the\n";
        cout << "candidate space can exceed practical processing or memory limits.\n";

        return 0;
    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }
}
