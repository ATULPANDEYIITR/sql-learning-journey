"use strict";

const fs = require("node:fs/promises");

const NormalForm = Object.freeze({
    UNNORMALIZED: "UNNORMALIZED",
    FIRST: "1NF",
    SECOND: "2NF",
    THIRD: "3NF"
});

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

class FunctionalDependency {
    constructor(determinant, dependent) {
        this.determinant = new Set(determinant);
        this.dependent = new Set(dependent);
    }

    toString() {
        return `${[...this.determinant].sort().join(", ")} -> ${[
            ...this.dependent
        ].sort().join(", ")}`;
    }
}

class Relation {
    constructor({ name, columns, primaryKey, rows = [], dependencies = [] }) {
        this.name = name;
        this.columns = new Set(columns);
        this.primaryKey = new Set(primaryKey);
        this.rows = rows;
        this.dependencies = dependencies;
    }

    validate() {
        if (this.columns.size === 0) {
            throw new ValidationError("A relation requires columns.");
        }

        if (this.primaryKey.size === 0) {
            throw new ValidationError("A relation requires a primary key.");
        }

        for (const key of this.primaryKey) {
            if (!this.columns.has(key)) {
                throw new ValidationError(
                    `Primary-key column '${key}' does not exist.`
                );
            }
        }

        const keys = new Set();

        for (let i = 0; i < this.rows.length; i++) {
            const row = this.rows[i];

            for (const column of this.columns) {
                if (!(column in row)) {
                    throw new ValidationError(
                        `Row ${i + 1} is missing '${column}'.`
                    );
                }
            }

            const key = [...this.primaryKey]
                .sort()
                .map(column => JSON.stringify(row[column]))
                .join("|");

            if (keys.has(key)) {
                throw new ValidationError(
                    `Duplicate primary key detected in row ${i + 1}.`
                );
            }

            keys.add(key);
        }
    }

    dependencyViolations() {
        const violations = [];

        for (const dependency of this.dependencies) {
            const groups = new Map();
            const determinant = [...dependency.determinant].sort();
            const dependent = [...dependency.dependent].sort();

            this.rows.forEach((row, index) => {
                const key = JSON.stringify(
                    determinant.map(column => row[column])
                );

                const values = dependent.map(column => row[column]);

                if (!groups.has(key)) {
                    groups.set(key, values);
                } else if (
                    JSON.stringify(groups.get(key)) !== JSON.stringify(values)
                ) {
                    violations.push(
                        `${dependency} is violated at row ${index + 1}.`
                    );
                }
            });
        }

        return violations;
    }
}

function isAtomic(value) {
    return (
        value === null ||
        typeof value !== "object" ||
        value instanceof Date
    );
}

function subset(left, right) {
    return [...left].every(value => right.has(value));
}

function properSubset(left, right) {
    return subset(left, right) && left.size < right.size;
}

function check1NF(relation) {
    const problems = [];

    try {
        relation.validate();
    } catch (error) {
        problems.push(error.message);
        return { valid: false, problems };
    }

    relation.rows.forEach((row, rowIndex) => {
        for (const column of relation.columns) {
            if (!isAtomic(row[column])) {
                problems.push(
                    `Row ${rowIndex + 1}, '${column}' is not atomic.`
                );
            }
        }
    });

    return {
        valid: problems.length === 0,
        problems
    };
}

function check2NF(relation) {
    const first = check1NF(relation);
    const problems = [...first.problems];

    for (const fd of relation.dependencies) {
        const determinantIsPartial =
            properSubset(fd.determinant, relation.primaryKey) &&
            subset(fd.determinant, relation.primaryKey) &&
            !subset(fd.dependent, relation.primaryKey);

        if (determinantIsPartial) {
            problems.push(
                `Partial dependency: ${fd}.`
            );
        }
    }

    return {
        valid: problems.length === 0,
        problems
    };
}

function check3NF(relation) {
    const second = check2NF(relation);
    const problems = [...second.problems];

    for (const fd of relation.dependencies) {
        const determinantIsNonKey =
            !subset(fd.determinant, relation.primaryKey) &&
            !subset(relation.primaryKey, fd.determinant);

        const dependentIsNonKey =
            !subset(fd.dependent, relation.primaryKey);

        if (determinantIsNonKey && dependentIsNonKey) {
            problems.push(
                `Transitive dependency candidate: ${fd}.`
            );
        }
    }

    return {
        valid: problems.length === 0,
        problems
    };
}

function classify(relation) {
    const third = check3NF(relation);

    if (third.valid) {
        return { form: NormalForm.THIRD, problems: [] };
    }

    const second = check2NF(relation);

    if (second.valid) {
        return { form: NormalForm.SECOND, problems: second.problems };
    }

    const first = check1NF(relation);

    if (first.valid) {
        return { form: NormalForm.FIRST, problems: first.problems };
    }

    return {
        form: NormalForm.UNNORMALIZED,
        problems: first.problems
    };
}

class EnrollmentService {
    constructor() {
        this.students = new Map();
        this.courses = new Map();
        this.instructors = new Map();
        this.enrollments = new Map();
        this.listeners = new Set();
    }

    on(eventName, handler) {
        this.listeners.add({ eventName, handler });
        return () => {
            for (const listener of this.listeners) {
                if (
                    listener.eventName === eventName &&
                    listener.handler === handler
                ) {
                    this.listeners.delete(listener);
                }
            }
        };
    }

    emit(eventName, payload) {
        for (const listener of this.listeners) {
            if (listener.eventName === eventName) {
                listener.handler(payload);
            }
        }
    }

    addStudent(id, name) {
        if (!Number.isInteger(id) || id <= 0) {
            throw new ValidationError("Student ID must be positive.");
        }

        if (!name.trim()) {
            throw new ValidationError("Student name cannot be empty.");
        }

        this.students.set(id, { id, name });
        this.emit("student.created", { id });
    }

    addInstructor(id, name) {
        if (!Number.isInteger(id) || id <= 0) {
            throw new ValidationError("Instructor ID must be positive.");
        }

        this.instructors.set(id, { id, name });
        this.emit("instructor.created", { id });
    }

    addCourse(id, name, instructorId) {
        if (!this.instructors.has(instructorId)) {
            throw new ValidationError("Instructor does not exist.");
        }

        this.courses.set(id, {
            id,
            name,
            instructorId
        });

        this.emit("course.created", { id });
    }

    enroll(id, studentId, courseId, grade) {
        if (!this.students.has(studentId)) {
            throw new ValidationError("Student does not exist.");
        }

        if (!this.courses.has(courseId)) {
            throw new ValidationError("Course does not exist.");
        }

        if (this.enrollments.has(id)) {
            throw new ValidationError("Enrollment ID already exists.");
        }

        const duplicate = [...this.enrollments.values()].some(
            enrollment =>
                enrollment.studentId === studentId &&
                enrollment.courseId === courseId
        );

        if (duplicate) {
            throw new ValidationError(
                "Student is already enrolled in this course."
            );
        }

        if (grade !== null && !["A", "B", "C", "D", "F"].includes(grade)) {
            throw new ValidationError("Invalid grade.");
        }

        this.enrollments.set(id, {
            id,
            studentId,
            courseId,
            grade
        });

        this.emit("enrollment.created", {
            id,
            studentId,
            courseId
        });
    }

    transcript(studentId) {
        if (!this.students.has(studentId)) {
            throw new ValidationError("Student does not exist.");
        }

        return [...this.enrollments.values()]
            .filter(item => item.studentId === studentId)
            .map(item => {
                const course = this.courses.get(item.courseId);
                const instructor = this.instructors.get(course.instructorId);

                return {
                    courseId: course.id,
                    courseName: course.name,
                    instructor: instructor.name,
                    grade: item.grade
                };
            })
            .sort((a, b) => a.courseId - b.courseId);
    }
}

async function writeAuditFile(events) {
    // The audit file contains only domain events, not credentials or secrets.
    await fs.writeFile(
        "normalization-audit.json",
        JSON.stringify(events, null, 2),
        "utf8"
    );
}

async function main() {
    const relation = new Relation({
        name: "EnrollmentRecord",
        columns: [
            "studentId",
            "studentName",
            "courseId",
            "courseName",
            "instructorId",
            "instructorName",
            "grade"
        ],
        primaryKey: ["studentId", "courseId"],
        rows: [
            {
                studentId: 1,
                studentName: "Asha",
                courseId: 101,
                courseName: "Database Systems",
                instructorId: 7,
                instructorName: "Dr Rao",
                grade: "A"
            },
            {
                studentId: 1,
                studentName: "Asha",
                courseId: 102,
                courseName: "Networks",
                instructorId: 8,
                instructorName: "Dr Singh",
                grade: "B"
            }
        ],
        dependencies: [
            new FunctionalDependency(
                ["studentId"],
                ["studentName"]
            ),
            new FunctionalDependency(
                ["courseId"],
                ["courseName", "instructorId"]
            ),
            new FunctionalDependency(
                ["instructorId"],
                ["instructorName"]
            )
        ]
    });

    const classification = classify(relation);

    console.log(`Normal form: ${classification.form}`);
    classification.problems.forEach(problem =>
        console.log(`- ${problem}`)
    );

    const events = [];

    const service = new EnrollmentService();

    service.on("student.created", event => {
        events.push({
            event: "student.created",
            ...event,
            timestamp: new Date().toISOString()
        });
    });

    service.on("enrollment.created", event => {
        events.push({
            event: "enrollment.created",
            ...event,
            timestamp: new Date().toISOString()
        });
    });

    service.addStudent(1, "Asha");
    service.addStudent(2, "Ravi");

    service.addInstructor(7, "Dr Rao");
    service.addInstructor(8, "Dr Singh");

    service.addCourse(101, "Database Systems", 7);
    service.addCourse(102, "Networks", 8);

    service.enroll(1001, 1, 101, "A");
    service.enroll(1002, 1, 102, "B");

    console.log("\nTranscript:");
    console.table(service.transcript(1));

    try {
        service.enroll(1003, 1, 101, "A");
    } catch (error) {
        console.log(`Rejected duplicate: ${error.message}`);
    }

    try {
        service.enroll(1004, 1, 102, "X");
    } catch (error) {
        console.log(`Rejected invalid grade: ${error.message}`);
    }

    await writeAuditFile(events);

    console.log("\nAudit events written:", events.length);
}

main().catch(error => {
    console.error("Execution failed:", error.message);
    process.exitCode = 1;
});
