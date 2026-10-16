#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

struct PullRequest {
    int id;
    std::string author;
    std::string targetBranch;
    int additions;
    int deletions;
    bool checksPassed;
};

struct Review {
    int pullRequestId;
    std::string reviewer;
    bool approved;
    std::string comment;
};

struct BranchPolicy {
    std::string branch;
    int requiredApprovals;
    bool requireChecks;
    bool restrictDirectPush;
};

class GovernanceEngine {
private:
    std::vector<PullRequest> pullRequests;
    std::vector<Review> reviews;
    std::unordered_map<std::string, BranchPolicy> policies;

public:
    void addPolicy(BranchPolicy policy) {
        if (policy.branch.empty()) {
            throw std::invalid_argument("Protected branch name cannot be empty.");
        }
        if (policy.requiredApprovals < 0) {
            throw std::invalid_argument("Required approvals cannot be negative.");
        }

        policies[policy.branch] = std::move(policy);
    }

    void addPullRequest(PullRequest request) {
        if (request.id <= 0) {
            throw std::invalid_argument("Pull request id must be positive.");
        }
        if (request.targetBranch.empty()) {
            throw std::invalid_argument("Target branch cannot be empty.");
        }
        if (request.additions < 0 || request.deletions < 0) {
            throw std::invalid_argument("Change counts cannot be negative.");
        }

        pullRequests.push_back(std::move(request));
    }

    void addReview(Review review) {
        if (review.reviewer.empty()) {
            throw std::invalid_argument("Reviewer identity is required.");
        }

        const auto pr = std::find_if(
            pullRequests.begin(),
            pullRequests.end(),
            [&](const PullRequest& item) {
                return item.id == review.pullRequestId;
            }
        );

        if (pr == pullRequests.end()) {
            throw std::invalid_argument("Review references an unknown pull request.");
        }

        reviews.push_back(std::move(review));
    }

    std::vector<Review> approvedReviews(int pullRequestId) const {
        std::vector<Review> result;

        for (const auto& review : reviews) {
            if (review.pullRequestId == pullRequestId && review.approved) {
                result.push_back(review);
            }
        }

        return result;
    }

    bool mergeEligible(const PullRequest& request) const {
        auto policyIt = policies.find(request.targetBranch);

        if (policyIt == policies.end()) {
            // An unprotected branch does not receive this policy's approval
            // requirements, though repository governance may impose others.
            return true;
        }

        const BranchPolicy& policy = policyIt->second;

        if (policy.requireChecks && !request.checksPassed) {
            return false;
        }

        const auto approvals = approvedReviews(request.id);

        // A distinct reviewer should represent a distinct approval. Counting
        // repeated approvals from the same reviewer would weaken the policy.
        std::map<std::string, bool> uniqueApprovers;

        for (const auto& review : approvals) {
            uniqueApprovers[review.reviewer] = true;
        }

        return static_cast<int>(uniqueApprovers.size()) >= policy.requiredApprovals;
    }

    void printDecision(const PullRequest& request) const {
        std::cout << "PR #" << request.id
                  << " -> " << request.targetBranch << '\n';

        std::cout << "  Changes: +" << request.additions
                  << " -" << request.deletions << '\n';

        std::cout << "  Status checks: "
                  << (request.checksPassed ? "passed" : "failed") << '\n';

        std::cout << "  Decision: "
                  << (mergeEligible(request) ? "merge eligible" : "blocked")
                  << "\n\n";
    }
};

int main() {
    try {
        GovernanceEngine engine;

        engine.addPolicy({
            "main",
            2,
            true,
            true
        });

        engine.addPolicy({
            "release",
            1,
            true,
            true
        });

        engine.addPullRequest({
            501,
            "developer-a",
            "main",
            185,
            42,
            true
        });

        engine.addPullRequest({
            502,
            "developer-b",
            "main",
            91,
            11,
            false
        });

        engine.addPullRequest({
            503,
            "developer-c",
            "release",
            20,
            4,
            true
        });

        engine.addReview({
            501,
            "reviewer-x",
            true,
            "Architecture and tests look acceptable."
        });

        engine.addReview({
            501,
            "reviewer-y",
            true,
            "Reviewed database changes."
        });

        engine.addReview({
            502,
            "reviewer-x",
            true,
            "Code looks reasonable."
        });

        engine.addReview({
            503,
            "release-manager",
            true,
            "Release-specific review completed."
        });

        std::cout << std::boolalpha;

        /*
         * The case study represents the evaluation layer that a repository
         * service might run after a pull request is updated. The engine does
         * not perform Git operations; it evaluates repository governance
         * state and makes the merge decision explicit.
         */
        std::cout << "Repository Governance Engine\n";
        std::cout << "============================\n\n";

        const std::vector<int> requestedIds = {501, 502, 503};

        for (int id : requestedIds) {
            // Locate the request through the stored repository state.
            for (const auto& request : std::vector<PullRequest>{
                     {501, "developer-a", "main", 185, 42, true},
                     {502, "developer-b", "main", 91, 11, false},
                     {503, "developer-c", "release", 20, 4, true}}) {
                if (request.id == id) {
                    engine.printDecision(request);
                }
            }
        }

        std::cout << "Governance characteristics\n";
        std::cout << "---------------------------\n";
        std::cout << "Protected branches convert repository policy into "
                     "machine-checkable merge conditions.\n";
        std::cout << "Approval counts use distinct reviewer identities.\n";
        std::cout << "Status checks are evaluated independently from approvals.\n";
        std::cout << "A failed check can block an otherwise approved request.\n";

    } catch (const std::exception& error) {
        std::cerr << "Governance error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
