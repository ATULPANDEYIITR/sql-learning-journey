"""
CREATING TABLES IN SQL
======================

A self-contained Python study script covering SQL table creation from beginner
through advanced concepts.

The examples use Python's built-in sqlite3 module because it requires no external
database server. SQLite supports standard SQL concepts such as:

- CREATE TABLE
- Column definitions
- Data types and type affinity
- PRIMARY KEY
- FOREIGN KEY
- NOT NULL
- UNIQUE
- CHECK
- DEFAULT
- Generated columns
- Temporary tables
- Composite keys
- Table relationships
- Schema inspection
- Transactions
- Error handling
- Validation
- Performance and indexing considerations
- Production-oriented design principles

SQLite differs from database systems such as PostgreSQL, MySQL, SQL Server, and
Oracle in some data-type and ALTER TABLE behavior. SQL concepts demonstrated here
remain broadly useful, while production systems may have database-specific syntax.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Optional


# =============================================================================
# 1. INTRODUCTION: WHAT IS A TABLE?
# =============================================================================
#
# A relational database stores structured data in tables.
#
# A table contains:
#
# - Columns: attributes or properties of an entity.
# - Rows: individual records.
# - Schema: the formal structure defining columns, types, and constraints.
#
# Example conceptual table:
#
# employees
#
# +----+------------+--------+------------+
# | id | name       | salary | department |
# +----+------------+--------+------------+
# | 1  | Asha       | 65000  | Engineering|
# | 2  | Ravi       | 72000  | Finance    |
# +----+------------+--------+------------+
#
# The CREATE TABLE statement defines the schema before data is inserted.


def print_section(title: str) -> None:
    """Print a visible separator for each educational section."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_rows(rows: Iterable[sqlite3.Row]) -> None:
    """Print query results in a readable form."""
    rows = list(rows)

    if not rows:
        print("(No rows returned)")
        return

    column_names = rows[0].keys()
    print(" | ".join(column_names))
    print("-" * 80)

    for row in rows:
        print(" | ".join(str(row[column]) for column in column_names))


# =============================================================================
# 2. DATABASE CONNECTION
# =============================================================================
#
# sqlite3.connect(":memory:") creates an in-memory database.
#
# Advantages for demonstrations:
# - No installation beyond Python's standard library.
# - No external files.
# - Every execution starts with a clean database.
#
# In production, SQLite can use a file:
#
# connection = sqlite3.connect("application.db")
#
# Other relational databases require database-specific drivers and connections.


print_section("1. DATABASE CONNECTION")

connection = sqlite3.connect(":memory:")
connection.row_factory = sqlite3.Row

# SQLite does not automatically enforce foreign key constraints unless explicitly
# enabled for the current database connection.
connection.execute("PRAGMA foreign_keys = ON")

print("Connected to an in-memory SQLite database.")
print("Foreign key enforcement enabled.")


# =============================================================================
# 3. BASIC CREATE TABLE SYNTAX
# =============================================================================
#
# General SQL structure:
#
# CREATE TABLE table_name (
#     column_name data_type column_constraint,
#     column_name data_type column_constraint,
#     table_constraint
# );
#
# Important components:
#
# CREATE TABLE
#     SQL command used to define a new table.
#
# table_name
#     Identifier representing the table.
#
# column_name
#     Identifier representing one attribute.
#
# data_type
#     Defines the intended kind of value.
#
# constraints
#     Rules that restrict valid data.
#
# Parentheses
#     Enclose the complete table definition.
#
# Commas
#     Separate columns and table-level constraints.
#
# Semicolon
#     Terminates an SQL statement in many SQL tools.


print_section("2. BASIC CREATE TABLE")

connection.execute(
    """
    CREATE TABLE students (
        student_id INTEGER,
        full_name TEXT,
        age INTEGER
    )
    """
)

print("Created table: students")

connection.execute(
    """
    INSERT INTO students (student_id, full_name, age)
    VALUES (?, ?, ?)
    """,
    (1, "Asha Sharma", 21),
)

rows = connection.execute("SELECT * FROM students")
print_rows(rows)


# =============================================================================
# 4. IF NOT EXISTS
# =============================================================================
#
# Attempting to create an already existing table normally produces an error.
#
# CREATE TABLE IF NOT EXISTS table_name (...)
#
# prevents an error if a table with the same name already exists.
#
# Important limitation:
# IF NOT EXISTS does not compare the desired schema with the existing schema.
# It only checks whether an object with that name exists.


print_section("3. CREATE TABLE IF NOT EXISTS")

connection.execute(
    """
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER,
        full_name TEXT,
        age INTEGER
    )
    """
)

print("CREATE TABLE IF NOT EXISTS executed safely.")


# =============================================================================
# 5. COLUMN DEFINITIONS
# =============================================================================
#
# A column definition generally contains:
#
# column_name data_type constraint1 constraint2 ...
#
# Example:
#
# employee_id INTEGER PRIMARY KEY
#
# employee_id -> column name
# INTEGER     -> intended data type
# PRIMARY KEY -> constraint
#
# Another example:
#
# email TEXT NOT NULL UNIQUE
#
# email    -> column name
# TEXT     -> text type
# NOT NULL -> value is required
# UNIQUE   -> duplicate values are not allowed


print_section("4. COLUMN DEFINITIONS")

connection.execute(
    """
    CREATE TABLE employees_basic (
        employee_id INTEGER,
        full_name TEXT NOT NULL,
        email TEXT,
        salary REAL,
        active INTEGER
    )
    """
)

connection.execute(
    """
    INSERT INTO employees_basic
        (employee_id, full_name, email, salary, active)
    VALUES
        (?, ?, ?, ?, ?)
    """,
    (101, "Ravi Kumar", "ravi@example.com", 75000.50, 1),
)

print_rows(connection.execute("SELECT * FROM employees_basic"))


# =============================================================================
# 6. SQL DATA TYPES
# =============================================================================
#
# Relational databases provide data types to communicate the intended kind of
# information stored in a column.
#
# Common concepts across SQL systems include:
#
# INTEGER / INT
#     Whole numbers.
#
# SMALLINT / BIGINT
#     Smaller or larger integer ranges in databases that distinguish them.
#
# REAL / FLOAT / DOUBLE
#     Approximate floating-point numbers.
#
# DECIMAL / NUMERIC
#     Exact fixed-point numeric values in many database systems.
#     Often preferred for financial calculations.
#
# TEXT / VARCHAR / CHAR
#     Character data.
#
# BOOLEAN
#     Logical true/false values in systems that support a dedicated boolean type.
#
# DATE
#     Calendar date.
#
# TIME
#     Time of day.
#
# TIMESTAMP / DATETIME
#     Date and time.
#
# BLOB / BYTEA
#     Binary data.
#
# SQLite uses dynamic typing and a type-affinity system. Its primary storage
# classes are:
#
# - NULL
# - INTEGER
# - REAL
# - TEXT
# - BLOB
#
# Declared column types still provide useful schema documentation and influence
# SQLite's type affinity.


print_section("5. DATA TYPES")

connection.execute(
    """
    CREATE TABLE data_type_examples (
        integer_value INTEGER,
        real_value REAL,
        text_value TEXT,
        binary_value BLOB,
        nullable_value TEXT
    )
    """
)

connection.execute(
    """
    INSERT INTO data_type_examples (
        integer_value,
        real_value,
        text_value,
        binary_value,
        nullable_value
    )
    VALUES (?, ?, ?, ?, ?)
    """,
    (
        42,
        3.14159,
        "Structured text",
        b"\x00\x01\x02",
        None,
    ),
)

row = connection.execute("SELECT * FROM data_type_examples").fetchone()

print("integer_value:", row["integer_value"], type(row["integer_value"]))
print("real_value:", row["real_value"], type(row["real_value"]))
print("text_value:", row["text_value"], type(row["text_value"]))
print("binary_value:", row["binary_value"], type(row["binary_value"]))
print("nullable_value:", row["nullable_value"], type(row["nullable_value"]))


# =============================================================================
# 7. NULL
# =============================================================================
#
# NULL does not mean:
#
# - zero
# - empty string
# - false
#
# NULL represents missing, unknown, undefined, or inapplicable information.
#
# SQL uses three-valued logic:
#
# TRUE
# FALSE
# UNKNOWN
#
# Comparisons with NULL require IS NULL or IS NOT NULL.
#
# Incorrect:
#
# WHERE column_name = NULL
#
# Correct:
#
# WHERE column_name IS NULL


print_section("6. NULL AND MISSING VALUES")

connection.execute(
    """
    CREATE TABLE nullable_example (
        id INTEGER PRIMARY KEY,
        optional_note TEXT
    )
    """
)

connection.executemany(
    """
    INSERT INTO nullable_example (id, optional_note)
    VALUES (?, ?)
    """,
    [
        (1, "Present"),
        (2, None),
        (3, ""),
    ],
)

print("Rows where optional_note IS NULL:")
print_rows(
    connection.execute(
        """
        SELECT *
        FROM nullable_example
        WHERE optional_note IS NULL
        """
    )
)

print("\nRows where optional_note is an empty string:")
print_rows(
    connection.execute(
        """
        SELECT *
        FROM nullable_example
        WHERE optional_note = ''
        """
    )
)


# =============================================================================
# 8. PRIMARY KEY
# =============================================================================
#
# A primary key uniquely identifies each row.
#
# Important characteristics:
#
# - Unique
# - Not NULL
# - Identifies one row
# - Usually stable
#
# Common designs:
#
# Surrogate key:
#
# id INTEGER PRIMARY KEY
#
# Natural key:
#
# email TEXT PRIMARY KEY
#
# Surrogate keys are often preferred because business values such as names and
# email addresses can change.


print_section("7. PRIMARY KEY")

connection.execute(
    """
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT NOT NULL,
        price REAL NOT NULL
    )
    """
)

connection.execute(
    """
    INSERT INTO products (product_id, product_name, price)
    VALUES (?, ?, ?)
    """,
    (1, "Keyboard", 1499.00),
)

print_rows(connection.execute("SELECT * FROM products"))

print("\nAttempting to insert a duplicate primary key:")

try:
    connection.execute(
        """
        INSERT INTO products (product_id, product_name, price)
        VALUES (?, ?, ?)
        """,
        (1, "Mouse", 799.00),
    )
except sqlite3.IntegrityError as error:
    print("IntegrityError:", error)


# =============================================================================
# 9. INTEGER PRIMARY KEY AND ROWID IN SQLITE
# =============================================================================
#
# In SQLite, an INTEGER PRIMARY KEY column has special behavior.
#
# It is an alias for the internal rowid in ordinary rowid tables.
#
# If a value is omitted, SQLite can generate an integer key automatically.


print_section("8. AUTO-GENERATED INTEGER PRIMARY KEY")

connection.execute(
    """
    CREATE TABLE tasks (
        task_id INTEGER PRIMARY KEY,
        title TEXT NOT NULL
    )
    """
)

connection.execute(
    """
    INSERT INTO tasks (title)
    VALUES (?)
    """,
    ("Learn SQL table creation",),
)

connection.execute(
    """
    INSERT INTO tasks (title)
    VALUES (?)
    """,
    ("Understand constraints",),
)

print_rows(connection.execute("SELECT * FROM tasks"))


# =============================================================================
# 10. AUTOINCREMENT: WHEN IT IS NOT NECESSARY
# =============================================================================
#
# SQLite also supports:
#
# id INTEGER PRIMARY KEY AUTOINCREMENT
#
# AUTOINCREMENT is often misunderstood.
#
# INTEGER PRIMARY KEY already generates a row identifier when a value is omitted.
#
# AUTOINCREMENT changes allocation behavior and prevents reuse of previously used
# rowids under certain circumstances.
#
# It can add overhead and is usually unnecessary unless the application explicitly
# requires that generated identifiers never reuse a previously allocated value.


print_section("9. AUTOINCREMENT")

connection.execute(
    """
    CREATE TABLE audit_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_name TEXT NOT NULL
    )
    """
)

connection.executemany(
    """
    INSERT INTO audit_events (event_name)
    VALUES (?)
    """,
    [
        ("User created"),
        ("Profile updated"),
    ],
)

print_rows(connection.execute("SELECT * FROM audit_events"))


# =============================================================================
# 11. NOT NULL
# =============================================================================
#
# NOT NULL prevents NULL values.
#
# Example:
#
# full_name TEXT NOT NULL
#
# A NOT NULL constraint does not prevent:
#
# - empty strings
# - whitespace-only strings
#
# Additional validation may be necessary when those values are invalid.


print_section("10. NOT NULL")

connection.execute(
    """
    CREATE TABLE required_fields (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    )
    """
)

connection.execute(
    """
    INSERT INTO required_fields (id, name)
    VALUES (?, ?)
    """,
    (1, "Valid Name"),
)

try:
    connection.execute(
        """
        INSERT INTO required_fields (id, name)
        VALUES (?, ?)
        """,
        (2, None),
    )
except sqlite3.IntegrityError as error:
    print("NOT NULL violation:", error)


# =============================================================================
# 12. UNIQUE
# =============================================================================
#
# UNIQUE prevents duplicate values.
#
# Example:
#
# email TEXT UNIQUE
#
# A UNIQUE constraint can also involve multiple columns.


print_section("11. UNIQUE CONSTRAINT")

connection.execute(
    """
    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE
    )
    """
)

connection.execute(
    """
    INSERT INTO users (username, email)
    VALUES (?, ?)
    """,
    ("asha", "asha@example.com"),
)

try:
    connection.execute(
        """
        INSERT INTO users (username, email)
        VALUES (?, ?)
        """,
        ("asha", "different@example.com"),
    )
except sqlite3.IntegrityError as error:
    print("UNIQUE violation:", error)


# =============================================================================
# 13. CHECK CONSTRAINT
# =============================================================================
#
# CHECK validates a logical condition.
#
# Examples:
#
# CHECK (age >= 18)
# CHECK (price >= 0)
# CHECK (status IN ('pending', 'approved', 'rejected'))
#
# CHECK constraints are useful for domain rules that should be enforced by the
# database.


print_section("12. CHECK CONSTRAINT")

connection.execute(
    """
    CREATE TABLE bank_accounts (
        account_id INTEGER PRIMARY KEY,
        account_holder TEXT NOT NULL,
        balance REAL NOT NULL CHECK (balance >= 0)
    )
    """
)

connection.execute(
    """
    INSERT INTO bank_accounts (account_holder, balance)
    VALUES (?, ?)
    """,
    ("Meera Singh", 5000.00),
)

try:
    connection.execute(
        """
        INSERT INTO bank_accounts (account_holder, balance)
        VALUES (?, ?)
        """,
        ("Invalid Account", -100.00),
    )
except sqlite3.IntegrityError as error:
    print("CHECK violation:", error)


# =============================================================================
# 14. DEFAULT VALUES
# =============================================================================
#
# DEFAULT supplies a value when an INSERT statement omits the column.
#
# Examples:
#
# active INTEGER DEFAULT 1
# created_at TEXT DEFAULT CURRENT_TIMESTAMP
# status TEXT DEFAULT 'pending'
#
# Important:
# A DEFAULT value is generally used when the column is omitted.
# Explicitly inserting NULL may produce NULL unless another constraint prevents it.


print_section("13. DEFAULT VALUES")

connection.execute(
    """
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

connection.execute(
    """
    INSERT INTO orders (customer_name)
    VALUES (?)
    """,
    ("Aman Verma",),
)

connection.execute(
    """
    INSERT INTO orders (customer_name, status)
    VALUES (?, ?)
    """,
    ("Neha Gupta", "approved"),
)

print_rows(connection.execute("SELECT * FROM orders"))


# =============================================================================
# 15. COLUMN-LEVEL VS TABLE-LEVEL CONSTRAINTS
# =============================================================================
#
# Column-level constraint:
#
# email TEXT UNIQUE
#
# Table-level constraint:
#
# UNIQUE (first_name, last_name)
#
# Table-level constraints are particularly useful for:
#
# - Composite primary keys
# - Composite unique constraints
# - Named constraints in database systems that support them


print_section("14. COLUMN-LEVEL AND TABLE-LEVEL CONSTRAINTS")

connection.execute(
    """
    CREATE TABLE class_enrollments (
        student_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (student_id, course_id)
    )
    """
)

connection.execute(
    """
    INSERT INTO class_enrollments (student_id, course_id)
    VALUES (?, ?)
    """,
    (1, 101),
)

try:
    connection.execute(
        """
        INSERT INTO class_enrollments (student_id, course_id)
        VALUES (?, ?)
        """,
        (1, 101),
    )
except sqlite3.IntegrityError as error:
    print("Composite PRIMARY KEY violation:", error)


# =============================================================================
# 16. COMPOSITE PRIMARY KEYS
# =============================================================================
#
# A composite primary key contains more than one column.
#
# Example:
#
# PRIMARY KEY (student_id, course_id)
#
# Neither column must be unique individually.
#
# The combination must be unique.
#
# Common use cases:
#
# - Enrollment tables
# - Junction tables
# - Association tables
# - Natural multi-column identifiers


print_section("15. COMPOSITE KEY BEHAVIOR")

connection.execute(
    """
    INSERT INTO class_enrollments (student_id, course_id)
    VALUES (?, ?)
    """,
    (1, 102),
)

connection.execute(
    """
    INSERT INTO class_enrollments (student_id, course_id)
    VALUES (?, ?)
    """,
    (2, 101),
)

print_rows(
    connection.execute(
        """
        SELECT *
        FROM class_enrollments
        ORDER BY student_id, course_id
        """
    )
)


# =============================================================================
# 17. FOREIGN KEYS
# =============================================================================
#
# A foreign key establishes a relationship between tables.
#
# Parent table:
#
# departments
#
# Child table:
#
# employees
#
# Example:
#
# department_id INTEGER REFERENCES departments(department_id)
#
# The child value must correspond to a valid parent value unless the foreign key
# permits NULL.


print_section("16. FOREIGN KEYS")

connection.execute(
    """
    CREATE TABLE departments (
        department_id INTEGER PRIMARY KEY,
        department_name TEXT NOT NULL UNIQUE
    )
    """
)

connection.execute(
    """
    CREATE TABLE employees (
        employee_id INTEGER PRIMARY KEY,
        employee_name TEXT NOT NULL,
        department_id INTEGER,
        FOREIGN KEY (department_id)
            REFERENCES departments(department_id)
    )
    """
)

connection.execute(
    """
    INSERT INTO departments (department_name)
    VALUES (?)
    """,
    ("Engineering",),
)

connection.execute(
    """
    INSERT INTO employees (employee_name, department_id)
    VALUES (?, ?)
    """,
    ("Priya", 1),
)

print_rows(
    connection.execute(
        """
        SELECT
            employees.employee_id,
            employees.employee_name,
            departments.department_name
        FROM employees
        JOIN departments
            ON employees.department_id = departments.department_id
        """
    )
)


# =============================================================================
# 18. FOREIGN KEY VIOLATIONS
# =============================================================================


print_section("17. FOREIGN KEY VALIDATION")

try:
    connection.execute(
        """
        INSERT INTO employees (employee_name, department_id)
        VALUES (?, ?)
        """,
        ("Invalid Employee", 999),
    )
except sqlite3.IntegrityError as error:
    print("Foreign key violation:", error)


# =============================================================================
# 19. REFERENTIAL ACTIONS
# =============================================================================
#
# Foreign keys can define behavior when a referenced parent row changes or is
# deleted.
#
# Common actions:
#
# ON DELETE CASCADE
#     Delete dependent rows automatically.
#
# ON DELETE SET NULL
#     Set the child foreign key to NULL.
#
# ON DELETE RESTRICT
#     Prevent deletion while dependent rows exist.
#
# ON DELETE NO ACTION
#     Database-specific behavior, often similar to restricting invalid changes.
#
# ON UPDATE CASCADE
#     Update dependent foreign key values.
#
# Choice depends on business rules.
#
# CASCADE is convenient but potentially dangerous when deleting important parent
# records because one operation can remove many dependent rows.


print_section("18. ON DELETE CASCADE")

connection.execute(
    """
    CREATE TABLE projects (
        project_id INTEGER PRIMARY KEY,
        project_name TEXT NOT NULL
    )
    """
)

connection.execute(
    """
    CREATE TABLE project_tasks (
        task_id INTEGER PRIMARY KEY,
        project_id INTEGER NOT NULL,
        task_name TEXT NOT NULL,
        FOREIGN KEY (project_id)
            REFERENCES projects(project_id)
            ON DELETE CASCADE
    )
    """
)

connection.execute(
    """
    INSERT INTO projects (project_name)
    VALUES (?)
    """,
    ("Website Redesign",),
)

connection.executemany(
    """
    INSERT INTO project_tasks (project_id, task_name)
    VALUES (?, ?)
    """,
    [
        (1, "Create schema"),
        (1, "Build interface"),
    ],
)

print("Tasks before deleting project:")
print_rows(connection.execute("SELECT * FROM project_tasks"))

connection.execute("DELETE FROM projects WHERE project_id = 1")

print("\nTasks after deleting project with ON DELETE CASCADE:")
print_rows(connection.execute("SELECT * FROM project_tasks"))


# =============================================================================
# 20. COMPOSITE UNIQUE CONSTRAINTS
# =============================================================================
#
# A composite UNIQUE constraint requires the combination of values to be unique.
#
# Example:
#
# UNIQUE (building, room_number)
#
# The same room number can exist in different buildings.
# The same building can contain multiple room numbers.
# The exact pair cannot be duplicated.


print_section("19. COMPOSITE UNIQUE CONSTRAINT")

connection.execute(
    """
    CREATE TABLE classrooms (
        classroom_id INTEGER PRIMARY KEY,
        building TEXT NOT NULL,
        room_number TEXT NOT NULL,
        UNIQUE (building, room_number)
    )
    """
)

connection.execute(
    """
    INSERT INTO classrooms (building, room_number)
    VALUES (?, ?)
    """,
    ("A", "101"),
)

connection.execute(
    """
    INSERT INTO classrooms (building, room_number)
    VALUES (?, ?)
    """,
    ("B", "101"),
)

try:
    connection.execute(
        """
        INSERT INTO classrooms (building, room_number)
        VALUES (?, ?)
        """,
        ("A", "101"),
    )
except sqlite3.IntegrityError as error:
    print("Composite UNIQUE violation:", error)


# =============================================================================
# 21. NAMING CONVENTIONS
# =============================================================================
#
# SQL identifiers include:
#
# - Database names
# - Table names
# - Column names
# - Constraint names in systems supporting named constraints
#
# Good naming principles:
#
# - Use descriptive names.
# - Keep names consistent.
# - Avoid ambiguous abbreviations.
# - Avoid unnecessary reserved words.
# - Choose one convention, such as snake_case.
#
# Example:
#
# employee_id
# created_at
# shipping_address
#
# Less clear:
#
# empid
# dt
# val
#
# Naming conventions should improve readability across queries, migrations,
# application code, and operational documentation.


print_section("20. NAMING CONVENTIONS")

connection.execute(
    """
    CREATE TABLE customer_orders_example (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        order_status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

print("Created table using descriptive snake_case identifiers.")


# =============================================================================
# 22. QUOTED IDENTIFIERS
# =============================================================================
#
# Identifiers sometimes require quoting because of:
#
# - Spaces
# - Reserved words
# - Special characters
#
# Example:
#
# "order"
#
# Although quoting can be necessary, names requiring constant quoting can make SQL
# harder to maintain.
#
# Parameter placeholders cannot be used for identifiers.
#
# This is valid:
#
# WHERE username = ?
#
# This is not an identifier parameterization mechanism:
#
# CREATE TABLE ? (...)
#
# Dynamic identifiers require careful validation because string interpolation of
# untrusted identifiers can create SQL injection vulnerabilities.


print_section("21. QUOTED IDENTIFIERS")

connection.execute(
    """
    CREATE TABLE "sales report" (
        "record id" INTEGER PRIMARY KEY,
        "total amount" REAL
    )
    """
)

connection.execute(
    """
    INSERT INTO "sales report" ("record id", "total amount")
    VALUES (?, ?)
    """,
    (1, 999.99),
)

print_rows(connection.execute('SELECT * FROM "sales report"'))


# =============================================================================
# 23. TEMPORARY TABLES
# =============================================================================
#
# Temporary tables are scoped to a database connection.
#
# Typical uses:
#
# - Intermediate processing
# - Session-specific calculations
# - Complex transformations
#
# Syntax:
#
# CREATE TEMP TABLE table_name (...)


print_section("22. TEMPORARY TABLES")

connection.execute(
    """
    CREATE TEMP TABLE temporary_calculations (
        value INTEGER
    )
    """
)

connection.executemany(
    """
    INSERT INTO temporary_calculations (value)
    VALUES (?)
    """,
    [(10,), (20,), (30,)],
)

print_rows(connection.execute("SELECT * FROM temporary_calculations"))


# =============================================================================
# 24. CREATE TABLE AS SELECT
# =============================================================================
#
# CREATE TABLE AS SELECT creates a new table from query results.
#
# Example:
#
# CREATE TABLE archived_orders AS
# SELECT ...
# FROM orders;
#
# Important distinction:
#
# This creates columns based on the query result, but constraints, indexes,
# triggers, and some metadata from source tables are generally not copied as a
# complete schema definition.
#
# It is useful for derived or snapshot data, but not always appropriate as a
# production replacement for a carefully designed schema.


print_section("23. CREATE TABLE AS SELECT")

connection.execute(
    """
    CREATE TABLE active_users AS
    SELECT
        user_id,
        username,
        email
    FROM users
    """
)

print_rows(connection.execute("SELECT * FROM active_users"))


# =============================================================================
# 25. GENERATED COLUMNS
# =============================================================================
#
# Generated columns calculate their values from other columns.
#
# SQLite supports generated columns with expressions.
#
# Example:
#
# full_name TEXT GENERATED ALWAYS AS (first_name || ' ' || last_name)
#
# This reduces duplication when a value can be derived reliably.
#
# Design caution:
# Avoid storing data redundantly when it can be safely derived, unless deliberate
# denormalization provides a justified performance or operational benefit.


print_section("24. GENERATED COLUMNS")

connection.execute(
    """
    CREATE TABLE people (
        person_id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name TEXT GENERATED ALWAYS AS (
            first_name || ' ' || last_name
        ) STORED
    )
    """
)

connection.execute(
    """
    INSERT INTO people (first_name, last_name)
    VALUES (?, ?)
    """,
    ("Anita", "Sharma"),
)

print_rows(connection.execute("SELECT * FROM people"))


# =============================================================================
# 26. DATA TYPE DESIGN: APPROXIMATE VS EXACT NUMBERS
# =============================================================================
#
# Floating-point values can have representation limitations.
#
# Example:
#
# 0.1 + 0.2
#
# may not produce an exact binary floating-point representation of 0.3.
#
# Financial systems often use:
#
# - DECIMAL / NUMERIC in databases supporting exact fixed-point arithmetic
# - Integer smallest units, such as paise or cents
#
# SQLite does not provide a dedicated fixed-precision DECIMAL storage class.
#
# A common SQLite strategy is storing money in the smallest currency unit.


print_section("25. FINANCIAL VALUE DESIGN")

connection.execute(
    """
    CREATE TABLE product_prices (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT NOT NULL,
        price_paise INTEGER NOT NULL CHECK (price_paise >= 0)
    )
    """
)

connection.execute(
    """
    INSERT INTO product_prices (product_name, price_paise)
    VALUES (?, ?)
    """,
    ("Notebook", 49950),
)

row = connection.execute(
    """
    SELECT product_name, price_paise
    FROM product_prices
    """
).fetchone()

print(
    f"{row['product_name']}: "
    f"{row['price_paise'] / 100:.2f} currency units"
)


# =============================================================================
# 27. DATE AND TIME DESIGN
# =============================================================================
#
# Database systems differ in native date/time support.
#
# Important design questions:
#
# - Is a value only a date?
# - Does it require a timezone?
# - Is it an instant in time?
# - Is local time important?
#
# Common production practice:
#
# - Store instants consistently, often in UTC.
# - Convert for presentation at application boundaries.
# - Document the representation clearly.
#
# SQLite commonly stores date/time information as:
#
# - TEXT
# - INTEGER Unix timestamps
# - REAL Julian day numbers
#
# The correct choice depends on application requirements.


print_section("26. DATE AND TIME COLUMNS")

connection.execute(
    """
    CREATE TABLE events (
        event_id INTEGER PRIMARY KEY,
        event_name TEXT NOT NULL,
        event_date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

connection.execute(
    """
    INSERT INTO events (event_name, event_date)
    VALUES (?, ?)
    """,
    ("Database Workshop", "2026-09-07"),
)

print_rows(connection.execute("SELECT * FROM events"))


# =============================================================================
# 28. BOOLEAN DESIGN
# =============================================================================
#
# Database systems represent boolean values differently.
#
# SQLite does not have a separate BOOLEAN storage class.
#
# A common convention is:
#
# 0 -> false
# 1 -> true
#
# A CHECK constraint can restrict valid values.


print_section("27. BOOLEAN-LIKE VALUES")

connection.execute(
    """
    CREATE TABLE subscriptions (
        subscription_id INTEGER PRIMARY KEY,
        customer_name TEXT NOT NULL,
        is_active INTEGER NOT NULL
            DEFAULT 1
            CHECK (is_active IN (0, 1))
    )
    """
)

connection.execute(
    """
    INSERT INTO subscriptions (customer_name)
    VALUES (?)
    """,
    ("Karan",),
)

try:
    connection.execute(
        """
        INSERT INTO subscriptions (customer_name, is_active)
        VALUES (?, ?)
        """,
        ("Invalid Boolean", 7),
    )
except sqlite3.IntegrityError as error:
    print("Boolean CHECK violation:", error)

print_rows(connection.execute("SELECT * FROM subscriptions"))


# =============================================================================
# 29. ENUM-LIKE DESIGN
# =============================================================================
#
# Some database systems provide ENUM types.
#
# SQLite can represent controlled values using:
#
# CHECK (status IN ('pending', 'paid', 'cancelled'))
#
# Advantages:
#
# - Simple
# - Schema-level validation
#
# Limitations:
#
# - Changing allowed values requires schema modification.
#
# For complex or frequently changing categories, a separate lookup table can be
# more flexible.


print_section("28. ENUM-LIKE CHECK CONSTRAINT")

connection.execute(
    """
    CREATE TABLE payments (
        payment_id INTEGER PRIMARY KEY,
        amount INTEGER NOT NULL CHECK (amount > 0),
        status TEXT NOT NULL
            CHECK (status IN ('pending', 'paid', 'failed'))
    )
    """
)

connection.execute(
    """
    INSERT INTO payments (amount, status)
    VALUES (?, ?)
    """,
    (2500, "pending"),
)

try:
    connection.execute(
        """
        INSERT INTO payments (amount, status)
        VALUES (?, ?)
        """,
        (2500, "unknown"),
    )
except sqlite3.IntegrityError as error:
    print("Invalid status:", error)


# =============================================================================
# 30. LOOKUP TABLE DESIGN
# =============================================================================
#
# A lookup table can represent controlled categories relationally.
#
# Advantages:
#
# - Centralized definitions
# - Additional metadata
# - Referential integrity
# - Easier category expansion through data changes
#
# Example:
#
# order_statuses
#     status_code PRIMARY KEY
#
# orders
#     status_code FOREIGN KEY


print_section("29. LOOKUP TABLE")

connection.execute(
    """
    CREATE TABLE order_statuses (
        status_code TEXT PRIMARY KEY,
        display_name TEXT NOT NULL UNIQUE
    )
    """
)

connection.executemany(
    """
    INSERT INTO order_statuses (status_code, display_name)
    VALUES (?, ?)
    """,
    [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("CANCELLED", "Cancelled"),
    ],
)

connection.execute(
    """
    CREATE TABLE relational_orders (
        order_id INTEGER PRIMARY KEY,
        customer_name TEXT NOT NULL,
        status_code TEXT NOT NULL,
        FOREIGN KEY (status_code)
            REFERENCES order_statuses(status_code)
    )
    """
)

connection.execute(
    """
    INSERT INTO relational_orders (customer_name, status_code)
    VALUES (?, ?)
    """,
    ("Divya", "PAID"),
)

print_rows(
    connection.execute(
        """
        SELECT
            relational_orders.order_id,
            relational_orders.customer_name,
            order_statuses.display_name
        FROM relational_orders
        JOIN order_statuses
            ON relational_orders.status_code = order_statuses.status_code
        """
    )
)


# =============================================================================
# 31. NORMALIZATION AND TABLE STRUCTURE
# =============================================================================
#
# Normalization organizes relational data to reduce unnecessary duplication and
# improve consistency.
#
# Example of a problematic design:
#
# orders
#
# order_id
# customer_name
# customer_email
# product_1
# product_2
# product_3
#
# Problems:
#
# - Repeating groups
# - Difficult querying
# - Arbitrary maximum number of products
# - Update anomalies
#
# A normalized structure separates entities:
#
# customers
# orders
# products
# order_items
#
# Each table has a specific responsibility.


print_section("30. NORMALIZED TABLE DESIGN")

connection.execute(
    """
    CREATE TABLE normalized_customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE
    )
    """
)

connection.execute(
    """
    CREATE TABLE normalized_products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT NOT NULL,
        price_paise INTEGER NOT NULL CHECK (price_paise >= 0)
    )
    """
)

connection.execute(
    """
    CREATE TABLE normalized_orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id)
            REFERENCES normalized_customers(customer_id)
    )
    """
)

connection.execute(
    """
    CREATE TABLE order_items (
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        PRIMARY KEY (order_id, product_id),
        FOREIGN KEY (order_id)
            REFERENCES normalized_orders(order_id)
            ON DELETE CASCADE,
        FOREIGN KEY (product_id)
            REFERENCES normalized_products(product_id)
    )
    """
)

print("Created normalized customer, product, order, and order_items tables.")


# =============================================================================
# 32. ONE-TO-ONE, ONE-TO-MANY, AND MANY-TO-MANY RELATIONSHIPS
# =============================================================================
#
# One-to-one:
#
# users -> user_profiles
#
# A UNIQUE foreign key can enforce that one profile belongs to at most one user.
#
# One-to-many:
#
# departments -> employees
#
# One department can have many employees.
#
# Many-to-many:
#
# students <-> courses
#
# A junction table stores relationships.


print_section("31. RELATIONSHIP TYPES")

connection.execute(
    """
    CREATE TABLE profile_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE
    )
    """
)

connection.execute(
    """
    CREATE TABLE user_profiles (
        profile_id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL UNIQUE,
        biography TEXT,
        FOREIGN KEY (user_id)
            REFERENCES profile_users(user_id)
            ON DELETE CASCADE
    )
    """
)

print("One-to-one relationship demonstrated using UNIQUE(user_id).")


# =============================================================================
# 33. TABLE STRUCTURE INSPECTION
# =============================================================================
#
# Database systems provide metadata facilities.
#
# SQLite supports:
#
# PRAGMA table_info(table_name)
#
# Useful metadata includes:
#
# - Column names
# - Declared types
# - Nullability
# - Default values
# - Primary key positions


print_section("32. INSPECTING TABLE STRUCTURE")

print_rows(
    connection.execute(
        """
        PRAGMA table_info(products)
        """
    )
)


# =============================================================================
# 34. VIEWING THE ORIGINAL CREATE TABLE STATEMENT
# =============================================================================
#
# SQLite stores schema SQL in sqlite_master.
#
# This is useful for understanding how a table was actually created.


print_section("33. VIEWING TABLE CREATION SQL")

row = connection.execute(
    """
    SELECT sql
    FROM sqlite_master
    WHERE type = 'table'
      AND name = 'products'
    """
).fetchone()

print(row["sql"])


# =============================================================================
# 35. ALTERING TABLES
# =============================================================================
#
# CREATE TABLE defines a new table.
#
# ALTER TABLE changes an existing table.
#
# SQLite supports a subset of schema alterations compared with some enterprise
# databases.
#
# Common operations include:
#
# ALTER TABLE table_name ADD COLUMN column_definition
#
# Production schema changes require careful migration planning because:
#
# - Existing data must remain valid.
# - Applications may expect the old schema.
# - Large table changes may be expensive.
# - Rollback may be difficult.


print_section("34. ALTER TABLE")

connection.execute(
    """
    ALTER TABLE products
    ADD COLUMN description TEXT
    """
)

connection.execute(
    """
    UPDATE products
    SET description = ?
    WHERE product_id = ?
    """,
    ("Mechanical keyboard", 1),
)

print_rows(connection.execute("SELECT * FROM products"))


# =============================================================================
# 36. CREATE TABLE ERRORS
# =============================================================================
#
# Common table creation problems:
#
# - Duplicate table names
# - Invalid syntax
# - Missing commas
# - Unsupported data types or features
# - Incorrect constraint definitions
# - Reserved words used improperly
# - Foreign key references to unsuitable columns
#
# Python should handle database exceptions rather than assuming every SQL statement
# succeeds.


print_section("35. ERROR HANDLING DURING TABLE CREATION")

try:
    connection.execute(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY
        )
        """
    )
except sqlite3.OperationalError as error:
    print("OperationalError:", error)


# =============================================================================
# 37. TRANSACTIONS
# =============================================================================
#
# A transaction groups related operations.
#
# ACID properties are commonly associated with relational transactions:
#
# Atomicity
#     A transaction completes entirely or is rolled back.
#
# Consistency
#     Database constraints help preserve valid states.
#
# Isolation
#     Concurrent transactions should behave according to the database's isolation
#     guarantees.
#
# Durability
#     Committed changes survive failures according to database configuration.
#
# Python's connection context manager can be used for transaction control.


print_section("36. TRANSACTIONS")

connection.execute(
    """
    CREATE TABLE transaction_example (
        id INTEGER PRIMARY KEY,
        value TEXT NOT NULL
    )
    """
)

try:
    with connection:
        connection.execute(
            """
            INSERT INTO transaction_example (id, value)
            VALUES (?, ?)
            """,
            (1, "First"),
        )

        connection.execute(
            """
            INSERT INTO transaction_example (id, value)
            VALUES (?, ?)
            """,
            (1, "Duplicate primary key"),
        )
except sqlite3.IntegrityError as error:
    print("Transaction rolled back due to:", error)

print("Rows after failed transaction:")
print_rows(connection.execute("SELECT * FROM transaction_example"))


# =============================================================================
# 38. PARAMETERIZED SQL
# =============================================================================
#
# SQL values should generally be supplied using parameters.
#
# Safe pattern:
#
# cursor.execute(
#     "INSERT INTO users (username) VALUES (?)",
#     (username,)
# )
#
# Unsafe pattern:
#
# sql = "INSERT INTO users VALUES ('" + username + "')"
#
# String concatenation can create SQL injection vulnerabilities.
#
# Parameterization applies to values, not arbitrary SQL identifiers or SQL syntax.


print_section("37. PARAMETERIZED INSERTS")

connection.execute(
    """
    CREATE TABLE secure_input_example (
        id INTEGER PRIMARY KEY,
        user_input TEXT NOT NULL
    )
    """
)

untrusted_input = "Robert'); DROP TABLE secure_input_example; --"

connection.execute(
    """
    INSERT INTO secure_input_example (user_input)
    VALUES (?)
    """,
    (untrusted_input,),
)

print_rows(connection.execute("SELECT * FROM secure_input_example"))


# =============================================================================
# 39. VALIDATING DYNAMIC IDENTIFIERS
# =============================================================================
#
# Parameter placeholders cannot represent table names.
#
# If an application must construct SQL dynamically using identifiers, the
# identifiers should come from trusted constants or strict allow-lists.


print_section("38. SAFE DYNAMIC IDENTIFIER SELECTION")

allowed_tables = {
    "users": "users",
    "products": "products",
    "orders": "orders",
}


def count_rows_in_allowed_table(
    database_connection: sqlite3.Connection,
    requested_table: str,
) -> int:
    """
    Count rows in a table selected from a fixed allow-list.

    The identifier is never taken directly from arbitrary user input.
    """
    if requested_table not in allowed_tables:
        raise ValueError(f"Table is not allowed: {requested_table}")

    safe_table_name = allowed_tables[requested_table]

    sql = f"SELECT COUNT(*) AS row_count FROM {safe_table_name}"

    row = database_connection.execute(sql).fetchone()
    return int(row["row_count"])


print("Rows in products:", count_rows_in_allowed_table(connection, "products"))

try:
    count_rows_in_allowed_table(
        connection,
        "products; DROP TABLE users; --",
    )
except ValueError as error:
    print("Rejected unsafe identifier:", error)


# =============================================================================
# 40. INDEXES AND TABLE DESIGN
# =============================================================================
#
# Indexes are separate database structures that can improve query performance.
#
# CREATE INDEX:
#
# CREATE INDEX index_name
# ON table_name(column_name);
#
# Constraints such as PRIMARY KEY and UNIQUE may create supporting indexes,
# depending on the database system.
#
# Index trade-offs:
#
# Benefits:
# - Faster searches
# - Faster joins
# - Faster ordered retrieval in suitable cases
#
# Costs:
# - Additional storage
# - Slower inserts
# - Slower updates
# - Slower deletes
#
# Table design should consider expected access patterns.


print_section("39. INDEXES")

connection.execute(
    """
    CREATE INDEX idx_employees_department_id
    ON employees(department_id)
    """
)

print("Created index on employees(department_id).")


# =============================================================================
# 41. EXPLAIN QUERY PLAN
# =============================================================================
#
# SQLite can display query planning information.
#
# This helps investigate whether indexes and query structures are being used as
# expected.
#
# Query plans should be interpreted in context. A query plan is not automatically
# proof that a design is optimal.


print_section("40. QUERY PLAN")

print_rows(
    connection.execute(
        """
        EXPLAIN QUERY PLAN
        SELECT *
        FROM employees
        WHERE department_id = 1
        """
    )
)


# =============================================================================
# 42. CONSTRAINTS VS APPLICATION VALIDATION
# =============================================================================
#
# Application validation and database constraints serve different purposes.
#
# Application validation:
#
# - Better user feedback
# - Domain-specific validation logic
# - Convenient input handling
#
# Database constraints:
#
# - Protect data regardless of which application writes it
# - Enforce shared invariants
# - Protect against accidental invalid writes
#
# Critical data rules are often enforced at both levels.


print_section("41. APPLICATION AND DATABASE VALIDATION")


def validate_product_input(
    product_name: str,
    price_paise: int,
) -> None:
    """Validate application-level business rules."""
    if not product_name.strip():
        raise ValueError("Product name must not be empty.")

    if price_paise < 0:
        raise ValueError("Price must not be negative.")


try:
    validate_product_input("   ", 100)
except ValueError as error:
    print("Application validation:", error)


# =============================================================================
# 43. DATACLASSES AND TABLE DESIGN
# =============================================================================
#
# Python dataclasses can model application-level records.
#
# A dataclass does not automatically create a database table.
#
# Object models and relational schemas are related but distinct:
#
# - Objects represent application structures.
# - Tables represent relational storage.
#
# Object-relational mapping frameworks automate some translation, but understanding
# SQL table structure remains important.


print_section("42. PYTHON DATA MODEL AND TABLE MODEL")


@dataclass
class Customer:
    customer_id: Optional[int]
    name: str
    email: str


customer = Customer(
    customer_id=None,
    name="Sonia",
    email="sonia@example.com",
)

print(customer)


# =============================================================================
# 44. SCHEMA DESIGN EXAMPLE: A COMPLETE BLOG SYSTEM
# =============================================================================
#
# This example combines multiple concepts:
#
# users
# posts
# comments
# tags
# post_tags
#
# Relationships:
#
# users 1 -> many posts
# users 1 -> many comments
# posts 1 -> many comments
# posts many <-> many tags


print_section("43. COMPLETE MULTI-TABLE SCHEMA")

connection.execute(
    """
    CREATE TABLE blog_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

connection.execute(
    """
    CREATE TABLE blog_posts (
        post_id INTEGER PRIMARY KEY,
        author_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        published INTEGER NOT NULL DEFAULT 0 CHECK (published IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (author_id)
            REFERENCES blog_users(user_id)
            ON DELETE CASCADE
    )
    """
)

connection.execute(
    """
    CREATE TABLE blog_comments (
        comment_id INTEGER PRIMARY KEY,
        post_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        body TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id)
            REFERENCES blog_posts(post_id)
            ON DELETE CASCADE,
        FOREIGN KEY (author_id)
            REFERENCES blog_users(user_id)
            ON DELETE CASCADE
    )
    """
)

connection.execute(
    """
    CREATE TABLE blog_tags (
        tag_id INTEGER PRIMARY KEY,
        tag_name TEXT NOT NULL UNIQUE
    )
    """
)

connection.execute(
    """
    CREATE TABLE blog_post_tags (
        post_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        PRIMARY KEY (post_id, tag_id),
        FOREIGN KEY (post_id)
            REFERENCES blog_posts(post_id)
            ON DELETE CASCADE,
        FOREIGN KEY (tag_id)
            REFERENCES blog_tags(tag_id)
            ON DELETE CASCADE
    )
    """
)

print("Created complete relational blog schema.")


# =============================================================================
# 45. POPULATING THE BLOG SCHEMA
# =============================================================================


print_section("44. POPULATING RELATED TABLES")

connection.execute(
    """
    INSERT INTO blog_users (username, email)
    VALUES (?, ?)
    """,
    ("database_student", "student@example.com"),
)

connection.execute(
    """
    INSERT INTO blog_posts (author_id, title, body, published)
    VALUES (?, ?, ?, ?)
    """,
    (
        1,
        "Creating Strong Table Schemas",
        "Table definitions establish the structural rules of relational data.",
        1,
    ),
)

connection.executemany(
    """
    INSERT INTO blog_tags (tag_name)
    VALUES (?)
    """,
    [
        ("SQL",),
        ("Database Design",),
    ],
)

connection.executemany(
    """
    INSERT INTO blog_post_tags (post_id, tag_id)
    VALUES (?, ?)
    """,
    [
        (1, 1),
        (1, 2),
    ],
)

print_rows(
    connection.execute(
        """
        SELECT
            blog_posts.title,
            blog_tags.tag_name
        FROM blog_post_tags
        JOIN blog_posts
            ON blog_post_tags.post_id = blog_posts.post_id
        JOIN blog_tags
            ON blog_post_tags.tag_id = blog_tags.tag_id
        ORDER BY blog_tags.tag_name
        """
    )
)


# =============================================================================
# 46. SELF-REFERENTIAL TABLES
# =============================================================================
#
# A table can reference itself.
#
# Example:
#
# employees
#
# employee_id
# manager_id -> employees.employee_id
#
# This can model organizational hierarchies.


print_section("45. SELF-REFERENTIAL FOREIGN KEY")

connection.execute(
    """
    CREATE TABLE organization_employees (
        employee_id INTEGER PRIMARY KEY,
        employee_name TEXT NOT NULL,
        manager_id INTEGER,
        FOREIGN KEY (manager_id)
            REFERENCES organization_employees(employee_id)
            ON DELETE SET NULL
    )
    """
)

connection.execute(
    """
    INSERT INTO organization_employees (employee_name, manager_id)
    VALUES (?, ?)
    """,
    ("CEO", None),
)

connection.execute(
    """
    INSERT INTO organization_employees (employee_name, manager_id)
    VALUES (?, ?)
    """,
    ("Engineering Manager", 1),
)

connection.execute(
    """
    INSERT INTO organization_employees (employee_name, manager_id)
    VALUES (?, ?)
    """,
    ("Developer", 2),
)

print_rows(
    connection.execute(
        """
        SELECT *
        FROM organization_employees
        """
    )
)


# =============================================================================
# 47. DEFERRABLE CONSTRAINT CONCEPTS
# =============================================================================
#
# Some database systems support deferred constraint checking.
#
# The idea is that temporary intermediate states may exist inside a transaction,
# provided that all constraints are valid when the transaction is committed.
#
# SQLite supports deferrable foreign keys.
#
# This is useful when mutually dependent records must be inserted as part of one
# transaction.


print_section("46. DEFERRABLE FOREIGN KEY")

connection.execute(
    """
    CREATE TABLE deferred_parent (
        id INTEGER PRIMARY KEY,
        child_id INTEGER,
        FOREIGN KEY (child_id)
            REFERENCES deferred_child(id)
            DEFERRABLE INITIALLY DEFERRED
    )
    """
)

connection.execute(
    """
    CREATE TABLE deferred_child (
        id INTEGER PRIMARY KEY
    )
    """
)

# The parent references a child before that child exists.
# Because the foreign key is deferred, the final transaction state is checked
# rather than requiring immediate validity after every statement.

with connection:
    connection.execute(
        """
        INSERT INTO deferred_parent (id, child_id)
        VALUES (?, ?)
        """,
        (1, 10),
    )

    connection.execute(
        """
        INSERT INTO deferred_child (id)
        VALUES (?)
        """,
        (10,),
    )

print("Deferred foreign key transaction committed successfully.")


# =============================================================================
# 48. STRICT TABLES IN SQLITE
# =============================================================================
#
# SQLite historically permits flexible typing.
#
# Modern SQLite versions support STRICT tables, which provide stronger type
# enforcement for supported column types.
#
# STRICT mode is SQLite-specific and may not be available in very old SQLite
# versions.
#
# To keep this study script portable across many Python installations, the feature
# is attempted conditionally.


print_section("47. SQLITE STRICT TABLES")

try:
    connection.execute(
        """
        CREATE TABLE strict_example (
            id INTEGER PRIMARY KEY,
            quantity INTEGER NOT NULL,
            description TEXT
        ) STRICT
        """
    )

    connection.execute(
        """
        INSERT INTO strict_example (quantity, description)
        VALUES (?, ?)
        """,
        (5, "Valid strict row"),
    )

    print("STRICT table created successfully.")

except sqlite3.OperationalError as error:
    print("STRICT tables are unavailable in this SQLite version:", error)


# =============================================================================
# 49. SCHEMA VERSIONING CONCEPT
# =============================================================================
#
# Production databases evolve.
#
# Typical changes include:
#
# - New tables
# - New columns
# - New indexes
# - New constraints
# - Data migrations
#
# Rather than manually changing production schemas, applications commonly use
# versioned migrations.
#
# A simple schema version table can record migration state.


print_section("48. SCHEMA VERSIONING CONCEPT")

connection.execute(
    """
    CREATE TABLE schema_migrations (
        version INTEGER PRIMARY KEY,
        description TEXT NOT NULL,
        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

connection.execute(
    """
    INSERT INTO schema_migrations (version, description)
    VALUES (?, ?)
    """,
    (1, "Initial schema demonstration"),
)

print_rows(connection.execute("SELECT * FROM schema_migrations"))


# =============================================================================
# 50. IDEMPOTENT SCHEMA INITIALIZATION
# =============================================================================
#
# An initialization function can safely ensure that required tables exist.
#
# IF NOT EXISTS helps avoid errors during repeated initialization.
#
# Important limitation:
# It does not upgrade an existing incompatible schema.
#
# Production systems normally combine initialization logic with explicit migrations.


print_section("49. IDEMPOTENT SCHEMA INITIALIZATION")


def initialize_inventory_schema(
    database_connection: sqlite3.Connection,
) -> None:
    """Create an inventory table if it does not already exist."""
    database_connection.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL UNIQUE,
            quantity INTEGER NOT NULL DEFAULT 0
                CHECK (quantity >= 0),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


initialize_inventory_schema(connection)
initialize_inventory_schema(connection)

print("Inventory schema initialized repeatedly without creation errors.")


# =============================================================================
# 51. EDGE CASE: EMPTY STRINGS VS NULL
# =============================================================================


print_section("50. EMPTY STRING VS NULL")

connection.execute(
    """
    CREATE TABLE text_edge_cases (
        id INTEGER PRIMARY KEY,
        value TEXT
    )
    """
)

connection.executemany(
    """
    INSERT INTO text_edge_cases (value)
    VALUES (?)
    """,
    [
        (None,),
        ("",),
        (" ",),
        ("text",),
    ],
)

print_rows(
    connection.execute(
        """
        SELECT
            id,
            value,
            CASE
                WHEN value IS NULL THEN 'NULL'
                WHEN value = '' THEN 'EMPTY STRING'
                WHEN value = ' ' THEN 'SPACE'
                ELSE 'TEXT'
            END AS classification
        FROM text_edge_cases
        """
    )
)


# =============================================================================
# 52. EDGE CASE: CHECK AND NULL
# =============================================================================
#
# CHECK expressions deserve careful attention when nullable columns are involved.
#
# SQL conditions involving NULL can evaluate to UNKNOWN.
#
# A CHECK constraint typically rejects FALSE conditions, while NULL/UNKNOWN behavior
# can require explicit NOT NULL constraints when a value must exist.


print_section("51. CHECK CONSTRAINT WITH NULL")

connection.execute(
    """
    CREATE TABLE nullable_check_example (
        id INTEGER PRIMARY KEY,
        score INTEGER CHECK (score >= 0)
    )
    """
)

connection.execute(
    """
    INSERT INTO nullable_check_example (score)
    VALUES (?)
    """,
    (None,),
)

print_rows(connection.execute("SELECT * FROM nullable_check_example"))

print(
    "NULL was accepted because the column is nullable. "
    "Use NOT NULL when the value is mandatory."
)


# =============================================================================
# 53. COMMON MISTAKE: USING BUSINESS DATA AS A PRIMARY KEY
# =============================================================================
#
# Natural keys can be appropriate, but mutable business values create risks.
#
# Example:
#
# email TEXT PRIMARY KEY
#
# Email addresses can change.
#
# A surrogate key plus UNIQUE(email) often provides more flexibility.


print_section("52. SURROGATE KEY PLUS UNIQUE BUSINESS VALUE")

connection.execute(
    """
    CREATE TABLE customers_with_surrogate_key (
        customer_id INTEGER PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL
    )
    """
)

connection.execute(
    """
    INSERT INTO customers_with_surrogate_key (email, full_name)
    VALUES (?, ?)
    """,
    ("customer@example.com", "Example Customer"),
)

connection.execute(
    """
    UPDATE customers_with_surrogate_key
    SET email = ?
    WHERE customer_id = ?
    """,
    ("new-email@example.com", 1),
)

print_rows(
    connection.execute(
        """
        SELECT *
        FROM customers_with_surrogate_key
        """
    )
)


# =============================================================================
# 54. COMMON MISTAKE: STORING MULTIPLE VALUES IN ONE COLUMN
# =============================================================================
#
# Problematic example:
#
# skills = "Python,SQL,Excel"
#
# This makes validation, searching, joining, and updates difficult.
#
# A normalized design uses separate tables.


print_section("53. MULTI-VALUE DATA NORMALIZATION")

connection.execute(
    """
    CREATE TABLE skill_users (
        user_id INTEGER PRIMARY KEY,
        user_name TEXT NOT NULL
    )
    """
)

connection.execute(
    """
    CREATE TABLE skills (
        skill_id INTEGER PRIMARY KEY,
        skill_name TEXT NOT NULL UNIQUE
    )
    """
)

connection.execute(
    """
    CREATE TABLE user_skills (
        user_id INTEGER NOT NULL,
        skill_id INTEGER NOT NULL,
        PRIMARY KEY (user_id, skill_id),
        FOREIGN KEY (user_id)
            REFERENCES skill_users(user_id)
            ON DELETE CASCADE,
        FOREIGN KEY (skill_id)
            REFERENCES skills(skill_id)
    )
    """
)

print("Normalized many-to-many skill structure created.")


# =============================================================================
# 55. COMMON MISTAKE: TOO MANY NULLABLE COLUMNS
# =============================================================================
#
# A table containing many unrelated optional columns can indicate multiple entities
# have been combined into one table.
#
# Example:
#
# person
# company_registration_number
# student_roll_number
# employee_salary
#
# If each row represents only one kind of entity, many columns may be irrelevant.
#
# Better designs may use:
#
# - Separate tables
# - Subtype tables
# - Carefully designed inheritance patterns
#
# The correct structure depends on the domain.


print_section("54. TABLE RESPONSIBILITY")

print(
    "A well-designed table should represent a coherent entity or relationship "
    "with columns that belong together."
)


# =============================================================================
# 56. PRODUCTION DESIGN CHECKLIST AS EXECUTABLE DATA
# =============================================================================


print_section("55. TABLE DESIGN CHECKLIST")

table_design_checklist = [
    "Does the table represent one coherent entity or relationship?",
    "Does every table have an appropriate primary key?",
    "Are mandatory values protected with NOT NULL?",
    "Are duplicate business values protected with UNIQUE where required?",
    "Are numeric domains validated with CHECK constraints?",
    "Are foreign key relationships explicitly defined?",
    "Are deletion behaviors chosen according to business rules?",
    "Are date and time representations documented?",
    "Are financial values represented without inappropriate floating-point error?",
    "Are names consistent and descriptive?",
    "Are sensitive values stored only when necessary?",
    "Are expected query patterns considered before adding indexes?",
    "Can schema changes be deployed safely through migrations?",
    "Are application validation and database constraints aligned?",
]

for number, question in enumerate(table_design_checklist, start=1):
    print(f"{number}. {question}")


# =============================================================================
# 57. A REUSABLE TABLE CREATION HELPER
# =============================================================================
#
# The following helper demonstrates careful SQL execution and error handling.
#
# In production, schema management should normally use reviewed migration scripts
# or migration tooling rather than arbitrary runtime SQL construction.


print_section("56. REUSABLE TABLE CREATION HELPER")


def create_table(
    database_connection: sqlite3.Connection,
    table_name: str,
    create_statement: str,
) -> bool:
    """
    Execute a pre-defined CREATE TABLE statement.

    table_name is used only for readable error reporting. The SQL statement itself
    should be a trusted, application-controlled schema definition.
    """
    try:
        database_connection.execute(create_statement)
        print(f"Table '{table_name}' created successfully.")
        return True
    except sqlite3.DatabaseError as error:
        print(f"Failed to create table '{table_name}': {error}")
        return False


create_table(
    connection,
    "categories",
    """
    CREATE TABLE categories (
        category_id INTEGER PRIMARY KEY,
        category_name TEXT NOT NULL UNIQUE
    )
    """,
)


# =============================================================================
# 58. TESTING A TABLE DEFINITION
# =============================================================================
#
# Schema tests should verify:
#
# - Table existence
# - Required columns
# - Constraints
# - Expected successful inserts
# - Expected failures
# - Relationship behavior
#
# The following functions demonstrate simple schema testing.


print_section("57. TESTING TABLE CONSTRAINTS")


def assert_raises_integrity_error(
    database_connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...],
) -> None:
    """Assert that a database operation violates an integrity constraint."""
    try:
        database_connection.execute(sql, parameters)
    except sqlite3.IntegrityError:
        print("Expected integrity error occurred.")
        return

    raise AssertionError("Expected sqlite3.IntegrityError was not raised.")


connection.execute(
    """
    CREATE TABLE tested_table (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity >= 0)
    )
    """
)

connection.execute(
    """
    INSERT INTO tested_table (name, quantity)
    VALUES (?, ?)
    """,
    ("Valid Row", 5),
)

assert_raises_integrity_error(
    connection,
    """
    INSERT INTO tested_table (name, quantity)
    VALUES (?, ?)
    """,
    ("Invalid Row", -1),
)


# =============================================================================
# 59. PRACTICAL COMPLETE EXAMPLE: E-COMMERCE INVENTORY
# =============================================================================
#
# This schema demonstrates:
#
# - Primary keys
# - Foreign keys
# - Unique values
# - Defaults
# - Checks
# - Composite primary keys
# - Normalized structure
# - Inventory quantities
#
# Tables:
#
# suppliers
# inventory_products
# warehouse_locations
# inventory_stock


print_section("58. COMPLETE INVENTORY SCHEMA")

connection.execute(
    """
    CREATE TABLE suppliers (
        supplier_id INTEGER PRIMARY KEY,
        supplier_name TEXT NOT NULL UNIQUE,
        email TEXT UNIQUE,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

connection.execute(
    """
    CREATE TABLE inventory_products (
        product_id INTEGER PRIMARY KEY,
        supplier_id INTEGER NOT NULL,
        sku TEXT NOT NULL UNIQUE,
        product_name TEXT NOT NULL,
        unit_price_paise INTEGER NOT NULL
            CHECK (unit_price_paise >= 0),
        active INTEGER NOT NULL DEFAULT 1
            CHECK (active IN (0, 1)),
        FOREIGN KEY (supplier_id)
            REFERENCES suppliers(supplier_id)
            ON DELETE RESTRICT
    )
    """
)

connection.execute(
    """
    CREATE TABLE warehouse_locations (
        location_id INTEGER PRIMARY KEY,
        location_code TEXT NOT NULL UNIQUE,
        location_name TEXT NOT NULL
    )
    """
)

connection.execute(
    """
    CREATE TABLE inventory_stock (
        product_id INTEGER NOT NULL,
        location_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0
            CHECK (quantity >= 0),
        reorder_level INTEGER NOT NULL DEFAULT 0
            CHECK (reorder_level >= 0),
        PRIMARY KEY (product_id, location_id),
        FOREIGN KEY (product_id)
            REFERENCES inventory_products(product_id)
            ON DELETE CASCADE,
        FOREIGN KEY (location_id)
            REFERENCES warehouse_locations(location_id)
            ON DELETE CASCADE
    )
    """
)

connection.execute(
    """
    INSERT INTO suppliers (supplier_name, email)
    VALUES (?, ?)
    """,
    ("Tech Supplies Ltd", "sales@techsupplies.example"),
)

connection.execute(
    """
    INSERT INTO inventory_products (
        supplier_id,
        sku,
        product_name,
        unit_price_paise
    )
    VALUES (?, ?, ?, ?)
    """,
    (1, "KB-001", "Mechanical Keyboard", 499900),
)

connection.execute(
    """
    INSERT INTO warehouse_locations (
        location_code,
        location_name
    )
    VALUES (?, ?)
    """,
    ("LKO-01", "Primary Warehouse"),
)

connection.execute(
    """
    INSERT INTO inventory_stock (
        product_id,
        location_id,
        quantity,
        reorder_level
    )
    VALUES (?, ?, ?, ?)
    """,
    (1, 1, 25, 10),
)

print_rows(
    connection.execute(
        """
        SELECT
            inventory_products.sku,
            inventory_products.product_name,
            inventory_stock.quantity,
            inventory_stock.reorder_level,
            warehouse_locations.location_code
        FROM inventory_stock
        JOIN inventory_products
            ON inventory_stock.product_id = inventory_products.product_id
        JOIN warehouse_locations
            ON inventory_stock.location_id = warehouse_locations.location_id
        """
    )
)


# =============================================================================
# 60. PERFORMANCE CONSIDERATION: INSERTING MANY ROWS
# =============================================================================
#
# Repeated individual commits can be slower than grouping operations into a
# transaction.
#
# executemany is convenient for repeated parameterized statements.


print_section("59. BULK INSERT CONSIDERATION")

connection.execute(
    """
    CREATE TABLE bulk_example (
        id INTEGER PRIMARY KEY,
        value TEXT NOT NULL
    )
    """
)

bulk_rows = [
    (number, f"Value {number}")
    for number in range(1, 11)
]

with connection:
    connection.executemany(
        """
        INSERT INTO bulk_example (id, value)
        VALUES (?, ?)
        """,
        bulk_rows,
    )

row_count = connection.execute(
    """
    SELECT COUNT(*) AS total
    FROM bulk_example
    """
).fetchone()

print("Inserted rows:", row_count["total"])


# =============================================================================
# 61. SECURITY CONSIDERATION: LEAST PRIVILEGE
# =============================================================================
#
# Production database users should not all have unrestricted permissions.
#
# A read-only service may require SELECT access but should not necessarily have:
#
# - DROP
# - ALTER
# - DELETE
# - unrestricted INSERT
#
# SQLite does not use the same server-side role model as enterprise database
# systems, but the principle remains important for database architecture.


print_section("60. SECURITY DESIGN PRINCIPLE")

print(
    "Production systems should grant database identities only the permissions "
    "required for their responsibilities."
)


# =============================================================================
# 62. PRODUCTION CONSIDERATION: SENSITIVE DATA
# =============================================================================
#
# Table creation determines what data can be stored.
#
# Important questions:
#
# - Is the column necessary?
# - Is the data sensitive?
# - How long should it be retained?
# - Who should access it?
# - Should it be encrypted?
# - Should it be hashed instead of stored directly?
#
# Passwords should not be stored as plain text.
#
# A password_hash column is conceptually different from a password column.


print_section("61. SENSITIVE DATA DESIGN")

connection.execute(
    """
    CREATE TABLE authentication_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

print(
    "Authentication table uses password_hash rather than storing a plain password."
)


# =============================================================================
# 63. TABLE CREATION ORDER
# =============================================================================
#
# When foreign keys are used, parent tables are generally created before child
# tables.
#
# Typical order:
#
# 1. Lookup tables
# 2. Independent entity tables
# 3. Dependent entity tables
# 4. Junction tables
# 5. Supporting indexes
#
# This ordering simplifies schema creation and migration planning.


print_section("62. TABLE CREATION ORDER")

schema_creation_order = [
    "Lookup tables",
    "Independent entity tables",
    "Parent tables",
    "Child tables",
    "Many-to-many junction tables",
    "Additional indexes",
]

for position, item in enumerate(schema_creation_order, start=1):
    print(f"{position}. {item}")


# =============================================================================
# 64. FINAL INTEGRATED EXAMPLE
# =============================================================================
#
# A course management schema combines major CREATE TABLE concepts.


print_section("63. FINAL INTEGRATED COURSE MANAGEMENT SCHEMA")

connection.execute(
    """
    CREATE TABLE courses (
        course_id INTEGER PRIMARY KEY,
        course_code TEXT NOT NULL UNIQUE,
        course_name TEXT NOT NULL,
        duration_hours INTEGER NOT NULL
            CHECK (duration_hours > 0),
        active INTEGER NOT NULL DEFAULT 1
            CHECK (active IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

connection.execute(
    """
    CREATE TABLE course_students (
        student_id INTEGER PRIMARY KEY,
        student_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

connection.execute(
    """
    CREATE TABLE course_registrations (
        student_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        registration_status TEXT NOT NULL DEFAULT 'registered'
            CHECK (
                registration_status IN (
                    'registered',
                    'completed',
                    'cancelled'
                )
            ),
        registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (student_id, course_id),
        FOREIGN KEY (student_id)
            REFERENCES course_students(student_id)
            ON DELETE CASCADE,
        FOREIGN KEY (course_id)
            REFERENCES courses(course_id)
            ON DELETE RESTRICT
    )
    """
)

connection.execute(
    """
    INSERT INTO courses (
        course_code,
        course_name,
        duration_hours
    )
    VALUES (?, ?, ?)
    """,
    ("SQL101", "Creating Tables in SQL", 20),
)

connection.execute(
    """
    INSERT INTO course_students (
        student_name,
        email
    )
    VALUES (?, ?)
    """,
    ("Arjun", "arjun@example.com"),
)

connection.execute(
    """
    INSERT INTO course_registrations (
        student_id,
        course_id
    )
    VALUES (?, ?)
    """,
    (1, 1),
)

print_rows(
    connection.execute(
        """
        SELECT
            course_students.student_name,
            courses.course_code,
            courses.course_name,
            course_registrations.registration_status
        FROM course_registrations
        JOIN course_students
            ON course_registrations.student_id =
               course_students.student_id
        JOIN courses
            ON course_registrations.course_id =
               courses.course_id
        """
    )
)


# =============================================================================
# 65. CLEANUP
# =============================================================================


print_section("64. STUDY SCRIPT COMPLETED")

print(
    "The examples demonstrated how CREATE TABLE defines relational structure "
    "through columns, data types, keys, constraints, relationships, and "
    "production-oriented schema design."
)

connection.close()

print("Database connection closed.")
