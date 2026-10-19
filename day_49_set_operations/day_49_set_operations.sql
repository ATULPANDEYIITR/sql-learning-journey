DROP SCHEMA IF EXISTS set_operations_demo CASCADE;
CREATE SCHEMA set_operations_demo;
SET search_path = set_operations_demo;

-- The model represents four independent business sources. Their customer
-- populations can be combined using SQL set operators without collapsing
-- source-specific audit information prematurely.

CREATE TABLE customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL,
    source_system TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT customers_email_source_unique UNIQUE (email, source_system),
    CONSTRAINT customers_email_check
        CHECK (email ~* '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
    CONSTRAINT customers_source_check
        CHECK (source_system IN ('crm', 'billing', 'support', 'product'))
);

CREATE INDEX idx_customers_email
    ON customers (email);

CREATE INDEX idx_customers_source_email
    ON customers (source_system, email);

INSERT INTO customers (email, source_system) VALUES
    ('alice@example.com', 'crm'),
    ('bob@example.com', 'crm'),
    ('carol@example.com', 'crm'),
    ('david@example.com', 'crm'),
    ('bob@example.com', 'billing'),
    ('carol@example.com', 'billing'),
    ('erin@example.com', 'billing'),
    ('carol@example.com', 'support'),
    ('david@example.com', 'support'),
    ('frank@example.com', 'support'),
    ('alice@example.com', 'product'),
    ('carol@example.com', 'product'),
    ('frank@example.com', 'product');

CREATE TABLE campaign_registrations (
    registration_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL,
    campaign TEXT NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT campaign_registration_unique
        UNIQUE (email, campaign)
);

INSERT INTO campaign_registrations (email, campaign) VALUES
    ('alice@example.com', 'security-webinar'),
    ('bob@example.com', 'security-webinar'),
    ('carol@example.com', 'security-webinar'),
    ('bob@example.com', 'security-webinar-duplicate-test');

CREATE TABLE purchases (
    purchase_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL,
    order_reference TEXT NOT NULL UNIQUE,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO purchases (email, order_reference, amount) VALUES
    ('alice@example.com', 'ORD-1001', 250.00),
    ('carol@example.com', 'ORD-1002', 480.00),
    ('carol@example.com', 'ORD-1003', 120.00),
    ('frank@example.com', 'ORD-1004', 90.00);

-- UNION removes duplicate rows from the combined result. The projection is
-- deliberately reduced to email because the two SELECT statements have to
-- return compatible column structures.

SELECT email
FROM customers
WHERE source_system = 'crm'
UNION
SELECT email
FROM customers
WHERE source_system = 'billing'
ORDER BY email;

-- UNION ALL preserves duplicate occurrences. A customer present in both
-- source systems therefore appears once for each contributing row.

SELECT email
FROM customers
WHERE source_system = 'crm'
UNION ALL
SELECT email
FROM customers
WHERE source_system = 'billing'
ORDER BY email;

-- INTERSECT returns customers represented by both source populations.

SELECT email
FROM customers
WHERE source_system = 'crm'
INTERSECT
SELECT email
FROM customers
WHERE source_system = 'billing'
ORDER BY email;

-- EXCEPT is directional. CRM EXCEPT billing is different from the reverse.

SELECT email
FROM customers
WHERE source_system = 'crm'
EXCEPT
SELECT email
FROM customers
WHERE source_system = 'billing'
ORDER BY email;

SELECT email
FROM customers
WHERE source_system = 'billing'
EXCEPT
SELECT email
FROM customers
WHERE source_system = 'crm'
ORDER BY email;

-- A CTE makes the source populations explicit before combining them.

WITH crm AS (
    SELECT email
    FROM customers
    WHERE source_system = 'crm'
),
product AS (
    SELECT email
    FROM customers
    WHERE source_system = 'product'
),
support AS (
    SELECT email
    FROM customers
    WHERE source_system = 'support'
)
SELECT email
FROM crm
INTERSECT
SELECT email
FROM product
INTERSECT
SELECT email
FROM support
ORDER BY email;

-- Customers known to any operational source but absent from the billing
-- population form a useful reconciliation set.

WITH known_customers AS (
    SELECT email
    FROM customers
    WHERE source_system IN ('crm', 'product', 'support')
    UNION
    SELECT email
    FROM customers
    WHERE source_system = 'billing'
),
billing_customers AS (
    SELECT email
    FROM customers
    WHERE source_system = 'billing'
)
SELECT email
FROM known_customers
EXCEPT
SELECT email
FROM billing_customers
ORDER BY email;

-- UNION is not a replacement for UNION ALL when occurrence counts matter.
-- The next query exposes how many source rows contribute to each customer.

SELECT
    email,
    COUNT(*) AS source_row_count
FROM customers
GROUP BY email
ORDER BY email;

-- Set operators can be applied to more complex projections. Here the entire
-- projected row is part of the distinctness comparison.

SELECT email, source_system
FROM customers
WHERE source_system IN ('crm', 'billing')
INTERSECT
SELECT email, source_system
FROM customers
WHERE source_system IN ('billing', 'support')
ORDER BY email, source_system;

-- The following query finds campaign registrants who have purchased.

SELECT email
FROM campaign_registrations
WHERE campaign = 'security-webinar'
INTERSECT
SELECT email
FROM purchases
ORDER BY email;

-- Registrants without a purchase are obtained with directional EXCEPT.

SELECT email
FROM campaign_registrations
WHERE campaign = 'security-webinar'
EXCEPT
SELECT email
FROM purchases
ORDER BY email;

-- Purchasers absent from the campaign population demonstrate the reverse
-- directional difference.

SELECT email
FROM purchases
EXCEPT
SELECT email
FROM campaign_registrations
WHERE campaign = 'security-webinar'
ORDER BY email;

-- Transactional integrity demonstration. The invalid source value violates
-- the CHECK constraint, so the transaction is rolled back as a unit.

BEGIN;

INSERT INTO customers (email, source_system)
VALUES ('invalid-source@example.com', 'unknown');

ROLLBACK;

-- PostgreSQL EXPLAIN can be used to inspect the physical strategy selected
-- for larger set-operation workloads. The query remains executable even
-- though the exact plan depends on table statistics and configuration.

EXPLAIN
SELECT email
FROM customers
WHERE source_system = 'crm'
INTERSECT
SELECT email
FROM customers
WHERE source_system = 'billing';

-- A reusable view exposes the distinct population represented by every source.

CREATE VIEW all_distinct_customers AS
SELECT email
FROM customers
UNION
SELECT email
FROM campaign_registrations
UNION
SELECT email
FROM purchases;

SELECT *
FROM all_distinct_customers
ORDER BY email;

-- This final reconciliation query reports source coverage. It does not rely
-- on UNION semantics because the count of contributing rows is itself useful.

SELECT
    email,
    COUNT(DISTINCT source_system) AS customer_source_count,
    ARRAY_AGG(DISTINCT source_system ORDER BY source_system) AS source_systems
FROM customers
GROUP BY email
ORDER BY email;
