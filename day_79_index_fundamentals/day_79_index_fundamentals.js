"use strict";

/**
 * INDEX FUNDAMENTALS
 *
 * Demonstrates:
 * - Why indexes exist
 * - Sequential scanning versus indexed lookup
 * - B-tree-inspired ordered index operations
 * - Binary search
 * - Composite keys
 * - Index maintenance
 * - Asynchronous query execution
 * - Query policy evaluation
 * - Validation and integrity checks
 *
 * Runtime: Node.js 18+
 * No external dependencies.
 */

const { performance } = require("node:perf_hooks");
const { EventEmitter } = require("node:events");
const crypto = require("node:crypto");

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

class IndexEntry {
    constructor(key, recordId) {
        this.key = key;
        this.recordId = recordId;
        Object.freeze(this);
    }
}

class OrderedIndex {
    /**
     * An ordered in-memory index using binary search.
     * This is a simplified ordered-index model, not a disk B-tree.
     */

    constructor(name, keySelector) {
        this.name = name;
        this.keySelector = keySelector;
        this.entries = [];
        this.recordToKey = new Map();
    }

    compare(a, b) {
        if (a < b) return -1;
        if (a > b) return 1;
        return 0;
    }

    lowerBound(key) {
        let low = 0;
        let high = this.entries.length;

        while (low < high) {
            const middle = Math.floor((low + high) / 2);

            if (this.compare(this.entries[middle].key, key) < 0) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }

        return low;
    }

    insert(record) {
        const key = this.keySelector(record);
        const recordId = record.id;

        if (this.recordToKey.has(recordId)) {
            throw new ValidationError(
                `Record ${recordId} already exists in index.`
            );
        }

        const position = this.lowerBound(key);

        if (
            position < this.entries.length &&
            this.compare(this.entries[position].key, key) === 0
        ) {
            throw new ValidationError(
                `Duplicate unique index key: ${key}`
            );
        }

        this.entries.splice(
            position,
            0,
            new IndexEntry(key, recordId)
        );

        this.recordToKey.set(recordId, key);
    }

    remove(recordId) {
        if (!this.recordToKey.has(recordId)) {
            throw new ValidationError("Index record not found.");
        }

        const key = this.recordToKey.get(recordId);
        const position = this.lowerBound(key);

        this.entries.splice(position, 1);
        this.recordToKey.delete(recordId);
    }

    lookup(key) {
        const position = this.lowerBound(key);

        if (
            position >= this.entries.length ||
            this.compare(this.entries[position].key, key) !== 0
        ) {
            return null;
        }

        return this.entries[position].recordId;
    }

    range(lower, upper) {
        if (lower > upper) {
            throw new ValidationError("Invalid range.");
        }

        const result = [];
        let position = this.lowerBound(lower);

        while (
            position < this.entries.length &&
            this.compare(this.entries[position].key, upper) <= 0
        ) {
            result.push(this.entries[position].recordId);
            position++;
        }

        return result;
    }

    validate() {
        for (let i = 1; i < this.entries.length; i++) {
            if (
                this.compare(
                    this.entries[i - 1].key,
                    this.entries[i].key
                ) >= 0
            ) {
                throw new Error("Index ordering is corrupted.");
            }
        }

        if (this.entries.length !== this.recordToKey.size) {
            throw new Error("Index metadata is inconsistent.");
        }

        return true;
    }
}

class EmployeeRepository extends EventEmitter {
    constructor() {
        super();

        this.records = new Map();

        this.idIndex = new OrderedIndex(
            "employee_id",
            employee => employee.id
        );

        this.departmentIndex = new Map();
    }

    validate(employee) {
        if (!Number.isSafeInteger(employee.id) || employee.id <= 0) {
            throw new ValidationError("Invalid employee ID.");
        }

        if (
            typeof employee.name !== "string" ||
            !employee.name.trim()
        ) {
            throw new ValidationError("Invalid employee name.");
        }

        if (
            typeof employee.department !== "string" ||
            !employee.department.trim()
        ) {
            throw new ValidationError("Invalid department.");
        }

        if (
            typeof employee.salary !== "number" ||
            !Number.isFinite(employee.salary) ||
            employee.salary < 0
        ) {
            throw new ValidationError("Invalid salary.");
        }
    }

    insert(employee) {
        this.validate(employee);

        if (this.records.has(employee.id)) {
            throw new ValidationError("Duplicate employee ID.");
        }

        const immutableRecord = Object.freeze({ ...employee });

        // Update index and table as one logical operation.
        this.idIndex.insert(immutableRecord);

        this.records.set(employee.id, immutableRecord);

        if (!this.departmentIndex.has(employee.department)) {
            this.departmentIndex.set(employee.department, new Set());
        }

        this.departmentIndex
            .get(employee.department)
            .add(employee.id);

        this.emit("recordInserted", {
            id: employee.id,
            timestamp: new Date().toISOString()
        });
    }

    sequentialLookup(id) {
        for (const employee of this.records.values()) {
            if (employee.id === id) {
                return employee;
            }
        }

        return null;
    }

    indexedLookup(id) {
        const recordId = this.idIndex.lookup(id);

        if (recordId === null) {
            return null;
        }

        return this.records.get(recordId) ?? null;
    }

    lookupDepartment(department) {
        const ids = this.departmentIndex.get(department);

        if (!ids) return [];

        return [...ids]
            .map(id => this.records.get(id))
            .filter(Boolean);
    }

    rangeLookup(lower, upper) {
        return this.idIndex
            .range(lower, upper)
            .map(id => this.records.get(id));
    }

    updateSalary(id, salary) {
        const existing = this.indexedLookup(id);

        if (!existing) {
            throw new ValidationError("Employee does not exist.");
        }

        if (!Number.isFinite(salary) || salary < 0) {
            throw new ValidationError("Invalid salary.");
        }

        const updated = Object.freeze({
            ...existing,
            salary
        });

        // The ID index is unaffected because its key has not changed.
        this.records.set(id, updated);

        this.emit("recordUpdated", {
            id,
            field: "salary"
        });
    }

    delete(id) {
        const existing = this.records.get(id);

        if (!existing) {
            throw new ValidationError("Employee not found.");
        }

        this.idIndex.remove(id);
        this.records.delete(id);

        const departmentRecords =
            this.departmentIndex.get(existing.department);

        departmentRecords.delete(id);

        if (departmentRecords.size === 0) {
            this.departmentIndex.delete(existing.department);
        }

        this.emit("recordDeleted", { id });
    }

    verifyIntegrity() {
        this.idIndex.validate();

        if (this.idIndex.entries.length !== this.records.size) {
            throw new Error("Table and primary index sizes differ.");
        }

        for (const [id, employee] of this.records) {
            if (this.idIndex.lookup(id) !== id) {
                throw new Error(`Missing index entry for ${id}`);
            }

            if (
                !this.departmentIndex
                    .get(employee.department)
                    ?.has(id)
            ) {
                throw new Error("Department index inconsistency.");
            }
        }

        return true;
    }
}

class QueryEngine extends EventEmitter {
    constructor(repository) {
        super();
        this.repository = repository;
        this.queryCount = 0;
    }

    async execute(query) {
        if (!query || typeof query !== "object") {
            throw new ValidationError("Query must be an object.");
        }

        const queryId = crypto.randomUUID();
        const start = performance.now();

        this.emit("queryStarted", { queryId, query });

        try {
            let result;

            switch (query.type) {
                case "primary_lookup":
                    result = this.repository.indexedLookup(query.id);
                    break;

                case "department_lookup":
                    result = this.repository.lookupDepartment(
                        query.department
                    );
                    break;

                case "range":
                    result = this.repository.rangeLookup(
                        query.lower,
                        query.upper
                    );
                    break;

                case "sequential_lookup":
                    result = this.repository.sequentialLookup(query.id);
                    break;

                default:
                    throw new ValidationError("Unsupported query type.");
            }

            // Simulates an asynchronous query boundary.
            await Promise.resolve();

            const duration = performance.now() - start;
            this.queryCount++;

            this.emit("queryCompleted", {
                queryId,
                duration,
                resultCount: Array.isArray(result)
                    ? result.length
                    : result === null ? 0 : 1
            });

            return {
                queryId,
                durationMs: Number(duration.toFixed(4)),
                result
            };
        } catch (error) {
            this.emit("queryFailed", {
                queryId,
                message: error.message
            });

            throw error;
        }
    }
}

async function benchmark(repository, repetitions = 3000) {
    if (!Number.isInteger(repetitions) || repetitions <= 0) {
        throw new ValidationError("Invalid benchmark repetitions.");
    }

    const ids = Array.from(
        { length: repetitions },
        () => 1 + Math.floor(Math.random() * repository.records.size)
    );

    let start = performance.now();

    for (const id of ids) {
        repository.sequentialLookup(id);
    }

    const sequential = performance.now() - start;

    start = performance.now();

    for (const id of ids) {
        repository.indexedLookup(id);
    }

    const indexed = performance.now() - start;

    return {
        sequentialMs: sequential.toFixed(4),
        indexedMs: indexed.toFixed(4),
        speedRatio: indexed > 0
            ? (sequential / indexed).toFixed(2)
            : "N/A"
    };
}

async function main() {
    const repository = new EmployeeRepository();

    repository.on("recordInserted", event => {
        if (event.id === 1) {
            console.log("First record inserted:", event.id);
        }
    });

    repository.on("recordUpdated", event => {
        console.log("Update event:", event);
    });

    const departments = [
        "Engineering",
        "Security",
        "Research",
        "Operations"
    ];

    for (let id = 1; id <= 10000; id++) {
        repository.insert({
            id,
            name: `Employee ${id}`,
            department: departments[id % departments.length],
            salary: 45000 + (id % 50000)
        });
    }

    const engine = new QueryEngine(repository);

    engine.on("queryCompleted", event => {
        console.log(
            `Query ${event.queryId.slice(0, 8)} completed in`,
            `${event.duration.toFixed(4)} ms`
        );
    });

    console.log("\nINDEX FUNDAMENTALS");

    const pointQuery = await engine.execute({
        type: "primary_lookup",
        id: 7500
    });

    console.log("Indexed result:", pointQuery.result);

    const rangeQuery = await engine.execute({
        type: "range",
        lower: 100,
        upper: 110
    });

    console.log("Range records:", rangeQuery.result.length);

    const departmentQuery = await engine.execute({
        type: "department_lookup",
        department: "Security"
    });

    console.log("Security employees:", departmentQuery.result.length);

    const sequentialQuery = await engine.execute({
        type: "sequential_lookup",
        id: 7500
    });

    console.log("Sequential result:", sequentialQuery.result);

    repository.updateSalary(7500, 150000);

    console.log(
        "Updated record:",
        repository.indexedLookup(7500)
    );

    console.log("\nINDEX VALIDATION");
    console.log("Integrity:", repository.verifyIntegrity());

    console.log("\nBENCHMARK");
    console.table(await benchmark(repository));

    console.log("\nDELETION");
    repository.delete(7500);

    console.log(
        "Deleted employee lookup:",
        repository.indexedLookup(7500)
    );

    console.log(
        "Final integrity:",
        repository.verifyIntegrity()
    );

    console.log("Executed queries:", engine.queryCount);

    // Invalid query handling.
    try {
        await engine.execute({ type: "unknown" });
    } catch (error) {
        console.log("Rejected query:", error.message);
    }
}

main().catch(error => {
    console.error("Application failure:", error.message);
    process.exitCode = 1;
});
