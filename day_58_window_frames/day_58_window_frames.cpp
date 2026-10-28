#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

enum class FrameType {
    Rows,
    Range,
    Groups
};

struct Sale {
    int id;
    std::string employee;
    int day;
    double amount;
};

struct FrameSpec {
    FrameType type;
    int preceding;
    int following;
};

class WindowEngine {
private:
    std::vector<Sale> sales;

    static void validate(const std::vector<Sale>& input) {
        if (input.empty()) {
            throw std::invalid_argument("At least one sale is required");
        }

        std::set<int> ids;

        for (const auto& sale : input) {
            if (sale.id <= 0) {
                throw std::invalid_argument("Sale id must be positive");
            }
            if (sale.employee.empty()) {
                throw std::invalid_argument("Employee cannot be empty");
            }
            if (!std::isfinite(sale.amount) || sale.amount < 0.0) {
                throw std::invalid_argument("Amount must be finite and non-negative");
            }
            if (!ids.insert(sale.id).second) {
                throw std::invalid_argument("Duplicate sale id");
            }
        }
    }

public:
    explicit WindowEngine(std::vector<Sale> input) : sales(std::move(input)) {
        validate(sales);
    }

    std::vector<double> rows(int preceding, int following) const {
        if (preceding < 0 || following < 0) {
            throw std::invalid_argument("ROWS offsets cannot be negative");
        }

        std::vector<double> result;
        result.reserve(sales.size());

        for (std::size_t i = 0; i < sales.size(); ++i) {
            const std::size_t start =
                i >= static_cast<std::size_t>(preceding)
                    ? i - preceding
                    : 0;

            const std::size_t end =
                std::min(
                    sales.size() - 1,
                    i + static_cast<std::size_t>(following)
                );

            double total = 0.0;
            for (std::size_t j = start; j <= end; ++j) {
                total += sales[j].amount;
            }

            result.push_back(total);
        }

        return result;
    }

    std::vector<double> rangeByAmount(double preceding, double following) const {
        if (preceding < 0.0 || following < 0.0) {
            throw std::invalid_argument("RANGE boundaries cannot be negative");
        }

        std::vector<Sale> ordered = sales;

        std::sort(
            ordered.begin(),
            ordered.end(),
            [](const Sale& a, const Sale& b) {
                if (a.amount != b.amount) {
                    return a.amount < b.amount;
                }
                return a.id < b.id;
            }
        );

        std::vector<double> result;
        result.reserve(ordered.size());

        for (const auto& current : ordered) {
            const double low = current.amount - preceding;
            const double high = current.amount + following;

            double total = 0.0;
            for (const auto& candidate : ordered) {
                if (candidate.amount >= low && candidate.amount <= high) {
                    total += candidate.amount;
                }
            }

            result.push_back(total);
        }

        return result;
    }

    std::vector<double> groupsByDay(int precedingGroups, int followingGroups) const {
        if (precedingGroups < 0 || followingGroups < 0) {
            throw std::invalid_argument("GROUPS boundaries cannot be negative");
        }

        std::vector<Sale> ordered = sales;

        std::sort(
            ordered.begin(),
            ordered.end(),
            [](const Sale& a, const Sale& b) {
                if (a.day != b.day) {
                    return a.day < b.day;
                }
                return a.id < b.id;
            }
        );

        std::vector<int> peerDays;
        for (const auto& sale : ordered) {
            if (peerDays.empty() || peerDays.back() != sale.day) {
                peerDays.push_back(sale.day);
            }
        }

        std::vector<double> result;
        result.reserve(ordered.size());

        for (const auto& current : ordered) {
            auto groupIt = std::find(
                peerDays.begin(),
                peerDays.end(),
                current.day
            );

            const int groupIndex =
                static_cast<int>(std::distance(peerDays.begin(), groupIt));

            const int first = std::max(0, groupIndex - precedingGroups);
            const int last = std::min(
                static_cast<int>(peerDays.size()) - 1,
                groupIndex + followingGroups
            );

            double total = 0.0;

            for (const auto& candidate : ordered) {
                auto candidateIt = std::find(
                    peerDays.begin(),
                    peerDays.end(),
                    candidate.day
                );

                const int candidateGroup =
                    static_cast<int>(
                        std::distance(peerDays.begin(), candidateIt)
                    );

                if (candidateGroup >= first && candidateGroup <= last) {
                    total += candidate.amount;
                }
            }

            result.push_back(total);
        }

        return result;
    }
};

void print(const std::string& title, const std::vector<double>& values) {
    std::cout << "\n" << title << "\n";
    for (std::size_t i = 0; i < values.size(); ++i) {
        std::cout << "row " << i + 1 << " -> "
                  << std::fixed << std::setprecision(2)
                  << values[i] << '\n';
    }
}

int main() {
    try {
        std::vector<Sale> sales{
            {1, "Asha", 1, 100.0},
            {2, "Asha", 2, 200.0},
            {3, "Asha", 2, 300.0},
            {4, "Asha", 4, 400.0},
            {5, "Asha", 7, 500.0}
        };

        WindowEngine engine(sales);

        auto rows = engine.rows(1, 0);
        auto range = engine.rangeByAmount(200.0, 0.0);
        auto groups = engine.groupsByDay(1, 0);

        print("ROWS BETWEEN 1 PRECEDING AND CURRENT ROW", rows);
        print("RANGE BETWEEN 200 PRECEDING AND CURRENT ROW", range);
        print("GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW", groups);

        if (rows.size() != 5 || rows[0] != 100.0 || rows[4] != 900.0) {
            throw std::runtime_error("ROWS invariant failed");
        }

        if (groups[0] != 100.0 + 200.0 + 300.0) {
            throw std::runtime_error("GROUPS invariant failed");
        }

        std::cout << "\nGovernance checks: passed\n";
        std::cout << "ROWS uses physical positions; RANGE uses values; "
                     "GROUPS uses peer groups.\n";

        // ROWS is O(n * frame_width). RANGE and GROUPS in this teaching
        // implementation are intentionally direct scans: O(n^2).
        // Production systems can optimize these with prefix sums, sorted
        // indexes, or peer-group boundaries.
    }
    catch (const std::exception& ex) {
        std::cerr << "Execution error: " << ex.what() << '\n';
        return 1;
    }

    return 0;
}
