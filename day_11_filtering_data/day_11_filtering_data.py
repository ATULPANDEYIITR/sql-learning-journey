"""
SQL FILTERING DATA: WHERE, COMPARISON OPERATORS, AND LOGICAL CONDITIONS

This standalone study script teaches SQL filtering from beginner to advanced level
using Python's built-in sqlite3 module. SQLite is used so that the examples run
without external packages or a separate database server.

Main topics:
- SELECT and WHERE
- Comparison operators
- NULL and three-valued logic
- AND, OR, NOT
- Operator precedence and parentheses
- IN, NOT IN
- BETWEEN, NOT BETWEEN
- LIKE and pattern matching
- IS NULL and IS NOT NULL
- CASE expressions used with filtering
- Filtering dates and numbers
- Filtering text
- Combining many conditions
- EXISTS and correlated filtering
- Subqueries
- Aggregate filtering with HAVING
- Filtering JOIN results
- Conditional aggregation
- Query debugging
- SQL injection and parameterized queries
- Indexes and filtering performance
- Common mistakes and edge cases
- Practical business-style examples
- Automated assertions for important results

Run with:
    python sql_filtering_data.py
"""

import sqlite3
from datetime import date


# =============================================================================
# SECTION 1: DATABASE SETUP
# =============================================================================

def create_database():
    """Create an in-memory SQLite database and populate it with realistic data."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            department_id INTEGER,
            job_title TEXT NOT NULL,
            salary REAL NOT NULL,
            age INTEGER,
            city TEXT,
            email TEXT,
            hire_date TEXT NOT NULL,
            manager_id INTEGER,
            employment_status TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY (department_id) REFERENCES departments(department_id),
            FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
        );

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            city TEXT,
            country TEXT NOT NULL,
            age INTEGER,
            credit_limit REAL,
            signup_date TEXT NOT NULL,
            status TEXT NOT NULL,
            email TEXT
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            payment_method TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL,
            rating REAL,
            discontinued INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE sales (
            sale_id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            sale_date TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            region TEXT,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        INSERT INTO departments VALUES
            (1, 'Engineering'),
            (2, 'Finance'),
            (3, 'Marketing'),
            (4, 'Human Resources'),
            (5, 'Operations');

        INSERT INTO employees VALUES
            (1, 'Anita Sharma', 1, 'Engineering Manager', 145000, 42, 'Delhi',
             'anita@example.com', '2017-03-15', NULL, 'Active'),
            (2, 'Rahul Verma', 1, 'Senior Developer', 118000, 35, 'Lucknow',
             'rahul@example.com', '2019-07-10', 1, 'Active'),
            (3, 'Priya Singh', 1, 'Data Engineer', 105000, 31, 'Lucknow',
             'priya@example.com', '2021-01-20', 1, 'Active'),
            (4, 'Vikram Rao', 2, 'Financial Analyst', 82000, 29, 'Mumbai',
             'vikram@example.com', '2022-05-11', 7, 'Active'),
            (5, 'Neha Gupta', 3, 'Marketing Specialist', 72000, 27, 'Delhi',
             'neha@example.com', '2023-02-14', 8, 'Active'),
            (6, 'Arjun Mehta', 1, 'Developer', 91000, 26, 'Pune',
             'arjun@example.com', '2023-08-01', 2, 'Active'),
            (7, 'Meera Kapoor', 2, 'Finance Manager', 125000, 40, 'Mumbai',
             'meera@example.com', '2018-11-05', NULL, 'Active'),
            (8, 'Sanjay Patel', 3, 'Marketing Manager', 112000, 38, 'Ahmedabad',
             'sanjay@example.com', '2019-04-22', NULL, 'Active'),
            (9, 'Karan Joshi', 4, 'HR Executive', 68000, 25, NULL,
             'karan@example.com', '2024-01-15', 10, 'Active'),
            (10, 'Pooja Nair', 4, 'HR Manager', 108000, 39, 'Bengaluru',
             'pooja@example.com', '2016-09-19', NULL, 'Active'),
            (11, 'Rohit Das', 5, 'Operations Analyst', 76000, 33, 'Kolkata',
             'rohit@example.com', '2020-06-30', 12, 'Inactive'),
            (12, 'Isha Malhotra', 5, 'Operations Manager', 115000, 44, 'Jaipur',
             'isha@example.com', '2015-12-01', NULL, 'Active');

        INSERT INTO customers VALUES
            (1, 'Amit Kumar', 'Lucknow', 'India', 31, 50000, '2023-01-15', 'Active',
             'amit@example.com'),
            (2, 'Sneha Patel', 'Mumbai', 'India', 27, 75000, '2022-08-12', 'Active',
             'sneha@example.com'),
            (3, 'John Smith', 'New York', 'USA', 45, 120000, '2021-04-20', 'Active',
             'john@example.com'),
            (4, 'Maria Garcia', 'Madrid', 'Spain', 38, 90000, '2023-06-17', 'Inactive',
             'maria@example.com'),
            (5, 'Ravi Shah', 'Delhi', 'India', 22, 30000, '2024-01-03', 'Active',
             'ravi@example.com'),
            (6, 'Emma Wilson', NULL, 'UK', 34, NULL, '2020-11-11', 'Active',
             'emma@example.com'),
            (7, 'Daniel Lee', 'Singapore', 'Singapore', 29, 65000, '2024-02-01', 'Pending',
             'daniel@example.com'),
            (8, 'Fatima Khan', 'Lucknow', 'India', 52, 100000, '2019-09-09', 'Active',
             'fatima@example.com');

        INSERT INTO orders VALUES
            (101, 1, '2025-01-05', 12500, 'Completed', 'UPI'),
            (102, 1, '2025-02-14', 8200, 'Completed', 'Card'),
            (103, 2, '2025-01-18', 45000, 'Completed', 'Card'),
            (104, 2, '2025-03-02', 15000, 'Cancelled', 'UPI'),
            (105, 3, '2025-02-20', 72000, 'Completed', 'Card'),
            (106, 4, '2025-02-25', 19000, 'Refunded', 'Card'),
            (107, 5, '2025-03-10', 5400, 'Pending', 'UPI'),
            (108, 6, '2025-03-15', 32000, 'Completed', 'Bank Transfer'),
            (109, 8, '2025-01-25', 67000, 'Completed', 'Card'),
            (110, 8, '2025-03-21', 18000, 'Completed', 'UPI');

        INSERT INTO products VALUES
            (1, 'Laptop Pro 14', 'Electronics', 125000, 12, 4.8, 0),
            (2, 'Wireless Mouse', 'Electronics', 1800, 150, 4.4, 0),
            (3, 'Mechanical Keyboard', 'Electronics', 6500, 70, 4.7, 0),
            (4, 'Office Chair', 'Furniture', 18500, 25, 4.2, 0),
            (5, 'Standing Desk', 'Furniture', 32000, 8, 4.6, 0),
            (6, 'Notebook', 'Stationery', 250, 500, 4.1, 0),
            (7, 'Old Monitor', 'Electronics', 9000, 0, 3.5, 1),
            (8, 'USB-C Hub', 'Electronics', 4200, 45, NULL, 0),
            (9, 'Desk Lamp', 'Furniture', 2800, 90, 4.0, 0);

        INSERT INTO sales VALUES
            (1, 1, '2025-01-05', 2, 125000, 'North'),
            (2, 2, '2025-01-05', 10, 1800, 'North'),
            (3, 3, '2025-01-06', 5, 6500, 'West'),
            (4, 4, '2025-01-08', 3, 18500, 'South'),
            (5, 5, '2025-01-10', 1, 32000, 'North'),
            (6, 2, '2025-02-11', 20, 1800, 'East'),
            (7, 6, '2025-02-15', 50, 250, 'West'),
            (8, 8, '2025-02-18', 7, 4200, 'South'),
            (9, 3, '2025-03-05', 12, 6500, 'North'),
            (10, 9, '2025-03-11', 8, 2800, 'East');

        CREATE INDEX idx_employees_salary ON employees(salary);
        CREATE INDEX idx_employees_department ON employees(department_id);
        CREATE INDEX idx_customers_country ON customers(country);
        CREATE INDEX idx_orders_customer ON orders(customer_id);
        CREATE INDEX idx_orders_date ON orders(order_date);
        CREATE INDEX idx_products_category_price ON products(category, price);
        """
    )

    connection.commit()
    return connection


# =============================================================================
# SECTION 2: DISPLAY HELPERS
# =============================================================================

def print_section(title):
    """Print a clear section heading."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_query_result(connection, sql, parameters=(), title=None):
    """
    Execute a SELECT query and print the result.

    Parameters are supplied separately from SQL. This is the safe approach for
    user-controlled values and avoids SQL injection.
    """
    if title:
        print(f"\n{title}")

    cursor = connection.execute(sql, parameters)
    rows = cursor.fetchall()

    if not rows:
        print("(no rows)")
        return rows

    column_names = rows[0].keys()
    print(" | ".join(column_names))
    print("-" * (len(" | ".join(column_names)) + 10))

    for row in rows:
        print(" | ".join(str(row[column]) for column in column_names))

    print(f"Rows returned: {len(rows)}")
    return rows


# =============================================================================
# SECTION 3: SELECT WITHOUT FILTERING
# =============================================================================

def demonstrate_basic_select(connection):
    print_section("1. BASIC SELECT BEFORE FILTERING")

    # SELECT chooses columns. WHERE chooses rows.
    print_query_result(
        connection,
        """
        SELECT employee_id, employee_name, department_id, salary
        FROM employees
        ORDER BY employee_id;
        """,
        title="All employees"
    )

    # Selecting only particular columns is independent of filtering.
    print_query_result(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        ORDER BY salary DESC;
        """,
        title="Only employee names and salaries"
    )


# =============================================================================
# SECTION 4: WHERE FUNDAMENTALS
# =============================================================================

def demonstrate_where(connection):
    print_section("2. WHERE: FILTERING ROWS")

    # WHERE evaluates a condition for every candidate row.
    # Rows for which the condition is TRUE are returned.
    print_query_result(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary > 100000
        ORDER BY salary DESC;
        """,
        title="Employees earning more than 100000"
    )

    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city = 'Lucknow';
        """,
        title="Employees located in Lucknow"
    )

    print_query_result(
        connection,
        """
        SELECT employee_name, employment_status
        FROM employees
        WHERE employment_status = 'Active';
        """,
        title="Active employees"
    )


# =============================================================================
# SECTION 5: COMPARISON OPERATORS
# =============================================================================

def demonstrate_comparison_operators(connection):
    print_section("3. COMPARISON OPERATORS")

    examples = [
        (
            "Equal to (=)",
            """
            SELECT employee_name, salary
            FROM employees
            WHERE salary = 105000;
            """
        ),
        (
            "Not equal to (<>), standard SQL form",
            """
            SELECT employee_name, employment_status
            FROM employees
            WHERE employment_status <> 'Active';
            """
        ),
        (
            "Not equal to (!=), supported by SQLite and many systems",
            """
            SELECT employee_name, employment_status
            FROM employees
            WHERE employment_status != 'Active';
            """
        ),
        (
            "Greater than (>)",
            """
            SELECT employee_name, age
            FROM employees
            WHERE age > 40;
            """
        ),
        (
            "Less than (<)",
            """
            SELECT employee_name, age
            FROM employees
            WHERE age < 30;
            """
        ),
        (
            "Greater than or equal to (>=)",
            """
            SELECT employee_name, salary
            FROM employees
            WHERE salary >= 100000;
            """
        ),
        (
            "Less than or equal to (<=)",
            """
            SELECT employee_name, salary
            FROM employees
            WHERE salary <= 80000;
            """
        ),
    ]

    for title, sql in examples:
        print_query_result(connection, sql, title=title)


# =============================================================================
# SECTION 6: AND
# =============================================================================

def demonstrate_and(connection):
    print_section("4. AND: ALL CONDITIONS MUST BE TRUE")

    # AND narrows the result.
    print_query_result(
        connection,
        """
        SELECT employee_name, salary, age
        FROM employees
        WHERE salary > 90000
          AND age < 40
        ORDER BY salary DESC;
        """,
        title="Salary > 90000 AND age < 40"
    )

    # A row must satisfy both conditions.
    print_query_result(
        connection,
        """
        SELECT employee_name, city, salary
        FROM employees
        WHERE city = 'Lucknow'
          AND salary >= 100000;
        """,
        title="Lucknow employees earning at least 100000"
    )


# =============================================================================
# SECTION 7: OR
# =============================================================================

def demonstrate_or(connection):
    print_section("5. OR: AT LEAST ONE CONDITION MUST BE TRUE")

    print_query_result(
        connection,
        """
        SELECT employee_name, department_id, salary
        FROM employees
        WHERE department_id = 1
           OR department_id = 2
        ORDER BY department_id, employee_name;
        """,
        title="Engineering OR Finance employees"
    )

    # OR can produce a wider result set than AND.
    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city = 'Lucknow'
           OR city = 'Mumbai';
        """,
        title="Employees in Lucknow OR Mumbai"
    )


# =============================================================================
# SECTION 8: NOT
# =============================================================================

def demonstrate_not(connection):
    print_section("6. NOT: NEGATING A CONDITION")

    print_query_result(
        connection,
        """
        SELECT employee_name, employment_status
        FROM employees
        WHERE NOT employment_status = 'Inactive';
        """,
        title="Employees whose status is not Inactive"
    )

    # NOT can also negate a grouped condition.
    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE NOT (city = 'Lucknow' OR city = 'Mumbai');
        """,
        title="Employees outside Lucknow and Mumbai"
    )


# =============================================================================
# SECTION 9: OPERATOR PRECEDENCE
# =============================================================================

def demonstrate_precedence(connection):
    print_section("7. OPERATOR PRECEDENCE AND PARENTHESES")

    # SQL generally evaluates NOT before AND before OR.
    # Without parentheses, this means:
    #
    #     A OR B AND C
    #
    # behaves like:
    #
    #     A OR (B AND C)
    #
    # Parentheses make the intended logic explicit.

    print_query_result(
        connection,
        """
        SELECT employee_name, department_id, city, salary
        FROM employees
        WHERE department_id = 1
           OR department_id = 2
          AND salary > 100000
        ORDER BY employee_id;
        """,
        title="Without parentheses: A OR (B AND C)"
    )

    print_query_result(
        connection,
        """
        SELECT employee_name, department_id, city, salary
        FROM employees
        WHERE (department_id = 1 OR department_id = 2)
          AND salary > 100000
        ORDER BY employee_id;
        """,
        title="With parentheses: (A OR B) AND C"
    )


# =============================================================================
# SECTION 10: IN AND NOT IN
# =============================================================================

def demonstrate_in(connection):
    print_section("8. IN AND NOT IN")

    # IN is useful when comparing one value against a list of possible values.
    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city IN ('Lucknow', 'Mumbai', 'Delhi')
        ORDER BY city, employee_name;
        """,
        title="Employees in any of three cities"
    )

    print_query_result(
        connection,
        """
        SELECT employee_name, department_id
        FROM employees
        WHERE department_id NOT IN (1, 3)
        ORDER BY employee_id;
        """,
        title="Employees outside Engineering and Marketing"
    )

    # IN is often clearer than a long chain of OR expressions.
    print_query_result(
        connection,
        """
        SELECT employee_name, employment_status
        FROM employees
        WHERE employment_status IN ('Active', 'Pending');
        """,
        title="Active or Pending employees"
    )


# =============================================================================
# SECTION 11: BETWEEN
# =============================================================================

def demonstrate_between(connection):
    print_section("9. BETWEEN AND NOT BETWEEN")

    # BETWEEN is inclusive at both ends.
    # salary BETWEEN 80000 AND 110000 means:
    # salary >= 80000 AND salary <= 110000
    print_query_result(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary BETWEEN 80000 AND 110000
        ORDER BY salary;
        """,
        title="Salary between 80000 and 110000 inclusive"
    )

    print_query_result(
        connection,
        """
        SELECT employee_name, age
        FROM employees
        WHERE age NOT BETWEEN 30 AND 40
        ORDER BY age;
        """,
        title="Age outside the inclusive range 30 to 40"
    )


# =============================================================================
# SECTION 12: TEXT FILTERING WITH LIKE
# =============================================================================

def demonstrate_like(connection):
    print_section("10. LIKE AND TEXT PATTERN MATCHING")

    # % means zero or more characters.
    print_query_result(
        connection,
        """
        SELECT employee_name, email
        FROM employees
        WHERE employee_name LIKE 'A%';
        """,
        title="Names beginning with A"
    )

    # % can also match a suffix.
    print_query_result(
        connection,
        """
        SELECT employee_name, email
        FROM employees
        WHERE email LIKE '%@example.com';
        """,
        title="Email addresses ending with @example.com"
    )

    # % can match text anywhere.
    print_query_result(
        connection,
        """
        SELECT employee_name
        FROM employees
        WHERE employee_name LIKE '%a%';
        """,
        title="Names containing the letter a"
    )

    # _ means exactly one character.
    print_query_result(
        connection,
        """
        SELECT employee_name
        FROM employees
        WHERE employee_name LIKE 'P____';
        """,
        title="Names beginning with P followed by exactly four characters"
    )


# =============================================================================
# SECTION 13: NULL AND THREE-VALUED LOGIC
# =============================================================================

def demonstrate_null(connection):
    print_section("11. NULL AND THREE-VALUED LOGIC")

    # NULL means missing, unknown, or not applicable.
    # It is not the same as 0, an empty string, or the text 'NULL'.

    # Correct way to find NULL.
    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city IS NULL;
        """,
        title="Employees with no city"
    )

    # Correct way to find non-NULL.
    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city IS NOT NULL;
        """,
        title="Employees whose city is known"
    )

    # Incorrect conceptual pattern:
    # WHERE city = NULL
    #
    # The comparison does not become TRUE. NULL represents an unknown value,
    # and comparisons involving NULL normally produce UNKNOWN.
    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city = NULL;
        """,
        title="Incorrect NULL comparison: city = NULL"
    )

    # The same issue affects NOT IN when its list contains NULL.
    print_query_result(
        connection,
        """
        SELECT employee_name
        FROM employees
        WHERE employee_id NOT IN (1, 2, NULL);
        """,
        title="NOT IN with NULL demonstrates an important edge case"
    )


# =============================================================================
# SECTION 14: THREE-VALUED LOGIC DEMONSTRATION
# =============================================================================

def demonstrate_three_valued_logic(connection):
    print_section("12. SQL THREE-VALUED LOGIC")

    # SQL conditions can evaluate to TRUE, FALSE, or UNKNOWN.
    # UNKNOWN is particularly important when NULL is involved.

    print_query_result(
        connection,
        """
        SELECT
            NULL = 5 AS null_equals_five,
            NULL <> 5 AS null_not_equal_five,
            NULL > 5 AS null_greater_than_five,
            NULL IS NULL AS null_is_null,
            NULL IS NOT NULL AS null_is_not_null;
        """,
        title="Direct NULL logic"
    )

    # WHERE returns rows only when the condition evaluates to TRUE.
    # FALSE and UNKNOWN rows are excluded.
    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city <> 'Lucknow';
        """,
        title="city <> 'Lucknow' does not return NULL cities"
    )


# =============================================================================
# SECTION 15: DATE FILTERING
# =============================================================================

def demonstrate_dates(connection):
    print_section("13. FILTERING DATES")

    # ISO YYYY-MM-DD strings sort chronologically in SQLite.
    print_query_result(
        connection,
        """
        SELECT employee_name, hire_date
        FROM employees
        WHERE hire_date >= '2020-01-01'
        ORDER BY hire_date;
        """,
        title="Employees hired on or after 2020-01-01"
    )

    print_query_result(
        connection,
        """
        SELECT employee_name, hire_date
        FROM employees
        WHERE hire_date BETWEEN '2020-01-01' AND '2023-12-31'
        ORDER BY hire_date;
        """,
        title="Employees hired during 2020 through 2023"
    )

    print_query_result(
        connection,
        """
        SELECT order_id, order_date, amount
        FROM orders
        WHERE order_date >= '2025-02-01'
          AND order_date < '2025-03-01'
        ORDER BY order_date;
        """,
        title="Orders during February 2025"
    )


# =============================================================================
# SECTION 16: NUMERIC FILTERING AND CALCULATED EXPRESSIONS
# =============================================================================

def demonstrate_numeric_expressions(connection):
    print_section("14. FILTERING USING CALCULATED EXPRESSIONS")

    print_query_result(
        connection,
        """
        SELECT product_name, price, stock_quantity,
               price * stock_quantity AS inventory_value
        FROM products
        WHERE price * stock_quantity > 100000
        ORDER BY inventory_value DESC;
        """,
        title="Products whose inventory value exceeds 100000"
    )

    print_query_result(
        connection,
        """
        SELECT employee_name, salary, salary * 1.10 AS projected_salary
        FROM employees
        WHERE salary * 1.10 >= 120000
        ORDER BY projected_salary DESC;
        """,
        title="Employees whose projected 10% increased salary reaches 120000"
    )


# =============================================================================
# SECTION 17: MULTIPLE CONDITIONS
# =============================================================================

def demonstrate_complex_conditions(connection):
    print_section("15. COMPLEX LOGICAL CONDITIONS")

    print_query_result(
        connection,
        """
        SELECT employee_name, department_id, salary, city
        FROM employees
        WHERE employment_status = 'Active'
          AND salary >= 90000
          AND (
                department_id = 1
                OR department_id = 2
              )
        ORDER BY salary DESC;
        """,
        title="Active employees in Engineering or Finance earning at least 90000"
    )

    print_query_result(
        connection,
        """
        SELECT employee_name, salary, age, city
        FROM employees
        WHERE (
                salary >= 110000
                AND age >= 35
              )
           OR (
                city = 'Lucknow'
                AND salary >= 100000
              )
        ORDER BY salary DESC;
        """,
        title="Two alternative business conditions"
    )


# =============================================================================
# SECTION 18: CASE EXPRESSIONS AND FILTERING
# =============================================================================

def demonstrate_case(connection):
    print_section("16. CASE EXPRESSIONS")

    # CASE is not itself a WHERE operator, but it is useful for deriving
    # classifications that can be displayed, sorted, grouped, or filtered
    # through a subquery/CTE.
    print_query_result(
        connection,
        """
        SELECT
            employee_name,
            salary,
            CASE
                WHEN salary >= 120000 THEN 'High'
                WHEN salary >= 90000 THEN 'Medium'
                ELSE 'Standard'
            END AS salary_band
        FROM employees
        ORDER BY salary DESC;
        """,
        title="Salary classification"
    )

    # Derived classification can be filtered by wrapping the query.
    print_query_result(
        connection,
        """
        SELECT *
        FROM (
            SELECT
                employee_name,
                salary,
                CASE
                    WHEN salary >= 120000 THEN 'High'
                    WHEN salary >= 90000 THEN 'Medium'
                    ELSE 'Standard'
                END AS salary_band
            FROM employees
        )
        WHERE salary_band = 'High';
        """,
        title="Filter a derived CASE classification"
    )


# =============================================================================
# SECTION 19: PARAMETERIZED QUERIES
# =============================================================================

def demonstrate_parameterized_filtering(connection):
    print_section("17. PARAMETERIZED FILTERING")

    minimum_salary = 100000
    city = "Lucknow"

    # Never construct SQL by concatenating untrusted input.
    # Parameter placeholders keep values separate from SQL instructions.
    print_query_result(
        connection,
        """
        SELECT employee_name, city, salary
        FROM employees
        WHERE salary >= ?
          AND city = ?
        ORDER BY salary DESC;
        """,
        (minimum_salary, city),
        title="Safe parameterized filtering"
    )


# =============================================================================
# SECTION 20: SQL INJECTION SECURITY
# =============================================================================

def demonstrate_sql_injection_concept(connection):
    print_section("18. SQL INJECTION: SECURITY CONSIDERATION")

    malicious_value = "' OR 1=1 --"

    # Unsafe SQL construction:
    unsafe_sql = (
        "SELECT employee_name FROM employees "
        f"WHERE city = '{malicious_value}'"
    )

    print("Unsafe SQL construction would produce:")
    print(unsafe_sql)

    # The safe approach treats the value as data.
    print_query_result(
        connection,
        """
        SELECT employee_name
        FROM employees
        WHERE city = ?;
        """,
        (malicious_value,),
        title="Parameterized query treats the input as data"
    )


# =============================================================================
# SECTION 21: IN WITH PARAMETERS
# =============================================================================

def demonstrate_dynamic_in(connection):
    print_section("19. PARAMETERIZED IN CONDITIONS")

    cities = ["Lucknow", "Mumbai", "Delhi"]

    # SQLite placeholders cannot directly represent a whole variable-length
    # list. Create one placeholder per value.
    placeholders = ", ".join("?" for _ in cities)

    sql = f"""
        SELECT employee_name, city
        FROM employees
        WHERE city IN ({placeholders})
        ORDER BY city, employee_name;
    """

    print_query_result(
        connection,
        sql,
        cities,
        title="Safe dynamic IN filtering"
    )


# =============================================================================
# SECTION 22: EXISTS
# =============================================================================

def demonstrate_exists(connection):
    print_section("20. EXISTS AND CORRELATED FILTERING")

    # EXISTS asks whether at least one matching row exists.
    print_query_result(
        connection,
        """
        SELECT c.customer_id, c.customer_name
        FROM customers AS c
        WHERE EXISTS (
            SELECT 1
            FROM orders AS o
            WHERE o.customer_id = c.customer_id
        )
        ORDER BY c.customer_id;
        """,
        title="Customers who have at least one order"
    )

    # NOT EXISTS is often safer than NOT IN when NULLs may be involved.
    print_query_result(
        connection,
        """
        SELECT c.customer_id, c.customer_name
        FROM customers AS c
        WHERE NOT EXISTS (
            SELECT 1
            FROM orders AS o
            WHERE o.customer_id = c.customer_id
        )
        ORDER BY c.customer_id;
        """,
        title="Customers with no orders"
    )


# =============================================================================
# SECTION 23: SUBQUERY FILTERING
# =============================================================================

def demonstrate_subqueries(connection):
    print_section("21. SUBQUERIES IN WHERE")

    # Filter employees whose salary is above the average salary.
    print_query_result(
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
        title="Employees earning above average"
    )

    # Filter employees earning more than the average salary of their department.
    # This is a correlated subquery because the inner query references the
    # department_id of the outer query.
    print_query_result(
        connection,
        """
        SELECT e.employee_name, e.department_id, e.salary
        FROM employees AS e
        WHERE e.salary > (
            SELECT AVG(e2.salary)
            FROM employees AS e2
            WHERE e2.department_id = e.department_id
        )
        ORDER BY e.department_id, e.salary DESC;
        """,
        title="Employees earning above their department average"
    )


# =============================================================================
# SECTION 24: CTE FILTERING
# =============================================================================

def demonstrate_cte_filtering(connection):
    print_section("22. COMMON TABLE EXPRESSIONS AND FILTERING")

    # A CTE makes a multi-stage filtering problem easier to read.
    print_query_result(
        connection,
        """
        WITH active_employees AS (
            SELECT employee_id, employee_name, department_id, salary
            FROM employees
            WHERE employment_status = 'Active'
        )
        SELECT employee_name, salary
        FROM active_employees
        WHERE salary >= 100000
        ORDER BY salary DESC;
        """,
        title="Filtering a CTE"
    )

    # Multiple CTEs can represent separate logical stages.
    print_query_result(
        connection,
        """
        WITH employee_metrics AS (
            SELECT
                employee_name,
                department_id,
                salary,
                salary / 12.0 AS monthly_salary
            FROM employees
        ),
        high_monthly_salary AS (
            SELECT *
            FROM employee_metrics
            WHERE monthly_salary > 8000
        )
        SELECT employee_name, department_id, monthly_salary
        FROM high_monthly_salary
        ORDER BY monthly_salary DESC;
        """,
        title="Multi-stage filtering with CTEs"
    )


# =============================================================================
# SECTION 25: FILTERING JOIN RESULTS
# =============================================================================

def demonstrate_join_filtering(connection):
    print_section("23. FILTERING JOIN RESULTS")

    print_query_result(
        connection,
        """
        SELECT
            e.employee_name,
            d.department_name,
            e.salary
        FROM employees AS e
        INNER JOIN departments AS d
            ON e.department_id = d.department_id
        WHERE d.department_name = 'Engineering'
          AND e.salary >= 100000
        ORDER BY e.salary DESC;
        """,
        title="Engineering employees earning at least 100000"
    )

    # A condition placed in WHERE after a LEFT JOIN can remove NULL-extended
    # rows and make the result behave like an INNER JOIN for that condition.
    print_query_result(
        connection,
        """
        SELECT
            c.customer_name,
            o.order_id,
            o.amount
        FROM customers AS c
        LEFT JOIN orders AS o
            ON c.customer_id = o.customer_id
        WHERE o.status = 'Completed'
        ORDER BY c.customer_id, o.order_id;
        """,
        title="LEFT JOIN followed by WHERE condition on the right table"
    )

    # Moving the condition into ON preserves customers without completed orders.
    print_query_result(
        connection,
        """
        SELECT
            c.customer_name,
            o.order_id,
            o.amount
        FROM customers AS c
        LEFT JOIN orders AS o
            ON c.customer_id = o.customer_id
           AND o.status = 'Completed'
        ORDER BY c.customer_id, o.order_id;
        """,
        title="LEFT JOIN with filtering condition in ON"
    )


# =============================================================================
# SECTION 26: AGGREGATION AND HAVING
# =============================================================================

def demonstrate_having(connection):
    print_section("24. WHERE VERSUS HAVING")

    # WHERE filters individual rows before grouping.
    # HAVING filters groups after GROUP BY and aggregation.
    print_query_result(
        connection,
        """
        SELECT
            customer_id,
            COUNT(*) AS completed_orders,
            SUM(amount) AS total_spend
        FROM orders
        WHERE status = 'Completed'
        GROUP BY customer_id
        HAVING SUM(amount) >= 30000
        ORDER BY total_spend DESC;
        """,
        title="Customers with at least 30000 in completed-order spend"
    )

    print_query_result(
        connection,
        """
        SELECT
            status,
            COUNT(*) AS order_count,
            AVG(amount) AS average_order
        FROM orders
        WHERE amount > 10000
        GROUP BY status
        HAVING COUNT(*) >= 1
        ORDER BY order_count DESC;
        """,
        title="WHERE before grouping and HAVING after grouping"
    )


# =============================================================================
# SECTION 27: FILTERING AGGREGATES WITH FILTER
# =============================================================================

def demonstrate_aggregate_filter(connection):
    print_section("25. FILTER CLAUSE WITH AGGREGATES")

    # SQLite supports the SQL FILTER clause for conditional aggregation.
    print_query_result(
        connection,
        """
        SELECT
            customer_id,
            COUNT(*) AS all_orders,
            COUNT(*) FILTER (WHERE status = 'Completed') AS completed_orders,
            SUM(amount) FILTER (WHERE status = 'Completed') AS completed_value
        FROM orders
        GROUP BY customer_id
        ORDER BY customer_id;
        """,
        title="Conditional aggregation using FILTER"
    )


# =============================================================================
# SECTION 28: PRACTICAL CUSTOMER FILTERING
# =============================================================================

def demonstrate_customer_business_filters(connection):
    print_section("26. PRACTICAL CUSTOMER FILTERS")

    print_query_result(
        connection,
        """
        SELECT customer_name, city, country, age
        FROM customers
        WHERE country = 'India'
          AND age BETWEEN 25 AND 50
          AND status = 'Active'
        ORDER BY age;
        """,
        title="Active Indian customers aged 25 to 50"
    )

    print_query_result(
        connection,
        """
        SELECT customer_name, country, credit_limit
        FROM customers
        WHERE credit_limit >= 60000
          AND country IN ('India', 'USA', 'UK')
          AND status <> 'Inactive'
        ORDER BY credit_limit DESC;
        """,
        title="Customers meeting credit and status criteria"
    )


# =============================================================================
# SECTION 29: PRACTICAL ORDER FILTERING
# =============================================================================

def demonstrate_order_business_filters(connection):
    print_section("27. PRACTICAL ORDER FILTERS")

    print_query_result(
        connection,
        """
        SELECT order_id, customer_id, order_date, amount, status
        FROM orders
        WHERE status = 'Completed'
          AND amount >= 20000
          AND order_date >= '2025-01-01'
          AND order_date < '2025-04-01'
        ORDER BY amount DESC;
        """,
        title="Large completed orders in Q1 2025"
    )

    print_query_result(
        connection,
        """
        SELECT order_id, amount, payment_method
        FROM orders
        WHERE payment_method IN ('UPI', 'Card')
          AND status NOT IN ('Cancelled', 'Refunded')
        ORDER BY amount DESC;
        """,
        title="Orders using UPI or Card that were not cancelled/refunded"
    )


# =============================================================================
# SECTION 30: PRODUCT FILTERING
# =============================================================================

def demonstrate_product_filters(connection):
    print_section("28. PRACTICAL PRODUCT FILTERS")

    print_query_result(
        connection,
        """
        SELECT product_name, category, price, stock_quantity, rating
        FROM products
        WHERE category = 'Electronics'
          AND price BETWEEN 2000 AND 10000
          AND stock_quantity > 0
          AND discontinued = 0
        ORDER BY price;
        """,
        title="Available active electronics between 2000 and 10000"
    )

    print_query_result(
        connection,
        """
        SELECT product_name, rating
        FROM products
        WHERE rating >= 4.5
           OR rating IS NULL
        ORDER BY rating DESC;
        """,
        title="Highly rated products or products without a rating"
    )


# =============================================================================
# SECTION 31: CONDITIONAL LOGIC WITH NULL
# =============================================================================

def demonstrate_null_safe_business_rules(connection):
    print_section("29. NULL-SAFE BUSINESS CONDITIONS")

    # Suppose the business rule is:
    # "Show customers whose credit limit is at least 60000, or whose credit
    # limit has not yet been assigned."
    print_query_result(
        connection,
        """
        SELECT customer_name, credit_limit
        FROM customers
        WHERE credit_limit >= 60000
           OR credit_limit IS NULL
        ORDER BY customer_name;
        """,
        title="Credit limit at least 60000 OR not yet assigned"
    )


# =============================================================================
# SECTION 32: FILTERING USING BOOLEAN-LIKE COLUMNS
# =============================================================================

def demonstrate_boolean_style_filtering(connection):
    print_section("30. BOOLEAN-LIKE FILTERING")

    # SQLite has no dedicated BOOLEAN storage class in the same way some
    # database systems do. Applications commonly use 0 and 1.
    print_query_result(
        connection,
        """
        SELECT product_name, discontinued
        FROM products
        WHERE discontinued = 0;
        """,
        title="Products that are not discontinued"
    )

    print_query_result(
        connection,
        """
        SELECT product_name, discontinued
        FROM products
        WHERE discontinued = 1;
        """,
        title="Discontinued products"
    )


# =============================================================================
# SECTION 33: FILTERING WITH FUNCTIONS
# =============================================================================

def demonstrate_functions_in_where(connection):
    print_section("31. FUNCTIONS INSIDE WHERE")

    # LOWER() allows case-normalized comparisons.
    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE LOWER(city) = 'lucknow';
        """,
        title="Case-normalized city comparison"
    )

    # LENGTH() is a SQLite string function.
    print_query_result(
        connection,
        """
        SELECT employee_name, LENGTH(employee_name) AS name_length
        FROM employees
        WHERE LENGTH(employee_name) > 12
        ORDER BY name_length DESC;
        """,
        title="Names longer than 12 characters"
    )


# =============================================================================
# SECTION 34: FILTERING USING DATE FUNCTIONS
# =============================================================================

def demonstrate_date_functions(connection):
    print_section("32. DATE FUNCTIONS IN FILTERS")

    # SQLite's strftime can extract year/month components from ISO dates.
    print_query_result(
        connection,
        """
        SELECT employee_name, hire_date
        FROM employees
        WHERE strftime('%Y', hire_date) = '2023'
        ORDER BY hire_date;
        """,
        title="Employees hired during 2023"
    )

    print_query_result(
        connection,
        """
        SELECT order_id, order_date, amount
        FROM orders
        WHERE strftime('%m', order_date) = '02'
        ORDER BY order_date;
        """,
        title="Orders placed during February"
    )


# =============================================================================
# SECTION 35: MULTIPLE FILTERING STRATEGIES
# =============================================================================

def demonstrate_equivalent_conditions(connection):
    print_section("33. EQUIVALENT FILTERING STRATEGIES")

    # These two queries express the same logical rule.
    print_query_result(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary >= 90000
          AND salary <= 120000
        ORDER BY salary;
        """,
        title="Range expressed with two comparisons"
    )

    print_query_result(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary BETWEEN 90000 AND 120000
        ORDER BY salary;
        """,
        title="Same range expressed with BETWEEN"
    )


# =============================================================================
# SECTION 36: EDGE CASES
# =============================================================================

def demonstrate_edge_cases(connection):
    print_section("34. IMPORTANT EDGE CASES")

    # Equality with NULL does not work as a NULL test.
    print_query_result(
        connection,
        """
        SELECT customer_name, credit_limit
        FROM customers
        WHERE credit_limit = NULL;
        """,
        title="Edge case: equality against NULL"
    )

    # NOT does not turn UNKNOWN into TRUE.
    print_query_result(
        connection,
        """
        SELECT customer_name, credit_limit
        FROM customers
        WHERE NOT (credit_limit >= 60000);
        """,
        title="Edge case: NOT with NULL"
    )

    # COALESCE can explicitly choose a replacement for NULL.
    print_query_result(
        connection,
        """
        SELECT
            customer_name,
            credit_limit,
            COALESCE(credit_limit, 0) AS effective_credit_limit
        FROM customers
        WHERE COALESCE(credit_limit, 0) < 60000
        ORDER BY effective_credit_limit;
        """,
        title="Using COALESCE to handle missing credit limits"
    )

    # Empty strings and NULL are different concepts.
    print_query_result(
        connection,
        """
        SELECT customer_name, city
        FROM customers
        WHERE city IS NULL OR city = '';
        """,
        title="Testing for NULL or empty text"
    )


# =============================================================================
# SECTION 37: FILTERING WITH SET LOGIC
# =============================================================================

def demonstrate_set_logic(connection):
    print_section("35. SET-BASED FILTERING")

    # UNION combines result sets rather than expressing a WHERE condition.
    # It is useful when separate queries are logically distinct.
    print_query_result(
        connection,
        """
        SELECT employee_name, city
        FROM employees
        WHERE city = 'Lucknow'
        UNION
        SELECT employee_name, city
        FROM employees
        WHERE city = 'Mumbai'
        ORDER BY employee_name;
        """,
        title="UNION as an alternative to two OR branches"
    )


# =============================================================================
# SECTION 38: QUERY PLAN AND PERFORMANCE
# =============================================================================

def demonstrate_query_plan(connection):
    print_section("36. FILTERING PERFORMANCE AND INDEXES")

    # EXPLAIN QUERY PLAN reveals how SQLite intends to execute a query.
    # Indexes can allow a database to locate matching rows without scanning
    # every row in a large table.
    print_query_result(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT employee_name, salary
        FROM employees
        WHERE salary >= 100000;
        """,
        title="Query plan for an indexed salary filter"
    )

    print_query_result(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT employee_name, salary
        FROM employees
        WHERE city = 'Lucknow';
        """,
        title="Query plan for a city filter"
    )


# =============================================================================
# SECTION 39: SARGABILITY AND FUNCTION USE
# =============================================================================

def demonstrate_sargability(connection):
    print_section("37. FILTER DESIGN AND INDEX USAGE")

    # A direct range predicate is usually easier for a database optimizer
    # to satisfy using an index than applying a function to the indexed column.
    #
    # Good pattern:
    #     hire_date >= '2023-01-01' AND hire_date < '2024-01-01'
    #
    # Potentially less index-friendly pattern:
    #     strftime('%Y', hire_date) = '2023'
    #
    # The exact optimizer behavior depends on the database engine and indexes.
    print_query_result(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT employee_name
        FROM employees
        WHERE hire_date >= '2023-01-01'
          AND hire_date < '2024-01-01';
        """,
        title="Range predicate suitable for indexed date filtering"
    )

    print_query_result(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT employee_name
        FROM employees
        WHERE strftime('%Y', hire_date) = '2023';
        """,
        title="Function applied to the date column"
    )


# =============================================================================
# SECTION 40: FILTERING AFTER JOIN WITH MULTIPLE CONDITIONS
# =============================================================================

def demonstrate_multi_table_business_filter(connection):
    print_section("38. MULTI-TABLE BUSINESS FILTER")

    print_query_result(
        connection,
        """
        SELECT
            c.customer_name,
            c.country,
            o.order_id,
            o.amount,
            o.order_date
        FROM customers AS c
        INNER JOIN orders AS o
            ON c.customer_id = o.customer_id
        WHERE c.country = 'India'
          AND c.status = 'Active'
          AND o.status = 'Completed'
          AND o.amount >= 10000
          AND o.order_date >= '2025-01-01'
        ORDER BY o.amount DESC;
        """,
        title="Active Indian customers with large completed orders"
    )


# =============================================================================
# SECTION 41: ADVANCED FILTERING WITH GROUPED BUSINESS RULES
# =============================================================================

def demonstrate_grouped_business_rules(connection):
    print_section("39. ADVANCED GROUPED BUSINESS RULES")

    # Parentheses make complex requirements auditable.
    #
    # Business rule:
    # Active employees who either:
    #   1. work in Engineering and earn at least 100000, OR
    #   2. work in Finance and are at least 35 years old.
    print_query_result(
        connection,
        """
        SELECT employee_name, department_id, salary, age
        FROM employees
        WHERE employment_status = 'Active'
          AND (
                (department_id = 1 AND salary >= 100000)
                OR
                (department_id = 2 AND age >= 35)
              )
        ORDER BY department_id, employee_name;
        """,
        title="Complex grouped business rule"
    )


# =============================================================================
# SECTION 42: FILTERING WITH ALL / ANY-LIKE LOGIC USING SUBQUERIES
# =============================================================================

def demonstrate_subquery_set_filters(connection):
    print_section("40. SUBQUERY SET FILTERS")

    # IN can consume the result of another query.
    print_query_result(
        connection,
        """
        SELECT employee_name, department_id
        FROM employees
        WHERE department_id IN (
            SELECT department_id
            FROM departments
            WHERE department_name IN ('Engineering', 'Finance')
        )
        ORDER BY department_id, employee_name;
        """,
        title="Employees in departments selected by a subquery"
    )

    # EXISTS is often a natural expression for relationship existence.
    print_query_result(
        connection,
        """
        SELECT d.department_name
        FROM departments AS d
        WHERE EXISTS (
            SELECT 1
            FROM employees AS e
            WHERE e.department_id = d.department_id
              AND e.salary > 120000
        );
        """,
        title="Departments with at least one employee earning above 120000"
    )


# =============================================================================
# SECTION 43: TESTING FILTER RESULTS
# =============================================================================

def demonstrate_assertions(connection):
    print_section("41. PROGRAMMATIC VALIDATION OF FILTERS")

    rows = connection.execute(
        """
        SELECT employee_id
        FROM employees
        WHERE salary >= 100000
        """
    ).fetchall()

    employee_ids = {row["employee_id"] for row in rows}

    # Assertions turn educational examples into executable checks.
    assert employee_ids == {1, 2, 3, 7, 8, 10, 12}

    rows = connection.execute(
        """
        SELECT employee_id
        FROM employees
        WHERE city IS NULL
        """
    ).fetchall()

    assert {row["employee_id"] for row in rows} == {9}

    rows = connection.execute(
        """
        SELECT product_id
        FROM products
        WHERE discontinued = 0
          AND stock_quantity > 0
        """
    ).fetchall()

    assert 7 not in {row["product_id"] for row in rows}

    print("All filtering assertions passed.")


# =============================================================================
# SECTION 44: MINI QUERY CHALLENGES
# =============================================================================

def demonstrate_mini_challenges(connection):
    print_section("42. MINI PRACTICE QUERIES")

    # Challenge 1:
    # Find active employees between 25 and 35 years old earning at least 70000.
    print_query_result(
        connection,
        """
        SELECT employee_name, age, salary
        FROM employees
        WHERE employment_status = 'Active'
          AND age BETWEEN 25 AND 35
          AND salary >= 70000
        ORDER BY age, salary DESC;
        """,
        title="Challenge 1: active employees aged 25-35 with salary >= 70000"
    )

    # Challenge 2:
    # Find customers from India who have a credit limit but are not inactive.
    print_query_result(
        connection,
        """
        SELECT customer_name, country, credit_limit, status
        FROM customers
        WHERE country = 'India'
          AND credit_limit IS NOT NULL
          AND status <> 'Inactive'
        ORDER BY credit_limit DESC;
        """,
        title="Challenge 2: eligible Indian customers with known credit limits"
    )

    # Challenge 3:
    # Find products that are either expensive and highly rated, or inexpensive
    # and very well stocked.
    print_query_result(
        connection,
        """
        SELECT product_name, price, rating, stock_quantity
        FROM products
        WHERE (
                price >= 30000
                AND rating >= 4.5
              )
           OR (
                price < 5000
                AND stock_quantity >= 100
              )
        ORDER BY price DESC;
        """,
        title="Challenge 3: grouped product conditions"
    )


# =============================================================================
# SECTION 45: COMMON MISTAKES
# =============================================================================

def demonstrate_common_mistakes(connection):
    print_section("43. COMMON FILTERING MISTAKES")

    # Mistake 1: Forgetting quotes around text values.
    # Correct:
    print_query_result(
        connection,
        """
        SELECT employee_name
        FROM employees
        WHERE city = 'Lucknow';
        """,
        title="Correct text comparison"
    )

    # Mistake 2: Using = NULL instead of IS NULL.
    print_query_result(
        connection,
        """
        SELECT employee_name
        FROM employees
        WHERE city IS NULL;
        """,
        title="Correct NULL comparison"
    )

    # Mistake 3: Forgetting that BETWEEN includes endpoints.
    print_query_result(
        connection,
        """
        SELECT employee_name, age
        FROM employees
        WHERE age BETWEEN 30 AND 35;
        """,
        title="BETWEEN includes 30 and 35"
    )

    # Mistake 4: Incorrectly assuming AND and OR have equal precedence.
    print_query_result(
        connection,
        """
        SELECT employee_name, department_id, salary
        FROM employees
        WHERE department_id = 1
           OR department_id = 2
          AND salary > 110000;
        """,
        title="Potentially misunderstood precedence"
    )

    # Explicit parentheses remove ambiguity.
    print_query_result(
        connection,
        """
        SELECT employee_name, department_id, salary
        FROM employees
        WHERE (department_id = 1 OR department_id = 2)
          AND salary > 110000;
        """,
        title="Explicit intended precedence"
    )


# =============================================================================
# SECTION 46: WHERE CLAUSE ORDER IN THE SQL STATEMENT
# =============================================================================

def demonstrate_sql_clause_order(connection):
    print_section("44. WHERE IN THE STRUCTURE OF A SELECT QUERY")

    # A common logical processing model is:
    #
    # FROM / JOIN
    # WHERE
    # GROUP BY
    # HAVING
    # SELECT
    # ORDER BY
    # LIMIT
    #
    # Physical execution may be optimized differently by the database engine.
    print_query_result(
        connection,
        """
        SELECT department_id, AVG(salary) AS average_salary
        FROM employees
        WHERE employment_status = 'Active'
        GROUP BY department_id
        HAVING AVG(salary) >= 90000
        ORDER BY average_salary DESC;
        """,
        title="WHERE filters rows before grouping; HAVING filters groups"
    )


# =============================================================================
# SECTION 47: LIMIT AFTER FILTERING
# =============================================================================

def demonstrate_limit(connection):
    print_section("45. WHERE WITH ORDER BY AND LIMIT")

    print_query_result(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE employment_status = 'Active'
        ORDER BY salary DESC
        LIMIT 3;
        """,
        title="Top three active employees by salary"
    )


# =============================================================================
# SECTION 48: FILTERING AND DISTINCT
# =============================================================================

def demonstrate_distinct(connection):
    print_section("46. WHERE WITH DISTINCT")

    print_query_result(
        connection,
        """
        SELECT DISTINCT city
        FROM employees
        WHERE city IS NOT NULL
        ORDER BY city;
        """,
        title="Unique known employee cities"
    )


# =============================================================================
# SECTION 49: FILTERING AND NULL SORTING
# =============================================================================

def demonstrate_null_sorting(connection):
    print_section("47. FILTERING AND NULL SORTING")

    # Filtering out NULL before ordering is often the clearest approach when
    # missing values should not participate.
    print_query_result(
        connection,
        """
        SELECT customer_name, credit_limit
        FROM customers
        WHERE credit_limit IS NOT NULL
        ORDER BY credit_limit DESC;
        """,
        title="Customers ordered by known credit limit"
    )


# =============================================================================
# SECTION 50: ADVANCED FILTERING WITH WINDOW FUNCTIONS
# =============================================================================

def demonstrate_window_function_filtering(connection):
    print_section("48. FILTERING RESULTS OF WINDOW FUNCTIONS")

    # A window-function result generally cannot be referenced directly in WHERE
    # at the same query level in standard SQL because WHERE is logically earlier.
    # Wrap the calculation in a subquery or CTE first.
    print_query_result(
        connection,
        """
        WITH ranked_employees AS (
            SELECT
                employee_name,
                department_id,
                salary,
                RANK() OVER (
                    PARTITION BY department_id
                    ORDER BY salary DESC
                ) AS salary_rank
            FROM employees
        )
        SELECT employee_name, department_id, salary, salary_rank
        FROM ranked_employees
        WHERE salary_rank <= 2
        ORDER BY department_id, salary_rank;
        """,
        title="Top two earners per department"
    )


# =============================================================================
# SECTION 51: FILTERING WITH CONDITIONAL AGGREGATION
# =============================================================================

def demonstrate_conditional_aggregation(connection):
    print_section("49. CONDITIONAL AGGREGATION")

    print_query_result(
        connection,
        """
        SELECT
            region,
            SUM(quantity * unit_price) AS total_sales,
            SUM(
                CASE
                    WHEN quantity >= 10
                    THEN quantity * unit_price
                    ELSE 0
                END
            ) AS large_quantity_sales
        FROM sales
        GROUP BY region
        ORDER BY total_sales DESC;
        """,
        title="Aggregate values conditionally"
    )


# =============================================================================
# SECTION 52: FILTERING WITH RANGE BOUNDARIES
# =============================================================================

def demonstrate_range_boundaries(connection):
    print_section("50. INCLUSIVE VERSUS EXCLUSIVE RANGES")

    print_query_result(
        connection,
        """
        SELECT employee_name, salary
        FROM employees
        WHERE salary >= 90000
          AND salary < 100000
        ORDER BY salary;
        """,
        title="Half-open salary interval [90000, 100000)"
    )

    # Half-open intervals are particularly useful for dates and adjacent
    # reporting periods because they avoid overlap at boundaries.
    print_query_result(
        connection,
        """
        SELECT order_id, order_date, amount
        FROM orders
        WHERE order_date >= '2025-01-01'
          AND order_date < '2025-02-01'
        ORDER BY order_date;
        """,
        title="January orders using a half-open date interval"
    )


# =============================================================================
# SECTION 53: FILTERING WITH COLLATION CONSIDERATIONS
# =============================================================================

def demonstrate_text_comparison_considerations(connection):
    print_section("51. TEXT COMPARISON CONSIDERATIONS")

    # SQLite's default LIKE behavior has specific case-sensitivity rules,
    # and behavior differs across database engines and collations.
    # Explicit normalization can make intent clearer for simple ASCII cases.
    print_query_result(
        connection,
        """
        SELECT employee_name
        FROM employees
        WHERE LOWER(employee_name) LIKE 'a%';
        """,
        title="Case-normalized prefix filtering"
    )


# =============================================================================
# SECTION 54: FILTERING AND DATA TYPES
# =============================================================================

def demonstrate_data_type_considerations(connection):
    print_section("52. DATA TYPE CONSIDERATIONS")

    # Dates should be stored consistently. ISO date strings work well for
    # chronological comparison in SQLite when all values use YYYY-MM-DD.
    print_query_result(
        connection,
        """
        SELECT order_id, order_date
        FROM orders
        WHERE order_date >= '2025-02-01'
          AND order_date < '2025-03-01';
        """,
        title="Consistent ISO date filtering"
    )

    # Numeric columns should be numeric rather than strings.
    print_query_result(
        connection,
        """
        SELECT product_name, price
        FROM products
        WHERE price > 10000
        ORDER BY price;
        """,
        title="Numeric comparison on a numeric column"
    )


# =============================================================================
# SECTION 55: REAL-WORLD ANALYTICAL FILTER
# =============================================================================

def demonstrate_real_world_analytical_filter(connection):
    print_section("53. REAL-WORLD ANALYTICAL FILTER")

    # Requirement:
    # Identify Indian customers who:
    # - are active,
    # - have known credit limits of at least 50000,
    # - placed at least one completed order,
    # - and have at least 20000 in completed-order value.
    print_query_result(
        connection,
        """
        SELECT
            c.customer_id,
            c.customer_name,
            c.city,
            c.credit_limit,
            COUNT(o.order_id) AS completed_orders,
            SUM(o.amount) AS completed_order_value
        FROM customers AS c
        INNER JOIN orders AS o
            ON c.customer_id = o.customer_id
        WHERE c.country = 'India'
          AND c.status = 'Active'
          AND c.credit_limit >= 50000
          AND o.status = 'Completed'
        GROUP BY
            c.customer_id,
            c.customer_name,
            c.city,
            c.credit_limit
        HAVING SUM(o.amount) >= 20000
        ORDER BY completed_order_value DESC;
        """,
        title="Customer qualification using WHERE and HAVING"
    )


# =============================================================================
# SECTION 56: DEBUGGING FILTERS STEP BY STEP
# =============================================================================

def demonstrate_filter_debugging(connection):
    print_section("54. DEBUGGING A COMPLEX WHERE CLAUSE")

    # Complex filters are easier to debug by adding conditions incrementally.
    queries = [
        (
            "Step 1: all active employees",
            """
            SELECT employee_name, salary, age, department_id
            FROM employees
            WHERE employment_status = 'Active';
            """
        ),
        (
            "Step 2: add salary condition",
            """
            SELECT employee_name, salary, age, department_id
            FROM employees
            WHERE employment_status = 'Active'
              AND salary >= 90000;
            """
        ),
        (
            "Step 3: add age condition",
            """
            SELECT employee_name, salary, age, department_id
            FROM employees
            WHERE employment_status = 'Active'
              AND salary >= 90000
              AND age < 40;
            """
        ),
        (
            "Step 4: add grouped department condition",
            """
            SELECT employee_name, salary, age, department_id
            FROM employees
            WHERE employment_status = 'Active'
              AND salary >= 90000
              AND age < 40
              AND department_id IN (1, 2);
            """
        ),
    ]

    for title, sql in queries:
        print_query_result(connection, sql, title=title)


# =============================================================================
# SECTION 57: PERFORMANCE TRADE-OFFS
# =============================================================================

def demonstrate_performance_tradeoffs(connection):
    print_section("55. PERFORMANCE TRADE-OFFS")

    # Filtering on an indexed column can be efficient.
    print_query_result(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT *
        FROM employees
        WHERE salary >= 100000;
        """,
        title="Indexed numeric filter"
    )

    # OR conditions may have different optimization strategies depending on
    # the database engine, available indexes, statistics, and selectivity.
    print_query_result(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT *
        FROM employees
        WHERE department_id = 1
           OR department_id = 2;
        """,
        title="OR filtering"
    )

    # LIKE with a leading wildcard often prevents a simple B-tree index from
    # efficiently seeking to a starting position.
    print_query_result(
        connection,
        """
        EXPLAIN QUERY PLAN
        SELECT *
        FROM employees
        WHERE employee_name LIKE '%a%';
        """,
        title="LIKE with a leading wildcard"
    )


# =============================================================================
# SECTION 58: TRANSACTIONAL DATA SAFETY
# =============================================================================

def demonstrate_read_only_nature(connection):
    print_section("56. WHERE DOES NOT AUTOMATICALLY MODIFY DATA")

    # SELECT ... WHERE is read-only. UPDATE and DELETE also use WHERE, but they
    # can modify or remove rows. This distinction is critical in production.
    print_query_result(
        connection,
        """
        SELECT employee_id, employee_name, salary
        FROM employees
        WHERE employee_id = 6;
        """,
        title="Inspect a row before a hypothetical modification"
    )

    print(
        "\nImportant production rule: always inspect the WHERE condition with "
        "SELECT before executing a potentially destructive UPDATE or DELETE."
    )


# =============================================================================
# SECTION 59: SAFE UPDATE PREVIEW
# =============================================================================

def demonstrate_safe_update_preview(connection):
    print_section("57. FILTERING FOR UPDATE SAFETY")

    # We demonstrate the idea without changing the original employee data.
    candidate_sql = """
        SELECT employee_id, employee_name, salary
        FROM employees
        WHERE department_id = 1
          AND employment_status = 'Active'
          AND salary < 100000;
    """

    candidates = print_query_result(
        connection,
        candidate_sql,
        title="Rows that would be candidates for an UPDATE"
    )

    print(f"Candidate row count: {len(candidates)}")
    print(
        "A production UPDATE should use the same carefully verified WHERE "
        "condition and an appropriate transaction."
    )


# =============================================================================
# SECTION 60: FILTERING CONCEPT CHECKS
# =============================================================================

def run_concept_checks(connection):
    print_section("58. CONCEPT CHECKS")

    checks = {
        "WHERE filters rows": """
            SELECT COUNT(*) AS count
            FROM employees
            WHERE salary > 100000;
        """,
        "NULL requires IS NULL": """
            SELECT COUNT(*) AS count
            FROM employees
            WHERE city IS NULL;
        """,
        "BETWEEN is inclusive": """
            SELECT COUNT(*) AS count
            FROM employees
            WHERE age BETWEEN 30 AND 35;
        """,
        "IN matches a set of values": """
            SELECT COUNT(*) AS count
            FROM employees
            WHERE department_id IN (1, 2);
        """,
    }

    for concept, sql in checks.items():
        count = connection.execute(sql).fetchone()["count"]
        print(f"{concept}: {count} matching rows")


# =============================================================================
# SECTION 61: COMPLETE PRACTICAL REPORT
# =============================================================================

def demonstrate_complete_report(connection):
    print_section("59. COMPLETE PRACTICAL REPORT QUERY")

    # This query combines:
    # - JOIN
    # - WHERE
    # - IN
    # - NULL-safe filtering
    # - GROUP BY
    # - HAVING
    # - aggregate functions
    # - ORDER BY
    #
    # Requirement:
    # Show active customers from selected countries whose completed spending
    # is at least 20000, with a known credit limit of at least 50000.
    print_query_result(
        connection,
        """
        SELECT
            c.customer_name,
            c.country,
            c.credit_limit,
            COUNT(o.order_id) AS completed_orders,
            SUM(o.amount) AS total_completed_spend,
            AVG(o.amount) AS average_completed_order
        FROM customers AS c
        INNER JOIN orders AS o
            ON c.customer_id = o.customer_id
        WHERE c.status = 'Active'
          AND c.country IN ('India', 'USA', 'UK')
          AND c.credit_limit IS NOT NULL
          AND c.credit_limit >= 50000
          AND o.status = 'Completed'
        GROUP BY
            c.customer_id,
            c.customer_name,
            c.country,
            c.credit_limit
        HAVING SUM(o.amount) >= 20000
        ORDER BY total_completed_spend DESC;
        """,
        title="Integrated filtering and reporting example"
    )


# =============================================================================
# SECTION 62: MAIN PROGRAM
# =============================================================================

def main():
    connection = create_database()

    try:
        demonstrate_basic_select(connection)
        demonstrate_where(connection)
        demonstrate_comparison_operators(connection)
        demonstrate_and(connection)
        demonstrate_or(connection)
        demonstrate_not(connection)
        demonstrate_precedence(connection)
        demonstrate_in(connection)
        demonstrate_between(connection)
        demonstrate_like(connection)
        demonstrate_null(connection)
        demonstrate_three_valued_logic(connection)
        demonstrate_dates(connection)
        demonstrate_numeric_expressions(connection)
        demonstrate_complex_conditions(connection)
        demonstrate_case(connection)
        demonstrate_parameterized_filtering(connection)
        demonstrate_sql_injection_concept(connection)
        demonstrate_dynamic_in(connection)
        demonstrate_exists(connection)
        demonstrate_subqueries(connection)
        demonstrate_cte_filtering(connection)
        demonstrate_join_filtering(connection)
        demonstrate_having(connection)
        demonstrate_aggregate_filter(connection)
        demonstrate_customer_business_filters(connection)
        demonstrate_order_business_filters(connection)
        demonstrate_product_filters(connection)
        demonstrate_null_safe_business_rules(connection)
        demonstrate_boolean_style_filtering(connection)
        demonstrate_functions_in_where(connection)
        demonstrate_date_functions(connection)
        demonstrate_equivalent_conditions(connection)
        demonstrate_edge_cases(connection)
        demonstrate_set_logic(connection)
        demonstrate_query_plan(connection)
        demonstrate_sargability(connection)
        demonstrate_multi_table_business_filter(connection)
        demonstrate_grouped_business_rules(connection)
        demonstrate_subquery_set_filters(connection)
        demonstrate_assertions(connection)
        demonstrate_mini_challenges(connection)
        demonstrate_common_mistakes(connection)
        demonstrate_sql_clause_order(connection)
        demonstrate_limit(connection)
        demonstrate_distinct(connection)
        demonstrate_null_sorting(connection)
        demonstrate_window_function_filtering(connection)
        demonstrate_conditional_aggregation(connection)
        demonstrate_range_boundaries(connection)
        demonstrate_text_comparison_considerations(connection)
        demonstrate_data_type_considerations(connection)
        demonstrate_real_world_analytical_filter(connection)
        demonstrate_filter_debugging(connection)
        demonstrate_performance_tradeoffs(connection)
        demonstrate_read_only_nature(connection)
        demonstrate_safe_update_preview(connection)
        run_concept_checks(connection)
        demonstrate_complete_report(connection)

        print_section("END OF SQL FILTERING STUDY SCRIPT")
        print("All examples executed successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
