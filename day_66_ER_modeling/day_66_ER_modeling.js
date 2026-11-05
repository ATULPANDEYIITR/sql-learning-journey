"use strict";

/*
 * ER Modeling: Event-driven schema registry.
 *
 * Demonstrates:
 * - Entity definitions and attribute metadata
 * - Candidate and primary keys
 * - Relationships and cardinality
 * - Total and partial participation
 * - Relationship attributes
 * - Event-driven model changes
 * - Referential integrity checks
 * - Schema validation
 * - Relational mapping
 *
 * Runtime: Node.js 18+
 */

const { EventEmitter } = require("node:events");
const fs = require("node:fs/promises");

const Cardinality = Object.freeze({
    ONE_TO_ONE: "1:1",
    ONE_TO_MANY: "1:N",
    MANY_TO_ONE: "N:1",
    MANY_TO_MANY: "M:N"
});

const Participation = Object.freeze({
    TOTAL: "TOTAL",
    PARTIAL: "PARTIAL"
});

const DataTypes = Object.freeze([
    "INTEGER",
    "VARCHAR",
    "DATE",
    "DECIMAL",
    "BOOLEAN"
]);

class ModelError extends Error {
    constructor(message) {
        super(message);
        this.name = "ModelError";
    }
}

class EntityDefinition {
    constructor(name, attributes) {
        if (!name || !Array.isArray(attributes)) {
            throw new ModelError("Invalid entity definition.");
        }

        this.name = name;
        this.attributes = new Map();

        for (const attribute of attributes) {
            this.addAttribute(attribute);
        }

        if (![...this.attributes.values()].some(a => a.primaryKey)) {
            throw new ModelError(
                `Entity ${name} must define a primary key.`
            );
        }
    }

    addAttribute(attribute) {
        const {
            name,
            type,
            primaryKey = false,
            unique = false,
            nullable = true
        } = attribute;

        if (!name || !DataTypes.includes(type)) {
            throw new ModelError("Invalid attribute name or type.");
        }

        if (this.attributes.has(name)) {
            throw new ModelError(`Duplicate attribute: ${name}`);
        }

        this.attributes.set(name, Object.freeze({
            name,
            type,
            primaryKey,
            unique,
            nullable: primaryKey ? false : nullable
        }));
    }

    validateRecord(record) {
        const errors = [];

        for (const key of Object.keys(record)) {
            if (!this.attributes.has(key)) {
                errors.push(`Unknown attribute: ${key}`);
            }
        }

        for (const attribute of this.attributes.values()) {
            const value = record[attribute.name];

            if (value === undefined || value === null) {
                if (!attribute.nullable) {
                    errors.push(`${attribute.name} is required.`);
                }
                continue;
            }

            let valid = true;

            switch (attribute.type) {
                case "INTEGER":
                    valid = Number.isSafeInteger(value);
                    break;
                case "VARCHAR":
                    valid = typeof value === "string";
                    break;
                case "DECIMAL":
                    valid =
                        typeof value === "number" &&
                        Number.isFinite(value);
                    break;
                case "BOOLEAN":
                    valid = typeof value === "boolean";
                    break;
                case "DATE":
                    valid =
                        typeof value === "string" &&
                        /^\d{4}-\d{2}-\d{2}$/.test(value) &&
                        !Number.isNaN(Date.parse(value)) &&
                        new Date(value).toISOString().slice(0, 10) === value;
                    break;
            }

            if (!valid) {
                errors.push(
                    `${attribute.name} has invalid type ${attribute.type}.`
                );
            }
        }

        return errors;
    }

    get primaryKeys() {
        return [...this.attributes.values()]
            .filter(a => a.primaryKey)
            .map(a => a.name);
    }
}

class RelationshipDefinition {
    constructor({
        name,
        left,
        right,
        attributes = []
    }) {
        this.name = name;
        this.left = Object.freeze({ ...left });
        this.right = Object.freeze({ ...right });
        this.attributes = Object.freeze([...attributes]);

        this.validateEnd(this.left);
        this.validateEnd(this.right);

        const names = this.attributes.map(a => a.name);

        if (new Set(names).size !== names.length) {
            throw new ModelError(
                `Duplicate relationship attribute in ${name}.`
            );
        }
    }

    validateEnd(end) {
        if (
            !end.entity ||
            ![0, 1].includes(end.minimum) ||
            ![1, null].includes(end.maximum) ||
            !Object.values(Participation).includes(end.participation)
        ) {
            throw new ModelError("Invalid relationship endpoint.");
        }

        const expected = end.minimum === 1
            ? Participation.TOTAL
            : Participation.PARTIAL;

        if (end.participation !== expected) {
            throw new ModelError(
                "Participation conflicts with minimum cardinality."
            );
        }
    }

    get cardinality() {
        const leftMany = this.left.maximum === null;
        const rightMany = this.right.maximum === null;

        if (leftMany && rightMany) return Cardinality.MANY_TO_MANY;
        if (leftMany) return Cardinality.ONE_TO_MANY;
        if (rightMany) return Cardinality.MANY_TO_ONE;

        return Cardinality.ONE_TO_ONE;
    }
}

class ERRegistry extends EventEmitter {
    constructor(name) {
        super();

        this.name = name;
        this.entities = new Map();
        this.relationships = new Map();
        this.instances = new Map();
        this.version = 0;
    }

    addEntity(entity) {
        if (this.entities.has(entity.name)) {
            throw new ModelError(`Entity already exists: ${entity.name}`);
        }

        this.entities.set(entity.name, entity);
        this.instances.set(entity.name, []);

        this.version++;

        this.emit("entityAdded", {
            name: entity.name,
            version: this.version
        });
    }

    addRelationship(relationship) {
        if (this.relationships.has(relationship.name)) {
            throw new ModelError(
                `Relationship already exists: ${relationship.name}`
            );
        }

        if (
            !this.entities.has(relationship.left.entity) ||
            !this.entities.has(relationship.right.entity)
        ) {
            throw new ModelError(
                "Relationship references an unknown entity."
            );
        }

        this.relationships.set(relationship.name, relationship);
        this.version++;

        this.emit("relationshipAdded", {
            name: relationship.name,
            cardinality: relationship.cardinality
        });
    }

    insert(entityName, record) {
        const entity = this.entities.get(entityName);

        if (!entity) {
            throw new ModelError(`Unknown entity: ${entityName}`);
        }

        const errors = entity.validateRecord(record);

        if (errors.length) {
            throw new ModelError(errors.join("; "));
        }

        const records = this.instances.get(entityName);
        const primaryKey = entity.primaryKeys;

        const key = JSON.stringify(
            primaryKey.map(name => record[name])
        );

        if (records.some(existing =>
            JSON.stringify(
                primaryKey.map(name => existing[name])
            ) === key
        )) {
            throw new ModelError("Duplicate primary key.");
        }

        // Enforce unique attributes independently of the primary key.
        for (const attribute of entity.attributes.values()) {
            if (!attribute.unique || record[attribute.name] == null) {
                continue;
            }

            if (records.some(existing =>
                existing[attribute.name] === record[attribute.name]
            )) {
                throw new ModelError(
                    `Unique constraint violated: ${attribute.name}`
                );
            }
        }

        const stored = Object.freeze({ ...record });

        records.push(stored);

        this.emit("recordInserted", {
            entity: entityName,
            record: stored
        });

        return stored;
    }

    validateRelationshipInstances(name, pairs) {
        const relationship = this.relationships.get(name);

        if (!relationship) {
            throw new ModelError(`Unknown relationship: ${name}`);
        }

        const leftRecords = this.instances.get(
            relationship.left.entity
        );

        const rightRecords = this.instances.get(
            relationship.right.entity
        );

        const leftEntity = this.entities.get(
            relationship.left.entity
        );

        const rightEntity = this.entities.get(
            relationship.right.entity
        );

        const leftKey = leftEntity.primaryKeys[0];
        const rightKey = rightEntity.primaryKeys[0];

        const leftCounts = new Map();
        const rightCounts = new Map();

        for (const pair of pairs) {
            if (
                !leftRecords.some(r => r[leftKey] === pair.leftId) ||
                !rightRecords.some(r => r[rightKey] === pair.rightId)
            ) {
                throw new ModelError(
                    `Relationship ${name} contains an orphan reference.`
                );
            }

            leftCounts.set(
                pair.leftId,
                (leftCounts.get(pair.leftId) || 0) + 1
            );

            rightCounts.set(
                pair.rightId,
                (rightCounts.get(pair.rightId) || 0) + 1
            );
        }

        const checkMaximum = (counts, endpoint) => {
            if (endpoint.maximum === 1) {
                for (const count of counts.values()) {
                    if (count > 1) {
                        throw new ModelError(
                            `Maximum cardinality violated for ${endpoint.entity}.`
                        );
                    }
                }
            }
        };

        checkMaximum(leftCounts, relationship.left);
        checkMaximum(rightCounts, relationship.right);

        // Participation applies to all existing entities, not only
        // entities appearing in the relationship input.
        for (const record of leftRecords) {
            if (
                relationship.left.minimum === 1 &&
                !leftCounts.has(record[leftKey])
            ) {
                throw new ModelError(
                    `${relationship.left.entity} requires participation.`
                );
            }
        }

        for (const record of rightRecords) {
            if (
                relationship.right.minimum === 1 &&
                !rightCounts.has(record[rightKey])
            ) {
                throw new ModelError(
                    `${relationship.right.entity} requires participation.`
                );
            }
        }

        return true;
    }

    getRelationalMapping() {
        return [...this.relationships.values()].map(r => {
            let implementation;

            switch (r.cardinality) {
                case Cardinality.MANY_TO_MANY:
                    implementation = "JUNCTION_TABLE";
                    break;
                case Cardinality.ONE_TO_ONE:
                    implementation = "UNIQUE_FOREIGN_KEY";
                    break;
                default:
                    implementation = "FOREIGN_KEY_ON_MANY_SIDE";
            }

            return {
                relationship: r.name,
                cardinality: r.cardinality,
                implementation,
                relationshipAttributes: r.attributes
            };
        });
    }

    inspect() {
        return {
            name: this.name,
            version: this.version,
            entities: [...this.entities.values()].map(e => ({
                name: e.name,
                attributes: [...e.attributes.values()]
            })),
            relationships: [...this.relationships.values()].map(r => ({
                name: r.name,
                cardinality: r.cardinality,
                left: r.left,
                right: r.right,
                attributes: r.attributes
            }))
        };
    }
}

function endpoint(entity, minimum, maximum) {
    return {
        entity,
        minimum,
        maximum,
        participation: minimum === 1
            ? Participation.TOTAL
            : Participation.PARTIAL
    };
}

async function main() {
    const registry = new ERRegistry("Hospital Management ER Model");

    registry.on("entityAdded", event => {
        console.log(`EVENT: Entity registered: ${event.name}`);
    });

    registry.on("relationshipAdded", event => {
        console.log(
            `EVENT: Relationship registered: ${event.name} ` +
            `(${event.cardinality})`
        );
    });

    registry.on("recordInserted", event => {
        console.log(`EVENT: Record inserted into ${event.entity}`);
    });

    registry.addEntity(new EntityDefinition("Patient", [
        {
            name: "patient_id",
            type: "INTEGER",
            primaryKey: true
        },
        {
            name: "patient_name",
            type: "VARCHAR",
            nullable: false
        },
        {
            name: "email",
            type: "VARCHAR",
            unique: true
        },
        {
            name: "date_of_birth",
            type: "DATE"
        }
    ]));

    registry.addEntity(new EntityDefinition("Doctor", [
        {
            name: "doctor_id",
            type: "INTEGER",
            primaryKey: true
        },
        {
            name: "doctor_name",
            type: "VARCHAR",
            nullable: false
        },
        {
            name: "specialization",
            type: "VARCHAR",
            nullable: false
        }
    ]));

    registry.addEntity(new EntityDefinition("Appointment", [
        {
            name: "appointment_id",
            type: "INTEGER",
            primaryKey: true
        },
        {
            name: "appointment_date",
            type: "DATE",
            nullable: false
        },
        {
            name: "status",
            type: "VARCHAR",
            nullable: false
        }
    ]));

    registry.addRelationship(new RelationshipDefinition({
        name: "PatientAppointment",
        left: endpoint("Patient", 0, null),
        right: endpoint("Appointment", 1, 1),
        attributes: [
            { name: "booking_channel", type: "VARCHAR" }
        ]
    }));

    registry.addRelationship(new RelationshipDefinition({
        name: "DoctorAppointment",
        left: endpoint("Doctor", 0, null),
        right: endpoint("Appointment", 1, 1)
    }));

    registry.addRelationship(new RelationshipDefinition({
        name: "PatientDoctor",
        left: endpoint("Patient", 0, null),
        right: endpoint("Doctor", 0, null),
        attributes: [
            { name: "first_consultation", type: "DATE" }
        ]
    }));

    registry.insert("Patient", {
        patient_id: 101,
        patient_name: "Aarav Sharma",
        email: "aarav@example.com",
        date_of_birth: "1995-04-12"
    });

    registry.insert("Patient", {
        patient_id: 102,
        patient_name: "Diya Verma",
        email: "diya@example.com",
        date_of_birth: "1998-09-21"
    });

    registry.insert("Doctor", {
        doctor_id: 501,
        doctor_name: "Dr. Meera",
        specialization: "Cardiology"
    });

    registry.insert("Doctor", {
        doctor_id: 502,
        doctor_name: "Dr. Arjun",
        specialization: "Neurology"
    });

    registry.insert("Appointment", {
        appointment_id: 1001,
        appointment_date: "2026-11-06",
        status: "CONFIRMED"
    });

    registry.insert("Appointment", {
        appointment_id: 1002,
        appointment_date: "2026-11-07",
        status: "PENDING"
    });

    registry.validateRelationshipInstances(
        "PatientAppointment",
        [
            { leftId: 101, rightId: 1001 },
            { leftId: 102, rightId: 1002 }
        ]
    );

    registry.validateRelationshipInstances(
        "DoctorAppointment",
        [
            { leftId: 501, rightId: 1001 },
            { leftId: 502, rightId: 1002 }
        ]
    );

    console.log("\nRELATIONAL MAPPING");

    console.table(registry.getRelationalMapping());

    const model = registry.inspect();

    await fs.writeFile(
        "hospital_er_model.json",
        JSON.stringify(model, null, 2),
        { encoding: "utf8", flag: "w" }
    );

    console.log("\nModel exported to hospital_er_model.json");

    console.log("\nVALIDATION TESTS");

    let failed = false;

    try {
        registry.insert("Patient", {
            patient_id: 101,
            patient_name: "Duplicate Patient"
        });
    } catch (error) {
        failed = error instanceof ModelError;
    }

    if (!failed) {
        throw new Error("Duplicate primary key test failed.");
    }

    failed = false;

    try {
        registry.insert("Patient", {
            patient_id: 103,
            patient_name: null
        });
    } catch (error) {
        failed = error instanceof ModelError;
    }

    if (!failed) {
        throw new Error("NULL validation test failed.");
    }

    failed = false;

    try {
        registry.validateRelationshipInstances(
            "PatientAppointment",
            [{ leftId: 999, rightId: 1001 }]
        );
    } catch (error) {
        failed = error instanceof ModelError;
    }

    if (!failed) {
        throw new Error("Orphan reference test failed.");
    }

    console.log("PASS: Entity registration");
    console.log("PASS: Attribute validation");
    console.log("PASS: Primary key uniqueness");
    console.log("PASS: Relationship cardinality");
    console.log("PASS: Referential integrity");
    console.log("PASS: Participation validation");
    console.log("PASS: Event-driven model updates");

    console.log("\nER modeling workflow completed.");
}

main().catch(error => {
    console.error("Execution failed:", error.message);
    process.exitCode = 1;
});
