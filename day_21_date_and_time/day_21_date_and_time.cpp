/*
DATE, TIME, TIMESTAMP, INTERVALS, AND DATE ARITHMETIC
=====================================================

C++17 technical case study:
A multi-time-zone event scheduling and maintenance system.

The program demonstrates:

- std::chrono::system_clock
- time_points
- durations
- calendar dates
- timestamps
- date arithmetic
- interval modeling
- interval overlap
- interval merging
- business-day calculations
- recurring events
- deadlines
- expiration
- serialization-oriented formatting
- validation
- scheduling conflicts
- complexity considerations
- exception handling
- modular design

The program uses only the C++ standard library and is intended for C++17 or later.

Important C++ limitation:
C++17's standard library has strong clock and duration support but does not provide
the modern C++20 calendar/time-zone facilities used by libraries or operating
systems for full named-time-zone conversion. The case study therefore models
time-zone offsets explicitly when a fixed offset is sufficient and explains why
production applications should distinguish fixed offsets from named time zones.
*/

#include <algorithm>
#include <chrono>
#include <cmath>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

using namespace std;


// -----------------------------------------------------------------------------
// 1. DATE REPRESENTATION
// -----------------------------------------------------------------------------

struct Date {
    int year;
    int month;
    int day;

    bool operator<(const Date& other) const {
        return tie(year, month, day) <
               tie(other.year, other.month, other.day);
    }

    bool operator==(const Date& other) const {
        return year == other.year &&
               month == other.month &&
               day == other.day;
    }

    bool operator!=(const Date& other) const {
        return !(*this == other);
    }

    bool operator<=(const Date& other) const {
        return *this < other || *this == other;
    }

    bool operator>(const Date& other) const {
        return other < *this;
    }

    bool operator>=(const Date& other) const {
        return other <= *this;
    }
};


// -----------------------------------------------------------------------------
// 2. DATE VALIDATION
// -----------------------------------------------------------------------------

bool isLeapYear(int year) {
    return year % 4 == 0 &&
           (year % 100 != 0 || year % 400 == 0);
}

int daysInMonth(int year, int month) {
    if (month < 1 || month > 12) {
        throw invalid_argument("Month must be between 1 and 12.");
    }

    static const int days[] = {
        31, 28, 31, 30, 31, 30,
        31, 31, 30, 31, 30, 31
    };

    if (month == 2 && isLeapYear(year)) {
        return 29;
    }

    return days[month - 1];
}

bool isValidDate(const Date& date) {
    if (date.month < 1 || date.month > 12) {
        return false;
    }

    return date.day >= 1 &&
           date.day <= daysInMonth(date.year, date.month);
}


// -----------------------------------------------------------------------------
// 3. DATE FORMATTING
// -----------------------------------------------------------------------------

string dateToString(const Date& date) {
    if (!isValidDate(date)) {
        throw invalid_argument("Invalid date.");
    }

    ostringstream output;

    output << setfill('0')
           << setw(4) << date.year
           << "-"
           << setw(2) << date.month
           << "-"
           << setw(2) << date.day;

    return output.str();
}


// -----------------------------------------------------------------------------
// 4. DAYS FROM CIVIL DATE
//
// Howard Hinnant's well-known civil-calendar arithmetic is used here in
// a compact form. It allows date differences without converting through
// platform-specific local-time functions.
// -----------------------------------------------------------------------------

long long daysFromCivil(Date value) {
    int y = value.year;
    unsigned m = static_cast<unsigned>(value.month);
    unsigned d = static_cast<unsigned>(value.day);

    y -= m <= 2;

    const int era =
        (y >= 0 ? y : y - 399) / 400;

    const unsigned yearOfEra =
        static_cast<unsigned>(y - era * 400);

    const unsigned dayOfYear =
        (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5
        + d - 1;

    const unsigned dayOfEra =
        yearOfEra * 365
        + yearOfEra / 4
        - yearOfEra / 100
        + dayOfYear;

    return static_cast<long long>(era) * 146097
           + static_cast<long long>(dayOfEra)
           - 719468;
}

Date civilFromDays(long long z) {
    z += 719468;

    const long long era =
        (z >= 0 ? z : z - 146096) / 146097;

    const unsigned dayOfEra =
        static_cast<unsigned>(
            z - era * 146097
        );

    const unsigned yearOfEra =
        (dayOfEra
         - dayOfEra / 1460
         + dayOfEra / 36524
         - dayOfEra / 146096) / 365;

    int year =
        static_cast<int>(
            yearOfEra + era * 400
        );

    const unsigned dayOfYear =
        dayOfEra -
        (365 * yearOfEra
         + yearOfEra / 4
         - yearOfEra / 100);

    const unsigned month =
        (5 * dayOfYear + 2) / 153;

    const unsigned day =
        dayOfYear -
        (153 * month + 2) / 5 + 1;

    const int actualMonth =
        static_cast<int>(
            month + (month < 10 ? 3 : -9)
        );

    year += actualMonth <= 2;

    return {
        year,
        actualMonth,
        static_cast<int>(day)
    };
}


// -----------------------------------------------------------------------------
// 5. DATE ARITHMETIC
// -----------------------------------------------------------------------------

Date addDays(Date date, long long numberOfDays) {
    if (!isValidDate(date)) {
        throw invalid_argument("Invalid starting date.");
    }

    return civilFromDays(
        daysFromCivil(date) + numberOfDays
    );
}

long long differenceInDays(
    const Date& first,
    const Date& second
) {
    if (!isValidDate(first) ||
        !isValidDate(second)) {
        throw invalid_argument("Invalid date.");
    }

    return daysFromCivil(second) -
           daysFromCivil(first);
}


// -----------------------------------------------------------------------------
// 6. ADDING MONTHS
// -----------------------------------------------------------------------------

Date addMonths(Date date, long long months) {
    if (!isValidDate(date)) {
        throw invalid_argument("Invalid starting date.");
    }

    long long zeroBased =
        static_cast<long long>(date.month - 1)
        + months;

    long long yearAdjustment =
        zeroBased >= 0
            ? zeroBased / 12
            : (zeroBased - 11) / 12;

    int targetYear =
        static_cast<int>(
            static_cast<long long>(date.year)
            + yearAdjustment
        );

    int targetMonth =
        static_cast<int>(
            zeroBased - yearAdjustment * 12 + 1
        );

    int targetDay =
        min(
            date.day,
            daysInMonth(targetYear, targetMonth)
        );

    return {
        targetYear,
        targetMonth,
        targetDay
    };
}


// -----------------------------------------------------------------------------
// 7. ADDING YEARS
// -----------------------------------------------------------------------------

Date addYears(Date date, int years) {
    if (!isValidDate(date)) {
        throw invalid_argument("Invalid starting date.");
    }

    int targetYear = date.year + years;

    int targetDay = date.day;

    if (
        date.month == 2 &&
        date.day == 29 &&
        !isLeapYear(targetYear)
    ) {
        targetDay = 28;
    }

    return {
        targetYear,
        date.month,
        targetDay
    };
}


// -----------------------------------------------------------------------------
// 8. WEEKDAY
// -----------------------------------------------------------------------------

int weekdayMondayZero(const Date& date) {
    /*
    1970-01-01 was Thursday.

    We normalize the number of days since the Unix epoch into:
    Monday = 0
    Tuesday = 1
    ...
    Sunday = 6
    */

    long long days = daysFromCivil(date);

    long long value = (days + 3) % 7;

    if (value < 0) {
        value += 7;
    }

    return static_cast<int>(value);
}

bool isBusinessDay(const Date& date) {
    int weekday = weekdayMondayZero(date);

    return weekday >= 0 &&
           weekday <= 4;
}


// -----------------------------------------------------------------------------
// 9. BUSINESS-DAY ARITHMETIC
// -----------------------------------------------------------------------------

Date addBusinessDays(
    Date start,
    int numberOfDays,
    const vector<Date>& holidays
) {
    if (!isValidDate(start)) {
        throw invalid_argument("Invalid start date.");
    }

    auto isHoliday = [&](const Date& value) {
        return find(
            holidays.begin(),
            holidays.end(),
            value
        ) != holidays.end();
    };

    int step =
        numberOfDays >= 0 ? 1 : -1;

    int remaining =
        abs(numberOfDays);

    Date current = start;

    while (remaining > 0) {
        current = addDays(current, step);

        if (
            isBusinessDay(current) &&
            !isHoliday(current)
        ) {
            --remaining;
        }
    }

    return current;
}


// -----------------------------------------------------------------------------
// 10. TIME OF DAY
// -----------------------------------------------------------------------------

struct TimeOfDay {
    int hour;
    int minute;
    int second;
    int millisecond;

    bool isValid() const {
        return hour >= 0 && hour <= 23 &&
               minute >= 0 && minute <= 59 &&
               second >= 0 && second <= 59 &&
               millisecond >= 0 &&
               millisecond <= 999;
    }
};

string timeToString(const TimeOfDay& time) {
    if (!time.isValid()) {
        throw invalid_argument("Invalid time.");
    }

    ostringstream output;

    output << setfill('0')
           << setw(2) << time.hour
           << ":"
           << setw(2) << time.minute
           << ":"
           << setw(2) << time.second
           << "."
           << setw(3) << time.millisecond;

    return output.str();
}


// -----------------------------------------------------------------------------
// 11. FIXED TIME-ZONE OFFSET
// -----------------------------------------------------------------------------

struct TimeZoneOffset {
    string name;
    int offsetMinutes;
};

string formatOffset(
    const TimeZoneOffset& offset
) {
    int absoluteMinutes =
        abs(offset.offsetMinutes);

    char sign =
        offset.offsetMinutes >= 0 ? '+' : '-';

    ostringstream output;

    output << sign
           << setfill('0')
           << setw(2)
           << absoluteMinutes / 60
           << ":"
           << setw(2)
           << absoluteMinutes % 60;

    return output.str();
}


// -----------------------------------------------------------------------------
// 12. UTC-BASED TIMESTAMP
// -----------------------------------------------------------------------------

using SystemClock =
    chrono::system_clock;

using TimePoint =
    SystemClock::time_point;

using Milliseconds =
    chrono::milliseconds;

TimePoint nowUtc() {
    return SystemClock::now();
}

long long unixMilliseconds(
    const TimePoint& value
) {
    return chrono::duration_cast<
        chrono::milliseconds
    >(
        value.time_since_epoch()
    ).count();
}


// -----------------------------------------------------------------------------
// 13. FORMATTING A SYSTEM TIMESTAMP
// -----------------------------------------------------------------------------

string formatSystemTime(
    const TimePoint& value
) {
    time_t rawTime =
        SystemClock::to_time_t(value);

    tm utcTime{};

#ifdef _WIN32
    gmtime_s(&utcTime, &rawTime);
#else
    gmtime_r(&rawTime, &utcTime);
#endif

    ostringstream output;

    output << put_time(
        &utcTime,
        "%Y-%m-%d %H:%M:%S UTC"
    );

    return output.str();
}


// -----------------------------------------------------------------------------
// 14. INTERVAL
// -----------------------------------------------------------------------------

struct DateTimeInterval {
    TimePoint start;
    TimePoint end;

    DateTimeInterval(
        TimePoint startValue,
        TimePoint endValue
    )
        : start(startValue),
          end(endValue) {
        if (start > end) {
            throw invalid_argument(
                "Interval start cannot be after end."
            );
        }
    }

    Milliseconds duration() const {
        return chrono::duration_cast<
            Milliseconds
        >(end - start);
    }

    bool contains(
        TimePoint value
    ) const {
        return value >= start &&
               value <= end;
    }

    bool overlaps(
        const DateTimeInterval& other
    ) const {
        return start <= other.end &&
               other.start <= end;
    }
};


// -----------------------------------------------------------------------------
// 15. INTERVAL INTERSECTION
// -----------------------------------------------------------------------------

optional<DateTimeInterval> intersection(
    const DateTimeInterval& first,
    const DateTimeInterval& second
) {
    TimePoint start =
        max(first.start, second.start);

    TimePoint end =
        min(first.end, second.end);

    if (start > end) {
        return nullopt;
    }

    return DateTimeInterval(start, end);
}


// -----------------------------------------------------------------------------
// 16. INTERVAL MERGING
// -----------------------------------------------------------------------------

vector<DateTimeInterval> mergeIntervals(
    vector<DateTimeInterval> intervals
) {
    if (intervals.empty()) {
        return {};
    }

    sort(
        intervals.begin(),
        intervals.end(),
        [](const auto& first, const auto& second) {
            return first.start < second.start;
        }
    );

    vector<DateTimeInterval> merged;

    merged.push_back(intervals.front());

    for (size_t index = 1;
         index < intervals.size();
         ++index) {

        auto& previous = merged.back();
        const auto& current = intervals[index];

        if (current.start <= previous.end) {
            previous.end =
                max(previous.end, current.end);
        } else {
            merged.push_back(current);
        }
    }

    return merged;
}


// -----------------------------------------------------------------------------
// 17. MEETING
// -----------------------------------------------------------------------------

class Meeting {
private:
    string title_;
    TimePoint start_;
    Milliseconds duration_;

public:
    Meeting(
        string title,
        TimePoint start,
        Milliseconds duration
    )
        : title_(move(title)),
          start_(start),
          duration_(duration) {

        if (duration_.count() < 0) {
            throw invalid_argument(
                "Meeting duration cannot be negative."
            );
        }
    }

    const string& title() const {
        return title_;
    }

    TimePoint start() const {
        return start_;
    }

    TimePoint end() const {
        return start_ + duration_;
    }

    bool overlaps(
        const Meeting& other
    ) const {
        return start_ < other.end() &&
               other.start_ < end();
    }

    Milliseconds duration() const {
        return duration_;
    }
};


// -----------------------------------------------------------------------------
// 18. DEADLINE
// -----------------------------------------------------------------------------

enum class DeadlineState {
    Open,
    DueNow,
    Overdue
};

struct DeadlineResult {
    DeadlineState state;
    Milliseconds difference;
};

DeadlineResult checkDeadline(
    TimePoint deadline,
    TimePoint current
) {
    if (current < deadline) {
        return {
            DeadlineState::Open,
            chrono::duration_cast<Milliseconds>(
                deadline - current
            )
        };
    }

    if (current == deadline) {
        return {
            DeadlineState::DueNow,
            Milliseconds(0)
        };
    }

    return {
        DeadlineState::Overdue,
        chrono::duration_cast<Milliseconds>(
            current - deadline
        )
    };
}

string deadlineStateToString(
    DeadlineState state
) {
    switch (state) {
        case DeadlineState::Open:
            return "OPEN";

        case DeadlineState::DueNow:
            return "DUE NOW";

        case DeadlineState::Overdue:
            return "OVERDUE";
    }

    return "UNKNOWN";
}


// -----------------------------------------------------------------------------
// 19. EXPIRATION
// -----------------------------------------------------------------------------

bool isExpired(
    TimePoint createdAt,
    Milliseconds lifetime,
    TimePoint current
) {
    return current >= createdAt + lifetime;
}


// -----------------------------------------------------------------------------
// 20. EVENT STORE
//
// A simple in-memory event repository demonstrates separation between
// data storage and business logic.
// -----------------------------------------------------------------------------

class EventStore {
private:
    vector<Meeting> meetings_;

public:
    void add(Meeting meeting) {
        meetings_.push_back(move(meeting));
    }

    const vector<Meeting>& all() const {
        return meetings_;
    }

    vector<pair<string, string>> conflicts() const {
        vector<pair<string, string>> result;

        for (size_t i = 0;
             i < meetings_.size();
             ++i) {

            for (size_t j = i + 1;
                 j < meetings_.size();
                 ++j) {

                if (
                    meetings_[i].overlaps(
                        meetings_[j]
                    )
                ) {
                    result.emplace_back(
                        meetings_[i].title(),
                        meetings_[j].title()
                    );
                }
            }
        }

        return result;
    }
};


// -----------------------------------------------------------------------------
// 21. SYSTEM STATUS
// -----------------------------------------------------------------------------

struct MaintenanceWindow {
    string service;
    Date date;
    TimeOfDay start;
    TimeOfDay end;

    bool valid() const {
        return isValidDate(date) &&
               start.isValid() &&
               end.isValid();
    }
};


// -----------------------------------------------------------------------------
// 22. UTC OFFSET CONVERSION
//
// This conversion is intentionally based on a fixed offset. A fixed offset
// is not the same thing as a named time zone because daylight-saving rules
// can change the offset during the year.
// -----------------------------------------------------------------------------

TimePoint applyOffset(
    TimePoint utc,
    const TimeZoneOffset& offset
) {
    return utc +
        chrono::minutes(offset.offsetMinutes);
}


// -----------------------------------------------------------------------------
// 23. PRINTING DURATION
// -----------------------------------------------------------------------------

string formatDuration(
    Milliseconds duration
) {
    long long totalMilliseconds =
        duration.count();

    bool negative =
        totalMilliseconds < 0;

    if (negative) {
        totalMilliseconds =
            -totalMilliseconds;
    }

    long long hours =
        totalMilliseconds / (60LL * 60LL * 1000LL);

    totalMilliseconds %=
        (60LL * 60LL * 1000LL);

    long long minutes =
        totalMilliseconds / (60LL * 1000LL);

    totalMilliseconds %=
        (60LL * 1000LL);

    long long seconds =
        totalMilliseconds / 1000LL;

    long long milliseconds =
        totalMilliseconds % 1000LL;

    ostringstream output;

    if (negative) {
        output << "-";
    }

    output << setfill('0')
           << setw(2) << hours
           << ":"
           << setw(2) << minutes
           << ":"
           << setw(2) << seconds
           << "."
           << setw(3) << milliseconds;

    return output.str();
}


// -----------------------------------------------------------------------------
// 24. MAIN CASE STUDY
// -----------------------------------------------------------------------------

int main() {
    try {
        cout << string(80, '=') << '\n';
        cout << "DATE, TIME, TIMESTAMP, INTERVALS, AND DATE ARITHMETIC\n";
        cout << string(80, '=') << '\n';

        // ---------------------------------------------------------------------
        // A. Calendar arithmetic
        // ---------------------------------------------------------------------

        Date baseDate{2026, 9, 21};

        cout << "\n1. DATE ARITHMETIC\n";

        cout << "Base date: "
             << dateToString(baseDate)
             << '\n';

        cout << "Tomorrow: "
             << dateToString(
                    addDays(baseDate, 1)
                )
             << '\n';

        cout << "Next week: "
             << dateToString(
                    addDays(baseDate, 7)
                )
             << '\n';

        cout << "Previous week: "
             << dateToString(
                    addDays(baseDate, -7)
                )
             << '\n';

        cout << "Thirty days later: "
             << dateToString(
                    addDays(baseDate, 30)
                )
             << '\n';

        // ---------------------------------------------------------------------
        // B. Date difference
        // ---------------------------------------------------------------------

        cout << "\n2. DATE DIFFERENCE\n";

        Date yearEnd{2026, 12, 31};

        cout << "Days between "
             << dateToString(baseDate)
             << " and "
             << dateToString(yearEnd)
             << ": "
             << differenceInDays(
                    baseDate,
                    yearEnd
                )
             << '\n';

        // ---------------------------------------------------------------------
        // C. Month arithmetic
        // ---------------------------------------------------------------------

        cout << "\n3. MONTH ARITHMETIC\n";

        Date january31{2026, 1, 31};

        cout << "January 31 + one month: "
             << dateToString(
                    addMonths(january31, 1)
                )
             << '\n';

        Date leapJanuary31{2024, 1, 31};

        cout << "2024 January 31 + one month: "
             << dateToString(
                    addMonths(leapJanuary31, 1)
                )
             << '\n';

        Date leapDay{2024, 2, 29};

        cout << "2024 February 29 + one year: "
             << dateToString(
                    addYears(leapDay, 1)
                )
             << '\n';

        // ---------------------------------------------------------------------
        // D. Business days
        // ---------------------------------------------------------------------

        cout << "\n4. BUSINESS-DAY ARITHMETIC\n";

        vector<Date> holidays{
            Date{2026, 9, 25}
        };

        Date businessResult =
            addBusinessDays(
                baseDate,
                5,
                holidays
            );

        cout << "Five business days after "
             << dateToString(baseDate)
             << ", excluding 2026-09-25: "
             << dateToString(businessResult)
             << '\n';

        // ---------------------------------------------------------------------
        // E. Current timestamp
        // ---------------------------------------------------------------------

        cout << "\n5. CURRENT TIMESTAMP\n";

        TimePoint current = nowUtc();

        cout << "Current UTC time: "
             << formatSystemTime(current)
             << '\n';

        cout << "Unix milliseconds: "
             << unixMilliseconds(current)
             << '\n';

        // ---------------------------------------------------------------------
        // F. Fixed time-zone offsets
        // ---------------------------------------------------------------------

        cout << "\n6. TIME-ZONE OFFSET MODEL\n";

        TimeZoneOffset india{
            "IST",
            330
        };

        TimePoint indiaInstant =
            applyOffset(current, india);

        cout << "Offset name: "
             << india.name
             << '\n';

        cout << "Offset: "
             << formatOffset(india)
             << '\n';

        cout << "UTC instant: "
             << formatSystemTime(current)
             << '\n';

        cout << "Adjusted fixed-offset instant: "
             << formatSystemTime(indiaInstant)
             << '\n';

        /*
        The fixed-offset calculation above is useful for understanding the
        relationship between UTC and an offset.

        It must not be treated as a complete named-time-zone implementation.
        A named zone such as America/New_York includes historical and future
        transition rules. C++20 introduces richer calendar/time-zone support,
        while C++17 programs commonly use an appropriate time-zone library
        when those capabilities are required.
        */

        // ---------------------------------------------------------------------
        // G. Intervals
        // ---------------------------------------------------------------------

        cout << "\n7. INTERVALS\n";

        TimePoint intervalStart =
            current;

        TimePoint intervalEnd =
            current + chrono::hours(3);

        DateTimeInterval intervalA(
            intervalStart,
            intervalEnd
        );

        cout << "Interval duration: "
             << formatDuration(
                    intervalA.duration()
                )
             << '\n';

        TimePoint secondStart =
            current + chrono::hours(2);

        TimePoint secondEnd =
            current + chrono::hours(5);

        DateTimeInterval intervalB(
            secondStart,
            secondEnd
        );

        cout << "Intervals overlap: "
             << boolalpha
             << intervalA.overlaps(intervalB)
             << '\n';

        // ---------------------------------------------------------------------
        // H. Interval intersection
        // ---------------------------------------------------------------------

        cout << "\n8. INTERVAL INTERSECTION\n";

        auto overlap =
            intersection(
                intervalA,
                intervalB
            );

        if (overlap.has_value()) {
            cout << "Intersection duration: "
                 << formatDuration(
                        overlap->duration()
                    )
                 << '\n';
        } else {
            cout << "No intersection.\n";
        }

        // ---------------------------------------------------------------------
        // I. Interval merging
        // ---------------------------------------------------------------------

        cout << "\n9. INTERVAL MERGING\n";

        vector<DateTimeInterval> rawIntervals{
            DateTimeInterval(
                current,
                current + chrono::hours(2)
            ),
            DateTimeInterval(
                current + chrono::hours(1),
                current + chrono::hours(4)
            ),
            DateTimeInterval(
                current + chrono::hours(6),
                current + chrono::hours(7)
            )
        };

        vector<DateTimeInterval> merged =
            mergeIntervals(rawIntervals);

        cout << "Input intervals: "
             << rawIntervals.size()
             << '\n';

        cout << "Merged intervals: "
             << merged.size()
             << '\n';

        for (const auto& item : merged) {
            cout << "Duration: "
                 << formatDuration(
                        item.duration()
                    )
                 << '\n';
        }

        // ---------------------------------------------------------------------
        // J. Event scheduling
        // ---------------------------------------------------------------------

        cout << "\n10. EVENT SCHEDULING\n";

        EventStore eventStore;

        eventStore.add(
            Meeting(
                "Architecture Review",
                current,
                chrono::hours(1)
            )
        );

        eventStore.add(
            Meeting(
                "Implementation Session",
                current + chrono::minutes(30),
                chrono::hours(2)
            )
        );

        eventStore.add(
            Meeting(
                "Deployment",
                current + chrono::hours(3),
                chrono::minutes(45)
            )
        );

        for (const auto& meeting :
             eventStore.all()) {

            cout << meeting.title()
                 << ": "
                 << formatSystemTime(
                        meeting.start()
                    )
                 << " -> "
                 << formatSystemTime(
                        meeting.end()
                    )
                 << '\n';
        }

        // ---------------------------------------------------------------------
        // K. Conflict detection
        // ---------------------------------------------------------------------

        cout << "\n11. SCHEDULE CONFLICTS\n";

        auto conflicts =
            eventStore.conflicts();

        if (conflicts.empty()) {
            cout << "No conflicts.\n";
        } else {
            for (const auto& conflict :
                 conflicts) {

                cout << conflict.first
                     << " conflicts with "
                     << conflict.second
                     << '\n';
            }
        }

        // ---------------------------------------------------------------------
        // L. Deadline management
        // ---------------------------------------------------------------------

        cout << "\n12. DEADLINE MANAGEMENT\n";

        TimePoint deadline =
            current + chrono::hours(24);

        DeadlineResult deadlineResult =
            checkDeadline(
                deadline,
                current
            );

        cout << "Deadline state: "
             << deadlineStateToString(
                    deadlineResult.state
                )
             << '\n';

        cout << "Difference: "
             << formatDuration(
                    deadlineResult.difference
                )
             << '\n';

        // ---------------------------------------------------------------------
        // M. Expiration
        // ---------------------------------------------------------------------

        cout << "\n13. EXPIRATION\n";

        TimePoint issuedAt =
            current - chrono::hours(3);

        bool expired =
            isExpired(
                issuedAt,
                chrono::hours(2),
                current
            );

        cout << "Two-hour token expired: "
             << expired
             << '\n';

        // ---------------------------------------------------------------------
        // N. Maintenance window
        // ---------------------------------------------------------------------

        cout << "\n14. MAINTENANCE WINDOW\n";

        MaintenanceWindow maintenance{
            "payments-api",
            Date{2026, 9, 25},
            TimeOfDay{18, 0, 0, 0},
            TimeOfDay{20, 30, 0, 0}
        };

        if (maintenance.valid()) {
            cout << "Service: "
                 << maintenance.service
                 << '\n';

            cout << "Date: "
                 << dateToString(
                        maintenance.date
                    )
                 << '\n';

            cout << "Start: "
                 << timeToString(
                        maintenance.start
                    )
                 << '\n';

            cout << "End: "
                 << timeToString(
                        maintenance.end
                    )
                 << '\n';
        }

        // ---------------------------------------------------------------------
        // O. Duration measurement
        // ---------------------------------------------------------------------

        cout << "\n15. PERFORMANCE TIMING\n";

        auto benchmarkStart =
            chrono::steady_clock::now();

        volatile long long calculation = 0;

        for (int i = 1; i <= 1'000'000; ++i) {
            calculation += i;
        }

        auto benchmarkEnd =
            chrono::steady_clock::now();

        auto elapsed =
            chrono::duration_cast<
                chrono::microseconds
            >(
                benchmarkEnd -
                benchmarkStart
            );

        cout << "Calculation result: "
             << calculation
             << '\n';

        cout << "Elapsed microseconds: "
             << elapsed.count()
             << '\n';

        /*
        steady_clock is appropriate for measuring elapsed duration because it
        is designed to be monotonic. system_clock represents civil/wall-clock
        time and can be adjusted by the operating system.
        */

        // ---------------------------------------------------------------------
        // P. Edge-case validation
        // ---------------------------------------------------------------------

        cout << "\n16. EDGE-CASE VALIDATION\n";

        vector<Date> testDates{
            Date{2024, 2, 29},
            Date{2025, 2, 28},
            Date{2100, 2, 28},
            Date{2000, 2, 29}
        };

        for (const Date& date :
             testDates) {

            cout << dateToString(date)
                 << " -> valid: "
                 << isValidDate(date)
                 << ", leap year: "
                 << isLeapYear(date.year)
                 << '\n';
        }

        // ---------------------------------------------------------------------
        // Q. Error handling
        // ---------------------------------------------------------------------

        cout << "\n17. ERROR HANDLING\n";

        try {
            Date invalidDate{
                2026,
                2,
                30
            };

            if (!isValidDate(invalidDate)) {
                throw invalid_argument(
                    "The supplied date does not exist."
                );
            }
        }
        catch (const exception& error) {
            cout << "Handled error: "
                 << error.what()
                 << '\n';
        }

        // ---------------------------------------------------------------------
        // R. Production design principles
        // ---------------------------------------------------------------------

        cout << "\n18. PRODUCTION DESIGN PRINCIPLES\n";

        vector<string> principles{
            "Use calendar dates when a calendar date is the actual business concept.",
            "Use durations for elapsed time.",
            "Use system_clock for civil timestamps.",
            "Use steady_clock for elapsed-performance measurement.",
            "Prefer a consistent UTC storage convention for distributed systems.",
            "Treat fixed offsets and named time zones as different concepts.",
            "Validate external date and time input.",
            "Define interval boundaries explicitly.",
            "Do not assume every local day is exactly 24 elapsed hours.",
            "Handle leap years and month lengths explicitly.",
            "Keep time-zone conversion at system boundaries.",
            "Serialize timestamps using an unambiguous standard representation."
        };

        for (size_t index = 0;
             index < principles.size();
             ++index) {

            cout << index + 1
                 << ". "
                 << principles[index]
                 << '\n';
        }

        // ---------------------------------------------------------------------
        // S. Complexity discussion
        // ---------------------------------------------------------------------

        cout << "\n19. ALGORITHMIC CONSIDERATIONS\n";

        cout << "Date arithmetic with civil-day conversion: O(1)\n";
        cout << "Business-day stepping: O(number of business days)\n";
        cout << "Interval sorting: O(n log n)\n";
        cout << "Interval merging after sorting: O(n)\n";
        cout << "Naive meeting conflict detection: O(n^2)\n";

        cout << "\nCase study completed successfully.\n";
    }
    catch (const exception& error) {
        cerr << "Fatal error: "
             << error.what()
             << '\n';

        return 1;
    }

    return 0;
}
