/*
===============================================================================
SEQUENTIAL SCAN, INDEX SCAN AND BITMAP SCAN
PostgreSQL 15+ executable learning and benchmarking script
===============================================================================

Demonstrates:

1. Sequential scans
2. B-tree index scans
3. Bitmap index scans
4. Bitmap AND and Bitmap OR
5. Selectivity and cardinality
6. Query planner cost estimation
7. Statistics and ANALYZE
8. Index-only scans
9. Partial and composite indexes
10. EXPLAIN and EXPLAIN ANALYZE
11. Index maintenance
12. Transaction handling

All objects are created inside the scan_lab schema.
*/

DROP SCHEMA IF EXISTS scan_lab CASCADE;

CREATE SCHEMA scan_lab;

SET search_path TO scan_lab, public;

-- ============================================================================
-- 1. RELATIONAL DATA MODEL
-- ============================================================================

CREATE TABLE departments (
    department_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE locations (
    location_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_name VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE employees (
    employee_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    employee_name VARCHAR(100) NOT NULL,

    department_id INTEGER NOT NULL
        REFERENCES departments(department_id),

    location_id INTEGER NOT NULL
        REFERENCES locations(location_id),

    salary NUMERIC(12, 2) NOT NULL
        CHECK (salary >= 0),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    hired_at DATE NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- A table designed to demonstrate different access paths.

INSERT INTO departments (department_name)
VALUES
    ('Engineering'),
    ('Finance'),
    ('Operations'),
    ('Security');

INSERT INTO locations (location_name)
VALUES
    ('Lucknow'),
    ('Delhi'),
    ('Mumbai'),
    ('Bengaluru');

-- ============================================================================
-- 2. GENERATE A REALISTIC DATASET
-- ============================================================================

INSERT INTO employees (
    employee_name,
    department_id,
    location_id,
    salary,
    is_active,
    hired_at
)
SELECT
    'Employee-' || n,

    1 + ((n * 7) % 4),

    1 + ((n * 11) % 4),

    30000 + ((n * 7919) % 150001),

    n % 7 <> 0,

    DATE '2015-01-01' + (n % 4000)

FROM generate_series(1, 100000) AS series(n);

-- Add a small number of deliberately selective records.

INSERT INTO employees (
    employee_name,
    department_id,
    location_id,
    salary,
    is_active,
    hired_at
)
VALUES
    ('Executive-001', 1, 1, 250000, TRUE, DATE '2020-01-01'),
    ('Executive-002', 2, 2, 275000, TRUE, DATE '2021-01-01'),
    ('Executive-003', 4, 1, 300000, FALSE, DATE '2019-01-01');

-- ============================================================================
-- 3. BASELINE STATISTICS
-- ============================================================================

-- ANALYZE collects column statistics used by the planner.
-- Without useful statistics, selectivity estimates may be inaccurate.

ANALYZE departments;
ANALYZE locations;
ANALYZE employees;

-- Inspect table size and approximate row count.

SELECT
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'scan_lab';

-- Inspect estimated column distributions.

SELECT
    attname AS column_name,
    null_frac,
    n_distinct,
    most_common_vals,
    most_common_freqs,
    correlation
FROM pg_stats
WHERE schemaname = 'scan_lab'
  AND tablename = 'employees'
ORDER BY attname;

-- ============================================================================
-- 4. SEQUENTIAL SCAN
-- ============================================================================

/*
A sequential scan reads table pages and evaluates the WHERE condition
against visible tuples.

It can be efficient when:
- A large percentage of rows is required.
- No suitable index exists.
- Random heap access would be expensive.
- The table is relatively small.
*/

EXPLAIN
SELECT *
FROM employees
WHERE salary = 50000;

EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS)
SELECT *
FROM employees
WHERE salary = 50000;

-- salary does not yet have an index.
-- A sequential scan is normally the natural access path.

-- Full table retrieval is another sequential scan candidate.

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM employees;

-- ============================================================================
-- 5. CREATE SECONDARY INDEXES
-- ============================================================================

CREATE INDEX idx_employees_department
ON employees (department_id);

CREATE INDEX idx_employees_location
ON employees (location_id);

CREATE INDEX idx_employees_salary
ON employees (salary);

CREATE INDEX idx_employees_active
ON employees (is_active);

-- Refresh statistics after creating indexes.

ANALYZE employees;

-- ============================================================================
-- 6. INDEX SCAN
-- ============================================================================

/*
An index scan uses an index to locate matching tuple identifiers.
It then accesses the corresponding heap tuples.

A selective equality lookup is a typical use case.
*/

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM employees
WHERE employee_id = 1000;

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM employees
WHERE salary = 250000;

-- The planner may still choose a sequential scan when the estimated
-- index-access cost exceeds the sequential-access cost.

-- ============================================================================
-- 7. INDEX-ONLY SCAN
-- ============================================================================

/*
An index-only scan can return requested columns from the index itself
when the index contains all required values and visibility-map
information confirms that heap visibility checks can be avoided.

A covering index reduces the need for heap access.
*/

CREATE INDEX idx_employees_department_salary_covering
ON employees (department_id, salary)
INCLUDE (employee_name);

ANALYZE employees;

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    department_id,
    salary,
    employee_name
FROM employees
WHERE department_id = 1
  AND salary > 100000;

-- VACUUM updates visibility-map information.
-- This may improve the opportunity for index-only scans.

VACUUM (ANALYZE) employees;

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    department_id,
    salary,
    employee_name
FROM employees
WHERE department_id = 1
  AND salary > 100000;

-- ============================================================================
-- 8. BITMAP INDEX SCAN AND BITMAP HEAP SCAN
-- ============================================================================

/*
A bitmap plan can combine multiple index results.

Bitmap Index Scan:
    Produces tuple-location bitmaps from individual indexes.

Bitmap AND:
    Intersects candidate tuple locations.

Bitmap OR:
    Combines candidate tuple locations.

Bitmap Heap Scan:
    Visits relevant heap pages and checks candidate tuples.

Bitmap access can reduce repeated random heap-page visits.
*/

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM employees
WHERE department_id = 1
  AND location_id = 1;

-- The planner decides whether BitmapAnd, Index Scan or Seq Scan
-- is the least expensive valid execution plan.

-- Explicitly demonstrate Bitmap OR eligibility.

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM employees
WHERE department_id = 1
   OR location_id = 2;

-- ============================================================================
-- 9. CONTROLLED SCAN STRATEGY EXPERIMENTS
-- ============================================================================

/*
These settings are diagnostic controls, not production tuning defaults.

They discourage selected plan types so alternative plans can be examined.
They do not guarantee that an impossible or unsupported plan will appear.
*/

BEGIN;

SET LOCAL enable_seqscan = OFF;
SET LOCAL enable_bitmapscan = OFF;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM employees
WHERE employee_id = 1000;

ROLLBACK;

BEGIN;

SET LOCAL enable_indexscan = OFF;
SET LOCAL enable_indexonlyscan = OFF;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM employees
WHERE employee_id = 1000;

ROLLBACK;

BEGIN;

SET LOCAL enable_seqscan = OFF;
SET LOCAL enable_indexscan = OFF;
SET LOCAL enable_indexonlyscan = OFF;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM employees
WHERE department_id = 1
  AND location_id = 1;

ROLLBACK;

-- ============================================================================
-- 10. SELECTIVITY AND CARDINALITY ANALYSIS
-- ============================================================================

CREATE VIEW employee_department_distribution AS
SELECT
    d.department_name,
    COUNT(*) AS total_employees,
    COUNT(*) FILTER (WHERE e.is_active) AS active_employees,
    ROUND(AVG(e.salary), 2) AS average_salary,
    MIN(e.salary) AS minimum_salary,
    MAX(e.salary) AS maximum_salary
FROM employees e
JOIN departments d
    ON d.department_id = e.department_id
GROUP BY d.department_name;

SELECT *
FROM employee_department_distribution
ORDER BY total_employees DESC;

-- Compare total rows and qualifying rows.

WITH filter_statistics AS (
    SELECT
        COUNT(*) AS total_rows,
        COUNT(*) FILTER (
            WHERE department_id = 1
        ) AS department_matches,
        COUNT(*) FILTER (
            WHERE location_id = 1
        ) AS location_matches,
        COUNT(*) FILTER (
            WHERE department_id = 1
              AND location_id = 1
        ) AS combined_matches
    FROM employees
)
SELECT
    total_rows,
    department_matches,
    location_matches,
    combined_matches,
    ROUND(
        department_matches::NUMERIC /
        NULLIF(total_rows, 0),
        4
    ) AS department_selectivity,
    ROUND(
        location_matches::NUMERIC /
        NULLIF(total_rows, 0),
        4
    ) AS location_selectivity,
    ROUND(
        combined_matches::NUMERIC /
        NULLIF(total_rows, 0),
        4
    ) AS combined_selectivity
FROM filter_statistics;

-- ============================================================================
-- 11. INDEX-RELATED TABLE METADATA
-- ============================================================================

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'scan_lab'
  AND tablename = 'employees'
ORDER BY indexname;

SELECT
    indexrelname AS index_name,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'scan_lab'
  AND relname = 'employees'
ORDER BY indexrelname;

-- ============================================================================
-- 12. PARTIAL INDEX
-- ============================================================================

/*
A partial index stores only rows satisfying its predicate.

It is useful when queries repeatedly target a relatively small,
well-defined subset of a table.
*/

CREATE INDEX idx_employees_active_salary
ON employees (salary)
WHERE is_active = TRUE;

ANALYZE employees;

EXPLAIN (ANALYZE, BUFFERS)
SELECT employee_id, employee_name, salary
FROM employees
WHERE is_active = TRUE
  AND salary > 150000;

-- ============================================================================
-- 13. COMPOSITE INDEX
-- ============================================================================

/*
Column order matters.

For an index on (department_id, location_id), queries using the
leading department_id column can benefit from the index.

The index is not equivalent to two independent single-column indexes.
*/

CREATE INDEX idx_employees_department_location
ON employees (department_id, location_id);

ANALYZE employees;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM employees
WHERE department_id = 1
  AND location_id = 1;

-- ============================================================================
-- 14. QUERY PERFORMANCE REPORTING
-- ============================================================================

CREATE VIEW employee_scan_report AS
SELECT
    d.department_name,
    l.location_name,
    COUNT(*) AS employee_count,
    COUNT(*) FILTER (
        WHERE e.is_active
    ) AS active_count,
    ROUND(AVG(e.salary), 2) AS average_salary,
    ROUND(
        COUNT(*) FILTER (WHERE e.is_active)::NUMERIC
        / NULLIF(COUNT(*), 0),
        4
    ) AS active_ratio
FROM employees e
JOIN departments d
    ON d.department_id = e.department_id
JOIN locations l
    ON l.location_id = e.location_id
GROUP BY
    d.department_name,
    l.location_name;

SELECT *
FROM employee_scan_report
ORDER BY employee_count DESC;

-- ============================================================================
-- 15. FUNCTION FOR SCAN COST COMPARISON
-- ============================================================================

/*
This function provides a simplified educational cost estimate.
It is not a replacement for PostgreSQL's internal cost model.
*/

CREATE OR REPLACE FUNCTION estimated_scan_costs(
    p_total_rows BIGINT,
    p_total_pages BIGINT,
    p_selectivity NUMERIC
)
RETURNS TABLE (
    scan_strategy TEXT,
    estimated_rows NUMERIC,
    estimated_cost NUMERIC
)
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_rows NUMERIC;
    v_seq_cost NUMERIC;
    v_index_cost NUMERIC;
    v_bitmap_cost NUMERIC;
BEGIN
    IF p_total_rows < 0
       OR p_total_pages < 0
       OR p_selectivity < 0
       OR p_selectivity > 1 THEN

        RAISE EXCEPTION
            'Invalid row count, page count or selectivity';
    END IF;

    v_rows := p_total_rows * p_selectivity;

    v_seq_cost :=
        p_total_pages * 1.0
        + p_total_rows * 0.01;

    v_index_cost :=
        LN(GREATEST(2, p_total_rows)) / LN(2)
        + v_rows * 4.005;

    v_bitmap_cost :=
        LN(GREATEST(2, p_total_rows)) / LN(2)
        + v_rows * 0.015
        + CEIL(v_rows / 100.0) * 4.0;

    RETURN QUERY
    SELECT
        'Sequential Scan'::TEXT,
        v_rows,
        v_seq_cost

    UNION ALL

    SELECT
        'Index Scan'::TEXT,
        v_rows,
        v_index_cost

    UNION ALL

    SELECT
        'Bitmap Heap Scan'::TEXT,
        v_rows,
        v_bitmap_cost;
END;
$$;

SELECT *
FROM estimated_scan_costs(
    100000,
    1500,
    0.001
)
ORDER BY estimated_cost;

-- Compare with a less selective query.

SELECT *
FROM estimated_scan_costs(
    100000,
    1500,
    0.75
)
ORDER BY estimated_cost;

-- ============================================================================
-- 16. FUNCTION FOR INDEX MAINTENANCE AUDIT
-- ============================================================================

CREATE TABLE index_maintenance_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL,
    operation VARCHAR(20) NOT NULL
        CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION audit_employee_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO index_maintenance_audit (
            employee_id,
            operation
        )
        VALUES (
            NEW.employee_id,
            'INSERT'
        );

        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO index_maintenance_audit (
            employee_id,
            operation
        )
        VALUES (
            NEW.employee_id,
            'UPDATE'
        );

        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO index_maintenance_audit (
            employee_id,
            operation
        )
        VALUES (
            OLD.employee_id,
            'DELETE'
        );

        RETURN OLD;
    END IF;

    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_employee_audit
AFTER INSERT OR UPDATE OR DELETE
ON employees
FOR EACH ROW
EXECUTE FUNCTION audit_employee_changes();

-- The database automatically maintains its indexes during these changes.
-- The trigger records the logical DML event.

BEGIN;

INSERT INTO employees (
    employee_name,
    department_id,
    location_id,
    salary,
    is_active,
    hired_at
)
VALUES (
    'Transaction-Test',
    1,
    1,
    85000,
    TRUE,
    CURRENT_DATE
);

UPDATE employees
SET salary = 90000
WHERE employee_name = 'Transaction-Test';

DELETE FROM employees
WHERE employee_name = 'Transaction-Test';

COMMIT;

SELECT *
FROM index_maintenance_audit
ORDER BY audit_id DESC
LIMIT 10;

-- ============================================================================
-- 17. INDEX USAGE AND STORAGE
-- ============================================================================

SELECT
    indexrelname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'scan_lab'
  AND relname = 'employees'
ORDER BY pg_relation_size(indexrelid) DESC;

SELECT
    pg_size_pretty(
        pg_relation_size('scan_lab.employees')
    ) AS table_size,
    pg_size_pretty(
        pg_total_relation_size('scan_lab.employees')
    ) AS total_size;

-- ============================================================================
-- 18. VALIDATION AND FINAL EXECUTION
-- ============================================================================

DO $$
DECLARE
    v_employee_count BIGINT;
    v_department_count BIGINT;
    v_index_count BIGINT;
BEGIN
    SELECT COUNT(*)
    INTO v_employee_count
    FROM employees;

    SELECT COUNT(*)
    INTO v_department_count
    FROM departments;

    SELECT COUNT(*)
    INTO v_index_count
    FROM pg_indexes
    WHERE schemaname = 'scan_lab'
      AND tablename = 'employees';

    IF v_employee_count < 100000 THEN
        RAISE EXCEPTION 'Employee dataset validation failed';
    END IF;

    IF v_department_count <> 4 THEN
        RAISE EXCEPTION 'Department validation failed';
    END IF;

    IF v_index_count < 5 THEN
        RAISE EXCEPTION 'Index creation validation failed';
    END IF;

    RAISE NOTICE 'Employee records: %', v_employee_count;
    RAISE NOTICE 'Departments: %', v_department_count;
    RAISE NOTICE 'Employee indexes: %', v_index_count;
    RAISE NOTICE 'All database validations passed';
END;
$$;

-- Final planner inspection.

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM employees
WHERE department_id = 1
  AND location_id = 1
  AND is_active = TRUE;

-- ============================================================================
-- END OF SCRIPT
-- ============================================================================
