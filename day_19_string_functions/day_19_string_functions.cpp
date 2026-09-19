/*
 * String Functions:
 * CONCAT, LENGTH, LOWER, UPPER, TRIM, SUBSTRING, REPLACE, POSITION
 *
 * C++17 industry-style case study:
 *
 * Customer Contact Normalization and Search Engine
 *
 * The program models a small customer-data processing system. Incoming
 * customer records may contain inconsistent capitalization, whitespace,
 * punctuation, and email formatting. The system normalizes the records,
 * extracts email components, validates basic structure, masks sensitive
 * display information, indexes normalized email values, and generates a
 * data-quality report.
 *
 * The case study deliberately uses the C++ standard library only.
 *
 * SQL correspondence:
 *
 *   CONCAT      -> concatenate fields with std::string operations
 *   LENGTH      -> std::string::size()
 *   LOWER       -> std::tolower() over characters
 *   UPPER       -> std::toupper() over characters
 *   TRIM        -> boundary whitespace removal
 *   SUBSTRING   -> std::string::substr()
 *   REPLACE     -> custom replacement operation
 *   POSITION    -> std::string::find(), converted to one-based position
 *
 * Compile:
 *   g++ -std=c++17 -O2 -Wall -Wextra -pedantic main.cpp -o string_case_study
 *
 * Run:
 *   ./string_case_study
 */

#include <algorithm>
#include <cctype>
#include <iomanip>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

using namespace std;


// -----------------------------------------------------------------------------
// 1. GENERAL UTILITY FUNCTIONS
// -----------------------------------------------------------------------------

void printSection(const string& title) {
    cout << "\n" << string(78, '=') << "\n";
    cout << title << "\n";
    cout << string(78, '=') << "\n";
}

void printSubsection(const string& title) {
    cout << "\n" << string(78, '-') << "\n";
    cout << title << "\n";
    cout << string(78, '-') << "\n";
}


// -----------------------------------------------------------------------------
// 2. SQL-LIKE STRING OPERATIONS
// -----------------------------------------------------------------------------

// CONCAT
//
// SQL concatenation combines multiple values into one string. C++ uses
// std::string concatenation, so this helper provides a clear abstraction.
string sqlConcat(initializer_list<string_view> values) {
    string result;

    size_t totalLength = 0;

    for (const auto value : values) {
        totalLength += value.size();
    }

    result.reserve(totalLength);

    for (const auto value : values) {
        result.append(value);
    }

    return result;
}


// LENGTH
//
// std::string::size() returns the number of bytes in the string. For ordinary
// ASCII data this matches character count. For UTF-8 text, byte count and
// Unicode character count can differ.
size_t sqlLength(string_view value) {
    return value.size();
}


// LOWER
//
// std::tolower works on unsigned char values safely for the basic character
// set. Full Unicode case mapping requires a Unicode-aware library and is not
// attempted in this standard-library-only case study.
string sqlLower(string_view value) {
    string result(value);

    transform(
        result.begin(),
        result.end(),
        result.begin(),
        [](unsigned char character) {
            return static_cast<char>(tolower(character));
        }
    );

    return result;
}


// UPPER
string sqlUpper(string_view value) {
    string result(value);

    transform(
        result.begin(),
        result.end(),
        result.begin(),
        [](unsigned char character) {
            return static_cast<char>(toupper(character));
        }
    );

    return result;
}


// TRIM
//
// Removes whitespace from both boundaries while preserving whitespace inside
// the value.
string sqlTrim(string_view value) {
    size_t start = 0;

    while (
        start < value.size() &&
        isspace(static_cast<unsigned char>(value[start]))
    ) {
        ++start;
    }

    if (start == value.size()) {
        return "";
    }

    size_t end = value.size();

    while (
        end > start &&
        isspace(static_cast<unsigned char>(value[end - 1]))
    ) {
        --end;
    }

    return string(value.substr(start, end - start));
}


// SUBSTRING
//
// SQL-style positions are normally one-based. C++ substr() uses a zero-based
// starting index, so the conversion is explicit here.
string sqlSubstring(
    string_view value,
    size_t startPosition,
    optional<size_t> length = nullopt
) {
    if (startPosition == 0) {
        throw invalid_argument(
            "SQL-style substring positions must start at 1."
        );
    }

    const size_t zeroBasedStart = startPosition - 1;

    if (zeroBasedStart >= value.size()) {
        return "";
    }

    if (length.has_value()) {
        return string(value.substr(zeroBasedStart, length.value()));
    }

    return string(value.substr(zeroBasedStart));
}


// REPLACE
//
// Replaces every non-overlapping occurrence.
string sqlReplace(
    string_view value,
    string_view oldValue,
    string_view newValue
) {
    if (oldValue.empty()) {
        return string(value);
    }

    string result;
    size_t currentPosition = 0;

    while (currentPosition < value.size()) {
        const size_t matchPosition =
            value.find(oldValue, currentPosition);

        if (matchPosition == string_view::npos) {
            result.append(value.substr(currentPosition));
            break;
        }

        result.append(
            value.substr(
                currentPosition,
                matchPosition - currentPosition
            )
        );

        result.append(newValue);

        currentPosition =
            matchPosition + oldValue.size();
    }

    return result;
}


// POSITION
//
// Returns a one-based position, with 0 meaning "not found".
size_t sqlPosition(
    string_view needle,
    string_view haystack
) {
    const size_t position = haystack.find(needle);

    if (position == string_view::npos) {
        return 0;
    }

    return position + 1;
}


// -----------------------------------------------------------------------------
// 3. BASIC STRING FUNCTION DEMONSTRATIONS
// -----------------------------------------------------------------------------

void demonstrateBasicFunctions() {
    printSection("1. Basic string-function operations");

    const string firstName = "Atul";
    const string lastName = "Pandey";

    const string fullName =
        sqlConcat({firstName, " ", lastName});

    cout << "CONCAT: " << fullName << '\n';
    cout << "LENGTH: " << sqlLength(fullName) << '\n';
    cout << "LOWER: " << sqlLower(fullName) << '\n';
    cout << "UPPER: " << sqlUpper(fullName) << '\n';
    cout << "TRIM: "
         << sqlTrim("   Atul Pandey   ")
         << '\n';
    cout << "SUBSTRING: "
         << sqlSubstring("DATABASE", 1, 4)
         << '\n';
    cout << "REPLACE: "
         << sqlReplace("abc-abc-abc", "-", "_")
         << '\n';
    cout << "POSITION: "
         << sqlPosition("BASE", "DATABASE")
         << '\n';
}


// -----------------------------------------------------------------------------
// 4. CUSTOMER DATA MODEL
// -----------------------------------------------------------------------------

struct Customer {
    int id;
    string firstName;
    string lastName;
    string email;
    string phone;
    string city;
};

struct NormalizedCustomer {
    int id;
    string displayName;
    string email;
    string phone;
    string city;
    string emailDomain;
    size_t nameLength;
    size_t atPosition;
    bool emailLooksValid;
};


// -----------------------------------------------------------------------------
// 5. PHONE NORMALIZATION
// -----------------------------------------------------------------------------

string normalizePhone(string_view phone) {
    string result = sqlTrim(phone);

    const vector<string> removableCharacters = {
        " ", "-", "(", ")", "."
    };

    for (const string& character : removableCharacters) {
        result = sqlReplace(result, character, "");
    }

    return result;
}


// -----------------------------------------------------------------------------
// 6. BASIC EMAIL VALIDATION
// -----------------------------------------------------------------------------

bool looksLikeEmail(string_view email) {
    const string cleaned = sqlLower(sqlTrim(email));

    if (cleaned.empty()) {
        return false;
    }

    const size_t atPosition =
        sqlPosition("@", cleaned);

    // There must be text before @ and after @.
    if (atPosition <= 1 || atPosition >= cleaned.size()) {
        return false;
    }

    // A basic validation rule rejects spaces.
    if (sqlPosition(" ", cleaned) != 0) {
        return false;
    }

    const string domain =
        sqlSubstring(cleaned, atPosition + 1);

    // This is deliberately lightweight. It does not attempt the complete
    // email-address grammar.
    return !domain.empty() &&
           sqlPosition(".", domain) != 0;
}


// -----------------------------------------------------------------------------
// 7. NORMALIZE CUSTOMER
// -----------------------------------------------------------------------------

NormalizedCustomer normalizeCustomer(
    const Customer& customer
) {
    const string trimmedFirstName =
        sqlTrim(customer.firstName);

    const string trimmedLastName =
        sqlTrim(customer.lastName);

    const string displayName =
        sqlUpper(
            sqlConcat({
                trimmedFirstName,
                " ",
                trimmedLastName
            })
        );

    const string normalizedEmail =
        sqlLower(sqlTrim(customer.email));

    const size_t atPosition =
        sqlPosition("@", normalizedEmail);

    string emailDomain;

    if (atPosition != 0) {
        emailDomain =
            sqlSubstring(
                normalizedEmail,
                atPosition + 1
            );
    }

    return {
        customer.id,
        displayName,
        normalizedEmail,
        normalizePhone(customer.phone),
        sqlTrim(customer.city),
        emailDomain,
        sqlLength(displayName),
        atPosition,
        looksLikeEmail(normalizedEmail)
    };
}


// -----------------------------------------------------------------------------
// 8. DISPLAY CUSTOMER
// -----------------------------------------------------------------------------

void printCustomer(const NormalizedCustomer& customer) {
    cout << left
         << setw(5) << customer.id
         << setw(24) << customer.displayName
         << setw(32) << customer.email
         << setw(18) << customer.phone
         << setw(16) << customer.city
         << '\n';
}


// -----------------------------------------------------------------------------
// 9. EMAIL MASKING
// -----------------------------------------------------------------------------

string maskEmail(string_view email) {
    const string cleaned =
        sqlLower(sqlTrim(email));

    if (!looksLikeEmail(cleaned)) {
        return "[invalid email]";
    }

    const size_t atPosition =
        sqlPosition("@", cleaned);

    const string username =
        sqlSubstring(
            cleaned,
            1,
            atPosition - 1
        );

    const string domain =
        sqlSubstring(
            cleaned,
            atPosition + 1
        );

    if (username.size() <= 2) {
        return "**@" + domain;
    }

    const string firstCharacter =
        sqlSubstring(username, 1, 1);

    const string lastCharacter =
        sqlSubstring(
            username,
            username.size(),
            1
        );

    const size_t hiddenLength =
        max<size_t>(username.size() - 2, 1);

    return firstCharacter +
           string(hiddenLength, '*') +
           lastCharacter +
           "@" +
           domain;
}


// -----------------------------------------------------------------------------
// 10. SEARCH INDEX
// -----------------------------------------------------------------------------

class CustomerSearchIndex {
private:
    // The normalized email is the key because email comparisons should not
    // depend on accidental capitalization or surrounding whitespace.
    unordered_map<string, vector<int>> emailToCustomerIds;

public:
    void add(const NormalizedCustomer& customer) {
        const string key =
            sqlLower(sqlTrim(customer.email));

        emailToCustomerIds[key].push_back(customer.id);
    }

    vector<int> findByEmail(string_view email) const {
        const string key =
            sqlLower(sqlTrim(email));

        const auto iterator =
            emailToCustomerIds.find(key);

        if (iterator == emailToCustomerIds.end()) {
            return {};
        }

        return iterator->second;
    }
};


// -----------------------------------------------------------------------------
// 11. DATA QUALITY REPORT
// -----------------------------------------------------------------------------

struct DataQualityReport {
    size_t totalRecords = 0;
    size_t missingEmail = 0;
    size_t invalidEmail = 0;
    size_t validEmail = 0;
    size_t emptyName = 0;
};

DataQualityReport buildDataQualityReport(
    const vector<NormalizedCustomer>& customers
) {
    DataQualityReport report;
    report.totalRecords = customers.size();

    for (const auto& customer : customers) {
        if (customer.displayName.empty()) {
            ++report.emptyName;
        }

        if (customer.email.empty()) {
            ++report.missingEmail;
            continue;
        }

        if (customer.emailLooksValid) {
            ++report.validEmail;
        } else {
            ++report.invalidEmail;
        }
    }

    return report;
}


// -----------------------------------------------------------------------------
// 12. CUSTOMER REPORT
// -----------------------------------------------------------------------------

void printQualityReport(
    const DataQualityReport& report
) {
    cout << "\nData-quality report\n";
    cout << "Total records:       " << report.totalRecords << '\n';
    cout << "Missing email:       " << report.missingEmail << '\n';
    cout << "Valid email:         " << report.validEmail << '\n';
    cout << "Invalid email:       " << report.invalidEmail << '\n';
    cout << "Empty display name:  " << report.emptyName << '\n';
}


// -----------------------------------------------------------------------------
// 13. SUBSTRING-BASED URL PARSING
// -----------------------------------------------------------------------------

struct ParsedUrl {
    string protocol;
    string host;
};

ParsedUrl parseUrl(string_view url) {
    const size_t protocolPosition =
        sqlPosition("://", url);

    if (protocolPosition == 0) {
        throw invalid_argument(
            "URL does not contain a protocol separator."
        );
    }

    const string protocol =
        sqlSubstring(
            url,
            1,
            protocolPosition - 1
        );

    const size_t hostStart =
        protocolPosition + 3;

    const string remaining =
        sqlSubstring(url, hostStart);

    const size_t pathPosition =
        sqlPosition("/", remaining);

    string host;

    if (pathPosition == 0) {
        host = remaining;
    } else {
        host =
            sqlSubstring(
                remaining,
                1,
                pathPosition - 1
            );
    }

    return {protocol, host};
}


// -----------------------------------------------------------------------------
// 14. UNIT TESTS
// -----------------------------------------------------------------------------

void requireEqual(
    const string& actual,
    const string& expected,
    string_view testName
) {
    if (actual != expected) {
        throw runtime_error(
            string(testName) +
            ": expected [" +
            expected +
            "] but received [" +
            actual +
            "]"
        );
    }
}

void requireEqual(
    size_t actual,
    size_t expected,
    string_view testName
) {
    if (actual != expected) {
        throw runtime_error(
            string(testName) +
            ": expected [" +
            to_string(expected) +
            "] but received [" +
            to_string(actual) +
            "]"
        );
    }
}

void runTests() {
    printSection("2. Automated tests");

    requireEqual(
        sqlConcat({"A", "B"}),
        "AB",
        "CONCAT"
    );

    requireEqual(
        sqlLength("ABC"),
        static_cast<size_t>(3),
        "LENGTH"
    );

    requireEqual(
        sqlLower("ABC"),
        "abc",
        "LOWER"
    );

    requireEqual(
        sqlUpper("abc"),
        "ABC",
        "UPPER"
    );

    requireEqual(
        sqlTrim("  ABC  "),
        "ABC",
        "TRIM"
    );

    requireEqual(
        sqlSubstring("DATABASE", 1, 4),
        "DATA",
        "SUBSTRING"
    );

    requireEqual(
        sqlSubstring("DATABASE", 5, 4),
        "BASE",
        "SUBSTRING later"
    );

    requireEqual(
        sqlReplace("a-b-c", "-", "_"),
        "a_b_c",
        "REPLACE"
    );

    requireEqual(
        sqlPosition("DATA", "DATABASE"),
        static_cast<size_t>(1),
        "POSITION"
    );

    requireEqual(
        sqlPosition("BASE", "DATABASE"),
        static_cast<size_t>(5),
        "POSITION later"
    );

    requireEqual(
        sqlPosition("XYZ", "DATABASE"),
        static_cast<size_t>(0),
        "POSITION missing"
    );

    bool exceptionRaised = false;

    try {
        sqlSubstring("ABC", 0, 1);
    } catch (const invalid_argument&) {
        exceptionRaised = true;
    }

    if (!exceptionRaised) {
        throw runtime_error(
            "SUBSTRING should reject a zero start position."
        );
    }

    cout << "All tests passed.\n";
}


// -----------------------------------------------------------------------------
// 15. MAIN INDUSTRY CASE STUDY
// -----------------------------------------------------------------------------

int main() {
    try {
        demonstrateBasicFunctions();

        runTests();

        printSection(
            "3. Industry case study: customer contact normalization"
        );

        const vector<Customer> rawCustomers = {
            {
                1001,
                "  Atul ",
                " Pandey ",
                " ATUL.PANDEY@EXAMPLE.COM ",
                "+91 987-654-3210",
                " Lucknow "
            },
            {
                1002,
                "ANITA",
                "Sharma",
                "anita@example.com",
                "(555) 123-4567",
                "Delhi"
            },
            {
                1003,
                " Rahul ",
                " VERMA ",
                "RAHUL@EXAMPLE.COM",
                "555-555-1010",
                " Mumbai "
            },
            {
                1004,
                "Priya",
                "Singh",
                "",
                "555.100.2000",
                "Pune"
            },
            {
                1005,
                "Invalid",
                "Customer",
                "invalid-email",
                "555-000-0000",
                "Jaipur"
            }
        };

        vector<NormalizedCustomer> normalizedCustomers;

        normalizedCustomers.reserve(rawCustomers.size());

        for (const Customer& customer : rawCustomers) {
            normalizedCustomers.push_back(
                normalizeCustomer(customer)
            );
        }

        printSubsection("Normalized customer records");

        cout << left
             << setw(5) << "ID"
             << setw(24) << "DISPLAY NAME"
             << setw(32) << "EMAIL"
             << setw(18) << "PHONE"
             << setw(16) << "CITY"
             << '\n';

        cout << string(95, '-') << '\n';

        for (const auto& customer : normalizedCustomers) {
            printCustomer(customer);
        }

        printSubsection("Email analysis");

        for (const auto& customer : normalizedCustomers) {
            cout << "Customer " << customer.id << '\n';
            cout << "  Email:       " << customer.email << '\n';
            cout << "  Length:      "
                 << sqlLength(customer.email)
                 << '\n';
            cout << "  @ position:  "
                 << customer.atPosition
                 << '\n';
            cout << "  Domain:      "
                 << customer.emailDomain
                 << '\n';
            cout << "  Valid shape: "
                 << boolalpha
                 << customer.emailLooksValid
                 << '\n';
            cout << "  Masked:      "
                 << maskEmail(customer.email)
                 << '\n';
        }

        printSubsection("Building normalized search index");

        CustomerSearchIndex searchIndex;

        for (const auto& customer : normalizedCustomers) {
            if (customer.emailLooksValid) {
                searchIndex.add(customer);
            }
        }

        const vector<int> searchResults =
            searchIndex.findByEmail(
                "  atul.pandey@example.com "
            );

        cout << "Search for normalized email returned IDs: ";

        for (const int id : searchResults) {
            cout << id << ' ';
        }

        cout << '\n';

        printSubsection("Data-quality analysis");

        const DataQualityReport report =
            buildDataQualityReport(normalizedCustomers);

        printQualityReport(report);

        printSubsection("URL parsing using POSITION and SUBSTRING");

        const vector<string> urls = {
            "https://example.com/products",
            "http://localhost:3000/api/users",
            "https://company.org"
        };

        for (const string& url : urls) {
            const ParsedUrl parsed = parseUrl(url);

            cout << "URL:      " << url << '\n';
            cout << "Protocol: " << parsed.protocol << '\n';
            cout << "Host:     " << parsed.host << '\n';
        }

        printSubsection("Edge cases");

        const vector<string> edgeValues = {
            "",
            " ",
            "   ",
            "A",
            "AAAAAAAA",
            "  A  B  "
        };

        for (const string& value : edgeValues) {
            cout << "Input: "
                 << quoted(value)
                 << " | LENGTH="
                 << sqlLength(value)
                 << " | TRIM="
                 << quoted(sqlTrim(value))
                 << " | LOWER="
                 << quoted(sqlLower(value))
                 << " | UPPER="
                 << quoted(sqlUpper(value))
                 << '\n';
        }

        printSubsection("Performance considerations");

        cout << R"(
The search index uses unordered_map so average lookup is approximately O(1)
for a normalized email key.

Normalization of each string is O(n), where n is the string length.

REPLACE is O(n) for ordinary inputs, although repeated replacement passes
can make a pipeline approximately O(k*n), where k is the number of separate
replacement operations.

SUBSTRING and related operations can require allocation when a new std::string
is returned. string_view can avoid copying when only temporary read access is
needed.

For large production datasets, the database may perform these operations over
millions of rows. Persisting normalized search keys or using suitable database
indexes can reduce repeated computation.

C++ std::string size() measures bytes, not Unicode grapheme clusters. Full
internationalized text processing requires a Unicode-aware design.
)";

        printSubsection("Security considerations");

        cout << R"(
String transformation is not a substitute for security controls.

When these normalized values are eventually used in SQL:
    - use parameterized queries;
    - do not concatenate untrusted values into SQL statements;
    - validate input according to the business requirement;
    - avoid logging unnecessary sensitive data;
    - mask personal information in display output;
    - distinguish normalization from authorization.

Email validation based on POSITION and SUBSTRING only checks basic structure.
It does not establish ownership, existence, or deliverability.
)";

        printSubsection("Completed case study");

        cout << R"(
The system has demonstrated:

    CONCAT      -> constructed customer display names
    LENGTH      -> measured names and emails
    LOWER       -> normalized email values
    UPPER       -> standardized display names
    TRIM        -> removed input boundary whitespace
    SUBSTRING   -> extracted usernames, domains, and URL components
    REPLACE     -> normalized phone numbers and text
    POSITION    -> located delimiters and searched strings

The same conceptual transformations appear in SQL reporting, ETL pipelines,
customer-data platforms, search systems, validation services, APIs, and
database migration processes.
)";

        return 0;
    }
    catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }
}
