#!/usr/bin/env python3
"""
EXISTS, NOT EXISTS, Semi-Joins, Anti-Joins, and Existence Checks

A self-contained demonstration using SQLite and Python's standard library.

The program models a software engineering organization and evaluates:
- EXISTS and NOT EXISTS predicates.
- Correlated and uncorrelated subqueries.
- Semi-join and anti-join behavior.
- Nested existence checks.
- NULL semantics and duplicate handling.
- Relational division using nested NOT EXISTS.
- Query plans, indexing, and parameterized queries.
- Equivalent SQL formulations and automated correctness tests.
"""

from __future__ import annotations

import sqlite3
import unittest
from contextlib import closing
from typing import Any, Iterable


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS developers (
    developer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    team TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS repositories (
    repository_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    owner_team TEXT NOT NULL,
    protected INTEGER NOT NULL DEFAULT 1
        CHECK (protected IN (0, 1))
);

CREATE TABLE IF NOT EXISTS pull_requests (
    pull_request_id INTEGER PRIMARY KEY,
    repository_id INTEGER NOT NULL
        REFERENCES repositories(repository_id),
    author_id INTEGER NOT NULL
        REFERENCES developers(developer_id),
    title TEXT NOT NULL,
    state TEXT NOT NULL
        CHECK (state IN ('open', 'merged', 'closed')),
    is_draft INTEGER NOT NULL DEFAULT 0
        CHECK (is_draft IN (0, 1))
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY,
    pull_request_id INTEGER NOT NULL
        REFERENCES pull_requests(pull_request_id),
    reviewer_id INTEGER NOT NULL
        REFERENCES developers(developer_id),
    state TEXT NOT NULL
        CHECK (state IN ('approved', 'changes_requested', 'commented')),
    submitted_at TEXT NOT NULL,
    UNIQUE (pull_request_id, reviewer_id, submitted_at)
);

CREATE TABLE IF NOT EXISTS status_checks (
    check_id INTEGER PRIMARY KEY,
    pull_request_id INTEGER NOT NULL
        REFERENCES pull_requests(pull_request_id),
    check_name TEXT NOT NULL,
    state TEXT NOT NULL
        CHECK (state IN ('success', 'failure', 'pending')),
    UNIQUE (pull_request_id, check_name)
);

CREATE TABLE IF NOT EXISTS repository_permissions (
    developer_id INTEGER NOT NULL
        REFERENCES developers(developer_id),
    repository_id INTEGER NOT NULL
        REFERENCES repositories(repository_id),
    permission TEXT NOT NULL
        CHECK (permission IN ('read', 'write', 'maintain', 'admin')),
    PRIMARY KEY (developer_id, repository_id)
);

CREATE TABLE IF NOT EXISTS required_checks (
    repository_id INTEGER NOT NULL
        REFERENCES repositories(repository_id),
    check_name TEXT NOT NULL,
    PRIMARY KEY (repository_id, check_name)
);

CREATE INDEX IF NOT EXISTS idx_pr_repository_state
    ON pull_requests(repository_id, state);

CREATE INDEX IF NOT EXISTS idx_reviews_pr_state
    ON reviews(pull_request_id, state);

CREATE INDEX IF NOT EXISTS idx_reviews_reviewer
    ON reviews(reviewer_id, pull_request_id);

CREATE INDEX IF NOT EXISTS idx_checks_pr_state
    ON status_checks(pull_request_id, state);

CREATE INDEX IF NOT EXISTS idx_permissions_repository
    ON repository_permissions(repository_id, developer_id);
"""


SAMPLE_DATA = """
INSERT OR IGNORE INTO developers
    (developer_id, name, team, active)
VALUES
    (1, 'Asha', 'Platform', 1),
    (2, 'Ravi', 'Platform', 1),
    (3, 'Meera', 'Security', 1),
    (4, 'Kabir', 'Quality', 1),
    (5, 'InactiveReviewer', 'Platform', 0),
    (6, 'Nisha', 'Data', 1);

INSERT OR IGNORE INTO repositories
    (repository_id, name, owner_team, protected)
VALUES
    (1, 'deployment-service', 'Platform', 1),
    (2, 'security-scanner', 'Security', 1),
    (3, 'analytics-pipeline', 'Data', 0);

INSERT OR IGNORE INTO pull_requests
    (pull_request_id, repository_id, author_id, title, state, is_draft)
VALUES
    (101, 1, 1, 'Improve deployment retries', 'open', 0),
    (102, 1, 2, 'Add rollback support', 'open', 0),
    (103, 1, 1, 'Draft health endpoint', 'open', 1),
    (104, 1, 2, 'Document deployment API', 'merged', 0),
    (201, 2, 3, 'Fix scanner validation', 'open', 0),
    (301, 3, 6, 'Optimize batch ingestion', 'open', 0);

INSERT OR IGNORE INTO reviews
    (review_id, pull_request_id, reviewer_id, state, submitted_at)
VALUES
    (1, 101, 2, 'approved', '2026-10-10T10:00:00Z'),
    (2, 101, 3, 'commented', '2026-10-10T11:00:00Z'),
    (3, 102, 3, 'changes_requested', '2026-10-11T09:00:00Z'),
    (4, 102, 4, 'approved', '2026-10-11T10:00:00Z'),
    (5, 104, 3, 'approved', '2026-10-09T09:00:00Z'),
    (6, 201, 4, 'approved', '2026-10-12T09:00:00Z'),
    (7, 201, 5, 'approved', '2026-10-12T10:00:00Z');

INSERT OR IGNORE INTO status_checks
    (check_id, pull_request_id, check_name, state)
VALUES
    (1, 101, 'unit-tests', 'success'),
    (2, 101, 'security-scan', 'success'),
    (3, 102, 'unit-tests', 'success'),
    (4, 102, 'security-scan', 'failure'),
    (5, 103, 'unit-tests', 'pending'),
    (6, 201, 'unit-tests', 'success'),
    (7, 301, 'unit-tests', 'success');

INSERT OR IGNORE INTO repository_permissions
    (developer_id, repository_id, permission)
VALUES
    (1, 1, 'write'),
    (2, 1, 'write'),
    (3, 1, 'maintain'),
    (4, 1, 'read'),
    (3, 2, 'write'),
    (4, 2, 'maintain'),
    (6, 3, 'write');

INSERT OR IGNORE INTO required_checks (repository_id, check_name)
VALUES
    (1, 'unit-tests'),
    (1, 'security-scan'),
    (2, 'unit-tests');
"""


def create_database() -> sqlite3.Connection:
    """Create an in-memory database with realistic repository data."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    connection.executescript(SAMPLE_DATA)
    return connection


def fetch_all(
    connection: sqlite3.Connection,
    sql: str,
    parameters: Iterable[Any] = (),
) -> list[dict[str, Any]]:
    """Execute parameterized SQL and return ordinary dictionaries."""
    return [
        dict(row)
        for row in connection.execute(sql, tuple(parameters)).fetchall()
    ]


def display(title: str, rows: list[dict[str, Any]]) -> None:
    print(f"\n--- {title} ---")
    if not rows:
        print("(no rows)")
        return

    for row in rows:
        print(" | ".join(f"{key}={value}" for key, value in row.items()))


def demo_exists(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """
    A semi-join returns each qualifying pull request once.

    EXISTS is a Boolean test. Multiple matching review records do not
    multiply the outer pull-request row.
    """
    sql = """
        SELECT p.pull_request_id, p.title
        FROM pull_requests AS p
        WHERE p.state = ?
          AND EXISTS (
              SELECT 1
              FROM reviews AS r
              WHERE r.pull_request_id = p.pull_request_id
                AND r.state = ?
          )
        ORDER BY p.pull_request_id
    """
    return fetch_all(connection, sql, ("open", "approved"))


def demo_not_exists(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """An anti-join returns open pull requests without any approved review."""
    sql = """
        SELECT p.pull_request_id, p.title
        FROM pull_requests AS p
        WHERE p.state = 'open'
          AND NOT EXISTS (
              SELECT 1
              FROM reviews AS r
              WHERE r.pull_request_id = p.pull_request_id
                AND r.state = 'approved'
          )
        ORDER BY p.pull_request_id
    """
    return fetch_all(connection, sql)


def demo_join_comparison(
    connection: sqlite3.Connection,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Compare a normal join with EXISTS.

    A join produces one row per matching pair. EXISTS preserves outer
    cardinality, which is often the desired behavior for existence tests.
    """
    join_sql = """
        SELECT p.pull_request_id, p.title
        FROM pull_requests AS p
        JOIN reviews AS r
          ON r.pull_request_id = p.pull_request_id
        WHERE p.state = 'open'
          AND r.state IN ('approved', 'commented')
        ORDER BY p.pull_request_id, r.review_id
    """

    exists_sql = """
        SELECT p.pull_request_id, p.title
        FROM pull_requests AS p
        WHERE p.state = 'open'
          AND EXISTS (
              SELECT 1
              FROM reviews AS r
              WHERE r.pull_request_id = p.pull_request_id
                AND r.state IN ('approved', 'commented')
          )
        ORDER BY p.pull_request_id
    """

    return fetch_all(connection, join_sql), fetch_all(connection, exists_sql)


def demo_nested_exists(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """
    Find open pull requests with an approval and all required checks passing.

    The nested NOT EXISTS pattern verifies that no required check is missing
    or unsuccessful. It distinguishes an absent check from a successful one.
    """
    sql = """
        SELECT p.pull_request_id, p.title
        FROM pull_requests AS p
        JOIN repositories AS repo
          ON repo.repository_id = p.repository_id
        WHERE p.state = 'open'
          AND p.is_draft = 0
          AND EXISTS (
              SELECT 1
              FROM reviews AS r
              JOIN developers AS reviewer
                ON reviewer.developer_id = r.reviewer_id
              WHERE r.pull_request_id = p.pull_request_id
                AND r.state = 'approved'
                AND reviewer.active = 1
          )
          AND NOT EXISTS (
              SELECT 1
              FROM required_checks AS required
              WHERE required.repository_id = p.repository_id
                AND NOT EXISTS (
                    SELECT 1
                    FROM status_checks AS actual
                    WHERE actual.pull_request_id = p.pull_request_id
                      AND actual.check_name = required.check_name
                      AND actual.state = 'success'
                )
          )
        ORDER BY p.pull_request_id
    """
    return fetch_all(connection, sql)


def demo_review_requirements(
    connection: sqlite3.Connection,
    minimum_approvals: int = 2,
) -> list[dict[str, Any]]:
    """
    Evaluate a two-approval policy.

    EXISTS establishes that the PR has an eligible approval. A grouped
    subquery counts distinct active reviewers, because approval policies
    often count people rather than review events.
    """
    if minimum_approvals < 1:
        raise ValueError("minimum_approvals must be at least one")

    sql = """
        SELECT
            p.pull_request_id,
            p.title,
            COUNT(DISTINCT CASE
                WHEN r.state = 'approved' AND d.active = 1
                THEN r.reviewer_id
            END) AS active_approvals
        FROM pull_requests AS p
        LEFT JOIN reviews AS r
          ON r.pull_request_id = p.pull_request_id
        LEFT JOIN developers AS d
          ON d.developer_id = r.reviewer_id
        WHERE p.state = 'open'
          AND p.is_draft = 0
          AND EXISTS (
              SELECT 1
              FROM reviews AS eligible
              JOIN developers AS reviewer
                ON reviewer.developer_id = eligible.reviewer_id
              WHERE eligible.pull_request_id = p.pull_request_id
                AND eligible.state = 'approved'
                AND reviewer.active = 1
          )
        GROUP BY p.pull_request_id, p.title
        HAVING COUNT(DISTINCT CASE
            WHEN r.state = 'approved' AND d.active = 1
            THEN r.reviewer_id
        END) >= ?
        ORDER BY p.pull_request_id
    """
    return fetch_all(connection, sql, (minimum_approvals,))


def demo_relational_division(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """
    Find repositories for which every required check is configured.

    The outer NOT EXISTS means there is no required check lacking a
    corresponding successful result. This is a standard relational-division
    pattern. Here the checks are required by repository policy.
    """
    sql = """
        SELECT repo.repository_id, repo.name
        FROM repositories AS repo
        WHERE EXISTS (
            SELECT 1
            FROM required_checks AS rc
            WHERE rc.repository_id = repo.repository_id
        )
        AND NOT EXISTS (
            SELECT 1
            FROM required_checks AS rc
            WHERE rc.repository_id = repo.repository_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM pull_requests AS p
                  JOIN status_checks AS sc
                    ON sc.pull_request_id = p.pull_request_id
                  WHERE p.repository_id = repo.repository_id
                    AND sc.check_name = rc.check_name
                    AND sc.state = 'success'
              )
        )
        ORDER BY repo.repository_id
    """
    return fetch_all(connection, sql)


def demo_null_semantics(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """
    Show why NOT EXISTS and NOT IN can differ when NULL enters a subquery.

    SQL uses three-valued logic. A NOT IN expression may evaluate to UNKNOWN
    if its candidate set contains NULL, whereas the correlated NOT EXISTS
    predicate evaluates each equality match independently.
    """
    connection.execute(
        "CREATE TEMP TABLE IF NOT EXISTS reviewer_candidates "
        "(developer_id INTEGER)"
    )
    connection.execute("DELETE FROM reviewer_candidates")
    connection.executemany(
        "INSERT INTO reviewer_candidates (developer_id) VALUES (?)",
        [(2,), (None,)],
    )

    not_exists_sql = """
        SELECT d.developer_id, d.name
        FROM developers AS d
        WHERE d.developer_id <> ?
          AND NOT EXISTS (
              SELECT 1
              FROM reviewer_candidates AS c
              WHERE c.developer_id = d.developer_id
          )
        ORDER BY d.developer_id
    """

    not_in_sql = """
        SELECT d.developer_id, d.name
        FROM developers AS d
        WHERE d.developer_id <> ?
          AND d.developer_id NOT IN (
              SELECT c.developer_id
              FROM reviewer_candidates AS c
          )
        ORDER BY d.developer_id
    """

    print("\nNULL semantics:")
    print("NOT EXISTS rows:", demo_names(fetch_all(
        connection, not_exists_sql, (1,)
    )))
    print("NOT IN rows:", demo_names(fetch_all(
        connection, not_in_sql, (1,)
    )))
    return fetch_all(connection, not_exists_sql, (1,))


def demo_names(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row["name"]) for row in rows]


def demo_parameterized_existence(
    connection: sqlite3.Connection,
    repository_name: str,
    required_permission: str,
) -> bool:
    """
    Safely test access without assembling SQL from untrusted text.

    Values are parameters, not SQL fragments. Parameterization prevents
    injection through repository names and permission values.
    """
    allowed_permissions = {"read", "write", "maintain", "admin"}
    if required_permission not in allowed_permissions:
        raise ValueError("Unknown permission")

    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM repositories AS repo
            JOIN repository_permissions AS permission
              ON permission.repository_id = repo.repository_id
            WHERE repo.name = ?
              AND permission.developer_id = ?
              AND permission.permission IN (?, ?, ?, ?)
        ) AS allowed
    """

    row = connection.execute(
        sql,
        (
            repository_name,
            3,
            required_permission,
            "maintain",
            "admin",
            "write",
        ),
    ).fetchone()

    return bool(row["allowed"])


def demo_query_plan(connection: sqlite3.Connection) -> None:
    sql = """
        SELECT p.pull_request_id
        FROM pull_requests AS p
        WHERE EXISTS (
            SELECT 1
            FROM reviews AS r
            WHERE r.pull_request_id = p.pull_request_id
              AND r.state = 'approved'
        )
    """
    rows = fetch_all(
        connection,
        "EXPLAIN QUERY PLAN " + sql,
    )
    display("SQLite query plan", rows)


class ExistenceQueryTests(unittest.TestCase):
    """Automated tests for existence semantics and boundary conditions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.connection = create_database()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_exists_returns_approved_open_requests(self) -> None:
        rows = demo_exists(self.connection)
        self.assertEqual(
            [row["pull_request_id"] for row in rows],
            [101, 102],
        )

    def test_not_exists_finds_requests_without_approval(self) -> None:
        rows = demo_not_exists(self.connection)
        self.assertEqual(
            [row["pull_request_id"] for row in rows],
            [103],
        )

    def test_exists_does_not_duplicate_outer_rows(self) -> None:
        joined, semijoin = demo_join_comparison(self.connection)
        self.assertGreater(len(joined), len(semijoin))
        self.assertEqual(
            len({row["pull_request_id"] for row in semijoin}),
            len(semijoin),
        )

    def test_nested_checks_exclude_failed_and_missing_checks(self) -> None:
        rows = demo_nested_exists(self.connection)
        self.assertEqual(
            [row["pull_request_id"] for row in rows],
            [101],
        )

    def test_approval_threshold(self) -> None:
        rows = demo_review_requirements(self.connection, 2)
        self.assertEqual(
            [row["pull_request_id"] for row in rows],
            [102],
        )

    def test_zero_approval_threshold_is_invalid(self) -> None:
        with self.assertRaises(ValueError):
            demo_review_requirements(self.connection, 0)

    def test_parameterized_access_check(self) -> None:
        self.assertTrue(
            demo_parameterized_existence(
                self.connection, "deployment-service", "maintain"
            )
        )
        self.assertFalse(
            demo_parameterized_existence(
                self.connection, "deployment-service", "read"
            )
        )

    def test_invalid_permission_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            demo_parameterized_existence(
                self.connection, "deployment-service", "root"
            )

    def test_null_semantics(self) -> None:
        rows = demo_null_semantics(self.connection)
        self.assertGreater(len(rows), 0)

    def test_foreign_key_integrity(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                """
                INSERT INTO pull_requests
                    (pull_request_id, repository_id, author_id,
                     title, state, is_draft)
                VALUES (999, 999, 1, 'Invalid repository', 'open', 0)
                """
            )


def main() -> None:
    with closing(create_database()) as connection:
        display("Open pull requests with approved reviews", demo_exists(connection))
        display("Open pull requests without approved reviews", demo_not_exists(connection))

        joined, semijoin = demo_join_comparison(connection)
        display("Ordinary join: matching review rows", joined)
        display("EXISTS: each qualifying pull request once", semijoin)

        display(
            "Approval and required-check eligibility",
            demo_nested_exists(connection),
        )

        display(
            "Pull requests with at least two active reviewers",
            demo_review_requirements(connection, 2),
        )

        display(
            "Repositories with required checks satisfied",
            demo_relational_division(connection),
        )

        demo_null_semantics(connection)

        print("\nParameterized permission checks:")
        print(
            "Maintainer access:",
            demo_parameterized_existence(
                connection, "deployment-service", "maintain"
            ),
        )
        print(
            "Reader access:",
            demo_parameterized_existence(
                connection, "deployment-service", "read"
            ),
        )

        demo_query_plan(connection)

    print("\nAutomated correctness tests:")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        ExistenceQueryTests
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
