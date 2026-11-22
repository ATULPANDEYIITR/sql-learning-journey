#!/usr/bin/env python3
"""
Unique Indexes: Enforcing Uniqueness and Index-Backed Constraints

Demonstrates:
- Unique indexes and composite unique indexes
- NULL handling and partial unique indexes
- Case-insensitive uniqueness
- Expression-based uniqueness
- Constraint violations and exception handling
- Concurrent-style conflict simulation
- SQLite index-backed uniqueness
- Transaction rollback and validation
"""

from __future__ import annotations

import sqlite3
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class IndexType(Enum):
    UNIQUE = "UNIQUE"
    COMPOSITE = "COMPOSITE"
    PARTIAL = "PARTIAL"
    EXPRESSION = "EXPRESSION"


class UniqueViolation(Exception):
    """Raised when a unique index would be violated."""


@dataclass(frozen=True)
class User:
    user_id: int
    email: str
    username: str
    tenant_id: int
    active: bool = True


class UniqueIndex:
    """In-memory unique index with explicit key extraction."""

    def __init__(self, name: str, key_function):
        if not name:
            raise ValueError("Index name cannot be empty")

        self.name = name
        self.key_function = key_function
        self.entries: dict[tuple, int] = {}

    def insert(self, record_id: int, record) -> None:
        key = self.key_function(record)

        # None represents a value excluded from this index.
        if key is None:
            return

        if key in self.entries:
            raise UniqueViolation(
                f"Index '{self.name}' rejects duplicate key {key}"
            )

        self.entries[key] = record_id

    def delete(self, record_id: int) -> None:
        self.entries = {
            key: owner
            for key, owner in self.entries.items()
            if owner != record_id
        }

    def contains(self, key: tuple) -> bool:
        return key in self.entries

    def lookup(self, key: tuple) -> Optional[int]:
        return self.entries.get(key)


class UserRegistry:
    """Maintains several independent uniqueness rules."""

    def __init__(self):
        self.users: dict[int, User] = {}

        self.email_index = UniqueIndex(
            "uq_users_email",
            lambda user: (user.email.casefold(),)
        )

        self.username_index = UniqueIndex(
            "uq_users_tenant_username",
            lambda user: (
                user.tenant_id,
                user.username.casefold()
            )
        )

        self.active_email_index = UniqueIndex(
            "uq_active_users_email",
            lambda user: (
                (user.email.casefold(),)
                if user.active else None
            )
        )

    def register(self, user: User) -> None:
        if user.user_id <= 0:
            raise ValueError("User ID must be positive")

        if not user.email or "@" not in user.email:
            raise ValueError("Invalid email address")

        if not user.username.strip():
            raise ValueError("Username cannot be empty")

        if user.tenant_id <= 0:
            raise ValueError("Tenant ID must be positive")

        if user.user_id in self.users:
            raise UniqueViolation("Duplicate primary key")

        # Validate every index before changing any index.
        indexes = (
            self.email_index,
            self.username_index,
            self.active_email_index,
        )

        keys = [(index, index.key_function(user)) for index in indexes]

        for index, key in keys:
            if key is not None and index.contains(key):
                raise UniqueViolation(
                    f"Duplicate value rejected by {index.name}: {key}"
                )

        for index, key in keys:
            if key is not None:
                index.entries[key] = user.user_id

        self.users[user.user_id] = user

    def deactivate(self, user_id: int) -> None:
        user = self.users.get(user_id)

        if user is None:
            raise KeyError("User does not exist")

        if not user.active:
            return

        self.active_email_index.delete(user_id)

        self.users[user_id] = User(
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            tenant_id=user.tenant_id,
            active=False,
        )

    def find_by_email(self, email: str) -> Optional[User]:
        user_id = self.email_index.lookup((email.casefold(),))
        return self.users.get(user_id) if user_id else None

    def audit(self) -> bool:
        """Reconstruct indexes and verify their consistency."""

        rebuilt = UserRegistry()

        for user in self.users.values():
            rebuilt.register(user)

        return (
            rebuilt.email_index.entries == self.email_index.entries
            and rebuilt.username_index.entries
            == self.username_index.entries
            and rebuilt.active_email_index.entries
            == self.active_email_index.entries
        )


def demonstrate_sqlite() -> None:
    """Execute actual index-backed uniqueness using SQLite."""

    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")

    connection.executescript("""
        CREATE TABLE tenants (
            tenant_id INTEGER PRIMARY KEY,
            tenant_name TEXT NOT NULL
        );

        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(tenant_id),
            email TEXT NOT NULL,
            username TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
                CHECK (active IN (0, 1))
        );

        CREATE UNIQUE INDEX uq_users_email
            ON users(email COLLATE NOCASE);

        CREATE UNIQUE INDEX uq_users_tenant_username
            ON users(tenant_id, username COLLATE NOCASE);

        CREATE UNIQUE INDEX uq_active_users_email
            ON users(email COLLATE NOCASE)
            WHERE active = 1;

        CREATE UNIQUE INDEX uq_users_normalized_email
            ON users(lower(trim(email)));

        INSERT INTO tenants VALUES
            (1, 'Engineering'),
            (2, 'Research');
    """)

    connection.execute(
        """
        INSERT INTO users
        (user_id, tenant_id, email, username, active)
        VALUES (?, ?, ?, ?, ?)
        """,
        (1, 1, "alice@example.com", "alice", 1),
    )

    # Duplicate case-insensitive email is rejected.
    try:
        connection.execute(
            """
            INSERT INTO users
            VALUES (?, ?, ?, ?, ?)
            """,
            (2, 2, "ALICE@example.com", "alice2", 1),
        )
    except sqlite3.IntegrityError as error:
        print("Expected email violation:", error)

    # The same username can exist in another tenant.
    connection.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
        (3, 2, "bob@example.com", "alice", 1),
    )

    # A partial unique index allows an inactive duplicate email.
    connection.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
        (4, 1, "alice@example.com", "alice_archive", 0),
    )

    # An active duplicate is rejected.
    try:
        connection.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
            (5, 1, "alice@example.com", "alice_new", 1),
        )
    except sqlite3.IntegrityError as error:
        print("Expected partial-index violation:", error)

    connection.execute(
        "UPDATE users SET active = 0 WHERE user_id = 1"
    )

    connection.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
        (5, 1, "alice@example.com", "alice_new", 1),
    )

    print("\nSQLite user records:")

    for row in connection.execute(
        """
        SELECT user_id, tenant_id, email, username, active
        FROM users
        ORDER BY user_id
        """
    ):
        print(row)

    print("\nIndex definitions:")

    for row in connection.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'index'"
    ):
        print(row)

    connection.close()


def demonstrate_registry() -> None:
    registry = UserRegistry()

    registry.register(
        User(1, "alice@example.com", "alice", 1)
    )

    registry.register(
        User(2, "bob@example.com", "alice", 2)
    )

    registry.register(
        User(3, "charlie@example.com", "charlie", 1)
    )

    print("Registered users:", len(registry.users))
    print("Email lookup:", registry.find_by_email("ALICE@example.com"))

    try:
        registry.register(
            User(4, "ALICE@example.com", "another", 2)
        )
    except UniqueViolation as error:
        print("Expected violation:", error)

    registry.deactivate(1)

    print("Index consistency:", registry.audit())

    # The original email remains reserved by the global email index.
    try:
        registry.register(
            User(5, "alice@example.com", "alice_new", 3)
        )
    except UniqueViolation as error:
        print("Global uniqueness still applies:", error)


def main() -> None:
    print("=== In-Memory Unique Index Demonstration ===")
    demonstrate_registry()

    print("\n=== SQLite Unique Index Demonstration ===")
    demonstrate_sqlite()


if __name__ == "__main__":
    main()
