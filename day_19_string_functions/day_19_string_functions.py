"""
String Functions: CONCAT, LENGTH, LOWER, UPPER, TRIM, SUBSTRING, REPLACE, POSITION

A standalone study script covering SQL-style string functions from beginner
through advanced usage, with executable Python demonstrations and SQLite
queries.

The examples use SQL semantics where possible. SQLite is part of Python's
standard library, so no external package is required.

Core functions covered:
    CONCAT      - combine strings
    LENGTH      - determine character/string length
    LOWER       - convert text to lowercase
    UPPER       - convert text to uppercase
    TRIM        - remove surrounding characters/whitespace
    SUBSTRING   - extract part of a string
    REPLACE     - substitute one substring with another
    POSITION     - find where a substring occurs

Important SQL dialect note:
    String functions are not perfectly standardized across all database
    systems. CONCAT is available directly in systems such as MySQL and
    PostgreSQL, while SQLite traditionally uses || for concatenation.
    POSITION is standard SQL syntax, but SQLite uses instr() instead.
    SUBSTRING may also appear as SUBSTR() depending on the database.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable, Iterable


# ---------------------------------------------------------------------------
# 1. BASIC PYTHON STRING CONCEPTS
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def subsection(title: str) -> None:
    print("\n" + "-" * 78)
    print(title)
    print("-" * 78)


section("1. Python foundations for SQL string functions")

first_name = "Atul"
last_name = "Pandey"

# Python uses + for string concatenation.
full_name = first_name + " " + last_name

# f-strings are often easier to read when several values are combined.
professional_name = f"{first_name} {last_name}"

print("First name:", first_name)
print("Last name:", last_name)
print("Concatenated name:", full_name)
print("Formatted name:", professional_name)

# len() corresponds conceptually to SQL LENGTH().
print("Length of full name:", len(full_name))

# Python string methods correspond closely to several SQL operations.
print("Lower:", full_name.lower())
print("Upper:", full_name.upper())
print("Trimmed:", "   Atul Pandey   ".strip())
print("Substring:", full_name[0:4])
print("Replaced:", full_name.replace("Atul", "A."))
print("Position of 'Pandey':", full_name.find("Pandey") + 1)


# ---------------------------------------------------------------------------
# 2. SQL DIALECT REFERENCE
# ---------------------------------------------------------------------------

section("2. SQL syntax reference")

print(
    """
Common SQL forms:

CONCAT:
    CONCAT(first_name, ' ', last_name)

LENGTH:
    LENGTH(full_name)

LOWER:
    LOWER(full_name)

UPPER:
    UPPER(full_name)

TRIM:
    TRIM(full_name)

SUBSTRING:
    SUBSTRING(full_name FROM 1 FOR 4)

REPLACE:
    REPLACE(email, '@old.com', '@new.com')

POSITION:
    POSITION('gmail' IN email)

Dialect differences matter:
    PostgreSQL:
        CONCAT(first_name, ' ', last_name)
        LENGTH(name)
        SUBSTRING(name FROM 1 FOR 4)
        POSITION('x' IN name)

    MySQL:
        CONCAT(first_name, ' ', last_name)
        LENGTH(name)
        SUBSTRING(name, 1, 4)
        LOCATE('x', name)

    SQLite:
        first_name || ' ' || last_name
        LENGTH(name)
        SUBSTR(name, 1, 4)
        instr(name, 'x')
    """
)


# ---------------------------------------------------------------------------
# 3. PYTHON FUNCTIONS THAT MODEL SQL BEHAVIOR
# ---------------------------------------------------------------------------

section("3. Reusable Python equivalents")

def sql_concat(*values: object) -> str:
    """
    Basic SQL-style concatenation.

    This implementation treats None as an empty string. Actual NULL behavior
    differs among SQL dialects and functions, so production SQL should follow
    the semantics of the target database.
    """
    return "".join("" if value is None else str(value) for value in values)


def sql_length(value: str | None) -> int | None:
    """Return the character count, preserving None as SQL-like NULL."""
    if value is None:
        return None
    return len(value)


def sql_lower(value: str | None) -> str | None:
    """Convert text to lowercase."""
    if value is None:
        return None
    return value.lower()


def sql_upper(value: str | None) -> str | None:
    """Convert text to uppercase."""
    if value is None:
        return None
    return value.upper()


def sql_trim(value: str | None, characters: str | None = None) -> str | None:
    """
    Remove whitespace or specified characters from both ends.

    SQL TRIM can support more detailed forms such as:
        TRIM(BOTH '-' FROM value)
    """
    if value is None:
        return None

    if characters is None:
        return value.strip()

    return value.strip(characters)


def sql_substring(
    value: str | None,
    start: int,
    length: int | None = None,
) -> str | None:
    """
    SQL-style one-based substring.

    Python slices are zero-based, while SQL substring positions are normally
    one-based. This function makes that distinction explicit.
    """
    if value is None:
        return None

    if start < 1:
        raise ValueError("SQL substring positions normally start at 1.")

    start_index = start - 1

    if length is None:
        return value[start_index:]

    if length < 0:
        raise ValueError("Substring length cannot be negative.")

    return value[start_index:start_index + length]


def sql_replace(
    value: str | None,
    old: str,
    new: str,
) -> str | None:
    """Replace every matching occurrence of old with new."""
    if value is None:
        return None
    return value.replace(old, new)


def sql_position(
    needle: str,
    haystack: str | None,
) -> int | None:
    """
    Return a one-based position.

    SQL POSITION conventionally returns:
        1-based position when found
        0 when not found
    """
    if haystack is None:
        return None

    index = haystack.find(needle)

    if index == -1:
        return 0

    return index + 1


sample = "   Atul Pandey   "

print("CONCAT:", sql_concat("Atul", " ", "Pandey"))
print("LENGTH:", sql_length("Atul Pandey"))
print("LOWER:", sql_lower("Atul Pandey"))
print("UPPER:", sql_upper("Atul Pandey"))
print("TRIM:", repr(sql_trim(sample)))
print("SUBSTRING:", sql_substring("Atul Pandey", 1, 4))
print("REPLACE:", sql_replace("atul@example.com", "@example.com", "@company.com"))
print("POSITION:", sql_position("Pandey", "Atul Pandey"))


# ---------------------------------------------------------------------------
# 4. CONCAT IN DEPTH
# ---------------------------------------------------------------------------

section("4. CONCAT")

subsection("Basic concatenation")

print(sql_concat("SQL", " ", "String", " ", "Functions"))

subsection("Combining database fields")

customer = {
    "first_name": "Anita",
    "middle_name": "K.",
    "last_name": "Sharma",
}

display_name = sql_concat(
    customer["first_name"],
    " ",
    customer["middle_name"],
    " ",
    customer["last_name"],
)

print(display_name)

subsection("NULL-like values")

print("With None:", repr(sql_concat("Atul", None, "Pandey")))

print(
    """
A major production concern is NULL behavior.

For example, some database expressions can produce NULL when one input is
NULL, while CONCAT-like functions in some systems treat NULL differently.

When portability matters, explicitly decide whether NULL should mean:
    - unknown value,
    - missing value,
    - empty value,
    - or an error condition.

Do not silently convert meaningful NULL values to empty strings without
considering the business meaning.
"""
)


# ---------------------------------------------------------------------------
# 5. LENGTH
# ---------------------------------------------------------------------------

section("5. LENGTH")

values = [
    "",
    "A",
    "Atul",
    "Atul Pandey",
    "  padded text  ",
    "café",
    "नमस्ते",
]

for value in values:
    print(repr(value), "=>", sql_length(value))

print(
    """
LENGTH is useful for:
    - validation
    - detecting empty values
    - identifying unusually long input
    - enforcing business rules
    - profiling data quality
    - measuring identifiers
    - preparing strings for further processing

Do not confuse character length with byte length. Different databases offer
different functions for byte-oriented measurements, and Unicode encoding can
cause the byte representation to be longer than the character count.
"""
)


# ---------------------------------------------------------------------------
# 6. LOWER AND UPPER
# ---------------------------------------------------------------------------

section("6. LOWER and UPPER")

mixed_text = "AtUl PaNdEy"

print("Original:", mixed_text)
print("LOWER:", sql_lower(mixed_text))
print("UPPER:", sql_upper(mixed_text))

emails = [
    "ATUL@EXAMPLE.COM",
    "Atul@Example.Com",
    "atul@example.com",
]

for email in emails:
    print(email, "=>", sql_lower(email))

print(
    """
LOWER is frequently used for normalization and case-insensitive matching.

Example conceptual SQL:

    WHERE LOWER(email) = LOWER(?)

This is simple, but applying a function to a database column can affect index
usage depending on the database and indexing strategy. Functional indexes,
computed columns, collations, or normalized storage may be better for large
tables.
"""
)


# ---------------------------------------------------------------------------
# 7. TRIM
# ---------------------------------------------------------------------------

section("7. TRIM")

dirty_values = [
    "  Atul Pandey  ",
    "\tAtul Pandey\t",
    "\nAtul Pandey\n",
    "-----Atul Pandey-----",
    "...Atul Pandey...",
]

for value in dirty_values:
    print(repr(value), "=>", repr(sql_trim(value)))

print("Custom character trim:", sql_trim("###Atul###", "#"))

print(
    """
TRIM normally removes characters from the boundaries, not from the middle.

    '  Atul  Pandey  '
        becomes
    'Atul  Pandey'

The internal spaces remain.

This distinction is important when cleaning names, addresses, identifiers,
CSV imports, form submissions, and user-entered search terms.
"""
)


# ---------------------------------------------------------------------------
# 8. SUBSTRING
# ---------------------------------------------------------------------------

section("8. SUBSTRING")

text = "DATABASE"

for start, length in [(1, 4), (5, 4), (2, 3), (4, None)]:
    print(
        f"SUBSTRING({text!r}, start={start}, length={length}) =",
        sql_substring(text, start, length),
    )

print(
    """
Important indexing distinction:

Python:
    text[0:4]

SQL:
    SUBSTRING(text FROM 1 FOR 4)

The first character is normally position 1 in SQL string functions, while
Python indexing begins at 0.

Substring is useful for:
    - extracting prefixes
    - extracting codes
    - parsing structured identifiers
    - masking sensitive values
    - extracting domain components
    - creating reporting labels
"""
)

try:
    print(sql_substring("DATABASE", 0, 3))
except ValueError as error:
    print("Expected validation error:", error)


# ---------------------------------------------------------------------------
# 9. REPLACE
# ---------------------------------------------------------------------------

section("9. REPLACE")

replacement_examples = [
    ("Hello World", "World", "SQL"),
    ("abc-abc-abc", "abc", "XYZ"),
    ("user@example.com", "@example.com", "@company.com"),
    ("  spaced  text  ", " ", "_"),
]

for original, old, new in replacement_examples:
    print(
        repr(original),
        "=>",
        repr(sql_replace(original, old, new)),
    )

print(
    """
REPLACE generally substitutes every matching occurrence.

It is useful for:
    - standardizing text
    - removing known unwanted characters
    - migration transformations
    - changing domains
    - creating normalized search values

Be careful with unrestricted REPLACE on structured data. Replacing a short
sequence can alter valid content unintentionally.
"""
)


# ---------------------------------------------------------------------------
# 10. POSITION
# ---------------------------------------------------------------------------

section("10. POSITION")

position_examples = [
    ("SQL", "SQL String Functions"),
    ("String", "SQL String Functions"),
    ("Functions", "SQL String Functions"),
    ("Missing", "SQL String Functions"),
    ("", "SQL String Functions"),
]

for needle, haystack in position_examples:
    print(
        f"POSITION({needle!r} IN {haystack!r}) =",
        sql_position(needle, haystack),
    )

print(
    """
POSITION answers a search question:

    Where does this substring begin?

The result is commonly one-based.

A return value of 0 conventionally indicates that a substring was not found
in several SQL implementations and related functions.

SQLite uses instr(haystack, needle), which also returns a one-based position
and returns 0 when the substring is absent.
"""
)


# ---------------------------------------------------------------------------
# 11. FUNCTION COMPOSITION
# ---------------------------------------------------------------------------

section("11. Combining multiple string functions")

raw_name = "   aTuL pAnDeY   "

normalized_name = sql_upper(
    sql_trim(raw_name)
)

print("Raw:", repr(raw_name))
print("Normalized:", normalized_name)

raw_email = "  ATUL.PANDEY@EXAMPLE.COM  "

normalized_email = sql_lower(sql_trim(raw_email))

print("Raw email:", repr(raw_email))
print("Normalized email:", normalized_email)

domain_position = sql_position("@", normalized_email)

if domain_position > 0:
    domain = sql_substring(normalized_email, domain_position + 1)
else:
    domain = None

print("Domain:", domain)

username = (
    sql_substring(normalized_email, 1, domain_position - 1)
    if domain_position > 0
    else None
)

print("Username:", username)


# ---------------------------------------------------------------------------
# 12. VALIDATION PIPELINE
# ---------------------------------------------------------------------------

section("12. Practical normalization pipeline")

@dataclass
class Contact:
    name: str
    email: str
    phone: str


def normalize_contact(contact: Contact) -> Contact:
    """
    Apply deterministic text normalization.

    This is intentionally conservative:
    - names are trimmed but internal capitalization is preserved
    - emails are trimmed and lowercased
    - phone numbers have common separators removed
    """
    normalized_name = sql_trim(contact.name)
    normalized_email = sql_lower(sql_trim(contact.email))

    normalized_phone = sql_replace(
        sql_replace(
            sql_replace(sql_trim(contact.phone), " ", ""),
            "-",
            "",
        ),
        "(",
        "",
    )
    normalized_phone = sql_replace(normalized_phone, ")", "")

    return Contact(
        name=normalized_name or "",
        email=normalized_email or "",
        phone=normalized_phone or "",
    )


contacts = [
    Contact("  Anita Sharma ", " ANITA@EXAMPLE.COM ", "+91 987-654-3210"),
    Contact("Rahul Verma", "RAHUL@EXAMPLE.COM", "(555) 123-4567"),
]

for contact in contacts:
    print("Before:", contact)
    print("After :", normalize_contact(contact))


# ---------------------------------------------------------------------------
# 13. SQLITE: ACTUAL EXECUTABLE SQL
# ---------------------------------------------------------------------------

section("13. Executing real SQL with SQLite")

connection = sqlite3.connect(":memory:")
cursor = connection.cursor()

cursor.execute(
    """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT,
        city TEXT
    )
    """
)

customers = [
    (1, "Atul", "Pandey", "ATUL@EXAMPLE.COM", "Lucknow"),
    (2, "Anita", "Sharma", " anita@example.com ", "Delhi"),
    (3, "Rahul", "Verma", "RAHUL@EXAMPLE.COM", "Mumbai"),
    (4, "Priya", "Singh", None, "Pune"),
]

cursor.executemany(
    """
    INSERT INTO customers
        (customer_id, first_name, last_name, email, city)
    VALUES (?, ?, ?, ?, ?)
    """,
    customers,
)

connection.commit()

subsection("CONCAT equivalent in SQLite")

cursor.execute(
    """
    SELECT
        customer_id,
        first_name || ' ' || last_name AS full_name
    FROM customers
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)

subsection("LENGTH")

cursor.execute(
    """
    SELECT
        customer_id,
        first_name,
        LENGTH(first_name) AS name_length
    FROM customers
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)

subsection("LOWER and UPPER")

cursor.execute(
    """
    SELECT
        customer_id,
        LOWER(email) AS lower_email,
        UPPER(city) AS upper_city
    FROM customers
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)

subsection("TRIM")

cursor.execute(
    """
    SELECT
        customer_id,
        email,
        TRIM(email) AS trimmed_email
    FROM customers
    WHERE email IS NOT NULL
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)

subsection("SUBSTRING through SQLite SUBSTR")

cursor.execute(
    """
    SELECT
        customer_id,
        first_name,
        SUBSTR(first_name, 1, 3) AS prefix
    FROM customers
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)

subsection("REPLACE")

cursor.execute(
    """
    SELECT
        customer_id,
        email,
        REPLACE(LOWER(TRIM(email)), '@example.com', '@company.com')
    FROM customers
    WHERE email IS NOT NULL
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)

subsection("POSITION equivalent through SQLite instr()")

cursor.execute(
    """
    SELECT
        customer_id,
        email,
        instr(LOWER(email), '@') AS at_position
    FROM customers
    WHERE email IS NOT NULL
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)


# ---------------------------------------------------------------------------
# 14. COMBINED SQL DATA-CLEANING QUERY
# ---------------------------------------------------------------------------

section("14. Combined SQL transformation")

cursor.execute(
    """
    SELECT
        customer_id,
        UPPER(TRIM(first_name || ' ' || last_name)) AS normalized_name,
        LOWER(TRIM(email)) AS normalized_email,
        LENGTH(TRIM(first_name || ' ' || last_name)) AS name_length,
        instr(LOWER(TRIM(email)), '@') AS at_position
    FROM customers
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)


# ---------------------------------------------------------------------------
# 15. EXTRACTING AN EMAIL DOMAIN
# ---------------------------------------------------------------------------

section("15. Extracting email domains")

cursor.execute(
    """
    SELECT
        customer_id,
        email,
        CASE
            WHEN email IS NOT NULL AND instr(TRIM(email), '@') > 0
            THEN SUBSTR(
                TRIM(email),
                instr(TRIM(email), '@') + 1
            )
            ELSE NULL
        END AS domain
    FROM customers
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)


# ---------------------------------------------------------------------------
# 16. EDGE CASES
# ---------------------------------------------------------------------------

section("16. Edge cases")

edge_cases = [
    "",
    " ",
    "   ",
    "A",
    "AAAAAAAAAA",
    "Atul Atul",
    None,
]

for value in edge_cases:
    print(
        "value=",
        repr(value),
        "| length=",
        sql_length(value),
        "| lower=",
        sql_lower(value),
        "| upper=",
        sql_upper(value),
        "| trim=",
        repr(sql_trim(value)),
    )

print(
    """
Important edge cases include:

1. Empty strings
2. NULL values
3. Strings containing only whitespace
4. Missing delimiters
5. Delimiters at the beginning or end
6. Multiple occurrences of a substring
7. Unicode characters
8. Very long text
9. Unexpected punctuation
10. Case differences
11. Leading and trailing whitespace
12. Invalid assumptions about substring positions
"""
)


# ---------------------------------------------------------------------------
# 17. EMAIL VALIDATION USING STRING FUNCTIONS
# ---------------------------------------------------------------------------

section("17. Practical email validation")

def looks_like_email(email: str | None) -> bool:
    """
    Lightweight structural validation.

    This intentionally does not attempt to implement the complete RFC email
    grammar. Production applications should use appropriate validation rules
    and should not assume that string functions alone prove deliverability.
    """
    if email is None:
        return False

    cleaned = sql_lower(sql_trim(email))

    if not cleaned:
        return False

    at_position = sql_position("@", cleaned)

    if at_position <= 1:
        return False

    if at_position >= len(cleaned):
        return False

    if sql_position(" ", cleaned) > 0:
        return False

    domain = sql_substring(cleaned, at_position + 1)

    if not domain or sql_position(".", domain) <= 0:
        return False

    return True


emails_to_validate = [
    "atul@example.com",
    " ATUL@EXAMPLE.COM ",
    "missing-at-symbol.example.com",
    "@example.com",
    "user@",
    "user example@example.com",
    "user@example",
]

for email in emails_to_validate:
    print(repr(email), "=>", looks_like_email(email))


# ---------------------------------------------------------------------------
# 18. DATA QUALITY REPORT
# ---------------------------------------------------------------------------

section("18. Data quality analysis")

cursor.execute(
    """
    SELECT
        COUNT(*) AS total_customers,
        SUM(
            CASE
                WHEN email IS NULL OR TRIM(email) = ''
                THEN 1
                ELSE 0
            END
        ) AS missing_email_count,
        SUM(
            CASE
                WHEN email IS NOT NULL
                     AND instr(TRIM(email), '@') = 0
                THEN 1
                ELSE 0
            END
        ) AS malformed_email_count
    FROM customers
    """
)

print(cursor.fetchone())


# ---------------------------------------------------------------------------
# 19. SEARCH AND NORMALIZATION
# ---------------------------------------------------------------------------

section("19. Case-normalized searching")

search_term = "atul"

cursor.execute(
    """
    SELECT
        customer_id,
        first_name,
        last_name
    FROM customers
    WHERE LOWER(first_name) = LOWER(?)
    """,
    (search_term,),
)

print("Search result:", cursor.fetchall())


# ---------------------------------------------------------------------------
# 20. PERFORMANCE CONSIDERATIONS
# ---------------------------------------------------------------------------

section("20. Performance considerations")

print(
    """
String functions are generally inexpensive for individual values, but their
cost becomes important when applied to millions of rows.

Potential issues:

    WHERE LOWER(email) = LOWER(?)

may require transforming many stored values before comparison.

Possible strategies include:
    - storing normalized values
    - using appropriate collations
    - creating functional indexes where supported
    - using generated/computed columns
    - indexing normalized search columns
    - avoiding unnecessary repeated transformations
    - performing data cleanup during ingestion

The correct solution depends on database engine, workload, collation,
character set, index design, and query planner behavior.
"""
)


# ---------------------------------------------------------------------------
# 21. SECURITY CONSIDERATIONS
# ---------------------------------------------------------------------------

section("21. Security considerations")

print(
    """
String functions themselves do not make SQL queries safe.

Never construct SQL using untrusted values through string concatenation.

Unsafe conceptual pattern:
    SQL = "SELECT ... WHERE name = '" + user_input + "'"

Preferred pattern:
    SQL = "SELECT ... WHERE name = ?"
    cursor.execute(SQL, (user_input,))

Parameterized queries separate SQL instructions from data and reduce the risk
of SQL injection.

String functions can still be useful for validation and normalization, but
validation is not a replacement for parameterized SQL.
"""
)


# ---------------------------------------------------------------------------
# 22. COMMON MISTAKES
# ---------------------------------------------------------------------------

section("22. Common mistakes")

mistakes = {
    "Using Python zero-based indexing as if it were SQL one-based indexing":
        "Convert positions carefully.",
    "Assuming every database has identical string syntax":
        "Check the target database dialect.",
    "Treating NULL as an empty string":
        "Decide explicitly what NULL means.",
    "Using TRIM to remove internal spaces":
        "TRIM normally affects boundaries only.",
    "Assuming LENGTH always means byte length":
        "Character and byte length can differ.",
    "Using LOWER() on every indexed search column":
        "Check query plans and indexing strategy.",
    "Using REPLACE without understanding all matches":
        "REPLACE can modify every occurrence.",
    "Assuming POSITION proves a valid structure":
        "Position checks provide structure clues, not complete validation.",
}

for mistake, correction in mistakes.items():
    print(f"- {mistake}: {correction}")


# ---------------------------------------------------------------------------
# 23. SIMPLE TESTS
# ---------------------------------------------------------------------------

section("23. Executable tests")

def run_tests() -> None:
    assert sql_concat("A", "B") == "AB"
    assert sql_concat("A", None, "B") == "AB"
    assert sql_length("ABC") == 3
    assert sql_length("") == 0
    assert sql_length(None) is None
    assert sql_lower("ABC") == "abc"
    assert sql_upper("abc") == "ABC"
    assert sql_trim("  ABC  ") == "ABC"
    assert sql_trim("###ABC###", "#") == "ABC"
    assert sql_substring("DATABASE", 1, 4) == "DATA"
    assert sql_substring("DATABASE", 5, 4) == "BASE"
    assert sql_replace("a-b-c", "-", "_") == "a_b_c"
    assert sql_position("DATA", "DATABASE") == 1
    assert sql_position("BASE", "DATABASE") == 5
    assert sql_position("XYZ", "DATABASE") == 0

    try:
        sql_substring("ABC", 0, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for start position 0.")

    print("All tests passed.")


run_tests()


# ---------------------------------------------------------------------------
# 24. FINAL SQL EXAMPLE: CUSTOMER DISPLAY RECORD
# ---------------------------------------------------------------------------

section("24. Final integrated SQL example")

cursor.execute(
    """
    SELECT
        customer_id,
        UPPER(TRIM(first_name || ' ' || last_name)) AS display_name,
        LOWER(TRIM(email)) AS normalized_email,
        LENGTH(TRIM(first_name || ' ' || last_name)) AS display_name_length,
        CASE
            WHEN email IS NULL OR TRIM(email) = ''
                THEN 'MISSING'
            WHEN instr(TRIM(email), '@') = 0
                THEN 'INVALID'
            ELSE 'PRESENT'
        END AS email_status
    FROM customers
    ORDER BY customer_id
    """
)

for row in cursor.fetchall():
    print(row)


# ---------------------------------------------------------------------------
# 25. CLEANUP
# ---------------------------------------------------------------------------

connection.close()

print(
    """
Study checkpoint:

CONCAT     -> combines values
LENGTH     -> measures string length
LOWER      -> normalizes text to lowercase
UPPER      -> normalizes text to uppercase
TRIM       -> removes unwanted boundary characters
SUBSTRING  -> extracts a portion of text
REPLACE    -> substitutes matching text
POSITION   -> locates a substring

The most important practical skill is not memorizing isolated functions.
It is understanding how they can be composed into reliable data cleaning,
validation, transformation, search, reporting, and application workflows.
"""
)
