#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

/*
    Repository Governance Data Quality Case Study

    This system models a repository governance report where pull requests,
    reviews, approvals, and protected-branch policies are combined.

    The important JOIN lesson is that a technically valid relationship can
    still produce an incorrect report if the query combines entities at
    incompatible grains.

    Example:
      Pull Request -> Review is one-to-many.
      Pull Request -> Status Check is one-to-many.
      Pull Request -> Reviewer is many-to-many through Review.

    Joining all three child collections directly can multiply rows.
    The program therefore provides both a deliberately naive report and a
    controlled report that aggregates child facts before joining them to the
    pull-request grain.
*/

enum class ReviewState {
    Commented,
    ChangesRequested,
    Approved,
    Dismissed
};

enum class CheckState {
    Pending,
    Passed,
    Failed
};

struct PullRequest {
    int id;
    string repository;
    string sourceBranch;
    string targetBranch;
    string author;
    string headCommit;
    bool draft;
    bool open;
};

struct Review {
    int id;
    int pullRequestId;
    string reviewer;
    ReviewState state;
};

struct StatusCheck {
    int id;
    int pullRequestId;
    string name;
    CheckState state;
};

struct BranchPolicy {
    string repository;
    string branch;
    int requiredApprovals;
    bool requireStatusChecks;
    bool restrictDirectPush;
    bool restrictForcePush;
    bool requireLinearHistory;
};

struct ApprovalSummary {
    int approvals = 0;
    int changeRequests = 0;
};

struct CheckSummary {
    int requiredChecks = 0;
    int passedChecks = 0;
    int failedChecks = 0;
    int pendingChecks = 0;
};

string reviewStateName(ReviewState state) {
    switch (state) {
        case ReviewState::Commented:
            return "COMMENTED";
        case ReviewState::ChangesRequested:
            return "CHANGES_REQUESTED";
        case ReviewState::Approved:
            return "APPROVED";
        case ReviewState::Dismissed:
            return "DISMISSED";
    }

    return "UNKNOWN";
}

string checkStateName(CheckState state) {
    switch (state) {
        case CheckState::Pending:
            return "PENDING";
        case CheckState::Passed:
            return "PASSED";
        case CheckState::Failed:
            return "FAILED";
    }

    return "UNKNOWN";
}

class GovernanceEngine {
private:
    vector<PullRequest> pullRequests;
    vector<Review> reviews;
    vector<StatusCheck> checks;
    vector<BranchPolicy> policies;

    const BranchPolicy* findPolicy(
        const string& repository,
        const string& branch
    ) const {
        for (const auto& policy : policies) {
            if (policy.repository == repository &&
                policy.branch == branch) {
                return &policy;
            }
        }

        return nullptr;
    }

    ApprovalSummary summarizeApprovals(int pullRequestId) const {
        ApprovalSummary summary;

        for (const auto& review : reviews) {
            if (review.pullRequestId != pullRequestId) {
                continue;
            }

            // Dismissed reviews are historical records, not active approvals.
            if (review.state == ReviewState::Approved) {
                ++summary.approvals;
            } else if (review.state == ReviewState::ChangesRequested) {
                ++summary.changeRequests;
            }
        }

        return summary;
    }

    CheckSummary summarizeChecks(int pullRequestId) const {
        CheckSummary summary;

        for (const auto& check : checks) {
            if (check.pullRequestId != pullRequestId) {
                continue;
            }

            ++summary.requiredChecks;

            if (check.state == CheckState::Passed) {
                ++summary.passedChecks;
            } else if (check.state == CheckState::Failed) {
                ++summary.failedChecks;
            } else {
                ++summary.pendingChecks;
            }
        }

        return summary;
    }

public:
    void loadData() {
        pullRequests = {
            {101, "payments-api", "feature/refund", "main",
             "atul", "a1b2c3", false, true},

            {102, "payments-api", "feature/ledger", "main",
             "ravi", "d4e5f6", false, true},

            {103, "payments-api", "feature/observability", "main",
             "meera", "g7h8i9", true, true}
        };

        reviews = {
            {1, 101, "reviewer-a", ReviewState::Approved},
            {2, 101, "reviewer-b", ReviewState::Commented},
            {3, 102, "reviewer-a", ReviewState::Approved},
            {4, 102, "reviewer-b", ReviewState::ChangesRequested},
            {5, 103, "reviewer-c", ReviewState::Approved}
        };

        checks = {
            {1, 101, "unit-tests", CheckState::Passed},
            {2, 101, "security-scan", CheckState::Passed},
            {3, 101, "integration-tests", CheckState::Passed},

            {4, 102, "unit-tests", CheckState::Passed},
            {5, 102, "security-scan", CheckState::Failed},

            {6, 103, "unit-tests", CheckState::Pending},
            {7, 103, "security-scan", CheckState::Passed}
        };

        policies = {
            {"payments-api", "main",
             1, true, true, true, true}
        };
    }

    void demonstrateNaiveJoinExplosion() const {
        cout << "\n=== Naive Pull Request / Review / Check Join ===\n";

        /*
            PR 101 has two reviews and three checks.
            A direct three-way child join creates 2 * 3 = 6 rows for PR 101.

            Neither the reviews nor the checks are wrong. The report is wrong
            if its intended grain is one row per pull request.
        */
        int rowsForPr101 = 0;

        for (const auto& review : reviews) {
            if (review.pullRequestId != 101) {
                continue;
            }

            for (const auto& check : checks) {
                if (check.pullRequestId != 101) {
                    continue;
                }

                ++rowsForPr101;
                cout << "PR 101 | review=" << review.id
                     << " | check=" << check.name << '\n';
            }
        }

        cout << "Rows generated for PR 101: " << rowsForPr101 << '\n';
        cout << "Expected PR-level rows: 1\n";
        cout << "Cause: independent one-to-many relationships were joined "
                "without reducing them to PR grain.\n";
    }

    void demonstrateControlledReport() const {
        cout << "\n=== Controlled Pull Request Governance Report ===\n";

        for (const auto& pr : pullRequests) {
            const auto* policy = findPolicy(pr.repository, pr.targetBranch);

            if (!policy) {
                throw runtime_error(
                    "No branch policy exists for protected target branch."
                );
            }

            ApprovalSummary approvals = summarizeApprovals(pr.id);
            CheckSummary checksSummary = summarizeChecks(pr.id);

            bool approvalSatisfied =
                approvals.approvals >= policy->requiredApprovals &&
                approvals.changeRequests == 0;

            bool checksSatisfied =
                !policy->requireStatusChecks ||
                (checksSummary.requiredChecks > 0 &&
                 checksSummary.failedChecks == 0 &&
                 checksSummary.pendingChecks == 0);

            bool mergeable =
                pr.open &&
                !pr.draft &&
                approvalSatisfied &&
                checksSatisfied;

            cout << left
                 << setw(5) << pr.id
                 << setw(24) << pr.sourceBranch
                 << " approvals=" << approvals.approvals
                 << " changes_requested=" << approvals.changeRequests
                 << " checks_passed=" << checksSummary.passedChecks
                 << " checks_failed=" << checksSummary.failedChecks
                 << " checks_pending=" << checksSummary.pendingChecks
                 << " mergeable=" << boolalpha << mergeable
                 << '\n';
        }
    }

    void demonstrateWrongPredicate() const {
        cout << "\n=== Incorrect Join Predicate ===\n";

        /*
            Joining reviews and checks only through repository identity would
            associate a review for one PR with checks belonging to another PR.

            The correct relationship is:
                review.pullRequestId == check.pullRequestId

            Repository name alone is not sufficient because many pull
            requests belong to the same repository.
        */

        int incorrectMatches = 0;
        int correctMatches = 0;

        for (const auto& review : reviews) {
            for (const auto& check : checks) {
                if (review.pullRequestId == check.pullRequestId) {
                    ++correctMatches;
                }

                // All records belong to the same repository in this dataset,
                // so a repository-only join would match unrelated PRs.
                ++incorrectMatches;
            }
        }

        cout << "Correct review/check pairings: "
             << correctMatches << '\n';

        cout << "Repository-only pairings: "
             << incorrectMatches << '\n';

        cout << "The larger value is not additional information. It is "
                "evidence that the join predicate is too broad.\n";
    }

    void demonstrateCardinalityChecks() const {
        cout << "\n=== Cardinality Assertions ===\n";

        unordered_map<int, int> reviewCounts;
        unordered_map<int, int> checkCounts;

        for (const auto& review : reviews) {
            ++reviewCounts[review.pullRequestId];
        }

        for (const auto& check : checks) {
            ++checkCounts[check.pullRequestId];
        }

        for (const auto& pr : pullRequests) {
            cout << "PR " << pr.id
                 << " has " << reviewCounts[pr.id] << " review rows and "
                 << checkCounts[pr.id] << " check rows.\n";
        }

        cout << "These counts must be known before interpreting a joined "
                "result as a PR-level report.\n";
    }

    void demonstrateNullLikeRelationship() const {
        cout << "\n=== Missing Relationship / NULL-like State ===\n";

        optional<string> missingReviewer;
        optional<string> actualReviewer = string("reviewer-a");

        cout << "Missing reviewer has value: "
             << boolalpha << missingReviewer.has_value() << '\n';

        cout << "Actual reviewer has value: "
             << actualReviewer.has_value() << '\n';

        /*
            SQL NULL is not ordinary equality data. An application should
            preserve that distinction rather than converting missing values
            to an arbitrary string such as "UNKNOWN", which can accidentally
            make unrelated records join together.
        */
        cout << "A missing relationship should remain distinguishable from "
                "a real reviewer identity.\n";
    }
};

int main() {
    try {
        GovernanceEngine engine;

        engine.loadData();
        engine.demonstrateNaiveJoinExplosion();
        engine.demonstrateControlledReport();
        engine.demonstrateWrongPredicate();
        engine.demonstrateCardinalityChecks();
        engine.demonstrateNullLikeRelationship();

        cout << "\n=== Engineering Principle ===\n";
        cout << "Define the grain of the desired result before combining "
                "one-to-many datasets. Aggregate independent child facts "
                "before joining them to a parent-grain report.\n";
    }
    catch (const exception& error) {
        cerr << "Governance analysis failed: "
             << error.what() << '\n';
        return 1;
    }

    return 0;
}
