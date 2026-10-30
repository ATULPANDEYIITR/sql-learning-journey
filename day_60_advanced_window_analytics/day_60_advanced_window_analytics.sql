-- Advanced Window Analytics
-- Retail sales model using rolling metrics, moving averages, growth,
-- competition rankings, percentile scores, and weighted product ranking.

DROP SCHEMA IF EXISTS window_analytics CASCADE;

CREATE SCHEMA window_analytics;

SET search_path TO window_analytics, public;

-- ---------------------------------------------------------------------
-- 1. Relational model
-- ---------------------------------------------------------------------

CREATE TABLE stores (
    store_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_code VARCHAR(30) NOT NULL UNIQUE,
    store_name VARCHAR(100) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT stores_code_not_blank
        CHECK (length(trim(store_code)) > 0),

    CONSTRAINT stores_name_not_blank
        CHECK (length(trim(store_name)) > 0)
);

CREATE TABLE products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_code VARCHAR(30) NOT NULL UNIQUE,
    product_name VARCHAR(120) NOT NULL,
    category VARCHAR(60) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT products_code_not_blank
        CHECK (length(trim(product_code)) > 0),

    CONSTRAINT products_name_not_blank
        CHECK (length(trim(product_name)) > 0),

    CONSTRAINT products_category_not_blank
        CHECK (length(trim(category)) > 0)
);

CREATE TABLE sales_events (
    sale_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_ref VARCHAR(60) NOT NULL UNIQUE,
    store_id BIGINT NOT NULL REFERENCES stores(store_id),
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    sale_date DATE NOT NULL,
    units INTEGER NOT NULL,
    revenue NUMERIC(14, 2) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT sales_units_positive
        CHECK (units > 0),

    CONSTRAINT sales_revenue_non_negative
        CHECK (revenue >= 0),

    CONSTRAINT sales_external_ref_not_blank
        CHECK (length(trim(external_ref)) > 0)
);

COMMENT ON TABLE sales_events IS
    'Transaction-level sales facts. Multiple transactions may occur for the same store, product, and date.';

COMMENT ON COLUMN sales_events.revenue IS
    'Non-negative transaction revenue stored with two decimal places.';

-- This index supports the aggregation and date-filtering workload.
CREATE INDEX idx_sales_store_product_date
    ON sales_events (store_id, product_id, sale_date);

CREATE INDEX idx_sales_date_store
    ON sales_events (sale_date, store_id);

-- ---------------------------------------------------------------------
-- 2. Ranking configuration
-- ---------------------------------------------------------------------

CREATE TABLE ranking_policy (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_name VARCHAR(80) NOT NULL UNIQUE,
    window_days INTEGER NOT NULL,
    revenue_weight NUMERIC(6, 5) NOT NULL,
    growth_weight NUMERIC(6, 5) NOT NULL,
    maximum_span_days INTEGER NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT policy_window_positive
        CHECK (window_days > 0),

    CONSTRAINT policy_span_valid
        CHECK (
            maximum_span_days >= 2 * window_days
            AND maximum_span_days <= 3660
        ),

    CONSTRAINT policy_weights_non_negative
        CHECK (revenue_weight >= 0 AND growth_weight >= 0),

    CONSTRAINT policy_weights_sum_to_one
        CHECK (revenue_weight + growth_weight = 1)
);

INSERT INTO ranking_policy (
    policy_name,
    window_days,
    revenue_weight,
    growth_weight,
    maximum_span_days
)
VALUES (
    'Seven-Day Revenue and Growth',
    7,
    0.60000,
    0.40000,
    3660
);

-- ---------------------------------------------------------------------
-- 3. Reproducible reference data
-- ---------------------------------------------------------------------

INSERT INTO stores (store_code, store_name)
VALUES
    ('LKO-01', 'Lucknow Central'),
    ('LKO-02', 'Lucknow East');

INSERT INTO products (product_code, product_name, category)
VALUES
    ('P-A', 'Enterprise Router', 'Networking'),
    ('P-B', 'Secure Storage Unit', 'Storage'),
    ('P-C', 'Monitoring Device', 'Monitoring');

-- Generate 21 calendar days of deterministic transactions.
-- One store-product-date combination is intentionally omitted to test
-- calendar densification and zero-activity handling.
WITH calendar_days AS (
    SELECT
        generated_date::DATE AS sale_date,
        (generated_date::DATE - DATE '2026-10-01')::INTEGER AS day_number
    FROM generate_series(
        DATE '2026-10-01',
        DATE '2026-10-21',
        INTERVAL '1 day'
    ) AS generated_date
),
store_parameters AS (
    SELECT
        store_id,
        store_code,
        CASE store_code
            WHEN 'LKO-01' THEN 0
            ELSE 1
        END AS store_number
    FROM stores
),
product_parameters AS (
    SELECT
        product_id,
        product_code,
        CASE product_code
            WHEN 'P-A' THEN 0
            WHEN 'P-B' THEN 1
            ELSE 2
        END AS product_number
    FROM products
)
INSERT INTO sales_events (
    external_ref,
    store_id,
    product_id,
    sale_date,
    units,
    revenue
)
SELECT
    'EVT-' || sp.store_code || '-' || pp.product_code || '-' ||
        to_char(cd.sale_date, 'YYYYMMDD'),
    sp.store_id,
    pp.product_id,
    cd.sale_date,
    5 + pp.product_number +
        ((cd.day_number + sp.store_number) % 4),
    (
        10000
        + pp.product_number * 1700
        + sp.store_number * 800
        + cd.day_number *
            (pp.product_number * 220 + sp.store_number * 90)
    )::NUMERIC / 100
FROM store_parameters sp
CROSS JOIN product_parameters pp
CROSS JOIN calendar_days cd
WHERE NOT (
    sp.store_code = 'LKO-02'
    AND pp.product_code = 'P-C'
    AND cd.day_number = 5
);

-- Add selected second daily transactions to demonstrate transaction-level
-- aggregation before window calculations.
WITH selected_days AS (
    SELECT
        generated_date::DATE AS sale_date,
        (generated_date::DATE - DATE '2026-10-01')::INTEGER AS day_number
    FROM generate_series(
        DATE '2026-10-01',
        DATE '2026-10-21',
        INTERVAL '1 day'
    ) AS generated_date
    WHERE (
        generated_date::DATE - DATE '2026-10-01'
    )::INTEGER % 5 = 0
),
selected_products AS (
    SELECT
        p.product_id,
        p.product_code,
        s.store_id,
        s.store_code
    FROM products p
    CROSS JOIN stores s
    WHERE p.product_code = 'P-A'
)
INSERT INTO sales_events (
    external_ref,
    store_id,
    product_id,
    sale_date,
    units,
    revenue
)
SELECT
    'EXTRA-' || sp.store_code || '-' || sd.day_number,
    sp.store_id,
    sp.product_id,
    sd.sale_date,
    2,
    (2500 + sd.day_number * 10)::NUMERIC / 100
FROM selected_products sp
CROSS JOIN selected_days sd;

-- ---------------------------------------------------------------------
-- 4. Safe growth calculation
-- ---------------------------------------------------------------------

CREATE OR REPLACE FUNCTION safe_growth_pct(
    p_current NUMERIC,
    p_previous NUMERIC
)
RETURNS NUMERIC
LANGUAGE SQL
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT CASE
        WHEN p_current IS NULL OR p_previous IS NULL OR p_previous <= 0
            THEN NULL
        ELSE (p_current - p_previous) / p_previous
    END;
$$;

COMMENT ON FUNCTION safe_growth_pct(NUMERIC, NUMERIC) IS
    'Returns fractional growth and NULL when the comparison baseline is absent or non-positive.';

-- ---------------------------------------------------------------------
-- 5. Daily aggregation and calendar densification
-- ---------------------------------------------------------------------

CREATE OR REPLACE VIEW daily_window_metrics AS
WITH event_daily AS (
    SELECT
        store_id,
        product_id,
        sale_date,
        SUM(revenue) AS daily_revenue,
        SUM(units)::BIGINT AS daily_units
    FROM sales_events
    GROUP BY store_id, product_id, sale_date
),
series_bounds AS (
    SELECT
        store_id,
        product_id,
        MIN(sale_date) AS first_day,
        MAX(sale_date) AS last_day
    FROM event_daily
    GROUP BY store_id, product_id
),
dense_daily AS (
    SELECT
        sb.store_id,
        sb.product_id,
        calendar.sale_date::DATE AS sale_date,
        COALESCE(ed.daily_revenue, 0::NUMERIC) AS daily_revenue,
        COALESCE(ed.daily_units, 0::BIGINT) AS daily_units
    FROM series_bounds sb
    CROSS JOIN LATERAL generate_series(
        sb.first_day,
        sb.last_day,
        INTERVAL '1 day'
    ) AS calendar(sale_date)
    LEFT JOIN event_daily ed
        ON ed.store_id = sb.store_id
        AND ed.product_id = sb.product_id
        AND ed.sale_date = calendar.sale_date
),
rolling AS (
    SELECT
        dd.*,

        -- Seven calendar observations, including the current date.
        SUM(daily_revenue) OVER (
            PARTITION BY store_id, product_id
            ORDER BY sale_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7d_revenue,

        SUM(daily_units) OVER (
            PARTITION BY store_id, product_id
            ORDER BY sale_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7d_units,

        AVG(daily_revenue) OVER (
            PARTITION BY store_id, product_id
            ORDER BY sale_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS moving_average_revenue_7d,

        -- The previous seven calendar observations do not overlap the
        -- current trailing seven-day window.
        SUM(daily_revenue) OVER (
            PARTITION BY store_id, product_id
            ORDER BY sale_date
            ROWS BETWEEN 13 PRECEDING AND 7 PRECEDING
        ) AS previous_7d_revenue,

        COUNT(*) OVER (
            PARTITION BY store_id, product_id
            ORDER BY sale_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS current_window_days,

        COUNT(*) OVER (
            PARTITION BY store_id, product_id
            ORDER BY sale_date
            ROWS BETWEEN 13 PRECEDING AND 7 PRECEDING
        ) AS previous_window_days,

        LAG(daily_revenue) OVER (
            PARTITION BY store_id, product_id
            ORDER BY sale_date
        ) AS previous_day_revenue,

        SUM(daily_revenue) OVER (
            PARTITION BY store_id, product_id
            ORDER BY sale_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_revenue,

        ROW_NUMBER() OVER (
            PARTITION BY store_id, product_id
            ORDER BY sale_date
        ) AS history_day_number

    FROM dense_daily dd
),
growth AS (
    SELECT
        r.*,

        safe_growth_pct(
            rolling_7d_revenue,
            previous_7d_revenue
        ) AS growth_pct,

        (
            current_window_days = 7
            AND previous_window_days = 7
            AND previous_7d_revenue > 0
        ) AS ranking_eligible

    FROM rolling r
),
revenue_ranked AS (
    SELECT
        g.*,

        RANK() OVER (
            PARTITION BY store_id, sale_date
            ORDER BY rolling_7d_revenue DESC
        ) AS revenue_rank,

        DENSE_RANK() OVER (
            PARTITION BY store_id, sale_date
            ORDER BY rolling_7d_revenue DESC
        ) AS revenue_dense_rank,

        ROW_NUMBER() OVER (
            PARTITION BY store_id, sale_date
            ORDER BY rolling_7d_revenue DESC, product_id
        ) AS revenue_row_number

    FROM growth g
),
eligible_scores AS (
    -- Non-eligible rows do not dilute the ranking population.
    SELECT
        store_id,
        product_id,
        sale_date,

        RANK() OVER (
            PARTITION BY store_id, sale_date
            ORDER BY growth_pct DESC
        ) AS growth_rank,

        1 - PERCENT_RANK() OVER (
            PARTITION BY store_id, sale_date
            ORDER BY rolling_7d_revenue DESC
        ) AS revenue_rank_score,

        1 - PERCENT_RANK() OVER (
            PARTITION BY store_id, sale_date
            ORDER BY growth_pct DESC
        ) AS growth_rank_score

    FROM revenue_ranked
    WHERE ranking_eligible
),
composite_scores AS (
    SELECT
        es.store_id,
        es.product_id,
        es.sale_date,
        es.growth_rank,
        es.revenue_rank_score,
        es.growth_rank_score,

        (
            es.revenue_rank_score * rp.revenue_weight
            + es.growth_rank_score * rp.growth_weight
        ) AS composite_score

    FROM eligible_scores es
    CROSS JOIN ranking_policy rp
    WHERE rp.active
),
composite_ranked AS (
    SELECT
        cs.*,

        RANK() OVER (
            PARTITION BY store_id, sale_date
            ORDER BY composite_score DESC
        ) AS composite_rank

    FROM composite_scores cs
)
SELECT
    rr.store_id,
    s.store_code,
    rr.product_id,
    p.product_code,
    p.product_name,
    p.category,
    rr.sale_date,

    rr.daily_revenue,
    rr.daily_units,

    rr.rolling_7d_revenue,
    rr.rolling_7d_units,
    rr.moving_average_revenue_7d,

    rr.previous_7d_revenue,
    rr.growth_pct,
    rr.previous_day_revenue,
    rr.cumulative_revenue,

    rr.current_window_days,
    rr.previous_window_days,
    rr.history_day_number,

    rr.revenue_rank,
    rr.revenue_dense_rank,
    rr.revenue_row_number,

    rr.ranking_eligible,

    cr.growth_rank,
    cr.revenue_rank_score,
    cr.growth_rank_score,
    cr.composite_score,
    cr.composite_rank

FROM revenue_ranked rr
JOIN stores s
    ON s.store_id = rr.store_id
JOIN products p
    ON p.product_id = rr.product_id
LEFT JOIN composite_ranked cr
    ON cr.store_id = rr.store_id
    AND cr.product_id = rr.product_id
    AND cr.sale_date = rr.sale_date;

COMMENT ON VIEW daily_window_metrics IS
    'Densified daily metrics, trailing windows, period growth, rankings, and eligible weighted scores.';

-- ---------------------------------------------------------------------
-- 6. Reporting view
-- ---------------------------------------------------------------------

CREATE OR REPLACE VIEW store_daily_report AS
SELECT
    store_id,
    store_code,
    sale_date,

    SUM(daily_revenue) AS total_daily_revenue,
    SUM(daily_units) AS total_daily_units,

    SUM(rolling_7d_revenue) AS combined_product_rolling_revenue_7d,
    SUM(rolling_7d_units) AS combined_product_rolling_units_7d,

    COUNT(*) AS product_count,
    COUNT(*) FILTER (WHERE ranking_eligible) AS eligible_product_count,

    AVG(composite_score) FILTER (
        WHERE composite_score IS NOT NULL
    ) AS average_composite_score

FROM daily_window_metrics
GROUP BY store_id, store_code, sale_date;

-- ---------------------------------------------------------------------
-- 7. Database integrity and failure-case demonstration
-- ---------------------------------------------------------------------

-- The first insert is valid, but the second violates sales_units_positive.
-- The PL/pgSQL exception block acts as a subtransaction, so the valid first
-- insert is also rolled back when the batch fails.
DO $$
DECLARE
    test_store_id BIGINT;
    test_product_id BIGINT;
BEGIN
    SELECT store_id
    INTO test_store_id
    FROM stores
    WHERE store_code = 'LKO-01';

    SELECT product_id
    INTO test_product_id
    FROM products
    WHERE product_code = 'P-A';

    BEGIN
        INSERT INTO sales_events (
            external_ref,
            store_id,
            product_id,
            sale_date,
            units,
            revenue
        )
        VALUES (
            'ROLLBACK-TEST-VALID',
            test_store_id,
            test_product_id,
            DATE '2026-10-21',
            1,
            10.00
        );

        INSERT INTO sales_events (
            external_ref,
            store_id,
            product_id,
            sale_date,
            units,
            revenue
        )
        VALUES (
            'ROLLBACK-TEST-INVALID',
            test_store_id,
            test_product_id,
            DATE '2026-10-21',
            0,
            10.00
        );

        RAISE EXCEPTION
            'The invalid batch unexpectedly passed validation.';

    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE
                'Invalid batch rejected. The preceding insert was rolled back.';
    END;
END;
$$;

-- ---------------------------------------------------------------------
-- 8. Retrieval: detailed daily metrics and latest rolling windows
-- ---------------------------------------------------------------------

SELECT
    store_code,
    product_code,
    sale_date,
    daily_revenue,
    rolling_7d_revenue,
    moving_average_revenue_7d,
    previous_7d_revenue,
    growth_pct
FROM daily_window_metrics
WHERE store_code = 'LKO-01'
ORDER BY product_code, sale_date;

-- Latest reporting date across the dataset.
WITH latest_date AS (
    SELECT MAX(sale_date) AS sale_date
    FROM daily_window_metrics
)
SELECT
    m.store_code,
    m.product_code,
    m.rolling_7d_revenue,
    m.moving_average_revenue_7d,
    m.growth_pct,
    m.revenue_rank,
    m.growth_rank,
    m.composite_score,
    m.composite_rank
FROM daily_window_metrics m
JOIN latest_date d
    ON d.sale_date = m.sale_date
ORDER BY
    m.store_code,
    m.composite_rank NULLS LAST,
    m.product_code;

-- ---------------------------------------------------------------------
-- 9. Validation: zero-activity dates and complete windows
-- ---------------------------------------------------------------------

SELECT
    store_code,
    product_code,
    sale_date,
    daily_revenue,
    daily_units,
    current_window_days,
    previous_window_days,
    ranking_eligible
FROM daily_window_metrics
WHERE daily_revenue = 0
ORDER BY store_code, product_code, sale_date;

-- Check that growth is absent before a complete comparison is available.
SELECT
    store_code,
    product_code,
    sale_date,
    history_day_number,
    previous_7d_revenue,
    growth_pct,
    ranking_eligible
FROM daily_window_metrics
WHERE history_day_number < 14
ORDER BY store_code, product_code, sale_date;

-- ---------------------------------------------------------------------
-- 10. Aggregation: store-level daily reporting
-- ---------------------------------------------------------------------

SELECT
    store_code,
    sale_date,
    total_daily_revenue,
    total_daily_units,
    combined_product_rolling_revenue_7d,
    product_count,
    eligible_product_count,
    average_composite_score
FROM store_daily_report
ORDER BY store_code, sale_date;

-- ---------------------------------------------------------------------
-- 11. Evaluation: compare rankings and ranking populations
-- ---------------------------------------------------------------------

WITH latest_date AS (
    SELECT MAX(sale_date) AS sale_date
    FROM daily_window_metrics
)
SELECT
    store_code,
    product_code,
    ROUND(rolling_7d_revenue, 2) AS rolling_revenue,
    ROUND(growth_pct * 100, 2) AS growth_percentage,
    revenue_rank,
    revenue_dense_rank,
    growth_rank,
    ROUND(revenue_rank_score, 4) AS revenue_score,
    ROUND(growth_rank_score, 4) AS growth_score,
    ROUND(composite_score, 4) AS composite_score,
    composite_rank
FROM daily_window_metrics
WHERE sale_date = (SELECT sale_date FROM latest_date)
  AND ranking_eligible
ORDER BY store_code, composite_rank, product_code;

-- ---------------------------------------------------------------------
-- 12. Reporting: strongest combined performance by store
-- ---------------------------------------------------------------------

WITH latest_date AS (
    SELECT MAX(sale_date) AS sale_date
    FROM daily_window_metrics
),
ranked_products AS (
    SELECT
        store_code,
        product_code,
        composite_score,
        composite_rank,
        rolling_7d_revenue,
        growth_pct,

        COUNT(*) OVER (
            PARTITION BY store_code
        ) AS eligible_population_size

    FROM daily_window_metrics
    WHERE sale_date = (SELECT sale_date FROM latest_date)
      AND ranking_eligible
)
SELECT
    store_code,
    product_code,
    eligible_population_size,
    ROUND(rolling_7d_revenue, 2) AS rolling_revenue,
    ROUND(growth_pct * 100, 2) AS growth_percentage,
    ROUND(composite_score, 4) AS composite_score,
    composite_rank
FROM ranked_products
ORDER BY store_code, composite_rank, product_code;

-- ---------------------------------------------------------------------
-- 13. Eligibility decisions
-- ---------------------------------------------------------------------

SELECT
    store_code,
    sale_date,

    COUNT(*) AS total_products,

    COUNT(*) FILTER (
        WHERE ranking_eligible
    ) AS eligible_products,

    COUNT(*) FILTER (
        WHERE NOT ranking_eligible
    ) AS ineligible_products,

    CASE
        WHEN COUNT(*) FILTER (WHERE ranking_eligible) > 0
            THEN 'LEADERBOARD_AVAILABLE'
        ELSE 'INSUFFICIENT_HISTORY'
    END AS leaderboard_status

FROM daily_window_metrics
GROUP BY store_code, sale_date
ORDER BY store_code, sale_date DESC;

-- Product-level explanation for ranking eligibility.
SELECT
    store_code,
    product_code,
    sale_date,
    current_window_days,
    previous_window_days,
    previous_7d_revenue,
    ranking_eligible,

    CASE
        WHEN current_window_days < 7
            THEN 'INCOMPLETE_CURRENT_WINDOW'
        WHEN previous_window_days < 7
            THEN 'INCOMPLETE_PREVIOUS_WINDOW'
        WHEN previous_7d_revenue <= 0
            THEN 'NON_POSITIVE_GROWTH_BASELINE'
        ELSE 'ELIGIBLE'
    END AS eligibility_reason

FROM daily_window_metrics
ORDER BY store_code, product_code, sale_date;

-- ---------------------------------------------------------------------
-- 14. Additional query: revenue and growth ranking disagreement
-- ---------------------------------------------------------------------

WITH latest_date AS (
    SELECT MAX(sale_date) AS sale_date
    FROM daily_window_metrics
)
SELECT
    store_code,
    product_code,
    revenue_rank,
    growth_rank,
    composite_rank,
    ABS(revenue_rank - growth_rank) AS ranking_disagreement
FROM daily_window_metrics
WHERE sale_date = (SELECT sale_date FROM latest_date)
  AND ranking_eligible
ORDER BY
    ranking_disagreement DESC,
    store_code,
    product_code;

-- ---------------------------------------------------------------------
-- 15. Additional query: historical top-ranked product by store
-- ---------------------------------------------------------------------

SELECT
    store_code,
    sale_date,
    product_code,
    composite_score,
    composite_rank
FROM daily_window_metrics
WHERE composite_rank = 1
ORDER BY store_code, sale_date;
