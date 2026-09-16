/*
 * SQL Operators: Industry-style C++ case study
 *
 * Case study:
 *     Employee analytics and rule-based search service
 *
 * The program models an application that receives filtering requirements,
 * validates them, evaluates them against an in-memory employee repository,
 * generates parameterized SQL, and produces analytical reports.
 *
 * The implementation demonstrates the conceptual role of:
 *
 * - arithmetic operators
 * - comparison operators
 * - AND / OR / NOT
 * - BETWEEN
 * - IN / NOT IN
 * - LIKE
 * - NULL handling
 * - parameterized query construction
 * - operator precedence
 * - validation
 * - aggregation
 * - complexity considerations
 *
 * The program does not depend on an external SQL library. The repository is
 * implemented in C++ so that the operator logic and application architecture
 * remain fully self-contained and compilable with C++17 or later.
 *
 * Compile:
 *     g++ -std=c++17 -O2 sql_operators_case_study.cpp -o sql_operators_case_study
 *
 * Run:
 *     ./sql_operators_case_study
 */

#include <algorithm>
#include <cassert>
#include <cctype>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>


struct Employee {
    int id;
    std::string name;
    std::string department;
    double salary;
    std::optional<double> bonus;
    int age;
    std::string city;
    std::string title;
    std::optional<double> performance;
    bool active;
};


struct SearchCriteria {
    std::optional<double> minimumSalary;
    std::optional<double> maximumSalary;
    std::set<std::string> cities;
    std::optional<std::string> nameLikePattern;
    std::optional<double> minimumPerformance;
    bool activeOnly = true;
    bool excludeFinance = false;
};


struct SqlQuery {
    std::string statement;
    std::vector<std::string> parameters;
};


void printTitle(const std::string& title) {
    std::cout << "\n" << std::string(78, '=') << "\n";
    std::cout << title << "\n";
    std::cout << std::string(78, '=') << "\n";
}


std::vector<Employee> createEmployees() {
    return {
        {1, "Aarav Sharma", "Engineering", 85000, 7000, 29,
         "Lucknow", "Software Engineer", 91.5, true},

        {2, "Priya Singh", "Engineering", 112000, 12000, 34,
         "Delhi", "Senior Software Engineer", 96.0, true},

        {3, "Rohan Verma", "Finance", 78000, std::nullopt, 41,
         "Mumbai", "Financial Analyst", 82.0, true},

        {4, "Neha Gupta", "Human Resources", 68000, 5000, 31,
         "Lucknow", "HR Manager", 88.0, true},

        {5, "Kabir Khan", "Security", 99000, 9000, 38,
         "Hyderabad", "Security Engineer", 93.0, true},

        {6, "Ananya Rao", "Sales", 72000, 4000, 26,
         "Bengaluru", "Sales Executive", 79.5, true},

        {7, "Vikram Patel", "Research", 125000, 18000, 45,
         "Pune", "Research Scientist", 97.0, true},

        {8, "Meera Joshi", "Engineering", 64000, std::nullopt, 24,
         "Lucknow", "Junior Developer", 74.0, true},

        {9, "Arjun Mehta", "Sales", 91000, 6000, 36,
         "Delhi", "Sales Manager", 89.0, true},

        {10, "Sara Ali", "Security", 105000, 11000, 33,
         "Mumbai", "Cybersecurity Analyst", 94.5, true},

        {11, "Dev Malhotra", "Finance", 88000, std::nullopt, 39,
         "Pune", "Risk Analyst", 86.0, false},

        {12, "Ishita Kapoor", "Research", 118000, 15000, 30,
         "Delhi", "Data Scientist", 95.5, true}
    };
}


void printEmployee(const Employee& employee) {
    std::cout
        << std::left
        << std::setw(20) << employee.name
        << std::setw(15) << employee.department
        << std::setw(11) << std::fixed << std::setprecision(2)
        << employee.salary
        << std::setw(12)
        << (employee.bonus.has_value()
                ? std::to_string(static_cast<int>(*employee.bonus))
                : "NULL")
        << std::setw(15) << employee.city
        << std::setw(27) << employee.title
        << (employee.active ? "ACTIVE" : "INACTIVE")
        << "\n";
}


void printEmployees(const std::vector<Employee>& employees) {
    if (employees.empty()) {
        std::cout << "(no matching employees)\n";
        return;
    }

    std::cout
        << std::left
        << std::setw(20) << "Name"
        << std::setw(15) << "Department"
        << std::setw(11) << "Salary"
        << std::setw(12) << "Bonus"
        << std::setw(15) << "City"
        << std::setw(27) << "Title"
        << "Status\n";

    std::cout << std::string(120, '-') << "\n";

    for (const auto& employee : employees) {
        printEmployee(employee);
    }
}


bool betweenInclusive(double value, double lower, double upper) {
    /*
     * SQL:
     *
     *     value BETWEEN lower AND upper
     *
     * means:
     *
     *     value >= lower AND value <= upper
     *
     * The boundaries are inclusive.
     */
    return value >= lower && value <= upper;
}


bool likeMatchRecursive(
    const std::string& value,
    std::size_t valueIndex,
    const std::string& pattern,
    std::size_t patternIndex
) {
    /*
     * A small LIKE matcher:
     *
     * % = zero or more characters
     * _ = exactly one character
     *
     * This recursive implementation is educational. Production systems
     * should use an appropriately optimized pattern-matching strategy.
     */
    if (patternIndex == pattern.size()) {
        return valueIndex == value.size();
    }

    if (pattern[patternIndex] == '%') {
        /*
         * % can consume zero characters or one character and remain active.
         */
        return likeMatchRecursive(
                   value,
                   valueIndex,
                   pattern,
                   patternIndex + 1
               ) ||
               (
                   valueIndex < value.size() &&
                   likeMatchRecursive(
                       value,
                       valueIndex + 1,
                       pattern,
                       patternIndex
                   )
               );
    }

    if (valueIndex == value.size()) {
        return false;
    }

    if (
        pattern[patternIndex] == '_' ||
        std::tolower(static_cast<unsigned char>(pattern[patternIndex])) ==
            std::tolower(static_cast<unsigned char>(value[valueIndex]))
    ) {
        return likeMatchRecursive(
            value,
            valueIndex + 1,
            pattern,
            patternIndex + 1
        );
    }

    return false;
}


bool sqlLike(const std::string& value, const std::string& pattern) {
    return likeMatchRecursive(value, 0, pattern, 0);
}


std::string escapeSqlLiteral(const std::string& value) {
    /*
     * This helper is intentionally included for demonstration of why raw
     * string interpolation is dangerous. It doubles single quotes.
     *
     * Real database applications should prefer the driver's parameter
     * binding API rather than manually escaping values.
     */
    std::string result;

    for (char character : value) {
        if (character == '\'') {
            result += "''";
        } else {
            result += character;
        }
    }

    return result;
}


bool matchesCriteria(
    const Employee& employee,
    const SearchCriteria& criteria
) {
    /*
     * This function represents the semantics of a SQL WHERE clause.
     *
     * Conditions are deliberately combined with explicit logical operations
     * and parentheses so the business rule is unambiguous.
     */

    if (
        criteria.minimumSalary.has_value() &&
        employee.salary < *criteria.minimumSalary
    ) {
        return false;
    }

    if (
        criteria.maximumSalary.has_value() &&
        employee.salary > *criteria.maximumSalary
    ) {
        return false;
    }

    if (
        !criteria.cities.empty() &&
        criteria.cities.find(employee.city) == criteria.cities.end()
    ) {
        return false;
    }

    if (
        criteria.nameLikePattern.has_value() &&
        !sqlLike(employee.name, *criteria.nameLikePattern)
    ) {
        return false;
    }

    if (
        criteria.minimumPerformance.has_value()
    ) {
        /*
         * SQL would require:
         *
         *     performance_score >= ?
         *
         * A NULL performance score should not pass this condition because
         * NULL >= value evaluates to UNKNOWN in SQL.
         */
        if (
            !employee.performance.has_value() ||
            *employee.performance < *criteria.minimumPerformance
        ) {
            return false;
        }
    }

    if (criteria.activeOnly && !employee.active) {
        return false;
    }

    if (criteria.excludeFinance) {
        /*
         * SQL equivalent:
         *
         *     NOT (department = 'Finance')
         */
        if (employee.department == "Finance") {
            return false;
        }
    }

    return true;
}


std::string formatDouble(double value) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(2) << value;
    return stream.str();
}


SqlQuery buildParameterizedQuery(const SearchCriteria& criteria) {
    SqlQuery result;

    result.statement = R"SQL(
SELECT
    employee_name,
    department,
    salary,
    bonus,
    city,
    job_title,
    performance_score,
    active
FROM employees
WHERE 1 = 1
)SQL";

    if (criteria.minimumSalary.has_value()) {
        result.statement += "  AND salary >= ?\n";
        result.parameters.push_back(formatDouble(*criteria.minimumSalary));
    }

    if (criteria.maximumSalary.has_value()) {
        result.statement += "  AND salary <= ?\n";
        result.parameters.push_back(formatDouble(*criteria.maximumSalary));
    }

    if (!criteria.cities.empty()) {
        result.statement += "  AND city IN (";

        bool first = true;

        for (const auto& city : criteria.cities) {
            if (!first) {
                result.statement += ", ";
            }

            result.statement += "?";
            result.parameters.push_back(city);
            first = false;
        }

        result.statement += ")\n";
    }

    if (criteria.nameLikePattern.has_value()) {
        result.statement += "  AND employee_name LIKE ?\n";
        result.parameters.push_back(*criteria.nameLikePattern);
    }

    if (criteria.minimumPerformance.has_value()) {
        result.statement += "  AND performance_score >= ?\n";
        result.parameters.push_back(
            formatDouble(*criteria.minimumPerformance)
        );
    }

    if (criteria.activeOnly) {
        result.statement += "  AND active = ?\n";
        result.parameters.push_back("1");
    }

    if (criteria.excludeFinance) {
        result.statement += "  AND NOT (department = ?)\n";
        result.parameters.push_back("Finance");
    }

    result.statement += "ORDER BY salary DESC, employee_name ASC;";

    return result;
}


void printSqlQuery(const SqlQuery& query) {
    std::cout << "\nGenerated parameterized SQL:\n";
    std::cout << query.statement << "\n";

    std::cout << "\nBound parameters:\n";

    for (std::size_t index = 0; index < query.parameters.size(); ++index) {
        std::cout
            << "  [" << index << "] = "
            << query.parameters[index] << "\n";
    }
}


void arithmeticCaseStudy(const std::vector<Employee>& employees) {
    printTitle("1. Arithmetic operators in an employee compensation report");

    std::cout
        << std::left
        << std::setw(20) << "Employee"
        << std::setw(14) << "Salary"
        << std::setw(14) << "Bonus"
        << std::setw(18) << "Total"
        << std::setw(18) << "Monthly"
        << "Raise +10%\n";

    std::cout << std::string(95, '-') << "\n";

    for (const auto& employee : employees) {
        const double bonus = employee.bonus.value_or(0.0);

        /*
         * SQL-style arithmetic:
         *
         * salary + COALESCE(bonus, 0)
         * salary / 12
         * salary * 1.10
         */
        const double total = employee.salary + bonus;
        const double monthly = employee.salary / 12.0;
        const double raisedSalary = employee.salary * 1.10;

        std::cout
            << std::setw(20) << employee.name
            << std::setw(14) << formatDouble(employee.salary)
            << std::setw(14) << formatDouble(bonus)
            << std::setw(18) << formatDouble(total)
            << std::setw(18) << formatDouble(monthly)
            << formatDouble(raisedSalary)
            << "\n";
    }
}


void comparisonCaseStudy(const std::vector<Employee>& employees) {
    printTitle("2. Comparison operators");

    std::vector<Employee> result;

    for (const auto& employee : employees) {
        if (
            employee.salary >= 90000 &&
            employee.salary <= 120000
        ) {
            result.push_back(employee);
        }
    }

    std::cout << "Employees satisfying salary >= 90000 AND salary <= 120000:\n";
    printEmployees(result);

    std::cout << "\nEmployees with salary > 100000:\n";
    result.clear();

    for (const auto& employee : employees) {
        if (employee.salary > 100000) {
            result.push_back(employee);
        }
    }

    printEmployees(result);
}


void logicalCaseStudy(const std::vector<Employee>& employees) {
    printTitle("3. AND, OR, and NOT");

    std::vector<Employee> result;

    for (const auto& employee : employees) {
        /*
         * Explicit parentheses document the intended precedence:
         *
         * (Delhi OR Lucknow) AND salary >= 90000
         */
        if (
            (employee.city == "Delhi" || employee.city == "Lucknow") &&
            employee.salary >= 90000
        ) {
            result.push_back(employee);
        }
    }

    printEmployees(result);

    std::cout << "\nNOT active employees:\n";
    result.clear();

    for (const auto& employee : employees) {
        if (!employee.active) {
            result.push_back(employee);
        }
    }

    printEmployees(result);
}


void betweenCaseStudy(const std::vector<Employee>& employees) {
    printTitle("4. BETWEEN");

    std::vector<Employee> result;

    for (const auto& employee : employees) {
        if (betweenInclusive(employee.salary, 80000, 100000)) {
            result.push_back(employee);
        }
    }

    std::cout
        << "Inclusive range: 80000 <= salary <= 100000\n";

    printEmployees(result);

    std::cout << "\nNOT BETWEEN age 30 and 40:\n";
    result.clear();

    for (const auto& employee : employees) {
        if (!betweenInclusive(employee.age, 30, 40)) {
            result.push_back(employee);
        }
    }

    printEmployees(result);
}


void inCaseStudy(const std::vector<Employee>& employees) {
    printTitle("5. IN and NOT IN");

    const std::unordered_set<std::string> selectedCities = {
        "Delhi",
        "Lucknow",
        "Mumbai"
    };

    std::vector<Employee> result;

    for (const auto& employee : employees) {
        /*
         * SQL:
         *
         * city IN ('Delhi', 'Lucknow', 'Mumbai')
         *
         * Application-side:
         *
         * selectedCities.find(city) != selectedCities.end()
         */
        if (selectedCities.find(employee.city) != selectedCities.end()) {
            result.push_back(employee);
        }
    }

    std::cout << "Employees in selected cities:\n";
    printEmployees(result);

    const std::unordered_set<std::string> excludedCities = {
        "Delhi",
        "Mumbai"
    };

    result.clear();

    for (const auto& employee : employees) {
        if (excludedCities.find(employee.city) == excludedCities.end()) {
            result.push_back(employee);
        }
    }

    std::cout << "\nNOT IN selected cities:\n";
    printEmployees(result);
}


void likeCaseStudy(const std::vector<Employee>& employees) {
    printTitle("6. LIKE pattern matching");

    std::vector<Employee> result;

    for (const auto& employee : employees) {
        if (sqlLike(employee.name, "A%")) {
            result.push_back(employee);
        }
    }

    std::cout << "Names matching LIKE 'A%':\n";
    printEmployees(result);

    result.clear();

    for (const auto& employee : employees) {
        if (sqlLike(employee.title, "%Engineer%")) {
            result.push_back(employee);
        }
    }

    std::cout << "\nJob titles matching LIKE '%Engineer%':\n";
    printEmployees(result);

    result.clear();

    for (const auto& employee : employees) {
        if (sqlLike(employee.name, "_a%")) {
            result.push_back(employee);
        }
    }

    std::cout << "\nNames matching LIKE '_a%':\n";
    printEmployees(result);
}


void nullCaseStudy(const std::vector<Employee>& employees) {
    printTitle("7. NULL handling");

    std::cout << "Employees with missing bonuses:\n";

    for (const auto& employee : employees) {
        /*
         * SQL:
         *
         *     bonus IS NULL
         *
         * C++:
         *
         *     !bonus.has_value()
         */
        if (!employee.bonus.has_value()) {
            std::cout << "  " << employee.name << "\n";
        }
    }

    std::cout << "\nCompensation using COALESCE-like behavior:\n";

    for (const auto& employee : employees) {
        const double bonus = employee.bonus.value_or(0.0);
        const double total = employee.salary + bonus;

        std::cout
            << "  "
            << std::setw(20) << employee.name
            << " total = "
            << formatDouble(total)
            << "\n";
    }

    std::cout
        << "\nSQL NULL rule:\n"
        << "  bonus = NULL       -> incorrect\n"
        << "  bonus IS NULL      -> correct\n"
        << "  bonus <> NULL      -> incorrect\n"
        << "  bonus IS NOT NULL  -> correct\n";
}


void aggregationCaseStudy(const std::vector<Employee>& employees) {
    printTitle("8. Aggregation and operator-based reporting");

    struct DepartmentStatistics {
        int count = 0;
        double totalSalary = 0.0;
    };

    std::map<std::string, DepartmentStatistics> statistics;

    for (const auto& employee : employees) {
        if (!employee.active) {
            continue;
        }

        auto& department = statistics[employee.department];

        department.count += 1;
        department.totalSalary += employee.salary;
    }

    std::cout
        << std::left
        << std::setw(22) << "Department"
        << std::setw(12) << "Employees"
        << "Average Salary\n";

    std::cout << std::string(55, '-') << "\n";

    for (const auto& [department, values] : statistics) {
        const double average =
            values.totalSalary / values.count;

        /*
         * This is conceptually similar to:
         *
         * GROUP BY department
         * HAVING AVG(salary) BETWEEN 80000 AND 120000
         */
        if (betweenInclusive(average, 80000, 120000)) {
            std::cout
                << std::setw(22) << department
                << std::setw(12) << values.count
                << formatDouble(average)
                << "\n";
        }
    }
}


void securityCaseStudy() {
    printTitle("9. Parameterized query security");

    const std::string userCity = "Delhi";
    const double minimumSalary = 90000;

    std::cout
        << "Unsafe conceptual SQL construction:\n"
        << "  SELECT ... WHERE city = '" << userCity << "'\n";

    std::cout
        << "\nSafe application design:\n"
        << "  SELECT ... WHERE city = ? AND salary >= ?\n"
        << "  Bind city separately.\n"
        << "  Bind salary separately.\n";

    /*
     * The point of parameter binding is separation:
     *
     * SQL syntax is controlled by the application.
     * Values are supplied through the database driver's parameter API.
     *
     * Manual escaping is not a substitute for parameterized queries.
     */
}


void validationCaseStudy(const std::vector<Employee>& employees) {
    printTitle("10. Validation and edge-case tests");

    const auto count = [](const std::vector<Employee>& values) {
        return values.size();
    };

    std::size_t highSalaryCount = 0;

    for (const auto& employee : employees) {
        if (employee.salary > 100000) {
            ++highSalaryCount;
        }
    }

    assert(highSalaryCount == 3);

    std::size_t nullBonusCount = 0;

    for (const auto& employee : employees) {
        if (!employee.bonus.has_value()) {
            ++nullBonusCount;
        }
    }

    assert(nullBonusCount == 3);

    assert(betweenInclusive(80000, 80000, 100000));
    assert(betweenInclusive(100000, 80000, 100000));
    assert(!betweenInclusive(100001, 80000, 100000));

    assert(sqlLike("Aarav Sharma", "A%"));
    assert(sqlLike("Software Engineer", "%Engineer%"));
    assert(sqlLike("Sara Ali", "_a%"));
    assert(!sqlLike("Vikram Patel", "A%"));

    std::cout << "All assertions passed.\n";
    std::cout << "Validated records: " << count(employees) << "\n";
}


void performanceDiscussion() {
    printTitle("11. Performance and design considerations");

    std::cout
        << R"TEXT(
Filtering an in-memory vector is O(n) for a single scan.

A hash-based membership structure such as unordered_set provides average
O(1) lookup for IN-style membership checks, making a filter over n records
approximately O(n) rather than O(n * k) when k is the number of allowed
values.

Database performance is different:

- A suitable index can reduce the amount of data scanned.
- Composite index ordering affects which predicates can be used efficiently.
- Highly selective predicates may be more useful than low-selectivity ones.
- Leading-wildcard LIKE patterns such as '%Engineer%' are difficult for
  ordinary B-tree indexes to optimize.
- 'Engineer%' has a known prefix and may be more index-friendly depending
  on the database and collation.
- Every index consumes storage and increases write/update cost.
- Query planners make decisions using statistics and engine-specific rules.
- Performance must be measured on realistic data.

The LIKE implementation in this educational C++ program is recursive and can
have poor performance for certain wildcard patterns. It is intentionally
simple to expose the matching mechanism, not to serve as a production SQL
engine.

)TEXT";
}


void buildAndShowRealisticQuery() {
    printTitle("12. Realistic search service query");

    SearchCriteria criteria;

    criteria.minimumSalary = 85000;
    criteria.maximumSalary = 120000;
    criteria.cities = {"Delhi", "Lucknow", "Mumbai"};
    criteria.nameLikePattern = "%a%";
    criteria.minimumPerformance = 85;
    criteria.activeOnly = true;
    criteria.excludeFinance = true;

    SqlQuery query = buildParameterizedQuery(criteria);

    printSqlQuery(query);
}


void runSearchService(const std::vector<Employee>& employees) {
    printTitle("13. Execute the application-level search rule");

    SearchCriteria criteria;

    criteria.minimumSalary = 85000;
    criteria.maximumSalary = 120000;
    criteria.cities = {"Delhi", "Lucknow", "Mumbai"};
    criteria.nameLikePattern = "%a%";
    criteria.minimumPerformance = 85;
    criteria.activeOnly = true;
    criteria.excludeFinance = true;

    std::vector<Employee> matches;

    for (const auto& employee : employees) {
        if (matchesCriteria(employee, criteria)) {
            matches.push_back(employee);
        }
    }

    std::cout << "Search results:\n";
    printEmployees(matches);

    std::cout
        << "\nBusiness rule represented by the filter:\n"
        << "salary >= 85000\n"
        << "AND salary <= 120000\n"
        << "AND city IN ('Delhi', 'Lucknow', 'Mumbai')\n"
        << "AND employee_name LIKE '%a%'\n"
        << "AND performance_score >= 85\n"
        << "AND active = 1\n"
        << "AND NOT (department = 'Finance')\n";
}


void showOperatorReference() {
    printTitle("14. Operator reference");

    std::cout
        << std::left
        << std::setw(18) << "Operator"
        << std::setw(18) << "Family"
        << "Purpose\n";

    std::cout << std::string(70, '-') << "\n";

    const std::vector<std::pair<std::string, std::string>> operators = {
        {"+", "Arithmetic"},
        {"-", "Arithmetic"},
        {"*", "Arithmetic"},
        {"/", "Arithmetic"},
        {"%", "Arithmetic"},
        {"=", "Comparison"},
        {"<> / !=", "Comparison"},
        {">", "Comparison"},
        {"<", "Comparison"},
        {">=", "Comparison"},
        {"<=", "Comparison"},
        {"AND", "Logical"},
        {"OR", "Logical"},
        {"NOT", "Logical"},
        {"BETWEEN", "Range"},
        {"IN", "Membership"},
        {"NOT IN", "Membership"},
        {"LIKE", "Pattern"},
        {"IS NULL", "NULL test"},
        {"IS NOT NULL", "NULL test"}
    };

    for (const auto& [operatorName, family] : operators) {
        std::string purpose;

        if (family == "Arithmetic") {
            purpose = "calculate numeric values";
        } else if (family == "Comparison") {
            purpose = "compare expressions";
        } else if (family == "Logical") {
            purpose = "combine or negate conditions";
        } else if (family == "Range") {
            purpose = "test an inclusive range";
        } else if (family == "Membership") {
            purpose = "test membership";
        } else if (family == "Pattern") {
            purpose = "match text patterns";
        } else {
            purpose = "test NULL state";
        }

        std::cout
            << std::setw(18) << operatorName
            << std::setw(18) << family
            << purpose
            << "\n";
    }
}


int main() {
    std::cout
        << "SQL Operators: Employee Analytics Case Study\n"
        << "C++17 self-contained implementation\n";

    const std::vector<Employee> employees = createEmployees();

    arithmeticCaseStudy(employees);
    comparisonCaseStudy(employees);
    logicalCaseStudy(employees);
    betweenCaseStudy(employees);
    inCaseStudy(employees);
    likeCaseStudy(employees);
    nullCaseStudy(employees);
    aggregationCaseStudy(employees);
    securityCaseStudy();
    validationCaseStudy(employees);
    performanceDiscussion();
    buildAndShowRealisticQuery();
    runSearchService(employees);
    showOperatorReference();

    printTitle("15. Case study complete");

    std::cout
        << "The program demonstrated how SQL operator concepts map to\n"
        << "application-level filtering, validation, reporting, query\n"
        << "construction, NULL handling, security, and performance design.\n";

    return 0;
}
