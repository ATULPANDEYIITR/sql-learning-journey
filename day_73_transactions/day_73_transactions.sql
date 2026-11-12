-- ============================================================
-- TRANSACTION MANAGEMENT AND ATOMIC OPERATIONS
-- PostgreSQL 15+
--
-- Demonstrates:
-- BEGIN, COMMIT, ROLLBACK, SAVEPOINT,
-- ACID properties, constraints, triggers,
-- transaction isolation, concurrent updates,
-- audit records, and reporting.
--
-- Run this script using psql.
-- The examples use integer minor currency units.
-- ============================================================

DROP SCHEMA IF EXISTS transaction_lab CASCADE;

CREATE SCHEMA transaction_lab;

SET search_path TO transaction_lab, public;

-- ============================================================
-- 1. DOMAIN TABLES
-- ============================================================

CREATE TABLE accounts (
    account_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_number VARCHAR(20) NOT NULL UNIQUE,
    owner_name VARCHAR(100) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    balance BIGINT NOT NULL DEFAULT 0,
    account_status VARCHAR(15) NOT NULL DEFAULT 'ACTIVE',
    version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT positive_account_number
        CHECK (length(account_number) >= 4),

    CONSTRAINT nonnegative_balance
        CHECK (balance >= 0),

    CONSTRAINT valid_account_status
        CHECK (
            account_status IN ('ACTIVE', 'FROZEN', 'CLOSED')
        ),

    CONSTRAINT nonnegative_version
        CHECK (version >= 0)
);

CREATE TABLE bank_transactions (
    transaction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reference_number UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    transaction_type VARCHAR(20) NOT NULL,
    transaction_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    amount BIGINT NOT NULL,
    source_account_id BIGINT REFERENCES accounts(account_id),
    destination_account_id BIGINT REFERENCES accounts(account_id),
    description TEXT,
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    CONSTRAINT valid_transaction_type
        CHECK (
            transaction_type IN (
                'TRANSFER',
                'DEPOSIT',
                'WITHDRAWAL'
            )
        ),

    CONSTRAINT valid_transaction_status
        CHECK (
            transaction_status IN (
                'PENDING',
                'COMMITTED',
                'FAILED',
                'ROLLED_BACK'
            )
        ),

    CONSTRAINT positive_transaction_amount
        CHECK (amount > 0),

    CONSTRAINT different_transfer_accounts
        CHECK (
            source_account_id IS NULL
            OR destination_account_id IS NULL
            OR source_account_id <> destination_account_id
        ),

    CONSTRAINT valid_transaction_accounts
        CHECK (
            (transaction_type = 'TRANSFER'
                AND source_account_id IS NOT NULL
                AND destination_account_id IS NOT NULL)
            OR
            (transaction_type = 'DEPOSIT'
                AND source_account_id IS NULL
                AND destination_account_id IS NOT NULL)
            OR
            (transaction_type = 'WITHDRAWAL'
                AND source_account_id IS NOT NULL
                AND destination_account_id IS NULL)
        )
);

CREATE TABLE transaction_ledger (
    ledger_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL
        REFERENCES bank_transactions(transaction_id),
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    entry_type VARCHAR(20) NOT NULL,
    amount BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_ledger_entry_type
        CHECK (
            entry_type IN (
                'DEBIT',
                'CREDIT'
            )
        ),

    CONSTRAINT valid_ledger_sign
        CHECK (
            (entry_type = 'DEBIT' AND amount < 0)
            OR
            (entry_type = 'CREDIT' AND amount > 0)
        )
);

CREATE TABLE transaction_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT
        REFERENCES bank_transactions(transaction_id),
    action VARCHAR(30) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    database_user TEXT NOT NULL DEFAULT CURRENT_USER,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Idempotency table prevents duplicate processing of the same request.
CREATE TABLE idempotency_keys (
    idempotency_key VARCHAR(100) PRIMARY KEY,
    transaction_id BIGINT UNIQUE
        REFERENCES bank_transactions(transaction_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. PERFORMANCE INDEXES
-- ============================================================

CREATE INDEX idx_transactions_status_created
    ON bank_transactions(transaction_status, created_at DESC);

CREATE INDEX idx_transactions_source
    ON bank_transactions(source_account_id, created_at DESC)
    WHERE source_account_id IS NOT NULL;

CREATE INDEX idx_transactions_destination
    ON bank_transactions(destination_account_id, created_at DESC)
    WHERE destination_account_id IS NOT NULL;

CREATE INDEX idx_ledger_account_date
    ON transaction_ledger(account_id, created_at DESC);

CREATE INDEX idx_audit_transaction_date
    ON transaction_audit(transaction_id, occurred_at DESC);

CREATE INDEX idx_transactions_reference
    ON bank_transactions(reference_number);

-- ============================================================
-- 3. ACCOUNT VALIDATION TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION validate_account_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.balance < 0 THEN
        RAISE EXCEPTION 'Account balance cannot be negative';
    END IF;

    IF NEW.currency <> OLD.currency THEN
        RAISE EXCEPTION
            'Account currency cannot be changed after creation';
    END IF;

    IF NEW.account_status = 'CLOSED'
       AND NEW.balance <> 0 THEN
        RAISE EXCEPTION
            'An account with a non-zero balance cannot be closed';
    END IF;

    IF NEW.balance IS DISTINCT FROM OLD.balance THEN
        NEW.version := OLD.version + 1;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_account_update
BEFORE UPDATE ON accounts
FOR EACH ROW
EXECUTE FUNCTION validate_account_update();

-- ============================================================
-- 4. TRANSACTION AUDIT TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION audit_transaction_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO transaction_audit (
        transaction_id,
        action,
        details
    )
    VALUES (
        NEW.transaction_id,
        'STATUS_CHANGED',
        jsonb_build_object(
            'old_status', OLD.transaction_status,
            'new_status', NEW.transaction_status,
            'failure_reason', NEW.failure_reason
        )
    );

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_transaction_status_audit
AFTER UPDATE OF transaction_status ON bank_transactions
FOR EACH ROW
WHEN (
    OLD.transaction_status IS DISTINCT FROM
    NEW.transaction_status
)
EXECUTE FUNCTION audit_transaction_changes();

-- ============================================================
-- 5. SAMPLE ACCOUNTS
-- ============================================================

INSERT INTO accounts (
    account_number,
    owner_name,
    currency,
    balance
)
VALUES
    ('ACC1001', 'Alice', 'INR', 1000000),
    ('ACC1002', 'Bob', 'INR', 500000),
    ('ACC1003', 'Charlie', 'INR', 200000),
    ('ACC1004', 'Diana', 'INR', 0),
    ('ACC1005', 'Ethan', 'USD', 100000);

-- ============================================================
-- 6. ATOMIC TRANSFER FUNCTION
--
-- Both account updates and ledger entries occur in the
-- same database transaction.
--
-- FOR UPDATE locks rows and prevents conflicting modifications
-- while the operation is being processed.
-- ============================================================

CREATE OR REPLACE FUNCTION transfer_funds(
    p_source_account BIGINT,
    p_destination_account BIGINT,
    p_amount BIGINT,
    p_idempotency_key VARCHAR(100)
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction_id BIGINT;
    v_existing_transaction BIGINT;
    v_source_currency CHAR(3);
    v_destination_currency CHAR(3);
    v_source_balance BIGINT;
    v_source_status VARCHAR(15);
    v_destination_status VARCHAR(15);
    v_locked_count INTEGER;
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Transfer amount must be positive';
    END IF;

    IF p_source_account = p_destination_account THEN
        RAISE EXCEPTION
            'Source and destination accounts must differ';
    END IF;

    IF p_idempotency_key IS NULL
       OR length(trim(p_idempotency_key)) = 0 THEN
        RAISE EXCEPTION 'Idempotency key is required';
    END IF;

    -- Serialize identical requests.
    INSERT INTO idempotency_keys(idempotency_key)
    VALUES (p_idempotency_key)
    ON CONFLICT (idempotency_key) DO NOTHING;

    IF NOT FOUND THEN
        SELECT transaction_id
        INTO v_existing_transaction
        FROM idempotency_keys
        WHERE idempotency_key = p_idempotency_key
        FOR UPDATE;

        IF v_existing_transaction IS NOT NULL THEN
            RETURN v_existing_transaction;
        END IF;

        RAISE EXCEPTION
            'Idempotency key is already being processed';
    END IF;

    -- Lock both rows in deterministic order to reduce deadlocks.
    PERFORM account_id
    FROM accounts
    WHERE account_id IN (
        p_source_account,
        p_destination_account
    )
    ORDER BY account_id
    FOR UPDATE;

    GET DIAGNOSTICS v_locked_count = ROW_COUNT;

    IF v_locked_count <> 2 THEN
        RAISE EXCEPTION 'One or both accounts do not exist';
    END IF;

    SELECT balance, currency, account_status
    INTO v_source_balance, v_source_currency, v_source_status
    FROM accounts
    WHERE account_id = p_source_account;

    SELECT currency, account_status
    INTO v_destination_currency, v_destination_status
    FROM accounts
    WHERE account_id = p_destination_account;

    IF v_source_status <> 'ACTIVE'
       OR v_destination_status <> 'ACTIVE' THEN
        RAISE EXCEPTION 'Both accounts must be active';
    END IF;

    IF v_source_currency <> v_destination_currency THEN
        RAISE EXCEPTION 'Currency mismatch';
    END IF;

    IF v_source_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds';
    END IF;

    INSERT INTO bank_transactions (
        transaction_type,
        transaction_status,
        amount,
        source_account_id,
        destination_account_id,
        description
    )
    VALUES (
        'TRANSFER',
        'PENDING',
        p_amount,
        p_source_account,
        p_destination_account,
        'Atomic account transfer'
    )
    RETURNING transaction_id INTO v_transaction_id;

    UPDATE accounts
    SET balance = balance - p_amount
    WHERE account_id = p_source_account;

    UPDATE accounts
    SET balance = balance + p_amount
    WHERE account_id = p_destination_account;

    INSERT INTO transaction_ledger (
        transaction_id,
        account_id,
        entry_type,
        amount
    )
    VALUES
        (
            v_transaction_id,
            p_source_account,
            'DEBIT',
            -p_amount
        ),
        (
            v_transaction_id,
            p_destination_account,
            'CREDIT',
            p_amount
        );

    UPDATE bank_transactions
    SET transaction_status = 'COMMITTED',
        completed_at = CURRENT_TIMESTAMP
    WHERE transaction_id = v_transaction_id;

    UPDATE idempotency_keys
    SET transaction_id = v_transaction_id
    WHERE idempotency_key = p_idempotency_key;

    RETURN v_transaction_id;
END;
$$;

-- ============================================================
-- 7. GENERAL TRANSACTION PROCESSING PROCEDURE
-- ============================================================

CREATE OR REPLACE PROCEDURE process_account_operation(
    p_operation VARCHAR(20),
    p_account_id BIGINT,
    p_amount BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction_id BIGINT;
    v_balance BIGINT;
    v_status VARCHAR(15);
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Amount must be positive';
    END IF;

    SELECT balance, account_status
    INTO v_balance, v_status
    FROM accounts
    WHERE account_id = p_account_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Account does not exist';
    END IF;

    IF v_status <> 'ACTIVE' THEN
        RAISE EXCEPTION 'Account is not active';
    END IF;

    IF p_operation = 'DEPOSIT' THEN
        UPDATE accounts
        SET balance = balance + p_amount
        WHERE account_id = p_account_id;

    ELSIF p_operation = 'WITHDRAWAL' THEN
        IF v_balance < p_amount THEN
            RAISE EXCEPTION 'Insufficient funds';
        END IF;

        UPDATE accounts
        SET balance = balance - p_amount
        WHERE account_id = p_account_id;

    ELSE
        RAISE EXCEPTION 'Unsupported operation: %', p_operation;
    END IF;

    INSERT INTO bank_transactions (
        transaction_type,
        transaction_status,
        amount,
        source_account_id,
        destination_account_id,
        description,
        completed_at
    )
    VALUES (
        p_operation,
        'COMMITTED',
        p_amount,
        CASE
            WHEN p_operation = 'WITHDRAWAL'
            THEN p_account_id
            ELSE NULL
        END,
        CASE
            WHEN p_operation = 'DEPOSIT'
            THEN p_account_id
            ELSE NULL
        END,
        'Single-account operation',
        CURRENT_TIMESTAMP
    )
    RETURNING transaction_id INTO v_transaction_id;

    INSERT INTO transaction_ledger (
        transaction_id,
        account_id,
        entry_type,
        amount
    )
    VALUES (
        v_transaction_id,
        p_account_id,
        CASE
            WHEN p_operation = 'DEPOSIT' THEN 'CREDIT'
            ELSE 'DEBIT'
        END,
        CASE
            WHEN p_operation = 'DEPOSIT' THEN p_amount
            ELSE -p_amount
        END
    );
END;
$$;

-- ============================================================
-- 8. EXECUTE A SUCCESSFUL ATOMIC TRANSFER
-- ============================================================

BEGIN;

SELECT transfer_funds(
    1,
    2,
    150000,
    'REQUEST-TRANSFER-001'
);

COMMIT;

-- ============================================================
-- 9. IDEMPOTENCY TEST
--
-- Repeating the same key returns the original transaction ID.
-- It does not debit or credit accounts again.
-- ============================================================

BEGIN;

SELECT transfer_funds(
    1,
    2,
    150000,
    'REQUEST-TRANSFER-001'
);

COMMIT;

-- ============================================================
-- 10. DEPOSIT TRANSACTION
-- ============================================================

BEGIN;

CALL process_account_operation(
    'DEPOSIT',
    3,
    50000
);

COMMIT;

-- ============================================================
-- 11. WITHDRAWAL TRANSACTION
-- ============================================================

BEGIN;

CALL process_account_operation(
    'WITHDRAWAL',
    2,
    25000
);

COMMIT;

-- ============================================================
-- 12. SAVEPOINT AND PARTIAL ROLLBACK
--
-- The deposit before the savepoint survives.
-- The withdrawal after the savepoint is undone.
-- The final COMMIT preserves only the deposit.
-- ============================================================

BEGIN;

CALL process_account_operation(
    'DEPOSIT',
    4,
    10000
);

SAVEPOINT before_withdrawal;

CALL process_account_operation(
    'WITHDRAWAL',
    4,
    5000
);

ROLLBACK TO SAVEPOINT before_withdrawal;

COMMIT;

-- ============================================================
-- 13. COMPLETE ROLLBACK DEMONSTRATION
--
-- The inserted transaction and its balance change disappear.
-- ============================================================

BEGIN;

CALL process_account_operation(
    'DEPOSIT',
    4,
    20000
);

ROLLBACK;

-- ============================================================
-- 14. FAILURE HANDLING WITH A SUBTRANSACTION
--
-- An exception block in PL/pgSQL creates a subtransaction.
-- The failed operation is rolled back without aborting the
-- surrounding DO block.
-- ============================================================

DO $$
BEGIN
    BEGIN
        CALL process_account_operation(
            'WITHDRAWAL',
            1,
            999999999
        );

        RAISE NOTICE 'Unexpected successful withdrawal';

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE
                'Expected failure safely handled: %',
                SQLERRM;
    END;
END;
$$;

-- ============================================================
-- 15. CURRENCY VALIDATION FAILURE
-- ============================================================

DO $$
BEGIN
    BEGIN
        PERFORM transfer_funds(
            1,
            5,
            1000,
            'REQUEST-INVALID-CURRENCY'
        );

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE
                'Expected currency failure: %',
                SQLERRM;
    END;
END;
$$;

-- ============================================================
-- 16. INSUFFICIENT FUNDS FAILURE
-- ============================================================

DO $$
BEGIN
    BEGIN
        PERFORM transfer_funds(
            2,
            1,
            999999999,
            'REQUEST-INSUFFICIENT'
        );

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE
                'Expected insufficient funds: %',
                SQLERRM;
    END;
END;
$$;

-- ============================================================
-- 17. ACCOUNT STATUS VALIDATION
-- ============================================================

UPDATE accounts
SET account_status = 'FROZEN'
WHERE account_id = 3;

DO $$
BEGIN
    BEGIN
        CALL process_account_operation(
            'DEPOSIT',
            3,
            1000
        );

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE
                'Expected frozen account failure: %',
                SQLERRM;
    END;
END;
$$;

UPDATE accounts
SET account_status = 'ACTIVE'
WHERE account_id = 3;

-- ============================================================
-- 18. REPORTING VIEW
-- ============================================================

CREATE OR REPLACE VIEW account_transaction_summary AS
SELECT
    a.account_id,
    a.account_number,
    a.owner_name,
    a.currency,
    a.balance,
    a.account_status,
    COUNT(DISTINCT t.transaction_id) AS transaction_count,
    COALESCE(
        SUM(
            CASE
                WHEN l.amount > 0 THEN l.amount
                ELSE 0
            END
        ),
        0
    ) AS total_credits,
    COALESCE(
        ABS(
            SUM(
                CASE
                    WHEN l.amount < 0 THEN l.amount
                    ELSE 0
                END
            )
        ),
        0
    ) AS total_debits
FROM accounts a
LEFT JOIN transaction_ledger l
    ON l.account_id = a.account_id
LEFT JOIN bank_transactions t
    ON t.transaction_id = l.transaction_id
GROUP BY
    a.account_id,
    a.account_number,
    a.owner_name,
    a.currency,
    a.balance,
    a.account_status;

-- ============================================================
-- 19. RETRIEVAL QUERIES
-- ============================================================

SELECT *
FROM accounts
ORDER BY account_id;

SELECT *
FROM bank_transactions
ORDER BY created_at DESC;

SELECT *
FROM transaction_ledger
ORDER BY ledger_id;

SELECT *
FROM account_transaction_summary
ORDER BY account_id;

-- ============================================================
-- 20. VALIDATION QUERIES
-- ============================================================

-- Identify negative balances.
SELECT *
FROM accounts
WHERE balance < 0;

-- Identify committed transactions without ledger entries.
SELECT
    t.transaction_id,
    t.transaction_type,
    t.amount
FROM bank_transactions t
LEFT JOIN transaction_ledger l
    ON l.transaction_id = t.transaction_id
WHERE t.transaction_status = 'COMMITTED'
GROUP BY
    t.transaction_id,
    t.transaction_type,
    t.amount
HAVING COUNT(l.ledger_id) = 0;

-- Check that every transfer has balanced debit and credit entries.
SELECT
    transaction_id,
    SUM(amount) AS net_amount,
    COUNT(*) AS entry_count
FROM transaction_ledger
GROUP BY transaction_id
HAVING SUM(amount) <> 0;

-- ============================================================
-- 21. AGGREGATION AND EVALUATION
-- ============================================================

SELECT
    transaction_status,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount
FROM bank_transactions
GROUP BY transaction_status
ORDER BY transaction_status;

SELECT
    currency,
    COUNT(*) AS account_count,
    SUM(balance) AS total_balance
FROM accounts
GROUP BY currency;

SELECT
    account_id,
    COUNT(*) AS ledger_entries,
    SUM(amount) AS net_movement
FROM transaction_ledger
GROUP BY account_id
ORDER BY account_id;

-- ============================================================
-- 22. COMMON TABLE EXPRESSION
--
-- Identify accounts with transaction activity exceeding
-- the average transaction amount.
-- ============================================================

WITH account_activity AS (
    SELECT
        account_id,
        COUNT(*) AS operation_count,
        SUM(ABS(amount)) AS gross_movement
    FROM transaction_ledger
    GROUP BY account_id
),
average_activity AS (
    SELECT AVG(gross_movement) AS average_movement
    FROM account_activity
)
SELECT
    aa.account_id,
    a.owner_name,
    aa.operation_count,
    aa.gross_movement
FROM account_activity aa
JOIN accounts a
    ON a.account_id = aa.account_id
CROSS JOIN average_activity av
WHERE aa.gross_movement > av.average_movement
ORDER BY aa.gross_movement DESC;

-- ============================================================
-- 23. TRANSACTION ELIGIBILITY DETERMINATION
-- ============================================================

CREATE OR REPLACE FUNCTION check_transfer_eligibility(
    p_source_account BIGINT,
    p_destination_account BIGINT,
    p_amount BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_source accounts%ROWTYPE;
    v_destination accounts%ROWTYPE;
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RETURN QUERY
        SELECT FALSE, 'Amount must be positive';
        RETURN;
    END IF;

    IF p_source_account = p_destination_account THEN
        RETURN QUERY
        SELECT FALSE, 'Accounts must differ';
        RETURN;
    END IF;

    SELECT *
    INTO v_source
    FROM accounts
    WHERE account_id = p_source_account;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'Source account does not exist';
        RETURN;
    END IF;

    SELECT *
    INTO v_destination
    FROM accounts
    WHERE account_id = p_destination_account;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'Destination account does not exist';
        RETURN;
    END IF;

    IF v_source.account_status <> 'ACTIVE'
       OR v_destination.account_status <> 'ACTIVE' THEN
        RETURN QUERY
        SELECT FALSE, 'An account is not active';
        RETURN;
    END IF;

    IF v_source.currency <> v_destination.currency THEN
        RETURN QUERY
        SELECT FALSE, 'Currency mismatch';
        RETURN;
    END IF;

    IF v_source.balance < p_amount THEN
        RETURN QUERY
        SELECT FALSE, 'Insufficient funds';
        RETURN;
    END IF;

    RETURN QUERY
    SELECT TRUE, 'Eligible';
END;
$$;

SELECT *
FROM check_transfer_eligibility(1, 2, 1000);

SELECT *
FROM check_transfer_eligibility(1, 2, 999999999);

SELECT *
FROM check_transfer_eligibility(1, 5, 1000);

-- ============================================================
-- 24. LEDGER INTEGRITY REPORT
-- ============================================================

SELECT
    t.transaction_id,
    t.transaction_type,
    t.transaction_status,
    t.amount,
    COUNT(l.ledger_id) AS ledger_entry_count,
    COALESCE(SUM(l.amount), 0) AS net_ledger_amount,
    CASE
        WHEN t.transaction_status = 'COMMITTED'
             AND COUNT(l.ledger_id) = 0
            THEN 'INVALID: MISSING LEDGER'
        WHEN t.transaction_type = 'TRANSFER'
             AND t.transaction_status = 'COMMITTED'
             AND COALESCE(SUM(l.amount), 0) <> 0
            THEN 'INVALID: UNBALANCED TRANSFER'
        WHEN t.transaction_status = 'COMMITTED'
            THEN 'COMMITTED'
        ELSE t.transaction_status
    END AS integrity_status
FROM bank_transactions t
LEFT JOIN transaction_ledger l
    ON l.transaction_id = t.transaction_id
GROUP BY
    t.transaction_id,
    t.transaction_type,
    t.transaction_status,
    t.amount
ORDER BY t.transaction_id;

-- ============================================================
-- 25. AUDIT REPORT
-- ============================================================

SELECT
    audit_id,
    transaction_id,
    action,
    details,
    database_user,
    occurred_at
FROM transaction_audit
ORDER BY occurred_at DESC;

-- ============================================================
-- 26. TRANSACTION CONTROL EXAMPLE
--
-- PostgreSQL transactions are connection-scoped.
-- Each BEGIN block must end in COMMIT or ROLLBACK.
--
-- A failed statement normally places the transaction into
-- an aborted state until it is rolled back or recovered
-- to a savepoint.
-- ============================================================

BEGIN;

UPDATE accounts
SET balance = balance + 100
WHERE account_id = 1;

SAVEPOINT before_second_update;

UPDATE accounts
SET balance = balance - 100
WHERE account_id = 2;

ROLLBACK TO SAVEPOINT before_second_update;

COMMIT;

-- ============================================================
-- 27. FINAL ACCOUNTING CHECK
-- ============================================================

SELECT
    currency,
    SUM(balance) AS total_account_balance,
    COUNT(*) AS number_of_accounts
FROM accounts
GROUP BY currency
ORDER BY currency;

SELECT
    SUM(amount) AS total_ledger_movement
FROM transaction_ledger;

SELECT
    COUNT(*) FILTER (
        WHERE transaction_status = 'COMMITTED'
    ) AS committed_count,
    COUNT(*) FILTER (
        WHERE transaction_status = 'FAILED'
    ) AS failed_count,
    COUNT(*) FILTER (
        WHERE transaction_status = 'ROLLED_BACK'
    ) AS rolled_back_count,
    COUNT(*) FILTER (
        WHERE transaction_status = 'PENDING'
    ) AS pending_count
FROM bank_transactions;

-- ============================================================
-- END OF TRANSACTION MANAGEMENT LAB
-- ============================================================
