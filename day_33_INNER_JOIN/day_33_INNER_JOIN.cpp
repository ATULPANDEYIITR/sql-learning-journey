#include <algorithm>
#include <cassert>
#include <functional>
#include <iomanip>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

/*
 * INNER JOIN case study:
 * Repository governance reporting.
 *
 * The system combines three relations:
 *
 *   Repository
 *       |
 *       | repository_id
 *       v
 *   PullRequest
 *       |
 *       | author_id
 *       v
 *   Developer
 *
 * The program evaluates whether a pull request can be considered a complete
 * governance record. INNER JOIN semantics are deliberately used: if a
 * referenced repository or author cannot be matched, the corresponding
 * combination is excluded from the joined result.
 *
 * C++17 is sufficient.
 */

struct Repository {
    int repositoryId;
    std::string name;
    std::string owner;
};

struct PullRequest {
    int pullRequestId;
    int repositoryId;
    int authorId;
    std::string title;
    std::string state;
};

struct Developer {
    int developerId;
    std::string username;
    std::string team;
};

struct GovernanceRecord {
    int pullRequestId;
    std::string repositoryName;
    std::string author;
    std::string team;
    std::string title;
    std::string state;
};

struct BranchPolicy {
    int repositoryId;
    std::string branchName;
    int requiredApprovals;
    bool requireLinearHistory;
    bool allowForcePush;
};

struct StatusCheck {
    int pullRequestId;
    std::string checkName;
    bool passed;
};

struct Review {
    int pullRequestId;
    int reviewerId;
    std::string state;
    bool dismissed;
};

struct MergeDecision {
    int pullRequestId;
    bool repositoryMatched;
    bool authorMatched;
    bool branchPolicyMatched;
    bool requiredChecksPassed;
    bool requiredApprovalsSatisfied;
    bool mergeable;
    std::string reason;
};

template <typename Left, typename Right, typename Key, typename Result>
std::vector<Result> equalityInnerJoin(
    const std::vector<Left>& leftRows,
    const std::vector<Right>& rightRows,
    std::function<Key(const Left&)> leftKey,
    std::function<Key(const Right&)> rightKey,
    std::function<Result(const Left&, const Right&)> combine
) {
    /*
     * This generic implementation indexes the right relation.
     *
     * Duplicate right-side keys are preserved in vectors. Therefore an input
     * key with three right-side matches produces three result rows for each
     * compatible left-side row.
     */
    std::unordered_multimap<Key, const Right*> index;

    for (const auto& right : rightRows) {
        index.emplace(rightKey(right), &right);
    }

    std::vector<Result> output;

    for (const auto& left : leftRows) {
        const auto key = leftKey(left);
        const auto range = index.equal_range(key);

        for (auto iterator = range.first; iterator != range.second; ++iterator) {
            output.push_back(combine(left, *iterator->second));
        }
    }

    return output;
}

template <typename Left, typename Right, typename Result>
std::vector<Result> nestedLoopInnerJoin(
    const std::vector<Left>& leftRows,
    const std::vector<Right>& rightRows,
    std::function<bool(const Left&, const Right&)> condition,
    std::function<Result(const Left&, const Right&)> combine
) {
    /*
     * A nested-loop join supports arbitrary predicates rather than only
     * equality. It is useful when the relationship includes multiple
     * conditions that cannot be represented by a single hash key.
     */
    std::vector<Result> output;

    for (const auto& left : leftRows) {
        for (const auto& right : rightRows) {
            if (condition(left, right)) {
                output.push_back(combine(left, right));
            }
        }
    }

    return output;
}

void printGovernanceRecords(const std::vector<GovernanceRecord>& records) {
    std::cout << "\n"
              << std::left
              << std::setw(8) << "PR"
              << std::setw(20) << "Repository"
              << std::setw(15) << "Author"
              << std::setw(15) << "Team"
              << std::setw(30) << "Title"
              << std::setw(12) << "State"
              << '\n';

    std::cout << std::string(100, '-') << '\n';

    for (const auto& record : records) {
        std::cout << std::left
                  << std::setw(8) << record.pullRequestId
                  << std::setw(20) << record.repositoryName
                  << std::setw(15) << record.author
                  << std::setw(15) << record.team
                  << std::setw(30) << record.title
                  << std::setw(12) << record.state
                  << '\n';
    }
}

void printDecision(const MergeDecision& decision) {
    std::cout << "\nPull Request " << decision.pullRequestId
              << ": " << (decision.mergeable ? "MERGEABLE" : "BLOCKED")
              << '\n';

    std::cout << "  repository matched: "
              << std::boolalpha << decision.repositoryMatched << '\n';
    std::cout << "  author matched: "
              << decision.authorMatched << '\n';
    std::cout << "  branch policy matched: "
              << decision.branchPolicyMatched << '\n';
    std::cout << "  required checks passed: "
              << decision.requiredChecksPassed << '\n';
    std::cout << "  required approvals satisfied: "
              << decision.requiredApprovalsSatisfied << '\n';
    std::cout << "  reason: " << decision.reason << '\n';
}

std::vector<GovernanceRecord> buildGovernanceDataset(
    const std::vector<Repository>& repositories,
    const std::vector<PullRequest>& pullRequests,
    const std::vector<Developer>& developers
) {
    /*
     * First join:
     * PullRequest.repositoryId = Repository.repositoryId
     *
     * Second join:
     * PullRequest.authorId = Developer.developerId
     *
     * A PR missing either relationship disappears from the final INNER JOIN
     * result. This is intentionally different from a LEFT JOIN, which would
     * preserve the unmatched PR.
     */
    struct RepositoryPullRequest {
        Repository repository;
        PullRequest pullRequest;
    };

    const auto repositoryPullRequests =
        equalityInnerJoin<Repository, PullRequest, int, RepositoryPullRequest>(
            repositories,
            pullRequests,
            [](const Repository& repository) {
                return repository.repositoryId;
            },
            [](const PullRequest& pullRequest) {
                return pullRequest.repositoryId;
            },
            [](const Repository& repository, const PullRequest& pullRequest) {
                return RepositoryPullRequest{repository, pullRequest};
            }
        );

    return nestedLoopInnerJoin<
        RepositoryPullRequest,
        Developer,
        GovernanceRecord
    >(
        repositoryPullRequests,
        developers,
        [](const RepositoryPullRequest& pair, const Developer& developer) {
            return pair.pullRequest.authorId == developer.developerId;
        },
        [](const RepositoryPullRequest& pair, const Developer& developer) {
            return GovernanceRecord{
                pair.pullRequest.pullRequestId,
                pair.repository.name,
                developer.username,
                developer.team,
                pair.pullRequest.title,
                pair.pullRequest.state
            };
        }
    );
}

std::optional<BranchPolicy> findBranchPolicy(
    const std::vector<BranchPolicy>& policies,
    int repositoryId,
    const std::string& branchName
) {
    /*
     * Branch policy lookup is a composite relationship:
     * repository ID AND target branch must match.
     */
    for (const auto& policy : policies) {
        if (policy.repositoryId == repositoryId &&
            policy.branchName == branchName) {
            return policy;
        }
    }

    return std::nullopt;
}

bool requiredChecksPassed(
    const std::vector<StatusCheck>& checks,
    int pullRequestId
) {
    /*
     * A real policy engine would identify which checks are required. This
     * case study treats every recorded check for the PR as required.
     *
     * An absent check set is considered a failure rather than an accidental
     * success, because missing evidence should not satisfy a governance rule.
     */
    bool foundCheck = false;

    for (const auto& check : checks) {
        if (check.pullRequestId != pullRequestId) {
            continue;
        }

        foundCheck = true;

        if (!check.passed) {
            return false;
        }
    }

    return foundCheck;
}

bool approvalsSatisfied(
    const std::vector<Review>& reviews,
    const std::unordered_set<int>& eligibleReviewerIds,
    int pullRequestId,
    int requiredApprovals
) {
    /*
     * Approval is counted only when:
     * - it belongs to this PR,
     * - the reviewer is eligible,
     * - the review is currently APPROVED,
     * - and the approval has not been dismissed.
     *
     * Distinct reviewers are counted rather than multiple approval records
     * from the same reviewer. This prevents duplicate review events from
     * inflating the approval count.
     */
    std::unordered_set<int> approvingReviewers;

    for (const auto& review : reviews) {
        if (review.pullRequestId != pullRequestId) {
            continue;
        }

        if (review.state != "APPROVED" || review.dismissed) {
            continue;
        }

        if (!eligibleReviewerIds.contains(review.reviewerId)) {
            continue;
        }

        approvingReviewers.insert(review.reviewerId);
    }

    return static_cast<int>(approvingReviewers.size()) >= requiredApprovals;
}

MergeDecision evaluateMergeEligibility(
    const PullRequest& pullRequest,
    const std::vector<Repository>& repositories,
    const std::vector<Developer>& developers,
    const std::vector<BranchPolicy>& policies,
    const std::vector<StatusCheck>& checks,
    const std::vector<Review>& reviews,
    const std::unordered_set<int>& eligibleReviewerIds,
    const std::string& targetBranch
) {
    /*
     * This function combines relationship validation with governance checks.
     * The INNER JOIN relationship itself is represented by the explicit
     * repository and author matches. Policy and status checks are separate
     * constraints applied after the relevant entities have been identified.
     */
    const auto repositoryIt = std::find_if(
        repositories.begin(),
        repositories.end(),
        [&](const Repository& repository) {
            return repository.repositoryId == pullRequest.repositoryId;
        }
    );

    if (repositoryIt == repositories.end()) {
        return {
            pullRequest.pullRequestId,
            false,
            false,
            false,
            false,
            false,
            false,
            "No repository row matches the pull request repository_id."
        };
    }

    const auto developerIt = std::find_if(
        developers.begin(),
        developers.end(),
        [&](const Developer& developer) {
            return developer.developerId == pullRequest.authorId;
        }
    );

    if (developerIt == developers.end()) {
        return {
            pullRequest.pullRequestId,
            true,
            false,
            false,
            false,
            false,
            false,
            "No developer row matches the pull request author_id."
        };
    }

    const auto policy =
        findBranchPolicy(policies, pullRequest.repositoryId, targetBranch);

    if (!policy.has_value()) {
        return {
            pullRequest.pullRequestId,
            true,
            true,
            false,
            false,
            false,
            false,
            "No branch policy matches repository_id and target branch."
        };
    }

    const bool checksPass =
        requiredChecksPassed(checks, pullRequest.pullRequestId);

    if (!checksPass) {
        return {
            pullRequest.pullRequestId,
            true,
            true,
            true,
            false,
            false,
            false,
            "One or more required status checks are missing or failed."
        };
    }

    const bool approvalsPass = approvalsSatisfied(
        reviews,
        eligibleReviewerIds,
        pullRequest.pullRequestId,
        policy->requiredApprovals
    );

    if (!approvalsPass) {
        return {
            pullRequest.pullRequestId,
            true,
            true,
            true,
            true,
            false,
            false,
            "The number of eligible, active approvals is below the policy."
        };
    }

    return {
        pullRequest.pullRequestId,
        true,
        true,
        true,
        true,
        true,
        true,
        "All relationship and governance conditions are satisfied."
    };
}

void demonstrateDuplicateMatches() {
    std::cout << "\n=== Duplicate-key INNER JOIN behavior ===\n";

    struct Team {
        int id;
        std::string name;
    };

    struct Person {
        int id;
        int teamId;
        std::string username;
    };

    const std::vector<Team> teams = {
        {1, "Platform"},
        {2, "Security"}
    };

    const std::vector<Person> people = {
        {10, 1, "alice"},
        {11, 1, "bob"},
        {12, 2, "carol"},
        {13, 1, "dave"}
    };

    struct Match {
        std::string team;
        std::string username;
    };

    const auto matches =
        equalityInnerJoin<Team, Person, int, Match>(
            teams,
            people,
            [](const Team& team) {
                return team.id;
            },
            [](const Person& person) {
                return person.teamId;
            },
            [](const Team& team, const Person& person) {
                return Match{team.name, person.username};
            }
        );

    for (const auto& match : matches) {
        std::cout << match.team << " -> " << match.username << '\n';
    }

    assert(matches.size() == 4);
}

void demonstrateCompositeCondition() {
    std::cout << "\n=== Composite join condition ===\n";

    const std::vector<BranchPolicy> policies = {
        {1, "main", 2, true, false},
        {1, "develop", 1, false, false},
        {2, "main", 1, true, false}
    };

    struct PullRequestTarget {
        int id;
        int repositoryId;
        std::string branch;
    };

    const std::vector<PullRequestTarget> targets = {
        {101, 1, "main"},
        {102, 1, "develop"},
        {103, 2, "main"},
        {104, 1, "release"}
    };

    struct PolicyMatch {
        int pullRequestId;
        int requiredApprovals;
    };

    const auto matches =
        nestedLoopInnerJoin<
            BranchPolicy,
            PullRequestTarget,
            PolicyMatch
        >(
            policies,
            targets,
            [](const BranchPolicy& policy,
               const PullRequestTarget& target) {
                return policy.repositoryId == target.repositoryId &&
                       policy.branchName == target.branch;
            },
            [](const BranchPolicy& policy,
               const PullRequestTarget& target) {
                return PolicyMatch{
                    target.id,
                    policy.requiredApprovals
                };
            }
        );

    for (const auto& match : matches) {
        std::cout << "PR " << match.pullRequestId
                  << " requires " << match.requiredApprovals
                  << " approval(s)\n";
    }

    assert(matches.size() == 3);
}

void runAssertions(
    const std::vector<GovernanceRecord>& records
) {
    /*
     * PR 9001, 9002, and 9003 have valid repository and developer references.
     * PR 9004 references a non-existent author and must disappear from the
     * complete INNER JOIN result.
     */
    assert(records.size() == 3);

    const auto containsPr = [&](int pullRequestId) {
        return std::any_of(
            records.begin(),
            records.end(),
            [&](const GovernanceRecord& record) {
                return record.pullRequestId == pullRequestId;
            }
        );
    };

    assert(containsPr(9001));
    assert(containsPr(9002));
    assert(containsPr(9003));
    assert(!containsPr(9004));

    for (const auto& record : records) {
        assert(!record.repositoryName.empty());
        assert(!record.author.empty());
    }

    std::cout << "\nAll C++ INNER JOIN assertions passed.\n";
}

int main() {
    try {
        std::cout << "INNER JOIN repository governance case study\n";

        const std::vector<Repository> repositories = {
            {100, "market-prism", "atul"},
            {200, "asset-logistics", "atul"},
            {300, "security-engine", "atul"}
        };

        const std::vector<Developer> developers = {
            {501, "maya", "quant"},
            {502, "rohan", "security"},
            {503, "neha", "platform"}
        };

        const std::vector<PullRequest> pullRequests = {
            {
                9001,
                100,
                501,
                "Improve risk calculation",
                "open"
            },
            {
                9002,
                200,
                503,
                "Add asset reconciliation",
                "open"
            },
            {
                9003,
                300,
                502,
                "Harden authentication flow",
                "open"
            },
            {
                9004,
                100,
                999,
                "Unknown author change",
                "open"
            }
        };

        const auto records = buildGovernanceDataset(
            repositories,
            pullRequests,
            developers
        );

        printGovernanceRecords(records);

        std::cout
            << "\nThe fourth pull request is excluded because its author_id "
            << "has no matching Developer row.\n";

        demonstrateDuplicateMatches();
        demonstrateCompositeCondition();

        const std::vector<BranchPolicy> policies = {
            {100, "main", 2, true, false},
            {200, "main", 1, true, false},
            {300, "main", 2, true, false}
        };

        const std::vector<StatusCheck> checks = {
            {9001, "unit-tests", true},
            {9001, "security-scan", true},

            {9002, "unit-tests", true},
            {9002, "security-scan", true},

            {9003, "unit-tests", true},
            {9003, "security-scan", false}
        };

        const std::vector<Review> reviews = {
            {9001, 502, "APPROVED", false},
            {9001, 503, "APPROVED", false},

            {9002, 501, "APPROVED", false},

            {9003, 501, "APPROVED", false},
            {9003, 503, "APPROVED", false}
        };

        const std::unordered_set<int> eligibleReviewers = {
            501,
            502,
            503
        };

        /*
         * The merge engine does not confuse relationship matching with policy
         * evaluation:
         *
         * INNER JOIN answers "which records belong together?"
         * Governance checks answer "does the resulting PR satisfy policy?"
         */
        const std::vector<std::pair<const PullRequest*, std::string>> evaluations = {
            {&pullRequests[0], "main"},
            {&pullRequests[1], "main"},
            {&pullRequests[2], "main"},
            {&pullRequests[3], "main"}
        };

        std::cout << "\n=== Merge eligibility evaluation ===\n";

        for (const auto& [pullRequest, targetBranch] : evaluations) {
            const auto decision = evaluateMergeEligibility(
                *pullRequest,
                repositories,
                developers,
                policies,
                checks,
                reviews,
                eligibleReviewers,
                targetBranch
            );

            printDecision(decision);
        }

        /*
         * PR 9001:
         * repository exists, author exists, branch policy exists, all checks
         * pass, and two distinct eligible reviewers approved it.
         */
        const auto decision9001 = evaluateMergeEligibility(
            pullRequests[0],
            repositories,
            developers,
            policies,
            checks,
            reviews,
            eligibleReviewers,
            "main"
        );

        assert(decision9001.mergeable);

        /*
         * PR 9003 fails because a required status check is false even though
         * two approvals exist. A join relationship does not itself make a
         * record valid for every downstream business rule.
         */
        const auto decision9003 = evaluateMergeEligibility(
            pullRequests[2],
            repositories,
            developers,
            policies,
            checks,
            reviews,
            eligibleReviewers,
            "main"
        );

        assert(!decision9003.mergeable);
        assert(!decision9003.requiredChecksPassed);

        /*
         * PR 9004 fails at relationship resolution because its author cannot
         * be matched. This is an INNER JOIN-style referential requirement.
         */
        const auto decision9004 = evaluateMergeEligibility(
            pullRequests[3],
            repositories,
            developers,
            policies,
            checks,
            reviews,
            eligibleReviewers,
            "main"
        );

        assert(!decision9004.authorMatched);
        assert(!decision9004.mergeable);

        runAssertions(records);

        std::cout
            << "\nPerformance characteristics:\n"
            << "  Equality join with an unordered_multimap index: "
            << "approximately O(L + R + M), where M is output size.\n"
            << "  General nested-loop join: O(L * R) predicate evaluations.\n"
            << "  Composite predicates may require nested-loop evaluation unless "
            << "their searchable components can be indexed.\n"
            << "  Duplicate keys increase output cardinality and can dominate "
            << "the cost of result construction.\n";

        std::cout
            << "\nCase-study design rule:\n"
            << "Use the INNER JOIN relationship to establish valid related "
            << "records, then evaluate independent governance constraints "
            << "such as checks and approvals. Combining these concepts into "
            << "one condition makes failures harder to diagnose.\n";

        return 0;
    }
    catch (const std::exception& exception) {
        std::cerr << "Fatal error: " << exception.what() << '\n';
        return 1;
    }
}
