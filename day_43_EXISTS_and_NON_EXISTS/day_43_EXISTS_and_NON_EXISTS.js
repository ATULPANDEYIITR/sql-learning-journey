"use strict";

/*
 * EXISTS, NOT EXISTS, semi-joins, anti-joins, and existence checks.
 *
 * Run with Node.js 18 or later:
 *     node existence_queries.js
 *
 * This implementation uses an event-driven repository workflow model.
 * It complements relational SQL by showing how existence predicates can
 * be represented in memory, applied to asynchronous data sources, and
 * protected against concurrent state changes.
 */

const { performance } = require("node:perf_hooks");

const developers = [
  { id: 1, name: "Asha", active: true, team: "Platform" },
  { id: 2, name: "Ravi", active: true, team: "Platform" },
  { id: 3, name: "Meera", active: true, team: "Security" },
  { id: 4, name: "Kabir", active: true, team: "Quality" },
  { id: 5, name: "InactiveReviewer", active: false, team: "Platform" }
];

const pullRequests = [
  {
    id: 101,
    repository: "deployment-service",
    authorId: 1,
    title: "Improve deployment retries",
    state: "open",
    draft: false,
    baseVersion: 7
  },
  {
    id: 102,
    repository: "deployment-service",
    authorId: 2,
    title: "Add rollback support",
    state: "open",
    draft: false,
    baseVersion: 7
  },
  {
    id: 103,
    repository: "deployment-service",
    authorId: 1,
    title: "Draft health endpoint",
    state: "open",
    draft: true,
    baseVersion: 7
  },
  {
    id: 201,
    repository: "security-scanner",
    authorId: 3,
    title: "Fix scanner validation",
    state: "open",
    draft: false,
    baseVersion: 4
  }
];

const reviews = [
  { id: 1, pullRequestId: 101, reviewerId: 2, state: "approved", version: 7 },
  { id: 2, pullRequestId: 101, reviewerId: 3, state: "commented", version: 7 },
  { id: 3, pullRequestId: 102, reviewerId: 3, state: "changes_requested", version: 7 },
  { id: 4, pullRequestId: 102, reviewerId: 4, state: "approved", version: 7 },
  { id: 5, pullRequestId: 201, reviewerId: 4, state: "approved", version: 4 },
  { id: 6, pullRequestId: 201, reviewerId: 5, state: "approved", version: 4 }
];

const checkResults = [
  { pullRequestId: 101, name: "unit-tests", state: "success" },
  { pullRequestId: 101, name: "security-scan", state: "success" },
  { pullRequestId: 102, name: "unit-tests", state: "success" },
  { pullRequestId: 102, name: "security-scan", state: "failure" },
  { pullRequestId: 201, name: "unit-tests", state: "success" }
];

const requiredChecks = new Map([
  ["deployment-service", ["unit-tests", "security-scan"]],
  ["security-scanner", ["unit-tests"]]
]);

function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function printRows(title, rows) {
  console.log(`\n--- ${title} ---`);
  if (rows.length === 0) {
    console.log("(no rows)");
    return;
  }
  for (const row of rows) {
    console.log(JSON.stringify(row));
  }
}

/*
 * Array.some() implements an existential quantifier:
 * it answers whether at least one element satisfies a predicate.
 * It short-circuits when a match is found.
 */
function exists(items, predicate) {
  return items.some(predicate);
}

/*
 * NOT EXISTS is the logical negation of existence.
 * It is true when no item satisfies the predicate.
 */
function notExists(items, predicate) {
  return !items.some(predicate);
}

/*
 * A semi-join retains outer records with at least one matching inner record.
 * It does not append inner records or duplicate the outer record.
 */
function semiJoin(outerRows, innerRows, matches) {
  return outerRows.filter(outer =>
    exists(innerRows, inner => matches(outer, inner))
  );
}

/*
 * An anti-join retains outer records with no matching inner record.
 * It is useful for finding missing approvals, missing assignments,
 * unresolved dependencies, and records without matching events.
 */
function antiJoin(outerRows, innerRows, matches) {
  return outerRows.filter(outer =>
    notExists(innerRows, inner => matches(outer, inner))
  );
}

/*
 * A regular join emits matching pairs. Multiple inner matches multiply
 * output rows, unlike a semi-join.
 */
function innerJoin(outerRows, innerRows, matches) {
  const output = [];
  for (const outer of outerRows) {
    for (const inner of innerRows) {
      if (matches(outer, inner)) {
        output.push({ outer, inner });
      }
    }
  }
  return output;
}

function getDeveloper(developerId) {
  return developers.find(developer => developer.id === developerId);
}

function approvedByActiveReviewer(pullRequest) {
  return exists(
    reviews,
    review =>
      review.pullRequestId === pullRequest.id &&
      review.state === "approved" &&
      getDeveloper(review.reviewerId)?.active === true &&
      review.version === pullRequest.baseVersion
  );
}

function hasPassingRequiredChecks(pullRequest) {
  const required = requiredChecks.get(pullRequest.repository) ?? [];

  /*
   * A nested anti-join detects a required check for which no successful
   * result exists. Missing results are failures, not implicit successes.
   */
  const missingOrFailed = antiJoin(
    required,
    checkResults.filter(
      check => check.pullRequestId === pullRequest.id
    ),
    (requiredName, actual) =>
      requiredName === actual.name && actual.state === "success"
  );

  return missingOrFailed.length === 0 && required.length > 0;
}

function isMergeEligible(pullRequest, minimumApprovals = 1) {
  if (!Number.isInteger(minimumApprovals) || minimumApprovals < 1) {
    throw new RangeError("minimumApprovals must be a positive integer");
  }

  if (pullRequest.state !== "open" || pullRequest.draft) {
    return false;
  }

  const eligibleReviewers = new Set(
    reviews
      .filter(review =>
        review.pullRequestId === pullRequest.id &&
        review.state === "approved" &&
        review.version === pullRequest.baseVersion &&
        getDeveloper(review.reviewerId)?.active === true
      )
      .map(review => review.reviewerId)
  );

  return eligibleReviewers.size >= minimumApprovals &&
    hasPassingRequiredChecks(pullRequest);
}

/*
 * Event-driven state updates make policy re-evaluation explicit.
 * An event is validated before it mutates the model.
 */
class RepositoryWorkflow extends EventTarget {
  constructor(requests) {
    super();
    this.requests = new Map(requests.map(request => [
      request.id,
      { ...request }
    ]));
    this.revision = 0;
  }

  getPullRequest(id) {
    const request = this.requests.get(id);
    return request ? { ...request } : null;
  }

  closePullRequest(id) {
    const request = this.requests.get(id);
    if (!request) {
      throw new Error(`Pull request ${id} does not exist`);
    }
    if (request.state !== "open") {
      throw new Error(`Cannot close a request in state ${request.state}`);
    }

    request.state = "closed";
    this.revision += 1;

    this.dispatchEvent(new CustomEvent("pull-request-changed", {
      detail: {
        id,
        state: request.state,
        revision: this.revision
      }
    }));

    return this.getPullRequest(id);
  }

  mergePullRequest(id, expectedRevision) {
    /*
     * The revision check prevents a stale client from merging based on
     * an earlier snapshot. A production server must enforce the same
     * rule atomically in persistent storage.
     */
    if (expectedRevision !== this.revision) {
      throw new Error("Repository state changed; refresh and retry");
    }

    const request = this.requests.get(id);
    if (!request) {
      throw new Error(`Pull request ${id} does not exist`);
    }
    if (!isMergeEligible(request)) {
      throw new Error(`Pull request ${id} is not merge-eligible`);
    }

    request.state = "merged";
    this.revision += 1;

    this.dispatchEvent(new CustomEvent("pull-request-changed", {
      detail: {
        id,
        state: request.state,
        revision: this.revision
      }
    }));

    return this.getPullRequest(id);
  }
}

/*
 * An asynchronous repository interface may query a remote service.
 * The in-memory adapter below is deterministic and requires no package.
 */
class ReviewRepository {
  constructor(records) {
    this.records = records;
  }

  async existsFor(pullRequestId, predicate) {
    await Promise.resolve();
    return exists(
      this.records,
      record =>
        record.pullRequestId === pullRequestId && predicate(record)
    );
  }

  async listFor(pullRequestId) {
    await Promise.resolve();
    return this.records.filter(
      record => record.pullRequestId === pullRequestId
    );
  }
}

async function demonstrateAsynchronousExistence() {
  const repository = new ReviewRepository(reviews);

  const results = await Promise.all(
    pullRequests.map(async request => ({
      pullRequestId: request.id,
      hasApproval: await repository.existsFor(
        request.id,
        review => review.state === "approved"
      )
    }))
  );

  printRows("Asynchronous review existence", results);
}

function demonstrateNullAndMissingValues() {
  /*
   * JavaScript's strict equality differs from SQL's three-valued logic.
   * Array.some() treats null as an ordinary value, so SQL NULL behavior
   * must be modeled explicitly when translating database predicates.
   */
  const candidates = [2, null];
  const reviewerId = 4;

  const javascriptNotExists = !candidates.some(
    candidate => candidate === reviewerId
  );

  const sqlNotInWouldBeUnknown =
    !candidates.includes(reviewerId) && !candidates.includes(null);

  console.log("\nNULL and missing-value behavior:");
  console.log({ javascriptNotExists, sqlNotInWouldBeUnknown });
}

function benchmarkExistenceStrategies() {
  const generatedRequests = Array.from({ length: 2000 }, (_, index) => ({
    id: index + 1
  }));

  const generatedReviews = Array.from({ length: 4000 }, (_, index) => ({
    pullRequestId: (index % 2000) + 1,
    state: index % 4 === 0 ? "approved" : "commented"
  }));

  const started = performance.now();
  const naive = semiJoin(
    generatedRequests,
    generatedReviews,
    (request, review) =>
      request.id === review.pullRequestId &&
      review.state === "approved"
  );
  const naiveDuration = performance.now() - started;

  /*
   * Index the inner relation by key. The indexed form avoids scanning every
   * review for every request, at the cost of building and storing the map.
   */
  const index = new Map();
  for (const review of generatedReviews) {
    if (review.state !== "approved") continue;
    if (!index.has(review.pullRequestId)) {
      index.set(review.pullRequestId, true);
    }
  }

  const indexedStart = performance.now();
  const indexed = generatedRequests.filter(request =>
    index.has(request.id)
  );
  const indexedDuration = performance.now() - indexedStart;

  assert(
    JSON.stringify(naive.map(row => row.id)) ===
      JSON.stringify(indexed.map(row => row.id)),
    "indexed and scan-based semi-joins must agree"
  );

  console.log("\nExistence strategy benchmark:");
  console.log({
    requestCount: generatedRequests.length,
    reviewCount: generatedReviews.length,
    matches: indexed.length,
    naiveMilliseconds: Number(naiveDuration.toFixed(2)),
    indexedMilliseconds: Number(indexedDuration.toFixed(2))
  });
}

function runTests() {
  const approvedOpen = semiJoin(
    pullRequests,
    reviews,
    (request, review) =>
      request.id === review.pullRequestId &&
      request.state === "open" &&
      review.state === "approved"
  );

  assert(
    approvedOpen.map(row => row.id).join(",") === "101,102,201",
    "semi-join should return each qualifying request once"
  );

  const noApproval = antiJoin(
    pullRequests.filter(request => request.state === "open"),
    reviews,
    (request, review) =>
      request.id === review.pullRequestId &&
      review.state === "approved"
  );

  assert(
    noApproval.map(row => row.id).join(",") === "103",
    "anti-join should identify requests without approvals"
  );

  const joined = innerJoin(
    pullRequests.filter(request => request.id === 101),
    reviews,
    (request, review) => request.id === review.pullRequestId
  );

  assert(joined.length === 2, "join should preserve matching pairs");

  const workflow = new RepositoryWorkflow(pullRequests);
  let receivedEvent = false;

  workflow.addEventListener("pull-request-changed", event => {
    receivedEvent = true;
    console.log("Workflow event:", event.detail);
  });

  workflow.closePullRequest(103);
  assert(receivedEvent, "state transition should dispatch an event");

  let invalidTransitionRejected = false;
  try {
    workflow.closePullRequest(103);
  } catch {
    invalidTransitionRejected = true;
  }

  assert(
    invalidTransitionRejected,
    "closing an already closed request must fail"
  );

  let invalidThresholdRejected = false;
  try {
    isMergeEligible(pullRequests[0], 0);
  } catch {
    invalidThresholdRejected = true;
  }

  assert(
    invalidThresholdRejected,
    "invalid approval thresholds must fail validation"
  );

  console.log("\nAll JavaScript assertions passed.");
}

async function main() {
  printRows(
    "Open pull requests with at least one approval",
    semiJoin(
      pullRequests,
      reviews,
      (request, review) =>
        request.id === review.pullRequestId &&
        request.state === "open" &&
        review.state === "approved"
    )
  );

  printRows(
    "Open pull requests without an approval",
    antiJoin(
      pullRequests.filter(request => request.state === "open"),
      reviews,
      (request, review) =>
        request.id === review.pullRequestId &&
        review.state === "approved"
    )
  );

  printRows(
    "Ordinary join with one row per matching review",
    innerJoin(
      pullRequests,
      reviews,
      (request, review) =>
        request.id === review.pullRequestId &&
        review.state === "approved"
    ).map(pair => ({
      pullRequestId: pair.outer.id,
      reviewerId: pair.inner.reviewerId
    }))
  );

  printRows(
    "Merge eligibility",
    pullRequests.map(request => ({
      pullRequestId: request.id,
      eligible: isMergeEligible(request)
    }))
  );

  await demonstrateAsynchronousExistence();
  demonstrateNullAndMissingValues();
  runTests();
  benchmarkExistenceStrategies();
}

main().catch(error => {
  console.error("Workflow demonstration failed:", error.message);
  process.exitCode = 1;
});
