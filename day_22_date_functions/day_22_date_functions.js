/*
 * PostgreSQL Date Functions:
 * EXTRACT, DATE_PART, DATE_TRUNC, AGE, CURRENT_DATE
 *
 * This JavaScript file complements the Python implementation.
 *
 * It demonstrates:
 *   - JavaScript Date fundamentals
 *   - PostgreSQL date-function syntax generation
 *   - EXTRACT and DATE_PART
 *   - DATE_TRUNC concepts
 *   - AGE concepts
 *   - CURRENT_DATE
 *   - ISO week behavior
 *   - calendar arithmetic
 *   - date validation
 *   - time-zone handling
 *   - query generation
 *   - safe identifier validation
 *   - analytical reporting
 *   - asynchronous database-style processing
 *
 * No external npm package is required.
 *
 * Run with:
 *   node date_functions.js
 *
 * The PostgreSQL statements printed by this program are intended for a
 * PostgreSQL database. The JavaScript calculations provide executable
 * demonstrations without requiring a database connection.
 */

"use strict";


// ============================================================================
// 1. BASIC DATE VALUES
// ============================================================================

console.log("=".repeat(80));
console.log("POSTGRESQL DATE FUNCTIONS - JAVASCRIPT STUDY PROGRAM");
console.log("=".repeat(80));

const referenceDate = new Date("2026-09-22T14:35:48Z");

console.log("\nReference timestamp:");
console.log(referenceDate.toISOString());


// ============================================================================
// 2. JAVASCRIPT DATE COMPONENTS
// ============================================================================

function extractJavaScriptComponent(value, field) {
    const date = value instanceof Date ? value : new Date(value);

    if (Number.isNaN(date.getTime())) {
        throw new Error("Invalid date");
    }

    switch (field.toLowerCase()) {
        case "year":
            return date.getUTCFullYear();

        case "month":
            // JavaScript months are zero-based.
            // PostgreSQL months are one-based.
            return date.getUTCMonth() + 1;

        case "day":
            return date.getUTCDate();

        case "hour":
            return date.getUTCHours();

        case "minute":
            return date.getUTCMinutes();

        case "second":
            return date.getUTCSeconds();

        case "quarter":
            return Math.floor(date.getUTCMonth() / 3) + 1;

        case "doy": {
            const startOfYear = Date.UTC(
                date.getUTCFullYear(),
                0,
                1
            );

            const currentDay = Date.UTC(
                date.getUTCFullYear(),
                date.getUTCMonth(),
                date.getUTCDate()
            );

            return Math.floor(
                (currentDay - startOfYear) / 86400000
            ) + 1;
        }

        default:
            throw new Error(`Unsupported field: ${field}`);
    }
}

console.log("\nEXTRACT CONCEPT");

for (const field of [
    "year",
    "month",
    "day",
    "hour",
    "minute",
    "second",
    "quarter",
    "doy"
]) {
    console.log(
        `${field.padEnd(10)} -> ${extractJavaScriptComponent(
            referenceDate,
            field
        )}`
    );
}


// ============================================================================
// 3. POSTGRESQL EXTRACT QUERY GENERATION
// ============================================================================

function postgresExtract(field, expression) {
    const allowedFields = new Set([
        "YEAR",
        "MONTH",
        "DAY",
        "QUARTER",
        "WEEK",
        "ISOYEAR",
        "ISODOW",
        "DOW",
        "DOY",
        "HOUR",
        "MINUTE",
        "SECOND",
        "EPOCH"
    ]);

    const normalizedField = field.toUpperCase();

    if (!allowedFields.has(normalizedField)) {
        throw new Error(`Unsupported PostgreSQL EXTRACT field: ${field}`);
    }

    return `EXTRACT(${normalizedField} FROM ${expression})`;
}

console.log("\nPOSTGRESQL EXTRACT QUERIES");

console.log(
    postgresExtract(
        "year",
        "DATE '2026-09-22'"
    )
);

console.log(
    postgresExtract(
        "month",
        "DATE '2026-09-22'"
    )
);

console.log(
    postgresExtract(
        "quarter",
        "DATE '2026-09-22'"
    )
);

console.log(
    postgresExtract(
        "hour",
        "TIMESTAMP '2026-09-22 14:35:48'"
    )
);


// ============================================================================
// 4. DATE_PART
// ============================================================================

function postgresDatePart(field, expression) {
    const allowedFields = new Set([
        "year",
        "month",
        "day",
        "quarter",
        "week",
        "isoyear",
        "isodow",
        "dow",
        "doy",
        "hour",
        "minute",
        "second",
        "epoch"
    ]);

    const normalizedField = field.toLowerCase();

    if (!allowedFields.has(normalizedField)) {
        throw new Error(`Unsupported DATE_PART field: ${field}`);
    }

    return `DATE_PART('${normalizedField}', ${expression})`;
}

console.log("\nDATE_PART QUERIES");

for (const field of [
    "year",
    "month",
    "day",
    "quarter",
    "week",
    "isoyear"
]) {
    console.log(
        postgresDatePart(
            field,
            "CURRENT_DATE"
        )
    );
}


// ============================================================================
// 5. EXTRACT VS DATE_PART
// ============================================================================

console.log("\nEXTRACT VS DATE_PART");

console.log(
    postgresExtract("year", "order_date")
);

console.log(
    postgresDatePart("year", "order_date")
);

console.log(`
Both forms communicate the same conceptual operation:

EXTRACT(YEAR FROM order_date)
DATE_PART('year', order_date)

EXTRACT uses SQL-style field syntax.

DATE_PART uses a string field name followed by the source expression.
`);


// ============================================================================
// 6. DATE_TRUNC
// ============================================================================

const dateTruncPrecisions = [
    "year",
    "quarter",
    "month",
    "week",
    "day",
    "hour",
    "minute",
    "second"
];

function postgresDateTrunc(precision, expression) {
    const allowed = new Set(dateTruncPrecisions);

    if (!allowed.has(precision)) {
        throw new Error(
            `Unsupported DATE_TRUNC precision: ${precision}`
        );
    }

    return `DATE_TRUNC('${precision}', ${expression})`;
}

console.log("\nDATE_TRUNC QUERIES");

for (const precision of dateTruncPrecisions) {
    console.log(
        postgresDateTrunc(
            precision,
            "order_timestamp"
        )
    );
}


// ============================================================================
// 7. JAVASCRIPT DATE TRUNCATION
// ============================================================================

function startOfMonth(date) {
    return new Date(
        Date.UTC(
            date.getUTCFullYear(),
            date.getUTCMonth(),
            1
        )
    );
}

function startOfQuarter(date) {
    const month = date.getUTCMonth();
    const quarterStartMonth = Math.floor(month / 3) * 3;

    return new Date(
        Date.UTC(
            date.getUTCFullYear(),
            quarterStartMonth,
            1
        )
    );
}

function startOfYear(date) {
    return new Date(
        Date.UTC(
            date.getUTCFullYear(),
            0,
            1
        )
    );
}

function startOfDay(date) {
    return new Date(
        Date.UTC(
            date.getUTCFullYear(),
            date.getUTCMonth(),
            date.getUTCDate()
        )
    );
}

function startOfHour(date) {
    return new Date(
        Date.UTC(
            date.getUTCFullYear(),
            date.getUTCMonth(),
            date.getUTCDate(),
            date.getUTCHours()
        )
    );
}

function startOfMinute(date) {
    return new Date(
        Date.UTC(
            date.getUTCFullYear(),
            date.getUTCMonth(),
            date.getUTCDate(),
            date.getUTCHours(),
            date.getUTCMinutes()
        )
    );
}

function startOfSecond(date) {
    return new Date(
        Date.UTC(
            date.getUTCFullYear(),
            date.getUTCMonth(),
            date.getUTCDate(),
            date.getUTCHours(),
            date.getUTCMinutes(),
            date.getUTCSeconds()
        )
    );
}

function startOfWeekMonday(date) {
    const day = date.getUTCDay();

    // JavaScript:
    // Sunday = 0, Monday = 1, ..., Saturday = 6.
    const daysSinceMonday = (day + 6) % 7;

    const result = new Date(date);

    result.setUTCDate(
        result.getUTCDate() - daysSinceMonday
    );

    return startOfDay(result);
}

console.log("\nJAVASCRIPT DATE_TRUNC EQUIVALENTS");

console.log(
    "year:",
    startOfYear(referenceDate).toISOString()
);

console.log(
    "quarter:",
    startOfQuarter(referenceDate).toISOString()
);

console.log(
    "month:",
    startOfMonth(referenceDate).toISOString()
);

console.log(
    "week:",
    startOfWeekMonday(referenceDate).toISOString()
);

console.log(
    "day:",
    startOfDay(referenceDate).toISOString()
);

console.log(
    "hour:",
    startOfHour(referenceDate).toISOString()
);

console.log(
    "minute:",
    startOfMinute(referenceDate).toISOString()
);

console.log(
    "second:",
    startOfSecond(referenceDate).toISOString()
);


// ============================================================================
// 8. CURRENT_DATE
// ============================================================================

function currentDateUTC() {
    const now = new Date();

    return new Date(
        Date.UTC(
            now.getUTCFullYear(),
            now.getUTCMonth(),
            now.getUTCDate()
        )
    );
}

const javascriptCurrentDate = currentDateUTC();

console.log("\nCURRENT_DATE CONCEPT");

console.log(
    "JavaScript current date:",
    javascriptCurrentDate.toISOString().slice(0, 10)
);

console.log(
    "PostgreSQL:",
    "SELECT CURRENT_DATE;"
);

console.log(
    "PostgreSQL current timestamp:",
    "SELECT CURRENT_TIMESTAMP;"
);


// ============================================================================
// 9. IMPORTANT TRANSACTION-TIME DISTINCTION
// ============================================================================

console.log("\nCURRENT_DATE TRANSACTION SEMANTICS");

console.log(`
PostgreSQL CURRENT_DATE represents the current date associated with the
current transaction-time context.

The application clock and database clock are separate concepts.

For database-owned business rules, examples such as:

    WHERE birth_date <= CURRENT_DATE

let PostgreSQL evaluate the current date itself.

For deterministic tests, an explicit date is often preferable:

    AGE(DATE '2026-09-22', birth_date)
`);


// ============================================================================
// 10. CALENDAR AGE
// ============================================================================

function daysInMonth(year, monthOneBased) {
    return new Date(
        Date.UTC(
            year,
            monthOneBased,
            0
        )
    ).getUTCDate();
}

function calendarAge(laterInput, earlierInput) {
    const later = laterInput instanceof Date
        ? new Date(laterInput)
        : new Date(laterInput);

    const earlier = earlierInput instanceof Date
        ? new Date(earlierInput)
        : new Date(earlierInput);

    if (
        Number.isNaN(later.getTime()) ||
        Number.isNaN(earlier.getTime())
    ) {
        throw new Error("Invalid date supplied to calendarAge");
    }

    if (later < earlier) {
        return {
            years: 0,
            months: 0,
            days: 0,
            negative: true
        };
    }

    let years =
        later.getUTCFullYear() -
        earlier.getUTCFullYear();

    let months =
        later.getUTCMonth() -
        earlier.getUTCMonth();

    let days =
        later.getUTCDate() -
        earlier.getUTCDate();

    if (days < 0) {
        months -= 1;

        const previousMonth =
            later.getUTCMonth() === 0
                ? 12
                : later.getUTCMonth();

        const previousYear =
            later.getUTCMonth() === 0
                ? later.getUTCFullYear() - 1
                : later.getUTCFullYear();

        days += daysInMonth(
            previousYear,
            previousMonth
        );
    }

    if (months < 0) {
        years -= 1;
        months += 12;
    }

    return {
        years,
        months,
        days,
        negative: false
    };
}

function formatAge(age) {
    if (age.negative) {
        return "negative calendar interval";
    }

    return (
        `${age.years} years, ` +
        `${age.months} months, ` +
        `${age.days} days`
    );
}

const birthDate = new Date(
    "1995-04-18T00:00:00Z"
);

const age = calendarAge(
    new Date("2026-09-22T00:00:00Z"),
    birthDate
);

console.log("\nAGE");
console.log("Birth date:", birthDate.toISOString());
console.log("Age:", formatAge(age));

console.log(
    "PostgreSQL:",
    "SELECT AGE(CURRENT_DATE, birth_date) FROM employees;"
);


// ============================================================================
// 11. AGE VS ELAPSED DAYS
// ============================================================================

function elapsedDays(laterInput, earlierInput) {
    const later = new Date(laterInput);
    const earlier = new Date(earlierInput);

    return Math.floor(
        (later.getTime() - earlier.getTime()) /
        86400000
    );
}

const leapExampleStart =
    new Date("2020-02-29T00:00:00Z");

const leapExampleEnd =
    new Date("2026-02-28T00:00:00Z");

console.log("\nAGE VS ELAPSED DAYS");

console.log(
    "Elapsed days:",
    elapsedDays(
        leapExampleEnd,
        leapExampleStart
    )
);

console.log(
    "Calendar age:",
    formatAge(
        calendarAge(
            leapExampleEnd,
            leapExampleStart
        )
    )
);

console.log(`
A day difference and AGE answer different questions.

Elapsed days:
    How many 24-hour date units separate two timestamps?

AGE:
    What calendar interval separates two timestamps?

A business application should select the representation according to the
question being answered.
`);


// ============================================================================
// 12. ISO WEEK EDGE CASE
// ============================================================================

console.log("\nISO WEEK EDGE CASE");

const isoDates = [
    "2020-12-28",
    "2020-12-31",
    "2021-01-01",
    "2021-01-04"
];

function isoWeekInfo(input) {
    const date = new Date(`${input}T00:00:00Z`);

    // ISO week algorithm:
    // Shift to Thursday because ISO week-years are defined around Thursday.
    const day = date.getUTCDay() || 7;

    const thursday = new Date(date);

    thursday.setUTCDate(
        date.getUTCDate() + 4 - day
    );

    const isoYear =
        thursday.getUTCFullYear();

    const yearStart = new Date(
        Date.UTC(isoYear, 0, 1)
    );

    const weekNumber =
        Math.ceil(
            (
                (
                    thursday.getTime() -
                    yearStart.getTime()
                ) / 86400000 + 1
            ) / 7
        );

    return {
        isoYear,
        weekNumber
    };
}

for (const input of isoDates) {
    console.log(
        input,
        isoWeekInfo(input)
    );
}

console.log(`
PostgreSQL:

EXTRACT(WEEK FROM event_date)
EXTRACT(ISOYEAR FROM event_date)

should be considered together when ISO-week reporting is required.
`);


// ============================================================================
// 13. EMPLOYEE MODEL
// ============================================================================

class Employee {
    constructor(
        id,
        name,
        birthDate,
        joinedDate,
        department
    ) {
        this.id = id;
        this.name = name;
        this.birthDate = new Date(
            `${birthDate}T00:00:00Z`
        );
        this.joinedDate = new Date(
            `${joinedDate}T00:00:00Z`
        );
        this.department = department;
    }

    ageAsOf(reference) {
        return calendarAge(
            reference,
            this.birthDate
        );
    }

    tenureAsOf(reference) {
        return calendarAge(
            reference,
            this.joinedDate
        );
    }

    report(reference) {
        if (this.birthDate > reference) {
            throw new Error(
                `${this.name} has an invalid future birth date`
            );
        }

        if (this.joinedDate > reference) {
            throw new Error(
                `${this.name} has an invalid future joining date`
            );
        }

        return {
            employeeId: this.id,
            name: this.name,
            department: this.department,
            birthYear:
                this.birthDate.getUTCFullYear(),
            birthMonth:
                this.birthDate.getUTCMonth() + 1,
            age:
                this.ageAsOf(reference),
            tenure:
                this.tenureAsOf(reference),
            joiningMonth:
                startOfMonth(
                    this.joinedDate
                )
        };
    }
}

const employees = [
    new Employee(
        101,
        "Asha",
        "1990-05-17",
        "2017-06-12",
        "Engineering"
    ),
    new Employee(
        102,
        "Ravi",
        "1987-11-03",
        "2015-02-09",
        "Finance"
    ),
    new Employee(
        103,
        "Meera",
        "1998-01-28",
        "2022-08-22",
        "Engineering"
    ),
    new Employee(
        104,
        "Kabir",
        "1995-12-31",
        "2020-01-06",
        "Operations"
    )
];

const reportDate =
    new Date("2026-09-22T00:00:00Z");

console.log("\nEMPLOYEE REPORT");

for (const employee of employees) {
    console.log(
        employee.report(reportDate)
    );
}


// ============================================================================
// 14. CORRESPONDING POSTGRESQL EMPLOYEE QUERY
// ============================================================================

console.log("\nPOSTGRESQL EMPLOYEE QUERY");

console.log(`
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
`);


// ============================================================================
// 15. QUERY IDENTIFIER VALIDATION
// ============================================================================

const identifierPattern =
    /^[A-Za-z_][A-Za-z0-9_]*$/;

function validateIdentifier(identifier) {
    if (!identifierPattern.test(identifier)) {
        throw new Error(
            `Invalid SQL identifier: ${identifier}`
        );
    }

    return identifier;
}

function monthlyReportQuery(
    tableName,
    timestampColumn
) {
    validateIdentifier(tableName);
    validateIdentifier(timestampColumn);

    return `
SELECT
    DATE_TRUNC(
        'month',
        ${timestampColumn}
    ) AS month_start,
    COUNT(*) AS row_count
FROM ${tableName}
GROUP BY DATE_TRUNC(
    'month',
    ${timestampColumn}
)
ORDER BY month_start;
`.trim();
}

console.log("\nSAFE QUERY GENERATION");

console.log(
    monthlyReportQuery(
        "orders",
        "created_at"
    )
);

try {
    monthlyReportQuery(
        "orders; DROP TABLE users;",
        "created_at"
    );
} catch (error) {
    console.log(
        "Rejected unsafe identifier:",
        error.message
    );
}


// ============================================================================
// 16. HALF-OPEN DATE RANGES
// ============================================================================

function nextDay(date) {
    const result = new Date(date);

    result.setUTCDate(
        result.getUTCDate() + 1
    );

    return result;
}

function dayRangeQuery(
    timestampColumn,
    startDate
) {
    validateIdentifier(timestampColumn);

    const start =
        startOfDay(
            new Date(`${startDate}T00:00:00Z`)
        );

    const end =
        nextDay(start);

    return {
        start,
        end,
        sql: `
SELECT *
FROM events
WHERE ${timestampColumn} >= $1
  AND ${timestampColumn} < $2;
`.trim()
    };
}

console.log("\nHALF-OPEN RANGE");

const range =
    dayRangeQuery(
        "event_timestamp",
        "2026-09-22"
    );

console.log(
    "Start:",
    range.start.toISOString()
);

console.log(
    "End:",
    range.end.toISOString()
);

console.log(range.sql);

console.log(`
The interval is:

    [start, end)

That means start is included and end is excluded.

This is safer than constructing a final timestamp such as
23:59:59.999999 because timestamp precision does not need to be guessed.
`);


// ============================================================================
// 17. TIME ZONE CONSIDERATIONS
// ============================================================================

console.log("\nTIME ZONE CONSIDERATIONS");

const utcTimestamp =
    new Date("2026-09-22T18:30:00Z");

const indiaFormatter =
    new Intl.DateTimeFormat(
        "en-IN",
        {
            timeZone: "Asia/Kolkata",
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false
        }
    );

console.log(
    "UTC:",
    utcTimestamp.toISOString()
);

console.log(
    "Asia/Kolkata:",
    indiaFormatter.format(utcTimestamp)
);

console.log(`
A global timestamp can belong to one instant while its local calendar
representation differs by time zone.

PostgreSQL examples:

SELECT DATE_TRUNC(
    'day',
    event_timestamp AT TIME ZONE 'Asia/Kolkata'
);

SELECT EXTRACT(
    HOUR FROM event_timestamp AT TIME ZONE 'Asia/Kolkata'
);

The intended business time zone should be explicit when local reporting
boundaries matter.
`);


// ============================================================================
// 18. NULL SEMANTICS
// ============================================================================

console.log("\nNULL SEMANTICS");

console.log(`
PostgreSQL date functions preserve NULL:

EXTRACT(YEAR FROM NULL::date)
DATE_PART('year', NULL::date)
DATE_TRUNC('month', NULL::timestamp)
AGE(CURRENT_DATE, NULL::date)

all result in NULL.

JavaScript has a different type system, so application code should explicitly
validate missing values rather than assuming a JavaScript invalid Date behaves
like SQL NULL.
`);


// ============================================================================
// 19. JAVASCRIPT DATE VALIDATION
// ============================================================================

function parseISODateOnly(value) {
    if (
        typeof value !== "string" ||
        !/^\d{4}-\d{2}-\d{2}$/.test(value)
    ) {
        return null;
    }

    const parsed =
        new Date(`${value}T00:00:00Z`);

    if (Number.isNaN(parsed.getTime())) {
        return null;
    }

    // JavaScript normalizes some invalid dates, so verify the components.
    const [year, month, day] =
        value.split("-").map(Number);

    if (
        parsed.getUTCFullYear() !== year ||
        parsed.getUTCMonth() + 1 !== month ||
        parsed.getUTCDate() !== day
    ) {
        return null;
    }

    return parsed;
}

console.log("\nDATE VALIDATION");

for (const value of [
    "2026-09-22",
    "2026-02-29",
    "2024-02-29",
    "2026-13-01",
    "not-a-date"
]) {
    const parsed =
        parseISODateOnly(value);

    console.log(
        value,
        "->",
        parsed
            ? parsed.toISOString()
            : "INVALID"
    );
}


// ============================================================================
// 20. MONTH BUCKETING
// ============================================================================

function groupByMonth(timestamps) {
    const result = new Map();

    for (const input of timestamps) {
        const timestamp =
            input instanceof Date
                ? input
                : new Date(input);

        if (Number.isNaN(timestamp.getTime())) {
            throw new Error(
                "Cannot group invalid timestamp"
            );
        }

        const bucket =
            startOfMonth(timestamp)
                .toISOString();

        result.set(
            bucket,
            (result.get(bucket) || 0) + 1
        );
    }

    return result;
}

const events = [
    "2026-09-01T08:30:00Z",
    "2026-09-01T09:15:00Z",
    "2026-09-02T10:00:00Z",
    "2026-09-15T12:45:00Z",
    "2026-10-01T07:10:00Z"
];

console.log("\nMONTHLY EVENT BUCKETS");

for (const [
    month,
    count
] of groupByMonth(events)) {
    console.log(
        month,
        "->",
        count
    );
}


// ============================================================================
// 21. QUARTERLY REVENUE MODEL
// ============================================================================

const transactions = [
    {
        timestamp: "2026-01-10T10:00:00Z",
        amount: 12000
    },
    {
        timestamp: "2026-02-20T15:00:00Z",
        amount: 8000
    },
    {
        timestamp: "2026-04-03T12:00:00Z",
        amount: 15000
    },
    {
        timestamp: "2026-05-18T14:00:00Z",
        amount: 21000
    },
    {
        timestamp: "2026-07-09T09:00:00Z",
        amount: 18000
    }
];

function quarterlyRevenue(records) {
    const result = new Map();

    for (const record of records) {
        const timestamp =
            new Date(record.timestamp);

        if (
            Number.isNaN(timestamp.getTime()) ||
            !Number.isFinite(record.amount)
        ) {
            throw new Error(
                "Invalid transaction record"
            );
        }

        const bucket =
            startOfQuarter(timestamp)
                .toISOString();

        result.set(
            bucket,
            (result.get(bucket) || 0) +
            record.amount
        );
    }

    return result;
}

console.log("\nQUARTERLY REVENUE");

for (const [
    quarter,
    revenue
] of quarterlyRevenue(transactions)) {
    console.log(
        quarter,
        "->",
        revenue
    );
}


// ============================================================================
// 22. ASYNCHRONOUS ANALYTICS PIPELINE
// ============================================================================

function delay(milliseconds) {
    return new Promise(
        resolve => setTimeout(
            resolve,
            milliseconds
        )
    );
}

async function processDateAnalytics(records) {
    // An async function demonstrates how a real application could combine
    // date calculations with asynchronous database/API work.
    await delay(5);

    return records.map(record => {
        const timestamp =
            new Date(record.timestamp);

        return {
            ...record,
            monthStart:
                startOfMonth(timestamp)
                    .toISOString(),
            quarterStart:
                startOfQuarter(timestamp)
                    .toISOString(),
            year:
                timestamp.getUTCFullYear(),
            month:
                timestamp.getUTCMonth() + 1,
            quarter:
                Math.floor(
                    timestamp.getUTCMonth() / 3
                ) + 1
        };
    });
}

console.log("\nASYNC DATE ANALYTICS");

processDateAnalytics(transactions)
    .then(result => {
        console.log(
            JSON.stringify(
                result,
                null,
                2
            )
        );
    })
    .catch(error => {
        console.error(
            "Analytics error:",
            error.message
        );
    });


// ============================================================================
// 23. ADVANCED POSTGRESQL REPORTING QUERIES
// ============================================================================

console.log("\nADVANCED POSTGRESQL QUERIES");

const queries = {
    monthlyActiveCustomers: `
SELECT
    DATE_TRUNC(
        'month',
        event_timestamp
    ) AS month_start,
    COUNT(DISTINCT customer_id)
        AS active_customers
FROM customer_events
WHERE event_timestamp >= $1
  AND event_timestamp < $2
GROUP BY DATE_TRUNC(
    'month',
    event_timestamp
)
ORDER BY month_start;
`.trim(),

    currentMonth: `
SELECT
    DATE_TRUNC(
        'month',
        CURRENT_DATE
    ) AS current_month_start,
    DATE_TRUNC(
        'month',
        CURRENT_DATE
    ) + INTERVAL '1 month'
        AS next_month_start;
`.trim(),

    currentQuarter: `
SELECT
    DATE_TRUNC(
        'quarter',
        CURRENT_DATE
    ) AS current_quarter_start,
    DATE_TRUNC(
        'quarter',
        CURRENT_DATE
    ) + INTERVAL '3 months'
        AS next_quarter_start;
`.trim(),

    ageInYears: `
SELECT
    employee_id,
    EXTRACT(
        YEAR FROM AGE(
            CURRENT_DATE,
            birth_date
        )
    )::int AS age_years
FROM employees;
`.trim(),

    birthdayMonth: `
SELECT
    employee_id,
    employee_name,
    birth_date
FROM employees
WHERE EXTRACT(
    MONTH FROM birth_date
) = EXTRACT(
    MONTH FROM CURRENT_DATE
);
`.trim()
};

for (const [
    name,
    query
] of Object.entries(queries)) {
    console.log(`\n-- ${name}`);
    console.log(query);
}


// ============================================================================
// 24. QUERY BUILDER
// ============================================================================

class DateQueryBuilder {
    constructor(tableName) {
        validateIdentifier(tableName);
        this.tableName = tableName;
    }

    monthlyAggregation(
        timestampColumn
    ) {
        validateIdentifier(timestampColumn);

        return `
SELECT
    DATE_TRUNC(
        'month',
        ${timestampColumn}
    ) AS month_start,
    COUNT(*) AS row_count
FROM ${this.tableName}
GROUP BY DATE_TRUNC(
    'month',
    ${timestampColumn}
)
ORDER BY month_start;
`.trim();
    }

    ageReport(
        birthDateColumn
    ) {
        validateIdentifier(
            birthDateColumn
        );

        return `
SELECT
    *,
    AGE(
        CURRENT_DATE,
        ${birthDateColumn}
    ) AS age
FROM ${this.tableName};
`.trim();
    }

    yearExtraction(
        dateColumn
    ) {
        validateIdentifier(dateColumn);

        return `
SELECT
    EXTRACT(
        YEAR FROM ${dateColumn}
    )::int AS year_value
FROM ${this.tableName};
`.trim();
    }
}

const builder =
    new DateQueryBuilder("employees");

console.log("\nQUERY BUILDER");

console.log(
    builder.monthlyAggregation(
        "joined_date"
    )
);

console.log(
    builder.ageReport(
        "birth_date"
    )
);

console.log(
    builder.yearExtraction(
        "birth_date"
    )
);


// ============================================================================
// 25. ERROR HANDLING
// ============================================================================

console.log("\nERROR HANDLING");

try {
    extractJavaScriptComponent(
        referenceDate,
        "invalid"
    );
} catch (error) {
    console.log(
        "Handled invalid extraction field:",
        error.message
    );
}

try {
    calendarAge(
        "not-a-date",
        birthDate
    );
} catch (error) {
    console.log(
        "Handled invalid age input:",
        error.message
    );
}

try {
    postgresDateTrunc(
        "invalid",
        "created_at"
    );
} catch (error) {
    console.log(
        "Handled invalid truncation:",
        error.message
    );
}


// ============================================================================
// 26. PERFORMANCE CONSIDERATIONS
// ============================================================================

console.log("\nPERFORMANCE CONSIDERATIONS");

function benchmark(
    operation,
    values
) {
    const start =
        performance.now();

    for (const value of values) {
        operation(value);
    }

    return performance.now() - start;
}

const benchmarkValues =
    Array.from(
        { length: 10000 },
        (_, index) =>
            new Date(
                Date.UTC(
                    2026,
                    index % 12,
                    (index % 28) + 1,
                    12,
                    0,
                    0
                )
            )
    );

const elapsed =
    benchmark(
        startOfMonth,
        benchmarkValues
    );

console.log(
    `Processed ${benchmarkValues.length} dates in ${elapsed.toFixed(3)} ms`
);

console.log(`
This measures JavaScript execution only.

For PostgreSQL, performance depends on the query plan, indexes, table size,
statistics, data distribution, expression evaluation, grouping strategy,
memory, CPU, storage, and network behavior.

Use PostgreSQL EXPLAIN and EXPLAIN ANALYZE when investigating database
performance.
`);


// ============================================================================
// 27. SECURITY
// ============================================================================

console.log("\nSECURITY");

console.log(`
Date functions are not inherently dangerous.

Unsafe SQL construction is dangerous.

Do not build:

    "WHERE created_at >= '" + userInput + "'"

Use parameterized queries:

    WHERE created_at >= $1

and provide the value separately.

For table and column names, validate identifiers or use the identifier
composition facilities supplied by the PostgreSQL driver.
`);


// ============================================================================
// 28. COMPARISON TABLE
// ============================================================================

console.log("\nFUNCTION SELECTION");

const functionSelection = [
    [
        "EXTRACT",
        "Retrieve a component",
        "EXTRACT(YEAR FROM order_date)"
    ],
    [
        "DATE_PART",
        "Retrieve a component",
        "DATE_PART('year', order_date)"
    ],
    [
        "DATE_TRUNC",
        "Get period beginning",
        "DATE_TRUNC('month', order_date)"
    ],
    [
        "AGE",
        "Calendar interval",
        "AGE(CURRENT_DATE, birth_date)"
    ],
    [
        "CURRENT_DATE",
        "Database current date",
        "CURRENT_DATE"
    ]
];

for (const row of functionSelection) {
    console.log(
        `${row[0].padEnd(14)} | ` +
        `${row[1].padEnd(24)} | ` +
        row[2]
    );
}


// ============================================================================
// 29. TESTS
// ============================================================================

function assert(condition, message) {
    if (!condition) {
        throw new Error(
            `Assertion failed: ${message}`
        );
    }
}

function runTests() {
    assert(
        extractJavaScriptComponent(
            referenceDate,
            "year"
        ) === 2026,
        "year extraction"
    );

    assert(
        extractJavaScriptComponent(
            referenceDate,
            "month"
        ) === 9,
        "month extraction"
    );

    assert(
        extractJavaScriptComponent(
            referenceDate,
            "quarter"
        ) === 3,
        "quarter extraction"
    );

    assert(
        startOfMonth(referenceDate)
            .toISOString()
            === "2026-09-01T00:00:00.000Z",
        "month truncation"
    );

    assert(
        startOfYear(referenceDate)
            .toISOString()
            === "2026-01-01T00:00:00.000Z",
        "year truncation"
    );

    const calculatedAge =
        calendarAge(
            new Date(
                "2026-09-22T00:00:00Z"
            ),
            new Date(
                "1995-04-18T00:00:00Z"
            )
        );

    assert(
        calculatedAge.years === 31,
        "age years"
    );

    assert(
        calculatedAge.months === 5,
        "age months"
    );

    assert(
        calculatedAge.days === 4,
        "age days"
    );

    assert(
        parseISODateOnly(
            "2026-09-22"
        ) !== null,
        "valid ISO date"
    );

    assert(
        parseISODateOnly(
            "2026-02-29"
        ) === null,
        "invalid non-leap-year date"
    );

    try {
        validateIdentifier(
            "orders;DROP"
        );
        throw new Error(
            "Unsafe identifier was accepted"
        );
    } catch (error) {
        if (
            !error.message.includes(
                "Invalid SQL identifier"
            )
        ) {
            throw error;
        }
    }

    console.log(
        "All JavaScript teaching tests passed."
    );
}

runTests();


// ============================================================================
// 30. FINAL COMBINED QUERY
// ============================================================================

console.log("\nFINAL COMBINED POSTGRESQL QUERY");

console.log(`
SELECT
    DATE_TRUNC(
        'month',
        order_timestamp
    ) AS month_start,
    EXTRACT(
        YEAR FROM order_timestamp
    )::int AS order_year,
    EXTRACT(
        QUARTER FROM order_timestamp
    )::int AS order_quarter,
    COUNT(*) AS order_count,
    SUM(order_amount) AS revenue
FROM orders
WHERE order_timestamp >= DATE_TRUNC(
    'year',
    CURRENT_DATE
)
AND order_timestamp < DATE_TRUNC(
    'year',
    CURRENT_DATE
) + INTERVAL '1 year'
GROUP BY
    DATE_TRUNC(
        'month',
        order_timestamp
    ),
    EXTRACT(
        YEAR FROM order_timestamp
    ),
    EXTRACT(
        QUARTER FROM order_timestamp
    )
ORDER BY month_start;
`);

console.log("\n" + "=".repeat(80));
console.log("END OF JAVASCRIPT DATE FUNCTIONS STUDY PROGRAM");
console.log("=".repeat(80));
