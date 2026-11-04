from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from typing import Any
import json
import time


class DenormalizationError(Exception):
    """Raised when a denormalization operation violates data rules."""


class AggregationStrategy(Enum):
    NONE = "none"
    DUPLICATED_COLUMN = "duplicated_column"
    SUMMARY_TABLE = "summary_table"
    MATERIALIZED_VIEW = "materialized_view"
    PRECOMPUTED_AGGREGATE = "precomputed_aggregate"


@dataclass
class Customer:
    customer_id: int
    name: str
    email: str


@dataclass
class Order:
    order_id: int
    customer_id: int
    amount: float
    status: str


@dataclass
class CustomerSummary:
    customer_id: int
    customer_name: str
    order_count: int = 0
    total_spending: float = 0.0
    completed_orders: int = 0
    version: int = 0


class NormalizedDatabase:
    """Stores authoritative customer and order records."""

    def __init__(self):
        self.customers: dict[int, Customer] = {}
        self.orders: dict[int, Order] = {}

    def add_customer(self, customer: Customer) -> None:
        if customer.customer_id <= 0:
            raise DenormalizationError("Invalid customer ID")
        if not customer.name.strip():
            raise DenormalizationError("Customer name cannot be empty")
        if customer.customer_id in self.customers:
            raise DenormalizationError("Duplicate customer ID")
        if any(c.email.lower() == customer.email.lower()
               for c in self.customers.values()):
            raise DenormalizationError("Duplicate customer email")
        self.customers[customer.customer_id] = customer

    def add_order(self, order: Order) -> None:
        if order.order_id <= 0:
            raise DenormalizationError("Invalid order ID")
        if order.order_id in self.orders:
            raise DenormalizationError("Duplicate order ID")
        if order.customer_id not in self.customers:
            raise DenormalizationError("Customer does not exist")
        if order.amount < 0:
            raise DenormalizationError("Order amount cannot be negative")
        if order.status not in {"pending", "completed", "cancelled"}:
            raise DenormalizationError("Invalid order status")
        self.orders[order.order_id] = order

    def update_customer_name(self, customer_id: int, name: str) -> None:
        if customer_id not in self.customers:
            raise DenormalizationError("Customer not found")
        if not name.strip():
            raise DenormalizationError("Customer name cannot be empty")

        customer = self.customers[customer_id]
        self.customers[customer_id] = Customer(
            customer_id, name, customer.email
        )


class DenormalizedDatabase:
    """Maintains a read-optimized customer summary."""

    def __init__(self, source: NormalizedDatabase):
        self.source = source
        self.summaries: dict[int, CustomerSummary] = {}
        self.dirty_customers: set[int] = set()
        self.rebuild_all()

    def calculate_summary(self, customer_id: int) -> CustomerSummary:
        customer = self.source.customers.get(customer_id)
        if customer is None:
            raise DenormalizationError("Customer not found")

        orders = [
            order for order in self.source.orders.values()
            if order.customer_id == customer_id
        ]

        return CustomerSummary(
            customer_id=customer_id,
            customer_name=customer.name,
            order_count=len(orders),
            total_spending=sum(
                order.amount for order in orders
                if order.status == "completed"
            ),
            completed_orders=sum(
                order.status == "completed" for order in orders
            ),
        )

    def rebuild_all(self) -> None:
        self.summaries = {
            customer_id: self.calculate_summary(customer_id)
            for customer_id in self.source.customers
        }
        self.dirty_customers.clear()

    def rebuild_customer(self, customer_id: int) -> None:
        previous = self.summaries.get(customer_id)
        summary = self.calculate_summary(customer_id)
        summary.version = previous.version + 1 if previous else 1
        self.summaries[customer_id] = summary
        self.dirty_customers.discard(customer_id)

    def mark_dirty(self, customer_id: int) -> None:
        self.dirty_customers.add(customer_id)

    def process_dirty_customers(self) -> None:
        for customer_id in sorted(self.dirty_customers):
            self.rebuild_customer(customer_id)

    def get_customer_summary(
        self, customer_id: int, strict: bool = True
    ) -> CustomerSummary:
        if strict and customer_id in self.dirty_customers:
            self.rebuild_customer(customer_id)

        summary = self.summaries.get(customer_id)
        if summary is None:
            raise DenormalizationError("Summary not found")

        return summary

    def validate_consistency(self) -> bool:
        for customer_id in self.source.customers:
            expected = self.calculate_summary(customer_id)
            actual = self.summaries.get(customer_id)

            if actual is None:
                return False

            if (
                expected.customer_name != actual.customer_name
                or expected.order_count != actual.order_count
                or abs(expected.total_spending - actual.total_spending) > 0.000001
                or expected.completed_orders != actual.completed_orders
            ):
                return False

        return True


@dataclass
class PerformanceResult:
    strategy: str
    execution_time_ms: float
    result_count: int


def measure_query(strategy: str, operation) -> PerformanceResult:
    start = time.perf_counter()
    results = operation()
    elapsed = (time.perf_counter() - start) * 1000

    return PerformanceResult(
        strategy=strategy,
        execution_time_ms=elapsed,
        result_count=len(results),
    )


def normalized_customer_report(
    database: NormalizedDatabase,
) -> list[dict[str, Any]]:
    """Computes aggregates at query time."""
    grouped = defaultdict(list)

    for order in database.orders.values():
        grouped[order.customer_id].append(order)

    results = []

    for customer_id, customer in database.customers.items():
        orders = grouped[customer_id]
        results.append({
            "customer_id": customer_id,
            "customer_name": customer.name,
            "order_count": len(orders),
            "total_spending": round(
                sum(o.amount for o in orders if o.status == "completed"), 2
            ),
        })

    return results


def denormalized_customer_report(
    database: DenormalizedDatabase,
) -> list[dict[str, Any]]:
    return [
        {
            "customer_id": summary.customer_id,
            "customer_name": summary.customer_name,
            "order_count": summary.order_count,
            "total_spending": round(summary.total_spending, 2),
        }
        for summary in database.summaries.values()
    ]


def run_demo() -> None:
    source = NormalizedDatabase()

    source.add_customer(Customer(1, "Aarav Sharma", "aarav@example.com"))
    source.add_customer(Customer(2, "Diya Verma", "diya@example.com"))
    source.add_customer(Customer(3, "Kabir Singh", "kabir@example.com"))

    orders = [
        Order(101, 1, 1200.00, "completed"),
        Order(102, 1, 800.00, "completed"),
        Order(103, 1, 500.00, "pending"),
        Order(104, 2, 2500.00, "completed"),
        Order(105, 2, 300.00, "cancelled"),
    ]

    for order in orders:
        source.add_order(order)

    denormalized = DenormalizedDatabase(source)

    print("INITIAL CUSTOMER SUMMARIES")
    print(json.dumps(
        denormalized_customer_report(denormalized), indent=2
    ))

    normalized_result = measure_query(
        "Normalized aggregation",
        lambda: normalized_customer_report(source)
    )

    denormalized_result = measure_query(
        "Denormalized lookup",
        lambda: denormalized_customer_report(denormalized)
    )

    print("\nQUERY PERFORMANCE")
    print(json.dumps([
        normalized_result.__dict__,
        denormalized_result.__dict__,
    ], indent=2))

    # A new order makes the affected summary stale.
    source.add_order(Order(106, 1, 400.00, "completed"))
    denormalized.mark_dirty(1)

    print("\nDIRTY CUSTOMER IDS")
    print(sorted(denormalized.dirty_customers))

    # Strict reads refresh stale data before returning it.
    refreshed = denormalized.get_customer_summary(1)
    print("\nREFRESHED CUSTOMER")
    print(refreshed)

    # Updating an authoritative customer name requires propagating
    # the change to every denormalized copy.
    source.update_customer_name(2, "Diya Sharma")
    denormalized.mark_dirty(2)
    denormalized.process_dirty_customers()

    print("\nUPDATED CUSTOMER SUMMARIES")
    print(json.dumps(
        denormalized_customer_report(denormalized), indent=2
    ))

    print("\nCONSISTENCY VALIDATION")
    print(denormalized.validate_consistency())

    # Demonstrate a deliberately stale summary.
    source.add_order(Order(107, 3, 1500.00, "completed"))
    denormalized.mark_dirty(3)

    print("\nNON-STRICT READ (POTENTIALLY STALE)")
    print(denormalized.get_customer_summary(3, strict=False))

    print("\nFINAL REBUILD")
    denormalized.process_dirty_customers()
    print("Consistent:", denormalized.validate_consistency())

    # Invalid records are rejected before corrupting authoritative data.
    try:
        source.add_order(Order(108, 999, 100.00, "completed"))
    except DenormalizationError as error:
        print("\nVALIDATION ERROR:", error)


if __name__ == "__main__":
    run_demo()
