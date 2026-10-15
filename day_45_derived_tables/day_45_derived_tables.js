/*
 * Derived Tables: subqueries in FROM and intermediate result sets
 *
 * This file models relational derived-table behavior using JavaScript
 * transformations. The implementation deliberately uses JavaScript-specific
 * Map, Set, higher-order functions, object composition, and event-style
 * processing rather than translating the Python program line by line.
 *
 * Runtime: Node.js 18+
 */

"use strict";

const pullRequests = [
  {
    id: 101,
    repository: "payment-platform",
    sourceBranch: "feature/checkout-validation",
    targetBranch: "main",
    author: "atul",
    additions: 340,
    deletions: 90,
    state: "OPEN"
  },
  {
    id: 102,
    repository: "payment-platform",
    sourceBranch: "fix/token-expiry",
    targetBranch: "main",
    author: "neha",
    additions: 80,
    deletions: 25,
    state: "OPEN"
  },
  {
    id: 103,
    repository: "payment-platform",
    sourceBranch: "release/2026-10",
    targetBranch: "release",
    author: "rahul",
    additions: 510,
    deletions: 180,
    state: "OPEN"
  },
  {
    id: 104,
    repository: "identity-service",
    sourceBranch: "feature/session-hardening",
    targetBranch: "main",
    author: "meera",
    additions: 210,
    deletions: 60,
    state: "OPEN"
  }
];

const reviews = [
  { id: 1, prId: 101, reviewer: "neha", state: "APPROVED" },
  { id: 2, prId: 101, reviewer: "rahul", state: "APPROVED" },
  { id: 3, prId: 102, reviewer: "meera", state: "APPROVED" },
  { id: 4, prId: 103, reviewer: "neha", state: "APPROVED" },
  { id: 5, prId: 103, reviewer: "vikas", state: "CHANGES_REQUESTED" },
  { id: 6, prId: 104, reviewer: "rahul", state: "APPROVED" }
];

const statusChecks = [
  { prId: 101, name: "unit-tests", state: "SUCCESS" },
  { prId: 101, name: "security-scan", state: "SUCCESS" },
  { prId: 102, name: "unit-tests", state: "SUCCESS" },
  { prId: 102, name: "security-scan", state: "FAILURE" },
  { prId: 103, name: "unit-tests", state: "SUCCESS" },
  { prId: 103, name: "security-scan", state: "SUCCESS" },
  { prId: 104, name: "unit-tests", state: "SUCCESS" },
  { prId: 104, name: "security-scan", state: "SUCCESS" }
];

const policies = [
  {
    repository: "payment-platform",
    branch: "main",
    requiredApprovals: 2,
    requiredChecks: new Set(["unit-tests", "security-scan"])
  },
  {
    repository: "payment-platform",
    branch: "release",
    requiredApprovals: 2,
    requiredChecks: new Set(["unit-tests", "security-scan"])
  },
  {
    repository: "identity-service",
    branch: "main",
    requiredApprovals: 2,
    requiredChecks: new Set(["unit-tests", "security-scan"])
  }
];

/*
 * A derived table is represented by an array of newly shaped objects.
 * The source array remains untouched, which is analogous to a SQL FROM
 * subquery producing a logical relation for the outer query.
 */
function derive(rows, projection) {
  return rows.map(projection);
}

function filterDerived(rows, predicate) {
  return rows.filter(predicate);
}

function groupBy(rows, keySelector) {
  const groups = new Map();

  for (const row of rows) {
    const key = keySelector(row);

    if (!groups.has(key)) {
      groups.set(key, []);
    }

    groups.get(key).push(row);
  }

  return groups;
}

function countGroups(groups, propertyName) {
  return [...groups.entries()].map(([key, rows]) => ({
    [propertyName]: key,
    rowCount: rows.length
  }));
}

function joinDerived(leftRows, rightRows, leftKey, rightKey) {
  const rightIndex = new Map();

  for (const row of rightRows) {
    const key = row[rightKey];

    if (!rightIndex.has(key)) {
      rightIndex.set(key, []);
    }

    rightIndex.get(key).push(row);
  }

  const result = [];

  for (const left of leftRows) {
    const matches = rightIndex.get(left[leftKey]) ?? [];

    for (const right of matches) {
      result.push({
        ...left,
        ...Object.fromEntries(
          Object.entries(right).map(([key, value]) => [
            Object.hasOwn(left, key) ? `right_${key}` : key,
            value
          ])
        )
      });
    }
  }

  return result;
}

function demonstrateChangeMetrics() {
  console.log("\n=== Change metrics derived table ===");

  const metrics = derive(pullRequests, pr => ({
    prId: pr.id,
    repository: pr.repository,
    targetBranch: pr.targetBranch,
    changeSize: pr.additions + pr.deletions,
    churnRatio:
      pr.additions + pr.deletions === 0
        ? 0
        : pr.deletions / (pr.additions + pr.deletions)
  }));

  const highChurnChanges = filterDerived(
    metrics,
    row => row.churnRatio >= 0.25 && row.changeSize >= 100
  );

  console.table(highChurnChanges);
}

function demonstrateNestedRelations() {
  console.log("\n=== Nested derived relations ===");

  const changeMetrics = derive(pullRequests, pr => ({
    prId: pr.id,
    repository: pr.repository,
    totalChange: pr.additions + pr.deletions
  }));

  const largeChanges = filterDerived(
    changeMetrics,
    row => row.totalChange >= 200
  );

  const repositorySummary = countGroups(
    groupBy(largeChanges, row => row.repository),
    "repository"
  );

  console.table(repositorySummary);
}

function demonstrateAggregation() {
  console.log("\n=== Aggregation over an intermediate result ===");

  const metrics = derive(pullRequests, pr => ({
    repository: pr.repository,
    changeSize: pr.additions + pr.deletions
  }));

  const grouped = groupBy(metrics, row => row.repository);

  const summary = [...grouped.entries()].map(([repository, rows]) => {
    const sizes = rows.map(row => row.changeSize);

    return {
      repository,
      averageChange: sizes.reduce((sum, value) => sum + value, 0) / sizes.length,
      maximumChange: Math.max(...sizes)
    };
  });

  console.table(summary);
}

function buildApprovalRelation() {
  /*
   * Review-level rows are reduced to approval facts. This is deliberately
   * separate from the Pull Request relation because the outer calculation
   * should consume an already-derived approval result.
   */
  const approvedReviews = filterDerived(
    reviews,
    review => review.state === "APPROVED"
  );

  const reviewerSets = new Map();

  for (const review of approvedReviews) {
    if (!reviewerSets.has(review.prId)) {
      reviewerSets.set(review.prId, new Set());
    }

    reviewerSets.get(review.prId).add(review.reviewer);
  }

  return [...reviewerSets.entries()].map(([prId, reviewers]) => ({
    prId,
    approvalCount: reviewers.size
  }));
}

function buildPassingCheckRelation() {
  const successfulChecks = filterDerived(
    statusChecks,
    check => check.state === "SUCCESS"
  );

  const checkSets = new Map();

  for (const check of successfulChecks) {
    if (!checkSets.has(check.prId)) {
      checkSets.set(check.prId, new Set());
    }

    checkSets.get(check.prId).add(check.name);
  }

  return [...checkSets.entries()].map(([prId, checks]) => ({
    prId,
    passingChecks: checks
  }));
}

function evaluateMergePolicy() {
  console.log("\n=== Policy evaluation from derived relations ===");

  const prRelation = derive(pullRequests, pr => ({
    prId: pr.id,
    repository: pr.repository,
    targetBranch: pr.targetBranch,
    state: pr.state
  }));

  const approvalRelation = buildApprovalRelation();
  const checkRelation = buildPassingCheckRelation();

  const policyRelation = derive(policies, policy => ({
    repository: policy.repository,
    branch: policy.branch,
    requiredApprovals: policy.requiredApprovals,
    requiredChecks: policy.requiredChecks
  }));

  /*
   * A normal join only compares the branch in this helper, so the repository
   * identity is checked explicitly afterward. This makes composite business
   * identity visible rather than hiding it in an overly generic helper.
   */
  const branchMatches = joinDerived(
    prRelation,
    policyRelation,
    "targetBranch",
    "branch"
  );

  const repositoryMatches = branchMatches.filter(
    row => row.repository === row.right_repository
  );

  const withApprovals = joinDerived(
    repositoryMatches,
    approvalRelation,
    "prId",
    "prId"
  );

  const withChecks = joinDerived(
    withApprovals,
    checkRelation,
    "prId",
    "prId"
  );

  const decisions = withChecks.map(row => {
    const passingChecks = row.passingChecks ?? new Set();

    const checksSatisfied = [...row.requiredChecks].every(
      required => passingChecks.has(required)
    );

    const approvalsSatisfied =
      row.approvalCount >= row.requiredApprovals;

    return {
      prId: row.prId,
      repository: row.repository,
      targetBranch: row.targetBranch,
      approvalCount: row.approvalCount,
      requiredApprovals: row.requiredApprovals,
      checksSatisfied,
      approvalsSatisfied,
      mergeEligible:
        row.state === "OPEN" &&
        approvalsSatisfied &&
        checksSatisfied
    };
  });

  console.table(decisions);
}

function demonstrateAsyncDerivedProcessing() {
  console.log("\n=== Event-driven derived processing ===");

  const events = [
    { type: "REVIEW", prId: 101, state: "APPROVED" },
    { type: "CHECK", prId: 101, state: "SUCCESS" },
    { type: "REVIEW", prId: 102, state: "CHANGES_REQUESTED" },
    { type: "CHECK", prId: 102, state: "FAILURE" }
  ];

  return Promise.resolve(events)
    .then(eventRows =>
      derive(eventRows, event => ({
        prId: event.prId,
        category: event.type,
        successful:
          event.state === "APPROVED" || event.state === "SUCCESS"
      }))
    )
    .then(intermediate =>
      filterDerived(intermediate, row => row.successful)
    )
    .then(successfulEvents => {
      console.table(successfulEvents);
      return successfulEvents;
    });
}

function demonstrateEdgeCases() {
  console.log("\n=== Edge cases ===");

  const emptyDerived = derive([], row => row);
  console.log("Empty derived relation:", emptyDerived);

  const zeroChange = derive(
    [{ additions: 0, deletions: 0 }],
    row => ({
      changeSize: row.additions + row.deletions
    })
  );

  console.log("Zero-change row:", zeroChange);

  const missingApprovalRelation = filterDerived(
    reviews,
    review => review.prId === 999
  );

  console.log(
    "PR with no review rows:",
    missingApprovalRelation
  );

  /*
   * Nullish coalescing prevents an absent derived relation from being treated
   * as an exceptional condition. In a database design, this corresponds to
   * deciding whether an outer join or an inner join is appropriate.
   */
  const approvalCount = missingApprovalRelation.length ?? 0;
  console.log("Safe count:", approvalCount);
}

async function main() {
  demonstrateChangeMetrics();
  demonstrateNestedRelations();
  demonstrateAggregation();
  evaluateMergePolicy();
  demonstrateEdgeCases();
  await demonstrateAsyncDerivedProcessing();
}

main().catch(error => {
  console.error("Derived-table processing failed:", error);
  process.exitCode = 1;
});
