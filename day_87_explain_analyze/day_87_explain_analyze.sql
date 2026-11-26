/*
 * EXPLAIN ANALYZE
 * PostgreSQL actual execution time, actual rows, loops and plan verification.
 *
 * PostgreSQL: 15+
 *
 * This script:
 * 1. Creates a representative order-processing database.
 * 2. Populates realistic customer and order records.
 * 3. Creates indexes and collects planner statistics.
 * 4. Demonstrates EXPLAIN and EXPLAIN ANALYZE.
 * 5. Compares estimated and actual cardinalities.
 * 6. Examines execution loops and buffer activity.
 * 7. Stores execution-plan observations.
 * 8. Implements a reusable plan-verification function.
 *
 * EXPLAIN ANALYZE executes the statement being explained.
 * DML statements therefore require particular care.
 */

BEGIN;

CREATE SCHEMA IF NOT EXISTS explain_lab;

SET search_path TO explain_lab, public;

-- ============================================================
-- 1. DOMAIN TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    region VARCHAR(40) NOT NULL,
    account_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_customer_status
        CHECK (account_status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED'))
);

CREATE TABLE IF NOT EXISTS orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    order_date DATE NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_order_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    CONSTRAINT valid_order_status
        CHECK (
            order_status IN (
                'PENDING',
                'PROCESSING',
                'COMPLETED',
                'CANCELLED'
            )
        ),

    CONSTRAINT valid_order_amount
        CHECK (total_amount >= 0)
);

CREATE TABLE IF NOT EXISTS query_benchmarks (
    benchmark_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_name VARCHAR(150) NOT NULL,
    execution_time_ms NUMERIC(14, 4) NOT NULL,
    planning_time_ms NUMERIC(14, 4) NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    plan_document JSONB,

    CONSTRAINT valid_execution_time
        CHECK (execution_time_ms >= 0),

    CONSTRAINT valid_planning_time
        CHECK (planning_time_ms >= 0)
);

CREATE TABLE IF NOT EXISTS plan_verification_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_name VARCHAR(100) NOT NULL UNIQUE,
    maximum_execution_time_ms NUMERIC(14, 4) NOT NULL,
    maximum_planning_time_ms NUMERIC(14, 4) NOT NULL,
    maximum_row_error_ratio NUMERIC(12, 4) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CHECK (maximum_execution_time_ms >= 0),
    CHECK (maximum_planning_time_ms >= 0),
    CHECK (maximum_row_error_ratio >= 1)
);

-- ============================================================
-- 2. INDEX DESIGN
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_customers_region_status
    ON customers(region, account_status);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON orders(customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_date
    ON orders(order_date);

CREATE INDEX IF NOT EXISTS idx_orders_status_date
    ON orders(order_status, order_date);

CREATE INDEX IF NOT EXISTS idx_benchmarks_query_time
    ON query_benchmarks(query_name, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_benchmarks_plan_gin
    ON query_benchmarks USING GIN(plan_document);

-- ============================================================
-- 3. SAMPLE DATA
-- ============================================================

INSERT INTO customers (
    customer_name,
    email,
    region,
    account_status
)
VALUES
    ('Aarav Sharma', 'aarav@example.com', 'NORTH', 'ACTIVE'),
    ('Priya Verma', 'priya@example.com', 'NORTH', 'ACTIVE'),
    ('Rohan Singh', 'rohan@example.com', 'SOUTH', 'ACTIVE'),
    ('Meera Gupta', 'meera@example.com', 'WEST', 'INACTIVE'),
    ('Kabir Patel', 'kabir@example.com', 'EAST', 'ACTIVE'),
    ('Ananya Rao', 'ananya@example.com', 'SOUTH', 'ACTIVE'),
    ('Vikram Das', 'vikram@example.com', 'WEST', 'SUSPENDED'),
    ('Ishita Jain', 'ishita@example.com', 'NORTH', 'ACTIVE')
ON CONFLICT (email) DO NOTHING;

-- Generate enough records to make execution-plan differences observable.
INSERT INTO orders (
    customer_id,
    order_date,
    order_status,
    total_amount
)
SELECT
    c.customer_id,
    DATE '2025-01-01' + (
        (g.sequence_number % 365)::INTEGER
    ),
    CASE g.sequence_number % 4
        WHEN 0 THEN 'PENDING'
        WHEN 1 THEN 'PROCESSING'
        WHEN 2 THEN 'COMPLETED'
        ELSE 'CANCELLED'
    END,
    ROUND(
        (
            100 + (g.sequence_number % 10000) * 1.25
        )::NUMERIC,
        2
    )
FROM generate_series(1, 50000) AS g(sequence_number)
JOIN customers c
    ON c.customer_id = (
        SELECT MIN(customer_id) +
               ((g.sequence_number - 1) % COUNT(*))
        FROM customers
    )
WHERE NOT EXISTS (
    SELECT 1
    FROM orders existing
    WHERE existing.customer_id = c.customer_id
      AND existing.order_date = (
          DATE '2025-01-01' +
          (g.sequence_number % 365)::INTEGER
      )
      AND existing.total_amount = ROUND(
          (
              100 + (g.sequence_number % 10000) * 1.25
          )::NUMERIC,
          2
      )
);

INSERT INTO plan_verification_policies (
    policy_name,
    maximum_execution_time_ms,
    maximum_planning_time_ms,
    maximum_row_error_ratio
)
VALUES
    ('STANDARD_QUERY', 100, 50, 20),
    ('STRICT_QUERY', 25, 20, 5)
ON CONFLICT (policy_name) DO NOTHING;

-- Statistics help the PostgreSQL planner estimate cardinality.
ANALYZE customers;
ANALYZE orders;

COMMIT;

-- ============================================================
-- 4. BASIC EXPLAIN
-- ============================================================

-- EXPLAIN estimates the plan without executing the SELECT.
EXPLAIN
SELECT
    customer_id,
    customer_name,
    region
FROM customers
WHERE region = 'NORTH'
  AND account_status = 'ACTIVE';

-- ============================================================
-- 5. EXPLAIN ANALYZE
-- ============================================================

-- Executes the query and reports actual measurements.
EXPLAIN (
    ANALYZE,
    BUFFERS,
    VERBOSE,
    COSTS,
    SETTINGS,
    SUMMARY,
    TIMING,
    FORMAT TEXT
)
SELECT
    c.customer_id,
    c.customer_name,
    COUNT(o.order_id) AS order_count,
    COALESCE(SUM(o.total_amount), 0) AS total_sales
FROM customers c
LEFT JOIN orders o
    ON o.customer_id = c.customer_id
WHERE c.region = 'NORTH'
GROUP BY
    c.customer_id,
    c.customer_name
ORDER BY total_sales DESC;

-- JSON format is suitable for programmatic analysis.
EXPLAIN (
    ANALYZE,
    BUFFERS,
    FORMAT JSON
)
SELECT
    order_status,
    COUNT(*) AS order_count,
    SUM(total_amount) AS total_value
FROM orders
WHERE order_date >= DATE '2025-06-01'
GROUP BY order_status;

-- ============================================================
-- 6. UNDERSTANDING ROWS AND LOOPS
-- ============================================================

-- PostgreSQL reports Actual Rows as an average per loop.
-- Total tuples processed at a node can be approximated by:
-- Actual Rows * Actual Loops.
--
-- Node timings are inclusive of their child execution.
-- Accumulated node times must not be summed to obtain query time.

EXPLAIN (
    ANALYZE,
    BUFFERS,
    TIMING,
    SUMMARY
)
SELECT
    c.customer_id,
    o.order_id,
    o.total_amount
FROM customers c
JOIN orders o
    ON o.customer_id = c.customer_id
WHERE c.customer_id BETWEEN 1 AND 5;

-- ============================================================
-- 7. SEQUENTIAL SCAN AND INDEX SCAN COMPARISON
-- ============================================================

-- Baseline: planner chooses the appropriate access method.
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE customer_id = 2;

-- Diagnostic experiment only.
-- Disabling sequential scans discourages that plan type.
-- It does not guarantee an index scan in every circumstance.
BEGIN;

SET LOCAL enable_seqscan = OFF;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE customer_id = 2;

ROLLBACK;

-- ============================================================
-- 8. CARDINALITY ESTIMATION AND STATISTICS
-- ============================================================

-- Compare estimates before and after refreshing statistics.
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE order_status = 'COMPLETED';

ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE order_status = 'COMPLETED';

-- Extended statistics can help with correlated columns.
CREATE STATISTICS IF NOT EXISTS orders_status_date_stats
    (dependencies, mcv)
ON order_status, order_date
FROM orders;

ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE order_status = 'COMPLETED'
  AND order_date >= DATE '2025-06-01';

-- ============================================================
-- 9. QUERY BENCHMARK STORAGE
-- ============================================================

INSERT INTO query_benchmarks (
    query_name,
    planning_time_ms,
    execution_time_ms,
    plan_document
)
VALUES
(
    'customer_order_aggregation',
    0.4500,
    3.7500,
    '{
        "Plan": {
            "Node Type": "Hash Join",
            "Plan Rows": 100,
            "Actual Rows": 100,
            "Actual Loops": 1,
            "Actual Total Time": 3.5
        }
    }'::JSONB
),
(
    'completed_order_filter',
    0.3000,
    5.2000,
    '{
        "Plan": {
            "Node Type": "Bitmap Heap Scan",
            "Plan Rows": 100,
            "Actual Rows": 500,
            "Actual Loops": 1,
            "Actual Total Time": 5.0
        }
    }'::JSONB
);

-- ============================================================
-- 10. JSON EXECUTION-PLAN EXTRACTION
-- ============================================================

CREATE OR REPLACE FUNCTION explain_lab.extract_plan_metrics(
    p_document JSONB
)
RETURNS TABLE (
    node_type TEXT,
    relation_name TEXT,
    estimated_rows NUMERIC,
    actual_rows NUMERIC,
    actual_loops INTEGER,
    actual_total_time_ms NUMERIC,
    accumulated_node_time_ms NUMERIC,
    estimation_error_ratio NUMERIC
)
LANGUAGE SQL
IMMUTABLE
AS $$
    WITH RECURSIVE plan_nodes AS (
        SELECT
            p_document -> 0 -> 'Plan' AS node,
            0 AS depth

        UNION ALL

        SELECT
            child.value,
            parent.depth + 1
        FROM plan_nodes parent
        CROSS JOIN LATERAL jsonb_array_elements(
            COALESCE(parent.node -> 'Plans', '[]'::JSONB)
        ) AS child(value)
    ),
    extracted AS (
        SELECT
            node ->> 'Node Type' AS node_type,
            node ->> 'Relation Name' AS relation_name,

            COALESCE(
                (node ->> 'Plan Rows')::NUMERIC,
                0
            ) AS estimated_rows,

            COALESCE(
                (node ->> 'Actual Rows')::NUMERIC,
                0
            ) AS actual_rows,

            COALESCE(
                (node ->> 'Actual Loops')::INTEGER,
                0
            ) AS actual_loops,

            COALESCE(
                (node ->> 'Actual Total Time')::NUMERIC,
                0
            ) AS actual_total_time_ms

        FROM plan_nodes
    )
    SELECT
        e.node_type,
        e.relation_name,
        e.estimated_rows,
        e.actual_rows,
        e.actual_loops,
        e.actual_total_time_ms,

        e.actual_total_time_ms * e.actual_loops,

        CASE
            WHEN e.estimated_rows = 0
                 AND e.actual_rows = 0 THEN 1
            WHEN e.estimated_rows = 0 THEN NULL
            WHEN e.actual_rows = 0 THEN NULL
            ELSE GREATEST(
                e.actual_rows / e.estimated_rows,
                e.estimated_rows / e.actual_rows
            )
        END

    FROM extracted e;
$$;

-- ============================================================
-- 11. EXECUTION-PLAN VERIFICATION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION explain_lab.verify_execution_plan(
    p_document JSONB,
    p_max_execution_time_ms NUMERIC,
    p_max_row_error_ratio NUMERIC
)
RETURNS TABLE (
    check_name TEXT,
    passed BOOLEAN,
    observed_value NUMERIC,
    permitted_value NUMERIC,
    explanation TEXT
)
LANGUAGE PLPGSQL
STABLE
AS $$
DECLARE
    v_execution_time NUMERIC;
    v_max_error NUMERIC;
BEGIN
    IF p_document IS NULL
       OR jsonb_typeof(p_document) <> 'array'
       OR jsonb_array_length(p_document) = 0 THEN
        RAISE EXCEPTION 'Invalid PostgreSQL JSON plan';
    END IF;

    IF p_max_execution_time_ms < 0 THEN
        RAISE EXCEPTION 'Execution threshold cannot be negative';
    END IF;

    IF p_max_row_error_ratio < 1 THEN
        RAISE EXCEPTION 'Row error ratio must be at least 1';
    END IF;

    IF p_document -> 0 ->> 'Execution Time' IS NULL THEN
        RAISE EXCEPTION
            'Execution Time missing: ANALYZE may not have been enabled';
    END IF;

    v_execution_time :=
        (p_document -> 0 ->> 'Execution Time')::NUMERIC;

    IF v_execution_time < 0 THEN
        RAISE EXCEPTION 'Invalid execution time';
    END IF;

    SELECT COALESCE(MAX(estimation_error_ratio), 1)
    INTO v_max_error
    FROM explain_lab.extract_plan_metrics(p_document);

    RETURN QUERY
    SELECT
        'EXECUTION_TIME'::TEXT,
        v_execution_time <= p_max_execution_time_ms,
        v_execution_time,
        p_max_execution_time_ms,
        'Actual query execution time compared with policy'::TEXT

    UNION ALL

    SELECT
        'ROW_ESTIMATION'::TEXT,
        v_max_error <= p_max_row_error_ratio,
        v_max_error,
        p_max_row_error_ratio,
        'Maximum node-level estimated-versus-actual row ratio'::TEXT;
END;
$$;

-- ============================================================
-- 12. REPORTING AND EVALUATION
-- ============================================================

-- Benchmark summary.
SELECT
    query_name,
    COUNT(*) AS benchmark_runs,
    ROUND(AVG(execution_time_ms), 4) AS average_execution_ms,
    ROUND(MIN(execution_time_ms), 4) AS minimum_execution_ms,
    ROUND(MAX(execution_time_ms), 4) AS maximum_execution_ms,
    ROUND(AVG(planning_time_ms), 4) AS average_planning_ms
FROM query_benchmarks
GROUP BY query_name
ORDER BY average_execution_ms DESC;

-- Queries exceeding the active standard policy.
SELECT
    b.query_name,
    b.execution_time_ms,
    p.maximum_execution_time_ms,
    b.execution_time_ms <= p.maximum_execution_time_ms AS time_passed
FROM query_benchmarks b
CROSS JOIN plan_verification_policies p
WHERE p.policy_name = 'STANDARD_QUERY'
  AND p.active
ORDER BY b.execution_time_ms DESC;

-- Extract individual nodes from stored plans.
SELECT
    b.query_name,
    m.node_type,
    m.relation_name,
    m.estimated_rows,
    m.actual_rows,
    m.actual_loops,
    m.actual_rows * m.actual_loops AS total_actual_rows,
    m.actual_total_time_ms,
    m.accumulated_node_time_ms,
    m.estimation_error_ratio
FROM query_benchmarks b
CROSS JOIN LATERAL
    explain_lab.extract_plan_metrics(b.plan_document) m
ORDER BY b.query_name, m.accumulated_node_time_ms DESC;

-- ============================================================
-- 13. VERIFICATION EXAMPLE
-- ============================================================

SELECT
    b.query_name,
    v.check_name,
    v.passed,
    v.observed_value,
    v.permitted_value,
    v.explanation
FROM query_benchmarks b
JOIN plan_verification_policies p
    ON p.policy_name = 'STANDARD_QUERY'
   AND p.active
CROSS JOIN LATERAL
    explain_lab.verify_execution_plan(
        b.plan_document,
        p.maximum_execution_time_ms,
        p.maximum_row_error_ratio
    ) v;

-- ============================================================
-- 14. REPORTING VIEW
-- ============================================================

CREATE OR REPLACE VIEW explain_lab.v_query_performance AS
SELECT
    query_name,
    COUNT(*) AS executions,
    ROUND(AVG(execution_time_ms), 4) AS avg_execution_ms,
    ROUND(AVG(planning_time_ms), 4) AS avg_planning_ms,
    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (ORDER BY execution_time_ms)::NUMERIC,
        4
    ) AS median_execution_ms,
    ROUND(MAX(execution_time_ms), 4) AS worst_execution_ms
FROM explain_lab.query_benchmarks
GROUP BY query_name;

SELECT *
FROM explain_lab.v_query_performance;

-- ============================================================
-- 15. SAFE DML EXPLAIN ANALYZE
-- ============================================================

-- EXPLAIN ANALYZE executes DML.
-- A transaction with ROLLBACK prevents this test modification
-- from becoming permanent.

BEGIN;

EXPLAIN (ANALYZE, BUFFERS, WAL)
UPDATE explain_lab.orders
SET total_amount = total_amount + 1
WHERE order_status = 'PENDING'
  AND customer_id = 1;

ROLLBACK;

-- ============================================================
-- 16. TABLE AND INDEX STATISTICS
-- ============================================================

SELECT
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'explain_lab'
ORDER BY n_live_tup DESC;

SELECT
    schemaname,
    relname,
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'explain_lab'
ORDER BY idx_scan DESC;

-- ============================================================
-- 17. TRANSACTIONAL PLAN-VERIFICATION TEST
-- ============================================================

BEGIN;

DO $$
DECLARE
    v_document JSONB;
    v_passed BOOLEAN;
BEGIN
    v_document := '[
        {
            "Planning Time": 0.2,
            "Execution Time": 2.5,
            "Plan": {
                "Node Type": "Index Scan",
                "Plan Rows": 100,
                "Actual Rows": 100,
                "Actual Loops": 1,
                "Actual Total Time": 2.0
            }
        }
    ]'::JSONB;

    SELECT BOOL_AND(passed)
    INTO v_passed
    FROM explain_lab.verify_execution_plan(
        v_document,
        10,
        5
    );

    IF NOT v_passed THEN
        RAISE EXCEPTION 'Execution plan verification failed';
    END IF;

    RAISE NOTICE 'Execution plan verification passed';
END;
$$;

COMMIT;

-- End of demonstration.
