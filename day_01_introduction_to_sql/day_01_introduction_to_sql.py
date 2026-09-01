# ============================================================
# DAY 01: INTRODUCTION TO SQL
# ============================================================
#
# Topic:
# Introduction to SQL
#
# Coverage:
# - What is SQL?
# - Why SQL exists
# - What is a database?
# - What is a relational database?
# - Tables, rows, columns
# - Primary keys and foreign keys
# - SQL vs programming languages
# - SQL use cases
# - Database-driven applications
# - SQL categories
# - PostgreSQL
# - SQL execution model
# - Client/server architecture
# - CRUD
# - Relational thinking
# - Basic SQL examples
# - PostgreSQL examples
# - Common misconceptions
# - Exercises
#
# ============================================================


# ============================================================
# 0. INTRODUCTION
# ============================================================

print("=" * 70)
print("DAY 01 - INTRODUCTION TO SQL")
print("=" * 70)

print("""
Welcome to Day 01 of the SQL Learning Journey.

Today we are starting from the absolute fundamentals.

The objective is NOT to memorize SQL commands.

The objective is to understand:

1. Why databases exist
2. Why SQL exists
3. What a relational database is
4. How data is organized
5. How SQL communicates with a database
6. How PostgreSQL fits into the picture
7. How applications use databases
8. How SQL differs from programming languages
9. How SQL is used in real-world systems

Once these concepts are clear, learning SQL syntax becomes
much easier.
""")


# ============================================================
# 1. WHAT IS DATA?
# ============================================================

print("\n" + "=" * 70)
print("1. WHAT IS DATA?")
print("=" * 70)

print("""
Data is a collection of facts, observations, measurements,
records, or values.

Examples:

Name       = Atul
Age        = 33
City       = Lucknow
Salary     = 75000
Experience = 5 years

A company may have millions of such values.

For example:

Customer:
    customer_id = 101
    name        = Rahul
    email       = rahul@example.com
    city        = Delhi

Data by itself is simply a representation of facts.

The challenge is:

How do we store enormous amounts of data?
How do we retrieve it?
How do we update it?
How do we delete it?
How do we keep it consistent?
How do we allow multiple users to access it?
How do we search millions of records efficiently?
""")


# ============================================================
# 2. WHY DO WE NEED DATABASES?
# ============================================================

print("\n" + "=" * 70)
print("2. WHY DO WE NEED DATABASES?")
print("=" * 70)

print("""
Imagine a company stores customer information in a text file.

customers.txt

101, Rahul, rahul@gmail.com, Delhi
102, Priya, priya@gmail.com, Mumbai
103, Amit, amit@gmail.com, Lucknow

This may work for a tiny amount of data.

But imagine:

10 customers
100 customers
10,000 customers
10 million customers
500 million customers

Problems appear quickly.

Problems include:

- Searching becomes difficult
- Updating records becomes difficult
- Duplicate data appears
- Multiple users may overwrite data
- Data relationships become difficult
- Security becomes difficult
- Backup becomes difficult
- Concurrent access becomes difficult
- Data validation becomes difficult
- Performance becomes difficult

A database system solves many of these problems.
""")


# ============================================================
# 3. WHAT IS A DATABASE?
# ============================================================

print("\n" + "=" * 70)
print("3. WHAT IS A DATABASE?")
print("=" * 70)

print("""
A database is an organized collection of data that can be
stored, managed, accessed, updated, and queried efficiently.

A database is not simply a file.

A modern database system can provide:

- Data storage
- Data retrieval
- Data modification
- Data validation
- Security
- Authentication
- Authorization
- Concurrency control
- Transactions
- Backup
- Recovery
- Indexing
- Query optimization
- Data integrity
""")


# ============================================================
# 4. DATABASE MANAGEMENT SYSTEM
# ============================================================

print("\n" + "=" * 70)
print("4. DATABASE MANAGEMENT SYSTEM - DBMS")
print("=" * 70)

print("""
A DBMS stands for:

Database Management System

A DBMS is software used to manage databases.

Examples include:

- PostgreSQL
- MySQL
- Microsoft SQL Server
- Oracle Database
- SQLite
- MariaDB

A DBMS provides mechanisms for applications and users to
interact with stored data.

Conceptually:

        USER
         |
         v
    APPLICATION
         |
         v
        DBMS
         |
         v
      DATABASE


The database stores the data.

The DBMS manages access to that data.
""")


# ============================================================
# 5. WHAT IS SQL?
# ============================================================

print("\n" + "=" * 70)
print("5. WHAT IS SQL?")
print("=" * 70)

print("""
SQL stands for:

Structured Query Language

SQL is a language used to interact with relational databases.

SQL allows us to:

- Create databases objects
- Create tables
- Insert data
- Retrieve data
- Update data
- Delete data
- Filter data
- Sort data
- Aggregate data
- Join tables
- Define relationships
- Control permissions
- Manage transactions

Example:

SELECT *
FROM employees;

This asks the database to retrieve all columns and rows
from the employees table.
""")


# ============================================================
# 6. WHY DOES SQL EXIST?
# ============================================================

print("\n" + "=" * 70)
print("6. WHY DOES SQL EXIST?")
print("=" * 70)

print("""
SQL exists because applications need a standardized way to
communicate with relational databases.

Suppose an application wants to ask:

"Give me all customers from Lucknow."

The application can send:

SELECT *
FROM customers
WHERE city = 'Lucknow';

The database engine interprets the SQL statement and produces
the requested result.

The important idea is:

SQL describes WHAT data you want.

The database engine determines HOW to retrieve it efficiently.
""")


# ============================================================
# 7. DECLARATIVE NATURE OF SQL
# ============================================================

print("\n" + "=" * 70)
print("7. SQL IS PRIMARILY DECLARATIVE")
print("=" * 70)

print("""
SQL is primarily a declarative language.

Declarative means:

You describe the desired result.

Example:

SELECT name
FROM employees
WHERE salary > 100000;

You are saying:

"Give me employee names where salary is greater than 100000."

You are generally NOT specifying:

1. Start at row 1
2. Check salary
3. Move to row 2
4. Check salary
5. Continue
6. Store matching names

The database optimizer decides how to execute the request.

This is one of the most important differences between SQL
and traditional procedural programming.
""")


# ============================================================
# 8. SQL VS PYTHON
# ============================================================

print("\n" + "=" * 70)
print("8. SQL VS PROGRAMMING LANGUAGES")
print("=" * 70)

print("""
SQL and Python solve different problems.

PYTHON:

Python is a general-purpose programming language.

It can be used for:

- Web development
- Automation
- Data analysis
- Machine learning
- APIs
- File processing
- Scientific computing
- Application development

SQL:

SQL is primarily designed for interacting with databases.

It is especially useful for:

- Querying data
- Filtering data
- Joining data
- Aggregating data
- Modifying data
- Managing relational structures

Think:

Python = general-purpose computation

SQL = database interaction and data querying
""")


# ============================================================
# 9. SQL VS PYTHON EXAMPLE
# ============================================================

print("\n" + "=" * 70)
print("9. SQL VS PYTHON - SIMPLE EXAMPLE")
print("=" * 70)

print("""
Suppose we have employee salaries:

100000
120000
80000
150000

Python could process values using a loop.

Conceptually:

for salary in salaries:
    if salary > 100000:
        print(salary)

SQL could express the same requirement as:

SELECT salary
FROM employees
WHERE salary > 100000;

SQL describes the required result.

Python commonly describes the computational procedure.
""")


# ============================================================
# 10. WHAT IS A RELATIONAL DATABASE?
# ============================================================

print("\n" + "=" * 70)
print("10. RELATIONAL DATABASE")
print("=" * 70)

print("""
A relational database stores data in structures commonly
represented as tables.

A table contains:

- Rows
- Columns

Example:

EMPLOYEES

employee_id | name  | department | salary
-------------+-------+------------+--------
1            | Rahul | IT         | 90000
2            | Priya | HR         | 80000
3            | Amit  | Finance    | 95000

The relational model allows different tables to be related
to each other.

For example:

EMPLOYEES
    |
    | department_id
    v
DEPARTMENTS
""")


# ============================================================
# 11. TABLES
# ============================================================

print("\n" + "=" * 70)
print("11. TABLES")
print("=" * 70)

print("""
A table represents a collection of related records.

Example:

CUSTOMERS

customer_id | name  | city
------------+-------+--------
1           | Rahul | Delhi
2           | Priya | Mumbai
3           | Amit  | Lucknow

The table has:

3 rows

and

3 columns.
""")


# ============================================================
# 12. ROWS
# ============================================================

print("\n" + "=" * 70)
print("12. ROWS")
print("=" * 70)

print("""
A row represents one record.

Example:

1 | Rahul | Delhi

This row represents one customer.

Another:

2 | Priya | Mumbai

represents another customer.

Rows are also commonly called:

- Records
- Tuples

in relational database terminology.
""")


# ============================================================
# 13. COLUMNS
# ============================================================

print("\n" + "=" * 70)
print("13. COLUMNS")
print("=" * 70)

print("""
A column represents an attribute of the records.

Example:

customer_id
name
email
city
phone

Each column normally has a defined data type.

For example:

customer_id -> INTEGER
name        -> VARCHAR
email       -> VARCHAR
age         -> INTEGER
salary      -> NUMERIC
""")


# ============================================================
# 14. DATA TYPES
# ============================================================

print("\n" + "=" * 70)
print("14. DATABASE DATA TYPES")
print("=" * 70)

print("""
Databases need to know what type of data a column contains.

Common PostgreSQL types include:

INTEGER
BIGINT
NUMERIC
DECIMAL
VARCHAR
TEXT
BOOLEAN
DATE
TIME
TIMESTAMP
TIMESTAMPTZ
UUID
JSON
JSONB
ARRAY

Example:

CREATE TABLE employees (
    employee_id INTEGER,
    name TEXT,
    salary NUMERIC(12,2),
    active BOOLEAN,
    joining_date DATE
);

The data type helps the database understand how values should
be stored, validated, compared, and processed.
""")


# ============================================================
# 15. PRIMARY KEY
# ============================================================

print("\n" + "=" * 70)
print("15. PRIMARY KEY")
print("=" * 70)

print("""
A primary key uniquely identifies each row.

Example:

employee_id

1
2
3
4

Each employee has a unique employee_id.

Example:

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    name TEXT,
    salary NUMERIC
);

A primary key generally means:

- Values must be unique
- NULL is not allowed
- It identifies a record
""")


# ============================================================
# 16. FOREIGN KEY
# ============================================================

print("\n" + "=" * 70)
print("16. FOREIGN KEY")
print("=" * 70)

print("""
A foreign key creates a relationship between tables.

Example:

departments

department_id | department_name
--------------+----------------
1             | IT
2             | HR
3             | Finance


employees

employee_id | name  | department_id
------------+-------+--------------
101         | Rahul | 1
102         | Priya | 2
103         | Amit  | 1

department_id in employees can reference
department_id in departments.

Example:

CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    name TEXT,
    department_id INTEGER,
    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

This establishes referential integrity.
""")


# ============================================================
# 17. RELATIONSHIPS
# ============================================================

print("\n" + "=" * 70)
print("17. RELATIONSHIPS BETWEEN TABLES")
print("=" * 70)

print("""
Common relationships include:

1. One-to-One
2. One-to-Many
3. Many-to-Many

ONE-TO-ONE:

One person -> One passport

ONE-TO-MANY:

One department -> Many employees

MANY-TO-MANY:

Students <-> Courses

A student can enroll in multiple courses.

A course can have multiple students.

This usually requires a junction table.

Example:

student_courses

student_id | course_id
-----------+----------
1          | 101
1          | 102
2          | 101
""")


# ============================================================
# 18. NORMALIZED THINKING
# ============================================================

print("\n" + "=" * 70)
print("18. WHY TABLES ARE SEPARATED")
print("=" * 70)

print("""
Suppose we store:

employee_id
employee_name
department_name
department_manager
department_location

inside every employee record.

If 1,000 employees belong to IT, we may repeatedly store
the same department information 1,000 times.

This creates redundancy.

Instead:

DEPARTMENTS

department_id
department_name
manager
location

EMPLOYEES

employee_id
employee_name
department_id

Now the department information is stored separately.

This is the basic idea behind normalization.

We will study normalization in detail later.
""")


# ============================================================
# 19. SQL CATEGORIES
# ============================================================

print("\n" + "=" * 70)
print("19. SQL COMMAND CATEGORIES")
print("=" * 70)

print("""
SQL commands are commonly grouped into categories.

------------------------------------------------------------
DDL - DATA DEFINITION LANGUAGE
------------------------------------------------------------

Used to define database structures.

Examples:

CREATE
ALTER
DROP
TRUNCATE


------------------------------------------------------------
DML - DATA MANIPULATION LANGUAGE
------------------------------------------------------------

Used to manipulate data.

Examples:

INSERT
UPDATE
DELETE


------------------------------------------------------------
DQL - DATA QUERY LANGUAGE
------------------------------------------------------------

Commonly used to refer to:

SELECT


------------------------------------------------------------
DCL - DATA CONTROL LANGUAGE
------------------------------------------------------------

Used for permissions and access control.

Examples:

GRANT
REVOKE


------------------------------------------------------------
TCL - TRANSACTION CONTROL LANGUAGE
------------------------------------------------------------

Used to manage transactions.

Examples:

COMMIT
ROLLBACK
SAVEPOINT
""")


# ============================================================
# 20. CRUD
# ============================================================

print("\n" + "=" * 70)
print("20. CRUD")
print("=" * 70)

print("""
CRUD represents four fundamental data operations.

C = CREATE
R = READ
U = UPDATE
D = DELETE

Example:

CREATE/INSERT:

INSERT INTO employees
(employee_id, name, salary)
VALUES
(1, 'Rahul', 90000);


READ:

SELECT *
FROM employees;


UPDATE:

UPDATE employees
SET salary = 95000
WHERE employee_id = 1;


DELETE:

DELETE FROM employees
WHERE employee_id = 1;
""")


# ============================================================
# 21. BASIC SELECT
# ============================================================

print("\n" + "=" * 70)
print("21. SELECT")
print("=" * 70)

print("""
SELECT retrieves data.

Example:

SELECT *
FROM employees;

The * means:

all columns

You can also request specific columns:

SELECT name, salary
FROM employees;

This is usually preferable when you only need selected columns.
""")


# ============================================================
# 22. WHERE
# ============================================================

print("\n" + "=" * 70)
print("22. WHERE")
print("=" * 70)

print("""
WHERE filters rows.

Example:

SELECT *
FROM employees
WHERE salary > 100000;

This means:

Return employees whose salary is greater than 100000.
""")


# ============================================================
# 23. ORDER BY
# ============================================================

print("\n" + "=" * 70)
print("23. ORDER BY")
print("=" * 70)

print("""
ORDER BY sorts results.

Ascending:

SELECT *
FROM employees
ORDER BY salary ASC;

Descending:

SELECT *
FROM employees
ORDER BY salary DESC;
""")


# ============================================================
# 24. DISTINCT
# ============================================================

print("\n" + "=" * 70)
print("24. DISTINCT")
print("=" * 70)

print("""
DISTINCT removes duplicate values from the result.

Example:

SELECT DISTINCT department_id
FROM employees;

If employees belong to:

IT
IT
HR
Finance
HR

The result contains:

IT
HR
Finance
""")


# ============================================================
# 25. AGGREGATION
# ============================================================

print("\n" + "=" * 70)
print("25. AGGREGATION")
print("=" * 70)

print("""
SQL can perform calculations over groups of rows.

Common aggregate functions:

COUNT()
SUM()
AVG()
MIN()
MAX()

Examples:

SELECT COUNT(*)
FROM employees;

SELECT AVG(salary)
FROM employees;

SELECT MAX(salary)
FROM employees;

SELECT MIN(salary)
FROM employees;

SELECT SUM(salary)
FROM employees;
""")


# ============================================================
# 26. GROUP BY
# ============================================================

print("\n" + "=" * 70)
print("26. GROUP BY")
print("=" * 70)

print("""
GROUP BY groups rows based on a column.

Example:

SELECT department_id, COUNT(*)
FROM employees
GROUP BY department_id;

This can answer:

"How many employees belong to each department?"
""")


# ============================================================
# 27. HAVING
# ============================================================

print("\n" + "=" * 70)
print("27. HAVING")
print("=" * 70)

print("""
HAVING filters groups.

Example:

SELECT department_id, COUNT(*)
FROM employees
GROUP BY department_id
HAVING COUNT(*) > 10;

This means:

Group employees by department and return only departments
containing more than 10 employees.
""")


# ============================================================
# 28. JOINS
# ============================================================

print("\n" + "=" * 70)
print("28. JOINS")
print("=" * 70)

print("""
One of the most powerful features of relational databases
is the ability to combine data from multiple tables.

Suppose:

employees

employee_id | name  | department_id
------------+-------+--------------
1           | Rahul | 10
2           | Priya | 20


departments

department_id | department_name
--------------+----------------
10            | IT
20            | HR

We can combine them:

SELECT
    employees.name,
    departments.department_name
FROM employees
JOIN departments
    ON employees.department_id = departments.department_id;

Result:

Rahul | IT
Priya | HR
""")


# ============================================================
# 29. TYPES OF JOINS
# ============================================================

print("\n" + "=" * 70)
print("29. TYPES OF JOINS")
print("=" * 70)

print("""
Important joins include:

INNER JOIN
LEFT JOIN
RIGHT JOIN
FULL OUTER JOIN
CROSS JOIN
SELF JOIN

These will become extremely important as your SQL skills
progress.

INNER JOIN:

Returns matching records.

LEFT JOIN:

Returns all rows from the left table and matching rows
from the right table.

RIGHT JOIN:

Returns all rows from the right table and matching rows
from the left table.

FULL OUTER JOIN:

Returns matching and non-matching rows from both tables.

CROSS JOIN:

Produces combinations between rows.

SELF JOIN:

A table is joined with itself.
""")


# ============================================================
# 30. DATABASE-DRIVEN APPLICATION
# ============================================================

print("\n" + "=" * 70)
print("30. DATABASE-DRIVEN APPLICATIONS")
print("=" * 70)

print("""
Most modern applications depend on databases.

Examples:

Banking applications
E-commerce applications
Social media
Hospital management
Airline reservation systems
Government portals
Learning management systems
ERP systems
CRM systems
Food delivery applications

Consider an e-commerce application.

A simplified architecture:

             USER
               |
               v
         WEB / MOBILE UI
               |
               v
          APPLICATION
            SERVER
               |
               v
           DATABASE
               |
               v
           PostgreSQL


The user does not normally directly write SQL.

The application sends database requests.
""")


# ============================================================
# 31. REAL-WORLD E-COMMERCE EXAMPLE
# ============================================================

print("\n" + "=" * 70)
print("31. E-COMMERCE DATABASE EXAMPLE")
print("=" * 70)

print("""
An e-commerce application may contain:

customers
products
orders
order_items
payments
addresses
reviews
inventory
categories
suppliers

Example:

CUSTOMERS
---------
customer_id
name
email


PRODUCTS
--------
product_id
name
price
stock


ORDERS
------
order_id
customer_id
order_date
status


ORDER_ITEMS
-----------
order_item_id
order_id
product_id
quantity
price

Relationships:

Customer
   |
   | 1-to-many
   v
Orders
   |
   | 1-to-many
   v
Order Items
   |
   | many-to-one
   v
Products
""")


# ============================================================
# 32. SQL IN BANKING
# ============================================================

print("\n" + "=" * 70)
print("32. SQL IN BANKING")
print("=" * 70)

print("""
Banks rely heavily on database systems.

Possible tables:

customers
accounts
transactions
branches
loans
cards
beneficiaries

Example question:

"Find all transactions above ₹100,000."

SQL:

SELECT *
FROM transactions
WHERE amount > 100000;

Another question:

"Find total transaction amount for each customer."

SQL:

SELECT
    customer_id,
    SUM(amount)
FROM transactions
GROUP BY customer_id;
""")


# ============================================================
# 33. SQL IN DATA ANALYTICS
# ============================================================

print("\n" + "=" * 70)
print("33. SQL IN DATA ANALYTICS")
print("=" * 70)

print("""
SQL is one of the most important tools in data analytics.

Analysts use SQL to:

- Extract data
- Clean data
- Filter data
- Aggregate data
- Join datasets
- Calculate metrics
- Build reports
- Prepare datasets
- Analyze trends
- Create dashboards

Example:

SELECT
    department,
    AVG(salary) AS average_salary
FROM employees
GROUP BY department;
""")


# ============================================================
# 34. SQL IN DATA ENGINEERING
# ============================================================

print("\n" + "=" * 70)
print("34. SQL IN DATA ENGINEERING")
print("=" * 70)

print("""
Data engineers use SQL for:

- ETL
- ELT
- Data transformation
- Data warehouse development
- Data quality
- Pipeline processing
- Data modeling
- Partitioning
- Performance optimization

SQL is not limited to simple SELECT queries.

Modern SQL systems support very sophisticated analytical
workloads.
""")


# ============================================================
# 35. SQL IN BACKEND DEVELOPMENT
# ============================================================

print("\n" + "=" * 70)
print("35. SQL IN BACKEND DEVELOPMENT")
print("=" * 70)

print("""
Backend developers use SQL to build applications that need
persistent data.

For example:

Python/FastAPI
      |
      v
Business Logic
      |
      v
Database Driver / ORM
      |
      v
PostgreSQL

A backend API may receive:

GET /customers/101

The application might execute:

SELECT *
FROM customers
WHERE customer_id = 101;
""")


# ============================================================
# 36. SQL AND APIS
# ============================================================

print("\n" + "=" * 70)
print("36. SQL + APIs")
print("=" * 70)

print("""
A typical API request might look like:

Client
  |
  | GET /products
  v
Backend
  |
  | SQL query
  v
PostgreSQL
  |
  | result
  v
Backend
  |
  | JSON
  v
Client

SQL therefore often operates behind the scenes.
""")


# ============================================================
# 37. WHAT IS POSTGRESQL?
# ============================================================

print("\n" + "=" * 70)
print("37. WHAT IS POSTGRESQL?")
print("=" * 70)

print("""
PostgreSQL is an open-source relational database management
system.

It is commonly used for:

- Web applications
- Enterprise applications
- Analytics
- APIs
- Financial systems
- SaaS applications
- Data platforms
- Geospatial applications
- Complex transactional systems

PostgreSQL supports SQL and provides many additional features.

Examples include:

- Advanced indexing
- JSON/JSONB
- Window functions
- Common Table Expressions
- Full-text search
- Arrays
- Custom data types
- Extensions
- Strong transactional capabilities
""")


# ============================================================
# 38. SQL VS POSTGRESQL
# ============================================================

print("\n" + "=" * 70)
print("38. SQL VS POSTGRESQL")
print("=" * 70)

print("""
This distinction is extremely important.

SQL:

A language.

PostgreSQL:

A database management system.

Think:

SQL = language

PostgreSQL = software that understands SQL

Similar database systems include:

MySQL
Oracle Database
SQL Server
MariaDB
SQLite

They all support SQL but may have different features,
syntax extensions, and behavior.
""")


# ============================================================
# 39. SQL STANDARD
# ============================================================

print("\n" + "=" * 70)
print("39. SQL STANDARD")
print("=" * 70)

print("""
SQL has standardized concepts and syntax.

But different database systems implement SQL with their own
extensions and differences.

For example:

PostgreSQL has PostgreSQL-specific features.

MySQL has MySQL-specific behavior.

SQL Server has T-SQL.

Oracle has PL/SQL.

Therefore:

Learning standard SQL gives you transferable knowledge.

Learning PostgreSQL teaches you a concrete implementation
of relational database technology.
""")


# ============================================================
# 40. DATABASE SERVER
# ============================================================

print("\n" + "=" * 70)
print("40. DATABASE SERVER")
print("=" * 70)

print("""
A database server is the system that runs the database
management software.

Conceptually:

CLIENT
   |
   | SQL request
   v
DATABASE SERVER
   |
   v
DATABASE


PostgreSQL commonly operates as a server process.

A client connects to it and sends SQL commands.
""")


# ============================================================
# 41. DATABASE CLIENT
# ============================================================

print("\n" + "=" * 70)
print("41. DATABASE CLIENTS")
print("=" * 70)

print("""
A database client is software used to connect to and interact
with a database.

Examples:

psql
pgAdmin
DBeaver
DataGrip
Application code
Python database drivers

For PostgreSQL, psql is the official command-line client.

A graphical client can make database exploration easier.
""")


# ============================================================
# 42. DATABASE CONNECTION
# ============================================================

print("\n" + "=" * 70)
print("42. DATABASE CONNECTION")
print("=" * 70)

print("""
A client normally needs information such as:

Host
Port
Database name
Username
Password

A conceptual PostgreSQL connection:

Host     = localhost
Port     = 5432
Database = company
User     = postgres

The default PostgreSQL port is commonly:

5432
""")


# ============================================================
# 43. DATABASE OBJECTS
# ============================================================

print("\n" + "=" * 70)
print("43. DATABASE OBJECTS")
print("=" * 70)

print("""
A PostgreSQL database can contain many objects.

Examples:

Database
Schema
Table
View
Materialized View
Index
Sequence
Function
Procedure
Trigger
Constraint
Type

You will encounter these progressively throughout the SQL
learning journey.
""")


# ============================================================
# 44. SCHEMAS
# ============================================================

print("\n" + "=" * 70)
print("44. SCHEMA")
print("=" * 70)

print("""
A schema is a namespace inside a database.

A simplified structure:

PostgreSQL Server
    |
    +-- Database
          |
          +-- Schema
                |
                +-- Tables
                +-- Views
                +-- Functions
                +-- Sequences

PostgreSQL commonly provides a schema named:

public

Example:

public.employees
""")


# ============================================================
# 45. BASIC CREATE TABLE
# ============================================================

print("\n" + "=" * 70)
print("45. CREATE TABLE")
print("=" * 70)

print("""
Example:

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    salary NUMERIC(12,2),
    active BOOLEAN DEFAULT TRUE
);

This creates a table named employees.

Important concepts:

PRIMARY KEY
NOT NULL
UNIQUE
DEFAULT
DATA TYPES
""")


# ============================================================
# 46. INSERT
# ============================================================

print("\n" + "=" * 70)
print("46. INSERT")
print("=" * 70)

print("""
INSERT adds rows.

Example:

INSERT INTO employees
(employee_id, name, email, salary)
VALUES
(1, 'Rahul', 'rahul@example.com', 90000);

Multiple rows:

INSERT INTO employees
(employee_id, name, email, salary)
VALUES
(2, 'Priya', 'priya@example.com', 85000),
(3, 'Amit', 'amit@example.com', 95000);
""")


# ============================================================
# 47. UPDATE
# ============================================================

print("\n" + "=" * 70)
print("47. UPDATE")
print("=" * 70)

print("""
UPDATE changes existing records.

Example:

UPDATE employees
SET salary = 100000
WHERE employee_id = 1;

IMPORTANT:

Never casually run:

UPDATE employees
SET salary = 100000;

unless you intentionally want to update every row.

The WHERE clause is often critical.
""")


# ============================================================
# 48. DELETE
# ============================================================

print("\n" + "=" * 70)
print("48. DELETE")
print("=" * 70)

print("""
DELETE removes rows.

Example:

DELETE FROM employees
WHERE employee_id = 3;

Again, be careful.

This:

DELETE FROM employees;

can delete every row in the table.

SQL gives enormous power.

That means SQL requires discipline.
""")


# ============================================================
# 49. NULL
# ============================================================

print("\n" + "=" * 70)
print("49. NULL")
print("=" * 70)

print("""
NULL is one of the most misunderstood concepts in SQL.

NULL generally represents:

unknown
missing
not provided
not applicable

NULL is NOT the same as:

0
''
FALSE

Example:

salary = NULL

does not mean:

salary = 0

To check NULL:

SELECT *
FROM employees
WHERE email IS NULL;

Not:

WHERE email = NULL

This distinction will become very important later.
""")


# ============================================================
# 50. CONSTRAINTS
# ============================================================

print("\n" + "=" * 70)
print("50. CONSTRAINTS")
print("=" * 70)

print("""
Constraints enforce rules on data.

Important constraints:

PRIMARY KEY
FOREIGN KEY
UNIQUE
NOT NULL
CHECK
DEFAULT

Example:

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    age INTEGER CHECK (age >= 18),
    email TEXT UNIQUE,
    name TEXT NOT NULL
);

Constraints protect data integrity.
""")


# ============================================================
# 51. DATA INTEGRITY
# ============================================================

print("\n" + "=" * 70)
print("51. DATA INTEGRITY")
print("=" * 70)

print("""
Data integrity means keeping data accurate, valid,
consistent, and reliable.

Examples:

An employee cannot have two identical employee IDs.

A foreign key should not reference a nonexistent department.

An employee's age should not be negative.

An email that must be unique should not appear twice.

Database constraints help enforce these rules.
""")


# ============================================================
# 52. TRANSACTIONS
# ============================================================

print("\n" + "=" * 70)
print("52. TRANSACTIONS")
print("=" * 70)

print("""
A transaction groups multiple database operations into
a logical unit of work.

Example:

Bank transfer:

Account A:
    -1000

Account B:
    +1000

Both operations should succeed together.

If the first succeeds but the second fails, the database
should not leave the system in an inconsistent state.

Conceptually:

BEGIN;

UPDATE accounts
SET balance = balance - 1000
WHERE account_id = 1;

UPDATE accounts
SET balance = balance + 1000
WHERE account_id = 2;

COMMIT;

If something goes wrong:

ROLLBACK;
""")


# ============================================================
# 53. ACID
# ============================================================

print("\n" + "=" * 70)
print("53. ACID")
print("=" * 70)

print("""
Relational databases are strongly associated with ACID
transactions.

A = Atomicity
C = Consistency
I = Isolation
D = Durability

ATOMICITY:

All operations in a transaction happen or none happen.

CONSISTENCY:

Transactions preserve defined integrity rules.

ISOLATION:

Concurrent transactions should not improperly interfere
with one another.

DURABILITY:

Committed changes survive system failures.

We will study ACID deeply later.
""")


# ============================================================
# 54. QUERY EXECUTION CONCEPT
# ============================================================

print("\n" + "=" * 70)
print("54. WHAT HAPPENS WHEN SQL RUNS?")
print("=" * 70)

print("""
Consider:

SELECT name
FROM employees
WHERE salary > 100000;

A simplified conceptual process is:

1. Client sends SQL
2. Database parses SQL
3. Database validates objects
4. Query planner/optimizer evaluates possible strategies
5. Database chooses an execution plan
6. Execution engine accesses required data
7. Results are produced
8. Results are returned to client

This is simplified.

Real database execution is considerably more sophisticated.
""")


# ============================================================
# 55. QUERY OPTIMIZER
# ============================================================

print("\n" + "=" * 70)
print("55. QUERY OPTIMIZER")
print("=" * 70)

print("""
The query optimizer tries to determine an efficient way
to execute a SQL query.

Suppose you write:

SELECT *
FROM employees
WHERE employee_id = 100;

If employee_id has an index, PostgreSQL may use that index
rather than scanning every row.

The important principle is:

SQL tells the database WHAT you want.

The optimizer helps determine HOW to obtain it efficiently.
""")


# ============================================================
# 56. INDEX INTRODUCTION
# ============================================================

print("\n" + "=" * 70)
print("56. INDEX - BASIC INTRODUCTION")
print("=" * 70)

print("""
An index is a database structure designed to make certain
queries faster.

Imagine a book.

Without an index:

You may scan every page.

With an index:

You can jump toward the relevant section.

Database indexes serve a similar conceptual purpose.

Example:

CREATE INDEX idx_employee_email
ON employees(email);

Indexes can dramatically improve reads.

But indexes also have costs:

- Additional storage
- Slower writes
- Maintenance overhead

Index design will be studied later.
""")


# ============================================================
# 57. SQL SECURITY
# ============================================================

print("\n" + "=" * 70)
print("57. SQL AND SECURITY")
print("=" * 70)

print("""
Databases contain sensitive information.

Examples:

Passwords
Financial records
Customer data
Medical records
Personal information
Business data

Database security includes:

- Authentication
- Authorization
- Roles
- Privileges
- Encryption
- Auditing
- Secure connections
- Access control

PostgreSQL provides role and privilege systems.
""")


# ============================================================
# 58. SQL IN ENTERPRISE
# ============================================================

print("\n" + "=" * 70)
print("58. SQL IN ENTERPRISE SYSTEMS")
print("=" * 70)

print("""
SQL can be found across many enterprise environments.

Examples:

ERP
CRM
Banking
Insurance
Telecommunications
Healthcare
Government
Manufacturing
Retail
Logistics
Education
Media
Cybersecurity

Large organizations may operate databases containing
billions of records.

This is why SQL performance, modeling, indexing,
transactions, security, and reliability matter.
""")


# ============================================================
# 59. SQL AND BIG DATA
# ============================================================

print("\n" + "=" * 70)
print("59. SQL AND MODERN DATA PLATFORMS")
print("=" * 70)

print("""
SQL is not limited to traditional relational databases.

Many modern data platforms provide SQL interfaces.

Examples of technologies in the broader data ecosystem include:

Data warehouses
Data lakes
Lakehouses
Distributed SQL engines
Cloud databases
Analytical databases

Therefore SQL remains extremely relevant even when the
underlying architecture becomes very large.
""")


# ============================================================
# 60. OLTP VS OLAP
# ============================================================

print("\n" + "=" * 70)
print("60. OLTP VS OLAP")
print("=" * 70)

print("""
Two important database workload categories are:

OLTP
Online Transaction Processing

OLAP
Online Analytical Processing


OLTP:

Designed for frequent transactional operations.

Examples:

Bank transaction
Order placement
Account update
Booking


OLAP:

Designed for analytical queries.

Examples:

Revenue analysis
Customer segmentation
Monthly sales reports
Business intelligence


OLTP tends to focus on:

- Transactions
- Consistency
- Low latency
- Frequent writes


OLAP tends to focus on:

- Large scans
- Aggregations
- Historical analysis
- Complex queries
""")


# ============================================================
# 61. RELATIONAL VS NON-RELATIONAL
# ============================================================

print("\n" + "=" * 70)
print("61. RELATIONAL VS NON-RELATIONAL DATABASES")
print("=" * 70)

print("""
RELATIONAL DATABASES:

Data is modeled using relations/tables.

Examples:

PostgreSQL
MySQL
Oracle
SQL Server


NON-RELATIONAL DATABASES:

Often grouped under the NoSQL category.

Examples:

Document databases
Key-value stores
Graph databases
Wide-column databases

Examples of systems include:

MongoDB
Redis
Neo4j
Cassandra

The choice depends on workload, data model, consistency
requirements, scalability requirements, and application needs.
""")


# ============================================================
# 62. SQL IS NOT A DATABASE
# ============================================================

print("\n" + "=" * 70)
print("62. IMPORTANT DISTINCTION")
print("=" * 70)

print("""
Remember:

SQL is NOT a database.

PostgreSQL is NOT SQL.

Correct conceptual relationship:

SQL
  |
  | language
  v
Relational Database Management System
  |
  v
PostgreSQL

PostgreSQL implements SQL and provides many capabilities
beyond the SQL language itself.
""")


# ============================================================
# 63. SQL IS NOT EXCEL
# ============================================================

print("\n" + "=" * 70)
print("63. SQL VS EXCEL")
print("=" * 70)

print("""
Excel is a spreadsheet application.

SQL is a language used to interact with databases.

Excel is excellent for:

- Small/medium manual analysis
- Spreadsheet modeling
- Charts
- Quick calculations
- Business reporting

Databases are designed for:

- Persistent structured storage
- Concurrent users
- Large datasets
- Transactions
- Data integrity
- Application backends
- Controlled access

They solve overlapping but different problems.
""")


# ============================================================
# 64. SQL IN A TYPICAL SOFTWARE STACK
# ============================================================

print("\n" + "=" * 70)
print("64. SQL IN A SOFTWARE STACK")
print("=" * 70)

print("""
A typical web application might look like:

FRONTEND
HTML
CSS
JavaScript
React

        |
        v

BACKEND
Python
FastAPI

        |
        v

DATABASE DRIVER / ORM

        |
        v

SQL

        |
        v

POSTGRESQL

        |
        v

DATABASE STORAGE

Each layer has a different responsibility.
""")


# ============================================================
# 65. ORM INTRODUCTION
# ============================================================

print("\n" + "=" * 70)
print("65. ORM")
print("=" * 70)

print("""
ORM means:

Object-Relational Mapping

An ORM allows application developers to interact with
database structures using programming-language objects.

Examples in Python include:

SQLAlchemy
Django ORM

Instead of manually writing every SQL statement, developers
can sometimes write application-level code that generates SQL.

But:

Knowing SQL remains important.

An ORM does not eliminate the need to understand databases.
""")


# ============================================================
# 66. SQL IN PYTHON
# ============================================================

print("\n" + "=" * 70)
print("66. PYTHON + POSTGRESQL")
print("=" * 70)

print("""
Python can communicate with PostgreSQL through database
drivers.

Examples include:

psycopg
asyncpg

A simplified conceptual example:

Python application
        |
        v
PostgreSQL driver
        |
        v
SQL query
        |
        v
PostgreSQL


Example conceptual Python code:

connection = connect(...)
cursor = connection.cursor()

cursor.execute(
    "SELECT * FROM employees;"
)

rows = cursor.fetchall()

The exact implementation depends on the library.
""")


# ============================================================
# 67. PARAMETERIZED QUERIES
# ============================================================

print("\n" + "=" * 70)
print("67. PARAMETERIZED QUERIES")
print("=" * 70)

print("""
Applications should generally use parameterized queries
rather than constructing SQL by directly concatenating
untrusted user input.

Unsafe conceptual pattern:

query = "SELECT * FROM users WHERE name = '" + user_input + "'"

This can contribute to SQL injection vulnerabilities.

Safer pattern:

Use parameters provided by the database driver.

Conceptually:

cursor.execute(
    "SELECT * FROM users WHERE name = %s",
    (user_input,)
)

The exact placeholder syntax depends on the driver.

SQL injection and secure database programming will be covered
later in depth.
""")


# ============================================================
# 68. SQL IN CYBERSECURITY
# ============================================================

print("\n" + "=" * 70)
print("68. SQL AND CYBERSECURITY")
print("=" * 70)

print("""
SQL is important in cybersecurity because databases contain
valuable information.

Security professionals should understand:

- SQL injection
- Database privileges
- Authentication
- Authorization
- Database auditing
- Sensitive data exposure
- Access control
- Secure queries
- Database logging

Example vulnerability category:

SQL Injection

A malicious user may manipulate poorly constructed SQL
statements.

Understanding SQL is therefore valuable for both developers
and security professionals.
""")


# ============================================================
# 69. SQL IN BUSINESS INTELLIGENCE
# ============================================================

print("\n" + "=" * 70)
print("69. SQL AND BUSINESS INTELLIGENCE")
print("=" * 70)

print("""
Business intelligence systems often depend on SQL.

Example questions:

What was revenue last month?

Which products sell the most?

Which customers are most valuable?

Which region has the highest sales?

What is the average order value?

SQL can transform raw transactional data into information
used for dashboards and decision-making.
""")


# ============================================================
# 70. SQL MENTAL MODEL
# ============================================================

print("\n" + "=" * 70)
print("70. THE SQL MENTAL MODEL")
print("=" * 70)

print("""
When learning SQL, develop this mental model:

DATABASE
    |
    +-- SCHEMAS
          |
          +-- TABLES
                |
                +-- COLUMNS
                +-- ROWS
                +-- CONSTRAINTS
                +-- INDEXES
                +-- RELATIONSHIPS


When writing a query, think:

1. What data do I need?
2. Which table contains it?
3. Which other tables are needed?
4. How are those tables related?
5. Which rows should be included?
6. Which columns should be returned?
7. Do I need aggregation?
8. Do I need grouping?
9. Do I need sorting?
10. Could performance become an issue?
""")


# ============================================================
# 71. SQL QUERY THINKING
# ============================================================

print("\n" + "=" * 70)
print("71. EXAMPLE QUERY THINKING")
print("=" * 70)

print("""
Question:

"Find the top 5 highest-paid employees in the IT department."

Think step by step:

1. Table?
   employees

2. Columns?
   name
   salary
   department

3. Filter?
   department = 'IT'

4. Sort?
   salary DESC

5. Limit?
   5

SQL:

SELECT name, salary
FROM employees
WHERE department = 'IT'
ORDER BY salary DESC
LIMIT 5;

This way of thinking is more important than memorizing
syntax blindly.
""")


# ============================================================
# 72. SQL CLAUSE ORDER
# ============================================================

print("\n" + "=" * 70)
print("72. COMMON SQL CLAUSE ORDER")
print("=" * 70)

print("""
A common SELECT query is written approximately as:

SELECT
FROM
WHERE
GROUP BY
HAVING
ORDER BY
LIMIT

Example:

SELECT department, AVG(salary)
FROM employees
WHERE active = TRUE
GROUP BY department
HAVING AVG(salary) > 80000
ORDER BY AVG(salary) DESC
LIMIT 10;

Later we will learn that the logical execution order is
not exactly the same as the written order.

That distinction becomes important for advanced SQL.
""")


# ============================================================
# 73. COMMENTS IN SQL
# ============================================================

print("\n" + "=" * 70)
print("73. SQL COMMENTS")
print("=" * 70)

print("""
Single-line comment:

-- This is a comment

Multi-line comment:

/*
This is
a multi-line
comment
*/

Comments are useful for documenting complex queries.
""")


# ============================================================
# 74. CASE SENSITIVITY
# ============================================================

print("\n" + "=" * 70)
print("74. CASE SENSITIVITY")
print("=" * 70)

print("""
SQL keywords are commonly written in uppercase:

SELECT
FROM
WHERE

But SQL is generally not dependent on keyword capitalization.

These are commonly equivalent:

select * from employees;

SELECT * FROM employees;

SQL formatting conventions usually prefer uppercase keywords
because it improves readability.
""")


# ============================================================
# 75. SQL STYLE
# ============================================================

print("\n" + "=" * 70)
print("75. SQL WRITING STYLE")
print("=" * 70)

print("""
Prefer readable SQL.

Less readable:

SELECT name,salary FROM employees WHERE salary>100000 ORDER BY salary DESC;

More readable:

SELECT
    name,
    salary
FROM employees
WHERE salary > 100000
ORDER BY salary DESC;

Readable SQL is easier to:

- Debug
- Review
- Maintain
- Optimize
- Explain
""")


# ============================================================
# 76. COMMON BEGINNER MISTAKES
# ============================================================

print("\n" + "=" * 70)
print("76. COMMON BEGINNER MISTAKES")
print("=" * 70)

mistakes = [
    "Confusing SQL with PostgreSQL",
    "Thinking SQL is only SELECT",
    "Forgetting WHERE in UPDATE",
    "Forgetting WHERE in DELETE",
    "Confusing NULL with zero",
    "Confusing NULL with an empty string",
    "Using SELECT * unnecessarily",
    "Not understanding primary keys",
    "Not understanding foreign keys",
    "Ignoring relationships between tables",
    "Ignoring data types",
    "Writing unreadable SQL",
    "Ignoring indexes",
    "Ignoring transactions",
    "Ignoring security"
]

for number, mistake in enumerate(mistakes, start=1):
    print(f"{number}. {mistake}")


# ============================================================
# 77. SQL LEARNING ROADMAP
# ============================================================

print("\n" + "=" * 70)
print("77. SQL LEARNING ROADMAP")
print("=" * 70)

print("""
After today's introduction, the learning journey can progress
through:

LEVEL 1 - FUNDAMENTALS

SELECT
WHERE
ORDER BY
LIMIT
DISTINCT
NULL
operators


LEVEL 2 - DATA MANIPULATION

INSERT
UPDATE
DELETE


LEVEL 3 - AGGREGATION

COUNT
SUM
AVG
MIN
MAX
GROUP BY
HAVING


LEVEL 4 - JOINS

INNER JOIN
LEFT JOIN
RIGHT JOIN
FULL JOIN
CROSS JOIN
SELF JOIN


LEVEL 5 - INTERMEDIATE SQL

Subqueries
CTEs
CASE
COALESCE
String functions
Date functions
Conditional logic


LEVEL 6 - ADVANCED SQL

Window functions
Recursive CTEs
Advanced aggregation
Set operations
LATERAL
Advanced joins


LEVEL 7 - DATABASE DESIGN

Normalization
Keys
Constraints
Relationships
ER modeling


LEVEL 8 - POSTGRESQL

Schemas
Sequences
Identity columns
JSONB
Arrays
Extensions
PostgreSQL-specific features


LEVEL 9 - PERFORMANCE

Indexes
EXPLAIN
EXPLAIN ANALYZE
Query planning
Statistics
Vacuum
Analyze


LEVEL 10 - DATABASE ENGINEERING

Transactions
Isolation
Locks
Concurrency
Deadlocks
MVCC


LEVEL 11 - SECURITY

Roles
Privileges
GRANT
REVOKE
SQL injection
Auditing


LEVEL 12 - EXPERT SQL

Query optimization
Advanced window functions
Recursive queries
Partitioning
Materialized views
Advanced indexing
Concurrency internals
Database architecture
""")


# ============================================================
# 78. MINI PRACTICE DATABASE
# ============================================================

print("\n" + "=" * 70)
print("78. MINI PRACTICE DATABASE")
print("=" * 70)

print("""
Use this schema throughout your SQL learning journey.

CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    department_id INTEGER,
    salary NUMERIC(12,2),
    joining_date DATE,
    active BOOLEAN DEFAULT TRUE,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

Sample departments:

1 | IT
2 | HR
3 | Finance
4 | Marketing

Sample employees:

101 | Rahul | IT       | 90000
102 | Priya | HR       | 80000
103 | Amit  | Finance  | 95000
104 | Neha  | IT       | 120000
105 | Ravi  | Marketing| 70000
""")


# ============================================================
# 79. PRACTICE QUESTIONS
# ============================================================

print("\n" + "=" * 70)
print("79. PRACTICE QUESTIONS")
print("=" * 70)

questions = [
    "What is SQL?",
    "Why do databases exist?",
    "What is a DBMS?",
    "What is PostgreSQL?",
    "How is SQL different from PostgreSQL?",
    "What is a relational database?",
    "What is a table?",
    "What is a row?",
    "What is a column?",
    "What is a primary key?",
    "What is a foreign key?",
    "What is a relationship?",
    "What is CRUD?",
    "What does SELECT do?",
    "What does WHERE do?",
    "What does ORDER BY do?",
    "What does GROUP BY do?",
    "What does HAVING do?",
    "What is a JOIN?",
    "What is NULL?",
    "What is a constraint?",
    "Why are transactions important?",
    "What does ACID mean?",
    "What is an index?",
    "What is SQL injection?",
    "Why is SQL important for data analytics?",
    "Why is SQL important for backend development?"
]

for number, question in enumerate(questions, start=1):
    print(f"{number}. {question}")


# ============================================================
# 80. MINI QUIZ
# ============================================================

print("\n" + "=" * 70)
print("80. MINI QUIZ")
print("=" * 70)

quiz = [
    {
        "question": "SQL stands for?",
        "answer": "Structured Query Language"
    },
    {
        "question": "PostgreSQL is?",
        "answer": "A relational database management system"
    },
    {
        "question": "What identifies a row uniquely?",
        "answer": "Primary key"
    },
    {
        "question": "Which SQL command retrieves data?",
        "answer": "SELECT"
    },
    {
        "question": "Which clause filters rows?",
        "answer": "WHERE"
    },
    {
        "question": "Which clause sorts results?",
        "answer": "ORDER BY"
    },
    {
        "question": "Which command adds data?",
        "answer": "INSERT"
    },
    {
        "question": "Which command modifies existing data?",
        "answer": "UPDATE"
    },
    {
        "question": "Which command removes rows?",
        "answer": "DELETE"
    },
    {
        "question": "Which command finalizes a transaction?",
        "answer": "COMMIT"
    }
]

for index, item in enumerate(quiz, start=1):
    print(f"\nQ{index}: {item['question']}")
    print(f"Answer: {item['answer']}")


# ============================================================
# 81. CONCEPT MAP
# ============================================================

print("\n" + "=" * 70)
print("81. CONCEPT MAP")
print("=" * 70)

print("""
                         SQL
                          |
          +---------------+---------------+
          |               |               |
       QUERYING       MODIFYING       DEFINING
          |               |               |
       SELECT        INSERT/UPDATE      CREATE
       WHERE         DELETE             ALTER
       JOIN                             DROP
       GROUP BY
          |
          v
    RELATIONAL DATABASE
          |
    +-----+-----+
    |           |
 TABLES      RELATIONSHIPS
    |           |
 ROWS       PRIMARY KEY
 COLUMNS    FOREIGN KEY
    |
    v
 POSTGRESQL
    |
    +-----------------------------+
    |             |               |
 TRANSACTIONS   INDEXES        SECURITY
    |
   ACID
""")


# ============================================================
# 82. FINAL TAKEAWAYS
# ============================================================

print("\n" + "=" * 70)
print("82. FINAL TAKEAWAYS")
print("=" * 70)

print("""
You should now understand:

1. Data is a collection of facts and values.

2. Databases provide organized and persistent data storage.

3. A DBMS manages databases.

4. SQL stands for Structured Query Language.

5. SQL is primarily used to interact with relational databases.

6. PostgreSQL is a relational database management system.

7. SQL and PostgreSQL are not the same thing.

8. Relational databases organize data into tables.

9. Tables contain rows and columns.

10. Primary keys uniquely identify records.

11. Foreign keys establish relationships between tables.

12. SQL supports querying and modifying data.

13. SELECT retrieves data.

14. INSERT adds data.

15. UPDATE modifies data.

16. DELETE removes data.

17. WHERE filters rows.

18. GROUP BY groups rows.

19. HAVING filters groups.

20. ORDER BY sorts results.

21. JOIN combines related tables.

22. Constraints protect data integrity.

23. Transactions allow operations to be treated as logical units.

24. ACID describes important transaction properties.

25. Indexes can improve query performance.

26. SQL is heavily used in analytics.

27. SQL is heavily used in backend development.

28. SQL is important in data engineering.

29. SQL is important in cybersecurity.

30. SQL knowledge is transferable across many database systems.
""")


# ============================================================
# 83. DAY 01 COMPLETION CHECK
# ============================================================

print("\n" + "=" * 70)
print("83. DAY 01 COMPLETION CHECK")
print("=" * 70)

checklist = [
    "I understand what data is.",
    "I understand why databases exist.",
    "I understand what a DBMS is.",
    "I understand what SQL is.",
    "I understand why SQL exists.",
    "I understand relational databases.",
    "I understand tables, rows and columns.",
    "I understand primary keys.",
    "I understand foreign keys.",
    "I understand basic relationships.",
    "I understand CRUD.",
    "I understand PostgreSQL.",
    "I understand SQL vs PostgreSQL.",
    "I understand basic SQL commands.",
    "I understand database-driven applications.",
    "I understand the role of SQL in analytics.",
    "I understand the role of SQL in backend systems.",
    "I understand the basics of transactions.",
    "I understand ACID at a high level.",
    "I understand the basic purpose of indexes."
]

for item in checklist:
    print("[ ] " + item)


# ============================================================
# 84. FINAL MESSAGE
# ============================================================

print("\n" + "=" * 70)
print("DAY 01 COMPLETE")
print("=" * 70)

print("""
Congratulations.

You have completed the conceptual introduction to SQL.

Do not worry if the syntax is not yet memorized.

At this stage, focus on understanding:

DATA
DATABASE
DBMS
RELATIONAL MODEL
TABLE
ROW
COLUMN
PRIMARY KEY
FOREIGN KEY
SQL
POSTGRESQL
CRUD
QUERY
JOIN
CONSTRAINT
TRANSACTION
ACID
INDEX

The next stage is to start writing SQL queries repeatedly.

The goal is not to memorize SQL.

The goal is to learn how to THINK in SQL.

============================================================
END OF DAY 01
============================================================
""")
