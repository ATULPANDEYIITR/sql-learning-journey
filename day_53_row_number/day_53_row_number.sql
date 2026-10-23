DROP SCHEMA IF EXISTS ranking_lab CASCADE;
CREATE SCHEMA ranking_lab;
SET search_path TO ranking_lab;

-- The relational model separates source rows from analytical results.
CREATE TABLE customers (
    customer_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name text NOT NULL,
    region text NOT NULL,
    CONSTRAINT customers_name_not_blank CHECK (btrim(customer_name) <> '')
);

CREATE TABLE products (
    product_id text PRIMARY KEY,
    category text NOT NULL,
    product_name text NOT NULL,
    CONSTRAINT products_category_not_blank CHECK (btrim(category) <> ''),
    CONSTRAINT products_name_not_blank CHECK (btrim(product_name) <> '')
);

CREATE TABLE sales (
    sale_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id integer NOT NULL REFERENCES customers(customer_id),
    product_id text NOT NULL REFERENCES products(product_id),
    sale_amount numeric(12,2) NOT NULL,
    sold_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT sales_amount_nonnegative CHECK (sale_amount >= 0)
);

CREATE INDEX idx_sales_customer_amount
    ON sales (customer_id, sale_amount DESC, sale_id);

CREATE INDEX idx_sales_category_amount
    ON products (category, product_id);

INSERT INTO customers (customer_name, region) VALUES
    ('Aarav Industries', 'North'),
    ('Bharat Retail', 'West'),
    ('Cedar Systems', 'South'),
    ('Delta Services', 'East'),
    ('Evergreen Labs', 'North'),
    ('Fusion Works', 'West'),
    ('Granite Foods', 'South'),
    ('Horizon Media', 'East'),
    ('Indigo Logistics', 'North');

INSERT INTO products (product_id, category, product_name) VALUES
    ('LAPTOP', 'Electronics', 'Business Laptop'),
    ('PHONE', 'Electronics', 'Enterprise Phone'),
    ('MONITOR', 'Electronics', 'Professional Monitor'),
    ('CHAIR', 'Furniture', 'Ergonomic Chair'),
    ('TABLE', 'Furniture', 'Work Table'),
    ('DESK', 'Furniture', 'Executive Desk');

INSERT INTO sales (customer_id, product_id, sale_amount) VALUES
    (1, 'LAPTOP', 1200.00),
    (2, 'PHONE', 800.00),
    (1, 'LAPTOP', 1250.00),
    (3, 'CHAIR', 300.00),
    (4, 'PHONE', 950.00),
    (2, 'MONITOR', 500.00),
    (5, 'TABLE', 700.00),
    (3, 'CHAIR', 320.00),
    (6, 'PHONE', 1100.00),
    (7, 'DESK', 900.00),
    (8, 'PHONE', 780.00),
    (9, 'TABLE', 650.00);

-- ROW_NUMBER creates a unique position inside each customer partition.
-- sale_id is included as a deterministic tie-breaker.
CREATE OR REPLACE VIEW customer_sale_row_numbers AS
SELECT
    s.sale_id,
    s.customer_id,
    c.customer_name,
    s.product_id,
    p.category,
    s.sale_amount,
    ROW_NUMBER() OVER (
        PARTITION BY s.customer_id
        ORDER BY s.sale_amount DESC, s.sale_id
    ) AS row_number
FROM sales s
JOIN customers c ON c.customer_id = s.customer_id
JOIN products p ON p.product_id = s.product_id;

-- The first row in each customer/product partition is the retained row.
CREATE OR REPLACE VIEW deduplicated_customer_products AS
WITH ranked AS (
    SELECT
        s.*,
        ROW_NUMBER() OVER (
            PARTITION BY s.customer_id, s.product_id
            ORDER BY s.sale_amount DESC, s.sale_id DESC
        ) AS duplicate_position
    FROM sales s
)
SELECT
    sale_id,
    customer_id,
    product_id,
    sale_amount,
    sold_at
FROM ranked
WHERE duplicate_position = 1;

-- Top-N within a group is different from global top-N.
CREATE OR REPLACE VIEW top_two_per_category AS
WITH ranked AS (
    SELECT
        s.sale_id,
        s.customer_id,
        c.customer_name,
        s.product_id,
        p.category,
        s.sale_amount,
        ROW_NUMBER() OVER (
            PARTITION BY p.category
            ORDER BY s.sale_amount DESC, s.sale_id
        ) AS category_row_number
    FROM sales s
    JOIN customers c ON c.customer_id = s.customer_id
    JOIN products p ON p.product_id = s.product_id
)
SELECT *
FROM ranked
WHERE category_row_number <= 2;

-- RANK preserves ties and can skip rank numbers.
CREATE OR REPLACE VIEW category_rank_comparison AS
SELECT
    s.sale_id,
    p.category,
    s.product_id,
    s.sale_amount,
    ROW_NUMBER() OVER (
        PARTITION BY p.category
        ORDER BY s.sale_amount DESC, s.sale_id
    ) AS row_number,
    RANK() OVER (
        PARTITION BY p.category
        ORDER BY s.sale_amount DESC
    ) AS rank,
    DENSE_RANK() OVER (
        PARTITION BY p.category
        ORDER BY s.sale_amount DESC
    ) AS dense_rank
FROM sales s
JOIN products p ON p.product_id = s.product_id;

-- A CTE makes a global top-N query explicit and reusable in larger workflows.
WITH ranked_sales AS (
    SELECT
        s.sale_id,
        c.customer_name,
        p.product_name,
        p.category,
        s.sale_amount,
        ROW_NUMBER() OVER (
            ORDER BY s.sale_amount DESC, s.sale_id
        ) AS global_row_number
    FROM sales s
    JOIN customers c ON c.customer_id = s.customer_id
    JOIN products p ON p.product_id = s.product_id
)
SELECT *
FROM ranked_sales
WHERE global_row_number <= 5
ORDER BY global_row_number;

-- Retrieve the highest-value sale for every customer.
SELECT *
FROM customer_sale_row_numbers
WHERE row_number = 1
ORDER BY customer_id;

-- Retrieve the top two records from every category.
SELECT *
FROM top_two_per_category
ORDER BY category, category_row_number;

-- Identify duplicate customer/product combinations before deduplication.
SELECT
    customer_id,
    product_id,
    COUNT(*) AS duplicate_count,
    MAX(sale_amount) AS highest_amount
FROM sales
GROUP BY customer_id, product_id
HAVING COUNT(*) > 1
ORDER BY customer_id, product_id;

-- Compare ROW_NUMBER, RANK, and DENSE_RANK on the same partitions.
SELECT *
FROM category_rank_comparison
ORDER BY category, sale_amount DESC, sale_id;

-- Transactional example: insert a sale and verify its analytical position
-- before committing. If validation fails, the entire operation is rolled back.
BEGIN;

INSERT INTO sales (customer_id, product_id, sale_amount)
VALUES (2, 'PHONE', 1025.00);

DO $$
DECLARE
    inserted_count integer;
BEGIN
    SELECT COUNT(*)
    INTO inserted_count
    FROM sales
    WHERE customer_id = 2
      AND product_id = 'PHONE'
      AND sale_amount = 1025.00;

    IF inserted_count <> 1 THEN
        RAISE EXCEPTION 'Expected exactly one transactional sale';
    END IF;
END;
$$;

COMMIT;

-- The inserted row changes the customer's ordering but does not alter
-- historical rows or the meaning of ROW_NUMBER.
SELECT *
FROM customer_sale_row_numbers
WHERE customer_id = 2
ORDER BY row_number;

-- Demonstrate a validation failure without damaging committed data.
BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sales
        WHERE sale_amount < 0
    ) THEN
        RAISE EXCEPTION 'Negative sales amount detected';
    END IF;
END;
$$;

ROLLBACK;

-- The database itself rejects invalid amounts.
-- This statement is intentionally not executed because the complete script
-- must finish successfully; the CHECK constraint represents the failure rule.

-- Useful production query: top customer within each region.
WITH customer_totals AS (
    SELECT
        c.region,
        c.customer_id,
        c.customer_name,
        SUM(s.sale_amount) AS total_sales
    FROM customers c
    JOIN sales s ON s.customer_id = c.customer_id
    GROUP BY c.region, c.customer_id, c.customer_name
),
ranked_regions AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY region
            ORDER BY total_sales DESC, customer_id
        ) AS region_row_number
    FROM customer_totals
)
SELECT
    region,
    customer_id,
    customer_name,
    total_sales,
    region_row_number
FROM ranked_regions
WHERE region_row_number = 1
ORDER BY region;

-- PostgreSQL window functions calculate rankings without collapsing rows.
-- GROUP BY is used when aggregation is required; ROW_NUMBER is used when
-- individual rows must remain visible.
