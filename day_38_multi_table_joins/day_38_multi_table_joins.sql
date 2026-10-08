-- Multi-Table JOINs
-- PostgreSQL-compatible executable demonstration.
--
-- Domain:
--     sales_regions
--          |
--      customers
--          |
--        orders
--          |
--     order_items
--          |
--       products
--
-- The schema deliberately contains both one-to-many relationships and the
-- order_items bridge needed to represent the many-to-many relationship
-- between orders and products.

DROP SCHEMA IF EXISTS multi_table_join_demo CASCADE;
CREATE SCHEMA multi_table_join_demo;
SET search_path TO multi_table_join_demo;

CREATE TABLE sales_regions (
    region_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    region_name TEXT NOT NULL UNIQUE
);

CREATE TABLE customers (
    customer_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name TEXT NOT NULL,
    region_id INTEGER NOT NULL
        REFERENCES sales_regions(region_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE products (
    product_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    UNIQUE (product_name)
);

CREATE TABLE orders (
    order_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id INTEGER NOT NULL
        REFERENCES customers(customer_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    order_date DATE NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED')
    )
);

CREATE TABLE order_items (
    order_id INTEGER NOT NULL
        REFERENCES orders(order_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    product_id INTEGER NOT NULL
        REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    PRIMARY KEY (order_id, product_id)
);

CREATE INDEX idx_customers_region
    ON customers(region_id);

CREATE INDEX idx_orders_customer
    ON orders(customer_id);

CREATE INDEX idx_orders_status_date
    ON orders(status, order_date);

CREATE INDEX idx_order_items_product
    ON order_items(product_id);

INSERT INTO sales_regions(region_name)
VALUES
    ('North'),
    ('South'),
    ('West'),
    ('East');

INSERT INTO customers(customer_name, region_id)
SELECT 'Aarav Systems', region_id
FROM sales_regions
WHERE region_name = 'North';

INSERT INTO customers(customer_name, region_id)
SELECT 'Bharat Logistics', region_id
FROM sales_regions
WHERE region_name = 'South';

INSERT INTO customers(customer_name, region_id)
SELECT 'Civic Research Lab', region_id
FROM sales_regions
WHERE region_name = 'West';

INSERT INTO customers(customer_name, region_id)
SELECT 'Delta Manufacturing', region_id
FROM sales_regions
WHERE region_name = 'North';

INSERT INTO customers(customer_name, region_id)
SELECT 'Eastern Retail Group', region_id
FROM sales_regions
WHERE region_name = 'East';

INSERT INTO products(product_name, category, unit_price)
VALUES
    ('Edge Sensor', 'IoT', 120.00),
    ('Gateway Pro', 'Networking', 450.00),
    ('Analytics License', 'Software', 800.00),
    ('Secure Router', 'Networking', 600.00),
    ('Inspection Camera', 'Vision', 950.00);

INSERT INTO orders(customer_id, order_date, status)
SELECT customer_id, DATE '2026-09-01', 'DELIVERED'
FROM customers
WHERE customer_name = 'Aarav Systems';

INSERT INTO orders(customer_id, order_date, status)
SELECT customer_id, DATE '2026-09-14', 'SHIPPED'
FROM customers
WHERE customer_name = 'Aarav Systems';

INSERT INTO orders(customer_id, order_date, status)
SELECT customer_id, DATE '2026-09-18', 'DELIVERED'
FROM customers
WHERE customer_name = 'Bharat Logistics';

INSERT INTO orders(customer_id, order_date, status)
SELECT customer_id, DATE '2026-09-20', 'CANCELLED'
FROM customers
WHERE customer_name = 'Civic Research Lab';

INSERT INTO orders(customer_id, order_date, status)
SELECT customer_id, DATE '2026-09-22', 'DELIVERED'
FROM customers
WHERE customer_name = 'Delta Manufacturing';

INSERT INTO orders(customer_id, order_date, status)
SELECT customer_id, DATE '2026-09-24', 'PLACED'
FROM customers
WHERE customer_name = 'Eastern Retail Group';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 10, 120.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Edge Sensor'
WHERE c.customer_name = 'Aarav Systems'
  AND o.order_date = DATE '2026-09-01';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 2, 450.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Gateway Pro'
WHERE c.customer_name = 'Aarav Systems'
  AND o.order_date = DATE '2026-09-01';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 1, 800.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Analytics License'
WHERE c.customer_name = 'Aarav Systems'
  AND o.order_date = DATE '2026-09-14';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 5, 120.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Edge Sensor'
WHERE c.customer_name = 'Aarav Systems'
  AND o.order_date = DATE '2026-09-14';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 3, 600.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Secure Router'
WHERE c.customer_name = 'Bharat Logistics'
  AND o.order_date = DATE '2026-09-18';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 20, 120.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Edge Sensor'
WHERE c.customer_name = 'Bharat Logistics'
  AND o.order_date = DATE '2026-09-18';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 1, 950.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Inspection Camera'
WHERE c.customer_name = 'Civic Research Lab'
  AND o.order_date = DATE '2026-09-20';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 4, 950.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Inspection Camera'
WHERE c.customer_name = 'Delta Manufacturing'
  AND o.order_date = DATE '2026-09-22';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 2, 800.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Analytics License'
WHERE c.customer_name = 'Delta Manufacturing'
  AND o.order_date = DATE '2026-09-22';

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 1, 450.00
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_name = 'Gateway Pro'
WHERE c.customer_name = 'Eastern Retail Group'
  AND o.order_date = DATE '2026-09-24';

-- Basic three-table JOIN:
-- customers -> orders -> order_items.
SELECT
    c.customer_name,
    o.order_id,
    o.order_date,
    oi.product_id,
    oi.quantity
FROM customers AS c
JOIN orders AS o
    ON o.customer_id = c.customer_id
JOIN order_items AS oi
    ON oi.order_id = o.order_id
ORDER BY c.customer_name, o.order_id, oi.product_id;

-- Five-table JOIN:
-- region -> customer -> order -> item -> product.
SELECT
    r.region_name,
    c.customer_name,
    o.order_id,
    o.status,
    p.product_name,
    p.category,
    oi.quantity,
    oi.unit_price,
    ROUND(oi.quantity * oi.unit_price, 2) AS line_value
FROM sales_regions AS r
JOIN customers AS c
    ON c.region_id = r.region_id
JOIN orders AS o
    ON o.customer_id = c.customer_id
JOIN order_items AS oi
    ON oi.order_id = o.order_id
JOIN products AS p
    ON p.product_id = oi.product_id
WHERE o.status <> 'CANCELLED'
ORDER BY r.region_name, o.order_id, p.product_name;

-- Written JOIN order can differ while the relational result remains the
-- same for inner joins. PostgreSQL's optimizer decides physical execution.
SELECT
    c.customer_name,
    o.order_id,
    p.product_name
FROM products AS p
JOIN order_items AS oi
    ON oi.product_id = p.product_id
JOIN orders AS o
    ON o.order_id = oi.order_id
JOIN customers AS c
    ON c.customer_id = o.customer_id
ORDER BY c.customer_name, o.order_id, p.product_name;

-- LEFT JOIN preserves every customer, including customers without an order.
SELECT
    c.customer_name,
    COUNT(o.order_id) AS order_count
FROM customers AS c
LEFT JOIN orders AS o
    ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY c.customer_id;

-- A predicate in WHERE can remove NULL rows from a LEFT JOIN. Keeping the
-- predicate in ON preserves customers that have no qualifying order.
SELECT
    c.customer_name,
    o.order_id
FROM customers AS c
LEFT JOIN orders AS o
    ON o.customer_id = c.customer_id
   AND o.status = 'DELIVERED'
ORDER BY c.customer_id;

-- Many-to-many analysis:
-- orders and products are connected through order_items.
SELECT
    p.product_name,
    COUNT(DISTINCT o.order_id) AS distinct_orders,
    SUM(oi.quantity) AS units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM products AS p
JOIN order_items AS oi
    ON oi.product_id = p.product_id
JOIN orders AS o
    ON o.order_id = oi.order_id
WHERE o.status <> 'CANCELLED'
GROUP BY p.product_id, p.product_name
ORDER BY revenue DESC;

-- CTE separates order-level aggregation from the later customer and region
-- joins. This is useful when the intermediate relation has business meaning.
WITH order_totals AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.status,
        SUM(oi.quantity * oi.unit_price) AS order_value
    FROM orders AS o
    JOIN order_items AS oi
        ON oi.order_id = o.order_id
    GROUP BY o.order_id, o.customer_id, o.status
)
SELECT
    r.region_name,
    c.customer_name,
    ot.order_id,
    ROUND(ot.order_value, 2) AS order_value
FROM order_totals AS ot
JOIN customers AS c
    ON c.customer_id = ot.customer_id
JOIN sales_regions AS r
    ON r.region_id = c.region_id
WHERE ot.status = 'DELIVERED'
  AND ot.order_value >= 1000
ORDER BY ot.order_value DESC;

-- Aggregate after joining all required relationships. COUNT(DISTINCT) is
-- used for orders because multiple order-item rows would otherwise multiply
-- the order count.
SELECT
    r.region_name,
    c.customer_name,
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS delivered_revenue
FROM sales_regions AS r
JOIN customers AS c
    ON c.region_id = r.region_id
JOIN orders AS o
    ON o.customer_id = c.customer_id
JOIN order_items AS oi
    ON oi.order_id = o.order_id
WHERE o.status = 'DELIVERED'
GROUP BY r.region_id, r.region_name, c.customer_id, c.customer_name
HAVING SUM(oi.quantity * oi.unit_price) > 1000
ORDER BY delivered_revenue DESC;

-- Relationship-aware validation query. A valid relational schema should
-- normally make these orphan rows impossible through foreign keys.
SELECT
    oi.order_id,
    oi.product_id
FROM order_items AS oi
LEFT JOIN orders AS o
    ON o.order_id = oi.order_id
LEFT JOIN products AS p
    ON p.product_id = oi.product_id
WHERE o.order_id IS NULL
   OR p.product_id IS NULL;

-- Query-plan inspection. PostgreSQL can reorder joins physically even when
-- the SQL text presents them in a different sequence.
EXPLAIN (COSTS OFF)
SELECT
    r.region_name,
    c.customer_name,
    o.order_id,
    p.product_name
FROM sales_regions AS r
JOIN customers AS c ON c.region_id = r.region_id
JOIN orders AS o ON o.customer_id = c.customer_id
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE r.region_name = 'North';

-- Transactional integrity demonstration. The invalid foreign-key insert
-- fails, and the transaction is rolled back.
BEGIN;

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
VALUES (999999, 1, 1, 120.00);

ROLLBACK;
