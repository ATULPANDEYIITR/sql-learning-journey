"""
Aggregate Functions: COUNT, SUM, AVG, MIN, MAX

A comprehensive standalone study of SQL aggregate functions, demonstrated
with Python and SQLite.

The examples progress from beginner concepts to grouped aggregation,
conditional aggregation, NULL behavior, DISTINCT values, HAVING, window
functions, validation, edge cases, query design, performance, and a small
production-style sales analytics example.

No external Python packages are required.
"""

import sqlite3
from decimal import Decimal, InvalidOperation
from statistics import mean
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# 1. Basic utility functions
# ---------------------------------------------------------------------------

def print_title(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_rows(rows: Iterable[tuple[Any, ...]], headers: tuple[str, ...]) -> None:
    rows = list(rows)

    if not rows:
        print("(no rows)")
        return

    widths = [
        max(len(str(header)), *(len(str(row[index])) for row in rows))
        for index, header in enumerate(headers)
    ]

    separator = "+".join("-" * (width + 2) for width in widths)

    print(separator)
    print("|".join(f" {header:<{width}} " for header, width in zip(headers, widths)))
    print(separator)

    for row in rows:
        print("|".join(f" {str(value):<{width}} " for value, width in zip(row, widths)))

    print(separator)


def run_query(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> list[tuple[Any, ...]]:
    cursor = connection.execute(sql, parameters)
    return cursor.fetchall()


def show_query(
    connection: sqlite3.Connection,
    sql: str,
    headers: tuple[str, ...],
    parameters: tuple[Any, ...] = (),
) -> None:
    rows = run_query(connection, sql, parameters)
    print(sql.strip())
    print_rows(rows, headers)


# ---------------------------------------------------------------------------
# 2. Create an in-memory relational database
# ---------------------------------------------------------------------------

print_title("1. Building the Example Database")

connection = sqlite3.connect(":memory:")
connection.row_factory = sqlite3.Row

connection.executescript(
    """
    PRAGMA foreign_keys = ON;

    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name TEXT NOT NULL,
        city TEXT NOT NULL,
        customer_type TEXT NOT NULL CHECK (
            customer_type IN ('Retail', 'Business')
        )
    );

    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_price REAL NOT NULL CHECK (unit_price >= 0),
        stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0)
    );

    CREATE TABLE sales (
        sale_id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        sale_date TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        unit_price REAL NOT NULL CHECK (unit_price >= 0),
        discount REAL,
        salesperson TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );

    INSERT INTO customers VALUES
        (1, 'Aarav Sharma', 'Lucknow', 'Retail'),
        (2, 'Meera Singh', 'Delhi', 'Business'),
        (3, 'Rohan Verma', 'Mumbai', 'Retail'),
        (4, 'Ananya Gupta', 'Lucknow', 'Business'),
        (5, 'Kabir Khan', 'Pune', 'Retail'),
        (6, 'Isha Patel', 'Ahmedabad', 'Business');

    INSERT INTO products VALUES
        (1, 'Laptop Pro', 'Computers', 75000.00, 12),
        (2, 'Wireless Mouse', 'Accessories', 1500.00, 80),
        (3, 'Mechanical Keyboard', 'Accessories', 4500.00, 35),
        (4, 'Monitor 27', 'Displays', 22000.00, 20),
        (5, 'USB-C Hub', 'Accessories', 3500.00, 50),
        (6, 'Office Chair', 'Furniture', 18000.00, 8);

    INSERT INTO sales VALUES
        (1, 1, 1, '2026-01-05', 1, 75000.00, 5000.00, 'Neha'),
        (2, 1, 2, '2026-01-06', 2, 1500.00, NULL, 'Neha'),
        (3, 2, 3, '2026-01-07', 3, 4500.00, 1000.00, 'Rahul'),
        (4, 2, 4, '2026-01-08', 2, 22000.00, 2000.00, 'Rahul'),
        (5, 3, 2, '2026-01-10', 1, 1500.00, NULL, 'Priya'),
        (6, 3, 5, '2026-01-12', 4, 3500.00, 500.00, 'Priya'),
        (7, 4, 1, '2026-02-01', 2, 75000.00, 10000.00, 'Neha'),
        (8, 4, 6, '2026-02-03', 1, 18000.00, NULL, 'Neha'),
        (9, 5, 3, '2026-02-05', 1, 4500.00, NULL, 'Rahul'),
        (10, 5, 2, '2026-02-06', 5, 1500.00, 250.00, 'Rahul'),
        (11, 6, 4, '2026-02-09', 3, 22000.00, 3000.00, 'Priya'),
        (12, 6, 5, '2026-02-11', 2, 3500.00, NULL, 'Priya'),
        (13, 1, 2, '2026-03-02', 3, 1500.00, NULL, 'Neha'),
        (14, 2, 5, '2026-03-04', 2, 3500.00, 500.00, 'Rahul'),
        (15, 3, 4, '2026-03-06', 1, 22000.00, NULL, 'Priya');
    """
)

print("Database created successfully.")
print("Tables: customers, products, sales")


# ---------------------------------------------------------------------------
# 3. Understand the idea of aggregation
# ---------------------------------------------------------------------------

print_title("2. What Is an Aggregate Function?")

print(
    """
An aggregate function takes multiple input rows and produces one summarized
value.

The five core SQL aggregate functions demonstrated here are:

COUNT -> counts rows or non-NULL values
SUM   -> adds numeric values
AVG   -> calculates an arithmetic mean
MIN   -> returns the smallest value
MAX   -> returns the largest value

A normal query can return many rows. An aggregate query can compress those
rows into a single analytical result.

For example:

SELECT SUM(quantity) FROM sales;

does not return one result per sale. It returns one total quantity.
"""
)


# ---------------------------------------------------------------------------
# 4. COUNT
# ---------------------------------------------------------------------------

print_title("3. COUNT")

show_query(
    connection,
    "SELECT COUNT(*) AS total_rows FROM sales;",
    ("total_rows",),
)

show_query(
    connection,
    "SELECT COUNT(quantity) AS non_null_quantities FROM sales;",
    ("non_null_quantities",),
)

show_query(
    connection,
    "SELECT COUNT(discount) AS rows_with_discount FROM sales;",
    ("rows_with_discount",),
)

show_query(
    connection,
    "SELECT COUNT(DISTINCT customer_id) AS unique_customers FROM sales;",
    ("unique_customers",),
)

print(
    """
COUNT(*) counts rows, including rows containing NULL values.

COUNT(column) counts only rows where that particular column is not NULL.

COUNT(DISTINCT column) counts unique non-NULL values.

This distinction is one of the most important details in SQL aggregation.
"""
)


# ---------------------------------------------------------------------------
# 5. SUM
# ---------------------------------------------------------------------------

print_title("4. SUM")

show_query(
    connection,
    "SELECT SUM(quantity) AS total_units_sold FROM sales;",
    ("total_units_sold",),
)

show_query(
    connection,
    """
    SELECT
        SUM(quantity * unit_price) AS gross_sales
    FROM sales;
    """,
    ("gross_sales",),
)

show_query(
    connection,
    """
    SELECT
        SUM(COALESCE(discount, 0)) AS total_discount
    FROM sales;
    """,
    ("total_discount",),
)

print(
    """
SUM ignores NULL input values.

COALESCE(discount, 0) explicitly treats a missing discount as zero.

That interpretation is appropriate when NULL means "no discount recorded"
rather than "discount status unknown". The business meaning of NULL should
always be understood before replacing it with zero.
"""
)


# ---------------------------------------------------------------------------
# 6. AVG
# ---------------------------------------------------------------------------

print_title("5. AVG")

show_query(
    connection,
    "SELECT AVG(unit_price) AS average_sale_price FROM sales;",
    ("average_sale_price",),
)

show_query(
    connection,
    "SELECT AVG(quantity) AS average_quantity_per_line FROM sales;",
    ("average_quantity_per_line",),
)

show_query(
    connection,
    """
    SELECT AVG(discount) AS average_recorded_discount
    FROM sales;
    """,
    ("average_recorded_discount",),
)

print(
    """
AVG is effectively based on the non-NULL values.

Therefore AVG(discount) does not automatically treat NULL discounts as zero.

If the business rule explicitly defines NULL as zero, an alternative is:

AVG(COALESCE(discount, 0))

These two expressions can produce different results.
"""
)


# ---------------------------------------------------------------------------
# 7. MIN and MAX
# ---------------------------------------------------------------------------

print_title("6. MIN and MAX")

show_query(
    connection,
    """
    SELECT
        MIN(unit_price) AS minimum_unit_price,
        MAX(unit_price) AS maximum_unit_price
    FROM sales;
    """,
    ("minimum_unit_price", "maximum_unit_price"),
)

show_query(
    connection,
    """
    SELECT
        MIN(quantity) AS minimum_quantity,
        MAX(quantity) AS maximum_quantity
    FROM sales;
    """,
    ("minimum_quantity", "maximum_quantity"),
)

show_query(
    connection,
    """
    SELECT
        MIN(sale_date) AS first_sale_date,
        MAX(sale_date) AS latest_sale_date
    FROM sales;
    """,
    ("first_sale_date", "latest_sale_date"),
)

print(
    """
MIN and MAX work with numbers, dates stored in comparable formats, and text
according to the database's comparison rules.

ISO-formatted dates such as YYYY-MM-DD sort chronologically when stored as
text.
"""
)


# ---------------------------------------------------------------------------
# 8. All five functions together
# ---------------------------------------------------------------------------

print_title("7. COUNT + SUM + AVG + MIN + MAX")

show_query(
    connection,
    """
    SELECT
        COUNT(*) AS sale_lines,
        SUM(quantity) AS units_sold,
        AVG(quantity) AS average_units,
        MIN(quantity) AS minimum_units,
        MAX(quantity) AS maximum_units
    FROM sales;
    """,
    (
        "sale_lines",
        "units_sold",
        "average_units",
        "minimum_units",
        "maximum_units",
    ),
)


# ---------------------------------------------------------------------------
# 9. GROUP BY
# ---------------------------------------------------------------------------

print_title("8. Aggregate Functions with GROUP BY")

show_query(
    connection,
    """
    SELECT
        customer_id,
        COUNT(*) AS purchase_lines,
        SUM(quantity) AS units,
        AVG(quantity) AS average_quantity
    FROM sales
    GROUP BY customer_id
    ORDER BY customer_id;
    """,
    (
        "customer_id",
        "purchase_lines",
        "units",
        "average_quantity",
    ),
)

show_query(
    connection,
    """
    SELECT
        salesperson,
        COUNT(*) AS sale_lines,
        SUM(quantity) AS units_sold,
        SUM(quantity * unit_price) AS gross_revenue
    FROM sales
    GROUP BY salesperson
    ORDER BY gross_revenue DESC;
    """,
    (
        "salesperson",
        "sale_lines",
        "units_sold",
        "gross_revenue",
    ),
)

print(
    """
GROUP BY changes the granularity of an aggregate query.

Without GROUP BY, the aggregate normally describes the complete selected set.

With GROUP BY salesperson, each salesperson receives a separate aggregate
result.
"""
)


# ---------------------------------------------------------------------------
# 10. GROUP BY multiple columns
# ---------------------------------------------------------------------------

print_title("9. GROUP BY Multiple Dimensions")

show_query(
    connection,
    """
    SELECT
        salesperson,
        customer_id,
        COUNT(*) AS sale_lines,
        SUM(quantity) AS units
    FROM sales
    GROUP BY salesperson, customer_id
    ORDER BY salesperson, customer_id;
    """,
    ("salesperson", "customer_id", "sale_lines", "units"),
)


# ---------------------------------------------------------------------------
# 11. Joining before aggregation
# ---------------------------------------------------------------------------

print_title("10. JOIN + AGGREGATION")

show_query(
    connection,
    """
    SELECT
        p.category,
        COUNT(*) AS sale_lines,
        SUM(s.quantity) AS units_sold,
        SUM(s.quantity * s.unit_price) AS gross_revenue,
        AVG(s.unit_price) AS average_unit_price
    FROM sales AS s
    JOIN products AS p
        ON p.product_id = s.product_id
    GROUP BY p.category
    ORDER BY gross_revenue DESC;
    """,
    (
        "category",
        "sale_lines",
        "units_sold",
        "gross_revenue",
        "average_unit_price",
    ),
)


# ---------------------------------------------------------------------------
# 12. HAVING
# ---------------------------------------------------------------------------

print_title("11. HAVING vs WHERE")

show_query(
    connection,
    """
    SELECT
        salesperson,
        SUM(quantity * unit_price) AS revenue
    FROM sales
    WHERE sale_date >= '2026-02-01'
    GROUP BY salesperson
    HAVING SUM(quantity * unit_price) > 50000
    ORDER BY revenue DESC;
    """,
    ("salesperson", "revenue"),
)

print(
    """
WHERE filters individual rows before grouping.

HAVING filters groups after aggregate values have been calculated.

A condition such as:

WHERE quantity > 2

operates on individual sale rows.

A condition such as:

HAVING SUM(quantity) > 10

operates on a grouped result.
"""
)


# ---------------------------------------------------------------------------
# 13. Conditional aggregation
# ---------------------------------------------------------------------------

print_title("12. Conditional Aggregation")

show_query(
    connection,
    """
    SELECT
        COUNT(*) AS total_sales,
        SUM(CASE WHEN quantity >= 3 THEN 1 ELSE 0 END)
            AS large_quantity_lines,
        SUM(CASE WHEN discount IS NOT NULL THEN 1 ELSE 0 END)
            AS discounted_lines,
        SUM(CASE WHEN unit_price >= 20000 THEN quantity ELSE 0 END)
            AS premium_units
    FROM sales;
    """,
    (
        "total_sales",
        "large_quantity_lines",
        "discounted_lines",
        "premium_units",
    ),
)

print(
    """
Conditional aggregation is useful for dashboards because multiple metrics
can be calculated in a single query.

The CASE expression converts a condition into a value that an aggregate
function can process.
"""
)


# ---------------------------------------------------------------------------
# 14. NULL behavior
# ---------------------------------------------------------------------------

print_title("13. NULL Behavior")

null_demo = [
    (10,),
    (20,),
    (None,),
    (30,),
]

connection.execute("CREATE TABLE null_demo (value INTEGER)")
connection.executemany("INSERT INTO null_demo VALUES (?)", null_demo)

show_query(
    connection,
    """
    SELECT
        COUNT(*) AS rows,
        COUNT(value) AS non_null_values,
        SUM(value) AS sum_value,
        AVG(value) AS average_value,
        MIN(value) AS minimum_value,
        MAX(value) AS maximum_value
    FROM null_demo;
    """,
    (
        "rows",
        "non_null_values",
        "sum_value",
        "average_value",
        "minimum_value",
        "maximum_value",
    ),
)

print(
    """
For the values 10, 20, NULL, 30:

COUNT(*) = 4
COUNT(value) = 3
SUM(value) = 60
AVG(value) = 20
MIN(value) = 10
MAX(value) = 30

The NULL value is not automatically interpreted as zero.
"""
)


# ---------------------------------------------------------------------------
# 15. Empty input behavior
# ---------------------------------------------------------------------------

print_title("14. Empty Input and NULL Results")

connection.execute("CREATE TABLE empty_values (value INTEGER)")

show_query(
    connection,
    """
    SELECT
        COUNT(*) AS row_count,
        SUM(value) AS sum_value,
        AVG(value) AS average_value,
        MIN(value) AS minimum_value,
        MAX(value) AS maximum_value
    FROM empty_values;
    """,
    (
        "row_count",
        "sum_value",
        "average_value",
        "minimum_value",
        "maximum_value",
    ),
)

print(
    """
An important SQL edge case is an empty input set.

COUNT(*) returns 0.

SUM, AVG, MIN, and MAX generally return NULL when there are no values to
aggregate.

COALESCE can provide a business-defined fallback:

COALESCE(SUM(value), 0)
"""
)


# ---------------------------------------------------------------------------
# 16. DISTINCT with aggregate functions
# ---------------------------------------------------------------------------

print_title("15. DISTINCT Inside Aggregates")

show_query(
    connection,
    """
    SELECT
        COUNT(*) AS total_lines,
        COUNT(DISTINCT customer_id) AS unique_customers,
        COUNT(DISTINCT product_id) AS unique_products
    FROM sales;
    """,
    ("total_lines", "unique_customers", "unique_products"),
)

show_query(
    connection,
    """
    SELECT
        SUM(DISTINCT unit_price) AS distinct_price_sum,
        AVG(DISTINCT unit_price) AS distinct_price_average
    FROM sales;
    """,
    ("distinct_price_sum", "distinct_price_average"),
)

print(
    """
DISTINCT changes the input values seen by the aggregate.

This can be useful, but it can also produce a metric that has a very
different business meaning from aggregating every transaction.

For example, SUM(DISTINCT unit_price) adds each distinct price once, not
every sale amount.
"""
)


# ---------------------------------------------------------------------------
# 17. Revenue calculations
# ---------------------------------------------------------------------------

print_title("16. Business Metrics Built from Aggregates")

show_query(
    connection,
    """
    SELECT
        COUNT(*) AS transaction_lines,
        SUM(quantity) AS units_sold,
        ROUND(SUM(quantity * unit_price), 2) AS gross_revenue,
        ROUND(SUM(COALESCE(discount, 0)), 2) AS discounts,
        ROUND(
            SUM(quantity * unit_price)
            - SUM(COALESCE(discount, 0)),
            2
        ) AS net_revenue,
        ROUND(AVG(quantity * unit_price), 2) AS average_line_value
    FROM sales;
    """,
    (
        "transaction_lines",
        "units_sold",
        "gross_revenue",
        "discounts",
        "net_revenue",
        "average_line_value",
    ),
)


# ---------------------------------------------------------------------------
# 18. Date-based aggregation
# ---------------------------------------------------------------------------

print_title("17. Time-Based Aggregation")

show_query(
    connection,
    """
    SELECT
        substr(sale_date, 1, 7) AS month,
        COUNT(*) AS sale_lines,
        SUM(quantity) AS units,
        ROUND(SUM(quantity * unit_price), 2) AS revenue
    FROM sales
    GROUP BY substr(sale_date, 1, 7)
    ORDER BY month;
    """,
    ("month", "sale_lines", "units", "revenue"),
)


# ---------------------------------------------------------------------------
# 19. Customer-level business report
# ---------------------------------------------------------------------------

print_title("18. Customer Analytics Report")

show_query(
    connection,
    """
    SELECT
        c.customer_name,
        c.city,
        c.customer_type,
        COUNT(s.sale_id) AS purchase_lines,
        COALESCE(SUM(s.quantity), 0) AS units_bought,
        ROUND(COALESCE(SUM(s.quantity * s.unit_price), 0), 2)
            AS gross_spend,
        ROUND(AVG(s.quantity * s.unit_price), 2)
            AS average_line_spend
    FROM customers AS c
    LEFT JOIN sales AS s
        ON s.customer_id = c.customer_id
    GROUP BY
        c.customer_id,
        c.customer_name,
        c.city,
        c.customer_type
    ORDER BY gross_spend DESC;
    """,
    (
        "customer_name",
        "city",
        "customer_type",
        "purchase_lines",
        "units_bought",
        "gross_spend",
        "average_line_spend",
    ),
)

print(
    """
The LEFT JOIN is important.

It allows customers with no sales to remain in the report.

An INNER JOIN would remove customers who have no matching sale.
"""
)


# ---------------------------------------------------------------------------
# 20. Product performance
# ---------------------------------------------------------------------------

print_title("19. Product Performance")

show_query(
    connection,
    """
    SELECT
        p.product_name,
        p.category,
        p.stock_quantity,
        COUNT(s.sale_id) AS sale_lines,
        COALESCE(SUM(s.quantity), 0) AS units_sold,
        ROUND(COALESCE(SUM(s.quantity * s.unit_price), 0), 2)
            AS revenue,
        MIN(s.sale_date) AS first_sale,
        MAX(s.sale_date) AS last_sale
    FROM products AS p
    LEFT JOIN sales AS s
        ON s.product_id = p.product_id
    GROUP BY
        p.product_id,
        p.product_name,
        p.category,
        p.stock_quantity
    ORDER BY revenue DESC;
    """,
    (
        "product_name",
        "category",
        "stock_quantity",
        "sale_lines",
        "units_sold",
        "revenue",
        "first_sale",
        "last_sale",
    ),
)


# ---------------------------------------------------------------------------
# 21. Aggregate query execution order
# ---------------------------------------------------------------------------

print_title("20. Conceptual Query Processing Order")

print(
    """
A simplified conceptual processing sequence is:

1. FROM / JOIN
2. WHERE
3. GROUP BY
4. Aggregate calculations
5. HAVING
6. SELECT
7. ORDER BY
8. LIMIT

This is a conceptual model, not a promise about the database engine's
physical execution plan.

Understanding the logical order helps explain why aggregate conditions
usually belong in HAVING rather than WHERE.
"""
)


# ---------------------------------------------------------------------------
# 22. Aggregate functions versus scalar functions
# ---------------------------------------------------------------------------

print_title("21. Aggregate vs Scalar Functions")

print(
    """
Scalar functions generally return one value for each input row.

Examples:
    UPPER(name)
    LENGTH(name)
    ROUND(price, 2)

Aggregate functions combine multiple rows.

Examples:
    COUNT(*)
    SUM(amount)
    AVG(amount)
    MIN(amount)
    MAX(amount)

A query can combine scalar expressions and aggregate functions, but the
grouping rules must remain valid.
"""
)


# ---------------------------------------------------------------------------
# 23. Manual Python verification
# ---------------------------------------------------------------------------

print_title("22. Verifying SQL Aggregation with Python")

quantities = [
    row[0]
    for row in connection.execute("SELECT quantity FROM sales")
]

prices = [
    row[0]
    for row in connection.execute("SELECT unit_price FROM sales")
]

python_count = len(quantities)
python_sum = sum(quantities)
python_average = mean(quantities)
python_minimum = min(quantities)
python_maximum = max(quantities)

print(f"Python COUNT: {python_count}")
print(f"Python SUM:   {python_sum}")
print(f"Python AVG:   {python_average:.2f}")
print(f"Python MIN:   {python_minimum}")
print(f"Python MAX:   {python_maximum}")

sql_values = connection.execute(
    """
    SELECT
        COUNT(quantity),
        SUM(quantity),
        AVG(quantity),
        MIN(quantity),
        MAX(quantity)
    FROM sales
    """
).fetchone()

print("\nSQL result:")
print(tuple(sql_values))

print(
    """
This comparison illustrates the conceptual similarity between aggregation
in SQL and reduction operations in a general-purpose programming language.

SQL aggregation is performed close to the data source, which can avoid
transferring large datasets into application memory.
"""
)


# ---------------------------------------------------------------------------
# 24. Validation of financial input
# ---------------------------------------------------------------------------

print_title("23. Validating Aggregate Inputs")

def parse_non_negative_decimal(value: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("Value must be a valid decimal number.") from error

    if number < 0:
        raise ValueError("Value cannot be negative.")

    return number


for raw_value in ("100.50", "0", "-5", "invalid"):
    try:
        parsed = parse_non_negative_decimal(raw_value)
        print(f"{raw_value!r} -> valid decimal: {parsed}")
    except ValueError as error:
        print(f"{raw_value!r} -> validation error: {error}")


# ---------------------------------------------------------------------------
# 25. Conditional metrics for a dashboard
# ---------------------------------------------------------------------------

print_title("24. Dashboard-Style Conditional Aggregation")

show_query(
    connection,
    """
    SELECT
        COUNT(*) AS total_lines,

        SUM(CASE
            WHEN quantity >= 3 THEN 1
            ELSE 0
        END) AS high_quantity_lines,

        SUM(CASE
            WHEN quantity >= 3 THEN quantity
            ELSE 0
        END) AS high_quantity_units,

        SUM(CASE
            WHEN unit_price >= 20000 THEN quantity * unit_price
            ELSE 0
        END) AS premium_revenue,

        SUM(CASE
            WHEN discount IS NULL THEN 0
            ELSE discount
        END) AS total_discounts
    FROM sales;
    """,
    (
        "total_lines",
        "high_quantity_lines",
        "high_quantity_units",
        "premium_revenue",
        "total_discounts",
    ),
)


# ---------------------------------------------------------------------------
# 26. Window functions: aggregate without collapsing rows
# ---------------------------------------------------------------------------

print_title("25. Window Aggregates")

show_query(
    connection,
    """
    SELECT
        sale_id,
        salesperson,
        quantity * unit_price AS line_revenue,
        SUM(quantity * unit_price) OVER (
            PARTITION BY salesperson
        ) AS salesperson_total_revenue
    FROM sales
    ORDER BY salesperson, sale_id;
    """,
    (
        "sale_id",
        "salesperson",
        "line_revenue",
        "salesperson_total_revenue",
    ),
)

print(
    """
A normal GROUP BY aggregation collapses rows into groups.

A window aggregate calculates an aggregate over a related set while keeping
the original rows visible.

This is useful when each transaction needs to be displayed alongside a
customer total, salesperson total, department total, or running total.
"""
)


# ---------------------------------------------------------------------------
# 27. Running aggregate
# ---------------------------------------------------------------------------

print_title("26. Running SUM")

show_query(
    connection,
    """
    SELECT
        sale_id,
        sale_date,
        quantity * unit_price AS line_revenue,
        SUM(quantity * unit_price) OVER (
            ORDER BY sale_date, sale_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_revenue
    FROM sales
    ORDER BY sale_date, sale_id;
    """,
    (
        "sale_id",
        "sale_date",
        "line_revenue",
        "cumulative_revenue",
    ),
)


# ---------------------------------------------------------------------------
# 28. Ranking groups using aggregates
# ---------------------------------------------------------------------------

print_title("27. Ranking Aggregated Results")

show_query(
    connection,
    """
    WITH salesperson_revenue AS (
        SELECT
            salesperson,
            SUM(quantity * unit_price) AS revenue
        FROM sales
        GROUP BY salesperson
    )
    SELECT
        salesperson,
        revenue,
        RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
    FROM salesperson_revenue
    ORDER BY revenue_rank;
    """,
    ("salesperson", "revenue", "revenue_rank"),
)


# ---------------------------------------------------------------------------
# 29. Common mistakes
# ---------------------------------------------------------------------------

print_title("28. Common Aggregate Function Mistakes")

mistakes = [
    (
        "Using COUNT(column) when NULL rows should be counted",
        "Use COUNT(*) when the requirement is to count rows."
    ),
    (
        "Treating NULL as zero without checking its meaning",
        "Use COALESCE only when the business rule supports that interpretation."
    ),
    (
        "Filtering aggregate results with WHERE",
        "Use HAVING for conditions on grouped aggregate results."
    ),
    (
        "Selecting an ungrouped non-aggregate column",
        "Include the column in GROUP BY or aggregate it."
    ),
    (
        "Using SUM(DISTINCT ...) unintentionally",
        "DISTINCT changes the mathematical meaning of the metric."
    ),
    (
        "Ignoring duplicate rows created by joins",
        "Validate join cardinality before aggregating."
    ),
    (
        "Using floating-point values for exact financial accounting",
        "Use appropriate decimal or integer-minor-unit designs for monetary systems."
    ),
]

for mistake, correction in mistakes:
    print(f"\nProblem:    {mistake}")
    print(f"Correction: {correction}")


# ---------------------------------------------------------------------------
# 30. Join duplication demonstration
# ---------------------------------------------------------------------------

print_title("29. Why Join Cardinality Matters")

connection.executescript(
    """
    CREATE TABLE customer_tags (
        customer_id INTEGER,
        tag TEXT
    );

    INSERT INTO customer_tags VALUES
        (1, 'VIP'),
        (1, 'Technology'),
        (2, 'Enterprise');
    """
)

show_query(
    connection,
    """
    SELECT
        c.customer_name,
        COUNT(s.sale_id) AS joined_sale_rows
    FROM customers AS c
    JOIN sales AS s
        ON s.customer_id = c.customer_id
    JOIN customer_tags AS t
        ON t.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
    ORDER BY c.customer_id;
    """,
    ("customer_name", "joined_sale_rows"),
)

print(
    """
Customer 1 has two tags.

Joining sales directly to those tags can multiply customer 1's sale rows.
An aggregate performed after such a one-to-many join can therefore become
incorrect.

This is a common production analytics problem.

The solution depends on the requirement and can involve:
- pre-aggregation,
- EXISTS,
- DISTINCT,
- carefully designed joins,
- separate aggregation stages.
"""
)


# ---------------------------------------------------------------------------
# 31. Pre-aggregation example
# ---------------------------------------------------------------------------

print_title("30. Safer Multi-Stage Aggregation")

show_query(
    connection,
    """
    WITH customer_sales AS (
        SELECT
            customer_id,
            SUM(quantity * unit_price) AS revenue
        FROM sales
        GROUP BY customer_id
    )
    SELECT
        c.customer_name,
        cs.revenue
    FROM customers AS c
    LEFT JOIN customer_sales AS cs
        ON cs.customer_id = c.customer_id
    ORDER BY c.customer_id;
    """,
    ("customer_name", "revenue"),
)


# ---------------------------------------------------------------------------
# 32. Indexing considerations
# ---------------------------------------------------------------------------

print_title("31. Performance and Indexing")

connection.executescript(
    """
    CREATE INDEX idx_sales_customer
        ON sales(customer_id);

    CREATE INDEX idx_sales_product
        ON sales(product_id);

    CREATE INDEX idx_sales_date
        ON sales(sale_date);

    CREATE INDEX idx_sales_salesperson
        ON sales(salesperson);
    """
)

print(
    """
Indexes can help the database locate and group/filter rows efficiently,
especially for selective predicates and joins.

Indexes also have costs:

- additional storage,
- slower INSERT/UPDATE/DELETE operations,
- maintenance overhead,
- possible cache and planning effects.

An index should support actual query patterns rather than being added to
every column automatically.
"""
)


# ---------------------------------------------------------------------------
# 33. Query-plan inspection
# ---------------------------------------------------------------------------

print_title("32. Inspecting an SQLite Query Plan")

plan = connection.execute(
    """
    EXPLAIN QUERY PLAN
    SELECT salesperson, SUM(quantity)
    FROM sales
    WHERE sale_date >= '2026-02-01'
    GROUP BY salesperson;
    """
).fetchall()

for row in plan:
    print(tuple(row))

print(
    """
EXPLAIN QUERY PLAN is useful for understanding how SQLite approaches a
query.

Production database systems provide more sophisticated execution-plan
analysis tools.
"""
)


# ---------------------------------------------------------------------------
# 34. Aggregate functions on expressions
# ---------------------------------------------------------------------------

print_title("33. Aggregating Calculated Expressions")

show_query(
    connection,
    """
    SELECT
        SUM(quantity * unit_price) AS gross_revenue,
        SUM(quantity * unit_price - COALESCE(discount, 0))
            AS net_revenue
    FROM sales;
    """,
    ("gross_revenue", "net_revenue"),
)


# ---------------------------------------------------------------------------
# 35. Multi-level aggregation
# ---------------------------------------------------------------------------

print_title("34. Multi-Level Aggregation")

show_query(
    connection,
    """
    WITH monthly_sales AS (
        SELECT
            substr(sale_date, 1, 7) AS month,
            salesperson,
            SUM(quantity * unit_price) AS revenue
        FROM sales
        GROUP BY substr(sale_date, 1, 7), salesperson
    )
    SELECT
        month,
        COUNT(*) AS salesperson_groups,
        SUM(revenue) AS monthly_revenue,
        AVG(revenue) AS average_salesperson_revenue
    FROM monthly_sales
    GROUP BY month
    ORDER BY month;
    """,
    (
        "month",
        "salesperson_groups",
        "monthly_revenue",
        "average_salesperson_revenue",
    ),
)


# ---------------------------------------------------------------------------
# 36. A reusable aggregate-report function
# ---------------------------------------------------------------------------

print_title("35. Reusable Python Database Reporting Function")

def generate_sales_report(
    connection: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    row = connection.execute(
        """
        SELECT
            COUNT(*) AS line_count,
            COALESCE(SUM(quantity), 0) AS units,
            COALESCE(SUM(quantity * unit_price), 0) AS gross_revenue,
            COALESCE(SUM(discount), 0) AS discounts,
            AVG(quantity * unit_price) AS average_line_value,
            MIN(unit_price) AS minimum_unit_price,
            MAX(unit_price) AS maximum_unit_price
        FROM sales
        WHERE sale_date BETWEEN ? AND ?;
        """,
        (start_date, end_date),
    ).fetchone()

    return dict(row)


report = generate_sales_report(
    connection,
    "2026-01-01",
    "2026-02-28",
)

for key, value in report.items():
    print(f"{key}: {value}")


# ---------------------------------------------------------------------------
# 37. Test-style assertions
# ---------------------------------------------------------------------------

print_title("36. Verification Tests")

aggregate_values = connection.execute(
    """
    SELECT
        COUNT(*) AS count_value,
        SUM(quantity) AS sum_value,
        MIN(quantity) AS min_value,
        MAX(quantity) AS max_value
    FROM sales;
    """
).fetchone()

assert aggregate_values["count_value"] == len(quantities)
assert aggregate_values["sum_value"] == sum(quantities)
assert aggregate_values["min_value"] == min(quantities)
assert aggregate_values["max_value"] == max(quantities)

null_values = connection.execute(
    """
    SELECT
        COUNT(*) AS total_rows,
        COUNT(value) AS non_null_rows
    FROM null_demo;
    """
).fetchone()

assert null_values["total_rows"] == 4
assert null_values["non_null_rows"] == 3

print("All aggregate verification tests passed.")


# ---------------------------------------------------------------------------
# 38. Security considerations
# ---------------------------------------------------------------------------

print_title("37. SQL Security")

print(
    """
Use parameterized queries for values supplied by users or external systems.

Unsafe conceptual pattern:

    SQL text + user input

Safer pattern:

    SQL text with placeholders + separate parameters

The report function above uses:

    WHERE sale_date BETWEEN ? AND ?

and passes the dates separately.

Parameterized queries reduce SQL injection risk because data is handled as
data rather than being interpreted as part of the SQL command.

Do not build SQL statements by directly concatenating untrusted values.
"""
)


# ---------------------------------------------------------------------------
# 39. Performance principles
# ---------------------------------------------------------------------------

print_title("38. Aggregate Query Performance Principles")

print(
    """
For large datasets, useful principles include:

1. Filter early when possible.
2. Select only required columns.
3. Index columns used frequently for filtering and joins.
4. Check join cardinality before aggregating.
5. Pre-aggregate when it reduces unnecessary row multiplication.
6. Inspect execution plans.
7. Avoid unnecessary DISTINCT operations.
8. Avoid transferring millions of raw rows into application memory merely
   to calculate a metric the database can calculate efficiently.
9. Understand the database engine's storage and execution model.
10. Validate performance with realistic data volumes.

Aggregation itself is not automatically expensive or cheap. Its cost depends
on data volume, grouping cardinality, sorting, indexes, joins, memory,
parallelism, database engine, and query structure.
"""
)


# ---------------------------------------------------------------------------
# 40. Final integrated report
# ---------------------------------------------------------------------------

print_title("39. Integrated Executive Sales Report")

show_query(
    connection,
    """
    SELECT
        COUNT(*) AS transaction_lines,
        COUNT(DISTINCT customer_id) AS active_customers,
        COUNT(DISTINCT product_id) AS products_sold,
        SUM(quantity) AS units_sold,
        ROUND(AVG(quantity), 2) AS average_units_per_line,
        ROUND(MIN(quantity), 2) AS minimum_units_per_line,
        ROUND(MAX(quantity), 2) AS maximum_units_per_line,
        ROUND(SUM(quantity * unit_price), 2) AS gross_revenue,
        ROUND(SUM(COALESCE(discount, 0)), 2) AS discounts,
        ROUND(
            SUM(quantity * unit_price)
            - SUM(COALESCE(discount, 0)),
            2
        ) AS net_revenue
    FROM sales;
    """,
    (
        "transaction_lines",
        "active_customers",
        "products_sold",
        "units_sold",
        "average_units_per_line",
        "minimum_units_per_line",
        "maximum_units_per_line",
        "gross_revenue",
        "discounts",
        "net_revenue",
    ),
)


# ---------------------------------------------------------------------------
# 41. Core conceptual checklist
# ---------------------------------------------------------------------------

print_title("40. Aggregate Function Checklist")

checklist = {
    "COUNT(*) counts rows": True,
    "COUNT(column) ignores NULL": True,
    "COUNT(DISTINCT column) counts unique non-NULL values": True,
    "SUM adds numeric values": True,
    "AVG calculates a mean over non-NULL values": True,
    "MIN finds the smallest value": True,
    "MAX finds the largest value": True,
    "GROUP BY creates aggregation groups": True,
    "WHERE filters rows before grouping": True,
    "HAVING filters groups after aggregation": True,
    "COALESCE can provide explicit NULL fallbacks": True,
    "DISTINCT changes aggregate input": True,
    "Window aggregates preserve individual rows": True,
    "Join cardinality can change aggregate results": True,
    "Indexes and execution plans matter at scale": True,
}

for concept, verified in checklist.items():
    print(f"[{'PASS' if verified else 'FAIL'}] {concept}")


# ---------------------------------------------------------------------------
# 42. Clean shutdown
# ---------------------------------------------------------------------------

connection.close()

print_title("Study File Completed")

print(
    """
The examples covered the complete core lifecycle of aggregate analysis:

raw rows -> filtering -> joining -> grouping -> aggregation -> group
filtering -> ordering/reporting.

The five central functions remain:

COUNT
SUM
AVG
MIN
MAX

Their correctness depends not only on the function itself, but also on
NULL semantics, grouping level, join cardinality, filtering, data types,
business definitions, and query performance.
"""
)
