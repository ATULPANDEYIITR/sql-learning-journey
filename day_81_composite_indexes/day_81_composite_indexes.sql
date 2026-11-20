/*
===============================================================================
COMPOSITE INDEXES
Multi-column Indexes, Column Ordering, and Selectivity
PostgreSQL 15+

Demonstrates:
- Composite B-tree indexes.
- Column ordering.
- Leftmost-prefix behavior.
- Equality and range conditions.
- Selectivity and cardinality.
- Query workload tracking.
- Index usage statistics.
- Redundancy investigation.
- Covering indexes and INCLUDE.
- Index maintenance considerations.
- Transactional index creation.
===============================================================================
*/

BEGIN;

CREATE SCHEMA IF NOT EXISTS index_lab;

SET search_path TO index_lab, public;

-- ============================================================================
-- 1. DOMAIN TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name VARCHAR(150) NOT NULL,
    region VARCHAR(30) NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT customers_region_check
        CHECK (region IN ('NORTH', 'SOUTH', 'EAST', 'WEST'))
);

CREATE TABLE IF NOT EXISTS orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    customer_id BIGINT NOT NULL
        REFERENCES customers(customer_id),

    status VARCHAR(20) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,

    total_amount NUMERIC(12, 2) NOT NULL,

    payment_method VARCHAR(30) NOT NULL,

    region VARCHAR(30) NOT NULL,

    CONSTRAINT orders_status_check
        CHECK (
            status IN (
                'PENDING',
                'PAID',
                'SHIPPED',
                'CANCELLED'
            )
        ),

    CONSTRAINT orders_amount_check
        CHECK (total_amount >= 0),

    CONSTRAINT orders_region_check
        CHECK (region IN ('NORTH', 'SOUTH', 'EAST', 'WEST')),

    CONSTRAINT orders_payment_check
        CHECK (
            payment_method IN (
                'CARD',
                'UPI',
                'NET_BANKING',
                'CASH',
                'WALLET'
            )
        )
);

-- ============================================================================
-- 2. SAMPLE DATA
-- ============================================================================

INSERT INTO customers (
    customer_name,
    region,
    registered_at
)
SELECT
    'Customer ' || number,
    CASE number % 4
        WHEN 0 THEN 'NORTH'
        WHEN 1 THEN 'SOUTH'
        WHEN 2 THEN 'EAST'
        ELSE 'WEST'
    END,
    TIMESTAMPTZ '2025-01-01 00:00:00+00'
        + number * INTERVAL '1 hour'
FROM generate_series(1, 1000) AS number
ON CONFLICT DO NOTHING;

INSERT INTO orders (
    customer_id,
    status,
    created_at,
    total_amount,
    payment_method,
    region
)
SELECT
    1 + (number % 1000),

    CASE
        WHEN number % 100 < 15 THEN 'PENDING'
        WHEN number % 100 < 60 THEN 'PAID'
        WHEN number % 100 < 90 THEN 'SHIPPED'
        ELSE 'CANCELLED'
    END,

    TIMESTAMPTZ '2025-01-01 00:00:00+00'
        + number * INTERVAL '5 minutes',

    ROUND(
        (50 + (number % 5000))::NUMERIC,
        2
    ),

    CASE number % 5
        WHEN 0 THEN 'CARD'
        WHEN 1 THEN 'UPI'
        WHEN 2 THEN 'NET_BANKING'
        WHEN 3 THEN 'CASH'
        ELSE 'WALLET'
    END,

    CASE number % 4
        WHEN 0 THEN 'NORTH'
        WHEN 1 THEN 'SOUTH'
        WHEN 2 THEN 'EAST'
        ELSE 'WEST'
    END

FROM generate_series(1, 20000) AS number;

-- ============================================================================
-- 3. COMPOSITE INDEX DEFINITIONS
-- ============================================================================

/*
Index A:
(customer_id, status, created_at)

Supports:
- customer_id
- customer_id + status
- customer_id + status + created_at

The customer_id leading column is important for customer-specific queries.
*/

CREATE INDEX IF NOT EXISTS idx_orders_customer_status_created
ON orders (
    customer_id,
    status,
    created_at DESC
);

/*
Index B:
(status, created_at)

Supports status-based retrieval and recent-order queries.

It does not provide an equivalent direct lookup path for customer_id alone.
*/

CREATE INDEX IF NOT EXISTS idx_orders_status_created
ON orders (
    status,
    created_at DESC
);

/*
Index C:
(region, total_amount)

Supports regional equality filtering followed by amount range filtering.
*/

CREATE INDEX IF NOT EXISTS idx_orders_region_amount
ON orders (
    region,
    total_amount
);

/*
Index D:
(customer_id, status, created_at)
with total_amount stored in leaf tuples.

INCLUDE columns are not search-key columns.
*/

CREATE INDEX IF NOT EXISTS idx_orders_customer_covering
ON orders (
    customer_id,
    status,
    created_at DESC
)
INCLUDE (total_amount);

/*
This overlapping index is intentionally created to demonstrate
redundancy investigation. It should not automatically be dropped.
*/

CREATE INDEX IF NOT EXISTS idx_orders_customer_only
ON orders(customer_id);

COMMIT;

-- Update planner statistics after loading records and creating indexes.

ANALYZE customers;
ANALYZE orders;

-- ============================================================================
-- 4. QUERY PLAN: COMPOSITE INDEX WITH EQUALITY CONDITIONS
-- ============================================================================

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    customer_id,
    status,
    created_at
FROM orders
WHERE customer_id = 42
  AND status = 'PAID';

-- ============================================================================
-- 5. QUERY PLAN: EQUALITY FOLLOWED BY RANGE
-- ============================================================================

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    created_at,
    total_amount
FROM orders
WHERE customer_id = 42
  AND status = 'PAID'
  AND created_at >= TIMESTAMPTZ '2025-02-01 00:00:00+00'
ORDER BY created_at DESC
LIMIT 20;

-- ============================================================================
-- 6. LEFTMOST-PREFIX INVESTIGATION
-- ============================================================================

-- Uses the leading customer_id column.

EXPLAIN (ANALYZE, BUFFERS)
SELECT order_id
FROM orders
WHERE customer_id = 42;

-- The customer_status_created index cannot efficiently use
-- created_at alone as a leading search condition.

EXPLAIN (ANALYZE, BUFFERS)
SELECT order_id
FROM orders
WHERE created_at >= TIMESTAMPTZ '2025-02-01 00:00:00+00';

-- Alternative index for status-based retrieval.

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    created_at
FROM orders
WHERE status = 'PAID'
ORDER BY created_at DESC
LIMIT 25;

-- ============================================================================
-- 7. SELECTIVITY ANALYSIS
-- ============================================================================

/*
Selectivity is the fraction of rows satisfying a predicate.

A lower fraction indicates a more selective predicate.

The following calculation uses actual table data rather than
assuming a uniform distribution.
*/

CREATE OR REPLACE VIEW v_column_selectivity AS
SELECT
    'customer_id' AS column_name,
    COUNT(DISTINCT customer_id)::NUMERIC /
        NULLIF(COUNT(*), 0) AS distinct_ratio,
    1.0 / NULLIF(COUNT(DISTINCT customer_id), 0) AS
        approximate_equality_selectivity
FROM orders

UNION ALL

SELECT
    'status',
    COUNT(DISTINCT status)::NUMERIC /
        NULLIF(COUNT(*), 0),
    1.0 / NULLIF(COUNT(DISTINCT status), 0)
FROM orders

UNION ALL

SELECT
    'region',
    COUNT(DISTINCT region)::NUMERIC /
        NULLIF(COUNT(*), 0),
    1.0 / NULLIF(COUNT(DISTINCT region), 0)
FROM orders

UNION ALL

SELECT
    'payment_method',
    COUNT(DISTINCT payment_method)::NUMERIC /
        NULLIF(COUNT(*), 0),
    1.0 / NULLIF(COUNT(DISTINCT payment_method), 0)
FROM orders;

SELECT *
FROM v_column_selectivity
ORDER BY approximate_equality_selectivity;

-- Actual predicate selectivity.

SELECT
    COUNT(*) AS total_rows,

    COUNT(*) FILTER (
        WHERE status = 'PAID'
    ) AS paid_rows,

    ROUND(
        COUNT(*) FILTER (
            WHERE status = 'PAID'
        )::NUMERIC /
        NULLIF(COUNT(*), 0),
        4
    ) AS paid_selectivity

FROM orders;

-- ============================================================================
-- 8. MULTI-COLUMN CORRELATION AND COMBINED SELECTIVITY
-- ============================================================================

/*
Multiplying individual selectivities assumes independence.
Real data can contain correlated columns.

This query compares an independence estimate with the actual
combined predicate fraction.
*/

WITH individual AS (
    SELECT
        COUNT(*) FILTER (
            WHERE customer_id = 42
        )::NUMERIC / NULLIF(COUNT(*), 0) AS customer_fraction,

        COUNT(*) FILTER (
            WHERE status = 'PAID'
        )::NUMERIC / NULLIF(COUNT(*), 0) AS status_fraction,

        COUNT(*) FILTER (
            WHERE customer_id = 42
              AND status = 'PAID'
        )::NUMERIC / NULLIF(COUNT(*), 0) AS actual_combined_fraction,

        COUNT(*) AS total_rows

    FROM orders
)

SELECT
    customer_fraction,
    status_fraction,

    customer_fraction * status_fraction
        AS independence_estimate,

    actual_combined_fraction,

    ABS(
        customer_fraction * status_fraction
        - actual_combined_fraction
    ) AS estimation_error

FROM individual;

-- ============================================================================
-- 9. POSTGRESQL COLUMN STATISTICS
-- ============================================================================

SELECT
    schemaname,
    tablename,
    attname,
    null_frac,
    n_distinct,
    most_common_vals,
    most_common_freqs,
    correlation
FROM pg_stats
WHERE schemaname = 'index_lab'
  AND tablename = 'orders'
ORDER BY attname;

-- ============================================================================
-- 10. WORKLOAD QUERY AGGREGATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS query_workload (
    workload_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    query_name VARCHAR(150) NOT NULL,

    predicate_columns TEXT[] NOT NULL,

    ordering_columns TEXT[] NOT NULL DEFAULT '{}',

    execution_count BIGINT NOT NULL DEFAULT 1,

    average_duration_ms NUMERIC(12, 4) NOT NULL,

    CONSTRAINT workload_execution_check
        CHECK (execution_count > 0),

    CONSTRAINT workload_duration_check
        CHECK (average_duration_ms >= 0)
);

INSERT INTO query_workload (
    query_name,
    predicate_columns,
    ordering_columns,
    execution_count,
    average_duration_ms
)
VALUES
(
    'Customer order history',
    ARRAY['customer_id', 'status', 'created_at'],
    ARRAY['created_at'],
    15000,
    4.20
),
(
    'Recent paid orders',
    ARRAY['status', 'created_at'],
    ARRAY['created_at'],
    30000,
    8.50
),
(
    'Regional sales',
    ARRAY['region', 'total_amount'],
    ARRAY[]::TEXT[],
    4000,
    12.80
),
(
    'Customer summary',
    ARRAY['customer_id'],
    ARRAY[]::TEXT[],
    50000,
    2.10
),
(
    'Payment method reporting',
    ARRAY['payment_method'],
    ARRAY[]::TEXT[],
    500,
    18.40
);

-- Frequent and expensive query identification.

SELECT
    query_name,
    predicate_columns,
    ordering_columns,
    execution_count,
    average_duration_ms,

    execution_count * average_duration_ms
        AS cumulative_duration_ms

FROM query_workload
ORDER BY cumulative_duration_ms DESC;

-- ============================================================================
-- 11. INDEX CATALOG AND INDEX USAGE
-- ============================================================================

SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'index_lab'
  AND tablename = 'orders'
ORDER BY indexname;

SELECT
    indexrelname AS index_name,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(
        pg_relation_size(indexrelid)
    ) AS index_size

FROM pg_stat_user_indexes
WHERE schemaname = 'index_lab'
  AND relname = 'orders'
ORDER BY idx_scan DESC;

-- ============================================================================
-- 12. INDEX REDUNDANCY INVESTIGATION
-- ============================================================================

/*
Find indexes whose ordered key columns form a prefix of a larger index.

This is an investigation query, not an automatic DROP recommendation.

Uniqueness, constraints, INCLUDE columns, partial predicates,
operator classes, sort direction and workload must also be considered.
*/

WITH index_columns AS (
    SELECT
        index_class.oid AS index_oid,
        index_class.relname AS index_name,
        table_class.relname AS table_name,
        access_method.amname AS access_method,

        ARRAY_AGG(
            attribute.attname
            ORDER BY key_position.position
        ) FILTER (
            WHERE key_position.position <=
                  index_metadata.indnkeyatts
        ) AS key_columns,

        index_metadata.indisunique AS is_unique,
        index_metadata.indisprimary AS is_primary,
        index_metadata.indisvalid AS is_valid

    FROM pg_index AS index_metadata

    JOIN pg_class AS index_class
        ON index_class.oid = index_metadata.indexrelid

    JOIN pg_class AS table_class
        ON table_class.oid = index_metadata.indrelid

    JOIN pg_namespace AS namespace
        ON namespace.oid = table_class.relnamespace

    JOIN pg_am AS access_method
        ON access_method.oid = index_class.relam

    JOIN LATERAL generate_series(
        1,
        index_metadata.indnatts
    ) AS key_position(position)
        ON TRUE

    JOIN pg_attribute AS attribute
        ON attribute.attrelid = table_class.oid
       AND attribute.attnum =
           index_metadata.indkey[key_position.position - 1]

    WHERE namespace.nspname = 'index_lab'
      AND table_class.relname = 'orders'

    GROUP BY
        index_class.oid,
        index_class.relname,
        table_class.relname,
        access_method.amname,
        index_metadata.indnkeyatts,
        index_metadata.indisunique,
        index_metadata.indisprimary,
        index_metadata.indisvalid
)

SELECT
    smaller.index_name AS potentially_redundant_index,
    larger.index_name AS possible_covering_index,
    smaller.key_columns AS smaller_key,
    larger.key_columns AS larger_key

FROM index_columns AS smaller

JOIN index_columns AS larger
    ON smaller.index_oid <> larger.index_oid
   AND smaller.table_name = larger.table_name
   AND smaller.access_method = larger.access_method
   AND CARDINALITY(smaller.key_columns) <
       CARDINALITY(larger.key_columns)
   AND larger.key_columns[
       1:CARDINALITY(smaller.key_columns)
   ] = smaller.key_columns

WHERE smaller.is_valid
  AND larger.is_valid
  AND NOT smaller.is_primary
  AND NOT smaller.is_unique
  AND NOT larger.is_primary
  AND NOT larger.is_unique

ORDER BY smaller.index_name;

-- ============================================================================
-- 13. COVERING INDEX INVESTIGATION
-- ============================================================================

/*
INCLUDE columns are stored in index leaf tuples.
They are not additional search-key columns.

Index-only scans depend on visibility-map coverage.
*/

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    customer_id,
    status,
    created_at,
    total_amount

FROM orders

WHERE customer_id = 42
  AND status = 'PAID'

ORDER BY created_at DESC

LIMIT 20;

-- ============================================================================
-- 14. PARTIAL INDEX
-- ============================================================================

/*
A partial index can reduce index size when the workload repeatedly
targets a stable subset of rows.
*/

CREATE INDEX IF NOT EXISTS idx_orders_pending_customer_date
ON orders (
    customer_id,
    created_at DESC
)
WHERE status = 'PENDING';

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    created_at
FROM orders
WHERE status = 'PENDING'
  AND customer_id = 42
ORDER BY created_at DESC;

-- ============================================================================
-- 15. TRANSACTIONAL WORKFLOW AND INDEX MAINTENANCE
-- ============================================================================

/*
Regular CREATE INDEX participates in a transaction.
CREATE INDEX CONCURRENTLY cannot execute inside a transaction block.

The following transaction demonstrates a regular index creation
and rollback-safe schema change.
*/

BEGIN;

CREATE INDEX idx_orders_region_status_date
ON orders (
    region,
    status,
    created_at DESC
);

COMMENT ON INDEX idx_orders_region_status_date IS
'Supports regional status filtering and recent-order retrieval.';

COMMIT;

-- ============================================================================
-- 16. INDEX ELIGIBILITY REPORT
-- ============================================================================

/*
This report checks whether the ordered index keys begin with
the required query columns.

It is a structural eligibility check, not a substitute for
PostgreSQL's actual cost-based optimizer.
*/

WITH required_workload AS (
    SELECT
        'Customer history' AS query_name,
        ARRAY['customer_id', 'status']::TEXT[] AS required_prefix

    UNION ALL

    SELECT
        'Status history',
        ARRAY['status']::TEXT[]

    UNION ALL

    SELECT
        'Regional amount filtering',
        ARRAY['region', 'total_amount']::TEXT[]

    UNION ALL

    SELECT
        'Created date only',
        ARRAY['created_at']::TEXT[]
),

available_indexes AS (
    SELECT
        index_class.relname AS index_name,

        ARRAY_AGG(
            attribute.attname
            ORDER BY key_position.position
        ) AS index_columns

    FROM pg_index AS index_metadata

    JOIN pg_class AS index_class
        ON index_class.oid = index_metadata.indexrelid

    JOIN pg_class AS table_class
        ON table_class.oid = index_metadata.indrelid

    JOIN pg_namespace AS namespace
        ON namespace.oid = table_class.relnamespace

    JOIN LATERAL generate_series(
        1,
        index_metadata.indnkeyatts
    ) AS key_position(position)
        ON TRUE

    JOIN pg_attribute AS attribute
        ON attribute.attrelid = table_class.oid
       AND attribute.attnum =
           index_metadata.indkey[key_position.position - 1]

    WHERE namespace.nspname = 'index_lab'
      AND table_class.relname = 'orders'
      AND index_metadata.indisvalid

    GROUP BY index_class.relname
)

SELECT
    workload.query_name,
    workload.required_prefix,
    index_info.index_name,
    index_info.index_columns,

    CASE
        WHEN index_info.index_columns[
            1:CARDINALITY(workload.required_prefix)
        ] = workload.required_prefix
        THEN TRUE
        ELSE FALSE
    END AS leading_prefix_compatible

FROM required_workload AS workload

CROSS JOIN available_indexes AS index_info

ORDER BY
    workload.query_name,
    leading_prefix_compatible DESC,
    index_info.index_name;

-- ============================================================================
-- 17. INDEX MAINTENANCE AND TABLE SIZE
-- ============================================================================

SELECT
    relname AS table_name,
    pg_size_pretty(
        pg_total_relation_size(relid)
    ) AS total_size,
    pg_size_pretty(
        pg_relation_size(relid)
    ) AS heap_size

FROM pg_catalog.pg_statio_user_tables

WHERE schemaname = 'index_lab'
ORDER BY pg_total_relation_size(relid) DESC;

-- ============================================================================
-- 18. FINAL WORKLOAD REPORT
-- ============================================================================

SELECT
    query_name,
    execution_count,
    average_duration_ms,

    ROUND(
        execution_count * average_duration_ms,
        2
    ) AS cumulative_duration_ms,

    predicate_columns,
    ordering_columns

FROM query_workload

ORDER BY
    execution_count * average_duration_ms DESC;

-- Refresh planner statistics after workload and index changes.

ANALYZE orders;

-- Reset session search path to avoid affecting subsequent sessions.

RESET search_path;
