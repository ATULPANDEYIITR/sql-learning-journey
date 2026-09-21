"""
DATE, TIME, TIMESTAMP, INTERVALS, AND DATE ARITHMETIC
=====================================================

A comprehensive standalone study program covering:

- Dates
- Times
- Datetimes
- Timestamps
- Time zones
- UTC
- Date and time parsing
- Formatting
- Date arithmetic
- Time arithmetic
- Timedeltas
- Intervals
- Comparisons
- Recurring dates
- Business-day calculations
- Unix timestamps
- Daylight-saving-time considerations
- Ambiguous and nonexistent local times
- Validation
- Serialization
- Scheduling concepts
- Logging timestamps
- Age calculations
- Duration calculations
- Deadline calculations
- Performance considerations
- Common mistakes
- Production-oriented patterns

Python's standard library is sufficient for the demonstrations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)
from zoneinfo import ZoneInfo
import calendar
import math
import re
import time as time_module
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# 1. BASIC DATE OBJECTS
# ---------------------------------------------------------------------------

print("=" * 80)
print("1. BASIC DATES")
print("=" * 80)

today = date.today()
print("Today's date:", today)
print("Year:", today.year)
print("Month:", today.month)
print("Day:", today.day)
print("ISO representation:", today.isoformat())

specific_date = date(2026, 9, 21)
print("Specific date:", specific_date)

print("Weekday number (Monday=0):", specific_date.weekday())
print("ISO weekday number (Monday=1):", specific_date.isoweekday())

iso_calendar = specific_date.isocalendar()
print("ISO calendar:", iso_calendar)
print("ISO year:", iso_calendar.year)
print("ISO week:", iso_calendar.week)
print("ISO weekday:", iso_calendar.weekday)

print("Days in month:", calendar.monthrange(
    specific_date.year,
    specific_date.month,
)[1])


# ---------------------------------------------------------------------------
# 2. BASIC TIME OBJECTS
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("2. BASIC TIMES")
print("=" * 80)

morning = time(9, 30, 15)
precise_time = time(9, 30, 15, 123456)

print("Time:", morning)
print("Hour:", morning.hour)
print("Minute:", morning.minute)
print("Second:", morning.second)
print("Microsecond:", precise_time.microsecond)

print("Formatted time:", morning.strftime("%H:%M:%S"))


# ---------------------------------------------------------------------------
# 3. DATETIME OBJECTS
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("3. DATETIME")
print("=" * 80)

local_now = datetime.now()
utc_now = datetime.now(timezone.utc)

print("Local datetime:", local_now)
print("UTC datetime:", utc_now)
print("ISO local datetime:", local_now.isoformat())
print("ISO UTC datetime:", utc_now.isoformat())

specific_datetime = datetime(2026, 9, 21, 11, 30, 45)
print("Specific datetime:", specific_datetime)


# ---------------------------------------------------------------------------
# 4. DATE + TIME -> DATETIME
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("4. COMBINING DATE AND TIME")
print("=" * 80)

event_date = date(2026, 10, 1)
event_time = time(14, 30)
event_datetime = datetime.combine(event_date, event_time)

print("Event datetime:", event_datetime)


# ---------------------------------------------------------------------------
# 5. DATETIME -> DATE AND TIME
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("5. EXTRACTING DATE AND TIME")
print("=" * 80)

sample_datetime = datetime(2026, 10, 1, 14, 30, 45)

print("Date part:", sample_datetime.date())
print("Time part:", sample_datetime.time())


# ---------------------------------------------------------------------------
# 6. DATE ARITHMETIC
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("6. DATE ARITHMETIC")
print("=" * 80)

base_date = date(2026, 9, 21)

print("Base date:", base_date)
print("Tomorrow:", base_date + timedelta(days=1))
print("Next week:", base_date + timedelta(days=7))
print("Previous week:", base_date - timedelta(days=7))
print("Thirty days later:", base_date + timedelta(days=30))

difference = date(2026, 12, 31) - base_date
print("Days until end of year:", difference.days)


# ---------------------------------------------------------------------------
# 7. TIME AND DATETIME ARITHMETIC
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("7. DATETIME ARITHMETIC")
print("=" * 80)

start = datetime(2026, 9, 21, 9, 0)
duration = timedelta(hours=8, minutes=30)

end = start + duration

print("Start:", start)
print("Duration:", duration)
print("End:", end)

elapsed = end - start
print("Elapsed:", elapsed)
print("Elapsed seconds:", elapsed.total_seconds())


# ---------------------------------------------------------------------------
# 8. TIMEDELTA
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("8. TIMEDELTA")
print("=" * 80)

interval = timedelta(
    days=2,
    hours=5,
    minutes=20,
    seconds=15,
)

print("Interval:", interval)
print("Days:", interval.days)
print("Seconds component:", interval.seconds)
print("Microseconds:", interval.microseconds)
print("Total seconds:", interval.total_seconds())

print("Half interval:", interval / 2)
print("Double interval:", interval * 2)


# ---------------------------------------------------------------------------
# 9. DATETIME COMPARISON
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("9. DATE AND DATETIME COMPARISON")
print("=" * 80)

date_a = date(2026, 9, 20)
date_b = date(2026, 9, 21)

print("a < b:", date_a < date_b)
print("a == b:", date_a == date_b)

datetime_a = datetime(2026, 9, 21, 10, 0)
datetime_b = datetime(2026, 9, 21, 11, 0)

print("datetime_a < datetime_b:", datetime_a < datetime_b)


# ---------------------------------------------------------------------------
# 10. AWARE VS NAIVE DATETIMES
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("10. NAIVE AND TIME-ZONE-AWARE DATETIMES")
print("=" * 80)

naive_datetime = datetime(2026, 9, 21, 12, 0)
aware_utc_datetime = datetime(
    2026,
    9,
    21,
    12,
    0,
    tzinfo=timezone.utc,
)

print("Naive:", naive_datetime)
print("Aware:", aware_utc_datetime)
print("Aware timezone:", aware_utc_datetime.tzinfo)

# Naive and aware datetime objects should not be mixed in comparisons.
try:
    print(naive_datetime < aware_utc_datetime)
except TypeError as error:
    print("Expected comparison error:", error)


# ---------------------------------------------------------------------------
# 11. TIME ZONES
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("11. TIME ZONES")
print("=" * 80)

utc_time = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)

india_time = utc_time.astimezone(ZoneInfo("Asia/Kolkata"))
new_york_time = utc_time.astimezone(ZoneInfo("America/New_York"))
london_time = utc_time.astimezone(ZoneInfo("Europe/London"))
tokyo_time = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))

print("UTC:", utc_time)
print("India:", india_time)
print("New York:", new_york_time)
print("London:", london_time)
print("Tokyo:", tokyo_time)


# ---------------------------------------------------------------------------
# 12. UTC AS A COMMON REFERENCE
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("12. UTC NORMALIZATION")
print("=" * 80)

user_local_time = datetime(
    2026,
    9,
    21,
    18,
    30,
    tzinfo=ZoneInfo("Asia/Kolkata"),
)

normalized_utc = user_local_time.astimezone(timezone.utc)

print("User local time:", user_local_time)
print("Normalized UTC:", normalized_utc)


# ---------------------------------------------------------------------------
# 13. UNIX TIMESTAMPS
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("13. UNIX TIMESTAMPS")
print("=" * 80)

timestamp = normalized_utc.timestamp()
print("Unix timestamp:", timestamp)

restored = datetime.fromtimestamp(timestamp, tz=timezone.utc)
print("Restored UTC datetime:", restored)

timestamp_seconds = int(timestamp)
print("Integer timestamp:", timestamp_seconds)


# ---------------------------------------------------------------------------
# 14. TIMESTAMP PRECISION
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("14. TIMESTAMP PRECISION")
print("=" * 80)

precise_timestamp = datetime.now(timezone.utc).timestamp()

print("Floating-point timestamp:", precise_timestamp)
print("Milliseconds:", int(precise_timestamp * 1000))
print("Microseconds:", int(precise_timestamp * 1_000_000))


# ---------------------------------------------------------------------------
# 15. STRING FORMATTING WITH STRFTIME
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("15. FORMATTING")
print("=" * 80)

formatted_datetime = datetime(
    2026,
    9,
    21,
    14,
    35,
    42,
)

formats = {
    "ISO-like": "%Y-%m-%d %H:%M:%S",
    "US-style": "%m/%d/%Y",
    "Human-readable": "%A, %B %d, %Y",
    "Time": "%I:%M:%S %p",
    "Compact": "%Y%m%d_%H%M%S",
}

for name, format_string in formats.items():
    print(f"{name}: {formatted_datetime.strftime(format_string)}")


# ---------------------------------------------------------------------------
# 16. PARSING STRINGS WITH STRPTIME
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("16. PARSING")
print("=" * 80)

date_text = "2026-09-21"
parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date()

datetime_text = "2026-09-21 14:35:42"
parsed_datetime = datetime.strptime(
    datetime_text,
    "%Y-%m-%d %H:%M:%S",
)

print("Parsed date:", parsed_date)
print("Parsed datetime:", parsed_datetime)


# ---------------------------------------------------------------------------
# 17. ISO 8601 PARSING
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("17. ISO 8601")
print("=" * 80)

iso_text = "2026-09-21T14:35:42+05:30"
iso_datetime = datetime.fromisoformat(iso_text)

print("Parsed ISO datetime:", iso_datetime)
print("UTC conversion:", iso_datetime.astimezone(timezone.utc))


# ---------------------------------------------------------------------------
# 18. SAFE DATE PARSING
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("18. VALIDATION")
print("=" * 80)


def parse_date_safely(value: str) -> Optional[date]:
    """Return a date or None when the input is invalid."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


for value in ["2026-09-21", "2026-02-30", "hello", "2026-13-01"]:
    print(value, "->", parse_date_safely(value))


# ---------------------------------------------------------------------------
# 19. LEAP YEARS
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("19. LEAP YEARS")
print("=" * 80)


def is_leap_year(year: int) -> bool:
    return calendar.isleap(year)


for year in [2024, 2025, 2026, 2100, 2000]:
    print(year, "is leap year:", is_leap_year(year))


# ---------------------------------------------------------------------------
# 20. DAYS IN MONTH
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("20. DAYS IN MONTH")
print("=" * 80)


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


for month in range(1, 13):
    print(
        f"{month:02d}:",
        days_in_month(2026, month),
    )


# ---------------------------------------------------------------------------
# 21. END OF MONTH
# ---------------------------------------------------------------------------


def end_of_month(value: date) -> date:
    last_day = calendar.monthrange(value.year, value.month)[1]
    return value.replace(day=last_day)


print("\nEnd of month:", end_of_month(date(2026, 2, 15)))


# ---------------------------------------------------------------------------
# 22. START OF MONTH
# ---------------------------------------------------------------------------


def start_of_month(value: date) -> date:
    return value.replace(day=1)


print("Start of month:", start_of_month(date(2026, 9, 21)))


# ---------------------------------------------------------------------------
# 23. QUARTER CALCULATION
# ---------------------------------------------------------------------------


def quarter_of_date(value: date) -> int:
    return ((value.month - 1) // 3) + 1


print("\nQuarter:", quarter_of_date(date(2026, 9, 21)))


# ---------------------------------------------------------------------------
# 24. START OF QUARTER
# ---------------------------------------------------------------------------


def start_of_quarter(value: date) -> date:
    quarter = quarter_of_date(value)
    first_month = 3 * (quarter - 1) + 1
    return date(value.year, first_month, 1)


print(
    "Start of quarter:",
    start_of_quarter(date(2026, 9, 21)),
)


# ---------------------------------------------------------------------------
# 25. END OF QUARTER
# ---------------------------------------------------------------------------


def end_of_quarter(value: date) -> date:
    quarter = quarter_of_date(value)

    if quarter == 4:
        next_quarter = date(value.year + 1, 1, 1)
    else:
        next_quarter = date(
            value.year,
            quarter * 3 + 1,
            1,
        )

    return next_quarter - timedelta(days=1)


print(
    "End of quarter:",
    end_of_quarter(date(2026, 9, 21)),
)


# ---------------------------------------------------------------------------
# 26. BUSINESS DAYS
# ---------------------------------------------------------------------------


def is_business_day(value: date) -> bool:
    return value.weekday() < 5


def add_business_days(
    start_date: date,
    number_of_days: int,
) -> date:
    """Move forward or backward while skipping Saturday and Sunday."""
    current = start_date
    step = 1 if number_of_days >= 0 else -1
    remaining = abs(number_of_days)

    while remaining:
        current += timedelta(days=step)
        if is_business_day(current):
            remaining -= 1

    return current


print("\nBusiness-day calculations:")
print(
    "5 business days after:",
    add_business_days(date(2026, 9, 21), 5),
)
print(
    "5 business days before:",
    add_business_days(date(2026, 9, 21), -5),
)


# ---------------------------------------------------------------------------
# 27. BUSINESS-DAY COUNT
# ---------------------------------------------------------------------------


def count_business_days(
    start_date: date,
    end_date: date,
) -> int:
    """Count business days in the inclusive range."""
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    count = 0
    current = start_date

    while current <= end_date:
        if is_business_day(current):
            count += 1
        current += timedelta(days=1)

    return count


print(
    "Business days in period:",
    count_business_days(
        date(2026, 9, 21),
        date(2026, 9, 30),
    ),
)


# ---------------------------------------------------------------------------
# 28. CUSTOM HOLIDAY CALENDAR
# ---------------------------------------------------------------------------


def add_business_days_with_holidays(
    start_date: date,
    number_of_days: int,
    holidays: Iterable[date],
) -> date:
    holiday_set = set(holidays)

    def valid_business_day(value: date) -> bool:
        return (
            value.weekday() < 5
            and value not in holiday_set
        )

    current = start_date
    step = 1 if number_of_days >= 0 else -1
    remaining = abs(number_of_days)

    while remaining:
        current += timedelta(days=step)
        if valid_business_day(current):
            remaining -= 1

    return current


holidays = {
    date(2026, 9, 25),
}

print(
    "\nBusiness day with holiday exclusion:",
    add_business_days_with_holidays(
        date(2026, 9, 21),
        5,
        holidays,
    ),
)


# ---------------------------------------------------------------------------
# 29. AGE CALCULATION
# ---------------------------------------------------------------------------


def calculate_age(
    birth_date: date,
    reference_date: Optional[date] = None,
) -> int:
    if reference_date is None:
        reference_date = date.today()

    age = reference_date.year - birth_date.year

    birthday_has_occurred = (
        (reference_date.month, reference_date.day)
        >= (birth_date.month, birth_date.day)
    )

    if not birthday_has_occurred:
        age -= 1

    return age


print(
    "\nAge:",
    calculate_age(
        date(1995, 5, 10),
        date(2026, 9, 21),
    ),
)


# ---------------------------------------------------------------------------
# 30. PRECISE AGE INFORMATION
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Age:
    years: int
    months: int
    days: int


def calculate_age_components(
    birth_date: date,
    reference_date: date,
) -> Age:
    if birth_date > reference_date:
        raise ValueError("Birth date cannot be in the future.")

    years = reference_date.year - birth_date.year
    anniversary = birth_date.replace(
        year=birth_date.year + years
    )

    if anniversary > reference_date:
        years -= 1
        anniversary = birth_date.replace(
            year=birth_date.year + years
        )

    months = 0
    cursor = anniversary

    while True:
        next_month = cursor.month + 1
        next_year = cursor.year

        if next_month == 13:
            next_month = 1
            next_year += 1

        last_day = calendar.monthrange(
            next_year,
            next_month,
        )[1]

        next_cursor = date(
            next_year,
            next_month,
            min(cursor.day, last_day),
        )

        if next_cursor <= reference_date:
            months += 1
            cursor = next_cursor
        else:
            break

    days = (reference_date - cursor).days

    return Age(years, months, days)


print(
    "Age components:",
    calculate_age_components(
        date(1995, 5, 10),
        date(2026, 9, 21),
    ),
)


# ---------------------------------------------------------------------------
# 31. MONTH ADDITION
# ---------------------------------------------------------------------------

def add_months(value: date, months: int) -> date:
    """
    Add calendar months while clamping the day to the last valid
    day of the destination month.

    Example:
        January 31 + 1 month -> February 28/29
    """
    zero_based_month = value.month - 1 + months

    target_year = value.year + zero_based_month // 12
    target_month = zero_based_month % 12 + 1

    last_day = calendar.monthrange(
        target_year,
        target_month,
    )[1]

    target_day = min(value.day, last_day)

    return date(
        target_year,
        target_month,
        target_day,
    )


print("\nMonth arithmetic:")
print("2026-01-31 + 1 month:", add_months(date(2026, 1, 31), 1))
print("2024-01-31 + 1 month:", add_months(date(2024, 1, 31), 1))
print("2026-03-31 - 1 month:", add_months(date(2026, 3, 31), -1))


# ---------------------------------------------------------------------------
# 32. YEAR ADDITION
# ---------------------------------------------------------------------------

def add_years(value: date, years: int) -> date:
    target_year = value.year + years

    if value.month == 2 and value.day == 29:
        if not calendar.isleap(target_year):
            return date(target_year, 2, 28)

    return date(
        target_year,
        value.month,
        value.day,
    )


print(
    "\nLeap-day year arithmetic:",
    add_years(date(2024, 2, 29), 1),
)


# ---------------------------------------------------------------------------
# 33. DATE RANGES
# ---------------------------------------------------------------------------


def date_range(
    start_date: date,
    end_date: date,
    step: int = 1,
) -> list[date]:
    if step == 0:
        raise ValueError("Step cannot be zero.")

    result = []
    current = start_date

    if step > 0:
        while current <= end_date:
            result.append(current)
            current += timedelta(days=step)
    else:
        while current >= end_date:
            result.append(current)
            current += timedelta(days=step)

    return result


print("\nDate range:")
for value in date_range(
    date(2026, 9, 21),
    date(2026, 9, 25),
):
    print(value)


# ---------------------------------------------------------------------------
# 34. RECURRING EVENTS
# ---------------------------------------------------------------------------


def generate_weekly_events(
    first_event: date,
    number_of_events: int,
) -> list[date]:
    return [
        first_event + timedelta(days=7 * index)
        for index in range(number_of_events)
    ]


print("\nWeekly events:")
for event in generate_weekly_events(
    date(2026, 9, 21),
    5,
):
    print(event)


# ---------------------------------------------------------------------------
# 35. INTERVAL MODEL
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DateInterval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(
                "Interval start cannot be after interval end."
            )

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def contains(self, value: datetime) -> bool:
        return self.start <= value <= self.end

    def overlaps(self, other: "DateInterval") -> bool:
        return (
            self.start <= other.end
            and other.start <= self.end
        )


interval_a = DateInterval(
    datetime(2026, 9, 21, 9),
    datetime(2026, 9, 21, 12),
)

interval_b = DateInterval(
    datetime(2026, 9, 21, 11),
    datetime(2026, 9, 21, 15),
)

print("\nInterval A duration:", interval_a.duration)
print("Interval A contains 10:00:", interval_a.contains(
    datetime(2026, 9, 21, 10),
))
print("Intervals overlap:", interval_a.overlaps(interval_b))


# ---------------------------------------------------------------------------
# 36. INTERVAL MERGING
# ---------------------------------------------------------------------------


def merge_intervals(
    intervals: list[DateInterval],
) -> list[DateInterval]:
    if not intervals:
        return []

    sorted_intervals = sorted(
        intervals,
        key=lambda item: item.start,
    )

    merged = [sorted_intervals[0]]

    for current in sorted_intervals[1:]:
        previous = merged[-1]

        if current.start <= previous.end:
            merged[-1] = DateInterval(
                previous.start,
                max(previous.end, current.end),
            )
        else:
            merged.append(current)

    return merged


merged = merge_intervals([
    DateInterval(
        datetime(2026, 9, 21, 9),
        datetime(2026, 9, 21, 11),
    ),
    DateInterval(
        datetime(2026, 9, 21, 10, 30),
        datetime(2026, 9, 21, 13),
    ),
    DateInterval(
        datetime(2026, 9, 21, 15),
        datetime(2026, 9, 21, 16),
    ),
])

print("\nMerged intervals:")
for interval_item in merged:
    print(interval_item)


# ---------------------------------------------------------------------------
# 37. INTERVAL INTERSECTION
# ---------------------------------------------------------------------------


def intersect_intervals(
    first: DateInterval,
    second: DateInterval,
) -> Optional[DateInterval]:
    start_value = max(first.start, second.start)
    end_value = min(first.end, second.end)

    if start_value > end_value:
        return None

    return DateInterval(start_value, end_value)


intersection = intersect_intervals(interval_a, interval_b)
print("\nIntersection:", intersection)


# ---------------------------------------------------------------------------
# 38. DST-AWARE TIME ZONES
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("38. DAYLIGHT-SAVING-TIME CONSIDERATIONS")
print("=" * 80)

new_york_zone = ZoneInfo("America/New_York")

before_dst = datetime(
    2026,
    3,
    8,
    1,
    30,
    tzinfo=new_york_zone,
)

print("DST-related local time:", before_dst)
print(
    "UTC equivalent:",
    before_dst.astimezone(timezone.utc),
)

# ZoneInfo applies the timezone rules known to the local timezone database.
# Applications that schedule events around DST transitions should explicitly
# decide whether a recurrence is defined in local wall-clock time or elapsed
# UTC duration.


# ---------------------------------------------------------------------------
# 39. WALL-CLOCK TIME VS ELAPSED TIME
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("39. WALL-CLOCK VS ELAPSED TIME")
print("=" * 80)

utc_start = datetime(
    2026,
    11,
    1,
    5,
    0,
    tzinfo=timezone.utc,
)

utc_end = utc_start + timedelta(hours=8)

ny_start = utc_start.astimezone(new_york_zone)
ny_end = utc_end.astimezone(new_york_zone)

print("UTC start:", utc_start)
print("UTC end:", utc_end)
print("New York start:", ny_start)
print("New York end:", ny_end)
print("Actual elapsed duration:", utc_end - utc_start)


# ---------------------------------------------------------------------------
# 40. ISO SERIALIZATION
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("40. SERIALIZATION")
print("=" * 80)

recorded_at = datetime.now(timezone.utc)

serialized = recorded_at.isoformat()
restored_datetime = datetime.fromisoformat(serialized)

print("Original:", recorded_at)
print("Serialized:", serialized)
print("Restored:", restored_datetime)


# ---------------------------------------------------------------------------
# 41. DATABASE-STYLE RECORD
# ---------------------------------------------------------------------------


@dataclass
class Event:
    event_id: int
    name: str
    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        if self.starts_at.tzinfo is None:
            raise ValueError("starts_at must be timezone-aware.")

        if self.ends_at.tzinfo is None:
            raise ValueError("ends_at must be timezone-aware.")

        if self.starts_at > self.ends_at:
            raise ValueError(
                "Event start cannot be after event end."
            )

    @property
    def duration(self) -> timedelta:
        return self.ends_at - self.starts_at


event = Event(
    event_id=1001,
    name="System Maintenance",
    starts_at=datetime(
        2026,
        9,
        25,
        18,
        0,
        tzinfo=timezone.utc,
    ),
    ends_at=datetime(
        2026,
        9,
        25,
        20,
        30,
        tzinfo=timezone.utc,
    ),
)

print("\nEvent:", event.name)
print("Duration:", event.duration)


# ---------------------------------------------------------------------------
# 42. DEADLINE CHECKING
# ---------------------------------------------------------------------------


def deadline_status(
    deadline: datetime,
    current: datetime,
) -> str:
    if deadline.tzinfo is None or current.tzinfo is None:
        raise ValueError(
            "Deadline and current time must be timezone-aware."
        )

    if current < deadline:
        remaining = deadline - current
        return f"OPEN: {remaining} remaining"

    if current == deadline:
        return "DUE NOW"

    overdue = current - deadline
    return f"OVERDUE: {overdue} past deadline"


print(
    "\nDeadline:",
    deadline_status(
        datetime(
            2026,
            9,
            22,
            17,
            0,
            tzinfo=timezone.utc,
        ),
        datetime(
            2026,
            9,
            21,
            17,
            0,
            tzinfo=timezone.utc,
        ),
    ),
)


# ---------------------------------------------------------------------------
# 43. EXPIRATION
# ---------------------------------------------------------------------------


def is_expired(
    created_at: datetime,
    lifetime: timedelta,
    current_time: Optional[datetime] = None,
) -> bool:
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    return current_time >= created_at + lifetime


created = datetime(
    2026,
    9,
    21,
    10,
    0,
    tzinfo=timezone.utc,
)

print(
    "\nExpired:",
    is_expired(
        created,
        timedelta(hours=2),
        datetime(
            2026,
            9,
            21,
            12,
            1,
            tzinfo=timezone.utc,
        ),
    ),
)


# ---------------------------------------------------------------------------
# 44. SLIDING TIME WINDOW
# ---------------------------------------------------------------------------


def is_within_window(
    timestamp_value: datetime,
    reference_time: datetime,
    window: timedelta,
) -> bool:
    return (
        reference_time - window
        <= timestamp_value
        <= reference_time
    )


reference = datetime(
    2026,
    9,
    21,
    12,
    0,
    tzinfo=timezone.utc,
)

candidate = reference - timedelta(minutes=20)

print(
    "\nWithin 30-minute window:",
    is_within_window(
        candidate,
        reference,
        timedelta(minutes=30),
    ),
)


# ---------------------------------------------------------------------------
# 45. ROUNDING TO A MINUTE
# ---------------------------------------------------------------------------


def floor_to_minute(value: datetime) -> datetime:
    return value.replace(
        second=0,
        microsecond=0,
    )


def ceil_to_minute(value: datetime) -> datetime:
    floored = floor_to_minute(value)

    if value == floored:
        return floored

    return floored + timedelta(minutes=1)


sample = datetime(
    2026,
    9,
    21,
    12,
    30,
    45,
    123,
)

print("\nOriginal:", sample)
print("Floor to minute:", floor_to_minute(sample))
print("Ceil to minute:", ceil_to_minute(sample))


# ---------------------------------------------------------------------------
# 46. ROUNDING TO AN INTERVAL
# ---------------------------------------------------------------------------


def floor_datetime(
    value: datetime,
    interval_seconds: int,
) -> datetime:
    if interval_seconds <= 0:
        raise ValueError("Interval must be positive.")

    epoch = datetime(
        1970,
        1,
        1,
        tzinfo=value.tzinfo,
    )

    elapsed_seconds = (value - epoch).total_seconds()
    floored_seconds = (
        math.floor(elapsed_seconds / interval_seconds)
        * interval_seconds
    )

    return epoch + timedelta(seconds=floored_seconds)


print(
    "\nFloor to 15-minute interval:",
    floor_datetime(
        datetime(
            2026,
            9,
            21,
            12,
            37,
            tzinfo=timezone.utc,
        ),
        15 * 60,
    ),
)


# ---------------------------------------------------------------------------
# 47. ISO WEEK DATE INFORMATION
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("47. ISO WEEK")
print("=" * 80)

for value in [
    date(2025, 12, 29),
    date(2025, 12, 31),
    date(2026, 1, 1),
]:
    print(value, "->", value.isocalendar())


# ---------------------------------------------------------------------------
# 48. PERIOD CLASSIFICATION
# ---------------------------------------------------------------------------


def classify_time_of_day(value: time) -> str:
    if value.hour < 5:
        return "night"
    if value.hour < 12:
        return "morning"
    if value.hour < 17:
        return "afternoon"
    if value.hour < 21:
        return "evening"
    return "night"


for hour in [2, 8, 13, 18, 22]:
    print(
        f"{hour:02d}:00 ->",
        classify_time_of_day(time(hour)),
    )


# ---------------------------------------------------------------------------
# 49. SCHEDULED EVENTS
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScheduledEvent:
    name: str
    starts_at: datetime
    duration: timedelta

    @property
    def ends_at(self) -> datetime:
        return self.starts_at + self.duration


schedule = [
    ScheduledEvent(
        "Stand-up",
        datetime(2026, 9, 21, 9, 0, tzinfo=timezone.utc),
        timedelta(minutes=30),
    ),
    ScheduledEvent(
        "Development",
        datetime(2026, 9, 21, 9, 30, tzinfo=timezone.utc),
        timedelta(hours=2),
    ),
    ScheduledEvent(
        "Review",
        datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        timedelta(hours=1),
    ),
]

print("\nSchedule:")
for scheduled_event in schedule:
    print(
        scheduled_event.name,
        scheduled_event.starts_at,
        "->",
        scheduled_event.ends_at,
    )


# ---------------------------------------------------------------------------
# 50. DETECTING SCHEDULE CONFLICTS
# ---------------------------------------------------------------------------


def has_schedule_conflict(
    first: ScheduledEvent,
    second: ScheduledEvent,
) -> bool:
    return (
        first.starts_at < second.ends_at
        and second.starts_at < first.ends_at
    )


print(
    "\nSchedule conflict:",
    has_schedule_conflict(
        schedule[0],
        schedule[1],
    ),
)


# ---------------------------------------------------------------------------
# 51. HIGH-RESOLUTION PERFORMANCE TIMING
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("51. PERFORMANCE TIMING")
print("=" * 80)

performance_start = time_module.perf_counter()

total = sum(range(1_000_000))

performance_end = time_module.perf_counter()

print("Calculated value:", total)
print(
    "Elapsed performance time:",
    performance_end - performance_start,
    "seconds",
)

# perf_counter() is intended for measuring elapsed execution time.
# datetime.now() is intended for civil time, not benchmark measurement.


# ---------------------------------------------------------------------------
# 52. MONOTONIC TIME CONCEPT
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("52. MONOTONIC CLOCK")
print("=" * 80)

monotonic_start = time_module.monotonic()
time_module.sleep(0.01)
monotonic_end = time_module.monotonic()

print(
    "Measured duration:",
    monotonic_end - monotonic_start,
)

# A monotonic clock should be preferred for measuring durations because
# wall-clock time can change due to synchronization or manual adjustment.


# ---------------------------------------------------------------------------
# 53. VALIDATING A TIME RANGE
# ---------------------------------------------------------------------------


def validate_time_range(
    start_time: time,
    end_time: time,
) -> bool:
    return start_time <= end_time


print(
    "\nValid time range:",
    validate_time_range(
        time(9),
        time(17),
    ),
)


# ---------------------------------------------------------------------------
# 54. OVERNIGHT TIME RANGE
# ---------------------------------------------------------------------------


def time_range_contains(
    target: time,
    start_time: time,
    end_time: time,
) -> bool:
    if start_time <= end_time:
        return start_time <= target <= end_time

    # When start > end, the interval crosses midnight.
    return target >= start_time or target <= end_time


print(
    "\n22:00-02:00 contains 23:30:",
    time_range_contains(
        time(23, 30),
        time(22),
        time(2),
    ),
)

print(
    "22:00-02:00 contains 12:00:",
    time_range_contains(
        time(12),
        time(22),
        time(2),
    ),
)


# ---------------------------------------------------------------------------
# 55. DATE RANGE OVERLAP
# ---------------------------------------------------------------------------


def date_ranges_overlap(
    first_start: date,
    first_end: date,
    second_start: date,
    second_end: date,
) -> bool:
    if first_start > first_end or second_start > second_end:
        raise ValueError("Invalid date range.")

    return (
        first_start <= second_end
        and second_start <= first_end
    )


print(
    "\nDate ranges overlap:",
    date_ranges_overlap(
        date(2026, 9, 1),
        date(2026, 9, 10),
        date(2026, 9, 10),
        date(2026, 9, 20),
    ),
)


# ---------------------------------------------------------------------------
# 56. SAFE CONVERSION FROM UNIX TIMESTAMP
# ---------------------------------------------------------------------------


def unix_to_utc(timestamp_value: float) -> datetime:
    return datetime.fromtimestamp(
        timestamp_value,
        tz=timezone.utc,
    )


print(
    "\nUnix to UTC:",
    unix_to_utc(0),
)


# ---------------------------------------------------------------------------
# 57. LOG RECORD WITH UTC TIMESTAMP
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LogRecord:
    level: str
    message: str
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError(
                "Log timestamps must be timezone-aware."
            )

    def serialize(self) -> str:
        return (
            f"{self.timestamp.isoformat()} "
            f"[{self.level}] {self.message}"
        )


log_record = LogRecord(
    level="INFO",
    message="Application started",
    timestamp=datetime.now(timezone.utc),
)

print("\nSerialized log:")
print(log_record.serialize())


# ---------------------------------------------------------------------------
# 58. TOKEN EXPIRATION MODEL
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Token:
    issued_at: datetime
    expires_at: datetime

    def is_valid(self, now: datetime) -> bool:
        return (
            self.issued_at <= now < self.expires_at
        )


issued = datetime(
    2026,
    9,
    21,
    10,
    tzinfo=timezone.utc,
)

token = Token(
    issued_at=issued,
    expires_at=issued + timedelta(hours=1),
)

print(
    "\nToken valid:",
    token.is_valid(
        issued + timedelta(minutes=30)
    ),
)

print(
    "Token valid after expiration:",
    token.is_valid(
        issued + timedelta(hours=2)
    ),
)


# ---------------------------------------------------------------------------
# 59. COMMON ERROR CASES
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("59. COMMON ERROR CASES")
print("=" * 80)

invalid_examples = [
    lambda: date(2026, 2, 30),
    lambda: time(25, 0),
    lambda: datetime.strptime(
        "2026/09/21",
        "%Y-%m-%d",
    ),
]

for example in invalid_examples:
    try:
        example()
    except (ValueError, OverflowError) as error:
        print("Handled:", error)


# ---------------------------------------------------------------------------
# 60. IMPORTANT DATE/TIME DESIGN RULES
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("60. PRODUCTION DESIGN RULES")
print("=" * 80)

rules = [
    "Use date when only a calendar date matters.",
    "Use time when only a wall-clock time matters.",
    "Use datetime when date and time are both meaningful.",
    "Use timezone-aware datetime for cross-system timestamps.",
    "Prefer UTC for stored machine timestamps.",
    "Convert UTC into local time at presentation boundaries.",
    "Use timedelta for elapsed durations.",
    "Use calendar-aware logic for months and years.",
    "Do not assume every day contains exactly 24 local-clock hours.",
    "Use monotonic clocks for elapsed-performance measurement.",
    "Validate external date/time input.",
    "Use ISO 8601 for interoperable serialized timestamps.",
]

for index, rule in enumerate(rules, start=1):
    print(f"{index:02d}. {rule}")


# ---------------------------------------------------------------------------
# 61. FINAL INTEGRATED EXAMPLE
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("61. INTEGRATED EVENT PROCESSING EXAMPLE")
print("=" * 80)


@dataclass
class Meeting:
    title: str
    start: datetime
    duration: timedelta

    @property
    def end(self) -> datetime:
        return self.start + self.duration

    def overlaps(self, other: "Meeting") -> bool:
        return (
            self.start < other.end
            and other.start < self.end
        )


meetings = [
    Meeting(
        "Architecture Review",
        datetime(
            2026,
            9,
            21,
            9,
            0,
            tzinfo=ZoneInfo("Asia/Kolkata"),
        ),
        timedelta(hours=1),
    ),
    Meeting(
        "Implementation Session",
        datetime(
            2026,
            9,
            21,
            10,
            30,
            tzinfo=ZoneInfo("Asia/Kolkata"),
        ),
        timedelta(hours=2),
    ),
    Meeting(
        "Deployment",
        datetime(
            2026,
            9,
            21,
            13,
            0,
            tzinfo=ZoneInfo("Asia/Kolkata"),
        ),
        timedelta(minutes=45),
    ),
]

for meeting in meetings:
    print(
        f"{meeting.title}: "
        f"{meeting.start.isoformat()} -> "
        f"{meeting.end.isoformat()} "
        f"({meeting.duration})"
    )

print("\nMeeting conflicts:")

for index, first in enumerate(meetings):
    for second in meetings[index + 1:]:
        print(
            f"{first.title} / {second.title}:",
            first.overlaps(second),
        )


# ---------------------------------------------------------------------------
# 62. FINAL PRACTICAL CHECKLIST
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("62. PRACTICAL CHECKLIST")
print("=" * 80)

checklist = {
    "Calendar date": isinstance(today, date),
    "Wall-clock time": isinstance(morning, time),
    "Datetime": isinstance(local_now, datetime),
    "Duration": isinstance(duration, timedelta),
    "UTC timestamp": aware_utc_datetime.tzinfo is not None,
    "ISO serialization": isinstance(serialized, str),
    "Date arithmetic": (base_date + timedelta(days=1)) > base_date,
    "Interval validation": interval_a.start <= interval_a.end,
}

for check_name, result in checklist.items():
    print(f"{check_name}: {'PASS' if result else 'FAIL'}")


print("\nDate, time, timestamp, interval, and date-arithmetic study complete.")
