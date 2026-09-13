"""
SQL Sorting Results: ORDER BY, ASC, DESC, Multiple-Column Sorting, and NULL Ordering
====================================================================================

A self-contained study script using Python's built-in sqlite3 module.

This script teaches SQL result ordering from absolute beginner through advanced
practical usage. SQLite is used so every SQL example can be executed without
installing an external database package.

Topics covered:
    1. Creating and populating a relational table
    2. SELECT and unordered result sets
    3. ORDER BY fundamentals
    4. ASC and DESC
    5. Sorting numbers, text, and dates
    6. Sorting by aliases and expressions
    7. Multiple-column sorting
    8. Tie-breaking behavior
    9. NULL values
    10. SQLite NULL ordering behavior
    11. Explicit NULLS FIRST / NULLS LAST
    12. Portable NULL-ordering techniques
    13. CASE-based custom ordering
    14. LIMIT and OFFSET with ORDER BY
    15. Pagination and deterministic ordering
    16. Aggregation followed by ordering
    17. Window functions and ordered analytical results
    18. Conditional and calculated sorting
    19. Collation and case-sensitive ordering
    20. Common mistakes
    21. Performance and indexes
    22. Security considerations
    23. Testing sorting behavior
    24. Advanced practical patterns
"""

import sqlite3
from datetime import datetime


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def print_section(title):
    """Print a readable section heading."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_rows(description, rows):
    """Display SQL result rows in a compact, readable form."""
    print(f"\n{description}")
    for row in rows:
        print(dict(row))


def execute_and_print(connection, sql, parameters=(), description="Query result"):
    """
    Execute a parameterized SQL statement and print all returned rows.

    Parameterized queries are used whenever values originate outside the SQL
    statement itself. This is important for avoiding SQL injection.
    """
    cursor = connection.execute(sql, parameters)
    rows = cursor.fetchall()
    print_rows(description, rows)
    return rows


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def create_database():
    """
    Create an in-memory SQLite database.

    An in-memory database disappears when the connection closes, making this
    script self-contained and safe for repeated execution.
    """
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.execute(
        """
        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            department TEXT NOT NULL,
            salary REAL NOT NULL,
            hire_date TEXT NOT NULL,
            performance_score REAL,
            bonus REAL,
            manager_id INTEGER,
            employment_status TEXT NOT NULL
        )
        """
    )

    employees = [
        (1, "Aarav", "Engineering", 95000, "2021-04-12", 91.5, 12000, None, "Active"),
        (2, "Meera", "Finance", 82000, "2020-01-20", 88.0, 9000, None, "Active"),
        (3, "Kabir", "Engineering", 105000, "2019-08-03", 95.0, 15000, 1, "Active"),
        (4, "Isha", "Marketing", 76000, "2022-06-15", None, 5000, None, "Active"),
        (5, "Rohan", "Engineering", 95000, "2023-02-10", 91.5, None, 3, "Active"),
        (6, "Ananya", "Finance", 88000, "2021-11-18", 93.0, 10000, 2, "Active"),
        (7, "Vihaan", "Marketing", 76000, "2020-09-27", 84.0, 4000, 4, "Active"),
        (8, "Diya", "Engineering", 72000, "2024-01-05", 79.5, None, 1, "Probation"),
        (9, "Arjun", "Finance", 88000, "2022-03-14", None, 7000, 2, "Active"),
        (10, "Sara", "HR", 68000, "2018-07-21", 90.0, 3000, None, "Active"),
        (11, "Neel", "HR", 68000, "2023-07-11", 90.0, None, 10, "Probation"),
        (12, "Tara", "Marketing", 83000, "2019-12-09", 87.0, 6000, 4, "Active"),
    ]

    connection.executemany(
        """
        INSERT INTO employees (
            employee_id,
            employee_name,
            department,
            salary,
            hire_date,
            performance_score,
            bonus,
            manager_id,
            employment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        employees,
    )

    connection.commit()
    return connection


# ---------------------------------------------------------------------------
# 1. Why ordering matters
# ---------------------------------------------------------------------------

def demonstrate_unordered_results(connection):
    print_section("1. SELECT does not guarantee a business-defined order")

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, salary
        FROM employees
        """,
        description="Rows without ORDER BY",
    )

    print(
        "\nImportant principle:"
        "\nSQL tables represent sets of rows. If an application needs a specific"
        "\norder, that order should be explicitly requested with ORDER BY."
    )


# ---------------------------------------------------------------------------
# 2. Basic ORDER BY
# ---------------------------------------------------------------------------

def demonstrate_basic_order_by(connection):
    print_section("2. Basic ORDER BY")

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, salary
        FROM employees
        ORDER BY salary
        """,
        description="Salary sorted in ascending order",
    )

    print(
        "\nORDER BY salary is ascending by default in SQLite."
        "\nWriting ASC explicitly is clearer when teaching or documenting intent."
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, salary
        FROM employees
        ORDER BY salary ASC
        """,
        description="Explicit ASC",
    )


# ---------------------------------------------------------------------------
# 3. ASC and DESC
# ---------------------------------------------------------------------------

def demonstrate_asc_desc(connection):
    print_section("3. ASC versus DESC")

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, salary
        FROM employees
        ORDER BY salary ASC
        """,
        description="Lowest salary first",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, salary
        FROM employees
        ORDER BY salary DESC
        """,
        description="Highest salary first",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, hire_date
        FROM employees
        ORDER BY hire_date ASC
        """,
        description="Oldest hire date first",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, hire_date
        FROM employees
        ORDER BY hire_date DESC
        """,
        description="Most recent hire date first",
    )

    print(
        "\nASC generally means ascending order:"
        "\n  numbers: smallest -> largest"
        "\n  dates: earliest -> latest"
        "\n  text: according to the active collation"
        "\n\nDESC reverses that ordering."
    )


# ---------------------------------------------------------------------------
# 4. Ordering text
# ---------------------------------------------------------------------------

def demonstrate_text_sorting(connection):
    print_section("4. Sorting text values")

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, department
        FROM employees
        ORDER BY employee_name ASC
        """,
        description="Employee names A-Z",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, department
        FROM employees
        ORDER BY employee_name DESC
        """,
        description="Employee names Z-A",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, department
        FROM employees
        ORDER BY department ASC, employee_name ASC
        """,
        description="Departments alphabetically, then employees alphabetically",
    )


# ---------------------------------------------------------------------------
# 5. Multiple-column sorting
# ---------------------------------------------------------------------------

def demonstrate_multiple_column_sorting(connection):
    print_section("5. Multiple-column sorting")

    print(
        "\nORDER BY can contain several expressions."
        "\nThe database sorts by the first expression."
        "\nRows tied on the first expression are then sorted by the second."
        "\nThe process continues from left to right."
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, department, salary
        FROM employees
        ORDER BY department ASC, salary DESC
        """,
        description="Department A-Z, salary highest-first within each department",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, department, salary
        FROM employees
        ORDER BY salary DESC, employee_name ASC
        """,
        description="Salary highest-first, employee name as tie-breaker",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, department, salary, hire_date
        FROM employees
        ORDER BY department ASC, salary DESC, hire_date ASC
        """,
        description="Three-level ordering",
    )


# ---------------------------------------------------------------------------
# 6. Tie-breaking
# ---------------------------------------------------------------------------

def demonstrate_tie_breaking(connection):
    print_section("6. Tie-breaking and deterministic ordering")

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, department, salary
        FROM employees
        WHERE salary = 88000
        ORDER BY salary DESC
        """,
        description="Rows tied on salary",
    )

    print(
        "\nIf two rows have equal values for every ORDER BY expression,"
        "\ntheir relative order should not be treated as meaningful."
        "\nFor deterministic application behavior, add a unique tie-breaker."
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, department, salary
        FROM employees
        WHERE salary = 88000
        ORDER BY salary DESC, employee_id ASC
        """,
        description="Deterministic tie-breaking with employee_id",
    )


# ---------------------------------------------------------------------------
# 7. Ordering by aliases
# ---------------------------------------------------------------------------

def demonstrate_alias_sorting(connection):
    print_section("7. ORDER BY aliases and calculated expressions")

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            salary,
            salary * 0.10 AS estimated_bonus
        FROM employees
        ORDER BY estimated_bonus DESC
        """,
        description="Sort by a SELECT-list alias",
    )

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            salary,
            COALESCE(bonus, 0) AS effective_bonus
        FROM employees
        ORDER BY effective_bonus DESC
        """,
        description="Sort by a calculated alias",
    )

    print(
        "\nAn alias defined in SELECT can often be referenced by ORDER BY."
        "\nThis can make complex calculated ordering more readable."
    )


# ---------------------------------------------------------------------------
# 8. Expressions in ORDER BY
# ---------------------------------------------------------------------------

def demonstrate_expression_sorting(connection):
    print_section("8. Sorting by expressions")

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            salary,
            bonus,
            salary + COALESCE(bonus, 0) AS total_compensation
        FROM employees
        ORDER BY salary + COALESCE(bonus, 0) DESC
        """,
        description="Sort by total compensation",
    )

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            performance_score,
            salary
        FROM employees
        ORDER BY
            CASE
                WHEN performance_score IS NULL THEN 1
                ELSE 0
            END,
            performance_score DESC
        """,
        description="Known performance scores first, highest score first",
    )


# ---------------------------------------------------------------------------
# 9. NULL fundamentals
# ---------------------------------------------------------------------------

def demonstrate_null_basics(connection):
    print_section("9. Understanding NULL")

    print(
        """
NULL does not mean:
    - zero
    - an empty string
    - false
    - the text 'NULL'

NULL represents an unknown, missing, or inapplicable value.

Because NULL represents an absence of a known value, comparisons involving
NULL use SQL's three-valued logic.

For example:
    performance_score = NULL

is not the correct test.

Use:
    performance_score IS NULL

or:
    performance_score IS NOT NULL
"""
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        WHERE performance_score IS NULL
        """,
        description="Employees with NULL performance scores",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        WHERE performance_score IS NOT NULL
        ORDER BY performance_score DESC
        """,
        description="Employees with known performance scores",
    )


# ---------------------------------------------------------------------------
# 10. Default NULL ordering
# ---------------------------------------------------------------------------

def demonstrate_default_null_ordering(connection):
    print_section("10. NULL ordering")

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        ORDER BY performance_score ASC
        """,
        description="Ascending performance score with SQLite's default NULL behavior",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        ORDER BY performance_score DESC
        """,
        description="Descending performance score with SQLite's default NULL behavior",
    )

    print(
        """
SQLite's default behavior places NULL values before non-NULL values for
ascending ORDER BY and after non-NULL values for descending ORDER BY.

This behavior is database-specific enough that portable SQL should make the
desired NULL placement explicit rather than assuming every database behaves
the same way.
"""
    )


# ---------------------------------------------------------------------------
# 11. NULLS FIRST and NULLS LAST
# ---------------------------------------------------------------------------

def demonstrate_nulls_first_last(connection):
    print_section("11. Explicit NULLS FIRST and NULLS LAST")

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        ORDER BY performance_score ASC NULLS FIRST
        """,
        description="Lowest scores first, NULL values first",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        ORDER BY performance_score ASC NULLS LAST
        """,
        description="Lowest scores first, NULL values last",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        ORDER BY performance_score DESC NULLS FIRST
        """,
        description="Highest scores first, NULL values first",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        ORDER BY performance_score DESC NULLS LAST
        """,
        description="Highest scores first, NULL values last",
    )


# ---------------------------------------------------------------------------
# 12. Portable NULL ordering with CASE
# ---------------------------------------------------------------------------

def demonstrate_portable_null_ordering(connection):
    print_section("12. Explicit NULL placement using CASE")

    print(
        """
A CASE expression can be used when explicit NULLS FIRST / NULLS LAST syntax
is unavailable or when more complicated business ordering is required.

Pattern for NULLS LAST:
    ORDER BY
        CASE WHEN column_name IS NULL THEN 1 ELSE 0 END,
        column_name ASC

Pattern for NULLS FIRST:
    ORDER BY
        CASE WHEN column_name IS NULL THEN 0 ELSE 1 END,
        column_name ASC
"""
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        ORDER BY
            CASE WHEN performance_score IS NULL THEN 1 ELSE 0 END,
            performance_score ASC
        """,
        description="Portable-style NULLS LAST",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        ORDER BY
            CASE WHEN performance_score IS NULL THEN 0 ELSE 1 END,
            performance_score ASC
        """,
        description="Portable-style NULLS FIRST",
    )


# ---------------------------------------------------------------------------
# 13. NULL ordering with multiple columns
# ---------------------------------------------------------------------------

def demonstrate_nulls_with_multiple_columns(connection):
    print_section("13. NULL ordering in multi-column sorting")

    execute_and_print(
        connection,
        """
        SELECT employee_name, department, performance_score, bonus
        FROM employees
        ORDER BY
            department ASC,
            CASE WHEN performance_score IS NULL THEN 1 ELSE 0 END,
            performance_score DESC,
            employee_id ASC
        """,
        description="Department, then known performance scores, then deterministic ID",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, department, performance_score, bonus
        FROM employees
        ORDER BY
            CASE WHEN bonus IS NULL THEN 1 ELSE 0 END,
            bonus DESC,
            employee_name ASC
        """,
        description="Bonus descending with missing bonuses last",
    )


# ---------------------------------------------------------------------------
# 14. LIMIT and OFFSET
# ---------------------------------------------------------------------------

def demonstrate_limit_offset(connection):
    print_section("14. ORDER BY with LIMIT and OFFSET")

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 5
        """,
        description="Top five salaries",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 5 OFFSET 5
        """,
        description="Second page of five rows",
    )

    print(
        """
LIMIT without ORDER BY does not mean "top" rows in a business sense.

For example:
    SELECT ... LIMIT 5

does not reliably mean:
    "give me the five highest values."

The correct form is:
    SELECT ...
    ORDER BY some_column DESC
    LIMIT 5
"""
    )


# ---------------------------------------------------------------------------
# 15. Pagination
# ---------------------------------------------------------------------------

def demonstrate_pagination(connection):
    print_section("15. Deterministic pagination")

    page_size = 4

    for page_number in range(1, 4):
        offset = (page_number - 1) * page_size

        execute_and_print(
            connection,
            """
            SELECT employee_id, employee_name, salary
            FROM employees
            ORDER BY salary DESC, employee_id ASC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
            description=f"Page {page_number}",
        )

    print(
        """
A stable pagination query should normally contain a unique final tie-breaker.

For example:
    ORDER BY salary DESC, employee_id ASC

If employee_id is unique, two rows cannot remain tied after all sorting
expressions have been evaluated.
"""
    )


# ---------------------------------------------------------------------------
# 16. Aggregation followed by ORDER BY
# ---------------------------------------------------------------------------

def demonstrate_aggregation_ordering(connection):
    print_section("16. GROUP BY results can also be ordered")

    execute_and_print(
        connection,
        """
        SELECT
            department,
            COUNT(*) AS employee_count,
            AVG(salary) AS average_salary
        FROM employees
        GROUP BY department
        ORDER BY average_salary DESC
        """,
        description="Departments ordered by average salary",
    )

    execute_and_print(
        connection,
        """
        SELECT
            department,
            COUNT(*) AS employee_count,
            SUM(salary) AS total_salary
        FROM employees
        GROUP BY department
        ORDER BY employee_count DESC, total_salary DESC
        """,
        description="Departments ordered by headcount, then total salary",
    )

    print(
        "\nORDER BY can sort grouped results using aggregate expressions or aliases."
    )


# ---------------------------------------------------------------------------
# 17. HAVING and ORDER BY
# ---------------------------------------------------------------------------

def demonstrate_having_and_ordering(connection):
    print_section("17. WHERE, GROUP BY, HAVING, and ORDER BY")

    execute_and_print(
        connection,
        """
        SELECT
            department,
            COUNT(*) AS employee_count,
            AVG(salary) AS average_salary
        FROM employees
        WHERE employment_status = 'Active'
        GROUP BY department
        HAVING AVG(salary) >= 75000
        ORDER BY average_salary DESC
        """,
        description="Filtered, grouped, restricted, and sorted departments",
    )

    print(
        """
A useful conceptual execution order is:

    FROM
    WHERE
    GROUP BY
    HAVING
    SELECT
    ORDER BY
    LIMIT / OFFSET

The exact internal optimizer behavior can differ, but this logical order
helps explain why ORDER BY works with SELECT aliases and aggregate results.
"""
    )


# ---------------------------------------------------------------------------
# 18. Custom business ordering
# ---------------------------------------------------------------------------

def demonstrate_custom_ordering(connection):
    print_section("18. Custom business ordering with CASE")

    execute_and_print(
        connection,
        """
        SELECT employee_name, employment_status, department
        FROM employees
        ORDER BY
            CASE employment_status
                WHEN 'Active' THEN 1
                WHEN 'Probation' THEN 2
                ELSE 3
            END,
            employee_name ASC
        """,
        description="Active employees first, probation employees second",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, department, salary
        FROM employees
        ORDER BY
            CASE department
                WHEN 'Engineering' THEN 1
                WHEN 'Finance' THEN 2
                WHEN 'Marketing' THEN 3
                WHEN 'HR' THEN 4
                ELSE 5
            END,
            salary DESC
        """,
        description="Business-defined department order",
    )

    print(
        """
Alphabetical ordering is not always the required business order.

CASE allows a domain-specific ranking to become the primary sort key.
"""
    )


# ---------------------------------------------------------------------------
# 19. Collation and text ordering
# ---------------------------------------------------------------------------

def demonstrate_collation(connection):
    print_section("19. Collation and text sorting")

    connection.execute(
        """
        CREATE TABLE names_for_sorting (
            name TEXT NOT NULL
        )
        """
    )

    names = [
        ("alice",),
        ("Bob",),
        ("charlie",),
        ("ALAN",),
        ("bob",),
    ]

    connection.executemany(
        "INSERT INTO names_for_sorting (name) VALUES (?)",
        names,
    )

    execute_and_print(
        connection,
        """
        SELECT name
        FROM names_for_sorting
        ORDER BY name ASC
        """,
        description="Default text ordering",
    )

    execute_and_print(
        connection,
        """
        SELECT name
        FROM names_for_sorting
        ORDER BY name COLLATE NOCASE ASC
        """,
        description="Case-insensitive ordering using SQLite NOCASE",
    )

    print(
        """
Text sorting depends on collation rules.

Case handling, accent handling, language-specific alphabetical rules, and
Unicode behavior can differ between database systems and collations.

For international applications, the selected collation should be treated
as part of the application's data-ordering requirements.
"""
    )


# ---------------------------------------------------------------------------
# 20. Sorting dates
# ---------------------------------------------------------------------------

def demonstrate_date_sorting(connection):
    print_section("20. Date and time sorting")

    print(
        """
The sample database stores dates as ISO-formatted text:

    YYYY-MM-DD

Lexicographic ordering of consistently formatted ISO dates matches
chronological ordering.

This works because:
    2020-01-20 < 2021-04-12 < 2024-01-05

For more complicated timestamps, timezone-aware data and database-specific
date/time types or functions should be considered carefully.
"""
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, hire_date
        FROM employees
        ORDER BY hire_date ASC
        """,
        description="Oldest hire dates first",
    )


# ---------------------------------------------------------------------------
# 21. Sorting by position
# ---------------------------------------------------------------------------

def demonstrate_ordinal_ordering(connection):
    print_section("21. ORDER BY select-list position")

    execute_and_print(
        connection,
        """
        SELECT employee_name, department, salary
        FROM employees
        ORDER BY 3 DESC, 1 ASC
        """,
        description="Sort using SELECT-list positions",
    )

    print(
        """
Some SQL systems allow ORDER BY 1, ORDER BY 2, and so on to refer to
SELECT-list positions.

Although valid in many systems, named columns or aliases are usually clearer
and safer because changing the SELECT-list order can silently change the
meaning of the query.
"""
    )


# ---------------------------------------------------------------------------
# 22. Sorting with DISTINCT
# ---------------------------------------------------------------------------

def demonstrate_distinct_ordering(connection):
    print_section("22. DISTINCT and ORDER BY")

    execute_and_print(
        connection,
        """
        SELECT DISTINCT department
        FROM employees
        ORDER BY department ASC
        """,
        description="Distinct departments alphabetically",
    )

    execute_and_print(
        connection,
        """
        SELECT DISTINCT department
        FROM employees
        ORDER BY department DESC
        """,
        description="Distinct departments reverse alphabetically",
    )

    print(
        "\nDISTINCT removes duplicate result rows before the final result is presented."
    )


# ---------------------------------------------------------------------------
# 23. Top-N and bottom-N patterns
# ---------------------------------------------------------------------------

def demonstrate_top_bottom_patterns(connection):
    print_section("23. Top-N and bottom-N patterns")

    execute_and_print(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 3
        """,
        description="Top three salaries",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        ORDER BY salary ASC, employee_id ASC
        LIMIT 3
        """,
        description="Bottom three salaries",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        WHERE performance_score IS NOT NULL
        ORDER BY performance_score DESC, employee_id ASC
        LIMIT 3
        """,
        description="Top three known performance scores",
    )


# ---------------------------------------------------------------------------
# 24. Window functions
# ---------------------------------------------------------------------------

def demonstrate_window_ordering(connection):
    print_section("24. Window functions and ORDER BY")

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            department,
            salary,
            RANK() OVER (
                PARTITION BY department
                ORDER BY salary DESC
            ) AS salary_rank
        FROM employees
        ORDER BY department ASC, salary_rank ASC, employee_id ASC
        """,
        description="Salary rank within each department",
    )

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            department,
            salary,
            ROW_NUMBER() OVER (
                PARTITION BY department
                ORDER BY salary DESC, employee_id ASC
            ) AS row_number_in_department
        FROM employees
        ORDER BY department ASC, row_number_in_department ASC
        """,
        description="Deterministic row numbering within departments",
    )

    print(
        """
There are two different ORDER BY concepts here:

1. ORDER BY inside OVER(...)
   This determines the order used by the window function.

2. The outer ORDER BY
   This determines the order of the final result set.

They serve different purposes and should not be confused.
"""
    )


# ---------------------------------------------------------------------------
# 25. Ranking differences
# ---------------------------------------------------------------------------

def demonstrate_ranking_functions(connection):
    print_section("25. ROW_NUMBER, RANK, and DENSE_RANK")

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            salary,
            ROW_NUMBER() OVER (ORDER BY salary DESC, employee_id ASC) AS row_number,
            RANK() OVER (ORDER BY salary DESC) AS rank_number,
            DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rank_number
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        """,
        description="Comparison of ranking functions",
    )

    print(
        """
ROW_NUMBER:
    Every row receives a unique sequential number.

RANK:
    Tied values receive the same rank and later ranks contain gaps.

DENSE_RANK:
    Tied values receive the same rank, but later ranks have no gaps.

The ORDER BY expression inside each window determines what counts as a tie.
"""
    )


# ---------------------------------------------------------------------------
# 26. NULL-safe business ranking
# ---------------------------------------------------------------------------

def demonstrate_advanced_null_ranking(connection):
    print_section("26. Advanced NULL-aware ranking")

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            performance_score,
            CASE
                WHEN performance_score IS NULL THEN 0
                ELSE 1
            END AS has_score,
            RANK() OVER (
                ORDER BY
                    CASE WHEN performance_score IS NULL THEN 1 ELSE 0 END,
                    performance_score DESC
            ) AS performance_rank
        FROM employees
        ORDER BY performance_rank ASC, employee_id ASC
        """,
        description="Known scores ranked before unknown scores",
    )


# ---------------------------------------------------------------------------
# 27. Sorting with COALESCE
# ---------------------------------------------------------------------------

def demonstrate_coalesce_sorting(connection):
    print_section("27. COALESCE and sorting")

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            bonus,
            COALESCE(bonus, 0) AS displayed_bonus
        FROM employees
        ORDER BY COALESCE(bonus, 0) DESC, employee_id ASC
        """,
        description="Treat NULL bonuses as zero for a calculated ordering",
    )

    print(
        """
COALESCE can be useful when NULL should have a specific business meaning.

But it must be used carefully.

Treating NULL as zero is correct only when:
    "missing bonus" and "zero bonus"

are equivalent for the business rule.

If NULL means "not yet calculated", converting it to zero may hide useful
information.
"""
    )


# ---------------------------------------------------------------------------
# 28. Security: parameters versus identifiers
# ---------------------------------------------------------------------------

def demonstrate_safe_dynamic_sorting(connection):
    print_section("28. Safe dynamic sorting")

    print(
        """
ORDER BY values such as ASC/DESC or column identifiers cannot generally be
supplied as ordinary value parameters.

Unsafe approach:
    Constructing arbitrary SQL directly from user input.

Safer approach:
    Map approved application choices to fixed SQL fragments.
"""
    )

    allowed_sort_columns = {
        "name": "employee_name",
        "salary": "salary",
        "department": "department",
        "hire_date": "hire_date",
    }

    allowed_directions = {
        "asc": "ASC",
        "desc": "DESC",
    }

    requested_column = "salary"
    requested_direction = "desc"

    column_sql = allowed_sort_columns.get(requested_column)
    direction_sql = allowed_directions.get(requested_direction)

    if column_sql is None or direction_sql is None:
        raise ValueError("Invalid sort option")

    sql = f"""
        SELECT employee_id, employee_name, department, salary
        FROM employees
        ORDER BY {column_sql} {direction_sql}, employee_id ASC
    """

    execute_and_print(
        connection,
        sql,
        description="Safely constructed ORDER BY from an allow-list",
    )

    print(
        """
The f-string is safe here only because column_sql and direction_sql came
from fixed allow-lists rather than being inserted directly from arbitrary
user input.

Use parameter binding for values:

    WHERE salary >= ?

Do not assume that:

    ORDER BY ?

will substitute a column name.
"""
    )


# ---------------------------------------------------------------------------
# 29. SQL injection demonstration concept
# ---------------------------------------------------------------------------

def demonstrate_injection_concept():
    print_section("29. Why dynamic ORDER BY requires validation")

    print(
        """
Suppose a web application accepts:

    sort_column
    sort_direction

It is dangerous to concatenate unchecked input:

    ORDER BY <raw user input>

A malicious value could attempt to alter the SQL statement.

The correct architecture is:

    external input
        |
        v
    validate against allowed choices
        |
        v
    select a predefined SQL identifier/direction
        |
        v
    execute the query

For ordinary data values, use parameterized SQL.
For identifiers and syntax fragments that cannot be parameters, use strict
allow-lists.
"""
    )


# ---------------------------------------------------------------------------
# 30. Query planning and indexes
# ---------------------------------------------------------------------------

def demonstrate_index_for_sorting(connection):
    print_section("30. Performance and indexes")

    connection.execute(
        """
        CREATE INDEX idx_employees_salary
        ON employees (salary)
        """
    )

    connection.execute(
        """
        CREATE INDEX idx_employees_department_salary
        ON employees (department, salary DESC)
        """
    )

    connection.commit()

    execute_and_print(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT employee_id, employee_name, department, salary
        FROM employees
        ORDER BY department ASC, salary DESC
        """,
        description="Query plan for an indexed multi-column ORDER BY",
    )

    print(
        """
Sorting can become expensive for large result sets.

An index can sometimes help the database produce rows in the requested
order without performing a separate full sort.

Whether an index helps depends on:
    - database engine
    - index definition
    - WHERE predicates
    - ORDER BY columns
    - column directions
    - selectivity
    - table size
    - requested result size
    - optimizer decisions

Indexes are not automatically beneficial. They consume storage and increase
the cost of INSERT, UPDATE, and DELETE operations.
"""
    )


# ---------------------------------------------------------------------------
# 31. Composite index ordering
# ---------------------------------------------------------------------------

def demonstrate_composite_index_principle():
    print_section("31. Composite index principle")

    print(
        """
Consider an index conceptually defined as:

    (department, salary)

It is naturally useful for ordering by:

    department
    department, salary

It is generally not equivalent to having a separate index beginning with
salary.

The leading-column principle matters.

For multi-column ORDER BY clauses, index design should be evaluated together
with the application's WHERE conditions and common access patterns.
"""
    )


# ---------------------------------------------------------------------------
# 32. Offset pagination limitation
# ---------------------------------------------------------------------------

def demonstrate_offset_pagination_limitation():
    print_section("32. OFFSET pagination trade-off")

    print(
        """
LIMIT/OFFSET is simple:

    ORDER BY salary DESC, employee_id ASC
    LIMIT 20 OFFSET 1000

For very large offsets, the database may still need to locate and skip many
rows before returning the requested page.

A common alternative is keyset or cursor pagination.

For a descending salary ordering with employee_id as a tie-breaker, a later
page can conceptually request:

    salary < previous_salary
    OR (
        salary = previous_salary
        AND employee_id > previous_employee_id
    )

This can be more efficient for large datasets when an appropriate index
exists, but it requires more application logic.
"""
    )


# ---------------------------------------------------------------------------
# 33. Keyset pagination implementation
# ---------------------------------------------------------------------------

def demonstrate_keyset_pagination(connection):
    print_section("33. Keyset pagination example")

    first_page = execute_and_print(
        connection,
        """
        SELECT employee_id, employee_name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 4
        """,
        description="First keyset page",
    )

    if first_page:
        last_row = first_page[-1]
        last_salary = last_row["salary"]
        last_employee_id = last_row["employee_id"]

        execute_and_print(
            connection,
            """
            SELECT employee_id, employee_name, salary
            FROM employees
            WHERE
                salary < ?
                OR (
                    salary = ?
                    AND employee_id > ?
                )
            ORDER BY salary DESC, employee_id ASC
            LIMIT 4
            """,
            (last_salary, last_salary, last_employee_id),
            description="Next page using the previous page's final key",
        )


# ---------------------------------------------------------------------------
# 34. Edge cases
# ---------------------------------------------------------------------------

def demonstrate_edge_cases(connection):
    print_section("34. Important edge cases")

    print(
        """
Edge case 1: all values are equal.
    A secondary sort key becomes important.

Edge case 2: many NULL values.
    Decide explicitly whether NULL belongs at the beginning or end.

Edge case 3: empty result set.
    ORDER BY still works, but no rows are returned.

Edge case 4: one row.
    Sorting has no visible effect.

Edge case 5: mixed data quality.
    Text that represents numbers should not be assumed to sort numerically.

Edge case 6: text collation.
    Case and language-specific rules can change visible ordering.

Edge case 7: pagination under changing data.
    Inserts and updates between requests can cause OFFSET pages to shift.

Edge case 8: non-unique ordering.
    Without a deterministic tie-breaker, applications should not assume
    stable row positions across executions.
"""
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE department = 'Nonexistent'
        ORDER BY salary DESC
        """,
        description="Empty result set",
    )


# ---------------------------------------------------------------------------
# 35. Common mistakes
# ---------------------------------------------------------------------------

def demonstrate_common_mistakes():
    print_section("35. Common ORDER BY mistakes")

    print(
        """
Mistake 1:
    Assuming database insertion order is guaranteed.

Correction:
    Use ORDER BY.

Mistake 2:
    Writing LIMIT without ORDER BY and calling the result "top N".

Correction:
    ORDER BY metric DESC before LIMIT.

Mistake 3:
    Assuming NULL means zero.

Correction:
    Decide what NULL means and encode that rule explicitly.

Mistake 4:
    Using:
        column = NULL

Correction:
        column IS NULL

Mistake 5:
    Sorting by only a non-unique column when deterministic pagination is needed.

Correction:
    Add a unique tie-breaker.

Mistake 6:
    Building an ORDER BY clause directly from raw user input.

Correction:
    Allow-list column names and directions.

Mistake 7:
    Assuming all database systems have identical NULL ordering behavior.

Correction:
    Use explicit NULL ordering where supported or CASE-based ordering.

Mistake 8:
    Using SELECT-list ordinal positions such as ORDER BY 1 without considering
    maintainability.

Correction:
    Prefer meaningful column names or aliases.

Mistake 9:
    Treating NULL and zero as interchangeable without a business justification.

Correction:
    Preserve semantic meaning when it matters.

Mistake 10:
    Expecting an index to automatically eliminate every sorting cost.

Correction:
    Inspect the query plan and benchmark realistic workloads.
"""
    )


# ---------------------------------------------------------------------------
# 36. Comparison table in executable data
# ---------------------------------------------------------------------------

def demonstrate_sorting_patterns():
    print_section("36. Sorting pattern reference")

    patterns = [
        ("Ascending", "ORDER BY salary ASC", "Smallest/highest lexical priority first"),
        ("Descending", "ORDER BY salary DESC", "Largest/highest lexical priority first"),
        ("Two columns", "ORDER BY department ASC, salary DESC", "Department then salary"),
        ("NULLS LAST", "ORDER BY score ASC NULLS LAST", "Known scores first"),
        ("NULLS FIRST", "ORDER BY score ASC NULLS FIRST", "Missing scores first"),
        (
            "Portable NULLS LAST",
            "ORDER BY CASE WHEN score IS NULL THEN 1 ELSE 0 END, score ASC",
            "Explicit CASE ranking",
        ),
        (
            "Tie-breaker",
            "ORDER BY salary DESC, employee_id ASC",
            "Deterministic ordering",
        ),
        (
            "Top N",
            "ORDER BY salary DESC LIMIT 10",
            "Highest ten rows",
        ),
        (
            "Custom business order",
            "ORDER BY CASE status WHEN 'Active' THEN 1 ELSE 2 END",
            "Domain-specific priority",
        ),
    ]

    for name, syntax, purpose in patterns:
        print(f"\n{name}")
        print(f"  SQL:     {syntax}")
        print(f"  Purpose: {purpose}")


# ---------------------------------------------------------------------------
# 37. Testing sorting invariants
# ---------------------------------------------------------------------------

def demonstrate_sorting_tests(connection):
    print_section("37. Testing ORDER BY behavior")

    rows = connection.execute(
        """
        SELECT salary
        FROM employees
        ORDER BY salary ASC
        """
    ).fetchall()

    salaries = [row["salary"] for row in rows]

    assert salaries == sorted(salaries), "Ascending salary order failed"

    rows_desc = connection.execute(
        """
        SELECT salary
        FROM employees
        ORDER BY salary DESC
        """
    ).fetchall()

    salaries_desc = [row["salary"] for row in rows_desc]

    assert salaries_desc == sorted(salaries_desc, reverse=True), (
        "Descending salary order failed"
    )

    rows_tie = connection.execute(
        """
        SELECT employee_id, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        """
    ).fetchall()

    previous = None

    for row in rows_tie:
        current = (row["salary"], -row["employee_id"])

        if previous is not None:
            assert previous >= current

        previous = current

    null_last_rows = connection.execute(
        """
        SELECT performance_score
        FROM employees
        ORDER BY performance_score ASC NULLS LAST
        """
    ).fetchall()

    values = [row["performance_score"] for row in null_last_rows]
    non_null_values = [value for value in values if value is not None]

    assert non_null_values == sorted(non_null_values)
    assert all(value is None for value in values[len(non_null_values):])

    print(
        "\nAll sorting assertions passed."
        "\nTests verified ascending order, descending order, tie-breaking,"
        "\nand explicit NULLS LAST behavior."
    )


# ---------------------------------------------------------------------------
# 38. Real-world examples
# ---------------------------------------------------------------------------

def demonstrate_real_world_queries(connection):
    print_section("38. Real-world sorting patterns")

    execute_and_print(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 10
        """,
        description="Highest-paid employees",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, hire_date
        FROM employees
        ORDER BY hire_date ASC, employee_id ASC
        LIMIT 5
        """,
        description="Longest-serving employees",
    )

    execute_and_print(
        connection,
        """
        SELECT employee_name, performance_score
        FROM employees
        ORDER BY
            CASE WHEN performance_score IS NULL THEN 1 ELSE 0 END,
            performance_score DESC,
            employee_id ASC
        LIMIT 5
        """,
        description="Top known performers, unknown scores last",
    )

    execute_and_print(
        connection,
        """
        SELECT
            employee_name,
            salary,
            COALESCE(bonus, 0) AS bonus,
            salary + COALESCE(bonus, 0) AS total_compensation
        FROM employees
        ORDER BY total_compensation DESC, employee_id ASC
        LIMIT 5
        """,
        description="Top total compensation",
    )

    execute_and_print(
        connection,
        """
        SELECT
            department,
            COUNT(*) AS employee_count,
            ROUND(AVG(salary), 2) AS average_salary
        FROM employees
        GROUP BY department
        ORDER BY employee_count DESC, average_salary DESC
        """,
        description="Departments ranked by employee count",
    )


# ---------------------------------------------------------------------------
# 39. SQL logical ordering and ORDER BY
# ---------------------------------------------------------------------------

def demonstrate_logical_query_processing():
    print_section("39. Logical relationship between SQL clauses")

    print(
        """
A useful conceptual model is:

FROM
    Determines the source rows.

WHERE
    Filters individual rows.

GROUP BY
    Forms groups.

HAVING
    Filters groups.

SELECT
    Defines the output expressions.

ORDER BY
    Arranges the final result rows.

LIMIT/OFFSET
    Restricts the requested portion of the ordered result.

Example:

    SELECT
        department,
        AVG(salary) AS average_salary
    FROM employees
    WHERE employment_status = 'Active'
    GROUP BY department
    HAVING AVG(salary) >= 75000
    ORDER BY average_salary DESC
    LIMIT 3

The ORDER BY occurs after grouping in the logical query model, so the query
can sort departments using the calculated average salary.
"""
    )


# ---------------------------------------------------------------------------
# 40. Production design considerations
# ---------------------------------------------------------------------------

def demonstrate_production_considerations():
    print_section("40. Production considerations")

    print(
        """
For production systems, ORDER BY should be designed around the actual
business requirement.

Questions to answer:

1. What does "first" mean?
   Highest value, lowest value, newest record, oldest record, priority,
   alphabetical order, or a custom business ranking?

2. What should happen to NULL?
   Missing values may belong first, last, or in a separate category.

3. Is the ordering deterministic?
   If users paginate, export, compare results, or cache results, a unique
   tie-breaker is often important.

4. Is the query large?
   Large sorts can consume memory and CPU.

5. Can an index support the common access pattern?
   Check actual query plans.

6. Is the sort dynamic?
   Use an allow-list for SQL identifiers and directions.

7. Is the order locale-sensitive?
   Choose an appropriate collation.

8. Does the application require stable pagination?
   Consider keyset pagination for large datasets.

9. Is NULL semantically different from zero or an empty string?
   Preserve that distinction.

10. Does the query expose sensitive data?
    Sorting itself is not authorization. Access control must be applied
    independently of ordering.
"""
    )


# ---------------------------------------------------------------------------
# 41. Final integrated example
# ---------------------------------------------------------------------------

def demonstrate_integrated_query(connection):
    print_section("41. Integrated advanced query")

    sql = """
        SELECT
            employee_id,
            employee_name,
            department,
            salary,
            performance_score,
            COALESCE(bonus, 0) AS effective_bonus,
            salary + COALESCE(bonus, 0) AS total_compensation,
            CASE
                WHEN performance_score >= 95 THEN 'Exceptional'
                WHEN performance_score >= 90 THEN 'Strong'
                WHEN performance_score >= 80 THEN 'Solid'
                WHEN performance_score IS NULL THEN 'Unrated'
                ELSE 'Needs Review'
            END AS performance_category
        FROM employees
        WHERE employment_status IN ('Active', 'Probation')
        ORDER BY
            CASE
                WHEN performance_score IS NULL THEN 1
                ELSE 0
            END ASC,
            performance_score DESC,
            total_compensation DESC,
            department ASC,
            employee_name ASC,
            employee_id ASC
        LIMIT 10
    """

    execute_and_print(
        connection,
        sql,
        description="Integrated NULL-aware, multi-column, deterministic ranking",
    )

    print(
        """
This query combines several important ideas:

    - filtering with WHERE
    - handling NULL with CASE
    - descending numerical ordering
    - calculated values with COALESCE
    - aliases in ORDER BY
    - multiple sorting levels
    - deterministic tie-breaking
    - LIMIT for a top-N style result

The ordering hierarchy is intentional. Earlier ORDER BY expressions have
higher priority than later expressions.
"""
    )


# ---------------------------------------------------------------------------
# 42. Quick reference
# ---------------------------------------------------------------------------

def demonstrate_quick_reference():
    print_section("42. ORDER BY quick reference")

    print(
        """
Basic:
    SELECT ... FROM table
    ORDER BY column ASC;

Descending:
    SELECT ... FROM table
    ORDER BY column DESC;

Multiple columns:
    ORDER BY column_a ASC, column_b DESC;

NULLS FIRST:
    ORDER BY column ASC NULLS FIRST;

NULLS LAST:
    ORDER BY column ASC NULLS LAST;

CASE-based NULLS LAST:
    ORDER BY
        CASE WHEN column IS NULL THEN 1 ELSE 0 END,
        column ASC;

Tie-breaker:
    ORDER BY score DESC, id ASC;

Top N:
    ORDER BY score DESC, id ASC
    LIMIT 10;

Pagination:
    ORDER BY score DESC, id ASC
    LIMIT 10 OFFSET 20;

Custom order:
    ORDER BY
        CASE status
            WHEN 'High' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 3
            ELSE 4
        END;

Aggregate ordering:
    GROUP BY department
    ORDER BY AVG(salary) DESC;

Window ordering:
    RANK() OVER (
        PARTITION BY department
        ORDER BY salary DESC
    );
"""
    )


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------

def main():
    print(
        """
SQL Sorting Results
===================
ORDER BY, ASC, DESC, Multiple-Column Sorting, and NULL Ordering

This executable lesson uses SQLite through Python's standard library.
"""
    )

    connection = create_database()

    try:
        demonstrate_unordered_results(connection)
        demonstrate_basic_order_by(connection)
        demonstrate_asc_desc(connection)
        demonstrate_text_sorting(connection)
        demonstrate_multiple_column_sorting(connection)
        demonstrate_tie_breaking(connection)
        demonstrate_alias_sorting(connection)
        demonstrate_expression_sorting(connection)
        demonstrate_null_basics(connection)
        demonstrate_default_null_ordering(connection)
        demonstrate_nulls_first_last(connection)
        demonstrate_portable_null_ordering(connection)
        demonstrate_nulls_with_multiple_columns(connection)
        demonstrate_limit_offset(connection)
        demonstrate_pagination(connection)
        demonstrate_aggregation_ordering(connection)
        demonstrate_having_and_ordering(connection)
        demonstrate_custom_ordering(connection)
        demonstrate_collation(connection)
        demonstrate_date_sorting(connection)
        demonstrate_ordinal_ordering(connection)
        demonstrate_distinct_ordering(connection)
        demonstrate_top_bottom_patterns(connection)
        demonstrate_window_ordering(connection)
        demonstrate_ranking_functions(connection)
        demonstrate_advanced_null_ranking(connection)
        demonstrate_coalesce_sorting(connection)
        demonstrate_safe_dynamic_sorting(connection)
        demonstrate_injection_concept()
        demonstrate_index_for_sorting(connection)
        demonstrate_composite_index_principle()
        demonstrate_offset_pagination_limitation()
        demonstrate_keyset_pagination(connection)
        demonstrate_edge_cases(connection)
        demonstrate_common_mistakes()
        demonstrate_sorting_patterns()
        demonstrate_sorting_tests(connection)
        demonstrate_real_world_queries(connection)
        demonstrate_logical_query_processing()
        demonstrate_production_considerations()
        demonstrate_integrated_query(connection)
        demonstrate_quick_reference()

        print_section("Completed")
        print(
            "The complete ORDER BY lesson executed successfully, including "
            "basic, multi-column, NULL-aware, analytical, performance, "
            "security, pagination, and testing examples."
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
