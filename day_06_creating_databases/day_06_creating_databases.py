"""
CREATING DATABASES
==================

Topic:
    CREATE DATABASE, database naming, connection management, and database lifecycle

Purpose:
    A self-contained study script that teaches database creation from absolute
    beginner concepts through advanced operational considerations.

Important distinction:
    SQLite does not implement SQL CREATE DATABASE because a database is represented
    by a file. This script therefore uses SQLite for executable demonstrations and
    also shows portable/vendor-specific CREATE DATABASE statements as strings for
    PostgreSQL, MySQL/MariaDB, and SQL Server.

The executable examples use only Python's standard library.
"""

from __future__ import annotations

import os
import re
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


# ============================================================================
# 1. FUNDAMENTALS: WHAT IS A DATABASE?
# ============================================================================

def section(title: str) -> None:
    """Print a readable section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def subsection(title: str) -> None:
    """Print a readable subsection heading."""
    print("\n" + "-" * 78)
    print(title)
    print("-" * 78)


def explain_database_basics() -> None:
    section("1. DATABASE FUNDAMENTALS")

    print(
        """
A database is an organized system for storing and retrieving structured data.

A database management system (DBMS) is software that manages databases.
Examples include PostgreSQL, MySQL, MariaDB, Microsoft SQL Server, Oracle
Database, and SQLite.

A database commonly contains objects such as:

    Database
        ├── Schemas
        │     ├── Tables
        │     ├── Views
        │     ├── Sequences
        │     ├── Functions / Procedures
        │     └── Other objects
        ├── Users / Roles
        ├── Permissions
        └── Configuration

The exact hierarchy differs by DBMS.

A database server can host multiple databases. A database can contain
schemas, and schemas can contain tables and other objects.

The SQL statement:

    CREATE DATABASE database_name;

asks a DBMS that supports server-side database creation to create a new
database.

SQLite is different. SQLite databases are files, so creating an SQLite
database normally means opening a connection to a database file.
"""
    )


# ============================================================================
# 2. DATABASE CREATION CONCEPT
# ============================================================================

def show_create_database_syntax() -> None:
    section("2. CREATE DATABASE: CORE SQL SYNTAX")

    sql_examples = {
        "Generic SQL concept": """
CREATE DATABASE database_name;
""",
        "PostgreSQL": """
CREATE DATABASE company_db;
""",
        "PostgreSQL with options": """
CREATE DATABASE company_db
    OWNER app_user
    ENCODING 'UTF8';
""",
        "MySQL / MariaDB": """
CREATE DATABASE company_db;
""",
        "MySQL / MariaDB with character set": """
CREATE DATABASE company_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
""",
        "SQL Server": """
CREATE DATABASE company_db;
""",
        "SQLite equivalent": """
-- SQLite has no CREATE DATABASE statement.
-- Opening a file creates the database when the file does not exist.

sqlite3.connect("company.db");
""",
    }

    for database_engine, statement in sql_examples.items():
        print(f"\n{database_engine}:{statement}")


def explain_create_database_semantics() -> None:
    subsection("What CREATE DATABASE actually does")

    print(
        """
CREATE DATABASE is a database-definition operation. It normally asks the
database server to establish a new database container and initialize the
structures and metadata required for that database.

It does not normally create application tables automatically.

For example:

    CREATE DATABASE sales_db;

creates the database container.

A later statement such as:

    CREATE TABLE customers (...);

creates a table inside the selected database.

A common lifecycle is therefore:

    server
      ↓
    create database
      ↓
    connect to database
      ↓
    create schema / tables
      ↓
    insert and query data
      ↓
    backup / maintain
      ↓
    migrate / upgrade
      ↓
    archive or drop database

Database creation and table creation are separate concerns.
"""
    )


# ============================================================================
# 3. DATABASE NAMING
# ============================================================================

DATABASE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def validate_database_name(database_name: str) -> bool:
    """
    Validate a conservative database naming convention.

    This is intentionally stricter than many DBMSs. A real naming policy
    should be adapted to the selected DBMS and organizational conventions.
    """
    if not isinstance(database_name, str):
        return False

    return bool(DATABASE_NAME_PATTERN.fullmatch(database_name))


def demonstrate_database_naming() -> None:
    section("3. DATABASE NAMING")

    names = [
        "company_db",
        "sales",
        "sales_2026",
        "1sales",
        "SalesDB",
        "sales-db",
        "sales db",
        "",
        "_sales",
        "customer_data",
    ]

    print("Conservative naming rule:")
    print("  - starts with a lowercase letter")
    print("  - contains lowercase letters, digits, and underscores")
    print("  - maximum length: 63 characters for this example policy")
    print("  - avoids spaces, hyphens, and punctuation")
    print("  - avoids unnecessary quoting")

    print("\nValidation results:")
    for name in names:
        print(f"  {name!r:20} -> {validate_database_name(name)}")


def explain_database_naming_rules() -> None:
    subsection("Naming principles")

    print(
        """
Good database names should be:

    - descriptive
    - consistent
    - easy to type
    - stable over time
    - compatible with the target DBMS
    - free from accidental ambiguity

Examples:

    customer_db
    inventory_db
    analytics_db
    billing_db

Avoid names that depend on temporary business assumptions:

    final_db
    new_db
    latest_database
    test123
    database2

Environment naming requires additional discipline.

Examples:

    app_dev
    app_test
    app_staging
    app_prod

An organization may instead use separate database servers, clusters, cloud
projects, or namespaces for environments.

Do not assume that a naming rule valid for one DBMS is universally valid.
Reserved words, maximum identifier lengths, case folding, and permitted
characters vary between systems.
"""
    )


# ============================================================================
# 4. IDENTIFIERS AND SQL INJECTION
# ============================================================================

def explain_identifier_safety() -> None:
    section("4. DATABASE NAMES ARE IDENTIFIERS, NOT VALUES")

    print(
        """
A database name is an SQL identifier.

This is different from a normal data value.

Data values can usually be parameterized:

    SELECT * FROM users WHERE username = ?;

A database identifier generally cannot be supplied through an ordinary
value parameter:

    CREATE DATABASE ?;

is not a portable solution.

This distinction is important when database names are supplied dynamically.

Never concatenate untrusted user input directly into SQL.

Unsafe conceptual pattern:

    sql = "CREATE DATABASE " + user_input

If user_input contains SQL syntax, the resulting command can become unsafe.

The preferred strategy is to avoid arbitrary dynamic identifiers whenever
possible. If dynamic names are genuinely required, validate them against a
strict allow-list or identifier policy and use the target DBMS's identifier
quoting mechanism where appropriate.

The conservative validator in this script accepts only:

    lowercase letters
    digits
    underscores

and requires the first character to be a lowercase letter.
"""
    )


# ============================================================================
# 5. SQLITE: EXECUTABLE DATABASE CREATION
# ============================================================================

@dataclass
class SQLiteDatabase:
    """
    Small lifecycle wrapper around an SQLite database.

    SQLite is used because it is available in Python's standard library and
    does not require a database server for this educational demonstration.
    """

    path: Path

    def exists(self) -> bool:
        """Return True when the database file exists."""
        return self.path.exists()

    def connect(self) -> sqlite3.Connection:
        """
        Open a connection.

        The actual database file is created by SQLite if it does not exist.
        """
        return sqlite3.connect(self.path)

    def create(self) -> None:
        """Create the SQLite database by opening and closing a connection."""
        with self.connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")

    def remove(self) -> None:
        """Remove the database file."""
        if self.path.exists():
            self.path.unlink()


def demonstrate_sqlite_creation() -> None:
    section("5. SQLITE DATABASE CREATION")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "learning.db"
        database = SQLiteDatabase(database_path)

        print(f"Database path before creation: {database_path}")
        print(f"Exists before creation:       {database.exists()}")

        database.create()

        print(f"Exists after creation:        {database.exists()}")
        print(f"File size after creation:     {database_path.stat().st_size} bytes")

        database.remove()

        print(f"Exists after deletion:         {database.exists()}")


# ============================================================================
# 6. CONNECTION MANAGEMENT
# ============================================================================

def demonstrate_connection_management() -> None:
    section("6. CONNECTION MANAGEMENT")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "connections.db"

        connection = sqlite3.connect(database_path)

        try:
            connection.execute("PRAGMA foreign_keys = ON")
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
                INSERT INTO products (product_name, price)
                VALUES (?, ?)
                """,
                ("Keyboard", 49.99),
            )

            connection.commit()

            rows = connection.execute(
                "SELECT product_id, product_name, price FROM products"
            ).fetchall()

            print("Rows:", rows)

        finally:
            connection.close()

        print("Connection closed safely.")

    print(
        """
Recommended lifecycle:

    open connection
        ↓
    configure connection
        ↓
    execute operations
        ↓
    commit successful transaction
        ↓
    close connection

Use context managers where possible because they reduce the chance of
leaking connections or forgetting to commit / roll back transactions.
"""
    )


@contextmanager
def managed_sqlite_connection(
    database_path: Path,
) -> Iterator[sqlite3.Connection]:
    """
    Context manager that provides predictable connection cleanup.

    A successful context commits. An exception causes rollback. The connection
    is always closed after leaving the context.
    """
    connection = sqlite3.connect(database_path)

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def demonstrate_managed_connection() -> None:
    section("7. MANAGED CONNECTION WITH COMMIT AND ROLLBACK")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "transactions.db"

        with managed_sqlite_connection(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE accounts (
                    account_id INTEGER PRIMARY KEY,
                    owner TEXT NOT NULL,
                    balance REAL NOT NULL
                )
                """
            )

        try:
            with managed_sqlite_connection(database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO accounts (owner, balance)
                    VALUES (?, ?)
                    """,
                    ("Alice", 1000.00),
                )

                connection.execute(
                    """
                    INSERT INTO accounts (owner, balance)
                    VALUES (?, ?)
                    """,
                    ("Bob", 500.00),
                )

        except sqlite3.Error as error:
            print("Unexpected database error:", error)

        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT owner, balance FROM accounts ORDER BY account_id"
            ).fetchall()

            print("Committed rows:", rows)


# ============================================================================
# 8. TRANSACTIONS DURING INITIALIZATION
# ============================================================================

def demonstrate_transaction_rollback() -> None:
    section("8. TRANSACTION FAILURE AND ROLLBACK")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "rollback.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL
                )
                """
            )
            connection.commit()

        try:
            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    "INSERT INTO users (username) VALUES (?)",
                    ("alice",),
                )

                # This violates the UNIQUE constraint.
                connection.execute(
                    "INSERT INTO users (username) VALUES (?)",
                    ("alice",),
                )

                connection.commit()

        except sqlite3.IntegrityError as error:
            print("Expected integrity error:", error)

        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT user_id, username FROM users"
            ).fetchall()

            print("Rows after failed transaction:", rows)

    print(
        """
A transaction provides an atomic unit of work.

If initialization contains several dependent operations, committing after
every individual statement can leave a partially initialized database.

A transaction can instead ensure that either the complete unit succeeds or
the unit is rolled back.
"""
    )


# ============================================================================
# 9. INITIAL DATABASE SCHEMA
# ============================================================================

INITIAL_SCHEMA = """
CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL,
    employee_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    salary REAL NOT NULL CHECK (salary >= 0),
    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

CREATE INDEX idx_employees_department
    ON employees(department_id);
"""


def initialize_schema(connection: sqlite3.Connection) -> None:
    """
    Create a small relational schema.

    executescript is appropriate here because this is trusted application
    source SQL, not untrusted user-generated SQL.
    """
    connection.executescript(INITIAL_SCHEMA)


def demonstrate_database_initialization() -> None:
    section("9. DATABASE INITIALIZATION")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "company.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")

            initialize_schema(connection)

            connection.execute(
                "INSERT INTO departments (department_name) VALUES (?)",
                ("Engineering",),
            )

            engineering_id = connection.execute(
                """
                SELECT department_id
                FROM departments
                WHERE department_name = ?
                """,
                ("Engineering",),
            ).fetchone()[0]

            connection.execute(
                """
                INSERT INTO employees
                    (department_id, employee_name, email, salary)
                VALUES (?, ?, ?, ?)
                """,
                (
                    engineering_id,
                    "Ravi",
                    "ravi@example.com",
                    85000.00,
                ),
            )

            connection.commit()

            rows = connection.execute(
                """
                SELECT
                    e.employee_name,
                    e.email,
                    d.department_name
                FROM employees AS e
                JOIN departments AS d
                    ON e.department_id = d.department_id
                """
            ).fetchall()

            print("Initialized data:")
            for row in rows:
                print(" ", row)


# ============================================================================
# 10. IDEMPOTENT DATABASE INITIALIZATION
# ============================================================================

def demonstrate_idempotent_initialization() -> None:
    section("10. IDEMPOTENT INITIALIZATION")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "idempotent.db"

        initialization_sql = """
        CREATE TABLE IF NOT EXISTS settings (
            setting_name TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        );

        INSERT OR IGNORE INTO settings (setting_name, setting_value)
        VALUES ('application_version', '1.0');
        """

        with sqlite3.connect(database_path) as connection:
            connection.executescript(initialization_sql)
            connection.commit()

        # Running the same initialization again does not fail.
        with sqlite3.connect(database_path) as connection:
            connection.executescript(initialization_sql)
            connection.commit()

            rows = connection.execute(
                "SELECT setting_name, setting_value FROM settings"
            ).fetchall()

        print("Settings after two initialization runs:", rows)

    print(
        """
Idempotent initialization means that repeating an operation does not create
an unintended different result.

Common SQL techniques include:

    CREATE TABLE IF NOT EXISTS ...
    CREATE SCHEMA IF NOT EXISTS ...
    CREATE INDEX IF NOT EXISTS ...

The exact syntax and behavior vary by DBMS.

Idempotency is especially useful for automated deployment and startup logic.
It does not mean that every migration should use IF NOT EXISTS. Schema
migration systems often need explicit version tracking and controlled
changes.
"""
    )


# ============================================================================
# 11. CHECKING DATABASE EXISTENCE
# ============================================================================

def database_file_exists(database_path: Path) -> bool:
    """Check whether an SQLite database file exists."""
    return database_path.is_file()


def demonstrate_existence_checks() -> None:
    section("11. CHECKING DATABASE EXISTENCE")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "existence.db"

        print("Before creation:", database_file_exists(database_path))

        with sqlite3.connect(database_path):
            pass

        print("After creation:", database_file_exists(database_path))

    print(
        """
Server-based DBMSs normally require a server-side existence check rather
than checking a local file.

Typical concepts include:

    PostgreSQL:
        SELECT datname FROM pg_database;

    MySQL / MariaDB:
        SHOW DATABASES;

    SQL Server:
        SELECT name FROM sys.databases;

The exact query should be selected for the target DBMS and privilege model.
"""
    )


# ============================================================================
# 12. DROP DATABASE AND DATABASE LIFECYCLE
# ============================================================================

def explain_database_lifecycle() -> None:
    section("12. DATABASE LIFECYCLE")

    print(
        """
A production database typically passes through several lifecycle stages.

1. Planning
   - identify purpose
   - define ownership
   - choose DBMS
   - establish naming conventions
   - determine environment

2. Provisioning
   - allocate server / managed service / storage
   - create database
   - configure access
   - establish backups

3. Initialization
   - create schemas
   - create tables
   - create constraints
   - create indexes
   - create required roles / permissions

4. Operation
   - applications connect
   - transactions execute
   - monitoring collects metrics
   - backups run
   - maintenance occurs

5. Evolution
   - migrations modify schema
   - indexes may be added or removed
   - compatibility must be preserved during deployments

6. Recovery
   - restore from backup
   - replay logs where supported
   - verify consistency
   - return application service to operation

7. Retirement
   - confirm the database is no longer required
   - export / archive required data
   - revoke access
   - retain required backups
   - remove the database

A destructive statement such as:

    DROP DATABASE company_db;

can permanently remove a database and should therefore be treated as a
high-risk administrative operation.
"""
    )


def demonstrate_sqlite_lifecycle() -> None:
    section("13. EXECUTABLE SQLITE LIFECYCLE")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "lifecycle.db"

        print("1. Planned path:", database_path)

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE lifecycle_events (
                    event_id INTEGER PRIMARY KEY,
                    event_name TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                INSERT INTO lifecycle_events (event_name, occurred_at)
                VALUES (?, datetime('now'))
                """,
                ("database_created",),
            )

            connection.commit()

        print("2. Created:", database_path.exists())

        with sqlite3.connect(database_path) as connection:
            events = connection.execute(
                """
                SELECT event_id, event_name, occurred_at
                FROM lifecycle_events
                """
            ).fetchall()

        print("3. Operational data:", events)

        database_path.unlink()

        print("4. Retired/deleted:", not database_path.exists())


# ============================================================================
# 14. CREATE DATABASE IF NOT EXISTS: IMPORTANT DISTINCTION
# ============================================================================

def explain_if_not_exists() -> None:
    section("14. CREATE DATABASE AND IF NOT EXISTS")

    print(
        """
Many database systems support a form of conditional creation, but the
syntax and concurrency semantics differ.

Conceptually:

    CREATE DATABASE IF NOT EXISTS company_db;

is intended to avoid an error when the database already exists.

Do not assume that all DBMSs support this exact syntax.

PostgreSQL historically differs here: CREATE DATABASE does not use the same
IF NOT EXISTS form as CREATE TABLE. An existence check may be performed
first, or administrative tooling may handle the operation.

A race condition can occur if two independent processes perform:

    1. check whether database exists
    2. if not, create database

Both processes can observe "does not exist" before either creates it.

Therefore, production automation should handle the DBMS's duplicate-object
or already-exists error safely rather than relying only on a non-atomic
check-then-create sequence.
"""
    )


# ============================================================================
# 15. CONNECTION PARAMETERS
# ============================================================================

@dataclass(frozen=True)
class ConnectionSettings:
    """
    Generic connection configuration.

    This structure deliberately does not contain a password.
    """

    host: str
    port: int
    database: str
    username: str


def demonstrate_connection_settings() -> None:
    section("15. CONNECTION SETTINGS")

    settings = ConnectionSettings(
        host="db.example.internal",
        port=5432,
        database="company_db",
        username="application_user",
    )

    print("Host:", settings.host)
    print("Port:", settings.port)
    print("Database:", settings.database)
    print("Username:", settings.username)

    print(
        """
A server-based database connection commonly needs:

    host
    port
    database name
    username
    authentication credentials
    optional SSL/TLS settings
    optional connection timeout
    optional application name

Do not hard-code production passwords in source code.

Prefer a secret manager, protected environment configuration, or an
equivalent secure configuration mechanism appropriate for the deployment.
"""
    )


# ============================================================================
# 16. SQLITE CONNECTION MODES
# ============================================================================

def demonstrate_sqlite_connection_modes() -> None:
    section("16. SQLITE CONNECTION MODES")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "modes.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "CREATE TABLE numbers (value INTEGER NOT NULL)"
            )
            connection.execute("INSERT INTO numbers VALUES (10)")
            connection.commit()

        # Read-only URI mode is useful when the application must not write.
        uri = f"file:{database_path.as_posix()}?mode=ro"

        with sqlite3.connect(uri, uri=True) as read_only_connection:
            value = read_only_connection.execute(
                "SELECT value FROM numbers"
            ).fetchone()[0]

            print("Read-only value:", value)

            try:
                read_only_connection.execute(
                    "INSERT INTO numbers VALUES (20)"
                )
            except sqlite3.OperationalError as error:
                print("Expected write failure in read-only mode:", error)


# ============================================================================
# 17. CONNECTION POOLING CONCEPT
# ============================================================================

def explain_connection_pooling() -> None:
    section("17. CONNECTION POOLING")

    print(
        """
Opening a database connection can involve authentication, network setup,
TLS negotiation, session initialization, and server-side resource
allocation.

For a high-throughput server application, repeatedly creating a new
connection for every request can be inefficient.

A connection pool maintains a bounded collection of reusable connections.

Conceptual flow:

    request
       ↓
    acquire connection from pool
       ↓
    execute transaction
       ↓
    commit / rollback
       ↓
    return connection to pool

Benefits:
    - lower connection setup overhead
    - bounded concurrent connections
    - improved latency
    - centralized connection configuration

Risks:
    - too many pooled connections can overload the database
    - leaked connections can exhaust the pool
    - stale connections may need health checks
    - transaction state must be cleaned before reuse
    - session-specific settings can accidentally leak between requests

SQLite normally does not need the same server-style pooling architecture
as PostgreSQL or MySQL because it is embedded and file-based. Its locking
and concurrency model are different.
"""
    )


# ============================================================================
# 18. CONNECTION TIMEOUTS AND LOCKING
# ============================================================================

def demonstrate_sqlite_timeout() -> None:
    section("18. CONNECTION TIMEOUT AND LOCK CONTENTION")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "locking.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "CREATE TABLE records (record_id INTEGER PRIMARY KEY)"
            )
            connection.commit()

        first_connection = sqlite3.connect(database_path, timeout=5.0)
        second_connection = sqlite3.connect(database_path, timeout=0.1)

        try:
            first_connection.execute("BEGIN EXCLUSIVE")

            try:
                second_connection.execute(
                    "INSERT INTO records (record_id) VALUES (?)",
                    (1,),
                )
                second_connection.commit()
            except sqlite3.OperationalError as error:
                print("Second connection encountered expected contention:")
                print(" ", error)

            first_connection.rollback()

        finally:
            first_connection.close()
            second_connection.close()

    print(
        """
Timeout configuration matters in concurrent applications.

A timeout is not a replacement for correct transaction design.

Long-running transactions can:
    - hold locks
    - block other work
    - increase latency
    - increase the chance of deadlocks in systems that support them
    - reduce throughput

Transactions should generally be kept as short as correctness permits.
"""
    )


# ============================================================================
# 19. FOREIGN KEYS AND CONNECTION INITIALIZATION
# ============================================================================

def demonstrate_connection_configuration() -> None:
    section("19. CONNECTION-LEVEL CONFIGURATION")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "foreign_keys.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")

            connection.execute(
                """
                CREATE TABLE parent (
                    parent_id INTEGER PRIMARY KEY
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE child (
                    child_id INTEGER PRIMARY KEY,
                    parent_id INTEGER NOT NULL,
                    FOREIGN KEY (parent_id)
                        REFERENCES parent(parent_id)
                )
                """
            )

            connection.commit()

            try:
                connection.execute(
                    "INSERT INTO child (parent_id) VALUES (?)",
                    (999,),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                print("Foreign-key protection:", error)


# ============================================================================
# 20. DATABASE METADATA
# ============================================================================

def demonstrate_sqlite_metadata() -> None:
    section("20. DATABASE METADATA")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "metadata.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE customers (
                    customer_id INTEGER PRIMARY KEY,
                    customer_name TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX idx_customers_name
                ON customers(customer_name)
                """
            )

            connection.commit()

            tables = connection.execute(
                """
                SELECT name, type
                FROM sqlite_master
                WHERE type IN ('table', 'index')
                ORDER BY type, name
                """
            ).fetchall()

            print("SQLite objects:")
            for object_name, object_type in tables:
                print(f"  {object_type:5} {object_name}")


# ============================================================================
# 21. CREATE DATABASE ACROSS DATABASE SYSTEMS
# ============================================================================

def show_vendor_comparison() -> None:
    section("21. DBMS COMPARISON")

    comparison = [
        (
            "PostgreSQL",
            "Server-based",
            "CREATE DATABASE name;",
            "Database is a server-managed logical container.",
        ),
        (
            "MySQL",
            "Server-based",
            "CREATE DATABASE name;",
            "CREATE SCHEMA is commonly treated as a synonym for CREATE DATABASE.",
        ),
        (
            "MariaDB",
            "Server-based",
            "CREATE DATABASE name;",
            "Supports database-level character set and collation options.",
        ),
        (
            "SQL Server",
            "Server-based",
            "CREATE DATABASE name;",
            "Database creation involves server-managed data and log files.",
        ),
        (
            "SQLite",
            "Embedded/file-based",
            "No CREATE DATABASE statement",
            "Opening a database file creates it if necessary.",
        ),
    ]

    print(
        f"{'DBMS':<15} {'Architecture':<18} {'Creation':<35} Description"
    )
    print("-" * 110)

    for row in comparison:
        print(f"{row[0]:<15} {row[1]:<18} {row[2]:<35} {row[3]}")


# ============================================================================
# 22. DATABASE OPTIONS
# ============================================================================

def explain_database_options() -> None:
    section("22. DATABASE CREATION OPTIONS")

    print(
        """
Depending on the DBMS, database creation can include options such as:

    - owner
    - default tablespace
    - character encoding
    - collation
    - locale
    - compatibility level
    - data file location
    - log file location
    - initial size
    - growth configuration
    - template database
    - encryption-related configuration

These options affect behavior and operations.

Character encoding:
    Determines how text is represented.

Collation:
    Controls rules for comparing and ordering text.

Locale:
    Can affect language-sensitive behavior.

Storage configuration:
    Controls where and how database files are stored.

Do not blindly copy database creation options from one environment to
another. Environment-specific storage paths, ownership, locale, capacity,
and security requirements can differ.
"""
    )


# ============================================================================
# 23. DATABASE CREATION PRIVILEGES
# ============================================================================

def explain_privileges() -> None:
    section("23. PRIVILEGES REQUIRED TO CREATE DATABASES")

    print(
        """
Creating a database is usually an administrative operation.

A normal application account should generally not have unrestricted
CREATE DATABASE or DROP DATABASE privileges.

Separate responsibilities:

    Database administrator / infrastructure identity
        - creates databases
        - manages storage
        - manages high-level security

    Migration identity
        - changes application schema
        - creates tables / indexes where permitted

    Application identity
        - performs required application data operations
        - normally does not create or drop the database

Principle of least privilege means granting only the permissions required
for a specific role.

A compromised application credential with database-creation or database-
deletion privileges has a much larger blast radius than a credential that
can only read and modify application tables.
"""
    )


# ============================================================================
# 24. SECURITY CONSIDERATIONS
# ============================================================================

def explain_security() -> None:
    section("24. SECURITY CONSIDERATIONS")

    print(
        """
Important security controls around database creation and lifecycle include:

1. Authentication
   Use strong, appropriately managed authentication.

2. Authorization
   Restrict CREATE DATABASE, ALTER DATABASE, and DROP DATABASE privileges.

3. Network security
   Restrict which systems can connect to database servers.

4. Encryption in transit
   Use TLS where supported and required.

5. Encryption at rest
   Protect database storage and backups according to the sensitivity of
   the stored information.

6. Secret management
   Never embed production passwords in source code or commit them to version
   control.

7. Auditing
   Record important administrative events where appropriate.

8. Backup protection
   Backups can contain the same sensitive information as the live database.

9. Identifier validation
   Never directly concatenate arbitrary external input into administrative
   SQL statements.

10. Destructive-operation controls
    DROP DATABASE should require explicit authorization and ideally an
    additional operational safeguard.

11. Environment separation
    Development credentials and databases should not automatically provide
    production access.

Security is part of database lifecycle management, not an isolated task
performed only after database creation.
"""
    )


# ============================================================================
# 25. BACKUP AND RESTORE
# ============================================================================

def demonstrate_sqlite_backup() -> None:
    section("25. SQLITE BACKUP AND RESTORE")

    with tempfile.TemporaryDirectory() as temporary_directory:
        source_path = Path(temporary_directory) / "source.db"
        backup_path = Path(temporary_directory) / "backup.db"
        restored_path = Path(temporary_directory) / "restored.db"

        with sqlite3.connect(source_path) as source:
            source.execute(
                """
                CREATE TABLE important_data (
                    item_id INTEGER PRIMARY KEY,
                    item_name TEXT NOT NULL
                )
                """
            )

            source.execute(
                """
                INSERT INTO important_data (item_name)
                VALUES (?), (?), (?)
                """,
                ("A", "B", "C"),
            )

            source.commit()

        with sqlite3.connect(source_path) as source, sqlite3.connect(
            backup_path
        ) as backup:
            source.backup(backup)

        with sqlite3.connect(backup_path) as backup, sqlite3.connect(
            restored_path
        ) as restored:
            backup.backup(restored)

        with sqlite3.connect(restored_path) as restored:
            rows = restored.execute(
                "SELECT item_id, item_name FROM important_data"
            ).fetchall()

        print("Restored rows:", rows)


def explain_backup_lifecycle() -> None:
    subsection("Backup principles")

    print(
        """
A database lifecycle is incomplete without recovery planning.

Important concepts:

    RPO - Recovery Point Objective
        How much recent data can the organization afford to lose?

    RTO - Recovery Time Objective
        How long can recovery take before the service must be restored?

Backup strategies can include:

    - full backups
    - incremental backups
    - differential backups
    - transaction-log / WAL-based recovery
    - snapshots
    - managed service backups

A backup that has never been tested is not sufficient evidence of
recoverability.

Restore testing verifies that:
    - the backup is readable
    - credentials and permissions work
    - the expected data exists
    - application compatibility is preserved
    - recovery time is acceptable
"""
    )


# ============================================================================
# 26. MIGRATIONS
# ============================================================================

def demonstrate_schema_migration() -> None:
    section("26. DATABASE SCHEMA MIGRATION")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "migration.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE customers (
                    customer_id INTEGER PRIMARY KEY,
                    customer_name TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                INSERT INTO customers (customer_name)
                VALUES (?)
                """,
                ("Alice",),
            )

            connection.commit()

            # Migration: add a new nullable column.
            connection.execute(
                """
                ALTER TABLE customers
                ADD COLUMN email TEXT
                """
            )

            connection.execute(
                """
                UPDATE customers
                SET email = ?
                WHERE customer_name = ?
                """,
                ("alice@example.com", "Alice"),
            )

            connection.commit()

            row = connection.execute(
                """
                SELECT customer_id, customer_name, email
                FROM customers
                """
            ).fetchone()

            print("After migration:", row)

    print(
        """
A migration is a controlled change to an existing database schema.

Production migrations should be:

    - versioned
    - repeatable or safely detectable
    - tested
    - observable
    - compatible with deployment order
    - reversible where practical

A major operational concern is backward compatibility.

For example, removing a column immediately can break an older application
version that still expects that column.

A safer deployment can use an expand-and-contract strategy:

    1. Expand:
       add the new structure without breaking the old application.

    2. Deploy:
       update application code to use the new structure.

    3. Migrate:
       move or backfill data.

    4. Contract:
       remove obsolete structures only after they are no longer needed.
"""
    )


# ============================================================================
# 27. PERFORMANCE CONSIDERATIONS
# ============================================================================

def explain_performance() -> None:
    section("27. PERFORMANCE CONSIDERATIONS")

    print(
        """
Database creation itself is usually an administrative event rather than
a high-frequency application operation. Performance considerations become
more important after creation.

Important factors include:

    Connection management
        Reusing connections or using an appropriate pool can reduce
        connection establishment overhead.

    Transactions
        Proper transaction boundaries improve consistency and can reduce
        unnecessary commit overhead.

    Indexes
        Indexes accelerate suitable reads but consume storage and make
        writes more expensive.

    Connection count
        Too many concurrent database connections can exhaust server memory
        and other resources.

    Schema initialization
        Large indexes and data backfills can make deployments expensive.

    Locking
        Long transactions can block other work depending on the DBMS.

    Maintenance
        Statistics, vacuuming, compaction, checkpointing, and related
        operations vary by DBMS.

Performance should be measured using the actual workload rather than
assuming that one configuration is optimal.
"""
    )


# ============================================================================
# 28. ERROR HANDLING
# ============================================================================

def demonstrate_database_error_handling() -> None:
    section("28. DATABASE ERROR HANDLING")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "errors.db"

        try:
            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE accounts (
                        account_id INTEGER PRIMARY KEY,
                        account_name TEXT UNIQUE NOT NULL
                    )
                    """
                )

                connection.execute(
                    """
                    INSERT INTO accounts (account_name)
                    VALUES (?)
                    """,
                    ("primary",),
                )

                connection.commit()

                try:
                    connection.execute(
                        """
                        INSERT INTO accounts (account_name)
                        VALUES (?)
                        """,
                        ("primary",),
                    )
                    connection.commit()
                except sqlite3.IntegrityError as error:
                    connection.rollback()
                    print("Handled integrity error:", error)

        except sqlite3.Error as error:
            print("Handled SQLite error:", error)


def explain_common_errors() -> None:
    subsection("Common database creation and connection errors")

    print(
        """
Examples include:

    Permission denied
        The current identity cannot create or access the database.

    Database already exists
        Creation conflicts with an existing database.

    Invalid identifier
        The database name violates DBMS-specific identifier rules.

    Invalid option
        A CREATE DATABASE option is unsupported or incorrectly specified.

    Authentication failure
        Credentials or authentication configuration are incorrect.

    Connection refused
        The server is unavailable or not accepting connections.

    Network timeout
        A server cannot be reached within the configured time.

    Resource exhaustion
        Storage, memory, file descriptors, connection slots, or other
        resources are insufficient.

    Lock timeout
        Another operation holds a lock longer than permitted.

    Constraint violation
        Data operations violate schema constraints.

Production systems should distinguish expected operational errors from
unexpected programming errors and should log enough information for
diagnosis without exposing secrets.
"""
    )


# ============================================================================
# 29. RETRIES
# ============================================================================

def retry_operation(
    operation,
    attempts: int = 3,
    delay_seconds: float = 0.1,
):
    """
    Retry a transient operation.

    This is deliberately generic. Production retry policies should identify
    which database errors are genuinely transient before retrying.
    """
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except sqlite3.OperationalError as error:
            last_error = error

            if attempt == attempts:
                raise

            time.sleep(delay_seconds * attempt)

    raise last_error  # Defensive; normally unreachable.


def demonstrate_retry_pattern() -> None:
    section("29. RETRY STRATEGIES")

    counter = {"attempts": 0}

    def occasionally_fails():
        counter["attempts"] += 1

        if counter["attempts"] < 3:
            raise sqlite3.OperationalError("simulated transient failure")

        return "operation succeeded"

    result = retry_operation(occasionally_fails)

    print("Retry result:", result)
    print("Attempts:", counter["attempts"])

    print(
        """
Retries should be used carefully.

Good candidates:
    - transient network failures
    - temporary connection failures
    - some lock/contention situations

Bad candidates:
    - syntax errors
    - invalid credentials
    - permission errors
    - invalid database names
    - deterministic constraint violations

Retries should use bounded attempts and preferably backoff.

Do not blindly retry non-idempotent operations because a timeout can occur
after the server has already committed the operation. Retrying such an
operation may duplicate the effect.
"""
    )


# ============================================================================
# 30. ENVIRONMENT CONFIGURATION
# ============================================================================

def get_database_name_from_environment(
    environment: Optional[dict[str, str]] = None,
) -> str:
    """
    Read a database name from an environment mapping.

    The default source is os.environ, while an explicit mapping makes the
    function deterministic and easy to test.
    """
    source = os.environ if environment is None else environment

    database_name = source.get("APP_DATABASE", "app_dev")

    if not validate_database_name(database_name):
        raise ValueError(
            f"Invalid database name: {database_name!r}"
        )

    return database_name


def demonstrate_environment_configuration() -> None:
    section("30. ENVIRONMENT-BASED DATABASE CONFIGURATION")

    test_environment = {
        "APP_DATABASE": "company_prod",
    }

    print(
        "Validated database name:",
        get_database_name_from_environment(test_environment),
    )

    print(
        """
Configuration should normally separate:

    code
    from
    environment-specific settings
    from
    secrets

Examples:

    Development:
        APP_DATABASE=company_dev

    Testing:
        APP_DATABASE=company_test

    Production:
        APP_DATABASE=company_prod

Do not assume that changing only the database name is enough to isolate
environments. The host, credentials, network, storage, encryption, and
permissions also need appropriate separation.
"""
    )


# ============================================================================
# 31. DATABASE HEALTH CHECK
# ============================================================================

def database_health_check(database_path: Path) -> dict[str, object]:
    """
    Perform a small SQLite health check.

    A real production health check should be designed around the DBMS and
    service architecture.
    """
    result: dict[str, object] = {
        "exists": database_path.exists(),
        "readable": False,
        "query_ok": False,
    }

    if not database_path.exists():
        return result

    try:
        with sqlite3.connect(database_path, timeout=1.0) as connection:
            result["readable"] = True

            connection.execute("SELECT 1").fetchone()
            result["query_ok"] = True

    except sqlite3.Error:
        pass

    return result


def demonstrate_health_check() -> None:
    section("31. DATABASE HEALTH CHECK")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "health.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute("CREATE TABLE health (value INTEGER)")
            connection.commit()

        print(database_health_check(database_path))

        missing_path = Path(temporary_directory) / "missing.db"

        print(database_health_check(missing_path))


# ============================================================================
# 32. DATABASE STATE MODEL
# ============================================================================

class DatabaseLifecycleState:
    """
    Small state model for teaching lifecycle transitions.

    This is an application-level model, not a replacement for DBMS state.
    """

    PLANNED = "planned"
    CREATED = "created"
    INITIALIZED = "initialized"
    OPERATIONAL = "operational"
    RETIRED = "retired"


@dataclass
class LifecycleTracker:
    state: str = DatabaseLifecycleState.PLANNED

    def create(self) -> None:
        if self.state != DatabaseLifecycleState.PLANNED:
            raise RuntimeError(
                f"Cannot create from state {self.state!r}"
            )

        self.state = DatabaseLifecycleState.CREATED

    def initialize(self) -> None:
        if self.state != DatabaseLifecycleState.CREATED:
            raise RuntimeError(
                f"Cannot initialize from state {self.state!r}"
            )

        self.state = DatabaseLifecycleState.INITIALIZED

    def activate(self) -> None:
        if self.state != DatabaseLifecycleState.INITIALIZED:
            raise RuntimeError(
                f"Cannot activate from state {self.state!r}"
            )

        self.state = DatabaseLifecycleState.OPERATIONAL

    def retire(self) -> None:
        if self.state not in (
            DatabaseLifecycleState.CREATED,
            DatabaseLifecycleState.INITIALIZED,
            DatabaseLifecycleState.OPERATIONAL,
        ):
            raise RuntimeError(
                f"Cannot retire from state {self.state!r}"
            )

        self.state = DatabaseLifecycleState.RETIRED


def demonstrate_lifecycle_state_machine() -> None:
    section("32. DATABASE LIFECYCLE STATE MODEL")

    tracker = LifecycleTracker()

    print("Initial state:", tracker.state)

    tracker.create()
    print("After creation:", tracker.state)

    tracker.initialize()
    print("After initialization:", tracker.state)

    tracker.activate()
    print("After activation:", tracker.state)

    tracker.retire()
    print("After retirement:", tracker.state)

    try:
        tracker.activate()
    except RuntimeError as error:
        print("Invalid transition correctly rejected:", error)


# ============================================================================
# 33. TESTING DATABASE INITIALIZATION
# ============================================================================

def test_database_initialization() -> None:
    """
    Lightweight executable test using only the standard library.
    """
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "test.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            initialize_schema(connection)

            table_names = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }

            assert "departments" in table_names
            assert "employees" in table_names

            connection.execute(
                "INSERT INTO departments (department_name) VALUES (?)",
                ("Finance",),
            )

            department_id = connection.execute(
                """
                SELECT department_id
                FROM departments
                WHERE department_name = ?
                """,
                ("Finance",),
            ).fetchone()[0]

            connection.execute(
                """
                INSERT INTO employees
                    (department_id, employee_name, email, salary)
                VALUES (?, ?, ?, ?)
                """,
                (
                    department_id,
                    "Maya",
                    "maya@example.com",
                    70000.0,
                ),
            )

            connection.commit()

            count = connection.execute(
                "SELECT COUNT(*) FROM employees"
            ).fetchone()[0]

            assert count == 1


def test_database_name_validation() -> None:
    """Test the conservative database naming policy."""
    assert validate_database_name("company_db")
    assert validate_database_name("a")
    assert validate_database_name("app2026")

    assert not validate_database_name("")
    assert not validate_database_name("1company")
    assert not validate_database_name("company-db")
    assert not validate_database_name("company db")
    assert not validate_database_name("Company_DB")
    assert not validate_database_name("company.db")


def test_transaction_rollback() -> None:
    """Verify that an integrity error does not leave duplicate data."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "test_rollback.db"

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL
                )
                """
            )
            connection.commit()

        try:
            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    "INSERT INTO users (username) VALUES (?)",
                    ("alice",),
                )

                connection.execute(
                    "INSERT INTO users (username) VALUES (?)",
                    ("alice",),
                )

                connection.commit()

        except sqlite3.IntegrityError:
            pass

        with sqlite3.connect(database_path) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0]

            assert count == 0


def run_tests() -> None:
    section("33. BUILT-IN TESTS")

    tests = [
        test_database_name_validation,
        test_database_initialization,
        test_transaction_rollback,
    ]

    passed = 0

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
        passed += 1

    print(f"\n{passed}/{len(tests)} tests passed.")


# ============================================================================
# 34. COMMON MISTAKES
# ============================================================================

def explain_common_mistakes() -> None:
    section("34. COMMON MISTAKES")

    mistakes = [
        (
            "Giving the application unrestricted database privileges",
            "Use least privilege and separate administrative identities.",
        ),
        (
            "Hard-coding production passwords",
            "Use secure secret management.",
        ),
        (
            "Using arbitrary user input as a database identifier",
            "Validate identifiers and use DBMS-specific identifier quoting.",
        ),
        (
            "Assuming every DBMS supports CREATE DATABASE identically",
            "Check the target DBMS syntax and semantics.",
        ),
        (
            "Confusing a database with a table",
            "A database is a higher-level container; tables store structured data.",
        ),
        (
            "Opening connections without closing them",
            "Use context managers or disciplined pool management.",
        ),
        (
            "Forgetting to commit",
            "Understand transaction boundaries and commit successful work.",
        ),
        (
            "Ignoring rollback after errors",
            "Roll back failed transactions before continuing.",
        ),
        (
            "Creating indexes without considering write cost",
            "Index only according to workload and query requirements.",
        ),
        (
            "Deleting a database without verifying backups",
            "Treat destructive lifecycle operations as controlled administrative actions.",
        ),
        (
            "Using retries for every error",
            "Retry only errors known to be transient and safe to retry.",
        ),
        (
            "Running destructive migrations immediately",
            "Use compatibility-aware deployment strategies.",
        ),
    ]

    for mistake, correction in mistakes:
        print(f"\nMistake:   {mistake}")
        print(f"Practice:  {correction}")


# ============================================================================
# 35. PRODUCTION CHECKLIST
# ============================================================================

def production_checklist() -> None:
    section("35. PRODUCTION DATABASE CREATION CHECKLIST")

    checklist = [
        "Choose the appropriate DBMS and deployment architecture.",
        "Define a stable database naming convention.",
        "Select the correct environment.",
        "Create the database using an authorized administrative identity.",
        "Configure encoding, collation, locale, and storage options as required.",
        "Create required schemas and database objects.",
        "Create roles and permissions according to least privilege.",
        "Configure secure network access.",
        "Enable encryption where required.",
        "Configure connection timeouts and appropriate pooling.",
        "Initialize the schema through version-controlled migrations.",
        "Verify constraints and indexes.",
        "Configure backups.",
        "Test restoration.",
        "Configure monitoring and alerting.",
        "Document ownership and operational responsibilities.",
        "Test application connectivity.",
        "Plan schema migration compatibility.",
        "Protect destructive operations.",
        "Define retirement and data-retention procedures.",
    ]

    for number, item in enumerate(checklist, start=1):
        print(f"[ ] {number:02}. {item}")


# ============================================================================
# 36. ADVANCED DESIGN DISCUSSION
# ============================================================================

def explain_advanced_design() -> None:
    section("36. ADVANCED DATABASE DESIGN CONSIDERATIONS")

    print(
        """
Database creation is often the first technical step in a larger
architecture decision.

Database-per-application:
    Each application receives its own database.
    Benefits include stronger isolation and simpler ownership boundaries.
    Costs include additional administration and operational overhead.

Database-per-tenant:
    Each customer receives a separate database.
    This can provide strong isolation but can become operationally expensive
    at very large tenant counts.

Schema-per-tenant:
    Tenants share a database but receive separate schemas.
    This can improve isolation compared with a shared schema while avoiding
    the cost of thousands of database instances.

Shared schema:
    Tenant identity is stored in rows, often using a tenant_id column.
    This is operationally efficient but requires rigorous authorization and
    query isolation.

Read replicas:
    A primary database handles writes while replicas serve eligible reads.
    Replication behavior and consistency vary by DBMS.

High availability:
    Multiple database instances can be used to reduce downtime.
    Failover architecture depends on the DBMS and infrastructure.

Sharding:
    Data is distributed across multiple database nodes.
    This can increase scalability but introduces routing, consistency,
    transaction, operational, and debugging complexity.

Managed database services:
    Cloud platforms can automate provisioning, backups, patching,
    monitoring, and failover. They do not eliminate the need for correct
    schema design, access control, backup validation, or lifecycle planning.
"""
    )


# ============================================================================
# 37. OBSERVABILITY
# ============================================================================

def explain_observability() -> None:
    section("37. DATABASE OBSERVABILITY")

    print(
        """
A production database should be observable.

Useful signals include:

    Availability
        Can applications connect?

    Latency
        How long do queries and transactions take?

    Errors
        Which operations fail and why?

    Connections
        Are connection pools or server connection limits exhausted?

    Locks
        Are transactions blocking other transactions?

    Storage
        Is disk capacity approaching a critical threshold?

    Replication
        Are replicas current?

    Backups
        Did scheduled backups complete successfully?

    Resource utilization
        CPU, memory, I/O, cache behavior, and related DBMS metrics.

Administrative actions such as database creation and deletion may also
need auditing.
"""
    )


# ============================================================================
# 38. COMPLETE DEMONSTRATION
# ============================================================================

def run_all_demonstrations() -> None:
    """
    Execute the complete educational sequence.
    """
    explain_database_basics()
    show_create_database_syntax()
    explain_create_database_semantics()
    demonstrate_database_naming()
    explain_database_naming_rules()
    explain_identifier_safety()
    demonstrate_sqlite_creation()
    demonstrate_connection_management()
    demonstrate_managed_connection()
    demonstrate_transaction_rollback()
    demonstrate_database_initialization()
    demonstrate_idempotent_initialization()
    demonstrate_existence_checks()
    explain_database_lifecycle()
    demonstrate_sqlite_lifecycle()
    explain_if_not_exists()
    demonstrate_connection_settings()
    demonstrate_sqlite_connection_modes()
    explain_connection_pooling()
    demonstrate_sqlite_timeout()
    demonstrate_connection_configuration()
    demonstrate_sqlite_metadata()
    show_vendor_comparison()
    explain_database_options()
    explain_privileges()
    explain_security()
    demonstrate_sqlite_backup()
    explain_backup_lifecycle()
    demonstrate_schema_migration()
    explain_performance()
    demonstrate_database_error_handling()
    explain_common_errors()
    demonstrate_retry_pattern()
    demonstrate_environment_configuration()
    demonstrate_health_check()
    demonstrate_lifecycle_state_machine()
    run_tests()
    explain_common_mistakes()
    production_checklist()
    explain_advanced_design()
    explain_observability()


# ============================================================================
# 39. MAIN ENTRY POINT
# ============================================================================

def main() -> None:
    """
    Entry point for the complete study script.

    The script uses temporary databases, so running it does not create
    permanent database files in the current working directory.
    """
    print("CREATING DATABASES: COMPLETE PYTHON STUDY SCRIPT")
    print("Executable examples use Python's built-in sqlite3 module.")

    run_all_demonstrations()

    section("END OF STUDY SCRIPT")
    print(
        """
The examples demonstrated database creation concepts, naming, connection
management, transactions, initialization, lifecycle, security, backup,
migration, testing, and production considerations.
"""
    )


if __name__ == "__main__":
    main()
