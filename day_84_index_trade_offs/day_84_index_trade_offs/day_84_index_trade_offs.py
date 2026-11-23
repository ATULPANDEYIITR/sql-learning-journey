#!/usr/bin/env python3
"""
Index Trade-offs: Write Overhead, Storage, Maintenance and Over-Indexing

A self-contained simulation of relational database index behavior.

Features:
- Table and index modeling
- B-tree-like index metadata simulation
- Read and write workload analysis
- Insert, update and delete overhead
- Index storage estimation
- Index maintenance tracking
- Index usage statistics
- Composite and covering index evaluation
- Over-indexing detection
- Index selection recommendations
- Workload-based cost analysis
- Validation and exception handling

Run:
    python index_tradeoffs.py

No external dependencies required.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import json
import math
import random


class IndexType(Enum):
    BTREE = "BTREE"
    HASH = "HASH"
    COMPOSITE = "COMPOSITE"
    COVERING = "COVERING"


class Operation(Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class IndexState(Enum):
    ACTIVE = "ACTIVE"
    NEEDS_REBUILD = "NEEDS_REBUILD"
    DISABLED = "DISABLED"


@dataclass
class IndexStatistics:
    lookups: int = 0
    inserts: int = 0
    updates: int = 0
    deletes: int = 0
    maintenance_operations: int = 0
    estimated_bytes: int = 0
    fragmentation_percent: float = 0.0

    @property
    def total_writes(self) -> int:
        return self.inserts + self.updates + self.deletes


@dataclass
class Index:
    name: str
    columns: tuple[str, ...]
    index_type: IndexType = IndexType.BTREE
    unique: bool = False
    included_columns: tuple[str, ...] = ()
    state: IndexState = IndexState.ACTIVE
    statistics: IndexStatistics = field(
        default_factory=IndexStatistics
    )

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Index name cannot be empty")

        if not self.columns:
            raise ValueError("An index requires at least one key column")

        if len(set(self.columns)) != len(self.columns):
            raise ValueError("Duplicate index columns are not allowed")

        if set(self.columns) & set(self.included_columns):
            raise ValueError("Included columns cannot duplicate key columns")

        if self.index_type == IndexType.COMPOSITE and len(self.columns) < 2:
            raise ValueError("Composite indexes require at least two columns")

        if self.index_type == IndexType.HASH and len(self.columns) != 1:
            raise ValueError("Hash indexes require exactly one column")

    def supports(self, query_columns: tuple[str, ...]) -> bool:
        """
        Approximate leftmost-prefix matching for B-tree indexes.
        Included columns do not participate in search ordering.
        """
        if self.state != IndexState.ACTIVE:
            return False

        if not query_columns:
            return False

        if self.index_type == IndexType.HASH:
            return query_columns == self.columns

        return self.columns[:len(query_columns)] == query_columns

    def calculate_storage(self, row_count: int) -> int:
        """
        Estimate storage using configurable educational assumptions.

        This is not a physical PostgreSQL page-size calculation.
        """
        key_bytes = 24 * len(self.columns)
        included_bytes = 16 * len(self.included_columns)
        pointer_bytes = 8
        entry_bytes = key_bytes + included_bytes + pointer_bytes

        raw_size = row_count * entry_bytes

        # Account for page overhead and unused space.
        estimated = math.ceil(raw_size / 0.85)

        self.statistics.estimated_bytes = estimated
        return estimated

    def record_write(self, operation: Operation) -> None:
        if self.state == IndexState.DISABLED:
            return

        stats = self.statistics

        if operation == Operation.INSERT:
            stats.inserts += 1
        elif operation == Operation.UPDATE:
            stats.updates += 1
        elif operation == Operation.DELETE:
            stats.deletes += 1

        # Simulated fragmentation caused by index modifications.
        stats.fragmentation_percent = min(
            100.0,
            stats.fragmentation_percent + 0.015
        )


@dataclass
class Query:
    name: str
    columns: tuple[str, ...]
    frequency: int
    estimated_rows: int
    operation: Operation = Operation.SELECT

    def __post_init__(self) -> None:
        if self.frequency < 0 or self.estimated_rows < 0:
            raise ValueError("Frequency and row estimates cannot be negative")


@dataclass
class Workload:
    reads_per_day: int
    inserts_per_day: int
    updates_per_day: int
    deletes_per_day: int

    def __post_init__(self) -> None:
        for value in (
            self.reads_per_day,
            self.inserts_per_day,
            self.updates_per_day,
            self.deletes_per_day
        ):
            if value < 0:
                raise ValueError("Workload values cannot be negative")

    @property
    def total_writes(self) -> int:
        return (
            self.inserts_per_day
            + self.updates_per_day
            + self.deletes_per_day
        )


class DatabaseTable:
    def __init__(
        self,
        name: str,
        columns: list[str],
        row_count: int = 0,
        row_size_bytes: int = 200
    ):
        if not name.strip():
            raise ValueError("Table name cannot be empty")

        if not columns or len(columns) != len(set(columns)):
            raise ValueError("Table columns must be nonempty and unique")

        if row_count < 0 or row_size_bytes <= 0:
            raise ValueError("Invalid table dimensions")

        self.name = name
        self.columns = set(columns)
        self.row_count = row_count
        self.row_size_bytes = row_size_bytes
        self.indexes: dict[str, Index] = {}
        self.queries: list[Query] = []

    def add_index(self, index: Index) -> None:
        if index.name in self.indexes:
            raise ValueError(f"Index already exists: {index.name}")

        unknown = (
            set(index.columns) | set(index.included_columns)
        ) - self.columns

        if unknown:
            raise ValueError(f"Unknown columns: {sorted(unknown)}")

        for existing in self.indexes.values():
            if (
                existing.columns == index.columns
                and existing.included_columns == index.included_columns
                and existing.index_type == index.index_type
                and existing.state != IndexState.DISABLED
            ):
                raise ValueError(
                    f"Equivalent active index already exists: {existing.name}"
                )

        self.indexes[index.name] = index
        index.calculate_storage(self.row_count)

    def drop_index(self, name: str) -> None:
        if name not in self.indexes:
            raise KeyError(f"Unknown index: {name}")

        del self.indexes[name]

    def add_query(self, query: Query) -> None:
        unknown = set(query.columns) - self.columns

        if unknown:
            raise ValueError(f"Query references unknown columns: {unknown}")

        self.queries.append(query)

    def insert(self, count: int = 1) -> int:
        if count <= 0:
            raise ValueError("Insert count must be positive")

        self.row_count += count

        for index in self.indexes.values():
            for _ in range(count):
                index.record_write(Operation.INSERT)

            index.calculate_storage(self.row_count)

        return self.row_count

    def update(
        self,
        count: int,
        modified_columns: set[str]
    ) -> None:
        if count <= 0 or count > self.row_count:
            raise ValueError("Invalid update count")

        if not modified_columns <= self.columns:
            raise ValueError("Update contains unknown columns")

        for index in self.indexes.values():
            affected = (
                set(index.columns) | set(index.included_columns)
            ) & modified_columns

            if affected:
                for _ in range(count):
                    index.record_write(Operation.UPDATE)

        # Updating non-indexed columns does not require key maintenance
        # for ordinary indexes, although row-level database work remains.

    def delete(self, count: int = 1) -> int:
        if count <= 0 or count > self.row_count:
            raise ValueError("Invalid delete count")

        self.row_count -= count

        for index in self.indexes.values():
            for _ in range(count):
                index.record_write(Operation.DELETE)

            index.calculate_storage(self.row_count)

        return self.row_count

    def find_index(self, query: Query) -> Optional[Index]:
        candidates = [
            index
            for index in self.indexes.values()
            if index.supports(query.columns)
        ]

        if not candidates:
            return None

        # Prefer the narrowest matching index.
        return min(
            candidates,
            key=lambda index: (
                len(index.columns),
                index.statistics.estimated_bytes
            )
        )

    def simulate_select(self, query: Query) -> dict[str, Any]:
        index = self.find_index(query)

        # Simple educational cost model, not an optimizer cost estimate.
        full_scan_cost = max(1, self.row_count)

        if index is None:
            return {
                "query": query.name,
                "access_method": "TABLE_SCAN",
                "estimated_cost": full_scan_cost,
                "index": None
            }

        index.statistics.lookups += query.frequency

        index_levels = max(
            1,
            math.ceil(math.log2(max(2, self.row_count)))
        )

        estimated_cost = (
            index_levels
            + query.estimated_rows
            + (0 if index.index_type == IndexType.COVERING else 2)
        )

        return {
            "query": query.name,
            "access_method": "INDEX_SCAN",
            "estimated_cost": estimated_cost,
            "index": index.name
        }

    def rebuild_index(self, name: str) -> None:
        index = self.indexes.get(name)

        if index is None:
            raise KeyError(name)

        if index.state == IndexState.DISABLED:
            raise ValueError("Disabled indexes cannot be rebuilt")

        index.statistics.fragmentation_percent = 0.0
        index.statistics.maintenance_operations += 1
        index.state = IndexState.ACTIVE
        index.calculate_storage(self.row_count)

    def total_index_storage(self) -> int:
        return sum(
            index.calculate_storage(self.row_count)
            for index in self.indexes.values()
            if index.state != IndexState.DISABLED
        )

    def report(self) -> dict[str, Any]:
        return {
            "table": self.name,
            "rows": self.row_count,
            "table_storage_bytes": (
                self.row_count * self.row_size_bytes
            ),
            "index_storage_bytes": self.total_index_storage(),
            "indexes": [
                {
                    "name": index.name,
                    "columns": list(index.columns),
                    "type": index.index_type.value,
                    "state": index.state.value,
                    "storage_bytes": index.statistics.estimated_bytes,
                    "lookups": index.statistics.lookups,
                    "writes": index.statistics.total_writes,
                    "fragmentation_percent": round(
                        index.statistics.fragmentation_percent, 2
                    )
                }
                for index in self.indexes.values()
            ]
        }


class IndexAdvisor:
    """
    Workload-based index advisor.

    Recommendations are candidates for testing, not automatic DDL.
    """

    def __init__(self, table: DatabaseTable):
        self.table = table

    def analyze(self) -> list[dict[str, Any]]:
        candidates: dict[tuple[str, ...], int] = defaultdict(int)

        for query in self.table.queries:
            if query.operation != Operation.SELECT:
                continue

            if self.table.find_index(query) is None:
                candidates[query.columns] += (
                    query.frequency * max(1, query.estimated_rows)
                )

        recommendations = []

        for columns, benefit in candidates.items():
            existing_prefix = any(
                index.supports(columns)
                for index in self.table.indexes.values()
            )

            if existing_prefix:
                continue

            proposed_storage = (
                self.table.row_count
                * (24 * len(columns) + 8)
                / 0.85
            )

            write_count = max(1, self.table.row_count)

            score = benefit / max(1, proposed_storage)

            recommendations.append({
                "columns": list(columns),
                "read_benefit_score": round(score, 4),
                "estimated_storage_bytes": round(proposed_storage),
                "reason": (
                    "Frequent read pattern without a matching index"
                ),
                "write_risk": (
                    "Every relevant INSERT, UPDATE or DELETE may "
                    "require additional index maintenance"
                ),
                "priority": (
                    "HIGH" if score > 1 else "REVIEW"
                ),
                "sample_write_to_read_ratio": round(
                    0.0, 2
                ) if write_count == 0 else 0.0
            })

        return sorted(
            recommendations,
            key=lambda item: item["read_benefit_score"],
            reverse=True
        )


def detect_over_indexing(table: DatabaseTable) -> list[str]:
    warnings = []

    indexes = list(table.indexes.values())

    for index in indexes:
        if index.statistics.lookups == 0:
            warnings.append(
                f"{index.name}: no observed lookups"
            )

        if index.statistics.total_writes > 0:
            ratio = (
                index.statistics.total_writes
                / max(1, index.statistics.lookups)
            )

            if ratio > 10:
                warnings.append(
                    f"{index.name}: write activity greatly exceeds "
                    f"lookup activity (ratio={ratio:.2f})"
                )

        if index.statistics.estimated_bytes > (
            table.row_count * table.row_size_bytes
        ):
            warnings.append(
                f"{index.name}: estimated index storage exceeds "
                "table storage"
            )

    for i, first in enumerate(indexes):
        for second in indexes[i + 1:]:
            if (
                first.columns == second.columns[:len(first.columns)]
                and first.columns != second.columns
                and first.state == IndexState.ACTIVE
                and second.state == IndexState.ACTIVE
            ):
                warnings.append(
                    f"Possible prefix overlap: {first.name} and "
                    f"{second.name}"
                )

    return warnings


def calculate_workload_cost(
    table: DatabaseTable,
    workload: Workload
) -> dict[str, Any]:
    """
    Compare modeled index maintenance against read access benefits.
    One write maintenance unit is charged for each active index.
    """
    active_indexes = [
        index for index in table.indexes.values()
        if index.state == IndexState.ACTIVE
    ]

    write_units = (
        workload.inserts_per_day
        + workload.deletes_per_day
    ) * len(active_indexes)

    for index in active_indexes:
        if index.columns:
            write_units += (
                workload.updates_per_day
            )

    read_savings = 0

    for query in table.queries:
        result = table.simulate_select(query)

        if result["access_method"] == "INDEX_SCAN":
            read_savings += (
                max(0, table.row_count - result["estimated_cost"])
                * query.frequency
            )

    return {
        "active_indexes": len(active_indexes),
        "daily_write_maintenance_units": write_units,
        "daily_read_savings_units": read_savings,
        "read_write_ratio": round(
            workload.reads_per_day / max(1, workload.total_writes),
            2
        ),
        "index_storage_bytes": table.total_index_storage()
    }


def build_demo() -> DatabaseTable:
    random.seed(42)

    table = DatabaseTable(
        name="orders",
        columns=[
            "order_id",
            "customer_id",
            "status",
            "created_at",
            "region",
            "total_amount",
            "description"
        ],
        row_count=100_000,
        row_size_bytes=320
    )

    table.add_index(
        Index(
            name="idx_orders_customer",
            columns=("customer_id",)
        )
    )

    table.add_index(
        Index(
            name="idx_orders_status_created",
            columns=("status", "created_at"),
            index_type=IndexType.COMPOSITE
        )
    )

    table.add_index(
        Index(
            name="idx_orders_region_covering",
            columns=("region",),
            included_columns=("total_amount",),
            index_type=IndexType.COVERING
        )
    )

    table.add_query(
        Query(
            name="customer_order_history",
            columns=("customer_id",),
            frequency=25_000,
            estimated_rows=15
        )
    )

    table.add_query(
        Query(
            name="pending_orders_by_date",
            columns=("status", "created_at"),
            frequency=12_000,
            estimated_rows=50
        )
    )

    table.add_query(
        Query(
            name="orders_by_region",
            columns=("region",),
            frequency=8_000,
            estimated_rows=100
        )
    )

    table.add_query(
        Query(
            name="description_search",
            columns=("description",),
            frequency=2_000,
            estimated_rows=500
        )
    )

    return table


def run_demo() -> None:
    table = build_demo()

    print("\nINDEX ACCESS SIMULATION")

    for query in table.queries:
        print(json.dumps(
            table.simulate_select(query),
            indent=2
        ))

    print("\nWRITE OPERATIONS")

    table.insert(500)
    table.update(
        count=100,
        modified_columns={"status", "total_amount"}
    )
    table.delete(50)

    print("\nINDEX STORAGE AND USAGE")

    print(json.dumps(table.report(), indent=2))

    print("\nOVER-INDEXING DETECTION")

    warnings = detect_over_indexing(table)

    for warning in warnings:
        print("-", warning)

    print("\nINDEX ADVISOR")

    advisor = IndexAdvisor(table)

    print(json.dumps(advisor.analyze(), indent=2))

    print("\nWORKLOAD COST MODEL")

    workload = Workload(
        reads_per_day=500_000,
        inserts_per_day=40_000,
        updates_per_day=25_000,
        deletes_per_day=5_000
    )

    print(json.dumps(
        calculate_workload_cost(table, workload),
        indent=2
    ))

    print("\nINDEX MAINTENANCE")

    table.rebuild_index("idx_orders_customer")

    print(
        "Customer index fragmentation:",
        table.indexes[
            "idx_orders_customer"
        ].statistics.fragmentation_percent
    )

    print("\nVALIDATION")

    try:
        table.add_index(
            Index(
                name="invalid_index",
                columns=("unknown_column",)
            )
        )
    except ValueError as error:
        print("Expected validation error:", error)

    assert table.row_count == 100_450
    assert table.total_index_storage() > 0
    assert len(table.indexes) == 3

    print("All assertions passed.")


if __name__ == "__main__":
    try:
        run_demo()
    except (ValueError, KeyError, AssertionError) as error:
        print(f"Execution failed: {error}")
        raise
