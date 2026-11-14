"use strict";

/*
 * Transaction Isolation and Concurrency Control
 *
 * Event-driven in-memory transaction engine.
 * Implements snapshot visibility, transaction-local writes,
 * isolation policies, optimistic conflict detection and
 * retry handling.
 *
 * Runtime: Node.js 18+
 * Dependencies: None
 */

const { EventEmitter } = require("node:events");
const crypto = require("node:crypto");

const Isolation = Object.freeze({
    READ_UNCOMMITTED: "READ_UNCOMMITTED",
    READ_COMMITTED: "READ_COMMITTED",
    REPEATABLE_READ: "REPEATABLE_READ",
    SERIALIZABLE: "SERIALIZABLE"
});

const State = Object.freeze({
    ACTIVE: "ACTIVE",
    COMMITTED: "COMMITTED",
    ROLLED_BACK: "ROLLED_BACK",
    ABORTED: "ABORTED"
});

class TransactionError extends Error {}
class WriteConflict extends TransactionError {}
class SerializationFailure extends TransactionError {}
class InvalidState extends TransactionError {}
class RecordNotFound extends TransactionError {}

function validateIsolation(level) {
    if (!Object.values(Isolation).includes(level)) {
        throw new TypeError(`Unsupported isolation level: ${level}`);
    }
}

function clone(value) {
    return structuredClone(value);
}

class VersionedStore extends EventEmitter {
    constructor() {
        super();
        this.tables = new Map();
        this.revision = 0;
        this.transactions = new Map();
        this.sequence = 1;
    }

    createTable(name) {
        if (typeof name !== "string" || !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) {
            throw new TypeError("Invalid table name");
        }

        if (this.tables.has(name)) {
            throw new Error(`Table already exists: ${name}`);
        }

        this.tables.set(name, new Map());
    }

    seed(table, key, value) {
        const records = this.tables.get(table);

        if (!records) {
            throw new Error(`Unknown table: ${table}`);
        }

        if (records.has(key)) {
            throw new WriteConflict(`Duplicate key: ${key}`);
        }

        this.revision++;
        records.set(key, [{
            value: clone(value),
            revision: this.revision,
            committed: true
        }]);
    }

    begin(isolation = Isolation.READ_COMMITTED) {
        validateIsolation(isolation);

        const transaction = {
            id: this.sequence++,
            isolation,
            snapshot: this.revision,
            state: State.ACTIVE,
            writes: new Map(),
            reads: new Map(),
            scans: new Set()
        };

        this.transactions.set(transaction.id, transaction);

        this.emit("transactionStarted", {
            id: transaction.id,
            isolation,
            snapshot: transaction.snapshot
        });

        return transaction;
    }

    assertActive(transaction) {
        if (
            !transaction ||
            transaction.state !== State.ACTIVE ||
            this.transactions.get(transaction.id) !== transaction
        ) {
            throw new InvalidState("Transaction is not active");
        }
    }

    key(table, id) {
        return `${table}\u0000${String(id)}`;
    }

    getVisibleVersion(transaction, table, id) {
        const versions = this.tables.get(table)?.get(id);

        if (!versions) {
            return null;
        }

        const visible = versions.filter(version =>
            version.committed &&
            (
                transaction.isolation === Isolation.READ_COMMITTED ||
                version.revision <= transaction.snapshot
            )
        );

        return visible.length
            ? visible.reduce((a, b) =>
                a.revision > b.revision ? a : b
            )
            : null;
    }

    read(transaction, table, id) {
        this.assertActive(transaction);

        const records = this.tables.get(table);

        if (!records) {
            throw new Error(`Unknown table: ${table}`);
        }

        const writeKey = this.key(table, id);

        if (transaction.writes.has(writeKey)) {
            return clone(transaction.writes.get(writeKey).value);
        }

        const version = this.getVisibleVersion(
            transaction,
            table,
            id
        );

        if (!version) {
            throw new RecordNotFound(`${table}[${id}] not found`);
        }

        transaction.reads.set(writeKey, version.revision);

        return clone(version.value);
    }

    scan(transaction, table, predicate = () => true) {
        this.assertActive(transaction);

        const records = this.tables.get(table);

        if (!records) {
            throw new Error(`Unknown table: ${table}`);
        }

        transaction.scans.add(table);
        const output = new Map();

        for (const id of records.keys()) {
            try {
                const value = this.read(transaction, table, id);
                if (predicate(value, id)) {
                    output.set(id, value);
                }
            } catch (error) {
                if (!(error instanceof RecordNotFound)) {
                    throw error;
                }
            }
        }

        // Include transaction-local inserts and updates.
        for (const entry of transaction.writes.values()) {
            if (
                entry.table === table &&
                predicate(entry.value, entry.id)
            ) {
                output.set(entry.id, clone(entry.value));
            }
        }

        return output;
    }

    write(transaction, table, id, value) {
        this.assertActive(transaction);

        if (!this.tables.has(table)) {
            throw new Error(`Unknown table: ${table}`);
        }

        if (id === undefined || id === null) {
            throw new TypeError("Primary key is required");
        }

        const writeKey = this.key(table, id);

        transaction.writes.set(writeKey, {
            table,
            id,
            value: clone(value)
        });

        this.emit("writeStaged", {
            transactionId: transaction.id,
            table,
            id
        });
    }

    update(transaction, table, id, updater) {
        if (typeof updater !== "function") {
            throw new TypeError("Updater must be a function");
        }

        const current = this.read(transaction, table, id);
        const updated = updater(clone(current));

        if (updated === undefined) {
            throw new TypeError("Updater must return a value");
        }

        this.write(transaction, table, id, updated);
    }

    validate(transaction) {
        for (const entry of transaction.writes.values()) {
            const versions = this.tables
                .get(entry.table)
                .get(entry.id) || [];

            const latest = versions
                .filter(v => v.committed)
                .reduce((maximum, v) => Math.max(maximum, v.revision), 0);

            if (
                transaction.isolation !== Isolation.READ_COMMITTED &&
                latest > transaction.snapshot
            ) {
                throw new WriteConflict(
                    `Write conflict on ${entry.table}[${entry.id}]`
                );
            }
        }

        if (transaction.isolation === Isolation.SERIALIZABLE) {
            for (const [key, observedRevision] of transaction.reads) {
                const separator = key.indexOf("\u0000");
                const table = key.slice(0, separator);
                const id = key.slice(separator + 1);

                const versions = this.tables.get(table).get(id) || [];

                const latest = versions
                    .filter(v => v.committed)
                    .reduce((maximum, v) => Math.max(maximum, v.revision), 0);

                if (
                    latest > transaction.snapshot &&
                    latest !== observedRevision
                ) {
                    throw new SerializationFailure(
                        `Read-write conflict on ${table}[${id}]`
                    );
                }
            }

            // Conservative predicate validation.
            for (const table of transaction.scans) {
                for (const versions of this.tables.get(table).values()) {
                    if (versions.some(v =>
                        v.committed &&
                        v.revision > transaction.snapshot
                    )) {
                        throw new SerializationFailure(
                            `Predicate conflict on ${table}`
                        );
                    }
                }
            }
        }
    }

    commit(transaction) {
        this.assertActive(transaction);

        try {
            this.validate(transaction);

            this.revision++;

            for (const entry of transaction.writes.values()) {
                const records = this.tables.get(entry.table);

                if (!records.has(entry.id)) {
                    records.set(entry.id, []);
                }

                records.get(entry.id).push({
                    value: clone(entry.value),
                    revision: this.revision,
                    committed: true
                });
            }

            transaction.state = State.COMMITTED;
            this.transactions.delete(transaction.id);

            const event = {
                transactionId: transaction.id,
                revision: this.revision,
                writeCount: transaction.writes.size
            };

            this.emit("transactionCommitted", event);
            return event;
        } catch (error) {
            transaction.state = State.ABORTED;
            transaction.writes.clear();
            this.transactions.delete(transaction.id);

            this.emit("transactionAborted", {
                transactionId: transaction.id,
                reason: error.message
            });

            throw error;
        }
    }

    rollback(transaction) {
        this.assertActive(transaction);

        transaction.writes.clear();
        transaction.state = State.ROLLED_BACK;
        this.transactions.delete(transaction.id);

        this.emit("transactionRolledBack", {
            transactionId: transaction.id
        });
    }

    currentValue(table, id) {
        const versions = this.tables.get(table)?.get(id);

        if (!versions) {
            throw new RecordNotFound(`${table}[${id}] not found`);
        }

        const committed = versions.filter(v => v.committed);

        return clone(
            committed.reduce((a, b) =>
                a.revision > b.revision ? a : b
            ).value
        );
    }
}

class RetryPolicy {
    constructor(maxAttempts = 3, baseDelayMs = 10) {
        if (!Number.isInteger(maxAttempts) || maxAttempts < 1) {
            throw new RangeError("maxAttempts must be positive");
        }

        this.maxAttempts = maxAttempts;
        this.baseDelayMs = baseDelayMs;
    }

    async execute(operation) {
        for (let attempt = 1; attempt <= this.maxAttempts; attempt++) {
            try {
                return await operation(attempt);
            } catch (error) {
                const retryable =
                    error instanceof SerializationFailure ||
                    error instanceof WriteConflict;

                if (!retryable || attempt === this.maxAttempts) {
                    throw error;
                }

                // Jitter reduces repeated collision between retrying workers.
                const delay = this.baseDelayMs * (2 ** (attempt - 1));
                const jitter = crypto.randomInt(0, Math.max(2, delay));

                await new Promise(resolve =>
                    setTimeout(resolve, delay + jitter)
                );
            }
        }
    }
}

async function runDemonstrations() {
    const store = new VersionedStore();

    store.on("transactionStarted", event =>
        console.log("START:", event)
    );

    store.on("transactionCommitted", event =>
        console.log("COMMIT:", event)
    );

    store.on("transactionAborted", event =>
        console.log("ABORT:", event)
    );

    store.createTable("accounts");
    store.seed("accounts", 101, { balance: 5000 });
    store.seed("accounts", 102, { balance: 3000 });

    console.log("\n1. READ COMMITTED");

    const reader = store.begin(Isolation.READ_COMMITTED);
    const writer = store.begin(Isolation.READ_COMMITTED);

    console.log("Initial:", store.read(reader, "accounts", 101));

    store.update(writer, "accounts", 101, account => ({
        ...account,
        balance: 4500
    }));

    store.commit(writer);

    console.log("After another commit:", store.read(reader, "accounts", 101));
    store.rollback(reader);

    console.log("\n2. REPEATABLE READ");

    const snapshotReader = store.begin(Isolation.REPEATABLE_READ);
    const concurrentWriter = store.begin(Isolation.READ_COMMITTED);

    console.log("Initial:", store.read(snapshotReader, "accounts", 102));

    store.update(concurrentWriter, "accounts", 102, account => ({
        ...account,
        balance: 2500
    }));

    store.commit(concurrentWriter);

    console.log(
        "Snapshot read:",
        store.read(snapshotReader, "accounts", 102)
    );

    store.rollback(snapshotReader);

    console.log("\n3. READ UNCOMMITTED");

    const uncommittedReader = store.begin(Isolation.READ_UNCOMMITTED);
    const uncommittedWriter = store.begin(Isolation.READ_COMMITTED);

    store.update(uncommittedWriter, "accounts", 101, account => ({
        ...account,
        balance: 100
    }));

    console.log(
        "Dirty read prevented:",
        store.read(uncommittedReader, "accounts", 101)
    );

    store.rollback(uncommittedWriter);
    store.rollback(uncommittedReader);

    console.log("\n4. SERIALIZABLE");

    const serialReader = store.begin(Isolation.SERIALIZABLE);
    const serialWriter = store.begin(Isolation.READ_COMMITTED);

    store.read(serialReader, "accounts", 101);

    store.update(serialWriter, "accounts", 101, account => ({
        ...account,
        balance: account.balance + 100
    }));

    store.commit(serialWriter);

    try {
        store.commit(serialReader);
    } catch (error) {
        console.log("Expected conflict:", error.message);
    }

    console.log("\n5. Atomic business operation");

    const retryPolicy = new RetryPolicy(3, 5);

    await retryPolicy.execute(async () => {
        const transaction = store.begin(Isolation.SERIALIZABLE);

        try {
            const source = store.read(transaction, "accounts", 101);
            const destination = store.read(transaction, "accounts", 102);

            const amount = 200;

            if (source.balance < amount) {
                throw new RangeError("Insufficient funds");
            }

            store.write(transaction, "accounts", 101, {
                balance: source.balance - amount
            });

            store.write(transaction, "accounts", 102, {
                balance: destination.balance + amount
            });

            store.commit(transaction);
        } catch (error) {
            if (transaction.state === State.ACTIVE) {
                store.rollback(transaction);
            }
            throw error;
        }
    });

    console.log("\nFinal accounts:");

    console.log("101:", store.currentValue("accounts", 101));
    console.log("102:", store.currentValue("accounts", 102));

    console.log("\n6. Predicate query");

    const report = store.begin(Isolation.REPEATABLE_READ);

    const wealthyAccounts = store.scan(
        report,
        "accounts",
        account => account.balance >= 1000
    );

    console.log("Accounts with balance >= 1000:", wealthyAccounts.size);

    store.rollback(report);
}

async function main() {
    try {
        await runDemonstrations();
        console.log("\nExecution completed.");
    } catch (error) {
        console.error("Execution failed:", error.message);
        process.exitCode = 1;
    }
}

if (require.main === module) {
    main();
}

module.exports = {
    Isolation,
    State,
    VersionedStore,
    RetryPolicy,
    TransactionError,
    WriteConflict,
    SerializationFailure
};
