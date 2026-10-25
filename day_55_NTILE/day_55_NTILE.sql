DROP SCHEMA IF EXISTS ntile_demo CASCADE;
CREATE SCHEMA ntile_demo;

SET search_path = ntile_demo;

-- The data model deliberately separates the observation from its
-- segmentation result. The score is the ordering input; the bucket
-- is derived analytically and should not be treated as source data.

CREATE TABLE customers (
    customer_id      BIGSERIAL PRIMARY KEY,
    customer_name    TEXT NOT NULL,
    segment_source   TEXT NOT NULL DEFAULT 'customer_score',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT customers_name_chk
        CHECK (btrim(customer_name) <> '')
);

CREATE TABLE customer_scores (
    score_id         BIGSERIAL PRIMARY KEY,
    customer_id      BIGINT NOT NULL
        REFERENCES customers(customer_id)
        ON DELETE CASCADE,
    score_date       DATE NOT NULL,
    score            NUMERIC(10, 2) NOT NULL,
    score_status     TEXT NOT NULL DEFAULT 'valid',
    CONSTRAINT customer_scores_score_chk
        CHECK (score >= 0 AND score <= 100),
    CONSTRAINT customer_scores_status_chk
        CHECK (score_status IN ('valid', 'invalid', 'superseded')),
    CONSTRAINT customer_scores_unique_date
        UNIQUE (customer_id, score_date)
);

CREATE INDEX customer_scores_date_score_idx
    ON customer_scores (score_date, score DESC, customer_id);

CREATE TABLE ntile_runs (
    run_id           BIGSERIAL PRIMARY KEY,
    run_name         TEXT NOT NULL UNIQUE,
    bucket_count     INTEGER NOT NULL,
    score_date       DATE NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ntile_runs_bucket_count_chk
        CHECK (bucket_count > 0)
);

CREATE TABLE score_buckets (
    run_id           BIGINT NOT NULL
        REFERENCES ntile_runs(run_id)
        ON DELETE CASCADE,
    customer_id      BIGINT NOT NULL
        REFERENCES customers(customer_id)
        ON DELETE CASCADE,
    score_id         BIGINT NOT NULL
        REFERENCES customer_scores(score_id)
        ON DELETE CASCADE,
    bucket_number    INTEGER NOT NULL,
    bucket_count     INTEGER NOT NULL,
    PRIMARY KEY (run_id, customer_id),
    CONSTRAINT score_buckets_number_chk
        CHECK (
            bucket_number >= 1
            AND bucket_number <= bucket_count
        ),
    CONSTRAINT score_buckets_count_chk
        CHECK (bucket_count > 0)
);

CREATE INDEX score_buckets_bucket_idx
    ON score_buckets (run_id, bucket_number);

CREATE OR REPLACE FUNCTION prevent_invalid_bucket_result()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.bucket_number < 1
       OR NEW.bucket_number > NEW.bucket_count THEN
        RAISE EXCEPTION
            'bucket_number % is invalid for bucket_count %',
            NEW.bucket_number,
            NEW.bucket_count;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER score_buckets_validation_trg
BEFORE INSERT OR UPDATE ON score_buckets
FOR EACH ROW
EXECUTE FUNCTION prevent_invalid_bucket_result();

INSERT INTO customers (customer_name) VALUES
    ('Asha'),
    ('Bharat'),
    ('Chirag'),
    ('Divya'),
    ('Esha'),
    ('Farhan'),
    ('Gita'),
    ('Harsh'),
    ('Isha'),
    ('Jay'),
    ('Kiran'),
    ('Lalit');

INSERT INTO customer_scores
    (customer_id, score_date, score)
SELECT
    customer_id,
    DATE '2026-10-25',
    score
FROM (
    VALUES
        (1, 96.00),
        (2, 82.00),
        (3, 91.00),
        (4, 74.00),
        (5, 88.00),
        (6, 67.00),
        (7, 91.00),
        (8, 59.00),
        (9, 84.00),
        (10, 72.00),
        (11, 95.00),
        (12, 63.00)
) AS source(customer_id, score);

-- One run for quartiles and one for deciles makes the two analytical
-- uses explicit instead of conflating them.
INSERT INTO ntile_runs
    (run_name, bucket_count, score_date)
VALUES
    ('customer-quartiles-2026-10-25', 4, DATE '2026-10-25'),
    ('customer-deciles-2026-10-25', 10, DATE '2026-10-25');

-- NTILE requires a deterministic ORDER BY. The customer_id tie-breaker
-- ensures equal scores are assigned consistently.
INSERT INTO score_buckets (
    run_id,
    customer_id,
    score_id,
    bucket_number,
    bucket_count
)
SELECT
    r.run_id,
    cs.customer_id,
    cs.score_id,
    NTILE(r.bucket_count) OVER (
        ORDER BY cs.score DESC, cs.customer_id
    ) AS bucket_number,
    r.bucket_count
FROM ntile_runs AS r
JOIN customer_scores AS cs
    ON cs.score_date = r.score_date
   AND cs.score_status = 'valid';

-- Retrieve every customer with its quartile and decile.
SELECT
    c.customer_id,
    c.customer_name,
    cs.score,
    q.bucket_number AS quartile,
    d.bucket_number AS decile
FROM customers AS c
JOIN customer_scores AS cs
    ON cs.customer_id = c.customer_id
   AND cs.score_date = DATE '2026-10-25'
LEFT JOIN score_buckets AS q
    ON q.customer_id = c.customer_id
   AND q.run_id = (
       SELECT run_id
       FROM ntile_runs
       WHERE run_name = 'customer-quartiles-2026-10-25'
   )
LEFT JOIN score_buckets AS d
    ON d.customer_id = c.customer_id
   AND d.run_id = (
       SELECT run_id
       FROM ntile_runs
       WHERE run_name = 'customer-deciles-2026-10-25'
   )
ORDER BY cs.score DESC, c.customer_id;

-- Bucket-level statistics.
SELECT
    r.run_name,
    sb.bucket_number,
    COUNT(*) AS record_count,
    MIN(cs.score) AS minimum_score,
    MAX(cs.score) AS maximum_score,
    ROUND(AVG(cs.score), 2) AS average_score
FROM score_buckets AS sb
JOIN ntile_runs AS r
    ON r.run_id = sb.run_id
JOIN customer_scores AS cs
    ON cs.score_id = sb.score_id
GROUP BY
    r.run_name,
    sb.bucket_number
ORDER BY
    r.run_name,
    sb.bucket_number;

-- Verify the core NTILE property:
-- bucket sizes differ by no more than one row.
WITH bucket_sizes AS (
    SELECT
        run_id,
        bucket_number,
        COUNT(*) AS bucket_size
    FROM score_buckets
    GROUP BY run_id, bucket_number
)
SELECT
    r.run_name,
    MIN(bs.bucket_size) AS smallest_bucket,
    MAX(bs.bucket_size) AS largest_bucket,
    MAX(bs.bucket_size) - MIN(bs.bucket_size) AS size_difference,
    (
        MAX(bs.bucket_size) - MIN(bs.bucket_size) <= 1
    ) AS balanced
FROM bucket_sizes AS bs
JOIN ntile_runs AS r
    ON r.run_id = bs.run_id
GROUP BY r.run_name;

-- Example of direct NTILE usage for a single query.
WITH ranked AS (
    SELECT
        c.customer_id,
        c.customer_name,
        cs.score,
        NTILE(4) OVER (
            ORDER BY cs.score DESC, c.customer_id
        ) AS quartile
    FROM customers AS c
    JOIN customer_scores AS cs
        ON cs.customer_id = c.customer_id
    WHERE cs.score_date = DATE '2026-10-25'
      AND cs.score_status = 'valid'
)
SELECT
    quartile,
    COUNT(*) AS customers,
    MIN(score) AS minimum_score,
    MAX(score) AS maximum_score,
    ROUND(AVG(score), 2) AS average_score
FROM ranked
GROUP BY quartile
ORDER BY quartile;

-- Decile-based business segmentation.
WITH deciles AS (
    SELECT
        c.customer_id,
        c.customer_name,
        cs.score,
        NTILE(10) OVER (
            ORDER BY cs.score DESC, c.customer_id
        ) AS decile
    FROM customers AS c
    JOIN customer_scores AS cs
        ON cs.customer_id = c.customer_id
    WHERE cs.score_date = DATE '2026-10-25'
      AND cs.score_status = 'valid'
)
SELECT
    customer_id,
    customer_name,
    score,
    decile,
    CASE
        WHEN decile = 1 THEN 'Top 10%'
        WHEN decile IN (2, 3) THEN 'High'
        WHEN decile IN (4, 5) THEN 'Upper-Middle'
        WHEN decile IN (6, 7) THEN 'Lower-Middle'
        WHEN decile IN (8, 9) THEN 'Low'
        WHEN decile = 10 THEN 'Bottom 10%'
    END AS segment
FROM deciles
ORDER BY decile, score DESC, customer_id;

-- Compare NTILE with PERCENT_RANK. They answer different questions:
-- NTILE forces records into approximately equal-sized groups,
-- while PERCENT_RANK reports a relative position.
SELECT
    c.customer_name,
    cs.score,
    NTILE(4) OVER (
        ORDER BY cs.score DESC, c.customer_id
    ) AS quartile,
    ROUND(
        PERCENT_RANK() OVER (
            ORDER BY cs.score
        )::NUMERIC,
        4
    ) AS percent_rank
FROM customers AS c
JOIN customer_scores AS cs
    ON cs.customer_id = c.customer_id
WHERE cs.score_date = DATE '2026-10-25'
ORDER BY cs.score DESC, c.customer_id;

-- Demonstrate that NTILE can be evaluated independently inside
-- partitions. Here each score date would receive its own deciles.
SELECT
    cs.score_date,
    c.customer_name,
    cs.score,
    NTILE(10) OVER (
        PARTITION BY cs.score_date
        ORDER BY cs.score DESC, c.customer_id
    ) AS daily_decile
FROM customers AS c
JOIN customer_scores AS cs
    ON cs.customer_id = c.customer_id
ORDER BY
    cs.score_date,
    daily_decile,
    cs.score DESC;

-- Transactional example: create a new segmentation run and populate it
-- atomically. If either statement fails, the entire operation can roll back.
BEGIN;

INSERT INTO ntile_runs
    (run_name, bucket_count, score_date)
VALUES
    ('customer-quintiles-2026-10-25', 5, DATE '2026-10-25');

INSERT INTO score_buckets (
    run_id,
    customer_id,
    score_id,
    bucket_number,
    bucket_count
)
SELECT
    r.run_id,
    cs.customer_id,
    cs.score_id,
    NTILE(r.bucket_count) OVER (
        ORDER BY cs.score DESC, cs.customer_id
    ),
    r.bucket_count
FROM ntile_runs AS r
JOIN customer_scores AS cs
    ON cs.score_date = r.score_date
   AND cs.score_status = 'valid'
WHERE r.run_name = 'customer-quintiles-2026-10-25';

COMMIT;
