/**
 * Relationships: One-to-One, One-to-Many, and Many-to-Many
 *
 * This Node.js program models a small engineering organization.
 *
 * Relationship design:
 *   Employee -> EmployeeProfile       one-to-one
 *   Team     -> WorkItem              one-to-many
 *   Employee <-> Skill                many-to-many
 *
 * The implementation intentionally uses JavaScript-specific mechanisms:
 * Maps for indexed entity storage, Sets for relationship membership,
 * events for relationship changes, asynchronous validation, and
 * structured error handling.
 *
 * Run with:
 *   node relationships.js
 */

"use strict";

const { EventEmitter } = require("node:events");

class RelationshipError extends Error {
    constructor(message) {
        super(message);
        this.name = "RelationshipError";
    }
}

class NotFoundError extends RelationshipError {
    constructor(message) {
        super(message);
        this.name = "NotFoundError";
    }
}

class ConstraintError extends RelationshipError {
    constructor(message) {
        super(message);
        this.name = "ConstraintError";
    }
}

function requireEntity(map, id, entityName) {
    if (!map.has(id)) {
        throw new NotFoundError(`${entityName} ${id} does not exist.`);
    }
    return map.get(id);
}

function requireNonEmpty(value, fieldName) {
    if (typeof value !== "string" || value.trim().length === 0) {
        throw new TypeError(`${fieldName} must be a non-empty string.`);
    }
}

class RelationshipModel extends EventEmitter {
    constructor() {
        super();

        this.employees = new Map();
        this.profiles = new Map();
        this.teams = new Map();
        this.workItems = new Map();
        this.skills = new Map();

        // A composite key represents the unique employee-skill pair.
        this.employeeSkills = new Map();

        // These indexes make relationship traversal inexpensive.
        this.profileByEmployee = new Map();
        this.teamsByEmployee = new Map();
        this.workItemsByTeam = new Map();
        this.skillsByEmployee = new Map();
        this.employeesBySkill = new Map();
    }

    addEmployee(id, name, email) {
        requireNonEmpty(name, "Employee name");
        requireNonEmpty(email, "Employee email");

        if (!email.includes("@")) {
            throw new TypeError("Employee email must contain '@'.");
        }

        if (this.employees.has(id)) {
            throw new ConstraintError(`Employee ${id} already exists.`);
        }

        const employee = Object.freeze({
            id,
            name: name.trim(),
            email: email.trim()
        });

        this.employees.set(id, employee);
        this.emit("employee.created", employee);

        return employee;
    }

    createProfile(id, employeeId, title, timezone) {
        requireEntity(this.employees, employeeId, "Employee");
        requireNonEmpty(title, "Profile title");
        requireNonEmpty(timezone, "Timezone");

        // The employeeId uniqueness rule is what enforces the
        // one-to-one cardinality instead of merely storing a foreign key.
        if (this.profileByEmployee.has(employeeId)) {
            throw new ConstraintError(
                `Employee ${employeeId} already owns a profile.`
            );
        }

        if (this.profiles.has(id)) {
            throw new ConstraintError(`Profile ${id} already exists.`);
        }

        const profile = Object.freeze({
            id,
            employeeId,
            title: title.trim(),
            timezone: timezone.trim()
        });

        this.profiles.set(id, profile);
        this.profileByEmployee.set(employeeId, id);

        this.emit("profile.created", profile);
        return profile;
    }

    getProfile(employeeId) {
        requireEntity(this.employees, employeeId, "Employee");

        const profileId = this.profileByEmployee.get(employeeId);
        return profileId === undefined
            ? null
            : requireEntity(this.profiles, profileId, "Profile");
    }

    createTeam(id, name, ownerId) {
        requireEntity(this.employees, ownerId, "Employee");
        requireNonEmpty(name, "Team name");

        if (this.teams.has(id)) {
            throw new ConstraintError(`Team ${id} already exists.`);
        }

        const team = Object.freeze({
            id,
            name: name.trim(),
            ownerId
        });

        this.teams.set(id, team);

        if (!this.teamsByEmployee.has(ownerId)) {
            this.teamsByEmployee.set(ownerId, new Set());
        }

        this.teamsByEmployee.get(ownerId).add(id);

        this.emit("team.created", team);
        return team;
    }

    createWorkItem(id, teamId, title, status = "open") {
        requireEntity(this.teams, teamId, "Team");
        requireNonEmpty(title, "Work item title");

        const allowedStatuses = new Set([
            "open",
            "in_progress",
            "done"
        ]);

        if (!allowedStatuses.has(status)) {
            throw new TypeError(
                `Invalid work-item status: ${status}.`
            );
        }

        if (this.workItems.has(id)) {
            throw new ConstraintError(`Work item ${id} already exists.`);
        }

        const workItem = Object.freeze({
            id,
            teamId,
            title: title.trim(),
            status
        });

        this.workItems.set(id, workItem);

        if (!this.workItemsByTeam.has(teamId)) {
            this.workItemsByTeam.set(teamId, new Set());
        }

        this.workItemsByTeam.get(teamId).add(id);

        this.emit("workitem.created", workItem);
        return workItem;
    }

    getWorkItemsForTeam(teamId) {
        requireEntity(this.teams, teamId, "Team");

        const itemIds = this.workItemsByTeam.get(teamId) ?? new Set();

        return [...itemIds]
            .sort((a, b) => a - b)
            .map((id) => requireEntity(this.workItems, id, "Work item"));
    }

    addSkill(id, name) {
        requireNonEmpty(name, "Skill name");

        if (this.skills.has(id)) {
            throw new ConstraintError(`Skill ${id} already exists.`);
        }

        const skill = Object.freeze({
            id,
            name: name.trim()
        });

        this.skills.set(id, skill);
        this.emit("skill.created", skill);

        return skill;
    }

    assignSkill(employeeId, skillId, proficiency) {
        requireEntity(this.employees, employeeId, "Employee");
        requireEntity(this.skills, skillId, "Skill");

        const allowed = new Set([
            "beginner",
            "intermediate",
            "advanced",
            "expert"
        ]);

        if (!allowed.has(proficiency)) {
            throw new TypeError(
                `Invalid proficiency: ${proficiency}.`
            );
        }

        const key = `${employeeId}:${skillId}`;

        if (this.employeeSkills.has(key)) {
            throw new ConstraintError(
                `Employee ${employeeId} is already associated ` +
                `with skill ${skillId}.`
            );
        }

        const relation = Object.freeze({
            employeeId,
            skillId,
            proficiency
        });

        this.employeeSkills.set(key, relation);

        if (!this.skillsByEmployee.has(employeeId)) {
            this.skillsByEmployee.set(employeeId, new Set());
        }

        if (!this.employeesBySkill.has(skillId)) {
            this.employeesBySkill.set(skillId, new Set());
        }

        this.skillsByEmployee.get(employeeId).add(skillId);
        this.employeesBySkill.get(skillId).add(employeeId);

        this.emit("skill.assigned", relation);
        return relation;
    }

    getSkillsForEmployee(employeeId) {
        requireEntity(this.employees, employeeId, "Employee");

        const skillIds =
            this.skillsByEmployee.get(employeeId) ?? new Set();

        return [...skillIds]
            .sort((a, b) => a - b)
            .map((skillId) => {
                const skill = requireEntity(
                    this.skills,
                    skillId,
                    "Skill"
                );

                const relation = this.employeeSkills.get(
                    `${employeeId}:${skillId}`
                );

                return {
                    skill,
                    proficiency: relation.proficiency
                };
            });
    }

    getEmployeesForSkill(skillId) {
        requireEntity(this.skills, skillId, "Skill");

        const employeeIds =
            this.employeesBySkill.get(skillId) ?? new Set();

        return [...employeeIds]
            .sort((a, b) => a - b)
            .map((employeeId) => {
                const employee = requireEntity(
                    this.employees,
                    employeeId,
                    "Employee"
                );

                const relation = this.employeeSkills.get(
                    `${employeeId}:${skillId}`
                );

                return {
                    employee,
                    proficiency: relation.proficiency
                };
            });
    }

    removeSkillAssignment(employeeId, skillId) {
        requireEntity(this.employees, employeeId, "Employee");
        requireEntity(this.skills, skillId, "Skill");

        const key = `${employeeId}:${skillId}`;

        if (!this.employeeSkills.has(key)) {
            throw new NotFoundError(
                `Relationship between employee ${employeeId} ` +
                `and skill ${skillId} does not exist.`
            );
        }

        this.employeeSkills.delete(key);
        this.skillsByEmployee.get(employeeId)?.delete(skillId);
        this.employeesBySkill.get(skillId)?.delete(employeeId);

        this.emit("skill.unassigned", {
            employeeId,
            skillId
        });
    }

    deleteTeam(teamId) {
        const team = requireEntity(this.teams, teamId, "Team");

        const children = this.workItemsByTeam.get(teamId) ?? new Set();

        // This models a restrictive parent-delete rule. A parent with
        // existing children cannot be removed until dependencies are handled.
        if (children.size > 0) {
            throw new ConstraintError(
                `Team ${teamId} still has ${children.size} work item(s).`
            );
        }

        this.teams.delete(teamId);
        this.teamsByEmployee.get(team.ownerId)?.delete(teamId);

        this.emit("team.deleted", team);
    }

    async validateRelationshipGraph() {
        // The async boundary represents a realistic validation step that
        // could involve a database, API, or other asynchronous source.
        await Promise.resolve();

        const errors = [];

        for (const [employeeId, profileId] of this.profileByEmployee) {
            if (!this.employees.has(employeeId)) {
                errors.push(
                    `Profile mapping references missing employee ${employeeId}.`
                );
            }

            if (!this.profiles.has(profileId)) {
                errors.push(
                    `Employee ${employeeId} references missing profile ${profileId}.`
                );
            }
        }

        for (const [key, relation] of this.employeeSkills) {
            if (!this.employees.has(relation.employeeId)) {
                errors.push(
                    `Skill relationship ${key} references a missing employee.`
                );
            }

            if (!this.skills.has(relation.skillId)) {
                errors.push(
                    `Skill relationship ${key} references a missing skill.`
                );
            }
        }

        if (errors.length > 0) {
            throw new ConstraintError(
                `Relationship graph validation failed:\n${errors.join("\n")}`
            );
        }

        return true;
    }

    describeEmployee(employeeId) {
        const employee = requireEntity(
            this.employees,
            employeeId,
            "Employee"
        );

        const profile = this.getProfile(employeeId);
        const teams =
            this.teamsByEmployee.get(employeeId) ?? new Set();

        const skills = this.getSkillsForEmployee(employeeId);

        return {
            employee,
            profile,
            teams: [...teams].map((id) =>
                requireEntity(this.teams, id, "Team")
            ),
            skills
        };
    }
}

function printEmployeeReport(model, employeeId) {
    const report = model.describeEmployee(employeeId);

    console.log(`\nEmployee: ${report.employee.name}`);
    console.log(`Email: ${report.employee.email}`);

    console.log(
        `Profile: ${
            report.profile
                ? `${report.profile.title} (${report.profile.timezone})`
                : "none"
        }`
    );

    console.log(
        "Teams:",
        report.teams.map((team) => team.name).join(", ") || "none"
    );

    console.log(
        "Skills:",
        report.skills
            .map(
                ({ skill, proficiency }) =>
                    `${skill.name} [${proficiency}]`
            )
            .join(", ") || "none"
    );
}

function demonstrateEventDrivenBehavior(model) {
    console.log("\n=== Event-Driven Relationship Changes ===");

    const eventNames = [
        "profile.created",
        "team.created",
        "workitem.created",
        "skill.assigned",
        "skill.unassigned"
    ];

    for (const eventName of eventNames) {
        model.on(eventName, (payload) => {
            console.log(
                `Event ${eventName}:`,
                JSON.stringify(payload)
            );
        });
    }

    model.createProfile(
        101,
        1,
        "Platform Engineer",
        "Asia/Kolkata"
    );

    model.createTeam(201, "Payments", 1);
    model.createWorkItem(
        301,
        201,
        "Validate settlement workflow",
        "in_progress"
    );

    model.assignSkill(1, 401, "advanced");
}

async function main() {
    console.log("RELATIONSHIP MODEL");
    console.log("==================");

    const model = new RelationshipModel();

    model.addEmployee(1, "Atul", "atul@example.com");
    model.addEmployee(2, "Maya", "maya@example.com");
    model.addEmployee(3, "Liam", "liam@example.com");

    model.addSkill(401, "SQL");
    model.addSkill(402, "Python");
    model.addSkill(403, "Security");
    model.addSkill(404, "Product Management");

    model.createTeam(202, "Research", 1);
    model.createTeam(203, "Security", 2);

    model.createWorkItem(
        302,
        202,
        "Analyze research dataset",
        "open"
    );

    model.createWorkItem(
        303,
        202,
        "Prepare publication metadata",
        "done"
    );

    model.createWorkItem(
        304,
        203,
        "Review access controls",
        "in_progress"
    );

    model.assignSkill(1, 401, "advanced");
    model.assignSkill(1, 402, "expert");
    model.assignSkill(2, 401, "intermediate");
    model.assignSkill(2, 404, "advanced");
    model.assignSkill(3, 403, "beginner");

    console.log("\n=== One-to-Many Traversal ===");

    for (const team of model.teams.values()) {
        const workItems = model.getWorkItemsForTeam(team.id);

        console.log(
            `${team.name}: ${workItems.length} work item(s)`
        );

        for (const item of workItems) {
            console.log(
                `  ${item.title} -> ${item.status}`
            );
        }
    }

    console.log("\n=== Many-to-Many Traversal ===");

    console.log(
        "Employees with SQL:",
        model
            .getEmployeesForSkill(401)
            .map(
                ({ employee, proficiency }) =>
                    `${employee.name} [${proficiency}]`
            )
            .join(", ")
    );

    console.log(
        "Skills for Atul:",
        model
            .getSkillsForEmployee(1)
            .map(
                ({ skill, proficiency }) =>
                    `${skill.name} [${proficiency}]`
            )
            .join(", ")
    );

    demonstrateEventDrivenBehavior(model);

    printEmployeeReport(model, 1);

    console.log("\n=== Asynchronous Integrity Validation ===");
    await model.validateRelationshipGraph();
    console.log("Relationship graph is internally consistent.");

    console.log("\n=== Constraint Failures ===");

    try {
        model.createProfile(
            102,
            1,
            "Second Profile",
            "UTC"
        );
    } catch (error) {
        console.log(error.name + ":", error.message);
    }

    try {
        model.assignSkill(1, 401, "expert");
    } catch (error) {
        console.log(error.name + ":", error.message);
    }

    try {
        model.createWorkItem(
            305,
            999,
            "Invalid parent"
        );
    } catch (error) {
        console.log(error.name + ":", error.message);
    }

    try {
        model.deleteTeam(202);
    } catch (error) {
        console.log(error.name + ":", error.message);
    }

    console.log("\n=== Removing a Many-to-Many Association ===");

    model.removeSkillAssignment(1, 402);

    console.log(
        "Atul's remaining skills:",
        model
            .getSkillsForEmployee(1)
            .map(
                ({ skill, proficiency }) =>
                    `${skill.name} [${proficiency}]`
            )
            .join(", ")
    );

    console.log("\n=== Relationship Characteristics ===");
    console.log(
        "One-to-one uses a unique employee-to-profile mapping."
    );
    console.log(
        "One-to-many stores the parent identifier on every child work item."
    );
    console.log(
        "Many-to-many uses a separate relationship record for each employee-skill pair."
    );
    console.log(
        "Maps and Sets provide indexed relationship traversal without scanning every entity."
    );
}

main().catch((error) => {
    console.error("Fatal error:", error);
    process.exitCode = 1;
});
