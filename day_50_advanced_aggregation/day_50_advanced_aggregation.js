"use strict";

const pullRequests = [
  {
    number: 101, repository: "payments-api", author: "alice",
    targetBranch: "main", status: "merged", additions: 420, deletions: 80,
    commits: 6, reviews: 3, approvals: 2, requestedChanges: 0,
    merged: true, mergeStrategy: "squash",
    openedAt: "2026-10-01T09:00:00Z", mergedAt: "2026-10-02T14:00:00Z",
    checksPassed: true
  },
  {
    number: 102, repository: "payments-api", author: "bob",
    targetBranch: "main", status: "merged", additions: 90, deletions: 20,
    commits: 3, reviews: 2, approvals: 1, requestedChanges: 0,
    merged: true, mergeStrategy: "merge",
    openedAt: "2026-10-02T10:00:00Z", mergedAt: "2026-10-02T17:00:00Z",
    checksPassed: true
  },
  {
    number: 103, repository: "payments-api", author: "carol",
    targetBranch: "release", status: "closed", additions: 700, deletions: 300,
    commits: 12, reviews: 4, approvals: 0, requestedChanges: 2,
    merged: false, mergeStrategy: "none",
    openedAt: "2026-10-03T08:00:00Z", mergedAt: null,
    checksPassed: false
  },
  {
    number: 104, repository: "web-portal", author: "alice",
    targetBranch: "main", status: "merged", additions: 130, deletions: 45,
    commits: 4, reviews: 3, approvals: 2, requestedChanges: 0,
    merged: true, mergeStrategy: "rebase",
    openedAt: "2026-10-04T11:00:00Z", mergedAt: "2026-10-05T10:00:00Z",
    checksPassed: true
  },
  {
    number: 105, repository: "web-portal", author: "david",
    targetBranch: "main", status: "open", additions: 35, deletions: 8,
    commits: 2, reviews: 1, approvals: 0, requestedChanges: 0,
    merged: false, mergeStrategy: "none",
    openedAt: "2026-10-06T13:00:00Z", mergedAt: null,
    checksPassed: true
  },
  {
    number: 106, repository: "web-portal", author: "carol",
    targetBranch: "develop", status: "merged", additions: 250, deletions: 120,
    commits: 7, reviews: 4, approvals: 3, requestedChanges: 0,
    merged: true, mergeStrategy: "squash",
    openedAt: "2026-10-07T09:00:00Z", mergedAt: "2026-10-08T15:00:00Z",
    checksPassed: true
  }
];

function validatePullRequests(records) {
  const numbers = new Set();

  for (const pr of records) {
    if (numbers.has(pr.number)) {
      throw new Error(`Duplicate Pull Request #${pr.number}`);
    }
    numbers.add(pr.number);

    if (pr.additions < 0 || pr.deletions < 0 ||
        pr.reviews < 0 || pr.approvals < 0) {
      throw new Error(`Negative aggregation input in PR #${pr.number}`);
    }

    if (!["open", "merged", "closed"].includes(pr.status)) {
      throw new Error(`Invalid PR status: ${pr.status}`);
    }

    if (pr.merged && (!pr.mergedAt || !pr.checksPassed)) {
      throw new Error(`Merged PR #${pr.number} violates workflow integrity`);
    }
  }
}

function groupBy(records, keySelector) {
  return Map.groupBy(records, keySelector);
}

function numericAggregate(values) {
  if (values.length === 0) {
    return { count: 0, sum: 0, average: 0, min: 0, max: 0 };
  }

  const sum = values.reduce((total, value) => total + value, 0);

  return {
    count: values.length,
    sum,
    average: sum / values.length,
    min: Math.min(...values),
    max: Math.max(...values)
  };
}

function cycleHours(pr) {
  if (!pr.mergedAt) return null;

  const start = new Date(pr.openedAt);
  const end = new Date(pr.mergedAt);
  return (end - start) / 3_600_000;
}

function aggregateByRepository(records) {
  const grouped = groupBy(records, pr => pr.repository);
  const result = {};

  for (const [repository, items] of grouped) {
    const changes = items.map(pr => pr.additions + pr.deletions);
    const cycles = items.map(cycleHours).filter(Number.isFinite);

    // Conditional aggregation evaluates predicates inside the reduction.
    const merged = items.reduce(
      (count, pr) => count + Number(pr.merged), 0
    );

    const checksPassed = items.reduce(
      (count, pr) => count + Number(pr.checksPassed), 0
    );

    const requestedChanges = items.reduce(
      (count, pr) => count + Number(pr.requestedChanges > 0), 0
    );

    result[repository] = {
      pullRequests: items.length,
      merged,
      mergeRate: merged / items.length,
      changes: numericAggregate(changes),
      reviews: numericAggregate(items.map(pr => pr.reviews)),
      approvals: numericAggregate(items.map(pr => pr.approvals)),
      cycleHours: numericAggregate(cycles),
      checksPassed,
      requestedChanges
    };
  }

  return result;
}

function aggregateByTargetBranch(records) {
  const grouped = groupBy(records, pr => pr.targetBranch);
  const result = {};

  for (const [branch, items] of grouped) {
    result[branch] = {
      prs: items.length,
      merged: items.filter(pr => pr.merged).length,
      totalChanges: items.reduce(
        (total, pr) => total + pr.additions + pr.deletions, 0
      ),
      averageApprovals:
        items.reduce((total, pr) => total + pr.approvals, 0) / items.length
    };
  }

  return result;
}

function aggregateMergeStrategies(records) {
  return records
    .filter(pr => pr.merged)
    .reduce((counts, pr) => {
      counts[pr.mergeStrategy] = (counts[pr.mergeStrategy] || 0) + 1;
      return counts;
    }, {});
}

function evaluateMergeEligibility(pr, requiredApprovals = 2) {
  const reasons = [];

  if (pr.status !== "open") {
    reasons.push("Pull Request is not open");
  }

  if (!pr.checksPassed) {
    reasons.push("required status checks are failing");
  }

  if (pr.approvals < requiredApprovals) {
    reasons.push(`requires ${requiredApprovals} approvals`);
  }

  if (pr.requestedChanges > 0) {
    reasons.push("review has requested changes");
  }

  return {
    eligible: reasons.length === 0,
    reasons
  };
}

function aggregateEligibility(records, requiredApprovals) {
  return records.reduce(
    (summary, pr) => {
      const evaluation = evaluateMergeEligibility(pr, requiredApprovals);
      summary.total += 1;
      summary.eligible += Number(evaluation.eligible);
      summary.ineligible += Number(!evaluation.eligible);
      return summary;
    },
    { total: 0, eligible: 0, ineligible: 0 }
  );
}

async function generateReport(records) {
  // Async event-driven reporting allows this function to be replaced by
  // an API or database source without changing the aggregation layer.
  await Promise.resolve();

  return {
    repositories: aggregateByRepository(records),
    targetBranches: aggregateByTargetBranch(records),
    mergeStrategies: aggregateMergeStrategies(records),
    eligibility: aggregateEligibility(records, 2)
  };
}

async function main() {
  validatePullRequests(pullRequests);

  const report = await generateReport(pullRequests);
  console.log(JSON.stringify(report, null, 2));

  console.log("\nIndividual merge decisions:");
  for (const pr of pullRequests) {
    console.log(
      `PR #${pr.number}:`,
      evaluateMergeEligibility(pr, 2)
    );
  }
}

main().catch(error => {
  console.error(`Aggregation failed: ${error.message}`);
  process.exitCode = 1;
});
