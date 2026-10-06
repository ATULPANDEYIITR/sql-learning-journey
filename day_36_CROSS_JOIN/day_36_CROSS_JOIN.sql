-- CROSS JOIN: Cartesian products, combination generation, and risk control
-- PostgreSQL-compatible SQL
--
-- The model represents a repository-development scenario in which independent
-- dimensions are combined to produce candidate deployment configurations.
-- CROSS JOIN deliberately creates every combination. Constraints and policy
-- queries then distinguish valid candidates from invalid ones.

DROP SCHEMA IF EXISTS cross_join_lab CASCADE;

CREATE SCHEMA cross_join_lab;

SET search_path = cross_join_lab;

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE environments (
    environment_id BIGSERIAL PRIMARY KEY,
    environment_name TEXT NOT NULL UNIQUE,
    risk_level TEXT NOT NULL CHECK (
        risk_level IN ('low', 'medium', 'high')
    )
);

CREATE TABLE test_suites (
    test_suite_id BIGSERIAL PRIMARY KEY,
    suite_name TEXT NOT NULL UNIQUE
);

CREATE TABLE release_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    policy_name TEXT NOT NULL UNIQUE,
    production_only BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO repositories (repository_name)
VALUES
    ('payments-api'),
    ('customer-web'),
    ('analytics-worker');

INSERT INTO environments (environment_name, risk_level)
VALUES
    ('development', 'low'),
    ('staging', 'medium'),
    ('production', 'high');

INSERT INTO test_suites (suite_name)
VALUES
    ('unit'),
    ('integration'),
    ('security');

INSERT INTO release_policies (policy_name, production_only)
VALUES
    ('standard', FALSE),
    ('regulated', TRUE);

-- A basic CROSS JOIN creates every repository/environment pair.
SELECT
    r.repository_name,
    e.environment_name,
    e.risk_level
FROM repositories AS r
CROSS JOIN environments AS e
ORDER BY r.repository_name, e.environment_name;

-- The expected cardinality is the product of the input cardinalities.
SELECT
    (SELECT COUNT(*) FROM repositories) AS repositories,
    (SELECT COUNT(*) FROM environments) AS environments,
    (SELECT COUNT(*) FROM repositories)
        * (SELECT COUNT(*) FROM environments) AS expected_rows;

-- A three-dimensional Cartesian product.
SELECT
    r.repository_name,
    e.environment_name,
    t.suite_name
FROM repositories AS r
CROSS JOIN environments AS e
CROSS JOIN test_suites AS t
ORDER BY
    r.repository_name,
    e.environment_name,
    t.suite_name;

-- A four-dimensional product represents the complete candidate deployment
-- configuration space.
CREATE VIEW candidate_deployment_matrix AS
SELECT
    r.repository_id,
    r.repository_name,
    e.environment_id,
    e.environment_name,
    t.test_suite_id,
    t.suite_name,
    p.policy_id,
    p.policy_name
FROM repositories AS r
CROSS JOIN environments AS e
CROSS JOIN test_suites AS t
CROSS JOIN release_policies AS p;

-- Inspect the raw Cartesian cardinality.
SELECT COUNT(*) AS raw_candidate_count
FROM candidate_deployment_matrix;

-- CROSS JOIN does not automatically eliminate duplicate input values.
-- This query demonstrates how DISTINCT is a separate operation.
WITH duplicate_teams(team_name) AS (
    VALUES
        ('platform'),
        ('platform'),
        ('security')
)
SELECT
    team_name,
    e.environment_name
FROM duplicate_teams
CROSS JOIN environments AS e
ORDER BY team_name, e.environment_name;

-- DISTINCT changes the result only because it is explicitly requested.
WITH duplicate_teams(team_name) AS (
    VALUES
        ('platform'),
        ('platform'),
        ('security')
)
SELECT DISTINCT
    team_name,
    e.environment_name
FROM duplicate_teams
CROSS JOIN environments AS e
ORDER BY team_name, e.environment_name;

-- Candidate validation belongs after candidate generation when the business
-- question is "which combinations are allowed?"
SELECT
    repository_name,
    environment_name,
    suite_name,
    policy_name
FROM candidate_deployment_matrix
WHERE
    NOT (
        environment_name = 'production'
        AND suite_name = 'security'
        AND policy_name <> 'regulated'
    )
    AND NOT (
        policy_name = 'regulated'
        AND environment_name <> 'production'
    )
ORDER BY
    repository_name,
    environment_name,
    suite_name,
    policy_name;

-- Store the resulting approved candidate combinations.
CREATE TABLE deployment_candidates (
    candidate_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),
    environment_id BIGINT NOT NULL
        REFERENCES environments(environment_id),
    test_suite_id BIGINT NOT NULL
        REFERENCES test_suites(test_suite_id),
    policy_id BIGINT NOT NULL
        REFERENCES release_policies(policy_id),
    candidate_status TEXT NOT NULL DEFAULT 'eligible'
        CHECK (
            candidate_status IN ('eligible', 'rejected', 'processed')
        ),
    UNIQUE (
        repository_id,
        environment_id,
        test_suite_id,
        policy_id
    )
);

-- Insert only candidates that satisfy the domain rules.
INSERT INTO deployment_candidates (
    repository_id,
    environment_id,
    test_suite_id,
    policy_id
)
SELECT
    repository_id,
    environment_id,
    test_suite_id,
    policy_id
FROM candidate_deployment_matrix
WHERE
    NOT (
        environment_name = 'production'
        AND suite_name = 'security'
        AND policy_name <> 'regulated'
    )
    AND NOT (
        policy_name = 'regulated'
        AND environment_name <> 'production'
    );

-- Indexes support common access paths after the Cartesian generation phase.
CREATE INDEX idx_deployment_candidates_environment
    ON deployment_candidates (environment_id);

CREATE INDEX idx_deployment_candidates_repository_status
    ON deployment_candidates (repository_id, candidate_status);

CREATE INDEX idx_candidate_matrix_policy
    ON deployment_candidates (policy_id);

-- A practical reporting query groups generated candidates by environment.
SELECT
    e.environment_name,
    COUNT(*) AS candidate_count
FROM deployment_candidates AS dc
JOIN environments AS e
    ON e.environment_id = dc.environment_id
GROUP BY e.environment_name
ORDER BY e.environment_name;

-- Find candidates that are production deployments and therefore require
-- stricter policy handling.
SELECT
    r.repository_name,
    e.environment_name,
    t.suite_name,
    p.policy_name
FROM deployment_candidates AS dc
JOIN repositories AS r
    ON r.repository_id = dc.repository_id
JOIN environments AS e
    ON e.environment_id = dc.environment_id
JOIN test_suites AS t
    ON t.test_suite_id = dc.test_suite_id
JOIN release_policies AS p
    ON p.policy_id = dc.policy_id
WHERE e.environment_name = 'production'
ORDER BY r.repository_name, t.suite_name;

-- Demonstrate transactionally marking a selected candidate as processed.
BEGIN;

UPDATE deployment_candidates
SET candidate_status = 'processed'
WHERE candidate_id = (
    SELECT MIN(candidate_id)
    FROM deployment_candidates
    WHERE candidate_status = 'eligible'
);

COMMIT;

-- Verify the state transition.
SELECT
    candidate_id,
    candidate_status
FROM deployment_candidates
ORDER BY candidate_id
LIMIT 5;

-- Demonstrate a database-side guard for the regulated policy.
CREATE OR REPLACE FUNCTION enforce_release_policy_scope()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    target_environment TEXT;
    target_policy TEXT;
BEGIN
    SELECT environment_name
    INTO target_environment
    FROM environments
    WHERE environment_id = NEW.environment_id;

    SELECT policy_name
    INTO target_policy
    FROM release_policies
    WHERE policy_id = NEW.policy_id;

    IF target_policy = 'regulated'
       AND target_environment <> 'production' THEN
        RAISE EXCEPTION
            'regulated policy may only be used for production';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_enforce_release_policy_scope
BEFORE INSERT OR UPDATE ON deployment_candidates
FOR EACH ROW
EXECUTE FUNCTION enforce_release_policy_scope();

-- The following statement intentionally violates the database-level policy.
-- It is wrapped in a savepoint so the demonstration does not abort the
-- surrounding transaction or leave a partial change.
BEGIN;

SAVEPOINT invalid_candidate;

DO $$
DECLARE
    repository_key BIGINT;
    staging_key BIGINT;
    regulated_key BIGINT;
    unit_key BIGINT;
BEGIN
    SELECT repository_id
    INTO repository_key
    FROM repositories
    WHERE repository_name = 'payments-api';

    SELECT environment_id
    INTO staging_key
    FROM environments
    WHERE environment_name = 'staging';

    SELECT policy_id
    INTO regulated_key
    FROM release_policies
    WHERE policy_name = 'regulated';

    SELECT test_suite_id
    INTO unit_key
    FROM test_suites
    WHERE suite_name = 'unit';

    BEGIN
        INSERT INTO deployment_candidates (
            repository_id,
            environment_id,
            test_suite_id,
            policy_id
        )
        VALUES (
            repository_key,
            staging_key,
            unit_key,
            regulated_key
        );
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Invalid combination rejected: %', SQLERRM;
    END;
END;
$$;

ROLLBACK TO SAVEPOINT invalid_candidate;
COMMIT;

-- The final query exposes the valid relational state.
SELECT
    dc.candidate_id,
    r.repository_name,
    e.environment_name,
    t.suite_name,
    p.policy_name,
    dc.candidate_status
FROM deployment_candidates AS dc
JOIN repositories AS r
    ON r.repository_id = dc.repository_id
JOIN environments AS e
    ON e.environment_id = dc.environment_id
JOIN test_suites AS t
    ON t.test_suite_id = dc.test_suite_id
JOIN release_policies AS p
    ON p.policy_id = dc.policy_id
ORDER BY
    dc.candidate_id;

-- Important operational property:
-- CROSS JOIN cardinality is multiplicative. If dimensions contain 3, 10,
-- 100, and 1,000 rows, the unfiltered product contains:
--
-- 3 * 10 * 100 * 1,000 = 3,000,000 rows.
--
-- Filtering conditions may reduce the final result, but the optimizer must
-- still reason about the candidate space. Restricting dimensions before the
-- CROSS JOIN can therefore be materially different from generating an
-- unnecessarily large intermediate relation and filtering afterward.
