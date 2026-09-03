"""
RELATIONAL DATABASE CONCEPTS
============================

Topics covered:
    1. What is a database?
    2. What is a relational database?
    3. Relational model
    4. Relations
    5. Tuples
    6. Attributes
    7. Domains
    8. Relation schema
    9. Relation instances
    10. Degree and cardinality
    11. NULL values
    12. Keys
    13. Primary keys
    14. Candidate keys
    15. Super keys
    16. Foreign keys
    17. Composite keys
    18. Integrity constraints
    19. Entity integrity
    20. Referential integrity
    21. Relational algebra
    22. Selection
    23. Projection
    24. Union
    25. Intersection
    26. Difference
    27. Cartesian product
    28. Rename
    29. Join
    30. Natural join
    31. Theta join
    32. Equi join
    33. Outer joins
    34. Relational algebra vs SQL
    35. SQL basics
    36. PostgreSQL concepts
    37. PostgreSQL data types
    38. PostgreSQL constraints
    39. PostgreSQL schemas
    40. PostgreSQL indexes
    41. Transactions
    42. ACID properties
    43. Normalization concepts
    44. Functional dependencies
    45. 1NF, 2NF, 3NF and BCNF
    46. Query optimization concepts
    47. EXPLAIN and EXPLAIN ANALYZE
    48. Views
    49. CTEs
    50. Window functions
    51. PostgreSQL-specific features
    52. Practical relational database design
    53. Advanced PostgreSQL concepts

IMPORTANT:
    - The examples below use SQLite for a zero-setup executable demonstration.
    - PostgreSQL SQL syntax/examples are included separately.
    - PostgreSQL is the target relational database system for this topic.
    - SQLite and PostgreSQL are both relational databases, but they are not identical.
"""

# =============================================================================
# SECTION 1: WHAT IS A DATABASE?
# =============================================================================

"""
A database is an organized collection of data.

For example, a college may need to store:

    Students
    Courses
    Teachers
    Departments
    Enrollments
    Exams
    Results

Instead of storing this information in random files, a database provides
structured storage and mechanisms for:

    - inserting data
    - retrieving data
    - updating data
    - deleting data
    - enforcing rules
    - controlling access
    - maintaining consistency
    - handling concurrent users
    - recovering from failures

A Database Management System (DBMS) is software that manages databases.

Examples:

    PostgreSQL
    MySQL
    Microsoft SQL Server
    Oracle Database
    SQLite

PostgreSQL is an advanced open-source object-relational database management
system with strong SQL support, transactions, indexing, extensibility,
concurrency control, JSON support, window functions, CTEs, and many other
features.
"""


# =============================================================================
# SECTION 2: WHAT IS A RELATIONAL DATABASE?
# =============================================================================

"""
A relational database organizes information into relations.

In practical database terminology, a relation is commonly represented as
a table.

Example:

    STUDENT

    student_id | name       | age | department
    -----------+------------+-----+-----------
    1          | Rahul      | 21  | CSE
    2          | Priya      | 22  | ECE
    3          | Amit       | 20  | CSE

The relational model was introduced by Edgar F. Codd.

The central idea is:

    Data is represented mathematically as relations.

A table is the practical SQL representation of a relation.

Important distinction:

    Relation        -> theoretical relational-model concept
    Table           -> practical SQL implementation concept

They are closely related but not necessarily perfectly identical in every
technical sense.
"""


# =============================================================================
# SECTION 3: RELATION
# =============================================================================

"""
A relation consists of:

    - a relation schema
    - a relation instance

Example schema:

    STUDENT(student_id, name, age, department)

This tells us the structure of the relation.

A relation instance contains the actual rows at a particular moment.

Example instance:

    (1, "Rahul", 21, "CSE")
    (2, "Priya", 22, "ECE")
    (3, "Amit", 20, "CSE")

The database changes its relation instances as records are inserted,
updated, or deleted.
"""


# =============================================================================
# SECTION 4: TUPLES
# =============================================================================

"""
A tuple is a single row in a relation.

Example:

    STUDENT

    student_id | name  | age | department
    -----------+-------+-----+-----------
    1          | Rahul | 21  | CSE

The tuple is:

    (1, "Rahul", 21, "CSE")

Therefore:

    Table/relation -> collection of tuples
    Tuple          -> one record/row

In mathematical terminology, a tuple is an ordered collection of values.
"""


# =============================================================================
# SECTION 5: ATTRIBUTES
# =============================================================================

"""
An attribute corresponds to a column.

For:

    STUDENT(student_id, name, age, department)

The attributes are:

    student_id
    name
    age
    department

Therefore:

    Attribute -> column
    Tuple     -> row

Example:

    student_id | name  | age
    -----------+-------+----
    1          | Rahul | 21

Here:

    student_id, name and age are attributes.

Each attribute describes a particular property of the entity being stored.
"""


# =============================================================================
# SECTION 6: DOMAINS
# =============================================================================

"""
A domain defines the set of valid values that an attribute can contain.

For example:

    age:
        positive integer

    department:
        {"CSE", "ECE", "ME", "CE"}

    gender:
        {"Male", "Female", "Other"}

    salary:
        non-negative numeric values

Conceptually:

    Domain = allowed set of values for an attribute.

In SQL, data types and constraints help implement domain restrictions.

Example PostgreSQL:

    age INTEGER CHECK (age >= 0)

    department VARCHAR(20)

    salary NUMERIC(12,2) CHECK (salary >= 0)

The SQL type determines the general type of value, while constraints can
restrict the permitted values further.
"""


# =============================================================================
# SECTION 7: RELATION SCHEMA
# =============================================================================

"""
A relation schema describes the structure of a relation.

Example:

    STUDENT(
        student_id,
        name,
        age,
        department
    )

A more SQL-like schema:

    CREATE TABLE student (
        student_id INTEGER,
        name VARCHAR(100),
        age INTEGER,
        department VARCHAR(50)
    );

The schema defines:

    - relation name
    - attributes
    - data types
    - constraints
    - relationships
"""


# =============================================================================
# SECTION 8: DEGREE AND CARDINALITY
# =============================================================================

"""
Two important relational terms:

DEGREE
------
The number of attributes/columns in a relation.

Example:

    STUDENT(student_id, name, age, department)

Degree = 4


CARDINALITY
-----------
The number of tuples/rows in a relation.

Example:

    100 students

Cardinality = 100


Remember:

    Degree     -> columns
    Cardinality -> rows
"""


# =============================================================================
# SECTION 9: NULL
# =============================================================================

"""
NULL is one of the most important concepts in SQL.

NULL generally represents:

    - unknown value
    - missing value
    - not applicable value

NULL is NOT:

    0
    ""
    False

Example:

    student_id | name  | phone
    -----------+-------+--------
    1          | Rahul | NULL

The phone number is unknown or unavailable.

IMPORTANT:

Do not write:

    WHERE phone = NULL

Instead write:

    WHERE phone IS NULL

And:

    WHERE phone IS NOT NULL

SQL uses three-valued logic:

    TRUE
    FALSE
    UNKNOWN

This is one reason NULL behavior can be surprising.
"""


# =============================================================================
# SECTION 10: KEYS
# =============================================================================

"""
Keys identify tuples and establish relationships.

Important types:

    1. Super key
    2. Candidate key
    3. Primary key
    4. Alternate key
    5. Foreign key
    6. Composite key


SUPER KEY
---------

Any set of attributes that uniquely identifies a tuple.

Suppose:

    STUDENT(student_id, email, name)

If student_id is unique:

    {student_id}

is a super key.

If email is unique:

    {email}

is also a super key.

The combination:

    {student_id, name}

could also be a super key, even though name is unnecessary.


CANDIDATE KEY
-------------

A minimal super key.

If both student_id and email individually identify a student:

    student_id
    email

can both be candidate keys.


PRIMARY KEY
-----------

One candidate key selected as the main identifier.

Example:

    PRIMARY KEY(student_id)


ALTERNATE KEY
-------------

A candidate key that was not selected as the primary key.


FOREIGN KEY
-----------

An attribute that references a key in another relation.

Example:

    STUDENT(student_id, name)

    ENROLLMENT(student_id, course_id)

    ENROLLMENT.student_id
        references
    STUDENT.student_id


COMPOSITE KEY
-------------

A key made from multiple attributes.

Example:

    ENROLLMENT(student_id, course_id)

The combination:

    (student_id, course_id)

may uniquely identify one enrollment.
"""


# =============================================================================
# SECTION 11: INTEGRITY CONSTRAINTS
# =============================================================================

"""
Constraints protect data quality.

Important SQL constraints:

    PRIMARY KEY
    FOREIGN KEY
    UNIQUE
    NOT NULL
    CHECK
    DEFAULT

Example:

    CREATE TABLE employee (
        employee_id INTEGER PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        age INTEGER CHECK (age >= 18),
        salary NUMERIC(12,2) DEFAULT 0
    );


ENTITY INTEGRITY
----------------

A primary key:

    - must uniquely identify each row
    - cannot be NULL


REFERENTIAL INTEGRITY
---------------------

A foreign-key value must refer to a valid referenced key, unless the
foreign-key column permits NULL and the value is NULL.

Example:

    employee.department_id

must reference a valid:

    department.department_id
"""


# =============================================================================
# SECTION 12: PRACTICAL DATABASE EXAMPLE
# =============================================================================

import sqlite3


def create_demo_database():
    """
    Creates an in-memory relational database.

    SQLite is used only so this educational script can run without requiring
    a PostgreSQL server.
    """

    connection = sqlite3.connect(":memory:")

    # Enforce foreign-key constraints in SQLite.
    connection.execute("PRAGMA foreign_keys = ON")

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE department (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE student (
            student_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER CHECK (age >= 0),
            department_id INTEGER,
            email TEXT UNIQUE,
            FOREIGN KEY (department_id)
                REFERENCES department(department_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE course (
            course_id INTEGER PRIMARY KEY,
            course_name TEXT NOT NULL,
            credits INTEGER CHECK (credits > 0)
        )
    """)

    cursor.execute("""
        CREATE TABLE enrollment (
            student_id INTEGER,
            course_id INTEGER,
            enrollment_date TEXT,
            grade TEXT,

            PRIMARY KEY (student_id, course_id),

            FOREIGN KEY (student_id)
                REFERENCES student(student_id),

            FOREIGN KEY (course_id)
                REFERENCES course(course_id)
        )
    """)

    cursor.executemany("""
        INSERT INTO department
        VALUES (?, ?)
    """, [
        (1, "Computer Science"),
        (2, "Electronics"),
        (3, "Mechanical Engineering")
    ])

    cursor.executemany("""
        INSERT INTO student
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, "Rahul", 21, 1, "rahul@example.com"),
        (2, "Priya", 22, 2, "priya@example.com"),
        (3, "Amit", 20, 1, "amit@example.com"),
        (4, "Neha", 23, 3, "neha@example.com")
    ])

    cursor.executemany("""
        INSERT INTO course
        VALUES (?, ?, ?)
    """, [
        (101, "Database Systems", 4),
        (102, "Python Programming", 3),
        (103, "Machine Learning", 4)
    ])

    cursor.executemany("""
        INSERT INTO enrollment
        VALUES (?, ?, ?, ?)
    """, [
        (1, 101, "2026-01-10", "A"),
        (1, 102, "2026-01-11", "A+"),
        (2, 101, "2026-01-12", "B+"),
        (3, 101, "2026-01-13", "A"),
        (3, 103, "2026-01-14", "A+"),
        (4, 102, "2026-01-15", "B")
    ])

    connection.commit()

    return connection


# =============================================================================
# SECTION 13: BASIC SQL OPERATIONS
# =============================================================================

def basic_sql_examples(connection):
    cursor = connection.cursor()

    # SELECT
    print("\nALL STUDENTS")
    cursor.execute("""
        SELECT *
        FROM student
    """)

    for row in cursor.fetchall():
        print(row)

    # SELECT specific attributes
    print("\nSTUDENT NAMES")
    cursor.execute("""
        SELECT name
        FROM student
    """)

    for row in cursor.fetchall():
        print(row)

    # WHERE = relational algebra selection
    print("\nCSE STUDENTS")
    cursor.execute("""
        SELECT name
        FROM student
        WHERE department_id = 1
    """)

    for row in cursor.fetchall():
        print(row)

    # Multiple conditions
    print("\nSTUDENTS AGE >= 21")
    cursor.execute("""
        SELECT name, age
        FROM student
        WHERE age >= 21
    """)

    for row in cursor.fetchall():
        print(row)

    # ORDER BY
    print("\nSTUDENTS SORTED BY AGE")
    cursor.execute("""
        SELECT name, age
        FROM student
        ORDER BY age DESC
    """)

    for row in cursor.fetchall():
        print(row)

    # DISTINCT
    print("\nDEPARTMENTS REPRESENTED")
    cursor.execute("""
        SELECT DISTINCT department_id
        FROM student
    """)

    for row in cursor.fetchall():
        print(row)


# =============================================================================
# SECTION 14: RELATIONAL ALGEBRA
# =============================================================================

"""
Relational algebra is a formal query language for relational databases.

It provides operations for manipulating relations.

Core operations include:

    Selection
    Projection
    Union
    Set difference
    Cartesian product
    Rename

Derived/commonly discussed operations include:

    Join
    Intersection
    Division

SQL is declarative.

Relational algebra is procedural/formal in the sense that an expression
describes operations used to derive a result relation.

Example:

    Find students older than 21.

Relational algebra:

    σ age > 21 (STUDENT)

SQL:

    SELECT *
    FROM STUDENT
    WHERE age > 21;
"""


# =============================================================================
# SECTION 15: SELECTION
# =============================================================================

"""
SELECTION
---------

Symbol:

    σ

Purpose:

    Select rows satisfying a condition.

Example relation:

    STUDENT

    ID | Name  | Age
    ---+-------+----
    1  | Rahul | 21
    2  | Priya | 22
    3  | Amit  | 20

Selection:

    σ age > 20 (STUDENT)

Result:

    1 | Rahul | 21
    2 | Priya | 22

SQL:

    SELECT *
    FROM student
    WHERE age > 20;

Important:

    Selection filters ROWS.
"""


# =============================================================================
# SECTION 16: PROJECTION
# =============================================================================

"""
PROJECTION
----------

Symbol:

    π

Purpose:

    Select specific attributes/columns.

Example:

    π name, age (STUDENT)

SQL:

    SELECT name, age
    FROM student;

Important:

    Projection filters COLUMNS.

Memory trick:

    Selection -> rows
    Projection -> columns
"""


# =============================================================================
# SECTION 17: UNION
# =============================================================================

"""
UNION combines compatible relations.

Example:

    A = students from CSE
    B = students from ECE

A UNION B

SQL:

    SELECT name FROM cse_students
    UNION
    SELECT name FROM ece_students;

Relations must be union-compatible.

Typically:

    - same number of attributes
    - corresponding attributes have compatible domains/types

SQL UNION removes duplicates.

SQL UNION ALL retains duplicates.
"""


# =============================================================================
# SECTION 18: INTERSECTION
# =============================================================================

"""
Intersection finds tuples present in both relations.

Relational algebra:

    A ∩ B

PostgreSQL:

    SELECT ...
    FROM A
    INTERSECT
    SELECT ...
    FROM B;

Example:

Students who are both in one result set and another.
"""


# =============================================================================
# SECTION 19: DIFFERENCE
# =============================================================================

"""
Difference returns tuples present in the first relation but not the second.

Relational algebra:

    A - B

PostgreSQL:

    SELECT ...
    FROM A
    EXCEPT
    SELECT ...
    FROM B;

Example:

Students who enrolled in Database Systems but not Machine Learning.
"""


# =============================================================================
# SECTION 20: CARTESIAN PRODUCT
# =============================================================================

"""
Cartesian product combines every tuple of one relation with every tuple
of another relation.

Symbol:

    ×

If:

    A has 3 rows
    B has 4 rows

Then:

    A × B

has:

    3 * 4 = 12 rows

SQL:

    SELECT *
    FROM A
    CROSS JOIN B;

Cartesian products can become extremely large.

They are useful conceptually and sometimes operationally, but accidental
CROSS JOINs can be a major performance problem.
"""


# =============================================================================
# SECTION 21: RENAME
# =============================================================================

"""
Rename is represented by:

    ρ

It allows us to rename relations or attributes.

Example:

    ρ S(STUDENT)

SQL equivalent:

    SELECT ...
    FROM student AS s;

Aliases are especially important when joining a table to itself.

Example:

    SELECT
        e.employee_name,
        m.employee_name AS manager_name
    FROM employee e
    JOIN employee m
        ON e.manager_id = m.employee_id;
"""


# =============================================================================
# SECTION 22: JOINS
# =============================================================================

"""
A JOIN combines related tuples from two or more relations.

Example:

    STUDENT
        |
        | department_id
        v
    DEPARTMENT

SQL:

    SELECT
        s.name,
        d.department_name
    FROM student s
    JOIN department d
        ON s.department_id = d.department_id;


TYPES OF JOINS
--------------

INNER JOIN
    Returns matching rows.

LEFT JOIN
    Returns every row from the left relation and matching rows from the
    right relation.

RIGHT JOIN
    Returns every row from the right relation and matching rows from the
    left relation.

FULL OUTER JOIN
    Returns matching rows plus unmatched rows from both sides.

CROSS JOIN
    Cartesian product.

SELF JOIN
    A table joined to itself.
"""


# =============================================================================
# SECTION 23: INNER JOIN
# =============================================================================

def demonstrate_inner_join(connection):
    print("\nINNER JOIN")

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            s.name,
            d.department_name
        FROM student AS s
        INNER JOIN department AS d
            ON s.department_id = d.department_id
        ORDER BY s.name
    """)

    for row in cursor.fetchall():
        print(row)


# =============================================================================
# SECTION 24: LEFT JOIN
# =============================================================================

"""
LEFT JOIN is extremely important for analytics.

Example:

    SELECT
        d.department_name,
        s.name
    FROM department d
    LEFT JOIN student s
        ON d.department_id = s.department_id;

Every department appears, even if no student exists in that department.

This is different from INNER JOIN.
"""


# =============================================================================
# SECTION 25: THETA JOIN
# =============================================================================

"""
A theta join uses a general comparison operator:

    =
    <
    >
    <=
    >=
    <>

Example:

    SELECT *
    FROM A
    JOIN B
        ON A.value > B.value;

An equi-join is a theta join specifically using equality.
"""


# =============================================================================
# SECTION 26: NATURAL JOIN
# =============================================================================

"""
A NATURAL JOIN automatically joins columns with matching names.

Example:

    SELECT *
    FROM student
    NATURAL JOIN department;

Natural joins should be used carefully because the join condition is
implicitly determined from column names.

Explicit JOIN ... ON is usually clearer and safer in production SQL.
"""


# =============================================================================
# SECTION 27: RELATIONAL ALGEBRA TO SQL
# =============================================================================

"""
RELATIONAL ALGEBRA                SQL
------------------------------------------------------------

σ condition (R)                   SELECT * FROM R WHERE condition

π columns (R)                     SELECT columns FROM R

R ∪ S                             SELECT ... FROM R
                                  UNION
                                  SELECT ... FROM S

R ∩ S                             SELECT ... FROM R
                                  INTERSECT
                                  SELECT ... FROM S

R - S                             SELECT ... FROM R
                                  EXCEPT
                                  SELECT ... FROM S

R × S                             SELECT * FROM R CROSS JOIN S

R ⋈ S                             SELECT ... FROM R JOIN S ON ...

ρ alias(R)                        SELECT ... FROM R AS alias
"""


# =============================================================================
# SECTION 28: AGGREGATION
# =============================================================================

"""
Relational algebra traditionally focuses on core relational operations.
SQL also provides aggregation capabilities.

Common aggregate functions:

    COUNT()
    SUM()
    AVG()
    MIN()
    MAX()

Example:

    SELECT COUNT(*)
    FROM student;

GROUP BY creates groups.

Example:

    SELECT
        department_id,
        COUNT(*) AS student_count
    FROM student
    GROUP BY department_id;

HAVING filters groups.

Example:

    SELECT
        department_id,
        COUNT(*) AS student_count
    FROM student
    GROUP BY department_id
    HAVING COUNT(*) > 1;
"""


# =============================================================================
# SECTION 29: DATABASE NORMALIZATION
# =============================================================================

"""
Normalization is the process of organizing data to reduce redundancy and
avoid update anomalies.

Common normal forms:

    1NF
    2NF
    3NF
    BCNF
    4NF
    5NF

The most commonly encountered in practical relational database design are
1NF, 2NF and 3NF, with BCNF being an important stronger condition.


UPDATE ANOMALY
--------------

Changing the same fact in multiple rows can create inconsistent data.


INSERT ANOMALY
--------------

You may be unable to store a fact without storing unrelated information.


DELETE ANOMALY
--------------

Deleting one fact may accidentally remove another important fact.
"""


# =============================================================================
# SECTION 30: FIRST NORMAL FORM
# =============================================================================

"""
1NF generally requires:

    - atomic attribute values
    - no repeating groups
    - each field contains one logical value

Bad:

    student_id | name  | courses
    -----------+-------+--------------------
    1          | Rahul | SQL, Python, ML

Better:

    enrollment table:

    student_id | course
    -----------+--------
    1          | SQL
    1          | Python
    1          | ML
"""


# =============================================================================
# SECTION 31: SECOND NORMAL FORM
# =============================================================================

"""
2NF:

    - must already satisfy 1NF
    - every non-key attribute must depend on the whole candidate key

This matters particularly when the primary key is composite.

Suppose:

    ENROLLMENT(
        student_id,
        course_id,
        student_name,
        course_name,
        grade
    )

Primary key:

    (student_id, course_id)

student_name depends only on student_id.

course_name depends only on course_id.

Therefore they have partial dependencies.

A normalized design separates:

    STUDENT
    COURSE
    ENROLLMENT
"""


# =============================================================================
# SECTION 32: THIRD NORMAL FORM
# =============================================================================

"""
3NF:

    - must satisfy 2NF
    - non-key attributes should not depend transitively on another
      non-key attribute in the problematic sense described by 3NF.

Example:

    EMPLOYEE(
        employee_id,
        employee_name,
        department_id,
        department_name
    )

employee_id -> department_id
department_id -> department_name

Therefore:

employee_id -> department_name

through department_id.

A normalized design:

    EMPLOYEE(
        employee_id,
        employee_name,
        department_id
    )

    DEPARTMENT(
        department_id,
        department_name
    )
"""


# =============================================================================
# SECTION 33: FUNCTIONAL DEPENDENCY
# =============================================================================

"""
A functional dependency is written:

    X -> Y

Meaning:

    If two rows have the same X value, they must have the same Y value.

Example:

    student_id -> student_name

A student_id determines a student's name.

Functional dependencies are central to normalization theory.

They help determine:

    - candidate keys
    - redundancy
    - normal forms
    - schema decomposition
"""


# =============================================================================
# SECTION 34: BCNF
# =============================================================================

"""
Boyce-Codd Normal Form (BCNF) is stronger than 3NF.

A relation is in BCNF if:

    For every non-trivial functional dependency X -> Y,
    X is a super key.

BCNF is useful for identifying dependency structures that may still cause
redundancy even after satisfying 3NF.

Normalization is not simply "split every table as much as possible."

A good database design balances:

    - correctness
    - integrity
    - maintainability
    - query performance
    - simplicity
    - operational requirements
"""


# =============================================================================
# SECTION 35: POSTGRESQL
# =============================================================================

"""
PostgreSQL is a powerful open-source relational/object-relational DBMS.

It supports:

    SQL
    ACID transactions
    MVCC
    Foreign keys
    Constraints
    Indexes
    Views
    Materialized views
    CTEs
    Recursive CTEs
    Window functions
    JSON/JSONB
    Arrays
    Full-text search
    Extensions
    User-defined functions
    Triggers
    Partitioning
    Row-level security
    Advanced indexing
    Geographic extensions through external extensions such as PostGIS

PostgreSQL is commonly used for:

    - web applications
    - analytics
    - SaaS systems
    - financial systems
    - enterprise applications
    - data platforms
    - geospatial applications
    - machine-learning data infrastructure
"""


# =============================================================================
# SECTION 36: POSTGRESQL DATA TYPES
# =============================================================================

"""
Common PostgreSQL types:

INTEGER
BIGINT
NUMERIC
REAL
DOUBLE PRECISION
BOOLEAN
CHAR
VARCHAR
TEXT
DATE
TIME
TIMESTAMP
TIMESTAMPTZ
UUID
JSON
JSONB
ARRAY
BYTEA

Example:

    CREATE TABLE customer (
        customer_id BIGSERIAL PRIMARY KEY,
        customer_uuid UUID,
        name TEXT NOT NULL,
        age INTEGER CHECK (age >= 18),
        balance NUMERIC(15,2),
        active BOOLEAN DEFAULT TRUE,
        metadata JSONB,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );

TEXT vs VARCHAR:

PostgreSQL does not generally impose a performance advantage on VARCHAR
over TEXT merely because VARCHAR has a length declaration. Choose based
on semantic requirements.

NUMERIC is useful when exact decimal arithmetic is required, such as
financial values.
"""


# =============================================================================
# SECTION 37: POSTGRESQL SERIAL AND IDENTITY
# =============================================================================

"""
PostgreSQL historically used:

    SERIAL
    BIGSERIAL

for auto-generated integer identifiers.

Modern PostgreSQL also supports SQL-standard identity columns.

Preferred modern style:

    CREATE TABLE customer (
        customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name TEXT NOT NULL
    );

Identity columns make the generation behavior explicit and are generally
preferred for new designs where appropriate.
"""


# =============================================================================
# SECTION 38: POSTGRESQL SCHEMAS
# =============================================================================

"""
A PostgreSQL database can contain multiple schemas.

Think of a schema as a namespace containing database objects.

Example:

    company.employee
    company.department

    analytics.sales
    analytics.customer_metrics

This helps organize objects and can help with permissions.

Example:

    CREATE SCHEMA analytics;

    CREATE TABLE analytics.sales (
        sale_id BIGINT PRIMARY KEY
    );

PostgreSQL also has a search_path that determines where unqualified object
names are resolved.
"""


# =============================================================================
# SECTION 39: INDEXES
# =============================================================================

"""
An index is a data structure that can speed up data retrieval.

Example:

    CREATE INDEX idx_student_department
    ON student(department_id);

Indexes can significantly improve SELECT performance.

But indexes are not free.

They can:

    - consume storage
    - slow INSERT operations
    - slow UPDATE operations
    - slow DELETE operations
    - require maintenance

Common PostgreSQL index types include:

    B-tree
    Hash
    GiST
    SP-GiST
    GIN
    BRIN

B-tree is the general-purpose default and works well for many equality,
range and ordering queries.

GIN is particularly useful for certain multi-valued/search-oriented
structures such as JSONB and arrays.

BRIN can be very efficient for very large tables where values correlate
with physical row order.
"""


# =============================================================================
# SECTION 40: COMPOSITE INDEXES
# =============================================================================

"""
Example:

    CREATE INDEX idx_orders_customer_date
    ON orders(customer_id, order_date);

The order of columns matters.

A composite index on:

    (customer_id, order_date)

is particularly useful for queries filtering by customer_id and possibly
order_date.

Example:

    SELECT *
    FROM orders
    WHERE customer_id = 100
      AND order_date >= DATE '2026-01-01';

Index design should be based on actual query patterns, not guesswork.
"""


# =============================================================================
# SECTION 41: UNIQUE INDEX
# =============================================================================

"""
A UNIQUE constraint can enforce uniqueness.

Example:

    CREATE TABLE user_account (
        user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        email TEXT UNIQUE NOT NULL
    );

PostgreSQL implements uniqueness using an underlying index structure.

You can also explicitly create unique indexes.
"""


# =============================================================================
# SECTION 42: TRANSACTIONS
# =============================================================================

"""
A transaction is a logical unit of work.

Example:

    BEGIN;

    UPDATE account
    SET balance = balance - 100
    WHERE account_id = 1;

    UPDATE account
    SET balance = balance + 100
    WHERE account_id = 2;

    COMMIT;

If something goes wrong:

    ROLLBACK;

Transactions are essential when multiple operations must succeed or fail
as a unit.
"""


# =============================================================================
# SECTION 43: ACID
# =============================================================================

"""
ACID means:

A = Atomicity
C = Consistency
I = Isolation
D = Durability


ATOMICITY
---------

All operations in a transaction happen or none happen.


CONSISTENCY
-----------

A successful transaction moves the database from one valid state to
another valid state, respecting declared integrity rules and other
database invariants.


ISOLATION
---------

Concurrent transactions should behave according to the database's
isolation semantics.


DURABILITY
----------

Once a committed transaction is acknowledged as durable, its effects
should survive appropriate failures.
"""


# =============================================================================
# SECTION 44: MVCC
# =============================================================================

"""
PostgreSQL uses Multi-Version Concurrency Control (MVCC).

The basic idea is that database rows can have multiple versions, allowing
transactions to see appropriate snapshots of data without requiring every
reader to block every writer.

Benefits include:

    - high concurrency
    - readers generally do not block writers in the same way as
      lock-only systems
    - consistent transaction snapshots

PostgreSQL periodically needs maintenance such as VACUUM to manage
dead row versions created by updates/deletes.

Autovacuum automates much of this maintenance.
"""


# =============================================================================
# SECTION 45: ISOLATION LEVELS
# =============================================================================

"""
SQL transaction isolation levels include:

    READ UNCOMMITTED
    READ COMMITTED
    REPEATABLE READ
    SERIALIZABLE

PostgreSQL's behavior differs from some systems in the treatment of
READ UNCOMMITTED; it effectively behaves like READ COMMITTED.

READ COMMITTED
--------------
Each statement sees a snapshot based on transaction visibility rules.

REPEATABLE READ
---------------
The transaction works with a stable snapshot.

SERIALIZABLE
------------
Provides the strongest isolation semantics and may require transactions
to retry when serialization conflicts occur.

Choosing an isolation level is a correctness and concurrency decision,
not simply a performance switch.
"""


# =============================================================================
# SECTION 46: VIEWS
# =============================================================================

"""
A view is a stored query presented as a virtual table.

Example:

    CREATE VIEW student_department AS
    SELECT
        s.student_id,
        s.name,
        d.department_name
    FROM student s
    JOIN department d
        ON s.department_id = d.department_id;

Then:

    SELECT *
    FROM student_department;

Benefits:

    - abstraction
    - reuse
    - simpler queries
    - security through controlled exposure
"""


# =============================================================================
# SECTION 47: MATERIALIZED VIEWS
# =============================================================================

"""
A materialized view stores the query result physically.

Example:

    CREATE MATERIALIZED VIEW department_summary AS
    SELECT
        department_id,
        COUNT(*) AS student_count
    FROM student
    GROUP BY department_id;

It can be refreshed:

    REFRESH MATERIALIZED VIEW department_summary;

Materialized views are useful when:

    - an expensive query is executed frequently
    - data can tolerate some staleness
    - precomputed results improve performance
"""


# =============================================================================
# SECTION 48: COMMON TABLE EXPRESSIONS
# =============================================================================

"""
A CTE is written using WITH.

Example:

    WITH department_counts AS (
        SELECT
            department_id,
            COUNT(*) AS student_count
        FROM student
        GROUP BY department_id
    )
    SELECT *
    FROM department_counts
    WHERE student_count > 5;

CTEs improve query readability.

Recursive CTEs can process hierarchical structures such as:

    organization charts
    category trees
    graph-like relationships
"""


# =============================================================================
# SECTION 49: WINDOW FUNCTIONS
# =============================================================================

"""
Window functions calculate values across related rows without collapsing
them into one row per group.

Example:

    SELECT
        student_id,
        name,
        age,
        ROW_NUMBER() OVER (
            ORDER BY age DESC
        ) AS age_rank
    FROM student;

Other common window functions:

    ROW_NUMBER()
    RANK()
    DENSE_RANK()
    LAG()
    LEAD()
    SUM() OVER (...)
    AVG() OVER (...)

Window functions are extremely important for analytics.
"""


# =============================================================================
# SECTION 50: POSTGRESQL JSONB
# =============================================================================

"""
PostgreSQL supports JSON and JSONB.

JSON:
    stores JSON data with JSON-oriented semantics.

JSONB:
    stores a decomposed binary representation designed for efficient
    processing and indexing.

Example:

    CREATE TABLE event (
        event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        payload JSONB
    );

Insert:

    INSERT INTO event(payload)
    VALUES (
        '{"user_id": 100, "action": "login"}'
    );

Query:

    SELECT payload ->> 'action'
    FROM event;

JSONB is useful when some data is semi-structured, but it should not be
used automatically for everything.

If the data has strong relational structure and relationships, normalized
relational tables are often preferable.
"""


# =============================================================================
# SECTION 51: POSTGRESQL ARRAYS
# =============================================================================

"""
PostgreSQL supports array types.

Example:

    CREATE TABLE article (
        article_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        title TEXT,
        tags TEXT[]
    );

Arrays can be useful for naturally grouped values.

But arrays should not automatically replace normalized child tables.

Ask:

    Is this genuinely a single-valued attribute containing a collection?

or:

    Is this actually a relationship that should be modeled using another
    relation?

Database modeling comes before choosing a convenient data type.
"""


# =============================================================================
# SECTION 52: QUERY PLANNER
# =============================================================================

"""
PostgreSQL has a query planner/optimizer.

You describe WHAT data you want:

    SELECT ...

PostgreSQL determines HOW to obtain it.

Possible execution strategies include:

    - sequential scan
    - index scan
    - bitmap index scan
    - nested loop join
    - hash join
    - merge join
    - sorting
    - aggregation

The planner estimates costs and chooses an execution plan.
"""


# =============================================================================
# SECTION 53: EXPLAIN
# =============================================================================

"""
EXPLAIN shows the execution plan.

Example:

    EXPLAIN
    SELECT *
    FROM student
    WHERE department_id = 1;

EXPLAIN ANALYZE actually executes the query and reports runtime-related
information.

Example:

    EXPLAIN ANALYZE
    SELECT *
    FROM student
    WHERE department_id = 1;

Use EXPLAIN ANALYZE carefully with:

    INSERT
    UPDATE
    DELETE

because the query actually runs.

Understanding query plans is an advanced and highly valuable PostgreSQL
skill.
"""


# =============================================================================
# SECTION 54: JOIN ALGORITHMS
# =============================================================================

"""
PostgreSQL can use different join algorithms.

NESTED LOOP JOIN
----------------

For each row on one side, search for matching rows on the other side.

Often effective when:

    - one relation is small
    - an efficient index exists
    - the estimated number of matching rows is low


HASH JOIN
---------

Build a hash table for one side and probe it using rows from the other.

Often effective for equality joins over sufficiently large datasets.


MERGE JOIN
----------

Sort both sides and merge matching values.

Can be useful when inputs are already appropriately ordered or sorting
is otherwise cost-effective.

The planner chooses among available strategies based on cost estimates.
"""


# =============================================================================
# SECTION 55: PARTITIONING
# =============================================================================

"""
Partitioning divides a logically single table into multiple physical
partitions.

Common strategies:

    RANGE
    LIST
    HASH

Example:

    CREATE TABLE sales (
        sale_id BIGINT,
        sale_date DATE,
        amount NUMERIC(12,2)
    ) PARTITION BY RANGE (sale_date);

Then create partitions for date ranges.

Partitioning can help with:

    - very large tables
    - partition pruning
    - lifecycle management
    - archival strategies
    - maintenance

Partitioning is not automatically faster.

It should be used when the workload and data distribution justify it.
"""


# =============================================================================
# SECTION 56: ROW LEVEL SECURITY
# =============================================================================

"""
PostgreSQL supports Row-Level Security (RLS).

RLS allows policies to control which rows users can access or modify.

Conceptually:

    User A -> sees only organization A rows.
    User B -> sees only organization B rows.

Example:

    ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

Then policies can define access rules.

RLS is especially useful for multi-tenant applications and sensitive
data access control.
"""


# =============================================================================
# SECTION 57: FOREIGN KEY ACTIONS
# =============================================================================

"""
PostgreSQL foreign keys can specify actions such as:

    ON DELETE CASCADE
    ON DELETE SET NULL
    ON DELETE RESTRICT
    ON DELETE NO ACTION

Example:

    FOREIGN KEY (department_id)
        REFERENCES department(department_id)
        ON DELETE SET NULL

CASCADE means deleting a parent can delete dependent rows.

This is powerful and must be used deliberately.

Cascade behavior should reflect actual business rules.
"""


# =============================================================================
# SECTION 58: DEFERRED CONSTRAINTS
# =============================================================================

"""
Some PostgreSQL constraints can be deferred.

This means constraint checking can be postponed until transaction commit.

This can be useful for complex operations involving interdependent rows.

Concept:

    DEFERRABLE
    INITIALLY DEFERRED

This is an advanced relational integrity feature.
"""


# =============================================================================
# SECTION 59: TRANSACTION EXAMPLE IN PYTHON
# =============================================================================

def transaction_example(connection):
    """
    Demonstrates a transaction using Python's DB-API interface.
    """

    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE student
            SET age = age + 1
            WHERE student_id = 1
        """)

        # Additional operations could happen here.

        connection.commit()

    except Exception:
        connection.rollback()
        raise


# =============================================================================
# SECTION 60: PARAMETERIZED QUERIES
# =============================================================================

"""
Never construct SQL by directly concatenating untrusted user input.

BAD:

    username = input("Username: ")

    query = (
        "SELECT * FROM users WHERE username = '"
        + username
        + "'"
    )

This can create SQL injection vulnerabilities.

GOOD:

    cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )

For PostgreSQL using psycopg, placeholders use the driver's parameter
syntax, commonly:

    cursor.execute(
        "SELECT * FROM users WHERE username = %s",
        (username,)
    )

Do not confuse Python string interpolation with SQL parameter binding.

Use the database driver's parameterization mechanism.
"""


# =============================================================================
# SECTION 61: POSTGRESQL CONNECTION USING PSYCOPG
# =============================================================================

"""
Optional PostgreSQL example.

Install:

    pip install "psycopg[binary]"

Example:

    import psycopg

    connection = psycopg.connect(
        "dbname=mydb user=postgres password=secret "
        "host=localhost port=5432"
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT student_id, name FROM student WHERE age > %s",
            (20,)
        )

        rows = cursor.fetchall()

    connection.close()

Production applications should generally avoid hardcoding passwords in
source code.

Prefer:

    environment variables
    secret managers
    secure configuration systems
"""


# =============================================================================
# SECTION 62: CRUD
# =============================================================================

"""
CRUD:

    CREATE
    READ
    UPDATE
    DELETE


CREATE:

    INSERT INTO student(...)
    VALUES (...);


READ:

    SELECT ...
    FROM student;


UPDATE:

    UPDATE student
    SET age = 22
    WHERE student_id = 1;


DELETE:

    DELETE FROM student
    WHERE student_id = 1;


Always think carefully about UPDATE and DELETE conditions.

A missing WHERE clause can modify or delete an entire table.
"""


# =============================================================================
# SECTION 63: PRACTICAL SQL EXAMPLES
# =============================================================================

def practical_queries(connection):
    cursor = connection.cursor()

    queries = {
        "count_students": """
            SELECT COUNT(*)
            FROM student
        """,

        "average_age": """
            SELECT AVG(age)
            FROM student
        """,

        "students_with_department": """
            SELECT
                s.name,
                d.department_name
            FROM student s
            JOIN department d
                ON s.department_id = d.department_id
        """,

        "course_enrollments": """
            SELECT
                c.course_name,
                COUNT(e.student_id) AS enrollment_count
            FROM course c
            LEFT JOIN enrollment e
                ON c.course_id = e.course_id
            GROUP BY c.course_id, c.course_name
            ORDER BY enrollment_count DESC
        """,

        "students_and_grades": """
            SELECT
                s.name,
                c.course_name,
                e.grade
            FROM enrollment e
            JOIN student s
                ON e.student_id = s.student_id
            JOIN course c
                ON e.course_id = c.course_id
            ORDER BY s.name, c.course_name
        """
    }

    for name, query in queries.items():
        print(f"\n{name.upper()}")

        cursor.execute(query)

        for row in cursor.fetchall():
            print(row)


# =============================================================================
# SECTION 64: SQL SET OPERATIONS
# =============================================================================

"""
PostgreSQL supports:

    UNION
    UNION ALL
    INTERSECT
    EXCEPT

UNION:
    combines results and removes duplicates.

UNION ALL:
    combines results without removing duplicates.

INTERSECT:
    returns common rows.

EXCEPT:
    returns rows in the first result that are absent from the second.
"""


# =============================================================================
# SECTION 65: CORRELATED SUBQUERIES
# =============================================================================

"""
A correlated subquery references the outer query.

Example:

    SELECT s.name
    FROM student s
    WHERE EXISTS (
        SELECT 1
        FROM enrollment e
        WHERE e.student_id = s.student_id
    );

EXISTS is often useful when you only care whether a related row exists.
"""


# =============================================================================
# SECTION 66: EXISTS VS IN
# =============================================================================

"""
Example:

    SELECT name
    FROM student s
    WHERE EXISTS (
        SELECT 1
        FROM enrollment e
        WHERE e.student_id = s.student_id
    );

This asks:

    "Does at least one enrollment exist for this student?"

IN can express similar logic:

    WHERE student_id IN (
        SELECT student_id
        FROM enrollment
    )

Do not blindly assume one is always faster.

Modern PostgreSQL can transform logically equivalent queries into
efficient plans depending on statistics and query structure.

Use EXPLAIN ANALYZE to investigate actual performance.
"""


# =============================================================================
# SECTION 67: CANDIDATE KEY EXAMPLE
# =============================================================================

"""
Suppose:

    EMPLOYEE(
        employee_id,
        email,
        employee_name
    )

And both:

    employee_id
    email

are unique.

Then:

    {employee_id}
    {email}

are candidate keys.

If we select employee_id as PRIMARY KEY:

    employee_id -> primary key
    email       -> alternate candidate key

A super key could be:

    {employee_id, employee_name}

because employee_id alone already identifies the row.

But it is not minimal, so it is not a candidate key.
"""


# =============================================================================
# SECTION 68: DATABASE DESIGN PROCESS
# =============================================================================

"""
A disciplined relational database design process:

    1. Understand the business requirements.
    2. Identify entities.
    3. Identify attributes.
    4. Identify relationships.
    5. Identify candidate keys.
    6. Choose primary keys.
    7. Define foreign keys.
    8. Define domains and data types.
    9. Define integrity constraints.
    10. Normalize where appropriate.
    11. Consider access patterns.
    12. Add indexes based on real query requirements.
    13. Define transactions.
    14. Define security rules.
    15. Test concurrency.
    16. Benchmark important queries.
    17. Inspect query plans.
    18. Monitor production behavior.
"""


# =============================================================================
# SECTION 69: ENTITY-RELATIONSHIP THINKING
# =============================================================================

"""
Before writing SQL, think about entities and relationships.

Example:

    Student
        |
        | enrolls in
        |
        v
    Course

This is many-to-many.

A relational implementation usually needs an associative relation:

    STUDENT
    COURSE
    ENROLLMENT

ENROLLMENT:

    student_id
    course_id
    enrollment_date
    grade

This converts the many-to-many relationship into two one-to-many
relationships.
"""


# =============================================================================
# SECTION 70: ONE-TO-ONE, ONE-TO-MANY, MANY-TO-MANY
# =============================================================================

"""
ONE-TO-ONE
----------

One record in A corresponds to at most one record in B.

Example:

    PERSON
    PASSPORT


ONE-TO-MANY
-----------

One record in A can correspond to many records in B.

Example:

    DEPARTMENT
        |
        +---- EMPLOYEE
        +---- EMPLOYEE
        +---- EMPLOYEE


MANY-TO-MANY
------------

Many records in A can correspond to many records in B.

Example:

    STUDENT <----> COURSE

Implement using:

    ENROLLMENT
"""


# =============================================================================
# SECTION 71: NULL AND THREE-VALUED LOGIC
# =============================================================================

"""
Consider:

    salary > 50000

If salary is NULL, the result is UNKNOWN, not TRUE or FALSE.

Therefore:

    WHERE salary > 50000

does not return rows where salary is NULL.

This becomes especially important with:

    NOT
    AND
    OR
    NOT IN

Example:

    WHERE id NOT IN (...)

can produce surprising results when NULL is present in the subquery.

For existence checks, NOT EXISTS is often safer and clearer than NOT IN
when NULL semantics could matter.
"""


# =============================================================================
# SECTION 72: DENORMALIZATION
# =============================================================================

"""
Normalization reduces redundancy.

Denormalization intentionally introduces redundancy to improve particular
read patterns.

Examples:

    storing precomputed totals
    duplicating frequently accessed attributes
    materializing aggregates
    maintaining summary tables

Denormalization can improve performance but creates additional consistency
responsibilities.

The correct approach is:

    Normalize for correctness first.
    Measure performance.
    Denormalize only when justified.
"""


# =============================================================================
# SECTION 73: OLTP VS OLAP
# =============================================================================

"""
OLTP
----

Online Transaction Processing.

Characteristics:

    - many small transactions
    - frequent INSERT/UPDATE/DELETE
    - strong consistency requirements
    - normalized models are common

Examples:

    banking
    ecommerce
    order management


OLAP
----

Online Analytical Processing.

Characteristics:

    - large scans
    - aggregations
    - reporting
    - historical analysis

Examples:

    dashboards
    business intelligence
    data analysis

The same PostgreSQL system can support analytical workloads, though very
large analytical workloads may use specialized architectures.
"""


# =============================================================================
# SECTION 74: SECURITY
# =============================================================================

"""
Database security includes:

    authentication
    authorization
    role management
    least privilege
    encryption in transit
    encryption at rest
    auditing
    row-level security
    secret management
    network controls

Principle of least privilege:

    Give users/applications only the permissions they actually need.

Do not use a superuser account for an ordinary application.
"""


# =============================================================================
# SECTION 75: BACKUPS AND RECOVERY
# =============================================================================

"""
A production database strategy needs:

    backups
    restore testing
    point-in-time recovery where appropriate
    replication strategy
    monitoring
    disaster recovery planning

A backup that has never been successfully restored should not be treated
as fully verified.

Database reliability is not only about preventing failures.

It is also about recovering correctly when failures occur.
"""


# =============================================================================
# SECTION 76: POSTGRESQL REPLICATION
# =============================================================================

"""
PostgreSQL supports replication mechanisms.

Common concepts include:

    streaming replication
    physical replication
    logical replication

Replication can be used for:

    high availability
    read scaling
    disaster recovery
    data integration

Replication is different from backup.

Replication can copy an accidental DELETE.
A proper backup can provide a recovery point before the mistake.
"""


# =============================================================================
# SECTION 77: DATABASE OBSERVABILITY
# =============================================================================

"""
Production PostgreSQL systems should be monitored for:

    - query latency
    - throughput
    - connection count
    - lock contention
    - deadlocks
    - cache behavior
    - disk usage
    - table/index growth
    - vacuum activity
    - replication lag
    - failed queries
    - transaction duration

Useful PostgreSQL tools/features include:

    EXPLAIN
    EXPLAIN ANALYZE
    pg_stat_activity
    pg_stat_statements
    PostgreSQL logs
"""


# =============================================================================
# SECTION 78: COMMON DATABASE MISTAKES
# =============================================================================

"""
1. No primary key.

2. Storing multiple values in one field when they should be related rows.

3. Using strings for everything.

4. Not enforcing foreign keys.

5. Overusing NULL.

6. Creating indexes on every column.

7. Creating indexes without understanding query patterns.

8. Running SELECT * unnecessarily.

9. Building SQL with string concatenation.

10. Ignoring transaction boundaries.

11. Running long transactions unnecessarily.

12. Ignoring query plans.

13. Using database superuser credentials in applications.

14. Forgetting backups.

15. Never testing restores.

16. Over-normalizing without considering actual workload.

17. Denormalizing without integrity mechanisms.

18. Assuming ORM-generated SQL is always efficient.

19. Ignoring concurrency.

20. Assuming development data represents production scale.
"""


# =============================================================================
# SECTION 79: ORM CONCEPT
# =============================================================================

"""
An ORM (Object-Relational Mapper) maps programming-language objects to
relational database structures.

Examples in Python include:

    SQLAlchemy
    Django ORM

ORMs can improve developer productivity.

But a developer should still understand:

    - SQL
    - joins
    - indexes
    - transactions
    - constraints
    - query plans
    - normalization

An ORM does not eliminate relational database concepts.
"""


# =============================================================================
# SECTION 80: RELATIONAL DATABASE MENTAL MODEL
# =============================================================================

"""
A strong mental model is:

    DATABASE
       |
       +-- SCHEMA
       |     |
       |     +-- TABLE
       |     |     |
       |     |     +-- COLUMNS / ATTRIBUTES
       |     |     +-- ROWS / TUPLES
       |     |     +-- CONSTRAINTS
       |     |     +-- INDEXES
       |     |
       |     +-- VIEW
       |     +-- FUNCTION
       |     +-- SEQUENCE
       |     +-- OTHER OBJECTS
       |
       +-- ROLES / USERS
       +-- TRANSACTIONS
       +-- SECURITY
"""


# =============================================================================
# SECTION 81: FINAL CONCEPTUAL SUMMARY
# =============================================================================

"""
The entire topic can be reduced to the following chain:

    DOMAIN
       |
       v
    ATTRIBUTE
       |
       v
    RELATION SCHEMA
       |
       v
    RELATION INSTANCE
       |
       v
    TUPLES
       |
       v
    KEYS + CONSTRAINTS
       |
       v
    RELATIONSHIPS
       |
       v
    RELATIONAL ALGEBRA
       |
       v
    SQL
       |
       v
    POSTGRESQL
       |
       v
    INDEXING + QUERY PLANNING
       |
       v
    TRANSACTIONS + CONCURRENCY
       |
       v
    NORMALIZATION + DATABASE DESIGN
       |
       v
    SECURITY + OPERATIONS
       |
       v
    PRODUCTION DATABASE SYSTEM
"""


# =============================================================================
# SECTION 82: MINI PROJECT
# =============================================================================

def mini_project(connection):
    """
    A small analytical exercise demonstrating joins and aggregation.
    """

    cursor = connection.cursor()

    print("\nMINI PROJECT")
    print("============")

    query = """
        SELECT
            d.department_name,
            COUNT(s.student_id) AS student_count,
            ROUND(AVG(s.age), 2) AS average_age
        FROM department d
        LEFT JOIN student s
            ON d.department_id = s.department_id
        GROUP BY
            d.department_id,
            d.department_name
        ORDER BY
            student_count DESC
    """

    cursor.execute(query)

    for row in cursor.fetchall():
        print(row)


# =============================================================================
# SECTION 83: POSTGRESQL PRACTICE DATABASE
# =============================================================================

POSTGRESQL_PRACTICE_SQL = r"""
-- ============================================================
-- POSTGRESQL PRACTICE SCRIPT
-- ============================================================

CREATE DATABASE university_db;

-- Connect to university_db using psql:
-- \c university_db

CREATE SCHEMA university;

CREATE TABLE university.department (
    department_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE
);

CREATE TABLE university.student (
    student_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    age INTEGER CHECK (age >= 0),
    department_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_student_department
        FOREIGN KEY (department_id)
        REFERENCES university.department(department_id)
        ON DELETE SET NULL
);

CREATE TABLE university.course (
    course_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    course_name TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
);

CREATE TABLE university.enrollment (
    student_id BIGINT NOT NULL,
    course_id BIGINT NOT NULL,
    enrollment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    grade TEXT,

    PRIMARY KEY (student_id, course_id),

    FOREIGN KEY (student_id)
        REFERENCES university.student(student_id)
        ON DELETE CASCADE,

    FOREIGN KEY (course_id)
        REFERENCES university.course(course_id)
        ON DELETE CASCADE
);

-- Insert departments

INSERT INTO university.department(department_name)
VALUES
    ('Computer Science'),
    ('Electronics'),
    ('Mechanical Engineering');

-- Insert students

INSERT INTO university.student(
    name,
    email,
    age,
    department_id
)
VALUES
    ('Rahul', 'rahul@example.com', 21, 1),
    ('Priya', 'priya@example.com', 22, 2),
    ('Amit', 'amit@example.com', 20, 1),
    ('Neha', 'neha@example.com', 23, 3);

-- Insert courses

INSERT INTO university.course(course_name, credits)
VALUES
    ('Database Systems', 4),
    ('Python Programming', 3),
    ('Machine Learning', 4);

-- Insert enrollments

INSERT INTO university.enrollment(
    student_id,
    course_id,
    grade
)
VALUES
    (1, 1, 'A'),
    (1, 2, 'A+'),
    (2, 1, 'B+'),
    (3, 1, 'A'),
    (3, 3, 'A+'),
    (4, 2, 'B');

-- ============================================================
-- SELECTION
-- ============================================================

SELECT *
FROM university.student
WHERE age > 20;

-- ============================================================
-- PROJECTION
-- ============================================================

SELECT name, email
FROM university.student;

-- ============================================================
-- JOIN
-- ============================================================

SELECT
    s.name,
    d.department_name
FROM university.student AS s
JOIN university.department AS d
    ON s.department_id = d.department_id;

-- ============================================================
-- LEFT JOIN
-- ============================================================

SELECT
    d.department_name,
    s.name
FROM university.department AS d
LEFT JOIN university.student AS s
    ON d.department_id = s.department_id;

-- ============================================================
-- MULTI-TABLE JOIN
-- ============================================================

SELECT
    s.name,
    c.course_name,
    e.grade
FROM university.enrollment AS e
JOIN university.student AS s
    ON e.student_id = s.student_id
JOIN university.course AS c
    ON e.course_id = c.course_id;

-- ============================================================
-- GROUP BY
-- ============================================================

SELECT
    department_id,
    COUNT(*) AS student_count
FROM university.student
GROUP BY department_id;

-- ============================================================
-- HAVING
-- ============================================================

SELECT
    department_id,
    COUNT(*) AS student_count
FROM university.student
GROUP BY department_id
HAVING COUNT(*) >= 2;

-- ============================================================
-- WINDOW FUNCTION
-- ============================================================

SELECT
    student_id,
    name,
    age,
    ROW_NUMBER() OVER (
        ORDER BY age DESC
    ) AS age_rank
FROM university.student;

-- ============================================================
-- CTE
-- ============================================================

WITH department_counts AS (
    SELECT
        department_id,
        COUNT(*) AS student_count
    FROM university.student
    GROUP BY department_id
)
SELECT *
FROM department_counts
WHERE student_count >= 2;

-- ============================================================
-- EXISTS
-- ============================================================

SELECT
    s.student_id,
    s.name
FROM university.student AS s
WHERE EXISTS (
    SELECT 1
    FROM university.enrollment AS e
    WHERE e.student_id = s.student_id
);

-- ============================================================
-- INDEX
-- ============================================================

CREATE INDEX idx_student_department
ON university.student(department_id);

CREATE INDEX idx_enrollment_course
ON university.enrollment(course_id);

-- ============================================================
-- EXPLAIN
-- ============================================================

EXPLAIN
SELECT *
FROM university.student
WHERE department_id = 1;

-- ============================================================
-- EXPLAIN ANALYZE
-- ============================================================

EXPLAIN ANALYZE
SELECT *
FROM university.student
WHERE department_id = 1;

-- ============================================================
-- VIEW
-- ============================================================

CREATE VIEW university.student_department_view AS
SELECT
    s.student_id,
    s.name,
    d.department_name
FROM university.student AS s
LEFT JOIN university.department AS d
    ON s.department_id = d.department_id;

SELECT *
FROM university.student_department_view;

-- ============================================================
-- TRANSACTION
-- ============================================================

BEGIN;

UPDATE university.student
SET age = age + 1
WHERE student_id = 1;

COMMIT;

-- If an error occurs:
-- ROLLBACK;

-- ============================================================
-- SET OPERATIONS
-- ============================================================

SELECT student_id
FROM university.enrollment
WHERE course_id = 1

INTERSECT

SELECT student_id
FROM university.enrollment
WHERE course_id = 2;

-- ============================================================
-- JSONB EXAMPLE
-- ============================================================

CREATE TABLE university.event (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payload JSONB NOT NULL
);

INSERT INTO university.event(payload)
VALUES
    ('{"user_id": 1, "action": "login"}'),
    ('{"user_id": 2, "action": "purchase"}');

SELECT
    payload ->> 'action' AS action
FROM university.event;

-- ============================================================
-- FINAL PRACTICE QUESTIONS
-- ============================================================

-- 1. Find all students older than 21.
-- 2. Find all students in Computer Science.
-- 3. Count students by department.
-- 4. Find courses with zero enrollments.
-- 5. Find students enrolled in Database Systems.
-- 6. Find the average age by department.
-- 7. Rank students by age.
-- 8. Find students who are not enrolled in any course.
-- 9. Find the most popular course.
-- 10. Explain the query plan for the most popular course query.
"""


# =============================================================================
# SECTION 84: EXECUTION
# =============================================================================

def main():
    print("=" * 70)
    print("RELATIONAL DATABASE CONCEPTS + POSTGRESQL")
    print("=" * 70)

    connection = create_demo_database()

    basic_sql_examples(connection)

    demonstrate_inner_join(connection)

    practical_queries(connection)

    mini_project(connection)

    print("\nPOSTGRESQL PRACTICE SQL IS AVAILABLE IN:")
    print("POSTGRESQL_PRACTICE_SQL")

    connection.close()

    print("\nLearning complete.")
    print("Next step: install PostgreSQL and practice the SQL examples.")


if __name__ == "__main__":
    main()
