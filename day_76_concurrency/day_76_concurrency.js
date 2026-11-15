'use strict';

/**
 * Concurrency, Locks, Concurrent Transactions, and Race Conditions.
 *
 * Node.js implementation featuring:
 * - Asynchronous mutexes
 * - Promise-based concurrent transactions
 * - Deadlock prevention through lock ordering
 * - Idempotency
 * - Optimistic concurrency control
 * - Event-driven transaction notifications
 * - Atomic state transitions
 * - Failure handling
 *
 * Runtime: Node.js 18+
 * Dependencies: None
 */

const { EventEmitter } = require('node:events');
const { randomUUID } = require('node:crypto');


class TransactionError extends Error {
    constructor(message) {
        super(message);
        this.name = 'TransactionError';
    }
}

class InsufficientFundsError extends TransactionError {
    constructor() {
        super('Insufficient funds');
        this.name = 'InsufficientFundsError';
    }
}

class ConcurrencyConflictError extends TransactionError {
    constructor() {
        super('Concurrent modification detected');
        this.name = 'ConcurrencyConflictError';
    }
}

class DuplicateTransactionError extends TransactionError {
    constructor() {
        super('Idempotency key reused with different parameters');
        this.name = 'DuplicateTransactionError';
    }
}


/**
 * FIFO asynchronous mutex.
 *
 * Every acquisition returns a release function.
 * A lock must always be released in a finally block.
 */
class AsyncMutex {
    constructor() {
        this.locked = false;
        this.waiters = [];
    }

    acquire() {
        return new Promise((resolve) => {
            const grant = () => {
                this.locked = true;
                let released = false;

                resolve(() => {
                    if (released) {
                        throw new Error('Mutex released twice');
                    }

                    released = true;

                    const next = this.waiters.shift();

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
                this.waiters.push(grant);
            }
        });
    }

    async runExclusive(operation) {
        const release = await this.acquire();

        try {
            return await operation();
        } finally {
            release();
        }
    }
}


/**
 * Account state is encapsulated.
 */
class Account {
    constructor(id, balance) {
        if (!id || typeof id !== 'string') {
            throw new TypeError('Account ID must be a string');
        }

        if (!Number.isSafeInteger(balance) || balance < 0) {
            throw new RangeError('Balance must be a non-negative integer');
        }

        this.id = id;
        this.balance = balance;
        this.version = 0;
        this.mutex = new AsyncMutex();
    }

    snapshot() {
        return Object.freeze({
            id: this.id,
            balance: this.balance,
            version: this.version
        });
    }
}


/**
 * Event-driven transaction service.
 */
class TransactionService extends EventEmitter {
    constructor() {
        super();

        this.accounts = new Map();
        this.idempotency = new Map();
        this.registryMutex = new AsyncMutex();
    }

    async createAccount(id, balance) {
        return this.registryMutex.runExclusive(async () => {
            if (this.accounts.has(id)) {
                throw new TransactionError('Account already exists');
            }

            const account = new Account(id, balance);
            this.accounts.set(id, account);

            this.emit('account:created', account.snapshot());

            return account.snapshot();
        });
    }

    getAccount(id) {
        const account = this.accounts.get(id);

        if (!account) {
            throw new TransactionError(`Unknown account: ${id}`);
        }

        return account;
    }

    async getBalance(id) {
        const account = this.getAccount(id);

        return account.mutex.runExclusive(async () => {
            return account.snapshot();
        });
    }

    /**
     * Acquires multiple account locks in sorted order.
     *
     * The deterministic ordering prevents circular wait.
     */
    async withAccountLocks(accounts, operation) {
        const ordered = [...accounts].sort(
            (a, b) => a.id.localeCompare(b.id)
        );

        const releases = [];

        try {
            for (const account of ordered) {
                releases.push(await account.mutex.acquire());
            }

            return await operation();
        } finally {
            for (const release of releases.reverse()) {
                release();
            }
        }
    }

    async transfer({
        sourceId,
        destinationId,
        amount,
        idempotencyKey
    }) {
        if (!sourceId || !destinationId) {
            throw new TypeError('Account IDs are required');
        }

        if (sourceId === destinationId) {
            throw new TransactionError(
                'Source and destination must differ'
            );
        }

        if (!Number.isSafeInteger(amount) || amount <= 0) {
            throw new RangeError(
                'Amount must be a positive safe integer'
            );
        }

        if (
            typeof idempotencyKey !== 'string' ||
            idempotencyKey.trim() === ''
        ) {
            throw new TypeError('Valid idempotency key required');
        }

        const source = this.getAccount(sourceId);
        const destination = this.getAccount(destinationId);

        const fingerprint = JSON.stringify({
            sourceId,
            destinationId,
            amount
        });

        // Registry mutex protects idempotency state and serializes
        // requests using the same service.
        return this.registryMutex.runExclusive(async () => {
            const existing = this.idempotency.get(idempotencyKey);

            if (existing) {
                if (existing.fingerprint !== fingerprint) {
                    throw new DuplicateTransactionError();
                }

                return existing.result;
            }

            return this.withAccountLocks(
                [source, destination],
                async () => {
                    if (source.balance < amount) {
                        const rejected = Object.freeze({
                            transactionId: randomUUID(),
                            status: 'REJECTED',
                            sourceId,
                            destinationId,
                            amount,
                            reason: 'Insufficient funds'
                        });

                        this.idempotency.set(idempotencyKey, {
                            fingerprint,
                            result: rejected
                        });

                        this.emit('transaction:rejected', rejected);

                        return rejected;
                    }

                    // Validate before modifying either account.
                    const oldSource = source.balance;
                    const oldDestination = destination.balance;

                    try {
                        const newSource = oldSource - amount;
                        const newDestination = oldDestination + amount;

                        if (
                            !Number.isSafeInteger(newSource) ||
                            !Number.isSafeInteger(newDestination)
                        ) {
                            throw new RangeError(
                                'Balance exceeds safe integer limits'
                            );
                        }

                        source.balance = newSource;
                        destination.balance = newDestination;

                        source.version++;
                        destination.version++;

                        const result = Object.freeze({
                            transactionId: randomUUID(),
                            status: 'COMMITTED',
                            sourceId,
                            destinationId,
                            amount,
                            sourceVersion: source.version,
                            destinationVersion: destination.version
                        });

                        this.idempotency.set(idempotencyKey, {
                            fingerprint,
                            result
                        });

                        this.emit('transaction:committed', result);

                        return result;

                    } catch (error) {
                        source.balance = oldSource;
                        destination.balance = oldDestination;

                        throw error;
                    }
                }
            );
        });
    }
}


/**
 * Compare-and-set optimistic concurrency model.
 */
class VersionedStore {
    constructor(initialValue) {
        this.value = initialValue;
        this.version = 0;
    }

    read() {
        return Object.freeze({
            value: this.value,
            version: this.version
        });
    }

    compareAndSet(expectedVersion, newValue) {
        if (this.version !== expectedVersion) {
            throw new ConcurrencyConflictError();
        }

        this.value = newValue;
        this.version++;

        return this.read();
    }
}


/**
 * Demonstrates the lost-update problem.
 *
 * JavaScript execution can still interleave across await points.
 */
async function demonstrateRaceCondition() {
    console.log('\n--- Race Condition ---');

    let unsafeCounter = 0;

    async function unsafeIncrement() {
        const current = unsafeCounter;

        await new Promise(resolve => setImmediate(resolve));

        unsafeCounter = current + 1;
    }

    await Promise.all(
        Array.from({ length: 100 }, unsafeIncrement)
    );

    console.log('Unsafe counter:', unsafeCounter);
    console.log('Expected counter: 100');

    const safeMutex = new AsyncMutex();
    let safeCounter = 0;

    async function safeIncrement() {
        await safeMutex.runExclusive(async () => {
            const current = safeCounter;

            await new Promise(resolve => setImmediate(resolve));

            safeCounter = current + 1;
        });
    }

    await Promise.all(
        Array.from({ length: 100 }, safeIncrement)
    );

    console.log('Safe counter:', safeCounter);

    if (safeCounter !== 100) {
        throw new Error('Safe counter invariant failed');
    }
}


/**
 * Executes concurrent transfers and checks conservation.
 */
async function demonstrateTransactions() {
    console.log('\n--- Concurrent Transactions ---');

    const service = new TransactionService();

    service.on('transaction:committed', transaction => {
        console.log(
            `Committed ${transaction.transactionId}: ` +
            `${transaction.sourceId} -> ${transaction.destinationId}`
        );
    });

    await service.createAccount('A', 10000);
    await service.createAccount('B', 10000);
    await service.createAccount('C', 5000);

    const initialTotal = 25000;

    const operations = Array.from({ length: 200 }, (_, index) => {
        if (index % 2 === 0) {
            return service.transfer({
                sourceId: 'A',
                destinationId: 'B',
                amount: 10,
                idempotencyKey: `TX-${index}`
            });
        }

        return service.transfer({
            sourceId: 'B',
            destinationId: 'A',
            amount: 10,
            idempotencyKey: `TX-${index}`
        });
    });

    const results = await Promise.all(operations);

    const balances = await Promise.all(
        ['A', 'B', 'C'].map(id => service.getBalance(id))
    );

    const finalTotal = balances.reduce(
        (total, account) => total + account.balance,
        0
    );

    console.log('Committed:', results.filter(
        result => result.status === 'COMMITTED'
    ).length);

    console.log('Balances:', balances);
    console.log('Initial total:', initialTotal);
    console.log('Final total:', finalTotal);

    if (initialTotal !== finalTotal) {
        throw new Error('Balance conservation violated');
    }
}


/**
 * Verifies idempotency and request fingerprint validation.
 */
async function demonstrateIdempotency() {
    console.log('\n--- Idempotency ---');

    const service = new TransactionService();

    await service.createAccount('SOURCE', 1000);
    await service.createAccount('TARGET', 500);

    const request = {
        sourceId: 'SOURCE',
        destinationId: 'TARGET',
        amount: 100,
        idempotencyKey: 'PAYMENT-001'
    };

    const first = await service.transfer(request);
    const second = await service.transfer(request);

    console.log('First transaction:', first.status);
    console.log('Repeated transaction:', second.status);
    console.log(
        'Same transaction ID:',
        first.transactionId === second.transactionId
    );

    try {
        await service.transfer({
            ...request,
            amount: 200
        });
    } catch (error) {
        console.log('Key reuse rejected:', error.message);
    }
}


/**
 * Demonstrates stale version detection.
 */
function demonstrateOptimisticConcurrency() {
    console.log('\n--- Optimistic Concurrency ---');

    const store = new VersionedStore(1000);

    const firstRead = store.read();
    const secondRead = store.read();

    store.compareAndSet(firstRead.version, 1200);

    try {
        store.compareAndSet(secondRead.version, 1500);
    } catch (error) {
        console.log('Stale update rejected:', error.message);
    }

    console.log('Current state:', store.read());
}


async function demonstrateDeadlockPrevention() {
    console.log('\n--- Deadlock Prevention ---');

    const service = new TransactionService();

    await service.createAccount('LEFT', 10000);
    await service.createAccount('RIGHT', 10000);

    const requests = [];

    for (let i = 0; i < 100; i++) {
        requests.push(
            service.transfer({
                sourceId: 'LEFT',
                destinationId: 'RIGHT',
                amount: 1,
                idempotencyKey: `FORWARD-${i}`
            })
        );

        requests.push(
            service.transfer({
                sourceId: 'RIGHT',
                destinationId: 'LEFT',
                amount: 1,
                idempotencyKey: `REVERSE-${i}`
            })
        );
    }

    const results = await Promise.all(requests);

    console.log('Completed:', results.length);

    const left = await service.getBalance('LEFT');
    const right = await service.getBalance('RIGHT');

    console.log('Left balance:', left.balance);
    console.log('Right balance:', right.balance);

    if (left.balance + right.balance !== 20000) {
        throw new Error('Deadlock test violated balance invariant');
    }
}


async function main() {
    console.log('CONCURRENCY MANAGEMENT SYSTEM');

    await demonstrateRaceCondition();
    await demonstrateTransactions();
    await demonstrateIdempotency();
    demonstrateOptimisticConcurrency();
    await demonstrateDeadlockPrevention();

    console.log('\nAll concurrency tests completed.');
}


main().catch(error => {
    console.error('Execution failed:', error);
    process.exitCode = 1;
});
