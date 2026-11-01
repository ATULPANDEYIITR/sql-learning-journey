'use strict';

/*
 * Database normalization policy engine.
 *
 * The implementation treats normalization as a sequence of domain events:
 * dependency analysis, anomaly detection, policy evaluation, and decomposition.
 * It uses JavaScript Maps/Sets and asynchronous event processing to model a
 * service that could evaluate schema changes before deployment.
 */

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ValidationError';
    }
}

class FunctionalDependency {
    constructor(determinant, dependent) {
        if (!(determinant instanceof Set) || !(dependent instanceof Set)) {
            throw new ValidationError('Functional dependency sides must be Sets.');
        }
        if (determinant.size === 0 || dependent.size === 0) {
            throw new ValidationError('Functional dependency sides cannot be empty.');
        }

        this.determinant = new Set(determinant);
        this.dependent = new Set(dependent);
    }

    toString() {
        return `${[...this.determinant].sort().join(', ')} -> ${[
            ...this.dependent
        ].sort().join(', ')}`;
    }
}

class RelationSchema {
    constructor(name, attributes, candidateKeys, dependencies) {
        this.name = name;
        this.attributes = new Set(attributes);
        this.candidateKeys = candidateKeys.map(key => new Set(key));
        this.dependencies = dependencies;

        this.validate();
    }

    validate() {
        if (!this.name || this.attributes.size === 0) {
            throw new ValidationError('Relation requires a name and attributes.');
        }

        if (this.candidateKeys.length === 0) {
            throw new ValidationError('At least one candidate key is required.');
        }

        for (const key of this.candidateKeys) {
            if (key.size === 0) {
                throw new ValidationError('Candidate keys cannot be empty.');
            }

            for (const attribute of key) {
                if (!this.attributes.has(attribute)) {
                    throw new ValidationError(
                        `Unknown candidate-key attribute: ${attribute}`
                    );
                }
            }
        }

        for (const fd of this.dependencies) {
            for (const attribute of [...fd.determinant, ...fd.dependent]) {
                if (!this.attributes.has(attribute)) {
                    throw new ValidationError(
                        `Dependency references unknown attribute: ${attribute}`
                    );
                }
            }
        }
    }

    closure(seed) {
        const closure = new Set(seed);
        let changed = true;

        while (changed) {
            changed = false;

            for (const fd of this.dependencies) {
                const determinantSatisfied =
                    [...fd.determinant].every(attribute => closure.has(attribute));

                if (!determinantSatisfied) {
                    continue;
                }

                for (const attribute of fd.dependent) {
                    if (!closure.has(attribute)) {
                        closure.add(attribute);
                        changed = true;
                    }
                }
            }
        }

        return closure;
    }

    isSuperkey(attributes) {
        const closure = this.closure(attributes);
        return [...this.attributes].every(attribute => closure.has(attribute));
    }

    primeAttributes() {
        const result = new Set();

        for (const key of this.candidateKeys) {
            for (const attribute of key) {
                result.add(attribute);
            }
        }

        return result;
    }
}

function setsEqual(left, right) {
    if (left.size !== right.size) {
        return false;
    }

    return [...left].every(value => right.has(value));
}

function isProperSubset(candidate, parent) {
    if (candidate.size >= parent.size) {
        return false;
    }

    return [...candidate].every(value => parent.has(value));
}

function detectPartialDependencies(schema) {
    const prime = schema.primeAttributes();
    const findings = [];

    for (const fd of schema.dependencies) {
        const nonPrimeDependent = [...fd.dependent].some(
            attribute => !prime.has(attribute)
        );

        if (!nonPrimeDependent) {
            continue;
        }

        for (const key of schema.candidateKeys) {
            if (isProperSubset(fd.determinant, key)) {
                findings.push(fd);
                break;
            }
        }
    }

    return findings;
}

function detectTransitiveDependencies(schema) {
    const prime = schema.primeAttributes();
    const findings = [];

    for (const fd of schema.dependencies) {
        if (schema.isSuperkey(fd.determinant)) {
            continue;
        }

        const nonPrimeDependent = [...fd.dependent].some(
            attribute => !prime.has(attribute)
        );

        if (nonPrimeDependent) {
            findings.push(fd);
        }
    }

    return findings;
}

function evaluateNormalForm(schema) {
    const partial = detectPartialDependencies(schema);

    if (partial.length > 0) {
        return {
            normalForm: '1NF',
            partialDependencies: partial,
            transitiveDependencies: []
        };
    }

    const transitive = detectTransitiveDependencies(schema);

    if (transitive.length > 0) {
        return {
            normalForm: '2NF',
            partialDependencies: [],
            transitiveDependencies: transitive
        };
    }

    return {
        normalForm: '3NF',
        partialDependencies: [],
        transitiveDependencies: []
    };
}

class NormalizationEventBus {
    constructor() {
        this.handlers = new Map();
    }

    on(eventName, handler) {
        if (!this.handlers.has(eventName)) {
            this.handlers.set(eventName, []);
        }

        this.handlers.get(eventName).push(handler);
    }

    async emit(eventName, payload) {
        const handlers = this.handlers.get(eventName) ?? [];

        return Promise.all(
            handlers.map(handler => Promise.resolve(handler(payload)))
        );
    }
}

class SchemaReviewService {
    constructor() {
        this.events = new NormalizationEventBus();

        this.events.on('analysis.completed', analysis => {
            console.log(
                `[event] ${analysis.schema.name}: highest detected normal form = ${analysis.normalForm}`
            );
        });

        this.events.on('anomaly.detected', anomaly => {
            console.log(`[event] ${anomaly.type}: ${anomaly.message}`);
        });
    }

    async evaluate(schema) {
        const analysis = evaluateNormalForm(schema);

        await this.events.emit('analysis.completed', {
            schema,
            normalForm: analysis.normalForm
        });

        for (const fd of analysis.partialDependencies) {
            await this.events.emit('anomaly.detected', {
                type: 'PARTIAL_DEPENDENCY',
                message: fd.toString()
            });
        }

        for (const fd of analysis.transitiveDependencies) {
            await this.events.emit('anomaly.detected', {
                type: 'TRANSITIVE_DEPENDENCY',
                message: fd.toString()
            });
        }

        return analysis;
    }
}

class EnrollmentStore {
    constructor() {
        this.students = new Map();
        this.instructors = new Map();
        this.courses = new Map();
        this.enrollments = new Map();
    }

    addStudent(id, name) {
        if (!id || !name?.trim()) {
            throw new ValidationError('Student ID and name are required.');
        }

        this.students.set(id, Object.freeze({ id, name: name.trim() }));
    }

    addInstructor(id, name) {
        if (!id || !name?.trim()) {
            throw new ValidationError('Instructor ID and name are required.');
        }

        this.instructors.set(
            id,
            Object.freeze({ id, name: name.trim() })
        );
    }

    addCourse(id, name, instructorId) {
        if (!id || !name?.trim() || !instructorId) {
            throw new ValidationError(
                'Course ID, course name, and instructor are required.'
            );
        }

        if (!this.instructors.has(instructorId)) {
            throw new ValidationError(`Unknown instructor: ${instructorId}`);
        }

        this.courses.set(
            id,
            Object.freeze({
                id,
                name: name.trim(),
                instructorId
            })
        );
    }

    enroll(studentId, courseId, grade = null) {
        if (!this.students.has(studentId)) {
            throw new ValidationError(`Unknown student: ${studentId}`);
        }

        if (!this.courses.has(courseId)) {
            throw new ValidationError(`Unknown course: ${courseId}`);
        }

        if (grade !== null && !/^[A-F][+-]?$/.test(grade)) {
            throw new ValidationError(`Invalid grade: ${grade}`);
        }

        const key = `${studentId}:${courseId}`;

        if (this.enrollments.has(key)) {
            throw new ValidationError('Duplicate enrollment.');
        }

        this.enrollments.set(
            key,
            Object.freeze({ studentId, courseId, grade })
        );
    }

    consistencyCheck() {
        const problems = [];

        for (const enrollment of this.enrollments.values()) {
            if (!this.students.has(enrollment.studentId)) {
                problems.push(`Missing student ${enrollment.studentId}`);
            }

            if (!this.courses.has(enrollment.courseId)) {
                problems.push(`Missing course ${enrollment.courseId}`);
            }
        }

        return problems;
    }
}

async function main() {
    const schema = new RelationSchema(
        'EnrollmentRecord',
        [
            'student_id',
            'student_name',
            'course_id',
            'course_name',
            'instructor_id',
            'instructor_name',
            'grade'
        ],
        [
            ['student_id', 'course_id']
        ],
        [
            new FunctionalDependency(
                new Set(['student_id']),
                new Set(['student_name'])
            ),
            new FunctionalDependency(
                new Set(['course_id']),
                new Set(['course_name', 'instructor_id'])
            ),
            new FunctionalDependency(
                new Set(['instructor_id']),
                new Set(['instructor_name'])
            ),
            new FunctionalDependency(
                new Set(['student_id', 'course_id']),
                new Set(['grade'])
            )
        ]
    );

    const service = new SchemaReviewService();
    const analysis = await service.evaluate(schema);

    console.log('\n=== Dependency Closures ===');

    for (const key of schema.candidateKeys) {
        const closure = schema.closure(key);
        console.log(
            `{${[...key].join(', ')}}+ = {${[...closure].sort().join(', ')}}`
        );
    }

    console.log('\n=== Normalization Decision ===');
    console.log(`Highest normal form: ${analysis.normalForm}`);

    const store = new EnrollmentStore();

    store.addStudent('S001', 'Asha Singh');
    store.addStudent('S002', 'Rahul Kumar');

    store.addInstructor('I001', 'Dr. Mehta');
    store.addInstructor('I002', 'Dr. Rao');

    store.addCourse('C101', 'Database Systems', 'I001');
    store.addCourse('C102', 'Operating Systems', 'I002');

    store.enroll('S001', 'C101', 'A');
    store.enroll('S002', 'C101', 'B');

    console.log('\n=== Normalized Domain State ===');
    console.log('Students:', [...store.students.values()]);
    console.log('Instructors:', [...store.instructors.values()]);
    console.log('Courses:', [...store.courses.values()]);
    console.log('Enrollments:', [...store.enrollments.values()]);

    console.log('\nConsistency problems:', store.consistencyCheck());

    try {
        store.enroll('S001', 'C101', 'A');
    } catch (error) {
        console.log(`Expected duplicate-enrollment failure: ${error.message}`);
    }

    try {
        store.addCourse('C999', 'Invalid Course', 'UNKNOWN');
    } catch (error) {
        console.log(`Expected foreign-key failure: ${error.message}`);
    }

    /*
     * The normalized design prevents update anomalies by storing instructor
     * identity once, insertion anomalies by allowing courses without
     * enrollments, and deletion anomalies by keeping course data independent
     * of individual enrollment rows.
     */
}

main().catch(error => {
    console.error('Fatal error:', error.message);
    process.exitCode = 1;
});
