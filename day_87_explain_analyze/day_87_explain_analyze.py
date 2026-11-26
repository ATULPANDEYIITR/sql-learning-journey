#!/usr/bin/env python3
"""
EXPLAIN ANALYZE: PostgreSQL Execution Plan Analysis and Verification

Demonstrates:
- Actual execution time versus estimated cost
- Actual rows versus estimated rows
- Loop interpretation
- Sequential scans, index scans, and nested loops
- Planning Time and Execution Time
- Buffer statistics
- Cardinality estimation errors
- Plan verification and performance regression detection
- JSON EXPLAIN plan parsing

Run:
    python explain_analyze.py

No external dependencies required.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PlanError(Exception):
    """Raised when an execution plan is invalid."""


class Severity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class PlanMetrics:
    node_type: str
    relation: Optional[str]
    estimated_rows: float
    actual_rows: float
    loops: int
    startup_cost: float
    total_cost: float
    startup_time_ms: float
    total_time_ms: float
    shared_hit_blocks: int = 0
    shared_read_blocks: int = 0
    children: list["PlanMetrics"] = field(default_factory=list)

    @property
    def total_actual_rows(self) -> float:
        return self.actual_rows * self.loops

    @property
    def total_node_time_ms(self) -> float:
        return self.total_time_ms * self.loops

    @property
    def row_estimation_ratio(self) -> float:
        if self.estimated_rows <= 0:
            return math.inf if self.actual_rows > 0 else 1.0
        return self.actual_rows / self.estimated_rows

    @property
    def estimation_error(self) -> float:
        if self.estimated_rows == 0:
            return 0.0 if self.actual_rows == 0 else math.inf
        return abs(self.actual_rows - self.estimated_rows) / self.estimated_rows

    @property
    def buffer_accesses(self) -> int:
        return self.shared_hit_blocks + self.shared_read_blocks


@dataclass
class ExecutionReport:
    planning_time_ms: float
    execution_time_ms: float
    root: PlanMetrics
    settings: dict[str, Any] = field(default_factory=dict)


class PlanParser:
    """Converts PostgreSQL JSON EXPLAIN output into typed metrics."""

    @staticmethod
    def _number(value: Any, field_name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PlanError(f"Invalid numeric field: {field_name}")
        result = float(value)
        if not math.isfinite(result) or result < 0:
            raise PlanError(f"Invalid value for {field_name}: {value}")
        return result

    @classmethod
    def parse_node(cls, node: dict[str, Any]) -> PlanMetrics:
        if not isinstance(node, dict):
            raise PlanError("Plan node must be an object")

        node_type = node.get("Node Type")
        if not isinstance(node_type, str) or not node_type:
            raise PlanError("Missing Node Type")

        loops_value = node.get("Actual Loops", 0)
        if isinstance(loops_value, bool) or not isinstance(loops_value, int):
            raise PlanError("Actual Loops must be an integer")
        if loops_value < 0:
            raise PlanError("Actual Loops cannot be negative")

        children_data = node.get("Plans", [])
        if not isinstance(children_data, list):
            raise PlanError("Plans must be an array")

        children = [cls.parse_node(child) for child in children_data]

        return PlanMetrics(
            node_type=node_type,
            relation=node.get("Relation Name"),
            estimated_rows=cls._number(
                node.get("Plan Rows", 0), "Plan Rows"
            ),
            actual_rows=cls._number(
                node.get("Actual Rows", 0), "Actual Rows"
            ),
            loops=loops_value,
            startup_cost=cls._number(
                node.get("Startup Cost", 0), "Startup Cost"
            ),
            total_cost=cls._number(
                node.get("Total Cost", 0), "Total Cost"
            ),
            startup_time_ms=cls._number(
                node.get("Actual Startup Time", 0),
                "Actual Startup Time"
            ),
            total_time_ms=cls._number(
                node.get("Actual Total Time", 0),
                "Actual Total Time"
            ),
            shared_hit_blocks=int(
                cls._number(
                    node.get("Shared Hit Blocks", 0),
                    "Shared Hit Blocks"
                )
            ),
            shared_read_blocks=int(
                cls._number(
                    node.get("Shared Read Blocks", 0),
                    "Shared Read Blocks"
                )
            ),
            children=children,
        )

    @classmethod
    def parse(cls, document: str) -> ExecutionReport:
        try:
            data = json.loads(document)
        except json.JSONDecodeError as exc:
            raise PlanError(f"Invalid JSON: {exc}") from exc

        if not isinstance(data, list) or not data:
            raise PlanError("Expected PostgreSQL JSON EXPLAIN array")

        entry = data[0]
        if not isinstance(entry, dict) or "Plan" not in entry:
            raise PlanError("Missing root Plan")

        planning = cls._number(
            entry.get("Planning Time", 0), "Planning Time"
        )
        execution = cls._number(
            entry.get("Execution Time", 0), "Execution Time"
        )

        root = cls.parse_node(entry["Plan"])

        return ExecutionReport(
            planning_time_ms=planning,
            execution_time_ms=execution,
            root=root,
            settings=entry.get("Settings", {}),
        )


class PlanAnalyzer:
    """Evaluates plan quality using configurable diagnostic rules."""

    def __init__(
        self,
        row_error_threshold: float = 10.0,
        expensive_node_threshold_ms: float = 20.0,
    ):
        if row_error_threshold < 1:
            raise ValueError("Row error threshold must be at least 1")
        if expensive_node_threshold_ms < 0:
            raise ValueError("Time threshold cannot be negative")

        self.row_error_threshold = row_error_threshold
        self.expensive_node_threshold_ms = expensive_node_threshold_ms

    def flatten(self, root: PlanMetrics) -> list[PlanMetrics]:
        result = []
        stack = [root]

        while stack:
            node = stack.pop()
            result.append(node)
            stack.extend(reversed(node.children))

        return result

    def analyze(self, report: ExecutionReport) -> list[str]:
        findings = []

        if report.execution_time_ms > 100:
            findings.append(
                "[WARNING] Query execution exceeded 100 ms."
            )

        if report.planning_time_ms > report.execution_time_ms:
            findings.append(
                "[INFO] Planning time exceeds execution time."
            )

        for node in self.flatten(report.root):
            if node.estimation_error >= self.row_error_threshold:
                findings.append(
                    f"[WARNING] Cardinality estimation error in "
                    f"{node.node_type}: estimated "
                    f"{node.estimated_rows:.0f}, actual "
                    f"{node.actual_rows:.0f} rows per loop."
                )

            if (
                node.node_type == "Seq Scan"
                and node.total_time_ms >= self.expensive_node_threshold_ms
            ):
                findings.append(
                    f"[WARNING] Expensive sequential scan on "
                    f"{node.relation or 'unknown relation'}."
                )

            if node.loops > 1 and node.total_node_time_ms >= 20:
                findings.append(
                    f"[WARNING] Repeated execution of {node.node_type}: "
                    f"{node.loops} loops, approximately "
                    f"{node.total_node_time_ms:.3f} ms accumulated "
                    f"node time."
                )

            if node.shared_read_blocks > 0:
                findings.append(
                    f"[INFO] {node.node_type} read "
                    f"{node.shared_read_blocks} shared blocks from storage."
                )

        if not findings:
            findings.append(
                "[INFO] No configured performance warning detected."
            )

        return findings

    def verify(
        self,
        report: ExecutionReport,
        maximum_execution_time_ms: float,
        maximum_estimation_error: float = 20.0,
    ) -> bool:
        if maximum_execution_time_ms < 0:
            raise ValueError("Execution limit cannot be negative")

        if maximum_estimation_error < 1:
            raise ValueError("Estimation error limit must be at least 1")

        if report.execution_time_ms > maximum_execution_time_ms:
            return False

        for node in self.flatten(report.root):
            if node.estimation_error > maximum_estimation_error:
                return False

        return True


class Benchmark:
    """Maintains repeated execution measurements."""

    def __init__(self):
        self.samples: list[float] = []

    def add(self, execution_time_ms: float) -> None:
        if (
            not math.isfinite(execution_time_ms)
            or execution_time_ms < 0
        ):
            raise ValueError("Invalid execution time")
        self.samples.append(execution_time_ms)

    def summary(self) -> dict[str, float]:
        if not self.samples:
            raise ValueError("No benchmark measurements available")

        return {
            "runs": len(self.samples),
            "minimum_ms": min(self.samples),
            "maximum_ms": max(self.samples),
            "average_ms": statistics.mean(self.samples),
            "median_ms": statistics.median(self.samples),
        }


class ReportPrinter:

    @staticmethod
    def print_node(node: PlanMetrics, depth: int = 0) -> None:
        indent = "  " * depth
        relation = f" [{node.relation}]" if node.relation else ""

        print(
            f"{indent}{node.node_type}{relation}\n"
            f"{indent}  Estimated rows: {node.estimated_rows:.0f}\n"
            f"{indent}  Actual rows/loop: {node.actual_rows:.0f}\n"
            f"{indent}  Loops: {node.loops}\n"
            f"{indent}  Total rows across loops: "
            f"{node.total_actual_rows:.0f}\n"
            f"{indent}  Actual time/loop: "
            f"{node.total_time_ms:.3f} ms\n"
            f"{indent}  Accumulated node time: "
            f"{node.total_node_time_ms:.3f} ms"
        )

        for child in node.children:
            ReportPrinter.print_node(child, depth + 1)

    @staticmethod
    def print_report(report: ExecutionReport) -> None:
        print("\nEXECUTION PLAN")
        print("=" * 60)
        ReportPrinter.print_node(report.root)

        print("\nQUERY TIMING")
        print("-" * 60)
        print(f"Planning Time : {report.planning_time_ms:.3f} ms")
        print(f"Execution Time: {report.execution_time_ms:.3f} ms")


def demonstration() -> None:
    # Representative structure of EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON).
    # These values are demonstration measurements, not live database results.
    sample_plan = [
        {
            "Plan": {
                "Node Type": "Nested Loop",
                "Startup Cost": 0.50,
                "Total Cost": 125.00,
                "Plan Rows": 50,
                "Actual Startup Time": 0.120,
                "Actual Total Time": 2.500,
                "Actual Rows": 50,
                "Actual Loops": 1,
                "Shared Hit Blocks": 15,
                "Shared Read Blocks": 0,
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "customers",
                        "Index Name": "customers_pkey",
                        "Startup Cost": 0.30,
                        "Total Cost": 8.00,
                        "Plan Rows": 50,
                        "Actual Startup Time": 0.020,
                        "Actual Total Time": 0.100,
                        "Actual Rows": 50,
                        "Actual Loops": 1,
                        "Shared Hit Blocks": 5,
                        "Shared Read Blocks": 0
                    },
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "orders",
                        "Index Name": "orders_customer_id_idx",
                        "Startup Cost": 0.20,
                        "Total Cost": 2.00,
                        "Plan Rows": 1,
                        "Actual Startup Time": 0.010,
                        "Actual Total Time": 0.030,
                        "Actual Rows": 1,
                        "Actual Loops": 50,
                        "Shared Hit Blocks": 10,
                        "Shared Read Blocks": 0
                    }
                ]
            },
            "Planning Time": 0.450,
            "Execution Time": 2.750
        }
    ]

    document = json.dumps(sample_plan)
    report = PlanParser.parse(document)

    ReportPrinter.print_report(report)

    analyzer = PlanAnalyzer(
        row_error_threshold=10,
        expensive_node_threshold_ms=20
    )

    print("\nDIAGNOSTICS")
    print("-" * 60)

    for finding in analyzer.analyze(report):
        print(finding)

    print("\nPLAN VERIFICATION")
    passed = analyzer.verify(
        report,
        maximum_execution_time_ms=10,
        maximum_estimation_error=20
    )
    print("PASS" if passed else "FAIL")

    benchmark = Benchmark()

    for measurement in [2.75, 2.60, 2.85, 2.70, 2.65]:
        benchmark.add(measurement)

    print("\nBENCHMARK STATISTICS")
    print("-" * 60)

    for key, value in benchmark.summary().items():
        print(f"{key}: {value}")


def run_tests() -> None:
    assert PlanAnalyzer().verify(
        PlanParser.parse(json.dumps([
            {
                "Plan": {
                    "Node Type": "Index Scan",
                    "Plan Rows": 10,
                    "Actual Rows": 10,
                    "Actual Loops": 1
                },
                "Planning Time": 0.1,
                "Execution Time": 1.0
            }
        ])),
        5
    )

    benchmark = Benchmark()
    benchmark.add(1.0)
    benchmark.add(3.0)
    assert benchmark.summary()["median_ms"] == 2.0

    try:
        PlanParser.parse("invalid")
        raise AssertionError("Invalid JSON was accepted")
    except PlanError:
        pass

    print("\nAll tests passed.")


if __name__ == "__main__":
    try:
        demonstration()
        run_tests()
    except (PlanError, ValueError, TypeError, KeyError) as exc:
        print(f"Execution failed: {exc}", file=sys.stderr)
        sys.exit(1)
