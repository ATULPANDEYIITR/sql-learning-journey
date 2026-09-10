"""
SELECT Fundamentals
====================

A standalone study script for learning SQL SELECT fundamentals from beginner
through advanced beginner/intermediate level.

Topics covered:
- SELECT and FROM
- Selecting individual columns
- Selecting multiple columns
- SELECT *
- Column order
- Expressions and calculated columns
- Arithmetic expressions
- String expressions
- NULL and NULL propagation
- Column aliases with AS
- Alias rules and limitations
- DISTINCT
- WHERE and its relationship with SELECT
- ORDER BY and aliases
- LIMIT and OFFSET
- CASE expressions
- Aggregate expressions
- Functions inside SELECT
- Selecting constants and literal values
- Table and column qualification
- Ambiguous column names
- Joins and qualified SELECT lists
- Expressions involving dates
- Boolean expressions
- Type conversion
- SQLite-specific observations
- Query readability
- Performance considerations
- Security considerations
- Common mistakes
- Edge cases
- Practical examples
- Testing and verification

The examples use Python's built-in sqlite3 module so that the SQL can be
executed without installing external packages.

The educational focus is SQL SELECT. Python is used only as the execution
environment and to demonstrate the SQL behavior programmatically.
"""

import sqlite3
from datetime import datetime


# ============================================================================
# 1. DATABASE SETUP
# ============================================================================

def create_connection():
    """Create an in-memory SQLite database."""
    return sqlite3.connect(":memory:")


def create_schema(connection):
    """Create tables used throughout the examples."""
    cursor = connection.cursor()

    cursor.executescript(
        """
        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL,
            location TEXT
        );

        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            department_id INTEGER,
            job_title TEXT,
            salary REAL,
            bonus REAL,
            hire_date TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (department_id) REFERENCES departments(department_id)
        );

        CREATE TABLE projects (
            project_id INTEGER PRIMARY KEY,
            project_name TEXT NOT NULL,
            department_id INTEGER,
            budget REAL,
            status TEXT,
            FOREIGN KEY (department_id) REFERENCES departments(department_id)
        );
        """
    )

    connection.commit()


def insert_sample_data(connection):
    """Insert realistic sample data, including NULL values."""
    cursor = connection.cursor()

    departments = [
        (10, "Engineering", "Bengaluru"),
        (20, "Finance", "Mumbai"),
        (30, "Human Resources", "Delhi"),
        (40, "Marketing", "Pune"),
        (50, "Operations", "Lucknow"),
    ]

    employees = [
        (
            1,
            "Aarav",
            "Sharma",
            "aarav@example.com",
            10,
            "Software Engineer",
            85000,
            5000,
            "2022-04-15",
            1,
        ),
        (
            2,
            "Priya",
            "Mehta",
            "priya@example.com",
            10,
            "Senior Software Engineer",
            115000,
            12000,
            "2020-08-10",
            1,
        ),
        (
            3,
            "Rahul",
            "Verma",
            "rahul@example.com",
            20,
            "Financial Analyst",
            72000,
            None,
            "2023-01-20",
            1,
        ),
        (
            4,
            "Neha",
            "Gupta",
            "neha@example.com",
            20,
            "Finance Manager",
            125000,
            15000,
            "2019-06-05",
            1,
        ),
        (
            5,
            "Kabir",
            "Singh",
            "kabir@example.com",
            30,
            "HR Specialist",
            65000,
            3000,
            "2024-02-12",
            1,
        ),
        (
            6,
            "Ananya",
            "Iyer",
            None,
            40,
            "Marketing Analyst",
            68000,
            4000,
            "2023-09-01",
            1,
        ),
        (
            7,
            "Vikram",
            "Patel",
            "vikram@example.com",
            50,
            "Operations Manager",
            98000,
            8000,
            "2018-11-23",
            1,
        ),
        (
            8,
            "Meera",
            "Nair",
            "meera@example.com",
            None,
            "Consultant",
            90000,
            None,
            "2025-03-18",
            1,
        ),
        (
            9,
            "Rohan",
            "Das",
            "rohan@example.com",
            10,
            "Intern",
            30000,
            1000,
            "2025-06-01",
            0,
        ),
    ]

    projects = [
        (101, "Analytics Platform", 10, 250000, "Active"),
        (102, "Budget Automation", 20, 175000, "Active"),
        (103, "Employee Portal", 30, 90000, "Completed"),
        (104, "Campaign Intelligence", 40, 140000, "Planning"),
        (105, "Supply Optimization", 50, 300000, "Active"),
    ]

    cursor.executemany(
        """
        INSERT INTO departments
        (department_id, department_name, location)
        VALUES (?, ?, ?)
        """,
        departments,
    )

    cursor.executemany(
        """
        INSERT INTO employees
        (
            employee_id,
            first_name,
            last_name,
            email,
            department_id,
            job_title,
            salary,
            bonus,
            hire_date,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        employees,
    )

    cursor.executemany(
        """
        INSERT INTO projects
        (project_id, project_name, department_id, budget, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        projects,
    )

    connection.commit()


# ============================================================================
# 2. HELPER FUNCTIONS
# ============================================================================

def print_title(title):
    """Print a readable section title."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_query(connection, sql, parameters=()):
    """
    Execute a SELECT statement and display column names and rows.

    This helper deliberately displays the SQL because the purpose of the
    script is to study the SELECT statement itself.
    """
    print("\nSQL:")
    print(sql.strip())

    if parameters:
        print("Parameters:", parameters)

    cursor = connection.execute(sql, parameters)

    if cursor.description is None:
        print("This statement did not return a result set.")
        return

    column_names = [column[0] for column in cursor.description]
    rows = cursor.fetchall()

    print("\nColumns:")
    print(column_names)

    print("Rows:")
    for row in rows:
        print(row)

    print(f"\nRow count: {len(rows)}")


def print_concept(name, explanation):
    """Display a concise conceptual explanation."""
    print(f"\n{name}")
    print("-" * len(name))
    print(explanation)


# ============================================================================
# 3. WHAT SELECT DOES
# ============================================================================

def section_select_basics(connection):
    print_title("3. SELECT fundamentals")

    print_concept(
        "What is SELECT?",
        """
SELECT is the SQL statement used to request data from a database.

A basic query normally has this structure:

SELECT column1, column2
FROM table_name;

The SELECT clause specifies what should appear in the result.
The FROM clause specifies where the data should come from.

The database evaluates the SQL statement and returns a result set.
A result set consists of rows and columns.
""",
    )

    print_query(
        connection,
        """
        SELECT first_name
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT first_name, last_name
        FROM employees;
        """,
    )


# ============================================================================
# 4. SELECTING A SINGLE COLUMN
# ============================================================================

def section_single_column(connection):
    print_title("4. Selecting a single column")

    print_concept(
        "Single-column selection",
        """
The simplest useful SELECT query chooses one column from a table.

The column name is written after SELECT.

Example:

SELECT first_name
FROM employees;

Only first_name is returned, even though the employees table contains
many other columns.
""",
    )

    print_query(
        connection,
        """
        SELECT first_name
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT salary
        FROM employees;
        """,
    )


# ============================================================================
# 5. SELECTING MULTIPLE COLUMNS
# ============================================================================

def section_multiple_columns(connection):
    print_title("5. Selecting multiple columns")

    print_concept(
        "Comma-separated column list",
        """
Multiple columns are separated by commas.

Example:

SELECT first_name, last_name, job_title
FROM employees;

The order of columns in the SELECT list determines the order of columns
in the result.
""",
    )

    print_query(
        connection,
        """
        SELECT first_name, last_name, job_title
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT job_title, first_name, salary
        FROM employees;
        """,
    )

    print_concept(
        "Important observation",
        """
Changing the order in SELECT does not change the underlying table.
It changes only the presentation order of columns in the result set.
""",
    )


# ============================================================================
# 6. SELECT *
# ============================================================================

def section_select_star(connection):
    print_title("6. SELECT *")

    print_concept(
        "The wildcard",
        """
The asterisk (*) means all columns from the selected source.

Example:

SELECT *
FROM employees;

This is convenient for exploration because it returns every column.

It is often less appropriate for production application queries because:
- the table may contain many columns;
- unnecessary data may be transferred;
- schema changes can change the result;
- sensitive columns might accidentally be returned;
- consumers become dependent on column order and schema;
- query intent becomes less explicit.
""",
    )

    print_query(
        connection,
        """
        SELECT *
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT *
        FROM departments;
        """,
    )

    print_concept(
        "Explicit selection versus *",
        """
Prefer explicit columns when the consumer knows exactly what it needs.

Exploratory analysis:
    SELECT * FROM employees;

Production-oriented query:
    SELECT employee_id, first_name, last_name, job_title
    FROM employees;

The second form documents the intended output more clearly.
""",
    )


# ============================================================================
# 7. SELECTING CONSTANTS
# ============================================================================

def section_literals(connection):
    print_title("7. Selecting constants and literal values")

    print_concept(
        "Literal expressions",
        """
SELECT can return literal values without reading a table column.

A literal is a value written directly in SQL.

Examples:
- numeric literal: 100
- text literal: 'Hello'
- NULL: NULL

SQLite allows a SELECT without FROM, which is useful for demonstrating
expressions and constants.
""",
    )

    print_query(
        connection,
        """
        SELECT 100;
        """,
    )

    print_query(
        connection,
        """
        SELECT 'SQL';
        """,
    )

    print_query(
        connection,
        """
        SELECT 10, 20, 'Database';
        """,
    )

    print_query(
        connection,
        """
        SELECT NULL;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            2026 AS current_year,
            'SQL' AS subject,
            100 AS score;
        """,
    )


# ============================================================================
# 8. EXPRESSIONS
# ============================================================================

def section_expressions(connection):
    print_title("8. Expressions in SELECT")

    print_concept(
        "What is an expression?",
        """
An expression is something SQL can evaluate to produce a value.

Examples:
- salary
- salary + bonus
- salary * 12
- first_name || ' ' || last_name
- UPPER(first_name)
- CASE WHEN salary >= 100000 THEN 'High' ELSE 'Standard' END

Expressions allow SELECT to return calculated or transformed values instead
of merely copying stored columns.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            salary * 12
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            bonus,
            salary + bonus
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            salary * 0.10
        FROM employees;
        """,
    )


# ============================================================================
# 9. ARITHMETIC EXPRESSIONS
# ============================================================================

def section_arithmetic(connection):
    print_title("9. Arithmetic expressions")

    print_concept(
        "Arithmetic operators",
        """
Common SQL arithmetic operators include:

+   addition
-   subtraction
*   multiplication
/   division
%   modulo in SQLite

Expressions can combine constants and columns.

For example:

SELECT salary * 1.10
FROM employees;

This calculates a hypothetical 10 percent salary increase without changing
the stored salary.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            salary * 1.10 AS projected_salary
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            salary / 12 AS approximate_monthly_salary
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            salary + 5000 AS salary_after_fixed_increment
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            17 % 5 AS remainder;
        """,
    )


# ============================================================================
# 10. NULL AND EXPRESSIONS
# ============================================================================

def section_null_behavior(connection):
    print_title("10. NULL and SELECT expressions")

    print_concept(
        "NULL is not zero",
        """
NULL represents missing, unknown, or unavailable information.

NULL is different from:
- 0
- an empty string
- the text 'NULL'

Arithmetic involving NULL normally produces NULL.

For example:

salary + bonus

will produce NULL when bonus is NULL in this dataset.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            bonus,
            salary + bonus AS total_compensation
        FROM employees;
        """,
    )

    print_concept(
        "COALESCE",
        """
COALESCE can replace NULL with another value.

For compensation calculations, treating a missing bonus as zero may be
appropriate:

COALESCE(bonus, 0)

This is a business decision, not merely a technical one. Missing data does
not always mean zero.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            bonus,
            salary + COALESCE(bonus, 0) AS total_compensation
        FROM employees;
        """,
    )


# ============================================================================
# 11. COLUMN ALIASES
# ============================================================================

def section_aliases(connection):
    print_title("11. Column aliases")

    print_concept(
        "What is an alias?",
        """
An alias gives a result column a temporary output name.

Syntax:

SELECT expression AS alias_name
FROM table_name;

The alias changes the name displayed in the result. It does not rename the
underlying database column.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name AS employee_first_name,
            last_name AS employee_last_name
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            salary * 12 AS annual_salary
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name || ' ' || last_name AS full_name
        FROM employees;
        """,
    )

    print_concept(
        "AS is optional in many SQL dialects",
        """
Many SQL implementations allow:

SELECT salary * 12 annual_salary
FROM employees;

Using AS is generally clearer, especially for beginners and complex
expressions.
""",
    )

    print_query(
        connection,
        """
        SELECT salary * 12 annual_salary
        FROM employees;
        """,
    )


# ============================================================================
# 12. ALIAS NAMING
# ============================================================================

def section_alias_naming(connection):
    print_title("12. Alias naming rules and practical choices")

    print_concept(
        "Readable aliases",
        """
Aliases should communicate what the result means.

Weak:
    salary * 12 AS x

Clear:
    salary * 12 AS annual_salary

For aliases containing spaces, quoting rules depend on the SQL dialect.
SQLite accepts double quotes for identifiers.

In production SQL, simple snake_case aliases are usually easy to consume
from applications and analytics tools.
""",
    )

    print_query(
        connection,
        """
        SELECT
            salary * 12 AS annual_salary,
            salary * 12 * 0.10 AS estimated_tax
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name || ' ' || last_name AS "Full Name"
        FROM employees;
        """,
    )


# ============================================================================
# 13. DISTINCT
# ============================================================================

def section_distinct(connection):
    print_title("13. DISTINCT in SELECT")

    print_concept(
        "Removing duplicate result rows",
        """
DISTINCT asks SQL to eliminate duplicate rows from the selected result.

Example:

SELECT DISTINCT department_id
FROM employees;

DISTINCT applies to the complete selected combination, not independently
to each selected column.
""",
    )

    print_query(
        connection,
        """
        SELECT department_id
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT DISTINCT department_id
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT DISTINCT department_id, active
        FROM employees;
        """,
    )

    print_concept(
        "DISTINCT and NULL",
        """
NULL values are considered as one distinct value for the purpose of
DISTINCT results. Therefore, a column containing several NULLs can produce
one NULL result.
""",
    )


# ============================================================================
# 14. WHERE AND SELECT
# ============================================================================

def section_where_relationship(connection):
    print_title("14. SELECT and WHERE")

    print_concept(
        "Selecting columns versus filtering rows",
        """
SELECT determines which columns appear in the result.

WHERE determines which rows qualify.

Example:

SELECT first_name, salary
FROM employees
WHERE salary > 80000;

The SELECT list does not determine which rows are included.
The WHERE condition does.
""",
    )

    print_query(
        connection,
        """
        SELECT first_name, salary
        FROM employees
        WHERE salary > 80000;
        """,
    )

    print_query(
        connection,
        """
        SELECT first_name, job_title
        FROM employees
        WHERE department_id = 10;
        """,
    )

    print_concept(
        "Important distinction",
        """
These are separate ideas:

SELECT first_name, salary
    chooses output columns.

WHERE salary > 80000
    filters input rows.

A query can select one column while filtering on another.
""",
    )

    print_query(
        connection,
        """
        SELECT first_name
        FROM employees
        WHERE salary > 80000;
        """,
    )


# ============================================================================
# 15. ORDER BY AND SELECT
# ============================================================================

def section_order_by(connection):
    print_title("15. ORDER BY with SELECT")

    print_concept(
        "Sorting results",
        """
ORDER BY controls result ordering.

Examples:

ORDER BY salary
ORDER BY salary DESC
ORDER BY first_name ASC

ASC is ascending and is the default in many systems.
DESC is descending.
""",
    )

    print_query(
        connection,
        """
        SELECT first_name, salary
        FROM employees
        ORDER BY salary;
        """,
    )

    print_query(
        connection,
        """
        SELECT first_name, salary
        FROM employees
        ORDER BY salary DESC;
        """,
    )

    print_query(
        connection,
        """
        SELECT first_name, salary
        FROM employees
        ORDER BY salary DESC, first_name ASC;
        """,
    )


# ============================================================================
# 16. ORDERING BY ALIASES
# ============================================================================

def section_order_by_alias(connection):
    print_title("16. ORDER BY an alias")

    print_concept(
        "Alias reuse in ORDER BY",
        """
In SQLite, an alias defined in SELECT can be referenced by ORDER BY.

This can make calculated-result sorting easier to read.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary * 12 AS annual_salary
        FROM employees
        ORDER BY annual_salary DESC;
        """,
    )


# ============================================================================
# 17. LIMIT AND OFFSET
# ============================================================================

def section_limit_offset(connection):
    print_title("17. LIMIT and OFFSET")

    print_concept(
        "Limiting result rows",
        """
LIMIT restricts how many rows are returned.

OFFSET skips rows before returning the requested number.

These clauses are useful for small previews and pagination.

Without ORDER BY, the database does not generally promise a meaningful
business ordering of rows. Pagination should normally use a deterministic
ORDER BY.
""",
    )

    print_query(
        connection,
        """
        SELECT employee_id, first_name, salary
        FROM employees
        ORDER BY salary DESC
        LIMIT 3;
        """,
    )

    print_query(
        connection,
        """
        SELECT employee_id, first_name, salary
        FROM employees
        ORDER BY employee_id
        LIMIT 3 OFFSET 3;
        """,
    )


# ============================================================================
# 18. STRING EXPRESSIONS
# ============================================================================

def section_string_expressions(connection):
    print_title("18. String expressions")

    print_concept(
        "Combining and transforming text",
        """
SQL can construct new text values.

In SQLite, || concatenates strings.

Examples:

first_name || ' ' || last_name
UPPER(first_name)
LOWER(last_name)
LENGTH(first_name)

These are expressions, so they can appear directly in SELECT.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            last_name,
            first_name || ' ' || last_name AS full_name
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            UPPER(first_name) AS uppercase_name,
            LOWER(last_name) AS lowercase_last_name,
            LENGTH(first_name) AS first_name_length
        FROM employees;
        """,
    )

    print_concept(
        "NULL and string concatenation",
        """
If a participating expression is NULL, concatenation behavior can produce
NULL depending on the SQL expression and database dialect. SQLite's
concatenation operator treats NULL as an empty string in this context.

For portable SQL, explicitly handling missing values with COALESCE can make
the intended behavior clearer.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            COALESCE(email, 'No email available') AS contact_email
        FROM employees;
        """,
    )


# ============================================================================
# 19. CASE EXPRESSIONS
# ============================================================================

def section_case(connection):
    print_title("19. CASE expressions")

    print_concept(
        "Conditional output",
        """
CASE allows SELECT to produce different values based on conditions.

Searched CASE syntax:

CASE
    WHEN condition THEN result
    WHEN condition THEN result
    ELSE result
END

It is useful for classifications, labels, business rules, and conditional
calculations.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            CASE
                WHEN salary >= 100000 THEN 'High'
                WHEN salary >= 70000 THEN 'Medium'
                ELSE 'Standard'
            END AS salary_band
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            active,
            CASE
                WHEN active = 1 THEN 'Active'
                ELSE 'Inactive'
            END AS employee_status
        FROM employees;
        """,
    )


# ============================================================================
# 20. DATE-RELATED EXPRESSIONS
# ============================================================================

def section_date_expressions(connection):
    print_title("20. Date expressions")

    print_concept(
        "Dates in SQLite",
        """
SQLite does not have a dedicated DATE storage class in the same way some
enterprise database systems do. Dates are commonly stored as ISO-formatted
text, Julian day values, or Unix timestamps.

SQLite provides date/time functions such as date(), datetime(), and strftime().

The dataset uses ISO text dates such as 2022-04-15.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            hire_date,
            strftime('%Y', hire_date) AS hire_year
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            hire_date,
            date(hire_date, '+1 year') AS first_anniversary
        FROM employees;
        """,
    )


# ============================================================================
# 21. BOOLEAN-STYLE EXPRESSIONS
# ============================================================================

def section_boolean_expressions(connection):
    print_title("21. Boolean-style expressions in SELECT")

    print_concept(
        "Conditions can produce values",
        """
SQL conditions can be used as expressions in many database systems.

SQLite represents boolean-like results as integers:
0 means false
1 means true

This can be useful for analytical flags.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            salary >= 100000 AS earns_at_least_100k
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            department_id = 10 AS engineering_employee
        FROM employees;
        """,
    )


# ============================================================================
# 22. TABLE QUALIFICATION
# ============================================================================

def section_qualified_columns(connection):
    print_title("22. Qualified column names")

    print_concept(
        "table_name.column_name",
        """
When multiple tables are involved, qualify columns with the table name or
table alias.

Example:

SELECT employees.first_name, departments.department_name
FROM employees
JOIN departments
    ON employees.department_id = departments.department_id;

Qualification improves clarity and prevents ambiguity when multiple tables
contain columns with the same name.
""",
    )

    print_query(
        connection,
        """
        SELECT
            employees.first_name,
            employees.last_name,
            departments.department_name
        FROM employees
        JOIN departments
            ON employees.department_id = departments.department_id;
        """,
    )


# ============================================================================
# 23. TABLE ALIASES
# ============================================================================

def section_table_aliases(connection):
    print_title("23. Table aliases")

    print_concept(
        "Shorter table references",
        """
A table alias gives a table a shorter temporary name.

Example:

FROM employees AS e

Then:

SELECT e.first_name
FROM employees AS e;

Table aliases are particularly useful with joins and self-joins.
""",
    )

    print_query(
        connection,
        """
        SELECT
            e.first_name,
            e.last_name,
            d.department_name
        FROM employees AS e
        JOIN departments AS d
            ON e.department_id = d.department_id;
        """,
    )


# ============================================================================
# 24. JOINED SELECT LISTS
# ============================================================================

def section_joined_select(connection):
    print_title("24. Selecting columns from joined tables")

    print_concept(
        "SELECT after JOIN",
        """
A SELECT list can contain columns from multiple sources.

For example:

SELECT
    e.first_name,
    d.department_name,
    p.project_name
FROM employees AS e
JOIN departments AS d
    ON e.department_id = d.department_id
LEFT JOIN projects AS p
    ON d.department_id = p.department_id;

The SELECT list determines which joined data is returned.
""",
    )

    print_query(
        connection,
        """
        SELECT
            e.first_name,
            e.job_title,
            d.department_name,
            d.location
        FROM employees AS e
        LEFT JOIN departments AS d
            ON e.department_id = d.department_id;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            d.department_name,
            p.project_name,
            p.budget
        FROM departments AS d
        LEFT JOIN projects AS p
            ON d.department_id = p.department_id;
        """,
    )


# ============================================================================
# 25. AMBIGUOUS COLUMN NAMES
# ============================================================================

def section_ambiguity(connection):
    print_title("25. Ambiguous column names")

    print_concept(
        "Why qualification matters",
        """
Suppose two joined tables both contain department_id.

Writing:

SELECT department_id

may be ambiguous because SQL cannot determine which source you mean.

Writing:

SELECT e.department_id

or:

SELECT d.department_id

removes the ambiguity.
""",
    )

    print_query(
        connection,
        """
        SELECT
            e.department_id AS employee_department_id,
            d.department_id AS matched_department_id,
            d.department_name
        FROM employees AS e
        LEFT JOIN departments AS d
            ON e.department_id = d.department_id;
        """,
    )


# ============================================================================
# 26. AGGREGATE EXPRESSIONS
# ============================================================================

def section_aggregate_expressions(connection):
    print_title("26. Aggregate expressions in SELECT")

    print_concept(
        "Aggregates",
        """
Aggregate functions calculate values across multiple rows.

Common aggregate functions include:

COUNT()
SUM()
AVG()
MIN()
MAX()

Examples:

SELECT COUNT(*)
FROM employees;

SELECT AVG(salary)
FROM employees;

Aggregates change the nature of a query because many input rows may become
one output row.
""",
    )

    print_query(
        connection,
        """
        SELECT COUNT(*) AS employee_count
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            AVG(salary) AS average_salary,
            MIN(salary) AS minimum_salary,
            MAX(salary) AS maximum_salary,
            SUM(salary) AS total_salary
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            COUNT(email) AS employees_with_email,
            COUNT(*) AS all_employees
        FROM employees;
        """,
    )

    print_concept(
        "COUNT(*) versus COUNT(column)",
        """
COUNT(*) counts rows.

COUNT(column) counts non-NULL values in that column.

Therefore, if email is NULL for one employee, COUNT(email) will be smaller
than COUNT(*).
""",
    )


# ============================================================================
# 27. AGGREGATES AND GROUP BY
# ============================================================================

def section_group_by(connection):
    print_title("27. SELECT with GROUP BY")

    print_concept(
        "Grouping",
        """
GROUP BY divides rows into groups before aggregate calculations are
returned.

Example:

SELECT department_id, AVG(salary)
FROM employees
GROUP BY department_id;

The result contains one row per department_id.
""",
    )

    print_query(
        connection,
        """
        SELECT
            department_id,
            COUNT(*) AS employee_count,
            AVG(salary) AS average_salary
        FROM employees
        GROUP BY department_id;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            department_id,
            COUNT(*) AS employee_count,
            AVG(salary) AS average_salary
        FROM employees
        WHERE active = 1
        GROUP BY department_id
        ORDER BY average_salary DESC;
        """,
    )


# ============================================================================
# 28. HAVING VERSUS WHERE
# ============================================================================

def section_having(connection):
    print_title("28. WHERE versus HAVING")

    print_concept(
        "Filtering rows versus groups",
        """
WHERE filters individual input rows before grouping.

HAVING filters groups after aggregation.

Example:

WHERE salary > 50000

filters employees.

HAVING AVG(salary) > 80000

filters grouped departments based on their average salary.
""",
    )

    print_query(
        connection,
        """
        SELECT
            department_id,
            AVG(salary) AS average_salary
        FROM employees
        WHERE active = 1
        GROUP BY department_id
        HAVING AVG(salary) > 70000;
        """,
    )


# ============================================================================
# 29. SELECT WITH MULTIPLE EXPRESSIONS
# ============================================================================

def section_complex_select(connection):
    print_title("29. Multiple expressions in one SELECT")

    print_concept(
        "Building an analytical result",
        """
A SELECT list can contain ordinary columns, calculations, functions,
conditional expressions, and aliases at the same time.
""",
    )

    print_query(
        connection,
        """
        SELECT
            employee_id,
            first_name || ' ' || last_name AS full_name,
            job_title,
            salary,
            COALESCE(bonus, 0) AS bonus,
            salary + COALESCE(bonus, 0) AS total_compensation,
            CASE
                WHEN salary >= 100000 THEN 'Senior compensation'
                WHEN salary >= 70000 THEN 'Mid compensation'
                ELSE 'Entry compensation'
            END AS compensation_category
        FROM employees
        ORDER BY total_compensation DESC;
        """,
    )


# ============================================================================
# 30. REPEATING EXPRESSIONS
# ============================================================================

def section_expression_reuse(connection):
    print_title("30. Reusing calculated values")

    print_concept(
        "Aliases are result names, not universal variables",
        """
A SELECT alias should not be treated as a general-purpose variable.

For example, depending on the SQL dialect, this may not be valid:

SELECT salary * 12 AS annual_salary,
       annual_salary * 0.10 AS tax
FROM employees;

A common portable solution is to place the first calculation in a
subquery or common table expression and reference it from an outer query.

This is an important distinction between a result-column alias and a
programming-language variable.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            annual_salary,
            annual_salary * 0.10 AS estimated_tax
        FROM (
            SELECT
                first_name,
                salary * 12 AS annual_salary
            FROM employees
        ) AS calculated_employees;
        """,
    )


# ============================================================================
# 31. SUBQUERIES AND SELECT
# ============================================================================

def section_subqueries(connection):
    print_title("31. SELECT from a subquery")

    print_concept(
        "Subquery as a derived table",
        """
A SELECT statement can use another SELECT statement as its input.

The inner query produces a temporary result.
The outer query selects from that result.

This is useful when a calculated result needs to be reused.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            annual_salary
        FROM (
            SELECT
                first_name,
                salary * 12 AS annual_salary
            FROM employees
        ) AS employee_pay
        WHERE annual_salary > 1000000;
        """,
    )


# ============================================================================
# 32. COMMON TABLE EXPRESSIONS
# ============================================================================

def section_cte(connection):
    print_title("32. Common table expressions and SELECT")

    print_concept(
        "WITH clause",
        """
A common table expression, or CTE, gives a subquery a named temporary
result for the duration of one SQL statement.

Structure:

WITH name AS (
    SELECT ...
)
SELECT ...
FROM name;

CTEs can make complex SELECT statements easier to read and maintain.
""",
    )

    print_query(
        connection,
        """
        WITH employee_pay AS (
            SELECT
                employee_id,
                first_name,
                salary * 12 AS annual_salary
            FROM employees
        )
        SELECT
            employee_id,
            first_name,
            annual_salary
        FROM employee_pay
        WHERE annual_salary >= 1000000
        ORDER BY annual_salary DESC;
        """,
    )


# ============================================================================
# 33. SELECT EXECUTION ORDER
# ============================================================================

def section_logical_order(connection):
    print_title("33. Logical processing order")

    print_concept(
        "Logical order versus written order",
        """
SQL is written approximately as:

SELECT
FROM
WHERE
GROUP BY
HAVING
ORDER BY
LIMIT

But the database conceptually processes relational operations in a
different logical sequence.

A simplified model is:

1. FROM and JOIN identify the input rows.
2. WHERE filters input rows.
3. GROUP BY forms groups.
4. HAVING filters groups.
5. SELECT produces the requested expressions.
6. DISTINCT removes duplicate result rows when requested.
7. ORDER BY sorts the result.
8. LIMIT/OFFSET restrict the final result.

Actual database engines use query optimizers and may physically execute
operations in a different order while preserving the required result.
""",
    )

    print_query(
        connection,
        """
        SELECT
            department_id,
            AVG(salary) AS average_salary
        FROM employees
        WHERE active = 1
        GROUP BY department_id
        HAVING AVG(salary) > 70000
        ORDER BY average_salary DESC
        LIMIT 3;
        """,
    )


# ============================================================================
# 34. SELECT AND DISTINCT EDGE CASE
# ============================================================================

def section_distinct_edge_cases(connection):
    print_title("34. DISTINCT edge cases")

    print_concept(
        "DISTINCT applies to the complete selected row",
        """
Consider:

SELECT DISTINCT department_id, active
FROM employees;

The combination of department_id and active determines uniqueness.

DISTINCT does not independently deduplicate department_id and active.
""",
    )

    print_query(
        connection,
        """
        SELECT DISTINCT
            department_id,
            active
        FROM employees
        ORDER BY department_id, active;
        """,
    )


# ============================================================================
# 35. NULL FILTERING EDGE CASE
# ============================================================================

def section_null_filtering(connection):
    print_title("35. NULL comparisons")

    print_concept(
        "NULL requires IS NULL or IS NOT NULL",
        """
Do not test NULL with:

column = NULL

Use:

column IS NULL

or:

column IS NOT NULL

SQL uses three-valued logic involving TRUE, FALSE, and UNKNOWN. A normal
comparison with NULL produces UNKNOWN rather than ordinary TRUE or FALSE.
""",
    )

    print_query(
        connection,
        """
        SELECT employee_id, first_name, email
        FROM employees
        WHERE email IS NULL;
        """,
    )

    print_query(
        connection,
        """
        SELECT employee_id, first_name, email
        FROM employees
        WHERE email IS NOT NULL;
        """,
    )


# ============================================================================
# 36. DIVISION EDGE CASE
# ============================================================================

def section_arithmetic_edge_cases(connection):
    print_title("36. Arithmetic edge cases")

    print_concept(
        "Division",
        """
Arithmetic behavior can vary between SQL implementations, particularly
for integer division, decimal precision, and division by zero.

SQLite has its own type affinity and expression behavior.

When precise financial calculations are required, understand the numeric
types and arithmetic semantics of the specific database system being used.
""",
    )

    print_query(
        connection,
        """
        SELECT
            5 / 2 AS integer_style_division,
            5.0 / 2 AS decimal_style_division;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            100.0 / NULL AS division_by_null;
        """,
    )


# ============================================================================
# 37. TYPE CONVERSION
# ============================================================================

def section_cast(connection):
    print_title("37. CAST and result types")

    print_concept(
        "Explicit conversion",
        """
CAST converts a value to a requested SQL type.

Syntax:

CAST(expression AS type)

Explicit conversion makes an intended data transformation easier to
understand and can be important when expression types affect arithmetic.
""",
    )

    print_query(
        connection,
        """
        SELECT
            salary,
            CAST(salary AS INTEGER) AS integer_salary
        FROM employees;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            CAST('2026' AS INTEGER) AS converted_year,
            CAST('123.45' AS REAL) AS converted_amount;
        """,
    )


# ============================================================================
# 38. SELECT AND CASE WITH NULL
# ============================================================================

def section_case_null(connection):
    print_title("38. CASE and missing values")

    print_concept(
        "Explicit NULL classification",
        """
CASE can make missing information visible in the result.

This is often preferable to silently converting every missing value to
zero or an empty string.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            bonus,
            CASE
                WHEN bonus IS NULL THEN 'Bonus not recorded'
                WHEN bonus = 0 THEN 'No bonus'
                ELSE 'Bonus recorded'
            END AS bonus_status
        FROM employees;
        """,
    )


# ============================================================================
# 39. PRACTICAL REPORT QUERY
# ============================================================================

def section_practical_report(connection):
    print_title("39. Practical employee report")

    print_concept(
        "Combining fundamentals",
        """
This example combines:
- explicit columns;
- table aliases;
- string expressions;
- COALESCE;
- arithmetic;
- CASE;
- JOIN;
- WHERE;
- ORDER BY;
- aliases.

The goal is to demonstrate how SELECT becomes a reporting interface over
relational data.
""",
    )

    print_query(
        connection,
        """
        SELECT
            e.employee_id,
            e.first_name || ' ' || e.last_name AS employee_name,
            e.job_title,
            d.department_name,
            e.salary,
            COALESCE(e.bonus, 0) AS bonus,
            e.salary + COALESCE(e.bonus, 0) AS total_compensation,
            CASE
                WHEN e.salary >= 100000 THEN 'Senior'
                WHEN e.salary >= 70000 THEN 'Mid-level'
                ELSE 'Entry-level'
            END AS salary_category
        FROM employees AS e
        LEFT JOIN departments AS d
            ON e.department_id = d.department_id
        WHERE e.active = 1
        ORDER BY total_compensation DESC;
        """,
    )


# ============================================================================
# 40. PRACTICAL MANAGEMENT QUERY
# ============================================================================

def section_management_query(connection):
    print_title("40. Practical management query")

    print_query(
        connection,
        """
        SELECT
            d.department_name,
            COUNT(e.employee_id) AS employee_count,
            ROUND(AVG(e.salary), 2) AS average_salary,
            ROUND(MAX(e.salary), 2) AS highest_salary
        FROM departments AS d
        LEFT JOIN employees AS e
            ON d.department_id = e.department_id
        GROUP BY d.department_id, d.department_name
        ORDER BY average_salary DESC;
        """,
    )


# ============================================================================
# 41. PERFORMANCE CONSIDERATIONS
# ============================================================================

def section_performance(connection):
    print_title("41. SELECT performance considerations")

    print_concept(
        "Projection and unnecessary columns",
        """
Selecting only required columns can reduce the amount of data transferred
from the database to an application.

SELECT * may cause unnecessary I/O, network transfer, serialization, and
memory usage when a table has many columns.

Performance depends on the database engine, storage system, indexes,
statistics, query plan, data size, and workload. Therefore, SELECT * is
not automatically slow, but unnecessary projection can matter at scale.
""",
    )

    print_query(
        connection,
        """
        SELECT employee_id, first_name
        FROM employees;
        """,
    )

    print_concept(
        "Query plans",
        """
SQLite can expose its planned execution strategy through EXPLAIN QUERY
PLAN.

For example, this can help investigate whether a query scans a table or
uses an index.
""",
    )

    print_query(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT employee_id, first_name
        FROM employees
        WHERE department_id = 10;
        """,
    )


# ============================================================================
# 42. INDEX AND SELECT
# ============================================================================

def section_index(connection):
    print_title("42. Indexes and SELECT")

    print_concept(
        "Indexes",
        """
An index can help a database locate rows efficiently for suitable
predicates.

Indexes are generally created based on access patterns, not simply because
a column appears in SELECT.

For example, department_id is a common filtering or joining column in this
dataset.
""",
    )

    connection.execute(
        """
        CREATE INDEX idx_employees_department_id
        ON employees(department_id);
        """
    )
    connection.commit()

    print_query(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT employee_id, first_name
        FROM employees
        WHERE department_id = 10;
        """,
    )


# ============================================================================
# 43. SECURITY
# ============================================================================

def section_security(connection):
    print_title("43. Security considerations for SELECT")

    print_concept(
        "Avoid accidental data exposure",
        """
SELECT * can unintentionally expose columns that an application should not
send to users.

Explicit projection is a useful defensive practice:

SELECT employee_id, first_name, job_title
FROM employees;

rather than:

SELECT *
FROM employees;

Database permissions, views, row-level security, application authorization,
encryption, and auditing may also be necessary depending on the system.
""",
    )

    print_concept(
        "Parameterized queries",
        """
Values supplied by users should be passed as parameters rather than
constructed by string concatenation.

Unsafe application pattern:

sql = "SELECT ... WHERE first_name = '" + user_input + "'"

Safer pattern:

SELECT ...
WHERE first_name = ?

The Python sqlite3 API demonstrates parameter binding below.
""",
    )

    user_supplied_name = "Aarav"

    print_query(
        connection,
        """
        SELECT employee_id, first_name, job_title
        FROM employees
        WHERE first_name = ?;
        """,
        (user_supplied_name,),
    )


# ============================================================================
# 44. DEBUGGING SELECT STATEMENTS
# ============================================================================

def section_debugging(connection):
    print_title("44. Debugging SELECT queries")

    print_concept(
        "A systematic debugging approach",
        """
When a SELECT query produces an unexpected result:

1. Start with SELECT * FROM table LIMIT a small number.
2. Confirm the table and columns.
3. Select only the columns needed.
4. Add expressions one at a time.
5. Add WHERE conditions carefully.
6. Test NULL behavior explicitly.
7. Add JOIN clauses separately.
8. Add GROUP BY and aggregates only after row-level logic is correct.
9. Add ORDER BY and LIMIT at the end.
10. Compare row counts after each stage.

This isolates errors instead of debugging a large query as one indivisible
piece.
""",
    )

    print_query(
        connection,
        """
        SELECT *
        FROM employees
        LIMIT 3;
        """,
    )

    print_query(
        connection,
        """
        SELECT employee_id, first_name, salary
        FROM employees
        LIMIT 3;
        """,
    )

    print_query(
        connection,
        """
        SELECT employee_id, first_name, salary
        FROM employees
        WHERE salary >= 80000
        LIMIT 3;
        """,
    )


# ============================================================================
# 45. COMMON MISTAKES
# ============================================================================

def section_common_mistakes(connection):
    print_title("45. Common SELECT mistakes")

    print_concept(
        "Mistake: missing comma",
        """
This is invalid:

SELECT first_name last_name
FROM employees;

Depending on the dialect, it may be interpreted as an alias rather than
two columns. Explicit commas make the intended projection clear.
""",
    )

    print_query(
        connection,
        """
        SELECT first_name, last_name
        FROM employees;
        """,
    )

    print_concept(
        "Mistake: confusing column names with string values",
        """
This selects the column:

SELECT first_name
FROM employees;

This selects the literal text:

SELECT 'first_name'
FROM employees;

Quotes change the meaning.
""",
    )

    print_query(
        connection,
        """
        SELECT first_name
        FROM employees
        LIMIT 2;
        """,
    )

    print_query(
        connection,
        """
        SELECT 'first_name'
        FROM employees
        LIMIT 2;
        """,
    )

    print_concept(
        "Mistake: treating NULL as an ordinary value",
        """
Incorrect:

WHERE email = NULL

Correct:

WHERE email IS NULL
""",
    )

    print_concept(
        "Mistake: assuming row order",
        """
Without ORDER BY, do not depend on the database returning rows in a
particular order.

If order matters, specify it explicitly.
""",
    )

    print_query(
        connection,
        """
        SELECT employee_id, first_name
        FROM employees
        ORDER BY employee_id;
        """,
    )


# ============================================================================
# 46. SELECT * WITH JOINS
# ============================================================================

def section_star_with_join(connection):
    print_title("46. SELECT * with joins")

    print_concept(
        "Why SELECT * can become problematic with joins",
        """
SELECT * after a JOIN can return every column from every joined table.

If both tables contain similarly named columns, the output can become
difficult to consume and reason about.

Explicit selection is usually clearer.
""",
    )

    print_query(
        connection,
        """
        SELECT *
        FROM employees AS e
        JOIN departments AS d
            ON e.department_id = d.department_id
        LIMIT 3;
        """,
    )

    print_query(
        connection,
        """
        SELECT
            e.employee_id,
            e.first_name,
            e.job_title,
            d.department_name,
            d.location
        FROM employees AS e
        JOIN departments AS d
            ON e.department_id = d.department_id
        LIMIT 3;
        """,
    )


# ============================================================================
# 47. MULTIPLE SELECT EXPRESSIONS WITH FILTERS
# ============================================================================

def section_analytical_select(connection):
    print_title("47. Analytical SELECT example")

    print_query(
        connection,
        """
        SELECT
            employee_id,
            first_name || ' ' || last_name AS full_name,
            salary,
            ROUND(salary / 12.0, 2) AS monthly_salary,
            ROUND(COALESCE(bonus, 0) / 12.0, 2) AS monthly_bonus,
            ROUND(
                (salary + COALESCE(bonus, 0)) / 12.0,
                2
            ) AS monthly_total_compensation
        FROM employees
        WHERE active = 1
        ORDER BY monthly_total_compensation DESC;
        """,
    )


# ============================================================================
# 48. RESULT COLUMN NAMES
# ============================================================================

def section_result_metadata(connection):
    print_title("48. Inspecting SELECT result metadata")

    print_concept(
        "Result columns",
        """
Applications often need both the returned values and the names of result
columns.

Python's sqlite3 cursor.description exposes metadata about the SELECT
result.
""",
    )

    sql = """
        SELECT
            employee_id,
            first_name AS employee_name,
            salary * 12 AS annual_salary
        FROM employees
        LIMIT 2;
    """

    cursor = connection.execute(sql)

    print("\nSQL:")
    print(sql.strip())

    print("\nResult metadata:")
    for column in cursor.description:
        print(
            {
                "name": column[0],
                "type_code": column[1],
                "display_size": column[2],
                "internal_size": column[3],
                "precision": column[4],
                "scale": column[5],
                "null_ok": column[6],
            }
        )

    print("\nRows:")
    for row in cursor.fetchall():
        print(row)


# ============================================================================
# 49. TESTING SELECT QUERIES
# ============================================================================

def section_testing(connection):
    print_title("49. Testing SELECT behavior")

    print_concept(
        "Testing principles",
        """
A SELECT query should be tested against:
- ordinary rows;
- boundary values;
- NULL values;
- duplicate values;
- missing relationships;
- empty result sets;
- unexpected data types;
- ordering requirements.

Assertions can turn assumptions into executable checks.
""",
    )

    cursor = connection.execute(
        """
        SELECT COUNT(*)
        FROM employees;
        """
    )
    employee_count = cursor.fetchone()[0]

    assert employee_count == 9

    cursor = connection.execute(
        """
        SELECT COUNT(*)
        FROM employees
        WHERE email IS NULL;
        """
    )
    missing_email_count = cursor.fetchone()[0]

    assert missing_email_count == 1

    cursor = connection.execute(
        """
        SELECT COUNT(*)
        FROM employees
        WHERE department_id IS NULL;
        """
    )
    missing_department_count = cursor.fetchone()[0]

    assert missing_department_count == 1

    print("All SELECT assertions passed.")


# ============================================================================
# 50. EMPTY RESULT SETS
# ============================================================================

def section_empty_results(connection):
    print_title("50. Empty result sets")

    print_concept(
        "A valid SELECT can return zero rows",
        """
An empty result set is not necessarily an error.

For example, a filter can legitimately match no rows.
Applications should distinguish:
- SQL execution failure;
- successful query with zero rows.
""",
    )

    print_query(
        connection,
        """
        SELECT employee_id, first_name
        FROM employees
        WHERE salary > 1000000;
        """,
    )


# ============================================================================
# 51. ERROR HANDLING
# ============================================================================

def section_error_handling(connection):
    print_title("51. SELECT error handling")

    print_concept(
        "Typical SQL errors",
        """
SELECT statements can fail because of:
- misspelled table names;
- misspelled column names;
- invalid syntax;
- ambiguous references;
- unsupported functions;
- incompatible expressions;
- permission problems in production systems.

The Python example catches sqlite3.Error so the failure can be inspected
without terminating the entire study script.
""",
    )

    try:
        connection.execute(
            """
            SELECT nonexistent_column
            FROM employees;
            """
        )
    except sqlite3.Error as error:
        print("Caught SQL error:", error)


# ============================================================================
# 52. TRANSACTIONS AND SELECT
# ============================================================================

def section_transactions(connection):
    print_title("52. SELECT and transaction awareness")

    print_concept(
        "SELECT inside transactions",
        """
A SELECT can execute within a transaction.

The exact visibility rules depend on the database's transaction and
isolation model. In production systems, understanding transaction
isolation is important when a SELECT is expected to observe a consistent
snapshot while other transactions modify data.
""",
    )

    print_query(
        connection,
        """
        SELECT COUNT(*) AS employee_count
        FROM employees;
        """,
    )


# ============================================================================
# 53. READABILITY
# ============================================================================

def section_readability(connection):
    print_title("53. SELECT readability and style")

    print_concept(
        "Readable SQL",
        """
Useful practices include:
- one logical expression per line;
- consistent indentation;
- explicit column lists;
- descriptive aliases;
- table aliases for multi-table queries;
- qualification when ambiguity is possible;
- meaningful ordering;
- avoiding unnecessary SELECT * in application-facing queries;
- keeping business calculations understandable.

Readable SQL is easier to test, review, debug, and maintain.
""",
    )

    print_query(
        connection,
        """
        SELECT
            e.employee_id,
            e.first_name || ' ' || e.last_name AS full_name,
            d.department_name,
            e.salary,
            COALESCE(e.bonus, 0) AS bonus,
            e.salary + COALESCE(e.bonus, 0) AS total_compensation
        FROM employees AS e
        LEFT JOIN departments AS d
            ON e.department_id = d.department_id
        WHERE e.active = 1
        ORDER BY total_compensation DESC, full_name ASC;
        """,
    )


# ============================================================================
# 54. SELECT AS A DATA PRESENTATION LAYER
# ============================================================================

def section_presentation_layer(connection):
    print_title("54. SELECT as a data presentation layer")

    print_concept(
        "Transforming stored data without changing it",
        """
SELECT can create a presentation-oriented result without modifying the
underlying records.

For example:
- stored first_name and last_name become full_name;
- salary becomes annual_salary;
- NULL bonus becomes a business-friendly display value;
- numeric salary becomes a category;
- internal IDs can be excluded from a user-facing result.

SELECT is therefore central to reporting, analytics, APIs, dashboards,
exports, and database-driven applications.
""",
    )

    print_query(
        connection,
        """
        SELECT
            e.first_name || ' ' || e.last_name AS employee_name,
            d.department_name AS department,
            e.job_title AS role,
            ROUND(e.salary, 2) AS base_salary
        FROM employees AS e
        LEFT JOIN departments AS d
            ON e.department_id = d.department_id
        WHERE e.active = 1
        ORDER BY employee_name;
        """,
    )


# ============================================================================
# 55. COMPARISON OF COMMON SELECT PATTERNS
# ============================================================================

def section_comparisons(connection):
    print_title("55. Common SELECT patterns compared")

    print_concept(
        "Explicit columns versus SELECT *",
        """
SELECT *
    useful for exploration and quick inspection.

SELECT employee_id, first_name, salary
    useful when the exact output contract matters.

Explicit columns generally provide stronger control over output shape.
""",
    )

    print_concept(
        "Stored value versus calculated value",
        """
salary
    returns the stored salary.

salary * 12 AS annual_salary
    calculates a new value without changing salary.

A SELECT expression does not update the source row.
""",
    )

    print_concept(
        "Column name versus literal",
        """
first_name
    refers to a column.

'first_name'
    refers to a text literal containing the characters first_name.
""",
    )

    print_concept(
        "WHERE versus SELECT",
        """
WHERE controls which rows qualify.

SELECT controls which values appear in the result.

They solve different problems and are frequently used together.
""",
    )

    print_query(
        connection,
        """
        SELECT
            first_name,
            salary * 12 AS annual_salary
        FROM employees
        WHERE salary >= 80000
        ORDER BY annual_salary DESC;
        """,
    )


# ============================================================================
# 56. MINI EXERCISES
# ============================================================================

def section_exercises(connection):
    print_title("56. Executable practice exercises")

    print_concept(
        "Exercise 1",
        "Select employee first names and last names.",
    )
    print_query(
        connection,
        """
        SELECT first_name, last_name
        FROM employees;
        """,
    )

    print_concept(
        "Exercise 2",
        "Select employees with salary and calculated annual salary.",
    )
    print_query(
        connection,
        """
        SELECT
            first_name,
            salary,
            salary * 12 AS annual_salary
        FROM employees;
        """,
    )

    print_concept(
        "Exercise 3",
        "Create a full name using string concatenation.",
    )
    print_query(
        connection,
        """
        SELECT
            first_name || ' ' || last_name AS full_name
        FROM employees;
        """,
    )

    print_concept(
        "Exercise 4",
        "Show a compensation value that treats missing bonuses as zero.",
    )
    print_query(
        connection,
        """
        SELECT
            first_name,
            salary + COALESCE(bonus, 0) AS total_compensation
        FROM employees;
        """,
    )

    print_concept(
        "Exercise 5",
        "Display the three highest salaries.",
    )
    print_query(
        connection,
        """
        SELECT
            first_name,
            salary
        FROM employees
        ORDER BY salary DESC
        LIMIT 3;
        """,
    )

    print_concept(
        "Exercise 6",
        "Show the average salary by department.",
    )
    print_query(
        connection,
        """
        SELECT
            department_id,
            ROUND(AVG(salary), 2) AS average_salary
        FROM employees
        GROUP BY department_id;
        """,
    )


# ============================================================================
# 57. COMPLETE SELECT EXAMPLE
# ============================================================================

def section_complete_example(connection):
    print_title("57. Complete SELECT example")

    print_concept(
        "Integrated query",
        """
The following query combines the major SELECT fundamentals into one
practical result.

It demonstrates:
- qualified columns;
- string expressions;
- aliases;
- COALESCE;
- arithmetic;
- CASE;
- JOIN;
- WHERE;
- ORDER BY.
""",
    )

    sql = """
        SELECT
            e.employee_id,
            e.first_name || ' ' || e.last_name AS full_name,
            d.department_name AS department,
            e.job_title AS role,
            e.salary AS base_salary,
            COALESCE(e.bonus, 0) AS bonus,
            e.salary + COALESCE(e.bonus, 0) AS total_compensation,
            CASE
                WHEN e.salary >= 100000 THEN 'High'
                WHEN e.salary >= 70000 THEN 'Medium'
                ELSE 'Standard'
            END AS salary_band,
            strftime('%Y', e.hire_date) AS hire_year
        FROM employees AS e
        LEFT JOIN departments AS d
            ON e.department_id = d.department_id
        WHERE e.active = 1
        ORDER BY total_compensation DESC, full_name ASC;
    """

    print_query(connection, sql)


# ============================================================================
# 58. FINAL CONCEPT CHECKS
# ============================================================================

def section_concept_checks(connection):
    print_title("58. Final concept checks")

    checks = [
        (
            "Selecting one column",
            """
            SELECT first_name
            FROM employees
            LIMIT 1;
            """,
        ),
        (
            "Selecting multiple columns",
            """
            SELECT first_name, salary
            FROM employees
            LIMIT 1;
            """,
        ),
        (
            "Selecting all columns",
            """
            SELECT *
            FROM employees
            LIMIT 1;
            """,
        ),
        (
            "Using an expression",
            """
            SELECT salary * 12 AS annual_salary
            FROM employees
            LIMIT 1;
            """,
        ),
        (
            "Using an alias",
            """
            SELECT first_name AS employee_name
            FROM employees
            LIMIT 1;
            """,
        ),
        (
            "Handling NULL",
            """
            SELECT COALESCE(bonus, 0) AS safe_bonus
            FROM employees
            LIMIT 1;
            """,
        ),
        (
            "Filtering rows",
            """
            SELECT first_name
            FROM employees
            WHERE salary > 80000;
            """,
        ),
        (
            "Sorting",
            """
            SELECT first_name, salary
            FROM employees
            ORDER BY salary DESC
            LIMIT 1;
            """,
        ),
        (
            "Aggregating",
            """
            SELECT COUNT(*) AS employee_count
            FROM employees;
            """,
        ),
    ]

    for concept, sql in checks:
        print(f"\nConcept check: {concept}")
        cursor = connection.execute(sql)
        print("Result:", cursor.fetchall())

    print(
        """
Core SELECT principles demonstrated:

1. SELECT defines the result columns.
2. FROM identifies the source.
3. A SELECT list can contain columns, literals, functions, and expressions.
4. Multiple columns are separated by commas.
5. SELECT * requests all columns from the source.
6. Aliases rename result columns without changing the stored schema.
7. Expressions can calculate values without modifying data.
8. NULL requires explicit handling.
9. WHERE filters rows.
10. ORDER BY controls result order.
11. LIMIT and OFFSET restrict result rows.
12. DISTINCT removes duplicate result rows.
13. JOIN allows SELECT to combine information from related tables.
14. Aggregates summarize rows.
15. GROUP BY produces grouped aggregate results.
16. Qualified names prevent ambiguity.
17. Explicit projection improves clarity and can reduce unnecessary data transfer.
18. Parameterized queries help prevent SQL injection in application code.
19. Query plans help investigate performance.
20. SELECT is primarily a read operation and does not itself modify stored rows.
"""
    )


# ============================================================================
# 59. MAIN PROGRAM
# ============================================================================

def main():
    """Run the complete SELECT fundamentals study program."""
    connection = create_connection()

    try:
        create_schema(connection)
        insert_sample_data(connection)

        section_select_basics(connection)
        section_single_column(connection)
        section_multiple_columns(connection)
        section_select_star(connection)
        section_literals(connection)
        section_expressions(connection)
        section_arithmetic(connection)
        section_null_behavior(connection)
        section_aliases(connection)
        section_alias_naming(connection)
        section_distinct(connection)
        section_where_relationship(connection)
        section_order_by(connection)
        section_order_by_alias(connection)
        section_limit_offset(connection)
        section_string_expressions(connection)
        section_case(connection)
        section_date_expressions(connection)
        section_boolean_expressions(connection)
        section_qualified_columns(connection)
        section_table_aliases(connection)
        section_joined_select(connection)
        section_ambiguity(connection)
        section_aggregate_expressions(connection)
        section_group_by(connection)
        section_having(connection)
        section_complex_select(connection)
        section_expression_reuse(connection)
        section_subqueries(connection)
        section_cte(connection)
        section_logical_order(connection)
        section_distinct_edge_cases(connection)
        section_null_filtering(connection)
        section_arithmetic_edge_cases(connection)
        section_cast(connection)
        section_case_null(connection)
        section_practical_report(connection)
        section_management_query(connection)
        section_performance(connection)
        section_index(connection)
        section_security(connection)
        section_debugging(connection)
        section_common_mistakes(connection)
        section_star_with_join(connection)
        section_analytical_select(connection)
        section_result_metadata(connection)
        section_testing(connection)
        section_empty_results(connection)
        section_error_handling(connection)
        section_transactions(connection)
        section_readability(connection)
        section_presentation_layer(connection)
        section_comparisons(connection)
        section_exercises(connection)
        section_complete_example(connection)
        section_concept_checks(connection)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
