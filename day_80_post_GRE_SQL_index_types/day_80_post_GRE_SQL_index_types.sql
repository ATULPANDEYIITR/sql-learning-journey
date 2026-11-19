/*
===============================================================================
POSTGRESQL INDEX TYPES LABORATORY
===============================================================================

Supported index methods:
    1. B-tree
    2. Hash
    3. GiST
    4. SP-GiST
    5. GIN
    6. BRIN

Requirements:
    PostgreSQL 14 or later recommended.
    No third-party extensions required.

Execution:
    psql -v ON_ERROR_STOP=1 -f postgresql_indexes.sql

This script creates an isolated schema, representative datasets,
six index implementations, workload queries, reporting views,
validation functions, and operational demonstrations.

The schema is recreated on each execution.
*/

BEGIN;

DROP SCHEMA IF EXISTS index_lab CASCADE;

CREATE SCHEMA index_lab;

SET search_path TO index_lab, public;

-- ============================================================================
-- 1. DOMAIN TABLES
-- ============================================================================

CREATE TABLE customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    city TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT uq_customer_email UNIQUE (email),
    CONSTRAINT chk_customer_email
        CHECK (position('@' IN email) > 1)
);

CREATE TABLE orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL
        REFERENCES customers(customer_id),
    order_number TEXT NOT NULL UNIQUE,
    total_amount NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',

    CONSTRAINT chk_order_amount CHECK (total_amount >= 0),
    CONSTRAINT chk_order_status
        CHECK (status IN ('pending', 'paid', 'shipped', 'cancelled'))
);

CREATE TABLE events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,

    CONSTRAINT chk_event_payload
        CHECK (jsonb_typeof(payload) = 'object')
);

CREATE TABLE documents (
    document_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector(
            'english',
            coalesce(title, '') || ' ' || coalesce(body, '')
        )
    ) STORED,
    published_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE network_logs (
    log_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_ip INET NOT NULL,
    server_ip INET NOT NULL,
    message TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE spatial_events (
    spatial_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_name TEXT NOT NULL,
    location TSRANGE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_spatial_range
        CHECK (NOT isempty(location))
);

CREATE TABLE index_maintenance_log (
    maintenance_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    index_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT chk_maintenance_operation
        CHECK (
            operation IN (
                'CREATE',
                'REINDEX',
                'ANALYZE',
                'DROP',
                'REVIEW'
            )
        )
);

-- ============================================================================
-- 2. SAMPLE DATA
-- ============================================================================

INSERT INTO customers (
    email,
    full_name,
    city,
    created_at
)
VALUES
    ('alice@example.com', 'Alice Sharma', 'Lucknow', '2025-01-10'),
    ('bob@example.com', 'Bob Verma', 'Delhi', '2025-02-15'),
    ('carol@example.com', 'Carol Singh', 'Mumbai', '2025-03-20'),
    ('david@example.com', 'David Kumar', 'Lucknow', '2025-04-25'),
    ('eve@example.com', 'Eve Gupta', 'Pune', '2025-05-30');

INSERT INTO orders (
    customer_id,
    order_number,
    total_amount,
    created_at,
    status
)
SELECT
    customer_id,
    'ORD-' || customer_id,
    customer_id * 1250.50,
    TIMESTAMPTZ '2025-01-01 10:00:00+05:30'
        + customer_id * INTERVAL '15 days',
    CASE
        WHEN customer_id % 2 = 0 THEN 'paid'
        ELSE 'pending'
    END
FROM customers;

INSERT INTO events (
    event_type,
    payload,
    tags,
    occurred_at,
    source
)
VALUES
(
    'login',
    '{"user_id": 101, "department": "engineering", "success": true}',
    ARRAY['authentication', 'security'],
    '2025-01-01 10:00:00+05:30',
    'web'
),
(
    'payment',
    '{"user_id": 102, "amount": 4500, "currency": "INR"}',
    ARRAY['finance', 'transaction'],
    '2025-01-02 11:00:00+05:30',
    'mobile'
),
(
    'login',
    '{"user_id": 103, "department": "research", "success": false}',
    ARRAY['authentication', 'security', 'failure'],
    '2025-01-03 12:00:00+05:30',
    'web'
),
(
    'shipment',
    '{"user_id": 104, "warehouse": "north", "priority": "high"}',
    ARRAY['logistics', 'priority'],
    '2025-01-04 13:00:00+05:30',
    'api'
);

INSERT INTO documents (
    title,
    body,
    published_at
)
VALUES
(
    'Database Indexing',
    'PostgreSQL B-tree indexes support equality and range queries.',
    '2025-01-01'
),
(
    'Search Architecture',
    'GIN indexes support full text search and document containment.',
    '2025-01-02'
),
(
    'Database Performance',
    'BRIN indexes summarize physical page ranges in large tables.',
    '2025-01-03'
),
(
    'Spatial Data',
    'GiST indexes support spatial and range-oriented operations.',
    '2025-01-04'
);

INSERT INTO network_logs (
    client_ip,
    server_ip,
    message,
    recorded_at
)
VALUES
(
    '192.168.1.10',
    '10.0.0.1',
    'Successful authentication',
    '2025-01-01 10:00:00+05:30'
),
(
    '192.168.1.20',
    '10.0.0.1',
    'Connection rejected',
    '2025-01-01 11:00:00+05:30'
),
(
    '10.10.1.25',
    '10.0.0.2',
    'Application request',
    '2025-01-02 10:00:00+05:30'
);

INSERT INTO spatial_events (
    event_name,
    location
)
VALUES
(
    'Morning maintenance',
    tsrange(
        '2025-01-01 09:00',
        '2025-01-01 12:00',
        '[)'
    )
),
(
    'Database migration',
    tsrange(
        '2025-01-02 10:00',
        '2025-01-02 14:00',
        '[)'
    )
),
(
    'Security inspection',
    tsrange(
        '2025-01-03 15:00',
        '2025-01-03 17:00',
        '[)'
    )
);

-- ============================================================================
-- 3. B-TREE INDEX
-- ============================================================================

-- B-tree is the default index method.
-- Supports equality, range comparisons, ordering and uniqueness.

CREATE INDEX idx_orders_created_btree
ON orders USING BTREE (created_at);

CREATE INDEX idx_orders_amount_btree
ON orders USING BTREE (total_amount);

CREATE INDEX idx_customers_city_active
ON customers USING BTREE (city)
WHERE active = TRUE;

-- Composite B-tree: leading-column order matters.
CREATE INDEX idx_orders_customer_date
ON orders USING BTREE (customer_id, created_at DESC);

-- Example:
SELECT order_id, order_number, created_at
FROM orders
WHERE created_at >= TIMESTAMPTZ '2025-01-01'
  AND created_at < TIMESTAMPTZ '2025-07-01'
ORDER BY created_at DESC;

-- ============================================================================
-- 4. HASH INDEX
-- ============================================================================

-- Hash indexes support equality comparisons.
-- They do not support range scans or ordered retrieval.

CREATE INDEX idx_network_message_hash
ON network_logs USING HASH (message);

SELECT log_id, message
FROM network_logs
WHERE message = 'Connection rejected';

-- ============================================================================
-- 5. GiST INDEX
-- ============================================================================

-- GiST is extensible and relies on operator classes.
-- Built-in range operator classes support overlap and containment.

CREATE INDEX idx_spatial_location_gist
ON spatial_events USING GIST (location);

-- Find events overlapping a specified interval.
SELECT spatial_id, event_name, location
FROM spatial_events
WHERE location &&
      tsrange(
          '2025-01-02 09:00',
          '2025-01-02 12:00',
          '[)'
      );

-- GiST also supports exclusion constraints for suitable range domains.
CREATE TABLE room_reservations (
    reservation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id INTEGER NOT NULL,
    reservation_period TSRANGE NOT NULL,

    CONSTRAINT chk_reservation_period
        CHECK (NOT isempty(reservation_period)),

    CONSTRAINT ex_room_reservation_overlap
        EXCLUDE USING GIST (
            room_id WITH =,
            reservation_period WITH &&
        )
);

INSERT INTO room_reservations (
    room_id,
    reservation_period
)
VALUES (
    1,
    tsrange('2025-06-01 09:00', '2025-06-01 10:00', '[)')
);

-- ============================================================================
-- 6. SP-GiST INDEX
-- ============================================================================

-- SP-GiST partitions search spaces.
-- PostgreSQL provides operator classes for supported types,
-- including inet and text.

CREATE INDEX idx_network_client_ip_spgist
ON network_logs USING SPGIST (client_ip);

SELECT log_id, client_ip
FROM network_logs
WHERE client_ip <<= INET '192.168.1.0/24';

-- ============================================================================
-- 7. GIN INDEX
-- ============================================================================

-- GIN maps individual component values to matching rows.
-- Appropriate for JSONB, arrays and full-text search.

CREATE INDEX idx_events_payload_gin
ON events USING GIN (payload);

-- jsonb_path_ops is optimized for containment workloads.
CREATE INDEX idx_events_payload_path_gin
ON events USING GIN (payload jsonb_path_ops);

CREATE INDEX idx_events_tags_gin
ON events USING GIN (tags);

CREATE INDEX idx_documents_search_gin
ON documents USING GIN (search_vector);

-- JSONB containment.
SELECT event_id, event_type
FROM events
WHERE payload @> '{"department": "engineering"}'::jsonb;

-- Array containment.
SELECT event_id, tags
FROM events
WHERE tags @> ARRAY['security'];

-- Full-text search.
SELECT document_id, title
FROM documents
WHERE search_vector @@ plainto_tsquery('english', 'database indexing');

-- ============================================================================
-- 8. BRIN INDEX
-- ============================================================================

-- BRIN stores summaries for physical block ranges.
-- It is especially useful for large tables with physically correlated values.
-- It is lossy: matching page ranges may require heap rechecks.

CREATE INDEX idx_events_occurred_brin
ON events USING BRIN (occurred_at)
WITH (
    pages_per_range = 32,
    autosummarize = TRUE
);

CREATE INDEX idx_network_recorded_brin
ON network_logs USING BRIN (recorded_at);

SELECT event_id, occurred_at
FROM events
WHERE occurred_at >= TIMESTAMPTZ '2025-01-01'
  AND occurred_at < TIMESTAMPTZ '2025-02-01';

-- ============================================================================
-- 9. INDEX CATALOG AND REPORTING
-- ============================================================================

CREATE VIEW v_index_inventory AS
SELECT
    ns.nspname AS schema_name,
    tbl.relname AS table_name,
    idx.relname AS index_name,
    am.amname AS index_method,
    pg_size_pretty(pg_relation_size(idx.oid)) AS index_size,
    pg_get_indexdef(idx.oid) AS index_definition,
    i.indisunique AS is_unique,
    i.indisprimary AS is_primary,
    i.indisvalid AS is_valid,
    i.indisready AS is_ready
FROM pg_index i
JOIN pg_class idx
    ON idx.oid = i.indexrelid
JOIN pg_class tbl
    ON tbl.oid = i.indrelid
JOIN pg_namespace ns
    ON ns.oid = tbl.relnamespace
JOIN pg_am am
    ON am.oid = idx.relam
WHERE ns.nspname = 'index_lab';

CREATE VIEW v_index_usage AS
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(
        pg_relation_size(indexrelid)
    ) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'index_lab';

-- Index inventory.
SELECT *
FROM v_index_inventory
ORDER BY table_name, index_name;

-- Usage statistics.
SELECT *
FROM v_index_usage
ORDER BY idx_scan DESC;

-- ============================================================================
-- 10. INDEX MAINTENANCE AUDIT TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_log_index_maintenance()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO index_maintenance_log (
        index_name,
        operation,
        details
    )
    VALUES (
        NEW.index_name,
        NEW.operation,
        NEW.details
    );

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_index_maintenance_audit
AFTER INSERT ON index_maintenance_log
FOR EACH ROW
EXECUTE FUNCTION fn_log_index_maintenance();

-- The audit trigger is demonstrated with a separate event table below.
-- A trigger cannot insert another row into its own triggering table
-- without creating recursive behavior.

DROP TRIGGER trg_index_maintenance_audit ON index_maintenance_log;

CREATE TABLE index_maintenance_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    index_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_index_maintenance_audit
AFTER INSERT ON index_maintenance_events
FOR EACH ROW
EXECUTE FUNCTION fn_log_index_maintenance();

-- ============================================================================
-- 11. MAINTENANCE PROCEDURE
-- ============================================================================

CREATE OR REPLACE PROCEDURE sp_record_index_review(
    p_index_name TEXT,
    p_details JSONB DEFAULT '{}'::jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_index_name IS NULL OR btrim(p_index_name) = '' THEN
        RAISE EXCEPTION 'Index name is required';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM v_index_inventory
        WHERE index_name = p_index_name
    ) THEN
        RAISE EXCEPTION 'Index does not exist: %', p_index_name;
    END IF;

    INSERT INTO index_maintenance_events (
        index_name,
        operation,
        details
    )
    VALUES (
        p_index_name,
        'REVIEW',
        p_details
    );
END;
$$;

CALL sp_record_index_review(
    'idx_orders_created_btree',
    '{"reviewer": "database_admin", "reason": "performance_audit"}'
);

-- ============================================================================
-- 12. ELIGIBILITY EVALUATION FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_index_eligibility(
    p_pattern TEXT,
    p_rows BIGINT,
    p_correlation NUMERIC,
    p_update_rate NUMERIC
)
RETURNS TABLE (
    index_method TEXT,
    applicable BOOLEAN,
    suitability TEXT,
    explanation TEXT
)
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF p_pattern IS NULL OR p_pattern NOT IN (
        'equality',
        'range',
        'ordering',
        'array',
        'contains',
        'spatial',
        'prefix',
        'full_text',
        'large_range'
    ) THEN
        RAISE EXCEPTION 'Unsupported query pattern: %', p_pattern;
    END IF;

    IF p_rows <= 0 THEN
        RAISE EXCEPTION 'Row count must be positive';
    END IF;

    IF p_correlation NOT BETWEEN 0 AND 1
       OR p_update_rate NOT BETWEEN 0 AND 1 THEN
        RAISE EXCEPTION 'Ratios must be between zero and one';
    END IF;

    RETURN QUERY
    SELECT
        candidate.method,
        candidate.applicable,
        candidate.suitability,
        candidate.explanation
    FROM (
        VALUES
        (
            'btree',
            p_pattern IN (
                'equality', 'range', 'ordering', 'prefix'
            ),
            'General purpose',
            'Ordered equality and range access'
        ),
        (
            'hash',
            p_pattern = 'equality',
            'Equality focused',
            'Hash-based equality lookup only'
        ),
        (
            'gist',
            p_pattern IN ('range', 'spatial', 'contains'),
            'Specialized',
            'Operator-class-dependent spatial and range searches'
        ),
        (
            'spgist',
            p_pattern IN ('spatial', 'prefix', 'equality'),
            'Specialized',
            'Partitioned search structures'
        ),
        (
            'gin',
            p_pattern IN ('array', 'contains', 'full_text'),
            CASE
                WHEN p_update_rate > 0.5 THEN 'Write intensive'
                ELSE 'Component lookup'
            END,
            'Inverted lookup for arrays, JSONB and text'
        ),
        (
            'brin',
            p_pattern IN ('range', 'large_range'),
            CASE
                WHEN p_correlation >= 0.7 THEN 'Good candidate'
                ELSE 'Correlation risk'
            END,
            'Block summaries depend on physical correlation'
        )
    ) AS candidate(
        method,
        applicable,
        suitability,
        explanation
    )
    ORDER BY candidate.applicable DESC, candidate.method;
END;
$$;

-- Example eligibility evaluation.
SELECT *
FROM fn_index_eligibility(
    'large_range',
    10000000,
    0.95,
    0.05
);

-- ============================================================================
-- 13. CTE-BASED INDEX REPORTING
-- ============================================================================

WITH index_statistics AS (
    SELECT
        schemaname,
        relname AS table_name,
        indexrelname AS index_name,
        idx_scan,
        idx_tup_read,
        idx_tup_fetch
    FROM pg_stat_user_indexes
    WHERE schemaname = 'index_lab'
),
ranked_indexes AS (
    SELECT
        *,
        DENSE_RANK() OVER (
            ORDER BY idx_scan DESC
        ) AS usage_rank
    FROM index_statistics
)
SELECT
    table_name,
    index_name,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    usage_rank
FROM ranked_indexes
ORDER BY usage_rank, index_name;

-- ============================================================================
-- 14. SIZE AND TABLE-CORRELATION REPORT
-- ============================================================================

SELECT
    schemaname,
    tablename,
    attname,
    correlation,
    null_frac,
    n_distinct
FROM pg_stats
WHERE schemaname = 'index_lab'
ORDER BY tablename, attname;

SELECT
    c.relname AS table_name,
    pg_size_pretty(pg_relation_size(c.oid)) AS heap_size,
    pg_size_pretty(pg_indexes_size(c.oid)) AS indexes_size,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c
JOIN pg_namespace n
    ON n.oid = c.relnamespace
WHERE n.nspname = 'index_lab'
  AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC;

-- ============================================================================
-- 15. QUERY PLAN INSPECTION
-- ============================================================================

-- ANALYZE refreshes planner statistics.
ANALYZE customers;
ANALYZE orders;
ANALYZE events;
ANALYZE documents;
ANALYZE network_logs;
ANALYZE spatial_events;

-- Planner may choose a sequential scan for small tables.
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM customers
WHERE email = 'alice@example.com';

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM events
WHERE tags @> ARRAY['security'];

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM documents
WHERE search_vector @@ plainto_tsquery(
    'english',
    'database indexing'
);

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM spatial_events
WHERE location && tsrange(
    '2025-01-02 09:00',
    '2025-01-02 12:00',
    '[)'
);

-- ============================================================================
-- 16. INDEX MAINTENANCE OPERATIONS
-- ============================================================================

-- Rebuild an index when operationally justified.
-- REINDEX acquires locks; plan production execution accordingly.

REINDEX INDEX idx_orders_created_btree;

-- Update planner statistics.
ANALYZE orders;

INSERT INTO index_maintenance_events (
    index_name,
    operation,
    details
)
VALUES (
    'idx_orders_created_btree',
    'REINDEX',
    '{"reason": "demonstration", "method": "REINDEX INDEX"}'
);

-- ============================================================================
-- 17. TRANSACTION AND FAILURE HANDLING
-- ============================================================================

-- A savepoint demonstrates rollback of an unsuccessful index operation.

SAVEPOINT index_operation;

CREATE INDEX idx_temporary_customer_city
ON customers USING BTREE (city);

ROLLBACK TO SAVEPOINT index_operation;

RELEASE SAVEPOINT index_operation;

-- Verify that the temporary index does not exist.
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'index_lab'
  AND indexname = 'idx_temporary_customer_city';

-- Demonstrate a transactionally safe maintenance record.
SAVEPOINT audit_operation;

INSERT INTO index_maintenance_events (
    index_name,
    operation,
    details
)
VALUES (
    'idx_events_payload_gin',
    'ANALYZE',
    '{"reason": "post_load_statistics"}'
);

RELEASE SAVEPOINT audit_operation;

-- ============================================================================
-- 18. VALIDATION AND GOVERNANCE QUERIES
-- ============================================================================

-- Invalid indexes.
SELECT
    index_name,
    index_method,
    is_valid,
    is_ready
FROM v_index_inventory
WHERE NOT is_valid OR NOT is_ready;

-- Duplicate-looking index definitions should be reviewed manually.
SELECT
    table_name,
    index_method,
    index_definition,
    COUNT(*) AS definition_count,
    array_agg(index_name) AS index_names
FROM v_index_inventory
GROUP BY
    table_name,
    index_method,
    index_definition
HAVING COUNT(*) > 1;

-- Indexes with no recorded scans.
-- Statistics are cumulative since the last statistics reset.
SELECT
    table_name,
    index_name,
    idx_scan,
    index_size
FROM v_index_usage
WHERE idx_scan = 0
ORDER BY table_name, index_name;

-- Index maintenance history.
SELECT
    index_name,
    operation,
    executed_at,
    details
FROM index_maintenance_log
ORDER BY executed_at DESC;

-- ============================================================================
-- 19. FINAL INDEX INVENTORY
-- ============================================================================

SELECT
    index_method,
    COUNT(*) AS index_count
FROM v_index_inventory
GROUP BY index_method
ORDER BY index_method;

SELECT
    table_name,
    index_name,
    index_method,
    index_size,
    is_unique,
    is_valid
FROM v_index_inventory
ORDER BY table_name, index_method, index_name;

COMMIT;

-- ============================================================================
-- END OF POSTGRESQL INDEX TYPES LABORATORY
-- ============================================================================
