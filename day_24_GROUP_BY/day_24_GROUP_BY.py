"""
GROUP BY: Grouping Rows, Grouped Calculations, and Grouping Multiple Columns

A self-contained study program for learning SQL-style GROUP BY concepts
from beginner to advanced level.

The examples use only the Python standard library. Python dictionaries,
collections, sorting, and custom functions are used to model the behavior
of SQL GROUP BY without requiring a database package.

The script covers:
- What grouping means
- GROUP BY and aggregation
- COUNT, SUM, AVG, MIN, and MAX
- Grouping by one column
- Grouping by multiple columns
- NULL-like values
- WHERE versus HAVING
- Filtering before and after grouping
- Conditional aggregation
- Distinct counts
- Empty groups and missing categories
- Numeric precision considerations
- Ordering grouped results
- Top-N groups
- Nested grouping
- Rollup-style totals
- Validation
- Common mistakes
- Performance considerations
- A reusable grouping engine
- SQL generation
- A realistic sales-analysis case study

The program prints educational demonstrations when executed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Iterable, Optional


# ---------------------------------------------------------------------------
# Section 1: Fundamental data
# ---------------------------------------------------------------------------

SALES = [
    {
        "order_id": 1001,
        "customer": "Asha",
        "region": "North",
        "city": "Delhi",
        "category": "Electronics",
        "product": "Laptop",
        "salesperson": "Ravi",
        "quantity": 2,
        "unit_price": 75000.00,
        "discount": 0.05,
        "status": "Completed",
    },
    {
        "order_id": 1002,
        "customer": "Bharat",
        "region": "North",
        "city": "Lucknow",
        "category": "Furniture",
        "product": "Chair",
        "salesperson": "Neha",
        "quantity": 5,
        "unit_price": 4500.00,
        "discount": 0.10,
        "status": "Completed",
    },
    {
        "order_id": 1003,
        "customer": "Charu",
        "region": "South",
        "city": "Bengaluru",
        "category": "Electronics",
        "product": "Phone",
        "salesperson": "Ravi",
        "quantity": 3,
        "unit_price": 30000.00,
        "discount": 0.00,
        "status": "Completed",
    },
    {
        "order_id": 1004,
        "customer": "Dev",
        "region": "West",
        "city": "Mumbai",
        "category": "Office",
        "product": "Desk",
        "salesperson": "Meera",
        "quantity": 4,
        "unit_price": 12000.00,
        "discount": 0.15,
        "status": "Cancelled",
    },
    {
        "order_id": 1005,
        "customer": "Esha",
        "region": "North",
        "city": "Delhi",
        "category": "Electronics",
        "product": "Monitor",
        "salesperson": "Ravi",
        "quantity": 4,
        "unit_price": 18000.00,
        "discount": 0.08,
        "status": "Completed",
    },
    {
        "order_id": 1006,
        "customer": "Farhan",
        "region": "East",
        "city": "Kolkata",
        "category": "Furniture",
        "product": "Table",
        "salesperson": "Neha",
        "quantity": 2,
        "unit_price": 16000.00,
        "discount": 0.05,
        "status": "Completed",
    },
    {
        "order_id": 1007,
        "customer": "Gita",
        "region": "South",
        "city": "Chennai",
        "category": "Office",
        "product": "Printer",
        "salesperson": "Meera",
        "quantity": 2,
        "unit_price": 22000.00,
        "discount": 0.12,
        "status": "Completed",
    },
    {
        "order_id": 1008,
        "customer": "Hari",
        "region": "West",
        "city": "Pune",
        "category": "Electronics",
        "product": "Tablet",
        "salesperson": "Ravi",
        "quantity": 6,
        "unit_price": 25000.00,
        "discount": 0.07,
        "status": "Completed",
    },
    {
        "order_id": 1009,
        "customer": "Isha",
        "region": "North",
        "city": "Lucknow",
        "category": "Office",
        "product": "Printer",
        "salesperson": "Neha",
        "quantity": 1,
        "unit_price": 22000.00,
        "discount": 0.00,
        "status": "Completed",
    },
    {
        "order_id": 1010,
        "customer": "Jai",
        "region": "South",
        "city": "Hyderabad",
        "category": "Furniture",
        "product": "Chair",
        "salesperson": "Meera",
        "quantity": 10,
        "unit_price": 4500.00,
        "discount": 0.20,
        "status": "Completed",
    },
    {
        "order_id": 1011,
        "customer": "Kiran",
        "region": None,
        "city": "Jaipur",
        "category": "Electronics",
        "product": "Keyboard",
        "salesperson": "Ravi",
        "quantity": 8,
        "unit_price": 2500.00,
        "discount": 0.03,
        "status": "Completed",
    },
    {
        "order_id": 1012,
        "customer": "Lata",
        "region": "East",
        "city": "Patna",
        "category": None,
        "product": "Desk",
        "salesperson": "Neha",
        "quantity": 3,
        "unit_price": 12000.00,
        "discount": 0.10,
        "status": "Completed",
    },
]


# ---------------------------------------------------------------------------
# Section 2: Utility functions
# ---------------------------------------------------------------------------

def money(value: float | Decimal) -> str:
    """Format a numeric amount as Indian-style currency text."""
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"₹{amount:,.2f}"


def print_title(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def print_rows(rows: Iterable[dict[str, Any]], columns: Optional[list[str]] = None) -> None:
    rows = list(rows)
    if not rows:
        print("(no rows)")
        return

    if columns is None:
        columns = list(rows[0].keys())

    widths = {}
    for column in columns:
        widths[column] = max(
            len(str(column)),
            *(len(str(row.get(column, ""))) for row in rows),
        )

    header = " | ".join(str(column).ljust(widths[column]) for column in columns)
    print(header)
    print("-+-".join("-" * widths[column] for column in columns))

    for row in rows:
        print(" | ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))


def calculate_net_sales(row: dict[str, Any]) -> float:
    """
    Equivalent to a row-level SQL expression such as:

    quantity * unit_price * (1 - discount)
    """
    return row["quantity"] * row["unit_price"] * (1 - row["discount"])


def normalize_group_value(value: Any) -> Any:
    """
    SQL groups NULL values together.

    Python dictionaries can also use None as a grouping key. This function
    makes the intention explicit and converts None to a readable label.
    """
    return "NULL" if value is None else value


# ---------------------------------------------------------------------------
# Section 3: Basic GROUP BY simulation
# ---------------------------------------------------------------------------

def group_rows(
    rows: Iterable[dict[str, Any]],
    key_function: Callable[[dict[str, Any]], Any],
) -> dict[Any, list[dict[str, Any]]]:
    """
    Generic GROUP BY implementation.

    Conceptually:

        SELECT grouping_key, ...
        FROM rows
        GROUP BY grouping_key;

    Every row is assigned to exactly one group according to key_function.
    """
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        key = key_function(row)
        groups[key].append(row)

    return dict(groups)


def group_by_column(
    rows: Iterable[dict[str, Any]],
    column: str,
) -> dict[Any, list[dict[str, Any]]]:
    """Group rows by one column."""
    return group_rows(rows, lambda row: normalize_group_value(row.get(column)))


def group_by_columns(
    rows: Iterable[dict[str, Any]],
    columns: list[str],
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    """
    Group rows by multiple columns.

    SQL equivalent:

        GROUP BY region, category

    The combination of values forms the group identity.
    """
    return group_rows(
        rows,
        lambda row: tuple(normalize_group_value(row.get(column)) for column in columns),
    )


# ---------------------------------------------------------------------------
# Section 4: Aggregate functions
# ---------------------------------------------------------------------------

def sql_count_star(rows: Iterable[dict[str, Any]]) -> int:
    """COUNT(*) counts every row in the group."""
    return sum(1 for _ in rows)


def sql_count_column(
    rows: Iterable[dict[str, Any]],
    column: str,
) -> int:
    """
    COUNT(column) counts non-NULL values.

    This differs from COUNT(*).
    """
    return sum(1 for row in rows if row.get(column) is not None)


def sql_sum(
    rows: Iterable[dict[str, Any]],
    column: str,
) -> Optional[float]:
    """
    Approximate SQL SUM semantics:
    NULL values are ignored and an entirely NULL/empty input has no numeric sum.
    """
    values = [row.get(column) for row in rows if row.get(column) is not None]

    if not values:
        return None

    return sum(values)


def sql_avg(
    rows: Iterable[dict[str, Any]],
    column: str,
) -> Optional[float]:
    """Average of non-NULL values."""
    values = [row.get(column) for row in rows if row.get(column) is not None]

    if not values:
        return None

    return sum(values) / len(values)


def sql_min(
    rows: Iterable[dict[str, Any]],
    column: str,
) -> Any:
    """Minimum non-NULL value."""
    values = [row.get(column) for row in rows if row.get(column) is not None]
    return min(values) if values else None


def sql_max(
    rows: Iterable[dict[str, Any]],
    column: str,
) -> Any:
    """Maximum non-NULL value."""
    values = [row.get(column) for row in rows if row.get(column) is not None]
    return max(values) if values else None


# ---------------------------------------------------------------------------
# Section 5: Grouped calculations
# ---------------------------------------------------------------------------

def aggregate_by_group(
    groups: dict[Any, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Create several aggregate columns for each group."""
    results = []

    for group_key, rows in groups.items():
        results.append(
            {
                "region": group_key,
                "orders": sql_count_star(rows),
                "customers_with_value": sql_count_column(rows, "customer"),
                "total_quantity": sql_sum(rows, "quantity"),
                "average_quantity": sql_avg(rows, "quantity"),
                "minimum_quantity": sql_min(rows, "quantity"),
                "maximum_quantity": sql_max(rows, "quantity"),
            }
        )

    return results


# ---------------------------------------------------------------------------
# Section 6: WHERE versus GROUP BY versus HAVING
# ---------------------------------------------------------------------------

def where(
    rows: Iterable[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    """
    Simulates WHERE.

    WHERE operates on individual rows before grouping.
    """
    return [row for row in rows if predicate(row)]


def having(
    grouped_rows: Iterable[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    """
    Simulates HAVING.

    HAVING operates on already grouped/aggregated results.
    """
    return [row for row in grouped_rows if predicate(row)]


# ---------------------------------------------------------------------------
# Section 7: Demonstration of the logical processing order
# ---------------------------------------------------------------------------

def demonstrate_query_order() -> None:
    print_title("Logical processing: WHERE -> GROUP BY -> aggregates -> HAVING -> ORDER BY")

    completed = where(SALES, lambda row: row["status"] == "Completed")

    grouped = group_by_column(completed, "region")

    aggregates = aggregate_by_group(grouped)

    qualified = having(
        aggregates,
        lambda row: row["total_quantity"] is not None and row["total_quantity"] >= 5,
    )

    ordered = sorted(
        qualified,
        key=lambda row: row["total_quantity"],
        reverse=True,
    )

    print_rows(
        ordered,
        [
            "region",
            "orders",
            "total_quantity",
            "average_quantity",
        ],
    )

    print("\nInterpretation:")
    print("1. WHERE removes cancelled rows.")
    print("2. GROUP BY creates one group per region.")
    print("3. Aggregate functions calculate values inside each group.")
    print("4. HAVING removes groups whose total quantity is below 5.")
    print("5. ORDER BY sorts the remaining grouped results.")


# ---------------------------------------------------------------------------
# Section 8: One-column GROUP BY
# ---------------------------------------------------------------------------

def demonstrate_single_column_grouping() -> None:
    print_title("GROUP BY one column")

    groups = group_by_column(SALES, "region")
    results = aggregate_by_group(groups)

    results.sort(key=lambda row: str(row["region"]))

    print_rows(
        results,
        [
            "region",
            "orders",
            "customers_with_value",
            "total_quantity",
            "average_quantity",
            "minimum_quantity",
            "maximum_quantity",
        ],
    )

    print("\nSQL concept:")
    print("SELECT region, COUNT(*), SUM(quantity), AVG(quantity)")
    print("FROM sales")
    print("GROUP BY region;")


# ---------------------------------------------------------------------------
# Section 9: Multiple-column GROUP BY
# ---------------------------------------------------------------------------

def demonstrate_multiple_column_grouping() -> None:
    print_title("GROUP BY multiple columns")

    groups = group_by_columns(SALES, ["region", "category"])

    results = []

    for (region, category), rows in groups.items():
        results.append(
            {
                "region": region,
                "category": category,
                "orders": sql_count_star(rows),
                "total_quantity": sql_sum(rows, "quantity"),
                "total_sales": sum(calculate_net_sales(row) for row in rows),
                "average_order_value": (
                    sum(calculate_net_sales(row) for row in rows) / len(rows)
                ),
            }
        )

    results.sort(key=lambda row: (str(row["region"]), str(row["category"])))

    print_rows(
        results,
        [
            "region",
            "category",
            "orders",
            "total_quantity",
            "total_sales",
            "average_order_value",
        ],
    )

    print("\nSQL concept:")
    print("SELECT region, category, COUNT(*), SUM(quantity)")
    print("FROM sales")
    print("GROUP BY region, category;")

    print("\nImportant distinction:")
    print("GROUP BY region creates groups only by region.")
    print("GROUP BY region, category creates groups by each region-category pair.")


# ---------------------------------------------------------------------------
# Section 10: COUNT(*) versus COUNT(column)
# ---------------------------------------------------------------------------

def demonstrate_count_behavior() -> None:
    print_title("COUNT(*) versus COUNT(column)")

    groups = group_by_column(SALES, "region")

    results = []

    for region, rows in groups.items():
        results.append(
            {
                "region": region,
                "count_star": sql_count_star(rows),
                "count_category": sql_count_column(rows, "category"),
                "count_city": sql_count_column(rows, "city"),
            }
        )

    results.sort(key=lambda row: str(row["region"]))

    print_rows(results)

    print("\nCOUNT(*) counts rows.")
    print("COUNT(category) ignores rows where category is NULL.")
    print("Therefore the two values can differ.")


# ---------------------------------------------------------------------------
# Section 11: Conditional aggregation
# ---------------------------------------------------------------------------

def demonstrate_conditional_aggregation() -> None:
    print_title("Conditional aggregation")

    groups = group_by_column(SALES, "region")
    results = []

    for region, rows in groups.items():
        completed = [
            row for row in rows
            if row["status"] == "Completed"
        ]

        cancelled = [
            row for row in rows
            if row["status"] == "Cancelled"
        ]

        completed_sales = sum(calculate_net_sales(row) for row in completed)

        results.append(
            {
                "region": region,
                "completed_orders": len(completed),
                "cancelled_orders": len(cancelled),
                "completed_sales": money(completed_sales),
            }
        )

    results.sort(key=lambda row: str(row["region"]))
    print_rows(results)

    print("\nSQL concept:")
    print(
        "SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) "
        "counts rows conditionally."
    )
    print(
        "SUM(CASE WHEN status = 'Completed' THEN net_sales ELSE 0 END) "
        "calculates conditional sales."
    )


# ---------------------------------------------------------------------------
# Section 12: Distinct values inside groups
# ---------------------------------------------------------------------------

def demonstrate_distinct_counts() -> None:
    print_title("COUNT(DISTINCT ...) inside groups")

    groups = group_by_column(SALES, "region")
    results = []

    for region, rows in groups.items():
        distinct_customers = {
            row["customer"]
            for row in rows
            if row["customer"] is not None
        }

        distinct_products = {
            row["product"]
            for row in rows
            if row["product"] is not None
        }

        results.append(
            {
                "region": region,
                "unique_customers": len(distinct_customers),
                "unique_products": len(distinct_products),
            }
        )

    results.sort(key=lambda row: str(row["region"]))
    print_rows(results)

    print("\nSQL concept:")
    print("COUNT(DISTINCT customer) counts unique customer values within each group.")


# ---------------------------------------------------------------------------
# Section 13: Weighted average versus ordinary average
# ---------------------------------------------------------------------------

def demonstrate_average_pitfall() -> None:
    print_title("Average: ordinary versus weighted")

    groups = group_by_column(SALES, "region")
    results = []

    for region, rows in groups.items():
        ordinary_average = sql_avg(rows, "unit_price")

        total_quantity = sum(row["quantity"] for row in rows)
        weighted_average = (
            sum(row["quantity"] * row["unit_price"] for row in rows)
            / total_quantity
            if total_quantity
            else None
        )

        results.append(
            {
                "region": region,
                "ordinary_unit_price": (
                    money(ordinary_average) if ordinary_average is not None else None
                ),
                "quantity_weighted_unit_price": (
                    money(weighted_average) if weighted_average is not None else None
                ),
            }
        )

    results.sort(key=lambda row: str(row["region"]))
    print_rows(results)

    print(
        "\nAVG(unit_price) gives every row equal weight. "
        "A weighted average can better represent the price per unit "
        "when rows contain different quantities."
    )


# ---------------------------------------------------------------------------
# Section 14: HAVING examples
# ---------------------------------------------------------------------------

def demonstrate_having() -> None:
    print_title("HAVING: filtering groups")

    groups = group_by_column(SALES, "region")
    results = aggregate_by_group(groups)

    print("All groups:")
    print_rows(results, ["region", "orders", "total_quantity"])

    qualified = having(
        results,
        lambda row: row["orders"] >= 2,
    )

    print("\nGroups with at least two rows:")
    print_rows(qualified, ["region", "orders", "total_quantity"])

    print("\nSQL concept:")
    print("SELECT region, COUNT(*)")
    print("FROM sales")
    print("GROUP BY region")
    print("HAVING COUNT(*) >= 2;")

    print("\nWHERE and HAVING are not interchangeable:")
    print("WHERE filters individual source rows.")
    print("HAVING filters groups after aggregation.")


# ---------------------------------------------------------------------------
# Section 15: Top-N groups
# ---------------------------------------------------------------------------

def demonstrate_top_groups() -> None:
    print_title("Ordering grouped results and selecting top groups")

    groups = group_by_column(
        where(SALES, lambda row: row["status"] == "Completed"),
        "category",
    )

    results = []

    for category, rows in groups.items():
        total_sales = sum(calculate_net_sales(row) for row in rows)

        results.append(
            {
                "category": category,
                "orders": len(rows),
                "sales": total_sales,
            }
        )

    results.sort(key=lambda row: row["sales"], reverse=True)

    print_rows(
        [
            {
                "category": row["category"],
                "orders": row["orders"],
                "sales": money(row["sales"]),
            }
            for row in results
        ]
    )

    print("\nThe first two rows after descending ordering form a Top-2 grouped result.")


# ---------------------------------------------------------------------------
# Section 16: Grouping sets and rollup-style calculations
# ---------------------------------------------------------------------------

def demonstrate_rollup() -> None:
    print_title("ROLLUP-style hierarchical totals")

    completed = where(SALES, lambda row: row["status"] == "Completed")

    region_category_groups = group_by_columns(
        completed,
        ["region", "category"],
    )

    output = []

    for (region, category), rows in region_category_groups.items():
        output.append(
            {
                "level": "region + category",
                "region": region,
                "category": category,
                "orders": len(rows),
                "sales": sum(calculate_net_sales(row) for row in rows),
            }
        )

    region_groups = group_by_column(completed, "region")

    for region, rows in region_groups.items():
        output.append(
            {
                "level": "region total",
                "region": region,
                "category": None,
                "orders": len(rows),
                "sales": sum(calculate_net_sales(row) for row in rows),
            }
        )

    output.append(
        {
            "level": "grand total",
            "region": None,
            "category": None,
            "orders": len(completed),
            "sales": sum(calculate_net_sales(row) for row in completed),
        }
    )

    output.sort(
        key=lambda row: (
            str(row["region"]),
            str(row["category"]),
            row["level"],
        )
    )

    display = [
        {
            "level": row["level"],
            "region": row["region"],
            "category": row["category"],
            "orders": row["orders"],
            "sales": money(row["sales"]),
        }
        for row in output
    ]

    print_rows(display)

    print(
        "\nThis manually demonstrates the idea behind hierarchical grouping "
        "such as SQL ROLLUP."
    )


# ---------------------------------------------------------------------------
# Section 17: A reusable aggregation engine
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AggregateDefinition:
    name: str
    function: Callable[[list[dict[str, Any]]], Any]


def aggregate_query(
    rows: Iterable[dict[str, Any]],
    group_columns: list[str],
    aggregates: list[AggregateDefinition],
    row_filter: Optional[Callable[[dict[str, Any]], bool]] = None,
    group_filter: Optional[Callable[[dict[str, Any]], bool]] = None,
) -> list[dict[str, Any]]:
    """
    Reusable GROUP BY engine.

    The stages intentionally resemble relational query processing:

        source rows
            -> WHERE
            -> GROUP BY
            -> aggregate calculations
            -> HAVING
    """
    source = list(rows)

    if row_filter is not None:
        source = [row for row in source if row_filter(row)]

    groups = group_by_columns(source, group_columns)

    results = []

    for key, grouped_rows in groups.items():
        result = {
            column: value
            for column, value in zip(group_columns, key)
        }

        for aggregate in aggregates:
            result[aggregate.name] = aggregate.function(grouped_rows)

        results.append(result)

    if group_filter is not None:
        results = [row for row in results if group_filter(row)]

    return results


def demonstrate_reusable_engine() -> None:
    print_title("Reusable aggregation engine")

    query = aggregate_query(
        SALES,
        group_columns=["region", "salesperson"],
        aggregates=[
            AggregateDefinition(
                "orders",
                lambda rows: len(rows),
            ),
            AggregateDefinition(
                "quantity",
                lambda rows: sum(row["quantity"] for row in rows),
            ),
            AggregateDefinition(
                "sales",
                lambda rows: sum(calculate_net_sales(row) for row in rows),
            ),
        ],
        row_filter=lambda row: row["status"] == "Completed",
        group_filter=lambda result: result["sales"] >= 10000,
    )

    query.sort(key=lambda row: row["sales"], reverse=True)

    display = [
        {
            **row,
            "sales": money(row["sales"]),
        }
        for row in query
    ]

    print_rows(display)


# ---------------------------------------------------------------------------
# Section 18: Edge cases
# ---------------------------------------------------------------------------

def demonstrate_edge_cases() -> None:
    print_title("GROUP BY edge cases")

    edge_rows = [
        {"department": "IT", "salary": 100},
        {"department": "IT", "salary": 200},
        {"department": None, "salary": 300},
        {"department": None, "salary": 400},
        {"department": "HR", "salary": None},
    ]

    groups = group_by_column(edge_rows, "department")

    results = []

    for department, rows in groups.items():
        results.append(
            {
                "department": department,
                "count_star": sql_count_star(rows),
                "count_salary": sql_count_column(rows, "salary"),
                "sum_salary": sql_sum(rows, "salary"),
                "avg_salary": sql_avg(rows, "salary"),
            }
        )

    results.sort(key=lambda row: str(row["department"]))
    print_rows(results)

    print("\nImportant behaviors:")
    print("- Multiple NULL values belong to the same GROUP BY group.")
    print("- COUNT(*) counts rows even when the grouped value is NULL.")
    print("- COUNT(column) ignores NULL values in that column.")
    print("- SUM and AVG ignore NULL input values.")
    print("- An aggregate over no qualifying numeric values may produce NULL.")


# ---------------------------------------------------------------------------
# Section 19: Validation and common mistakes
# ---------------------------------------------------------------------------

def validate_group_columns(
    rows: list[dict[str, Any]],
    columns: list[str],
) -> None:
    """Fail early when a requested grouping column does not exist."""
    if not columns:
        raise ValueError("At least one GROUP BY column is required.")

    if not rows:
        return

    missing = [
        column
        for column in columns
        if column not in rows[0]
    ]

    if missing:
        raise KeyError(f"Unknown grouping columns: {missing}")


def demonstrate_validation() -> None:
    print_title("Validation and common mistakes")

    try:
        validate_group_columns(SALES, [])
    except ValueError as error:
        print("Caught invalid empty grouping list:", error)

    try:
        validate_group_columns(SALES, ["does_not_exist"])
    except KeyError as error:
        print("Caught unknown grouping column:", error)

    print("\nCommon SQL mistakes:")
    print("1. Selecting a non-aggregated column that is neither grouped nor otherwise valid.")
    print("2. Using WHERE when the intended condition depends on an aggregate.")
    print("3. Using HAVING for a row-level filter that belongs in WHERE.")
    print("4. Forgetting that COUNT(column) ignores NULL.")
    print("5. Assuming AVG is a weighted average.")
    print("6. Grouping by a display label that merges distinct underlying values.")
    print("7. Accidentally multiplying rows through joins before GROUP BY.")
    print("8. Relying on unordered grouped output without ORDER BY.")
    print("9. Using floating-point arithmetic when exact financial arithmetic matters.")
    print("10. Ignoring the effect of filtering before aggregation.")


# ---------------------------------------------------------------------------
# Section 20: Join multiplication warning
# ---------------------------------------------------------------------------

def demonstrate_join_multiplication() -> None:
    print_title("Why joins can change grouped totals")

    orders = [
        {"order_id": 1, "customer_id": 10, "amount": 100},
        {"order_id": 2, "customer_id": 20, "amount": 200},
    ]

    customer_tags = [
        {"customer_id": 10, "tag": "VIP"},
        {"customer_id": 10, "tag": "Wholesale"},
        {"customer_id": 20, "tag": "Retail"},
    ]

    joined = []

    for order in orders:
        for tag in customer_tags:
            if order["customer_id"] == tag["customer_id"]:
                joined.append(
                    {
                        **order,
                        "tag": tag["tag"],
                    }
                )

    print("Original order rows:", len(orders))
    print("Joined rows:", len(joined))

    original_total = sum(order["amount"] for order in orders)
    joined_total = sum(row["amount"] for row in joined)

    print("Original total:", money(original_total))
    print("Naively summed joined total:", money(joined_total))

    print(
        "\nThe first order appears twice after the one-to-many join, "
        "so summing its amount after the join double-counts it."
    )
    print(
        "Production queries must understand join cardinality before "
        "performing grouped financial calculations."
    )


# ---------------------------------------------------------------------------
# Section 21: Performance considerations
# ---------------------------------------------------------------------------

def explain_performance() -> None:
    print_title("Performance considerations")

    print("Hash-style grouping:")
    print("- Usually approximately O(n) expected time for n rows.")
    print("- Requires memory for group keys and group state.")
    print("- Particularly useful when many rows must be grouped.")

    print("\nSort-style grouping:")
    print("- Sort rows by grouping keys, then scan contiguous groups.")
    print("- Typically O(n log n) because of sorting.")
    print("- Can be useful when ordered grouped output is also required.")

    print("\nDatabase considerations:")
    print("- Indexes can help filtering and sometimes grouping.")
    print("- The optimizer may choose hash aggregation or sort-based aggregation.")
    print("- Large GROUP BY operations can require substantial memory.")
    print("- Pre-filtering rows with WHERE can reduce the amount of data grouped.")
    print("- Distributed databases may perform local partial aggregation before merging results.")
    print("- EXPLAIN or EXPLAIN ANALYZE is used to inspect an actual database plan.")

    print("\nThe Python implementation uses dictionaries and therefore resembles hash aggregation.")


# ---------------------------------------------------------------------------
# Section 22: SQL generation
# ---------------------------------------------------------------------------

def build_group_by_sql(
    table: str,
    group_columns: list[str],
    aggregate_expressions: list[str],
    where_clause: Optional[str] = None,
    having_clause: Optional[str] = None,
    order_by_clause: Optional[str] = None,
) -> str:
    """
    Generate a simple illustrative SQL statement.

    This function deliberately does not execute SQL and should not be used
    as a general SQL injection-safe query builder. Production applications
    should parameterize values and validate identifiers.
    """
    if not table:
        raise ValueError("Table name cannot be empty.")

    if not group_columns:
        raise ValueError("At least one grouping column is required.")

    select_items = group_columns + aggregate_expressions

    query = "SELECT " + ", ".join(select_items)
    query += f" FROM {table}"

    if where_clause:
        query += f" WHERE {where_clause}"

    query += " GROUP BY " + ", ".join(group_columns)

    if having_clause:
        query += f" HAVING {having_clause}"

    if order_by_clause:
        query += f" ORDER BY {order_by_clause}"

    return query + ";"


def demonstrate_sql_generation() -> None:
    print_title("SQL statement construction")

    sql = build_group_by_sql(
        table="sales",
        group_columns=["region", "category"],
        aggregate_expressions=[
            "COUNT(*) AS order_count",
            "SUM(quantity) AS total_quantity",
            "AVG(unit_price) AS average_unit_price",
        ],
        where_clause="status = 'Completed'",
        having_clause="SUM(quantity) >= 5",
        order_by_clause="total_quantity DESC",
    )

    print(sql)

    print(
        "\nSecurity rule: table and column identifiers should be controlled "
        "by trusted application logic. User-provided values should normally "
        "be passed as parameters rather than concatenated into SQL."
    )


# ---------------------------------------------------------------------------
# Section 23: Advanced sales analytics
# ---------------------------------------------------------------------------

def run_sales_case_study() -> None:
    print_title("Advanced sales analysis case study")

    completed = where(
        SALES,
        lambda row: row["status"] == "Completed",
    )

    grouped = aggregate_query(
        completed,
        group_columns=["region", "category"],
        aggregates=[
            AggregateDefinition(
                "orders",
                lambda rows: len(rows),
            ),
            AggregateDefinition(
                "units",
                lambda rows: sum(row["quantity"] for row in rows),
            ),
            AggregateDefinition(
                "gross_sales",
                lambda rows: sum(
                    row["quantity"] * row["unit_price"]
                    for row in rows
                ),
            ),
            AggregateDefinition(
                "net_sales",
                lambda rows: sum(
                    calculate_net_sales(row)
                    for row in rows
                ),
            ),
            AggregateDefinition(
                "average_order_value",
                lambda rows: sum(
                    calculate_net_sales(row)
                    for row in rows
                ) / len(rows),
            ),
            AggregateDefinition(
                "unique_customers",
                lambda rows: len(
                    {
                        row["customer"]
                        for row in rows
                        if row["customer"] is not None
                    }
                ),
            ),
        ],
        group_filter=lambda result: result["net_sales"] >= 10000,
    )

    grouped.sort(
        key=lambda result: result["net_sales"],
        reverse=True,
    )

    display = []

    for result in grouped:
        display.append(
            {
                "region": result["region"],
                "category": result["category"],
                "orders": result["orders"],
                "units": result["units"],
                "gross_sales": money(result["gross_sales"]),
                "net_sales": money(result["net_sales"]),
                "average_order_value": money(result["average_order_value"]),
                "unique_customers": result["unique_customers"],
            }
        )

    print_rows(display)


# ---------------------------------------------------------------------------
# Section 24: Exact financial aggregation
# ---------------------------------------------------------------------------

def decimal_net_sales(row: dict[str, Any]) -> Decimal:
    """Use Decimal for exact cent-level financial calculations."""
    quantity = Decimal(str(row["quantity"]))
    unit_price = Decimal(str(row["unit_price"]))
    discount = Decimal(str(row["discount"]))

    return quantity * unit_price * (Decimal("1") - discount)


def demonstrate_decimal_finance() -> None:
    print_title("Financial precision and grouped calculations")

    groups = group_by_column(SALES, "region")

    results = []

    for region, rows in groups.items():
        total = sum(
            (decimal_net_sales(row) for row in rows),
            Decimal("0"),
        )

        total = total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        results.append(
            {
                "region": region,
                "exact_net_sales": money(total),
            }
        )

    results.sort(key=lambda row: str(row["region"]))
    print_rows(results)

    print(
        "\nFor production financial systems, decimal/fixed-point or "
        "database NUMERIC/DECIMAL types are generally preferable to "
        "binary floating-point arithmetic for monetary values."
    )


# ---------------------------------------------------------------------------
# Section 25: Comparison with a SQL query
# ---------------------------------------------------------------------------

def demonstrate_sql_translation() -> None:
    print_title("Translating the Python grouping model into SQL")

    print(
        """
Python model:
    filtered = [row for row in SALES if row["status"] == "Completed"]
    groups = group_by_columns(filtered, ["region", "category"])
    aggregate each group

SQL model:
    SELECT
        region,
        category,
        COUNT(*) AS orders,
        SUM(quantity) AS units,
        SUM(quantity * unit_price * (1 - discount)) AS net_sales
    FROM sales
    WHERE status = 'Completed'
    GROUP BY region, category
    HAVING SUM(quantity * unit_price * (1 - discount)) >= 10000
    ORDER BY net_sales DESC;

The two approaches express the same relational idea, although a real SQL
database has a query optimizer, indexes, execution plans, parallelism,
storage engines, transaction semantics, and database-specific behavior.
"""
    )


# ---------------------------------------------------------------------------
# Section 26: Study checklist
# ---------------------------------------------------------------------------

def print_study_checklist() -> None:
    print_title("GROUP BY study checklist")

    checklist = [
        "A group contains rows sharing the same grouping key.",
        "GROUP BY transforms row-level data into groups.",
        "Aggregate functions calculate values for each group.",
        "COUNT(*) counts rows.",
        "COUNT(column) ignores NULL values.",
        "SUM, AVG, MIN, and MAX operate over group members.",
        "Multiple GROUP BY columns form composite grouping keys.",
        "WHERE filters rows before grouping.",
        "HAVING filters groups after aggregation.",
        "ORDER BY controls result ordering.",
        "COUNT(DISTINCT column) counts unique non-NULL values.",
        "Conditional aggregation computes metrics for subsets inside groups.",
        "NULL handling matters when interpreting grouped results.",
        "Join cardinality can alter aggregate totals.",
        "Financial calculations require attention to numeric precision.",
        "Large grouped queries require memory and execution-plan awareness.",
        "Indexes and pre-filtering can affect database performance.",
        "Grouped output should not be assumed to have a stable order without ORDER BY.",
    ]

    for number, item in enumerate(checklist, start=1):
        print(f"{number:02d}. {item}")


# ---------------------------------------------------------------------------
# Section 27: Main program
# ---------------------------------------------------------------------------

def main() -> None:
    print_title("GROUP BY: complete Python study program")

    print(
        "This program models the central idea of SQL GROUP BY: "
        "partitioning rows into groups and calculating aggregate values "
        "for each group."
    )

    demonstrate_single_column_grouping()
    demonstrate_multiple_column_grouping()
    demonstrate_count_behavior()
    demonstrate_query_order()
    demonstrate_having()
    demonstrate_conditional_aggregation()
    demonstrate_distinct_counts()
    demonstrate_average_pitfall()
    demonstrate_top_groups()
    demonstrate_rollup()
    demonstrate_reusable_engine()
    demonstrate_edge_cases()
    demonstrate_validation()
    demonstrate_join_multiplication()
    explain_performance()
    demonstrate_sql_generation()
    run_sales_case_study()
    demonstrate_decimal_finance()
    demonstrate_sql_translation()
    print_study_checklist()

    print_title("Program completed")
    print("All GROUP BY demonstrations executed successfully.")


if __name__ == "__main__":
    main()
