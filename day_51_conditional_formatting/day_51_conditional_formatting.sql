DROP SCHEMA IF EXISTS conditional_aggregation_demo CASCADE;
CREATE SCHEMA conditional_aggregation_demo;
SET search_path TO conditional_aggregation_demo;

-- The model separates raw transactional facts from conditional KPI rules.
CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL,
    region TEXT NOT NULL CHECK (btrim(region) <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    order_date DATE NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('completed', 'cancelled', 'pending')
    ),
    channel TEXT NOT NULL CHECK (
        channel IN ('web', 'mobile', 'store')
    ),
    amount NUMERIC(14, 2) NOT NULL CHECK (amount >= 0),
    returned BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (
        NOT returned OR status = 'completed'
    )
);

CREATE TABLE kpi_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    policy_name TEXT NOT NULL UNIQUE,
    minimum_completion_rate NUMERIC(5, 2) NOT NULL CHECK (
        minimum_completion_rate BETWEEN 0 AND 100
    ),
    minimum_completed_orders INTEGER NOT NULL CHECK (
        minimum_completed_orders >= 0
    )
);

CREATE TABLE kpi_evaluations (
    evaluation_id BIGSERIAL PRIMARY KEY,
    policy_id BIGINT NOT NULL REFERENCES kpi_policies(policy_id),
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_orders BIGINT NOT NULL CHECK (total_orders >= 0),
    completed_orders BIGINT NOT NULL CHECK (completed_orders >= 0),
    cancelled_orders BIGINT NOT NULL CHECK (cancelled_orders >= 0),
    completed_revenue NUMERIC(14, 2) NOT NULL CHECK (
        completed_revenue >= 0
    ),
    completion_rate NUMERIC(7, 2) NOT NULL CHECK (
        completion_rate BETWEEN 0 AND 100
    ),
    policy_passed BOOLEAN NOT NULL
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date_status ON orders(order_date, status);
CREATE INDEX idx_orders_region_status ON customers(region, customer_id);

INSERT INTO customers (customer_name, region) VALUES
    ('North Retail Ltd', 'North'),
    ('North Systems Ltd', 'North'),
    ('South Manufacturing Ltd', 'South'),
    ('South Digital Ltd', 'South'),
    ('East Trading Ltd', 'East'),
    ('East Services Ltd', 'East'),
    ('West Logistics Ltd', 'West'),
    ('West Technology Ltd', 'West'),
    ('North Analytics Ltd', 'North'),
    ('South Infrastructure Ltd', 'South');

INSERT INTO orders (
    customer_id,
    order_date,
    status,
    channel,
    amount,
    returned
) VALUES
    (1, '2026-10-01', 'completed', 'web',    1250.00, FALSE),
    (2, '2026-10-01', 'cancelled', 'mobile', 800.00, FALSE),
    (3, '2026-10-02', 'completed', 'mobile', 2100.00, FALSE),
    (4, '2026-10-03', 'completed', 'web',    1750.00, TRUE),
    (5, '2026-10-04', 'pending',   'web',     900.00, FALSE),
    (6, '2026-10-05', 'completed', 'store',  3200.00, FALSE),
    (7, '2026-10-05', 'cancelled', 'web',     600.00, FALSE),
    (8, '2026-10-06', 'completed', 'mobile', 1450.00, FALSE),
    (9, '2026-10-07', 'completed', 'web',    2800.00, FALSE),
    (10, '2026-10-08', 'pending',  'mobile', 1100.00, FALSE);

INSERT INTO kpi_policies (
    policy_name,
    minimum_completion_rate,
    minimum_completed_orders
) VALUES
    ('Monthly Sales Health', 50.00, 5),
    ('Strict Sales Health', 70.00, 7);

-- SUM(CASE ...) demonstrates portable conditional aggregation.
CREATE OR REPLACE VIEW order_kpi_report AS
SELECT
    COUNT(*) AS total_orders,

    COUNT(CASE WHEN o.status = 'completed' THEN 1 END)
        AS completed_orders,

    COUNT(CASE WHEN o.status = 'cancelled' THEN 1 END)
        AS cancelled_orders,

    COUNT(CASE WHEN o.status = 'pending' THEN 1 END)
        AS pending_orders,

    SUM(
        CASE
            WHEN o.status = 'completed' THEN o.amount
            ELSE 0
        END
    )::NUMERIC(14, 2) AS completed_revenue,

    SUM(
        CASE
            WHEN o.status = 'cancelled' THEN o.amount
            ELSE 0
        END
    )::NUMERIC(14, 2) AS cancelled_value,

    SUM(
        CASE
            WHEN o.status = 'completed'
                 AND o.channel = 'web'
            THEN o.amount
            ELSE 0
        END
    )::NUMERIC(14, 2) AS web_completed_revenue,

    SUM(
        CASE
            WHEN o.status = 'completed'
                 AND o.channel = 'mobile'
            THEN o.amount
            ELSE 0
        END
    )::NUMERIC(14, 2) AS mobile_completed_revenue,

    COUNT(
        CASE
            WHEN o.status = 'completed'
                 AND o.returned
            THEN 1
        END
    ) AS returned_completed_orders,

    ROUND(
        100.0 * COUNT(
            CASE WHEN o.status = 'completed' THEN 1 END
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate,

    ROUND(
        100.0 * COUNT(
            CASE WHEN o.status = 'cancelled' THEN 1 END
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate

FROM orders AS o;

-- PostgreSQL FILTER expresses conditional aggregates directly.
CREATE OR REPLACE VIEW channel_kpi_report AS
SELECT
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_orders,
    COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_orders,
    COUNT(*) FILTER (WHERE status = 'pending') AS pending_orders,
    SUM(amount) FILTER (
        WHERE status = 'completed'
    )::NUMERIC(14, 2) AS completed_revenue,
    SUM(amount) FILTER (
        WHERE status = 'completed'
          AND channel = 'web'
    )::NUMERIC(14, 2) AS web_revenue,
    SUM(amount) FILTER (
        WHERE status = 'completed'
          AND channel = 'mobile'
    )::NUMERIC(14, 2) AS mobile_revenue,
    SUM(amount) FILTER (
        WHERE status = 'completed'
          AND channel = 'store'
    )::NUMERIC(14, 2) AS store_revenue,
    COUNT(*) FILTER (
        WHERE status = 'completed' AND returned
    ) AS returned_completed_orders
FROM orders;

-- Conditional aggregation after GROUP BY produces one KPI row per region.
CREATE OR REPLACE VIEW regional_kpi_report AS
SELECT
    c.region,

    COUNT(o.order_id) AS total_orders,

    COUNT(o.order_id) FILTER (
        WHERE o.status = 'completed'
    ) AS completed_orders,

    COUNT(o.order_id) FILTER (
        WHERE o.status = 'cancelled'
    ) AS cancelled_orders,

    COUNT(o.order_id) FILTER (
        WHERE o.status = 'pending'
    ) AS pending_orders,

    COALESCE(
        SUM(o.amount) FILTER (
            WHERE o.status = 'completed'
        ),
        0
    )::NUMERIC(14, 2) AS completed_revenue,

    COALESCE(
        SUM(o.amount) FILTER (
            WHERE o.status = 'completed'
              AND o.channel = 'web'
        ),
        0
    )::NUMERIC(14, 2) AS web_revenue,

    COUNT(o.order_id) FILTER (
        WHERE o.status = 'completed'
          AND o.returned
    ) AS returned_completed_orders,

    ROUND(
        100.0 * COUNT(o.order_id) FILTER (
            WHERE o.status = 'completed'
        ) / NULLIF(COUNT(o.order_id), 0),
        2
    ) AS completion_rate

FROM customers AS c
LEFT JOIN orders AS o
    ON o.customer_id = c.customer_id
GROUP BY c.region;

-- A CTE makes KPI calculation and policy evaluation separate operations.
WITH kpis AS (
    SELECT
        COUNT(*) AS total_orders,
        COUNT(*) FILTER (WHERE status = 'completed')
            AS completed_orders,
        COUNT(*) FILTER (WHERE status = 'cancelled')
            AS cancelled_orders,
        SUM(amount) FILTER (WHERE status = 'completed')
            AS completed_revenue
    FROM orders
),
rates AS (
    SELECT
        *,
        ROUND(
            100.0 * completed_orders
            / NULLIF(total_orders, 0),
            2
        ) AS completion_rate
    FROM kpis
)
SELECT
    r.total_orders,
    r.completed_orders,
    r.cancelled_orders,
    r.completed_revenue,
    r.completion_rate,
    p.policy_name,
    (
        r.completed_orders >= p.minimum_completed_orders
        AND r.completion_rate >= p.minimum_completion_rate
    ) AS policy_passed
FROM rates AS r
CROSS JOIN kpi_policies AS p
ORDER BY p.policy_id;

-- Customer-level KPIs illustrate multiple conditional metrics in one row.
SELECT
    c.customer_id,
    c.customer_name,
    c.region,

    COUNT(o.order_id) AS total_orders,

    COUNT(o.order_id) FILTER (
        WHERE o.status = 'completed'
    ) AS completed_orders,

    SUM(o.amount) FILTER (
        WHERE o.status = 'completed'
    )::NUMERIC(14, 2) AS completed_revenue,

    COUNT(o.order_id) FILTER (
        WHERE o.status = 'cancelled'
    ) AS cancelled_orders,

    COUNT(o.order_id) FILTER (
        WHERE o.status = 'completed'
          AND o.returned
    ) AS returned_completed_orders

FROM customers AS c
LEFT JOIN orders AS o
    ON o.customer_id = c.customer_id
GROUP BY
    c.customer_id,
    c.customer_name,
    c.region
ORDER BY completed_revenue DESC NULLS LAST;

-- Validate that mutually exclusive status metrics partition every order.
SELECT
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE status = 'completed')
        + COUNT(*) FILTER (WHERE status = 'cancelled')
        + COUNT(*) FILTER (WHERE status = 'pending')
        AS status_partition_count,
    (
        COUNT(*)
        =
        COUNT(*) FILTER (WHERE status = 'completed')
        + COUNT(*) FILTER (WHERE status = 'cancelled')
        + COUNT(*) FILTER (WHERE status = 'pending')
    ) AS partition_is_valid
FROM orders;

-- Demonstrate a conditional aggregate with no matching rows.
SELECT
    COALESCE(
        SUM(amount) FILTER (
            WHERE status = 'completed'
              AND amount > 1000000
        ),
        0
    )::NUMERIC(14, 2) AS no_match_revenue
FROM orders;

-- A transaction protects an evaluation and its KPI snapshot as one unit.
BEGIN;

WITH kpis AS (
    SELECT
        COUNT(*) AS total_orders,
        COUNT(*) FILTER (WHERE status = 'completed')
            AS completed_orders,
        COUNT(*) FILTER (WHERE status = 'cancelled')
            AS cancelled_orders,
        COALESCE(
            SUM(amount) FILTER (WHERE status = 'completed'),
            0
        )::NUMERIC(14, 2) AS completed_revenue
    FROM orders
),
calculated AS (
    SELECT
        k.*,
        ROUND(
            100.0 * completed_orders
            / NULLIF(total_orders, 0),
            2
        ) AS completion_rate
    FROM kpis AS k
)
INSERT INTO kpi_evaluations (
    policy_id,
    total_orders,
    completed_orders,
    cancelled_orders,
    completed_revenue,
    completion_rate,
    policy_passed
)
SELECT
    p.policy_id,
    c.total_orders,
    c.completed_orders,
    c.cancelled_orders,
    c.completed_revenue,
    c.completion_rate,
    (
        c.completed_orders >= p.minimum_completed_orders
        AND c.completion_rate >= p.minimum_completion_rate
    )
FROM calculated AS c
CROSS JOIN kpi_policies AS p
WHERE p.policy_name = 'Monthly Sales Health';

COMMIT;

-- Reporting the stored KPI evaluation avoids recalculating historical values.
SELECT
    e.evaluation_id,
    p.policy_name,
    e.evaluated_at,
    e.total_orders,
    e.completed_orders,
    e.cancelled_orders,
    e.completed_revenue,
    e.completion_rate,
    e.policy_passed
FROM kpi_evaluations AS e
JOIN kpi_policies AS p
    ON p.policy_id = e.policy_id
ORDER BY e.evaluation_id;
