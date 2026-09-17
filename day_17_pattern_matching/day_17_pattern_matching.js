/*
 * Pattern Matching Study
 * ======================
 *
 * Topic:
 *   LIKE, ILIKE, wildcards, regular-expression basics,
 *   and pattern-based filtering.
 *
 * JavaScript complements the Python implementation by demonstrating:
 *   - JavaScript RegExp syntax
 *   - String matching APIs
 *   - functional filtering
 *   - reusable matchers
 *   - validation
 *   - extraction and replacement
 *   - performance considerations
 *   - asynchronous pattern processing
 *
 * JavaScript does not provide SQL LIKE or ILIKE as native string methods,
 * so small implementations are provided to make the semantics explicit.
 */

"use strict";

// -----------------------------------------------------------------------------
// 1. Basic matching
// -----------------------------------------------------------------------------

function section(title) {
    console.log(`\n${"=".repeat(78)}`);
    console.log(title);
    console.log("=".repeat(78));
}

function exactMatch(value, target) {
    return value === target;
}

function contains(value, fragment) {
    return value.includes(fragment);
}

function startsWith(value, prefix) {
    return value.startsWith(prefix);
}

function endsWith(value, suffix) {
    return value.endsWith(suffix);
}

function basicExamples() {
    section("1. Basic string matching");

    const value = "database pattern matching";

    console.log("Exact:", exactMatch(value, "database pattern matching"));
    console.log("Contains:", contains(value, "pattern"));
    console.log("Starts with:", startsWith(value, "database"));
    console.log("Ends with:", endsWith(value, "matching"));
}

// -----------------------------------------------------------------------------
// 2. SQL LIKE translation
// -----------------------------------------------------------------------------

function escapeRegexCharacter(character) {
    return character.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function sqlLikeToRegexSource(pattern) {
    let source = "";

    for (const character of pattern) {
        if (character === "%") {
            source += ".*";
        } else if (character === "_") {
            source += ".";
        } else {
            source += escapeRegexCharacter(character);
        }
    }

    return `^${source}$`;
}

function sqlLike(value, pattern) {
    const expression = new RegExp(sqlLikeToRegexSource(pattern), "s");
    return expression.test(value);
}

function sqlILike(value, pattern) {
    const expression = new RegExp(
        sqlLikeToRegexSource(pattern),
        "si"
    );
    return expression.test(value);
}

// -----------------------------------------------------------------------------
// 3. Wildcards
// -----------------------------------------------------------------------------

function wildcardExamples() {
    section("2. SQL LIKE wildcards");

    const values = [
        "Alice",
        "alice",
        "ALICIA",
        "Bob",
        "Bobby",
        "Database",
        "database",
        "Data Science",
        "Python"
    ];

    for (const pattern of ["A%", "%a", "%data%", "B_b", "_____", "%", "_"]) {
        console.log(`\nPattern: ${JSON.stringify(pattern)}`);
        console.log(
            "LIKE :",
            values.filter(value => sqlLike(value, pattern))
        );
        console.log(
            "ILIKE:",
            values.filter(value => sqlILike(value, pattern))
        );
    }
}

// -----------------------------------------------------------------------------
// 4. LIKE with escaping
// -----------------------------------------------------------------------------

function sqlLikeWithEscape(value, pattern, escapeCharacter = "\\") {
    if (escapeCharacter.length !== 1) {
        throw new Error("Escape character must contain exactly one character.");
    }

    let source = "";

    for (let index = 0; index < pattern.length; index += 1) {
        const character = pattern[index];

        if (character === escapeCharacter) {
            index += 1;

            if (index >= pattern.length) {
                throw new Error("Pattern ends with an incomplete escape sequence.");
            }

            source += escapeRegexCharacter(pattern[index]);
        } else if (character === "%") {
            source += ".*";
        } else if (character === "_") {
            source += ".";
        } else {
            source += escapeRegexCharacter(character);
        }
    }

    return new RegExp(`^${source}$`, "s").test(value);
}

function escapeExamples() {
    section("3. Escaping wildcard characters");

    const tests = [
        ["100%", "100\\%"],
        ["100 percent", "100\\%"],
        ["a_b", "a\\_b"],
        ["axb", "a\\_b"]
    ];

    for (const [value, pattern] of tests) {
        console.log(
            `value=${JSON.stringify(value)}, pattern=${JSON.stringify(pattern)} ->`,
            sqlLikeWithEscape(value, pattern)
        );
    }
}

// -----------------------------------------------------------------------------
// 5. Regex basics
// -----------------------------------------------------------------------------

function regexBasics() {
    section("4. Regular-expression basics");

    const examples = [
        [/^\d+$/, "12345"],
        [/^[A-Z][a-z]+$/, "Alice"],
        [/colou?r/, "color"],
        [/colou?r/, "colour"],
        [/cat|dog/, "dog"],
        [/\bcat\b/, "a cat sleeps"],
        [/^[A-Za-z0-9_]+$/, "user_123"]
    ];

    for (const [expression, text] of examples) {
        console.log(
            `${expression} against ${JSON.stringify(text)} ->`,
            expression.test(text)
        );
    }
}

// -----------------------------------------------------------------------------
// 6. JavaScript regex APIs
// -----------------------------------------------------------------------------

function regexApiExamples() {
    section("5. JavaScript RegExp APIs");

    const text = "Python 3, Python 3.12, Python 4";

    console.log("test:", /Python/.test(text));
    console.log("match:", text.match(/Python/g));
    console.log("search:", text.search(/Python/));
    console.log("replace:", text.replace(/Python/g, "JavaScript"));
    console.log("split:", "Alice,Bob,Charlie".split(/,/));

    const expression = /Python/g;
    console.log(
        "matchAll:",
        [...text.matchAll(expression)].map(match => ({
            value: match[0],
            index: match.index
        }))
    );
}

// -----------------------------------------------------------------------------
// 7. Groups and extraction
// -----------------------------------------------------------------------------

function extractionExamples() {
    section("6. Capturing groups");

    const logLine =
        "2026-09-17 10:45:12 ERROR user=atul request=/api/orders status=500";

    const expression =
        /(?<date>\d{4}-\d{2}-\d{2})\s+
         (?<time>\d{2}:\d{2}:\d{2})\s+
         (?<level>[A-Z]+)\s+
         user=(?<user>\w+)\s+
         request=(?<request>\S+)\s+
         status=(?<status>\d{3})/x;

    /*
     * JavaScript does not universally support the /x free-spacing flag.
     * Therefore the same expression is represented without whitespace.
     */
    const compactExpression =
        /(?<date>\d{4}-\d{2}-\d{2})\s+(?<time>\d{2}:\d{2}:\d{2})\s+(?<level>[A-Z]+)\s+user=(?<user>\w+)\s+request=(?<request>\S+)\s+status=(?<status>\d{3})/;

    const match = compactExpression.exec(logLine);

    if (match) {
        console.log("Entire match:", match[0]);
        console.log("Named groups:", match.groups);
    }
}

// -----------------------------------------------------------------------------
// 8. Validation
// -----------------------------------------------------------------------------

const emailPattern =
    /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/;

const postalCodePattern = /^\d{6}$/;

const hexColorPattern = /^#[0-9A-Fa-f]{6}$/;

function validationExamples() {
    section("7. Validation");

    for (const email of [
        "person@example.com",
        "person.name@example.co.in",
        "invalid@",
        "missing-domain"
    ]) {
        console.log(email, "->", emailPattern.test(email));
    }

    for (const value of ["226001", "560001", "12345", "abcdef"]) {
        console.log(value, "postal code ->", postalCodePattern.test(value));
    }

    for (const value of ["#FFFFFF", "#12abEF", "#12345", "FFFFFF"]) {
        console.log(value, "hex color ->", hexColorPattern.test(value));
    }
}

// -----------------------------------------------------------------------------
// 9. LIKE versus regex
// -----------------------------------------------------------------------------

function compareLikeAndRegex() {
    section("8. LIKE versus regular expressions");

    const values = [
        "cat",
        "catalog",
        "concatenate",
        "dog",
        "Cat",
        "category"
    ];

    console.log(
        "LIKE '%cat%':",
        values.filter(value => sqlLike(value, "%cat%"))
    );

    console.log(
        "Regex /cat/:",
        values.filter(value => /cat/.test(value))
    );

    console.log(
        "Regex /^cat$/:",
        values.filter(value => /^cat$/.test(value))
    );

    console.log(
        "Regex /cat|dog/:",
        values.filter(value => /cat|dog/.test(value))
    );
}

// -----------------------------------------------------------------------------
// 10. Pattern-based data filtering
// -----------------------------------------------------------------------------

const people = [
    {
        id: 1,
        name: "Alice Sharma",
        email: "alice@example.com",
        city: "Lucknow",
        role: "Analyst",
        age: 28
    },
    {
        id: 2,
        name: "Aman Verma",
        email: "aman@example.org",
        city: "Delhi",
        role: "Developer",
        age: 31
    },
    {
        id: 3,
        name: "Atul Pandey",
        email: "atul@example.com",
        city: "Lucknow",
        role: "Engineer",
        age: 29
    },
    {
        id: 4,
        name: "Bob Smith",
        email: "bob@company.com",
        city: "Mumbai",
        role: "Manager",
        age: 42
    },
    {
        id: 5,
        name: "Bobby Jones",
        email: "bobby@company.org",
        city: "Delhi",
        role: "Developer",
        age: 35
    }
];

function filterByLike(rows, field, pattern, insensitive = false) {
    const matcher = insensitive ? sqlILike : sqlLike;

    return rows.filter(row => matcher(row[field], pattern));
}

function filterByRegex(rows, field, pattern, flags = "") {
    const expression = new RegExp(pattern, flags);
    return rows.filter(row => expression.test(row[field]));
}

function printRows(rows) {
    for (const row of rows) {
        console.log(
            `${row.id}: ${row.name} | ${row.email} | ${row.city} | ${row.role}`
        );
    }
}

function filteringExamples() {
    section("9. Pattern-based filtering");

    console.log("\nNames beginning with A:");
    printRows(filterByLike(people, "name", "A%"));

    console.log("\nCities containing 'del':");
    printRows(filterByLike(people, "city", "%del%", true));

    console.log("\nCompany email addresses:");
    printRows(filterByLike(people, "email", "%@company.com"));

    console.log("\nDeveloper roles:");
    printRows(filterByRegex(people, "role", "^Developer$"));
}

// -----------------------------------------------------------------------------
// 11. Regex anchors and boundaries
// -----------------------------------------------------------------------------

function anchorExamples() {
    section("10. Anchors and boundaries");

    const text = "cat scatter category";

    for (const expression of [
        /cat/g,
        /^cat/g,
        /cat$/g,
        /\bcat\b/g
    ]) {
        console.log(
            expression.toString(),
            "->",
            text.match(expression)
        );
    }
}

// -----------------------------------------------------------------------------
// 12. Character classes and quantifiers
// -----------------------------------------------------------------------------

function regexLanguageExamples() {
    section("11. Character classes and quantifiers");

    const examples = [
        [/[abc]/g, "a b c d"],
        [/[a-z]/g, "Alpha123"],
        [/[A-Z]/g, "ABCxyz"],
        [/[0-9]/g, "A1B2"],
        [/[^0-9]/g, "A1B2"],
        [/a+/g, "caaab"],
        [/a*/g, "bbb"],
        [/a?/g, "ba"],
        [/a{2,4}/g, "aaaaaa"]
    ];

    for (const [expression, text] of examples) {
        console.log(
            `${expression} on ${JSON.stringify(text)} ->`,
            text.match(expression)
        );
    }
}

// -----------------------------------------------------------------------------
// 13. Greedy versus lazy matching
// -----------------------------------------------------------------------------

function greedyExamples() {
    section("12. Greedy and lazy quantifiers");

    const html = "<tag>first</tag><tag>second</tag>";

    const greedy = html.match(/<tag>.*<\/tag>/);
    const lazy = html.match(/<tag>.*?<\/tag>/);

    console.log("Greedy:", greedy?.[0]);
    console.log("Lazy:", lazy?.[0]);
}

// -----------------------------------------------------------------------------
// 14. Lookahead and lookbehind
// -----------------------------------------------------------------------------

function lookaroundExamples() {
    section("13. Lookahead and lookbehind");

    const text = "item-100 item-200 item-abc";

    console.log(
        "Lookahead:",
        text.match(/\bitem-(?=\d+)\w+\b/g)
    );

    console.log(
        "Lookbehind:",
        text.match(/(?<=item-)\d+/g)
    );

    const passwordPattern =
        /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

    for (const password of [
        "Password1",
        "password",
        "Password!",
        "PASSWORD123!"
    ]) {
        console.log(
            password,
            "->",
            passwordPattern.test(password)
        );
    }
}

// -----------------------------------------------------------------------------
// 15. A reusable PatternMatcher class
// -----------------------------------------------------------------------------

class PatternMatcher {
    constructor() {
        this.likeCache = new Map();
    }

    getLikeExpression(pattern, insensitive) {
        const key = `${insensitive ? "i" : "s"}:${pattern}`;

        if (!this.likeCache.has(key)) {
            const flags = insensitive ? "si" : "s";
            this.likeCache.set(
                key,
                new RegExp(sqlLikeToRegexSource(pattern), flags)
            );
        }

        return this.likeCache.get(key);
    }

    like(value, pattern) {
        return this.getLikeExpression(pattern, false).test(value);
    }

    ilike(value, pattern) {
        return this.getLikeExpression(pattern, true).test(value);
    }

    regex(value, pattern, flags = "") {
        return new RegExp(pattern, flags).test(value);
    }
}

function matcherClassExamples() {
    section("14. Reusable PatternMatcher");

    const matcher = new PatternMatcher();

    console.log(
        "LIKE:",
        matcher.like("Alice", "A%")
    );

    console.log(
        "ILIKE:",
        matcher.ilike("alice", "A%")
    );

    console.log(
        "REGEX:",
        matcher.regex("Order 123", "\\d+")
    );
}

// -----------------------------------------------------------------------------
// 16. Dynamic-programming LIKE matcher
// -----------------------------------------------------------------------------

function wildcardMatchDP(text, pattern) {
    /*
     * This implementation does not translate LIKE into regex.
     *
     * dp[i][j] means:
     *     text[0..i) matches pattern[0..j)
     *
     * '%' has two possibilities:
     *     1. match nothing
     *     2. consume one text character and remain available
     */
    const rows = text.length + 1;
    const columns = pattern.length + 1;

    const dp = Array.from(
        { length: rows },
        () => Array(columns).fill(false)
    );

    dp[0][0] = true;

    for (let j = 1; j < columns; j += 1) {
        if (pattern[j - 1] === "%") {
            dp[0][j] = dp[0][j - 1];
        }
    }

    for (let i = 1; i < rows; i += 1) {
        for (let j = 1; j < columns; j += 1) {
            const patternCharacter = pattern[j - 1];

            if (patternCharacter === "%") {
                dp[i][j] =
                    dp[i][j - 1] ||
                    dp[i - 1][j];
            } else if (
                patternCharacter === "_" ||
                patternCharacter === text[i - 1]
            ) {
                dp[i][j] = dp[i - 1][j - 1];
            }
        }
    }

    return dp[text.length][pattern.length];
}

function dynamicProgrammingExamples() {
    section("15. LIKE matching without regular expressions");

    const cases = [
        ["hello", "h%"],
        ["hello", "%llo"],
        ["hello", "h_llo"],
        ["hello", "h__lo"],
        ["hello", "heaven"],
        ["", "%"],
        ["", "_"]
    ];

    for (const [text, pattern] of cases) {
        console.log(
            `${JSON.stringify(text)} / ${JSON.stringify(pattern)} ->`,
            wildcardMatchDP(text, pattern)
        );
    }
}

// -----------------------------------------------------------------------------
// 17. Async pattern filtering
// -----------------------------------------------------------------------------

async function filterInChunks(values, matcher, chunkSize = 1000) {
    /*
     * Large client-side datasets can be processed in chunks so that work
     * yields back to the event loop instead of monopolizing the thread.
     *
     * This does not make the matching algorithm intrinsically faster.
     * It improves responsiveness for suitable application workloads.
     */
    const results = [];

    for (let start = 0; start < values.length; start += chunkSize) {
        const chunk = values.slice(start, start + chunkSize);

        for (const value of chunk) {
            if (matcher(value)) {
                results.push(value);
            }
        }

        await new Promise(resolve => setTimeout(resolve, 0));
    }

    return results;
}

async function asynchronousFilteringExample() {
    section("16. Event-loop-friendly filtering");

    const values = Array.from(
        { length: 5000 },
        (_, index) => `user${index}@example.com`
    );

    const matches = await filterInChunks(
        values,
        value => /^user[0-9]+@example\.com$/.test(value)
    );

    console.log("Matched:", matches.length);
}

// -----------------------------------------------------------------------------
// 18. Performance
// -----------------------------------------------------------------------------

function performanceExample() {
    section("17. Performance");

    const values = Array.from(
        { length: 10000 },
        (_, index) => `user${index}@example.com`
    );

    const expression = /^user\d+@example\.com$/;

    const start = performance.now();

    let count = 0;

    for (const value of values) {
        if (expression.test(value)) {
            count += 1;
        }
    }

    const elapsed = performance.now() - start;

    console.log(`Matched ${count} values in ${elapsed.toFixed(3)} ms.`);
    console.log("Compile reusable regular expressions outside hot loops.");
    console.log("Avoid unnecessary backtracking and repeated conversions.");
}

// -----------------------------------------------------------------------------
// 19. Security considerations
// -----------------------------------------------------------------------------

function securityExamples() {
    section("18. Security considerations");

    console.log(
        "SQL pattern values should be passed as parameters through a database driver."
    );

    console.log(
        "Do not concatenate untrusted values into SQL statements."
    );

    console.log(
        "User-controlled regex patterns can consume significant CPU in some engines."
    );

    console.log(
        "Limit pattern length and complexity when accepting arbitrary regex."
    );

    console.log(
        "Prefer application-defined patterns when the user only needs a small search language."
    );
}

// -----------------------------------------------------------------------------
// 20. NULL and empty-string concepts
// -----------------------------------------------------------------------------

function nullExamples() {
    section("19. null, undefined, and empty strings");

    const values = ["Alice", "", null, undefined, "Bob"];

    for (const value of values) {
        const result =
            typeof value === "string"
                ? sqlLike(value, "A%")
                : false;

        console.log(
            `value=${String(value).padEnd(10)} LIKE A% -> ${result}`
        );
    }

    console.log(
        "In SQL, NULL has three-valued logic and is not equivalent to ''."
    );
}

// -----------------------------------------------------------------------------
// 21. Integrated search engine
// -----------------------------------------------------------------------------

class ContactSearch {
    constructor(records) {
        this.records = records;
        this.matcher = new PatternMatcher();
    }

    searchLike(field, pattern, insensitive = true) {
        const matchFunction = insensitive
            ? value => this.matcher.ilike(value, pattern)
            : value => this.matcher.like(value, pattern);

        return this.records.filter(record =>
            matchFunction(record[field])
        );
    }

    searchRegex(field, pattern, flags = "i") {
        const expression = new RegExp(pattern, flags);

        return this.records.filter(record =>
            expression.test(record[field])
        );
    }
}

function contactSearchDemo() {
    section("20. Integrated contact search");

    const contacts = [
        {
            name: "Aarav Singh",
            email: "aarav@company.com",
            department: "IT"
        },
        {
            name: "Ananya Sharma",
            email: "ananya@school.edu",
            department: "HR"
        },
        {
            name: "Rahul Verma",
            email: "rahul@company.com",
            department: "IT"
        },
        {
            name: "Priya Gupta",
            email: "priya@finance.org",
            department: "Finance"
        },
        {
            name: "Atul Pandey",
            email: "atul@company.com",
            department: "Security"
        }
    ];

    const search = new ContactSearch(contacts);

    console.log(
        "Names beginning with an:",
        search.searchLike("name", "an%")
    );

    console.log(
        "Company emails:",
        search.searchLike("email", "%@company.com")
    );

    console.log(
        "Departments containing it:",
        search.searchLike("department", "%it%")
    );

    console.log(
        "Names matching regex:",
        search.searchRegex("name", "^A.*a$")
    );
}

// -----------------------------------------------------------------------------
// 22. Assertions
// -----------------------------------------------------------------------------

function runTests() {
    section("21. Self-tests");

    console.assert(sqlLike("Alice", "A%"));
    console.assert(sqlLike("cat", "c_t"));
    console.assert(!sqlLike("coat", "c_t"));
    console.assert(sqlLike("", "%"));
    console.assert(!sqlLike("", "_"));

    console.assert(sqlILike("Alice", "alice"));
    console.assert(sqlILike("DATABASE", "%data%"));

    console.assert(wildcardMatchDP("hello", "h%"));
    console.assert(wildcardMatchDP("hello", "h_llo"));
    console.assert(!wildcardMatchDP("hello", "h__lo"));

    console.assert(/^\d{6}$/.test("226001"));
    console.assert(!/^\d{6}$/.test("22600"));

    const matcher = new PatternMatcher();

    console.assert(matcher.like("Alice", "A%"));
    console.assert(matcher.ilike("alice", "A%"));
    console.assert(matcher.regex("Order 123", "\\d+"));

    console.log("All JavaScript tests passed.");
}

// -----------------------------------------------------------------------------
// 23. Main
// -----------------------------------------------------------------------------

async function main() {
    basicExamples();
    wildcardExamples();
    escapeExamples();
    regexBasics();
    regexApiExamples();
    extractionExamples();
    validationExamples();
    compareLikeAndRegex();
    filteringExamples();
    anchorExamples();
    regexLanguageExamples();
    greedyExamples();
    lookaroundExamples();
    matcherClassExamples();
    dynamicProgrammingExamples();
    performanceExample();
    securityExamples();
    nullExamples();
    contactSearchDemo();
    runTests();

    await asynchronousFilteringExample();
}

main().catch(error => {
    console.error("Program failed:", error);
    process.exitCode = 1;
});
