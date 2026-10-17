DROP SCHEMA IF EXISTS advanced_aggregation CASCADE;
CREATE SCHEMA advanced_aggregation;
SET search_path TO advanced_aggregation;

CREATE TYPE pull_request_state AS ENUM (
    'draft',
    'open',
    'closed',
    'merged'
);

CREATE TYPE change_category AS ENUM (
    'feature',
    'bugfix',
    'security',
    'performance'
);

CREATE TYPE review_state AS ENUM (
    'commented',
    'changes_requested',
    'approved',
    'dismissed'
);

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    team_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    branch_name TEXT NOT NULL,
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    source_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    category change_category NOT NULL,
    state pull_request_state NOT NULL,
    additions INTEGER NOT NULL CHECK (additions >= 0),
    deletions INTEGER NOT NULL CHECK (deletions >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    merged_at TIMESTAMPTZ,
    CHECK (source_branch_id <> target_branch_id),
    CHECK (
        state <> 'merged'
        OR merged_at IS NOT NULL
    )
);

CREATE TABLE reviewers (
    reviewer_id BIGSERIAL PRIMARY KEY,
    reviewer_name TEXT NOT NULL UNIQUE,
    team_name TEXT NOT NULL
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES reviewers(reviewer_id),
    review_state review_state NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    dismissed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, reviewer_id, submitted_at),
    CHECK (
        review_state <> 'dismissed'
        OR dismissed_at IS NOT NULL
    )
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES reviewers(reviewer_id),
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL CHECK (line_number > 0),
    comment_body TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    UNIQUE (pull_request_id, check_name)
);

CREATE TABLE branch_protection_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    required_approvals INTEGER NOT NULL DEFAULT 1
        CHECK (required_approvals >= 0),
    require_status_checks BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    allow_force_push BOOLEAN NOT NULL DEFAULT FALSE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_pull_requests_repository_state
    ON pull_requests(repository_id, state);

CREATE INDEX idx_pull_requests_category
    ON pull_requests(category);

CREATE INDEX idx_reviews_pull_request_state
    ON reviews(pull_request_id, review_state);

CREATE INDEX idx_status_checks_pull_request
    ON status_checks(pull_request_id);

CREATE INDEX idx_comments_pull_request_resolution
    ON review_comments(pull_request_id, resolved);

INSERT INTO repositories (repository_name, team_name)
VALUES
    ('platform-api', 'Core'),
    ('identity-service', 'Security'),
    ('data-pipeline', 'Data');

INSERT INTO branches (
    repository_id,
    branch_name,
    is_protected
)
SELECT repository_id, 'main', TRUE
FROM repositories;

INSERT INTO branches (
    repository_id,
    branch_name,
    is_protected
)
SELECT repository_id, 'develop', FALSE
FROM repositories;

INSERT INTO reviewers (reviewer_name, team_name)
VALUES
    ('Asha', 'Core'),
    ('Ravi', 'Security'),
    ('Meera', 'Data'),
    ('Vikram', 'Core'),
    ('Neha', 'Security');

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    category,
    state,
    additions,
    deletions,
    created_at,
    merged_at
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    x.category::change_category,
    x.state::pull_request_state,
    x.additions,
    x.deletions,
    x.created_at,
    x.merged_at
FROM (
    VALUES
        ('platform-api', 'feature/auth-cache', 'feature',
         'merged', 420, 90, '2026-10-01 09:00+05:30',
         '2026-10-01 15:00+05:30'),

        ('platform-api', 'bugfix/parser', 'bugfix',
         'merged', 80, 40, '2026-10-02 10:00+05:30',
         '2026-10-02 16:00+05:30'),

        ('identity-service', 'security/token-hardening', 'security',
         'merged', 260, 30, '2026-10-03 09:30+05:30',
         '2026-10-03 14:00+05:30'),

        ('identity-service', 'bugfix/session-timeout', 'bugfix',
         'open', 120, 70, '2026-10-04 11:00+05:30',
         NULL),

        ('data-pipeline', 'feature/batch-loader', 'feature',
         'merged', 760, 210, '2026-10-05 08:00+05:30',
         '2026-10-05 18:00+05:30'),

        ('data-pipeline', 'performance/query-cache', 'performance',
         'merged', 310, 190, '2026-10-06 09:00+05:30',
         '2026-10-06 13:00+05:30'),

        ('platform-api', 'feature/api-v2', 'feature',
         'open', 900, 420, '2026-10-07 10:00+05:30',
         NULL),

        ('identity-service', 'security/audit-events', 'security',
         'merged', 180, 20, '2026-10-08 09:00+05:30',
         '2026-10-08 12:30+05:30'),

        ('data-pipeline', 'bugfix/csv-parser', 'bugfix',
         'closed', 95, 60, '2026-10-09 12:00+05:30',
         NULL),

        ('platform-api', 'performance/cache-index', 'performance',
         'merged', 500, 150, '2026-10-10 08:30+05:30',
         '2026-10-10 12:00+05:30')
) AS x(
    repository_name,
    source_branch_name,
    category,
    state,
    additions,
    deletions,
    created_at,
    merged_at
)
JOIN repositories r
    ON r.repository_name = x.repository_name
JOIN branches source
    ON source.repository_id = r.repository_id
   AND source.branch_name = x.source_branch_name
JOIN branches target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main';

INSERT INTO branch_protection_policies (
    branch_id,
    required_approvals,
    require_status_checks,
    restrict_direct_push,
    allow_force_push,
    require_linear_history,
    require_conversation_resolution
)
SELECT
    branch_id,
    2,
    TRUE,
    TRUE,
    FALSE,
    TRUE,
    TRUE
FROM branches
WHERE branch_name = 'main';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state,
    submitted_at
)
SELECT
    pr.pull_request_id,
    rv.reviewer_id,
    x.review_state::review_state,
    x.submitted_at
FROM (
    VALUES
        (1, 'Asha', 'approved', '2026-10-01 12:00+05:30'),
        (1, 'Vikram', 'approved', '2026-10-01 13:00+05:30'),
        (2, 'Asha', 'approved', '2026-10-02 14:00+05:30'),
        (3, 'Ravi', 'approved', '2026-10-03 11:00+05:30'),
        (3, 'Neha', 'approved', '2026-10-03 11:30+05:30'),
        (3, 'Asha', 'approved', '2026-10-03 12:00+05:30'),
        (4, 'Ravi', 'changes_requested', '2026-10-04 13:00+05:30'),
        (4, 'Neha', 'approved', '2026-10-04 14:00+05:30'),
        (5, 'Meera', 'approved', '2026-10-05 13:00+05:30'),
        (5, 'Asha', 'approved', '2026-10-05 14:00+05:30'),
        (6, 'Meera', 'approved', '2026-10-06 11:00+05:30'),
        (6, 'Asha', 'approved', '2026-10-06 11:30+05:30'),
        (7, 'Asha', 'approved', '2026-10-07 13:00+05:30'),
        (7, 'Vikram', 'approved', '2026-10-07 14:00+05:30'),
        (8, 'Ravi', 'approved', '2026-10-08 10:00+05:30'),
        (8, 'Neha', 'approved', '2026-10-08 10:30+05:30'),
        (8, 'Asha', 'approved', '2026-10-08 11:00+05:30'),
        (9, 'Meera', 'commented', '2026-10-09 13:00+05:30'),
        (10, 'Asha', 'approved', '2026-10-10 10:00+05:30'),
        (10, 'Vikram', 'approved', '2026-10-10 10:30+05:30')
) AS x(
    pull_request_number,
    reviewer_name,
    review_state,
    submitted_at
)
JOIN pull_requests pr
    ON pr.pull_request_id = x.pull_request_number
JOIN reviewers rv
    ON rv.reviewer_name = x.reviewer_name;

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    passed,
    completed_at
)
SELECT
    pr.pull_request_id,
    x.check_name,
    x.passed,
    x.completed_at
FROM (
    VALUES
        (1, 'unit-tests', TRUE, '2026-10-01 13:30+05:30'),
        (1, 'security-scan', TRUE, '2026-10-01 13:40+05:30'),
        (2, 'unit-tests', TRUE, '2026-10-02 15:00+05:30'),
        (3, 'unit-tests', TRUE, '2026-10-03 12:30+05:30'),
        (3, 'security-scan', TRUE, '2026-10-03 12:40+05:30'),
        (4, 'unit-tests', TRUE, '2026-10-04 15:00+05:30'),
        (5, 'unit-tests', TRUE, '2026-10-05 16:00+05:30'),
        (5, 'security-scan', TRUE, '2026-10-05 16:10+05:30'),
        (6, 'unit-tests', TRUE, '2026-10-06 12:00+05:30'),
        (7, 'unit-tests', FALSE, '2026-10-07 15:00+05:30'),
        (8, 'unit-tests', TRUE, '2026-10-08 11:30+05:30'),
        (8, 'security-scan', TRUE, '2026-10-08 11:40+05:30'),
        (9, 'unit-tests', FALSE, '2026-10-09 14:00+05:30'),
        (10, 'unit-tests', TRUE, '2026-10-10 11:00+05:30')
) AS x(
    pull_request_number,
    check_name,
    passed,
    completed_at
)
JOIN pull_requests pr
    ON pr.pull_request_id = x.pull_request_number;

INSERT INTO review_comments (
    pull_request_id,
    reviewer_id,
    file_path,
    line_number,
    comment_body,
    resolved
)
SELECT
    4,
    reviewer_id,
    'src/session/TimeoutService.java',
    87,
    'Validate timeout bounds before persisting the policy.',
    FALSE
FROM reviewers
WHERE reviewer_name = 'Ravi';

CREATE VIEW repository_aggregation AS
SELECT
    r.repository_name,
    COUNT(pr.pull_request_id) AS pull_request_count,
    COUNT(*) FILTER (
        WHERE pr.state = 'merged'
    ) AS merged_count,
    COUNT(*) FILTER (
        WHERE pr.state = 'open'
    ) AS open_count,
    COUNT(*) FILTER (
        WHERE pr.state = 'closed'
    ) AS closed_count,
    SUM(pr.additions + pr.deletions) AS total_changed_lines,
    ROUND(
        AVG(pr.additions + pr.deletions)::numeric,
        2
    ) AS average_changed_lines,
    MIN(pr.additions + pr.deletions) AS minimum_change_size,
    MAX(pr.additions + pr.deletions) AS maximum_change_size,
    COUNT(*) FILTER (
        WHERE pr.additions + pr.deletions >= 500
    ) AS large_change_count
FROM repositories r
LEFT JOIN pull_requests pr
    ON pr.repository_id = r.repository_id
GROUP BY r.repository_id, r.repository_name;

CREATE VIEW repository_review_aggregation AS
SELECT
    r.repository_name,
    COUNT(DISTINCT pr.pull_request_id) AS pull_request_count,
    COUNT(DISTINCT rv.reviewer_id) AS distinct_reviewers,
    COUNT(*) FILTER (
        WHERE rv.review_state = 'approved'
    ) AS approval_events,
    COUNT(*) FILTER (
        WHERE rv.review_state = 'changes_requested'
    ) AS change_request_events,
    COUNT(*) FILTER (
        WHERE rv.review_state = 'dismissed'
    ) AS dismissed_reviews,
    COUNT(DISTINCT rc.comment_id) AS review_comments,
    COUNT(DISTINCT rc.comment_id) FILTER (
        WHERE rc.resolved
    ) AS resolved_comments
FROM repositories r
LEFT JOIN pull_requests pr
    ON pr.repository_id = r.repository_id
LEFT JOIN reviews rv
    ON rv.pull_request_id = pr.pull_request_id
LEFT JOIN review_comments rc
    ON rc.pull_request_id = pr.pull_request_id
GROUP BY r.repository_id, r.repository_name;

SELECT *
FROM repository_aggregation
ORDER BY total_changed_lines DESC;

SELECT
    repository_name,
    pull_request_count,
    merged_count,
    open_count,
    ROUND(
        merged_count::numeric /
        NULLIF(pull_request_count, 0),
        3
    ) AS merge_rate
FROM repository_aggregation
ORDER BY merge_rate DESC;

SELECT
    category,
    COUNT(*) AS pull_request_count,
    COUNT(*) FILTER (
        WHERE state = 'merged'
    ) AS merged_count,
    COUNT(*) FILTER (
        WHERE state = 'open'
    ) AS open_count,
    COUNT(*) FILTER (
        WHERE additions + deletions >= 500
    ) AS large_change_count,
    SUM(additions + deletions) AS total_changed_lines,
    ROUND(
        AVG(additions + deletions)::numeric,
        2
    ) AS average_change_size
FROM pull_requests
GROUP BY category
ORDER BY total_changed_lines DESC;

SELECT
    r.repository_name,
    COUNT(*) AS total_pull_requests,
    COUNT(*) FILTER (
        WHERE pr.category = 'security'
    ) AS security_changes,
    COUNT(*) FILTER (
        WHERE pr.category = 'security'
          AND pr.state = 'merged'
    ) AS merged_security_changes,
    COUNT(*) FILTER (
        WHERE pr.category = 'security'
          AND pr.additions + pr.deletions >= 500
    ) AS large_security_changes,
    COUNT(*) FILTER (
        WHERE pr.category = 'security'
          AND NOT EXISTS (
              SELECT 1
              FROM status_checks sc
              WHERE sc.pull_request_id = pr.pull_request_id
                AND sc.passed = FALSE
          )
    ) AS security_changes_without_failed_checks
FROM repositories r
JOIN pull_requests pr
    ON pr.repository_id = r.repository_id
GROUP BY r.repository_id, r.repository_name
ORDER BY security_changes DESC;

WITH review_counts AS (
    SELECT
        pr.pull_request_id,
        COUNT(*) FILTER (
            WHERE rv.review_state = 'approved'
        ) AS approvals,
        COUNT(*) FILTER (
            WHERE rv.review_state = 'changes_requested'
        ) AS change_requests
    FROM pull_requests pr
    LEFT JOIN reviews rv
        ON rv.pull_request_id = pr.pull_request_id
    GROUP BY pr.pull_request_id
),
check_counts AS (
    SELECT
        pr.pull_request_id,
        COUNT(sc.status_check_id) AS check_count,
        COUNT(*) FILTER (
            WHERE sc.passed
        ) AS passed_checks
    FROM pull_requests pr
    LEFT JOIN status_checks sc
        ON sc.pull_request_id = pr.pull_request_id
    GROUP BY pr.pull_request_id
)
SELECT
    r.repository_name,
    pr.pull_request_id,
    pr.state,
    rc.approvals,
    rc.change_requests,
    cc.check_count,
    cc.passed_checks,
    bp.required_approvals,
    (
        pr.state = 'merged'
        AND rc.approvals >= bp.required_approvals
        AND (
            NOT bp.require_status_checks
            OR cc.check_count > 0
            AND cc.passed_checks = cc.check_count
        )
        AND (
            NOT bp.require_conversation_resolution
            OR NOT EXISTS (
                SELECT 1
                FROM review_comments unresolved
                WHERE unresolved.pull_request_id = pr.pull_request_id
                  AND unresolved.resolved = FALSE
            )
        )
    ) AS satisfies_protection_policy
FROM pull_requests pr
JOIN repositories r
    ON r.repository_id = pr.repository_id
JOIN branches b
    ON b.branch_id = pr.target_branch_id
LEFT JOIN branch_protection_policies bp
    ON bp.branch_id = b.branch_id
JOIN review_counts rc
    ON rc.pull_request_id = pr.pull_request_id
JOIN check_counts cc
    ON cc.pull_request_id = pr.pull_request_id
ORDER BY r.repository_name, pr.pull_request_id;

SELECT
    r.repository_name,
    COUNT(*) AS pull_request_count,
    COUNT(*) FILTER (
        WHERE rv.review_state = 'approved'
    ) AS approval_events,
    COUNT(*) FILTER (
        WHERE rv.review_state = 'changes_requested'
    ) AS requested_change_events,
    COUNT(*) FILTER (
        WHERE rv.review_state = 'dismissed'
    ) AS dismissed_approval_events
FROM repositories r
JOIN pull_requests pr
    ON pr.repository_id = r.repository_id
LEFT JOIN reviews rv
    ON rv.pull_request_id = pr.pull_request_id
GROUP BY r.repository_id, r.repository_name
ORDER BY approval_events DESC;

BEGIN;

UPDATE branch_protection_policies
SET required_approvals = 3
WHERE branch_id = (
    SELECT b.branch_id
    FROM branches b
    JOIN repositories r
        ON r.repository_id = b.repository_id
    WHERE r.repository_name = 'identity-service'
      AND b.branch_name = 'main'
);

SELECT
    r.repository_name,
    bp.required_approvals
FROM branch_protection_policies bp
JOIN branches b
    ON b.branch_id = bp.branch_id
JOIN repositories r
    ON r.repository_id = b.repository_id
WHERE r.repository_name = 'identity-service'
  AND b.branch_name = 'main';

ROLLBACK;

SELECT
    r.repository_name,
    COUNT(*) AS pull_requests,
    COUNT(*) FILTER (
        WHERE pr.state = 'merged'
    ) AS merged,
    COUNT(*) FILTER (
        WHERE pr.state = 'merged'
          AND pr.category = 'security'
    ) AS merged_security,
    SUM(pr.additions) AS additions,
    SUM(pr.deletions) AS deletions,
    SUM(pr.additions + pr.deletions) AS total_changed_lines
FROM repositories r
JOIN pull_requests pr
    ON pr.repository_id = r.repository_id
GROUP BY GROUPING SETS (
    (r.repository_name),
    ()
)
ORDER BY r.repository_name NULLS LAST;

WITH repository_metrics AS (
    SELECT
        r.repository_name,
        COUNT(pr.pull_request_id) AS total_prs,
        COUNT(*) FILTER (
            WHERE pr.state = 'merged'
        ) AS merged_prs,
        COUNT(*) FILTER (
            WHERE pr.additions + pr.deletions >= 500
        ) AS large_prs,
        COUNT(*) FILTER (
            WHERE EXISTS (
                SELECT 1
                FROM status_checks sc
                WHERE sc.pull_request_id = pr.pull_request_id
                  AND sc.passed = FALSE
            )
        ) AS prs_with_failed_checks
    FROM repositories r
    LEFT JOIN pull_requests pr
        ON pr.repository_id = r.repository_id
    GROUP BY r.repository_id, r.repository_name
)
SELECT
    repository_name,
    total_prs,
    merged_prs,
    large_prs,
    prs_with_failed_checks,
    ROUND(
        merged_prs::numeric / NULLIF(total_prs, 0),
        3
    ) AS merge_rate,
    CASE
        WHEN total_prs = 0 THEN 'no activity'
        WHEN merged_prs::numeric / total_prs >= 0.75
             AND prs_with_failed_checks = 0
            THEN 'healthy aggregation profile'
        WHEN prs_with_failed_checks > 0
            THEN 'requires check investigation'
        ELSE 'requires workflow investigation'
    END AS aggregate_health
FROM repository_metrics
ORDER BY
    CASE
        WHEN prs_with_failed_checks > 0 THEN 0
        ELSE 1
    END,
    merge_rate DESC;
