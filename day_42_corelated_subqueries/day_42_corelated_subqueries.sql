DROP SCHEMA IF EXISTS correlated_governance CASCADE;
CREATE SCHEMA correlated_governance;
SET search_path TO correlated_governance;

-- The schema models repository governance while using correlated subqueries
-- as the primary query mechanism for evaluating each Pull Request in the
-- context of its related reviews, comments, commits, checks, and policy.

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    owner_name TEXT NOT NULL
);

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    reviewer_eligible BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),
    branch_name TEXT NOT NULL,
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    author_id BIGINT NOT NULL
        REFERENCES users(user_id),
    source_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    state TEXT NOT NULL
        CHECK (state IN ('OPEN', 'CLOSED', 'MERGED')),
    is_draft BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    merged_at TIMESTAMPTZ,
    UNIQUE (repository_id, number),
    CHECK (source_branch_id <> target_branch_id)
);

CREATE TABLE commits (
    commit_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    commit_sha CHAR(40) NOT NULL UNIQUE,
    committed_by BIGINT NOT NULL
        REFERENCES users(user_id),
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES users(user_id),
    review_state TEXT NOT NULL
        CHECK (
            review_state IN (
                'APPROVED',
                'COMMENTED',
                'CHANGES_REQUESTED',
                'DISMISSED'
            )
        ),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES users(user_id),
    body TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    check_state TEXT NOT NULL
        CHECK (check_state IN ('SUCCESS', 'FAILURE', 'PENDING')),
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name)
);

CREATE TABLE branch_protection_policies (
    branch_id BIGINT PRIMARY KEY
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    required_approvals INTEGER NOT NULL DEFAULT 0
        CHECK (required_approvals >= 0),
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT TRUE,
    allow_force_push BOOLEAN NOT NULL DEFAULT FALSE,
    allow_deletion BOOLEAN NOT NULL DEFAULT FALSE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE required_status_checks (
    branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    PRIMARY KEY (branch_id, check_name)
);

CREATE INDEX idx_reviews_pull_request
    ON reviews (pull_request_id);

CREATE INDEX idx_comments_pull_request
    ON review_comments (pull_request_id);

CREATE INDEX idx_checks_pull_request
    ON status_checks (pull_request_id);

CREATE INDEX idx_commits_pull_request
    ON commits (pull_request_id);

CREATE INDEX idx_pull_requests_target_branch
    ON pull_requests (target_branch_id);

INSERT INTO repositories (repository_name, owner_name)
VALUES ('payments-service', 'platform-team');

INSERT INTO users (username, active, reviewer_eligible)
VALUES
    ('alice', TRUE, TRUE),
    ('bob', TRUE, FALSE),
    ('carol', TRUE, TRUE),
    ('david', TRUE, FALSE);

INSERT INTO branches (
    repository_id,
    branch_name,
    is_protected
)
SELECT
    repository_id,
    branch_name,
    branch_name = 'main'
FROM repositories
CROSS JOIN (
    VALUES
        ('main'),
        ('feature/reconciliation'),
        ('fix/payment-timeout'),
        ('refactor/settlement')
) AS branch_names(branch_name);

INSERT INTO branch_protection_policies (
    branch_id,
    required_approvals,
    require_conversation_resolution,
    allow_force_push,
    allow_deletion,
    require_linear_history
)
SELECT
    b.branch_id,
    1,
    TRUE,
    FALSE,
    FALSE,
    TRUE
FROM branches AS b
JOIN repositories AS r
    ON r.repository_id = b.repository_id
WHERE r.repository_name = 'payments-service'
  AND b.branch_name = 'main';

INSERT INTO required_status_checks (branch_id, check_name)
SELECT
    b.branch_id,
    checks.check_name
FROM branches AS b
JOIN repositories AS r
    ON r.repository_id = b.repository_id
CROSS JOIN (
    VALUES ('unit-tests'), ('security-scan')
) AS checks(check_name)
WHERE r.repository_name = 'payments-service'
  AND b.branch_name = 'main';

INSERT INTO pull_requests (
    repository_id,
    number,
    title,
    author_id,
    source_branch_id,
    target_branch_id,
    state,
    is_draft
)
SELECT
    r.repository_id,
    source.number,
    source.title,
    u.user_id,
    source_branch.branch_id,
    target_branch.branch_id,
    'OPEN',
    source.is_draft
FROM repositories AS r
JOIN (
    VALUES
        (
            41,
            'Add transaction reconciliation',
            'david',
            'feature/reconciliation',
            'main',
            FALSE
        ),
        (
            42,
            'Improve payment timeout handling',
            'alice',
            'fix/payment-timeout',
            'main',
            FALSE
        ),
        (
            43,
            'Refactor settlement validation',
            'bob',
            'refactor/settlement',
            'main',
            TRUE
        )
) AS source(
    number,
    title,
    author,
    source_branch,
    target_branch,
    is_draft
)
    ON TRUE
JOIN users AS u
    ON u.username = source.author
JOIN branches AS source_branch
    ON source_branch.repository_id = r.repository_id
   AND source_branch.branch_name = source.source_branch
JOIN branches AS target_branch
    ON target_branch.repository_id = r.repository_id
   AND target_branch.branch_name = source.target_branch
WHERE r.repository_name = 'payments-service';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state
)
SELECT
    pr.pull_request_id,
    u.user_id,
    source.review_state
FROM (
    VALUES
        (41, 'alice', 'APPROVED'),
        (41, 'bob', 'COMMENTED'),
        (42, 'carol', 'APPROVED'),
        (43, 'alice', 'CHANGES_REQUESTED')
) AS source(pr_number, reviewer, review_state)
JOIN pull_requests AS pr
    ON pr.number = source.pr_number
JOIN users AS u
    ON u.username = source.reviewer;

INSERT INTO review_comments (
    pull_request_id,
    reviewer_id,
    body,
    resolved
)
SELECT
    pr.pull_request_id,
    u.user_id,
    source.body,
    source.resolved
FROM (
    VALUES
        (
            41,
            'bob',
            'Document the reconciliation fallback.',
            FALSE
        ),
        (
            42,
            'carol',
            'Timeout handling looks correct.',
            TRUE
        )
) AS source(pr_number, reviewer, body, resolved)
JOIN pull_requests AS pr
    ON pr.number = source.pr_number
JOIN users AS u
    ON u.username = source.reviewer;

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    check_state
)
SELECT
    pr.pull_request_id,
    source.check_name,
    source.check_state
FROM (
    VALUES
        (41, 'unit-tests', 'SUCCESS'),
        (41, 'security-scan', 'SUCCESS'),
        (42, 'unit-tests', 'SUCCESS'),
        (42, 'security-scan', 'FAILURE')
) AS source(pr_number, check_name, check_state)
JOIN pull_requests AS pr
    ON pr.number = source.pr_number;

INSERT INTO commits (
    pull_request_id,
    commit_sha,
    committed_by
)
SELECT
    pr.pull_request_id,
    source.commit_sha,
    u.user_id
FROM (
    VALUES
        (41, '1111111111111111111111111111111111111111', 'david'),
        (42, '2222222222222222222222222222222222222222', 'alice'),
        (43, '3333333333333333333333333333333333333333', 'bob')
) AS source(pr_number, commit_sha, author)
JOIN pull_requests AS pr
    ON pr.number = source.pr_number
JOIN users AS u
    ON u.username = source.author;


-- Correlated EXISTS:
-- Find Pull Requests for which the current PR has at least one approval.

SELECT
    pr.number,
    pr.title
FROM pull_requests AS pr
WHERE EXISTS (
    SELECT 1
    FROM reviews AS r
    WHERE r.pull_request_id = pr.pull_request_id
      AND r.review_state = 'APPROVED'
);


-- Correlated NOT EXISTS:
-- Find Pull Requests with no unresolved review conversation.

SELECT
    pr.number,
    pr.title
FROM pull_requests AS pr
WHERE NOT EXISTS (
    SELECT 1
    FROM review_comments AS c
    WHERE c.pull_request_id = pr.pull_request_id
      AND c.resolved = FALSE
);


-- Correlated scalar aggregate:
-- COUNT(*) is evaluated separately in the logical context of each PR.

SELECT
    pr.number,
    pr.title,
    (
        SELECT COUNT(*)
        FROM reviews AS r
        WHERE r.pull_request_id = pr.pull_request_id
    ) AS review_count
FROM pull_requests AS pr
ORDER BY pr.number;


-- Correlated scalar aggregate with MAX:
-- A PR with no reviews receives NULL from MAX().

SELECT
    pr.number,
    pr.title,
    (
        SELECT MAX(r.submitted_at)
        FROM reviews AS r
        WHERE r.pull_request_id = pr.pull_request_id
    ) AS latest_review_at
FROM pull_requests AS pr
ORDER BY pr.number;


-- Correlated comparison against the current PR author:
-- A self-approval is not counted as a valid approval.

SELECT
    pr.number,
    pr.title,
    (
        SELECT COUNT(*)
        FROM reviews AS r
        JOIN users AS reviewer
            ON reviewer.user_id = r.reviewer_id
        WHERE r.pull_request_id = pr.pull_request_id
          AND r.review_state = 'APPROVED'
          AND reviewer.user_id <> pr.author_id
          AND reviewer.active = TRUE
          AND reviewer.reviewer_eligible = TRUE
    ) AS valid_approval_count
FROM pull_requests AS pr
ORDER BY pr.number;


-- Correlated status-check validation:
-- The outer PR and its target branch determine which protected branch
-- policy applies. Each required check is then evaluated for that PR.

SELECT
    pr.number,
    pr.title,
    NOT EXISTS (
        SELECT 1
        FROM required_status_checks AS required_check
        WHERE required_check.branch_id = pr.target_branch_id
          AND NOT EXISTS (
              SELECT 1
              FROM status_checks AS actual_check
              WHERE actual_check.pull_request_id = pr.pull_request_id
                AND actual_check.check_name = required_check.check_name
                AND actual_check.check_state = 'SUCCESS'
          )
    ) AS all_required_checks_pass
FROM pull_requests AS pr
ORDER BY pr.number;


-- Correlated branch-protection evaluation:
-- Each condition remains tied to the current Pull Request rather than being
-- evaluated as one repository-wide aggregate.

SELECT
    pr.number,
    pr.title,
    CASE
        WHEN pr.is_draft THEN FALSE
        WHEN (
            SELECT COUNT(*)
            FROM reviews AS r
            JOIN users AS reviewer
                ON reviewer.user_id = r.reviewer_id
            WHERE r.pull_request_id = pr.pull_request_id
              AND r.review_state = 'APPROVED'
              AND reviewer.user_id <> pr.author_id
              AND reviewer.active = TRUE
              AND reviewer.reviewer_eligible = TRUE
        ) < (
            SELECT policy.required_approvals
            FROM branch_protection_policies AS policy
            WHERE policy.branch_id = pr.target_branch_id
        ) THEN FALSE
        WHEN EXISTS (
            SELECT 1
            FROM required_status_checks AS required_check
            WHERE required_check.branch_id = pr.target_branch_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM status_checks AS actual_check
                  WHERE actual_check.pull_request_id = pr.pull_request_id
                    AND actual_check.check_name =
                        required_check.check_name
                    AND actual_check.check_state = 'SUCCESS'
              )
        ) THEN FALSE
        WHEN EXISTS (
            SELECT 1
            FROM branch_protection_policies AS policy
            JOIN review_comments AS c
                ON c.pull_request_id = pr.pull_request_id
            WHERE policy.branch_id = pr.target_branch_id
              AND policy.require_conversation_resolution = TRUE
              AND c.resolved = FALSE
        ) THEN FALSE
        ELSE TRUE
    END AS merge_eligible
FROM pull_requests AS pr
ORDER BY pr.number;


-- A correlated subquery can also compare a row to an aggregate belonging
-- specifically to that row's group.
--
-- This query identifies PRs whose review count is above the average review
-- count for PRs in the same repository.

SELECT
    pr.number,
    pr.title,
    (
        SELECT COUNT(*)
        FROM reviews AS r
        WHERE r.pull_request_id = pr.pull_request_id
    ) AS review_count
FROM pull_requests AS pr
WHERE (
    SELECT COUNT(*)
    FROM reviews AS r
    WHERE r.pull_request_id = pr.pull_request_id
) > (
    SELECT AVG(review_counts.review_count)
    FROM (
        SELECT
            inner_pr.pull_request_id,
            COUNT(inner_review.review_id) AS review_count
        FROM pull_requests AS inner_pr
        LEFT JOIN reviews AS inner_review
            ON inner_review.pull_request_id =
               inner_pr.pull_request_id
        WHERE inner_pr.repository_id = pr.repository_id
        GROUP BY inner_pr.pull_request_id
    ) AS review_counts
)
ORDER BY pr.number;


-- Nested correlation:
-- Determine whether the current PR has an approval from an active,
-- review-eligible user.

SELECT
    pr.number,
    pr.title
FROM pull_requests AS pr
WHERE EXISTS (
    SELECT 1
    FROM reviews AS r
    WHERE r.pull_request_id = pr.pull_request_id
      AND r.review_state = 'APPROVED'
      AND EXISTS (
          SELECT 1
          FROM users AS reviewer
          WHERE reviewer.user_id = r.reviewer_id
            AND reviewer.active = TRUE
            AND reviewer.reviewer_eligible = TRUE
      )
);


-- Transactional policy update.
-- This demonstrates that branch protection is data enforced at the
-- database layer, while correlated queries consume that policy.

BEGIN;

UPDATE branch_protection_policies
SET required_approvals = 2
WHERE branch_id = (
    SELECT b.branch_id
    FROM branches AS b
    JOIN repositories AS r
        ON r.repository_id = b.repository_id
    WHERE r.repository_name = 'payments-service'
      AND b.branch_name = 'main'
);

COMMIT;


-- Re-evaluate merge eligibility after the policy change.

SELECT
    pr.number,
    pr.title,
    (
        SELECT COUNT(*)
        FROM reviews AS review
        JOIN users AS reviewer
            ON reviewer.user_id = review.reviewer_id
        WHERE review.pull_request_id = pr.pull_request_id
          AND review.review_state = 'APPROVED'
          AND reviewer.user_id <> pr.author_id
          AND reviewer.active = TRUE
          AND reviewer.reviewer_eligible = TRUE
    ) AS approvals,
    (
        SELECT policy.required_approvals
        FROM branch_protection_policies AS policy
        WHERE policy.branch_id = pr.target_branch_id
    ) AS required_approvals
FROM pull_requests AS pr
WHERE pr.target_branch_id = (
    SELECT b.branch_id
    FROM branches AS b
    JOIN repositories AS r
        ON r.repository_id = b.repository_id
    WHERE r.repository_name = 'payments-service'
      AND b.branch_name = 'main'
)
ORDER BY pr.number;


-- Reset the demonstration policy so the script remains deterministic if
-- its final queries are executed again in the same session.

UPDATE branch_protection_policies
SET required_approvals = 1
WHERE branch_id = (
    SELECT b.branch_id
    FROM branches AS b
    JOIN repositories AS r
        ON r.repository_id = b.repository_id
    WHERE r.repository_name = 'payments-service'
      AND b.branch_name = 'main'
);
