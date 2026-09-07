# Creating Tables in SQL

## Introduction

Creating tables is one of the foundational activities in relational database design. A table defines how a category of information is represented, which values are allowed, how records are identified, and how one category of information relates to another.

The SQL statement used to define a table is `CREATE TABLE`.

A table definition is often called a schema definition. The schema establishes the structural rules that data must follow before rows are inserted.

The Python script accompanying this README uses Python's built-in `sqlite3` module and an in-memory SQLite database to demonstrate table creation through executable examples. SQLite is used because it allows the SQL concepts to be demonstrated without installing an external database server.

The major ideas apply broadly to relational database systems, although individual database products such as SQLite, PostgreSQL, MySQL, SQL Server, and Oracle may differ in supported data types, syntax, constraint behavior, schema alteration features, and administrative capabilities.

---

# Fundamental Table Structure

A relational table consists primarily of rows and columns.

## Rows

A row represents one record.

For example, an employee table might contain one row for each employee.

Conceptually:

| employee_id | employee_name | salary |
|---|---|---:|
| 1 | Asha | 65000 |
| 2 | Ravi | 72000 |

Each horizontal record is a row.

## Columns

A column represents one property or attribute.

Examples include:

- `employee_id`
- `employee_name`
- `salary`
- `department_id`
- `created_at`

Columns are defined when the table is created.

## Schema

The schema describes the formal structure of the table.

It specifies information such as:

- table name
- column names
- data types
- required values
- uniqueness rules
- default values
- primary keys
- foreign keys
- validation constraints

The schema controls structure, while rows contain the actual stored data.

---

# The CREATE TABLE Statement

The basic SQL structure is:

    CREATE TABLE table_name (
        column_name data_type,
        column_name data_type
    );

A more realistic definition can include constraints:

    CREATE TABLE employees (
        employee_id INTEGER PRIMARY KEY,
        employee_name TEXT NOT NULL,
        email TEXT UNIQUE,
        salary REAL CHECK (salary >= 0)
    );

The important components are:

- `CREATE TABLE`: creates a new table.
- `employees`: the table identifier.
- `employee_id`, `employee_name`, `email`, and `salary`: column identifiers.
- `INTEGER`, `TEXT`, and `REAL`: declared data types.
- `PRIMARY KEY`, `NOT NULL`, `UNIQUE`, and `CHECK`: constraints.

The table definition becomes part of the database schema.

---

# CREATE TABLE IF NOT EXISTS

A table creation statement normally fails if a table with the same name already exists.

SQLite supports:

    CREATE TABLE IF NOT EXISTS table_name (...);

This makes repeated initialization safer because the command does not fail merely because the table already exists.

An important limitation is that `IF NOT EXISTS` does not compare the existing table definition with the new definition.

For example, if an existing table has three columns and the new SQL statement describes five columns, `IF NOT EXISTS` does not automatically upgrade the table.

This distinction is important in production systems. Repeated initialization and schema migration are different problems.

---

# Column Definitions

A column definition usually follows this conceptual structure:

    column_name data_type constraint constraint ...

For example:

    email TEXT NOT NULL UNIQUE

This definition contains:

- `email`: column name
- `TEXT`: intended data type
- `NOT NULL`: the value is required
- `UNIQUE`: duplicate values are prohibited

Another example is:

    price INTEGER NOT NULL CHECK (price >= 0)

This requires:

- an integer value
- no missing value
- a value greater than or equal to zero

A well-designed column definition communicates both the intended data and the rules governing that data.

---

# SQL Data Types

Relational database systems use data types to describe the kind of information intended for a column.

Common categories include numeric, textual, temporal, logical, and binary data.

## Integer Types

Typical names include:

- `INTEGER`
- `INT`
- `SMALLINT`
- `BIGINT`

They represent whole numbers.

Examples include:

- identifiers
- quantities
- counts
- years

Different database systems may support different numeric ranges.

## Floating-Point Types

Typical names include:

- `REAL`
- `FLOAT`
- `DOUBLE`

These represent approximate numeric values.

They are suitable for many scientific and measurement calculations.

They require caution when exact decimal arithmetic is important.

## Exact Numeric Types

Many relational databases support:

- `DECIMAL`
- `NUMERIC`

These are commonly used for fixed-precision values, particularly financial values.

SQLite differs because it uses a dynamic type system and does not provide a dedicated fixed-precision decimal storage class equivalent to the exact decimal systems of many server databases.

The script demonstrates an alternative SQLite design in which monetary values are stored in the smallest currency unit as integers.

For example:

- 499.50 currency units can be represented as 49,950 paise.

This avoids many floating-point representation problems.

## Text Types

Common text types include:

- `TEXT`
- `VARCHAR`
- `CHAR`

The differences depend on the database system.

Text columns are commonly used for:

- names
- descriptions
- email addresses
- codes
- identifiers that are not numeric quantities

## Binary Types

Binary data may use types such as:

- `BLOB`
- `BYTEA`

depending on the database.

Binary columns can store raw bytes.

## Date and Time Types

Many databases provide types such as:

- `DATE`
- `TIME`
- `TIMESTAMP`
- `DATETIME`

SQLite commonly stores temporal information as:

- text
- integer timestamps
- real-number date representations

The correct design depends on whether the application represents:

- a calendar date
- a local time
- a precise instant
- a timezone-aware event

---

# SQLite Type Affinity

SQLite differs from strongly typed relational systems because its storage model is dynamic.

SQLite's primary storage classes are:

- `NULL`
- `INTEGER`
- `REAL`
- `TEXT`
- `BLOB`

A declared type still provides useful information and influences SQLite's type affinity behavior.

For example:

    quantity INTEGER

communicates that the column is intended to store numeric quantities, even though SQLite's dynamic typing behavior differs from systems that enforce rigid column types.

The script also attempts to demonstrate SQLite `STRICT` tables where supported by the installed SQLite version.

Strict tables provide stronger type enforcement for supported SQLite data types.

---

# NULL

`NULL` represents missing, unknown, undefined, or inapplicable information.

It is not equivalent to:

- zero
- an empty string
- false
- a blank space

Consider these values:

| Value | Meaning |
|---|---|
| `NULL` | No known value |
| `0` | Numeric zero |
| `''` | Empty text |
| `' '` | A text value containing one space |

The script demonstrates that these states are different.

## Testing for NULL

A common mistake is:

    WHERE column_name = NULL

The correct form is:

    WHERE column_name IS NULL

Similarly:

    WHERE column_name IS NOT NULL

SQL comparisons involving `NULL` follow three-valued logic:

- true
- false
- unknown

This behavior has important implications for conditions and constraints.

---

# Primary Keys

A primary key uniquely identifies each row.

Example:

    product_id INTEGER PRIMARY KEY

Primary keys should normally be:

- unique
- stable
- appropriate for identifying a record

A primary key prevents two rows from representing the same key value.

The script demonstrates duplicate primary key insertion producing an `IntegrityError`.

## Surrogate Keys

A surrogate key is an identifier with no direct business meaning.

Example:

    customer_id INTEGER PRIMARY KEY

A surrogate key is often paired with a separate uniqueness constraint:

    email TEXT UNIQUE

This allows the business value to change without changing the row's primary identity.

## Natural Keys

A natural key is derived from real-world data.

Examples might include:

- country code
- tax identifier
- email address in some systems

Natural keys can be useful when they are truly stable and inherently unique.

They can become problematic when business values change.

---

# SQLite INTEGER PRIMARY KEY

In SQLite, `INTEGER PRIMARY KEY` has special behavior.

It is associated with SQLite's internal row identifier in ordinary rowid tables.

Example:

    task_id INTEGER PRIMARY KEY

When inserting a row without supplying the key, SQLite can generate an integer value automatically.

The script demonstrates this behavior.

---

# AUTOINCREMENT

SQLite also supports:

    INTEGER PRIMARY KEY AUTOINCREMENT

This is not automatically required for automatic integer key generation.

`INTEGER PRIMARY KEY` already supports generated identifiers.

`AUTOINCREMENT` changes how identifiers are allocated and generally prevents reuse of previously generated row identifiers under relevant conditions.

It can introduce additional overhead.

It should therefore be used only when its specific identifier-allocation behavior is required.

---

# NOT NULL

The `NOT NULL` constraint prevents missing values.

Example:

    employee_name TEXT NOT NULL

An attempt to insert `NULL` into the column fails.

A subtle distinction is that `NOT NULL` does not prevent empty strings.

For example:

    ''

is still a text value.

If an application requires non-empty text, additional validation is necessary.

Depending on the database and requirements, validation can be implemented through:

- `CHECK` constraints
- application validation
- database functions or triggers where appropriate

---

# UNIQUE Constraints

A `UNIQUE` constraint prevents duplicate values.

Example:

    username TEXT UNIQUE

A common use case is an email address:

    email TEXT NOT NULL UNIQUE

This ensures every row contains an email and that no two rows use the same value.

The script demonstrates a duplicate insertion raising an integrity error.

## Composite UNIQUE Constraints

A uniqueness rule can involve more than one column.

Example:

    UNIQUE (building, room_number)

This means:

- multiple buildings may have room `101`
- one building may have multiple rooms
- the same building and room combination cannot be duplicated

Composite uniqueness is useful when uniqueness belongs to a combination rather than a single attribute.

---

# CHECK Constraints

A `CHECK` constraint validates a logical expression.

Examples include:

    CHECK (balance >= 0)

    CHECK (quantity > 0)

    CHECK (status IN ('pending', 'paid', 'failed'))

`CHECK` constraints are useful for protecting domain rules at the database level.

The script demonstrates validation of:

- non-negative balances
- positive quantities
- controlled status values
- boolean-like values

## CHECK and NULL

A nullable column combined with a `CHECK` constraint may behave differently than a required column.

For example:

    score INTEGER CHECK (score >= 0)

does not necessarily mean that every row must contain a score.

If the value is required, the design should explicitly include:

    score INTEGER NOT NULL CHECK (score >= 0)

This combination communicates two separate rules:

1. a score must exist
2. the score must satisfy the range condition

---

# DEFAULT Values

A `DEFAULT` expression supplies a value when an insert omits a column.

Example:

    status TEXT DEFAULT 'pending'

Another example:

    created_at TEXT DEFAULT CURRENT_TIMESTAMP

The script demonstrates both fixed and dynamically generated default values.

A default is not a substitute for every form of validation.

The exact behavior when explicitly inserting `NULL` depends on the column definition and database rules.

A design requiring a guaranteed value often combines:

- `NOT NULL`
- `DEFAULT`

Example:

    active INTEGER NOT NULL DEFAULT 1

---

# Column-Level and Table-Level Constraints

Constraints can be written directly in a column definition or separately at table level.

## Column-Level Example

    email TEXT UNIQUE

## Table-Level Example

    PRIMARY KEY (student_id, course_id)

Table-level constraints are particularly useful for rules involving multiple columns.

Examples include:

- composite primary keys
- composite unique constraints
- multi-column foreign keys in appropriate designs

---

# Composite Primary Keys

A composite primary key contains more than one column.

Example:

    PRIMARY KEY (student_id, course_id)

The pair must be unique.

This means:

- student 1 can enroll in course 101
- student 1 can enroll in course 102
- student 2 can enroll in course 101
- student 1 cannot enroll twice in course 101

Composite keys are common in:

- enrollment tables
- many-to-many relationship tables
- association tables
- natural multi-column identifiers

---

# Foreign Keys

A foreign key defines a relationship between tables.

Consider:

    departments
    employees

The department table may define:

    department_id INTEGER PRIMARY KEY

The employee table may define:

    department_id INTEGER REFERENCES departments(department_id)

The employee's `department_id` must correspond to a valid department when foreign key enforcement is active.

Foreign keys help preserve referential integrity.

The script explicitly enables SQLite foreign key enforcement with:

    PRAGMA foreign_keys = ON

This is important because SQLite foreign key enforcement must be enabled for the active connection.

---

# Referential Integrity

Referential integrity prevents relationships from pointing to nonexistent records.

For example, an employee should not refer to department `999` if no such department exists.

Foreign key constraints prevent these invalid references when enforcement is enabled.

Referential integrity is especially important when multiple applications, services, administrators, or scripts can write to the same database.

Application-level validation alone may not protect the database from every possible writer.

---

# Referential Actions

Foreign keys can specify what happens when a parent record changes or is deleted.

## ON DELETE CASCADE

Example:

    FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
        ON DELETE CASCADE

Deleting a project automatically deletes its dependent tasks.

This is useful when child records have no independent meaning without the parent.

It can also be dangerous if a deletion unexpectedly affects a large number of records.

## ON DELETE SET NULL

Example conceptually:

    ON DELETE SET NULL

When the parent is deleted, the child reference becomes `NULL`.

This is appropriate only when the child can meaningfully exist without the parent.

## ON DELETE RESTRICT

This prevents deletion of a parent while dependent rows exist.

It is useful when dependent records should be resolved explicitly before deleting the parent.

The correct referential action is a business rule, not merely a technical preference.

---

# One-to-One Relationships

A one-to-one relationship can be modeled using a foreign key with a `UNIQUE` constraint.

Example:

    user_id INTEGER NOT NULL UNIQUE

in a profile table.

This ensures that one user cannot have multiple profile rows.

One-to-one structures are useful when data is logically separated for reasons such as:

- optional attributes
- access control
- organizational clarity
- lifecycle differences

---

# One-to-Many Relationships

A one-to-many relationship places a foreign key in the child table.

Example:

    departments
        one department

    employees
        many employees

The employee table contains the department reference.

---

# Many-to-Many Relationships

Many-to-many relationships require an intermediate table.

Example:

    students
    courses
    enrollments

The `enrollments` table may contain:

    student_id
    course_id

with:

    PRIMARY KEY (student_id, course_id)

and foreign keys referencing both parent tables.

The script demonstrates this pattern in several schemas.

---

# Temporary Tables

SQLite supports temporary tables:

    CREATE TEMP TABLE temporary_calculations (...);

Temporary tables are scoped to the current database connection.

They can be useful for:

- intermediate processing
- temporary transformations
- session-specific calculations

They are generally not a replacement for carefully designed permanent tables.

---

# CREATE TABLE AS SELECT

A table can be created from a query result.

Conceptually:

    CREATE TABLE active_users AS
    SELECT ...
    FROM users;

This is useful for:

- snapshots
- derived datasets
- reporting tables
- temporary transformations

A critical distinction is that a table created from query results does not automatically reproduce every property of the source schema.

Constraints, indexes, triggers, and detailed metadata may not be copied as a complete production schema.

A derived table should therefore not automatically be treated as structurally equivalent to its source.

---

# Generated Columns

Generated columns derive their values from other columns.

The script demonstrates a full name calculated from first and last names.

Conceptually:

    full_name GENERATED ALWAYS AS (
        first_name || ' ' || last_name
    )

Generated columns can reduce redundant storage when a value is reliably derived from other stored values.

They require careful consideration because:

- generated expressions must remain meaningful
- database support differs
- storage and indexing options differ between systems

---

# Boolean-Like Values

SQLite does not use a dedicated BOOLEAN storage class in the same way as many database systems.

A common convention is:

- `0` for false
- `1` for true

The script strengthens this convention with:

    CHECK (is_active IN (0, 1))

This prevents unrelated numeric values such as `7`.

A boolean column in a strongly typed database may instead use:

    BOOLEAN

The exact implementation should match the target database.

---

# Enum-Like Values

A controlled category can be represented with a `CHECK` constraint.

Example:

    status TEXT NOT NULL
        CHECK (status IN ('pending', 'paid', 'failed'))

This provides simple schema-level validation.

A separate lookup table may be more appropriate when categories:

- require metadata
- change frequently
- participate in relationships
- require centralized management

The script demonstrates both approaches.

---

# Lookup Tables

A lookup table stores controlled categories as rows.

Example:

    order_statuses

with:

    status_code PRIMARY KEY
    display_name UNIQUE

Other tables reference the status code through a foreign key.

Advantages include:

- centralized category definitions
- referential integrity
- extensibility
- additional metadata

This approach is often preferable when categories are part of the application's relational model rather than merely a small fixed validation list.

---

# Naming Conventions

Clear names improve database maintainability.

The script uses descriptive `snake_case` names such as:

- `employee_id`
- `created_at`
- `customer_name`
- `order_status`

Good naming principles include:

- consistency
- descriptive identifiers
- avoidance of unnecessary abbreviations
- avoidance of ambiguous names
- predictable key naming

A common convention is to name primary keys with the entity name followed by `_id`.

For example:

- `customer_id`
- `product_id`
- `order_id`

Foreign keys often use the same name as the referenced key.

For example:

    orders.customer_id

references:

    customers.customer_id

---

# Quoted Identifiers

Identifiers containing spaces or reserved words may require quoting.

For example:

    "sales report"

and:

    "total amount"

The script demonstrates this syntax.

Quoted identifiers should be used carefully.

A schema requiring constant quoting is often harder to maintain than one using simple consistent identifiers.

---

# SQL Injection and Parameterization

Values supplied to SQL should normally use parameterized statements.

The script uses:

    INSERT INTO table_name (column_name)
    VALUES (?)

with the value supplied separately through Python.

This prevents user-controlled values from becoming executable SQL syntax.

A dangerous pattern is constructing SQL values through string concatenation.

Parameterization applies to data values.

It does not allow arbitrary table names or column names to be inserted safely through placeholders.

Dynamic identifiers require a different strategy.

The script demonstrates an allow-list approach where requested table names must match a predefined set of trusted identifiers.

---

# Normalization

Normalization organizes relational data to reduce unnecessary duplication and structural anomalies.

A poorly structured table might contain:

- customer information
- multiple product columns
- repeated groups
- unrelated attributes

A normalized design separates concepts into related tables.

The script demonstrates structures such as:

- customers
- products
- orders
- order_items

This design improves:

- consistency
- relationship management
- query flexibility
- data integrity

## Repeating Groups

A design such as:

    product_1
    product_2
    product_3

creates an arbitrary maximum number of products and makes queries difficult.

A related child table is usually more appropriate.

---

# Multi-Valued Attributes

Storing multiple values in one text field is often problematic.

For example:

    skills = "Python,SQL,Excel"

This makes:

- validation difficult
- searching less reliable
- joins awkward
- updates error-prone

The script demonstrates a normalized structure:

    users
    skills
    user_skills

The intermediate table represents the many-to-many relationship.

---

# Table Responsibility

A well-designed table should represent a coherent entity or relationship.

When one table contains many unrelated optional columns, the design may be combining several entities.

Examples might include columns relevant only to:

- employees
- students
- companies
- customers

A better design may separate these concepts into appropriate related tables.

The correct structure depends on the domain, business rules, and query requirements.

---

# Date and Time Design

Date and time columns require deliberate design.

Important questions include:

- Is the value a date only?
- Is it a time of day?
- Is it an absolute moment?
- Does timezone information matter?
- Should the database store UTC?

The script uses text values for SQLite demonstrations and `CURRENT_TIMESTAMP` for creation timestamps.

Production systems should define temporal conventions consistently.

Mixing local time, UTC, and timezone-less timestamps without a clear model can create difficult data errors.

---

# Financial Value Design

Approximate floating-point values can produce representation artifacts.

For exact financial values, many databases use:

- `DECIMAL`
- `NUMERIC`

SQLite applications often use integer smallest units.

For example:

    price_paise INTEGER

A value of `49950` can represent 499.50 currency units.

This approach provides predictable integer arithmetic when the smallest unit is appropriate for the application's requirements.

---

# Inspecting Table Structure

Database metadata is important for debugging and verification.

SQLite supports:

    PRAGMA table_info(table_name)

The script uses this command to inspect:

- column names
- declared types
- nullability
- default values
- primary key information

SQLite also stores schema SQL in its metadata tables.

The script queries `sqlite_master` to display the original table creation SQL.

Schema inspection is useful when:

- debugging
- reviewing migrations
- verifying deployed structures
- investigating unexpected constraints

---

# ALTER TABLE

`CREATE TABLE` creates a new table.

`ALTER TABLE` changes an existing table.

The script demonstrates adding a column.

Schema changes require more care than initial creation because existing data and applications already depend on the current structure.

Potential concerns include:

- compatibility with existing application versions
- migration duration
- locking behavior
- data conversion
- rollback difficulty
- validation of historical rows

SQLite supports a more limited set of schema alterations than some enterprise database systems.

Production schema changes should therefore be designed with the target database's capabilities in mind.

---

# Transactions

A transaction groups related database operations.

If an operation fails, the transaction can be rolled back.

The script demonstrates a transaction containing:

1. a valid insert
2. an invalid duplicate primary key insert

The failure prevents the partial transaction from remaining committed.

Transactions are commonly associated with ACID principles.

## Atomicity

A transaction is treated as a unit.

## Consistency

Constraints help preserve valid database states.

## Isolation

Concurrent operations are governed by the database's isolation behavior.

## Durability

Committed changes persist according to the database system's durability guarantees and configuration.

---

# Python Error Handling

Database operations can fail.

The script demonstrates handling exceptions such as:

- `sqlite3.IntegrityError`
- `sqlite3.OperationalError`
- `sqlite3.DatabaseError`

Important failure categories include:

- duplicate primary keys
- duplicate unique values
- missing required values
- failed check constraints
- invalid foreign keys
- syntax errors
- duplicate table creation

Applications should not assume schema operations always succeed.

Meaningful error handling is important during:

- initialization
- migration
- deployment
- data import
- automated testing

---

# Constraints and Application Validation

Database constraints and application validation have different roles.

## Application Validation

Useful for:

- user-friendly error messages
- input normalization
- interface-level validation
- domain-specific workflows

## Database Constraints

Useful for:

- protecting the stored data
- enforcing rules regardless of which application writes data
- maintaining consistency across services

Important invariants are often enforced at both levels.

For example:

Application validation can reject a negative price before submitting a request.

The database can still enforce:

    CHECK (price >= 0)

This protects the data if another application bypasses the original validation layer.

---

# Python Data Models and Relational Tables

The script demonstrates a Python dataclass representing a customer.

A Python object and a relational table are not identical concepts.

A Python object model describes application structures and behavior.

A relational schema describes persistent relational data.

Object-relational mapping systems can translate between these models, but understanding the underlying table structure remains important for:

- debugging
- performance analysis
- migration design
- query design
- data integrity

---

# Complete Relational Schema Design

The script builds a multi-table blog system containing:

- users
- posts
- comments
- tags
- post-tag relationships

This demonstrates how individual `CREATE TABLE` statements combine into a complete schema.

The relationships include:

- one user to many posts
- one user to many comments
- one post to many comments
- many posts to many tags

The many-to-many relationship uses a junction table with a composite primary key.

This structure demonstrates that table design is not only about defining individual columns. It also concerns the relationships and constraints connecting the database as a whole.

---

# Self-Referential Foreign Keys

A table can reference itself.

The script demonstrates an organizational structure in which:

    manager_id

references another employee in the same table.

This pattern can represent:

- management hierarchies
- category trees
- organizational structures
- parent-child relationships

The deletion behavior must be chosen carefully.

The script uses `ON DELETE SET NULL` so that removing a manager does not automatically remove all subordinate records.

---

# Deferred Foreign Keys

Some relationships cannot be valid after every individual SQL statement but can be valid by the end of a transaction.

Deferred foreign keys allow constraint validation to occur at transaction completion.

The script demonstrates a parent record referencing a child before the child is inserted, followed by insertion of the required child before the transaction commits.

This feature is useful for specific transactional dependency structures.

Its exact behavior and support depend on the database system.

---

# SQLite STRICT Tables

Traditional SQLite behavior allows flexible typing.

SQLite versions supporting `STRICT` tables can enforce stronger type requirements.

The script attempts to create a strict table and handles the possibility that the installed SQLite version does not support the feature.

This demonstrates an important production principle: database capabilities can depend on the deployed engine version.

Applications should not assume every environment supports identical SQL features.

---

# Schema Versioning

Database schemas evolve.

Typical changes include:

- creating new tables
- adding columns
- changing constraints
- adding indexes
- transforming stored data

A migration system records and applies these changes in controlled versions.

The script demonstrates a simple `schema_migrations` table.

Production migration systems normally require additional capabilities such as:

- ordered versions
- deployment tracking
- transactional migrations where supported
- compatibility planning
- rollback strategies where practical

Repeated `CREATE TABLE IF NOT EXISTS` is not a complete schema versioning strategy.

---

# Idempotent Schema Initialization

Initialization code is idempotent when running it multiple times produces a safe result.

The script defines a function that uses:

    CREATE TABLE IF NOT EXISTS

and calls it repeatedly.

This is useful for simple setup logic.

It does not solve schema upgrades.

If an existing table has an outdated structure, initialization must be combined with explicit migration logic.

---

# Indexes

Indexes are separate structures used to improve data retrieval performance.

The script creates an index on a foreign key column:

    CREATE INDEX idx_employees_department_id
    ON employees(department_id)

Indexes can improve:

- filtering
- joins
- ordering in appropriate query patterns

Indexes also have costs:

- storage
- slower inserts
- slower updates
- slower deletes

Indexes should therefore be chosen according to actual query behavior.

Adding indexes indiscriminately can reduce write performance.

---

# Query Plans

SQLite provides:

    EXPLAIN QUERY PLAN

This displays information about how SQLite intends to execute a query.

The script demonstrates query-plan inspection.

Query plans are useful for:

- investigating slow queries
- determining whether indexes are being considered
- understanding join behavior

A query plan must be interpreted in context.

The presence of an index does not guarantee optimal performance for every workload.

---

# Performance Considerations

Table design affects performance.

Important considerations include:

- key selection
- index design
- normalization
- row width
- data types
- transaction size
- write frequency
- expected query patterns

The script demonstrates bulk insertion using:

    executemany

inside a transaction.

Grouping related operations can reduce unnecessary transaction overhead.

Performance optimization should be based on measured workload behavior rather than assumptions.

---

# Security Considerations

Table design has security implications.

## Parameterized Values

Values should normally use parameterized SQL statements.

This reduces SQL injection risk.

## Dynamic Identifiers

Table names and column names cannot normally be parameterized like data values.

Dynamic identifiers should be selected from trusted constants or validated against strict allow-lists.

## Least Privilege

Production database identities should receive only the permissions necessary for their responsibilities.

A read-only service should not automatically have unrestricted schema modification permissions.

## Sensitive Data

A schema should store sensitive information only when necessary.

Important questions include:

- Is this column required?
- Who needs access?
- How long must it be retained?
- Should it be encrypted?
- Should it be hashed?

The script demonstrates an authentication table containing:

    password_hash

rather than a plain password column.

Passwords should not be stored as plain text.

---

# Production Table Design

Production table definitions should be reviewed as part of system design.

Important considerations include:

- business requirements
- data ownership
- expected volume
- query patterns
- concurrency
- data retention
- security
- migration strategy
- backup and recovery requirements
- database-specific capabilities

A table that works for a small demonstration may require different indexing, partitioning, security, or operational design at large scale.

---

# Table Creation Order

When tables contain foreign keys, creation order matters.

A practical sequence is:

1. Lookup tables
2. Independent entity tables
3. Parent tables
4. Child tables
5. Junction tables
6. Additional indexes

Creating referenced tables before dependent tables simplifies schema deployment.

---

# Common Mistakes

## Using Mutable Business Data as the Primary Key

An email address or other business value may change.

A surrogate primary key plus a `UNIQUE` constraint often provides greater flexibility.

## Confusing NULL with Empty Text

`NULL`, `''`, and `' '` are different values.

A schema should distinguish them intentionally.

## Using Floating Point for Exact Currency

Approximate floating-point representation can create undesirable precision behavior.

Exact decimal types or integer smallest units are often safer for monetary values.

## Omitting NOT NULL

A `CHECK` constraint does not necessarily make a value mandatory.

If a value must exist, explicitly declare `NOT NULL`.

## Missing Foreign Keys

Relationships represented only by application conventions can become inconsistent.

Foreign keys provide database-level referential protection.

## Storing Lists in One Column

Comma-separated lists often reduce relational integrity and query flexibility.

A related table or junction table is usually preferable.

## Overusing AUTOINCREMENT

SQLite's ordinary `INTEGER PRIMARY KEY` already provides automatic key generation.

`AUTOINCREMENT` should be used only when its special behavior is actually required.

## Creating Too Many Indexes

Indexes improve some reads but increase storage and write costs.

## Treating IF NOT EXISTS as Schema Migration

`IF NOT EXISTS` prevents duplicate creation errors but does not update an existing table definition.

## Using Ambiguous Names

Names such as `data`, `value`, or `info` often become difficult to understand as the schema grows.

---

# Testing Table Definitions

A schema should be tested.

Useful tests include verifying:

- required tables exist
- expected columns exist
- valid rows can be inserted
- duplicate primary keys fail
- duplicate unique values fail
- invalid foreign keys fail
- invalid check values fail
- cascading behavior works as intended
- transactions roll back correctly

The script includes a helper that verifies expected integrity errors.

Schema testing is especially important when database changes are managed through migrations.

---

# Complete Inventory Schema

The script concludes with a more complete inventory model containing:

- suppliers
- inventory products
- warehouse locations
- inventory stock

The schema demonstrates:

- surrogate primary keys
- unique supplier names
- unique product SKUs
- foreign keys
- non-negative quantity validation
- boolean-like active status
- composite primary keys
- deletion rules

The inventory stock table uses:

    PRIMARY KEY (product_id, location_id)

because one product can exist in multiple locations and each product-location combination should appear only once.

This is a practical example of a composite key representing a relationship.

---

# Complete Course Management Schema

The final integrated example contains:

- courses
- students
- registrations

The registration table contains a composite primary key:

    PRIMARY KEY (student_id, course_id)

This prevents duplicate registrations for the same student and course.

The schema also demonstrates:

- unique course codes
- unique student emails
- positive duration validation
- controlled registration statuses
- default values
- timestamps
- foreign keys
- deletion behavior

This integrated example shows how individual `CREATE TABLE` concepts combine into a coherent relational design.

---

# Practical Table Design Checklist

Before creating a production table, important questions include:

1. Does the table represent one coherent entity or relationship?
2. Does it have an appropriate primary key?
3. Which values are mandatory?
4. Which values must be unique?
5. Which numeric ranges are valid?
6. Which values require defaults?
7. Which relationships require foreign keys?
8. What should happen when parent rows are deleted?
9. Are date and time values represented consistently?
10. Are financial values represented precisely?
11. Are sensitive values necessary and appropriately protected?
12. Are names descriptive and consistent?
13. Are many-to-many relationships modeled through junction tables?
14. Are repeated groups avoided?
15. Are indexes aligned with expected query patterns?
16. Can future schema changes be deployed safely?
17. Are important database rules also validated appropriately in the application?

---

# Key Distinctions

## CREATE TABLE vs ALTER TABLE

`CREATE TABLE` creates a new structure.

`ALTER TABLE` modifies an existing structure.

## PRIMARY KEY vs UNIQUE

A primary key identifies the row.

A unique constraint prevents duplicate values but does not necessarily serve as the table's primary identity.

## NOT NULL vs CHECK

`NOT NULL` requires a value.

`CHECK` validates a logical rule.

Both may be required.

## Surrogate Key vs Natural Key

A surrogate key is an artificial identifier.

A natural key is derived from meaningful business data.

## CHECK List vs Lookup Table

A `CHECK` list is simple and fixed.

A lookup table is relational and extensible.

## INTEGER PRIMARY KEY vs AUTOINCREMENT in SQLite

Both can support automatically generated integer identifiers.

`AUTOINCREMENT` imposes additional allocation behavior and is not required for ordinary automatic key generation.

## Application Validation vs Database Constraints

Application validation improves interaction and workflow handling.

Database constraints protect the stored data itself.

---

# Limitations and Database Differences

The script uses SQLite for portability.

SQLite differs from server-based relational systems in several areas, including:

- type enforcement
- supported data types
- decimal arithmetic
- schema alteration capabilities
- permission systems
- concurrency architecture
- administrative features

When moving a schema to PostgreSQL, MySQL, SQL Server, Oracle, or another database system, the SQL should be reviewed for:

- data type compatibility
- generated column syntax
- boolean handling
- timestamp behavior
- constraint support
- identity or sequence syntax
- migration behavior
- index capabilities

The relational design principles remain applicable even when implementation syntax differs.

---

# Execution

The Python script is self-contained.

It requires a Python installation that includes the standard `sqlite3` module.

The script creates an in-memory database, executes the table definitions and demonstrations, prints results, handles expected constraint errors, and closes the database connection after completion.

No external database server, external file, or third-party Python package is required.
