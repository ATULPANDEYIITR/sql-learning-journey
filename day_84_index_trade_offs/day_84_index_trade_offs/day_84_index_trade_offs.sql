-- ============================================================
-- INDEX TRADE-OFFS
-- Write Overhead, Storage, Maintenance and Over-Indexing
-- PostgreSQL 14+
--
-- Demonstrates:
-- 1. Relational modeling of index metadata
-- 2. Read and write workload collection
-- 3. Index storage estimation
-- 4. Composite and covering index definitions
-- 5. Index maintenance history
-- 6. Index usage reporting
-- 7. Write amplification analysis
-- 8. Duplicate and prefix-overlap detection
-- 9. Workload-based index recommendations
-- 10. Transaction-safe index governance decisions
--
-- Note:
-- Modeled index statistics are educational workload metrics.
-- PostgreSQL's actual index usage statistics are separately
-- available through pg_stat_user_indexes.
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS index_lab;

SET search_path TO index_lab, public;

-- ------------------------------------------------------------
-- 1. DOMAIN TABLES
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    repository_name VARCHAR(150) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(repository_name)) > 0)
);

CREATE TABLE IF NOT EXISTS database_tables (
    table_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    table_name VARCHAR(150) NOT NULL,
    row_count BIGINT NOT NULL DEFAULT 0,
    average_row_size_bytes INTEGER NOT NULL DEFAULT 200,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, table_name),
    CHECK (row_count >= 0),
    CHECK (average_row_size_bytes > 0)
);

CREATE TABLE IF NOT EXISTS index_definitions (
    index_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    table_id BIGINT NOT NULL
        REFERENCES database_tables(table_id)
        ON DELETE CASCADE,
    index_name VARCHAR(150) NOT NULL,
    index_type VARCHAR(20) NOT NULL DEFAULT 'BTREE',
    key_columns TEXT[] NOT NULL,
    included_columns TEXT[] NOT NULL DEFAULT '{}',
    is_unique BOOLEAN NOT NULL DEFAULT FALSE,
    index_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    estimated_storage_bytes BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(table_id, index_name),

    CHECK (
        index_type IN (
            'BTREE',
            'HASH',
            'COMPOSITE',
            'COVERING'
        )
    ),

    CHECK (
        index_status IN (
            'ACTIVE',
            'DISABLED',
            'NEEDS_REBUILD'
        )
    ),

    CHECK (cardinality(key_columns) > 0),
    CHECK (estimated_storage_bytes >= 0),

    CHECK (
        index_type <> 'COMPOSITE'
        OR cardinality(key_columns) >= 2
    ),

    CHECK (
        index_type <> 'HASH'
        OR cardinality(key_columns) = 1
    )
);

CREATE TABLE IF NOT EXISTS workload_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    table_id BIGINT NOT NULL
        REFERENCES database_tables(table_id)
        ON DELETE CASCADE,
    operation_type VARCHAR(10) NOT NULL,
    affected_rows BIGINT NOT NULL DEFAULT 1,
    modified_columns TEXT[] NOT NULL DEFAULT '{}',
    execution_time_ms NUMERIC(12,3),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        operation_type IN (
            'SELECT',
            'INSERT',
            'UPDATE',
            'DELETE'
        )
    ),

    CHECK (affected_rows >= 0),
    CHECK (
        execution_time_ms IS NULL
        OR execution_time_ms >= 0
    )
);

CREATE TABLE IF NOT EXISTS index_usage_metrics (
    metric_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    index_id BIGINT NOT NULL
        REFERENCES index_definitions(index_id)
        ON DELETE CASCADE,
    read_count BIGINT NOT NULL DEFAULT 0,
    insert_count BIGINT NOT NULL DEFAULT 0,
    update_count BIGINT NOT NULL DEFAULT 0,
    delete_count BIGINT NOT NULL DEFAULT 0,
    fragmentation_percent NUMERIC(6,2) NOT NULL DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(index_id),

    CHECK (read_count >= 0),
    CHECK (insert_count >= 0),
    CHECK (update_count >= 0),
    CHECK (delete_count >= 0),
    CHECK (
        fragmentation_percent BETWEEN 0 AND 100
    )
);

CREATE TABLE IF NOT EXISTS maintenance_history (
    maintenance_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    index_id BIGINT NOT NULL
        REFERENCES index_definitions(index_id)
        ON DELETE CASCADE,
    maintenance_type VARCHAR(30) NOT NULL,
    fragmentation_before NUMERIC(6,2) NOT NULL,
    fragmentation_after NUMERIC(6,2) NOT NULL,
    duration_ms NUMERIC(12,3),
    performed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        maintenance_type IN (
            'REBUILD',
            'REINDEX',
            'REVIEW',
            'DISABLE'
        )
    ),

    CHECK (
        fragmentation_before BETWEEN 0 AND 100
    ),

    CHECK (
        fragmentation_after BETWEEN 0 AND 100
    )
);

CREATE TABLE IF NOT EXISTS index_recommendations (
    recommendation_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    table_id BIGINT NOT NULL
        REFERENCES database_tables(table_id)
        ON DELETE CASCADE,
    proposed_columns TEXT[] NOT NULL,
    estimated_read_benefit NUMERIC(18,4) NOT NULL,
    estimated_storage_bytes BIGINT NOT NULL,
    write_risk VARCHAR(20) NOT NULL,
    recommendation_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (cardinality(proposed_columns) > 0),
    CHECK (estimated_read_benefit >= 0),
    CHECK (estimated_storage_bytes >= 0),

    CHECK (
        write_risk IN (
            'LOW',
            'MEDIUM',
            'HIGH'
        )
    ),

    CHECK (
        recommendation_status IN (
            'PENDING',
            'APPROVED',
            'REJECTED',
            'IMPLEMENTED'
        )
    )
);

-- ------------------------------------------------------------
-- 2. PERFORMANCE INDEXES FOR THE GOVERNANCE TABLES
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_database_tables_repository
    ON database_tables(repository_id);

CREATE INDEX IF NOT EXISTS idx_index_definitions_table_status
    ON index_definitions(table_id, index_status);

CREATE INDEX IF NOT EXISTS idx_workload_table_operation_date
    ON workload_events(table_id, operation_type, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_usage_index_measured
    ON index_usage_metrics(index_id, measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_maintenance_index_date
    ON maintenance_history(index_id, performed_at DESC);

CREATE INDEX IF NOT EXISTS idx_recommendations_status
    ON index_recommendations(recommendation_status, created_at DESC);

-- ------------------------------------------------------------
-- 3. SAMPLE REPOSITORY AND TABLE METADATA
-- ------------------------------------------------------------

INSERT INTO repositories(repository_name, description)
VALUES (
    'commerce_platform',
    'Production commerce database index analysis'
)
ON CONFLICT(repository_name) DO NOTHING;

INSERT INTO database_tables(
    repository_id,
    table_name,
    row_count,
    average_row_size_bytes
)
SELECT
    repository_id,
    'orders',
    100000,
    320
FROM repositories
WHERE repository_name = 'commerce_platform'
ON CONFLICT(repository_id, table_name)
DO UPDATE SET
    row_count = EXCLUDED.row_count,
    average_row_size_bytes =
        EXCLUDED.average_row_size_bytes;

-- ------------------------------------------------------------
-- 4. INDEX DEFINITIONS
-- ------------------------------------------------------------

INSERT INTO index_definitions(
    table_id,
    index_name,
    index_type,
    key_columns,
    included_columns,
    estimated_storage_bytes
)
SELECT
    table_id,
    'idx_orders_customer',
    'BTREE',
    ARRAY['customer_id'],
    ARRAY[]::TEXT[],
    3764706
FROM database_tables
WHERE table_name = 'orders'
ON CONFLICT(table_id, index_name) DO NOTHING;

INSERT INTO index_definitions(
    table_id,
    index_name,
    index_type,
    key_columns,
    included_columns,
    estimated_storage_bytes
)
SELECT
    table_id,
    'idx_orders_status_date',
    'COMPOSITE',
    ARRAY['status', 'created_at'],
    ARRAY[]::TEXT[],
    6588236
FROM database_tables
WHERE table_name = 'orders'
ON CONFLICT(table_id, index_name) DO NOTHING;

INSERT INTO index_definitions(
    table_id,
    index_name,
    index_type,
    key_columns,
    included_columns,
    estimated_storage_bytes
)
SELECT
    table_id,
    'idx_orders_region_covering',
    'COVERING',
    ARRAY['region'],
    ARRAY['total_amount'],
    5647059
FROM database_tables
WHERE table_name = 'orders'
ON CONFLICT(table_id, index_name) DO NOTHING;

INSERT INTO index_definitions(
    table_id,
    index_name,
    index_type,
    key_columns,
    included_columns,
    estimated_storage_bytes
)
SELECT
    table_id,
    'idx_orders_unused_reference',
    'BTREE',
    ARRAY['description'],
    ARRAY[]::TEXT[],
    3764706
FROM database_tables
WHERE table_name = 'orders'
ON CONFLICT(table_id, index_name) DO NOTHING;

-- ------------------------------------------------------------
-- 5. INDEX USAGE METRICS
-- ------------------------------------------------------------

INSERT INTO index_usage_metrics(
    index_id,
    read_count,
    insert_count,
    update_count,
    delete_count,
    fragmentation_percent,
    last_used_at
)
SELECT
    index_id,
    CASE index_name
        WHEN 'idx_orders_customer' THEN 25000
        WHEN 'idx_orders_status_date' THEN 12000
        WHEN 'idx_orders_region_covering' THEN 8000
        ELSE 0
    END,
    40000,
    CASE
        WHEN index_name = 'idx_orders_unused_reference'
        THEN 0
        ELSE 15000
    END,
    5000,
    CASE
        WHEN index_name = 'idx_orders_unused_reference'
        THEN 22.50
        ELSE 8.50
    END,
    CASE
        WHEN index_name = 'idx_orders_unused_reference'
        THEN NULL
        ELSE CURRENT_TIMESTAMP
    END
FROM index_definitions
ON CONFLICT(index_id) DO UPDATE SET
    read_count = EXCLUDED.read_count,
    insert_count = EXCLUDED.insert_count,
    update_count = EXCLUDED.update_count,
    delete_count = EXCLUDED.delete_count,
    fragmentation_percent =
        EXCLUDED.fragmentation_percent,
    last_used_at = EXCLUDED.last_used_at,
    measured_at = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- 6. SAMPLE WORKLOAD EVENTS
-- ------------------------------------------------------------

INSERT INTO workload_events(
    table_id,
    operation_type,
    affected_rows,
    modified_columns,
    execution_time_ms
)
SELECT
    table_id,
    event.operation_type,
    event.affected_rows,
    event.modified_columns,
    event.execution_time_ms
FROM database_tables
CROSS JOIN (
    VALUES
        (
            'SELECT'::VARCHAR,
            1::BIGINT,
            ARRAY['customer_id']::TEXT[],
            4.50::NUMERIC
        ),
        (
            'SELECT',
            1,
            ARRAY['status', 'created_at'],
            7.20
        ),
        (
            'INSERT',
            500,
            ARRAY[]::TEXT[],
            30.00
        ),
        (
            'UPDATE',
            100,
            ARRAY['status', 'total_amount'],
            15.00
        ),
        (
            'DELETE',
            50,
            ARRAY[]::TEXT[],
            9.00
        )
) AS event(
    operation_type,
    affected_rows,
    modified_columns,
    execution_time_ms
)
WHERE table_name = 'orders';

-- ------------------------------------------------------------
-- 7. INDEX STORAGE ESTIMATION FUNCTION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION estimate_index_storage(
    p_row_count BIGINT,
    p_key_column_count INTEGER,
    p_included_column_count INTEGER
)
RETURNS BIGINT
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    v_entry_bytes BIGINT;
BEGIN
    IF p_row_count < 0
       OR p_key_column_count <= 0
       OR p_included_column_count < 0 THEN
        RAISE EXCEPTION 'Invalid storage estimation inputs';
    END IF;

    v_entry_bytes :=
        p_key_column_count * 24
        + p_included_column_count * 16
        + 8;

    RETURN CEIL(
        p_row_count::NUMERIC * v_entry_bytes / 0.85
    )::BIGINT;
END;
$$;

-- ------------------------------------------------------------
-- 8. WORKLOAD METRIC UPDATE FUNCTION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION apply_index_workload(
    p_index_id BIGINT,
    p_operation VARCHAR,
    p_count BIGINT DEFAULT 1
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_count <= 0 THEN
        RAISE EXCEPTION 'Operation count must be positive';
    END IF;

    IF p_operation NOT IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE') THEN
        RAISE EXCEPTION 'Unsupported operation: %', p_operation;
    END IF;

    UPDATE index_usage_metrics
    SET
        read_count = read_count +
            CASE WHEN p_operation = 'SELECT' THEN p_count ELSE 0 END,

        insert_count = insert_count +
            CASE WHEN p_operation = 'INSERT' THEN p_count ELSE 0 END,

        update_count = update_count +
            CASE WHEN p_operation = 'UPDATE' THEN p_count ELSE 0 END,

        delete_count = delete_count +
            CASE WHEN p_operation = 'DELETE' THEN p_count ELSE 0 END,

        fragmentation_percent = LEAST(
            100,
            fragmentation_percent +
            CASE
                WHEN p_operation = 'SELECT' THEN 0
                ELSE p_count * 0.015
            END
        ),

        last_used_at = CASE
            WHEN p_operation = 'SELECT'
            THEN CURRENT_TIMESTAMP
            ELSE last_used_at
        END,

        measured_at = CURRENT_TIMESTAMP
    WHERE index_id = p_index_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Index metrics not found: %', p_index_id;
    END IF;
END;
$$;

-- ------------------------------------------------------------
-- 9. INDEX USAGE REPORT
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW index_usage_report AS
SELECT
    r.repository_name,
    t.table_name,
    i.index_id,
    i.index_name,
    i.index_type,
    i.key_columns,
    i.included_columns,
    i.index_status,
    i.estimated_storage_bytes,

    COALESCE(m.read_count, 0) AS reads,

    COALESCE(m.insert_count, 0) AS inserts,

    COALESCE(m.update_count, 0) AS updates,

    COALESCE(m.delete_count, 0) AS deletes,

    COALESCE(m.insert_count, 0)
        + COALESCE(m.update_count, 0)
        + COALESCE(m.delete_count, 0)
        AS total_writes,

    ROUND(
        (
            COALESCE(m.insert_count, 0)
            + COALESCE(m.update_count, 0)
            + COALESCE(m.delete_count, 0)
        )::NUMERIC
        / GREATEST(COALESCE(m.read_count, 0), 1),
        2
    ) AS write_read_ratio,

    COALESCE(
        m.fragmentation_percent,
        0
    ) AS fragmentation_percent,

    m.last_used_at

FROM index_definitions i
JOIN database_tables t
    ON t.table_id = i.table_id
JOIN repositories r
    ON r.repository_id = t.repository_id
LEFT JOIN index_usage_metrics m
    ON m.index_id = i.index_id;

-- ------------------------------------------------------------
-- 10. INDEX STORAGE REPORT
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW index_storage_report AS
SELECT
    t.table_id,
    t.table_name,
    t.row_count,
    t.row_count * t.average_row_size_bytes
        AS estimated_table_storage_bytes,

    COALESCE(
        SUM(
            CASE
                WHEN i.index_status <> 'DISABLED'
                THEN i.estimated_storage_bytes
                ELSE 0
            END
        ),
        0
    ) AS total_index_storage_bytes,

    COUNT(i.index_id) FILTER (
        WHERE i.index_status = 'ACTIVE'
    ) AS active_index_count

FROM database_tables t
LEFT JOIN index_definitions i
    ON i.table_id = t.table_id
GROUP BY
    t.table_id,
    t.table_name,
    t.row_count,
    t.average_row_size_bytes;

-- ------------------------------------------------------------
-- 11. INDEX GOVERNANCE EVALUATION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION evaluate_index_governance(
    p_minimum_writes BIGINT DEFAULT 100,
    p_maximum_write_read_ratio NUMERIC DEFAULT 10
)
RETURNS TABLE (
    index_name VARCHAR,
    recommendation VARCHAR,
    write_read_ratio NUMERIC,
    reasons TEXT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        u.index_name,

        CASE
            WHEN u.total_writes >= p_minimum_writes
             AND (
                 u.reads = 0
                 OR u.write_read_ratio >
                    p_maximum_write_read_ratio
             )
            THEN 'REVIEW'

            WHEN u.fragmentation_percent > 30
            THEN 'REBUILD_REVIEW'

            ELSE 'RETAIN'
        END::VARCHAR,

        u.write_read_ratio,

        CONCAT_WS(
            '; ',

            CASE
                WHEN u.total_writes >= p_minimum_writes
                 AND u.reads = 0
                THEN 'No observed reads'
            END,

            CASE
                WHEN u.total_writes >= p_minimum_writes
                 AND u.write_read_ratio >
                    p_maximum_write_read_ratio
                THEN 'High write-to-read ratio'
            END,

            CASE
                WHEN u.fragmentation_percent > 30
                THEN 'Fragmentation threshold exceeded'
            END
        ) AS reasons

    FROM index_usage_report u
    WHERE u.index_status = 'ACTIVE';
$$;

-- ------------------------------------------------------------
-- 12. COMPOSITE INDEX PREFIX-OVERLAP DETECTION
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW index_prefix_overlaps AS
SELECT
    first_index.index_name AS shorter_index,
    second_index.index_name AS longer_index,
    first_index.key_columns AS shorter_columns,
    second_index.key_columns AS longer_columns,
    first_index.table_name

FROM index_usage_report first_index

JOIN index_usage_report second_index
    ON first_index.table_name = second_index.table_name
    AND first_index.index_name < second_index.index_name

WHERE
    cardinality(first_index.key_columns)
        < cardinality(second_index.key_columns)

    AND first_index.key_columns =
        second_index.key_columns[
            1:cardinality(first_index.key_columns)
        ]

    AND first_index.index_status = 'ACTIVE'
    AND second_index.index_status = 'ACTIVE';

-- ------------------------------------------------------------
-- 13. INDEX RECOMMENDATION PROCEDURE
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE generate_index_recommendations(
    p_table_id BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM database_tables
        WHERE table_id = p_table_id
    ) THEN
        RAISE EXCEPTION 'Unknown table: %', p_table_id;
    END IF;

    INSERT INTO index_recommendations(
        table_id,
        proposed_columns,
        estimated_read_benefit,
        estimated_storage_bytes,
        write_risk,
        reason
    )
    SELECT
        p_table_id,
        ARRAY['description'],
        2000,
        estimate_index_storage(
            t.row_count,
            1,
            0
        ),
        'HIGH',
        'Unindexed description search pattern. '
        || 'Validate selectivity, query frequency and write cost '
        || 'before creating an index.'

    FROM database_tables t

    WHERE t.table_id = p_table_id

      AND NOT EXISTS (
          SELECT 1
          FROM index_definitions i
          WHERE i.table_id = t.table_id
            AND i.key_columns = ARRAY['description']::TEXT[]
            AND i.index_status = 'ACTIVE'
      )

      AND NOT EXISTS (
          SELECT 1
          FROM index_recommendations r
          WHERE r.table_id = p_table_id
            AND r.proposed_columns =
                ARRAY['description']::TEXT[]
            AND r.recommendation_status = 'PENDING'
      );
END;
$$;

-- ------------------------------------------------------------
-- 14. MAINTENANCE PROCEDURE
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE rebuild_index_metadata(
    p_index_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_before NUMERIC(6,2);
    v_name VARCHAR(150);
BEGIN
    SELECT
        i.index_name,
        m.fragmentation_percent
    INTO
        v_name,
        v_before
    FROM index_definitions i
    JOIN index_usage_metrics m
        ON m.index_id = i.index_id
    WHERE i.index_id = p_index_id
    FOR UPDATE OF i, m;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Index or usage metrics not found';
    END IF;

    UPDATE index_definitions
    SET index_status = 'NEEDS_REBUILD'
    WHERE index_id = p_index_id;

    UPDATE index_usage_metrics
    SET
        fragmentation_percent = 0,
        measured_at = CURRENT_TIMESTAMP
    WHERE index_id = p_index_id;

    INSERT INTO maintenance_history(
        index_id,
        maintenance_type,
        fragmentation_before,
        fragmentation_after,
        duration_ms
    )
    VALUES (
        p_index_id,
        'REBUILD',
        v_before,
        0,
        125.000
    );

    UPDATE index_definitions
    SET index_status = 'ACTIVE'
    WHERE index_id = p_index_id;

    RAISE NOTICE 'Maintenance metadata updated for %', v_name;
END;
$$;

-- ------------------------------------------------------------
-- 15. VALIDATION: INDEX DEFINITION INTEGRITY
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_index_definition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_table_columns TEXT[];
    v_all_columns TEXT[];
BEGIN
    SELECT array_agg(column_name::TEXT ORDER BY ordinal_position)
    INTO v_table_columns
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'nonexistent';

    -- The logical table schema is managed through metadata.
    -- The following validation prevents empty and repeated
    -- key/included column declarations.

    IF cardinality(NEW.key_columns) = 0 THEN
        RAISE EXCEPTION 'Index requires key columns';
    END IF;

    SELECT array_agg(DISTINCT column_name)
    INTO v_all_columns
    FROM unnest(
        NEW.key_columns || NEW.included_columns
    ) AS column_name;

    IF cardinality(v_all_columns) <>
       cardinality(NEW.key_columns)
       + cardinality(NEW.included_columns) THEN
        RAISE EXCEPTION
            'Duplicate key or included column declaration';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_index_definition
ON index_definitions;

CREATE TRIGGER trg_validate_index_definition
BEFORE INSERT OR UPDATE OF
    key_columns,
    included_columns,
    index_type
ON index_definitions
FOR EACH ROW
EXECUTE FUNCTION validate_index_definition();

-- ------------------------------------------------------------
-- 16. POSTGRESQL NATIVE INDEX USAGE
-- ------------------------------------------------------------

-- Run against the actual application database.
-- These statistics are separate from the simulated workload.

CREATE OR REPLACE VIEW native_index_usage AS
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS scan_count,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_relation_size(indexrelid) AS actual_index_bytes

FROM pg_stat_user_indexes;

-- ------------------------------------------------------------
-- 17. INDEX MAINTENANCE AND STORAGE OBSERVABILITY
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW native_index_storage AS
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    pg_size_pretty(
        pg_relation_size(indexrelid)
    ) AS readable_size,
    pg_relation_size(indexrelid) AS size_bytes

FROM pg_stat_user_indexes;

-- ------------------------------------------------------------
-- 18. WORKFLOW TRANSACTION
-- ------------------------------------------------------------

DO $$
DECLARE
    v_table_id BIGINT;
    v_index_id BIGINT;
BEGIN
    SELECT table_id
    INTO v_table_id
    FROM database_tables
    WHERE table_name = 'orders'
    LIMIT 1;

    -- Simulate an index write operation.
    SELECT index_id
    INTO v_index_id
    FROM index_definitions
    WHERE table_id = v_table_id
      AND index_name = 'idx_orders_customer';

    PERFORM apply_index_workload(
        v_index_id,
        'INSERT',
        500
    );

    -- Simulate an index read operation.
    PERFORM apply_index_workload(
        v_index_id,
        'SELECT',
        25000
    );

    -- Generate a candidate for a frequent unindexed query.
    CALL generate_index_recommendations(v_table_id);

    -- Rebuild metadata for a fragmented index.
    SELECT index_id
    INTO v_index_id
    FROM index_definitions
    WHERE table_id = v_table_id
      AND index_name = 'idx_orders_customer';

    CALL rebuild_index_metadata(v_index_id);
END;
$$;

-- ------------------------------------------------------------
-- 19. RETRIEVAL QUERIES
-- ------------------------------------------------------------

-- A. Complete index usage report.

SELECT *
FROM index_usage_report
ORDER BY total_writes DESC, reads DESC;

-- B. Table and index storage comparison.

SELECT *
FROM index_storage_report
ORDER BY total_index_storage_bytes DESC;

-- C. Indexes requiring governance review.

SELECT *
FROM evaluate_index_governance(100, 10)
ORDER BY write_read_ratio DESC;

-- D. Composite index prefix overlap.

SELECT *
FROM index_prefix_overlaps;

-- E. Maintenance history.

SELECT
    i.index_name,
    h.maintenance_type,
    h.fragmentation_before,
    h.fragmentation_after,
    h.duration_ms,
    h.performed_at
FROM maintenance_history h
JOIN index_definitions i
    ON i.index_id = h.index_id
ORDER BY h.performed_at DESC;

-- F. Pending recommendations.

SELECT
    t.table_name,
    r.proposed_columns,
    r.estimated_read_benefit,
    r.estimated_storage_bytes,
    r.write_risk,
    r.reason
FROM index_recommendations r
JOIN database_tables t
    ON t.table_id = r.table_id
WHERE r.recommendation_status = 'PENDING'
ORDER BY r.estimated_read_benefit DESC;

-- G. Aggregate workload distribution.

SELECT
    t.table_name,
    COUNT(*) FILTER (
        WHERE w.operation_type = 'SELECT'
    ) AS select_events,

    COUNT(*) FILTER (
        WHERE w.operation_type = 'INSERT'
    ) AS insert_events,

    COUNT(*) FILTER (
        WHERE w.operation_type = 'UPDATE'
    ) AS update_events,

    COUNT(*) FILTER (
        WHERE w.operation_type = 'DELETE'
    ) AS delete_events,

    SUM(w.affected_rows) AS total_affected_rows,

    ROUND(
        AVG(w.execution_time_ms),
        2
    ) AS average_execution_ms

FROM database_tables t
LEFT JOIN workload_events w
    ON w.table_id = t.table_id
GROUP BY t.table_id, t.table_name;

-- H. Native PostgreSQL index size and usage.

SELECT *
FROM native_index_usage
ORDER BY scan_count ASC;

-- ------------------------------------------------------------
-- 20. ELIGIBILITY DETERMINATION
-- ------------------------------------------------------------

-- An index is eligible for a disable review when:
-- - It is active.
-- - It has enough observed write activity.
-- - It has no observed reads or an excessive write/read ratio.
-- - The decision is a review candidate, not automatic deletion.

WITH evaluated AS (
    SELECT
        u.index_id,
        u.index_name,
        u.reads,
        u.total_writes,
        u.write_read_ratio,
        u.estimated_storage_bytes,
        u.index_status

    FROM index_usage_report u
)
SELECT
    index_id,
    index_name,
    reads,
    total_writes,
    write_read_ratio,
    estimated_storage_bytes,

    CASE
        WHEN total_writes >= 100
         AND reads = 0
        THEN 'ELIGIBLE_FOR_UNUSED_INDEX_REVIEW'

        WHEN total_writes >= 100
         AND write_read_ratio > 10
        THEN 'ELIGIBLE_FOR_WRITE_COST_REVIEW'

        ELSE 'RETAIN_PENDING_MORE_EVIDENCE'
    END AS eligibility

FROM evaluated
WHERE index_status = 'ACTIVE';

COMMIT;

-- ============================================================
-- END OF INDEX TRADE-OFFS DATABASE MODEL
-- ============================================================
