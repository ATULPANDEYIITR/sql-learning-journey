"""
LIMIT, OFFSET, FETCH, AND PAGINATION FUNDAMENTALS
=================================================

A self-contained study program for learning how databases limit result sets.

This script uses Python's built-in sqlite3 module so that the examples can
run without installing an external package.

Topics covered
--------------
1. Why limiting database results matters
2. LIMIT
3. OFFSET
4. LIMIT + OFFSET pagination
5. FETCH concepts and SQL dialect differences
6. Deterministic ordering
7. Page-number pagination
8. Keyset/cursor pagination
9. Offset versus keyset pagination
10. First-page, middle-page, and last-page behavior
11. Edge cases and validation
12. NULL ordering considerations
13. Filtering before limiting
14. Aggregation and limiting
15. DISTINCT and limiting
16. JOINs and limiting
17. Top-N queries
18. Pagination consistency problems
19. Performance considerations
20. Large OFFSET problems
21. Indexing
22. SQL injection considerations
23. API-style pagination
24. Testing pagination behavior
25. Production-oriented pagination helpers

SQLite does not implement the SQL-standard FETCH FIRST syntax in the same
form as systems such as PostgreSQL, SQL Server, Oracle, and DB2. Therefore,
this script demonstrates the standard concept with executable SQLite
equivalents and also shows representative FETCH syntax as strings for study.

Run:
    python limiting_results.py
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Sequence


# =============================================================================
# 1. DATABASE SETUP
# =============================================================================

def create_connection() -> sqlite3.Connection:
    """Create an in-memory database and configure useful SQLite behavior."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Create tables used throughout the examples."""
    connection.executescript(
        """
        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            salary INTEGER NOT NULL,
            hire_year INTEGER NOT NULL
        );

        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        );
        """
    )


def insert_sample_data(connection: sqlite3.Connection) -> None:
    """Insert deterministic sample data."""
    employees = [
        (1, "Aarav", "Engineering", 95000, 2020),
        (2, "Bhavna", "Finance", 85000, 2021),
        (3, "Chirag", "Engineering", 110000, 2019),
        (4, "Diya", "Marketing", 72000, 2022),
        (5, "Esha", "Engineering", 98000, 2023),
        (6, "Farhan", "Finance", 91000, 2020),
        (7, "Gauri", "HR", 68000, 2021),
        (8, "Harsh", "Marketing", 76000, 2020),
        (9, "Ishita", "Engineering", 110000, 2021),
        (10, "Jatin", "Finance", 88000, 2022),
        (11, "Kavya", "HR", 70000, 2023),
        (12, "Laksh", "Engineering", 102000, 2022),
        (13, "Meera", "Marketing", 79000, 2023),
        (14, "Nikhil", "Finance", 93000, 2019),
        (15, "Ojas", "Engineering", 87000, 2024),
        (16, "Priya", "HR", 73000, 2022),
        (17, "Rahul", "Engineering", 110000, 2020),
        (18, "Sneha", "Marketing", 81000, 2021),
        (19, "Tanvi", "Finance", 96000, 2023),
        (20, "Varun", "Engineering", 89000, 2024),
    ]

    departments = [
        (1, "Engineering"),
        (2, "Finance"),
        (3, "Marketing"),
        (4, "HR"),
    ]

    products = [
        (1, "Laptop", "Electronics", 75000, 12),
        (2, "Keyboard", "Electronics", 2500, 50),
        (3, "Mouse", "Electronics", 1200, 100),
        (4, "Monitor", "Electronics", 18000, 25),
        (5, "Desk", "Furniture", 15000, 10),
        (6, "Chair", "Furniture", 9000, 18),
        (7, "Notebook", "Stationery", 250, 200),
        (8, "Pen", "Stationery", 50, 500),
    ]

    connection.executemany(
        """
        INSERT INTO employees
            (employee_id, name, department, salary, hire_year)
        VALUES (?, ?, ?, ?, ?)
        """,
        employees,
    )

    connection.executemany(
        """
        INSERT INTO departments
            (department_id, department_name)
        VALUES (?, ?)
        """,
        departments,
    )

    connection.executemany(
        """
        INSERT INTO products
            (product_id, product_name, category, price, stock)
        VALUES (?, ?, ?, ?, ?)
        """,
        products,
    )

    connection.commit()


# =============================================================================
# 2. GENERAL DISPLAY HELPERS
# =============================================================================

def print_title(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def print_rows(rows: Iterable[sqlite3.Row]) -> None:
    """Print SQLite rows in a readable form."""
    rows = list(rows)

    if not rows:
        print("(no rows)")
        return

    for row in rows:
        print(dict(row))


def execute_and_print(
    connection: sqlite3.Connection,
    sql: str,
    parameters: Sequence[Any] = (),
) -> list[sqlite3.Row]:
    """Execute a parameterized query, print it, and return the rows."""
    print(f"\nSQL: {sql}")
    print(f"Parameters: {tuple(parameters)}")

    cursor = connection.execute(sql, parameters)
    rows = cursor.fetchall()
    print_rows(rows)
    return rows


# =============================================================================
# 3. LIMIT FUNDAMENTALS
# =============================================================================

def demonstrate_limit(connection: sqlite3.Connection) -> None:
    print_title("3. LIMIT: restricting the number of returned rows")

    # Without LIMIT, the query can return every matching employee.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY employee_id
        """,
    )

    # LIMIT restricts the maximum number of rows returned.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY employee_id
        LIMIT 5
        """,
    )

    # LIMIT 1 is useful for queries where only one row is required.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 1
        """,
    )


# =============================================================================
# 4. LIMIT MUST BE COMBINED WITH ORDER BY FOR PAGINATION
# =============================================================================

def demonstrate_order_by_importance(connection: sqlite3.Connection) -> None:
    print_title("4. ORDER BY: the foundation of predictable limiting")

    # ORDER BY defines which rows should be considered first.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 5
        """,
    )

    # Multiple ordering columns are important when the primary ordering
    # column contains duplicate values.
    #
    # Three employees have a salary of 110000. employee_id gives the query
    # a deterministic tie-breaker.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 10
        """,
    )

    # LIMIT without ORDER BY should not be treated as "the first five
    # logical records". The database is free to return rows according to
    # its execution plan.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name
        FROM employees
        LIMIT 5
        """,
    )


# =============================================================================
# 5. OFFSET FUNDAMENTALS
# =============================================================================

def demonstrate_offset(connection: sqlite3.Connection) -> None:
    print_title("5. OFFSET: skipping rows before returning results")

    # OFFSET 0 skips nothing.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name
        FROM employees
        ORDER BY employee_id
        LIMIT 5 OFFSET 0
        """,
    )

    # OFFSET 5 skips the first five ordered rows.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name
        FROM employees
        ORDER BY employee_id
        LIMIT 5 OFFSET 5
        """,
    )

    # OFFSET 10 skips the first ten ordered rows.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name
        FROM employees
        ORDER BY employee_id
        LIMIT 5 OFFSET 10
        """,
    )


# =============================================================================
# 6. LIMIT + OFFSET AS PAGE-BASED PAGINATION
# =============================================================================

@dataclass(frozen=True)
class PageRequest:
    """Represent a traditional page-number pagination request."""

    page: int
    page_size: int

    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def validate_page_request(page: int, page_size: int, max_page_size: int = 100) -> None:
    """
    Validate API-style page parameters.

    Rejecting invalid values prevents confusing behavior and helps prevent
    excessive database work caused by unbounded page sizes.
    """
    if page < 1:
        raise ValueError("page must be at least 1")

    if page_size < 1:
        raise ValueError("page_size must be at least 1")

    if page_size > max_page_size:
        raise ValueError(
            f"page_size cannot exceed the configured maximum of {max_page_size}"
        )


def fetch_employee_page(
    connection: sqlite3.Connection,
    page: int,
    page_size: int,
) -> list[sqlite3.Row]:
    """Fetch one page using LIMIT and OFFSET."""
    validate_page_request(page, page_size)

    offset = (page - 1) * page_size

    # LIMIT and OFFSET are values, not column names. The SQLite driver safely
    # parameterizes them here.
    cursor = connection.execute(
        """
        SELECT employee_id, name, department, salary
        FROM employees
        ORDER BY employee_id ASC
        LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    )

    return cursor.fetchall()


def demonstrate_page_pagination(connection: sqlite3.Connection) -> None:
    print_title("6. Page-number pagination with LIMIT + OFFSET")

    for page in range(1, 5):
        page_rows = fetch_employee_page(connection, page=page, page_size=5)

        print(f"\nPage {page}:")
        print_rows(page_rows)


# =============================================================================
# 7. PAGINATION MATH
# =============================================================================

def demonstrate_pagination_math() -> None:
    print_title("7. Pagination mathematics")

    page_size = 10

    for page in [1, 2, 3, 10]:
        offset = (page - 1) * page_size
        print(
            f"page={page}, page_size={page_size}, "
            f"offset={offset}, rows={offset + 1}-{offset + page_size}"
        )

    print(
        "\nFormula: OFFSET = (page - 1) * page_size"
    )

    print(
        "For page 1 with size 10: OFFSET = (1 - 1) * 10 = 0"
    )
    print(
        "For page 2 with size 10: OFFSET = (2 - 1) * 10 = 10"
    )
    print(
        "For page 3 with size 10: OFFSET = (3 - 1) * 10 = 20"
    )


# =============================================================================
# 8. FETCH FIRST / FETCH NEXT CONCEPTS
# =============================================================================

def demonstrate_fetch_concepts() -> None:
    print_title("8. FETCH FIRST / FETCH NEXT concepts")

    print(
        """
SQL-standard-style concepts:

FETCH FIRST 10 ROWS ONLY
    Return at most 10 rows.

OFFSET 20 ROWS
FETCH NEXT 10 ROWS ONLY
    Skip 20 rows and return the next 10 rows.

Representative query:

SELECT employee_id, name
FROM employees
ORDER BY employee_id
OFFSET 20 ROWS
FETCH NEXT 10 ROWS ONLY;

Dialect note:
SQLite uses LIMIT/OFFSET instead of this FETCH syntax. Other database
systems have different support and syntax details. Always verify the
syntax supported by the target database engine.
        """.strip()
    )


# =============================================================================
# 9. TOP-N QUERIES
# =============================================================================

def demonstrate_top_n(connection: sqlite3.Connection) -> None:
    print_title("9. Top-N queries")

    # Highest-paid five employees.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 5
        """,
    )

    # Lowest-priced three products.
    execute_and_print(
        connection,
        """
        SELECT product_id, product_name, price
        FROM products
        ORDER BY price ASC, product_id ASC
        LIMIT 3
        """,
    )

    # Top three employees hired most recently.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, hire_year
        FROM employees
        ORDER BY hire_year DESC, employee_id ASC
        LIMIT 3
        """,
    )


# =============================================================================
# 10. FILTERING HAPPENS BEFORE LIMITING
# =============================================================================

def demonstrate_filter_then_limit(connection: sqlite3.Connection) -> None:
    print_title("10. WHERE filtering before LIMIT")

    # SQL logically filters rows before applying the final result limit.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, department, salary
        FROM employees
        WHERE department = ?
        ORDER BY salary DESC, employee_id ASC
        LIMIT 3
        """,
        ("Engineering",),
    )

    # This means LIMIT 3 means three rows from the filtered set, not
    # necessarily three rows from the entire table.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        WHERE salary >= ?
        ORDER BY salary DESC, employee_id ASC
        LIMIT 5
        """,
        (90000,),
    )


# =============================================================================
# 11. DISTINCT + LIMIT
# =============================================================================

def demonstrate_distinct_and_limit(connection: sqlite3.Connection) -> None:
    print_title("11. DISTINCT combined with LIMIT")

    # DISTINCT eliminates duplicate department values before the final
    # limited result is returned.
    execute_and_print(
        connection,
        """
        SELECT DISTINCT department
        FROM employees
        ORDER BY department ASC
        LIMIT 2
        """,
    )


# =============================================================================
# 12. AGGREGATION + LIMIT
# =============================================================================

def demonstrate_aggregation_and_limit(connection: sqlite3.Connection) -> None:
    print_title("12. GROUP BY, aggregation, ORDER BY, and LIMIT")

    # Find the three departments with the highest average salary.
    execute_and_print(
        connection,
        """
        SELECT
            department,
            COUNT(*) AS employee_count,
            ROUND(AVG(salary), 2) AS average_salary
        FROM employees
        GROUP BY department
        ORDER BY average_salary DESC, department ASC
        LIMIT 3
        """,
    )

    # The LIMIT is applied to the grouped result, not individual employee
    # rows.
    execute_and_print(
        connection,
        """
        SELECT
            department,
            COUNT(*) AS employee_count
        FROM employees
        GROUP BY department
        ORDER BY employee_count DESC, department ASC
        LIMIT 2
        """,
    )


# =============================================================================
# 13. JOIN + LIMIT
# =============================================================================

def demonstrate_join_and_limit(connection: sqlite3.Connection) -> None:
    print_title("13. JOIN + LIMIT")

    # The JOIN creates a result set. LIMIT then restricts the returned rows.
    execute_and_print(
        connection,
        """
        SELECT
            e.employee_id,
            e.name,
            d.department_id,
            d.department_name
        FROM employees AS e
        JOIN departments AS d
            ON e.department = d.department_name
        ORDER BY e.employee_id ASC
        LIMIT 5
        """,
    )


# =============================================================================
# 14. OFFSET EDGE CASES
# =============================================================================

def demonstrate_offset_edge_cases(connection: sqlite3.Connection) -> None:
    print_title("14. OFFSET edge cases")

    # OFFSET beyond the end produces zero rows.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name
        FROM employees
        ORDER BY employee_id
        LIMIT 5 OFFSET 1000
        """,
    )

    # LIMIT 0 intentionally asks for no rows.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name
        FROM employees
        ORDER BY employee_id
        LIMIT 0
        """,
    )

    # The helper rejects invalid page numbers before reaching the database.
    for invalid_page in [0, -1]:
        try:
            fetch_employee_page(connection, invalid_page, 5)
        except ValueError as error:
            print(f"Invalid page {invalid_page!r}: {error}")

    # A zero or negative page size is invalid at the application layer.
    for invalid_size in [0, -5]:
        try:
            fetch_employee_page(connection, 1, invalid_size)
        except ValueError as error:
            print(f"Invalid page size {invalid_size!r}: {error}")


# =============================================================================
# 15. LAST PAGE DETECTION
# =============================================================================

@dataclass
class PageResult:
    """Application-level representation of a paginated response."""

    items: list[dict[str, Any]]
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


def fetch_page_with_has_next(
    connection: sqlite3.Connection,
    page: int,
    page_size: int,
) -> PageResult:
    """
    Fetch one extra row to determine whether another page exists.

    Instead of running COUNT(*) for every request, retrieve page_size + 1
    records. If the extra row exists, has_next is True.
    """
    validate_page_request(page, page_size)

    offset = (page - 1) * page_size

    cursor = connection.execute(
        """
        SELECT employee_id, name, department, salary
        FROM employees
        ORDER BY employee_id ASC
        LIMIT ? OFFSET ?
        """,
        (page_size + 1, offset),
    )

    rows = cursor.fetchall()

    has_next = len(rows) > page_size
    visible_rows = rows[:page_size]

    return PageResult(
        items=[dict(row) for row in visible_rows],
        page=page,
        page_size=page_size,
        has_next=has_next,
        has_previous=page > 1,
    )


def demonstrate_has_next(connection: sqlite3.Connection) -> None:
    print_title("15. Detecting whether another page exists")

    for page in [1, 2, 4, 5]:
        result = fetch_page_with_has_next(connection, page, 5)

        print(
            f"\nPage {result.page}: "
            f"items={len(result.items)}, "
            f"has_previous={result.has_previous}, "
            f"has_next={result.has_next}"
        )


# =============================================================================
# 16. COUNT(*) VERSUS FETCHING AN EXTRA ROW
# =============================================================================

def demonstrate_count_tradeoff(connection: sqlite3.Connection) -> None:
    print_title("16. Counting total rows versus checking only has_next")

    total = connection.execute(
        "SELECT COUNT(*) AS total FROM employees"
    ).fetchone()["total"]

    print(f"Total employee count: {total}")

    result = fetch_page_with_has_next(connection, page=2, page_size=5)

    print(
        "The extra-row technique only needs to know whether more rows exist. "
        f"For page 2, has_next={result.has_next}."
    )

    print(
        """
COUNT(*) is useful when an API genuinely needs total pages or total records.
Fetching one extra row is often simpler when the UI only needs Next/Previous
controls. The best choice depends on database size, indexes, filtering,
counting cost, and product requirements.
        """.strip()
    )


# =============================================================================
# 17. OFFSET PAGINATION WITH FILTERS
# =============================================================================

def fetch_department_page(
    connection: sqlite3.Connection,
    department: str,
    page: int,
    page_size: int,
) -> list[sqlite3.Row]:
    """Paginate a filtered dataset."""
    validate_page_request(page, page_size)

    offset = (page - 1) * page_size

    return connection.execute(
        """
        SELECT employee_id, name, department, salary
        FROM employees
        WHERE department = ?
        ORDER BY employee_id ASC
        LIMIT ? OFFSET ?
        """,
        (department, page_size, offset),
    ).fetchall()


def demonstrate_filtered_pagination(connection: sqlite3.Connection) -> None:
    print_title("17. Pagination after filtering")

    for page in [1, 2]:
        rows = fetch_department_page(
            connection,
            department="Engineering",
            page=page,
            page_size=3,
        )

        print(f"\nEngineering page {page}:")
        print_rows(rows)


# =============================================================================
# 18. KEYSET/CURSOR PAGINATION
# =============================================================================

def fetch_employees_after_id(
    connection: sqlite3.Connection,
    last_seen_id: int | None,
    page_size: int,
) -> list[sqlite3.Row]:
    """
    Fetch the next page using the last seen employee_id.

    This is called keyset pagination or cursor-style pagination.

    Instead of saying:
        skip 10,000 rows

    we say:
        give me rows whose key is greater than the last key I saw.

    This can be substantially more efficient for large ordered datasets
    when the ordering column is indexed.
    """
    validate_page_request(1, page_size)

    if last_seen_id is None:
        return connection.execute(
            """
            SELECT employee_id, name, department, salary
            FROM employees
            ORDER BY employee_id ASC
            LIMIT ?
            """,
            (page_size,),
        ).fetchall()

    return connection.execute(
        """
        SELECT employee_id, name, department, salary
        FROM employees
        WHERE employee_id > ?
        ORDER BY employee_id ASC
        LIMIT ?
        """,
        (last_seen_id, page_size),
    ).fetchall()


def demonstrate_keyset_pagination(connection: sqlite3.Connection) -> None:
    print_title("18. Keyset/cursor pagination")

    last_seen_id: int | None = None

    for page_number in range(1, 5):
        rows = fetch_employees_after_id(
            connection,
            last_seen_id=last_seen_id,
            page_size=5,
        )

        print(f"\nCursor page {page_number}:")
        print_rows(rows)

        if not rows:
            break

        last_seen_id = rows[-1]["employee_id"]
        print(f"Next cursor: {last_seen_id}")


# =============================================================================
# 19. KEYSET PAGINATION WITH COMPOSITE ORDERING
# =============================================================================

def fetch_salary_ordered_page(
    connection: sqlite3.Connection,
    last_salary: int | None,
    last_employee_id: int | None,
    page_size: int,
) -> list[sqlite3.Row]:
    """
    Demonstrate keyset pagination when ORDER BY uses two columns.

    Ordering:
        salary DESC
        employee_id ASC

    The cursor must contain both ordering values because salary is not unique.
    """
    validate_page_request(1, page_size)

    if last_salary is None or last_employee_id is None:
        return connection.execute(
            """
            SELECT employee_id, name, salary
            FROM employees
            ORDER BY salary DESC, employee_id ASC
            LIMIT ?
            """,
            (page_size,),
        ).fetchall()

    return connection.execute(
        """
        SELECT employee_id, name, salary
        FROM employees
        WHERE
            salary < ?
            OR (salary = ? AND employee_id > ?)
        ORDER BY salary DESC, employee_id ASC
        LIMIT ?
        """,
        (last_salary, last_salary, last_employee_id, page_size),
    ).fetchall()


def demonstrate_composite_keyset(connection: sqlite3.Connection) -> None:
    print_title("19. Keyset pagination with a composite cursor")

    last_salary: int | None = None
    last_employee_id: int | None = None

    for page_number in range(1, 4):
        rows = fetch_salary_ordered_page(
            connection,
            last_salary=last_salary,
            last_employee_id=last_employee_id,
            page_size=5,
        )

        print(f"\nSalary-ordered cursor page {page_number}:")
        print_rows(rows)

        if not rows:
            break

        last_salary = rows[-1]["salary"]
        last_employee_id = rows[-1]["employee_id"]

        print(
            "Next cursor: "
            f"(salary={last_salary}, employee_id={last_employee_id})"
        )


# =============================================================================
# 20. OFFSET VERSUS KEYSET CONCEPTUAL COMPARISON
# =============================================================================

def demonstrate_pagination_comparison() -> None:
    print_title("20. OFFSET versus keyset pagination")

    comparison = [
        ("Jump directly to page 50", "Easy", "Not naturally page-number based"),
        ("Next/previous navigation", "Good", "Excellent"),
        ("Very large datasets", "Can become expensive", "Usually better"),
        ("Stable traversal during inserts", "Can shift", "Usually more stable"),
        ("Simple implementation", "Very simple", "More complex"),
        ("Arbitrary sorting", "Flexible", "Cursor must match ordering"),
        ("Exact total page count", "Easy with COUNT(*)", "Usually separate concern"),
    ]

    print(f"{'Requirement':<38} {'OFFSET':<22} {'Keyset':<30}")
    print("-" * 92)

    for requirement, offset_value, keyset_value in comparison:
        print(
            f"{requirement:<38} "
            f"{offset_value:<22} "
            f"{keyset_value:<30}"
        )


# =============================================================================
# 21. SIMULATING DATA CHANGES BETWEEN PAGES
# =============================================================================

def demonstrate_offset_consistency_problem(connection: sqlite3.Connection) -> None:
    print_title("21. Offset pagination and changing data")

    # Read page 1.
    page_one = fetch_employee_page(connection, page=1, page_size=5)

    print("Page 1 before insertion:")
    print_rows(page_one)

    # Insert a new employee with an ID that sorts before many existing rows.
    connection.execute(
        """
        INSERT INTO employees
            (employee_id, name, department, salary, hire_year)
        VALUES (?, ?, ?, ?, ?)
        """,
        (21, "New Employee", "Engineering", 100000, 2026),
    )
    connection.commit()

    # Page 2 is now calculated against the changed dataset.
    page_two = fetch_employee_page(connection, page=2, page_size=5)

    print("\nPage 2 after insertion:")
    print_rows(page_two)

    print(
        """
If rows are inserted or deleted between requests, OFFSET pagination can
produce duplicates or skipped records when the ordering changes relative to
the client traversal.

A stable unique ORDER BY helps, but it cannot completely solve every
concurrent-data problem. Keyset pagination often provides better traversal
behavior for continuously changing datasets.
        """.strip()
    )


# =============================================================================
# 22. REST-STYLE PAGINATION RESPONSE
# =============================================================================

def build_api_page(
    connection: sqlite3.Connection,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Build a simple dictionary suitable for serialization by an API."""
    result = fetch_page_with_has_next(connection, page, page_size)

    return {
        "data": result.items,
        "pagination": {
            "page": result.page,
            "page_size": result.page_size,
            "has_previous": result.has_previous,
            "has_next": result.has_next,
        },
    }


def demonstrate_api_response(connection: sqlite3.Connection) -> None:
    print_title("22. API-style page response")

    response = build_api_page(
        connection,
        page=2,
        page_size=4,
    )

    print(response)


# =============================================================================
# 23. CURSOR-STYLE API RESPONSE
# =============================================================================

def build_cursor_api_page(
    connection: sqlite3.Connection,
    cursor_id: int | None,
    page_size: int,
) -> dict[str, Any]:
    """Build a cursor-based API response."""
    rows = fetch_employees_after_id(
        connection,
        last_seen_id=cursor_id,
        page_size=page_size + 1,
    )

    has_next = len(rows) > page_size
    visible_rows = rows[:page_size]

    next_cursor = (
        visible_rows[-1]["employee_id"]
        if visible_rows and has_next
        else None
    )

    return {
        "data": [dict(row) for row in visible_rows],
        "pagination": {
            "page_size": page_size,
            "has_next": has_next,
            "next_cursor": next_cursor,
        },
    }


def demonstrate_cursor_api(connection: sqlite3.Connection) -> None:
    print_title("23. Cursor-style API response")

    cursor_id = None

    for request_number in range(1, 4):
        response = build_cursor_api_page(
            connection,
            cursor_id=cursor_id,
            page_size=4,
        )

        print(f"\nRequest {request_number}:")
        print(response)

        cursor_id = response["pagination"]["next_cursor"]

        if cursor_id is None:
            break


# =============================================================================
# 24. SAFE PARAMETERIZATION
# =============================================================================

def demonstrate_parameterization(connection: sqlite3.Connection) -> None:
    print_title("24. Parameterized LIMIT and OFFSET")

    page = 2
    page_size = 4
    offset = (page - 1) * page_size

    # Values supplied by an application should be validated and parameterized.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name
        FROM employees
        ORDER BY employee_id
        LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    )

    print(
        """
Do not construct SQL by concatenating untrusted values into the query text.

Good pattern:
    SQL contains placeholders
    Python supplies validated values separately

The exact parameterization mechanism varies by database driver.
        """.strip()
    )


# =============================================================================
# 25. SQL INJECTION ANTI-PATTERN EXPLANATION
# =============================================================================

def demonstrate_sql_injection_risk() -> None:
    print_title("25. SQL injection risk")

    unsafe_example = """
page_size = user_input
sql = "SELECT * FROM employees LIMIT " + page_size
"""

    safe_example = """
page_size = int(user_input)
validate_page_request(1, page_size)
cursor.execute(
    "SELECT * FROM employees LIMIT ?",
    (page_size,),
)
"""

    print("Unsafe pattern:")
    print(unsafe_example)

    print("Safer pattern:")
    print(safe_example)

    print(
        """
The important principles are:
1. Validate pagination parameters.
2. Keep SQL structure separate from user-controlled values.
3. Use the database driver's parameter binding where supported.
4. Enforce a maximum page size.
        """.strip()
    )


# =============================================================================
# 26. LARGE OFFSET PERFORMANCE
# =============================================================================

def demonstrate_large_offset_concept() -> None:
    print_title("26. Why large OFFSET values can be expensive")

    examples = [
        ("OFFSET 0", "The database needs to locate the beginning of the result."),
        ("OFFSET 1,000", "More rows may need to be considered before the requested page."),
        ("OFFSET 100,000", "The database may need to process/skip a large prefix."),
        ("OFFSET 1,000,000", "Deep pagination can become expensive on large datasets."),
    ]

    for expression, explanation in examples:
        print(f"{expression:<18} {explanation}")

    print(
        """
LIMIT controls how many rows are returned to the client. It does not
necessarily mean the database can avoid processing all preceding rows needed
to determine the OFFSET position.

Indexes, query plans, ordering, filtering, database engine, and data
distribution all affect actual performance.
        """.strip()
    )


# =============================================================================
# 27. INDEXING FOR PAGINATION
# =============================================================================

def demonstrate_indexing(connection: sqlite3.Connection) -> None:
    print_title("27. Indexing and pagination")

    # employee_id is already the primary key and therefore indexed by SQLite.
    # A separate index can support common filtering and ordering patterns.
    connection.execute(
        """
        CREATE INDEX idx_employees_department_employee_id
        ON employees(department, employee_id)
        """
    )

    # The indexed columns align with this filter/order pattern.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, department
        FROM employees
        WHERE department = ?
        ORDER BY employee_id ASC
        LIMIT ? OFFSET ?
        """,
        ("Engineering", 5, 0),
    )

    print(
        """
A useful index often starts with columns used in filtering and continues
with columns useful for ordering.

For example:
    (department, employee_id)

can support queries filtering by department and ordering by employee_id.

Index design must be based on real query patterns. Indexes also consume
storage and can increase INSERT, UPDATE, and DELETE costs.
        """.strip()
    )


# =============================================================================
# 28. EXPLAIN QUERY PLAN
# =============================================================================

def demonstrate_query_plan(connection: sqlite3.Connection) -> None:
    print_title("28. Inspecting a SQLite query plan")

    query = """
        SELECT employee_id, name, department
        FROM employees
        WHERE department = ?
        ORDER BY employee_id ASC
        LIMIT ? OFFSET ?
    """

    plan_rows = connection.execute(
        "EXPLAIN QUERY PLAN " + query,
        ("Engineering", 5, 0),
    ).fetchall()

    print("SQLite query plan:")
    print_rows(plan_rows)

    print(
        """
EXPLAIN or EXPLAIN QUERY PLAN is useful when investigating performance.

A production investigation should consider:
- execution plan
- indexes
- cardinality
- filtering selectivity
- sort operations
- rows examined
- rows returned
- database statistics
- actual workload
        """.strip()
    )


# =============================================================================
# 29. PAGE SIZE LIMITS
# =============================================================================

def demonstrate_page_size_limits() -> None:
    print_title("29. Enforcing a maximum page size")

    for page_size in [10, 50, 100, 101, 1000]:
        try:
            validate_page_request(page=1, page_size=page_size, max_page_size=100)
            print(f"page_size={page_size}: accepted")
        except ValueError as error:
            print(f"page_size={page_size}: rejected ({error})")


# =============================================================================
# 30. PAGE NUMBER VERSUS OFFSET INPUT
# =============================================================================

def demonstrate_page_and_offset_difference() -> None:
    print_title("30. Page number versus raw OFFSET")

    page = 4
    page_size = 25
    calculated_offset = (page - 1) * page_size

    print(f"Requested page: {page}")
    print(f"Page size: {page_size}")
    print(f"Database OFFSET: {calculated_offset}")

    print(
        """
Applications commonly expose page=4 to users while the database query uses
OFFSET=75.

The two concepts should not be confused:

page
    A human/API navigation concept.

OFFSET
    A database result-set positioning concept.
        """.strip()
    )


# =============================================================================
# 31. PAGINATION WITH SORT DIRECTION
# =============================================================================

def demonstrate_sort_direction(connection: sqlite3.Connection) -> None:
    print_title("31. Pagination with ascending and descending order")

    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY salary ASC, employee_id ASC
        LIMIT 5
        """,
    )

    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 5
        """,
    )


# =============================================================================
# 32. NULL ORDERING
# =============================================================================

def demonstrate_null_ordering(connection: sqlite3.Connection) -> None:
    print_title("32. NULL ordering considerations")

    connection.execute(
        """
        CREATE TABLE optional_scores (
            item_id INTEGER PRIMARY KEY,
            item_name TEXT NOT NULL,
            score INTEGER
        )
        """
    )

    connection.executemany(
        """
        INSERT INTO optional_scores (item_id, item_name, score)
        VALUES (?, ?, ?)
        """,
        [
            (1, "A", 90),
            (2, "B", None),
            (3, "C", 70),
            (4, "D", None),
            (5, "E", 80),
        ],
    )

    # NULL ordering is database-specific in important details. SQLite has
    # its own default behavior, so production SQL should explicitly express
    # the intended ordering when NULL placement matters.
    execute_and_print(
        connection,
        """
        SELECT item_id, item_name, score
        FROM optional_scores
        ORDER BY score ASC
        LIMIT 5
        """,
    )

    # A CASE expression can make NULL placement explicit.
    execute_and_print(
        connection,
        """
        SELECT item_id, item_name, score
        FROM optional_scores
        ORDER BY
            CASE WHEN score IS NULL THEN 1 ELSE 0 END,
            score ASC
        LIMIT 5
        """,
    )


# =============================================================================
# 33. PAGINATION TESTING
# =============================================================================

def test_page_boundaries(connection: sqlite3.Connection) -> None:
    print_title("33. Testing pagination boundaries")

    # The sample dataset contains 21 employees at this point because the
    # earlier consistency example inserted one additional employee.
    total = connection.execute(
        "SELECT COUNT(*) AS total FROM employees"
    ).fetchone()["total"]

    page_size = 5

    expected_page_count = (total + page_size - 1) // page_size

    print(f"Total rows: {total}")
    print(f"Page size: {page_size}")
    print(f"Expected page count: {expected_page_count}")

    for page in range(1, expected_page_count + 1):
        rows = fetch_employee_page(connection, page, page_size)

        assert 1 <= len(rows) <= page_size
        print(f"Page {page}: {len(rows)} rows")

    # The page after the last page should be empty.
    rows_after_last_page = fetch_employee_page(
        connection,
        expected_page_count + 1,
        page_size,
    )

    assert rows_after_last_page == []
    print("Page after the final page: empty, as expected")


# =============================================================================
# 34. DUPLICATE ORDERING VALUES
# =============================================================================

def demonstrate_tie_breaking(connection: sqlite3.Connection) -> None:
    print_title("34. Tie-breaking for deterministic pagination")

    # salary alone is not unique.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY salary DESC
        LIMIT 10
        """,
    )

    # Adding a unique key creates deterministic ordering.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name, salary
        FROM employees
        ORDER BY salary DESC, employee_id ASC
        LIMIT 10
        """,
    )

    print(
        """
When a pagination ORDER BY column contains duplicates, add a stable,
unique tie-breaker where possible.

Example:
    ORDER BY created_at DESC, id DESC

This prevents ambiguous ordering among rows sharing the same timestamp.
        """.strip()
    )


# =============================================================================
# 35. MULTI-COLUMN KEYSET PAGINATION WITH DESCENDING ORDER
# =============================================================================

def fetch_descending_cursor_page(
    connection: sqlite3.Connection,
    last_salary: int | None,
    last_employee_id: int | None,
    page_size: int,
) -> list[sqlite3.Row]:
    """
    Keyset pagination for:
        ORDER BY salary DESC, employee_id DESC

    Since both fields descend, the next page contains:
        salary < last_salary
    OR
        same salary and employee_id < last_employee_id
    """
    validate_page_request(1, page_size)

    if last_salary is None or last_employee_id is None:
        return connection.execute(
            """
            SELECT employee_id, name, salary
            FROM employees
            ORDER BY salary DESC, employee_id DESC
            LIMIT ?
            """,
            (page_size,),
        ).fetchall()

    return connection.execute(
        """
        SELECT employee_id, name, salary
        FROM employees
        WHERE
            salary < ?
            OR (salary = ? AND employee_id < ?)
        ORDER BY salary DESC, employee_id DESC
        LIMIT ?
        """,
        (last_salary, last_salary, last_employee_id, page_size),
    ).fetchall()


def demonstrate_descending_keyset(connection: sqlite3.Connection) -> None:
    print_title("35. Descending composite keyset pagination")

    last_salary: int | None = None
    last_employee_id: int | None = None

    for page_number in range(1, 4):
        rows = fetch_descending_cursor_page(
            connection,
            last_salary=last_salary,
            last_employee_id=last_employee_id,
            page_size=5,
        )

        print(f"\nDescending cursor page {page_number}:")
        print_rows(rows)

        if not rows:
            break

        last_salary = rows[-1]["salary"]
        last_employee_id = rows[-1]["employee_id"]


# =============================================================================
# 36. PAGINATION WITH A SEARCH FILTER
# =============================================================================

def search_employees(
    connection: sqlite3.Connection,
    search_term: str,
    page: int,
    page_size: int,
) -> list[sqlite3.Row]:
    """Search and paginate using a bound parameter."""
    validate_page_request(page, page_size)

    offset = (page - 1) * page_size
    pattern = f"%{search_term}%"

    return connection.execute(
        """
        SELECT employee_id, name, department
        FROM employees
        WHERE name LIKE ?
        ORDER BY employee_id ASC
        LIMIT ? OFFSET ?
        """,
        (pattern, page_size, offset),
    ).fetchall()


def demonstrate_search_pagination(connection: sqlite3.Connection) -> None:
    print_title("36. Search + pagination")

    rows = search_employees(
        connection,
        search_term="a",
        page=1,
        page_size=5,
    )

    print_rows(rows)


# =============================================================================
# 37. LIMIT WITH EXPRESSIONS
# =============================================================================

def demonstrate_limit_expressions(connection: sqlite3.Connection) -> None:
    print_title("37. LIMIT values and application-side calculations")

    page = 2
    page_size = 3
    offset = (page - 1) * page_size

    # Calculate pagination values in application code when this makes the
    # query easier to understand and validate.
    execute_and_print(
        connection,
        """
        SELECT employee_id, name
        FROM employees
        ORDER BY employee_id
        LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    )


# =============================================================================
# 38. PAGINATION WITH TOTAL COUNT
# =============================================================================

def fetch_page_with_total(
    connection: sqlite3.Connection,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Return rows plus total-count metadata."""
    validate_page_request(page, page_size)

    total = connection.execute(
        "SELECT COUNT(*) AS total FROM employees"
    ).fetchone()["total"]

    offset = (page - 1) * page_size

    rows = connection.execute(
        """
        SELECT employee_id, name, department, salary
        FROM employees
        ORDER BY employee_id
        LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    ).fetchall()

    total_pages = (total + page_size - 1) // page_size

    return {
        "data": [dict(row) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
        },
    }


def demonstrate_total_count(connection: sqlite3.Connection) -> None:
    print_title("38. Pagination with total record count")

    response = fetch_page_with_total(
        connection,
        page=2,
        page_size=5,
    )

    print(response)


# =============================================================================
# 39. TRANSACTION CONSISTENCY CONCEPT
# =============================================================================

def demonstrate_consistency_concept() -> None:
    print_title("39. Consistency and pagination")

    print(
        """
Pagination requests are usually separate database operations.

Request 1:
    SELECT ... ORDER BY ... LIMIT 10 OFFSET 0

Request 2:
    SELECT ... ORDER BY ... LIMIT 10 OFFSET 10

If rows are inserted, deleted, or updated between the requests, the two
queries can observe different datasets.

Possible approaches include:
- stable deterministic ordering
- keyset pagination
- snapshot/transaction techniques when appropriate
- immutable ordering keys
- explicit product behavior for changing data

The correct solution depends on isolation requirements and workload.
        """.strip()
    )


# =============================================================================
# 40. COMMON MISTAKES
# =============================================================================

def demonstrate_common_mistakes() -> None:
    print_title("40. Common mistakes")

    mistakes = {
        "LIMIT without meaningful ORDER BY":
            "The returned subset may not be deterministic.",
        "Using page number directly as OFFSET":
            "OFFSET is a row count, so use (page - 1) * page_size.",
        "Allowing unlimited page_size":
            "A client can request an unnecessarily large result set.",
        "Ignoring duplicate ORDER BY values":
            "Pagination order can be ambiguous without a tie-breaker.",
        "Using huge OFFSET values blindly":
            "Deep pages can require substantial work.",
        "Building SQL with string concatenation":
            "Can create SQL injection vulnerabilities.",
        "Assuming FETCH syntax is universal":
            "Database dialects differ.",
        "Counting when only has_next is required":
            "COUNT(*) can add unnecessary work for some workloads.",
        "Using keyset pagination with an incomplete cursor":
            "The cursor must represent the complete ordering.",
        "Changing ORDER BY between requests":
            "Different pages no longer represent one coherent ordering.",
    }

    for mistake, consequence in mistakes.items():
        print(f"\nMistake: {mistake}")
        print(f"Consequence: {consequence}")


# =============================================================================
# 41. LIMIT/OFFSET/FETCH SYNTAX REFERENCE
# =============================================================================

def print_syntax_reference() -> None:
    print_title("41. Syntax reference")

    syntax_examples = [
        (
            "LIMIT",
            "SELECT * FROM table_name ORDER BY id LIMIT 10;",
        ),
        (
            "LIMIT + OFFSET",
            "SELECT * FROM table_name ORDER BY id LIMIT 10 OFFSET 20;",
        ),
        (
            "FETCH FIRST concept",
            "SELECT * FROM table_name ORDER BY id FETCH FIRST 10 ROWS ONLY;",
        ),
        (
            "OFFSET + FETCH concept",
            (
                "SELECT * FROM table_name ORDER BY id "
                "OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY;"
            ),
        ),
        (
            "Page calculation",
            "offset = (page - 1) * page_size",
        ),
    ]

    for name, syntax in syntax_examples:
        print(f"{name:<25} {syntax}")


# =============================================================================
# 42. PRACTICAL DESIGN DECISION
# =============================================================================

def choose_pagination_strategy(
    needs_page_numbers: bool,
    needs_total_count: bool,
    very_large_dataset: bool,
    frequent_inserts: bool,
) -> str:
    """
    Provide a simple decision heuristic.

    This is educational, not a replacement for query-plan analysis.
    """
    if very_large_dataset and frequent_inserts:
        return "Prefer keyset/cursor pagination."

    if needs_page_numbers and needs_total_count:
        return "LIMIT/OFFSET is often the simpler fit."

    if very_large_dataset:
        return "Strongly consider keyset/cursor pagination."

    if needs_page_numbers:
        return "LIMIT/OFFSET is usually straightforward."

    return "Either approach may work; benchmark the real workload."


def demonstrate_design_decisions() -> None:
    print_title("42. Choosing a pagination strategy")

    scenarios = [
        {
            "name": "Admin table with page numbers",
            "needs_page_numbers": True,
            "needs_total_count": True,
            "very_large_dataset": False,
            "frequent_inserts": False,
        },
        {
            "name": "Large social feed",
            "needs_page_numbers": False,
            "needs_total_count": False,
            "very_large_dataset": True,
            "frequent_inserts": True,
        },
        {
            "name": "Moderate product catalog",
            "needs_page_numbers": True,
            "needs_total_count": False,
            "very_large_dataset": False,
            "frequent_inserts": False,
        },
    ]

    for scenario in scenarios:
        decision = choose_pagination_strategy(
            needs_page_numbers=scenario["needs_page_numbers"],
            needs_total_count=scenario["needs_total_count"],
            very_large_dataset=scenario["very_large_dataset"],
            frequent_inserts=scenario["frequent_inserts"],
        )

        print(f"\n{scenario['name']}: {decision}")


# =============================================================================
# 43. PRODUCTION-ORIENTED PAGINATION HELPER
# =============================================================================

@dataclass(frozen=True)
class PaginationConfig:
    """Configuration for an API's page-number pagination."""

    default_page_size: int = 20
    max_page_size: int = 100


def normalize_pagination_parameters(
    requested_page: int | None,
    requested_page_size: int | None,
    config: PaginationConfig,
) -> PageRequest:
    """
    Normalize optional API parameters into safe values.

    A production API may choose a different policy, but it should have an
    explicit default and maximum.
    """
    page = (
        config.default_page_size
        if requested_page is None
        else requested_page
    )

    # The line above demonstrates that page parameters need careful handling.
    # Correct the value to the actual default page number of 1.
    if requested_page is None:
        page = 1

    page_size = (
        config.default_page_size
        if requested_page_size is None
        else requested_page_size
    )

    validate_page_request(
        page=page,
        page_size=page_size,
        max_page_size=config.max_page_size,
    )

    return PageRequest(
        page=page,
        page_size=page_size,
    )


def demonstrate_production_helper(connection: sqlite3.Connection) -> None:
    print_title("43. Production-oriented pagination helper")

    config = PaginationConfig(
        default_page_size=20,
        max_page_size=100,
    )

    request = normalize_pagination_parameters(
        requested_page=2,
        requested_page_size=5,
        config=config,
    )

    rows = fetch_employee_page(
        connection,
        page=request.page,
        page_size=request.page_size,
    )

    print(f"Normalized request: {request}")
    print_rows(rows)


# =============================================================================
# 44. PERFORMANCE BENCHMARK SHAPE
# =============================================================================

def demonstrate_benchmark_methodology() -> None:
    print_title("44. Pagination performance benchmarking")

    print(
        """
A meaningful benchmark should compare queries against realistic data sizes.

For OFFSET pagination, test values such as:
    OFFSET 0
    OFFSET 1,000
    OFFSET 10,000
    OFFSET 100,000
    OFFSET 1,000,000

For keyset pagination, test equivalent traversal positions using the
appropriate cursor.

Measure:
- execution time
- rows examined
- logical/physical reads where available
- memory usage
- sort operations
- index usage
- database CPU
- application latency

Do not assume that a query is slow or fast based only on LIMIT or OFFSET.
Use the database's execution plan and real workload measurements.
        """.strip()
    )


# =============================================================================
# 45. SECURITY CHECKLIST
# =============================================================================

def print_security_checklist() -> None:
    print_title("45. Pagination security checklist")

    checklist = [
        "Validate page and page_size.",
        "Enforce a maximum page size.",
        "Use parameterized SQL values.",
        "Do not concatenate untrusted SQL fragments.",
        "Whitelist sortable column names when clients can choose sorting.",
        "Whitelist sort directions such as ASC and DESC.",
        "Avoid exposing sensitive records through careless pagination filters.",
        "Apply authorization before limiting results.",
        "Be aware that pagination can reveal information through record counts.",
    ]

    for item in checklist:
        print(f"- {item}")


# =============================================================================
# 46. DYNAMIC SORTING SAFELY
# =============================================================================

ALLOWED_SORT_COLUMNS = {
    "id": "employee_id",
    "name": "name",
    "salary": "salary",
    "hire_year": "hire_year",
}

ALLOWED_SORT_DIRECTIONS = {
    "asc": "ASC",
    "desc": "DESC",
}


def fetch_sorted_page_safely(
    connection: sqlite3.Connection,
    page: int,
    page_size: int,
    sort_column: str,
    sort_direction: str,
) -> list[sqlite3.Row]:
    """
    Demonstrate safe dynamic ORDER BY construction.

    Parameter placeholders are for values, not arbitrary SQL identifiers.
    Therefore, identifiers supplied by a client should be selected from a
    server-side allowlist rather than inserted directly without validation.
    """
    validate_page_request(page, page_size)

    try:
        safe_column = ALLOWED_SORT_COLUMNS[sort_column.lower()]
        safe_direction = ALLOWED_SORT_DIRECTIONS[sort_direction.lower()]
    except KeyError as error:
        raise ValueError("Unsupported sort option") from error

    offset = (page - 1) * page_size

    sql = f"""
        SELECT employee_id, name, department, salary, hire_year
        FROM employees
        ORDER BY {safe_column} {safe_direction}, employee_id ASC
        LIMIT ? OFFSET ?
    """

    return connection.execute(
        sql,
        (page_size, offset),
    ).fetchall()


def demonstrate_safe_dynamic_sorting(connection: sqlite3.Connection) -> None:
    print_title("46. Safe dynamic sorting")

    rows = fetch_sorted_page_safely(
        connection,
        page=1,
        page_size=5,
        sort_column="salary",
        sort_direction="desc",
    )

    print_rows(rows)

    try:
        fetch_sorted_page_safely(
            connection,
            page=1,
            page_size=5,
            sort_column="DROP TABLE employees",
            sort_direction="desc",
        )
    except ValueError as error:
        print(f"Rejected unsupported sort column: {error}")


# =============================================================================
# 47. PRACTICAL PRODUCTION CHECKLIST
# =============================================================================

def print_production_checklist() -> None:
    print_title("47. Production pagination checklist")

    checklist = [
        "Define a deterministic ORDER BY.",
        "Add a unique tie-breaker to the ordering where needed.",
        "Validate page number and page size.",
        "Set a maximum page size.",
        "Use parameter binding for values.",
        "Use allowlists for dynamic identifiers such as sort columns.",
        "Create indexes that match common filtering and ordering patterns.",
        "Inspect execution plans for important queries.",
        "Benchmark deep pagination against realistic data volumes.",
        "Consider keyset pagination for very large or frequently changing datasets.",
        "Decide whether total counts are truly required.",
        "Consider fetching one extra row to determine has_next.",
        "Define behavior for deleted or newly inserted records.",
        "Return clear pagination metadata in API responses.",
        "Test empty pages and final-page behavior.",
        "Test duplicate ordering values.",
        "Test invalid and excessively large parameters.",
    ]

    for number, item in enumerate(checklist, start=1):
        print(f"{number:02d}. {item}")


# =============================================================================
# 48. COMPLETE STUDY DEMONSTRATION
# =============================================================================

def run_study_program() -> None:
    connection = create_connection()

    try:
        create_schema(connection)
        insert_sample_data(connection)

        demonstrate_limit(connection)
        demonstrate_order_by_importance(connection)
        demonstrate_offset(connection)
        demonstrate_page_pagination(connection)
        demonstrate_pagination_math()
        demonstrate_fetch_concepts()
        demonstrate_top_n(connection)
        demonstrate_filter_then_limit(connection)
        demonstrate_distinct_and_limit(connection)
        demonstrate_aggregation_and_limit(connection)
        demonstrate_join_and_limit(connection)
        demonstrate_offset_edge_cases(connection)
        demonstrate_has_next(connection)
        demonstrate_count_tradeoff(connection)
        demonstrate_filtered_pagination(connection)
        demonstrate_keyset_pagination(connection)
        demonstrate_composite_keyset(connection)
        demonstrate_pagination_comparison()
        demonstrate_offset_consistency_problem(connection)
        demonstrate_api_response(connection)
        demonstrate_cursor_api(connection)
        demonstrate_parameterization(connection)
        demonstrate_sql_injection_risk()
        demonstrate_large_offset_concept()
        demonstrate_indexing(connection)
        demonstrate_query_plan(connection)
        demonstrate_page_size_limits()
        demonstrate_page_and_offset_difference()
        demonstrate_sort_direction(connection)
        demonstrate_null_ordering(connection)
        test_page_boundaries(connection)
        demonstrate_tie_breaking(connection)
        demonstrate_descending_keyset(connection)
        demonstrate_search_pagination(connection)
        demonstrate_limit_expressions(connection)
        demonstrate_total_count(connection)
        demonstrate_consistency_concept()
        demonstrate_common_mistakes()
        print_syntax_reference()
        demonstrate_design_decisions()
        demonstrate_production_helper(connection)
        demonstrate_benchmark_methodology()
        print_security_checklist()
        demonstrate_safe_dynamic_sorting(connection)
        print_production_checklist()

    finally:
        connection.close()


# =============================================================================
# 49. ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_study_program()
