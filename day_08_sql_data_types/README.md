# SQL Data Types: INTEGER, NUMERIC, DECIMAL, VARCHAR, TEXT, BOOLEAN, DATE, TIME, and TIMESTAMP

## Introduction

A relational database stores information in tables. Each table consists of rows and columns, and every column has an intended kind of data. SQL data types provide the mechanism for expressing that intended representation.

The data type of a column affects how values are stored, validated, compared, sorted, calculated, indexed, and interpreted. A correct data type is therefore part of database design rather than merely a storage decision.

This study material covers the following SQL data types:

- INTEGER
- NUMERIC
- DECIMAL
- VARCHAR
- TEXT
- BOOLEAN
- DATE
- TIME
- TIMESTAMP

The accompanying Python script demonstrates these concepts using Python and SQLite. SQLite is included with Python, allowing SQL examples to run without an external database server.

## Fundamental Concepts

A SQL table contains:

- Columns, which define attributes of stored entities.
- Rows, which represent individual records.
- Values, which are stored in individual cells.
- Data types, which define the intended representation of each column.

For example, an employee table may conceptually contain:

    employee_id      INTEGER
    employee_name    VARCHAR
    salary           DECIMAL
    is_active        BOOLEAN
    birth_date       DATE
    created_at       TIMESTAMP

The choice of type should be based on the meaning of the data.

A quantity is conceptually numeric. A date of birth is conceptually temporal. An account status is conceptually logical. A product description is conceptually textual.

Using a generic text type for every column can make a schema easier to create initially, but it removes useful information about the meaning and expected behavior of data.

## NULL and Missing Values

SQL uses NULL to represent the absence of a known value.

NULL can represent different situations depending on the business domain:

- Unknown
- Missing
- Not yet determined
- Not applicable

NULL is not equivalent to:

- Zero
- An empty string
- FALSE

SQL also uses three-valued logic:

- TRUE
- FALSE
- UNKNOWN

A comparison involving NULL commonly produces UNKNOWN.

For this reason, SQL uses:

    column_name IS NULL

and:

    column_name IS NOT NULL

rather than:

    column_name = NULL

The distinction is important for query correctness.

A nullable BOOLEAN column can conceptually represent three states:

- TRUE
- FALSE
- NULL, meaning unknown or not determined

This should be used intentionally because unknown and false are different business states.

# INTEGER

## Definition

INTEGER stores whole numbers without a fractional component.

Examples include:

    -10
    0
    1
    42
    100000

INTEGER values are appropriate when the meaning of the data is inherently whole-number based.

## Common Uses

INTEGER is commonly used for:

- Identifiers
- Counts
- Quantities
- Sequence numbers
- Ages
- Inventory units
- Number of completed transactions

## Integer Arithmetic

Integer values support arithmetic operations such as:

    +
    -
    *
    /

The exact behavior of division and type conversion can differ between database systems.

For example, the distinction between integer division and decimal division should be verified in the target DBMS.

## Integer Constraints

An INTEGER type alone does not guarantee that the value satisfies a business rule.

An inventory quantity may require a non-negative value.

A schema can express this using a constraint such as:

    quantity INTEGER NOT NULL CHECK (quantity >= 0)

The data type defines the representation. The constraint defines an additional business rule.

## Range Considerations

INTEGER ranges vary between database systems.

Some database systems provide related integer types such as:

- SMALLINT
- INTEGER
- BIGINT

The appropriate type depends on the expected range of values and database-specific implementation details.

Large systems should consider future growth. Choosing a type with insufficient range can eventually create migration and compatibility problems.

# NUMERIC

## Definition

NUMERIC represents decimal numeric values. In many database systems, NUMERIC is designed for exact or controlled decimal arithmetic.

Typical syntax is:

    NUMERIC(precision, scale)

Precision defines the total number of digits.

Scale defines the number of digits to the right of the decimal point.

For example:

    NUMERIC(8, 2)

conceptually allows eight total digits, with two digits after the decimal point.

A value such as:

    123456.78

contains eight digits in total.

## Use Cases

NUMERIC is useful for values such as:

- Financial amounts
- Measurements requiring controlled decimal representation
- Rates
- Percentages
- Scores

The exact behavior of NUMERIC varies between database systems. Precision limits, scale limits, rounding, overflow, and storage behavior should be verified for the target DBMS.

# DECIMAL

## Definition

DECIMAL is another fixed-precision decimal type.

Typical syntax is:

    DECIMAL(precision, scale)

For example:

    DECIMAL(12, 2)

is commonly suitable for monetary values requiring up to twelve total digits and two fractional digits.

## Precision

Precision is the total number of significant decimal digits.

For a conceptual type:

    DECIMAL(6, 2)

the scale is two digits after the decimal point.

Values may conceptually include:

    1234.56
    9999.99
    0.01

A value with excessive total digits or excessive fractional digits may be rejected, rounded, or handled differently depending on the database system.

## Why DECIMAL Matters for Money

Binary floating-point arithmetic can produce representation artifacts.

For example, in many programming environments:

    0.1 + 0.2

may not produce a binary floating-point representation that displays exactly as 0.3.

Exact decimal arithmetic is generally more appropriate for financial values where decimal accuracy is important.

The Python script demonstrates this difference using Python's Decimal type.

## Rounding

Financial systems should define explicit rounding behavior.

Common concerns include:

- Number of decimal places
- When rounding occurs
- Rounding mode
- Tax calculations
- Per-line versus invoice-total rounding

A schema type alone does not define every financial rule.

# INTEGER, NUMERIC, and DECIMAL Compared

## INTEGER

Best suited for:

- Whole-number counts
- Identifiers
- Quantities

Fractional values are not conceptually represented.

## NUMERIC

Best suited for:

- Exact or controlled decimal values
- Measurements
- Rates
- Values requiring configured precision and scale

## DECIMAL

Best suited for:

- Monetary values
- Prices
- Exact fixed-point decimal values

NUMERIC and DECIMAL are treated similarly by many database systems, but exact standards and implementation details can differ.

# VARCHAR

## Definition

VARCHAR stores variable-length character strings.

Typical syntax:

    VARCHAR(50)

The number defines a maximum length according to the rules of the database system.

Examples of VARCHAR values include:

    Alice
    employee_123
    example@example.com

## Common Uses

VARCHAR is commonly appropriate for:

- Names
- Usernames
- Email addresses
- Short titles
- Labels
- Codes
- Phone numbers stored as textual identifiers

## Length Limits

A VARCHAR length can represent a useful business rule.

For example:

    username VARCHAR(50)

communicates that usernames are intended to be limited in length.

The length constraint does not validate the complete meaning of the value.

For example, an email column may have a length limit while still requiring separate validation rules.

## Semantic Validation

A data type determines the general representation of a value. It does not necessarily validate every business requirement.

A username may require rules such as:

- Minimum length
- Maximum length
- Allowed characters
- No whitespace
- Uniqueness

These requirements may be implemented using:

- CHECK constraints
- UNIQUE constraints
- Application validation
- Database-specific validation features

# TEXT

## Definition

TEXT stores textual data.

It is suitable for information that can be substantially longer or does not have a meaningful small maximum length.

## Common Uses

TEXT is commonly used for:

- Product descriptions
- Comments
- Articles
- Notes
- Long-form content
- Messages

## VARCHAR Versus TEXT

VARCHAR is useful when maximum length is part of the business definition.

TEXT is useful when the data is naturally long-form or does not require a specific bounded length.

The exact performance and storage differences depend on the database system.

A type should not be selected solely on the assumption that TEXT is universally slower or VARCHAR is universally more efficient. Database implementation and workload characteristics matter.

# BOOLEAN

## Definition

BOOLEAN represents a logical value.

The conceptual values are:

- TRUE
- FALSE

Typical use cases include:

- Whether an account is active
- Whether a user is verified
- Whether a feature is enabled
- Whether an item is available

## Database Differences

Not all database systems implement BOOLEAN identically.

Some systems provide a native BOOLEAN type.

Others represent logical values using integers such as:

    1 for true
    0 for false

SQLite commonly uses integer storage for boolean-style values.

A constraint can enforce the intended domain:

    CHECK (is_active IN (0, 1))

## Nullable Boolean

A nullable BOOLEAN can represent:

- TRUE
- FALSE
- Unknown

This can be useful when the logical state has not yet been determined.

It should not be used accidentally when the business domain requires only two states.

# DATE

## Definition

DATE represents a calendar date without a time-of-day component.

A common ISO-style representation is:

    YYYY-MM-DD

Examples:

    2026-09-08
    1993-05-18

## Common Uses

DATE is appropriate for:

- Birth dates
- Due dates
- Holidays
- Contract dates
- Invoice dates
- Launch dates

## DATE Versus TIMESTAMP

A DATE should be preferred when time of day is irrelevant.

A birth date, for example, generally does not require:

    1993-05-18 00:00:00

Using a TIMESTAMP when only a date is meaningful can introduce unnecessary assumptions about time and timezone.

## Invalid Dates

Date validation must handle:

- Leap years
- Invalid months
- Invalid days

For example:

    2024-02-29

is valid because 2024 is a leap year.

    2026-02-29

is invalid because 2026 is not a leap year.

# TIME

## Definition

TIME represents a time of day without a calendar date.

A common representation is:

    HH:MM:SS

Examples:

    09:30:00
    17:45:12
    23:59:59

## Common Uses

TIME is useful for:

- Opening hours
- Closing hours
- Daily schedules
- Shift start times
- Appointment times

## TIME Limitations

A TIME value does not represent a unique historical moment.

The value:

    09:00:00

does not specify:

- The date
- The timezone
- The geographical location

A TIME column is appropriate when only the clock time is meaningful.

# TIMESTAMP

## Definition

TIMESTAMP stores both date and time.

Examples include:

    2026-09-08 11:30:00

and:

    2026-09-08T11:30:00

depending on the database and application representation.

## Common Uses

TIMESTAMP is commonly used for:

- Record creation times
- Login events
- Transaction times
- Audit records
- Scheduled events
- System events

## Timestamp and Timezones

Timezone handling is one of the most important temporal design issues.

A timestamp such as:

    2026-09-08 09:00:00

does not independently identify a timezone.

If the value represents a real-world event, the application must define whether it represents:

- Local time
- UTC
- A timezone-aware timestamp

Different database systems provide different timestamp types and timezone semantics.

A robust global system often stores real-world event instants using a consistent timezone-aware convention, frequently UTC, while converting values to local time for presentation.

## Naive and Timezone-Aware Values

A timezone-naive timestamp contains no timezone information.

A timezone-aware timestamp is associated with an offset or timezone context.

Two displayed timestamps can represent the same moment while showing different clock times in different zones.

This distinction is important for:

- Distributed systems
- International applications
- Logging
- Auditing
- Scheduled events

# DATE, TIME, and TIMESTAMP Compared

## DATE

Contains:

- Year
- Month
- Day

Example:

    2026-09-08

Use when only the calendar date matters.

## TIME

Contains:

- Hour
- Minute
- Second

Example:

    09:30:00

Use when only time of day matters.

## TIMESTAMP

Contains:

- Date
- Time

Example:

    2026-09-08 09:30:00

Use when both date and time are required.

Timezone requirements must be considered separately according to the database system and application design.

# SQLite Type Behavior

The executable examples use SQLite.

SQLite differs from many strictly typed relational database systems because it uses a flexible type system.

Declared column types such as:

    INTEGER
    NUMERIC
    DECIMAL
    VARCHAR
    TEXT
    BOOLEAN

provide type affinity rather than identical strict enforcement to every other SQL database.

SQLite storage classes include concepts such as:

- NULL
- INTEGER
- REAL
- TEXT
- BLOB

The script uses SQLite's `typeof()` function to inspect runtime storage behavior.

This demonstrates an important production principle:

SQL type declarations are not guaranteed to behave identically across database systems.

Schema portability requires understanding the target DBMS.

# Constraints and Data Types

Data types and constraints solve different problems.

A type defines the intended representation.

A constraint defines additional rules.

Examples include:

    NOT NULL

which requires a value.

    UNIQUE

which prevents duplicate values.

    CHECK

which validates a logical condition.

For example:

    quantity INTEGER NOT NULL CHECK (quantity >= 0)

requires:

- An integer value
- A non-null value
- A value greater than or equal to zero

The type and constraint work together.

# Parameterized Queries and Security

Textual input must not be inserted into SQL statements through direct string concatenation.

Unsafe conceptual construction mixes SQL code and input values.

Parameterized queries separate the SQL structure from the values.

A parameterized query conceptually uses:

    SELECT user_id
    FROM users
    WHERE username = ?

The input value is passed separately.

This reduces SQL injection risk and improves correctness when handling special characters.

Data types do not replace parameterized queries.

VARCHAR and TEXT columns can still be vulnerable to SQL injection if external input is inserted into query strings incorrectly.

# Casting

CAST converts a value from one SQL representation to another.

Examples include conceptual operations such as:

    CAST('42' AS INTEGER)

and:

    CAST(42 AS TEXT)

Casting can be useful when a controlled conversion is required.

Repeated or unnecessary casting can create problems:

- Reduced readability
- Conversion errors
- Possible loss of precision
- Database-specific behavior
- Potentially less efficient queries

Implicit conversions should also be understood carefully because database systems may convert types differently.

# Sorting and Comparisons

Different data types have different comparison semantics.

Integer values are compared numerically.

Text values are compared according to textual ordering and collation rules.

Temporal values are compared according to their temporal representation.

NULL behaves differently because comparisons involving NULL generally produce UNKNOWN.

A consistent storage format is important.

For example, ISO-like date-time text:

    YYYY-MM-DD HH:MM:SS

sorts chronologically as text when all values follow the same complete format.

Inconsistent formats can produce incorrect lexical ordering.

# Indexing and Performance

Indexes improve access performance for suitable queries.

A timestamp column used frequently in range queries may benefit from an index.

Conceptually:

    CREATE INDEX idx_events_timestamp
    ON events(event_timestamp)

The effectiveness of an index depends on:

- Query patterns
- Data distribution
- Table size
- Database optimizer behavior
- Type consistency
- Expressions applied to indexed columns

Applying transformations to indexed columns inside predicates can sometimes reduce index effectiveness.

The target database's query-plan tools should be used to verify actual behavior.

# Practical Schema Example

The script creates an e-commerce-style product table containing:

- INTEGER for the product identifier
- VARCHAR for the product name
- TEXT for the description
- DECIMAL for price
- INTEGER for inventory quantity
- BOOLEAN for availability
- DATE for launch date
- TIMESTAMP for record creation time

This demonstrates that a real schema commonly combines multiple types because different attributes have different meanings.

A conceptual product record might contain:

    product_id          INTEGER
    product_name        VARCHAR(150)
    description         TEXT
    price               DECIMAL(12, 2)
    quantity_in_stock   INTEGER
    is_available        BOOLEAN
    launch_date         DATE
    created_at          TIMESTAMP

The schema also uses constraints for rules such as:

- Price cannot be negative
- Quantity cannot be negative
- Availability must be represented as a valid boolean domain
- Required values must not be NULL

# Common Mistakes

## Using Floating-Point Representation for Money

Binary floating-point values can create precision artifacts.

Fixed decimal representations are generally safer for currency when exact decimal behavior is required.

## Using INTEGER for Phone Numbers

Phone numbers are identifiers rather than quantities.

They may contain:

- Leading zeros
- Country prefixes
- Separators
- Formatting characters

They are generally better represented as text.

## Using VARCHAR for Every Value

Storing dates, quantities, and logical values as text removes useful type semantics.

Text-based numeric values can produce incorrect arithmetic and sorting behavior.

Text-based dates can also be incorrectly ordered if formatting is inconsistent.

## Using TIMESTAMP for Date-Only Concepts

A date of birth usually requires a DATE rather than a timestamp.

Adding an arbitrary time creates unnecessary information.

## Comparing NULL with Equals

The expression:

    column = NULL

does not perform the intended null check.

Use:

    column IS NULL

instead.

## Assuming BOOLEAN Is Identical Across Databases

BOOLEAN behavior differs across database systems.

The target DBMS should be considered when designing portable schemas.

## Ignoring Timezones

A timestamp without timezone semantics can be ambiguous.

This is particularly important for globally distributed applications.

## Depending Only on Data Types for Validation

A VARCHAR column does not guarantee that its contents are semantically valid.

Business rules may require:

- CHECK constraints
- UNIQUE constraints
- Foreign keys
- Application validation

# Best Practices

## Match the Type to the Meaning

Use:

- INTEGER for whole-number concepts
- DECIMAL or NUMERIC for exact decimal concepts
- VARCHAR for bounded strings
- TEXT for long-form text
- BOOLEAN for logical state
- DATE for dates
- TIME for time-of-day values
- TIMESTAMP for date-time values

## Use Constraints Deliberately

Use NOT NULL when missing values are not allowed.

Use CHECK for domain rules.

Use UNIQUE where duplication is invalid.

Use foreign keys to preserve relationships.

## Define Decimal Precision Explicitly

Financial and measurement systems should define appropriate precision and scale.

The values should be based on realistic domain requirements rather than arbitrary defaults.

## Define Timezone Policy Explicitly

Systems should document how real-world moments are represented and stored.

Timezone ambiguity should not be left to application assumptions.

## Use Parameterized Queries

Parameterized queries should be used for external values.

This improves security and prevents many quoting and injection problems.

## Verify Database-Specific Behavior

SQL is standardized, but database systems differ.

Important differences can include:

- Type ranges
- Boolean implementation
- Decimal precision
- Timezone behavior
- String length rules
- Implicit conversion
- NULL behavior in special expressions
- Index behavior

# Implementation Considerations

A database schema should be designed together with application code.

The application must understand:

- How dates are serialized
- How timestamps are interpreted
- How decimal values are handled
- Whether booleans are native or integer-backed
- How NULL values are represented
- How validation is divided between application and database layers

For Python applications, `decimal.Decimal` is appropriate when exact decimal arithmetic is required.

Python's `datetime.date`, `datetime.time`, and `datetime.datetime` provide corresponding temporal representations.

Conversions between application values and database values should be explicit and consistently tested.

# Real-World Applications

## Financial Systems

Typical types:

- INTEGER for transaction identifiers
- DECIMAL or NUMERIC for amounts
- BOOLEAN for transaction status flags
- TIMESTAMP for transaction time

Precision and rounding policies are critical.

## E-Commerce

Typical types:

- INTEGER for inventory counts
- VARCHAR for product names
- TEXT for descriptions
- DECIMAL for prices
- BOOLEAN for availability
- DATE for launch dates
- TIMESTAMP for record creation

## Authentication Systems

Typical types:

- INTEGER or another identifier type for users
- VARCHAR for usernames
- BOOLEAN for account status
- TIMESTAMP for login and audit events

Parameterized queries and careful validation are essential.

## Scheduling Systems

Typical types:

- DATE for calendar dates
- TIME for recurring daily times
- TIMESTAMP for specific event moments

Timezone handling becomes increasingly important when users or systems operate across regions.

## Analytics and Reporting

Typical types:

- INTEGER for counts
- NUMERIC or DECIMAL for precise measurements
- DATE and TIMESTAMP for time-based analysis
- BOOLEAN for categorical logical states
- TEXT and VARCHAR for labels and descriptions

Correct types improve filtering, aggregation, sorting, and interpretation.

# Limitations and Trade-Offs

No SQL data type is universally optimal.

INTEGER is efficient for whole-number concepts but cannot represent fractions.

DECIMAL provides controlled decimal arithmetic but may have different performance characteristics from native binary numeric representations.

VARCHAR provides bounded textual storage but requires a meaningful length rule.

TEXT provides flexibility for long content but may require different indexing or search strategies.

BOOLEAN is simple conceptually but implemented differently across database systems.

DATE and TIME are precise for their respective concepts but cannot independently represent complete moments.

TIMESTAMP represents date and time but requires careful timezone semantics for globally meaningful events.

Schema design therefore involves balancing:

- Correctness
- Precision
- Validation
- Storage
- Query performance
- Portability
- Business semantics

# Testing Data Type Behavior

Data type assumptions should be tested.

Useful tests include:

- Valid and invalid numeric ranges
- Decimal precision boundaries
- Maximum VARCHAR lengths
- Empty strings
- NULL handling
- Boolean domain validation
- Leap-year dates
- Invalid dates
- Invalid times
- Timestamp timezone conversion
- Constraint violations
- Type conversions
- Parameterized query behavior

The accompanying script includes executable validation examples and assertions for these cases.

Testing is especially important when moving between database systems because apparently similar SQL type declarations can have different storage and conversion behavior.
