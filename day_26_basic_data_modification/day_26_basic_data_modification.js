/*
 * Basic Data Modification with SQL:
 * UPDATE, DELETE, Conditional Updates, and Safe Deletion
 *
 * This file uses JavaScript to demonstrate how an application can construct
 * and safely execute data-modification operations. It uses an in-memory
 * JavaScript data store to keep the file executable with plain Node.js.
 *
 * The SQL statements shown as strings correspond to real SQL patterns.
 * The data-store class simulates the database boundary so that the study
 * file requires no external npm package.
 */

"use strict";

// ---------------------------------------------------------------------------
// 1. SAMPLE DATA
// ---------------------------------------------------------------------------

const initialEmployees = [
    {
        employeeId: 1,
        employeeCode: "EMP001",
        fullName: "Aarav Sharma",
        department: "Engineering",
        salary: 75000,
        status: "ACTIVE",
        performanceScore: 91
    },
    {
        employeeId: 2,
        employeeCode: "EMP002",
        fullName: "Meera Singh",
        department: "Engineering",
        salary: 68000,
        status: "ACTIVE",
        performanceScore: 84
    },
    {
        employeeId: 3,
        employeeCode: "EMP003",
        fullName: "Kabir Verma",
        department: "Finance",
        salary: 62000,
        status: "ACTIVE",
        performanceScore: 76
    },
    {
        employeeId: 4,
        employeeCode: "EMP004",
        fullName: "Isha Gupta",
        department: "Human Resources",
        salary: 58000,
        status: "ACTIVE",
        performanceScore: 88
    },
    {
        employeeId: 5,
        employeeCode: "EMP005",
        fullName: "Rohan Das",
        department: "Operations",
        salary: 52000,
        status: "INACTIVE",
        performanceScore: 61
    }
];

function cloneEmployees() {
    return structuredClone(initialEmployees);
}

// ---------------------------------------------------------------------------
// 2. DATABASE-LIKE STORE
// ---------------------------------------------------------------------------

class EmployeeStore {
    constructor(employees = []) {
        this.employees = employees;
        this.auditLog = [];
    }

    findById(employeeId) {
        return this.employees.find(
            employee => employee.employeeId === employeeId
        );
    }

    findByCode(employeeCode) {
        return this.employees.find(
            employee => employee.employeeCode === employeeCode
        );
    }

    select(predicate = () => true) {
        return this.employees.filter(predicate);
    }

    update(predicate, changes) {
        let affectedRows = 0;

        for (const employee of this.employees) {
            if (predicate(employee)) {
                Object.assign(employee, changes(employee));
                affectedRows += 1;
            }
        }

        return affectedRows;
    }

    delete(predicate) {
        const originalLength = this.employees.length;

        this.employees = this.employees.filter(
            employee => !predicate(employee)
        );

        return originalLength - this.employees.length;
    }

    snapshot() {
        return structuredClone({
            employees: this.employees,
            auditLog: this.auditLog
        });
    }

    restore(snapshot) {
        this.employees = structuredClone(snapshot.employees);
        this.auditLog = structuredClone(snapshot.auditLog);
    }
}

// ---------------------------------------------------------------------------
// 3. BASIC UPDATE
// ---------------------------------------------------------------------------

function basicUpdate(store) {
    /*
     * SQL equivalent:
     *
     * UPDATE employees
     * SET salary = 78000
     * WHERE employee_id = 1;
     *
     * The predicate represents the WHERE clause.
     */
    return store.update(
        employee => employee.employeeId === 1,
        () => ({
            salary: 78000,
            lastModified: new Date().toISOString()
        })
    );
}

// ---------------------------------------------------------------------------
// 4. CONDITIONAL UPDATE
// ---------------------------------------------------------------------------

function conditionalUpdate(store) {
    /*
     * Multiple conditions correspond to:
     *
     * UPDATE employees
     * SET salary = salary * 1.05
     * WHERE department = 'Engineering'
     *   AND status = 'ACTIVE';
     */
    return store.update(
        employee =>
            employee.department === "Engineering" &&
            employee.status === "ACTIVE",
        employee => ({
            salary: Number((employee.salary * 1.05).toFixed(2)),
            lastModified: new Date().toISOString()
        })
    );
}

// ---------------------------------------------------------------------------
// 5. CASE-LIKE BUSINESS RULE
// ---------------------------------------------------------------------------

function performanceBasedUpdate(store) {
    /*
     * JavaScript conditional logic can represent SQL CASE expressions.
     * Each employee receives a different adjustment based on performance.
     */
    return store.update(
        employee => employee.status === "ACTIVE",
        employee => {
            let multiplier = 1;

            if (employee.performanceScore >= 90) {
                multiplier = 1.10;
            } else if (employee.performanceScore >= 80) {
                multiplier = 1.07;
            } else if (employee.performanceScore >= 70) {
                multiplier = 1.04;
            }

            return {
                salary: Number(
                    (employee.salary * multiplier).toFixed(2)
                ),
                lastModified: new Date().toISOString()
            };
        }
    );
}

// ---------------------------------------------------------------------------
// 6. INPUT VALIDATION
// ---------------------------------------------------------------------------

function validateStatus(status) {
    const allowedStatuses = new Set(["ACTIVE", "INACTIVE"]);

    if (!allowedStatuses.has(status)) {
        throw new Error(`Invalid status: ${status}`);
    }
}

function validateEmployeeId(employeeId) {
    if (!Number.isInteger(employeeId) || employeeId <= 0) {
        throw new Error("Employee ID must be a positive integer.");
    }
}

// ---------------------------------------------------------------------------
// 7. SAFE UPDATE BY BUSINESS KEY
// ---------------------------------------------------------------------------

function safeUpdateStatus(store, employeeCode, newStatus) {
    validateStatus(newStatus);

    /*
     * In a real SQL application, employeeCode and newStatus should be bound
     * parameters rather than inserted into SQL through string concatenation.
     *
     * Conceptually:
     *
     * UPDATE employees
     * SET status = ?
     * WHERE employee_code = ?;
     */
    return store.update(
        employee => employee.employeeCode === employeeCode,
        () => ({
            status: newStatus,
            lastModified: new Date().toISOString()
        })
    );
}

// ---------------------------------------------------------------------------
// 8. OPTIMISTIC CONDITIONAL UPDATE
// ---------------------------------------------------------------------------

function optimisticSalaryUpdate(
    store,
    employeeId,
    expectedSalary,
    newSalary
) {
    validateEmployeeId(employeeId);

    if (!Number.isFinite(newSalary) || newSalary < 0) {
        throw new Error("New salary must be a non-negative number.");
    }

    /*
     * The expected old value is part of the condition.
     *
     * SQL pattern:
     *
     * UPDATE employees
     * SET salary = ?
     * WHERE employee_id = ?
     *   AND salary = ?;
     *
     * If another process already changed the salary, zero rows are affected.
     */
    return store.update(
        employee =>
            employee.employeeId === employeeId &&
            employee.salary === expectedSalary,
        () => ({
            salary: newSalary,
            lastModified: new Date().toISOString()
        })
    );
}

// ---------------------------------------------------------------------------
// 9. PREVIEW BEFORE UPDATE
// ---------------------------------------------------------------------------

function previewCandidates(store, predicate) {
    return store.select(predicate).map(employee => ({
        employeeId: employee.employeeId,
        employeeCode: employee.employeeCode,
        fullName: employee.fullName
    }));
}

function previewAndUpdate(store) {
    const predicate = employee =>
        employee.status === "ACTIVE" &&
        employee.performanceScore >= 90;

    const preview = previewCandidates(store, predicate);

    console.log("\nRows selected before modification:");
    console.table(preview);

    const affectedRows = store.update(
        predicate,
        employee => ({
            salary: Number((employee.salary * 1.02).toFixed(2)),
            lastModified: new Date().toISOString()
        })
    );

    return affectedRows;
}

// ---------------------------------------------------------------------------
// 10. SAFE DELETE
// ---------------------------------------------------------------------------

function safeDelete(store, employeeId) {
    validateEmployeeId(employeeId);

    /*
     * SQL equivalent:
     *
     * DELETE FROM employees
     * WHERE employee_id = ?;
     */
    return store.delete(
        employee => employee.employeeId === employeeId
    );
}

// ---------------------------------------------------------------------------
// 11. CONDITIONAL DELETE
// ---------------------------------------------------------------------------

function conditionalDelete(store) {
    /*
     * Narrow conditions reduce accidental deletion.
     *
     * SQL equivalent:
     *
     * DELETE FROM employees
     * WHERE status = 'INACTIVE'
     *   AND department = 'Operations';
     */
    return store.delete(
        employee =>
            employee.status === "INACTIVE" &&
            employee.department === "Operations"
    );
}

// ---------------------------------------------------------------------------
// 12. DANGEROUS DELETE EXAMPLE
// ---------------------------------------------------------------------------

function explainDangerousDelete() {
    /*
     * NEVER execute this without an intentional reason:
     *
     * DELETE FROM employees;
     *
     * It removes every row.
     */
    console.log(
        "\nDangerous SQL pattern (not executed): DELETE FROM employees;"
    );
}

// ---------------------------------------------------------------------------
// 13. SOFT DELETE
// ---------------------------------------------------------------------------

function softDelete(store, employeeId) {
    /*
     * A soft delete changes state instead of physically removing the row.
     *
     * SQL:
     *
     * UPDATE employees
     * SET status = 'INACTIVE'
     * WHERE employee_id = ?;
     */
    return store.update(
        employee => employee.employeeId === employeeId,
        () => ({
            status: "INACTIVE",
            lastModified: new Date().toISOString()
        })
    );
}

// ---------------------------------------------------------------------------
// 14. AUDITED UPDATE
// ---------------------------------------------------------------------------

function auditedSalaryUpdate(store, employeeId, newSalary) {
    validateEmployeeId(employeeId);

    if (!Number.isFinite(newSalary) || newSalary < 0) {
        throw new Error("Salary must be a non-negative number.");
    }

    const employee = store.findById(employeeId);

    if (!employee) {
        throw new Error("Employee does not exist.");
    }

    const oldSalary = employee.salary;

    const affectedRows = store.update(
        candidate => candidate.employeeId === employeeId,
        () => ({
            salary: newSalary,
            lastModified: new Date().toISOString()
        })
    );

    if (affectedRows === 1) {
        store.auditLog.push({
            employeeId,
            action: "UPDATE",
            oldSalary,
            newSalary,
            changedAt: new Date().toISOString()
        });
    }

    return affectedRows;
}

// ---------------------------------------------------------------------------
// 15. TRANSACTION SIMULATION
// ---------------------------------------------------------------------------

function runTransaction(store, operation) {
    /*
     * Databases provide real transaction mechanisms. This function models
     * the same principle: capture state, execute changes, and restore state
     * when an error occurs.
     */
    const snapshot = store.snapshot();

    try {
        operation();
    } catch (error) {
        store.restore(snapshot);
        throw error;
    }
}

function demonstrateRollback(store) {
    const originalSalary = store.findById(1).salary;

    try {
        runTransaction(store, () => {
            store.update(
                employee => employee.employeeId === 1,
                () => ({ salary: originalSalary + 5000 })
            );

            // Simulate a failed business rule.
            throw new Error("Simulated transaction failure.");
        });
    } catch (error) {
        console.log("\nTransaction rolled back:", error.message);
    }

    const finalSalary = store.findById(1).salary;

    console.log(
        "Original salary:",
        originalSalary,
        "| Salary after rollback:",
        finalSalary
    );
}

// ---------------------------------------------------------------------------
// 16. BULK UPDATE WITH VALIDATION
// ---------------------------------------------------------------------------

function bulkSalaryUpdate(store, minimumPerformance, percentage) {
    if (!Number.isFinite(minimumPerformance)) {
        throw new Error("Minimum performance must be numeric.");
    }

    if (!Number.isFinite(percentage) || percentage < 0) {
        throw new Error("Percentage must be non-negative.");
    }

    const multiplier = 1 + percentage / 100;

    return store.update(
        employee =>
            employee.status === "ACTIVE" &&
            employee.performanceScore >= minimumPerformance,
        employee => ({
            salary: Number((employee.salary * multiplier).toFixed(2)),
            lastModified: new Date().toISOString()
        })
    );
}

// ---------------------------------------------------------------------------
// 17. APPLICATION-LEVEL GUARD
// ---------------------------------------------------------------------------

function guardedDeleteInactiveEmployee(store, employeeId) {
    validateEmployeeId(employeeId);

    const employee = store.findById(employeeId);

    if (!employee) {
        return {
            success: false,
            affectedRows: 0,
            reason: "Employee does not exist."
        };
    }

    if (employee.status !== "INACTIVE") {
        return {
            success: false,
            affectedRows: 0,
            reason: "Only inactive employees may be permanently deleted."
        };
    }

    const affectedRows = store.delete(
        candidate =>
            candidate.employeeId === employeeId &&
            candidate.status === "INACTIVE"
    );

    return {
        success: affectedRows === 1,
        affectedRows,
        reason: affectedRows === 1
            ? "Employee deleted."
            : "Employee was not deleted."
    };
}

// ---------------------------------------------------------------------------
// 18. ASYNCHRONOUS DATABASE-LIKE API
// ---------------------------------------------------------------------------

class AsyncEmployeeRepository {
    constructor(store) {
        this.store = store;
    }

    async updateStatus(employeeCode, status) {
        /*
         * Real database drivers normally expose Promise-based APIs.
         * Awaiting the operation makes ordering and error handling explicit.
         */
        await Promise.resolve();

        const affectedRows = safeUpdateStatus(
            this.store,
            employeeCode,
            status
        );

        return {
            affectedRows
        };
    }

    async deleteInactive(employeeId) {
        await Promise.resolve();

        const result = guardedDeleteInactiveEmployee(
            this.store,
            employeeId
        );

        return result;
    }
}

// ---------------------------------------------------------------------------
// 19. REPORTING AND OUTPUT
// ---------------------------------------------------------------------------

function printEmployees(store, title) {
    console.log(`\n--- ${title} ---`);

    if (store.employees.length === 0) {
        console.log("(no employees)");
        return;
    }

    console.table(store.employees);
}

function printAuditLog(store) {
    console.log("\n--- Audit Log ---");

    if (store.auditLog.length === 0) {
        console.log("(no audit records)");
        return;
    }

    console.table(store.auditLog);
}

// ---------------------------------------------------------------------------
// 20. TESTS
// ---------------------------------------------------------------------------

function assert(condition, message) {
    if (!condition) {
        throw new Error(`Assertion failed: ${message}`);
    }
}

function testBasicUpdate() {
    const store = new EmployeeStore(cloneEmployees());

    const affectedRows = basicUpdate(store);

    assert(affectedRows === 1, "Basic update should affect one row.");
    assert(
        store.findById(1).salary === 78000,
        "Salary should become 78000."
    );
}

function testConditionalDelete() {
    const store = new EmployeeStore(cloneEmployees());

    const affectedRows = conditionalDelete(store);

    assert(
        affectedRows === 1,
        "Only the inactive Operations employee should be deleted."
    );

    assert(
        store.findById(5) === undefined,
        "Employee 5 should have been deleted."
    );
}

function testOptimisticUpdate() {
    const store = new EmployeeStore(cloneEmployees());

    const affectedRows = optimisticSalaryUpdate(
        store,
        1,
        99999,
        100000
    );

    assert(
        affectedRows === 0,
        "Unexpected salary should prevent the update."
    );

    assert(
        store.findById(1).salary === 75000,
        "Salary should remain unchanged."
    );
}

function testRollback() {
    const store = new EmployeeStore(cloneEmployees());
    const originalSalary = store.findById(1).salary;

    try {
        runTransaction(store, () => {
            store.update(
                employee => employee.employeeId === 1,
                () => ({ salary: originalSalary + 1000 })
            );

            throw new Error("Forced failure");
        });
    } catch {
        // Expected failure.
    }

    assert(
        store.findById(1).salary === originalSalary,
        "Rollback should restore the original salary."
    );
}

function runTests() {
    testBasicUpdate();
    testConditionalDelete();
    testOptimisticUpdate();
    testRollback();

    console.log("\nAll JavaScript tests passed.");
}

// ---------------------------------------------------------------------------
// 21. MAIN PROGRAM
// ---------------------------------------------------------------------------

async function main() {
    const store = new EmployeeStore(cloneEmployees());

    printEmployees(store, "Initial records");

    const updated = basicUpdate(store);
    console.log(`Basic UPDATE affected ${updated} row(s).`);

    conditionalUpdate(store);
    printEmployees(store, "After conditional update");

    performanceBasedUpdate(store);
    printEmployees(store, "After performance-based update");

    const statusChanged = safeUpdateStatus(
        store,
        "EMP004",
        "INACTIVE"
    );

    console.log(
        `Parameterized-style status update affected ${statusChanged} row(s).`
    );

    const currentSalary = store.findById(2).salary;

    const optimisticResult = optimisticSalaryUpdate(
        store,
        2,
        currentSalary,
        currentSalary + 2500
    );

    console.log(
        `Optimistic update affected ${optimisticResult} row(s).`
    );

    const previewUpdated = previewAndUpdate(store);

    console.log(
        `Preview-based update affected ${previewUpdated} row(s).`
    );

    auditedSalaryUpdate(store, 3, 65000);

    printAuditLog(store);

    demonstrateRollback(store);

    softDelete(store, 4);

    const deleted = conditionalDelete(store);

    console.log(
        `Conditional DELETE affected ${deleted} row(s).`
    );

    explainDangerousDelete();

    const repository = new AsyncEmployeeRepository(store);

    const asyncUpdate = await repository.updateStatus(
        "EMP002",
        "INACTIVE"
    );

    console.log(
        "Async repository update:",
        asyncUpdate
    );

    const asyncDelete = await repository.deleteInactive(2);

    console.log(
        "Async repository deletion:",
        asyncDelete
    );

    const guardedDelete = guardedDeleteInactiveEmployee(
        store,
        999
    );

    console.log(
        "Guarded deletion of nonexistent employee:",
        guardedDelete
    );

    const bulkUpdated = bulkSalaryUpdate(
        store,
        80,
        2
    );

    console.log(
        `Bulk performance update affected ${bulkUpdated} row(s).`
    );

    printEmployees(store, "Final records");

    runTests();
}

main().catch(error => {
    console.error("\nApplication error:", error.message);
    process.exitCode = 1;
});
