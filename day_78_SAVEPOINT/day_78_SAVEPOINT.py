#!/usr/bin/env python3
"""
SAVEPOINT: Partial Rollback and Nested Transaction Patterns

Demonstrates:
- Transaction boundaries and savepoints
- Partial rollback using ROLLBACK TO SAVEPOINT
- Releasing savepoints
- Nested transaction patterns using savepoint stacks
- Atomic operations and exception handling
- Transaction state management
- Resource reservation and order processing
- Transaction isolation concepts and failure simulation

Requires Python 3.10 or later.
Uses only the Python standard library.
"""

from __future__ import annotations

import copy
import logging
import unittest
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Callable


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("savepoint")


class TransactionError(Exception):
    """Base transaction exception."""


class InvalidTransactionState(TransactionError):
    """Raised when an operation violates transaction state."""


class SavepointNotFound(TransactionError):
    """Raised when a requested savepoint does not exist."""


class InsufficientInventory(TransactionError):
    """Raised when requested inventory is unavailable."""


class InsufficientFunds(TransactionError):
    """Raised when an account cannot cover a payment."""


class TransactionStatus(Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class Product:
    product_id: int
    name: str
    stock: int
    price: Decimal

    def __post_init__(self):
        if self.product_id <= 0:
            raise ValueError("Product ID must be positive.")
        if not self.name.strip():
            raise ValueError("Product name cannot be empty.")
        if self.stock < 0:
            raise ValueError("Stock cannot be negative.")
        if self.price <= 0:
            raise ValueError("Price must be positive.")


@dataclass
class Account:
    account_id: int
    owner: str
    balance: Decimal

    def __post_init__(self):
        if self.account_id <= 0:
            raise ValueError("Account ID must be positive.")
        if self.balance < 0:
            raise ValueError("Balance cannot be negative.")


@dataclass
class Order:
    order_id: int
    account_id: int
    product_id: int
    quantity: int
    amount: Decimal
    status: str = "PENDING"


@dataclass
class DatabaseState:
    products: dict[int, Product] = field(default_factory=dict)
    accounts: dict[int, Account] = field(default_factory=dict)
    orders: dict[int, Order] = field(default_factory=dict)
    audit_log: list[str] = field(default_factory=list)
    next_order_id: int = 1


@dataclass
class Savepoint:
    name: str
    snapshot: DatabaseState


class Transaction:
    """
    In-memory transaction simulator.

    Snapshots represent transaction-local state. A real database uses
    transaction logs, MVCC, or equivalent mechanisms rather than
    necessarily copying the entire database.
    """

    def __init__(self, database: "Database"):
        self.database = database
        self.working_state = copy.deepcopy(database.state)
        self.savepoints: list[Savepoint] = []
        self.status = TransactionStatus.ACTIVE

    def _ensure_active(self):
        if self.status != TransactionStatus.ACTIVE:
            raise InvalidTransactionState(
                f"Transaction is {self.status.value}."
            )

    def create_savepoint(self, name: str):
        self._ensure_active()

        if not name or not name.replace("_", "").isalnum():
            raise ValueError("Invalid savepoint name.")

        self.savepoints.append(
            Savepoint(name, copy.deepcopy(self.working_state))
        )
        logger.info("SAVEPOINT %s created.", name)

    def rollback_to_savepoint(self, name: str):
        self._ensure_active()

        index = next(
            (
                i for i in range(len(self.savepoints) - 1, -1, -1)
                if self.savepoints[i].name == name
            ),
            None
        )

        if index is None:
            raise SavepointNotFound(name)

        self.working_state = copy.deepcopy(
            self.savepoints[index].snapshot
        )

        # The target savepoint remains available.
        # Later savepoints are discarded.
        self.savepoints = self.savepoints[:index + 1]

        logger.info("Rolled back to SAVEPOINT %s.", name)

    def release_savepoint(self, name: str):
        self._ensure_active()

        index = next(
            (
                i for i in range(len(self.savepoints) - 1, -1, -1)
                if self.savepoints[i].name == name
            ),
            None
        )

        if index is None:
            raise SavepointNotFound(name)

        # Releasing a savepoint does not commit the transaction.
        # Descendant savepoints are no longer independently usable.
        self.savepoints = self.savepoints[:index]

        logger.info("SAVEPOINT %s released.", name)

    def commit(self):
        self._ensure_active()

        # Atomic replacement of the committed in-memory state.
        self.database.state = copy.deepcopy(self.working_state)
        self.savepoints.clear()
        self.status = TransactionStatus.COMMITTED

        logger.info("Transaction committed.")

    def rollback(self):
        self._ensure_active()

        self.savepoints.clear()
        self.status = TransactionStatus.ROLLED_BACK

        logger.info("Entire transaction rolled back.")

    def add_order(
        self,
        account_id: int,
        product_id: int,
        quantity: int
    ) -> Order:
        self._ensure_active()

        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        account = self.working_state.accounts.get(account_id)
        product = self.working_state.products.get(product_id)

        if account is None:
            raise ValueError("Account does not exist.")

        if product is None:
            raise ValueError("Product does not exist.")

        if product.stock < quantity:
            raise InsufficientInventory(
                f"Available stock: {product.stock}"
            )

        amount = product.price * quantity

        if account.balance < amount:
            raise InsufficientFunds(
                f"Required: {amount}, available: {account.balance}"
            )

        product.stock -= quantity
        account.balance -= amount

        order = Order(
            order_id=self.working_state.next_order_id,
            account_id=account_id,
            product_id=product_id,
            quantity=quantity,
            amount=amount,
            status="CONFIRMED"
        )

        self.working_state.orders[order.order_id] = order
        self.working_state.next_order_id += 1

        self.working_state.audit_log.append(
            f"Order {order.order_id} confirmed for account {account_id}"
        )

        return order

    def update_order_status(self, order_id: int, status: str):
        self._ensure_active()

        allowed = {"PENDING", "CONFIRMED", "CANCELLED"}

        if status not in allowed:
            raise ValueError("Unsupported order status.")

        order = self.working_state.orders.get(order_id)

        if order is None:
            raise ValueError("Order does not exist.")

        order.status = status


class Database:
    def __init__(self):
        self.state = DatabaseState()

    def begin(self) -> Transaction:
        return Transaction(self)

    def seed(self):
        self.state.products = {
            101: Product(
                101, "Enterprise Laptop", 10, Decimal("75000.00")
            ),
            102: Product(
                102, "Wireless Keyboard", 20, Decimal("2500.00")
            ),
            103: Product(
                103, "External SSD", 5, Decimal("6500.00")
            )
        }

        self.state.accounts = {
            1: Account(
                1, "Corporate Procurement", Decimal("200000.00")
            ),
            2: Account(
                2, "Regional Procurement", Decimal("10000.00")
            )
        }


def demonstrate_partial_rollback(database: Database):
    print("\n1. PARTIAL ROLLBACK")

    tx = database.begin()

    try:
        tx.create_savepoint("before_orders")

        first = tx.add_order(1, 101, 1)
        print("First order:", first)

        tx.create_savepoint("before_optional_items")

        second = tx.add_order(1, 102, 2)
        print("Second order:", second)

        # Simulate failure in an optional operation.
        try:
            tx.add_order(1, 103, 100)
        except InsufficientInventory as error:
            print("Optional operation failed:", error)
            tx.rollback_to_savepoint("before_optional_items")

        # First order remains in the transaction.
        tx.commit()

    except Exception:
        if tx.status == TransactionStatus.ACTIVE:
            tx.rollback()
        raise


def demonstrate_nested_patterns(database: Database):
    print("\n2. NESTED TRANSACTION PATTERN")

    tx = database.begin()

    try:
        tx.create_savepoint("outer_operation")

        tx.add_order(1, 102, 1)

        tx.create_savepoint("inner_operation")

        try:
            tx.add_order(2, 101, 1)
        except InsufficientFunds as error:
            print("Nested operation failed:", error)
            tx.rollback_to_savepoint("inner_operation")

        # The outer operation is still valid.
        tx.release_savepoint("inner_operation")
        tx.commit()

    except Exception:
        if tx.status == TransactionStatus.ACTIVE:
            tx.rollback()
        raise


def demonstrate_full_rollback(database: Database):
    print("\n3. FULL ROLLBACK")

    tx = database.begin()

    try:
        tx.create_savepoint("transaction_start")
        tx.add_order(1, 102, 1)

        raise RuntimeError("Simulated critical processing failure")

    except RuntimeError as error:
        print("Critical failure:", error)
        tx.rollback()

    print("Transaction status:", tx.status.value)


def demonstrate_release(database: Database):
    print("\n4. SAVEPOINT RELEASE")

    tx = database.begin()

    tx.create_savepoint("phase_one")
    tx.add_order(1, 102, 1)

    tx.release_savepoint("phase_one")

    try:
        tx.rollback_to_savepoint("phase_one")
    except SavepointNotFound as error:
        print("Expected result:", error)

    tx.commit()


def demonstrate_savepoint_shadowing(database: Database):
    print("\n5. REPEATED SAVEPOINT NAMES")

    tx = database.begin()

    tx.create_savepoint("checkpoint")
    tx.add_order(1, 102, 1)

    tx.create_savepoint("checkpoint")
    tx.add_order(1, 103, 1)

    # The most recently created savepoint with this name is used.
    tx.rollback_to_savepoint("checkpoint")
    tx.commit()

    print("Repeated-name behavior demonstrated.")


def print_database(database: Database):
    print("\nFINAL DATABASE STATE")

    for product in database.state.products.values():
        print(
            f"Product {product.product_id}: "
            f"{product.name}, stock={product.stock}"
        )

    for account in database.state.accounts.values():
        print(
            f"Account {account.account_id}: "
            f"{account.owner}, balance={account.balance}"
        )

    print("\nOrders")

    for order in database.state.orders.values():
        print(order)

    print("\nAudit log")

    for entry in database.state.audit_log:
        print(entry)


class SavepointTests(unittest.TestCase):
    def setUp(self):
        self.database = Database()
        self.database.seed()

    def test_partial_rollback(self):
        tx = self.database.begin()

        tx.create_savepoint("first")
        tx.add_order(1, 102, 1)

        tx.create_savepoint("second")
        tx.add_order(1, 103, 1)

        tx.rollback_to_savepoint("second")

        self.assertEqual(len(tx.working_state.orders), 1)
        self.assertEqual(
            tx.working_state.products[103].stock, 5
        )

    def test_full_rollback(self):
        tx = self.database.begin()
        tx.add_order(1, 102, 1)
        tx.rollback()

        self.assertEqual(len(self.database.state.orders), 0)

    def test_commit(self):
        tx = self.database.begin()
        tx.add_order(1, 102, 1)
        tx.commit()

        self.assertEqual(len(self.database.state.orders), 1)

    def test_release(self):
        tx = self.database.begin()
        tx.create_savepoint("phase")
        tx.release_savepoint("phase")

        with self.assertRaises(SavepointNotFound):
            tx.rollback_to_savepoint("phase")

    def test_invalid_state(self):
        tx = self.database.begin()
        tx.commit()

        with self.assertRaises(InvalidTransactionState):
            tx.create_savepoint("invalid")

    def test_invalid_quantity(self):
        tx = self.database.begin()

        with self.assertRaises(ValueError):
            tx.add_order(1, 102, 0)

    def test_insufficient_funds(self):
        tx = self.database.begin()

        with self.assertRaises(InsufficientFunds):
            tx.add_order(2, 101, 1)

    def test_rollback_removes_later_savepoints(self):
        tx = self.database.begin()
        tx.create_savepoint("outer")
        tx.create_savepoint("inner")
        tx.rollback_to_savepoint("outer")

        with self.assertRaises(SavepointNotFound):
            tx.rollback_to_savepoint("inner")


def main():
    database = Database()
    database.seed()

    demonstrate_partial_rollback(database)
    demonstrate_nested_patterns(database)
    demonstrate_full_rollback(database)
    demonstrate_release(database)
    demonstrate_savepoint_shadowing(database)

    print_database(database)

    print("\nRUNNING TESTS")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        SavepointTests
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
