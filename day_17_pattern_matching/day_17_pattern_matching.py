"""
Pattern Matching Study
======================

Topic:
    LIKE, ILIKE, wildcards, regular-expression basics, and pattern-based filtering.

This standalone script teaches pattern matching from beginner to advanced level.
It deliberately avoids external packages and implements SQL-style LIKE/ILIKE
behavior so that the mechanisms can be studied directly in Python.

Important SQL ideas:
    %  -> zero or more characters
    _  -> exactly one character
    LIKE -> usually case-sensitive according to database/collation rules
    ILIKE -> case-insensitive matching in systems that support it, such as PostgreSQL
    regex -> a more expressive pattern language than LIKE

The examples use strings rather than a real database so that the matching
algorithms themselves remain visible and executable.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Iterable, Pattern


# ---------------------------------------------------------------------------
# 1. Basic string matching
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def exact_match(value: str, target: str) -> bool:
    """Exact matching requires the complete strings to be equal."""
    return value == target


def contains(value: str, fragment: str) -> bool:
    """Substring matching checks whether fragment occurs anywhere."""
    return fragment in value


def starts_with(value: str, prefix: str) -> bool:
    return value.startswith(prefix)


def ends_with(value: str, suffix: str) -> bool:
    return value.endswith(suffix)


def basic_examples() -> None:
    section("1. Exact, substring, prefix, and suffix matching")

    value = "database pattern matching"

    examples = [
        ("Exact", exact_match(value, "database pattern matching")),
        ("Contains", contains(value, "pattern")),
        ("Starts with", starts_with(value, "database")),
        ("Ends with", ends_with(value, "matching")),
    ]

    for name, result in examples:
        print(f"{name:12}: {result}")


# ---------------------------------------------------------------------------
# 2. SQL LIKE implementation
# ---------------------------------------------------------------------------

def sql_like_to_regex(pattern: str) -> str:
    """
    Translate a SQL LIKE pattern into an equivalent Python regular expression.

    SQL LIKE:
        % = zero or more characters
        _ = exactly one character

    All other characters are treated literally.

    re.escape() is important because characters such as '.', '+', '(' and
    '[' have special meanings in regular expressions but not in ordinary
    SQL LIKE patterns.
    """
    pieces: list[str] = []

    for character in pattern:
        if character == "%":
            pieces.append(".*")
        elif character == "_":
            pieces.append(".")
        else:
            pieces.append(re.escape(character))

    return "^" + "".join(pieces) + "$"


def sql_like(value: str, pattern: str) -> bool:
    """Perform complete-string SQL LIKE-style matching."""
    regex_pattern = sql_like_to_regex(pattern)
    return re.match(regex_pattern, value, flags=re.DOTALL) is not None


def sql_ilike(value: str, pattern: str) -> bool:
    """
    Perform case-insensitive SQL ILIKE-style matching.

    PostgreSQL provides ILIKE directly. Other database engines can have
    different case-sensitivity behavior depending on collation and syntax.
    """
    regex_pattern = sql_like_to_regex(pattern)
    return re.match(
        regex_pattern,
        value,
        flags=re.IGNORECASE | re.DOTALL,
    ) is not None


def like_examples() -> None:
    section("2. SQL LIKE and ILIKE")

    records = [
        "Alice",
        "alice",
        "ALICIA",
        "Bob",
        "Bobby",
        "Database",
        "database",
        "Data Science",
        "Data Engineering",
        "Python",
        "JavaScript",
    ]

    patterns = [
        "A%",
        "%a",
        "%data%",
        "Data%",
        "B_b",
        "_____",
        "%",
        "_",
    ]

    for pattern in patterns:
        print(f"\nPattern: {pattern!r}")
        print("LIKE :", [value for value in records if sql_like(value, pattern)])
        print("ILIKE:", [value for value in records if sql_ilike(value, pattern)])


# ---------------------------------------------------------------------------
# 3. Why % and _ behave differently
# ---------------------------------------------------------------------------

def wildcard_examples() -> None:
    section("3. Wildcard semantics")

    cases = [
        ("cat", "c_t"),
        ("coat", "c_t"),
        ("ct", "c_t"),
        ("cat", "c%"),
        ("catalog", "c%"),
        ("", "%"),
        ("a", "_"),
        ("ab", "_"),
        ("", "_"),
    ]

    for value, pattern in cases:
        print(
            f"value={value!r:10} pattern={pattern!r:8} "
            f"LIKE={sql_like(value, pattern)}"
        )

    print("\nKey distinction:")
    print("_ matches exactly one character.")
    print("% matches zero or more characters.")


# ---------------------------------------------------------------------------
# 4. SQL LIKE with escaping
# ---------------------------------------------------------------------------

def sql_like_with_escape(
    value: str,
    pattern: str,
    escape_character: str = "\\",
) -> bool:
    """
    LIKE implementation supporting an explicit escape character.

    Example:
        pattern = r"100\%"
        value   = "100%"
        result  = True

    The escaped '%' is treated as a literal percent sign.
    """
    if len(escape_character) != 1:
        raise ValueError("escape_character must contain exactly one character")

    pieces: list[str] = []
    index = 0

    while index < len(pattern):
        character = pattern[index]

        if character == escape_character:
            index += 1
            if index >= len(pattern):
                raise ValueError("Pattern ends with an incomplete escape sequence")
            pieces.append(re.escape(pattern[index]))
        elif character == "%":
            pieces.append(".*")
        elif character == "_":
            pieces.append(".")
        else:
            pieces.append(re.escape(character))

        index += 1

    expression = "^" + "".join(pieces) + "$"
    return re.match(expression, value, flags=re.DOTALL) is not None


def escape_examples() -> None:
    section("4. Escaping wildcard characters")

    tests = [
        ("100%", r"100\%"),
        ("100 percent", r"100\%"),
        ("a_b", r"a\_b"),
        ("axb", r"a\_b"),
        ("C:\\data", r"C:\\data"),
    ]

    for value, pattern in tests:
        try:
            result = sql_like_with_escape(value, pattern)
        except ValueError as error:
            result = f"ERROR: {error}"
        print(f"value={value!r:16} pattern={pattern!r:16} result={result}")


# ---------------------------------------------------------------------------
# 5. Pattern-based filtering
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Person:
    person_id: int
    name: str
    email: str
    city: str
    role: str
    age: int


PEOPLE = [
    Person(1, "Alice Sharma", "alice@example.com", "Lucknow", "Analyst", 28),
    Person(2, "Aman Verma", "aman@example.org", "Delhi", "Developer", 31),
    Person(3, "Atul Pandey", "atul@example.com", "Lucknow", "Engineer", 29),
    Person(4, "Bob Smith", "bob@company.com", "Mumbai", "Manager", 42),
    Person(5, "Bobby Jones", "bobby@company.org", "Delhi", "Developer", 35),
    Person(6, "Anita Singh", "anita@school.edu", "Jaipur", "Teacher", 38),
    Person(7, "David Brown", "david@example.net", "Pune", "Engineer", 27),
]


def filter_like(
    rows: Iterable[Person],
    field_getter: Callable[[Person], str],
    pattern: str,
    case_insensitive: bool = False,
) -> list[Person]:
    matcher = sql_ilike if case_insensitive else sql_like
    return [row for row in rows if matcher(field_getter(row), pattern)]


def print_people(rows: Iterable[Person]) -> None:
    for person in rows:
        print(
            f"{person.person_id}: {person.name:16} "
            f"{person.email:24} {person.city:10} "
            f"{person.role:12} age={person.age}"
        )


def filtering_examples() -> None:
    section("5. Pattern-based filtering")

    print("\nNames beginning with 'A':")
    print_people(filter_like(PEOPLE, lambda p: p.name, "A%"))

    print("\nCities containing 'del':")
    print_people(filter_like(PEOPLE, lambda p: p.city, "%del%", True))

    print("\nEmail addresses ending with .org:")
    print_people(filter_like(PEOPLE, lambda p: p.email, "%.org"))

    print("\nRoles beginning with 'Dev':")
    print_people(filter_like(PEOPLE, lambda p: p.role, "Dev%"))


# ---------------------------------------------------------------------------
# 6. Regular-expression fundamentals
# ---------------------------------------------------------------------------

REGEX_EXAMPLES = {
    "literal": r"cat",
    "digit": r"\d+",
    "word": r"\w+",
    "whitespace": r"\s+",
    "optional_character": r"colou?r",
    "one_or_more": r"a+",
    "zero_or_more": r"a*",
    "zero_or_one": r"a?",
    "exactly_three": r"a{3}",
    "range": r"a{2,4}",
    "start": r"^Python",
    "end": r"Python$",
    "character_class": r"[A-Z][a-z]+",
    "negated_class": r"[^0-9]+",
    "alternation": r"cat|dog",
}


def regex_fundamentals() -> None:
    section("6. Regular-expression fundamentals")

    test_cases = [
        (r"\d+", "Order 123"),
        (r"[A-Z][a-z]+", "Alice"),
        (r"^Python$", "Python"),
        (r"colou?r", "color"),
        (r"colou?r", "colour"),
        (r"cat|dog", "dog"),
        (r"\bcat\b", "a cat sleeps"),
    ]

    for pattern, text in test_cases:
        match = re.search(pattern, text)
        print(f"pattern={pattern!r:18} text={text!r:20} match={bool(match)}")


# ---------------------------------------------------------------------------
# 7. Search, match, fullmatch, findall, finditer
# ---------------------------------------------------------------------------

def regex_api_examples() -> None:
    section("7. Important regular-expression operations")

    text = "Python 3, Python 3.12, Python 4, and Pythonista."

    print("re.search     :", re.search(r"Python", text).group())
    print("re.match      :", re.match(r"Python", text).group())
    print("re.fullmatch  :", re.fullmatch(r"Python", text))

    print("re.findall    :", re.findall(r"Python", text))

    print("re.finditer   :", [
        (match.group(), match.start(), match.end())
        for match in re.finditer(r"Python", text)
    ])

    print("\nImportant:")
    print("match() checks from the beginning.")
    print("search() looks anywhere.")
    print("fullmatch() requires the entire string to match.")


# ---------------------------------------------------------------------------
# 8. Capturing groups and extraction
# ---------------------------------------------------------------------------

def extraction_examples() -> None:
    section("8. Capturing groups and structured extraction")

    log_line = (
        "2026-09-17 10:45:12 ERROR user=atul "
        "request=/api/orders status=500"
    )

    pattern = re.compile(
        r"(?P<date>\d{4}-\d{2}-\d{2})\s+"
        r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
        r"(?P<level>[A-Z]+)\s+"
        r"user=(?P<user>\w+)\s+"
        r"request=(?P<request>\S+)\s+"
        r"status=(?P<status>\d{3})"
    )

    match = pattern.fullmatch(log_line)

    if match:
        print("Entire match:", match.group())
        print("Groups:", match.groups())
        print("Named groups:", match.groupdict())


# ---------------------------------------------------------------------------
# 9. Validation with regular expressions
# ---------------------------------------------------------------------------

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)

POSTAL_CODE_PATTERN = re.compile(r"^\d{6}$")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validation_examples() -> None:
    section("9. Validation")

    email_values = [
        "person@example.com",
        "person.name@example.co.in",
        "invalid@",
        "missing-domain",
    ]

    for email in email_values:
        print(f"email={email:32} valid={bool(EMAIL_PATTERN.fullmatch(email))}")

    postal_values = ["226001", "560001", "12345", "abcdef"]

    for postal_code in postal_values:
        print(
            f"postal_code={postal_code:10} "
            f"valid={bool(POSTAL_CODE_PATTERN.fullmatch(postal_code))}"
        )

    colors = ["#FFFFFF", "#12abEF", "#12345", "FFFFFF"]

    for color in colors:
        print(
            f"hex_color={color:10} "
            f"valid={bool(HEX_COLOR_PATTERN.fullmatch(color))}"
        )


# ---------------------------------------------------------------------------
# 10. Compiled expressions
# ---------------------------------------------------------------------------

def compiled_regex_examples() -> None:
    section("10. Compiled regular expressions")

    pattern = re.compile(r"\b[A-Z][a-z]{2,}\b")

    words = ["Alice", "bob", "Python", "SQL", "Database", "x"]

    for word in words:
        print(f"{word:12} -> {bool(pattern.fullmatch(word))}")

    print(
        "\nCompilation is useful when the same regular expression is applied "
        "many times because the pattern object can be reused."
    )


# ---------------------------------------------------------------------------
# 11. Regex substitution and transformation
# ---------------------------------------------------------------------------

def substitution_examples() -> None:
    section("11. Regex replacement")

    text = "Phone: 9876543210; Phone: 9123456789"

    redacted = re.sub(r"\b\d{10}\b", "[REDACTED]", text)
    print("Original:", text)
    print("Redacted:", redacted)

    normalized_spaces = re.sub(r"\s+", " ", "many     spaces\nand\ttabs")
    print("Normalized:", normalized_spaces)


# ---------------------------------------------------------------------------
# 12. LIKE versus regex
# ---------------------------------------------------------------------------

def compare_like_and_regex() -> None:
    section("12. LIKE versus regular expressions")

    values = [
        "cat",
        "catalog",
        "concatenate",
        "dog",
        "Cat",
        "category",
    ]

    print("LIKE '%cat%':")
    print([value for value in values if sql_like(value, "%cat%")])

    print("\nRegex r'cat':")
    print([value for value in values if re.search(r"cat", value)])

    print("\nRegex r'^cat$':")
    print([value for value in values if re.fullmatch(r"cat", value)])

    print("\nRegex r'cat|dog':")
    print([value for value in values if re.search(r"cat|dog", value)])


# ---------------------------------------------------------------------------
# 13. Case sensitivity and Unicode
# ---------------------------------------------------------------------------

def case_and_unicode_examples() -> None:
    section("13. Case sensitivity and Unicode")

    values = ["Python", "python", "PYTHON", "Pythön", "café", "CAFÉ"]

    print("LIKE 'python':")
    print([value for value in values if sql_like(value, "python")])

    print("\nILIKE 'python':")
    print([value for value in values if sql_ilike(value, "python")])

    print("\nUnicode-aware Python regex:")
    print([value for value in values if re.search(r"^\w+$", value)])


# ---------------------------------------------------------------------------
# 14. Wildcard matching without regex
# ---------------------------------------------------------------------------

def wildcard_match_dp(text: str, pattern: str) -> bool:
    """
    Direct dynamic-programming implementation of LIKE-style matching.

    This implementation demonstrates the wildcard algorithm without converting
    the pattern into a regex.

    dp[i][j] means:
        text[:i] matches pattern[:j]

    Complexity:
        Time:  O(len(text) * len(pattern))
        Space: O(len(text) * len(pattern))
    """
    text_length = len(text)
    pattern_length = len(pattern)

    dp = [
        [False] * (pattern_length + 1)
        for _ in range(text_length + 1)
    ]

    dp[0][0] = True

    for j in range(1, pattern_length + 1):
        if pattern[j - 1] == "%":
            dp[0][j] = dp[0][j - 1]

    for i in range(1, text_length + 1):
        for j in range(1, pattern_length + 1):
            pattern_character = pattern[j - 1]

            if pattern_character == "%":
                # Two choices:
                # 1. % matches nothing: dp[i][j - 1]
                # 2. % consumes one text character: dp[i - 1][j]
                dp[i][j] = dp[i][j - 1] or dp[i - 1][j]

            elif pattern_character == "_" or pattern_character == text[i - 1]:
                dp[i][j] = dp[i - 1][j - 1]

    return dp[text_length][pattern_length]


def wildcard_dp_examples() -> None:
    section("14. LIKE matching with dynamic programming")

    cases = [
        ("hello", "h%"),
        ("hello", "%llo"),
        ("hello", "h_llo"),
        ("hello", "h__lo"),
        ("hello", "h__l_"),
        ("hello", "heaven"),
        ("", "%"),
        ("", "_"),
    ]

    for text, pattern in cases:
        print(
            f"text={text!r:10} pattern={pattern!r:10} "
            f"match={wildcard_match_dp(text, pattern)}"
        )


# ---------------------------------------------------------------------------
# 15. Recursive wildcard matching with memoization
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def wildcard_match_recursive(
    text: str,
    pattern: str,
    text_index: int = 0,
    pattern_index: int = 0,
) -> bool:
    """
    Memoized recursive wildcard matcher.

    This version makes the branching behavior of '%' explicit.
    """

    if pattern_index == len(pattern):
        return text_index == len(text)

    current = pattern[pattern_index]

    if current == "%":
        # Option A: % matches zero characters.
        if wildcard_match_recursive(
            text, pattern, text_index, pattern_index + 1
        ):
            return True

        # Option B: % consumes one character.
        if text_index < len(text):
            return wildcard_match_recursive(
                text, pattern, text_index + 1, pattern_index
            )

        return False

    if text_index >= len(text):
        return False

    if current == "_" or current == text[text_index]:
        return wildcard_match_recursive(
            text,
            pattern,
            text_index + 1,
            pattern_index + 1,
        )

    return False


# ---------------------------------------------------------------------------
# 16. Query-style filtering pipeline
# ---------------------------------------------------------------------------

def filter_values(
    values: Iterable[str],
    pattern: str,
    *,
    case_insensitive: bool = False,
    use_regex: bool = False,
) -> list[str]:
    """
    Generic filtering function supporting LIKE or regex semantics.
    """
    if use_regex:
        flags = re.IGNORECASE if case_insensitive else 0
        compiled = re.compile(pattern, flags)
        return [
            value
            for value in values
            if compiled.search(value) is not None
        ]

    matcher = sql_ilike if case_insensitive else sql_like
    return [
        value
        for value in values
        if matcher(value, pattern)
    ]


def filtering_pipeline_examples() -> None:
    section("15. A reusable filtering pipeline")

    names = [person.name for person in PEOPLE]

    queries = [
        ("LIKE", "A%", False, False),
        ("ILIKE", "%an%", True, False),
        ("REGEX", r"^A.*a$", False, True),
        ("REGEX", r"developer", True, True),
    ]

    for name, pattern, insensitive, regex_mode in queries:
        matches = filter_values(
            names,
            pattern,
            case_insensitive=insensitive,
            use_regex=regex_mode,
        )
        print(f"{name:7} {pattern!r:15} -> {matches}")


# ---------------------------------------------------------------------------
# 17. Regex anchors and boundaries
# ---------------------------------------------------------------------------

def anchors_examples() -> None:
    section("16. Anchors and boundaries")

    text = "cat scatter category"

    expressions = [
        r"cat",
        r"^cat",
        r"cat$",
        r"\bcat\b",
        r"\Bcat\B",
    ]

    for expression in expressions:
        matches = re.findall(expression, text)
        print(f"{expression:12} -> {matches}")


# ---------------------------------------------------------------------------
# 18. Character classes
# ---------------------------------------------------------------------------

def character_class_examples() -> None:
    section("17. Character classes")

    expressions = {
        r"[abc]": "a b c d",
        r"[a-z]": "alpha123",
        r"[A-Z]": "ABCxyz",
        r"[0-9]": "A1B2",
        r"[^0-9]": "A1B2",
        r"[A-Za-z0-9_]+": "user_123",
    }

    for expression, text in expressions.items():
        print(
            f"{expression:20} "
            f"-> {re.findall(expression, text)}"
        )


# ---------------------------------------------------------------------------
# 19. Quantifiers
# ---------------------------------------------------------------------------

def quantifier_examples() -> None:
    section("18. Quantifiers")

    tests = [
        (r"a*", "bbb"),
        (r"a+", "aaab"),
        (r"a?", "ba"),
        (r"a{2}", "aaaa"),
        (r"a{2,4}", "aaaaaa"),
        (r"a{2,}", "aaaaaa"),
    ]

    for expression, text in tests:
        match = re.search(expression, text)
        print(
            f"pattern={expression:8} text={text:8} "
            f"match={match.group() if match else None!r}"
        )


# ---------------------------------------------------------------------------
# 20. Greedy versus non-greedy matching
# ---------------------------------------------------------------------------

def greedy_examples() -> None:
    section("19. Greedy and non-greedy quantifiers")

    html = "<tag>first</tag><tag>second</tag>"

    greedy = re.search(r"<tag>.*</tag>", html)
    non_greedy = re.search(r"<tag>.*?</tag>", html)

    print("Greedy:", greedy.group() if greedy else None)
    print("Non-greedy:", non_greedy.group() if non_greedy else None)

    print(
        "\nGreedy quantifiers normally consume as much as possible while "
        "still allowing the complete expression to succeed."
    )
    print(
        "Adding ? after a quantifier usually changes it to a non-greedy "
        "form."
    )


# ---------------------------------------------------------------------------
# 21. Lookaround
# ---------------------------------------------------------------------------

def lookaround_examples() -> None:
    section("20. Lookahead and lookbehind")

    text = "item-100 item-200 item-abc"

    positive_lookahead = re.findall(r"\bitem-(?=\d+)\w+\b", text)
    positive_lookbehind = re.findall(r"(?<=item-)\d+", text)

    print("Positive lookahead :", positive_lookahead)
    print("Positive lookbehind:", positive_lookbehind)

    password_candidates = [
        "Password1",
        "password",
        "Password!",
        "PASSWORD123!",
    ]

    password_pattern = re.compile(
        r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
    )

    for password in password_candidates:
        print(
            f"{password:16} -> "
            f"{bool(password_pattern.fullmatch(password))}"
        )


# ---------------------------------------------------------------------------
# 22. Performance and catastrophic backtracking
# ---------------------------------------------------------------------------

def performance_examples() -> None:
    section("21. Performance considerations")

    values = [f"user{i}@example.com" for i in range(10_000)]

    compiled = re.compile(r"^user\d+@example\.com$")

    start = time.perf_counter()
    count = sum(
        1
        for value in values
        if compiled.fullmatch(value)
    )
    elapsed = time.perf_counter() - start

    print(f"Compiled regex matched {count} values in {elapsed:.6f} seconds.")

    print("\nPerformance principles:")
    print("- Compile repeatedly used regex patterns.")
    print("- Prefer simple predicates when LIKE is sufficient.")
    print("- Avoid unnecessarily complex nested quantifiers.")
    print("- Index-friendly database patterns can be much faster than scans.")
    print("- Benchmark against realistic data rather than tiny examples.")


# ---------------------------------------------------------------------------
# 23. Database indexing concepts
# ---------------------------------------------------------------------------

def database_indexing_concepts() -> None:
    section("22. Database indexing concepts")

    print("Typical pattern-search behavior:")
    print("1. WHERE name = 'Alice' can often use an ordinary index efficiently.")
    print("2. WHERE name LIKE 'Alice%' can often use a suitable index.")
    print("3. WHERE name LIKE '%Alice' commonly requires more work.")
    print("4. WHERE name LIKE '%Alice%' commonly scans many candidate values.")
    print("5. Regex predicates may require specialized indexing or scanning.")
    print("6. Exact behavior depends on the database, collation, operator class,")
    print("   statistics, query planner, and index configuration.")


# ---------------------------------------------------------------------------
# 24. SQL examples as strings
# ---------------------------------------------------------------------------

def sql_query_examples() -> None:
    section("23. SQL pattern-matching syntax")

    queries = [
        "SELECT * FROM users WHERE name LIKE 'A%';",
        "SELECT * FROM users WHERE name LIKE '%son';",
        "SELECT * FROM users WHERE name LIKE '%data%';",
        "SELECT * FROM users WHERE code LIKE 'AB__';",
        "SELECT * FROM users WHERE name ILIKE 'atul%';",
        "SELECT * FROM users WHERE email LIKE '%@example.com';",
        "SELECT * FROM products WHERE name LIKE '100\\%' ESCAPE '\\\\';",
        "SELECT * FROM users WHERE name ~ '^[A-Z][a-z]+$';",
    ]

    for query in queries:
        print(query)


# ---------------------------------------------------------------------------
# 25. SQL dialect distinctions
# ---------------------------------------------------------------------------

def dialect_notes() -> None:
    section("24. SQL dialect distinctions")

    print("LIKE is widely available in SQL systems.")
    print("ILIKE is particularly associated with PostgreSQL.")
    print("PostgreSQL also provides regex operators such as ~ and ~*.")
    print("MySQL commonly provides REGEXP/REGEXP_LIKE depending on version.")
    print("SQL Server uses LIKE and has different regex capabilities.")
    print("Oracle provides REGEXP_LIKE and related regex functions.")
    print("Case sensitivity can depend on collation and database configuration.")
    print("Therefore, SQL syntax should always be checked against the target DBMS.")


# ---------------------------------------------------------------------------
# 26. Security: pattern injection and ReDoS
# ---------------------------------------------------------------------------

def security_examples() -> None:
    section("25. Security considerations")

    print("User-controlled LIKE patterns should be parameterized in SQL.")
    print("Do not concatenate untrusted input into SQL statements.")
    print("User-controlled regular expressions can be dangerous.")
    print("Some regex engines can suffer catastrophic backtracking.")
    print("Limit regex length and complexity when accepting patterns from users.")
    print("Apply execution timeouts or safer regex engines where appropriate.")
    print("Validate and normalize data before applying business rules.")

    unsafe_concept = (
        "SELECT * FROM users WHERE name LIKE '" +
        "USER_INPUT" +
        "';"
    )
    print("\nConceptual unsafe construction:", unsafe_concept)
    print("Prefer parameterized statements supplied by the database driver.")


# ---------------------------------------------------------------------------
# 27. Common mistakes
# ---------------------------------------------------------------------------

def common_mistakes() -> None:
    section("26. Common mistakes")

    mistakes = [
        "Using = when wildcard matching is required.",
        "Forgetting that LIKE normally matches the complete value.",
        "Confusing % with _.",
        "Assuming LIKE and ILIKE are available identically in every DBMS.",
        "Using regex syntax inside a LIKE pattern.",
        "Forgetting to escape literal % or _ when they are data.",
        "Using search() when full validation requires fullmatch().",
        "Creating a regex inside a high-volume loop unnecessarily.",
        "Assuming case-insensitive matching is identical for every Unicode language.",
        "Building SQL by string concatenation with user input.",
    ]

    for number, mistake in enumerate(mistakes, start=1):
        print(f"{number:2}. {mistake}")


# ---------------------------------------------------------------------------
# 28. Advanced reusable matcher
# ---------------------------------------------------------------------------

class PatternMatcher:
    """
    Reusable matcher supporting SQL LIKE, ILIKE, and regular expressions.

    The class keeps the distinction between pattern languages explicit.
    """

    def __init__(self) -> None:
        self._regex_cache: dict[tuple[str, bool], Pattern[str]] = {}

    def _get_like_regex(
        self,
        pattern: str,
        case_insensitive: bool,
    ) -> Pattern[str]:
        key = (pattern, case_insensitive)

        if key not in self._regex_cache:
            flags = re.IGNORECASE if case_insensitive else 0
            self._regex_cache[key] = re.compile(
                sql_like_to_regex(pattern),
                flags | re.DOTALL,
            )

        return self._regex_cache[key]

    def like(self, value: str, pattern: str) -> bool:
        return self._get_like_regex(pattern, False).match(value) is not None

    def ilike(self, value: str, pattern: str) -> bool:
        return self._get_like_regex(pattern, True).match(value) is not None

    def regex(
        self,
        value: str,
        pattern: str,
        case_insensitive: bool = False,
    ) -> bool:
        flags = re.IGNORECASE if case_insensitive else 0
        return re.search(pattern, value, flags) is not None


def matcher_class_examples() -> None:
    section("27. Reusable PatternMatcher class")

    matcher = PatternMatcher()

    tests = [
        ("Alice", "A%", "LIKE"),
        ("alice", "A%", "ILIKE"),
        ("Alice42", r"^[A-Za-z]+\d+$", "REGEX"),
    ]

    for value, pattern, mode in tests:
        if mode == "LIKE":
            result = matcher.like(value, pattern)
        elif mode == "ILIKE":
            result = matcher.ilike(value, pattern)
        else:
            result = matcher.regex(value, pattern)

        print(f"{mode:5} {value!r:12} {pattern!r:22} -> {result}")


# ---------------------------------------------------------------------------
# 29. Test suite without external packages
# ---------------------------------------------------------------------------

def run_tests() -> None:
    section("28. Self-tests")

    assert sql_like("Alice", "A%")
    assert sql_like("Alice", "A____")
    assert not sql_like("Alice", "B%")
    assert sql_like("cat", "c_t")
    assert not sql_like("coat", "c_t")
    assert sql_like("", "%")
    assert not sql_like("", "_")

    assert sql_ilike("Alice", "alice")
    assert sql_ilike("DATABASE", "%data%")

    assert wildcard_match_dp("hello", "h%")
    assert wildcard_match_dp("hello", "h_llo")
    assert not wildcard_match_dp("hello", "h__lo")
    assert wildcard_match_recursive("hello", "%")
    assert wildcard_match_recursive("hello", "h%")
    assert not wildcard_match_recursive("hello", "x%")

    assert re.fullmatch(r"\d{6}", "226001")
    assert not re.fullmatch(r"\d{6}", "22600")

    matcher = PatternMatcher()
    assert matcher.like("Alice", "A%")
    assert matcher.ilike("alice", "A%")
    assert matcher.regex("Order 123", r"\d+")

    print("All tests passed.")


# ---------------------------------------------------------------------------
# 30. Practical mini-project: searchable contact directory
# ---------------------------------------------------------------------------

def contact_directory_demo() -> None:
    section("29. Practical mini-project: searchable contact directory")

    contacts = [
        {"name": "Aarav Singh", "email": "aarav@company.com", "department": "IT"},
        {"name": "Ananya Sharma", "email": "ananya@school.edu", "department": "HR"},
        {"name": "Rahul Verma", "email": "rahul@company.com", "department": "IT"},
        {"name": "Priya Gupta", "email": "priya@finance.org", "department": "Finance"},
        {"name": "Atul Pandey", "email": "atul@company.com", "department": "Security"},
    ]

    def search_contacts(
        field: str,
        pattern: str,
        insensitive: bool = True,
    ) -> list[dict[str, str]]:
        matcher = sql_ilike if insensitive else sql_like
        return [
            contact
            for contact in contacts
            if matcher(contact[field], pattern)
        ]

    print("Names beginning with 'an':")
    for contact in search_contacts("name", "an%"):
        print(contact)

    print("\nEmails from company.com:")
    for contact in search_contacts("email", "%@company.com"):
        print(contact)

    print("\nDepartments containing 'it':")
    for contact in search_contacts("department", "%it%"):
        print(contact)


# ---------------------------------------------------------------------------
# 31. Production design checklist
# ---------------------------------------------------------------------------

def production_checklist() -> None:
    section("30. Production considerations")

    checklist = [
        "Know the exact pattern language being used.",
        "Know whether matching is case-sensitive.",
        "Understand the database collation.",
        "Use parameterized SQL statements.",
        "Measure query plans for large datasets.",
        "Add appropriate indexes for common search patterns.",
        "Avoid leading wildcards when an index-dependent prefix search is required.",
        "Use full-text search when substring matching is not the right model.",
        "Validate user-supplied regular expressions.",
        "Limit expensive regex operations.",
        "Test Unicode and locale-sensitive behavior.",
        "Test empty strings and NULL values explicitly.",
        "Do not assume different database systems implement matching identically.",
    ]

    for item in checklist:
        print(f"[ ] {item}")


# ---------------------------------------------------------------------------
# 32. NULL concept
# ---------------------------------------------------------------------------

def null_concept() -> None:
    section("31. NULL is different from an empty string")

    values: list[str | None] = [
        "Alice",
        "",
        None,
        "Bob",
    ]

    print("Python-style demonstration:")
    for value in values:
        print(
            f"value={value!r:8} "
            f"LIKE A% -> {False if value is None else sql_like(value, 'A%')}"
        )

    print(
        "\nIn SQL, NULL represents an unknown/missing value. "
        "A comparison involving NULL normally produces UNKNOWN rather "
        "than TRUE or FALSE. SQL queries commonly use IS NULL or IS NOT NULL."
    )


# ---------------------------------------------------------------------------
# 33. Final integrated demonstration
# ---------------------------------------------------------------------------

def integrated_demo() -> None:
    section("32. Integrated pattern-search demonstration")

    values = [
        "Alice@example.com",
        "alice@example.org",
        "Atul@example.com",
        "bob@company.com",
        "admin@company.org",
        "support@example.com",
    ]

    like_pattern = "%@example.com"
    regex_pattern = r"^[A-Za-z0-9._%+-]+@example\.com$"

    print("ILIKE results:")
    print([
        value
        for value in values
        if sql_ilike(value, like_pattern)
    ])

    print("\nRegex results:")
    print([
        value
        for value in values
        if re.fullmatch(regex_pattern, value)
    ])

    print("\nInterpretation:")
    print("LIKE expresses a small wildcard language.")
    print("Regex provides character classes, groups, quantifiers, anchors,")
    print("alternation, lookarounds, extraction, and transformation.")
    print("The right choice depends on the problem, database, performance")
    print("requirements, and security constraints.")


def main() -> None:
    basic_examples()
    like_examples()
    wildcard_examples()
    escape_examples()
    filtering_examples()
    regex_fundamentals()
    regex_api_examples()
    extraction_examples()
    validation_examples()
    compiled_regex_examples()
    substitution_examples()
    compare_like_and_regex()
    case_and_unicode_examples()
    wildcard_dp_examples()

    # Clear memoization before the independent recursive demonstration.
    wildcard_match_recursive.cache_clear()

    filtering_pipeline_examples()
    anchors_examples()
    character_class_examples()
    quantifier_examples()
    greedy_examples()
    lookaround_examples()
    performance_examples()
    database_indexing_concepts()
    sql_query_examples()
    dialect_notes()
    security_examples()
    common_mistakes()
    matcher_class_examples()
    run_tests()
    contact_directory_demo()
    production_checklist()
    null_concept()
    integrated_demo()


if __name__ == "__main__":
    main()
