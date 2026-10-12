#include <algorithm>
#include <chrono>
#include <functional>
#include <iomanip>
#include <iostream>
#include <optional>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

enum class ReviewState {
    Approved,
    Commented,
    ChangesRequested
};

enum class CheckState {
    Success,
    Failure,
    Pending
};

struct PullRequest {
    int id;
    int number;
    string title;
    string author;
    string sourceBranch;
    string targetBranch;
    bool draft;
};

struct Review {
    int id;
    int pullRequestId;
    string reviewer;
    ReviewState state;
};

struct StatusCheck {
    int pullRequestId;
    string name;
    CheckState state;
};

struct ReviewComment {
    int id;
    int pullRequestId;
    string reviewer;
    bool resolved;
    string body;
};

struct BranchProtection {
    string branch;
    size_t requiredApprovals;
    vector<string> requiredChecks;
    bool requireResolvedConversations;
    bool allowForcePush;
    bool allowDeletion;
    bool requireLinearHistory;
};

struct MergeDecision {
    bool eligible;
    vector<string> reasons;
};


/*
 * This function models a correlated EXISTS operation.
 *
 * SQL shape:
 *
 * SELECT p.*
 * FROM pull_requests p
 * WHERE EXISTS (
 *     SELECT 1
 *     FROM reviews r
 *     WHERE r.pull_request_id = p.id
 *       AND r.state = 'APPROVED'
 * );
 *
 * The review predicate receives the current PullRequest. The reference to
 * pr.id is the equivalent of the SQL outer reference.
 */
vector<PullRequest> approvedPullRequests(
    const vector<PullRequest>& pullRequests,
    const vector<Review>& reviews
) {
    vector<PullRequest> result;

    for (const auto& pr : pullRequests) {
        bool exists = any_of(
            reviews.begin(),
            reviews.end(),
            [&pr](const Review& review) {
                return review.pullRequestId == pr.id &&
                       review.state == ReviewState::Approved;
            }
        );

        if (exists) {
            result.push_back(pr);
        }
    }

    return result;
}


/*
 * NOT EXISTS is useful for finding PRs whose current row has no matching
 * unresolved conversation.
 */
vector<PullRequest> cleanPullRequests(
    const vector<PullRequest>& pullRequests,
    const vector<ReviewComment>& comments
) {
    vector<PullRequest> result;

    for (const auto& pr : pullRequests) {
        bool unresolvedExists = any_of(
            comments.begin(),
            comments.end(),
            [&pr](const ReviewComment& comment) {
                return comment.pullRequestId == pr.id &&
                       !comment.resolved;
            }
        );

        if (!unresolvedExists) {
            result.push_back(pr);
        }
    }

    return result;
}


/*
 * This is a correlated scalar aggregate:
 *
 * SELECT p.number,
 *        (
 *          SELECT COUNT(*)
 *          FROM reviews r
 *          WHERE r.pull_request_id = p.id
 *        ) AS review_count
 * FROM pull_requests p;
 *
 * The inner COUNT is evaluated in the context of each PR.
 */
unordered_map<int, size_t> reviewCounts(
    const vector<PullRequest>& pullRequests,
    const vector<Review>& reviews
) {
    unordered_map<int, size_t> counts;

    for (const auto& pr : pullRequests) {
        size_t count = count_if(
            reviews.begin(),
            reviews.end(),
            [&pr](const Review& review) {
                return review.pullRequestId == pr.id;
            }
        );

        counts[pr.id] = count;
    }

    return counts;
}


/*
 * A production database should not necessarily execute the logical
 * correlated operation as repeated table scans. An index on
 * reviews.pull_request_id can allow indexed lookup, and an optimizer can
 * sometimes transform the correlated query into a join or semi-join.
 *
 * This unordered_map models that index explicitly.
 */
unordered_map<int, vector<const Review*>> buildReviewIndex(
    const vector<Review>& reviews
) {
    unordered_map<int, vector<const Review*>> index;

    for (const auto& review : reviews) {
        index[review.pullRequestId].push_back(&review);
    }

    return index;
}


size_t indexedApprovalCount(
    const PullRequest& pr,
    const unordered_map<int, vector<const Review*>>& reviewIndex
) {
    auto it = reviewIndex.find(pr.id);

    if (it == reviewIndex.end()) {
        return 0;
    }

    return count_if(
        it->second.begin(),
        it->second.end(),
        [](const Review* review) {
            return review->state == ReviewState::Approved;
        }
    );
}


/*
 * The enterprise case study uses several correlated conditions to determine
 * whether a PR may merge into a protected branch.
 *
 * Pull Request mechanics are represented by the PR state itself:
 * source branch, target branch, draft status, and merge eligibility.
 *
 * Code Review is represented by Review and ReviewComment records.
 *
 * Approvals are evaluated separately from comments and are counted only
 * when the review state is Approved and the reviewer is not the author.
 *
 * Branch Protection supplies the repository-level policy.
 */
MergeDecision evaluateMergeEligibility(
    const PullRequest& pr,
    const vector<Review>& reviews,
    const vector<StatusCheck>& checks,
    const vector<ReviewComment>& comments,
    const BranchProtection& policy
) {
    vector<string> reasons;

    if (pr.draft) {
        reasons.push_back("Pull Request is a draft.");
    }

    size_t approvals = 0;

    /*
     * Correlated COUNT:
     * only reviews whose pullRequestId equals the current PR's id belong
     * to this PR's approval calculation.
     */
    for (const auto& review : reviews) {
        if (review.pullRequestId == pr.id &&
            review.state == ReviewState::Approved &&
            review.reviewer != pr.author) {
            ++approvals;
        }
    }

    if (approvals < policy.requiredApprovals) {
        reasons.push_back(
            "Required approvals: " +
            to_string(policy.requiredApprovals) +
            ", available approvals: " +
            to_string(approvals)
        );
    }

    /*
     * Each required status check is itself a correlated EXISTS condition:
     *
     * EXISTS (
     *     SELECT 1
     *     FROM status_checks s
     *     WHERE s.pull_request_id = p.id
     *       AND s.name = required_check
     *       AND s.state = 'SUCCESS'
     * )
     */
    for (const auto& requiredCheck : policy.requiredChecks) {
        bool successful = any_of(
            checks.begin(),
            checks.end(),
            [&pr, &requiredCheck](const StatusCheck& check) {
                return check.pullRequestId == pr.id &&
                       check.name == requiredCheck &&
                       check.state == CheckState::Success;
            }
        );

        if (!successful) {
            reasons.push_back(
                "Required check is not successful: " + requiredCheck
            );
        }
    }

    /*
     * NOT EXISTS is used here:
     *
     * NOT EXISTS (
     *     SELECT 1
     *     FROM review_comments c
     *     WHERE c.pull_request_id = p.id
     *       AND c.resolved = false
     * )
     */
    if (policy.requireResolvedConversations) {
        bool unresolvedExists = any_of(
            comments.begin(),
            comments.end(),
            [&pr](const ReviewComment& comment) {
                return comment.pullRequestId == pr.id &&
                       !comment.resolved;
            }
        );

        if (unresolvedExists) {
            reasons.push_back(
                "At least one review conversation remains unresolved."
            );
        }
    }

    return {
        reasons.empty(),
        reasons
    };
}


/*
 * Nested correlation:
 *
 * Outer PR
 *   -> matching approval
 *      -> reviewer is eligible for this repository
 *
 * A real SQL implementation could express the same relationship through
 * nested EXISTS predicates.
 */
bool hasEligibleApproval(
    const PullRequest& pr,
    const vector<Review>& reviews,
    const unordered_set<string>& eligibleReviewers
) {
    return any_of(
        reviews.begin(),
        reviews.end(),
        [&pr, &eligibleReviewers](const Review& review) {
            return review.pullRequestId == pr.id &&
                   review.state == ReviewState::Approved &&
                   eligibleReviewers.find(review.reviewer) !=
                       eligibleReviewers.end();
        }
    );
}


void printDecision(
    const PullRequest& pr,
    const MergeDecision& decision
) {
    cout << "PR #" << pr.number << ": "
         << (decision.eligible ? "MERGE ELIGIBLE" : "BLOCKED")
         << '\n';

    for (const auto& reason : decision.reasons) {
        cout << "  " << reason << '\n';
    }
}


int main() {
    vector<PullRequest> pullRequests{
        {
            101,
            41,
            "Add transaction reconciliation",
            "david",
            "feature/reconciliation",
            "main",
            false
        },
        {
            102,
            42,
            "Improve payment timeout handling",
            "alice",
            "fix/payment-timeout",
            "main",
            false
        },
        {
            103,
            43,
            "Refactor settlement validation",
            "bob",
            "refactor/settlement",
            "main",
            true
        }
    };

    vector<Review> reviews{
        {1, 101, "alice", ReviewState::Approved},
        {2, 101, "bob", ReviewState::Commented},
        {3, 102, "carol", ReviewState::Approved},
        {4, 103, "alice", ReviewState::ChangesRequested}
    };

    vector<StatusCheck> checks{
        {101, "unit-tests", CheckState::Success},
        {101, "security-scan", CheckState::Success},
        {102, "unit-tests", CheckState::Success},
        {102, "security-scan", CheckState::Failure}
    };

    vector<ReviewComment> comments{
        {
            1,
            101,
            "bob",
            false,
            "Document the reconciliation fallback."
        },
        {
            2,
            102,
            "carol",
            true,
            "Timeout handling looks correct."
        }
    };

    BranchProtection mainProtection{
        "main",
        1,
        {"unit-tests", "security-scan"},
        true,
        false,
        false,
        true
    };

    cout << "Repository Governance Engine\n";
    cout << "Correlated subquery case study\n\n";

    cout << "=== Correlated EXISTS ===\n";

    for (const auto& pr : approvedPullRequests(pullRequests, reviews)) {
        cout << "PR #" << pr.number << ": " << pr.title << '\n';
    }

    cout << "\n=== Correlated NOT EXISTS ===\n";

    for (const auto& pr : cleanPullRequests(pullRequests, comments)) {
        cout << "PR #" << pr.number
             << ": no unresolved review conversation\n";
    }

    cout << "\n=== Correlated COUNT ===\n";

    auto counts = reviewCounts(pullRequests, reviews);

    for (const auto& pr : pullRequests) {
        cout << "PR #" << pr.number
             << ": " << counts[pr.id]
             << " review(s)\n";
    }

    cout << "\n=== Indexed correlated lookup ===\n";

    auto reviewIndex = buildReviewIndex(reviews);

    for (const auto& pr : pullRequests) {
        cout << "PR #" << pr.number
             << ": " << indexedApprovalCount(pr, reviewIndex)
             << " approval(s)\n";
    }

    cout << "\n=== Merge eligibility ===\n";

    for (const auto& pr : pullRequests) {
        auto decision = evaluateMergeEligibility(
            pr,
            reviews,
            checks,
            comments,
            mainProtection
        );

        printDecision(pr, decision);
    }

    cout << "\n=== Reviewer eligibility through nested correlation ===\n";

    unordered_set<string> eligibleReviewers{
        "alice",
        "carol"
    };

    for (const auto& pr : pullRequests) {
        cout << "PR #" << pr.number << ": "
             << (
                    hasEligibleApproval(
                        pr,
                        reviews,
                        eligibleReviewers
                    )
                        ? "eligible approval found"
                        : "no eligible approval"
                )
             << '\n';
    }

    cout << "\n=== Complexity note ===\n";
    cout << "A naive correlated scan over N PRs and M reviews can "
            "perform O(N*M) comparisons.\n";
    cout << "An index keyed by pull_request_id reduces repeated searches "
            "and models the role of a database index.\n";
    cout << "A SQL optimizer may also decorrelate a logically correlated "
            "subquery into a join, semi-join, or another equivalent plan.\n";

    return 0;
}
