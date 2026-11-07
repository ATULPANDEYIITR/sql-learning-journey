from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
import re
import unittest


class KeyStrategy(Enum):
    SURROGATE_UUID = "surrogate_uuid"
    SURROGATE_SEQUENCE = "surrogate_sequence"
    NATURAL = "natural"


class DuplicateKeyError(Exception):
    pass


class RecordNotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


@dataclass
class Customer:
    customer_id: int
    public_id: UUID
    email: str
    full_name: str
    country_code: str
    external_reference: Optional[str] = None


@dataclass
class NaturalCustomer:
    country_code: str
    national_identifier: str
    full_name: str

    @property
    def natural_key(self) -> tuple[str, str]:
        return self.country_code, self.national_identifier


@dataclass
class KeyStatistics:
    records: int
    integer_keys: int
    uuid_keys: int
    natural_key_fields: int


class CustomerRepository:
    """
    Demonstrates three identification strategies.

    Integer identity: compact internal relational identifier.
    UUID: globally unique public-facing identifier.
    Natural key: business identifier with a uniqueness constraint.
    """

    def __init__(self):
        self._next_id = 1
        self._customers: dict[int, Customer] = {}
        self._uuid_index: dict[UUID, int] = {}
        self._email_index: dict[str, int] = {}
        self._external_index: dict[str, int] = {}

    @staticmethod
    def normalize_email(email: str) -> str:
        if not isinstance(email, str):
            raise ValidationError("Email must be a string.")

        normalized = email.strip().casefold()

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValidationError("Invalid email address.")

        return normalized

    @staticmethod
    def validate_country(country_code: str) -> str:
        country = country_code.strip().upper()

        if not re.fullmatch(r"[A-Z]{2}", country):
            raise ValidationError("Country code must contain two letters.")

        return country

    def create(
        self,
        email: str,
        full_name: str,
        country_code: str,
        external_reference: Optional[str] = None,
    ) -> Customer:

        normalized_email = self.normalize_email(email)
        country = self.validate_country(country_code)

        if not full_name.strip():
            raise ValidationError("Customer name cannot be empty.")

        if normalized_email in self._email_index:
            raise DuplicateKeyError("Email already belongs to a customer.")

        if external_reference is not None:
            external_reference = external_reference.strip()

            if not external_reference:
                raise ValidationError("External reference cannot be empty.")

            if external_reference in self._external_index:
                raise DuplicateKeyError("External reference already exists.")

        customer = Customer(
            customer_id=self._next_id,
            public_id=uuid4(),
            email=normalized_email,
            full_name=full_name.strip(),
            country_code=country,
            external_reference=external_reference,
        )

        # Update all indexes only after validation succeeds.
        self._customers[customer.customer_id] = customer
        self._uuid_index[customer.public_id] = customer.customer_id
        self._email_index[normalized_email] = customer.customer_id

        if external_reference:
            self._external_index[external_reference] = customer.customer_id

        self._next_id += 1
        return customer

    def get_by_id(self, customer_id: int) -> Customer:
        customer = self._customers.get(customer_id)

        if customer is None:
            raise RecordNotFoundError(
                f"Customer ID {customer_id} does not exist."
            )

        return customer

    def get_by_uuid(self, public_id: UUID) -> Customer:
        customer_id = self._uuid_index.get(public_id)

        if customer_id is None:
            raise RecordNotFoundError("UUID does not exist.")

        return self.get_by_id(customer_id)

    def get_by_email(self, email: str) -> Customer:
        normalized = self.normalize_email(email)
        customer_id = self._email_index.get(normalized)

        if customer_id is None:
            raise RecordNotFoundError("Email does not exist.")

        return self.get_by_id(customer_id)

    def update_email(self, customer_id: int, new_email: str) -> Customer:
        customer = self.get_by_id(customer_id)
        normalized = self.normalize_email(new_email)

        existing_id = self._email_index.get(normalized)

        if existing_id is not None and existing_id != customer_id:
            raise DuplicateKeyError("Email belongs to another customer.")

        old_email = customer.email

        # The surrogate identifiers remain unchanged.
        del self._email_index[old_email]
        customer.email = normalized
        self._email_index[normalized] = customer_id

        return customer

    def delete(self, customer_id: int) -> None:
        customer = self.get_by_id(customer_id)

        del self._customers[customer_id]
        del self._uuid_index[customer.public_id]
        del self._email_index[customer.email]

        if customer.external_reference:
            del self._external_index[customer.external_reference]

    def statistics(self) -> KeyStatistics:
        return KeyStatistics(
            records=len(self._customers),
            integer_keys=len(self._customers),
            uuid_keys=len(self._uuid_index),
            natural_key_fields=2,
        )

    def all_customers(self) -> list[Customer]:
        return list(self._customers.values())


class NaturalKeyRegistry:
    """Demonstrates a composite natural primary key."""

    def __init__(self):
        self._records: dict[tuple[str, str], NaturalCustomer] = {}

    def register(
        self,
        country_code: str,
        national_identifier: str,
        full_name: str,
    ) -> NaturalCustomer:

        country = CustomerRepository.validate_country(country_code)
        identifier = national_identifier.strip()

        if not re.fullmatch(r"[A-Za-z0-9-]{4,40}", identifier):
            raise ValidationError("Invalid national identifier.")

        if not full_name.strip():
            raise ValidationError("Name cannot be empty.")

        key = (country, identifier)

        if key in self._records:
            raise DuplicateKeyError("Natural composite key already exists.")

        record = NaturalCustomer(country, identifier, full_name.strip())
        self._records[key] = record

        return record

    def find(self, country_code: str, identifier: str) -> NaturalCustomer:
        key = (country_code.upper(), identifier.strip())

        if key not in self._records:
            raise RecordNotFoundError("Natural key not found.")

        return self._records[key]


class KeyDesignAnalyzer:
    """Provides a simple qualitative comparison of key strategies."""

    @staticmethod
    def compare() -> dict[str, dict[str, str]]:
        return {
            "integer_identity": {
                "generation": "Database-managed sequence",
                "storage": "Compact",
                "ordering": "Usually increasing",
                "distribution": "Requires coordinated allocation",
                "business_meaning": "None",
                "best_use": "Internal relational primary keys",
            },
            "uuid": {
                "generation": "Random or time-based UUID",
                "storage": "16 bytes",
                "ordering": "UUIDv4 is not time ordered",
                "distribution": "Suitable for distributed generation",
                "business_meaning": "None",
                "best_use": "Distributed and public identifiers",
            },
            "natural": {
                "generation": "Existing business attributes",
                "storage": "Depends on attribute types",
                "ordering": "Depends on values",
                "distribution": "Requires business uniqueness rules",
                "business_meaning": "Contains business meaning",
                "best_use": "Stable business identification",
            },
        }


class TestKeyDesign(unittest.TestCase):

    def setUp(self):
        self.repository = CustomerRepository()

    def test_surrogate_identifiers(self):
        customer = self.repository.create(
            "alice@example.com",
            "Alice Sharma",
            "IN",
        )

        self.assertEqual(customer.customer_id, 1)
        self.assertIsInstance(customer.public_id, UUID)

        self.assertEqual(
            self.repository.get_by_uuid(customer.public_id).customer_id,
            customer.customer_id,
        )

    def test_natural_identifier_uniqueness(self):
        self.repository.create(
            "alice@example.com",
            "Alice",
            "IN",
        )

        with self.assertRaises(DuplicateKeyError):
            self.repository.create(
                "ALICE@example.com",
                "Another Alice",
                "IN",
            )

    def test_email_change_preserves_surrogate_keys(self):
        customer = self.repository.create(
            "alice@example.com",
            "Alice",
            "IN",
        )

        original_id = customer.customer_id
        original_uuid = customer.public_id

        self.repository.update_email(
            original_id,
            "alice.new@example.com",
        )

        updated = self.repository.get_by_id(original_id)

        self.assertEqual(updated.public_id, original_uuid)
        self.assertEqual(updated.email, "alice.new@example.com")

    def test_duplicate_email_update_is_rejected(self):
        first = self.repository.create(
            "first@example.com",
            "First",
            "IN",
        )

        self.repository.create(
            "second@example.com",
            "Second",
            "IN",
        )

        with self.assertRaises(DuplicateKeyError):
            self.repository.update_email(
                first.customer_id,
                "second@example.com",
            )

    def test_composite_natural_key(self):
        registry = NaturalKeyRegistry()

        registry.register("IN", "ID-10001", "Customer One")

        with self.assertRaises(DuplicateKeyError):
            registry.register("IN", "ID-10001", "Customer Two")

        # The same identifier in a different country is distinct.
        registry.register("US", "ID-10001", "Customer Three")

        self.assertEqual(len(registry._records), 2)

    def test_invalid_country(self):
        with self.assertRaises(ValidationError):
            self.repository.create(
                "test@example.com",
                "Test",
                "IND",
            )

    def test_missing_record(self):
        with self.assertRaises(RecordNotFoundError):
            self.repository.get_by_id(999)

    def test_delete_cleans_indexes(self):
        customer = self.repository.create(
            "delete@example.com",
            "Delete Me",
            "IN",
        )

        self.repository.delete(customer.customer_id)

        with self.assertRaises(RecordNotFoundError):
            self.repository.get_by_uuid(customer.public_id)

    def test_invalid_email(self):
        with self.assertRaises(ValidationError):
            self.repository.create(
                "invalid-email",
                "Invalid",
                "IN",
            )


def demonstrate():
    repository = CustomerRepository()
    registry = NaturalKeyRegistry()

    print("=" * 65)
    print("SURROGATE VS NATURAL KEY DEMONSTRATION")
    print("=" * 65)

    alice = repository.create(
        email="alice@example.com",
        full_name="Alice Sharma",
        country_code="IN",
        external_reference="ERP-CUST-1001",
    )

    bob = repository.create(
        email="bob@example.com",
        full_name="Bob Verma",
        country_code="IN",
        external_reference="ERP-CUST-1002",
    )

    print("\n1. Surrogate identifiers")
    for customer in repository.all_customers():
        print(
            f"ID={customer.customer_id}, "
            f"UUID={customer.public_id}, "
            f"Email={customer.email}"
        )

    print("\n2. Natural identifier lookup")
    found = repository.get_by_email("ALICE@EXAMPLE.COM")
    print(f"Found: {found.full_name}")

    print("\n3. Updating a natural identifier")
    original_id = alice.customer_id
    original_uuid = alice.public_id

    repository.update_email(
        alice.customer_id,
        "alice.sharma@example.com",
    )

    print(f"Updated email: {alice.email}")
    print(f"Integer ID unchanged: {alice.customer_id == original_id}")
    print(f"UUID unchanged: {alice.public_id == original_uuid}")

    print("\n4. Composite natural key")
    registry.register("IN", "TAX-10001", "Enterprise One")
    registry.register("US", "TAX-10001", "Enterprise Two")

    print(f"Registered composite keys: {len(registry._records)}")

    print("\n5. Duplicate key handling")
    try:
        repository.create(
            "BOB@EXAMPLE.COM",
            "Duplicate Bob",
            "IN",
        )
    except DuplicateKeyError as error:
        print(f"Rejected: {error}")

    print("\n6. Identifier comparison")
    for strategy, details in KeyDesignAnalyzer.compare().items():
        print(f"\n{strategy.upper()}")
        for attribute, value in details.items():
            print(f"  {attribute}: {value}")

    print("\n7. Repository statistics")
    print(repository.statistics())

    print("\n8. Referential identity")
    print(f"Customer ID: {bob.customer_id}")
    print(f"Public UUID: {bob.public_id}")
    print(f"Email: {bob.email}")


if __name__ == "__main__":
    demonstrate()

    print("\n" + "=" * 65)
    print("RUNNING UNIT TESTS")
    print("=" * 65)

    unittest.main(argv=["surrogate_natural_keys.py"], exit=False)
