/*
DATE, TIME, TIMESTAMP, INTERVALS, AND DATE ARITHMETIC
=====================================================

This file provides a standalone JavaScript study program covering:

- Date objects
- Time representation
- Date and time components
- Unix timestamps
- UTC
- Local time
- ISO 8601
- Parsing
- Formatting
- Date arithmetic
- Duration and intervals
- Month and year arithmetic
- Business days
- Recurring events
- Date ranges
- Interval overlap
- Scheduling
- Expiration
- Deadlines
- Validation
- Daylight-saving-time considerations
- Performance timing
- Temporal design principles

The implementation uses standard JavaScript APIs and requires no npm packages.
It can run in Node.js.
*/

"use strict";

console.log("=".repeat(80));
console.log("DATE, TIME, TIMESTAMP, INTERVALS, AND DATE ARITHMETIC");
console.log("=".repeat(80));


// -----------------------------------------------------------------------------
// 1. CURRENT DATE AND TIME
// -----------------------------------------------------------------------------

console.log("\n1. CURRENT DATE AND TIME");

const now = new Date();

console.log("Current Date object:", now);
console.log("ISO:", now.toISOString());
console.log("Timestamp milliseconds:", now.getTime());


// -----------------------------------------------------------------------------
// 2. DATE COMPONENTS
// -----------------------------------------------------------------------------

console.log("\n2. DATE COMPONENTS");

console.log("Local year:", now.getFullYear());
console.log("Local month:", now.getMonth() + 1);
console.log("Local day:", now.getDate());
console.log("Local weekday:", now.getDay());
console.log("Local hour:", now.getHours());
console.log("Local minute:", now.getMinutes());
console.log("Local second:", now.getSeconds());

console.log("UTC year:", now.getUTCFullYear());
console.log("UTC month:", now.getUTCMonth() + 1);
console.log("UTC day:", now.getUTCDate());
console.log("UTC hour:", now.getUTCHours());


// -----------------------------------------------------------------------------
// 3. CREATING A DATE
// -----------------------------------------------------------------------------

console.log("\n3. CREATING DATES");

const specificDate = new Date(2026, 8, 21, 11, 30, 45);

console.log("Specific local date:", specificDate);
console.log("ISO representation:", specificDate.toISOString());

/*
JavaScript's numeric month argument is zero-based:

0 = January
1 = February
...
8 = September

This is a common source of mistakes.
*/


// -----------------------------------------------------------------------------
// 4. UTC DATE CREATION
// -----------------------------------------------------------------------------

console.log("\n4. UTC DATE CREATION");

const utcDate = new Date(Date.UTC(
    2026,
    8,
    21,
    11,
    30,
    45
));

console.log("UTC date:", utcDate);
console.log("ISO:", utcDate.toISOString());


// -----------------------------------------------------------------------------
// 5. UNIX TIMESTAMP
// -----------------------------------------------------------------------------

console.log("\n5. UNIX TIMESTAMP");

const timestampMilliseconds = utcDate.getTime();
const timestampSeconds = Math.floor(timestampMilliseconds / 1000);

console.log("Milliseconds:", timestampMilliseconds);
console.log("Seconds:", timestampSeconds);

const restoredDate = new Date(timestampMilliseconds);
console.log("Restored:", restoredDate.toISOString());


// -----------------------------------------------------------------------------
// 6. DATE ARITHMETIC
// -----------------------------------------------------------------------------

console.log("\n6. DATE ARITHMETIC");

function addDays(date, numberOfDays) {
    const result = new Date(date.getTime());
    result.setDate(result.getDate() + numberOfDays);
    return result;
}

const baseDate = new Date(2026, 8, 21);

console.log("Base:", baseDate.toISOString());
console.log("Tomorrow:", addDays(baseDate, 1).toISOString());
console.log("Next week:", addDays(baseDate, 7).toISOString());
console.log("Previous week:", addDays(baseDate, -7).toISOString());


// -----------------------------------------------------------------------------
// 7. DIFFERENCE BETWEEN TWO DATES
// -----------------------------------------------------------------------------

console.log("\n7. DATE DIFFERENCE");

function differenceInMilliseconds(first, second) {
    return second.getTime() - first.getTime();
}

function differenceInDays(first, second) {
    return differenceInMilliseconds(first, second)
        / (24 * 60 * 60 * 1000);
}

const firstDate = new Date("2026-09-21T00:00:00Z");
const secondDate = new Date("2026-09-30T00:00:00Z");

console.log(
    "Milliseconds:",
    differenceInMilliseconds(firstDate, secondDate)
);

console.log(
    "Days:",
    differenceInDays(firstDate, secondDate)
);


// -----------------------------------------------------------------------------
// 8. DURATION REPRESENTATION
// -----------------------------------------------------------------------------

console.log("\n8. DURATION");

const duration = {
    days: 2,
    hours: 5,
    minutes: 30,
    seconds: 15
};

function durationToMilliseconds(value) {
    return (
        value.days * 24 * 60 * 60 * 1000 +
        value.hours * 60 * 60 * 1000 +
        value.minutes * 60 * 1000 +
        value.seconds * 1000
    );
}

console.log(
    "Duration milliseconds:",
    durationToMilliseconds(duration)
);


// -----------------------------------------------------------------------------
// 9. DATE FORMATTING
// -----------------------------------------------------------------------------

console.log("\n9. FORMATTING");

const formattingDate = new Date("2026-09-21T14:35:42Z");

console.log("ISO:", formattingDate.toISOString());
console.log("UTC string:", formattingDate.toUTCString());
console.log("Local string:", formattingDate.toString());

const formatter = new Intl.DateTimeFormat("en-IN", {
    dateStyle: "full",
    timeStyle: "long",
    timeZone: "Asia/Kolkata"
});

console.log(
    "India formatting:",
    formatter.format(formattingDate)
);


// -----------------------------------------------------------------------------
// 10. INTERNATIONALIZED TIME ZONES
// -----------------------------------------------------------------------------

console.log("\n10. TIME ZONES");

const zones = [
    "UTC",
    "Asia/Kolkata",
    "Europe/London",
    "America/New_York",
    "Asia/Tokyo"
];

for (const zone of zones) {
    const zoneFormatter = new Intl.DateTimeFormat("en-IN", {
        dateStyle: "medium",
        timeStyle: "long",
        timeZone: zone
    });

    console.log(`${zone}: ${zoneFormatter.format(formattingDate)}`);
}


// -----------------------------------------------------------------------------
// 11. ISO 8601 PARSING
// -----------------------------------------------------------------------------

console.log("\n11. ISO 8601 PARSING");

const isoInput = "2026-09-21T14:35:42+05:30";
const parsedIsoDate = new Date(isoInput);

console.log("Input:", isoInput);
console.log("Parsed:", parsedIsoDate.toISOString());


// -----------------------------------------------------------------------------
// 12. VALID DATE PARSING
// -----------------------------------------------------------------------------

console.log("\n12. VALIDATION");

function parseDateSafely(value) {
    const parsed = new Date(value);

    if (Number.isNaN(parsed.getTime())) {
        return null;
    }

    return parsed;
}

for (const value of [
    "2026-09-21",
    "not-a-date",
    "2026-02-30"
]) {
    const result = parseDateSafely(value);
    console.log(value, "->", result);
}


// -----------------------------------------------------------------------------
// 13. DAYS IN MONTH
// -----------------------------------------------------------------------------

console.log("\n13. DAYS IN MONTH");

function daysInMonth(year, month) {
    // month is one-based in this helper.
    return new Date(
        Date.UTC(year, month, 0)
    ).getUTCDate();
}

for (let month = 1; month <= 12; month++) {
    console.log(
        `2026-${String(month).padStart(2, "0")}:`,
        daysInMonth(2026, month)
    );
}


// -----------------------------------------------------------------------------
// 14. LEAP YEAR
// -----------------------------------------------------------------------------

console.log("\n14. LEAP YEARS");

function isLeapYear(year) {
    return (
        year % 4 === 0 &&
        (year % 100 !== 0 || year % 400 === 0)
    );
}

for (const year of [2024, 2025, 2100, 2000]) {
    console.log(year, "->", isLeapYear(year));
}


// -----------------------------------------------------------------------------
// 15. START AND END OF MONTH
// -----------------------------------------------------------------------------

console.log("\n15. MONTH BOUNDARIES");

function startOfMonth(date) {
    return new Date(Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth(),
        1
    ));
}

function endOfMonth(date) {
    return new Date(Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth() + 1,
        0,
        23,
        59,
        59,
        999
    ));
}

const monthSample = new Date("2026-09-21T12:00:00Z");

console.log(
    "Start:",
    startOfMonth(monthSample).toISOString()
);

console.log(
    "End:",
    endOfMonth(monthSample).toISOString()
);


// -----------------------------------------------------------------------------
// 16. ADDING MONTHS
// -----------------------------------------------------------------------------

console.log("\n16. MONTH ARITHMETIC");

function addMonths(date, numberOfMonths) {
    const originalDay = date.getUTCDate();

    const result = new Date(Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth() + numberOfMonths,
        1,
        date.getUTCHours(),
        date.getUTCMinutes(),
        date.getUTCSeconds(),
        date.getUTCMilliseconds()
    ));

    const lastDay = daysInMonth(
        result.getUTCFullYear(),
        result.getUTCMonth() + 1
    );

    result.setUTCDate(
        Math.min(originalDay, lastDay)
    );

    return result;
}

console.log(
    "2026-01-31 + 1 month:",
    addMonths(
        new Date("2026-01-31T00:00:00Z"),
        1
    ).toISOString()
);

console.log(
    "2024-01-31 + 1 month:",
    addMonths(
        new Date("2024-01-31T00:00:00Z"),
        1
    ).toISOString()
);


// -----------------------------------------------------------------------------
// 17. ADDING YEARS
// -----------------------------------------------------------------------------

console.log("\n17. YEAR ARITHMETIC");

function addYears(date, numberOfYears) {
    const result = new Date(date.getTime());
    const originalMonth = result.getUTCMonth();
    const originalDay = result.getUTCDate();

    result.setUTCDate(1);
    result.setUTCFullYear(
        result.getUTCFullYear() + numberOfYears
    );
    result.setUTCMonth(originalMonth);

    const lastDay = daysInMonth(
        result.getUTCFullYear(),
        originalMonth + 1
    );

    result.setUTCDate(
        Math.min(originalDay, lastDay)
    );

    return result;
}

console.log(
    "Leap-day example:",
    addYears(
        new Date("2024-02-29T00:00:00Z"),
        1
    ).toISOString()
);


// -----------------------------------------------------------------------------
// 18. BUSINESS DAYS
// -----------------------------------------------------------------------------

console.log("\n18. BUSINESS DAYS");

function isBusinessDay(date) {
    const day = date.getUTCDay();
    return day >= 1 && day <= 5;
}

function addBusinessDays(startDate, numberOfDays, holidays = []) {
    const holidaySet = new Set(
        holidays.map(value => value.toISOString().slice(0, 10))
    );

    const result = new Date(startDate.getTime());
    const step = numberOfDays >= 0 ? 1 : -1;
    let remaining = Math.abs(numberOfDays);

    while (remaining > 0) {
        result.setUTCDate(
            result.getUTCDate() + step
        );

        const key = result.toISOString().slice(0, 10);

        if (
            isBusinessDay(result) &&
            !holidaySet.has(key)
        ) {
            remaining--;
        }
    }

    return result;
}

const holiday = new Date("2026-09-25T00:00:00Z");

console.log(
    "5 business days later:",
    addBusinessDays(
        new Date("2026-09-21T00:00:00Z"),
        5,
        [holiday]
    ).toISOString()
);


// -----------------------------------------------------------------------------
// 19. DATE RANGE
// -----------------------------------------------------------------------------

console.log("\n19. DATE RANGE");

function dateRange(startDate, endDate, stepDays = 1) {
    if (stepDays === 0) {
        throw new Error("Step cannot be zero.");
    }

    const result = [];
    const current = new Date(startDate.getTime());

    if (stepDays > 0) {
        while (current <= endDate) {
            result.push(new Date(current.getTime()));
            current.setUTCDate(
                current.getUTCDate() + stepDays
            );
        }
    } else {
        while (current >= endDate) {
            result.push(new Date(current.getTime()));
            current.setUTCDate(
                current.getUTCDate() + stepDays
            );
        }
    }

    return result;
}

for (const date of dateRange(
    new Date("2026-09-21T00:00:00Z"),
    new Date("2026-09-25T00:00:00Z")
)) {
    console.log(date.toISOString());
}


// -----------------------------------------------------------------------------
// 20. WEEKLY RECURRENCE
// -----------------------------------------------------------------------------

console.log("\n20. RECURRING EVENTS");

function weeklyEvents(firstEvent, count) {
    return Array.from(
        { length: count },
        (_, index) => addDays(firstEvent, index * 7)
    );
}

for (const eventDate of weeklyEvents(
    new Date("2026-09-21T09:00:00Z"),
    5
)) {
    console.log(eventDate.toISOString());
}


// -----------------------------------------------------------------------------
// 21. AGE CALCULATION
// -----------------------------------------------------------------------------

console.log("\n21. AGE CALCULATION");

function calculateAge(birthDate, referenceDate = new Date()) {
    let age =
        referenceDate.getUTCFullYear() -
        birthDate.getUTCFullYear();

    const birthdayThisYear = new Date(Date.UTC(
        referenceDate.getUTCFullYear(),
        birthDate.getUTCMonth(),
        birthDate.getUTCDate()
    ));

    if (referenceDate < birthdayThisYear) {
        age--;
    }

    return age;
}

console.log(
    "Age:",
    calculateAge(
        new Date("1995-05-10T00:00:00Z"),
        new Date("2026-09-21T00:00:00Z")
    )
);


// -----------------------------------------------------------------------------
// 22. INTERVAL CLASS
// -----------------------------------------------------------------------------

console.log("\n22. INTERVALS");

class DateInterval {
    constructor(start, end) {
        if (start > end) {
            throw new Error(
                "Interval start cannot be after interval end."
            );
        }

        this.start = new Date(start.getTime());
        this.end = new Date(end.getTime());
    }

    durationMilliseconds() {
        return this.end.getTime() - this.start.getTime();
    }

    contains(value) {
        return (
            value >= this.start &&
            value <= this.end
        );
    }

    overlaps(other) {
        return (
            this.start <= other.end &&
            other.start <= this.end
        );
    }
}

const intervalA = new DateInterval(
    new Date("2026-09-21T09:00:00Z"),
    new Date("2026-09-21T12:00:00Z")
);

const intervalB = new DateInterval(
    new Date("2026-09-21T11:00:00Z"),
    new Date("2026-09-21T15:00:00Z")
);

console.log(
    "Duration:",
    intervalA.durationMilliseconds()
);

console.log(
    "Contains 10:00:",
    intervalA.contains(
        new Date("2026-09-21T10:00:00Z")
    )
);

console.log(
    "Overlap:",
    intervalA.overlaps(intervalB)
);


// -----------------------------------------------------------------------------
// 23. INTERVAL INTERSECTION
// -----------------------------------------------------------------------------

console.log("\n23. INTERVAL INTERSECTION");

function intersection(first, second) {
    const start = new Date(
        Math.max(
            first.start.getTime(),
            second.start.getTime()
        )
    );

    const end = new Date(
        Math.min(
            first.end.getTime(),
            second.end.getTime()
        )
    );

    if (start > end) {
        return null;
    }

    return new DateInterval(start, end);
}

const overlap = intersection(intervalA, intervalB);

console.log(
    overlap
        ? {
            start: overlap.start.toISOString(),
            end: overlap.end.toISOString()
        }
        : null
);


// -----------------------------------------------------------------------------
// 24. INTERVAL MERGING
// -----------------------------------------------------------------------------

console.log("\n24. INTERVAL MERGING");

function mergeIntervals(intervals) {
    if (intervals.length === 0) {
        return [];
    }

    const sorted = [...intervals].sort(
        (a, b) => a.start - b.start
    );

    const merged = [
        new DateInterval(
            sorted[0].start,
            sorted[0].end
        )
    ];

    for (const current of sorted.slice(1)) {
        const previous = merged[merged.length - 1];

        if (current.start <= previous.end) {
            previous.end = new Date(
                Math.max(
                    previous.end.getTime(),
                    current.end.getTime()
                )
            );
        } else {
            merged.push(
                new DateInterval(
                    current.start,
                    current.end
                )
            );
        }
    }

    return merged;
}

const mergedIntervals = mergeIntervals([
    new DateInterval(
        new Date("2026-09-21T09:00:00Z"),
        new Date("2026-09-21T11:00:00Z")
    ),
    new DateInterval(
        new Date("2026-09-21T10:30:00Z"),
        new Date("2026-09-21T13:00:00Z")
    ),
    new DateInterval(
        new Date("2026-09-21T15:00:00Z"),
        new Date("2026-09-21T16:00:00Z")
    )
]);

for (const interval of mergedIntervals) {
    console.log(
        interval.start.toISOString(),
        "->",
        interval.end.toISOString()
    );
}


// -----------------------------------------------------------------------------
// 25. SCHEDULING
// -----------------------------------------------------------------------------

console.log("\n25. SCHEDULING");

class Meeting {
    constructor(title, start, durationMilliseconds) {
        if (durationMilliseconds < 0) {
            throw new Error(
                "Duration cannot be negative."
            );
        }

        this.title = title;
        this.start = new Date(start.getTime());
        this.durationMilliseconds = durationMilliseconds;
    }

    get end() {
        return new Date(
            this.start.getTime() +
            this.durationMilliseconds
        );
    }

    overlaps(other) {
        return (
            this.start < other.end &&
            other.start < this.end
        );
    }
}

const meetings = [
    new Meeting(
        "Architecture Review",
        new Date("2026-09-21T09:00:00Z"),
        60 * 60 * 1000
    ),
    new Meeting(
        "Implementation",
        new Date("2026-09-21T10:30:00Z"),
        2 * 60 * 60 * 1000
    ),
    new Meeting(
        "Deployment",
        new Date("2026-09-21T13:00:00Z"),
        45 * 60 * 1000
    )
];

for (const meeting of meetings) {
    console.log(
        meeting.title,
        meeting.start.toISOString(),
        "->",
        meeting.end.toISOString()
    );
}

for (let i = 0; i < meetings.length; i++) {
    for (let j = i + 1; j < meetings.length; j++) {
        console.log(
            meetings[i].title,
            "/",
            meetings[j].title,
            "conflict:",
            meetings[i].overlaps(meetings[j])
        );
    }
}


// -----------------------------------------------------------------------------
// 26. DEADLINE CHECK
// -----------------------------------------------------------------------------

console.log("\n26. DEADLINES");

function deadlineStatus(deadline, current) {
    const difference =
        deadline.getTime() - current.getTime();

    if (difference > 0) {
        return `OPEN: ${difference} ms remaining`;
    }

    if (difference === 0) {
        return "DUE NOW";
    }

    return `OVERDUE: ${Math.abs(difference)} ms`;
}

console.log(
    deadlineStatus(
        new Date("2026-09-22T17:00:00Z"),
        new Date("2026-09-21T17:00:00Z")
    )
);


// -----------------------------------------------------------------------------
// 27. EXPIRATION
// -----------------------------------------------------------------------------

console.log("\n27. EXPIRATION");

function isExpired(createdAt, lifetimeMilliseconds, currentTime) {
    return (
        currentTime.getTime() >=
        createdAt.getTime() + lifetimeMilliseconds
    );
}

console.log(
    isExpired(
        new Date("2026-09-21T10:00:00Z"),
        2 * 60 * 60 * 1000,
        new Date("2026-09-21T12:01:00Z")
    )
);


// -----------------------------------------------------------------------------
// 28. SLIDING TIME WINDOW
// -----------------------------------------------------------------------------

console.log("\n28. SLIDING WINDOW");

function isWithinWindow(
    candidate,
    reference,
    windowMilliseconds
) {
    const difference =
        reference.getTime() -
        candidate.getTime();

    return (
        difference >= 0 &&
        difference <= windowMilliseconds
    );
}

console.log(
    isWithinWindow(
        new Date("2026-09-21T11:40:00Z"),
        new Date("2026-09-21T12:00:00Z"),
        30 * 60 * 1000
    )
);


// -----------------------------------------------------------------------------
// 29. FLOOR TO MINUTE
// -----------------------------------------------------------------------------

console.log("\n29. ROUNDING");

function floorToMinute(date) {
    const result = new Date(date.getTime());

    result.setUTCSeconds(0, 0);

    return result;
}

function ceilToMinute(date) {
    const floor = floorToMinute(date);

    if (floor.getTime() === date.getTime()) {
        return floor;
    }

    return new Date(
        floor.getTime() + 60 * 1000
    );
}

const preciseDate = new Date(
    "2026-09-21T12:30:45.123Z"
);

console.log(
    "Original:",
    preciseDate.toISOString()
);

console.log(
    "Floor:",
    floorToMinute(preciseDate).toISOString()
);

console.log(
    "Ceil:",
    ceilToMinute(preciseDate).toISOString()
);


// -----------------------------------------------------------------------------
// 30. PERFORMANCE TIMING
// -----------------------------------------------------------------------------

console.log("\n30. PERFORMANCE TIMING");

const performanceStart = performance.now();

let total = 0;

for (let i = 1; i <= 1_000_000; i++) {
    total += i;
}

const performanceEnd = performance.now();

console.log("Total:", total);
console.log(
    "Elapsed milliseconds:",
    performanceEnd - performanceStart
);

/*
performance.now() is designed for measuring elapsed execution time.

Date.now() represents wall-clock time and is not the preferred tool
for precise performance measurements.
*/


// -----------------------------------------------------------------------------
// 31. DATE-ONLY VALIDATION
// -----------------------------------------------------------------------------

console.log("\n31. DATE-ONLY VALIDATION");

function isValidISODate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        return false;
    }

    const [year, month, day] =
        value.split("-").map(Number);

    if (month < 1 || month > 12) {
        return false;
    }

    const maximumDay = daysInMonth(year, month);

    return day >= 1 && day <= maximumDay;
}

for (const value of [
    "2026-09-21",
    "2026-02-30",
    "2026-13-01",
    "hello"
]) {
    console.log(
        value,
        "->",
        isValidISODate(value)
    );
}


// -----------------------------------------------------------------------------
// 32. DATE RANGE OVERLAP
// -----------------------------------------------------------------------------

console.log("\n32. DATE RANGE OVERLAP");

function dateRangesOverlap(
    firstStart,
    firstEnd,
    secondStart,
    secondEnd
) {
    if (firstStart > firstEnd || secondStart > secondEnd) {
        throw new Error("Invalid date range.");
    }

    return (
        firstStart <= secondEnd &&
        secondStart <= firstEnd
    );
}

console.log(
    dateRangesOverlap(
        new Date("2026-09-01T00:00:00Z"),
        new Date("2026-09-10T00:00:00Z"),
        new Date("2026-09-10T00:00:00Z"),
        new Date("2026-09-20T00:00:00Z")
    )
);


// -----------------------------------------------------------------------------
// 33. ISO SERIALIZATION
// -----------------------------------------------------------------------------

console.log("\n33. SERIALIZATION");

const serializedEventTime = new Date().toISOString();

const serializedRecord = JSON.stringify({
    id: 1001,
    event: "System maintenance",
    occurredAt: serializedEventTime
});

console.log(serializedRecord);

const restoredRecord = JSON.parse(serializedRecord);

console.log(
    "Restored event time:",
    new Date(restoredRecord.occurredAt).toISOString()
);


// -----------------------------------------------------------------------------
// 34. COMMON JAVASCRIPT DATE PITFALLS
// -----------------------------------------------------------------------------

console.log("\n34. COMMON PITFALLS");

console.log(
    "JavaScript Date stores an instant as milliseconds from the Unix epoch."
);

console.log(
    "getMonth() is zero-based."
);

console.log(
    "toISOString() represents the instant in UTC."
);

console.log(
    "Local getters and UTC getters have different meanings."
);

console.log(
    "Parsing ambiguous date strings can produce unexpected results."
);

console.log(
    "Date has no dedicated date-only or time-only type."
);

console.log(
    "Calendar months are not fixed durations."
);


// -----------------------------------------------------------------------------
// 35. PRODUCTION EVENT MODEL
// -----------------------------------------------------------------------------

console.log("\n35. PRODUCTION EVENT MODEL");

class EventRecord {
    constructor({
        id,
        name,
        startsAt,
        endsAt
    }) {
        if (!(startsAt instanceof Date)) {
            throw new TypeError(
                "startsAt must be a Date."
            );
        }

        if (!(endsAt instanceof Date)) {
            throw new TypeError(
                "endsAt must be a Date."
            );
        }

        if (startsAt > endsAt) {
            throw new RangeError(
                "startsAt cannot be after endsAt."
            );
        }

        this.id = id;
        this.name = name;
        this.startsAt = new Date(startsAt.getTime());
        this.endsAt = new Date(endsAt.getTime());
    }

    get durationMilliseconds() {
        return (
            this.endsAt.getTime() -
            this.startsAt.getTime()
        );
    }

    toJSON() {
        return {
            id: this.id,
            name: this.name,
            startsAt: this.startsAt.toISOString(),
            endsAt: this.endsAt.toISOString()
        };
    }
}

const eventRecord = new EventRecord({
    id: 5001,
    name: "Database maintenance",
    startsAt: new Date("2026-09-25T18:00:00Z"),
    endsAt: new Date("2026-09-25T20:30:00Z")
});

console.log(eventRecord);
console.log(
    "Duration:",
    eventRecord.durationMilliseconds
);

console.log(
    "JSON:",
    JSON.stringify(eventRecord)
);


// -----------------------------------------------------------------------------
// 36. FINAL CHECKLIST
// -----------------------------------------------------------------------------

console.log("\n36. FINAL CHECKLIST");

const checks = {
    dateObject: now instanceof Date,
    timestamp: Number.isFinite(now.getTime()),
    isoSerialization: typeof now.toISOString() === "string",
    duration: durationToMilliseconds(duration) > 0,
    interval: intervalA.start <= intervalA.end,
    businessDayFunction: typeof isBusinessDay === "function",
    monthArithmetic: typeof addMonths === "function",
    timezoneFormatting: typeof Intl.DateTimeFormat === "function"
};

for (const [name, result] of Object.entries(checks)) {
    console.log(
        `${name}: ${result ? "PASS" : "FAIL"}`
    );
}

console.log(
    "\nDate, time, timestamp, interval, and date-arithmetic study complete."
);
