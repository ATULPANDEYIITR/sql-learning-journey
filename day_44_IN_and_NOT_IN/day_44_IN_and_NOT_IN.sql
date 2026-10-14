-- PostgreSQL-compatible demonstration of:
-- IN, NOT IN, NULL behavior, NULL-safe alternatives, and membership
-- in a repository-governance domain.

DROP SCHEMA IF EXISTS membership_demo CASCADE;
CREATE SCHEMA membership_demo;
SET search_path TO membership_demo;

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    branch_name TEXT NOT NULL,
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE reviewers (
    reviewer_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    source_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    author_reviewer_id BIGINT REFERENCES reviewers(reviewer_id),
    title TEXT NOT NULL,
    is_draft BOOLEAN NOT NULL DEFAULT FALSE,
    is_open BOOLEAN NOT NULL DEFAULT TRUE,
    synchronized_with_base BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (source_branch_id <> target_branch_id)
);

CREATE TABLE commits (
    commit_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id),
    commit_hash TEXT NOT NULL UNIQUE,
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id),
    reviewer_id BIGINT NOT NULL REFERENCES reviewers(reviewer_id),
    review_state TEXT NOT NULL CHECK (
        review_state IN (
            'APPROVED',
            'CHANGES_REQUESTED',
            'COMMENTED',
            'DISMISSED'
        )
    ),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stale BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(review_id),
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL CHECK (line_number > 0),
    comment_body TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id),
    check_name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    required BOOLEAN NOT NULL DEFAULT TRUE,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE branch_protection (
    branch_id BIGINT PRIMARY KEY REFERENCES branches(branch_id),
    required_approvals INTEGER NOT NULL DEFAULT 0 CHECK (required_approvals >= 0),
    require_passing_checks BOOLEAN NOT NULL DEFAULT TRUE,
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT FALSE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    allow_force_push BOOLEAN NOT NULL DEFAULT FALSE,
    allow_deletion BOOLEAN NOT NULL DEFAULT FALSE,
    allow_direct_push BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_pull_requests_target
    ON pull_requests(target_branch_id);

CREATE INDEX idx_reviews_pull_request_state
    ON reviews(pull_request_id, review_state, stale);

CREATE INDEX idx_status_checks_pull_request
    ON status_checks(pull_request_id, required, passed);

INSERT INTO repositories (repository_name)
VALUES ('platform-api');

INSERT INTO reviewers (username)
VALUES
    ('atul'),
    ('security-reviewer'),
    ('platform-reviewer'),
    ('external-contributor'),
    ('release-manager');

INSERT INTO branches (repository_id, branch_name, protected)
SELECT repository_id, 'main', TRUE
FROM repositories
WHERE repository_name = 'platform-api';

INSERT INTO branches (repository_id, branch_name, protected)
SELECT repository_id, 'develop', FALSE
FROM repositories
WHERE repository_name = 'platform-api';

INSERT INTO branches (repository_id, branch_name, protected)
SELECT repository_id, 'feature/security-policy', FALSE
FROM repositories
WHERE repository_name = 'platform-api';

INSERT INTO branch_protection (
    branch_id,
    required_approvals,
    require_passing_checks,
    require_conversation_resolution,
    require_linear_history,
    allow_force_push,
    allow_deletion,
    allow_direct_push
)
SELECT
    branch_id,
    2,
    TRUE,
    TRUE,
    TRUE,
    FALSE,
    FALSE,
    FALSE
FROM branches
WHERE branch_name = 'main';

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    author_reviewer_id,
    title,
    is_draft,
    is_open,
    synchronized_with_base
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    author.reviewer_id,
    'Require security review for sensitive changes',
    FALSE,
    TRUE,
    TRUE
FROM repositories r
JOIN branches source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/security-policy'
JOIN branches target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN reviewers author
    ON author.username = 'atul'
WHERE r.repository_name = 'platform-api';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state,
    stale
)
SELECT
    pr.pull_request_id,
    reviewer.reviewer_id,
    'APPROVED',
    FALSE
FROM pull_requests pr
JOIN reviewers reviewer
    ON reviewer.username = 'security-reviewer';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state,
    stale
)
SELECT
    pr.pull_request_id,
    reviewer.reviewer_id,
    'APPROVED',
    FALSE
FROM pull_requests pr
JOIN reviewers reviewer
    ON reviewer.username = 'platform-reviewer';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state,
    stale
)
SELECT
    pr.pull_request_id,
    reviewer.reviewer_id,
    'APPROVED',
    FALSE
FROM pull_requests pr
JOIN reviewers reviewer
    ON reviewer.username = 'external-contributor';

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    passed,
    required
)
SELECT
    pull_request_id,
    'unit-tests',
    TRUE,
    TRUE
FROM pull_requests;

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    passed,
    required
)
SELECT
    pull_request_id,
    'security-scan',
    TRUE,
    TRUE
FROM pull_requests;

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    passed,
    required
)
SELECT
    pull_request_id,
    'integration-tests',
    FALSE,
    TRUE
FROM pull_requests;

INSERT INTO review_comments (
    review_id,
    file_path,
    line_number,
    comment_body,
    resolved
)
SELECT
    review_id,
    'src/security/policy.py',
    42,
    'Verify that policy evaluation cannot bypass protected branch requirements.',
    FALSE
FROM reviews
WHERE review_state = 'APPROVED'
  AND reviewer_id = (
      SELECT reviewer_id
      FROM reviewers
      WHERE username = 'security-reviewer'
  );

-- Basic IN membership.
SELECT
    username,
    username IN (
        'security-reviewer',
        'platform-reviewer'
    ) AS is_governance_reviewer
FROM reviewers
ORDER BY username;

-- IN with NULL: the result can be UNKNOWN.
SELECT
    username,
    username IN (
        'security-reviewer',
        NULL
    ) AS membership_result
FROM reviewers
ORDER BY username;

-- Demonstrates the NOT IN NULL trap.
-- A non-matching username can become UNKNOWN because the list contains NULL.
SELECT
    username,
    username NOT IN (
        'security-reviewer',
        NULL
    ) AS not_membership_result
FROM reviewers
ORDER BY username;

-- WHERE retains only TRUE, so the NULL-producing rows disappear.
SELECT username
FROM reviewers
WHERE username NOT IN (
    'security-reviewer',
    NULL
)
ORDER BY username;

-- Correct use of NOT IN when the candidate set is guaranteed NOT NULL.
SELECT username
FROM reviewers
WHERE username NOT IN (
    'security-reviewer',
    'platform-reviewer'
)
ORDER BY username;

-- If NULL is possible in a static list and the intended policy is
-- "not equal to any actual value", remove NULL explicitly.
SELECT username
FROM reviewers
WHERE username NOT IN (
    'security-reviewer',
    'platform-reviewer'
)
ORDER BY username;

-- NOT EXISTS is usually the stronger relational alternative when
-- the exclusion set comes from a table.
--
-- This query finds reviewers who are not the author of any open PR.
SELECT reviewer.username
FROM reviewers reviewer
WHERE NOT EXISTS (
    SELECT 1
    FROM pull_requests pr
    WHERE pr.author_reviewer_id = reviewer.reviewer_id
      AND pr.is_open = TRUE
)
ORDER BY reviewer.username;

-- NOT EXISTS remains safe even if a related table contains NULL-capable
-- data, because the subquery asks whether a matching row exists rather
-- than applying NOT to an UNKNOWN membership expression.

-- Find PRs with no blocking review.
SELECT
    pr.pull_request_id,
    pr.title
FROM pull_requests pr
WHERE NOT EXISTS (
    SELECT 1
    FROM reviews rv
    WHERE rv.pull_request_id = pr.pull_request_id
      AND rv.review_state = 'CHANGES_REQUESTED'
      AND rv.stale = FALSE
);

-- Count only eligible approvals.
WITH current_approvals AS (
    SELECT
        rv.pull_request_id,
        COUNT(*) AS approval_count
    FROM reviews rv
    JOIN reviewers r
        ON r.reviewer_id = rv.reviewer_id
    WHERE rv.review_state = 'APPROVED'
      AND rv.stale = FALSE
      AND r.active = TRUE
    GROUP BY rv.pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    COALESCE(ca.approval_count, 0) AS approval_count,
    bp.required_approvals
FROM pull_requests pr
JOIN branch_protection bp
    ON bp.branch_id = pr.target_branch_id
LEFT JOIN current_approvals ca
    ON ca.pull_request_id = pr.pull_request_id;

-- Evaluate required status checks.
SELECT
    pr.pull_request_id,
    pr.title,
    BOOL_AND(sc.passed) FILTER (WHERE sc.required) AS required_checks_pass,
    COUNT(*) FILTER (
        WHERE sc.required AND NOT sc.passed
    ) AS failed_required_checks
FROM pull_requests pr
LEFT JOIN status_checks sc
    ON sc.pull_request_id = pr.pull_request_id
GROUP BY pr.pull_request_id, pr.title;

-- Inline review comments that are still unresolved.
SELECT
    pr.pull_request_id,
    rv.reviewer_id,
    rc.file_path,
    rc.line_number,
    rc.comment_body
FROM pull_requests pr
JOIN reviews rv
    ON rv.pull_request_id = pr.pull_request_id
JOIN review_comments rc
    ON rc.review_id = rv.review_id
WHERE rc.resolved = FALSE
ORDER BY pr.pull_request_id, rc.file_path, rc.line_number;

-- A merge-eligibility view combines Pull Request state, approvals,
-- status checks, synchronization, and branch protection.
CREATE OR REPLACE VIEW merge_eligibility AS
WITH approvals AS (
    SELECT
        rv.pull_request_id,
        COUNT(*) FILTER (
            WHERE rv.review_state = 'APPROVED'
              AND rv.stale = FALSE
              AND reviewer.active = TRUE
        ) AS approval_count
    FROM reviews rv
    JOIN reviewers reviewer
        ON reviewer.reviewer_id = rv.reviewer_id
    GROUP BY rv.pull_request_id
),
checks AS (
    SELECT
        sc.pull_request_id,
        BOOL_AND(sc.passed) FILTER (
            WHERE sc.required
        ) AS required_checks_pass
    FROM status_checks sc
    GROUP BY sc.pull_request_id
),
unresolved AS (
    SELECT
        rv.pull_request_id,
        COUNT(*) AS unresolved_comment_count
    FROM review_comments rc
    JOIN reviews rv
        ON rv.review_id = rc.review_id
    WHERE rc.resolved = FALSE
    GROUP BY rv.pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    pr.is_draft,
    pr.is_open,
    pr.synchronized_with_base,
    COALESCE(a.approval_count, 0) AS approval_count,
    bp.required_approvals,
    COALESCE(c.required_checks_pass, TRUE) AS required_checks_pass,
    COALESCE(u.unresolved_comment_count, 0) AS unresolved_comment_count,
    bp.require_conversation_resolution,
    (
        pr.is_open
        AND NOT pr.is_draft
        AND pr.synchronized_with_base
        AND COALESCE(a.approval_count, 0) >= bp.required_approvals
        AND (
            NOT bp.require_passing_checks
            OR COALESCE(c.required_checks_pass, FALSE)
        )
        AND (
            NOT bp.require_conversation_resolution
            OR COALESCE(u.unresolved_comment_count, 0) = 0
        )
    ) AS merge_eligible
FROM pull_requests pr
JOIN branch_protection bp
    ON bp.branch_id = pr.target_branch_id
LEFT JOIN approvals a
    ON a.pull_request_id = pr.pull_request_id
LEFT JOIN checks c
    ON c.pull_request_id = pr.pull_request_id
LEFT JOIN unresolved u
    ON u.pull_request_id = pr.pull_request_id;

SELECT *
FROM merge_eligibility;

-- Transactional example: a review decision changes state atomically.
BEGIN;

UPDATE reviews
SET review_state = 'CHANGES_REQUESTED'
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    WHERE title = 'Require security review for sensitive changes'
)
AND reviewer_id = (
    SELECT reviewer_id
    FROM reviewers
    WHERE username = 'platform-reviewer'
);

-- The following query observes the state before committing.
SELECT *
FROM merge_eligibility;

ROLLBACK;

-- A NULL-safe comparison can use IS NOT DISTINCT FROM when NULL
-- itself is a meaningful value.
SELECT
    NULL::TEXT IS NOT DISTINCT FROM NULL::TEXT AS null_equals_null,
    'Finance'::TEXT IS NOT DISTINCT FROM NULL::TEXT AS finance_equals_null,
    'Finance'::TEXT IS DISTINCT FROM NULL::TEXT AS finance_distinct_null;

-- COALESCE can be used when business rules explicitly define a NULL
-- fallback, but it should not be used blindly because it changes semantics.
SELECT
    username,
    COALESCE(username, '<unknown-reviewer>') AS display_username
FROM reviewers
ORDER BY username;

-- The central rule demonstrated by this script is:
-- IN asks whether at least one equality comparison is TRUE.
-- NOT IN is logically the negation of that membership result.
-- NULL introduces UNKNOWN into comparisons.
-- WHERE accepts TRUE only.
-- NOT EXISTS expresses relational absence without the same NOT IN NULL trap.
