"""
DATABASE FUNDAMENTALS
=====================

A detailed, executable study script covering database fundamentals from
basic concepts to advanced database engineering principles.

This script uses Python's built-in sqlite3 module so that the examples
can be executed without installing an external database server.

The purpose of this file is educational. Each section explains a
database concept and, where practical, demonstrates it using SQLite.

Topics covered include:

    1. What a database is
    2. DBMS and RDBMS
    3. Relational database concepts
    4. Tables, rows, columns and records
    5. Schemas
    6. SQL
    7. SQL command categories
    8. Creating databases and tables
    9. Data types
    10. Primary keys
    11. Foreign keys
    12. Candidate keys
    13. Alternate keys
    14. Composite keys
    15. Natural and surrogate keys
    16. Constraints
    17. INSERT
    18. SELECT
    19. UPDATE
    20. DELETE
    21. WHERE
    22. ORDER BY
    23. LIMIT
    24. DISTINCT
    25. NULL
    26. Three-valued logic
    27. Aggregate functions
    28. GROUP BY
    29. HAVING
    30. JOINs
    31. Subqueries
    32. CTEs
    33. Recursive CTEs
    34. Set operations
    35. CASE expressions
    36. Views
    37. Indexes
    38. Query optimization
    39. EXPLAIN QUERY PLAN
    40. Transactions
    41. ACID
    42. COMMIT
    43. ROLLBACK
    44. SAVEPOINT
    45. Isolation
    46. Locks
    47. Deadlocks
    48. Normalization
    49. Denormalization
    50. Referential integrity
    51. Cascading actions
    52. Database anomalies
    53. Entity relationships
    54. One-to-one relationships
    55. One-to-many relationships
    56. Many-to-many relationships
    57. Junction tables
    58. Window functions
    59. UPSERT
    60. Triggers
    61. Auditing
    62. JSON and semi-structured data
    63. OLTP
    64. OLAP
    65. Fact and dimension tables
    66. ETL and ELT
    67. Replication
    68. Partitioning
    69. Sharding
    70. Connection pooling
    71. ORM concepts
    72. N+1 query problem
    73. Database migrations
    74. SQL injection
    75. Parameterized queries
    76. Database security
    77. Backup and recovery
    78. WAL and transaction logs
    79. CAP theorem
    80. Relational vs NoSQL databases
    81. Distributed databases
    82. Cardinality
    83. Selectivity
    84. Covering indexes
    85. Query design
    86. Data modeling
    87. Historical data
    88. Derived data
    89. Idempotency
    90. Database testing
    91. Observability
    92. Production database architecture
    93. Practical e-commerce database
    94. Database terminology

SQLite is used for executable demonstrations. Some concepts such as
stored procedures, users/roles, replication and sharding are discussed
conceptually because SQLite is an embedded database and does not provide
the same server-side capabilities as PostgreSQL, MySQL, SQL Server or
Oracle.
"""

import sqlite3
from datetime import datetime


# ============================================================
# 1. HELPER FUNCTIONS
# ============================================================

def title(text):
    print("\n")
    print("=" * 78)
    print(text.upper())
    print("=" * 78)


def explain(text):
    print(f"\n{text}\n")


def show_rows(cursor, rows=None):
    if rows is None:
        rows = cursor.fetchall()

    if not rows:
        print("(no rows)")
        return

    columns = [description[0] for description in cursor.description]

    print(" | ".join(columns))
    print("-" * 78)

    for row in rows:
        print(" | ".join(str(value) for value in row))


def execute_and_show(connection, sql, parameters=()):
    cursor = connection.execute(sql, parameters)

    if cursor.description:
        show_rows(cursor)

    return cursor


# ============================================================
# 2. WHAT IS A DATABASE?
# ============================================================

title("1. What is a Database")

explain("""
A database is an organized collection of data that can be stored,
retrieved, modified and managed efficiently.

The important idea is not merely storage.

A database provides a structured mechanism for:

    - storing data
    - retrieving data
    - changing data
    - enforcing rules
    - maintaining relationships
    - controlling access
    - handling concurrent operations
    - recovering from failures
    - maintaining consistency

For example, an e-commerce system may need to store:

    customers
    products
    orders
    payments
    shipments
    inventory

A simple file can store this information, but a database provides
mechanisms that make the data reliable and manageable when many
operations and users are involved.
""")


# ============================================================
# 3. DBMS AND RDBMS
# ============================================================

title("2. DBMS and RDBMS")

explain("""
DBMS stands for Database Management System.

A DBMS is software responsible for managing databases.

Examples include:

    SQLite
    PostgreSQL
    MySQL
    Microsoft SQL Server
    Oracle Database
    MongoDB

RDBMS means Relational Database Management System.

A relational database organizes information primarily into tables
and represents relationships between tables using keys.

Examples of relational databases include:

    PostgreSQL
    MySQL
    Oracle
    SQL Server
    SQLite

SQLite is relational, although its architecture is very different
from a traditional client-server database.
""")


# ============================================================
# 4. RELATIONAL MODEL
# ============================================================

title("3. Relational Database Model")

explain("""
The relational model represents data using relations.

In practical SQL terminology:

    relation -> table
    tuple    -> row
    attribute -> column

Suppose we have:

customers
------------------------------------------------
id | name | email
------------------------------------------------
1  | Ravi | ravi@example.com
2  | Neha | neha@example.com

The table represents a relation.

Each row represents one entity occurrence.

Each column represents an attribute of that entity.
""")


# ============================================================
# 5. CREATE DATABASE
# ============================================================

title("4. Creating a Database")

explain("""
SQLite can create a database directly in memory.

The following connection creates a temporary database that exists
only for the lifetime of this Python process.
""")

connection = sqlite3.connect(":memory:")

# SQLite does not enforce foreign keys unless enabled.
connection.execute("PRAGMA foreign_keys = ON")


# ============================================================
# 6. TABLES, ROWS AND COLUMNS
# ============================================================

title("5. Tables, Rows and Columns")

explain("""
A table describes a particular type of data.

For example:

    customers
    products
    orders

A row represents one record.

A column represents one property of the record.

The table definition establishes structural rules for the data.
""")

connection.execute("""
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    city TEXT,
    created_at TEXT NOT NULL
)
""")

connection.execute("""
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0
)
""")


# ============================================================
# 7. DATA TYPES
# ============================================================

title("6. Data Types")

explain("""
A database uses data types to describe what kind of value a column
can contain.

Common SQL data types include:

    INTEGER
    DECIMAL
    NUMERIC
    REAL
    CHAR
    VARCHAR
    TEXT
    DATE
    TIMESTAMP
    BOOLEAN
    BINARY

Different database systems implement types differently.

SQLite uses a flexible type system based around storage classes:

    NULL
    INTEGER
    REAL
    TEXT
    BLOB

This is one reason SQLite examples should not automatically be
treated as identical to PostgreSQL or MySQL behavior.
""")


# ============================================================
# 8. PRIMARY KEY
# ============================================================

title("7. Primary Key")

explain("""
A primary key uniquely identifies a row.

A good primary key should provide unique identity.

For customers:

    customer_id

For products:

    product_id

A primary key cannot contain duplicate values.

A primary key normally should not be NULL.

In this database:

    customer_id INTEGER PRIMARY KEY

is the primary key of customers.
""")


# ============================================================
# 9. INSERT DATA
# ============================================================

title("8. INSERT")

explain("""
INSERT adds records to a table.

Always specify the target columns explicitly when writing application
SQL. This makes the statement easier to understand and safer when
the table structure changes.
""")

customers = [
    (1, "Ravi", "ravi@example.com", "Lucknow", "2026-01-10"),
    (2, "Neha", "neha@example.com", "Delhi", "2026-01-11"),
    (3, "Aman", "aman@example.com", "Mumbai", "2026-01-12"),
    (4, "Priya", "priya@example.com", "Pune", "2026-01-13"),
]

connection.executemany("""
INSERT INTO customers
(customer_id, name, email, city, created_at)
VALUES (?, ?, ?, ?, ?)
""", customers)

products = [
    (1, "Laptop", "Electronics", 75000, 10),
    (2, "Mouse", "Electronics", 1200, 50),
    (3, "Keyboard", "Electronics", 2500, 25),
    (4, "Office Chair", "Furniture", 12000, 15),
    (5, "Desk", "Furniture", 18000, 8),
]

connection.executemany("""
INSERT INTO products
(product_id, product_name, category, price, stock_quantity)
VALUES (?, ?, ?, ?, ?)
""", products)

connection.commit()

execute_and_show(
    connection,
    "SELECT * FROM customers"
)


# ============================================================
# 10. PARAMETERIZED QUERIES
# ============================================================

title("9. Parameterized Queries")

explain("""
Parameterized queries separate SQL instructions from data values.

This is important for both correctness and security.

Avoid constructing SQL by concatenating user input.

Unsafe idea:

    SELECT * FROM users WHERE name = '""" + "user_input" + """'

Safe approach:

    SELECT * FROM users WHERE name = ?

The parameter is supplied separately.
""")

name_to_find = "Ravi"

execute_and_show(
    connection,
    "SELECT * FROM customers WHERE name = ?",
    (name_to_find,)
)


# ============================================================
# 11. SELECT
# ============================================================

title("10. SELECT")

explain("""
SELECT retrieves data.

The simplest form is:

    SELECT column1, column2
    FROM table;

Using explicit columns is usually preferable to SELECT * in
production application queries because it makes the required data
clear and avoids retrieving unnecessary columns.
""")

execute_and_show(
    connection,
    """
    SELECT customer_id, name, email
    FROM customers
    """
)


# ============================================================
# 12. WHERE
# ============================================================

title("11. WHERE")

explain("""
WHERE filters rows.

The condition is evaluated for each candidate row.

Examples include:

    price > 1000
    city = 'Delhi'
    stock_quantity > 0

Multiple conditions can be combined using:

    AND
    OR
    NOT
""")

execute_and_show(
    connection,
    """
    SELECT product_name, price
    FROM products
    WHERE price > ?
    """,
    (5000,)
)


# ============================================================
# 13. COMPARISON OPERATORS
# ============================================================

title("12. Comparison Operators")

explain("""
Common comparison operators are:

    =
    <>
    !=
    >
    <
    >=
    <=

Additional operators include:

    BETWEEN
    IN
    LIKE
    IS NULL
    IS NOT NULL
""")

execute_and_show(
    connection,
    """
    SELECT product_name, price
    FROM products
    WHERE price BETWEEN ? AND ?
    """,
    (1000, 20000)
)


# ============================================================
# 14. DISTINCT
# ============================================================

title("13. DISTINCT")

explain("""
DISTINCT removes duplicate result values.

It is useful when asking for unique values rather than individual rows.
""")

execute_and_show(
    connection,
    """
    SELECT DISTINCT category
    FROM products
    """
)


# ============================================================
# 15. ORDER BY
# ============================================================

title("14. ORDER BY")

explain("""
ORDER BY controls the order of the result.

ASC means ascending.

DESC means descending.
""")

execute_and_show(
    connection,
    """
    SELECT product_name, price
    FROM products
    ORDER BY price DESC
    """
)


# ============================================================
# 16. LIMIT
# ============================================================

title("15. LIMIT")

explain("""
LIMIT restricts the number of rows returned.

It is often used for pagination or top-N queries.

LIMIT by itself does not guarantee which rows are returned unless
the query also specifies an appropriate ORDER BY.
""")

execute_and_show(
    connection,
    """
    SELECT product_name, price
    FROM products
    ORDER BY price DESC
    LIMIT 3
    """
)


# ============================================================
# 17. UPDATE
# ============================================================

title("16. UPDATE")

explain("""
UPDATE modifies existing rows.

The WHERE condition is critical.

Without WHERE, every row may be updated.
""")

connection.execute("""
UPDATE products
SET stock_quantity = stock_quantity + 5
WHERE product_id = ?
""", (1,))

connection.commit()

execute_and_show(
    connection,
    "SELECT * FROM products WHERE product_id = 1"
)


# ============================================================
# 18. DELETE
# ============================================================

title("17. DELETE")

explain("""
DELETE removes rows.

As with UPDATE, an accidental missing WHERE clause can affect every
row in the table.

Production applications often use transactions around important
modification operations.
""")

connection.execute("""
DELETE FROM customers
WHERE customer_id = ?
""", (4,))

connection.commit()

execute_and_show(
    connection,
    "SELECT * FROM customers"
)


# ============================================================
# 19. NULL
# ============================================================

title("18. NULL")

explain("""
NULL represents the absence of a value.

NULL is not the same as:

    0
    ''
    FALSE
    'NULL'

NULL represents unknown, missing or inapplicable information,
depending on the context.

This distinction is important because SQL uses three-valued logic:

    TRUE
    FALSE
    UNKNOWN

A comparison such as:

    city = NULL

does not correctly test for NULL.

Use:

    city IS NULL

or:

    city IS NOT NULL
""")

connection.execute("""
CREATE TABLE null_demo (
    id INTEGER PRIMARY KEY,
    value TEXT
)
""")

connection.executemany(
    "INSERT INTO null_demo (id, value) VALUES (?, ?)",
    [
        (1, "hello"),
        (2, None),
        (3, "world"),
    ]
)

execute_and_show(
    connection,
    """
    SELECT *
    FROM null_demo
    WHERE value IS NULL
    """
)


# ============================================================
# 20. CONSTRAINTS
# ============================================================

title("19. Constraints")

explain("""
Constraints are database-level rules that protect data integrity.

Important constraints include:

    PRIMARY KEY
    FOREIGN KEY
    UNIQUE
    NOT NULL
    CHECK
    DEFAULT

Constraints are important because application code alone is not a
complete integrity mechanism.

A database should protect critical invariants itself.
""")

connection.execute("""
CREATE TABLE constrained_products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL CHECK(price >= 0),
    sku TEXT UNIQUE,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0)
)
""")


# ============================================================
# 21. FOREIGN KEYS
# ============================================================

title("20. Foreign Keys")

explain("""
A foreign key establishes a relationship between tables.

Suppose:

    customers.customer_id

is referenced by:

    orders.customer_id

The foreign key ensures that an order cannot refer to a customer
that does not exist, unless the relationship is intentionally nullable
and NULL is used.
""")

connection.execute("""
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL,
    total_amount REAL NOT NULL,
    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
)
""")

connection.execute("""
CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    FOREIGN KEY (order_id)
        REFERENCES orders(order_id),
    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
)
""")


# ============================================================
# 22. INSERT ORDERS
# ============================================================

title("21. Creating Related Data")

orders = [
    (1, 1, "2026-02-01", "PAID", 76200),
    (2, 2, "2026-02-02", "PAID", 13200),
    (3, 3, "2026-02-03", "PENDING", 18000),
]

connection.executemany("""
INSERT INTO orders
(order_id, customer_id, order_date, status, total_amount)
VALUES (?, ?, ?, ?, ?)
""", orders)

order_items = [
    (1, 1, 1, 1, 75000),
    (2, 1, 2, 1, 1200),
    (3, 2, 4, 1, 12000),
    (4, 2, 2, 1, 1200),
    (5, 3, 4, 1, 12000),
    (6, 3, 2, 5, 1200),
]

connection.executemany("""
INSERT INTO order_items
(order_item_id, order_id, product_id, quantity, unit_price)
VALUES (?, ?, ?, ?, ?)
""", order_items)

connection.commit()


# ============================================================
# 23. RELATIONSHIPS
# ============================================================

title("22. Database Relationships")

explain("""
A relationship describes how entities relate to one another.

One-to-one:

    person -> passport

One-to-many:

    customer -> orders

Many-to-many:

    students <-> courses

Many-to-many relationships require an associative or junction table.

In this database:

    orders
    order_items
    products

allow one order to contain many products and one product to appear
in many orders.

order_items acts as the junction table.
""")


# ============================================================
# 24. JOIN
# ============================================================

title("23. INNER JOIN")

explain("""
A JOIN combines rows from multiple tables based on a relationship.

INNER JOIN returns rows where matching records exist in both sides.
""")

execute_and_show(
    connection,
    """
    SELECT
        o.order_id,
        c.name AS customer_name,
        o.status,
        o.total_amount
    FROM orders AS o
    INNER JOIN customers AS c
        ON o.customer_id = c.customer_id
    """
)


# ============================================================
# 25. LEFT JOIN
# ============================================================

title("24. LEFT JOIN")

explain("""
LEFT JOIN returns all rows from the left table.

If a matching row does not exist in the right table, the right-side
columns become NULL.

LEFT JOIN is useful for questions such as:

    Which customers have never placed an order?

The absence of a matching record becomes visible as NULL.
""")

execute_and_show(
    connection,
    """
    SELECT
        c.customer_id,
        c.name,
        o.order_id
    FROM customers AS c
    LEFT JOIN orders AS o
        ON c.customer_id = o.customer_id
    """
)


# ============================================================
# 26. JOIN CARDINALITY
# ============================================================

title("25. Join Cardinality")

explain("""
Join cardinality describes how many rows can match another row.

One-to-one:

    1 -> 1

One-to-many:

    1 -> many

Many-to-many:

    many -> many

A join can increase the number of result rows.

For example, one order with five order items produces five rows when
orders are joined to order_items.

This is one of the most important causes of accidental duplication
in analytical SQL.
""")

execute_and_show(
    connection,
    """
    SELECT
        o.order_id,
        p.product_name,
        oi.quantity
    FROM orders AS o
    JOIN order_items AS oi
        ON o.order_id = oi.order_id
    JOIN products AS p
        ON oi.product_id = p.product_id
    ORDER BY o.order_id
    """
)


# ============================================================
# 27. AGGREGATE FUNCTIONS
# ============================================================

title("26. Aggregate Functions")

explain("""
Aggregate functions operate across multiple rows.

Common aggregate functions:

    COUNT()
    SUM()
    AVG()
    MIN()
    MAX()

They are used for reporting and analytical calculations.
""")

execute_and_show(
    connection,
    """
    SELECT
        COUNT(*) AS product_count,
        SUM(stock_quantity) AS total_stock,
        AVG(price) AS average_price,
        MIN(price) AS minimum_price,
        MAX(price) AS maximum_price
    FROM products
    """
)


# ============================================================
# 28. GROUP BY
# ============================================================

title("27. GROUP BY")

explain("""
GROUP BY divides rows into groups and calculates aggregates for each
group.

For example:

    total sales by customer
    average price by category
    number of orders by status
""")

execute_and_show(
    connection,
    """
    SELECT
        category,
        COUNT(*) AS product_count,
        AVG(price) AS average_price
    FROM products
    GROUP BY category
    """
)


# ============================================================
# 29. HAVING
# ============================================================

title("28. HAVING")

explain("""
WHERE filters individual rows before grouping.

HAVING filters groups after aggregation.

Example:

    WHERE price > 1000

filters products.

    HAVING AVG(price) > 10000

filters categories after their average price has been calculated.
""")

execute_and_show(
    connection,
    """
    SELECT
        category,
        AVG(price) AS average_price
    FROM products
    GROUP BY category
    HAVING AVG(price) > 5000
    """
)


# ============================================================
# 30. CASE
# ============================================================

title("29. CASE Expressions")

explain("""
CASE creates conditional expressions inside SQL.

It is similar to if/elif/else logic in programming.

It can be used for:

    categorization
    conditional calculations
    labels
    reporting logic
""")

execute_and_show(
    connection,
    """
    SELECT
        product_name,
        price,
        CASE
            WHEN price < 2000 THEN 'LOW'
            WHEN price < 10000 THEN 'MEDIUM'
            ELSE 'HIGH'
        END AS price_band
    FROM products
    ORDER BY price
    """
)


# ============================================================
# 31. SUBQUERIES
# ============================================================

title("30. Subqueries")

explain("""
A subquery is a query nested inside another query.

Subqueries can be used in:

    WHERE
    FROM
    SELECT
    HAVING

They allow one query to depend on the result of another query.
""")

execute_and_show(
    connection,
    """
    SELECT product_name, price
    FROM products
    WHERE price > (
        SELECT AVG(price)
        FROM products
    )
    """
)


# ============================================================
# 32. EXISTS
# ============================================================

title("31. EXISTS")

explain("""
EXISTS checks whether a subquery returns at least one row.

It is especially useful when asking whether a related record exists.

For example:

    Which customers have at least one order?
""")

execute_and_show(
    connection,
    """
    SELECT
        c.customer_id,
        c.name
    FROM customers AS c
    WHERE EXISTS (
        SELECT 1
        FROM orders AS o
        WHERE o.customer_id = c.customer_id
    )
    """
)


# ============================================================
# 33. COMMON TABLE EXPRESSIONS
# ============================================================

title("32. Common Table Expressions")

explain("""
A Common Table Expression, or CTE, is defined using WITH.

CTEs make complicated SQL easier to structure.

Instead of placing everything inside one deeply nested query,
intermediate logical results can be named.
""")

execute_and_show(
    connection,
    """
    WITH customer_sales AS (
        SELECT
            customer_id,
            SUM(total_amount) AS total_sales
        FROM orders
        GROUP BY customer_id
    )
    SELECT
        c.name,
        cs.total_sales
    FROM customer_sales AS cs
    JOIN customers AS c
        ON c.customer_id = cs.customer_id
    ORDER BY cs.total_sales DESC
    """
)


# ============================================================
# 34. RECURSIVE CTE
# ============================================================

title("33. Recursive CTE")

explain("""
Recursive CTEs are useful for hierarchical data.

Examples:

    employee -> manager
    folder -> subfolder
    category -> subcategory
    organization -> department

The recursive query consists of:

    an anchor query

and

    a recursive query

SQLite supports recursive CTEs.
""")

execute_and_show(
    connection,
    """
    WITH RECURSIVE numbers(n) AS (
        SELECT 1

        UNION ALL

        SELECT n + 1
        FROM numbers
        WHERE n < 5
    )
    SELECT n
    FROM numbers
    """
)


# ============================================================
# 35. SET OPERATIONS
# ============================================================

title("34. Set Operations")

explain("""
SQL supports operations that combine result sets.

UNION:

    combines results and removes duplicates.

UNION ALL:

    combines results without removing duplicates.

INTERSECT:

    returns rows present in both result sets.

EXCEPT:

    returns rows present in the first result but not the second.

UNION ALL is generally cheaper than UNION because duplicate removal
requires additional work.
""")

execute_and_show(
    connection,
    """
    SELECT city
    FROM customers
    WHERE city IN ('Lucknow', 'Delhi')

    UNION

    SELECT city
    FROM customers
    WHERE city IN ('Delhi', 'Mumbai')
    """
)


# ============================================================
# 36. VIEWS
# ============================================================

title("35. Views")

explain("""
A view is a stored SQL query that behaves like a virtual table.

Views can:

    simplify repeated queries
    provide abstraction
    restrict exposed columns
    centralize reporting logic

A normal view does not necessarily store the result itself.
""")

connection.execute("""
CREATE VIEW customer_order_report AS
SELECT
    c.customer_id,
    c.name,
    o.order_id,
    o.order_date,
    o.status,
    o.total_amount
FROM customers AS c
JOIN orders AS o
    ON c.customer_id = o.customer_id
""")

execute_and_show(
    connection,
    "SELECT * FROM customer_order_report"
)


# ============================================================
# 37. NORMALIZATION
# ============================================================

title("36. Database Normalization")

explain("""
Normalization is a design process used to reduce unnecessary
duplication and dependency problems.

Important normal forms include:

    First Normal Form
    Second Normal Form
    Third Normal Form
    Boyce-Codd Normal Form

First Normal Form generally requires atomic values and no repeating
groups.

Second Normal Form requires 1NF and removal of partial dependency
on part of a composite key.

Third Normal Form requires 2NF and removal of inappropriate
transitive dependencies.

Normalization is primarily about logical data organization.
It is not simply a rule that says every table must be as small as
possible.
""")


# ============================================================
# 38. DATABASE ANOMALIES
# ============================================================

title("37. Database Anomalies")

explain("""
Poorly designed tables can create anomalies.

INSERT anomaly:

    It becomes difficult to insert one fact without another unrelated
    fact.

UPDATE anomaly:

    The same fact appears in many rows and must be changed repeatedly.

DELETE anomaly:

    Deleting one fact accidentally removes another useful fact.

Normalization helps reduce these problems.
""")


# ============================================================
# 39. COMPOSITE KEYS
# ============================================================

title("38. Composite Keys")

explain("""
A composite key consists of multiple columns.

For example, a student can enroll in a course.

student_id + course_id

can uniquely identify an enrollment.

The combination is unique even if each individual value appears many
times.
""")

connection.execute("""
CREATE TABLE course_enrollments (
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    enrolled_at TEXT NOT NULL,
    PRIMARY KEY (student_id, course_id)
)
""")


# ============================================================
# 40. NATURAL VS SURROGATE KEYS
# ============================================================

title("39. Natural and Surrogate Keys")

explain("""
A natural key comes from real-world business data.

Examples:

    email
    ISBN
    government-issued identifier
    product SKU

A surrogate key is generated specifically for database identity.

Examples:

    customer_id
    order_id

Surrogate keys are often convenient because business attributes
can change independently of internal identity.

A natural key may still need a UNIQUE constraint even when a
surrogate primary key is used.
""")


# ============================================================
# 41. INDEXES
# ============================================================

title("40. Indexes")

explain("""
An index is a data structure that helps the database locate rows
more efficiently.

Without a useful index, the database may need to scan many or all
rows.

An index can improve reads but introduces costs:

    additional storage
    slower writes
    maintenance overhead

Indexes should support actual access patterns.
""")

connection.execute("""
CREATE INDEX idx_products_category
ON products(category)
""")

connection.execute("""
CREATE INDEX idx_orders_customer
ON orders(customer_id)
""")


# ============================================================
# 42. INDEXED SEARCH
# ============================================================

title("41. Index Usage")

execute_and_show(
    connection,
    """
    SELECT *
    FROM products
    WHERE category = ?
    """,
    ("Electronics",)
)


# ============================================================
# 43. EXPLAIN QUERY PLAN
# ============================================================

title("42. Query Execution Plans")

explain("""
A database optimizer decides how to execute SQL.

EXPLAIN QUERY PLAN provides information about the chosen strategy
in SQLite.

Possible operations include:

    table scan
    index search
    temporary sorting
    nested-loop joins

The exact syntax and output differ across database engines.
""")

execute_and_show(
    connection,
    """
    EXPLAIN QUERY PLAN
    SELECT *
    FROM products
    WHERE category = 'Electronics'
    """
)


# ============================================================
# 44. SELECTIVITY
# ============================================================

title("43. Selectivity")

explain("""
Selectivity describes how effectively a condition narrows the result.

A highly selective condition returns relatively few rows.

For example:

    customer_id = 12345

is often highly selective.

A condition such as:

    gender = 'M'

may be less selective in a large dataset.

Index usefulness depends partly on selectivity and the database
optimizer's cost model.
""")


# ============================================================
# 45. CARDINALITY
# ============================================================

title("44. Cardinality")

explain("""
Cardinality can refer to the number of distinct values in a column
or to the relationship between entities.

Examples:

    primary key -> high uniqueness
    status      -> low number of distinct values

In relationship modeling:

    one-to-one
    one-to-many
    many-to-many

are cardinality patterns.
""")


# ============================================================
# 46. COVERING INDEX
# ============================================================

title("45. Covering Index")

explain("""
A covering index contains enough information for a query to be
answered directly from the index without retrieving the table row.

For example, if a query needs:

    category
    price

an index containing both may allow the database to satisfy the query
more efficiently.

Whether this happens depends on the database engine and execution plan.
""")


# ============================================================
# 47. TRANSACTIONS
# ============================================================

title("46. Transactions")

explain("""
A transaction groups multiple database operations into one logical
unit.

Consider transferring money:

    subtract from account A
    add to account B

If the first operation succeeds and the second fails, the system
must not leave the database in an invalid state.

A transaction provides atomicity.
""")

connection.execute("""
CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY,
    owner TEXT NOT NULL,
    balance REAL NOT NULL CHECK(balance >= 0)
)
""")

connection.executemany(
    "INSERT INTO accounts (account_id, owner, balance) VALUES (?, ?, ?)",
    [
        (1, "Alice", 10000),
        (2, "Bob", 5000),
    ]
)

connection.commit()


# ============================================================
# 48. COMMIT AND ROLLBACK
# ============================================================

title("47. COMMIT and ROLLBACK")

explain("""
COMMIT permanently applies a successful transaction.

ROLLBACK reverses changes made since the transaction began.

The exact durability behavior depends on the database engine,
storage configuration and transaction settings.
""")

try:
    connection.execute("BEGIN")

    connection.execute("""
        UPDATE accounts
        SET balance = balance - 1000
        WHERE account_id = 1
    """)

    connection.execute("""
        UPDATE accounts
        SET balance = balance + 1000
        WHERE account_id = 2
    """)

    connection.commit()

except Exception:
    connection.rollback()

execute_and_show(
    connection,
    "SELECT * FROM accounts"
)


# ============================================================
# 49. ACID
# ============================================================

title("48. ACID")

explain("""
ACID describes four important transaction properties.

Atomicity:

    The transaction behaves as a unit.

Consistency:

    Valid database rules are maintained before and after the
    transaction.

Isolation:

    Concurrent transactions are controlled so that intermediate
    states do not cause unacceptable interference.

Durability:

    Once committed, data is intended to survive failures according
    to the database's durability guarantees.

ACID is not one specific implementation. Different databases provide
these guarantees using different storage and concurrency mechanisms.
""")


# ============================================================
# 50. SAVEPOINT
# ============================================================

title("49. SAVEPOINT")

explain("""
A SAVEPOINT creates a point inside a transaction to which the
transaction can partially roll back.

This is useful when a large transaction contains multiple logical
steps.
""")

connection.execute("BEGIN")

connection.execute("""
UPDATE accounts
SET balance = balance - 500
WHERE account_id = 1
""")

connection.execute("SAVEPOINT after_withdrawal")

connection.execute("""
UPDATE accounts
SET balance = balance + 500
WHERE account_id = 2
""")

connection.execute("ROLLBACK TO after_withdrawal")

connection.execute("RELEASE after_withdrawal")

connection.rollback()


# ============================================================
# 51. ISOLATION AND CONCURRENCY
# ============================================================

title("50. Isolation and Concurrency")

explain("""
Multiple users or processes may access a database at the same time.

Concurrency creates problems such as:

    dirty reads
    non-repeatable reads
    phantom reads
    lost updates

Database systems use locking, MVCC, snapshots and other techniques
to control concurrent access.

Isolation levels commonly discussed include:

    Read Uncommitted
    Read Committed
    Repeatable Read
    Serializable

The exact behavior differs by database engine.
""")


# ============================================================
# 52. LOCKING
# ============================================================

title("51. Locks")

explain("""
Locks coordinate concurrent access to shared database resources.

Conceptually, systems may use:

    shared/read locks
    exclusive/write locks

Lock granularity can vary:

    row
    page
    table
    database

Modern database engines may also use multi-version concurrency
control rather than relying solely on blocking locks.
""")


# ============================================================
# 53. DEADLOCKS
# ============================================================

title("52. Deadlocks")

explain("""
A deadlock occurs when transactions wait for one another indefinitely.

Example:

Transaction A:

    locks resource X
    waits for resource Y

Transaction B:

    locks resource Y
    waits for resource X

The database may detect the deadlock and abort one transaction.

Applications must be prepared to retry transactions where appropriate.
""")


# ============================================================
# 54. REFERENTIAL ACTIONS
# ============================================================

title("53. Referential Actions")

explain("""
Foreign keys can specify what should happen when a referenced row
changes or is deleted.

Common actions include:

    CASCADE
    SET NULL
    RESTRICT
    NO ACTION

For example:

    ON DELETE CASCADE

means deleting a parent row may automatically delete dependent rows.

Cascades should be designed carefully because one delete operation
can affect many records.
""")


# ============================================================
# 55. UPSERT
# ============================================================

title("54. UPSERT")

explain("""
UPSERT means:

    insert if the record does not exist
    otherwise update an existing record

SQLite supports INSERT ... ON CONFLICT.

UPSERT is useful for synchronization and idempotent operations.
""")

connection.execute("""
CREATE TABLE product_inventory (
    product_id INTEGER PRIMARY KEY,
    quantity INTEGER NOT NULL
)
""")

connection.execute("""
INSERT INTO product_inventory(product_id, quantity)
VALUES (?, ?)
ON CONFLICT(product_id)
DO UPDATE SET quantity = excluded.quantity
""", (1, 25))

connection.commit()

execute_and_show(
    connection,
    "SELECT * FROM product_inventory"
)


# ============================================================
# 56. WINDOW FUNCTIONS
# ============================================================

title("55. Window Functions")

explain("""
A window function performs a calculation across related rows while
keeping the individual rows visible.

This differs from GROUP BY.

GROUP BY reduces rows into groups.

A window function calculates over a group of rows without necessarily
collapsing them.

Common window functions include:

    ROW_NUMBER()
    RANK()
    DENSE_RANK()
    LAG()
    LEAD()
    SUM() OVER(...)
    AVG() OVER(...)
""")

execute_and_show(
    connection,
    """
    SELECT
        product_name,
        category,
        price,
        RANK() OVER (
            PARTITION BY category
            ORDER BY price DESC
        ) AS category_rank
    FROM products
    ORDER BY category, category_rank
    """
)


# ============================================================
# 57. LAG AND LEAD
# ============================================================

title("56. LAG and LEAD")

explain("""
LAG accesses a previous row.

LEAD accesses a following row.

They are useful for:

    time-series analysis
    comparing periods
    calculating changes
    detecting transitions
""")

execute_and_show(
    connection,
    """
    SELECT
        order_id,
        order_date,
        total_amount,
        LAG(total_amount) OVER (
            ORDER BY order_date
        ) AS previous_order_amount
    FROM orders
    ORDER BY order_date
    """
)


# ============================================================
# 58. TRIGGERS
# ============================================================

title("57. Triggers")

explain("""
A trigger automatically executes when a specified database event
occurs.

Typical events:

    INSERT
    UPDATE
    DELETE

Triggers can be used for:

    auditing
    maintaining derived data
    enforcing specialized rules

Triggers should be used carefully because they create behavior that
may not be visible from the application code invoking the statement.
""")

connection.execute("""
CREATE TABLE order_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")

connection.execute("""
CREATE TRIGGER audit_order_insert
AFTER INSERT ON orders
BEGIN
    INSERT INTO order_audit
    (order_id, action, created_at)
    VALUES
    (NEW.order_id, 'INSERT', datetime('now'));
END
""")


# ============================================================
# 59. TRIGGER DEMONSTRATION
# ============================================================

title("58. Trigger Demonstration")

connection.execute("""
INSERT INTO orders
(order_id, customer_id, order_date, status, total_amount)
VALUES
(4, 1, '2026-02-05', 'PAID', 2500)
""")

connection.commit()

execute_and_show(
    connection,
    "SELECT * FROM order_audit"
)


# ============================================================
# 60. AUDITING
# ============================================================

title("59. Auditing")

explain("""
Auditing records important changes to data.

An audit record may contain:

    who changed the record
    what changed
    when it changed
    previous value
    new value
    source or application

Audit tables can be implemented using triggers, application logic,
database features or specialized auditing systems.
""")


# ============================================================
# 61. SQL COMMAND CATEGORIES
# ============================================================

title("60. SQL Command Categories")

explain("""
SQL statements are often grouped into categories.

DDL - Data Definition Language

    CREATE
    ALTER
    DROP
    TRUNCATE

DML - Data Manipulation Language

    INSERT
    UPDATE
    DELETE

DQL - Data Query Language

    SELECT

DCL - Data Control Language

    GRANT
    REVOKE

TCL - Transaction Control Language

    COMMIT
    ROLLBACK
    SAVEPOINT

Exact classifications vary somewhat between educational sources.
""")


# ============================================================
# 62. SCHEMA
# ============================================================

title("61. Database Schema")

explain("""
A schema describes the logical structure of database objects.

It can include:

    tables
    columns
    data types
    constraints
    indexes
    views
    relationships
    functions
    triggers

In PostgreSQL, schemas are also explicit namespaces within a database.

SQLite has a different schema model.
""")


# ============================================================
# 63. ENTITY RELATIONSHIP MODEL
# ============================================================

title("62. Entity Relationship Modeling")

explain("""
Entity Relationship modeling is used to design a database before
implementation.

An entity represents something important to the business.

Examples:

    Customer
    Product
    Order
    Employee

Attributes describe entities.

Relationships describe how entities interact.

An ER model helps translate business requirements into database
structures.
""")


# ============================================================
# 64. ONE-TO-ONE
# ============================================================

title("63. One-to-One Relationship")

explain("""
A one-to-one relationship means each record in one table corresponds
to at most one record in another table.

Example:

    employee
    employee_profile

One implementation is to use the parent primary key as the child
primary key and foreign key.
""")


# ============================================================
# 65. ONE-TO-MANY
# ============================================================

title("64. One-to-Many Relationship")

explain("""
A one-to-many relationship means one parent can have many children.

Example:

    customer -> orders

The foreign key normally exists on the many side:

    orders.customer_id
""")


# ============================================================
# 66. MANY-TO-MANY
# ============================================================

title("65. Many-to-Many Relationship")

explain("""
A many-to-many relationship cannot normally be represented by placing
one foreign key in either table.

Instead, a junction table is introduced.

Example:

    students
    courses
    enrollments

The enrollments table can contain:

    student_id
    course_id
    enrolled_at
""")


# ============================================================
# 67. OLTP
# ============================================================

title("66. OLTP")

explain("""
OLTP stands for Online Transaction Processing.

OLTP systems handle operational transactions such as:

    placing orders
    updating inventory
    processing payments
    registering users
    booking tickets

OLTP workloads usually involve:

    many concurrent users
    relatively small transactions
    frequent INSERT/UPDATE operations
    strong consistency requirements
    low-latency queries
""")


# ============================================================
# 68. OLAP
# ============================================================

title("67. OLAP")

explain("""
OLAP stands for Online Analytical Processing.

OLAP systems support analysis such as:

    revenue by region
    sales trends
    customer segmentation
    monthly performance
    business intelligence

OLAP workloads often involve:

    large scans
    aggregations
    historical datasets
    complex analytical queries
""")


# ============================================================
# 69. FACT AND DIMENSION
# ============================================================

title("68. Fact and Dimension Tables")

explain("""
A common analytical design is the star schema.

Fact tables contain measurable business events.

Examples:

    sales
    transactions
    clicks
    shipments

Dimension tables provide descriptive context.

Examples:

    customer
    product
    date
    region

A sales fact may contain:

    date_id
    customer_id
    product_id
    quantity
    revenue
""")


# ============================================================
# 70. ETL AND ELT
# ============================================================

title("69. ETL and ELT")

explain("""
ETL means:

    Extract
    Transform
    Load

Data is extracted from sources, transformed and then loaded into
the destination.

ELT means:

    Extract
    Load
    Transform

Data is loaded first and transformations occur inside the target
data platform.

The distinction matters because modern analytical systems often
have substantial computational capacity for transformations.
""")


# ============================================================
# 71. DENORMALIZATION
# ============================================================

title("70. Denormalization")

explain("""
Denormalization intentionally introduces some redundancy to improve
specific read patterns.

Possible reasons:

    reduce expensive joins
    simplify reporting
    improve read performance
    support specialized workloads

Denormalization creates additional consistency responsibilities.

It should be based on actual workload requirements rather than
being used simply because joins appear inconvenient.
""")


# ============================================================
# 72. DERIVED DATA
# ============================================================

title("71. Derived Data")

explain("""
Derived data is calculated from other information.

Examples:

    order total
    account balance
    customer lifetime value
    inventory availability

The key design question is whether to calculate the value when it
is requested or store it.

Stored derived data can improve read performance but introduces the
risk of stale or inconsistent values.
""")


# ============================================================
# 73. HISTORICAL DATA
# ============================================================

title("72. Historical Data")

explain("""
Historical modeling becomes important when the system must preserve
past states.

Example:

A customer's address changes.

If the system simply updates the current address, the old address
is lost.

Historical approaches can include:

    audit tables
    effective_from / effective_to
    version numbers
    temporal modeling
    event records

The correct approach depends on the business requirement.
""")


# ============================================================
# 74. SOFT DELETE
# ============================================================

title("73. Soft Delete")

explain("""
A soft delete marks a record as inactive rather than physically
deleting it.

Common columns include:

    deleted_at
    is_deleted

Advantages:

    recoverability
    historical visibility
    easier auditing

Disadvantages:

    every query may need to filter deleted rows
    indexes may become more complex
    uniqueness rules can become complicated
    storage is retained

Soft deletion is a data lifecycle decision, not merely a coding trick.
""")


# ============================================================
# 75. SQL INJECTION
# ============================================================

title("74. SQL Injection")

explain("""
SQL injection occurs when untrusted input is interpreted as SQL
syntax.

The core defense is parameterized queries.

Bad pattern:

    SQL string + user input

Good pattern:

    SQL statement with placeholders
    values supplied separately

The database driver then handles the parameter as data rather than
SQL code.
""")


# ============================================================
# 76. SECURITY
# ============================================================

title("75. Database Security")

explain("""
Database security includes:

    authentication
    authorization
    encryption
    auditing
    least privilege
    network security
    credential management
    backup protection
    monitoring

Least privilege means users and applications should receive only
the permissions required for their responsibilities.

A web application normally should not have unrestricted administrative
permissions on the production database.
""")


# ============================================================
# 77. ORM
# ============================================================

title("76. Object Relational Mapping")

explain("""
ORM stands for Object Relational Mapping.

An ORM maps application objects to database structures.

Examples of ORM concepts include:

    model
    entity
    relationship
    repository
    query builder
    migration

ORMs can reduce repetitive SQL but do not eliminate the need to
understand SQL.

Complex queries, performance problems and transaction behavior still
require database knowledge.
""")


# ============================================================
# 78. N+1 QUERY
# ============================================================

title("77. N+1 Query Problem")

explain("""
The N+1 problem occurs when an application executes:

    1 query to retrieve N parent records

and then:

    1 additional query for each parent

This produces:

    1 + N queries

For large N, this can become expensive.

A JOIN, batch query, prefetch strategy or carefully designed query
can often reduce the number of database round trips.
""")


# ============================================================
# 79. CONNECTION POOLING
# ============================================================

title("78. Connection Pooling")

explain("""
Creating database connections has overhead.

A connection pool maintains a collection of reusable connections.

An application:

    acquires a connection
    performs database work
    releases the connection

The connection can then be reused.

Connection pooling is especially important in server applications
with many requests.
""")


# ============================================================
# 80. DATABASE MIGRATIONS
# ============================================================

title("79. Database Migrations")

explain("""
A migration is a controlled change to database structure or sometimes
data.

Examples:

    add a column
    create an index
    create a table
    change a constraint

Migrations allow database schema changes to be versioned and applied
consistently across environments.

A production migration must consider:

    existing data
    application compatibility
    execution time
    locking
    rollback strategy
    deployment order
""")


# ============================================================
# 81. BACKUP AND RECOVERY
# ============================================================

title("80. Backup and Recovery")

explain("""
A backup is a copy of database data that can be used for recovery.

Important concepts include:

    full backup
    incremental backup
    differential backup
    point-in-time recovery
    recovery point objective
    recovery time objective

RPO answers:

    How much data loss can the organization tolerate?

RTO answers:

    How long can the service remain unavailable?

A backup strategy is incomplete unless restoration has been tested.
""")


# ============================================================
# 82. WAL
# ============================================================

title("81. Write-Ahead Logging")

explain("""
Write-Ahead Logging, commonly called WAL, is a technique where
changes are recorded in a log before the modified data pages are
considered durable.

The log can help with:

    crash recovery
    durability
    concurrency
    replication

PostgreSQL and many other databases use WAL-style mechanisms.

SQLite also supports WAL mode.
""")

connection.execute("PRAGMA journal_mode = WAL")


# ============================================================
# 83. REPLICATION
# ============================================================

title("82. Replication")

explain("""
Replication means maintaining copies of database data on multiple
database instances.

Common reasons include:

    high availability
    read scaling
    disaster recovery
    geographic distribution

Replication can be:

    synchronous
    asynchronous

Synchronous replication generally prioritizes stronger confirmation
of durability across replicas but can increase latency.

Asynchronous replication can reduce write latency but creates a
window where replicas may lag behind the primary.
""")


# ============================================================
# 84. PARTITIONING
# ============================================================

title("83. Partitioning")

explain("""
Partitioning divides a large logical table into smaller physical
partitions.

Common strategies:

    range partitioning
    list partitioning
    hash partitioning

A common example is partitioning event data by month.

Partitioning can help with:

    data management
    query pruning
    maintenance
    archival

Partitioning behavior and syntax differ substantially among database
systems.
""")


# ============================================================
# 85. SHARDING
# ============================================================

title("84. Sharding")

explain("""
Sharding distributes data across multiple database nodes.

For example:

    users 1-1,000,000 -> shard A
    users 1,000,001-2,000,000 -> shard B

A shard key determines where data is stored.

Good shard keys distribute workload evenly.

Poor shard keys can create hotspots.

Sharding introduces complexity around:

    routing
    cross-shard queries
    transactions
    rebalancing
    consistency
    operational management
""")


# ============================================================
# 86. CAP THEOREM
# ============================================================

title("85. CAP Theorem")

explain("""
CAP theorem concerns distributed systems.

It describes a trade-off involving:

    Consistency
    Availability
    Partition tolerance

During a network partition, a distributed system cannot simultaneously
guarantee both unrestricted availability and strong consistency.

Partition tolerance matters because network failures can occur.

CAP should not be interpreted as a simple permanent choice of
"two out of three" in normal operation. The important situation is
what the system does when a partition occurs.
""")


# ============================================================
# 87. NOSQL
# ============================================================

title("86. Relational and NoSQL Databases")

explain("""
Relational databases organize data around tables, relationships,
constraints and SQL.

NoSQL is a broad category containing different models such as:

    document databases
    key-value stores
    wide-column databases
    graph databases

The correct choice depends on:

    access patterns
    consistency requirements
    data relationships
    scale
    operational constraints
    transaction requirements

NoSQL does not simply mean "faster database."
""")


# ============================================================
# 88. JSON
# ============================================================

title("87. JSON and Semi-Structured Data")

explain("""
Modern relational databases often support JSON or other semi-structured
data.

JSON can be useful when attributes vary between records or when
external payloads need to be stored.

It should not automatically replace normalized columns.

Frequently queried, constrained or relationally important fields
are often better represented as proper columns.
""")


# ============================================================
# 89. JSON DEMONSTRATION
# ============================================================

title("88. JSON Demonstration")

connection.execute("""
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    preferences TEXT
)
""")

connection.execute("""
INSERT INTO user_preferences
(user_id, preferences)
VALUES
(1, '{"theme":"dark","language":"en","notifications":true}')
""")

execute_and_show(
    connection,
    """
    SELECT
        json_extract(preferences, '$.theme') AS theme,
        json_extract(preferences, '$.language') AS language
    FROM user_preferences
    """
)


# ============================================================
# 90. DATABASE THINKING
# ============================================================

title("89. Database Thinking")

explain("""
Database thinking requires understanding the difference between:

    data
    identity
    relationships
    constraints
    operations
    transactions
    access patterns
    performance
    reliability

A table should not be designed only around how data looks.

It should be designed around:

    what the data means
    what must remain true
    how records relate
    how the application reads data
    how the application writes data
    how data changes over time
""")


# ============================================================
# 91. DATA INTEGRITY
# ============================================================

title("90. Data Integrity")

explain("""
Data integrity means that stored information remains valid and
consistent with the rules of the system.

Important categories include:

Entity integrity:

    rows have valid identity.

Referential integrity:

    relationships point to valid records.

Domain integrity:

    values satisfy their allowed domain or constraints.

Business integrity:

    values satisfy organization-specific rules.
""")


# ============================================================
# 92. APPLICATION TRANSACTION BOUNDARIES
# ============================================================

title("91. Transaction Boundaries")

explain("""
A transaction boundary defines which operations must succeed or fail
together.

For an order:

    create order
    create order items
    reduce inventory
    record payment state

The exact boundary depends on business requirements.

A transaction that is too small can leave related changes inconsistent.

A transaction that is unnecessarily large can increase locking,
contention and rollback cost.
""")


# ============================================================
# 93. IDEMPOTENCY
# ============================================================

title("92. Idempotency")

explain("""
An operation is idempotent when repeating it produces the same intended
result as performing it once.

This matters in distributed systems because requests may be retried.

For example, creating a payment using a unique payment request ID
can prevent accidental duplicate processing.

Database uniqueness constraints and UPSERT operations are often
important components of idempotent design.
""")


# ============================================================
# 94. DATABASE TESTING
# ============================================================

title("93. Database Testing")

explain("""
Database tests should verify both successful behavior and failure
behavior.

Important tests include:

    constraint tests
    foreign key tests
    transaction tests
    rollback tests
    uniqueness tests
    migration tests
    query result tests
    concurrency tests
    performance tests

A test should verify not only that valid data can be inserted but
also that invalid data is rejected.
""")


# ============================================================
# 95. DATABASE OBSERVABILITY
# ============================================================

title("94. Database Observability")

explain("""
Database observability involves understanding system behavior through
metrics, logs and traces.

Useful measurements include:

    query latency
    transaction latency
    throughput
    connection count
    lock waits
    deadlocks
    cache hit ratio
    replication lag
    disk utilization
    storage growth

Slow-query analysis is especially important in production systems.
""")


# ============================================================
# 96. QUERY DESIGN
# ============================================================

title("95. Query Design")

explain("""
Good SQL query design begins with a precise question.

Before writing SQL, determine:

    What entities are required?
    What columns are required?
    What relationships are required?
    Which rows qualify?
    Is aggregation required?
    Is ordering required?
    Can duplicates occur?
    What should happen with NULL?
    What is the expected data volume?

A correct query is more important than a clever query.
""")


# ============================================================
# 97. PERFORMANCE
# ============================================================

title("96. Database Performance")

explain("""
Database performance depends on several factors:

    query structure
    indexes
    data volume
    cardinality
    selectivity
    join strategy
    memory
    disk I/O
    CPU
    concurrency
    network latency
    connection management

A query that is fast on 1,000 rows may behave very differently
on 100 million rows.

Performance analysis should therefore consider realistic data volume.
""")


# ============================================================
# 98. COMMON PERFORMANCE PROBLEMS
# ============================================================

title("97. Common Performance Problems")

explain("""
Frequent database performance problems include:

    missing indexes
    excessive indexes
    SELECT *
    unnecessary joins
    inefficient pagination
    N+1 queries
    functions preventing index usage
    large unfiltered scans
    excessive network round trips
    oversized transactions
    poor connection management
    bad join conditions
    unnecessary DISTINCT
    inefficient sorting
""")


# ============================================================
# 99. OFFSET PAGINATION
# ============================================================

title("98. Pagination")

explain("""
Traditional pagination often uses:

    LIMIT
    OFFSET

For example:

    LIMIT 20 OFFSET 1000

As OFFSET becomes large, the database may need to process and discard
many preceding rows.

Keyset or cursor pagination can be more efficient for large datasets.

Example concept:

    WHERE id > last_seen_id
    ORDER BY id
    LIMIT 20
""")


# ============================================================
# 100. APPLICATION ARCHITECTURE
# ============================================================

title("99. Database in Application Architecture")

explain("""
A typical backend architecture may look like:

    Client
       |
       v
    API
       |
       v
    Application Service
       |
       v
    Repository / Data Access Layer
       |
       v
    Database

The database is responsible for durable data and integrity.

The application is responsible for business workflows and orchestration.

The exact division depends on system requirements.
""")


# ============================================================
# 101. DATABASE DESIGN PROCESS
# ============================================================

title("100. Database Design Process")

explain("""
A practical database design process can be expressed as:

    1. Identify business entities.
    2. Identify attributes.
    3. Identify relationships.
    4. Identify candidate keys.
    5. Select primary keys.
    6. Define foreign keys.
    7. Define constraints.
    8. Normalize the structure.
    9. Identify major access patterns.
    10. Add appropriate indexes.
    11. Define transaction boundaries.
    12. Consider security.
    13. Consider backup and recovery.
    14. Test realistic workloads.

Database design is therefore both a modeling problem and an operational
problem.
""")


# ============================================================
# 102. PRACTICAL E-COMMERCE DATABASE
# ============================================================

title("101. Practical E-Commerce Database Model")

explain("""
A basic e-commerce system may contain:

    customers
    addresses
    products
    categories
    inventory
    orders
    order_items
    payments
    shipments
    coupons
    reviews

Relationships:

    customer -> orders
    order -> order_items
    product -> order_items
    order -> payment
    order -> shipment
    product -> reviews
    customer -> reviews

Each relationship should be represented using appropriate keys and
constraints.
""")


# ============================================================
# 103. ORDER TOTALS
# ============================================================

title("102. Calculating Order Totals")

execute_and_show(
    connection,
    """
    SELECT
        o.order_id,
        SUM(oi.quantity * oi.unit_price) AS calculated_total
    FROM orders AS o
    JOIN order_items AS oi
        ON o.order_id = oi.order_id
    GROUP BY o.order_id
    ORDER BY o.order_id
    """
)


# ============================================================
# 104. CUSTOMER SPENDING
# ============================================================

title("103. Customer Spending")

execute_and_show(
    connection,
    """
    SELECT
        c.customer_id,
        c.name,
        COALESCE(SUM(o.total_amount), 0) AS total_spending
    FROM customers AS c
    LEFT JOIN orders AS o
        ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.name
    ORDER BY total_spending DESC
    """
)


# ============================================================
# 105. COALESCE
# ============================================================

title("104. COALESCE")

explain("""
COALESCE returns the first non-NULL expression.

For example:

    COALESCE(total, 0)

means:

    use total if it exists
    otherwise use 0

It is particularly useful with aggregate functions and LEFT JOINs.
""")


# ============================================================
# 106. NULLIF
# ============================================================

title("105. NULLIF")

explain("""
NULLIF returns NULL when two expressions are equal.

A common use is avoiding division by zero:

    value / NULLIF(denominator, 0)

This converts a zero denominator to NULL rather than attempting
division by zero.
""")


# ============================================================
# 107. CONSTRAINT-BASED DESIGN
# ============================================================

title("106. Constraint-Based Design")

explain("""
A strong database design expresses important business invariants
through constraints whenever possible.

Examples:

    price >= 0
    quantity >= 0
    email UNIQUE
    order.customer_id must exist
    order_item.quantity > 0

The database becomes an active participant in maintaining correctness
rather than merely acting as passive storage.
""")


# ============================================================
# 108. STORED PROCEDURES
# ============================================================

title("107. Stored Procedures and Functions")

explain("""
Some relational database systems support stored procedures and
stored functions.

They allow reusable logic to execute inside the database server.

Examples include:

    PostgreSQL functions
    SQL Server stored procedures
    Oracle PL/SQL procedures

SQLite does not provide server-side stored procedures in the same
way.

Stored procedures can be useful for:

    complex database-side operations
    controlled access
    reusable calculations
    transactional workflows

They can also make application architecture harder to understand
if excessive business logic is hidden inside the database.
""")


# ============================================================
# 109. DATABASE ROLES
# ============================================================

title("108. Users, Roles and Permissions")

explain("""
Server-based relational databases commonly provide:

    users
    roles
    privileges

Privileges can include:

    SELECT
    INSERT
    UPDATE
    DELETE
    EXECUTE

A role groups permissions.

For example:

    reporting_role
    application_role
    administrator_role

SQLite does not provide the same server-side user and role system.
""")


# ============================================================
# 110. DATABASE RELIABILITY
# ============================================================

title("109. Reliability")

explain("""
Database reliability depends on more than transaction semantics.

It includes:

    hardware reliability
    storage reliability
    backups
    replication
    monitoring
    recovery procedures
    schema management
    capacity planning
    failure testing

A database can provide ACID transactions and still be operationally
unreliable if backups are missing or recovery procedures are never tested.
""")


# ============================================================
# 111. AVAILABILITY
# ============================================================

title("110. Availability")

explain("""
Availability describes whether the database service can respond to
requests when needed.

Availability strategies can include:

    replication
    failover
    clustering
    redundancy
    health checks
    automated recovery

Higher availability usually introduces additional architectural and
operational complexity.
""")


# ============================================================
# 112. DURABILITY
# ============================================================

title("111. Durability")

explain("""
Durability means that committed data is intended to survive failures
according to the database's configured durability guarantees.

Durability can depend on:

    transaction logs
    fsync behavior
    storage hardware
    replication
    backup systems
    operating system behavior

A successful COMMIT does not mean that every possible disaster is
automatically recoverable.
""")


# ============================================================
# 113. DATABASE ADMINISTRATION
# ============================================================

title("112. Database Administration")

explain("""
Database administration involves operational responsibilities such as:

    installation
    configuration
    backups
    recovery
    monitoring
    indexing
    security
    capacity planning
    upgrades
    replication
    troubleshooting

A DBA must understand both database internals and operational risk.
""")


# ============================================================
# 114. RELATIONAL ALGEBRA
# ============================================================

title("113. Relational Algebra")

explain("""
Relational algebra provides a mathematical foundation for relational
query processing.

Important operations include:

    selection
    projection
    union
    difference
    Cartesian product
    join

SQL is a practical declarative language influenced by relational
theory, although SQL includes features that extend beyond classical
relational algebra.
""")


# ============================================================
# 115. DECLARATIVE SQL
# ============================================================

title("114. Declarative Nature of SQL")

explain("""
SQL is primarily declarative.

In imperative programming, the programmer describes how to perform
an operation step by step.

In SQL, the programmer generally describes what result is required.

The database optimizer determines an execution strategy.

This separation allows the database engine to change execution plans
without requiring the application to manually implement every access
algorithm.
""")


# ============================================================
# 116. QUERY OPTIMIZER
# ============================================================

title("115. Query Optimizer")

explain("""
A query optimizer evaluates possible execution strategies.

It can consider:

    indexes
    join order
    join algorithms
    filtering
    statistics
    sorting
    estimated row counts

The optimizer attempts to choose a plan with acceptable cost.

Database statistics help the optimizer estimate data distribution.
""")


# ============================================================
# 117. JOIN ALGORITHMS
# ============================================================

title("116. Join Algorithms")

explain("""
Common join algorithms include:

    nested loop join
    hash join
    merge join

The availability and implementation of these algorithms depend on
the database engine.

A nested loop can be effective when one side is small and the other
side has a suitable index.

A hash join can be useful for equality joins on large datasets.

A merge join can be effective when inputs are appropriately sorted.
""")


# ============================================================
# 118. TEMPORARY TABLES
# ============================================================

title("117. Temporary Tables")

explain("""
Temporary tables store intermediate data for a limited scope.

They can be useful when:

    an intermediate result is reused
    a complex transformation needs stages
    repeated calculations are expensive

Temporary tables differ from CTEs because a temporary table creates
a database object containing materialized rows, while a CTE primarily
provides query structure.
""")


# ============================================================
# 119. MATERIALIZED VIEWS
# ============================================================

title("118. Materialized Views")

explain("""
A materialized view stores the result of a query.

Unlike a normal view, the result is physically stored.

Advantages:

    faster repeated reads
    useful for expensive aggregations

Cost:

    stored results must be refreshed

PostgreSQL supports materialized views.

SQLite does not provide native materialized views in the same way.
""")


# ============================================================
# 120. DATABASE DIALECTS
# ============================================================

title("119. SQL Dialects")

explain("""
SQL is standardized, but database systems implement different
dialects and extensions.

Examples of differences include:

    pagination syntax
    date functions
    JSON operators
    generated columns
    procedural languages
    indexing features
    transaction behavior
    isolation implementation
    upsert syntax

Therefore SQL knowledge includes both general SQL principles and
engine-specific knowledge.
""")


# ============================================================
# 121. SQLITE FOREIGN KEY VERIFICATION
# ============================================================

title("120. Foreign Key Enforcement")

explain("""
SQLite requires foreign key enforcement to be enabled explicitly
for connections.

The setting used earlier was:

    PRAGMA foreign_keys = ON

Without enforcement, foreign-key declarations may not provide the
expected protection.
""")

foreign_key_state = connection.execute(
    "PRAGMA foreign_keys"
).fetchone()

print("Foreign key enforcement:", foreign_key_state[0])


# ============================================================
# 122. TRANSACTION SAFETY EXAMPLE
# ============================================================

title("121. Transaction Safety Example")

explain("""
The following example demonstrates how a transaction can prevent
partial completion of a multi-step operation.

The transaction intentionally raises an error so that the changes
are rolled back.
""")

try:
    connection.execute("BEGIN")

    connection.execute("""
        UPDATE accounts
        SET balance = balance - 100
        WHERE account_id = 1
    """)

    raise RuntimeError("Simulated application failure")

    connection.execute("""
        UPDATE accounts
        SET balance = balance + 100
        WHERE account_id = 2
    """)

    connection.commit()

except Exception as error:
    print("Transaction failed:", error)
    connection.rollback()

execute_and_show(
    connection,
    "SELECT * FROM accounts"
)


# ============================================================
# 123. CONSTRAINT FAILURE
# ============================================================

title("122. Constraint Failure")

explain("""
A database constraint should reject invalid data.

The following attempt violates the CHECK constraint because
quantity cannot be negative.
""")

try:
    connection.execute("""
        INSERT INTO constrained_products
        (id, name, price, sku, quantity)
        VALUES (?, ?, ?, ?, ?)
    """, (99, "Invalid Product", 100, "INVALID-1", -5))

    connection.commit()

except sqlite3.IntegrityError as error:
    print("Constraint rejected the data:", error)
    connection.rollback()


# ============================================================
# 124. UNIQUE CONSTRAINT
# ============================================================

title("123. UNIQUE Constraint")

explain("""
UNIQUE prevents duplicate values for a constrained column or
combination of columns.

It is useful for business identifiers such as:

    email
    username
    SKU

A UNIQUE constraint is different from a primary key because a table
has one primary key definition, while it can have multiple UNIQUE
constraints.
""")

try:
    connection.execute("""
        INSERT INTO constrained_products
        (id, name, price, sku, quantity)
        VALUES (?, ?, ?, ?, ?)
    """, (100, "Another Product", 200, "DUPLICATE", 5))

    connection.execute("""
        INSERT INTO constrained_products
        (id, name, price, sku, quantity)
        VALUES (?, ?, ?, ?, ?)
    """, (101, "Duplicate SKU", 300, "DUPLICATE", 4))

    connection.commit()

except sqlite3.IntegrityError as error:
    print("Unique constraint rejected the duplicate:", error)
    connection.rollback()


# ============================================================
# 125. GENERATED IDENTIFIERS
# ============================================================

title("124. Generated Identifiers")

explain("""
Many databases support automatically generated identifiers.

Common approaches include:

    auto-incrementing integers
    identity columns
    sequences
    UUIDs

SQLite's INTEGER PRIMARY KEY has special behavior that allows the
database to generate integer row identifiers.

The correct identifier strategy depends on:

    scale
    distribution
    replication
    ordering requirements
    security considerations
    application architecture
""")


# ============================================================
# 126. TIME AND DATE DATA
# ============================================================

title("125. Dates and Times")

explain("""
Date and time handling is a frequent source of database errors.

Important concepts include:

    date
    time
    timestamp
    time zone
    UTC
    local time
    daylight saving changes

Applications should establish clear rules for storage and conversion.

SQLite does not have a dedicated timestamp storage type comparable
to some server databases. Dates and times are commonly stored as
TEXT, REAL or INTEGER depending on the chosen representation.
""")


# ============================================================
# 127. DATA CONSISTENCY
# ============================================================

title("126. Consistency")

explain("""
Consistency means that database operations preserve defined rules.

Examples:

    foreign keys remain valid
    balances do not become negative
    required values are present
    unique identifiers remain unique

Consistency can be enforced through:

    constraints
    transactions
    application logic
    triggers
    database procedures
    architecture
""")


# ============================================================
# 128. DATABASE LIFECYCLE
# ============================================================

title("127. Data Lifecycle")

explain("""
Database data has a lifecycle.

A record may move through stages such as:

    creation
    modification
    active use
    archival
    retention
    deletion

Lifecycle policies matter for:

    storage cost
    performance
    legal requirements
    security
    recovery
    historical analysis
""")


# ============================================================
# 129. DATABASE VS FILE SYSTEM
# ============================================================

title("128. Database Compared with Files")

explain("""
Files are excellent for many tasks.

A database becomes particularly useful when requirements include:

    structured querying
    concurrent access
    transactions
    relationships
    constraints
    indexes
    recovery
    authorization
    scalable data management

The choice depends on the problem.

A database is not automatically the right tool for every storage task.
""")


# ============================================================
# 130. PRACTICAL QUERY
# ============================================================

title("129. Practical Business Query")

explain("""
The following query answers:

    Which customers have placed orders and how much have they spent?
""")

execute_and_show(
    connection,
    """
    SELECT
        c.customer_id,
        c.name,
        COUNT(o.order_id) AS order_count,
        SUM(o.total_amount) AS total_spending
    FROM customers AS c
    JOIN orders AS o
        ON c.customer_id = o.customer_id
    GROUP BY
        c.customer_id,
        c.name
    ORDER BY total_spending DESC
    """
)


# ============================================================
# 131. PRACTICAL PRODUCT QUERY
# ============================================================

title("130. Products Never Ordered")

explain("""
A common relational question is:

    Which products have never appeared in an order?

A LEFT JOIN can expose missing relationships.
""")

execute_and_show(
    connection,
    """
    SELECT
        p.product_id,
        p.product_name
    FROM products AS p
    LEFT JOIN order_items AS oi
        ON p.product_id = oi.product_id
    WHERE oi.product_id IS NULL
    """
)


# ============================================================
# 132. ANTI-JOIN CONCEPT
# ============================================================

title("131. Anti-Join")

explain("""
An anti-join finds rows for which no matching row exists.

SQL commonly expresses this through:

    LEFT JOIN ... IS NULL

or:

    NOT EXISTS

NOT EXISTS is often clearer when the intent is explicitly to test
for absence of a related record.
""")

execute_and_show(
    connection,
    """
    SELECT
        p.product_id,
        p.product_name
    FROM products AS p
    WHERE NOT EXISTS (
        SELECT 1
        FROM order_items AS oi
        WHERE oi.product_id = p.product_id
    )
    """
)


# ============================================================
# 133. EXISTS VS IN
# ============================================================

title("132. EXISTS and IN")

explain("""
IN checks whether a value belongs to a set of values.

EXISTS checks whether a related query produces at least one row.

The optimizer may transform these queries internally, but their
semantics and NULL behavior can differ.

Query clarity and correct handling of NULL should be considered.
""")


# ============================================================
# 134. DATABASE DESIGN TRADE-OFFS
# ============================================================

title("133. Database Design Trade-Offs")

explain("""
Database design contains trade-offs.

Normalization versus denormalization.

Read performance versus write simplicity.

Strong consistency versus distributed availability.

Flexible JSON versus strongly modeled columns.

Application logic versus database-side logic.

Simple architecture versus specialized scaling.

There is no universal database design that is optimal for every
workload.
""")


# ============================================================
# 135. DATABASE TEST DATABASE
# ============================================================

title("134. Testing Isolation")

explain("""
Tests often require isolated database state.

An in-memory SQLite database is useful for small automated tests
because it can be created and destroyed quickly.

For production database compatibility, tests should also be run
against the actual database engine when engine-specific behavior
matters.
""")


# ============================================================
# 136. ERROR HANDLING
# ============================================================

title("135. Database Error Handling")

explain("""
Database operations can fail for many reasons:

    constraint violations
    connection failures
    timeouts
    deadlocks
    serialization failures
    disk errors
    syntax errors
    unavailable database
    network failures

Applications should distinguish expected data errors from transient
infrastructure errors.
""")


# ============================================================
# 137. RETRIES
# ============================================================

title("136. Transaction Retries")

explain("""
Some database failures are transient.

Examples:

    deadlock victim
    serialization conflict
    temporary connection failure

A retry can be appropriate when the operation is safe to repeat.

Retry logic must be combined with idempotency so that repeating the
operation does not accidentally create duplicate business effects.
""")


# ============================================================
# 138. CONNECTION LIFECYCLE
# ============================================================

title("137. Connection Lifecycle")

explain("""
A database connection generally follows this lifecycle:

    open connection
    begin or enter transaction
    execute statements
    commit or rollback
    release connection

Long-lived transactions can hold locks or snapshots and may cause
resource pressure.

Connections should therefore be managed deliberately.
""")


# ============================================================
# 139. TRANSACTION CONTEXT MANAGER
# ============================================================

title("138. Python Transaction Context")

explain("""
Python's sqlite3 connection can be used as a context manager.

This makes transaction handling easier to structure.

The example below demonstrates the pattern conceptually.
""")

transaction_connection = sqlite3.connect(":memory:")

transaction_connection.execute("""
CREATE TABLE example (
    id INTEGER PRIMARY KEY,
    value TEXT NOT NULL
)
""")

try:
    with transaction_connection:
        transaction_connection.execute(
            "INSERT INTO example(value) VALUES (?)",
            ("transactional value",)
        )
except sqlite3.Error as error:
    print("Database error:", error)

execute_and_show(
    transaction_connection,
    "SELECT * FROM example"
)

transaction_connection.close()


# ============================================================
# 140. PRODUCTION ARCHITECTURE
# ============================================================

title("139. Production Database Architecture")

explain("""
A production system may contain:

    application servers
    connection pools
    primary database
    read replicas
    cache
    backup storage
    monitoring
    log aggregation
    disaster recovery infrastructure

The database architecture should be designed around:

    workload
    consistency
    availability
    latency
    recovery requirements
    security
    cost
""")


# ============================================================
# 141. DATABASE CACHE
# ============================================================

title("140. Database Caching")

explain("""
Caching stores frequently accessed data in a faster layer.

A cache can reduce repeated database reads.

Caching introduces its own problems:

    stale data
    invalidation
    memory limits
    consistency
    cache stampedes

A database should not automatically be bypassed with a cache.
The caching strategy should correspond to actual access patterns.
""")


# ============================================================
# 142. DATABASE SCALING
# ============================================================

title("141. Vertical and Horizontal Scaling")

explain("""
Vertical scaling means increasing the resources of a database server:

    CPU
    RAM
    storage
    I/O capacity

Horizontal scaling means distributing work across multiple systems.

Examples:

    read replicas
    sharding
    distributed databases

Vertical scaling is often simpler.

Horizontal scaling can support larger workloads but introduces
architectural complexity.
""")


# ============================================================
# 143. READ REPLICAS
# ============================================================

title("142. Read Replicas")

explain("""
A read replica maintains a copy of data from a primary database.

Applications may route:

    writes -> primary
    reads  -> replicas

This can increase read capacity.

Replication lag means a replica may temporarily return older data.

Applications must therefore understand whether a particular read
requires the latest committed value.
""")


# ============================================================
# 144. EVENTUAL CONSISTENCY
# ============================================================

title("143. Eventual Consistency")

explain("""
Eventual consistency means that replicas or distributed components
may temporarily contain different states but are expected to converge.

This model can be useful for distributed systems where low latency
and availability are important.

It changes application design because users may temporarily observe
stale information.
""")


# ============================================================
# 145. DATABASE MIGRATION COMPATIBILITY
# ============================================================

title("144. Backward-Compatible Schema Changes")

explain("""
A schema migration can affect old and new versions of an application.

A safer deployment pattern is often:

    expand
    migrate
    switch
    contract

For example:

    add a new nullable column
    deploy application that writes both fields
    backfill old records
    switch reads
    remove the old field later

This reduces the risk of deploying an application and database
change that cannot coexist.
""")


# ============================================================
# 146. DATABASE ANTI-PATTERNS
# ============================================================

title("145. Database Anti-Patterns")

explain("""
Common database anti-patterns include:

    storing unrelated entities in one giant table
    using comma-separated values for relationships
    ignoring foreign keys
    using SELECT * everywhere
    creating indexes without workload analysis
    creating too many indexes
    building SQL with string concatenation
    keeping transactions open unnecessarily
    ignoring NULL semantics
    relying entirely on application-side integrity
    storing every attribute as TEXT
    hiding critical logic in excessive triggers
    using soft deletes without query discipline
    ignoring migration compatibility
""")


# ============================================================
# 147. RELATIONAL INTEGRITY EXAMPLE
# ============================================================

title("146. Referential Integrity Demonstration")

explain("""
The following statement attempts to insert an order referencing a
customer that does not exist.

Foreign key enforcement should reject it.
""")

try:
    connection.execute("""
        INSERT INTO orders
        (order_id, customer_id, order_date, status, total_amount)
        VALUES (?, ?, ?, ?, ?)
    """, (999, 999999, "2026-03-01", "PENDING", 100))

    connection.commit()

except sqlite3.IntegrityError as error:
    print("Foreign key rejected the invalid relationship:", error)
    connection.rollback()


# ============================================================
# 148. DATABASE DOCUMENTATION
# ============================================================

title("147. Database Documentation")

explain("""
A useful database document can describe:

    table purpose
    column meaning
    data type
    nullability
    primary key
    foreign keys
    constraints
    indexes
    expected volume
    ownership
    retention
    sensitivity
    important queries

Good documentation reduces ambiguity during development and operations.
""")


# ============================================================
# 149. DATA OWNERSHIP
# ============================================================

title("148. Data Ownership")

explain("""
Data ownership defines responsibility for important data.

For example:

    customer data -> customer domain
    payment data  -> payment domain
    inventory     -> inventory domain

Ownership becomes particularly important in large systems where
multiple services or teams interact with related information.
""")


# ============================================================
# 150. DATABASE TERMINOLOGY
# ============================================================

title("149. Database Terminology")

explain("""
DATABASE

    Organized persistent collection of data.

DBMS

    Software that manages databases.

RDBMS

    Database management system based on the relational model.

TABLE

    Structured collection of rows and columns.

ROW

    One record or tuple.

COLUMN

    Attribute of a record.

SCHEMA

    Logical definition of database structures.

PRIMARY KEY

    Unique identifier for rows.

FOREIGN KEY

    Reference from one table to another.

CONSTRAINT

    Rule enforced by the database.

INDEX

    Data structure used to improve data retrieval.

QUERY

    Request for information or database operation.

TRANSACTION

    Logical unit of database work.

COMMIT

    Permanently applies a transaction.

ROLLBACK

    Reverses uncommitted transaction changes.

JOIN

    Combines related rows from multiple tables.

NORMALIZATION

    Logical design technique for reducing redundancy and anomalies.

DENORMALIZATION

    Intentional redundancy for specific workload requirements.

OLTP

    Transaction-oriented operational workload.

OLAP

    Analytical workload.

REPLICATION

    Maintaining copies of data on multiple systems.

PARTITIONING

    Dividing a table into partitions.

SHARDING

    Distributing data across multiple database nodes.

CARDINALITY

    Number or relationship multiplicity of data.

SELECTIVITY

    Degree to which a condition narrows the candidate rows.

ACID

    Atomicity, Consistency, Isolation and Durability.

MVCC

    Multi-Version Concurrency Control.

WAL

    Write-Ahead Logging.

RPO

    Recovery Point Objective.

RTO

    Recovery Time Objective.

ORM

    Object Relational Mapping.

UPSERT

    Insert or update depending on conflict.

CTE

    Common Table Expression.

DDL

    Data Definition Language.

DML

    Data Manipulation Language.

DCL

    Data Control Language.

TCL

    Transaction Control Language.
""")


# ============================================================
# 151. FINAL DATABASE STATE
# ============================================================

title("150. Inspecting the Database")

explain("""
The following statements inspect the main objects created during
this study script.
""")

execute_and_show(
    connection,
    """
    SELECT
        name,
        type
    FROM sqlite_master
    WHERE type IN ('table', 'index', 'view', 'trigger')
    ORDER BY type, name
    """)


# ============================================================
# 152. CLOSE DATABASE
# ============================================================

title("151. Closing the Database")

explain("""
A database connection should be closed when it is no longer needed.

Closing the connection releases associated resources.
""")

connection.close()

print("\nDatabase connection closed.")
