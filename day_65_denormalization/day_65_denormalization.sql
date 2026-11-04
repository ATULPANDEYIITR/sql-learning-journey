-- ============================================================
-- DENORMALIZATION: PERFORMANCE-DRIVEN READ MODEL
-- PostgreSQL 15+
-- ============================================================

DROP SCHEMA IF EXISTS denorm_demo CASCADE;
CREATE SCHEMA denorm_demo;

SET search_path TO denorm_demo, public;

-- ------------------------------------------------------------
-- 1. NORMALIZED AUTHORITATIVE DATA
-- ------------------------------------------------------------

CREATE TABLE customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT customer_name_nonempty
        CHECK (length(trim(customer_name)) > 0)
);

CREATE TABLE orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL
        REFERENCES customers(customer_id) ON DELETE RESTRICT,
    order_amount NUMERIC(14, 2) NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT order_amount_nonnegative
        CHECK (order_amount >= 0),

    CONSTRAINT valid_order_status
        CHECK (order_status IN ('pending', 'completed', 'cancelled'))
);

CREATE INDEX idx_orders_customer
    ON orders(customer_id);

CREATE INDEX idx_orders_completed_customer
    ON orders(customer_id)
    INCLUDE (order_amount)
    WHERE order_status = 'completed';

CREATE INDEX idx_orders_created_at
    ON orders(created_at DESC);

-- ------------------------------------------------------------
-- 2. DENORMALIZED READ MODEL
-- ------------------------------------------------------------

CREATE TABLE customer_order_summary (
    customer_id BIGINT PRIMARY KEY
        REFERENCES customers(customer_id) ON DELETE CASCADE,

    customer_name VARCHAR(150) NOT NULL,
    order_count BIGINT NOT NULL DEFAULT 0,
    completed_order_count BIGINT NOT NULL DEFAULT 0,
    total_spending NUMERIC(16, 2) NOT NULL DEFAULT 0,

    projection_version BIGINT NOT NULL DEFAULT 0,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT summary_order_count_nonnegative
        CHECK (order_count >= 0),

    CONSTRAINT summary_completed_count_valid
        CHECK (
            completed_order_count >= 0
            AND completed_order_count <= order_count
        ),

    CONSTRAINT summary_spending_nonnegative
        CHECK (total_spending >= 0)
);

CREATE INDEX idx_summary_spending
    ON customer_order_summary(total_spending DESC);

CREATE INDEX idx_summary_completed_orders
    ON customer_order_summary(completed_order_count DESC);

-- ------------------------------------------------------------
-- 3. PROJECTION AUDIT AND INVALIDATION QUEUE
-- ------------------------------------------------------------

CREATE TABLE projection_refresh_queue (
    customer_id BIGINT PRIMARY KEY
        REFERENCES customers(customer_id) ON DELETE CASCADE,

    invalidated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT valid_retry_count CHECK (retry_count >= 0)
);

CREATE TABLE projection_refresh_log (
    refresh_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    operation VARCHAR(30) NOT NULL,
    succeeded BOOLEAN NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_refresh_log_customer_time
    ON projection_refresh_log(customer_id, created_at DESC);

-- ------------------------------------------------------------
-- 4. SOURCE CHANGE INVALIDATION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION invalidate_customer_projection()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    affected_customer BIGINT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        affected_customer := OLD.customer_id;
    ELSE
        affected_customer := NEW.customer_id;
    END IF;

    INSERT INTO projection_refresh_queue (
        customer_id,
        invalidated_at
    )
    VALUES (
        affected_customer,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (customer_id)
    DO UPDATE SET
        invalidated_at = EXCLUDED.invalidated_at;

    IF TG_OP = 'UPDATE'
       AND OLD.customer_id IS DISTINCT FROM NEW.customer_id THEN

        INSERT INTO projection_refresh_queue (
            customer_id,
            invalidated_at
        )
        VALUES (
            OLD.customer_id,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (customer_id)
        DO UPDATE SET
            invalidated_at = EXCLUDED.invalidated_at;
    END IF;

    RETURN NULL;
END;
$$;

CREATE TRIGGER orders_invalidate_projection
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW
EXECUTE FUNCTION invalidate_customer_projection();

CREATE OR REPLACE FUNCTION invalidate_customer_name_projection()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.customer_name IS DISTINCT FROM NEW.customer_name THEN
        INSERT INTO projection_refresh_queue (
            customer_id,
            invalidated_at
        )
        VALUES (
            NEW.customer_id,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (customer_id)
        DO UPDATE SET
            invalidated_at = EXCLUDED.invalidated_at;
    END IF;

    RETURN NULL;
END;
$$;

CREATE TRIGGER customer_name_invalidation
AFTER UPDATE OF customer_name ON customers
FOR EACH ROW
EXECUTE FUNCTION invalidate_customer_name_projection();

-- ------------------------------------------------------------
-- 5. PROJECTION REBUILD FUNCTION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION refresh_customer_summary(
    p_customer_id BIGINT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_customer_name VARCHAR(150);
    v_order_count BIGINT;
    v_completed_count BIGINT;
    v_total NUMERIC(16, 2);
BEGIN
    SELECT customer_name
    INTO v_customer_name
    FROM customers
    WHERE customer_id = p_customer_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Customer % does not exist', p_customer_id;
    END IF;

    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE order_status = 'completed'),
        COALESCE(
            SUM(order_amount) FILTER (
                WHERE order_status = 'completed'
            ),
            0
        )
    INTO
        v_order_count,
        v_completed_count,
        v_total
    FROM orders
    WHERE customer_id = p_customer_id;

    INSERT INTO customer_order_summary (
        customer_id,
        customer_name,
        order_count,
        completed_order_count,
        total_spending,
        projection_version,
        generated_at
    )
    VALUES (
        p_customer_id,
        v_customer_name,
        v_order_count,
        v_completed_count,
        v_total,
        1,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (customer_id)
    DO UPDATE SET
        customer_name = EXCLUDED.customer_name,
        order_count = EXCLUDED.order_count,
        completed_order_count = EXCLUDED.completed_order_count,
        total_spending = EXCLUDED.total_spending,
        projection_version =
            customer_order_summary.projection_version + 1,
        generated_at = CURRENT_TIMESTAMP;

    DELETE FROM projection_refresh_queue
    WHERE customer_id = p_customer_id;

    INSERT INTO projection_refresh_log (
        customer_id,
        operation,
        succeeded,
        details
    )
    VALUES (
        p_customer_id,
        'REFRESH',
        TRUE,
        'Customer summary rebuilt from authoritative records'
    );

EXCEPTION
    WHEN OTHERS THEN
        INSERT INTO projection_refresh_log (
            customer_id,
            operation,
            succeeded,
            details
        )
        VALUES (
            p_customer_id,
            'REFRESH',
            FALSE,
            SQLSTATE || ': ' || SQLERRM
        );

        RAISE;
END;
$$;

-- ------------------------------------------------------------
-- 6. BATCH REFRESH PROCEDURE
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE refresh_dirty_summaries(
    p_batch_size INTEGER DEFAULT 100
)
LANGUAGE plpgsql
AS $$
DECLARE
    item RECORD;
BEGIN
    IF p_batch_size < 1 OR p_batch_size > 10000 THEN
        RAISE EXCEPTION 'Batch size must be between 1 and 10000';
    END IF;

    FOR item IN
        SELECT customer_id
        FROM projection_refresh_queue
        ORDER BY invalidated_at, customer_id
        LIMIT p_batch_size
    LOOP
        PERFORM refresh_customer_summary(item.customer_id);
    END LOOP;
END;
$$;

-- ------------------------------------------------------------
-- 7. SAMPLE DATA
-- ------------------------------------------------------------

INSERT INTO customers (customer_name, email)
VALUES
    ('Aarav Sharma', 'aarav@example.com'),
    ('Diya Verma', 'diya@example.com'),
    ('Kabir Singh', 'kabir@example.com'),
    ('Meera Gupta', 'meera@example.com');

INSERT INTO orders (
    customer_id,
    order_amount,
    order_status
)
VALUES
    (1, 1200.00, 'completed'),
    (1, 800.00, 'completed'),
    (1, 500.00, 'pending'),
    (2, 2500.00, 'completed'),
    (2, 300.00, 'cancelled'),
    (3, 1000.00, 'pending'),
    (3, 1500.00, 'completed');

-- Initial population of the denormalized read model.
INSERT INTO projection_refresh_queue (customer_id)
SELECT customer_id FROM customers
ON CONFLICT (customer_id)
DO UPDATE SET invalidated_at = CURRENT_TIMESTAMP;

CALL refresh_dirty_summaries(100);

-- ------------------------------------------------------------
-- 8. NORMALIZED QUERY
-- Aggregation is calculated during every query.
-- ------------------------------------------------------------

SELECT
    c.customer_id,
    c.customer_name,
    COUNT(o.order_id) AS order_count,
    COUNT(o.order_id) FILTER (
        WHERE o.order_status = 'completed'
    ) AS completed_order_count,
    COALESCE(
        SUM(o.order_amount) FILTER (
            WHERE o.order_status = 'completed'
        ),
        0
    ) AS total_spending
FROM customers c
LEFT JOIN orders o
    ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY c.customer_id;

-- ------------------------------------------------------------
-- 9. DENORMALIZED QUERY
-- Reads precomputed values without aggregating orders.
-- ------------------------------------------------------------

SELECT
    customer_id,
    customer_name,
    order_count,
    completed_order_count,
    total_spending,
    projection_version,
    generated_at
FROM customer_order_summary
ORDER BY total_spending DESC;

-- ------------------------------------------------------------
-- 10. READ-OPTIMIZED REPORTING VIEW
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW customer_spending_report AS
SELECT
    customer_id,
    customer_name,
    order_count,
    completed_order_count,
    total_spending,
    CASE
        WHEN order_count = 0 THEN 'NO_ORDERS'
        WHEN completed_order_count = 0 THEN 'NO_COMPLETED_ORDERS'
        WHEN total_spending >= 2000 THEN 'HIGH_VALUE'
        ELSE 'STANDARD'
    END AS customer_segment,
    generated_at
FROM customer_order_summary;

SELECT * FROM customer_spending_report;

-- ------------------------------------------------------------
-- 11. RETRIEVAL AND AGGREGATION
-- ------------------------------------------------------------

SELECT
    customer_segment,
    COUNT(*) AS customer_count,
    SUM(total_spending) AS segment_revenue,
    AVG(total_spending) AS average_spending
FROM customer_spending_report
GROUP BY customer_segment
ORDER BY segment_revenue DESC;

-- ------------------------------------------------------------
-- 12. CONSISTENCY EVALUATION
-- Compares the projection with authoritative normalized data.
-- ------------------------------------------------------------

WITH normalized_values AS (
    SELECT
        c.customer_id,
        c.customer_name,
        COUNT(o.order_id) AS order_count,
        COUNT(o.order_id) FILTER (
            WHERE o.order_status = 'completed'
        ) AS completed_order_count,
        COALESCE(
            SUM(o.order_amount) FILTER (
                WHERE o.order_status = 'completed'
            ),
            0
        ) AS total_spending
    FROM customers c
    LEFT JOIN orders o
        ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT
    n.customer_id,
    n.customer_name AS authoritative_name,
    s.customer_name AS projected_name,
    n.order_count AS authoritative_orders,
    s.order_count AS projected_orders,
    n.total_spending AS authoritative_spending,
    s.total_spending AS projected_spending,
    CASE
        WHEN s.customer_id IS NULL THEN 'MISSING'
        WHEN n.customer_name IS DISTINCT FROM s.customer_name
          OR n.order_count <> s.order_count
          OR n.completed_order_count <> s.completed_order_count
          OR n.total_spending <> s.total_spending
        THEN 'INCONSISTENT'
        ELSE 'CONSISTENT'
    END AS consistency_status
FROM normalized_values n
LEFT JOIN customer_order_summary s
    ON s.customer_id = n.customer_id
ORDER BY n.customer_id;

-- ------------------------------------------------------------
-- 13. TRANSACTIONAL SOURCE WRITE AND REFRESH
-- ------------------------------------------------------------

BEGIN;

INSERT INTO orders (
    customer_id,
    order_amount,
    order_status
)
VALUES (1, 400.00, 'completed');

-- Trigger has automatically invalidated customer 1.
SELECT customer_id, invalidated_at
FROM projection_refresh_queue
WHERE customer_id = 1;

-- Refresh occurs within the same transaction.
SELECT refresh_customer_summary(1);

COMMIT;

-- ------------------------------------------------------------
-- 14. EVENTUAL CONSISTENCY WORKFLOW
-- ------------------------------------------------------------

INSERT INTO orders (
    customer_id,
    order_amount,
    order_status
)
VALUES
    (2, 700.00, 'completed'),
    (3, 200.00, 'pending');

-- These writes invalidate summaries but do not rebuild them.
SELECT
    customer_id,
    invalidated_at,
    retry_count
FROM projection_refresh_queue
ORDER BY invalidated_at;

-- Background worker processes a bounded batch.
CALL refresh_dirty_summaries(50);

-- Verify queue clearance.
SELECT COUNT(*) AS pending_refreshes
FROM projection_refresh_queue;

-- ------------------------------------------------------------
-- 15. FAILURE CASE: INVALID ORDER
-- The statement is expected to fail due to the CHECK constraint.
-- Run independently if testing failures interactively.
-- ------------------------------------------------------------

-- INSERT INTO orders (customer_id, order_amount, order_status)
-- VALUES (1, -100.00, 'completed');

-- ------------------------------------------------------------
-- 16. ELIGIBILITY AND STALENESS REPORT
-- ------------------------------------------------------------

SELECT
    s.customer_id,
    s.customer_name,
    s.projection_version,
    s.generated_at,
    EXTRACT(
        EPOCH FROM (CURRENT_TIMESTAMP - s.generated_at)
    ) AS age_seconds,
    CASE
        WHEN q.customer_id IS NOT NULL THEN 'REFRESH_REQUIRED'
        WHEN s.generated_at <
            CURRENT_TIMESTAMP - INTERVAL '5 minutes'
            THEN 'STALE_BY_AGE'
        ELSE 'ELIGIBLE'
    END AS projection_status
FROM customer_order_summary s
LEFT JOIN projection_refresh_queue q
    ON q.customer_id = s.customer_id
ORDER BY s.customer_id;

-- ------------------------------------------------------------
-- 17. EXPLAIN PERFORMANCE
-- Compare execution plans for both access patterns.
-- ------------------------------------------------------------

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    customer_id,
    COUNT(*),
    SUM(order_amount)
FROM orders
WHERE order_status = 'completed'
GROUP BY customer_id;

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    customer_id,
    order_count,
    completed_order_count,
    total_spending
FROM customer_order_summary
ORDER BY total_spending DESC;

-- ------------------------------------------------------------
-- 18. OPERATIONAL MONITORING
-- ------------------------------------------------------------

SELECT
    operation,
    succeeded,
    COUNT(*) AS operation_count
FROM projection_refresh_log
GROUP BY operation, succeeded
ORDER BY operation, succeeded;

SELECT
    COUNT(*) AS total_customers,
    SUM(order_count) AS total_orders,
    SUM(completed_order_count) AS completed_orders,
    SUM(total_spending) AS total_revenue
FROM customer_order_summary;

SELECT
    customer_id,
    COUNT(*) FILTER (WHERE succeeded) AS successful_refreshes,
    COUNT(*) FILTER (WHERE NOT succeeded) AS failed_refreshes,
    MAX(created_at) AS last_attempt
FROM projection_refresh_log
GROUP BY customer_id
ORDER BY customer_id;

RESET search_path;
