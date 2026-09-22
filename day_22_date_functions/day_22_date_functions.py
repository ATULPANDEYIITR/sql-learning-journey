"""
PostgreSQL Date Functions: EXTRACT, DATE_PART, DATE_TRUNC, AGE, CURRENT_DATE

This standalone study script teaches PostgreSQL date and time functions from
beginner to advanced level.

The script does not require a PostgreSQL server to run. It contains:
    1. A conceptual Python model of important PostgreSQL date operations.
    2. Exact PostgreSQL SQL examples as executable query strings.
    3. A realistic employee analytics example.
    4. Edge-case demonstrations.
    5. Validation and error-handling examples.
    6. Query-generation helpers.
    7. A small test suite.
    8. A performance-oriented discussion represented through executable code.

For actual PostgreSQL execution, the generated SQL can be run against a
PostgreSQL database using psql or a PostgreSQL Python driver such as psycopg.

Important distinction:
Python's datetime module is used here to make the concepts executable without
requiring an external database. The SQL strings demonstrate PostgreSQL's actual
syntax and semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import calendar
import re
import sys
import time
from typing import Any, Callable, Iterable, Optional


# ============================================================================
# 1. FUNDAMENTAL TERMINOLOGY
# ============================================================================

print("=" * 80)
print("POSTGRESQL DATE FUNCTIONS STUDY PROGRAM")
print("=" * 80)

print(
    """
The five central PostgreSQL concepts covered by this program are:

EXTRACT
    Retrieves a specific component from a date/time value.
    Example:
        EXTRACT(YEAR FROM order_date)

DATE_PART
    An alternative function-style syntax for extracting a component.
    Example:
        DATE_PART('year', order_date)

DATE_TRUNC
    Removes smaller units from a date/time value and returns the beginning
    of a selected time period.
    Example:
        DATE_TRUNC('month', order_date)

AGE
    Calculates an interval representing the calendar difference between
    dates or timestamps.
    Example:
        AGE(CURRENT_DATE, birth_date)

CURRENT_DATE
    Returns the current date according to PostgreSQL's current transaction
    time context.
    Example:
        CURRENT_DATE
"""
)


# ============================================================================
# 2. REFERENCE DATE VALUES
# ============================================================================

REFERENCE_DATE = date(2026, 9, 22)
REFERENCE_TIMESTAMP = datetime(2026, 9, 22, 14, 35, 48)

print("\nREFERENCE VALUES")
print("-" * 80)
print("Reference date:", REFERENCE_DATE)
print("Reference timestamp:", REFERENCE_TIMESTAMP)


# ============================================================================
# 3. PYTHON EQUIVALENTS OF EXTRACT
# ============================================================================

def python_extract(value: date | datetime, field: str) -> float | int:
    """
    Approximate the most commonly used PostgreSQL EXTRACT fields.

    PostgreSQL supports many more fields than this compact teaching model,
    including timezone-related fields for timestamp with time zone values.
    """
    field = field.lower().strip()

    if field == "year":
        return value.year

    if field == "month":
        return value.month

    if field == "day":
        return value.day

    if field == "hour":
        return value.hour if isinstance(value, datetime) else 0

    if field == "minute":
        return value.minute if isinstance(value, datetime) else 0

    if field == "second":
        if isinstance(value, datetime):
            return value.second + value.microsecond / 1_000_000
        return 0

    if field == "quarter":
        return ((value.month - 1) // 3) + 1

    if field == "week":
        return value.isocalendar().week

    if field == "isoyear":
        return value.isocalendar().year

    if field == "isodow":
        return value.isoweekday()

    if field == "dow":
        # PostgreSQL DOW uses Sunday=0, Monday=1, ..., Saturday=6.
        return (value.weekday() + 1) % 7

    if field == "doy":
        return value.timetuple().tm_yday

    if field == "epoch":
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.timestamp()
            return value.timestamp()
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        current = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
        return (current - epoch).total_seconds()

    raise ValueError(f"Unsupported teaching field: {field}")


print("\nEXTRACT CONCEPT")
print("-" * 80)

for field in [
    "year",
    "month",
    "day",
    "quarter",
    "week",
    "isoyear",
    "isodow",
    "dow",
    "doy",
]:
    print(f"{field:10} -> {python_extract(REFERENCE_DATE, field)}")


# ============================================================================
# 4. EXACT POSTGRESQL EXTRACT SYNTAX
# ============================================================================

print("\nPOSTGRESQL EXTRACT SYNTAX")
print("-" * 80)

extract_examples = [
    "SELECT EXTRACT(YEAR FROM DATE '2026-09-22');",
    "SELECT EXTRACT(MONTH FROM DATE '2026-09-22');",
    "SELECT EXTRACT(DAY FROM DATE '2026-09-22');",
    "SELECT EXTRACT(QUARTER FROM DATE '2026-09-22');",
    "SELECT EXTRACT(WEEK FROM DATE '2026-09-22');",
    "SELECT EXTRACT(ISOYEAR FROM DATE '2026-09-22');",
    "SELECT EXTRACT(ISODOW FROM DATE '2026-09-22');",
    "SELECT EXTRACT(DOW FROM DATE '2026-09-22');",
    "SELECT EXTRACT(DOY FROM DATE '2026-09-22');",
    "SELECT EXTRACT(HOUR FROM TIMESTAMP '2026-09-22 14:35:48');",
    "SELECT EXTRACT(MINUTE FROM TIMESTAMP '2026-09-22 14:35:48');",
    "SELECT EXTRACT(SECOND FROM TIMESTAMP '2026-09-22 14:35:48');",
]

for query in extract_examples:
    print(query)


# ============================================================================
# 5. DATE_PART
# ============================================================================

print("\nDATE_PART")
print("-" * 80)

date_part_examples = [
    "SELECT DATE_PART('year', DATE '2026-09-22');",
    "SELECT DATE_PART('month', DATE '2026-09-22');",
    "SELECT DATE_PART('day', DATE '2026-09-22');",
    "SELECT DATE_PART('quarter', DATE '2026-09-22');",
    "SELECT DATE_PART('week', DATE '2026-09-22');",
    "SELECT DATE_PART('isoyear', DATE '2026-09-22');",
    "SELECT DATE_PART('dow', DATE '2026-09-22');",
    "SELECT DATE_PART('doy', DATE '2026-09-22');",
    "SELECT DATE_PART('hour', TIMESTAMP '2026-09-22 14:35:48');",
]

for query in date_part_examples:
    print(query)


def demonstrate_extract_and_date_part(value: date | datetime) -> None:
    """
    Demonstrates that EXTRACT and DATE_PART can represent the same
    conceptual operation using different PostgreSQL syntax.
    """
    print("\nEXTRACT VS DATE_PART")

    fields = ["year", "month", "day", "quarter", "week"]

    for field in fields:
        extract_result = python_extract(value, field)
        date_part_result = python_extract(value, field)

        print(
            f"{field:10} "
            f"EXTRACT={extract_result!r:<8} "
            f"DATE_PART={date_part_result!r:<8}"
        )


demonstrate_extract_and_date_part(REFERENCE_DATE)


# ============================================================================
# 6. IMPORTANT TYPE DIFFERENCE
# ============================================================================

print("\nTYPE CONSIDERATION")
print("-" * 80)

print(
    """
In PostgreSQL, EXTRACT returns a numeric value.

DATE_PART also returns a double precision value.

This matters when an application expects an integer. A query such as:

    SELECT EXTRACT(YEAR FROM birth_date);

may produce a numeric representation rather than a language-level integer.

If integer output is explicitly required, PostgreSQL can cast it:

    SELECT EXTRACT(YEAR FROM birth_date)::int;

For ordinary reporting queries, the distinction is often invisible, but it
matters in strict type-sensitive application code.
"""
)


# ============================================================================
# 7. DATE_TRUNC CONCEPT
# ============================================================================

def start_of_month(value: date | datetime) -> date | datetime:
    """Return the beginning of the month."""
    if isinstance(value, datetime):
        return value.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    return value.replace(day=1)


def start_of_quarter(value: date | datetime) -> date | datetime:
    """Return the beginning of the calendar quarter."""
    first_month = ((value.month - 1) // 3) * 3 + 1

    if isinstance(value, datetime):
        return value.replace(
            month=first_month,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    return value.replace(month=first_month, day=1)


def start_of_year(value: date | datetime) -> date | datetime:
    """Return the beginning of the calendar year."""
    if isinstance(value, datetime):
        return value.replace(
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    return value.replace(month=1, day=1)


def start_of_week(value: date | datetime) -> date | datetime:
    """
    PostgreSQL DATE_TRUNC('week', ...) uses Monday as the beginning
    of the ISO week.
    """
    monday = value - timedelta(days=value.weekday())

    if isinstance(value, datetime):
        return monday.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    return monday


def truncate_datetime(value: datetime, precision: str) -> datetime:
    """
    Approximate common DATE_TRUNC precisions.

    This intentionally focuses on widely used business-reporting units.
    """
    precision = precision.lower().strip()

    if precision == "year":
        return value.replace(
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    if precision == "quarter":
        first_month = ((value.month - 1) // 3) * 3 + 1
        return value.replace(
            month=first_month,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    if precision == "month":
        return value.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    if precision == "week":
        monday = value - timedelta(days=value.weekday())
        return monday.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    if precision == "day":
        return value.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    if precision == "hour":
        return value.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

    if precision == "minute":
        return value.replace(
            second=0,
            microsecond=0,
        )

    if precision == "second":
        return value.replace(microsecond=0)

    raise ValueError(f"Unsupported DATE_TRUNC precision: {precision}")


print("\nDATE_TRUNC")
print("-" * 80)

for precision in [
    "year",
    "quarter",
    "month",
    "week",
    "day",
    "hour",
    "minute",
    "second",
]:
    print(
        f"{precision:10} -> "
        f"{truncate_datetime(REFERENCE_TIMESTAMP, precision)}"
    )


# ============================================================================
# 8. DATE_TRUNC SQL EXAMPLES
# ============================================================================

date_trunc_examples = [
    "SELECT DATE_TRUNC('year', TIMESTAMP '2026-09-22 14:35:48');",
    "SELECT DATE_TRUNC('quarter', TIMESTAMP '2026-09-22 14:35:48');",
    "SELECT DATE_TRUNC('month', TIMESTAMP '2026-09-22 14:35:48');",
    "SELECT DATE_TRUNC('week', TIMESTAMP '2026-09-22 14:35:48');",
    "SELECT DATE_TRUNC('day', TIMESTAMP '2026-09-22 14:35:48');",
    "SELECT DATE_TRUNC('hour', TIMESTAMP '2026-09-22 14:35:48');",
    "SELECT DATE_TRUNC('minute', TIMESTAMP '2026-09-22 14:35:48');",
    "SELECT DATE_TRUNC('second', TIMESTAMP '2026-09-22 14:35:48');",
]

print("\nPOSTGRESQL DATE_TRUNC QUERIES")
print("-" * 80)

for query in date_trunc_examples:
    print(query)


# ============================================================================
# 9. EXTRACT VS DATE_TRUNC
# ============================================================================

print("\nEXTRACT VS DATE_TRUNC")
print("-" * 80)

print(
    """
EXTRACT answers:
    "What is the value of this particular date/time component?"

Example:
    EXTRACT(MONTH FROM order_date)

Result concept:
    9

DATE_TRUNC answers:
    "What is the beginning of the selected time period containing this value?"

Example:
    DATE_TRUNC('month', order_date)

Result concept:
    2026-09-01 00:00:00

The two functions are therefore complementary rather than interchangeable.
"""
)


# ============================================================================
# 10. CURRENT_DATE
# ============================================================================

print("\nCURRENT_DATE")
print("-" * 80)

current_date_sql = [
    "SELECT CURRENT_DATE;",
    "SELECT CURRENT_DATE - DATE '2020-01-01';",
    "SELECT EXTRACT(YEAR FROM CURRENT_DATE);",
    "SELECT DATE_TRUNC('month', CURRENT_DATE);",
    "SELECT AGE(CURRENT_DATE, DATE '2000-01-01');",
]

for query in current_date_sql:
    print(query)

print("\nPython runtime date for comparison:", date.today())

print(
    """
PostgreSQL CURRENT_DATE is not the same concept as repeatedly calling a
wall-clock function from an application.

PostgreSQL's current-date/time functions are tied to the current transaction
time context. This gives consistent results within a transaction.

For database logic that needs the database's own notion of today's date,
CURRENT_DATE is usually preferable to sending an application-generated date.
"""
)


# ============================================================================
# 11. CALENDAR AGE CALCULATION
# ============================================================================

@dataclass(frozen=True)
class CalendarInterval:
    """
    Represents the calendar-style result commonly associated with PostgreSQL
    AGE: years, months, and remaining days.

    This is different from simply dividing a number of days by 365.
    """

    years: int
    months: int
    days: int

    def __str__(self) -> str:
        return (
            f"{self.years} years, "
            f"{self.months} months, "
            f"{self.days} days"
        )


def calendar_age(later: date, earlier: date) -> CalendarInterval:
    """
    Approximate PostgreSQL's calendar-oriented AGE behavior.

    The implementation performs calendar subtraction rather than converting
    the entire period to a fixed number of days.

    It is intended as a teaching model, not as a replacement for PostgreSQL.
    """
    if later < earlier:
        raise ValueError("later date must not precede earlier date")

    years = later.year - earlier.year
    months = later.month - earlier.month
    days = later.day - earlier.day

    if days < 0:
        months -= 1

        previous_month = later.month - 1
        previous_year = later.year

        if previous_month == 0:
            previous_month = 12
            previous_year -= 1

        days_in_previous_month = calendar.monthrange(
            previous_year,
            previous_month,
        )[1]

        days += days_in_previous_month

    if months < 0:
        years -= 1
        months += 12

    return CalendarInterval(years, months, days)


birth_date = date(1995, 4, 18)

print("\nAGE CONCEPT")
print("-" * 80)

print("Birth date:", birth_date)
print("Reference date:", REFERENCE_DATE)
print("Calendar age:", calendar_age(REFERENCE_DATE, birth_date))

age_queries = [
    "SELECT AGE(CURRENT_DATE, DATE '1995-04-18');",
    "SELECT AGE(DATE '2026-09-22', DATE '1995-04-18');",
    "SELECT AGE(CURRENT_DATE, birth_date) FROM employees;",
]

for query in age_queries:
    print(query)


# ============================================================================
# 12. AGE VS SIMPLE DAY SUBTRACTION
# ============================================================================

print("\nAGE VS DATE SUBTRACTION")
print("-" * 80)

earlier = date(2020, 2, 29)
later = date(2026, 2, 28)

day_difference = (later - earlier).days
calendar_difference = calendar_age(later, earlier)

print("Earlier:", earlier)
print("Later:", later)
print("Elapsed days:", day_difference)
print("Calendar age:", calendar_difference)

print(
    """
A raw date subtraction answers an elapsed-time question in days.

AGE answers a calendar-relative question in years, months, and days.

This distinction is important for:
    - employee tenure
    - customer age
    - subscription duration
    - legal or contractual periods
    - anniversaries
    - human-readable reporting
"""
)


# ============================================================================
# 13. AGE WITH ONE ARGUMENT
# ============================================================================

print("\nAGE WITH ONE ARGUMENT")
print("-" * 80)

print(
    "PostgreSQL supports the one-argument form:",
    "AGE(timestamp)",
)

print("Example:")
print("SELECT AGE(TIMESTAMP '1995-04-18 10:30:00');")

print(
    """
The one-argument form compares the supplied timestamp with the current
transaction timestamp.

For deterministic analytics and tests, the two-argument form is often easier
to reason about:

    AGE(reference_timestamp, birth_timestamp)

because both values are explicit.
"""
)


# ============================================================================
# 14. NEGATIVE AGE
# ============================================================================

print("\nNEGATIVE AGE EDGE CASE")
print("-" * 80)

future_date = date(2030, 1, 1)

try:
    result = calendar_age(REFERENCE_DATE, future_date)
    print(result)
except ValueError as exc:
    print("Validation caught:", exc)

print(
    """
PostgreSQL can represent negative intervals. The Python teaching helper above
instead rejects reversed arguments to make the business-rule distinction
explicit.

When writing production SQL, decide whether future dates should be:
    - accepted as negative intervals,
    - rejected as invalid data,
    - or interpreted as a future-duration calculation.
"""
)


# ============================================================================
# 15. ISO WEEK AND YEAR EDGE CASE
# ============================================================================

print("\nISO WEEK EDGE CASE")
print("-" * 80)

iso_boundary_dates = [
    date(2020, 12, 28),
    date(2020, 12, 31),
    date(2021, 1, 1),
    date(2021, 1, 4),
]

for value in iso_boundary_dates:
    print(
        value,
        "calendar year=",
        value.year,
        "ISO year=",
        value.isocalendar().year,
        "ISO week=",
        value.isocalendar().week,
    )

print(
    """
Calendar year and ISO week-year are not always the same.

For reporting based on ISO weeks, use:

    EXTRACT(ISOYEAR FROM event_date)
    EXTRACT(WEEK FROM event_date)

rather than assuming EXTRACT(YEAR ...) and EXTRACT(WEEK ...) form a single
calendar-year/week key.
"""
)


# ============================================================================
# 16. WEEK START BEHAVIOR
# ============================================================================

print("\nDATE_TRUNC WEEK")
print("-" * 80)

week_test_date = datetime(2026, 9, 22, 14, 35, 48)
week_start = truncate_datetime(week_test_date, "week")

print("Input:", week_test_date)
print("Week start:", week_start)

print(
    """
For PostgreSQL timestamp values, DATE_TRUNC('week', value) truncates to the
beginning of the ISO week, which starts on Monday.

This is useful for:
    - weekly sales reports
    - operational dashboards
    - weekly active-user analysis
    - support-ticket reporting
"""
)


# ============================================================================
# 17. BUSINESS REPORTING EXAMPLES
# ============================================================================

print("\nBUSINESS REPORTING QUERIES")
print("-" * 80)

business_queries = {
    "monthly_sales":
        """
SELECT
    DATE_TRUNC('month', order_date) AS month_start,
    SUM(amount) AS monthly_sales
FROM orders
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month_start;
""".strip(),

    "quarterly_sales":
        """
SELECT
    DATE_TRUNC('quarter', order_date) AS quarter_start,
    SUM(amount) AS quarterly_sales
FROM orders
GROUP BY DATE_TRUNC('quarter', order_date)
ORDER BY quarter_start;
""".strip(),

    "employee_age":
        """
SELECT
    employee_id,
    employee_name,
    AGE(CURRENT_DATE, birth_date) AS age_interval
FROM employees
ORDER BY employee_id;
""".strip(),

    "employee_birth_year":
        """
SELECT
    employee_id,
    EXTRACT(YEAR FROM birth_date)::int AS birth_year
FROM employees;
""".strip(),

    "daily_activity":
        """
SELECT
    DATE_TRUNC('day', event_timestamp) AS event_day,
    COUNT(*) AS event_count
FROM application_events
GROUP BY DATE_TRUNC('day', event_timestamp)
ORDER BY event_day;
""".strip(),

    "hourly_activity":
        """
SELECT
    DATE_TRUNC('hour', event_timestamp) AS event_hour,
    COUNT(*) AS event_count
FROM application_events
GROUP BY DATE_TRUNC('hour', event_timestamp)
ORDER BY event_hour;
""".strip(),
}

for name, query in business_queries.items():
    print(f"\n-- {name}")
    print(query)


# ============================================================================
# 18. GROUPING BY EXTRACT
# ============================================================================

print("\nGROUPING WITH EXTRACT")
print("-" * 80)

print(
    """
A component can be extracted for categorization.

Example:

SELECT
    EXTRACT(YEAR FROM order_date)::int AS order_year,
    EXTRACT(MONTH FROM order_date)::int AS order_month,
    SUM(amount) AS total_amount
FROM orders
GROUP BY
    EXTRACT(YEAR FROM order_date),
    EXTRACT(MONTH FROM order_date)
ORDER BY
    order_year,
    order_month;

This produces numeric year/month categories.

DATE_TRUNC is often more convenient when the reporting system needs an actual
period boundary:

SELECT
    DATE_TRUNC('month', order_date) AS month_start,
    SUM(amount)
FROM orders
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month_start;
"""
)


# ============================================================================
# 19. RANGE FILTERING AND DATE_TRUNC
# ============================================================================

print("\nDATE FILTERING")
print("-" * 80)

print(
    """
A common mistake is to use a function around an indexed timestamp column in
a WHERE clause without considering index usage.

For example:

    WHERE DATE_TRUNC('day', event_timestamp) = DATE '2026-09-22'

may require PostgreSQL to evaluate DATE_TRUNC for many rows.

A half-open range is often easier for an index to use:

    WHERE event_timestamp >= TIMESTAMP '2026-09-22 00:00:00'
      AND event_timestamp <  TIMESTAMP '2026-09-23 00:00:00'

For parameterized application code, bind the boundary values rather than
constructing them by unsafe string concatenation.
"""
)


# ============================================================================
# 20. SAFE SQL QUERY BUILDING
# ============================================================================

def build_monthly_report_query(table_name: str, date_column: str) -> str:
    """
    Build a query only after validating identifiers.

    Values should normally be supplied as parameters rather than interpolated.
    Identifiers such as table and column names are different because most SQL
    drivers do not treat them as ordinary bound values.
    """
    identifier_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    if not identifier_pattern.fullmatch(table_name):
        raise ValueError("Invalid table identifier")

    if not identifier_pattern.fullmatch(date_column):
        raise ValueError("Invalid date-column identifier")

    return f"""
SELECT
    DATE_TRUNC('month', {date_column}) AS month_start,
    COUNT(*) AS row_count
FROM {table_name}
GROUP BY DATE_TRUNC('month', {date_column})
ORDER BY month_start;
""".strip()


print("\nSAFE IDENTIFIER VALIDATION")
print("-" * 80)

print(build_monthly_report_query("orders", "created_at"))

try:
    print(build_monthly_report_query("orders; DROP TABLE users;", "created_at"))
except ValueError as exc:
    print("Rejected unsafe identifier:", exc)


# ============================================================================
# 21. REALISTIC EMPLOYEE DATASET
# ============================================================================

@dataclass
class Employee:
    employee_id: int
    name: str
    birth_date: date
    joined_date: date
    department: str


employees = [
    Employee(
        101,
        "Asha",
        date(1990, 5, 17),
        date(2017, 6, 12),
        "Engineering",
    ),
    Employee(
        102,
        "Ravi",
        date(1987, 11, 3),
        date(2015, 2, 9),
        "Finance",
    ),
    Employee(
        103,
        "Meera",
        date(1998, 1, 28),
        date(2022, 8, 22),
        "Engineering",
    ),
    Employee(
        104,
        "Kabir",
        date(1995, 12, 31),
        date(2020, 1, 6),
        "Operations",
    ),
]


def employee_report(
    employee_list: Iterable[Employee],
    reference_date: date,
) -> list[dict[str, Any]]:
    """
    Produce a Python equivalent of an SQL analytical report.
    """
    report = []

    for employee in employee_list:
        if employee.birth_date > reference_date:
            raise ValueError(
                f"{employee.name} has a birth date after the reference date"
            )

        if employee.joined_date > reference_date:
            raise ValueError(
                f"{employee.name} has a future joining date"
            )

        age = calendar_age(reference_date, employee.birth_date)
        tenure = calendar_age(reference_date, employee.joined_date)

        report.append(
            {
                "employee_id": employee.employee_id,
                "name": employee.name,
                "department": employee.department,
                "birth_year": python_extract(
                    employee.birth_date,
                    "year",
                ),
                "birth_month": python_extract(
                    employee.birth_date,
                    "month",
                ),
                "age_years": age.years,
                "age_months": age.months,
                "age_days": age.days,
                "tenure_years": tenure.years,
                "tenure_months": tenure.months,
                "tenure_days": tenure.days,
                "join_month": start_of_month(employee.joined_date),
            }
        )

    return report


print("\nEMPLOYEE ANALYTICS CASE STUDY")
print("-" * 80)

for row in employee_report(employees, REFERENCE_DATE):
    print(row)


# ============================================================================
# 22. CORRESPONDING POSTGRESQL EMPLOYEE QUERY
# ============================================================================

print("\nCORRESPONDING POSTGRESQL EMPLOYEE QUERY")
print("-" * 80)

employee_sql = """
SELECT
    employee_id,
    employee_name,
    department,
    EXTRACT(YEAR FROM birth_date)::int AS birth_year,
    EXTRACT(MONTH FROM birth_date)::int AS birth_month,
    AGE(CURRENT_DATE, birth_date) AS age,
    AGE(CURRENT_DATE, joined_date) AS tenure,
    DATE_TRUNC('month', joined_date) AS joining_month
FROM employees
WHERE birth_date <= CURRENT_DATE
  AND joined_date <= CURRENT_DATE
ORDER BY employee_id;
""".strip()

print(employee_sql)


# ============================================================================
# 23. MONTH-END AND MONTH-START CONCEPT
# ============================================================================

def days_in_month(value: date) -> int:
    return calendar.monthrange(value.year, value.month)[1]


def end_of_month(value: date) -> date:
    return value.replace(day=days_in_month(value))


print("\nMONTH BOUNDARIES")
print("-" * 80)

for sample in [
    date(2024, 2, 10),
    date(2025, 2, 10),
    date(2026, 9, 22),
]:
    print(
        sample,
        "-> start:",
        start_of_month(sample),
        "end:",
        end_of_month(sample),
    )

print(
    """
DATE_TRUNC naturally produces the beginning of a period.

For example:

    DATE_TRUNC('month', timestamp_value)

returns the first moment of that month.

To derive the next month boundary safely:

    DATE_TRUNC('month', timestamp_value) + INTERVAL '1 month'

A half-open interval can then be expressed as:

    timestamp_value >= month_start
    AND timestamp_value < next_month_start

This avoids having to calculate a final timestamp such as 23:59:59.999999.
"""
)


# ============================================================================
# 24. CURRENT_DATE AND CURRENT_TIMESTAMP DISTINCTION
# ============================================================================

print("\nCURRENT DATE/TIME FUNCTIONS")
print("-" * 80)

current_function_examples = [
    "SELECT CURRENT_DATE;",
    "SELECT CURRENT_TIME;",
    "SELECT CURRENT_TIMESTAMP;",
    "SELECT LOCALTIME;",
    "SELECT LOCALTIMESTAMP;",
    "SELECT NOW();",
]

for query in current_function_examples:
    print(query)

print(
    """
CURRENT_DATE returns a date.

CURRENT_TIMESTAMP returns a timestamp with time zone.

LOCALTIMESTAMP returns a timestamp without time zone.

NOW() is commonly used as a synonym for the current transaction timestamp.

Choosing the correct type is important because a date-only business rule
should not be implemented as though it required a full timestamp.
"""
)


# ============================================================================
# 25. TIMESTAMP AND TIME ZONE CONSIDERATION
# ============================================================================

print("\nTIME ZONE CONSIDERATIONS")
print("-" * 80)

timezone_queries = [
    """
SELECT DATE_TRUNC(
    'day',
    event_timestamp AT TIME ZONE 'Asia/Kolkata'
)
FROM events;
""".strip(),

    """
SELECT EXTRACT(
    HOUR FROM event_timestamp AT TIME ZONE 'Asia/Kolkata'
)
FROM events;
""".strip(),

    """
SELECT DATE_TRUNC(
    'month',
    event_timestamp
)
FROM events;
""".strip(),
]

for query in timezone_queries:
    print(query)
    print()

print(
    """
Time zones matter when a business period is defined by a local clock.

For example, a global event timestamp may need to be converted to the
business's local time zone before extracting the local hour or truncating
to a local calendar day.

A technically correct query can still produce an incorrect business result
if the intended time zone is not understood.
"""
)


# ============================================================================
# 26. NULL BEHAVIOR
# ============================================================================

print("\nNULL BEHAVIOR")
print("-" * 80)

print(
    """
Date functions normally propagate NULL.

Examples:

    SELECT EXTRACT(YEAR FROM NULL::date);
    SELECT DATE_PART('year', NULL::date);
    SELECT DATE_TRUNC('month', NULL::timestamp);
    SELECT AGE(CURRENT_DATE, NULL::date);

These expressions produce NULL rather than inventing a date.

This is important because NULL means "unknown or absent", not "zero",
"today", or "1970-01-01".
"""
)


# ============================================================================
# 27. INVALID DATE INPUT
# ============================================================================

print("\nINVALID DATE VALIDATION")
print("-" * 80)

invalid_dates = [
    "2026-02-29",
    "2026-13-01",
    "not-a-date",
]


def parse_iso_date(value: str) -> Optional[date]:
    """Safely parse an ISO date string."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


for raw_value in invalid_dates:
    parsed = parse_iso_date(raw_value)
    print(raw_value, "->", parsed)


# ============================================================================
# 28. LEAP YEAR TESTING
# ============================================================================

print("\nLEAP YEAR")
print("-" * 80)

for year in [2024, 2025, 2026, 2100, 2000]:
    print(
        year,
        "leap year =",
        calendar.isleap(year),
        "days in February =",
        calendar.monthrange(year, 2)[1],
    )

print(
    """
Calendar arithmetic must not assume every year has 365 days.

The Gregorian leap-year rules include:
    - divisible by 4 -> normally leap year
    - divisible by 100 -> normally not a leap year
    - divisible by 400 -> leap year

Thus 2000 is a leap year, while 2100 is not.
"""
)


# ============================================================================
# 29. DATE_TRUNC REPORTING BUCKETS
# ============================================================================

def generate_time_buckets(
    timestamps: Iterable[datetime],
    precision: str,
) -> dict[datetime, int]:
    """Count timestamps by a DATE_TRUNC-like bucket."""
    buckets: dict[datetime, int] = {}

    for timestamp in timestamps:
        bucket = truncate_datetime(timestamp, precision)
        buckets[bucket] = buckets.get(bucket, 0) + 1

    return dict(sorted(buckets.items()))


sample_events = [
    datetime(2026, 9, 1, 8, 30),
    datetime(2026, 9, 1, 9, 15),
    datetime(2026, 9, 2, 10, 0),
    datetime(2026, 9, 15, 12, 45),
    datetime(2026, 10, 1, 7, 10),
]

print("\nTIME BUCKETING")
print("-" * 80)

for precision in ["day", "month"]:
    print(f"\nPrecision: {precision}")

    for bucket, count in generate_time_buckets(
        sample_events,
        precision,
    ).items():
        print(bucket, "->", count)


# ============================================================================
# 30. DATE_PART FOR ANALYTICS
# ============================================================================

print("\nDATE_PART ANALYTICS EXAMPLES")
print("-" * 80)

analytics_queries = [
    """
SELECT
    DATE_PART('dow', created_at) AS day_of_week,
    COUNT(*) AS events
FROM events
GROUP BY DATE_PART('dow', created_at)
ORDER BY day_of_week;
""".strip(),

    """
SELECT
    DATE_PART('hour', created_at) AS event_hour,
    COUNT(*) AS events
FROM events
GROUP BY DATE_PART('hour', created_at)
ORDER BY event_hour;
""".strip(),

    """
SELECT
    DATE_PART('quarter', created_at) AS quarter,
    SUM(amount) AS revenue
FROM sales
GROUP BY DATE_PART('quarter', created_at)
ORDER BY quarter;
""".strip(),
]

for query in analytics_queries:
    print(query)
    print()


# ============================================================================
# 31. FUNCTION SELECTION GUIDE
# ============================================================================

print("\nFUNCTION SELECTION GUIDE")
print("-" * 80)

selection_guide = {
    "Need one component": "EXTRACT or DATE_PART",
    "Need period beginning": "DATE_TRUNC",
    "Need calendar difference": "AGE",
    "Need database current date": "CURRENT_DATE",
    "Need elapsed days": "date subtraction",
    "Need period grouping": "DATE_TRUNC + GROUP BY",
    "Need year/month number": "EXTRACT",
}

for requirement, function in selection_guide.items():
    print(f"{requirement:30} -> {function}")


# ============================================================================
# 32. COMMON MISTAKES
# ============================================================================

print("\nCOMMON MISTAKES")
print("-" * 80)

mistakes = [
    (
        "Using EXTRACT when a period boundary is required",
        "Use DATE_TRUNC for month/week/day buckets.",
    ),
    (
        "Treating AGE as a fixed day count",
        "AGE represents calendar intervals.",
    ),
    (
        "Ignoring ISO week-year behavior",
        "Use ISOYEAR with WEEK when reporting ISO weeks.",
    ),
    (
        "Assuming all months have equal length",
        "Calendar arithmetic must account for month lengths.",
    ),
    (
        "Ignoring time zones",
        "Convert to the intended business time zone before local extraction.",
    ),
    (
        "Using unsafe SQL identifier interpolation",
        "Validate identifiers and parameterize values.",
    ),
    (
        "Using an inclusive end-of-day timestamp",
        "Prefer half-open ranges: >= start AND < next_start.",
    ),
    (
        "Treating NULL as zero",
        "Preserve NULL semantics or handle them explicitly.",
    ),
]

for mistake, correction in mistakes:
    print(f"\nMistake: {mistake}")
    print(f"Correction: {correction}")


# ============================================================================
# 33. TESTABLE SQL GENERATION
# ============================================================================

def sql_extract_year(column: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", column):
        raise ValueError("Invalid SQL identifier")
    return f"EXTRACT(YEAR FROM {column})::int"


def sql_month_bucket(column: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", column):
        raise ValueError("Invalid SQL identifier")
    return f"DATE_TRUNC('month', {column})"


def sql_age_from_current_date(column: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", column):
        raise ValueError("Invalid SQL identifier")
    return f"AGE(CURRENT_DATE, {column})"


print("\nQUERY GENERATION")
print("-" * 80)

print(sql_extract_year("birth_date"))
print(sql_month_bucket("created_at"))
print(sql_age_from_current_date("birth_date"))


# ============================================================================
# 34. PERFORMANCE CONSIDERATIONS
# ============================================================================

print("\nPERFORMANCE CONSIDERATIONS")
print("-" * 80)

print(
    """
Date functions themselves are usually inexpensive compared with scanning a
large table.

The important performance question is often where the function is applied.

For reporting:

    SELECT DATE_TRUNC('month', created_at)
    FROM events;

is normal.

For selective filtering on an indexed timestamp:

    WHERE created_at >= :start_time
      AND created_at < :end_time

often gives the optimizer a clearer range condition than:

    WHERE DATE_TRUNC('day', created_at) = :day

Expression indexes can also be appropriate when a functional expression is
frequently queried and the workload justifies maintaining such an index.

Always evaluate the actual query plan for production workloads.
"""
)


# ============================================================================
# 35. SECURITY CONSIDERATIONS
# ============================================================================

print("\nSECURITY CONSIDERATIONS")
print("-" * 80)

print(
    """
Date functions do not normally create a security problem by themselves.

The security risk appears when application code constructs SQL unsafely.

Unsafe pattern:

    sql = "SELECT ... WHERE created_at >= '" + user_input + "'"

Safer pattern:

    SELECT ... WHERE created_at >= %s

with the value supplied through the database driver's parameter mechanism.

SQL identifiers require different handling because they usually cannot be
bound as ordinary values. Validate allowed identifiers or use the database
driver's identifier-composition facilities.
"""
)


# ============================================================================
# 36. ADVANCED QUERY: MONTHLY ACTIVE CUSTOMERS
# ============================================================================

print("\nADVANCED ANALYTICS CASE")
print("-" * 80)

monthly_active_customer_query = """
SELECT
    DATE_TRUNC('month', event_timestamp) AS month_start,
    COUNT(DISTINCT customer_id) AS active_customers
FROM customer_events
WHERE event_timestamp >= :report_start
  AND event_timestamp < :report_end
GROUP BY DATE_TRUNC('month', event_timestamp)
ORDER BY month_start;
""".strip()

print(monthly_active_customer_query)


# ============================================================================
# 37. ADVANCED QUERY: EMPLOYEE TENURE GROUPS
# ============================================================================

tenure_query = """
SELECT
    employee_id,
    employee_name,
    AGE(CURRENT_DATE, joined_date) AS tenure,
    CASE
        WHEN joined_date > CURRENT_DATE THEN 'INVALID_FUTURE_DATE'
        WHEN AGE(CURRENT_DATE, joined_date) < INTERVAL '1 year'
            THEN 'UNDER_1_YEAR'
        WHEN AGE(CURRENT_DATE, joined_date) < INTERVAL '5 years'
            THEN '1_TO_5_YEARS'
        ELSE '5_PLUS_YEARS'
    END AS tenure_group
FROM employees
ORDER BY employee_id;
""".strip()

print(tenure_query)


# ============================================================================
# 38. ADVANCED QUERY: CURRENT MONTH
# ============================================================================

current_month_query = """
SELECT
    DATE_TRUNC('month', CURRENT_DATE) AS current_month_start,
    DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
        AS next_month_start;
""".strip()

print("\nCURRENT MONTH BOUNDARIES")
print(current_month_query)


# ============================================================================
# 39. ADVANCED QUERY: CURRENT QUARTER
# ============================================================================

current_quarter_query = """
SELECT
    DATE_TRUNC('quarter', CURRENT_DATE) AS current_quarter_start,
    DATE_TRUNC('quarter', CURRENT_DATE) + INTERVAL '3 months'
        AS next_quarter_start;
""".strip()

print("\nCURRENT QUARTER BOUNDARIES")
print(current_quarter_query)


# ============================================================================
# 40. ADVANCED QUERY: BIRTHDAY MONTH
# ============================================================================

birthday_query = """
SELECT
    employee_id,
    employee_name,
    birth_date
FROM employees
WHERE EXTRACT(MONTH FROM birth_date)
      = EXTRACT(MONTH FROM CURRENT_DATE);
""".strip()

print("\nBIRTHDAY MONTH QUERY")
print(birthday_query)


# ============================================================================
# 41. ADVANCED QUERY: AGE IN FULL YEARS
# ============================================================================

full_year_age_query = """
SELECT
    employee_id,
    EXTRACT(
        YEAR FROM AGE(CURRENT_DATE, birth_date)
    )::int AS age_years
FROM employees;
""".strip()

print("\nFULL-YEAR AGE QUERY")
print(full_year_age_query)


# ============================================================================
# 42. DIFFERENCE BETWEEN EXTRACT(YEAR) AND AGE
# ============================================================================

print("\nEXTRACT YEAR VS AGE")
print("-" * 80)

print(
    """
These two expressions answer different questions.

    EXTRACT(YEAR FROM birth_date)

answers:
    "What calendar year was this person born?"

    EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_date))

answers:
    "How many complete calendar years old is this person?"

The first describes the date.

The second derives an age from the date.
"""
)


# ============================================================================
# 43. MINI SQL CURRICULUM
# ============================================================================

print("\nMINI STUDY CURRICULUM")
print("-" * 80)

curriculum = [
    "1. Understand DATE, TIMESTAMP, and TIMESTAMPTZ.",
    "2. Learn EXTRACT(field FROM source).",
    "3. Learn DATE_PART('field', source).",
    "4. Compare EXTRACT and DATE_PART.",
    "5. Learn DATE_TRUNC for period boundaries.",
    "6. Understand ISO week and ISO year.",
    "7. Learn AGE for calendar intervals.",
    "8. Understand CURRENT_DATE and transaction time.",
    "9. Combine date functions with GROUP BY.",
    "10. Combine date functions with CASE.",
    "11. Use half-open timestamp ranges for filtering.",
    "12. Consider indexes and query plans.",
    "13. Account for NULL values and invalid dates.",
    "14. Account for time zones.",
    "15. Validate SQL identifiers and parameterize values.",
]

for item in curriculum:
    print(item)


# ============================================================================
# 44. TEST SUITE
# ============================================================================

def run_tests() -> None:
    """Run deterministic tests for the Python teaching implementation."""
    assert python_extract(date(2026, 9, 22), "year") == 2026
    assert python_extract(date(2026, 9, 22), "month") == 9
    assert python_extract(date(2026, 9, 22), "quarter") == 3
    assert python_extract(date(2026, 9, 22), "isodow") == 2

    assert (
        truncate_datetime(
            datetime(2026, 9, 22, 14, 35, 48),
            "day",
        )
        == datetime(2026, 9, 22)
    )

    assert (
        truncate_datetime(
            datetime(2026, 9, 22, 14, 35, 48),
            "month",
        )
        == datetime(2026, 9, 1)
    )

    assert (
        truncate_datetime(
            datetime(2026, 9, 22, 14, 35, 48),
            "year",
        )
        == datetime(2026, 1, 1)
    )

    age = calendar_age(
        date(2026, 9, 22),
        date(1995, 4, 18),
    )

    assert age.years == 31
    assert age.months == 5
    assert age.days == 4

    assert parse_iso_date("2026-09-22") == date(2026, 9, 22)
    assert parse_iso_date("invalid") is None

    try:
        python_extract(REFERENCE_DATE, "invalid-field")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid field should raise ValueError")

    try:
        build_monthly_report_query("orders;DROP", "created_at")
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe identifier should be rejected")

    print("All Python teaching tests passed.")


run_tests()


# ============================================================================
# 45. PERFORMANCE MICRO-EXAMPLE
# ============================================================================

print("\nMICRO PERFORMANCE EXAMPLE")
print("-" * 80)


def benchmark(
    function: Callable[[datetime], Any],
    values: list[datetime],
) -> float:
    start = time.perf_counter()

    for value in values:
        function(value)

    return time.perf_counter() - start


benchmark_values = [
    datetime(2026, 1 + (index % 12), 1 + (index % 28), 12, 0, 0)
    for index in range(10_000)
]

elapsed = benchmark(
    lambda value: truncate_datetime(value, "month"),
    benchmark_values,
)

print(f"Processed {len(benchmark_values):,} timestamp values.")
print(f"Python teaching-model execution time: {elapsed:.6f} seconds.")

print(
    """
This benchmark is not a PostgreSQL database benchmark.

Database performance depends on:
    - table size
    - indexes
    - data distribution
    - PostgreSQL version
    - statistics
    - query plan
    - CPU and memory
    - parallelism
    - storage
    - network overhead
    - whether the expression is evaluated during filtering, grouping,
      projection, or indexing

Use EXPLAIN and EXPLAIN ANALYZE for real PostgreSQL performance investigation.
"""
)


# ============================================================================
# 46. COMPLETE SQL REFERENCE
# ============================================================================

print("\nCOMPLETE SQL REFERENCE")
print("-" * 80)

reference_queries = [
    "SELECT CURRENT_DATE;",
    "SELECT EXTRACT(YEAR FROM CURRENT_DATE);",
    "SELECT DATE_PART('year', CURRENT_DATE);",
    "SELECT DATE_TRUNC('year', CURRENT_DATE);",
    "SELECT AGE(CURRENT_DATE, DATE '1990-05-17');",
    "SELECT EXTRACT(QUARTER FROM CURRENT_DATE);",
    "SELECT EXTRACT(WEEK FROM CURRENT_DATE);",
    "SELECT EXTRACT(ISOYEAR FROM CURRENT_DATE);",
    "SELECT EXTRACT(ISODOW FROM CURRENT_DATE);",
    "SELECT EXTRACT(DOY FROM CURRENT_DATE);",
    "SELECT DATE_TRUNC('week', CURRENT_DATE);",
    "SELECT DATE_TRUNC('month', CURRENT_DATE);",
    "SELECT DATE_TRUNC('quarter', CURRENT_DATE);",
    "SELECT DATE_TRUNC('year', CURRENT_DATE);",
]

for index, query in enumerate(reference_queries, start=1):
    print(f"{index:02}. {query}")


# ============================================================================
# 47. FINAL PRACTICAL SCENARIO
# ============================================================================

print("\nFINAL PRACTICAL SCENARIO")
print("-" * 80)

final_query = """
SELECT
    DATE_TRUNC('month', order_timestamp) AS month_start,
    EXTRACT(YEAR FROM order_timestamp)::int AS order_year,
    EXTRACT(QUARTER FROM order_timestamp)::int AS order_quarter,
    COUNT(*) AS order_count,
    SUM(order_amount) AS revenue
FROM orders
WHERE order_timestamp >= DATE_TRUNC('year', CURRENT_DATE)
  AND order_timestamp < DATE_TRUNC('year', CURRENT_DATE) + INTERVAL '1 year'
GROUP BY
    DATE_TRUNC('month', order_timestamp),
    EXTRACT(YEAR FROM order_timestamp),
    EXTRACT(QUARTER FROM order_timestamp)
ORDER BY month_start;
""".strip()

print(final_query)

print(
    """
This final query combines the central ideas:

CURRENT_DATE
    Establishes the database's current date.

DATE_TRUNC('year', CURRENT_DATE)
    Establishes the beginning of the current year.

INTERVAL '1 year'
    Establishes the exclusive upper boundary.

EXTRACT
    Produces analytical calendar components.

DATE_TRUNC('month', order_timestamp)
    Produces a stable monthly reporting bucket.

GROUP BY
    Converts individual timestamped transactions into reporting periods.

The combination is representative of practical PostgreSQL analytics work.
"""
)

print("\n" + "=" * 80)
print("END OF POSTGRESQL DATE FUNCTIONS STUDY PROGRAM")
print("=" * 80)
