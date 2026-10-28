DROP SCHEMA IF EXISTS window_frames_demo CASCADE;
CREATE SCHEMA window_frames_demo;
SET search_path TO window_frames_demo;

-- The model keeps the ORDER BY key separate from the physical row identity.
-- This is important because ROWS, RANGE, and GROUPS interpret boundaries
-- differently even when they use the same ordered result set.

CREATE TABLE employees (
    employee_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_name text NOT NULL UNIQUE,
    department text NOT NULL
);

CREATE TABLE sales (
    sale_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id bigint NOT NULL REFERENCES employees(employee_id),
    sale_date date NOT NULL,
    amount numeric(12,2) NOT NULL CHECK (amount >= 0),
    status text NOT NULL CHECK (
        status IN ('posted', 'cancelled')
    )
);

CREATE INDEX idx_sales_employee_date
    ON sales (employee_id, sale_date, sale_id);

CREATE INDEX idx_sales_employee_amount
    ON sales (employee_id, amount, sale_id);

INSERT INTO employees (employee_name, department)
VALUES
    ('Asha', 'Engineering'),
    ('Ravi', 'Engineering'),
    ('Meera', 'Operations');

INSERT INTO sales (employee_id, sale_date, amount, status)
SELECT employee_id, sale_date, amount, status
FROM (
    VALUES
        ('Asha',   DATE '2026-10-01', 100.00::numeric, 'posted'),
        ('Asha',   DATE '2026-10-02', 200.00::numeric, 'posted'),
        ('Asha',   DATE '2026-10-02', 300.00::numeric, 'posted'),
        ('Asha',   DATE '2026-10-04', 400.00::numeric, 'posted'),
        ('Asha',   DATE '2026-10-07', 500.00::numeric, 'posted'),
        ('Ravi',   DATE '2026-10-01', 120.00::numeric, 'posted'),
        ('Ravi',   DATE '2026-10-01', 180.00::numeric, 'posted'),
        ('Ravi',   DATE '2026-10-03', 250.00::numeric, 'posted'),
        ('Meera',  DATE '2026-10-02', 90.00::numeric, 'posted'),
        ('Meera',  DATE '2026-10-05', 160.00::numeric, 'cancelled')
) AS x(employee_name, sale_date, amount, status)
JOIN employees e
  ON e.employee_name = x.employee_name;

-- ROWS counts physical rows in the window.
SELECT
    employee_name,
    sale_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date, sale_id
        ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
    ) AS rows_two_row_total
FROM sales s
JOIN employees e USING (employee_id)
WHERE status = 'posted'
ORDER BY employee_name, sale_date, sale_id;

-- RANGE uses the ORDER BY value. With dates, INTERVAL defines the value
-- distance rather than the number of records.
SELECT
    employee_name,
    sale_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date
        RANGE BETWEEN INTERVAL '2 days' PRECEDING AND CURRENT ROW
    ) AS range_2_day_total
FROM sales s
JOIN employees e USING (employee_id)
WHERE status = 'posted'
ORDER BY employee_name, sale_date, sale_id;

-- GROUPS counts peer groups. Rows with the same ORDER BY date are one
-- peer group, so both 2026-10-02 rows participate together.
SELECT
    employee_name,
    sale_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date
        GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW
    ) AS groups_previous_date_total
FROM sales s
JOIN employees e USING (employee_id)
WHERE status = 'posted'
ORDER BY employee_name, sale_date, sale_id;

-- The three frame types can produce different results from the same data.
WITH base AS (
    SELECT
        s.*,
        e.employee_name,
        ROW_NUMBER() OVER (
            PARTITION BY s.employee_id
            ORDER BY s.sale_date, s.sale_id
        ) AS physical_position
    FROM sales s
    JOIN employees e USING (employee_id)
    WHERE s.status = 'posted'
)
SELECT
    employee_name,
    sale_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date, sale_id
        ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
    ) AS rows_total,
    SUM(amount) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date
        RANGE BETWEEN INTERVAL '1 day' PRECEDING AND CURRENT ROW
    ) AS range_total,
    SUM(amount) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date
        GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW
    ) AS groups_total
FROM base
ORDER BY employee_name, physical_position;

-- FIRST_VALUE and LAST_VALUE show why explicit frame boundaries matter.
-- LAST_VALUE with the default frame usually means the last row of the
-- current peer group, not the last row of the complete partition.
SELECT
    employee_name,
    sale_date,
    amount,
    LAST_VALUE(amount) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date, sale_id
    ) AS default_last_value,
    LAST_VALUE(amount) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date, sale_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS partition_last_value
FROM sales s
JOIN employees e USING (employee_id)
WHERE status = 'posted'
ORDER BY employee_name, sale_date, sale_id;

-- Explicit validation query: compare ROWS and GROUPS where duplicate
-- ORDER BY values exist. A difference is expected for peer groups.
SELECT
    employee_name,
    sale_date,
    COUNT(*) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date
        ROWS BETWEEN CURRENT ROW AND CURRENT ROW
    ) AS rows_current_count,
    COUNT(*) OVER (
        PARTITION BY employee_id
        ORDER BY sale_date
        GROUPS BETWEEN CURRENT ROW AND CURRENT ROW
    ) AS groups_current_peer_count
FROM sales s
JOIN employees e USING (employee_id)
WHERE status = 'posted'
ORDER BY employee_name, sale_date, sale_id;

-- Transactional example: a cancellation changes the reporting population
-- while preserving referential and check-constraint integrity.
BEGIN;

UPDATE sales
SET status = 'cancelled'
WHERE sale_id = (
    SELECT sale_id
    FROM sales
    WHERE amount = 300.00
    ORDER BY sale_id
    LIMIT 1
);

SELECT
    employee_name,
    SUM(amount) FILTER (WHERE status = 'posted') AS posted_amount,
    SUM(amount) FILTER (WHERE status = 'cancelled') AS cancelled_amount
FROM sales s
JOIN employees e USING (employee_id)
GROUP BY employee_name
ORDER BY employee_name;

ROLLBACK;

-- Reporting view with an explicit running frame.
CREATE OR REPLACE VIEW employee_window_report AS
SELECT
    s.sale_id,
    e.employee_name,
    e.department,
    s.sale_date,
    s.amount,
    SUM(s.amount) OVER (
        PARTITION BY s.employee_id
        ORDER BY s.sale_date, s.sale_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_rows_total,
    SUM(s.amount) OVER (
        PARTITION BY s.employee_id
        ORDER BY s.sale_date
        RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW
    ) AS seven_day_range_total,
    SUM(s.amount) OVER (
        PARTITION BY s.employee_id
        ORDER BY s.sale_date
        GROUPS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS three_date_group_total
FROM sales s
JOIN employees e USING (employee_id)
WHERE s.status = 'posted';

SELECT *
FROM employee_window_report
ORDER BY employee_name, sale_date, sale_id;
