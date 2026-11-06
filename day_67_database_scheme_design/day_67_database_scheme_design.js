"use strict";

/**
 * Database Schema Design
 *
 * Event-driven schema registry and OLTP integrity evaluator.
 * Node.js standard library only.
 */

const crypto = require("node:crypto");
const { EventEmitter } = require("node:events");

class SchemaError extends Error {
    constructor(message) {
        super(message);
        this.name = "SchemaError";
    }
}

const TYPES = new Set([
    "INTEGER",
    "BIGINT",
    "VARCHAR",
    "TEXT",
    "BOOLEAN",
    "NUMERIC",
    "TIMESTAMPTZ"
]);

const ACTIONS = new Set([
    "RESTRICT",
    "CASCADE",
    "SET NULL",
    "NO ACTION"
]);

class SchemaRegistry extends EventEmitter {
    #tables = new Map();
    #indexes = new Map();
    #version = 1;

    constructor() {
        super();
    }

    get version() {
        return this.#version;
    }

    getTable(name) {
        return this.#tables.get(name) ?? null;
    }

    get tables() {
        return [...this.#tables.values()].map(
            table => structuredClone(table)
        );
    }

    registerTable(definition) {
        this.#validateTable(definition);

        if (this.#tables.has(definition.name)) {
            throw new SchemaError(
                `Table ${definition.name} already exists.`
            );
        }

        const table = structuredClone(definition);

        this.#tables.set(table.name, table);
        this.#version++;

        this.emit("tableCreated", {
            name: table.name,
            version: this.#version
        });

        return table;
    }

    #validateTable(table) {
        if (!/^[a-z][a-z0-9_]*$/.test(table.name)) {
            throw new SchemaError("Invalid table naming convention.");
        }

        if (!Array.isArray(table.columns) || table.columns.length === 0) {
            throw new SchemaError("A table requires columns.");
        }

        const names = new Set();

        for (const column of table.columns) {
            if (!/^[a-z][a-z0-9_]*$/.test(column.name)) {
                throw new SchemaError(
                    `Invalid column name: ${column.name}`
                );
            }

            if (names.has(column.name)) {
                throw new SchemaError(
                    `Duplicate column: ${column.name}`
                );
            }

            names.add(column.name);

            if (!TYPES.has(column.type)) {
                throw new SchemaError(
                    `Unsupported data type: ${column.type}`
                );
            }

            if (column.primaryKey && column.nullable === true) {
                throw new SchemaError(
                    "Primary key columns cannot be nullable."
                );
            }
        }

        if (table.primaryKey) {
            this.#validateColumnList(
                table.primaryKey,
                names,
                "Primary key"
            );
        }

        for (const constraint of table.unique ?? []) {
            this.#validateColumnList(
                constraint,
                names,
                "Unique constraint"
            );
        }

        for (const foreignKey of table.foreignKeys ?? []) {
            this.#validateColumnList(
                foreignKey.columns,
                names,
                "Foreign key"
            );

            if (
                foreignKey.columns.length !==
                foreignKey.references.columns.length
            ) {
                throw new SchemaError(
                    "Foreign key column count mismatch."
                );
            }

            if (!ACTIONS.has(foreignKey.onDelete)) {
                throw new SchemaError("Invalid deletion action.");
            }
        }
    }

    #validateColumnList(columns, available, label) {
        if (
            !Array.isArray(columns) ||
            columns.length === 0 ||
            columns.some(column => !available.has(column))
        ) {
            throw new SchemaError(`${label} contains invalid columns.`);
        }

        if (new Set(columns).size !== columns.length) {
            throw new SchemaError(`${label} contains duplicate columns.`);
        }
    }

    validateRelationships() {
        const errors = [];

        for (const table of this.#tables.values()) {
            for (const fk of table.foreignKeys ?? []) {
                const parent = this.#tables.get(
                    fk.references.table
                );

                if (!parent) {
                    errors.push(
                        `${table.name}: missing parent table`
                    );
                    continue;
                }

                const parentColumns = new Set(
                    parent.columns.map(column => column.name)
                );

                if (
                    fk.references.columns.some(
                        column => !parentColumns.has(column)
                    )
                ) {
                    errors.push(
                        `${table.name}: unknown referenced column`
                    );
                    continue;
                }

                const candidateKeys = [
                    parent.primaryKey ?? [],
                    ...(parent.unique ?? [])
                ];

                const isCandidateKey = candidateKeys.some(
                    key =>
                        key.length === fk.references.columns.length &&
                        key.every(
                            column =>
                                fk.references.columns.includes(column)
                        )
                );

                if (!isCandidateKey) {
                    errors.push(
                        `${table.name}: referenced columns are not unique`
                    );
                }
            }
        }

        return {
            valid: errors.length === 0,
            errors
        };
    }

    creationOrder() {
        const completed = new Set();
        const active = new Set();
        const result = [];

        const visit = name => {
            if (active.has(name)) {
                throw new SchemaError(
                    `Circular dependency involving ${name}`
                );
            }

            if (completed.has(name)) return;

            const table = this.#tables.get(name);

            if (!table) {
                throw new SchemaError(`Unknown table: ${name}`);
            }

            active.add(name);

            for (const fk of table.foreignKeys ?? []) {
                visit(fk.references.table);
            }

            active.delete(name);
            completed.add(name);
            result.push(name);
        };

        for (const name of this.#tables.keys()) {
            visit(name);
        }

        return result;
    }

    registerIndex(index) {
        if (
            !/^[a-z][a-z0-9_]*$/.test(index.name) ||
            this.#indexes.has(index.name)
        ) {
            throw new SchemaError("Invalid or duplicate index name.");
        }

        const table = this.#tables.get(index.table);

        if (!table) {
            throw new SchemaError("Index table does not exist.");
        }

        const columns = new Set(
            table.columns.map(column => column.name)
        );

        if (
            !index.columns.length ||
            index.columns.some(column => !columns.has(column))
        ) {
            throw new SchemaError("Index contains invalid columns.");
        }

        this.#indexes.set(index.name, structuredClone(index));
        this.#version++;

        this.emit("indexCreated", {
            name: index.name,
            version: this.#version
        });
    }

    inspect() {
        return {
            version: this.#version,
            creationOrder: this.creationOrder(),
            tables: this.tables,
            indexes: [...this.#indexes.values()]
        };
    }
}

class RelationalStore {
    #tables = new Map();

    constructor(registry) {
        this.registry = registry;

        for (const definition of registry.tables) {
            this.#tables.set(definition.name, new Map());
        }
    }

    #primaryKey(table, record) {
        const definition = this.registry.getTable(table);

        if (!definition) {
            throw new SchemaError(`Unknown table: ${table}`);
        }

        const keys = definition.primaryKey ??
            definition.columns
                .filter(column => column.primaryKey)
                .map(column => column.name);

        if (!keys.length) {
            throw new SchemaError("Table has no primary key.");
        }

        const values = keys.map(key => record[key]);

        if (values.some(value => value === null || value === undefined)) {
            throw new SchemaError("Primary key cannot contain NULL.");
        }

        return JSON.stringify(values);
    }

    #validateRecord(tableName, record) {
        const definition = this.registry.getTable(tableName);

        if (!definition) {
            throw new SchemaError(`Unknown table: ${tableName}`);
        }

        const allowed = new Set(
            definition.columns.map(column => column.name)
        );

        for (const key of Object.keys(record)) {
            if (!allowed.has(key)) {
                throw new SchemaError(`Unknown column: ${key}`);
            }
        }

        for (const column of definition.columns) {
            const value = record[column.name];

            if (
                !column.nullable &&
                (value === null || value === undefined) &&
                !column.primaryKey &&
                column.default === undefined
            ) {
                throw new SchemaError(
                    `${column.name} cannot be NULL.`
                );
            }

            if (
                value !== null &&
                value !== undefined &&
                column.type === "INTEGER" &&
                (!Number.isSafeInteger(value))
            ) {
                throw new SchemaError(
                    `${column.name} must be a safe integer.`
                );
            }

            if (
                value !== null &&
                value !== undefined &&
                column.type === "NUMERIC" &&
                !Number.isFinite(Number(value))
            ) {
                throw new SchemaError(
                    `${column.name} must be numeric.`
                );
            }

            if (
                column.check &&
                value !== null &&
                value !== undefined &&
                !column.check(value)
            ) {
                throw new SchemaError(
                    `CHECK constraint failed: ${column.name}`
                );
            }
        }

        for (const uniqueKey of definition.unique ?? []) {
            const values = uniqueKey.map(key => record[key]);

            // SQL UNIQUE constraints permit multiple NULL values.
            if (values.some(value => value === null || value === undefined)) {
                continue;
            }

            for (const existing of this.#tables.get(tableName).values()) {
                if (
                    uniqueKey.every(
                        (key, index) => existing[key] === values[index]
                    )
                ) {
                    throw new SchemaError(
                        `Unique constraint failed: ${uniqueKey.join(",")}`
                    );
                }
            }
        }

        for (const fk of definition.foreignKeys ?? []) {
            const values = fk.columns.map(key => record[key]);

            if (values.every(
                value => value === null || value === undefined
            )) {
                continue;
            }

            if (values.some(
                value => value === null || value === undefined
            )) {
                throw new SchemaError(
                    "Composite foreign key cannot be partially NULL."
                );
            }

            const parentRows = this.#tables.get(
                fk.references.table
            );

            const found = [...parentRows.values()].some(parent =>
                fk.references.columns.every(
                    (key, index) => parent[key] === values[index]
                )
            );

            if (!found) {
                throw new SchemaError(
                    `Foreign key violation in ${tableName}.`
                );
            }
        }
    }

    insert(tableName, input) {
        const record = { ...input };
        const definition = this.registry.getTable(tableName);

        if (!definition) {
            throw new SchemaError(`Unknown table: ${tableName}`);
        }

        for (const column of definition.columns) {
            if (
                record[column.name] === undefined &&
                column.default !== undefined
            ) {
                record[column.name] = column.default;
            }
        }

        this.#validateRecord(tableName, record);

        const key = this.#primaryKey(tableName, record);
        const table = this.#tables.get(tableName);

        if (table.has(key)) {
            throw new SchemaError("Duplicate primary key.");
        }

        table.set(key, Object.freeze(record));

        return { ...record };
    }

    rows(tableName) {
        const table = this.#tables.get(tableName);

        if (!table) {
            throw new SchemaError("Unknown table.");
        }

        return [...table.values()].map(record => ({ ...record }));
    }
}

function createRegistry() {
    const registry = new SchemaRegistry();

    registry.on("tableCreated", event => {
        console.log(
            `[DDL] Created ${event.name}, version ${event.version}`
        );
    });

    registry.registerTable({
        name: "customers",
        primaryKey: ["customer_id"],
        columns: [
            {
                name: "customer_id",
                type: "BIGINT",
                nullable: false,
                primaryKey: true
            },
            {
                name: "email",
                type: "VARCHAR",
                nullable: false
            },
            {
                name: "full_name",
                type: "VARCHAR",
                nullable: false
            }
        ],
        unique: [["email"]]
    });

    registry.registerTable({
        name: "products",
        primaryKey: ["product_id"],
        columns: [
            {
                name: "product_id",
                type: "BIGINT",
                nullable: false,
                primaryKey: true
            },
            {
                name: "sku",
                type: "VARCHAR",
                nullable: false
            },
            {
                name: "product_name",
                type: "VARCHAR",
                nullable: false
            },
            {
                name: "unit_price",
                type: "NUMERIC",
                nullable: false,
                check: value => Number(value) >= 0
            }
        ],
        unique: [["sku"]]
    });

    registry.registerTable({
        name: "orders",
        primaryKey: ["order_id"],
        columns: [
            {
                name: "order_id",
                type: "BIGINT",
                nullable: false,
                primaryKey: true
            },
            {
                name: "customer_id",
                type: "BIGINT",
                nullable: false
            },
            {
                name: "order_status",
                type: "VARCHAR",
                nullable: false,
                default: "PENDING",
                check: value =>
                    ["PENDING", "CONFIRMED", "SHIPPED", "CANCELLED"]
                        .includes(value)
            }
        ],
        foreignKeys: [
            {
                columns: ["customer_id"],
                references: {
                    table: "customers",
                    columns: ["customer_id"]
                },
                onDelete: "RESTRICT"
            }
        ]
    });

    registry.registerTable({
        name: "order_items",
        primaryKey: ["order_item_id"],
        columns: [
            {
                name: "order_item_id",
                type: "BIGINT",
                nullable: false,
                primaryKey: true
            },
            {
                name: "order_id",
                type: "BIGINT",
                nullable: false
            },
            {
                name: "product_id",
                type: "BIGINT",
                nullable: false
            },
            {
                name: "quantity",
                type: "INTEGER",
                nullable: false,
                check: value => value > 0
            },
            {
                name: "unit_price",
                type: "NUMERIC",
                nullable: false,
                check: value => Number(value) >= 0
            }
        ],
        unique: [["order_id", "product_id"]],
        foreignKeys: [
            {
                columns: ["order_id"],
                references: {
                    table: "orders",
                    columns: ["order_id"]
                },
                onDelete: "CASCADE"
            },
            {
                columns: ["product_id"],
                references: {
                    table: "products",
                    columns: ["product_id"]
                },
                onDelete: "RESTRICT"
            }
        ]
    });

    registry.registerIndex({
        name: "idx_orders_customer_status",
        table: "orders",
        columns: ["customer_id", "order_status"]
    });

    return registry;
}

async function runWorkflow(store) {
    const customer = store.insert("customers", {
        customer_id: 1,
        email: "customer@example.com",
        full_name: "Aarav Sharma"
    });

    const product = store.insert("products", {
        product_id: 101,
        sku: "SKU-101",
        product_name: "Business Laptop",
        unit_price: "75000.00"
    });

    const order = store.insert("orders", {
        order_id: 5001,
        customer_id: customer.customer_id
    });

    const item = store.insert("order_items", {
        order_item_id: 9001,
        order_id: order.order_id,
        product_id: product.product_id,
        quantity: 2,
        unit_price: product.unit_price
    });

    console.log("\nOLTP TRANSACTION DATA");

    console.table(store.rows("customers"));
    console.table(store.rows("orders"));
    console.table(store.rows("order_items"));

    console.log(
        "Order amount:",
        Number(item.quantity * Number(item.unit_price)).toFixed(2)
    );

    return { customer, product, order, item };
}

async function main() {
    const registry = createRegistry();

    const relationshipReport = registry.validateRelationships();

    if (!relationshipReport.valid) {
        throw new SchemaError(
            relationshipReport.errors.join("; ")
        );
    }

    console.log("\nTABLE CREATION ORDER");
    console.log(registry.creationOrder().join(" -> "));

    const store = new RelationalStore(registry);

    await runWorkflow(store);

    console.log("\nVALIDATION TESTS");

    const invalidCases = [
        () => store.insert("customers", {
            customer_id: 2,
            email: "customer@example.com",
            full_name: "Duplicate Email"
        }),

        () => store.insert("orders", {
            order_id: 5002,
            customer_id: 999
        }),

        () => store.insert("products", {
            product_id: 102,
            sku: "SKU-102",
            product_name: "Invalid Product",
            unit_price: -100
        }),

        () => store.insert("order_items", {
            order_item_id: 9002,
            order_id: 5001,
            product_id: 101,
            quantity: 0,
            unit_price: 75000
        })
    ];

    for (const operation of invalidCases) {
        try {
            operation();
            throw new Error("Invalid operation unexpectedly succeeded.");
        } catch (error) {
            if (!(error instanceof SchemaError)) {
                throw error;
            }

            console.log("Rejected:", error.message);
        }
    }

    const schemaSnapshot = registry.inspect();

    console.log("\nSCHEMA VERSION:", schemaSnapshot.version);
    console.log(
        "REGISTERED TABLES:",
        schemaSnapshot.tables.map(table => table.name)
    );
    console.log(
        "INDEXES:",
        schemaSnapshot.indexes.map(index => index.name)
    );

    console.log("\nSchema design demonstration completed.");
}

main().catch(error => {
    console.error("Execution failed:", error.message);
    process.exitCode = 1;
});
