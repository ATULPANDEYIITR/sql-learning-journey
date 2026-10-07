"use strict";

/*
 * SELF JOIN hierarchy model
 *
 * A relational employee table can reference itself:
 *
 *   employees.manager_id -> employees.employee_id
 *
 * A SELF JOIN then gives two logical aliases to the same table:
 *
 *   employees AS employee
 *   employees AS manager
 *
 * This program focuses on employee-manager hierarchies and uses
 * JavaScript's event-driven model to simulate organizational changes.
 */

class Employee {
    constructor({
        id,
        name,
        title,
        managerId = null,
        department,
        salary,
        active = true
    }) {
        this.id = id;
        this.name = name;
        this.title = title;
        this.managerId = managerId;
        this.department = department;
        this.salary = salary;
        this.active = active;
    }
}

class Organization {
    constructor(employees) {
        this.employees = new Map(
            employees.map((employee) => [employee.id, employee])
        );

        this.validate();
    }

    validate() {
        for (const employee of this.employees.values()) {
            if (employee.managerId === null) {
                continue;
            }

            if (!this.employees.has(employee.managerId)) {
                throw new Error(
                    `Employee ${employee.id} references missing manager ${employee.managerId}.`
                );
            }

            if (employee.managerId === employee.id) {
                throw new Error(
                    `Employee ${employee.id} cannot manage themselves.`
                );
            }
        }

        this.validateNoCycles();
    }

    validateNoCycles() {
        for (const employee of this.employees.values()) {
            const visited = new Set();
            let currentId = employee.id;

            while (currentId !== null) {
                if (visited.has(currentId)) {
                    throw new Error(
                        `Management cycle detected at employee ${currentId}.`
                    );
                }

                visited.add(currentId);

                const current = this.getEmployee(currentId);
                currentId = current.managerId;
            }
        }
    }

    getEmployee(employeeId) {
        const employee = this.employees.get(employeeId);

        if (!employee) {
            throw new Error(`Unknown employee ID: ${employeeId}.`);
        }

        return employee;
    }

    managerOf(employeeId) {
        const employee = this.getEmployee(employeeId);

        if (employee.managerId === null) {
            return null;
        }

        return this.getEmployee(employee.managerId);
    }

    directReports(managerId) {
        this.getEmployee(managerId);

        return [...this.employees.values()]
            .filter(
                (employee) =>
                    employee.managerId === managerId && employee.active
            )
            .sort((a, b) => a.name.localeCompare(b.name));
    }

    selfJoinRows() {
        return [...this.employees.values()]
            .filter((employee) => employee.managerId !== null)
            .map((employee) => {
                const manager = this.managerOf(employee.id);

                return {
                    employeeId: employee.id,
                    employeeName: employee.name,
                    employeeTitle: employee.title,
                    managerId: manager.id,
                    managerName: manager.name,
                    managerTitle: manager.title
                };
            })
            .sort((a, b) => a.employeeId - b.employeeId);
    }

    hierarchyDepth(employeeId) {
        let depth = 0;
        let current = this.getEmployee(employeeId);

        while (current.managerId !== null) {
            depth += 1;
            current = this.getEmployee(current.managerId);
        }

        return depth;
    }

    managementChain(employeeId) {
        const chain = [];
        let current = this.getEmployee(employeeId);

        while (current) {
            chain.push(current);
            current =
                current.managerId === null
                    ? null
                    : this.getEmployee(current.managerId);
        }

        return chain;
    }

    nearestCommonManager(firstId, secondId) {
        const firstChain = this.managementChain(firstId);
        const secondIds = new Set(
            this.managementChain(secondId).map((employee) => employee.id)
        );

        return firstChain.find((employee) => secondIds.has(employee.id)) ?? null;
    }

    descendants(employeeId) {
        const result = [];
        const queue = [employeeId];

        while (queue.length > 0) {
            const currentId = queue.shift();

            for (const report of this.directReports(currentId)) {
                result.push(report);
                queue.push(report.id);
            }
        }

        return result;
    }

    moveEmployee(employeeId, newManagerId) {
        const employee = this.getEmployee(employeeId);

        if (newManagerId === employeeId) {
            throw new Error("An employee cannot become their own manager.");
        }

        if (newManagerId !== null) {
            const newManager = this.getEmployee(newManagerId);

            const descendantIds = new Set(
                this.descendants(employeeId).map((person) => person.id)
            );

            if (descendantIds.has(newManager.id)) {
                throw new Error(
                    "A descendant cannot become a manager because that would create a cycle."
                );
            }
        }

        const oldManagerId = employee.managerId;
        employee.managerId = newManagerId;

        try {
            this.validate();
        } catch (error) {
            employee.managerId = oldManagerId;
            throw error;
        }
    }

    departmentReport(department) {
        return [...this.employees.values()]
            .filter(
                (employee) =>
                    employee.active && employee.department === department
            )
            .map((employee) => {
                const manager = this.managerOf(employee.id);

                return {
                    employee: employee.name,
                    title: employee.title,
                    manager: manager?.name ?? "Organization Root"
                };
            })
            .sort((a, b) => a.employee.localeCompare(b.employee));
    }

    renderChart() {
        const children = new Map();

        for (const employee of this.employees.values()) {
            const key = employee.managerId;

            if (!children.has(key)) {
                children.set(key, []);
            }

            children.get(key).push(employee);
        }

        for (const reports of children.values()) {
            reports.sort((a, b) => a.name.localeCompare(b.name));
        }

        const lines = [];

        const render = (managerId, depth) => {
            for (const employee of children.get(managerId) ?? []) {
                lines.push(
                    `${"  ".repeat(depth)}- ${employee.name} ` +
                    `(${employee.title}, ${employee.department})`
                );

                render(employee.id, depth + 1);
            }
        };

        render(null, 0);
        return lines.join("\n");
    }
}

class HierarchyEventProcessor {
    /*
     * EventEmitter is a Node.js-specific mechanism. It models how a real
     * organization service might publish an event after a manager changes.
     */
    constructor(organization) {
        this.organization = organization;
        this.listeners = new Map();
    }

    on(eventName, listener) {
        if (!this.listeners.has(eventName)) {
            this.listeners.set(eventName, []);
        }

        this.listeners.get(eventName).push(listener);
    }

    emit(eventName, payload) {
        for (const listener of this.listeners.get(eventName) ?? []) {
            listener(payload);
        }
    }

    async moveEmployee(employeeId, newManagerId) {
        const employee = this.organization.getEmployee(employeeId);
        const oldManagerId = employee.managerId;

        this.organization.moveEmployee(employeeId, newManagerId);

        this.emit("employee.managerChanged", {
            employeeId,
            oldManagerId,
            newManagerId
        });

        await Promise.resolve();
    }
}

function createOrganization() {
    return new Organization([
        new Employee({
            id: 1,
            name: "Anita",
            title: "Chief Executive Officer",
            department: "Executive",
            salary: 220000
        }),
        new Employee({
            id: 2,
            name: "Rahul",
            title: "VP Engineering",
            managerId: 1,
            department: "Engineering",
            salary: 170000
        }),
        new Employee({
            id: 3,
            name: "Meera",
            title: "VP Operations",
            managerId: 1,
            department: "Operations",
            salary: 165000
        }),
        new Employee({
            id: 4,
            name: "Vikram",
            title: "Engineering Manager",
            managerId: 2,
            department: "Engineering",
            salary: 125000
        }),
        new Employee({
            id: 5,
            name: "Priya",
            title: "Engineering Manager",
            managerId: 2,
            department: "Engineering",
            salary: 128000
        }),
        new Employee({
            id: 6,
            name: "Daniel",
            title: "Operations Manager",
            managerId: 3,
            department: "Operations",
            salary: 120000
        }),
        new Employee({
            id: 7,
            name: "Arjun",
            title: "Senior Engineer",
            managerId: 4,
            department: "Engineering",
            salary: 105000
        }),
        new Employee({
            id: 8,
            name: "Sana",
            title: "Software Engineer",
            managerId: 4,
            department: "Engineering",
            salary: 90000
        }),
        new Employee({
            id: 9,
            name: "Karan",
            title: "Software Engineer",
            managerId: 5,
            department: "Engineering",
            salary: 92000
        }),
        new Employee({
            id: 10,
            name: "Leena",
            title: "Software Engineer",
            managerId: 5,
            department: "Engineering",
            salary: 94000
        }),
        new Employee({
            id: 11,
            name: "Rohit",
            title: "Operations Analyst",
            managerId: 6,
            department: "Operations",
            salary: 76000
        }),
        new Employee({
            id: 12,
            name: "Neha",
            title: "Operations Analyst",
            managerId: 6,
            department: "Operations",
            salary: 78000
        }),
        new Employee({
            id: 13,
            name: "Ishaan",
            title: "Intern",
            managerId: 7,
            department: "Engineering",
            salary: 30000
        })
    ]);
}

async function main() {
    const organization = createOrganization();

    console.log("SELF JOIN: EMPLOYEE-MANAGER HIERARCHY");
    console.log("======================================");

    console.log("\nOrganization chart");
    console.log(organization.renderChart());

    console.log("\nLogical SELF JOIN result");
    console.table(organization.selfJoinRows());

    console.log("\nDirect reports of Priya");
    console.table(
        organization.directReports(5).map((employee) => ({
            name: employee.name,
            title: employee.title
        }))
    );

    console.log("\nHierarchy depth");
    for (const employeeId of [1, 5, 7, 13]) {
        const employee = organization.getEmployee(employeeId);
        console.log(
            `${employee.name}: depth ${organization.hierarchyDepth(employeeId)}`
        );
    }

    console.log("\nNearest common manager");
    const commonManager = organization.nearestCommonManager(7, 9);
    console.log(
        `Arjun and Karan share nearest manager: ${commonManager?.name ?? "None"}`
    );

    console.log("\nEngineering department report");
    console.table(organization.departmentReport("Engineering"));

    const processor = new HierarchyEventProcessor(organization);

    processor.on("employee.managerChanged", (event) => {
        console.log(
            `Event: employee ${event.employeeId} moved from ` +
            `${event.oldManagerId ?? "root"} to ${event.newManagerId ?? "root"}`
        );
    });

    console.log("\nEvent-driven hierarchy change");
    await processor.moveEmployee(8, 5);

    console.log("\nUpdated organization chart");
    console.log(organization.renderChart());

    console.log("\nInvalid hierarchy operation");
    try {
        await processor.moveEmployee(2, 7);
    } catch (error) {
        console.error(`Rejected: ${error.message}`);
    }

    console.log("\nInvalid self-management operation");
    try {
        await processor.moveEmployee(5, 5);
    } catch (error) {
        console.error(`Rejected: ${error.message}`);
    }

    console.log("\nWhy this is a SELF JOIN");
    console.log(
        "The employee table supplies both sides of the relationship. " +
        "One logical row is the employee and another logical row is the manager. " +
        "The employee.managerId value identifies the manager's employeeId."
    );
}

main().catch((error) => {
    console.error(`Fatal error: ${error.message}`);
    process.exitCode = 1;
});
