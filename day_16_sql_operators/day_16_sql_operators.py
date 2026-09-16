"""
SQL Operators: Arithmetic, Comparison, Logical, BETWEEN, IN, NOT, LIKE

A standalone educational study program using Python's built-in sqlite3 module.

The program progresses from fundamental SQL operator concepts to practical
queries, edge cases, NULL behavior, pattern matching, query composition,
validation, parameterized SQL, aggregation, indexes, query planning, and
security considerations.

SQLite is used because it is included with Python and requires no external
database server or third-party package.
"""

import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable


DATABASE = ":memory:"


def print_title(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def print_rows(cursor: sqlite3.Cursor) -> None:
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    if not rows:
        print("(no rows)")
        return

    print(" | ".join(columns))
    print("-" * 78)

    for row in rows:
        print(" | ".join(str(value) if value is not None else "NULL" for value in row))


def execute_and_display(
    connection: sqlite3.Connection,
    sql: str,
    parameters: Iterable[Any] = (),
) -> None:
    print(f"\nSQL:\n{sql.strip()}")
    if parameters:
        print(f"Parameters: {tuple(parameters)}")

    cursor = connection.execute(sql, tuple(parameters))
    print_rows(cursor)


def create_database(connection: sqlite3.Connection) -> None:
    """Create a realistic employee database used throughout the lesson."""
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            salary REAL NOT NULL CHECK (salary >= 0),
            bonus REAL,
            age INTEGER NOT NULL CHECK (age >= 18),
            city TEXT NOT NULL,
            job_title TEXT NOT NULL,
            performance_score REAL,
            email TEXT,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            FOREIGN KEY (department_id) REFERENCES departments(department_id)
        );

        INSERT INTO departments (department_id, department_name) VALUES
            (1, 'Engineering'),
            (2, 'Finance'),
            (3, 'Human Resources'),
            (4, 'Security'),
            (5, 'Sales'),
            (6, 'Research');

        INSERT INTO employees
            (employee_id, employee_name, department_id, salary, bonus, age,
             city, job_title, performance_score, email, active)
        VALUES
            (1, 'Aarav Sharma', 1, 85000, 7000, 29, 'Lucknow',
             'Software Engineer', 91.5, 'aarav.sharma@example.com', 1),
            (2, 'Priya Singh', 1, 112000, 12000, 34, 'Delhi',
             'Senior Software Engineer', 96.0, 'priya.singh@example.com', 1),
            (3, 'Rohan Verma', 2, 78000, NULL, 41, 'Mumbai',
             'Financial Analyst', 82.0, 'rohan.verma@example.com', 1),
            (4, 'Neha Gupta', 3, 68000, 5000, 31, 'Lucknow',
             'HR Manager', 88.0, 'neha.gupta@example.com', 1),
            (5, 'Kabir Khan', 4, 99000, 9000, 38, 'Hyderabad',
             'Security Engineer', 93.0, 'kabir.khan@example.com', 1),
            (6, 'Ananya Rao', 5, 72000, 4000, 26, 'Bengaluru',
             'Sales Executive', 79.5, 'ananya.rao@example.com', 1),
            (7, 'Vikram Patel', 6, 125000, 18000, 45, 'Pune',
             'Research Scientist', 97.0, 'vikram.patel@example.com', 1),
            (8, 'Meera Joshi', 1, 64000, NULL, 24, 'Lucknow',
             'Junior Developer', 74.0, 'meera.joshi@example.com', 1),
            (9, 'Arjun Mehta', 5, 91000, 6000, 36, 'Delhi',
             'Sales Manager', 89.0, 'arjun.mehta@example.com', 1),
            (10, 'Sara Ali', 4, 105000, 11000, 33, 'Mumbai',
             'Cybersecurity Analyst', 94.5, 'sara.ali@example.com', 1),
            (11, 'Dev Malhotra', 2, 88000, NULL, 39, 'Pune',
             'Risk Analyst', 86.0, 'dev.malhotra@example.com', 0),
            (12, 'Ishita Kapoor', 6, 118000, 15000, 30, 'Delhi',
             'Data Scientist', 95.5, 'ishita.kapoor@example.com', 1);
        """
    )


def section_arithmetic(connection: sqlite3.Connection) -> None:
    print_title("1. Arithmetic operators")

    print(
        """
SQL arithmetic operators:

    +   addition
    -   subtraction
    *   multiplication
    /   division
    %   remainder/modulo in SQLite

Arithmetic operators normally operate on numeric expressions. They can be
used in SELECT lists, calculated columns, ORDER BY expressions, and many
other SQL expressions.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT
            employee_name,
            salary,
            bonus,
            salary + COALESCE(bonus, 0) AS total_compensation,
            salary * 12 AS annualized_monthly_equivalent,
            salary / 12 AS approximate_monthly_salary,
            age + 1 AS next_age
        FROM employees
        ORDER BY employee_id
        LIMIT 6;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT
            employee_name,
            salary,
            salary * 0.10 AS estimated_ten_percent_raise,
            salary + (salary * 0.10) AS salary_after_raise
        FROM employees
        WHERE salary > 90000
        ORDER BY salary DESC;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT
            employee_name,
            salary,
            salary % 10000 AS remainder_after_10000
        FROM employees
        ORDER BY employee_id
        LIMIT 8;
        """,
    )

    print(
        """
Important distinction:
Arithmetic calculates values. It does not itself filter rows.

For example:
    salary * 1.10

calculates a new value, while:
    salary > 90000

produces a condition that can be used by WHERE.
"""
    )


def section_comparison(connection: sqlite3.Connection) -> None:
    print_title("2. Comparison operators")

    print(
        """
Common SQL comparison operators:

    =    equal to
    <>   not equal to
    !=   not equal to, supported by SQLite
    >    greater than
    <    less than
    >=   greater than or equal to
    <=   less than or equal to

A comparison produces a logical result used by SQL expressions such as WHERE.
"""
    )

    comparisons = [
        (
            "Salary greater than 100000",
            """
            SELECT employee_name, salary
            FROM employees
            WHERE salary > 100000
            ORDER BY salary DESC;
            """,
        ),
        (
            "Salary less than or equal to 80000",
            """
            SELECT employee_name, salary
            FROM employees
            WHERE salary <= 80000
            ORDER BY salary;
            """,
        ),
        (
            "Engineering department",
            """
            SELECT employee_name, department_id
            FROM employees
            WHERE department_id = 1
            ORDER BY employee_id;
            """,
        ),
        (
            "Inactive employees using <>",
            """
            SELECT employee_name, active
            FROM employees
            WHERE active <> 1
            ORDER BY employee_id;
            """,
        ),
        (
            "Age exactly 30",
            """
            SELECT employee_name, age
            FROM employees
            WHERE age = 30;
            """,
        ),
    ]

    for description, query in comparisons:
        print(f"\n{description}")
        execute_and_display(connection, query)


def section_logical(connection: sqlite3.Connection) -> None:
    print_title("3. Logical operators: AND, OR, NOT")

    print(
        """
AND:
All combined conditions must be true.

OR:
At least one combined condition must be true.

NOT:
Negates a logical condition.

Parentheses are important when several logical operators appear together.
SQL precedence commonly makes NOT bind more tightly than AND, and AND more
tightly than OR. Explicit parentheses make intent much clearer.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, salary, age
        FROM employees
        WHERE salary > 90000
          AND age < 40
        ORDER BY salary DESC;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, city, department_id
        FROM employees
        WHERE city = 'Lucknow'
           OR city = 'Delhi'
        ORDER BY employee_name;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, active
        FROM employees
        WHERE NOT (active = 1)
        ORDER BY employee_id;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, salary, age, city
        FROM employees
        WHERE (salary > 100000 OR age >= 40)
          AND city <> 'Lucknow'
        ORDER BY employee_name;
        """,
    )

    print(
        """
Common precedence mistake:

    WHERE city = 'Delhi'
       OR city = 'Lucknow'
       AND salary > 90000

is interpreted approximately as:

    WHERE city = 'Delhi'
       OR (city = 'Lucknow' AND salary > 90000)

If the intended meaning is that both cities must also satisfy the salary
condition, write:

    WHERE (city = 'Delhi' OR city = 'Lucknow')
      AND salary > 90000
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, salary, city
        FROM employees
        WHERE (city = 'Delhi' OR city = 'Lucknow')
          AND salary > 90000
        ORDER BY salary DESC;
        """,
    )


def section_between(connection: sqlite3.Connection) -> None:
    print_title("4. BETWEEN and NOT BETWEEN")

    print(
        """
BETWEEN tests whether a value lies within an inclusive range.

    value BETWEEN lower AND upper

is equivalent in meaning to:

    value >= lower AND value <= upper

The endpoints are included.

NOT BETWEEN is the negated range condition.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary BETWEEN 80000 AND 100000
        ORDER BY salary;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, age
        FROM employees
        WHERE age NOT BETWEEN 30 AND 40
        ORDER BY age;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        WHERE performance_score BETWEEN 90 AND 100
        ORDER BY performance_score DESC;
        """,
    )

    print(
        """
For dates, BETWEEN is also inclusive. When timestamps contain times,
care is required because the upper boundary can unintentionally exclude
records later on the upper date.

For example, instead of relying on:

    timestamp BETWEEN '2026-01-01' AND '2026-01-31'

a half-open interval is often safer:

    timestamp >= '2026-01-01'
    AND timestamp < '2026-02-01'

The exact approach depends on the database and timestamp representation.
"""
    )


def section_in(connection: sqlite3.Connection) -> None:
    print_title("5. IN and NOT IN")

    print(
        """
IN tests membership in a list of values.

    city IN ('Delhi', 'Lucknow', 'Mumbai')

is conceptually similar to:

    city = 'Delhi'
    OR city = 'Lucknow'
    OR city = 'Mumbai'

NOT IN tests non-membership.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city IN ('Delhi', 'Lucknow', 'Mumbai')
        ORDER BY city, employee_name;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, department_id
        FROM employees
        WHERE department_id NOT IN (2, 3)
        ORDER BY department_id, employee_name;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, job_title
        FROM employees
        WHERE job_title IN (
            'Data Scientist',
            'Security Engineer',
            'Cybersecurity Analyst'
        )
        ORDER BY employee_name;
        """,
    )

    print(
        """
Important NULL edge case:

NOT IN can behave unexpectedly if the list or subquery contains NULL.

For example:

    value NOT IN (1, 2, NULL)

does not simply mean "value is neither 1 nor 2". SQL's three-valued logic
can cause the result to become UNKNOWN.

When NOT IN is used with a subquery, make sure NULL handling is intentional.
For anti-joins, NOT EXISTS is often a safer alternative.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city NOT IN ('Delhi', 'Lucknow')
        ORDER BY employee_name;
        """,
    )


def section_not(connection: sqlite3.Connection) -> None:
    print_title("6. NOT with other predicates")

    execute_and_display(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE NOT (salary > 100000)
        ORDER BY salary;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE NOT city IN ('Delhi', 'Mumbai')
        ORDER BY employee_name;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, age
        FROM employees
        WHERE NOT (age BETWEEN 30 AND 40)
        ORDER BY age;
        """,
    )

    print(
        """
NOT is useful, but explicit positive conditions can sometimes be easier to
read and reason about.

Also remember that NOT does not turn UNKNOWN into TRUE. NULL participates in
SQL's three-valued logic.
"""
    )


def section_like(connection: sqlite3.Connection) -> None:
    print_title("7. LIKE pattern matching")

    print(
        """
LIKE performs pattern matching.

SQLite's common wildcards include:

    %   zero or more characters
    _   exactly one character

Examples:

    'A%'     starts with A
    '%a'     ends with a
    '%an%'   contains an
    '_a%'    second character is a

LIKE is different from =. Equality compares values; LIKE interprets
wildcards as pattern syntax.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name
        FROM employees
        WHERE employee_name LIKE 'A%'
        ORDER BY employee_name;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, email
        FROM employees
        WHERE email LIKE '%@example.com'
        ORDER BY employee_name;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, job_title
        FROM employees
        WHERE job_title LIKE '%Engineer%'
        ORDER BY employee_name;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name
        FROM employees
        WHERE employee_name LIKE '_e%'
        ORDER BY employee_name;
        """,
    )

    print(
        """
LIKE and indexes:
A pattern such as 'A%' may be optimizable in appropriate database
configurations because the prefix is known.

A pattern such as '%Engineer%' begins with a wildcard, so ordinary B-tree
index usage is generally much less effective.

Case sensitivity is database-specific. SQLite's default LIKE behavior has
specific ASCII case-insensitivity characteristics. Production applications
should not assume identical LIKE semantics across PostgreSQL, MySQL,
SQL Server, Oracle, and SQLite.
"""
    )


def section_null_logic(connection: sqlite3.Connection) -> None:
    print_title("8. NULL and three-valued logic")

    print(
        """
NULL means "missing", "unknown", or "not available"; it is not the same as
zero, an empty string, or FALSE.

SQL conditions can evaluate to:

    TRUE
    FALSE
    UNKNOWN

WHERE keeps rows for which the condition evaluates to TRUE.

Do not write:

    bonus = NULL

or:

    bonus <> NULL

Use IS NULL or IS NOT NULL instead.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, bonus
        FROM employees
        WHERE bonus IS NULL
        ORDER BY employee_id;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, bonus
        FROM employees
        WHERE bonus IS NOT NULL
        ORDER BY employee_id;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT
            employee_name,
            bonus,
            bonus + 1000 AS incorrect_for_missing_bonus,
            COALESCE(bonus, 0) + 1000 AS explicit_missing_bonus_policy
        FROM employees
        WHERE employee_id IN (1, 3, 8);
        """,
    )

    print(
        """
Arithmetic with NULL generally propagates NULL.

For example:

    NULL + 1000

is NULL.

COALESCE can explicitly choose a replacement value:

    COALESCE(bonus, 0)
"""
    )


def section_case(connection: sqlite3.Connection) -> None:
    print_title("9. Combining operators with CASE")

    print(
        """
CASE is not itself one of the requested operators, but it is important
because operator-based conditions are often used inside CASE expressions.

This example creates compensation bands.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT
            employee_name,
            salary,
            CASE
                WHEN salary >= 120000 THEN 'Executive / Principal Range'
                WHEN salary BETWEEN 90000 AND 119999.99 THEN 'Senior Range'
                WHEN salary BETWEEN 70000 AND 89999.99 THEN 'Professional Range'
                ELSE 'Entry Range'
            END AS salary_band
        FROM employees
        ORDER BY salary DESC;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT
            employee_name,
            performance_score,
            CASE
                WHEN performance_score IS NULL THEN 'Not Rated'
                WHEN performance_score >= 90 THEN 'High'
                WHEN performance_score >= 75 THEN 'Medium'
                ELSE 'Low'
            END AS performance_band
        FROM employees
        ORDER BY employee_name;
        """,
    )


def section_subqueries(connection: sqlite3.Connection) -> None:
    print_title("10. Operators with subqueries")

    print(
        """
Operators become particularly useful when the comparison value comes from
another query.

The following query finds employees whose salary is above the average salary.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary > (
            SELECT AVG(salary)
            FROM employees
        )
        ORDER BY salary DESC;
        """,
    )

    print(
        """
IN can also consume a subquery.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, department_id
        FROM employees
        WHERE department_id IN (
            SELECT department_id
            FROM departments
            WHERE department_name LIKE '%Engineering%'
               OR department_name LIKE '%Research%'
        )
        ORDER BY department_id, employee_name;
        """,
    )


def section_exists(connection: sqlite3.Connection) -> None:
    print_title("11. EXISTS and NOT EXISTS")

    print(
        """
EXISTS is not one of the named operator families in the requested topic,
but it is closely related to IN and is important for advanced SQL.

EXISTS asks whether a subquery produces at least one matching row.

It can be particularly useful for correlated existence tests.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT d.department_name
        FROM departments AS d
        WHERE EXISTS (
            SELECT 1
            FROM employees AS e
            WHERE e.department_id = d.department_id
              AND e.active = 1
        )
        ORDER BY d.department_name;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT d.department_name
        FROM departments AS d
        WHERE NOT EXISTS (
            SELECT 1
            FROM employees AS e
            WHERE e.department_id = d.department_id
              AND e.salary > 120000
        )
        ORDER BY d.department_name;
        """,
    )


def section_aggregate_filters(connection: sqlite3.Connection) -> None:
    print_title("12. Operators with aggregation and HAVING")

    print(
        """
WHERE filters individual rows before grouping.

HAVING filters groups after aggregation.

Operator conditions can therefore appear at different stages of a query.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT
            department_id,
            COUNT(*) AS employee_count,
            AVG(salary) AS average_salary
        FROM employees
        WHERE active = 1
        GROUP BY department_id
        HAVING AVG(salary) BETWEEN 80000 AND 120000
        ORDER BY average_salary DESC;
        """,
    )


def section_parameterized_queries(connection: sqlite3.Connection) -> None:
    print_title("13. Parameterized SQL and safe operator usage")

    print(
        """
Do not construct SQL by concatenating untrusted input.

Bad approach conceptually:

    "SELECT ... WHERE city = '" + user_input + "'"

A malicious value can change the SQL syntax.

Use parameterized statements instead. Python's sqlite3 driver sends the value
separately from the SQL statement.
"""
    )

    requested_city = "Delhi"
    minimum_salary = 85000

    execute_and_display(
        connection,
        """
        SELECT employee_name, city, salary
        FROM employees
        WHERE city = ?
          AND salary >= ?
        ORDER BY salary DESC;
        """,
        (requested_city, minimum_salary),
    )

    print(
        """
Parameters are for values, not arbitrary SQL identifiers.

For example, this is not generally valid:

    ORDER BY ?

If a user is allowed to choose a sort column, map a small approved set of
application-level names to known SQL identifiers instead of inserting raw
input.
"""
    )


def section_dynamic_filters(connection: sqlite3.Connection) -> None:
    print_title("14. Building dynamic operator-based filters safely")

    print(
        """
Real applications often allow optional filters.

The safe pattern is:
1. Start with a trusted base statement.
2. Add trusted SQL fragments selected by application logic.
3. Put user-supplied values into parameters.
4. Never interpolate raw user input into SQL syntax.
"""
    )

    filters = []
    parameters: list[Any] = []

    minimum_salary = 80000
    maximum_salary = 120000
    cities = ["Delhi", "Lucknow", "Pune"]

    filters.append("salary BETWEEN ? AND ?")
    parameters.extend([minimum_salary, maximum_salary])

    placeholders = ", ".join("?" for _ in cities)
    filters.append(f"city IN ({placeholders})")
    parameters.extend(cities)

    filters.append("active = ?")
    parameters.append(1)

    query = f"""
        SELECT employee_name, salary, city, active
        FROM employees
        WHERE {" AND ".join(filters)}
        ORDER BY salary DESC;
    """

    execute_and_display(connection, query, parameters)


def section_operator_precedence(connection: sqlite3.Connection) -> None:
    print_title("15. Operator precedence and explicit parentheses")

    print(
        """
A simplified mental model for many SQL expressions is:

    arithmetic expressions
        ↓
    comparisons
        ↓
    NOT
        ↓
    AND
        ↓
    OR

Exact precedence details can vary by database and operator family.

Parentheses should be used when the intended grouping is important.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, city, salary
        FROM employees
        WHERE city = 'Delhi'
           OR city = 'Lucknow'
          AND salary >= 90000
        ORDER BY employee_name;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT employee_name, city, salary
        FROM employees
        WHERE (city = 'Delhi' OR city = 'Lucknow')
          AND salary >= 90000
        ORDER BY employee_name;
        """,
    )

    print(
        """
The two queries above intentionally demonstrate different meanings.
Do not rely on readers remembering precedence when parentheses can make the
business rule explicit.
"""
    )


def section_expression_alias(connection: sqlite3.Connection) -> None:
    print_title("16. Operators in calculated business metrics")

    execute_and_display(
        connection,
        """
        SELECT
            employee_name,
            salary,
            COALESCE(bonus, 0) AS bonus,
            salary + COALESCE(bonus, 0) AS total_compensation,
            ROUND(
                (salary + COALESCE(bonus, 0)) / salary * 100,
                2
            ) AS compensation_index_percent
        FROM employees
        WHERE salary > 0
        ORDER BY total_compensation DESC;
        """,
    )

    execute_and_display(
        connection,
        """
        SELECT
            employee_name,
            salary,
            performance_score,
            ROUND(
                salary / 1000.0
                + COALESCE(performance_score, 0) * 10,
                2
            ) AS illustrative_internal_score
        FROM employees
        WHERE performance_score >= 80
          AND salary BETWEEN 70000 AND 130000
        ORDER BY illustrative_internal_score DESC;
        """,
    )


def section_edge_cases(connection: sqlite3.Connection) -> None:
    print_title("17. Edge cases and subtle behaviors")

    print(
        """
1. Division:
Database-specific behavior matters for division by zero. Never assume
behavior is identical across SQL engines.

2. NULL:
Comparisons involving NULL generally produce UNKNOWN rather than TRUE/FALSE.

3. Type conversion:
Different databases have different rules for implicit type conversion.

4. Floating-point values:
Exact equality on calculated floating-point values can be problematic.
Prefer suitable numeric types and comparison strategies for financial data.

5. LIKE:
Case sensitivity and collation depend on database configuration.

6. NOT IN:
NULL values in a subquery can produce surprising UNKNOWN results.

7. Empty IN lists:
Some SQL dialects reject an empty IN list. Application code should handle
empty collections explicitly.

8. Dates:
BETWEEN is inclusive. Timestamp boundaries need careful design.
"""
    )

    execute_and_display(
        connection,
        """
        SELECT
            employee_name,
            salary,
            salary > 100000 AS is_high_salary,
            salary BETWEEN 80000 AND 100000 AS is_mid_salary,
            city IN ('Delhi', 'Mumbai') AS is_selected_city,
            city LIKE 'L%' AS city_starts_with_l
        FROM employees
        ORDER BY employee_id
        LIMIT 8;
        """,
    )


def section_query_plans(connection: sqlite3.Connection) -> None:
    print_title("18. Performance and query planning")

    print(
        """
Indexes can make comparisons and filtering substantially faster when the
database can use them effectively.

The following index supports frequent salary filtering.
"""
    )

    connection.execute(
        "CREATE INDEX idx_employees_salary ON employees(salary)"
    )

    execute_and_display(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT employee_name, salary
        FROM employees
        WHERE salary >= 100000;
        """,
    )

    print(
        """
Performance considerations:

- Index columns frequently used for selective filtering when justified.
- Avoid indexing every column indiscriminately.
- Indexes consume storage and increase write/update cost.
- Composite index order matters.
- Functions applied to indexed columns can affect index usage.
- Leading-wildcard LIKE patterns are generally difficult for ordinary
  B-tree indexes.
- Always measure query performance on realistic data.
- Use the database's query-plan tools rather than guessing.
"""
    )


def section_comparison_table() -> None:
    print_title("19. Operator comparison reference")

    rows = [
        ("+", "Arithmetic", "salary + bonus", "Calculates a value"),
        ("-", "Arithmetic", "salary - deduction", "Calculates a value"),
        ("*", "Arithmetic", "salary * 1.10", "Calculates a value"),
        ("/", "Arithmetic", "salary / 12", "Calculates a value"),
        ("%", "Arithmetic", "age % 2", "Remainder"),
        ("=", "Comparison", "city = 'Delhi'", "Equality test"),
        ("<> / !=", "Comparison", "salary <> 0", "Inequality test"),
        (">", "Comparison", "salary > 90000", "Greater than"),
        ("<", "Comparison", "age < 40", "Less than"),
        (">=", "Comparison", "salary >= 90000", "Greater/equal"),
        ("<=", "Comparison", "age <= 40", "Less/equal"),
        ("AND", "Logical", "salary > 80000 AND active = 1", "All conditions"),
        ("OR", "Logical", "city = 'Delhi' OR city = 'Pune'", "Any condition"),
        ("NOT", "Logical", "NOT active = 1", "Negation"),
        ("BETWEEN", "Range", "salary BETWEEN 80000 AND 100000", "Inclusive range"),
        ("IN", "Membership", "city IN ('Delhi', 'Pune')", "List membership"),
        ("LIKE", "Pattern", "name LIKE 'A%'", "Pattern matching"),
        ("IS NULL", "NULL test", "bonus IS NULL", "Missing/unknown value"),
        ("IS NOT NULL", "NULL test", "bonus IS NOT NULL", "Known value"),
    ]

    print(f"{'Operator':<15} {'Family':<15} {'Example':<42} Meaning")
    print("-" * 110)
    for operator, family, example, meaning in rows:
        print(f"{operator:<15} {family:<15} {example:<42} {meaning}")


@dataclass
class EmployeeFilter:
    """A small application-level representation of filter requirements."""

    minimum_salary: float | None = None
    maximum_salary: float | None = None
    allowed_cities: tuple[str, ...] = ()
    active_only: bool = True
    name_pattern: str | None = None


def run_filter_application(
    connection: sqlite3.Connection,
    employee_filter: EmployeeFilter,
) -> None:
    print_title("20. Mini application: operator-driven employee search")

    conditions = []
    parameters: list[Any] = []

    if employee_filter.minimum_salary is not None:
        conditions.append("salary >= ?")
        parameters.append(employee_filter.minimum_salary)

    if employee_filter.maximum_salary is not None:
        conditions.append("salary <= ?")
        parameters.append(employee_filter.maximum_salary)

    if employee_filter.allowed_cities:
        placeholders = ", ".join("?" for _ in employee_filter.allowed_cities)
        conditions.append(f"city IN ({placeholders})")
        parameters.extend(employee_filter.allowed_cities)

    if employee_filter.active_only:
        conditions.append("active = ?")
        parameters.append(1)

    if employee_filter.name_pattern is not None:
        conditions.append("employee_name LIKE ?")
        parameters.append(employee_filter.name_pattern)

    where_clause = " AND ".join(conditions) if conditions else "1 = 1"

    query = f"""
        SELECT
            employee_name,
            salary,
            city,
            job_title,
            active
        FROM employees
        WHERE {where_clause}
        ORDER BY salary DESC, employee_name ASC;
    """

    execute_and_display(connection, query, parameters)


def demonstrate_python_side_equivalence(connection: sqlite3.Connection) -> None:
    print_title("21. SQL operators versus Python expressions")

    print(
        """
Python and SQL use related but not identical expression syntax.

Examples:

SQL:
    salary >= 90000 AND active = 1

Python:
    salary >= 90000 and active == 1

SQL:
    city IN ('Delhi', 'Pune')

Python:
    city in ('Delhi', 'Pune')

SQL:
    bonus IS NULL

Python:
    bonus is None

The important lesson is not to assume that operators have identical syntax
or identical NULL/three-valued-logic behavior in every language.
"""
    )

    employee = connection.execute(
        """
        SELECT salary, active, city, bonus
        FROM employees
        WHERE employee_id = 1
        """
    ).fetchone()

    salary, active, city, bonus = employee

    python_condition = salary >= 90000 and active == 1
    python_membership = city in ("Delhi", "Pune")
    python_missing = bonus is None

    print(f"Employee values: salary={salary}, active={active}, city={city}")
    print(f"Python salary/active condition: {python_condition}")
    print(f"Python membership condition: {python_membership}")
    print(f"Python NULL-equivalent test: {python_missing}")


def test_queries(connection: sqlite3.Connection) -> None:
    print_title("22. Lightweight validation tests")

    high_salary_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM employees
        WHERE salary > 100000
        """
    ).fetchone()[0]

    assert high_salary_count == 3, "Unexpected high-salary count"

    null_bonus_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM employees
        WHERE bonus IS NULL
        """
    ).fetchone()[0]

    assert null_bonus_count == 3, "Unexpected NULL-bonus count"

    delhi_or_lucknow_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM employees
        WHERE city IN ('Delhi', 'Lucknow')
        """
    ).fetchone()[0]

    assert delhi_or_lucknow_count == 5, "Unexpected city membership count"

    between_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM employees
        WHERE salary BETWEEN 80000 AND 100000
        """
    ).fetchone()[0]

    assert between_count == 4, "BETWEEN is expected to be inclusive"

    print("All educational query tests passed.")


def security_notes() -> None:
    print_title("23. Security principles")

    print(
        """
SQL operators themselves are not an injection vulnerability. Unsafe SQL
construction is.

Primary rules:

- Parameterize values.
- Validate application-level filter choices.
- Use allowlists for dynamic column names and sort directions.
- Avoid concatenating raw request parameters into SQL.
- Give database users only the permissions they need.
- Avoid exposing detailed database errors directly to untrusted users.
- Log useful diagnostic information without leaking credentials or secrets.
- Treat LIKE patterns as user input and consider performance implications.
- Apply pagination to large result sets.
"""
    )


def main() -> None:
    print_title("SQL Operators: Complete Practical Study")

    print(
        """
This program demonstrates:

- Arithmetic operators
- Comparison operators
- AND, OR, and NOT
- BETWEEN and NOT BETWEEN
- IN and NOT IN
- LIKE and wildcards
- NULL and three-valued logic
- CASE with operator-based conditions
- Subqueries
- EXISTS and NOT EXISTS
- Aggregation and HAVING
- Parameterized SQL
- Dynamic filters
- Operator precedence
- Business calculations
- Edge cases
- Query planning and indexes
- Security considerations
- Lightweight testing
"""
    )

    connection = sqlite3.connect(DATABASE)

    try:
        create_database(connection)

        section_arithmetic(connection)
        section_comparison(connection)
        section_logical(connection)
        section_between(connection)
        section_in(connection)
        section_not(connection)
        section_like(connection)
        section_null_logic(connection)
        section_case(connection)
        section_subqueries(connection)
        section_exists(connection)
        section_aggregate_filters(connection)
        section_parameterized_queries(connection)
        section_dynamic_filters(connection)
        section_operator_precedence(connection)
        section_expression_alias(connection)
        section_edge_cases(connection)
        section_query_plans(connection)
        section_comparison_table()

        employee_filter = EmployeeFilter(
            minimum_salary=85000,
            maximum_salary=120000,
            allowed_cities=("Delhi", "Lucknow", "Mumbai"),
            active_only=True,
            name_pattern="%a%",
        )
        run_filter_application(connection, employee_filter)

        demonstrate_python_side_equivalence(connection)
        test_queries(connection)
        security_notes()

        print_title("24. End of executable study")
        print(
            """
The database remains entirely in memory, so running this file does not
create an external database file.

The most important practical distinction is:

Arithmetic operators calculate values.
Comparison operators create conditions.
Logical operators combine conditions.
BETWEEN expresses inclusive ranges.
IN expresses membership.
NOT negates conditions.
LIKE performs pattern matching.
IS NULL / IS NOT NULL handle SQL's NULL semantics.
"""
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
