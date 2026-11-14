/*
===============================================================================
TRANSACTION ISOLATION AND CONCURRENCY CONTROL
PostgreSQL 14+
===============================================================================

This script implements a banking transaction workflow with:

1. Read Uncommitted concepts
2. Read Committed
3. Repeatable Read
4. Serializable
5. MVCC visibility
6. Row-level locking
7. Optimistic concurrency checks
8. Transaction rollback
9. Serializable retry handling
10. Audit records
11. Concurrent transaction demonstrations

IMPORTANT POSTGRESQL SEMANTICS

PostgreSQL maps READ UNCOMMITTED to READ COMMITTED.
Dirty reads are therefore not permitted.

PostgreSQL REPEATABLE READ uses snapshot isolation.
It prevents non-repeatable reads and, in PostgreSQL, phantom reads.
It can still permit serialization anomalies such as write skew.

SERIALIZABLE uses Serializable Snapshot Isolation (SSI).
A transaction may fail with SQLSTATE 40001 and must be retried.

Concurrency demonstrations involving two sessions are provided
as commented operational instructions.
===============================================================================
*/

CREATE SCHEMA IF NOT EXISTS isolation_lab;

SET search_path TO isolation_lab, public;


/* ============================================================================
   1. DOMAIN TABLES
============================================================================ */

CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    account_number VARCHAR(30) NOT NULL UNIQUE,
    account_type VARCHAR(20) NOT NULL
        CHECK (account_type IN ('SAVINGS', 'CURRENT')),
    balance NUMERIC(18, 2) NOT NULL DEFAULT 0
        CHECK (balance >= 0),
    version BIGINT NOT NULL DEFAULT 1
        CHECK (version > 0),
    status VARCHAR(15) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'FROZEN', 'CLOSED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transfers (
    transfer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    destination_account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    amount NUMERIC(18, 2) NOT NULL CHECK (amount > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'COMPLETED', 'REJECTED')),
    idempotency_key UUID NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CONSTRAINT different_transfer_accounts
        CHECK (source_account_id <> destination_account_id)
);

CREATE TABLE IF NOT EXISTS transaction_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transfer_id BIGINT REFERENCES transfers(transfer_id),
    transaction_identifier TEXT NOT NULL,
    operation VARCHAR(30) NOT NULL,
    isolation_level TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS account_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    old_balance NUMERIC(18, 2),
    new_balance NUMERIC(18, 2),
    old_version BIGINT,
    new_version BIGINT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


/* ============================================================================
   2. PERFORMANCE INDEXES
============================================================================ */

CREATE INDEX IF NOT EXISTS idx_accounts_customer
    ON accounts(customer_id);

CREATE INDEX IF NOT EXISTS idx_accounts_status_balance
    ON accounts(status, balance);

CREATE INDEX IF NOT EXISTS idx_transfers_source_created
    ON transfers(source_account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transfers_destination_created
    ON transfers(destination_account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transfers_status
    ON transfers(status, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_transfer
    ON transaction_audit(transfer_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_transaction
    ON transaction_audit(transaction_identifier);


/* ============================================================================
   3. ACCOUNT VERSION AND AUDIT TRIGGER
============================================================================ */

CREATE OR REPLACE FUNCTION maintain_account_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.balance IS DISTINCT FROM OLD.balance THEN
        NEW.version := OLD.version + 1;

        INSERT INTO account_events (
            account_id,
            old_balance,
            new_balance,
            old_version,
            new_version
        )
        VALUES (
            OLD.account_id,
            OLD.balance,
            NEW.balance,
            OLD.version,
            NEW.version
        );
    ELSE
        NEW.version := OLD.version;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_account_version ON accounts;

CREATE TRIGGER trg_account_version
BEFORE UPDATE ON accounts
FOR EACH ROW
EXECUTE FUNCTION maintain_account_version();


/* ============================================================================
   4. AUDIT FUNCTION
============================================================================ */

CREATE OR REPLACE FUNCTION record_transaction_event(
    p_transfer_id BIGINT,
    p_operation TEXT,
    p_details JSONB DEFAULT '{}'::JSONB
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO transaction_audit (
        transfer_id,
        transaction_identifier,
        operation,
        isolation_level,
        details
    )
    VALUES (
        p_transfer_id,
        pg_backend_pid()::TEXT || ':' ||
            txid_current()::TEXT,
        p_operation,
        current_setting('transaction_isolation'),
        p_details
    );
END;
$$;


/* ============================================================================
   5. ATOMIC TRANSFER FUNCTION
============================================================================

   Row locks serialize concurrent modifications to the two accounts.
   Accounts are locked in ascending account_id order to reduce deadlocks.

   The caller controls transaction boundaries and isolation level.
============================================================================ */

CREATE OR REPLACE FUNCTION execute_transfer(
    p_source BIGINT,
    p_destination BIGINT,
    p_amount NUMERIC(18, 2),
    p_idempotency UUID
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_transfer_id BIGINT;
    v_source_balance NUMERIC(18, 2);
    v_destination_balance NUMERIC(18, 2);
    v_first_id BIGINT;
    v_second_id BIGINT;
BEGIN
    IF p_source = p_destination THEN
        RAISE EXCEPTION 'Source and destination must differ';
    END IF;

    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Transfer amount must be positive';
    END IF;

    IF p_idempotency IS NULL THEN
        RAISE EXCEPTION 'Idempotency key is required';
    END IF;

    SELECT transfer_id
    INTO v_transfer_id
    FROM transfers
    WHERE idempotency_key = p_idempotency;

    IF FOUND THEN
        RETURN v_transfer_id;
    END IF;

    v_first_id := LEAST(p_source, p_destination);
    v_second_id := GREATEST(p_source, p_destination);

    -- Consistent lock order reduces deadlock probability.
    PERFORM account_id
    FROM accounts
    WHERE account_id IN (v_first_id, v_second_id)
    ORDER BY account_id
    FOR UPDATE;

    IF (
        SELECT COUNT(*)
        FROM accounts
        WHERE account_id IN (p_source, p_destination)
    ) <> 2 THEN
        RAISE EXCEPTION 'One or both accounts do not exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM accounts
        WHERE account_id IN (p_source, p_destination)
          AND status <> 'ACTIVE'
    ) THEN
        RAISE EXCEPTION 'Account is not active';
    END IF;

    SELECT balance
    INTO v_source_balance
    FROM accounts
    WHERE account_id = p_source;

    SELECT balance
    INTO v_destination_balance
    FROM accounts
    WHERE account_id = p_destination;

    IF v_source_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds';
    END IF;

    INSERT INTO transfers (
        source_account_id,
        destination_account_id,
        amount,
        status,
        idempotency_key
    )
    VALUES (
        p_source,
        p_destination,
        p_amount,
        'PENDING',
        p_idempotency
    )
    RETURNING transfer_id INTO v_transfer_id;

    UPDATE accounts
    SET balance = balance - p_amount
    WHERE account_id = p_source;

    UPDATE accounts
    SET balance = balance + p_amount
    WHERE account_id = p_destination;

    UPDATE transfers
    SET status = 'COMPLETED',
        completed_at = CURRENT_TIMESTAMP
    WHERE transfer_id = v_transfer_id;

    PERFORM record_transaction_event(
        v_transfer_id,
        'TRANSFER_COMPLETED',
        jsonb_build_object(
            'source', p_source,
            'destination', p_destination,
            'amount', p_amount,
            'source_balance_before', v_source_balance,
            'destination_balance_before', v_destination_balance
        )
    );

    RETURN v_transfer_id;
END;
$$;


/* ============================================================================
   6. OPTIMISTIC CONCURRENCY UPDATE
============================================================================

   A version supplied by the application prevents stale updates.
   A zero-row update means that the record was changed by another transaction.
============================================================================ */

CREATE OR REPLACE FUNCTION update_account_balance(
    p_account_id BIGINT,
    p_expected_version BIGINT,
    p_new_balance NUMERIC(18, 2)
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    affected_rows INTEGER;
BEGIN
    IF p_new_balance IS NULL OR p_new_balance < 0 THEN
        RAISE EXCEPTION 'Invalid account balance';
    END IF;

    UPDATE accounts
    SET balance = p_new_balance
    WHERE account_id = p_account_id
      AND version = p_expected_version
      AND status = 'ACTIVE';

    GET DIAGNOSTICS affected_rows = ROW_COUNT;

    RETURN affected_rows = 1;
END;
$$;


/* ============================================================================
   7. DEMONSTRATION DATA
============================================================================ */

INSERT INTO customers (customer_name, email)
VALUES
    ('Aarav Sharma', 'aarav@example.test'),
    ('Meera Verma', 'meera@example.test'),
    ('Kabir Singh', 'kabir@example.test')
ON CONFLICT (email) DO NOTHING;

INSERT INTO accounts (
    customer_id,
    account_number,
    account_type,
    balance
)
SELECT
    customer_id,
    'ACC-' || customer_id::TEXT,
    'SAVINGS',
    CASE customer_name
        WHEN 'Aarav Sharma' THEN 10000.00
        WHEN 'Meera Verma' THEN 6000.00
        ELSE 2000.00
    END
FROM customers
WHERE email IN (
    'aarav@example.test',
    'meera@example.test',
    'kabir@example.test'
)
ON CONFLICT (account_number) DO NOTHING;


/* ============================================================================
   8. READ UNCOMMITTED CONCEPT
============================================================================

   PostgreSQL accepts this command but implements READ COMMITTED behavior.

   Dirty reads remain impossible. A transaction cannot observe another
   transaction's uncommitted modifications.

   The following is executable and demonstrates the effective setting.
============================================================================ */

BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

SHOW transaction_isolation;

SELECT
    account_id,
    account_number,
    balance
FROM accounts
ORDER BY account_id;

ROLLBACK;


/* ============================================================================
   9. READ COMMITTED
============================================================================

   Each statement obtains a fresh snapshot.

   Under concurrent execution, two SELECT statements can return different
   committed values inside the same transaction.
============================================================================ */

BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;

SELECT
    account_id,
    balance,
    version
FROM accounts
ORDER BY account_id;

SELECT
    account_id,
    balance,
    version
FROM accounts
WHERE status = 'ACTIVE'
ORDER BY account_id;

ROLLBACK;


/* ============================================================================
   10. REPEATABLE READ
============================================================================

   The transaction retains its snapshot.

   A concurrent transaction's later commit is not visible to subsequent
   ordinary SELECT statements in this transaction.
============================================================================ */

BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;

SELECT
    account_id,
    balance,
    version
FROM accounts
ORDER BY account_id;

SELECT
    account_id,
    balance,
    version
FROM accounts
WHERE status = 'ACTIVE'
ORDER BY account_id;

ROLLBACK;


/* ============================================================================
   11. SERIALIZABLE
============================================================================

   PostgreSQL uses SSI to detect dangerous dependency structures.
   SQLSTATE 40001 indicates a serialization failure.
============================================================================ */

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

SELECT
    account_id,
    SUM(balance) AS total_balance
FROM accounts
GROUP BY account_id;

SELECT
    COUNT(*) AS active_accounts
FROM accounts
WHERE status = 'ACTIVE';

ROLLBACK;


/* ============================================================================
   12. EXECUTABLE TRANSFER WORKFLOW
============================================================================ */

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

SELECT execute_transfer(
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-1'
    ),
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-2'
    ),
    250.00,
    '11111111-1111-4111-8111-111111111111'::UUID
);

COMMIT;


/* ============================================================================
   13. ROLLBACK DEMONSTRATION
============================================================================

   The transfer is staged and then rolled back.
   Neither account balance nor transfer status is permanently changed.
============================================================================ */

BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;

SELECT execute_transfer(
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-2'
    ),
    (
        SELECT account_id
        FROM accounts
        WHERE account_number = 'ACC-3'
    ),
    100.00,
    '22222222-2222-4222-8222-222222222222'::UUID
);

ROLLBACK;


/* ============================================================================
   14. VALIDATION AND ELIGIBILITY QUERIES
============================================================================ */

-- Account-level integrity validation.
SELECT
    account_id,
    account_number,
    balance,
    version,
    status,
    CASE
        WHEN balance >= 0 AND version > 0 THEN 'VALID'
        ELSE 'INVALID'
    END AS validation_status
FROM accounts
ORDER BY account_id;

-- Transfer eligibility before processing.
SELECT
    source.account_id AS source_account,
    destination.account_id AS destination_account,
    source.balance AS available_balance,
    250.00::NUMERIC(18, 2) AS requested_amount,
    CASE
        WHEN source.status <> 'ACTIVE' THEN 'SOURCE_INACTIVE'
        WHEN destination.status <> 'ACTIVE' THEN 'DESTINATION_INACTIVE'
        WHEN source.balance < 250.00 THEN 'INSUFFICIENT_FUNDS'
        WHEN source.account_id = destination.account_id THEN 'INVALID_ROUTE'
        ELSE 'ELIGIBLE'
    END AS eligibility
FROM accounts source
JOIN accounts destination
    ON destination.account_id <> source.account_id
WHERE source.account_number = 'ACC-1'
  AND destination.account_number = 'ACC-2';


/* ============================================================================
   15. TRANSACTION AGGREGATION AND REPORTING
============================================================================ */

-- Total account balances by account type.
SELECT
    account_type,
    COUNT(*) AS account_count,
    SUM(balance) AS aggregate_balance,
    AVG(balance) AS average_balance
FROM accounts
GROUP BY account_type
ORDER BY account_type;

-- Transfer volume and success rate.
SELECT
    status,
    COUNT(*) AS transfer_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS average_amount
FROM transfers
GROUP BY status
ORDER BY status;

-- Customer account report.
CREATE OR REPLACE VIEW customer_account_report AS
SELECT
    c.customer_id,
    c.customer_name,
    COUNT(a.account_id) AS account_count,
    COALESCE(SUM(a.balance), 0) AS total_balance,
    COUNT(a.account_id) FILTER (
        WHERE a.status = 'ACTIVE'
    ) AS active_account_count
FROM customers c
LEFT JOIN accounts a
    ON a.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name;

SELECT *
FROM customer_account_report
ORDER BY customer_id;


/* ============================================================================
   16. CTE: ACCOUNT TRANSACTION HISTORY
============================================================================ */

WITH account_activity AS (
    SELECT
        source_account_id AS account_id,
        amount,
        'DEBIT'::TEXT AS direction,
        created_at
    FROM transfers
    WHERE status = 'COMPLETED'

    UNION ALL

    SELECT
        destination_account_id AS account_id,
        amount,
        'CREDIT'::TEXT AS direction,
        created_at
    FROM transfers
    WHERE status = 'COMPLETED'
),
activity_totals AS (
    SELECT
        account_id,
        COUNT(*) AS transaction_count,
        SUM(amount) FILTER (
            WHERE direction = 'DEBIT'
        ) AS total_debits,
        SUM(amount) FILTER (
            WHERE direction = 'CREDIT'
        ) AS total_credits
    FROM account_activity
    GROUP BY account_id
)
SELECT
    a.account_number,
    COALESCE(t.transaction_count, 0) AS transaction_count,
    COALESCE(t.total_debits, 0) AS total_debits,
    COALESCE(t.total_credits, 0) AS total_credits
FROM accounts a
LEFT JOIN activity_totals t
    ON t.account_id = a.account_id
ORDER BY a.account_id;


/* ============================================================================
   17. AUDIT REPORT
============================================================================ */

SELECT
    audit_id,
    transfer_id,
    transaction_identifier,
    operation,
    isolation_level,
    details,
    recorded_at
FROM transaction_audit
ORDER BY audit_id;


/* ============================================================================
   18. VERSION HISTORY
============================================================================ */

SELECT
    account_id,
    old_balance,
    new_balance,
    old_version,
    new_version,
    changed_at
FROM account_events
ORDER BY event_id;


/* ============================================================================
   19. CONCURRENT SESSION EXPERIMENTS
============================================================================

   Run the following experiments in TWO separate PostgreSQL sessions.
   Execute Session A and Session B statements in the specified order.

   EXPERIMENT A: READ COMMITTED NON-REPEATABLE READ

   SESSION A:
       BEGIN ISOLATION LEVEL READ COMMITTED;
       SELECT balance FROM isolation_lab.accounts
       WHERE account_id = 1;

   SESSION B:
       BEGIN;
       UPDATE isolation_lab.accounts
       SET balance = balance + 100
       WHERE account_id = 1;
       COMMIT;

   SESSION A:
       SELECT balance FROM isolation_lab.accounts
       WHERE account_id = 1;
       COMMIT;

   Expected: The second SELECT can see the committed update.

   EXPERIMENT B: REPEATABLE READ SNAPSHOT

   SESSION A:
       BEGIN ISOLATION LEVEL REPEATABLE READ;
       SELECT balance FROM isolation_lab.accounts
       WHERE account_id = 1;

   SESSION B:
       BEGIN;
       UPDATE isolation_lab.accounts
       SET balance = balance + 100
       WHERE account_id = 1;
       COMMIT;

   SESSION A:
       SELECT balance FROM isolation_lab.accounts
       WHERE account_id = 1;
       COMMIT;

   Expected: SESSION A sees its original snapshot.

   EXPERIMENT C: REPEATABLE READ CONCURRENT UPDATE

   SESSION A:
       BEGIN ISOLATION LEVEL REPEATABLE READ;
       UPDATE isolation_lab.accounts
       SET balance = balance + 50
       WHERE account_id = 1;

   SESSION B:
       UPDATE isolation_lab.accounts
       SET balance = balance + 100
       WHERE account_id = 1;
       COMMIT;

   SESSION A:
       COMMIT;

   Expected: SESSION A can receive SQLSTATE 40001.

   EXPERIMENT D: SERIALIZABLE WRITE SKEW

   Reset test data before execution.

   SESSION A:
       BEGIN ISOLATION LEVEL SERIALIZABLE;
       SELECT COUNT(*) FROM isolation_lab.accounts
       WHERE status = 'ACTIVE';
       UPDATE isolation_lab.accounts
       SET status = 'FROZEN'
       WHERE account_id = 1;

   SESSION B:
       BEGIN ISOLATION LEVEL SERIALIZABLE;
       SELECT COUNT(*) FROM isolation_lab.accounts
       WHERE status = 'ACTIVE';
       UPDATE isolation_lab.accounts
       SET status = 'FROZEN'
       WHERE account_id = 2;
       COMMIT;

   SESSION A:
       COMMIT;

   Expected: PostgreSQL may abort a transaction to prevent a
   non-serializable dependency structure.

============================================================================ */


/* ============================================================================
   20. OPERATIONAL GUIDANCE
============================================================================

   Isolation selection:

   READ UNCOMMITTED:
       PostgreSQL treats this as READ COMMITTED.

   READ COMMITTED:
       Appropriate for many ordinary application operations.
       Each statement can observe newly committed data.

   REPEATABLE READ:
       Appropriate when a consistent transaction-wide snapshot is needed.
       Concurrent updates can produce serialization failures.
       Predicate anomalies such as write skew remain possible.

   SERIALIZABLE:
       Appropriate when the business invariant requires serial execution.
       Applications must retry SQLSTATE 40001.

   Locking:
       SELECT ... FOR UPDATE obtains row-level locks.
       Consistent lock ordering reduces deadlock risk.

   Security:
       Use least-privilege database roles.
       Do not expose raw SQL construction to untrusted input.
       Use parameterized queries.
       Restrict audit-table modifications.

   Performance:
       Long-running transactions retain old snapshots and can delay vacuum.
       Index predicate columns used by frequent transactional queries.
       Keep transactions short.
       Avoid unnecessary serializable transactions.
       Implement bounded retries with backoff.

   The application must treat transaction errors as expected control-flow
   conditions, not as successful business operations.
============================================================================ */
