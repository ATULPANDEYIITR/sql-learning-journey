"use strict";

/*
 * Database Views: CREATE VIEW, View Abstraction, and Reusable Queries.
 *
 * Runtime: Node.js 18+
 *
 * This implementation models a view registry and query engine using
 * immutable snapshots, dependency tracking, asynchronous refreshes,
 * event-driven invalidation, and policy-controlled view access.
 *
 * No external npm dependencies.
 */

const { EventEmitter } = require("node:events");
const { performance } = require("node:perf_hooks");

class ViewError extends Error {}
class ValidationError extends Error {}
class AccessDeniedError extends Error {}


const employees = [
    {
        id: 101,
        name: "Aarav",
        departmentId: 1,
        salary: 95000,
        active: true
    },
    {
        id: 102,
        name: "Meera",
        departmentId: 1,
        salary: 110000,
        active: true
    },
    {
        id: 103,
        name: "Kabir",
        departmentId: 2,
        salary: 85000,
        active: true
    },
    {
        id: 104,
        name: "Ananya",
        departmentId: 3,
        salary: 120000,
        active: true
    },
    {
        id: 105,
        name: "Rohan",
        departmentId: 2,
        salary: 75000,
        active: false
    },
    {
        id: 106,
        name: "Ishita",
        departmentId: 4,
        salary: 80000,
        active: true
    }
];

const departments = [
    { id: 1, name: "Engineering", location: "Bangalore" },
    { id: 2, name: "Finance", location: "Mumbai" },
    { id: 3, name: "Research", location: "Hyderabad" },
    { id: 4, name: "Operations", location: "Lucknow" }
];

const projects = [
    { id: 201, name: "Cloud Platform", budget: 500000, departmentId: 1 },
    { id: 202, name: "Financial Analytics", budget: 250000, departmentId: 2 },
    { id: 203, name: "Research Intelligence", budget: 700000, departmentId: 3 },
    { id: 204, name: "Process Automation", budget: 180000, departmentId: 4 }
];

const assignments = [
    { id: 1, employeeId: 101, projectId: 201, hours: 120 },
    { id: 2, employeeId: 102, projectId: 201, hours: 160 },
    { id: 3, employeeId: 103, projectId: 202, hours: 90 },
    { id: 4, employeeId: 104, projectId: 203, hours: 180 },
    { id: 5, employeeId: 106, projectId: 204, hours: 110 },
    { id: 6, employeeId: 101, projectId: 204, hours: 40 }
];


function validateRows(rows, name) {
    if (!Array.isArray(rows)) {
        throw new ValidationError(`${name} must be an array.`);
    }

    return rows;
}


function freezeRows(rows) {
    return Object.freeze(
        rows.map(row => Object.freeze({ ...row }))
    );
}


class DataStore extends EventEmitter {
    #tables = new Map();
    #version = 0;

    constructor(initialData) {
        super();

        for (const [name, rows] of Object.entries(initialData)) {
            this.#tables.set(name, freezeRows(rows));
        }
    }

    get version() {
        return this.#version;
    }

    read(tableName) {
        const rows = this.#tables.get(tableName);

        if (!rows) {
            throw new ValidationError(`Unknown table: ${tableName}`);
        }

        return rows;
    }

    replace(tableName, rows) {
        if (!this.#tables.has(tableName)) {
            throw new ValidationError(`Unknown table: ${tableName}`);
        }

        validateRows(rows, tableName);

        // Build a new immutable snapshot rather than modifying shared data.
        this.#tables.set(tableName, freezeRows(rows));
        this.#version++;

        this.emit("changed", {
            tableName,
            version: this.#version
        });
    }
}


class ViewRegistry extends EventEmitter {
    #definitions = new Map();
    #cache = new Map();
    #store;
    #refreshLocks = new Map();

    constructor(store) {
        super();
        this.#store = store;

        store.on("changed", event => {
            this.invalidateDependency(event.tableName);
        });
    }

    register(name, dependencies, evaluator, options = {}) {
        if (!/^[a-z][a-z0-9_]*$/.test(name)) {
            throw new ValidationError("Invalid view identifier.");
        }

        if (this.#definitions.has(name)) {
            throw new ValidationError(`View already exists: ${name}`);
        }

        if (!Array.isArray(dependencies) || dependencies.length === 0) {
            throw new ValidationError("View dependencies are required.");
        }

        if (typeof evaluator !== "function") {
            throw new ValidationError("Evaluator must be a function.");
        }

        for (const dependency of dependencies) {
            if (
                !this.#store.read.bind(this.#store) ||
                !this.#storeDependencyExists(dependency)
            ) {
                throw new ValidationError(
                    `Invalid dependency: ${dependency}`
                );
            }
        }

        this.#definitions.set(name, {
            dependencies: new Set(dependencies),
            evaluator,
            roles: new Set(options.roles || ["reader", "analyst", "admin"]),
            sensitive: options.sensitive === true
        });

        this.emit("registered", { name });
    }

    #storeDependencyExists(name) {
        try {
            this.#store.read(name);
            return true;
        } catch {
            return this.#definitions.has(name);
        }
    }

    getDefinition(name) {
        const definition = this.#definitions.get(name);

        if (!definition) {
            throw new ViewError(`View does not exist: ${name}`);
        }

        return definition;
    }

    invalidateDependency(dependency) {
        for (const [name, definition] of this.#definitions) {
            if (definition.dependencies.has(dependency)) {
                this.#cache.delete(name);

                this.emit("invalidated", {
                    name,
                    dependency
                });
            }
        }
    }

    async query(name, principal = "reader", options = {}) {
        const definition = this.getDefinition(name);

        if (!definition.roles.has(principal)) {
            throw new AccessDeniedError(
                `${principal} cannot access ${name}`
            );
        }

        const started = performance.now();

        let result;

        if (options.useCache) {
            const cached = this.#cache.get(name);

            if (cached && cached.version === this.#store.version) {
                result = cached.rows;
            }
        }

        if (!result) {
            const context = {
                read: tableName => this.#store.read(tableName),
                query: async dependency =>
                    this.query(dependency, principal)
            };

            const evaluated = await definition.evaluator(context);

            if (!Array.isArray(evaluated)) {
                throw new ViewError(
                    `View ${name} did not return rows.`
                );
            }

            result = freezeRows(evaluated);

            if (options.useCache) {
                this.#cache.set(name, {
                    rows: result,
                    version: this.#store.version
                });
            }
        }

        this.emit("queried", {
            name,
            rowCount: result.length,
            durationMs: performance.now() - started
        });

        return result.map(row => ({ ...row }));
    }

    async refresh(name, principal = "admin") {
        if (principal !== "admin") {
            throw new AccessDeniedError(
                "Only administrators may refresh cached views."
            );
        }

        // Concurrent refresh requests share the same Promise.
        if (this.#refreshLocks.has(name)) {
            return this.#refreshLocks.get(name);
        }

        const task = (async () => {
            const rows = await this.query(name, principal);

            this.#cache.set(name, {
                rows: freezeRows(rows),
                version: this.#store.version
            });

            this.emit("refreshed", {
                name,
                rowCount: rows.length
            });

            return rows.length;
        })();

        this.#refreshLocks.set(name, task);

        try {
            return await task;
        } finally {
            this.#refreshLocks.delete(name);
        }
    }

    metadata() {
        return [...this.#definitions.entries()].map(
            ([name, definition]) => ({
                name,
                dependencies: [...definition.dependencies],
                sensitive: definition.sensitive,
                roles: [...definition.roles]
            })
        );
    }
}


function createDepartmentStatistics(context) {
    const departments = context.read("departments");
    const employees = context.read("employees");

    return departments.map(department => {
        const members = employees.filter(
            employee =>
                employee.departmentId === department.id &&
                employee.active
        );

        const payroll = members.reduce(
            (sum, employee) => sum + employee.salary,
            0
        );

        return {
            departmentId: department.id,
            departmentName: department.name,
            employeeCount: members.length,
            averageSalary: members.length
                ? payroll / members.length
                : 0,
            payroll
        };
    });
}


function createProjectWorkload(context) {
    const projects = context.read("projects");
    const departments = context.read("departments");
    const assignments = context.read("assignments");

    return projects.map(project => {
        const workload = assignments.filter(
            assignment => assignment.projectId === project.id
        );

        const department = departments.find(
            item => item.id === project.departmentId
        );

        if (!department) {
            throw new ViewError(
                `Missing department for project ${project.id}`
            );
        }

        return {
            projectId: project.id,
            projectName: project.name,
            departmentName: department.name,
            assignmentCount: workload.length,
            totalHours: workload.reduce(
                (sum, item) => sum + item.hours,
                0
            ),
            budget: project.budget
        };
    });
}


function createActiveEmployeeDirectory(context) {
    return context.read("employees")
        .filter(employee => employee.active)
        .map(employee => ({
            employeeId: employee.id,
            employeeName: employee.name,
            departmentId: employee.departmentId
        }));
}


function createHighWorkloadProjects(context) {
    return context.read("projects")
        .filter(project => project.budget >= 250000)
        .map(project => ({
            projectId: project.id,
            projectName: project.name,
            budget: project.budget
        }));
}


async function main() {
    const store = new DataStore({
        employees,
        departments,
        projects,
        assignments
    });

    const views = new ViewRegistry(store);

    views.on("queried", event => {
        console.log(
            `[QUERY] ${event.name}: ${event.rowCount} rows, ` +
            `${event.durationMs.toFixed(3)} ms`
        );
    });

    views.on("invalidated", event => {
        console.log(
            `[INVALIDATION] ${event.name} due to ${event.dependency}`
        );
    });

    views.on("refreshed", event => {
        console.log(`[REFRESH] ${event.name}`);
    });

    views.register(
        "employee_directory",
        ["employees"],
        createActiveEmployeeDirectory
    );

    views.register(
        "department_statistics",
        ["departments", "employees"],
        createDepartmentStatistics,
        { roles: ["analyst", "admin"] }
    );

    views.register(
        "project_workload",
        ["projects", "departments", "assignments"],
        createProjectWorkload
    );

    views.register(
        "high_budget_projects",
        ["projects"],
        createHighWorkloadProjects
    );

    console.log("\n1. Active Employee Directory");

    console.table(
        await views.query("employee_directory")
    );

    console.log("\n2. Department Statistics");

    console.table(
        await views.query("department_statistics", "analyst")
    );

    console.log("\n3. Project Workload");

    console.table(
        await views.query("project_workload")
    );

    console.log("\n4. Reusable View with Consumer Filtering");

    const workload = await views.query("project_workload");

    console.table(
        workload.filter(project => project.totalHours > 100)
    );

    console.log("\n5. View Metadata");

    console.table(views.metadata());

    console.log("\n6. Cached View");

    await views.refresh("department_statistics");

    console.table(
        await views.query(
            "department_statistics",
            "analyst",
            { useCache: true }
        )
    );

    console.log("\n7. Source Table Modification");

    const updatedEmployees = employees.map(employee =>
        employee.id === 101
            ? { ...employee, name: "Aarav Sharma" }
            : employee
    );

    store.replace("employees", updatedEmployees);

    // Cached results are invalidated after a dependency changes.
    console.table(
        await views.query(
            "employee_directory",
            "reader",
            { useCache: true }
        )
    );

    console.log("\n8. Access Control");

    try {
        await views.query("department_statistics", "reader");
    } catch (error) {
        console.log("Expected access error:", error.message);
    }

    console.log("\n9. Validation");

    try {
        views.register(
            "invalid view",
            ["employees"],
            createActiveEmployeeDirectory
        );
    } catch (error) {
        console.log("Expected validation error:", error.message);
    }

    console.log("\n10. Assertions");

    const statistics = await views.query(
        "department_statistics",
        "analyst"
    );

    const engineering = statistics.find(
        item => item.departmentId === 1
    );

    if (
        !engineering ||
        engineering.employeeCount !== 2 ||
        engineering.payroll !== 205000
    ) {
        throw new Error("Department statistics assertion failed.");
    }

    const projectsResult = await views.query("project_workload");

    if (projectsResult.length !== 4) {
        throw new Error("Project view assertion failed.");
    }

    console.log("All assertions passed.");
}


main().catch(error => {
    console.error("Application failure:", error.message);
    process.exitCode = 1;
});
