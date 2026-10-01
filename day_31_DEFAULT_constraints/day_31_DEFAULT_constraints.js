"use strict";

/*
 * DEFAULT Constraints
 *
 * This file provides a JavaScript-specific model of database DEFAULT
 * behavior. It uses Node.js-compatible JavaScript and demonstrates:
 *
 * - static defaults
 * - omission versus explicit null
 * - generated UUID values
 * - dynamic timestamps
 * - application-side versus persistence-side defaults
 * - event-driven record creation
 * - reviewable default policies
 * - validation and failure handling
 * - schema migration reasoning
 * - merge-style persistence behavior
 *
 * No external npm packages are required.
 */

const crypto = require("node:crypto");

function heading(title) {
  console.log(`\n${"=".repeat(78)}\n${title}\n${"=".repeat(78)}`);
}

function subsection(title) {
  console.log(`\n--- ${title} ---`);
}

// ---------------------------------------------------------------------------
// Static defaults
// ---------------------------------------------------------------------------

heading("Static DEFAULT Values");

const accountDefaults = Object.freeze({
  status: "active",
  role: "member",
  timezone: "UTC",
  notificationEnabled: true,
});

console.log("Static policy:", accountDefaults);

function createAccount(input = {}) {
  const account = {
    status: input.status ?? accountDefaults.status,
    role: input.role ?? accountDefaults.role,
    timezone: input.timezone ?? accountDefaults.timezone,
    notificationEnabled:
      input.notificationEnabled ?? accountDefaults.notificationEnabled,
  };

  if (!["active", "suspended", "closed"].includes(account.status)) {
    throw new Error(`Unsupported account status: ${account.status}`);
  }

  if (!["member", "admin", "service"].includes(account.role)) {
    throw new Error(`Unsupported account role: ${account.role}`);
  }

  return account;
}

console.log("Defaulted account:", createAccount());
console.log(
  "Explicit account:",
  createAccount({
    status: "suspended",
    role: "service",
    notificationEnabled: false,
  })
);


// ---------------------------------------------------------------------------
// Omission versus explicit null
//
// The nullish-coalescing operator treats null like an absent value. That is
// appropriate for some application APIs, but it does not exactly reproduce
// SQL semantics where explicit NULL can remain NULL. The next model preserves
// that distinction.
// ---------------------------------------------------------------------------

heading("Omission Versus Explicit NULL");

const MISSING = Symbol("missing");

function resolveSqlLikeDefault(value, defaultValue) {
  if (value === MISSING) {
    return typeof defaultValue === "function" ? defaultValue() : defaultValue;
  }

  return value;
}

console.log(
  "Omitted:",
  resolveSqlLikeDefault(MISSING, "pending")
);

console.log(
  "Explicit null:",
  resolveSqlLikeDefault(null, "pending")
);

function insertLikeDatabase(row) {
  const nullable = new Set(["description"]);

  const status = resolveSqlLikeDefault(row.status, "pending");
  const description = resolveSqlLikeDefault(row.description, null);

  if (status === null) {
    throw new Error("status cannot be NULL");
  }

  if (description === null && !nullable.has("description")) {
    throw new Error("description cannot be NULL");
  }

  return {
    status,
    description,
  };
}

console.log(insertLikeDatabase({
  status: MISSING,
  description: MISSING,
}));

console.log(insertLikeDatabase({
  status: MISSING,
  description: null,
}));


// ---------------------------------------------------------------------------
// Generated UUID defaults
// ---------------------------------------------------------------------------

heading("Generated UUID Defaults");

function generateUuid() {
  return crypto.randomUUID();
}

function createJob(input = {}) {
  return {
    id: input.id === undefined ? generateUuid() : input.id,
    name: input.name ?? "background-job",
    state: input.state ?? "queued",
  };
}

const jobA = createJob({ name: "invoice-worker" });
const jobB = createJob({ name: "audit-worker" });

console.log(jobA);
console.log(jobB);

if (jobA.id === jobB.id) {
  throw new Error("UUID generation produced a duplicate identifier");
}


// ---------------------------------------------------------------------------
// Dynamic timestamps
// ---------------------------------------------------------------------------

heading("Timestamp Defaults");

function utcTimestamp() {
  return new Date().toISOString();
}

function createAuditEvent(name, input = {}) {
  return {
    eventId: input.eventId ?? generateUuid(),
    name,
    createdAt: input.createdAt ?? utcTimestamp(),
  };
}

const createdEvent = createAuditEvent("account.created");

console.log(createdEvent);

function parseTimestamp(value) {
  const timestamp = Date.parse(value);

  if (Number.isNaN(timestamp)) {
    throw new Error(`Invalid timestamp: ${value}`);
  }

  return timestamp;
}

parseTimestamp(createdEvent.createdAt);


// ---------------------------------------------------------------------------
// Default factories
//
// A factory must run for each object. Reusing one generated value at module
// initialization would accidentally turn a dynamic default into a constant.
// ---------------------------------------------------------------------------

heading("Per-Record Default Factories");

const incorrectSharedTimestamp = utcTimestamp();
const incorrectSharedId = generateUuid();

function incorrectRecord() {
  return {
    id: incorrectSharedId,
    createdAt: incorrectSharedTimestamp,
  };
}

function correctRecord() {
  return {
    id: generateUuid(),
    createdAt: utcTimestamp(),
  };
}

const incorrectA = incorrectRecord();
const incorrectB = incorrectRecord();

console.log("Incorrect shared defaults:", incorrectA, incorrectB);

const correctA = correctRecord();
const correctB = correctRecord();

console.log("Correct per-record defaults:", correctA, correctB);


// ---------------------------------------------------------------------------
// Application-side and database-side ownership
// ---------------------------------------------------------------------------

heading("Default Ownership");

class ApplicationDefaultStore {
  createInvoice(input) {
    const invoice = {
      id: generateUuid(),
      state: input.state ?? "draft",
      currency: input.currency ?? "INR",
      createdAt: utcTimestamp(),
      amount: input.amount,
    };

    this.validateInvoice(invoice);
    return invoice;
  }

  validateInvoice(invoice) {
    if (!Number.isFinite(invoice.amount) || invoice.amount <= 0) {
      throw new Error("Invoice amount must be greater than zero");
    }

    if (!["INR", "USD", "EUR"].includes(invoice.currency)) {
      throw new Error("Unsupported invoice currency");
    }
  }
}

const applicationStore = new ApplicationDefaultStore();

console.log(
  applicationStore.createInvoice({
    amount: 12500,
  })
);


// ---------------------------------------------------------------------------
// A persistence model. This intentionally behaves like a database table:
// callers provide only columns they explicitly want to override, while the
// persistence boundary fills database-owned defaults.
// ---------------------------------------------------------------------------

class InMemoryTable {
  constructor(schema) {
    this.schema = schema;
    this.rows = [];
  }

  insert(input = {}) {
    const row = {};

    for (const [column, definition] of Object.entries(this.schema)) {
      if (Object.prototype.hasOwnProperty.call(input, column)) {
        row[column] = input[column];
      } else if (definition.hasDefault) {
        row[column] =
          typeof definition.defaultValue === "function"
            ? definition.defaultValue()
            : definition.defaultValue;
      } else if (definition.required) {
        throw new Error(`Required column omitted: ${column}`);
      } else {
        row[column] = null;
      }

      if (row[column] === null && !definition.nullable) {
        throw new Error(`Column does not permit NULL: ${column}`);
      }

      if (definition.validate) {
        definition.validate(row[column]);
      }
    }

    this.rows.push(Object.freeze(row));
    return row;
  }

  all() {
    return [...this.rows];
  }
}

const users = new InMemoryTable({
  id: {
    required: true,
    nullable: false,
    hasDefault: true,
    defaultValue: generateUuid,
  },
  username: {
    required: true,
    nullable: false,
    hasDefault: false,
    validate(value) {
      if (!/^[a-z][a-z0-9_]{2,31}$/.test(value)) {
        throw new Error("username has an invalid format");
      }
    },
  },
  status: {
    required: true,
    nullable: false,
    hasDefault: true,
    defaultValue: "active",
  },
  createdAt: {
    required: true,
    nullable: false,
    hasDefault: true,
    defaultValue: utcTimestamp,
  },
  timezone: {
    required: true,
    nullable: false,
    hasDefault: true,
    defaultValue: "UTC",
  },
});

console.log(
  users.insert({
    username: "atul_dev",
  })
);

console.log(
  users.insert({
    username: "service_account",
    status: "active",
    timezone: "Asia/Kolkata",
  })
);

try {
  users.insert({
    username: "INVALID USER",
  });
} catch (error) {
  console.log("Validation failure:", error.message);
}


// ---------------------------------------------------------------------------
// Event-driven default processing
//
// JavaScript's event model makes it useful to model a persistence pipeline
// in which the INSERT operation emits an event after defaults have been
// resolved.
// ---------------------------------------------------------------------------

heading("Event-Driven Default Resolution");

class DefaultAwareRepository {
  constructor() {
    this.records = new Map();
    this.listeners = new Map();
  }

  on(eventName, callback) {
    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, []);
    }

    this.listeners.get(eventName).push(callback);
  }

  emit(eventName, payload) {
    for (const callback of this.listeners.get(eventName) ?? []) {
      callback(payload);
    }
  }

  insert(input) {
    const record = {
      id: input.id ?? generateUuid(),
      state: input.state ?? "queued",
      createdAt: input.createdAt ?? utcTimestamp(),
      attempts: input.attempts ?? 0,
    };

    if (!Number.isInteger(record.attempts) || record.attempts < 0) {
      throw new Error("attempts must be a non-negative integer");
    }

    this.records.set(record.id, Object.freeze(record));
    this.emit("inserted", record);

    return record;
  }
}

const repository = new DefaultAwareRepository();

repository.on("inserted", (record) => {
  console.log(
    `Inserted ${record.id} with state=${record.state} at ${record.createdAt}`
  );
});

repository.insert({});


// ---------------------------------------------------------------------------
// Default policy evaluation
// ---------------------------------------------------------------------------

heading("Default Policy Evaluation");

const policies = {
  state: {
    owner: "database",
    expression: "'queued'",
    rationale: "Every newly persisted job starts in a known state.",
  },
  id: {
    owner: "application",
    expression: "crypto.randomUUID()",
    rationale: "The service needs the identifier before persistence.",
  },
  createdAt: {
    owner: "database",
    expression: "CURRENT_TIMESTAMP",
    rationale: "Persistence time should be authoritative at the storage boundary.",
  },
  attempts: {
    owner: "database",
    expression: "0",
    rationale: "New work has not yet been attempted.",
  },
};

for (const [column, policy] of Object.entries(policies)) {
  console.log(
    `${column}: owner=${policy.owner}; ` +
    `expression=${policy.expression}; ` +
    `${policy.rationale}`
  );
}


// ---------------------------------------------------------------------------
// Schema migration model
//
// Changing a DEFAULT does not automatically mean that existing stored rows
// should change. This model separates schema policy from data migration.
// ---------------------------------------------------------------------------

heading("Default Migration Semantics");

class VersionedTable {
  constructor(defaultState) {
    this.defaultState = defaultState;
    this.rows = [];
  }

  insert(name, explicitState = MISSING) {
    const state = explicitState === MISSING
      ? this.defaultState
      : explicitState;

    const row = {
      id: generateUuid(),
      name,
      state,
    };

    this.rows.push(row);
    return row;
  }

  changeDefault(newDefaultState) {
    this.defaultState = newDefaultState;
  }
}

const workflowTable = new VersionedTable("pending");

const oldRow = workflowTable.insert("old-task");

workflowTable.changeDefault("queued");

const newRow = workflowTable.insert("new-task");

console.log("Existing row:", oldRow);
console.log("Future insert:", newRow);


// ---------------------------------------------------------------------------
// Explicit data migration. This is deliberately separate from changing the
// default because historical data may require different business rules.
// ---------------------------------------------------------------------------

function migratePendingToQueued(rows) {
  return rows.map((row) => {
    if (row.state === "pending") {
      return {
        ...row,
        state: "queued",
        migratedAt: utcTimestamp(),
      };
    }

    return row;
  });
}

const migratedRows = migratePendingToQueued([
  oldRow,
  newRow,
]);

console.log("Migrated data:", migratedRows);


// ---------------------------------------------------------------------------
// Partial update behavior
//
// Defaults generally operate during INSERT, not arbitrary UPDATE operations.
// An update that does not mention a column normally leaves its current value
// unchanged.
// ---------------------------------------------------------------------------

heading("INSERT Defaults Versus UPDATE Behavior");

function updateRecord(record, patch) {
  const updated = { ...record, ...patch };

  if (updated.attempts < 0) {
    throw new Error("attempts cannot be negative");
  }

  return updated;
}

const existingJob = {
  id: generateUuid(),
  state: "queued",
  attempts: 0,
};

const updatedJob = updateRecord(existingJob, {
  state: "running",
});

console.log("Original:", existingJob);
console.log("Updated:", updatedJob);

if (updatedJob.attempts !== 0) {
  throw new Error("Unmodified column should retain its stored value");
}


// ---------------------------------------------------------------------------
// Security and correctness: defaults must not be treated as authorization.
// A default role can establish an initial state, but privilege checks should
// still validate the requested operation.
// ---------------------------------------------------------------------------

heading("Security Boundary");

function createSecurityPrincipal(input = {}) {
  const principal = {
    id: input.id ?? generateUuid(),
    role: input.role ?? "member",
    enabled: input.enabled ?? true,
  };

  const allowedRoles = new Set(["member", "admin", "service"]);

  if (!allowedRoles.has(principal.role)) {
    throw new Error("Invalid principal role");
  }

  return principal;
}

function requireAdmin(principal) {
  if (!principal.enabled) {
    throw new Error("Disabled principal cannot perform administrative actions");
  }

  if (principal.role !== "admin") {
    throw new Error("Administrative role required");
  }
}

const principal = createSecurityPrincipal();

try {
  requireAdmin(principal);
} catch (error) {
  console.log("Authorization failure:", error.message);
}


// ---------------------------------------------------------------------------
// Performance: generated identifiers and timestamps are normally inexpensive,
// but identifier representation can influence indexes, storage size, and
// locality in high-write systems.
// ---------------------------------------------------------------------------

heading("Performance Characteristics");

const performanceObservations = [
  "Literal defaults have negligible generation cost.",
  "Timestamp defaults execute once for each inserted row.",
  "UUID generation is inexpensive but produces a larger identifier than many integer keys.",
  "Random UUID ordering can reduce index locality in storage engines that use ordered indexes.",
  "Database-owned defaults avoid repeated client-side implementation of persistence metadata.",
];

for (const observation of performanceObservations) {
  console.log(`- ${observation}`);
}


// ---------------------------------------------------------------------------
// Final integrated example
// ---------------------------------------------------------------------------

heading("Integrated Service Record Example");

class ServiceRecordStore {
  constructor() {
    this.records = new Map();
  }

  create(input = {}) {
    if (typeof input.name !== "string" || input.name.trim() === "") {
      throw new Error("name is required");
    }

    const record = {
      id: input.id ?? generateUuid(),
      name: input.name,
      status: input.status ?? "ready",
      priority: input.priority ?? 5,
      enabled: input.enabled ?? true,
      createdAt: input.createdAt ?? utcTimestamp(),
    };

    if (!Number.isInteger(record.priority) || record.priority < 0) {
      throw new Error("priority must be a non-negative integer");
    }

    if (!["ready", "paused", "disabled"].includes(record.status)) {
      throw new Error("invalid service status");
    }

    if (typeof record.enabled !== "boolean") {
      throw new Error("enabled must be boolean");
    }

    this.records.set(record.id, Object.freeze(record));
    return record;
  }

  find(id) {
    return this.records.get(id) ?? null;
  }
}

const serviceStore = new ServiceRecordStore();

const service = serviceStore.create({
  name: "risk-calculation-worker",
});

const highPriorityService = serviceStore.create({
  name: "audit-worker",
  priority: 10,
  status: "ready",
});

console.log(service);
console.log(highPriorityService);

console.log(
  "Lookup:",
  serviceStore.find(service.id)
);

console.log("\nDEFAULT constraint demonstrations completed successfully.");
