/*
================================================================
PARTIAL AND EXPRESSION INDEXES
Conditional indexes and function-based indexing
PostgreSQL executable implementation
================================================================

This script demonstrates:

1. Conventional B-tree indexes.
2. Partial indexes.
3. Expression indexes.
4. Unique partial indexes.
5. Partial expression indexes.
6. Composite conditional indexes.
7. Predicate implication and index eligibility.
8. Index maintenance during DML.
9. Index statistics and reporting.
10. EXPLAIN and EXPLAIN ANALYZE.
11. Transactional integrity.
12. Index governance and workload analysis.

Target: PostgreSQL 14+
================================================================
*/

-- ============================================================
-- 1. SCHEMA
-- ============================================================

DROP SCHEMA IF EXISTS indexing_lab CASCADE;

CREATE SCHEMA indexing_lab;

SET search_path TO indexing_lab, public;

-- ============================================================
-- 2. MASTER TABLES
-- ============================================================

CREATE TABLE customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    email TEXT NOT NULL,

    region TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT customers_email_not_empty
        CHECK (length(trim(email)) > 0),

    CONSTRAINT customers_region_not_empty
        CHECK (length(trim(region)) > 0)
);


CREATE TABLE orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    customer_id BIGINT NOT NULL
        REFERENCES customers(customer_id),

    customer_email TEXT NOT NULL,

    status TEXT NOT NULL,

    amount NUMERIC(12, 2) NOT NULL,

    region TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT orders_status_valid
        CHECK (
            status IN (
                'OPEN',
                'PAID',
                'CANCELLED',
                'ARCHIVED'
            )
        ),

    CONSTRAINT orders_amount_nonnegative
        CHECK (amount >= 0),

    CONSTRAINT orders_email_nonempty
        CHECK (length(trim(customer_email)) > 0)
);


CREATE TABLE user_accounts (
    account_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    email TEXT NOT NULL,

    account_status TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT account_status_valid
        CHECK (
            account_status IN (
                'ACTIVE',
                'INACTIVE',
                'SUSPENDED'
            )
        )
);


-- ============================================================
-- 3. INDEX GOVERNANCE TABLE
-- ============================================================

CREATE TABLE index_catalog (
    index_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    index_name TEXT NOT NULL UNIQUE,

    table_name TEXT NOT NULL,

    index_type TEXT NOT NULL,

    indexed_expression TEXT NOT NULL,

    partial_predicate TEXT,

    is_unique BOOLEAN NOT NULL DEFAULT FALSE,

    purpose TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT index_type_valid
        CHECK (
            index_type IN (
                'FULL',
                'PARTIAL',
                'EXPRESSION',
                'PARTIAL_EXPRESSION',
                'COMPOSITE'
            )
        ),

    CONSTRAINT partial_predicate_required
        CHECK (
            (
                index_type IN ('PARTIAL', 'PARTIAL_EXPRESSION')
                AND partial_predicate IS NOT NULL
            )
            OR
            (
                index_type NOT IN ('PARTIAL', 'PARTIAL_EXPRESSION')
                AND partial_predicate IS NULL
            )
        )
);


CREATE TABLE query_workload (
    workload_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    query_name TEXT NOT NULL,

    indexed_expression TEXT NOT NULL,

    query_predicate TEXT,

    execution_count BIGINT NOT NULL DEFAULT 0,

    average_execution_ms NUMERIC(12, 4),

    last_executed_at TIMESTAMPTZ,

    CONSTRAINT workload_execution_nonnegative
        CHECK (execution_count >= 0),

    CONSTRAINT workload_latency_nonnegative
        CHECK (
            average_execution_ms IS NULL
            OR average_execution_ms >= 0
        )
);


-- ============================================================
-- 4. SAMPLE CUSTOMERS
-- ============================================================

INSERT INTO customers (email, region)
VALUES
    ('alice@example.com', 'NORTH'),
    ('bob@example.com', 'SOUTH'),
    ('carol@example.com', 'NORTH'),
    ('david@example.com', 'WEST'),
    ('eve@example.com', 'EAST'),
    ('frank@example.com', 'SOUTH'),
    ('grace@example.com', 'NORTH'),
    ('henry@example.com', 'WEST');


-- ============================================================
-- 5. SAMPLE ORDERS
-- ============================================================

INSERT INTO orders (
    customer_id,
    customer_email,
    status,
    amount,
    region
)
SELECT
    customer_id,
    email,
    CASE customer_id
        WHEN 1 THEN 'OPEN'
        WHEN 2 THEN 'PAID'
        WHEN 3 THEN 'OPEN'
        WHEN 4 THEN 'CANCELLED'
        WHEN 5 THEN 'ARCHIVED'
        WHEN 6 THEN 'OPEN'
        WHEN 7 THEN 'PAID'
        WHEN 8 THEN 'OPEN'
    END,
    CASE customer_id
        WHEN 1 THEN 450.00
        WHEN 2 THEN 900.00
        WHEN 3 THEN 250.00
        WHEN 4 THEN 120.00
        WHEN 5 THEN 300.00
        WHEN 6 THEN 780.00
        WHEN 7 THEN 150.00
        WHEN 8 THEN 1100.00
    END,
    region
FROM customers
WHERE customer_id <= 8;


-- ============================================================
-- 6. SAMPLE USER ACCOUNTS
-- ============================================================

INSERT INTO user_accounts (email, account_status)
VALUES
    ('admin@example.com', 'ACTIVE'),
    ('old@example.com', 'INACTIVE'),
    ('support@example.com', 'ACTIVE'),
    ('suspended@example.com', 'SUSPENDED');


-- ============================================================
-- 7. CONVENTIONAL INDEX
-- ============================================================

/*
A conventional index contains entries for all applicable
table rows, subject to PostgreSQL's NULL handling.
*/

CREATE INDEX idx_orders_status
ON orders (status);


-- ============================================================
-- 8. PARTIAL INDEX
-- ============================================================

/*
Only OPEN orders are included.

This index is useful for queries whose conditions imply
status = 'OPEN'.

Rows with PAID, CANCELLED, and ARCHIVED statuses do not
contribute entries.
*/

CREATE INDEX idx_orders_open
ON orders (order_id)
WHERE status = 'OPEN';


-- ============================================================
-- 9. EXPRESSION INDEX
-- ============================================================

/*
The indexed key is the result of lower(customer_email).

The query must use a compatible expression.
*/

CREATE INDEX idx_orders_lower_email
ON orders (lower(customer_email));


/*
Another expression index using upper(region).
*/

CREATE INDEX idx_orders_upper_region
ON orders (upper(region));


-- ============================================================
-- 10. PARTIAL EXPRESSION INDEX
-- ============================================================

/*
This index combines:

1. Expression-based indexing on lower(customer_email).
2. Conditional inclusion of OPEN orders.

Only OPEN orders have entries.
*/

CREATE INDEX idx_open_orders_lower_email
ON orders (lower(customer_email))
WHERE status = 'OPEN';


/*
A partial index on high-value open orders.

The index stores only order_id values for records
satisfying both conditions.
*/

CREATE INDEX idx_open_high_value
ON orders (order_id)
WHERE status = 'OPEN'
  AND amount > 300;


-- ============================================================
-- 11. COMPOSITE PARTIAL INDEX
-- ============================================================

/*
Useful when queries filter by region and sort or retrieve
records using created_at.

The predicate limits entries to OPEN orders.
*/

CREATE INDEX idx_open_region_created
ON orders (region, created_at DESC)
WHERE status = 'OPEN';


-- ============================================================
-- 12. UNIQUE PARTIAL INDEX
-- ============================================================

/*
Multiple historical inactive accounts may share an email.

Only one ACTIVE account can own a given case-insensitive email.
*/

CREATE UNIQUE INDEX idx_unique_active_email
ON user_accounts (lower(email))
WHERE account_status = 'ACTIVE';


-- ============================================================
-- 13. REGISTER INDEX DEFINITIONS
-- ============================================================

INSERT INTO index_catalog (
    index_name,
    table_name,
    index_type,
    indexed_expression,
    partial_predicate,
    is_unique,
    purpose
)
VALUES
(
    'idx_orders_status',
    'orders',
    'FULL',
    'status',
    NULL,
    FALSE,
    'General order status filtering'
),
(
    'idx_orders_open',
    'orders',
    'PARTIAL',
    'order_id',
    'status = OPEN',
    FALSE,
    'Frequent retrieval of open orders'
),
(
    'idx_orders_lower_email',
    'orders',
    'EXPRESSION',
    'lower(customer_email)',
    NULL,
    FALSE,
    'Case-insensitive email lookup'
),
(
    'idx_orders_upper_region',
    'orders',
    'EXPRESSION',
    'upper(region)',
    NULL,
    FALSE,
    'Case-insensitive region lookup'
),
(
    'idx_open_orders_lower_email',
    'orders',
    'PARTIAL_EXPRESSION',
    'lower(customer_email)',
    'status = OPEN',
    FALSE,
    'Case-insensitive lookup of open orders'
),
(
    'idx_open_high_value',
    'orders',
    'PARTIAL',
    'order_id',
    'status = OPEN AND amount > 300',
    FALSE,
    'High-value open-order retrieval'
),
(
    'idx_open_region_created',
    'orders',
    'COMPOSITE',
    'region, created_at DESC',
    NULL,
    FALSE,
    'Open-order regional retrieval'
),
(
    'idx_unique_active_email',
    'user_accounts',
    'PARTIAL_EXPRESSION',
    'lower(email)',
    'account_status = ACTIVE',
    TRUE,
    'Case-insensitive active-account uniqueness'
);


-- ============================================================
-- 14. QUERY RETRIEVAL
-- ============================================================

-- A. Partial index query.

SELECT
    order_id,
    customer_email,
    amount
FROM orders
WHERE status = 'OPEN'
ORDER BY order_id;


-- B. Expression index query.

SELECT
    order_id,
    customer_email
FROM orders
WHERE lower(customer_email) = 'alice@example.com';


-- C. Partial expression index query.

SELECT
    order_id,
    customer_email
FROM orders
WHERE status = 'OPEN'
  AND lower(customer_email) = 'alice@example.com';


-- D. Composite partial index query.

SELECT
    order_id,
    region,
    created_at
FROM orders
WHERE status = 'OPEN'
  AND region = 'NORTH'
ORDER BY created_at DESC;


-- E. High-value partial index query.

SELECT
    order_id,
    amount
FROM orders
WHERE status = 'OPEN'
  AND amount > 300;


-- ============================================================
-- 15. PREDICATE IMPLICATION
-- ============================================================

/*
PostgreSQL can use a partial index when it can establish
that the query predicate implies the index predicate.

For example:

Index:
    WHERE status = 'OPEN'

Eligible query:
    WHERE status = 'OPEN' AND amount > 500

The query condition is more restrictive.

Ineligible query:
    WHERE status = 'PAID'

The query does not imply the index predicate.

Predicate matching is based on planner-recognizable
conditions, not arbitrary theorem proving.
*/


-- Eligible query.

EXPLAIN
SELECT order_id
FROM orders
WHERE status = 'OPEN'
  AND amount > 500;


-- Ineligible for idx_orders_open.

EXPLAIN
SELECT order_id
FROM orders
WHERE status = 'PAID';


-- ============================================================
-- 16. EXPRESSION MATCHING
-- ============================================================

/*
The expression in the query must be compatible with
the indexed expression.

This query can use idx_orders_lower_email.
*/

EXPLAIN
SELECT order_id
FROM orders
WHERE lower(customer_email) = 'alice@example.com';


/*
A direct comparison does not request the same normalized
expression. The expression index is not a substitute for
every possible comparison on customer_email.
*/

EXPLAIN
SELECT order_id
FROM orders
WHERE customer_email = 'alice@example.com';


-- ============================================================
-- 17. FUNCTION-BASED INDEXING
-- ============================================================

/*
Function-based indexing stores the result of a function
or expression rather than only the original column.

PostgreSQL requires functions used in index expressions
to be IMMUTABLE.

lower(text) is suitable for this expression index.
*/


-- Case-insensitive customer search.

SELECT
    order_id,
    customer_email
FROM orders
WHERE lower(customer_email) = lower('ALICE@EXAMPLE.COM');


-- Uppercase region search.

SELECT
    order_id,
    region
FROM orders
WHERE upper(region) = 'NORTH';


-- ============================================================
-- 18. PARTIAL INDEX ELIGIBILITY FUNCTION
-- ============================================================

/*
This function provides a simple metadata-level eligibility
demonstration. It does not replace PostgreSQL's actual
query planner.
*/

CREATE OR REPLACE FUNCTION is_partial_index_eligible(
    p_query_status TEXT,
    p_index_status TEXT
)
RETURNS BOOLEAN
LANGUAGE SQL
IMMUTABLE
AS $$
    SELECT
        p_index_status IS NULL
        OR p_query_status = p_index_status;
$$;


SELECT
    is_partial_index_eligible('OPEN', 'OPEN')
        AS matching_predicate,

    is_partial_index_eligible('PAID', 'OPEN')
        AS nonmatching_predicate,

    is_partial_index_eligible('OPEN', NULL)
        AS unrestricted_index;


-- ============================================================
-- 19. VALIDATION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_order_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.amount < 0 THEN
        RAISE EXCEPTION
            'Order amount cannot be negative';
    END IF;

    IF NEW.status NOT IN (
        'OPEN',
        'PAID',
        'CANCELLED',
        'ARCHIVED'
    ) THEN
        RAISE EXCEPTION
            'Invalid order status: %',
            NEW.status;
    END IF;

    NEW.updated_at := CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$;


CREATE TRIGGER trg_validate_order_insert
BEFORE INSERT OR UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION validate_order_insert();


-- ============================================================
-- 20. INDEX MAINTENANCE DEMONSTRATION
-- ============================================================

/*
PostgreSQL automatically maintains indexes when indexed
columns, expression inputs, or partial-index predicates
change.

Changing OPEN to PAID removes the row from an OPEN-only
partial index.

Changing PAID to OPEN inserts the row into that index.
*/

BEGIN;

UPDATE orders
SET status = 'PAID'
WHERE order_id = 1;

SELECT
    order_id,
    status
FROM orders
WHERE order_id = 1;

COMMIT;


-- ============================================================
-- 21. TRANSACTIONAL VALIDATION
-- ============================================================

/*
A failed insert must not leave a partially inserted row.
*/

BEGIN;

DO $$
BEGIN
    BEGIN
        INSERT INTO orders (
            customer_id,
            customer_email,
            status,
            amount,
            region
        )
        VALUES (
            1,
            'invalid@example.com',
            'OPEN',
            -100,
            'NORTH'
        );

        RAISE EXCEPTION
            'Negative amount validation unexpectedly failed';

    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE
                'Expected validation failure captured';
        WHEN OTHERS THEN
            RAISE;
    END;
END;
$$;

ROLLBACK;


-- ============================================================
-- 22. UNIQUE PARTIAL INDEX VALIDATION
-- ============================================================

/*
An ACTIVE duplicate email is rejected.

An INACTIVE duplicate email is permitted.
*/

BEGIN;

DO $$
BEGIN
    BEGIN
        INSERT INTO user_accounts (
            email,
            account_status
        )
        VALUES (
            'ADMIN@example.com',
            'ACTIVE'
        );

        RAISE EXCEPTION
            'Expected unique violation did not occur';

    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE
                'Active duplicate email correctly rejected';
    END;
END;
$$;

COMMIT;


-- Inactive duplicate is allowed.

INSERT INTO user_accounts (
    email,
    account_status
)
VALUES (
    'ADMIN@example.com',
    'INACTIVE'
);


-- ============================================================
-- 23. QUERY WORKLOAD
-- ============================================================

INSERT INTO query_workload (
    query_name,
    indexed_expression,
    query_predicate,
    execution_count,
    average_execution_ms,
    last_executed_at
)
VALUES
(
    'case_insensitive_email_lookup',
    'lower(customer_email)',
    NULL,
    12000,
    1.25,
    CURRENT_TIMESTAMP
),
(
    'open_order_retrieval',
    'order_id',
    'status = OPEN',
    8500,
    0.95,
    CURRENT_TIMESTAMP
),
(
    'high_value_open_orders',
    'order_id',
    'status = OPEN AND amount > 300',
    3200,
    0.72,
    CURRENT_TIMESTAMP
),
(
    'regional_open_order_report',
    'region, created_at DESC',
    'status = OPEN',
    1600,
    2.10,
    CURRENT_TIMESTAMP
);


-- ============================================================
-- 24. INDEX GOVERNANCE REPORT
-- ============================================================

SELECT
    index_name,
    table_name,
    index_type,
    indexed_expression,
    partial_predicate,
    is_unique,
    purpose
FROM index_catalog
ORDER BY index_type, index_name;


-- ============================================================
-- 25. WORKLOAD ANALYSIS
-- ============================================================

SELECT
    query_name,
    indexed_expression,
    query_predicate,
    execution_count,
    average_execution_ms,
    ROUND(
        execution_count * average_execution_ms,
        2
    ) AS estimated_cumulative_ms
FROM query_workload
ORDER BY
    estimated_cumulative_ms DESC;


-- ============================================================
-- 26. INDEX SIZE AND USAGE STATISTICS
-- ============================================================

/*
pg_stat_user_indexes reports PostgreSQL's actual index usage.

A low idx_scan value does not automatically mean that
an index should be removed. Consider workload frequency,
maintenance costs, table size, and reporting periods.
*/

SELECT
    indexrelname AS index_name,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(
        pg_relation_size(indexrelid)
    ) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'indexing_lab'
ORDER BY idx_scan DESC;


-- ============================================================
-- 27. TABLE STATISTICS
-- ============================================================

SELECT
    schemaname,
    relname AS table_name,
    n_live_tup,
    n_dead_tup,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'indexing_lab';


-- ============================================================
-- 28. ACTUAL QUERY PLAN
-- ============================================================

/*
ANALYZE and BUFFERS provide execution information.
Small sample tables may produce sequential scans because
the planner estimates them to be cheaper.

A sequential scan does not indicate an invalid index.
*/

ANALYZE orders;

ANALYZE user_accounts;

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT
    order_id,
    customer_email
FROM orders
WHERE status = 'OPEN'
  AND lower(customer_email) = 'frank@example.com';


EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    amount
FROM orders
WHERE status = 'OPEN'
  AND amount > 300;


-- ============================================================
-- 29. INDEX ELIGIBILITY REPORT
-- ============================================================

SELECT
    i.index_name,
    i.index_type,
    i.indexed_expression,
    i.partial_predicate,
    CASE
        WHEN i.partial_predicate IS NULL
            THEN 'UNCONDITIONAL INDEX'

        WHEN i.partial_predicate = 'status = OPEN'
            THEN 'OPEN ORDER QUERIES'

        WHEN i.partial_predicate =
             'status = OPEN AND amount > 300'
            THEN 'HIGH-VALUE OPEN ORDER QUERIES'

        ELSE 'SPECIALIZED QUERY'
    END AS intended_eligibility
FROM index_catalog AS i
WHERE i.table_name = 'orders'
ORDER BY i.index_name;


-- ============================================================
-- 30. INDEX MAINTENANCE AND STORAGE TRADE-OFFS
-- ============================================================

/*
Partial indexes:
- Store fewer entries when predicates are selective.
- Reduce storage compared with equivalent full indexes.
- Reduce maintenance for rows outside the predicate.
- Require compatible query predicates.

Expression indexes:
- Avoid recalculating indexed expressions during qualifying
  indexed lookups.
- Require compatible query expressions.
- Increase maintenance when source columns change.
- Require immutable indexed functions.

Unique partial indexes:
- Enforce uniqueness only within the indexed subset.
- Support conditional uniqueness rules.

Composite partial indexes:
- Combine key ordering with row filtering.
- Must match actual query patterns.

Every additional index consumes storage and adds write cost.
*/


-- ============================================================
-- 31. PRODUCTION INDEX MAINTENANCE
-- ============================================================

/*
REINDEX can rebuild an existing index:

REINDEX INDEX indexing_lab.idx_orders_open;

For a large production database, concurrent index creation
can reduce write blocking:

CREATE INDEX CONCURRENTLY idx_orders_region
ON indexing_lab.orders (region);

CREATE INDEX CONCURRENTLY cannot execute inside a
transaction block.

Similarly, CREATE INDEX CONCURRENTLY and
DROP INDEX CONCURRENTLY have special transaction restrictions.

The demonstration indexes above are created normally
to keep this script transactionally executable.
*/


-- ============================================================
-- 32. FINAL VALIDATION REPORT
-- ============================================================

SELECT
    'CUSTOMERS' AS entity,
    COUNT(*) AS record_count
FROM customers

UNION ALL

SELECT
    'ORDERS',
    COUNT(*)
FROM orders

UNION ALL

SELECT
    'USER ACCOUNTS',
    COUNT(*)
FROM user_accounts

UNION ALL

SELECT
    'INDEX DEFINITIONS',
    COUNT(*)
FROM index_catalog

UNION ALL

SELECT
    'WORKLOAD RECORDS',
    COUNT(*)
FROM query_workload;


SELECT
    status,
    COUNT(*) AS order_count,
    SUM(amount) AS total_amount
FROM orders
GROUP BY status
ORDER BY status;


SELECT
    account_status,
    COUNT(*) AS account_count
FROM user_accounts
GROUP BY account_status
ORDER BY account_status;


-- ============================================================
-- END OF PARTIAL AND EXPRESSION INDEX IMPLEMENTATION
-- ============================================================
