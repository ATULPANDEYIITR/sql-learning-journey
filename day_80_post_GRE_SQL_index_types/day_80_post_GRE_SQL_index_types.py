#!/usr/bin/env python3
"""
PostgreSQL Index Types: B-tree, Hash, GiST, SP-GiST, GIN, and BRIN.

A self-contained index selection and workload simulation.
Python 3.10+; standard library only.

The program models index capabilities, evaluates query workloads,
estimates index suitability, generates PostgreSQL DDL, and validates
index-selection decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable
import json
import logging
import math
import time


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("postgres_index_lab")


class IndexType(Enum):
    BTREE = "B-tree"
    HASH = "Hash"
    GIST = "GiST"
    SPGIST = "SP-GiST"
    GIN = "GIN"
    BRIN = "BRIN"


class AccessPattern(Enum):
    EQUALITY = "equality"
    RANGE = "range"
    ORDERING = "ordering"
    MULTIPLE_VALUES = "multiple_values"
    CONTAINS = "contains"
    SPATIAL = "spatial"
    PREFIX = "prefix"
    FULL_TEXT = "full_text"
    LARGE_TABLE_RANGE = "large_table_range"


@dataclass(frozen=True)
class IndexCapability:
    index_type: IndexType
    patterns: frozenset[AccessPattern]
    description: str
    strengths: tuple[str, ...]
    limitations: tuple[str, ...]


CAPABILITIES = {
    IndexType.BTREE: IndexCapability(
        IndexType.BTREE,
        frozenset({
            AccessPattern.EQUALITY,
            AccessPattern.RANGE,
            AccessPattern.ORDERING,
            AccessPattern.PREFIX,
        }),
        "Balanced search tree with ordered keys.",
        ("Equality", "Range", "Sorting", "Uniqueness"),
        ("Large indexes for some workloads", "Not an inverted index"),
    ),
    IndexType.HASH: IndexCapability(
        IndexType.HASH,
        frozenset({AccessPattern.EQUALITY}),
        "Hash-based index for equality comparisons.",
        ("Equality lookups",),
        ("No range scans", "No ordering", "No uniqueness enforcement"),
    ),
    IndexType.GIST: IndexCapability(
        IndexType.GIST,
        frozenset({
            AccessPattern.SPATIAL,
            AccessPattern.RANGE,
            AccessPattern.CONTAINS,
        }),
        "Generalized Search Tree supporting extensible operator classes.",
        ("Spatial searches", "Range operations", "Overlap queries"),
        ("Performance depends on operator class and data distribution"),
    ),
    IndexType.SPGIST: IndexCapability(
        IndexType.SPGIST,
        frozenset({
            AccessPattern.SPATIAL,
            AccessPattern.PREFIX,
            AccessPattern.EQUALITY,
        }),
        "Space-partitioned search tree.",
        ("Radix-tree searches", "Partitioned search spaces"),
        ("Supported operations depend on operator class"),
    ),
    IndexType.GIN: IndexCapability(
        IndexType.GIN,
        frozenset({
            AccessPattern.MULTIPLE_VALUES,
            AccessPattern.CONTAINS,
            AccessPattern.FULL_TEXT,
        }),
        "Inverted index mapping component values to rows.",
        ("Arrays", "JSONB containment", "Full-text search"),
        ("Expensive updates", "No general ordering", "Potentially large indexes"),
    ),
    IndexType.BRIN: IndexCapability(
        IndexType.BRIN,
        frozenset({
            AccessPattern.LARGE_TABLE_RANGE,
            AccessPattern.RANGE,
        }),
        "Block Range Index storing summaries of physical page ranges.",
        ("Very small indexes", "Large naturally ordered tables"),
        ("Lossy page-range filtering", "Depends on physical correlation"),
    ),
}


@dataclass(frozen=True)
class QueryWorkload:
    name: str
    pattern: AccessPattern
    table_rows: int
    selectivity: float
    update_frequency: float = 0.0
    physical_correlation: float = 0.0
    ordered_output: bool = False
    description: str = ""

    def __post_init__(self):
        if self.table_rows <= 0:
            raise ValueError("table_rows must be positive")
        if not 0 <= self.selectivity <= 1:
            raise ValueError("selectivity must be between 0 and 1")
        if not 0 <= self.update_frequency <= 1:
            raise ValueError("update_frequency must be between 0 and 1")
        if not 0 <= self.physical_correlation <= 1:
            raise ValueError("physical_correlation must be between 0 and 1")


@dataclass
class IndexRecommendation:
    index_type: IndexType
    score: float
    applicable: bool
    reasons: list[str] = field(default_factory=list)


class IndexAdvisor:
    """Ranks index types using workload characteristics.

    Scores are educational heuristics, not PostgreSQL planner estimates.
    """

    def evaluate(
        self,
        workload: QueryWorkload
    ) -> list[IndexRecommendation]:

        results = []

        for index_type, capability in CAPABILITIES.items():
            applicable = workload.pattern in capability.patterns
            reasons = []
            score = 0.0

            if not applicable:
                results.append(
                    IndexRecommendation(
                        index_type, 0.0, False,
                        ["The access pattern is not supported by this index type."]
                    )
                )
                continue

            score += 50
            reasons.append("The index supports the requested access pattern.")

            if index_type == IndexType.BTREE:
                score += 15

                if workload.ordered_output:
                    score += 20
                    reasons.append("B-tree can provide ordered output.")

                if workload.selectivity < 0.05:
                    score += 10
                    reasons.append("Selective lookup may reduce heap access.")

            elif index_type == IndexType.HASH:
                score += 12

                if workload.pattern != AccessPattern.EQUALITY:
                    score = 0
                    applicable = False

            elif index_type == IndexType.GIST:
                score += 20
                reasons.append(
                    "GiST supports specialized operator classes."
                )

            elif index_type == IndexType.SPGIST:
                score += 20
                reasons.append(
                    "SP-GiST can partition suitable search spaces."
                )

            elif index_type == IndexType.GIN:
                score += 25
                reasons.append(
                    "GIN supports component-level inverted lookups."
                )

                if workload.update_frequency > 0.5:
                    score -= 20
                    reasons.append(
                        "Frequent updates increase GIN maintenance cost."
                    )

            elif index_type == IndexType.BRIN:
                score += 15

                score += workload.physical_correlation * 30

                if workload.table_rows >= 1_000_000:
                    score += 15
                    reasons.append(
                        "Large table size favors compact block summaries."
                    )

                if workload.physical_correlation < 0.4:
                    score -= 30
                    reasons.append(
                        "Low physical correlation weakens BRIN effectiveness."
                    )

            score -= workload.update_frequency * 15

            results.append(
                IndexRecommendation(
                    index_type,
                    max(0.0, min(score, 100.0)),
                    applicable,
                    reasons
                )
            )

        return sorted(
            results,
            key=lambda item: item.score,
            reverse=True
        )


@dataclass(frozen=True)
class IndexDefinition:
    table: str
    column: str
    index_name: str
    index_type: IndexType
    unique: bool = False
    operator_class: str | None = None
    partial_condition: str | None = None

    def validate(self):
        import re

        identifier = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

        for value in (self.table, self.column, self.index_name):
            if not identifier.fullmatch(value):
                raise ValueError(f"Invalid SQL identifier: {value}")

        if self.unique and self.index_type != IndexType.BTREE:
            raise ValueError(
                "This educational catalog permits unique B-tree indexes only."
            )

        if self.index_type == IndexType.HASH and self.unique:
            raise ValueError("PostgreSQL hash indexes cannot be unique.")

        if self.partial_condition:
            if ";" in self.partial_condition:
                raise ValueError("Unsafe partial index condition.")
            if "--" in self.partial_condition:
                raise ValueError("Comments are not allowed in conditions.")

    def to_sql(self) -> str:
        self.validate()

        unique = "UNIQUE " if self.unique else ""
        operator = (
            f" {self.operator_class}"
            if self.operator_class
            else ""
        )
        condition = (
            f" WHERE {self.partial_condition}"
            if self.partial_condition
            else ""
        )

        return (
            f"CREATE {unique}INDEX {self.index_name} "
            f"ON {self.table} USING {self.index_type.name} "
            f"({self.column}{operator}){condition};"
        )


class IndexCatalog:
    def __init__(self):
        self._indexes: dict[str, IndexDefinition] = {}

    def add(self, definition: IndexDefinition):
        definition.validate()

        if definition.index_name in self._indexes:
            raise ValueError("Index name already exists.")

        self._indexes[definition.index_name] = definition

    def remove(self, index_name: str):
        if index_name not in self._indexes:
            raise KeyError(index_name)

        del self._indexes[index_name]

    def list_indexes(self) -> list[IndexDefinition]:
        return sorted(
            self._indexes.values(),
            key=lambda index: index.index_name
        )

    def export_sql(self) -> str:
        return "\n".join(
            index.to_sql()
            for index in self.list_indexes()
        )


def create_workloads() -> list[QueryWorkload]:
    return [
        QueryWorkload(
            "Customer lookup",
            AccessPattern.EQUALITY,
            500_000,
            0.001,
            0.05,
            description="Find a customer by customer_id."
        ),
        QueryWorkload(
            "Order date filtering",
            AccessPattern.RANGE,
            5_000_000,
            0.02,
            0.10,
            0.95,
            description="Retrieve orders within a date interval."
        ),
        QueryWorkload(
            "JSONB containment",
            AccessPattern.CONTAINS,
            1_000_000,
            0.01,
            0.60,
            description="Search document attributes."
        ),
        QueryWorkload(
            "Array membership",
            AccessPattern.MULTIPLE_VALUES,
            800_000,
            0.05,
            0.20,
            description="Find records containing a tag."
        ),
        QueryWorkload(
            "Spatial overlap",
            AccessPattern.SPATIAL,
            300_000,
            0.01,
            0.05,
            description="Find intersecting geographical objects."
        ),
        QueryWorkload(
            "Full-text search",
            AccessPattern.FULL_TEXT,
            2_000_000,
            0.005,
            0.10,
            description="Search document text."
        ),
    ]


def demonstrate_advisor():
    advisor = IndexAdvisor()

    print("\nINDEX ADVISOR")
    print("=" * 75)

    for workload in create_workloads():
        print(f"\nWorkload: {workload.name}")
        print(f"Pattern: {workload.pattern.value}")

        recommendations = advisor.evaluate(workload)

        for recommendation in recommendations[:3]:
            if recommendation.applicable:
                print(
                    f"  {recommendation.index_type.value:10} "
                    f"Score={recommendation.score:5.1f}"
                )

                for reason in recommendation.reasons:
                    print(f"      - {reason}")


def demonstrate_catalog():
    catalog = IndexCatalog()

    definitions = [
        IndexDefinition(
            "customers", "email",
            "idx_customers_email",
            IndexType.BTREE,
            unique=True
        ),
        IndexDefinition(
            "events", "payload",
            "idx_events_payload",
            IndexType.GIN,
            operator_class="jsonb_path_ops"
        ),
        IndexDefinition(
            "orders", "created_at",
            "idx_orders_created_at",
            IndexType.BRIN
        ),
        IndexDefinition(
            "documents", "search_vector",
            "idx_documents_search",
            IndexType.GIN
        ),
        IndexDefinition(
            "network_logs", "client_ip",
            "idx_network_client_ip",
            IndexType.SPGIST
        ),
    ]

    for definition in definitions:
        catalog.add(definition)

    print("\nGENERATED POSTGRESQL DDL")
    print("=" * 75)
    print(catalog.export_sql())


def demonstrate_edge_cases():
    print("\nVALIDATION TESTS")
    print("=" * 75)

    tests: list[tuple[str, Callable[[], object]]] = [
        (
            "Invalid selectivity",
            lambda: QueryWorkload(
                "Invalid", AccessPattern.EQUALITY, 100, 1.5
            )
        ),
        (
            "Invalid identifier",
            lambda: IndexDefinition(
                "users;DROP TABLE users",
                "email",
                "idx_users",
                IndexType.BTREE
            ).to_sql()
        ),
        (
            "Unsupported unique hash index",
            lambda: IndexDefinition(
                "users", "email", "idx_hash",
                IndexType.HASH, unique=True
            ).to_sql()
        ),
    ]

    for name, operation in tests:
        try:
            operation()
            print(f"FAILED: {name}")
        except (ValueError, TypeError) as error:
            print(f"PASS: {name}: {error}")


def benchmark_simulation():
    """Demonstrate scalable in-memory catalog operations."""

    catalog = IndexCatalog()
    start = time.perf_counter()

    for number in range(1000):
        catalog.add(
            IndexDefinition(
                "events",
                "event_id",
                f"idx_event_{number}",
                IndexType.BTREE
            )
        )

    elapsed = time.perf_counter() - start

    print("\nCATALOG PERFORMANCE")
    print(f"Indexes created: {len(catalog.list_indexes())}")
    print(f"Elapsed seconds: {elapsed:.6f}")


def run_tests():
    advisor = IndexAdvisor()

    equality = QueryWorkload(
        "Equality",
        AccessPattern.EQUALITY,
        100_000,
        0.01
    )

    ranked = advisor.evaluate(equality)

    assert ranked[0].index_type == IndexType.BTREE
    assert any(
        item.index_type == IndexType.HASH and item.applicable
        for item in ranked
    )

    full_text = QueryWorkload(
        "Text",
        AccessPattern.FULL_TEXT,
        100_000,
        0.01
    )

    ranked = advisor.evaluate(full_text)

    assert ranked[0].index_type == IndexType.GIN

    high_correlation = QueryWorkload(
        "Ordered data",
        AccessPattern.LARGE_TABLE_RANGE,
        10_000_000,
        0.10,
        physical_correlation=0.99
    )

    ranked = advisor.evaluate(high_correlation)

    assert ranked[0].index_type == IndexType.BRIN

    print("\nAll assertions passed.")


def main():
    print("POSTGRESQL INDEX TYPES LABORATORY")
    print("=" * 75)

    for index_type, capability in CAPABILITIES.items():
        print(f"\n{index_type.value}")
        print(f"  {capability.description}")
        print(f"  Strengths: {', '.join(capability.strengths)}")
        print(f"  Limitations: {', '.join(capability.limitations)}")

    demonstrate_advisor()
    demonstrate_catalog()
    demonstrate_edge_cases()
    benchmark_simulation()
    run_tests()

    print("\nExecution completed successfully.")


if __name__ == "__main__":
    main()
