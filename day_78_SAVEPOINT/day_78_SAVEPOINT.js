"use strict";

/*
 * SAVEPOINT: Partial Rollback and Nested Transaction Patterns
 *
 * Node.js implementation featuring:
 * - Event-driven transaction processing
 * - Asynchronous transaction operations
 * - Named savepoint management
 * - Partial and complete rollback
 * - Nested transaction scopes
 * - Transaction lifecycle policies
 * - Optimistic version checking
 * - Concurrency conflict detection
 *
 * Run with Node.js 18 or later.
 */

const { EventEmitter } = require("node:events");
const assert = require("node:assert/strict");
const { randomUUID } = require("node:crypto");

class TransactionError extends Error {}
class TransactionStateError extends TransactionError {}
class SavepointError extends TransactionError {}
class ConcurrencyError extends TransactionError {}
class ValidationError extends TransactionError {}

const TransactionStatus = Object.freeze({
    ACTIVE: "ACTIVE",
    COMMITTED: "COMMITTED",
    ROLLED_BACK: "ROLLED_BACK"
});

function clone(value) {
    return structuredClone(value);
}

function validateMoney(value) {
    if (!Number.isSafeInteger(value) || value < 0) {
        throw new ValidationError(
            "Money must be a non-negative integer in paise."
        );
    }
}

class EventJournal extends EventEmitter {
    constructor() {
        super();
        this.events = [];
    }

    record(type, transactionId, details = {}) {
        const event = Object.freeze({
            eventId: randomUUID(),
            type,
            transactionId,
            timestamp: new Date().toISOString(),
            details: Object.freeze(clone(details))
        });

        this.events.push(event);
        this.emit(type, event);

        return event;
    }

    getEvents(transactionId) {
        return this.events.filter(
            event => event.transactionId === transactionId
        );
    }
}

class Repository {
    constructor() {
        this.version = 0;

        this.state = {
            products: new Map([
                [101, {
                    id: 101,
                    name: "Enterprise Laptop",
                    stock: 10,
                    pricePaise: 7500000
                }],
                [102, {
                    id: 102,
                    name: "Wireless Keyboard",
                    stock: 20,
                    pricePaise: 250000
                }],
                [103, {
                    id: 103,
                    name: "External SSD",
                    stock: 5,
                    pricePaise: 650000
                }]
            ]),
            accounts: new Map([
                [1, {
                    id: 1,
                    owner: "Corporate Procurement",
                    balancePaise: 20000000
                }],
                [2, {
                    id: 2,
                    owner: "Regional Procurement",
                    balancePaise: 1000000
                }]
            ]),
            orders: new Map(),
            nextOrderId: 1
        };
    }

    begin() {
        return new Transaction(this);
    }

    read() {
        return clone(this.state);
    }

    snapshot() {
        return {
            version: this.version,
            state: clone(this.state)
        };
    }

    apply(expectedVersion, newState) {
        if (expectedVersion !== this.version) {
            throw new ConcurrencyError(
                `Expected version ${expectedVersion}; ` +
                `actual version ${this.version}.`
            );
        }

        this.state = clone(newState);
        this.version += 1;
    }
}

class Transaction {
    constructor(repository) {
        this.repository = repository;
        this.id = randomUUID();
        this.status = TransactionStatus.ACTIVE;

        const snapshot = repository.snapshot();

        this.baseVersion = snapshot.version;
        this.workingState = snapshot.state;
        this.savepoints = [];

        this.journal = repository.journal;
    }

    ensureActive() {
        if (this.status !== TransactionStatus.ACTIVE) {
            throw new TransactionStateError(
                `Transaction is ${this.status}.`
            );
        }
    }

    createSavepoint(name) {
        this.ensureActive();

        if (
            typeof name !== "string" ||
            !/^[A-Za-z_][A-Za-z0-9_]{0,62}$/.test(name)
        ) {
            throw new ValidationError("Invalid savepoint name.");
        }

        this.savepoints.push({
            name,
            snapshot: clone(this.workingState)
        });

        this.journal.record("savepoint", this.id, { name });
    }

    rollbackTo(name) {
        this.ensureActive();

        let index = -1;

        for (let i = this.savepoints.length - 1; i >= 0; i--) {
            if (this.savepoints[i].name === name) {
                index = i;
                break;
            }
        }

        if (index === -1) {
            throw new SavepointError(
                `Savepoint ${name} does not exist.`
            );
        }

        this.workingState = clone(
            this.savepoints[index].snapshot
        );

        this.savepoints = this.savepoints.slice(0, index + 1);

        this.journal.record("rollback_to", this.id, { name });
    }

    release(name) {
        this.ensureActive();

        let index = -1;

        for (let i = this.savepoints.length - 1; i >= 0; i--) {
            if (this.savepoints[i].name === name) {
                index = i;
                break;
            }
        }

        if (index === -1) {
            throw new SavepointError(
                `Savepoint ${name} does not exist.`
            );
        }

        this.savepoints = this.savepoints.slice(0, index);

        this.journal.record("release", this.id, { name });
    }

    async execute(operation) {
        this.ensureActive();

        if (typeof operation !== "function") {
            throw new ValidationError(
                "Operation must be a function."
            );
        }

        return await operation(this);
    }

    addOrder(accountId, productId, quantity) {
        this.ensureActive();

        if (!Number.isSafeInteger(quantity) || quantity <= 0) {
            throw new ValidationError("Invalid quantity.");
        }

        const account = this.workingState.accounts.get(accountId);
        const product = this.workingState.products.get(productId);

        if (!account || !product) {
            throw new ValidationError(
                "Account or product does not exist."
            );
        }

        if (product.stock < quantity) {
            throw new TransactionError(
                "Insufficient inventory."
            );
        }

        const amount = product.pricePaise * quantity;

        validateMoney(amount);

        if (account.balancePaise < amount) {
            throw new TransactionError(
                "Insufficient account balance."
            );
        }

        product.stock -= quantity;
        account.balancePaise -= amount;

        const order = Object.freeze({
            id: this.workingState.nextOrderId++,
            accountId,
            productId,
            quantity,
            amountPaise: amount,
            status: "CONFIRMED"
        });

        this.workingState.orders.set(order.id, order);

        this.journal.record("order_created", this.id, {
            orderId: order.id,
            amountPaise: amount
        });

        return order;
    }

    async commit() {
        this.ensureActive();

        // Version validation prevents lost updates in this
        // in-memory optimistic concurrency model.
        this.repository.apply(
            this.baseVersion,
            this.workingState
        );

        this.savepoints = [];
        this.status = TransactionStatus.COMMITTED;

        this.journal.record("commit", this.id);
    }

    rollback() {
        this.ensureActive();

        this.savepoints = [];
        this.status = TransactionStatus.ROLLED_BACK;

        this.journal.record("rollback", this.id);
    }
}

class TransactionManager {
    constructor(repository) {
        this.repository = repository;
    }

    async run(callback) {
        const transaction = this.repository.begin();

        try {
            const result = await callback(transaction);
            await transaction.commit();
            return result;
        } catch (error) {
            if (transaction.status === TransactionStatus.ACTIVE) {
                transaction.rollback();
            }

            throw error;
        }
    }

    async nested(transaction, name, callback) {
        transaction.ensureActive();
        transaction.createSavepoint(name);

        try {
            const result = await callback(transaction);

            transaction.release(name);
            return result;
        } catch (error) {
            transaction.rollbackTo(name);
            throw error;
        }
    }
}

async function runDemonstrations() {
    const repository = new Repository();
    repository.journal = new EventJournal();

    const manager = new TransactionManager(repository);

    repository.journal.on("commit", event => {
        console.log("Committed:", event.transactionId);
    });

    console.log("\n1. PARTIAL ROLLBACK");

    await manager.run(async tx => {
        tx.createSavepoint("before_optional");

        tx.addOrder(1, 101, 1);

        try {
            await manager.nested(tx, "optional_items", async inner => {
                inner.addOrder(1, 103, 1);

                // Force an optional operation to fail.
                inner.addOrder(1, 103, 100);
            });
        } catch (error) {
            console.log("Optional operation failed:", error.message);
        }

        // The first order remains available.
        assert.equal(tx.workingState.orders.size, 1);
    });

    console.log("\n2. SUCCESSFUL NESTED OPERATION");

    await manager.run(async tx => {
        tx.addOrder(1, 102, 2);

        await manager.nested(tx, "optional_service", async inner => {
            inner.addOrder(1, 103, 1);
        });
    });

    console.log("\n3. FULL ROLLBACK");

    const failed = repository.begin();

    failed.addOrder(1, 102, 1);
    failed.rollback();

    console.log("Status:", failed.status);

    console.log("\n4. CONCURRENCY CONFLICT");

    const first = repository.begin();
    const second = repository.begin();

    first.addOrder(1, 102, 1);
    second.addOrder(1, 102, 1);

    await first.commit();

    try {
        await second.commit();
    } catch (error) {
        console.log("Conflict detected:", error.message);

        if (second.status === TransactionStatus.ACTIVE) {
            second.rollback();
        }
    }

    console.log("\n5. DATABASE STATE");

    const state = repository.read();

    console.log("Repository version:", repository.version);
    console.log("Committed orders:", state.orders.size);

    for (const [id, product] of state.products) {
        console.log(
            `Product ${id}: ${product.name}, stock=${product.stock}`
        );
    }

    console.log("\n6. EVENT JOURNAL");

    for (const event of repository.journal.events) {
        console.log(event.type, event.transactionId);
    }

    console.log("\nALL ASSERTIONS PASSED");
}

async function main() {
    try {
        await runDemonstrations();
    } catch (error) {
        console.error("Fatal error:", error);
        process.exitCode = 1;
    }
}

main();
