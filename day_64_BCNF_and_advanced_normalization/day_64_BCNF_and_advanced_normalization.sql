DROP SCHEMA IF EXISTS repository_governance CASCADE;
CREATE SCHEMA repository_governance;

SET search_path TO repository_governance;

CREATE TYPE pull_request_state AS ENUM (
    'draft',
    'open',
    'closed',
    'merged'
);

CREATE TYPE review_state AS ENUM (
    'commented',
    'changes_requested',
    'approved',
    'dismissed'
);

CREATE TYPE merge_strategy AS ENUM (
    'merge_commit',
    'squash',
    'rebase'
);

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    name TEXT NOT NULL,
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, name)
);

CREATE TABLE commits (
    commit_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    sha CHAR(40) NOT NULL,
    author_id BIGINT NOT NULL
        REFERENCES users(user_id),
    message TEXT NOT NULL,
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (repository_id, sha)
);

CREATE TABLE branch_commits (
    branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id)
        ON DELETE CASCADE,
    position BIGINT NOT NULL CHECK (position > 0),
    PRIMARY KEY (branch_id, commit_id),
    UNIQUE (branch_id, position)
);

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    number INTEGER NOT NULL CHECK (number > 0),
    source_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    author_id BIGINT NOT NULL
        REFERENCES users(user_id),
    state pull_request_state NOT NULL DEFAULT 'open',
    draft BOOLEAN NOT NULL DEFAULT FALSE,
    merge_strategy merge_strategy NOT NULL DEFAULT 'squash',
    base_sync_required BOOLEAN NOT NULL DEFAULT FALSE,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    merged_at TIMESTAMPTZ,
    UNIQUE (repository_id, number),
    CHECK (source_branch_id <> target_branch_id),
    CHECK (
        state <> 'merged'
        OR merged_at IS NOT NULL
    )
);

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    position BIGINT NOT NULL CHECK (position > 0),
    PRIMARY KEY (pull_request_id, commit_id),
    UNIQUE (pull_request_id, position)
);

CREATE TABLE review_requests (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES users(user_id),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pull_request_id, reviewer_id)
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES users(user_id),
    state review_state NOT NULL,
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL
        REFERENCES reviews(review_id)
        ON DELETE CASCADE,
    body TEXT NOT NULL CHECK (length(trim(body)) > 0),
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversations (
    conversation_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    opened_by_review_id BIGINT
        REFERENCES reviews(review_id),
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    name TEXT NOT NULL,
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    passed BOOLEAN NOT NULL,
    required BOOLEAN NOT NULL DEFAULT TRUE,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE branch_protection_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    required_reviews INTEGER NOT NULL DEFAULT 0
        CHECK (required_reviews >= 0),
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_deletion BOOLEAN NOT NULL DEFAULT TRUE,
    require_conversations_resolved BOOLEAN NOT NULL DEFAULT TRUE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE required_status_checks (
    policy_id BIGINT NOT NULL
        REFERENCES branch_protection_policies(policy_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    PRIMARY KEY (policy_id, check_name)
);

CREATE TABLE merges (
    merge_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL UNIQUE
        REFERENCES pull_requests(pull_request_id)
        ON DELETE RESTRICT,
    merged_by BIGINT NOT NULL
        REFERENCES users(user_id),
    strategy merge_strategy NOT NULL,
    merge_commit_id BIGINT
        REFERENCES commits(commit_id),
    merged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pr_target_state
    ON pull_requests(target_branch_id, state);

CREATE INDEX idx_reviews_pr_state_commit
    ON reviews(pull_request_id, state, commit_id);

CREATE INDEX idx_status_checks_pr_commit
    ON status_checks(pull_request_id, commit_id, name);

CREATE INDEX idx_comments_review_resolved
    ON review_comments(review_id, resolved);

CREATE INDEX idx_conversations_pr_resolved
    ON conversations(pull_request_id, resolved);

CREATE INDEX idx_branch_commits_branch_position
    ON branch_commits(branch_id, position);

CREATE OR REPLACE FUNCTION prevent_self_review()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    pr_author BIGINT;
BEGIN
    SELECT author_id
    INTO pr_author
    FROM pull_requests
    WHERE pull_request_id = NEW.pull_request_id;

    IF NEW.reviewer_id = pr_author THEN
        RAISE EXCEPTION
            'Pull Request authors cannot review their own Pull Request';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_prevent_self_review
BEFORE INSERT OR UPDATE ON reviews
FOR EACH ROW
EXECUTE FUNCTION prevent_self_review();

CREATE OR REPLACE FUNCTION enforce_merge_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.state = 'merged'
       AND OLD.state <> 'merged'
       AND NEW.merged_at IS NULL THEN
        NEW.merged_at := CURRENT_TIMESTAMP;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_merge_timestamp
BEFORE UPDATE ON pull_requests
FOR EACH ROW
EXECUTE FUNCTION enforce_merge_timestamp();

CREATE OR REPLACE FUNCTION get_merge_eligibility(
    p_pull_request_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    failure_reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_target_branch BIGINT;
    v_policy_id BIGINT;
    v_required_reviews INTEGER;
    v_required_conversations BOOLEAN;
    v_linear_history BOOLEAN;
    v_head_commit BIGINT;
    v_state pull_request_state;
    v_draft BOOLEAN;
    v_base_sync_required BOOLEAN;
    v_strategy merge_strategy;
    v_approval_count INTEGER;
BEGIN
    SELECT
        target_branch_id,
        state,
        draft,
        base_sync_required,
        merge_strategy
    INTO
        v_target_branch,
        v_state,
        v_draft,
        v_base_sync_required,
        v_strategy
    FROM pull_requests
    WHERE pull_request_id = p_pull_request_id;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'Pull Request does not exist';
        RETURN;
    END IF;

    SELECT commit_id
    INTO v_head_commit
    FROM pull_request_commits
    WHERE pull_request_id = p_pull_request_id
    ORDER BY position DESC
    LIMIT 1;

    SELECT
        policy_id,
        required_reviews,
        require_conversations_resolved,
        require_linear_history
    INTO
        v_policy_id,
        v_required_reviews,
        v_required_conversations,
        v_linear_history
    FROM branch_protection_policies
    WHERE branch_id = v_target_branch;

    v_required_reviews := COALESCE(v_required_reviews, 0);
    v_required_conversations :=
        COALESCE(v_required_conversations, FALSE);
    v_linear_history :=
        COALESCE(v_linear_history, FALSE);

    IF v_state <> 'open' THEN
        RETURN QUERY
        SELECT FALSE, 'Pull Request is not open';
    END IF;

    IF v_draft THEN
        RETURN QUERY
        SELECT FALSE, 'Pull Request is still a draft';
    END IF;

    IF v_base_sync_required THEN
        RETURN QUERY
        SELECT FALSE, 'Base branch synchronization is required';
    END IF;

    SELECT COUNT(DISTINCT reviewer_id)
    INTO v_approval_count
    FROM reviews
    WHERE pull_request_id = p_pull_request_id
      AND state = 'approved'
      AND commit_id = v_head_commit
      AND reviewer_id <>
          (
              SELECT author_id
              FROM pull_requests
              WHERE pull_request_id = p_pull_request_id
          );

    IF v_approval_count < v_required_reviews THEN
        RETURN QUERY
        SELECT FALSE,
               format(
                   'Required approvals: %s, current approvals: %s',
                   v_required_reviews,
                   v_approval_count
               );
    END IF;

    IF EXISTS (
        SELECT 1
        FROM required_status_checks rsc
        JOIN branch_protection_policies bpp
          ON bpp.policy_id = rsc.policy_id
        WHERE bpp.branch_id = v_target_branch
          AND NOT EXISTS (
              SELECT 1
              FROM status_checks sc
              WHERE sc.pull_request_id = p_pull_request_id
                AND sc.name = rsc.check_name
                AND sc.commit_id = v_head_commit
                AND sc.passed
          )
    ) THEN
        RETURN QUERY
        SELECT FALSE, 'Required status check is missing or failed';
    END IF;

    IF v_required_conversations
       AND EXISTS (
           SELECT 1
           FROM conversations
           WHERE pull_request_id = p_pull_request_id
             AND NOT resolved
       )
    THEN
        RETURN QUERY
        SELECT FALSE, 'Unresolved review conversations remain';
    END IF;

    IF v_linear_history
       AND v_strategy = 'merge_commit'
    THEN
        RETURN QUERY
        SELECT FALSE, 'Merge commits are prohibited';
    END IF;

    RETURN QUERY
    SELECT TRUE, 'All merge conditions satisfied';
END;
$$;

INSERT INTO repositories(name)
VALUES ('payments-platform');

INSERT INTO users(username)
VALUES
    ('alice'),
    ('bob'),
    ('carol'),
    ('diana'),
    ('release-bot');

INSERT INTO branches(repository_id, name, protected)
SELECT repository_id, 'main', TRUE
FROM repositories
WHERE name = 'payments-platform';

INSERT INTO branches(repository_id, name)
SELECT repository_id, 'feature/fraud-rules'
FROM repositories
WHERE name = 'payments-platform';

INSERT INTO commits(repository_id, sha, author_id, message)
SELECT
    r.repository_id,
    repeat('a', 40),
    u.user_id,
    'Initial release'
FROM repositories r
JOIN users u ON u.username = 'alice'
WHERE r.name = 'payments-platform';

INSERT INTO commits(repository_id, sha, author_id, message)
SELECT
    r.repository_id,
    repeat('b', 40),
    u.user_id,
    'Payment API'
FROM repositories r
JOIN users u ON u.username = 'alice'
WHERE r.name = 'payments-platform';

INSERT INTO commits(repository_id, sha, author_id, message)
SELECT
    r.repository_id,
    repeat('c', 40),
    u.user_id,
    'Add fraud rules'
FROM repositories r
JOIN users u ON u.username = 'alice'
WHERE r.name = 'payments-platform';

INSERT INTO commits(repository_id, sha, author_id, message)
SELECT
    r.repository_id,
    repeat('d', 40),
    u.user_id,
    'Validate fraud thresholds'
FROM repositories r
JOIN users u ON u.username = 'alice'
WHERE r.name = 'payments-platform';

INSERT INTO branch_commits(branch_id, commit_id, position)
SELECT
    b.branch_id,
    c.commit_id,
    1
FROM branches b
JOIN commits c
  ON c.sha = repeat('a', 40)
WHERE b.name = 'main';

INSERT INTO branch_commits(branch_id, commit_id, position)
SELECT
    b.branch_id,
    c.commit_id,
    2
FROM branches b
JOIN commits c
  ON c.sha = repeat('b', 40)
WHERE b.name = 'main';

INSERT INTO pull_requests (
    repository_id,
    number,
    source_branch_id,
    target_branch_id,
    author_id,
    state,
    draft,
    merge_strategy
)
SELECT
    r.repository_id,
    1,
    source.branch_id,
    target.branch_id,
    author.user_id,
    'open',
    FALSE,
    'squash'
FROM repositories r
JOIN branches source
  ON source.repository_id = r.repository_id
 AND source.name = 'feature/fraud-rules'
JOIN branches target
  ON target.repository_id = r.repository_id
 AND target.name = 'main'
JOIN users author
  ON author.username = 'alice'
WHERE r.name = 'payments-platform';

INSERT INTO pull_request_commits(
    pull_request_id,
    commit_id,
    position
)
SELECT
    pr.pull_request_id,
    c.commit_id,
    1
FROM pull_requests pr
JOIN commits c
  ON c.sha = repeat('c', 40)
WHERE pr.number = 1;

INSERT INTO pull_request_commits(
    pull_request_id,
    commit_id,
    position
)
SELECT
    pr.pull_request_id,
    c.commit_id,
    2
FROM pull_requests pr
JOIN commits c
  ON c.sha = repeat('d', 40)
WHERE pr.number = 1;

INSERT INTO review_requests(
    pull_request_id,
    reviewer_id
)
SELECT pr.pull_request_id, u.user_id
FROM pull_requests pr
CROSS JOIN users u
WHERE pr.number = 1
  AND u.username IN ('bob', 'carol');

INSERT INTO reviews(
    pull_request_id,
    reviewer_id,
    state,
    commit_id
)
SELECT
    pr.pull_request_id,
    u.user_id,
    'approved',
    c.commit_id
FROM pull_requests pr
JOIN users u
  ON u.username = 'bob'
JOIN commits c
  ON c.sha = repeat('d', 40)
WHERE pr.number = 1;

INSERT INTO reviews(
    pull_request_id,
    reviewer_id,
    state,
    commit_id
)
SELECT
    pr.pull_request_id,
    u.user_id,
    'changes_requested',
    c.commit_id
FROM pull_requests pr
JOIN users u
  ON u.username = 'carol'
JOIN commits c
  ON c.sha = repeat('d', 40)
WHERE pr.number = 1;

INSERT INTO review_comments(review_id, body)
SELECT
    review_id,
    'Reject duplicate fraud threshold definitions'
FROM reviews
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    WHERE number = 1
)
AND reviewer_id = (
    SELECT user_id
    FROM users
    WHERE username = 'carol'
);

INSERT INTO conversations(
    pull_request_id,
    opened_by_review_id,
    resolved
)
SELECT
    pr.pull_request_id,
    r.review_id,
    FALSE
FROM pull_requests pr
JOIN reviews r
  ON r.pull_request_id = pr.pull_request_id
JOIN users u
  ON u.user_id = r.reviewer_id
WHERE pr.number = 1
  AND u.username = 'carol';

INSERT INTO status_checks(
    pull_request_id,
    name,
    commit_id,
    passed
)
SELECT
    pr.pull_request_id,
    checks.name,
    c.commit_id,
    checks.passed
FROM pull_requests pr
JOIN commits c
  ON c.sha = repeat('d', 40)
CROSS JOIN (
    VALUES
        ('unit-tests', TRUE),
        ('security-scan', TRUE)
) AS checks(name, passed)
WHERE pr.number = 1;

INSERT INTO branch_protection_policies(
    branch_id,
    required_reviews,
    restrict_direct_push,
    restrict_force_push,
    restrict_deletion,
    require_conversations_resolved,
    require_linear_history
)
SELECT
    branch_id,
    2,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE
FROM branches
WHERE name = 'main';

INSERT INTO required_status_checks(policy_id, check_name)
SELECT
    policy_id,
    required_check
FROM branch_protection_policies
CROSS JOIN (
    VALUES
        ('unit-tests'),
        ('security-scan')
) AS checks(required_check);

SELECT
    pr.number,
    u.username AS author,
    source.name AS source_branch,
    target.name AS target_branch,
    pr.state,
    pr.draft
FROM pull_requests pr
JOIN users u
  ON u.user_id = pr.author_id
JOIN branches source
  ON source.branch_id = pr.source_branch_id
JOIN branches target
  ON target.branch_id = pr.target_branch_id
ORDER BY pr.number;

SELECT
    pr.number,
    r.reviewer_id,
    u.username AS reviewer,
    r.state,
    c.sha
FROM reviews r
JOIN pull_requests pr
  ON pr.pull_request_id = r.pull_request_id
JOIN users u
  ON u.user_id = r.reviewer_id
JOIN commits c
  ON c.commit_id = r.commit_id
ORDER BY pr.number, r.submitted_at;

SELECT
    pr.number,
    sc.name,
    sc.passed,
    c.sha
FROM status_checks sc
JOIN pull_requests pr
  ON pr.pull_request_id = sc.pull_request_id
JOIN commits c
  ON c.commit_id = sc.commit_id
ORDER BY pr.number, sc.name;

SELECT
    pr.number,
    eligibility.eligible,
    eligibility.failure_reason
FROM pull_requests pr
CROSS JOIN LATERAL get_merge_eligibility(
    pr.pull_request_id
) AS eligibility
ORDER BY pr.number;

SELECT
    target.name AS protected_branch,
    bpp.required_reviews,
    bpp.restrict_direct_push,
    bpp.restrict_force_push,
    bpp.restrict_deletion,
    bpp.require_conversations_resolved,
    bpp.require_linear_history
FROM branch_protection_policies bpp
JOIN branches target
  ON target.branch_id = bpp.branch_id;

WITH review_totals AS (
    SELECT
        pull_request_id,
        COUNT(*) AS total_reviews,
        COUNT(*) FILTER (
            WHERE state = 'approved'
        ) AS approvals,
        COUNT(*) FILTER (
            WHERE state = 'changes_requested'
        ) AS requested_changes
    FROM reviews
    GROUP BY pull_request_id
),
check_totals AS (
    SELECT
        pull_request_id,
        COUNT(*) AS checks,
        COUNT(*) FILTER (
            WHERE passed
        ) AS passed_checks
    FROM status_checks
    GROUP BY pull_request_id
)
SELECT
    pr.number,
    COALESCE(rt.total_reviews, 0) AS total_reviews,
    COALESCE(rt.approvals, 0) AS approvals,
    COALESCE(rt.requested_changes, 0) AS requested_changes,
    COALESCE(ct.checks, 0) AS checks,
    COALESCE(ct.passed_checks, 0) AS passed_checks
FROM pull_requests pr
LEFT JOIN review_totals rt
  ON rt.pull_request_id = pr.pull_request_id
LEFT JOIN check_totals ct
  ON ct.pull_request_id = pr.pull_request_id
ORDER BY pr.number;

BEGIN;

UPDATE conversations
SET
    resolved = TRUE,
    resolved_at = CURRENT_TIMESTAMP
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    WHERE number = 1
)
AND resolved = FALSE;

UPDATE reviews
SET state = 'approved'
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    WHERE number = 1
)
AND reviewer_id = (
    SELECT user_id
    FROM users
    WHERE username = 'carol'
)
AND commit_id = (
    SELECT commit_id
    FROM commits
    WHERE sha = repeat('d', 40)
);

COMMIT;

SELECT
    pr.number,
    eligibility.eligible,
    eligibility.failure_reason
FROM pull_requests pr
CROSS JOIN LATERAL get_merge_eligibility(
    pr.pull_request_id
) AS eligibility
WHERE pr.number = 1;

BEGIN;

DO $$
DECLARE
    v_pr BIGINT;
    v_eligible BOOLEAN;
BEGIN
    SELECT pull_request_id
    INTO v_pr
    FROM pull_requests
    WHERE number = 1
    FOR UPDATE;

    SELECT bool_and(eligible)
    INTO v_eligible
    FROM get_merge_eligibility(v_pr);

    IF NOT COALESCE(v_eligible, FALSE) THEN
        RAISE EXCEPTION
            'Merge transaction rejected by repository policy';
    END IF;

    UPDATE pull_requests
    SET state = 'merged',
        merged_at = CURRENT_TIMESTAMP
    WHERE pull_request_id = v_pr;

    INSERT INTO merges(
        pull_request_id,
        merged_by,
        strategy
    )
    SELECT
        v_pr,
        user_id,
        merge_strategy
    FROM pull_requests
    CROSS JOIN users
    WHERE pull_request_id = v_pr
      AND users.username = 'release-bot';
END;
$$;

COMMIT;
