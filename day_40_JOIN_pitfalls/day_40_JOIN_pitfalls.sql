DROP SCHEMA IF EXISTS join_pitfalls_lab CASCADE;
CREATE SCHEMA join_pitfalls_lab;
SET search_path TO join_pitfalls_lab;

-- The schema uses PostgreSQL because its constraints, CTEs, FILTER clauses,
-- partial indexes, and IS NOT DISTINCT FROM make JOIN behavior easy to
-- demonstrate precisely.

CREATE TABLE repository (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE
);

CREATE TABLE app_user (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE
);

CREATE TABLE branch (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repository(repository_id),
    branch_name TEXT NOT NULL,
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE pull_request (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repository(repository_id),
    source_branch_id BIGINT NOT NULL REFERENCES branch(branch_id),
    target_branch_id BIGINT NOT NULL REFERENCES branch(branch_id),
    author_id BIGINT NOT NULL REFERENCES app_user(user_id),
    title TEXT NOT NULL,
    is_draft BOOLEAN NOT NULL DEFAULT FALSE,
    state TEXT NOT NULL CHECK (state IN ('OPEN', 'CLOSED')),
    head_commit_sha TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE commit_record (
    commit_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_request(pull_request_id),
    commit_sha TEXT NOT NULL,
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (pull_request_id, commit_sha)
);

CREATE TABLE review (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_request(pull_request_id),
    reviewer_id BIGINT NOT NULL REFERENCES app_user(user_id),
    review_state TEXT NOT NULL CHECK (
        review_state IN (
            'COMMENTED',
            'CHANGES_REQUESTED',
            'APPROVED',
            'DISMISSED'
        )
    ),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE review_comment (
    review_comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES review(review_id),
    file_path TEXT NOT NULL,
    line_number INTEGER CHECK (line_number > 0),
    comment_text TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE status_check (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_request(pull_request_id),
    check_name TEXT NOT NULL,
    check_state TEXT NOT NULL CHECK (
        check_state IN ('PENDING', 'PASSED', 'FAILED')
    ),
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name)
);

CREATE TABLE branch_protection (
    branch_protection_id BIGSERIAL PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE REFERENCES branch(branch_id),
    required_approvals INTEGER NOT NULL CHECK (required_approvals >= 0),
    require_status_checks BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_deletion BOOLEAN NOT NULL DEFAULT TRUE,
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT FALSE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_pr_target_branch
    ON pull_request(target_branch_id);

CREATE INDEX idx_review_pr_state
    ON review(pull_request_id, review_state);

CREATE INDEX idx_review_pr_reviewer
    ON review(pull_request_id, reviewer_id);

CREATE INDEX idx_status_check_pr_state
    ON status_check(pull_request_id, check_state);

CREATE INDEX idx_review_comment_review_resolved
    ON review_comment(review_id, resolved);

INSERT INTO repository (repository_name)
VALUES ('payments-api');

INSERT INTO app_user (username)
VALUES
    ('atul'),
    ('ravi'),
    ('meera'),
    ('reviewer_a'),
    ('reviewer_b'),
    ('reviewer_c');

INSERT INTO branch (repository_id, branch_name, protected)
SELECT repository_id, 'main', TRUE
FROM repository
WHERE repository_name = 'payments-api';

INSERT INTO branch (repository_id, branch_name, protected)
SELECT repository_id, 'feature/refund', FALSE
FROM repository
WHERE repository_name = 'payments-api';

INSERT INTO branch (repository_id, branch_name, protected)
SELECT repository_id, 'feature/ledger', FALSE
FROM repository
WHERE repository_name = 'payments-api';

INSERT INTO branch (repository_id, branch_name, protected)
SELECT repository_id, 'feature/metrics', FALSE
FROM repository
WHERE repository_name = 'payments-api';

INSERT INTO pull_request (
    repository_id,
    source_branch_id,
    target_branch_id,
    author_id,
    title,
    is_draft,
    state,
    head_commit_sha
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    author.user_id,
    'Implement refund workflow',
    FALSE,
    'OPEN',
    'a1b2c3'
FROM repository r
JOIN branch source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/refund'
JOIN branch target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN app_user author
    ON author.username = 'atul'
WHERE r.repository_name = 'payments-api';

INSERT INTO pull_request (
    repository_id,
    source_branch_id,
    target_branch_id,
    author_id,
    title,
    is_draft,
    state,
    head_commit_sha
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    author.user_id,
    'Improve ledger consistency',
    FALSE,
    'OPEN',
    'd4e5f6'
FROM repository r
JOIN branch source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/ledger'
JOIN branch target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN app_user author
    ON author.username = 'ravi'
WHERE r.repository_name = 'payments-api';

INSERT INTO pull_request (
    repository_id,
    source_branch_id,
    target_branch_id,
    author_id,
    title,
    is_draft,
    state,
    head_commit_sha
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    author.user_id,
    'Add observability metrics',
    TRUE,
    'OPEN',
    'g7h8i9'
FROM repository r
JOIN branch source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/metrics'
JOIN branch target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN app_user author
    ON author.username = 'meera'
WHERE r.repository_name = 'payments-api';

INSERT INTO commit_record (pull_request_id, commit_sha)
SELECT pull_request_id, head_commit_sha
FROM pull_request;

INSERT INTO review (pull_request_id, reviewer_id, review_state)
SELECT pr.pull_request_id, u.user_id, 'APPROVED'
FROM pull_request pr
JOIN app_user u ON u.username = 'reviewer_a'
WHERE pr.pull_request_id = (
    SELECT pull_request_id
    FROM pull_request
    WHERE title = 'Implement refund workflow'
);

INSERT INTO review (pull_request_id, reviewer_id, review_state)
SELECT pr.pull_request_id, u.user_id, 'COMMENTED'
FROM pull_request pr
JOIN app_user u ON u.username = 'reviewer_b'
WHERE pr.pull_request_id = (
    SELECT pull_request_id
    FROM pull_request
    WHERE title = 'Implement refund workflow'
);

INSERT INTO review (pull_request_id, reviewer_id, review_state)
SELECT pr.pull_request_id, u.user_id, 'APPROVED'
FROM pull_request pr
JOIN app_user u ON u.username = 'reviewer_a'
WHERE pr.title = 'Improve ledger consistency';

INSERT INTO review (pull_request_id, reviewer_id, review_state)
SELECT pr.pull_request_id, u.user_id, 'CHANGES_REQUESTED'
FROM pull_request pr
JOIN app_user u ON u.username = 'reviewer_b'
WHERE pr.title = 'Improve ledger consistency';

INSERT INTO review (pull_request_id, reviewer_id, review_state)
SELECT pr.pull_request_id, u.user_id, 'APPROVED'
FROM pull_request pr
JOIN app_user u ON u.username = 'reviewer_c'
WHERE pr.title = 'Add observability metrics';

INSERT INTO status_check (pull_request_id, check_name, check_state)
SELECT pull_request_id, 'unit-tests', 'PASSED'
FROM pull_request
WHERE title = 'Implement refund workflow';

INSERT INTO status_check (pull_request_id, check_name, check_state)
SELECT pull_request_id, 'security-scan', 'PASSED'
FROM pull_request
WHERE title = 'Implement refund workflow';

INSERT INTO status_check (pull_request_id, check_name, check_state)
SELECT pull_request_id, 'integration-tests', 'PASSED'
FROM pull_request
WHERE title = 'Implement refund workflow';

INSERT INTO status_check (pull_request_id, check_name, check_state)
SELECT pull_request_id, 'unit-tests', 'PASSED'
FROM pull_request
WHERE title = 'Improve ledger consistency';

INSERT INTO status_check (pull_request_id, check_name, check_state)
SELECT pull_request_id, 'security-scan', 'FAILED'
FROM pull_request
WHERE title = 'Improve ledger consistency';

INSERT INTO status_check (pull_request_id, check_name, check_state)
SELECT pull_request_id, 'unit-tests', 'PENDING'
FROM pull_request
WHERE title = 'Add observability metrics';

INSERT INTO branch_protection (
    branch_id,
    required_approvals,
    require_status_checks,
    restrict_direct_push,
    restrict_force_push,
    restrict_deletion,
    require_conversation_resolution,
    require_linear_history
)
SELECT
    branch_id,
    1,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE
FROM branch
WHERE branch_name = 'main';

-- A direct parent-to-child join is legitimate when the requested output grain
-- is one row per review. It is not legitimate to assume that the result
-- remains one row per pull request.
SELECT
    pr.pull_request_id,
    pr.title,
    r.review_id,
    r.review_state
FROM pull_request pr
JOIN review r
    ON r.pull_request_id = pr.pull_request_id
ORDER BY pr.pull_request_id, r.review_id;

-- This query demonstrates a many-to-many multiplication effect:
-- PR 101 has two reviews and three checks, producing six combinations.
SELECT
    pr.pull_request_id,
    r.review_id,
    r.review_state,
    sc.check_name,
    sc.check_state
FROM pull_request pr
JOIN review r
    ON r.pull_request_id = pr.pull_request_id
JOIN status_check sc
    ON sc.pull_request_id = pr.pull_request_id
WHERE pr.pull_request_id = (
    SELECT pull_request_id
    FROM pull_request
    WHERE title = 'Implement refund workflow'
)
ORDER BY r.review_id, sc.check_name;

-- The following aggregation exposes the multiplication mathematically.
-- It is diagnostic, not a replacement for a correct query.
SELECT
    pr.pull_request_id,
    COUNT(DISTINCT r.review_id) AS review_count,
    COUNT(DISTINCT sc.status_check_id) AS check_count,
    COUNT(*) AS multiplied_rows,
    COUNT(DISTINCT r.review_id)
        * COUNT(DISTINCT sc.status_check_id) AS expected_multiplication
FROM pull_request pr
LEFT JOIN review r
    ON r.pull_request_id = pr.pull_request_id
LEFT JOIN status_check sc
    ON sc.pull_request_id = pr.pull_request_id
GROUP BY pr.pull_request_id
ORDER BY pr.pull_request_id;

-- A common incorrect predicate joins child records through repository
-- identity. Because many pull requests belong to the same repository,
-- unrelated reviews and checks become associated.
SELECT
    r.review_id,
    r.pull_request_id AS review_pr,
    sc.status_check_id,
    sc.pull_request_id AS check_pr
FROM review r
JOIN pull_request review_pr
    ON review_pr.pull_request_id = r.pull_request_id
JOIN status_check sc
    ON sc.pull_request_id IN (
        SELECT pull_request_id
        FROM pull_request
        WHERE repository_id = review_pr.repository_id
    )
WHERE r.pull_request_id <> sc.pull_request_id
ORDER BY r.review_id, sc.status_check_id;

-- Pre-aggregate each independent one-to-many relationship to PR grain before
-- combining the summaries. This preserves one result row per pull request.
WITH review_summary AS (
    SELECT
        pull_request_id,
        COUNT(*) FILTER (
            WHERE review_state = 'APPROVED'
        ) AS approval_count,
        COUNT(*) FILTER (
            WHERE review_state = 'CHANGES_REQUESTED'
        ) AS changes_requested_count
    FROM review
    GROUP BY pull_request_id
),
check_summary AS (
    SELECT
        pull_request_id,
        COUNT(*) AS total_checks,
        COUNT(*) FILTER (
            WHERE check_state = 'PASSED'
        ) AS passed_checks,
        COUNT(*) FILTER (
            WHERE check_state = 'FAILED'
        ) AS failed_checks,
        COUNT(*) FILTER (
            WHERE check_state = 'PENDING'
        ) AS pending_checks
    FROM status_check
    GROUP BY pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    COALESCE(rs.approval_count, 0) AS approval_count,
    COALESCE(rs.changes_requested_count, 0) AS changes_requested_count,
    COALESCE(cs.total_checks, 0) AS total_checks,
    COALESCE(cs.passed_checks, 0) AS passed_checks,
    COALESCE(cs.failed_checks, 0) AS failed_checks,
    COALESCE(cs.pending_checks, 0) AS pending_checks
FROM pull_request pr
LEFT JOIN review_summary rs
    ON rs.pull_request_id = pr.pull_request_id
LEFT JOIN check_summary cs
    ON cs.pull_request_id = pr.pull_request_id
ORDER BY pr.pull_request_id;

-- Correct LEFT JOIN semantics retain the pull request even when there are
-- no child records. The right-side columns become NULL.
SELECT
    pr.pull_request_id,
    pr.title,
    sc.check_name,
    sc.check_state
FROM pull_request pr
LEFT JOIN status_check sc
    ON sc.pull_request_id = pr.pull_request_id
ORDER BY pr.pull_request_id, sc.check_name;

-- Moving a right-side predicate into WHERE removes NULL-extended rows.
-- This is a frequent reason a LEFT JOIN behaves like an INNER JOIN.
SELECT
    pr.pull_request_id,
    pr.title,
    sc.check_name
FROM pull_request pr
LEFT JOIN status_check sc
    ON sc.pull_request_id = pr.pull_request_id
WHERE sc.check_state = 'PASSED'
ORDER BY pr.pull_request_id;

-- Keeping the predicate in the JOIN condition preserves unmatched PRs.
SELECT
    pr.pull_request_id,
    pr.title,
    sc.check_name,
    sc.check_state
FROM pull_request pr
LEFT JOIN status_check sc
    ON sc.pull_request_id = pr.pull_request_id
   AND sc.check_state = 'PASSED'
ORDER BY pr.pull_request_id;

-- NULL never equals NULL under ordinary SQL equality.
WITH left_data(key_value) AS (
    VALUES
        (NULL::TEXT),
        ('A')
),
right_data(key_value) AS (
    VALUES
        (NULL::TEXT),
        ('A')
)
SELECT
    l.key_value AS left_key,
    r.key_value AS right_key
FROM left_data l
JOIN right_data r
    ON l.key_value = r.key_value;

-- IS NOT DISTINCT FROM deliberately treats NULL as equal to NULL.
WITH left_data(key_value) AS (
    VALUES
        (NULL::TEXT),
        ('A')
),
right_data(key_value) AS (
    VALUES
        (NULL::TEXT),
        ('A')
)
SELECT
    l.key_value AS left_key,
    r.key_value AS right_key
FROM left_data l
JOIN right_data r
    ON l.key_value IS NOT DISTINCT FROM r.key_value;

-- Duplicate business keys can multiply a join even when the columns are
-- technically valid. This diagnostic finds reviewer duplication per PR.
SELECT
    pull_request_id,
    reviewer_id,
    COUNT(*) AS review_rows
FROM review
GROUP BY pull_request_id, reviewer_id
HAVING COUNT(*) > 1;

-- Review-level comments are another one-to-many relationship. Joining
-- comments directly with checks would create another multiplication axis.
SELECT
    pr.pull_request_id,
    COUNT(DISTINCT r.review_id) AS reviews,
    COUNT(DISTINCT rc.review_comment_id) AS comments,
    COUNT(DISTINCT sc.status_check_id) AS checks,
    COUNT(*) AS direct_combination_rows
FROM pull_request pr
LEFT JOIN review r
    ON r.pull_request_id = pr.pull_request_id
LEFT JOIN review_comment rc
    ON rc.review_id = r.review_id
LEFT JOIN status_check sc
    ON sc.pull_request_id = pr.pull_request_id
GROUP BY pr.pull_request_id
ORDER BY pr.pull_request_id;

-- Merge eligibility is evaluated after independent child facts have been
-- reduced to PR grain. This avoids treating the Cartesian multiplication
-- as if it represented independent approvals or checks.
WITH review_summary AS (
    SELECT
        pull_request_id,
        COUNT(DISTINCT reviewer_id) FILTER (
            WHERE review_state = 'APPROVED'
        ) AS distinct_approvers,
        COUNT(*) FILTER (
            WHERE review_state = 'CHANGES_REQUESTED'
        ) AS change_requests
    FROM review
    GROUP BY pull_request_id
),
check_summary AS (
    SELECT
        pull_request_id,
        COUNT(*) AS total_checks,
        COUNT(*) FILTER (
            WHERE check_state = 'FAILED'
        ) AS failed_checks,
        COUNT(*) FILTER (
            WHERE check_state = 'PENDING'
        ) AS pending_checks
    FROM status_check
    GROUP BY pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    COALESCE(rs.distinct_approvers, 0) AS distinct_approvers,
    bp.required_approvals,
    COALESCE(rs.change_requests, 0) AS change_requests,
    COALESCE(cs.total_checks, 0) AS total_checks,
    COALESCE(cs.failed_checks, 0) AS failed_checks,
    COALESCE(cs.pending_checks, 0) AS pending_checks,
    (
        NOT pr.is_draft
        AND pr.state = 'OPEN'
        AND COALESCE(rs.distinct_approvers, 0) >= bp.required_approvals
        AND COALESCE(rs.change_requests, 0) = 0
        AND (
            NOT bp.require_status_checks
            OR (
                COALESCE(cs.total_checks, 0) > 0
                AND COALESCE(cs.failed_checks, 0) = 0
                AND COALESCE(cs.pending_checks, 0) = 0
            )
        )
    ) AS mergeable
FROM pull_request pr
JOIN branch_protection bp
    ON bp.branch_id = pr.target_branch_id
LEFT JOIN review_summary rs
    ON rs.pull_request_id = pr.pull_request_id
LEFT JOIN check_summary cs
    ON cs.pull_request_id = pr.pull_request_id
ORDER BY pr.pull_request_id;

-- A transaction demonstrates that integrity rules belong at the database
-- layer where the relationship itself must remain valid.
BEGIN;

INSERT INTO commit_record (
    pull_request_id,
    commit_sha
)
SELECT pull_request_id, 'new-head-123'
FROM pull_request
WHERE title = 'Implement refund workflow';

UPDATE pull_request
SET head_commit_sha = 'new-head-123'
WHERE title = 'Implement refund workflow';

COMMIT;

-- This query verifies that the latest commit relationship remains attached
-- to the intended pull request rather than another repository record.
SELECT
    pr.pull_request_id,
    pr.title,
    pr.head_commit_sha,
    cr.commit_sha
FROM pull_request pr
JOIN commit_record cr
    ON cr.pull_request_id = pr.pull_request_id
   AND cr.commit_sha = pr.head_commit_sha
ORDER BY pr.pull_request_id;

-- Cardinality checks are useful as automated data-quality assertions.
-- A supposedly one-to-one relationship should not return duplicate parent
-- keys.
SELECT
    pr.pull_request_id,
    COUNT(bp.branch_protection_id) AS protection_rows
FROM pull_request pr
JOIN branch_protection bp
    ON bp.branch_id = pr.target_branch_id
GROUP BY pr.pull_request_id
HAVING COUNT(bp.branch_protection_id) <> 1;

-- This query exposes orphan-like missing child relationships without
-- incorrectly assuming that every child table must contain a row.
SELECT
    pr.pull_request_id,
    pr.title
FROM pull_request pr
LEFT JOIN status_check sc
    ON sc.pull_request_id = pr.pull_request_id
GROUP BY pr.pull_request_id, pr.title
HAVING COUNT(sc.status_check_id) = 0;
