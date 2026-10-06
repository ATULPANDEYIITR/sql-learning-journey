"use strict";

/*
 * CROSS JOIN: Cartesian Products and Combination Management
 *
 * This Node.js program models CROSS JOIN behavior using JavaScript-specific
 * techniques: iterators, generators, Sets, Maps, asynchronous processing,
 * event-driven notifications, validation, and bounded combination generation.
 *
 * Run with:
 *   node cross_join.js
 */

const EventEmitter = require("node:events");

function printHeading(title) {
  console.log(`\n${"=".repeat(78)}`);
  console.log(title);
  console.log("=".repeat(78));
}

function crossJoin(left, right) {
  if (!Array.isArray(left) || !Array.isArray(right)) {
    throw new TypeError("Both CROSS JOIN inputs must be arrays.");
  }

  const result = [];

  for (const leftRow of left) {
    for (const rightRow of right) {
      result.push([leftRow, rightRow]);
    }
  }

  return result;
}

function* crossJoinGenerator(left, right) {
  /*
   * A generator yields one combination at a time. This avoids retaining the
   * entire Cartesian product in an array.
   */
  if (!left || !right || typeof left[Symbol.iterator] !== "function") {
    throw new TypeError("Inputs must be iterable.");
  }

  const rightValues = Array.from(right);

  for (const leftRow of left) {
    for (const rightRow of rightValues) {
      yield [leftRow, rightRow];
    }
  }
}

function cartesianProduct(groups) {
  if (!Array.isArray(groups)) {
    throw new TypeError("groups must be an array.");
  }

  if (groups.length === 0) {
    return [[]];
  }

  if (groups.some((group) => !Array.isArray(group))) {
    throw new TypeError("Every Cartesian-product dimension must be an array.");
  }

  let combinations = [[]];

  for (const group of groups) {
    const next = [];

    for (const prefix of combinations) {
      for (const value of group) {
        next.push([...prefix, value]);
      }
    }

    combinations = next;

    if (combinations.length === 0) {
      break;
    }
  }

  return combinations;
}

function cartesianSize(groups) {
  if (!Array.isArray(groups)) {
    throw new TypeError("groups must be an array.");
  }

  let size = 1;

  for (const group of groups) {
    if (!Array.isArray(group)) {
      throw new TypeError("Every Cartesian-product dimension must be an array.");
    }

    size *= group.length;

    if (group.length === 0) {
      return 0;
    }
  }

  return size;
}

function assertSafeCartesianSize(groups, maximumRows) {
  if (!Number.isSafeInteger(maximumRows) || maximumRows < 0) {
    throw new RangeError("maximumRows must be a non-negative safe integer.");
  }

  let size = 1;

  for (const group of groups) {
    if (group.length === 0) {
      return 0;
    }

    if (size > Math.floor(maximumRows / group.length)) {
      throw new RangeError(
        `Cartesian product exceeds the configured limit of ${maximumRows}.`
      );
    }

    size *= group.length;
  }

  return size;
}

function demoBasicCrossJoin() {
  printHeading("Basic Cartesian Product");

  const developers = ["Asha", "Ravi", "Maya"];
  const environments = ["staging", "production"];

  const combinations = crossJoin(developers, environments);

  console.log(`Developers: ${developers.length}`);
  console.log(`Environments: ${environments.length}`);
  console.log(`Rows: ${combinations.length}`);
  console.table(combinations);
}

function demoMultiDimensionProduct() {
  printHeading("Multiple Independent Dimensions");

  const repositories = ["payments", "customer-web"];
  const environments = ["staging", "production"];
  const testSuites = ["unit", "integration", "security"];

  const combinations = cartesianProduct([
    repositories,
    environments,
    testSuites,
  ]);

  console.log(
    `${repositories.length} × ${environments.length} × ${testSuites.length} = ` +
      `${combinations.length} combinations`
  );

  console.table(combinations);
}

function demoDuplicateRows() {
  printHeading("Duplicates Remain Significant");

  const teams = ["platform", "platform", "security"];
  const environments = ["staging", "production"];

  const combinations = crossJoin(teams, environments);

  console.table(combinations);
  console.log(
    "The repeated 'platform' input produces repeated output rows."
  );
}

function demoFilteringCandidates() {
  printHeading("Candidate Generation Followed by Policy Filtering");

  const roles = ["developer", "reviewer", "release-manager"];
  const repositories = ["api", "web"];

  const candidates = crossJoin(roles, repositories);

  const validAssignments = candidates.filter(([role, repository]) => {
    if (role === "release-manager" && repository === "web") {
      return false;
    }

    return true;
  });

  console.log(`Candidate combinations: ${candidates.length}`);
  console.log(`Valid combinations: ${validAssignments.length}`);
  console.table(validAssignments);
}

class CombinationEngine extends EventEmitter {
  constructor(maximumRows = 100_000) {
    super();

    if (!Number.isSafeInteger(maximumRows) || maximumRows <= 0) {
      throw new RangeError("maximumRows must be a positive safe integer.");
    }

    this.maximumRows = maximumRows;
  }

  evaluate(groups) {
    const size = assertSafeCartesianSize(groups, this.maximumRows);

    this.emit("estimated", {
      dimensions: groups.length,
      combinations: size,
    });

    return size;
  }

  *generate(groups) {
    this.evaluate(groups);

    yield* cartesianProductGenerator(groups);
  }
}

function* cartesianProductGenerator(groups, prefix = []) {
  if (groups.length === 0) {
    yield prefix;
    return;
  }

  const [first, ...remaining] = groups;

  for (const value of first) {
    yield* cartesianProductGenerator(remaining, [...prefix, value]);
  }
}

function demoEventDrivenEngine() {
  printHeading("Event-Driven Cartesian Product Governance");

  const engine = new CombinationEngine(1_000);

  engine.on("estimated", (event) => {
    console.log(
      `Estimated ${event.combinations} rows across ` +
        `${event.dimensions} dimensions.`
    );
  });

  const groups = [
    ["api", "web"],
    ["staging", "production"],
    ["unit", "integration"],
  ];

  let consumed = 0;

  for (const combination of engine.generate(groups)) {
    console.log(`Combination ${consumed + 1}: ${combination.join(" / ")}`);
    consumed += 1;
  }

  console.log(`Consumed ${consumed} combinations.`);
}

async function processCartesianProductInBatches(
  left,
  right,
  batchSize,
  processor
) {
  if (!Number.isInteger(batchSize) || batchSize <= 0) {
    throw new RangeError("batchSize must be positive.");
  }

  if (typeof processor !== "function") {
    throw new TypeError("processor must be a function.");
  }

  let batch = [];
  let processed = 0;

  for (const combination of crossJoinGenerator(left, right)) {
    batch.push(combination);

    if (batch.length === batchSize) {
      await processor(batch);
      processed += batch.length;
      batch = [];
    }
  }

  if (batch.length > 0) {
    await processor(batch);
    processed += batch.length;
  }

  return processed;
}

async function demoAsyncBatchProcessing() {
  printHeading("Asynchronous Batch Processing");

  const repositories = ["api", "web", "worker"];
  const environments = ["staging", "production"];

  const processed = await processCartesianProductInBatches(
    repositories,
    environments,
    2,
    async (batch) => {
      /*
       * A real application could persist, validate, or send each batch to a
       * service. The delay demonstrates an asynchronous processing boundary.
       */
      await new Promise((resolve) => setTimeout(resolve, 5));
      console.log(`Processed batch: ${JSON.stringify(batch)}`);
    }
  );

  console.log(`Total processed rows: ${processed}`);
}

function buildPermissionCandidates() {
  const roles = ["developer", "reviewer", "release-manager"];
  const repositories = ["payments-api", "customer-web"];
  const environments = ["staging", "production"];
  const permissions = ["read", "write", "deploy"];

  return cartesianProduct([
    roles,
    repositories,
    environments,
    permissions,
  ]).map(([role, repository, environment, permission]) => ({
    role,
    repository,
    environment,
    permission,
  }));
}

function enforcePermissionPolicy(candidates) {
  return candidates.filter((candidate) => {
    if (
      candidate.environment === "production" &&
      candidate.permission === "deploy" &&
      candidate.role !== "release-manager"
    ) {
      return false;
    }

    if (
      candidate.permission === "write" &&
      candidate.role === "reviewer"
    ) {
      return false;
    }

    return true;
  });
}

function demoSetBasedDeduplication() {
  printHeading("Deduplication Is Separate From CROSS JOIN");

  const left = ["platform", "platform", "security"];
  const right = ["staging", "production"];

  const raw = crossJoin(left, right);

  /*
   * CROSS JOIN itself does not perform DISTINCT. If the application needs
   * unique value combinations, deduplication must be explicit.
   */
  const unique = new Set(raw.map(([a, b]) => `${a}|${b}`));

  console.log(`Raw rows: ${raw.length}`);
  console.log(`Unique value pairs: ${unique.size}`);
  console.log([...unique]);
}

function demoRiskControls() {
  printHeading("Cardinality Risk Controls");

  const scenarios = [
    {
      name: "small",
      groups: [
        Array.from({ length: 10 }, (_, i) => i),
        Array.from({ length: 20 }, (_, i) => i),
      ],
    },
    {
      name: "large",
      groups: [
        Array.from({ length: 1_000 }, (_, i) => i),
        Array.from({ length: 1_000 }, (_, i) => i),
        Array.from({ length: 100 }, (_, i) => i),
      ],
    },
  ];

  for (const scenario of scenarios) {
    try {
      const size = assertSafeCartesianSize(scenario.groups, 5_000_000);
      console.log(`${scenario.name}: ${size.toLocaleString()} rows`);
    } catch (error) {
      console.log(`${scenario.name}: REJECTED -> ${error.message}`);
    }
  }
}

function demoEmptyInput() {
  printHeading("Empty Input Semantics");

  const result = crossJoin(["a", "b"], []);

  console.log(`Rows produced: ${result.length}`);
  console.log("A zero-cardinality dimension collapses the Cartesian result.");
}

function runAssertions() {
  printHeading("Validation");

  const basic = crossJoin([1, 2], ["x", "y"]);

  console.assert(
    JSON.stringify(basic) ===
      JSON.stringify([
        [1, "x"],
        [1, "y"],
        [2, "x"],
        [2, "y"],
      ]),
    "Basic Cartesian product failed."
  );

  console.assert(
    cartesianSize([[1, 2], ["a", "b"], [true, false]]) === 8,
    "Cardinality calculation failed."
  );

  console.assert(
    cartesianSize([[], [1, 2]]) === 0,
    "Empty dimension behavior failed."
  );

  try {
    assertSafeCartesianSize(
      [Array.from({ length: 100 }, () => 1), Array.from({ length: 100 }, () => 1)],
      500
    );
    throw new Error("Oversized product was not rejected.");
  } catch (error) {
    console.log("Oversized product validation passed.");
  }

  console.log("Assertions completed.");
}

async function main() {
  printHeading("CROSS JOIN Technical Demonstration");

  demoBasicCrossJoin();
  demoMultiDimensionProduct();
  demoDuplicateRows();
  demoFilteringCandidates();
  demoEventDrivenEngine();
  await demoAsyncBatchProcessing();

  const candidates = buildPermissionCandidates();
  const valid = enforcePermissionPolicy(candidates);

  printHeading("Permission Matrix");
  console.log(`Raw candidates: ${candidates.length}`);
  console.log(`Policy-compliant candidates: ${valid.length}`);
  console.table(valid.slice(0, 15));

  demoSetBasedDeduplication();
  demoRiskControls();
  demoEmptyInput();
  runAssertions();

  printHeading("Operational Principle");
  console.log(
    "A CROSS JOIN deliberately constructs every combination. " +
      "Estimate its cardinality before materializing it, then use filtering, " +
      "streaming, batching, or explicit limits when the candidate space is large."
  );
}

main().catch((error) => {
  console.error(`Fatal error: ${error.message}`);
  process.exitCode = 1;
});
