from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


NULL = None


@dataclass(frozen=True)
class Employee:
    employee_id: int
    name: str
    department_id: int | None


@dataclass(frozen=True)
class Department:
    department_id: int
    department_name: str
    manager_id: int | None


@dataclass(frozen=True)
class Project:
    project_id: int
    project_name: str
    department_id: int | None


def print_rows(title: str, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    print(f"\n--- {title} ---")

    if not rows:
        print("(no rows)")
        return

    columns = list(rows[0].keys())
    widths = {
        column: max(
            len(column),
            max(len(str(row.get(column, ""))) for row in rows),
        )
        for column in columns
    }

    print(" | ".join(column.ljust(widths[column]) for column in columns))
    print("-+-".join("-" * widths[column] for column in columns))

    for row in rows:
        print(" | ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))


def normalize_key(value: Any) -> Any:
    # None represents SQL NULL for this in-memory demonstration.
    # SQL equality does not match NULL with NULL, so NULL never becomes
    # a successful join key.
    return value


def right_join(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    left_key: str,
    right_key: str,
) -> list[dict[str, Any]]:
    """
    RIGHT JOIN semantics:

        left JOIN right ON left.key = right.key

    Every row from the right relation survives. If no matching left row
    exists, the left-side columns become None.
    """

    left_columns = list(left_rows[0].keys()) if left_rows else []
    right_columns = list(right_rows[0].keys()) if right_rows else []

    index: dict[Any, list[dict[str, Any]]] = {}

    for left in left_rows:
        key = normalize_key(left.get(left_key))
        if key is not None:
            index.setdefault(key, []).append(left)

    result: list[dict[str, Any]] = []

    for right in right_rows:
        key = normalize_key(right.get(right_key))
        matches = index.get(key, []) if key is not None else []

        if matches:
            for left in matches:
                merged = {column: left.get(column) for column in left_columns}
                merged.update({column: right.get(column) for column in right_columns})
                result.append(merged)
        else:
            merged = {column: None for column in left_columns}
            merged.update({column: right.get(column) for column in right_columns})
            result.append(merged)

    return result


def full_outer_join(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    left_key: str,
    right_key: str,
) -> list[dict[str, Any]]:
    """
    FULL OUTER JOIN semantics:

    * matching rows are returned once per matching pair;
    * unmatched left rows survive with NULL right-side values;
    * unmatched right rows survive with NULL left-side values.
    """

    left_columns = list(left_rows[0].keys()) if left_rows else []
    right_columns = list(right_rows[0].keys()) if right_rows else []

    right_index: dict[Any, list[tuple[int, dict[str, Any]]]] = {}

    for right_index_position, right in enumerate(right_rows):
        key = normalize_key(right.get(right_key))
        if key is not None:
            right_index.setdefault(key, []).append(
                (right_index_position, right)
            )

    matched_right_positions: set[int] = set()
    result: list[dict[str, Any]] = []

    for left in left_rows:
        key = normalize_key(left.get(left_key))
        matches = right_index.get(key, []) if key is not None else []

        if matches:
            for position, right in matches:
                matched_right_positions.add(position)

                merged = {column: left.get(column) for column in left_columns}
                merged.update({column: right.get(column) for column in right_columns})
                result.append(merged)
        else:
            merged = {column: left.get(column) for column in left_columns}
            merged.update({column: None for column in right_columns})
            result.append(merged)

    for position, right in enumerate(right_rows):
        if position not in matched_right_positions:
            merged = {column: None for column in left_columns}
            merged.update({column: right.get(column) for column in right_columns})
            result.append(merged)

    return result


def inner_join(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    left_key: str,
    right_key: str,
) -> list[dict[str, Any]]:
    """Reference implementation used to contrast INNER JOIN with outer joins."""

    right_index: dict[Any, list[dict[str, Any]]] = {}

    for right in right_rows:
        key = right.get(right_key)
        if key is not None:
            right_index.setdefault(key, []).append(right)

    left_columns = list(left_rows[0].keys()) if left_rows else []
    right_columns = list(right_rows[0].keys()) if right_rows else []

    result = []

    for left in left_rows:
        key = left.get(left_key)
        if key is None:
            continue

        for right in right_index.get(key, []):
            merged = {column: left.get(column) for column in left_columns}
            merged.update({column: right.get(column) for column in right_columns})
            result.append(merged)

    return result


def anti_join_right(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    left_key: str,
    right_key: str,
) -> list[dict[str, Any]]:
    """
    Returns right-side rows without a matching left-side row.

    This is useful when a RIGHT JOIN is used specifically to discover
    records that have no corresponding record on the other side.
    """

    left_keys = {
        row.get(left_key)
        for row in left_rows
        if row.get(left_key) is not None
    }

    return [
        row for row in right_rows
        if row.get(right_key) is None or row.get(right_key) not in left_keys
    ]


def main() -> None:
    employees = [
        {"employee_id": 101, "employee_name": "Aarav", "department_id": 10},
        {"employee_id": 102, "employee_name": "Meera", "department_id": 20},
        {"employee_id": 103, "employee_name": "Kabir", "department_id": 20},
        {"employee_id": 104, "employee_name": "Isha", "department_id": 40},
        {"employee_id": 105, "employee_name": "Rohan", "department_id": None},
    ]

    departments = [
        {"department_id": 10, "department_name": "Engineering", "manager_id": 9001},
        {"department_id": 20, "department_name": "Finance", "manager_id": 9002},
        {"department_id": 30, "department_name": "Research", "manager_id": 9003},
        {"department_id": 40, "department_name": "Operations", "manager_id": None},
        {"department_id": 50, "department_name": "Legal", "manager_id": 9005},
    ]

    projects = [
        {"project_id": 501, "project_name": "Data Platform", "department_id": 10},
        {"project_id": 502, "project_name": "Risk Engine", "department_id": 20},
        {"project_id": 503, "project_name": "Quantum Lab", "department_id": 30},
        {"project_id": 504, "project_name": "Warehouse Automation", "department_id": 60},
    ]

    print("RIGHT JOIN AND FULL OUTER JOIN")
    print("==============================")

    # A RIGHT JOIN preserves every department, even departments with
    # no employee. This makes it useful when the right table is the
    # business-complete side of the relationship.
    employee_department_right = right_join(
        employees,
        departments,
        "department_id",
        "department_id",
    )

    print_rows(
        "RIGHT JOIN: every department must remain visible",
        employee_department_right,
    )

    # Department 30 and 50 appear even though no employee belongs to them.
    # Department 40 has an employee but no manager; manager_id remains NULL
    # because that NULL is stored in the department row itself.

    employee_department_full = full_outer_join(
        employees,
        departments,
        "department_id",
        "department_id",
    )

    print_rows(
        "FULL OUTER JOIN: preserve employees and departments",
        employee_department_full,
    )

    # Rohan has no department, so his employee row survives with
    # department columns set to None. Departments 30 and 50 also survive
    # because no employee matches them.
    print_rows(
        "Unmatched departments",
        anti_join_right(
            employees,
            departments,
            "department_id",
            "department_id",
        ),
    )

    # FULL OUTER JOIN is especially useful for reconciliation. Here it
    # exposes both orphaned employees and departments with no employees.
    reconciliation = full_outer_join(
        employees,
        departments,
        "department_id",
        "department_id",
    )

    print_rows("Reconciliation result", reconciliation)

    # A second dataset shows why FULL OUTER JOIN is different from merely
    # running two separate queries. Projects contain department 60, which
    # has no department master record, while department 30 has a department
    # but no employee and still owns a project.
    project_department_full = full_outer_join(
        projects,
        departments,
        "department_id",
        "department_id",
    )

    print_rows(
        "FULL OUTER JOIN: projects versus departments",
        project_department_full,
    )

    # Duplicate keys produce multiple result rows. This is an important
    # property of relational joins: a single left row can match multiple
    # right rows and vice versa.
    duplicate_left = [
        {"assignment_id": 1, "department_id": 20, "role": "Analyst"},
        {"assignment_id": 2, "department_id": 20, "role": "Controller"},
    ]

    duplicate_right = [
        {"department_id": 20, "policy": "Quarterly Review"},
        {"department_id": 20, "policy": "Budget Approval"},
    ]

    print_rows(
        "Many-to-many matching behavior",
        full_outer_join(
            duplicate_left,
            duplicate_right,
            "department_id",
            "department_id",
        ),
    )

    # NULL never equals NULL in SQL. The Python implementation explicitly
    # follows that rule instead of treating two None values as a match.
    null_left = [{"id": 1, "group_id": None}]
    null_right = [{"group_id": None, "label": "Unassigned"}]

    print_rows(
        "NULL does not match NULL",
        full_outer_join(null_left, null_right, "group_id", "group_id"),
    )

    # Compare the preservation behavior with INNER JOIN.
    print_rows(
        "INNER JOIN for comparison",
        inner_join(
            employees,
            departments,
            "department_id",
            "department_id",
        ),
    )

    # Demonstrate a practical reporting transformation. A FULL OUTER JOIN
    # is followed by classification so data-quality problems become explicit.
    classified = []

    for row in reconciliation:
        employee_present = row["employee_id"] is not None
        department_present = row["department_id"] is not None
        department_name = row["department_name"]

        if employee_present and department_name is not None:
            status = "MATCHED"
        elif employee_present:
            status = "EMPLOYEE_WITHOUT_DEPARTMENT"
        else:
            status = "DEPARTMENT_WITHOUT_EMPLOYEE"

        classified.append(
            {
                "employee_name": row["employee_name"],
                "department_name": department_name,
                "status": status,
            }
        )

    print_rows("Data-quality classification", classified)

    # Complexity note:
    # The implementations build hash indexes, giving expected O(L + R)
    # lookup behavior for a single-key equality join, where L and R are the
    # input sizes. Output generation can still be larger because joins with
    # duplicate keys create one row for every matching pair.
    print("\nPerformance considerations:")
    print("Hash-based equality joins avoid repeatedly scanning the opposite table.")
    print("Duplicate keys can increase output size multiplicatively.")
    print("SQL databases may instead choose hash, merge, or nested-loop join plans.")
    print("Indexes, statistics, cardinality, predicates, and table size affect the plan.")

    # Production validation prevents accidental joins on incompatible domains.
    if not all(isinstance(row["department_id"], (int, type(None))) for row in employees):
        raise ValueError("Employee department_id values must be integers or None.")

    if not all(isinstance(row["department_id"], (int, type(None))) for row in departments):
        raise ValueError("Department department_id values must be integers or None.")

    print("\nValidation completed successfully.")


if __name__ == "__main__":
    main()
