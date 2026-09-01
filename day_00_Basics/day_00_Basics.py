# ============================================================
# DAY 00: SQL FUNDAMENTALS
# ============================================================

print("DAY 01 - SQL FUNDAMENTALS")


# ============================================================
# 1. WHAT IS SQL?
# ============================================================

print("\n1. WHAT IS SQL?")

print("SQL stands for Structured Query Language.")
print("It is used to interact with relational databases.")
print("SQL can be used to create, read, update, and delete data.")


# ============================================================
# 2. WHAT IS A DATABASE?
# ============================================================

print("\n2. WHAT IS A DATABASE?")

print("A database is an organized collection of data")
print("that can be stored, managed, and retrieved efficiently.")


# ============================================================
# 3. RELATIONAL DATABASE
# ============================================================

print("\n3. RELATIONAL DATABASE")

print("A relational database organizes data into tables.")
print("Tables can be connected using relationships.")


# ============================================================
# 4. TABLE
# ============================================================

print("\n4. TABLE")

students = [
    {"id": 1, "name": "Alice", "age": 21, "course": "Python"},
    {"id": 2, "name": "Bob", "age": 22, "course": "SQL"},
    {"id": 3, "name": "Charlie", "age": 20, "course": "Python"},
    {"id": 4, "name": "David", "age": 23, "course": "SQL"}
]

print("Students Table:")

for student in students:
    print(student)


# ============================================================
# 5. ROWS AND COLUMNS
# ============================================================

print("\n5. ROWS AND COLUMNS")

print("Columns:")
print("- id")
print("- name")
print("- age")
print("- course")

print("\nNumber of rows:", len(students))


# ============================================================
# 6. PRIMARY KEY
# ============================================================

print("\n6. PRIMARY KEY")

print("A primary key uniquely identifies each record.")

primary_keys = []

for student in students:
    primary_keys.append(student["id"])

print("Primary Key Values:", primary_keys)

if len(primary_keys) == len(set(primary_keys)):
    print("All primary key values are unique.")


# ============================================================
# 7. SQL CRUD OPERATIONS
# ============================================================

print("\n7. SQL CRUD OPERATIONS")

crud = {
    "CREATE": "Create database objects",
    "READ": "Retrieve data",
    "UPDATE": "Modify existing data",
    "DELETE": "Remove data"
}

for operation, meaning in crud.items():
    print(operation, "->", meaning)


# ============================================================
# 8. SELECT
# ============================================================

print("\n8. SELECT")

print("SQL Example:")
print("SELECT * FROM students;")

print("\nEquivalent Python concept:")

for student in students:
    print(student)


# ============================================================
# 9. SELECT SPECIFIC COLUMNS
# ============================================================

print("\n9. SELECT SPECIFIC COLUMNS")

print("SQL Example:")
print("SELECT name, course FROM students;")

for student in students:
    print(student["name"], "->", student["course"])


# ============================================================
# 10. WHERE
# ============================================================

print("\n10. WHERE")

print("SQL Example:")
print("SELECT * FROM students WHERE age > 21;")

for student in students:

    if student["age"] > 21:
        print(student)


# ============================================================
# 11. AND / OR
# ============================================================

print("\n11. AND / OR")

print("SQL Example:")
print("""
SELECT *
FROM students
WHERE age > 20
AND course = 'SQL';
""")

for student in students:

    if student["age"] > 20 and student["course"] == "SQL":
        print(student)


# ============================================================
# 12. ORDER BY
# ============================================================

print("\n12. ORDER BY")

print("SQL Example:")
print("SELECT * FROM students ORDER BY age;")

sorted_students = sorted(
    students,
    key=lambda student: student["age"]
)

for student in sorted_students:
    print(student)


# ============================================================
# 13. LIMIT
# ============================================================

print("\n13. LIMIT")

print("SQL Example:")
print("SELECT * FROM students LIMIT 2;")

for student in students[:2]:
    print(student)


# ============================================================
# 14. INSERT
# ============================================================

print("\n14. INSERT")

print("SQL Example:")
print("""
INSERT INTO students
(id, name, age, course)
VALUES
(5, 'Emma', 21, 'Python');
""")

new_student = {
    "id": 5,
    "name": "Emma",
    "age": 21,
    "course": "Python"
}

students.append(new_student)

print("New Student Added:", new_student)


# ============================================================
# 15. UPDATE
# ============================================================

print("\n15. UPDATE")

print("SQL Example:")
print("""
UPDATE students
SET course = 'SQL'
WHERE id = 5;
""")

for student in students:

    if student["id"] == 5:
        student["course"] = "SQL"

print("Updated Student:", students[-1])


# ============================================================
# 16. DELETE
# ============================================================

print("\n16. DELETE")

print("SQL Example:")
print("""
DELETE FROM students
WHERE id = 5;
""")

students = [
    student
    for student in students
    if student["id"] != 5
]

print("Remaining Records:", len(students))


# ============================================================
# 17. AGGREGATE FUNCTIONS
# ============================================================

print("\n17. AGGREGATE FUNCTIONS")

ages = [student["age"] for student in students]

print("COUNT:", len(ages))
print("SUM:", sum(ages))
print("MIN:", min(ages))
print("MAX:", max(ages))
print("AVG:", sum(ages) / len(ages))

print("\nCommon SQL aggregate functions:")
print("- COUNT()")
print("- SUM()")
print("- AVG()")
print("- MIN()")
print("- MAX()")


# ============================================================
# 18. GROUP BY
# ============================================================

print("\n18. GROUP BY")

print("SQL Example:")
print("""
SELECT course, COUNT(*)
FROM students
GROUP BY course;
""")

course_count = {}

for student in students:

    course = student["course"]

    if course not in course_count:
        course_count[course] = 0

    course_count[course] += 1

for course, count in course_count.items():
    print(course, "->", count)


# ============================================================
# 19. DATABASE RELATIONSHIPS
# ============================================================

print("\n19. DATABASE RELATIONSHIPS")

courses = [
    {"course_id": 101, "course_name": "Python"},
    {"course_id": 102, "course_name": "SQL"}
]

print("Students Table")
for student in students:
    print(student)

print("\nCourses Table")
for course in courses:
    print(course)


# ============================================================
# 20. FOREIGN KEY
# ============================================================

print("\n20. FOREIGN KEY")

print("A foreign key connects a record in one table")
print("to a related record in another table.")

print("\nExample:")
print("students.course_id -> courses.course_id")


# ============================================================
# 21. JOINS
# ============================================================

print("\n21. JOINS")

print("Common SQL JOIN types:")

joins = [
    "INNER JOIN",
    "LEFT JOIN",
    "RIGHT JOIN",
    "FULL OUTER JOIN"
]

for join in joins:
    print("-", join)


# ============================================================
# 22. INNER JOIN CONCEPT
# ============================================================

print("\n22. INNER JOIN CONCEPT")

print("""
Students
   +
Courses
   ↓
Matching Records
""")

print("An INNER JOIN returns records that have")
print("matching values in both tables.")


# ============================================================
# 23. CONSTRAINTS
# ============================================================

print("\n23. DATABASE CONSTRAINTS")

constraints = [
    "PRIMARY KEY",
    "FOREIGN KEY",
    "NOT NULL",
    "UNIQUE",
    "CHECK",
    "DEFAULT"
]

for constraint in constraints:
    print("-", constraint)


# ============================================================
# 24. DATABASE DESIGN
# ============================================================

print("\n24. BASIC DATABASE DESIGN")

design_steps = [
    "Identify entities",
    "Identify attributes",
    "Create tables",
    "Define primary keys",
    "Define relationships",
    "Apply constraints",
    "Reduce unnecessary duplication"
]

for step_number, step in enumerate(design_steps, start=1):
    print(step_number, "->", step)


# ============================================================
# 25. NORMALIZATION
# ============================================================

print("\n25. NORMALIZATION")

print("Normalization is a database design technique")
print("used to organize data and reduce unnecessary")
print("duplication and update problems.")

print("\nCommon normal forms:")
print("- 1NF")
print("- 2NF")
print("- 3NF")


# ============================================================
# 26. TRANSACTIONS
# ============================================================

print("\n26. DATABASE TRANSACTIONS")

print("A transaction is a logical unit of database work.")

transaction_properties = [
    "Atomicity",
    "Consistency",
    "Isolation",
    "Durability"
]

for property_name in transaction_properties:
    print("-", property_name)


# ============================================================
# 27. SQL CATEGORIES
# ============================================================

print("\n27. SQL COMMAND CATEGORIES")

sql_categories = {
    "DDL": "Data Definition Language",
    "DML": "Data Manipulation Language",
    "DQL": "Data Query Language",
    "DCL": "Data Control Language",
    "TCL": "Transaction Control Language"
}

for category, meaning in sql_categories.items():
    print(category, "->", meaning)


# ============================================================
# 28. BASIC SQL WORKFLOW
# ============================================================

print("\n28. BASIC SQL WORKFLOW")

print("""
Database
    ↓
Table
    ↓
SQL Query
    ↓
Filter / Sort / Group / Join
    ↓
Result
    ↓
Analysis / Application
""")


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("DAY 01 COMPLETED")
print("=" * 60)

print("""
Today you learned:

1. SQL
2. Databases
3. Relational Databases
4. Tables
5. Rows and Columns
6. Primary Keys
7. CRUD Operations
8. SELECT
9. WHERE
10. AND / OR
11. ORDER BY
12. LIMIT
13. INSERT
14. UPDATE
15. DELETE
16. Aggregate Functions
17. GROUP BY
18. Database Relationships
19. Foreign Keys
20. JOINs
21. Constraints
22. Database Design
23. Normalization
24. Transactions and ACID
25. SQL Command Categories
26. Basic SQL Workflow
""")

