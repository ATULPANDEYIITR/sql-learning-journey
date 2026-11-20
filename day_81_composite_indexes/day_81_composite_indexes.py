#!/usr/bin/env python3
"""
Composite Indexes: Multi-column Indexes, Column Ordering, and Selectivity.

Demonstrates:
- Composite B-tree index behavior.
- Leftmost-prefix rules.
- Equality and range predicates.
- Column ordering and selectivity.
- Workload-based index selection.
- Index redundancy detection.
- Query-plan inspection using SQLite.
- Practical index maintenance considerations.

Python 3.10+. Standard library only.
"""

from __future__ import annotations

import sqlite3
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PredicateType(Enum):
    EQUALITY = "equality"
    RANGE = "range"
    ORDERING = "ordering"


@dataclass(frozen=True)
class ColumnStats:
    name: str
    distinct_values: int
    total_rows: int
    nullable: bool = False

    def __post_init__(self):
        if not self.name:
            raise ValueError("Column name cannot be empty.")
        if self.distinct_values < 1:
            raise ValueError("Distinct values must be positive.")
        if self.total_rows < self.distinct_values:
            raise ValueError("Distinct values cannot exceed total rows.")

    @property
    def selectivity(self) -> float:
        """Approximate equality selectivity under uniform distribution."""
        return 1.0 / self.distinct_values


@dataclass(frozen=True)
class Predicate:
    column: str
    kind: PredicateType
    estimated_fraction: Optional[float] = None

    def __post_init__(self):
        if not self.column:
            raise ValueError("Predicate column is required.")

        if self.estimated_fraction is not None:
            if not 0 < self.estimated_fraction <= 1:
                raise ValueError("Estimated fraction must be in (0, 1].")


@dataclass
class IndexCandidate:
    name: str
    columns: tuple[str, ...]

    def __post_init__(self):
        if not self.name or not self.columns:
            raise ValueError("Index name and columns are required.")

        if len(set(self.columns)) != len(self.columns):
            raise ValueError("An index cannot repeat columns.")


@dataclass
class Query:
    name: str
    predicates: list[Predicate]
    ordering: tuple[str, ...] = ()


class CompositeIndexAdvisor:
    def __init__(self, statistics: list[ColumnStats]):
        self.statistics = {item.name: item for item in statistics}

    def validate_columns(self, columns: tuple[str, ...]):
        unknown = set(columns) - self.statistics.keys()

        if unknown:
            raise ValueError(f"Unknown columns: {sorted(unknown)}")

    def leftmost_prefix_match(
        self,
        index: IndexCandidate,
        query: Query
    ) -> int:
        """
        Count consecutive index columns usable from the left.

        A range condition normally terminates further B-tree
        search-key matching, although later columns can still
        contribute to filtering or index-only access.
        """
        equality_columns = {
            predicate.column
            for predicate in query.predicates
            if predicate.kind == PredicateType.EQUALITY
        }

        range_columns = {
            predicate.column
            for predicate in query.predicates
            if predicate.kind == PredicateType.RANGE
        }

        matched = 0

        for column in index.columns:
            if column in equality_columns:
                matched += 1
            elif column in range_columns:
                matched += 1
                break
            else:
                break

        return matched

    def estimate_selectivity(
        self,
        query: Query
    ) -> float:
        """
        Estimate result fraction using an independence assumption.

        Correlated columns can make this estimate inaccurate.
        """
        fraction = 1.0

        for predicate in query.predicates:
            stats = self.statistics.get(predicate.column)

            if stats is None:
                raise ValueError(
                    f"Missing statistics for {predicate.column}"
                )

            if predicate.kind == PredicateType.EQUALITY:
                fraction *= stats.selectivity

            elif predicate.kind == PredicateType.RANGE:
                fraction *= (
                    predicate.estimated_fraction
                    if predicate.estimated_fraction is not None
                    else 0.25
                )

        return max(fraction, 1.0 / max(
            item.total_rows for item in self.statistics.values()
        ))

    def evaluate(
        self,
        index: IndexCandidate,
        query: Query
    ) -> dict:
        self.validate_columns(index.columns)

        matched = self.leftmost_prefix_match(index, query)
        selectivity = self.estimate_selectivity(query)

        ordering_covered = (
            bool(query.ordering)
            and index.columns[:len(query.ordering)] == query.ordering
        )

        return {
            "index": index.name,
            "query": query.name,
            "matched_prefix_columns": matched,
            "total_index_columns": len(index.columns),
            "estimated_result_fraction": round(selectivity, 6),
            "estimated_result_percentage": round(
                selectivity * 100, 4
            ),
            "ordering_prefix_covered": ordering_covered,
            "usable_for_search": matched > 0,
        }

    def recommend(
        self,
        query: Query,
        candidates: list[IndexCandidate]
    ) -> list[dict]:
        evaluations = [
            self.evaluate(index, query)
            for index in candidates
        ]

        return sorted(
            evaluations,
            key=lambda result: (
                result["matched_prefix_columns"],
                result["ordering_prefix_covered"]
            ),
            reverse=True
        )

    def suggest_column_order(
        self,
        equality_columns: list[str],
        range_columns: list[str],
        ordering_columns: list[str]
    ) -> tuple[str, ...]:
        """
        Equality columns precede range columns.

        Among equality columns, higher cardinality is a useful
        starting heuristic, not a universal ordering rule.
        """
        for column in (
            equality_columns + range_columns + ordering_columns
        ):
            self.validate_columns((column,))

        equality = sorted(
            set(equality_columns),
            key=lambda column: (
                self.statistics[column].distinct_values
            ),
            reverse=True
        )

        result = list(equality)

        for column in range_columns + ordering_columns:
            if column not in result:
                result.append(column)

        return tuple(result)

    @staticmethod
    def is_redundant(
        candidate: IndexCandidate,
        existing: list[IndexCandidate]
    ) -> bool:
        """Detect an exact leftmost-prefix duplicate."""
        return any(
            len(index.columns) >= len(candidate.columns)
            and index.columns[:len(candidate.columns)]
            == candidate.columns
            for index in existing
            if index.name != candidate.name
        )


class OrderDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.create_schema()

    def create_schema(self):
        self.connection.executescript("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                region TEXT NOT NULL,
                total_amount REAL NOT NULL CHECK(total_amount >= 0),
                created_at INTEGER NOT NULL
            );

            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                customer_name TEXT NOT NULL
            );

            CREATE INDEX idx_orders_customer_status_created
            ON orders(customer_id, status, created_at DESC);

            CREATE INDEX idx_orders_status_created
            ON orders(status, created_at DESC);

            CREATE INDEX idx_orders_region_amount
            ON orders(region, total_amount);
        """)

    def seed(self, count: int = 10000):
        if count < 1 or count > 1_000_000:
            raise ValueError("Record count must be between 1 and 1,000,000.")

        random.seed(42)

        statuses = ["PENDING", "PAID", "SHIPPED", "CANCELLED"]
        regions = ["NORTH", "SOUTH", "EAST", "WEST"]

        with self.connection:
            self.connection.executemany(
                """
                INSERT INTO customers(customer_id, customer_name)
                VALUES (?, ?)
                """,
                [
                    (i, f"Customer {i}")
                    for i in range(1, 1001)
                ]
            )

            batch = []

            for order_id in range(1, count + 1):
                batch.append((
                    order_id,
                    random.randint(1, 1000),
                    random.choices(
                        statuses,
                        weights=[15, 45, 30, 10]
                    )[0],
                    random.choice(regions),
                    round(random.uniform(10, 5000), 2),
                    1700000000 + random.randint(0, 10000000)
                ))

                if len(batch) >= 1000:
                    self.connection.executemany(
                        """
                        INSERT INTO orders
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        batch
                    )
                    batch.clear()

            if batch:
                self.connection.executemany(
                    "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
                    batch
                )

        self.connection.execute("ANALYZE")

    def explain(self, sql: str, parameters: tuple = ()):
        if not sql.lstrip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are permitted.")

        plan = self.connection.execute(
            "EXPLAIN QUERY PLAN " + sql,
            parameters
        ).fetchall()

        return [dict(row) for row in plan]

    def query(self, sql: str, parameters: tuple = ()):
        if not sql.lstrip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are permitted.")

        return [
            dict(row)
            for row in self.connection.execute(sql, parameters)
        ]

    def close(self):
        self.connection.close()


def demonstrate():
    statistics = [
        ColumnStats("customer_id", 1000, 10000),
        ColumnStats("status", 4, 10000),
        ColumnStats("region", 4, 10000),
        ColumnStats("created_at", 9000, 10000),
        ColumnStats("total_amount", 8000, 10000),
    ]

    advisor = CompositeIndexAdvisor(statistics)

    indexes = [
        IndexCandidate(
            "idx_customer_status_created",
            ("customer_id", "status", "created_at")
        ),
        IndexCandidate(
            "idx_status_customer_created",
            ("status", "customer_id", "created_at")
        ),
        IndexCandidate(
            "idx_region_amount",
            ("region", "total_amount")
        ),
    ]

    queries = [
        Query(
            "Customer order history",
            [
                Predicate("customer_id", PredicateType.EQUALITY),
                Predicate("status", PredicateType.EQUALITY),
                Predicate(
                    "created_at",
                    PredicateType.RANGE,
                    0.20
                )
            ]
        ),
        Query(
            "Recent paid orders",
            [
                Predicate("status", PredicateType.EQUALITY),
                Predicate(
                    "created_at",
                    PredicateType.RANGE,
                    0.10
                )
            ],
            ordering=("status", "created_at")
        ),
        Query(
            "Regional sales",
            [
                Predicate("region", PredicateType.EQUALITY),
                Predicate("total_amount", PredicateType.RANGE, 0.15)
            ]
        )
    ]

    print("\nCOMPOSITE INDEX EVALUATION")
    print("=" * 65)

    for query in queries:
        print(f"\nQuery: {query.name}")

        for result in advisor.recommend(query, indexes):
            print(result)

    suggested = advisor.suggest_column_order(
        ["status", "customer_id"],
        ["created_at"],
        []
    )

    print("\nSuggested index ordering:")
    print(suggested)

    print("\nREDUNDANCY CHECK")
    candidate = IndexCandidate(
        "idx_customer_only",
        ("customer_id",)
    )

    print(
        "Customer-only index redundant:",
        advisor.is_redundant(candidate, indexes)
    )

    database = OrderDatabase()

    try:
        database.seed(10000)

        examples = [
            (
                "Composite equality lookup",
                """
                SELECT order_id, created_at
                FROM orders
                WHERE customer_id = ?
                  AND status = ?
                """,
                (42, "PAID")
            ),
            (
                "Composite range lookup",
                """
                SELECT order_id, created_at
                FROM orders
                WHERE customer_id = ?
                  AND status = ?
                  AND created_at >= ?
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (42, "PAID", 1700000000)
            ),
            (
                "Leftmost prefix lookup",
                """
                SELECT order_id
                FROM orders
                WHERE customer_id = ?
                """,
                (42,)
            ),
            (
                "Non-leftmost lookup",
                """
                SELECT order_id
                FROM orders
                WHERE created_at >= ?
                """,
                (1700000000,)
            ),
            (
                "Alternative index lookup",
                """
                SELECT order_id
                FROM orders
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT 20
                """,
                ("PAID",)
            )
        ]

        print("\nSQL QUERY PLAN INSPECTION")
        print("=" * 65)

        for name, sql, parameters in examples:
            print(f"\n{name}")
            for step in database.explain(sql, parameters):
                print(step["detail"])

        results = database.query(
            """
            SELECT region,
                   COUNT(*) AS order_count,
                   ROUND(AVG(total_amount), 2) AS average_amount
            FROM orders
            GROUP BY region
            ORDER BY order_count DESC
            """
        )

        print("\nREGIONAL AGGREGATION")

        for row in results:
            print(row)

    finally:
        database.close()


if __name__ == "__main__":
    demonstrate()
