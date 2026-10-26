DROP SCHEMA IF EXISTS lag_lead_lab CASCADE;
CREATE SCHEMA lag_lead_lab;

SET search_path TO lag_lead_lab;

-- ============================================================
-- Domain model
-- ============================================================

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    default_branch TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(repository_name)) >= 2),
    CHECK (length(trim(default_branch)) >= 1)
);

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    role_name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (username ~ '^[A-Za-z0-9_.-]{2,50}$')
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id) ON DELETE CASCADE,
    branch_name TEXT NOT NULL,
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE commits (
    commit_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id) ON DELETE CASCADE,
    branch_id BIGINT NOT NULL REFERENCES branches(branch_id) ON DELETE CASCADE,
    commit_hash TEXT NOT NULL UNIQUE,
    committed_at TIMESTAMPTZ NOT NULL,
    author_id BIGINT NOT NULL REFERENCES users(user_id),
    CHECK (commit_hash ~ '^[0-9a-f]{7,64}$')
);

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id) ON DELETE CASCADE,
    source_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    title TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'OPEN',
    is_draft BOOLEAN NOT NULL DEFAULT FALSE,
    merge_conflict BOOLEAN NOT NULL DEFAULT FALSE,
    created_by BIGINT NOT NULL REFERENCES users(user_id),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    merged_at TIMESTAMPTZ,
    CHECK (state IN ('OPEN', 'CLOSED', 'MERGED')),
    CHECK (length(trim(title)) >= 3),
    CHECK (source_branch_id <> target_branch_id),
    CHECK (
        (state = 'MERGED' AND merged_at IS NOT NULL)
        OR state <> 'MERGED'
    )
);

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    commit_id BIGINT NOT NULL REFERENCES commits(commit_id) ON DELETE RESTRICT,
    commit_position INTEGER NOT NULL,
    PRIMARY KEY (pull_request_id, commit_id),
    UNIQUE (pull_request_id, commit_position),
    CHECK (commit_position > 0)
);

CREATE TABLE reviewers (
    reviewer_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    eligible BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (repository_id, user_id)
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL REFERENCES reviewers(reviewer_id),
    state TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dismissed_at TIMESTAMPTZ,
    CHECK (state IN ('PENDING', 'APPROVED', 'CHANGES_REQUESTED', 'DISMISSED')),
    CHECK (
        (state = 'DISMISSED' AND dismissed_at IS NOT NULL)
        OR state <> 'DISMISSED'
    )
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    body TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (line_number IS NULL OR line_number > 0),
    CHECK (length(trim(body)) > 0)
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name),
    CHECK (status IN ('PENDING', 'PASSING', 'FAILING', 'CANCELLED'))
);

CREATE TABLE branch_protection_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE REFERENCES branches(branch_id) ON DELETE CASCADE,
    required_approvals INTEGER NOT NULL DEFAULT 0,
    require_passing_checks BOOLEAN NOT NULL DEFAULT TRUE,
    require_resolved_conversations BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_deletion BOOLEAN NOT NULL DEFAULT TRUE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    allow_administrator_bypass BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (required_approvals >= 0)
);

CREATE TABLE approval_requirements (
    requirement_id BIGSERIAL PRIMARY KEY,
    policy_id BIGINT NOT NULL REFERENCES branch_protection_policies(policy_id) ON DELETE CASCADE,
    required_role TEXT,
    required_approvals INTEGER NOT NULL,
    CHECK (required_approvals > 0)
);

CREATE INDEX idx_commits_branch_time
    ON commits(branch_id, committed_at DESC);

CREATE INDEX idx_reviews_pr_state
    ON reviews(pull_request_id, state);

CREATE INDEX idx_status_checks_pr_status
    ON status_checks(pull_request_id, status);

CREATE INDEX idx_review_comments_review_resolved
    ON review_comments(review_id, resolved);

-- ============================================================
-- Trigger: source and target branches must belong to the same
-- repository as the Pull Request.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_pull_request_repository()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    source_repository BIGINT;
    target_repository BIGINT;
BEGIN
    SELECT repository_id
    INTO source_repository
    FROM branches
    WHERE branch_id = NEW.source_branch_id;

    SELECT repository_id
    INTO target_repository
    FROM branches
    WHERE branch_id = NEW.target_branch_id;

    IF source_repository IS NULL
       OR target_repository IS NULL
       OR source_repository <> NEW.repository_id
       OR target_repository <> NEW.repository_id THEN
        RAISE EXCEPTION
            'Pull Request branches must belong to its repository';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_pull_request_repository
BEFORE INSERT OR UPDATE ON pull_requests
FOR EACH ROW
EXECUTE FUNCTION validate_pull_request_repository();

-- ============================================================
-- Sample repository and users
-- ============================================================

INSERT INTO repositories(repository_name, default_branch)
VALUES ('revenue-platform', 'main');

INSERT INTO users(username, role_name)
VALUES
    ('alice', 'maintainer'),
    ('bob', 'developer'),
    ('carol', 'security'),
    ('dave', 'developer'),
    ('contractor', 'external');

INSERT INTO branches(repository_id, branch_name, is_protected)
SELECT repository_id, branch_name, protected
FROM repositories
CROSS JOIN (
    VALUES
        ('main', TRUE),
        ('develop', FALSE),
        ('feature/revenue-model', FALSE)
) AS b(branch_name, protected);

INSERT INTO commits(
    repository_id,
    branch_id,
    commit_hash,
    committed_at,
    author_id
)
SELECT
    r.repository_id,
    b.branch_id,
    x.commit_hash,
    x.committed_at,
    u.user_id
FROM repositories r
JOIN branches b
    ON b.repository_id = r.repository_id
CROSS JOIN (
    VALUES
        ('a1b2c3d', TIMESTAMPTZ '2026-10-20 09:00:00+05:30'),
        ('d4e5f6a', TIMESTAMPTZ '2026-10-21 10:00:00+05:30'),
        ('b7c8d9e', TIMESTAMPTZ '2026-10-22 11:00:00+05:30')
) AS x(commit_hash, committed_at)
JOIN users u ON u.username = 'bob'
WHERE b.branch_name = 'feature/revenue-model';

INSERT INTO pull_requests(
    repository_id,
    source_branch_id,
    target_branch_id,
    title,
    created_by
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    'Improve revenue time-series reporting',
    u.user_id
FROM repositories r
JOIN branches source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/revenue-model'
JOIN branches target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN users u ON u.username = 'bob';

INSERT INTO pull_request_commits(pull_request_id, commit_id, commit_position)
SELECT pr.pull_request_id, c.commit_id,
       row_number() OVER (ORDER BY c.committed_at)
FROM pull_requests pr
JOIN commits c
    ON c.repository_id = pr.repository_id
WHERE pr.title = 'Improve revenue time-series reporting';

INSERT INTO reviewers(repository_id, user_id, eligible)
SELECT r.repository_id, u.user_id, u.username <> 'contractor'
FROM repositories r
CROSS JOIN users u
WHERE u.username IN ('alice', 'bob', 'carol', 'contractor');

INSERT INTO reviews(pull_request_id, reviewer_id, state)
SELECT
    pr.pull_request_id,
    rv.reviewer_id,
    x.state
FROM pull_requests pr
JOIN reviewers rv
    ON rv.repository_id = pr.repository_id
JOIN users u
    ON u.user_id = rv.user_id
JOIN (
    VALUES
        ('alice', 'APPROVED'),
        ('carol', 'APPROVED'),
        ('contractor', 'APPROVED')
) AS x(username, state)
    ON x.username = u.username;

INSERT INTO review_comments(review_id, file_path, line_number, body, resolved)
SELECT
    review_id,
    'src/revenue.py',
    42,
    'Validate zero-value periods before calculating percentage change.',
    TRUE
FROM reviews
WHERE state = 'APPROVED'
LIMIT 1;

INSERT INTO status_checks(
    pull_request_id,
    check_name,
    status,
    completed_at
)
SELECT
    pull_request_id,
    x.check_name,
    x.status,
    CASE
        WHEN x.status IN ('PASSING', 'FAILING')
        THEN CURRENT_TIMESTAMP
        ELSE NULL
    END
FROM pull_requests
CROSS JOIN (
    VALUES
        ('unit-tests', 'PASSING'),
        ('integration-tests', 'PASSING'),
        ('security-scan', 'PASSING')
) AS x(check_name, status);

INSERT INTO branch_protection_policies(
    branch_id,
    required_approvals,
    require_passing_checks,
    require_resolved_conversations,
    restrict_direct_push,
    restrict_force_push,
    restrict_deletion,
    require_linear_history,
    allow_administrator_bypass
)
SELECT
    b.branch_id,
    2,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    FALSE
FROM branches b
WHERE b.branch_name = 'main';

INSERT INTO approval_requirements(policy_id, required_role, required_approvals)
SELECT policy_id, 'maintainer', 1
FROM branch_protection_policies;

-- ============================================================
-- Time-series example specifically for LAG/LEAD analysis.
-- ============================================================

CREATE TABLE daily_metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    metric_date DATE NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC(14,2) NOT NULL,
    UNIQUE(repository_id, metric_date, metric_name)
);

INSERT INTO daily_metrics(repository_id, metric_date, metric_name, metric_value)
SELECT
    repository_id,
    x.metric_date,
    'daily_revenue',
    x.metric_value
FROM repositories
CROSS JOIN (
    VALUES
        (DATE '2026-10-19', 120.00),
        (DATE '2026-10-20', 126.00),
        (DATE '2026-10-21', 131.00),
        (DATE '2026-10-22', 127.00),
        (DATE '2026-10-23', 135.00),
        (DATE '2026-10-24', 135.00),
        (DATE '2026-10-25', 142.00)
) AS x(metric_date, metric_value)
WHERE repository_id = 1;

-- Previous-row and next-row analysis.
SELECT
    metric_date,
    metric_value,
    LAG(metric_value) OVER (
        PARTITION BY repository_id, metric_name
        ORDER BY metric_date
    ) AS previous_value,
    LEAD(metric_value) OVER (
        PARTITION BY repository_id, metric_name
        ORDER BY metric_date
    ) AS next_value
FROM daily_metrics
ORDER BY metric_date;

-- Difference from the previous observation.
SELECT
    metric_date,
    metric_value,
    metric_value
        - LAG(metric_value) OVER (
            PARTITION BY repository_id, metric_name
            ORDER BY metric_date
        ) AS change_from_previous
FROM daily_metrics
ORDER BY metric_date;

-- Forward difference using LEAD.
SELECT
    metric_date,
    metric_value,
    LEAD(metric_value) OVER (
        PARTITION BY repository_id, metric_name
        ORDER BY metric_date
    ) - metric_value AS change_to_next
FROM daily_metrics
ORDER BY metric_date;

-- Percentage comparison with zero-division protection.
SELECT
    metric_date,
    metric_value,
    ROUND(
        (
            (metric_value - LAG(metric_value) OVER (
                PARTITION BY repository_id, metric_name
                ORDER BY metric_date
            ))
            /
            NULLIF(
                LAG(metric_value) OVER (
                    PARTITION BY repository_id, metric_name
                    ORDER BY metric_date
                ),
                0
            )
        ) * 100,
        2
    ) AS percentage_change
FROM daily_metrics
ORDER BY metric_date;

-- Identify local peaks using both neighboring rows.
WITH neighbors AS (
    SELECT
        metric_date,
        metric_value,
        LAG(metric_value) OVER (
            PARTITION BY repository_id, metric_name
            ORDER BY metric_date
        ) AS previous_value,
        LEAD(metric_value) OVER (
            PARTITION BY repository_id, metric_name
            ORDER BY metric_date
        ) AS next_value
    FROM daily_metrics
)
SELECT *
FROM neighbors
WHERE previous_value IS NOT NULL
  AND next_value IS NOT NULL
  AND metric_value > previous_value
  AND metric_value > next_value
ORDER BY metric_date;

-- ============================================================
-- Merge eligibility view.
-- ============================================================

CREATE OR REPLACE VIEW merge_eligibility AS
WITH approval_counts AS (
    SELECT
        r.pull_request_id,
        COUNT(*) FILTER (
            WHERE r.state = 'APPROVED'
              AND rv.eligible = TRUE
        ) AS eligible_approvals
    FROM reviews r
    JOIN reviewers rv
      ON rv.reviewer_id = r.reviewer_id
    GROUP BY r.pull_request_id
),
check_results AS (
    SELECT
        pull_request_id,
        COUNT(*) AS total_checks,
        COUNT(*) FILTER (WHERE status = 'PASSING') AS passing_checks,
        COUNT(*) FILTER (WHERE status = 'FAILING') AS failing_checks
    FROM status_checks
    GROUP BY pull_request_id
),
unresolved AS (
    SELECT
        r.pull_request_id,
        COUNT(*) FILTER (WHERE rc.resolved = FALSE) AS unresolved_comments
    FROM reviews r
    LEFT JOIN review_comments rc
      ON rc.review_id = r.review_id
    GROUP BY r.pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    b.branch_name AS target_branch,
    p.required_approvals,
    COALESCE(a.eligible_approvals, 0) AS eligible_approvals,
    COALESCE(c.total_checks, 0) AS total_checks,
    COALESCE(c.passing_checks, 0) AS passing_checks,
    COALESCE(c.failing_checks, 0) AS failing_checks,
    COALESCE(u.unresolved_comments, 0) AS unresolved_comments,
    pr.merge_conflict,
    pr.is_draft,
    (
        pr.state = 'OPEN'
        AND NOT pr.is_draft
        AND NOT pr.merge_conflict
        AND COALESCE(a.eligible_approvals, 0) >= p.required_approvals
        AND (
            NOT p.require_passing_checks
            OR (
                COALESCE(c.total_checks, 0) > 0
                AND COALESCE(c.failing_checks, 0) = 0
                AND COALESCE(c.passing_checks, 0) = COALESCE(c.total_checks, 0)
            )
        )
        AND (
            NOT p.require_resolved_conversations
            OR COALESCE(u.unresolved_comments, 0) = 0
        )
    ) AS merge_eligible
FROM pull_requests pr
JOIN branches b
  ON b.branch_id = pr.target_branch_id
JOIN branch_protection_policies p
  ON p.branch_id = b.branch_id
LEFT JOIN approval_counts a
  ON a.pull_request_id = pr.pull_request_id
LEFT JOIN check_results c
  ON c.pull_request_id = pr.pull_request_id
LEFT JOIN unresolved u
  ON u.pull_request_id = pr.pull_request_id;

SELECT *
FROM merge_eligibility;

-- ============================================================
-- Transactional example: approve a review and verify eligibility.
-- ============================================================

BEGIN;

UPDATE reviews
SET state = 'APPROVED',
    dismissed_at = NULL
WHERE pull_request_id = 1
  AND reviewer_id = (
      SELECT rv.reviewer_id
      FROM reviewers rv
      JOIN users u ON u.user_id = rv.user_id
      WHERE u.username = 'alice'
  );

SELECT *
FROM merge_eligibility
WHERE pull_request_id = 1;

COMMIT;
