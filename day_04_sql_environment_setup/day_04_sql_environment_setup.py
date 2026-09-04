"""
SQL Environment Setup with PostgreSQL

This standalone study script teaches PostgreSQL environment setup from absolute
beginner level through advanced operational concepts.

Topics covered:
    1. What PostgreSQL is and how its architecture works
    2. PostgreSQL installation concepts on Windows, macOS, and Linux
    3. PostgreSQL server, cluster, instance, database, schema, and role concepts
    4. Starting, stopping, and checking the PostgreSQL service
    5. PostgreSQL command-line tools
    6. Connecting with psql
    7. Connection parameters and connection strings
    8. Creating and deleting databases
    9. Creating users and roles
    10. Database ownership and privileges
    11. Schemas and search_path
    12. Basic psql navigation
    13. Executing SQL through psql
    14. Transactions in psql
    15. Environment variables and .pgpass
    16. PostgreSQL configuration concepts
    17. Port and network configuration
    18. Authentication through pg_hba.conf
    19. pgAdmin concepts and workflows
    20. Common connection failures and debugging
    21. Secure configuration practices
    22. Reproducible environment setup
    23. Programmatic connectivity from Python
    24. Connection pooling concepts
    25. Production-oriented considerations
    26. Environment validation and diagnostic helpers
    27. A complete local development setup demonstration

The script intentionally uses Python's standard library wherever possible.
PostgreSQL itself and its command-line utilities must be installed separately
because they are external system software.

Most examples are educational and are safe to study locally. Commands that
create or remove databases, roles, or files are either demonstrated as strings
or executed only when the user explicitly enables the corresponding operation.

Python version:
    Python 3.10+

PostgreSQL:
    A supported PostgreSQL release installed locally or available remotely.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


# ============================================================================
# 1. FOUNDATIONAL CONCEPTS
# ============================================================================

def print_section(title: str) -> None:
    """Print a consistent section heading."""
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_subsection(title: str) -> None:
    """Print a smaller heading inside a major section."""
    print()
    print("-" * 78)
    print(title)
    print("-" * 78)


def explain(text: str) -> None:
    """Print educational prose while keeping line lengths readable."""
    print(textwrap.dedent(text).strip())


def demonstrate(title: str, value: object) -> None:
    """Display a labeled value used by an educational example."""
    print(f"{title}: {value}")


def pause_briefly(seconds: float = 0.1) -> None:
    """
    Give some systems a moment between demonstrations.

    This is intentionally short. It is not a PostgreSQL requirement.
    """
    time.sleep(seconds)


# PostgreSQL terminology:
#
# PostgreSQL:
#     The database management system.
#
# Server:
#     The PostgreSQL server process that accepts client connections.
#
# Cluster:
#     A PostgreSQL data directory containing one PostgreSQL database cluster.
#     A cluster contains databases, roles, configuration, and system catalogs.
#
# Database:
#     A logical database inside a PostgreSQL cluster.
#
# Schema:
#     A namespace inside a database that can contain tables, views, functions,
#     types, sequences, and other database objects.
#
# Role:
#     PostgreSQL's security principal abstraction. A role can behave as a
#     login user, a group role, or both.
#
# Client:
#     A program that connects to PostgreSQL. Examples include psql, pgAdmin,
#     application programs, and migration tools.
#
# psql:
#     PostgreSQL's interactive command-line client.
#
# pgAdmin:
#     A graphical administration client for PostgreSQL.
#
# libpq:
#     PostgreSQL's standard client library. Many PostgreSQL client programs
#     use its connection semantics.
#
# Port:
#     The TCP port on which PostgreSQL listens. The conventional default is
#     5432, although production environments often use different values.
#
# Host:
#     The network address where the PostgreSQL server can be reached.
#
# Authentication:
#     Determining whether a connection attempt is allowed to identify itself
#     as a particular PostgreSQL role.
#
# Authorization:
#     Determining which database objects and operations that role can use.


def demonstrate_postgresql_vocabulary() -> None:
    print_section("1. PostgreSQL Vocabulary")

    vocabulary = {
        "DBMS": "Database management system",
        "PostgreSQL server": "Server software accepting database connections",
        "Cluster": "A PostgreSQL data directory containing databases and roles",
        "Database": "A logical database within a PostgreSQL cluster",
        "Schema": "A namespace for objects within a database",
        "Role": "A PostgreSQL identity used for login and privileges",
        "psql": "PostgreSQL command-line client",
        "pgAdmin": "Graphical PostgreSQL administration client",
        "Host": "Machine or network address running PostgreSQL",
        "Port": "TCP endpoint used by the PostgreSQL server",
        "Authentication": "Checking connection identity and access rules",
        "Authorization": "Checking permissions after authentication",
    }

    for term, definition in vocabulary.items():
        print(f"{term:<22} -> {definition}")

    explain(
        """
        A common beginner mistake is to treat "PostgreSQL", "database", and
        "server" as interchangeable words.

        PostgreSQL is the database system. The server is the running PostgreSQL
        service. A PostgreSQL server can manage a cluster, and a cluster can
        contain multiple databases. A database can contain multiple schemas.

        A useful mental model is:

            PostgreSQL installation
                    |
                    v
            PostgreSQL server
                    |
                    v
              database cluster
                    |
             +------+------+
             |             |
             v             v
          database A    database B
             |
             v
          schemas
             |
             v
          tables / views / functions / sequences

        Roles are security identities associated with the PostgreSQL cluster.
        They are not simply objects belonging to one database.
        """
    )


# ============================================================================
# 2. OPERATING SYSTEM INFORMATION
# ============================================================================

def show_operating_system_information() -> None:
    print_section("2. Operating System and Python Environment")

    demonstrate("Operating system", platform.system())
    demonstrate("OS release", platform.release())
    demonstrate("Architecture", platform.machine())
    demonstrate("Python version", platform.python_version())
    demonstrate("Python executable", sys.executable)
    demonstrate("Current working directory", Path.cwd())

    explain(
        """
        Installation commands differ by operating system.

        Windows:
            PostgreSQL is commonly installed using the official installer.
            The installer can provide PostgreSQL Server, command-line tools,
            pgAdmin, and Stack Builder.

        Ubuntu/Debian:
            PostgreSQL can be installed through the distribution package
            manager or the PostgreSQL project's package repository.

        macOS:
            PostgreSQL can be installed through the official installer,
            Homebrew, or another package-management mechanism.

        The important principle is that Python does not install PostgreSQL
        itself. Python applications are PostgreSQL clients. The database
        server is separate system software.
        """
    )


# ============================================================================
# 3. DETECT POSTGRESQL CLIENT TOOLS
# ============================================================================

@dataclass
class CommandAvailability:
    """Describe whether a command exists on PATH."""

    command: str
    path: Optional[str]

    @property
    def available(self) -> bool:
        return self.path is not None


def find_command(command: str) -> CommandAvailability:
    """Locate a command using the operating system PATH."""
    return CommandAvailability(command=command, path=shutil.which(command))


def show_postgresql_client_tools() -> None:
    print_section("3. PostgreSQL Command-Line Tools")

    commands = [
        "psql",
        "pg_isready",
        "createdb",
        "dropdb",
        "createuser",
        "dropuser",
        "pg_dump",
        "pg_restore",
        "pg_config",
    ]

    for command in commands:
        availability = find_command(command)
        status = availability.path if availability.available else "NOT FOUND"
        print(f"{command:<15} -> {status}")

    explain(
        """
        These tools are normally installed with PostgreSQL's client/server
        packages.

        psql:
            Interactive SQL client.

        pg_isready:
            Checks whether a PostgreSQL server is accepting connections.

        createdb:
            Command-line utility for creating a database.

        dropdb:
            Command-line utility for dropping a database.

        createuser:
            Command-line utility for creating PostgreSQL roles.

        dropuser:
            Command-line utility for dropping PostgreSQL roles.

        pg_dump:
            Produces a logical backup of a database.

        pg_restore:
            Restores a backup created in an appropriate archive format.

        pg_config:
            Reports information about a PostgreSQL installation.

        A command being absent from PATH does not necessarily mean PostgreSQL
        is not installed. The executable may exist outside PATH.
        """
    )


# ============================================================================
# 4. SAFE COMMAND EXECUTION
# ============================================================================

@dataclass
class CommandResult:
    """Result returned by a subprocess execution."""

    command: list[str]
    return_code: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0


def run_command(
    command: list[str],
    *,
    timeout: int = 15,
    input_text: Optional[str] = None,
) -> CommandResult:
    """
    Execute a system command safely.

    shell=False is deliberate. It avoids unnecessary shell interpretation and
    reduces command-injection risk when arguments originate from user input.
    """
    try:
        completed = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except FileNotFoundError:
        return CommandResult(
            command=command,
            return_code=127,
            stdout="",
            stderr=f"Command not found: {command[0]}",
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            command=command,
            return_code=124,
            stdout=exc.stdout or "",
            stderr=f"Command timed out after {timeout} seconds.",
        )
    except OSError as exc:
        return CommandResult(
            command=command,
            return_code=1,
            stdout="",
            stderr=str(exc),
        )

    return CommandResult(
        command=command,
        return_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def print_command_result(result: CommandResult) -> None:
    """Display a subprocess result without hiding diagnostic information."""
    print(f"$ {' '.join(result.command)}")
    print(f"Return code: {result.return_code}")

    if result.stdout.strip():
        print("STDOUT:")
        print(result.stdout.strip())

    if result.stderr.strip():
        print("STDERR:")
        print(result.stderr.strip())


# ============================================================================
# 5. CHECK SERVER READINESS
# ============================================================================

def check_server_readiness(
    host: str = "localhost",
    port: int = 5432,
) -> bool:
    """
    Use pg_isready when available to check whether PostgreSQL accepts requests.

    This is a readiness check, not a proof that a particular user can log in.
    Authentication can still fail after the server is ready.
    """
    command = find_command("pg_isready")

    if not command.available:
        print("pg_isready is not available on PATH.")
        return False

    result = run_command(
        [
            command.path,
            "--host",
            host,
            "--port",
            str(port),
        ]
    )

    print_command_result(result)
    return result.succeeded


def check_tcp_port(
    host: str = "localhost",
    port: int = 5432,
    timeout: float = 1.5,
) -> bool:
    """
    Perform a basic TCP connectivity test.

    A successful TCP connection means something is listening on that endpoint.
    It does not prove that the listener is PostgreSQL or that authentication
    will succeed.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def demonstrate_server_readiness() -> None:
    print_section("4. PostgreSQL Server Readiness")

    host = os.getenv("PGHOST", "localhost")
    port_text = os.getenv("PGPORT", "5432")

    try:
        port = int(port_text)
    except ValueError:
        port = 5432

    print(f"Checking host={host!r}, port={port}")

    tcp_available = check_tcp_port(host, port)
    print(f"TCP endpoint reachable: {tcp_available}")

    if find_command("pg_isready").available:
        ready = check_server_readiness(host, port)
        print(f"PostgreSQL readiness command succeeded: {ready}")
    else:
        print(
            "Install PostgreSQL client tools or add their binary directory "
            "to PATH to use pg_isready."
        )

    explain(
        """
        There are several distinct failure layers:

        1. DNS or hostname resolution failure
        2. Network route failure
        3. TCP connection refusal
        4. PostgreSQL server not accepting connections
        5. pg_hba.conf authentication rejection
        6. Password authentication failure
        7. Database does not exist
        8. Role does not exist
        9. Role lacks CONNECT permission
        10. TLS/SSL negotiation failure

        Treating all connection failures as "wrong password" makes debugging
        much slower.
        """
    )


# ============================================================================
# 6. CONNECTION PARAMETERS
# ============================================================================

@dataclass
class PostgreSQLConnectionParameters:
    """
    Standard connection parameters.

    Password is intentionally omitted from __repr__ by not storing it here.
    Applications should avoid logging database passwords.
    """

    host: str = "localhost"
    port: int = 5432
    database: str = "postgres"
    user: str = "postgres"
    sslmode: Optional[str] = None

    def as_dict(self) -> dict[str, object]:
        """Return non-secret connection parameters."""
        values: dict[str, object] = {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
        }

        if self.sslmode:
            values["sslmode"] = self.sslmode

        return values


def get_environment_connection_parameters() -> PostgreSQLConnectionParameters:
    """
    Read standard PostgreSQL connection environment variables.

    PGHOST:
        Server hostname.

    PGPORT:
        Server port.

    PGDATABASE:
        Default database.

    PGUSER:
        Default user.

    PGPASSWORD:
        Password. It is deliberately not returned by this helper because
        passwords should not be printed or accidentally logged.

    PGSSLMODE:
        SSL behavior requested by the client.
    """
    port_text = os.getenv("PGPORT", "5432")

    try:
        port = int(port_text)
    except ValueError:
        port = 5432

    return PostgreSQLConnectionParameters(
        host=os.getenv("PGHOST", "localhost"),
        port=port,
        database=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        sslmode=os.getenv("PGSSLMODE"),
    )


def demonstrate_connection_parameters() -> None:
    print_section("5. PostgreSQL Connection Parameters")

    parameters = get_environment_connection_parameters()

    for key, value in parameters.as_dict().items():
        print(f"{key:<10}: {value}")

    explain(
        """
        A PostgreSQL connection generally needs:

            host
            port
            database
            user
            authentication information

        Typical local development values are:

            host=localhost
            port=5432
            database=postgres
            user=postgres

        These are conventions, not universal requirements.

        localhost means the local machine. It can resolve through the local
        networking stack and may behave differently from a remote hostname.

        127.0.0.1 is the IPv4 loopback address.

        ::1 is the IPv6 loopback address.

        A PostgreSQL connection URI can look conceptually like:

            postgresql://username:password@hostname:5432/database

        Passwords should not be embedded in source code or committed to Git.
        """
    )


# ============================================================================
# 7. SQL COMMAND GENERATION
# ============================================================================

def quote_sql_identifier(identifier: str) -> str:
    """
    Safely quote a PostgreSQL identifier for educational SQL generation.

    PostgreSQL identifiers use double quotes. Embedded double quotes are
    represented by two double quotes.

    This is not a replacement for parameterized SQL libraries. It is provided
    to demonstrate the distinction between identifiers and values.
    """
    if not identifier:
        raise ValueError("Identifier cannot be empty.")

    return '"' + identifier.replace('"', '""') + '"'


def quote_sql_literal(value: str) -> str:
    """
    Quote a string literal for educational purposes.

    Application code should normally use parameterized queries instead of
    manually building SQL values.
    """
    return "'" + value.replace("'", "''") + "'"


def demonstrate_sql_generation() -> None:
    print_section("6. SQL Identifiers Versus SQL Values")

    database_name = "learning_db"
    role_name = "learning_user"
    display_name = "O'Reilly"

    print("Identifier example:")
    print(f"CREATE DATABASE {quote_sql_identifier(database_name)};")

    print()
    print("Role identifier example:")
    print(
        f"CREATE ROLE {quote_sql_identifier(role_name)} "
        "LOGIN;"
    )

    print()
    print("String literal example:")
    print(
        "INSERT INTO people(name) VALUES "
        f"({quote_sql_literal(display_name)});"
    )

    explain(
        """
        SQL identifiers name database objects:

            database names
            table names
            column names
            schema names
            role names

        SQL values are data:

            strings
            numbers
            dates
            timestamps
            booleans
            NULL

        These two categories should not be handled identically.

        Most application values should be sent through parameterized queries.
        Dynamic identifiers require a different technique, such as safe
        identifier quoting provided by a trusted database driver.

        Never solve SQL injection by blindly concatenating untrusted values
        into SQL statements.
        """
    )


# ============================================================================
# 8. IMPORTANT SQL COMMANDS
# ============================================================================

def show_database_creation_commands() -> None:
    print_section("7. Database Creation and Management Commands")

    commands = [
        "CREATE DATABASE learning_db;",
        "CREATE DATABASE learning_db OWNER learning_user;",
        "DROP DATABASE learning_db;",
        "ALTER DATABASE learning_db RENAME TO learning_db_v2;",
        "ALTER DATABASE learning_db OWNER TO learning_user;",
    ]

    for command in commands:
        print(command)

    print_subsection("Command-line equivalents")

    cli_commands = [
        "createdb learning_db",
        "createdb --owner=learning_user learning_db",
        "dropdb learning_db",
    ]

    for command in cli_commands:
        print(command)

    explain(
        """
        CREATE DATABASE is SQL executed by a PostgreSQL client.

        createdb is a command-line utility that ultimately requests the server
        to create a database.

        DROP DATABASE is destructive. A database cannot normally be dropped
        while active sessions are connected to it. Modern PostgreSQL versions
        provide options for terminating conflicting connections in supported
        circumstances, but terminating sessions should be deliberate.

        Database creation also depends on privileges. A normal application
        role should not automatically receive broad cluster-level privileges.
        """
    )


# ============================================================================
# 9. ROLE AND USER CONCEPTS
# ============================================================================

def show_role_concepts() -> None:
    print_section("8. Roles, Users, and Privileges")

    commands = [
        "CREATE ROLE analyst LOGIN PASSWORD 'use-a-secret-manager';",
        "CREATE ROLE reporting_group NOLOGIN;",
        "GRANT reporting_group TO analyst;",
        "GRANT CONNECT ON DATABASE learning_db TO analyst;",
        "ALTER ROLE analyst SET search_path TO app, public;",
        "DROP ROLE analyst;",
    ]

    for command in commands:
        print(command)

    explain(
        """
        PostgreSQL uses the term ROLE as the fundamental security identity.

        A role can have LOGIN:
            The role can authenticate as a connection identity.

        A role can have NOLOGIN:
            The role is commonly used as a group or privilege container.

        A role can have SUPERUSER:
            The role has extremely broad privileges. This should be restricted.

        A role can inherit privileges from roles granted to it.

        A strong production pattern is:

            human/admin roles
                    |
                    v
              group roles
                    |
                    v
            object privileges

        Applications should normally use dedicated least-privilege roles
        instead of the initial PostgreSQL superuser.
        """
    )


# ============================================================================
# 10. SCHEMAS
# ============================================================================

def show_schema_concepts() -> None:
    print_section("9. Schemas and search_path")

    schema_commands = [
        "CREATE SCHEMA app;",
        "CREATE TABLE app.customers (id bigint PRIMARY KEY, name text);",
        "SET search_path TO app, public;",
        "SHOW search_path;",
        "SELECT * FROM app.customers;",
    ]

    for command in schema_commands:
        print(command)

    explain(
        """
        A schema is a namespace inside a database.

        For example:

            app.customers
            reporting.monthly_sales
            audit.events

        Schemas are useful for separating application objects, reporting
        objects, administrative objects, or different logical areas.

        search_path controls which schemas PostgreSQL searches when an
        unqualified object name is used.

        This means:

            SELECT * FROM customers;

        may resolve differently depending on search_path.

        Explicit schema qualification such as:

            SELECT * FROM app.customers;

        makes object resolution clearer and can reduce ambiguity.
        """
    )


# ============================================================================
# 11. PSQL COMMANDS
# ============================================================================

def show_psql_meta_commands() -> None:
    print_section("10. psql Interactive Command-Line Usage")

    commands = [
        "\\l",
        "\\list",
        "\\c learning_db",
        "\\connect learning_db",
        "\\conninfo",
        "\\du",
        "\\dn",
        "\\dt",
        "\\dt app.*",
        "\\d app.customers",
        "\\d+ app.customers",
        "\\df",
        "\\dv",
        "\\dx",
        "\\q",
        "\\?",
        "\\h SELECT",
        "\\timing",
        "\\x",
        "\\i setup.sql",
        "\\o output.txt",
    ]

    for command in commands:
        print(command)

    explain(
        """
        psql has two broad categories of input:

        SQL:
            SELECT version();

        psql meta-commands:
            \\conninfo

        Meta-commands begin with a backslash and are interpreted by psql,
        not by PostgreSQL's SQL parser.

        Useful beginner commands:

            \\l
                List databases.

            \\c database_name
                Connect to another database.

            \\conninfo
                Show the current connection.

            \\du
                List roles.

            \\dn
                List schemas.

            \\dt
                List tables.

            \\d table_name
                Describe a relation.

            \\q
                Exit psql.

        The distinction between SQL and psql commands is fundamental.
        """
    )


# ============================================================================
# 12. PSQL CONNECTION EXAMPLES
# ============================================================================

def show_psql_connection_examples() -> None:
    print_section("11. Connecting with psql")

    examples = [
        "psql",
        "psql -h localhost -p 5432 -U postgres -d postgres",
        "psql --host=localhost --port=5432 --username=postgres --dbname=postgres",
        "psql postgresql://postgres@localhost:5432/postgres",
    ]

    for command in examples:
        print(command)

    explain(
        """
        psql with no explicit parameters uses environment variables and client
        defaults where available.

        Explicit parameters make the connection target obvious:

            -h    host
            -p    port
            -U    user
            -d    database

        A URI can represent the same information.

        A password prompt is preferable to putting a password directly on the
        command line because command-line arguments can sometimes be visible
        through process inspection or shell history.

        For unattended environments, PostgreSQL supports password files such
        as .pgpass on Unix-like systems and the corresponding password-file
        convention on Windows. File permissions must be handled carefully.
        """
    )


# ============================================================================
# 13. CONNECTION STRING PARSING
# ============================================================================

def demonstrate_connection_uri_structure() -> None:
    print_section("12. PostgreSQL Connection URI Structure")

    uri = "postgresql://app_user:REDACTED@localhost:5432/learning_db"

    print("Example URI:")
    print(uri)

    print()
    print("Conceptual components:")
    print("scheme      = postgresql")
    print("user        = app_user")
    print("password    = REDACTED")
    print("host        = localhost")
    print("port        = 5432")
    print("database    = learning_db")

    explain(
        """
        A PostgreSQL URI commonly follows:

            postgresql://user:password@host:port/database

        Additional connection parameters may be encoded in a query component.

        Special characters in usernames, passwords, or other URI components may
        need percent encoding.

        A common operational mistake is copying a URI containing a password
        into:

            source code
            Git history
            shell history
            CI logs
            screenshots
            issue trackers
            configuration files

        Treat connection strings containing credentials as secrets.
        """
    )


# ============================================================================
# 14. ENVIRONMENT VARIABLES
# ============================================================================

def show_postgresql_environment_variables() -> None:
    print_section("13. PostgreSQL Environment Variables")

    variables = {
        "PGHOST": "Default server host",
        "PGPORT": "Default server port",
        "PGDATABASE": "Default database",
        "PGUSER": "Default role/user",
        "PGPASSWORD": "Password for client authentication",
        "PGSSLMODE": "SSL connection mode",
        "PGSERVICE": "Named service from a service configuration",
        "PGOPTIONS": "Client-supplied server startup options",
    }

    for name, purpose in variables.items():
        value = os.getenv(name)

        if name in {"PGPASSWORD"} and value:
            displayed_value = "[SET BUT HIDDEN]"
        else:
            displayed_value = value if value is not None else "[NOT SET]"

        print(f"{name:<14} {purpose:<45} {displayed_value}")

    explain(
        """
        Environment variables are useful for local development and deployment.

        They separate configuration from application code.

        A common mistake is assuming environment variables are automatically
        secure. They are not a universal secret-management solution.

        Secrets can be exposed through:

            process inspection
            debugging output
            shell history
            CI logs
            crash reports
            accidental printing

        Dedicated secret-management systems are usually preferable for
        production credentials.
        """
    )


# ============================================================================
# 15. PASSWORD FILE
# ============================================================================

def postgres_password_file_locations() -> list[Path]:
    """
    Return likely password-file locations without creating or modifying them.
    """
    home = Path.home()

    if platform.system() == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            return [Path(appdata) / "postgresql" / "pgpass.conf"]
        return [home / "AppData" / "Roaming" / "postgresql" / "pgpass.conf"]

    return [home / ".pgpass"]


def show_password_file_information() -> None:
    print_section("14. PostgreSQL Password File")

    locations = postgres_password_file_locations()

    for location in locations:
        print(f"Possible password file: {location}")
        print(f"Exists: {location.exists()}")

    print()
    print("Conceptual format:")
    print("hostname:port:database:username:password")

    explain(
        """
        The PostgreSQL client supports a password file so interactive commands
        do not repeatedly require password entry.

        Unix-like systems traditionally use:

            ~/.pgpass

        Windows commonly uses:

            %APPDATA%\\postgresql\\pgpass.conf

        The exact behavior depends on the client and operating system.

        Password files must be protected. On Unix-like systems, PostgreSQL
        clients expect restrictive permissions because exposing the file can
        expose database credentials.

        Do not print the contents of a password file in logs.
        """
    )


# ============================================================================
# 16. SERVICE MANAGEMENT
# ============================================================================

def show_service_management_examples() -> None:
    print_section("15. Starting and Stopping PostgreSQL")

    explain(
        """
        PostgreSQL runs as a system service or managed process.

        Linux systems using systemd commonly use commands conceptually such as:

            systemctl status postgresql
            systemctl start postgresql
            systemctl stop postgresql
            systemctl restart postgresql

        Exact service names can differ by distribution and installation.

        Windows commonly manages PostgreSQL through Windows Services or the
        installer-provided service configuration.

        macOS installations through package managers may use commands specific
        to that package manager.

        Never assume that a command copied from one operating system applies
        unchanged to another.
        """
    )

    commands = {
        "Linux/systemd status": "systemctl status postgresql",
        "Linux/systemd start": "sudo systemctl start postgresql",
        "Linux/systemd stop": "sudo systemctl stop postgresql",
        "Linux/systemd restart": "sudo systemctl restart postgresql",
        "Docker alternative": "docker ps",
    }

    for description, command in commands.items():
        print(f"{description:<25} -> {command}")


# ============================================================================
# 17. CONFIGURATION FILES
# ============================================================================

def show_configuration_concepts() -> None:
    print_section("16. PostgreSQL Configuration")

    explain(
        """
        PostgreSQL commonly uses several important configuration files.

        postgresql.conf:
            Main server configuration.

        pg_hba.conf:
            Host-based authentication rules.

        pg_ident.conf:
            Optional operating-system-to-database identity mapping.

        The exact file locations depend on how PostgreSQL was installed.

        Useful SQL commands can reveal active configuration paths:

            SHOW config_file;
            SHOW hba_file;
            SHOW data_directory;

        PostgreSQL can also report configuration settings through:

            SHOW listen_addresses;
            SHOW port;
            SHOW max_connections;

        Configuration changes may require a reload or restart depending on the
        parameter. A reload is less disruptive than a full restart when the
        parameter supports reload semantics.
        """
    )

    configuration_queries = [
        "SHOW config_file;",
        "SHOW hba_file;",
        "SHOW data_directory;",
        "SHOW listen_addresses;",
        "SHOW port;",
        "SHOW max_connections;",
        "SHOW shared_buffers;",
        "SHOW work_mem;",
        "SHOW timezone;",
        "SHOW search_path;",
    ]

    for query in configuration_queries:
        print(query)


# ============================================================================
# 18. LISTENING ADDRESSES
# ============================================================================

def show_listen_address_security() -> None:
    print_section("17. listen_addresses and Network Exposure")

    explain(
        """
        PostgreSQL does not need to listen on every network interface for a
        typical local development installation.

        A local-only setup may use:

            listen_addresses = 'localhost'

        A server intended to accept remote clients may listen on additional
        interfaces, depending on architecture.

        Setting:

            listen_addresses = '*'

        can expose PostgreSQL on all available network interfaces. This is not
        automatically unsafe, but it increases the attack surface and must be
        paired with restrictive network controls and pg_hba.conf rules.

        Network exposure should be intentional.

        A secure architecture normally combines:

            firewall rules
            private networking
            restrictive listen_addresses
            restrictive pg_hba.conf
            strong authentication
            TLS where appropriate
            least-privilege roles
        """
    )


# ============================================================================
# 19. PG_HBA.CONF
# ============================================================================

def show_pg_hba_concepts() -> None:
    print_section("18. pg_hba.conf Authentication")

    example_lines = [
        "local   all   postgres                         peer",
        "local   all   all                              scram-sha-256",
        "host    all   all   127.0.0.1/32               scram-sha-256",
        "host    all   all   ::1/128                    scram-sha-256",
        "hostssl all   app_user  10.0.0.0/24            scram-sha-256",
    ]

    print("Illustrative rules:")
    for line in example_lines:
        print(line)

    explain(
        """
        pg_hba.conf controls how clients are authenticated.

        A rule contains concepts such as:

            connection type
            database
            role
            client address
            authentication method

        Common connection types include:

            local
                Unix-domain socket connections.

            host
                TCP/IP connections.

            hostssl
                TCP/IP connections using SSL.

        Common authentication methods include:

            peer
                Uses the operating-system identity for local authentication.

            scram-sha-256
                Password authentication using SCRAM.

            trust
                Allows access without password verification and should be used
                only with a deliberate security model.

        Rule order matters. PostgreSQL uses the first matching rule.

        A configuration can therefore contain a correct rule that is never
        reached because an earlier rule matches first.
        """
    )


# ============================================================================
# 20. PG_HBA DEBUGGING
# ============================================================================

def explain_authentication_failure_layers() -> None:
    print_section("19. Understanding Authentication Failures")

    cases = [
        (
            "connection refused",
            "Server may be stopped, host/port may be wrong, or a firewall may block access.",
        ),
        (
            "no pg_hba.conf entry",
            "The server received the connection but no authentication rule matched.",
        ),
        (
            "password authentication failed",
            "The role exists but authentication credentials or authentication configuration failed.",
        ),
        (
            "role does not exist",
            "The requested PostgreSQL role is absent from the cluster.",
        ),
        (
            "database does not exist",
            "The requested database is absent or the connection target is incorrect.",
        ),
        (
            "permission denied",
            "Authentication succeeded but authorization for the requested object failed.",
        ),
    ]

    for error, meaning in cases:
        print(f"{error:<32} -> {meaning}")


# ============================================================================
# 21. PGADMIN
# ============================================================================

def show_pgadmin_concepts() -> None:
    print_section("20. pgAdmin")

    explain(
        """
        pgAdmin is a graphical administration and development interface for
        PostgreSQL.

        A common workflow is:

            1. Install PostgreSQL.
            2. Open pgAdmin.
            3. Register a server connection.
            4. Provide a connection name.
            5. Provide host.
            6. Provide port.
            7. Provide maintenance database.
            8. Provide username.
            9. Enter authentication credentials.
            10. Save the connection.
            11. Expand Databases.
            12. Select a database.
            13. Use Query Tool for SQL.

        Typical local settings are:

            Host:
                localhost

            Port:
                5432

            Maintenance database:
                postgres

            Username:
                postgres

        These values depend on the installation.

        pgAdmin and psql are clients. Neither one is the PostgreSQL database
        server itself.
        """
    )

    print_subsection("pgAdmin conceptual object tree")

    tree = [
        "Servers",
        "  PostgreSQL Server",
        "    Databases",
        "      postgres",
        "      learning_db",
        "        Schemas",
        "          public",
        "          app",
        "            Tables",
        "            Views",
        "            Functions",
        "            Sequences",
        "    Login/Group Roles",
    ]

    for line in tree:
        print(line)


# ============================================================================
# 22. PSQL VERSUS PGADMIN
# ============================================================================

def compare_psql_and_pgadmin() -> None:
    print_section("21. psql Versus pgAdmin")

    rows = [
        ("Interface", "Terminal", "Graphical/web interface"),
        ("Automation", "Excellent", "Possible, but less natural"),
        ("SQL learning", "Excellent", "Excellent"),
        ("Administration", "Excellent", "Excellent"),
        ("Remote usage", "Very efficient", "Convenient"),
        ("Scripting", "Excellent", "Limited compared with shell/psql"),
        ("Visual exploration", "Limited", "Strong"),
        ("Resource usage", "Low", "Higher"),
    ]

    print(f"{'Category':<20} {'psql':<25} {'pgAdmin':<25}")
    print("-" * 72)

    for category, psql_value, pgadmin_value in rows:
        print(f"{category:<20} {psql_value:<25} {pgadmin_value:<25}")

    explain(
        """
        psql is particularly strong for:

            repeatable scripts
            SSH sessions
            CI/CD
            automation
            lightweight administration
            precise command-line workflows

        pgAdmin is particularly strong for:

            visual browsing
            graphical administration
            object exploration
            query development
            users who prefer a GUI

        They are complementary rather than mutually exclusive.
        """
    )


# ============================================================================
# 23. VERSION DETECTION
# ============================================================================

def get_psql_version() -> Optional[str]:
    """Return psql version text if the command is available."""
    command = find_command("psql")

    if not command.available:
        return None

    result = run_command([command.path, "--version"])

    if result.succeeded:
        return result.stdout.strip()

    return None


def get_pg_config_version() -> Optional[str]:
    """Return pg_config version text if available."""
    command = find_command("pg_config")

    if not command.available:
        return None

    result = run_command([command.path, "--version"])

    if result.succeeded:
        return result.stdout.strip()

    return None


def demonstrate_version_detection() -> None:
    print_section("22. PostgreSQL Client Version Detection")

    psql_version = get_psql_version()
    pg_config_version = get_pg_config_version()

    print(f"psql version: {psql_version or 'Not available'}")
    print(f"pg_config version: {pg_config_version or 'Not available'}")

    explain(
        """
        PostgreSQL has client and server versions.

        Running:

            psql --version

        reports the installed psql client version.

        It does not necessarily prove that the PostgreSQL server has exactly
        the same version.

        Once connected to a server, SQL such as:

            SELECT version();

        reports server version information.

        Keeping client and server compatibility in mind is important, especially
        when multiple PostgreSQL installations exist on one workstation.
        """
    )


# ============================================================================
# 24. PYTHON DRIVER CONCEPTS
# ============================================================================

def explain_python_postgresql_drivers() -> None:
    print_section("23. Connecting to PostgreSQL from Python")

    explain(
        """
        Python applications need a PostgreSQL driver.

        Common choices include modern PostgreSQL drivers such as psycopg.

        A typical application workflow is:

            Python application
                    |
                    v
            PostgreSQL driver
                    |
                    v
              network/socket
                    |
                    v
            PostgreSQL server

        The driver handles:

            connection establishment
            protocol communication
            parameter binding
            result retrieval
            transaction interaction
            type adaptation

        A driver is different from PostgreSQL itself.

        The following optional demonstration attempts to import psycopg if it
        is installed. The script does not require it for its other educational
        sections.
        """
    )


def try_import_psycopg() -> Optional[object]:
    """Attempt to import psycopg without making it a mandatory dependency."""
    try:
        import psycopg  # type: ignore

        return psycopg
    except ImportError:
        return None


def demonstrate_psycopg_import() -> None:
    print_section("24. Optional Python Driver Check")

    psycopg = try_import_psycopg()

    if psycopg is None:
        print("psycopg is not installed.")
        print("The rest of this script does not require psycopg.")
        print("If a Python connection example is needed, install a supported")
        print("psycopg package in the intended virtual environment.")
        return

    print(f"psycopg is installed: {psycopg.__version__}")


# ============================================================================
# 25. PROGRAMMATIC CONNECTION EXAMPLE
# ============================================================================

def demonstrate_programmatic_connection() -> None:
    print_section("25. Optional Live PostgreSQL Connection")

    psycopg = try_import_psycopg()

    if psycopg is None:
        print("Skipped because psycopg is not installed.")
        return

    parameters = get_environment_connection_parameters()

    explain(
        """
        The live connection demonstration uses environment variables rather
        than embedding a password in the source file.

        Set appropriate PGHOST, PGPORT, PGDATABASE, PGUSER, and authentication
        configuration before running this section.

        The connection is attempted with a short timeout and is immediately
        closed after retrieving basic server information.
        """
    )

    connection_kwargs = parameters.as_dict()

    try:
        with psycopg.connect(
            **connection_kwargs,
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version(), current_database(), current_user;")
                row = cursor.fetchone()

            print("Connection succeeded.")
            if row:
                print(f"Server version: {row[0]}")
                print(f"Current database: {row[1]}")
                print(f"Current user: {row[2]}")

    except Exception as exc:
        print("Connection attempt failed.")
        print(f"Error type: {type(exc).__name__}")
        print(f"Error: {exc}")

        explain(
            """
            A failed application connection should be diagnosed using the same
            layers used for psql:

                host
                port
                server readiness
                authentication
                role
                database
                authorization
                TLS
                network policy
            """
        )


# ============================================================================
# 26. PARAMETERIZED SQL
# ============================================================================

def demonstrate_parameterized_sql() -> None:
    print_section("26. Parameterized SQL")

    explain(
        """
        Never construct application SQL by concatenating untrusted values.

        Unsafe conceptual pattern:

            query = "SELECT * FROM users WHERE name = '" + user_input + "'"

        A malicious value can alter the meaning of the SQL statement.

        Correct conceptual pattern:

            cursor.execute(
                "SELECT * FROM users WHERE name = %s",
                (user_input,),
            )

        The driver sends the value separately from the SQL structure.

        PostgreSQL drivers use their own parameter style and adaptation rules.
        Follow the driver documentation instead of assuming that every Python
        database library uses identical placeholder syntax.
        """
    )

    safe_example = (
        'cursor.execute("SELECT * FROM users WHERE name = %s", (user_input,))'
    )

    print("Safe conceptual example:")
    print(safe_example)


# ============================================================================
# 27. TRANSACTIONS
# ============================================================================

def show_transaction_concepts() -> None:
    print_section("27. Transactions in PostgreSQL")

    commands = [
        "BEGIN;",
        "INSERT INTO accounts(id, balance) VALUES (1, 1000);",
        "UPDATE accounts SET balance = balance - 100 WHERE id = 1;",
        "COMMIT;",
        "ROLLBACK;",
        "SAVEPOINT before_change;",
        "ROLLBACK TO SAVEPOINT before_change;",
    ]

    for command in commands:
        print(command)

    explain(
        """
        PostgreSQL uses transactions to group operations into an atomic unit.

        COMMIT:
            Make transaction changes durable according to PostgreSQL's
            transactional guarantees.

        ROLLBACK:
            Discard uncommitted changes.

        SAVEPOINT:
            Establish an intermediate point that can be rolled back to without
            necessarily discarding the entire transaction.

        Python database drivers may manage transactions automatically or expose
        explicit transaction contexts.

        Understanding transaction state is important when diagnosing errors.
        A statement failure can leave a transaction in an aborted state until
        rollback, depending on the client and driver behavior.
        """
    )


# ============================================================================
# 28. DATABASE OWNERSHIP
# ============================================================================

def show_database_ownership() -> None:
    print_section("28. Database Ownership and Privileges")

    commands = [
        "CREATE ROLE app_owner LOGIN;",
        "CREATE DATABASE application_db OWNER app_owner;",
        "CREATE ROLE app_runtime LOGIN;",
        "GRANT CONNECT ON DATABASE application_db TO app_runtime;",
        "GRANT USAGE ON SCHEMA app TO app_runtime;",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO app_runtime;",
    ]

    for command in commands:
        print(command)

    explain(
        """
        Ownership and privileges are separate concepts.

        An owner generally has broad control over an object.

        A role can also receive specific privileges without becoming owner.

        Common object privileges include:

            SELECT
            INSERT
            UPDATE
            DELETE
            REFERENCES
            TRIGGER
            EXECUTE
            USAGE
            CREATE
            CONNECT
            TEMPORARY

        The correct privilege depends on the object type.

        An application role that only needs to read data should not automatically
        receive INSERT, UPDATE, DELETE, CREATE, or administrative privileges.
        """
    )


# ============================================================================
# 29. DEFAULT PRIVILEGES
# ============================================================================

def show_default_privileges() -> None:
    print_section("29. Default Privileges")

    commands = [
        (
            "ALTER DEFAULT PRIVILEGES IN SCHEMA app "
            "GRANT SELECT ON TABLES TO reporting_role;"
        ),
        (
            "ALTER DEFAULT PRIVILEGES IN SCHEMA app "
            "GRANT USAGE, SELECT ON SEQUENCES TO reporting_role;"
        ),
    ]

    for command in commands:
        print(command)

    explain(
        """
        GRANT on existing objects does not automatically grant the same
        privilege to future objects.

        ALTER DEFAULT PRIVILEGES can establish privileges for objects created
        in the future by a particular role.

        A subtle point is that default privileges are associated with the role
        that creates the objects. Changing default privileges for one creator
        does not automatically alter defaults for every other role.
        """
    )


# ============================================================================
# 30. CONNECTION DATABASE VERSUS TARGET DATABASE
# ============================================================================

def explain_database_connection_model() -> None:
    print_section("30. PostgreSQL Database Connection Model")

    explain(
        """
        A PostgreSQL connection is associated with one database.

        For example:

            psql -d learning_db

        connects the session to learning_db.

        PostgreSQL does not provide a general SQL command equivalent to
        switching arbitrary databases inside an existing connection in the
        same way some other database systems do.

        To work with another database, the client normally establishes another
        connection.

        In psql:

            \\c another_database

        closes the current connection context and establishes the new target
        connection.
        """
    )


# ============================================================================
# 31. DATABASE LISTING QUERY
# ============================================================================

def show_database_information_queries() -> None:
    print_section("31. Useful SQL Diagnostic Queries")

    queries = [
        "SELECT version();",
        "SELECT current_database();",
        "SELECT current_user;",
        "SELECT current_schema();",
        "SELECT current_setting('server_version');",
        "SHOW port;",
        "SHOW listen_addresses;",
        "SHOW search_path;",
        "SELECT inet_server_addr();",
        "SELECT inet_server_port();",
        "SELECT pg_backend_pid();",
        "SELECT now();",
    ]

    for query in queries:
        print(query)

    explain(
        """
        These queries help establish exactly where a session is connected.

        This is valuable when several PostgreSQL installations, containers,
        virtual machines, ports, or databases exist on one computer.

        A frequent debugging mistake is changing configuration on one
        PostgreSQL installation while the application is connected to another.
        """
    )


# ============================================================================
# 32. LOCALHOST AND IPV4/IPV6
# ============================================================================

def demonstrate_localhost_resolution() -> None:
    print_section("32. localhost, IPv4, and IPv6")

    try:
        addresses = socket.getaddrinfo(
            "localhost",
            5432,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        print(f"Could not resolve localhost: {exc}")
        return

    unique_addresses: list[str] = []

    for entry in addresses:
        address = entry[4][0]
        if address not in unique_addresses:
            unique_addresses.append(address)

    for address in unique_addresses:
        print(address)

    explain(
        """
        localhost can resolve to more than one address family.

        Common possibilities include:

            127.0.0.1
            ::1

        This matters because PostgreSQL authentication rules may distinguish
        IPv4 and IPv6 address ranges.

        For example:

            127.0.0.1/32

        does not match:

            ::1/128

        If psql behaves differently when connecting to localhost versus
        127.0.0.1, inspect both server listening configuration and pg_hba.conf.
        """
    )


# ============================================================================
# 33. PORT CHECKING
# ============================================================================

def demonstrate_port_checking() -> None:
    print_section("33. Checking Whether Port 5432 Is Reachable")

    host = os.getenv("PGHOST", "localhost")

    try:
        port = int(os.getenv("PGPORT", "5432"))
    except ValueError:
        port = 5432

    reachable = check_tcp_port(host, port)

    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"TCP reachable: {reachable}")

    if not reachable:
        explain(
            """
            TCP failure does not necessarily mean PostgreSQL is uninstalled.

            Possible explanations include:

                server is stopped
                wrong port
                wrong host
                PostgreSQL listens only on another interface
                firewall rule
                container port not published
                network namespace isolation
                remote server unavailable
            """
        )


# ============================================================================
# 34. DOCKER CONCEPTS
# ============================================================================

def show_docker_postgresql_concept() -> None:
    print_section("34. PostgreSQL with Docker")

    commands = [
        "docker pull postgres",
        (
            "docker run --name postgres-learning "
            "-e POSTGRES_PASSWORD=<secret> "
            "-p 5432:5432 "
            "-d postgres"
        ),
        "docker ps",
        "docker logs postgres-learning",
        "docker stop postgres-learning",
        "docker start postgres-learning",
        "docker rm postgres-learning",
    ]

    for command in commands:
        print(command)

    explain(
        """
        Containers provide an alternative way to run PostgreSQL locally.

        The database server runs inside the container.

        Port mapping:

            host_port:container_port

        means that a host connection such as:

            localhost:5432

        can be forwarded to the PostgreSQL process listening inside the
        container.

        Containerized PostgreSQL introduces additional concepts:

            container lifecycle
            volumes
            port publishing
            environment variables
            networking
            persistent storage

        A container without persistent storage can lose database state when
        removed. Development and production persistence must therefore be
        designed explicitly.
        """
    )


# ============================================================================
# 35. PERSISTENCE
# ============================================================================

def show_postgresql_storage_concepts() -> None:
    print_section("35. PostgreSQL Data Persistence")

    explain(
        """
        PostgreSQL stores data on disk.

        The PostgreSQL data directory contains the cluster's persistent state,
        including database files and configuration-related information.

        PostgreSQL should not be treated like a stateless application process.

        In container environments, persistent volumes are important because:

            container filesystem lifetime
                is not necessarily
            database data lifetime

        Backups are still required even when persistent volumes are used.

        A volume protects against some container lifecycle events. It does not
        replace:

            logical backups
            physical backups
            replication
            disaster recovery
            restore testing
        """
    )


# ============================================================================
# 36. INSTALLATION VALIDATION
# ============================================================================

@dataclass
class EnvironmentCheck:
    """A single environment validation result."""

    name: str
    passed: bool
    details: str


def validate_local_environment() -> list[EnvironmentCheck]:
    """Perform non-destructive checks of the local PostgreSQL environment."""
    checks: list[EnvironmentCheck] = []

    psql = find_command("psql")
    checks.append(
        EnvironmentCheck(
            name="psql available",
            passed=psql.available,
            details=psql.path or "psql not found on PATH",
        )
    )

    pg_isready = find_command("pg_isready")
    checks.append(
        EnvironmentCheck(
            name="pg_isready available",
            passed=pg_isready.available,
            details=pg_isready.path or "pg_isready not found on PATH",
        )
    )

    pg_config = find_command("pg_config")
    checks.append(
        EnvironmentCheck(
            name="pg_config available",
            passed=pg_config.available,
            details=pg_config.path or "pg_config not found on PATH",
        )
    )

    host = os.getenv("PGHOST", "localhost")

    try:
        port = int(os.getenv("PGPORT", "5432"))
    except ValueError:
        port = 5432

    tcp_reachable = check_tcp_port(host, port)

    checks.append(
        EnvironmentCheck(
            name="PostgreSQL TCP endpoint",
            passed=tcp_reachable,
            details=f"{host}:{port}",
        )
    )

    return checks


def print_environment_validation() -> None:
    print_section("36. Local Environment Validation")

    checks = validate_local_environment()

    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"[{status}] {check.name:<30} {check.details}")

    passed_count = sum(check.passed for check in checks)
    print()
    print(f"Checks passed: {passed_count}/{len(checks)}")

    explain(
        """
        Environment validation should be layered.

        A useful sequence is:

            1. Is the client executable installed?
            2. Is the server process running?
            3. Is the network endpoint reachable?
            4. Does pg_isready report readiness?
            5. Can authentication succeed?
            6. Does the target database exist?
            7. Does the role have required privileges?
            8. Can the application execute its intended queries?

        Passing an earlier check does not guarantee later checks will pass.
        """
    )


# ============================================================================
# 37. REPRODUCIBLE DEVELOPMENT SETUP
# ============================================================================

def show_reproducible_setup() -> None:
    print_section("37. Reproducible PostgreSQL Development Setup")

    files = {
        ".env": "Local environment configuration; keep secrets out of Git.",
        ".gitignore": "Prevents secrets and local artifacts from being committed.",
        "schema.sql": "Database schema initialization SQL.",
        "seed.sql": "Development-only seed data.",
        "README.md": "Documents setup and operational assumptions.",
        "requirements.txt": "Python dependencies when the application uses Python.",
    }

    for filename, purpose in files.items():
        print(f"{filename:<20} -> {purpose}")

    explain(
        """
        A reproducible development environment should specify:

            PostgreSQL version
            expected port
            database name
            role names
            schema initialization
            seed data strategy
            migration strategy
            required extensions
            application connection configuration

        Avoid documenting only "install PostgreSQL".

        A new developer should be able to understand exactly which server,
        database, role, schema, and configuration the application expects.
        """
    )


# ============================================================================
# 38. MIGRATIONS
# ============================================================================

def show_migration_concepts() -> None:
    print_section("38. Schema Migrations")

    example_migrations = [
        "001_create_customers.sql",
        "002_create_orders.sql",
        "003_add_customer_email.sql",
        "004_create_indexes.sql",
    ]

    for migration in example_migrations:
        print(migration)

    explain(
        """
        A migration records a controlled schema change.

        Instead of manually creating tables on every machine, a team can keep
        database structure in version-controlled migration files.

        Migration systems commonly track:

            migration identifier
            applied timestamp
            checksum or content identity
            execution state

        A development database may be recreated from migrations.

        Production databases generally require careful forward-only change
        planning, backups, compatibility considerations, and rollback strategy.

        Migrations should not be confused with data backups.
        """
    )


# ============================================================================
# 39. EXTENSIONS
# ============================================================================

def show_extensions() -> None:
    print_section("39. PostgreSQL Extensions")

    commands = [
        "SELECT * FROM pg_available_extensions;",
        "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;",
        "CREATE EXTENSION IF NOT EXISTS citext;",
    ]

    for command in commands:
        print(command)

    explain(
        """
        PostgreSQL extensions add functionality to the database.

        Examples include extensions for:

            statistics
            specialized data types
            geographic data
            cryptographic functions
            text/search functionality

        Extensions can have:

            PostgreSQL version compatibility requirements
            operating-system packaging requirements
            privilege requirements
            operational implications

        Do not install extensions merely because they are available. Every
        extension should have a justified purpose in the environment.
        """
    )


# ============================================================================
# 40. TIMEZONE
# ============================================================================

def show_timezone_concepts() -> None:
    print_section("40. Time Zone Configuration")

    queries = [
        "SHOW timezone;",
        "SELECT now();",
        "SELECT current_timestamp;",
        "SELECT current_setting('TimeZone');",
    ]

    for query in queries:
        print(query)

    explain(
        """
        Time zone configuration affects timestamp interpretation and display.

        A production system should establish a clear policy for:

            database timezone
            application timezone
            user-facing timezone
            timestamp data types

        Many systems standardize stored event timestamps around UTC and convert
        them to user-local time at presentation boundaries.

        Environment setup should include time-zone expectations because
        inconsistent assumptions can create difficult-to-diagnose reporting
        problems.
        """
    )


# ============================================================================
# 41. LOCALE AND ENCODING
# ============================================================================

def show_encoding_locale_concepts() -> None:
    print_section("41. Encoding, Locale, and Database Initialization")

    queries = [
        "SHOW server_encoding;",
        "SHOW lc_collate;",
        "SHOW lc_ctype;",
    ]

    for query in queries:
        print(query)

    explain(
        """
        PostgreSQL databases have encoding and locale-related properties.

        UTF-8 is commonly used for modern applications because it supports a
        wide range of characters.

        Locale and collation influence operations such as sorting and
        comparison. These properties can be especially important for
        multilingual applications.

        Database initialization choices can affect what locale behavior is
        available. Changing these properties later may be more complicated
        than changing a normal runtime parameter.
        """
    )


# ============================================================================
# 42. DATABASE TEMPLATES
# ============================================================================

def show_database_templates() -> None:
    print_section("42. PostgreSQL Database Templates")

    explain(
        """
        PostgreSQL uses template databases when creating new databases.

        Common system databases include:

            postgres
            template0
            template1

        template1 is commonly used as the starting point for new databases.

        template0 is a clean template that is useful in special initialization
        scenarios.

        System databases should not be casually modified.

        The important environment-setup lesson is that CREATE DATABASE is not
        simply creating an empty directory. PostgreSQL initializes a database
        using its database-cluster mechanisms and templates.
        """
    )


# ============================================================================
# 43. DATABASE SIZE AND SERVER INFORMATION
# ============================================================================

def show_diagnostic_queries() -> None:
    print_section("43. Useful Diagnostic SQL")

    queries = [
        "SELECT current_database();",
        "SELECT current_user;",
        "SELECT pg_size_pretty(pg_database_size(current_database()));",
        "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database;",
        "SELECT pid, usename, datname, client_addr, state FROM pg_stat_activity;",
        "SELECT * FROM pg_settings WHERE name = 'port';",
    ]

    for query in queries:
        print(query)

    explain(
        """
        pg_database contains information about databases in the cluster.

        pg_stat_activity exposes information about server sessions, subject to
        permissions and version-specific behavior.

        pg_settings exposes PostgreSQL configuration settings.

        Diagnostic SQL is useful because it lets an administrator inspect the
        actual server rather than relying on assumptions about configuration
        files or installation paths.
        """
    )


# ============================================================================
# 44. ACTIVE CONNECTIONS
# ============================================================================

def explain_active_connections() -> None:
    print_section("44. Active Sessions and Database Drops")

    explain(
        """
        PostgreSQL maintains client sessions.

        A database cannot normally be dropped while sessions are connected to
        it because active sessions depend on the database.

        To diagnose this situation, administrators can inspect:

            pg_stat_activity

        An administrator may need to terminate sessions deliberately before
        destructive maintenance.

        Session termination should never be treated as a harmless shortcut.
        It can interrupt transactions, application requests, background jobs,
        or administrative operations.
        """
    )

    print(
        "Diagnostic query:"
        "\nSELECT pid, usename, datname, state, query "
        "\nFROM pg_stat_activity;"
    )


# ============================================================================
# 45. CONNECTION POOLING
# ============================================================================

def show_connection_pooling() -> None:
    print_section("45. Connection Pooling")

    explain(
        """
        Opening a new database connection for every request can be expensive.

        A connection pool maintains a controlled set of reusable connections.

        Conceptually:

            application requests
                 |   |   |   |
                 v   v   v   v
              connection pool
                 |   |   |
                 v   v   v
            PostgreSQL server

        Benefits:

            reduced connection setup overhead
            controlled concurrency
            predictable resource usage

        Risks of poor configuration:

            too many connections
            exhausted server resources
            long-lived idle sessions
            transaction leaks
            pool starvation

        PostgreSQL's max_connections limits server-side connection capacity.
        Increasing it without considering memory and workload can make a system
        less stable rather than more stable.

        Pool sizing should account for application concurrency and database
        workload.
        """
    )


# ============================================================================
# 46. MAX_CONNECTIONS
# ============================================================================

def show_connection_limits() -> None:
    print_section("46. max_connections")

    print("SHOW max_connections;")
    print("SELECT count(*) FROM pg_stat_activity;")

    explain(
        """
        max_connections controls the number of server connections PostgreSQL
        permits.

        A high number is not automatically better.

        Each connection consumes server resources.

        Applications that create large numbers of independent connections can
        overwhelm PostgreSQL even when CPU and disk are otherwise adequate.

        Connection pooling is frequently preferable to simply raising
        max_connections.
        """
    )


# ============================================================================
# 47. SECURITY BASELINE
# ============================================================================

def show_security_baseline() -> None:
    print_section("47. PostgreSQL Security Baseline")

    checklist = [
        "Do not use the superuser for normal application queries.",
        "Create dedicated roles for applications.",
        "Grant only required privileges.",
        "Use strong authentication.",
        "Prefer SCRAM-based password authentication where appropriate.",
        "Protect password files and environment configuration.",
        "Do not commit credentials to Git.",
        "Restrict network exposure.",
        "Use firewalls and private networking where appropriate.",
        "Use TLS for connections that require transport protection.",
        "Keep PostgreSQL and client components maintained.",
        "Review role memberships regularly.",
        "Audit privileged operations.",
        "Back up important databases.",
        "Test restoration rather than assuming backups work.",
    ]

    for item in checklist:
        print(f"[ ] {item}")

    explain(
        """
        Security is not a single PostgreSQL setting.

        It is the combination of:

            identity
            authentication
            authorization
            network controls
            encryption
            operating-system security
            credential management
            patch management
            monitoring
            backup and recovery

        Local development may use a simpler setup, but production deployments
        should not inherit development shortcuts without deliberate review.
        """
    )


# ============================================================================
# 48. TLS / SSL
# ============================================================================

def show_ssl_concepts() -> None:
    print_section("48. SSL/TLS Connection Security")

    modes = [
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
    ]

    for mode in modes:
        print(mode)

    explain(
        """
        PostgreSQL clients can negotiate encrypted connections.

        The precise security behavior depends on the sslmode and certificate
        configuration.

        Important distinction:

            encryption
                Protects communication from being read in transit.

            server identity verification
                Helps ensure the client is communicating with the intended
                server.

        A mode that encrypts traffic does not automatically provide the same
        identity-verification guarantees as strict certificate verification.

        For sensitive remote connections, certificate validation and hostname
        verification should be considered carefully.
        """
    )


# ============================================================================
# 49. BACKUP AND RESTORE
# ============================================================================

def show_backup_tools() -> None:
    print_section("49. PostgreSQL Backup Tools")

    commands = [
        "pg_dump learning_db > learning_db.sql",
        "pg_dump -Fc learning_db -f learning_db.dump",
        "pg_restore -d learning_db learning_db.dump",
        "pg_dumpall > cluster.sql",
    ]

    for command in commands:
        print(command)

    explain(
        """
        pg_dump creates a logical backup of a database.

        pg_restore is used with appropriate archive formats such as custom or
        directory formats.

        pg_dumpall can represent cluster-level objects and multiple databases
        in a SQL-oriented output, depending on usage.

        Backups should be treated as operational assets.

        A backup strategy should define:

            what is backed up
            how often
            where it is stored
            encryption
            retention
            access control
            restoration procedure
            recovery objectives

        A backup that has never been restored in testing is not equivalent to a
        proven recovery process.
        """
    )


# ============================================================================
# 50. COMMON INSTALLATION FAILURES
# ============================================================================

def show_common_installation_failures() -> None:
    print_section("50. Common PostgreSQL Setup Problems")

    problems = {
        "psql command not found": (
            "PostgreSQL client tools may not be installed or their directory "
            "may not be included in PATH."
        ),
        "connection refused": (
            "The server may be stopped, the port may be wrong, or the listener "
            "may not be reachable."
        ),
        "password authentication failed": (
            "Check username, authentication method, password, and pg_hba.conf."
        ),
        "database does not exist": (
            "Verify the target database name with \\l or pg_database."
        ),
        "role does not exist": (
            "Verify the role with \\du or pg_roles."
        ),
        "no pg_hba.conf entry": (
            "The server received the request but no authentication rule matched."
        ),
        "permission denied": (
            "Authentication succeeded but the role lacks required privileges."
        ),
        "port already in use": (
            "Another service may already be using the configured TCP port."
        ),
        "wrong PostgreSQL instance": (
            "Multiple installations or containers may be running simultaneously."
        ),
        "pgAdmin cannot connect": (
            "Validate the same host, port, role, database, and authentication "
            "settings with psql."
        ),
    }

    for problem, explanation_text in problems.items():
        print(f"{problem:<32} -> {explanation_text}")


# ============================================================================
# 51. DEBUGGING WORKFLOW
# ============================================================================

def show_debugging_workflow() -> None:
    print_section("51. Systematic PostgreSQL Connection Debugging")

    steps = [
        "1. Confirm which host and port the client is using.",
        "2. Check whether PostgreSQL is running.",
        "3. Check the TCP endpoint.",
        "4. Run pg_isready.",
        "5. Try psql with explicit host, port, user, and database.",
        "6. Inspect the exact PostgreSQL error message.",
        "7. Verify the role exists.",
        "8. Verify the database exists.",
        "9. Inspect pg_hba.conf matching rules.",
        "10. Verify password/authentication configuration.",
        "11. Check database CONNECT privileges.",
        "12. Check object-level privileges if connection succeeds but SQL fails.",
        "13. Check TLS requirements when applicable.",
        "14. Confirm the application is using the same connection parameters.",
    ]

    for step in steps:
        print(step)

    explain(
        """
        Debugging should proceed from infrastructure toward application logic.

        Do not start by changing passwords when the error is "connection
        refused". Do not change pg_hba.conf when the client is connecting to
        the wrong server.

        The error message is evidence. Preserve the exact error before changing
        configuration.
        """
    )


# ============================================================================
# 52. MULTIPLE POSTGRESQL INSTALLATIONS
# ============================================================================

def show_multiple_installation_problem() -> None:
    print_section("52. Multiple PostgreSQL Installations")

    explain(
        """
        Developers can accidentally install PostgreSQL more than once.

        Examples:

            native Windows installation
            WSL PostgreSQL
            Docker PostgreSQL
            Homebrew PostgreSQL
            package-manager PostgreSQL
            cloud PostgreSQL

        This can produce confusing behavior:

            psql connects successfully
            but not to the database you expected.

        Diagnostic checks include:

            where psql
                Windows

            which psql
                Unix-like systems

            psql --version

            SELECT version();

            SELECT inet_server_addr(), inet_server_port();

        Compare the client executable, server version, host, port, and database.
        """
    )


# ============================================================================
# 53. WINDOWS PATH CONCEPTS
# ============================================================================

def show_windows_setup_concepts() -> None:
    print_section("53. Windows Installation Concepts")

    if platform.system() != "Windows":
        print("This machine is not running Windows; showing conceptual guidance.")

    explain(
        """
        On Windows, the PostgreSQL installer typically installs server
        components and client utilities.

        During installation, pay attention to:

            installation directory
            data directory
            database superuser name
            password
            port
            locale
            pgAdmin installation

        The PostgreSQL binary directory may need to be added to PATH if you
        want to invoke psql and related utilities from any terminal.

        The PostgreSQL server is normally registered as a Windows service.

        If psql is not recognized after installation, first check whether the
        PostgreSQL bin directory is included in PATH.
        """
    )


# ============================================================================
# 54. LINUX SETUP CONCEPTS
# ============================================================================

def show_linux_setup_concepts() -> None:
    print_section("54. Linux Installation Concepts")

    explain(
        """
        On Debian/Ubuntu systems, package-manager installation commonly
        involves commands in this family:

            sudo apt update
            sudo apt install postgresql postgresql-contrib

        The exact package names and supported PostgreSQL versions depend on
        the distribution and configured repositories.

        After installation, inspect service status:

            systemctl status postgresql

        A local psql session may be accessed through the postgres operating
        system account depending on the distribution's authentication setup.

        Do not assume that a Linux distribution's authentication defaults are
        identical to a Windows installer.
        """
    )


# ============================================================================
# 55. MACOS SETUP CONCEPTS
# ============================================================================

def show_macos_setup_concepts() -> None:
    print_section("55. macOS Installation Concepts")

    explain(
        """
        PostgreSQL on macOS can be installed through multiple approaches,
        including package managers and PostgreSQL installers.

        When using a package manager, service management may be controlled by
        the package manager.

        Verify:

            psql --version
            pg_isready
            which psql
            server connection parameters

        The goal is not to memorize one installation command. The important
        skill is understanding where the client, server, data directory,
        service manager, and configuration files are located.
        """
    )


# ============================================================================
# 56. SQL SCRIPT EXECUTION
# ============================================================================

def show_sql_file_execution() -> None:
    print_section("56. Executing SQL Files")

    commands = [
        "psql -d learning_db -f schema.sql",
        "psql -d learning_db -f seed.sql",
        "psql -d learning_db",
        "\\i schema.sql",
    ]

    for command in commands:
        print(command)

    explain(
        """
        SQL files make environment initialization reproducible.

        A schema.sql file might contain:

            CREATE SCHEMA app;
            CREATE TABLE app.customers (...);
            CREATE INDEX ...;

        psql can execute the file non-interactively.

        This makes SQL scripts useful in:

            local development
            CI pipelines
            test environments
            deployment automation

        Production migration systems should still provide proper migration
        ordering and failure handling rather than relying on one enormous
        initialization file.
        """
    )


# ============================================================================
# 57. PSQL OUTPUT CONTROL
# ============================================================================

def show_psql_output_features() -> None:
    print_section("57. Useful psql Output Features")

    commands = [
        "\\x",
        "\\timing",
        "\\pset pager off",
        "\\pset null '[NULL]'",
        "\\o query_output.txt",
        "\\o",
        "\\copy app.customers TO 'customers.csv' CSV HEADER",
    ]

    for command in commands:
        print(command)

    explain(
        """
        psql provides extensive output control.

        \\x
            Expanded display, useful for wide rows.

        \\timing
            Shows query execution time.

        \\pset
            Controls display behavior.

        \\o
            Redirects psql output to a file.

        \\copy
            Performs client-side data movement through psql.

        \\copy differs from server-side COPY in where the file is accessed.
        This distinction becomes important when the client and PostgreSQL
        server run on different machines.
        """
    )


# ============================================================================
# 58. COPY VERSUS \copy
# ============================================================================

def show_copy_difference() -> None:
    print_section("58. COPY Versus psql \\copy")

    print("Server-side SQL:")
    print("COPY app.customers TO '/server/path/customers.csv' CSV HEADER;")

    print()
    print("psql client-side command:")
    print("\\copy app.customers TO 'customers.csv' CSV HEADER")

    explain(
        """
        COPY is a PostgreSQL SQL command and interacts with the server's file
        system for file-based COPY operations.

        \\copy is a psql meta-command that transfers data through the client.

        This difference explains many file-permission and path-related errors.

        If a file exists on your laptop but PostgreSQL runs on a remote server,
        server-side COPY cannot automatically see your laptop's filesystem.
        """
    )


# ============================================================================
# 59. DATABASE CREATION WORKFLOW
# ============================================================================

def show_complete_database_setup_workflow() -> None:
    print_section("59. Complete Local Database Setup Workflow")

    workflow = [
        "1. Install PostgreSQL server and client tools.",
        "2. Verify psql is available.",
        "3. Verify PostgreSQL service is running.",
        "4. Confirm the configured port.",
        "5. Run pg_isready.",
        "6. Connect to the administrative postgres database.",
        "7. Create a dedicated development role.",
        "8. Create the application database.",
        "9. Connect to the new database.",
        "10. Create an application schema.",
        "11. Create tables through migrations or SQL scripts.",
        "12. Grant only required privileges.",
        "13. Verify current_user and current_database().",
        "14. Test application connectivity.",
        "15. Record setup assumptions in version control.",
    ]

    for item in workflow:
        print(item)


# ============================================================================
# 60. DATABASE CREATION AS SQL
# ============================================================================

def show_complete_setup_sql() -> None:
    print_section("60. Example Database Setup SQL")

    sql = """
    CREATE ROLE app_owner LOGIN;
    CREATE ROLE app_runtime LOGIN;

    CREATE DATABASE learning_db OWNER app_owner;

    -- Connect to learning_db before running the following statements.

    CREATE SCHEMA app AUTHORIZATION app_owner;

    GRANT CONNECT ON DATABASE learning_db TO app_runtime;
    GRANT USAGE ON SCHEMA app TO app_runtime;

    GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA app
    TO app_runtime;

    ALTER DEFAULT PRIVILEGES FOR ROLE app_owner
    IN SCHEMA app
    GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLES TO app_runtime;
    """

    print(textwrap.dedent(sql).strip())

    explain(
        """
        The example separates ownership from runtime access.

        app_owner:
            Owns application objects.

        app_runtime:
            Runs application queries with explicitly granted privileges.

        This is safer than using a superuser account for application traffic.

        In a real environment, role creation, passwords, ownership, migrations,
        and grants should be designed according to the application's actual
        security model.
        """
    )


# ============================================================================
# 61. SETUP VERIFICATION SQL
# ============================================================================

def show_setup_verification_sql() -> None:
    print_section("61. Verify the Environment from Inside PostgreSQL")

    queries = [
        "SELECT version();",
        "SELECT current_database();",
        "SELECT current_user;",
        "SELECT current_schema();",
        "SHOW server_version;",
        "SHOW port;",
        "SHOW listen_addresses;",
        "SHOW config_file;",
        "SHOW hba_file;",
        "SHOW data_directory;",
        "SHOW search_path;",
        "SELECT inet_server_addr();",
        "SELECT inet_server_port();",
    ]

    for query in queries:
        print(query)


# ============================================================================
# 62. PRODUCTION CONFIGURATION PRINCIPLES
# ============================================================================

def show_production_principles() -> None:
    print_section("62. Production-Oriented PostgreSQL Setup")

    principles = [
        "Use a dedicated database service rather than an ad-hoc workstation process.",
        "Define ownership and privilege boundaries.",
        "Use least-privilege application roles.",
        "Protect administrative credentials.",
        "Restrict inbound network access.",
        "Use TLS when required by the threat model.",
        "Centralize and monitor logs.",
        "Monitor connection counts and resource consumption.",
        "Establish backup retention policies.",
        "Test restoration procedures.",
        "Use schema migration tooling.",
        "Document configuration and version dependencies.",
        "Patch PostgreSQL and operating-system components.",
        "Avoid manually changing production databases without change control.",
        "Measure before changing performance parameters.",
    ]

    for principle in principles:
        print(f"[ ] {principle}")


# ============================================================================
# 63. PERFORMANCE SETUP CONSIDERATIONS
# ============================================================================

def show_performance_setup() -> None:
    print_section("63. Performance-Related Environment Considerations")

    settings = [
        "max_connections",
        "shared_buffers",
        "work_mem",
        "maintenance_work_mem",
        "effective_cache_size",
        "wal_buffers",
        "checkpoint_timeout",
        "max_wal_size",
    ]

    for setting in settings:
        print(f"SHOW {setting};")

    explain(
        """
        PostgreSQL performance settings depend heavily on workload and
        hardware.

        Do not copy a random configuration from the Internet and assume it is
        optimal.

        Important factors include:

            available RAM
            CPU count
            storage latency
            transaction volume
            query complexity
            connection count
            working-set size
            backup strategy
            replication
            workload mix

        Environment setup establishes the foundation. Performance tuning
        should be evidence-driven using measurements and workload observation.
        """
    )


# ============================================================================
# 64. LOGGING
# ============================================================================

def show_logging_concepts() -> None:
    print_section("64. PostgreSQL Logging")

    settings = [
        "SHOW log_destination;",
        "SHOW logging_collector;",
        "SHOW log_directory;",
        "SHOW log_filename;",
        "SHOW log_min_duration_statement;",
        "SHOW log_connections;",
        "SHOW log_disconnections;",
    ]

    for setting in settings:
        print(setting)

    explain(
        """
        Logs are essential for diagnosing:

            authentication failures
            server startup problems
            crashes
            connection problems
            long-running statements
            operational events

        Logging too little can hide failures.

        Logging too much can create:

            storage growth
            performance overhead
            sensitive-data exposure

        Production logging should therefore be deliberate and monitored.
        """
    )


# ============================================================================
# 65. HEALTH CHECK DESIGN
# ============================================================================

def show_health_check_design() -> None:
    print_section("65. PostgreSQL Health Checks")

    checks = [
        "TCP port reachable",
        "pg_isready reports readiness",
        "application role can authenticate",
        "target database exists",
        "basic SELECT succeeds",
        "critical schema exists",
        "critical migration version is present",
    ]

    for index, check in enumerate(checks, start=1):
        print(f"{index}. {check}")

    explain(
        """
        A health check should answer a specific operational question.

        "Port 5432 is open" is a weak health check.

        A stronger application-level check verifies that:

            the intended PostgreSQL server is reachable
            the intended role can authenticate
            the intended database exists
            a basic query works

        Deeper checks may validate migrations and application-specific
        dependencies.
        """
    )


# ============================================================================
# 66. CONFIGURATION DRIFT
# ============================================================================

def show_configuration_drift() -> None:
    print_section("66. Configuration Drift")

    explain(
        """
        Configuration drift occurs when environments gradually stop matching
        their intended configuration.

        Examples:

            development uses PostgreSQL 18
            staging uses PostgreSQL 17
            production uses PostgreSQL 16

        or:

            local pg_hba.conf differs from documented assumptions
            application uses port 5433 on one machine
            another machine has two PostgreSQL instances
            one developer has a manually created schema

        Reproducibility reduces drift.

        Useful controls include:

            version pinning
            migration files
            infrastructure configuration
            environment documentation
            automated validation
            CI checks
        """
    )


# ============================================================================
# 67. SECURITY MISTAKES
# ============================================================================

def show_security_mistakes() -> None:
    print_section("67. Common Security Mistakes")

    mistakes = [
        "Using the postgres superuser inside an application.",
        "Using trust authentication without understanding the network boundary.",
        "Opening PostgreSQL to the public internet unnecessarily.",
        "Committing passwords to Git.",
        "Printing connection URIs containing credentials.",
        "Using a single shared account for every application.",
        "Granting broad privileges instead of specific privileges.",
        "Ignoring TLS requirements for remote connections.",
        "Leaving unused roles active indefinitely.",
        "Treating a successful port scan as proof of safe configuration.",
        "Assuming persistent storage is a backup.",
        "Never testing restore procedures.",
    ]

    for mistake in mistakes:
        print(f"[!] {mistake}")


# ============================================================================
# 68. EDGE CASES
# ============================================================================

def show_edge_cases() -> None:
    print_section("68. PostgreSQL Environment Edge Cases")

    cases = [
        (
            "Port 5432 is occupied",
            "PostgreSQL may fail to start or may use another configured port.",
        ),
        (
            "localhost resolves to IPv6",
            "The pg_hba.conf rule may permit IPv4 but not IPv6.",
        ),
        (
            "psql connects to the wrong server",
            "PATH, containers, ports, or multiple installations can cause confusion.",
        ),
        (
            "Role exists but cannot connect",
            "The role may have NOLOGIN or lack CONNECT permission.",
        ),
        (
            "Database exists but cannot be dropped",
            "Active sessions may be connected to it.",
        ),
        (
            "Password is correct but login fails",
            "Authentication method or pg_hba.conf can still reject the connection.",
        ),
        (
            "pgAdmin works but application fails",
            "Application connection parameters, driver behavior, or TLS settings may differ.",
        ),
        (
            "psql works locally but remote connection fails",
            "listen_addresses, firewall, pg_hba.conf, DNS, or network routing may differ.",
        ),
        (
            "Schema exists but table is not found",
            "search_path or schema qualification may be incorrect.",
        ),
    ]

    for title, explanation_text in cases:
        print(f"{title:<34} -> {explanation_text}")


# ============================================================================
# 69. BEST PRACTICES
# ============================================================================

def show_best_practices() -> None:
    print_section("69. PostgreSQL Environment Best Practices")

    practices = [
        "Know exactly which PostgreSQL server your client is connecting to.",
        "Use explicit host, port, database, and user values while debugging.",
        "Use psql for precise command-line diagnostics.",
        "Use pgAdmin when graphical inspection is useful.",
        "Keep database schema changes in version-controlled migrations.",
        "Use dedicated roles.",
        "Apply least privilege.",
        "Keep secrets outside source code.",
        "Use secure authentication.",
        "Restrict network exposure.",
        "Document environment-specific assumptions.",
        "Use health checks.",
        "Monitor server logs.",
        "Measure before tuning.",
        "Back up important data.",
        "Regularly test restoration.",
    ]

    for practice in practices:
        print(f"[✓] {practice}")


# ============================================================================
# 70. MINI KNOWLEDGE TEST
# ============================================================================

def knowledge_test() -> None:
    print_section("70. PostgreSQL Environment Knowledge Test")

    questions = [
        (
            "What is the conventional PostgreSQL TCP port?",
            "5432",
        ),
        (
            "What command-line client is commonly used to interact with PostgreSQL?",
            "psql",
        ),
        (
            "What GUI administration tool is commonly associated with PostgreSQL?",
            "pgAdmin",
        ),
        (
            "Which configuration file controls host-based authentication?",
            "pg_hba.conf",
        ),
        (
            "What SQL command creates a database?",
            "CREATE DATABASE",
        ),
        (
            "What SQL command creates a role?",
            "CREATE ROLE",
        ),
        (
            "What psql command lists databases?",
            "\\l",
        ),
        (
            "What psql command changes the connected database?",
            "\\c",
        ),
        (
            "What environment variable commonly specifies PostgreSQL's host?",
            "PGHOST",
        ),
        (
            "What environment variable commonly specifies PostgreSQL's port?",
            "PGPORT",
        ),
    ]

    for number, (question, answer) in enumerate(questions, start=1):
        print(f"{number}. {question}")
        print(f"   Answer: {answer}")


# ============================================================================
# 71. COMMAND REFERENCE
# ============================================================================

def show_command_reference() -> None:
    print_section("71. Compact Command Reference")

    commands = [
        ("Check psql", "psql --version"),
        ("Check readiness", "pg_isready"),
        ("Connect", "psql -h localhost -p 5432 -U postgres -d postgres"),
        ("List databases", "\\l"),
        ("Connect to database", "\\c database_name"),
        ("Connection details", "\\conninfo"),
        ("List roles", "\\du"),
        ("List schemas", "\\dn"),
        ("List tables", "\\dt"),
        ("Describe table", "\\d table_name"),
        ("Exit", "\\q"),
        ("SQL help", "\\h SELECT"),
        ("psql help", "\\?"),
        ("Create database", "createdb database_name"),
        ("Drop database", "dropdb database_name"),
        ("Create role", "createuser role_name"),
        ("Drop role", "dropuser role_name"),
        ("Backup", "pg_dump database_name > backup.sql"),
        ("Restore archive", "pg_restore -d database_name backup.dump"),
    ]

    print(f"{'Purpose':<25} Command")
    print("-" * 78)

    for purpose, command in commands:
        print(f"{purpose:<25} {command}")


# ============================================================================
# 72. SAMPLE SQL STUDY SCRIPT
# ============================================================================

def show_sample_sql_study_script() -> None:
    print_section("72. Sample SQL Study Script")

    sql = """
    -- Create a schema.
    CREATE SCHEMA IF NOT EXISTS app;

    -- Create a simple table.
    CREATE TABLE IF NOT EXISTS app.customers (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- Insert sample data.
    INSERT INTO app.customers (name, email)
    VALUES
        ('Alice', 'alice@example.com'),
        ('Bob', 'bob@example.com');

    -- Query the data.
    SELECT id, name, email, created_at
    FROM app.customers
    ORDER BY id;
    """

    print(textwrap.dedent(sql).strip())

    explain(
        """
        This illustrates how environment setup leads into actual SQL work.

        PostgreSQL installation alone does not create application structure.
        The client connects to the server, the application database is selected,
        schemas and tables are created, and data operations can then occur.
        """
    )


# ============================================================================
# 73. SAFE DEMONSTRATION OF DESTRUCTIVE COMMANDS
# ============================================================================

def show_destructive_operation_warning() -> None:
    print_section("73. Destructive Operations")

    destructive_commands = [
        "DROP DATABASE learning_db;",
        "DROP ROLE learning_user;",
        "dropdb learning_db",
        "dropuser learning_user",
    ]

    print("Examples that require deliberate confirmation:")
    for command in destructive_commands:
        print(command)

    explain(
        """
        Destructive commands are shown but are not executed automatically by
        this educational script.

        Before destructive database operations, establish:

            correct server
            correct database
            correct role
            active backup
            expected session state
            intended change scope

        This is especially important when multiple environments exist.
        """
    )


# ============================================================================
# 74. ARGUMENT PARSER
# ============================================================================

def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Study PostgreSQL environment setup from beginner to advanced concepts."
        )
    )

    parser.add_argument(
        "--environment-check",
        action="store_true",
        help="Run non-destructive local PostgreSQL environment checks.",
    )

    parser.add_argument(
        "--readiness",
        action="store_true",
        help="Check PostgreSQL readiness using pg_isready when available.",
    )

    parser.add_argument(
        "--connection-test",
        action="store_true",
        help="Attempt a live Python connection if psycopg is installed.",
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only the core environment checks and command reference.",
    )

    return parser


# ============================================================================
# 75. QUICK MODE
# ============================================================================

def run_quick_mode() -> None:
    print_section("Quick PostgreSQL Environment Check")

    show_operating_system_information()
    show_postgresql_client_tools()
    demonstrate_version_detection()
    demonstrate_connection_parameters()
    print_environment_validation()
    show_command_reference()


# ============================================================================
# 76. FULL STUDY MODE
# ============================================================================

def run_full_study() -> None:
    demonstrate_postgresql_vocabulary()
    show_operating_system_information()
    show_postgresql_client_tools()
    demonstrate_server_readiness()
    demonstrate_connection_parameters()
    demonstrate_sql_generation()
    show_database_creation_commands()
    show_role_concepts()
    show_schema_concepts()
    show_psql_meta_commands()
    show_psql_connection_examples()
    demonstrate_connection_uri_structure()
    show_postgresql_environment_variables()
    show_password_file_information()
    show_service_management_examples()
    show_configuration_concepts()
    show_listen_address_security()
    show_pg_hba_concepts()
    explain_authentication_failure_layers()
    show_pgadmin_concepts()
    compare_psql_and_pgadmin()
    demonstrate_version_detection()
    explain_python_postgresql_drivers()
    demonstrate_psycopg_import()
    demonstrate_programmatic_connection()
    demonstrate_parameterized_sql()
    show_transaction_concepts()
    show_database_ownership()
    show_default_privileges()
    explain_database_connection_model()
    show_database_information_queries()
    demonstrate_localhost_resolution()
    demonstrate_port_checking()
    show_docker_postgresql_concept()
    show_postgresql_storage_concepts()
    print_environment_validation()
    show_reproducible_setup()
    show_migration_concepts()
    show_extensions()
    show_timezone_concepts()
    show_encoding_locale_concepts()
    show_database_templates()
    show_diagnostic_queries()
    explain_active_connections()
    show_connection_pooling()
    show_connection_limits()
    show_security_baseline()
    show_ssl_concepts()
    show_backup_tools()
    show_common_installation_failures()
    show_debugging_workflow()
    show_multiple_installation_problem()
    show_windows_setup_concepts()
    show_linux_setup_concepts()
    show_macos_setup_concepts()
    show_sql_file_execution()
    show_psql_output_features()
    show_copy_difference()
    show_complete_database_setup_workflow()
    show_complete_setup_sql()
    show_setup_verification_sql()
    show_production_principles()
    show_performance_setup()
    show_logging_concepts()
    show_health_check_design()
    show_configuration_drift()
    show_security_mistakes()
    show_edge_cases()
    show_best_practices()
    knowledge_test()
    show_command_reference()
    show_sample_sql_study_script()
    show_destructive_operation_warning()


# ============================================================================
# 77. MAIN ENTRY POINT
# ============================================================================

def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    print(
        """
PostgreSQL Environment Setup
A comprehensive Python-based study and diagnostic guide
        """.strip()
    )

    if args.quick:
        run_quick_mode()
        return

    if args.environment_check:
        print_environment_validation()

    if args.readiness:
        demonstrate_server_readiness()

    if args.connection_test:
        demonstrate_programmatic_connection()

    # If no special operation was requested, run the complete educational guide.
    if not any(
        [
            args.environment_check,
            args.readiness,
            args.connection_test,
            args.quick,
        ]
    ):
        run_full_study()


if __name__ == "__main__":
    main()
