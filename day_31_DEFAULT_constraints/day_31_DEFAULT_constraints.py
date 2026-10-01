"""
DEFAULT Constraints: default values, generated defaults, timestamps, UUID defaults.

This executable learning model focuses on database DEFAULT semantics. It
demonstrates static defaults, generated application defaults, database-owned
timestamps, UUID generation, insert-time behavior, explicit overrides,
NULL semantics, migrations, validation, and production-oriented design.

The examples use only the Python standard library so the file can run without
external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import json
import re
import sqlite3
import uuid
from typing import Any, Callable, Iterable


def heading(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def subsection(title: str) -> None:
    print(f"\n--- {title} ---")


# ---------------------------------------------------------------------------
# Fundamental model: a DEFAULT supplies a value when a column is omitted.
# ---------------------------------------------------------------------------

heading("DEFAULT Constraint Fundamentals")

subsection("Static defaults")

# These values represent the same kinds of defaults commonly declared in SQL:
# DEFAULT 'pending', DEFAULT 0, DEFAULT 1, DEFAULT 'USD'.
order_defaults = {
    "status": "pending",
    "quantity": 1,
    "currency": "USD",
    "is_active": True,
}

print("Defaults:", order_defaults)


subsection("Omitted value versus explicit value")

def create_order(
    product: str,
    quantity: int | None = None,
    status: str | None = None,
    currency: str | None = None,
) -> dict[str, Any]:
    """
    Model INSERT behavior.

    In a real database, an omitted column can receive its DEFAULT.
    A caller that explicitly supplies a value is normally overriding that
    default. This function uses None as an API-level signal for omission.
    """
    if not product.strip():
        raise ValueError("product must not be empty")

    if quantity is None:
        quantity = 1
    elif quantity <= 0:
        raise ValueError("quantity must be positive")

    if status is None:
        status = "pending"

    if currency is None:
        currency = "USD"

    return {
        "product": product,
        "quantity": quantity,
        "status": status,
        "currency": currency,
    }


print(create_order("Keyboard"))
print(create_order("Monitor", quantity=2, status="confirmed", currency="EUR"))


# ---------------------------------------------------------------------------
# Static defaults should be deterministic and appropriate for their domain.
# ---------------------------------------------------------------------------

heading("Choosing Static Defaults")

VALID_STATUSES = {"pending", "confirmed", "cancelled", "fulfilled"}
VALID_CURRENCIES = {"USD", "EUR", "GBP", "INR"}


@dataclass
class InventoryItem:
    name: str
    quantity: int = 0
    reorder_level: int = 10
    is_active: bool = True
    unit: str = "piece"

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("inventory name is required")
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")
        if self.reorder_level < 0:
            raise ValueError("reorder_level cannot be negative")
        if not self.unit.strip():
            raise ValueError("unit is required")


item = InventoryItem(name="SSD")
item.validate()
print(item)


def validate_order(order: dict[str, Any]) -> None:
    if order["status"] not in VALID_STATUSES:
        raise ValueError(f"invalid status: {order['status']}")
    if order["currency"] not in VALID_CURRENCIES:
        raise ValueError(f"invalid currency: {order['currency']}")
    if order["quantity"] <= 0:
        raise ValueError("quantity must be positive")


order = create_order("Laptop")
validate_order(order)
print("Validated:", order)


# ---------------------------------------------------------------------------
# Generated defaults: values whose generation happens at record creation.
# ---------------------------------------------------------------------------

heading("Generated Defaults")

subsection("UUID defaults")

def generate_uuid() -> str:
    """Generate a fresh identifier for each new record."""
    return str(uuid.uuid4())


record_a = {"id": generate_uuid(), "name": "Alice"}
record_b = {"id": generate_uuid(), "name": "Bob"}

assert record_a["id"] != record_b["id"]

print(json.dumps(record_a, indent=2))
print(json.dumps(record_b, indent=2))


subsection("Why the generator must execute per row")

@dataclass
class UserRecord:
    username: str
    user_id: str = field(default_factory=generate_uuid)


users = [
    UserRecord("atul"),
    UserRecord("developer"),
    UserRecord("reviewer"),
]

for user in users:
    print(user.username, user.user_id)


# ---------------------------------------------------------------------------
# Timestamps are dynamic defaults. They must be evaluated when a row is
# created rather than once when application code is imported.
# ---------------------------------------------------------------------------

heading("Timestamp Defaults")

def utc_now() -> datetime:
    """
    Return a timezone-aware UTC timestamp.

    UTC avoids ambiguity across servers and is generally preferable for
    persisted event times. Presentation can convert UTC to a local zone.
    """
    return datetime.now(timezone.utc)


@dataclass
class AuditRecord:
    event: str
    created_at: datetime = field(default_factory=utc_now)


first_event = AuditRecord("account_created")
second_event = AuditRecord("profile_updated")

print(first_event.created_at.isoformat())
print(second_event.created_at.isoformat())

if second_event.created_at < first_event.created_at:
    raise RuntimeError("timestamps moved backwards")


subsection("Timestamp precision and deterministic testing")

class Clock:
    """Injectable clock used to make time-dependent code testable."""

    def __init__(self, current: datetime | None = None):
        self.current = current or utc_now()

    def now(self) -> datetime:
        return self.current


fixed_clock = Clock(datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc))


@dataclass
class Event:
    name: str
    clock: Callable[[], datetime] = utc_now
    created_at: datetime = field(init=False)

    def __post_init__(self) -> None:
        self.created_at = self.clock()


event = Event("deployment", clock=fixed_clock.now)
print("Deterministic timestamp:", event.created_at.isoformat())


# ---------------------------------------------------------------------------
# NULL is distinct from omission. This is one of the most important DEFAULT
# semantics: a DEFAULT generally applies because a value was not supplied.
# Explicit NULL is normally stored as NULL when the column permits it.
# ---------------------------------------------------------------------------

heading("Omitted Values, Explicit NULL, and Defaults")

def simulate_insert(
    supplied: dict[str, Any],
    defaults: dict[str, Any],
    nullable: set[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for column, default_value in defaults.items():
        if column in supplied:
            value = supplied[column]

            if value is None and column not in nullable:
                raise ValueError(f"{column} does not permit NULL")

            result[column] = value
        else:
            result[column] = default_value() if callable(default_value) else default_value

    return result


schema_defaults = {
    "status": "pending",
    "created_at": utc_now,
    "is_active": True,
}

print(
    "Omitted status:",
    simulate_insert({}, schema_defaults, {"status", "created_at"}),
)

print(
    "Explicit NULL status:",
    simulate_insert({"status": None}, schema_defaults, {"status", "created_at"}),
)

try:
    simulate_insert({"is_active": None}, schema_defaults, {"status", "created_at"})
except ValueError as exc:
    print("Rejected:", exc)


# ---------------------------------------------------------------------------
# Application defaults versus database defaults.
# ---------------------------------------------------------------------------

heading("Application Defaults Versus Database Defaults")

class ApplicationRecordFactory:
    """
    Application-side default generation.

    This is useful when the application needs the generated value before
    sending an INSERT, such as an id needed for an event or an API response.
    """

    @staticmethod
    def create() -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "created_at": utc_now(),
            "status": "pending",
        }


class DatabaseStyleRecordFactory:
    """
    Simulates a database-owned default.

    The application supplies only business data and lets the persistence
    layer establish generated metadata.
    """

    @staticmethod
    def persist(business_value: str) -> dict[str, Any]:
        return {
            "business_value": business_value,
            "id": str(uuid.uuid4()),
            "created_at": utc_now(),
            "status": "pending",
        }


application_record = ApplicationRecordFactory.create()
database_record = DatabaseStyleRecordFactory.persist("invoice")

print("Application-generated:", application_record)
print("Persistence-generated:", database_record)


# ---------------------------------------------------------------------------
# SQLite provides an actual database environment for DEFAULT behavior.
# ---------------------------------------------------------------------------

heading("Actual SQLite DEFAULT Constraints")

connection = sqlite3.connect(":memory:")
connection.row_factory = sqlite3.Row

connection.execute(
    """
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        quantity INTEGER NOT NULL DEFAULT 1,
        currency TEXT NOT NULL DEFAULT 'USD',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """
)

connection.execute(
    "INSERT INTO orders (customer_name) VALUES (?)",
    ("Atul",),
)

connection.execute(
    """
    INSERT INTO orders (customer_name, status, quantity, currency)
    VALUES (?, ?, ?, ?)
    """,
    ("Research Team", "confirmed", 3, "EUR"),
)

connection.commit()

rows = connection.execute(
    """
    SELECT id, customer_name, status, quantity, currency, created_at, is_active
    FROM orders
    ORDER BY id
    """
).fetchall()

for row in rows:
    print(dict(row))


subsection("Explicit NULL does not mean DEFAULT")

connection.execute(
    "CREATE TABLE nullable_demo (value TEXT DEFAULT 'generated-value')"
)

connection.execute(
    "INSERT INTO nullable_demo DEFAULT VALUES"
)

connection.execute(
    "INSERT INTO nullable_demo (value) VALUES (NULL)"
)

demo_rows = connection.execute(
    "SELECT rowid, value FROM nullable_demo ORDER BY rowid"
).fetchall()

for row in demo_rows:
    print(dict(row))


subsection("DEFAULT VALUES")

connection.execute(
    """
    CREATE TABLE job_runs (
        id INTEGER PRIMARY KEY,
        state TEXT NOT NULL DEFAULT 'queued',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

connection.execute("INSERT INTO job_runs DEFAULT VALUES")

job = connection.execute(
    "SELECT * FROM job_runs"
).fetchone()

print("Generated job:", dict(job))


# ---------------------------------------------------------------------------
# Dynamic UUID defaults in SQLite require application generation in this
# example because SQLite does not provide a built-in UUID() expression.
# ---------------------------------------------------------------------------

heading("UUID Persistence Pattern")

connection.execute(
    """
    CREATE TABLE api_keys (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

new_key_id = str(uuid.uuid4())

connection.execute(
    """
    INSERT INTO api_keys (id, owner)
    VALUES (?, ?)
    """,
    (new_key_id, "service-account"),
)

api_key = connection.execute(
    "SELECT * FROM api_keys"
).fetchone()

print(dict(api_key))


# ---------------------------------------------------------------------------
# Defaults and migrations: changing a default affects future inserts, not
# existing rows. Existing values generally require an explicit data migration.
# ---------------------------------------------------------------------------

heading("Default Changes and Migration Semantics")

connection.execute(
    """
    CREATE TABLE feature_flags (
        name TEXT PRIMARY KEY,
        enabled INTEGER NOT NULL DEFAULT 0
    )
    """
)

connection.execute(
    "INSERT INTO feature_flags (name) VALUES (?)",
    ("new_dashboard",),
)

connection.commit()

before_migration = connection.execute(
    "SELECT * FROM feature_flags"
).fetchone()

print("Existing row before policy change:", dict(before_migration))

# SQLite has restrictions around ALTER COLUMN DEFAULT, so the example models
# a migration by rebuilding the table. The important distinction is that a
# changed DEFAULT is a schema policy for future inserts, not a retroactive
# transformation of stored data.
connection.execute(
    """
    CREATE TABLE feature_flags_new (
        name TEXT PRIMARY KEY,
        enabled INTEGER NOT NULL DEFAULT 1
    )
    """
)

connection.execute(
    """
    INSERT INTO feature_flags_new (name, enabled)
    SELECT name, enabled
    FROM feature_flags
    """
)

connection.execute("DROP TABLE feature_flags")
connection.execute("ALTER TABLE feature_flags_new RENAME TO feature_flags")

connection.execute(
    "INSERT INTO feature_flags (name) VALUES (?)",
    ("risk_dashboard",),
)

connection.commit()

migration_rows = connection.execute(
    "SELECT * FROM feature_flags ORDER BY name"
).fetchall()

for row in migration_rows:
    print(dict(row))


# ---------------------------------------------------------------------------
# Defaults should not silently hide invalid business input.
# ---------------------------------------------------------------------------

heading("Validation and Default Safety")

def create_payment(
    amount: float,
    currency: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    selected_currency = currency if currency is not None else "INR"
    selected_status = status if status is not None else "pending"

    if selected_currency not in {"INR", "USD", "EUR"}:
        raise ValueError("unsupported currency")

    if selected_status not in {"pending", "authorized", "captured", "failed"}:
        raise ValueError("invalid payment status")

    return {
        "amount": round(amount, 2),
        "currency": selected_currency,
        "status": selected_status,
    }


print(create_payment(1500.50))

try:
    create_payment(-20)
except ValueError as exc:
    print("Invalid payment:", exc)


# ---------------------------------------------------------------------------
# A realistic order model combines static defaults, generated UUIDs,
# timestamps, and explicit business validation.
# ---------------------------------------------------------------------------

heading("Integrated Order Creation Service")


class OrderState(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass
class Order:
    customer_id: str
    product_code: str
    quantity: int
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderState = OrderState.PENDING
    currency: str = "INR"
    created_at: datetime = field(default_factory=utc_now)
    is_active: bool = True

    def validate(self) -> None:
        if not self.customer_id.strip():
            raise ValueError("customer_id is required")

        if not re.fullmatch(r"[A-Z]{3}-\d{4}", self.product_code):
            raise ValueError(
                "product_code must use the format ABC-1234"
            )

        if self.quantity <= 0:
            raise ValueError("quantity must be positive")

        if self.currency not in VALID_CURRENCIES:
            raise ValueError("unsupported currency")

    def cancel(self) -> None:
        if self.status == OrderState.CANCELLED:
            raise ValueError("order is already cancelled")

        self.status = OrderState.CANCELLED
        self.is_active = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "product_code": self.product_code,
            "quantity": self.quantity,
            "status": self.status.value,
            "currency": self.currency,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }


order = Order(
    customer_id="CUST-001",
    product_code="SSD-2048",
    quantity=2,
)

order.validate()
print(json.dumps(order.to_dict(), indent=2))

order.cancel()
print("After cancellation:", order.to_dict())


# ---------------------------------------------------------------------------
# Edge cases around mutable defaults. A mutable object must not be shared
# across instances. default_factory creates a separate object per instance.
# ---------------------------------------------------------------------------

heading("Mutable Default Edge Case")

@dataclass
class RequestContext:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    warnings: list[str] = field(default_factory=list)


request_a = RequestContext()
request_b = RequestContext()

request_a.warnings.append("currency defaulted to INR")

print("A:", request_a)
print("B:", request_b)

assert request_a.warnings != request_b.warnings


# ---------------------------------------------------------------------------
# Production-oriented inspection: classify defaults according to ownership.
# ---------------------------------------------------------------------------

heading("Default Ownership Model")

@dataclass(frozen=True)
class DefaultPolicy:
    column: str
    owner: str
    expression: str
    purpose: str


policies = [
    DefaultPolicy(
        "status",
        "database",
        "'pending'",
        "establish a valid initial workflow state",
    ),
    DefaultPolicy(
        "created_at",
        "database",
        "CURRENT_TIMESTAMP",
        "record persistence time consistently",
    ),
    DefaultPolicy(
        "id",
        "application",
        "uuid.uuid4()",
        "create an identifier before persistence",
    ),
    DefaultPolicy(
        "currency",
        "database",
        "'USD'",
        "supply the domain's configured default currency",
    ),
]

for policy in policies:
    print(
        f"{policy.column}: owner={policy.owner}, "
        f"expression={policy.expression}, purpose={policy.purpose}"
    )


# ---------------------------------------------------------------------------
# Debugging: verify which fields were supplied rather than assuming that
# the final row reveals whether a default was used.
# ---------------------------------------------------------------------------

heading("Debugging Default Behavior")

def build_insert_payload(
    customer: str,
    status: str | None = None,
    include_status: bool = False,
) -> dict[str, Any]:
    payload = {"customer": customer}

    # Distinguishing omission from explicit NULL requires preserving the
    # caller's intent. A dictionary key that is absent represents omission.
    if include_status:
        payload["status"] = status

    return payload


print(
    "Omitted status payload:",
    build_insert_payload("Atul"),
)

print(
    "Explicit NULL payload:",
    build_insert_payload("Atul", status=None, include_status=True),
)


# ---------------------------------------------------------------------------
# Transactional behavior: defaults are applied as part of INSERT processing.
# ---------------------------------------------------------------------------

heading("Defaults Inside Transactions")

connection.execute(
    """
    CREATE TABLE transaction_events (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'created',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

try:
    with connection:
        connection.execute(
            "INSERT INTO transaction_events (name) VALUES (?)",
            ("transactional-event",),
        )

        connection.execute(
            "INSERT INTO transaction_events (name) VALUES (?)",
            ("another-event",),
        )

    transaction_rows = connection.execute(
        "SELECT * FROM transaction_events ORDER BY id"
    ).fetchall()

    for row in transaction_rows:
        print(dict(row))

except sqlite3.Error as exc:
    print("Transaction failed:", exc)


# ---------------------------------------------------------------------------
# Performance consideration: defaults are generally cheap, but generated
# expressions and indexes can have system-wide effects. UUID choice can also
# influence index locality depending on the database and UUID representation.
# ---------------------------------------------------------------------------

heading("Performance and Production Considerations")

performance_notes = {
    "static defaults": "Usually inexpensive because the value is deterministic.",
    "current timestamp": "Generated during row creation and adds minimal computation.",
    "random UUID": "Convenient for distributed identifiers but random ordering can affect index locality.",
    "application-generated UUID": "Useful when the identifier is needed before the INSERT.",
    "database-generated UUID": "Centralizes identifier ownership and protects consistency across writers.",
    "default expressions": "Should be deterministic enough for the domain and supported by the target database.",
}

for key, value in performance_notes.items():
    print(f"{key}: {value}")


# ---------------------------------------------------------------------------
# Final integrated demonstration.
# ---------------------------------------------------------------------------

heading("Integrated Demonstration")

connection.execute(
    """
    CREATE TABLE service_records (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'queued',
        priority INTEGER NOT NULL DEFAULT 5,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        enabled INTEGER NOT NULL DEFAULT 1
    )
    """
)

service_id = str(uuid.uuid4())

connection.execute(
    """
    INSERT INTO service_records (id, name)
    VALUES (?, ?)
    """,
    (service_id, "risk-calculation-worker"),
)

connection.execute(
    """
    INSERT INTO service_records (id, name, priority)
    VALUES (?, ?, ?)
    """,
    (str(uuid.uuid4()), "audit-worker", 10),
)

connection.commit()

for row in connection.execute(
    """
    SELECT id, name, state, priority, created_at, enabled
    FROM service_records
    ORDER BY created_at, id
    """
):
    print(dict(row))


connection.close()

print("\nDEFAULT constraint demonstrations completed successfully.")
