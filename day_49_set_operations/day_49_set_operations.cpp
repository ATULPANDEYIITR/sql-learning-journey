#include <algorithm>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using EmailSet = std::set<std::string>;

EmailSet setUnion(const EmailSet& left, const EmailSet& right) {
    EmailSet result;
    std::set_union(
        left.begin(), left.end(),
        right.begin(), right.end(),
        std::inserter(result, result.begin())
    );
    return result;
}

EmailSet setIntersection(const EmailSet& left, const EmailSet& right) {
    EmailSet result;
    std::set_intersection(
        left.begin(), left.end(),
        right.begin(), right.end(),
        std::inserter(result, result.begin())
    );
    return result;
}

EmailSet setDifference(const EmailSet& left, const EmailSet& right) {
    EmailSet result;
    std::set_difference(
        left.begin(), left.end(),
        right.begin(), right.end(),
        std::inserter(result, result.begin())
    );
    return result;
}

std::vector<std::string> unionAll(
    const std::vector<std::string>& left,
    const std::vector<std::string>& right
) {
    std::vector<std::string> result;
    result.reserve(left.size() + right.size());
    result.insert(result.end(), left.begin(), left.end());
    result.insert(result.end(), right.begin(), right.end());
    return result;
}

void printSet(const std::string& label, const EmailSet& values) {
    std::cout << label << ": {";
    bool first = true;

    for (const auto& value : values) {
        if (!first) {
            std::cout << ", ";
        }
        std::cout << value;
        first = false;
    }

    std::cout << "}\n";
}

void printVector(const std::string& label, const std::vector<std::string>& values) {
    std::cout << label << ": [";

    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i > 0) {
            std::cout << ", ";
        }
        std::cout << values[i];
    }

    std::cout << "]\n";
}

class RepositoryGovernanceCaseStudy {
private:
    std::map<std::string, EmailSet> repositoryTeams;

public:
    void addRepository(const std::string& repository, EmailSet members) {
        if (repository.empty()) {
            throw std::invalid_argument("Repository name cannot be empty.");
        }

        if (members.empty()) {
            throw std::invalid_argument("Repository must have at least one member.");
        }

        repositoryTeams.emplace(repository, std::move(members));
    }

    EmailSet combinedMaintainers(
        const std::string& repositoryA,
        const std::string& repositoryB
    ) const {
        return setUnion(repositoryTeams.at(repositoryA), repositoryTeams.at(repositoryB));
    }

    EmailSet sharedMaintainers(
        const std::string& repositoryA,
        const std::string& repositoryB
    ) const {
        return setIntersection(repositoryTeams.at(repositoryA), repositoryTeams.at(repositoryB));
    }

    EmailSet exclusiveMaintainers(
        const std::string& repositoryA,
        const std::string& repositoryB
    ) const {
        return setDifference(repositoryTeams.at(repositoryA), repositoryTeams.at(repositoryB));
    }

    std::map<std::string, int> crossRepositoryCoverage() const {
        std::map<std::string, int> coverage;

        for (const auto& [repository, members] : repositoryTeams) {
            for (const auto& member : members) {
                ++coverage[member];
            }
        }

        return coverage;
    }
};

int main() {
    try {
        std::cout << "Set Operations: Repository Governance Case Study\n\n";

        EmailSet applicationTeam{
            "alice@example.com",
            "bob@example.com",
            "carol@example.com",
            "david@example.com"
        };

        EmailSet securityTeam{
            "carol@example.com",
            "david@example.com",
            "erin@example.com"
        };

        printSet("Application team UNION Security team",
                 setUnion(applicationTeam, securityTeam));

        printSet("Application team INTERSECT Security team",
                 setIntersection(applicationTeam, securityTeam));

        printSet("Application team EXCEPT Security team",
                 setDifference(applicationTeam, securityTeam));

        printSet("Security team EXCEPT Application team",
                 setDifference(securityTeam, applicationTeam));

        std::vector<std::string> pullRequestReviewers{
            "alice@example.com",
            "bob@example.com",
            "bob@example.com"
        };

        std::vector<std::string> requiredReviewers{
            "bob@example.com",
            "carol@example.com"
        };

        printVector(
            "Reviewer UNION ALL",
            unionAll(pullRequestReviewers, requiredReviewers)
        );

        EmailSet reviewerSet(
            pullRequestReviewers.begin(),
            pullRequestReviewers.end()
        );

        EmailSet requiredSet(
            requiredReviewers.begin(),
            requiredReviewers.end()
        );

        printSet("Distinct reviewers", reviewerSet);
        printSet("Reviewers satisfying required pool",
                 setIntersection(reviewerSet, requiredSet));

        RepositoryGovernanceCaseStudy governance;

        governance.addRepository(
            "payments-service",
            {
                "alice@example.com",
                "bob@example.com",
                "carol@example.com"
            }
        );

        governance.addRepository(
            "identity-service",
            {
                "carol@example.com",
                "david@example.com",
                "erin@example.com"
            }
        );

        governance.addRepository(
            "security-platform",
            {
                "carol@example.com",
                "erin@example.com",
                "frank@example.com"
            }
        );

        printSet(
            "Cross-service maintainer UNION",
            governance.combinedMaintainers(
                "payments-service",
                "identity-service"
            )
        );

        printSet(
            "Cross-service shared maintainers",
            governance.sharedMaintainers(
                "payments-service",
                "identity-service"
            )
        );

        printSet(
            "Payments-only maintainers",
            governance.exclusiveMaintainers(
                "payments-service",
                "identity-service"
            )
        );

        std::cout << "\nMaintainer coverage across repositories:\n";

        for (const auto& [member, count] : governance.crossRepositoryCoverage()) {
            std::cout << "  " << member << ": " << count << " repository(s)\n";
        }

        EmailSet allThree = setIntersection(
            governance.sharedMaintainers("payments-service", "identity-service"),
            governance.sharedMaintainers("identity-service", "security-platform")
        );

        printSet("Maintainers common to all three services", allThree);

        std::cout
            << "\nAlgorithmic behavior:\n"
            << "std::set_union, std::set_intersection, and std::set_difference "
            << "operate on sorted ranges. With sets of sizes n and m, each "
            << "operation runs in O(n + m) time.\n";

        std::cout
            << "\nUNION and UNION ALL are deliberately distinct. "
            << "std::set_union removes duplicate values because the inputs "
            << "represent sets, while unionAll operates on vectors and "
            << "preserves duplicate occurrences.\n";

        std::cout
            << "\nA production system must choose the representation according "
            << "to business meaning: a set is appropriate for membership and "
            << "distinctness, while a sequence is required when occurrence "
            << "frequency affects the result.\n";

        return 0;
    } catch (const std::out_of_range& error) {
        std::cerr << "Unknown repository: " << error.what() << '\n';
        return 1;
    } catch (const std::exception& error) {
        std::cerr << "Validation failure: " << error.what() << '\n';
        return 1;
    }
}
