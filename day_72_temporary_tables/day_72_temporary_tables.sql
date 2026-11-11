/*
 * TEMPORARY TABLES
 * PostgreSQL session scope, staging, validation and promotion.
 *
 * Execute the entire script in one database session.
 * Recommended:
 * psql -X -v ON_ERROR_STOP=1 -d your_database -f temporary_tables.sql
 *
 * Permanent objects:
 *   temp_demo.products
 *   temp_demo.import_batches
 *   temp_demo.import_audit
 *
 * Session-local objects:
 *   pg_temp.staging_products
 *   pg_temp.staging_validation
 *
 * Temporary tables are connection-specific and disappear when
 * the database session ends.
 */

BEGIN;

CREATE SCHEMA IF NOT EXISTS temp_demo;

CREATE TABLE IF NOT EXISTS temp_demo.products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(150) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(14, 2) NOT NULL
        CHECK (unit_price >= 0),
    total_value NUMERIC(18, 2)
        GENERATED ALWAYS AS (quantity * unit_price) STORED,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS temp_demo.import_batches (
    batch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_name VARCHAR(100) NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    batch_status VARCHAR(20) NOT NULL DEFAULT 'CREATED'
        CHECK (
            batch_status IN (
                'CREATED',
                'LOADED',
                'VALIDATED',
                'PROMOTED',
                'FAILED'
            )
        ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS temp_demo.import_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_id BIGINT NOT NULL
        REFERENCES temp_demo.import_batches(batch_id),
    external_id VARCHAR(50),
    outcome VARCHAR(20) NOT NULL
        CHECK (outcome IN ('ACCEPTED', 'REJECTED', 'PROMOTED')),
    reason TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_name
    ON temp_demo.products(product_name);

CREATE INDEX IF NOT EXISTS idx_import_batches_status
    ON temp_demo.import_batches(batch_status);

CREATE INDEX IF NOT EXISTS idx_import_audit_batch
    ON temp_demo.import_audit(batch_id, recorded_at DESC);

COMMIT;


/* ---------------------------------------------------------
   1. Create temporary tables.
   --------------------------------------------------------- */

/*
 * ON COMMIT PRESERVE ROWS is PostgreSQL's default.
 * Explicitly specifying it documents the intended lifecycle.
 *
 * The tables remain available after COMMIT but only within
 * the current database session.
 */

CREATE TEMP TABLE staging_products (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id VARCHAR(50),
    product_name VARCHAR(150),
    quantity INTEGER,
    unit_price NUMERIC(14, 2),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
) ON COMMIT PRESERVE ROWS;

CREATE INDEX idx_staging_external_id
    ON staging_products(external_id);

CREATE TEMP TABLE staging_validation (
    staging_id BIGINT PRIMARY KEY
        REFERENCES staging_products(staging_id)
        ON DELETE CASCADE,
    validation_status VARCHAR(20) NOT NULL
        CHECK (
            validation_status IN ('ACCEPTED', 'REJECTED')
        ),
    rejection_reason TEXT NOT NULL
) ON COMMIT PRESERVE ROWS;


/* ---------------------------------------------------------
   2. Create an import batch.
   --------------------------------------------------------- */

INSERT INTO temp_demo.import_batches (
    batch_name,
    source_name
)
VALUES (
    'November Inventory Import',
    'inventory_november.csv'
)
RETURNING batch_id;


/*
 * The demonstration uses a known batch identifier of 1 when
 * the schema is first initialized. To keep repeated executions
 * safe, retrieve the latest matching batch through a CTE.
 */

INSERT INTO staging_products (
    external_id,
    product_name,
    quantity,
    unit_price
)
VALUES
    ('P1001', 'Laptop', 5, 75000.00),
    ('P1002', 'Monitor', 10, 12000.00),
    ('P1003', 'Keyboard', 20, 1500.00),
    ('P1001', 'Duplicate Laptop', 2, 70000.00),
    ('P1004', 'Invalid Quantity', 0, 500.00),
    ('P1005', 'Invalid Price', 2, -100.00),
    ('P1006', 'Missing Name', 4, 500.00),
    ('P1007', 'Invalid Identifier', 1, 500.00);

UPDATE staging_products
SET external_id = NULL
WHERE product_name = 'Invalid Identifier';

UPDATE staging_products
SET product_name = NULL
WHERE product_name = 'Missing Name';


/* ---------------------------------------------------------
   3. Validate the staging batch.
   --------------------------------------------------------- */

/*
 * ROW_NUMBER identifies repeated identifiers without deleting
 * original input rows.
 *
 * Existing permanent identifiers are also rejected.
 */

INSERT INTO staging_validation (
    staging_id,
    validation_status,
    rejection_reason
)
WITH ranked AS (
    SELECT
        s.staging_id,
        s.external_id,
        s.product_name,
        s.quantity,
        s.unit_price,
        ROW_NUMBER() OVER (
            PARTITION BY s.external_id
            ORDER BY s.staging_id
        ) AS duplicate_rank
    FROM staging_products s
),
evaluated AS (
    SELECT
        r.staging_id,
        CASE
            WHEN r.external_id IS NULL
                OR BTRIM(r.external_id) = ''
                THEN 'Missing external identifier'

            WHEN r.product_name IS NULL
                OR BTRIM(r.product_name) = ''
                THEN 'Missing product name'

            WHEN r.duplicate_rank > 1
                THEN 'Duplicate identifier in staging batch'

            WHEN EXISTS (
                SELECT 1
                FROM temp_demo.products p
                WHERE p.external_id = r.external_id
            )
                THEN 'Identifier already exists permanently'

            WHEN r.quantity IS NULL OR r.quantity <= 0
                THEN 'Quantity must be positive'

            WHEN r.unit_price IS NULL OR r.unit_price < 0
                THEN 'Unit price cannot be negative'

            ELSE 'Valid record'
        END AS reason
    FROM ranked r
)
SELECT
    staging_id,
    CASE
        WHEN reason = 'Valid record' THEN 'ACCEPTED'
        ELSE 'REJECTED'
    END,
    reason
FROM evaluated;


/* ---------------------------------------------------------
   4. Inspect validation results.
   --------------------------------------------------------- */

SELECT
    s.staging_id,
    s.external_id,
    s.product_name,
    s.quantity,
    s.unit_price,
    v.validation_status,
    v.rejection_reason
FROM staging_products s
JOIN staging_validation v
    ON v.staging_id = s.staging_id
ORDER BY s.staging_id;


/* Validation aggregation. */

SELECT
    validation_status,
    COUNT(*) AS total_records
FROM staging_validation
GROUP BY validation_status
ORDER BY validation_status;


/* ---------------------------------------------------------
   5. Record validation audit.
   --------------------------------------------------------- */

WITH current_batch AS (
    SELECT batch_id
    FROM temp_demo.import_batches
    WHERE batch_name = 'November Inventory Import'
      AND source_name = 'inventory_november.csv'
    ORDER BY batch_id DESC
    LIMIT 1
)
INSERT INTO temp_demo.import_audit (
    batch_id,
    external_id,
    outcome,
    reason
)
SELECT
    b.batch_id,
    s.external_id,
    v.validation_status,
    v.rejection_reason
FROM staging_products s
JOIN staging_validation v
    ON v.staging_id = s.staging_id
CROSS JOIN current_batch b;


/* ---------------------------------------------------------
   6. Promote accepted rows transactionally.
   --------------------------------------------------------- */

/*
 * Only accepted rows enter the permanent table.
 *
 * The permanent UNIQUE constraint remains the final protection
 * against duplicate identifiers.
 *
 * The validation decision and insertion occur within one
 * transaction to avoid partial promotion.
 */

BEGIN;

SAVEPOINT promotion_savepoint;

INSERT INTO temp_demo.products (
    external_id,
    product_name,
    quantity,
    unit_price
)
SELECT
    s.external_id,
    s.product_name,
    s.quantity,
    s.unit_price
FROM staging_products s
JOIN staging_validation v
    ON v.staging_id = s.staging_id
WHERE v.validation_status = 'ACCEPTED'
ON CONFLICT (external_id) DO NOTHING;

WITH current_batch AS (
    SELECT batch_id
    FROM temp_demo.import_batches
    WHERE batch_name = 'November Inventory Import'
      AND source_name = 'inventory_november.csv'
    ORDER BY batch_id DESC
    LIMIT 1
)
INSERT INTO temp_demo.import_audit (
    batch_id,
    external_id,
    outcome,
    reason
)
SELECT
    b.batch_id,
    s.external_id,
    'PROMOTED',
    'Successfully inserted into permanent products'
FROM staging_products s
JOIN staging_validation v
    ON v.staging_id = s.staging_id
CROSS JOIN current_batch b
WHERE v.validation_status = 'ACCEPTED'
  AND EXISTS (
      SELECT 1
      FROM temp_demo.products p
      WHERE p.external_id = s.external_id
  );

UPDATE temp_demo.import_batches
SET
    batch_status = 'PROMOTED',
    completed_at = CURRENT_TIMESTAMP
WHERE batch_id = (
    SELECT batch_id
    FROM temp_demo.import_batches
    WHERE batch_name = 'November Inventory Import'
      AND source_name = 'inventory_november.csv'
    ORDER BY batch_id DESC
    LIMIT 1
);

RELEASE SAVEPOINT promotion_savepoint;

COMMIT;


/* ---------------------------------------------------------
   7. Permanent data retrieval and reporting.
   --------------------------------------------------------- */

SELECT
    product_id,
    external_id,
    product_name,
    quantity,
    unit_price,
    total_value,
    imported_at
FROM temp_demo.products
ORDER BY product_id;


/* Aggregated inventory valuation. */

SELECT
    COUNT(*) AS total_products,
    SUM(quantity) AS total_units,
    SUM(total_value) AS total_inventory_value,
    AVG(unit_price) AS average_unit_price
FROM temp_demo.products;


/* Audit report. */

SELECT
    batch_id,
    outcome,
    COUNT(*) AS record_count
FROM temp_demo.import_audit
GROUP BY batch_id, outcome
ORDER BY batch_id, outcome;


/* ---------------------------------------------------------
   8. Reusable temporary-table validation function.
   --------------------------------------------------------- */

/*
 * This function validates an existing session-local staging
 * table. It demonstrates PL/pgSQL and exception handling.
 */

CREATE OR REPLACE FUNCTION pg_temp.staging_summary()
RETURNS TABLE (
    validation_status TEXT,
    record_count BIGINT
)
LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        v.validation_status::TEXT,
        COUNT(*)::BIGINT
    FROM staging_validation v
    GROUP BY v.validation_status
    ORDER BY v.validation_status;
EXCEPTION
    WHEN undefined_table THEN
        RAISE EXCEPTION
            'Required temporary staging table does not exist';
END;
$function$;

SELECT * FROM pg_temp.staging_summary();


/* ---------------------------------------------------------
   9. Reusable promotion procedure.
   --------------------------------------------------------- */

CREATE OR REPLACE PROCEDURE pg_temp.promote_staging()
LANGUAGE plpgsql
AS $procedure$
DECLARE
    inserted_count BIGINT;
BEGIN
    INSERT INTO temp_demo.products (
        external_id,
        product_name,
        quantity,
        unit_price
    )
    SELECT
        s.external_id,
        s.product_name,
        s.quantity,
        s.unit_price
    FROM staging_products s
    JOIN staging_validation v
        ON v.staging_id = s.staging_id
    WHERE v.validation_status = 'ACCEPTED'
    ON CONFLICT (external_id) DO NOTHING;

    GET DIAGNOSTICS inserted_count = ROW_COUNT;

    RAISE NOTICE
        'Records inserted by procedure: %',
        inserted_count;
END;
$procedure$;


/* ---------------------------------------------------------
   10. Demonstrate ON COMMIT DELETE ROWS.
   --------------------------------------------------------- */

/*
 * This is a separate temporary table with a different lifecycle.
 * Its definition survives COMMIT, but its contents do not.
 */

CREATE TEMP TABLE session_work_area (
    work_id BIGINT GENERATED ALWAYS AS IDENTITY,
    description TEXT NOT NULL
) ON COMMIT DELETE ROWS;

BEGIN;

INSERT INTO session_work_area(description)
VALUES
    ('Temporary transformation'),
    ('Intermediate aggregation');

SELECT * FROM session_work_area;

COMMIT;

/* The table exists but its rows have been removed. */

SELECT COUNT(*) AS remaining_work_rows
FROM session_work_area;


/* ---------------------------------------------------------
   11. Demonstrate ON COMMIT DROP.
   --------------------------------------------------------- */

/*
 * This table is removed automatically when its transaction commits.
 */

BEGIN;

CREATE TEMP TABLE transaction_work_area (
    work_id INTEGER,
    description TEXT
) ON COMMIT DROP;

INSERT INTO transaction_work_area
VALUES (1, 'Single transaction calculation');

SELECT * FROM transaction_work_area;

COMMIT;


/* ---------------------------------------------------------
   12. Session-level cleanup.
   --------------------------------------------------------- */

/*
 * DROP TABLE removes the temporary table definition and data.
 * It does not affect permanent tables.
 */

DROP TABLE IF EXISTS
    session_work_area,
    staging_validation,
    staging_products;

DROP FUNCTION IF EXISTS pg_temp.staging_summary();

DROP PROCEDURE IF EXISTS pg_temp.promote_staging();


/* ---------------------------------------------------------
   13. Permanent reporting view.
   --------------------------------------------------------- */

CREATE OR REPLACE VIEW temp_demo.inventory_report AS
SELECT
    product_id,
    external_id,
    product_name,
    quantity,
    unit_price,
    total_value,
    imported_at
FROM temp_demo.products;

SELECT * FROM temp_demo.inventory_report;


/*
 * IMPORTANT LIFECYCLE DISTINCTIONS
 *
 * ON COMMIT PRESERVE ROWS:
 *   Table and data survive transaction commits.
 *   Both disappear when the session ends.
 *
 * ON COMMIT DELETE ROWS:
 *   Table survives commits; data is deleted.
 *
 * ON COMMIT DROP:
 *   Table and data disappear at transaction commit.
 *
 * TEMP tables:
 *   Are isolated by database session.
 *   Do not provide cross-session shared staging.
 *   Can shadow permanent tables of the same unqualified name.
 *
 * Explicitly qualify permanent objects with their schema.
 */
