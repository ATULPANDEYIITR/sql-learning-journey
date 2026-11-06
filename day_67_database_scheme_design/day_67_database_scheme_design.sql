-- ============================================================
-- DATABASE SCHEMA DESIGN
-- OLTP schema design, naming conventions, keys and constraints
-- PostgreSQL 15+
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS commerce;

SET search_path TO commerce, public;

-- ============================================================
-- 1. DOMAIN TYPES
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'order_status'
          AND n.nspname = 'commerce'
    ) THEN
        CREATE TYPE order_status AS ENUM (
            'PENDING',
            'CONFIRMED',
            'SHIPPED',
            'CANCELLED'
        );
    END IF;
END
$$;

-- ============================================================
-- 2. CUSTOMER MASTER
-- Surrogate primary key and natural candidate key.
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY,
    email VARCHAR(254) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_customers
        PRIMARY KEY (customer_id),

    CONSTRAINT uq_customers_email
        UNIQUE (email),

    CONSTRAINT ck_customers_email
        CHECK (
            email = lower(email)
            AND email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
        ),

    CONSTRAINT ck_customers_full_name
        CHECK (length(trim(full_name)) > 0)
);

-- ============================================================
-- 3. PRODUCT MASTER
-- SKU is a candidate key.
-- ============================================================

CREATE TABLE IF NOT EXISTS products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY,
    sku VARCHAR(40) NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    description TEXT,
    unit_price NUMERIC(12, 2) NOT NULL,
    currency_code CHAR(3) NOT NULL DEFAULT 'INR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_products
        PRIMARY KEY (product_id),

    CONSTRAINT uq_products_sku
        UNIQUE (sku),

    CONSTRAINT ck_products_price
        CHECK (unit_price >= 0),

    CONSTRAINT ck_products_currency
        CHECK (currency_code ~ '^[A-Z]{3}$'),

    CONSTRAINT ck_products_name
        CHECK (length(trim(product_name)) > 0)
);

-- ============================================================
-- 4. CUSTOMER ADDRESSES
-- One customer can have multiple addresses.
-- ============================================================

CREATE TABLE IF NOT EXISTS customer_addresses (
    address_id BIGINT GENERATED ALWAYS AS IDENTITY,
    customer_id BIGINT NOT NULL,
    address_type VARCHAR(20) NOT NULL,
    address_line_1 VARCHAR(200) NOT NULL,
    address_line_2 VARCHAR(200),
    city VARCHAR(100) NOT NULL,
    state_code VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country_code CHAR(2) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT pk_customer_addresses
        PRIMARY KEY (address_id),

    CONSTRAINT fk_customer_addresses_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_customer_addresses_type
        CHECK (address_type IN ('BILLING', 'SHIPPING')),

    CONSTRAINT ck_customer_addresses_country
        CHECK (country_code ~ '^[A-Z]{2}$')
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_default_address
    ON customer_addresses(customer_id, address_type)
    WHERE is_default = TRUE;

-- ============================================================
-- 5. ORDERS
-- Header-level information is separated from line items.
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY,
    customer_id BIGINT NOT NULL,
    shipping_address_id BIGINT,
    order_status commerce.order_status NOT NULL DEFAULT 'PENDING',
    order_reference UUID NOT NULL DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_orders
        PRIMARY KEY (order_id),

    CONSTRAINT uq_orders_reference
        UNIQUE (order_reference),

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_orders_shipping_address
        FOREIGN KEY (shipping_address_id)
        REFERENCES customer_addresses(address_id)
        ON DELETE RESTRICT
);

-- ============================================================
-- 6. ORDER ITEMS
-- Composite candidate key prevents duplicate products
-- within the same order.
-- unit_price preserves the price agreed at purchase time.
-- ============================================================

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id BIGINT GENERATED ALWAYS AS IDENTITY,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,

    CONSTRAINT pk_order_items
        PRIMARY KEY (order_item_id),

    CONSTRAINT uq_order_items_order_product
        UNIQUE (order_id, product_id),

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_order_items_quantity
        CHECK (quantity > 0),

    CONSTRAINT ck_order_items_price
        CHECK (unit_price >= 0)
);

-- ============================================================
-- 7. PAYMENTS
-- Separate payment records support multiple payment attempts.
-- ============================================================

CREATE TABLE IF NOT EXISTS payments (
    payment_id BIGINT GENERATED ALWAYS AS IDENTITY,
    order_id BIGINT NOT NULL,
    payment_reference UUID NOT NULL DEFAULT gen_random_uuid(),
    payment_method VARCHAR(30) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    processed_at TIMESTAMPTZ,

    CONSTRAINT pk_payments
        PRIMARY KEY (payment_id),

    CONSTRAINT uq_payments_reference
        UNIQUE (payment_reference),

    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_payments_amount
        CHECK (amount > 0),

    CONSTRAINT ck_payments_method
        CHECK (
            payment_method IN (
                'CARD', 'UPI', 'BANK_TRANSFER', 'CASH'
            )
        ),

    CONSTRAINT ck_payments_status
        CHECK (
            payment_status IN (
                'PENDING', 'SUCCESS', 'FAILED', 'REFUNDED'
            )
        ),

    CONSTRAINT ck_payments_processed_time
        CHECK (
            payment_status <> 'SUCCESS'
            OR processed_at IS NOT NULL
        )
);

-- ============================================================
-- 8. INDEXES
-- Foreign keys are not automatically indexed on the
-- referencing side in PostgreSQL.
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_addresses_customer
    ON customer_addresses(customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_customer_created
    ON orders(customer_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_status_created
    ON orders(order_status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_items_product
    ON order_items(product_id);

CREATE INDEX IF NOT EXISTS idx_payments_order
    ON payments(order_id);

CREATE INDEX IF NOT EXISTS idx_products_active
    ON products(product_id)
    WHERE is_active = TRUE;

-- ============================================================
-- 9. UPDATED_AT TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_customers_updated_at ON customers;

CREATE TRIGGER trg_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_orders_updated_at ON orders;

CREATE TRIGGER trg_orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 10. ORDER STATUS TRANSITION VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_order_status_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.order_status = NEW.order_status THEN
        RETURN NEW;
    END IF;

    IF OLD.order_status IN ('SHIPPED', 'CANCELLED') THEN
        RAISE EXCEPTION
            'Terminal order status cannot be changed from %',
            OLD.order_status;
    END IF;

    IF OLD.order_status = 'PENDING'
       AND NEW.order_status NOT IN ('CONFIRMED', 'CANCELLED') THEN
        RAISE EXCEPTION 'Invalid transition from PENDING';
    END IF;

    IF OLD.order_status = 'CONFIRMED'
       AND NEW.order_status NOT IN ('SHIPPED', 'CANCELLED') THEN
        RAISE EXCEPTION 'Invalid transition from CONFIRMED';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_order_status_transition ON orders;

CREATE TRIGGER trg_order_status_transition
BEFORE UPDATE OF order_status ON orders
FOR EACH ROW
EXECUTE FUNCTION validate_order_status_transition();

-- ============================================================
-- 11. ORDER ITEM VALIDATION
-- Product must be active when an item is inserted or changed.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_order_item_product()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    product_active BOOLEAN;
    current_status commerce.order_status;
BEGIN
    SELECT is_active
    INTO product_active
    FROM products
    WHERE product_id = NEW.product_id
    FOR KEY SHARE;

    IF NOT FOUND OR product_active IS NOT TRUE THEN
        RAISE EXCEPTION 'Product is unavailable';
    END IF;

    SELECT order_status
    INTO current_status
    FROM orders
    WHERE order_id = NEW.order_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Order does not exist';
    END IF;

    IF current_status <> 'PENDING' THEN
        RAISE EXCEPTION
            'Order items can only be changed for PENDING orders';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_order_item ON order_items;

CREATE TRIGGER trg_validate_order_item
BEFORE INSERT OR UPDATE ON order_items
FOR EACH ROW
EXECUTE FUNCTION validate_order_item_product();

-- ============================================================
-- 12. ORDER TOTAL VIEW
-- ============================================================

CREATE OR REPLACE VIEW v_order_totals AS
SELECT
    o.order_id,
    o.order_reference,
    o.customer_id,
    c.full_name,
    o.order_status,
    COUNT(oi.order_item_id) AS item_count,
    COALESCE(
        SUM(oi.quantity * oi.unit_price),
        0
    )::NUMERIC(14, 2) AS order_total,
    o.created_at
FROM orders o
JOIN customers c
    ON c.customer_id = o.customer_id
LEFT JOIN order_items oi
    ON oi.order_id = o.order_id
GROUP BY
    o.order_id,
    o.order_reference,
    o.customer_id,
    c.full_name,
    o.order_status,
    o.created_at;

-- ============================================================
-- 13. ORDER CREATION PROCEDURE
-- All line items are inserted in the same transaction.
-- Prices are fetched from the trusted product table.
-- ============================================================

CREATE OR REPLACE PROCEDURE create_order(
    IN p_customer_id BIGINT,
    IN p_items JSONB,
    INOUT p_order_id BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    item JSONB;
    product_record RECORD;
    requested_product_id BIGINT;
    requested_quantity INTEGER;
BEGIN
    IF p_customer_id IS NULL THEN
        RAISE EXCEPTION 'Customer ID is required';
    END IF;

    IF p_items IS NULL
       OR jsonb_typeof(p_items) <> 'array'
       OR jsonb_array_length(p_items) = 0 THEN
        RAISE EXCEPTION 'Order must contain at least one item';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM customers
        WHERE customer_id = p_customer_id
          AND is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Customer is unavailable';
    END IF;

    -- Reject malformed JSON properties and duplicate products.
    IF EXISTS (
        SELECT 1
        FROM jsonb_array_elements(p_items) AS element
        WHERE jsonb_typeof(element) <> 'object'
           OR NOT (
               element ? 'product_id'
               AND element ? 'quantity'
           )
    ) THEN
        RAISE EXCEPTION 'Each item requires product_id and quantity';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM jsonb_array_elements(p_items) AS element
        WHERE jsonb_object_length(element) <> 2
    ) THEN
        RAISE EXCEPTION 'Unexpected order item properties';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM jsonb_array_elements(p_items) AS element
        WHERE jsonb_typeof(element -> 'product_id') <> 'number'
           OR jsonb_typeof(element -> 'quantity') <> 'number'
    ) THEN
        RAISE EXCEPTION 'Product IDs and quantities must be numbers';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM jsonb_array_elements(p_items) AS element
        WHERE (element ->> 'product_id') !~ '^[1-9][0-9]*$'
           OR (element ->> 'quantity') !~ '^[1-9][0-9]*$'
    ) THEN
        RAISE EXCEPTION 'Product IDs and quantities must be positive integers';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM jsonb_array_elements(p_items) AS element
        WHERE (element ->> 'product_id')::NUMERIC > 9223372036854775807
           OR (element ->> 'quantity')::NUMERIC > 2147483647
    ) THEN
        RAISE EXCEPTION 'Order item value exceeds supported range';
    END IF;

    IF (
        SELECT COUNT(*) <> COUNT(DISTINCT product_id)
        FROM jsonb_to_recordset(p_items)
            AS x(product_id BIGINT, quantity INTEGER)
    ) THEN
        RAISE EXCEPTION 'Duplicate product in order';
    END IF;

    INSERT INTO orders(customer_id)
    VALUES (p_customer_id)
    RETURNING order_id INTO p_order_id;

    FOR item IN
        SELECT value
        FROM jsonb_array_elements(p_items)
    LOOP
        requested_product_id :=
            (item ->> 'product_id')::BIGINT;

        requested_quantity :=
            (item ->> 'quantity')::INTEGER;

        SELECT product_id, unit_price
        INTO product_record
        FROM products
        WHERE product_id = requested_product_id
          AND is_active = TRUE
        FOR KEY SHARE;

        IF NOT FOUND THEN
            RAISE EXCEPTION
                'Product % is unavailable',
                requested_product_id;
        END IF;

        INSERT INTO order_items(
            order_id,
            product_id,
            quantity,
            unit_price
        )
        VALUES (
            p_order_id,
            product_record.product_id,
            requested_quantity,
            product_record.unit_price
        );
    END LOOP;
END;
$$;

-- ============================================================
-- 14. SAMPLE DATA
-- ============================================================

INSERT INTO customers(
    email,
    full_name,
    phone
)
VALUES
    ('aarav@example.com', 'Aarav Sharma', '+919876543210'),
    ('diya@example.com', 'Diya Verma', '+919876543211')
ON CONFLICT (email) DO NOTHING;

INSERT INTO products(
    sku,
    product_name,
    unit_price
)
VALUES
    ('SKU-1001', 'Business Laptop', 65000.00),
    ('SKU-1002', 'Mechanical Keyboard', 1500.00),
    ('SKU-1003', 'External Monitor', 12000.00),
    ('SKU-1004', 'USB Hub', 0.00)
ON CONFLICT (sku) DO NOTHING;

INSERT INTO customer_addresses(
    customer_id,
    address_type,
    address_line_1,
    city,
    state_code,
    postal_code,
    country_code,
    is_default
)
SELECT
    customer_id,
    'SHIPPING',
    '12 Gomti Nagar',
    'Lucknow',
    'Uttar Pradesh',
    '226010',
    'IN',
    TRUE
FROM customers
WHERE email = 'aarav@example.com'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 15. WORKFLOW PROCESSING
-- ============================================================

DO $$
DECLARE
    customer_key BIGINT;
    laptop_key BIGINT;
    keyboard_key BIGINT;
    created_order_id BIGINT;
BEGIN
    SELECT customer_id
    INTO customer_key
    FROM customers
    WHERE email = 'aarav@example.com';

    SELECT product_id
    INTO laptop_key
    FROM products
    WHERE sku = 'SKU-1001';

    SELECT product_id
    INTO keyboard_key
    FROM products
    WHERE sku = 'SKU-1002';

    CALL create_order(
        customer_key,
        jsonb_build_array(
            jsonb_build_object(
                'product_id', laptop_key,
                'quantity', 1
            ),
            jsonb_build_object(
                'product_id', keyboard_key,
                'quantity', 2
            )
        ),
        created_order_id
    );

    RAISE NOTICE 'Created order: %', created_order_id;

    UPDATE orders
    SET order_status = 'CONFIRMED'
    WHERE order_id = created_order_id;
END;
$$;

COMMIT;

-- ============================================================
-- 16. RETRIEVAL QUERIES
-- ============================================================

SELECT *
FROM customers
ORDER BY customer_id;

SELECT *
FROM products
WHERE is_active = TRUE
ORDER BY product_name;

SELECT *
FROM v_order_totals
ORDER BY created_at DESC;

-- ============================================================
-- 17. AGGREGATION AND REPORTING
-- ============================================================

SELECT
    customer_id,
    full_name,
    COUNT(order_id) AS total_orders,
    SUM(order_total) AS lifetime_order_value
FROM v_order_totals
GROUP BY customer_id, full_name
ORDER BY lifetime_order_value DESC NULLS LAST;

SELECT
    order_status,
    COUNT(*) AS order_count,
    AVG(order_total) AS average_order_value,
    SUM(order_total) AS total_value
FROM v_order_totals
GROUP BY order_status
ORDER BY order_status;

-- Product-level sales performance.
SELECT
    p.product_id,
    p.sku,
    p.product_name,
    COALESCE(SUM(oi.quantity), 0) AS units_sold,
    COALESCE(
        SUM(oi.quantity * oi.unit_price),
        0
    ) AS revenue
FROM products p
LEFT JOIN order_items oi
    ON oi.product_id = p.product_id
GROUP BY
    p.product_id,
    p.sku,
    p.product_name
ORDER BY revenue DESC;

-- ============================================================
-- 18. CTE: CUSTOMER ORDER RANKING
-- ============================================================

WITH customer_sales AS (
    SELECT
        customer_id,
        full_name,
        COUNT(order_id) AS order_count,
        SUM(order_total) AS total_spend
    FROM v_order_totals
    GROUP BY customer_id, full_name
),
ranked_customers AS (
    SELECT
        *,
        DENSE_RANK() OVER (
            ORDER BY total_spend DESC
        ) AS spending_rank
    FROM customer_sales
)
SELECT *
FROM ranked_customers
ORDER BY spending_rank, customer_id;

-- ============================================================
-- 19. ELIGIBILITY EVALUATION
-- Customers qualify for priority handling when they are active
-- and have at least one confirmed or shipped order.
-- ============================================================

SELECT
    c.customer_id,
    c.full_name,
    c.is_active,
    COUNT(o.order_id) FILTER (
        WHERE o.order_status IN ('CONFIRMED', 'SHIPPED')
    ) AS eligible_orders,
    (
        c.is_active
        AND COUNT(o.order_id) FILTER (
            WHERE o.order_status IN ('CONFIRMED', 'SHIPPED')
        ) > 0
    ) AS priority_eligible
FROM customers c
LEFT JOIN orders o
    ON o.customer_id = c.customer_id
GROUP BY
    c.customer_id,
    c.full_name,
    c.is_active
ORDER BY c.customer_id;

-- ============================================================
-- 20. SCHEMA VALIDATION REPORT
-- ============================================================

-- Tables and approximate row counts.
SELECT
    schemaname,
    relname AS table_name,
    n_live_tup AS estimated_rows
FROM pg_stat_user_tables
WHERE schemaname = 'commerce'
ORDER BY relname;

-- Primary and foreign key definitions.
SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.constraint_schema = 'commerce'
ORDER BY tc.table_name, tc.constraint_type;

-- Index inventory.
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'commerce'
ORDER BY tablename, indexname;

-- Detect orders with no line items.
SELECT
    o.order_id,
    o.order_status
FROM orders o
WHERE NOT EXISTS (
    SELECT 1
    FROM order_items oi
    WHERE oi.order_id = o.order_id
);

-- ============================================================
-- 21. FAILURE CASES
-- Run individually inside a transaction and roll back.
-- ============================================================

-- Duplicate email:
-- INSERT INTO customers(email, full_name)
-- VALUES ('aarav@example.com', 'Duplicate');

-- Invalid quantity:
-- INSERT INTO order_items(
--     order_id, product_id, quantity, unit_price
-- )
-- VALUES (1, 1, -1, 100.00);

-- Missing customer:
-- INSERT INTO orders(customer_id)
-- VALUES (999999);

-- Invalid order status transition:
-- UPDATE orders
-- SET order_status = 'SHIPPED'
-- WHERE order_status = 'PENDING';

-- ============================================================
-- 22. QUERY PLAN
-- ============================================================

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    order_status,
    created_at
FROM orders
WHERE customer_id = 1
ORDER BY created_at DESC;

-- ============================================================
-- 23. SCHEMA DESIGN INSPECTION
-- ============================================================

SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'commerce'
ORDER BY table_name, ordinal_position;
