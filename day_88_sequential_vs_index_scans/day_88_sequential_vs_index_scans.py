#!/usr/bin/env python3
"""
Sequential Scan, Index Scan, and Bitmap Scan
A self-contained PostgreSQL-inspired query execution simulator.

Run:
    python scan_simulator.py

The program demonstrates:
    1. Sequential scans
    2. Index scans
    3. Bitmap index scans
    4. Bitmap AND operations
    5. Selectivity estimation
    6. Cost-based query planning
    7. Query execution and instrumentation
    8. Index maintenance and validation
    9. Performance comparisons
"""

from __future__ import annotations

import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PAGE_SIZE = 100
RANDOM_PAGE_COST = 4.0
SEQUENTIAL_PAGE_COST = 1.0
CPU_TUPLE_COST = 0.01
CPU_INDEX_TUPLE_COST = 0.005


class ScanType(Enum):
    SEQUENTIAL = "Seq Scan"
    INDEX = "Index Scan"
    BITMAP = "Bitmap Heap Scan"


class Operator(Enum):
    EQUALS = "="
    IN = "IN"


# ---------------------------------------------------------
# Domain models
# ---------------------------------------------------------

@dataclass(frozen=True)
class Predicate:
    column: str
    operator: Operator
    value: Any

    def matches(self, row: dict[str, Any]) -> bool:
        actual = row[self.column]

        if self.operator == Operator.EQUALS:
            return actual == self.value

        if self.operator == Operator.IN:
            return actual in self.value

        raise ValueError("Unsupported predicate operator")


@dataclass
class ExecutionMetrics:
    scan_type: ScanType
    rows_examined: int = 0
    rows_returned: int = 0
    pages_read: int = 0
    index_entries_examined: int = 0
    heap_blocks_accessed: int = 0
    bitmap_memory_bytes: int = 0
    execution_time_ms: float = 0.0
    estimated_cost: float = 0.0


@dataclass
class QueryResult:
    rows: list[dict[str, Any]]
    metrics: ExecutionMetrics


@dataclass
class Index:
    name: str
    column: str
    entries: dict[Any, set[int]] = field(
        default_factory=lambda: defaultdict(set)
    )

    def add(self, value: Any, row_id: int) -> None:
        self.entries[value].add(row_id)

    def remove(self, value: Any, row_id: int) -> None:
        self.entries[value].discard(row_id)

    def lookup(self, predicate: Predicate) -> set[int]:
        if predicate.operator == Operator.EQUALS:
            return set(self.entries.get(predicate.value, set()))

        if predicate.operator == Operator.IN:
            result: set[int] = set()
            for value in predicate.value:
                result.update(self.entries.get(value, set()))
            return result

        raise ValueError("Unsupported index operation")


# ---------------------------------------------------------
# Table implementation
# ---------------------------------------------------------

class Table:
    def __init__(self, name: str, rows: Iterable[dict[str, Any]]):
        self.name = name
        self.rows: list[dict[str, Any]] = []
        self.indexes: dict[str, Index] = {}
        self.columns: set[str] = set()

        for row in rows:
            self.insert(row)

    def insert(self, row: dict[str, Any]) -> int:
        if not isinstance(row, dict) or not row:
            raise ValueError("A non-empty dictionary row is required")

        if self.columns and set(row) != self.columns:
            raise ValueError("Row columns do not match table definition")

        if not self.columns:
            self.columns = set(row)

        row_id = len(self.rows)
        stored = dict(row)
        self.rows.append(stored)

        for index in self.indexes.values():
            index.add(stored[index.column], row_id)

        return row_id

    def create_index(self, column: str, name: str | None = None) -> None:
        if column not in self.columns:
            raise ValueError(f"Unknown column: {column}")

        if column in self.indexes:
            raise ValueError(f"Index already exists on {column}")

        index = Index(name or f"idx_{self.name}_{column}", column)

        for row_id, row in enumerate(self.rows):
            index.add(row[column], row_id)

        self.indexes[column] = index

    def delete(self, row_id: int) -> None:
        if not 0 <= row_id < len(self.rows):
            raise IndexError("Invalid row identifier")

        row = self.rows[row_id]

        for index in self.indexes.values():
            index.remove(row[index.column], row_id)

        # Preserve row identifiers so existing index references remain valid.
        self.rows[row_id] = {}

    def validate_indexes(self) -> bool:
        for column, index in self.indexes.items():
            expected: dict[Any, set[int]] = defaultdict(set)

            for row_id, row in enumerate(self.rows):
                if row:
                    expected[row[column]].add(row_id)

            if dict(expected) != dict(index.entries):
                return False

        return True

    @property
    def active_rows(self) -> int:
        return sum(bool(row) for row in self.rows)

    @property
    def page_count(self) -> int:
        return max(1, math.ceil(self.active_rows / PAGE_SIZE))


# ---------------------------------------------------------
# Cost-based query planner
# ---------------------------------------------------------

class QueryPlanner:
    def __init__(self, table: Table):
        self.table = table

    def estimate_selectivity(self, predicate: Predicate) -> float:
        values = [
            row[predicate.column]
            for row in self.table.rows if row
        ]

        if not values:
            return 0.0

        if predicate.operator == Operator.EQUALS:
            return values.count(predicate.value) / len(values)

        if predicate.operator == Operator.IN:
            return sum(
                value in predicate.value for value in values
            ) / len(values)

        raise ValueError("Unsupported predicate")

    def plan(self, predicates: list[Predicate]) -> tuple[ScanType, float]:
        if not predicates:
            return (
                ScanType.SEQUENTIAL,
                self.table.page_count * SEQUENTIAL_PAGE_COST
                + self.table.active_rows * CPU_TUPLE_COST
            )

        if any(p.column not in self.table.columns for p in predicates):
            raise ValueError("Predicate references an unknown column")

        sequential_cost = (
            self.table.page_count * SEQUENTIAL_PAGE_COST
            + self.table.active_rows * CPU_TUPLE_COST
        )

        indexable = [
            p for p in predicates if p.column in self.table.indexes
        ]

        if not indexable:
            return ScanType.SEQUENTIAL, sequential_cost

        selectivities = [
            self.estimate_selectivity(p) for p in indexable
        ]

        if len(indexable) >= 2:
            combined = min(
                1.0,
                math.prod(selectivities)
            )

            estimated_rows = self.table.active_rows * combined

            # Bitmap construction, index access, and heap-page access.
            bitmap_blocks = min(
                self.table.page_count,
                math.ceil(estimated_rows / PAGE_SIZE)
            )

            bitmap_cost = (
                len(indexable) * math.log2(
                    max(2, self.table.active_rows)
                )
                + estimated_rows * CPU_INDEX_TUPLE_COST
                + bitmap_blocks * RANDOM_PAGE_COST
                + self.table.active_rows * combined * CPU_TUPLE_COST
            )

            if bitmap_cost < sequential_cost:
                return ScanType.BITMAP, bitmap_cost

        best_index = min(
            selectivities,
            key=lambda selectivity: (
                math.log2(max(2, self.table.active_rows))
                + selectivity * self.table.active_rows
                * (RANDOM_PAGE_COST + CPU_INDEX_TUPLE_COST)
            )
        )

        index_cost = (
            math.log2(max(2, self.table.active_rows))
            + best_index * self.table.active_rows
            * (RANDOM_PAGE_COST + CPU_INDEX_TUPLE_COST)
        )

        if index_cost < sequential_cost:
            return ScanType.INDEX, index_cost

        return ScanType.SEQUENTIAL, sequential_cost


# ---------------------------------------------------------
# Query executor
# ---------------------------------------------------------

class QueryExecutor:
    def __init__(self, table: Table):
        self.table = table
        self.planner = QueryPlanner(table)

    def execute(
        self,
        predicates: list[Predicate],
        forced_scan: ScanType | None = None
    ) -> QueryResult:

        if not all(isinstance(p, Predicate) for p in predicates):
            raise TypeError("All filters must be Predicate objects")

        scan_type, cost = self.planner.plan(predicates)

        if forced_scan is not None:
            scan_type = forced_scan

        started = time.perf_counter()

        metrics = ExecutionMetrics(
            scan_type=scan_type,
            estimated_cost=cost
        )

        if scan_type == ScanType.SEQUENTIAL:
            candidates = range(len(self.table.rows))

            for row_id in candidates:
                row = self.table.rows[row_id]

                if not row:
                    continue

                metrics.rows_examined += 1

                if all(p.matches(row) for p in predicates):
                    metrics.rows_returned += 1

            result_ids = [
                i for i, row in enumerate(self.table.rows)
                if row and all(p.matches(row) for p in predicates)
            ]

            metrics.pages_read = self.table.page_count
            metrics.heap_blocks_accessed = self.table.page_count

        elif scan_type == ScanType.INDEX:
            if not self.table.indexes:
                raise ValueError("Index Scan requires an index")

            usable = [
                p for p in predicates
                if p.column in self.table.indexes
            ]

            if not usable:
                raise ValueError("No usable index")

            best = min(
                usable,
                key=self.planner.estimate_selectivity
            )

            index = self.table.indexes[best.column]
            result_ids = sorted(index.lookup(best))

            metrics.index_entries_examined = len(result_ids)
            metrics.rows_examined = len(result_ids)

            result_ids = [
                i for i in result_ids
                if self.table.rows[i]
                and all(p.matches(self.table.rows[i]) for p in predicates)
            ]

            metrics.rows_returned = len(result_ids)
            metrics.heap_blocks_accessed = len({
                i // PAGE_SIZE for i in result_ids
            })
            metrics.pages_read = metrics.heap_blocks_accessed

        elif scan_type == ScanType.BITMAP:
            usable = [
                p for p in predicates
                if p.column in self.table.indexes
            ]

            if len(usable) < 2:
                raise ValueError("Bitmap Scan requires two indexed predicates")

            bitmaps = []

            for predicate in usable:
                ids = self.table.indexes[predicate.column].lookup(predicate)
                metrics.index_entries_examined += len(ids)
                bitmaps.append(ids)

            # Bitmap AND combines candidate tuple identifiers.
            bitmap = set.intersection(*bitmaps)
            metrics.bitmap_memory_bytes = max(
                8, ((len(self.table.rows) + 63) // 64) * 8
            )

            result_ids = sorted(
                row_id for row_id in bitmap
                if self.table.rows[row_id]
                and all(p.matches(self.table.rows[row_id])
                        for p in predicates)
            )

            metrics.rows_examined = len(bitmap)
            metrics.rows_returned = len(result_ids)

            metrics.heap_blocks_accessed = len({
                i // PAGE_SIZE for i in bitmap
            })
            metrics.pages_read = metrics.heap_blocks_accessed

        else:
            raise ValueError("Unsupported scan strategy")

        metrics.execution_time_ms = (
            time.perf_counter() - started
        ) * 1000

        return QueryResult(
            rows=[dict(self.table.rows[i]) for i in result_ids],
            metrics=metrics
        )


# ---------------------------------------------------------
# Demonstration dataset
# ---------------------------------------------------------

def generate_employees(count: int = 10000) -> list[dict[str, Any]]:
    random.seed(42)

    departments = ["Engineering", "Finance", "Operations", "Security"]
    locations = ["Lucknow", "Delhi", "Mumbai", "Bengaluru"]

    rows = []

    for employee_id in range(1, count + 1):
        rows.append({
            "employee_id": employee_id,
            "department": random.choices(
                departments,
                weights=[50, 15, 25, 10]
            )[0],
            "location": random.choice(locations),
            "salary": random.randint(30000, 180000),
            "active": random.random() < 0.85
        })

    return rows


def print_metrics(label: str, result: QueryResult) -> None:
    m = result.metrics

    print(f"\n{label}")
    print("-" * 55)
    print(f"Scan type             : {m.scan_type.value}")
    print(f"Estimated cost        : {m.estimated_cost:.2f}")
    print(f"Rows examined         : {m.rows_examined}")
    print(f"Rows returned         : {m.rows_returned}")
    print(f"Index entries         : {m.index_entries_examined}")
    print(f"Heap blocks accessed  : {m.heap_blocks_accessed}")
    print(f"Pages read            : {m.pages_read}")
    print(f"Bitmap memory         : {m.bitmap_memory_bytes} bytes")
    print(f"Execution time        : {m.execution_time_ms:.3f} ms")


# ---------------------------------------------------------
# Main execution
# ---------------------------------------------------------

def main() -> None:
    table = Table("employees", generate_employees())

    table.create_index("employee_id")
    table.create_index("department")
    table.create_index("location")

    executor = QueryExecutor(table)

    print("=" * 65)
    print("POSTGRESQL SCAN STRATEGY SIMULATOR")
    print("=" * 65)
    print(f"Table: {table.name}")
    print(f"Rows: {table.active_rows}")
    print(f"Pages: {table.page_count}")
    print(f"Indexes: {list(table.indexes)}")

    # 1. Sequential scan.
    broad_query = [
        Predicate("salary", Operator.EQUALS, 50000)
    ]

    # Salary is not indexed, so the planner selects Seq Scan.
    sequential = executor.execute(broad_query)
    print_metrics("1. Sequential Scan", sequential)

    # 2. Index scan.
    selective_query = [
        Predicate("employee_id", Operator.EQUALS, 500)
    ]

    index_result = executor.execute(selective_query)
    print_metrics("2. Index Scan", index_result)

    # 3. Bitmap scan.
    bitmap_query = [
        Predicate("department", Operator.EQUALS, "Engineering"),
        Predicate("location", Operator.EQUALS, "Lucknow")
    ]

    bitmap_result = executor.execute(
        bitmap_query,
        forced_scan=ScanType.BITMAP
    )
    print_metrics("3. Bitmap AND Scan", bitmap_result)

    # 4. Compare all strategies on the same indexed query.
    print("\n4. Strategy comparison")

    for strategy in ScanType:
        result = executor.execute(
            selective_query,
            forced_scan=strategy
        )
        print(
            f"{strategy.value:22} "
            f"rows={result.metrics.rows_returned:5} "
            f"examined={result.metrics.rows_examined:5}"
        )

    # 5. Verify correctness across strategies.
    reference = executor.execute(
        selective_query,
        forced_scan=ScanType.SEQUENTIAL
    )

    for strategy in ScanType:
        if strategy == ScanType.BITMAP:
            continue

        candidate = executor.execute(
            selective_query,
            forced_scan=strategy
        )

        assert reference.rows == candidate.rows

    # 6. Validate index integrity.
    assert table.validate_indexes()
    print("\nIndex integrity: VALID")

    # 7. Insert and verify index maintenance.
    new_id = table.insert({
        "employee_id": 10001,
        "department": "Security",
        "location": "Lucknow",
        "salary": 95000,
        "active": True
    })

    assert new_id == 10000
    assert table.validate_indexes()

    inserted = executor.execute([
        Predicate("employee_id", Operator.EQUALS, 10001)
    ])

    assert len(inserted.rows) == 1
    print("Insert and index maintenance: VALID")

    # 8. Delete and verify index maintenance.
    table.delete(new_id)
    assert table.validate_indexes()

    print("Delete and index maintenance: VALID")

    # 9. Invalid input handling.
    try:
        executor.execute([
            Predicate("unknown_column", Operator.EQUALS, 1)
        ])
    except ValueError as error:
        print(f"Expected validation error: {error}")

    print("\nAll validation checks passed.")


if __name__ == "__main__":
    main()
