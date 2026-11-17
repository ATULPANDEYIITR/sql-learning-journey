/*
===============================================================================
SAVEPOINT: PARTIAL ROLLBACK AND NESTED TRANSACTION PATTERNS
===============================================================================

PostgreSQL 15+ compatible.

This script demonstrates:
1. Transaction boundaries.
2. SAVEPOINT creation.
3. ROLLBACK TO SAVEPOINT.
4. RELEASE SAVEPOINT.
5. Nested transaction patterns.
6. Transaction-local error recovery.
7. Constraint enforcement.
8. Transactional business operations.
9. Deferred and immediate integrity checks.
10. Concurrency-oriented transaction design.
11. Reporting and transaction auditing.

Important:
PostgreSQL does not provide independently committed nested transactions.
SAVEPOINT provides nested transactional scopes inside one outer transaction.

Execute the entire script in a PostgreSQL client supporting SQL transactions.
*/

DROP SCHEMA IF EXISTS savepoint_lab CASCADE;

CREATE SCHEMA savepoint_lab;

SET search_path TO savepoint_lab, public;

-- ============================================================================
-- 1. DOMAIN TABLES
-- ============================================================================

CREATE TABLE accounts (
    account_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_name VARCHAR(120) NOT NULL UNIQUE,
    balance NUMERIC(14, 2) NOT NULL DEFAULT 0,
    account_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT accounts_balance_nonnegative
        CHECK (balance >= 0),

    CONSTRAINT accounts_status_valid
        CHECK (
            account_status IN ('ACTIVE', 'SUSPENDED', 'CLOSED')
        )
);

CREATE TABLE products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL UNIQUE,
    stock_quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT products_stock_nonnegative
        CHECK (stock_quantity >= 0),

    CONSTRAINT products_price_positive
        CHECK (unit_price > 0)
);

CREATE TABLE orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    order_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    total_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT orders_status_valid
        CHECK (
            order_status IN (
                'PENDING',
                'CONFIRMED',
                'CANCELLED',
                'FAILED'
            )
        ),

    CONSTRAINT orders_amount_nonnegative
        CHECK (total_amount >= 0)
);

CREATE TABLE order_items (
    order_item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL
        REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,

    CONSTRAINT order_items_quantity_positive
        CHECK (quantity > 0),

    CONSTRAINT order_items_price_positive
        CHECK (unit_price > 0),

    CONSTRAINT order_items_unique_product
        UNIQUE (order_id, product_id)
);

CREATE TABLE transaction_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_label VARCHAR(100) NOT NULL,
    operation VARCHAR(60) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transaction_batches (
    batch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_name VARCHAR(120) NOT NULL UNIQUE,
    batch_status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT batch_status_valid
        CHECK (
            batch_status IN ('OPEN', 'COMPLETED', 'FAILED')
        )
);

-- ============================================================================
-- 2. PERFORMANCE INDEXES
-- ============================================================================

CREATE INDEX idx_orders_account_created
    ON orders(account_id, created_at DESC);

CREATE INDEX idx_orders_status_created
    ON orders(order_status, created_at DESC);

CREATE INDEX idx_order_items_product
    ON order_items(product_id);

CREATE INDEX idx_audit_transaction_time
    ON transaction_audit(transaction_label, recorded_at DESC);

CREATE INDEX idx_products_active
    ON products(product_id)
    WHERE active = TRUE;

-- ============================================================================
-- 3. SAMPLE DATA
-- ============================================================================

INSERT INTO accounts (
    account_name,
    balance
)
VALUES
    ('Corporate Procurement', 200000.00),
    ('Regional Procurement', 10000.00),
    ('Restricted Account', 0.00);

INSERT INTO products (
    product_name,
    stock_quantity,
    unit_price
)
VALUES
    ('Enterprise Laptop', 10, 75000.00),
    ('Wireless Keyboard', 20, 2500.00),
    ('External SSD', 5, 6500.00);

INSERT INTO transaction_batches(batch_name)
VALUES
    ('MONTHLY_PROCUREMENT'),
    ('REGIONAL_PROCUREMENT');

-- ============================================================================
-- 4. ORDER PROCESSING FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION create_order(
    p_account_id BIGINT,
    p_product_id BIGINT,
    p_quantity INTEGER
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_price NUMERIC(12, 2);
    v_stock INTEGER;
    v_balance NUMERIC(14, 2);
    v_order_id BIGINT;
    v_amount NUMERIC(14, 2);
    v_account_status VARCHAR(20);
BEGIN
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION 'Quantity must be positive';
    END IF;

    -- Lock rows to prevent concurrent overselling and overspending.
    SELECT balance, account_status
    INTO v_balance, v_account_status
    FROM accounts
    WHERE account_id = p_account_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Account % does not exist', p_account_id;
    END IF;

    IF v_account_status <> 'ACTIVE' THEN
        RAISE EXCEPTION 'Account % is not active', p_account_id;
    END IF;

    SELECT unit_price, stock_quantity
    INTO v_price, v_stock
    FROM products
    WHERE product_id = p_product_id
      AND active = TRUE
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active product % does not exist', p_product_id;
    END IF;

    IF v_stock < p_quantity THEN
        RAISE EXCEPTION
            'Insufficient inventory: available %, requested %',
            v_stock,
            p_quantity;
    END IF;

    v_amount := v_price * p_quantity;

    IF v_balance < v_amount THEN
        RAISE EXCEPTION
            'Insufficient balance: available %, required %',
            v_balance,
            v_amount;
    END IF;

    INSERT INTO orders (
        account_id,
        order_status,
        total_amount
    )
    VALUES (
        p_account_id,
        'CONFIRMED',
        v_amount
    )
    RETURNING order_id INTO v_order_id;

    INSERT INTO order_items (
        order_id,
        product_id,
        quantity,
        unit_price
    )
    VALUES (
        v_order_id,
        p_product_id,
        p_quantity,
        v_price
    );

    UPDATE products
    SET stock_quantity = stock_quantity - p_quantity
    WHERE product_id = p_product_id;

    UPDATE accounts
    SET balance = balance - v_amount
    WHERE account_id = p_account_id;

    RETURN v_order_id;
END;
$$;

-- ============================================================================
-- 5. TRANSACTION AUDIT FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION audit_transaction_event(
    p_label VARCHAR(100),
    p_operation VARCHAR(60),
    p_details JSONB DEFAULT '{}'::JSONB
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO transaction_audit (
        transaction_label,
        operation,
        details
    )
    VALUES (
        p_label,
        p_operation,
        COALESCE(p_details, '{}'::JSONB)
    );
END;
$$;

-- ============================================================================
-- 6. AUTOMATIC ORDER VALIDATION TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION validate_order_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.order_status IN ('CONFIRMED', 'CANCELLED')
       AND NEW.order_status <> OLD.order_status THEN
        RAISE EXCEPTION
            'Terminal order status cannot be changed';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_order_status
BEFORE UPDATE OF order_status
ON orders
FOR EACH ROW
EXECUTE FUNCTION validate_order_status();

-- ============================================================================
-- 7. VIEW: ORDER AND ACCOUNT REPORTING
-- ============================================================================

CREATE OR REPLACE VIEW order_summary AS
SELECT
    o.order_id,
    a.account_name,
    o.order_status,
    o.total_amount,
    COUNT(oi.order_item_id) AS item_count,
    COALESCE(SUM(oi.quantity), 0) AS total_quantity,
    o.created_at
FROM orders o
JOIN accounts a
    ON a.account_id = o.account_id
LEFT JOIN order_items oi
    ON oi.order_id = o.order_id
GROUP BY
    o.order_id,
    a.account_name,
    o.order_status,
    o.total_amount,
    o.created_at;

-- ============================================================================
-- 8. BASIC TRANSACTION WITH SAVEPOINT
-- ============================================================================

BEGIN;

SELECT audit_transaction_event(
    'BASIC_TRANSACTION',
    'BEGIN',
    '{"description": "Initial transaction"}'
);

SELECT create_order(1, 101, 1);

SAVEPOINT optional_operation;

SELECT create_order(1, 102, 2);

-- The following statement deliberately fails due to insufficient stock.
-- In a client that stops on SQL errors, execute this statement separately
-- or use the PL/pgSQL exception demonstration below.
ROLLBACK TO SAVEPOINT optional_operation;

SELECT audit_transaction_event(
    'BASIC_TRANSACTION',
    'PARTIAL_ROLLBACK',
    '{"savepoint": "optional_operation"}'
);

RELEASE SAVEPOINT optional_operation;

COMMIT;

-- ============================================================================
-- 9. NESTED TRANSACTION PATTERN
-- ============================================================================

BEGIN;

SAVEPOINT outer_operation;

SELECT create_order(1, 102, 2);

SAVEPOINT inner_operation;

-- The account has sufficient funds for the operation below.
SELECT create_order(1, 103, 1);

-- Roll back only the inner operation.
ROLLBACK TO SAVEPOINT inner_operation;

-- The outer operation remains part of the transaction.
RELEASE SAVEPOINT inner_operation;

SELECT audit_transaction_event(
    'NESTED_TRANSACTION',
    'INNER_ROLLBACK',
    '{"preserved": "outer_operation"}'
);

COMMIT;

-- ============================================================================
-- 10. PL/PGSQL EXCEPTION BLOCKS AS SUBTRANSACTIONS
-- ============================================================================

/*
A PL/pgSQL block containing an EXCEPTION clause establishes an implicit
subtransaction.

When an exception is caught, database changes made inside that block are
rolled back, while changes made before entering the block remain.

The block's exception handler executes after the subtransaction rollback.
*/

DO $$
DECLARE
    v_order_id BIGINT;
BEGIN
    -- Outer transaction work.
    v_order_id := create_order(1, 102, 1);

    RAISE NOTICE 'Outer order created: %', v_order_id;

    BEGIN
        -- Inner subtransaction.
        PERFORM create_order(1, 103, 100);

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE
                'Inner operation rolled back: %',
                SQLERRM;

            INSERT INTO transaction_audit (
                transaction_label,
                operation,
                details
            )
            VALUES (
                'PLPGSQL_NESTED',
                'INNER_FAILURE',
                jsonb_build_object(
                    'error',
                    SQLERRM
                )
            );
    END;

    -- Outer work can continue.
    UPDATE transaction_batches
    SET batch_status = 'COMPLETED'
    WHERE batch_name = 'MONTHLY_PROCUREMENT';

END;
$$;

-- ============================================================================
-- 11. MULTIPLE SAVEPOINTS AND PARTIAL ROLLBACK
-- ============================================================================

BEGIN;

SAVEPOINT stage_one;

SELECT create_order(1, 102, 1);

SAVEPOINT stage_two;

SELECT create_order(1, 103, 1);

-- Restore the state at stage_two.
ROLLBACK TO SAVEPOINT stage_two;

-- stage_two remains available.
SELECT audit_transaction_event(
    'MULTI_STAGE',
    'ROLLBACK_TO_STAGE_TWO',
    '{"stage": 2}'
);

-- Remove stage_two without committing the transaction.
RELEASE SAVEPOINT stage_two;

COMMIT;

-- ============================================================================
-- 12. FULL TRANSACTION ROLLBACK
-- ============================================================================

BEGIN;

SELECT create_order(1, 102, 1);

SAVEPOINT recovery_point;

SELECT create_order(1, 103, 1);

-- Complete rollback removes all transactional changes,
-- including changes made before the savepoint.
ROLLBACK;

-- ============================================================================
-- 13. TRANSACTIONAL PROCEDURE WITH PARTIAL RECOVERY
-- ============================================================================

CREATE OR REPLACE PROCEDURE process_procurement_batch(
    p_batch_name VARCHAR(120),
    p_account_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_order_id BIGINT;
    v_failure_count INTEGER := 0;
BEGIN
    UPDATE transaction_batches
    SET batch_status = 'OPEN'
    WHERE batch_name = p_batch_name;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Batch % does not exist', p_batch_name;
    END IF;

    -- Successful mandatory operation.
    v_order_id := create_order(p_account_id, 102, 1);

    RAISE NOTICE 'Mandatory order created: %', v_order_id;

    -- Optional operation is isolated by its exception block.
    BEGIN
        PERFORM create_order(p_account_id, 103, 100);

    EXCEPTION
        WHEN OTHERS THEN
            v_failure_count := v_failure_count + 1;

            INSERT INTO transaction_audit (
                transaction_label,
                operation,
                details
            )
            VALUES (
                p_batch_name,
                'OPTIONAL_OPERATION_FAILED',
                jsonb_build_object(
                    'error',
                    SQLERRM
                )
            );
    END;

    UPDATE transaction_batches
    SET batch_status = 'COMPLETED'
    WHERE batch_name = p_batch_name;

    RAISE NOTICE
        'Batch completed with % optional failures',
        v_failure_count;
END;
$$;

-- CALL executes inside the caller's transaction.
BEGIN;

CALL process_procurement_batch(
    'REGIONAL_PROCUREMENT',
    1
);

COMMIT;

-- ============================================================================
-- 14. SAVEPOINT RECOVERY AND CONSTRAINT FAILURE
-- ============================================================================

BEGIN;

SAVEPOINT before_invalid_update;

-- This update violates the non-negative stock constraint.
-- Execute as an isolated statement when using a client that stops on error.
-- ROLLBACK TO SAVEPOINT before_invalid_update restores the transaction
-- after the constraint violation.

ROLLBACK TO SAVEPOINT before_invalid_update;

RELEASE SAVEPOINT before_invalid_update;

COMMIT;

-- ============================================================================
-- 15. TRANSACTION STATE AND ELIGIBILITY REPORT
-- ============================================================================

WITH account_exposure AS (
    SELECT
        a.account_id,
        a.account_name,
        a.balance,
        COUNT(o.order_id) FILTER (
            WHERE o.order_status = 'CONFIRMED'
        ) AS confirmed_orders,
        COALESCE(
            SUM(o.total_amount) FILTER (
                WHERE o.order_status = 'CONFIRMED'
            ),
            0
        ) AS confirmed_amount
    FROM accounts a
    LEFT JOIN orders o
        ON o.account_id = a.account_id
    GROUP BY
        a.account_id,
        a.account_name,
        a.balance
)
SELECT
    account_id,
    account_name,
    balance,
    confirmed_orders,
    confirmed_amount,
    CASE
        WHEN balance > 0 THEN 'ELIGIBLE'
        ELSE 'REQUIRES_FUNDING'
    END AS account_eligibility
FROM account_exposure
ORDER BY account_id;

-- ============================================================================
-- 16. SAVEPOINT AUDIT REPORT
-- ============================================================================

SELECT
    transaction_label,
    operation,
    details,
    recorded_at
FROM transaction_audit
ORDER BY audit_id;

-- ============================================================================
-- 17. ORDER REPORT
-- ============================================================================

SELECT *
FROM order_summary
ORDER BY created_at DESC, order_id DESC;

-- ============================================================================
-- 18. INVENTORY REPORT
-- ============================================================================

SELECT
    product_id,
    product_name,
    stock_quantity,
    unit_price,
    CASE
        WHEN stock_quantity = 0 THEN 'OUT_OF_STOCK'
        WHEN stock_quantity <= 5 THEN 'LOW_STOCK'
        ELSE 'AVAILABLE'
    END AS inventory_status
FROM products
ORDER BY product_id;

-- ============================================================================
-- 19. TRANSACTION ISOLATION DEMONSTRATION
-- ============================================================================

/*
Run the following in two independent PostgreSQL sessions.

Session A:

BEGIN ISOLATION LEVEL READ COMMITTED;

SELECT stock_quantity
FROM products
WHERE product_id = 102;

UPDATE products
SET stock_quantity = stock_quantity - 1
WHERE product_id = 102
  AND stock_quantity > 0;

COMMIT;

Session B:

BEGIN ISOLATION LEVEL READ COMMITTED;

SELECT stock_quantity
FROM products
WHERE product_id = 102;

UPDATE products
SET stock_quantity = stock_quantity - 1
WHERE product_id = 102
  AND stock_quantity > 0;

COMMIT;

For more demanding workloads, use row locking, conditional updates,
appropriate isolation levels, and retry logic for serialization failures.

A savepoint does not provide concurrency isolation by itself.
*/

-- ============================================================================
-- 20. DATABASE VALIDATION QUERIES
-- ============================================================================

-- Verify that no negative stock exists.
SELECT COUNT(*) AS invalid_inventory_records
FROM products
WHERE stock_quantity < 0;

-- Verify that no negative account balance exists.
SELECT COUNT(*) AS invalid_account_records
FROM accounts
WHERE balance < 0;

-- Verify that every order item has an existing order.
SELECT COUNT(*) AS orphan_order_items
FROM order_items oi
LEFT JOIN orders o
    ON o.order_id = oi.order_id
WHERE o.order_id IS NULL;

-- Verify that order totals equal their item totals.
SELECT
    o.order_id,
    o.total_amount,
    COALESCE(
        SUM(oi.quantity * oi.unit_price),
        0
    ) AS calculated_total
FROM orders o
LEFT JOIN order_items oi
    ON oi.order_id = o.order_id
GROUP BY
    o.order_id,
    o.total_amount
HAVING o.total_amount <> COALESCE(
    SUM(oi.quantity * oi.unit_price),
    0
);

-- ============================================================================
-- END OF SAVEPOINT DEMONSTRATION
-- ============================================================================
