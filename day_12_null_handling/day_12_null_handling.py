"""
NULL Handling in SQL
====================

A standalone study script covering SQL NULL semantics from beginner to advanced
level using Python's built-in sqlite3 module.

The examples use SQLite because it is available in the Python standard library.
Most NULL behavior demonstrated here follows standard SQL semantics, while
comments identify SQLite-specific behavior where relevant.

Run:
    python null_handling_sql.py
"""

import sqlite3
from pprint import pprint


# ---------------------------------------------------------------------------
# 1. DATABASE SETUP
# ---------------------------------------------------------------------------

def create_connection():
    """Create an in-memory SQLite database."""
    return sqlite3.connect(":memory:")


def create_sample_database(connection):
    """Create tables and insert rows containing ordinary values and NULLs."""
    cursor = connection.cursor()

    cursor.executescript(
        """
        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            department TEXT,
            manager_id INTEGER,
            salary REAL,
            bonus REAL,
            email TEXT UNIQUE
        );

        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL
        );

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            city TEXT,
            phone TEXT
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date TEXT,
            shipped_date TEXT,
            delivered_date TEXT,
            amount REAL,
            discount REAL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT,
            price REAL,
            stock INTEGER
        );

        INSERT INTO departments VALUES
            (1, 'Engineering'),
            (2, 'Finance'),
            (3, 'Marketing'),
            (4, 'Human Resources');

        INSERT INTO employees VALUES
            (1, 'Asha', 'Engineering', NULL, 90000, 10000, 'asha@example.com'),
            (2, 'Bharat', 'Engineering', 1, 70000, NULL, NULL),
            (3, 'Chitra', 'Finance', NULL, 80000, 5000, 'chitra@example.com'),
            (4, 'Dev', NULL, NULL, 60000, NULL, 'dev@example.com'),
            (5, 'Esha', 'Marketing', 3, NULL, 3000, NULL),
            (6, 'Farhan', 'Engineering', 1, 75000, 7500, 'farhan@example.com'),
            (7, 'Gauri', NULL, NULL, NULL, NULL, NULL);

        INSERT INTO customers VALUES
            (1, 'Customer A', 'Lucknow', '9876543210'),
            (2, 'Customer B', NULL, '9123456780'),
            (3, 'Customer C', 'Delhi', NULL),
            (4, 'Customer D', NULL, NULL);

        INSERT INTO orders VALUES
            (101, 1, '2026-01-05', '2026-01-07', '2026-01-10', 1000, 100),
            (102, 2, '2026-01-06', NULL, NULL, 1500, NULL),
            (103, 3, '2026-01-08', '2026-01-09', NULL, 2000, 200),
            (104, 4, NULL, NULL, NULL, NULL, NULL);

        INSERT INTO products VALUES
            (1, 'Laptop', 'Electronics', 80000, 5),
            (2, 'Mouse', 'Electronics', 1200, NULL),
            (3, 'Notebook', NULL, 150, 100),
            (4, 'Monitor', 'Electronics', NULL, 10),
            (5, 'Chair', 'Furniture', 7000, NULL);
        """
    )

    connection.commit()


def show_query(connection, title, query, parameters=()):
    """Execute a query and print column names and rows."""
    print(f"\n--- {title} ---")
    print(query.strip())

    cursor = connection.execute(query, parameters)
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    print("Columns:", columns)
    for row in rows:
        print(row)

    return rows


# ---------------------------------------------------------------------------
# 2. WHAT NULL MEANS
# ---------------------------------------------------------------------------

def demonstrate_null_concept(connection):
    """
    NULL represents a missing, unknown, unavailable, or inapplicable value.

    NULL is not:
        - zero
        - an empty string
        - FALSE
        - the string "NULL"
        - a normal comparable value

    The exact business meaning depends on the database design.
    """
    show_query(
        connection,
        "Rows containing NULL values",
        """
        SELECT employee_id, employee_name, department, salary, bonus, email
        FROM employees
        ORDER BY employee_id;
        """,
    )

    print(
        "\nImportant distinction:\n"
        "salary = NULL means the salary is unknown/missing.\n"
        "salary = 0 means the salary is known and equals zero.\n"
        "email = '' means an empty string, not SQL NULL."
    )


# ---------------------------------------------------------------------------
# 3. THREE-VALUED LOGIC
# ---------------------------------------------------------------------------

def demonstrate_three_valued_logic(connection):
    """
    SQL uses three-valued logic for expressions involving NULL:

        TRUE
        FALSE
        UNKNOWN

    A comparison involving NULL normally produces UNKNOWN.

    Examples:
        NULL = NULL       -> UNKNOWN
        NULL <> NULL      -> UNKNOWN
        5 = NULL          -> UNKNOWN
        5 <> NULL         -> UNKNOWN

    SQLite exposes UNKNOWN through expressions used in WHERE clauses:
    UNKNOWN behaves like a condition that is not TRUE.
    """

    queries = {
        "NULL = NULL": "SELECT NULL = NULL AS result;",
        "NULL <> NULL": "SELECT NULL <> NULL AS result;",
        "NULL > 10": "SELECT NULL > 10 AS result;",
        "NULL < 10": "SELECT NULL < 10 AS result;",
        "5 = NULL": "SELECT 5 = NULL AS result;",
        "5 <> NULL": "SELECT 5 <> NULL AS result;",
        "NULL IS NULL": "SELECT NULL IS NULL AS result;",
        "NULL IS NOT NULL": "SELECT NULL IS NOT NULL AS result;",
    }

    for title, query in queries.items():
        show_query(connection, title, query)


# ---------------------------------------------------------------------------
# 4. WHY = NULL DOES NOT WORK
# ---------------------------------------------------------------------------

def demonstrate_wrong_null_comparison(connection):
    """
    Incorrect:

        WHERE department = NULL

    Correct:

        WHERE department IS NULL

    NULL cannot be tested with ordinary equality because NULL represents
    an unknown/missing value rather than a known value.
    """

    show_query(
        connection,
        "Incorrect NULL comparison",
        """
        SELECT employee_id, employee_name, department
        FROM employees
        WHERE department = NULL;
        """,
    )

    show_query(
        connection,
        "Correct NULL test",
        """
        SELECT employee_id, employee_name, department
        FROM employees
        WHERE department IS NULL;
        """,
    )

    show_query(
        connection,
        "Correct NOT NULL test",
        """
        SELECT employee_id, employee_name, department
        FROM employees
        WHERE department IS NOT NULL;
        """,
    )


# ---------------------------------------------------------------------------
# 5. IS NULL
# ---------------------------------------------------------------------------

def demonstrate_is_null(connection):
    """
    IS NULL explicitly tests whether an expression evaluates to NULL.
    """

    show_query(
        connection,
        "Employees without a department",
        """
        SELECT employee_name
        FROM employees
        WHERE department IS NULL;
        """,
    )

    show_query(
        connection,
        "Employees without a manager",
        """
        SELECT employee_name
        FROM employees
        WHERE manager_id IS NULL;
        """,
    )

    show_query(
        connection,
        "Employees without a bonus",
        """
        SELECT employee_name
        FROM employees
        WHERE bonus IS NULL;
        """,
    )


# ---------------------------------------------------------------------------
# 6. IS NOT NULL
# ---------------------------------------------------------------------------

def demonstrate_is_not_null(connection):
    """IS NOT NULL identifies values that are actually present."""

    show_query(
        connection,
        "Employees with a known salary",
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary IS NOT NULL;
        """,
    )

    show_query(
        connection,
        "Employees with email addresses",
        """
        SELECT employee_name, email
        FROM employees
        WHERE email IS NOT NULL;
        """,
    )


# ---------------------------------------------------------------------------
# 7. NULL AND WHERE
# ---------------------------------------------------------------------------

def demonstrate_where_behavior(connection):
    """
    WHERE keeps rows only when its predicate evaluates to TRUE.

    FALSE and UNKNOWN are both filtered out.

    This is why:
        WHERE salary > 70000

    does not include employees whose salary is NULL.
    """

    show_query(
        connection,
        "Salary greater than 70000",
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary > 70000;
        """,
    )

    show_query(
        connection,
        "Salary not greater than 70000",
        """
        SELECT employee_name, salary
        FROM employees
        WHERE NOT (salary > 70000);
        """,
    )

    print(
        "\nEmployees with NULL salary appear in neither result because "
        "salary > 70000 evaluates to UNKNOWN and NOT UNKNOWN remains UNKNOWN."
    )


# ---------------------------------------------------------------------------
# 8. NULL WITH AND
# ---------------------------------------------------------------------------

def demonstrate_and_logic(connection):
    """
    Important three-valued logic rules:

        TRUE AND UNKNOWN   = UNKNOWN
        FALSE AND UNKNOWN  = FALSE
        UNKNOWN AND TRUE   = UNKNOWN
        UNKNOWN AND FALSE  = FALSE

    WHERE removes UNKNOWN.
    """

    show_query(
        connection,
        "AND with a NULL salary",
        """
        SELECT employee_name, salary, department
        FROM employees
        WHERE salary > 70000
          AND department = 'Engineering';
        """,
    )

    show_query(
        connection,
        "Explicitly including NULL salaries",
        """
        SELECT employee_name, salary, department
        FROM employees
        WHERE (salary > 70000 OR salary IS NULL)
          AND department = 'Engineering';
        """,
    )


# ---------------------------------------------------------------------------
# 9. NULL WITH OR
# ---------------------------------------------------------------------------

def demonstrate_or_logic(connection):
    """
    Important rules:

        TRUE OR UNKNOWN   = TRUE
        FALSE OR UNKNOWN  = UNKNOWN
        UNKNOWN OR UNKNOWN = UNKNOWN

    Example:
        salary > 70000 OR salary IS NULL

    explicitly includes employees whose salary is unknown.
    """

    show_query(
        connection,
        "Salary above 70000 OR unknown",
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary > 70000 OR salary IS NULL;
        """,
    )


# ---------------------------------------------------------------------------
# 10. NOT AND UNKNOWN
# ---------------------------------------------------------------------------

def demonstrate_not_unknown(connection):
    """
    A common misconception is that NOT UNKNOWN becomes TRUE.

    It does not.

        NOT TRUE     = FALSE
        NOT FALSE    = TRUE
        NOT UNKNOWN  = UNKNOWN
    """

    show_query(
        connection,
        "NOT comparison involving NULL",
        """
        SELECT
            employee_name,
            salary,
            NOT (salary = 70000) AS not_equal_expression
        FROM employees;
        """,
    )


# ---------------------------------------------------------------------------
# 11. COALESCE
# ---------------------------------------------------------------------------

def demonstrate_coalesce(connection):
    """
    COALESCE(expression1, expression2, ...)
    returns the first non-NULL expression.

    Examples:

        COALESCE(bonus, 0)
        COALESCE(city, 'Unknown')
        COALESCE(phone, email, 'No contact information')
    """

    show_query(
        connection,
        "Replace missing bonuses with zero",
        """
        SELECT
            employee_name,
            bonus,
            COALESCE(bonus, 0) AS normalized_bonus
        FROM employees;
        """,
    )

    show_query(
        connection,
        "Replace missing cities",
        """
        SELECT
            customer_name,
            city,
            COALESCE(city, 'Unknown city') AS display_city
        FROM customers;
        """,
    )

    show_query(
        connection,
        "Multiple fallback values",
        """
        SELECT
            customer_name,
            COALESCE(phone, 'No phone') AS contact_phone
        FROM customers;
        """,
    )


# ---------------------------------------------------------------------------
# 12. COALESCE WITH CALCULATIONS
# ---------------------------------------------------------------------------

def demonstrate_coalesce_calculations(connection):
    """
    NULL propagates through many arithmetic operations.

        100 + NULL -> NULL
        100 * NULL -> NULL

    COALESCE can make the intended business rule explicit.
    """

    show_query(
        connection,
        "Raw compensation calculation",
        """
        SELECT
            employee_name,
            salary,
            bonus,
            salary + bonus AS total_compensation
        FROM employees;
        """,
    )

    show_query(
        connection,
        "Compensation treating missing bonus as zero",
        """
        SELECT
            employee_name,
            salary,
            bonus,
            COALESCE(salary, 0) + COALESCE(bonus, 0) AS total_compensation
        FROM employees;
        """,
    )

    print(
        "\nImportant design point: COALESCE changes NULL into a business-defined "
        "fallback. That is appropriate only when the fallback is semantically correct."
    )


# ---------------------------------------------------------------------------
# 13. NULL IN ARITHMETIC
# ---------------------------------------------------------------------------

def demonstrate_null_arithmetic(connection):
    """
    Most arithmetic involving NULL produces NULL because the result is unknown.
    """

    show_query(
        connection,
        "Arithmetic involving NULL",
        """
        SELECT
            10 + NULL AS addition,
            10 - NULL AS subtraction,
            10 * NULL AS multiplication,
            10 / NULL AS division;
        """,
    )

    show_query(
        connection,
        "Arithmetic with COALESCE",
        """
        SELECT
            10 + COALESCE(NULL, 0) AS addition,
            10 * COALESCE(NULL, 1) AS multiplication;
        """,
    )


# ---------------------------------------------------------------------------
# 14. NULL IN COMPARISONS
# ---------------------------------------------------------------------------

def demonstrate_comparison_behavior(connection):
    """
    Ordinary comparison operators do not provide a NULL test.

    Operators:
        =
        <>
        !=
        >
        <
        >=
        <=

    Use IS NULL and IS NOT NULL for NULL detection.
    """

    show_query(
        connection,
        "Ordinary comparison with NULL column",
        """
        SELECT
            employee_name,
            salary,
            salary = 70000 AS equals_70000,
            salary <> 70000 AS not_equals_70000,
            salary > 70000 AS greater_than_70000
        FROM employees;
        """,
    )


# ---------------------------------------------------------------------------
# 15. NULL AND IN
# ---------------------------------------------------------------------------

def demonstrate_in_operator(connection):
    """
    NULL has subtle behavior with IN and NOT IN.

    For example:

        value IN (10, 20, NULL)

    can evaluate to UNKNOWN when value does not match 10 or 20.

    This becomes especially important with NOT IN.
    """

    show_query(
        connection,
        "IN containing NULL",
        """
        SELECT
            30 IN (10, 20, NULL) AS result_1,
            20 IN (10, 20, NULL) AS result_2,
            NULL IN (10, 20, NULL) AS result_3;
        """,
    )

    show_query(
        connection,
        "NOT IN containing NULL",
        """
        SELECT
            30 NOT IN (10, 20, NULL) AS result_1,
            20 NOT IN (10, 20, NULL) AS result_2;
        """,
    )

    print(
        "\nRule: avoid putting NULL into an IN list unless the three-valued "
        "logic behavior is deliberately intended."
    )


# ---------------------------------------------------------------------------
# 16. NOT IN AND SUBQUERIES
# ---------------------------------------------------------------------------

def demonstrate_not_in_subquery(connection):
    """
    The classic NOT IN problem:

        WHERE customer_id NOT IN (
            SELECT customer_id
            FROM some_table
        )

    If the subquery returns NULL, the NOT IN predicate can become UNKNOWN
    for values that otherwise appear to be non-matches.

    A NULL-safe alternative is often NOT EXISTS.
    """

    connection.execute(
        """
        CREATE TABLE blocked_customers (
            customer_id INTEGER
        );
        """
    )

    connection.executemany(
        "INSERT INTO blocked_customers(customer_id) VALUES (?)",
        [(2,), (None,)],
    )

    show_query(
        connection,
        "NOT IN with a NULL-producing subquery",
        """
        SELECT customer_id, customer_name
        FROM customers
        WHERE customer_id NOT IN (
            SELECT customer_id
            FROM blocked_customers
        );
        """,
    )

    show_query(
        connection,
        "NOT EXISTS alternative",
        """
        SELECT c.customer_id, c.customer_name
        FROM customers AS c
        WHERE NOT EXISTS (
            SELECT 1
            FROM blocked_customers AS b
            WHERE b.customer_id = c.customer_id
        );
        """,
    )


# ---------------------------------------------------------------------------
# 17. NULL AND DISTINCT
# ---------------------------------------------------------------------------

def demonstrate_distinct(connection):
    """
    DISTINCT removes duplicate result values.

    NULL values are treated as one distinct grouping value in this context.
    """

    show_query(
        connection,
        "Distinct departments",
        """
        SELECT DISTINCT department
        FROM employees
        ORDER BY department;
        """,
    )


# ---------------------------------------------------------------------------
# 18. NULL AND GROUP BY
# ---------------------------------------------------------------------------

def demonstrate_group_by(connection):
    """
    GROUP BY groups rows with NULL in the same grouping category.
    """

    show_query(
        connection,
        "Employees grouped by department",
        """
        SELECT
            department,
            COUNT(*) AS employee_count
        FROM employees
        GROUP BY department
        ORDER BY department;
        """,
    )


# ---------------------------------------------------------------------------
# 19. NULL AND AGGREGATE FUNCTIONS
# ---------------------------------------------------------------------------

def demonstrate_aggregates(connection):
    """
    Most aggregate functions ignore NULL values.

        COUNT(*) counts rows.
        COUNT(column) counts non-NULL column values.
        SUM(column) ignores NULL values.
        AVG(column) ignores NULL values.
        MIN(column) ignores NULL values.
        MAX(column) ignores NULL values.

    This distinction is fundamental.
    """

    show_query(
        connection,
        "COUNT star versus COUNT column",
        """
        SELECT
            COUNT(*) AS all_employees,
            COUNT(salary) AS employees_with_salary,
            COUNT(bonus) AS employees_with_bonus,
            COUNT(email) AS employees_with_email
        FROM employees;
        """,
    )

    show_query(
        connection,
        "Aggregate behavior",
        """
        SELECT
            SUM(salary) AS salary_sum,
            AVG(salary) AS salary_average,
            MIN(salary) AS minimum_salary,
            MAX(salary) AS maximum_salary
        FROM employees;
        """,
    )

    show_query(
        connection,
        "Aggregate after replacing NULL",
        """
        SELECT
            SUM(COALESCE(bonus, 0)) AS total_bonus,
            AVG(COALESCE(bonus, 0)) AS average_bonus_treating_missing_as_zero
        FROM employees;
        """,
    )

    print(
        "\nWarning: AVG(bonus) and AVG(COALESCE(bonus, 0)) answer different questions."
    )


# ---------------------------------------------------------------------------
# 20. COUNT DISTINCT AND NULL
# ---------------------------------------------------------------------------

def demonstrate_count_distinct(connection):
    """
    COUNT(DISTINCT column) counts distinct non-NULL values.
    NULL is not counted as a distinct value by COUNT.
    """

    show_query(
        connection,
        "COUNT DISTINCT",
        """
        SELECT
            COUNT(DISTINCT department) AS distinct_departments_without_null,
            COUNT(DISTINCT email) AS distinct_emails
        FROM employees;
        """,
    )


# ---------------------------------------------------------------------------
# 21. NULL AND HAVING
# ---------------------------------------------------------------------------

def demonstrate_having(connection):
    """HAVING also filters using SQL's three-valued logic."""

    show_query(
        connection,
        "Groups with known average salary",
        """
        SELECT
            department,
            AVG(salary) AS average_salary
        FROM employees
        GROUP BY department
        HAVING AVG(salary) > 65000;
        """,
    )


# ---------------------------------------------------------------------------
# 22. NULL AND ORDER BY
# ---------------------------------------------------------------------------

def demonstrate_order_by(connection):
    """
    NULL sorting order is database-specific.

    Do not assume every SQL database places NULL first or last by default.

    SQLite has its own default ordering behavior. Explicit expressions can
    provide portable control.
    """

    show_query(
        connection,
        "Default NULL ordering",
        """
        SELECT employee_name, salary
        FROM employees
        ORDER BY salary;
        """,
    )

    show_query(
        connection,
        "Force NULL salaries last",
        """
        SELECT employee_name, salary
        FROM employees
        ORDER BY salary IS NULL, salary;
        """,
    )

    show_query(
        connection,
        "Force NULL salaries first",
        """
        SELECT employee_name, salary
        FROM employees
        ORDER BY salary IS NOT NULL, salary;
        """,
    )


# ---------------------------------------------------------------------------
# 23. NULL AND CASE
# ---------------------------------------------------------------------------

def demonstrate_case(connection):
    """
    CASE can explicitly classify NULL values.

    A searched CASE is often clearer for NULL-specific business rules.
    """

    show_query(
        connection,
        "Classify salary availability",
        """
        SELECT
            employee_name,
            salary,
            CASE
                WHEN salary IS NULL THEN 'Salary unavailable'
                WHEN salary = 0 THEN 'Zero salary'
                ELSE 'Salary available'
            END AS salary_status
        FROM employees;
        """,
    )

    show_query(
        connection,
        "Simple CASE versus NULL",
        """
        SELECT
            employee_name,
            CASE department
                WHEN NULL THEN 'No department'
                ELSE department
            END AS department_label
        FROM employees;
        """,
    )

    print(
        "\nThe simple CASE above does not reliably test NULL using WHEN NULL. "
        "Use searched CASE with WHEN department IS NULL instead."
    )


# ---------------------------------------------------------------------------
# 24. CORRECT CASE NULL HANDLING
# ---------------------------------------------------------------------------

def demonstrate_correct_case(connection):
    """Use IS NULL inside a searched CASE."""

    show_query(
        connection,
        "Correct CASE NULL handling",
        """
        SELECT
            employee_name,
            CASE
                WHEN department IS NULL THEN 'No department'
                ELSE department
            END AS department_label
        FROM employees;
        """,
    )


# ---------------------------------------------------------------------------
# 25. NULLIF
# ---------------------------------------------------------------------------

def demonstrate_nullif(connection):
    """
    NULLIF(a, b) returns NULL when a = b; otherwise it returns a.

    It is useful for converting sentinel values such as zero or an empty
    string into NULL when that represents the desired data meaning.

    It is also useful for avoiding division-by-zero errors.
    """

    show_query(
        connection,
        "NULLIF basics",
        """
        SELECT
            NULLIF(10, 10) AS same_values,
            NULLIF(10, 5) AS different_values,
            NULLIF('', '') AS empty_string;
        """,
    )

    show_query(
        connection,
        "NULLIF for safe division",
        """
        SELECT
            100.0 / NULLIF(10, 0) AS normal_division,
            100.0 / NULLIF(0, 0) AS zero_denominator_becomes_null;
        """,
    )


# ---------------------------------------------------------------------------
# 26. COALESCE VERSUS NULLIF
# ---------------------------------------------------------------------------

def demonstrate_coalesce_vs_nullif(connection):
    """
    COALESCE:
        NULL -> fallback value

    NULLIF:
        specific value -> NULL

    They often appear together in data-cleaning expressions.
    """

    show_query(
        connection,
        "Convert empty string to NULL, then use a fallback",
        """
        SELECT
            COALESCE(NULLIF('', ''), 'No value') AS cleaned_value;
        """,
    )


# ---------------------------------------------------------------------------
# 27. NULL IN JOINS
# ---------------------------------------------------------------------------

def demonstrate_joins(connection):
    """
    Ordinary equality joins do not match NULL to NULL.

        a.key = b.key

    If both keys are NULL, the comparison is UNKNOWN.

    LEFT JOIN is particularly important because unmatched rows on the
    right side are represented by NULL columns.
    """

    show_query(
        connection,
        "INNER JOIN",
        """
        SELECT
            e.employee_name,
            e.department,
            d.department_name
        FROM employees AS e
        INNER JOIN departments AS d
            ON e.department = d.department_name;
        """,
    )

    show_query(
        connection,
        "LEFT JOIN exposes NULLs",
        """
        SELECT
            e.employee_name,
            e.department,
            d.department_id
        FROM employees AS e
        LEFT JOIN departments AS d
            ON e.department = d.department_name
        ORDER BY e.employee_id;
        """,
    )


# ---------------------------------------------------------------------------
# 28. NULL-SAFE JOIN THINKING
# ---------------------------------------------------------------------------

def demonstrate_null_safe_join(connection):
    """
    If business semantics require NULL to match NULL, ordinary equality is
    not sufficient.

    SQLite supports the NULL-safe IS operator:

        a.key IS b.key

    PostgreSQL provides:

        a.key IS NOT DISTINCT FROM b.key

    MySQL also provides NULL-safe equality with:

        a.key <=> b.key

    These operators are not interchangeable across all database engines.
    """

    connection.execute(
        """
        CREATE TABLE nullable_codes_a (
            id INTEGER,
            code TEXT
        );

        CREATE TABLE nullable_codes_b (
            id INTEGER,
            code TEXT
        );
        """
    )

    connection.executemany(
        "INSERT INTO nullable_codes_a VALUES (?, ?)",
        [(1, "A"), (2, None)],
    )

    connection.executemany(
        "INSERT INTO nullable_codes_b VALUES (?, ?)",
        [(10, "A"), (20, None)],
    )

    show_query(
        connection,
        "Ordinary NULL equality join",
        """
        SELECT a.id, a.code, b.id, b.code
        FROM nullable_codes_a AS a
        JOIN nullable_codes_b AS b
          ON a.code = b.code;
        """,
    )

    show_query(
        connection,
        "SQLite NULL-safe join using IS",
        """
        SELECT a.id, a.code, b.id, b.code
        FROM nullable_codes_a AS a
        JOIN nullable_codes_b AS b
          ON a.code IS b.code;
        """,
    )


# ---------------------------------------------------------------------------
# 29. LEFT JOIN FILTERING: ON VERSUS WHERE
# ---------------------------------------------------------------------------

def demonstrate_on_versus_where(connection):
    """
    A frequent source of bugs:

        LEFT JOIN ... WHERE right_table.column = value

    can remove NULL-extended rows and make the query behave like an INNER JOIN.

    Moving the condition into ON can preserve unmatched left-side rows.
    """

    show_query(
        connection,
        "Condition in WHERE",
        """
        SELECT
            c.customer_name,
            o.order_id
        FROM customers AS c
        LEFT JOIN orders AS o
            ON c.customer_id = o.customer_id
        WHERE o.shipped_date IS NOT NULL
        ORDER BY c.customer_id;
        """,
    )

    show_query(
        connection,
        "Condition in ON",
        """
        SELECT
            c.customer_name,
            o.order_id
        FROM customers AS c
        LEFT JOIN orders AS o
            ON c.customer_id = o.customer_id
           AND o.shipped_date IS NOT NULL
        ORDER BY c.customer_id;
        """,
    )


# ---------------------------------------------------------------------------
# 30. NULL AND UNIQUE CONSTRAINTS
# ---------------------------------------------------------------------------

def demonstrate_unique_and_null(connection):
    """
    SQL implementations commonly allow multiple NULL values in a UNIQUE
    column because NULL represents absence/unknown rather than equality.

    SQLite permits multiple NULLs in a UNIQUE column.
    Other database engines have broadly similar behavior, but exact indexing
    and constraint semantics can differ.
    """

    connection.execute(
        """
        CREATE TABLE unique_demo (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE
        );
        """
    )

    connection.executemany(
        "INSERT INTO unique_demo(email) VALUES (?)",
        [(None,), (None,), ("same@example.com",)],
    )

    show_query(
        connection,
        "Multiple NULL values in a UNIQUE column",
        """
        SELECT id, email
        FROM unique_demo
        ORDER BY id;
        """,
    )


# ---------------------------------------------------------------------------
# 31. NULL AND CONSTRAINTS
# ---------------------------------------------------------------------------

def demonstrate_constraints(connection):
    """
    NOT NULL prevents a column from storing NULL.

    It is a schema-level rule and should be used when the value is genuinely
    mandatory.

    CHECK constraints and NULL require care because CHECK behavior interacts
    with UNKNOWN differently than a WHERE clause.
    """

    connection.execute(
        """
        CREATE TABLE required_data (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER CHECK (age >= 0)
        );
        """
    )

    connection.execute(
        "INSERT INTO required_data(name, age) VALUES (?, ?)",
        ("Valid person", 25),
    )

    connection.execute(
        "INSERT INTO required_data(name, age) VALUES (?, ?)",
        ("Unknown age", None),
    )

    show_query(
        connection,
        "NOT NULL versus nullable CHECK column",
        """
        SELECT *
        FROM required_data;
        """,
    )

    try:
        connection.execute(
            "INSERT INTO required_data(name, age) VALUES (?, ?)",
            (None, 30),
        )
    except sqlite3.IntegrityError as error:
        print("\nNOT NULL violation:", error)

    try:
        connection.execute(
            "INSERT INTO required_data(name, age) VALUES (?, ?)",
            ("Negative age", -1),
        )
    except sqlite3.IntegrityError as error:
        print("CHECK violation:", error)


# ---------------------------------------------------------------------------
# 32. NULL AND FOREIGN KEYS
# ---------------------------------------------------------------------------

def demonstrate_foreign_keys(connection):
    """
    A nullable foreign key can represent an optional relationship.

    Example:
        manager_id NULL

    means that an employee currently has no recorded manager.

    This is different from pointing to a fake manager such as ID 0.
    """

    connection.execute("PRAGMA foreign_keys = ON")

    show_query(
        connection,
        "Nullable manager relationships",
        """
        SELECT
            employee_name,
            manager_id
        FROM employees
        ORDER BY employee_id;
        """,
    )


# ---------------------------------------------------------------------------
# 33. NULL AND DATE/TIME DATA
# ---------------------------------------------------------------------------

def demonstrate_date_nulls(connection):
    """
    A missing date is NULL, not a special invented date such as
    '1900-01-01' unless that value has an explicit business meaning.
    """

    show_query(
        connection,
        "Orders with missing shipment dates",
        """
        SELECT
            order_id,
            order_date,
            shipped_date
        FROM orders
        WHERE shipped_date IS NULL;
        """,
    )

    show_query(
        connection,
        "Orders that have shipped",
        """
        SELECT
            order_id,
            shipped_date
        FROM orders
        WHERE shipped_date IS NOT NULL;
        """,
    )


# ---------------------------------------------------------------------------
# 34. NULL AND BUSINESS METRICS
# ---------------------------------------------------------------------------

def demonstrate_business_metrics(connection):
    """
    Business reporting requires an explicit decision about NULL semantics.

    Example:
        revenue - discount

    produces NULL if discount is NULL.

    If NULL means "no discount", COALESCE(discount, 0) may be appropriate.
    If NULL means "discount data unavailable", replacing it with zero could
    produce a misleading metric.
    """

    show_query(
        connection,
        "Raw net amount",
        """
        SELECT
            order_id,
            amount,
            discount,
            amount - discount AS net_amount
        FROM orders;
        """,
    )

    show_query(
        connection,
        "Net amount treating missing discount as zero",
        """
        SELECT
            order_id,
            amount,
            discount,
            amount - COALESCE(discount, 0) AS net_amount
        FROM orders;
        """,
    )


# ---------------------------------------------------------------------------
# 35. NULL AND RATIOS
# ---------------------------------------------------------------------------

def demonstrate_safe_ratio(connection):
    """
    A denominator of NULL means the ratio is unknown.
    A denominator of zero is mathematically undefined.

    NULLIF can protect against division by zero.
    """

    show_query(
        connection,
        "Safe ratio pattern",
        """
        SELECT
            order_id,
            amount,
            discount,
            discount / NULLIF(amount, 0) AS discount_ratio
        FROM orders;
        """,
    )


# ---------------------------------------------------------------------------
# 36. NULL AND STRING FUNCTIONS
# ---------------------------------------------------------------------------

def demonstrate_string_functions(connection):
    """
    Many scalar functions propagate NULL.

    Example:
        LENGTH(NULL) -> NULL

    COALESCE can be applied before the function when a fallback is intended.
    """

    show_query(
        connection,
        "String functions with NULL",
        """
        SELECT
            customer_name,
            phone,
            LENGTH(phone) AS phone_length,
            LENGTH(COALESCE(phone, '')) AS fallback_length
        FROM customers;
        """,
    )


# ---------------------------------------------------------------------------
# 37. NULL AND CONCATENATION
# ---------------------------------------------------------------------------

def demonstrate_concatenation(connection):
    """
    Concatenation behavior can vary by database engine.

    SQLite's || operator propagates NULL.
    Explicit COALESCE makes the intended output clear.
    """

    show_query(
        connection,
        "Concatenation with NULL",
        """
        SELECT
            customer_name,
            city,
            customer_name || ' - ' || city AS raw_label,
            customer_name || ' - ' || COALESCE(city, 'Unknown city') AS safe_label
        FROM customers;
        """,
    )


# ---------------------------------------------------------------------------
# 38. NULL AND SUBQUERIES
# ---------------------------------------------------------------------------

def demonstrate_subqueries(connection):
    """
    Scalar subqueries can return NULL.

    Any calculation using that NULL can also become NULL.
    """

    show_query(
        connection,
        "Subquery that can produce NULL",
        """
        SELECT
            employee_name,
            salary,
            salary - (
                SELECT AVG(salary)
                FROM employees
                WHERE department = 'Nonexistent Department'
            ) AS difference_from_average
        FROM employees;
        """,
    )

    show_query(
        connection,
        "COALESCE around a nullable subquery",
        """
        SELECT
            employee_name,
            salary,
            salary - COALESCE(
                (
                    SELECT AVG(salary)
                    FROM employees
                    WHERE department = 'Nonexistent Department'
                ),
                0
            ) AS adjusted_difference
        FROM employees;
        """,
    )


# ---------------------------------------------------------------------------
# 39. EXISTS VERSUS IN
# ---------------------------------------------------------------------------

def demonstrate_exists(connection):
    """
    EXISTS checks whether a subquery returns at least one row.

    EXISTS itself does not have the same NULL trap as NOT IN.

    This is one reason NOT EXISTS is often preferred when nullable values
    can occur in the subquery.
    """

    show_query(
        connection,
        "EXISTS",
        """
        SELECT c.customer_id, c.customer_name
        FROM customers AS c
        WHERE EXISTS (
            SELECT 1
            FROM orders AS o
            WHERE o.customer_id = c.customer_id
        );
        """,
    )

    show_query(
        connection,
        "NOT EXISTS",
        """
        SELECT c.customer_id, c.customer_name
        FROM customers AS c
        WHERE NOT EXISTS (
            SELECT 1
            FROM orders AS o
            WHERE o.customer_id = c.customer_id
        );
        """,
    )


# ---------------------------------------------------------------------------
# 40. NULL AND WINDOW FUNCTIONS
# ---------------------------------------------------------------------------

def demonstrate_window_functions(connection):
    """
    Window aggregates follow aggregate NULL behavior.

    AVG(salary) OVER (...) ignores NULL salary values.
    """

    show_query(
        connection,
        "Window average by department",
        """
        SELECT
            employee_name,
            department,
            salary,
            AVG(salary) OVER (
                PARTITION BY department
            ) AS department_average
        FROM employees
        ORDER BY employee_id;
        """,
    )


# ---------------------------------------------------------------------------
# 41. NULLS IN WINDOW ORDERING
# ---------------------------------------------------------------------------

def demonstrate_window_ordering(connection):
    """NULL ordering also matters inside window functions."""

    show_query(
        connection,
        "Ranking salaries with explicit NULL ordering",
        """
        SELECT
            employee_name,
            salary,
            ROW_NUMBER() OVER (
                ORDER BY salary IS NULL, salary DESC
            ) AS salary_rank
        FROM employees;
        """,
    )


# ---------------------------------------------------------------------------
# 42. NULL AND SET OPERATIONS
# ---------------------------------------------------------------------------

def demonstrate_set_operations(connection):
    """
    UNION removes duplicates. NULL participates in duplicate elimination
    according to set-operation semantics.

    UNION ALL preserves rows exactly as produced.
    """

    show_query(
        connection,
        "UNION",
        """
        SELECT department AS value
        FROM employees
        WHERE employee_id <= 4
        UNION
        SELECT department AS value
        FROM employees
        WHERE employee_id >= 5;
        """,
    )

    show_query(
        connection,
        "UNION ALL",
        """
        SELECT department AS value
        FROM employees
        WHERE employee_id <= 4
        UNION ALL
        SELECT department AS value
        FROM employees
        WHERE employee_id >= 5;
        """,
    )


# ---------------------------------------------------------------------------
# 43. NULL AND UPDATE
# ---------------------------------------------------------------------------

def demonstrate_update(connection):
    """
    Updating NULL should use IS NULL in the predicate.

    Never write:
        WHERE bonus = NULL
    """

    connection.execute(
        """
        UPDATE employees
        SET bonus = 0
        WHERE employee_id = 2
          AND bonus IS NULL;
        """
    )
    connection.commit()

    show_query(
        connection,
        "After safely updating a NULL value",
        """
        SELECT employee_id, employee_name, bonus
        FROM employees
        WHERE employee_id = 2;
        """,
    )


# ---------------------------------------------------------------------------
# 44. NULL AND DELETE
# ---------------------------------------------------------------------------

def demonstrate_delete(connection):
    """
    DELETE also requires IS NULL for NULL matching.
    The example uses a temporary table so that the main sample data remains
    available for other demonstrations.
    """

    connection.execute(
        """
        CREATE TABLE delete_demo (
            id INTEGER,
            value TEXT
        );
        """
    )

    connection.executemany(
        "INSERT INTO delete_demo VALUES (?, ?)",
        [(1, "A"), (2, None), (3, "B")],
    )

    connection.execute(
        """
        DELETE FROM delete_demo
        WHERE value IS NULL;
        """
    )

    show_query(
        connection,
        "DELETE with IS NULL",
        """
        SELECT *
        FROM delete_demo;
        """,
    )


# ---------------------------------------------------------------------------
# 45. NULL AND INSERT
# ---------------------------------------------------------------------------

def demonstrate_insert_null(connection):
    """
    NULL can be inserted explicitly into a nullable column.
    Omitting a column can also cause NULL or a DEFAULT value depending on
    the schema.
    """

    connection.execute(
        """
        CREATE TABLE insert_demo (
            id INTEGER PRIMARY KEY,
            required_value TEXT NOT NULL,
            optional_value TEXT DEFAULT 'DEFAULT VALUE'
        );
        """
    )

    connection.execute(
        """
        INSERT INTO insert_demo(required_value)
        VALUES ('Present');
        """
    )

    connection.execute(
        """
        INSERT INTO insert_demo(required_value, optional_value)
        VALUES ('Present', NULL);
        """
    )

    show_query(
        connection,
        "Omitted column versus explicitly supplied NULL",
        """
        SELECT *
        FROM insert_demo
        ORDER BY id;
        """,
    )


# ---------------------------------------------------------------------------
# 46. DEFAULT IS NOT THE SAME AS NULL
# ---------------------------------------------------------------------------

def demonstrate_default_vs_null(connection):
    """
    A DEFAULT is applied when the column is omitted from INSERT.
    Explicitly inserting NULL normally stores NULL instead of the DEFAULT.

    This distinction is important in application/database integration.
    """

    show_query(
        connection,
        "Default versus explicit NULL",
        """
        SELECT
            id,
            required_value,
            optional_value
        FROM insert_demo;
        """,
    )


# ---------------------------------------------------------------------------
# 47. PYTHON NONE AND SQL NULL
# ---------------------------------------------------------------------------

def demonstrate_python_mapping(connection):
    """
    Python's None maps to SQL NULL through sqlite3 parameter binding.

    This is the correct way to send a NULL value from Python.
    """

    connection.execute(
        """
        CREATE TABLE python_mapping (
            id INTEGER,
            value TEXT
        );
        """
    )

    connection.execute(
        "INSERT INTO python_mapping VALUES (?, ?)",
        (1, None),
    )

    row = connection.execute(
        "SELECT id, value FROM python_mapping WHERE value IS NULL"
    ).fetchone()

    print("\nPython None -> SQL NULL:", row)

    python_value = row[1]
    print("SQL NULL -> Python:", repr(python_value))
    print("Python type:", type(python_value).__name__)


# ---------------------------------------------------------------------------
# 48. PARAMETERIZED QUERIES
# ---------------------------------------------------------------------------

def demonstrate_parameterized_null_query(connection):
    """
    A parameter containing Python None represents SQL NULL, but this still
    does not make '= ?' a valid NULL comparison.

    Incorrect:
        WHERE department = ?

    with parameter None.

    Correct:
        WHERE department IS NULL

    Some applications dynamically generate predicates based on whether the
    supplied parameter is None.
    """

    show_query(
        connection,
        "Parameterized equality with None",
        """
        SELECT employee_name, department
        FROM employees
        WHERE department = ?;
        """,
        (None,),
    )

    show_query(
        connection,
        "Explicit IS NULL predicate",
        """
        SELECT employee_name, department
        FROM employees
        WHERE department IS NULL;
        """,
    )


# ---------------------------------------------------------------------------
# 49. DYNAMIC NULL FILTERING
# ---------------------------------------------------------------------------

def find_employees_by_department(connection, department):
    """
    Build the predicate according to the meaning of the input.

    None means:
        search for rows whose department IS NULL.

    A normal string means:
        search for an ordinary department value.

    Parameters are still used for actual values.
    """
    if department is None:
        query = """
            SELECT employee_id, employee_name, department
            FROM employees
            WHERE department IS NULL
            ORDER BY employee_id;
        """
        return show_query(
            connection,
            "Dynamic search for NULL department",
            query,
        )

    query = """
        SELECT employee_id, employee_name, department
        FROM employees
        WHERE department = ?
        ORDER BY employee_id;
    """

    return show_query(
        connection,
        "Dynamic search for a known department",
        query,
        (department,),
    )


# ---------------------------------------------------------------------------
# 50. NULL AND INDEXING
# ---------------------------------------------------------------------------

def demonstrate_indexing(connection):
    """
    NULL predicates can often use indexes, but exact optimizer behavior
    depends on the database engine, index definition, statistics, query
    shape, and data distribution.

    SQLite can create an index on a nullable column.
    """

    connection.execute(
        """
        CREATE INDEX idx_employees_department
        ON employees(department);
        """
    )

    show_query(
        connection,
        "Indexed NULL lookup",
        """
        SELECT employee_id, employee_name
        FROM employees
        WHERE department IS NULL;
        """,
    )

    show_query(
        connection,
        "SQLite query plan",
        """
        EXPLAIN QUERY PLAN
        SELECT employee_id, employee_name
        FROM employees
        WHERE department IS NULL;
        """,
    )


# ---------------------------------------------------------------------------
# 51. PERFORMANCE AND COALESCE IN PREDICATES
# ---------------------------------------------------------------------------

def demonstrate_predicate_design(connection):
    """
    Compare:

        WHERE COALESCE(department, 'UNKNOWN') = 'Engineering'

    with:

        WHERE department = 'Engineering'

    The second predicate directly expresses the search for a stored value.

    Wrapping an indexed column in a function can prevent efficient index
    usage in some database systems unless a suitable functional/indexed
    expression exists.

    Do not use COALESCE in predicates merely to avoid writing correct
    NULL logic.
    """

    show_query(
        connection,
        "Direct predicate",
        """
        SELECT employee_id, employee_name
        FROM employees
        WHERE department = 'Engineering';
        """,
    )

    show_query(
        connection,
        "COALESCE predicate",
        """
        SELECT employee_id, employee_name
        FROM employees
        WHERE COALESCE(department, 'UNKNOWN') = 'Engineering';
        """,
    )


# ---------------------------------------------------------------------------
# 52. NULL SENTINELS
# ---------------------------------------------------------------------------

def demonstrate_sentinel_values(connection):
    """
    Sentinel values are artificial values used to mean "missing".

    Examples:
        -1
        0
        'UNKNOWN'
        '1900-01-01'

    They can be useful in legacy systems but create semantic problems when
    the sentinel is also a legitimate business value.

    NULL is preferable when the relational model genuinely requires
    "no known value".
    """

    connection.execute(
        """
        CREATE TABLE sentinel_demo (
            id INTEGER,
            score INTEGER
        );
        """
    )

    connection.executemany(
        "INSERT INTO sentinel_demo VALUES (?, ?)",
        [(1, 90), (2, -1), (3, None)],
    )

    show_query(
        connection,
        "Sentinel and NULL",
        """
        SELECT
            id,
            score,
            CASE
                WHEN score IS NULL THEN 'Unknown'
                WHEN score = -1 THEN 'Legacy sentinel'
                ELSE 'Known score'
            END AS interpretation
        FROM sentinel_demo;
        """,
    )


# ---------------------------------------------------------------------------
# 53. DATA QUALITY: EMPTY STRING VERSUS NULL
# ---------------------------------------------------------------------------

def demonstrate_empty_string_vs_null(connection):
    """
    NULL and empty string are different concepts.

    SQLite permits both.

    A data-quality policy should define whether:
        NULL = unknown/not supplied
        ''   = deliberately empty

    Some database systems treat empty strings differently from SQLite.
    """

    connection.execute(
        """
        CREATE TABLE text_values (
            id INTEGER,
            value TEXT
        );
        """
    )

    connection.executemany(
        "INSERT INTO text_values VALUES (?, ?)",
        [(1, None), (2, ""), (3, "Known")],
    )

    show_query(
        connection,
        "NULL versus empty string",
        """
        SELECT
            id,
            value,
            value IS NULL AS is_null,
            value = '' AS is_empty
        FROM text_values
        ORDER BY id;
        """,
    )


# ---------------------------------------------------------------------------
# 54. NULL AND LOGICAL EQUIVALENCES
# ---------------------------------------------------------------------------

def demonstrate_logical_non_equivalence(connection):
    """
    Classical Boolean algebra cannot always be applied naively to SQL
    three-valued logic.

    For example, expressions involving NULL can produce UNKNOWN rather than
    the TRUE/FALSE result expected from ordinary two-valued Boolean logic.

    SQL has optimizer rules and predicate transformations that preserve
    SQL semantics, but developers should not assume that NULL behaves like
    a normal Boolean value.
    """

    show_query(
        connection,
        "Three-valued logical expressions",
        """
        SELECT
            NULL AS value,
            NOT NULL AS not_null_expression,
            (NULL AND TRUE) AS null_and_true,
            (NULL AND FALSE) AS null_and_false,
            (NULL OR TRUE) AS null_or_true,
            (NULL OR FALSE) AS null_or_false;
        """,
    )


# ---------------------------------------------------------------------------
# 55. NULL AND IS DISTINCT FROM
# ---------------------------------------------------------------------------

def demonstrate_is_distinct_from(connection):
    """
    Standard SQL provides NULL-safe comparison concepts:

        IS DISTINCT FROM
        IS NOT DISTINCT FROM

    They treat two NULLs as equal for comparison purposes.

    SQLite versions support IS / IS NOT for similar NULL-safe comparison
    behavior. PostgreSQL and modern SQL systems may provide the standard
    IS DISTINCT FROM syntax directly.

    This section uses SQLite's portable-within-SQLite form.
    """

    show_query(
        connection,
        "SQLite NULL-safe equality",
        """
        SELECT
            NULL IS NULL AS both_null,
            10 IS 10 AS same_value,
            10 IS NULL AS value_vs_null,
            NULL IS NOT NULL AS null_distinct_from_non_null;
        """,
    )


# ---------------------------------------------------------------------------
# 56. NULL AND FULL OUTER JOIN CONCEPT
# ---------------------------------------------------------------------------

def demonstrate_full_outer_join_concept(connection):
    """
    FULL OUTER JOIN is supported by several modern SQL systems, but exact
    support differs across database engines and versions.

    Its important NULL behavior is conceptual:

        unmatched left row  -> NULL columns from right
        unmatched right row -> NULL columns from left

    SQLite versions without native FULL OUTER JOIN can emulate it using
    LEFT JOIN plus UNION.
    """

    connection.execute(
        """
        CREATE TABLE left_data (
            id INTEGER,
            value TEXT
        );

        CREATE TABLE right_data (
            id INTEGER,
            value TEXT
        );
        """
    )

    connection.executemany(
        "INSERT INTO left_data VALUES (?, ?)",
        [(1, "Left A"), (2, "Left B")],
    )

    connection.executemany(
        "INSERT INTO right_data VALUES (?, ?)",
        [(2, "Right B"), (3, "Right C")],
    )

    show_query(
        connection,
        "FULL OUTER JOIN concept using SQLite-compatible UNION",
        """
        SELECT
            l.id AS left_id,
            l.value AS left_value,
            r.id AS right_id,
            r.value AS right_value
        FROM left_data AS l
        LEFT JOIN right_data AS r
            ON l.id = r.id

        UNION

        SELECT
            l.id AS left_id,
            l.value AS left_value,
            r.id AS right_id,
            r.value AS right_value
        FROM right_data AS r
        LEFT JOIN left_data AS l
            ON l.id = r.id
        WHERE l.id IS NULL;
        """,
    )


# ---------------------------------------------------------------------------
# 57. ADVANCED REPORTING: CONDITIONAL AGGREGATION
# ---------------------------------------------------------------------------

def demonstrate_conditional_aggregation(connection):
    """
    Conditional aggregation often combines CASE, IS NULL, and COUNT.

    This makes NULL-aware data-quality reports possible.
    """

    show_query(
        connection,
        "NULL data-quality metrics",
        """
        SELECT
            COUNT(*) AS total_employees,
            SUM(CASE WHEN department IS NULL THEN 1 ELSE 0 END)
                AS missing_departments,
            SUM(CASE WHEN salary IS NULL THEN 1 ELSE 0 END)
                AS missing_salaries,
            SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END)
                AS missing_emails
        FROM employees;
        """,
    )


# ---------------------------------------------------------------------------
# 58. ADVANCED REPORTING: NULL PERCENTAGES
# ---------------------------------------------------------------------------

def demonstrate_null_percentage(connection):
    """Calculate the percentage of rows with missing salary information."""

    show_query(
        connection,
        "Percentage of missing salaries",
        """
        SELECT
            100.0 *
            SUM(CASE WHEN salary IS NULL THEN 1 ELSE 0 END)
            / NULLIF(COUNT(*), 0) AS missing_salary_percentage
        FROM employees;
        """,
    )


# ---------------------------------------------------------------------------
# 59. ADVANCED DATA CLEANING
# ---------------------------------------------------------------------------

def demonstrate_data_cleaning(connection):
    """
    A common cleaning pipeline is:

        1. Normalize empty values.
        2. Convert known sentinels to NULL.
        3. Apply a business fallback only when appropriate.
        4. Preserve the original meaning where possible.
    """

    show_query(
        connection,
        "Normalize textual missing values",
        """
        SELECT
            id,
            value,
            NULLIF(TRIM(value), '') AS normalized_value
        FROM text_values;
        """,
    )


# ---------------------------------------------------------------------------
# 60. ADVANCED NULL-AWARE CUSTOMER REPORT
# ---------------------------------------------------------------------------

def demonstrate_customer_report(connection):
    """
    A realistic reporting query combines:
        - LEFT JOIN
        - COUNT
        - COALESCE
        - IS NULL
        - GROUP BY
    """

    show_query(
        connection,
        "Customer order report",
        """
        SELECT
            c.customer_id,
            c.customer_name,
            COALESCE(c.city, 'Unknown city') AS city,
            COUNT(o.order_id) AS order_count,
            COALESCE(SUM(o.amount), 0) AS total_order_amount,
            COUNT(o.shipped_date) AS shipped_order_count
        FROM customers AS c
        LEFT JOIN orders AS o
            ON c.customer_id = o.customer_id
        GROUP BY
            c.customer_id,
            c.customer_name,
            c.city
        ORDER BY c.customer_id;
        """,
    )


# ---------------------------------------------------------------------------
# 61. ADVANCED NULL-AWARE EMPLOYEE REPORT
# ---------------------------------------------------------------------------

def demonstrate_employee_report(connection):
    """Build a NULL-aware compensation report."""

    show_query(
        connection,
        "Employee compensation report",
        """
        SELECT
            employee_name,
            COALESCE(department, 'Unassigned') AS department,
            COALESCE(salary, 0) AS salary_for_display,
            COALESCE(bonus, 0) AS bonus_for_display,
            COALESCE(salary, 0) + COALESCE(bonus, 0)
                AS displayed_total_compensation,
            CASE
                WHEN salary IS NULL THEN 'Salary missing'
                ELSE 'Salary available'
            END AS salary_data_status
        FROM employees
        ORDER BY employee_id;
        """,
    )


# ---------------------------------------------------------------------------
# 62. ADVANCED NULL-AWARE FILTER
# ---------------------------------------------------------------------------

def demonstrate_business_filter(connection):
    """
    Suppose the business rule is:

        "Find employees whose salary is at least 70,000,
         while also including employees whose salary is not yet known."

    That rule must explicitly include IS NULL.
    """

    show_query(
        connection,
        "Known high salaries plus unknown salaries",
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary >= 70000
           OR salary IS NULL
        ORDER BY employee_id;
        """,
    )


# ---------------------------------------------------------------------------
# 63. COMMON MISTAKES
# ---------------------------------------------------------------------------

def demonstrate_common_mistakes(connection):
    """
    The following mistakes are common in production SQL.

    Mistake 1:
        WHERE column = NULL

    Mistake 2:
        WHERE column <> NULL

    Mistake 3:
        NOT IN with a nullable subquery

    Mistake 4:
        Assuming NULL means zero

    Mistake 5:
        Using COALESCE without understanding its business meaning

    Mistake 6:
        Turning a LEFT JOIN into an INNER JOIN unintentionally

    Mistake 7:
        Assuming aggregate NULL behavior means "NULL becomes zero"

    Mistake 8:
        Treating empty strings and NULL as universally identical

    Mistake 9:
        Assuming NULL sorting is identical across database systems

    Mistake 10:
        Using a sentinel value when NULL is the correct semantic model
    """

    show_query(
        connection,
        "Mistake: equality against NULL",
        """
        SELECT employee_name
        FROM employees
        WHERE bonus = NULL;
        """,
    )

    show_query(
        connection,
        "Correct: IS NULL",
        """
        SELECT employee_name
        FROM employees
        WHERE bonus IS NULL;
        """,
    )


# ---------------------------------------------------------------------------
# 64. TESTS FOR NULL SEMANTICS
# ---------------------------------------------------------------------------

def run_assertion_tests(connection):
    """
    Small executable tests turn NULL rules into verifiable behavior.
    """

    cursor = connection.cursor()

    # NULL = NULL does not evaluate to TRUE.
    result = cursor.execute(
        "SELECT NULL = NULL;"
    ).fetchone()[0]
    assert result is None

    # IS NULL is explicitly TRUE for NULL.
    result = cursor.execute(
        "SELECT NULL IS NULL;"
    ).fetchone()[0]
    assert result == 1

    # IS NOT NULL is FALSE for NULL.
    result = cursor.execute(
        "SELECT NULL IS NOT NULL;"
    ).fetchone()[0]
    assert result == 0

    # COUNT(column) excludes NULL.
    result = cursor.execute(
        "SELECT COUNT(bonus) FROM employees;"
    ).fetchone()[0]
    expected = cursor.execute(
        "SELECT COUNT(*) FROM employees WHERE bonus IS NOT NULL;"
    ).fetchone()[0]
    assert result == expected

    # COALESCE returns the first non-NULL expression.
    result = cursor.execute(
        "SELECT COALESCE(NULL, NULL, 'fallback');"
    ).fetchone()[0]
    assert result == "fallback"

    # NULLIF converts equal values into NULL.
    result = cursor.execute(
        "SELECT NULLIF(5, 5);"
    ).fetchone()[0]
    assert result is None

    print("\nAll NULL semantic assertion tests passed.")


# ---------------------------------------------------------------------------
# 65. INTERACTIVE NULL LAB
# ---------------------------------------------------------------------------

def interactive_null_lab(connection):
    """
    A small reusable laboratory for experimenting with expressions.

    Enter a SQL expression without SELECT, for example:
        NULL = NULL
        NULL IS NULL
        COALESCE(NULL, 42)
        NULLIF(10, 10)

    The expression is inserted into a fixed SELECT statement.
    This function is intentionally not called automatically because user
    input is not necessary for the educational demonstration.
    """

    print(
        "\nInteractive lab available through interactive_null_lab(connection)."
    )


# ---------------------------------------------------------------------------
# 66. CONCEPTUAL DECISION TABLE
# ---------------------------------------------------------------------------

def print_decision_table():
    """Print a compact mental model for choosing NULL operators."""

    table = [
        ("Need to find missing values", "IS NULL"),
        ("Need to find present values", "IS NOT NULL"),
        ("Need a fallback value", "COALESCE(value, fallback)"),
        ("Need to turn one value into NULL", "NULLIF(value, unwanted_value)"),
        ("Need ordinary value comparison", "=, <>, <, >, <=, >="),
        ("Need NULL-safe equality", "Engine-specific / IS DISTINCT FROM family"),
        ("Need anti-join with nullable subquery", "Prefer NOT EXISTS when appropriate"),
        ("Need count of all rows", "COUNT(*)"),
        ("Need count of non-NULL values", "COUNT(column)"),
        ("Need missing-value percentage", "Conditional aggregation"),
    ]

    print("\n--- NULL Decision Table ---")
    for situation, technique in table:
        print(f"{situation:<50} -> {technique}")


# ---------------------------------------------------------------------------
# 67. PRACTICAL RULES
# ---------------------------------------------------------------------------

def print_best_practices():
    """Print production-oriented NULL handling rules."""

    rules = [
        "Use IS NULL and IS NOT NULL for NULL tests.",
        "Never rely on = NULL or <> NULL.",
        "Remember that NULL introduces UNKNOWN into SQL logic.",
        "Remember that WHERE retains only TRUE predicates.",
        "Use COALESCE only when the fallback has correct business meaning.",
        "Use NULLIF for deliberate conversion to NULL and safe division patterns.",
        "Prefer NOT EXISTS over NOT IN when nullable subquery values create risk.",
        "Distinguish COUNT(*) from COUNT(column).",
        "Check aggregate semantics before interpreting missing values as zeros.",
        "Be deliberate about NULL placement in ORDER BY.",
        "Understand LEFT JOIN behavior when filtering nullable right-side columns.",
        "Use NOT NULL constraints when data is genuinely mandatory.",
        "Do not replace NULL with arbitrary sentinel values without a clear reason.",
        "Parameterize values in application SQL; do not construct SQL with string concatenation.",
        "Test NULL cases explicitly because they often expose hidden logic errors.",
        "Check database-specific NULL behavior when writing portable SQL.",
    ]

    print("\n--- Best Practices ---")
    for index, rule in enumerate(rules, start=1):
        print(f"{index:02d}. {rule}")


# ---------------------------------------------------------------------------
# 68. MAIN PROGRAM
# ---------------------------------------------------------------------------

def main():
    connection = create_connection()

    try:
        create_sample_database(connection)

        demonstrate_null_concept(connection)
        demonstrate_three_valued_logic(connection)
        demonstrate_wrong_null_comparison(connection)
        demonstrate_is_null(connection)
        demonstrate_is_not_null(connection)
        demonstrate_where_behavior(connection)
        demonstrate_and_logic(connection)
        demonstrate_or_logic(connection)
        demonstrate_not_unknown(connection)
        demonstrate_coalesce(connection)
        demonstrate_coalesce_calculations(connection)
        demonstrate_null_arithmetic(connection)
        demonstrate_comparison_behavior(connection)
        demonstrate_in_operator(connection)
        demonstrate_not_in_subquery(connection)
        demonstrate_distinct(connection)
        demonstrate_group_by(connection)
        demonstrate_aggregates(connection)
        demonstrate_count_distinct(connection)
        demonstrate_having(connection)
        demonstrate_order_by(connection)
        demonstrate_case(connection)
        demonstrate_correct_case(connection)
        demonstrate_nullif(connection)
        demonstrate_coalesce_vs_nullif(connection)
        demonstrate_joins(connection)
        demonstrate_null_safe_join(connection)
        demonstrate_on_versus_where(connection)
        demonstrate_unique_and_null(connection)
        demonstrate_constraints(connection)
        demonstrate_foreign_keys(connection)
        demonstrate_date_nulls(connection)
        demonstrate_business_metrics(connection)
        demonstrate_safe_ratio(connection)
        demonstrate_string_functions(connection)
        demonstrate_concatenation(connection)
        demonstrate_subqueries(connection)
        demonstrate_exists(connection)
        demonstrate_window_functions(connection)
        demonstrate_window_ordering(connection)
        demonstrate_set_operations(connection)
        demonstrate_update(connection)
        demonstrate_delete(connection)
        demonstrate_insert_null(connection)
        demonstrate_default_vs_null(connection)
        demonstrate_python_mapping(connection)
        demonstrate_parameterized_null_query(connection)
        find_employees_by_department(connection, None)
        find_employees_by_department(connection, "Engineering")
        demonstrate_indexing(connection)
        demonstrate_predicate_design(connection)
        demonstrate_sentinel_values(connection)
        demonstrate_empty_string_vs_null(connection)
        demonstrate_logical_non_equivalence(connection)
        demonstrate_is_distinct_from(connection)
        demonstrate_full_outer_join_concept(connection)
        demonstrate_conditional_aggregation(connection)
        demonstrate_null_percentage(connection)
        demonstrate_data_cleaning(connection)
        demonstrate_customer_report(connection)
        demonstrate_employee_report(connection)
        demonstrate_business_filter(connection)
        demonstrate_common_mistakes(connection)

        run_assertion_tests(connection)
        print_decision_table()
        print_best_practices()

        print(
            "\n--- Completion ---\n"
            "The script has demonstrated NULL handling from basic semantics "
            "through joins, aggregation, subqueries, constraints, reporting, "
            "data cleaning, performance considerations, and production-oriented "
            "query design."
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
