#!/usr/bin/env python3
"""
Concurrency, Locks, Concurrent Transactions, and Race Conditions.

Demonstrates:
- Thread synchronization
- Race conditions and lost updates
- Mutex locks and critical sections
- Deadlock prevention through ordered locking
- Atomic bank transfers
- Transaction rollback
- Idempotency
- Optimistic concurrency control
- Thread-safe shared state
- Concurrent invariant testing

Python 3.10+
Standard library only.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(threadName)s %(message)s",
)

logger = logging.getLogger("concurrency")


class TransactionError(Exception):
    """Base exception for transaction failures."""


class InsufficientFunds(TransactionError):
    pass


class AccountNotFound(TransactionError):
    pass


class DuplicateTransaction(TransactionError):
    pass


class ConcurrentModification(TransactionError):
    pass


class TransactionStatus(Enum):
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class Account:
    account_id: str
    balance: float
    version: int = 0
    lock: threading.RLock = field(
        default_factory=threading.RLock,
        repr=False,
        compare=False,
    )

    def __post_init__(self):
        if not self.account_id:
            raise ValueError("Account ID cannot be empty")

        if self.balance < 0:
            raise ValueError("Initial balance cannot be negative")


@dataclass(frozen=True)
class TransactionResult:
    transaction_id: str
    status: TransactionStatus
    source: str
    destination: str
    amount: float
    message: str


class Bank:
    """
    Thread-safe banking service.

    Lock ordering prevents circular wait between concurrent transfers.
    Account updates occur only after all validation succeeds.
    """

    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self._registry_lock = threading.RLock()
        self._transaction_lock = threading.RLock()
        self._processed: dict[str, TransactionResult] = {}

    def add_account(self, account_id: str, balance: float):
        with self._registry_lock:
            if account_id in self.accounts:
                raise ValueError("Account already exists")

            self.accounts[account_id] = Account(
                account_id=account_id,
                balance=balance,
            )

    def get_account(self, account_id: str) -> Account:
        with self._registry_lock:
            account = self.accounts.get(account_id)

        if account is None:
            raise AccountNotFound(account_id)

        return account

    def get_balance(self, account_id: str) -> float:
        account = self.get_account(account_id)

        with account.lock:
            return account.balance

    def transfer(
        self,
        source_id: str,
        destination_id: str,
        amount: float,
        idempotency_key: str | None = None,
    ) -> TransactionResult:

        if source_id == destination_id:
            raise ValueError("Source and destination must differ")

        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        if idempotency_key is None:
            idempotency_key = str(uuid.uuid4())

        if not idempotency_key.strip():
            raise ValueError("Invalid idempotency key")

        # Serializes duplicate transaction requests.
        with self._transaction_lock:
            existing = self._processed.get(idempotency_key)

            if existing is not None:
                if (
                    existing.source != source_id
                    or existing.destination != destination_id
                    or existing.amount != amount
                ):
                    raise DuplicateTransaction(
                        "Idempotency key reused with different parameters"
                    )

                return existing

            source = self.get_account(source_id)
            destination = self.get_account(destination_id)

            # A consistent lock order prevents deadlocks.
            first, second = sorted(
                (source, destination),
                key=lambda account: account.account_id,
            )

            with first.lock:
                with second.lock:
                    if source.balance < amount:
                        result = TransactionResult(
                            str(uuid.uuid4()),
                            TransactionStatus.REJECTED,
                            source_id,
                            destination_id,
                            amount,
                            "Insufficient funds",
                        )

                        self._processed[idempotency_key] = result
                        return result

                    # Preserve original state for rollback.
                    old_source = source.balance
                    old_destination = destination.balance

                    try:
                        source.balance -= amount
                        destination.balance += amount

                        source.version += 1
                        destination.version += 1

                        if source.balance < 0:
                            raise TransactionError(
                                "Account balance invariant violated"
                            )

                    except Exception:
                        source.balance = old_source
                        destination.balance = old_destination
                        raise

                    result = TransactionResult(
                        str(uuid.uuid4()),
                        TransactionStatus.COMMITTED,
                        source_id,
                        destination_id,
                        amount,
                        "Transfer committed",
                    )

                    self._processed[idempotency_key] = result
                    return result

    def total_balance(self) -> float:
        accounts = sorted(
            self.accounts.values(),
            key=lambda account: account.account_id,
        )

        # Lock every account in deterministic order.
        for account in accounts:
            account.lock.acquire()

        try:
            return sum(account.balance for account in accounts)
        finally:
            for account in reversed(accounts):
                account.lock.release()


class OptimisticAccount:
    """
    Version-based concurrency control.

    Updates succeed only when the expected version matches
    the current version.
    """

    def __init__(self, balance: float):
        if balance < 0:
            raise ValueError("Invalid initial balance")

        self.balance = balance
        self.version = 0
        self._lock = threading.Lock()

    def read(self) -> tuple[float, int]:
        with self._lock:
            return self.balance, self.version

    def update(
        self,
        expected_version: int,
        new_balance: float,
    ) -> int:

        if new_balance < 0:
            raise ValueError("Balance cannot be negative")

        with self._lock:
            if self.version != expected_version:
                raise ConcurrentModification(
                    "Account changed during transaction"
                )

            self.balance = new_balance
            self.version += 1

            return self.version


class UnsafeCounter:
    """Intentionally unsafe example illustrating a lost update."""

    def __init__(self):
        self.value = 0

    def increment(self):
        current = self.value
        time.sleep(0.00001)
        self.value = current + 1


class SafeCounter:
    """Thread-safe counter using mutual exclusion."""

    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self.value += 1


def demonstrate_race_conditions():
    print("\n--- Race Condition Demonstration ---")

    unsafe = UnsafeCounter()

    with ThreadPoolExecutor(max_workers=12) as executor:
        list(
            executor.map(
                lambda _: unsafe.increment(),
                range(1000),
            )
        )

    print("Unsafe counter:", unsafe.value)
    print("Expected counter: 1000")

    safe = SafeCounter()

    with ThreadPoolExecutor(max_workers=12) as executor:
        list(
            executor.map(
                lambda _: safe.increment(),
                range(1000),
            )
        )

    print("Safe counter:", safe.value)

    assert safe.value == 1000


def demonstrate_concurrent_transfers():
    print("\n--- Concurrent Transactions ---")

    bank = Bank()

    bank.add_account("ACCOUNT-A", 10000)
    bank.add_account("ACCOUNT-B", 10000)
    bank.add_account("ACCOUNT-C", 5000)

    initial_total = bank.total_balance()

    def execute_transfer(index: int):
        if index % 2 == 0:
            return bank.transfer(
                "ACCOUNT-A",
                "ACCOUNT-B",
                10,
                f"TX-{index}",
            )

        return bank.transfer(
            "ACCOUNT-B",
            "ACCOUNT-A",
            10,
            f"TX-{index}",
        )

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(
            executor.map(execute_transfer, range(500))
        )

    committed = sum(
        result.status == TransactionStatus.COMMITTED
        for result in results
    )

    print("Committed transactions:", committed)
    print("Account A:", bank.get_balance("ACCOUNT-A"))
    print("Account B:", bank.get_balance("ACCOUNT-B"))
    print("Account C:", bank.get_balance("ACCOUNT-C"))
    print("Initial total:", initial_total)
    print("Final total:", bank.total_balance())

    assert bank.total_balance() == initial_total
    assert all(
        bank.get_balance(account_id) >= 0
        for account_id in bank.accounts
    )


def demonstrate_idempotency():
    print("\n--- Idempotency ---")

    bank = Bank()
    bank.add_account("A", 1000)
    bank.add_account("B", 500)

    first = bank.transfer("A", "B", 100, "PAYMENT-001")
    second = bank.transfer("A", "B", 100, "PAYMENT-001")

    assert first == second
    assert bank.get_balance("A") == 900
    assert bank.get_balance("B") == 600

    print("Duplicate request returned original result")
    print("Account A:", bank.get_balance("A"))
    print("Account B:", bank.get_balance("B"))

    try:
        bank.transfer("A", "B", 200, "PAYMENT-001")
    except DuplicateTransaction as error:
        print("Rejected key reuse:", error)


def demonstrate_optimistic_locking():
    print("\n--- Optimistic Concurrency Control ---")

    account = OptimisticAccount(1000)

    balance, version = account.read()

    print("Read balance:", balance)
    print("Read version:", version)

    account.update(version, 1200)

    try:
        account.update(version, 1500)
    except ConcurrentModification as error:
        print("Stale update rejected:", error)

    print("Current state:", account.read())


def demonstrate_transaction_failures():
    print("\n--- Transaction Failure Handling ---")

    bank = Bank()
    bank.add_account("A", 100)
    bank.add_account("B", 50)

    result = bank.transfer("A", "B", 500, "FAILED-001")

    assert result.status == TransactionStatus.REJECTED
    assert bank.get_balance("A") == 100
    assert bank.get_balance("B") == 50

    print("Status:", result.status.value)
    print("Reason:", result.message)

    try:
        bank.transfer("A", "B", -10)
    except ValueError as error:
        print("Validation rejected:", error)


def main():
    print("=" * 65)
    print("CONCURRENCY AND TRANSACTION MANAGEMENT")
    print("=" * 65)

    demonstrate_race_conditions()
    demonstrate_concurrent_transfers()
    demonstrate_idempotency()
    demonstrate_optimistic_locking()
    demonstrate_transaction_failures()

    print("\nAll concurrency invariants verified.")


if __name__ == "__main__":
    main()
