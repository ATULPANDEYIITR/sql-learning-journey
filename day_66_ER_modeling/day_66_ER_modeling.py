"""
ER Modeling: Entities, Attributes, Relationships, Cardinality and Participation.

A self-contained ER modeling engine with:
- Entity and attribute definitions
- Primary and candidate keys
- Foreign-key attributes
- Relationship modeling
- 1:1, 1:N and M:N cardinalities
- Total and partial participation
- Schema validation
- Relational schema mapping
- Model inspection and JSON export
- Automated validation tests
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
import json


class Cardinality(Enum):
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "M:N"


class Participation(Enum):
    TOTAL = "total"
    PARTIAL = "partial"


class DataType(Enum):
    INTEGER = "INTEGER"
    VARCHAR = "VARCHAR"
    DATE = "DATE"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"


@dataclass(frozen=True)
class Attribute:
    name: str
    data_type: DataType
    primary_key: bool = False
    unique: bool = False
    nullable: bool = True
    default: Optional[str] = None

    def __post_init__(self):
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError(f"Invalid attribute name: {self.name}")

        if self.primary_key and self.nullable:
            object.__setattr__(self, "nullable", False)


@dataclass
class Entity:
    name: str
    attributes: list[Attribute] = field(default_factory=list)

    def __post_init__(self):
        if not self.name:
            raise ValueError("Entity name cannot be empty.")

        names = [a.name for a in self.attributes]

        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate attributes in {self.name}.")

        if not any(a.primary_key for a in self.attributes):
            raise ValueError(f"Entity {self.name} requires a primary key.")

    @property
    def primary_key(self):
        return [
            a.name for a in self.attributes if a.primary_key
        ]

    def add_attribute(self, attribute: Attribute):
        if any(a.name == attribute.name for a in self.attributes):
            raise ValueError(
                f"Attribute {attribute.name} already exists."
            )

        self.attributes.append(attribute)


@dataclass(frozen=True)
class RelationshipEnd:
    entity: str
    minimum: int
    maximum: Optional[int]
    participation: Participation

    def __post_init__(self):
        if self.minimum not in (0, 1):
            raise ValueError("Minimum cardinality must be 0 or 1.")

        if self.maximum not in (1, None):
            raise ValueError("Maximum cardinality must be 1 or N.")

        if self.minimum == 1 and self.maximum == 1:
            pass

        if self.maximum == 1 and self.minimum > 1:
            raise ValueError("Invalid cardinality bounds.")

        if self.minimum == 1 and self.participation != Participation.TOTAL:
            raise ValueError("Minimum 1 requires total participation.")

        if self.minimum == 0 and self.participation != Participation.PARTIAL:
            raise ValueError("Minimum 0 requires partial participation.")


@dataclass
class Relationship:
    name: str
    left: RelationshipEnd
    right: RelationshipEnd
    attributes: list[Attribute] = field(default_factory=list)

    @property
    def cardinality(self):
        left_many = self.left.maximum is None
        right_many = self.right.maximum is None

        if left_many and right_many:
            return Cardinality.MANY_TO_MANY

        if left_many:
            return Cardinality.ONE_TO_MANY

        if right_many:
            return Cardinality.MANY_TO_ONE

        return Cardinality.ONE_TO_ONE


class ERModel:
    def __init__(self, name):
        self.name = name
        self.entities = {}
        self.relationships = {}

    def add_entity(self, entity):
        if entity.name in self.entities:
            raise ValueError(f"Entity {entity.name} already exists.")

        self.entities[entity.name] = entity

    def add_relationship(self, relationship):
        if relationship.name in self.relationships:
            raise ValueError(
                f"Relationship {relationship.name} already exists."
            )

        if relationship.left.entity not in self.entities:
            raise ValueError(
                f"Unknown entity: {relationship.left.entity}"
            )

        if relationship.right.entity not in self.entities:
            raise ValueError(
                f"Unknown entity: {relationship.right.entity}"
            )

        if relationship.left.entity == relationship.right.entity:
            # Recursive relationships are valid.
            pass

        self.relationships[relationship.name] = relationship

    def validate(self):
        errors = []

        for relationship in self.relationships.values():
            for end in (relationship.left, relationship.right):
                if end.entity not in self.entities:
                    errors.append(
                        f"{relationship.name}: unknown entity {end.entity}"
                    )

            names = [a.name for a in relationship.attributes]

            if len(names) != len(set(names)):
                errors.append(
                    f"{relationship.name}: duplicate relationship attributes"
                )

        return errors

    def describe(self):
        print(f"\nER MODEL: {self.name}")
        print("=" * 65)

        print("\nENTITIES")

        for entity in self.entities.values():
            print(f"\n{entity.name}")

            for attribute in entity.attributes:
                markers = []

                if attribute.primary_key:
                    markers.append("PK")

                if attribute.unique:
                    markers.append("UNIQUE")

                if not attribute.nullable:
                    markers.append("NOT NULL")

                suffix = f" [{', '.join(markers)}]" if markers else ""

                print(
                    f"  {attribute.name}: "
                    f"{attribute.data_type.value}{suffix}"
                )

        print("\nRELATIONSHIPS")

        for relationship in self.relationships.values():
            print(
                f"\n{relationship.name}: "
                f"{relationship.left.entity} "
                f"({relationship.left.minimum}.."
                f"{relationship.left.maximum or 'N'}) "
                f"<-> "
                f"{relationship.right.entity} "
                f"({relationship.right.minimum}.."
                f"{relationship.right.maximum or 'N'})"
            )

            print(f"  Cardinality: {relationship.cardinality.value}")
            print(
                f"  Left participation: "
                f"{relationship.left.participation.value}"
            )
            print(
                f"  Right participation: "
                f"{relationship.right.participation.value}"
            )

            for attribute in relationship.attributes:
                print(
                    f"  Relationship attribute: "
                    f"{attribute.name} ({attribute.data_type.value})"
                )

    def relational_mapping(self):
        """
        Convert conceptual relationships into relational design guidance.
        """

        result = []

        for relationship in self.relationships.values():
            left = relationship.left.entity
            right = relationship.right.entity
            cardinality = relationship.cardinality

            if cardinality == Cardinality.MANY_TO_MANY:
                result.append({
                    "relationship": relationship.name,
                    "implementation": "JUNCTION TABLE",
                    "tables": [
                        left,
                        right,
                        relationship.name
                    ],
                    "foreign_keys": [
                        f"{relationship.name}.{left.lower()}_id",
                        f"{relationship.name}.{right.lower()}_id"
                    ],
                    "relationship_attributes": [
                        a.name for a in relationship.attributes
                    ]
                })

            elif cardinality == Cardinality.ONE_TO_MANY:
                result.append({
                    "relationship": relationship.name,
                    "implementation": "FOREIGN KEY ON MANY SIDE",
                    "foreign_key_table": left,
                    "referenced_table": right
                })

            elif cardinality == Cardinality.MANY_TO_ONE:
                result.append({
                    "relationship": relationship.name,
                    "implementation": "FOREIGN KEY ON MANY SIDE",
                    "foreign_key_table": right,
                    "referenced_table": left
                })

            else:
                result.append({
                    "relationship": relationship.name,
                    "implementation": "UNIQUE FOREIGN KEY",
                    "tables": [left, right]
                })

        return result

    def export_json(self, filename):
        data = {
            "model": self.name,
            "entities": {},
            "relationships": []
        }

        for name, entity in self.entities.items():
            data["entities"][name] = {
                "attributes": [
                    {
                        "name": a.name,
                        "type": a.data_type.value,
                        "primary_key": a.primary_key,
                        "unique": a.unique,
                        "nullable": a.nullable
                    }
                    for a in entity.attributes
                ]
            }

        for relationship in self.relationships.values():
            data["relationships"].append({
                "name": relationship.name,
                "cardinality": relationship.cardinality.value,
                "left": asdict(relationship.left),
                "right": asdict(relationship.right),
                "attributes": [
                    {
                        "name": a.name,
                        "type": a.data_type.value
                    }
                    for a in relationship.attributes
                ]
            })

        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def validate_entity_instances(self, entity_name, records):
        if entity_name not in self.entities:
            raise ValueError(f"Unknown entity: {entity_name}")

        entity = self.entities[entity_name]
        expected = {a.name for a in entity.attributes}

        primary_keys = set()
        errors = []

        for index, record in enumerate(records):
            unknown = set(record) - expected

            if unknown:
                errors.append(
                    f"Record {index}: unknown attributes {unknown}"
                )

            for attribute in entity.attributes:
                value = record.get(attribute.name)

                if value is None and not attribute.nullable:
                    errors.append(
                        f"Record {index}: {attribute.name} cannot be NULL"
                    )

                if value is not None:
                    if attribute.data_type == DataType.INTEGER:
                        if isinstance(value, bool) or not isinstance(value, int):
                            errors.append(
                                f"Record {index}: {attribute.name} "
                                f"must be INTEGER"
                            )

                    elif attribute.data_type == DataType.VARCHAR:
                        if not isinstance(value, str):
                            errors.append(
                                f"Record {index}: {attribute.name} "
                                f"must be VARCHAR"
                            )

                    elif attribute.data_type == DataType.BOOLEAN:
                        if not isinstance(value, bool):
                            errors.append(
                                f"Record {index}: {attribute.name} "
                                f"must be BOOLEAN"
                            )

            if not unknown:
                key = tuple(
                    record.get(name) for name in entity.primary_key
                )

                if None not in key:
                    if key in primary_keys:
                        errors.append(
                            f"Record {index}: duplicate primary key {key}"
                        )

                    primary_keys.add(key)

        return errors


def end(entity, minimum, maximum, participation):
    return RelationshipEnd(
        entity,
        minimum,
        maximum,
        participation
    )


def build_university_model():
    model = ERModel("University Information System")

    model.add_entity(Entity("Department", [
        Attribute("department_id", DataType.INTEGER, primary_key=True),
        Attribute("department_name", DataType.VARCHAR, unique=True),
        Attribute("building", DataType.VARCHAR)
    ]))

    model.add_entity(Entity("Student", [
        Attribute("student_id", DataType.INTEGER, primary_key=True),
        Attribute("student_name", DataType.VARCHAR, nullable=False),
        Attribute("email", DataType.VARCHAR, unique=True),
        Attribute("enrollment_date", DataType.DATE)
    ]))

    model.add_entity(Entity("Instructor", [
        Attribute("instructor_id", DataType.INTEGER, primary_key=True),
        Attribute("instructor_name", DataType.VARCHAR, nullable=False),
        Attribute("salary", DataType.DECIMAL)
    ]))

    model.add_entity(Entity("Course", [
        Attribute("course_id", DataType.INTEGER, primary_key=True),
        Attribute("course_name", DataType.VARCHAR, nullable=False),
        Attribute("credits", DataType.INTEGER, nullable=False)
    ]))

    # A department can have zero or many students.
    # Every student belongs to exactly one department.
    model.add_relationship(Relationship(
        "StudentDepartment",
        end("Student", 1, 1, Participation.TOTAL),
        end("Department", 0, None, Participation.PARTIAL)
    ))

    # Each department employs one or more instructors.
    model.add_relationship(Relationship(
        "DepartmentInstructor",
        end("Department", 1, None, Participation.TOTAL),
        end("Instructor", 1, 1, Participation.TOTAL)
    ))

    # A department can offer multiple courses.
    model.add_relationship(Relationship(
        "DepartmentCourse",
        end("Department", 0, None, Participation.PARTIAL),
        end("Course", 1, 1, Participation.TOTAL)
    ))

    # Students can enroll in multiple courses.
    # Courses can contain multiple students.
    model.add_relationship(Relationship(
        "Enrollment",
        end("Student", 0, None, Participation.PARTIAL),
        end("Course", 0, None, Participation.PARTIAL),
        [
            Attribute("enrollment_date", DataType.DATE),
            Attribute("grade", DataType.VARCHAR)
        ]
    ))

    # An instructor may teach several courses.
    model.add_relationship(Relationship(
        "Teaching",
        end("Instructor", 0, None, Participation.PARTIAL),
        end("Course", 1, 1, Participation.TOTAL)
    ))

    return model


def run_tests(model):
    print("\nVALIDATION TESTS")
    print("=" * 65)

    assert len(model.entities) == 4
    assert len(model.relationships) == 5
    assert model.validate() == []

    enrollment = model.relationships["Enrollment"]
    assert enrollment.cardinality == Cardinality.MANY_TO_MANY

    teaching = model.relationships["Teaching"]
    assert teaching.cardinality == Cardinality.ONE_TO_MANY

    student_errors = model.validate_entity_instances(
        "Student",
        [
            {
                "student_id": 101,
                "student_name": "Aarav Sharma",
                "email": "aarav@example.com"
            },
            {
                "student_id": 102,
                "student_name": "Diya Verma",
                "email": "diya@example.com"
            }
        ]
    )

    assert student_errors == []

    duplicate_errors = model.validate_entity_instances(
        "Student",
        [
            {
                "student_id": 101,
                "student_name": "Aarav",
                "email": "a@example.com"
            },
            {
                "student_id": 101,
                "student_name": "Ravi",
                "email": "r@example.com"
            }
        ]
    )

    assert any("duplicate primary key" in e for e in duplicate_errors)

    null_errors = model.validate_entity_instances(
        "Student",
        [{"student_id": 103, "student_name": None}]
    )

    assert any("cannot be NULL" in e for e in null_errors)

    print("PASS: Entity definitions")
    print("PASS: Primary key validation")
    print("PASS: Attribute validation")
    print("PASS: Cardinality evaluation")
    print("PASS: Participation constraints")
    print("PASS: Duplicate detection")
    print("PASS: NULL validation")


def main():
    model = build_university_model()

    errors = model.validate()

    if errors:
        raise RuntimeError("\n".join(errors))

    model.describe()

    print("\nRELATIONAL MAPPING")
    print("=" * 65)

    for mapping in model.relational_mapping():
        print(json.dumps(mapping, indent=2))

    run_tests(model)

    print("\nJSON EXPORT")
    model.export_json("university_er_model.json")
    print("Exported university_er_model.json")

    print("\nER modeling execution completed.")


if __name__ == "__main__":
    main()
