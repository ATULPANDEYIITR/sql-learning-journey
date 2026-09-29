/*
FOREIGN KEY: Referential Integrity, Parent-Child Relationships,
and Cascading Actions

This self-contained JavaScript file teaches the conceptual and practical
side of foreign keys while using in-memory data structures to model the
same behavior that a relational database enforces.

The implementation intentionally builds a small relational integrity engine.
This makes the mechanisms visible without requiring an external database
package.

Run with:
    node foreign_key.js
*/

"use strict";

class ForeignKeyError extends Error {
    constructor(message) {
        super(message);
        this.name = "ForeignKeyError";
    }
}

class Table {
    constructor(name, primaryKey) {
        this.name = name;
        this.primaryKey = primaryKey;
        this.rows = new Map();
    }

    insert(row) {
        const key = row[this.primaryKey];

        if (key === undefined || key === null) {
            throw new ForeignKeyError(
                `${this.name}: primary key ${this.primaryKey} is required`
            );
        }

        if (this.rows.has(key)) {
            throw new ForeignKeyError(
                `${this.name}: duplicate primary key ${key}`
            );
        }

        this.rows.set(key, structuredClone(row));
    }

    get(key) {
        return this.rows.get(key);
    }

    delete(key) {
        this.rows.delete(key);
    }

    all() {
        return [...this.rows.values()].map((row) => structuredClone(row));
    }
}

class ForeignKeyConstraint {
    constructor({
        childTable,
        childColumn,
        parentTable,
        parentColumn,
        onDelete = "RESTRICT",
        onUpdate = "RESTRICT",
    }) {
        this.childTable = childTable;
        this.childColumn = childColumn;
        this.parentTable = parentTable;
        this.parentColumn = parentColumn;
        this.onDelete = onDelete;
        this.onUpdate = onUpdate;

        const supportedActions = new Set([
            "RESTRICT",
            "NO ACTION",
            "CASCADE",
            "SET NULL",
            "SET DEFAULT",
        ]);

        if (!supportedActions.has(onDelete)) {
            throw new Error(`Unsupported ON DELETE action: ${onDelete}`);
        }

        if (!supportedActions.has(onUpdate)) {
            throw new Error(`Unsupported ON UPDATE action: ${onUpdate}`);
        }
    }

    findChildren(parentKey) {
        return this.childTable.all().filter(
            (child) => child[this.childColumn] === parentKey
        );
    }

    validateInsert(childRow) {
        const foreignKeyValue = childRow[this.childColumn];

        // A NULL foreign key represents no relationship when the column
        // is nullable. A real database can separately enforce NOT NULL.
        if (foreignKeyValue === null || foreignKeyValue === undefined) {
            return;
        }

        const parent = this.parentTable.get(foreignKeyValue);

        if (!parent) {
            throw new ForeignKeyError(
                `Cannot insert child row: ${this.childTable.name}.${this.childColumn}=` +
                `${foreignKeyValue} does not reference an existing ` +
                `${this.parentTable.name}.${this.parentColumn}`
            );
        }
    }

    handleParentDelete(parentKey) {
        const children = this.findChildren(parentKey);

        if (children.length === 0) {
            return;
        }

        switch (this.onDelete) {
            case "RESTRICT":
            case "NO ACTION":
                throw new ForeignKeyError(
                    `Cannot delete parent ${parentKey}: ` +
                    `${children.length} child row(s) still reference it`
                );

            case "CASCADE":
                for (const child of children) {
                    this.childTable.delete(child[this.childTable.primaryKey]);
                }
                break;

            case "SET NULL":
                for (const child of children) {
                    const updatedChild = {
                        ...child,
                        [this.childColumn]: null,
                    };
                    this.childTable.rows.set(
                        updatedChild[this.childTable.primaryKey],
                        updatedChild
                    );
                }
                break;

            case "SET DEFAULT":
                throw new ForeignKeyError(
                    "SET DEFAULT requires a schema-level default in this demonstration"
                );

            default:
                throw new Error(`Unknown delete action ${this.onDelete}`);
        }
    }

    handleParentUpdate(oldKey, newKey) {
        const children = this.findChildren(oldKey);

        if (children.length === 0 || oldKey === newKey) {
            return;
        }

        switch (this.onUpdate) {
            case "RESTRICT":
            case "NO ACTION":
                throw new ForeignKeyError(
                    `Cannot change parent key ${oldKey}: child rows reference it`
                );

            case "CASCADE":
                for (const child of children) {
                    const updatedChild = {
                        ...child,
                        [this.childColumn]: newKey,
                    };

                    this.childTable.rows.set(
                        updatedChild[this.childTable.primaryKey],
                        updatedChild
                    );
                }
                break;

            case "SET NULL":
                for (const child of children) {
                    const updatedChild = {
                        ...child,
                        [this.childColumn]: null,
                    };

                    this.childTable.rows.set(
                        updatedChild[this.childTable.primaryKey],
                        updatedChild
                    );
                }
                break;

            default:
                throw new ForeignKeyError(
                    `ON UPDATE ${this.onUpdate} is not implemented for this demo`
                );
        }
    }
}

class RelationalDatabaseDemo {
    constructor() {
        this.tables = new Map();
        this.constraints = [];
    }

    addTable(table) {
        this.tables.set(table.name, table);
    }

    addForeignKey(constraint) {
        this.constraints.push(constraint);
    }

    getTable(name) {
        const table = this.tables.get(name);

        if (!table) {
            throw new Error(`Unknown table: ${name}`);
        }

        return table;
    }

    insert(tableName, row) {
        const table = this.getTable(tableName);

        // Validate all constraints where this table is the child.
        for (const constraint of this.constraints) {
            if (constraint.childTable === table) {
                constraint.validateInsert(row);
            }
        }

        table.insert(row);
    }

    delete(tableName, primaryKey) {
        const table = this.getTable(tableName);

        // Parent actions happen before the parent row disappears.
        for (const constraint of this.constraints) {
            if (constraint.parentTable === table) {
                constraint.handleParentDelete(primaryKey);
            }
        }

        table.delete(primaryKey);
    }

    updatePrimaryKey(tableName, oldKey, newKey) {
        const table = this.getTable(tableName);

        if (table.get(newKey)) {
            throw new ForeignKeyError(
                `Cannot update ${tableName}: target key ${newKey} already exists`
            );
        }

        const row = table.get(oldKey);

        if (!row) {
            throw new ForeignKeyError(
                `Cannot update ${tableName}: key ${oldKey} does not exist`
            );
        }

        for (const constraint of this.constraints) {
            if (constraint.parentTable === table) {
                constraint.handleParentUpdate(oldKey, newKey);
            }
        }

        table.delete(oldKey);
        table.rows.set(newKey, {
            ...row,
            [table.primaryKey]: newKey,
        });
    }

    print(tableName) {
        console.table(this.getTable(tableName).all());
    }
}

function section(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}

function subsection(title) {
    console.log(`\n--- ${title} ---`);
}

function runBasicParentChildExample() {
    section("1. Parent-Child Relationship");

    const database = new RelationalDatabaseDemo();

    const customers = new Table("customers", "customerId");
    const orders = new Table("orders", "orderId");

    database.addTable(customers);
    database.addTable(orders);

    database.addForeignKey(
        new ForeignKeyConstraint({
            childTable: orders,
            childColumn: "customerId",
            parentTable: customers,
            parentColumn: "customerId",
            onDelete: "RESTRICT",
            onUpdate: "CASCADE",
        })
    );

    database.insert("customers", {
        customerId: 1,
        name: "Anika",
    });

    database.insert("customers", {
        customerId: 2,
        name: "Rahul",
    });

    database.insert("orders", {
        orderId: 101,
        customerId: 1,
        amount: 1250,
    });

    database.insert("orders", {
        orderId: 102,
        customerId: 1,
        amount: 800,
    });

    database.insert("orders", {
        orderId: 103,
        customerId: 2,
        amount: 450,
    });

    subsection("Customers");
    database.print("customers");

    subsection("Orders");
    database.print("orders");

    return database;
}

function demonstrateInvalidReference(database) {
    section("2. Referential Integrity");

    try {
        database.insert("orders", {
            orderId: 104,
            customerId: 999,
            amount: 100,
        });
    } catch (error) {
        if (error instanceof ForeignKeyError) {
            console.log("Expected constraint failure:");
            console.log(error.message);
        } else {
            throw error;
        }
    }
}

function demonstrateRestrict(database) {
    section("3. ON DELETE RESTRICT");

    try {
        database.delete("customers", 1);
    } catch (error) {
        console.log("Expected RESTRICT failure:");
        console.log(error.message);
    }

    console.log(
        "The parent remains because deleting it would create orphaned orders."
    );

    subsection("Delete child rows first");

    database.getTable("orders").delete(101);
    database.getTable("orders").delete(102);

    database.delete("customers", 1);

    database.print("customers");
    database.print("orders");
}

function demonstrateUpdateCascade() {
    section("4. ON UPDATE CASCADE");

    const database = new RelationalDatabaseDemo();

    const customers = new Table("customers", "customerId");
    const orders = new Table("orders", "orderId");

    database.addTable(customers);
    database.addTable(orders);

    database.addForeignKey(
        new ForeignKeyConstraint({
            childTable: orders,
            childColumn: "customerId",
            parentTable: customers,
            parentColumn: "customerId",
            onDelete: "RESTRICT",
            onUpdate: "CASCADE",
        })
    );

    database.insert("customers", {
        customerId: 10,
        name: "Meera",
    });

    database.insert("orders", {
        orderId: 200,
        customerId: 10,
        amount: 900,
    });

    subsection("Before key update");
    database.print("customers");
    database.print("orders");

    database.updatePrimaryKey("customers", 10, 11);

    subsection("After key update");
    database.print("customers");
    database.print("orders");
}

function demonstrateDeleteCascade() {
    section("5. ON DELETE CASCADE");

    const database = new RelationalDatabaseDemo();

    const customers = new Table("customers", "customerId");
    const orders = new Table("orders", "orderId");
    const payments = new Table("payments", "paymentId");

    database.addTable(customers);
    database.addTable(orders);
    database.addTable(payments);

    database.addForeignKey(
        new ForeignKeyConstraint({
            childTable: orders,
            childColumn: "customerId",
            parentTable: customers,
            parentColumn: "customerId",
            onDelete: "CASCADE",
        })
    );

    database.addForeignKey(
        new ForeignKeyConstraint({
            childTable: payments,
            childColumn: "orderId",
            parentTable: orders,
            parentColumn: "orderId",
            onDelete: "CASCADE",
        })
    );

    database.insert("customers", {
        customerId: 1,
        name: "Cascade Customer",
    });

    database.insert("orders", {
        orderId: 500,
        customerId: 1,
        amount: 500,
    });

    database.insert("payments", {
        paymentId: 900,
        orderId: 500,
        amount: 500,
    });

    subsection("Before deletion");
    database.print("customers");
    database.print("orders");
    database.print("payments");

    database.delete("customers", 1);

    subsection("After deletion");
    database.print("customers");
    database.print("orders");
    database.print("payments");
}

function demonstrateSetNull() {
    section("6. ON DELETE SET NULL");

    const database = new RelationalDatabaseDemo();

    const departments = new Table("departments", "departmentId");
    const employees = new Table("employees", "employeeId");

    database.addTable(departments);
    database.addTable(employees);

    database.addForeignKey(
        new ForeignKeyConstraint({
            childTable: employees,
            childColumn: "departmentId",
            parentTable: departments,
            parentColumn: "departmentId",
            onDelete: "SET NULL",
        })
    );

    database.insert("departments", {
        departmentId: 1,
        name: "Research",
    });

    database.insert("employees", {
        employeeId: 1,
        name: "Dev",
        departmentId: 1,
    });

    database.delete("departments", 1);

    database.print("employees");
}

function demonstrateOptionalRelationship() {
    section("7. Optional vs Mandatory Relationships");

    const optionalEmployee = {
        employeeId: 1,
        name: "Unassigned Employee",
        departmentId: null,
    };

    console.log(
        "Optional relationship:",
        JSON.stringify(optionalEmployee)
    );

    console.log(
        "If departmentId is mandatory, a database schema should use NOT NULL."
    );
}

function demonstrateSelfReference() {
    section("8. Self-Referencing Foreign Key");

    const database = new RelationalDatabaseDemo();
    const organization = new Table("organization", "employeeId");

    database.addTable(organization);

    database.addForeignKey(
        new ForeignKeyConstraint({
            childTable: organization,
            childColumn: "managerId",
            parentTable: organization,
            parentColumn: "employeeId",
            onDelete: "SET NULL",
        })
    );

    database.insert("organization", {
        employeeId: 1,
        name: "CEO",
        managerId: null,
    });

    database.insert("organization", {
        employeeId: 2,
        name: "Engineering Manager",
        managerId: 1,
    });

    database.insert("organization", {
        employeeId: 3,
        name: "Developer",
        managerId: 2,
    });

    database.print("organization");

    database.delete("organization", 2);

    subsection("After manager deletion");
    database.print("organization");
}

function demonstrateValidation() {
    section("9. Application Validation");

    function validateRequiredParent(parentId, parentTable) {
        if (!parentTable.get(parentId)) {
            throw new ForeignKeyError(
                `Parent ${parentId} does not exist`
            );
        }
    }

    const parents = new Table("parents", "id");

    parents.insert({
        id: 1,
        name: "Valid Parent",
    });

    validateRequiredParent(1, parents);

    try {
        validateRequiredParent(999, parents);
    } catch (error) {
        console.log("Application validation:", error.message);
    }

    console.log(
        "Application validation improves error messages, but the database "
        + "constraint remains the authoritative integrity boundary."
    );
}

function demonstrateTransactionsConceptually() {
    section("10. Transactional Thinking");

    const changes = [];

    try {
        changes.push("insert parent");
        changes.push("insert child");

        // Simulate an integrity failure.
        throw new ForeignKeyError(
            "Third operation references a nonexistent parent"
        );
    } catch (error) {
        changes.length = 0;
        console.log("Transaction rolled back.");
        console.log("Pending changes:", changes);
        console.log("Reason:", error.message);
    }
}

function demonstrateCompositeKeyConcept() {
    section("11. Composite Foreign Key");

    const offerings = new Map();

    offerings.set("CS101|2026-FALL", {
        courseCode: "CS101",
        semester: "2026-FALL",
        instructor: "Dr. Rao",
    });

    const validEnrollment = {
        student: "Arjun",
        courseCode: "CS101",
        semester: "2026-FALL",
    };

    const invalidEnrollment = {
        student: "Nisha",
        courseCode: "CS101",
        semester: "2027-SPRING",
    };

    const keyFor = (record) =>
        `${record.courseCode}|${record.semester}`;

    console.log(
        "Valid composite reference exists:",
        offerings.has(keyFor(validEnrollment))
    );

    console.log(
        "Invalid composite reference exists:",
        offerings.has(keyFor(invalidEnrollment))
    );
}

function demonstratePerformance() {
    section("12. Performance Considerations");

    console.log(
        "Without an efficient lookup structure, finding every child row "
        + "for a parent can require scanning the entire child table."
    );

    console.log(
        "A database index on the child foreign-key column can make joins "
        + "and referential actions much faster for large tables."
    );

    const childRows = Array.from({ length: 10000 }, (_, index) => ({
        id: index + 1,
        parentId: (index % 100) + 1,
    }));

    console.time("linear child lookup");

    const matchingRows = childRows.filter(
        (row) => row.parentId === 50
    );

    console.timeEnd("linear child lookup");

    console.log("Matching rows:", matchingRows.length);
    console.log(
        "Real relational databases can use B-tree or other indexes instead "
        + "of scanning every child row."
    );
}

function demonstrateCommonMistakes() {
    section("13. Common Mistakes");

    const mistakes = [
        "Using a non-unique parent column as a reference target.",
        "Allowing required foreign keys to remain nullable.",
        "Disabling foreign-key enforcement.",
        "Using CASCADE without considering destructive consequences.",
        "Forgetting indexes on frequently queried foreign-key columns.",
        "Checking only application code and not enforcing integrity in the database.",
        "Confusing a foreign key with a unique constraint.",
        "Assuming every foreign key must use CASCADE.",
        "Using unstable natural keys when a stable surrogate key is more appropriate.",
    ];

    mistakes.forEach((mistake, index) => {
        console.log(`${index + 1}. ${mistake}`);
    });
}

function runAssertions() {
    section("14. Automated Assertions");

    const database = new RelationalDatabaseDemo();

    const parents = new Table("parents", "id");
    const children = new Table("children", "id");

    database.addTable(parents);
    database.addTable(children);

    database.addForeignKey(
        new ForeignKeyConstraint({
            childTable: children,
            childColumn: "parentId",
            parentTable: parents,
            parentColumn: "id",
            onDelete: "CASCADE",
        })
    );

    database.insert("parents", { id: 1, name: "Parent" });
    database.insert("children", {
        id: 1,
        parentId: 1,
        value: "Child",
    });

    if (children.all().length !== 1) {
        throw new Error("Expected one child");
    }

    let invalidInsertFailed = false;

    try {
        database.insert("children", {
            id: 2,
            parentId: 999,
            value: "Invalid",
        });
    } catch (error) {
        invalidInsertFailed = error instanceof ForeignKeyError;
    }

    if (!invalidInsertFailed) {
        throw new Error("Invalid foreign-key insert should fail");
    }

    database.delete("parents", 1);

    if (children.all().length !== 0) {
        throw new Error("CASCADE should remove dependent children");
    }

    console.log("All assertions passed.");
}

function main() {
    const database = runBasicParentChildExample();

    demonstrateInvalidReference(database);
    demonstrateRestrict(database);
    demonstrateUpdateCascade();
    demonstrateDeleteCascade();
    demonstrateSetNull();
    demonstrateOptionalRelationship();
    demonstrateSelfReference();
    demonstrateValidation();
    demonstrateTransactionsConceptually();
    demonstrateCompositeKeyConcept();
    demonstratePerformance();
    demonstrateCommonMistakes();
    runAssertions();

    section("15. Finished");
    console.log(
        "The demonstration covered foreign keys, referential integrity, "
        + "parent-child relationships, and common cascading actions."
    );
}

main();
