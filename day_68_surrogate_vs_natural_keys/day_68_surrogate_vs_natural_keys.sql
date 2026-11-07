-- ============================================================
-- SURROGATE VS NATURAL KEYS
-- PostgreSQL implementation
-- Requires PostgreSQL 13 or later.
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS key_design;

SET search_path TO key_design, public;

-- ============================================================
-- 1. SEQUENCE-BASED IDENTIFIERS
-- ============================================================

-- An explicit sequence can be shared or customized independently
-- of an identity column.

CREATE SEQUENCE IF NOT EXISTS customer_reference_seq
    START WITH 10001
    INCREMENT BY 1
    MINVALUE 1
    CACHE 50
    NO CYCLE;

-- ============================================================
-- 2. CUSTOMER TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY
        (START WITH 1 INCREMENT BY 1)
        PRIMARY KEY,

    public_id UUID NOT NULL DEFAULT gen_random_uuid(),

    email VARCHAR(254) NOT NULL,

    full_name VARCHAR(150) NOT NULL,

    country_code CHAR(2) NOT NULL,

    external_reference VARCHAR(80),

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_customer_public_id UNIQUE (public_id),

    CONSTRAINT uq_customer_email UNIQUE (email),

    CONSTRAINT uq_customer_external_reference
        UNIQUE (external_reference),

    CONSTRAINT chk_customer_email
        CHECK (
            email = lower(trim(email))
            AND email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
        ),

    CONSTRAINT chk_customer_country
        CHECK (country_code ~ '^[A-Z]{2}$'),

    CONSTRAINT chk_customer_name
        CHECK (length(trim(full_name)) > 0),

    CONSTRAINT chk_customer_status
        CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CLOSED'))
);

-- ============================================================
-- 3. NATURAL IDENTIFIER TABLE
-- ============================================================

-- Country + business identifier forms a composite natural key.
-- The same identifier can exist in different countries.

CREATE TABLE IF NOT EXISTS business_registrations (
    country_code CHAR(2) NOT NULL,

    registration_number VARCHAR(40) NOT NULL,

    business_name VARCHAR(150) NOT NULL,

    registration_date DATE NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_business_registration
        PRIMARY KEY (country_code, registration_number),

    CONSTRAINT chk_registration_country
        CHECK (country_code ~ '^[A-Z]{2}$'),

    CONSTRAINT chk_registration_number
        CHECK (registration_number ~ '^[A-Za-z0-9-]{4,40}$'),

    CONSTRAINT chk_business_name
        CHECK (length(trim(business_name)) > 0)
);

-- ============================================================
-- 4. CUSTOMER REGISTRATION MAPPING
-- ============================================================

-- A surrogate primary key is used for the relationship.
-- Natural business identifiers remain independently constrained.

CREATE TABLE IF NOT EXISTS customer_business_registrations (
    mapping_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    customer_id BIGINT NOT NULL,

    country_code CHAR(2) NOT NULL,

    registration_number VARCHAR(40) NOT NULL,

    linked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_mapping_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_mapping_registration
        FOREIGN KEY (country_code, registration_number)
        REFERENCES business_registrations(
            country_code,
            registration_number
        )
        ON DELETE RESTRICT,

    CONSTRAINT uq_customer_registration
        UNIQUE (
            customer_id,
            country_code,
            registration_number
        )
);

-- ============================================================
-- 5. EXPLICIT SEQUENCE-BASED ORDER REFERENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    order_reference BIGINT NOT NULL
        DEFAULT nextval('key_design.customer_reference_seq'),

    customer_id BIGINT NOT NULL,

    amount NUMERIC(14, 2) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'CREATED',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_order_reference UNIQUE (order_reference),

    CONSTRAINT fk_order_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_order_amount
        CHECK (amount > 0),

    CONSTRAINT chk_order_status
        CHECK (
            status IN (
                'CREATED',
                'CONFIRMED',
                'CANCELLED'
            )
        )
);

-- ============================================================
-- 6. AUDIT TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS customer_identifier_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    customer_id BIGINT NOT NULL,

    old_email VARCHAR(254),

    new_email VARCHAR(254),

    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT
);

-- ============================================================
-- 7. INDEXES
-- ============================================================

-- Primary key and unique constraints create their own indexes.
-- These additional indexes support foreign-key joins and reports.

CREATE INDEX IF NOT EXISTS idx_customers_status
    ON customers(status);

CREATE INDEX IF NOT EXISTS idx_customers_created_at
    ON customers(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_customer_created
    ON orders(customer_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_status
    ON orders(status);

CREATE INDEX IF NOT EXISTS idx_registration_business_name
    ON business_registrations(business_name);

CREATE INDEX IF NOT EXISTS idx_customer_registration_customer
    ON customer_business_registrations(customer_id);

-- ============================================================
-- 8. AUTOMATIC UPDATED TIMESTAMP
-- ============================================================

CREATE OR REPLACE FUNCTION update_customer_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_customer_timestamp ON customers;

CREATE TRIGGER trg_customer_timestamp
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_customer_timestamp();

-- ============================================================
-- 9. EMAIL CHANGE AUDIT
-- ============================================================

CREATE OR REPLACE FUNCTION audit_customer_email_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.email IS DISTINCT FROM NEW.email THEN
        INSERT INTO customer_identifier_audit (
            customer_id,
            old_email,
            new_email
        )
        VALUES (
            OLD.customer_id,
            OLD.email,
            NEW.email
        );
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_customer_email_audit ON customers;

CREATE TRIGGER trg_customer_email_audit
AFTER UPDATE OF email ON customers
FOR EACH ROW
EXECUTE FUNCTION audit_customer_email_change();

-- ============================================================
-- 10. CUSTOMER CREATION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION register_customer(
    p_email VARCHAR,
    p_full_name VARCHAR,
    p_country_code CHAR(2)
)
RETURNS TABLE (
    generated_customer_id BIGINT,
    generated_public_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_customer_id BIGINT;
    v_public_id UUID;
BEGIN
    IF p_email IS NULL OR
       p_email !~* '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
    THEN
        RAISE EXCEPTION 'Invalid email address';
    END IF;

    IF p_full_name IS NULL OR length(trim(p_full_name)) = 0 THEN
        RAISE EXCEPTION 'Customer name is required';
    END IF;

    IF p_country_code IS NULL OR
       p_country_code !~ '^[A-Za-z]{2}$'
    THEN
        RAISE EXCEPTION 'Invalid country code';
    END IF;

    INSERT INTO customers (
        email,
        full_name,
        country_code
    )
    VALUES (
        lower(trim(p_email)),
        trim(p_full_name),
        upper(p_country_code)
    )
    RETURNING customer_id, public_id
    INTO v_customer_id, v_public_id;

    RETURN QUERY
    SELECT v_customer_id, v_public_id;
END;
$$;

-- ============================================================
-- 11. ORDER CREATION PROCEDURE
-- ============================================================

CREATE OR REPLACE PROCEDURE create_customer_order(
    p_customer_id BIGINT,
    p_amount NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status VARCHAR(20);
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Order amount must be positive';
    END IF;

    SELECT status
    INTO v_status
    FROM customers
    WHERE customer_id = p_customer_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Customer % does not exist', p_customer_id;
    END IF;

    IF v_status <> 'ACTIVE' THEN
        RAISE EXCEPTION 'Customer is not active';
    END IF;

    INSERT INTO orders (
        customer_id,
        amount
    )
    VALUES (
        p_customer_id,
        p_amount
    );
END;
$$;

-- ============================================================
-- 12. SAMPLE CUSTOMER RECORDS
-- ============================================================

INSERT INTO customers (
    email,
    full_name,
    country_code,
    external_reference,
    status
)
VALUES
(
    'alice@example.com',
    'Alice Sharma',
    'IN',
    'ERP-CUST-1001',
    'ACTIVE'
),
(
    'bob@example.com',
    'Bob Verma',
    'IN',
    'ERP-CUST-1002',
    'ACTIVE'
),
(
    'charlie@example.com',
    'Charlie Smith',
    'US',
    'ERP-CUST-1003',
    'SUSPENDED'
)
ON CONFLICT (email) DO NOTHING;

-- ============================================================
-- 13. NATURAL IDENTIFIER RECORDS
-- ============================================================

INSERT INTO business_registrations (
    country_code,
    registration_number,
    business_name,
    registration_date
)
VALUES
(
    'IN',
    'TAX-1001',
    'Indian Enterprise',
    DATE '2024-01-15'
),
(
    'US',
    'TAX-1001',
    'American Enterprise',
    DATE '2024-02-20'
),
(
    'IN',
    'TAX-1002',
    'Second Indian Enterprise',
    DATE '2024-03-10'
)
ON CONFLICT (
    country_code,
    registration_number
) DO NOTHING;

-- ============================================================
-- 14. LINK CUSTOMERS TO NATURAL IDENTIFIERS
-- ============================================================

INSERT INTO customer_business_registrations (
    customer_id,
    country_code,
    registration_number
)
SELECT
    c.customer_id,
    b.country_code,
    b.registration_number
FROM customers c
JOIN business_registrations b
    ON (
        c.country_code = b.country_code
        AND (
            (c.email = 'alice@example.com'
                AND b.registration_number = 'TAX-1001')
            OR
            (c.email = 'bob@example.com'
                AND b.registration_number = 'TAX-1002')
        )
    )
ON CONFLICT (
    customer_id,
    country_code,
    registration_number
) DO NOTHING;

-- ============================================================
-- 15. SAMPLE ORDERS
-- ============================================================

INSERT INTO orders (
    customer_id,
    amount,
    status
)
SELECT
    customer_id,
    25000.00,
    'CONFIRMED'
FROM customers
WHERE email = 'alice@example.com'
AND NOT EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.customer_id = customers.customer_id
);

INSERT INTO orders (
    customer_id,
    amount,
    status
)
SELECT
    customer_id,
    45000.00,
    'CREATED'
FROM customers
WHERE email = 'bob@example.com'
AND NOT EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.customer_id = customers.customer_id
);

-- ============================================================
-- 16. UUID AND IDENTITY RETRIEVAL
-- ============================================================

SELECT
    customer_id,
    public_id,
    email,
    full_name
FROM customers
ORDER BY customer_id;

-- ============================================================
-- 17. NATURAL KEY RETRIEVAL
-- ============================================================

SELECT
    country_code,
    registration_number,
    business_name
FROM business_registrations
WHERE country_code = 'IN'
AND registration_number = 'TAX-1001';

-- ============================================================
-- 18. COMPOSITE NATURAL KEY COMPARISON
-- ============================================================

SELECT
    country_code,
    registration_number,
    COUNT(*) AS matching_records
FROM business_registrations
GROUP BY
    country_code,
    registration_number
ORDER BY
    country_code,
    registration_number;

-- ============================================================
-- 19. SURROGATE FOREIGN KEY RELATIONSHIPS
-- ============================================================

SELECT
    o.order_id,
    o.order_reference,
    c.customer_id,
    c.public_id,
    c.full_name,
    o.amount,
    o.status
FROM orders o
JOIN customers c
    ON c.customer_id = o.customer_id
ORDER BY o.order_id;

-- ============================================================
-- 20. NATURAL IDENTIFIER AND SURROGATE JOIN
-- ============================================================

SELECT
    c.customer_id,
    c.public_id,
    c.full_name,
    b.country_code,
    b.registration_number,
    b.business_name
FROM customer_business_registrations mapping
JOIN customers c
    ON c.customer_id = mapping.customer_id
JOIN business_registrations b
    ON b.country_code = mapping.country_code
    AND b.registration_number = mapping.registration_number;

-- ============================================================
-- 21. AGGREGATION AND EVALUATION
-- ============================================================

SELECT
    c.status,
    COUNT(DISTINCT c.customer_id) AS customer_count,
    COUNT(o.order_id) AS order_count,
    COALESCE(SUM(o.amount), 0) AS total_order_value
FROM customers c
LEFT JOIN orders o
    ON o.customer_id = c.customer_id
GROUP BY c.status
ORDER BY c.status;

-- ============================================================
-- 22. KEY UNIQUENESS VALIDATION
-- ============================================================

SELECT
    email,
    COUNT(*) AS occurrences
FROM customers
GROUP BY email
HAVING COUNT(*) > 1;

SELECT
    public_id,
    COUNT(*) AS occurrences
FROM customers
GROUP BY public_id
HAVING COUNT(*) > 1;

SELECT
    country_code,
    registration_number,
    COUNT(*) AS occurrences
FROM business_registrations
GROUP BY country_code, registration_number
HAVING COUNT(*) > 1;

-- These queries should return no rows when constraints are valid.

-- ============================================================
-- 23. IDENTITY AND SEQUENCE INSPECTION
-- ============================================================

SELECT
    column_name,
    data_type,
    is_identity,
    identity_generation
FROM information_schema.columns
WHERE table_schema = 'key_design'
AND table_name = 'customers'
AND column_name = 'customer_id';

SELECT
    last_value,
    increment_by,
    cache_size,
    cycle
FROM key_design.customer_reference_seq;

-- ============================================================
-- 24. UUID UNIQUENESS VALIDATION
-- ============================================================

SELECT
    public_id,
    COUNT(*)
FROM customers
GROUP BY public_id
HAVING COUNT(*) > 1;

-- UUIDs are identifiers, not authorization credentials.
-- Access control must still be enforced independently.

-- ============================================================
-- 25. VIEWS
-- ============================================================

CREATE OR REPLACE VIEW customer_key_report AS
SELECT
    c.customer_id,
    c.public_id,
    c.email,
    c.full_name,
    c.country_code,
    c.status,
    COUNT(DISTINCT o.order_id) AS order_count,
    COALESCE(SUM(o.amount), 0) AS total_order_value
FROM customers c
LEFT JOIN orders o
    ON o.customer_id = c.customer_id
GROUP BY
    c.customer_id,
    c.public_id,
    c.email,
    c.full_name,
    c.country_code,
    c.status;

CREATE OR REPLACE VIEW natural_identifier_report AS
SELECT
    b.country_code,
    b.registration_number,
    b.business_name,
    COUNT(mapping.mapping_id) AS linked_customer_count
FROM business_registrations b
LEFT JOIN customer_business_registrations mapping
    ON mapping.country_code = b.country_code
    AND mapping.registration_number = b.registration_number
GROUP BY
    b.country_code,
    b.registration_number,
    b.business_name;

SELECT * FROM customer_key_report;

SELECT * FROM natural_identifier_report;

-- ============================================================
-- 26. CTE-BASED ELIGIBILITY DETERMINATION
-- ============================================================

WITH customer_activity AS (
    SELECT
        c.customer_id,
        c.full_name,
        c.status,
        COUNT(o.order_id) AS total_orders,
        COALESCE(SUM(o.amount), 0) AS total_value
    FROM customers c
    LEFT JOIN orders o
        ON o.customer_id = c.customer_id
    GROUP BY
        c.customer_id,
        c.full_name,
        c.status
),
eligibility AS (
    SELECT
        *,
        CASE
            WHEN status = 'ACTIVE' AND total_orders > 0
                THEN 'ELIGIBLE'
            WHEN status <> 'ACTIVE'
                THEN 'BLOCKED'
            ELSE 'REVIEW'
        END AS decision
    FROM customer_activity
)
SELECT *
FROM eligibility
ORDER BY customer_id;

-- ============================================================
-- 27. EMAIL UPDATE AND AUDIT TRANSACTION
-- ============================================================

DO $$
DECLARE
    v_customer_id BIGINT;
BEGIN
    SELECT customer_id
    INTO v_customer_id
    FROM customers
    WHERE email = 'alice@example.com';

    IF v_customer_id IS NOT NULL THEN
        UPDATE customers
        SET email = 'alice.sharma@example.com'
        WHERE customer_id = v_customer_id;
    END IF;
END;
$$;

-- The identity and UUID remain unchanged.
-- The audit trigger records the email modification.

SELECT
    c.customer_id,
    c.public_id,
    c.email,
    a.old_email,
    a.new_email,
    a.changed_at
FROM customers c
LEFT JOIN customer_identifier_audit a
    ON a.customer_id = c.customer_id
WHERE c.email = 'alice.sharma@example.com';

-- ============================================================
-- 28. VALIDATION OF FOREIGN KEY RELATIONSHIPS
-- ============================================================

SELECT o.*
FROM orders o
LEFT JOIN customers c
    ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;

SELECT mapping.*
FROM customer_business_registrations mapping
LEFT JOIN business_registrations b
    ON b.country_code = mapping.country_code
    AND b.registration_number = mapping.registration_number
WHERE b.registration_number IS NULL;

-- Both validation queries should return no rows.

-- ============================================================
-- 29. FAILURE CASES
-- ============================================================

-- Execute these statements individually to observe the constraints.
-- They are not executed automatically because they intentionally fail.

-- Duplicate natural key:
-- INSERT INTO business_registrations
-- (country_code, registration_number, business_name, registration_date)
-- VALUES ('IN', 'TAX-1001', 'Duplicate', CURRENT_DATE);

-- Duplicate public UUID:
-- INSERT INTO customers
-- (public_id, email, full_name, country_code)
-- VALUES (
--     (SELECT public_id FROM customers LIMIT 1),
--     'duplicate@example.com',
--     'Duplicate Customer',
--     'IN'
-- );

-- Invalid order amount:
-- INSERT INTO orders (customer_id, amount)
-- VALUES (1, -100);

-- Missing foreign key:
-- INSERT INTO orders (customer_id, amount)
-- VALUES (999999, 100);

-- ============================================================
-- 30. PROCEDURE EXECUTION
-- ============================================================

CALL create_customer_order(
    (
        SELECT customer_id
        FROM customers
        WHERE email = 'alice.sharma@example.com'
    ),
    1500.00
);

-- ============================================================
-- 31. FINAL REPORT
-- ============================================================

SELECT
    COUNT(*) AS total_customers,
    COUNT(DISTINCT customer_id) AS distinct_identity_keys,
    COUNT(DISTINCT public_id) AS distinct_uuid_keys,
    COUNT(DISTINCT email) AS distinct_natural_attributes
FROM customers;

SELECT
    COUNT(*) AS total_orders,
    COUNT(DISTINCT customer_id) AS customers_with_orders,
    SUM(amount) AS total_transaction_value
FROM orders;

COMMIT;

-- ============================================================
-- DESIGN NOTES
-- ============================================================
--
-- 1. IDENTITY:
--    Database-managed BIGINT primary key.
--
-- 2. UUID:
--    Independent 128-bit public identifier.
--
-- 3. NATURAL:
--    Business attributes with explicit uniqueness constraints.
--
-- 4. SEQUENCE:
--    Explicitly allocated order references.
--
-- 5. FOREIGN KEYS:
--    Internal relationships use compact surrogate identifiers.
--
-- 6. COMPOSITE KEY:
--    Country and registration number identify a business record.
--
-- 7. AUDIT:
--    Natural attribute changes do not modify surrogate identifiers.
--
-- 8. SECURITY:
--    UUID unpredictability does not replace authorization.
--
-- 9. PERFORMANCE:
--    UUID and natural-key indexes consume more storage than BIGINT
--    indexes. Index design should reflect actual query patterns.
--
-- 10. TRANSACTIONS:
--     Constraints, triggers, and database transactions protect
--     relational integrity.
-- ============================================================
