DROP SCHEMA IF EXISTS window_value_demo CASCADE;
CREATE SCHEMA window_value_demo;

SET search_path TO window_value_demo;

-- Observations are deliberately ordered by event time so that
-- FIRST_VALUE and LAST_VALUE have deterministic semantics.
CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE observations (
    observation_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    observed_at TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value BIGINT NOT NULL CHECK (metric_value >= 0),
    UNIQUE (repository_id, observed_at, metric_name)
);

CREATE INDEX idx_observations_repository_time
    ON observations (repository_id, observed_at);

INSERT INTO repositories (repository_name)
VALUES
    ('payment-api'),
    ('search-api'),
    ('catalog-api');

INSERT INTO observations (
    repository_id,
    observed_at,
    metric_name,
    metric_value
)
SELECT r.repository_id, v.observed_at, 'deployments', v.metric_value
FROM repositories r
JOIN (
    VALUES
        ('payment-api', TIMESTAMPTZ '2026-10-01 09:00:00+00', 4::BIGINT),
        ('payment-api', TIMESTAMPTZ '2026-10-01 11:00:00+00', 7::BIGINT),
        ('payment-api', TIMESTAMPTZ '2026-10-01 13:00:00+00', 11::BIGINT),
        ('search-api', TIMESTAMPTZ '2026-10-01 09:00:00+00', 3::BIGINT),
        ('search-api', TIMESTAMPTZ '2026-10-01 11:00:00+00', 6::BIGINT),
        ('search-api', TIMESTAMPTZ '2026-10-01 13:00:00+00', 5::BIGINT),
        ('catalog-api', TIMESTAMPTZ '2026-10-01 09:00:00+00', 2::BIGINT),
        ('catalog-api', TIMESTAMPTZ '2026-10-01 11:00:00+00', 8::BIGINT),
        ('catalog-api', TIMESTAMPTZ '2026-10-01 13:00:00+00', 9::BIGINT)
) AS v(repository_name, observed_at, metric_value)
    ON r.repository_name = v.repository_name;

-- FIRST_VALUE is anchored to the first row of the ordered partition.
SELECT
    r.repository_name,
    o.observed_at,
    o.metric_value,
    FIRST_VALUE(o.metric_value) OVER (
        PARTITION BY o.repository_id
        ORDER BY o.observed_at
    ) AS first_observation
FROM observations o
JOIN repositories r
    ON r.repository_id = o.repository_id
WHERE o.metric_name = 'deployments'
ORDER BY r.repository_name, o.observed_at;

-- With the normal ordered frame, LAST_VALUE ends at CURRENT ROW.
-- It therefore returns the current row, not the final partition row.
SELECT
    r.repository_name,
    o.observed_at,
    o.metric_value,
    LAST_VALUE(o.metric_value) OVER (
        PARTITION BY o.repository_id
        ORDER BY o.observed_at
    ) AS last_value_default_frame
FROM observations o
JOIN repositories r
    ON r.repository_id = o.repository_id
WHERE o.metric_name = 'deployments'
ORDER BY r.repository_name, o.observed_at;

-- To obtain the final observation for every row, explicitly extend
-- the frame through UNBOUNDED FOLLOWING.
SELECT
    r.repository_name,
    o.observed_at,
    o.metric_value,
    LAST_VALUE(o.metric_value) OVER (
        PARTITION BY o.repository_id
        ORDER BY o.observed_at
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS final_observation
FROM observations o
JOIN repositories r
    ON r.repository_id = o.repository_id
WHERE o.metric_name = 'deployments'
ORDER BY r.repository_name, o.observed_at;

-- A bounded ROWS frame expresses "last value in the current two-row history".
SELECT
    r.repository_name,
    o.observed_at,
    o.metric_value,
    LAST_VALUE(o.metric_value) OVER (
        PARTITION BY o.repository_id
        ORDER BY o.observed_at
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS last_value_in_two_preceding_frame
FROM observations o
JOIN repositories r
    ON r.repository_id = o.repository_id
WHERE o.metric_name = 'deployments'
ORDER BY r.repository_name, o.observed_at;

-- FIRST_VALUE and full-partition LAST_VALUE can be combined to
-- identify the change between the first and final observation.
WITH windowed AS (
    SELECT
        o.repository_id,
        o.observed_at,
        o.metric_value,
        FIRST_VALUE(o.metric_value) OVER (
            PARTITION BY o.repository_id
            ORDER BY o.observed_at
        ) AS first_value,
        LAST_VALUE(o.metric_value) OVER (
            PARTITION BY o.repository_id
            ORDER BY o.observed_at
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS final_value
    FROM observations o
    WHERE o.metric_name = 'deployments'
)
SELECT
    r.repository_name,
    MAX(first_value) AS first_value,
    MAX(final_value) AS final_value,
    MAX(final_value) - MAX(first_value) AS change
FROM windowed w
JOIN repositories r
    ON r.repository_id = w.repository_id
GROUP BY r.repository_name
ORDER BY r.repository_name;

-- A validation query checks whether the final observation is greater
-- than or equal to the first observation.
WITH windowed AS (
    SELECT
        repository_id,
        FIRST_VALUE(metric_value) OVER (
            PARTITION BY repository_id
            ORDER BY observed_at
        ) AS first_value,
        LAST_VALUE(metric_value) OVER (
            PARTITION BY repository_id
            ORDER BY observed_at
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS final_value
    FROM observations
    WHERE metric_name = 'deployments'
)
SELECT DISTINCT
    r.repository_name,
    first_value,
    final_value,
    CASE
        WHEN final_value >= first_value THEN 'NON_DECREASING'
        ELSE 'DECREASING'
    END AS trend_classification
FROM windowed w
JOIN repositories r
    ON r.repository_id = w.repository_id
ORDER BY r.repository_name;

-- Demonstrate transactional insertion and rollback. The failed
-- negative metric violates the CHECK constraint and the transaction
-- remains atomic.
BEGIN;

INSERT INTO observations (
    repository_id,
    observed_at,
    metric_name,
    metric_value
)
SELECT repository_id,
       TIMESTAMPTZ '2026-10-01 15:00:00+00',
       'deployments',
       12
FROM repositories
WHERE repository_name = 'payment-api';

COMMIT;

-- The following transaction is intentionally rolled back after the
-- invalid value is detected before it can become durable.
BEGIN;

DO $$
BEGIN
    IF -1 < 0 THEN
        RAISE EXCEPTION 'Rejected negative metric value';
    END IF;
END;
$$;

ROLLBACK;

-- A view exposes the semantically useful first and final observations.
CREATE OR REPLACE VIEW repository_observation_extremes AS
WITH windowed AS (
    SELECT
        o.repository_id,
        o.observed_at,
        o.metric_name,
        o.metric_value,
        FIRST_VALUE(o.metric_value) OVER (
            PARTITION BY o.repository_id, o.metric_name
            ORDER BY o.observed_at
        ) AS first_value,
        LAST_VALUE(o.metric_value) OVER (
            PARTITION BY o.repository_id, o.metric_name
            ORDER BY o.observed_at
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS last_value
    FROM observations o
)
SELECT DISTINCT
    r.repository_name,
    w.metric_name,
    w.first_value,
    w.last_value
FROM windowed w
JOIN repositories r
    ON r.repository_id = w.repository_id;

SELECT *
FROM repository_observation_extremes
ORDER BY repository_name, metric_name;
