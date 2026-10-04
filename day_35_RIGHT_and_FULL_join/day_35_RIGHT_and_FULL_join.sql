DROP SCHEMA IF EXISTS join_lab CASCADE;

CREATE SCHEMA join_lab;

SET search_path TO join_lab;

-- The employee table represents the left relation in the demonstrations.
CREATE TABLE employee (
    employee_id      INTEGER PRIMARY KEY,
    employee_name    TEXT NOT NULL,
    department_id    INTEGER NULL
);

-- The department table represents the right relation. Its rows form the
-- complete master population for the RIGHT JOIN examples.
CREATE TABLE department (
    department_id    INTEGER PRIMARY KEY,
    department_name  TEXT NOT NULL UNIQUE,
    manager_id       INTEGER NULL
);

ALTER TABLE employee
    ADD CONSTRAINT employee_department_fk
    FOREIGN KEY (department_id)
    REFERENCES department (department_id);

CREATE INDEX employee_department_id_idx
    ON employee (department_id);

CREATE INDEX department_manager_id_idx
    ON department (manager_id);

INSERT INTO department (
    department_id,
    department_name,
    manager_id
)
VALUES
    (10, 'Engineering', 9001),
    (20, 'Finance', 9002),
    (30, 'Research', 9003),
    (40, 'Operations', NULL),
    (50, 'Legal', 9005);

INSERT INTO employee (
    employee_id,
    employee_name,
    department_id
)
VALUES
    (101, 'Aarav', 10),
    (102, 'Meera', 20),
    (103, 'Kabir', 20),
    (104, 'Isha', 40),
    (105, 'Rohan', NULL);

-- RIGHT JOIN preserves every row from department because department is the
-- right-side relation. Research and Legal therefore remain visible despite
-- having no employees.
SELECT
    e.employee_id,
    e.employee_name,
    e.department_id AS employee_department_id,
    d.department_id,
    d.department_name,
    d.manager_id
FROM employee AS e
RIGHT JOIN department AS d
    ON e.department_id = d.department_id
ORDER BY d.department_id, e.employee_id;

-- The same relationship written with LEFT JOIN is logically equivalent
-- when the table order is reversed. RIGHT JOIN is useful when the desired
-- preserved population is naturally expressed on the right.
SELECT
    e.employee_id,
    e.employee_name,
    d.department_id,
    d.department_name
FROM department AS d
LEFT JOIN employee AS e
    ON e.department_id = d.department_id
ORDER BY d.department_id, e.employee_id;

-- FULL OUTER JOIN preserves unmatched rows from both relations. Rohan is
-- preserved on the employee side and Research/Legal are preserved on the
-- department side.
SELECT
    e.employee_id,
    e.employee_name,
    e.department_id AS employee_department_id,
    d.department_id,
    d.department_name,
    d.manager_id,
    CASE
        WHEN e.employee_id IS NOT NULL
             AND d.department_id IS NOT NULL
            THEN 'MATCHED'
        WHEN e.employee_id IS NOT NULL
            THEN 'EMPLOYEE_WITHOUT_DEPARTMENT'
        ELSE 'DEPARTMENT_WITHOUT_EMPLOYEE'
    END AS relationship_status
FROM employee AS e
FULL OUTER JOIN department AS d
    ON e.department_id = d.department_id
ORDER BY
    CASE
        WHEN e.employee_id IS NOT NULL
             AND d.department_id IS NOT NULL THEN 1
        WHEN e.employee_id IS NOT NULL THEN 2
        ELSE 3
    END,
    COALESCE(e.employee_id, d.department_id);

-- FULL OUTER JOIN can be turned into a data-quality report by filtering
-- specifically for unmatched records.
SELECT
    e.employee_id,
    e.employee_name,
    d.department_id,
    d.department_name,
    CASE
        WHEN e.employee_id IS NULL THEN 'DEPARTMENT_HAS_NO_EMPLOYEE'
        WHEN d.department_id IS NULL THEN 'EMPLOYEE_HAS_NO_DEPARTMENT'
    END AS issue
FROM employee AS e
FULL OUTER JOIN department AS d
    ON e.department_id = d.department_id
WHERE e.employee_id IS NULL
   OR d.department_id IS NULL
ORDER BY COALESCE(e.employee_id, d.department_id);

-- SQL NULL does not equal SQL NULL. This query therefore produces two rows
-- rather than one matched pair.
WITH left_data (id, group_id) AS (
    VALUES (1, NULL::INTEGER)
),
right_data (group_id, label) AS (
    VALUES (NULL::INTEGER, 'Unassigned')
)
SELECT
    l.id,
    l.group_id AS left_group_id,
    r.group_id AS right_group_id,
    r.label
FROM left_data AS l
FULL OUTER JOIN right_data AS r
    ON l.group_id = r.group_id;

-- Multiple rows on the same key produce multiple joined rows. Finance has
-- two employees, so the single Finance department row appears twice.
SELECT
    e.employee_id,
    e.employee_name,
    d.department_id,
    d.department_name
FROM employee AS e
FULL OUTER JOIN department AS d
    ON e.department_id = d.department_id
WHERE d.department_id = 20
ORDER BY e.employee_id;

-- RIGHT JOIN is particularly useful for master-data reporting where every
-- master record must appear, including records that currently have no child.
SELECT
    d.department_id,
    d.department_name,
    COUNT(e.employee_id) AS employee_count
FROM employee AS e
RIGHT JOIN department AS d
    ON e.department_id = d.department_id
GROUP BY
    d.department_id,
    d.department_name
ORDER BY d.department_id;

-- HAVING identifies right-side departments with no matching employee.
SELECT
    d.department_id,
    d.department_name
FROM employee AS e
RIGHT JOIN department AS d
    ON e.department_id = d.department_id
GROUP BY
    d.department_id,
    d.department_name
HAVING COUNT(e.employee_id) = 0
ORDER BY d.department_id;

-- A FULL OUTER JOIN can compare two independently maintained datasets.
CREATE TABLE department_snapshot (
    department_id    INTEGER PRIMARY KEY,
    department_name  TEXT NOT NULL
);

INSERT INTO department_snapshot (
    department_id,
    department_name
)
VALUES
    (10, 'Engineering'),
    (20, 'Finance'),
    (30, 'Research'),
    (60, 'Logistics');

SELECT
    d.department_id AS current_department_id,
    d.department_name AS current_department_name,
    s.department_id AS snapshot_department_id,
    s.department_name AS snapshot_department_name,
    CASE
        WHEN d.department_id IS NOT NULL
             AND s.department_id IS NOT NULL
            THEN CASE
                WHEN d.department_name = s.department_name
                    THEN 'UNCHANGED'
                ELSE 'NAME_CHANGED'
            END
        WHEN d.department_id IS NOT NULL
            THEN 'NEW_IN_CURRENT'
        ELSE 'MISSING_FROM_CURRENT'
    END AS reconciliation_status
FROM department AS d
FULL OUTER JOIN department_snapshot AS s
    ON d.department_id = s.department_id
ORDER BY COALESCE(d.department_id, s.department_id);

-- EXPLAIN shows the optimizer's chosen strategy. The exact plan depends on
-- table statistics, indexes, PostgreSQL version, data volume, and settings.
EXPLAIN
SELECT
    e.employee_id,
    e.employee_name,
    d.department_name
FROM employee AS e
FULL OUTER JOIN department AS d
    ON e.department_id = d.department_id;

-- Transactional demonstration: the following statement is intentionally
-- invalid because the foreign key prevents an employee from referencing a
-- department that does not exist.
BEGIN;

INSERT INTO employee (
    employee_id,
    employee_name,
    department_id
)
VALUES
    (999, 'Invalid Employee', 9999);

ROLLBACK;

-- The transaction above is rolled back after PostgreSQL rejects the foreign
-- key violation. Application code should still handle constraint errors,
-- while the database remains the final integrity boundary.
SELECT
    employee_id,
    employee_name,
    department_id
FROM employee
ORDER BY employee_id;

-- This view provides a reusable department-centric report. It intentionally
-- uses RIGHT JOIN because department is the population that must be complete.
CREATE OR REPLACE VIEW department_employee_report AS
SELECT
    d.department_id,
    d.department_name,
    d.manager_id,
    COUNT(e.employee_id) AS employee_count
FROM employee AS e
RIGHT JOIN department AS d
    ON e.department_id = d.department_id
GROUP BY
    d.department_id,
    d.department_name,
    d.manager_id;

SELECT *
FROM department_employee_report
ORDER BY department_id;
