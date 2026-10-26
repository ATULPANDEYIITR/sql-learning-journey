#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

enum class ReviewStatus {
    Pending,
    Approved,
    Rejected
};

enum class Trend {
    Up,
    Down,
    Flat,
    Unknown
};

struct Commit {
    std::string hash;
    int sequence;
};

struct StatusCheck {
    std::string name;
    bool passed;
};

struct Review {
    std::string reviewer;
    ReviewStatus status;
    bool eligible;
};

struct PullRequest {
    int id;
    std::string sourceBranch;
    std::string targetBranch;
    std::vector<Commit> commits;
    std::vector<Review> reviews;
    std::vector<StatusCheck> checks;
    bool conversationsResolved;
    bool draft;
    bool mergeConflict;
};

struct BranchProtection {
    std::string branchName;
    int requiredApprovals;
    bool requireAllChecks;
    bool requireResolvedConversations;
    bool restrictDirectPush;
    bool restrictForcePush;
    bool requireLinearHistory;
};

struct MergeDecision {
    bool eligible;
    std::vector<std::string> reasons;
};

class GovernanceEngine {
public:
    static Trend classify(double current, const std::optional<double>& previous) {
        if (!previous.has_value()) {
            return Trend::Unknown;
        }

        if (current > *previous) return Trend::Up;
        if (current < *previous) return Trend::Down;
        return Trend::Flat;
    }

    static std::optional<double> percentageChange(
        double current,
        const std::optional<double>& reference
    ) {
        if (!reference.has_value() || *reference == 0.0) {
            return std::nullopt;
        }

        return ((current - *reference) / *reference) * 100.0;
    }

    MergeDecision evaluate(
        const PullRequest& pr,
        const BranchProtection& protection
    ) const {
        MergeDecision decision{true, {}};

        if (pr.targetBranch != protection.branchName) {
            decision.eligible = false;
            decision.reasons.push_back("Pull Request targets a different branch.");
        }

        if (pr.draft) {
            decision.eligible = false;
            decision.reasons.push_back("Draft Pull Requests cannot be merged.");
        }

        if (pr.commits.empty()) {
            decision.eligible = false;
            decision.reasons.push_back("Pull Request contains no commits.");
        }

        if (pr.mergeConflict) {
            decision.eligible = false;
            decision.reasons.push_back("Source and target branches have merge conflicts.");
        }

        if (protection.requireResolvedConversations && !pr.conversationsResolved) {
            decision.eligible = false;
            decision.reasons.push_back("Review conversations remain unresolved.");
        }

        int approvals = 0;

        for (const auto& review : pr.reviews) {
            if (review.eligible && review.status == ReviewStatus::Approved) {
                ++approvals;
            }
        }

        if (approvals < protection.requiredApprovals) {
            decision.eligible = false;
            decision.reasons.push_back(
                "Required eligible approvals have not been reached."
            );
        }

        if (protection.requireAllChecks) {
            for (const auto& check : pr.checks) {
                if (!check.passed) {
                    decision.eligible = false;
                    decision.reasons.push_back(
                        "Status check failed: " + check.name
                    );
                }
            }

            if (pr.checks.empty()) {
                decision.eligible = false;
                decision.reasons.push_back("No required status checks were recorded.");
            }
        }

        return decision;
    }
};

class TimeSeries {
private:
    std::vector<double> values;

public:
    explicit TimeSeries(std::vector<double> input) : values(std::move(input)) {
        if (values.empty()) {
            throw std::invalid_argument("Time series cannot be empty.");
        }

        for (double value : values) {
            if (!std::isfinite(value)) {
                throw std::invalid_argument("All metric values must be finite.");
            }
        }
    }

    struct Row {
        double value;
        std::optional<double> lag;
        std::optional<double> lead;
    };

    std::vector<Row> analyze() const {
        std::vector<Row> rows;
        rows.reserve(values.size());

        for (std::size_t i = 0; i < values.size(); ++i) {
            rows.push_back({
                values[i],
                i > 0 ? std::optional<double>(values[i - 1]) : std::nullopt,
                i + 1 < values.size()
                    ? std::optional<double>(values[i + 1])
                    : std::nullopt
            });
        }

        return rows;
    }

    std::vector<double> localPeaks() const {
        std::vector<double> peaks;

        if (values.size() < 3) {
            return peaks;
        }

        for (std::size_t i = 1; i + 1 < values.size(); ++i) {
            if (values[i] > values[i - 1] && values[i] > values[i + 1]) {
                peaks.push_back(values[i]);
            }
        }

        return peaks;
    }
};

std::string trendToString(Trend trend) {
    switch (trend) {
        case Trend::Up: return "UP";
        case Trend::Down: return "DOWN";
        case Trend::Flat: return "FLAT";
        default: return "UNKNOWN";
    }
}

int main() {
    try {
        TimeSeries series({120, 126, 131, 127, 135, 135, 142});
        const auto rows = series.analyze();

        std::cout << std::fixed << std::setprecision(2);
        std::cout << "VALUE   LAG       LEAD      LAG_TREND   LEAD_TREND\n";
        std::cout << "-----------------------------------------------------\n";

        for (const auto& row : rows) {
            std::optional<double> lagDifference;
            std::optional<double> leadDifference;

            if (row.lag.has_value()) {
                lagDifference = row.value - *row.lag;
            }

            if (row.lead.has_value()) {
                leadDifference = *row.lead - row.value;
            }

            std::cout
                << std::setw(6) << row.value << " "
                << std::setw(8)
                << (row.lag.has_value() ? std::to_string(*row.lag) : "-")
                << " "
                << std::setw(9)
                << (row.lead.has_value() ? std::to_string(*row.lead) : "-")
                << " "
                << std::setw(11)
                << trendToString(GovernanceEngine::classify(row.value, row.lag))
                << " "
                << std::setw(11)
                << trendToString(
                    row.lead.has_value()
                        ? GovernanceEngine::classify(*row.lead, row.value)
                        : Trend::Unknown
                )
                << "\n";
        }

        std::cout << "\nLocal peaks:\n";
        for (double peak : series.localPeaks()) {
            std::cout << peak << "\n";
        }

        PullRequest pr{
            101,
            "feature/revenue-dashboard",
            "main",
            {
                {"a1b2c3", 1},
                {"d4e5f6", 2}
            },
            {
                {"alice", ReviewStatus::Approved, true},
                {"bob", ReviewStatus::Approved, true},
                {"external-reviewer", ReviewStatus::Approved, false}
            },
            {
                {"unit-tests", true},
                {"security-scan", true},
                {"integration-tests", true}
            },
            true,
            false,
            false
        };

        BranchProtection protection{
            "main",
            2,
            true,
            true,
            true,
            true,
            true
        };

        GovernanceEngine engine;
        const MergeDecision decision = engine.evaluate(pr, protection);

        std::cout << "\nMerge eligibility: "
                  << (decision.eligible ? "ELIGIBLE" : "BLOCKED")
                  << "\n";

        for (const auto& reason : decision.reasons) {
            std::cout << "- " << reason << "\n";
        }

        /*
         * Approval from an ineligible reviewer is intentionally ignored.
         * This prevents a review from satisfying governance requirements
         * merely because its state is "Approved".
         */

    } catch (const std::exception& error) {
        std::cerr << "Execution failure: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
