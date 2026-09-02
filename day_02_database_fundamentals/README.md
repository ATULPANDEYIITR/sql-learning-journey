# Database Fundamentals

## Purpose

This document contains a complete Python-based study script for understanding Database Fundamentals from basic concepts through advanced database concepts.

The Python examples use SQLite because it is available through Python's standard library and allows database concepts to be demonstrated without installing a separate database server.

---

# Part 1: Database Fundamentals Python Script

```python
"""
DATABASE FUNDAMENTALS
=====================

A comprehensive academic and practical study script covering:

1. What databases are
2. Database terminology
3. DBMS and RDBMS
4. Relational data model
5. Tables, rows, columns
6. Primary keys
7. Foreign keys
8. Candidate keys
9. Composite keys
10. Relationships
11. CRUD operations
12. SQL fundamentals
13. SELECT
14. WHERE
15. ORDER BY
16. GROUP BY
17. HAVING
18. DISTINCT
19. Aggregate functions
20. NULL
21. SQL operators
22. Joins
23. Subqueries
24. Common Table Expressions
25. Recursive CTEs
26. Views
27. Constraints
28. Normalization
29. Functional dependencies
30. Database anomalies
31. Transactions
32. ACID properties
33. COMMIT
34. ROLLBACK
35. SAVEPOINT
36. Concurrency
37. Locking
38. Deadlocks
39. Isolation levels
40. Indexes
41. Query optimization
42. Query plans
43. Window functions
44. Set operations
45. UPSERT
46. Triggers
47. Audit trails
48. JSON and semi-structured data
49. OLTP
50. OLAP
51. Fact and dimension tables
52. ETL and ELT
53. Data warehouses
54. Database security
55. SQL injection
56. Parameterized queries
57. Backup and recovery
58. Replication
59. Partitioning
60. Sharding
61. Distributed databases
62. Relational vs NoSQL databases
63. ORMs
64. Connection pooling
65. N+1 query problem
66. Database migrations
67. Idempotency
68. Historical data
69. Derived data
70. Data integrity
71. Cardinality
72. Selectivity
73. Covering indexes
74. Database architecture
75. Database design
76. E-commerce database example
77. Reporting queries
78. Practical database reasoning
79. Advanced terminology
"""

import sqlite3
from contextlib import closing
from datetime import datetime


# ============================================================
# SECTION 1: BASIC DATABASE CONCEPT
# ============================================================

print("=" * 80)
print("DATABASE FUNDAMENTALS")
print("=" * 80)

print("""
A database is an organized collection of data that can be stored,
retrieved, modified, protected, and managed systematically.

A Database Management System (DBMS) is software responsible for
managing databases.

Examples of database systems include:

- PostgreSQL
- MySQL
- Microsoft SQL Server
- Oracle Database
- SQLite
- MongoDB
- Redis
- Cassandra

A relational database stores information primarily in tables.

A table consists of:

- rows
- columns

A row normally represents one record or entity instance.

A column represents an attribute of that entity.
""")

# ============================================================
# SECTION 2: DBMS VS RDBMS
# ============================================================

print("\n" + "=" * 80)
print("DBMS VS RDBMS")
print("=" * 80)

print("""
DBMS means Database Management System.

RDBMS means Relational Database Management System.

An RDBMS follows the relational model and organizes data into
relations, which are represented as tables.

Important relational concepts include:

- tables
- tuples
- attributes
- keys
- relationships
- constraints
- relational operations

The relational model is based on mathematical set theory and
relational algebra.

SQLite is a relational database system.
""")

# ============================================================
# SECTION 3: CREATE DATABASE CONNECTION
# ============================================================

print("\n" + "=" * 80)
print("CREATING A DATABASE")
print("=" * 80)

connection = sqlite3.connect(":memory:")

print("""
The database connection is created using sqlite3.connect().

The database is stored in memory in this example.

SQLite also supports file-based databases:

sqlite3.connect("company.db")

A connection represents the communication channel between the
Python application and the database.
""")

# Enable foreign key enforcement.
connection.execute("PRAGMA foreign_keys = ON")

# ============================================================
# SECTION 4: CREATE TABLES
# ============================================================

print("\n" + "=" * 80)
print("TABLE DESIGN")
print("=" * 80)

connection.executescript("""
CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    employee_name TEXT NOT NULL,
    email TEXT UNIQUE,
    salary REAL CHECK (salary >= 0),
    department_id INTEGER,
    manager_id INTEGER,
    joining_date TEXT,
    FOREIGN KEY (department_id)
        REFERENCES departments(department_id),
    FOREIGN KEY (manager_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE projects (
    project_id INTEGER PRIMARY KEY,
    project_name TEXT NOT NULL,
    budget REAL CHECK (budget >= 0)
);

CREATE TABLE employee_projects (
    employee_id INTEGER,
    project_id INTEGER,
    assigned_on TEXT NOT NULL,

    PRIMARY KEY (employee_id, project_id),

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
);
""")

print("""
The database contains four tables.

departments
-----------
Stores department information.

employees
---------
Stores employee information.

projects
--------
Stores project information.

employee_projects
-----------------
Connects employees and projects.

The employee_projects table represents a many-to-many relationship.
""")

# ============================================================
# SECTION 5: TABLE TERMINOLOGY
# ============================================================

print("\n" + "=" * 80)
print("TABLE TERMINOLOGY")
print("=" * 80)

print("""
Table:
    Collection of related records.

Row:
    One record in a table.

Column:
    An attribute of the records.

Tuple:
    Relational-model terminology for a row.

Attribute:
    Relational-model terminology for a column.

Schema:
    The structural definition of the database.

Instance:
    The actual data stored in the database at a particular time.

Domain:
    The set of valid values for an attribute.
""")

# ============================================================
# SECTION 6: INSERT DATA
# ============================================================

print("\n" + "=" * 80)
print("INSERTING DATA")
print("=" * 80)

departments = [
    (1, "Engineering"),
    (2, "Finance"),
    (3, "Human Resources"),
    (4, "Marketing")
]

connection.executemany(
    """
    INSERT INTO departments
    (department_id, department_name)
    VALUES (?, ?)
    """,
    departments
)

employees = [
    (1, "Amit", "amit@example.com", 95000, 1, None, "2022-01-10"),
    (2, "Priya", "priya@example.com", 85000, 1, 1, "2023-03-15"),
    (3, "Rahul", "rahul@example.com", 70000, 1, 1, "2024-02-20"),
    (4, "Neha", "neha@example.com", 90000, 2, None, "2021-06-01"),
    (5, "Karan", "karan@example.com", 65000, 2, 4, "2024-05-10"),
    (6, "Sneha", "sneha@example.com", 60000, 3, None, "2023-08-18"),
    (7, "Vikas", "vikas@example.com", 72000, 4, None, "2022-11-11")
]

connection.executemany(
    """
    INSERT INTO employees
    (
        employee_id,
        employee_name,
        email,
        salary,
        department_id,
        manager_id,
        joining_date
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    employees
)

projects = [
    (1, "Database Migration", 150000),
    (2, "Mobile Application", 300000),
    (3, "Analytics Platform", 500000)
]

connection.executemany(
    """
    INSERT INTO projects
    (project_id, project_name, budget)
    VALUES (?, ?, ?)
    """,
    projects
)

employee_projects = [
    (1, 1, "2023-01-01"),
    (2, 1, "2023-02-01"),
    (2, 2, "2024-01-01"),
    (3, 2, "2024-03-01"),
    (4, 3, "2023-05-01"),
    (5, 3, "2024-06-01")
]

connection.executemany(
    """
    INSERT INTO employee_projects
    (employee_id, project_id, assigned_on)
    VALUES (?, ?, ?)
    """,
    employee_projects
)

connection.commit()

print("""
INSERT adds records to a table.

Parameterized queries use ? placeholders.

This is preferable to constructing SQL by concatenating user input.
""")

# ============================================================
# SECTION 7: SELECT
# ============================================================

print("\n" + "=" * 80)
print("SELECT")
print("=" * 80)

rows = connection.execute(
    "SELECT employee_id, employee_name, salary FROM employees"
).fetchall()

for row in rows:
    print(row)

print("""
SELECT retrieves data.

SELECT * retrieves all columns.

Explicitly naming columns is generally preferable because it makes
queries clearer and avoids unintentionally retrieving unnecessary data.
""")

# ============================================================
# SECTION 8: WHERE
# ============================================================

print("\n" + "=" * 80)
print("WHERE")
print("=" * 80)

rows = connection.execute(
    """
    SELECT employee_name, salary
    FROM employees
    WHERE salary > ?
    """,
    (80000,)
).fetchall()

for row in rows:
    print(row)

print("""
WHERE filters rows before grouping and aggregation.

Examples:

WHERE salary > 80000
WHERE department_id = 1
WHERE salary BETWEEN 60000 AND 90000
WHERE department_id IN (1, 2)
WHERE employee_name LIKE 'A%'
""")

# ============================================================
# SECTION 9: ORDER BY
# ============================================================

print("\n" + "=" * 80)
print("ORDER BY")
print("=" * 80)

rows = connection.execute(
    """
    SELECT employee_name, salary
    FROM employees
    ORDER BY salary DESC
    """
).fetchall()

for row in rows:
    print(row)

print("""
ORDER BY sorts query results.

ASC means ascending.

DESC means descending.

Ordering is applied to the result set and does not change the
physical meaning of the underlying records.
""")

# ============================================================
# SECTION 10: DISTINCT
# ============================================================

print("\n" + "=" * 80)
print("DISTINCT")
print("=" * 80)

rows = connection.execute(
    """
    SELECT DISTINCT department_id
    FROM employees
    """
).fetchall()

print(rows)

print("""
DISTINCT removes duplicate rows from the result.

It should not be used as a generic method for hiding incorrect
join logic because unnecessary DISTINCT operations may increase
query cost and can hide data-model problems.
""")

# ============================================================
# SECTION 11: UPDATE
# ============================================================

print("\n" + "=" * 80)
print("UPDATE")
print("=" * 80)

connection.execute(
    """
    UPDATE employees
    SET salary = salary * 1.05
    WHERE employee_id = ?
    """,
    (2,)
)

connection.commit()

print("""
UPDATE modifies existing records.

A WHERE clause is important when only selected records should be
modified.

Without WHERE, every row can potentially be updated.
""")

# ============================================================
# SECTION 12: DELETE
# ============================================================

print("\n" + "=" * 80)
print("DELETE")
print("=" * 80)

connection.execute(
    """
    DELETE FROM employees
    WHERE employee_id = ?
    """,
    (7,)
)

connection.commit()

print("""
DELETE removes records.

DELETE with a WHERE clause removes matching rows.

DELETE without WHERE can remove every row in a table.

DROP TABLE removes the table structure itself.

TRUNCATE, available in many database systems, removes table data
while retaining the table structure. SQLite does not implement
TRUNCATE TABLE as a separate SQL command.
""")

# Reinsert employee 7 for later examples.
connection.execute(
    """
    INSERT INTO employees
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (7, "Vikas", "vikas@example.com", 72000, 4, None, "2022-11-11")
)

connection.commit()

# ============================================================
# SECTION 13: SQL OPERATORS
# ============================================================

print("\n" + "=" * 80)
print("SQL OPERATORS")
print("=" * 80)

print("""
Comparison operators:

=
<>
!=
>
<
>=
<=

Logical operators:

AND
OR
NOT

Range:

BETWEEN

Membership:

IN

Pattern matching:

LIKE

NULL checks:

IS NULL
IS NOT NULL

A common mistake is writing:

salary = NULL

The correct form is:

salary IS NULL

NULL represents missing, unknown, or inapplicable information.
It does not behave like an ordinary value.
""")

# ============================================================
# SECTION 14: NULL
# ============================================================

print("\n" + "=" * 80)
print("NULL AND THREE-VALUED LOGIC")
print("=" * 80)

rows = connection.execute(
    """
    SELECT employee_name, manager_id
    FROM employees
    WHERE manager_id IS NULL
    """
).fetchall()

print(rows)

print("""
SQL logic involving NULL uses three logical states:

TRUE
FALSE
UNKNOWN

For example:

NULL = NULL

does not evaluate to TRUE.

This is why SQL uses:

IS NULL

and:

IS NOT NULL

NULL also affects aggregate functions.

COUNT(column) ignores NULL values.

COUNT(*) counts rows regardless of NULL values in individual columns.
""")

# ============================================================
# SECTION 15: AGGREGATE FUNCTIONS
# ============================================================

print("\n" + "=" * 80)
print("AGGREGATE FUNCTIONS")
print("=" * 80)

row = connection.execute(
    """
    SELECT
        COUNT(*) AS employee_count,
        AVG(salary) AS average_salary,
        MIN(salary) AS minimum_salary,
        MAX(salary) AS maximum_salary,
        SUM(salary) AS total_salary
    FROM employees
    """
).fetchone()

print(row)

print("""
Important aggregate functions:

COUNT()
SUM()
AVG()
MIN()
MAX()

Aggregate functions operate across multiple rows and produce
calculated results.
""")

# ============================================================
# SECTION 16: GROUP BY
# ============================================================

print("\n" + "=" * 80)
print("GROUP BY")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        department_id,
        COUNT(*) AS employee_count,
        AVG(salary) AS average_salary
    FROM employees
    GROUP BY department_id
    ORDER BY department_id
    """
).fetchall()

for row in rows:
    print(row)

print("""
GROUP BY divides rows into groups based on one or more expressions.

For example:

GROUP BY department_id

creates one group for each department.
""")

# ============================================================
# SECTION 17: HAVING
# ============================================================

print("\n" + "=" * 80)
print("HAVING")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        department_id,
        COUNT(*) AS employee_count
    FROM employees
    GROUP BY department_id
    HAVING COUNT(*) >= 2
    """
).fetchall()

print(rows)

print("""
WHERE filters individual rows.

HAVING filters groups after aggregation.

Conceptually:

FROM
WHERE
GROUP BY
HAVING
SELECT
ORDER BY

This is a simplified representation of SQL's logical processing
order. Actual database execution may use a different physical plan.
""")

# ============================================================
# SECTION 18: PRIMARY KEY
# ============================================================

print("\n" + "=" * 80)
print("PRIMARY KEY")
print("=" * 80)

print("""
A primary key uniquely identifies a row.

Characteristics normally associated with a primary key:

- uniqueness
- non-nullability
- stable identity
- row identification

Example:

employee_id INTEGER PRIMARY KEY

A table has one primary key constraint, although that primary key
can contain multiple columns.
""")

# ============================================================
# SECTION 19: COMPOSITE KEY
# ============================================================

print("\n" + "=" * 80)
print("COMPOSITE PRIMARY KEY")
print("=" * 80)

print("""
employee_projects uses:

PRIMARY KEY (employee_id, project_id)

This is a composite key.

Neither employee_id alone nor project_id alone identifies an
assignment.

The combination identifies one employee-project relationship.
""")

# ============================================================
# SECTION 20: CANDIDATE KEYS
# ============================================================

print("\n" + "=" * 80)
print("KEY TYPES")
print("=" * 80)

print("""
Super key:
    Any set of attributes that uniquely identifies a row.

Candidate key:
    A minimal super key.

Primary key:
    The candidate key selected as the principal identifier.

Alternate key:
    A candidate key not selected as the primary key.

Foreign key:
    Attribute(s) referencing a key in another table.

Composite key:
    Key consisting of multiple attributes.

Surrogate key:
    Artificial identifier such as an auto-generated integer.

Natural key:
    Identifier that has meaning in the business domain, such as
    a government-issued registration number.
""")

# ============================================================
# SECTION 21: FOREIGN KEY
# ============================================================

print("\n" + "=" * 80)
print("FOREIGN KEYS")
print("=" * 80)

print("""
A foreign key establishes a relationship between tables.

employees.department_id references:

departments.department_id

The foreign key helps enforce referential integrity.

For example, an employee cannot normally reference a department
that does not exist when foreign-key enforcement is enabled.
""")

# ============================================================
# SECTION 22: RELATIONSHIPS
# ============================================================

print("\n" + "=" * 80)
print("CARDINALITY AND RELATIONSHIPS")
print("=" * 80)

print("""
One-to-one:
    One record corresponds to at most one record in another table.

One-to-many:
    One department can have many employees.

Many-to-many:
    Many employees can work on many projects.

Many-to-many relationships are normally represented through a
junction or associative table.

Here:

employees
    |
    |
employee_projects
    |
    |
projects
""")

# ============================================================
# SECTION 23: INNER JOIN
# ============================================================

print("\n" + "=" * 80)
print("INNER JOIN")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        e.employee_name,
        d.department_name
    FROM employees AS e
    INNER JOIN departments AS d
        ON e.department_id = d.department_id
    ORDER BY e.employee_id
    """
).fetchall()

for row in rows:
    print(row)

print("""
INNER JOIN returns rows where the join condition matches.

Aliases such as e and d make multi-table queries easier to read.
""")

# ============================================================
# SECTION 24: LEFT JOIN
# ============================================================

print("\n" + "=" * 80)
print("LEFT JOIN")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        d.department_name,
        e.employee_name
    FROM departments AS d
    LEFT JOIN employees AS e
        ON d.department_id = e.department_id
    ORDER BY d.department_id
    """
).fetchall()

for row in rows:
    print(row)

print("""
LEFT JOIN preserves every row from the left table.

If there is no matching row on the right side, right-side columns
become NULL.

LEFT JOIN is especially useful for finding entities that do not
have related records.
""")

# ============================================================
# SECTION 25: FINDING RECORDS WITHOUT MATCHES
# ============================================================

print("\n" + "=" * 80)
print("ANTI-JOIN PATTERN")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        d.department_name
    FROM departments AS d
    LEFT JOIN employees AS e
        ON d.department_id = e.department_id
    WHERE e.employee_id IS NULL
    """
).fetchall()

print(rows)

print("""
This is a common anti-join pattern.

It identifies departments without employees.

Another common approach is:

WHERE NOT EXISTS (...)

NOT EXISTS is often clearer when the relationship logic is complex.
""")

# ============================================================
# SECTION 26: MANY-TO-MANY JOIN
# ============================================================

print("\n" + "=" * 80)
print("MANY-TO-MANY JOIN")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        e.employee_name,
        p.project_name
    FROM employees AS e
    JOIN employee_projects AS ep
        ON e.employee_id = ep.employee_id
    JOIN projects AS p
        ON ep.project_id = p.project_id
    ORDER BY e.employee_name
    """
).fetchall()

for row in rows:
    print(row)

print("""
The junction table converts a many-to-many relationship into
two one-to-many relationships.
""")

# ============================================================
# SECTION 27: SELF JOIN
# ============================================================

print("\n" + "=" * 80)
print("SELF JOIN")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        e.employee_name AS employee,
        m.employee_name AS manager
    FROM employees AS e
    LEFT JOIN employees AS m
        ON e.manager_id = m.employee_id
    ORDER BY e.employee_id
    """
).fetchall()

for row in rows:
    print(row)

print("""
A self join joins a table to itself.

It is useful for hierarchical structures such as:

employee -> manager
category -> parent category
folder -> parent folder
employee -> supervisor
""")

# ============================================================
# SECTION 28: SUBQUERY
# ============================================================

print("\n" + "=" * 80)
print("SUBQUERIES")
print("=" * 80)

rows = connection.execute(
    """
    SELECT employee_name, salary
    FROM employees
    WHERE salary >
        (
            SELECT AVG(salary)
            FROM employees
        )
    """
).fetchall()

for row in rows:
    print(row)

print("""
A subquery is a query nested inside another query.

Subqueries can appear in:

- SELECT
- FROM
- WHERE
- HAVING

A subquery may be scalar, correlated, or table-valued depending
on its position and structure.
""")

# ============================================================
# SECTION 29: EXISTS
# ============================================================

print("\n" + "=" * 80)
print("EXISTS")
print("=" * 80)

rows = connection.execute(
    """
    SELECT employee_name
    FROM employees AS e
    WHERE EXISTS (
        SELECT 1
        FROM employee_projects AS ep
        WHERE ep.employee_id = e.employee_id
    )
    """
).fetchall()

print(rows)

print("""
EXISTS checks whether at least one matching row exists.

It does not need to return the matching row's data.

EXISTS is useful for relationship-based conditions.
""")

# ============================================================
# SECTION 30: COMMON TABLE EXPRESSIONS
# ============================================================

print("\n" + "=" * 80)
print("COMMON TABLE EXPRESSIONS")
print("=" * 80)

rows = connection.execute(
    """
    WITH department_stats AS (
        SELECT
            department_id,
            AVG(salary) AS average_salary
        FROM employees
        GROUP BY department_id
    )
    SELECT
        d.department_name,
        ds.average_salary
    FROM department_stats AS ds
    JOIN departments AS d
        ON d.department_id = ds.department_id
    ORDER BY ds.average_salary DESC
    """
).fetchall()

for row in rows:
    print(row)

print("""
A Common Table Expression, or CTE, is introduced with WITH.

CTEs can improve readability by giving a complex intermediate
result a name.

A CTE is normally scoped to a single SQL statement.
""")

# ============================================================
# SECTION 31: RECURSIVE CTE
# ============================================================

print("\n" + "=" * 80)
print("RECURSIVE CTE")
print("=" * 80)

rows = connection.execute(
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
).fetchall()

print(rows)

print("""
Recursive CTEs contain:

1. Anchor query
2. Recursive query

They are useful for hierarchical and graph-like structures.

Examples:

- organization charts
- category trees
- folder structures
- dependency graphs
- bill of materials
""")

# ============================================================
# SECTION 32: VIEWS
# ============================================================

print("\n" + "=" * 80)
print("VIEWS")
print("=" * 80)

connection.execute(
    """
    CREATE VIEW employee_department_view AS
    SELECT
        e.employee_id,
        e.employee_name,
        e.salary,
        d.department_name
    FROM employees AS e
    JOIN departments AS d
        ON e.department_id = d.department_id
    """
)

rows = connection.execute(
    """
    SELECT *
    FROM employee_department_view
    ORDER BY employee_id
    """
).fetchall()

for row in rows:
    print(row)

print("""
A view is a stored query definition.

Views can provide:

- abstraction
- reusable query logic
- simplified reporting interfaces
- controlled exposure of columns

A normal view generally does not store a separate copy of the
underlying result.

Materialized views, supported by some database systems, physically
store query results and must be refreshed.
""")

# ============================================================
# SECTION 33: CONSTRAINTS
# ============================================================

print("\n" + "=" * 80)
print("DATABASE CONSTRAINTS")
print("=" * 80)

print("""
Constraints protect data integrity.

Common constraints:

PRIMARY KEY
FOREIGN KEY
UNIQUE
NOT NULL
CHECK
DEFAULT

Example:

salary REAL CHECK (salary >= 0)

The database itself rejects invalid salary values.

Constraints should be treated as part of the data model rather
than relying exclusively on application-level validation.
""")

# ============================================================
# SECTION 34: UNIQUE
# ============================================================

print("\n" + "=" * 80)
print("UNIQUE CONSTRAINT")
print("=" * 80)

print("""
The email column is UNIQUE.

This means two rows cannot normally contain the same non-null email.

UNIQUE is different from PRIMARY KEY.

A table can have multiple UNIQUE constraints.

A table has one primary key constraint.
""")

# ============================================================
# SECTION 35: NORMALIZATION
# ============================================================

print("\n" + "=" * 80)
print("DATABASE NORMALIZATION")
print("=" * 80)

print("""
Normalization is the systematic organization of relational data
to reduce redundancy and undesirable dependencies.

Important normal forms:

First Normal Form (1NF)
----------------------

Values should be atomic with respect to the chosen relational
design.

Instead of:

employee_id | skills
1           | Python, SQL, Java

a normalized design may use:

employee
skill
employee_skill

Second Normal Form (2NF)
------------------------

The relation must satisfy 1NF and every non-key attribute must
depend on the whole candidate key.

This is particularly important for composite keys.

Third Normal Form (3NF)
-----------------------

The relation must satisfy 2NF and non-key attributes should not
depend transitively on another non-key attribute.

Boyce-Codd Normal Form (BCNF)
-----------------------------

A stronger version of 3NF where every determinant is a candidate key.

Higher normal forms include:

4NF
5NF

These address increasingly complex dependency structures.
""")

# ============================================================
# SECTION 36: INSERTION ANOMALY
# ============================================================

print("\n" + "=" * 80)
print("DATABASE ANOMALIES")
print("=" * 80)

print("""
Poorly designed tables can produce anomalies.

Insertion anomaly:
    It may be impossible to insert one fact without another unrelated
    fact.

Update anomaly:
    The same fact exists in multiple places and must be updated
    consistently.

Deletion anomaly:
    Deleting one fact accidentally removes another useful fact.

Normalization attempts to reduce these problems.
""")

# ============================================================
# SECTION 37: FUNCTIONAL DEPENDENCY
# ============================================================

print("\n" + "=" * 80)
print("FUNCTIONAL DEPENDENCY")
print("=" * 80)

print("""
A functional dependency describes a relationship where one attribute
or set of attributes determines another.

Notation:

A -> B

means:

If two rows have the same A value, they must have the same B value.

Example:

employee_id -> employee_name

because employee_id identifies one employee.

Functional dependencies are fundamental to normalization.
""")

# ============================================================
# SECTION 38: TRANSACTIONS
# ============================================================

print("\n" + "=" * 80)
print("TRANSACTIONS")
print("=" * 80)

print("""
A transaction is a logical unit of work.

A transaction may contain multiple database operations.

The goal is to ensure that related operations behave as one
consistent unit.

Typical transaction flow:

BEGIN
    operation 1
    operation 2
    operation 3
COMMIT

If something goes wrong:

ROLLBACK
""")

connection.execute(
    """
    CREATE TABLE accounts (
        account_id INTEGER PRIMARY KEY,
        owner TEXT NOT NULL,
        balance REAL NOT NULL CHECK(balance >= 0)
    )
    """
)

connection.executemany(
    """
    INSERT INTO accounts
    VALUES (?, ?, ?)
    """,
    [
        (1, "A", 1000),
        (2, "B", 500)
    ]
)

connection.commit()

# ============================================================
# SECTION 39: TRANSACTION EXAMPLE
# ============================================================

print("\n" + "=" * 80)
print("TRANSACTION EXAMPLE")
print("=" * 80)

try:
    connection.execute("BEGIN")

    connection.execute(
        """
        UPDATE accounts
        SET balance = balance - ?
        WHERE account_id = ?
        """,
        (100, 1)
    )

    connection.execute(
        """
        UPDATE accounts
        SET balance = balance + ?
        WHERE account_id = ?
        """,
        (100, 2)
    )

    connection.commit()

except Exception:
    connection.rollback()

print(
    connection.execute(
        "SELECT * FROM accounts ORDER BY account_id"
    ).fetchall()
)

# ============================================================
# SECTION 40: ACID
# ============================================================

print("\n" + "=" * 80)
print("ACID PROPERTIES")
print("=" * 80)

print("""
Atomicity
---------

A transaction is treated as one logical unit.

Either all required operations succeed or the transaction is
rolled back.

Consistency
-----------

A committed transaction should preserve defined database
constraints and integrity rules.

Isolation
---------

Concurrent transactions should not interfere in ways that violate
the selected isolation guarantees.

Durability
----------

Once a transaction is committed, the database should preserve its
effects despite ordinary failures, subject to the database system's
durability guarantees and storage configuration.
""")

# ============================================================
# SECTION 41: SAVEPOINT
# ============================================================

print("\n" + "=" * 80)
print("SAVEPOINT")
print("=" * 80)

connection.execute("BEGIN")

connection.execute(
    """
    UPDATE accounts
    SET balance = balance + 50
    WHERE account_id = 1
    """
)

connection.execute("SAVEPOINT before_second_change")

connection.execute(
    """
    UPDATE accounts
    SET balance = balance - 25
    WHERE account_id = 2
    """
)

connection.execute("ROLLBACK TO before_second_change")

connection.execute("RELEASE before_second_change")

connection.commit()

print("""
SAVEPOINT allows partial rollback inside a transaction.

ROLLBACK TO savepoint

undoes changes after that savepoint while keeping the transaction
active.
""")

# ============================================================
# SECTION 42: CONCURRENCY
# ============================================================

print("\n" + "=" * 80)
print("CONCURRENCY")
print("=" * 80)

print("""
Concurrency means multiple transactions or database operations
can occur during overlapping periods.

Concurrency introduces concerns such as:

Dirty read
----------

A transaction reads data written by another transaction that has
not committed.

Non-repeatable read
-------------------

The same row produces different values when read twice because
another transaction committed an update.

Phantom read
------------

A repeated query returns a different set of rows because another
transaction inserted or deleted matching records.

Lost update
-----------

One update unintentionally overwrites another update.

Different database systems and isolation levels provide different
guarantees.
""")

# ============================================================
# SECTION 43: LOCKING
# ============================================================

print("\n" + "=" * 80)
print("LOCKING")
print("=" * 80)

print("""
Database systems use locking and other concurrency-control
mechanisms to coordinate transactions.

Common conceptual lock categories include:

Shared lock:
    Used for reading.

Exclusive lock:
    Used for modifications.

The exact locking implementation depends on the database engine.

SQLite uses a different concurrency architecture from systems such
as PostgreSQL and SQL Server, so locking terminology should not be
assumed to behave identically across all database products.
""")

# ============================================================
# SECTION 44: DEADLOCK
# ============================================================

print("\n" + "=" * 80)
print("DEADLOCK")
print("=" * 80)

print("""
A deadlock occurs when transactions wait for each other indefinitely.

Conceptual example:

Transaction A locks Resource 1
Transaction B locks Resource 2

Transaction A waits for Resource 2
Transaction B waits for Resource 1

Neither transaction can proceed.

Databases can detect deadlocks and abort one transaction.

Application code should normally be prepared to retry transactions
when the database reports retryable concurrency failures.
""")

# ============================================================
# SECTION 45: INDEXES
# ============================================================

print("\n" + "=" * 80)
print("INDEXES")
print("=" * 80)

connection.execute(
    """
    CREATE INDEX idx_employee_department
    ON employees(department_id)
    """
)

connection.execute(
    """
    CREATE INDEX idx_employee_salary
    ON employees(salary)
    """
)

print("""
An index is an auxiliary data structure used to make certain
queries faster.

Without an appropriate index, a database may need to inspect many
rows.

Indexes can improve reads but introduce costs:

- additional storage
- additional write work
- maintenance overhead
- memory usage

An index is not automatically beneficial for every column.
""")

# ============================================================
# SECTION 46: COMPOSITE INDEX
# ============================================================

print("\n" + "=" * 80)
print("COMPOSITE INDEX")
print("=" * 80)

connection.execute(
    """
    CREATE INDEX idx_department_salary
    ON employees(department_id, salary)
    """
)

print("""
A composite index contains multiple columns.

Index:

(department_id, salary)

is different from two independent indexes:

(department_id)
(salary)

Column order matters.

A composite index beginning with department_id can efficiently
support queries whose filtering or ordering begins with
department_id.

This is related to the leftmost-prefix concept in many B-tree
index implementations.
""")

# ============================================================
# SECTION 47: SELECTIVITY
# ============================================================

print("\n" + "=" * 80)
print("CARDINALITY AND SELECTIVITY")
print("=" * 80)

print("""
Cardinality can refer to the number of distinct values or, depending
on context, the number of rows in a relation.

Selectivity describes how narrowly a predicate filters rows.

A predicate matching 1% of a table is highly selective.

A predicate matching 90% of a table is not highly selective.

Indexes are often particularly useful when they allow the database
to quickly narrow a large candidate set.
""")

# ============================================================
# SECTION 48: EXPLAIN QUERY PLAN
# ============================================================

print("\n" + "=" * 80)
print("QUERY PLAN")
print("=" * 80)

plan = connection.execute(
    """
    EXPLAIN QUERY PLAN
    SELECT employee_name
    FROM employees
    WHERE department_id = 1
    """
).fetchall()

for row in plan:
    print(row)

print("""
EXPLAIN and EXPLAIN QUERY PLAN expose information about how the
database intends to execute a query.

A query plan may involve:

- table scans
- index scans
- index lookups
- sorting
- temporary structures
- joins

Query optimization is based on the actual execution strategy,
not merely on the textual appearance of the SQL statement.
""")

# ============================================================
# SECTION 49: COVERING INDEX
# ============================================================

print("\n" + "=" * 80)
print("COVERING INDEX")
print("=" * 80)

print("""
A covering index contains enough information for a query to be
answered using the index without consulting the underlying table
for every requested value.

For example, an index containing:

(department_id, employee_name)

may be able to satisfy:

SELECT employee_name
FROM employees
WHERE department_id = ?

without requiring a separate table lookup.

Whether a database chooses such a strategy depends on its optimizer
and cost estimates.
""")

# ============================================================
# SECTION 50: WINDOW FUNCTIONS
# ============================================================

print("\n" + "=" * 80)
print("WINDOW FUNCTIONS")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        employee_name,
        department_id,
        salary,
        RANK() OVER (
            PARTITION BY department_id
            ORDER BY salary DESC
        ) AS salary_rank
    FROM employees
    ORDER BY department_id, salary_rank
    """
).fetchall()

for row in rows:
    print(row)

print("""
Window functions calculate values across related rows without
collapsing those rows into one result row.

Common window functions:

ROW_NUMBER()
RANK()
DENSE_RANK()
LAG()
LEAD()
SUM() OVER (...)
AVG() OVER (...)

PARTITION BY divides rows into logical groups.

ORDER BY inside OVER determines ordering within the window.
""")

# ============================================================
# SECTION 51: ROW_NUMBER
# ============================================================

print("\n" + "=" * 80)
print("ROW_NUMBER")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        employee_name,
        salary,
        ROW_NUMBER() OVER (
            ORDER BY salary DESC
        ) AS row_number
    FROM employees
    """
).fetchall()

for row in rows:
    print(row)

print("""
ROW_NUMBER assigns a unique sequential number within the window.

RANK can produce equal ranks when values are tied.

DENSE_RANK also produces equal ranks for ties but does not leave
gaps after a tie.
""")

# ============================================================
# SECTION 52: SET OPERATIONS
# ============================================================

print("\n" + "=" * 80)
print("SET OPERATIONS")
print("=" * 80)

rows = connection.execute(
    """
    SELECT department_id
    FROM employees
    WHERE salary > 80000

    UNION

    SELECT department_id
    FROM employees
    WHERE salary < 70000
    """
).fetchall()

print(rows)

print("""
SQL set operations include:

UNION
UNION ALL
INTERSECT
EXCEPT

UNION removes duplicates.

UNION ALL preserves duplicates and is generally cheaper when
duplicate elimination is unnecessary.

The queries involved in set operations must have compatible
result structures.
""")

# ============================================================
# SECTION 53: UPSERT
# ============================================================

print("\n" + "=" * 80)
print("UPSERT")
print("=" * 80)

connection.execute(
    """
    INSERT INTO departments(department_id, department_name)
    VALUES (?, ?)
    ON CONFLICT(department_id)
    DO UPDATE SET department_name = excluded.department_name
    """,
    (1, "Engineering and Technology")
)

connection.commit()

print(
    connection.execute(
        "SELECT * FROM departments WHERE department_id = 1"
    ).fetchone()
)

print("""
UPSERT combines insertion and conflict handling.

The exact syntax differs between database systems.

The conceptual pattern is:

If the record does not exist:
    INSERT

If a defined conflict occurs:
    UPDATE or perform another action.
""")

# Restore name for remaining examples.
connection.execute(
    """
    UPDATE departments
    SET department_name = 'Engineering'
    WHERE department_id = 1
    """
)

connection.commit()

# ============================================================
# SECTION 54: TRIGGERS
# ============================================================

print("\n" + "=" * 80)
print("TRIGGERS")
print("=" * 80)

connection.executescript("""
CREATE TABLE employee_audit (
    audit_id INTEGER PRIMARY KEY,
    employee_id INTEGER,
    operation TEXT NOT NULL,
    changed_at TEXT NOT NULL
);

CREATE TRIGGER employee_insert_audit
AFTER INSERT ON employees
BEGIN
    INSERT INTO employee_audit
    (
        employee_id,
        operation,
        changed_at
    )
    VALUES
    (
        NEW.employee_id,
        'INSERT',
        CURRENT_TIMESTAMP
    );
END;
""")

connection.execute(
    """
    INSERT INTO employees
    (
        employee_id,
        employee_name,
        email,
        salary,
        department_id,
        manager_id,
        joining_date
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (
        8,
        "Temporary Employee",
        "temporary@example.com",
        55000,
        1,
        1,
        "2025-01-01"
    )
)

connection.commit()

print(
    connection.execute(
        "SELECT * FROM employee_audit"
    ).fetchall()
)

connection.execute(
    "DELETE FROM employees WHERE employee_id = 8"
)

connection.commit()

print("""
A trigger automatically executes when a specified database event
occurs.

Common trigger events:

INSERT
UPDATE
DELETE

Triggers can be useful for auditing and enforcing certain rules,
but excessive trigger usage can make database behavior difficult
to understand because logic becomes implicit.
""")

# ============================================================
# SECTION 55: AUDIT TRAILS
# ============================================================

print("\n" + "=" * 80)
print("AUDITING")
print("=" * 80)

print("""
An audit trail records important changes.

Typical audit fields include:

- record identifier
- operation
- actor
- timestamp
- previous value
- new value
- request identifier

Auditing is important when the system needs to answer:

Who changed this?
What changed?
When did it change?
What was the previous value?
""")

# ============================================================
# SECTION 56: SQL INJECTION
# ============================================================

print("\n" + "=" * 80)
print("SQL INJECTION")
print("=" * 80)

print("""
SQL injection occurs when untrusted input is incorrectly inserted
into SQL text.

Unsafe conceptual code:

query = "SELECT * FROM users WHERE name = '" + user_input + "'"

An attacker may manipulate the SQL syntax.

The safer approach is parameterized SQL:

cursor.execute(
    "SELECT * FROM users WHERE name = ?",
    (user_input,)
)

The database driver treats the parameter as data rather than SQL
syntax.

Parameterized queries are one of the fundamental defenses against
SQL injection.
""")

# ============================================================
# SECTION 57: DATABASE SECURITY
# ============================================================

print("\n" + "=" * 80)
print("DATABASE SECURITY")
print("=" * 80)

print("""
Database security involves multiple layers.

Authentication:
    Establishing who the user is.

Authorization:
    Determining what the user is allowed to do.

Encryption:
    Protecting data during transmission and, where appropriate,
    at rest.

Auditing:
    Recording important database activities.

Least privilege:
    Giving identities only the permissions they actually need.

Secrets management:
    Avoiding passwords and credentials embedded directly in source
    code.

Input validation:
    Ensuring application input is handled safely.

Parameterized queries:
    Separating SQL instructions from data values.
""")

# ============================================================
# SECTION 58: DATA TYPES
# ============================================================

print("\n" + "=" * 80)
print("DATA TYPES")
print("=" * 80)

print("""
Common relational data types include:

INTEGER
BIGINT
DECIMAL
NUMERIC
REAL
FLOAT
CHAR
VARCHAR
TEXT
DATE
TIME
TIMESTAMP
BOOLEAN
BINARY
JSON

Exact types and semantics differ between database systems.

For financial values, fixed-precision numeric types are generally
preferred over floating-point representations because floating-point
arithmetic can introduce representation errors.

SQLite uses dynamic typing with type affinities, so SQLite's type
behavior differs from strongly typed systems such as PostgreSQL.
""")

# ============================================================
# SECTION 59: SCHEMA
# ============================================================

print("\n" + "=" * 80)
print("DATABASE SCHEMA")
print("=" * 80)

print("""
A schema describes the structure and organization of database
objects.

Depending on the database system, schema-related objects can include:

- tables
- columns
- constraints
- indexes
- views
- sequences
- functions
- procedures
- triggers

In some systems, a schema is also a namespace that contains
database objects.

SQLite's schema model is simpler than the schema and namespace
systems used by PostgreSQL or SQL Server.
""")

# ============================================================
# SECTION 60: OLTP
# ============================================================

print("\n" + "=" * 80)
print("OLTP")
print("=" * 80)

print("""
OLTP means Online Transaction Processing.

OLTP systems handle operational transactions.

Examples:

- placing an order
- transferring money
- registering a customer
- updating inventory
- creating an employee record

Typical characteristics:

- frequent writes
- relatively small transactions
- many concurrent users
- strong consistency requirements
- normalized schemas
- low-latency operations
""")

# ============================================================
# SECTION 61: OLAP
# ============================================================

print("\n" + "=" * 80)
print("OLAP")
print("=" * 80)

print("""
OLAP means Online Analytical Processing.

OLAP systems are optimized for analysis.

Examples:

- monthly sales analysis
- customer segmentation
- financial reporting
- business intelligence
- historical trend analysis

Typical characteristics:

- large analytical queries
- aggregations
- historical data
- fewer writes
- large scans
- dimensional models
""")

# ============================================================
# SECTION 62: DATA WAREHOUSE
# ============================================================

print("\n" + "=" * 80)
print("DATA WAREHOUSE")
print("=" * 80)

print("""
A data warehouse is designed for analytical workloads.

A common dimensional model contains:

Fact tables
    Store measurable business events.

Dimension tables
    Store descriptive context.

Example:

fact_sales

Dimensions:

dim_customer
dim_product
dim_date
dim_store

A sales fact might contain:

customer_key
product_key
date_key
store_key
quantity
revenue
discount
""")

# ============================================================
# SECTION 63: ETL AND ELT
# ============================================================

print("\n" + "=" * 80)
print("ETL AND ELT")
print("=" * 80)

print("""
ETL:

Extract
Transform
Load

Data is transformed before loading into the destination system.

ELT:

Extract
Load
Transform

Raw or lightly processed data is loaded first and transformed
inside the target analytical system.

The distinction is architectural rather than merely terminological.
""")

# ============================================================
# SECTION 64: RELATIONAL VS NOSQL
# ============================================================

print("\n" + "=" * 80)
print("RELATIONAL VS NOSQL")
print("=" * 80)

print("""
Relational databases emphasize:

- structured schemas
- tables
- relationships
- SQL
- constraints
- transactions
- relational algebra

NoSQL is a broad category containing several models.

Document databases:
    JSON-like documents.

Key-value databases:
    key -> value.

Wide-column databases:
    column-family-oriented storage.

Graph databases:
    nodes and relationships.

NoSQL does not mean "no structure."

It generally means the database model is not limited to the
traditional relational model.

The choice depends on access patterns, consistency requirements,
scale, operational requirements, and data structure.
""")

# ============================================================
# SECTION 65: JSON
# ============================================================

print("\n" + "=" * 80)
print("SEMI-STRUCTURED DATA")
print("=" * 80)

connection.execute(
    """
    CREATE TABLE customer_profiles (
        customer_id INTEGER PRIMARY KEY,
        profile TEXT
    )
    """
)

connection.execute(
    """
    INSERT INTO customer_profiles
    VALUES (?, ?)
    """,
    (
        1,
        '{"name":"Amit","preferences":{"language":"English","theme":"dark"}}'
    )
)

connection.commit()

print(
    connection.execute(
        "SELECT * FROM customer_profiles"
    ).fetchall()
)

print("""
JSON can be useful when data has variable structure.

It should not automatically replace relational columns.

A field should generally remain a normal relational column when
the application frequently filters, joins, constrains, or indexes
it as a first-class business attribute.

JSON is useful for genuinely flexible or semi-structured data.
""")

# ============================================================
# SECTION 66: DENORMALIZATION
# ============================================================

print("\n" + "=" * 80)
print("DENORMALIZATION")
print("=" * 80)

print("""
Denormalization intentionally introduces redundancy to improve
specific access patterns.

Reasons can include:

- reducing expensive joins
- improving read performance
- simplifying reporting
- storing precomputed values

The trade-off is increased complexity in maintaining consistency.

Normalization is not a rule that must always be maximized.

Database design is about selecting an appropriate balance between:

- integrity
- performance
- maintainability
- storage
- simplicity
""")

# ============================================================
# SECTION 67: DERIVED DATA
# ============================================================

print("\n" + "=" * 80)
print("DERIVED DATA")
print("=" * 80)

print("""
Derived data is information that can be calculated from other data.

Example:

total_price = quantity * unit_price

Storing both the inputs and the derived result creates a consistency
problem unless there is a clear reason to store the derived value.

Derived values can be appropriate when:

- calculation is expensive
- historical value must be preserved
- reporting performance matters
- business semantics require a snapshot
""")

# ============================================================
# SECTION 68: HISTORICAL DATA
# ============================================================

print("\n" + "=" * 80)
print("HISTORICAL DATA")
print("=" * 80)

print("""
Current-state data answers:

What is true now?

Historical data answers:

What was true at a particular time?

A price table may contain:

product_id
price
effective_from
effective_to

This permits temporal analysis.

Historical modeling is important for:

- pricing
- employment
- contracts
- customer status
- organizational structures
- regulatory records
""")

# ============================================================
# SECTION 69: DATABASE MIGRATIONS
# ============================================================

print("\n" + "=" * 80)
print("DATABASE MIGRATIONS")
print("=" * 80)

print("""
A migration is a controlled change to database structure or
database-related data.

Examples:

- creating a table
- adding a column
- creating an index
- changing a constraint
- transforming existing data

A migration system maintains a sequence of schema changes so that
different environments can reach the same intended database state.

Migrations should be:

- ordered
- reproducible
- reviewable
- tested
- tracked
""")

# ============================================================
# SECTION 70: ORM
# ============================================================

print("\n" + "=" * 80)
print("ORM")
print("=" * 80)

print("""
ORM means Object-Relational Mapping.

An ORM maps application objects to relational database structures.

Conceptually:

Python class -> table
object -> row
attribute -> column
relationship -> foreign-key relationship

ORMs can reduce repetitive SQL.

They can also hide important database behavior.

A developer using an ORM still needs to understand:

- SQL
- joins
- indexes
- transactions
- constraints
- query plans
- locking
- cardinality
""")

# ============================================================
# SECTION 71: N+1 QUERY PROBLEM
# ============================================================

print("\n" + "=" * 80)
print("N+1 QUERY PROBLEM")
print("=" * 80)

print("""
The N+1 query problem occurs when an application executes:

1 query to retrieve N parent records

followed by:

N additional queries to retrieve related records.

Total:

N + 1 queries

This can create severe performance problems.

A join, eager loading strategy, batch query, or carefully designed
data access pattern can often reduce the number of database calls.
""")

# ============================================================
# SECTION 72: CONNECTION POOLING
# ============================================================

print("\n" + "=" * 80)
print("CONNECTION POOLING")
print("=" * 80)

print("""
Opening a database connection can be expensive.

Connection pooling maintains reusable connections.

A typical application may:

1. obtain a connection
2. execute database work
3. commit or roll back
4. return the connection to the pool

Pooling improves efficiency for systems with many requests.

The correct pool size depends on workload, database capacity,
application concurrency, and infrastructure.
""")

# ============================================================
# SECTION 73: DATABASE APPLICATION ARCHITECTURE
# ============================================================

print("\n" + "=" * 80)
print("APPLICATION DATABASE ARCHITECTURE")
print("=" * 80)

print("""
A common architecture is:

Client
   |
Application/API
   |
Database access layer
   |
Database

The application should normally define transaction boundaries
around logical units of work.

A transaction should not remain open unnecessarily while unrelated
application work is being performed.
""")

# ============================================================
# SECTION 74: TRANSACTION BOUNDARIES
# ============================================================

print("\n" + "=" * 80)
print("TRANSACTION BOUNDARIES")
print("=" * 80)

print("""
Consider an order placement operation:

1. create order
2. create order items
3. reduce inventory
4. record payment state

If these operations represent one atomic business action, the
transaction boundary may encompass all relevant operations.

If only the first operation succeeds and the others fail, the
system could enter an inconsistent state.

Transaction boundaries should reflect business consistency
requirements.
""")

# ============================================================
# SECTION 75: IDEMPOTENCY
# ============================================================

print("\n" + "=" * 80)
print("IDEMPOTENCY")
print("=" * 80)

print("""
An operation is idempotent if repeating it produces the same
effective result after the first successful execution.

Idempotency is important in distributed systems because network
requests may be retried.

Example:

A payment request contains:

idempotency_key = ABC123

The server records the key and prevents the same logical operation
from being performed twice.
""")

# ============================================================
# SECTION 76: DATABASE RELIABILITY
# ============================================================

print("\n" + "=" * 80)
print("RELIABILITY")
print("=" * 80)

print("""
Database reliability involves:

- durability
- backups
- recovery
- replication
- monitoring
- integrity checking
- capacity management
- failure handling

A database system should be designed according to required
availability and recovery objectives.
""")

# ============================================================
# SECTION 77: BACKUP AND RECOVERY
# ============================================================

print("\n" + "=" * 80)
print("BACKUP AND RECOVERY")
print("=" * 80)

print("""
A backup is a recoverable copy of database state.

Common backup concepts:

Full backup
    Complete database backup.

Incremental backup
    Changes since a previous backup.

Differential backup
    Changes since a full backup.

Point-in-time recovery
    Restore the database to a particular moment using backups and
    transaction logs where supported.

Two important operational concepts:

RPO:
    Recovery Point Objective.
    How much data loss is acceptable.

RTO:
    Recovery Time Objective.
    How long recovery may take.
""")

# ============================================================
# SECTION 78: WRITE-AHEAD LOGGING
# ============================================================

print("\n" + "=" * 80)
print("WRITE-AHEAD LOGGING")
print("=" * 80)

print("""
Write-Ahead Logging, or WAL, records changes in a log before the
corresponding database pages are considered durably committed.

The general principle is:

log the intended change first
then persist the affected database state

Transaction logs are important for:

- durability
- crash recovery
- replication
- point-in-time recovery

Different database systems implement logging differently.
""")

# ============================================================
# SECTION 79: REPLICATION
# ============================================================

print("\n" + "=" * 80)
print("REPLICATION")
print("=" * 80)

print("""
Replication means maintaining copies of database data across
multiple database instances.

Common concepts:

Primary:
    Instance that accepts certain writes.

Replica:
    Instance maintaining a copy.

Synchronous replication:
    Stronger coordination before acknowledging writes.

Asynchronous replication:
    Replica may temporarily lag behind the primary.

Replication can support:

- high availability
- disaster recovery
- read scaling
- geographic distribution

Replication is not the same thing as backup.
""")

# ============================================================
# SECTION 80: PARTITIONING
# ============================================================

print("\n" + "=" * 80)
print("PARTITIONING")
print("=" * 80)

print("""
Partitioning divides a large logical table into smaller physical
partitions.

Common strategies:

Range partitioning
    Partition by ranges such as dates.

List partitioning
    Partition by specified values.

Hash partitioning
    Partition using a hash function.

Partitioning can improve manageability and performance for large
datasets when queries align with the partitioning strategy.

Partitioning is different from sharding.

Partitioning usually occurs within a database system.

Sharding distributes data across multiple database nodes.
""")

# ============================================================
# SECTION 81: SHARDING
# ============================================================

print("\n" + "=" * 80)
print("SHARDING")
print("=" * 80)

print("""
Sharding divides data across multiple database servers.

Example:

Customer IDs 1-1,000,000
    -> shard A

Customer IDs 1,000,001-2,000,000
    -> shard B

A shard key determines where a record belongs.

A poor shard key can cause:

- hotspots
- uneven storage
- difficult rebalancing
- expensive cross-shard queries
""")

# ============================================================
# SECTION 82: DISTRIBUTED DATABASES
# ============================================================

print("\n" + "=" * 80)
print("DISTRIBUTED DATABASES")
print("=" * 80)

print("""
A distributed database stores or processes data across multiple
networked nodes.

Distributed systems introduce challenges such as:

- network failures
- latency
- partial failure
- clock differences
- replication lag
- consistency trade-offs
- distributed transactions
- partitioning
- leader election

A local database can often assume direct access to storage.

A distributed database must reason about the network as part of
the system.
""")

# ============================================================
# SECTION 83: CONSISTENCY MODELS
# ============================================================

print("\n" + "=" * 80)
print("CONSISTENCY")
print("=" * 80)

print("""
Strong consistency means reads observe results according to a
strong ordering guarantee.

Eventual consistency means replicas may temporarily disagree but
converge if updates stop.

Distributed systems often choose consistency characteristics
according to application requirements.

Consistency is not simply a binary choice between "consistent"
and "inconsistent."

There are different consistency models and guarantees.
""")

# ============================================================
# SECTION 84: RELATIONAL ALGEBRA
# ============================================================

print("\n" + "=" * 80)
print("RELATIONAL ALGEBRA")
print("=" * 80)

print("""
Relational algebra provides formal operations over relations.

Important operations include:

Selection
    Filters rows.

Projection
    Selects attributes.

Join
    Combines related relations.

Union
    Combines compatible relations.

Difference
    Finds rows present in one relation but not another.

Cartesian product
    Produces combinations of rows.

Relational algebra provides a mathematical foundation for relational
query processing.
""")

# ============================================================
# SECTION 85: JOIN CARDINALITY
# ============================================================

print("\n" + "=" * 80)
print("JOIN CARDINALITY")
print("=" * 80)

print("""
Join cardinality describes how many rows can result from combining
two relations.

If a customer has five orders, joining the customer to orders
produces five rows for that customer.

Joining two one-to-many relationships without understanding their
multiplication can create unexpectedly large result sets.

For example:

customers
    1 -> many orders

orders
    1 -> many order_items

Joining all three can produce one row per order item.

Understanding cardinality is essential for:

- correct reports
- avoiding duplicate counts
- query optimization
- schema design
""")

# ============================================================
# SECTION 86: COUNTING WITH JOINS
# ============================================================

print("\n" + "=" * 80)
print("COUNTING WITH JOINS")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        d.department_name,
        COUNT(e.employee_id) AS employee_count
    FROM departments AS d
    LEFT JOIN employees AS e
        ON e.department_id = d.department_id
    GROUP BY d.department_id, d.department_name
    ORDER BY d.department_id
    """
).fetchall()

for row in rows:
    print(row)

print("""
COUNT(*) and COUNT(column) can behave differently with outer joins.

COUNT(*) counts result rows.

COUNT(e.employee_id) counts only non-null employee IDs.

This distinction is important when preserving unmatched rows with
LEFT JOIN.
""")

# ============================================================
# SECTION 87: TEMPORARY TABLES
# ============================================================

print("\n" + "=" * 80)
print("TEMPORARY TABLES")
print("=" * 80)

connection.execute(
    """
    CREATE TEMP TABLE high_salary_employees AS
    SELECT employee_id, employee_name, salary
    FROM employees
    WHERE salary >= 80000
    """
)

rows = connection.execute(
    """
    SELECT *
    FROM high_salary_employees
    """
).fetchall()

print(rows)

print("""
Temporary tables can store intermediate results for a session or
transaction depending on database behavior.

They can be useful for:

- complex data processing
- staging
- multi-step transformations
- procedural workflows

They should not automatically replace CTEs or well-designed
queries.
""")

# ============================================================
# SECTION 88: QUERY OPTIMIZATION
# ============================================================

print("\n" + "=" * 80)
print("QUERY OPTIMIZATION")
print("=" * 80)

print("""
Query optimization involves selecting efficient execution strategies.

Important factors include:

- indexes
- filtering
- join order
- cardinality
- selectivity
- statistics
- sorting
- aggregation
- data volume
- network transfer
- disk I/O
- memory

A query that is fast on 10,000 rows may become slow on 100 million
rows.

Performance must therefore be considered relative to data volume
and workload.
""")

# ============================================================
# SECTION 89: SARGABILITY
# ============================================================

print("\n" + "=" * 80)
print("SARGABILITY")
print("=" * 80)

print("""
A predicate is often described as sargable when the database can
use an index effectively for the search condition.

Conceptually:

WHERE salary = 50000

is more directly index-friendly than expressions that transform
the indexed column unnecessarily.

For example:

WHERE function(salary) = ...

may prevent efficient index use depending on the database.

The exact optimization behavior depends on the database engine and
available indexes.
""")

# ============================================================
# SECTION 90: QUERY DESIGN
# ============================================================

print("\n" + "=" * 80)
print("QUERY DESIGN PRINCIPLES")
print("=" * 80)

print("""
A well-designed query should:

- express the required business logic clearly
- return only necessary columns
- filter appropriately
- use correct join conditions
- avoid accidental Cartesian products
- use indexes where justified
- respect transaction boundaries
- handle NULL correctly
- account for data volume
- use parameters for external values
""")

# ============================================================
# SECTION 91: CARTESIAN PRODUCT
# ============================================================

print("\n" + "=" * 80)
print("CARTESIAN PRODUCT")
print("=" * 80)

print("""
A Cartesian product combines every row of one relation with every
row of another.

If table A has 100 rows and table B has 1,000 rows:

100 x 1,000 = 100,000 combinations

A Cartesian product may be intentional in some analytical queries,
but accidental Cartesian products are a common source of performance
and correctness problems.
""")

# ============================================================
# SECTION 92: DATABASE TESTING
# ============================================================

print("\n" + "=" * 80)
print("DATABASE TESTING")
print("=" * 80)

print("""
Database testing can verify:

Schema correctness
------------------
Are tables and columns defined correctly?

Constraint correctness
----------------------
Are invalid records rejected?

Query correctness
-----------------
Does the query return the expected result?

Transaction correctness
------------------------
Do operations commit and roll back correctly?

Concurrency behavior
---------------------
Does the system behave correctly under simultaneous operations?

Migration correctness
---------------------
Can the schema move between versions safely?

Performance behavior
--------------------
Does the query remain acceptable at realistic data volumes?
""")

# ============================================================
# SECTION 93: DATA INTEGRITY
# ============================================================

print("\n" + "=" * 80)
print("DATA INTEGRITY")
print("=" * 80)

print("""
Entity integrity:
    Every row should have a valid unique identifier.

Referential integrity:
    Foreign-key relationships should point to valid records.

Domain integrity:
    Attribute values should satisfy their allowed rules.

User-defined integrity:
    Business-specific rules should be enforced where appropriate.

Database constraints are one of the strongest mechanisms for
protecting integrity because they operate at the data layer.
""")

# ============================================================
# SECTION 94: APPLICATION VALIDATION VS DATABASE VALIDATION
# ============================================================

print("\n" + "=" * 80)
print("APPLICATION VS DATABASE VALIDATION")
print("=" * 80)

print("""
Application validation provides:

- user-friendly error messages
- early feedback
- interface-specific rules

Database validation provides:

- centralized integrity
- protection against multiple applications
- protection against accidental direct writes
- consistent enforcement

A robust system commonly uses both.

Application validation improves usability.

Database constraints protect correctness.
""")

# ============================================================
# SECTION 95: E-COMMERCE DATA MODEL
# ============================================================

print("\n" + "=" * 80)
print("E-COMMERCE DATABASE MODEL")
print("=" * 80)

print("""
A simplified e-commerce system might contain:

customers
---------
customer_id
name
email

products
--------
product_id
name
price

orders
------
order_id
customer_id
order_date
status

order_items
-----------
order_id
product_id
quantity
unit_price

payments
--------
payment_id
order_id
amount
status

inventory
---------
product_id
quantity

Relationships:

customer 1 ---- N orders

order 1 ---- N order_items

product 1 ---- N order_items

order 1 ---- N payments

product 1 ---- 1 inventory record
""")

# ============================================================
# SECTION 96: SNAPSHOT VALUES
# ============================================================

print("\n" + "=" * 80)
print("SNAPSHOT VALUES")
print("=" * 80)

print("""
Suppose a product currently costs 1,500.

An order was placed when the product cost 1,200.

The order should normally preserve the historical transaction
price rather than calculating it from the current product price.

Therefore:

products.price
    represents current product pricing.

order_items.unit_price
    represents the price applicable to the historical transaction.

This is an example where storing a value that appears redundant
is necessary because it represents a different business fact.
""")

# ============================================================
# SECTION 97: GENERATED IDENTIFIERS
# ============================================================

print("\n" + "=" * 80)
print("SURROGATE IDENTIFIERS")
print("=" * 80)

print("""
A surrogate key is an artificial identifier.

Example:

employee_id = 101

Advantages:

- compact
- stable
- easy to reference
- independent of business meaning

A natural key may change because business rules change.

For example, an email address may look unique but can change.

Using email as the primary identifier can therefore create
unnecessary coupling.
""")

# ============================================================
# SECTION 98: DATABASE DESIGN PROCESS
# ============================================================

print("\n" + "=" * 80)
print("DATABASE DESIGN")
print("=" * 80)

print("""
A relational database design begins with understanding the business
domain.

Typical reasoning process:

1. Identify entities.
2. Identify attributes.
3. Identify relationships.
4. Identify candidate keys.
5. Select primary keys.
6. Define foreign keys.
7. Define constraints.
8. Analyze functional dependencies.
9. Normalize where appropriate.
10. Consider access patterns.
11. Create indexes based on actual requirements.
12. Define transaction boundaries.
13. Consider security.
14. Consider backup and recovery requirements.
15. Test realistic workloads.
""")

# ============================================================
# SECTION 99: SCHEMA EVOLUTION
# ============================================================

print("\n" + "=" * 80)
print("SCHEMA EVOLUTION")
print("=" * 80)

print("""
A database schema changes as software changes.

Examples:

Version 1:
    users(name)

Version 2:
    users(first_name, last_name)

Version 3:
    users(first_name, last_name, created_at)

Schema evolution must consider:

- existing data
- application compatibility
- migration duration
- indexes
- constraints
- rollback strategy
- deployment ordering
""")

# ============================================================
# SECTION 100: BACKWARD COMPATIBILITY
# ============================================================

print("\n" + "=" * 80)
print("BACKWARD COMPATIBILITY")
print("=" * 80)

print("""
During a rolling deployment, old and new application versions may
temporarily run simultaneously.

A database migration should therefore often be designed so that
both versions can operate safely during the transition.

A common strategy is:

1. Add new structure.
2. Deploy application support.
3. Backfill data.
4. Switch reads and writes.
5. Remove obsolete structure later.

This avoids requiring every application instance to change at
exactly the same instant.
""")

# ============================================================
# SECTION 101: STORED PROCEDURES
# ============================================================

print("\n" + "=" * 80)
print("STORED PROCEDURES AND FUNCTIONS")
print("=" * 80)

print("""
Many database systems support stored procedures and functions.

A stored procedure can encapsulate database-side operations.

A function can calculate or return a value.

Advantages can include:

- centralized database logic
- reduced network round trips
- controlled interfaces

Disadvantages can include:

- vendor-specific syntax
- deployment complexity
- logic split between application and database
- testing complexity

SQLite does not provide stored procedures in the same way as
systems such as PostgreSQL, SQL Server, or Oracle.
""")

# ============================================================
# SECTION 102: DATABASE OBSERVABILITY
# ============================================================

print("\n" + "=" * 80)
print("DATABASE OBSERVABILITY")
print("=" * 80)

print("""
Database observability involves understanding database behavior
through measurable signals.

Useful metrics include:

- query latency
- throughput
- transaction rate
- connection count
- lock waits
- cache efficiency
- disk usage
- replication lag
- error rate
- slow queries

Observability allows database problems to be investigated using
evidence rather than assumptions.
""")

# ============================================================
# SECTION 103: SLOW QUERIES
# ============================================================

print("\n" + "=" * 80)
print("SLOW QUERY INVESTIGATION")
print("=" * 80)

print("""
A systematic investigation may involve:

1. Identify the slow query.
2. Measure execution time.
3. Inspect the query plan.
4. Examine indexes.
5. Examine row counts.
6. Examine cardinality.
7. Check filtering selectivity.
8. Check join behavior.
9. Check sorting and aggregation.
10. Check database resource usage.
11. Compare estimated and actual behavior where supported.
12. Test changes against realistic data.

Adding an index without understanding the workload is not always
the correct solution.
""")

# ============================================================
# SECTION 104: DATABASE ANTI-PATTERNS
# ============================================================

print("\n" + "=" * 80)
print("COMMON DATABASE ANTI-PATTERNS")
print("=" * 80)

print("""
Common problems include:

1. Storing comma-separated lists in relational columns.

2. Using SELECT * everywhere.

3. Missing foreign keys.

4. Missing constraints.

5. Using application code to enforce every integrity rule.

6. Creating indexes on every column.

7. Using indexes without analyzing query patterns.

8. Ignoring NULL semantics.

9. Using DISTINCT to hide duplicate rows caused by incorrect joins.

10. Performing N+1 queries.

11. Keeping transactions open for too long.

12. Storing passwords as plain text.

13. Building SQL through string concatenation.

14. Using a natural key without considering stability.

15. Storing derived data without defining consistency rules.

16. Ignoring migration compatibility.

17. Assuming replication is a substitute for backup.

18. Assuming database scaling is solved by adding indexes alone.
""")

# ============================================================
# SECTION 105: DATABASE DIALECTS
# ============================================================

print("\n" + "=" * 80)
print("SQL DIALECTS")
print("=" * 80)

print("""
SQL is standardized, but database systems implement different
dialects and features.

Differences may exist in:

- data types
- pagination syntax
- date functions
- JSON functions
- UPSERT syntax
- procedural languages
- stored procedures
- indexing
- generated columns
- identity columns
- recursive queries
- locking behavior

Common SQL systems include:

PostgreSQL
MySQL
SQL Server
Oracle
SQLite

SQL knowledge transfers across systems, but production SQL must
respect the target database's dialect.
""")

# ============================================================
# SECTION 106: DATABASE ENGINE
# ============================================================

print("\n" + "=" * 80)
print("DATABASE ENGINE")
print("=" * 80)

print("""
The database engine is responsible for implementing database
operations.

Major internal responsibilities can include:

- parsing SQL
- optimizing queries
- executing query plans
- managing storage
- maintaining indexes
- enforcing constraints
- managing transactions
- concurrency control
- logging
- recovery
""")

# ============================================================
# SECTION 107: QUERY PROCESSING
# ============================================================

print("\n" + "=" * 80)
print("QUERY PROCESSING")
print("=" * 80)

print("""
A simplified query-processing pipeline is:

SQL text
   |
Parser
   |
Parsed representation
   |
Optimizer
   |
Execution plan
   |
Execution engine
   |
Storage/index access
   |
Result

The optimizer attempts to choose an efficient plan based on
available information and cost estimates.
""")

# ============================================================
# SECTION 108: COST-BASED OPTIMIZATION
# ============================================================

print("\n" + "=" * 80)
print("COST-BASED OPTIMIZATION")
print("=" * 80)

print("""
Many database optimizers use cost estimates.

Possible cost components include:

- disk I/O
- CPU
- memory
- number of rows
- sorting
- join operations
- index access
- network transfer

The optimizer compares possible execution strategies and selects
one it estimates to be efficient.

Statistics help the optimizer estimate data distribution.
""")

# ============================================================
# SECTION 109: DATABASE STATISTICS
# ============================================================

print("\n" + "=" * 80)
print("DATABASE STATISTICS")
print("=" * 80)

print("""
Database statistics describe data characteristics such as:

- row counts
- value distribution
- distinct values
- selectivity
- index distribution

Optimizers use statistics when deciding between execution plans.

Outdated statistics can lead to poor estimates and poor plans.
""")

# ============================================================
# SECTION 110: NORMALIZED VS DENORMALIZED DESIGN
# ============================================================

print("\n" + "=" * 80)
print("NORMALIZED VS DENORMALIZED")
print("=" * 80)

print("""
Normalized design emphasizes:

- reduced redundancy
- integrity
- maintainability
- fewer update anomalies

Denormalized design emphasizes:

- read efficiency
- fewer joins
- reporting convenience
- precomputed values

Neither approach is universally superior.

The correct design depends on:

- workload
- data size
- consistency requirements
- query patterns
- write frequency
- reporting requirements
""")

# ============================================================
# SECTION 111: DATA LIFECYCLE
# ============================================================

print("\n" + "=" * 80)
print("DATA LIFECYCLE")
print("=" * 80)

print("""
Data generally passes through stages such as:

creation
    |
storage
    |
processing
    |
usage
    |
archival
    |
deletion

Database design must consider how data behaves throughout its
lifecycle.

Retention requirements may require historical storage.

Privacy requirements may require controlled deletion.

Operational requirements may require archival.
""")

# ============================================================
# SECTION 112: DATABASE ADMINISTRATOR
# ============================================================

print("\n" + "=" * 80)
print("DATABASE ADMINISTRATION")
print("=" * 80)

print("""
Database administration may include:

- installation
- configuration
- user management
- permissions
- backup
- recovery
- monitoring
- performance tuning
- capacity planning
- replication
- upgrades
- patching
- security
- disaster recovery

The exact responsibilities depend on the organization's
architecture and operating model.
""")

# ============================================================
# SECTION 113: DATABASE SECURITY PRINCIPLES
# ============================================================

print("\n" + "=" * 80)
print("DATABASE SECURITY PRINCIPLES")
print("=" * 80)

print("""
Important security principles include:

Least privilege
---------------
Users and services receive only required permissions.

Defense in depth
----------------
Multiple security controls are used.

Separation of duties
--------------------
Critical responsibilities are distributed.

Secure credential handling
--------------------------
Credentials should be protected and rotated.

Encryption
----------
Sensitive data should be protected appropriately.

Auditing
--------
Important activities should be traceable.

Parameterized SQL
-----------------
External data should not be interpreted as SQL instructions.
""")

# ============================================================
# SECTION 114: DATA MODELING
# ============================================================

print("\n" + "=" * 80)
print("DATA MODELING")
print("=" * 80)

print("""
Data modeling converts business requirements into structured
representations.

Conceptual model:
    High-level business entities and relationships.

Logical model:
    Detailed attributes, relationships, keys, and constraints.

Physical model:
    Database-specific implementation involving data types,
    indexes, partitions, storage structures, and performance choices.
""")

# ============================================================
# SECTION 115: ENTITY-RELATIONSHIP MODEL
# ============================================================

print("\n" + "=" * 80)
print("ENTITY-RELATIONSHIP MODEL")
print("=" * 80)

print("""
An ER model describes:

Entities:
    Objects or concepts of interest.

Attributes:
    Properties of entities.

Relationships:
    Associations between entities.

Example:

Customer
    |
    | places
    |
Order
    |
    | contains
    |
OrderItem
    |
    | references
    |
Product
""")

# ============================================================
# SECTION 116: OPTIONALITY
# ============================================================

print("\n" + "=" * 80)
print("RELATIONSHIP OPTIONALITY")
print("=" * 80)

print("""
Relationships can be optional or mandatory.

Example:

An employee may or may not have a manager.

That can be represented by:

manager_id NULL

An employee must belong to a department.

That can be represented by:

department_id NOT NULL

Optionality is part of the business meaning encoded in the schema.
""")

# ============================================================
# SECTION 117: REFERENTIAL ACTIONS
# ============================================================

print("\n" + "=" * 80)
print("REFERENTIAL ACTIONS")
print("=" * 80)

print("""
Foreign keys can define behavior when referenced records change.

Common actions include:

CASCADE
SET NULL
SET DEFAULT
RESTRICT
NO ACTION

Example:

ON DELETE CASCADE

can cause child rows to be deleted when the parent is deleted.

Cascade behavior must be chosen carefully because deleting one
record can then affect many related records.
""")

# ============================================================
# SECTION 118: PRACTICAL REPORT QUERY
# ============================================================

print("\n" + "=" * 80)
print("PRACTICAL REPORT")
print("=" * 80)

rows = connection.execute(
    """
    SELECT
        d.department_name,
        COUNT(e.employee_id) AS employees,
        ROUND(AVG(e.salary), 2) AS average_salary,
        MAX(e.salary) AS highest_salary
    FROM departments AS d
    LEFT JOIN employees AS e
        ON e.department_id = d.department_id
    GROUP BY
        d.department_id,
        d.department_name
    ORDER BY
        average_salary DESC
    """
).fetchall()

for row in rows:
    print(row)

print("""
This query combines:

- LEFT JOIN
- COUNT
- AVG
- MAX
- GROUP BY
- ORDER BY

It demonstrates how database fundamentals combine to answer a
business question.
""")

# ============================================================
# SECTION 119: TRANSACTIONAL THINKING
# ============================================================

print("\n" + "=" * 80)
print("TRANSACTIONAL THINKING")
print("=" * 80)

print("""
A database transaction should represent a meaningful unit of
business consistency.

Examples:

Bank transfer:
    debit + credit

Order creation:
    order + order items

Inventory reservation:
    reserve inventory + create reservation record

Employee creation:
    employee + required related records

The important question is not merely:

"Which SQL statements should run?"

The deeper question is:

"Which changes must succeed or fail together?"
""")

# ============================================================
# SECTION 120: DATABASE THINKING
# ============================================================

print("\n" + "=" * 80)
print("DATABASE THINKING")
print("=" * 80)

print("""
Database fundamentals involve more than memorizing SQL syntax.

A database professional must reason about:

DATA
----
What information exists?

IDENTITY
--------
How is each entity uniquely identified?

RELATIONSHIPS
-------------
How are entities connected?

INTEGRITY
---------
What values and relationships are valid?

TRANSACTIONS
------------
Which changes must happen together?

CONCURRENCY
-----------
What happens when operations occur simultaneously?

PERFORMANCE
-----------
How will the system behave as data grows?

SECURITY
--------
Who can access or modify the data?

RECOVERY
--------
What happens after failure?

SCALABILITY
-----------
What happens when the workload becomes larger?

These questions form the practical foundation of database design.
""")

# ============================================================
# SECTION 121: FINAL TECHNICAL TERMINOLOGY
# ============================================================

print("\n" + "=" * 80)
print("DATABASE TERMINOLOGY")
print("=" * 80)

print("""
Database
    Organized collection of data.

DBMS
    Software for managing databases.

RDBMS
    Database management system based on the relational model.

Table
    Relation represented as rows and columns.

Row
    Individual record.

Column
    Attribute.

Schema
    Database structure.

Primary key
    Principal unique identifier.

Foreign key
    Reference to a key in another table.

Candidate key
    Minimal unique identifier.

Composite key
    Key containing multiple attributes.

Constraint
    Rule protecting data integrity.

Index
    Data structure supporting efficient access.

Query
    Request for database information or modification.

Transaction
    Logical unit of database work.

ACID
    Atomicity, Consistency, Isolation, Durability.

Normalization
    Structured reduction of redundancy and dependency problems.

Denormalization
    Intentional redundancy for specific reasons.

Join
    Operation combining related records.

Aggregation
    Combining rows into calculated results.

View
    Stored query definition.

Trigger
    Automatic database-side event action.

CTE
    Named query expression using WITH.

OLTP
    Operational transaction processing.

OLAP
    Analytical processing.

ETL
    Extract, Transform, Load.

ELT
    Extract, Load, Transform.

Replication
    Maintaining copies of data across database instances.

Partitioning
    Dividing a logical table into physical partitions.

Sharding
    Distributing data across database nodes.

Cardinality
    Quantity or distinctness of data depending on context.

Selectivity
    Degree to which a condition filters rows.

Query plan
    Execution strategy chosen for a query.

Deadlock
    Circular waiting between transactions.

Idempotency
    Ability to safely repeat a logical operation without producing
    unintended duplicate effects.
""")

# ============================================================
# CLOSE DATABASE
# ============================================================

connection.close()

print("\n" + "=" * 80)
print("DATABASE FUNDAMENTALS SCRIPT EXECUTION COMPLETE")
print("=" * 80)
