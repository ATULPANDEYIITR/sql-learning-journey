"""
PRIMARY KEY
===========

A comprehensive standalone study file covering:

1. Primary-key fundamentals
2. Entity identification
3. Uniqueness and NOT NULL semantics
4. Candidate keys and alternate keys
5. Natural and surrogate keys
6. Composite primary keys
7. Foreign-key relationships
8. Referential integrity
9. Validation and error handling
10. In-memory relational modeling
11. SQL schema examples
12. Key generation strategies
13. Mutable natural keys
14. Duplicate and missing identifiers
15. Performance and indexing
16. Security considerations
17. Advanced design trade-offs
18. A small order-management case study
19. Testing and edge cases

The program intentionally uses only the Python standard library so that it
can be executed without external dependencies.

Run with:
    python primary_key.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Generic, Hashable, Iterable, List, Optional, Tuple, TypeVar
from uuid import UUID, uuid4
import hashlib
import re
import sqlite3
import time


# ============================================================================
# 1. FUNDAMENTAL CONCEPT
# ============================================================================

def print_section(title: str) -> None:
    """Print a visually consistent section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def explain_fundamentals() -> None:
    print_section("1. PRIMARY-KEY FUNDAMENTALS")

    print(
        """
A primary key is a column or set of columns chosen to uniquely identify
each row in a relational table.

Important properties:

    UNIQUE:
        Two rows cannot have the same primary-key value.

    NOT NULL:
        A primary-key value cannot be absent.

    IDENTIFICATION:
        The key identifies one specific entity or relationship instance.

    STABILITY:
        A well-designed key should normally remain unchanged.

    MINIMALITY:
        A candidate key should contain no unnecessary attributes.

Examples:

    students(student_id, name, email)
        student_id can identify one student.

    products(product_id, name, price)
        product_id can identify one product.

    enrollments(student_id, course_id, enrolled_on)
        (student_id, course_id) can identify one enrollment.

A primary key can contain one column or several columns.
"""
    )


# ============================================================================
# 2. SIMPLE RELATIONAL TABLE MODEL
# ============================================================================

T = TypeVar("T", bound=Hashable)


class DuplicateKeyError(ValueError):
    """Raised when an inserted row conflicts with an existing primary key."""


class MissingKeyError(ValueError):
    """Raised when a row has no valid primary-key value."""


class ForeignKeyError(ValueError):
    """Raised when a foreign-key reference does not exist."""


class ValidationError(ValueError):
    """Raised when a row violates a table constraint."""


class Table(Generic[T]):
    """
    A small in-memory relational table.

    The dictionary models the most important behavior of a primary-key index:
    key -> row.

    This is educational and does not attempt to reproduce a full database
    engine.
    """

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.rows: Dict[T, dict] = {}

    def insert(self, primary_key: T, row: dict) -> None:
        if primary_key is None:
            raise MissingKeyError(
                f"{self.table_name}: primary key cannot be None"
            )

        if primary_key in self.rows:
            raise DuplicateKeyError(
                f"{self.table_name}: duplicate primary key {primary_key!r}"
            )

        self.rows[primary_key] = dict(row)

    def get(self, primary_key: T) -> Optional[dict]:
        return self.rows.get(primary_key)

    def exists(self, primary_key: T) -> bool:
        return primary_key in self.rows

    def delete(self, primary_key: T) -> bool:
        return self.rows.pop(primary_key, None) is not None

    def count(self) -> int:
        return len(self.rows)

    def all_rows(self) -> List[dict]:
        return list(self.rows.values())


def demonstrate_simple_key() -> None:
    print_section("2. SIMPLE PRIMARY KEY")

    students = Table[int]("students")

    students.insert(
        101,
        {
            "student_id": 101,
            "name": "Asha",
            "email": "asha@example.com",
        },
    )

    students.insert(
        102,
        {
            "student_id": 102,
            "name": "Rahul",
            "email": "rahul@example.com",
        },
    )

    print("Student 101:", students.get(101))
    print("Student count:", students.count())

    try:
        students.insert(
            101,
            {
                "student_id": 101,
                "name": "Different Person",
                "email": "different@example.com",
            },
        )
    except DuplicateKeyError as error:
        print("Duplicate rejected:", error)

    try:
        students.insert(
            None,
            {
                "student_id": None,
                "name": "Missing ID",
                "email": "missing@example.com",
            },
        )
    except MissingKeyError as error:
        print("Missing key rejected:", error)


# ============================================================================
# 3. ENTITY IDENTIFICATION
# ============================================================================

@dataclass(frozen=True)
class Student:
    student_id: int
    name: str
    email: str


def demonstrate_entity_identification() -> None:
    print_section("3. ENTITY IDENTIFICATION")

    students = {
        1001: Student(1001, "Anita", "anita@example.com"),
        1002: Student(1002, "Vikram", "vikram@example.com"),
    }

    requested_id = 1002
    student = students.get(requested_id)

    print("Requested entity:", student)

    print(
        """
The identifier is not merely an arbitrary number. Its relational purpose is
to answer:

    "Which exact row represents this entity?"

An email address may also appear unique, but it can be changed. A stable
student_id can remain the identity of the student even if the email changes.
"""
    )


# ============================================================================
# 4. CANDIDATE KEYS, ALTERNATE KEYS, AND PRIMARY KEY SELECTION
# ============================================================================

@dataclass(frozen=True)
class CandidateKey:
    name: str
    columns: Tuple[str, ...]
    is_primary: bool = False


def demonstrate_candidate_keys() -> None:
    print_section("4. CANDIDATE KEYS AND ALTERNATE KEYS")

    candidates = [
        CandidateKey("Student ID", ("student_id",), True),
        CandidateKey("University Registration Number", ("registration_no",)),
        CandidateKey("Email", ("email",)),
    ]

    for candidate in candidates:
        kind = "PRIMARY" if candidate.is_primary else "ALTERNATE"
        print(f"{kind:9} {candidate.name}: {candidate.columns}")

    print(
        """
A candidate key is a minimal attribute set capable of uniquely identifying
rows.

One candidate key is selected as the primary key.

Other candidate keys can be enforced with UNIQUE constraints and are often
called alternate keys.

A column being unique does not automatically make it the primary key.
"""
    )


# ============================================================================
# 5. NATURAL VS SURROGATE KEYS
# ============================================================================

def demonstrate_natural_vs_surrogate() -> None:
    print_section("5. NATURAL KEYS VS SURROGATE KEYS")

    print(
        """
Natural key:
    An identifier with business meaning.

    Example:
        country_code = "IN"
        ISBN
        employee_number

Advantages:
    - Meaningful
    - Can already exist in the source system
    - May avoid an unnecessary artificial identifier

Risks:
    - Business rules can change
    - Values may be long
    - Data quality can be difficult
    - Privacy-sensitive values may be inappropriate
    - Composite natural keys can make relationships cumbersome

Surrogate key:
    An identifier created specifically for database identity.

Examples:
    integer sequence
    UUID
    generated database identity

Advantages:
    - Stable
    - Usually compact or standardized
    - Separates identity from changing business attributes

Risks:
    - Does not carry business meaning
    - Requires another constraint if a business identifier must be unique
    - UUIDs can consume more storage than small integers
"""
    )


# ============================================================================
# 6. COMPOSITE PRIMARY KEYS
# ============================================================================

CompositeKey = Tuple[int, int]


def demonstrate_composite_key() -> None:
    print_section("6. COMPOSITE PRIMARY KEYS")

    enrollments = Table[CompositeKey]("enrollments")

    enrollments.insert(
        (101, 501),
        {
            "student_id": 101,
            "course_id": 501,
            "grade": "A",
        },
    )

    enrollments.insert(
        (101, 502),
        {
            "student_id": 101,
            "course_id": 502,
            "grade": "B",
        },
    )

    enrollments.insert(
        (102, 501),
        {
            "student_id": 102,
            "course_id": 501,
            "grade": "A",
        },
    )

    print("Enrollment (101, 501):", enrollments.get((101, 501)))

    try:
        enrollments.insert(
            (101, 501),
            {
                "student_id": 101,
                "course_id": 501,
                "grade": "C",
            },
        )
    except DuplicateKeyError as error:
        print("Duplicate composite key rejected:", error)

    print(
        """
A composite key identifies a row through a combination of attributes.

For:

    enrollment(student_id, course_id)

student_id alone is not unique because one student can take many courses.

course_id alone is not unique because one course can contain many students.

Together:

    (student_id, course_id)

identify one enrollment.
"""
    )


# ============================================================================
# 7. FOREIGN KEYS AND REFERENTIAL INTEGRITY
# ============================================================================

@dataclass
class Enrollment:
    student_id: int
    course_id: int


def validate_foreign_key(
    referenced_table: Table[int],
    referenced_key: int,
    child_table_name: str,
) -> None:
    if not referenced_table.exists(referenced_key):
        raise ForeignKeyError(
            f"{child_table_name}: referenced key {referenced_key} does not exist"
        )


def demonstrate_foreign_keys() -> None:
    print_section("7. FOREIGN KEYS AND REFERENTIAL INTEGRITY")

    students = Table[int]("students")
    students.insert(1, {"student_id": 1, "name": "Asha"})
    students.insert(2, {"student_id": 2, "name": "Ravi"})

    enrollments = Table[CompositeKey]("enrollments")

    enrollment = Enrollment(student_id=1, course_id=900)

    validate_foreign_key(students, enrollment.student_id, "enrollments")

    enrollments.insert(
        (enrollment.student_id, enrollment.course_id),
        {
            "student_id": enrollment.student_id,
            "course_id": enrollment.course_id,
        },
    )

    print("Valid enrollment inserted.")

    invalid = Enrollment(student_id=999, course_id=900)

    try:
        validate_foreign_key(students, invalid.student_id, "enrollments")
    except ForeignKeyError as error:
        print("Invalid reference rejected:", error)

    print(
        """
Primary keys and foreign keys work together.

Parent:
    students(student_id PRIMARY KEY)

Child:
    enrollments(student_id FOREIGN KEY REFERENCES students)

The primary key establishes identity in the parent table.
The foreign key ensures that a referenced parent identity exists.
"""
    )


# ============================================================================
# 8. NATURAL KEY MUTABILITY
# ============================================================================

def demonstrate_mutable_identifier_problem() -> None:
    print_section("8. MUTABLE NATURAL IDENTIFIERS")

    print(
        """
Suppose email is used as the primary key:

    customer(email PRIMARY KEY, name)

If a customer changes:

    old@example.com -> new@example.com

every referencing row must account for the change.

With:

    customer(customer_id PRIMARY KEY, email UNIQUE, name)

the identity remains customer_id while email can change.

This is one reason surrogate keys are common in systems where business
attributes are mutable.
"""
    )


# ============================================================================
# 9. SQL PRIMARY KEY SYNTAX
# ============================================================================

def sql_schema_examples() -> None:
    print_section("9. SQL PRIMARY-KEY DEFINITIONS")

    examples = [
        """
CREATE TABLE students (
    student_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);
""",
        """
CREATE TABLE enrollments (
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    enrolled_on TEXT NOT NULL,
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);
""",
        """
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    serial_number TEXT NOT NULL UNIQUE
);
""",
    ]

    for index, sql in enumerate(examples, start=1):
        print(f"Example {index}:")
        print(sql.strip())


# ============================================================================
# 10. SQLITE EXECUTABLE EXAMPLE
# ============================================================================

def demonstrate_sqlite() -> None:
    print_section("10. EXECUTABLE SQLITE EXAMPLE")

    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")

    connection.execute(
        """
        CREATE TABLE customer (
            customer_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE product (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            price_cents INTEGER NOT NULL CHECK (price_cents >= 0)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE order_item (
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY (product_id) REFERENCES product(product_id)
        )
        """
    )

    connection.execute(
        "INSERT INTO customer(customer_id, email, name) VALUES (?, ?, ?)",
        (1, "customer@example.com", "Customer One"),
    )

    connection.execute(
        "INSERT INTO product(product_id, product_name, price_cents) VALUES (?, ?, ?)",
        (10, "Keyboard", 4999),
    )

    connection.execute(
        """
        INSERT INTO order_item(order_id, product_id, quantity)
        VALUES (?, ?, ?)
        """,
        (5001, 10, 2),
    )

    row = connection.execute(
        "SELECT order_id, product_id, quantity FROM order_item"
    ).fetchone()

    print("Valid order item:", row)

    try:
        connection.execute(
            """
            INSERT INTO order_item(order_id, product_id, quantity)
            VALUES (?, ?, ?)
            """,
            (5001, 10, 3),
        )
    except sqlite3.IntegrityError as error:
        print("Composite primary-key violation:", error)

    try:
        connection.execute(
            """
            INSERT INTO order_item(order_id, product_id, quantity)
            VALUES (?, ?, ?)
            """,
            (5002, 9999, 1),
        )
    except sqlite3.IntegrityError as error:
        print("Foreign-key violation:", error)

    connection.close()


# ============================================================================
# 11. UUID PRIMARY KEYS
# ============================================================================

def uuid_primary_key_example() -> None:
    print_section("11. UUID AS A SURROGATE PRIMARY KEY")

    first_id: UUID = uuid4()
    second_id: UUID = uuid4()

    records = {
        first_id: {"name": "Service A"},
        second_id: {"name": "Service B"},
    }

    for identifier, record in records.items():
        print(identifier, "->", record)

    print(
        """
UUIDs are useful when identifiers must be generated independently by
different application instances.

Benefits:
    - Extremely low collision probability
    - Can be generated without a central sequence
    - Useful for distributed systems

Trade-offs:
    - Larger than small integer identifiers
    - Random UUIDs can have less favorable index locality
    - Human readability is poor
"""
    )


# ============================================================================
# 12. DETERMINISTIC HASH-BASED IDENTIFIERS
# ============================================================================

def deterministic_identifier(value: str) -> str:
    """Create a stable digest for demonstration purposes."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def demonstrate_hash_identifier() -> None:
    print_section("12. HASHES ARE NOT AUTOMATICALLY PRIMARY KEYS")

    value = "example-record"
    digest = deterministic_identifier(value)

    print("Input:", value)
    print("SHA-256:", digest)

    print(
        """
A hash can be unique enough for a particular engineering use case, but a
hash function should not be confused with a formal relational key.

A database key still requires an explicit uniqueness constraint.

Hash collisions are theoretically possible, so applications should choose
an identifier strategy based on the actual requirements.
"""
    )


# ============================================================================
# 13. KEY VALIDATION
# ============================================================================

def validate_integer_identifier(identifier: object) -> int:
    if isinstance(identifier, bool):
        raise ValidationError("Boolean values are not valid integer IDs.")

    if not isinstance(identifier, int):
        raise ValidationError("Identifier must be an integer.")

    if identifier <= 0:
        raise ValidationError("Identifier must be positive.")

    return identifier


def validate_uuid_identifier(identifier: str) -> UUID:
    try:
        return UUID(identifier)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValidationError("Invalid UUID identifier.") from error


def demonstrate_validation() -> None:
    print_section("13. KEY VALIDATION")

    valid = [1, 42, 100000]

    for identifier in valid:
        print("Accepted:", validate_integer_identifier(identifier))

    invalid = [0, -1, True, "100", None]

    for identifier in invalid:
        try:
            validate_integer_identifier(identifier)
        except ValidationError as error:
            print(f"Rejected {identifier!r}: {error}")

    generated = str(uuid4())
    print("Valid UUID:", validate_uuid_identifier(generated))


# ============================================================================
# 14. COMPOSITE KEY OBJECT
# ============================================================================

@dataclass(frozen=True)
class OrderLineKey:
    """
    Explicit composite-key value object.

    frozen=True makes the object immutable, which is useful because keys
    should not silently change while they are being used for identification.
    """

    order_id: int
    product_id: int

    def __post_init__(self) -> None:
        if self.order_id <= 0:
            raise ValidationError("order_id must be positive.")
        if self.product_id <= 0:
            raise ValidationError("product_id must be positive.")


def demonstrate_composite_key_object() -> None:
    print_section("14. COMPOSITE KEY AS AN IMMUTABLE OBJECT")

    key = OrderLineKey(order_id=7001, product_id=45)

    table = Table[OrderLineKey]("order_line")
    table.insert(
        key,
        {
            "order_id": key.order_id,
            "product_id": key.product_id,
            "quantity": 4,
        },
    )

    print("Stored row:", table.get(key))

    try:
        key.order_id = 9999  # type: ignore[misc]
    except Exception as error:
        print("Immutable key rejected:", type(error).__name__)


# ============================================================================
# 15. PERFORMANCE: DICTIONARY INDEXING
# ============================================================================

def performance_demo() -> None:
    print_section("15. PRIMARY-KEY LOOKUP PERFORMANCE")

    records = {identifier: f"Entity {identifier}" for identifier in range(100_000)}

    start = time.perf_counter()
    result = records.get(99_999)
    elapsed = time.perf_counter() - start

    print("Lookup result:", result)
    print(f"Dictionary lookup elapsed time: {elapsed:.9f} seconds")

    print(
        """
This dictionary demonstration approximates indexed lookup rather than
database internals.

A database primary key normally has an associated index or index-like
structure, depending on the database engine.

Conceptually:

    scan every row:
        approximately O(n)

    indexed lookup:
        commonly approximately O(log n) for a B-tree
        or approximately O(1) average for a hash-based structure

Actual database behavior depends on the engine, index structure, storage
layout, cache state, query plan, and workload.
"""
    )


# ============================================================================
# 16. COMPOSITE INDEX ORDER
# ============================================================================

def composite_index_explanation() -> None:
    print_section("16. COMPOSITE KEY ORDER MATTERS")

    print(
        """
Consider:

    PRIMARY KEY (customer_id, order_id)

The index is ordered around the first component and then the second.

Queries filtering by:

    customer_id

can often use the leading portion of the composite index efficiently.

A query filtering only by:

    order_id

may not receive the same benefit from that index.

Therefore, column order in a composite key has practical performance
consequences.

The logical uniqueness rule and the physical index design are related but
are not conceptually identical.
"""
    )


# ============================================================================
# 17. NULL SEMANTICS
# ============================================================================

def null_semantics_explanation() -> None:
    print_section("17. NULL AND PRIMARY KEYS")

    print(
        """
A primary key represents identity, so an unknown or absent identity is
generally invalid.

A primary key therefore has NOT NULL semantics.

This differs from ordinary UNIQUE constraints in some database systems,
where NULL handling can have engine-specific behavior.

For example, SQL uses three-valued logic:

    TRUE
    FALSE
    UNKNOWN

NULL is not an ordinary value that compares equal to another NULL.

Primary-key design avoids this ambiguity by requiring an actual identifier.
"""
    )


# ============================================================================
# 18. DELETION AND REFERENTIAL ACTIONS
# ============================================================================

def referential_actions_explanation() -> None:
    print_section("18. DELETIONS AND REFERENTIAL INTEGRITY")

    print(
        """
Suppose:

    customer(customer_id PRIMARY KEY)
    order(order_id PRIMARY KEY, customer_id FOREIGN KEY)

Deleting a customer can affect orders.

Common database policies include:

    RESTRICT / NO ACTION
        Reject deletion while dependent rows exist.

    CASCADE
        Delete dependent rows automatically.

    SET NULL
        Remove the reference by setting the foreign key to NULL, if allowed.

The appropriate action depends on business semantics.

CASCADE is convenient but can remove more data than an operator expects.
RESTRICT can preserve historical records but may require explicit cleanup.
"""
    )


# ============================================================================
# 19. ORDER MANAGEMENT CASE STUDY
# ============================================================================

@dataclass
class Customer:
    customer_id: int
    email: str
    name: str


@dataclass
class Product:
    product_id: int
    name: str
    price_cents: int


@dataclass
class OrderLine:
    order_id: int
    product_id: int
    quantity: int


class OrderManagementSystem:
    """
    Small relational-style application.

    Primary keys:
        Customer.customer_id
        Product.product_id
        OrderLine(order_id, product_id)

    Foreign keys:
        OrderLine.product_id -> Product.product_id

    The example deliberately uses explicit dictionaries to make the identity
    structures visible rather than hiding them behind a database ORM.
    """

    def __init__(self) -> None:
        self.customers: Dict[int, Customer] = {}
        self.products: Dict[int, Product] = {}
        self.order_lines: Dict[OrderLineKey, OrderLine] = {}

    def add_customer(self, customer: Customer) -> None:
        if customer.customer_id <= 0:
            raise ValidationError("Customer ID must be positive.")

        if not customer.email or "@" not in customer.email:
            raise ValidationError("Customer email is invalid.")

        if customer.customer_id in self.customers:
            raise DuplicateKeyError("Customer ID already exists.")

        if any(existing.email == customer.email for existing in self.customers.values()):
            raise ValidationError("Customer email must be unique.")

        self.customers[customer.customer_id] = customer

    def add_product(self, product: Product) -> None:
        if product.product_id <= 0:
            raise ValidationError("Product ID must be positive.")

        if not product.name.strip():
            raise ValidationError("Product name cannot be empty.")

        if product.price_cents < 0:
            raise ValidationError("Product price cannot be negative.")

        if product.product_id in self.products:
            raise DuplicateKeyError("Product ID already exists.")

        self.products[product.product_id] = product

    def add_order_line(self, line: OrderLine) -> None:
        if line.order_id <= 0:
            raise ValidationError("Order ID must be positive.")

        if line.product_id not in self.products:
            raise ForeignKeyError("Product does not exist.")

        if line.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        key = OrderLineKey(line.order_id, line.product_id)

        if key in self.order_lines:
            raise DuplicateKeyError(
                "The same product can occur only once per order."
            )

        self.order_lines[key] = line

    def calculate_order_total(self, order_id: int) -> int:
        total = 0

        for line in self.order_lines.values():
            if line.order_id == order_id:
                product = self.products[line.product_id]
                total += product.price_cents * line.quantity

        return total


def run_order_case_study() -> None:
    print_section("19. INDUSTRY-STYLE ORDER CASE STUDY")

    system = OrderManagementSystem()

    system.add_customer(
        Customer(
            customer_id=1,
            email="buyer@example.com",
            name="Buyer",
        )
    )

    system.add_product(
        Product(
            product_id=101,
            name="Keyboard",
            price_cents=5000,
        )
    )

    system.add_product(
        Product(
            product_id=102,
            name="Mouse",
            price_cents=2500,
        )
    )

    system.add_order_line(
        OrderLine(
            order_id=9001,
            product_id=101,
            quantity=2,
        )
    )

    system.add_order_line(
        OrderLine(
            order_id=9001,
            product_id=102,
            quantity=1,
        )
    )

    total = system.calculate_order_total(9001)

    print("Order 9001 total:", total, "cents")

    test_cases = [
        lambda: system.add_product(
            Product(101, "Duplicate Keyboard", 7000)
        ),
        lambda: system.add_order_line(
            OrderLine(9001, 101, 1)
        ),
        lambda: system.add_order_line(
            OrderLine(9002, 999, 1)
        ),
        lambda: system.add_order_line(
            OrderLine(9003, 101, 0)
        ),
    ]

    for test_case in test_cases:
        try:
            test_case()
        except (DuplicateKeyError, ForeignKeyError, ValidationError) as error:
            print("Expected failure:", error)


# ============================================================================
# 20. KEY DESIGN DECISION MATRIX
# ============================================================================

def design_decision_matrix() -> None:
    print_section("20. PRIMARY-KEY DESIGN DECISIONS")

    rows = [
        ("Small internal identity", "Integer surrogate", "Compact and simple"),
        ("Distributed identifier", "UUID", "Can be generated independently"),
        ("Relationship table", "Composite key", "Represents combination identity"),
        ("Stable business identifier", "Natural key", "Meaningful if genuinely immutable"),
        ("Mutable business attribute", "Surrogate + UNIQUE", "Separates identity from business data"),
    ]

    for scenario, strategy, reason in rows:
        print(f"{scenario:32} | {strategy:25} | {reason}")


# ============================================================================
# 21. COMMON MISTAKES
# ============================================================================

def common_mistakes() -> None:
    print_section("21. COMMON PRIMARY-KEY MISTAKES")

    mistakes = [
        "Allowing duplicate identifiers",
        "Allowing NULL identity values",
        "Using mutable business data without considering updates",
        "Assuming UNIQUE automatically means PRIMARY KEY",
        "Using only one column when identity is actually composite",
        "Using a composite key without considering relationship complexity",
        "Exposing sensitive business identifiers unnecessarily",
        "Ignoring foreign-key integrity",
        "Using application-only uniqueness checks without database constraints",
        "Assuming every UUID/index workload has identical performance",
        "Changing identifiers casually after dependent records exist",
        "Failing to test duplicate, missing, and referenced-key cases",
    ]

    for number, mistake in enumerate(mistakes, start=1):
        print(f"{number:2}. {mistake}")


# ============================================================================
# 22. SECURITY CONSIDERATIONS
# ============================================================================

def security_considerations() -> None:
    print_section("22. SECURITY CONSIDERATIONS")

    print(
        """
A primary key is an identifier, not an authorization mechanism.

Never assume:

    knowing customer_id == permission to access customer data

Authorization must be checked separately.

Sequential IDs can also make enumeration easier:

    /customers/1001
    /customers/1002
    /customers/1003

An attacker may infer that nearby identifiers exist.

Possible mitigations include:
    - Proper authorization checks
    - Non-guessable public identifiers where appropriate
    - Rate limiting
    - Avoiding unnecessary identifier disclosure
    - Logging and monitoring
    - Separating internal database identity from public resource identifiers

A UUID does not replace authorization.
A UUID only changes the identifier characteristics.
"""
    )


# ============================================================================
# 23. TESTING
# ============================================================================

def run_tests() -> None:
    print_section("23. AUTOMATED TESTS")

    table = Table[int]("test_table")
    table.insert(1, {"id": 1})

    assert table.exists(1)
    assert table.get(1) == {"id": 1}
    assert table.count() == 1

    try:
        table.insert(1, {"id": 1})
        raise AssertionError("Duplicate key should have failed.")
    except DuplicateKeyError:
        pass

    try:
        table.insert(None, {"id": None})
        raise AssertionError("Missing key should have failed.")
    except MissingKeyError:
        pass

    key_a = OrderLineKey(1, 10)
    key_b = OrderLineKey(1, 10)

    assert key_a == key_b
    assert hash(key_a) == hash(key_b)

    print("All assertions passed.")


# ============================================================================
# 24. ADVANCED RELATIONAL OBSERVATIONS
# ============================================================================

def advanced_observations() -> None:
    print_section("24. ADVANCED PRIMARY-KEY OBSERVATIONS")

    print(
        """
1. PRIMARY KEY is a logical constraint.
   An index is a physical implementation detail, although many engines use
   an index to enforce the constraint efficiently.

2. A primary key may be clustered in some database engines.
   Clustered and non-clustered implementations have different storage and
   access characteristics.

3. Composite keys influence foreign keys.
   A child table referencing a composite parent key generally needs matching
   columns.

4. Key width matters.
   A large key can increase storage requirements for indexes and foreign keys.

5. Key distribution matters.
   Sequential and random identifiers can produce different insertion and
   locality behavior.

6. Identity and business uniqueness are different concerns.
   A surrogate primary key does not eliminate the need for UNIQUE constraints
   on business identifiers.

7. Keys should be designed with lifecycle behavior in mind.
   Consider creation, update, merge, deletion, replication, import, and
   synchronization before selecting an identifier.

8. Database constraints should enforce critical invariants.
   Application validation improves usability, but database constraints are
   the final line of integrity when multiple application processes can write
   the same database.
"""
    )


# ============================================================================
# 25. PRACTICAL IMPORTANCE OF TRANSACTIONS
# ============================================================================

def demonstrate_transactional_integrity() -> None:
    print_section("25. TRANSACTIONS AND PRIMARY-KEY INTEGRITY")

    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE account (
            account_id INTEGER PRIMARY KEY,
            owner TEXT NOT NULL
        )
        """
    )

    connection.execute(
        "INSERT INTO account(account_id, owner) VALUES (?, ?)",
        (1, "Alice"),
    )

    try:
        with connection:
            connection.execute(
                "INSERT INTO account(account_id, owner) VALUES (?, ?)",
                (2, "Bob"),
            )

            connection.execute(
                "INSERT INTO account(account_id, owner) VALUES (?, ?)",
                (1, "Duplicate Alice"),
            )
    except sqlite3.IntegrityError as error:
        print("Transaction failed:", error)

    rows = connection.execute(
        "SELECT account_id, owner FROM account ORDER BY account_id"
    ).fetchall()

    print("Rows after rollback:", rows)
    connection.close()

    print(
        """
A transaction can make a group of changes atomic.

If a later operation violates a primary-key constraint, the transaction can
be rolled back so that earlier changes in the same transaction are not left
partially committed.
"""
    )


# ============================================================================
# 26. MAIN
# ============================================================================

def main() -> None:
    explain_fundamentals()
    demonstrate_simple_key()
    demonstrate_entity_identification()
    demonstrate_candidate_keys()
    demonstrate_natural_vs_surrogate()
    demonstrate_composite_key()
    demonstrate_foreign_keys()
    demonstrate_mutable_identifier_problem()
    sql_schema_examples()
    demonstrate_sqlite()
    uuid_primary_key_example()
    demonstrate_hash_identifier()
    demonstrate_validation()
    demonstrate_composite_key_object()
    performance_demo()
    composite_index_explanation()
    null_semantics_explanation()
    referential_actions_explanation()
    run_order_case_study()
    design_decision_matrix()
    common_mistakes()
    security_considerations()
    run_tests()
    advanced_observations()
    demonstrate_transactional_integrity()

    print_section("27. END OF PRIMARY-KEY STUDY")
    print(
        "The examples above model primary keys as identity constraints, "
        "including simple, natural, surrogate, UUID, and composite keys."
    )


if __name__ == "__main__":
    main()
