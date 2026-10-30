#include <algorithm>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

using namespace std;

namespace window_analytics {

constexpr size_t MAX_EVENTS = 500000;
constexpr int MAX_SPAN_DAYS = 3660;

struct Date {
    int64_t serial{};

    static bool leapYear(int year) {
        return year % 400 == 0 || (year % 4 == 0 && year % 100 != 0);
    }

    static int daysInMonth(int year, int month) {
        static const int lengths[] = {
            31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31
        };

        if (month < 1 || month > 12) {
            throw invalid_argument("Month must be between 1 and 12.");
        }

        if (month == 2 && leapYear(year)) {
            return 29;
        }

        return lengths[month - 1];
    }

    // Convert a validated Gregorian date into days since 1970-01-01.
    static int64_t daysFromCivil(int year, unsigned month, unsigned day) {
        year -= month <= 2;
        const int era = (year >= 0 ? year : year - 399) / 400;
        const unsigned yearOfEra = static_cast<unsigned>(year - era * 400);
        const unsigned adjustedMonth =
            month > 2 ? month - 3 : month + 9;
        const unsigned dayOfYear =
            (153 * adjustedMonth + 2) / 5 + day - 1;
        const unsigned dayOfEra =
            yearOfEra * 365 + yearOfEra / 4 -
            yearOfEra / 100 + dayOfYear;

        return static_cast<int64_t>(era) * 146097 +
               static_cast<int64_t>(dayOfEra) - 719468;
    }

    static Date parse(const string& value) {
        if (value.size() != 10 || value[4] != '-' || value[7] != '-') {
            throw invalid_argument("Date must use YYYY-MM-DD format.");
        }

        try {
            const int year = stoi(value.substr(0, 4));
            const int month = stoi(value.substr(5, 2));
            const int day = stoi(value.substr(8, 2));

            if (year < 1900 || year > 9999 ||
                month < 1 || month > 12 ||
                day < 1 || day > daysInMonth(year, month)) {
                throw invalid_argument("Invalid calendar date: " + value);
            }

            return {daysFromCivil(year,
                                  static_cast<unsigned>(month),
                                  static_cast<unsigned>(day))};
        } catch (const invalid_argument&) {
            throw;
        } catch (...) {
            throw invalid_argument("Invalid calendar date: " + value);
        }
    }

    string toString() const {
        int64_t z = serial + 719468;
        const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
        const unsigned dayOfEra =
            static_cast<unsigned>(z - era * 146097);
        const unsigned yearOfEra =
            (dayOfEra - dayOfEra / 1460 +
             dayOfEra / 36524 - dayOfEra / 146096) / 365;

        int year = static_cast<int>(yearOfEra) +
                   static_cast<int>(era * 400);

        const unsigned dayOfYear =
            dayOfEra - (365 * yearOfEra +
                        yearOfEra / 4 - yearOfEra / 100);

        const unsigned monthPrime = (5 * dayOfYear + 2) / 153;
        const unsigned day =
            dayOfYear - (153 * monthPrime + 2) / 5 + 1;
        const unsigned month =
            monthPrime < 10 ? monthPrime + 3 : monthPrime - 9;

        year += month <= 2;

        string result = to_string(year) + "-";
        result += month < 10 ? "0" : "";
        result += to_string(month) + "-";
        result += day < 10 ? "0" : "";
        result += to_string(day);
        return result;
    }
};

struct SaleEvent {
    string eventId;
    string storeId;
    string productId;
    Date saleDate;
    int units{};
    int64_t revenueCents{};
};

struct WindowPolicy {
    int windowDays{7};
    int maximumSpanDays{MAX_SPAN_DAYS};
    long double revenueWeight{0.60L};
    long double growthWeight{0.40L};

    void validate() const {
        if (windowDays < 1) {
            throw invalid_argument("Window length must be positive.");
        }

        if (maximumSpanDays < 2 * windowDays ||
            maximumSpanDays > MAX_SPAN_DAYS) {
            throw invalid_argument("Invalid maximum date span.");
        }

        if (!isfinite(revenueWeight) ||
            !isfinite(growthWeight) ||
            revenueWeight < 0 ||
            growthWeight < 0 ||
            abs(revenueWeight + growthWeight - 1.0L) > 1e-12L) {
            throw invalid_argument("Invalid ranking weights.");
        }
    }
};

struct DailyAggregate {
    int units{};
    int64_t revenueCents{};
};

struct Metric {
    string storeId;
    string productId;
    Date date;

    int dailyUnits{};
    int64_t dailyRevenueCents{};

    int rollingUnits7d{};
    int64_t rollingRevenue7dCents{};
    long double movingAverageRevenue7dCents{};

    optional<int64_t> previous7dRevenueCents;
    optional<long double> growthRate;
    optional<int64_t> previousDayRevenueCents;

    int64_t cumulativeRevenueCents{};

    optional<int> revenueRank;
    optional<int> growthRank;
    optional<long double> compositeScore;
    optional<int> compositeRank;
};

struct GroupKey {
    string storeId;
    string productId;

    bool operator<(const GroupKey& other) const {
        return tie(storeId, productId) <
               tie(other.storeId, other.productId);
    }
};

struct StoreDateKey {
    string storeId;
    int64_t day;

    bool operator<(const StoreDateKey& other) const {
        return tie(storeId, day) < tie(other.storeId, other.day);
    }
};

bool validIdentifier(const string& value) {
    if (value.empty() || value.size() > 50) {
        return false;
    }

    return all_of(value.begin(), value.end(), [](unsigned char ch) {
        return (ch >= 'A' && ch <= 'Z') ||
               (ch >= 'a' && ch <= 'z') ||
               (ch >= '0' && ch <= '9') ||
               ch == '_' || ch == '-';
    });
}

long double safeGrowth(int64_t current, int64_t previous) {
    if (previous <= 0) {
        throw invalid_argument("Growth denominator must be positive.");
    }

    return static_cast<long double>(current - previous) /
           static_cast<long double>(previous);
}

long double normalizedRankScore(int rank, int populationSize) {
    if (populationSize <= 1) {
        return 1.0L;
    }

    return static_cast<long double>(populationSize - rank) /
           static_cast<long double>(populationSize - 1);
}

template <typename Getter, typename Setter>
void assignCompetitionRanks(
    vector<Metric*>& items,
    Getter valueOf,
    Setter assignRank
) {
    sort(items.begin(), items.end(), [&](const Metric* left, const Metric* right) {
        return valueOf(*left) > valueOf(*right);
    });

    optional<long double> previousValue;
    int currentRank = 0;

    for (size_t index = 0; index < items.size(); ++index) {
        const long double value = valueOf(*items[index]);

        if (index == 0 || !previousValue || value != *previousValue) {
            currentRank = static_cast<int>(index + 1);
        }

        assignRank(*items[index], currentRank);
        previousValue = value;
    }
}

class AnalyticsEngine {
private:
    WindowPolicy policy;

    void validateEvents(const vector<SaleEvent>& events) const {
        if (events.empty()) {
            throw invalid_argument("At least one event is required.");
        }

        if (events.size() > MAX_EVENTS) {
            throw invalid_argument("Event limit exceeded.");
        }

        set<string> eventIds;

        for (const auto& event : events) {
            if (!validIdentifier(event.eventId) ||
                !validIdentifier(event.storeId) ||
                !validIdentifier(event.productId)) {
                throw invalid_argument("Invalid event, store, or product identifier.");
            }

            if (!eventIds.insert(event.eventId).second) {
                throw invalid_argument(
                    "Duplicate event identifier: " + event.eventId
                );
            }

            if (event.units <= 0 || event.revenueCents < 0) {
                throw invalid_argument("Invalid sales quantity or revenue.");
            }
        }
    }

public:
    explicit AnalyticsEngine(WindowPolicy configuredPolicy = {})
        : policy(configuredPolicy) {
        policy.validate();
    }

    vector<Metric> calculate(const vector<SaleEvent>& events) const {
        validateEvents(events);

        // Transaction-level input is compressed into a map of daily totals.
        map<GroupKey, map<int64_t, DailyAggregate>> grouped;

        for (const auto& event : events) {
            auto& aggregate = grouped[
                {event.storeId, event.productId}
            ][event.saleDate.serial];

            if (aggregate.revenueCents >
                numeric_limits<int64_t>::max() - event.revenueCents) {
                throw overflow_error("Revenue aggregation overflow.");
            }

            aggregate.revenueCents += event.revenueCents;
            aggregate.units += event.units;
        }

        vector<Metric> result;
        const int window = policy.windowDays;

        for (const auto& [key, observations] : grouped) {
            const int64_t firstDay = observations.begin()->first;
            const int64_t lastDay = observations.rbegin()->first;
            const int64_t span = lastDay - firstDay + 1;

            if (span > policy.maximumSpanDays) {
                throw invalid_argument("A series exceeds the permitted date span.");
            }

            vector<int64_t> revenue;
            vector<int> units;
            vector<int64_t> revenuePrefix(1, 0);
            vector<int64_t> unitsPrefix(1, 0);

            revenue.reserve(static_cast<size_t>(span));
            units.reserve(static_cast<size_t>(span));

            for (int64_t day = firstDay; day <= lastDay; ++day) {
                auto found = observations.find(day);

                const int64_t amount = found == observations.end()
                    ? 0
                    : found->second.revenueCents;

                const int quantity = found == observations.end()
                    ? 0
                    : found->second.units;

                if (revenuePrefix.back() >
                    numeric_limits<int64_t>::max() - amount) {
                    throw overflow_error("Prefix sum overflow.");
                }

                revenue.push_back(amount);
                units.push_back(quantity);
                revenuePrefix.push_back(revenuePrefix.back() + amount);
                unitsPrefix.push_back(unitsPrefix.back() + quantity);
            }

            // Prefix sums make each rolling revenue and unit query O(1).
            for (int64_t index = 0; index < span; ++index) {
                const int64_t currentStart =
                    max<int64_t>(0, index - window + 1);

                const int64_t currentRevenue =
                    revenuePrefix[index + 1] - revenuePrefix[currentStart];

                const int currentUnits =
                    static_cast<int>(
                        unitsPrefix[index + 1] - unitsPrefix[currentStart]
                    );

                const int observedDays =
                    static_cast<int>(index - currentStart + 1);

                Metric metric;
                metric.storeId = key.storeId;
                metric.productId = key.productId;
                metric.date = {firstDay + index};
                metric.dailyRevenueCents = revenue[index];
                metric.dailyUnits = units[index];
                metric.rollingRevenue7dCents = currentRevenue;
                metric.rollingUnits7d = currentUnits;
                metric.movingAverageRevenue7dCents =
                    static_cast<long double>(currentRevenue) / observedDays;
                metric.cumulativeRevenueCents = revenuePrefix[index + 1];

                if (index > 0) {
                    metric.previousDayRevenueCents = revenue[index - 1];
                }

                // A complete comparison requires a current and a preceding
                // non-overlapping window, each containing window days.
                if (index >= 2 * window - 1) {
                    const int64_t previousStart = index - 2 * window + 1;
                    const int64_t previousEnd = index - window + 1;

                    const int64_t previousRevenue =
                        revenuePrefix[previousEnd] -
                        revenuePrefix[previousStart];

                    metric.previous7dRevenueCents = previousRevenue;

                    if (previousRevenue > 0) {
                        metric.growthRate =
                            safeGrowth(currentRevenue, previousRevenue);
                    }
                }

                result.push_back(move(metric));
            }
        }

        // Keep pointers into the completed vector only after it has reached
        // its final size. This avoids pointer invalidation during reallocation.
        map<StoreDateKey, vector<Metric*>> comparisonGroups;

        for (auto& row : result) {
            comparisonGroups[
                {row.storeId, row.date.serial}
            ].push_back(&row);
        }

        for (auto& [groupKey, candidates] : comparisonGroups) {
            assignCompetitionRanks(
                candidates,
                [](const Metric& row) {
                    return static_cast<long double>(row.rollingRevenue7dCents);
                },
                [](Metric& row, int rank) {
                    row.revenueRank = rank;
                }
            );

            vector<Metric*> eligible;

            for (Metric* row : candidates) {
                if (row->growthRate.has_value() &&
                    row->previous7dRevenueCents.has_value() &&
                    *row->previous7dRevenueCents > 0) {
                    eligible.push_back(row);
                }
            }

            if (eligible.empty()) {
                continue;
            }

            assignCompetitionRanks(
                eligible,
                [](const Metric& row) {
                    return *row.growthRate;
                },
                [](Metric& row, int rank) {
                    row.growthRank = rank;
                }
            );

            const int populationSize = static_cast<int>(eligible.size());

            for (Metric* row : eligible) {
                const long double revenueScore =
                    normalizedRankScore(*row->revenueRank, populationSize);

                const long double growthScore =
                    normalizedRankScore(*row->growthRank, populationSize);

                row->compositeScore =
                    policy.revenueWeight * revenueScore +
                    policy.growthWeight * growthScore;
            }

            assignCompetitionRanks(
                eligible,
                [](const Metric& row) {
                    return *row.compositeScore;
                },
                [](Metric& row, int rank) {
                    row.compositeRank = rank;
                }
            );
        }

        sort(result.begin(), result.end(), [](const Metric& left, const Metric& right) {
            return tie(left.date.serial, left.storeId, left.productId) <
                   tie(right.date.serial, right.storeId, right.productId);
        });

        return result;
    }
};

vector<SaleEvent> createSampleEvents() {
    vector<SaleEvent> events;

    const vector<string> stores = {"LKO-01", "LKO-02"};
    const vector<string> products = {"P-A", "P-B", "P-C"};

    const Date start = Date::parse("2026-10-01");
    int eventNumber = 1;

    for (size_t storeIndex = 0; storeIndex < stores.size(); ++storeIndex) {
        for (size_t productIndex = 0;
             productIndex < products.size(); ++productIndex) {

            for (int dayNumber = 0; dayNumber < 21; ++dayNumber) {
                if (stores[storeIndex] == "LKO-02" &&
                    products[productIndex] == "P-C" &&
                    dayNumber == 5) {
                    continue;
                }

                const int64_t revenueCents =
                    10000 +
                    static_cast<int64_t>(productIndex) * 1700 +
                    static_cast<int64_t>(storeIndex) * 800 +
                    static_cast<int64_t>(dayNumber) *
                    (static_cast<int64_t>(productIndex) * 220 +
                     static_cast<int64_t>(storeIndex) * 90);

                const int units =
                    5 + static_cast<int>(productIndex) +
                    ((dayNumber + static_cast<int>(storeIndex)) % 4);

                events.push_back({
                    "EVT-" + to_string(eventNumber++),
                    stores[storeIndex],
                    products[productIndex],
                    {start.serial + dayNumber},
                    units,
                    revenueCents
                });

                if (dayNumber % 5 == 0 && productIndex == 0) {
                    events.push_back({
                        "EVT-" + to_string(eventNumber++),
                        stores[storeIndex],
                        products[productIndex],
                        {start.serial + dayNumber},
                        2,
                        2500 + dayNumber * 10
                    });
                }
            }
        }
    }

    return events;
}

void verifyResults(const vector<Metric>& rows) {
    if (rows.size() != 126) {
        throw runtime_error("Unexpected analytics row count.");
    }

    const Date missingDate = Date::parse("2026-10-06");

    auto missing = find_if(rows.begin(), rows.end(), [&](const Metric& row) {
        return row.storeId == "LKO-02" &&
               row.productId == "P-C" &&
               row.date.serial == missingDate.serial;
    });

    if (missing == rows.end() ||
        missing->dailyRevenueCents != 0 ||
        missing->dailyUnits != 0) {
        throw runtime_error("Missing calendar date was not filled correctly.");
    }

    const Date firstEligibleDate = Date::parse("2026-10-14");

    auto eligible = find_if(rows.begin(), rows.end(), [&](const Metric& row) {
        return row.storeId == "LKO-01" &&
               row.productId == "P-A" &&
               row.date.serial == firstEligibleDate.serial;
    });

    if (eligible == rows.end() ||
        !eligible->growthRate.has_value() ||
        !eligible->compositeRank.has_value()) {
        throw runtime_error("Window eligibility validation failed.");
    }
}

void printReport(const vector<Metric>& rows) {
    if (rows.empty()) {
        throw runtime_error("No analytics rows are available.");
    }

    const int64_t latestDay = max_element(
        rows.begin(), rows.end(),
        [](const Metric& left, const Metric& right) {
            return left.date.serial < right.date.serial;
        }
    )->date.serial;

    vector<const Metric*> latestRows;

    for (const auto& row : rows) {
        if (row.date.serial == latestDay) {
            latestRows.push_back(&row);
        }
    }

    sort(latestRows.begin(), latestRows.end(),
         [](const Metric* left, const Metric* right) {
             if (left->storeId != right->storeId) {
                 return left->storeId < right->storeId;
             }

             const int leftRank =
                 left->compositeRank.value_or(numeric_limits<int>::max());
             const int rightRank =
                 right->compositeRank.value_or(numeric_limits<int>::max());

             return tie(leftRank, left->productId) <
                    tie(rightRank, right->productId);
         });

    cout << "Advanced Window Analytics | Reporting date: "
         << Date{latestDay}.toString() << "\n\n";

    cout << left << setw(10) << "Store"
         << setw(9) << "Product"
         << right << setw(13) << "Daily"
         << setw(14) << "Rolling 7d"
         << setw(12) << "Growth %"
         << setw(10) << "Score"
         << setw(7) << "Rank" << '\n';

    cout << string(75, '-') << '\n';
    cout << fixed << setprecision(2);

    for (const Metric* row : latestRows) {
        cout << left << setw(10) << row->storeId
             << setw(9) << row->productId
             << right << setw(13)
             << static_cast<long double>(row->dailyRevenueCents) / 100.0L
             << setw(14)
             << static_cast<long double>(row->rollingRevenue7dCents) / 100.0L;

        if (row->growthRate.has_value()) {
            cout << setw(12) << (*row->growthRate * 100.0L);
        } else {
            cout << setw(12) << "N/A";
        }

        if (row->compositeScore.has_value()) {
            cout << setw(10) << *row->compositeScore;
        } else {
            cout << setw(10) << "N/A";
        }

        if (row->compositeRank.has_value()) {
            cout << setw(7) << *row->compositeRank;
        } else {
            cout << setw(7) << "N/A";
        }

        cout << '\n';
    }
}

} // namespace window_analytics

int main() {
    using namespace window_analytics;

    try {
        WindowPolicy policy;
        policy.windowDays = 7;
        policy.revenueWeight = 0.60L;
        policy.growthWeight = 0.40L;

        AnalyticsEngine engine(policy);

        const vector<SaleEvent> events = createSampleEvents();
        const vector<Metric> rows = engine.calculate(events);

        verifyResults(rows);
        printReport(rows);

        const auto eligibleCount = count_if(
            rows.begin(), rows.end(),
            [](const Metric& row) {
                return row.compositeScore.has_value();
            }
        );

        cout << "\nTransactions processed: " << events.size() << '\n';
        cout << "Daily analytics rows: " << rows.size() << '\n';
        cout << "Ranking-eligible rows: " << eligibleCount << '\n';

    } catch (const exception& error) {
        cerr << "Analytics execution failed: "
             << error.what() << '\n';
        return 1;
    }

    return 0;
}
