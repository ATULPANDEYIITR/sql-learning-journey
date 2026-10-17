"use strict";

/*
 * Advanced aggregation model for repository analytics.
 *
 * The implementation uses an event-driven Node.js style rather than
 * translating the Python data-processing flow. It demonstrates multiple
 * aggregates, conditional aggregates, incremental aggregation, strategy
 * selection, and policy evaluation.
 */

const transactions = [
  { id: 1001, repository: "platform-api", team: "Core", category: "feature", additions: 420, deletions: 90, state: "merged", reviewerCount: 2, approvalCount: 2, checksPassed: true },
  { id: 1002, repository: "platform-api", team: "Core", category: "bugfix", additions: 80, deletions: 40, state: "merged", reviewerCount: 1, approvalCount: 1, checksPassed: true },
  { id: 1003, repository: "identity-service", team: "Security", category: "security", additions: 260, deletions: 30, state: "merged", reviewerCount: 3, approvalCount: 3, checksPassed: true },
  { id: 1004, repository: "identity-service", team: "Security", category: "bugfix", additions: 120, deletions: 70, state: "open", reviewerCount: 2, approvalCount: 1, checksPassed: true },
  { id: 1005, repository: "data-pipeline", team: "Data", category: "feature", additions: 760, deletions: 210, state: "merged", reviewerCount: 3, approvalCount: 2, checksPassed: true },
  { id: 1006, repository: "data-pipeline", team: "Data", category: "performance", additions: 310, deletions: 190, state: "merged", reviewerCount: 2, approvalCount: 2, checksPassed: true },
  { id: 1007, repository: "platform-api", team: "Core", category: "feature", additions: 900, deletions: 420, state: "open", reviewerCount: 4, approvalCount: 2, checksPassed: false },
  { id: 1008, repository: "identity-service", team: "Security", category: "security", additions: 180, deletions: 20, state: "merged", reviewerCount: 3, approvalCount: 3, checksPassed: true },
  { id: 1009, repository: "data-pipeline", team: "Data", category: "bugfix", additions: 95, deletions: 60, state: "closed", reviewerCount: 1, approvalCount: 0, checksPassed: false },
  { id: 1010, repository: "platform-api", team: "Core", category: "performance", additions: 500, deletions: 150, state: "merged", reviewerCount: 2, approvalCount: 2, checksPassed: true }
];

function validatePullRequestChange(change) {
  if (!Number.isInteger(change.id) || change.id <= 0) {
    throw new Error(`Invalid change identifier: ${change.id}`);
  }

  if (change.additions < 0 || change.deletions < 0) {
    throw new Error(`Negative line counts are invalid for ${change.id}`);
  }

  if (!["merged", "open", "closed"].includes(change.state)) {
    throw new Error(`Unsupported state: ${change.state}`);
  }

  if (change.approvalCount > change.reviewerCount) {
    throw new Error(`Approvals exceed reviewers for ${change.id}`);
  }

  return change;
}

function createAggregate() {
  return {
    count: 0,
    additions: 0,
    deletions: 0,
    merged: 0,
    open: 0,
    closed: 0,
    approved: 0,
    checksPassed: 0,
    reviewCoverageTotal: 0
  };
}

function updateAggregate(aggregate, change) {
  aggregate.count += 1;
  aggregate.additions += change.additions;
  aggregate.deletions += change.deletions;

  if (change.state === "merged") aggregate.merged += 1;
  if (change.state === "open") aggregate.open += 1;
  if (change.state === "closed") aggregate.closed += 1;

  if (change.approvalCount >= 2) aggregate.approved += 1;
  if (change.checksPassed) aggregate.checksPassed += 1;

  aggregate.reviewCoverageTotal +=
    change.reviewerCount === 0
      ? 0
      : change.approvalCount / change.reviewerCount;
}

function finalizeAggregate(aggregate) {
  if (aggregate.count === 0) {
    return {
      ...aggregate,
      averageChangeSize: 0,
      mergeRate: 0,
      approvalCoverage: 0
    };
  }

  return {
    ...aggregate,
    averageChangeSize:
      (aggregate.additions + aggregate.deletions) / aggregate.count,
    mergeRate: aggregate.merged / aggregate.count,
    approvalCoverage:
      aggregate.reviewCoverageTotal / aggregate.count
  };
}

function aggregateBy(keySelector) {
  const grouped = new Map();

  for (const change of transactions) {
    const key = keySelector(change);

    if (!grouped.has(key)) {
      grouped.set(key, createAggregate());
    }

    updateAggregate(grouped.get(key), change);
  }

  return new Map(
    [...grouped.entries()].map(([key, aggregate]) => [
      key,
      finalizeAggregate(aggregate)
    ])
  );
}

function conditionalAggregation(changes) {
  const result = {
    total: 0,
    securityChanges: 0,
    largeChanges: 0,
    mergedWithPassedChecks: 0,
    openWithoutEnoughApprovals: 0,
    failedChecks: 0
  };

  for (const change of changes) {
    result.total += 1;

    if (change.category === "security") {
      result.securityChanges += 1;
    }

    if (change.additions + change.deletions >= 500) {
      result.largeChanges += 1;
    }

    if (change.state === "merged" && change.checksPassed) {
      result.mergedWithPassedChecks += 1;
    }

    if (change.state === "open" && change.approvalCount < 2) {
      result.openWithoutEnoughApprovals += 1;
    }

    if (!change.checksPassed) {
      result.failedChecks += 1;
    }
  }

  return result;
}

function categoryMetrics(changes) {
  const result = new Map();

  for (const change of changes) {
    if (!result.has(change.category)) {
      result.set(change.category, {
        count: 0,
        merged: 0,
        additions: 0,
        deletions: 0,
        failedChecks: 0
      });
    }

    const metric = result.get(change.category);

    metric.count += 1;
    metric.additions += change.additions;
    metric.deletions += change.deletions;

    if (change.state === "merged") metric.merged += 1;
    if (!change.checksPassed) metric.failedChecks += 1;
  }

  return result;
}

class AggregationEngine {
  constructor(records) {
    this.records = records.map(validatePullRequestChange);
  }

  groupByRepository() {
    return aggregateBy(change => change.repository);
  }

  groupByTeam() {
    return aggregateBy(change => change.team);
  }

  conditional() {
    return conditionalAggregation(this.records);
  }

  categoryMetrics() {
    return categoryMetrics(this.records);
  }

  evaluatePolicy(policy) {
    const metrics = this.groupByRepository();
    const decisions = [];

    for (const [repository, aggregate] of metrics) {
      const eligible =
        aggregate.merged >= policy.minimumMerged &&
        aggregate.approvalCoverage >= policy.minimumApprovalCoverage &&
        aggregate.checksPassed / aggregate.count >= policy.minimumCheckPassRate;

      decisions.push({
        repository,
        eligible,
        reason: eligible
          ? "Repository meets aggregate governance thresholds"
          : "Repository does not meet aggregate governance thresholds"
      });
    }

    return decisions;
  }
}

function printMap(title, map) {
  console.log(`\n${title}`);
  console.log("-".repeat(title.length));

  for (const [key, value] of map) {
    console.log(key, value);
  }
}

async function processEvents(engine) {
  /*
   * Event-driven processing demonstrates that aggregation does not have to
   * wait for a complete batch. A live service can maintain incremental
   * metrics as events arrive.
   */
  const live = new Map();

  for (const record of engine.records) {
    await Promise.resolve();

    const key = record.repository;

    if (!live.has(key)) {
      live.set(key, createAggregate());
    }

    updateAggregate(live.get(key), record);
  }

  return new Map(
    [...live.entries()].map(([key, aggregate]) => [
      key,
      finalizeAggregate(aggregate)
    ])
  );
}

async function main() {
  const engine = new AggregationEngine(transactions);

  printMap("Repository Aggregation", engine.groupByRepository());
  printMap("Team Aggregation", engine.groupByTeam());
  printMap("Category Metrics", engine.categoryMetrics());

  console.log("\nConditional Aggregation");
  console.log("-----------------------");
  console.table(engine.conditional());

  console.log("\nGovernance Evaluation");
  console.log("---------------------");

  const policy = {
    minimumMerged: 2,
    minimumApprovalCoverage: 0.75,
    minimumCheckPassRate: 0.80
  };

  console.table(engine.evaluatePolicy(policy));

  const liveMetrics = await processEvents(engine);

  console.log("\nIncremental Event Aggregation");
  console.log("-----------------------------");
  console.table([...liveMetrics.entries()].map(([repository, metrics]) => ({
    repository,
    count: metrics.count,
    merged: metrics.merged,
    averageChangeSize: metrics.averageChangeSize.toFixed(2),
    approvalCoverage: metrics.approvalCoverage.toFixed(2)
  })));

  /*
   * Strategy selection is based on workload characteristics. A Map provides
   * expected O(1) grouping updates, while sorting is preferable when a
   * downstream operation requires ordered grouped records.
   */
  const strategy =
    engine.records.length > 100000
      ? "Hash aggregation with partitioning"
      : "In-memory Map aggregation with incremental accumulators";

  console.log("\nSelected aggregation strategy:");
  console.log(strategy);
}

main().catch(error => {
  console.error("Aggregation failed:", error.message);
  process.exitCode = 1;
});
