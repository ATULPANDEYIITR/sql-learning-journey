"use strict";

const { EventEmitter } = require("node:events");
const fs = require("node:fs/promises");
const crypto = require("node:crypto");

class TransactionError extends Error {}
class InsufficientFundsError extends TransactionError {}
class TransactionStateError extends TransactionError {}
class ValidationError extends TransactionError {}
class ConcurrencyError extends TransactionError {}

const State = Object.freeze({
    ACTIVE: "ACTIVE",
    COMMITTED: "COMMITTED",
    ROLLED_BACK: "ROLLED_BACK"
});

class Mutex {
    constructor() {
        this.tail = Promise.resolve();
    }

    async runExclusive(callback) {
        let release;

        const previous = this.tail;

        this.tail = new Promise(resolve => {
            release = resolve;
        });

        await previous;

        try {
            return await callback();
        } finally {
            release();
        }
    }
}

class Account {
    constructor(id, owner, balance, currency = "INR") {
        if (!id || !owner) {
            throw new ValidationError("Account ID and owner are required");
        }

        if (!Number.isSafeInteger(balance) || balance < 0) {
            throw new ValidationError(
                "Balance must be a non-negative integer in minor units"
            );
        }

        this.id = id;
        this.owner = owner;
        this.balance = balance;
        this.currency = currency;
    }
}

class Transaction {
    constructor(version) {
        this.id = crypto.randomUUID();
        this.state = State.ACTIVE;
        this.baseVersion = version;
        this.operations = [];
        this.createdAt = new Date().toISOString();
    }
}

class TransactionEngine extends EventEmitter {
    constructor() {
        super();

        this.accounts = new Map();
        this.transactions = new Map();
        this.ledger = [];
        this.version = 0;
        this.mutex = new Mutex();
    }

    createAccount(id, owner, balance, currency = "INR") {
        if (this.accounts.has(id)) {
            throw new ValidationError("Duplicate account");
        }

        this.accounts.set(
            id,
            new Account(id, owner, balance, currency)
        );

        this.version++;
        this.emit("accountCreated", { id, owner });
    }

    begin() {
        const transaction = new Transaction(this.version);

        this.transactions.set(transaction.id, transaction);

        this.emit("transactionStarted", {
            transactionId: transaction.id
        });

        return transaction;
    }

    assertActive(transaction) {
        if (!transaction || transaction.state !== State.ACTIVE) {
            throw new TransactionStateError(
                "Transaction is not active"
            );
        }
    }

    stageTransfer(transaction, source, destination, amount) {
        this.assertActive(transaction);

        if (!Number.isSafeInteger(amount) || amount <= 0) {
            throw new ValidationError(
                "Amount must be a positive integer in minor units"
            );
        }

        if (source === destination) {
            throw new ValidationError(
                "Source and destination must differ"
            );
        }

        const from = this.accounts.get(source);
        const to = this.accounts.get(destination);

        if (!from || !to) {
            throw new ValidationError("Account does not exist");
        }

        if (from.currency !== to.currency) {
            throw new ValidationError("Currency mismatch");
        }

        transaction.operations.push({
            type: "TRANSFER",
            source,
            destination,
            amount
        });

        this.emit("operationStaged", {
            transactionId: transaction.id,
            type: "TRANSFER"
        });
    }

    stageDeposit(transaction, accountId, amount) {
        this.assertActive(transaction);

        if (!Number.isSafeInteger(amount) || amount <= 0) {
            throw new ValidationError("Invalid deposit amount");
        }

        if (!this.accounts.has(accountId)) {
            throw new ValidationError("Unknown account");
        }

        transaction.operations.push({
            type: "DEPOSIT",
            accountId,
            amount
        });
    }

    stageWithdrawal(transaction, accountId, amount) {
        this.assertActive(transaction);

        if (!Number.isSafeInteger(amount) || amount <= 0) {
            throw new ValidationError("Invalid withdrawal amount");
        }

        if (!this.accounts.has(accountId)) {
            throw new ValidationError("Unknown account");
        }

        transaction.operations.push({
            type: "WITHDRAW",
            accountId,
            amount
        });
    }

    async commit(transaction) {
        this.assertActive(transaction);

        return this.mutex.runExclusive(async () => {
            this.assertActive(transaction);

            // Optimistic concurrency check prevents publishing a
            // transaction based on an outdated account snapshot.
            if (transaction.baseVersion !== this.version) {
                transaction.state = State.ROLLED_BACK;

                this.emit("transactionConflict", {
                    transactionId: transaction.id
                });

                throw new ConcurrencyError(
                    "Database version changed; retry transaction"
                );
            }

            const balances = new Map(
                [...this.accounts].map(
                    ([id, account]) => [id, account.balance]
                )
            );

            const pendingLedger = [];

            try {
                for (const operation of transaction.operations) {
                    if (operation.type === "TRANSFER") {
                        const {
                            source,
                            destination,
                            amount
                        } = operation;

                        if (balances.get(source) < amount) {
                            throw new InsufficientFundsError(
                                `Insufficient funds in ${source}`
                            );
                        }

                        balances.set(
                            source,
                            balances.get(source) - amount
                        );

                        balances.set(
                            destination,
                            balances.get(destination) + amount
                        );

                        pendingLedger.push(
                            {
                                transactionId: transaction.id,
                                accountId: source,
                                amount: -amount,
                                type: "TRANSFER_OUT"
                            },
                            {
                                transactionId: transaction.id,
                                accountId: destination,
                                amount,
                                type: "TRANSFER_IN"
                            }
                        );

                    } else if (operation.type === "DEPOSIT") {
                        const { accountId, amount } = operation;
                        const updated = balances.get(accountId) + amount;

                        if (!Number.isSafeInteger(updated)) {
                            throw new ValidationError(
                                "Balance exceeds safe integer range"
                            );
                        }

                        balances.set(accountId, updated);

                        pendingLedger.push({
                            transactionId: transaction.id,
                            accountId,
                            amount,
                            type: "DEPOSIT"
                        });

                    } else if (operation.type === "WITHDRAW") {
                        const { accountId, amount } = operation;

                        if (balances.get(accountId) < amount) {
                            throw new InsufficientFundsError(
                                `Insufficient funds in ${accountId}`
                            );
                        }

                        balances.set(
                            accountId,
                            balances.get(accountId) - amount
                        );

                        pendingLedger.push({
                            transactionId: transaction.id,
                            accountId,
                            amount: -amount,
                            type: "WITHDRAWAL"
                        });
                    } else {
                        throw new ValidationError(
                            "Unsupported transaction operation"
                        );
                    }
                }

                for (const balance of balances.values()) {
                    if (!Number.isSafeInteger(balance) || balance < 0) {
                        throw new ValidationError(
                            "Invalid resulting account balance"
                        );
                    }
                }

                // Publish all balances and ledger entries together
                // while holding the exclusive commit lock.
                for (const [id, balance] of balances) {
                    this.accounts.get(id).balance = balance;
                }

                this.ledger.push(...pendingLedger);
                this.version++;
                transaction.state = State.COMMITTED;

                this.emit("transactionCommitted", {
                    transactionId: transaction.id,
                    version: this.version
                });

                return transaction.id;

            } catch (error) {
                transaction.state = State.ROLLED_BACK;

                this.emit("transactionRolledBack", {
                    transactionId: transaction.id,
                    reason: error.message
                });

                throw error;
            }
        });
    }

    rollback(transaction) {
        this.assertActive(transaction);

        transaction.operations.length = 0;
        transaction.state = State.ROLLED_BACK;

        this.emit("transactionRolledBack", {
            transactionId: transaction.id,
            reason: "Explicit rollback"
        });
    }

    getBalance(accountId) {
        const account = this.accounts.get(accountId);

        if (!account) {
            throw new ValidationError("Unknown account");
        }

        return account.balance;
    }

    async executeWithRetry(operationFactory, maximumAttempts = 3) {
        if (!Number.isInteger(maximumAttempts) || maximumAttempts < 1) {
            throw new ValidationError("Invalid retry limit");
        }

        for (let attempt = 1; attempt <= maximumAttempts; attempt++) {
            const transaction = this.begin();

            try {
                await operationFactory(transaction);
                await this.commit(transaction);
                return transaction.id;

            } catch (error) {
                if (
                    error instanceof ConcurrencyError &&
                    attempt < maximumAttempts
                ) {
                    continue;
                }

                if (transaction.state === State.ACTIVE) {
                    this.rollback(transaction);
                }

                throw error;
            }
        }

        throw new ConcurrencyError("Retry limit exceeded");
    }

    async exportReport(filename) {
        const report = {
            version: this.version,
            accounts: [...this.accounts.values()],
            ledger: this.ledger
        };

        await fs.writeFile(
            filename,
            JSON.stringify(report, null, 2),
            { encoding: "utf8", flag: "w" }
        );
    }

    printBalances() {
        console.log("\nACCOUNT BALANCES");

        for (const account of this.accounts.values()) {
            console.log(
                `${account.id}: ${account.owner}: ` +
                `${(account.balance / 100).toFixed(2)} ${account.currency}`
            );
        }
    }
}

async function main() {
    const engine = new TransactionEngine();

    engine.on("transactionCommitted", event => {
        console.log("COMMIT EVENT:", event.transactionId);
    });

    engine.on("transactionRolledBack", event => {
        console.log("ROLLBACK EVENT:", event.reason);
    });

    engine.on("transactionConflict", event => {
        console.log("CONCURRENCY CONFLICT:", event.transactionId);
    });

    engine.createAccount("A100", "Alice", 1000000);
    engine.createAccount("A200", "Bob", 500000);
    engine.createAccount("A300", "Charlie", 200000);

    console.log("\n1. Atomic transfer");

    const first = engine.begin();

    engine.stageTransfer(first, "A100", "A200", 150000);
    engine.stageDeposit(first, "A300", 50000);

    await engine.commit(first);

    engine.printBalances();

    console.log("\n2. Explicit rollback");

    const second = engine.begin();

    engine.stageWithdrawal(second, "A100", 100000);
    engine.rollback(second);

    engine.printBalances();

    console.log("\n3. Insufficient funds");

    const third = engine.begin();

    try {
        engine.stageWithdrawal(third, "A200", 99999999);
        await engine.commit(third);
    } catch (error) {
        console.log("Expected failure:", error.message);
    }

    engine.printBalances();

    console.log("\n4. Optimistic concurrency conflict");

    const stale = engine.begin();

    engine.stageDeposit(stale, "A100", 10000);

    const concurrent = engine.begin();

    engine.stageDeposit(concurrent, "A200", 20000);

    await engine.commit(concurrent);

    try {
        await engine.commit(stale);
    } catch (error) {
        console.log("Expected conflict:", error.message);
    }

    console.log("\n5. Transaction retry");

    await engine.executeWithRetry(async transaction => {
        engine.stageDeposit(transaction, "A300", 25000);
    });

    engine.printBalances();

    console.log("\n6. Invalid amount");

    const invalid = engine.begin();

    try {
        engine.stageDeposit(invalid, "A100", -100);
    } catch (error) {
        engine.rollback(invalid);
        console.log("Validation failure:", error.message);
    }

    await engine.exportReport("transaction_report.json");

    console.log("\nReport saved to transaction_report.json");

    const total = [...engine.accounts.values()]
        .reduce((sum, account) => sum + account.balance, 0);

    if (total !== 1775000) {
        throw new Error(`Accounting invariant failed: ${total}`);
    }

    console.log("Final total in minor units:", total);
}

main().catch(error => {
    console.error("Application failure:", error);
    process.exitCode = 1;
});
