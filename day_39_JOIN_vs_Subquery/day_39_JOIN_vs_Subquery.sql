-- JOIN vs Subquery
-- PostgreSQL-compatible relational laboratory.
--
-- The schema models employees, departments, projects, and assignments.
-- The queries intentionally demonstrate different relational intentions:
-- direct relationship retrieval, existence testing, correlated comparison,
-- pre-aggregation, anti-joins, and query-plan inspection.
--
-- PostgreSQL is used because it provides strong constraints, CTEs,
-- EXPLAIN, indexes, and transaction support suitable for query-design study.

DROP SCHEMA IF EXISTS join_subquery_lab CASCADE;
CREATE SCHEMA join_subquery_lab;
SET search_path TO join_subquery_lab;

CREATE TABLE departments (
    department_id BIGSERIAL PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE
);

CREATE TABLE employees (
    employee_id BIGSERIAL PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department_id BIGINT NOT NULL
        REFERENCES departments(department_id),
    salary NUMERIC(12, 2) NOT NULL
        CHECK (salary > 0)
);

CREATE TABLE projects (
    project_id BIGSERIAL PRIMARY KEY,
    project_name TEXT NOT NULL UNIQUE,
    department_id BIGINT NOT NULL
        REFERENCES departments(department_id),
    budget NUMERIC(14, 2) NOT NULL
        CHECK (budget >= 0)
);

CREATE TABLE employee_projects (
    employee_id BIGINT NOT NULL
        REFERENCES employees(employee_id)
        ON DELETE CASCADE,
    project_id BIGINT NOT NULL
        REFERENCES projects(project_id)
        ON DELETE CASCADE,
    hours_per_month INTEGER NOT NULL
        CHECK (hours_per_month > 0),
    PRIMARY KEY (employee_id, project_id)
);

CREATE INDEX idx_employees_department
    ON employees(department_id);

CREATE INDEX idx_employees_salary
    ON employees(salary);

CREATE INDEX idx_projects_department
    ON projects(department_id);

CREATE INDEX idx_employee_projects_project
    ON employee_projects(project_id);

INSERT INTO departments (department_name)
VALUES
    ('Engineering'),
    ('Finance'),
    ('Operations'),
    ('Human Resources'),
    ('Research');

INSERT INTO employees
    (employee_name, department_id, salary)
VALUES
    ('Asha', 1, 125000),
    ('Ravi', 1, 98000),
    ('Meera', 1, 112000),
    ('Kabir', 2, 87000),
    ('Neha', 2, 92000),
    ('Arjun', 3, 76000),
    ('Isha', 3, 81000),
    ('Vikram', 4, 72000),
    ('Sara', 5, 130000),
    ('Dev', 5, 105000);

INSERT INTO projects
    (project_name, department_id, budget)
VALUES
    ('Cloud Migration', 1, 500000),
    ('Fraud Analytics', 2, 350000),
    ('Warehouse Automation', 3, 275000),
    ('Recruitment Portal', 4, 90000),
    ('Quantum Research', 5, 600000),
    ('Internal Audit', 2, 120000);

INSERT INTO employee_projects
    (employee_id, project_id, hours_per_month)
VALUES
    (1, 1, 80),
    (2, 1, 120),
    (3, 1, 90),
    (3, 5, 40),
    (4, 2, 70),
    (5, 2, 110),
    (6, 3, 100),
    (7, 3, 120),
    (8, 4, 100),
    (9, 5, 130),
    (10, 5, 100),
    (5, 6, 50);

-- Direct relationship retrieval.
-- JOIN is natural because columns from both relations belong in the output.
SELECT
    e.employee_name,
    d.department_name,
    e.salary
FROM employees AS e
JOIN departments AS d
  ON d.department_id = e.department_id
ORDER BY e.employee_id;

-- A subquery can express the same department-filtering requirement when
-- the intermediate department set is the conceptual focus.
SELECT
    e.employee_name,
    e.salary
FROM employees AS e
WHERE e.department_id IN (
    SELECT d.department_id
    FROM departments AS d
    WHERE d.department_name IN ('Engineering', 'Research')
)
ORDER BY e.employee_id;

-- Scalar subquery versus JOIN for a single department lookup.
-- The scalar form assumes the department name identifies at most one row,
-- which is guaranteed by the UNIQUE constraint.
SELECT
    e.employee_name,
    e.salary
FROM employees AS e
WHERE e.department_id = (
    SELECT d.department_id
    FROM departments AS d
    WHERE d.department_name = 'Engineering'
)
ORDER BY e.salary DESC;

SELECT
    e.employee_name,
    e.salary
FROM employees AS e
JOIN departments AS d
  ON d.department_id = e.department_id
WHERE d.department_name = 'Engineering'
ORDER BY e.salary DESC;

-- JOIN aggregation.
-- LEFT JOIN preserves departments that have no employees.
SELECT
    d.department_name,
    COUNT(e.employee_id) AS employee_count,
    ROUND(AVG(e.salary), 2) AS average_salary
FROM departments AS d
LEFT JOIN employees AS e
  ON e.department_id = d.department_id
GROUP BY d.department_id, d.department_name
ORDER BY d.department_id;

-- Correlated subqueries.
-- Each scalar subquery is evaluated conceptually in relation to the current
-- department row. The database optimizer may transform the physical plan.
SELECT
    d.department_name,
    (
        SELECT COUNT(*)
        FROM employees AS e
        WHERE e.department_id = d.department_id
    ) AS employee_count,
    (
        SELECT ROUND(AVG(e.salary), 2)
        FROM employees AS e
        WHERE e.department_id = d.department_id
    ) AS average_salary
FROM departments AS d
ORDER BY d.department_id;

-- Correlated comparison:
-- each employee is compared with the average salary of that employee's
-- department.
SELECT
    e.employee_name,
    d.department_name,
    e.salary
FROM employees AS e
JOIN departments AS d
  ON d.department_id = e.department_id
WHERE e.salary > (
    SELECT AVG(e2.salary)
    FROM employees AS e2
    WHERE e2.department_id = e.department_id
)
ORDER BY d.department_name, e.salary DESC;

-- Derived-table alternative.
-- The aggregate relation is computed first, then joined to employees.
SELECT
    e.employee_name,
    d.department_name,
    e.salary,
    averages.average_salary
FROM employees AS e
JOIN departments AS d
  ON d.department_id = e.department_id
JOIN (
    SELECT
        department_id,
        AVG(salary) AS average_salary
    FROM employees
    GROUP BY department_id
) AS averages
  ON averages.department_id = e.department_id
WHERE e.salary > averages.average_salary
ORDER BY d.department_name, e.salary DESC;

-- CTE alternative.
-- A CTE gives the aggregate relation a meaningful name and makes the
-- multi-stage query easier to reason about.
WITH department_salary AS (
    SELECT
        department_id,
        AVG(salary) AS average_salary,
        MAX(salary) AS maximum_salary,
        MIN(salary) AS minimum_salary
    FROM employees
    GROUP BY department_id
)
SELECT
    d.department_name,
    ds.average_salary,
    ds.minimum_salary,
    ds.maximum_salary
FROM department_salary AS ds
JOIN departments AS d
  ON d.department_id = ds.department_id
ORDER BY d.department_id;

-- EXISTS for relationship existence.
-- An employee appears once even when multiple qualifying projects exist.
SELECT
    e.employee_name,
    e.salary
FROM employees AS e
WHERE EXISTS (
    SELECT 1
    FROM employee_projects AS ep
    JOIN projects AS p
      ON p.project_id = ep.project_id
    WHERE ep.employee_id = e.employee_id
      AND p.budget >= 500000
)
ORDER BY e.employee_id;

-- JOIN version of the same relationship test.
-- This produces one row for every qualifying project relationship.
SELECT
    e.employee_name,
    p.project_name,
    p.budget
FROM employees AS e
JOIN employee_projects AS ep
  ON ep.employee_id = e.employee_id
JOIN projects AS p
  ON p.project_id = ep.project_id
WHERE p.budget >= 500000
ORDER BY e.employee_id, p.project_id;

-- DISTINCT can recover employee-level uniqueness from the JOIN, but it is
-- unnecessary when the real requirement is merely existence.
SELECT DISTINCT
    e.employee_name
FROM employees AS e
JOIN employee_projects AS ep
  ON ep.employee_id = e.employee_id
JOIN projects AS p
  ON p.project_id = ep.project_id
WHERE p.budget >= 500000
ORDER BY e.employee_name;

-- Anti-join.
-- The NULL test identifies departments for which the LEFT JOIN found no
-- matching employee.
SELECT
    d.department_name
FROM departments AS d
LEFT JOIN employees AS e
  ON e.department_id = d.department_id
WHERE e.employee_id IS NULL
ORDER BY d.department_name;

-- NOT EXISTS expresses the absence condition directly.
SELECT
    d.department_name
FROM departments AS d
WHERE NOT EXISTS (
    SELECT 1
    FROM employees AS e
    WHERE e.department_id = d.department_id
)
ORDER BY d.department_name;

-- NOT EXISTS is preferable to NOT IN when the subquery can contain NULLs.
-- This demonstration uses an explicit nullable expression to make the
-- semantic distinction visible.
SELECT
    d.department_name
FROM departments AS d
WHERE NOT EXISTS (
    SELECT 1
    FROM employees AS e
    WHERE e.department_id = d.department_id
      AND e.employee_id IS NULL
)
ORDER BY d.department_name;

-- A realistic multi-stage report:
-- first aggregate assignment hours, then compare project budgets with the
-- average budget of projects in the same department.
WITH project_metrics AS (
    SELECT
        p.project_id,
        p.project_name,
        p.department_id,
        p.budget,
        COALESCE(SUM(ep.hours_per_month), 0) AS monthly_hours,
        COUNT(DISTINCT ep.employee_id) AS assigned_employee_count
    FROM projects AS p
    LEFT JOIN employee_projects AS ep
      ON ep.project_id = p.project_id
    GROUP BY
        p.project_id,
        p.project_name,
        p.department_id,
        p.budget
),
department_project_average AS (
    SELECT
        department_id,
        AVG(budget) AS average_project_budget
    FROM projects
    GROUP BY department_id
)
SELECT
    pm.project_name,
    d.department_name,
    pm.budget,
    pm.monthly_hours,
    pm.assigned_employee_count,
    ROUND(dpa.average_project_budget, 2)
        AS average_project_budget
FROM project_metrics AS pm
JOIN departments AS d
  ON d.department_id = pm.department_id
JOIN department_project_average AS dpa
  ON dpa.department_id = pm.department_id
WHERE pm.budget > dpa.average_project_budget
ORDER BY pm.budget DESC;

-- PostgreSQL execution-plan inspection.
-- EXPLAIN estimates work; EXPLAIN ANALYZE executes the statement and reports
-- actual timing and row counts. ANALYZE should be used carefully for
-- statements that modify data, so the examples below are SELECT statements.
EXPLAIN
SELECT
    e.employee_name,
    d.department_name
FROM employees AS e
JOIN departments AS d
  ON d.department_id = e.department_id
WHERE d.department_name = 'Engineering';

EXPLAIN
SELECT
    e.employee_name
FROM employees AS e
WHERE e.department_id = (
    SELECT d.department_id
    FROM departments AS d
    WHERE d.department_name = 'Engineering'
);

EXPLAIN
SELECT
    e.employee_name
FROM employees AS e
WHERE EXISTS (
    SELECT 1
    FROM employee_projects AS ep
    JOIN projects AS p
      ON p.project_id = ep.project_id
    WHERE ep.employee_id = e.employee_id
      AND p.budget >= 500000
);

-- EXPLAIN ANALYZE provides measured behavior on the current data.
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    e.employee_name,
    d.department_name
FROM employees AS e
JOIN departments AS d
  ON d.department_id = e.department_id
WHERE d.department_name = 'Engineering';

-- Transactional demonstration.
-- Temporary staging data shows how a query can be evaluated and rolled back
-- without permanently changing the relational model.
BEGIN;

CREATE TEMP TABLE query_design_probe (
    employee_name TEXT,
    salary NUMERIC(12, 2)
) ON COMMIT DROP;

INSERT INTO query_design_probe
SELECT
    employee_name,
    salary
FROM employees
WHERE salary > (
    SELECT AVG(salary)
    FROM employees
);

SELECT *
FROM query_design_probe
ORDER BY salary DESC;

ROLLBACK;

-- Final integrity check.
-- The relational design prevents orphaned departments, projects, employees,
-- and assignments through foreign keys.
SELECT
    'employees' AS relation_name,
    COUNT(*) AS row_count
FROM employees
UNION ALL
SELECT
    'departments',
    COUNT(*)
FROM departments
UNION ALL
SELECT
    'projects',
    COUNT(*)
FROM projects
UNION ALL
SELECT
    'employee_projects',
    COUNT(*)
FROM employee_projects
ORDER BY relation_name;
