"""
INSERT Statements: INSERT, Multiple-Row Insertion, Column Ordering, and Default Values

A self-contained SQL/SQLite study script progressing from absolute beginner to
advanced INSERT concepts.

The script uses Python's built-in sqlite3 module, so no external package is
required.

Run:
    python insert_statements.py
"""

import sqlite3
from pprint import pprint


# =============================================================================
# 1. DATABASE CONNECTION AND HELPER FUNCTIONS
# =============================================================================

def create_connection():
    """Create an in-memory SQLite database for reproducible demonstrations."""
    return sqlite3.connect(":memory:")


def execute_sql(connection, sql, parameters=()):
    """
    Execute one SQL statement safely and commit the transaction.

    Parameterized SQL is preferred whenever values originate outside the SQL
    source itself. It prevents SQL injection and avoids manual quoting errors.
    """
    cursor = connection.execute(sql, parameters)
    connection.commit()
    return cursor


def execute_many(connection, sql, rows):
    """Execute a parameterized statement for multiple rows."""
    cursor = connection.executemany(sql, rows)
    connection.commit()
    return cursor


def print_rows(connection, sql, parameters=(), title=None):
    """Display query results in a readable form."""
    if title:
        print(f"\n--- {title} ---")

    cursor = connection.execute(sql, parameters)
    rows = cursor.fetchall()

    if not rows:
        print("(no rows)")
        return

    column_names = [description[0] for description in cursor.description]
    print(" | ".join(column_names))
    print("-" * (len(" | ".join(column_names)) + 4))

    for row in rows:
        print(" | ".join(str(value) if value is not None else "NULL" for value in row))


def show_table_schema(connection, table_name):
    """Display SQLite's metadata for a table."""
    print(f"\n--- Schema: {table_name} ---")
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    for row in rows:
        print(row)


# =============================================================================
# 2. FUNDAMENTAL TABLE USED THROUGHOUT THE LESSON
# =============================================================================

def create_employee_table(connection):
    """
    Create an employee table demonstrating:
    - required columns
    - PRIMARY KEY
    - AUTOINCREMENT
    - NOT NULL
    - DEFAULT
    - UNIQUE
    - CHECK
    """
    execute_sql(
        connection,
        """
        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            department TEXT DEFAULT 'General',
            salary REAL DEFAULT 30000,
            status TEXT NOT NULL DEFAULT 'Active',
            country TEXT DEFAULT 'India',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            CHECK (salary >= 0),
            CHECK (status IN ('Active', 'Inactive', 'On Leave'))
        )
        """,
    )


def show_intro():
    print(
        """
============================================================
INSERT STATEMENTS
============================================================

INSERT adds new rows to an existing table.

Core forms demonstrated in this script:

1. INSERT INTO table VALUES (...)
2. INSERT INTO table (column1, column2, ...) VALUES (...)
3. INSERT INTO table (column1, column2, ...)
   VALUES (...), (...), (...)
4. INSERT ... DEFAULT VALUES
5. INSERT with DEFAULT explicitly requested
6. INSERT ... SELECT ...
7. Parameterized INSERT
8. executemany() for repeated parameterized INSERT operations
9. Transactional INSERT operations
10. Constraint failures and rollback
11. RETURNING
12. UPSERT using INSERT ... ON CONFLICT
13. Edge cases and production considerations
"""
    )


# =============================================================================
# 3. BASIC INSERT SYNTAX
# =============================================================================

def demonstrate_basic_insert(connection):
    print("\n" + "=" * 60)
    print("3. BASIC INSERT")
    print("=" * 60)

    # The simplest conceptual form is:
    #
    # INSERT INTO table_name
    # VALUES (value1, value2, ...);
    #
    # When no column list is supplied, values must correspond to the table's
    # declared column order.

    execute_sql(
        connection,
        """
        INSERT INTO employees
        VALUES (
            NULL,
            'Asha',
            'Sharma',
            'asha@example.com',
            'Engineering',
            75000,
            'Active',
            'India',
            CURRENT_TIMESTAMP
        )
        """,
    )

    print_rows(
        connection,
        "SELECT * FROM employees",
        title="Employee inserted using table-column order",
    )

    print(
        """
Important:
- INSERT creates a row.
- The table must already exist.
- VALUES supplies the values for that row.
- If a column is omitted, its DEFAULT may be used, or NULL may be
  inserted if NULL is permitted and no default exists.
"""
    )


# =============================================================================
# 4. WHY EXPLICIT COLUMN LISTS ARE IMPORTANT
# =============================================================================

def demonstrate_column_ordering(connection):
    print("\n" + "=" * 60)
    print("4. COLUMN ORDERING")
    print("=" * 60)

    # Recommended production form:
    #
    # INSERT INTO employees (first_name, last_name, email, department)
    # VALUES ('Ravi', 'Kumar', 'ravi@example.com', 'Finance');

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email, department)
        VALUES
            ('Ravi', 'Kumar', 'ravi@example.com', 'Finance')
        """,
    )

    print_rows(
        connection,
        """
        SELECT employee_id, first_name, last_name, email,
               department, salary, status, country
        FROM employees
        WHERE email = 'ravi@example.com'
        """,
        title="Explicit column ordering",
    )

    print(
        """
Column ordering rule:

INSERT INTO table (A, B, C)
VALUES (value_for_A, value_for_B, value_for_C);

The order of the VALUES expressions follows the column list,
not necessarily the physical/table declaration order.

This makes INSERT statements safer and easier to maintain.
"""
    )

    # Reordered column list is valid because values follow that list.
    execute_sql(
        connection,
        """
        INSERT INTO employees
            (email, last_name, first_name, department, salary)
        VALUES
            (
                'neha@example.com',
                'Verma',
                'Neha',
                'Marketing',
                62000
            )
        """,
    )

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email, department, salary
        FROM employees
        WHERE email = 'neha@example.com'
        """,
        title="Same table, different column-list order",
    )

    print(
        """
A common mistake is assuming that the VALUES order is independent
of the column list. It is not.

Correct:
    INSERT INTO employees (first_name, last_name)
    VALUES ('A', 'B');

This means:
    first_name = 'A'
    last_name  = 'B'

If the list is reversed:
    INSERT INTO employees (last_name, first_name)
    VALUES ('A', 'B');

then:
    last_name  = 'A'
    first_name = 'B'
"""
    )


# =============================================================================
# 5. DEFAULT VALUES
# =============================================================================

def demonstrate_default_values(connection):
    print("\n" + "=" * 60)
    print("5. DEFAULT VALUES")
    print("=" * 60)

    # DEFAULT VALUES tells the database to create a row using each column's
    # default value where one exists.
    #
    # This table has NOT NULL columns without defaults, so a completely
    # default-generated employee row would fail. We demonstrate DEFAULT VALUES
    # with a separate table designed for that purpose.

    execute_sql(
        connection,
        """
        CREATE TABLE system_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT DEFAULT 'INFO',
            message TEXT DEFAULT 'System event',
            severity INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO system_events
        DEFAULT VALUES
        """,
    )

    print_rows(
        connection,
        "SELECT * FROM system_events",
        title="Row generated entirely from defaults",
    )

    print(
        """
DEFAULT VALUES is useful when a table has sensible defaults for
all columns that need values.

Conceptual syntax:

INSERT INTO table_name
DEFAULT VALUES;

It is different from omitting the column list in an ordinary INSERT.
"""
    )


# =============================================================================
# 6. OMITTING COLUMNS TO USE THEIR DEFAULT VALUES
# =============================================================================

def demonstrate_omitted_columns_and_defaults(connection):
    print("\n" + "=" * 60)
    print("6. OMITTED COLUMNS AND DEFAULT VALUES")
    print("=" * 60)

    # employee_id is generated automatically.
    # salary is omitted, so its DEFAULT 30000 is used.
    # status is omitted, so its DEFAULT 'Active' is used.
    # country is omitted, so its DEFAULT 'India' is used.
    # created_at is omitted, so CURRENT_TIMESTAMP is used.

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email, department)
        VALUES
            ('Priya', 'Singh', 'priya@example.com', 'HR')
        """,
    )

    print_rows(
        connection,
        """
        SELECT employee_id, first_name, last_name, email,
               department, salary, status, country, created_at
        FROM employees
        WHERE email = 'priya@example.com'
        """,
        title="Omitted columns receive their defaults",
    )

    print(
        """
Omitting a column does not necessarily mean NULL.

For an omitted column:

1. If a DEFAULT exists, the default is normally used.
2. If there is no DEFAULT and NULL is allowed, NULL is used.
3. If the column is NOT NULL and has no usable default, the INSERT
   fails.
4. Identity/auto-generated columns may generate their own value.

This distinction is fundamental when reading INSERT statements.
"""
    )


# =============================================================================
# 7. EXPLICIT DEFAULT KEYWORD
# =============================================================================

def demonstrate_explicit_default(connection):
    print("\n" + "=" * 60)
    print("7. EXPLICIT DEFAULT VALUES IN AN INSERT")
    print("=" * 60)

    # SQLite supports DEFAULT in INSERT VALUES expressions in newer versions
    # only in certain contexts, so the safest portable demonstration is to
    # omit columns and let their defaults apply.
    #
    # We demonstrate the concept through a table where a column can be
    # explicitly reset to its declared default using an UPDATE, while also
    # showing why omission is often the more portable INSERT technique.

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email, department, salary)
        VALUES
            ('Arjun', 'Mehta', 'arjun@example.com', 'Sales', 45000)
        """,
    )

    print_rows(
        connection,
        """
        SELECT first_name, last_name, department, salary, status
        FROM employees
        WHERE email = 'arjun@example.com'
        """,
        title="Explicitly supplied values versus omitted defaults",
    )

    print(
        """
DEFAULT has two closely related meanings:

- A column declaration such as:
      status TEXT DEFAULT 'Active'

  defines the value used when the INSERT does not provide a value
  for status.

- DEFAULT VALUES means:
      use defaults for the entire row where applicable.

When writing portable SQL, omitting a column is often the clearest
way to request its declared default.
"""
    )


# =============================================================================
# 8. MULTIPLE-ROW INSERT
# =============================================================================

def demonstrate_multiple_row_insert(connection):
    print("\n" + "=" * 60)
    print("8. MULTIPLE-ROW INSERT")
    print("=" * 60)

    # One INSERT statement can create several rows.
    #
    # INSERT INTO employees (first_name, last_name, email, department)
    # VALUES
    #     ('Vikram', 'Rao', 'vikram@example.com', 'IT'),
    #     ('Kiran', 'Patel', 'kiran@example.com', 'Finance'),
    #     ('Meera', 'Joshi', 'meera@example.com', 'Operations');

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email, department)
        VALUES
            ('Vikram', 'Rao', 'vikram@example.com', 'IT'),
            ('Kiran', 'Patel', 'kiran@example.com', 'Finance'),
            ('Meera', 'Joshi', 'meera@example.com', 'Operations')
        """,
    )

    print_rows(
        connection,
        """
        SELECT employee_id, first_name, last_name, email, department
        FROM employees
        WHERE email IN (
            'vikram@example.com',
            'kiran@example.com',
            'meera@example.com'
        )
        ORDER BY employee_id
        """,
        title="Three rows inserted by one INSERT statement",
    )

    print(
        """
Benefits:
- Fewer SQL statements.
- Less network/protocol overhead in client-server databases.
- Often faster than individual INSERT statements.
- The rows share the same INSERT statement and transaction context.

The exact maximum number of rows or bound parameters depends on
the database engine and configuration.
"""
    )


# =============================================================================
# 9. MULTIPLE-ROW INSERT WITH DEFAULTS
# =============================================================================

def demonstrate_multiple_rows_with_defaults(connection):
    print("\n" + "=" * 60)
    print("9. MULTIPLE ROW INSERTS WITH OMITTED DEFAULTED COLUMNS")
    print("=" * 60)

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email)
        VALUES
            ('Sonal', 'Gupta', 'sonal@example.com'),
            ('Amit', 'Nair', 'amit@example.com')
        """,
    )

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email, department, salary, status
        FROM employees
        WHERE email IN ('sonal@example.com', 'amit@example.com')
        ORDER BY employee_id
        """,
        title="Multiple rows using column defaults",
    )


# =============================================================================
# 10. NULL VERSUS DEFAULT VERSUS OMITTED COLUMN
# =============================================================================

def demonstrate_null_vs_default(connection):
    print("\n" + "=" * 60)
    print("10. NULL VERSUS DEFAULT VERSUS OMITTED COLUMN")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE preferences (
            preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            theme TEXT DEFAULT 'light',
            language TEXT DEFAULT 'English'
        )
        """,
    )

    # Omitted theme => default 'light'.
    execute_sql(
        connection,
        """
        INSERT INTO preferences (username)
        VALUES ('user_default')
        """,
    )

    # Explicit NULL => NULL, not the DEFAULT, because NULL is a supplied value.
    execute_sql(
        connection,
        """
        INSERT INTO preferences (username, theme)
        VALUES ('user_null', NULL)
        """,
    )

    # Explicitly supplying a value => that value is stored.
    execute_sql(
        connection,
        """
        INSERT INTO preferences (username, theme)
        VALUES ('user_custom', 'dark')
        """,
    )

    print_rows(
        connection,
        """
        SELECT username, theme, language
        FROM preferences
        ORDER BY preference_id
        """,
        title="Omitted column versus NULL versus explicit value",
    )

    print(
        """
Critical distinction:

INSERT INTO preferences (username)
VALUES ('user_default');

uses the DEFAULT for theme.

INSERT INTO preferences (username, theme)
VALUES ('user_null', NULL);

explicitly supplies NULL and therefore does not request the
column's default.

INSERT INTO preferences (username, theme)
VALUES ('user_custom', 'dark');

stores the supplied value.

DEFAULT and NULL are not interchangeable.
"""
    )


# =============================================================================
# 11. NULLABILITY AND NOT NULL
# =============================================================================

def demonstrate_not_null(connection):
    print("\n" + "=" * 60)
    print("11. NOT NULL CONSTRAINT")
    print("=" * 60)

    try:
        execute_sql(
            connection,
            """
            INSERT INTO employees
                (first_name, last_name, email)
            VALUES
                (NULL, 'Invalid', 'invalid@example.com')
            """,
        )
    except sqlite3.IntegrityError as error:
        print("Expected NOT NULL failure:")
        print(error)

    print(
        """
NOT NULL means a column cannot contain NULL.

A NOT NULL column may still be omitted from INSERT if its schema
provides a valid default or automatic value.

Example:
    status TEXT NOT NULL DEFAULT 'Active'

can be omitted during INSERT because the database can supply
'Active'.
"""
    )


# =============================================================================
# 12. UNIQUE CONSTRAINT
# =============================================================================

def demonstrate_unique_constraint(connection):
    print("\n" + "=" * 60)
    print("12. UNIQUE CONSTRAINT")
    print("=" * 60)

    try:
        execute_sql(
            connection,
            """
            INSERT INTO employees
                (first_name, last_name, email)
            VALUES
                ('Duplicate', 'Email', 'asha@example.com')
            """,
        )
    except sqlite3.IntegrityError as error:
        print("Expected UNIQUE constraint failure:")
        print(error)

    print(
        """
UNIQUE prevents duplicate values in the constrained column or
column combination.

This matters for INSERT because an INSERT can fail even when its
SQL syntax is correct.

Typical production response:
- reject the operation,
- update the existing record,
- ignore the duplicate,
- or use an UPSERT strategy.
"""
    )


# =============================================================================
# 13. PRIMARY KEY AND AUTO-GENERATED VALUES
# =============================================================================

def demonstrate_primary_key_generation(connection):
    print("\n" + "=" * 60)
    print("13. PRIMARY KEY AND GENERATED IDENTIFIERS")
    print("=" * 60)

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email)
        VALUES
            ('Generated', 'Identifier', 'generated@example.com')
        """,
    )

    print_rows(
        connection,
        """
        SELECT employee_id, first_name, last_name, email
        FROM employees
        WHERE email = 'generated@example.com'
        """,
        title="Automatically generated employee_id",
    )

    print(
        """
employee_id is omitted because SQLite generates it.

Do not manually provide generated identifiers unless the application
has a specific reason to do so and the database design permits it.
"""
    )


# =============================================================================
# 14. CHECK CONSTRAINT
# =============================================================================

def demonstrate_check_constraint(connection):
    print("\n" + "=" * 60)
    print("14. CHECK CONSTRAINT")
    print("=" * 60)

    try:
        execute_sql(
            connection,
            """
            INSERT INTO employees
                (first_name, last_name, email, salary)
            VALUES
                ('Negative', 'Salary', 'negative@example.com', -5000)
            """,
        )
    except sqlite3.IntegrityError as error:
        print("Expected CHECK constraint failure:")
        print(error)

    print(
        """
CHECK constraints validate a logical condition.

Here:
    CHECK (salary >= 0)

prevents an invalid negative salary from being inserted.

Database constraints are valuable because they protect data
integrity even when multiple applications write to the same database.
"""
    )


# =============================================================================
# 15. PARAMETERIZED INSERT
# =============================================================================

def demonstrate_parameterized_insert(connection):
    print("\n" + "=" * 60)
    print("15. PARAMETERIZED INSERT")
    print("=" * 60)

    first_name = "Rahul"
    last_name = "Das"
    email = "rahul@example.com"
    department = "Security"
    salary = 81000

    # Never build SQL by concatenating untrusted values:
    #
    # BAD:
    # sql = "INSERT INTO employees (...) VALUES ('" + first_name + "', ...)"
    #
    # Parameter binding keeps data separate from SQL syntax.

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email, department, salary)
        VALUES
            (?, ?, ?, ?, ?)
        """,
        (first_name, last_name, email, department, salary),
    )

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email, department, salary
        FROM employees
        WHERE email = ?
        """,
        (email,),
        title="Parameterized INSERT",
    )

    print(
        """
Parameterized queries:
- prevent SQL injection when used correctly,
- handle quoting safely,
- reduce manual SQL escaping,
- improve correctness for strings and special characters.

Do not parameterize SQL identifiers such as table names using
ordinary value placeholders. Identifiers require controlled SQL
construction or database-specific identifier handling.
"""
    )


# =============================================================================
# 16. PARAMETERIZED MULTIPLE INSERTS WITH executemany()
# =============================================================================

def demonstrate_executemany(connection):
    print("\n" + "=" * 60)
    print("16. executemany() FOR REPEATED INSERTS")
    print("=" * 60)

    employees = [
        ("Dev", "Shah", "dev@example.com", "Engineering", 72000),
        ("Isha", "Roy", "isha@example.com", "Analytics", 68000),
        ("Manoj", "Seth", "manoj@example.com", "Operations", 59000),
    ]

    execute_many(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email, department, salary)
        VALUES
            (?, ?, ?, ?, ?)
        """,
        employees,
    )

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email, department, salary
        FROM employees
        WHERE email IN (
            'dev@example.com',
            'isha@example.com',
            'manoj@example.com'
        )
        ORDER BY employee_id
        """,
        title="Rows inserted using executemany()",
    )

    print(
        """
executemany() is a client-side API pattern for executing the same
parameterized INSERT structure against many sets of values.

It is especially useful when rows are already available in Python.

For very large datasets, batch size, transaction size, indexes,
constraints, logging, and database-specific bulk-loading facilities
must be considered.
"""
    )


# =============================================================================
# 17. INSERT ... SELECT
# =============================================================================

def demonstrate_insert_select(connection):
    print("\n" + "=" * 60)
    print("17. INSERT ... SELECT")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE employee_archive (
            employee_id INTEGER,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            department TEXT,
            salary REAL,
            status TEXT
        )
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO employee_archive
            (employee_id, first_name, last_name, email,
             department, salary, status)
        SELECT
            employee_id, first_name, last_name, email,
            department, salary, status
        FROM employees
        WHERE status = 'Inactive'
        """,
    )

    print_rows(
        connection,
        "SELECT * FROM employee_archive",
        title="Rows copied with INSERT ... SELECT",
    )

    print(
        """
INSERT ... SELECT is useful when new rows are derived from data
already stored in the database.

General form:

INSERT INTO destination (A, B, C)
SELECT X, Y, Z
FROM source
WHERE condition;

The selected expressions must be compatible with the destination
columns in count, order, and data type requirements.
"""
    )


# =============================================================================
# 18. INSERT ... SELECT WITH TRANSFORMATION
# =============================================================================

def demonstrate_transformed_insert_select(connection):
    print("\n" + "=" * 60)
    print("18. INSERT ... SELECT WITH EXPRESSIONS")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE employee_directory (
            employee_id INTEGER,
            display_name TEXT,
            contact_email TEXT,
            department TEXT
        )
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO employee_directory
            (employee_id, display_name, contact_email, department)
        SELECT
            employee_id,
            first_name || ' ' || last_name,
            email,
            department
        FROM employees
        WHERE department IS NOT NULL
        """,
    )

    print_rows(
        connection,
        """
        SELECT employee_id, display_name, contact_email, department
        FROM employee_directory
        ORDER BY employee_id
        """,
        title="INSERT ... SELECT with computed values",
    )


# =============================================================================
# 19. RETURNING
# =============================================================================

def demonstrate_returning(connection):
    print("\n" + "=" * 60)
    print("19. RETURNING")
    print("=" * 60)

    # SQLite supports RETURNING in modern versions.
    # It allows an INSERT to return generated or inserted values.

    try:
        cursor = connection.execute(
            """
            INSERT INTO employees
                (first_name, last_name, email, department)
            VALUES
                ('Returned', 'Row', 'returned@example.com', 'Platform')
            RETURNING employee_id, first_name, email, department
            """
        )

        returned_row = cursor.fetchone()
        connection.commit()

        print("Values returned by INSERT:")
        print(returned_row)

    except sqlite3.OperationalError as error:
        print("RETURNING is unavailable in this SQLite environment:")
        print(error)

    print(
        """
RETURNING is useful when the application needs values generated by
the database, such as:
- generated primary keys,
- timestamps,
- computed/defaulted values.

Database support and exact RETURNING syntax vary by SQL dialect.
"""
    )


# =============================================================================
# 20. TRANSACTIONS
# =============================================================================

def demonstrate_transaction_rollback(connection):
    print("\n" + "=" * 60)
    print("20. TRANSACTIONS AND ROLLBACK")
    print("=" * 60)

    # A transaction groups changes into an atomic unit.
    # If a constraint failure occurs and the transaction is rolled back,
    # earlier successful INSERTs in that transaction can be undone.

    connection.execute("BEGIN")

    try:
        connection.execute(
            """
            INSERT INTO employees
                (first_name, last_name, email, department)
            VALUES
                ('Transaction', 'Good', 'transaction_good@example.com', 'IT')
            """
        )

        # This violates the UNIQUE constraint on email.
        connection.execute(
            """
            INSERT INTO employees
                (first_name, last_name, email, department)
            VALUES
                ('Transaction', 'Bad', 'asha@example.com', 'IT')
            """
        )

        connection.commit()

    except sqlite3.IntegrityError as error:
        print("Transaction failed:")
        print(error)
        connection.rollback()

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email
        FROM employees
        WHERE email = 'transaction_good@example.com'
        """,
        title="First INSERT was rolled back",
    )

    print(
        """
Transactions are important when several INSERTs represent one
logical operation.

Typical transaction lifecycle:

BEGIN
    INSERT ...
    INSERT ...
    INSERT ...
COMMIT

If an unrecoverable error occurs:

ROLLBACK

This protects atomicity: either the logical operation succeeds as
a unit or its changes are undone.
"""
    )


# =============================================================================
# 21. SAVEPOINTS
# =============================================================================

def demonstrate_savepoint(connection):
    print("\n" + "=" * 60)
    print("21. SAVEPOINT")
    print("=" * 60)

    connection.execute("BEGIN")

    try:
        connection.execute(
            """
            INSERT INTO employees
                (first_name, last_name, email)
            VALUES
                ('Before', 'Savepoint', 'before_savepoint@example.com')
            """
        )

        connection.execute("SAVEPOINT employee_batch")

        connection.execute(
            """
            INSERT INTO employees
                (first_name, last_name, email)
            VALUES
                ('Temporary', 'Row', 'temporary_savepoint@example.com')
            """
        )

        # Undo only the work after the savepoint.
        connection.execute("ROLLBACK TO employee_batch")

        # Release the savepoint and commit the outer transaction.
        connection.execute("RELEASE employee_batch")
        connection.commit()

    except sqlite3.Error as error:
        connection.rollback()
        print("Unexpected transaction error:", error)

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email
        FROM employees
        WHERE email IN (
            'before_savepoint@example.com',
            'temporary_savepoint@example.com'
        )
        """,
        title="Savepoint result",
    )

    print(
        """
SAVEPOINT allows partial rollback inside a larger transaction.

This is useful when a transaction contains multiple logical stages
and one stage may need to be undone without discarding everything.
"""
    )


# =============================================================================
# 22. UPSERT
# =============================================================================

def demonstrate_upsert(connection):
    print("\n" + "=" * 60)
    print("22. UPSERT")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE inventory (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            CHECK (quantity >= 0)
        )
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO inventory
            (product_id, product_name, quantity)
        VALUES
            (1, 'Keyboard', 10)
        """,
    )

    # If product_id already exists, update the quantity instead of failing.
    execute_sql(
        connection,
        """
        INSERT INTO inventory
            (product_id, product_name, quantity)
        VALUES
            (1, 'Keyboard', 15)
        ON CONFLICT(product_id)
        DO UPDATE SET
            quantity = inventory.quantity + excluded.quantity
        """,
    )

    print_rows(
        connection,
        "SELECT * FROM inventory",
        title="UPSERT result",
    )

    print(
        """
UPSERT combines insertion and conflict handling.

The exact syntax varies among database systems.

SQLite/PostgreSQL-style conceptual form:

INSERT INTO table (...)
VALUES (...)
ON CONFLICT (...)
DO UPDATE SET ...;

The special 'excluded' row represents the values proposed by the
INSERT that caused the conflict.

UPSERT is useful for:
- counters,
- synchronization,
- idempotent writes,
- cache refreshes,
- inventory updates.

Careful design is required when concurrent transactions can update
the same logical record.
"""
    )


# =============================================================================
# 23. IGNORING CONFLICTS
# =============================================================================

def demonstrate_insert_or_ignore(connection):
    print("\n" + "=" * 60)
    print("23. CONFLICT-IGNORING INSERT")
    print("=" * 60)

    execute_sql(
        connection,
        """
        INSERT OR IGNORE INTO employees
            (first_name, last_name, email)
        VALUES
            ('Duplicate', 'Ignored', 'asha@example.com')
        """,
    )

    print(
        """
SQLite's INSERT OR IGNORE can suppress certain constraint failures.

This can be useful for intentionally idempotent operations, but it
can also hide data-quality problems.

Use conflict-ignoring behavior only when ignoring the conflicting
row is actually part of the application's intended semantics.
"""
    )


# =============================================================================
# 24. DATATYPES AND INSERT VALUES
# =============================================================================

def demonstrate_values_and_types(connection):
    print("\n" + "=" * 60)
    print("24. VALUES AND DATA TYPES")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE data_types_demo (
            id INTEGER PRIMARY KEY,
            text_value TEXT,
            integer_value INTEGER,
            decimal_value REAL,
            nullable_value TEXT
        )
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO data_types_demo
            (id, text_value, integer_value, decimal_value, nullable_value)
        VALUES
            (?, ?, ?, ?, ?)
        """,
        (1, "hello", 42, 19.95, None),
    )

    print_rows(
        connection,
        "SELECT * FROM data_types_demo",
        title="Inserted values of different types",
    )

    print(
        """
A value's representation and the database column's type system are
database-specific.

For reliable INSERT statements:
- supply semantically appropriate values,
- validate application input,
- use parameters,
- understand implicit conversion rules,
- do not assume every database has SQLite's type behavior.
"""
    )


# =============================================================================
# 25. DATE AND TIME VALUES
# =============================================================================

def demonstrate_datetime_defaults(connection):
    print("\n" + "=" * 60)
    print("25. DATE/TIME DEFAULTS")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO audit_log (action)
        VALUES (?)
        """,
        ("LOGIN",),
    )

    print_rows(
        connection,
        "SELECT * FROM audit_log",
        title="Timestamp generated by a DEFAULT expression",
    )

    print(
        """
Defaults can be expressions supported by the database.

A common pattern is a creation timestamp:

created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

The exact timestamp type and functions differ between SQL systems.
"""
    )


# =============================================================================
# 26. INSERT AND FOREIGN KEYS
# =============================================================================

def demonstrate_foreign_keys(connection):
    print("\n" + "=" * 60)
    print("26. FOREIGN KEY CONSTRAINTS")
    print("=" * 60)

    connection.execute("PRAGMA foreign_keys = ON")

    execute_sql(
        connection,
        """
        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL UNIQUE
        )
        """,
    )

    execute_sql(
        connection,
        """
        CREATE TABLE department_employees (
            employee_id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            FOREIGN KEY (department_id)
                REFERENCES departments(department_id)
        )
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO departments
            (department_id, department_name)
        VALUES
            (1, 'Engineering')
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO department_employees
            (employee_id, employee_name, department_id)
        VALUES
            (101, 'Valid Employee', 1)
        """,
    )

    try:
        execute_sql(
            connection,
            """
            INSERT INTO department_employees
                (employee_id, employee_name, department_id)
            VALUES
                (102, 'Invalid Employee', 999)
            """,
        )
    except sqlite3.IntegrityError as error:
        print("Expected FOREIGN KEY failure:")
        print(error)

    print_rows(
        connection,
        """
        SELECT employee_id, employee_name, department_id
        FROM department_employees
        """,
        title="Only valid foreign-key INSERT survived",
    )


# =============================================================================
# 27. COLUMN COUNT MISMATCH
# =============================================================================

def demonstrate_column_count_error(connection):
    print("\n" + "=" * 60)
    print("27. COLUMN COUNT MISMATCH")
    print("=" * 60)

    try:
        execute_sql(
            connection,
            """
            INSERT INTO employees
                (first_name, last_name, email)
            VALUES
                ('Too', 'Many', 'values@example.com', 'Extra')
            """,
        )
    except sqlite3.Error as error:
        print("Expected column/value count failure:")
        print(error)

    print(
        """
The number of values must match the number of explicitly listed
columns.

Correct:
    INSERT INTO employees (first_name, last_name)
    VALUES ('A', 'B');

Incorrect:
    INSERT INTO employees (first_name, last_name)
    VALUES ('A');

Incorrect:
    INSERT INTO employees (first_name, last_name)
    VALUES ('A', 'B', 'C');
"""
    )


# =============================================================================
# 28. WRONG COLUMN ORDER
# =============================================================================

def demonstrate_wrong_order_concept(connection):
    print("\n" + "=" * 60)
    print("28. WRONG COLUMN ORDER")
    print("=" * 60)

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email)
        VALUES
            ('Correct', 'Order', 'correct-order@example.com')
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (last_name, first_name, email)
        VALUES
            ('Order', 'Reversed', 'reversed-order@example.com')
        """,
    )

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email
        FROM employees
        WHERE email IN (
            'correct-order@example.com',
            'reversed-order@example.com'
        )
        ORDER BY employee_id
        """,
        title="Values follow the explicit column list",
    )

    print(
        """
A syntactically valid INSERT can still be semantically wrong.

The database cannot necessarily detect that a first name was
accidentally supplied for a last-name column if both columns have
compatible types.

Explicit column lists prevent dependence on table declaration order,
but developers must still put values in the correct listed order.
"""
    )


# =============================================================================
# 29. INSERTING SPECIAL CHARACTERS SAFELY
# =============================================================================

def demonstrate_special_characters(connection):
    print("\n" + "=" * 60)
    print("29. SPECIAL CHARACTERS AND PARAMETER BINDING")
    print("=" * 60)

    special_name = "O'Connor"
    special_email = "oconnor@example.com"

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email)
        VALUES
            (?, ?, ?)
        """,
        ("John", special_name, special_email),
    )

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email
        FROM employees
        WHERE email = ?
        """,
        (special_email,),
        title="Apostrophe safely inserted with parameters",
    )

    print(
        """
Parameter binding is especially important for strings containing
apostrophes, quotation marks, newline characters, Unicode characters,
and other special content.

Do not manually construct SQL strings from user-controlled values.
"""
    )


# =============================================================================
# 30. SQL INJECTION DEMONSTRATION
# =============================================================================

def demonstrate_sql_injection_defense(connection):
    print("\n" + "=" * 60)
    print("30. SQL INJECTION DEFENSE")
    print("=" * 60)

    malicious_value = "Robert'); DROP TABLE employees; --"

    # Safe approach:
    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email)
        VALUES
            (?, ?, ?)
        """,
        ("Safe", malicious_value, "safe-injection@example.com"),
    )

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email
        FROM employees
        WHERE email = ?
        """,
        ("safe-injection@example.com",),
        title="Malicious-looking input treated as data",
    )

    print(
        """
SQL injection occurs when untrusted input is incorrectly combined
with SQL syntax.

The safe pattern is:

SQL template + bound parameters

rather than:

SQL template + string concatenation

The parameter value remains data instead of becoming executable SQL.
"""
    )


# =============================================================================
# 31. INDEXES AND INSERT PERFORMANCE
# =============================================================================

def demonstrate_indexes_and_insert_cost(connection):
    print("\n" + "=" * 60)
    print("31. INDEXES AND INSERT PERFORMANCE")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE indexed_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            event_code TEXT NOT NULL
        )
        """,
    )

    execute_sql(
        connection,
        """
        CREATE INDEX idx_indexed_events_code
        ON indexed_events(event_code)
        """,
    )

    execute_many(
        connection,
        """
        INSERT INTO indexed_events (event_name, event_code)
        VALUES (?, ?)
        """,
        [
            ("Login", "AUTH"),
            ("Logout", "AUTH"),
            ("Purchase", "PAYMENT"),
            ("Refund", "PAYMENT"),
        ],
    )

    print_rows(
        connection,
        """
        SELECT event_id, event_name, event_code
        FROM indexed_events
        ORDER BY event_id
        """,
        title="Rows inserted into indexed table",
    )

    print(
        """
Indexes improve lookup performance but add write cost.

For every INSERT affecting an indexed column, the database may need
to update the corresponding index structure.

Production trade-off:
- more indexes can improve reads,
- more indexes can slow writes,
- indexes consume storage,
- excessive indexes increase maintenance cost.

Index design must reflect actual workload.
"""
    )


# =============================================================================
# 32. BULK INSERT AND TRANSACTION SIZE
# =============================================================================

def demonstrate_bulk_transaction(connection):
    print("\n" + "=" * 60)
    print("32. BULK INSERT AND TRANSACTION SIZE")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE measurements (
            measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_name TEXT NOT NULL,
            reading REAL NOT NULL
        )
        """,
    )

    rows = [
        ("sensor-A", 10.1),
        ("sensor-A", 10.4),
        ("sensor-B", 20.3),
        ("sensor-B", 20.8),
        ("sensor-C", 5.9),
    ]

    # One transaction containing multiple parameterized inserts.
    connection.execute("BEGIN")

    try:
        connection.executemany(
            """
            INSERT INTO measurements (sensor_name, reading)
            VALUES (?, ?)
            """,
            rows,
        )
        connection.commit()
    except sqlite3.Error:
        connection.rollback()
        raise

    print_rows(
        connection,
        "SELECT * FROM measurements",
        title="Bulk insertion inside one transaction",
    )

    print(
        """
For large workloads, repeatedly committing every individual row can
be much slower than batching rows into transactions.

A production strategy often considers:
- batch size,
- transaction duration,
- lock contention,
- memory usage,
- failure recovery,
- replication/logging behavior,
- database-specific bulk-loading features.

There is no universally optimal batch size.
"""
    )


# =============================================================================
# 33. IDEMPOTENCY
# =============================================================================

def demonstrate_idempotent_insert(connection):
    print("\n" + "=" * 60)
    print("33. IDEMPOTENT INSERT DESIGN")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE external_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """,
    )

    event = ("evt-1001", "PAYMENT_RECEIVED", '{"amount": 100}')

    execute_sql(
        connection,
        """
        INSERT OR IGNORE INTO external_events
            (event_id, event_type, payload)
        VALUES
            (?, ?, ?)
        """,
        event,
    )

    # Repeating the same operation does not create a second row.
    execute_sql(
        connection,
        """
        INSERT OR IGNORE INTO external_events
            (event_id, event_type, payload)
        VALUES
            (?, ?, ?)
        """,
        event,
    )

    print_rows(
        connection,
        "SELECT * FROM external_events",
        title="Idempotent event insertion",
    )

    print(
        """
Idempotency means repeating the same logical operation produces
the intended same final state.

A unique event identifier combined with conflict handling can prevent
duplicate processing when clients retry requests.
"""
    )


# =============================================================================
# 34. DATA VALIDATION BEFORE INSERT
# =============================================================================

def validate_employee_input(first_name, last_name, email, salary):
    """Perform basic application-level validation before INSERT."""
    if not first_name.strip():
        raise ValueError("first_name cannot be empty")

    if not last_name.strip():
        raise ValueError("last_name cannot be empty")

    if "@" not in email:
        raise ValueError("email must contain '@'")

    if salary < 0:
        raise ValueError("salary cannot be negative")


def demonstrate_application_validation(connection):
    print("\n" + "=" * 60)
    print("34. APPLICATION VALIDATION")
    print("=" * 60)

    candidate = {
        "first_name": "Valid",
        "last_name": "Candidate",
        "email": "valid.candidate@example.com",
        "salary": 55000,
    }

    try:
        validate_employee_input(
            candidate["first_name"],
            candidate["last_name"],
            candidate["email"],
            candidate["salary"],
        )

        execute_sql(
            connection,
            """
            INSERT INTO employees
                (first_name, last_name, email, salary)
            VALUES
                (?, ?, ?, ?)
            """,
            (
                candidate["first_name"],
                candidate["last_name"],
                candidate["email"],
                candidate["salary"],
            ),
        )

        print("Validated employee inserted successfully.")

    except (ValueError, sqlite3.IntegrityError) as error:
        print("Insertion rejected:", error)

    print(
        """
Application validation and database constraints serve different
purposes.

Application validation:
- provides early, user-friendly feedback,
- checks business input requirements.

Database constraints:
- provide authoritative integrity enforcement,
- protect data regardless of which application writes it.

Production systems generally need both where appropriate.
"""
    )


# =============================================================================
# 35. DEFAULTS AND BUSINESS LOGIC
# =============================================================================

def demonstrate_default_design(connection):
    print("\n" + "=" * 60)
    print("35. DEFAULT DESIGN")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            priority INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO orders (customer_name)
        VALUES (?)
        """,
        ("Customer A",),
    )

    execute_sql(
        connection,
        """
        INSERT INTO orders (customer_name, priority)
        VALUES (?, ?)
        """,
        ("Customer B", 10),
    )

    print_rows(
        connection,
        "SELECT * FROM orders ORDER BY order_id",
        title="Business-oriented defaults",
    )

    print(
        """
Good defaults are generally:
- deterministic or intentionally generated,
- valid according to constraints,
- appropriate for newly created records,
- aligned with business semantics.

Be cautious with defaults that hide missing required information.
For example, automatically assigning a generic customer or financial
amount can create incorrect data rather than merely incomplete data.
"""
    )


# =============================================================================
# 36. INSERT WITH SELECTED COLUMNS ONLY
# =============================================================================

def demonstrate_partial_column_insert(connection):
    print("\n" + "=" * 60)
    print("36. PARTIAL COLUMN INSERT")
    print("=" * 60)

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email, country)
        VALUES
            ('Partial', 'Insert', 'partial@example.com', 'Nepal')
        """,
    )

    print_rows(
        connection,
        """
        SELECT first_name, last_name, email, department,
               salary, status, country
        FROM employees
        WHERE email = 'partial@example.com'
        """,
        title="Only selected columns supplied",
    )


# =============================================================================
# 37. INSERT ORDER IS NOT QUERY ORDER
# =============================================================================

def demonstrate_row_order(connection):
    print("\n" + "=" * 60)
    print("37. INSERT ORDER AND SELECT ORDER")
    print("=" * 60)

    execute_sql(
        connection,
        """
        CREATE TABLE sequence_demo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value TEXT NOT NULL
        )
        """,
    )

    execute_sql(
        connection,
        """
        INSERT INTO sequence_demo (value)
        VALUES ('first'), ('second'), ('third')
        """,
    )

    print_rows(
        connection,
        """
        SELECT id, value
        FROM sequence_demo
        ORDER BY id
        """,
        title="Explicitly ordered SELECT",
    )

    print(
        """
The order in which rows were inserted does not guarantee the order
in which a SELECT returns rows.

If application logic requires an order, specify ORDER BY explicitly.

This matters when developers assume that insertion order is a
permanent ordering guarantee.
"""
    )


# =============================================================================
# 38. TESTING INSERT OPERATIONS
# =============================================================================

def test_basic_insert(connection):
    """Test that a basic employee INSERT creates exactly one row."""
    before = connection.execute(
        "SELECT COUNT(*) FROM employees"
    ).fetchone()[0]

    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email)
        VALUES
            ('Test', 'User', 'test@example.com')
        """,
    )

    after = connection.execute(
        "SELECT COUNT(*) FROM employees"
    ).fetchone()[0]

    assert after == before + 1


def test_default_value(connection):
    """Test that omitted columns receive their defaults."""
    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email)
        VALUES
            ('Default', 'Test', 'default-test@example.com')
        """,
    )

    row = connection.execute(
        """
        SELECT department, salary, status, country
        FROM employees
        WHERE email = ?
        """,
        ("default-test@example.com",),
    ).fetchone()

    assert row == ("General", 30000.0, "Active", "India")


def test_unique_constraint(connection):
    """Test that duplicate email addresses are rejected."""
    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email)
        VALUES
            ('Unique', 'Test', 'unique-test@example.com')
        """,
    )

    try:
        execute_sql(
            connection,
            """
            INSERT INTO employees
                (first_name, last_name, email)
            VALUES
                ('Duplicate', 'Test', 'unique-test@example.com')
            """,
        )
    except sqlite3.IntegrityError:
        return

    raise AssertionError("Expected UNIQUE constraint failure")


def test_multiple_row_insert(connection):
    """Test that a single INSERT can create multiple rows."""
    execute_sql(
        connection,
        """
        INSERT INTO employees
            (first_name, last_name, email)
        VALUES
            ('Multi', 'One', 'multi-one@example.com'),
            ('Multi', 'Two', 'multi-two@example.com')
        """,
    )

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM employees
        WHERE email IN ('multi-one@example.com', 'multi-two@example.com')
        """
    ).fetchone()[0]

    assert count == 2


def run_tests():
    print("\n" + "=" * 60)
    print("38. TESTS")
    print("=" * 60)

    connection = create_connection()
    create_employee_table(connection)

    tests = [
        test_basic_insert,
        test_default_value,
        test_unique_constraint,
        test_multiple_row_insert,
    ]

    passed = 0

    for test in tests:
        test(connection)
        print(f"PASS: {test.__name__}")
        passed += 1

    connection.close()
    print(f"\n{passed}/{len(tests)} tests passed.")


# =============================================================================
# 39. COMMON MISTAKES REFERENCE
# =============================================================================

def show_common_mistakes():
    print("\n" + "=" * 60)
    print("39. COMMON INSERT MISTAKES")
    print("=" * 60)

    mistakes = {
        "Missing column list": (
            "INSERT INTO employees VALUES (...); "
            "can break when table structure changes."
        ),
        "Wrong value order": (
            "Values must correspond exactly to the explicit column list."
        ),
        "Wrong number of values": (
            "Column count and value count must match."
        ),
        "Confusing NULL with DEFAULT": (
            "Explicit NULL is not the same as omitting a defaulted column."
        ),
        "Ignoring constraints": (
            "PRIMARY KEY, UNIQUE, NOT NULL, CHECK, and FOREIGN KEY rules "
            "can reject an otherwise syntactically valid INSERT."
        ),
        "String concatenation": (
            "Building SQL with untrusted input creates SQL injection risk."
        ),
        "Too many individual commits": (
            "Committing every row can create substantial write overhead."
        ),
        "Too many indexes": (
            "Indexes can improve reads while increasing INSERT maintenance."
        ),
        "Assuming INSERT order": (
            "SELECT results require ORDER BY when ordering matters."
        ),
        "Hiding errors with conflict-ignore behavior": (
            "Ignoring conflicts can conceal real data-quality problems."
        ),
    }

    for mistake, explanation in mistakes.items():
        print(f"\n{mistake}:\n  {explanation}")


# =============================================================================
# 40. INSERT DECISION GUIDE
# =============================================================================

def show_decision_guide():
    print("\n" + "=" * 60)
    print("40. INSERT DECISION GUIDE")
    print("=" * 60)

    print(
        """
Use a basic INSERT when:
    One row needs to be created from known values.

Use an explicit column list when:
    Writing maintainable production SQL.

Use multi-row VALUES when:
    Several literal or parameterized rows share the same structure.

Use executemany() when:
    Application code has many parameter sets for one INSERT template.

Use INSERT ... SELECT when:
    New rows are derived from existing database rows.

Use DEFAULT values when:
    The schema provides meaningful automatic values.

Use a transaction when:
    Multiple writes must succeed or fail as one logical operation.

Use an UPSERT when:
    A conflict should update or otherwise resolve an existing record.

Use conflict-ignore behavior when:
    Duplicate/conflicting rows are intentionally harmless and should
    be skipped.

Use database constraints when:
    Data integrity must be enforced regardless of application behavior.
"""
    )


# =============================================================================
# 41. SQL DIALECT DIFFERENCES
# =============================================================================

def show_dialect_considerations():
    print("\n" + "=" * 60)
    print("41. SQL DIALECT CONSIDERATIONS")
    print("=" * 60)

    print(
        """
INSERT is standardized SQL, but implementations differ.

Common differences include:
- identity/auto-increment syntax,
- DEFAULT expression support,
- RETURNING support,
- conflict handling,
- UPSERT syntax,
- boolean representation,
- date/time types,
- parameter placeholder styles,
- maximum parameter counts,
- bulk-loading facilities,
- generated columns,
- trigger behavior.

Examples of database families include:
- PostgreSQL
- MySQL
- SQL Server
- Oracle
- SQLite

Do not assume that SQL written for one engine is completely
portable to another.
"""
    )


# =============================================================================
# 42. ADVANCED INSERT DESIGN PRINCIPLES
# =============================================================================

def show_advanced_principles():
    print("\n" + "=" * 60)
    print("42. ADVANCED DESIGN PRINCIPLES")
    print("=" * 60)

    principles = [
        (
            "Schema correctness",
            "INSERT logic should respect primary keys, foreign keys, "
            "unique constraints, NOT NULL rules, CHECK constraints, "
            "generated columns, and defaults."
        ),
        (
            "Explicit column lists",
            "Production INSERT statements should generally specify "
            "the destination columns explicitly."
        ),
        (
            "Parameter binding",
            "Use bound parameters for data values rather than string "
            "concatenation."
        ),
        (
            "Transaction boundaries",
            "Group related changes into intentional transactions."
        ),
        (
            "Idempotency",
            "Design retries so repeated requests do not create unintended "
            "duplicate business records."
        ),
        (
            "Observability",
            "Record sufficient application-level information to diagnose "
            "failed INSERT operations without exposing sensitive data."
        ),
        (
            "Performance",
            "Batch writes appropriately and keep indexes aligned with "
            "actual query and integrity requirements."
        ),
        (
            "Error handling",
            "Distinguish constraint violations, connection failures, "
            "serialization/deadlock conditions, validation failures, "
            "and unexpected database errors."
        ),
        (
            "Data integrity",
            "Do not rely solely on application validation when a rule "
            "can and should be enforced by the database."
        ),
    ]

    for title, explanation in principles:
        print(f"\n{title}:")
        print(f"  {explanation}")


# =============================================================================
# 43. MINI END-TO-END APPLICATION EXAMPLE
# =============================================================================

class EmployeeRepository:
    """
    Small repository abstraction demonstrating production-oriented INSERT
    practices.

    It uses:
    - explicit column lists,
    - parameterized SQL,
    - transaction handling,
    - database-generated identifiers.
    """

    def __init__(self, connection):
        self.connection = connection

    def create_employee(
        self,
        first_name,
        last_name,
        email,
        department=None,
        salary=None,
    ):
        """Insert an employee and return its generated identifier."""

        columns = ["first_name", "last_name", "email"]
        values = [first_name, last_name, email]

        # Build the optional column list from trusted, internally controlled
        # identifiers. User values are still passed as parameters.
        if department is not None:
            columns.append("department")
            values.append(department)

        if salary is not None:
            columns.append("salary")
            values.append(salary)

        placeholders = ", ".join("?" for _ in values)
        column_sql = ", ".join(columns)

        cursor = self.connection.execute(
            f"""
            INSERT INTO employees ({column_sql})
            VALUES ({placeholders})
            RETURNING employee_id
            """,
            values,
        )

        employee_id = cursor.fetchone()[0]
        self.connection.commit()
        return employee_id


def demonstrate_repository(connection):
    print("\n" + "=" * 60)
    print("43. END-TO-END REPOSITORY EXAMPLE")
    print("=" * 60)

    repository = EmployeeRepository(connection)

    employee_id = repository.create_employee(
        first_name="Production",
        last_name="Example",
        email="production@example.com",
        department="Technology",
        salary=95000,
    )

    print("Created employee ID:", employee_id)

    print_rows(
        connection,
        """
        SELECT employee_id, first_name, last_name, email,
               department, salary, status
        FROM employees
        WHERE employee_id = ?
        """,
        (employee_id,),
        title="Repository-created employee",
    )


# =============================================================================
# 44. FINAL DATABASE INSPECTION
# =============================================================================

def display_final_state(connection):
    print("\n" + "=" * 60)
    print("44. FINAL EMPLOYEE TABLE")
    print("=" * 60)

    print_rows(
        connection,
        """
        SELECT
            employee_id,
            first_name,
            last_name,
            email,
            department,
            salary,
            status,
            country
        FROM employees
        ORDER BY employee_id
        """,
    )

    show_table_schema(connection, "employees")


# =============================================================================
# 45. MAIN PROGRAM
# =============================================================================

def main():
    show_intro()

    connection = create_connection()

    try:
        # The employee table is intentionally created once and reused so
        # later demonstrations can show interactions among INSERT concepts.
        create_employee_table(connection)

        demonstrate_basic_insert(connection)
        demonstrate_column_ordering(connection)
        demonstrate_default_values(connection)
        demonstrate_omitted_columns_and_defaults(connection)
        demonstrate_explicit_default(connection)
        demonstrate_multiple_row_insert(connection)
        demonstrate_multiple_rows_with_defaults(connection)
        demonstrate_null_vs_default(connection)
        demonstrate_not_null(connection)
        demonstrate_unique_constraint(connection)
        demonstrate_primary_key_generation(connection)
        demonstrate_check_constraint(connection)
        demonstrate_parameterized_insert(connection)
        demonstrate_executemany(connection)
        demonstrate_insert_select(connection)
        demonstrate_transformed_insert_select(connection)
        demonstrate_returning(connection)
        demonstrate_transaction_rollback(connection)
        demonstrate_savepoint(connection)
        demonstrate_upsert(connection)
        demonstrate_insert_or_ignore(connection)
        demonstrate_values_and_types(connection)
        demonstrate_datetime_defaults(connection)
        demonstrate_foreign_keys(connection)
        demonstrate_column_count_error(connection)
        demonstrate_wrong_order_concept(connection)
        demonstrate_special_characters(connection)
        demonstrate_sql_injection_defense(connection)
        demonstrate_indexes_and_insert_cost(connection)
        demonstrate_bulk_transaction(connection)
        demonstrate_idempotent_insert(connection)
        demonstrate_application_validation(connection)
        demonstrate_default_design(connection)
        demonstrate_partial_column_insert(connection)
        demonstrate_row_order(connection)
        demonstrate_repository(connection)

        show_common_mistakes()
        show_decision_guide()
        show_dialect_considerations()
        show_advanced_principles()
        display_final_state(connection)

    finally:
        connection.close()

    run_tests()

    print("\n" + "=" * 60)
    print("INSERT LESSON COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
