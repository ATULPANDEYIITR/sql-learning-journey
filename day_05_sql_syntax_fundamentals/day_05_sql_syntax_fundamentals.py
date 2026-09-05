"""
SQL Syntax Fundamentals
=======================

A self-contained Python study file for learning SQL syntax from absolute
beginner through advanced syntax patterns.

The examples use Python's built-in sqlite3 module so that SQL statements
can be executed without installing an external database package.

Covered:
- SQL statements, keywords, identifiers, literals, comments
- Semicolons and statement boundaries
- Case sensitivity
- DDL, DML, DQL, DCL/TCL concepts
- CREATE, ALTER, DROP, INSERT, SELECT, UPDATE, DELETE
- WHERE, ORDER BY, GROUP BY, HAVING
- DISTINCT, aliases, expressions, operators
- NULL and three-valued logic
- JOIN syntax
- Subqueries and common table expressions
- Set operations
- CASE expressions
- Aggregate and scalar functions
- Constraints
- Views
- Transactions
- Parameterized SQL and SQL injection prevention
- Quoting and identifier rules
- SQLite-specific syntax differences
- Edge cases, common mistakes, debugging, performance, and production concerns
"""

import sqlite3
from pprint import pprint


# =============================================================================
# 1. DATABASE SETUP
# =============================================================================

def create_connection():
    """Create an in-memory SQLite database."""
    return sqlite3.connect(":memory:")


connection = create_connection()
connection.row_factory = sqlite3.Row
cursor = connection.cursor()


# =============================================================================
# 2. SQL FUNDAMENTALS
# =============================================================================

"""
A SQL statement is an instruction sent to a database.

Common categories:

DDL - Data Definition Language
    CREATE, ALTER, DROP

DML - Data Manipulation Language
    INSERT, UPDATE, DELETE

DQL - Data Query Language
    SELECT

TCL - Transaction Control Language
    BEGIN, COMMIT, ROLLBACK

DCL - Data Control Language
    GRANT, REVOKE

SQLite does not implement every SQL feature from these categories.
For example, GRANT and REVOKE are not SQLite commands.

SQL keywords are normally written in uppercase for readability:

    SELECT
    FROM
    WHERE

SQL itself is generally case-insensitive for keywords:

    SELECT * FROM employees;
    select * from employees;

These have the same meaning in SQLite.

Identifiers are names of database objects:

    employees
    employee_id
    salary

String literals use single quotes:

    'Alice'

Numeric literals do not require quotes:

    100
    3.14

Double quotes are generally used for identifiers:

    "employee_name"

Backticks may also be accepted by some database systems, including SQLite,
but portability is better when standard SQL quoting conventions are used.

A semicolon marks the end of a SQL statement. It is especially important
when multiple statements are supplied as one script.
"""


# =============================================================================
# 3. COMMENTS
# =============================================================================

# SQL single-line comments begin with two hyphens.
cursor.execute("""
    -- This is a SQL comment.
    SELECT 1;
""")

cursor.execute("""
    /*
       This is a SQL block comment.
       It can span multiple lines.
    */
    SELECT 2;
""")


# =============================================================================
# 4. CREATE TABLE
# =============================================================================

cursor.executescript("""
CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department_id INTEGER,
    salary REAL NOT NULL CHECK (salary >= 0),
    hire_date TEXT,
    email TEXT UNIQUE,
    manager_id INTEGER,
    FOREIGN KEY (department_id)
        REFERENCES departments(department_id),
    FOREIGN KEY (manager_id)
        REFERENCES employees(employee_id)
);
""")


# =============================================================================
# 5. INSERT SYNTAX
# =============================================================================

"""
Basic INSERT syntax:

INSERT INTO table_name (column1, column2)
VALUES (value1, value2);

Explicitly naming columns is preferable because it makes the statement
clearer and protects against changes in table column order.
"""

cursor.execute("""
    INSERT INTO departments (department_id, department_name)
    VALUES (?, ?);
""", (1, "Engineering"))

cursor.execute("""
    INSERT INTO departments (department_id, department_name)
    VALUES (?, ?);
""", (2, "Finance"))

cursor.execute("""
    INSERT INTO departments (department_id, department_name)
    VALUES (?, ?);
""", (3, "Human Resources"))


employees = [
    (1, "Alice", 1, 95000, "2021-04-12", "alice@example.com", None),
    (2, "Bob", 1, 72000, "2022-07-18", "bob@example.com", 1),
    (3, "Carol", 2, 88000, "2020-01-10", "carol@example.com", None),
    (4, "David", 2, 64000, "2023-03-22", "david@example.com", 3),
    (5, "Eva", 3, 70000, "2024-06-01", "eva@example.com", None),
    (6, "Frank", None, 55000, "2025-02-14", "frank@example.com", None),
]

cursor.executemany("""
    INSERT INTO employees (
        employee_id,
        employee_name,
        department_id,
        salary,
        hire_date,
        email,
        manager_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?);
""", employees)

connection.commit()


# =============================================================================
# 6. SELECT BASICS
# =============================================================================

def print_rows(rows):
    """Print sqlite3.Row objects in a readable form."""
    for row in rows:
        print(dict(row))


rows = cursor.execute("""
    SELECT *
    FROM employees;
""").fetchall()

print("All employees:")
print_rows(rows)


rows = cursor.execute("""
    SELECT employee_id, employee_name, salary
    FROM employees;
""").fetchall()

print("\nSelected columns:")
print_rows(rows)


# =============================================================================
# 7. DISTINCT
# =============================================================================

rows = cursor.execute("""
    SELECT DISTINCT department_id
    FROM employees;
""").fetchall()

print("\nDistinct department IDs:")
print_rows(rows)


# =============================================================================
# 8. ALIASES
# =============================================================================

"""
Aliases temporarily rename a table or column in a query.

AS is normally used for clarity:

SELECT salary AS annual_salary
FROM employees;

The AS keyword is optional for many column aliases, but explicit AS improves
readability.
"""

rows = cursor.execute("""
    SELECT
        employee_name AS name,
        salary AS annual_salary
    FROM employees;
""").fetchall()

print("\nColumn aliases:")
print_rows(rows)


# =============================================================================
# 9. EXPRESSIONS AND ARITHMETIC
# =============================================================================

rows = cursor.execute("""
    SELECT
        employee_name,
        salary,
        salary * 12 AS estimated_annual_pay
    FROM employees;
""").fetchall()

print("\nArithmetic expressions:")
print_rows(rows)


# =============================================================================
# 10. WHERE
# =============================================================================

"""
WHERE filters rows before grouping and aggregation.

Common comparison operators:

=
<>
!=
<
>
<=
>=

Logical operators:

AND
OR
NOT

Membership:

IN
NOT IN

Range:

BETWEEN
NOT BETWEEN

Pattern matching:

LIKE
NOT LIKE
"""


rows = cursor.execute("""
    SELECT employee_name, salary
    FROM employees
    WHERE salary >= 70000;
""").fetchall()

print("\nSalary >= 70000:")
print_rows(rows)


rows = cursor.execute("""
    SELECT employee_name, salary
    FROM employees
    WHERE salary >= 70000
      AND salary < 90000;
""").fetchall()

print("\nSalary between 70000 and 89999:")
print_rows(rows)


rows = cursor.execute("""
    SELECT employee_name, department_id
    FROM employees
    WHERE department_id IN (1, 2);
""").fetchall()

print("\nEmployees in departments 1 or 2:")
print_rows(rows)


rows = cursor.execute("""
    SELECT employee_name
    FROM employees
    WHERE employee_name LIKE 'A%';
""").fetchall()

print("\nNames beginning with A:")
print_rows(rows)


# =============================================================================
# 11. NULL
# =============================================================================

"""
NULL means missing, unknown, or not applicable data.

NULL is not the same as:
    0
    ''
    False

Incorrect:

    WHERE department_id = NULL

Correct:

    WHERE department_id IS NULL

Likewise:

    WHERE department_id IS NOT NULL
"""

rows = cursor.execute("""
    SELECT employee_name
    FROM employees
    WHERE department_id IS NULL;
""").fetchall()

print("\nEmployees without a department:")
print_rows(rows)


# =============================================================================
# 12. THREE-VALUED LOGIC
# =============================================================================

"""
SQL logical expressions can evaluate to:

TRUE
FALSE
UNKNOWN

Comparisons involving NULL usually produce UNKNOWN.

For example:

    salary = NULL

does not evaluate to TRUE.

This is why IS NULL and IS NOT NULL are required.

NOT UNKNOWN remains UNKNOWN.

This behavior is one reason NULL handling requires special attention.
"""


# =============================================================================
# 13. ORDER BY
# =============================================================================

rows = cursor.execute("""
    SELECT employee_name, salary
    FROM employees
    ORDER BY salary ASC;
""").fetchall()

print("\nAscending salary:")
print_rows(rows)


rows = cursor.execute("""
    SELECT employee_name, salary
    FROM employees
    ORDER BY salary DESC;
""").fetchall()

print("\nDescending salary:")
print_rows(rows)


rows = cursor.execute("""
    SELECT employee_name, department_id, salary
    FROM employees
    ORDER BY department_id ASC, salary DESC;
""").fetchall()

print("\nMultiple ordering expressions:")
print_rows(rows)


# =============================================================================
# 14. LIMIT AND OFFSET
# =============================================================================

rows = cursor.execute("""
    SELECT employee_name, salary
    FROM employees
    ORDER BY salary DESC
    LIMIT 3;
""").fetchall()

print("\nTop three salaries:")
print_rows(rows)


rows = cursor.execute("""
    SELECT employee_name, salary
    FROM employees
    ORDER BY salary DESC
    LIMIT 3 OFFSET 2;
""").fetchall()

print("\nThree rows after skipping two:")
print_rows(rows)


# =============================================================================
# 15. AGGREGATE FUNCTIONS
# =============================================================================

"""
Aggregate functions process multiple rows and produce a result:

COUNT
SUM
AVG
MIN
MAX

COUNT(*) counts rows.

COUNT(column) counts non-NULL values in that column.
"""

rows = cursor.execute("""
    SELECT
        COUNT(*) AS employee_count,
        SUM(salary) AS total_salary,
        AVG(salary) AS average_salary,
        MIN(salary) AS minimum_salary,
        MAX(salary) AS maximum_salary
    FROM employees;
""").fetchall()

print("\nAggregate functions:")
print_rows(rows)


# =============================================================================
# 16. GROUP BY
# =============================================================================

rows = cursor.execute("""
    SELECT
        department_id,
        COUNT(*) AS employee_count,
        AVG(salary) AS average_salary
    FROM employees
    GROUP BY department_id;
""").fetchall()

print("\nGrouping by department:")
print_rows(rows)


# =============================================================================
# 17. HAVING
# =============================================================================

"""
WHERE filters individual rows.

HAVING filters groups after GROUP BY.

Example:

WHERE salary > 60000

filters employees.

HAVING AVG(salary) > 70000

filters departments based on their average salary.
"""

rows = cursor.execute("""
    SELECT
        department_id,
        COUNT(*) AS employee_count,
        AVG(salary) AS average_salary
    FROM employees
    GROUP BY department_id
    HAVING AVG(salary) > 70000;
""").fetchall()

print("\nDepartments with average salary above 70000:")
print_rows(rows)


# =============================================================================
# 18. SQL QUERY LOGICAL ORDER
# =============================================================================

"""
Although SQL is written approximately as:

SELECT
FROM
WHERE
GROUP BY
HAVING
ORDER BY
LIMIT

the conceptual logical processing order is approximately:

FROM
WHERE
GROUP BY
HAVING
SELECT
DISTINCT
ORDER BY
LIMIT

This explains why an alias created in SELECT is not universally available
in WHERE. SQL dialects have special cases, so portable SQL should not rely
on SELECT aliases inside WHERE.
"""


# =============================================================================
# 19. STRING FUNCTIONS
# =============================================================================

rows = cursor.execute("""
    SELECT
        employee_name,
        UPPER(employee_name) AS uppercase_name,
        LOWER(employee_name) AS lowercase_name,
        LENGTH(employee_name) AS name_length
    FROM employees;
""").fetchall()

print("\nString functions:")
print_rows(rows)


# =============================================================================
# 20. COALESCE
# =============================================================================

"""
COALESCE returns the first non-NULL expression.

COALESCE(department_id, 0)

means:
    use department_id when it exists;
    otherwise use 0.
"""

rows = cursor.execute("""
    SELECT
        employee_name,
        COALESCE(department_id, 0) AS department_id_or_zero
    FROM employees;
""").fetchall()

print("\nCOALESCE:")
print_rows(rows)


# =============================================================================
# 21. CASE EXPRESSIONS
# =============================================================================

rows = cursor.execute("""
    SELECT
        employee_name,
        salary,
        CASE
            WHEN salary >= 90000 THEN 'High'
            WHEN salary >= 70000 THEN 'Medium'
            ELSE 'Low'
        END AS salary_band
    FROM employees;
""").fetchall()

print("\nCASE expression:")
print_rows(rows)


# =============================================================================
# 22. INNER JOIN
# =============================================================================

"""
JOIN combines rows from multiple tables.

INNER JOIN returns rows where the join condition matches.
"""

rows = cursor.execute("""
    SELECT
        e.employee_name,
        d.department_name
    FROM employees AS e
    INNER JOIN departments AS d
        ON e.department_id = d.department_id;
""").fetchall()

print("\nINNER JOIN:")
print_rows(rows)


# =============================================================================
# 23. LEFT JOIN
# =============================================================================

"""
LEFT JOIN preserves every row from the left table.

If no matching row exists in the right table, right-side columns become NULL.
"""

rows = cursor.execute("""
    SELECT
        e.employee_name,
        d.department_name
    FROM employees AS e
    LEFT JOIN departments AS d
        ON e.department_id = d.department_id;
""").fetchall()

print("\nLEFT JOIN:")
print_rows(rows)


# =============================================================================
# 24. SELF JOIN
# =============================================================================

"""
A self join joins a table to itself.

The employees table contains manager_id, which points to another employee.
"""

rows = cursor.execute("""
    SELECT
        employee.employee_name AS employee,
        manager.employee_name AS manager
    FROM employees AS employee
    LEFT JOIN employees AS manager
        ON employee.manager_id = manager.employee_id;
""").fetchall()

print("\nSELF JOIN:")
print_rows(rows)


# =============================================================================
# 25. CROSS JOIN
# =============================================================================

"""
CROSS JOIN produces the Cartesian product.

If table A has m rows and table B has n rows,
the result can contain m * n rows.

Use it deliberately because accidental Cartesian products can be enormous.
"""

rows = cursor.execute("""
    SELECT
        e.employee_name,
        d.department_name
    FROM employees AS e
    CROSS JOIN departments AS d
    LIMIT 5;
""").fetchall()

print("\nCROSS JOIN sample:")
print_rows(rows)


# =============================================================================
# 26. SUBQUERIES
# =============================================================================

"""
A subquery is a query nested inside another SQL statement.

Scalar subquery:
    returns one value.

Set subquery:
    can return multiple rows.

Correlated subquery:
    refers to columns from the outer query.
"""

rows = cursor.execute("""
    SELECT employee_name, salary
    FROM employees
    WHERE salary > (
        SELECT AVG(salary)
        FROM employees
    );
""").fetchall()

print("\nEmployees above average salary:")
print_rows(rows)


# =============================================================================
# 27. EXISTS
# =============================================================================

rows = cursor.execute("""
    SELECT d.department_name
    FROM departments AS d
    WHERE EXISTS (
        SELECT 1
        FROM employees AS e
        WHERE e.department_id = d.department_id
    );
""").fetchall()

print("\nDepartments with employees:")
print_rows(rows)


# =============================================================================
# 28. NOT EXISTS
# =============================================================================

rows = cursor.execute("""
    SELECT d.department_name
    FROM departments AS d
    WHERE NOT EXISTS (
        SELECT 1
        FROM employees AS e
        WHERE e.department_id = d.department_id
    );
""").fetchall()

print("\nDepartments without employees:")
print_rows(rows)


# =============================================================================
# 29. COMMON TABLE EXPRESSIONS
# =============================================================================

"""
A Common Table Expression (CTE) uses WITH.

Basic form:

WITH name AS (
    SELECT ...
)
SELECT ...
FROM name;

CTEs improve readability for complex queries.
"""

rows = cursor.execute("""
    WITH department_stats AS (
        SELECT
            department_id,
            COUNT(*) AS employee_count,
            AVG(salary) AS average_salary
        FROM employees
        GROUP BY department_id
    )
    SELECT *
    FROM department_stats
    WHERE average_salary > 70000;
""").fetchall()

print("\nCTE:")
print_rows(rows)


# =============================================================================
# 30. MULTIPLE CTEs
# =============================================================================

rows = cursor.execute("""
    WITH
    department_stats AS (
        SELECT
            department_id,
            AVG(salary) AS average_salary
        FROM employees
        GROUP BY department_id
    ),
    high_value_departments AS (
        SELECT department_id
        FROM department_stats
        WHERE average_salary > 70000
    )
    SELECT
        e.employee_name,
        e.salary
    FROM employees AS e
    WHERE e.department_id IN (
        SELECT department_id
        FROM high_value_departments
    );
""").fetchall()

print("\nMultiple CTEs:")
print_rows(rows)


# =============================================================================
# 31. SET OPERATIONS
# =============================================================================

"""
UNION combines results and removes duplicate rows.

UNION ALL combines results while preserving duplicates.

INTERSECT returns rows common to both queries.

EXCEPT returns rows from the first query that are absent from the second.

Corresponding SELECT statements must have compatible column counts and types.
"""

rows = cursor.execute("""
    SELECT employee_name
    FROM employees
    WHERE salary >= 90000

    UNION

    SELECT employee_name
    FROM employees
    WHERE department_id = 2;
""").fetchall()

print("\nUNION:")
print_rows(rows)


rows = cursor.execute("""
    SELECT employee_name
    FROM employees
    WHERE department_id = 1

    UNION ALL

    SELECT employee_name
    FROM employees
    WHERE department_id = 1;
""").fetchall()

print("\nUNION ALL:")
print_rows(rows)


# =============================================================================
# 32. INSERT FROM SELECT
# =============================================================================

cursor.execute("""
    CREATE TABLE employee_archive (
        employee_id INTEGER,
        employee_name TEXT,
        salary REAL
    );
""")

cursor.execute("""
    INSERT INTO employee_archive (
        employee_id,
        employee_name,
        salary
    )
    SELECT
        employee_id,
        employee_name,
        salary
    FROM employees
    WHERE salary >= 85000;
""")

print("\nINSERT INTO ... SELECT:")
print_rows(cursor.execute("""
    SELECT *
    FROM employee_archive;
""").fetchall())


# =============================================================================
# 33. UPDATE
# =============================================================================

cursor.execute("""
    UPDATE employees
    SET salary = salary * 1.05
    WHERE department_id = 1;
""")

connection.commit()

print("\nAfter UPDATE:")
print_rows(cursor.execute("""
    SELECT employee_name, salary
    FROM employees
    WHERE department_id = 1;
""").fetchall())


# =============================================================================
# 34. UPDATE WITH MULTIPLE COLUMNS
# =============================================================================

cursor.execute("""
    UPDATE employees
    SET
        salary = salary + 1000,
        email = LOWER(email)
    WHERE employee_id = 2;
""")

connection.commit()


# =============================================================================
# 35. DELETE
# =============================================================================

"""
DELETE removes rows.

Always verify the WHERE condition before executing a production DELETE.

Without WHERE:

    DELETE FROM employees;

all rows are removed.
"""

cursor.execute("""
    DELETE FROM employees
    WHERE employee_id = 6;
""")

connection.commit()

print("\nAfter DELETE:")
print_rows(cursor.execute("""
    SELECT employee_id, employee_name
    FROM employees;
""").fetchall())


# =============================================================================
# 36. ALTER TABLE
# =============================================================================

cursor.execute("""
    ALTER TABLE employees
    ADD COLUMN employment_status TEXT DEFAULT 'Active';
""")

print("\nAfter ALTER TABLE:")
print_rows(cursor.execute("""
    PRAGMA table_info(employees);
""").fetchall())


# =============================================================================
# 37. CONSTRAINTS
# =============================================================================

"""
Important constraints:

PRIMARY KEY
    Uniquely identifies rows.

FOREIGN KEY
    Establishes a relationship with another table.

NOT NULL
    Prevents NULL values.

UNIQUE
    Prevents duplicate values.

CHECK
    Requires a Boolean condition to be satisfied.

DEFAULT
    Supplies a value when one is not explicitly provided.

Constraints are part of data integrity. Application validation alone is
not a substitute for appropriate database constraints.
"""


# =============================================================================
# 38. TRANSACTIONS
# =============================================================================

"""
A transaction groups operations into a unit of work.

Typical operations:

BEGIN
COMMIT
ROLLBACK

ACID describes important transactional properties:

Atomicity
    All-or-nothing behavior.

Consistency
    Valid database state before and after the transaction.

Isolation
    Concurrent transactions should not improperly interfere.

Durability
    Committed changes survive appropriate failures.

SQLite starts transactions automatically in many circumstances through its
Python driver. Explicit transaction control is useful when a sequence of
operations must succeed or fail together.
"""

try:
    connection.execute("BEGIN")

    connection.execute("""
        UPDATE employees
        SET salary = salary + 500
        WHERE employee_id = 1;
    """)

    connection.execute("""
        UPDATE employees
        SET salary = salary + 500
        WHERE employee_id = 2;
    """)

    connection.commit()
except sqlite3.Error:
    connection.rollback()
    raise


# Demonstrate rollback.
try:
    connection.execute("BEGIN")

    connection.execute("""
        UPDATE employees
        SET salary = salary + 100000
        WHERE employee_id = 1;
    """)

    raise RuntimeError("Simulated application failure")

except RuntimeError:
    connection.rollback()


# =============================================================================
# 39. PARAMETERIZED QUERIES
# =============================================================================

"""
Never construct SQL by concatenating untrusted user input.

Unsafe concept:

    "SELECT ... WHERE employee_name = '" + user_input + "'"

A malicious value can change the structure of the SQL statement.

Parameterized queries keep data separate from SQL syntax.

SQLite uses ? placeholders for positional parameters.
"""

employee_name = "Alice"

rows = cursor.execute("""
    SELECT employee_id, employee_name, salary
    FROM employees
    WHERE employee_name = ?;
""", (employee_name,)).fetchall()

print("\nParameterized query:")
print_rows(rows)


# Named parameters are also possible in SQLite.
department_id = 1

rows = cursor.execute("""
    SELECT employee_name, salary
    FROM employees
    WHERE department_id = :department_id;
""", {"department_id": department_id}).fetchall()

print("\nNamed parameter:")
print_rows(rows)


# =============================================================================
# 40. SQL INJECTION DEMONSTRATION
# =============================================================================

"""
The following demonstrates the conceptual difference between unsafe
string construction and parameterization.

The unsafe query is shown as text only and is intentionally not executed.

If user input were:

    Alice' OR '1'='1

a concatenated query could become structurally different from the intended
query.

The safe version treats the entire value as data.
"""

malicious_input = "Alice' OR '1'='1"

unsafe_sql = (
    "SELECT employee_name FROM employees "
    "WHERE employee_name = '" + malicious_input + "';"
)

print("\nUnsafe SQL construction example:")
print(unsafe_sql)

safe_rows = cursor.execute("""
    SELECT employee_name
    FROM employees
    WHERE employee_name = ?;
""", (malicious_input,)).fetchall()

print("\nSafe parameterized result:")
print_rows(safe_rows)


# =============================================================================
# 41. IDENTIFIERS VS LITERALS
# =============================================================================

"""
This distinction is fundamental.

Identifier:
    table name, column name, alias, schema name

Literal:
    actual data value

This is valid:

    WHERE salary > 50000

50000 is a numeric literal.

This is valid:

    WHERE employee_name = 'Alice'

'Alice' is a string literal.

A parameter placeholder can represent a value:

    WHERE employee_name = ?

A normal value parameter cannot directly represent a table name:

    SELECT * FROM ?

Dynamic identifiers require a carefully controlled allow-list and appropriate
identifier quoting supported by the database engine.
"""


# =============================================================================
# 42. SAFE DYNAMIC SQL WITH AN ALLOW-LIST
# =============================================================================

"""
When dynamic column or table selection is unavoidable, do not accept an
arbitrary identifier directly from a user.

Instead, map approved application choices to known SQL identifiers.
"""

allowed_sort_columns = {
    "name": "employee_name",
    "salary": "salary",
    "hire_date": "hire_date",
}

requested_sort = "salary"

if requested_sort not in allowed_sort_columns:
    raise ValueError("Unsupported sort field")

safe_column = allowed_sort_columns[requested_sort]

dynamic_sql = f"""
    SELECT employee_name, salary
    FROM employees
    ORDER BY {safe_column} DESC;
"""

rows = cursor.execute(dynamic_sql).fetchall()

print("\nAllow-listed dynamic SQL:")
print_rows(rows)


# =============================================================================
# 43. QUOTING IDENTIFIERS
# =============================================================================

cursor.execute("""
    CREATE TABLE "sales-data" (
        "order id" INTEGER PRIMARY KEY,
        "order value" REAL
    );
""")

cursor.execute("""
    INSERT INTO "sales-data" ("order id", "order value")
    VALUES (1, 1250.50);
""")

rows = cursor.execute("""
    SELECT
        "order id",
        "order value"
    FROM "sales-data";
""").fetchall()

print("\nQuoted identifiers:")
print_rows(rows)


# =============================================================================
# 44. CASE SENSITIVITY
# =============================================================================

"""
SQL keyword case generally does not matter:

SELECT
select
SeLeCt

String comparison behavior is database- and collation-dependent.

SQLite's default LIKE behavior and equality behavior should not be assumed
to match every other database system.

Identifiers can also have database-specific case rules.

Portable SQL should avoid depending on implementation-specific case behavior.
"""

rows = cursor.execute("""
    SELECT employee_name
    FROM employees
    WHERE employee_name = 'alice';
""").fetchall()

print("\nCase-sensitive equality behavior in this SQLite database:")
print_rows(rows)


# =============================================================================
# 45. DATE AND TIME SYNTAX
# =============================================================================

"""
SQL date/time syntax varies significantly between database systems.

SQLite commonly stores dates and times as TEXT, REAL, or INTEGER rather than
having a dedicated DATE type.

SQLite provides functions such as:

date()
time()
datetime()
strftime()
"""

rows = cursor.execute("""
    SELECT
        employee_name,
        hire_date,
        date(hire_date) AS normalized_date,
        strftime('%Y', hire_date) AS hire_year
    FROM employees;
""").fetchall()

print("\nDate/time functions:")
print_rows(rows)


# =============================================================================
# 46. INDEXES
# =============================================================================

"""
Indexes can accelerate searches, joins, and ordering.

Basic syntax:

CREATE INDEX index_name
ON table_name (column_name);

Indexes also have costs:
- additional storage
- additional write work
- maintenance overhead
- possible memory/cache impact

An index should support actual query patterns rather than being added
indiscriminately.
"""

cursor.execute("""
    CREATE INDEX idx_employees_department
    ON employees (department_id);
""")


# =============================================================================
# 47. COMPOSITE INDEX
# =============================================================================

cursor.execute("""
    CREATE INDEX idx_employees_department_salary
    ON employees (department_id, salary);
""")

"""
Column order matters in composite indexes.

An index on:

    (department_id, salary)

is naturally useful for predicates beginning with department_id.

It is not automatically equivalent to having an independent index on salary.
"""


# =============================================================================
# 48. QUERY PLAN
# =============================================================================

"""
EXPLAIN QUERY PLAN helps inspect how SQLite intends to execute a query.

It is a diagnostic tool, not a guarantee of actual runtime under every
condition.
"""

plan = cursor.execute("""
    EXPLAIN QUERY PLAN
    SELECT employee_name, salary
    FROM employees
    WHERE department_id = 1
    ORDER BY salary;
""").fetchall()

print("\nEXPLAIN QUERY PLAN:")
print_rows(plan)


# =============================================================================
# 49. VIEW
# =============================================================================

"""
A view stores a query definition rather than a separate copy of the data.

Views can:
- simplify repeated queries
- provide a stable abstraction
- hide unnecessary columns
- centralize query logic

A normal view does not necessarily materialize its result.
"""

cursor.execute("""
    CREATE VIEW employee_directory AS
    SELECT
        employee_id,
        employee_name,
        department_id
    FROM employees;
""")

rows = cursor.execute("""
    SELECT *
    FROM employee_directory;
""").fetchall()

print("\nView:")
print_rows(rows)


# =============================================================================
# 50. DISTINCT WITH EXPRESSIONS
# =============================================================================

rows = cursor.execute("""
    SELECT DISTINCT
        CASE
            WHEN salary >= 80000 THEN 'High'
            ELSE 'Standard'
        END AS salary_category
    FROM employees;
""").fetchall()

print("\nDISTINCT on an expression:")
print_rows(rows)


# =============================================================================
# 51. FILTERING AGGREGATES WITH CASE
# =============================================================================

rows = cursor.execute("""
    SELECT
        COUNT(*) AS total_employees,
        SUM(
            CASE
                WHEN salary >= 80000 THEN 1
                ELSE 0
            END
        ) AS high_salary_employees
    FROM employees;
""").fetchall()

print("\nConditional aggregation:")
print_rows(rows)


# =============================================================================
# 52. WINDOW FUNCTIONS
# =============================================================================

"""
Window functions calculate values across related rows without collapsing
those rows like GROUP BY does.

Common window functions include:

ROW_NUMBER()
RANK()
DENSE_RANK()
LAG()
LEAD()
SUM() OVER (...)
AVG() OVER (...)

Example: rank employees within each department.
"""

rows = cursor.execute("""
    SELECT
        employee_name,
        department_id,
        salary,
        RANK() OVER (
            PARTITION BY department_id
            ORDER BY salary DESC
        ) AS salary_rank
    FROM employees;
""").fetchall()

print("\nWindow function:")
print_rows(rows)


# =============================================================================
# 53. ROW_NUMBER
# =============================================================================

rows = cursor.execute("""
    SELECT
        employee_name,
        salary,
        ROW_NUMBER() OVER (
            ORDER BY salary DESC
        ) AS row_number
    FROM employees;
""").fetchall()

print("\nROW_NUMBER:")
print_rows(rows)


# =============================================================================
# 54. LAG AND LEAD
# =============================================================================

rows = cursor.execute("""
    SELECT
        employee_name,
        salary,
        LAG(salary) OVER (
            ORDER BY salary DESC
        ) AS previous_salary,
        LEAD(salary) OVER (
            ORDER BY salary DESC
        ) AS next_salary
    FROM employees;
""").fetchall()

print("\nLAG and LEAD:")
print_rows(rows)


# =============================================================================
# 55. RECURSIVE CTE
# =============================================================================

"""
Recursive CTEs are useful for hierarchical data such as organizational
structures, trees, and graph-like relationships.

The recursive CTE below walks the employee-manager hierarchy.
"""

rows = cursor.execute("""
    WITH RECURSIVE hierarchy AS (
        SELECT
            employee_id,
            employee_name,
            manager_id,
            0 AS level
        FROM employees
        WHERE manager_id IS NULL

        UNION ALL

        SELECT
            employee.employee_id,
            employee.employee_name,
            employee.manager_id,
            hierarchy.level + 1
        FROM employees AS employee
        JOIN hierarchy
            ON employee.manager_id = hierarchy.employee_id
    )
    SELECT
        employee_id,
        employee_name,
        manager_id,
        level
    FROM hierarchy
    ORDER BY level, employee_id;
""").fetchall()

print("\nRecursive CTE:")
print_rows(rows)


# =============================================================================
# 56. TRANSACTIONAL ERROR HANDLING
# =============================================================================

"""
Production database code should handle failures explicitly.

A transaction should generally:
1. start
2. perform related operations
3. commit on success
4. rollback on failure
"""

try:
    connection.execute("BEGIN")

    connection.execute("""
        UPDATE employees
        SET salary = salary + 250
        WHERE employee_id = 1;
    """)

    connection.execute("""
        UPDATE employees
        SET salary = salary + 250
        WHERE employee_id = 2;
    """)

    connection.commit()

except sqlite3.Error:
    connection.rollback()
    raise


# =============================================================================
# 57. CONSTRAINT FAILURE
# =============================================================================

"""
Constraints deliberately reject invalid data.

The following insertion violates the salary CHECK constraint.
"""

try:
    cursor.execute("""
        INSERT INTO employees (
            employee_id,
            employee_name,
            salary
        )
        VALUES (?, ?, ?);
    """, (99, "Invalid Employee", -100))

except sqlite3.IntegrityError as error:
    print("\nConstraint violation caught:")
    print(error)


# =============================================================================
# 58. FOREIGN KEY ENFORCEMENT
# =============================================================================

"""
SQLite requires foreign key enforcement to be enabled explicitly for
connections where enforcement is desired.
"""

connection.execute("PRAGMA foreign_keys = ON;")


# =============================================================================
# 59. TESTING SQL STATEMENTS
# =============================================================================

def test_employee_count_is_positive(db_connection):
    """Basic executable database assertion."""
    row = db_connection.execute("""
        SELECT COUNT(*) AS count
        FROM employees;
    """).fetchone()

    assert row["count"] > 0


def test_no_negative_salaries(db_connection):
    """Verify the business invariant represented by the CHECK constraint."""
    row = db_connection.execute("""
        SELECT COUNT(*) AS invalid_count
        FROM employees
        WHERE salary < 0;
    """).fetchone()

    assert row["invalid_count"] == 0


def test_departments_have_valid_names(db_connection):
    """Check that department names are not NULL."""
    row = db_connection.execute("""
        SELECT COUNT(*) AS invalid_count
        FROM departments
        WHERE department_name IS NULL;
    """).fetchone()

    assert row["invalid_count"] == 0


test_employee_count_is_positive(connection)
test_no_negative_salaries(connection)
test_departments_have_valid_names(connection)

print("\nSQL tests passed.")


# =============================================================================
# 60. COMMON SYNTAX MISTAKES
# =============================================================================

"""
Mistake 1:
    SELECT employee_name employees;

Correct:
    SELECT employee_name
    FROM employees;

Mistake 2:
    WHERE department_id = NULL

Correct:
    WHERE department_id IS NULL

Mistake 3:
    SELECT department_id, AVG(salary)
    FROM employees;

This may be invalid or semantically incorrect depending on the SQL dialect
because department_id is neither aggregated nor grouped.

Correct:
    SELECT department_id, AVG(salary)
    FROM employees
    GROUP BY department_id;

Mistake 4:
    HAVING salary > 70000

when the intention is to filter individual rows.

Usually:
    WHERE salary > 70000

Mistake 5:
    UPDATE employees
    SET salary = salary * 1.10;

without checking whether all rows should actually change.

Mistake 6:
    DELETE FROM employees;

when only selected records were intended for deletion.

Mistake 7:
    SELECT *
    FROM employees
    JOIN departments;

without an appropriate join condition.

This can produce an unintended Cartesian product.

Mistake 8:
    SQL string concatenation with untrusted input.

Use parameters.

Mistake 9:
    Confusing identifiers and literals.

    employee_name     -> identifier
    'employee_name'   -> string literal

Mistake 10:
    Assuming SQL dialects are identical.

Syntax for identity columns, date arithmetic, string functions, pagination,
upsert behavior, procedural SQL, and metadata varies across database systems.
"""


# =============================================================================
# 61. SQL STYLE AND READABILITY
# =============================================================================

"""
Good SQL style:

- Put SQL keywords in a consistent case.
- Use explicit column lists for INSERT.
- Use meaningful aliases.
- Qualify ambiguous columns in joins.
- Format long queries across multiple lines.
- Keep JOIN conditions near the JOIN.
- Keep filters in WHERE.
- Use parameterized values.
- Avoid SELECT * in stable production interfaces.
- Give constraints and indexes meaningful names.
- Prefer simple queries when a complex query is unnecessary.
"""

well_formatted_query = """
SELECT
    e.employee_id,
    e.employee_name,
    d.department_name,
    e.salary
FROM employees AS e
LEFT JOIN departments AS d
    ON e.department_id = d.department_id
WHERE e.salary >= ?
ORDER BY e.salary DESC;
"""

print("\nWell-formatted SQL:")
print(well_formatted_query)


# =============================================================================
# 62. SELECT * VS EXPLICIT COLUMNS
# =============================================================================

"""
SELECT * is convenient during exploration.

Production code often benefits from explicit columns because:
- the returned schema is intentional
- unnecessary data is avoided
- application code is less sensitive to schema additions
- query intent is clearer
"""

rows = cursor.execute("""
    SELECT employee_id, employee_name
    FROM employees;
""").fetchall()

print("\nExplicit projection:")
print_rows(rows)


# =============================================================================
# 63. SQL NULL EDGE CASES
# =============================================================================

cursor.execute("""
    CREATE TABLE null_examples (
        id INTEGER PRIMARY KEY,
        value INTEGER
    );
""")

cursor.executemany("""
    INSERT INTO null_examples (id, value)
    VALUES (?, ?);
""", [
    (1, 10),
    (2, None),
    (3, 0),
])

rows = cursor.execute("""
    SELECT
        id,
        value,
        value + 5 AS plus_five,
        COALESCE(value, 0) + 5 AS safe_plus_five
    FROM null_examples;
""").fetchall()

print("\nNULL arithmetic:")
print_rows(rows)


# =============================================================================
# 64. IN AND NULL EDGE CASE
# =============================================================================

"""
NULL interacts subtly with IN and NOT IN.

A NOT IN condition can produce unexpected results when its comparison set
contains NULL because the result may become UNKNOWN.

When NULL semantics matter, NOT EXISTS is often a clearer alternative.
"""

cursor.execute("""
    CREATE TABLE lookup_values (
        value INTEGER
    );
""")

cursor.executemany("""
    INSERT INTO lookup_values (value)
    VALUES (?);
""", [(1,), (None,)])

rows = cursor.execute("""
    SELECT value
    FROM null_examples
    WHERE value NOT IN (
        SELECT value
        FROM lookup_values
    );
""").fetchall()

print("\nNOT IN with NULL in the subquery:")
print_rows(rows)


# =============================================================================
# 65. COLLATION AND TEXT COMPARISON
# =============================================================================

"""
Collation controls how text values are compared and ordered.

SQLite provides built-in collations such as:

BINARY
NOCASE
RTRIM

Other database systems offer substantially richer collation systems.

Example:
"""

cursor.execute("""
    CREATE TABLE case_demo (
        value TEXT COLLATE NOCASE
    );
""")

cursor.executemany("""
    INSERT INTO case_demo (value)
    VALUES (?);
""", [
    ("Alice",),
    ("BOB",),
])

rows = cursor.execute("""
    SELECT value
    FROM case_demo
    WHERE value = 'alice';
""").fetchall()

print("\nNOCASE collation:")
print_rows(rows)


# =============================================================================
# 66. UPSERT
# =============================================================================

"""
An UPSERT handles a conflict by updating or otherwise resolving it instead
of simply failing.

SQLite supports:

INSERT ... ON CONFLICT ... DO UPDATE

The exact UPSERT syntax differs between database systems.
"""

cursor.execute("""
    INSERT INTO departments (department_id, department_name)
    VALUES (?, ?)
    ON CONFLICT(department_id)
    DO UPDATE SET department_name = excluded.department_name;
""", (1, "Engineering & Technology"))

print("\nUPSERT:")
print_rows(cursor.execute("""
    SELECT *
    FROM departments
    WHERE department_id = 1;
""").fetchall())


# =============================================================================
# 67. TRANSACTION ISOLATION CONSIDERATIONS
# =============================================================================

"""
Concurrent database behavior depends on the database engine and isolation
level.

Important concepts include:

Dirty read
    Reading uncommitted changes.

Non-repeatable read
    Reading the same row twice and seeing different committed values.

Phantom read
    Re-running a range query and seeing additional or missing rows.

Write conflicts
    Concurrent modifications competing for the same data.

SQLite uses a locking and transaction model that differs from server
databases such as PostgreSQL, MySQL, SQL Server, and Oracle.

Applications should understand the selected database's transaction semantics
rather than assuming that all SQL engines behave identically.
"""


# =============================================================================
# 68. SECURITY PRINCIPLES
# =============================================================================

"""
SQL security requires several layers:

1. Parameterize data values.
2. Never concatenate untrusted values into SQL syntax.
3. Validate dynamic identifiers with allow-lists.
4. Use least-privilege database accounts.
5. Restrict access to sensitive tables and columns.
6. Avoid exposing database error details to untrusted clients.
7. Encrypt connections when the database architecture requires network
   communication.
8. Protect database credentials.
9. Audit sensitive operations.
10. Use constraints to protect data integrity.

SQL injection is not prevented merely by validating that an input "looks
safe." Parameterization is the primary defense for values.
"""


# =============================================================================
# 69. PERFORMANCE PRINCIPLES
# =============================================================================

"""
SQL performance depends on:
- table size
- indexes
- cardinality
- query shape
- join strategy
- filtering selectivity
- sorting
- grouping
- disk and memory
- database engine
- statistics
- concurrency

Useful techniques:

- Select only required columns.
- Filter early when appropriate.
- Index columns used frequently in selective predicates and joins.
- Inspect query plans.
- Avoid accidental Cartesian products.
- Avoid unnecessary DISTINCT.
- Avoid unnecessary ORDER BY.
- Avoid applying functions to indexed columns when that prevents useful
  index access in the relevant database.
- Use pagination carefully for large datasets.
- Batch related writes where appropriate.
- Measure actual workloads rather than optimizing based solely on intuition.
"""


# =============================================================================
# 70. PAGINATION
# =============================================================================

"""
LIMIT/OFFSET is simple:

LIMIT 20 OFFSET 40

But very large OFFSET values can become inefficient because the database may
need to walk past many preceding rows.

Keyset or cursor pagination is often better for large, ordered datasets.
"""

last_seen_id = 2

rows = cursor.execute("""
    SELECT employee_id, employee_name
    FROM employees
    WHERE employee_id > ?
    ORDER BY employee_id
    LIMIT 3;
""", (last_seen_id,)).fetchall()

print("\nKeyset-style pagination:")
print_rows(rows)


# =============================================================================
# 71. SQL STATEMENT TYPES IN PRACTICE
# =============================================================================

"""
DDL example:
    CREATE TABLE ...

DML example:
    INSERT INTO ...
    UPDATE ...
    DELETE ...

DQL example:
    SELECT ...

TCL example:
    BEGIN
    COMMIT
    ROLLBACK

DCL examples in systems that support them:
    GRANT
    REVOKE
"""


# =============================================================================
# 72. MINI END-TO-END REPORT QUERY
# =============================================================================

"""
This query combines:
- SELECT
- aliases
- LEFT JOIN
- GROUP BY
- COUNT
- AVG
- CASE
- HAVING
- ORDER BY
"""

rows = cursor.execute("""
    SELECT
        d.department_name AS department,
        COUNT(e.employee_id) AS employee_count,
        ROUND(AVG(e.salary), 2) AS average_salary,
        CASE
            WHEN AVG(e.salary) >= 80000 THEN 'High'
            WHEN AVG(e.salary) >= 65000 THEN 'Medium'
            ELSE 'Low'
        END AS salary_level
    FROM departments AS d
    LEFT JOIN employees AS e
        ON d.department_id = e.department_id
    GROUP BY
        d.department_id,
        d.department_name
    HAVING COUNT(e.employee_id) > 0
    ORDER BY average_salary DESC;
""").fetchall()

print("\nEnd-to-end department report:")
print_rows(rows)


# =============================================================================
# 73. MINI DATA-QUALITY QUERY
# =============================================================================

rows = cursor.execute("""
    SELECT
        COUNT(*) AS total_rows,
        SUM(
            CASE
                WHEN employee_name IS NULL THEN 1
                ELSE 0
            END
        ) AS missing_names,
        SUM(
            CASE
                WHEN salary IS NULL THEN 1
                ELSE 0
            END
        ) AS missing_salaries,
        SUM(
            CASE
                WHEN salary < 0 THEN 1
                ELSE 0
            END
        ) AS negative_salaries
    FROM employees;
""").fetchall()

print("\nData-quality check:")
print_rows(rows)


# =============================================================================
# 74. DEBUGGING SQL
# =============================================================================

"""
A systematic debugging process:

1. Read the exact database error.
2. Identify the failing SQL statement.
3. Run the smallest reproducible query.
4. Check table and column names.
5. Check data types and NULL behavior.
6. Check JOIN conditions.
7. Check GROUP BY and aggregate logic.
8. Check parentheses and quotation marks.
9. Check parameter values independently.
10. Inspect EXPLAIN QUERY PLAN when performance is the problem.
11. Compare expected rows with actual intermediate results.

A complex query can often be debugged by executing its FROM/JOIN section,
then adding WHERE, GROUP BY, HAVING, SELECT expressions, and ORDER BY
incrementally.
"""


# =============================================================================
# 75. DATABASE METADATA
# =============================================================================

"""
SQLite-specific metadata commands are useful while learning and debugging.

PRAGMA table_info(table_name)
    Displays column information.

sqlite_master
    Stores metadata about SQLite schema objects.
"""

rows = cursor.execute("""
    PRAGMA table_info(employees);
""").fetchall()

print("\nEmployee table metadata:")
print_rows(rows)


# =============================================================================
# 76. CLEANUP
# =============================================================================

connection.close()

print("\nDatabase connection closed.")
print("SQL Syntax Fundamentals examples completed successfully.")
