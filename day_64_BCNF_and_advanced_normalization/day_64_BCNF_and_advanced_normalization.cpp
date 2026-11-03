#include <algorithm>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

enum class PullRequestState {
    Draft,
    Open,
    Closed,
    Merged
};

enum class ReviewState {
    Commented,
    ChangesRequested,
    Approved,
    Dismissed
};

enum class MergeStrategy {
    MergeCommit,
    Squash,
    Rebase
};

struct Commit {
    std::string sha;
    std::string message;
    std::string author;
};

struct Review {
    std::string reviewer;
    ReviewState state;
    std::string commitSha;
    std::vector<std::string> comments;
};

struct StatusCheck {
    std::string name;
    bool passed;
    bool required;
    std::string commitSha;
};

struct BranchProtection {
    int requiredReviews{1};
    std::set<std::string> requiredStatusChecks;
    bool restrictDirectPush{true};
    bool restrictForcePush{true};
    bool restrictDeletion{true};
    bool requireConversationsResolved{true};
    bool requireLinearHistory{false};
};

struct Branch {
    std::string name;
    bool protectedBranch{false};
    std::vector<Commit> commits;
};

struct PullRequest {
    int number;
    std::string sourceBranch;
    std::string targetBranch;
    std::string author;
    std::vector<Commit> commits;
    PullRequestState state{PullRequestState::Open};
    bool draft{false};
    std::vector<Review> reviews;
    std::vector<StatusCheck> checks;
    int unresolvedConversations{0};
    MergeStrategy strategy{MergeStrategy::Squash};
    bool baseSyncRequired{false};

    const std::string& headSha() const {
        if (commits.empty()) {
            throw std::runtime_error("Pull Request has no commits");
        }
        return commits.back().sha;
    }
};

class GovernanceError : public std::runtime_error {
public:
    explicit GovernanceError(const std::string& message)
        : std::runtime_error(message) {}
};

class Repository {
private:
    std::string name_;
    std::map<std::string, Branch> branches_;
    std::set<std::string> eligibleReviewers_;
    std::map<std::string, BranchProtection> protections_;
    std::map<int, PullRequest> pullRequests_;
    int nextPrNumber_{1};

public:
    explicit Repository(std::string name)
        : name_(std::move(name)) {}

    void addBranch(Branch branch) {
        if (branches_.contains(branch.name)) {
            throw GovernanceError("Duplicate branch: " + branch.name);
        }
        branches_.emplace(branch.name, std::move(branch));
    }

    void addReviewer(const std::string& reviewer) {
        eligibleReviewers_.insert(reviewer);
    }

    void protectBranch(
        const std::string& branch,
        BranchProtection protection
    ) {
        if (!branches_.contains(branch)) {
            throw GovernanceError("Unknown branch: " + branch);
        }

        branches_.at(branch).protectedBranch = true;
        protections_[branch] = std::move(protection);
    }

    PullRequest& createPullRequest(
        const std::string& source,
        const std::string& target,
        const std::string& author,
        std::vector<Commit> commits,
        bool draft = false
    ) {
        if (!branches_.contains(source) || !branches_.contains(target)) {
            throw GovernanceError("Source or target branch does not exist");
        }

        if (source == target) {
            throw GovernanceError("Source and target must differ");
        }

        if (commits.empty()) {
            throw GovernanceError("Pull Request requires changes");
        }

        int number = nextPrNumber_++;

        PullRequest pr{
            number,
            source,
            target,
            author,
            std::move(commits)
        };

        pr.draft = draft;

        auto [it, inserted] =
            pullRequests_.emplace(number, std::move(pr));

        if (!inserted) {
            throw GovernanceError("Unable to create Pull Request");
        }

        return it->second;
    }

    void requestReview(int number, const std::string& reviewer) {
        PullRequest& pr = getPr(number);

        if (pr.state != PullRequestState::Open) {
            throw GovernanceError("Pull Request is not open");
        }

        if (reviewer == pr.author) {
            throw GovernanceError("Author cannot review own Pull Request");
        }

        if (!eligibleReviewers_.contains(reviewer)) {
            throw GovernanceError("Reviewer is not eligible");
        }
    }

    void submitReview(
        int number,
        const std::string& reviewer,
        ReviewState state,
        std::vector<std::string> comments = {}
    ) {
        PullRequest& pr = getPr(number);

        if (!eligibleReviewers_.contains(reviewer)) {
            throw GovernanceError("Reviewer is not eligible");
        }

        if (reviewer == pr.author) {
            throw GovernanceError("Author cannot approve own Pull Request");
        }

        if (
            state == ReviewState::ChangesRequested &&
            comments.empty()
        ) {
            throw GovernanceError(
                "Changes-requested review needs a comment"
            );
        }

        pr.reviews.push_back({
            reviewer,
            state,
            pr.headSha(),
            std::move(comments)
        });
    }

    void addStatusCheck(
        int number,
        const std::string& name,
        bool passed,
        bool required = true
    ) {
        PullRequest& pr = getPr(number);

        pr.checks.push_back({
            name,
            passed,
            required,
            pr.headSha()
        });
    }

    void addConversation(int number) {
        getPr(number).unresolvedConversations++;
    }

    void resolveConversation(int number) {
        PullRequest& pr = getPr(number);

        if (pr.unresolvedConversations == 0) {
            throw GovernanceError("No conversation to resolve");
        }

        --pr.unresolvedConversations;
    }

    std::pair<bool, std::vector<std::string>>
    mergeEligibility(int number) const {
        const PullRequest& pr = getPrConst(number);

        BranchProtection defaultPolicy;
        const auto policyIt = protections_.find(pr.targetBranch);

        const BranchProtection& policy =
            policyIt == protections_.end()
                ? defaultPolicy
                : policyIt->second;

        std::vector<std::string> failures;

        if (pr.state != PullRequestState::Open) {
            failures.push_back("Pull Request is not open");
        }

        if (pr.draft) {
            failures.push_back("Pull Request is a draft");
        }

        if (pr.baseSyncRequired) {
            failures.push_back("Base synchronization required");
        }

        std::set<std::string> approvals;

        for (const Review& review : pr.reviews) {
            if (
                review.state == ReviewState::Approved &&
                review.commitSha == pr.headSha() &&
                review.reviewer != pr.author
            ) {
                approvals.insert(review.reviewer);
            }
        }

        if (
            static_cast<int>(approvals.size()) <
            policy.requiredReviews
        ) {
            failures.push_back(
                "Insufficient current approvals"
            );
        }

        for (const auto& required : policy.requiredStatusChecks) {
            bool found = false;
            bool passed = false;

            for (const auto& check : pr.checks) {
                if (
                    check.name == required &&
                    check.commitSha == pr.headSha()
                ) {
                    found = true;
                    passed = check.passed;
                }
            }

            if (!found) {
                failures.push_back(
                    "Missing status check: " + required
                );
            } else if (!passed) {
                failures.push_back(
                    "Failed status check: " + required
                );
            }
        }

        if (
            policy.requireConversationsResolved &&
            pr.unresolvedConversations > 0
        ) {
            failures.push_back(
                "Unresolved conversations remain"
            );
        }

        if (
            policy.requireLinearHistory &&
            pr.strategy == MergeStrategy::MergeCommit
        ) {
            failures.push_back(
                "Merge commits violate linear-history policy"
            );
        }

        return {failures.empty(), failures};
    }

    void merge(int number) {
        PullRequest& pr = getPr(number);

        const auto [eligible, failures] =
            mergeEligibility(number);

        if (!eligible) {
            std::string message = "Merge blocked:";
            for (const auto& failure : failures) {
                message += " " + failure + ";";
            }
            throw GovernanceError(message);
        }

        Branch& target = branches_.at(pr.targetBranch);

        if (pr.strategy == MergeStrategy::Squash) {
            target.commits.push_back({
                "squash-" + std::to_string(pr.number),
                "Squash Pull Request #" +
                    std::to_string(pr.number),
                pr.author
            });
        } else if (pr.strategy == MergeStrategy::Rebase) {
            target.commits.insert(
                target.commits.end(),
                pr.commits.begin(),
                pr.commits.end()
            );
        } else {
            target.commits.push_back({
                "merge-" + std::to_string(pr.number),
                "Merge Pull Request #" +
                    std::to_string(pr.number),
                pr.author
            });
        }

        pr.state = PullRequestState::Merged;
    }

private:
    PullRequest& getPr(int number) {
        auto it = pullRequests_.find(number);

        if (it == pullRequests_.end()) {
            throw GovernanceError(
                "Pull Request does not exist"
            );
        }

        return it->second;
    }

    const PullRequest& getPrConst(int number) const {
        auto it = pullRequests_.find(number);

        if (it == pullRequests_.end()) {
            throw GovernanceError(
                "Pull Request does not exist"
            );
        }

        return it->second;
    }
};

int main() {
    try {
        Repository repository("payments-platform");

        repository.addBranch({
            "main",
            true,
            {
                {"a1", "Initial release", "alice"},
                {"b2", "Payment API", "alice"}
            }
        });

        repository.addBranch({
            "feature/fraud",
            false,
            {}
        });

        repository.addReviewer("bob");
        repository.addReviewer("carol");
        repository.addReviewer("diana");

        BranchProtection protection;
        protection.requiredReviews = 2;
        protection.requiredStatusChecks = {
            "unit-tests",
            "security-scan"
        };
        protection.requireConversationsResolved = true;
        protection.requireLinearHistory = true;

        repository.protectBranch("main", protection);

        PullRequest& pr = repository.createPullRequest(
            "feature/fraud",
            "main",
            "alice",
            {
                {"c1", "Add fraud rules", "alice"},
                {"c2", "Validate thresholds", "alice"}
            }
        );

        repository.requestReview(pr.number, "bob");
        repository.requestReview(pr.number, "carol");

        repository.submitReview(
            pr.number,
            "bob",
            ReviewState::Approved
        );

        repository.submitReview(
            pr.number,
            "carol",
            ReviewState::ChangesRequested,
            {"Reject duplicate threshold definitions"}
        );

        repository.addConversation(pr.number);
        repository.addStatusCheck(
            pr.number,
            "unit-tests",
            true
        );
        repository.addStatusCheck(
            pr.number,
            "security-scan",
            true
        );

        auto first = repository.mergeEligibility(pr.number);

        std::cout
            << "First merge eligibility: "
            << (first.first ? "allowed" : "blocked")
            << '\n';

        for (const auto& failure : first.second) {
            std::cout << " - " << failure << '\n';
        }

        repository.resolveConversation(pr.number);

        repository.submitReview(
            pr.number,
            "carol",
            ReviewState::Approved
        );

        auto second = repository.mergeEligibility(pr.number);

        std::cout
            << "\nSecond merge eligibility: "
            << (second.first ? "allowed" : "blocked")
            << '\n';

        repository.merge(pr.number);

        std::cout << "Pull Request merged successfully.\n";

        try {
            repository.merge(pr.number);
        } catch (const GovernanceError& error) {
            std::cout
                << "Expected failure: "
                << error.what()
                << '\n';
        }

    } catch (const std::exception& error) {
        std::cerr
            << "Fatal error: "
            << error.what()
            << '\n';
        return 1;
    }

    return 0;
}
