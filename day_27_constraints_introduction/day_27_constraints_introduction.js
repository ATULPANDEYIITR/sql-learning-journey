/*
 * Constraints Introduction: Constraints, Data Integrity, and Constraint Enforcement
 *
 * This self-contained JavaScript study file demonstrates the concepts of
 * database constraints by building a small in-memory relational-style system.
 *
 * The implementation intentionally does not require an external npm package.
 * It focuses on the semantics and engineering discipline behind:
 *
 * - NOT NULL
 * - PRIMARY KEY
 * - UNIQUE
 * - CHECK
 * - DEFAULT
 * - FOREIGN KEY
 * - Referential actions
 * - Composite constraints
 * - Transactions
 * - Validation layers
 * - Constraint errors
 * - NULL behavior
 * - Conditional uniqueness
 * - Concurrency and race-condition considerations
 * - Testing
 *
 * In a production JavaScript application, these rules would normally also be
 * represented in an actual database schema. The in-memory implementation makes
 * the enforcement mechanisms visible without requiring an external database.
 */

"use strict";

// -----------------------------------------------------------------------------
// 1. ERROR TYPES
// -----------------------------------------------------------------------------

class ConstraintError extends Error {
    constructor(constraintType, message) {
        super(message);
        this.name = "ConstraintError";
        this.constraintType = constraintType;
    }
}

class TransactionError extends Error {
    constructor(message) {
        super(message);
        this.name = "TransactionError";
    }
}


// -----------------------------------------------------------------------------
// 2. GENERIC HELPERS
// -----------------------------------------------------------------------------

function deepClone(value) {
    /*
     * Structured cloning is available in modern JavaScript runtimes.
     * This is sufficient for the primitive/object structures used by this
     * educational database. A production database handles persistence and
     * concurrency differently.
     */
    return structuredClone(value);
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function printSection(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}

function printRows(rows) {
    if (rows.length === 0) {
        console.log("(no rows)");
        return;
    }

    const columns = Object.keys(rows[0]);
    console.log(columns.join(" | "));
    console.log("-".repeat(78));

    for (const row of rows) {
        console.log(columns.map(column => String(row[column])).join(" | "));
    }
}


// -----------------------------------------------------------------------------
// 3. COLUMN AND TABLE DEFINITIONS
// -----------------------------------------------------------------------------

class ColumnDefinition {
    constructor({
        name,
        nullable = true,
        defaultValue = undefined,
        primaryKey = false,
        unique = false,
        check = null
    }) {
        this.name = name;
        this.nullable = nullable;
        this.defaultValue = defaultValue;
        this.primaryKey = primaryKey;
        this.unique = unique;
        this.check = check;
    }
}

class Table {
    constructor(name, columns, options = {}) {
        this.name = name;
        this.columns = new Map(columns.map(column => [column.name, column]));
        this.rows = [];

        this.primaryKey = options.primaryKey ?? null;
        this.uniqueConstraints = options.uniqueConstraints ?? [];
        this.foreignKeys = options.foreignKeys ?? [];
        this.checkConstraints = options.checkConstraints ?? [];
        this.partialUniqueIndexes = options.partialUniqueIndexes ?? [];
    }

    getColumn(name) {
        const column = this.columns.get(name);

        if (!column) {
            throw new Error(
                `Unknown column '${name}' in table '${this.name}'.`
            );
        }

        return column;
    }

    insert(input) {
        const candidate = {};

        // Apply DEFAULT values and supplied values.
        for (const [name, column] of this.columns) {
            if (Object.prototype.hasOwnProperty.call(input, name)) {
                candidate[name] = input[name];
            } else if (column.defaultValue !== undefined) {
                candidate[name] =
                    typeof column.defaultValue === "function"
                        ? column.defaultValue()
                        : column.defaultValue;
            } else {
                candidate[name] = null;
            }
        }

        this.validateRow(candidate, null);
        this.rows.push(candidate);

        return deepClone(candidate);
    }

    update(predicate, changes) {
        const updatedRows = [];
        let count = 0;

        for (const currentRow of this.rows) {
            if (!predicate(currentRow)) {
                updatedRows.push(currentRow);
                continue;
            }

            const candidate = {
                ...currentRow,
                ...changes
            };

            this.validateRow(candidate, currentRow);
            updatedRows.push(candidate);
            count += 1;
        }

        this.rows = updatedRows;
        return count;
    }

    delete(predicate) {
        const before = this.rows.length;
        this.rows = this.rows.filter(row => !predicate(row));
        return before - this.rows.length;
    }

    validateRow(candidate, oldRow) {
        // NOT NULL and column-level CHECK rules.
        for (const [name, column] of this.columns) {
            const value = candidate[name];

            if (value === null || value === undefined) {
                if (!column.nullable) {
                    throw new ConstraintError(
                        "NOT NULL",
                        `${this.name}.${name} cannot be NULL.`
                    );
                }

                continue;
            }

            if (column.check && !column.check(value, candidate)) {
                throw new ConstraintError(
                    "CHECK",
                    `CHECK constraint failed for ${this.name}.${name}.`
                );
            }
        }

        // PRIMARY KEY.
        if (this.primaryKey) {
            const key = this.keyFromRow(candidate, this.primaryKey);

            const conflict = this.rows.some(row => {
                if (oldRow && row === oldRow) {
                    return false;
                }

                return this.keysEqual(
                    this.keyFromRow(row, this.primaryKey),
                    key
                );
            });

            if (conflict) {
                throw new ConstraintError(
                    "PRIMARY KEY",
                    `Duplicate primary key in ${this.name}.`
                );
            }
        }

        // UNIQUE constraints.
        for (const columns of this.uniqueConstraints) {
            const key = this.keyFromRow(candidate, columns);

            const conflict = this.rows.some(row => {
                if (oldRow && row === oldRow) {
                    return false;
                }

                const otherKey = this.keyFromRow(row, columns);

                /*
                 * SQL NULL uniqueness semantics vary by database engine.
                 * This educational implementation treats any NULL-containing
                 * unique key as not comparable for uniqueness.
                 */
                if (key.some(value => value === null)) {
                    return false;
                }

                if (otherKey.some(value => value === null)) {
                    return false;
                }

                return this.keysEqual(otherKey, key);
            });

            if (conflict) {
                throw new ConstraintError(
                    "UNIQUE",
                    `Duplicate value for UNIQUE(${columns.join(", ")}).`
                );
            }
        }

        // Table-level CHECK constraints.
        for (const check of this.checkConstraints) {
            if (!check(candidate)) {
                throw new ConstraintError(
                    "CHECK",
                    `Table-level CHECK constraint failed in ${this.name}.`
                );
            }
        }

        // Conditional/partial uniqueness.
        for (const index of this.partialUniqueIndexes) {
            if (!index.predicate(candidate)) {
                continue;
            }

            const key = this.keyFromRow(candidate, index.columns);

            const conflict = this.rows.some(row => {
                if (oldRow && row === oldRow) {
                    return false;
                }

                if (!index.predicate(row)) {
                    return false;
                }

                return this.keysEqual(
                    this.keyFromRow(row, index.columns),
                    key
                );
            });

            if (conflict) {
                throw new ConstraintError(
                    "PARTIAL UNIQUE",
                    `Conditional uniqueness failed for ${index.columns.join(", ")}.`
                );
            }
        }
    }

    keyFromRow(row, columns) {
        return columns.map(column => row[column]);
    }

    keysEqual(left, right) {
        return (
            left.length === right.length &&
            left.every((value, index) => value === right[index])
        );
    }

    all() {
        return deepClone(this.rows);
    }
}


// -----------------------------------------------------------------------------
// 4. FOREIGN KEY SUPPORT
// -----------------------------------------------------------------------------

class ForeignKeyDefinition {
    constructor({
        childColumns,
        parentTable,
        parentColumns,
        onDelete = "RESTRICT",
        onUpdate = "RESTRICT"
    }) {
        this.childColumns = childColumns;
        this.parentTable = parentTable;
        this.parentColumns = parentColumns;
        this.onDelete = onDelete;
        this.onUpdate = onUpdate;
    }
}

class Database {
    constructor() {
        this.tables = new Map();
        this.transactionSnapshot = null;
        this.inTransaction = false;
    }

    addTable(table) {
        if (this.tables.has(table.name)) {
            throw new Error(`Table '${table.name}' already exists.`);
        }

        this.tables.set(table.name, table);
        return table;
    }

    table(name) {
        const table = this.tables.get(name);

        if (!table) {
            throw new Error(`Table '${name}' does not exist.`);
        }

        return table;
    }

    insert(tableName, row) {
        const table = this.table(tableName);

        // First perform the local constraints.
        const inserted = table.insert(row);

        // Then enforce foreign keys.
        try {
            this.validateForeignKeys();
        } catch (error) {
            table.delete(
                candidate =>
                    JSON.stringify(candidate) === JSON.stringify(inserted)
            );
            throw error;
        }

        return inserted;
    }

    update(tableName, predicate, changes) {
        const table = this.table(tableName);
        const oldRows = table.all();

        const count = table.update(predicate, changes);

        try {
            this.validateForeignKeys();
        } catch (error) {
            table.rows = oldRows;
            throw error;
        }

        return count;
    }

    delete(tableName, predicate) {
        const table = this.table(tableName);

        const oldRows = table.all();
        const deletedRows = table.rows.filter(predicate);

        table.delete(predicate);

        try {
            this.enforceDeleteActions(tableName, deletedRows);
            this.validateForeignKeys();
        } catch (error) {
            table.rows = oldRows;
            throw error;
        }

        return deletedRows.length;
    }

    validateForeignKeys() {
        for (const childTable of this.tables.values()) {
            for (const foreignKey of childTable.foreignKeys) {
                const parentTable = this.table(foreignKey.parentTable);

                for (const childRow of childTable.rows) {
                    const childKey = foreignKey.childColumns.map(
                        column => childRow[column]
                    );

                    /*
                     * SQL foreign keys normally permit NULL foreign-key
                     * components when the child column is nullable.
                     */
                    if (childKey.some(value => value === null)) {
                        continue;
                    }

                    const parentExists = parentTable.rows.some(parentRow => {
                        const parentKey = foreignKey.parentColumns.map(
                            column => parentRow[column]
                        );

                        return childKey.every(
                            (value, index) => value === parentKey[index]
                        );
                    });

                    if (!parentExists) {
                        throw new ConstraintError(
                            "FOREIGN KEY",
                            `Foreign key violation in ${childTable.name}.`
                        );
                    }
                }
            }
        }
    }

    enforceDeleteActions(parentTableName, deletedRows) {
        if (deletedRows.length === 0) {
            return;
        }

        for (const childTable of this.tables.values()) {
            for (const foreignKey of childTable.foreignKeys) {
                if (foreignKey.parentTable !== parentTableName) {
                    continue;
                }

                const parentTable = this.table(parentTableName);

                for (const deletedParent of deletedRows) {
                    const matchingChildRows = childTable.rows.filter(
                        childRow => {
                            return foreignKey.childColumns.every(
                                (childColumn, index) =>
                                    childRow[childColumn] ===
                                    deletedParent[foreignKey.parentColumns[index]]
                            );
                        }
                    );

                    if (matchingChildRows.length === 0) {
                        continue;
                    }

                    if (foreignKey.onDelete === "RESTRICT") {
                        throw new ConstraintError(
                            "FOREIGN KEY",
                            `Cannot delete referenced row from ${parentTable.name}.`
                        );
                    }

                    if (foreignKey.onDelete === "CASCADE") {
                        childTable.rows = childTable.rows.filter(
                            childRow => !matchingChildRows.includes(childRow)
                        );
                    }

                    if (foreignKey.onDelete === "SET NULL") {
                        for (const childRow of matchingChildRows) {
                            for (const childColumn of foreignKey.childColumns) {
                                childRow[childColumn] = null;
                            }
                        }
                    }
                }
            }
        }
    }

    transaction(callback) {
        if (this.inTransaction) {
            throw new TransactionError("Nested transactions are not supported.");
        }

        this.transactionSnapshot = new Map();

        for (const [name, table] of this.tables) {
            this.transactionSnapshot.set(name, table.all());
        }

        this.inTransaction = true;

        try {
            const result = callback();
            this.validateForeignKeys();

            this.transactionSnapshot = null;
            this.inTransaction = false;

            return result;
        } catch (error) {
            for (const [name, rows] of this.transactionSnapshot) {
                this.table(name).rows = rows;
            }

            this.transactionSnapshot = null;
            this.inTransaction = false;

            throw error;
        }
    }
}


// -----------------------------------------------------------------------------
// 5. SCHEMA CREATION
// -----------------------------------------------------------------------------

function buildCommerceDatabase() {
    const database = new Database();

    database.addTable(
        new Table(
            "customers",
            [
                new ColumnDefinition({
                    name: "customerId",
                    nullable: false,
                    primaryKey: true
                }),
                new ColumnDefinition({
                    name: "email",
                    nullable: false
                }),
                new ColumnDefinition({
                    name: "name",
                    nullable: false
                }),
                new ColumnDefinition({
                    name: "age",
                    nullable: false,
                    check: value => value >= 18
                }),
                new ColumnDefinition({
                    name: "status",
                    nullable: false,
                    defaultValue: "active",
                    check: value => ["active", "inactive"].includes(value)
                })
            ],
            {
                primaryKey: ["customerId"],
                uniqueConstraints: [["email"]]
            }
        )
    );

    database.addTable(
        new Table(
            "orders",
            [
                new ColumnDefinition({
                    name: "orderId",
                    nullable: false,
                    primaryKey: true
                }),
                new ColumnDefinition({
                    name: "customerId",
                    nullable: false
                }),
                new ColumnDefinition({
                    name: "amountCents",
                    nullable: false,
                    check: value => value > 0
                }),
                new ColumnDefinition({
                    name: "status",
                    nullable: false,
                    defaultValue: "pending",
                    check: value =>
                        ["pending", "paid", "cancelled"].includes(value)
                })
            ],
            {
                primaryKey: ["orderId"],
                foreignKeys: [
                    new ForeignKeyDefinition({
                        childColumns: ["customerId"],
                        parentTable: "customers",
                        parentColumns: ["customerId"],
                        onDelete: "RESTRICT"
                    })
                ]
            }
        )
    );

    database.addTable(
        new Table(
            "userAccounts",
            [
                new ColumnDefinition({
                    name: "userId",
                    nullable: false,
                    primaryKey: true
                }),
                new ColumnDefinition({
                    name: "phone",
                    nullable: false
                }),
                new ColumnDefinition({
                    name: "active",
                    nullable: false,
                    check: value => value === true || value === false
                })
            ],
            {
                primaryKey: ["userId"],
                partialUniqueIndexes: [
                    {
                        columns: ["phone"],
                        predicate: row => row.active === true
                    }
                ]
            }
        )
    );

    return database;
}


// -----------------------------------------------------------------------------
// 6. BEGINNER EXAMPLES
// -----------------------------------------------------------------------------

function demonstrateBasicConstraints(database) {
    printSection("1. Basic constraints");

    database.insert("customers", {
        customerId: 1,
        email: "alice@example.com",
        name: "Alice",
        age: 30
    });

    database.insert("orders", {
        orderId: 1001,
        customerId: 1,
        amountCents: 4999
    });

    console.log("Customers:");
    printRows(database.table("customers").all());

    console.log("\nOrders:");
    printRows(database.table("orders").all());

    const invalidOperations = [
        [
            "Duplicate primary key",
            () =>
                database.insert("customers", {
                    customerId: 1,
                    email: "bob@example.com",
                    name: "Bob",
                    age: 25
                })
        ],
        [
            "Duplicate unique email",
            () =>
                database.insert("customers", {
                    customerId: 2,
                    email: "alice@example.com",
                    name: "Another Alice",
                    age: 25
                })
        ],
        [
            "Missing required value",
            () =>
                database.insert("customers", {
                    customerId: 3,
                    email: null,
                    name: "No Email",
                    age: 25
                })
        ],
        [
            "CHECK violation",
            () =>
                database.insert("customers", {
                    customerId: 3,
                    email: "young@example.com",
                    name: "Young",
                    age: 17
                })
        ],
        [
            "FOREIGN KEY violation",
            () =>
                database.insert("orders", {
                    orderId: 1002,
                    customerId: 999,
                    amountCents: 1000
                })
        ]
    ];

    for (const [description, operation] of invalidOperations) {
        try {
            operation();
        } catch (error) {
            console.log(
                `${description}: rejected -> ${error.name}: ${error.message}`
            );
        }
    }
}


// -----------------------------------------------------------------------------
// 7. APPLICATION VALIDATION
// -----------------------------------------------------------------------------

function validateCustomerInput(input) {
    const errors = [];

    if (typeof input.email !== "string" || input.email.trim() === "") {
        errors.push("Email is required.");
    }

    if (typeof input.email === "string" && !input.email.includes("@")) {
        errors.push("Email must contain '@'.");
    }

    if (typeof input.name !== "string" || input.name.trim() === "") {
        errors.push("Name is required.");
    }

    if (!Number.isInteger(input.age) || input.age < 18) {
        errors.push("Age must be an integer of at least 18.");
    }

    return errors;
}

function demonstrateValidationLayers(database) {
    printSection("2. Application validation versus database enforcement");

    const invalidInput = {
        email: "invalid-email",
        name: "",
        age: 15
    };

    console.log("Application validation:");
    console.log(validateCustomerInput(invalidInput));

    const validInput = {
        email: "diana@example.com",
        name: "Diana",
        age: 28
    };

    const errors = validateCustomerInput(validInput);

    if (errors.length === 0) {
        database.insert("customers", {
            customerId: 2,
            ...validInput
        });
    }

    console.log("Database-enforced rows:");
    printRows(database.table("customers").all());

    /*
     * Application validation improves user experience.
     * Database constraints protect the stored data even if another client
     * bypasses the application validation.
     */
}


// -----------------------------------------------------------------------------
// 8. COMPOSITE CONSTRAINTS
// -----------------------------------------------------------------------------

function demonstrateCompositeConstraints() {
    printSection("3. Composite uniqueness");

    const enrollmentTable = new Table(
        "enrollments",
        [
            new ColumnDefinition({
                name: "studentId",
                nullable: false
            }),
            new ColumnDefinition({
                name: "courseId",
                nullable: false
            }),
            new ColumnDefinition({
                name: "grade",
                nullable: true,
                check: value =>
                    ["A", "B", "C", "D", "F"].includes(value)
            })
        ],
        {
            primaryKey: ["studentId", "courseId"]
        }
    );

    enrollmentTable.insert({
        studentId: 10,
        courseId: 501,
        grade: "A"
    });

    try {
        enrollmentTable.insert({
            studentId: 10,
            courseId: 501,
            grade: "B"
        });
    } catch (error) {
        console.log(
            `Composite key correctly rejected: ${error.message}`
        );
    }

    printRows(enrollmentTable.all());
}


// -----------------------------------------------------------------------------
// 9. CONDITIONAL UNIQUENESS
// -----------------------------------------------------------------------------

function demonstratePartialUniqueIndex(database) {
    printSection("4. Conditional uniqueness");

    database.insert("userAccounts", {
        userId: 1,
        phone: "+911111111111",
        active: true
    });

    database.insert("userAccounts", {
        userId: 2,
        phone: "+911111111111",
        active: false
    });

    /*
     * The inactive historical account may share the phone number.
     * A second active account may not.
     */

    try {
        database.insert("userAccounts", {
            userId: 3,
            phone: "+911111111111",
            active: true
        });
    } catch (error) {
        console.log(
            `Active duplicate rejected: ${error.constraintType}`
        );
    }

    printRows(database.table("userAccounts").all());
}


// -----------------------------------------------------------------------------
// 10. TRANSACTIONS
// -----------------------------------------------------------------------------

function demonstrateTransactions(database) {
    printSection("5. Transactions and atomicity");

    const accounts = new Table(
        "accounts",
        [
            new ColumnDefinition({
                name: "accountId",
                nullable: false,
                primaryKey: true
            }),
            new ColumnDefinition({
                name: "owner",
                nullable: false
            }),
            new ColumnDefinition({
                name: "balanceCents",
                nullable: false,
                check: value => value >= 0
            })
        ],
        {
            primaryKey: ["accountId"]
        }
    );

    database.addTable(accounts);

    accounts.insert({
        accountId: 1,
        owner: "Asha",
        balanceCents: 10000
    });

    accounts.insert({
        accountId: 2,
        owner: "Rahul",
        balanceCents: 5000
    });

    try {
        database.transaction(() => {
            database.update(
                "accounts",
                row => row.accountId === 1,
                {
                    balanceCents: 3000
                }
            );

            /*
             * This would produce 12000, which is valid. The example then
             * deliberately creates an invalid negative balance in order to
             * demonstrate rollback.
             */
            database.update(
                "accounts",
                row => row.accountId === 2,
                {
                    balanceCents: -7000
                }
            );
        });
    } catch (error) {
        console.log(`Transaction failed: ${error.message}`);
    }

    /*
     * Because the transaction rolled back, Asha's original balance is still
     * present. Partial changes must not survive a failed atomic operation.
     */
    printRows(accounts.all());
}


// -----------------------------------------------------------------------------
// 11. NULL SEMANTICS
// -----------------------------------------------------------------------------

function demonstrateNullSemantics() {
    printSection("6. NULL and uniqueness semantics");

    const table = new Table(
        "nullableValues",
        [
            new ColumnDefinition({
                name: "id",
                nullable: false,
                primaryKey: true
            }),
            new ColumnDefinition({
                name: "code",
                nullable: true
            })
        ],
        {
            primaryKey: ["id"],
            uniqueConstraints: [["code"]]
        }
    );

    table.insert({
        id: 1,
        code: null
    });

    table.insert({
        id: 2,
        code: null
    });

    /*
     * SQL NULL means "unknown/missing", not an ordinary value.
     * The exact treatment of NULL under UNIQUE constraints varies by DBMS,
     * so schema designers should verify the semantics of their target engine.
     */

    console.log("Nullable unique values:");
    printRows(table.all());
}


// -----------------------------------------------------------------------------
// 12. REFERENTIAL ACTIONS
// -----------------------------------------------------------------------------

function demonstrateReferentialActions() {
    printSection("7. Referential actions");

    const database = new Database();

    database.addTable(
        new Table(
            "departments",
            [
                new ColumnDefinition({
                    name: "departmentId",
                    nullable: false,
                    primaryKey: true
                }),
                new ColumnDefinition({
                    name: "name",
                    nullable: false
                })
            ],
            {
                primaryKey: ["departmentId"],
                uniqueConstraints: [["name"]]
            }
        )
    );

    database.addTable(
        new Table(
            "employees",
            [
                new ColumnDefinition({
                    name: "employeeId",
                    nullable: false,
                    primaryKey: true
                }),
                new ColumnDefinition({
                    name: "departmentId",
                    nullable: true
                }),
                new ColumnDefinition({
                    name: "name",
                    nullable: false
                })
            ],
            {
                primaryKey: ["employeeId"],
                foreignKeys: [
                    new ForeignKeyDefinition({
                        childColumns: ["departmentId"],
                        parentTable: "departments",
                        parentColumns: ["departmentId"],
                        onDelete: "SET NULL"
                    })
                ]
            }
        )
    );

    database.insert("departments", {
        departmentId: 1,
        name: "Engineering"
    });

    database.insert("employees", {
        employeeId: 1,
        departmentId: 1,
        name: "Priya"
    });

    database.delete(
        "departments",
        row => row.departmentId === 1
    );

    console.log("Employees after SET NULL:");
    printRows(database.table("employees").all());
}


// -----------------------------------------------------------------------------
// 13. TESTING
// -----------------------------------------------------------------------------

function expectConstraintError(description, operation) {
    try {
        operation();
        console.log(`FAIL: ${description}`);
    } catch (error) {
        if (error instanceof ConstraintError) {
            console.log(`PASS: ${description}`);
        } else {
            console.log(`FAIL: ${description} -> unexpected error`);
        }
    }
}

function runTests() {
    printSection("8. Constraint tests");

    const database = buildCommerceDatabase();

    database.insert("customers", {
        customerId: 1,
        email: "test@example.com",
        name: "Test",
        age: 25
    });

    expectConstraintError(
        "UNIQUE rejects duplicate email",
        () =>
            database.insert("customers", {
                customerId: 2,
                email: "test@example.com",
                name: "Duplicate",
                age: 25
            })
    );

    expectConstraintError(
        "NOT NULL rejects missing email",
        () =>
            database.insert("customers", {
                customerId: 2,
                email: null,
                name: "Missing",
                age: 25
            })
    );

    expectConstraintError(
        "CHECK rejects underage customer",
        () =>
            database.insert("customers", {
                customerId: 2,
                email: "young@example.com",
                name: "Young",
                age: 17
            })
    );

    expectConstraintError(
        "FOREIGN KEY rejects unknown customer",
        () =>
            database.insert("orders", {
                orderId: 2,
                customerId: 999,
                amountCents: 500
            })
    );

    expectConstraintError(
        "CHECK rejects negative order amount",
        () =>
            database.insert("orders", {
                orderId: 2,
                customerId: 1,
                amountCents: -1
            })
    );
}


// -----------------------------------------------------------------------------
// 14. PERFORMANCE AND CONCURRENCY DISCUSSION
// -----------------------------------------------------------------------------

function demonstrateEngineeringConsiderations() {
    printSection("9. Performance, concurrency, and production considerations");

    const considerations = [
        [
            "Indexes",
            "UNIQUE rules normally require efficient uniqueness checking. Indexes speed reads and constraint checks but increase storage and write cost."
        ],
        [
            "Transactions",
            "Multi-step changes should be atomic when partial completion would violate a business invariant."
        ],
        [
            "Concurrency",
            "A check-then-insert sequence in application code can race. An authoritative UNIQUE constraint closes this correctness gap at the database layer."
        ],
        [
            "Isolation",
            "Real databases provide transaction isolation and locking/MVCC mechanisms. An in-memory JavaScript object model does not reproduce those guarantees."
        ],
        [
            "Validation",
            "Validate early in the application for good error messages, then enforce authoritative invariants in the database."
        ],
        [
            "Migrations",
            "Adding NOT NULL, UNIQUE, CHECK, or FOREIGN KEY rules to existing data requires checking and possibly repairing incompatible records before enforcement."
        ],
        [
            "Security",
            "Constraints are not authorization controls. Access control, authentication, input handling, parameterized queries, and auditing remain separate concerns."
        ]
    ];

    for (const [topic, explanation] of considerations) {
        console.log(`${topic}: ${explanation}`);
    }
}


// -----------------------------------------------------------------------------
// 15. COMMON MISTAKES
// -----------------------------------------------------------------------------

function printCommonMistakes() {
    printSection("10. Common mistakes");

    const mistakes = [
        "Relying exclusively on browser validation.",
        "Treating NULL as equivalent to an empty string or zero.",
        "Assuming all database engines implement NULL and constraint behavior identically.",
        "Forgetting foreign-key enforcement or configuration.",
        "Using a UNIQUE rule when the business rule actually requires conditional uniqueness.",
        "Using CASCADE without understanding the historical-data consequences.",
        "Checking uniqueness in JavaScript and then inserting without a database-level UNIQUE constraint.",
        "Ignoring transaction rollback after a failed multi-step operation.",
        "Assuming row-level CHECK constraints can automatically enforce cross-row aggregate rules.",
        "Returning raw database errors to end users without appropriate application-level translation."
    ];

    mistakes.forEach((mistake, index) => {
        console.log(`${index + 1}. ${mistake}`);
    });
}


// -----------------------------------------------------------------------------
// 16. MAIN
// -----------------------------------------------------------------------------

function main() {
    console.log(
        "CONSTRAINTS, DATA INTEGRITY, AND CONSTRAINT ENFORCEMENT"
    );
    console.log(
        "JavaScript implementation and in-memory relational case study"
    );

    const database = buildCommerceDatabase();

    demonstrateBasicConstraints(database);
    demonstrateValidationLayers(database);
    demonstrateCompositeConstraints();
    demonstratePartialUniqueIndex(database);
    demonstrateTransactions(database);
    demonstrateNullSemantics();
    demonstrateReferentialActions();
    runTests();
    demonstrateEngineeringConsiderations();
    printCommonMistakes();

    console.log("\nStudy execution completed successfully.");
}

main();
