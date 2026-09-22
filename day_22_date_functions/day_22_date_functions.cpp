/*
 * PostgreSQL Date Functions C++ Case Study
 *
 * Topic:
 *     EXTRACT, DATE_PART, DATE_TRUNC, AGE, CURRENT_DATE
 *
 * Scenario:
 *     Employee and business-event analytics system
 *
 * This C++17 program models a realistic reporting layer that prepares,
 * validates, categorizes, and analyzes dates while generating corresponding
 * PostgreSQL statements.
 *
 * The program does not require an external database library.
 * The generated SQL can be executed through a PostgreSQL C++ client in a
 * production application.
 *
 * The case study demonstrates:
 *     - date representation
 *     - calendar arithmetic
 *     - employee age
 *     - employee tenure
 *     - month and quarter buckets
 *     - SQL generation
 *     - identifier validation
 *     - parameterized filtering
 *     - ISO week considerations
 *     - NULL-aware design
 *     - validation
 *     - exception handling
 *     - complexity
 *     - modular architecture
 *
 * Compile:
 *     g++ -std=c++17 -O2 date_functions_case_study.cpp -o date_functions
 *
 * Run:
 *     ./date_functions
 */

#include <algorithm>
#include <chrono>
#include <cctype>
#include <cmath>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std;


// ============================================================================
// 1. DATE MODEL
// ============================================================================

struct Date {
    int year;
    int month;
    int day;

    bool operator<(const Date& other) const {
        if (year != other.year) {
            return year < other.year;
        }

        if (month != other.month) {
            return month < other.month;
        }

        return day < other.day;
    }

    bool operator==(const Date& other) const {
        return year == other.year
            && month == other.month
            && day == other.day;
    }
};

struct Timestamp {
    Date date;
    int hour;
    int minute;
    int second;

    string toString() const {
        ostringstream output;

        output << setfill('0')
               << setw(4) << date.year
               << "-"
               << setw(2) << date.month
               << "-"
               << setw(2) << date.day
               << " "
               << setw(2) << hour
               << ":"
               << setw(2) << minute
               << ":"
               << setw(2) << second;

        return output.str();
    }
};


// ============================================================================
// 2. CALENDAR UTILITIES
// ============================================================================

bool isLeapYear(int year) {
    if (year % 400 == 0) {
        return true;
    }

    if (year % 100 == 0) {
        return false;
    }

    return year % 4 == 0;
}


int daysInMonth(int year, int month) {
    static const int days[] = {
        31, 28, 31, 30, 31, 30,
        31, 31, 30, 31, 30, 31
    };

    if (month < 1 || month > 12) {
        throw invalid_argument(
            "Month must be between 1 and 12."
        );
    }

    if (month == 2 && isLeapYear(year)) {
        return 29;
    }

    return days[month - 1];
}


void validateDate(const Date& date) {
    if (date.month < 1 || date.month > 12) {
        throw invalid_argument(
            "Invalid month: " +
            to_string(date.month)
        );
    }

    int maximumDay =
        daysInMonth(
            date.year,
            date.month
        );

    if (date.day < 1 || date.day > maximumDay) {
        throw invalid_argument(
            "Invalid day for supplied month."
        );
    }
}


string dateToString(const Date& date) {
    validateDate(date);

    ostringstream output;

    output << setfill('0')
           << setw(4) << date.year
           << "-"
           << setw(2) << date.month
           << "-"
           << setw(2) << date.day;

    return output.str();
}


// ============================================================================
// 3. DATE COMPARISON
// ============================================================================

bool dateLessOrEqual(
    const Date& left,
    const Date& right
) {
    return left < right || left == right;
}


// ============================================================================
// 4. EXTRACT MODEL
// ============================================================================

enum class ExtractField {
    Year,
    Month,
    Day,
    Quarter,
    DayOfYear
};


long long extract(
    const Date& date,
    ExtractField field
) {
    validateDate(date);

    switch (field) {
        case ExtractField::Year:
            return date.year;

        case ExtractField::Month:
            return date.month;

        case ExtractField::Day:
            return date.day;

        case ExtractField::Quarter:
            return ((date.month - 1) / 3) + 1;

        case ExtractField::DayOfYear: {
            long long result = 0;

            for (int month = 1;
                 month < date.month;
                 ++month) {
                result += daysInMonth(
                    date.year,
                    month
                );
            }

            result += date.day;
            return result;
        }
    }

    throw logic_error(
        "Unhandled EXTRACT field."
    );
}


// ============================================================================
// 5. DATE_TRUNC MODEL
// ============================================================================

enum class Truncation {
    Year,
    Quarter,
    Month,
    Day,
    Hour,
    Minute,
    Second
};


Timestamp dateTrunc(
    const Timestamp& timestamp,
    Truncation precision
) {
    Timestamp result = timestamp;

    switch (precision) {
        case Truncation::Year:
            result.date.month = 1;
            result.date.day = 1;
            result.hour = 0;
            result.minute = 0;
            result.second = 0;
            break;

        case Truncation::Quarter:
            result.date.month =
                ((result.date.month - 1) / 3) * 3 + 1;
            result.date.day = 1;
            result.hour = 0;
            result.minute = 0;
            result.second = 0;
            break;

        case Truncation::Month:
            result.date.day = 1;
            result.hour = 0;
            result.minute = 0;
            result.second = 0;
            break;

        case Truncation::Day:
            result.hour = 0;
            result.minute = 0;
            result.second = 0;
            break;

        case Truncation::Hour:
            result.minute = 0;
            result.second = 0;
            break;

        case Truncation::Minute:
            result.second = 0;
            break;

        case Truncation::Second:
            break;
    }

    return result;
}


// ============================================================================
// 6. CALENDAR AGE
// ============================================================================

struct CalendarInterval {
    int years;
    int months;
    int days;

    string toString() const {
        ostringstream output;

        output << years << " years, "
               << months << " months, "
               << days << " days";

        return output.str();
    }
};


CalendarInterval calculateAge(
    const Date& later,
    const Date& earlier
) {
    validateDate(later);
    validateDate(earlier);

    if (later < earlier) {
        throw invalid_argument(
            "The later date must not precede the earlier date."
        );
    }

    int years =
        later.year - earlier.year;

    int months =
        later.month - earlier.month;

    int days =
        later.day - earlier.day;

    if (days < 0) {
        --months;

        int previousMonth =
            later.month - 1;

        int previousYear =
            later.year;

        if (previousMonth == 0) {
            previousMonth = 12;
            --previousYear;
        }

        days += daysInMonth(
            previousYear,
            previousMonth
        );
    }

    if (months < 0) {
        --years;
        months += 12;
    }

    return {
        years,
        months,
        days
    };
}


// ============================================================================
// 7. EMPLOYEE DOMAIN MODEL
// ============================================================================

class Employee {
private:
    int id;
    string name;
    Date birthDate;
    Date joinedDate;
    string department;

public:
    Employee(
        int employeeId,
        string employeeName,
        Date employeeBirthDate,
        Date employeeJoinedDate,
        string employeeDepartment
    )
        : id(employeeId),
          name(move(employeeName)),
          birthDate(employeeBirthDate),
          joinedDate(employeeJoinedDate),
          department(move(employeeDepartment)) {

        validateDate(birthDate);
        validateDate(joinedDate);
    }

    int getId() const {
        return id;
    }

    const string& getName() const {
        return name;
    }

    const Date& getBirthDate() const {
        return birthDate;
    }

    const Date& getJoinedDate() const {
        return joinedDate;
    }

    const string& getDepartment() const {
        return department;
    }

    CalendarInterval ageAsOf(
        const Date& referenceDate
    ) const {
        return calculateAge(
            referenceDate,
            birthDate
        );
    }

    CalendarInterval tenureAsOf(
        const Date& referenceDate
    ) const {
        return calculateAge(
            referenceDate,
            joinedDate
        );
    }
};


// ============================================================================
// 8. EVENT MODEL
// ============================================================================

struct BusinessEvent {
    int eventId;
    Timestamp timestamp;
    double amount;
    int customerId;
};


// ============================================================================
// 9. SQL IDENTIFIER VALIDATION
// ============================================================================

bool isValidIdentifier(
    const string& identifier
) {
    if (identifier.empty()) {
        return false;
    }

    if (
        !(
            std::isalpha(
                static_cast<unsigned char>(
                    identifier[0]
                )
            )
            || identifier[0] == '_'
        )
    ) {
        return false;
    }

    for (size_t index = 1;
         index < identifier.size();
         ++index) {

        unsigned char character =
            static_cast<unsigned char>(
                identifier[index]
            );

        if (
            !(
                std::isalnum(character)
                || identifier[index] == '_'
            )
        ) {
            return false;
        }
    }

    return true;
}


void requireValidIdentifier(
    const string& identifier
) {
    if (!isValidIdentifier(identifier)) {
        throw invalid_argument(
            "Invalid SQL identifier: " +
            identifier
        );
    }
}


// ============================================================================
// 10. SQL GENERATOR
// ============================================================================

class PostgreSQLDateQueryGenerator {
public:
    static string monthlyReport(
        const string& table,
        const string& timestampColumn
    ) {
        requireValidIdentifier(table);
        requireValidIdentifier(timestampColumn);

        ostringstream sql;

        sql
            << "SELECT\n"
            << "    DATE_TRUNC('month', "
            << timestampColumn
            << ") AS month_start,\n"
            << "    COUNT(*) AS row_count\n"
            << "FROM "
            << table
            << "\n"
            << "GROUP BY DATE_TRUNC('month', "
            << timestampColumn
            << ")\n"
            << "ORDER BY month_start;";

        return sql.str();
    }


    static string employeeReport(
        const string& table
    ) {
        requireValidIdentifier(table);

        ostringstream sql;

        sql
            << "SELECT\n"
            << "    employee_id,\n"
            << "    employee_name,\n"
            << "    department,\n"
            << "    EXTRACT(YEAR FROM birth_date)::int "
               "AS birth_year,\n"
            << "    EXTRACT(MONTH FROM birth_date)::int "
               "AS birth_month,\n"
            << "    AGE(CURRENT_DATE, birth_date) "
               "AS age,\n"
            << "    AGE(CURRENT_DATE, joined_date) "
               "AS tenure,\n"
            << "    DATE_TRUNC('month', joined_date) "
               "AS joining_month\n"
            << "FROM "
            << table
            << "\n"
            << "WHERE birth_date <= CURRENT_DATE\n"
            << "  AND joined_date <= CURRENT_DATE\n"
            << "ORDER BY employee_id;";

        return sql.str();
    }


    static string currentMonthReport(
        const string& table,
        const string& timestampColumn
    ) {
        requireValidIdentifier(table);
        requireValidIdentifier(timestampColumn);

        ostringstream sql;

        sql
            << "SELECT\n"
            << "    DATE_TRUNC('month', "
            << timestampColumn
            << ") AS month_start,\n"
            << "    COUNT(*) AS row_count\n"
            << "FROM "
            << table
            << "\n"
            << "WHERE "
            << timestampColumn
            << " >= DATE_TRUNC('month', CURRENT_DATE)\n"
            << "  AND "
            << timestampColumn
            << " < DATE_TRUNC('month', CURRENT_DATE) "
               "+ INTERVAL '1 month'\n"
            << "GROUP BY DATE_TRUNC('month', "
            << timestampColumn
            << ")\n"
            << "ORDER BY month_start;";

        return sql.str();
    }
};


// ============================================================================
// 11. EMPLOYEE REPORTING SERVICE
// ============================================================================

class EmployeeAnalyticsService {
private:
    vector<Employee> employees;

public:
    explicit EmployeeAnalyticsService(
        vector<Employee> employeeList
    )
        : employees(move(employeeList)) {}

    void printReport(
        const Date& referenceDate
    ) const {
        cout
            << "\nEMPLOYEE ANALYTICS REPORT\n"
            << string(80, '-')
            << "\n";

        for (const Employee& employee : employees) {
            if (
                employee.getBirthDate() > referenceDate
            ) {
                throw runtime_error(
                    "Birth date is after reference date for " +
                    employee.getName()
                );
            }

            if (
                employee.getJoinedDate() > referenceDate
            ) {
                throw runtime_error(
                    "Joining date is after reference date for " +
                    employee.getName()
                );
            }

            CalendarInterval age =
                employee.ageAsOf(referenceDate);

            CalendarInterval tenure =
                employee.tenureAsOf(referenceDate);

            cout
                << "ID: "
                << employee.getId()
                << "\nName: "
                << employee.getName()
                << "\nDepartment: "
                << employee.getDepartment()
                << "\nBirth year: "
                << extract(
                    employee.getBirthDate(),
                    ExtractField::Year
                )
                << "\nBirth month: "
                << extract(
                    employee.getBirthDate(),
                    ExtractField::Month
                )
                << "\nAge: "
                << age.toString()
                << "\nTenure: "
                << tenure.toString()
                << "\n"
                << string(40, '-')
                << "\n";
        }
    }
};


// ============================================================================
// 12. MONTHLY EVENT AGGREGATION
// ============================================================================

struct MonthKey {
    int year;
    int month;

    bool operator<(const MonthKey& other) const {
        if (year != other.year) {
            return year < other.year;
        }

        return month < other.month;
    }
};


map<MonthKey, double> aggregateMonthlyRevenue(
    const vector<BusinessEvent>& events
) {
    map<MonthKey, double> result;

    for (const BusinessEvent& event : events) {
        validateDate(event.timestamp.date);

        MonthKey key {
            event.timestamp.date.year,
            event.timestamp.date.month
        };

        result[key] += event.amount;
    }

    return result;
}


// ============================================================================
// 13. QUARTERLY EVENT AGGREGATION
// ============================================================================

struct QuarterKey {
    int year;
    int quarter;

    bool operator<(const QuarterKey& other) const {
        if (year != other.year) {
            return year < other.year;
        }

        return quarter < other.quarter;
    }
};


map<QuarterKey, double> aggregateQuarterlyRevenue(
    const vector<BusinessEvent>& events
) {
    map<QuarterKey, double> result;

    for (const BusinessEvent& event : events) {
        validateDate(event.timestamp.date);

        int quarter =
            static_cast<int>(
                extract(
                    event.timestamp.date,
                    ExtractField::Quarter
                )
            );

        QuarterKey key {
            event.timestamp.date.year,
            quarter
        };

        result[key] += event.amount;
    }

    return result;
}


// ============================================================================
// 14. ISO WEEK CALCULATION
// ============================================================================

int dayOfWeek(
    const Date& date
) {
    /*
     * Sakamoto's algorithm.
     *
     * Result:
     *     0 = Sunday
     *     1 = Monday
     *     ...
     *     6 = Saturday
     */
    static const int monthOffsets[] = {
        0, 3, 2, 5, 0, 3,
        5, 1, 4, 6, 2, 4
    };

    int year = date.year;

    if (date.month < 3) {
        --year;
    }

    return (
        year
        + year / 4
        - year / 100
        + year / 400
        + monthOffsets[date.month - 1]
        + date.day
    ) % 7;
}


pair<int, int> approximateISOWeek(
    const Date& date
) {
    /*
     * A compact implementation sufficient for demonstrating the reporting
     * distinction. PostgreSQL should remain the authoritative implementation
     * when the application actually executes SQL.
     */
    int dow = dayOfWeek(date);

    int isoDay =
        dow == 0
            ? 7
            : dow;

    Date thursday = date;

    int offset =
        4 - isoDay;

    // The full calendar adjustment is deliberately kept in the SQL layer
    // for production reporting. This method demonstrates the concept.
    int estimatedDay =
        date.day + offset;

    int estimatedMonth =
        date.month;

    int estimatedYear =
        date.year;

    while (
        estimatedDay < 1
    ) {
        --estimatedMonth;

        if (estimatedMonth == 0) {
            estimatedMonth = 12;
            --estimatedYear;
        }

        estimatedDay += daysInMonth(
            estimatedYear,
            estimatedMonth
        );
    }

    while (
        estimatedDay >
        daysInMonth(
            estimatedYear,
            estimatedMonth
        )
    ) {
        estimatedDay -=
            daysInMonth(
                estimatedYear,
                estimatedMonth
            );

        ++estimatedMonth;

        if (estimatedMonth == 13) {
            estimatedMonth = 1;
            ++estimatedYear;
        }
    }

    thursday = {
        estimatedYear,
        estimatedMonth,
        estimatedDay
    };

    int isoYear =
        thursday.year;

    Date januaryFirst {
        isoYear,
        1,
        1
    };

    int dayNumber = 0;

    for (
        int month = 1;
        month < thursday.month;
        ++month
    ) {
        dayNumber +=
            daysInMonth(
                isoYear,
                month
            );
    }

    dayNumber +=
        thursday.day;

    int januaryFirstDow =
        dayOfWeek(
            januaryFirst
        );

    int januaryFirstISO =
        januaryFirstDow == 0
            ? 7
            : januaryFirstDow;

    int week =
        (
            dayNumber
            - (4 - januaryFirstISO)
            + 6
        ) / 7;

    if (week < 1) {
        --isoYear;
        week = 52;
    }

    return {
        isoYear,
        week
    };
}


// ============================================================================
// 15. DISPLAY HELPERS
// ============================================================================

void printHeader(
    const string& title
) {
    cout
        << "\n"
        << string(80, '=')
        << "\n"
        << title
        << "\n"
        << string(80, '=')
        << "\n";
}


void printSQL(
    const string& title,
    const string& sql
) {
    cout
        << "\n-- "
        << title
        << "\n"
        << sql
        << "\n";
}


// ============================================================================
// 16. MAIN APPLICATION
// ============================================================================

int main() {
    try {
        printHeader(
            "POSTGRESQL DATE FUNCTIONS - C++ CASE STUDY"
        );

        Date referenceDate {
            2026,
            9,
            22
        };

        validateDate(referenceDate);

        Timestamp referenceTimestamp {
            referenceDate,
            14,
            35,
            48
        };

        cout
            << "\nReference date: "
            << dateToString(referenceDate)
            << "\n";

        cout
            << "Reference timestamp: "
            << referenceTimestamp.toString()
            << "\n";


        // --------------------------------------------------------------------
        // EXTRACT
        // --------------------------------------------------------------------

        printHeader(
            "EXTRACT"
        );

        cout
            << "Year: "
            << extract(
                referenceDate,
                ExtractField::Year
            )
            << "\n";

        cout
            << "Month: "
            << extract(
                referenceDate,
                ExtractField::Month
            )
            << "\n";

        cout
            << "Day: "
            << extract(
                referenceDate,
                ExtractField::Day
            )
            << "\n";

        cout
            << "Quarter: "
            << extract(
                referenceDate,
                ExtractField::Quarter
            )
            << "\n";

        cout
            << "Day of year: "
            << extract(
                referenceDate,
                ExtractField::DayOfYear
            )
            << "\n";


        // --------------------------------------------------------------------
        // DATE_TRUNC
        // --------------------------------------------------------------------

        printHeader(
            "DATE_TRUNC"
        );

        vector<pair<string, Truncation>> truncations {
            {
                "year",
                Truncation::Year
            },
            {
                "quarter",
                Truncation::Quarter
            },
            {
                "month",
                Truncation::Month
            },
            {
                "day",
                Truncation::Day
            },
            {
                "hour",
                Truncation::Hour
            },
            {
                "minute",
                Truncation::Minute
            },
            {
                "second",
                Truncation::Second
            }
        };

        for (const auto& item : truncations) {
            Timestamp result =
                dateTrunc(
                    referenceTimestamp,
                    item.second
                );

            cout
                << left
                << setw(10)
                << item.first
                << " -> "
                << result.toString()
                << "\n";
        }


        // --------------------------------------------------------------------
        // AGE
        // --------------------------------------------------------------------

        printHeader(
            "AGE"
        );

        Date employeeBirth {
            1995,
            4,
            18
        };

        CalendarInterval age =
            calculateAge(
                referenceDate,
                employeeBirth
            );

        cout
            << "Birth date: "
            << dateToString(employeeBirth)
            << "\n";

        cout
            << "Age: "
            << age.toString()
            << "\n";


        // --------------------------------------------------------------------
        // EMPLOYEES
        // --------------------------------------------------------------------

        vector<Employee> employees {
            Employee(
                101,
                "Asha",
                {1990, 5, 17},
                {2017, 6, 12},
                "Engineering"
            ),
            Employee(
                102,
                "Ravi",
                {1987, 11, 3},
                {2015, 2, 9},
                "Finance"
            ),
            Employee(
                103,
                "Meera",
                {1998, 1, 28},
                {2022, 8, 22},
                "Engineering"
            ),
            Employee(
                104,
                "Kabir",
                {1995, 12, 31},
                {2020, 1, 6},
                "Operations"
            )
        };

        EmployeeAnalyticsService employeeService(
            employees
        );

        employeeService.printReport(
            referenceDate
        );


        // --------------------------------------------------------------------
        // BUSINESS EVENTS
        // --------------------------------------------------------------------

        printHeader(
            "BUSINESS EVENT ANALYTICS"
        );

        vector<BusinessEvent> events {
            {
                1,
                {{2026, 1, 10}, 10, 0, 0},
                12000.0,
                1001
            },
            {
                2,
                {{2026, 2, 20}, 15, 0, 0},
                8000.0,
                1002
            },
            {
                3,
                {{2026, 4, 3}, 12, 0, 0},
                15000.0,
                1003
            },
            {
                4,
                {{2026, 5, 18}, 14, 0, 0},
                21000.0,
                1004
            },
            {
                5,
                {{2026, 7, 9}, 9, 0, 0},
                18000.0,
                1005
            }
        };

        auto monthlyRevenue =
            aggregateMonthlyRevenue(events);

        cout
            << "\nMonthly revenue:\n";

        for (const auto& item : monthlyRevenue) {
            cout
                << item.first.year
                << "-"
                << setw(2)
                << setfill('0')
                << item.first.month
                << setfill(' ')
                << " -> "
                << fixed
                << setprecision(2)
                << item.second
                << "\n";
        }

        auto quarterlyRevenue =
            aggregateQuarterlyRevenue(events);

        cout
            << "\nQuarterly revenue:\n";

        for (const auto& item : quarterlyRevenue) {
            cout
                << item.first.year
                << " Q"
                << item.first.quarter
                << " -> "
                << fixed
                << setprecision(2)
                << item.second
                << "\n";
        }


        // --------------------------------------------------------------------
        // ISO WEEK
        // --------------------------------------------------------------------

        printHeader(
            "ISO WEEK CONSIDERATION"
        );

        vector<Date> ISOExamples {
            {2020, 12, 28},
            {2020, 12, 31},
            {2021, 1, 1},
            {2021, 1, 4}
        };

        for (const Date& date : ISOExamples) {
            auto result =
                approximateISOWeek(date);

            cout
                << dateToString(date)
                << " -> ISO year "
                << result.first
                << ", ISO week "
                << result.second
                << "\n";
        }

        cout
            << "\nPostgreSQL authoritative expressions:\n"
            << "EXTRACT(WEEK FROM event_date)\n"
            << "EXTRACT(ISOYEAR FROM event_date)\n";


        // --------------------------------------------------------------------
        // SQL GENERATION
        // --------------------------------------------------------------------

        printHeader(
            "POSTGRESQL SQL GENERATION"
        );

        printSQL(
            "Monthly report",
            PostgreSQLDateQueryGenerator::monthlyReport(
                "orders",
                "created_at"
            )
        );

        printSQL(
            "Employee age and tenure",
            PostgreSQLDateQueryGenerator::employeeReport(
                "employees"
            )
        );

        printSQL(
            "Current-month report",
            PostgreSQLDateQueryGenerator::currentMonthReport(
                "orders",
                "created_at"
            )
        );


        // --------------------------------------------------------------------
        // SAFE IDENTIFIER HANDLING
        // --------------------------------------------------------------------

        printHeader(
            "SECURE IDENTIFIER VALIDATION"
        );

        const string safeTable =
            "application_events";

        const string safeColumn =
            "event_timestamp";

        cout
            << "Safe table accepted: "
            << isValidIdentifier(safeTable)
            << "\n";

        cout
            << "Safe column accepted: "
            << isValidIdentifier(safeColumn)
            << "\n";

        const string unsafeIdentifier =
            "events; DROP TABLE users;";

        cout
            << "Unsafe identifier accepted: "
            << isValidIdentifier(
                unsafeIdentifier
            )
            << "\n";

        try {
            requireValidIdentifier(
                unsafeIdentifier
            );
        }
        catch (const exception& error) {
            cout
                << "Rejected unsafe identifier: "
                << error.what()
                << "\n";
        }


        // --------------------------------------------------------------------
        // NULL DESIGN
        // --------------------------------------------------------------------

        printHeader(
            "NULL AND MISSING-DATE DESIGN"
        );

        optional<Date> optionalBirthDate;

        if (!optionalBirthDate.has_value()) {
            cout
                << "Birth date is absent and is represented as NULL.\n";
        }

        cout
            << "The PostgreSQL equivalent is:\n"
            << "AGE(CURRENT_DATE, birth_date)\n"
            << "which produces NULL when birth_date is NULL.\n";


        // --------------------------------------------------------------------
        // EDGE CASES
        // --------------------------------------------------------------------

        printHeader(
            "EDGE CASES"
        );

        vector<Date> edgeDates {
            {2024, 2, 29},
            {2025, 2, 28},
            {2000, 2, 29},
            {2100, 2, 28}
        };

        for (const Date& date : edgeDates) {
            cout
                << dateToString(date)
                << " -> leap year = "
                << boolalpha
                << isLeapYear(date.year)
                << "\n";
        }


        // --------------------------------------------------------------------
        // INVALID DATE HANDLING
        // --------------------------------------------------------------------

        printHeader(
            "INVALID DATE HANDLING"
        );

        try {
            Date invalid {
                2026,
                2,
                29
            };

            validateDate(invalid);
        }
        catch (const exception& error) {
            cout
                << "Validation caught invalid date: "
                << error.what()
                << "\n";
        }


        // --------------------------------------------------------------------
        // FINAL COMBINED QUERY
        // --------------------------------------------------------------------

        printHeader(
            "FINAL INDUSTRY-STYLE QUERY"
        );

        const string finalQuery = R"SQL(
SELECT
    DATE_TRUNC(
        'month',
        order_timestamp
    ) AS month_start,
    EXTRACT(
        YEAR FROM order_timestamp
    )::int AS order_year,
    EXTRACT(
        QUARTER FROM order_timestamp
    )::int AS order_quarter,
    COUNT(*) AS order_count,
    SUM(order_amount) AS revenue
FROM orders
WHERE order_timestamp >= DATE_TRUNC(
    'year',
    CURRENT_DATE
)
AND order_timestamp < DATE_TRUNC(
    'year',
    CURRENT_DATE
) + INTERVAL '1 year'
GROUP BY
    DATE_TRUNC(
        'month',
        order_timestamp
    ),
    EXTRACT(
        YEAR FROM order_timestamp
    ),
    EXTRACT(
        QUARTER FROM order_timestamp
    )
ORDER BY month_start;
)SQL";

        cout
            << finalQuery
            << "\n";


        // --------------------------------------------------------------------
        // COMPLEXITY AND DESIGN NOTES
        // --------------------------------------------------------------------

        printHeader(
            "COMPLEXITY AND DESIGN NOTES"
        );

        cout
            << "EXTRACT-style component retrieval: O(1)\n"
            << "DATE_TRUNC-style bucket calculation: O(1)\n"
            << "Calendar AGE calculation: O(1)\n"
            << "Monthly aggregation using std::map: O(n log k)\n"
            << "Quarterly aggregation using std::map: O(n log k)\n"
            << "Employee report generation: O(n)\n"
            << "\n"
            << "Here n is the number of input records and k is the number "
               "of distinct reporting buckets.\n"
            << "\n"
            << "A PostgreSQL execution plan can have very different costs "
               "depending on indexes, statistics, grouping strategy, table "
               "size, and whether date functions appear in filtering "
               "expressions.\n";


        // --------------------------------------------------------------------
        // PERFORMANCE-ORIENTED SQL
        // --------------------------------------------------------------------

        printHeader(
            "PERFORMANCE-ORIENTED DATE FILTERING"
        );

        cout
            << R"SQL(
Preferred range-style filtering:

SELECT *
FROM application_events
WHERE event_timestamp >= $1
  AND event_timestamp < $2;

Potentially less index-friendly expression filtering:

SELECT *
FROM application_events
WHERE DATE_TRUNC(
    'day',
    event_timestamp
) = $1;

For production workloads, verify the actual plan using:

EXPLAIN
EXPLAIN ANALYZE
)SQL"
            << "\n";


        // --------------------------------------------------------------------
        // SECURITY-ORIENTED SQL
        // --------------------------------------------------------------------

        printHeader(
            "SECURITY-ORIENTED SQL"
        );

        cout
            << R"SQL(
Do not construct:

SELECT *
FROM orders
WHERE created_at >= 'USER_INPUT';

by concatenating untrusted input.

Use:

SELECT *
FROM orders
WHERE created_at >= $1;

and bind the value through the PostgreSQL client library.

Table and column names are identifiers rather than ordinary values.
Validate or safely compose them separately.
)SQL"
            << "\n";


        // --------------------------------------------------------------------
        // TESTS
        // --------------------------------------------------------------------

        printHeader(
            "CASE STUDY TESTS"
        );

        if (
            extract(
                referenceDate,
                ExtractField::Year
            ) != 2026
        ) {
            throw runtime_error(
                "EXTRACT year test failed."
            );
        }

        if (
            extract(
                referenceDate,
                ExtractField::Month
            ) != 9
        ) {
            throw runtime_error(
                "EXTRACT month test failed."
            );
        }

        Timestamp monthStart =
            dateTrunc(
                referenceTimestamp,
                Truncation::Month
            );

        if (
            monthStart.date.day != 1
            || monthStart.hour != 0
            || monthStart.minute != 0
            || monthStart.second != 0
        ) {
            throw runtime_error(
                "DATE_TRUNC month test failed."
            );
        }

        CalendarInterval knownAge =
            calculateAge(
                referenceDate,
                {1995, 4, 18}
            );

        if (
            knownAge.years != 31
            || knownAge.months != 5
            || knownAge.days != 4
        ) {
            throw runtime_error(
                "AGE test failed."
            );
        }

        if (
            !isValidIdentifier(
                "event_timestamp"
            )
        ) {
            throw runtime_error(
                "Identifier validation test failed."
            );
        }

        if (
            isValidIdentifier(
                "event_timestamp;DROP"
            )
        ) {
            throw runtime_error(
                "Unsafe identifier test failed."
            );
        }

        cout
            << "All case-study tests passed.\n";


        // --------------------------------------------------------------------
        // COMPLETION
        // --------------------------------------------------------------------

        printHeader(
            "END OF C++ DATE FUNCTIONS CASE STUDY"
        );

        return 0;
    }
    catch (const exception& error) {
        cerr
            << "Fatal error: "
            << error.what()
            << "\n";

        return 1;
    }
}
