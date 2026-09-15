"""
PostgreSQL DISTINCT, duplicate elimination, and DISTINCT ON
============================================================

This standalone study program teaches:

1. What duplicate rows mean in a relational result
2. SELECT DISTINCT
3. DISTINCT across one and multiple columns
4. NULL behavior with DISTINCT
5. DISTINCT versus GROUP BY
6. DISTINCT versus aggregation
7. DISTINCT ON in PostgreSQL
8. DISTINCT ON and ORDER BY
9. Selecting the first row from each group
10. Why ORDER BY is essential with DISTINCT ON
11. PostgreSQL's DISTINCT ON ordering rule
12. Common mistakes
13. Query design and readability
14. Performance and indexes
15. Pagination considerations
16. Real-world deduplication patterns
17. SQL NULL semantics relevant to duplicate elimination
18. Python simulations of PostgreSQL result-set behavior
19. Testing and validation

The program does not require PostgreSQL or third-party Python packages.
It contains executable in-memory demonstrations plus PostgreSQL SQL examples.

Important distinction:
- SELECT DISTINCT is standard SQL.
- DISTINCT ON is PostgreSQL-specific.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Callable, Iterable, Sequence


# ---------------------------------------------------------------------------
# Section 1: Basic data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Customer:
    customer_id: int
    name: str
    city: str | None


@dataclass(frozen=True)
class LoginEvent:
    event_id: int
    customer_id: int
    event_time: str
    ip_address: str


@dataclass(frozen=True)
class ProductPrice:
    product_id: int
    product_name: str
    price: Decimal
    observed_at: str


def print_title(title: str) -> None:
    """Print a readable section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def print_rows(rows: Iterable[Any], title: str | None = None) -> None:
    """Print a small collection of rows in a readable form."""
    if title:
        print(f"\n{title}")

    rows = list(rows)

    if not rows:
        print("(no rows)")
        return

    for index, row in enumerate(rows, start=1):
        print(f"{index:>3}: {row}")


# ---------------------------------------------------------------------------
# Section 2: Understanding duplicate rows
# ---------------------------------------------------------------------------

def demo_raw_duplicates() -> None:
    print_title("1. Duplicate rows in a result set")

    cities = [
        ("Lucknow",),
        ("Delhi",),
        ("Lucknow",),
        ("Mumbai",),
        ("Delhi",),
        ("Delhi",),
    ]

    print_rows(cities, "Result without DISTINCT:")

    print(
        "\nThe same value can occur multiple times because SQL normally returns "
        "every qualifying row."
    )


# ---------------------------------------------------------------------------
# Section 3: A Python equivalent of SELECT DISTINCT
# ---------------------------------------------------------------------------

def distinct_rows(rows: Iterable[Sequence[Any]]) -> list[tuple[Any, ...]]:
    """
    Remove duplicate rows while preserving the first occurrence.

    PostgreSQL's SELECT DISTINCT returns one row for each unique combination
    of selected values. The order of rows should not be assumed unless an
    ORDER BY clause is specified.
    """
    seen: set[tuple[Any, ...]] = set()
    result: list[tuple[Any, ...]] = []

    for row in rows:
        normalized = tuple(row)

        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result


def demo_select_distinct() -> None:
    print_title("2. SELECT DISTINCT")

    rows = [
        ("Lucknow",),
        ("Delhi",),
        ("Lucknow",),
        ("Mumbai",),
        ("Delhi",),
        ("Delhi",),
    ]

    unique_cities = distinct_rows(rows)

    print_rows(unique_cities, "Equivalent conceptual result of SELECT DISTINCT city:")

    print(
        """
PostgreSQL query:

SELECT DISTINCT city
FROM customers;

DISTINCT applies to the complete SELECT list. If the SELECT list contains
one column, uniqueness is determined by that column. If it contains several
columns, uniqueness is determined by the combination of all selected columns.
"""
    )


# ---------------------------------------------------------------------------
# Section 4: DISTINCT over multiple columns
# ---------------------------------------------------------------------------

def demo_multi_column_distinct() -> None:
    print_title("3. DISTINCT over multiple columns")

    customer_locations = [
        ("Alice", "Delhi"),
        ("Bob", "Delhi"),
        ("Alice", "Delhi"),
        ("Alice", "Mumbai"),
        ("Bob", "Delhi"),
        ("Bob", "Mumbai"),
    ]

    result = distinct_rows(customer_locations)

    print_rows(result, "Unique (name, city) combinations:")

    print(
        """
SQL:

SELECT DISTINCT name, city
FROM customers;

The pair ('Alice', 'Delhi') is duplicated and is therefore returned once.

The pair ('Alice', 'Mumbai') is different, so it remains a separate result.

DISTINCT does NOT independently deduplicate each column. It deduplicates
complete result rows.
"""
    )


# ---------------------------------------------------------------------------
# Section 5: NULL and DISTINCT
# ---------------------------------------------------------------------------

def sql_distinct_key(value: Any) -> Any:
    """
    Conceptual normalization for DISTINCT.

    SQL has three-valued logic, where NULL is not equal to NULL in ordinary
    comparisons. DISTINCT is different: duplicate elimination treats NULL
    occurrences as belonging to the same duplicate class for result purposes.

    This function therefore does not need a special replacement for None:
    Python's None can act as the same key value for this educational model.
    """
    return value


def distinct_sql(rows: Iterable[Sequence[Any]]) -> list[tuple[Any, ...]]:
    """Educational DISTINCT implementation with SQL-like NULL grouping."""
    seen: set[tuple[Any, ...]] = set()
    result: list[tuple[Any, ...]] = []

    for row in rows:
        key = tuple(sql_distinct_key(value) for value in row)

        if key not in seen:
            seen.add(key)
            result.append(tuple(row))

    return result


def demo_null_distinct() -> None:
    print_title("4. NULL behavior")

    rows = [
        ("Delhi",),
        (None,),
        ("Delhi",),
        (None,),
        ("Mumbai",),
    ]

    result = distinct_sql(rows)

    print_rows(result, "Conceptual SELECT DISTINCT result:")

    print(
        """
For duplicate elimination, multiple NULL values collapse into one DISTINCT
result value.

This should not be confused with:

SELECT NULL = NULL;

which does not produce TRUE. NULL represents an unknown/missing value and
normal comparisons involving NULL use SQL's three-valued logic.
"""
    )


# ---------------------------------------------------------------------------
# Section 6: DISTINCT versus SELECT without DISTINCT
# ---------------------------------------------------------------------------

def demo_distinct_comparison() -> None:
    print_title("5. SELECT versus SELECT DISTINCT")

    emails = [
        ("alice@example.com",),
        ("bob@example.com",),
        ("alice@example.com",),
        ("carol@example.com",),
        ("bob@example.com",),
    ]

    print_rows(emails, "SELECT email:")
    print_rows(distinct_sql(emails), "SELECT DISTINCT email:")

    print(
        """
The first query preserves multiplicity.
The second query performs duplicate elimination.

This distinction is important when a query is intended to count events,
return every transaction, or preserve row-level information.
"""
    )


# ---------------------------------------------------------------------------
# Section 7: DISTINCT is not the same as GROUP BY
# ---------------------------------------------------------------------------

def group_by_count(
    rows: Iterable[Sequence[Any]],
    key_index: int,
) -> list[tuple[Any, int]]:
    """Simple in-memory grouping and counting."""
    counts: dict[Any, int] = {}

    for row in rows:
        key = row[key_index]
        counts[key] = counts.get(key, 0) + 1

    return list(counts.items())


def demo_distinct_vs_group_by() -> None:
    print_title("6. DISTINCT versus GROUP BY")

    orders = [
        (1, "Delhi", 500),
        (2, "Delhi", 700),
        (3, "Mumbai", 900),
        (4, "Delhi", 300),
        (5, "Mumbai", 400),
    ]

    unique_cities = distinct_sql([(row[1],) for row in orders])
    city_counts = group_by_count(orders, key_index=1)

    print_rows(unique_cities, "DISTINCT city:")
    print_rows(city_counts, "GROUP BY city with COUNT:")

    print(
        """
DISTINCT answers:

"Which unique values occur?"

GROUP BY usually answers:

"How should rows be divided into groups so that each group can be
aggregated or otherwise processed?"

Examples:

SELECT DISTINCT city
FROM orders;

SELECT city, COUNT(*)
FROM orders
GROUP BY city;

GROUP BY can sometimes produce the same unique-key result as DISTINCT,
but the two constructs express different intentions.
"""
    )


# ---------------------------------------------------------------------------
# Section 8: DISTINCT with expressions
# ---------------------------------------------------------------------------

def demo_distinct_expression() -> None:
    print_title("7. DISTINCT can operate on expressions")

    names = [
        ("Alice",),
        ("alice",),
        ("ALICE",),
        ("Bob",),
        ("bob",),
    ]

    normalized = [(row[0].lower(),) for row in names]

    print_rows(
        distinct_sql(normalized),
        "Conceptual SELECT DISTINCT LOWER(name):",
    )

    print(
        """
PostgreSQL:

SELECT DISTINCT LOWER(name)
FROM customers;

The expression is evaluated first, then duplicate elimination is performed
on the resulting values.

Therefore Alice, alice, and ALICE can become one result value when LOWER()
is applied.
"""
    )


# ---------------------------------------------------------------------------
# Section 9: DISTINCT with ORDER BY
# ---------------------------------------------------------------------------

def demo_distinct_order_by() -> None:
    print_title("8. DISTINCT and ORDER BY")

    cities = [
        ("Mumbai",),
        ("Delhi",),
        ("Lucknow",),
        ("Delhi",),
        ("Chennai",),
    ]

    unique_cities = distinct_sql(cities)

    print_rows(
        sorted(unique_cities, key=lambda row: row[0]),
        "Conceptual SELECT DISTINCT city ORDER BY city:",
    )

    print(
        """
SQL:

SELECT DISTINCT city
FROM customers
ORDER BY city;

DISTINCT determines uniqueness.
ORDER BY determines presentation order.

A crucial principle is:

Without ORDER BY, SQL does not promise a particular output ordering.

Do not rely on the apparent order produced by a particular execution plan.
"""
    )


# ---------------------------------------------------------------------------
# Section 10: DISTINCT ON
# ---------------------------------------------------------------------------

def distinct_on(
    rows: Iterable[Sequence[Any]],
    key_function: Callable[[Sequence[Any]], Any],
) -> list[Sequence[Any]]:
    """
    Educational model of PostgreSQL DISTINCT ON.

    DISTINCT ON keeps the first row encountered for each key.

    PostgreSQL determines which row is "first" according to the query's
    ORDER BY. Therefore this function intentionally assumes that rows have
    already been ordered according to the desired rule.
    """
    seen: set[Any] = set()
    result: list[Sequence[Any]] = []

    for row in rows:
        key = key_function(row)

        if key not in seen:
            seen.add(key)
            result.append(row)

    return result


def demo_distinct_on_basic() -> None:
    print_title("9. PostgreSQL DISTINCT ON")

    logins = [
        (101, 1, "2026-09-15 08:10:00", "10.0.0.1"),
        (102, 1, "2026-09-15 09:20:00", "10.0.0.2"),
        (103, 2, "2026-09-15 07:15:00", "10.0.0.3"),
        (104, 2, "2026-09-15 11:40:00", "10.0.0.4"),
        (105, 3, "2026-09-15 10:00:00", "10.0.0.5"),
    ]

    ordered = sorted(
        logins,
        key=lambda row: (row[1], row[2]),
        reverse=False,
    )

    first_per_customer = distinct_on(
        ordered,
        key_function=lambda row: row[1],
    )

    print_rows(
        first_per_customer,
        "First login per customer after ordering by customer_id and time:",
    )

    print(
        """
PostgreSQL-specific syntax:

SELECT DISTINCT ON (customer_id)
       customer_id,
       event_id,
       event_time,
       ip_address
FROM login_events
ORDER BY customer_id, event_time;

DISTINCT ON differs fundamentally from ordinary DISTINCT.

SELECT DISTINCT eliminates duplicate result rows.

SELECT DISTINCT ON (customer_id) selects one complete row from each
customer_id group. The ORDER BY determines which row wins.
"""
    )


# ---------------------------------------------------------------------------
# Section 11: Latest row per group
# ---------------------------------------------------------------------------

def demo_latest_row_per_group() -> None:
    print_title("10. DISTINCT ON for latest row per group")

    prices = [
        (10, "Laptop", Decimal("70000"), "2026-09-10 10:00:00"),
        (10, "Laptop", Decimal("69000"), "2026-09-12 12:00:00"),
        (10, "Laptop", Decimal("68000"), "2026-09-14 15:30:00"),
        (20, "Phone", Decimal("30000"), "2026-09-11 09:00:00"),
        (20, "Phone", Decimal("29500"), "2026-09-14 17:00:00"),
        (30, "Tablet", Decimal("25000"), "2026-09-13 14:00:00"),
    ]

    ordered = sorted(
        prices,
        key=lambda row: (row[0], row[3]),
        reverse=True,
    )

    latest = distinct_on(
        ordered,
        key_function=lambda row: row[0],
    )

    print_rows(latest, "Latest price per product:")

    print(
        """
Canonical PostgreSQL pattern:

SELECT DISTINCT ON (product_id)
       product_id,
       product_name,
       price,
       observed_at
FROM product_prices
ORDER BY product_id, observed_at DESC;

The ORDER BY says:

1. Group the rows by product_id for DISTINCT ON.
2. Within each product, place the newest observation first.
3. Keep the first row.

This is one of the most useful practical applications of DISTINCT ON.
"""
    )


# ---------------------------------------------------------------------------
# Section 12: The ORDER BY prefix rule
# ---------------------------------------------------------------------------

def demo_distinct_on_order_rule() -> None:
    print_title("11. DISTINCT ON and the ORDER BY prefix rule")

    print(
        """
PostgreSQL requires the expressions in DISTINCT ON to match the leftmost
expressions in ORDER BY.

Valid:

SELECT DISTINCT ON (customer_id)
       customer_id, event_id, event_time
FROM login_events
ORDER BY customer_id, event_time DESC;

Here customer_id is the leftmost ORDER BY expression.

Another valid example:

SELECT DISTINCT ON (customer_id, product_id)
       customer_id, product_id, price
FROM prices
ORDER BY customer_id, product_id, price DESC;

Invalid pattern:

SELECT DISTINCT ON (customer_id)
       customer_id, event_id
FROM login_events
ORDER BY event_time DESC, customer_id;

The ordering does not begin with customer_id, so PostgreSQL rejects this
kind of DISTINCT ON / ORDER BY combination.

The rule exists because PostgreSQL needs the ordering to define which row
is first within each DISTINCT ON group.
"""
    )


# ---------------------------------------------------------------------------
# Section 13: Tie-breaking
# ---------------------------------------------------------------------------

def demo_tie_breaking() -> None:
    print_title("12. Tie-breaking with DISTINCT ON")

    events = [
        (1, "2026-09-15 10:00:00", 900),
        (1, "2026-09-15 10:00:00", 901),
        (1, "2026-09-15 09:00:00", 899),
        (2, "2026-09-15 12:00:00", 700),
        (2, "2026-09-15 12:00:00", 701),
    ]

    ordered = sorted(
        events,
        key=lambda row: (row[0], row[1], row[2]),
        reverse=True,
    )

    result = distinct_on(ordered, lambda row: row[0])

    print_rows(result, "Deterministically selected rows:")

    print(
        """
Suppose two rows have the same timestamp.

ORDER BY customer_id, event_time DESC

may leave two candidate rows tied on event_time.

A deterministic query can add a unique or sufficiently selective
tie-breaker:

ORDER BY customer_id,
         event_time DESC,
         event_id DESC;

Now the larger event_id wins when timestamps are equal.

This matters when the selected row is used for auditing, reporting,
synchronization, or downstream processing.
"""
    )


# ---------------------------------------------------------------------------
# Section 14: DISTINCT ON versus window functions
# ---------------------------------------------------------------------------

def row_number_per_group(
    rows: Iterable[Sequence[Any]],
    group_index: int,
    sort_key: Callable[[Sequence[Any]], Any],
    reverse: bool = True,
) -> list[tuple[Sequence[Any], int]]:
    """Educational ROW_NUMBER() equivalent."""
    grouped: dict[Any, list[Sequence[Any]]] = {}

    for row in rows:
        grouped.setdefault(row[group_index], []).append(row)

    result: list[tuple[Sequence[Any], int]] = []

    for group_rows in grouped.values():
        ordered = sorted(group_rows, key=sort_key, reverse=reverse)

        for number, row in enumerate(ordered, start=1):
            result.append((row, number))

    return result


def demo_distinct_on_vs_row_number() -> None:
    print_title("13. DISTINCT ON versus ROW_NUMBER()")

    rows = [
        (1, "Alice", "2026-09-10", 500),
        (1, "Alice", "2026-09-15", 700),
        (2, "Bob", "2026-09-12", 600),
        (2, "Bob", "2026-09-14", 800),
    ]

    ranked = row_number_per_group(
        rows,
        group_index=0,
        sort_key=lambda row: row[2],
        reverse=True,
    )

    winners = [row for row, rank in ranked if rank == 1]

    print_rows(winners, "ROW_NUMBER() = 1 conceptual result:")

    print(
        """
A window-function equivalent is:

SELECT customer_id,
       name,
       event_date,
       amount
FROM (
    SELECT customer_id,
           name,
           event_date,
           amount,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id
               ORDER BY event_date DESC
           ) AS rn
    FROM events
) ranked
WHERE rn = 1;

DISTINCT ON is often concise for "one row per group."

ROW_NUMBER() is more flexible when you need:
- rank 1, 2, 3, ...
- multiple rows per group
- ranking information in the result
- more complex analytical logic
"""
    )


# ---------------------------------------------------------------------------
# Section 15: DISTINCT versus aggregation
# ---------------------------------------------------------------------------

def demo_distinct_vs_max() -> None:
    print_title("14. DISTINCT ON versus MAX()")

    prices = [
        (1, "Laptop", Decimal("70000"), "2026-09-10"),
        (1, "Laptop", Decimal("68000"), "2026-09-14"),
        (2, "Phone", Decimal("30000"), "2026-09-13"),
        (2, "Phone", Decimal("29000"), "2026-09-15"),
    ]

    print_rows(prices, "Input price history:")

    print(
        """
A query such as:

SELECT product_id, MAX(observed_at)
FROM product_prices
GROUP BY product_id;

returns the maximum date.

It does not automatically return the other columns from the same row.

DISTINCT ON can return the complete row:

SELECT DISTINCT ON (product_id)
       product_id,
       product_name,
       price,
       observed_at
FROM product_prices
ORDER BY product_id, observed_at DESC;

This distinction is important. Finding the maximum value and retrieving the
entire row associated with that maximum are related but different problems.
"""
    )


# ---------------------------------------------------------------------------
# Section 16: Common mistakes
# ---------------------------------------------------------------------------

def demo_common_mistakes() -> None:
    print_title("15. Common mistakes")

    mistakes = [
        (
            "Assuming DISTINCT chooses a preferred row",
            "DISTINCT removes duplicate result rows. It does not choose the latest "
            "or highest-valued row from a group."
        ),
        (
            "Using DISTINCT ON without meaningful ORDER BY",
            "The selected row for each group can be unpredictable when the query "
            "does not define the desired ordering."
        ),
        (
            "Forgetting the DISTINCT ON ordering rule",
            "The DISTINCT ON expressions must match the leftmost ORDER BY expressions."
        ),
        (
            "Using DISTINCT to fix a bad JOIN",
            "DISTINCT can hide duplicate-producing joins instead of fixing the "
            "relationship or join condition."
        ),
        (
            "Selecting extra columns with ordinary DISTINCT",
            "Adding a column to SELECT can create new unique combinations and therefore "
            "increase the number of result rows."
        ),
        (
            "Assuming DISTINCT means indexed lookup",
            "Duplicate elimination may require sorting, hashing, or another execution "
            "strategy depending on the query and available indexes."
        ),
    ]

    for mistake, explanation in mistakes:
        print(f"\nMistake: {mistake}\nReason: {explanation}")


# ---------------------------------------------------------------------------
# Section 17: Why DISTINCT sometimes hides JOIN problems
# ---------------------------------------------------------------------------

def demo_bad_join_pattern() -> None:
    print_title("16. DISTINCT should not be used as a universal duplicate fixer")

    customers = [
        (1, "Alice"),
        (2, "Bob"),
    ]

    orders = [
        (101, 1),
        (102, 1),
        (103, 2),
    ]

    joined = [
        (customer_id, name, order_id)
        for customer_id, name in customers
        for order_id, order_customer_id in orders
        if customer_id == order_customer_id
    ]

    print_rows(joined, "Correct one-to-many join result:")

    unique_customers = distinct_sql([(row[0], row[1]) for row in joined])

    print_rows(
        unique_customers,
        "DISTINCT customer projection:",
    )

    print(
        """
If the application expects one row per customer, SELECT DISTINCT may be a
legitimate projection.

But if the application expected every order, adding DISTINCT would destroy
information.

The right question is not:

"How do I remove duplicates?"

It is:

"Why does the result contain multiple rows, and is that multiplicity correct?"
"""
    )


# ---------------------------------------------------------------------------
# Section 18: Multiple DISTINCT ON expressions
# ---------------------------------------------------------------------------

def demo_composite_distinct_on() -> None:
    print_title("17. DISTINCT ON over multiple columns")

    rows = [
        ("Delhi", "Laptop", 70000, "2026-09-10"),
        ("Delhi", "Laptop", 68000, "2026-09-14"),
        ("Delhi", "Phone", 30000, "2026-09-12"),
        ("Mumbai", "Laptop", 72000, "2026-09-11"),
        ("Mumbai", "Laptop", 69000, "2026-09-15"),
    ]

    ordered = sorted(
        rows,
        key=lambda row: (row[0], row[1], row[3]),
        reverse=True,
    )

    result = distinct_on(
        ordered,
        key_function=lambda row: (row[0], row[1]),
    )

    print_rows(
        result,
        "Latest price per (city, product) combination:",
    )

    print(
        """
PostgreSQL:

SELECT DISTINCT ON (city, product)
       city,
       product,
       price,
       observed_at
FROM product_prices
ORDER BY city, product, observed_at DESC;

The DISTINCT ON key can contain multiple expressions.
"""
    )


# ---------------------------------------------------------------------------
# Section 19: SQL NULL ordering and DISTINCT ON
# ---------------------------------------------------------------------------

def demo_null_ordering() -> None:
    print_title("18. NULL ordering and DISTINCT ON")

    print(
        """
DISTINCT ON can select rows based on an ORDER BY expression that contains
NULL values.

PostgreSQL's ordering of NULL values depends on ASC/DESC and explicit
NULLS FIRST / NULLS LAST.

For deterministic intent, write the NULL behavior explicitly when it matters:

ORDER BY customer_id,
         last_seen DESC NULLS LAST;

or:

ORDER BY customer_id,
         last_seen DESC NULLS FIRST;

This is especially useful when "latest record" logic can encounter missing
timestamps.
"""
    )


# ---------------------------------------------------------------------------
# Section 20: DISTINCT and JOIN examples
# ---------------------------------------------------------------------------

def demo_distinct_join() -> None:
    print_title("19. DISTINCT with JOIN")

    customer_tags = [
        (1, "Alice", "python"),
        (1, "Alice", "sql"),
        (1, "Alice", "python"),
        (2, "Bob", "sql"),
    ]

    print_rows(customer_tags, "Joined/projection-like data:")

    unique_customer_tags = distinct_sql(
        [(row[1], row[2]) for row in customer_tags]
    )

    print_rows(
        unique_customer_tags,
        "SELECT DISTINCT customer_name, tag:",
    )

    print(
        """
When a JOIN creates repeated combinations, DISTINCT can be appropriate if
the required output is genuinely a set of unique projected combinations.

If duplicates represent meaningful facts, DISTINCT should not be used merely
to make the result look cleaner.
"""
    )


# ---------------------------------------------------------------------------
# Section 21: PostgreSQL SQL catalog
# ---------------------------------------------------------------------------

POSTGRESQL_SQL_EXAMPLES = {
    "ordinary_distinct": """
SELECT DISTINCT city
FROM customers;
""".strip(),
    "multi_column_distinct": """
SELECT DISTINCT city, country
FROM customers;
""".strip(),
    "ordered_distinct": """
SELECT DISTINCT city
FROM customers
ORDER BY city;
""".strip(),
    "distinct_on_latest": """
SELECT DISTINCT ON (customer_id)
       customer_id,
       order_id,
       order_date,
       total_amount
FROM orders
ORDER BY customer_id, order_date DESC, order_id DESC;
""".strip(),
    "distinct_on_cheapest": """
SELECT DISTINCT ON (product_id)
       product_id,
       product_name,
       price,
       observed_at
FROM product_prices
ORDER BY product_id, price ASC, observed_at DESC;
""".strip(),
    "distinct_on_composite_key": """
SELECT DISTINCT ON (customer_id, product_id)
       customer_id,
       product_id,
       price,
       observed_at
FROM product_prices
ORDER BY customer_id, product_id, observed_at DESC;
""".strip(),
}


def show_sql_catalog() -> None:
    print_title("20. PostgreSQL SQL examples")

    for name, sql in POSTGRESQL_SQL_EXAMPLES.items():
        print(f"\n{name}:\n{sql}")


# ---------------------------------------------------------------------------
# Section 22: Query intent comparison
# ---------------------------------------------------------------------------

def demo_query_intent() -> None:
    print_title("21. Choosing the correct PostgreSQL construct")

    comparisons = [
        ("Need unique projected values", "SELECT DISTINCT"),
        ("Need one preferred complete row per group", "SELECT DISTINCT ON"),
        ("Need ranking within every group", "ROW_NUMBER()"),
        ("Need counts, sums, averages", "GROUP BY + aggregate"),
        ("Need maximum value only", "MAX()"),
        ("Need maximum value and the complete associated row", "DISTINCT ON or window function"),
        ("Need every source row", "Plain SELECT without duplicate elimination"),
    ]

    for requirement, construct in comparisons:
        print(f"{requirement:<62} -> {construct}")


# ---------------------------------------------------------------------------
# Section 23: Performance discussion
# ---------------------------------------------------------------------------

def demo_performance_concepts() -> None:
    print_title("22. Performance considerations")

    print(
        """
DISTINCT can require PostgreSQL to identify duplicate result rows.

Depending on the query, PostgreSQL may use:
- Sort-based processing
- Hash-based processing
- Index-supported strategies
- Other plan-specific mechanisms

Always inspect the real query plan when performance matters:

EXPLAIN
SELECT DISTINCT city
FROM customers;

For actual runtime information:

EXPLAIN (ANALYZE, BUFFERS)
SELECT DISTINCT city
FROM customers;

Important factors include:
- Number of input rows
- Width of each row
- Number of unique values
- Available indexes
- Statistics
- work_mem
- Join cardinality
- Sort requirements
- Whether the query can exploit an ordered index

DISTINCT ON has an important ordering requirement. A useful index for a
"latest row per group" query may resemble:

CREATE INDEX ON orders (customer_id, order_date DESC, order_id DESC);

The exact optimal index depends on the real query, predicates, selected
columns, PostgreSQL version, table size, data distribution, and workload.

Do not add indexes solely because a query contains DISTINCT. Measure first.
"""
    )


# ---------------------------------------------------------------------------
# Section 24: Memory and complexity of the educational implementation
# ---------------------------------------------------------------------------

def demo_algorithmic_complexity() -> None:
    print_title("23. Complexity of the Python educational model")

    rows = [
        ("A",),
        ("B",),
        ("A",),
        ("C",),
        ("B",),
    ]

    result = distinct_sql(rows)

    print_rows(result)

    print(
        """
The Python set-based DISTINCT implementation has expected O(n) insertion/
membership behavior for n rows, with O(u) additional memory for u unique
rows.

A database engine is more sophisticated. PostgreSQL can choose different
execution strategies and can optimize based on indexes, statistics, memory,
parallelism, and query structure.

The educational algorithm therefore demonstrates the logical operation, not
PostgreSQL's exact internal executor implementation.
"""
    )


# ---------------------------------------------------------------------------
# Section 25: Production-safe query construction
# ---------------------------------------------------------------------------

def demo_parameterization() -> None:
    print_title("24. Parameterization and security")

    print(
        """
DISTINCT itself is not an injection vulnerability.

The security risk appears when dynamic SQL is constructed unsafely.

Unsafe conceptual pattern:

sql = "SELECT DISTINCT city FROM customers WHERE country = '" + user_input + "'";

Use parameterized queries through the PostgreSQL client library instead.

For example, a PostgreSQL Python application using psycopg would conceptually
use a parameter placeholder and pass the value separately.

Parameterized values should be used for data values. Identifiers such as
column names require a different safe composition mechanism provided by the
database client library.

The examples in this study intentionally do not connect to a live database,
so no external database credentials are required.
"""
    )


# ---------------------------------------------------------------------------
# Section 26: Testing DISTINCT behavior
# ---------------------------------------------------------------------------

def assert_unique(rows: Sequence[Sequence[Any]]) -> None:
    normalized = [tuple(row) for row in rows]
    assert len(normalized) == len(set(normalized))


def demo_testing() -> None:
    print_title("25. Testing duplicate elimination")

    input_rows = [
        ("Delhi",),
        ("Delhi",),
        ("Mumbai",),
        ("Mumbai",),
        ("Lucknow",),
    ]

    result = distinct_sql(input_rows)

    assert_unique(result)
    assert len(result) == 3
    assert ("Delhi",) in result
    assert ("Mumbai",) in result
    assert ("Lucknow",) in result

    null_result = distinct_sql([(None,), (None,), ("Delhi",)])

    assert len(null_result) == 2

    print("All DISTINCT behavior assertions passed.")

    print(
        """
Useful production tests should include:
- No duplicates
- Many duplicates
- No duplicates at all
- NULL values
- Composite keys
- Empty input
- Ties in ORDER BY
- Missing ordering columns
- Very large groups
- Unexpected JOIN multiplicity
"""
    )


# ---------------------------------------------------------------------------
# Section 27: Empty input and edge cases
# ---------------------------------------------------------------------------

def demo_edge_cases() -> None:
    print_title("26. Edge cases")

    print_rows(
        distinct_sql([]),
        "DISTINCT over an empty result:",
    )

    print_rows(
        distinct_sql([("A", "X"), ("A", "X")]),
        "Only one unique composite row:",
    )

    print_rows(
        distinct_sql([("A", None), ("A", None), ("A", "X")]),
        "Composite values containing NULL:",
    )

    print(
        """
Edge-case reasoning matters because duplicate elimination operates on the
entire selected result row, not on an informal idea of "same record."
"""
    )


# ---------------------------------------------------------------------------
# Section 28: Full practical case study
# ---------------------------------------------------------------------------

def latest_customer_orders(
    orders: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Simulate:

    SELECT DISTINCT ON (customer_id)
           customer_id, order_id, order_date, total_amount
    FROM orders
    ORDER BY customer_id, order_date DESC, order_id DESC;
    """
    ordered = sorted(
        orders,
        key=lambda order: (
            order["customer_id"],
            order["order_date"],
            order["order_id"],
        ),
        reverse=True,
    )

    result = distinct_on(
        ordered,
        key_function=lambda order: order["customer_id"],
    )

    return list(result)


def demo_full_case_study() -> None:
    print_title("27. Practical case study: latest order per customer")

    orders = [
        {
            "customer_id": 1,
            "order_id": 1001,
            "order_date": "2026-09-10",
            "total_amount": Decimal("1500.00"),
        },
        {
            "customer_id": 1,
            "order_id": 1002,
            "order_date": "2026-09-14",
            "total_amount": Decimal("2400.00"),
        },
        {
            "customer_id": 2,
            "order_id": 2001,
            "order_date": "2026-09-12",
            "total_amount": Decimal("900.00"),
        },
        {
            "customer_id": 2,
            "order_id": 2002,
            "order_date": "2026-09-12",
            "total_amount": Decimal("1200.00"),
        },
        {
            "customer_id": 3,
            "order_id": 3001,
            "order_date": "2026-09-13",
            "total_amount": Decimal("1800.00"),
        },
    ]

    latest = latest_customer_orders(orders)

    print_rows(latest, "Latest order per customer:")

    print(
        """
PostgreSQL version:

SELECT DISTINCT ON (customer_id)
       customer_id,
       order_id,
       order_date,
       total_amount
FROM orders
ORDER BY customer_id,
         order_date DESC,
         order_id DESC;

The final order_id is a tie-breaker. If two orders have the same date,
the larger order_id wins.

This is a complete example of the logical relationship:

GROUP KEY
    ↓
ORDER WITHIN GROUP
    ↓
KEEP FIRST ROW
"""
    )


# ---------------------------------------------------------------------------
# Section 29: Date and time import demonstration
# ---------------------------------------------------------------------------

def demo_typed_values() -> None:
    print_title("28. Data types and DISTINCT")

    dates = [
        (date(2026, 9, 15),),
        (date(2026, 9, 15),),
        (date(2026, 9, 16),),
    ]

    amounts = [
        (Decimal("100.00"),),
        (Decimal("100.00"),),
        (Decimal("100.01"),),
    ]

    print_rows(distinct_sql(dates), "Distinct dates:")
    print_rows(distinct_sql(amounts), "Distinct decimal values:")

    print(
        """
PostgreSQL compares values according to their data types and relevant type
semantics. Choosing an appropriate database type is therefore part of correct
duplicate analysis.

For example, NUMERIC is generally preferable to floating-point types for
exact monetary calculations.
"""
    )


# ---------------------------------------------------------------------------
# Section 30: DISTINCT in subqueries
# ---------------------------------------------------------------------------

def demo_distinct_subquery() -> None:
    print_title("29. DISTINCT inside a subquery")

    print(
        """
A DISTINCT result can be used as an input relation:

SELECT c.customer_id, c.name
FROM customers AS c
JOIN (
    SELECT DISTINCT customer_id
    FROM orders
) AS active_customers
    ON active_customers.customer_id = c.customer_id;

This pattern can express:

"Return customers that appear in the order table, using a deduplicated
customer_id relation."

The optimizer may transform the query internally, so the SQL text does not
necessarily correspond one-to-one with executor operations.
"""
    )


# ---------------------------------------------------------------------------
# Section 31: DISTINCT and set semantics
# ---------------------------------------------------------------------------

def demo_set_semantics() -> None:
    print_title("30. SQL bags, sets, and DISTINCT")

    print(
        """
Relational theory often discusses sets, where duplicate tuples do not exist.

SQL query results generally behave more like multisets, also called bags:
duplicate rows can occur.

DISTINCT requests duplicate elimination and moves the result toward set-like
semantics.

For example:

SELECT city FROM customers;

can return:

Delhi
Delhi
Mumbai

while:

SELECT DISTINCT city FROM customers;

returns one Delhi and one Mumbai.

This distinction is fundamental to understanding why DISTINCT exists.
"""
    )


# ---------------------------------------------------------------------------
# Section 32: Production checklist
# ---------------------------------------------------------------------------

def print_production_checklist() -> None:
    print_title("31. Production checklist")

    checklist = [
        "Identify whether duplicates are actually incorrect.",
        "Inspect JOIN cardinality before adding DISTINCT.",
        "Use SELECT DISTINCT when the entire selected row must be unique.",
        "Use DISTINCT ON when PostgreSQL-specific one-row-per-group behavior is desired.",
        "Use ORDER BY with DISTINCT ON to define which row wins.",
        "Ensure DISTINCT ON expressions form the leftmost ORDER BY expressions.",
        "Add deterministic tie-breakers when multiple rows can tie.",
        "Consider ROW_NUMBER() when ranking or multiple rows per group are required.",
        "Use GROUP BY when aggregation is part of the requirement.",
        "Use EXPLAIN and EXPLAIN ANALYZE for performance investigations.",
        "Consider indexes that support filtering and ordering when justified.",
        "Do not assume output order without ORDER BY.",
        "Use parameterized queries for user-supplied values.",
        "Test NULL values and empty result sets.",
        "Validate the result against business semantics, not only row counts.",
    ]

    for item in checklist:
        print(f"[ ] {item}")


# ---------------------------------------------------------------------------
# Section 33: Main execution
# ---------------------------------------------------------------------------

def main() -> None:
    print_title("PostgreSQL DISTINCT Study Program")

    print(
        """
This program demonstrates the logical behavior of PostgreSQL duplicate
elimination constructs.

Core distinction:

SELECT DISTINCT
    -> remove duplicate result rows

SELECT DISTINCT ON (...)
    -> PostgreSQL-specific one-row-per-group selection,
       with ORDER BY controlling which row is retained
"""
    )

    demo_raw_duplicates()
    demo_select_distinct()
    demo_multi_column_distinct()
    demo_null_distinct()
    demo_distinct_comparison()
    demo_distinct_vs_group_by()
    demo_distinct_expression()
    demo_distinct_order_by()
    demo_distinct_on_basic()
    demo_latest_row_per_group()
    demo_distinct_on_order_rule()
    demo_tie_breaking()
    demo_distinct_on_vs_row_number()
    demo_distinct_vs_max()
    demo_common_mistakes()
    demo_bad_join_pattern()
    demo_composite_distinct_on()
    demo_null_ordering()
    demo_distinct_join()
    show_sql_catalog()
    demo_query_intent()
    demo_performance_concepts()
    demo_algorithmic_complexity()
    demo_parameterization()
    demo_testing()
    demo_edge_cases()
    demo_full_case_study()
    demo_typed_values()
    demo_distinct_subquery()
    demo_set_semantics()
    print_production_checklist()

    print_title("Study complete")
    print(
        "The examples above can be used as a reference when writing and "
        "reviewing PostgreSQL DISTINCT and DISTINCT ON queries."
    )


if __name__ == "__main__":
    main()
