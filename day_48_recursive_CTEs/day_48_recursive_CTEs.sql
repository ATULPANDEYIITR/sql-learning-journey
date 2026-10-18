DROP SCHEMA IF EXISTS recursive_cte_demo CASCADE;
CREATE SCHEMA recursive_cte_demo;
SET search_path TO recursive_cte_demo;

CREATE TABLE employees (
    employee_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_code text NOT NULL UNIQUE,
    employee_name text NOT NULL,
    job_title text NOT NULL,
    manager_id integer NULL,
    hired_on date NOT NULL,
    active boolean NOT NULL DEFAULT true,
    CONSTRAINT employees_manager_fk
        FOREIGN KEY (manager_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT,
    CONSTRAINT employees_not_self_managed
        CHECK (manager_id IS NULL OR manager_id <> employee_id)
);

CREATE INDEX employees_manager_idx
    ON employees(manager_id);

INSERT INTO employees
    (employee_code, employee_name, job_title, manager_id, hired_on)
VALUES
    ('CEO-001', 'Maya', 'Chief Executive Officer', NULL, '2018-04-02');

INSERT INTO employees
    (employee_code, employee_name, job_title, manager_id, hired_on)
SELECT
    'CTO-001', 'Arjun', 'Chief Technology Officer', employee_id, '2019-01-14'
FROM employees
WHERE employee_code = 'CEO-001';

INSERT INTO employees
    (employee_code, employee_name, job_title, manager_id, hired_on)
SELECT
    'CFO-001', 'Neha', 'Chief Financial Officer', employee_id, '2019-02-11'
FROM employees
WHERE employee_code = 'CEO-001';

INSERT INTO employees
    (employee_code, employee_name, job_title, manager_id, hired_on)
SELECT
    v.code,
    v.name,
    v.title,
    e.employee_id,
    v.hired_on
FROM (
    VALUES
        ('ENG-DIR', 'Ravi', 'Engineering Director', '2019-08-05'::date),
        ('SEC-DIR', 'Sara', 'Security Director', '2020-01-06'::date)
) AS v(code, name, title, hired_on)
CROSS JOIN employees e
WHERE e.employee_code = 'CTO-001';

INSERT INTO employees
    (employee_code, employee_name, job_title, manager_id, hired_on)
SELECT
    v.code,
    v.name,
    v.title,
    e.employee_id,
    v.hired_on
FROM (
    VALUES
        ('FIN-MGR', 'Ishaan', 'Finance Manager', '2020-07-13'::date)
) AS v(code, name, title, hired_on)
CROSS JOIN employees e
WHERE e.employee_code = 'CFO-001';

INSERT INTO employees
    (employee_code, employee_name, job_title, manager_id, hired_on)
SELECT
    v.code,
    v.name,
    v.title,
    e.employee_id,
    v.hired_on
FROM (
    VALUES
        ('BE-LEAD', 'Kiran', 'Backend Lead', '2021-03-15'::date),
        ('FE-LEAD', 'Asha', 'Frontend Lead', '2021-05-17'::date)
) AS v(code, name, title, hired_on)
CROSS JOIN employees e
WHERE e.employee_code = 'ENG-DIR';

INSERT INTO employees
    (employee_code, employee_name, job_title, manager_id, hired_on)
SELECT
    v.code,
    v.name,
    v.title,
    e.employee_id,
    v.hired_on
FROM (
    VALUES
        ('BE-001', 'Dev', 'Backend Engineer', '2022-02-07'::date),
        ('BE-002', 'Meera', 'Backend Engineer', '2022-06-20'::date)
) AS v(code, name, title, hired_on)
CROSS JOIN employees e
WHERE e.employee_code = 'BE-LEAD';

INSERT INTO employees
    (employee_code, employee_name, job_title, manager_id, hired_on)
SELECT
    v.code,
    v.name,
    v.title,
    e.employee_id,
    v.hired_on
FROM (
    VALUES
        ('SEC-001', 'Vikram', 'Security Engineer', '2021-09-13'::date),
        ('SEC-002', 'Nisha', 'Security Analyst', '2022-11-21'::date)
) AS v(code, name, title, hired_on)
CROSS JOIN employees e
WHERE e.employee_code = 'SEC-DIR';

-- The anchor member selects organizational roots. The recursive member
-- repeatedly joins employees to the employee reached by the previous level.
WITH RECURSIVE organization_tree AS (
    SELECT
        employee_id,
        employee_code,
        employee_name,
        job_title,
        manager_id,
        0 AS depth,
        ARRAY[employee_id] AS id_path,
        employee_name::text AS name_path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    SELECT
        child.employee_id,
        child.employee_code,
        child.employee_name,
        child.job_title,
        child.manager_id,
        parent.depth + 1,
        parent.id_path || child.employee_id,
        parent.name_path || ' > ' || child.employee_name
    FROM organization_tree AS parent
    JOIN employees AS child
      ON child.manager_id = parent.employee_id
    WHERE NOT child.employee_id = ANY(parent.id_path)
)
SELECT
    employee_code,
    employee_name,
    job_title,
    depth,
    name_path
FROM organization_tree
ORDER BY id_path;

-- Recursive traversal rooted at one manager. This returns only that
-- manager's reachable descendants and preserves depth relative to the root.
WITH RECURSIVE engineering_tree AS (
    SELECT
        employee_id,
        employee_name,
        manager_id,
        0 AS depth,
        ARRAY[employee_id] AS path
    FROM employees
    WHERE employee_code = 'ENG-DIR'

    UNION ALL

    SELECT
        child.employee_id,
        child.employee_name,
        child.manager_id,
        parent.depth + 1,
        parent.path || child.employee_id
    FROM engineering_tree AS parent
    JOIN employees AS child
      ON child.manager_id = parent.employee_id
    WHERE NOT child.employee_id = ANY(parent.path)
)
SELECT
    employee_name,
    depth,
    path
FROM engineering_tree
ORDER BY path;

-- Recursive upward traversal follows manager_id in the opposite direction.
WITH RECURSIVE management_chain AS (
    SELECT
        employee_id,
        employee_name,
        manager_id,
        0 AS distance,
        ARRAY[employee_id] AS path
    FROM employees
    WHERE employee_code = 'BE-001'

    UNION ALL

    SELECT
        manager.employee_id,
        manager.employee_name,
        manager.manager_id,
        chain.distance + 1,
        chain.path || manager.employee_id
    FROM management_chain AS chain
    JOIN employees AS manager
      ON manager.employee_id = chain.manager_id
    WHERE NOT manager.employee_id = ANY(chain.path)
)
SELECT
    employee_name,
    distance,
    path
FROM management_chain
ORDER BY distance;

-- A recursive CTE can also produce subtree membership, which can then
-- participate in normal aggregation.
WITH RECURSIVE subtree AS (
    SELECT
        employee_id AS root_id,
        employee_id AS member_id
    FROM employees

    UNION ALL

    SELECT
        subtree.root_id,
        child.employee_id
    FROM subtree
    JOIN employees AS child
      ON child.manager_id = subtree.member_id
)
SELECT
    root.employee_name AS manager,
    COUNT(subtree.member_id) AS subtree_size
FROM subtree
JOIN employees AS root
  ON root.employee_id = subtree.root_id
GROUP BY root.employee_id, root.employee_name
ORDER BY subtree_size DESC, manager;

-- PostgreSQL can enforce a bounded hierarchy depth with a validation
-- function. The function walks upward and rejects cycles even when data
-- is introduced by multiple statements.
CREATE OR REPLACE FUNCTION validate_manager_chain()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    current_manager integer;
    visited integer[] := ARRAY[]::integer[];
BEGIN
    current_manager := NEW.manager_id;

    WHILE current_manager IS NOT NULL LOOP
        IF current_manager = NEW.employee_id THEN
            RAISE EXCEPTION
                'Management cycle detected for employee %',
                NEW.employee_id;
        END IF;

        IF current_manager = ANY(visited) THEN
            RAISE EXCEPTION
                'Existing management cycle detected near employee %',
                current_manager;
        END IF;

        visited := visited || current_manager;

        SELECT manager_id
        INTO current_manager
        FROM employees
        WHERE employee_id = current_manager;
    END LOOP;

    RETURN NEW;
END;
$$;

CREATE TRIGGER employees_validate_manager_chain
BEFORE INSERT OR UPDATE OF manager_id
ON employees
FOR EACH ROW
EXECUTE FUNCTION validate_manager_chain();

-- Transactional reassignment demonstrates that hierarchy changes should
-- be validated atomically. The trigger prevents assigning an employee below
-- itself or into a cycle.
BEGIN;

UPDATE employees
SET manager_id = (
    SELECT employee_id
    FROM employees
    WHERE employee_code = 'SEC-DIR'
)
WHERE employee_code = 'SEC-002';

COMMIT;

-- A failed operation is rolled back by the transaction, leaving the
-- hierarchy consistent.
BEGIN;

SAVEPOINT before_invalid_reassignment;

DO $$
DECLARE
    employee_id_value integer;
BEGIN
    SELECT employee_id
    INTO employee_id_value
    FROM employees
    WHERE employee_code = 'SEC-DIR';

    BEGIN
        UPDATE employees
        SET manager_id = employee_id_value
        WHERE employee_id = employee_id_value;
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE 'Self-management was rejected';
            ROLLBACK TO SAVEPOINT before_invalid_reassignment;
    END;
END;
$$;

ROLLBACK;

-- Materialized hierarchy information should not replace recursive traversal
-- when organizational relationships change frequently. This view always
-- computes the current tree.
CREATE OR REPLACE VIEW employee_hierarchy AS
WITH RECURSIVE tree AS (
    SELECT
        employee_id,
        employee_code,
        employee_name,
        job_title,
        manager_id,
        0 AS depth,
        ARRAY[employee_id] AS path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    SELECT
        child.employee_id,
        child.employee_code,
        child.employee_name,
        child.job_title,
        child.manager_id,
        tree.depth + 1,
        tree.path || child.employee_id
    FROM tree
    JOIN employees AS child
      ON child.manager_id = tree.employee_id
    WHERE NOT child.employee_id = ANY(tree.path)
)
SELECT
    employee_id,
    employee_code,
    employee_name,
    job_title,
    manager_id,
    depth,
    path
FROM tree;

SELECT *
FROM employee_hierarchy
ORDER BY path;

-- Recursive queries become especially useful when a business question is
-- expressed as "all descendants satisfying a condition".
WITH RECURSIVE security_tree AS (
    SELECT employee_id, employee_name, manager_id, 0 AS depth
    FROM employees
    WHERE employee_code = 'SEC-DIR'

    UNION ALL

    SELECT child.employee_id, child.employee_name, child.manager_id,
           security_tree.depth + 1
    FROM security_tree
    JOIN employees AS child
      ON child.manager_id = security_tree.employee_id
)
SELECT employee_name, depth
FROM security_tree
WHERE depth > 0
ORDER BY depth, employee_name;
