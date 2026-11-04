"use strict";

const { performance } = require("node:perf_hooks");
const { EventEmitter } = require("node:events");

class ValidationError extends Error {}
class ConsistencyError extends Error {}

const OrderStatus = Object.freeze({
    PENDING: "pending",
    COMPLETED: "completed",
    CANCELLED: "cancelled"
});

const Strategy = Object.freeze({
    NORMALIZED: "normalized",
    SNAPSHOT: "denormalized_snapshot",
    CACHE: "materialized_cache"
});

class OrderRepository {
    #customers = new Map();
    #orders = new Map();

    addCustomer(customer) {
        if (!Number.isSafeInteger(customer.id) || customer.id <= 0) {
            throw new ValidationError("Invalid customer ID");
        }

        if (!customer.name?.trim() || !customer.email?.trim()) {
            throw new ValidationError("Customer name and email are required");
        }

        if (this.#customers.has(customer.id)) {
            throw new ValidationError("Customer already exists");
        }

        const email = customer.email.toLowerCase();

        if ([...this.#customers.values()].some(
            item => item.email.toLowerCase() === email
        )) {
            throw new ValidationError("Email already exists");
        }

        this.#customers.set(customer.id, Object.freeze({
            id: customer.id,
            name: customer.name.trim(),
            email
        }));
    }

    getCustomer(id) {
        return this.#customers.get(id);
    }

    getCustomers() {
        return [...this.#customers.values()];
    }

    getOrders() {
        return [...this.#orders.values()];
    }

    addOrder(order) {
        if (!Number.isSafeInteger(order.id) || order.id <= 0) {
            throw new ValidationError("Invalid order ID");
        }

        if (this.#orders.has(order.id)) {
            throw new ValidationError("Duplicate order ID");
        }

        if (!this.#customers.has(order.customerId)) {
            throw new ValidationError("Unknown customer");
        }

        if (!Number.isFinite(order.amount) || order.amount < 0) {
            throw new ValidationError("Invalid order amount");
        }

        if (!Object.values(OrderStatus).includes(order.status)) {
            throw new ValidationError("Invalid order status");
        }

        this.#orders.set(order.id, Object.freeze({ ...order }));
    }

    updateCustomerName(id, name) {
        const existing = this.#customers.get(id);

        if (!existing) {
            throw new ValidationError("Customer not found");
        }

        if (!name?.trim()) {
            throw new ValidationError("Customer name cannot be empty");
        }

        this.#customers.set(id, Object.freeze({
            ...existing,
            name: name.trim()
        }));
    }
}

class SummaryProjection extends EventEmitter {
    #repository;
    #summaries = new Map();
    #dirty = new Set();
    #revision = 0;

    constructor(repository) {
        super();
        this.#repository = repository;
        this.rebuildAll();
    }

    #calculate(customerId) {
        const customer = this.#repository.getCustomer(customerId);

        if (!customer) {
            throw new ValidationError("Customer not found");
        }

        const orders = this.#repository.getOrders().filter(
            order => order.customerId === customerId
        );

        const completed = orders.filter(
            order => order.status === OrderStatus.COMPLETED
        );

        return Object.freeze({
            customerId,
            customerName: customer.name,
            orderCount: orders.length,
            completedCount: completed.length,
            totalSpending: Number(
                completed.reduce((sum, order) => sum + order.amount, 0)
                    .toFixed(2)
            ),
            revision: ++this.#revision,
            generatedAt: new Date().toISOString()
        });
    }

    rebuildAll() {
        const next = new Map();

        for (const customer of this.#repository.getCustomers()) {
            next.set(customer.id, this.#calculate(customer.id));
        }

        // Replace the projection only after every record is calculated.
        this.#summaries = next;
        this.#dirty.clear();

        this.emit("rebuilt", { count: next.size });
    }

    rebuild(customerId) {
        const summary = this.#calculate(customerId);
        this.#summaries.set(customerId, summary);
        this.#dirty.delete(customerId);

        this.emit("refreshed", summary);
        return summary;
    }

    invalidate(customerId) {
        if (!this.#repository.getCustomer(customerId)) {
            throw new ValidationError("Cannot invalidate unknown customer");
        }

        this.#dirty.add(customerId);
        this.emit("invalidated", customerId);
    }

    async refresh(customerId) {
        // Asynchronous boundary permits batching or external storage adapters.
        await Promise.resolve();
        return this.rebuild(customerId);
    }

    async refreshDirty() {
        const ids = [...this.#dirty];

        for (const id of ids) {
            await this.refresh(id);
        }

        return ids.length;
    }

    get(customerId, consistency = "strict") {
        if (consistency === "strict" && this.#dirty.has(customerId)) {
            return this.rebuild(customerId);
        }

        if (!["strict", "eventual"].includes(consistency)) {
            throw new ValidationError("Unknown consistency mode");
        }

        const summary = this.#summaries.get(customerId);

        if (!summary) {
            throw new ValidationError("Summary not found");
        }

        return summary;
    }

    getDirtyIds() {
        return [...this.#dirty];
    }

    getAll() {
        return [...this.#summaries.values()];
    }

    validate() {
        for (const customer of this.#repository.getCustomers()) {
            const expected = this.#calculate(customer.id);
            const actual = this.#summaries.get(customer.id);

            if (!actual ||
                actual.customerName !== expected.customerName ||
                actual.orderCount !== expected.orderCount ||
                actual.completedCount !== expected.completedCount ||
                Math.abs(
                    actual.totalSpending - expected.totalSpending
                ) > 0.000001) {
                return false;
            }
        }

        return true;
    }
}

class DenormalizationPolicy {
    constructor({
        minimumReadQueries,
        maximumStalenessMs,
        writeAmplificationLimit,
        allowEventualConsistency
    }) {
        if (minimumReadQueries < 1 ||
            maximumStalenessMs < 0 ||
            writeAmplificationLimit < 1) {
            throw new ValidationError("Invalid denormalization policy");
        }

        this.minimumReadQueries = minimumReadQueries;
        this.maximumStalenessMs = maximumStalenessMs;
        this.writeAmplificationLimit = writeAmplificationLimit;
        this.allowEventualConsistency = allowEventualConsistency;
    }

    evaluate(metrics) {
        const reasons = [];

        if (metrics.readQueries < this.minimumReadQueries) {
            reasons.push("Insufficient read workload");
        }

        if (metrics.writeAmplification > this.writeAmplificationLimit) {
            reasons.push("Write amplification exceeds policy");
        }

        if (metrics.expectedStalenessMs > this.maximumStalenessMs) {
            reasons.push("Expected staleness exceeds policy");
        }

        if (metrics.eventualConsistency &&
            !this.allowEventualConsistency) {
            reasons.push("Eventual consistency is prohibited");
        }

        return Object.freeze({
            approved: reasons.length === 0,
            reasons
        });
    }
}

async function benchmark(name, operation) {
    const start = performance.now();
    const result = await operation();

    return {
        strategy: name,
        elapsedMs: Number((performance.now() - start).toFixed(4)),
        records: result.length
    };
}

function normalizedReport(repository) {
    const grouped = new Map();

    for (const order of repository.getOrders()) {
        if (!grouped.has(order.customerId)) {
            grouped.set(order.customerId, []);
        }

        grouped.get(order.customerId).push(order);
    }

    return repository.getCustomers().map(customer => {
        const orders = grouped.get(customer.id) ?? [];
        const completed = orders.filter(
            order => order.status === OrderStatus.COMPLETED
        );

        return {
            customerId: customer.id,
            customerName: customer.name,
            orderCount: orders.length,
            totalSpending: completed.reduce(
                (sum, order) => sum + order.amount, 0
            )
        };
    });
}

async function main() {
    const repository = new OrderRepository();

    repository.addCustomer({
        id: 1, name: "Aarav Sharma", email: "aarav@example.com"
    });

    repository.addCustomer({
        id: 2, name: "Diya Verma", email: "diya@example.com"
    });

    repository.addCustomer({
        id: 3, name: "Kabir Singh", email: "kabir@example.com"
    });

    [
        { id: 101, customerId: 1, amount: 1200, status: "completed" },
        { id: 102, customerId: 1, amount: 800, status: "completed" },
        { id: 103, customerId: 1, amount: 500, status: "pending" },
        { id: 104, customerId: 2, amount: 2500, status: "completed" },
        { id: 105, customerId: 2, amount: 300, status: "cancelled" }
    ].forEach(order => repository.addOrder(order));

    const projection = new SummaryProjection(repository);

    projection.on("invalidated", id => {
        console.log(`Projection invalidated for customer ${id}`);
    });

    projection.on("refreshed", summary => {
        console.log(`Projection refreshed: revision ${summary.revision}`);
    });

    console.log("INITIAL PROJECTION");
    console.table(projection.getAll());

    console.log("\nQUERY COMPARISON");

    const results = await Promise.all([
        benchmark(Strategy.NORMALIZED, async () =>
            normalizedReport(repository)
        ),
        benchmark(Strategy.SNAPSHOT, async () =>
            projection.getAll()
        )
    ]);

    console.table(results);

    // A source write invalidates the affected read model.
    repository.addOrder({
        id: 106,
        customerId: 1,
        amount: 400,
        status: "completed"
    });

    projection.invalidate(1);

    console.log("\nEVENTUAL CONSISTENCY READ");
    console.log(projection.get(1, "eventual"));

    console.log("\nSTRICT CONSISTENCY READ");
    console.log(await projection.refresh(1));

    // A dimension update also requires projection refresh.
    repository.updateCustomerName(2, "Diya Sharma");
    projection.invalidate(2);

    await projection.refreshDirty();

    console.log("\nUPDATED PROJECTION");
    console.table(projection.getAll());

    const policy = new DenormalizationPolicy({
        minimumReadQueries: 1000,
        maximumStalenessMs: 5000,
        writeAmplificationLimit: 3,
        allowEventualConsistency: true
    });

    console.log("\nPOLICY EVALUATION");
    console.log(policy.evaluate({
        readQueries: 5000,
        expectedStalenessMs: 1000,
        writeAmplification: 2,
        eventualConsistency: true
    }));

    console.log("\nCONSISTENCY VALIDATION");
    console.log(projection.validate());

    try {
        repository.addOrder({
            id: 107,
            customerId: 999,
            amount: 500,
            status: "completed"
        });
    } catch (error) {
        console.error("EXPECTED VALIDATION ERROR:", error.message);
    }

    console.log("\nDIRTY CUSTOMERS");
    console.log(projection.getDirtyIds());
}

main().catch(error => {
    console.error("Application failure:", error.message);
    process.exitCode = 1;
});
