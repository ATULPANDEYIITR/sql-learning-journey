#include <algorithm>
#include <iostream>
#include <optional>
#include <set>
#include <string>
#include <unordered_set>
#include <vector>

enum class SqlTruth {
    True,
    False,
    Unknown
};

std::string truthToString(SqlTruth value) {
    switch (value) {
        case SqlTruth::True:
            return "TRUE";
        case SqlTruth::False:
            return "FALSE";
        case SqlTruth::Unknown:
            return "UNKNOWN";
    }

    return "UNKNOWN";
}

SqlTruth sqlEqual(
    const std::optional<std::string>& left,
    const std::optional<std::string>& right
) {
    if (!left.has_value() || !right.has_value()) {
        return SqlTruth::Unknown;
    }

    return *left == *right ? SqlTruth::True : SqlTruth::False;
}

SqlTruth sqlIn(
    const std::optional<std::string>& value,
    const std::vector<std::optional<std::string>>& candidates
) {
    bool unknownEncountered = false;

    for (const auto& candidate : candidates) {
        const SqlTruth comparison = sqlEqual(value, candidate);

        if (comparison == SqlTruth::True) {
            return SqlTruth::True;
        }

        if (comparison == SqlTruth::Unknown) {
            unknownEncountered = true;
        }
    }

    return unknownEncountered ? SqlTruth::Unknown : SqlTruth::False;
}

SqlTruth sqlNot(SqlTruth value) {
    if (value == SqlTruth::Unknown) {
        return SqlTruth::Unknown;
    }

    return value == SqlTruth::True
        ? SqlTruth::False
        : SqlTruth::True;
}

bool passesWhere(SqlTruth value) {
    return value == SqlTruth::True;
}

struct PullRequest {
    int id;
    std::string sourceBranch;
    std::string targetBranch;
    std::optional<std::string> author;
    bool draft;
};

struct Review {
    std::string reviewer;
    std::string state;
    bool eligible;
};

struct StatusCheck {
    std::string name;
    bool passed;
};

struct BranchPolicy {
    std::string branch;
    int requiredApprovals;
    bool requirePassingChecks;
    bool preventDirectPush;
};

struct MergeDecision {
    bool eligible;
    std::vector<std::string> reasons;
};

MergeDecision evaluateMerge(
    const PullRequest& pullRequest,
    const std::vector<Review>& reviews,
    const std::vector<StatusCheck>& checks,
    const BranchPolicy& policy
) {
    MergeDecision decision{true, {}};

    if (pullRequest.targetBranch != policy.branch) {
        decision.eligible = false;
        decision.reasons.push_back("Target branch is not governed by this policy.");
    }

    if (pullRequest.draft) {
        decision.eligible = false;
        decision.reasons.push_back("Draft Pull Request cannot be merged.");
    }

    if (pullRequest.author.has_value() == false) {
        decision.eligible = false;
        decision.reasons.push_back("Pull Request author is missing.");
    }

    int validApprovals = 0;

    for (const auto& review : reviews) {
        if (review.eligible && review.state == "APPROVED") {
            ++validApprovals;
        }
    }

    if (validApprovals < policy.requiredApprovals) {
        decision.eligible = false;
        decision.reasons.push_back(
            "Required approval count has not been satisfied."
        );
    }

    if (policy.requirePassingChecks) {
        for (const auto& check : checks) {
            if (!check.passed) {
                decision.eligible = false;
                decision.reasons.push_back(
                    "A required status check has failed."
                );
            }
        }
    }

    return decision;
}

void demonstrateNullAwareMembership() {
    std::cout << "SQL-style membership semantics\n\n";

    const std::vector<std::optional<std::string>> blocked = {
        std::string("Finance"),
        std::nullopt
    };

    const std::vector<std::optional<std::string>> departments = {
        std::string("Engineering"),
        std::string("Finance"),
        std::string("Security"),
        std::nullopt
    };

    for (const auto& department : departments) {
        const SqlTruth inResult = sqlIn(department, blocked);
        const SqlTruth notInResult = sqlNot(inResult);

        std::cout
            << "department="
            << (department.has_value() ? *department : "NULL")
            << " IN -> " << truthToString(inResult)
            << ", NOT IN -> " << truthToString(notInResult)
            << ", WHERE -> "
            << (passesWhere(notInResult) ? "returned" : "filtered")
            << '\n';
    }

    std::cout << '\n';
}

void demonstrateSetAlternative() {
    std::cout << "Application-side set membership\n\n";

    std::unordered_set<int> activeEmployeeIds = {
        101, 102, 104, 107
    };

    std::vector<int> requestedIds = {
        101, 105, 107, 999
    };

    for (int id : requestedIds) {
        const bool exists = activeEmployeeIds.contains(id);

        std::cout
            << "employee " << id
            << ": "
            << (exists ? "member" : "not a member")
            << '\n';
    }

    std::cout << '\n';
}

void demonstrateRepositoryGovernance() {
    std::cout << "Repository governance merge evaluation\n\n";

    PullRequest pullRequest{
        842,
        "feature/review-policy",
        "main",
        std::string("atul"),
        false
    };

    std::vector<Review> reviews{
        {"security-reviewer", "APPROVED", true},
        {"platform-reviewer", "COMMENTED", true},
        {"external-contributor", "APPROVED", false}
    };

    std::vector<StatusCheck> checks{
        {"unit-tests", true},
        {"security-scan", true},
        {"integration-tests", false}
    };

    BranchPolicy policy{
        "main",
        2,
        true,
        true
    };

    MergeDecision decision = evaluateMerge(
        pullRequest,
        reviews,
        checks,
        policy
    );

    std::cout
        << "Pull Request #" << pullRequest.id
        << ": "
        << (decision.eligible ? "MERGE ELIGIBLE" : "BLOCKED")
        << '\n';

    for (const auto& reason : decision.reasons) {
        std::cout << "  - " << reason << '\n';
    }

    std::cout << '\n';
}

int main() {
    demonstrateNullAwareMembership();
    demonstrateSetAlternative();
    demonstrateRepositoryGovernance();

    std::cout << "C++ case study complete.\n";
    return 0;
}
