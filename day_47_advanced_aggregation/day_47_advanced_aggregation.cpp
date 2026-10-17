#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

enum class PullRequestState {
    Open,
    Merged,
    Closed
};

struct PullRequest {
    int id;
    std::string repository;
    std::string team;
    std::string category;
    PullRequestState state;
    int additions;
    int deletions;
    int reviewers;
    int approvals;
    bool checksPassed;
};

struct Aggregate {
    int count = 0;
    int merged = 0;
    int open = 0;
    int closed = 0;
    int approved = 0;
    int failedChecks = 0;
    long long additions = 0;
    long long deletions = 0;
    double approvalCoverage = 0.0;
};

struct GovernancePolicy {
    int minimumMerged = 2;
    double minimumApprovalCoverage = 0.75;
    double minimumCheckPassRate = 0.80;
};

std::string stateName(PullRequestState state) {
    switch (state) {
        case PullRequestState::Open:
            return "open";
        case PullRequestState::Merged:
            return "merged";
        case PullRequestState::Closed:
            return "closed";
    }

    return "unknown";
}

void validate(const PullRequest& pr) {
    if (pr.id <= 0) {
        throw std::invalid_argument("Pull Request ID must be positive");
    }

    if (pr.additions < 0 || pr.deletions < 0) {
        throw std::invalid_argument("Line counts cannot be negative");
    }

    if (pr.reviewers < 0 || pr.approvals < 0) {
        throw std::invalid_argument("Reviewer counts cannot be negative");
    }

    if (pr.approvals > pr.reviewers) {
        throw std::invalid_argument(
            "Approval count cannot exceed reviewer count"
        );
    }
}

void accumulate(Aggregate& aggregate, const PullRequest& pr) {
    ++aggregate.count;
    aggregate.additions += pr.additions;
    aggregate.deletions += pr.deletions;

    if (pr.state == PullRequestState::Merged) {
        ++aggregate.merged;
    } else if (pr.state == PullRequestState::Open) {
        ++aggregate.open;
    } else {
        ++aggregate.closed;
    }

    if (pr.approvals >= 2) {
        ++aggregate.approved;
    }

    if (!pr.checksPassed) {
        ++aggregate.failedChecks;
    }

    /*
     * Approval coverage is an aggregate of reviewer-level participation.
     * Keeping its numerator as a sum allows the final average to be computed
     * after all records in the group have been processed.
     */
    if (pr.reviewers > 0) {
        aggregate.approvalCoverage +=
            static_cast<double>(pr.approvals) / pr.reviewers;
    }
}

void finalize(Aggregate& aggregate) {
    if (aggregate.count > 0) {
        aggregate.approvalCoverage /= aggregate.count;
    }
}

template <typename KeyFunction>
std::map<std::string, Aggregate> groupBy(
    const std::vector<PullRequest>& pullRequests,
    KeyFunction keyFunction
) {
    std::map<std::string, Aggregate> result;

    for (const auto& pr : pullRequests) {
        result[keyFunction(pr)].count += 0;
        accumulate(result[keyFunction(pr)], pr);
    }

    for (auto& [key, aggregate] : result) {
        finalize(aggregate);
    }

    return result;
}

std::map<std::string, Aggregate> aggregateByRepository(
    const std::vector<PullRequest>& pullRequests
) {
    return groupBy(
        pullRequests,
        [](const PullRequest& pr) {
            return pr.repository;
        }
    );
}

std::map<std::string, Aggregate> aggregateByCategory(
    const std::vector<PullRequest>& pullRequests
) {
    return groupBy(
        pullRequests,
        [](const PullRequest& pr) {
            return pr.category;
        }
    );
}

struct ConditionalMetrics {
    int total = 0;
    int securityPullRequests = 0;
    int largeChanges = 0;
    int mergedWithPassingChecks = 0;
    int openWithoutRequiredApprovals = 0;
    long long mergedAdditions = 0;
};

ConditionalMetrics conditionalAggregation(
    const std::vector<PullRequest>& pullRequests
) {
    ConditionalMetrics metrics;

    for (const auto& pr : pullRequests) {
        ++metrics.total;

        if (pr.category == "security") {
            ++metrics.securityPullRequests;
        }

        if (pr.additions + pr.deletions >= 500) {
            ++metrics.largeChanges;
        }

        if (pr.state == PullRequestState::Merged && pr.checksPassed) {
            ++metrics.mergedWithPassingChecks;
            metrics.mergedAdditions += pr.additions;
        }

        if (pr.state == PullRequestState::Open && pr.approvals < 2) {
            ++metrics.openWithoutRequiredApprovals;
        }
    }

    return metrics;
}

bool eligibleForGovernance(
    const Aggregate& aggregate,
    const GovernancePolicy& policy
) {
    if (aggregate.count == 0) {
        return false;
    }

    const double checkPassRate =
        1.0 -
        static_cast<double>(aggregate.failedChecks) / aggregate.count;

    return aggregate.merged >= policy.minimumMerged &&
           aggregate.approvalCoverage >= policy.minimumApprovalCoverage &&
           checkPassRate >= policy.minimumCheckPassRate;
}

void printAggregates(
    const std::string& title,
    const std::map<std::string, Aggregate>& aggregates
) {
    std::cout << "\n" << title << "\n";
    std::cout << std::string(title.size(), '-') << "\n";

    std::cout
        << std::left << std::setw(24) << "Group"
        << std::right << std::setw(8) << "Count"
        << std::setw(10) << "Merged"
        << std::setw(10) << "Open"
        << std::setw(10) << "Failed"
        << std::setw(14) << "Lines Changed"
        << std::setw(16) << "Approval Cov."
        << "\n";

    for (const auto& [key, aggregate] : aggregates) {
        const long long linesChanged =
            aggregate.additions + aggregate.deletions;

        std::cout
            << std::left << std::setw(24) << key
            << std::right << std::setw(8) << aggregate.count
            << std::setw(10) << aggregate.merged
            << std::setw(10) << aggregate.open
            << std::setw(10) << aggregate.failedChecks
            << std::setw(14) << linesChanged
            << std::setw(15)
            << std::fixed << std::setprecision(2)
            << aggregate.approvalCoverage
            << "\n";
    }
}

int main() {
    try {
        const std::vector<PullRequest> pullRequests = {
            {1001, "platform-api", "Core", "feature",
             PullRequestState::Merged, 420, 90, 2, 2, true},

            {1002, "platform-api", "Core", "bugfix",
             PullRequestState::Merged, 80, 40, 1, 1, true},

            {1003, "identity-service", "Security", "security",
             PullRequestState::Merged, 260, 30, 3, 3, true},

            {1004, "identity-service", "Security", "bugfix",
             PullRequestState::Open, 120, 70, 2, 1, true},

            {1005, "data-pipeline", "Data", "feature",
             PullRequestState::Merged, 760, 210, 3, 2, true},

            {1006, "data-pipeline", "Data", "performance",
             PullRequestState::Merged, 310, 190, 2, 2, true},

            {1007, "platform-api", "Core", "feature",
             PullRequestState::Open, 900, 420, 4, 2, false},

            {1008, "identity-service", "Security", "security",
             PullRequestState::Merged, 180, 20, 3, 3, true},

            {1009, "data-pipeline", "Data", "bugfix",
             PullRequestState::Closed, 95, 60, 1, 0, false},

            {1010, "platform-api", "Core", "performance",
             PullRequestState::Merged, 500, 150, 2, 2, true}
        };

        for (const auto& pr : pullRequests) {
            validate(pr);
        }

        auto repositoryAggregates =
            aggregateByRepository(pullRequests);

        auto categoryAggregates =
            aggregateByCategory(pullRequests);

        printAggregates(
            "Repository Aggregation",
            repositoryAggregates
        );

        printAggregates(
            "Category Aggregation",
            categoryAggregates
        );

        const auto conditional =
            conditionalAggregation(pullRequests);

        std::cout << "\nConditional Aggregation\n";
        std::cout << "----------------------\n";
        std::cout
            << "Total Pull Requests: "
            << conditional.total << "\n"
            << "Security Pull Requests: "
            << conditional.securityPullRequests << "\n"
            << "Large changes: "
            << conditional.largeChanges << "\n"
            << "Merged with passing checks: "
            << conditional.mergedWithPassingChecks << "\n"
            << "Open without required approvals: "
            << conditional.openWithoutRequiredApprovals << "\n"
            << "Merged additions with passing checks: "
            << conditional.mergedAdditions << "\n";

        /*
         * Governance is evaluated from aggregates rather than from one
         * Pull Request at a time. This separates raw event data from the
         * repository-level decision derived from that data.
         */
        const GovernancePolicy policy;

        std::cout << "\nGovernance Eligibility\n";
        std::cout << "---------------------\n";

        for (const auto& [repository, aggregate] : repositoryAggregates) {
            const bool eligible =
                eligibleForGovernance(aggregate, policy);

            const double checkPassRate =
                1.0 -
                static_cast<double>(aggregate.failedChecks) /
                aggregate.count;

            std::cout
                << repository
                << " -> "
                << (eligible ? "eligible" : "not eligible")
                << " | merged=" << aggregate.merged
                << " | approvalCoverage="
                << std::fixed << std::setprecision(2)
                << aggregate.approvalCoverage
                << " | checkPassRate="
                << checkPassRate
                << "\n";
        }

        /*
         * The grouped map uses logarithmic ordered-map insertion. An
         * unordered_map could provide expected constant-time grouping when
         * ordering is unnecessary. The selected map is useful here because
         * deterministic repository ordering is part of the report output.
         */
        std::cout << "\nAggregation Strategy\n";
        std::cout << "--------------------\n";
        std::cout
            << "Ordered grouping is used because the report requires "
               "deterministic group ordering.\n";

    } catch (const std::exception& error) {
        std::cerr
            << "Aggregation engine failure: "
            << error.what()
            << "\n";
        return 1;
    }

    return 0;
}
