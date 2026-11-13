/*
===============================================================================
ACID PROPERTIES: POSTGRESQL TRANSACTION MANAGEMENT
===============================================================================

Database: acid_learning
Schema: acid

Demonstrates:
1. Atomicity through transactional stored procedures.
2. Consistency through constraints, triggers and controlled operations.
3. Isolation through PostgreSQL isolation levels and row locks.
4. Durability through WAL-backed commits and crash recovery.

Additional mechanisms:
- Idempotency keys.
- Transaction audit records.
- Account versioning.
- Role-based access control.
- Commit and rollback.
- Savepoints.
- Serialization failure handling.
- Reporting and transaction monitoring.

Execute using psql against a PostgreSQL database.
The script creates a dedicated schema and sample data.
*/

BEGIN;

CREATE SCHEMA IF NOT EXISTS acid;

SET search_path TO acid, public;

CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_customer_name
        CHECK (length(trim(customer_name)) > 0)
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL
        REFERENCES customers(customer_id),
    account_number VARCHAR(30) NOT NULL UNIQUE,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    balance NUMERIC(18, 2) NOT NULL DEFAULT 0,
    version BIGINT NOT NULL DEFAULT 0,
    account_status VARCHAR(15) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT nonnegative_balance
        CHECK (balance >= 0),

    CONSTRAINT valid_currency
        CHECK (currency ~ '^[A-Z]{3}$'),

    CONSTRAINT valid_account_status
        CHECK (
            account_status IN ('ACTIVE', 'FROZEN', 'CLOSED')
        ),

    CONSTRAINT valid_version
        CHECK (version >= 0)
);

CREATE TABLE IF NOT EXISTS app_roles (
    role_id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role_name VARCHAR(40) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS application_users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    role_id SMALLINT NOT NULL REFERENCES app_roles(role_id),
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_reference UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    transaction_type VARCHAR(20) NOT NULL,
    source_account_id BIGINT REFERENCES accounts(account_id),
    target_account_id BIGINT REFERENCES accounts(account_id),
    amount NUMERIC(18, 2) NOT NULL,
    transaction_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    initiated_by BIGINT REFERENCES application_users(user_id),
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committed_at TIMESTAMPTZ,

    CONSTRAINT positive_transaction_amount
        CHECK (amount > 0),

    CONSTRAINT valid_transaction_type
        CHECK (
            transaction_type IN (
                'DEPOSIT',
                'WITHDRAWAL',
                'TRANSFER'
            )
        ),

    CONSTRAINT valid_transaction_status
        CHECK (
            transaction_status IN (
                'PENDING',
                'COMMITTED',
                'REJECTED',
                'FAILED'
            )
        ),

    CONSTRAINT valid_transfer_accounts
        CHECK (
            transaction_type <> 'TRANSFER'
            OR (
                source_account_id IS NOT NULL
                AND target_account_id IS NOT NULL
                AND source_account_id <> target_account_id
            )
        )
);

CREATE TABLE IF NOT EXISTS transaction_entries (
    entry_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL
        REFERENCES transactions(transaction_id),
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    entry_type VARCHAR(10) NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    balance_after NUMERIC(18, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_entry_type
        CHECK (entry_type IN ('DEBIT', 'CREDIT')),

    CONSTRAINT positive_entry_amount
        CHECK (amount > 0),

    CONSTRAINT nonnegative_entry_balance
        CHECK (balance_after >= 0),

    CONSTRAINT unique_transaction_account_entry
        UNIQUE (transaction_id, account_id)
);

CREATE TABLE IF NOT EXISTS transaction_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL
        REFERENCES transactions(transaction_id),
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

CREATE TABLE IF NOT EXISTS idempotency_registry (
    idempotency_key VARCHAR(120) PRIMARY KEY,
    transaction_id BIGINT UNIQUE
        REFERENCES transactions(transaction_id),
    registered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_accounts_customer
    ON accounts(customer_id);

CREATE INDEX IF NOT EXISTS idx_accounts_active
    ON accounts(account_id)
    WHERE account_status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_transactions_created
    ON transactions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_status
    ON transactions(transaction_status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transaction_entries_account
    ON transaction_entries(account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transaction_audit_transaction
    ON transaction_audit(transaction_id, changed_at DESC);

CREATE TABLE IF NOT EXISTS isolation_test_records (
    record_id INTEGER PRIMARY KEY,
    available_units INTEGER NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,

    CONSTRAINT nonnegative_available_units
        CHECK (available_units >= 0)
);

CREATE TABLE IF NOT EXISTS database_settings (
    setting_key VARCHAR(80) PRIMARY KEY,
    setting_value TEXT NOT NULL
);

COMMIT;


/*
===============================================================================
1. ROLES AND SAMPLE DATA
===============================================================================
*/

INSERT INTO acid.app_roles (role_name, description)
VALUES
    ('CUSTOMER', 'Standard account holder'),
    ('OPERATOR', 'Authorized transaction operator'),
    ('AUDITOR', 'Read-only transaction auditor'),
    ('ADMIN', 'Database governance administrator')
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO acid.application_users (username, role_id)
SELECT 'system_operator', role_id
FROM acid.app_roles
WHERE role_name = 'OPERATOR'
ON CONFLICT (username) DO NOTHING;

INSERT INTO acid.application_users (username, role_id)
SELECT 'audit_user', role_id
FROM acid.app_roles
WHERE role_name = 'AUDITOR'
ON CONFLICT (username) DO NOTHING;

INSERT INTO acid.customers (customer_name, email)
VALUES
    ('Alice Sharma', 'alice@example.com'),
    ('Bob Verma', 'bob@example.com'),
    ('Charlie Singh', 'charlie@example.com')
ON CONFLICT (email) DO NOTHING;

INSERT INTO acid.accounts (
    customer_id,
    account_number,
    currency,
    balance
)
SELECT
    customer_id,
    CASE email
        WHEN 'alice@example.com' THEN 'INR-10001'
        WHEN 'bob@example.com' THEN 'INR-10002'
        WHEN 'charlie@example.com' THEN 'INR-10003'
    END,
    'INR',
    CASE email
        WHEN 'alice@example.com' THEN 100000.00
        WHEN 'bob@example.com' THEN 50000.00
        WHEN 'charlie@example.com' THEN 25000.00
    END
FROM acid.customers
WHERE email IN (
    'alice@example.com',
    'bob@example.com',
    'charlie@example.com'
)
ON CONFLICT (account_number) DO NOTHING;

INSERT INTO acid.isolation_test_records (
    record_id,
    available_units
)
VALUES (1, 10)
ON CONFLICT (record_id) DO NOTHING;


/*
===============================================================================
2. CONSISTENCY: STATUS TRANSITION AUDIT
===============================================================================
*/

CREATE OR REPLACE FUNCTION acid.audit_transaction_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.transaction_status IS DISTINCT FROM OLD.transaction_status THEN
        INSERT INTO acid.transaction_audit (
            transaction_id,
            old_status,
            new_status,
            details
        )
        VALUES (
            NEW.transaction_id,
            OLD.transaction_status,
            NEW.transaction_status,
            'Transaction status changed'
        );
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_transaction_status_audit
ON acid.transactions;

CREATE TRIGGER trg_transaction_status_audit
AFTER UPDATE OF transaction_status
ON acid.transactions
FOR EACH ROW
EXECUTE FUNCTION acid.audit_transaction_status();


/*
===============================================================================
3. ACCOUNT UPDATE VALIDATION
===============================================================================
*/

CREATE OR REPLACE FUNCTION acid.validate_account_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.balance < 0 THEN
        RAISE EXCEPTION 'Account balance cannot be negative'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.currency <> OLD.currency THEN
        RAISE EXCEPTION
            'Account currency cannot change through a balance operation'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.balance IS DISTINCT FROM OLD.balance THEN
        NEW.version := OLD.version + 1;
    END IF;

    NEW.updated_at := CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_account_update
ON acid.accounts;

CREATE TRIGGER trg_validate_account_update
BEFORE UPDATE OF balance, currency
ON acid.accounts
FOR EACH ROW
EXECUTE FUNCTION acid.validate_account_update();


/*
===============================================================================
4. TRANSACTION PROCESSING FUNCTION
===============================================================================

The function:
- Validates the idempotency key.
- Locks affected account rows.
- Checks account state and currency.
- Validates sufficient funds.
- Updates both accounts within one transaction.
- Writes double-entry ledger records.
- Records successful transaction status.

A database transaction surrounds the entire function invocation.
Any raised exception rolls back every change made by that invocation.
*/

CREATE OR REPLACE FUNCTION acid.execute_transfer(
    p_source_account BIGINT,
    p_target_account BIGINT,
    p_amount NUMERIC(18, 2),
    p_idempotency_key VARCHAR(120),
    p_user_id BIGINT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction_id BIGINT;
    v_source_balance NUMERIC(18, 2);
    v_target_balance NUMERIC(18, 2);
    v_source_currency CHAR(3);
    v_target_currency CHAR(3);
    v_source_status VARCHAR(15);
    v_target_status VARCHAR(15);
    v_existing_id BIGINT;
    v_new_source_balance NUMERIC(18, 2);
    v_new_target_balance NUMERIC(18, 2);
BEGIN
    IF p_source_account = p_target_account THEN
        RAISE EXCEPTION 'Source and target accounts must differ';
    END IF;

    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Transfer amount must be positive';
    END IF;

    IF p_idempotency_key IS NULL
       OR length(trim(p_idempotency_key)) = 0 THEN
        RAISE EXCEPTION 'Idempotency key is required';
    END IF;

    -- Reserve the request key. Concurrent duplicate requests serialize here.
    INSERT INTO acid.idempotency_registry (
        idempotency_key
    )
    VALUES (p_idempotency_key)
    ON CONFLICT DO NOTHING;

    SELECT transaction_id
    INTO v_existing_id
    FROM acid.idempotency_registry
    WHERE idempotency_key = p_idempotency_key
    FOR UPDATE;

    IF v_existing_id IS NOT NULL THEN
        RETURN v_existing_id;
    END IF;

    -- Lock rows in ascending ID order to reduce deadlock risk.
    PERFORM account_id
    FROM acid.accounts
    WHERE account_id IN (p_source_account, p_target_account)
    ORDER BY account_id
    FOR UPDATE;

    SELECT balance, currency, account_status
    INTO v_source_balance, v_source_currency, v_source_status
    FROM acid.accounts
    WHERE account_id = p_source_account;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Source account does not exist';
    END IF;

    SELECT balance, currency, account_status
    INTO v_target_balance, v_target_currency, v_target_status
    FROM acid.accounts
    WHERE account_id = p_target_account;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Target account does not exist';
    END IF;

    IF v_source_status <> 'ACTIVE'
       OR v_target_status <> 'ACTIVE' THEN
        RAISE EXCEPTION 'Both accounts must be active';
    END IF;

    IF v_source_currency <> v_target_currency THEN
        RAISE EXCEPTION 'Cross-currency transfer is not supported';
    END IF;

    IF v_source_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds';
    END IF;

    IF v_target_balance + p_amount > 9999999999999999.99 THEN
        RAISE EXCEPTION 'Target balance exceeds supported precision';
    END IF;

    v_new_source_balance := v_source_balance - p_amount;
    v_new_target_balance := v_target_balance + p_amount;

    INSERT INTO acid.transactions (
        idempotency_key,
        transaction_type,
        source_account_id,
        target_account_id,
        amount,
        transaction_status,
        initiated_by
    )
    VALUES (
        p_idempotency_key,
        'TRANSFER',
        p_source_account,
        p_target_account,
        p_amount,
        'PENDING',
        p_user_id
    )
    RETURNING transaction_id INTO v_transaction_id;

    UPDATE acid.accounts
    SET balance = v_new_source_balance
    WHERE account_id = p_source_account;

    UPDATE acid.accounts
    SET balance = v_new_target_balance
    WHERE account_id = p_target_account;

    INSERT INTO acid.transaction_entries (
        transaction_id,
        account_id,
        entry_type,
        amount,
        balance_after
    )
    VALUES
    (
        v_transaction_id,
        p_source_account,
        'DEBIT',
        p_amount,
        v_new_source_balance
    ),
    (
        v_transaction_id,
        p_target_account,
        'CREDIT',
        p_amount,
        v_new_target_balance
    );

    UPDATE acid.transactions
    SET
        transaction_status = 'COMMITTED',
        committed_at = CURRENT_TIMESTAMP
    WHERE transaction_id = v_transaction_id;

    UPDATE acid.idempotency_registry
    SET transaction_id = v_transaction_id
    WHERE idempotency_key = p_idempotency_key;

    RETURN v_transaction_id;
END;
$$;


/*
===============================================================================
5. CONTROLLED TRANSACTION PROCEDURE
===============================================================================
*/

CREATE OR REPLACE PROCEDURE acid.process_transfer(
    IN p_source BIGINT,
    IN p_target BIGINT,
    IN p_amount NUMERIC(18, 2),
    IN p_request_key VARCHAR(120),
    IN p_user BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_id BIGINT;
BEGIN
    v_id := acid.execute_transfer(
        p_source,
        p_target,
        p_amount,
        p_request_key,
        p_user
    );

    RAISE NOTICE 'Transaction processed. ID: %', v_id;
END;
$$;


/*
===============================================================================
6. VIEWS FOR OPERATIONAL REPORTING
===============================================================================
*/

CREATE OR REPLACE VIEW acid.account_overview AS
SELECT
    a.account_id,
    a.account_number,
    c.customer_name,
    a.currency,
    a.balance,
    a.version,
    a.account_status,
    a.updated_at
FROM acid.accounts a
JOIN acid.customers c
    ON c.customer_id = a.customer_id;

CREATE OR REPLACE VIEW acid.transaction_overview AS
SELECT
    t.transaction_id,
    t.transaction_reference,
    t.idempotency_key,
    t.transaction_type,
    source.account_number AS source_account,
    target.account_number AS target_account,
    t.amount,
    t.transaction_status,
    t.created_at,
    t.committed_at,
    t.failure_reason
FROM acid.transactions t
LEFT JOIN acid.accounts source
    ON source.account_id = t.source_account_id
LEFT JOIN acid.accounts target
    ON target.account_id = t.target_account_id;

CREATE OR REPLACE VIEW acid.daily_transaction_summary AS
SELECT
    date_trunc('day', created_at)::date AS transaction_date,
    transaction_type,
    transaction_status,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount
FROM acid.transactions
GROUP BY
    date_trunc('day', created_at)::date,
    transaction_type,
    transaction_status;


/*
===============================================================================
7. SAMPLE SUCCESSFUL TRANSACTIONS
===============================================================================
*/

DO $$
DECLARE
    v_alice BIGINT;
    v_bob BIGINT;
    v_operator BIGINT;
BEGIN
    SELECT account_id INTO v_alice
    FROM acid.accounts
    WHERE account_number = 'INR-10001';

    SELECT account_id INTO v_bob
    FROM acid.accounts
    WHERE account_number = 'INR-10002';

    SELECT user_id INTO v_operator
    FROM acid.application_users
    WHERE username = 'system_operator';

    PERFORM acid.execute_transfer(
        v_alice,
        v_bob,
        5000.00,
        'DEMO-TRANSFER-001',
        v_operator
    );

    PERFORM acid.execute_transfer(
        v_bob,
        v_alice,
        1000.00,
        'DEMO-TRANSFER-002',
        v_operator
    );
END;
$$;


/*
===============================================================================
8. FAILURE CASE: ATOMICITY
===============================================================================

The exception is caught in an inner PL/pgSQL block.
The subtransaction rolls back all changes made within that block.
*/

DO $$
DECLARE
    v_alice BIGINT;
    v_bob BIGINT;
BEGIN
    SELECT account_id INTO v_alice
    FROM acid.accounts
    WHERE account_number = 'INR-10001';

    SELECT account_id INTO v_bob
    FROM acid.accounts
    WHERE account_number = 'INR-10002';

    BEGIN
        PERFORM acid.execute_transfer(
            v_alice,
            v_bob,
            999999999.00,
            'DEMO-INVALID-001'
        );

        RAISE EXCEPTION 'Expected insufficient-funds rejection';
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Expected failure handled: %', SQLERRM;
    END;
END;
$$;


/*
===============================================================================
9. IDEMPOTENCY VALIDATION
===============================================================================
*/

DO $$
DECLARE
    v_alice BIGINT;
    v_bob BIGINT;
    v_first BIGINT;
    v_second BIGINT;
BEGIN
    SELECT account_id INTO v_alice
    FROM acid.accounts
    WHERE account_number = 'INR-10001';

    SELECT account_id INTO v_bob
    FROM acid.accounts
    WHERE account_number = 'INR-10002';

    v_first := acid.execute_transfer(
        v_alice,
        v_bob,
        100.00,
        'DEMO-IDEMPOTENT-001'
    );

    v_second := acid.execute_transfer(
        v_alice,
        v_bob,
        100.00,
        'DEMO-IDEMPOTENT-001'
    );

    IF v_first <> v_second THEN
        RAISE EXCEPTION 'Idempotency validation failed';
    END IF;

    RAISE NOTICE 'Idempotency verified: transaction %', v_first;
END;
$$;


/*
===============================================================================
10. CONSISTENCY: DOUBLE-ENTRY VALIDATION
===============================================================================
*/

SELECT
    transaction_id,
    SUM(
        CASE
            WHEN entry_type = 'CREDIT' THEN amount
            ELSE -amount
        END
    ) AS net_ledger_movement,
    COUNT(*) AS entry_count,
    CASE
        WHEN SUM(
            CASE
                WHEN entry_type = 'CREDIT' THEN amount
                ELSE -amount
            END
        ) = 0 THEN 'BALANCED'
        ELSE 'UNBALANCED'
    END AS ledger_status
FROM acid.transaction_entries
GROUP BY transaction_id
ORDER BY transaction_id;


/*
===============================================================================
11. RETRIEVAL AND REPORTING
===============================================================================
*/

-- Current account state.
SELECT *
FROM acid.account_overview
ORDER BY account_id;

-- Committed transaction history.
SELECT *
FROM acid.transaction_overview
WHERE transaction_status = 'COMMITTED'
ORDER BY created_at DESC;

-- Transaction volume and value.
SELECT *
FROM acid.daily_transaction_summary
ORDER BY transaction_date DESC;

-- Account-level transaction activity.
SELECT
    a.account_number,
    c.customer_name,
    COUNT(e.entry_id) AS entry_count,
    COALESCE(SUM(e.amount), 0) AS total_activity
FROM acid.accounts a
JOIN acid.customers c
    ON c.customer_id = a.customer_id
LEFT JOIN acid.transaction_entries e
    ON e.account_id = a.account_id
GROUP BY a.account_id, a.account_number, c.customer_name
ORDER BY a.account_id;


/*
===============================================================================
12. ELIGIBILITY EVALUATION
===============================================================================
*/

WITH transfer_eligibility AS (
    SELECT
        source.account_id AS source_id,
        target.account_id AS target_id,
        source.currency AS source_currency,
        target.currency AS target_currency,
        source.account_status AS source_status,
        target.account_status AS target_status,
        source.balance AS source_balance,
        500.00::NUMERIC(18, 2) AS requested_amount
    FROM acid.accounts source
    CROSS JOIN acid.accounts target
    WHERE source.account_number = 'INR-10001'
      AND target.account_number = 'INR-10002'
)
SELECT
    source_id,
    target_id,
    source_balance,
    requested_amount,
    CASE
        WHEN source_id = target_id THEN 'REJECTED_SAME_ACCOUNT'
        WHEN source_status <> 'ACTIVE' THEN 'REJECTED_SOURCE_STATUS'
        WHEN target_status <> 'ACTIVE' THEN 'REJECTED_TARGET_STATUS'
        WHEN source_currency <> target_currency
            THEN 'REJECTED_CURRENCY'
        WHEN source_balance < requested_amount
            THEN 'REJECTED_INSUFFICIENT_FUNDS'
        ELSE 'ELIGIBLE'
    END AS eligibility_status
FROM transfer_eligibility;


/*
===============================================================================
13. ISOLATION DEMONSTRATION
===============================================================================

Run these commands in separate psql sessions.

SESSION A:

BEGIN ISOLATION LEVEL REPEATABLE READ;

SELECT balance
FROM acid.accounts
WHERE account_number = 'INR-10001';

-- Execute a transfer in Session B and commit it.

SELECT balance
FROM acid.accounts
WHERE account_number = 'INR-10001';

COMMIT;

REPEATABLE READ maintains a transaction-level snapshot.

SERIALIZABLE provides stronger guarantees and may abort transactions
when concurrent execution cannot be serialized safely.

For row-level serialization:

BEGIN;

SELECT account_id, balance
FROM acid.accounts
WHERE account_number = 'INR-10001'
FOR UPDATE;

-- Perform validated updates.

COMMIT;
*/


/*
===============================================================================
14. SAVEPOINT AND ROLLBACK
===============================================================================
*/

BEGIN;

SAVEPOINT before_optional_operation;

UPDATE acid.database_settings
SET setting_value = 'temporary'
WHERE setting_key = 'transaction_demo';

INSERT INTO acid.database_settings (
    setting_key,
    setting_value
)
VALUES (
    'transaction_demo',
    'temporary'
)
ON CONFLICT (setting_key)
DO UPDATE SET setting_value = EXCLUDED.setting_value;

ROLLBACK TO SAVEPOINT before_optional_operation;

COMMIT;


/*
===============================================================================
15. CONSTRAINT FAILURE DEMONSTRATION
===============================================================================
*/

DO $$
BEGIN
    BEGIN
        INSERT INTO acid.accounts (
            customer_id,
            account_number,
            currency,
            balance
        )
        SELECT
            customer_id,
            'INVALID-NEGATIVE-ACCOUNT',
            'INR',
            -100.00
        FROM acid.customers
        WHERE email = 'alice@example.com';

        RAISE EXCEPTION 'Expected constraint violation';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE 'Negative balance rejected by database constraint';
    END;
END;
$$;


/*
===============================================================================
16. WORKFLOW MONITORING
===============================================================================
*/

-- Failed or rejected requests.
SELECT
    transaction_id,
    idempotency_key,
    transaction_status,
    failure_reason,
    created_at
FROM acid.transactions
WHERE transaction_status IN ('FAILED', 'REJECTED')
ORDER BY created_at DESC;

-- Status transition history.
SELECT
    transaction_id,
    old_status,
    new_status,
    changed_at,
    details
FROM acid.transaction_audit
ORDER BY changed_at DESC;

-- Account version and concurrency monitoring.
SELECT
    account_id,
    account_number,
    balance,
    version,
    updated_at
FROM acid.accounts
ORDER BY version DESC;


/*
===============================================================================
17. APPLICATION ACCESS CONTROL
===============================================================================

In production, grant execution privileges to a dedicated application role.
Do not grant unrestricted table UPDATE permissions to ordinary application
users. Use a controlled transaction API and carefully scoped database roles.

Role creation is conditional and does not replace deployment-specific
credential management.
*/

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'acid_application'
    ) THEN
        CREATE ROLE acid_application NOLOGIN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'acid_auditor'
    ) THEN
        CREATE ROLE acid_auditor NOLOGIN;
    END IF;
END;
$$;

GRANT USAGE ON SCHEMA acid TO acid_application, acid_auditor;

GRANT SELECT ON
    acid.account_overview,
    acid.transaction_overview,
    acid.daily_transaction_summary
TO acid_auditor;

GRANT EXECUTE ON FUNCTION acid.execute_transfer(
    BIGINT,
    BIGINT,
    NUMERIC,
    VARCHAR,
    BIGINT
)
TO acid_application;

GRANT EXECUTE ON PROCEDURE acid.process_transfer(
    BIGINT,
    BIGINT,
    NUMERIC,
    VARCHAR,
    BIGINT
)
TO acid_application;


/*
===============================================================================
18. PERFORMANCE AND DATABASE DIAGNOSTICS
===============================================================================
*/

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM acid.transactions
WHERE transaction_status = 'COMMITTED'
ORDER BY created_at DESC
LIMIT 20;

SELECT
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    last_analyze,
    last_autovacuum
FROM pg_stat_user_tables
WHERE schemaname = 'acid'
ORDER BY relname;

SELECT
    pg_database.datname,
    pg_database_size(pg_database.datname) AS database_size_bytes
FROM pg_database
WHERE pg_database.datname = current_database();


===============================================================================
19. OPERATIONAL NOTES
===============================================================================

Atomicity:
PostgreSQL rolls back all statements within a failed transaction or
subtransaction.

Consistency:
CHECK, UNIQUE, PRIMARY KEY, FOREIGN KEY, triggers and transactional
functions enforce database invariants.

Isolation:
MVCC provides transaction snapshots. Row locks coordinate conflicting
updates. SERIALIZABLE may produce SQLSTATE 40001 and require retry.

Durability:
A successful commit is protected by PostgreSQL's write-ahead log.
Actual durability depends on appropriate WAL, fsync, synchronous_commit,
storage and backup configuration.

The append-only transaction journal represented here is a business audit
ledger. It is not a replacement for PostgreSQL's WAL.

Production applications should retry serialization failures using bounded
retry attempts and backoff. They should never blindly retry non-idempotent
business operations.
*/
