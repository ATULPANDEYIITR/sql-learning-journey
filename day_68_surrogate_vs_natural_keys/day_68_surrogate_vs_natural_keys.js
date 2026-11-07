"use strict";

const { randomUUID } = require("node:crypto");
const { EventEmitter } = require("node:events");

class ValidationError extends Error {}
class DuplicateKeyError extends Error {}
class NotFoundError extends Error {}
class ReferentialIntegrityError extends Error {}

const KeyType = Object.freeze({
    IDENTITY: "IDENTITY",
    UUID: "UUID",
    NATURAL: "NATURAL"
});

class IdentifierValidator {
    static email(value) {
        if (typeof value !== "string") {
            throw new ValidationError("Email must be a string.");
        }

        const normalized = value.trim().toLowerCase();

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) {
            throw new ValidationError("Invalid email.");
        }

        return normalized;
    }

    static country(value) {
        if (typeof value !== "string" ||
            !/^[A-Za-z]{2}$/.test(value.trim())) {
            throw new ValidationError("Invalid country code.");
        }

        return value.trim().toUpperCase();
    }

    static requiredString(value, field) {
        if (typeof value !== "string" || !value.trim()) {
            throw new ValidationError(`${field} is required.`);
        }

        return value.trim();
    }
}

class Customer {
    constructor({ id, uuid, email, name, country, externalReference }) {
        this.id = id;
        this.uuid = uuid;
        this.email = email;
        this.name = name;
        this.country = country;
        this.externalReference = externalReference;
        Object.seal(this);
    }
}

class CustomerService extends EventEmitter {
    #nextId = 1;
    #customers = new Map();
    #uuidIndex = new Map();
    #emailIndex = new Map();
    #externalIndex = new Map();

    create(input) {
        const email = IdentifierValidator.email(input.email);
        const name = IdentifierValidator.requiredString(
            input.name,
            "Customer name"
        );
        const country = IdentifierValidator.country(input.country);

        const externalReference = input.externalReference == null
            ? null
            : IdentifierValidator.requiredString(
                input.externalReference,
                "External reference"
            );

        if (this.#emailIndex.has(email)) {
            throw new DuplicateKeyError("Email already exists.");
        }

        if (externalReference &&
            this.#externalIndex.has(externalReference)) {
            throw new DuplicateKeyError("External reference already exists.");
        }

        const customer = new Customer({
            id: this.#nextId,
            uuid: randomUUID(),
            email,
            name,
            country,
            externalReference
        });

        // All uniqueness checks happen before modifying repository state.
        this.#customers.set(customer.id, customer);
        this.#uuidIndex.set(customer.uuid, customer.id);
        this.#emailIndex.set(email, customer.id);

        if (externalReference) {
            this.#externalIndex.set(externalReference, customer.id);
        }

        this.#nextId++;

        this.emit("customerCreated", {
            id: customer.id,
            uuid: customer.uuid
        });

        return customer;
    }

    getById(id) {
        if (!Number.isSafeInteger(id) || id <= 0) {
            throw new ValidationError("Invalid identity value.");
        }

        const customer = this.#customers.get(id);

        if (!customer) {
            throw new NotFoundError(`Customer ${id} not found.`);
        }

        return customer;
    }

    getByUuid(uuid) {
        if (typeof uuid !== "string") {
            throw new ValidationError("UUID must be a string.");
        }

        const id = this.#uuidIndex.get(uuid);

        if (id === undefined) {
            throw new NotFoundError("UUID not found.");
        }

        return this.getById(id);
    }

    getByEmail(email) {
        const normalized = IdentifierValidator.email(email);
        const id = this.#emailIndex.get(normalized);

        if (id === undefined) {
            throw new NotFoundError("Email not found.");
        }

        return this.getById(id);
    }

    updateEmail(id, newEmail) {
        const customer = this.getById(id);
        const normalized = IdentifierValidator.email(newEmail);

        const existingId = this.#emailIndex.get(normalized);

        if (existingId !== undefined && existingId !== id) {
            throw new DuplicateKeyError("Email already assigned.");
        }

        const previousEmail = customer.email;

        // Email changes do not modify surrogate identifiers.
        this.#emailIndex.delete(previousEmail);
        customer.email = normalized;
        this.#emailIndex.set(normalized, id);

        this.emit("customerEmailChanged", {
            id,
            previousEmail,
            newEmail: normalized
        });

        return customer;
    }

    delete(id) {
        const customer = this.getById(id);

        this.#customers.delete(id);
        this.#uuidIndex.delete(customer.uuid);
        this.#emailIndex.delete(customer.email);

        if (customer.externalReference) {
            this.#externalIndex.delete(customer.externalReference);
        }

        this.emit("customerDeleted", { id });
    }

    list() {
        return Array.from(this.#customers.values());
    }

    get size() {
        return this.#customers.size;
    }
}

class NaturalKeyRegistry {
    #records = new Map();

    register(country, identifier, name) {
        const normalizedCountry = IdentifierValidator.country(country);
        const normalizedIdentifier = IdentifierValidator.requiredString(
            identifier,
            "Natural identifier"
        );
        const normalizedName = IdentifierValidator.requiredString(
            name,
            "Name"
        );

        if (!/^[A-Za-z0-9-]{4,40}$/.test(normalizedIdentifier)) {
            throw new ValidationError("Invalid natural identifier.");
        }

        // JSON tuple encoding avoids ambiguous string concatenation.
        const compositeKey = JSON.stringify([
            normalizedCountry,
            normalizedIdentifier
        ]);

        if (this.#records.has(compositeKey)) {
            throw new DuplicateKeyError("Natural key already exists.");
        }

        const record = Object.freeze({
            country: normalizedCountry,
            identifier: normalizedIdentifier,
            name: normalizedName
        });

        this.#records.set(compositeKey, record);
        return record;
    }

    find(country, identifier) {
        const key = JSON.stringify([
            IdentifierValidator.country(country),
            identifier.trim()
        ]);

        const record = this.#records.get(key);

        if (!record) {
            throw new NotFoundError("Natural key not found.");
        }

        return record;
    }

    get size() {
        return this.#records.size;
    }
}

class KeyPolicy {
    static describe(type) {
        const policies = {
            [KeyType.IDENTITY]: {
                purpose: "Internal relational identification",
                generation: "Database sequence",
                storage: "Compact integer",
                distribution: "Coordinated allocation",
                mutable: false
            },
            [KeyType.UUID]: {
                purpose: "Distributed and public identification",
                generation: "Cryptographically random UUID",
                storage: "128-bit identifier",
                distribution: "Independent generation",
                mutable: false
            },
            [KeyType.NATURAL]: {
                purpose: "Business identification",
                generation: "Existing business attributes",
                storage: "Depends on attributes",
                distribution: "Business uniqueness enforcement",
                mutable: true
            }
        };

        if (!policies[type]) {
            throw new ValidationError("Unsupported key type.");
        }

        return Object.freeze({ ...policies[type] });
    }
}

class OrderService {
    #nextOrderId = 1;
    #orders = new Map();
    #customers;

    constructor(customers) {
        this.#customers = customers;
    }

    createOrder(customerId, amount) {
        // Foreign references use the stable internal customer identifier.
        const customer = this.#customers.getById(customerId);

        if (!Number.isFinite(amount) || amount <= 0) {
            throw new ValidationError("Order amount must be positive.");
        }

        const order = Object.freeze({
            orderId: this.#nextOrderId++,
            customerId: customer.id,
            customerUuid: customer.uuid,
            amount,
            status: "CREATED",
            createdAt: new Date().toISOString()
        });

        this.#orders.set(order.orderId, order);
        return order;
    }

    findByCustomer(customerId) {
        this.#customers.getById(customerId);

        return Array.from(this.#orders.values())
            .filter(order => order.customerId === customerId);
    }
}

async function executeWithRetry(operation, attempts = 3) {
    if (!Number.isInteger(attempts) || attempts < 1) {
        throw new ValidationError("Attempts must be positive.");
    }

    let lastError;

    for (let attempt = 1; attempt <= attempts; attempt++) {
        try {
            return await operation();
        } catch (error) {
            lastError = error;

            if (error instanceof ValidationError ||
                error instanceof DuplicateKeyError ||
                error instanceof NotFoundError) {
                throw error;
            }

            if (attempt === attempts) {
                break;
            }

            await new Promise(resolve =>
                setTimeout(resolve, attempt * 100)
            );
        }
    }

    throw lastError;
}

async function main() {
    console.log("SURROGATE VS NATURAL KEYS");
    console.log("=".repeat(55));

    const customers = new CustomerService();
    const naturalKeys = new NaturalKeyRegistry();

    customers.on("customerCreated", event => {
        console.log("EVENT customerCreated:", event);
    });

    customers.on("customerEmailChanged", event => {
        console.log("EVENT customerEmailChanged:", event);
    });

    const alice = customers.create({
        email: "alice@example.com",
        name: "Alice Sharma",
        country: "IN",
        externalReference: "ERP-1001"
    });

    const bob = customers.create({
        email: "bob@example.com",
        name: "Bob Verma",
        country: "IN",
        externalReference: "ERP-1002"
    });

    console.log("\n1. Generated identifiers");

    for (const customer of customers.list()) {
        console.log({
            identity: customer.id,
            uuid: customer.uuid,
            email: customer.email
        });
    }

    console.log("\n2. Natural key lookup");
    console.log(customers.getByEmail("ALICE@EXAMPLE.COM"));

    console.log("\n3. Updating mutable natural attributes");

    customers.updateEmail(
        alice.id,
        "alice.sharma@example.com"
    );

    console.log("Internal ID unchanged:", alice.id);
    console.log("UUID unchanged:", alice.uuid);

    console.log("\n4. Composite natural identifiers");

    naturalKeys.register("IN", "TAX-1001", "Enterprise India");
    naturalKeys.register("US", "TAX-1001", "Enterprise USA");

    console.log("Distinct composite keys:", naturalKeys.size);

    console.log("\n5. Referential integrity");

    const orders = new OrderService(customers);

    console.log(orders.createOrder(alice.id, 25000));
    console.log(orders.createOrder(bob.id, 45000));

    console.log(
        "Alice orders:",
        orders.findByCustomer(alice.id)
    );

    console.log("\n6. Duplicate natural key handling");

    try {
        naturalKeys.register("IN", "TAX-1001", "Duplicate");
    } catch (error) {
        console.log("Rejected:", error.message);
    }

    console.log("\n7. Key policy comparison");

    for (const type of Object.values(KeyType)) {
        console.log(type, KeyPolicy.describe(type));
    }

    console.log("\n8. Asynchronous operation");

    const result = await executeWithRetry(
        async () => customers.getByUuid(alice.uuid)
    );

    console.log("Retrieved asynchronously:", result.name);

    console.log("\n9. Missing identifier handling");

    try {
        customers.getById(999);
    } catch (error) {
        console.log("Handled:", error.message);
    }

    console.log("\n10. Final record count:", customers.size);
}

main().catch(error => {
    console.error("Application failure:", error.message);
    process.exitCode = 1;
});
