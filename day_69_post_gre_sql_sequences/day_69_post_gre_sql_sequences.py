#!/usr/bin/env python3
"""
PostgreSQL Sequences: SERIAL, IDENTITY, and Sequence Behavior

Demonstrates:
- Sequence creation and configuration
- SERIAL and GENERATED IDENTITY semantics
- NEXTVAL, CURRVAL, and SETVAL behavior
- Increment, minimum, maximum, cache, and cycle
- Non-transactional sequence allocation
- Gaps caused by rollbacks and failed inserts
- Ownership and sequence synchronization
- Concurrent allocation simulation
- Validation and automated tests

Requires: Python 3.10+
No external dependencies.
"""

from __future__ import annotations

import argparse
import json
import logging
import threading
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

logger = logging.getLogger("postgresql_sequences")


class SequenceError(Exception):
    """Base exception for sequence operations."""


class SequenceLimitError(SequenceError):
    """Raised when a sequence reaches its configured boundary."""


class SequenceConfigurationError(SequenceError):
    """Raised for invalid sequence configuration."""


class OwnershipError(SequenceError):
    """Raised when sequence ownership is invalid."""


class IdentityMode(Enum):
    SERIAL = "serial"
    GENERATED_ALWAYS = "generated_always"
    GENERATED_BY_DEFAULT = "generated_by_default"


@dataclass(frozen=True)
class SequenceConfig:
    name: str
    start: int = 1
    increment: int = 1
    minimum: int = 1
    maximum: int = 2**63 - 1
    cache: int = 1
    cycle: bool = False

    def __post_init__(self):
        if not self.name.strip():
            raise SequenceConfigurationError(
                "Sequence name cannot be empty."
            )

        if self.increment == 0:
            raise SequenceConfigurationError(
                "Sequence increment cannot be zero."
            )

        if self.minimum > self.maximum:
            raise SequenceConfigurationError(
                "Minimum cannot exceed maximum."
            )

        if not self.minimum <= self.start <= self.maximum:
            raise SequenceConfigurationError(
                "Starting value must be within configured limits."
            )

        if self.cache < 1:
            raise SequenceConfigurationError(
                "Cache must be at least one."
            )

        if self.increment > 0 and self.start < self.minimum:
            raise SequenceConfigurationError(
                "Invalid ascending sequence start."
            )

        if self.increment < 0 and self.start > self.maximum:
            raise SequenceConfigurationError(
                "Invalid descending sequence start."
            )


@dataclass
class SequenceSnapshot:
    name: str
    last_value: Optional[int]
    is_called: bool
    allocations: int
    cache: int
    cycle: bool


class PostgreSQLSequence:
    """
    Thread-safe sequence simulator.

    PostgreSQL sequence allocation is not transactional.
    Rolling back a transaction does not restore values consumed
    through nextval().
    """

    def __init__(self, config: SequenceConfig):
        self.config = config
        self._last_value: Optional[int] = None
        self._is_called = False
        self._allocations = 0
        self._lock = threading.Lock()
        self._session_values: dict[str, int] = {}

    def _calculate_next(self) -> int:
        config = self.config

        if not self._is_called:
            return config.start

        current = self._last_value
        assert current is not None

        candidate = current + config.increment

        if config.increment > 0 and candidate > config.maximum:
            if not config.cycle:
                raise SequenceLimitError(
                    f"Sequence {config.name} reached maximum."
                )
            return config.minimum

        if config.increment < 0 and candidate < config.minimum:
            if not config.cycle:
                raise SequenceLimitError(
                    f"Sequence {config.name} reached minimum."
                )
            return config.maximum

        return candidate

    def nextval(self, session_id: str = "default") -> int:
        if not session_id:
            raise ValueError("Session ID cannot be empty.")

        with self._lock:
            value = self._calculate_next()
            self._last_value = value
            self._is_called = True
            self._allocations += 1
            self._session_values[session_id] = value

            return value

    def currval(self, session_id: str = "default") -> int:
        """
        Return the last value obtained by this session.

        CURRVAL is session-specific and fails if the session
        has not called NEXTVAL on this sequence.
        """
        with self._lock:
            if session_id not in self._session_values:
                raise SequenceError(
                    f"Session {session_id} has not called NEXTVAL."
                )

            return self._session_values[session_id]

    def last_value(self) -> Optional[int]:
        with self._lock:
            return self._last_value

    def setval(
        self,
        value: int,
        is_called: bool = True
    ) -> int:
        """
        Simulate PostgreSQL SETVAL.

        is_called=True:
            Next NEXTVAL returns value + increment.

        is_called=False:
            Next NEXTVAL returns value.
        """
        with self._lock:
            if not self.config.minimum <= value <= self.config.maximum:
                raise SequenceLimitError(
                    "SETVAL value is outside sequence limits."
                )

            self._last_value = value
            self._is_called = is_called

            return value

    def restart(self, value: Optional[int] = None) -> None:
        with self._lock:
            restart_value = (
                self.config.start if value is None else value
            )

            if not (
                self.config.minimum
                <= restart_value
                <= self.config.maximum
            ):
                raise SequenceLimitError(
                    "Restart value is outside sequence limits."
                )

            self._last_value = restart_value
            self._is_called = False
            self._session_values.clear()

    def snapshot(self) -> SequenceSnapshot:
        with self._lock:
            return SequenceSnapshot(
                name=self.config.name,
                last_value=self._last_value,
                is_called=self._is_called,
                allocations=self._allocations,
                cache=self.config.cache,
                cycle=self.config.cycle
            )


@dataclass
class Customer:
    customer_id: int
    name: str
    email: str


class CustomerIdentityTable:
    """
    Models a customer table with an identity-generated primary key.
    """

    def __init__(
        self,
        sequence: PostgreSQLSequence,
        mode: IdentityMode
    ):
        self.sequence = sequence
        self.mode = mode
        self.rows: dict[int, Customer] = {}
        self._lock = threading.Lock()

    def insert(
        self,
        name: str,
        email: str,
        explicit_id: Optional[int] = None,
        overriding_system_value: bool = False,
        session_id: str = "default"
    ) -> Customer:

        if not name.strip():
            raise ValueError("Customer name is required.")

        if "@" not in email:
            raise ValueError("Invalid email address.")

        if explicit_id is not None:
            if self.mode == IdentityMode.GENERATED_ALWAYS:
                if not overriding_system_value:
                    raise ValueError(
                        "GENERATED ALWAYS rejects explicit values."
                    )

            elif self.mode == IdentityMode.GENERATED_BY_DEFAULT:
                pass

            elif self.mode == IdentityMode.SERIAL:
                pass

            customer_id = explicit_id

        else:
            customer_id = self.sequence.nextval(session_id)

        if customer_id <= 0:
            raise ValueError("Customer ID must be positive.")

        with self._lock:
            if customer_id in self.rows:
                raise ValueError(
                    f"Duplicate customer ID: {customer_id}"
                )

            customer = Customer(
                customer_id=customer_id,
                name=name.strip(),
                email=email.strip().lower()
            )

            self.rows[customer_id] = customer
            return customer

    def find(self, customer_id: int) -> Optional[Customer]:
        with self._lock:
            return self.rows.get(customer_id)

    def synchronize_sequence(self) -> int:
        """
        Synchronize a sequence after manual ID insertion.

        For a positive increment, the sequence must advance beyond
        the maximum existing ID.
        """
        with self._lock:
            maximum_id = max(self.rows, default=0)

        current = self.sequence.last_value()

        if current is None or maximum_id > current:
            self.sequence.setval(maximum_id, True)

        return maximum_id


class TransactionSimulator:
    """
    Demonstrates the difference between transaction rollback
    and sequence allocation.
    """

    def __init__(self, sequence: PostgreSQLSequence):
        self.sequence = sequence

    def failed_transaction(self) -> int:
        allocated = self.sequence.nextval("transaction-session")

        logger.info(
            "Allocated ID %s before simulated transaction failure.",
            allocated
        )

        # A real ROLLBACK does not return this value to the sequence.
        return allocated


def demonstrate_basic_sequence():
    print("\n1. BASIC SEQUENCE")

    sequence = PostgreSQLSequence(
        SequenceConfig(
            name="orders_order_id_seq",
            start=1000,
            increment=1,
            minimum=1000,
            maximum=1100
        )
    )

    first = sequence.nextval("session-a")
    second = sequence.nextval("session-a")

    print("NEXTVAL:", first)
    print("NEXTVAL:", second)
    print("CURRVAL:", sequence.currval("session-a"))

    return sequence


def demonstrate_sessions():
    print("\n2. SESSION-SPECIFIC CURRVAL")

    sequence = PostgreSQLSequence(
        SequenceConfig(name="invoice_id_seq")
    )

    value_a = sequence.nextval("session-a")

    try:
        sequence.currval("session-b")
    except SequenceError as error:
        print("Expected error:", error)

    value_b = sequence.nextval("session-b")

    print("Session A:", value_a)
    print("Session B:", value_b)
    print("Session A CURRVAL:", sequence.currval("session-a"))


def demonstrate_setval():
    print("\n3. SETVAL BEHAVIOR")

    sequence = PostgreSQLSequence(
        SequenceConfig(name="shipment_id_seq")
    )

    sequence.setval(500, True)
    print("SETVAL(500, true), NEXTVAL:", sequence.nextval())

    sequence.setval(900, False)
    print("SETVAL(900, false), NEXTVAL:", sequence.nextval())


def demonstrate_identity():
    print("\n4. IDENTITY COLUMN BEHAVIOR")

    sequence = PostgreSQLSequence(
        SequenceConfig(name="customers_customer_id_seq")
    )

    table = CustomerIdentityTable(
        sequence,
        IdentityMode.GENERATED_ALWAYS
    )

    customer = table.insert(
        "Aarav Sharma",
        "aarav@example.com"
    )

    print("Generated customer:", asdict(customer))

    try:
        table.insert(
            "Manual Customer",
            "manual@example.com",
            explicit_id=500
        )
    except ValueError as error:
        print("Expected identity restriction:", error)

    manual_customer = table.insert(
        "Manual Customer",
        "manual@example.com",
        explicit_id=500,
        overriding_system_value=True
    )

    print("Overridden identity:", asdict(manual_customer))

    table.synchronize_sequence()

    next_customer = table.insert(
        "Next Customer",
        "next@example.com"
    )

    print("Next generated customer:", asdict(next_customer))


def demonstrate_rollback():
    print("\n5. NON-TRANSACTIONAL SEQUENCE ALLOCATION")

    sequence = PostgreSQLSequence(
        SequenceConfig(name="payments_payment_id_seq")
    )

    transaction = TransactionSimulator(sequence)

    allocated = transaction.failed_transaction()

    print("Failed transaction consumed:", allocated)
    print("Next available value:", sequence.nextval())


def demonstrate_cycle_and_limits():
    print("\n6. CYCLE AND BOUNDARY BEHAVIOR")

    sequence = PostgreSQLSequence(
        SequenceConfig(
            name="temporary_code_seq",
            start=1,
            minimum=1,
            maximum=3,
            cycle=True
        )
    )

    values = [sequence.nextval() for _ in range(7)]

    print("Cyclic sequence:", values)

    limited = PostgreSQLSequence(
        SequenceConfig(
            name="limited_sequence",
            start=1,
            minimum=1,
            maximum=2,
            cycle=False
        )
    )

    print("Limited values:", limited.nextval(), limited.nextval())

    try:
        limited.nextval()
    except SequenceLimitError as error:
        print("Expected boundary error:", error)


def demonstrate_descending_sequence():
    print("\n7. DESCENDING SEQUENCE")

    sequence = PostgreSQLSequence(
        SequenceConfig(
            name="descending_sequence",
            start=10,
            increment=-2,
            minimum=0,
            maximum=10
        )
    )

    print([sequence.nextval() for _ in range(6)])


def demonstrate_concurrency():
    print("\n8. CONCURRENT ALLOCATION")

    sequence = PostgreSQLSequence(
        SequenceConfig(
            name="concurrent_order_sequence"
        )
    )

    allocated: list[int] = []
    result_lock = threading.Lock()

    def worker(worker_id: int):
        local_values = [
            sequence.nextval(f"worker-{worker_id}")
            for _ in range(100)
        ]

        with result_lock:
            allocated.extend(local_values)

    threads = [
        threading.Thread(target=worker, args=(i,))
        for i in range(8)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    unique_values = set(allocated)

    assert len(allocated) == 800
    assert len(unique_values) == 800

    print("Total allocations:", len(allocated))
    print("Unique allocations:", len(unique_values))
    print("Minimum:", min(allocated))
    print("Maximum:", max(allocated))


def export_report(path: Path, sequence: PostgreSQLSequence):
    report = asdict(sequence.snapshot())

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nSequence report saved:", path)


def run_tests():
    print("\n9. AUTOMATED VALIDATION")

    sequence = PostgreSQLSequence(
        SequenceConfig(
            name="test_sequence",
            start=10,
            increment=5,
            minimum=10,
            maximum=30
        )
    )

    assert sequence.nextval() == 10
    assert sequence.nextval() == 15
    assert sequence.currval() == 15

    sequence.setval(20, False)
    assert sequence.nextval() == 20

    sequence.setval(25, True)
    assert sequence.nextval() == 30

    try:
        sequence.nextval()
        raise AssertionError("Expected sequence limit error.")
    except SequenceLimitError:
        pass

    try:
        SequenceConfig(
            name="invalid_sequence",
            increment=0
        )
        raise AssertionError("Expected configuration error.")
    except SequenceConfigurationError:
        pass

    print("All tests passed.")


def main():
    parser = argparse.ArgumentParser(
        description="PostgreSQL sequence behavior simulator."
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/sequence_report.json")
    )

    args = parser.parse_args()

    print("=" * 65)
    print("POSTGRESQL SEQUENCES")
    print("=" * 65)

    basic_sequence = demonstrate_basic_sequence()

    demonstrate_sessions()
    demonstrate_setval()
    demonstrate_identity()
    demonstrate_rollback()
    demonstrate_cycle_and_limits()
    demonstrate_descending_sequence()
    demonstrate_concurrency()
    run_tests()

    export_report(args.report, basic_sequence)

    print("\nExecution completed successfully.")


if __name__ == "__main__":
    main()
