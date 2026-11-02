from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable
from collections import defaultdict
import json


class NormalForm(str, Enum):
    UNNORMALIZED = "UNNORMALIZED"
    FIRST = "1NF"
    SECOND = "2NF"
    THIRD = "3NF"


@dataclass(frozen=True)
class Column:
    name: str
    atomic: bool = True


@dataclass(frozen=True)
class FunctionalDependency:
    determinant: frozenset[str]
    dependent: frozenset[str]

    def __str__(self) -> str:
        left = ", ".join(sorted(self.determinant))
        right = ", ".join(sorted(self.dependent))
        return f"{left} -> {right}"


@dataclass
class Relation:
    name: str
    columns: list[str]
    primary_key: frozenset[str]
    rows: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[FunctionalDependency] = field(default_factory=list)

    def validate(self) -> None:
        if not self.columns:
            raise ValueError("A relation must contain at least one column.")

        if not self.primary_key:
            raise ValueError("A relation must have a primary key.")

        unknown_key_columns = self.primary_key - set(self.columns)
        if unknown_key_columns:
            raise ValueError(
                f"Primary-key columns do not exist: {sorted(unknown_key_columns)}"
            )

        for row_number, row in enumerate(self.rows, start=1):
            missing = set(self.columns) - set(row)
            extra = set(row) - set(self.columns)

            if missing or extra:
                raise ValueError(
                    f"Row {row_number} has missing={sorted(missing)} "
                    f"and extra={sorted(extra)}."
                )

        keys = set()
        for row_number, row in enumerate(self.rows, start=1):
            key = tuple(row[column] for column in sorted(self.primary_key))
            if key in keys:
                raise ValueError(f"Duplicate primary key at row {row_number}: {key}")
            keys.add(key)

    def dependency_violations(self) -> list[str]:
        violations = []

        for fd in self.dependencies:
            determinant_values: dict[tuple[Any, ...], dict[str, Any]] = {}

            determinant_columns = sorted(fd.determinant)
            dependent_columns = sorted(fd.dependent)

            for row_number, row in enumerate(self.rows, start=1):
                determinant = tuple(row[column] for column in determinant_columns)

                if determinant not in determinant_values:
                    determinant_values[determinant] = {
                        column: row[column] for column in dependent_columns
                    }
                elif any(
                    determinant_values[determinant][column] != row[column]
                    for column in dependent_columns
                ):
                    violations.append(
                        f"{fd} is violated at row {row_number}: "
                        f"the same determinant has different dependent values."
                    )

        return violations


def is_atomic_value(value: Any) -> bool:
    if isinstance(value, (list, tuple, set, dict)):
        return False
    return True


def check_1nf(relation: Relation) -> tuple[bool, list[str]]:
    problems: list[str] = []

    try:
        relation.validate()
    except ValueError as exc:
        problems.append(str(exc))
        return False, problems

    for row_number, row in enumerate(relation.rows, start=1):
        for column, value in row.items():
            if not is_atomic_value(value):
                problems.append(
                    f"Row {row_number}, column '{column}' contains "
                    f"a non-atomic value."
                )

    return not problems, problems


def is_partial_dependency(
    relation: Relation,
    fd: FunctionalDependency,
) -> bool:
    key = relation.primary_key

    return (
        fd.determinant < key
        and fd.determinant
        and fd.dependent
        and fd.determinant.issubset(key)
        and not fd.dependent.issubset(key)
    )


def check_2nf(relation: Relation) -> tuple[bool, list[str]]:
    first_ok, problems = check_1nf(relation)

    for fd in relation.dependencies:
        if is_partial_dependency(relation, fd):
            problems.append(
                f"Partial dependency detected: {fd}. "
                f"The determinant is a proper subset of the composite key."
            )

    return not problems and first_ok, problems


def is_transitive_dependency(
    relation: Relation,
    fd: FunctionalDependency,
) -> bool:
    key = relation.primary_key

    # A direct key -> non-key dependency is not transitive by itself.
    if fd.determinant == key:
        return False

    if fd.dependent & key:
        return False

    # A non-key determinant determining a non-key attribute indicates
    # a transitive dependency when the determinant is reachable from the key.
    return bool(fd.determinant - key) and bool(fd.dependent - key)


def check_3nf(relation: Relation) -> tuple[bool, list[str]]:
    second_ok, problems = check_2nf(relation)

    for fd in relation.dependencies:
        if is_transitive_dependency(relation, fd):
            problems.append(
                f"Possible transitive dependency detected: {fd}. "
                f"A non-key attribute determines another non-key attribute."
            )

    return not problems and second_ok, problems


@dataclass
class NormalizationResult:
    form: NormalForm
    valid: bool
    problems: list[str]


def classify(relation: Relation) -> NormalizationResult:
    third_ok, third_problems = check_3nf(relation)
    if third_ok:
        return NormalizationResult(NormalForm.THIRD, True, [])

    second_ok, second_problems = check_2nf(relation)
    if second_ok:
        return NormalizationResult(NormalForm.SECOND, True, second_problems)

    first_ok, first_problems = check_1nf(relation)
    if first_ok:
        return NormalizationResult(NormalForm.FIRST, True, first_problems)

    return NormalizationResult(
        NormalForm.UNNORMALIZED,
        False,
        first_problems,
    )


class NormalizedDatabase:
    """
    A small in-memory 3NF design for a course-enrollment domain.

    The original relation mixes:
      enrollment_id, student_id, student_name,
      course_id, course_name, instructor_id, instructor_name, grade

    The normalized design separates facts according to their determinants.
    """

    def __init__(self) -> None:
        self.students: dict[int, dict[str, Any]] = {}
        self.instructors: dict[int, dict[str, Any]] = {}
        self.courses: dict[int, dict[str, Any]] = {}
        self.enrollments: dict[int, dict[str, Any]] = {}

    def add_student(self, student_id: int, name: str) -> None:
        if not name.strip():
            raise ValueError("Student name cannot be empty.")
        self.students[student_id] = {"student_id": student_id, "name": name}

    def add_instructor(self, instructor_id: int, name: str) -> None:
        if not name.strip():
            raise ValueError("Instructor name cannot be empty.")
        self.instructors[instructor_id] = {
            "instructor_id": instructor_id,
            "name": name,
        }

    def add_course(
        self,
        course_id: int,
        name: str,
        instructor_id: int,
    ) -> None:
        if instructor_id not in self.instructors:
            raise KeyError("Instructor does not exist.")
        if not name.strip():
            raise ValueError("Course name cannot be empty.")

        self.courses[course_id] = {
            "course_id": course_id,
            "name": name,
            "instructor_id": instructor_id,
        }

    def enroll(
        self,
        enrollment_id: int,
        student_id: int,
        course_id: int,
        grade: str | None,
    ) -> None:
        if student_id not in self.students:
            raise KeyError("Student does not exist.")

        if course_id not in self.courses:
            raise KeyError("Course does not exist.")

        if enrollment_id in self.enrollments:
            raise ValueError("Enrollment already exists.")

        if grade is not None and grade not in {"A", "B", "C", "D", "F"}:
            raise ValueError("Invalid grade.")

        duplicate = any(
            row["student_id"] == student_id and row["course_id"] == course_id
            for row in self.enrollments.values()
        )

        if duplicate:
            raise ValueError("The student is already enrolled in this course.")

        self.enrollments[enrollment_id] = {
            "enrollment_id": enrollment_id,
            "student_id": student_id,
            "course_id": course_id,
            "grade": grade,
        }

    def transcript(self, student_id: int) -> list[dict[str, Any]]:
        if student_id not in self.students:
            raise KeyError("Student does not exist.")

        result = []

        for enrollment in self.enrollments.values():
            if enrollment["student_id"] != student_id:
                continue

            course = self.courses[enrollment["course_id"]]
            instructor = self.instructors[course["instructor_id"]]

            result.append(
                {
                    "course_id": course["course_id"],
                    "course_name": course["name"],
                    "instructor": instructor["name"],
                    "grade": enrollment["grade"],
                }
            )

        return sorted(result, key=lambda item: item["course_id"])


def demonstrate_anomalies() -> None:
    print("=== NORMALIZATION CASE STUDY ===")

    unnormalized = Relation(
        name="EnrollmentRecord",
        columns=[
            "student_id",
            "student_name",
            "course_id",
            "course_name",
            "instructor_id",
            "instructor_name",
            "grade",
        ],
        primary_key=frozenset({"student_id", "course_id"}),
        rows=[
            {
                "student_id": 1,
                "student_name": "Asha",
                "course_id": 101,
                "course_name": "Database Systems",
                "instructor_id": 7,
                "instructor_name": "Dr Rao",
                "grade": "A",
            },
            {
                "student_id": 1,
                "student_name": "Asha",
                "course_id": 102,
                "course_name": "Networks",
                "instructor_id": 8,
                "instructor_name": "Dr Singh",
                "grade": "B",
            },
        ],
        dependencies=[
            FunctionalDependency(
                frozenset({"student_id"}),
                frozenset({"student_name"}),
            ),
            FunctionalDependency(
                frozenset({"course_id"}),
                frozenset({"course_name", "instructor_id"}),
            ),
            FunctionalDependency(
                frozenset({"instructor_id"}),
                frozenset({"instructor_name"}),
            ),
        ],
    )

    result = classify(unnormalized)
    print(f"Detected normal form: {result.form.value}")
    for problem in result.problems:
        print(f"  - {problem}")

    print("\n=== 1NF FAILURE ===")

    non_atomic = Relation(
        name="StudentPhones",
        columns=["student_id", "student_name", "phone_numbers"],
        primary_key=frozenset({"student_id"}),
        rows=[
            {
                "student_id": 1,
                "student_name": "Asha",
                "phone_numbers": ["9000000001", "9000000002"],
            }
        ],
    )

    atomic_ok, atomic_problems = check_1nf(non_atomic)
    print(f"1NF valid: {atomic_ok}")
    for problem in atomic_problems:
        print(f"  - {problem}")

    print("\n=== NORMALIZED 3NF DESIGN ===")

    database = NormalizedDatabase()

    database.add_student(1, "Asha")
    database.add_student(2, "Ravi")

    database.add_instructor(7, "Dr Rao")
    database.add_instructor(8, "Dr Singh")

    database.add_course(101, "Database Systems", 7)
    database.add_course(102, "Networks", 8)

    database.enroll(1001, 1, 101, "A")
    database.enroll(1002, 1, 102, "B")
    database.enroll(1003, 2, 101, "A")

    print(json.dumps(database.transcript(1), indent=2))

    print("\n=== UPDATE ANOMALY PREVENTION ===")
    database.instructors[7]["name"] = "Dr A. Rao"
    print(database.transcript(1)[0])

    print("\n=== EDGE-CASE VALIDATION ===")

    try:
        database.enroll(1004, 1, 101, "A")
    except ValueError as exc:
        print(f"Duplicate enrollment rejected: {exc}")

    try:
        database.add_course(103, "Distributed Systems", 999)
    except KeyError as exc:
        print(f"Foreign-key-like rule rejected: {exc}")

    try:
        database.enroll(1005, 1, 102, "Z")
    except ValueError as exc:
        print(f"Invalid grade rejected: {exc}")


def run_assertions() -> None:
    relation = Relation(
        name="Course",
        columns=["course_id", "course_name", "instructor_id"],
        primary_key=frozenset({"course_id"}),
        rows=[
            {
                "course_id": 101,
                "course_name": "Database Systems",
                "instructor_id": 7,
            }
        ],
        dependencies=[
            FunctionalDependency(
                frozenset({"course_id"}),
                frozenset({"course_name", "instructor_id"}),
            )
        ],
    )

    result = classify(relation)
    assert result.form == NormalForm.THIRD
    assert result.valid

    atomic_relation = Relation(
        name="Atomic",
        columns=["id", "value"],
        primary_key=frozenset({"id"}),
        rows=[{"id": 1, "value": "A"}],
    )

    assert check_1nf(atomic_relation)[0]


if __name__ == "__main__":
    run_assertions()
    demonstrate_anomalies()
