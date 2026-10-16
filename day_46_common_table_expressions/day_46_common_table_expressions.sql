DROP SCHEMA IF EXISTS cte_learning CASCADE;
CREATE SCHEMA cte_learning;
SET search_path TO cte_learning;

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    owner_name TEXT NOT NULL
);

CREATE TABLE branches (
    branch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    branch_name TEXT NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE contributors (
    contributor_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL
);

CREATE TABLE pull_requests (
    pull_request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    source_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    author_id BIGINT NOT NULL REFERENCES contributors(contributor_id),
    title TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('draft', 'open', 'closed', 'merged')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (repository_id, pull_request_id)
);

CREATE TABLE commits (
    commit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id),
    commit_hash TEXT NOT NULL UNIQUE,
    committed_by BIGINT NOT NULL REFERENCES contributors(contributor_id),
    additions INTEGER NOT NULL CHECK (additions >= 0),
    deletions INTEGER NOT NULL CHECK (deletions >= 0),
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reviews (
    review_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id),
    reviewer_id BIGINT NOT NULL REFERENCES contributors(contributor_id),
    review_state TEXT NOT NULL CHECK (
        review_state IN ('commented', 'changes_requested', 'approved', 'dismissed')
    ),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE review_comments (
    comment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(review_id),
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL CHECK (line_number > 0),
    comment_text TEXT NOT NULL,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE status_checks (
    status_check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id),
    check_name TEXT NOT NULL,
    check_state TEXT NOT NULL CHECK (
        check_state IN ('pending', 'passed', 'failed')
    ),
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name)
);

CREATE TABLE branch_protection_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE REFERENCES branches(branch_id),
    required_approvals INTEGER NOT NULL CHECK (required_approvals >= 0),
    require_passing_checks BOOLEAN NOT NULL DEFAULT TRUE,
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT FALSE,
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    allow_force_push BOOLEAN NOT NULL DEFAULT FALSE,
    allow_branch_deletion BOOLEAN NOT NULL DEFAULT FALSE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO repositories (repository_name, owner_name)
VALUES ('analytics-platform', 'engineering');

INSERT INTO branches (repository_id, branch_name, is_default)
SELECT repository_id, 'main', TRUE
FROM repositories
WHERE repository_name = 'analytics-platform';

INSERT INTO branches (repository_id, branch_name)
SELECT repository_id, 'feature/customer-ctes'
FROM repositories
WHERE repository_name = 'analytics-platform';

INSERT INTO branches (repository_id, branch_name)
SELECT repository_id, 'feature/reporting'
FROM repositories
WHERE repository_name = 'analytics-platform';

INSERT INTO contributors (username, display_name)
VALUES
    ('asha', 'Asha Rao'),
    ('ravi', 'Ravi Singh'),
    ('meera', 'Meera Shah'),
    ('kabir', 'Kabir Das');

INSERT INTO branch_protection_policies (
    branch_id,
    required_approvals,
    require_passing_checks,
    require_conversation_resolution,
    restrict_direct_push,
    allow_force_push,
    allow_branch_deletion,
    require_linear_history
)
SELECT
    branch_id,
    2,
    TRUE,
    TRUE,
    TRUE,
    FALSE,
    FALSE,
    TRUE
FROM branches
WHERE branch_name = 'main';

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    author_id,
    title,
    state
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    c.contributor_id,
    'Build customer revenue report with CTEs',
    'open'
FROM repositories r
JOIN branches source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/customer-ctes'
JOIN branches target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN contributors c
    ON c.username = 'asha'
WHERE r.repository_name = 'analytics-platform';

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    author_id,
    title,
    state
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    c.contributor_id,
    'Refactor reporting query',
    'open'
FROM repositories r
JOIN branches source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/reporting'
JOIN branches target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN contributors c
    ON c.username = 'ravi'
WHERE r.repository_name = 'analytics-platform';

INSERT INTO commits (
    pull_request_id,
    commit_hash,
    committed_by,
    additions,
    deletions
)
SELECT
    pr.pull_request_id,
    'abc123customercte',
    c.contributor_id,
    120,
    35
FROM pull_requests pr
JOIN contributors c ON c.username = 'asha'
WHERE pr.title = 'Build customer revenue report with CTEs';

INSERT INTO commits (
    pull_request_id,
    commit_hash,
    committed_by,
    additions,
    deletions
)
SELECT
    pr.pull_request_id,
    'def456reporting',
    c.contributor_id,
    75,
    20
FROM pull_requests pr
JOIN contributors c ON c.username = 'ravi'
WHERE pr.title = 'Refactor reporting query';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state
)
SELECT pr.pull_request_id, c.contributor_id, 'approved'
FROM pull_requests pr
JOIN contributors c ON c.username = 'ravi'
WHERE pr.title = 'Build customer revenue report with CTEs';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state
)
SELECT pr.pull_request_id, c.contributor_id, 'approved'
FROM pull_requests pr
JOIN contributors c ON c.username = 'meera'
WHERE pr.title = 'Build customer revenue report with CTEs';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state
)
SELECT pr.pull_request_id, c.contributor_id, 'changes_requested'
FROM pull_requests pr
JOIN contributors c ON c.username = 'meera'
WHERE pr.title = 'Refactor reporting query';

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    check_state
)
SELECT pr.pull_request_id, 'build', 'passed'
FROM pull_requests pr;

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    check_state
)
SELECT pr.pull_request_id, 'unit-tests', 'passed'
FROM pull_requests pr
WHERE pr.title = 'Build customer revenue report with CTEs';

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    check_state
)
SELECT pr.pull_request_id, 'unit-tests', 'failed'
FROM pull_requests pr
WHERE pr.title = 'Refactor reporting query';

CREATE INDEX idx_pr_target_state
ON pull_requests (target_branch_id, state);

CREATE INDEX idx_reviews_pr_state
ON reviews (pull_request_id, review_state);

CREATE INDEX idx_checks_pr_state
ON status_checks (pull_request_id, check_state);

-- A CTE makes the first relational transformation explicit.
WITH completed_reviews AS (
    SELECT
        pull_request_id,
        reviewer_id,
        submitted_at
    FROM reviews
    WHERE review_state = 'approved'
),
approval_counts AS (
    SELECT
        pull_request_id,
        COUNT(DISTINCT reviewer_id) AS approval_count
    FROM completed_reviews
    GROUP BY pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    COALESCE(ac.approval_count, 0) AS approval_count
FROM pull_requests pr
LEFT JOIN approval_counts ac
    ON ac.pull_request_id = pr.pull_request_id
ORDER BY pr.pull_request_id;

-- Multiple CTEs form a readable relational pipeline.
WITH protected_targets AS (
    SELECT
        pr.pull_request_id,
        pr.title,
        pr.target_branch_id,
        bp.required_approvals,
        bp.require_passing_checks,
        bp.require_conversation_resolution
    FROM pull_requests pr
    JOIN branch_protection_policies bp
        ON bp.branch_id = pr.target_branch_id
    WHERE pr.state = 'open'
),
approval_state AS (
    SELECT
        review.pull_request_id,
        COUNT(DISTINCT review.reviewer_id) FILTER (
            WHERE review.review_state = 'approved'
        ) AS approvals
    FROM reviews review
    GROUP BY review.pull_request_id
),
check_state AS (
    SELECT
        pull_request_id,
        BOOL_AND(check_state = 'passed') AS all_checks_pass
    FROM status_checks
    GROUP BY pull_request_id
),
unresolved_conversations AS (
    SELECT
        review.pull_request_id,
        COUNT(*) FILTER (WHERE comment.is_resolved = FALSE) AS unresolved_count
    FROM reviews review
    JOIN review_comments comment
        ON comment.review_id = review.review_id
    GROUP BY review.pull_request_id
)
SELECT
    pt.pull_request_id,
    pt.title,
    COALESCE(a.approvals, 0) AS approvals,
    COALESCE(cs.all_checks_pass, FALSE) AS checks_pass,
    COALESCE(uc.unresolved_count, 0) AS unresolved_comments,
    (
        COALESCE(a.approvals, 0) >= pt.required_approvals
        AND (
            NOT pt.require_passing_checks
            OR COALESCE(cs.all_checks_pass, FALSE)
        )
        AND (
            NOT pt.require_conversation_resolution
            OR COALESCE(uc.unresolved_count, 0) = 0
        )
    ) AS merge_eligible
FROM protected_targets pt
LEFT JOIN approval_state a
    ON a.pull_request_id = pt.pull_request_id
LEFT JOIN check_state cs
    ON cs.pull_request_id = pt.pull_request_id
LEFT JOIN unresolved_conversations uc
    ON uc.pull_request_id = pt.pull_request_id
ORDER BY pt.pull_request_id;

-- A CTE can isolate aggregation before a ranking operation.
WITH contributor_changes AS (
    SELECT
        c.contributor_id,
        c.username,
        SUM(commits.additions) AS additions,
        SUM(commits.deletions) AS deletions
    FROM commits
    JOIN contributors c
        ON c.contributor_id = commits.committed_by
    GROUP BY c.contributor_id, c.username
)
SELECT
    username,
    additions,
    deletions,
    additions - deletions AS net_change,
    RANK() OVER (ORDER BY additions DESC) AS addition_rank
FROM contributor_changes
ORDER BY addition_rank, username;

-- Recursive CTE: discover a branch hierarchy represented as paths.
CREATE TABLE branch_relationships (
    parent_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    child_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    PRIMARY KEY (parent_branch_id, child_branch_id),
    CHECK (parent_branch_id <> child_branch_id)
);

INSERT INTO branch_relationships
SELECT
    parent.branch_id,
    child.branch_id
FROM branches parent
JOIN branches child
    ON child.branch_name = 'feature/customer-ctes'
WHERE parent.branch_name = 'main';

WITH RECURSIVE branch_tree AS (
    SELECT
        branch_id,
        branch_name,
        0 AS depth,
        branch_name::TEXT AS path
    FROM branches
    WHERE branch_name = 'main'

    UNION ALL

    SELECT
        child.branch_id,
        child.branch_name,
        tree.depth + 1,
        tree.path || ' -> ' || child.branch_name
    FROM branch_tree tree
    JOIN branch_relationships relation
        ON relation.parent_branch_id = tree.branch_id
    JOIN branches child
        ON child.branch_id = relation.child_branch_id
)
SELECT
    branch_name,
    depth,
    path
FROM branch_tree
ORDER BY depth, branch_name;

-- PostgreSQL statement-level CTEs are scoped to the statement in which
-- they occur. The following transaction demonstrates a data correction
-- followed by a query against the corrected relational state.
BEGIN;

WITH failed_checks AS (
    SELECT pull_request_id
    FROM status_checks
    WHERE check_name = 'unit-tests'
      AND check_state = 'failed'
)
UPDATE status_checks
SET check_state = 'passed',
    completed_at = CURRENT_TIMESTAMP
WHERE check_name = 'unit-tests'
  AND pull_request_id IN (SELECT pull_request_id FROM failed_checks);

WITH current_checks AS (
    SELECT
        pull_request_id,
        BOOL_AND(check_state = 'passed') AS checks_pass
    FROM status_checks
    GROUP BY pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    current_checks.checks_pass
FROM pull_requests pr
JOIN current_checks
    ON current_checks.pull_request_id = pr.pull_request_id
ORDER BY pr.pull_request_id;

COMMIT;

-- Data-integrity behavior: negative additions would fail because of the
-- CHECK constraint on commits.additions.
-- Example intentionally omitted as an executable failure so the complete
-- demonstration remains runnable from start to finish.
