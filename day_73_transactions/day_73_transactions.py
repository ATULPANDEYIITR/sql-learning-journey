from __future__ import annotations

import copy
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("transaction_engine")


class TransactionState(Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"


class TransactionError(Exception):
    pass


class InsufficientFunds(TransactionError):
    pass


class ConstraintViolation(TransactionError):
    pass


class TransactionNotActive(TransactionError):
    pass


@dataclass
class Account:
    account_id: str
    owner: str
    balance: Decimal
    currency: str = "INR"

    def __post_init__(self):
        if not self.account_id or not self.owner:
            raise ValueError("Account identifiers and owners are required")
        if self.balance < 0:
            raise ValueError("Initial balance cannot be negative")


@dataclass
class LedgerEntry:
    transaction_id: str
    account_id: str
    amount: Decimal
    entry_type: str
    description: str


@dataclass
class Transaction:
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: TransactionState = TransactionState.ACTIVE
    operations: list[dict[str, Any]] = field(default_factory=list)
    started_at: str = ""


class TransactionalBank:
    """
    In-memory transaction simulator.

    A transaction works on a private snapshot and publishes its
    changes only after validation. A lock serializes commits.
    """

    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.ledger: list[LedgerEntry] = []
        self.transactions: dict[str, Transaction] = {}
        self._lock = threading.RLock()
        self._version = 0

    def create_account(
        self,
        account_id: str,
        owner: str,
        balance: Decimal
    ) -> None:
        with self._lock:
            if account_id in self.accounts:
                raise ConstraintViolation("Account already exists")

            self.accounts[account_id] = Account(
                account_id,
                owner,
                Decimal(balance)
            )
            self._version += 1

    def get_balance(self, account_id: str) -> Decimal:
        with self._lock:
            if account_id not in self.accounts:
                raise KeyError(f"Unknown account: {account_id}")
            return self.accounts[account_id].balance

    def begin(self) -> Transaction:
        with self._lock:
            transaction = Transaction()
            transaction.started_at = str(uuid.uuid4())
            self.transactions[transaction.transaction_id] = transaction
            logger.info("BEGIN %s", transaction.transaction_id)
            return transaction

    def _require_active(self, transaction: Transaction):
        if transaction.state != TransactionState.ACTIVE:
            raise TransactionNotActive(
                f"Transaction is {transaction.state.value}"
            )

    def transfer(
        self,
        transaction: Transaction,
        source: str,
        destination: str,
        amount: Decimal
    ) -> None:
        self._require_active(transaction)

        amount = Decimal(amount)

        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        if source == destination:
            raise ConstraintViolation(
                "Source and destination must differ"
            )

        with self._lock:
            if source not in self.accounts or destination not in self.accounts:
                raise KeyError("Source or destination account does not exist")

            source_account = self.accounts[source]
            destination_account = self.accounts[destination]

            if source_account.currency != destination_account.currency:
                raise ConstraintViolation("Currency mismatch")

            if source_account.balance < amount:
                raise InsufficientFunds("Insufficient account balance")

            transaction.operations.append({
                "type": "TRANSFER",
                "source": source,
                "destination": destination,
                "amount": amount
            })

        logger.info(
            "Staged transfer: %s -> %s: %s",
            source, destination, amount
        )

    def deposit(
        self,
        transaction: Transaction,
        account_id: str,
        amount: Decimal
    ) -> None:
        self._require_active(transaction)
        amount = Decimal(amount)

        if amount <= 0:
            raise ValueError("Deposit must be positive")

        with self._lock:
            if account_id not in self.accounts:
                raise KeyError("Account does not exist")

            transaction.operations.append({
                "type": "DEPOSIT",
                "account": account_id,
                "amount": amount
            })

    def withdraw(
        self,
        transaction: Transaction,
        account_id: str,
        amount: Decimal
    ) -> None:
        self._require_active(transaction)
        amount = Decimal(amount)

        if amount <= 0:
            raise ValueError("Withdrawal must be positive")

        with self._lock:
            if account_id not in self.accounts:
                raise KeyError("Account does not exist")

            transaction.operations.append({
                "type": "WITHDRAW",
                "account": account_id,
                "amount": amount
            })

    def commit(self, transaction: Transaction) -> None:
        self._require_active(transaction)

        with self._lock:
            # Work on a private copy so failed operations cannot
            # partially modify the published account balances.
            balances = {
                key: account.balance
                for key, account in self.accounts.items()
            }

            pending_entries = []

            try:
                for operation in transaction.operations:
                    operation_type = operation["type"]

                    if operation_type == "TRANSFER":
                        source = operation["source"]
                        destination = operation["destination"]
                        amount = operation["amount"]

                        if balances[source] < amount:
                            raise InsufficientFunds(
                                f"Insufficient funds in {source}"
                            )

                        balances[source] -= amount
                        balances[destination] += amount

                        pending_entries.extend([
                            LedgerEntry(
                                transaction.transaction_id,
                                source,
                                -amount,
                                "TRANSFER_OUT",
                                f"Transfer to {destination}"
                            ),
                            LedgerEntry(
                                transaction.transaction_id,
                                destination,
                                amount,
                                "TRANSFER_IN",
                                f"Transfer from {source}"
                            )
                        ])

                    elif operation_type == "DEPOSIT":
                        account = operation["account"]
                        amount = operation["amount"]
                        balances[account] += amount

                        pending_entries.append(
                            LedgerEntry(
                                transaction.transaction_id,
                                account,
                                amount,
                                "DEPOSIT",
                                "Account deposit"
                            )
                        )

                    elif operation_type == "WITHDRAW":
                        account = operation["account"]
                        amount = operation["amount"]

                        if balances[account] < amount:
                            raise InsufficientFunds(
                                f"Insufficient funds in {account}"
                            )

                        balances[account] -= amount

                        pending_entries.append(
                            LedgerEntry(
                                transaction.transaction_id,
                                account,
                                -amount,
                                "WITHDRAWAL",
                                "Account withdrawal"
                            )
                        )

                    else:
                        raise ConstraintViolation(
                            "Unsupported operation"
                        )

                # Atomic publication occurs only after all operations pass.
                for account_id, balance in balances.items():
                    if balance < 0:
                        raise ConstraintViolation(
                            "Negative account balance detected"
                        )
                    self.accounts[account_id].balance = balance

                self.ledger.extend(pending_entries)
                self._version += 1
                transaction.state = TransactionState.COMMITTED

                logger.info(
                    "COMMIT %s",
                    transaction.transaction_id
                )

            except Exception:
                transaction.state = TransactionState.ROLLED_BACK
                logger.exception("Transaction failed and was rolled back")
                raise

    def rollback(self, transaction: Transaction) -> None:
        self._require_active(transaction)

        with self._lock:
            transaction.operations.clear()
            transaction.state = TransactionState.ROLLED_BACK

        logger.info("ROLLBACK %s", transaction.transaction_id)

    def execute(
        self,
        operations: list[Callable[[Transaction], None]]
    ) -> Transaction:
        transaction = self.begin()

        try:
            for operation in operations:
                operation(transaction)

            self.commit(transaction)

        except Exception:
            if transaction.state == TransactionState.ACTIVE:
                self.rollback(transaction)
            raise

        return transaction

    def save_report(self, filename: str) -> None:
        with self._lock:
            report = {
                "version": self._version,
                "accounts": [
                    {
                        "account_id": account.account_id,
                        "owner": account.owner,
                        "balance": str(account.balance),
                        "currency": account.currency
                    }
                    for account in self.accounts.values()
                ],
                "ledger": [
                    {
                        "transaction_id": entry.transaction_id,
                        "account_id": entry.account_id,
                        "amount": str(entry.amount),
                        "type": entry.entry_type,
                        "description": entry.description
                    }
                    for entry in self.ledger
                ]
            }

        path = Path(filename)
        temporary = path.with_suffix(path.suffix + ".tmp")

        temporary.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8"
        )
        temporary.replace(path)

    def display(self) -> None:
        print("\nACCOUNT BALANCES")

        for account in self.accounts.values():
            print(
                f"{account.account_id}: "
                f"{account.owner}: "
                f"{account.balance} {account.currency}"
            )

        print(f"Ledger entries: {len(self.ledger)}")


def demonstrate_transactions():
    bank = TransactionalBank()

    bank.create_account("A100", "Alice", Decimal("10000.00"))
    bank.create_account("A200", "Bob", Decimal("5000.00"))
    bank.create_account("A300", "Charlie", Decimal("2000.00"))

    print("\n1. Successful transaction")

    transaction = bank.begin()
    bank.transfer(
        transaction,
        "A100",
        "A200",
        Decimal("1500.00")
    )
    bank.deposit(
        transaction,
        "A300",
        Decimal("500.00")
    )
    bank.commit(transaction)

    bank.display()

    print("\n2. Explicit rollback")

    transaction = bank.begin()
    bank.withdraw(
        transaction,
        "A100",
        Decimal("1000.00")
    )
    bank.rollback(transaction)

    bank.display()

    print("\n3. Failed transaction")

    transaction = bank.begin()

    try:
        bank.withdraw(
            transaction,
            "A200",
            Decimal("100000.00")
        )
        bank.commit(transaction)
    except TransactionError as error:
        print("Expected failure:", error)

    bank.display()

    print("\n4. Multiple operations in one transaction")

    transaction = bank.begin()

    bank.deposit(
        transaction,
        "A100",
        Decimal("250.00")
    )
    bank.withdraw(
        transaction,
        "A300",
        Decimal("100.00")
    )

    bank.commit(transaction)
    bank.display()

    print("\n5. Invalid operation")

    transaction = bank.begin()

    try:
        bank.deposit(
            transaction,
            "A100",
            Decimal("-50.00")
        )
    except ValueError as error:
        bank.rollback(transaction)
        print("Validation failure:", error)

    print("\n6. Persistent report")

    bank.save_report("transaction_report.json")
    print("Report saved to transaction_report.json")

    # Accounting invariant: total funds remain unchanged
    # by transfers, but deposits and withdrawals change totals.
    total = sum(
        (account.balance for account in bank.accounts.values()),
        Decimal("0.00")
    )

    assert total == Decimal("14250.00")
    assert all(account.balance >= 0 for account in bank.accounts.values())

    print("\nAll transaction demonstrations completed.")
    print("Final total balance:", total)


if __name__ == "__main__":
    demonstrate_transactions()
