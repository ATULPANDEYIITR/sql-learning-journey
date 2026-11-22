"use strict";

/*
 * Unique Indexes: Event-Driven Uniqueness and Policy Evaluation
 *
 * Demonstrates:
 * - Hash-based unique indexes
 * - Composite index keys
 * - Partial unique indexes
 * - Normalized expression keys
 * - Atomic in-memory writes
 * - Asynchronous concurrent insert attempts
 * - Index maintenance and integrity auditing
 * - Event-driven conflict reporting
 *
 * Runtime: Node.js 18+
 */

const { EventEmitter } = require("node:events");

class UniqueViolation extends Error {
    constructor(indexName, key) {
        super(`Unique index ${indexName} rejected key ${key}`);
        this.name = "UniqueViolation";
        this.indexName = indexName;
        this.key = key;
    }
}

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

function normalize(value) {
    if (typeof value !== "string") {
        throw new ValidationError("Expected a string");
    }

    const normalized = value.trim().toLowerCase();

    if (!normalized) {
        throw new ValidationError("Empty values are not permitted");
    }

    return normalized;
}

function encodeKey(parts) {
    // JSON encoding avoids ambiguous delimiter-based composite keys.
    return JSON.stringify(parts);
}

class UniqueIndex {
    constructor({ name, keyFunction, predicate = () => true }) {
        this.name = name;
        this.keyFunction = keyFunction;
        this.predicate = predicate;
        this.entries = new Map();
    }

    getKey(record) {
        if (!this.predicate(record)) {
            return null;
        }

        const parts = this.keyFunction(record);

        if (!Array.isArray(parts)) {
            throw new ValidationError(
                `Index ${this.name} must return an array key`
            );
        }

        // This example models NULLS DISTINCT behavior.
        if (parts.some(value => value === null || value === undefined)) {
            return null;
        }

        return encodeKey(parts);
    }

    validate(record, ignoredId = null) {
        const key = this.getKey(record);

        if (key === null) return;

        const existingId = this.entries.get(key);

        if (existingId !== undefined && existingId !== ignoredId) {
            throw new UniqueViolation(this.name, key);
        }
    }

    add(record) {
        const key = this.getKey(record);

        if (key !== null) {
            this.entries.set(key, record.id);
        }
    }

    remove(record) {
        const key = this.getKey(record);

        if (key !== null && this.entries.get(key) === record.id) {
            this.entries.delete(key);
        }
    }

    lookup(parts) {
        return this.entries.get(encodeKey(parts));
    }
}

class Repository extends EventEmitter {
    constructor() {
        super();

        this.records = new Map();
        this.nextId = 1;

        this.indexes = [
            new UniqueIndex({
                name: "uq_accounts_email",
                keyFunction: record => [normalize(record.email)]
            }),

            new UniqueIndex({
                name: "uq_accounts_tenant_username",
                keyFunction: record => [
                    record.tenantId,
                    normalize(record.username)
                ]
            }),

            new UniqueIndex({
                name: "uq_active_accounts_email",
                keyFunction: record => [normalize(record.email)],
                predicate: record => record.active
            })
        ];
    }

    validateRecord(input) {
        if (!Number.isSafeInteger(input.tenantId) || input.tenantId <= 0) {
            throw new ValidationError("Invalid tenant identifier");
        }

        if (!input.email || !input.email.includes("@")) {
            throw new ValidationError("Invalid email address");
        }

        if (!input.username || !input.username.trim()) {
            throw new ValidationError("Username is required");
        }

        return {
            tenantId: input.tenantId,
            email: input.email.trim(),
            username: input.username.trim(),
            active: input.active !== false
        };
    }

    insert(input) {
        const data = this.validateRecord(input);

        const record = {
            id: this.nextId,
            ...data
        };

        // All indexes are checked before any state is modified.
        for (const index of this.indexes) {
            index.validate(record);
        }

        this.records.set(record.id, record);

        for (const index of this.indexes) {
            index.add(record);
        }

        this.nextId++;

        this.emit("inserted", Object.freeze({ ...record }));

        return Object.freeze({ ...record });
    }

    update(id, changes) {
        const previous = this.records.get(id);

        if (!previous) {
            throw new ValidationError("Record does not exist");
        }

        const candidate = {
            ...previous,
            ...this.validateRecord({
                ...previous,
                ...changes
            }),
            id
        };

        for (const index of this.indexes) {
            index.validate(candidate, id);
        }

        // Remove old index keys only after validation succeeds.
        for (const index of this.indexes) {
            index.remove(previous);
        }

        this.records.set(id, candidate);

        for (const index of this.indexes) {
            index.add(candidate);
        }

        this.emit("updated", Object.freeze({ ...candidate }));

        return Object.freeze({ ...candidate });
    }

    deactivate(id) {
        return this.update(id, { active: false });
    }

    findByEmail(email) {
        const id = this.indexes[0].lookup([normalize(email)]);

        return id === undefined
            ? null
            : Object.freeze({ ...this.records.get(id) });
    }

    audit() {
        const rebuilt = this.indexes.map(index => new UniqueIndex({
            name: index.name,
            keyFunction: index.keyFunction,
            predicate: index.predicate
        }));

        for (const record of this.records.values()) {
            for (const index of rebuilt) {
                index.validate(record);
                index.add(record);
            }
        }

        return rebuilt.every((index, position) => {
            const original = this.indexes[position].entries;

            if (original.size !== index.entries.size) return false;

            return [...original].every(
                ([key, id]) => index.entries.get(key) === id
            );
        });
    }
}

async function concurrentInsert(repository, input) {
    // JavaScript executes each synchronous insertion section without
    // interleaving at await boundaries. The uniqueness check and write
    // therefore form one atomic event-loop operation in this model.
    await Promise.resolve();

    try {
        return {
            success: true,
            record: repository.insert(input)
        };
    } catch (error) {
        if (error instanceof UniqueViolation) {
            repository.emit("conflict", {
                index: error.indexName,
                key: error.key
            });
        }

        return {
            success: false,
            error: error.message
        };
    }
}

async function main() {
    const repository = new Repository();

    repository.on("inserted", record => {
        console.log("INSERT:", record.id, record.email);
    });

    repository.on("updated", record => {
        console.log("UPDATE:", record.id, "active =", record.active);
    });

    repository.on("conflict", conflict => {
        console.log("CONFLICT:", conflict.index);
    });

    repository.insert({
        tenantId: 10,
        email: "alice@example.com",
        username: "alice"
    });

    repository.insert({
        tenantId: 20,
        email: "bob@example.com",
        username: "alice"
    });

    console.log(
        "Case-insensitive lookup:",
        repository.findByEmail("ALICE@example.com")
    );

    const attempts = await Promise.all([
        concurrentInsert(repository, {
            tenantId: 30,
            email: "charlie@example.com",
            username: "charlie"
        }),
        concurrentInsert(repository, {
            tenantId: 40,
            email: "CHARLIE@example.com",
            username: "charlie2"
        })
    ]);

    console.log("\nConcurrent insert results:");
    console.log(attempts);

    repository.deactivate(1);

    console.log("\nIndex integrity:", repository.audit());

    try {
        repository.insert({
            tenantId: 50,
            email: "alice@example.com",
            username: "new_alice"
        });
    } catch (error) {
        console.log("Expected global uniqueness error:", error.message);
    }

    try {
        repository.insert({
            tenantId: 50,
            email: "invalid-email",
            username: "invalid"
        });
    } catch (error) {
        console.log("Expected validation error:", error.message);
    }
}

main().catch(error => {
    console.error("Fatal execution error:", error);
    process.exitCode = 1;
});
