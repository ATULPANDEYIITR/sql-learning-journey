-- ============================================================
-- INDEX FUNDAMENTALS
-- Why indexes exist, B-tree concepts, and index lookup.
--
-- PostgreSQL 15+
--
-- Demonstrates:
-- 1. Heap table storage and sequential scans
-- 2. B-tree indexes
-- 3. Unique indexes
-- 4. Composite indexes
-- 5. Covering indexes
-- 6. Partial indexes
-- 7. Index lookup and range lookup
-- 8. Index maintenance
-- 9. EXPLAIN and EXPLAIN ANALYZE
-- 10. Index statistics and performance reporting
-- ============================================================

DROP SCHEMA IF EXISTS index_lab CASCADE;

CREATE SCHEMA index_lab;

SET search_path TO index_lab, public;

-- ============================================================
-- 1. TABLE DESIGN
-- ============================================================

CREATE TABLE departments (
    department_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employees (
    employee_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    employee_code VARCHAR(30) NOT NULL UNIQUE,

    employee_name VARCHAR(150) NOT NULL,

    department_id BIGINT NOT NULL
        REFERENCES departments(department_id),

    salary NUMERIC(12, 2) NOT NULL
        CHECK (salary >= 0),

    employment_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (
            employment_status IN (
                'ACTIVE',
                'INACTIVE',
                'ON_LEAVE',
                'TERMINATED'
            )
        ),

    email VARCHAR(200) NOT NULL UNIQUE,

    hired_at DATE NOT NULL DEFAULT CURRENT_DATE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- The primary key and UNIQUE constraints automatically
-- create indexes. They should not be duplicated unnecessarily.

-- ============================================================
-- 2. SAMPLE DATA
-- ============================================================

INSERT INTO departments (department_name)
VALUES
    ('Engineering'),
    ('Security'),
    ('Research'),
    ('Operations'),
    ('Finance');

INSERT INTO employees (
    employee_code,
    employee_name,
    department_id,
    salary,
    employment_status,
    email,
    hired_at
)
SELECT
    'EMP-' || LPAD(g::TEXT, 6, '0'),
    'Employee ' || g,
    ((g - 1) % 5) + 1,
    40000 + ((g * 137) % 110001),
    CASE
        WHEN g % 20 = 0 THEN 'ON_LEAVE'
        WHEN g % 25 = 0 THEN 'INACTIVE'
        ELSE 'ACTIVE'
    END,
    'employee' || g || '@example.org',
    DATE '2020-01-01' + (g % 2000)
FROM generate_series(1, 20000) AS g;

ANALYZE employees;
ANALYZE departments;

-- ============================================================
-- 3. SEQUENTIAL SCAN
-- ============================================================

-- A sequential scan reads table pages and checks records.
-- It is useful when a large percentage of the table is required.

EXPLAIN
SELECT *
FROM employees
WHERE employee_id = 7500;

-- ============================================================
-- 4. BASIC B-TREE INDEX
-- ============================================================

-- B-tree is the default PostgreSQL index method.
-- The primary key already has a unique B-tree index.
-- This example adds an index on a frequently searched column.

CREATE INDEX idx_employees_salary
ON employees USING BTREE (salary);

ANALYZE employees;

-- Range retrieval can use the ordered index.

EXPLAIN
SELECT employee_id, employee_name, salary
FROM employees
WHERE salary BETWEEN 70000 AND 90000
ORDER BY salary;

-- ============================================================
-- 5. COMPOSITE INDEX
-- ============================================================

-- The order of columns matters.
--
-- This index is useful for:
-- department_id
-- department_id + employment_status
--
-- It is not generally equivalent to a separate index
-- on employment_status alone.

CREATE INDEX idx_employees_department_status
ON employees USING BTREE (
    department_id,
    employment_status
);

ANALYZE employees;

EXPLAIN
SELECT employee_id, employee_name
FROM employees
WHERE department_id = 2
  AND employment_status = 'ACTIVE';

-- Leading-column lookup.

EXPLAIN
SELECT employee_id
FROM employees
WHERE department_id = 2;

-- A query filtering only by employment_status may not
-- efficiently use this composite index.

EXPLAIN
SELECT employee_id
FROM employees
WHERE employment_status = 'ACTIVE';

-- ============================================================
-- 6. COVERING INDEX
-- ============================================================

-- INCLUDE stores additional non-key columns in index entries.
-- These columns can help PostgreSQL perform index-only scans
-- when visibility-map conditions also permit them.

CREATE INDEX idx_employees_covering
ON employees USING BTREE (department_id)
INCLUDE (
    employee_name,
    salary
);

ANALYZE employees;

VACUUM (ANALYZE) employees;

EXPLAIN
SELECT employee_name, salary
FROM employees
WHERE department_id = 3;

-- An index-only scan is possible, not guaranteed.

-- ============================================================
-- 7. PARTIAL INDEX
-- ============================================================

-- A partial index contains only records satisfying its predicate.
-- Useful when a common workload targets a relatively small subset.

CREATE INDEX idx_employees_active
ON employees USING BTREE (
    department_id,
    employee_id
)
WHERE employment_status = 'ACTIVE';

ANALYZE employees;

EXPLAIN
SELECT employee_id, employee_name
FROM employees
WHERE department_id = 1
  AND employment_status = 'ACTIVE';

-- ============================================================
-- 8. INDEX LOOKUP AND RANGE LOOKUP
-- ============================================================

-- Equality lookup.

SELECT
    employee_id,
    employee_name,
    salary
FROM employees
WHERE employee_id = 7500;

-- Range lookup.

SELECT
    employee_id,
    employee_name,
    salary
FROM employees
WHERE salary >= 80000
  AND salary <= 100000
ORDER BY salary;

-- Composite lookup.

SELECT
    employee_id,
    employee_name,
    employment_status
FROM employees
WHERE department_id = 4
  AND employment_status = 'ACTIVE'
ORDER BY employee_id;

-- ============================================================
-- 9. INDEX MAINTENANCE
-- ============================================================

-- Updating an indexed column may require index maintenance.
-- Updating a non-indexed column may also prevent a HOT update
-- when other PostgreSQL conditions are not satisfied.

UPDATE employees
SET salary = salary + 5000,
    updated_at = CURRENT_TIMESTAMP
WHERE employee_id = 7500;

-- Verify the updated value.

SELECT employee_id, salary
FROM employees
WHERE employee_id = 7500;

-- Insert a new record.

INSERT INTO employees (
    employee_code,
    employee_name,
    department_id,
    salary,
    employment_status,
    email
)
VALUES (
    'EMP-NEW-001',
    'New Research Employee',
    3,
    85000,
    'ACTIVE',
    'new.research@example.org'
);

-- Deletion also requires maintenance of associated indexes.

DELETE FROM employees
WHERE employee_code = 'EMP-NEW-001';

-- ============================================================
-- 10. VALIDATION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_employee(
    p_employee_id BIGINT
)
RETURNS TABLE (
    record_exists BOOLEAN,
    department_exists BOOLEAN,
    salary_valid BOOLEAN,
    employee_status TEXT
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        e.employee_id IS NOT NULL,
        d.department_id IS NOT NULL,
        COALESCE(e.salary >= 0, FALSE),
        COALESCE(e.employment_status, 'NOT_FOUND')
    FROM (SELECT p_employee_id AS id) input
    LEFT JOIN employees e
        ON e.employee_id = input.id
    LEFT JOIN departments d
        ON d.department_id = e.department_id;
$$;

SELECT *
FROM validate_employee(7500);

SELECT *
FROM validate_employee(999999);

-- ============================================================
-- 11. INDEXED WORKFLOW FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION find_employees_by_department(
    p_department_id BIGINT,
    p_status VARCHAR DEFAULT 'ACTIVE'
)
RETURNS TABLE (
    employee_id BIGINT,
    employee_name VARCHAR,
    salary NUMERIC
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        e.employee_id,
        e.employee_name,
        e.salary
    FROM employees e
    WHERE e.department_id = p_department_id
      AND e.employment_status = p_status
    ORDER BY e.employee_id;
$$;

SELECT *
FROM find_employees_by_department(2, 'ACTIVE')
LIMIT 20;

-- ============================================================
-- 12. INDEX USAGE REPORT
-- ============================================================

CREATE OR REPLACE VIEW index_usage_report AS
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS index_scans,
    idx_tup_read AS index_entries_read,
    idx_tup_fetch AS table_rows_fetched,
    pg_size_pretty(
        pg_relation_size(indexrelid)
    ) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'index_lab';

SELECT *
FROM index_usage_report
ORDER BY index_scans DESC;

-- ============================================================
-- 13. TABLE AND INDEX SIZE REPORT
-- ============================================================

SELECT
    c.relname AS table_name,
    pg_size_pretty(pg_relation_size(c.oid)) AS table_size,
    pg_size_pretty(pg_indexes_size(c.oid)) AS indexes_size,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c
JOIN pg_namespace n
    ON n.oid = c.relnamespace
WHERE n.nspname = 'index_lab'
  AND c.relkind = 'r';

-- ============================================================
-- 14. INDEX DEFINITION REPORT
-- ============================================================

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'index_lab'
ORDER BY indexname;

-- ============================================================
-- 15. QUERY PLAN ANALYSIS
-- ============================================================

-- EXPLAIN shows the selected execution plan.
-- EXPLAIN ANALYZE executes the query and measures actual work.
--
-- Disabling sequential scans is useful for controlled
-- demonstrations, not a normal production tuning strategy.

BEGIN;

SET LOCAL enable_seqscan = OFF;

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT employee_id, employee_name
FROM employees
WHERE employee_id = 7500;

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT employee_id, employee_name, salary
FROM employees
WHERE department_id = 2
  AND employment_status = 'ACTIVE';

ROLLBACK;

-- ============================================================
-- 16. AGGREGATION AND REPORTING
-- ============================================================

SELECT
    d.department_name,
    COUNT(e.employee_id) AS employee_count,
    ROUND(AVG(e.salary), 2) AS average_salary,
    MIN(e.salary) AS minimum_salary,
    MAX(e.salary) AS maximum_salary
FROM departments d
LEFT JOIN employees e
    ON e.department_id = d.department_id
GROUP BY
    d.department_id,
    d.department_name
ORDER BY employee_count DESC;

-- ============================================================
-- 17. CTE-BASED INDEXED RETRIEVAL
-- ============================================================

WITH department_metrics AS (
    SELECT
        department_id,
        COUNT(*) AS employee_count,
        AVG(salary) AS average_salary
    FROM employees
    WHERE employment_status = 'ACTIVE'
    GROUP BY department_id
),
ranked_departments AS (
    SELECT
        department_id,
        employee_count,
        average_salary,
        DENSE_RANK() OVER (
            ORDER BY average_salary DESC
        ) AS salary_rank
    FROM department_metrics
)
SELECT
    d.department_name,
    r.employee_count,
    ROUND(r.average_salary, 2) AS average_salary,
    r.salary_rank
FROM ranked_departments r
JOIN departments d
    ON d.department_id = r.department_id
ORDER BY r.salary_rank;

-- ============================================================
-- 18. TRANSACTION AND FAILURE HANDLING
-- ============================================================

BEGIN;

-- A valid insertion.

INSERT INTO employees (
    employee_code,
    employee_name,
    department_id,
    salary,
    employment_status,
    email
)
VALUES (
    'EMP-TXN-001',
    'Transaction Test',
    1,
    90000,
    'ACTIVE',
    'transaction.test@example.org'
);

SAVEPOINT before_invalid_operation;

-- This violates the salary CHECK constraint.
-- Run this statement separately when demonstrating
-- the failure, because a failed PostgreSQL transaction
-- must be rolled back to a savepoint or transaction boundary.

ROLLBACK TO SAVEPOINT before_invalid_operation;

COMMIT;

-- ============================================================
-- 19. INVALID DATA TESTS
-- ============================================================

-- Uncomment individually to observe constraint failures.
--
-- INSERT INTO employees (
--     employee_code, employee_name, department_id,
--     salary, employment_status, email
-- )
-- VALUES (
--     'EMP-INVALID-001', 'Invalid Salary', 1,
--     -1000, 'ACTIVE', 'invalid@example.org'
-- );
--
-- Duplicate email and employee code are also rejected
-- by UNIQUE constraints.

-- ============================================================
-- 20. INDEX MAINTENANCE UTILITIES
-- ============================================================

-- ANALYZE updates planner statistics.
ANALYZE employees;

-- VACUUM makes dead tuple space reusable.
VACUUM (ANALYZE) employees;

-- REINDEX rebuilds an index.
-- Use appropriate locking and operational planning in production.
-- REINDEX INDEX index_lab.idx_employees_salary;

-- ============================================================
-- 21. FINAL VALIDATION
-- ============================================================

SELECT
    COUNT(*) AS total_employees,
    COUNT(DISTINCT employee_id) AS unique_employee_ids,
    COUNT(DISTINCT email) AS unique_emails,
    MIN(salary) AS minimum_salary,
    MAX(salary) AS maximum_salary
FROM employees;

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'index_lab'
ORDER BY indexname;

-- End of Index Fundamentals demonstration.
