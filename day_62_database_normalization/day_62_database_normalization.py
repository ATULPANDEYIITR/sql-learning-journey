from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Sequence, Set, Tuple


class NormalForm(Enum):
    UNNORMALIZED = "UNF"
    FIRST = "1NF"
    SECOND = "2NF"
    THIRD = "3NF"


class NormalizationError(ValueError):
    pass


@dataclass(frozen=True)
class FunctionalDependency:
    determinant: frozenset[str]
    dependent: frozenset[str]

    def __str__(self) -> str:
        return f"{', '.join(sorted(self.determinant))} -> {', '.join(sorted(self.dependent))}"


@dataclass
class Relation:
    name: str
    attributes: Set[str]
    candidate_keys: List[Set[str]]
    dependencies: List[FunctionalDependency] = field(default_factory=list)

    def validate(self) -> None:
        if not self.attributes:
            raise NormalizationError("A relation must contain attributes.")

        if not self.candidate_keys:
            raise NormalizationError("At least one candidate key is required.")

        for key in self.candidate_keys:
            if not key:
                raise NormalizationError("Candidate keys cannot be empty.")
            if not key <= self.attributes:
                raise NormalizationError(f"Candidate key {key} contains unknown attributes.")

        for fd in self.dependencies:
            if not fd.determinant <= self.attributes:
                raise NormalizationError(f"Unknown determinant attributes in {fd}.")
            if not fd.dependent <= self.attributes:
                raise NormalizationError(f"Unknown dependent attributes in {fd}.")

    def closure(self, attributes: Iterable[str]) -> Set[str]:
        closure = set(attributes)

        changed = True
        while changed:
            changed = False
            for fd in self.dependencies:
                if set(fd.determinant) <= closure:
                    before = len(closure)
                    closure.update(fd.dependent)
                    changed |= len(closure) > before

        return closure

    def is_superkey(self, attributes: Iterable[str]) -> bool:
        return self.closure(attributes) >= self.attributes

    def is_candidate_key(self, attributes: Iterable[str]) -> bool:
        candidate = set(attributes)
        if not self.is_superkey(candidate):
            return False

        for attribute in candidate:
            reduced = candidate - {attribute}
            if reduced and self.is_superkey(reduced):
                return False

        return True

    def prime_attributes(self) -> Set[str]:
        result: Set[str] = set()
        for key in self.candidate_keys:
            result.update(key)
        return result


def minimal_cover(dependencies: Sequence[FunctionalDependency]) -> List[FunctionalDependency]:
    """
    Produces a practical minimal cover:
    1. Split right-hand sides.
    2. Remove extraneous determinant attributes.
    3. Remove redundant dependencies.
    """
    cover: List[FunctionalDependency] = []

    for fd in dependencies:
        for attribute in fd.dependent:
            cover.append(
                FunctionalDependency(
                    frozenset(fd.determinant),
                    frozenset({attribute}),
                )
            )

    changed = True
    while changed:
        changed = False

        for index, fd in enumerate(list(cover)):
            determinant = set(fd.determinant)

            for attribute in list(determinant):
                reduced = determinant - {attribute}
                test = list(cover)
                test[index] = FunctionalDependency(
                    frozenset(reduced),
                    fd.dependent,
                )

                relation = Relation(
                    name="temporary",
                    attributes=set().union(
                        *(set(x.determinant) | set(x.dependent) for x in test)
                    ),
                    candidate_keys=[set()],
                    dependencies=test,
                )

                closure = relation.closure(reduced)
                if set(fd.dependent) <= closure:
                    cover[index] = FunctionalDependency(
                        frozenset(reduced),
                        fd.dependent,
                    )
                    changed = True
                    break

            if changed:
                break

    index = 0
    while index < len(cover):
        fd = cover[index]
        remaining = cover[:index] + cover[index + 1:]

        relation = Relation(
            name="temporary",
            attributes=set().union(
                *(set(x.determinant) | set(x.dependent) for x in remaining)
            ),
            candidate_keys=[set()],
            dependencies=remaining,
        )

        if set(fd.dependent) <= relation.closure(fd.determinant):
            cover.pop(index)
        else:
            index += 1

    return cover


def detect_partial_dependencies(relation: Relation) -> List[FunctionalDependency]:
    """
    A partial dependency exists when a non-prime attribute depends on
    a proper subset of a composite candidate key.
    """
    prime = relation.prime_attributes()
    result: List[FunctionalDependency] = []

    for fd in relation.dependencies:
        if not (set(fd.dependent) - prime):
            continue

        for key in relation.candidate_keys:
            determinant = set(fd.determinant)
            if determinant < key and determinant:
                result.append(fd)
                break

    return result


def detect_transitive_dependencies(relation: Relation) -> List[FunctionalDependency]:
    """
    Finds X -> Y where X is not a superkey and Y is non-prime.
    This is a practical 3NF diagnostic.
    """
    prime = relation.prime_attributes()
    result: List[FunctionalDependency] = []

    for fd in relation.dependencies:
        determinant = set(fd.determinant)
        dependent = set(fd.dependent)

        if not relation.is_superkey(determinant) and not (dependent & prime):
            result.append(fd)

    return result


def highest_normal_form(relation: Relation) -> NormalForm:
    relation.validate()

    if not relation.candidate_keys:
        return NormalForm.UNNORMALIZED

    # 1NF assumes atomic attributes in this learning model.
    partial = detect_partial_dependencies(relation)
    if partial:
        return NormalForm.FIRST

    transitive = detect_transitive_dependencies(relation)
    if transitive:
        return NormalForm.SECOND

    return NormalForm.THIRD


@dataclass
class Student:
    student_id: str
    student_name: str


@dataclass
class Course:
    course_id: str
    course_name: str
    instructor_id: str
    instructor_name: str


@dataclass
class Enrollment:
    student_id: str
    course_id: str
    student_name: str
    course_name: str
    instructor_id: str
    instructor_name: str
    grade: str | None = None


class EnrollmentSystem:
    """
    Demonstrates why a single enrollment table creates update,
    insertion, and deletion anomalies.
    """

    def __init__(self) -> None:
        self.students: Dict[str, Student] = {}
        self.courses: Dict[str, Course] = {}
        self.enrollments: Dict[Tuple[str, str], Enrollment] = {}

    def add_student(self, student: Student) -> None:
        if not student.student_id.strip():
            raise ValueError("Student ID cannot be empty.")
        if not student.student_name.strip():
            raise ValueError("Student name cannot be empty.")
        self.students[student.student_id] = student

    def add_course(self, course: Course) -> None:
        if not course.course_id.strip():
            raise ValueError("Course ID cannot be empty.")
        if not course.course_name.strip():
            raise ValueError("Course name cannot be empty.")
        self.courses[course.course_id] = course

    def enroll(self, student_id: str, course_id: str, grade: str | None = None) -> None:
        if student_id not in self.students:
            raise KeyError(f"Unknown student: {student_id}")
        if course_id not in self.courses:
            raise KeyError(f"Unknown course: {course_id}")

        student = self.students[student_id]
        course = self.courses[course_id]

        self.enrollments[(student_id, course_id)] = Enrollment(
            student_id=student_id,
            course_id=course_id,
            student_name=student.student_name,
            course_name=course.course_name,
            instructor_id=course.instructor_id,
            instructor_name=course.instructor_name,
            grade=grade,
        )

    def change_instructor(self, instructor_id: str, new_name: str) -> int:
        if not instructor_id.strip() or not new_name.strip():
            raise ValueError("Instructor ID and name are required.")

        affected = 0
        for course in self.courses.values():
            if course.instructor_id == instructor_id:
                course.instructor_name = new_name
                affected += 1

        return affected

    def validate_consistency(self) -> List[str]:
        problems: List[str] = []

        for enrollment in self.enrollments.values():
            student = self.students.get(enrollment.student_id)
            course = self.courses.get(enrollment.course_id)

            if student is None or course is None:
                problems.append(
                    f"Broken enrollment reference: "
                    f"{enrollment.student_id}/{enrollment.course_id}"
                )
                continue

            if enrollment.student_name != student.student_name:
                problems.append(
                    f"Student name anomaly for {enrollment.student_id}: "
                    f"stored={enrollment.student_name!r}, "
                    f"canonical={student.student_name!r}"
                )

            if enrollment.course_name != course.course_name:
                problems.append(
                    f"Course name anomaly for {enrollment.course_id}"
                )

            if enrollment.instructor_id != course.instructor_id:
                problems.append(
                    f"Instructor relationship anomaly for {enrollment.course_id}"
                )

        return problems


def build_normalization_analysis() -> Relation:
    attributes = {
        "student_id",
        "student_name",
        "course_id",
        "course_name",
        "instructor_id",
        "instructor_name",
        "grade",
    }

    dependencies = [
        FunctionalDependency(frozenset({"student_id"}), frozenset({"student_name"})),
        FunctionalDependency(
            frozenset({"course_id"}),
            frozenset({"course_name", "instructor_id"}),
        ),
        FunctionalDependency(
            frozenset({"instructor_id"}),
            frozenset({"instructor_name"}),
        ),
        FunctionalDependency(
            frozenset({"student_id", "course_id"}),
            frozenset({"grade"}),
        ),
    ]

    return Relation(
        name="enrollment_record",
        attributes=attributes,
        candidate_keys=[{"student_id", "course_id"}],
        dependencies=dependencies,
    )


def print_analysis(relation: Relation) -> None:
    relation.validate()

    print("=== Functional Dependency Analysis ===")
    for fd in relation.dependencies:
        print(f"  {fd}")

    print("\nCandidate keys:")
    for key in relation.candidate_keys:
        print(f"  {{{', '.join(sorted(key))}}}")

    print("\nAttribute closures:")
    for key in relation.candidate_keys:
        closure = relation.closure(key)
        print(f"  closure({{{', '.join(sorted(key))}}}) = "
              f"{{{', '.join(sorted(closure))}}}")

    cover = minimal_cover(relation.dependencies)

    print("\nMinimal cover:")
    for fd in cover:
        print(f"  {fd}")

    print("\nNormal form diagnostics:")
    partial = detect_partial_dependencies(relation)
    transitive = detect_transitive_dependencies(relation)

    print(f"  Highest normal form: {highest_normal_form(relation).value}")
    print(f"  Partial dependencies: {len(partial)}")
    for fd in partial:
        print(f"    {fd}")

    print(f"  Transitive dependencies: {len(transitive)}")
    for fd in transitive:
        print(f"    {fd}")


def demonstrate_anomalies() -> None:
    system = EnrollmentSystem()

    system.add_student(Student("S001", "Asha Singh"))
    system.add_student(Student("S002", "Rahul Kumar"))

    system.add_course(
        Course("C101", "Database Systems", "I01", "Dr. Mehta")
    )
    system.add_course(
        Course("C102", "Operating Systems", "I02", "Dr. Rao")
    )

    system.enroll("S001", "C101", "A")
    system.enroll("S002", "C101", "B")

    print("\n=== Normalized Storage ===")
    for student in system.students.values():
        print(student)

    for course in system.courses.values():
        print(course)

    for enrollment in system.enrollments.values():
        print(enrollment)

    # Instructor data is stored once in the course relation, so one
    # update changes the authoritative value instead of every enrollment row.
    changed = system.change_instructor("I01", "Dr. Mehta-Singh")
    print(f"\nCourses updated for instructor I01: {changed}")

    problems = system.validate_consistency()
    print(f"Consistency problems: {len(problems)}")

    print("\nAnomaly interpretation:")
    print("  Update anomaly is avoided because instructor data has one owner.")
    print("  Insertion anomaly is avoided because courses exist independently of enrollments.")
    print("  Deletion anomaly is avoided because removing an enrollment does not remove course data.")


def demonstrate_edge_cases() -> None:
    print("\n=== Validation and Edge Cases ===")

    relation = build_normalization_analysis()

    assert relation.is_superkey({"student_id", "course_id"})
    assert not relation.is_superkey({"student_id"})
    assert relation.closure({"student_id", "course_id"}) == relation.attributes

    try:
        EnrollmentSystem().enroll("missing", "missing")
    except KeyError as exc:
        print(f"Expected failure: {exc}")

    try:
        EnrollmentSystem().add_student(Student("", "Invalid"))
    except ValueError as exc:
        print(f"Expected validation failure: {exc}")

    print("Closure and validation assertions passed.")


def main() -> None:
    relation = build_normalization_analysis()

    print_analysis(relation)
    demonstrate_anomalies()
    demonstrate_edge_cases()

    print("\n=== Practical Normalization Target ===")
    print("Student(student_id, student_name)")
    print("Instructor(instructor_id, instructor_name)")
    print("Course(course_id, course_name, instructor_id)")
    print("Enrollment(student_id, course_id, grade)")
    print("\nThe decomposition separates facts according to their functional dependencies.")


if __name__ == "__main__":
    main()
