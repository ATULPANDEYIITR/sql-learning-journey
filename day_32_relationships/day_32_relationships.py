"""
Relationships: One-to-One, One-to-Many, and Many-to-Many

A self-contained relational-data modeling laboratory.

The program progresses from simple relationship concepts to a small
repository-style project management system. It demonstrates:

- One-to-one relationships
- One-to-many relationships
- Many-to-many relationships
- Primary and foreign keys
- Referential integrity
- Cardinality validation
- Relationship traversal
- Association tables
- Duplicate relationship prevention
- Deletion behavior
- Transaction-like validation
- Querying related records
- Schema inspection
- Constraint failures
- Performance considerations through indexed lookup structures

The implementation uses only Python's standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Generic, Iterable, List, Optional, Set, Tuple, TypeVar


T = TypeVar("T")


class RelationshipError(Exception):
    """Base exception for invalid relationship operations."""


class NotFoundError(RelationshipError):
    """Raised when a requested entity does not exist."""


class IntegrityError(RelationshipError):
    """Raised when an operation violates a relationship constraint."""


@dataclass
class User:
    user_id: int
    username: str
    email: str


@dataclass
class UserProfile:
    profile_id: int
    user_id: int
    display_name: str
    timezone: str


@dataclass
class Project:
    project_id: int
    name: str
    owner_id: int


@dataclass
class Task:
    task_id: int
    project_id: int
    title: str
    status: str = "open"


@dataclass
class Skill:
    skill_id: int
    name: str


@dataclass
class UserSkill:
    user_id: int
    skill_id: int
    proficiency: str


class Repository(Generic[T]):
    """Small in-memory repository using an integer primary key."""

    def __init__(self) -> None:
        self.records: Dict[int, T] = {}

    def add(self, key: int, value: T) -> None:
        if key in self.records:
            raise IntegrityError(f"Primary key {key} already exists.")
        self.records[key] = value

    def get(self, key: int) -> T:
        try:
            return self.records[key]
        except KeyError as exc:
            raise NotFoundError(f"Record {key} does not exist.") from exc

    def delete(self, key: int) -> T:
        value = self.get(key)
        del self.records[key]
        return value

    def all(self) -> List[T]:
        return list(self.records.values())


class RelationshipDatabase:
    """
    Models three relationship types in one coherent domain.

    One-to-one:
        User -> UserProfile

    One-to-many:
        Project -> Task

    Many-to-many:
        User <-> Skill through UserSkill
    """

    VALID_TASK_STATUSES = {"open", "in_progress", "done"}
    VALID_PROFICIENCY = {"beginner", "intermediate", "advanced", "expert"}

    def __init__(self) -> None:
        self.users = Repository[User]()
        self.profiles = Repository[UserProfile]()
        self.projects = Repository[Project]()
        self.tasks = Repository[Task]()
        self.skills = Repository[Skill]()

        # A relationship table normally has a composite primary key.
        # Here (user_id, skill_id) prevents the same relationship
        # from being inserted twice.
        self.user_skills: Dict[Tuple[int, int], UserSkill] = {}

        # Reverse indexes make relationship traversal efficient.
        self.profile_by_user: Dict[int, int] = {}
        self.projects_by_owner: Dict[int, Set[int]] = {}
        self.tasks_by_project: Dict[int, Set[int]] = {}
        self.skills_by_user: Dict[int, Set[int]] = {}
        self.users_by_skill: Dict[int, Set[int]] = {}

    # ------------------------------------------------------------------
    # User and one-to-one profile relationship
    # ------------------------------------------------------------------

    def create_user(self, user_id: int, username: str, email: str) -> User:
        if not username.strip():
            raise ValueError("Username cannot be empty.")
        if "@" not in email:
            raise ValueError("Email must contain '@'.")

        user = User(user_id, username.strip(), email.strip())
        self.users.add(user_id, user)
        return user

    def create_profile(
        self,
        profile_id: int,
        user_id: int,
        display_name: str,
        timezone: str,
    ) -> UserProfile:
        self.users.get(user_id)

        # A unique foreign key on user_id is what turns an ordinary
        # foreign-key relationship into a one-to-one relationship.
        if user_id in self.profile_by_user:
            raise IntegrityError(
                f"User {user_id} already has profile "
                f"{self.profile_by_user[user_id]}."
            )

        profile = UserProfile(
            profile_id=profile_id,
            user_id=user_id,
            display_name=display_name.strip(),
            timezone=timezone.strip(),
        )

        self.profiles.add(profile_id, profile)
        self.profile_by_user[user_id] = profile_id
        return profile

    def get_profile_for_user(self, user_id: int) -> Optional[UserProfile]:
        self.users.get(user_id)

        profile_id = self.profile_by_user.get(user_id)
        if profile_id is None:
            return None

        return self.profiles.get(profile_id)

    # ------------------------------------------------------------------
    # Project and one-to-many task relationship
    # ------------------------------------------------------------------

    def create_project(self, project_id: int, name: str, owner_id: int) -> Project:
        self.users.get(owner_id)

        if not name.strip():
            raise ValueError("Project name cannot be empty.")

        project = Project(project_id, name.strip(), owner_id)
        self.projects.add(project_id, project)

        self.projects_by_owner.setdefault(owner_id, set()).add(project_id)
        return project

    def create_task(
        self,
        task_id: int,
        project_id: int,
        title: str,
        status: str = "open",
    ) -> Task:
        self.projects.get(project_id)

        if not title.strip():
            raise ValueError("Task title cannot be empty.")

        if status not in self.VALID_TASK_STATUSES:
            raise ValueError(
                f"Invalid task status: {status}. "
                f"Allowed values: {sorted(self.VALID_TASK_STATUSES)}"
            )

        task = Task(
            task_id=task_id,
            project_id=project_id,
            title=title.strip(),
            status=status,
        )

        self.tasks.add(task_id, task)
        self.tasks_by_project.setdefault(project_id, set()).add(task_id)
        return task

    def get_tasks_for_project(self, project_id: int) -> List[Task]:
        self.projects.get(project_id)

        task_ids = self.tasks_by_project.get(project_id, set())
        return [self.tasks.get(task_id) for task_id in sorted(task_ids)]

    # ------------------------------------------------------------------
    # User and skill many-to-many relationship
    # ------------------------------------------------------------------

    def create_skill(self, skill_id: int, name: str) -> Skill:
        if not name.strip():
            raise ValueError("Skill name cannot be empty.")

        skill = Skill(skill_id, name.strip())
        self.skills.add(skill_id, skill)
        return skill

    def assign_skill(
        self,
        user_id: int,
        skill_id: int,
        proficiency: str,
    ) -> UserSkill:
        self.users.get(user_id)
        self.skills.get(skill_id)

        if proficiency not in self.VALID_PROFICIENCY:
            raise ValueError(
                f"Invalid proficiency: {proficiency}. "
                f"Allowed values: {sorted(self.VALID_PROFICIENCY)}"
            )

        relationship_key = (user_id, skill_id)

        # The pair acts as a composite primary key.
        if relationship_key in self.user_skills:
            raise IntegrityError(
                f"User {user_id} already has skill {skill_id}."
            )

        relation = UserSkill(
            user_id=user_id,
            skill_id=skill_id,
            proficiency=proficiency,
        )

        self.user_skills[relationship_key] = relation
        self.skills_by_user.setdefault(user_id, set()).add(skill_id)
        self.users_by_skill.setdefault(skill_id, set()).add(user_id)

        return relation

    def get_skills_for_user(self, user_id: int) -> List[Tuple[Skill, str]]:
        self.users.get(user_id)

        skill_ids = self.skills_by_user.get(user_id, set())
        result: List[Tuple[Skill, str]] = []

        for skill_id in sorted(skill_ids):
            skill = self.skills.get(skill_id)
            relation = self.user_skills[(user_id, skill_id)]
            result.append((skill, relation.proficiency))

        return result

    def get_users_for_skill(self, skill_id: int) -> List[Tuple[User, str]]:
        self.skills.get(skill_id)

        user_ids = self.users_by_skill.get(skill_id, set())
        result: List[Tuple[User, str]] = []

        for user_id in sorted(user_ids):
            user = self.users.get(user_id)
            relation = self.user_skills[(user_id, skill_id)]
            result.append((user, relation.proficiency))

        return result

    # ------------------------------------------------------------------
    # Referential-integrity-aware deletion
    # ------------------------------------------------------------------

    def delete_profile(self, profile_id: int) -> None:
        profile = self.profiles.delete(profile_id)

        if self.profile_by_user.get(profile.user_id) == profile_id:
            del self.profile_by_user[profile.user_id]

    def delete_task(self, task_id: int) -> None:
        task = self.tasks.delete(task_id)

        project_tasks = self.tasks_by_project.get(task.project_id)
        if project_tasks is not None:
            project_tasks.discard(task_id)
            if not project_tasks:
                del self.tasks_by_project[task.project_id]

    def delete_project(self, project_id: int) -> None:
        """
        Uses an explicit RESTRICT policy.

        A project cannot disappear while child tasks still reference it.
        This models a common foreign-key ON DELETE RESTRICT policy.
        """
        self.projects.get(project_id)

        child_tasks = self.tasks_by_project.get(project_id, set())
        if child_tasks:
            raise IntegrityError(
                f"Cannot delete project {project_id}; "
                f"{len(child_tasks)} task(s) still reference it."
            )

        project = self.projects.delete(project_id)

        owner_projects = self.projects_by_owner.get(project.owner_id)
        if owner_projects is not None:
            owner_projects.discard(project_id)
            if not owner_projects:
                del self.projects_by_owner[project.owner_id]

    def unassign_skill(self, user_id: int, skill_id: int) -> None:
        self.users.get(user_id)
        self.skills.get(skill_id)

        key = (user_id, skill_id)

        if key not in self.user_skills:
            raise NotFoundError(
                f"User {user_id} is not assigned skill {skill_id}."
            )

        del self.user_skills[key]

        user_skills = self.skills_by_user.get(user_id)
        if user_skills is not None:
            user_skills.discard(skill_id)
            if not user_skills:
                del self.skills_by_user[user_id]

        skill_users = self.users_by_skill.get(skill_id)
        if skill_users is not None:
            skill_users.discard(user_id)
            if not skill_users:
                del self.users_by_skill[skill_id]

    # ------------------------------------------------------------------
    # Relationship-oriented reporting
    # ------------------------------------------------------------------

    def describe_user(self, user_id: int) -> str:
        user = self.users.get(user_id)
        profile = self.get_profile_for_user(user_id)
        projects = [
            project
            for project_id in self.projects_by_owner.get(user_id, set())
            for project in [self.projects.get(project_id)]
        ]
        skills = self.get_skills_for_user(user_id)

        lines = [
            f"User: {user.username} ({user.email})",
            f"Profile: "
            f"{profile.display_name if profile else 'not created'}",
            f"Owned projects: {len(projects)}",
            f"Skills: {len(skills)}",
        ]

        if projects:
            lines.append(
                "  Projects: "
                + ", ".join(project.name for project in projects)
            )

        if skills:
            lines.append(
                "  Skills: "
                + ", ".join(
                    f"{skill.name} [{proficiency}]"
                    for skill, proficiency in skills
                )
            )

        return "\n".join(lines)

    def schema_report(self) -> str:
        return """
Relationship schema

users
  PK: user_id

user_profiles
  PK: profile_id
  FK: user_id -> users.user_id
  UNIQUE: user_id
  Cardinality: one user to zero-or-one profile

projects
  PK: project_id
  FK: owner_id -> users.user_id
  Cardinality: one user to many projects

tasks
  PK: task_id
  FK: project_id -> projects.project_id
  Cardinality: one project to many tasks

skills
  PK: skill_id

user_skills
  Composite PK: (user_id, skill_id)
  FK: user_id -> users.user_id
  FK: skill_id -> skills.skill_id
  Cardinality: many users to many skills
""".strip()


def demonstrate_beginner_relationships() -> None:
    print("\n=== Relationship Fundamentals ===")

    print(
        "One-to-one: one entity is associated with at most one entity "
        "on the other side."
    )
    print(
        "One-to-many: one parent entity can be referenced by many child "
        "entities."
    )
    print(
        "Many-to-many: many records on each side can be associated, "
        "normally through an association table."
    )


def demonstrate_database() -> RelationshipDatabase:
    db = RelationshipDatabase()

    print("\n=== Creating Users ===")
    db.create_user(1, "atul", "atul@example.com")
    db.create_user(2, "maya", "maya@example.com")
    db.create_user(3, "liam", "liam@example.com")

    print("\n=== One-to-One: User -> Profile ===")
    db.create_profile(
        101,
        user_id=1,
        display_name="Atul Pandey",
        timezone="Asia/Kolkata",
    )
    print(db.get_profile_for_user(1))

    print("\n=== One-to-Many: User -> Projects -> Tasks ===")
    db.create_project(201, "Market Analytics", owner_id=1)
    db.create_project(202, "Research Tracker", owner_id=1)
    db.create_project(203, "Security Dashboard", owner_id=2)

    db.create_task(301, 201, "Build portfolio model")
    db.create_task(302, 201, "Validate market data", "in_progress")
    db.create_task(303, 201, "Write risk report", "done")
    db.create_task(304, 202, "Import research records")

    print("Tasks in Market Analytics:")
    for task in db.get_tasks_for_project(201):
        print(f"  {task.task_id}: {task.title} [{task.status}]")

    print("\n=== Many-to-Many: Users <-> Skills ===")
    db.create_skill(401, "Python")
    db.create_skill(402, "SQL")
    db.create_skill(403, "Cybersecurity")
    db.create_skill(404, "Product Management")

    db.assign_skill(1, 401, "advanced")
    db.assign_skill(1, 402, "advanced")
    db.assign_skill(1, 403, "intermediate")
    db.assign_skill(2, 401, "intermediate")
    db.assign_skill(2, 404, "advanced")
    db.assign_skill(3, 402, "beginner")

    print("Skills for Atul:")
    for skill, proficiency in db.get_skills_for_user(1):
        print(f"  {skill.name}: {proficiency}")

    print("Users with Python:")
    for user, proficiency in db.get_users_for_skill(401):
        print(f"  {user.username}: {proficiency}")

    print("\n=== Relationship Traversal ===")
    print(db.describe_user(1))

    print("\n=== Schema ===")
    print(db.schema_report())

    return db


def demonstrate_integrity_rules(db: RelationshipDatabase) -> None:
    print("\n=== Integrity and Failure Conditions ===")

    try:
        db.create_profile(
            102,
            user_id=1,
            display_name="Second Profile",
            timezone="UTC",
        )
    except IntegrityError as exc:
        print(f"Expected one-to-one failure: {exc}")

    try:
        db.create_task(
            305,
            project_id=999,
            title="Invalid parent reference",
        )
    except NotFoundError as exc:
        print(f"Expected foreign-key failure: {exc}")

    try:
        db.assign_skill(1, 401, "expert")
    except IntegrityError as exc:
        print(f"Expected duplicate many-to-many failure: {exc}")

    try:
        db.delete_project(201)
    except IntegrityError as exc:
        print(f"Expected restricted-delete failure: {exc}")

    print("\nDeleting child tasks allows the parent to be removed:")
    db.delete_task(301)
    db.delete_task(302)
    db.delete_task(303)
    db.delete_project(201)
    print("Project 201 deleted after its dependent tasks were removed.")

    print("\nRemoving one many-to-many relationship:")
    db.unassign_skill(1, 403)
    print("Cybersecurity removed from Atul's skill associations.")


def demonstrate_query_patterns(db: RelationshipDatabase) -> None:
    print("\n=== Query Patterns ===")

    # Parent-to-child traversal represents a one-to-many query.
    for project in db.projects.all():
        tasks = db.get_tasks_for_project(project.project_id)
        print(
            f"Project '{project.name}' has {len(tasks)} "
            f"task(s)."
        )

    # Child-to-parent traversal uses the foreign key.
    task = db.tasks.get(304)
    project = db.projects.get(task.project_id)
    print(
        f"Task '{task.title}' belongs to project '{project.name}'."
    )

    # The association table supports both directions of a many-to-many
    # relationship without duplicating the full user or skill record.
    python_users = db.get_users_for_skill(401)
    print(
        "Python association count:",
        len(python_users),
    )


def demonstrate_edge_cases() -> None:
    print("\n=== Edge Cases ===")

    db = RelationshipDatabase()

    # Zero-or-one on the profile side is valid. A user does not need
    # to have a profile immediately.
    user = db.create_user(1, "new_user", "new@example.com")
    print(
        f"{user.username} initially has profile:",
        db.get_profile_for_user(1),
    )

    # A one-to-many parent may have zero children.
    project = db.create_project(1, "Empty Project", 1)
    print(
        f"{project.name} initially has tasks:",
        db.get_tasks_for_project(1),
    )

    # A many-to-many entity may have zero relationships.
    db.create_skill(1, "Rust")
    print(
        "Users associated with Rust:",
        db.get_users_for_skill(1),
    )

    # Empty and invalid values are rejected close to the operation
    # that would otherwise create invalid data.
    try:
        db.create_project(2, "   ", 1)
    except ValueError as exc:
        print(f"Validation failure: {exc}")


def main() -> None:
    print("RELATIONAL RELATIONSHIPS LAB")
    print("=" * 30)

    demonstrate_beginner_relationships()

    database = demonstrate_database()
    demonstrate_integrity_rules(database)
    demonstrate_query_patterns(database)
    demonstrate_edge_cases()

    print("\n=== Practical Design Rules ===")
    print(
        "One-to-one commonly uses a foreign key with a UNIQUE constraint "
        "on the dependent table."
    )
    print(
        "One-to-many normally places the foreign key on the many side."
    )
    print(
        "Many-to-many normally requires an association table containing "
        "foreign keys to both participating entities."
    )
    print(
        "Foreign keys protect references; uniqueness constraints control "
        "cardinality; association-table keys prevent duplicate pairs."
    )


if __name__ == "__main__":
    main()
