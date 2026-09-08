"""
SQL Data Types: INTEGER, NUMERIC, DECIMAL, VARCHAR, TEXT, BOOLEAN,
DATE, TIME, and TIMESTAMP

This self-contained study script teaches SQL data type concepts through Python
simulations and SQLite examples.

SQLite is included with Python and is used here because it allows executable SQL
examples without requiring an external database server.

Important portability note:
SQL data type behavior differs between database systems such as PostgreSQL,
MySQL, SQL Server, Oracle, and SQLite. SQLite uses a flexible type system based
on type affinity, so some examples demonstrate SQL concepts generally while
also showing SQLite-specific behavior.
"""

from __future__ import annotations

import datetime as dt
import decimal
import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable


# =============================================================================
# 1. FUNDAMENTAL CONCEPT: WHAT IS A DATA TYPE?
# =============================================================================

"""
A data type defines the kind of value a database column is intended to store.

Examples:

    INTEGER     -> whole numbers
    DECIMAL     -> exact fixed-point numbers
    NUMERIC     -> exact numeric values with configurable precision and scale
    VARCHAR     -> variable-length bounded strings
    TEXT        -> text strings, often without a practical length limit
    BOOLEAN     -> logical true/false values
    DATE        -> calendar dates
    TIME        -> times of day
    TIMESTAMP   -> date and time values

Data types influence:

- Storage
- Validation
- Arithmetic
- Comparisons
- Sorting
- Index behavior
- Precision
- Application compatibility
- Query correctness

A good schema assigns each column a type that represents the meaning of the
data, not merely the current appearance of the values.
"""


# =============================================================================
# 2. TERMINOLOGY: VALUES, COLUMNS, ROWS, TABLES, AND NULL
# =============================================================================

@dataclass
class ColumnExample:
    name: str
    sql_type: str
    example_value: Any
    meaning: str


COLUMN_EXAMPLES = [
    ColumnExample("employee_id", "INTEGER", 101, "Whole-number identifier"),
    ColumnExample("salary", "DECIMAL(12, 2)", "75000.50", "Exact monetary amount"),
    ColumnExample("rating", "NUMERIC(4, 2)", "4.75", "Exact value with scale"),
    ColumnExample("username", "VARCHAR(50)", "alex_2026", "Bounded text"),
    ColumnExample("description", "TEXT", "Long product description", "Long-form text"),
    ColumnExample("is_active", "BOOLEAN", True, "Logical state"),
    ColumnExample("birth_date", "DATE", "1993-05-18", "Calendar date"),
    ColumnExample("start_time", "TIME", "09:30:00", "Time of day"),
    ColumnExample(
        "created_at",
        "TIMESTAMP",
        "2026-09-08 11:30:00",
        "Date and time",
    ),
]


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def display_column_examples() -> None:
    print_section("DATA TYPE TERMINOLOGY")

    for example in COLUMN_EXAMPLES:
        print(
            f"{example.name:<15} | "
            f"{example.sql_type:<20} | "
            f"{str(example.example_value):<25} | "
            f"{example.meaning}"
        )


# =============================================================================
# 3. NULL: THE ABSENCE OF A VALUE
# =============================================================================

"""
NULL is not a normal data type in the same sense as INTEGER or TEXT.

NULL represents an unknown, missing, unavailable, or inapplicable value.

Important SQL behavior:

    NULL = NULL

does not evaluate to TRUE. SQL uses three-valued logic:

    TRUE
    FALSE
    UNKNOWN

A comparison involving NULL usually produces UNKNOWN.

Correct SQL checks:

    column_name IS NULL
    column_name IS NOT NULL

Incorrect:

    column_name = NULL
"""


def demonstrate_null_logic() -> None:
    print_section("NULL AND THREE-VALUED LOGIC")

    values = [10, None, 20]

    for value in values:
        python_result = value == None  # Demonstration only; "is None" is preferred.
        print(f"Python value: {value!r:<6} | value == None -> {python_result}")

    print(
        "\nIn Python, use 'is None'. In SQL, use IS NULL rather than = NULL."
    )


# =============================================================================
# 4. INTEGER
# =============================================================================

"""
INTEGER stores whole numbers.

Examples:

    -10
    0
    1
    250000

INTEGER does not represent fractional values such as:

    3.14
    10.50

Common uses:

- Primary keys
- Counts
- Quantities
- Ages
- Sequence numbers
- Boolean representations in databases without a dedicated BOOLEAN type

Important considerations:

- Integer ranges differ by database and integer subtype.
- Some systems provide SMALLINT, INTEGER, BIGINT, and related types.
- Overflow behavior differs between database systems.
"""


def integer_examples() -> None:
    print_section("INTEGER")

    employee_count = 125
    items_sold = 42
    stock_change = -7

    print("employee_count:", employee_count)
    print("items_sold:", items_sold)
    print("stock_change:", stock_change)

    print("\nInteger arithmetic:")
    print("42 + 8 =", 42 + 8)
    print("42 * 3 =", 42 * 3)

    # Python demonstrates the conceptual difference between integer and decimal
    # values, although exact SQL behavior depends on the database engine.
    print("\nType distinction:")
    print("Type of 42:", type(42).__name__)
    print("Type of 42.0:", type(42.0).__name__)


# =============================================================================
# 5. NUMERIC AND DECIMAL
# =============================================================================

"""
NUMERIC and DECIMAL represent exact decimal values in many SQL database systems.

Typical syntax:

    DECIMAL(precision, scale)
    NUMERIC(precision, scale)

Precision:
    Total number of significant decimal digits.

Scale:
    Number of digits to the right of the decimal point.

Example:

    DECIMAL(8, 2)

allows up to 8 total digits, including 2 digits after the decimal point.

Examples of values conceptually fitting DECIMAL(8, 2):

    123456.78
    10.50
    -999.99

A value with more fractional digits may be rounded, rejected, or handled
differently depending on the database system and configuration.

DECIMAL/NUMERIC are usually preferable to binary floating-point values for
currency and other values where decimal exactness matters.
"""


def decimal_examples() -> None:
    print_section("NUMERIC AND DECIMAL")

    # Floating-point arithmetic can produce binary representation artifacts.
    floating_result = 0.1 + 0.2

    # Decimal uses decimal arithmetic and is conceptually closer to SQL DECIMAL.
    decimal_result = decimal.Decimal("0.1") + decimal.Decimal("0.2")

    print("Floating-point 0.1 + 0.2:", floating_result)
    print("Decimal       0.1 + 0.2:", decimal_result)

    price = decimal.Decimal("19.99")
    quantity = decimal.Decimal("3")
    total = price * quantity

    print("\nExact decimal arithmetic:")
    print("Price:", price)
    print("Quantity:", quantity)
    print("Total:", total)


def validate_precision_scale(
    value: str,
    precision: int,
    scale: int,
) -> bool:
    """
    Simulate DECIMAL(precision, scale) validation.

    This is a conceptual validator for educational purposes. Exact SQL database
    behavior can differ.

    Examples:
        validate_precision_scale("123.45", 5, 2) -> True
        validate_precision_scale("1234.56", 5, 2) -> False
        validate_precision_scale("12.345", 5, 2) -> False
    """

    try:
        parsed = decimal.Decimal(value)
    except decimal.InvalidOperation:
        return False

    sign, digits, exponent = parsed.as_tuple()
    digit_count = len(digits)

    if exponent >= 0:
        fractional_digits = 0
        integer_digits = digit_count + exponent
    else:
        fractional_digits = -exponent
        integer_digits = digit_count - fractional_digits

        # Numbers such as 0.01 require conceptual handling because Decimal's
        # tuple representation may not directly reflect visible leading zeros.
        integer_digits = max(integer_digits, 0)

    total_digits = integer_digits + fractional_digits

    return (
        fractional_digits <= scale
        and total_digits <= precision
    )


def demonstrate_precision_scale() -> None:
    print_section("DECIMAL PRECISION AND SCALE")

    precision = 6
    scale = 2

    test_values = [
        "1234.56",
        "12345.67",
        "12.345",
        "-999.99",
        "0.01",
    ]

    print(f"Conceptual validation for DECIMAL({precision}, {scale}):")

    for value in test_values:
        valid = validate_precision_scale(value, precision, scale)
        print(f"{value:>10} -> {valid}")


# =============================================================================
# 6. INTEGER VS NUMERIC VS DECIMAL
# =============================================================================

def compare_numeric_types() -> None:
    print_section("INTEGER VS NUMERIC VS DECIMAL")

    comparison = [
        (
            "INTEGER",
            "Whole numbers",
            "Counts, identifiers, quantities",
            "No fractional component",
        ),
        (
            "NUMERIC",
            "Exact decimal numbers",
            "Measurements, finance",
            "Precision/scale behavior varies by DBMS",
        ),
        (
            "DECIMAL",
            "Exact decimal numbers",
            "Currency, prices",
            "Precision/scale behavior varies by DBMS",
        ),
    ]

    for name, representation, use_case, limitation in comparison:
        print(f"\n{name}")
        print("  Representation:", representation)
        print("  Typical use:    ", use_case)
        print("  Consideration:  ", limitation)


# =============================================================================
# 7. VARCHAR
# =============================================================================

"""
VARCHAR stores variable-length character strings.

Typical syntax:

    VARCHAR(50)

The number usually represents a maximum length in characters, although exact
behavior and enforcement can vary by database system and configuration.

Examples:

    VARCHAR(20) -> "alex"
    VARCHAR(50) -> "employee@example.com"

VARCHAR is commonly used for:

- Names
- Email addresses
- Usernames
- Phone numbers
- Codes
- Short labels

A VARCHAR length is not a substitute for complete semantic validation.

For example, VARCHAR(254) can limit email length, but it does not guarantee that
a value is a valid email address.
"""


def varchar_examples() -> None:
    print_section("VARCHAR")

    maximum_length = 10

    test_values = [
        "Alice",
        "Alexander",
        "VeryLongUsername",
        "",
    ]

    for value in test_values:
        is_valid = len(value) <= maximum_length
        print(
            f"Value: {value!r:<20} "
            f"Length: {len(value):<3} "
            f"Fits VARCHAR({maximum_length}): {is_valid}"
        )


def validate_varchar(value: str, maximum_length: int) -> bool:
    """
    Conceptual VARCHAR length validation.

    SQL databases may differ in character counting, collation, encoding, and
    enforcement details.
    """
    return len(value) <= maximum_length


# =============================================================================
# 8. TEXT
# =============================================================================

"""
TEXT represents textual data.

It is commonly used for:

- Descriptions
- Articles
- Comments
- Notes
- Logs
- Long-form content

TEXT differs from VARCHAR mainly in intended schema semantics and length
constraints. Exact storage and performance differences depend on the database.

Choosing TEXT simply because the maximum possible length is unknown can reduce
schema-level validation. When a field has a meaningful business limit, an
appropriate VARCHAR limit or explicit CHECK constraint can improve validation.
"""


def text_examples() -> None:
    print_section("TEXT")

    article = (
        "A text column is suitable for content whose practical length may be "
        "substantially larger than a short identifier or label."
    )

    print("Stored text:")
    print(article)
    print("Character count:", len(article))


# =============================================================================
# 9. VARCHAR VS TEXT
# =============================================================================

def compare_varchar_and_text() -> None:
    print_section("VARCHAR VS TEXT")

    print("VARCHAR")
    print("  Intended for bounded variable-length strings.")
    print("  Useful when maximum length is part of the business rule.")
    print("  Example: VARCHAR(100) for a product name.")

    print("\nTEXT")
    print("  Intended for larger or less predictably bounded text.")
    print("  Useful for descriptions, comments, and article content.")
    print("  Example: TEXT for a detailed product description.")


# =============================================================================
# 10. BOOLEAN
# =============================================================================

"""
BOOLEAN represents logical truth values.

Typical values:

    TRUE
    FALSE

Some database systems have a dedicated BOOLEAN type. Others internally store
boolean values using integer-like representations.

SQLite accepts many type declarations but does not have a separate native
BOOLEAN storage class. A common representation is:

    1 -> true
    0 -> false

Schema constraints can restrict values to 0 and 1.
"""


def boolean_examples() -> None:
    print_section("BOOLEAN")

    is_active = True
    is_verified = False

    print("is_active:", is_active)
    print("is_verified:", is_verified)

    integer_true = 1
    integer_false = 0

    print("\nInteger representation:")
    print("1 interpreted as true:", bool(integer_true))
    print("0 interpreted as false:", bool(integer_false))


def normalize_boolean(value: Any) -> bool:
    """
    Convert selected representations to a Python boolean.

    This demonstrates application-level normalization.

    Accepted true representations:
        True, 1, "true", "yes", "1"

    Accepted false representations:
        False, 0, "false", "no", "0"
    """

    if value is True or value == 1:
        return True

    if value is False or value == 0:
        return False

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {"true", "yes", "1"}:
            return True

        if normalized in {"false", "no", "0"}:
            return False

    raise ValueError(f"Cannot normalize {value!r} as a boolean.")


def demonstrate_boolean_normalization() -> None:
    print_section("BOOLEAN NORMALIZATION")

    values = [True, False, 1, 0, "YES", "false", "unknown"]

    for value in values:
        try:
            result = normalize_boolean(value)
            print(f"{value!r:<10} -> {result}")
        except ValueError as error:
            print(f"{value!r:<10} -> ERROR: {error}")


# =============================================================================
# 11. DATE
# =============================================================================

"""
DATE represents a calendar date without a time-of-day component.

Typical conceptual format:

    YYYY-MM-DD

Examples:

    2026-09-08
    1993-05-18

Common uses:

- Birth dates
- Order dates
- Holidays
- Contract dates
- Due dates

A DATE should normally be preferred over TIMESTAMP when time of day is
meaningless to the business concept.
"""


def date_examples() -> None:
    print_section("DATE")

    today = dt.date.today()
    birth_date = dt.date(1993, 5, 18)

    age_approximation = today.year - birth_date.year

    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age_approximation -= 1

    print("Today's date:", today.isoformat())
    print("Birth date:", birth_date.isoformat())
    print("Approximate age:", age_approximation)


def parse_iso_date(value: str) -> dt.date:
    """
    Parse an ISO 8601 calendar date.

    Raises ValueError when the date is invalid.
    """
    return dt.date.fromisoformat(value)


def demonstrate_invalid_dates() -> None:
    print_section("DATE VALIDATION")

    values = [
        "2026-09-08",
        "2026-02-29",
        "2024-02-29",
        "2026-13-01",
    ]

    for value in values:
        try:
            parsed = parse_iso_date(value)
            print(f"{value} -> valid date: {parsed}")
        except ValueError as error:
            print(f"{value} -> invalid: {error}")


# =============================================================================
# 12. TIME
# =============================================================================

"""
TIME represents a time of day without a calendar date.

Typical conceptual format:

    HH:MM:SS

Examples:

    09:30:00
    17:45:12

TIME is useful for:

- Opening times
- Appointment times
- Daily schedules
- Shift start times

TIME alone cannot identify a unique moment in history because it contains no
date and usually no timezone context.
"""


def time_examples() -> None:
    print_section("TIME")

    opening_time = dt.time(9, 30, 0)
    closing_time = dt.time(18, 0, 0)

    print("Opening time:", opening_time.isoformat())
    print("Closing time:", closing_time.isoformat())

    print("Opening occurs before closing:", opening_time < closing_time)


def parse_iso_time(value: str) -> dt.time:
    """Parse a time value in an ISO-compatible format."""
    return dt.time.fromisoformat(value)


def demonstrate_invalid_times() -> None:
    print_section("TIME VALIDATION")

    values = [
        "09:30:00",
        "23:59:59",
        "24:00:00",
        "12:61:00",
    ]

    for value in values:
        try:
            parsed = parse_iso_time(value)
            print(f"{value} -> valid time: {parsed}")
        except ValueError as error:
            print(f"{value} -> invalid: {error}")


# =============================================================================
# 13. TIMESTAMP
# =============================================================================

"""
TIMESTAMP represents both a calendar date and a time.

Conceptual examples:

    2026-09-08 11:30:00
    2026-09-08T11:30:00

Common uses:

- Record creation times
- Login events
- Transaction events
- Audit information
- Scheduled execution times

Timezone handling is critical.

Database systems differ in their timestamp types. For example, some distinguish
between timestamp values with timezone awareness and values without timezone
awareness.

A timezone-naive timestamp such as:

    2026-09-08 09:00:00

does not independently identify which geographical time zone the value refers to.

For events representing real-world moments, storing an unambiguous UTC instant
or using an appropriate timezone-aware database type is often safer.
"""


def timestamp_examples() -> None:
    print_section("TIMESTAMP")

    naive_timestamp = dt.datetime(2026, 9, 8, 11, 30, 0)

    utc_timestamp = dt.datetime(
        2026,
        9,
        8,
        6,
        0,
        0,
        tzinfo=dt.timezone.utc,
    )

    print("Naive timestamp:", naive_timestamp)
    print("Timezone-aware UTC timestamp:", utc_timestamp)


def demonstrate_timezone_conversion() -> None:
    print_section("TIMEZONE-AWARE TIMESTAMP")

    utc = dt.timezone.utc
    india_standard_time = dt.timezone(dt.timedelta(hours=5, minutes=30))

    utc_event = dt.datetime(
        2026,
        9,
        8,
        6,
        0,
        0,
        tzinfo=utc,
    )

    local_event = utc_event.astimezone(india_standard_time)

    print("UTC event:", utc_event.isoformat())
    print("Converted event:", local_event.isoformat())

    print(
        "\nBoth values represent the same instant but display different "
        "local clock times."
    )


# =============================================================================
# 14. DATE VS TIME VS TIMESTAMP
# =============================================================================

def compare_temporal_types() -> None:
    print_section("DATE VS TIME VS TIMESTAMP")

    comparisons = [
        (
            "DATE",
            "Calendar day only",
            "2026-09-08",
            "Birthday, due date",
        ),
        (
            "TIME",
            "Time of day only",
            "09:30:00",
            "Daily opening time",
        ),
        (
            "TIMESTAMP",
            "Date and time",
            "2026-09-08 09:30:00",
            "Event creation time",
        ),
    ]

    for type_name, content, example, use_case in comparisons:
        print(
            f"{type_name:<12} | "
            f"{content:<25} | "
            f"{example:<22} | "
            f"{use_case}"
        )


# =============================================================================
# 15. SQLITE DATABASE SETUP
# =============================================================================

"""
The following examples execute actual SQL using sqlite3.

SQLite is embedded and requires no external server.

Important SQLite characteristics:

- Flexible typing
- Storage classes differ from many strictly typed databases
- Declared SQL types generally provide type affinity
- BOOLEAN is commonly represented using integers
- DATE, TIME, and TIMESTAMP are commonly stored using TEXT, INTEGER, or REAL
  representations depending on application design

Therefore, the SQL examples demonstrate general SQL schema design while also
showing practical SQLite behavior.
"""


def create_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")

    # Return rows with column names.
    connection.row_factory = sqlite3.Row

    # Enforce foreign keys if they are used.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# =============================================================================
# 16. CREATE TABLE WITH THE REQUESTED DATA TYPES
# =============================================================================

def create_demo_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE data_type_demo (
            id INTEGER PRIMARY KEY,
            whole_number INTEGER NOT NULL,
            numeric_value NUMERIC,
            decimal_value DECIMAL(12, 2),
            short_text VARCHAR(50),
            long_text TEXT,
            is_active BOOLEAN NOT NULL CHECK (is_active IN (0, 1)),
            event_date DATE,
            event_time TIME,
            created_at TIMESTAMP
        )
        """
    )

    connection.commit()


def insert_demo_data(connection: sqlite3.Connection) -> None:
    rows = [
        (
            1,
            42,
            "12345.678",
            "19.99",
            "Alice",
            "A short demonstration row.",
            1,
            "2026-09-08",
            "09:30:00",
            "2026-09-08 09:30:00",
        ),
        (
            2,
            -7,
            "0.001",
            "999999.99",
            "Bob",
            "This row contains a longer text value.",
            0,
            "2024-02-29",
            "23:59:59",
            "2026-09-08 18:00:00",
        ),
        (
            3,
            0,
            None,
            None,
            None,
            None,
            1,
            None,
            None,
            None,
        ),
    ]

    connection.executemany(
        """
        INSERT INTO data_type_demo (
            id,
            whole_number,
            numeric_value,
            decimal_value,
            short_text,
            long_text,
            is_active,
            event_date,
            event_time,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    connection.commit()


def display_sqlite_rows(connection: sqlite3.Connection) -> None:
    print_section("SQLITE TABLE DATA")

    cursor = connection.execute(
        """
        SELECT
            id,
            whole_number,
            numeric_value,
            decimal_value,
            short_text,
            long_text,
            is_active,
            event_date,
            event_time,
            created_at
        FROM data_type_demo
        ORDER BY id
        """
    )

    for row in cursor:
        print(dict(row))


# =============================================================================
# 17. SQLITE STORAGE TYPE INSPECTION
# =============================================================================

def inspect_sqlite_types(connection: sqlite3.Connection) -> None:
    print_section("SQLITE RUNTIME STORAGE TYPES")

    cursor = connection.execute(
        """
        SELECT
            id,
            typeof(whole_number) AS whole_number_type,
            typeof(numeric_value) AS numeric_value_type,
            typeof(decimal_value) AS decimal_value_type,
            typeof(short_text) AS short_text_type,
            typeof(long_text) AS long_text_type,
            typeof(is_active) AS is_active_type,
            typeof(event_date) AS event_date_type,
            typeof(event_time) AS event_time_type,
            typeof(created_at) AS created_at_type
        FROM data_type_demo
        ORDER BY id
        """
    )

    for row in cursor:
        print(dict(row))


# =============================================================================
# 18. INTEGER EDGE CASES AND CONSTRAINTS
# =============================================================================

def demonstrate_integer_constraints(connection: sqlite3.Connection) -> None:
    print_section("INTEGER CONSTRAINTS AND EDGE CASES")

    connection.execute(
        """
        CREATE TABLE inventory (
            item_id INTEGER PRIMARY KEY,
            quantity INTEGER NOT NULL CHECK (quantity >= 0)
        )
        """
    )

    connection.execute(
        "INSERT INTO inventory (item_id, quantity) VALUES (?, ?)",
        (1, 25),
    )

    try:
        connection.execute(
            "INSERT INTO inventory (item_id, quantity) VALUES (?, ?)",
            (2, -5),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        print("Negative quantity rejected by CHECK constraint:")
        print(" ", error)
        connection.rollback()

    row = connection.execute(
        "SELECT item_id, quantity FROM inventory"
    ).fetchone()

    print("Stored inventory row:", dict(row))


# =============================================================================
# 19. NUMERIC AND DECIMAL: MONEY DESIGN
# =============================================================================

def calculate_invoice_total() -> None:
    print_section("MONEY AND DECIMAL DESIGN")

    line_items = [
        ("Notebook", decimal.Decimal("49.99"), decimal.Decimal("2")),
        ("Pen", decimal.Decimal("9.50"), decimal.Decimal("3")),
        ("Bag", decimal.Decimal("999.00"), decimal.Decimal("1")),
    ]

    total = decimal.Decimal("0.00")

    for product, unit_price, quantity in line_items:
        line_total = unit_price * quantity
        total += line_total

        print(
            f"{product:<10} "
            f"price={unit_price:<8} "
            f"quantity={quantity:<3} "
            f"line_total={line_total}"
        )

    print("Invoice total:", total)

    # Financial systems often need explicit rounding rules.
    rounded_total = total.quantize(
        decimal.Decimal("0.01"),
        rounding=decimal.ROUND_HALF_UP,
    )

    print("Rounded total:", rounded_total)


# =============================================================================
# 20. TEXT VALIDATION AND BUSINESS RULES
# =============================================================================

def validate_username(username: str) -> bool:
    """
    Demonstrates that a SQL type alone is insufficient for semantic validation.

    Rules:
    - Length from 3 to 20 characters
    - Only letters, digits, underscore
    """

    if not 3 <= len(username) <= 20:
        return False

    return all(
        character.isalnum() or character == "_"
        for character in username
    )


def demonstrate_text_validation() -> None:
    print_section("VARCHAR PLUS APPLICATION VALIDATION")

    usernames = [
        "alex",
        "ab",
        "valid_user_123",
        "name with spaces",
        "very_very_very_long_username",
    ]

    for username in usernames:
        print(
            f"{username!r:<32} "
            f"valid={validate_username(username)}"
        )


# =============================================================================
# 21. BOOLEAN DATABASE CONSTRAINTS
# =============================================================================

def demonstrate_boolean_constraints(connection: sqlite3.Connection) -> None:
    print_section("BOOLEAN CONSTRAINTS")

    connection.execute(
        """
        CREATE TABLE user_status (
            user_id INTEGER PRIMARY KEY,
            is_active BOOLEAN NOT NULL CHECK (is_active IN (0, 1))
        )
        """
    )

    connection.execute(
        "INSERT INTO user_status (user_id, is_active) VALUES (?, ?)",
        (1, 1),
    )

    try:
        connection.execute(
            "INSERT INTO user_status (user_id, is_active) VALUES (?, ?)",
            (2, 5),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        print("Invalid boolean representation rejected:")
        print(" ", error)
        connection.rollback()

    rows = connection.execute(
        "SELECT user_id, is_active FROM user_status"
    ).fetchall()

    for row in rows:
        print(dict(row))


# =============================================================================
# 22. DATE VALIDATION IN SQL
# =============================================================================

def demonstrate_date_storage(connection: sqlite3.Connection) -> None:
    print_section("DATE STORAGE")

    connection.execute(
        """
        CREATE TABLE appointments (
            appointment_id INTEGER PRIMARY KEY,
            appointment_date DATE NOT NULL
        )
        """
    )

    connection.execute(
        """
        INSERT INTO appointments (appointment_id, appointment_date)
        VALUES (?, ?)
        """,
        (1, "2026-09-08"),
    )

    row = connection.execute(
        """
        SELECT
            appointment_id,
            appointment_date,
            typeof(appointment_date) AS storage_type
        FROM appointments
        """
    ).fetchone()

    print(dict(row))


# =============================================================================
# 23. TEMPORAL ORDERING
# =============================================================================

def demonstrate_temporal_ordering(connection: sqlite3.Connection) -> None:
    print_section("TEMPORAL ORDERING")

    connection.execute(
        """
        CREATE TABLE events (
            event_id INTEGER PRIMARY KEY,
            event_name VARCHAR(100) NOT NULL,
            event_timestamp TIMESTAMP NOT NULL
        )
        """
    )

    rows = [
        (1, "Deployment", "2026-09-08 10:00:00"),
        (2, "Backup", "2026-09-08 02:00:00"),
        (3, "Report", "2026-09-09 09:00:00"),
    ]

    connection.executemany(
        """
        INSERT INTO events (event_id, event_name, event_timestamp)
        VALUES (?, ?, ?)
        """,
        rows,
    )

    cursor = connection.execute(
        """
        SELECT event_name, event_timestamp
        FROM events
        ORDER BY event_timestamp
        """
    )

    for row in cursor:
        print(f"{row['event_timestamp']} -> {row['event_name']}")

    print(
        "\nISO-like YYYY-MM-DD HH:MM:SS text formats sort chronologically "
        "when formatting is consistent."
    )


# =============================================================================
# 24. SQL PARAMETERIZATION AND TYPE SAFETY
# =============================================================================

"""
Parameterized SQL separates SQL code from values.

Unsafe string construction can create SQL injection vulnerabilities.

Unsafe conceptual example:

    query = "SELECT * FROM users WHERE username = '" + username + "'"

Safer approach:

    SELECT * FROM users WHERE username = ?

with the value supplied separately.

Parameterization is especially important for TEXT and VARCHAR values originating
from users or external systems.
"""


def demonstrate_parameterized_queries(connection: sqlite3.Connection) -> None:
    print_section("PARAMETERIZED QUERIES")

    connection.execute(
        """
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            username VARCHAR(50) NOT NULL
        )
        """
    )

    connection.executemany(
        "INSERT INTO users (user_id, username) VALUES (?, ?)",
        [
            (1, "alice"),
            (2, "bob"),
            (3, "charlie"),
        ],
    )

    requested_username = "bob"

    row = connection.execute(
        """
        SELECT user_id, username
        FROM users
        WHERE username = ?
        """,
        (requested_username,),
    ).fetchone()

    print("Requested username:", requested_username)
    print("Result:", dict(row) if row else None)

    malicious_looking_input = "' OR 1=1 --"

    safe_result = connection.execute(
        """
        SELECT user_id, username
        FROM users
        WHERE username = ?
        """,
        (malicious_looking_input,),
    ).fetchall()

    print("\nParameterized query with malicious-looking input:")
    print("Returned rows:", [dict(row) for row in safe_result])


# =============================================================================
# 25. TYPE AFFINITY AND DATABASE PORTABILITY
# =============================================================================

def demonstrate_sqlite_affinity(connection: sqlite3.Connection) -> None:
    print_section("SQLITE TYPE AFFINITY")

    connection.execute(
        """
        CREATE TABLE affinity_demo (
            integer_column INTEGER,
            numeric_column NUMERIC,
            decimal_column DECIMAL(10, 2),
            varchar_column VARCHAR(20),
            text_column TEXT,
            boolean_column BOOLEAN
        )
        """
    )

    connection.execute(
        """
        INSERT INTO affinity_demo (
            integer_column,
            numeric_column,
            decimal_column,
            varchar_column,
            text_column,
            boolean_column
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "42",
            "123.45",
            "19.99",
            123,
            456,
            True,
        ),
    )

    row = connection.execute(
        """
        SELECT
            integer_column,
            typeof(integer_column) AS integer_type,
            numeric_column,
            typeof(numeric_column) AS numeric_type,
            decimal_column,
            typeof(decimal_column) AS decimal_type,
            varchar_column,
            typeof(varchar_column) AS varchar_type,
            text_column,
            typeof(text_column) AS text_type,
            boolean_column,
            typeof(boolean_column) AS boolean_type
        FROM affinity_demo
        """
    ).fetchone()

    print(dict(row))

    print(
        "\nSQLite may coerce values according to column affinity. "
        "A declared type does not behave identically to strict typing in every "
        "database system."
    )


# =============================================================================
# 26. TYPE CHOICE DECISION FUNCTION
# =============================================================================

def recommend_data_type(
    meaning: str,
    requires_fraction: bool = False,
    requires_exact_decimal: bool = False,
    maximum_text_length: int | None = None,
    has_date: bool = False,
    has_time: bool = False,
    is_boolean: bool = False,
) -> str:
    """
    A conceptual type-selection helper.

    This function is not a replacement for database-specific schema design.
    It demonstrates the reasoning used when selecting types.
    """

    if is_boolean:
        return "BOOLEAN"

    if has_date and has_time:
        return "TIMESTAMP"

    if has_date:
        return "DATE"

    if has_time:
        return "TIME"

    if maximum_text_length is not None:
        return f"VARCHAR({maximum_text_length})"

    if meaning in {
        "description",
        "comment",
        "article",
        "notes",
        "long_text",
    }:
        return "TEXT"

    if requires_fraction and requires_exact_decimal:
        return "DECIMAL(precision, scale)"

    if requires_fraction:
        return "NUMERIC(precision, scale)"

    return "INTEGER"


def demonstrate_type_selection() -> None:
    print_section("CONCEPTUAL DATA TYPE SELECTION")

    scenarios = [
        (
            "Number of products",
            dict(meaning="count"),
        ),
        (
            "Product price",
            dict(
                meaning="price",
                requires_fraction=True,
                requires_exact_decimal=True,
            ),
        ),
        (
            "Username",
            dict(
                meaning="username",
                maximum_text_length=50,
            ),
        ),
        (
            "Product description",
            dict(meaning="description"),
        ),
        (
            "Account enabled",
            dict(
                meaning="status",
                is_boolean=True,
            ),
        ),
        (
            "Birth date",
            dict(
                meaning="birth",
                has_date=True,
            ),
        ),
        (
            "Store opening time",
            dict(
                meaning="schedule",
                has_time=True,
            ),
        ),
        (
            "Record creation moment",
            dict(
                meaning="audit",
                has_date=True,
                has_time=True,
            ),
        ),
    ]

    for description, arguments in scenarios:
        recommended = recommend_data_type(**arguments)
        print(f"{description:<30} -> {recommended}")


# =============================================================================
# 27. COMMON MISTAKES
# =============================================================================

def demonstrate_common_mistakes() -> None:
    print_section("COMMON DATA TYPE MISTAKES")

    mistakes = [
        (
            "Using FLOAT-like values for money",
            "Binary floating-point can introduce representation artifacts.",
        ),
        (
            "Using INTEGER for phone numbers",
            "Phone numbers are identifiers and may contain leading zeros or symbols.",
        ),
        (
            "Using VARCHAR for every column",
            "Text storage loses numeric and temporal semantics.",
        ),
        (
            "Using TIMESTAMP when only DATE matters",
            "Unnecessary time information can complicate interpretation.",
        ),
        (
            "Using = NULL",
            "SQL NULL comparisons require IS NULL or IS NOT NULL.",
        ),
        (
            "Assuming BOOLEAN behaves identically everywhere",
            "Database engines use different implementations and coercion rules.",
        ),
        (
            "Ignoring timezone semantics",
            "A local timestamp can be ambiguous for global event data.",
        ),
        (
            "Relying only on a data type for validation",
            "Business rules often require CHECK constraints or application validation.",
        ),
    ]

    for mistake, explanation in mistakes:
        print(f"\nMistake: {mistake}")
        print(f"Reason:  {explanation}")


# =============================================================================
# 28. PRACTICAL E-COMMERCE SCHEMA
# =============================================================================

def create_ecommerce_schema(connection: sqlite3.Connection) -> None:
    print_section("PRACTICAL SCHEMA DESIGN")

    connection.execute(
        """
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name VARCHAR(150) NOT NULL,
            description TEXT,
            price DECIMAL(12, 2) NOT NULL CHECK (price >= 0),
            quantity_in_stock INTEGER NOT NULL CHECK (quantity_in_stock >= 0),
            is_available BOOLEAN NOT NULL DEFAULT 1 CHECK (
                is_available IN (0, 1)
            ),
            launch_date DATE,
            created_at TIMESTAMP NOT NULL
        )
        """
    )

    connection.execute(
        """
        INSERT INTO products (
            product_id,
            product_name,
            description,
            price,
            quantity_in_stock,
            is_available,
            launch_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "Wireless Keyboard",
            "Compact keyboard with rechargeable battery.",
            "2499.00",
            50,
            1,
            "2026-09-01",
            "2026-09-08 10:15:00",
        ),
    )

    row = connection.execute(
        "SELECT * FROM products WHERE product_id = 1"
    ).fetchone()

    print(dict(row))


# =============================================================================
# 29. INDEXING AND DATA TYPE PERFORMANCE
# =============================================================================

"""
Indexes can improve lookup and sorting performance.

Data type choices influence index design.

General considerations:

- Smaller, fixed-size values can be efficient to compare.
- Very large TEXT values may require special indexing strategies.
- Applying functions to indexed columns can prevent efficient index usage.
- Implicit type conversion can sometimes prevent index use.
- The best index depends on query patterns, data distribution, and DBMS behavior.

Example:

    CREATE INDEX idx_events_timestamp
    ON events(event_timestamp);

The exact query optimizer behavior should be verified using the database's query
plan tools.
"""


def demonstrate_index_usage(connection: sqlite3.Connection) -> None:
    print_section("INDEXING AND TYPE-AWARE QUERIES")

    connection.execute(
        """
        CREATE INDEX idx_events_timestamp
        ON events(event_timestamp)
        """
    )

    query_plan = connection.execute(
        """
        EXPLAIN QUERY PLAN
        SELECT event_name
        FROM events
        WHERE event_timestamp >= ?
        """,
        ("2026-09-08 00:00:00",),
    ).fetchall()

    print("Query plan:")
    for row in query_plan:
        print(tuple(row))


# =============================================================================
# 30. DATA TYPE COMPARISON OPERATIONS
# =============================================================================

def demonstrate_comparisons(connection: sqlite3.Connection) -> None:
    print_section("COMPARISONS")

    integer_result = connection.execute(
        "SELECT 10 > 5 AS result"
    ).fetchone()

    text_result = connection.execute(
        "SELECT 'banana' > 'apple' AS result"
    ).fetchone()

    null_result = connection.execute(
        "SELECT NULL = NULL AS result"
    ).fetchone()

    print("10 > 5:", integer_result["result"])
    print("'banana' > 'apple':", text_result["result"])
    print("NULL = NULL:", null_result["result"])

    print(
        "\nThe NULL comparison result is represented as SQL NULL because "
        "the comparison is UNKNOWN rather than TRUE."
    )


# =============================================================================
# 31. CASTING
# =============================================================================

"""
CAST converts a value to another type.

Typical SQL syntax:

    CAST(expression AS INTEGER)
    CAST(expression AS TEXT)

Casting can be useful for controlled conversions, but unnecessary or repeated
casting can create performance and correctness problems.

A conversion that succeeds in one database may fail or behave differently in
another.
"""


def demonstrate_casting(connection: sqlite3.Connection) -> None:
    print_section("CASTING")

    row = connection.execute(
        """
        SELECT
            CAST('42' AS INTEGER) AS integer_value,
            CAST(42 AS TEXT) AS text_value,
            CAST('19.99' AS NUMERIC) AS numeric_value
        """
    ).fetchone()

    print(dict(row))


# =============================================================================
# 32. RANGE AND REPRESENTATION CONSIDERATIONS
# =============================================================================

def demonstrate_range_concepts() -> None:
    print_section("RANGE AND REPRESENTATION")

    print(
        "INTEGER range is database-specific. Some systems provide multiple "
        "integer sizes such as SMALLINT, INTEGER, and BIGINT."
    )

    print(
        "DECIMAL and NUMERIC capacity depends on configured precision and scale."
    )

    print(
        "VARCHAR capacity depends on its declared maximum length and database "
        "character rules."
    )

    print(
        "DATE, TIME, and TIMESTAMP supported ranges and precision can differ "
        "between database systems."
    )


# =============================================================================
# 33. SCHEMA DESIGN PRINCIPLES
# =============================================================================

def schema_design_principles() -> None:
    print_section("SCHEMA DESIGN PRINCIPLES")

    principles = [
        "Choose types based on the meaning of data.",
        "Use exact decimal types for values requiring decimal exactness.",
        "Use INTEGER for quantities and whole-number concepts.",
        "Use VARCHAR when a meaningful maximum length exists.",
        "Use TEXT for longer textual content.",
        "Use BOOLEAN for logical state where supported.",
        "Use DATE when time of day is irrelevant.",
        "Use TIME when only time of day matters.",
        "Use TIMESTAMP for date-time events.",
        "Define NULL behavior explicitly using NOT NULL where required.",
        "Use CHECK constraints for domain rules.",
        "Use parameterized queries for external input.",
        "Design timezone handling explicitly for real-world events.",
        "Verify type behavior in the target database system.",
    ]

    for number, principle in enumerate(principles, start=1):
        print(f"{number:>2}. {principle}")


# =============================================================================
# 34. ADVANCED CASE: NULLABLE BOOLEAN AND THREE STATES
# =============================================================================

def demonstrate_nullable_boolean(connection: sqlite3.Connection) -> None:
    print_section("NULLABLE BOOLEAN AND THREE STATES")

    connection.execute(
        """
        CREATE TABLE verification (
            user_id INTEGER PRIMARY KEY,
            is_verified BOOLEAN CHECK (
                is_verified IN (0, 1) OR is_verified IS NULL
            )
        )
        """
    )

    connection.executemany(
        """
        INSERT INTO verification (user_id, is_verified)
        VALUES (?, ?)
        """,
        [
            (1, 1),      # Verified
            (2, 0),      # Explicitly not verified
            (3, None),   # Unknown or not yet determined
        ],
    )

    rows = connection.execute(
        """
        SELECT user_id, is_verified
        FROM verification
        ORDER BY user_id
        """
    ).fetchall()

    for row in rows:
        print(dict(row))

    print(
        "\nA nullable BOOLEAN can represent three business states, but this "
        "should be intentional because NULL is semantically different from FALSE."
    )


# =============================================================================
# 35. ADVANCED CASE: TEMPORAL DATA AND TIMEZONES
# =============================================================================

def demonstrate_timestamp_design() -> None:
    print_section("TIMESTAMP DESIGN")

    local_naive = dt.datetime(2026, 9, 8, 9, 0, 0)

    utc_aware = dt.datetime(
        2026,
        9,
        8,
        3,
        30,
        0,
        tzinfo=dt.timezone.utc,
    )

    print("Naive local timestamp:", local_naive)
    print("UTC-aware timestamp:", utc_aware)

    print(
        "\nA naive timestamp may be appropriate for concepts tied to local "
        "clock time, such as a recurring office opening schedule."
    )

    print(
        "An actual event that happened at a specific instant is often better "
        "represented using a timezone-aware convention or normalized UTC storage."
    )


# =============================================================================
# 36. TESTING DATA TYPE ASSUMPTIONS
# =============================================================================

def run_basic_tests() -> None:
    print_section("BASIC TESTS")

    assert validate_varchar("abc", 3)
    assert not validate_varchar("abcd", 3)

    assert normalize_boolean("yes") is True
    assert normalize_boolean("NO") is False

    assert parse_iso_date("2024-02-29") == dt.date(2024, 2, 29)

    try:
        parse_iso_date("2026-02-29")
        raise AssertionError("Invalid date unexpectedly parsed.")
    except ValueError:
        pass

    assert parse_iso_time("23:59:59") == dt.time(23, 59, 59)

    try:
        parse_iso_time("24:00:00")
        raise AssertionError("Invalid time unexpectedly parsed.")
    except ValueError:
        pass

    print("All basic tests passed.")


# =============================================================================
# 37. COMPLETE STUDY DEMONSTRATION
# =============================================================================

def main() -> None:
    display_column_examples()
    demonstrate_null_logic()

    integer_examples()

    decimal_examples()
    demonstrate_precision_scale()
    compare_numeric_types()

    varchar_examples()
    text_examples()
    compare_varchar_and_text()

    boolean_examples()
    demonstrate_boolean_normalization()

    date_examples()
    demonstrate_invalid_dates()

    time_examples()
    demonstrate_invalid_times()

    timestamp_examples()
    demonstrate_timezone_conversion()
    compare_temporal_types()

    connection = create_connection()

    try:
        create_demo_table(connection)
        insert_demo_data(connection)
        display_sqlite_rows(connection)
        inspect_sqlite_types(connection)

        demonstrate_integer_constraints(connection)
        calculate_invoice_total()
        demonstrate_text_validation()
        demonstrate_boolean_constraints(connection)
        demonstrate_date_storage(connection)
        demonstrate_temporal_ordering(connection)
        demonstrate_parameterized_queries(connection)
        demonstrate_sqlite_affinity(connection)
        demonstrate_type_selection()
        demonstrate_common_mistakes()
        create_ecommerce_schema(connection)
        demonstrate_index_usage(connection)
        demonstrate_comparisons(connection)
        demonstrate_casting(connection)
        demonstrate_range_concepts()
        schema_design_principles()
        demonstrate_nullable_boolean(connection)
        demonstrate_timestamp_design()
        run_basic_tests()

    finally:
        connection.close()

    print_section("END OF SQL DATA TYPE STUDY SCRIPT")


if __name__ == "__main__":
    main()
