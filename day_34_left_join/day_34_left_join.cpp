#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * LEFT JOIN | Repository-style governance case study adapted to relational data
 *
 * Scenario:
 * A software organization needs a reporting engine that combines repositories
 * with deployment records. Every repository must appear in the report, even
 * when no deployment has ever been recorded.
 *
 * The central operation is a LEFT JOIN:
 *
 *   repositories LEFT JOIN deployments
 *       ON repositories.repository_id = deployments.repository_id
 *
 * The program demonstrates:
 * - preservation of left-side rows
 * - NULL-like optional right-side values
 * - one-to-many result expansion
 * - composite-key joins
 * - ON-style filtering
 * - post-join filtering
 * - anti-join reporting
 * - aggregation
 * - validation
 * - explicit C++ ownership/value semantics
 * - hash-based indexing and complexity
 */

struct Repository {
    int id;
    std::string name;
    std::string owner;
    std::string criticality;
};

struct Deployment {
    int id;
    int repository_id;
    std::string environment;
    std::string status;
    int duration_seconds;
};

struct RepositoryDeploymentRow {
    Repository repository;
    std::optional<Deployment> deployment;
};

struct RegionRepository {
    int repository_id;
    std::string region;
    std::string service;
};

struct RegionDeployment {
    int deployment_id;
    int repository_id;
    std::string region;
    std::string version;
};

struct CompositeJoinRow {
    RegionRepository repository;
    std::optional<RegionDeployment> deployment;
};

void print_title(const std::string& title) {
    std::cout << "\n" << std::string(82, '=')
              << "\n" << title
              << "\n" << std::string(82, '=')
              << "\n";
}

void validate_repositories(const std::vector<Repository>& repositories) {
    std::map<int, bool> seen;

    for (const auto& repository : repositories) {
        if (repository.id <= 0) {
            throw std::invalid_argument("Repository IDs must be positive.");
        }

        if (repository.name.empty()) {
            throw std::invalid_argument("Repository names cannot be empty.");
        }

        if (seen.contains(repository.id)) {
            throw std::invalid_argument("Repository IDs must be unique.");
        }

        seen[repository.id] = true;
    }
}

void validate_deployments(
    const std::vector<Deployment>& deployments,
    const std::vector<Repository>& repositories
) {
    std::unordered_map<int, bool> repository_ids;

    for (const auto& repository : repositories) {
        repository_ids[repository.id] = true;
    }

    for (const auto& deployment : deployments) {
        if (deployment.id <= 0) {
            throw std::invalid_argument("Deployment IDs must be positive.");
        }

        if (!repository_ids.contains(deployment.repository_id)) {
            /*
             * A real database could enforce this relationship with a foreign
             * key. Rejecting the invalid reference here prevents an orphaned
             * deployment from entering the reporting dataset.
             */
            throw std::invalid_argument(
                "Deployment references a repository that does not exist."
            );
        }

        if (deployment.environment != "production" &&
            deployment.environment != "staging") {
            throw std::invalid_argument(
                "Environment must be production or staging."
            );
        }

        if (deployment.duration_seconds < 0) {
            throw std::invalid_argument(
                "Deployment duration cannot be negative."
            );
        }
    }
}

std::vector<RepositoryDeploymentRow> left_join_repositories_deployments(
    const std::vector<Repository>& repositories,
    const std::vector<Deployment>& deployments
) {
    /*
     * The right-side table is indexed by repository_id. This converts the
     * equality part of the join into hash lookups instead of scanning every
     * deployment for every repository.
     */
    std::unordered_map<int, std::vector<const Deployment*>> index;

    for (const auto& deployment : deployments) {
        index[deployment.repository_id].push_back(&deployment);
    }

    std::vector<RepositoryDeploymentRow> result;

    for (const auto& repository : repositories) {
        auto iterator = index.find(repository.id);

        if (iterator == index.end()) {
            /*
             * The optional has no value. This is the C++ representation of the
             * NULL-extended right-side columns created by a LEFT JOIN.
             */
            result.push_back({repository, std::nullopt});
            continue;
        }

        /*
         * Multiple deployments create multiple output rows for one repository.
         * This is the normal one-to-many behavior of a relational join.
         */
        for (const Deployment* deployment : iterator->second) {
            result.push_back({repository, *deployment});
        }
    }

    return result;
}

std::vector<RepositoryDeploymentRow> left_join_with_on_condition(
    const std::vector<Repository>& repositories,
    const std::vector<Deployment>& deployments,
    const std::string& required_environment
) {
    std::unordered_map<int, std::vector<const Deployment*>> index;

    for (const auto& deployment : deployments) {
        /*
         * This condition is evaluated as part of the join. A repository with
         * only staging deployments still receives a NULL production deployment
         * row instead of disappearing from the result.
         */
        if (deployment.environment == required_environment) {
            index[deployment.repository_id].push_back(&deployment);
        }
    }

    std::vector<RepositoryDeploymentRow> result;

    for (const auto& repository : repositories) {
        auto iterator = index.find(repository.id);

        if (iterator == index.end()) {
            result.push_back({repository, std::nullopt});
        } else {
            for (const Deployment* deployment : iterator->second) {
                result.push_back({repository, *deployment});
            }
        }
    }

    return result;
}

std::vector<RepositoryDeploymentRow> filter_after_join(
    const std::vector<RepositoryDeploymentRow>& rows,
    const std::string& environment
) {
    std::vector<RepositoryDeploymentRow> result;

    /*
     * This models a WHERE condition. Rows with no deployment contain no
     * environment value, so they fail this predicate and are removed.
     */
    for (const auto& row : rows) {
        if (row.deployment.has_value() &&
            row.deployment->environment == environment) {
            result.push_back(row);
        }
    }

    return result;
}

std::vector<RepositoryDeploymentRow> find_repositories_without_deployment(
    const std::vector<RepositoryDeploymentRow>& rows
) {
    std::vector<RepositoryDeploymentRow> result;

    /*
     * This is the anti-join pattern:
     *
     * LEFT JOIN ...
     * WHERE deployment.id IS NULL
     */
    for (const auto& row : rows) {
        if (!row.deployment.has_value()) {
            result.push_back(row);
        }
    }

    return result;
}

struct DeploymentCounts {
    int count_star = 0;
    int count_deployment_id = 0;
};

std::map<int, DeploymentCounts> count_deployments_by_repository(
    const std::vector<RepositoryDeploymentRow>& rows
) {
    std::map<int, DeploymentCounts> counts;

    for (const auto& row : rows) {
        auto& aggregate = counts[row.repository.id];

        /*
         * COUNT(*) counts the NULL-extended row produced for an unmatched
         * repository.
         */
        ++aggregate.count_star;

        /*
         * COUNT(deployment.id) ignores the NULL right-side value.
         */
        if (row.deployment.has_value()) {
            ++aggregate.count_deployment_id;
        }
    }

    return counts;
}

struct CompositeKey {
    int repository_id;
    std::string region;

    bool operator==(const CompositeKey& other) const {
        return repository_id == other.repository_id &&
               region == other.region;
    }
};

struct CompositeKeyHash {
    std::size_t operator()(const CompositeKey& key) const {
        std::size_t first = std::hash<int>{}(key.repository_id);
        std::size_t second = std::hash<std::string>{}(key.region);

        /*
         * Hash-combining keeps both attributes in the equality key. A join
         * based only on repository_id would incorrectly match different
         * regions.
         */
        return first ^ (second + 0x9e3779b9u + (first << 6) + (first >> 2));
    }
};

std::vector<CompositeJoinRow> composite_left_join(
    const std::vector<RegionRepository>& repositories,
    const std::vector<RegionDeployment>& deployments
) {
    std::unordered_map<
        CompositeKey,
        std::vector<const RegionDeployment*>,
        CompositeKeyHash
    > index;

    for (const auto& deployment : deployments) {
        CompositeKey key{
            deployment.repository_id,
            deployment.region
        };

        index[key].push_back(&deployment);
    }

    std::vector<CompositeJoinRow> result;

    for (const auto& repository : repositories) {
        CompositeKey key{
            repository.repository_id,
            repository.region
        };

        auto iterator = index.find(key);

        if (iterator == index.end()) {
            result.push_back({repository, std::nullopt});
        } else {
            for (const RegionDeployment* deployment : iterator->second) {
                result.push_back({repository, *deployment});
            }
        }
    }

    return result;
}

void print_basic_join(
    const std::vector<RepositoryDeploymentRow>& rows
) {
    std::cout
        << std::left
        << std::setw(8) << "Repo"
        << std::setw(22) << "Repository"
        << std::setw(16) << "Environment"
        << std::setw(14) << "Status"
        << std::setw(12) << "Duration"
        << "\n";

    std::cout << std::string(72, '-') << "\n";

    for (const auto& row : rows) {
        std::cout
            << std::left
            << std::setw(8) << row.repository.id
            << std::setw(22) << row.repository.name;

        if (row.deployment.has_value()) {
            std::cout
                << std::setw(16) << row.deployment->environment
                << std::setw(14) << row.deployment->status
                << std::setw(12) << row.deployment->duration_seconds;
        } else {
            std::cout
                << std::setw(16) << "NULL"
                << std::setw(14) << "NULL"
                << std::setw(12) << "NULL";
        }

        std::cout << "\n";
    }
}

void print_repository_names(
    const std::vector<RepositoryDeploymentRow>& rows
) {
    for (const auto& row : rows) {
        std::cout
            << row.repository.id
            << " | "
            << row.repository.name
            << "\n";
    }
}

void demonstrate_basic_case_study(
    const std::vector<Repository>& repositories,
    const std::vector<Deployment>& deployments
) {
    print_title("Repository deployment inventory: basic LEFT JOIN");

    const auto joined =
        left_join_repositories_deployments(repositories, deployments);

    print_basic_join(joined);

    std::cout
        << "\nThe Payments repository appears twice because it has two deployments.\n"
        << "The Security repository appears once with NULL deployment fields because it has no deployment.\n";
}

void demonstrate_on_vs_where(
    const std::vector<Repository>& repositories,
    const std::vector<Deployment>& deployments
) {
    print_title("ON-style environment condition versus WHERE-style filtering");

    const auto production_in_on =
        left_join_with_on_condition(
            repositories,
            deployments,
            "production"
        );

    std::cout << "Production condition evaluated during the join:\n";
    print_basic_join(production_in_on);

    const auto all_deployments =
        left_join_repositories_deployments(
            repositories,
            deployments
        );

    const auto production_in_where =
        filter_after_join(
            all_deployments,
            "production"
        );

    std::cout << "\nProduction condition evaluated after the join:\n";
    print_basic_join(production_in_where);

    std::cout
        << "\nThe ON-style condition preserves repositories with no production deployment.\n"
        << "The WHERE-style condition removes NULL deployment rows.\n";
}

void demonstrate_anti_join(
    const std::vector<Repository>& repositories,
    const std::vector<Deployment>& deployments
) {
    print_title("Finding repositories without any deployment");

    const auto joined =
        left_join_repositories_deployments(
            repositories,
            deployments
        );

    const auto unmatched =
        find_repositories_without_deployment(joined);

    print_repository_names(unmatched);
}

void demonstrate_aggregation(
    const std::vector<Repository>& repositories,
    const std::vector<Deployment>& deployments
) {
    print_title("Aggregation after LEFT JOIN");

    const auto joined =
        left_join_repositories_deployments(
            repositories,
            deployments
        );

    const auto counts =
        count_deployments_by_repository(joined);

    std::cout
        << std::left
        << std::setw(10) << "Repo"
        << std::setw(16) << "COUNT(*)"
        << std::setw(24) << "COUNT(deployment.id)"
        << "\n";

    std::cout << std::string(50, '-') << "\n";

    for (const auto& [repository_id, aggregate] : counts) {
        std::cout
            << std::left
            << std::setw(10) << repository_id
            << std::setw(16) << aggregate.count_star
            << std::setw(24) << aggregate.count_deployment_id
            << "\n";
    }

    std::cout
        << "\nThe unmatched Security row contributes to COUNT(*) but not to COUNT(deployment.id).\n";
}

void demonstrate_composite_join() {
    print_title("Composite-key LEFT JOIN: repository and region");

    std::vector<RegionRepository> repositories{
        {1, "IN", "payments"},
        {1, "US", "payments"},
        {2, "IN", "analytics"},
    };

    std::vector<RegionDeployment> deployments{
        {101, 1, "IN", "v4.2.1"},
        {102, 2, "IN", "v8.1.0"},
    };

    const auto result =
        composite_left_join(
            repositories,
            deployments
        );

    std::cout
        << std::left
        << std::setw(10) << "Repo"
        << std::setw(10) << "Region"
        << std::setw(18) << "Service"
        << std::setw(16) << "Deployment"
        << std::setw(14) << "Version"
        << "\n";

    std::cout << std::string(68, '-') << "\n";

    for (const auto& row : result) {
        std::cout
            << std::left
            << std::setw(10) << row.repository.repository_id
            << std::setw(10) << row.repository.region
            << std::setw(18) << row.repository.service;

        if (row.deployment.has_value()) {
            std::cout
                << std::setw(16) << row.deployment->deployment_id
                << std::setw(14) << row.deployment->version;
        } else {
            std::cout
                << std::setw(16) << "NULL"
                << std::setw(14) << "NULL";
        }

        std::cout << "\n";
    }
}

void demonstrate_failure_validation() {
    print_title("Data-integrity validation");

    try {
        std::vector<Repository> invalid_repositories{
            {1, "payments", "platform", "critical"},
            {1, "duplicate", "platform", "normal"}
        };

        validate_repositories(invalid_repositories);
    } catch (const std::invalid_argument& error) {
        std::cout
            << "Duplicate repository ID rejected: "
            << error.what()
            << "\n";
    }

    try {
        std::vector<Repository> repositories{
            {1, "payments", "platform", "critical"}
        };

        std::vector<Deployment> invalid_deployments{
            {10, 999, "production", "success", 42}
        };

        validate_deployments(
            invalid_deployments,
            repositories
        );
    } catch (const std::invalid_argument& error) {
        std::cout
            << "Orphan deployment rejected: "
            << error.what()
            << "\n";
    }
}

void demonstrate_performance() {
    print_title("Performance and design characteristics");

    std::cout
        << "Right-side indexing uses unordered_map keyed by repository ID.\n"
        << "Expected equality-join cost is approximately O(L + R + M), where:\n"
        << "  L = number of left rows\n"
        << "  R = number of right rows\n"
        << "  M = number of matching output combinations\n\n"
        << "A nested-loop join can approach O(L * R) when every left row scans the entire right table.\n"
        << "The output itself can become large in one-to-many relationships, so M cannot be ignored.\n"
        << "unordered_map provides average constant-time lookup but can degrade with poor hashing or severe collisions.\n"
        << "std::optional makes the NULL state explicit and prevents accidental dereferencing of a missing deployment.\n"
        << "A production database may choose hash join, merge join, or nested-loop join using indexes and statistics.\n";
}

int main() {
    try {
        print_title("LEFT JOIN | C++ Technical Case Study");

        std::vector<Repository> repositories{
            {1, "Payments API", "Platform", "critical"},
            {2, "Analytics Engine", "Data", "high"},
            {3, "Identity Service", "Security", "critical"},
            {4, "Research Lab", "Research", "normal"}
        };

        std::vector<Deployment> deployments{
            {101, 1, "production", "success", 180},
            {102, 1, "staging", "success", 95},
            {103, 2, "production", "failed", 240},
            {104, 2, "production", "success", 205},
            {105, 4, "staging", "success", 70}
        };

        validate_repositories(repositories);
        validate_deployments(deployments, repositories);

        demonstrate_basic_case_study(
            repositories,
            deployments
        );

        demonstrate_on_vs_where(
            repositories,
            deployments
        );

        demonstrate_anti_join(
            repositories,
            deployments
        );

        demonstrate_aggregation(
            repositories,
            deployments
        );

        demonstrate_composite_join();

        demonstrate_failure_validation();

        demonstrate_performance();

        print_title("Case study complete");
        std::cout
            << "The repository relation remained the preserved side of every LEFT JOIN. "
            << "Missing deployment information was represented by std::nullopt, "
            << "which corresponds to NULL-extended right-side attributes.\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Execution failed: "
            << error.what()
            << "\n";

        return 1;
    }
}
