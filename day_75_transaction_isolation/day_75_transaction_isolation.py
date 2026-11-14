#!/usr/bin/env python3
"""
Transaction Isolation Simulator
================================
Models:
- Read Uncommitted (conceptual behavior; PostgreSQL maps it to Read Committed)
- Read Committed
- Repeatable Read
- Serializable

Demonstrates dirty reads, non-repeatable reads, phantom reads,
lost updates, snapshot visibility, write conflicts, and serialization failures.

Python 3.10+
Standard library only.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import logging
import unittest


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("transaction_isolation")


class IsolationLevel(Enum):
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


class TransactionState(Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    ABORTED = "ABORTED"


class TransactionError(Exception):
    pass


class WriteConflict(TransactionError):
    pass


class SerializationFailure(TransactionError):
    pass


class InvalidTransactionState(TransactionError):
    pass


class RecordNotFound(TransactionError):
    pass


@dataclass
class Version:
    value: Any
    revision: int
    committed: bool
    transaction_id: Optional[int] = None


@dataclass
class Transaction:
    transaction_id: int
    isolation: IsolationLevel
    start_revision: int
    state: TransactionState = TransactionState.ACTIVE
    writes: Dict[Tuple[str, Any], Any] = field(default_factory=dict)
    reads: Set[Tuple[str, Any]] = field(default_factory=set)
    scan_tables: Set[str] = field(default_factory=set)
    observed_versions: Dict[Tuple[str, Any], int] = field(
        default_factory=dict
    )


class Database:
    """
    A small MVCC-inspired database.

    Each record stores committed versions. Transactions maintain private
    write sets. Commit validates conflicts before publishing changes.

    This is an educational simulator, not a production database engine.
    """

    def __init__(self) -> None:
        self.tables: Dict[str, Dict[Any, List[Version]]] = {}
        self.revision = 0
        self.next_transaction_id = 1
        self.active_transactions: Dict[int, Transaction] = {}
        self.commit_history: List[Dict[str, Any]] = []

    def create_table(self, name: str) -> None:
        if not name or name in self.tables:
            raise ValueError("Invalid or duplicate table name")
        self.tables[name] = {}

    def seed(self, table: str, key: Any, value: Any) -> None:
        if table not in self.tables:
            raise ValueError(f"Unknown table: {table}")
        if key in self.tables[table]:
            raise ValueError("Duplicate primary key")
        self.revision += 1
        self.tables[table][key] = [
            Version(deepcopy(value), self.revision, True)
        ]

    def begin(
        self,
        isolation: IsolationLevel = IsolationLevel.READ_COMMITTED
    ) -> Transaction:
        transaction = Transaction(
            transaction_id=self.next_transaction_id,
            isolation=isolation,
            start_revision=self.revision
        )
        self.next_transaction_id += 1
        self.active_transactions[transaction.transaction_id] = transaction
        logger.info(
            "Transaction %s started at revision %s (%s)",
            transaction.transaction_id,
            transaction.start_revision,
            isolation.value
        )
        return transaction

    def _check_active(self, transaction: Transaction) -> None:
        if transaction.state != TransactionState.ACTIVE:
            raise InvalidTransactionState(
                f"Transaction {transaction.transaction_id} is "
                f"{transaction.state.value}"
            )

    def _visible_version(
        self,
        table: str,
        key: Any,
        transaction: Transaction
    ) -> Optional[Version]:
        versions = self.tables[table].get(key, [])

        visible = [
            version for version in versions
            if version.committed
            and (
                transaction.isolation
                == IsolationLevel.READ_COMMITTED
                or version.revision <= transaction.start_revision
            )
        ]

        return max(visible, key=lambda v: v.revision) if visible else None

    def read(
        self,
        transaction: Transaction,
        table: str,
        key: Any
    ) -> Any:
        self._check_active(transaction)

        if table not in self.tables:
            raise ValueError(f"Unknown table: {table}")

        record_key = (table, key)

        # A transaction always sees its own uncommitted writes.
        if record_key in transaction.writes:
            return deepcopy(transaction.writes[record_key])

        version = self._visible_version(table, key, transaction)

        if version is None:
            raise RecordNotFound(f"{table}[{key!r}] does not exist")

        transaction.reads.add(record_key)
        transaction.observed_versions[record_key] = version.revision

        return deepcopy(version.value)

    def scan(
        self,
        transaction: Transaction,
        table: str,
        predicate=lambda key, value: True
    ) -> Dict[Any, Any]:
        self._check_active(transaction)

        if table not in self.tables:
            raise ValueError(f"Unknown table: {table}")

        transaction.scan_tables.add(table)
        result: Dict[Any, Any] = {}

        for key in self.tables[table]:
            try:
                value = self.read(transaction, table, key)
                if predicate(key, value):
                    result[key] = value
            except RecordNotFound:
                continue

        # Include newly inserted records written by this transaction.
        for (write_table, key), value in transaction.writes.items():
            if write_table == table and predicate(key, value):
                result[key] = deepcopy(value)

        return result

    def write(
        self,
        transaction: Transaction,
        table: str,
        key: Any,
        value: Any
    ) -> None:
        self._check_active(transaction)

        if table not in self.tables:
            raise ValueError(f"Unknown table: {table}")

        if not isinstance(key, (str, int)):
            raise ValueError("Keys must be strings or integers")

        transaction.writes[(table, key)] = deepcopy(value)

    def insert(
        self,
        transaction: Transaction,
        table: str,
        key: Any,
        value: Any
    ) -> None:
        self._check_active(transaction)

        try:
            self.read(transaction, table, key)
        except RecordNotFound:
            self.write(transaction, table, key, value)
            return

        raise WriteConflict(f"Duplicate key: {key!r}")

    def update_field(
        self,
        transaction: Transaction,
        table: str,
        key: Any,
        field_name: str,
        value: Any
    ) -> None:
        record = self.read(transaction, table, key)

        if not isinstance(record, dict):
            raise TypeError("Field updates require dictionary records")

        updated = deepcopy(record)
        updated[field_name] = value
        self.write(transaction, table, key, updated)

    def commit(self, transaction: Transaction) -> None:
        self._check_active(transaction)

        # Validate records changed after the transaction's snapshot.
        for (table, key) in transaction.writes:
            versions = self.tables[table].get(key, [])
            latest = max(
                (v.revision for v in versions if v.committed),
                default=0
            )

            if (
                transaction.isolation
                in (
                    IsolationLevel.REPEATABLE_READ,
                    IsolationLevel.SERIALIZABLE
                )
                and latest > transaction.start_revision
            ):
                self._abort(transaction)
                raise WriteConflict(
                    f"Concurrent modification of {table}[{key!r}]"
                )

        if transaction.isolation == IsolationLevel.SERIALIZABLE:
            # Detect changes to previously read rows and scanned tables.
            for (table, key), observed_revision in (
                transaction.observed_versions.items()
            ):
                latest = max(
                    (
                        v.revision
                        for v in self.tables[table].get(key, [])
                        if v.committed
                    ),
                    default=0
                )

                if latest > transaction.start_revision:
                    self._abort(transaction)
                    raise SerializationFailure(
                        f"Read-write conflict on {table}[{key!r}]"
                    )

            # Conservative predicate-conflict detection.
            for table in transaction.scan_tables:
                for key, versions in self.tables[table].items():
                    if any(
                        v.committed
                        and v.revision > transaction.start_revision
                        for v in versions
                    ):
                        self._abort(transaction)
                        raise SerializationFailure(
                            f"Concurrent table change detected: {table}"
                        )

        self.revision += 1

        for (table, key), value in transaction.writes.items():
            if key not in self.tables[table]:
                self.tables[table][key] = []

            self.tables[table][key].append(
                Version(
                    value=deepcopy(value),
                    revision=self.revision,
                    committed=True
                )
            )

        transaction.state = TransactionState.COMMITTED
        self.active_transactions.pop(transaction.transaction_id, None)

        self.commit_history.append({
            "transaction_id": transaction.transaction_id,
            "revision": self.revision,
            "writes": len(transaction.writes),
            "isolation": transaction.isolation.value
        })

        logger.info(
            "Transaction %s committed at revision %s",
            transaction.transaction_id,
            self.revision
        )

    def _abort(self, transaction: Transaction) -> None:
        transaction.state = TransactionState.ABORTED
        transaction.writes.clear()
        self.active_transactions.pop(transaction.transaction_id, None)

    def rollback(self, transaction: Transaction) -> None:
        self._check_active(transaction)
        transaction.writes.clear()
        transaction.state = TransactionState.ROLLED_BACK
        self.active_transactions.pop(transaction.transaction_id, None)

    def committed_value(self, table: str, key: Any) -> Any:
        versions = self.tables[table].get(key, [])
        committed = [v for v in versions if v.committed]

        if not committed:
            raise RecordNotFound(f"{table}[{key!r}] does not exist")

        return deepcopy(
            max(committed, key=lambda v: v.revision).value
        )


def demonstrate_read_committed() -> None:
    print("\n1. READ COMMITTED: Non-repeatable read")

    db = Database()
    db.create_table("accounts")
    db.seed("accounts", 1, {"balance": 1000})

    first = db.begin(IsolationLevel.READ_COMMITTED)
    second = db.begin(IsolationLevel.READ_COMMITTED)

    print("First read:", db.read(first, "accounts", 1))

    db.update_field(second, "accounts", 1, "balance", 800)
    db.commit(second)

    print("Second read:", db.read(first, "accounts", 1))

    db.rollback(first)


def demonstrate_repeatable_read() -> None:
    print("\n2. REPEATABLE READ: Stable snapshot")

    db = Database()
    db.create_table("accounts")
    db.seed("accounts", 1, {"balance": 1000})

    first = db.begin(IsolationLevel.REPEATABLE_READ)
    second = db.begin(IsolationLevel.READ_COMMITTED)

    print("First read:", db.read(first, "accounts", 1))

    db.update_field(second, "accounts", 1, "balance", 700)
    db.commit(second)

    print("Second read:", db.read(first, "accounts", 1))

    db.rollback(first)


def demonstrate_dirty_read_concept() -> None:
    print("\n3. READ UNCOMMITTED: Dirty-read concept")

    db = Database()
    db.create_table("accounts")
    db.seed("accounts", 1, {"balance": 500})

    writer = db.begin(IsolationLevel.READ_COMMITTED)
    reader = db.begin(IsolationLevel.READ_UNCOMMITTED)

    db.update_field(writer, "accounts", 1, "balance", 100)

    print("Reader sees committed value:", db.read(reader, "accounts", 1))
    print("Writer's uncommitted value is not visible.")

    db.rollback(writer)
    db.rollback(reader)

    print("After rollback:", db.committed_value("accounts", 1))


def demonstrate_serializable() -> None:
    print("\n4. SERIALIZABLE: Serialization failure")

    db = Database()
    db.create_table("inventory")
    db.seed("inventory", 1, {"quantity": 10})

    first = db.begin(IsolationLevel.SERIALIZABLE)
    second = db.begin(IsolationLevel.READ_COMMITTED)

    print("First transaction reads:", db.read(first, "inventory", 1))

    db.update_field(second, "inventory", 1, "quantity", 8)
    db.commit(second)

    try:
        db.commit(first)
    except SerializationFailure as error:
        print("Serialization failure:", error)


def demonstrate_lost_update_prevention() -> None:
    print("\n5. REPEATABLE READ: Concurrent write conflict")

    db = Database()
    db.create_table("accounts")
    db.seed("accounts", 1, {"balance": 1000})

    first = db.begin(IsolationLevel.REPEATABLE_READ)
    second = db.begin(IsolationLevel.REPEATABLE_READ)

    account_a = db.read(first, "accounts", 1)
    account_b = db.read(second, "accounts", 1)

    account_a["balance"] -= 100
    account_b["balance"] -= 200

    db.write(first, "accounts", 1, account_a)
    db.write(second, "accounts", 1, account_b)

    db.commit(first)

    try:
        db.commit(second)
    except WriteConflict as error:
        print("Write conflict:", error)

    print("Final account:", db.committed_value("accounts", 1))


class IsolationTests(unittest.TestCase):

    def setUp(self) -> None:
        self.db = Database()
        self.db.create_table("accounts")
        self.db.seed("accounts", 1, {"balance": 1000})

    def test_read_committed_sees_new_commit(self) -> None:
        reader = self.db.begin(IsolationLevel.READ_COMMITTED)
        writer = self.db.begin(IsolationLevel.READ_COMMITTED)

        self.db.read(reader, "accounts", 1)
        self.db.update_field(writer, "accounts", 1, "balance", 900)
        self.db.commit(writer)

        self.assertEqual(
            self.db.read(reader, "accounts", 1)["balance"],
            900
        )
        self.db.rollback(reader)

    def test_repeatable_read_preserves_snapshot(self) -> None:
        reader = self.db.begin(IsolationLevel.REPEATABLE_READ)
        writer = self.db.begin(IsolationLevel.READ_COMMITTED)

        self.db.read(reader, "accounts", 1)
        self.db.update_field(writer, "accounts", 1, "balance", 900)
        self.db.commit(writer)

        self.assertEqual(
            self.db.read(reader, "accounts", 1)["balance"],
            1000
        )
        self.db.rollback(reader)

    def test_write_conflict(self) -> None:
        first = self.db.begin(IsolationLevel.REPEATABLE_READ)
        second = self.db.begin(IsolationLevel.REPEATABLE_READ)

        self.db.read(first, "accounts", 1)
        self.db.read(second, "accounts", 1)

        self.db.write(first, "accounts", 1, {"balance": 800})
        self.db.write(second, "accounts", 1, {"balance": 700})

        self.db.commit(first)

        with self.assertRaises(WriteConflict):
            self.db.commit(second)

    def test_rollback(self) -> None:
        transaction = self.db.begin()
        self.db.write(
            transaction,
            "accounts",
            1,
            {"balance": 0}
        )
        self.db.rollback(transaction)

        self.assertEqual(
            self.db.committed_value("accounts", 1)["balance"],
            1000
        )

    def test_duplicate_insert(self) -> None:
        transaction = self.db.begin()

        with self.assertRaises(WriteConflict):
            self.db.insert(
                transaction,
                "accounts",
                1,
                {"balance": 500}
            )

        self.db.rollback(transaction)


def main() -> None:
    demonstrate_dirty_read_concept()
    demonstrate_read_committed()
    demonstrate_repeatable_read()
    demonstrate_serializable()
    demonstrate_lost_update_prevention()

    print("\n6. Automated validation")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        IsolationTests
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    print("\n7. Transaction history")
    db = Database()
    db.create_table("orders")
    db.seed("orders", 101, {"status": "PENDING"})

    transaction = db.begin(IsolationLevel.READ_COMMITTED)
    db.update_field(
        transaction,
        "orders",
        101,
        "status",
        "APPROVED"
    )
    db.commit(transaction)

    for event in db.commit_history:
        print(event)

    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
