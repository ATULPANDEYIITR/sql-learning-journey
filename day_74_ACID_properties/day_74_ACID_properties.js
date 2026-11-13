'use strict';

/*
 * ACID Properties: Atomicity, Consistency, Isolation, Durability
 *
 * Event-driven transaction engine for an account ledger.
 *
 * Features:
 * - Promise-based transaction execution.
 * - Atomic staged writes.
 * - Validation policies.
 * - Optimistic concurrency control.
 * - Serializable conflict detection.
 * - Idempotency keys.
 * - Commit event notifications.
 * - Durable append-only journal.
 * - Recovery and operational reporting.
 *
 * Run: node acid_properties.js
 */

const fs = require('node:fs/promises');
const crypto = require('node:crypto');

const Isolation = Object.freeze({
    READ_COMMITTED: 'READ_COMMITTED',
    REPEATABLE_READ: 'REPEATABLE_READ',
    SERIALIZABLE: 'SERIALIZABLE'
});

const State = Object.freeze({
    ACTIVE: 'ACTIVE',
    COMMITTED: 'COMMITTED',
    ROLLED_BACK: 'ROLLED_BACK',
    FAILED: 'FAILED'
});

class TransactionError extends Error {}
class ValidationError extends TransactionError {}
class SerializationError extends TransactionError {}
class DurabilityError extends TransactionError {}

class AsyncMutex {
    constructor() {
        this.locked = false;
        this.queue = [];
    }

    async acquire() {
        return new Promise(resolve => {
            const grant = () => {
                this.locked = true;
                let released = false;

                resolve(() => {
                    if (released) return;
                    released = true;

                    const next = this.queue.shift();

                    if (next) {
                        next();
                    } else {
                        this.locked = false;
                    }
                });
            };

            if (!this.locked) {
                grant();
            } else {
                this.queue.push(grant);
            }
        });
    }
}

class DurableJournal {
    constructor(path) {
        this.path = path;
        this.entries = [];
    }

    async load() {
        try {
            const content = await fs.readFile(this.path, 'utf8');
            const records = JSON.parse(content);

            if (!Array.isArray(records)) {
                throw new Error('Invalid journal format');
            }

            this.entries = records;
        } catch (error) {
            if (error.code === 'ENOENT') {
                this.entries = [];
                return;
            }

            throw new DurabilityError(
                `Cannot load journal: ${error.message}`
            );
        }
    }

    async append(record) {
        const updated = [...this.entries, record];
        const temporary = `${this.path}.${process.pid}.tmp`;

        try {
            const handle = await fs.open(temporary, 'w');

            try {
                await handle.writeFile(
                    JSON.stringify(updated, null, 2),
                    'utf8'
                );
                await handle.sync();
            } finally {
                await handle.close();
            }

            await fs.rename(temporary, this.path);
            this.entries = updated;

        } catch (error) {
            await fs.rm(temporary, { force: true }).catch(() => {});

            throw new DurabilityError(
                `Journal append failed: ${error.message}`
            );
        }
    }
}

class AccountLedger {
    constructor(journal) {
        this.accounts = new Map();
        this.journal = journal;
        this.commitMutex = new AsyncMutex();
        this.listeners = new Map();
        this.idempotency = new Map();
        this.nextId = 1;
    }

    createAccount(owner, initialBalance) {
        if (typeof owner !== 'string' || !owner.trim()) {
            throw new ValidationError('Invalid account owner');
        }

        if (!Number.isSafeInteger(initialBalance) || initialBalance < 0) {
            throw new ValidationError(
                'Balance must be a nonnegative safe integer'
            );
        }

        const id = this.nextId++;

        this.accounts.set(id, {
            id,
            owner: owner.trim(),
            balance: initialBalance,
            version: 0,
            active: true
        });

        return id;
    }

    begin(isolation = Isolation.SERIALIZABLE) {
        if (!Object.values(Isolation).includes(isolation)) {
            throw new ValidationError('Unsupported isolation level');
        }

        return new LedgerTransaction(this, isolation);
    }

    subscribe(eventName, callback) {
        if (typeof callback !== 'function') {
            throw new TypeError('Listener must be a function');
        }

        if (!this.listeners.has(eventName)) {
            this.listeners.set(eventName, new Set());
        }

        this.listeners.get(eventName).add(callback);

        return () => this.listeners.get(eventName)?.delete(callback);
    }

    emit(eventName, event) {
        for (const callback of this.listeners.get(eventName) ?? []) {
            try {
                callback(Object.freeze({ ...event }));
            } catch (error) {
                // An observer failure must not reverse a committed transaction.
                process.stderr.write(
                    `Event listener error: ${error.message}\n`
                );
            }
        }
    }

    async executeTransfer({
        source,
        target,
        amount,
        idempotencyKey
    }) {
        if (!idempotencyKey || typeof idempotencyKey !== 'string') {
            throw new ValidationError('Idempotency key is required');
        }

        const existing = this.idempotency.get(idempotencyKey);

        if (existing) {
            return { ...existing, replayed: true };
        }

        const transaction = this.begin();

        try {
            transaction.transfer(source, target, amount);

            const result = await transaction.commit();

            this.idempotency.set(idempotencyKey, result);

            return { ...result, replayed: false };

        } catch (error) {
            if (transaction.state === State.ACTIVE) {
                transaction.rollback();
            }
            throw error;
        }
    }

    recover() {
        for (const record of this.journal.entries) {
            if (record.type !== 'TRANSFER') continue;

            for (const item of record.accounts) {
                const account = this.accounts.get(item.id);

                if (!account) {
                    throw new DurabilityError(
                        `Missing account ${item.id} during recovery`
                    );
                }

                account.balance = item.balance;
                account.version = item.version;
            }

            if (record.idempotencyKey) {
                this.idempotency.set(
                    record.idempotencyKey,
                    record.result
                );
            }
        }
    }

    report() {
        return [...this.accounts.values()].map(account => ({
            ...account
        }));
    }
}

class LedgerTransaction {
    constructor(ledger, isolation) {
        this.ledger = ledger;
        this.isolation = isolation;
        this.id = crypto.randomUUID();
        this.state = State.ACTIVE;
        this.readSet = new Map();
        this.writeSet = new Map();
        this.operations = [];
    }

    assertActive() {
        if (this.state !== State.ACTIVE) {
            throw new TransactionError(
                `Transaction is ${this.state}`
            );
        }
    }

    read(accountId) {
        this.assertActive();

        const account = this.ledger.accounts.get(accountId);

        if (!account || !account.active) {
            throw new ValidationError('Account is unavailable');
        }

        if (this.writeSet.has(accountId)) {
            return this.writeSet.get(accountId).balance;
        }

        if (
            this.isolation !== Isolation.READ_COMMITTED &&
            this.readSet.has(accountId)
        ) {
            return this.readSet.get(accountId).balance;
        }

        this.readSet.set(accountId, {
            balance: account.balance,
            version: account.version
        });

        return account.balance;
    }

    transfer(sourceId, targetId, amount) {
        this.assertActive();

        if (sourceId === targetId) {
            throw new ValidationError('Accounts must differ');
        }

        if (!Number.isSafeInteger(amount) || amount <= 0) {
            throw new ValidationError('Amount must be a positive integer');
        }

        const source = this.ledger.accounts.get(sourceId);
        const target = this.ledger.accounts.get(targetId);

        if (!source || !target || !source.active || !target.active) {
            throw new ValidationError('Invalid transfer accounts');
        }

        const sourceBalance = this.read(sourceId);
        const targetBalance = this.read(targetId);

        if (sourceBalance < amount) {
            throw new ValidationError('Insufficient funds');
        }

        this.writeSet.set(sourceId, {
            balance: sourceBalance - amount,
            expectedVersion: source.version
        });

        this.writeSet.set(targetId, {
            balance: targetBalance + amount,
            expectedVersion: target.version
        });

        this.operations.push({
            type: 'TRANSFER',
            sourceId,
            targetId,
            amount
        });
    }

    async commit(idempotencyKey = null) {
        this.assertActive();

        const release = await this.ledger.commitMutex.acquire();

        try {
            // Validate the read set before publishing any writes.
            if (
                this.isolation === Isolation.SERIALIZABLE ||
                this.isolation === Isolation.REPEATABLE_READ
            ) {
                for (const [id, snapshot] of this.readSet) {
                    const current = this.ledger.accounts.get(id);

                    if (!current || current.version !== snapshot.version) {
                        throw new SerializationError(
                            `Concurrent modification of account ${id}`
                        );
                    }
                }
            }

            const totalBefore = [...this.ledger.accounts.values()]
                .filter(a => a.active)
                .reduce((sum, a) => sum + a.balance, 0);

            const projected = new Map(
                [...this.ledger.accounts].map(([id, account]) => [
                    id,
                    account.balance
                ])
            );

            for (const [id, change] of this.writeSet) {
                const current = this.ledger.accounts.get(id);

                if (current.version !== change.expectedVersion) {
                    throw new SerializationError(
                        `Write conflict on account ${id}`
                    );
                }

                if (
                    !Number.isSafeInteger(change.balance) ||
                    change.balance < 0
                ) {
                    throw new ValidationError('Invalid resulting balance');
                }

                projected.set(id, change.balance);
            }

            const totalAfter = [...projected.values()]
                .reduce((sum, value) => sum + value, 0);

            if (totalBefore !== totalAfter) {
                throw new ValidationError(
                    'Balance conservation constraint failed'
                );
            }

            const updatedAccounts = [...this.writeSet].map(([id, change]) => ({
                id,
                balance: change.balance,
                version: this.ledger.accounts.get(id).version + 1
            }));

            const result = Object.freeze({
                transactionId: this.id,
                state: State.COMMITTED,
                operations: this.operations.length
            });

            // The durable record must succeed before memory state is changed.
            if (updatedAccounts.length > 0) {
                await this.ledger.journal.append({
                    type: 'TRANSFER',
                    transactionId: this.id,
                    idempotencyKey,
                    accounts: updatedAccounts,
                    result,
                    committedAt: new Date().toISOString()
                });
            }

            for (const item of updatedAccounts) {
                Object.assign(
                    this.ledger.accounts.get(item.id),
                    {
                        balance: item.balance,
                        version: item.version
                    }
                );
            }

            this.state = State.COMMITTED;

            this.ledger.emit('committed', {
                transactionId: this.id,
                accounts: updatedAccounts
            });

            return result;

        } catch (error) {
            this.state = State.FAILED;
            this.writeSet.clear();
            throw error;

        } finally {
            release();
        }
    }

    rollback() {
        this.assertActive();
        this.writeSet.clear();
        this.state = State.ROLLED_BACK;
    }
}

async function main() {
    const journal = new DurableJournal('acid_js_journal.json');
    await journal.load();

    const ledger = new AccountLedger(journal);

    const alice = ledger.createAccount('Alice', 100000);
    const bob = ledger.createAccount('Bob', 50000);
    const charlie = ledger.createAccount('Charlie', 25000);

    ledger.subscribe('committed', event => {
        console.log('Commit event:', event.transactionId);
    });

    console.log('Initial ledger:', ledger.report());

    const transfer = await ledger.executeTransfer({
        source: alice,
        target: bob,
        amount: 20000,
        idempotencyKey: 'PAYMENT-1001'
    });

    console.log('\nTransfer result:', transfer);

    // Repeating the same request returns the previous result.
    const repeated = await ledger.executeTransfer({
        source: alice,
        target: bob,
        amount: 20000,
        idempotencyKey: 'PAYMENT-1001'
    });

    console.log('\nIdempotent replay:', repeated);

    // A failed transfer cannot publish partial changes.
    try {
        await ledger.executeTransfer({
            source: alice,
            target: charlie,
            amount: 999999,
            idempotencyKey: 'PAYMENT-1002'
        });
    } catch (error) {
        console.log('\nRejected transaction:', error.message);
    }

    // Independent transaction with an invalid amount.
    try {
        const tx = ledger.begin();
        tx.transfer(alice, charlie, -50);
    } catch (error) {
        console.log('Validation test:', error.message);
    }

    const total = ledger.report()
        .reduce((sum, account) => sum + account.balance, 0);

    if (total !== 175000) {
        throw new Error('Consistency assertion failed');
    }

    console.log('\nFinal ledger:', ledger.report());
    console.log('Total balance:', total);
    console.log('Journal records:', journal.entries.length);
}

main().catch(error => {
    console.error('Application failure:', error.message);
    process.exitCode = 1;
});
