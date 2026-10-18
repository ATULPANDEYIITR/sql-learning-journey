"use strict";

/*
 * Recursive CTEs are a database mechanism, but JavaScript can model the
 * same recursive state explicitly. This file focuses on event-driven
 * hierarchy traversal, where each expansion emits an event.
 */

class OrganizationTree {
    constructor(employees) {
        this.employees = new Map();
        this.children = new Map();

        for (const employee of employees) {
            if (this.employees.has(employee.id)) {
                throw new Error(`Duplicate employee id: ${employee.id}`);
            }

            this.employees.set(employee.id, Object.freeze({ ...employee }));
        }

        for (const employee of this.employees.values()) {
            if (employee.managerId !== null &&
                !this.employees.has(employee.managerId)) {
                throw new Error(
                    `Employee ${employee.id} references missing manager ${employee.managerId}`
                );
            }

            if (employee.managerId === employee.id) {
                throw new Error(`Employee ${employee.id} cannot manage itself`);
            }

            if (!this.children.has(employee.managerId)) {
                this.children.set(employee.managerId, []);
            }

            this.children.get(employee.managerId).push(employee.id);
        }

        for (const childIds of this.children.values()) {
            childIds.sort((a, b) => a - b);
        }

        this.assertAcyclic();
    }

    assertAcyclic() {
        const state = new Map();

        const visit = (id) => {
            const current = state.get(id) ?? 0;

            if (current === 1) {
                throw new Error(`Management cycle detected at ${id}`);
            }

            if (current === 2) {
                return;
            }

            state.set(id, 1);
            const managerId = this.employees.get(id).managerId;

            if (managerId !== null) {
                visit(managerId);
            }

            state.set(id, 2);
        };

        for (const id of this.employees.keys()) {
            visit(id);
        }
    }

    async *walk(rootId = null) {
        const roots = rootId === null
            ? (this.children.get(null) ?? [])
            : [rootId];

        for (const id of roots) {
            if (!this.employees.has(id)) {
                throw new Error(`Unknown employee: ${id}`);
            }
        }

        const queue = roots.map((id) => ({
            id,
            depth: 0,
            path: [id]
        }));

        while (queue.length > 0) {
            const current = queue.shift();
            const employee = this.employees.get(current.id);

            yield {
                ...employee,
                depth: current.depth,
                path: current.path
            };

            /*
             * An async generator makes the traversal streamable. A consumer
             * can stop early without constructing the complete hierarchy.
             */
            await Promise.resolve();

            for (const childId of this.children.get(current.id) ?? []) {
                if (current.path.includes(childId)) {
                    throw new Error("Cycle encountered during traversal");
                }

                queue.push({
                    id: childId,
                    depth: current.depth + 1,
                    path: [...current.path, childId]
                });
            }
        }
    }

    descendants(rootId) {
        return this.walk(rootId);
    }

    async collectSubtree(rootId) {
        const result = [];

        for await (const node of this.descendants(rootId)) {
            result.push(node);
        }

        return result;
    }

    async emitTraversal(rootId, onVisit) {
        for await (const node of this.walk(rootId)) {
            onVisit(node);
        }
    }

    managementPath(employeeId) {
        if (!this.employees.has(employeeId)) {
            throw new Error(`Unknown employee: ${employeeId}`);
        }

        const path = [];
        let current = employeeId;

        while (current !== null) {
            const employee = this.employees.get(current);
            path.push(employee);
            current = employee.managerId;
        }

        return path;
    }
}

async function main() {
    const organization = new OrganizationTree([
        { id: 1, name: "Maya", title: "CEO", managerId: null },
        { id: 2, name: "Arjun", title: "CTO", managerId: 1 },
        { id: 3, name: "Neha", title: "CFO", managerId: 1 },
        { id: 4, name: "Ravi", title: "Engineering Director", managerId: 2 },
        { id: 5, name: "Sara", title: "Security Director", managerId: 2 },
        { id: 6, name: "Asha", title: "Backend Engineer", managerId: 4 },
        { id: 7, name: "Dev", title: "Backend Engineer", managerId: 4 },
        { id: 8, name: "Meera", title: "Security Engineer", managerId: 5 }
    ]);

    console.log("ROOT-TO-LEAF TRAVERSAL");

    await organization.emitTraversal(1, (node) => {
        console.log(
            `${"  ".repeat(node.depth)}${node.name} <${node.title}>`
        );
    });

    console.log("\nSTREAMED SUBTREE");

    let emitted = 0;
    for await (const node of organization.descendants(4)) {
        console.log(node.path.join(" -> "), node.name);
        emitted++;

        // Demonstrates early termination of a streaming traversal.
        if (emitted === 2) {
            break;
        }
    }

    console.log("\nMANAGEMENT PATH");
    console.log(
        organization
            .managementPath(6)
            .map((employee) => employee.name)
            .join(" -> ")
    );

    console.log("\nINVALID HIERARCHY");

    try {
        new OrganizationTree([
            { id: 1, name: "A", title: "CEO", managerId: 2 },
            { id: 2, name: "B", title: "Manager", managerId: 1 }
        ]);
    } catch (error) {
        console.log(error.message);
    }
}

main().catch((error) => {
    console.error("Hierarchy processing failed:", error.message);
    process.exitCode = 1;
});
