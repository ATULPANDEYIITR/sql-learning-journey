-- ============================================================
-- QUERY OPTIMIZATION
-- Predicate Pushdown, Join Optimization and Reduced Work
-- PostgreSQL 14+
-- ============================================================

DROP SCHEMA IF EXISTS query_optimization CASCADE;
CREATE SCHEMA query_optimization;

SET search_path TO query_optimization, public;

-- ============================================================
-- 1. RELATIONAL DATA MODEL
-- ============================================================

CREATE TABLE departments (
    department_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    CONSTRAINT uq_department_name UNIQUE (department_name)
);

CREATE TABLE employees (
    employee_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_name VARCHAR(150) NOT NULL,
    department_id BIGINT NOT NULL,
    salary NUMERIC(12, 2) NOT NULL,
    employment_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_employee_department
        FOREIGN KEY (department_id)
        REFERENCES departments(department_id),

    CONSTRAINT ck_salary_nonnegative
        CHECK (salary >= 0),

    CONSTRAINT ck_employment_status
        CHECK (
            employment_status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')
        )
);

-- ============================================================
-- 2. INDEXES
-- ============================================================

-- Supports department-based employee retrieval.
CREATE INDEX idx_employees_department
    ON employees(department_id);

-- Supports filtering active employees by salary.
CREATE INDEX idx_employees_active_salary
    ON employees(salary)
    WHERE employment_status = 'ACTIVE';

-- Supports location-based department filtering.
CREATE INDEX idx_departments_location
    ON departments(location);

-- Supports common department and salary retrieval.
CREATE INDEX idx_employees_department_salary
    ON employees(department_id, salary DESC)
    WHERE employment_status = 'ACTIVE';

-- ============================================================
-- 3. SAMPLE DATA
-- ============================================================

INSERT INTO departments (department_name, location)
VALUES
    ('Engineering', 'Lucknow'),
    ('Research', 'Delhi'),
    ('Cybersecurity', 'Lucknow'),
    ('Finance', 'Mumbai'),
    ('Operations', 'Pune'),
    ('Data Science', 'Bengaluru');

INSERT INTO employees (
    employee_name,
    department_id,
    salary,
    employment_status
)
SELECT
    'Employee-' || generated_id,
    ((generated_id - 1) % 6) + 1,
    20000 + ((generated_id * 7919) % 130001),
    CASE
        WHEN generated_id % 5 = 0 THEN 'INACTIVE'
        WHEN generated_id % 17 = 0 THEN 'SUSPENDED'
        ELSE 'ACTIVE'
    END
FROM generate_series(1, 10000) AS generated_id;

-- ============================================================
-- 4. QUERY METRICS
-- ============================================================

CREATE TABLE optimization_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    strategy VARCHAR(40) NOT NULL,
    rows_returned BIGINT NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    execution_details JSONB NOT NULL DEFAULT '{}'::JSONB
);

-- ============================================================
-- 5. BASELINE QUERY
-- ============================================================

-- This query expresses a relational operation without forcing a
-- physical join algorithm. PostgreSQL chooses the actual plan.

CREATE OR REPLACE VIEW active_employee_details AS
SELECT
    e.employee_id,
    e.employee_name,
    e.salary,
    d.department_name,
    d.location
FROM employees AS e
JOIN departments AS d
    ON d.department_id = e.department_id
WHERE e.employment_status = 'ACTIVE';

-- ============================================================
-- 6. PREDICATE PUSHDOWN
-- ============================================================

-- Filter both relations before performing the logical join.
-- PostgreSQL may independently perform equivalent transformations.

CREATE OR REPLACE VIEW optimized_employee_details AS
WITH filtered_employees AS (
    SELECT
        employee_id,
        employee_name,
        department_id,
        salary
    FROM employees
    WHERE employment_status = 'ACTIVE'
      AND salary >= 75000
),
filtered_departments AS (
    SELECT
        department_id,
        department_name,
        location
    FROM departments
    WHERE location = 'Lucknow'
)
SELECT
    e.employee_id,
    e.employee_name,
    e.salary,
    d.department_name,
    d.location
FROM filtered_employees AS e
JOIN filtered_departments AS d
    ON d.department_id = e.department_id;

-- ============================================================
-- 7. COMPARING QUERY PLANS
-- ============================================================

-- Execute these statements in a PostgreSQL client.
-- EXPLAIN ANALYZE actually executes the SELECT statement.

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT
    e.employee_id,
    e.employee_name,
    e.salary,
    d.department_name
FROM employees AS e
JOIN departments AS d
    ON e.department_id = d.department_id
WHERE e.employment_status = 'ACTIVE'
  AND e.salary >= 75000
  AND d.location = 'Lucknow';

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
WITH filtered_employees AS (
    SELECT *
    FROM employees
    WHERE employment_status = 'ACTIVE'
      AND salary >= 75000
),
filtered_departments AS (
    SELECT *
    FROM departments
    WHERE location = 'Lucknow'
)
SELECT
    e.employee_id,
    e.employee_name,
    e.salary,
    d.department_name
FROM filtered_employees AS e
JOIN filtered_departments AS d
    ON e.department_id = d.department_id;

-- ============================================================
-- 8. JOIN STRATEGY COMPARISON
-- ============================================================

-- Nested-loop join experiment.
-- Planner switches are diagnostic controls, not general tuning advice.

BEGIN;

SET LOCAL enable_hashjoin = OFF;
SET LOCAL enable_mergejoin = OFF;

EXPLAIN (ANALYZE, BUFFERS)
SELECT e.employee_id, d.department_name
FROM employees AS e
JOIN departments AS d
    ON e.department_id = d.department_id
WHERE e.employment_status = 'ACTIVE'
  AND d.location = 'Lucknow';

ROLLBACK;

-- Hash-join experiment.

BEGIN;

SET LOCAL enable_nestloop = OFF;
SET LOCAL enable_mergejoin = OFF;

EXPLAIN (ANALYZE, BUFFERS)
SELECT e.employee_id, d.department_name
FROM employees AS e
JOIN departments AS d
    ON e.department_id = d.department_id
WHERE e.employment_status = 'ACTIVE'
  AND d.location = 'Lucknow';

ROLLBACK;

-- ============================================================
-- 9. FUNCTION: VALIDATE QUERY PARAMETERS
-- ============================================================

CREATE OR REPLACE FUNCTION validate_query_parameters(
    p_minimum_salary NUMERIC,
    p_location VARCHAR
)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF p_minimum_salary IS NULL OR p_minimum_salary < 0 THEN
        RAISE EXCEPTION 'Minimum salary must be nonnegative';
    END IF;

    IF p_location IS NULL OR BTRIM(p_location) = '' THEN
        RAISE EXCEPTION 'Location cannot be empty';
    END IF;

    RETURN TRUE;
END;
$$;

-- ============================================================
-- 10. OPTIMIZED QUERY FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION find_eligible_employees(
    p_minimum_salary NUMERIC,
    p_location VARCHAR,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    employee_id BIGINT,
    employee_name VARCHAR,
    salary NUMERIC,
    department_name VARCHAR
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    PERFORM validate_query_parameters(
        p_minimum_salary,
        p_location
    );

    IF p_limit IS NULL OR p_limit < 1 OR p_limit > 10000 THEN
        RAISE EXCEPTION 'Limit must be between 1 and 10000';
    END IF;

    RETURN QUERY
    SELECT
        e.employee_id,
        e.employee_name,
        e.salary,
        d.department_name
    FROM employees AS e
    JOIN departments AS d
        ON d.department_id = e.department_id
    WHERE e.employment_status = 'ACTIVE'
      AND e.salary >= p_minimum_salary
      AND d.location = p_location
    ORDER BY e.salary DESC, e.employee_id
    LIMIT p_limit;
END;
$$;

-- ============================================================
-- 11. QUERY SELECTIVITY ESTIMATION
-- ============================================================

CREATE OR REPLACE FUNCTION predicate_selectivity_report()
RETURNS TABLE (
    predicate_name TEXT,
    matching_rows BIGINT,
    total_rows BIGINT,
    selectivity NUMERIC
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        'ACTIVE employees'::TEXT,
        COUNT(*) FILTER (
            WHERE employment_status = 'ACTIVE'
        ),
        COUNT(*),
        ROUND(
            COUNT(*) FILTER (
                WHERE employment_status = 'ACTIVE'
            )::NUMERIC / NULLIF(COUNT(*), 0),
            4
        )
    FROM employees

    UNION ALL

    SELECT
        'Salary >= 75000',
        COUNT(*) FILTER (WHERE salary >= 75000),
        COUNT(*),
        ROUND(
            COUNT(*) FILTER (
                WHERE salary >= 75000
            )::NUMERIC / NULLIF(COUNT(*), 0),
            4
        )
    FROM employees;
$$;

-- ============================================================
-- 12. MATERIALIZED AGGREGATION
-- ============================================================

CREATE MATERIALIZED VIEW department_salary_summary AS
SELECT
    d.department_id,
    d.department_name,
    d.location,
    COUNT(e.employee_id) AS total_employees,
    COUNT(e.employee_id) FILTER (
        WHERE e.employment_status = 'ACTIVE'
    ) AS active_employees,
    COALESCE(
        AVG(e.salary) FILTER (
            WHERE e.employment_status = 'ACTIVE'
        ),
        0
    ) AS average_active_salary
FROM departments AS d
LEFT JOIN employees AS e
    ON e.department_id = d.department_id
GROUP BY
    d.department_id,
    d.department_name,
    d.location;

CREATE UNIQUE INDEX idx_department_salary_summary_id
    ON department_salary_summary(department_id);

-- Refresh after changes to the underlying tables.
REFRESH MATERIALIZED VIEW department_salary_summary;

-- ============================================================
-- 13. TRIGGER-BASED AUDIT
-- ============================================================

CREATE OR REPLACE FUNCTION audit_employee_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO optimization_audit (
        strategy,
        rows_returned,
        execution_details
    )
    VALUES (
        'EMPLOYEE_DATA_CHANGE',
        1,
        jsonb_build_object(
            'operation', TG_OP,
            'employee_id',
            CASE
                WHEN TG_OP = 'DELETE' THEN OLD.employee_id
                ELSE NEW.employee_id
            END
        )
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_employee_audit
AFTER INSERT OR UPDATE OR DELETE
ON employees
FOR EACH ROW
EXECUTE FUNCTION audit_employee_changes();

-- ============================================================
-- 14. WORKFLOW PROCESSING
-- ============================================================

CREATE OR REPLACE PROCEDURE execute_optimized_report(
    p_minimum_salary NUMERIC,
    p_location VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_count BIGINT;
BEGIN
    PERFORM validate_query_parameters(
        p_minimum_salary,
        p_location
    );

    SELECT COUNT(*)
    INTO v_count
    FROM employees AS e
    JOIN departments AS d
        ON d.department_id = e.department_id
    WHERE e.employment_status = 'ACTIVE'
      AND e.salary >= p_minimum_salary
      AND d.location = p_location;

    INSERT INTO optimization_audit (
        strategy,
        rows_returned,
        execution_details
    )
    VALUES (
        'PREDICATE_PUSHDOWN',
        v_count,
        jsonb_build_object(
            'minimum_salary', p_minimum_salary,
            'location', p_location
        )
    );
END;
$$;

-- ============================================================
-- 15. TRANSACTION AND FAILURE HANDLING
-- ============================================================

BEGIN;

SAVEPOINT before_salary_update;

UPDATE employees
SET salary = salary * 1.05
WHERE department_id = 1
  AND employment_status = 'ACTIVE'
  AND salary < 100000;

-- The update is committed only if the complete transaction succeeds.

COMMIT;

-- ============================================================
-- 16. RETRIEVAL AND REPORTING
-- ============================================================

-- Optimized employee retrieval.
SELECT *
FROM find_eligible_employees(75000, 'Lucknow', 50);

-- Department aggregation.
SELECT *
FROM department_salary_summary
ORDER BY active_employees DESC;

-- Predicate selectivity.
SELECT *
FROM predicate_selectivity_report();

-- Audit history.
SELECT
    audit_id,
    strategy,
    rows_returned,
    execution_details,
    executed_at
FROM optimization_audit
ORDER BY audit_id DESC
LIMIT 20;

-- CTE-based department analysis.
WITH department_counts AS (
    SELECT
        department_id,
        COUNT(*) AS employee_count,
        COUNT(*) FILTER (
            WHERE employment_status = 'ACTIVE'
        ) AS active_count
    FROM employees
    GROUP BY department_id
)
SELECT
    d.department_name,
    d.location,
    COALESCE(c.employee_count, 0) AS employee_count,
    COALESCE(c.active_count, 0) AS active_count
FROM departments AS d
LEFT JOIN department_counts AS c
    ON c.department_id = d.department_id
ORDER BY active_count DESC;

-- ============================================================
-- 17. STATISTICS MAINTENANCE
-- ============================================================

ANALYZE employees;
ANALYZE departments;

-- Inspect index definitions.
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'query_optimization'
ORDER BY tablename, indexname;
