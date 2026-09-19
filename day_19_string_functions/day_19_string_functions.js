/*
 * String Functions:
 * CONCAT, LENGTH, LOWER, UPPER, TRIM, SUBSTRING, REPLACE, POSITION
 *
 * This standalone JavaScript file demonstrates SQL-style string operations
 * through browser/Node-compatible JavaScript.
 *
 * JavaScript does not provide SQL itself. The functions below model the
 * corresponding SQL concepts and demonstrate how the same transformations
 * can be implemented at the application layer.
 *
 * SQL dialect differences are important:
 *   CONCAT(...)        -> direct SQL function in several databases
 *   LENGTH(...)        -> common SQL function
 *   LOWER(...)         -> common SQL function
 *   UPPER(...)         -> common SQL function
 *   TRIM(...)          -> common SQL function
 *   SUBSTRING(...)     -> common SQL operation
 *   REPLACE(...)       -> common SQL function
 *   POSITION(...)      -> standard SQL-style substring search
 *
 * JavaScript uses:
 *   + / template literals
 *   .length
 *   .toLowerCase()
 *   .toUpperCase()
 *   .trim()
 *   .substring() / .slice()
 *   .replaceAll()
 *   .indexOf()
 */

"use strict";

// -----------------------------------------------------------------------------
// 1. OUTPUT HELPERS
// -----------------------------------------------------------------------------

function section(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}

function subsection(title) {
    console.log("\n" + "-".repeat(78));
    console.log(title);
    console.log("-".repeat(78));
}


// -----------------------------------------------------------------------------
// 2. BASIC STRING OPERATIONS
// -----------------------------------------------------------------------------

section("1. JavaScript string fundamentals");

const firstName = "Atul";
const lastName = "Pandey";

// JavaScript can concatenate strings with +.
const fullName = firstName + " " + lastName;

// Template literals are convenient when combining several values.
const formattedName = `${firstName} ${lastName}`;

console.log("First name:", firstName);
console.log("Last name:", lastName);
console.log("Full name:", fullName);
console.log("Formatted name:", formattedName);

// JavaScript string length is zero-based in indexing but counts characters
// represented by UTF-16 code units. This matters for some Unicode characters.
console.log("Length:", fullName.length);


// -----------------------------------------------------------------------------
// 3. SQL-STYLE HELPER FUNCTIONS
// -----------------------------------------------------------------------------

section("2. SQL-style JavaScript helper functions");

function sqlConcat(...values) {
    // This implementation treats null/undefined as empty values.
    // Actual SQL NULL behavior differs among database engines/functions.
    return values
        .map(value => value == null ? "" : String(value))
        .join("");
}

function sqlLength(value) {
    if (value == null) {
        return null;
    }

    return String(value).length;
}

function sqlLower(value) {
    if (value == null) {
        return null;
    }

    return String(value).toLowerCase();
}

function sqlUpper(value) {
    if (value == null) {
        return null;
    }

    return String(value).toUpperCase();
}

function sqlTrim(value, characters = null) {
    if (value == null) {
        return null;
    }

    const text = String(value);

    if (characters === null) {
        return text.trim();
    }

    // JavaScript trim() does not directly support a character set.
    // Build a boundary-removal expression for demonstration.
    const escaped = characters.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pattern = new RegExp(`^[${escaped}]+|[${escaped}]+$`, "g");

    return text.replace(pattern, "");
}

function sqlSubstring(value, start, length = null) {
    if (value == null) {
        return null;
    }

    if (!Number.isInteger(start) || start < 1) {
        throw new RangeError("SQL substring positions normally start at 1.");
    }

    if (length !== null) {
        if (!Number.isInteger(length) || length < 0) {
            throw new RangeError("Substring length must be a non-negative integer.");
        }

        return String(value).substring(start - 1, start - 1 + length);
    }

    return String(value).substring(start - 1);
}

function sqlReplace(value, oldValue, newValue) {
    if (value == null) {
        return null;
    }

    return String(value).split(oldValue).join(newValue);
}

function sqlPosition(needle, haystack) {
    if (haystack == null) {
        return null;
    }

    const index = String(haystack).indexOf(String(needle));

    // SQL POSITION-style result is represented as one-based.
    return index === -1 ? 0 : index + 1;
}


// -----------------------------------------------------------------------------
// 4. BASIC DEMONSTRATIONS
// -----------------------------------------------------------------------------

subsection("Basic function demonstrations");

console.log("CONCAT:", sqlConcat("SQL", " ", "String", " ", "Functions"));
console.log("LENGTH:", sqlLength("Atul Pandey"));
console.log("LOWER:", sqlLower("AtUl PaNdEy"));
console.log("UPPER:", sqlUpper("AtUl PaNdEy"));
console.log("TRIM:", JSON.stringify(sqlTrim("   Atul Pandey   ")));
console.log("SUBSTRING:", sqlSubstring("DATABASE", 1, 4));
console.log("REPLACE:", sqlReplace("abc-abc-abc", "-", "_"));
console.log("POSITION:", sqlPosition("BASE", "DATABASE"));


// -----------------------------------------------------------------------------
// 5. CONCAT
// -----------------------------------------------------------------------------

section("3. CONCAT");

const customer = {
    firstName: "Anita",
    middleName: "K.",
    lastName: "Sharma"
};

const displayName = sqlConcat(
    customer.firstName,
    " ",
    customer.middleName,
    " ",
    customer.lastName
);

console.log("Display name:", displayName);

const product = {
    brand: "Nexaris",
    name: "Analytics Platform",
    version: "2.5"
};

const productLabel = sqlConcat(
    product.brand,
    " ",
    product.name,
    " v",
    product.version
);

console.log("Product label:", productLabel);

console.log("NULL-like example:", JSON.stringify(
    sqlConcat("Atul", null, "Pandey")
));


// -----------------------------------------------------------------------------
// 6. LENGTH
// -----------------------------------------------------------------------------

section("4. LENGTH");

const lengthExamples = [
    "",
    "A",
    "Atul",
    "Atul Pandey",
    "   padded text   ",
    "café",
    "नमस्ते"
];

for (const value of lengthExamples) {
    console.log(JSON.stringify(value), "=>", sqlLength(value));
}

console.log(
    "\nJavaScript length uses UTF-16 code units. For Unicode-aware character",
    "counting, Array.from(value).length or [...value].length can be useful."
);

const unicodeText = "😀";

console.log("UTF-16 length of 😀:", unicodeText.length);
console.log("Code-point count of 😀:", Array.from(unicodeText).length);


// -----------------------------------------------------------------------------
// 7. LOWER AND UPPER
// -----------------------------------------------------------------------------

section("5. LOWER and UPPER");

const mixedText = "AtUl PaNdEy";

console.log("Original:", mixedText);
console.log("LOWER:", sqlLower(mixedText));
console.log("UPPER:", sqlUpper(mixedText));

const emails = [
    "ATUL@EXAMPLE.COM",
    "Atul@Example.Com",
    "atul@example.com"
];

for (const email of emails) {
    console.log(email, "=>", sqlLower(email));
}


// -----------------------------------------------------------------------------
// 8. TRIM
// -----------------------------------------------------------------------------

section("6. TRIM");

const dirtyValues = [
    "  Atul Pandey  ",
    "\tAtul Pandey\t",
    "\nAtul Pandey\n",
    "-----Atul Pandey-----",
    "...Atul Pandey..."
];

for (const value of dirtyValues) {
    console.log(JSON.stringify(value), "=>", JSON.stringify(sqlTrim(value)));
}

console.log(
    "Custom character trim:",
    sqlTrim("###Atul###", "#")
);

console.log(
    "\nTRIM affects boundaries. It does not normally remove spaces inside",
    "the string."
);


// -----------------------------------------------------------------------------
// 9. SUBSTRING
// -----------------------------------------------------------------------------

section("7. SUBSTRING");

const databaseWord = "DATABASE";

const substringCases = [
    [1, 4],
    [5, 4],
    [2, 3],
    [4, null]
];

for (const [start, length] of substringCases) {
    console.log(
        `SUBSTRING(${databaseWord}, ${start}, ${length}) =`,
        sqlSubstring(databaseWord, start, length)
    );
}

console.log(
    "\nSQL positions are normally one-based, while JavaScript indexes are",
    "zero-based."
);

try {
    sqlSubstring("DATABASE", 0, 3);
} catch (error) {
    console.log("Expected validation error:", error.message);
}


// -----------------------------------------------------------------------------
// 10. REPLACE
// -----------------------------------------------------------------------------

section("8. REPLACE");

const replacements = [
    ["Hello World", "World", "SQL"],
    ["abc-abc-abc", "abc", "XYZ"],
    ["user@example.com", "@example.com", "@company.com"],
    ["A B C", " ", "_"]
];

for (const [original, oldValue, newValue] of replacements) {
    console.log(
        JSON.stringify(original),
        "=>",
        JSON.stringify(sqlReplace(original, oldValue, newValue))
    );
}

console.log(
    "\nREPLACE can affect every occurrence. A transformation should be",
    "designed with the complete input structure in mind."
);


// -----------------------------------------------------------------------------
// 11. POSITION
// -----------------------------------------------------------------------------

section("9. POSITION");

const positionCases = [
    ["SQL", "SQL String Functions"],
    ["String", "SQL String Functions"],
    ["Functions", "SQL String Functions"],
    ["Missing", "SQL String Functions"],
    ["", "SQL String Functions"]
];

for (const [needle, haystack] of positionCases) {
    console.log(
        `POSITION(${JSON.stringify(needle)} IN ${JSON.stringify(haystack)}) =`,
        sqlPosition(needle, haystack)
    );
}


// -----------------------------------------------------------------------------
// 12. COMPOSITION
// -----------------------------------------------------------------------------

section("10. Combining string functions");

const rawEmail = "  ATUL.PANDEY@EXAMPLE.COM  ";

const normalizedEmail = sqlLower(sqlTrim(rawEmail));

const atPosition = sqlPosition("@", normalizedEmail);

const username = atPosition > 0
    ? sqlSubstring(normalizedEmail, 1, atPosition - 1)
    : null;

const domain = atPosition > 0
    ? sqlSubstring(normalizedEmail, atPosition + 1)
    : null;

console.log("Raw email:", JSON.stringify(rawEmail));
console.log("Normalized:", normalizedEmail);
console.log("Username:", username);
console.log("Domain:", domain);


// -----------------------------------------------------------------------------
// 13. PRACTICAL CONTACT NORMALIZATION
// -----------------------------------------------------------------------------

section("11. Contact normalization");

function normalizePhone(phone) {
    if (phone == null) {
        return null;
    }

    let normalized = sqlTrim(phone);

    for (const character of [" ", "-", "(", ")", "."]) {
        normalized = sqlReplace(normalized, character, "");
    }

    return normalized;
}

function normalizeContact(contact) {
    return {
        name: sqlTrim(contact.name) ?? "",
        email: sqlLower(sqlTrim(contact.email)) ?? "",
        phone: normalizePhone(contact.phone) ?? ""
    };
}

const contacts = [
    {
        name: "  Anita Sharma ",
        email: " ANITA@EXAMPLE.COM ",
        phone: "+91 987-654-3210"
    },
    {
        name: "Rahul Verma",
        email: "RAHUL@EXAMPLE.COM",
        phone: "(555) 123-4567"
    }
];

for (const contact of contacts) {
    console.log("Before:", contact);
    console.log("After :", normalizeContact(contact));
}


// -----------------------------------------------------------------------------
// 14. EMAIL VALIDATION
// -----------------------------------------------------------------------------

section("12. Lightweight email validation");

function looksLikeEmail(email) {
    if (email == null) {
        return false;
    }

    const cleaned = sqlLower(sqlTrim(email));

    if (!cleaned) {
        return false;
    }

    const atPosition = sqlPosition("@", cleaned);

    if (atPosition <= 1 || atPosition >= cleaned.length) {
        return false;
    }

    if (sqlPosition(" ", cleaned) > 0) {
        return false;
    }

    const domain = sqlSubstring(cleaned, atPosition + 1);

    if (!domain || sqlPosition(".", domain) <= 0) {
        return false;
    }

    return true;
}

const emailCandidates = [
    "atul@example.com",
    " ATUL@EXAMPLE.COM ",
    "missing-at-symbol.example.com",
    "@example.com",
    "user@",
    "user example@example.com",
    "user@example"
];

for (const email of emailCandidates) {
    console.log(JSON.stringify(email), "=>", looksLikeEmail(email));
}

console.log(
    "\nThis checks basic structure only. It does not prove that an email",
    "address exists or can receive mail."
);


// -----------------------------------------------------------------------------
// 15. SEARCH USING NORMALIZED VALUES
// -----------------------------------------------------------------------------

section("13. Case-normalized search");

const users = [
    { id: 1, name: "Atul Pandey", email: "ATUL@EXAMPLE.COM" },
    { id: 2, name: "Anita Sharma", email: "ANITA@EXAMPLE.COM" },
    { id: 3, name: "Rahul Verma", email: "RAHUL@EXAMPLE.COM" }
];

function findUserByEmail(users, searchEmail) {
    const normalizedSearch = sqlLower(sqlTrim(searchEmail));

    return users.filter(user =>
        sqlLower(sqlTrim(user.email)) === normalizedSearch
    );
}

console.log(
    findUserByEmail(users, "  atul@example.com ")
);


// -----------------------------------------------------------------------------
// 16. DATA MASKING
// -----------------------------------------------------------------------------

section("14. Substring-based masking");

function maskEmail(email) {
    const cleaned = sqlLower(sqlTrim(email));

    if (!looksLikeEmail(cleaned)) {
        return "[invalid email]";
    }

    const atPosition = sqlPosition("@", cleaned);
    const username = sqlSubstring(cleaned, 1, atPosition - 1);
    const domain = sqlSubstring(cleaned, atPosition + 1);

    if (username.length <= 2) {
        return `**@${domain}`;
    }

    const firstCharacter = sqlSubstring(username, 1, 1);
    const lastCharacter = sqlSubstring(username, username.length, 1);
    const hiddenLength = Math.max(username.length - 2, 1);

    return `${firstCharacter}${"*".repeat(hiddenLength)}${lastCharacter}@${domain}`;
}

for (const email of [
    "atul.pandey@example.com",
    "ab@example.com",
    "a@example.com"
]) {
    console.log(email, "=>", maskEmail(email));
}


// -----------------------------------------------------------------------------
// 17. URL/PATH PROCESSING
// -----------------------------------------------------------------------------

section("15. Practical URL-like processing");

function extractProtocol(url) {
    const separatorPosition = sqlPosition("://", url);

    if (separatorPosition === 0) {
        return null;
    }

    return sqlSubstring(url, 1, separatorPosition - 1);
}

function extractHost(url) {
    const protocolPosition = sqlPosition("://", url);

    if (protocolPosition === 0) {
        return null;
    }

    const hostStart = protocolPosition + 3;
    const pathPosition = sqlPosition("/", sqlSubstring(url, hostStart));

    if (pathPosition === 0) {
        return sqlSubstring(url, hostStart);
    }

    return sqlSubstring(
        url,
        hostStart,
        pathPosition - 1
    );
}

const urls = [
    "https://example.com/products",
    "http://localhost:3000/api/users",
    "https://company.org"
];

for (const url of urls) {
    console.log(
        url,
        "protocol=",
        extractProtocol(url),
        "host=",
        extractHost(url)
    );
}


// -----------------------------------------------------------------------------
// 18. PERFORMANCE COMPARISON
// -----------------------------------------------------------------------------

section("16. Performance considerations");

const largeSample = Array.from(
    { length: 100000 },
    (_, index) => `USER${index}@EXAMPLE.COM`
);

console.time("lowercase normalization");

let normalizedCount = 0;

for (const email of largeSample) {
    const normalized = sqlLower(email);
    if (normalized.includes("@example.com")) {
        normalizedCount++;
    }
}

console.timeEnd("lowercase normalization");

console.log("Matching records:", normalizedCount);

console.log(
    "\nRepeated transformations over large datasets have a cost. In a",
    "database, indexed normalized columns or functional indexes may be",
    "preferable to repeatedly transforming millions of rows."
);


// -----------------------------------------------------------------------------
// 19. ERROR HANDLING
// -----------------------------------------------------------------------------

section("17. Error handling");

const invalidSubstringInputs = [
    ["ABC", 0, 2],
    ["ABC", -1, 2],
    ["ABC", 1, -2]
];

for (const [value, start, length] of invalidSubstringInputs) {
    try {
        console.log(sqlSubstring(value, start, length));
    } catch (error) {
        console.log(
            `Invalid substring (${start}, ${length}):`,
            error.message
        );
    }
}


// -----------------------------------------------------------------------------
// 20. EDGE CASES
// -----------------------------------------------------------------------------

section("18. Edge cases");

const edgeCases = [
    "",
    " ",
    "   ",
    "A",
    "AAAAAAAA",
    null,
    undefined
];

for (const value of edgeCases) {
    console.log({
        value,
        length: sqlLength(value),
        lower: sqlLower(value),
        upper: sqlUpper(value),
        trim: sqlTrim(value)
    });
}


// -----------------------------------------------------------------------------
// 21. JAVASCRIPT-SPECIFIC REPLACE BEHAVIOR
// -----------------------------------------------------------------------------

section("19. JavaScript replace versus SQL REPLACE");

const originalText = "one two two three two";

console.log(
    "replace() with string:",
    originalText.replace("two", "TWO")
);

console.log(
    "replaceAll():",
    originalText.replaceAll("two", "TWO")
);

console.log(
    "SQL-style helper:",
    sqlReplace(originalText, "two", "TWO")
);

console.log(
    "\nJavaScript String.prototype.replace() with a plain string replaces",
    "the first occurrence. SQL REPLACE normally replaces all matching",
    "occurrences. The distinction is important."
);


// -----------------------------------------------------------------------------
// 22. TESTS
// -----------------------------------------------------------------------------

section("20. Executable tests");

function assertEqual(actual, expected, description) {
    if (actual !== expected) {
        throw new Error(
            `${description}: expected ${JSON.stringify(expected)}, ` +
            `received ${JSON.stringify(actual)}`
        );
    }
}

function runTests() {
    assertEqual(sqlConcat("A", "B"), "AB", "CONCAT");
    assertEqual(sqlConcat("A", null, "B"), "AB", "CONCAT null handling");
    assertEqual(sqlLength("ABC"), 3, "LENGTH");
    assertEqual(sqlLength(""), 0, "empty LENGTH");
    assertEqual(sqlLength(null), null, "NULL LENGTH");
    assertEqual(sqlLower("ABC"), "abc", "LOWER");
    assertEqual(sqlUpper("abc"), "ABC", "UPPER");
    assertEqual(sqlTrim("  ABC  "), "ABC", "TRIM");
    assertEqual(sqlTrim("###ABC###", "#"), "ABC", "custom TRIM");
    assertEqual(sqlSubstring("DATABASE", 1, 4), "DATA", "SUBSTRING");
    assertEqual(sqlSubstring("DATABASE", 5, 4), "BASE", "SUBSTRING later");
    assertEqual(sqlReplace("a-b-c", "-", "_"), "a_b_c", "REPLACE");
    assertEqual(sqlPosition("DATA", "DATABASE"), 1, "POSITION");
    assertEqual(sqlPosition("BASE", "DATABASE"), 5, "POSITION later");
    assertEqual(sqlPosition("XYZ", "DATABASE"), 0, "POSITION missing");

    let errorWasRaised = false;

    try {
        sqlSubstring("ABC", 0, 1);
    } catch {
        errorWasRaised = true;
    }

    if (!errorWasRaised) {
        throw new Error("Expected substring validation error.");
    }

    console.log("All tests passed.");
}

runTests();


// -----------------------------------------------------------------------------
// 23. FINAL INTEGRATED EXAMPLE
// -----------------------------------------------------------------------------

section("21. Final integrated customer transformation");

function transformCustomer(customerRecord) {
    const normalizedName = sqlUpper(
        sqlTrim(
            sqlConcat(
                customerRecord.firstName,
                " ",
                customerRecord.lastName
            )
        )
    );

    const normalizedEmail = sqlLower(
        sqlTrim(customerRecord.email)
    );

    const emailPosition = sqlPosition("@", normalizedEmail);

    const emailDomain = emailPosition > 0
        ? sqlSubstring(normalizedEmail, emailPosition + 1)
        : null;

    return {
        id: customerRecord.id,
        displayName: normalizedName,
        email: normalizedEmail,
        nameLength: sqlLength(normalizedName),
        emailAtPosition: emailPosition,
        emailDomain,
        emailStatus: looksLikeEmail(normalizedEmail)
            ? "PRESENT"
            : "INVALID"
    };
}

const transformedCustomers = users.map(user => {
    const [firstName, ...remainingName] = user.name.split(" ");

    return transformCustomer({
        id: user.id,
        firstName,
        lastName: remainingName.join(" "),
        email: user.email
    });
});

console.table(transformedCustomers);

console.log(
    "\nKey concepts demonstrated:",
    "\nCONCAT -> combine values",
    "\nLENGTH -> measure text",
    "\nLOWER -> lowercase normalization",
    "\nUPPER -> uppercase normalization",
    "\nTRIM -> remove boundary whitespace/characters",
    "\nSUBSTRING -> extract text",
    "\nREPLACE -> substitute text",
    "\nPOSITION -> locate text"
);
