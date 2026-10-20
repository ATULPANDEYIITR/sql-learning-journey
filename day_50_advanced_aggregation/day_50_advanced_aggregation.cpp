#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

struct PullRequest {
    int number;
    std::string repository;
    std::string author;
    std::string targetBranch;
    std::string status;
    int additions;
    int deletions;
    int commits;
    int reviews;
    int approvals;
    int requestedChanges;
    bool merged;
    std::string mergeStrategy;
    double cycleHours;
    bool checksPassed;
};

struct Aggregate {
    std::size_t count{};
    long long sum{};
    double average{};
    long long minimum{};
    long long maximum{};
};

Aggregate aggregate(const std::vector<long long>& values) {
    if (values.empty()) {
        return {};
    }

    const auto [minimum, maximum] =
        std::minmax_element(values.begin(), values.end());

    const long long sum =
        std::accumulate(values.begin(), values.end(), 0LL);

    return {
        values.size(),
        sum,
        static_cast<double>(sum) / values.size(),
        *minimum,
        *maximum
    };
}

struct RepositoryMetrics {
    std::vector<long long> changes;
    std::vector<long long> reviews;
    std::vector<long long> approvals;
    std::vector<double> cycleHours;
    int prs{};
    int merged{};
    int passedChecks{};
    int largePrs{};
};

void validate(const std::vector<PullRequest>& prs) {
    std::unordered_set<int> numbers;

    for (const auto& pr : prs) {
        if (!numbers.insert(pr.number).second) {
            throw std::invalid_argument(
                "Duplicate Pull Request number: " +
                std::to_string(pr.number)
            );
        }

        if (pr.additions < 0 || pr.deletions < 0 ||
            pr.commits < 0 || pr.reviews < 0 ||
            pr.approvals < 0 || pr.requestedChanges < 0) {
            throw std::invalid_argument(
                "Negative metric in PR #" + std::to_string(pr.number)
            );
        }

        if (pr.merged && !pr.checksPassed) {
            throw std::invalid_argument(
                "Merged PR has failed checks: #" +
                std::to_string(pr.number)
            );
        }

        if (pr.status != "open" &&
            pr.status != "merged" &&
            pr.status != "closed") {
            throw std::invalid_argument(
                "Invalid status in PR #" +
                std::to_string(pr.number)
            );
        }
    }
}

std::map<std::string, RepositoryMetrics>
aggregateByRepository(const std::vector<PullRequest>& prs) {
    std::map<std::string, RepositoryMetrics> result;

    for (const auto& pr : prs) {
        auto& metrics = result[pr.repository];

        ++metrics.prs;
        metrics.merged += pr.merged ? 1 : 0;
        metrics.passedChecks += pr.checksPassed ? 1 : 0;

        const int changes = pr.additions + pr.deletions;
        metrics.changes.push_back(changes);
        metrics.reviews.push_back(pr.reviews);
        metrics.approvals.push_back(pr.approvals);

        if (pr.merged) {
            metrics.cycleHours.push_back(pr.cycleHours);
        }

        // Conditional aggregation is represented by a predicate at
        // accumulation time rather than filtering the entire dataset first.
        if (changes >= 500) {
            ++metrics.largePrs;
        }
    }

    return result;
}

std::map<std::string, int>
aggregateStrategies(const std::vector<PullRequest>& prs) {
    std::map<std::string, int> result;

    for (const auto& pr : prs) {
        if (pr.merged) {
            ++result[pr.mergeStrategy];
        }
    }

    return result;
}

bool mergeEligible(const PullRequest& pr, int requiredApprovals) {
    return pr.status == "open" &&
           pr.checksPassed &&
           pr.approvals >= requiredApprovals &&
           pr.requestedChanges == 0;
}

struct EligibilityAggregate {
    int total{};
    int eligible{};
    int ineligible{};
};

EligibilityAggregate aggregateEligibility(
    const std::vector<PullRequest>& prs,
    int requiredApprovals
) {
    EligibilityAggregate result;

    for (const auto& pr : prs) {
        ++result.total;
        if (mergeEligible(pr, requiredApprovals)) {
            ++result.eligible;
        } else {
            ++result.ineligible;
        }
    }

    return result;
}

void printAggregate(
    const std::string& label,
    const Aggregate& value
) {
    std::cout << "    " << label
              << ": count=" << value.count
              << ", sum=" << value.sum
              << ", average=" << std::fixed
              << std::setprecision(2) << value.average
              << ", min=" << value.minimum
              << ", max=" << value.maximum
              << '\n';
}

int main() {
    try {
        const std::vector<PullRequest> prs = {
            {101, "payments-api", "alice", "main", "merged",
             420, 80, 6, 3, 2, 0, true, "squash", 29.0, true},

            {102, "payments-api", "bob", "main", "merged",
             90, 20, 3, 2, 1, 0, true, "merge", 7.0, true},

            {103, "payments-api", "carol", "release", "closed",
             700, 300, 12, 4, 0, 2, false, "none", 0.0, false},

            {104, "web-portal", "alice", "main", "merged",
             130, 45, 4, 3, 2, 0, true, "rebase", 23.0, true},

            {105, "web-portal", "david", "main", "open",
             35, 8, 2, 1, 0, 0, false, "none", 0.0, true},

            {106, "web-portal", "carol", "develop", "merged",
             250, 120, 7, 4, 3, 0, true, "squash", 30.0, true}
        };

        validate(prs);

        const auto repositoryMetrics = aggregateByRepository(prs);

        std::cout << "Repository aggregation\n";

        for (const auto& [repository, metrics] : repositoryMetrics) {
            std::cout << '\n' << repository << '\n';
            std::cout << "  PRs: " << metrics.prs << '\n';
            std::cout << "  Merged: " << metrics.merged << '\n';
            std::cout << "  Merge rate: "
                      << std::fixed << std::setprecision(1)
                      << (100.0 * metrics.merged / metrics.prs)
                      << "%\n";

            printAggregate("Changes", aggregate(metrics.changes));
            printAggregate("Reviews", aggregate(metrics.reviews));
            printAggregate("Approvals", aggregate(metrics.approvals));
            printAggregate("Cycle hours",
                           aggregate(std::vector<long long>(
                               metrics.cycleHours.begin(),
                               metrics.cycleHours.end()
                           )));

            std::cout << "    Passed checks: "
                      << metrics.passedChecks << '\n';
            std::cout << "    Large PRs: "
                      << metrics.largePrs << '\n';
        }

        std::cout << "\nMerge strategy aggregation\n";
        for (const auto& [strategy, count] : aggregateStrategies(prs)) {
            std::cout << "  " << strategy << ": "
                      << count << '\n';
        }

        constexpr int requiredApprovals = 2;
        const auto eligibility =
            aggregateEligibility(prs, requiredApprovals);

        std::cout << "\nMerge eligibility aggregation\n";
        std::cout << "  Total: " << eligibility.total << '\n';
        std::cout << "  Eligible: " << eligibility.eligible << '\n';
        std::cout << "  Ineligible: " << eligibility.ineligible << '\n';

        // A protected branch can combine several independent conditions.
        // Aggregating their failures gives governance teams a useful
        // diagnostic distribution rather than a single Boolean result.
        std::map<std::string, int> failureReasons;

        for (const auto& pr : prs) {
            if (pr.status != "open") ++failureReasons["not_open"];
            if (!pr.checksPassed) ++failureReasons["failed_checks"];
            if (pr.approvals < requiredApprovals)
                ++failureReasons["insufficient_approvals"];
            if (pr.requestedChanges > 0)
                ++failureReasons["requested_changes"];
        }

        std::cout << "\nGovernance failure aggregation\n";
        for (const auto& [reason, count] : failureReasons) {
            std::cout << "  " << reason << ": "
                      << count << '\n';
        }

    } catch (const std::exception& error) {
        std::cerr << "Governance aggregation failed: "
                  << error.what() << '\n';
        return 1;
    }

    return 0;
}
