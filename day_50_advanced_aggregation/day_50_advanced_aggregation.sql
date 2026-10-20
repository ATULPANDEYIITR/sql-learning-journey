DROP SCHEMA IF EXISTS advanced_aggregation CASCADE;
CREATE SCHEMA advanced_aggregation;
SET search_path TO advanced_aggregation;

CREATE TYPE pr_state AS ENUM ('open', 'merged', 'closed');
CREATE TYPE merge_strategy AS ENUM ('merge', 'squash', 'rebase', 'none');
CREATE TYPE review_state AS ENUM ('approved', 'changes_requested', 'commented');

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE
);

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    branch_name TEXT NOT NULL,
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    number INTEGER NOT NULL,
    author_id BIGINT NOT NULL REFERENCES users(user_id),
    source_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    state pr_state NOT NULL,
    additions INTEGER NOT NULL DEFAULT 0 CHECK (additions >= 0),
    deletions INTEGER NOT NULL DEFAULT 0 CHECK (deletions >= 0),
    commit_count INTEGER NOT NULL DEFAULT 0 CHECK (commit_count >= 0),
    merge_strategy merge_strategy NOT NULL DEFAULT 'none',
    opened_at TIMESTAMPTZ NOT NULL,
    merged_at TIMESTAMPTZ,
    UNIQUE (repository_id, number),
    CHECK (
        (state = 'merged' AND merged_at IS NOT NULL)
        OR state <> 'merged'
    ),
    CHECK (
        merged_at IS NULL OR merged_at >= opened_at
    )
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL REFERENCES users(user_id),
    state review_state NOT NULL,
    eligible_reviewer BOOLEAN NOT NULL DEFAULT TRUE,
    dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(review_id)
        ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER CHECK (line_number > 0),
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    body TEXT NOT NULL CHECK (length(trim(body)) > 0)
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name)
);

CREATE TABLE branch_protection (
    branch_id BIGINT PRIMARY KEY REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    required_reviews INTEGER NOT NULL DEFAULT 0 CHECK (required_reviews >= 0),
    require_passing_checks BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_deletion BOOLEAN NOT NULL DEFAULT TRUE,
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT FALSE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    allow_administrator_bypass BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_pr_repository_state
    ON pull_requests(repository_id, state);

CREATE INDEX idx_review_pr_state
    ON reviews(pull_request_id, state);

CREATE INDEX idx_status_check_pr_passed
    ON status_checks(pull_request_id, passed);

CREATE VIEW pull_request_aggregation AS
SELECT
    pr.pull_request_id,
    pr.repository_id,
    r.repository_name,
    pr.number,
    pr.state,
    pr.additions + pr.deletions AS total_changes,
    COUNT(DISTINCT rv.review_id) AS review_count,
    COUNT(DISTINCT rv.review_id) FILTER (
        WHERE rv.state = 'approved'
          AND rv.eligible_reviewer
          AND NOT rv.dismissed
    ) AS active_approval_count,
    COUNT(DISTINCT sc.status_check_id) FILTER (
        WHERE sc.passed
    ) AS passed_check_count,
    COUNT(DISTINCT sc.status_check_id) AS total_check_count,
    COUNT(DISTINCT rc.comment_id) FILTER (
        WHERE NOT rc.resolved
    ) AS unresolved_comments,
    EXTRACT(
        EPOCH FROM (pr.merged_at - pr.opened_at)
    ) / 3600.0 AS cycle_hours
FROM pull_requests pr
JOIN repositories r
  ON r.repository_id = pr.repository_id
LEFT JOIN reviews rv
  ON rv.pull_request_id = pr.pull_request_id
LEFT JOIN review_comments rc
  ON rc.review_id = rv.review_id
LEFT JOIN status_checks sc
  ON sc.pull_request_id = pr.pull_request_id
GROUP BY
    pr.pull_request_id,
    r.repository_name;

INSERT INTO repositories (repository_name)
VALUES ('payments-api'), ('web-portal');

INSERT INTO users (username)
VALUES
    ('alice'),
    ('bob'),
    ('carol'),
    ('david'),
    ('ravi'),
    ('meera'),
    ('sam'),
    ('lee');

INSERT INTO branches (repository_id, branch_name, protected)
SELECT repository_id, 'main', TRUE
FROM repositories;

INSERT INTO branches (repository_id, branch_name, protected)
SELECT repository_id, 'develop', FALSE
FROM repositories
WHERE repository_name = 'web-portal';

INSERT INTO branches (repository_id, branch_name, protected)
SELECT repository_id, 'release', TRUE
FROM repositories
WHERE repository_name = 'payments-api';

INSERT INTO branch_protection (
    branch_id,
    required_reviews,
    require_passing_checks,
    restrict_direct_push,
    restrict_force_push,
    restrict_deletion,
    require_conversation_resolution,
    require_linear_history,
    allow_administrator_bypass
)
SELECT
    b.branch_id,
    CASE WHEN b.branch_name IN ('main', 'release') THEN 2 ELSE 0 END,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    FALSE,
    FALSE
FROM branches b;

INSERT INTO pull_requests (
    repository_id, number, author_id,
    source_branch_id, target_branch_id,
    state, additions, deletions, commit_count,
    merge_strategy, opened_at, merged_at
)
SELECT
    r.repository_id,
    x.number,
    u.user_id,
    sb.branch_id,
    tb.branch_id,
    x.state::pr_state,
    x.additions,
    x.deletions,
    x.commit_count,
    x.merge_strategy::merge_strategy,
    x.opened_at,
    x.merged_at
FROM (
    VALUES
    ('payments-api', 101, 'alice', 'feature/payments-101', 'main',
     'merged', 420, 80, 6, 'squash',
     '2026-10-01 09:00+00', '2026-10-02 14:00+00'),

    ('payments-api', 102, 'bob', 'feature/payments-102', 'main',
     'merged', 90, 20, 3, 'merge',
     '2026-10-02 10:00+00', '2026-10-02 17:00+00'),

    ('payments-api', 103, 'carol', 'feature/payments-103', 'release',
     'closed', 700, 300, 12, 'none',
     '2026-10-03 08:00+00', NULL),

    ('web-portal', 104, 'alice', 'feature/web-104', 'main',
     'merged', 130, 45, 4, 'rebase',
     '2026-10-04 11:00+00', '2026-10-05 10:00+00'),

    ('web-portal', 105, 'david', 'feature/web-105', 'main',
     'open', 35, 8, 2, 'none',
     '2026-10-06 13:00+00', NULL),

    ('web-portal', 106, 'carol', 'feature/web-106', 'develop',
     'merged', 250, 120, 7, 'squash',
     '2026-10-07 09:00+00', '2026-10-08 15:00+00')
) AS x(
    repository_name, number, author,
    source_branch, target_branch,
    state, additions, deletions, commit_count,
    merge_strategy, opened_at, merged_at
)
JOIN repositories r
  ON r.repository_name = x.repository_name
JOIN users u
  ON u.username = x.author
JOIN branches sb
  ON sb.repository_id = r.repository_id
 AND sb.branch_name = x.source_branch
LEFT JOIN branches tb
  ON tb.repository_id = r.repository_id
 AND tb.branch_name = x.target_branch;

-- Feature branches are created only after their PR source references are
-- required, so the source rows must exist before the PR insertion.
-- The following transaction creates the missing feature branches safely.
ROLLBACK;

BEGIN;

INSERT INTO branches (repository_id, branch_name, protected)
SELECT r.repository_id, v.branch_name, FALSE
FROM repositories r
CROSS JOIN (
    VALUES
        ('payments-api', 'feature/payments-101'),
        ('payments-api', 'feature/payments-102'),
        ('payments-api', 'feature/payments-103'),
        ('web-portal', 'feature/web-104'),
        ('web-portal', 'feature/web-105'),
        ('web-portal', 'feature/web-106')
) AS v(repository_name, branch_name)
WHERE r.repository_name = v.repository_name
ON CONFLICT (repository_id, branch_name) DO NOTHING;

INSERT INTO pull_requests (
    repository_id, number, author_id,
    source_branch_id, target_branch_id,
    state, additions, deletions, commit_count,
    merge_strategy, opened_at, merged_at
)
SELECT
    r.repository_id,
    x.number,
    u.user_id,
    sb.branch_id,
    tb.branch_id,
    x.state::pr_state,
    x.additions,
    x.deletions,
    x.commit_count,
    x.merge_strategy::merge_strategy,
    x.opened_at::timestamptz,
    x.merged_at::timestamptz
FROM (
    VALUES
    ('payments-api', 101, 'alice', 'feature/payments-101', 'main',
     'merged', 420, 80, 6, 'squash',
     '2026-10-01 09:00+00', '2026-10-02 14:00+00'),

    ('payments-api', 102, 'bob', 'feature/payments-102', 'main',
     'merged', 90, 20, 3, 'merge',
     '2026-10-02 10:00+00', '2026-10-02 17:00+00'),

    ('payments-api', 103, 'carol', 'feature/payments-103', 'release',
     'closed', 700, 300, 12, 'none',
     '2026-10-03 08:00+00', NULL),

    ('web-portal', 104, 'alice', 'feature/web-104', 'main',
     'merged', 130, 45, 4, 'rebase',
     '2026-10-04 11:00+00', '2026-10-05 10:00+00'),

    ('web-portal', 105, 'david', 'feature/web-105', 'main',
     'open', 35, 8, 2, 'none',
     '2026-10-06 13:00+00', NULL),

    ('web-portal', 106, 'carol', 'feature/web-106', 'develop',
     'merged', 250, 120, 7, 'squash',
     '2026-10-07 09:00+00', '2026-10-08 15:00+00')
) AS x(
    repository_name, number, author,
    source_branch, target_branch,
    state, additions, deletions, commit_count,
    merge_strategy, opened_at, merged_at
)
JOIN repositories r
  ON r.repository_name = x.repository_name
JOIN users u
  ON u.username = x.author
JOIN branches sb
  ON sb.repository_id = r.repository_id
 AND sb.branch_name = x.source_branch
JOIN branches tb
  ON tb.repository_id = r.repository_id
 AND tb.branch_name = x.target_branch;

COMMIT;

INSERT INTO reviews (
    pull_request_id, reviewer_id, state,
    eligible_reviewer, dismissed
)
SELECT
    pr.pull_request_id,
    u.user_id,
    x.state::review_state,
    x.eligible,
    x.dismissed
FROM (
    VALUES
    (101, 'ravi', 'approved', TRUE, FALSE),
    (101, 'meera', 'approved', TRUE, FALSE),
    (101, 'sam', 'commented', TRUE, FALSE),
    (102, 'ravi', 'approved', TRUE, FALSE),
    (102, 'meera', 'commented', TRUE, FALSE),
    (103, 'ravi', 'changes_requested', TRUE, FALSE),
    (103, 'sam', 'commented', TRUE, FALSE),
    (104, 'ravi', 'approved', TRUE, FALSE),
    (104, 'meera', 'approved', TRUE, FALSE),
    (104, 'sam', 'commented', TRUE, FALSE),
    (105, 'ravi', 'commented', TRUE, FALSE),
    (106, 'ravi', 'approved', TRUE, FALSE),
    (106, 'meera', 'approved', TRUE, FALSE),
    (106, 'sam', 'approved', TRUE, FALSE),
    (106, 'lee', 'commented', FALSE, FALSE)
) AS x(pr_number, reviewer, state, eligible, dismissed)
JOIN pull_requests pr
  ON pr.number = x.pr_number
JOIN users u
  ON u.username = x.reviewer;

INSERT INTO review_comments (
    review_id, file_path, line_number, resolved, body
)
SELECT
    rv.review_id,
    'src/payment_service.py',
    42,
    FALSE,
    'Validation does not cover an invalid currency value.'
FROM reviews rv
JOIN pull_requests pr
  ON pr.pull_request_id = rv.pull_request_id
WHERE pr.number = 103
  AND rv.state = 'changes_requested';

INSERT INTO status_checks (
    pull_request_id, check_name, passed, completed_at
)
SELECT
    pr.pull_request_id,
    x.check_name,
    x.passed,
    CURRENT_TIMESTAMP
FROM (
    VALUES
    (101, 'tests', TRUE),
    (101, 'security', TRUE),
    (102, 'tests', TRUE),
    (103, 'tests', FALSE),
    (104, 'tests', TRUE),
    (105, 'tests', TRUE),
    (106, 'tests', TRUE),
    (106, 'lint', TRUE)
) AS x(pr_number, check_name, passed)
JOIN pull_requests pr
  ON pr.number = x.pr_number;

-- Multiple aggregations grouped by repository.
SELECT
    repository_name,
    COUNT(*) AS pull_requests,
    COUNT(*) FILTER (WHERE state = 'merged') AS merged,
    SUM(total_changes) AS total_changes,
    ROUND(AVG(review_count), 2) AS avg_reviews,
    ROUND(AVG(active_approval_count), 2) AS avg_active_approvals,
    ROUND(AVG(cycle_hours) FILTER (WHERE cycle_hours IS NOT NULL), 2)
        AS avg_cycle_hours
FROM pull_request_aggregation
GROUP BY repository_name
ORDER BY repository_name;

-- Conditional aggregation measures governance conditions without
-- materializing separate filtered datasets.
SELECT
    repository_name,
    COUNT(*) AS total_prs,
    COUNT(*) FILTER (WHERE state = 'merged') AS merged_prs,
    COUNT(*) FILTER (
        WHERE total_changes >= 500
    ) AS large_prs,
    COUNT(*) FILTER (
        WHERE active_approval_count >= 2
    ) AS prs_with_two_approvals,
    COUNT(*) FILTER (
        WHERE total_check_count > 0
          AND passed_check_count = total_check_count
    ) AS prs_with_all_checks_passing,
    COUNT(*) FILTER (
        WHERE unresolved_comments = 0
    ) AS prs_with_resolved_discussions
FROM pull_request_aggregation
GROUP BY repository_name;

-- CTE isolates branch-policy evaluation from final aggregation.
WITH policy_evaluation AS (
    SELECT
        p.pull_request_id,
        p.repository_id,
        r.repository_name,
        p.number,
        p.state,
        b.branch_name,
        bp.required_reviews,
        a.active_approval_count,
        a.total_check_count,
        a.passed_check_count,
        a.unresolved_comments,
        bp.require_passing_checks,
        bp.require_conversation_resolution,
        (
            p.state = 'open'
            AND a.active_approval_count >= bp.required_reviews
            AND (
                NOT bp.require_passing_checks
                OR (
                    a.total_check_count > 0
                    AND a.passed_check_count = a.total_check_count
                )
            )
            AND (
                NOT bp.require_conversation_resolution
                OR a.unresolved_comments = 0
            )
        ) AS merge_eligible
    FROM pull_requests p
    JOIN repositories r
      ON r.repository_id = p.repository_id
    JOIN branches b
      ON b.branch_id = p.target_branch_id
    JOIN branch_protection bp
      ON bp.branch_id = b.branch_id
    JOIN pull_request_aggregation a
      ON a.pull_request_id = p.pull_request_id
)
SELECT
    repository_name,
    COUNT(*) AS evaluated_prs,
    COUNT(*) FILTER (WHERE merge_eligible) AS eligible,
    COUNT(*) FILTER (WHERE NOT merge_eligible) AS blocked
FROM policy_evaluation
GROUP BY repository_name
ORDER BY repository_name;

-- Aggregation by merge strategy demonstrates categorical grouping.
SELECT
    merge_strategy,
    COUNT(*) AS merged_prs,
    SUM(additions + deletions) AS total_changes,
    ROUND(AVG(additions + deletions), 2) AS average_changes
FROM pull_requests
WHERE state = 'merged'
GROUP BY merge_strategy
ORDER BY merged_prs DESC;

-- Review-state aggregation separates review activity from approval policy.
SELECT
    rv.state,
    COUNT(*) AS review_count,
    COUNT(*) FILTER (
        WHERE rv.eligible_reviewer AND NOT rv.dismissed
    ) AS active_reviewer_count
FROM reviews rv
GROUP BY rv.state
ORDER BY rv.state;

-- Reviewer-level conditional aggregation identifies approval behavior.
SELECT
    u.username,
    COUNT(*) AS reviews_submitted,
    COUNT(*) FILTER (
        WHERE rv.state = 'approved'
          AND rv.eligible_reviewer
          AND NOT rv.dismissed
    ) AS active_approvals,
    COUNT(*) FILTER (
        WHERE rv.state = 'changes_requested'
    ) AS change_requests
FROM users u
JOIN reviews rv
  ON rv.reviewer_id = u.user_id
GROUP BY u.username
ORDER BY active_approvals DESC, u.username;

-- Transactional validation: this statement intentionally fails because
-- an approval requirement cannot be negative. PostgreSQL rolls it back
-- without corrupting existing governance data.
BEGIN;
UPDATE branch_protection
SET required_reviews = -1
WHERE branch_id = (
    SELECT b.branch_id
    FROM branches b
    JOIN repositories r
      ON r.repository_id = b.repository_id
    WHERE r.repository_name = 'payments-api'
      AND b.branch_name = 'main'
);
ROLLBACK;
