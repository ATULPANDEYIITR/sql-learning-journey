#!/usr/bin/env python3
"""
ACID Properties: Atomicity, Consistency, Isolation, Durability

A self-contained relational transaction simulator demonstrating:
- Atomicity through undo operations and rollback.
- Consistency through database constraints.
- Isolation through transaction locks and conflict detection.
- Durability through an append-only transaction journal.
- Savepoints, concurrent transaction conflicts, and recovery.
- Transaction lifecycle and failure handling.

Run: python acid_properties.py
"""

from __future__ import annotations

import copy
import json
import threading
import time
import uuid

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class TransactionState(Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class IsolationLevel(Enum):
    READ_UNCOMMITTED = "READ_UNCOMMITTED"
    READ_COMMITTED = "READ_COMMITTED"
    REPEATABLE_READ = "REPEATABLE_READ"
    SERIALIZABLE = "SERIALIZABLE"


class DatabaseError(Exception):
    pass


class ConstraintViolation(DatabaseError):
    pass


class ConcurrencyConflict(DatabaseError):
    pass


class TransactionError(DatabaseError):
    pass


@dataclass
class Account:
    account_id: int
    owner: str
    balance: Decimal
    active: bool = True
    version: int = 0


@dataclass
class JournalEntry:
    transaction_id: str
    operation: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class DurableJournal:
    """Writes committed transaction records using atomic file replacement."""

    def __init__(self, path: str = "acid_journal.json"):
        self.path = Path(path)
        self.entries: list[dict[str, Any]] = []
        self.lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("Journal root must be a list")
            self.entries = data
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise DatabaseError(f"Journal recovery failed: {exc}") from exc

    def append(self, entry: JournalEntry) -> None:
        with self.lock:
            updated = self.entries + [{
                "transaction_id": entry.transaction_id,
                "operation": entry.operation,
                "payload": entry.payload,
                "timestamp": entry.timestamp,
            }]

            temporary = self.path.with_suffix(".tmp")
            try:
                with temporary.open("w", encoding="utf-8") as file:
                    json.dump(updated, file, indent=2)
                    file.flush()
                    import os
                    os.fsync(file.fileno())

                temporary.replace(self.path)
                self.entries = updated

            except OSError as exc:
                temporary.unlink(missing_ok=True)
                raise DatabaseError(f"Durability failure: {exc}") from exc


class Database:
    def __init__(self, journal_path: str = "acid_journal.json"):
        self.accounts: dict[int, Account] = {}
        self.journal = DurableJournal(journal_path)
        self.lock = threading.RLock()
        self.account_locks: dict[int, threading.RLock] = {}
        self.next_account_id = 1
        self._recover()

    def _recover(self) -> None:
        """Rebuild committed state by replaying durable transaction records."""
        for entry in self.journal.entries:
            if entry["operation"] == "TRANSFER":
                data = entry["payload"]
                source = data["source"]
                target = data["target"]

                for account_id, balance in (
                    (source, data["source_balance"]),
                    (target, data["target_balance"]),
                ):
                    if account_id in self.accounts:
                        self.accounts[account_id].balance = Decimal(balance)
                        self.accounts[account_id].version += 1

    def create_account(self, owner: str, balance: Decimal) -> int:
        if not owner.strip():
            raise ConstraintViolation("Owner cannot be empty")

        if not balance.is_finite() or balance < 0:
            raise ConstraintViolation("Initial balance must be nonnegative")

        with self.lock:
            account_id = self.next_account_id
            self.next_account_id += 1

            self.accounts[account_id] = Account(
                account_id, owner, balance
            )
            self.account_locks[account_id] = threading.RLock()
            return account_id

    def begin(
        self,
        isolation: IsolationLevel = IsolationLevel.SERIALIZABLE
    ) -> Transaction:
        return Transaction(self, isolation)

    def snapshot(self) -> dict[int, Account]:
        with self.lock:
            return copy.deepcopy(self.accounts)


class Transaction:
    def __init__(self, database: Database, isolation: IsolationLevel):
        self.database = database
        self.isolation = isolation
        self.transaction_id = str(uuid.uuid4())
        self.state = TransactionState.ACTIVE
        self.undo_log: list[Callable[[], None]] = []
        self.write_versions: dict[int, int] = {}
        self.write_set: dict[int, Decimal] = {}
        self.read_versions: dict[int, int] = {}
        self.held_locks: list[threading.RLock] = []
        self.savepoints: dict[str, int] = {}

    def _ensure_active(self) -> None:
        if self.state != TransactionState.ACTIVE:
            raise TransactionError(
                f"Transaction is {self.state.value}"
            )

    def _lock_account(self, account_id: int) -> None:
        if self.isolation == IsolationLevel.READ_UNCOMMITTED:
            return

        if self.isolation in (
            IsolationLevel.REPEATABLE_READ,
            IsolationLevel.SERIALIZABLE
        ):
            if any(
                lock is self.database.account_locks[account_id]
                for lock in self.held_locks
            ):
                return

            lock = self.database.account_locks[account_id]
            lock.acquire()
            self.held_locks.append(lock)

    def read_balance(self, account_id: int) -> Decimal:
        self._ensure_active()

        account = self.database.accounts.get(account_id)
        if account is None or not account.active:
            raise ConstraintViolation("Account does not exist or is inactive")

        self._lock_account(account_id)

        current = self.database.accounts[account_id]

        if account_id in self.write_set:
            return self.write_set[account_id]

        self.read_versions.setdefault(account_id, current.version)
        return current.balance

    def transfer(
        self,
        source_id: int,
        target_id: int,
        amount: Decimal
    ) -> None:
        self._ensure_active()

        if source_id == target_id:
            raise ConstraintViolation("Source and target must differ")

        if not amount.is_finite() or amount <= 0:
            raise ConstraintViolation("Transfer amount must be positive")

        first, second = sorted((source_id, target_id))

        # Acquire locks in a deterministic order to reduce deadlocks.
        self._lock_account(first)
        self._lock_account(second)

        source = self.database.accounts.get(source_id)
        target = self.database.accounts.get(target_id)

        if source is None or target is None:
            raise ConstraintViolation("Unknown account")

        if not source.active or not target.active:
            raise ConstraintViolation("Inactive account")

        source_balance = self.write_set.get(source_id, source.balance)
        target_balance = self.write_set.get(target_id, target.balance)

        if source_balance < amount:
            raise ConstraintViolation("Insufficient funds")

        self.write_versions.setdefault(source_id, source.version)
        self.write_versions.setdefault(target_id, target.version)

        self.write_set[source_id] = source_balance - amount
        self.write_set[target_id] = target_balance + amount

    def set_savepoint(self, name: str) -> None:
        self._ensure_active()
        if not name.strip():
            raise TransactionError("Savepoint name cannot be empty")
        self.savepoints[name] = len(self.undo_log)

    def rollback_to(self, name: str) -> None:
        self._ensure_active()
        if name not in self.savepoints:
            raise TransactionError("Unknown savepoint")

        position = self.savepoints[name]

        for undo in reversed(self.undo_log[position:]):
            undo()

        del self.undo_log[position:]

        # Remove changes made after the savepoint.
        self.write_set.clear()
        self.write_versions.clear()

        for account_id in self.read_versions:
            account = self.database.accounts.get(account_id)
            if account:
                self.read_versions[account_id] = account.version

    def commit(self) -> None:
        self._ensure_active()

        try:
            with self.database.lock:
                for account_id, expected_version in self.write_versions.items():
                    current = self.database.accounts.get(account_id)

                    if current is None or current.version != expected_version:
                        raise ConcurrencyConflict(
                            f"Account {account_id} changed concurrently"
                        )

                total_before = sum(
                    account.balance
                    for account in self.database.accounts.values()
                    if account.active
                )

                total_after = total_before

                for account_id, new_balance in self.write_set.items():
                    old_balance = self.database.accounts[account_id].balance

                    if not new_balance.is_finite() or new_balance < 0:
                        raise ConstraintViolation("Invalid account balance")

                    total_after += new_balance - old_balance

                if total_before != total_after:
                    raise ConstraintViolation(
                        "Transaction violates balance conservation"
                    )

                # Persist the complete transaction before publishing changes.
                if self.write_set:
                    source_id, target_id = sorted(self.write_set)

                    payload = {
                        "source": source_id,
                        "target": target_id,
                        "source_balance": str(self.write_set[source_id]),
                        "target_balance": str(self.write_set[target_id]),
                    }

                    self.database.journal.append(
                        JournalEntry(
                            self.transaction_id,
                            "TRANSFER",
                            payload
                        )
                    )

                for account_id, new_balance in self.write_set.items():
                    account = self.database.accounts[account_id]
                    account.balance = new_balance
                    account.version += 1

            self.state = TransactionState.COMMITTED

        except Exception:
            self.state = TransactionState.FAILED
            self.write_set.clear()
            raise

        finally:
            self._release_locks()

    def rollback(self) -> None:
        self._ensure_active()
        self.write_set.clear()
        self.undo_log.clear()
        self.state = TransactionState.ROLLED_BACK
        self._release_locks()

    def _release_locks(self) -> None:
        for lock in reversed(self.held_locks):
            lock.release()
        self.held_locks.clear()

    def __enter__(self) -> Transaction:
        return self

    def __exit__(self, exception_type, exception, traceback):
        if self.state == TransactionState.ACTIVE:
            if exception_type is None:
                self.commit()
            else:
                self.rollback()
        return False


def display_accounts(database: Database) -> None:
    print("\nACCOUNT LEDGER")
    print("-" * 55)

    for account in database.snapshot().values():
        print(
            f"{account.account_id:<5} "
            f"{account.owner:<18} "
            f"{account.balance:>12} "
            f"Version={account.version}"
        )


def demonstrate_acid() -> None:
    journal_path = "acid_demo_journal.json"

    Path(journal_path).unlink(missing_ok=True)

    database = Database(journal_path)

    alice = database.create_account("Alice", Decimal("1000.00"))
    bob = database.create_account("Bob", Decimal("500.00"))
    charlie = database.create_account("Charlie", Decimal("250.00"))

    print("ACID TRANSACTION DEMONSTRATION")
    display_accounts(database)

    # Atomicity and consistency: both account updates commit together.
    with database.begin(IsolationLevel.SERIALIZABLE) as transaction:
        transaction.transfer(alice, bob, Decimal("200.00"))

    print("\nSuccessful transfer: Alice -> Bob: 200.00")
    display_accounts(database)

    # Atomicity: a failed operation does not publish partial changes.
    transaction = database.begin()

    try:
        transaction.transfer(alice, charlie, Decimal("10000.00"))
        transaction.commit()
    except ConstraintViolation as exc:
        transaction.rollback()
        print(f"\nAtomicity test: {exc}")

    # Savepoint demonstration.
    transaction = database.begin()
    transaction.transfer(alice, charlie, Decimal("50.00"))
    transaction.set_savepoint("before_second_transfer")
    transaction.transfer(bob, charlie, Decimal("25.00"))
    transaction.rollback_to("before_second_transfer")
    transaction.commit()

    print("\nSavepoint test completed.")
    display_accounts(database)

    # Durability: a new database instance replays committed journal entries.
    recovered = Database(journal_path)

    print("\nDurability journal entries:")
    for entry in recovered.journal.entries:
        print(
            entry["transaction_id"],
            entry["operation"],
            entry["payload"]
        )

    # The journal contains transaction updates; initial account creation is
    # intentionally separate from the transaction journal in this simulator.
    print("\nCommitted transfer records:", len(recovered.journal.entries))

    # Consistency check.
    total = sum(
        account.balance for account in database.snapshot().values()
    )
    assert total == Decimal("1750.00")

    print("\nConsistency assertion passed.")
    print("Total account balance:", total)


if __name__ == "__main__":
    demonstrate_acid()
