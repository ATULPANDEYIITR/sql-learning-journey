#include <algorithm>
#include <chrono>
#include <cstddef>
#include <functional>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

/*
 * Repository governance engine using C++17.
 *
 * Case study:
 * A deployment platform must determine whether a pull request can be merged.
 * The engine evaluates active reviewers, distinct current approvals,
 * required checks, branch protection, unresolved review discussions,
 * and merge-state transitions.
 *
 * Semi-join and anti-join helpers are expressed using existence predicates.
 * The example is an in-memory policy model, not a replacement for the
 * atomic checks performed by a hosting provider.
 */

enum class PullRequestState {
    Open,
    Draft,
    Merged,
    Closed
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

enum class Permission {
    Read,
    Write,
    Maintain,
    Admin
};

std::string toString(PullRequestState state) {
    switch (state) {
        case PullRequestState::Open: return "open";
        case PullRequestState::Draft: return "draft";
        case PullRequestState::Merged: return "merged";
        case PullRequestState::Closed: return "closed";
    }
    throw std::logic_error("Unknown pull-request state");
}

std::string toString(CheckState state) {
    switch (state) {
        case CheckState::Success: return "success";
        case CheckState::Failure: return "failure";
        case CheckState::Pending: return "pending";
    }
    throw std::logic_error("Unknown status-check state");
}

struct Developer {
    int id;
    std::string name;
    bool active;
};

struct Repository {
    int id;
    std::string name;
    bool protectedBranch;
    int requiredApprovals;
    bool requireLinearHistory;
    bool restrictDirectPushes;
    bool restrictForcePushes;
    bool restrictDeletion;
    bool dismissStaleApprovals;
    bool requireResolvedConversations;
    bool allowAdministratorBypass;
};

struct PullRequest {
    int id;
    int repositoryId;
    int authorId;
    std::string title;
    PullRequestState state;
    int baseVersion;
    bool linearHistory;
    bool conversationsResolved;
};

struct Review {
    int pullRequestId;
    int reviewerId;
    ReviewState state;
    int reviewedBaseVersion;
    bool discussionResolved;
};

struct StatusCheck {
    int pullRequestId;
    std::string name;
    CheckState state;
};

struct Eligibility {
    bool eligible = false;
    std::vector<std::string> reasons;
    int validApprovalCount = 0;
};

template <typename Outer, typename Inner, typename Predicate>
std::vector<Outer> semiJoin(
    const std::vector<Outer>& outer,
    const std::vector<Inner>& inner,
    Predicate matches
) {
    std::vector<Outer> result;
    result.reserve(outer.size());

    for (const auto& outerRow : outer) {
        const bool found = std::any_of(
            inner.begin(),
            inner.end(),
            [&](const Inner& innerRow) {
                return matches(outerRow, innerRow);
            }
        );

        if (found) {
            result.push_back(outerRow);
        }
    }

    return result;
}

template <typename Outer, typename Inner, typename Predicate>
std::vector<Outer> antiJoin(
    const std::vector<Outer>& outer,
    const std::vector<Inner>& inner,
    Predicate matches
) {
    std::vector<Outer> result;
    result.reserve(outer.size());

    for (const auto& outerRow : outer) {
        const bool found = std::any_of(
            inner.begin(),
            inner.end(),
            [&](const Inner& innerRow) {
                return matches(outerRow, innerRow);
            }
        );

        if (!found) {
            result.push_back(outerRow);
        }
    }

    return result;
}

class RepositoryGovernance {
private:
    std::unordered_map<int, Developer> developers_;
    std::unordered_map<int, Repository> repositories_;
    std::unordered_map<int, PullRequest> pullRequests_;
    std::vector<Review> reviews_;
    std::vector<StatusCheck> checks_;
    std::unordered_map<int, std::unordered_set<int>> writers_;
    std::unordered_map<int, std::unordered_set<int>> maintainers_;
    std::unordered_map<int, std::unordered_set<int>> administrators_;
    std::unordered_map<int, std::unordered_set<std::string>> requiredChecks_;
    std::unordered_set<int> bypassedPullRequests_;

public:
    void addDeveloper(Developer developer) {
        if (developer.id <= 0 || developer.name.empty()) {
            throw std::invalid_argument("Invalid developer identity");
        }
        if (!developers_.emplace(developer.id, std::move(developer)).second) {
            throw std::invalid_argument("Duplicate developer ID");
        }
    }

    void addRepository(Repository repository) {
        if (repository.id <= 0 || repository.name.empty()) {
            throw std::invalid_argument("Invalid repository");
        }
        if (repository.requiredApprovals < 0) {
            throw std::invalid_argument("Approval threshold cannot be negative");
        }
        if (!repositories_.emplace(repository.id, repository).second) {
            throw std::invalid_argument("Duplicate repository ID");
        }
    }

    void addPullRequest(PullRequest request) {
        if (repositories_.find(request.repositoryId) == repositories_.end()) {
            throw std::invalid_argument("Pull request references unknown repository");
        }
        if (developers_.find(request.authorId) == developers_.end()) {
            throw std::invalid_argument("Pull request references unknown author");
        }
        if (request.id <= 0 || request.baseVersion < 0) {
            throw std::invalid_argument("Invalid pull-request identifier or base version");
        }
        if (!pullRequests_.emplace(request.id, std::move(request)).second) {
            throw std::invalid_argument("Duplicate pull-request ID");
        }
    }

    void addReview(Review review) {
        if (pullRequests_.find(review.pullRequestId) == pullRequests_.end()) {
            throw std::invalid_argument("Review references unknown pull request");
        }
        if (developers_.find(review.reviewerId) == developers_.end()) {
            throw std::invalid_argument("Review references unknown reviewer");
        }
        if (review.reviewedBaseVersion < 0) {
            throw std::invalid_argument("Invalid reviewed base version");
        }
        reviews_.push_back(std::move(review));
    }

    void addCheck(StatusCheck check) {
        if (pullRequests_.find(check.pullRequestId) == pullRequests_.end()) {
            throw std::invalid_argument("Status check references unknown pull request");
        }
        checks_.push_back(std::move(check));
    }

    void requireCheck(int repositoryId, std::string checkName) {
        if (repositories_.find(repositoryId) == repositories_.end()) {
            throw std::invalid_argument("Unknown repository");
        }
        if (checkName.empty()) {
            throw std::invalid_argument("Required check name cannot be empty");
        }
        requiredChecks_[repositoryId].insert(std::move(checkName));
    }

    void grantWrite(int repositoryId, int developerId) {
        requireKnownIdentity(repositoryId, developerId);
        writers_[repositoryId].insert(developerId);
    }

    void grantMaintain(int repositoryId, int developerId) {
        requireKnownIdentity(repositoryId, developerId);
        maintainers_[repositoryId].insert(developerId);
    }

    void grantAdmin(int repositoryId, int developerId) {
        requireKnownIdentity(repositoryId, developerId);
        administrators_[repositoryId].insert(developerId);
    }

    void markAdministratorBypass(int pullRequestId, int administratorId) {
        const auto request = pullRequests_.find(pullRequestId);
        if (request == pullRequests_.end()) {
            throw std::invalid_argument("Unknown pull request");
        }

        const int repositoryId = request->second.repositoryId;
        const auto admins = administrators_.find(repositoryId);

        if (admins == administrators_.end() ||
            admins->second.find(administratorId) == admins->second.end()) {
            throw std::runtime_error("Only a repository administrator may bypass policy");
        }

        const auto repo = repositories_.at(repositoryId);
        if (!repo.allowAdministratorBypass) {
            throw std::runtime_error("Administrator bypass is disabled");
        }

        bypassedPullRequests_.insert(pullRequestId);
    }

    Eligibility evaluate(int pullRequestId) const {
        const auto requestIterator = pullRequests_.find(pullRequestId);
        if (requestIterator == pullRequests_.end()) {
            throw std::invalid_argument("Unknown pull request");
        }

        const PullRequest& request = requestIterator->second;
        const Repository& repository = repositories_.at(request.repositoryId);
        Eligibility result;

        if (request.state == PullRequestState::Merged) {
            result.reasons.push_back("Pull request is already merged");
            return result;
        }

        if (request.state == PullRequestState::Closed) {
            result.reasons.push_back("Closed pull request cannot be merged");
            return result;
        }

        if (request.state == PullRequestState::Draft) {
            result.reasons.push_back("Draft pull request is not mergeable");
            return result;
        }

        if (!repository.protectedBranch) {
            result.reasons.push_back("Target branch is not protected");
        }

        if (repository.requireLinearHistory && !request.linearHistory) {
            result.reasons.push_back("Required linear history is absent");
        }

        if (repository.requireResolvedConversations &&
            !request.conversationsResolved) {
            result.reasons.push_back("Review conversations remain unresolved");
        }

        if (repository.restrictDirectPushes) {
            const auto writerGroup = writers_.find(repository.id);
            const bool authorCanWrite =
                writerGroup != writers_.end() &&
                writerGroup->second.find(request.authorId) != writerGroup->second.end();

            if (!authorCanWrite) {
                result.reasons.push_back("Author lacks the required repository permission");
            }
        }

        std::unordered_set<int> distinctApprovers;
        bool activeChangeRequest = false;

        for (const auto& review : reviews_) {
            if (review.pullRequestId != request.id) {
                continue;
            }

            const Developer& reviewer = developers_.at(review.reviewerId);

            if (!reviewer.active || review.reviewerId == request.authorId) {
                continue;
            }

            if (review.state == ReviewState::ChangesRequested &&
                review.reviewedBaseVersion == request.baseVersion) {
                activeChangeRequest = true;
            }

            /*
             * A stale approval is ignored when repository policy requires
             * re-review after the base branch advances.
             */
            const bool stale =
                review.reviewedBaseVersion != request.baseVersion;

            if (review.state == ReviewState::Approved &&
                (!repository.dismissStaleApprovals || !stale)) {
                distinctApprovers.insert(review.reviewerId);
            }
        }

        result.validApprovalCount = static_cast<int>(distinctApprovers.size());

        if (result.validApprovalCount < repository.requiredApprovals) {
            result.reasons.push_back(
                "Insufficient distinct eligible approvals: " +
                std::to_string(result.validApprovalCount) + "/" +
                std::to_string(repository.requiredApprovals)
            );
        }

        if (activeChangeRequest) {
            result.reasons.push_back(
                "An active reviewer has requested changes"
            );
        }

        /*
         * Anti-join semantics: for every required check, there must exist
         * a successful matching result for this pull request.
         */
        const auto requirements = requiredChecks_.find(repository.id);
        if (requirements != requiredChecks_.end()) {
            for (const auto& requiredName : requirements->second) {
                const bool successful = std::any_of(
                    checks_.begin(),
                    checks_.end(),
                    [&](const StatusCheck& check) {
                        return check.pullRequestId == request.id &&
                               check.name == requiredName &&
                               check.state == CheckState::Success;
                    }
                );

                if (!successful) {
                    result.reasons.push_back(
                        "Required check missing or unsuccessful: " + requiredName
                    );
                }
            }
        }

        const bool bypassed =
            bypassedPullRequests_.find(request.id) != bypassedPullRequests_.end();

        /*
         * A bypass is an explicit policy exception, not an approval.
         * This demonstration bypasses merge-policy findings for an authorized
         * administrator but never permits merging a closed or draft request.
         */
        if (bypassed) {
            result.eligible = true;
            result.reasons.clear();
            result.reasons.push_back("Authorized administrator bypass recorded");
        } else {
            result.eligible = result.reasons.empty();
        }

        return result;
    }

    void merge(int pullRequestId) {
        auto iterator = pullRequests_.find(pullRequestId);
        if (iterator == pullRequests_.end()) {
            throw std::invalid_argument("Unknown pull request");
        }

        if (!evaluate(pullRequestId).eligible) {
            throw std::runtime_error("Merge rejected by repository governance");
        }

        iterator->second.state = PullRequestState::Merged;
        bypassedPullRequests_.erase(pullRequestId);
    }

    void close(int pullRequestId) {
        auto iterator = pullRequests_.find(pullRequestId);
        if (iterator == pullRequests_.end()) {
            throw std::invalid_argument("Unknown pull request");
        }
        if (iterator->second.state != PullRequestState::Open &&
            iterator->second.state != PullRequestState::Draft) {
            throw std::runtime_error("Only open or draft requests can be closed");
        }

        iterator->second.state = PullRequestState::Closed;
    }

    const std::unordered_map<int, PullRequest>& pullRequests() const {
        return pullRequests_;
    }

private:
    void requireKnownIdentity(int repositoryId, int developerId) const {
        if (repositories_.find(repositoryId) == repositories_.end()) {
            throw std::invalid_argument("Unknown repository");
        }
        if (developers_.find(developerId) == developers_.end()) {
            throw std::invalid_argument("Unknown developer");
        }
    }
};

int main() {
    try {
        RepositoryGovernance governance;

        governance.addDeveloper({1, "Asha", true});
        governance.addDeveloper({2, "Ravi", true});
        governance.addDeveloper({3, "Meera", true});
        governance.addDeveloper({4, "Kabir", true});
        governance.addDeveloper({5, "InactiveReviewer", false});

        governance.addRepository({
            1,
            "deployment-service",
            true,
            2,
            true,
            true,
            true,
            true,
            true,
            true,
            false
        });

        governance.addRepository({
            2,
            "security-scanner",
            true,
            1,
            false,
            true,
            true,
            true,
            true,
            false,
            true
        });

        governance.grantWrite(1, 1);
        governance.grantWrite(1, 2);
        governance.grantMaintain(1, 3);
        governance.grantAdmin(2, 3);

        governance.requireCheck(1, "unit-tests");
        governance.requireCheck(1, "security-scan");
        governance.requireCheck(2, "unit-tests");

        governance.addPullRequest({
            101, 1, 1, "Improve deployment retries",
            PullRequestState::Open, 7, true, true
        });

        governance.addPullRequest({
            102, 1, 2, "Add rollback support",
            PullRequestState::Open, 7, true, true
        });

        governance.addPullRequest({
            103, 1, 1, "Draft health endpoint",
            PullRequestState::Draft, 7, true, false
        });

        governance.addPullRequest({
            201, 2, 3, "Fix scanner validation",
            PullRequestState::Open, 4, true, true
        });

        governance.addReview({101, 2, ReviewState::Approved, 7, true});
        governance.addReview({101, 3, ReviewState::Approved, 7, true});
        governance.addReview({102, 3, ReviewState::ChangesRequested, 7, false});
        governance.addReview({102, 4, ReviewState::Approved, 7, true});
        governance.addReview({201, 4, ReviewState::Approved, 4, true});
        governance.addReview({201, 5, ReviewState::Approved, 4, true});

        governance.addCheck({101, "unit-tests", CheckState::Success});
        governance.addCheck({101, "security-scan", CheckState::Success});
        governance.addCheck({102, "unit-tests", CheckState::Success});
        governance.addCheck({102, "security-scan", CheckState::Failure});
        governance.addCheck({201, "unit-tests", CheckState::Success});

        std::cout << "Repository governance evaluation\n";

        for (const auto& [id, request] : governance.pullRequests()) {
            const Eligibility decision = governance.evaluate(id);

            std::cout << "\nPR #" << id << ": " << request.title
                      << " [" << toString(request.state) << "]\n";
            std::cout << "Eligible approvals: "
                      << decision.validApprovalCount << '\n';
            std::cout << "Merge eligible: "
                      << (decision.eligible ? "yes" : "no") << '\n';

            for (const auto& reason : decision.reasons) {
                std::cout << "  - " << reason << '\n';
            }
        }

        const Eligibility ready = governance.evaluate(101);
        if (ready.eligible) {
            governance.merge(101);
            std::cout << "\nPR #101 merged successfully.\n";
        }

        bool mergeRejected = false;
        try {
            governance.merge(102);
        } catch (const std::runtime_error& error) {
            mergeRejected = true;
            std::cout << "PR #102 rejected: " << error.what() << '\n';
        }

        if (!mergeRejected) {
            throw std::logic_error("Expected policy rejection did not occur");
        }

        /*
         * A production implementation would store records in a database,
         * enforce uniqueness and foreign keys, and re-evaluate policy in an
         * atomic transaction to prevent concurrent merges from using stale
         * review or check results.
         */
        std::cout << "\nGovernance case study completed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Governance error: " << error.what() << '\n';
        return 1;
    }
}
