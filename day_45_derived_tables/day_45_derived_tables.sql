/*
Derived Tables: Subqueries in FROM and Intermediate Result Sets
PostgreSQL-compatible SQL

The database represents repository governance data and uses derived tables
inside FROM clauses to create intermediate result sets.

The examples deliberately separate:
- Pull Request facts
- review decisions
- approval aggregation
- status-check aggregation
- branch-protection policy
- final merge eligibility

A subquery in FROM is treated as a logical relation by the outer query.
*/

DROP SCHEMA IF EXISTS derived_table_lab CASCADE;
CREATE SCHEMA derived_table_lab;

SET search_path TO derived_table_lab;

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE
);

CREATE TABLE branches (
    branch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    branch_name TEXT NOT NULL,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE pull_requests (
    pull_request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),
    source_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    author TEXT NOT NULL,
    state TEXT NOT NULL
        CHECK (state IN ('OPEN', 'CLOSED', 'MERGED')),
    additions INTEGER NOT NULL CHECK (additions >= 0),
    deletions INTEGER NOT NULL CHECK (deletions >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (source_branch_id <> target_branch_id)
);

CREATE TABLE reviewers (
    reviewer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username TEXT NOT NULL UNIQUE
);

CREATE TABLE reviews (
    review_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES reviewers(reviewer_id),
    review_state TEXT NOT NULL
        CHECK (
            review_state IN (
                'APPROVED',
                'CHANGES_REQUESTED',
                'COMMENTED'
            )
        ),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (pull_request_id, reviewer_id, submitted_at)
);

CREATE TABLE review_comments (
    comment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    review_id BIGINT NOT NULL
        REFERENCES reviews(review_id)
        ON DELETE CASCADE,
    comment_body TEXT NOT NULL,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE status_checks (
    status_check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    check_state TEXT NOT NULL
        CHECK (
            check_state IN (
                'SUCCESS',
                'FAILURE',
                'PENDING'
            )
        ),
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name)
);

CREATE TABLE branch_protection_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    required_approvals INTEGER NOT NULL
        CHECK (required_approvals >= 0),
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    prohibit_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    prohibit_deletion BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE required_policy_checks (
    policy_id BIGINT NOT NULL
        REFERENCES branch_protection_policies(policy_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    PRIMARY KEY (policy_id, check_name)
);

CREATE INDEX idx_pr_target_branch
    ON pull_requests(target_branch_id);

CREATE INDEX idx_reviews_pr_state
    ON reviews(pull_request_id, review_state);

CREATE INDEX idx_status_checks_pr_state
    ON status_checks(pull_request_id, check_state);

CREATE INDEX idx_comments_unresolved
    ON review_comments(review_id)
    WHERE is_resolved = FALSE;

INSERT INTO repositories (repository_name)
VALUES
    ('payment-platform'),
    ('identity-service');

INSERT INTO branches (repository_id, branch_name)
SELECT r.repository_id, b.branch_name
FROM repositories r
CROSS JOIN (
    VALUES
        ('main'),
        ('release'),
        ('feature/checkout-validation'),
        ('fix/token-expiry'),
        ('release/2026-10'),
        ('feature/session-hardening')
) AS b(branch_name)
WHERE
    (r.repository_name = 'payment-platform'
     AND b.branch_name IN (
        'main',
        'release',
        'feature/checkout-validation',
        'fix/token-expiry',
        'release/2026-10'
     ))
    OR
    (r.repository_name = 'identity-service'
     AND b.branch_name IN (
        'main',
        'feature/session-hardening'
     ));

INSERT INTO reviewers (username)
VALUES
    ('atul'),
    ('neha'),
    ('rahul'),
    ('vikas'),
    ('meera');

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    author,
    state,
    additions,
    deletions
)
SELECT
    r.repository_id,
    source_branch.branch_id,
    target_branch.branch_id,
    data.author,
    data.state,
    data.additions,
    data.deletions
FROM (
    VALUES
        (
            'payment-platform',
            'feature/checkout-validation',
            'main',
            'atul',
            'OPEN',
            340,
            90
        ),
        (
            'payment-platform',
            'fix/token-expiry',
            'main',
            'neha',
            'OPEN',
            80,
            25
        ),
        (
            'payment-platform',
            'release/2026-10',
            'release',
            'rahul',
            'OPEN',
            510,
            180
        ),
        (
            'identity-service',
            'feature/session-hardening',
            'main',
            'meera',
            'OPEN',
            210,
            60
        )
) AS data(
    repository_name,
    source_branch,
    target_branch,
    author,
    state,
    additions,
    deletions
)
JOIN repositories r
    ON r.repository_name = data.repository_name
JOIN branches source_branch
    ON source_branch.repository_id = r.repository_id
    AND source_branch.branch_name = data.source_branch
JOIN branches target_branch
    ON target_branch.repository_id = r.repository_id
    AND target_branch.branch_name = data.target_branch;

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state,
    submitted_at
)
SELECT
    pr.pull_request_id,
    reviewer.reviewer_id,
    data.review_state,
    CURRENT_TIMESTAMP - data.age
FROM (
    VALUES
        (1::BIGINT, 'neha', 'APPROVED', INTERVAL '4 hours'),
        (1::BIGINT, 'rahul', 'APPROVED', INTERVAL '3 hours'),
        (2::BIGINT, 'meera', 'APPROVED', INTERVAL '5 hours'),
        (3::BIGINT, 'neha', 'APPROVED', INTERVAL '2 hours'),
        (3::BIGINT, 'vikas', 'CHANGES_REQUESTED', INTERVAL '1 hour'),
        (4::BIGINT, 'rahul', 'APPROVED', INTERVAL '2 hours')
) AS data(
    pull_request_id,
    username,
    review_state,
    age
)
JOIN pull_requests pr
    ON pr.pull_request_id = data.pull_request_id
JOIN reviewers reviewer
    ON reviewer.username = data.username;

INSERT INTO review_comments (
    review_id,
    comment_body,
    is_resolved
)
SELECT
    review_id,
    'Validate the security-sensitive path before merge.',
    FALSE
FROM reviews
WHERE review_state = 'CHANGES_REQUESTED';

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    check_state,
    completed_at
)
VALUES
    (1, 'unit-tests', 'SUCCESS', CURRENT_TIMESTAMP),
    (1, 'security-scan', 'SUCCESS', CURRENT_TIMESTAMP),
    (2, 'unit-tests', 'SUCCESS', CURRENT_TIMESTAMP),
    (2, 'security-scan', 'FAILURE', CURRENT_TIMESTAMP),
    (3, 'unit-tests', 'SUCCESS', CURRENT_TIMESTAMP),
    (3, 'security-scan', 'SUCCESS', CURRENT_TIMESTAMP),
    (4, 'unit-tests', 'SUCCESS', CURRENT_TIMESTAMP),
    (4, 'security-scan', 'SUCCESS', CURRENT_TIMESTAMP);

INSERT INTO branch_protection_policies (
    branch_id,
    required_approvals,
    require_linear_history,
    prohibit_force_push,
    prohibit_deletion
)
SELECT
    b.branch_id,
    2,
    TRUE,
    TRUE,
    TRUE
FROM branches b
JOIN repositories r
    ON r.repository_id = b.repository_id
WHERE
    (r.repository_name = 'payment-platform'
     AND b.branch_name IN ('main', 'release'))
    OR
    (r.repository_name = 'identity-service'
     AND b.branch_name = 'main');

INSERT INTO required_policy_checks (
    policy_id,
    check_name
)
SELECT
    policy.policy_id,
    check_name
FROM branch_protection_policies policy
CROSS JOIN (
    VALUES
        ('unit-tests'),
        ('security-scan')
) AS required(check_name);

/*
The following query creates a derived table containing change metrics.

The outer query does not need to know how additions and deletions were
combined. It treats the subquery as an intermediate relation.
*/
SELECT
    large_changes.pull_request_id,
    large_changes.repository_name,
    large_changes.total_change
FROM (
    SELECT
        pr.pull_request_id,
        r.repository_name,
        pr.additions + pr.deletions AS total_change
    FROM pull_requests pr
    JOIN repositories r
        ON r.repository_id = pr.repository_id
) AS large_changes
WHERE large_changes.total_change >= 200
ORDER BY large_changes.total_change DESC;

/*
Nested derived tables:
the first FROM-subquery calculates change size;
the next derived relation filters large changes;
the outer query aggregates the intermediate rows.
*/
SELECT
    large_change_groups.repository_name,
    COUNT(*) AS large_pull_request_count,
    AVG(large_change_groups.total_change) AS average_change
FROM (
    SELECT
        change_metrics.pull_request_id,
        change_metrics.repository_name,
        change_metrics.total_change
    FROM (
        SELECT
            pr.pull_request_id,
            r.repository_name,
            pr.additions + pr.deletions AS total_change
        FROM pull_requests pr
        JOIN repositories r
            ON r.repository_id = pr.repository_id
    ) AS change_metrics
    WHERE change_metrics.total_change >= 100
) AS large_change_groups
GROUP BY large_change_groups.repository_name
ORDER BY large_change_groups.repository_name;

/*
Approval derived table:
only approved reviews are retained before reviewers are counted.

This keeps review-state interpretation inside the review-specific
intermediate relation instead of mixing it into every outer expression.
*/
SELECT
    approval_counts.pull_request_id,
    approval_counts.approval_count
FROM (
    SELECT
        approved_reviews.pull_request_id,
        COUNT(DISTINCT approved_reviews.reviewer_id)
            AS approval_count
    FROM (
        SELECT
            review.pull_request_id,
            review.reviewer_id
        FROM reviews review
        WHERE review.review_state = 'APPROVED'
    ) AS approved_reviews
    GROUP BY approved_reviews.pull_request_id
) AS approval_counts
ORDER BY approval_counts.pull_request_id;

/*
Status-check derived table:
successful checks are transformed into a relation that can be compared
against the checks required by a branch policy.
*/
SELECT
    passing.pull_request_id,
    passing.passing_check_count
FROM (
    SELECT
        status_check.pull_request_id,
        COUNT(*) AS passing_check_count
    FROM (
        SELECT
            sc.pull_request_id,
            sc.check_name
        FROM status_checks sc
        WHERE sc.check_state = 'SUCCESS'
    ) AS status_check
    GROUP BY status_check.pull_request_id
) AS passing
ORDER BY passing.pull_request_id;

/*
The following query constructs a multi-stage intermediate result.

The policy relation identifies the protection policy for the target branch.
The approval relation independently calculates approved reviewers.
The check relation independently calculates successful required checks.
The outer query combines those relations into merge eligibility.
*/
WITH policy_relation AS (
    SELECT
        policy.policy_id,
        branch.branch_id,
        repository.repository_id,
        repository.repository_name,
        branch.branch_name,
        policy.required_approvals
    FROM branch_protection_policies policy
    JOIN branches branch
        ON branch.branch_id = policy.branch_id
    JOIN repositories repository
        ON repository.repository_id = branch.repository_id
),
approval_relation AS (
    SELECT
        review.pull_request_id,
        COUNT(DISTINCT review.reviewer_id) AS approval_count
    FROM reviews review
    WHERE review.review_state = 'APPROVED'
    GROUP BY review.pull_request_id
),
passing_check_relation AS (
    SELECT
        check_rows.pull_request_id,
        COUNT(*) AS passing_check_count
    FROM status_checks check_rows
    WHERE check_rows.check_state = 'SUCCESS'
    GROUP BY check_rows.pull_request_id
),
required_check_relation AS (
    SELECT
        policy.policy_id,
        COUNT(*) AS required_check_count
    FROM branch_protection_policies policy
    JOIN required_policy_checks required_check
        ON required_check.policy_id = policy.policy_id
    GROUP BY policy.policy_id
),
pull_request_relation AS (
    SELECT
        pr.pull_request_id,
        pr.repository_id,
        pr.target_branch_id,
        pr.state,
        repository.repository_name,
        branch.branch_name
    FROM pull_requests pr
    JOIN repositories repository
        ON repository.repository_id = pr.repository_id
    JOIN branches branch
        ON branch.branch_id = pr.target_branch_id
)
SELECT
    pr.pull_request_id,
    pr.repository_name,
    pr.branch_name AS target_branch,
    COALESCE(approval.approval_count, 0) AS approval_count,
    policy.required_approvals,
    COALESCE(passing_check.passing_check_count, 0)
        AS passing_check_count,
    required_check.required_check_count,
    (
        pr.state = 'OPEN'
        AND COALESCE(approval.approval_count, 0)
            >= policy.required_approvals
        AND COALESCE(passing_check.passing_check_count, 0)
            >= required_check.required_check_count
    ) AS merge_eligible
FROM pull_request_relation pr
JOIN policy_relation policy
    ON policy.repository_id = pr.repository_id
    AND policy.branch_id = pr.target_branch_id
LEFT JOIN approval_relation approval
    ON approval.pull_request_id = pr.pull_request_id
LEFT JOIN passing_check_relation passing_check
    ON passing_check.pull_request_id = pr.pull_request_id
JOIN required_check_relation required_check
    ON required_check.policy_id = policy.policy_id
ORDER BY pr.pull_request_id;

/*
A derived table can expose an aggregate before another query filters it.

Here the intermediate relation calculates review density and the outer query
identifies Pull Requests with more than one distinct reviewer.
*/
SELECT
    review_density.repository_name,
    review_density.pull_request_id,
    review_density.reviewer_count
FROM (
    SELECT
        repository.repository_name,
        review.pull_request_id,
        COUNT(DISTINCT review.reviewer_id) AS reviewer_count
    FROM reviews review
    JOIN pull_requests pr
        ON pr.pull_request_id = review.pull_request_id
    JOIN repositories repository
        ON repository.repository_id = pr.repository_id
    GROUP BY
        repository.repository_name,
        review.pull_request_id
) AS review_density
WHERE review_density.reviewer_count > 1
ORDER BY review_density.reviewer_count DESC;

/*
A derived table can also isolate unresolved review discussions before the
outer query evaluates whether a Pull Request has outstanding review work.
*/
SELECT
    unresolved.pull_request_id,
    unresolved.unresolved_comment_count
FROM (
    SELECT
        review.pull_request_id,
        COUNT(comment.comment_id) AS unresolved_comment_count
    FROM reviews review
    JOIN review_comments comment
        ON comment.review_id = review.review_id
    WHERE comment.is_resolved = FALSE
    GROUP BY review.pull_request_id
) AS unresolved
WHERE unresolved.unresolved_comment_count > 0
ORDER BY unresolved.pull_request_id;

/*
Integrity demonstration.

The database rejects negative additions because the CHECK constraint belongs
to the relational model. The statement is intentionally not executed here so
that the complete demonstration script remains successful.
*/
SELECT
    conname,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'pull_requests'::regclass
ORDER BY conname;

/*
Performance inspection:
the derived-table queries can be examined with PostgreSQL's planner.
EXPLAIN ANALYZE is executable and uses the indexes defined above.
*/
EXPLAIN ANALYZE
SELECT
    derived.repository_name,
    COUNT(*) AS large_pr_count
FROM (
    SELECT
        pr.pull_request_id,
        repository.repository_name,
        pr.additions + pr.deletions AS total_change
    FROM pull_requests pr
    JOIN repositories repository
        ON repository.repository_id = pr.repository_id
) AS derived
WHERE derived.total_change >= 200
GROUP BY derived.repository_name;
