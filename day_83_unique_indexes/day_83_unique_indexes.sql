/*
===============================================================================
UNIQUE INDEXES: ENFORCING UNIQUENESS AND INDEX-BACKED CONSTRAINTS
===============================================================================

PostgreSQL 15+

Demonstrates:
1. Primary keys and unique constraints.
2. Standalone unique indexes.
3. Composite unique indexes.
4. Partial unique indexes.
5. Expression-based unique indexes.
6. Case-insensitive uniqueness.
7. NULLS DISTINCT and NULLS NOT DISTINCT.
8. Deferrable unique constraints.
9. Transaction rollback after uniqueness violations.
10. ON CONFLICT processing.
11. Index inspection and integrity reporting.
12. Query planning and performance evaluation.

The script is designed to be rerunnable.
*/

BEGIN;

DROP SCHEMA IF EXISTS unique_index_lab CASCADE;

CREATE SCHEMA unique_index_lab;

SET search_path TO unique_index_lab, public;

-- ============================================================================
-- 1. CORE RELATIONAL MODEL
-- ============================================================================

CREATE TABLE tenants (
    tenant_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_name VARCHAR(150) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_tenants_name UNIQUE (tenant_name)
);

CREATE TABLE accounts (
    account_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    tenant_id BIGINT NOT NULL
        REFERENCES tenants(tenant_id),

    email VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_accounts_status
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),

    -- Constraint-backed unique index.
    CONSTRAINT uq_accounts_tenant_username
        UNIQUE (tenant_id, username)
);

-- Standalone unique expression index.
-- Case and surrounding spaces are ignored during uniqueness evaluation.
CREATE UNIQUE INDEX uq_accounts_normalized_email
    ON accounts (lower(btrim(email)));

-- Partial unique index.
-- Only ACTIVE accounts must have distinct normalized email addresses.
CREATE UNIQUE INDEX uq_active_accounts_email
    ON accounts (lower(btrim(email)))
    WHERE status = 'ACTIVE';

-- Supporting non-unique index for tenant account retrieval.
CREATE INDEX ix_accounts_tenant_status
    ON accounts (tenant_id, status);

-- ============================================================================
-- 2. NULL SEMANTICS
-- ============================================================================

CREATE TABLE contact_methods (
    contact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    external_reference VARCHAR(100),

    CONSTRAINT uq_contact_external_reference
        UNIQUE NULLS DISTINCT (external_reference)
);

-- NULLS DISTINCT permits multiple NULL values.
-- NULLS NOT DISTINCT treats NULL as one comparable unique value.
CREATE TABLE optional_identifiers (
    identifier_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identifier_code VARCHAR(100),

    CONSTRAINT uq_optional_identifier
        UNIQUE NULLS NOT DISTINCT (identifier_code)
);

-- ============================================================================
-- 3. DEFERRABLE UNIQUE CONSTRAINT
-- ============================================================================

CREATE TABLE ordered_items (
    item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    list_name VARCHAR(100) NOT NULL,
    position INTEGER NOT NULL,

    CONSTRAINT ck_ordered_item_position
        CHECK (position > 0),

    CONSTRAINT uq_ordered_item_position
        UNIQUE (list_name, position)
        DEFERRABLE INITIALLY IMMEDIATE
);

-- ============================================================================
-- 4. SAMPLE DATA
-- ============================================================================

INSERT INTO tenants (tenant_name)
VALUES
    ('Engineering'),
    ('Research'),
    ('Operations');

INSERT INTO accounts (
    tenant_id,
    email,
    username,
    status
)
VALUES
    (1, 'alice@example.com', 'alice', 'ACTIVE'),
    (2, 'bob@example.com', 'alice', 'ACTIVE'),
    (1, 'charlie@example.com', 'charlie', 'ACTIVE'),
    (1, 'archive@example.com', 'archive', 'INACTIVE');

-- Same username is permitted in different tenants.
-- A normalized duplicate email is not permitted, even if case differs.

-- ============================================================================
-- 5. UNIQUENESS VIOLATION EXAMPLES
-- ============================================================================

-- The following operations are intentionally isolated by savepoints.
-- A violation is caught and reported without aborting the entire script.

DO $$
BEGIN
    BEGIN
        INSERT INTO accounts (
            tenant_id, email, username, status
        )
        VALUES (
            3, 'ALICE@EXAMPLE.COM', 'alice_new', 'ACTIVE'
        );

        RAISE EXCEPTION
            'Expected normalized email uniqueness violation was not raised';

    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE
                'Expected result: normalized email duplicate rejected';
    END;

    BEGIN
        INSERT INTO accounts (
            tenant_id, email, username, status
        )
        VALUES (
            1, 'different@example.com', 'alice', 'ACTIVE'
        );

        RAISE EXCEPTION
            'Expected composite uniqueness violation was not raised';

    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE
                'Expected result: duplicate tenant username rejected';
    END;
END;
$$;

-- ============================================================================
-- 6. PARTIAL UNIQUE INDEX WORKFLOW
-- ============================================================================

-- Inactive records are excluded from the partial unique index.
INSERT INTO accounts (
    tenant_id, email, username, status
)
VALUES (
    1, 'alice@example.com', 'alice_archive', 'INACTIVE'
);

-- An active account can now use the email because the previous
-- active account is transitioned to INACTIVE.
UPDATE accounts
SET status = 'INACTIVE'
WHERE tenant_id = 1
  AND username = 'alice';

INSERT INTO accounts (
    tenant_id, email, username, status
)
VALUES (
    3, 'alice@example.com', 'alice_reactivated', 'ACTIVE'
);

-- ============================================================================
-- 7. EXPRESSION INDEX FOR EMAIL NORMALIZATION
-- ============================================================================

CREATE TABLE employee_directory (
    employee_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_name VARCHAR(150) NOT NULL,
    work_email VARCHAR(255) NOT NULL
);

CREATE UNIQUE INDEX uq_employee_normalized_email
    ON employee_directory (
        lower(btrim(work_email))
    );

INSERT INTO employee_directory (employee_name, work_email)
VALUES
    ('Employee One', 'employee.one@example.com'),
    ('Employee Two', 'employee.two@example.com');

DO $$
BEGIN
    BEGIN
        INSERT INTO employee_directory (
            employee_name, work_email
        )
        VALUES (
            'Duplicate Employee', ' EMPLOYEE.ONE@EXAMPLE.COM '
        );

        RAISE EXCEPTION 'Expected expression-index violation';

    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE
                'Expression index rejected normalized duplicate';
    END;
END;
$$;

-- ============================================================================
-- 8. NULL UNIQUENESS BEHAVIOR
-- ============================================================================

INSERT INTO optional_identifiers (identifier_code)
VALUES (NULL);

DO $$
BEGIN
    BEGIN
        INSERT INTO optional_identifiers (identifier_code)
        VALUES (NULL);

        RAISE EXCEPTION 'Expected NULLS NOT DISTINCT violation';

    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE
                'NULLS NOT DISTINCT rejected the second NULL';
    END;
END;
$$;

INSERT INTO contact_methods (account_id, external_reference)
VALUES
    (1, NULL),
    (2, NULL),
    (3, 'EXT-100'),
    (4, 'EXT-200');

-- Multiple NULL values are permitted by NULLS DISTINCT.

-- ============================================================================
-- 9. DEFERRABLE CONSTRAINT PROCESSING
-- ============================================================================

INSERT INTO ordered_items (list_name, position)
VALUES
    ('Priority Queue', 1),
    ('Priority Queue', 2),
    ('Priority Queue', 3);

-- Temporary duplicates are allowed inside the transaction.
-- The final transaction state must satisfy the unique constraint.

BEGIN;

SET CONSTRAINTS uq_ordered_item_position DEFERRED;

UPDATE ordered_items
SET position = CASE position
    WHEN 1 THEN 2
    WHEN 2 THEN 3
    WHEN 3 THEN 1
END
WHERE list_name = 'Priority Queue';

SET CONSTRAINTS uq_ordered_item_position IMMEDIATE;

COMMIT;

-- ============================================================================
-- 10. ATOMIC INSERT AND ON CONFLICT
-- ============================================================================

INSERT INTO accounts (
    tenant_id, email, username, status
)
VALUES (
    2, 'bob@example.com', 'bob_new', 'ACTIVE'
)
ON CONFLICT DO NOTHING;

-- A targeted expression-index conflict can be handled through inference.
INSERT INTO accounts (
    tenant_id, email, username, status
)
VALUES (
    3, 'BOB@EXAMPLE.COM', 'bob_second', 'ACTIVE'
)
ON CONFLICT (lower(btrim(email)))
DO NOTHING;

-- The following statement updates an existing matching account.
INSERT INTO employee_directory (
    employee_name, work_email
)
VALUES (
    'Employee One Updated', 'EMPLOYEE.ONE@EXAMPLE.COM'
)
ON CONFLICT (lower(btrim(work_email)))
DO UPDATE
SET employee_name = EXCLUDED.employee_name;

-- ============================================================================
-- 11. INDEX-BACKED CONSTRAINT INSPECTION
-- ============================================================================

-- Constraint-backed indexes can be inspected through PostgreSQL catalogs.
SELECT
    constraint_name,
    constraint_type,
    table_name
FROM information_schema.table_constraints
WHERE constraint_schema = 'unique_index_lab'
ORDER BY table_name, constraint_name;

-- Inspect all indexes in the demonstration schema.
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'unique_index_lab'
ORDER BY tablename, indexname;

-- Inspect index validity, uniqueness and readiness.
SELECT
    index_class.relname AS index_name,
    table_class.relname AS table_name,
    index_metadata.indisunique AS is_unique,
    index_metadata.indisvalid AS is_valid,
    index_metadata.indisready AS is_ready,
    pg_size_pretty(
        pg_relation_size(index_class.oid)
    ) AS index_size
FROM pg_index AS index_metadata
JOIN pg_class AS index_class
    ON index_class.oid = index_metadata.indexrelid
JOIN pg_class AS table_class
    ON table_class.oid = index_metadata.indrelid
JOIN pg_namespace AS namespace
    ON namespace.oid = table_class.relnamespace
WHERE namespace.nspname = 'unique_index_lab'
ORDER BY table_name, index_name;

-- ============================================================================
-- 12. UNIQUENESS VALIDATION REPORT
-- ============================================================================

CREATE OR REPLACE VIEW account_uniqueness_report AS
SELECT
    account_id,
    tenant_id,
    email,
    username,
    status,
    lower(btrim(email)) AS normalized_email,
    COUNT(*) OVER (
        PARTITION BY lower(btrim(email))
    ) AS global_email_count,
    COUNT(*) OVER (
        PARTITION BY tenant_id, lower(btrim(username))
    ) AS tenant_username_count,
    COUNT(*) FILTER (
        WHERE status = 'ACTIVE'
    ) OVER (
        PARTITION BY lower(btrim(email))
    ) AS active_email_count
FROM accounts;

SELECT *
FROM account_uniqueness_report
ORDER BY account_id;

-- ============================================================================
-- 13. FUNCTION: CHECK EMAIL AVAILABILITY
-- ============================================================================

CREATE OR REPLACE FUNCTION is_email_available(
    p_email VARCHAR,
    p_excluded_account_id BIGINT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
AS $$
    SELECT NOT EXISTS (
        SELECT 1
        FROM accounts
        WHERE lower(btrim(email)) = lower(btrim(p_email))
          AND (
              p_excluded_account_id IS NULL
              OR account_id <> p_excluded_account_id
          )
    );
$$;

SELECT
    is_email_available('new@example.com') AS new_email_available,
    is_email_available('alice@example.com') AS existing_email_available,
    is_email_available('alice@example.com', 1)
        AS existing_owner_excluded;

-- Availability checks are informational.
-- Concurrent writes must still rely on the unique index itself.

-- ============================================================================
-- 14. FUNCTION: CREATE ACCOUNT SAFELY
-- ============================================================================

CREATE OR REPLACE FUNCTION create_account(
    p_tenant_id BIGINT,
    p_email VARCHAR,
    p_username VARCHAR
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_account_id BIGINT;
BEGIN
    IF p_email IS NULL OR position('@' IN p_email) = 0 THEN
        RAISE EXCEPTION 'Invalid email address'
            USING ERRCODE = '22023';
    END IF;

    IF p_username IS NULL OR btrim(p_username) = '' THEN
        RAISE EXCEPTION 'Username cannot be empty'
            USING ERRCODE = '22023';
    END IF;

    INSERT INTO accounts (
        tenant_id,
        email,
        username,
        status
    )
    VALUES (
        p_tenant_id,
        btrim(p_email),
        btrim(p_username),
        'ACTIVE'
    )
    RETURNING account_id INTO v_account_id;

    RETURN v_account_id;

EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION
            'Account conflicts with an existing unique index or constraint'
            USING ERRCODE = '23505';
END;
$$;

-- ============================================================================
-- 15. PROCEDURE: ACCOUNT UNIQUENESS AUDIT
-- ============================================================================

CREATE OR REPLACE PROCEDURE audit_account_uniqueness()
LANGUAGE plpgsql
AS $$
DECLARE
    v_duplicate_count BIGINT;
BEGIN
    SELECT COUNT(*)
    INTO v_duplicate_count
    FROM (
        SELECT lower(btrim(email))
        FROM accounts
        GROUP BY lower(btrim(email))
        HAVING COUNT(*) > 1
    ) AS duplicate_groups;

    RAISE NOTICE
        'Global normalized email duplicate groups: %',
        v_duplicate_count;

    SELECT COUNT(*)
    INTO v_duplicate_count
    FROM (
        SELECT tenant_id, lower(btrim(username))
        FROM accounts
        GROUP BY tenant_id, lower(btrim(username))
        HAVING COUNT(*) > 1
    ) AS duplicate_groups;

    RAISE NOTICE
        'Composite username duplicate groups: %',
        v_duplicate_count;

    SELECT COUNT(*)
    INTO v_duplicate_count
    FROM (
        SELECT lower(btrim(email))
        FROM accounts
        WHERE status = 'ACTIVE'
        GROUP BY lower(btrim(email))
        HAVING COUNT(*) > 1
    ) AS duplicate_groups;

    RAISE NOTICE
        'Active email duplicate groups: %',
        v_duplicate_count;
END;
$$;

CALL audit_account_uniqueness();

-- ============================================================================
-- 16. RETRIEVAL AND AGGREGATION
-- ============================================================================

-- Retrieve all accounts for a tenant.
SELECT
    account_id,
    email,
    username,
    status
FROM accounts
WHERE tenant_id = 1
ORDER BY username;

-- Aggregate account counts by tenant and status.
SELECT
    t.tenant_name,
    a.status,
    COUNT(a.account_id) AS account_count
FROM tenants AS t
LEFT JOIN accounts AS a
    ON a.tenant_id = t.tenant_id
GROUP BY t.tenant_id, t.tenant_name, a.status
ORDER BY t.tenant_name, a.status;

-- Identify active email groups.
SELECT
    lower(btrim(email)) AS normalized_email,
    COUNT(*) AS active_accounts
FROM accounts
WHERE status = 'ACTIVE'
GROUP BY lower(btrim(email))
ORDER BY normalized_email;

-- ============================================================================
-- 17. QUERY PLANNING
-- ============================================================================

-- A matching expression index can support this predicate.
EXPLAIN (ANALYZE, BUFFERS)
SELECT account_id, email
FROM accounts
WHERE lower(btrim(email)) = 'alice@example.com';

-- The composite index supports equality filtering on tenant_id
-- and username together.
EXPLAIN (ANALYZE, BUFFERS)
SELECT account_id
FROM accounts
WHERE tenant_id = 1
  AND username = 'alice';

-- The partial index is applicable when the predicate is included.
EXPLAIN (ANALYZE, BUFFERS)
SELECT account_id
FROM accounts
WHERE lower(btrim(email)) = 'alice@example.com'
  AND status = 'ACTIVE';

-- ============================================================================
-- 18. TRANSACTIONAL FAILURE DEMONSTRATION
-- ============================================================================

DO $$
BEGIN
    BEGIN
        INSERT INTO accounts (
            tenant_id, email, username, status
        )
        VALUES (
            1, 'transaction@example.com', 'transaction_user', 'ACTIVE'
        );

        INSERT INTO accounts (
            tenant_id, email, username, status
        )
        VALUES (
            2, 'TRANSACTION@EXAMPLE.COM', 'transaction_user_2', 'ACTIVE'
        );

        RAISE NOTICE 'Unexpected success';

    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE
                'Transaction sub-block rolled back after uniqueness conflict';
    END;
END;
$$;

-- The first insert inside the failed subtransaction was rolled back.

SELECT *
FROM accounts
WHERE lower(btrim(email)) = 'transaction@example.com';

-- ============================================================================
-- 19. OPERATIONAL GUIDANCE
-- ============================================================================

-- For production systems, large indexes may be built concurrently:
--
-- CREATE UNIQUE INDEX CONCURRENTLY uq_example_email
-- ON some_schema.some_table (lower(btrim(email)));
--
-- CREATE INDEX CONCURRENTLY cannot execute inside a transaction block.
-- It must be run as a separate top-level command.
--
-- Before creating a unique index on an existing large table:
-- 1. Identify and resolve duplicate keys.
-- 2. Validate the intended NULL semantics.
-- 3. Confirm the expression and collation.
-- 4. Assess write-lock and storage requirements.
-- 5. Monitor invalid indexes after failed concurrent builds.
--
-- A unique index prevents concurrent duplicate insertion at the
-- database level. Application-level prechecks alone do not.

COMMIT;
