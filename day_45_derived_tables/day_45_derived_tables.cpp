#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

/*
 * Repository Governance Merge Engine
 *
 * This case study demonstrates the relational idea of derived tables by
 * constructing intermediate result sets inside a C++17 repository-governance
 * engine.
 *
 * The engine evaluates Pull Requests against:
 *   - review decisions,
 *   - approval requirements,
 *   - required status checks,
 *   - protected-branch policies.
 *
 * Each stage creates a distinct data structure that acts as an intermediate
 * relation consumed by a later stage.
 */

enum class PullRequestState {
    Open,
    Closed,
    Merged
};

enum class ReviewState {
    Approved,
    ChangesRequested,
    Commented
};

enum class CheckState {
    Success,
    Failure,
    Pending
};

struct PullRequest {
    int id;
    std::string repository;
    std::string sourceBranch;
    std::string targetBranch;
    std::string author;
    PullRequestState state;
    int additions;
    int deletions;
};

struct Review {
    int id;
    int pullRequestId;
    std::string reviewer;
    ReviewState state;
};

struct StatusCheck {
    int pullRequestId;
    std::string name;
    CheckState state;
};

struct BranchProtectionPolicy {
    std::string repository;
    std::string branch;
    int requiredApprovals;
    std::set<std::string> requiredChecks;
    bool requireLinearHistory;
};

struct ChangeMetric {
    int pullRequestId;
    std::string repository;
    int totalChange;
    double deletionRatio;
};

struct ApprovalSummary {
    int pullRequestId;
    int approvalCount;
    std::set<std::string> approvingReviewers;
};

struct CheckSummary {
    int pullRequestId;
    std::set<std::string> passingChecks;
};

struct PolicyMatch {
    PullRequest pullRequest;
    BranchProtectionPolicy policy;
};

struct MergeDecision {
    int pullRequestId;
    std::string repository;
    std::string targetBranch;
    int approvalCount;
    bool approvalsSatisfied;
    bool checksSatisfied;
    bool stateSatisfied;
    bool mergeEligible;
    std::string reason;
};

std::string stateName(PullRequestState state) {
    switch (state) {
        case PullRequestState::Open:
            return "OPEN";
        case PullRequestState::Closed:
            return "CLOSED";
        case PullRequestState::Merged:
            return "MERGED";
    }
    return "UNKNOWN";
}

std::vector<ChangeMetric> deriveChangeMetrics(
    const std::vector<PullRequest>& pullRequests
) {
    std::vector<ChangeMetric> result;
    result.reserve(pullRequests.size());

    for (const auto& pr : pullRequests) {
        const int total = pr.additions + pr.deletions;

        /*
         * A derived row does not replace the original Pull Request. It exposes
         * only the computed attributes needed by a later operation.
         */
        const double deletionRatio =
            total == 0
                ? 0.0
                : static_cast<double>(pr.deletions) / total;

        result.push_back({
            pr.id,
            pr.repository,
            total,
            deletionRatio
        });
    }

    return result;
}

std::vector<ChangeMetric> filterLargeChanges(
    const std::vector<ChangeMetric>& metrics,
    int minimumChange
) {
    std::vector<ChangeMetric> result;

    for (const auto& metric : metrics) {
        if (metric.totalChange >= minimumChange) {
            result.push_back(metric);
        }
    }

    return result;
}

std::map<std::string, int> countLargeChangesByRepository(
    const std::vector<ChangeMetric>& metrics
) {
    std::map<std::string, int> counts;

    for (const auto& metric : metrics) {
        ++counts[metric.repository];
    }

    return counts;
}

std::vector<ApprovalSummary> deriveApprovalSummary(
    const std::vector<Review>& reviews
) {
    std::map<int, std::set<std::string>> reviewerSets;

    for (const auto& review : reviews) {
        if (review.state == ReviewState::Approved) {
            reviewerSets[review.pullRequestId].insert(review.reviewer);
        }
    }

    std::vector<ApprovalSummary> result;

    for (const auto& [prId, reviewers] : reviewerSets) {
        result.push_back({
            prId,
            static_cast<int>(reviewers.size()),
            reviewers
        });
    }

    return result;
}

std::vector<CheckSummary> derivePassingChecks(
    const std::vector<StatusCheck>& checks
) {
    std::map<int, std::set<std::string>> passing;

    for (const auto& check : checks) {
        if (check.state == CheckState::Success) {
            passing[check.pullRequestId].insert(check.name);
        }
    }

    std::vector<CheckSummary> result;

    for (const auto& [prId, names] : passing) {
        result.push_back({prId, names});
    }

    return result;
}

const ApprovalSummary* findApprovalSummary(
    const std::vector<ApprovalSummary>& summaries,
    int prId
) {
    for (const auto& summary : summaries) {
        if (summary.pullRequestId == prId) {
            return &summary;
        }
    }

    return nullptr;
}

const CheckSummary* findCheckSummary(
    const std::vector<CheckSummary>& summaries,
    int prId
) {
    for (const auto& summary : summaries) {
        if (summary.pullRequestId == prId) {
            return &summary;
        }
    }

    return nullptr;
}

std::vector<PolicyMatch> derivePolicyMatches(
    const std::vector<PullRequest>& pullRequests,
    const std::vector<BranchProtectionPolicy>& policies
) {
    std::vector<PolicyMatch> result;

    /*
     * Repository and branch together identify the policy. Matching only the
     * branch would incorrectly apply the payment-platform policy to another
     * repository's main branch.
     */
    for (const auto& pr : pullRequests) {
        for (const auto& policy : policies) {
            if (
                pr.repository == policy.repository &&
                pr.targetBranch == policy.branch
            ) {
                result.push_back({pr, policy});
            }
        }
    }

    return result;
}

MergeDecision evaluatePolicy(
    const PolicyMatch& match,
    const std::vector<ApprovalSummary>& approvalSummaries,
    const std::vector<CheckSummary>& checkSummaries
) {
    const auto* approval = findApprovalSummary(
        approvalSummaries,
        match.pullRequest.id
    );

    const auto* checks = findCheckSummary(
        checkSummaries,
        match.pullRequest.id
    );

    const int approvalCount =
        approval == nullptr ? 0 : approval->approvalCount;

    const bool approvalsSatisfied =
        approvalCount >= match.policy.requiredApprovals;

    bool checksSatisfied = true;

    for (const auto& required : match.policy.requiredChecks) {
        if (checks == nullptr ||
            !checks->passingChecks.contains(required)) {
            checksSatisfied = false;
            break;
        }
    }

    const bool stateSatisfied =
        match.pullRequest.state == PullRequestState::Open;

    std::string reason;

    if (!stateSatisfied) {
        reason = "Pull Request is not open";
    } else if (!approvalsSatisfied) {
        reason = "required approval count has not been reached";
    } else if (!checksSatisfied) {
        reason = "one or more required status checks are not passing";
    } else {
        reason = "all derived policy conditions are satisfied";
    }

    return {
        match.pullRequest.id,
        match.pullRequest.repository,
        match.pullRequest.targetBranch,
        approvalCount,
        approvalsSatisfied,
        checksSatisfied,
        stateSatisfied,
        approvalsSatisfied &&
            checksSatisfied &&
            stateSatisfied,
        reason
    };
}

std::vector<MergeDecision> evaluateMergeEligibility(
    const std::vector<PullRequest>& pullRequests,
    const std::vector<Review>& reviews,
    const std::vector<StatusCheck>& checks,
    const std::vector<BranchProtectionPolicy>& policies
) {
    /*
     * This function intentionally creates separate intermediate relations:
     *
     * Pull Requests
     *      |
     *      +--> change metrics
     *      |
     * Reviews
     *      |
     *      +--> approval summary
     *      |
     * Status checks
     *      |
     *      +--> passing-check summary
     *      |
     * Branch policies
     *      |
     *      +--> policy matches
     *      |
     *      +--> final eligibility
     *
     * The separation mirrors nested FROM-subquery reasoning: each stage
     * produces a smaller logical relation with a specific responsibility.
     */

    const auto metrics = deriveChangeMetrics(pullRequests);
    const auto significantChanges = filterLargeChanges(metrics, 100);

    std::cout << "\nLarge-change intermediate relation:\n";
    for (const auto& metric : significantChanges) {
        std::cout
            << "PR " << metric.pullRequestId
            << " repository=" << metric.repository
            << " total_change=" << metric.totalChange
            << " deletion_ratio="
            << std::fixed << std::setprecision(2)
            << metric.deletionRatio
            << '\n';
    }

    const auto repositoryCounts =
        countLargeChangesByRepository(significantChanges);

    std::cout << "\nRepository aggregation over derived relation:\n";
    for (const auto& [repository, count] : repositoryCounts) {
        std::cout
            << repository
            << " large_changes=" << count
            << '\n';
    }

    const auto approvalSummaries =
        deriveApprovalSummary(reviews);

    const auto checkSummaries =
        derivePassingChecks(checks);

    const auto policyMatches =
        derivePolicyMatches(pullRequests, policies);

    std::vector<MergeDecision> decisions;

    for (const auto& match : policyMatches) {
        decisions.push_back(
            evaluatePolicy(
                match,
                approvalSummaries,
                checkSummaries
            )
        );
    }

    return decisions;
}

void printDecisions(
    const std::vector<MergeDecision>& decisions
) {
    std::cout << "\nFinal merge-eligibility relation:\n";

    for (const auto& decision : decisions) {
        std::cout
            << "PR " << decision.pullRequestId
            << " repository=" << decision.repository
            << " target=" << decision.targetBranch
            << " approvals=" << decision.approvalCount
            << " approvals_ok="
            << (decision.approvalsSatisfied ? "true" : "false")
            << " checks_ok="
            << (decision.checksSatisfied ? "true" : "false")
            << " state_ok="
            << (decision.stateSatisfied ? "true" : "false")
            << " merge_eligible="
            << (decision.mergeEligible ? "true" : "false")
            << " reason=\"" << decision.reason << "\"\n";
    }
}

void demonstrateMissingIntermediateRows(
    const std::vector<ApprovalSummary>& summaries
) {
    std::cout << "\nMissing derived-row behavior:\n";

    const int unknownPrId = 999;
    const auto* summary =
        findApprovalSummary(summaries, unknownPrId);

    if (summary == nullptr) {
        std::cout
            << "PR " << unknownPrId
            << " has no approval-summary row; "
            << "the evaluator treats its approval count as zero.\n";
    }
}

int main() {
    try {
        const std::vector<PullRequest> pullRequests = {
            {
                101,
                "payment-platform",
                "feature/checkout-validation",
                "main",
                "atul",
                PullRequestState::Open,
                340,
                90
            },
            {
                102,
                "payment-platform",
                "fix/token-expiry",
                "main",
                "neha",
                PullRequestState::Open,
                80,
                25
            },
            {
                103,
                "payment-platform",
                "release/2026-10",
                "release",
                "rahul",
                PullRequestState::Open,
                510,
                180
            },
            {
                104,
                "identity-service",
                "feature/session-hardening",
                "main",
                "meera",
                PullRequestState::Open,
                210,
                60
            }
        };

        const std::vector<Review> reviews = {
            {1, 101, "neha", ReviewState::Approved},
            {2, 101, "rahul", ReviewState::Approved},
            {3, 102, "meera", ReviewState::Approved},
            {4, 103, "neha", ReviewState::Approved},
            {5, 103, "vikas", ReviewState::ChangesRequested},
            {6, 104, "rahul", ReviewState::Approved}
        };

        const std::vector<StatusCheck> checks = {
            {101, "unit-tests", CheckState::Success},
            {101, "security-scan", CheckState::Success},
            {102, "unit-tests", CheckState::Success},
            {102, "security-scan", CheckState::Failure},
            {103, "unit-tests", CheckState::Success},
            {103, "security-scan", CheckState::Success},
            {104, "unit-tests", CheckState::Success},
            {104, "security-scan", CheckState::Success}
        };

        const std::vector<BranchProtectionPolicy> policies = {
            {
                "payment-platform",
                "main",
                2,
                {"unit-tests", "security-scan"},
                true
            },
            {
                "payment-platform",
                "release",
                2,
                {"unit-tests", "security-scan"},
                true
            },
            {
                "identity-service",
                "main",
                2,
                {"unit-tests", "security-scan"},
                false
            }
        };

        const auto decisions = evaluateMergeEligibility(
            pullRequests,
            reviews,
            checks,
            policies
        );

        printDecisions(decisions);

        const auto approvalSummaries =
            deriveApprovalSummary(reviews);

        demonstrateMissingIntermediateRows(
            approvalSummaries
        );

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Repository governance evaluation failed: "
            << error.what()
            << '\n';

        return 1;
    }
}
