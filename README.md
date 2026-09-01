# SQL LEARNING JOURNEY
## 120-Day SQL Mastery Roadmap
### Beginner → Intermediate → Advanced → Expert → Extreme Advanced

| S.No. | Day | Topic | Subtopics Covered | Tools Covered |
|---:|---:|---|---|---|
| 1 | Day 01 | Introduction to SQL | What is SQL, why SQL exists, databases, relational databases, SQL vs programming languages, SQL use cases, database-driven applications | SQL, PostgreSQL |
| 2 | Day 02 | Database Fundamentals | Data, records, tables, schemas, databases, DBMS, RDBMS, rows, columns, relationships | PostgreSQL, pgAdmin |
| 3 | Day 03 | Relational Database Concepts | Relations, tuples, attributes, domains, relational model, relational algebra basics | PostgreSQL |
| 4 | Day 04 | SQL Environment Setup | PostgreSQL installation, database creation, connecting to database, command-line usage, pgAdmin | PostgreSQL, psql, pgAdmin |
| 5 | Day 05 | SQL Syntax Fundamentals | SQL statements, keywords, identifiers, literals, comments, semicolons, case sensitivity | PostgreSQL |
| 6 | Day 06 | Creating Databases | CREATE DATABASE, database naming, connection management, database lifecycle | PostgreSQL, psql |
| 7 | Day 07 | Creating Tables | CREATE TABLE, column definitions, data types, table structure | PostgreSQL |
| 8 | Day 08 | SQL Data Types | INTEGER, NUMERIC, DECIMAL, VARCHAR, TEXT, BOOLEAN, DATE, TIME, TIMESTAMP | PostgreSQL |
| 9 | Day 09 | INSERT Statements | INSERT, multiple-row insertion, column ordering, default values | PostgreSQL |
| 10 | Day 10 | SELECT Fundamentals | SELECT, selecting columns, expressions, aliases, SELECT * | PostgreSQL |
| 11 | Day 11 | Filtering Data | WHERE, comparison operators, logical conditions | PostgreSQL |
| 12 | Day 12 | NULL Handling | NULL semantics, IS NULL, IS NOT NULL, NULL comparisons, COALESCE | PostgreSQL |
| 13 | Day 13 | Sorting Results | ORDER BY, ASC, DESC, multiple-column sorting, NULL ordering | PostgreSQL |
| 14 | Day 14 | Limiting Results | LIMIT, OFFSET, FETCH, pagination fundamentals | PostgreSQL |
| 15 | Day 15 | DISTINCT | DISTINCT, duplicate elimination, DISTINCT ON in PostgreSQL | PostgreSQL |
| 16 | Day 16 | SQL Operators | Arithmetic, comparison, logical, BETWEEN, IN, NOT, LIKE | PostgreSQL |
| 17 | Day 17 | Pattern Matching | LIKE, ILIKE, wildcards, regex basics, pattern-based filtering | PostgreSQL |
| 18 | Day 18 | Conditional Logic | CASE, WHEN, THEN, ELSE, conditional expressions | PostgreSQL |
| 19 | Day 19 | String Functions | CONCAT, LENGTH, LOWER, UPPER, TRIM, SUBSTRING, REPLACE, POSITION | PostgreSQL |
| 20 | Day 20 | Numeric Functions | ROUND, CEIL, FLOOR, ABS, MOD, POWER, RANDOM | PostgreSQL |
| 21 | Day 21 | Date and Time | DATE, TIME, TIMESTAMP, intervals, date arithmetic | PostgreSQL |
| 22 | Day 22 | Date Functions | EXTRACT, DATE_PART, DATE_TRUNC, AGE, CURRENT_DATE | PostgreSQL |
| 23 | Day 23 | Aggregate Functions | COUNT, SUM, AVG, MIN, MAX | PostgreSQL |
| 24 | Day 24 | GROUP BY | Grouping rows, grouped calculations, grouping multiple columns | PostgreSQL |
| 25 | Day 25 | HAVING | Filtering aggregated results, WHERE vs HAVING | PostgreSQL |
| 26 | Day 26 | Basic Data Modification | UPDATE, DELETE, conditional updates, safe deletion | PostgreSQL |
| 27 | Day 27 | Constraints Introduction | Constraints, data integrity, constraint enforcement | PostgreSQL |
| 28 | Day 28 | PRIMARY KEY | Primary keys, uniqueness, entity identification, composite primary keys | PostgreSQL |
| 29 | Day 29 | FOREIGN KEY | Referential integrity, parent-child relationships, cascading actions | PostgreSQL |
| 30 | Day 30 | UNIQUE and CHECK | UNIQUE constraints, CHECK constraints, business rules | PostgreSQL |
| 31 | Day 31 | DEFAULT Constraints | Default values, generated defaults, timestamps, UUID defaults | PostgreSQL |
| 32 | Day 32 | Relationships | One-to-one, one-to-many, many-to-many relationships | PostgreSQL, ER diagrams |
| 33 | Day 33 | INNER JOIN | Join fundamentals, matching rows, join conditions | PostgreSQL |
| 34 | Day 34 | LEFT JOIN | Left outer joins, unmatched rows, NULL results | PostgreSQL |
| 35 | Day 35 | RIGHT and FULL JOIN | RIGHT JOIN, FULL OUTER JOIN, use cases | PostgreSQL |
| 36 | Day 36 | CROSS JOIN | Cartesian products, generating combinations, risks | PostgreSQL |
| 37 | Day 37 | SELF JOIN | Hierarchical relationships, employee-manager relationships | PostgreSQL |
| 38 | Day 38 | Multi-Table JOINs | Joining three or more tables, join order, complex relationships | PostgreSQL |
| 39 | Day 39 | JOIN vs Subquery | Query design choices, readability, performance considerations | PostgreSQL |
| 40 | Day 40 | JOIN Pitfalls | Duplicate rows, accidental Cartesian products, NULL behavior, incorrect joins | PostgreSQL |
| 41 | Day 41 | Subqueries Fundamentals | Scalar, single-row, multi-row and table subqueries | PostgreSQL |
| 42 | Day 42 | Correlated Subqueries | Correlated execution, outer references, use cases | PostgreSQL |
| 43 | Day 43 | EXISTS and NOT EXISTS | Semi-joins, anti-joins, existence checks | PostgreSQL |
| 44 | Day 44 | IN and NOT IN | Membership tests, NULL pitfalls, alternatives | PostgreSQL |
| 45 | Day 45 | Derived Tables | Subqueries in FROM, intermediate result sets | PostgreSQL |
| 46 | Day 46 | Common Table Expressions | WITH clause, CTE fundamentals, readable query architecture | PostgreSQL |
| 47 | Day 47 | Multiple CTEs | Chained CTEs, modular query design, reusable transformations | PostgreSQL |
| 48 | Day 48 | Recursive CTEs | WITH RECURSIVE, recursion, hierarchical data, organizational trees | PostgreSQL |
| 49 | Day 49 | Set Operations | UNION, UNION ALL, INTERSECT, EXCEPT | PostgreSQL |
| 50 | Day 50 | Advanced Aggregation | Multiple aggregations, conditional aggregation, aggregation strategies | PostgreSQL |
| 51 | Day 51 | Conditional Aggregation | SUM(CASE), COUNT(CASE), filtered metrics, KPI calculations | PostgreSQL |
| 52 | Day 52 | Window Functions Introduction | OVER(), partitions, ordering, window concepts | PostgreSQL |
| 53 | Day 53 | ROW_NUMBER | Ranking rows, deduplication, top-N problems | PostgreSQL |
| 54 | Day 54 | RANK and DENSE_RANK | Ranking differences, ties, leaderboard problems | PostgreSQL |
| 55 | Day 55 | NTILE | Bucketing records, quartiles, deciles, segmentation | PostgreSQL |
| 56 | Day 56 | LAG and LEAD | Previous/next row analysis, time-series comparisons | PostgreSQL |
| 57 | Day 57 | FIRST_VALUE and LAST_VALUE | First/last observations, window frames | PostgreSQL |
| 58 | Day 58 | Window Frames | ROWS, RANGE, GROUPS, frame boundaries | PostgreSQL |
| 59 | Day 59 | Running Calculations | Running totals, cumulative averages, cumulative metrics | PostgreSQL |
| 60 | Day 60 | Advanced Window Analytics | Moving averages, rolling metrics, ranking combinations | PostgreSQL |
| 61 | Day 61 | Mid-Level SQL Project | Sales database, customers, products, orders, revenue analysis | PostgreSQL, SQL |
| 62 | Day 62 | Database Normalization | Functional dependencies, normalization goals, anomalies | PostgreSQL |
| 63 | Day 63 | 1NF, 2NF and 3NF | Atomicity, partial dependency, transitive dependency | PostgreSQL |
| 64 | Day 64 | BCNF and Advanced Normalization | Boyce-Codd Normal Form, higher normal forms, trade-offs | PostgreSQL |
| 65 | Day 65 | Denormalization | Performance-driven denormalization, redundancy, trade-offs | PostgreSQL |
| 66 | Day 66 | ER Modeling | Entities, attributes, relationships, cardinality, participation | ER diagrams, PostgreSQL |
| 67 | Day 67 | Database Schema Design | OLTP schema design, naming conventions, keys, constraints | PostgreSQL |
| 68 | Day 68 | Surrogate vs Natural Keys | UUIDs, sequences, identity columns, natural identifiers | PostgreSQL |
| 69 | Day 69 | PostgreSQL Sequences | SERIAL, IDENTITY, sequences, sequence behavior | PostgreSQL |
| 70 | Day 70 | Views | CREATE VIEW, view abstraction, reusable queries | PostgreSQL |
| 71 | Day 71 | Materialized Views | Materialized views, refresh strategies, performance use cases | PostgreSQL |
| 72 | Day 72 | Temporary Tables | TEMP tables, session scope, staging workflows | PostgreSQL |
| 73 | Day 73 | Transactions | BEGIN, COMMIT, ROLLBACK, atomic operations | PostgreSQL |
| 74 | Day 74 | ACID Properties | Atomicity, consistency, isolation, durability | PostgreSQL |
| 75 | Day 75 | Transaction Isolation | Read Uncommitted concepts, Read Committed, Repeatable Read, Serializable | PostgreSQL |
| 76 | Day 76 | Concurrency | Locks, concurrent transactions, race conditions | PostgreSQL |
| 77 | Day 77 | Deadlocks | Deadlock causes, detection, prevention, transaction design | PostgreSQL |
| 78 | Day 78 | SAVEPOINT | Partial rollback, nested transaction patterns | PostgreSQL |
| 79 | Day 79 | Index Fundamentals | Why indexes exist, B-tree concepts, index lookup | PostgreSQL |
| 80 | Day 80 | PostgreSQL Index Types | B-tree, Hash, GiST, SP-GiST, GIN, BRIN | PostgreSQL |
| 81 | Day 81 | Composite Indexes | Multi-column indexes, column ordering, selectivity | PostgreSQL |
| 82 | Day 82 | Partial and Expression Indexes | Conditional indexes, function-based indexing | PostgreSQL |
| 83 | Day 83 | Unique Indexes | Enforcing uniqueness, index-backed constraints | PostgreSQL |
| 84 | Day 84 | Index Trade-offs | Write overhead, storage, maintenance, over-indexing | PostgreSQL |
| 85 | Day 85 | Query Execution | SQL parsing, planning, optimization and execution | PostgreSQL |
| 86 | Day 86 | EXPLAIN | Execution plans, cost estimates, scan types | PostgreSQL |
| 87 | Day 87 | EXPLAIN ANALYZE | Actual execution time, rows, loops, plan verification | PostgreSQL |
| 88 | Day 88 | Sequential vs Index Scans | Seq Scan, Index Scan, Bitmap Scan | PostgreSQL |
| 89 | Day 89 | Query Optimization | Predicate pushdown, join optimization, reducing unnecessary work | PostgreSQL |
| 90 | Day 90 | Advanced Query Tuning | Slow queries, execution plans, statistics, bottleneck identification | PostgreSQL, EXPLAIN ANALYZE |
| 91 | Day 91 | PostgreSQL Statistics | ANALYZE, planner statistics, cardinality estimation | PostgreSQL |
| 92 | Day 92 | VACUUM and Maintenance | MVCC, dead tuples, VACUUM, VACUUM ANALYZE | PostgreSQL |
| 93 | Day 93 | PostgreSQL MVCC | Multi-Version Concurrency Control, snapshots, tuple visibility | PostgreSQL |
| 94 | Day 94 | PostgreSQL System Catalogs | pg_catalog, metadata, table information, index information | PostgreSQL |
| 95 | Day 95 | Information Schema | INFORMATION_SCHEMA, portable metadata queries | PostgreSQL |
| 96 | Day 96 | Stored Functions | CREATE FUNCTION, parameters, return types, function execution | PostgreSQL, PL/pgSQL |
| 97 | Day 97 | PL/pgSQL | Variables, control flow, IF, LOOP, exceptions | PostgreSQL |
| 98 | Day 98 | Stored Procedures | CREATE PROCEDURE, CALL, procedural database logic | PostgreSQL |
| 99 | Day 99 | Triggers | BEFORE, AFTER, INSTEAD OF triggers, trigger functions | PostgreSQL, PL/pgSQL |
| 100 | Day 100 | Advanced SQL Programming | Dynamic SQL, EXECUTE, exception handling, reusable database logic | PostgreSQL, PL/pgSQL |
| 101 | Day 101 | JSON in PostgreSQL | JSON, JSONB, operators, extraction, nested structures | PostgreSQL |
| 102 | Day 102 | JSONB Indexing | GIN indexes, JSONB containment, semi-structured data | PostgreSQL |
| 103 | Day 103 | Arrays | Array data types, indexing, searching, unnesting | PostgreSQL |
| 104 | Day 104 | Full-Text Search | tsvector, tsquery, text search, ranking | PostgreSQL |
| 105 | Day 105 | Regular Expressions | Regex matching, extraction, validation and transformation | PostgreSQL |
| 106 | Day 106 | Advanced Data Transformation | STRING_AGG, ARRAY_AGG, JSON aggregation, complex transformations | PostgreSQL |
| 107 | Day 107 | Analytical SQL | Cohort analysis, retention, conversion rates, segmentation | PostgreSQL |
| 108 | Day 108 | Time-Series SQL | Date buckets, trends, rolling windows, period-over-period analysis | PostgreSQL |
| 109 | Day 109 | Advanced Business Analytics | Revenue, profit, customer lifetime value, churn, growth metrics | PostgreSQL |
| 110 | Day 110 | SQL for Data Science | Feature extraction, preprocessing, analytical datasets, statistical summaries | PostgreSQL, Python |
| 111 | Day 111 | SQL + Python | Connecting Python to databases, executing SQL, retrieving results | Python, PostgreSQL, psycopg |
| 112 | Day 112 | SQL + Pandas | Reading SQL data, writing SQL queries, dataframe integration | Python, Pandas, SQLAlchemy |
| 113 | Day 113 | SQL APIs | Database-backed APIs, parameterized queries, connection handling | FastAPI, PostgreSQL |
| 114 | Day 114 | SQL Security | Users, roles, privileges, GRANT, REVOKE, least privilege | PostgreSQL |
| 115 | Day 115 | SQL Injection | Injection mechanics, parameterized queries, prepared statements, prevention | PostgreSQL, Python |
| 116 | Day 116 | Database Backup and Recovery | pg_dump, pg_restore, logical backups, recovery concepts | PostgreSQL |
| 117 | Day 117 | Data Warehousing | OLTP vs OLAP, fact tables, dimension tables, star schema, snowflake schema | PostgreSQL, SQL |
| 118 | Day 118 | Advanced Data Engineering SQL | ETL, ELT, staging tables, incremental loading, Slowly Changing Dimensions | PostgreSQL, SQL |
| 119 | Day 119 | Extreme SQL Mastery | Complex CTEs, recursive queries, advanced windows, optimization, execution plans, production patterns | PostgreSQL, SQL |
| 120 | Day 120 | Capstone SQL Project | Complete production-style database, schema design, complex queries, analytics, optimization, security and documentation | PostgreSQL, pgAdmin, Python, Pandas, SQLAlchemy |
