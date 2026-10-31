from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
import csv
import json
import tempfile
from typing import Iterable


CENT = Decimal("0.01")


def money(value: Decimal | int | float | str) -> Decimal:
    """Normalize monetary values to two decimal places."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


class OrderStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Customer:
    customer_id: int
    name: str
    email: str
    city: str
    credit_limit: Decimal = Decimal("0")


@dataclass(frozen=True)
class Product:
    product_id: int
    name: str
    category: str
    unit_price: Decimal
    stock: int


@dataclass(frozen=True)
class OrderItem:
    product_id: int
    quantity: int
    unit_price: Decimal

    @property
    def revenue(self) -> Decimal:
        return money(self.quantity * self.unit_price)


@dataclass
class Order:
    order_id: int
    customer_id: int
    order_date: date
    status: OrderStatus
    items: list[OrderItem] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return money(sum((item.revenue for item in self.items), Decimal("0")))


class SalesDatabase:
    """In-memory sales database supporting validation and analytical queries."""

    def __init__(self) -> None:
        self.customers: dict[int, Customer] = {}
        self.products: dict[int, Product] = {}
        self.orders: dict[int, Order] = {}

    def add_customer(self, customer: Customer) -> None:
        if customer.customer_id in self.customers:
            raise ValueError("Customer ID already exists.")
        if not customer.name.strip():
            raise ValueError("Customer name cannot be empty.")
        if "@" not in customer.email:
            raise ValueError("Invalid customer email.")
        if customer.credit_limit < 0:
            raise ValueError("Credit limit cannot be negative.")
        self.customers[customer.customer_id] = customer

    def add_product(self, product: Product) -> None:
        if product.product_id in self.products:
            raise ValueError("Product ID already exists.")
        if not product.name.strip():
            raise ValueError("Product name cannot be empty.")
        if product.unit_price <= 0:
            raise ValueError("Product price must be positive.")
        if product.stock < 0:
            raise ValueError("Product stock cannot be negative.")
        self.products[product.product_id] = product

    def create_order(
        self,
        order_id: int,
        customer_id: int,
        order_date: date,
        requested_items: Iterable[tuple[int, int]],
    ) -> Order:
        if order_id in self.orders:
            raise ValueError("Order ID already exists.")
        if customer_id not in self.customers:
            raise ValueError("Customer does not exist.")

        items: list[OrderItem] = []
        for product_id, quantity in requested_items:
            if product_id not in self.products:
                raise ValueError(f"Product {product_id} does not exist.")
            if quantity <= 0:
                raise ValueError("Quantity must be positive.")

            product = self.products[product_id]
            if quantity > product.stock:
                raise ValueError(
                    f"Insufficient stock for {product.name}: "
                    f"requested {quantity}, available {product.stock}."
                )

            items.append(OrderItem(product_id, quantity, product.unit_price))

        if not items:
            raise ValueError("An order must contain at least one item.")

        order = Order(
            order_id=order_id,
            customer_id=customer_id,
            order_date=order_date,
            status=OrderStatus.PENDING,
            items=items,
        )
        self.orders[order_id] = order

        # Reserve stock only after every line has passed validation.
        for item in items:
            product = self.products[item.product_id]
            self.products[item.product_id] = Product(
                product.product_id,
                product.name,
                product.category,
                product.unit_price,
                product.stock - item.quantity,
            )

        return order

    def update_order_status(self, order_id: int, status: OrderStatus) -> None:
        if order_id not in self.orders:
            raise ValueError("Order does not exist.")

        order = self.orders[order_id]
        allowed = {
            OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
            OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
            OrderStatus.SHIPPED: set(),
            OrderStatus.CANCELLED: set(),
        }

        if status not in allowed[order.status]:
            raise ValueError(
                f"Invalid transition: {order.status.value} -> {status.value}"
            )

        # Cancelled orders release previously reserved stock.
        if status == OrderStatus.CANCELLED:
            for item in order.items:
                product = self.products[item.product_id]
                self.products[item.product_id] = Product(
                    product.product_id,
                    product.name,
                    product.category,
                    product.unit_price,
                    product.stock + item.quantity,
                )

        order.status = status

    def completed_orders(self) -> list[Order]:
        return [
            order
            for order in self.orders.values()
            if order.status in {OrderStatus.PAID, OrderStatus.SHIPPED}
        ]

    def revenue_by_category(self) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for order in self.completed_orders():
            for item in order.items:
                category = self.products[item.product_id].category
                result[category] = money(
                    result.get(category, Decimal("0")) + item.revenue
                )
        return dict(sorted(result.items(), key=lambda pair: pair[1], reverse=True))

    def revenue_by_customer(self) -> list[tuple[str, Decimal]]:
        totals: dict[int, Decimal] = {}
        for order in self.completed_orders():
            totals[order.customer_id] = money(
                totals.get(order.customer_id, Decimal("0")) + order.total
            )

        result = [
            (self.customers[customer_id].name, total)
            for customer_id, total in totals.items()
        ]
        return sorted(result, key=lambda pair: pair[1], reverse=True)

    def monthly_revenue(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for order in self.completed_orders():
            key = order.order_date.strftime("%Y-%m")
            totals[key] = money(totals.get(key, Decimal("0")) + order.total)
        return dict(sorted(totals.items()))

    def top_products(self, limit: int = 5) -> list[tuple[str, int, Decimal]]:
        if limit <= 0:
            raise ValueError("Limit must be positive.")

        quantities: dict[int, int] = {}
        revenue: dict[int, Decimal] = {}

        for order in self.completed_orders():
            for item in order.items:
                quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
                revenue[item.product_id] = money(
                    revenue.get(item.product_id, Decimal("0")) + item.revenue
                )

        rows = [
            (
                self.products[product_id].name,
                quantity,
                revenue[product_id],
            )
            for product_id, quantity in quantities.items()
        ]
        rows.sort(key=lambda row: (row[2], row[1]), reverse=True)
        return rows[:limit]

    def customer_lifetime_value(self, customer_id: int) -> Decimal:
        if customer_id not in self.customers:
            raise ValueError("Customer does not exist.")
        return money(
            sum(
                (order.total for order in self.completed_orders()
                 if order.customer_id == customer_id),
                Decimal("0"),
            )
        )

    def export_report(self, path: Path) -> None:
        """Export customer revenue using CSV without exposing internal objects."""
        rows = self.revenue_by_customer()
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["customer", "revenue"])
            for customer, revenue in rows:
                writer.writerow([customer, f"{revenue:.2f}"])


def seed_database() -> SalesDatabase:
    db = SalesDatabase()

    customers = [
        Customer(1, "Apex Retail", "sales@apex.example", "Delhi", Decimal("15000")),
        Customer(2, "Northstar Foods", "orders@northstar.example", "Lucknow", Decimal("10000")),
        Customer(3, "Greenline Stores", "procurement@greenline.example", "Pune", Decimal("12000")),
        Customer(4, "Metro Office", "buying@metro.example", "Mumbai", Decimal("8000")),
    ]

    products = [
        Product(101, "Business Laptop", "Computers", Decimal("85000"), 20),
        Product(102, "Wireless Keyboard", "Accessories", Decimal("2500"), 100),
        Product(103, "USB-C Dock", "Accessories", Decimal("6500"), 50),
        Product(104, "Network Switch", "Networking", Decimal("12000"), 30),
        Product(105, "Wi-Fi Router", "Networking", Decimal("7000"), 40),
    ]

    for customer in customers:
        db.add_customer(customer)
    for product in products:
        db.add_product(product)

    base = date(2026, 1, 10)

    db.create_order(
        1001,
        1,
        base,
        [(101, 2), (102, 5)],
    )
    db.update_order_status(1001, OrderStatus.PAID)
    db.update_order_status(1001, OrderStatus.SHIPPED)

    db.create_order(
        1002,
        2,
        base + timedelta(days=12),
        [(104, 2), (105, 3)],
    )
    db.update_order_status(1002, OrderStatus.PAID)

    db.create_order(
        1003,
        3,
        base + timedelta(days=35),
        [(103, 4), (102, 10)],
    )
    db.update_order_status(1003, OrderStatus.PAID)
    db.update_order_status(1003, OrderStatus.SHIPPED)

    db.create_order(
        1004,
        1,
        base + timedelta(days=50),
        [(101, 1), (103, 2)],
    )
    db.update_order_status(1004, OrderStatus.PAID)

    # This order exercises cancellation and stock restoration.
    db.create_order(
        1005,
        4,
        base + timedelta(days=55),
        [(105, 2)],
    )
    db.update_order_status(1005, OrderStatus.CANCELLED)

    db.create_order(
        1006,
        2,
        date(2026, 3, 5),
        [(101, 1), (104, 1)],
    )
    db.update_order_status(1006, OrderStatus.PAID)
    db.update_order_status(1006, OrderStatus.SHIPPED)

    return db


def run_assertions(db: SalesDatabase) -> None:
    assert db.customer_lifetime_value(1) == Decimal("186000.00")
    assert db.customer_lifetime_value(4) == Decimal("0.00")

    categories = db.revenue_by_category()
    assert categories["Computers"] == Decimal("255000.00")
    assert categories["Networking"] == Decimal("45000.00")

    top = db.top_products()
    assert top[0][0] == "Business Laptop"

    # Cancelled order must not contribute to revenue.
    assert all(order.order_id != 1005 for order in db.completed_orders())

    try:
        db.create_order(1007, 1, date.today(), [(101, 999)])
    except ValueError:
        pass
    else:
        raise AssertionError("Overselling should fail.")

    try:
        db.update_order_status(1001, OrderStatus.PAID)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid status transition should fail.")


def main() -> None:
    db = seed_database()
    run_assertions(db)

    print("SALES DATABASE ANALYSIS")
    print("=" * 60)

    total_revenue = money(
        sum((order.total for order in db.completed_orders()), Decimal("0"))
    )
    print(f"Completed revenue: {total_revenue:.2f}")
    print(f"Completed orders: {len(db.completed_orders())}")

    print("\nRevenue by category:")
    for category, revenue in db.revenue_by_category().items():
        print(f"  {category:15} {revenue:>12.2f}")

    print("\nRevenue by customer:")
    for customer, revenue in db.revenue_by_customer():
        print(f"  {customer:20} {revenue:>12.2f}")

    print("\nMonthly revenue:")
    for month, revenue in db.monthly_revenue().items():
        print(f"  {month}: {revenue:.2f}")

    print("\nTop products:")
    for name, quantity, revenue in db.top_products(3):
        print(f"  {name:20} units={quantity:3} revenue={revenue:.2f}")

    with tempfile.TemporaryDirectory() as directory:
        report_path = Path(directory) / "customer_revenue.csv"
        db.export_report(report_path)
        print(f"\nCSV report generated: {report_path.name}")

        # Read the generated file to verify that the persisted report is valid.
        with report_path.open(encoding="utf-8") as handle:
            exported_rows = list(csv.DictReader(handle))
        assert exported_rows

    # JSON serialization example for an API/reporting boundary.
    summary = {
        "completed_revenue": str(total_revenue),
        "completed_orders": len(db.completed_orders()),
        "category_revenue": {
            category: str(value)
            for category, value in db.revenue_by_category().items()
        },
    }
    print("\nMachine-readable summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
