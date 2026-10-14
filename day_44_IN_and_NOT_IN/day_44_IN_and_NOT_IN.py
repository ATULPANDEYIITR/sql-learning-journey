from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Employee:
    employee_id: int
    name: str
    department: Optional[str]
    status: str


def membership(value: Optional[str], candidates: Iterable[Optional[str]]) -> Optional[bool]:
    """
    Model SQL-style three-valued membership reasoning.

    Python's `in` operator normally returns True or False. SQL is different:
    comparisons involving NULL produce UNKNOWN, and WHERE keeps only TRUE.
    This function therefore returns True, False, or None.
    """
    values = list(candidates)

    if value is None:
        return None

    if value in values:
        return True

    if any(candidate is None for candidate in values):
        return None

    return False


def sql_not(value: Optional[bool]) -> Optional[bool]:
    """Negate a SQL truth value while preserving UNKNOWN."""
    if value is None:
        return None
    return not value


def sql_where(value: Optional[bool]) -> bool:
    """A SQL WHERE clause retains only TRUE."""
    return value is True


def demonstrate_basic_membership() -> None:
    print("Basic membership")

    allowed_departments = {"Engineering", "Security", "Research"}

    employee_departments = [
        "Engineering",
        "Finance",
        "Security",
        None,
    ]

    for department in employee_departments:
        result = membership(department, allowed_departments)
        print(f"{department!r:12} IN allowed set -> {result}")

    print()


def demonstrate_not_in_null_trap() -> None:
    print("NOT IN and NULL")

    blocked_departments = ["Finance", None]

    for department in ["Engineering", "Finance", "Security", None]:
        in_result = membership(department, blocked_departments)
        not_in_result = sql_not(in_result)

        print(
            f"{department!r:12} "
            f"IN {blocked_departments!r:<20} -> {in_result!s:<5} "
            f"NOT IN -> {not_in_result!s:<5} "
            f"WHERE keeps row -> {sql_where(not_in_result)}"
        )

    print(
        "\nThe important case is Engineering: "
        "Engineering is not Finance, but comparison with NULL is UNKNOWN. "
        "Therefore NOT IN becomes UNKNOWN rather than TRUE."
    )
    print()


def demonstrate_where_semantics() -> None:
    print("SQL WHERE keeps TRUE, not FALSE or UNKNOWN")

    results = [
        ("Engineering", True),
        ("Finance", False),
        ("Research", None),
    ]

    for department, predicate_result in results:
        if sql_where(predicate_result):
            print(f"Returned: {department}")
        else:
            print(f"Filtered: {department} because predicate = {predicate_result}")

    print()


def demonstrate_safe_alternatives() -> None:
    print("Safe alternatives to NOT IN when NULL may exist")

    employees = [
        Employee(1, "Asha", "Engineering", "active"),
        Employee(2, "Ravi", "Finance", "active"),
        Employee(3, "Mira", "Security", "active"),
        Employee(4, "Noor", None, "active"),
    ]

    blocked = ["Finance", None]

    print("Original NOT IN semantics:")
    for employee in employees:
        result = membership(employee.department, blocked)
        if sql_where(sql_not(result)):
            print(f"  selected: {employee.name}")

    print("\nPython-side equivalent of an explicit NULL-safe policy:")
    for employee in employees:
        if employee.department is not None and employee.department not in {
            x for x in blocked if x is not None
        }:
            print(f"  selected: {employee.name}")

    print(
        "\nIn SQL, the corresponding database-safe pattern is usually "
        "NOT EXISTS when the exclusion set comes from another relation."
    )
    print()


def demonstrate_exists_logic() -> None:
    print("NOT EXISTS conceptual model")

    employees = [
        Employee(1, "Asha", "Engineering", "active"),
        Employee(2, "Ravi", "Finance", "active"),
        Employee(3, "Mira", "Security", "active"),
        Employee(4, "Noor", None, "active"),
    ]

    blocked_departments = ["Finance", None]

    for employee in employees:
        matching_block = any(
            employee.department is not None
            and employee.department == blocked
            for blocked in blocked_departments
            if blocked is not None
        )

        not_exists = not matching_block

        if not_exists:
            print(f"{employee.name:6} -> allowed")
        else:
            print(f"{employee.name:6} -> blocked")

    print(
        "\nThe comparison is evaluated only against actual non-NULL values. "
        "A NULL row in the exclusion relation does not poison NOT EXISTS."
    )
    print()


def demonstrate_set_operations() -> None:
    print("Python set membership versus SQL NULL semantics")

    candidate_ids = {101, 102, 103, 104}
    requested_ids = {102, 104, 999}

    print("Python intersection:", sorted(candidate_ids & requested_ids))
    print("Python difference:", sorted(candidate_ids - requested_ids))

    print(
        "\nThese set operations are useful for application-side filtering, "
        "but they are not a substitute for understanding SQL three-valued logic."
    )
    print()


def demonstrate_edge_cases() -> None:
    print("Edge cases")

    cases = [
        ("value exists", "Engineering", ["Engineering", "Security"]),
        ("value absent", "Finance", ["Engineering", "Security"]),
        ("candidate NULL", "Finance", ["Engineering", None]),
        ("value NULL", None, ["Engineering", "Security"]),
        ("both NULL", None, ["Engineering", None]),
        ("empty candidate set", "Finance", []),
    ]

    for label, value, candidates in cases:
        result = membership(value, candidates)
        print(f"{label:22} value={value!r:14} candidates={candidates!r:30} result={result}")

    print()


def validate_identifier_set(values: Iterable[int]) -> set[int]:
    """Validate a set of IDs before using it in application-generated SQL."""
    result = set()

    for value in values:
        if not isinstance(value, int):
            raise TypeError(f"Employee ID must be an integer: {value!r}")
        if value <= 0:
            raise ValueError(f"Employee ID must be positive: {value}")
        result.add(value)

    return result


def build_parameterized_in_clause(
    column: str,
    values: Iterable[int],
) -> tuple[str, list[int]]:
    """
    Build an IN predicate using placeholders rather than interpolating values.

    This demonstrates the application-layer concern surrounding membership
    predicates: values should be parameters, not SQL source text.
    """
    if not column.replace("_", "").isalnum():
        raise ValueError("Unsafe column identifier")

    validated = sorted(validate_identifier_set(values))

    if not validated:
        return "FALSE", []

    placeholders = ", ".join(["%s"] * len(validated))
    return f"{column} IN ({placeholders})", validated


def demonstrate_parameterization() -> None:
    print("Parameterized membership predicate")

    predicate, parameters = build_parameterized_in_clause(
        "employee_id",
        [104, 101, 103],
    )

    print("SQL predicate:", predicate)
    print("Parameters:", parameters)

    print(
        "\nThe values are passed separately from SQL syntax. "
        "This avoids turning user-controlled membership values into executable SQL."
    )
    print()


def demonstrate_performance_reasoning() -> None:
    print("Performance considerations")

    large_membership_set = set(range(1, 100_001))

    probes = [1, 50_000, 100_000, 150_000]

    for probe in probes:
        print(f"{probe:7} -> {probe in large_membership_set}")

    print(
        "\nPython sets provide average O(1) membership lookup. "
        "Database IN performance depends on the query plan, number of values, "
        "indexes, cardinality, statistics, and whether the values come from "
        "a relation. For large relational exclusion sets, NOT EXISTS or a "
        "join-based design is often more appropriate than constructing a huge IN list."
    )
    print()


def main() -> None:
    print("=" * 72)
    print("IN and NOT IN: Membership Tests, NULL Pitfalls, and Alternatives")
    print("=" * 72)
    print()

    demonstrate_basic_membership()
    demonstrate_not_in_null_trap()
    demonstrate_where_semantics()
    demonstrate_safe_alternatives()
    demonstrate_exists_logic()
    demonstrate_set_operations()
    demonstrate_edge_cases()
    demonstrate_parameterization()
    demonstrate_performance_reasoning()

    print("Demonstration complete.")


if __name__ == "__main__":
    main()
