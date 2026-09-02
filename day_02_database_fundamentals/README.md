# Database Fundamentals

## Overview

This learning exercise covers the fundamental concepts of databases, relational database systems, SQL, database design, data integrity, transactions, concurrency, indexing, performance, security, scalability, and modern database architecture.

The practical code was used as a way to understand how these concepts behave in an actual database environment. The objective was not only to learn database terminology, but to understand how data is structured, connected, queried, protected, modified, and maintained throughout the lifecycle of an application.

The concepts covered range from basic database terminology to advanced topics such as transaction isolation, query optimization, replication, partitioning, sharding, distributed databases, OLTP, OLAP, and application-database architecture.

---

# 1. Understanding Databases

A database is an organized system for storing and managing data.

The fundamental purpose of a database is not simply to store information. A database provides a structured environment in which information can be created, retrieved, modified, validated, related, secured, and recovered.

A database is particularly useful when an application needs to manage large amounts of structured information and support multiple users or processes at the same time.

Examples of information commonly stored in databases include:

- Customers
- Employees
- Products
- Orders
- Payments
- Transactions
- Inventory
- Addresses
- Courses
- Students
- Financial records
- Application activity

The learning exercise demonstrated that database design begins with understanding the information an application needs to store and the relationships among different types of information.

---

# 2. Database Management Systems

A Database Management System, commonly called a DBMS, is the software responsible for managing databases.

The DBMS provides mechanisms for:

- Creating databases and database objects
- Storing information
- Retrieving information
- Modifying information
- Enforcing constraints
- Managing transactions
- Controlling concurrent access
- Providing security
- Recovering from failures
- Optimizing queries
- Managing indexes
- Supporting backup and recovery

Examples of database management systems include PostgreSQL, MySQL, MariaDB, Oracle Database, Microsoft SQL Server, and SQLite.

The learning exercise used SQLite to demonstrate database concepts because it is lightweight and can be accessed directly through Python without requiring a separate database server.

---

# 3. Relational Database Fundamentals

A relational database organizes information into relations, which are commonly represented as tables.

A table consists of rows and columns.

A row represents an individual record, while a column represents an attribute of that record.

For example, a customer table may contain information such as:

- Customer identifier
- Customer name
- Email address
- City
- Creation date

The relational model makes relationships between different tables explicit.

Instead of keeping all information inside one large structure, related concepts are separated into appropriate tables and connected using keys.

---

# 4. Tables, Rows, and Columns

The learning exercise established the distinction between tables, rows, and columns.

A table represents a collection of related records.

A row represents one individual record.

A column represents a specific attribute.

For example, in a customer database:

- The `customers` table represents customers.
- One row represents one customer.
- The `email` column represents the customer's email address.

This distinction is fundamental because relational database operations work primarily by selecting, combining, filtering, grouping, and modifying rows and columns.

---

# 5. Database Schema

A database schema describes the structure of a database.

It defines how data is organized and can include:

- Tables
- Columns
- Data types
- Primary keys
- Foreign keys
- Constraints
- Indexes
- Views
- Functions
- Procedures
- Other database objects

The schema represents the logical structure of the database rather than the individual values currently stored in it.

Understanding schemas is important because a well-designed schema provides a clear representation of the application's data model.

---

# 6. Data Models

Different database systems use different approaches to representing data.

Important database models include:

- Relational
- Hierarchical
- Network
- Document
- Key-value
- Graph
- Wide-column
- Object-oriented

The relational model was the primary focus of this learning exercise.

The exercise also introduced the conceptual differences between relational and non-relational databases and showed that different database models are designed around different workload requirements.

---

# 7. SQL

SQL, or Structured Query Language, is the primary language used to interact with relational databases.

SQL can be used for:

- Creating database structures
- Inserting data
- Retrieving data
- Updating data
- Deleting data
- Defining constraints
- Creating indexes
- Managing transactions
- Managing database permissions

One of the most important concepts learned is that SQL is primarily declarative.

The developer describes the desired result, while the database engine determines an appropriate execution strategy.

This separation between the logical request and the physical execution is one of the foundations of modern database systems.

---

# 8. SQL Command Categories

SQL commands can be understood through several broad categories.

## Data Definition Language

Data Definition Language is concerned with database structures.

It includes operations for creating, modifying, and removing objects such as tables.

## Data Manipulation Language

Data Manipulation Language deals with modifying stored records.

It includes inserting, updating, and deleting information.

## Data Query Language

Data Query Language is primarily concerned with retrieving information from the database.

The SELECT operation is the central component.

## Data Control Language

Data Control Language deals with database permissions and access control.

## Transaction Control Language

Transaction Control Language is associated with transaction management, including committing and rolling back changes.

Understanding these categories provides a clearer picture of the different responsibilities handled through SQL.

---

# 9. Database Tables and Data Types

Each database column has a defined data type.

Common categories include:

- Integer values
- Decimal values
- Character strings
- Boolean values
- Dates
- Times
- Timestamps
- Binary values
- JSON or semi-structured values

The choice of data type affects:

- Storage requirements
- Valid values
- Precision
- Comparisons
- Sorting
- Indexing
- Application behavior

Choosing appropriate data types is therefore part of database design rather than simply a syntactical decision.

---

# 10. Primary Keys

A primary key uniquely identifies records in a table.

The primary key provides identity to each row.

A good primary key should provide a reliable and stable way to distinguish one record from another.

The learning exercise demonstrated both simple primary keys and the concept of composite primary keys.

Primary keys are fundamental because relationships between tables frequently depend on them.

---

# 11. Composite Keys

A composite key consists of multiple columns that together identify a record.

Composite keys are particularly useful when the uniqueness of a record depends on a combination of attributes.

For example, a relationship between students and courses can use the combination of student identity and course identity to uniquely represent an enrollment.

Composite keys are commonly encountered in junction or association tables.

---

# 12. Candidate Keys and Alternate Keys

A candidate key is a minimal set of attributes capable of uniquely identifying a record.

A table may have more than one candidate key.

One candidate key can be selected as the primary key.

Other candidate keys can be maintained using uniqueness constraints.

This distinction helps separate the concept of uniqueness from the specific choice of primary identifier.

---

# 13. Surrogate Keys and Natural Keys

A surrogate key is an artificial identifier created specifically for database records.

Examples include generated numeric identifiers and UUIDs.

A natural key is based on a real-world attribute that naturally identifies an entity.

Examples can include:

- Email address
- ISBN
- Government-issued business identifiers
- Product codes

Surrogate keys can provide stable identifiers even when real-world attributes change.

Natural keys can carry business meaning but may be more difficult to maintain when the underlying business information changes.

---

# 14. Foreign Keys

A foreign key represents a relationship between tables.

A foreign key usually references a primary key or another candidate key in a related table.

For example, an order can contain a customer identifier that refers to an existing customer.

This creates a relationship between customers and orders.

Foreign keys are essential for maintaining referential integrity.

---

# 15. Referential Integrity

Referential integrity ensures that relationships between related records remain valid.

For example, an order should not reference a customer that does not exist.

Foreign key constraints help enforce this rule.

The learning exercise demonstrated why referential integrity is important and how it prevents inconsistent relationships between tables.

Without referential integrity, databases can accumulate orphaned records and invalid references.

---

# 16. Referential Actions

Foreign key relationships can define behavior when referenced records are updated or deleted.

Common behaviors include:

- Cascade
- Restrict
- No action
- Set null
- Set default

These options determine what happens to related records when their parent record changes.

Cascading operations can be useful, but they must be designed carefully because one operation can affect many related records.

---

# 17. Database Constraints

Constraints are rules enforced by the database.

Important constraints include:

- Primary key
- Foreign key
- Unique
- Not null
- Check
- Default

Constraints protect the integrity of stored information.

The exercise demonstrated that validation should not exist only in application code.

When an important business rule can be represented as a database constraint, enforcing it at the database level provides an additional layer of protection.

---

# 18. NOT NULL

A NOT NULL constraint requires a value to exist for a particular column.

This is useful when an attribute is mandatory.

Examples include:

- Required customer names
- Required product names
- Required identifiers
- Required transaction information

Using NOT NULL communicates an important assumption about the data model.

---

# 19. UNIQUE Constraints

A UNIQUE constraint prevents duplicate values for a defined uniqueness rule.

Email addresses are a common example.

A database can therefore prevent two records from having the same value when uniqueness is a business requirement.

The exact treatment of NULL values in unique constraints can vary between database systems.

---

# 20. CHECK Constraints

CHECK constraints allow conditions to be enforced at the database level.

Examples of useful business rules include:

- Prices cannot be negative.
- Quantities must be positive.
- Age cannot be below a defined threshold.
- Status must belong to an accepted set of values.

CHECK constraints help ensure that invalid information cannot enter the database through an uncontrolled data-access path.

---

# 21. DEFAULT Values

Default values automatically provide a value when one is not explicitly supplied.

Examples include:

- Default order status
- Creation timestamp
- Default boolean state
- Default quantity

Defaults reduce repetitive application logic and establish consistent initial values.

---

# 22. CRUD Operations

CRUD represents four fundamental operations:

- Create
- Read
- Update
- Delete

These operations correspond closely to the basic lifecycle of database records.

Create adds information.

Read retrieves information.

Update changes information.

Delete removes information.

Understanding CRUD provides the foundation for understanding application-database interaction.

---

# 23. Data Retrieval

Data retrieval is primarily performed through queries.

Queries can:

- Select particular columns
- Filter rows
- Sort results
- Group records
- Aggregate values
- Join tables
- Use subqueries
- Use common table expressions
- Apply window functions

The exercise demonstrated how simple retrieval operations develop into complex analytical queries.

---

# 24. Filtering Data

Filtering allows only records satisfying a condition to be returned.

Common filtering concepts include:

- Equality
- Inequality
- Greater than
- Less than
- Ranges
- Membership in a set
- Pattern matching
- Logical combinations

Filtering is fundamental because most real-world queries do not require every row in a table.

---

# 25. Logical Operators

Database conditions can be combined using logical operators.

The major operators are:

- AND
- OR
- NOT

Understanding operator precedence is important because complex conditions can produce unexpected results if their logical structure is misunderstood.

Parentheses can be used to make the intended logic explicit.

---

# 26. NULL and Three-Valued Logic

NULL is one of the most important and frequently misunderstood database concepts.

NULL does not simply mean zero.

It does not necessarily mean an empty string.

It represents the absence of a value.

SQL uses three-valued logic:

- TRUE
- FALSE
- UNKNOWN

This means comparisons involving NULL do not behave like ordinary comparisons.

NULL must generally be tested using dedicated NULL predicates.

Understanding NULL is essential for writing correct database queries.

---

# 27. DISTINCT

DISTINCT removes duplicate result combinations from a query.

It is useful when the objective is to obtain unique values rather than every individual occurrence.

The meaning of uniqueness depends on all columns included in the selected result.

---

# 28. Sorting and Ordering

Database query results do not inherently have a guaranteed meaningful order unless an explicit ordering requirement is specified.

ORDER BY is used when a particular ordering is required.

Sorting can be ascending or descending.

Ordering becomes particularly important for:

- Reports
- Ranking
- Pagination
- Time-based data
- Top-N queries
- Analytical operations

---

# 29. Pagination

Pagination limits the amount of data returned to an application at one time.

Offset-based pagination is simple but can become inefficient for very large datasets.

Keyset or cursor-based pagination can provide better performance for certain large-scale workloads because it avoids repeatedly processing large numbers of skipped rows.

Pagination is therefore both an application design and database performance concern.

---

# 30. Joins

Joins combine information from multiple tables.

Important join types include:

- Inner join
- Left join
- Right join
- Full outer join
- Cross join
- Self join

Joins are central to relational database systems because related information is often intentionally stored in separate tables.

---

# 31. INNER JOIN

An inner join returns records where the join condition matches between the participating tables.

It is useful when only related records are required.

For example, joining customers with orders can return customers who have matching orders.

---

# 32. LEFT JOIN

A left join preserves all records from the left table.

If a matching record does not exist in the right table, the right-side values are represented as NULL.

This makes left joins useful for questions such as:

- Which customers have no orders?
- Which products have never been sold?
- Which employees have no assigned department?

---

# 33. RIGHT JOIN and FULL OUTER JOIN

A right join preserves all records from the right table.

A full outer join preserves unmatched records from both sides as well as matching records.

Not every database system provides identical support for all join types.

Understanding the logical behavior of each join is more important than memorizing syntax.

---

# 34. CROSS JOIN

A cross join creates a Cartesian product between two sets of rows.

If one table contains three records and another contains four records, the result can contain twelve combinations.

Cross joins are useful in certain analytical and combinational problems but can produce extremely large results if used unintentionally.

---

# 35. SELF JOIN

A self join occurs when a table is joined with itself.

This is useful for hierarchical relationships.

Examples include:

- Employees and managers
- Parent and child categories
- Organizational structures
- Referral relationships

A self join allows different rows in the same table to be treated as related entities.

---

# 36. Join Cardinality

Join cardinality describes how many rows can be produced when records from tables are combined.

A one-to-many relationship can cause one row from one table to appear multiple times in the result.

Understanding cardinality is essential for avoiding accidental duplicate results.

Many incorrect aggregation queries are actually caused by misunderstanding join cardinality.

---

# 37. Aggregation

Aggregation summarizes multiple rows.

Common aggregate operations include:

- Count
- Sum
- Average
- Minimum
- Maximum

Aggregation is commonly used in:

- Reporting
- Financial calculations
- Business intelligence
- Statistical analysis
- Operational dashboards

---

# 38. GROUP BY

GROUP BY divides records into logical groups before aggregation.

For example, employee records can be grouped by department to calculate the number of employees or average salary for each department.

GROUP BY changes the shape of the result because multiple source records can become one result record per group.

---

# 39. HAVING

HAVING filters groups after aggregation.

The distinction between WHERE and HAVING is important.

WHERE filters individual rows before grouping.

HAVING filters groups after aggregation.

This difference becomes especially important when working with aggregate functions.

---

# 40. Subqueries

A subquery is a query contained inside another query.

Subqueries can be used to:

- Compare against calculated values
- Test for existence
- Filter using another query
- Retrieve related information
- Build intermediate logic

Subqueries provide a way to express complex relationships between query operations.

---

# 41. Correlated Subqueries

A correlated subquery depends on values from the outer query.

This allows each outer row to influence the inner query.

Correlated subqueries are powerful but can sometimes result in inefficient execution depending on the database engine and query structure.

Equivalent joins or window functions may sometimes provide a better execution strategy.

---

# 42. EXISTS and NOT EXISTS

EXISTS checks whether a related record exists.

NOT EXISTS checks whether no matching record exists.

These operations are particularly useful for questions involving the existence or absence of related data.

They form an important class of anti-join and semi-join patterns.

---

# 43. Common Table Expressions

Common Table Expressions, or CTEs, provide a way to define named intermediate query results.

They can improve the readability and organization of complex queries.

CTEs are useful for:

- Breaking complex queries into logical stages
- Reusing intermediate results
- Recursive queries
- Hierarchical data processing

They are primarily a query organization mechanism rather than automatically a performance optimization.

---

# 44. Recursive Queries

Recursive queries can process hierarchical structures.

Examples include:

- Organization charts
- Folder structures
- Category trees
- Dependency relationships
- Parent-child hierarchies

Recursive querying is especially useful when the depth of the hierarchy is not known in advance.

---

# 45. Set Operations

SQL supports operations that combine result sets.

Important set operations include:

- UNION
- UNION ALL
- INTERSECT
- EXCEPT

UNION removes duplicate result rows.

UNION ALL preserves duplicates and can therefore avoid the additional work required for duplicate elimination.

Understanding set operations provides another way to reason about query results mathematically.

---

# 46. Views

A view is a logical representation of a query.

Views can provide:

- Abstraction
- Reusable query definitions
- Simplified interfaces
- Controlled access to selected data

A view does not necessarily store its result physically.

It can instead represent a query that is evaluated when accessed.

---

# 47. Materialized Views

A materialized view stores the result of a query physically.

This can improve performance for expensive and frequently repeated analytical operations.

The trade-off is that materialized data must be refreshed when underlying information changes.

Materialized views therefore exchange freshness and maintenance cost for faster access.

---

# 48. Database Normalization

Normalization is a database design technique used to reduce unnecessary redundancy and dependency problems.

Important normal forms include:

- First Normal Form
- Second Normal Form
- Third Normal Form
- Boyce-Codd Normal Form
- Fourth Normal Form
- Fifth Normal Form

Normalization is not simply about creating more tables.

It is about organizing information according to dependency and relational principles.

---

# 49. First Normal Form

First Normal Form is concerned with atomic representation of values according to the chosen relational design.

A column should not normally contain an uncontrolled collection of independent values.

For example, storing several unrelated course names inside one field makes querying, validation, indexing, and relationship management more difficult.

A properly structured relational design represents individual values in a form that can be addressed independently.

---

# 50. Second Normal Form

Second Normal Form concerns partial dependencies on part of a composite key.

If a table uses a composite key and an attribute depends only on one component of that key, the design contains a partial dependency.

Separating the dependent information into an appropriate table can remove this problem.

---

# 51. Third Normal Form

Third Normal Form addresses transitive dependencies.

If one non-key attribute determines another non-key attribute, information may be unnecessarily duplicated.

Separating those dependencies helps ensure that each fact is stored in an appropriate location.

---

# 52. Boyce-Codd Normal Form

Boyce-Codd Normal Form is stricter than Third Normal Form.

It requires determinants to correspond to candidate keys.

BCNF becomes relevant in schemas where complex candidate-key relationships can still produce anomalies even after applying conventional 3NF reasoning.

---

# 53. Database Anomalies

Poor database design can lead to several anomalies.

## Insertion Anomaly

A record cannot be inserted without unrelated information.

## Update Anomaly

The same fact is duplicated across multiple records and must be updated consistently.

## Deletion Anomaly

Deleting one record unintentionally removes information about another concept.

Normalization helps reduce these anomalies.

---

# 54. Denormalization

Denormalization intentionally introduces redundancy.

It may be used to improve:

- Read performance
- Reporting performance
- Query simplicity
- Access speed
- Application response time

Denormalization is a deliberate engineering decision.

The duplicated information creates a consistency responsibility that must be managed.

---

# 55. Transactions

A transaction represents a logical unit of database work.

Transactions are important when several operations must succeed or fail together.

For example, a financial transfer can involve:

- Decreasing one account balance
- Increasing another account balance

If only one operation succeeds, the database can become inconsistent.

A transaction allows these operations to be treated as one logical unit.

---

# 56. ACID Properties

ACID represents four important transaction properties:

- Atomicity
- Consistency
- Isolation
- Durability

These properties provide a conceptual framework for understanding transactional behavior.

---

# 57. Atomicity

Atomicity means that a transaction is treated as a logical unit.

If a transaction fails before completion, its intended changes can be rolled back according to the database's transaction semantics.

This prevents partially completed transactional operations from becoming committed as though the complete operation succeeded.

---

# 58. Consistency

Consistency means that transactions preserve defined database rules and invariants.

Examples include:

- Valid foreign-key relationships
- Unique values
- Valid numeric ranges
- Required fields
- Business constraints

Consistency depends on the rules defined by the database and application.

---

# 59. Isolation

Isolation concerns how concurrent transactions interact.

Multiple users can access the same database simultaneously.

The database must control what one transaction can observe about another transaction's work.

Different isolation levels provide different guarantees.

---

# 60. Durability

Durability means that committed changes should survive failures according to the database system's durability guarantees.

Database engines use mechanisms such as:

- Transaction logs
- Write-ahead logging
- Persistent storage
- Checkpoints
- Recovery procedures

to support durability.

---

# 61. COMMIT and ROLLBACK

COMMIT finalizes a transaction.

ROLLBACK reverses uncommitted changes.

These operations are fundamental to transaction management.

They allow applications to either complete a logical unit of work or return the database to an earlier transactional state.

---

# 62. SAVEPOINT

A savepoint creates an intermediate point inside a transaction.

It allows part of a transaction to be rolled back without necessarily discarding all work performed since the transaction began.

Savepoints are useful for complex transactional workflows where partial recovery is required.

---

# 63. Concurrency

Database systems commonly serve many users at the same time.

Concurrency introduces the possibility that multiple transactions may read or modify the same information simultaneously.

The DBMS must coordinate these operations to maintain correct behavior.

Concurrency control can involve:

- Locks
- MVCC
- Isolation levels
- Transaction ordering
- Conflict detection
- Serialization mechanisms

---

# 64. Dirty Reads

A dirty read occurs when one transaction observes data written by another transaction before that transaction commits.

If the writing transaction later rolls back, the reader may have observed information that never became part of the committed database state.

This illustrates why transaction isolation matters.

---

# 65. Non-Repeatable Reads

A non-repeatable read occurs when a transaction reads the same record more than once and obtains different committed values because another transaction changed the record between reads.

This demonstrates that isolation is not simply about preventing corruption. It also determines what a transaction is allowed to observe.

---

# 66. Phantom Reads

A phantom read occurs when repeated execution of a range-based query produces a different set of rows because another transaction inserted or removed matching records.

Phantom behavior becomes important when transactions operate over sets of rows rather than a single record.

---

# 67. Lost Updates

A lost update can occur when two concurrent transactions read the same original value and then independently write changes, causing one update to overwrite another.

Concurrency control mechanisms are necessary to prevent or detect such situations.

---

# 68. Isolation Levels

Common SQL isolation levels include:

- Read Uncommitted
- Read Committed
- Repeatable Read
- Serializable

Different database systems implement these isolation levels differently.

The isolation level represents a trade-off between concurrency, consistency guarantees, and performance.

---

# 69. Locks

Database systems can use locks to coordinate concurrent operations.

Conceptual lock categories include:

- Shared locks
- Exclusive locks

Shared locks generally relate to concurrent reads.

Exclusive locks generally relate to modifications.

Modern database engines may also use multiversion concurrency control and other mechanisms rather than relying exclusively on traditional locking.

---

# 70. Deadlocks

A deadlock occurs when transactions wait for resources held by each other.

For example:

- Transaction A holds resource 1 and waits for resource 2.
- Transaction B holds resource 2 and waits for resource 1.

Neither transaction can continue.

Database systems generally detect deadlocks and terminate one transaction so that the system can recover.

Applications should be designed to handle appropriate transaction failures and retries.

---

# 71. Indexes

An index is a database data structure designed to make particular access patterns more efficient.

Indexes can significantly improve read performance when they match query conditions.

Common indexing concepts include:

- B-tree indexes
- Composite indexes
- Unique indexes
- Covering indexes
- Partial indexes
- Specialized indexes

The exact index types available depend on the database system.

---

# 72. Index Trade-Offs

Indexes are not free.

They require:

- Additional storage
- Additional maintenance
- Memory or cache resources
- Extra work during inserts
- Extra work during updates
- Extra work during deletes

Therefore, adding indexes indiscriminately can harm write performance.

Indexes should be created based on actual query patterns and workload requirements.

---

# 73. Composite Indexes

A composite index contains multiple columns.

The order of columns in a composite index matters.

An index containing:

- Customer identifier
- Order date

is not equivalent to an index containing:

- Order date
- Customer identifier

for every possible query.

Index design must therefore consider how queries filter, sort, and access data.

---

# 74. Selectivity

Selectivity describes how effectively a condition narrows down the number of candidate rows.

Highly selective values can identify a small portion of a table.

Low-selectivity values may match a large portion of the table.

Selectivity influences whether an index is likely to be useful for a particular query.

---

# 75. Cardinality

Cardinality can refer to the number of distinct values in a column or the nature of relationships between entities, depending on context.

Examples of relationship cardinality include:

- One-to-one
- One-to-many
- Many-to-many

Understanding cardinality is essential for database modeling and query optimization.

---

# 76. Covering Indexes

A covering index contains enough information to satisfy a query without requiring the database to access the underlying table for every matching record.

This can reduce additional data access and improve performance in suitable workloads.

Whether an index is covering depends on the query, selected columns, index structure, and database engine.

---

# 77. Query Execution Plans

A database optimizer creates an execution plan describing how a query should be executed.

Possible operations include:

- Sequential scans
- Index scans
- Index-only scans
- Nested-loop joins
- Hash joins
- Merge joins
- Sort operations
- Aggregation

Understanding execution plans is essential for database performance analysis.

---

# 78. Query Optimization

The database optimizer attempts to choose an efficient execution strategy.

It can consider:

- Available indexes
- Table statistics
- Estimated row counts
- Selectivity
- Join strategies
- Sorting requirements
- Filtering conditions
- Cost estimates

The optimizer does not simply execute SQL in the order in which the developer wrote it.

The logical query describes the requested result, while the optimizer determines a physical strategy.

---

# 79. Logical Query Processing

SQL is written in a particular syntactical order, but its logical processing can be understood through operations such as:

- FROM
- JOIN
- WHERE
- GROUP BY
- HAVING
- SELECT
- DISTINCT
- ORDER BY
- LIMIT

Understanding logical processing helps explain many SQL behaviors.

It also explains why certain aliases or expressions cannot always be referenced in every clause.

---

# 80. Window Functions

Window functions perform calculations across related rows without collapsing those rows into a single grouped record.

They are useful for:

- Ranking
- Running totals
- Comparisons with previous rows
- Comparisons with next rows
- Partition-level statistics
- Top-N analysis

Window functions are particularly powerful for analytical SQL.

---

# 81. Ranking

Ranking functions allow records to be ordered within a defined group.

Important concepts include:

- ROW_NUMBER
- RANK
- DENSE_RANK

These functions differ in how they treat tied values.

Understanding those differences is important when building rankings and analytical reports.

---

# 82. Running Calculations

Window functions can calculate values across an ordered sequence.

Examples include:

- Running totals
- Cumulative averages
- Previous transaction values
- Next transaction values
- Change from previous period

This avoids the need to collapse the underlying rows into groups.

---

# 83. Temporary Tables

Temporary tables store intermediate information for a limited scope.

They can be useful for:

- Complex transformations
- Intermediate calculations
- Data preparation
- Multi-stage database operations

Temporary table behavior differs between database systems.

---

# 84. Stored Procedures and Functions

Some database systems allow executable logic to be stored inside the database.

Stored procedures and functions can encapsulate reusable database operations.

Potential use cases include:

- Complex transactional operations
- Administrative processes
- Reusable database calculations
- Specialized database-side logic

The exact capabilities and syntax vary considerably between database products.

---

# 85. Triggers

A trigger is database-side logic that automatically executes when a defined event occurs.

Common events include:

- Insert
- Update
- Delete

Triggers can be useful for:

- Auditing
- Maintaining derived information
- Enforcing specialized rules

They can also make system behavior less obvious because an operation on one table may automatically cause changes elsewhere.

---

# 86. Database Security

Database security involves protecting information and controlling access.

Important security concepts include:

- Authentication
- Authorization
- Least privilege
- Encryption
- Auditing
- Secure connections
- Credential management
- Data protection
- Backup protection

Security should be considered part of database architecture rather than an afterthought.

---

# 87. Authentication and Authorization

Authentication determines who is accessing the system.

Authorization determines what that authenticated identity is allowed to do.

A user can be successfully authenticated while still lacking permission to read or modify a particular table.

This distinction is fundamental to access control.

---

# 88. Least Privilege

Least privilege means providing users and applications only the permissions they actually require.

An application that only needs to read data should not automatically receive administrative privileges.

Reducing permissions limits the potential impact of compromised credentials or application vulnerabilities.

---

# 89. SQL Injection

SQL injection occurs when untrusted input is improperly incorporated into SQL statements.

The fundamental problem is the mixing of SQL structure and user-provided data.

Parameterized queries separate the SQL statement from its values.

This is one of the most important security practices when applications communicate with databases.

---

# 90. Application Validation and Database Validation

Application-level validation is useful for providing user-friendly feedback.

Database-level validation protects the underlying data itself.

For important rules, both layers can be useful.

The application can provide immediate validation.

The database can enforce the invariant regardless of which application or process modifies the data.

---

# 91. Database Backups

Backups provide protection against data loss.

Failures that can require recovery include:

- Hardware failures
- Software failures
- Accidental deletion
- Human mistakes
- Data corruption
- Security incidents
- Operational errors

Common backup concepts include:

- Full backups
- Incremental backups
- Differential backups
- Logical backups
- Physical backups

---

# 92. Recovery

Backup alone is not enough.

A database system also needs a recovery strategy.

Recovery may involve:

- Restoring backups
- Replaying transaction logs
- Reconstructing database state
- Recovering to a specific point in time

Recovery procedures should be tested rather than assumed to work.

---

# 93. Point-in-Time Recovery

Point-in-time recovery allows a database to be restored to a particular point in time using backups and transaction logs.

This is particularly useful when an accidental operation damages data.

For example, if a destructive operation occurs at a particular time, recovery mechanisms can potentially reconstruct the database state from before that event.

---

# 94. Write-Ahead Logging

Write-Ahead Logging, commonly called WAL, records changes in a log before the corresponding data changes are considered durably written.

WAL can support:

- Crash recovery
- Durability
- Replication
- Recovery procedures

The exact implementation differs between database systems.

---

# 95. Replication

Replication means maintaining copies of database information across multiple nodes.

A common architecture contains:

- Primary node
- Replica nodes

Replication can support:

- Read scaling
- High availability
- Disaster recovery
- Geographic distribution

Replication does not automatically solve every scalability or availability problem.

---

# 96. Synchronous Replication

In synchronous replication, a primary may wait for confirmation that changes have been replicated before considering an operation fully committed according to the configured durability model.

This can improve consistency or durability guarantees but can increase latency.

---

# 97. Asynchronous Replication

In asynchronous replication, the primary can continue without waiting for replicas to confirm every change.

This can reduce latency but creates the possibility of replication lag.

If the primary fails before changes reach a replica, recovery may involve losing or reconstructing those changes depending on the architecture.

---

# 98. Replication Lag

Replication lag is the delay between a change occurring on a source node and that change becoming available on a replica.

This creates an important application-level consideration.

An application that writes to a primary and immediately reads from a lagging replica may not see its own recently committed change.

---

# 99. Partitioning

Partitioning divides a large logical dataset into smaller physical sections.

Common partitioning strategies include:

- Range partitioning
- List partitioning
- Hash partitioning

Partitioning can improve manageability and performance for certain large datasets.

---

# 100. Partition Pruning

Partition pruning allows the database to avoid accessing partitions that cannot contain relevant data.

For example, a date-based partitioned table can allow a query for a specific time range to access only relevant partitions.

Partition pruning can significantly reduce unnecessary data processing.

---

# 101. Sharding

Sharding distributes data across multiple database nodes.

Each node is responsible for a portion of the overall dataset.

A sharded architecture may divide users or records based on a shard key.

Sharding can provide horizontal scalability but introduces additional complexity around:

- Routing
- Rebalancing
- Cross-shard queries
- Transactions
- Consistency
- Failure handling

---

# 102. Shard Keys

A shard key determines how records are distributed across shards.

A good shard key should ideally provide:

- Balanced distribution
- Predictable routing
- Appropriate query locality
- Low risk of hotspots

A poor shard key can concentrate traffic on a small number of nodes.

---

# 103. Hotspots

A hotspot occurs when one database node, partition, or shard receives disproportionately high traffic.

Hotspots reduce the benefits of distribution because one part of the system becomes overloaded while others remain underutilized.

Shard-key design is therefore a critical distributed database concern.

---

# 104. Distributed Databases

A distributed database stores or processes data across multiple machines.

Distributed systems introduce problems that are less significant in a single-node database.

These include:

- Network failures
- Partial failures
- Replication
- Coordination
- Latency
- Consistency
- Data placement
- Failover

Distributed database design requires thinking about the network as part of the database environment.

---

# 105. CAP Theorem

The CAP theorem describes important trade-offs in distributed systems under network partition.

The three properties are:

- Consistency
- Availability
- Partition tolerance

When a network partition occurs, a system cannot simultaneously guarantee the strongest forms of both consistency and availability under the formal CAP model.

CAP should not be reduced to the simplistic idea of choosing any two properties in every situation.

The theorem is specifically concerned with behavior during network partitions.

---

# 106. Strong Consistency

Strong consistency provides a well-defined view of committed data across distributed components.

It simplifies application reasoning but can require coordination that increases latency or reduces availability under certain failure conditions.

---

# 107. Eventual Consistency

Eventual consistency allows different replicas to temporarily contain different states.

If updates stop and the system continues operating normally, replicas can eventually converge.

This model can support highly distributed and available systems but requires applications to tolerate temporary inconsistencies.

---

# 108. OLTP

OLTP stands for Online Transaction Processing.

OLTP systems are designed for operational workloads.

Typical characteristics include:

- Frequent writes
- Small transactions
- Many concurrent users
- Low-latency operations
- Structured data
- Strong transactional requirements

Examples include:

- Banking systems
- Order processing
- Payment systems
- Inventory systems
- Customer account systems

---

# 109. OLAP

OLAP stands for Online Analytical Processing.

OLAP systems focus on analytical workloads.

Typical characteristics include:

- Large data scans
- Aggregations
- Historical analysis
- Complex queries
- Reporting
- Business intelligence

OLAP workloads often have very different optimization requirements from OLTP workloads.

---

# 110. OLTP vs OLAP

The fundamental difference is workload purpose.

OLTP is primarily concerned with operating the business.

OLAP is primarily concerned with analyzing the business.

OLTP commonly emphasizes:

- Fast transactions
- Concurrent updates
- Normalized data
- Operational correctness

OLAP commonly emphasizes:

- Large analytical queries
- Aggregations
- Historical information
- Analytical performance

A system can contain both types of workloads, but separating them is often useful at scale.

---

# 111. Data Warehouses

A data warehouse is designed primarily for analytical workloads.

It can combine information from multiple operational sources.

Sources can include:

- Application databases
- Enterprise systems
- CRM systems
- ERP systems
- Files
- APIs
- External data sources

The warehouse organizes information to support reporting and analysis.

---

# 112. Fact Tables

Fact tables commonly represent measurable business events.

Examples include:

- Sales
- Transactions
- Orders
- Shipments
- Payments

A fact record may contain numerical measurements and references to dimensions.

---

# 113. Dimension Tables

Dimension tables describe entities involved in analytical events.

Examples include:

- Customer
- Product
- Store
- Employee
- Date
- Region

Dimensions provide descriptive context for facts.

---

# 114. Star Schema

A star schema places a fact table at the center and connects it to dimension tables.

This design is common in analytical databases because it makes business-oriented analytical queries relatively straightforward.

The structure typically resembles:

```text
                Customer
                   |
                   |
Product ---- Fact Table ---- Date
                   |
                   |
                 Store
```

---

# 115. ETL

ETL stands for:

- Extract
- Transform
- Load

Data is extracted from source systems, transformed into the required form, and loaded into a destination system.

ETL is commonly associated with traditional data integration and warehouse pipelines.

---

# 116. ELT

ELT stands for:

- Extract
- Load
- Transform

Data is first loaded into the destination analytical platform and transformed there.

Modern analytical platforms frequently support ELT architectures because they provide substantial computational capacity for transformation.

---

# 117. Relational and NoSQL Databases

Relational databases organize information primarily through structured tables and relationships.

NoSQL is a broad category covering several different data models.

These include:

- Document databases
- Key-value databases
- Wide-column databases
- Graph databases

The choice between relational and non-relational systems depends on:

- Data structure
- Query patterns
- Consistency requirements
- Scale
- Availability requirements
- Development model
- Operational requirements

NoSQL does not mean "no structure."

Different NoSQL systems simply apply different structural models.

---

# 118. Document Databases

Document databases store records as documents, commonly using JSON-like structures.

They are useful when application data is naturally hierarchical or when records have flexible structures.

The trade-off is that relationships and constraints may need to be handled differently from traditional relational databases.

---

# 119. Key-Value Databases

Key-value databases associate a key with a value.

They are particularly effective when the application knows the key required to retrieve information.

They are commonly associated with:

- Caching
- Session storage
- Fast lookups
- Distributed state

---

# 120. Graph Databases

Graph databases represent information using concepts such as:

- Nodes
- Relationships
- Properties

They are useful when relationships are central to the workload.

Examples include:

- Social networks
- Recommendation systems
- Fraud analysis
- Knowledge graphs
- Network analysis

---

# 121. Semi-Structured Data

Semi-structured data contains organizational information without necessarily following a rigid relational schema.

JSON is a common example.

Modern relational databases often support JSON because applications frequently need both structured relational data and flexible metadata.

---

# 122. Database Design

Database design begins with understanding the business domain.

The process generally involves:

1. Identifying entities
2. Identifying attributes
3. Identifying relationships
4. Identifying business rules
5. Selecting keys
6. Defining constraints
7. Normalizing the design
8. Considering query patterns
9. Designing indexes
10. Considering performance and scalability

Database design is therefore closely connected to application requirements.

---

# 123. Entities

An entity represents a meaningful concept in the domain.

Examples include:

- Customer
- Product
- Employee
- Department
- Order
- Payment

An entity normally becomes a table in a relational implementation.

---

# 124. Attributes

Attributes describe entities.

For a customer, attributes may include:

- Customer identifier
- Name
- Email
- Phone number
- City
- Creation date

Attributes should represent meaningful facts about the entity.

---

# 125. Relationships

Relationships describe how entities interact.

Common relationship types include:

- One-to-one
- One-to-many
- Many-to-many

Relationships are represented using foreign keys, junction tables, or other relational structures.

---

# 126. Many-to-Many Relationships

Many-to-many relationships require an intermediate structure.

For example:

- One student can take many courses.
- One course can have many students.

A separate enrollment structure represents the relationship.

This avoids storing uncontrolled collections inside individual fields.

---

# 127. Business Rules

Business rules describe conditions that must remain true.

Examples include:

- A customer can have multiple orders.
- An order must belong to a customer.
- An order item must reference a valid product.
- A quantity must be positive.
- A product price cannot be negative.
- An email address must be unique.

Business rules influence schema design and constraints.

---

# 128. Derived Data

Derived data is calculated from other information.

For example, an order total can be calculated from quantities and prices.

Storing derived values can improve performance but creates an additional consistency responsibility.

If the underlying information changes, derived information must remain synchronized.

---

# 129. Historical Data

Historical information often needs to remain accurate even when current values change.

For example, the current price of a product may change, but an old order should still preserve the price that applied when the order occurred.

This is why transactional records often store historical snapshots of important values.

---

# 130. Temporal Data

Temporal data represents information that changes over time.

Examples include:

- Employee salary history
- Product price history
- Customer addresses
- Account status
- Subscription states

A temporal design can preserve when a value became valid and when it stopped being valid.

---

# 131. Soft Deletes

A soft delete marks a record as deleted instead of physically removing it.

Common representations include deletion flags or deletion timestamps.

Soft deletion can help with:

- Recovery
- Auditing
- Historical records

It also creates additional query complexity because normal application queries may need to exclude logically deleted records.

---

# 132. Database Integrity

Database integrity refers to maintaining correct and consistent information.

Important integrity categories include:

- Entity integrity
- Referential integrity
- Domain integrity
- Business-rule integrity

Primary keys support entity identity.

Foreign keys support relationships.

Data types and CHECK constraints support domain rules.

Business rules may require combinations of constraints, transactions, application logic, or database-side logic.

---

# 133. Database Performance

Database performance depends on many factors.

Important factors include:

- Query structure
- Indexes
- Data volume
- Join cardinality
- Query plans
- Statistics
- CPU
- Memory
- Storage
- Network latency
- Lock contention
- Connection management
- Caching

Performance problems should therefore be investigated systematically rather than solved by automatically adding indexes.

---

# 134. Query Performance

A query can become slow because of:

- Large table scans
- Missing indexes
- Poor index selection
- Inefficient joins
- Excessive sorting
- Large result sets
- Incorrect cardinality estimates
- Lock contention
- Network overhead
- Inefficient application access patterns

The appropriate solution depends on the actual cause.

---

# 135. N+1 Query Problem

The N+1 problem occurs when an application first retrieves a collection and then performs an additional database query for each individual item.

For example:

- One query retrieves customers.
- A separate query retrieves orders for each customer.

For N customers, this can produce N+1 queries.

The result can be excessive network communication and database overhead.

Possible solutions include appropriate joins, batching, eager loading, or carefully designed data-access patterns.

---

# 136. Connection Pooling

Applications typically communicate with databases through connections.

Creating a new connection for every request can be expensive.

Connection pooling maintains reusable database connections.

A pool can improve efficiency by:

- Reusing established connections
- Limiting simultaneous connections
- Reducing connection setup overhead

The pool must be configured appropriately because too many connections can overload the database.

---

# 137. Database Drivers

A database driver provides the interface through which an application communicates with a database.

Python provides the sqlite3 module for SQLite.

Other database systems generally require their own drivers or compatible database libraries.

The driver translates application-level requests into communication understood by the database system.

---

# 138. ORM

ORM stands for Object-Relational Mapping.

An ORM maps application objects and structures to relational database concepts.

ORMs can simplify development by reducing repetitive database-access code.

They can also introduce abstraction that hides important database behavior.

Understanding SQL, indexes, transactions, joins, and execution plans remains important even when using an ORM.

---

# 139. Database Migrations

A migration represents a controlled change to database structure.

Examples include:

- Creating a table
- Adding a column
- Removing a column
- Creating an index
- Adding a constraint
- Renaming a structure

Migrations allow schema changes to be versioned and reproduced across environments.

---

# 140. Schema Evolution

Database schemas change as applications evolve.

Schema evolution becomes particularly challenging when multiple versions of an application are running simultaneously.

Techniques such as backward-compatible changes and expand-and-contract migrations can help applications transition between schema versions safely.

---

# 141. Idempotency

Idempotency means that repeating an operation does not produce unintended repeated effects.

Idempotency is particularly important for:

- APIs
- Payment processing
- Distributed systems
- Retry mechanisms
- Message processing

For example, setting a record to a specific final state can be idempotent, while creating a new record repeatedly may not be.

---

# 142. UPSERT

An upsert represents an operation where existing information is updated while missing information is inserted.

The exact syntax differs between database systems.

Upsert behavior is useful for synchronization, data ingestion, configuration management, and other workflows where a record may or may not already exist.

---

# 143. Auditing

Auditing records changes made to data.

An audit system can capture information such as:

- Who made a change
- What operation occurred
- Which record was affected
- When the change occurred
- Previous state
- New state

Auditing can be implemented at the application level, database level, or through specialized data-change mechanisms.

---

# 144. Data Lineage

Data lineage describes where information originates, how it changes, and where it is consumed.

Lineage becomes important in:

- Data warehouses
- Analytics
- Regulatory environments
- Data governance
- Machine learning pipelines

Understanding lineage helps determine whether a value can be trusted and how it was produced.

---

# 145. Database Observability

Database observability involves understanding database behavior through measurable signals.

Important metrics include:

- Query latency
- Transactions per second
- Connection count
- Cache hit rate
- Lock waits
- Deadlocks
- Replication lag
- CPU utilization
- Memory utilization
- Disk usage
- Storage growth

Logs and execution statistics can help identify abnormal behavior and performance problems.

---

# 146. Database Availability

Availability describes whether the database can continue serving requests when needed.

Availability can be improved through:

- Replication
- Redundancy
- Failover
- Load balancing
- Disaster recovery
- Monitoring

Availability is different from durability.

A database can preserve committed data while temporarily being unavailable.

---

# 147. Database Durability

Durability concerns the survival of committed information after failures.

A durable system uses mechanisms such as:

- Persistent storage
- Transaction logging
- WAL
- Replication
- Recovery procedures

Durability and availability address different aspects of reliability.

---

# 148. Vertical Scaling

Vertical scaling increases the resources available to a database server.

Resources can include:

- CPU
- Memory
- Storage performance
- Storage capacity

Vertical scaling is often simpler than distributed scaling, but it eventually encounters hardware limits and cost constraints.

---

# 149. Horizontal Scaling

Horizontal scaling adds additional machines or database nodes.

It can provide greater scalability but introduces distributed-system complexity.

Challenges can include:

- Data distribution
- Coordination
- Consistency
- Routing
- Replication
- Failure handling

---

# 150. Read Scaling

Read-heavy workloads can sometimes be distributed across replicas.

A common architecture has:

- One primary for writes
- Multiple replicas for reads

This can increase read capacity.

The application must account for replication lag when using replicas.

---

# 151. Write Scaling

Write scaling is more difficult because writes often require coordination.

Possible approaches include:

- Partitioning
- Sharding
- Batching
- Workload separation
- Distributed processing

The appropriate approach depends on the application's workload and consistency requirements.

---

# 152. Caching

Caching stores frequently accessed information in a faster storage layer.

A common pattern is:

1. Application checks cache.
2. If data exists, return it.
3. If data does not exist, retrieve it from the database.
4. Store the result in the cache.
5. Return the result.

Caching reduces database load but introduces the problem of stale data.

---

# 153. Cache Invalidation

When database information changes, cached information may become outdated.

Common caching strategies include:

- Cache-aside
- Write-through
- Write-back
- Time-based expiration
- Explicit invalidation

Cache consistency must be considered carefully when cached information affects important business decisions.

---

# 154. Database and External Systems

A database transaction normally cannot automatically make an external API call atomic with the database transaction.

For example, updating an order and calling an external payment service are separate systems.

Distributed application architectures therefore use patterns such as:

- Idempotency
- Retry mechanisms
- Compensation
- Outbox pattern
- Saga pattern

These approaches help coordinate work across system boundaries.

---

# 155. Outbox Pattern

The outbox pattern stores an event in the same database transaction as the business change.

The event is then processed by another component and published to external systems.

This helps prevent situations where a database change succeeds but the corresponding event fails to reach another service.

---

# 156. Database Lifecycle

Data has a lifecycle:

- Creation
- Storage
- Access
- Modification
- Archival
- Deletion

Database architecture should consider this complete lifecycle.

Storage decisions made during initial development can affect operational costs, historical analysis, security, and deletion requirements later.

---

# 157. Data Retention

Data retention determines how long information should be preserved.

Retention requirements can be influenced by:

- Business requirements
- Legal requirements
- Compliance
- Historical analysis
- Storage costs
- Privacy considerations

Retention policies should be explicit because keeping everything forever can create unnecessary operational and governance problems.

---

# 158. Database Portability

SQL has standardized concepts, but database systems implement different dialects and features.

Differences can occur in:

- Data types
- Generated identifiers
- Date functions
- JSON functionality
- Upsert operations
- Pagination
- Index types
- Stored procedures
- Transaction behavior

Therefore, SQL knowledge should include both standard relational concepts and awareness of database-specific behavior.

---

# 159. SQLite

SQLite is an embedded relational database.

It is useful for:

- Learning
- Prototyping
- Local applications
- Testing
- Small workloads

SQLite differs architecturally from server-based database systems such as PostgreSQL and MySQL.

One important SQLite concept is that foreign-key enforcement needs to be explicitly enabled in environments where it is not already enabled.

This demonstrates that database features can depend not only on schema definitions but also on configuration and runtime behavior.

---

# 160. Database Testing

Database testing can verify:

- Schema correctness
- Constraints
- Relationships
- Query behavior
- Transaction behavior
- Migrations
- Data integrity
- Concurrency behavior
- Performance

Testing should verify both successful operations and invalid operations.

A database is reliable only when its failure behavior is understood as well as its successful behavior.

---

# 161. Constraint Testing

Constraint tests verify that invalid states cannot be created.

Examples include:

- Duplicate unique values
- Missing required values
- Invalid foreign-key references
- Negative prices
- Invalid quantities

These tests verify that the database actually enforces the intended data model.

---

# 162. Transaction Testing

Transaction tests verify that operations either produce the intended committed state or are rolled back correctly when failures occur.

This is especially important for multi-step operations.

A test should verify not only that an error is generated, but also that the database has not been left in an unintended partial state.

---

# 163. Migration Testing

Migration testing ensures that database schema changes can be applied safely.

Important concerns include:

- Existing data
- Existing indexes
- Existing constraints
- Application compatibility
- Rollback requirements
- Migration ordering

Database migrations should be treated as production changes rather than simple scripts.

---

# 164. Database Anti-Patterns

Several database practices commonly create problems.

Examples include:

- Excessive use of SELECT *
- Missing indexes for important access patterns
- Too many unnecessary indexes
- N+1 queries
- Large unbounded result sets
- Poor pagination
- Storing unrelated data in one table
- Excessive denormalization
- Ignoring constraints
- Long-running transactions
- Excessive database connections
- Treating database errors as unexpected events
- Relying entirely on application validation

Recognizing anti-patterns is part of developing good database judgment.

---

# 165. Long-Running Transactions

Transactions that remain open for too long can cause:

- Lock contention
- Increased resource usage
- Greater deadlock risk
- Reduced concurrency
- Larger recovery requirements

Transaction boundaries should therefore correspond to meaningful business operations without unnecessarily keeping database resources occupied.

---

# 166. Database Connection Limits

Every database connection consumes resources.

An application that opens too many connections can overload the database even when individual queries are efficient.

Connection pooling and appropriate concurrency limits are therefore important parts of application architecture.

---

# 167. Batch Processing

Batching combines multiple database operations into fewer database interactions.

It can reduce:

- Network round trips
- Statement overhead
- Transaction overhead

Batching is particularly useful for large data imports and bulk updates.

---

# 168. Bulk Loading

Bulk loading mechanisms are designed to efficiently insert large amounts of data.

They are commonly used for:

- Data migration
- Initial database population
- Data warehouse ingestion
- Large-scale imports

Bulk operations are generally preferable to processing millions of records through inefficient individual requests.

---

# 169. Database as a System of Record

A system of record is the authoritative source for a particular category of information.

For example, an order database may be the authoritative source for order state.

Other systems may cache or replicate the information, but the system of record establishes the authoritative state.

This concept is important in distributed application architectures.

---

# 170. Database Architecture

A modern application may follow an architecture such as:

Application

↓

API

↓

Business Logic

↓

Data Access Layer

↓

Database Driver

↓

Database

The database is therefore one component of a larger software system.

The application determines business behavior.

The database provides persistent storage, data integrity, transactions, query processing, and other database services.

---

# 171. Repository and Data Access Layers

A data-access layer can isolate database interaction from the rest of the application.

This can provide:

- Separation of concerns
- Easier testing
- Reusable data-access operations
- Reduced duplication

The exact architecture depends on the application.

The important concept is that database interaction should have clearly defined responsibilities within the software system.

---

# 172. Transaction Boundaries in Applications

Application operations should define appropriate transaction boundaries.

For example, creating an order may require multiple related operations.

These operations may need to succeed together.

At the same time, transactions should not remain open while unrelated external operations are being performed.

Transaction boundaries therefore affect both correctness and performance.

---

# 173. Historical Consistency

Operational databases often need to preserve the state of information at the time an event occurred.

This is particularly important for:

- Orders
- Payments
- Financial records
- Contracts
- Pricing
- Inventory

Current values should not automatically overwrite information that is historically important.

---

# 174. Data Redundancy

Redundancy means that the same information exists in multiple places.

Uncontrolled redundancy can create update anomalies.

Controlled redundancy can improve:

- Read performance
- Availability
- Historical accuracy
- Analytical efficiency

The important distinction is whether redundancy is intentional and managed.

---

# 175. Database Design Trade-Offs

Database design involves trade-offs rather than universal rules.

Examples include:

### Normalization vs Performance

Normalization reduces redundancy but can require additional joins.

### Indexes vs Write Performance

Indexes improve selected reads but increase write overhead.

### Consistency vs Availability

Distributed systems may need to balance strong consistency against availability during failures.

### Simplicity vs Scalability

A single database can be simpler to operate, while distributed architectures can support larger workloads at the cost of additional complexity.

### Flexibility vs Integrity

Flexible schemas can support rapidly changing data, while strict schemas provide stronger structural guarantees.

---

# 176. Relational Algebra

Relational algebra provides a theoretical foundation for relational databases.

Important operations include:

- Selection
- Projection
- Join
- Union
- Difference
- Cartesian product

Selection corresponds conceptually to choosing rows based on conditions.

Projection corresponds conceptually to choosing columns.

Joins combine relations according to defined relationships.

Understanding relational algebra helps explain how SQL queries can be transformed into different execution strategies.

---

# 177. Query Results and Stored Data

A query result does not necessarily represent stored information.

A database can dynamically calculate:

- Totals
- Averages
- Rankings
- Derived values
- Joined information
- Aggregated statistics

Some calculated results may later be materialized for performance.

This distinction between stored data and derived query results is fundamental to database design.

---

# 178. Reliability

Database reliability depends on more than successful queries.

Important reliability mechanisms include:

- Constraints
- Transactions
- Recovery
- Backups
- Replication
- Monitoring
- Testing
- Failover
- Operational procedures

Reliability is therefore an architectural property rather than a single database feature.

---

# 179. Failure Handling

Database systems must account for different types of failures.

These include:

- Application failures
- Transaction failures
- Process failures
- Machine failures
- Storage failures
- Network failures
- Human errors
- Data corruption

The database's recovery mechanisms determine how the system returns to a valid state.

---

# 180. Database Security and Reliability Together

Security and reliability are closely related.

A database must protect information from unauthorized access while also protecting it from accidental or operational loss.

Important areas include:

- Access control
- Encryption
- Backups
- Auditing
- Recovery
- Monitoring
- Least privilege
- Secure application connections

---

# 181. Core Database Mental Model

The database concepts learned through the exercise can be understood as a connected system:

- Business requirements determine the information that must exist.
- Entities become logical data structures.
- Tables represent structured collections of records.
- Columns describe attributes.
- Keys establish identity.
- Foreign keys establish relationships.
- Constraints protect integrity.
- SQL provides the interface for manipulating and retrieving data.
- Transactions group related operations.
- Isolation controls concurrent behavior.
- Indexes improve access patterns.
- Query plans explain execution.
- Backups and logs support recovery.
- Replication improves availability and scalability.
- Partitioning divides large datasets.
- Sharding distributes data across nodes.
- Analytical systems organize information differently from operational systems.

This relationship between concepts is more important than memorizing individual SQL commands.

---

# 182. Core Database Terminology

## Database

An organized collection of data.

## DBMS

Software that manages databases.

## Table

A structured collection of records.

## Row

An individual record in a table.

## Column

An attribute of a record.

## Schema

The logical structure of a database.

## Primary Key

A key used to uniquely identify records.

## Foreign Key

A key that references a related record in another table.

## Candidate Key

A minimal set of attributes capable of uniquely identifying a record.

## Composite Key

A key consisting of multiple columns.

## Constraint

A rule enforced by the database.

## Index

A data structure designed to accelerate particular access patterns.

## Query

A request to retrieve or manipulate database information.

## Transaction

A logical unit of database work.

## Commit

The operation that finalizes a transaction.

## Rollback

The operation that reverses uncommitted transactional changes.

## View

A logical representation of a query.

## Materialized View

A physically stored query result.

## Trigger

Database-side logic automatically executed by a defined event.

## Normalization

A database design approach for reducing redundancy and dependency anomalies.

## Denormalization

Intentional introduction of redundancy for specific design objectives.

## Replication

Maintaining copies of database information across nodes.

## Partitioning

Dividing a logical dataset into physical partitions.

## Sharding

Distributing portions of a dataset across multiple database nodes.

## OLTP

Operational transaction processing.

## OLAP

Analytical processing.

## ETL

Extract, Transform, Load.

## ELT

Extract, Load, Transform.

## Cardinality

A measure describing distinct values or relationship multiplicity depending on context.

## Selectivity

The degree to which a condition narrows the candidate dataset.

## Concurrency

Simultaneous database activity by multiple transactions or users.

## Deadlock

A situation in which transactions wait indefinitely for resources held by each other.

## Replication Lag

The delay between a change on one database node and its availability on a replica.

## Idempotency

The property that repeated execution does not produce unintended repeated effects.

---

# 183. Practical Database Concepts Demonstrated

The practical learning exercise connected theoretical database concepts with actual database behavior.

The concepts demonstrated include:

- Creating a relational database
- Creating tables
- Defining columns
- Selecting data types
- Creating primary keys
- Creating foreign keys
- Enforcing constraints
- Establishing relationships
- Inserting records
- Retrieving records
- Filtering records
- Sorting records
- Updating records
- Deleting records
- Handling NULL values
- Joining tables
- Aggregating information
- Grouping records
- Using subqueries
- Using existence checks
- Using CTEs
- Working with views
- Understanding normalization
- Working with transactions
- Committing changes
- Rolling back changes
- Understanding savepoints
- Understanding concurrency
- Understanding isolation
- Understanding locking
- Understanding deadlocks
- Understanding indexes
- Understanding query execution
- Understanding database security
- Understanding backups
- Understanding replication
- Understanding partitioning
- Understanding sharding
- Understanding analytical databases
- Understanding application-database interaction

---

# 184. Database Fundamentals as an Engineering Discipline

Database fundamentals extend beyond learning SQL syntax.

A database engineer or software developer must understand how data behaves throughout its lifecycle.

This includes understanding:

- How data is modeled
- How records are identified
- How relationships are represented
- How integrity is enforced
- How concurrent operations interact
- How failures are recovered
- How queries are optimized
- How indexes affect workloads
- How applications communicate with databases
- How schemas evolve
- How data is secured
- How databases scale
- How historical information is preserved
- How operational and analytical workloads differ

Database knowledge therefore connects software development, system architecture, data engineering, security, and application design.

---

# 185. Database Fundamentals: Conceptual Flow

A complete database system can be understood through the following conceptual flow:

Business Requirements

↓

Entities and Relationships

↓

Database Schema

↓

Tables, Columns, Keys, and Constraints

↓

Data

↓

SQL Queries

↓

Query Processing

↓

Query Optimization

↓

Execution Plan

↓

Storage and Indexes

↓

Transactions and Concurrency

↓

Logging and Recovery

↓

Replication and Availability

↓

Partitioning and Scaling

↓

Operational and Analytical Systems

This flow demonstrates how basic database concepts connect to advanced database architecture.

---

# 186. Final Working Perspective

Database fundamentals provide the foundation for understanding how modern applications store and manage persistent information.

The most important concepts are interconnected.

A table is not simply a collection of rows.

A key is not simply an identifier.

A foreign key is not simply another column.

A transaction is not simply a group of SQL statements.

An index is not simply a performance switch.

A database is a system that combines data modeling, integrity, querying, transactions, concurrency, storage, security, recovery, and performance management.

Understanding these relationships makes it possible to reason about database behavior rather than treating the database as a black box.

The practical exercises provide a foundation for understanding how relational databases behave when data is created, related, queried, modified, constrained, transacted, indexed, and managed as part of a real software system.
