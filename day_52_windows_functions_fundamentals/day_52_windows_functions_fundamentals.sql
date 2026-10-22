DROP SCHEMA IF EXISTS window_functions_demo CASCADE;
CREATE SCHEMA window_functions_demo;
SET search_path TO window_functions_demo;

-- A sale is the base row. Window functions enrich these rows without
-- collapsing them into one row per department.
CREATE TABLE departments (
    department_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name text NOT NULL UNIQUE
);

CREATE TABLE employees (
    employee_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_name text NOT NULL,
    department_id integer NOT NULL REFERENCES departments(department_id),
    active boolean NOT NULL DEFAULT true,
    UNIQUE (employee_name, department_id)
);

CREATE TABLE sales (
    sale_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id integer NOT NULL REFERENCES employees(employee_id),
    sale_date date NOT NULL,
    amount numeric(12, 2) NOT NULL CHECK (amount >= 0),
    UNIQUE (employee_id, sale_date, amount)
);

CREATE INDEX idx_sales_employee_date
    ON sales (employee_id, sale_date, sale_id);

CREATE INDEX idx_sales_date
    ON sales (sale_date);

INSERT INTO departments (department_name)
VALUES
    ('Technology'),
    ('Finance'),
    ('Operations');

INSERT INTO employees (employee_name, department_id)
SELECT v.employee_name, d.department_id
FROM (
    VALUES
        ('Asha', 'Technology'),
        ('Ravi', 'Technology'),
        ('Neha', 'Finance'),
        ('Vikram', 'Finance'),
        ('Meera', 'Operations')
) AS v(employee_name, department_name)
JOIN departments d
  ON d.department_name = v.department_name;

INSERT INTO sales (employee_id, sale_date, amount)
SELECT e.employee_id, v.sale_date, v.amount
FROM (
    VALUES
        ('Asha',   '2026-01-05'::date, 12000.00::numeric),
        ('Ravi',   '2026-01-12'::date, 18000.00::numeric),
        ('Asha',   '2026-02-03'::date, 15000.00::numeric),
        ('Ravi',   '2026-02-17'::date, 22000.00::numeric),
        ('Neha',   '2026-01-08'::date,  9000.00::numeric),
        ('Vikram', '2026-01-22'::date, 14000.00::numeric),
        ('Neha',   '2026-02-06'::date, 11000.00::numeric),
        ('Vikram', '2026-02-20'::date, 17000.00::numeric),
        ('Meera',  '2026-01-10'::date,  7000.00::numeric),
        ('Meera',  '2026-02-14'::date, 13000.00::numeric)
) AS v(employee_name, sale_date, amount)
JOIN employees e
  ON e.employee_name = v.employee_name;

-- The base relation contains one row per sale.
-- Window functions calculate values across related rows while retaining
-- every original sale.
CREATE VIEW sale_window_analysis AS
SELECT
    s.sale_id,
    e.employee_name,
    d.department_name,
    s.sale_date,
    s.amount,

    ROW_NUMBER() OVER (
        PARTITION BY d.department_id
        ORDER BY s.sale_date, s.sale_id
    ) AS row_number_in_department,

    RANK() OVER (
        PARTITION BY d.department_id
        ORDER BY s.amount DESC
    ) AS amount_rank,

    DENSE_RANK() OVER (
        PARTITION BY d.department_id
        ORDER BY s.amount DESC
    ) AS dense_amount_rank,

    SUM(s.amount) OVER (
        PARTITION BY d.department_id
        ORDER BY s.sale_date, s.sale_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_department_total,

    AVG(s.amount) OVER (
        PARTITION BY d.department_id
        ORDER BY s.sale_date, s.sale_id
        ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
    ) AS two_row_moving_average,

    LAG(s.amount) OVER (
        PARTITION BY d.department_id
        ORDER BY s.sale_date, s.sale_id
    ) AS previous_sale_amount,

    LEAD(s.amount) OVER (
        PARTITION BY d.department_id
        ORDER BY s.sale_date, s.sale_id
    ) AS next_sale_amount,

    FIRST_VALUE(s.amount) OVER (
        PARTITION BY d.department_id
        ORDER BY s.sale_date, s.sale_id
    ) AS first_department_sale,

    LAST_VALUE(s.amount) OVER (
        PARTITION BY d.department_id
        ORDER BY s.sale_date, s.sale_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS last_department_sale

FROM sales s
JOIN employees e
  ON e.employee_id = s.employee_id
JOIN departments d
  ON d.department_id = e.department_id;

-- Complete window report.
SELECT *
FROM sale_window_analysis
ORDER BY department_name, sale_date, sale_id;

-- Demonstrate that window functions preserve the detail rows while
-- ordinary GROUP BY collapses them.
SELECT
    department_name,
    COUNT(*) AS sale_count,
    SUM(amount) AS department_total,
    AVG(amount) AS department_average
FROM sale_window_analysis
GROUP BY department_name
ORDER BY department_name;

-- Compare each sale with its department average.
WITH evaluated AS (
    SELECT
        *,
        AVG(amount) OVER (
            PARTITION BY department_name
        ) AS department_average
    FROM sale_window_analysis
)
SELECT
    sale_id,
    department_name,
    employee_name,
    amount,
    department_average,
    ROUND(amount - department_average, 2) AS difference_from_average
FROM evaluated
ORDER BY department_name, sale_date, sale_id;

-- Select the top two sales in every department.
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY department_name
            ORDER BY amount DESC, sale_id
        ) AS position
    FROM sale_window_analysis
)
SELECT
    sale_id,
    department_name,
    employee_name,
    amount,
    position
FROM ranked
WHERE position <= 2
ORDER BY department_name, position;

-- Use a window result inside a CTE for a second analytical decision.
WITH ranked AS (
    SELECT
        *,
        RANK() OVER (
            PARTITION BY department_name
            ORDER BY amount DESC
        ) AS rank_in_department
    FROM sales s
    JOIN employees e ON e.employee_id = s.employee_id
    JOIN departments d ON d.department_id = e.department_id
)
SELECT
    department_name,
    employee_name,
    amount,
    rank_in_department
FROM ranked
WHERE rank_in_department = 1
ORDER BY department_name;

-- Transactional integrity example. The CHECK constraint rejects negative
-- amounts before the transaction can commit.
BEGIN;

INSERT INTO sales (employee_id, sale_date, amount)
SELECT employee_id, DATE '2026-03-01', 19500.00
FROM employees
WHERE employee_name = 'Asha'
  AND department_id = (
      SELECT department_id
      FROM departments
      WHERE department_name = 'Technology'
  );

-- Re-querying the window view inside the transaction includes the new row.
SELECT
    sale_id,
    department_name,
    employee_name,
    sale_date,
    amount,
    running_department_total
FROM sale_window_analysis
WHERE department_name = 'Technology'
ORDER BY sale_date, sale_id;

COMMIT;

-- PostgreSQL-specific frame behavior:
-- ROWS uses physical ordered rows, so an explicit frame is preferable
-- when the intended calculation is "previous N rows".
SELECT
    sale_id,
    department_name,
    sale_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY department_name
        ORDER BY sale_date, sale_id
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS three_row_sum
FROM sale_window_analysis
ORDER BY department_name, sale_date, sale_id;

-- Identify sales above their department's average without losing detail.
SELECT
    sale_id,
    department_name,
    employee_name,
    amount
FROM (
    SELECT
        *,
        AVG(amount) OVER (
            PARTITION BY department_name
        ) AS department_average
    FROM sale_window_analysis
) x
WHERE amount > department_average
ORDER BY department_name, amount DESC;

-- Query-plan inspection can be used in production to verify whether
-- partition/order operations benefit from the available indexes.
EXPLAIN (COSTS OFF)
SELECT
    department_name,
    sale_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY department_name
        ORDER BY sale_date, sale_id
    ) AS running_total
FROM sale_window_analysis;
