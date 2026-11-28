"use strict";

const { performance } = require("node:perf_hooks");
const { randomInt } = require("node:crypto");

class QueryValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "QueryValidationError";
    }
}

class QueryMetrics {
    constructor() {
        this.scanned = 0;
        this.filtered = 0;
        this.joined = 0;
        this.returned = 0;
        this.elapsedMs = 0;
    }
}

class Repository {
    constructor() {
        this.employees = new Map();
        this.departments = new Map();
        this.employeeIndex = new Map();
        this.locationIndex = new Map();
        this.version = 0;
    }

    addDepartment(department) {
        if (
            !Number.isSafeInteger(department.id) ||
            department.id <= 0 ||
            !department.name ||
            !department.location
        ) {
            throw new QueryValidationError("Invalid department");
        }

        if (this.departments.has(department.id)) {
            throw new QueryValidationError("Duplicate department ID");
        }

        const stored = Object.freeze({ ...department });
        this.departments.set(stored.id, stored);

        const ids = this.locationIndex.get(stored.location) ?? new Set();
        ids.add(stored.id);
        this.locationIndex.set(stored.location, ids);
        this.version++;
    }

    addEmployee(employee) {
        if (
            !Number.isSafeInteger(employee.id) ||
            employee.id <= 0 ||
            !Number.isFinite(employee.salary) ||
            employee.salary < 0 ||
            typeof employee.active !== "boolean"
        ) {
            throw new QueryValidationError("Invalid employee");
        }

        if (this.employees.has(employee.id)) {
            throw new QueryValidationError("Duplicate employee ID");
        }

        if (!this.departments.has(employee.departmentId)) {
            throw new QueryValidationError("Unknown department");
        }

        const stored = Object.freeze({ ...employee });
        this.employees.set(stored.id, stored);

        const ids = this.employeeIndex.get(stored.departmentId) ?? [];
        ids.push(stored.id);
        this.employeeIndex.set(stored.departmentId, ids);
        this.version++;
    }

    validateQuery(query) {
        if (
            !Number.isFinite(query.minimumSalary) ||
            query.minimumSalary < 0
        ) {
            throw new QueryValidationError("Invalid salary threshold");
        }

        if (typeof query.location !== "string" || !query.location.trim()) {
            throw new QueryValidationError("Location is required");
        }

        if (query.limit !== undefined &&
            (!Number.isSafeInteger(query.limit) || query.limit < 0)) {
            throw new QueryValidationError("Invalid result limit");
        }
    }

    getDepartmentsByLocation(location) {
        const ids = this.locationIndex.get(location) ?? new Set();
        return [...ids]
            .map(id => this.departments.get(id))
            .filter(Boolean);
    }

    async execute(query, strategy = "pushdown") {
        this.validateQuery(query);

        const metrics = new QueryMetrics();
        const start = performance.now();

        let result;

        if (strategy === "nested-loop") {
            result = this.nestedLoop(query, metrics);
        } else if (strategy === "pushdown") {
            result = await this.pushdown(query, metrics);
        } else if (strategy === "indexed") {
            result = this.indexed(query, metrics);
        } else {
            throw new QueryValidationError("Unknown execution strategy");
        }

        result.sort((a, b) => b.salary - a.salary || a.id - b.id);

        if (query.limit !== undefined) {
            result = result.slice(0, query.limit);
        }

        metrics.returned = result.length;
        metrics.elapsedMs = performance.now() - start;

        return Object.freeze({
            rows: result,
            metrics: Object.freeze({ ...metrics }),
            repositoryVersion: this.version
        });
    }

    nestedLoop(query, metrics) {
        const result = [];

        for (const employee of this.employees.values()) {
            for (const department of this.departments.values()) {
                metrics.joined++;

                if (employee.departmentId !== department.id) continue;

                metrics.scanned++;

                if (
                    employee.active &&
                    employee.salary >= query.minimumSalary &&
                    department.location === query.location
                ) {
                    result.push({
                        id: employee.id,
                        name: employee.name,
                        salary: employee.salary,
                        department: department.name
                    });
                }
            }
        }

        return result;
    }

    async pushdown(query, metrics) {
        // Process employees in asynchronous batches to avoid monopolizing
        // the event loop when datasets are large.
        const result = [];
        const employees = [...this.employees.values()];
        const matchingDepartments = new Set(
            this.getDepartmentsByLocation(query.location).map(d => d.id)
        );

        const batchSize = 1000;

        for (let offset = 0; offset < employees.length; offset += batchSize) {
            const batch = employees.slice(offset, offset + batchSize);

            for (const employee of batch) {
                metrics.scanned++;

                if (!employee.active || employee.salary < query.minimumSalary) {
                    continue;
                }

                metrics.filtered++;

                if (!matchingDepartments.has(employee.departmentId)) {
                    continue;
                }

                const department = this.departments.get(employee.departmentId);

                metrics.joined++;

                result.push({
                    id: employee.id,
                    name: employee.name,
                    salary: employee.salary,
                    department: department.name
                });
            }

            if (offset + batchSize < employees.length) {
                await new Promise(resolve => setImmediate(resolve));
            }
        }

        return result;
    }

    indexed(query, metrics) {
        const result = [];
        const departments = this.getDepartmentsByLocation(query.location);

        for (const department of departments) {
            const employeeIds = this.employeeIndex.get(department.id) ?? [];

            for (const id of employeeIds) {
                metrics.scanned++;

                const employee = this.employees.get(id);

                if (!employee.active || employee.salary < query.minimumSalary) {
                    continue;
                }

                metrics.filtered++;
                metrics.joined++;

                result.push({
                    id: employee.id,
                    name: employee.name,
                    salary: employee.salary,
                    department: department.name
                });
            }
        }

        return result;
    }
}

class QueryPlanner {
    constructor(repository) {
        this.repository = repository;
    }

    estimate(query) {
        const employeeCount = this.repository.employees.size;
        const departmentCount = this.repository.departments.size;

        const activeCount = [...this.repository.employees.values()]
            .filter(e => e.active).length;

        const salaryCount = [...this.repository.employees.values()]
            .filter(e => e.salary >= query.minimumSalary).length;

        const matchingDepartments =
            this.repository.getDepartmentsByLocation(query.location).length;

        const locationFraction = departmentCount === 0
            ? 0
            : matchingDepartments / departmentCount;

        return {
            employeeCount,
            departmentCount,
            estimatedRows: Math.round(
                Math.min(activeCount, salaryCount) * locationFraction
            ),
            recommendedStrategy:
                matchingDepartments <= departmentCount / 2
                    ? "indexed"
                    : "pushdown"
        };
    }
}

async function main() {
    const repository = new Repository();
    const locations = ["Lucknow", "Delhi", "Mumbai", "Pune"];

    for (let id = 1; id <= 100; id++) {
        repository.addDepartment({
            id,
            name: `Department-${id}`,
            location: locations[(id - 1) % locations.length]
        });
    }

    for (let id = 1; id <= 10000; id++) {
        repository.addEmployee({
            id,
            name: `Employee-${id}`,
            departmentId: randomInt(1, 101),
            salary: randomInt(20000, 150001),
            active: randomInt(0, 5) !== 0
        });
    }

    const query = {
        minimumSalary: 75000,
        location: "Lucknow",
        limit: 100
    };

    const planner = new QueryPlanner(repository);
    console.log("Estimated plan:", planner.estimate(query));

    const results = [];

    for (const strategy of ["nested-loop", "pushdown", "indexed"]) {
        const execution = await repository.execute(query, strategy);
        results.push(execution);

        console.log(`\n${strategy}`);
        console.log("Rows returned:", execution.metrics.returned);
        console.log("Rows scanned:", execution.metrics.scanned);
        console.log("Join operations:", execution.metrics.joined);
        console.log("Time:", execution.metrics.elapsedMs.toFixed(3), "ms");
        console.log("First results:", execution.rows.slice(0, 3));
    }

    // All strategies must return identical ordered results.
    const reference = results[0].rows.map(row => row.id);

    for (const result of results.slice(1)) {
        const actual = result.rows.map(row => row.id);
        if (JSON.stringify(reference) !== JSON.stringify(actual)) {
            throw new Error("Execution strategies produced different results");
        }
    }

    console.log("\nAll execution strategies returned equivalent results.");

    try {
        await repository.execute({
            minimumSalary: -100,
            location: "Lucknow"
        });
    } catch (error) {
        console.log("Expected validation failure:", error.message);
    }
}

main().catch(error => {
    console.error("Query execution failed:", error);
    process.exitCode = 1;
});
