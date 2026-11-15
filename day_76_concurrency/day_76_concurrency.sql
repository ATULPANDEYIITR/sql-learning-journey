/*
===============================================================================
CONCURRENCY, LOCKS, CONCURRENT TRANSACTIONS AND RACE CONDITIONS
PostgreSQL 15+

Demonstrates:
- ACID transactions
- Concurrent database sessions
- Row-level locking
- SELECT FOR UPDATE
- Deadlock prevention through deterministic lock ordering
- Optimistic concurrency through version columns
- Pessimistic concurrency through row locks
- Idempotent transaction requests
- Transaction rollback
- Unique constraints
- Advisory locks
- Transaction isolation
- Serialization failures
- Audit records
- Operational reporting

Run this script in a PostgreSQL database using psql.

The transfer function does not commit transactions itself.
The calling session controls COMMIT and ROLLBACK.
===============================================================================
*/

BEGIN;

CREATE SCHEMA IF NOT EXISTS concurrency_lab;

SET search_path TO concurrency_lab, public;


-- ============================================================================
-- 1. DOMAIN TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS accounts (
    account_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    account_number VARCHAR(30) NOT NULL UNIQUE,

    account_name VARCHAR(120) NOT NULL,

    balance NUMERIC(18, 2) NOT NULL DEFAULT 0,

    version BIGINT NOT NULL DEFAULT 0,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT positive_account_balance
        CHECK (balance >= 0),

    CONSTRAINT valid_account_version
        CHECK (version >= 0),

    CONSTRAINT valid_account_status
        CHECK (
            status IN ('ACTIVE', 'FROZEN', 'CLOSED')
        )
);


CREATE TABLE IF NOT EXISTS transaction_requests (
    transaction_id UUID PRIMARY KEY,

    idempotency_key VARCHAR(100) NOT NULL UNIQUE,

    source_account_id BIGINT NOT NULL
        REFERENCES accounts(account_id),

    destination_account_id BIGINT NOT NULL
        REFERENCES accounts(account_id),

    amount NUMERIC(18, 2) NOT NULL,

    status VARCHAR(20) NOT NULL,

    failure_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    completed_at TIMESTAMPTZ,

    CONSTRAINT positive_transfer_amount
        CHECK (amount > 0),

    CONSTRAINT different_transfer_accounts
        CHECK (source_account_id <> destination_account_id),

    CONSTRAINT valid_transaction_status
        CHECK (
            status IN (
                'PROCESSING',
                'COMMITTED',
                'REJECTED'
            )
        )
);


CREATE TABLE IF NOT EXISTS account_ledger (
    ledger_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transaction_id UUID NOT NULL
        REFERENCES transaction_requests(transaction_id),

    account_id BIGINT NOT NULL
        REFERENCES accounts(account_id),

    entry_type VARCHAR(10) NOT NULL,

    amount NUMERIC(18, 2) NOT NULL,

    balance_after NUMERIC(18, 2) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_ledger_entry_type
        CHECK (entry_type IN ('DEBIT', 'CREDIT')),

    CONSTRAINT positive_ledger_amount
        CHECK (amount > 0),

    CONSTRAINT nonnegative_ledger_balance
        CHECK (balance_after >= 0),

    CONSTRAINT unique_transaction_account_entry
        UNIQUE (transaction_id, account_id)
);


CREATE TABLE IF NOT EXISTS concurrency_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transaction_id UUID,

    event_type VARCHAR(40) NOT NULL,

    event_details JSONB NOT NULL DEFAULT '{}'::JSONB,

    session_id INTEGER NOT NULL DEFAULT pg_backend_pid(),

    event_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================================
-- 2. PERFORMANCE INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_transactions_source
    ON transaction_requests(source_account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_destination
    ON transaction_requests(destination_account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_status
    ON transaction_requests(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ledger_account_time
    ON account_ledger(account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_event_time
    ON concurrency_audit(event_time DESC);


-- ============================================================================
-- 3. ACCOUNT UPDATE TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION update_account_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


DROP TRIGGER IF EXISTS trg_account_timestamp ON accounts;

CREATE TRIGGER trg_account_timestamp
BEFORE UPDATE ON accounts
FOR EACH ROW
EXECUTE FUNCTION update_account_timestamp();


-- ============================================================================
-- 4. AUDIT FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION record_concurrency_event(
    p_transaction_id UUID,
    p_event_type VARCHAR(40),
    p_details JSONB DEFAULT '{}'::JSONB
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO concurrency_audit (
        transaction_id,
        event_type,
        event_details
    )
    VALUES (
        p_transaction_id,
        p_event_type,
        p_details
    );
END;
$$;


-- ============================================================================
-- 5. TRANSACTION PROCESSING FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION transfer_funds(
    p_source_account_id BIGINT,
    p_destination_account_id BIGINT,
    p_amount NUMERIC(18, 2),
    p_idempotency_key VARCHAR(100)
)
RETURNS TABLE (
    result_transaction_id UUID,
    result_status VARCHAR(20),
    result_message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction_id UUID;
    v_existing transaction_requests%ROWTYPE;

    v_source_balance NUMERIC(18, 2);
    v_destination_balance NUMERIC(18, 2);

    v_source_version BIGINT;
    v_destination_version BIGINT;

    v_account_id BIGINT;
    v_inserted BOOLEAN;

BEGIN

    -- Validate request before taking database locks.
    IF p_source_account_id = p_destination_account_id THEN
        RAISE EXCEPTION
            'Source and destination must differ';
    END IF;

    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION
            'Transfer amount must be positive';
    END IF;

    IF p_idempotency_key IS NULL
       OR LENGTH(TRIM(p_idempotency_key)) = 0 THEN
        RAISE EXCEPTION
            'Idempotency key is required';
    END IF;

    IF p_source_account_id <= 0
       OR p_destination_account_id <= 0 THEN
        RAISE EXCEPTION
            'Invalid account identifier';
    END IF;


    /*
     * Create a request using a unique idempotency key.
     *
     * Concurrent requests using the same key are coordinated
     * by the unique constraint.
     *
     * INSERT ON CONFLICT waits when another transaction is
     * currently inserting the same key.
     */

    v_transaction_id := gen_random_uuid();

    INSERT INTO transaction_requests (
        transaction_id,
        idempotency_key,
        source_account_id,
        destination_account_id,
        amount,
        status
    )
    VALUES (
        v_transaction_id,
        p_idempotency_key,
        p_source_account_id,
        p_destination_account_id,
        p_amount,
        'PROCESSING'
    )
    ON CONFLICT (idempotency_key) DO NOTHING
    RETURNING TRUE INTO v_inserted;


    IF NOT COALESCE(v_inserted, FALSE) THEN

        SELECT *
        INTO STRICT v_existing
        FROM transaction_requests
        WHERE idempotency_key = p_idempotency_key;

        IF v_existing.source_account_id <> p_source_account_id
           OR v_existing.destination_account_id <>
              p_destination_account_id
           OR v_existing.amount <> p_amount THEN

            RAISE EXCEPTION
                'Idempotency key reused with different parameters';
        END IF;

        RETURN QUERY
        SELECT
            v_existing.transaction_id,
            v_existing.status,
            COALESCE(
                v_existing.failure_reason,
                'Existing transaction request'
            );

        RETURN;
    END IF;


    /*
     * Lock both accounts in ascending ID order.
     *
     * This avoids inconsistent lock ordering between
     * simultaneous A-to-B and B-to-A transfers.
     *
     * FOR UPDATE prevents concurrent modifications of
     * the selected account rows.
     */

    FOR v_account_id IN
        SELECT a.account_id
        FROM accounts a
        WHERE a.account_id IN (
            p_source_account_id,
            p_destination_account_id
        )
        ORDER BY a.account_id
        FOR UPDATE
    LOOP
        NULL;
    END LOOP;


    -- Read source and destination only after acquiring locks.
    SELECT balance, version
    INTO v_source_balance, v_source_version
    FROM accounts
    WHERE account_id = p_source_account_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Source account does not exist';
    END IF;


    SELECT balance, version
    INTO v_destination_balance, v_destination_version
    FROM accounts
    WHERE account_id = p_destination_account_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Destination account does not exist';
    END IF;


    -- Frozen or closed accounts cannot participate.
    IF NOT EXISTS (
        SELECT 1
        FROM accounts
        WHERE account_id = p_source_account_id
          AND status = 'ACTIVE'
    ) THEN
        RAISE EXCEPTION
            'Source account is not active';
    END IF;


    IF NOT EXISTS (
        SELECT 1
        FROM accounts
        WHERE account_id = p_destination_account_id
          AND status = 'ACTIVE'
    ) THEN
        RAISE EXCEPTION
            'Destination account is not active';
    END IF;


    -- Business validation occurs before balance modification.
    IF v_source_balance < p_amount THEN

        UPDATE transaction_requests
        SET status = 'REJECTED',
            failure_reason = 'Insufficient funds',
            completed_at = CURRENT_TIMESTAMP
        WHERE transaction_id = v_transaction_id;

        PERFORM record_concurrency_event(
            v_transaction_id,
            'TRANSACTION_REJECTED',
            jsonb_build_object(
                'reason', 'Insufficient funds',
                'source_balance', v_source_balance,
                'requested_amount', p_amount
            )
        );

        RETURN QUERY
        SELECT
            v_transaction_id,
            'REJECTED'::VARCHAR(20),
            'Insufficient funds'::TEXT;

        RETURN;
    END IF;


    /*
     * Account updates occur while both row locks remain held.
     * Version numbers increase with every successful update.
     */

    UPDATE accounts
    SET balance = balance - p_amount,
        version = version + 1
    WHERE account_id = p_source_account_id
      AND version = v_source_version;


    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Source account version conflict';
    END IF;


    UPDATE accounts
    SET balance = balance + p_amount,
        version = version + 1
    WHERE account_id = p_destination_account_id
      AND version = v_destination_version;


    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Destination account version conflict';
    END IF;


    -- Record the debit and credit in the ledger.
    INSERT INTO account_ledger (
        transaction_id,
        account_id,
        entry_type,
        amount,
        balance_after
    )
    SELECT
        v_transaction_id,
        account_id,
        'DEBIT',
        p_amount,
        balance
    FROM accounts
    WHERE account_id = p_source_account_id;


    INSERT INTO account_ledger (
        transaction_id,
        account_id,
        entry_type,
        amount,
        balance_after
    )
    SELECT
        v_transaction_id,
        account_id,
        'CREDIT',
        p_amount,
        balance
    FROM accounts
    WHERE account_id = p_destination_account_id;


    UPDATE transaction_requests
    SET status = 'COMMITTED',
        failure_reason = NULL,
        completed_at = CURRENT_TIMESTAMP
    WHERE transaction_id = v_transaction_id;


    PERFORM record_concurrency_event(
        v_transaction_id,
        'TRANSACTION_COMMITTED',
        jsonb_build_object(
            'source_account_id', p_source_account_id,
            'destination_account_id', p_destination_account_id,
            'amount', p_amount,
            'source_version', v_source_version + 1,
            'destination_version', v_destination_version + 1
        )
    );


    RETURN QUERY
    SELECT
        v_transaction_id,
        'COMMITTED'::VARCHAR(20),
        'Transfer completed successfully'::TEXT;

END;
$$;


-- ============================================================================
-- 6. STORED PROCEDURE
-- ============================================================================

CREATE OR REPLACE PROCEDURE process_transfer(
    p_source_account_id BIGINT,
    p_destination_account_id BIGINT,
    p_amount NUMERIC(18, 2),
    p_idempotency_key VARCHAR(100)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_result RECORD;
BEGIN

    SELECT *
    INTO v_result
    FROM transfer_funds(
        p_source_account_id,
        p_destination_account_id,
        p_amount,
        p_idempotency_key
    );

    RAISE NOTICE
        'Transaction %, status %, message %',
        v_result.result_transaction_id,
        v_result.result_status,
        v_result.result_message;

END;
$$;


-- ============================================================================
-- 7. OPTIMISTIC CONCURRENCY FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION update_balance_optimistic(
    p_account_id BIGINT,
    p_expected_version BIGINT,
    p_new_balance NUMERIC(18, 2)
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows INTEGER;
BEGIN

    IF p_new_balance < 0 THEN
        RAISE EXCEPTION
            'Balance cannot be negative';
    END IF;

    UPDATE accounts
    SET balance = p_new_balance,
        version = version + 1
    WHERE account_id = p_account_id
      AND version = p_expected_version
      AND status = 'ACTIVE';

    GET DIAGNOSTICS v_rows = ROW_COUNT;

    IF v_rows = 0 THEN
        RETURN FALSE;
    END IF;

    RETURN TRUE;

END;
$$;


-- ============================================================================
-- 8. PESSIMISTIC LOCKING DEMONSTRATION
-- ============================================================================

CREATE OR REPLACE FUNCTION lock_account(
    p_account_id BIGINT
)
RETURNS TABLE (
    locked_account_id BIGINT,
    current_balance NUMERIC(18, 2),
    current_version BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN

    RETURN QUERY
    SELECT
        account_id,
        balance,
        version
    FROM accounts
    WHERE account_id = p_account_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Account not found: %', p_account_id;
    END IF;

END;
$$;


-- ============================================================================
-- 9. ADVISORY LOCK DEMONSTRATION
-- ============================================================================

CREATE OR REPLACE FUNCTION acquire_account_advisory_lock(
    p_account_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN

    RETURN pg_try_advisory_xact_lock(
        741852,
        p_account_id::INTEGER
    );

END;
$$;


-- ============================================================================
-- 10. REPORTING VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW account_transaction_summary AS
SELECT
    a.account_id,
    a.account_number,
    a.account_name,
    a.balance,
    a.version,
    a.status,

    COUNT(DISTINCT t.transaction_id) AS transaction_count,

    COALESCE(
        SUM(
            CASE
                WHEN l.entry_type = 'DEBIT'
                THEN l.amount
                ELSE 0
            END
        ),
        0
    ) AS total_debits,

    COALESCE(
        SUM(
            CASE
                WHEN l.entry_type = 'CREDIT'
                THEN l.amount
                ELSE 0
            END
        ),
        0
    ) AS total_credits

FROM accounts a

LEFT JOIN account_ledger l
    ON l.account_id = a.account_id

LEFT JOIN transaction_requests t
    ON t.transaction_id = l.transaction_id

GROUP BY
    a.account_id,
    a.account_number,
    a.account_name,
    a.balance,
    a.version,
    a.status;


CREATE OR REPLACE VIEW transaction_monitor AS
SELECT
    t.transaction_id,
    t.idempotency_key,
    source.account_number AS source_account,
    destination.account_number AS destination_account,
    t.amount,
    t.status,
    t.failure_reason,
    t.created_at,
    t.completed_at

FROM transaction_requests t

JOIN accounts source
    ON source.account_id = t.source_account_id

JOIN accounts destination
    ON destination.account_id = t.destination_account_id;


-- ============================================================================
-- 11. SAMPLE DATA
-- ============================================================================

INSERT INTO accounts (
    account_number,
    account_name,
    balance
)
VALUES
    ('ACC-1001', 'Operating Account', 100000.00),
    ('ACC-1002', 'Settlement Account', 50000.00),
    ('ACC-1003', 'Reserve Account', 25000.00),
    ('ACC-1004', 'Frozen Account', 10000.00)
ON CONFLICT (account_number) DO NOTHING;


UPDATE accounts
SET status = 'FROZEN'
WHERE account_number = 'ACC-1004';


COMMIT;


-- ============================================================================
-- 12. SAMPLE TRANSACTION
-- ============================================================================

BEGIN;

SELECT *
FROM transfer_funds(
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-1001'
    ),
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-1002'
    ),
    1000.00,
    'PAYMENT-1001'
);

COMMIT;


-- ============================================================================
-- 13. IDEMPOTENCY TEST
-- ============================================================================

BEGIN;

-- Repeating the same key returns the original transaction result.
SELECT *
FROM transfer_funds(
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-1001'
    ),
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-1002'
    ),
    1000.00,
    'PAYMENT-1001'
);

COMMIT;


-- ============================================================================
-- 14. VALIDATION AND FAILURE CASES
-- ============================================================================

-- Insufficient funds: request is rejected without changing balances.
BEGIN;

SELECT *
FROM transfer_funds(
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-1001'
    ),
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-1003'
    ),
    999999999.00,
    'INSUFFICIENT-001'
);

COMMIT;


-- Frozen account: this transaction raises an exception.
-- Execute separately if testing the failure path.
--
-- BEGIN;
-- SELECT *
-- FROM transfer_funds(
--     (SELECT account_id FROM accounts
--      WHERE account_number = 'ACC-1004'),
--     (SELECT account_id FROM accounts
--      WHERE account_number = 'ACC-1002'),
--     100.00,
--     'FROZEN-001'
-- );
-- ROLLBACK;


-- Optimistic update: expected version must match.
BEGIN;

SELECT update_balance_optimistic(
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-1003'
    ),
    (
        SELECT version
        FROM accounts
        WHERE account_number = 'ACC-1003'
    ),
    26000.00
) AS optimistic_update_success;

COMMIT;


-- ============================================================================
-- 15. TRANSACTION ROLLBACK DEMONSTRATION
-- ============================================================================

BEGIN;

UPDATE accounts
SET balance = balance - 500
WHERE account_number = 'ACC-1001';

-- The update is deliberately rolled back.
ROLLBACK;


-- ============================================================================
-- 16. RETRIEVAL QUERIES
-- ============================================================================

SELECT *
FROM accounts
ORDER BY account_id;


SELECT *
FROM transaction_monitor
ORDER BY created_at DESC;


SELECT *
FROM account_ledger
ORDER BY created_at DESC;


-- ============================================================================
-- 17. AGGREGATION AND REPORTING
-- ============================================================================

SELECT *
FROM account_transaction_summary
ORDER BY account_number;


SELECT
    status,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount
FROM transaction_requests
GROUP BY status
ORDER BY status;


SELECT
    entry_type,
    COUNT(*) AS entry_count,
    SUM(amount) AS aggregate_amount
FROM account_ledger
GROUP BY entry_type;


-- ============================================================================
-- 18. CTE-BASED TRANSACTION EVALUATION
-- ============================================================================

WITH transaction_statistics AS (
    SELECT
        source_account_id AS account_id,
        COUNT(*) AS outgoing_count,
        SUM(amount) AS outgoing_amount
    FROM transaction_requests
    WHERE status = 'COMMITTED'
    GROUP BY source_account_id
),

incoming_statistics AS (
    SELECT
        destination_account_id AS account_id,
        COUNT(*) AS incoming_count,
        SUM(amount) AS incoming_amount
    FROM transaction_requests
    WHERE status = 'COMMITTED'
    GROUP BY destination_account_id
)

SELECT
    a.account_number,
    a.balance,
    COALESCE(outgoing.outgoing_count, 0) AS outgoing_count,
    COALESCE(outgoing.outgoing_amount, 0) AS outgoing_amount,
    COALESCE(incoming.incoming_count, 0) AS incoming_count,
    COALESCE(incoming.incoming_amount, 0) AS incoming_amount

FROM accounts a

LEFT JOIN transaction_statistics outgoing
    ON outgoing.account_id = a.account_id

LEFT JOIN incoming_statistics incoming
    ON incoming.account_id = a.account_id

ORDER BY a.account_number;


-- ============================================================================
-- 19. INVARIANT VALIDATION
-- ============================================================================

-- No account can have a negative balance.
SELECT *
FROM accounts
WHERE balance < 0;


-- Every committed transfer must have two ledger entries.
SELECT
    t.transaction_id,
    COUNT(l.ledger_id) AS ledger_entries
FROM transaction_requests t
LEFT JOIN account_ledger l
    ON l.transaction_id = t.transaction_id
WHERE t.status = 'COMMITTED'
GROUP BY t.transaction_id
HAVING COUNT(l.ledger_id) <> 2;


-- Debit and credit entries must balance.
SELECT
    transaction_id,
    SUM(
        CASE
            WHEN entry_type = 'DEBIT' THEN -amount
            WHEN entry_type = 'CREDIT' THEN amount
        END
    ) AS net_amount
FROM account_ledger
GROUP BY transaction_id
HAVING SUM(
    CASE
        WHEN entry_type = 'DEBIT' THEN -amount
        WHEN entry_type = 'CREDIT' THEN amount
    END
) <> 0;


-- ============================================================================
-- 20. CONCURRENCY DIAGNOSTICS
-- ============================================================================

-- Inspect active sessions and their transaction states.
SELECT
    pid,
    usename,
    state,
    wait_event_type,
    wait_event,
    query_start,
    LEFT(query, 120) AS current_query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY query_start DESC NULLS LAST;


-- Identify blocked sessions and their blocking sessions.
SELECT
    blocked.pid AS blocked_pid,
    blocking.pid AS blocking_pid,
    blocked.wait_event_type,
    blocked.wait_event,
    LEFT(blocked.query, 100) AS blocked_query,
    LEFT(blocking.query, 100) AS blocking_query

FROM pg_stat_activity blocked

CROSS JOIN LATERAL
    UNNEST(pg_blocking_pids(blocked.pid)) AS blocking_pid(pid)

JOIN pg_stat_activity blocking
    ON blocking.pid = blocking_pid.pid;


-- Inspect recent transaction audit events.
SELECT *
FROM concurrency_audit
ORDER BY event_time DESC
LIMIT 100;


-- ============================================================================
-- 21. DEADLOCK AND ISOLATION TESTING GUIDE
-- ============================================================================
--
-- Use two independent psql sessions.
--
-- Session A:
--
-- BEGIN;
-- SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
-- SELECT * FROM accounts
-- WHERE account_number = 'ACC-1001'
-- FOR UPDATE;
-- SELECT pg_sleep(5);
-- COMMIT;
--
-- Session B:
--
-- BEGIN;
-- SELECT * FROM accounts
-- WHERE account_number = 'ACC-1001'
-- FOR UPDATE;
-- COMMIT;
--
-- Session B waits until Session A commits.
--
-- Deadlock demonstration:
--
-- Session A:
-- BEGIN;
-- SELECT * FROM accounts
-- WHERE account_number = 'ACC-1001'
-- FOR UPDATE;
-- SELECT pg_sleep(3);
-- SELECT * FROM accounts
-- WHERE account_number = 'ACC-1002'
-- FOR UPDATE;
-- COMMIT;
--
-- Session B, started while A sleeps:
-- BEGIN;
-- SELECT * FROM accounts
-- WHERE account_number = 'ACC-1002'
-- FOR UPDATE;
-- SELECT pg_sleep(3);
-- SELECT * FROM accounts
-- WHERE account_number = 'ACC-1001'
-- FOR UPDATE;
-- COMMIT;
--
-- PostgreSQL detects the deadlock and aborts one transaction.
--
-- Production applications should retry deadlock victims
-- using bounded retries and randomized backoff.
--
-- SERIALIZABLE isolation:
--
-- BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
-- SELECT SUM(balance) FROM accounts;
-- COMMIT;
--
-- Applications must handle SQLSTATE 40001 by retrying
-- the complete transaction.
--
-- Common concurrency SQLSTATE codes:
-- 40001 = Serialization failure
-- 40P01 = Deadlock detected
-- 55P03 = Lock not available
--
-- A failed SQL statement does not imply that an entire
-- business operation was successfully completed.
--
-- ============================================================================
-- END OF CONCURRENCY MANAGEMENT SCRIPT
-- ============================================================================
