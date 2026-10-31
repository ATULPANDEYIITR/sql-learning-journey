"use strict";

const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { EventEmitter } = require("node:events");

const CENTS = 100;

function money(value) {
    if (!Number.isFinite(value)) {
        throw new TypeError("Money value must be finite.");
    }
    return Math.round((value + Number.EPSILON) * CENTS) / CENTS;
}

function requirePositiveInteger(value, field) {
    if (!Number.isInteger(value) || value <= 0) {
        throw new RangeError(`${field} must be a positive integer.`);
    }
}

class SalesError extends Error {
    constructor(message, code) {
        super(message);
        this.name = "SalesError";
        this.code = code;
    }
}

class Customer {
    constructor({ id, name, email, city, creditLimit }) {
        requirePositiveInteger(id, "Customer ID");
        if (!name?.trim()) throw new SalesError("Customer name is required", "INVALID_CUSTOMER");
        if (!email?.includes("@")) throw new SalesError("Invalid email", "INVALID_CUSTOMER");
        if (!Number.isFinite(creditLimit) || creditLimit < 0) {
            throw new SalesError("Invalid credit limit", "INVALID_CUSTOMER");
        }

        this.id = id;
        this.name = name.trim();
        this.email = email.toLowerCase();
        this.city = city?.trim() || "Unknown";
        this.creditLimit = money(creditLimit);
    }
}

class Product {
    constructor({ id, name, category, price, stock }) {
        requirePositiveInteger(id, "Product ID");
        if (!name?.trim()) throw new SalesError("Product name is required", "INVALID_PRODUCT");
        if (!Number.isFinite(price) || price <= 0) {
            throw new SalesError("Product price must be positive", "INVALID_PRODUCT");
        }
        if (!Number.isInteger(stock) || stock < 0) {
            throw new SalesError("Product stock cannot be negative", "INVALID_PRODUCT");
        }

        this.id = id;
        this.name = name.trim();
        this.category = category.trim();
        this.price = money(price);
        this.stock = stock;
    }
}

class SalesEventBus extends EventEmitter {}

class SalesRepository {
    constructor(eventBus) {
        this.customers = new Map();
        this.products = new Map();
        this.orders = new Map();
        this.eventBus = eventBus;
    }

    addCustomer(customer) {
        if (this.customers.has(customer.id)) {
            throw new SalesError("Customer already exists", "DUPLICATE_CUSTOMER");
        }
        this.customers.set(customer.id, customer);
    }

    addProduct(product) {
        if (this.products.has(product.id)) {
            throw new SalesError("Product already exists", "DUPLICATE_PRODUCT");
        }
        this.products.set(product.id, product);
    }

    createOrder({ id, customerId, orderDate, lines }) {
        requirePositiveInteger(id, "Order ID");
        if (this.orders.has(id)) {
            throw new SalesError("Order already exists", "DUPLICATE_ORDER");
        }
        if (!this.customers.has(customerId)) {
            throw new SalesError("Customer does not exist", "MISSING_CUSTOMER");
        }
        if (!Array.isArray(lines) || lines.length === 0) {
            throw new SalesError("Order must contain lines", "EMPTY_ORDER");
        }

        const normalizedLines = [];
        const requestedQuantities = new Map();

        for (const line of lines) {
            requirePositiveInteger(line.productId, "Product ID");
            requirePositiveInteger(line.quantity, "Quantity");

            const product = this.products.get(line.productId);
            if (!product) {
                throw new SalesError(
                    `Product ${line.productId} does not exist`,
                    "MISSING_PRODUCT"
                );
            }

            const quantity =
                (requestedQuantities.get(line.productId) || 0) + line.quantity;

            if (quantity > product.stock) {
                throw new SalesError(
                    `Insufficient stock for ${product.name}`,
                    "INSUFFICIENT_STOCK"
                );
            }

            requestedQuantities.set(line.productId, quantity);
            normalizedLines.push({
                productId: product.id,
                quantity: line.quantity,
                unitPrice: product.price
            });
        }

        // All validation completes before stock is changed.
        for (const [productId, quantity] of requestedQuantities) {
            this.products.get(productId).stock -= quantity;
        }

        const order = {
            id,
            customerId,
            orderDate: new Date(orderDate),
            status: "PENDING",
            lines: normalizedLines
        };

        if (Number.isNaN(order.orderDate.getTime())) {
            throw new SalesError("Invalid order date", "INVALID_DATE");
        }

        this.orders.set(id, order);
        this.eventBus.emit("order.created", order);
        return order;
    }

    total(order) {
        return money(
            order.lines.reduce(
                (sum, line) => sum + line.quantity * line.unitPrice,
                0
            )
        );
    }

    changeStatus(orderId, newStatus) {
        const order = this.orders.get(orderId);
        if (!order) throw new SalesError("Order does not exist", "MISSING_ORDER");

        const transitions = {
            PENDING: new Set(["PAID", "CANCELLED"]),
            PAID: new Set(["SHIPPED", "CANCELLED"]),
            SHIPPED: new Set(),
            CANCELLED: new Set()
        };

        if (!transitions[order.status].has(newStatus)) {
            throw new SalesError(
                `Invalid transition ${order.status} -> ${newStatus}`,
                "INVALID_TRANSITION"
            );
        }

        if (newStatus === "CANCELLED") {
            for (const line of order.lines) {
                this.products.get(line.productId).stock += line.quantity;
            }
        }

        order.status = newStatus;
        this.eventBus.emit("order.statusChanged", {
            orderId,
            status: newStatus
        });
    }

    completedOrders() {
        return [...this.orders.values()].filter(
            order => order.status === "PAID" || order.status === "SHIPPED"
        );
    }

    revenueByCategory() {
        const result = new Map();

        for (const order of this.completedOrders()) {
            for (const line of order.lines) {
                const category = this.products.get(line.productId).category;
                const value = (result.get(category) || 0) +
                    line.quantity * line.unitPrice;
                result.set(category, money(value));
            }
        }

        return [...result.entries()]
            .sort((a, b) => b[1] - a[1]);
    }

    topCustomers(limit = 5) {
        requirePositiveInteger(limit, "Limit");

        const totals = new Map();

        for (const order of this.completedOrders()) {
            const current = totals.get(order.customerId) || 0;
            totals.set(order.customerId, money(current + this.total(order)));
        }

        return [...totals.entries()]
            .map(([customerId, revenue]) => ({
                customer: this.customers.get(customerId).name,
                revenue
            }))
            .sort((a, b) => b.revenue - a.revenue)
            .slice(0, limit);
    }

    async writeCustomerRevenueReport(filePath) {
        const rows = ["customer,revenue"];

        for (const row of this.topCustomers(Number.MAX_SAFE_INTEGER)) {
            const safeName = row.customer.replaceAll('"', '""');
            rows.push(`"${safeName}",${row.revenue.toFixed(2)}`);
        }

        await fs.writeFile(filePath, rows.join("\n") + "\n", "utf8");
    }
}

function seed(repository) {
    [
        new Customer({
            id: 1,
            name: "Apex Retail",
            email: "sales@apex.example",
            city: "Delhi",
            creditLimit: 15000
        }),
        new Customer({
            id: 2,
            name: "Northstar Foods",
            email: "orders@northstar.example",
            city: "Lucknow",
            creditLimit: 10000
        }),
        new Customer({
            id: 3,
            name: "Greenline Stores",
            email: "procurement@greenline.example",
            city: "Pune",
            creditLimit: 12000
        })
    ].forEach(customer => repository.addCustomer(customer));

    [
        new Product({
            id: 101,
            name: "Business Laptop",
            category: "Computers",
            price: 85000,
            stock: 20
        }),
        new Product({
            id: 102,
            name: "Wireless Keyboard",
            category: "Accessories",
            price: 2500,
            stock: 100
        }),
        new Product({
            id: 103,
            name: "USB-C Dock",
            category: "Accessories",
            price: 6500,
            stock: 50
        }),
        new Product({
            id: 104,
            name: "Network Switch",
            category: "Networking",
            price: 12000,
            stock: 30
        })
    ].forEach(product => repository.addProduct(product));
}

async function main() {
    const eventBus = new SalesEventBus();

    eventBus.on("order.created", order => {
        console.log(`Event: order ${order.id} created`);
    });

    eventBus.on("order.statusChanged", event => {
        console.log(`Event: order ${event.orderId} -> ${event.status}`);
    });

    const repository = new SalesRepository(eventBus);
    seed(repository);

    repository.createOrder({
        id: 1001,
        customerId: 1,
        orderDate: "2026-01-10",
        lines: [
            { productId: 101, quantity: 2 },
            { productId: 102, quantity: 5 }
        ]
    });
    repository.changeStatus(1001, "PAID");
    repository.changeStatus(1001, "SHIPPED");

    repository.createOrder({
        id: 1002,
        customerId: 2,
        orderDate: "2026-02-12",
        lines: [
            { productId: 104, quantity: 2 },
            { productId: 103, quantity: 3 }
        ]
    });
    repository.changeStatus(1002, "PAID");

    repository.createOrder({
        id: 1003,
        customerId: 3,
        orderDate: "2026-03-05",
        lines: [
            { productId: 102, quantity: 10 },
            { productId: 103, quantity: 4 }
        ]
    });
    repository.changeStatus(1003, "PAID");

    // Demonstrate failure handling without corrupting inventory.
    const stockBefore = repository.products.get(101).stock;
    try {
        repository.createOrder({
            id: 1004,
            customerId: 1,
            orderDate: "2026-03-10",
            lines: [{ productId: 101, quantity: 999 }]
        });
    } catch (error) {
        console.log(`Rejected order: ${error.code}`);
    }
    if (repository.products.get(101).stock !== stockBefore) {
        throw new Error("Failed validation changed stock.");
    }

    const completedRevenue = repository
        .completedOrders()
        .reduce((sum, order) => sum + repository.total(order), 0);

    console.log("\nSALES ANALYSIS");
    console.log(`Completed orders: ${repository.completedOrders().length}`);
    console.log(`Completed revenue: ${money(completedRevenue).toFixed(2)}`);

    console.log("\nRevenue by category:");
    for (const [category, revenue] of repository.revenueByCategory()) {
        console.log(`${category}: ${revenue.toFixed(2)}`);
    }

    console.log("\nTop customers:");
    for (const row of repository.topCustomers()) {
        console.log(`${row.customer}: ${row.revenue.toFixed(2)}`);
    }

    const reportPath = path.join(
        await fs.mkdtemp(path.join(os.tmpdir(), "sales-")),
        "customer-revenue.csv"
    );

    await repository.writeCustomerRevenueReport(reportPath);
    console.log(`\nReport written to: ${path.basename(reportPath)}`);

    const report = await fs.readFile(reportPath, "utf8");
    if (!report.startsWith("customer,revenue")) {
        throw new Error("Report validation failed.");
    }
}

main().catch(error => {
    console.error(`Fatal error: ${error.message}`);
    process.exitCode = 1;
});
