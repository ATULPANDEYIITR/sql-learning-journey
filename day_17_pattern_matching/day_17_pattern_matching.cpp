/*
 * Pattern Matching Case Study
 * ===========================
 *
 * C++17 implementation of a searchable contact and incident-record
 * classification system.
 *
 * The system demonstrates:
 *   - SQL-LIKE-style wildcard matching
 *   - ILIKE-style case-insensitive matching
 *   - direct dynamic programming for wildcard matching
 *   - regular expressions using std::regex
 *   - structured records and indexes
 *   - validation
 *   - query processing
 *   - error handling
 *   - performance-aware design
 *   - security boundaries
 *
 * Compile:
 *   g++ -std=c++17 -O2 pattern_matching.cpp -o pattern_matching
 *
 * Run:
 *   ./pattern_matching
 */

#include <algorithm>
#include <cctype>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <regex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std;

// -----------------------------------------------------------------------------
// Utility functions
// -----------------------------------------------------------------------------

string toLower(string value) {
    transform(
        value.begin(),
        value.end(),
        value.begin(),
        [](unsigned char character) {
            return static_cast<char>(tolower(character));
        }
    );

    return value;
}

void section(const string& title) {
    cout << "\n" << string(78, '=') << "\n";
    cout << title << "\n";
    cout << string(78, '=') << "\n";
}

// -----------------------------------------------------------------------------
// SQL-LIKE matcher
// -----------------------------------------------------------------------------

class LikeMatcher {
public:
    /*
     * Dynamic programming implementation.
     *
     * '%' matches zero or more characters.
     * '_' matches exactly one character.
     *
     * Time complexity:
     *     O(text_length * pattern_length)
     *
     * Space complexity:
     *     O(text_length * pattern_length)
     *
     * This avoids translating the pattern into regex and makes the LIKE
     * semantics directly visible.
     */
    static bool match(
        const string& text,
        const string& pattern,
        bool caseInsensitive = false
    ) {
        string normalizedText = text;
        string normalizedPattern = pattern;

        if (caseInsensitive) {
            normalizedText = toLower(normalizedText);
            normalizedPattern = toLower(normalizedPattern);
        }

        const size_t textLength = normalizedText.size();
        const size_t patternLength = normalizedPattern.size();

        vector<vector<bool>> dp(
            textLength + 1,
            vector<bool>(patternLength + 1, false)
        );

        dp[0][0] = true;

        for (size_t patternIndex = 1;
             patternIndex <= patternLength;
             ++patternIndex) {
            if (normalizedPattern[patternIndex - 1] == '%') {
                dp[0][patternIndex] =
                    dp[0][patternIndex - 1];
            }
        }

        for (size_t textIndex = 1;
             textIndex <= textLength;
             ++textIndex) {

            for (size_t patternIndex = 1;
                 patternIndex <= patternLength;
                 ++patternIndex) {

                const char patternCharacter =
                    normalizedPattern[patternIndex - 1];

                if (patternCharacter == '%') {
                    /*
                     * '%' either matches nothing or consumes the current
                     * text character while remaining active.
                     */
                    dp[textIndex][patternIndex] =
                        dp[textIndex][patternIndex - 1] ||
                        dp[textIndex - 1][patternIndex];
                }
                else if (
                    patternCharacter == '_' ||
                    patternCharacter ==
                        normalizedText[textIndex - 1]
                ) {
                    dp[textIndex][patternIndex] =
                        dp[textIndex - 1][patternIndex - 1];
                }
            }
        }

        return dp[textLength][patternLength];
    }
};

// -----------------------------------------------------------------------------
// Regex wrapper
// -----------------------------------------------------------------------------

class RegexMatcher {
public:
    static bool search(
        const string& text,
        const string& pattern,
        bool caseInsensitive = false
    ) {
        try {
            auto flags = regex_constants::ECMAScript;

            if (caseInsensitive) {
                flags |= regex_constants::icase;
            }

            regex expression(pattern, flags);

            return regex_search(text, expression);
        }
        catch (const regex_error& error) {
            throw invalid_argument(
                string("Invalid regular expression: ") +
                error.what()
            );
        }
    }

    static bool fullMatch(
        const string& text,
        const string& pattern,
        bool caseInsensitive = false
    ) {
        try {
            auto flags = regex_constants::ECMAScript;

            if (caseInsensitive) {
                flags |= regex_constants::icase;
            }

            regex expression(pattern, flags);

            return regex_match(text, expression);
        }
        catch (const regex_error& error) {
            throw invalid_argument(
                string("Invalid regular expression: ") +
                error.what()
            );
        }
    }
};

// -----------------------------------------------------------------------------
// Domain model
// -----------------------------------------------------------------------------

struct Record {
    int id;
    string name;
    string email;
    string city;
    string department;
    string status;
    int priority;
};

void printRecord(const Record& record) {
    cout
        << setw(3) << record.id
        << " | " << setw(18) << left << record.name
        << " | " << setw(27) << left << record.email
        << " | " << setw(12) << left << record.city
        << " | " << setw(12) << left << record.department
        << " | " << setw(10) << left << record.status
        << " | priority=" << record.priority
        << "\n";
}

// -----------------------------------------------------------------------------
// Search engine
// -----------------------------------------------------------------------------

class SearchEngine {
private:
    vector<Record> records;

public:
    explicit SearchEngine(vector<Record> inputRecords)
        : records(move(inputRecords)) {}

    vector<Record> like(
        const string& field,
        const string& pattern,
        bool caseInsensitive = false
    ) const {
        vector<Record> results;

        for (const Record& record : records) {
            const string* value = getField(record, field);

            if (value == nullptr) {
                throw invalid_argument(
                    "Unknown search field: " + field
                );
            }

            if (LikeMatcher::match(
                    *value,
                    pattern,
                    caseInsensitive)) {
                results.push_back(record);
            }
        }

        return results;
    }

    vector<Record> regexSearch(
        const string& field,
        const string& pattern,
        bool caseInsensitive = false
    ) const {
        vector<Record> results;

        for (const Record& record : records) {
            const string* value = getField(record, field);

            if (value == nullptr) {
                throw invalid_argument(
                    "Unknown search field: " + field
                );
            }

            if (RegexMatcher::search(
                    *value,
                    pattern,
                    caseInsensitive)) {
                results.push_back(record);
            }
        }

        return results;
    }

    vector<Record> priorityAtLeast(int minimumPriority) const {
        vector<Record> results;

        for (const Record& record : records) {
            if (record.priority >= minimumPriority) {
                results.push_back(record);
            }
        }

        return results;
    }

    vector<Record> combinedSearch(
        const string& namePattern,
        const string& departmentPattern,
        int minimumPriority
    ) const {
        vector<Record> results;

        for (const Record& record : records) {
            const bool nameMatches =
                LikeMatcher::match(
                    record.name,
                    namePattern,
                    true
                );

            const bool departmentMatches =
                LikeMatcher::match(
                    record.department,
                    departmentPattern,
                    true
                );

            const bool priorityMatches =
                record.priority >= minimumPriority;

            if (
                nameMatches &&
                departmentMatches &&
                priorityMatches
            ) {
                results.push_back(record);
            }
        }

        return results;
    }

private:
    static const string* getField(
        const Record& record,
        const string& field
    ) {
        if (field == "name") {
            return &record.name;
        }

        if (field == "email") {
            return &record.email;
        }

        if (field == "city") {
            return &record.city;
        }

        if (field == "department") {
            return &record.department;
        }

        if (field == "status") {
            return &record.status;
        }

        return nullptr;
    }
};

// -----------------------------------------------------------------------------
// Input validation
// -----------------------------------------------------------------------------

bool validEmail(const string& email) {
    /*
     * This intentionally uses a practical application-level validation
     * expression rather than attempting to reproduce the complete formal
     * email grammar.
     */
    static const regex pattern(
        R"(^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$)"
    );

    return regex_match(email, pattern);
}

bool validStatus(const string& status) {
    return status == "OPEN" ||
           status == "CLOSED" ||
           status == "REVIEW";
}

bool validPriority(int priority) {
    return priority >= 1 && priority <= 5;
}

void validateRecords(const vector<Record>& records) {
    for (const Record& record : records) {
        if (record.id <= 0) {
            throw invalid_argument("Record ID must be positive.");
        }

        if (record.name.empty()) {
            throw invalid_argument("Record name cannot be empty.");
        }

        if (!validEmail(record.email)) {
            throw invalid_argument(
                "Invalid email for record: " +
                to_string(record.id)
            );
        }

        if (!validStatus(record.status)) {
            throw invalid_argument(
                "Invalid status for record: " +
                to_string(record.id)
            );
        }

        if (!validPriority(record.priority)) {
            throw invalid_argument(
                "Invalid priority for record: " +
                to_string(record.id)
            );
        }
    }
}

// -----------------------------------------------------------------------------
// Query parsing
// -----------------------------------------------------------------------------

struct Query {
    string field;
    string pattern;
    bool caseInsensitive;
    bool regexMode;
};

Query parseQuery(
    const string& field,
    const string& pattern,
    bool caseInsensitive,
    bool regexMode
) {
    if (field.empty()) {
        throw invalid_argument("Query field cannot be empty.");
    }

    if (pattern.empty() && !regexMode) {
        /*
         * Empty LIKE pattern is valid SQL semantics and matches only an
         * empty string. The system permits it deliberately.
         */
        return {
            field,
            pattern,
            caseInsensitive,
            regexMode
        };
    }

    if (pattern.size() > 256) {
        throw invalid_argument(
            "Pattern exceeds the maximum allowed length of 256 characters."
        );
    }

    return {
        field,
        pattern,
        caseInsensitive,
        regexMode
    };
}

// -----------------------------------------------------------------------------
// Performance benchmark
// -----------------------------------------------------------------------------

void performanceBenchmark() {
    section("Performance benchmark");

    vector<string> values;
    values.reserve(20000);

    for (int index = 0; index < 20000; ++index) {
        values.push_back(
            "user" +
            to_string(index) +
            "@example.com"
        );
    }

    const string pattern = "user%";

    const auto start =
        chrono::high_resolution_clock::now();

    size_t matches = 0;

    for (const string& value : values) {
        if (LikeMatcher::match(value, pattern)) {
            ++matches;
        }
    }

    const auto end =
        chrono::high_resolution_clock::now();

    const auto duration =
        chrono::duration_cast<chrono::microseconds>(
            end - start
        );

    cout
        << "Values: " << values.size() << "\n"
        << "Matches: " << matches << "\n"
        << "Elapsed: " << duration.count()
        << " microseconds\n";

    cout << "\nThe dynamic-programming implementation is O(n*m) per value,\n";
    cout << "where n is the text length and m is the pattern length.\n";
}

// -----------------------------------------------------------------------------
// Edge cases
// -----------------------------------------------------------------------------

void edgeCases() {
    section("Edge cases");

    const vector<pair<string, string>> cases = {
        {"", "%"},
        {"", "_"},
        {"a", "%"},
        {"a", "_"},
        {"ab", "_"},
        {"ab", "__"},
        {"database", "database"},
        {"database", "DATABASE"},
        {"hello", "h%"},
        {"hello", "%lo"},
        {"hello", "%ell%"},
        {"hello", "h___o"}
    };

    for (const auto& [text, pattern] : cases) {
        cout
            << "text=" << quoted(text)
            << " pattern=" << quoted(pattern)
            << " LIKE="
            << boolalpha
            << LikeMatcher::match(text, pattern)
            << " ILIKE="
            << LikeMatcher::match(text, pattern, true)
            << "\n";
    }
}

// -----------------------------------------------------------------------------
// Regex examples
// -----------------------------------------------------------------------------

void regexExamples() {
    section("Regular expressions");

    const vector<pair<string, string>> cases = {
        {"Order 123", R"(\d+)"},
        {"Alice", R"([A-Z][a-z]+)"},
        {"cat", R"(^cat$)"},
        {"dog", R"(cat|dog)"},
        {"user_123", R"(^[A-Za-z0-9_]+$)"},
        {"226001", R"(^\d{6}$)"}
    };

    for (const auto& [text, pattern] : cases) {
        cout
            << quoted(text)
            << " / "
            << quoted(pattern)
            << " -> "
            << boolalpha
            << RegexMatcher::search(text, pattern)
            << "\n";
    }
}

// -----------------------------------------------------------------------------
// Query demonstrations
// -----------------------------------------------------------------------------

void queryExamples(const SearchEngine& engine) {
    section("Search queries");

    cout << "\nNames beginning with A:\n";
    for (const Record& record :
         engine.like("name", "A%", true)) {
        printRecord(record);
    }

    cout << "\nEmails ending in company.com:\n";
    for (const Record& record :
         engine.like("email", "%@company.com", true)) {
        printRecord(record);
    }

    cout << "\nDepartments containing 'it':\n";
    for (const Record& record :
         engine.like("department", "%it%", true)) {
        printRecord(record);
    }

    cout << "\nRegex names beginning with A and ending in a:\n";
    for (const Record& record :
         engine.regexSearch("name", R"(^A.*a$)", true)) {
        printRecord(record);
    }

    cout << "\nCombined pattern and priority search:\n";
    for (const Record& record :
         engine.combinedSearch("a%", "%engine%", 3)) {
        printRecord(record);
    }
}

// -----------------------------------------------------------------------------
// Failure handling
// -----------------------------------------------------------------------------

void failureExamples(const SearchEngine& engine) {
    section("Failure conditions");

    try {
        engine.like("unknown_field", "%");
    }
    catch (const exception& error) {
        cout << "Caught expected field error: "
             << error.what() << "\n";
    }

    try {
        engine.regexSearch("name", "[");
    }
    catch (const exception& error) {
        cout << "Caught expected regex error: "
             << error.what() << "\n";
    }

    try {
        parseQuery(
            "name",
            string(300, 'a'),
            false,
            false
        );
    }
    catch (const exception& error) {
        cout << "Caught expected pattern-size error: "
             << error.what() << "\n";
    }
}

// -----------------------------------------------------------------------------
// SQL conceptual examples
// -----------------------------------------------------------------------------

void sqlExamples() {
    section("Equivalent SQL concepts");

    cout << "SELECT * FROM users WHERE name LIKE 'A%';\n";
    cout << "SELECT * FROM users WHERE name LIKE '%son';\n";
    cout << "SELECT * FROM users WHERE name LIKE '%data%';\n";
    cout << "SELECT * FROM users WHERE code LIKE 'AB__';\n";
    cout << "SELECT * FROM users WHERE name ILIKE 'atul%';\n";
    cout << "SELECT * FROM users WHERE name ~ '^[A-Z][a-z]+$';\n";

    cout << "\nLIKE uses % and _.\n";
    cout << "Regular expressions use a substantially larger pattern language.\n";
}

// -----------------------------------------------------------------------------
// Main case study
// -----------------------------------------------------------------------------

int main() {
    try {
        section("Pattern Matching Case Study");

        vector<Record> records = {
            {
                1,
                "Alice Sharma",
                "alice@example.com",
                "Lucknow",
                "Analytics",
                "OPEN",
                3
            },
            {
                2,
                "Aman Verma",
                "aman@company.com",
                "Delhi",
                "Engineering",
                "REVIEW",
                4
            },
            {
                3,
                "Atul Pandey",
                "atul@company.com",
                "Lucknow",
                "Security",
                "OPEN",
                5
            },
            {
                4,
                "Bob Smith",
                "bob@company.com",
                "Mumbai",
                "Management",
                "CLOSED",
                2
            },
            {
                5,
                "Bobby Jones",
                "bobby@company.org",
                "Delhi",
                "Engineering",
                "OPEN",
                4
            },
            {
                6,
                "Anita Singh",
                "anita@school.edu",
                "Jaipur",
                "Education",
                "REVIEW",
                3
            },
            {
                7,
                "David Brown",
                "david@example.net",
                "Pune",
                "Engineering",
                "OPEN",
                5
            }
        };

        validateRecords(records);

        SearchEngine engine(records);

        cout << "\nValidated records:\n";
        for (const Record& record : records) {
            printRecord(record);
        }

        queryExamples(engine);
        regexExamples();
        edgeCases();
        failureExamples(engine);
        sqlExamples();
        performanceBenchmark();

        section("Security and design notes");

        cout << "1. User input must not be concatenated into SQL commands.\n";
        cout << "2. Database drivers should receive pattern values as parameters.\n";
        cout << "3. Arbitrary regular expressions should be treated as potentially\n";
        cout << "   expensive input and subject to appropriate limits.\n";
        cout << "4. Case-insensitive matching depends on normalization and locale.\n";
        cout << "5. Leading '%' patterns commonly prevent ordinary prefix indexes\n";
        cout << "   from being used in the same way as prefix searches.\n";
        cout << "6. Large-scale search systems may require specialized indexing,\n";
        cout << "   full-text search, or search-oriented data structures.\n";

        section("Case study completed");

        return 0;
    }
    catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }
}
