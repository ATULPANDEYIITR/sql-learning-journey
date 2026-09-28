/*
 * PRIMARY KEY
 * ===========
 *
 * A standalone JavaScript study file covering:
 * - primary-key fundamentals
 * - entity identification
 * - uniqueness
 * - candidate and alternate keys
 * - natural and surrogate identifiers
 * - composite primary keys
 * - foreign-key relationships
 * - validation
 * - immutable key objects
 * - JavaScript Map-based indexing
 * - UUIDs
 * - deterministic identifiers
 * - realistic order-management modeling
 * - performance considerations
 * - security considerations
 * - edge cases and testing
 *
 * Run:
 *   node primary_key.js
 */

"use strict";

// ============================================================================
// 1. OUTPUT HELPERS
// ============================================================================

function printSection(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}

function printObject(label, value) {
    console.log(label, JSON.stringify(value, null, 2));
}


// ============================================================================
// 2. CUSTOM ERRORS
// ============================================================================

class DuplicateKeyError extends Error {
    constructor(message) {
        super(message);
        this.name = "DuplicateKeyError";
    }
}

class MissingKeyError extends Error {
    constructor(message) {
        super(message);
        this.name = "MissingKeyError";
    }
}

class ForeignKeyError extends Error {
    constructor(message) {
        super(message);
        this.name = "ForeignKeyError";
    }
}

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}


// ============================================================================
// 3. FUNDAMENTALS
// ============================================================================

function explainFundamentals() {
    printSection("1. PRIMARY-KEY FUNDAMENTALS");

    console.log(`
A primary key identifies exactly one row in a relational table.

Core properties:

  UNIQUE:
      Two rows cannot have the same primary-key value.

  NOT NULL:
      A row must have an actual identity.

  IDENTIFICATION:
      The key answers which entity or relationship instance a row represents.

  STABILITY:
      A good key normally does not change during ordinary business updates.

  MINIMALITY:
      A candidate key should contain no unnecessary attributes.

Examples:

  student(student_id, name, email)
      student_id identifies one student.

  product(product_id, name, price)
      product_id identifies one product.

  enrollment(student_id, course_id)
      the pair identifies one student-course relationship.
`);
}


// ============================================================================
// 4. SIMPLE PRIMARY-KEY TABLE
// ============================================================================

class PrimaryKeyTable {
    constructor(name) {
        this.name = name;

        // Map is useful for demonstrating direct key-based lookup.
        // A database uses its own physical indexing structures internally.
        this.rows = new Map();
    }

    insert(primaryKey, row) {
        if (primaryKey === null || primaryKey === undefined) {
            throw new MissingKeyError(
                `${this.name}: primary key cannot be null or undefined`
            );
        }

        if (this.rows.has(primaryKey)) {
            throw new DuplicateKeyError(
                `${this.name}: duplicate primary key ${String(primaryKey)}`
            );
        }

        this.rows.set(primaryKey, { ...row });
    }

    get(primaryKey) {
        return this.rows.get(primaryKey);
    }

    has(primaryKey) {
        return this.rows.has(primaryKey);
    }

    delete(primaryKey) {
        return this.rows.delete(primaryKey);
    }

    count() {
        return this.rows.size;
    }
}

function demonstrateSimpleKey() {
    printSection("2. SIMPLE PRIMARY KEY");

    const students = new PrimaryKeyTable("students");

    students.insert(101, {
        studentId: 101,
        name: "Asha",
        email: "asha@example.com"
    });

    students.insert(102, {
        studentId: 102,
        name: "Ravi",
        email: "ravi@example.com"
    });

    printObject("Student 101:", students.get(101));
    console.log("Student count:", students.count());

    try {
        students.insert(101, {
            studentId: 101,
            name: "Duplicate",
            email: "duplicate@example.com"
        });
    } catch (error) {
        console.log("Duplicate rejected:", error.message);
    }

    try {
        students.insert(null, {
            studentId: null,
            name: "Missing",
            email: "missing@example.com"
        });
    } catch (error) {
        console.log("Missing key rejected:", error.message);
    }
}


// ============================================================================
// 5. ENTITY IDENTIFICATION
// ============================================================================

function demonstrateEntityIdentification() {
    printSection("3. ENTITY IDENTIFICATION");

    const students = new Map([
        [1001, { studentId: 1001, name: "Anita" }],
        [1002, { studentId: 1002, name: "Vikram" }]
    ]);

    const requestedId = 1002;
    const entity = students.get(requestedId);

    printObject("Requested entity:", entity);

    console.log(`
The identifier separates identity from other attributes.

A student's name can change.
A student's email can change.
A student's identity should remain associated with the same primary key.

This distinction is particularly important when other tables reference
the student.
`);
}


// ============================================================================
// 6. CANDIDATE AND ALTERNATE KEYS
// ============================================================================

function demonstrateCandidateKeys() {
    printSection("4. CANDIDATE AND ALTERNATE KEYS");

    const candidateKeys = [
        {
            name: "Student ID",
            columns: ["studentId"],
            selectedAsPrimary: true
        },
        {
            name: "University Registration Number",
            columns: ["registrationNumber"],
            selectedAsPrimary: false
        },
        {
            name: "Email",
            columns: ["email"],
            selectedAsPrimary: false
        }
    ];

    candidateKeys.forEach(key => {
        console.log(
            `${key.selectedAsPrimary ? "PRIMARY" : "ALTERNATE"} | ` +
            `${key.name} | ${key.columns.join(", ")}`
        );
    });

    console.log(`
A candidate key is a minimal set of attributes capable of uniquely
identifying a row.

One candidate key is selected as the primary key.

Other candidate keys can still be enforced with UNIQUE constraints.
`);
}


// ============================================================================
// 7. NATURAL AND SURROGATE KEYS
// ============================================================================

function explainNaturalAndSurrogateKeys() {
    printSection("5. NATURAL VS SURROGATE KEYS");

    console.log(`
Natural key:
  A business or domain attribute that already identifies an entity.

Examples:
  country code
  ISBN
  employee number

Surrogate key:
  A database-oriented identifier created specifically for identity.

Examples:
  integer sequence
  UUID

A natural key can be attractive because it carries meaning. The risk is that
business meaning can change.

A surrogate key can remain stable while business attributes change.

A common design is:

  customer_id PRIMARY KEY
  email UNIQUE

This separates stable identity from business uniqueness.
`);
}


// ============================================================================
// 8. COMPOSITE PRIMARY KEYS
// ============================================================================

function compositeKeyToString(left, right) {
    // A delimiter makes the two components distinguishable.
    // Production systems should choose a representation that cannot create
    // ambiguous collisions.
    return `${left}:${right}`;
}

function demonstrateCompositeKey() {
    printSection("6. COMPOSITE PRIMARY KEY");

    const enrollments = new Map();

    const firstKey = compositeKeyToString(101, 501);
    const secondKey = compositeKeyToString(101, 502);
    const thirdKey = compositeKeyToString(102, 501);

    enrollments.set(firstKey, {
        studentId: 101,
        courseId: 501,
        grade: "A"
    });

    enrollments.set(secondKey, {
        studentId: 101,
        courseId: 502,
        grade: "B"
    });

    enrollments.set(thirdKey, {
        studentId: 102,
        courseId: 501,
        grade: "A"
    });

    printObject(
        "Enrollment (101, 501):",
        enrollments.get(firstKey)
    );

    if (enrollments.has(firstKey)) {
        console.log("Duplicate composite key rejected.");
    }

    console.log(`
Why are two columns required?

studentId alone:
  Not unique because one student can take many courses.

courseId alone:
  Not unique because one course can contain many students.

(studentId, courseId):
  Unique for the enrollment relationship.
`);
}


// ============================================================================
// 9. FOREIGN-KEY VALIDATION
// ============================================================================

function demonstrateForeignKeys() {
    printSection("7. FOREIGN KEYS AND REFERENTIAL INTEGRITY");

    const students = new Map([
        [1, { studentId: 1, name: "Asha" }],
        [2, { studentId: 2, name: "Ravi" }]
    ]);

    const enrollment = {
        studentId: 1,
        courseId: 900
    };

    if (!students.has(enrollment.studentId)) {
        throw new ForeignKeyError("Student does not exist.");
    }

    console.log("Valid foreign-key reference accepted.");

    const invalidEnrollment = {
        studentId: 999,
        courseId: 900
    };

    try {
        if (!students.has(invalidEnrollment.studentId)) {
            throw new ForeignKeyError(
                `Student ${invalidEnrollment.studentId} does not exist.`
            );
        }
    } catch (error) {
        console.log("Invalid reference rejected:", error.message);
    }
}


// ============================================================================
// 10. UUID IDENTIFIERS
// ============================================================================

function createUuid() {
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
        return crypto.randomUUID();
    }

    // Node.js exposes crypto.randomUUID through the global crypto API in
    // modern runtimes. This fallback is intentionally deterministic in
    // structure but not cryptographically equivalent.
    const bytes = Array.from({ length: 16 }, () =>
        Math.floor(Math.random() * 256)
    );

    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    const hex = bytes.map(value => value.toString(16).padStart(2, "0"));

    return [
        hex.slice(0, 4).join(""),
        hex.slice(4, 6).join(""),
        hex.slice(6, 8).join(""),
        hex.slice(8, 10).join(""),
        hex.slice(10, 16).join("")
    ].join("-");
}

function demonstrateUuidKeys() {
    printSection("8. UUID PRIMARY KEYS");

    const firstId = createUuid();
    const secondId = createUuid();

    console.log("UUID 1:", firstId);
    console.log("UUID 2:", secondId);
    console.log("UUIDs different:", firstId !== secondId);

    console.log(`
UUIDs are useful in distributed systems because separate application
instances can generate identifiers without relying on a single sequence.

Trade-offs include:

  - Larger storage than small integer keys.
  - Poorer human readability.
  - Random identifiers can have different index-locality behavior than
    sequential identifiers.
`);
}


// ============================================================================
// 11. KEY VALIDATION
// ============================================================================

function validatePositiveIntegerKey(value) {
    if (typeof value !== "number" || !Number.isInteger(value)) {
        throw new ValidationError("Primary key must be an integer.");
    }

    if (value <= 0) {
        throw new ValidationError("Primary key must be positive.");
    }

    return value;
}

function validateUuidKey(value) {
    if (typeof value !== "string") {
        throw new ValidationError("UUID must be a string.");
    }

    const uuidPattern =
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

    if (!uuidPattern.test(value)) {
        throw new ValidationError("Invalid UUID.");
    }

    return value;
}

function demonstrateValidation() {
    printSection("9. PRIMARY-KEY VALIDATION");

    [1, 10, 1000].forEach(value => {
        console.log("Accepted:", validatePositiveIntegerKey(value));
    });

    [0, -1, 1.5, "100", null].forEach(value => {
        try {
            validatePositiveIntegerKey(value);
        } catch (error) {
            console.log(`Rejected ${JSON.stringify(value)}:`, error.message);
        }
    });

    const uuid = createUuid();
    console.log("UUID validation:", validateUuidKey(uuid));
}


// ============================================================================
// 12. IMMUTABLE COMPOSITE KEY
// ============================================================================

class OrderLineKey {
    constructor(orderId, productId) {
        if (!Number.isInteger(orderId) || orderId <= 0) {
            throw new ValidationError("orderId must be positive.");
        }

        if (!Number.isInteger(productId) || productId <= 0) {
            throw new ValidationError("productId must be positive.");
        }

        // Object.freeze prevents accidental mutation of the key object.
        this.orderId = orderId;
        this.productId = productId;
        Object.freeze(this);
    }

    toString() {
        return `${this.orderId}:${this.productId}`;
    }
}

function demonstrateImmutableCompositeKey() {
    printSection("10. IMMUTABLE COMPOSITE KEY OBJECT");

    const key = new OrderLineKey(7001, 45);
    console.log("Key:", key.toString());

    try {
        key.orderId = 9999;
    } catch (error) {
        console.log("Mutation rejected in strict mode:", error.message);
    }

    console.log("Key after attempted mutation:", key.toString());
}


// ============================================================================
// 13. REALISTIC ORDER SYSTEM
// ============================================================================

class Customer {
    constructor(customerId, email, name) {
        validatePositiveIntegerKey(customerId);

        if (typeof email !== "string" || !email.includes("@")) {
            throw new ValidationError("Invalid email.");
        }

        if (!name || !name.trim()) {
            throw new ValidationError("Name cannot be empty.");
        }

        this.customerId = customerId;
        this.email = email;
        this.name = name;
    }
}

class Product {
    constructor(productId, name, priceCents) {
        validatePositiveIntegerKey(productId);

        if (!name || !name.trim()) {
            throw new ValidationError("Product name cannot be empty.");
        }

        if (!Number.isInteger(priceCents) || priceCents < 0) {
            throw new ValidationError(
                "Price must be a non-negative integer number of cents."
            );
        }

        this.productId = productId;
        this.name = name;
        this.priceCents = priceCents;
    }
}

class OrderLine {
    constructor(orderId, productId, quantity) {
        validatePositiveIntegerKey(orderId);
        validatePositiveIntegerKey(productId);

        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new ValidationError("Quantity must be positive.");
        }

        this.orderId = orderId;
        this.productId = productId;
        this.quantity = quantity;
    }
}

class OrderManagementSystem {
    constructor() {
        this.customers = new Map();
        this.products = new Map();
        this.orderLines = new Map();
    }

    addCustomer(customer) {
        if (this.customers.has(customer.customerId)) {
            throw new DuplicateKeyError(
                `Customer ${customer.customerId} already exists.`
            );
        }

        for (const existing of this.customers.values()) {
            if (existing.email === customer.email) {
                throw new ValidationError(
                    "Customer email must be unique."
                );
            }
        }

        this.customers.set(customer.customerId, customer);
    }

    addProduct(product) {
        if (this.products.has(product.productId)) {
            throw new DuplicateKeyError(
                `Product ${product.productId} already exists.`
            );
        }

        this.products.set(product.productId, product);
    }

    addOrderLine(orderLine) {
        if (!this.products.has(orderLine.productId)) {
            throw new ForeignKeyError(
                `Product ${orderLine.productId} does not exist.`
            );
        }

        const key = new OrderLineKey(
            orderLine.orderId,
            orderLine.productId
        );

        const serializedKey = key.toString();

        if (this.orderLines.has(serializedKey)) {
            throw new DuplicateKeyError(
                `Order line ${serializedKey} already exists.`
            );
        }

        this.orderLines.set(serializedKey, orderLine);
    }

    calculateOrderTotal(orderId) {
        let total = 0;

        for (const line of this.orderLines.values()) {
            if (line.orderId === orderId) {
                const product = this.products.get(line.productId);

                if (!product) {
                    throw new ForeignKeyError(
                        `Product ${line.productId} no longer exists.`
                    );
                }

                total += product.priceCents * line.quantity;
            }
        }

        return total;
    }
}

function runOrderCaseStudy() {
    printSection("11. INDUSTRY-STYLE ORDER CASE STUDY");

    const system = new OrderManagementSystem();

    system.addCustomer(
        new Customer(
            1,
            "buyer@example.com",
            "Buyer"
        )
    );

    system.addProduct(
        new Product(
            101,
            "Keyboard",
            5000
        )
    );

    system.addProduct(
        new Product(
            102,
            "Mouse",
            2500
        )
    );

    system.addOrderLine(
        new OrderLine(
            9001,
            101,
            2
        )
    );

    system.addOrderLine(
        new OrderLine(
            9001,
            102,
            1
        )
    );

    console.log(
        "Order 9001 total:",
        system.calculateOrderTotal(9001),
        "cents"
    );

    const testCases = [
        () => system.addProduct(
            new Product(101, "Duplicate Keyboard", 7000)
        ),
        () => system.addOrderLine(
            new OrderLine(9001, 101, 1)
        ),
        () => system.addOrderLine(
            new OrderLine(9002, 999, 1)
        ),
        () => system.addOrderLine(
            new OrderLine(9003, 101, 0)
        )
    ];

    testCases.forEach((testCase, index) => {
        try {
            testCase();
        } catch (error) {
            console.log(
                `Expected failure ${index + 1}:`,
                error.message
            );
        }
    });
}


// ============================================================================
// 14. PERFORMANCE
// ============================================================================

function demonstratePerformance() {
    printSection("12. KEY LOOKUP PERFORMANCE");

    const records = new Map();

    for (let id = 1; id <= 100000; id += 1) {
        records.set(id, `Entity ${id}`);
    }

    const start = performance.now();
    const result = records.get(99999);
    const elapsed = performance.now() - start;

    console.log("Lookup result:", result);
    console.log(
        "Map lookup elapsed time:",
        elapsed.toFixed(6),
        "ms"
    );

    console.log(`
Map lookup is designed for efficient key-based access.

This does not mean that every database primary-key lookup is literally a
JavaScript Map lookup. Database engines use specialized indexing and storage
structures.

Typical conceptual comparisons:

  Full scan:
      O(n)

  Balanced-tree index:
      approximately O(log n)

  Hash-based lookup:
      approximately O(1) average

Actual database performance depends on the database engine, index design,
cache behavior, data distribution, query plan, and workload.
`);
}


// ============================================================================
// 15. HASH IDENTIFIERS
// ============================================================================

async function demonstrateHashIdentifier() {
    printSection("13. HASHES AND IDENTIFIERS");

    console.log(`
A cryptographic hash can provide a deterministic digest, but a hash is not
automatically a relational primary key.

A primary key still needs an explicit uniqueness constraint.

Hash collisions are theoretically possible.
`);

    if (globalThis.crypto && typeof globalThis.crypto.subtle === "object") {
        const data = new TextEncoder().encode("example-record");
        const digest = await globalThis.crypto.subtle.digest(
            "SHA-256",
            data
        );

        const bytes = new Uint8Array(digest);
        const hexadecimal = Array.from(bytes)
            .map(byte => byte.toString(16).padStart(2, "0"))
            .join("");

        console.log("SHA-256:", hexadecimal);
    } else {
        console.log(
            "Web Crypto API is unavailable in this runtime."
        );
    }
}


// ============================================================================
// 16. NULL / UNDEFINED / EMPTY STRING
// ============================================================================

function demonstrateMissingValues() {
    printSection("14. NULL, UNDEFINED, AND EMPTY VALUES");

    const values = [
        null,
        undefined,
        "",
        0,
        false
    ];

    values.forEach(value => {
        console.log(
            JSON.stringify(value),
            "typeof =",
            typeof value
        );
    });

    console.log(`
JavaScript has several values that can represent absence or falsy state.

A relational primary key should not rely on JavaScript truthiness.

Bad validation:

    if (!id) { ... }

This rejects 0 but can also blur the distinction between different invalid
values.

Prefer explicit validation based on the actual identifier contract.
`);
}


// ============================================================================
// 17. SECURITY
// ============================================================================

function explainSecurity() {
    printSection("15. SECURITY CONSIDERATIONS");

    console.log(`
A primary key is an identity value, not an authorization credential.

This is unsafe as an authorization model:

    GET /customers/123
    "The caller knows 123, therefore access is allowed."

The application must separately determine whether the authenticated user is
authorized to access customer 123.

Sequential identifiers can also make resource enumeration easier.

Possible defensive techniques include:

  - authorization checks
  - rate limiting
  - audit logging
  - non-guessable public identifiers where appropriate
  - avoiding unnecessary exposure of internal identifiers

UUIDs can reduce casual predictability but do not replace authorization.
`);
}


// ============================================================================
// 18. TESTS
// ============================================================================

function runTests() {
    printSection("16. AUTOMATED TESTS");

    const table = new PrimaryKeyTable("test");

    table.insert(1, { id: 1 });

    if (!table.has(1)) {
        throw new Error("Primary-key existence test failed.");
    }

    if (table.count() !== 1) {
        throw new Error("Count test failed.");
    }

    try {
        table.insert(1, { id: 1 });
        throw new Error("Duplicate should have failed.");
    } catch (error) {
        if (!(error instanceof DuplicateKeyError)) {
            throw error;
        }
    }

    try {
        table.insert(null, { id: null });
        throw new Error("Missing key should have failed.");
    } catch (error) {
        if (!(error instanceof MissingKeyError)) {
            throw error;
        }
    }

    const key = new OrderLineKey(1, 10);

    if (key.toString() !== "1:10") {
        throw new Error("Composite key serialization failed.");
    }

    console.log("All tests passed.");
}


// ============================================================================
// 19. DESIGN COMPARISON
// ============================================================================

function designComparison() {
    printSection("17. KEY-DESIGN COMPARISON");

    const strategies = [
        {
            situation: "Internal entity identity",
            strategy: "Integer surrogate",
            consideration: "Compact and simple"
        },
        {
            situation: "Distributed generation",
            strategy: "UUID",
            consideration: "No central sequence required"
        },
        {
            situation: "Many-to-many relationship",
            strategy: "Composite key",
            consideration: "Represents relationship identity"
        },
        {
            situation: "Stable business identifier",
            strategy: "Natural key",
            consideration: "Meaningful but must remain suitable"
        },
        {
            situation: "Mutable business attribute",
            strategy: "Surrogate + UNIQUE",
            consideration: "Identity remains stable"
        }
    ];

    console.table(strategies);
}


// ============================================================================
// 20. MAIN
// ============================================================================

async function main() {
    explainFundamentals();
    demonstrateSimpleKey();
    demonstrateEntityIdentification();
    demonstrateCandidateKeys();
    explainNaturalAndSurrogateKeys();
    demonstrateCompositeKey();
    demonstrateForeignKeys();
    demonstrateUuidKeys();
    demonstrateValidation();
    demonstrateImmutableCompositeKey();
    runOrderCaseStudy();
    demonstratePerformance();
    await demonstrateHashIdentifier();
    demonstrateMissingValues();
    explainSecurity();
    runTests();
    designComparison();

    printSection("18. END OF PRIMARY-KEY STUDY");
    console.log(
        "The program demonstrated simple, natural, surrogate, UUID, and " +
        "composite primary-key strategies."
    );
}

main().catch(error => {
    console.error("Program failed:", error);
    process.exitCode = 1;
});
