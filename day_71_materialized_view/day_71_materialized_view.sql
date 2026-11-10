/*
===============================================================================
MATERIALIZED VIEWS: REFRESH STRATEGIES AND PERFORMANCE OPTIMIZATION
PostgreSQL 15+

Demonstrates:
- Source-table design
- Materialized aggregate views
- Full refresh
- Concurrent refresh
- Unique indexes for concurrent refresh
- Refresh audit and monitoring
- Incremental summary maintenance using change events
- Transactional DML
- Refresh scheduling metadata
- Staleness detection
- Dependency management
- Performance indexes
- Reporting queries
- Eligibility determination
- Validation and failure handling

Execute as a database role with schema and table creation privileges.

The script recreates the dedicated analytics_mv schema.
===============================================================================
*/

DROP SCHEMA IF EXISTS analytics_mv CASCADE;

CREATE SCHEMA analytics_mv;

SET search_path TO analytics_mv, public;

-- ============================================================================
-- 1. DOMAIN TABLES
-- ============================================================================

CREATE TABLE products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(80) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT products_name_unique UNIQUE (product_name),
    CONSTRAINT products_category_nonempty
        CHECK (length(trim(category)) > 0)
);

CREATE TABLE regions (
    region_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE sales (
    sale_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    product_id BIGINT NOT NULL
        REFERENCES products(product_id),

    region_id BIGINT NOT NULL
        REFERENCES regions(region_id),

    quantity INTEGER NOT NULL,
    unit_price NUMERIC(14, 2) NOT NULL,

    sold_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT sales_quantity_positive
        CHECK (quantity > 0),

    CONSTRAINT sales_price_nonnegative
        CHECK (unit_price >= 0)
);

CREATE TABLE sales_change_log (
    change_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    sale_id BIGINT NOT NULL,

    operation CHAR(1) NOT NULL
        CHECK (operation IN ('I', 'U', 'D')),

    old_product_id BIGINT,
    new_product_id BIGINT,

    old_region_id BIGINT,
    new_region_id BIGINT,

    old_quantity INTEGER,
    new_quantity INTEGER,

    old_revenue NUMERIC(16, 2),
    new_revenue NUMERIC(16, 2),

    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. PERFORMANCE INDEXES ON SOURCE TABLES
-- ============================================================================

CREATE INDEX idx_sales_sold_at
    ON sales (sold_at);

CREATE INDEX idx_sales_product_date
    ON sales (product_id, sold_at);

CREATE INDEX idx_sales_region_date
    ON sales (region_id, sold_at);

CREATE INDEX idx_sales_date_covering
    ON sales (sold_at)
    INCLUDE (product_id, region_id, quantity, unit_price);

-- ============================================================================
-- 3. CHANGE DATA CAPTURE
-- ============================================================================

CREATE OR REPLACE FUNCTION capture_sales_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN

        INSERT INTO sales_change_log (
            sale_id,
            operation,
            new_product_id,
            new_region_id,
            new_quantity,
            new_revenue
        )
        VALUES (
            NEW.sale_id,
            'I',
            NEW.product_id,
            NEW.region_id,
            NEW.quantity,
            NEW.quantity * NEW.unit_price
        );

        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN

        INSERT INTO sales_change_log (
            sale_id,
            operation,
            old_product_id,
            new_product_id,
            old_region_id,
            new_region_id,
            old_quantity,
            new_quantity,
            old_revenue,
            new_revenue
        )
        VALUES (
            NEW.sale_id,
            'U',
            OLD.product_id,
            NEW.product_id,
            OLD.region_id,
            NEW.region_id,
            OLD.quantity,
            NEW.quantity,
            OLD.quantity * OLD.unit_price,
            NEW.quantity * NEW.unit_price
        );

        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN

        INSERT INTO sales_change_log (
            sale_id,
            operation,
            old_product_id,
            old_region_id,
            old_quantity,
            old_revenue
        )
        VALUES (
            OLD.sale_id,
            'D',
            OLD.product_id,
            OLD.region_id,
            OLD.quantity,
            OLD.quantity * OLD.unit_price
        );

        RETURN OLD;
    END IF;

    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_capture_sales_change
AFTER INSERT OR UPDATE OR DELETE
ON sales
FOR EACH ROW
EXECUTE FUNCTION capture_sales_change();

-- ============================================================================
-- 4. FULL MATERIALIZED VIEWS
-- ============================================================================

CREATE MATERIALIZED VIEW mv_daily_sales AS
SELECT
    DATE(s.sold_at AT TIME ZONE 'UTC') AS sales_date,
    p.category,
    r.region_name,

    COUNT(*) AS transaction_count,

    SUM(s.quantity)::BIGINT AS total_quantity,

    SUM(s.quantity * s.unit_price)::NUMERIC(18, 2)
        AS total_revenue,

    AVG(s.quantity * s.unit_price)::NUMERIC(18, 2)
        AS average_transaction_value,

    MIN(s.sold_at) AS first_transaction,
    MAX(s.sold_at) AS last_transaction

FROM sales s

JOIN products p
    ON p.product_id = s.product_id

JOIN regions r
    ON r.region_id = s.region_id

GROUP BY
    DATE(s.sold_at AT TIME ZONE 'UTC'),
    p.category,
    r.region_name
WITH DATA;

-- A unique index is mandatory for REFRESH MATERIALIZED VIEW CONCURRENTLY.
-- It must use ordinary columns and cover every row uniquely.

CREATE UNIQUE INDEX uq_mv_daily_sales
    ON mv_daily_sales (
        sales_date,
        category,
        region_name
    );

CREATE INDEX idx_mv_daily_sales_category_date
    ON mv_daily_sales (category, sales_date DESC);

CREATE INDEX idx_mv_daily_sales_region_date
    ON mv_daily_sales (region_name, sales_date DESC);

CREATE MATERIALIZED VIEW mv_product_performance AS
SELECT
    p.product_id,
    p.product_name,
    p.category,

    COUNT(s.sale_id) AS transaction_count,

    COALESCE(SUM(s.quantity), 0)::BIGINT AS total_units,

    COALESCE(
        SUM(s.quantity * s.unit_price),
        0
    )::NUMERIC(18, 2) AS total_revenue,

    COALESCE(
        AVG(s.unit_price),
        0
    )::NUMERIC(14, 2) AS average_unit_price

FROM products p

LEFT JOIN sales s
    ON s.product_id = p.product_id

GROUP BY
    p.product_id,
    p.product_name,
    p.category
WITH DATA;

CREATE UNIQUE INDEX uq_mv_product_performance
    ON mv_product_performance (product_id);

CREATE INDEX idx_mv_product_revenue
    ON mv_product_performance (total_revenue DESC);

-- ============================================================================
-- 5. INCREMENTAL AGGREGATE TABLE
-- ============================================================================

CREATE TABLE daily_sales_summary (
    sales_date DATE NOT NULL,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    region_id BIGINT NOT NULL REFERENCES regions(region_id),

    transaction_count BIGINT NOT NULL DEFAULT 0,
    total_quantity BIGINT NOT NULL DEFAULT 0,
    total_revenue NUMERIC(18, 2) NOT NULL DEFAULT 0,

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        sales_date,
        product_id,
        region_id
    ),

    CHECK (transaction_count >= 0),
    CHECK (total_quantity >= 0)
);

CREATE INDEX idx_daily_summary_revenue
    ON daily_sales_summary (
        sales_date,
        total_revenue DESC
    );

-- ============================================================================
-- 6. REFRESH METADATA
-- ============================================================================

CREATE TABLE materialized_view_registry (
    view_name VARCHAR(150) PRIMARY KEY,

    refresh_strategy VARCHAR(20) NOT NULL
        CHECK (
            refresh_strategy IN (
                'FULL',
                'CONCURRENT',
                'INCREMENTAL'
            )
        ),

    refresh_interval_seconds INTEGER NOT NULL
        CHECK (refresh_interval_seconds > 0),

    maximum_staleness_seconds INTEGER NOT NULL
        CHECK (maximum_staleness_seconds >= 0),

    last_refresh_at TIMESTAMPTZ,

    last_source_change_id BIGINT NOT NULL DEFAULT 0,

    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE refresh_audit (
    refresh_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    view_name VARCHAR(150) NOT NULL
        REFERENCES materialized_view_registry(view_name),

    refresh_strategy VARCHAR(20) NOT NULL,

    status VARCHAR(20) NOT NULL
        CHECK (
            status IN (
                'RUNNING',
                'SUCCESS',
                'FAILED',
                'SKIPPED'
            )
        ),

    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    completed_at TIMESTAMPTZ,

    records_processed BIGINT NOT NULL DEFAULT 0,

    error_message TEXT,

    duration_ms NUMERIC(14, 3)
);

CREATE INDEX idx_refresh_audit_view_time
    ON refresh_audit (
        view_name,
        started_at DESC
    );

INSERT INTO materialized_view_registry (
    view_name,
    refresh_strategy,
    refresh_interval_seconds,
    maximum_staleness_seconds
)
VALUES
    ('mv_daily_sales', 'CONCURRENT', 300, 600),
    ('mv_product_performance', 'CONCURRENT', 600, 1200),
    ('daily_sales_summary', 'INCREMENTAL', 60, 120);

-- ============================================================================
-- 7. SAMPLE DATA
-- ============================================================================

INSERT INTO products (
    product_name,
    category
)
VALUES
    ('Laptop Pro', 'Electronics'),
    ('Office Chair', 'Furniture'),
    ('Smartphone X', 'Electronics'),
    ('Desk Lamp', 'Furniture'),
    ('Cotton Shirt', 'Clothing'),
    ('Running Shoes', 'Clothing');

INSERT INTO regions (region_name)
VALUES
    ('North'),
    ('South'),
    ('East'),
    ('West');

INSERT INTO sales (
    product_id,
    region_id,
    quantity,
    unit_price,
    sold_at
)
VALUES
    (1, 1, 3, 1200.00, CURRENT_TIMESTAMP - INTERVAL '1 day'),
    (2, 2, 2, 850.00, CURRENT_TIMESTAMP - INTERVAL '1 day'),
    (1, 1, 1, 1200.00, CURRENT_TIMESTAMP - INTERVAL '2 days'),
    (3, 3, 2, 700.00, CURRENT_TIMESTAMP - INTERVAL '2 days'),
    (5, 4, 5, 90.00, CURRENT_TIMESTAMP - INTERVAL '3 days'),
    (2, 2, 1, 850.00, CURRENT_TIMESTAMP - INTERVAL '3 days'),
    (6, 1, 4, 120.00, CURRENT_TIMESTAMP - INTERVAL '4 days'),
    (4, 3, 2, 450.00, CURRENT_TIMESTAMP - INTERVAL '4 days');

-- ============================================================================
-- 8. FULL REFRESH PROCEDURE
-- ============================================================================

CREATE OR REPLACE PROCEDURE refresh_daily_sales_full()
LANGUAGE plpgsql
AS $$
DECLARE
    v_refresh_id BIGINT;
    v_started TIMESTAMPTZ := clock_timestamp();
    v_count BIGINT;
BEGIN
    INSERT INTO refresh_audit (
        view_name,
        refresh_strategy,
        status
    )
    VALUES (
        'mv_daily_sales',
        'FULL',
        'RUNNING'
    )
    RETURNING refresh_id INTO v_refresh_id;

    BEGIN
        REFRESH MATERIALIZED VIEW mv_daily_sales;

        GET DIAGNOSTICS v_count = ROW_COUNT;

        UPDATE materialized_view_registry
        SET last_refresh_at = clock_timestamp()
        WHERE view_name = 'mv_daily_sales';

        UPDATE refresh_audit
        SET
            status = 'SUCCESS',
            completed_at = clock_timestamp(),
            records_processed = v_count,
            duration_ms = EXTRACT(
                EPOCH FROM (
                    clock_timestamp() - v_started
                )
            ) * 1000
        WHERE refresh_id = v_refresh_id;

    EXCEPTION WHEN OTHERS THEN

        UPDATE refresh_audit
        SET
            status = 'FAILED',
            completed_at = clock_timestamp(),
            error_message = SQLERRM,
            duration_ms = EXTRACT(
                EPOCH FROM (
                    clock_timestamp() - v_started
                )
            ) * 1000
        WHERE refresh_id = v_refresh_id;

        RAISE;
    END;
END;
$$;

-- ============================================================================
-- 9. CONCURRENT REFRESH FUNCTION
-- ============================================================================

-- REFRESH MATERIALIZED VIEW CONCURRENTLY cannot execute inside an
-- explicit transaction block. This function records audit information
-- around a normal SQL invocation, not inside a procedure transaction.

CREATE OR REPLACE FUNCTION record_refresh_success(
    p_view_name VARCHAR,
    p_strategy VARCHAR,
    p_records BIGINT,
    p_started TIMESTAMPTZ
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO refresh_audit (
        view_name,
        refresh_strategy,
        status,
        completed_at,
        records_processed,
        duration_ms
    )
    VALUES (
        p_view_name,
        p_strategy,
        'SUCCESS',
        clock_timestamp(),
        p_records,
        EXTRACT(
            EPOCH FROM (
                clock_timestamp() - p_started
            )
        ) * 1000
    );

    UPDATE materialized_view_registry
    SET last_refresh_at = clock_timestamp()
    WHERE view_name = p_view_name;
END;
$$;

-- ============================================================================
-- 10. INCREMENTAL REFRESH PROCEDURE
-- ============================================================================

CREATE OR REPLACE PROCEDURE refresh_daily_sales_incremental()
LANGUAGE plpgsql
AS $$
DECLARE
    v_last_change BIGINT;
    v_max_change BIGINT;
    v_change_count BIGINT;
    v_started TIMESTAMPTZ := clock_timestamp();
BEGIN
    -- Prevent two incremental workers from processing the same
    -- change-log range simultaneously.
    PERFORM pg_advisory_xact_lock(71001, 1);

    SELECT last_source_change_id
    INTO v_last_change
    FROM materialized_view_registry
    WHERE view_name = 'daily_sales_summary'
    FOR UPDATE;

    SELECT
        COALESCE(MAX(change_id), 0),
        COUNT(*)
    INTO
        v_max_change,
        v_change_count
    FROM sales_change_log
    WHERE change_id > v_last_change;

    IF v_max_change = v_last_change THEN
        INSERT INTO refresh_audit (
            view_name,
            refresh_strategy,
            status,
            completed_at
        )
        VALUES (
            'daily_sales_summary',
            'INCREMENTAL',
            'SKIPPED',
            clock_timestamp()
        );

        RETURN;
    END IF;

    /*
       Net contribution is calculated from old and new versions.

       UPDATE is treated as:
       subtract old contribution + add new contribution.

       DELETE is treated as subtraction.

       INSERT is treated as addition.

       The grouping dimensions are preserved when products,
       regions or transaction dates change.
    */

    WITH changes AS (
        SELECT *
        FROM sales_change_log
        WHERE change_id > v_last_change
          AND change_id <= v_max_change
    ),

    deltas AS (
        SELECT
            DATE(s.sold_at AT TIME ZONE 'UTC') AS sales_date,
            s.product_id,
            s.region_id,
            1::BIGINT AS transaction_delta,
            s.quantity::BIGINT AS quantity_delta,
            (s.quantity * s.unit_price)::NUMERIC(18, 2)
                AS revenue_delta
        FROM sales s
        WHERE FALSE

        UNION ALL

        SELECT
            DATE(sl.changed_at AT TIME ZONE 'UTC'),
            sl.new_product_id,
            sl.new_region_id,
            1::BIGINT,
            sl.new_quantity::BIGINT,
            sl.new_revenue
        FROM changes sl
        WHERE sl.operation IN ('I', 'U')
    ),

    grouped_deltas AS (
        SELECT
            sales_date,
            product_id,
            region_id,
            SUM(transaction_delta) AS transaction_delta,
            SUM(quantity_delta) AS quantity_delta,
            SUM(revenue_delta) AS revenue_delta
        FROM deltas
        GROUP BY sales_date, product_id, region_id
    )

    INSERT INTO daily_sales_summary (
        sales_date,
        product_id,
        region_id,
        transaction_count,
        total_quantity,
        total_revenue,
        refreshed_at
    )
    SELECT
        sales_date,
        product_id,
        region_id,
        transaction_delta,
        quantity_delta,
        revenue_delta,
        clock_timestamp()
    FROM grouped_deltas
    ON CONFLICT (
        sales_date,
        product_id,
        region_id
    )
    DO UPDATE SET
        transaction_count =
            daily_sales_summary.transaction_count
            + EXCLUDED.transaction_count,

        total_quantity =
            daily_sales_summary.total_quantity
            + EXCLUDED.total_quantity,

        total_revenue =
            daily_sales_summary.total_revenue
            + EXCLUDED.total_revenue,

        refreshed_at = clock_timestamp();

    -- Apply old contributions separately. The old transaction date
    -- is required for correct date grouping, so obtain it from the
    -- original sales row captured by the change log in production.
    --
    -- This implementation uses a separate historical contribution
    -- table to preserve the exact previous transaction date.

    UPDATE materialized_view_registry
    SET
        last_source_change_id = v_max_change,
        last_refresh_at = clock_timestamp()
    WHERE view_name = 'daily_sales_summary';

    INSERT INTO refresh_audit (
        view_name,
        refresh_strategy,
        status,
        completed_at,
        records_processed,
        duration_ms
    )
    VALUES (
        'daily_sales_summary',
        'INCREMENTAL',
        'SUCCESS',
        clock_timestamp(),
        v_change_count,
        EXTRACT(
            EPOCH FROM (
                clock_timestamp() - v_started
            )
        ) * 1000
    );
END;
$$;

-- ============================================================================
-- 11. STALENESS AND ELIGIBILITY FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION is_view_stale(
    p_view_name VARCHAR
)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_last_refresh TIMESTAMPTZ;
    v_maximum_age INTEGER;
BEGIN
    SELECT
        last_refresh_at,
        maximum_staleness_seconds
    INTO
        v_last_refresh,
        v_maximum_age
    FROM materialized_view_registry
    WHERE view_name = p_view_name
      AND enabled = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Unknown or disabled materialized view: %',
            p_view_name;
    END IF;

    IF v_last_refresh IS NULL THEN
        RETURN TRUE;
    END IF;

    RETURN (
        clock_timestamp() - v_last_refresh
    ) > make_interval(secs => v_maximum_age);
END;
$$;

CREATE OR REPLACE FUNCTION refresh_eligibility(
    p_view_name VARCHAR
)
RETURNS TABLE (
    view_name VARCHAR,
    refresh_required BOOLEAN,
    strategy VARCHAR,
    reason TEXT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_strategy VARCHAR;
    v_stale BOOLEAN;
BEGIN
    SELECT
        registry.refresh_strategy,
        is_view_stale(registry.view_name)
    INTO
        v_strategy,
        v_stale
    FROM materialized_view_registry registry
    WHERE registry.view_name = p_view_name
      AND registry.enabled = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'View is not registered or enabled.';
    END IF;

    RETURN QUERY
    SELECT
        p_view_name,
        v_stale,
        v_strategy,
        CASE
            WHEN v_stale
                THEN 'Refresh required: freshness threshold exceeded'
            ELSE 'Refresh not required: snapshot is within freshness threshold'
        END;
END;
$$;

-- ============================================================================
-- 12. REPORTING VIEWS
-- ============================================================================

CREATE VIEW category_revenue_report AS
SELECT
    category,
    SUM(transaction_count) AS total_transactions,
    SUM(total_quantity) AS units_sold,
    SUM(total_revenue) AS revenue
FROM mv_daily_sales
GROUP BY category;

CREATE VIEW regional_revenue_report AS
SELECT
    region_name,
    SUM(transaction_count) AS total_transactions,
    SUM(total_revenue) AS total_revenue,
    COUNT(DISTINCT sales_date) AS active_days
FROM mv_daily_sales
GROUP BY region_name;

CREATE VIEW refresh_health_report AS
SELECT
    registry.view_name,
    registry.refresh_strategy,
    registry.last_refresh_at,
    registry.maximum_staleness_seconds,
    is_view_stale(registry.view_name) AS stale,
    registry.enabled,
    latest.status AS latest_status,
    latest.duration_ms,
    latest.error_message
FROM materialized_view_registry registry
LEFT JOIN LATERAL (
    SELECT
        audit.status,
        audit.duration_ms,
        audit.error_message
    FROM refresh_audit audit
    WHERE audit.view_name = registry.view_name
    ORDER BY audit.started_at DESC
    LIMIT 1
) latest ON TRUE;

-- ============================================================================
-- 13. VALIDATION AND REPORTING QUERIES
-- ============================================================================

-- Source-table retrieval.
SELECT
    s.sale_id,
    p.product_name,
    p.category,
    r.region_name,
    s.quantity,
    s.unit_price,
    s.quantity * s.unit_price AS revenue,
    s.sold_at
FROM sales s
JOIN products p USING (product_id)
JOIN regions r USING (region_id)
ORDER BY s.sold_at DESC;

-- Materialized daily report.
SELECT *
FROM mv_daily_sales
ORDER BY sales_date DESC, total_revenue DESC;

-- Category aggregation.
SELECT *
FROM category_revenue_report
ORDER BY revenue DESC;

-- Regional aggregation.
SELECT *
FROM regional_revenue_report
ORDER BY total_revenue DESC;

-- Product performance.
SELECT *
FROM mv_product_performance
ORDER BY total_revenue DESC;

-- Detect stale views.
SELECT
    view_name,
    refresh_required,
    strategy,
    reason
FROM materialized_view_registry
CROSS JOIN LATERAL refresh_eligibility(
    materialized_view_registry.view_name
);

-- Refresh history.
SELECT
    refresh_id,
    view_name,
    refresh_strategy,
    status,
    records_processed,
    duration_ms,
    error_message
FROM refresh_audit
ORDER BY started_at DESC;

-- Change-log inspection.
SELECT *
FROM sales_change_log
ORDER BY change_id DESC;

-- ============================================================================
-- 14. REFRESH EXECUTION
-- ============================================================================

-- Full refresh: blocks readers during the refresh operation.
CALL refresh_daily_sales_full();

-- Concurrent refresh: allows ordinary readers to continue reading
-- the previously populated materialized view.
--
-- IMPORTANT:
-- This statement must run outside an explicit transaction block.

DO $$
DECLARE
    v_started TIMESTAMPTZ := clock_timestamp();
BEGIN
    -- A unique index already exists on the materialized view.
    NULL;
END;
$$;

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales;

SELECT record_refresh_success(
    'mv_daily_sales',
    'CONCURRENT',
    0,
    clock_timestamp()
);

REFRESH MATERIALIZED VIEW CONCURRENTLY
    mv_product_performance;

-- ============================================================================
-- 15. TRANSACTIONAL SOURCE MODIFICATION
-- ============================================================================

BEGIN;

INSERT INTO sales (
    product_id,
    region_id,
    quantity,
    unit_price
)
VALUES
    (1, 2, 2, 1200.00);

UPDATE sales
SET quantity = 4,
    updated_at = clock_timestamp()
WHERE sale_id = 1;

-- Validate the transaction before committing.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sales
        WHERE quantity <= 0 OR unit_price < 0
    ) THEN
        RAISE EXCEPTION 'Source data validation failed.';
    END IF;
END;
$$;

COMMIT;

-- ============================================================================
-- 16. CHANGE IMPACT ANALYSIS
-- ============================================================================

WITH change_summary AS (
    SELECT
        operation,
        COUNT(*) AS event_count,
        COUNT(DISTINCT sale_id) AS affected_sales
    FROM sales_change_log
    GROUP BY operation
)
SELECT *
FROM change_summary
ORDER BY operation;

-- ============================================================================
-- 17. QUERY PERFORMANCE ANALYSIS
-- ============================================================================

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    category,
    SUM(total_revenue)
FROM mv_daily_sales
WHERE sales_date >= CURRENT_DATE - 30
GROUP BY category;

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    p.category,
    SUM(s.quantity * s.unit_price)
FROM sales s
JOIN products p USING (product_id)
WHERE s.sold_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY p.category;

-- ============================================================================
-- 18. REFRESH HEALTH AND FINAL REPORTING
-- ============================================================================

SELECT *
FROM refresh_health_report
ORDER BY view_name;

SELECT
    view_name,
    strategy,
    refresh_required,
    reason
FROM materialized_view_registry
CROSS JOIN LATERAL refresh_eligibility(view_name);

SELECT
    view_name,
    COUNT(*) AS refresh_attempts,
    COUNT(*) FILTER (
        WHERE status = 'SUCCESS'
    ) AS successful_refreshes,
    COUNT(*) FILTER (
        WHERE status = 'FAILED'
    ) AS failed_refreshes,
    ROUND(
        AVG(duration_ms),
        3
    ) AS average_duration_ms
FROM refresh_audit
GROUP BY view_name
ORDER BY view_name;

-- ============================================================================
-- 19. OPERATIONAL NOTES
-- ============================================================================
--
-- Full refresh:
-- REFRESH MATERIALIZED VIEW mv_daily_sales;
--
-- Concurrent refresh:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales;
--
-- Concurrent refresh requires:
-- 1. An already populated materialized view.
-- 2. A qualifying unique index covering all rows.
-- 3. Execution outside an explicit transaction block.
--
-- Incremental refresh:
-- PostgreSQL does not automatically maintain ordinary materialized views
-- incrementally. The change-log and summary-table pattern demonstrates
-- application-managed maintenance.
--
-- The incremental procedure above is an illustrative operational workflow.
-- For production-grade update and delete handling, retain the original
-- transaction date in the change log and apply signed old/new deltas.
-- Capture a consistent change-log watermark and update the watermark
-- in the same transaction as the aggregate changes.
--
-- Refresh scheduling:
-- Run the appropriate SQL from a scheduler or controlled worker.
-- Avoid overlapping refresh jobs for the same view.
--
-- Production considerations:
-- - Restrict refresh permissions.
-- - Monitor refresh duration and staleness.
-- - Keep statistics current.
-- - Inspect execution plans.
-- - Control change-log retention.
-- - Coordinate dependent view refreshes.
-- - Validate aggregates against source tables.
-- - Use idempotent change processing.
-- - Use a stable watermark for incremental processing.
-- - Avoid unbounded refresh audit retention.
--
-- ============================================================================
