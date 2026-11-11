#!/usr/bin/env python3
"""
Temporary Tables: TEMP tables, session scope, and staging workflows.

Demonstrates:
- Session-scoped temporary tables using SQLite.
- Staging and validation of incoming records.
- Duplicate detection and rejection handling.
- Transactional promotion into permanent tables.
- Savepoints, rollback, indexes, cleanup, and session isolation.
- CSV ingestion and reproducible reporting.

Run: python temporary_tables.py
"""

from __future__ import annotations

import csv
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class RecordStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class IncomingRecord:
    external_id: str
    product: str
    quantity: int
    unit_price: float


@dataclass
class ValidationResult:
    external_id: str
    status: RecordStatus
    reason: str


class StagingError(Exception):
    """Raised when a staging workflow cannot safely continue."""


class TemporaryTablePipeline:
    """
    Each SQLite connection represents an independent database session.

    SQLite TEMP tables belong to the connection that creates them.
    Closing the connection destroys its temporary tables.
    """

    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.closed = False
        self.create_permanent_tables()
        self.create_temporary_tables()

    def ensure_open(self) -> None:
        if self.closed:
            raise StagingError("Database session is closed")

    def create_permanent_tables(self) -> None:
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                external_id TEXT PRIMARY KEY,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_price REAL NOT NULL CHECK(unit_price >= 0),
                total_value REAL NOT NULL,
                imported_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS import_audit (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                reason TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_products_product
                ON products(product);
        """)

    def create_temporary_tables(self) -> None:
        self.ensure_open()

        self.connection.executescript("""
            CREATE TEMP TABLE IF NOT EXISTS staging_products (
                external_id TEXT NOT NULL,
                product TEXT NOT NULL,
                quantity INTEGER,
                unit_price REAL,
                loaded_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_staging_external_id
                ON staging_products(external_id);

            CREATE TEMP TABLE IF NOT EXISTS staging_validation (
                external_id TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT NOT NULL
            );
        """)

    @staticmethod
    def timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def clear_staging(self) -> None:
        """Reuse temporary tables without dropping their definitions."""
        self.ensure_open()
        self.connection.execute("DELETE FROM staging_products")
        self.connection.execute("DELETE FROM staging_validation")

    def load_records(self, records: list[IncomingRecord]) -> int:
        self.ensure_open()

        if not records:
            raise StagingError("Input batch cannot be empty")

        if len(records) > 100_000:
            raise StagingError("Batch exceeds the configured limit")

        rows = []

        for record in records:
            if not isinstance(record, IncomingRecord):
                raise StagingError("Invalid record type")

            rows.append((
                record.external_id,
                record.product,
                record.quantity,
                record.unit_price,
                self.timestamp()
            ))

        self.connection.executemany("""
            INSERT INTO staging_products
                (external_id, product, quantity, unit_price, loaded_at)
            VALUES (?, ?, ?, ?, ?)
        """, rows)

        return len(rows)

    def load_csv(self, path: str) -> int:
        """Load a CSV file using explicit field names and parameterized SQL."""
        records = []

        with Path(path).open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file)

            required = {
                "external_id", "product", "quantity", "unit_price"
            }

            if not required.issubset(reader.fieldnames or []):
                raise StagingError("CSV is missing required columns")

            for row in reader:
                try:
                    records.append(IncomingRecord(
                        external_id=row["external_id"].strip(),
                        product=row["product"].strip(),
                        quantity=int(row["quantity"]),
                        unit_price=float(row["unit_price"])
                    ))
                except (ValueError, TypeError, KeyError) as exc:
                    raise StagingError(
                        f"Invalid CSV record at line {reader.line_num}"
                    ) from exc

        return self.load_records(records)

    def validate_records(self) -> list[ValidationResult]:
        self.ensure_open()

        self.connection.execute("DELETE FROM staging_validation")

        rows = self.connection.execute("""
            SELECT external_id, product, quantity, unit_price
            FROM staging_products
            ORDER BY rowid
        """).fetchall()

        seen: set[str] = set()
        results = []

        existing_ids = {
            row["external_id"]
            for row in self.connection.execute(
                "SELECT external_id FROM products"
            )
        }

        for row in rows:
            external_id = row["external_id"]
            reason = "Valid record"

            if not external_id or not external_id.strip():
                reason = "Missing external identifier"
            elif not row["product"] or not row["product"].strip():
                reason = "Missing product name"
            elif external_id in seen:
                reason = "Duplicate identifier in staging batch"
            elif external_id in existing_ids:
                reason = "Identifier already exists in permanent table"
            elif row["quantity"] is None or row["quantity"] <= 0:
                reason = "Quantity must be positive"
            elif row["unit_price"] is None or row["unit_price"] < 0:
                reason = "Unit price cannot be negative"

            status = (
                RecordStatus.ACCEPTED
                if reason == "Valid record"
                else RecordStatus.REJECTED
            )

            seen.add(external_id)

            result = ValidationResult(
                external_id, status, reason
            )
            results.append(result)

            self.connection.execute("""
                INSERT INTO staging_validation
                    (external_id, status, reason)
                VALUES (?, ?, ?)
            """, (external_id, status.value, reason))

        return results

    def promote_records(self) -> int:
        """
        Atomically promote valid records.

        A savepoint permits rollback of promotion without destroying
        the loaded staging batch.
        """
        self.ensure_open()

        self.connection.execute("SAVEPOINT promotion")

        try:
            cursor = self.connection.execute("""
                INSERT INTO products (
                    external_id,
                    product,
                    quantity,
                    unit_price,
                    total_value,
                    imported_at
                )
                SELECT
                    s.external_id,
                    s.product,
                    s.quantity,
                    s.unit_price,
                    s.quantity * s.unit_price,
                    ?
                FROM staging_products AS s
                JOIN staging_validation AS v
                    ON v.external_id = s.external_id
                WHERE v.status = 'ACCEPTED'
            """, (self.timestamp(),))

            inserted = cursor.rowcount

            self.connection.execute("""
                INSERT INTO import_audit (
                    external_id, outcome, reason, recorded_at
                )
                SELECT
                    external_id, status, reason, ?
                FROM staging_validation
            """, (self.timestamp(),))

            self.connection.execute("RELEASE SAVEPOINT promotion")
            self.connection.commit()

            return inserted

        except sqlite3.Error as exc:
            self.connection.execute("ROLLBACK TO SAVEPOINT promotion")
            self.connection.execute("RELEASE SAVEPOINT promotion")
            self.connection.rollback()
            raise StagingError("Promotion failed") from exc

    def report(self) -> dict[str, Any]:
        self.ensure_open()

        permanent = self.connection.execute("""
            SELECT
                COUNT(*) AS record_count,
                COALESCE(SUM(total_value), 0) AS inventory_value
            FROM products
        """).fetchone()

        validation = self.connection.execute("""
            SELECT status, COUNT(*) AS total
            FROM staging_validation
            GROUP BY status
        """).fetchall()

        return {
            "permanent_records": permanent["record_count"],
            "inventory_value": round(
                permanent["inventory_value"], 2
            ),
            "validation": {
                row["status"]: row["total"]
                for row in validation
            }
        }

    def get_staged_records(self) -> list[dict[str, Any]]:
        self.ensure_open()

        rows = self.connection.execute("""
            SELECT
                s.external_id,
                s.product,
                s.quantity,
                s.unit_price,
                v.status,
                v.reason
            FROM staging_products s
            LEFT JOIN staging_validation v
                ON v.external_id = s.external_id
            ORDER BY s.rowid
        """).fetchall()

        return [dict(row) for row in rows]

    def close(self) -> None:
        if not self.closed:
            self.connection.close()
            self.closed = True

    def __enter__(self) -> TemporaryTablePipeline:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def demonstrate_session_isolation() -> None:
    first = sqlite3.connect(":memory:")
    second = sqlite3.connect(":memory:")

    try:
        first.execute("""
            CREATE TEMP TABLE session_data (value TEXT)
        """)
        first.execute("""
            INSERT INTO session_data VALUES ('Session A')
        """)

        try:
            second.execute("SELECT * FROM session_data")
            raise AssertionError("Session isolation was not enforced")
        except sqlite3.OperationalError:
            print("Session isolation: verified")

    finally:
        first.close()
        second.close()


def main() -> None:
    records = [
        IncomingRecord("P1001", "Laptop", 5, 75000.00),
        IncomingRecord("P1002", "Monitor", 10, 12000.00),
        IncomingRecord("P1003", "Keyboard", 20, 1500.00),
        IncomingRecord("P1001", "Duplicate Laptop", 2, 70000.00),
        IncomingRecord("P1004", "Invalid Quantity", 0, 500.00),
        IncomingRecord("P1005", "Invalid Price", 4, -100.00),
    ]

    with TemporaryTablePipeline() as pipeline:
        print("\nLoading records")
        print("Loaded:", pipeline.load_records(records))

        print("\nValidation results")
        results = pipeline.validate_records()

        for result in results:
            print(
                result.external_id,
                result.status.value,
                result.reason
            )

        print("\nStaging records")
        for record in pipeline.get_staged_records():
            print(record)

        print("\nPromotion")
        print("Inserted:", pipeline.promote_records())

        print("\nFinal report")
        print(pipeline.report())

        assert pipeline.report()["permanent_records"] == 3
        assert pipeline.report()["validation"]["REJECTED"] == 3

        # A new staging batch can reuse the existing TEMP tables.
        pipeline.clear_staging()
        pipeline.load_records([
            IncomingRecord("P1006", "Mouse", 15, 800.00)
        ])

        pipeline.validate_records()
        assert pipeline.promote_records() == 1

        print("\nSecond batch")
        print(pipeline.report())

    demonstrate_session_isolation()

    print("\nTemporary table session closed successfully.")


if __name__ == "__main__":
    main()
