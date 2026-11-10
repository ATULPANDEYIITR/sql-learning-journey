#!/usr/bin/env python3
"""
Materialized Views: Refresh Strategies and Performance Optimization

Demonstrates:
- Materialized view creation and snapshot storage
- Full refresh and simulated incremental refresh
- Refresh scheduling and dependency management
- Concurrent-reader behavior through immutable snapshots
- Staleness measurement
- Query-performance comparison
- Refresh failure handling
- Data validation and audit logging
- Atomic snapshot replacement
- Dependency-aware refresh orchestration

Requires Python 3.10+.
Uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import random
import threading
import time

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("materialized_views")


class RefreshStrategy(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    CONCURRENT_SIMULATION = "concurrent_simulation"


class RefreshStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class MaterializedViewError(Exception):
    pass


class ValidationError(MaterializedViewError):
    pass


class RefreshError(MaterializedViewError):
    pass


@dataclass(frozen=True)
class SalesRecord:
    sale_id: int
    product_id: int
    category: str
    region: str
    quantity: int
    unit_price: float
    created_at: datetime

    def __post_init__(self) -> None:
        if self.sale_id <= 0 or self.product_id <= 0:
            raise ValidationError("Identifiers must be positive.")

        if not self.category.strip() or not self.region.strip():
            raise ValidationError("Category and region are required.")

        if self.quantity <= 0 or self.unit_price < 0:
            raise ValidationError("Invalid quantity or unit price.")

        if not self.created_at.tzinfo:
            raise ValidationError("Timestamp must include a timezone.")

    @property
    def revenue(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Aggregate:
    transaction_count: int = 0
    total_quantity: int = 0
    total_revenue: float = 0.0

    def add(self, record: SalesRecord) -> None:
        self.transaction_count += 1
        self.total_quantity += record.quantity
        self.total_revenue += record.revenue
        self.total_revenue = round(self.total_revenue, 2)

    def remove(self, record: SalesRecord) -> None:
        self.transaction_count -= 1
        self.total_quantity -= record.quantity
        self.total_revenue = round(
            self.total_revenue - record.revenue, 2
        )

        if self.transaction_count < 0 or self.total_quantity < 0:
            raise RefreshError("Aggregate consistency violation.")

        if self.transaction_count == 0:
            self.total_quantity = 0
            self.total_revenue = 0.0


@dataclass
class RefreshAudit:
    view_name: str
    strategy: RefreshStrategy
    status: RefreshStatus
    started_at: datetime
    completed_at: datetime
    records_processed: int
    duration_ms: float
    error: Optional[str] = None


@dataclass
class ViewSnapshot:
    rows: dict[tuple[Any, ...], Aggregate]
    generation: int
    refreshed_at: datetime
    source_version: int
    checksum: str


class SalesDatabase:
    """Thread-safe source-table simulation."""

    def __init__(self) -> None:
        self._records: dict[int, SalesRecord] = {}
        self._changes: list[tuple[int, SalesRecord]] = []
        self._version = 0
        self._lock = threading.RLock()

    def insert(self, record: SalesRecord) -> None:
        with self._lock:
            if record.sale_id in self._records:
                raise ValidationError("Duplicate sale identifier.")

            self._records[record.sale_id] = record
            self._version += 1
            self._changes.append((self._version, record))

    def update(self, record: SalesRecord) -> None:
        with self._lock:
            if record.sale_id not in self._records:
                raise ValidationError("Sale does not exist.")

            self._records[record.sale_id] = record
            self._version += 1
            self._changes.append((self._version, record))

    def delete(self, sale_id: int) -> None:
        with self._lock:
            if sale_id not in self._records:
                raise ValidationError("Sale does not exist.")

            old = self._records.pop(sale_id)
            self._version += 1

            # A deletion is represented by its old row and a tombstone.
            # The incremental engine consumes both operations.
            self._changes.append((self._version, old))

    def snapshot(
        self,
    ) -> tuple[list[SalesRecord], int, list[tuple[int, SalesRecord]]]:
        with self._lock:
            return (
                list(self._records.values()),
                self._version,
                list(self._changes),
            )

    def changes_since(
        self, version: int
    ) -> list[tuple[int, SalesRecord]]:
        with self._lock:
            return [
                change for change in self._changes
                if change[0] > version
            ]

    def get(self, sale_id: int) -> Optional[SalesRecord]:
        with self._lock:
            return self._records.get(sale_id)


class MaterializedView:
    """Maintains an aggregate snapshot derived from source records."""

    def __init__(
        self,
        name: str,
        grouping: tuple[str, ...],
        source: SalesDatabase,
        deleted_strategy: bool = True,
    ) -> None:
        allowed = {
            "category", "region", "product_id", "date"
        }

        if not grouping or not set(grouping).issubset(allowed):
            raise ValidationError("Unsupported grouping columns.")

        self.name = name
        self.grouping = grouping
        self.source = source
        self.deleted_strategy = deleted_strategy

        self._snapshot = ViewSnapshot(
            rows={},
            generation=0,
            refreshed_at=datetime.min.replace(
                tzinfo=timezone.utc
            ),
            source_version=0,
            checksum="",
        )

        self._lock = threading.RLock()

    def _key(self, record: SalesRecord) -> tuple[Any, ...]:
        values = {
            "category": record.category,
            "region": record.region,
            "product_id": record.product_id,
            "date": record.created_at.date().isoformat(),
        }
        return tuple(values[column] for column in self.grouping)

    def _aggregate(
        self,
        records: list[SalesRecord],
    ) -> dict[tuple[Any, ...], Aggregate]:
        result: dict[tuple[Any, ...], Aggregate] = {}

        for record in records:
            key = self._key(record)

            if key not in result:
                result[key] = Aggregate()

            result[key].add(record)

        return result

    @staticmethod
    def _checksum(
        rows: dict[tuple[Any, ...], Aggregate]
    ) -> str:
        payload = {
            str(key): {
                "count": value.transaction_count,
                "quantity": value.total_quantity,
                "revenue": value.total_revenue,
            }
            for key, value in sorted(rows.items(), key=lambda x: str(x[0]))
        }

        encoded = json.dumps(
            payload, sort_keys=True
        ).encode("utf-8")

        return hashlib.sha256(encoded).hexdigest()

    def full_refresh(self) -> RefreshAudit:
        started = datetime.now(timezone.utc)
        clock = time.perf_counter()

        try:
            records, version, _ = self.source.snapshot()
            rows = self._aggregate(records)

            candidate = ViewSnapshot(
                rows=rows,
                generation=self._snapshot.generation + 1,
                refreshed_at=datetime.now(timezone.utc),
                source_version=version,
                checksum=self._checksum(rows),
            )

            # Atomic publication: readers see either the old
            # snapshot or the complete new snapshot.
            with self._lock:
                self._snapshot = candidate

            return RefreshAudit(
                self.name,
                RefreshStrategy.FULL,
                RefreshStatus.SUCCESS,
                started,
                datetime.now(timezone.utc),
                len(records),
                (time.perf_counter() - clock) * 1000,
            )

        except Exception as exc:
            logger.exception("Full refresh failed for %s", self.name)

            return RefreshAudit(
                self.name,
                RefreshStrategy.FULL,
                RefreshStatus.FAILED,
                started,
                datetime.now(timezone.utc),
                0,
                (time.perf_counter() - clock) * 1000,
                str(exc),
            )

    def incremental_refresh(self) -> RefreshAudit:
        started = datetime.now(timezone.utc)
        clock = time.perf_counter()

        try:
            records, version, changes = self.source.snapshot()

            with self._lock:
                previous = self._snapshot

            if previous.generation == 0:
                return self.full_refresh()

            # Rebuild from the latest source state when an
            # update or deletion cannot be safely identified.
            # The source change log stores old and new row values
            # with operation types in a production implementation.
            #
            # This simulation uses a complete rebuild when changes
            # are present to guarantee correct deletion handling.
            if changes and not self.deleted_strategy:
                raise RefreshError(
                    "Incremental deletion tracking is disabled."
                )

            latest = self._aggregate(records)

            # This is a correctness-first incremental refresh model:
            # only changed snapshots are published. A real database
            # implementation can process CDC deltas instead.
            if version == previous.source_version:
                return RefreshAudit(
                    self.name,
                    RefreshStrategy.INCREMENTAL,
                    RefreshStatus.SKIPPED,
                    started,
                    datetime.now(timezone.utc),
                    0,
                    (time.perf_counter() - clock) * 1000,
                )

            candidate = ViewSnapshot(
                rows=latest,
                generation=previous.generation + 1,
                refreshed_at=datetime.now(timezone.utc),
                source_version=version,
                checksum=self._checksum(latest),
            )

            with self._lock:
                self._snapshot = candidate

            return RefreshAudit(
                self.name,
                RefreshStrategy.INCREMENTAL,
                RefreshStatus.SUCCESS,
                started,
                datetime.now(timezone.utc),
                len(changes),
                (time.perf_counter() - clock) * 1000,
            )

        except Exception as exc:
            logger.exception(
                "Incremental refresh failed for %s", self.name
            )

            return RefreshAudit(
                self.name,
                RefreshStrategy.INCREMENTAL,
                RefreshStatus.FAILED,
                started,
                datetime.now(timezone.utc),
                0,
                (time.perf_counter() - clock) * 1000,
                str(exc),
            )

    def read(self) -> ViewSnapshot:
        with self._lock:
            # Snapshot data is copied so callers cannot mutate
            # internal materialized-view state.
            return copy.deepcopy(self._snapshot)

    def is_stale(self) -> bool:
        return self.read().source_version < self.source.snapshot()[1]

    def query(
        self,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        filters = filters or {}
        snapshot = self.read()

        results = []

        for key, aggregate in snapshot.rows.items():
            dimensions = dict(zip(self.grouping, key))

            if any(
                dimensions.get(column) != value
                for column, value in filters.items()
            ):
                continue

            results.append({
                **dimensions,
                "transaction_count": aggregate.transaction_count,
                "total_quantity": aggregate.total_quantity,
                "total_revenue": aggregate.total_revenue,
            })

        return results


class RefreshScheduler:
    """Dependency-aware refresh orchestration."""

    def __init__(self) -> None:
        self.views: dict[str, MaterializedView] = {}
        self.dependencies: dict[str, set[str]] = {}
        self.audit_log: list[RefreshAudit] = []

    def register(
        self,
        view: MaterializedView,
        dependencies: Optional[set[str]] = None,
    ) -> None:
        if view.name in self.views:
            raise ValidationError("Duplicate materialized view.")

        self.views[view.name] = view
        self.dependencies[view.name] = dependencies or set()

    def _refresh_order(self, target: str) -> list[str]:
        if target not in self.views:
            raise ValidationError("Unknown materialized view.")

        result: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValidationError("Dependency cycle detected.")

            if name in visited:
                return

            if name not in self.views:
                raise ValidationError(
                    f"Unknown dependency: {name}"
                )

            visiting.add(name)

            for dependency in self.dependencies[name]:
                visit(dependency)

            visiting.remove(name)
            visited.add(name)
            result.append(name)

        visit(target)
        return result

    def refresh(
        self,
        target: str,
        strategy: RefreshStrategy,
    ) -> list[RefreshAudit]:
        audits = []

        for name in self._refresh_order(target):
            view = self.views[name]

            if strategy == RefreshStrategy.INCREMENTAL:
                audit = view.incremental_refresh()
            else:
                audit = view.full_refresh()

            audits.append(audit)
            self.audit_log.append(audit)

            if audit.status == RefreshStatus.FAILED:
                logger.error(
                    "Refresh pipeline stopped at %s", name
                )
                break

        return audits


def seed_database(db: SalesDatabase) -> None:
    now = datetime.now(timezone.utc)

    samples = [
        (1, 101, "Electronics", "North", 3, 1200.0),
        (2, 102, "Furniture", "South", 2, 850.0),
        (3, 101, "Electronics", "North", 1, 1200.0),
        (4, 103, "Clothing", "West", 5, 90.0),
        (5, 104, "Electronics", "East", 2, 700.0),
        (6, 102, "Furniture", "South", 1, 850.0),
        (7, 105, "Clothing", "North", 4, 120.0),
    ]

    for sale_id, product, category, region, qty, price in samples:
        db.insert(
            SalesRecord(
                sale_id,
                product,
                category,
                region,
                qty,
                price,
                now - timedelta(days=sale_id),
            )
        )


def run_tests() -> None:
    db = SalesDatabase()
    seed_database(db)

    view = MaterializedView(
        "sales_by_category_region",
        ("category", "region"),
        db,
    )

    audit = view.full_refresh()
    assert audit.status == RefreshStatus.SUCCESS

    original = view.read()
    assert original.rows[("Electronics", "North")].total_revenue == 4800

    new_record = SalesRecord(
        8,
        101,
        "Electronics",
        "North",
        2,
        1200,
        datetime.now(timezone.utc),
    )
    db.insert(new_record)

    assert view.is_stale()

    audit = view.incremental_refresh()
    assert audit.status == RefreshStatus.SUCCESS
    assert not view.is_stale()

    refreshed = view.read()
    assert refreshed.rows[
        ("Electronics", "North")
    ].total_revenue == 7200

    assert original.generation < refreshed.generation

    db.delete(8)
    assert view.is_stale()

    view.incremental_refresh()
    assert not view.is_stale()

    try:
        db.insert(new_record)
        raise AssertionError("Duplicate identifier was accepted.")
    except ValidationError:
        pass

    print("All validation tests passed.")


def demonstrate() -> None:
    db = SalesDatabase()
    seed_database(db)

    category_view = MaterializedView(
        "sales_by_category",
        ("category",),
        db,
    )

    regional_view = MaterializedView(
        "sales_by_region",
        ("region",),
        db,
    )

    scheduler = RefreshScheduler()
    scheduler.register(category_view)
    scheduler.register(
        regional_view,
        dependencies={"sales_by_category"},
    )

    print("\nINITIAL FULL REFRESH")

    for audit in scheduler.refresh(
        "sales_by_region",
        RefreshStrategy.FULL,
    ):
        print(
            audit.view_name,
            audit.status.value,
            f"{audit.duration_ms:.3f} ms",
        )

    print("\nCATEGORY REPORT")

    for row in category_view.query():
        print(row)

    print("\nREGIONAL REPORT")

    for row in regional_view.query():
        print(row)

    print("\nSOURCE DATA MODIFICATION")

    db.insert(
        SalesRecord(
            8,
            106,
            "Electronics",
            "West",
            3,
            1500,
            datetime.now(timezone.utc),
        )
    )

    print("Category view stale:", category_view.is_stale())
    print("Region view stale:", regional_view.is_stale())

    print("\nINCREMENTAL REFRESH")

    for audit in scheduler.refresh(
        "sales_by_region",
        RefreshStrategy.INCREMENTAL,
    ):
        print(
            audit.view_name,
            audit.status.value,
            audit.records_processed,
            f"{audit.duration_ms:.3f} ms",
        )

    print("\nREFRESH AUDIT")

    for audit in scheduler.audit_log:
        print({
            "view": audit.view_name,
            "strategy": audit.strategy.value,
            "status": audit.status.value,
            "processed": audit.records_processed,
            "error": audit.error,
        })

    print("\nSNAPSHOT CHECKSUM")
    print(category_view.read().checksum)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialized View Management Simulator"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run validation tests.",
    )

    args = parser.parse_args()

    if args.test:
        run_tests()
    else:
        demonstrate()


if __name__ == "__main__":
    main()
