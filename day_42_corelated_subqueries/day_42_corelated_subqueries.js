"use strict";

/*
 * Correlated subqueries are represented here through functions whose inner
 * predicate receives the current outer row.
 *
 * The repository domain makes the relationship concrete:
 *
 *   pullRequests.forEach(pr => {
 *       reviews.some(review =>
 *           review.pullRequestId === pr.id
 *       );
 *   });
 *
 * The comparison against pr.id is the correlation.
 *
 * This file deliberately uses JavaScript-specific mechanisms such as
 * Array.prototype.some(), filter(), reduce(), Map indexing, asynchronous
 * event processing, immutable objects, and event-driven policy evaluation.
 */

const repository = Object.freeze({
  name: "payments-service",

  pullRequests: Object.freeze([
    Object.freeze({
      id: 101,
      number: 41,
      title: "Add transaction reconciliation",
      author: "david",
      baseBranch: "main",
      sourceBranch: "feature/reconciliation",
      draft: false,
    }),
    Object.freeze({
      id: 102,
      number: 42,
      title: "Improve payment timeout handling",
      author: "alice",
      baseBranch: "main",
      sourceBranch: "fix/payment-timeout",
      draft: false,
    }),
    Object.freeze({
      id: 103,
      number: 43,
      title: "Refactor settlement validation",
      author: "bob",
      baseBranch: "main",
      sourceBranch: "refactor/settlement",
      draft: true,
    }),
  ]),

  reviews: Object.freeze([
    Object.freeze({
      id: 1,
      pullRequestId: 101,
      reviewer: "alice",
      state: "APPROVED",
    }),
    Object.freeze({
      id: 2,
      pullRequestId: 101,
      reviewer: "bob",
      state: "COMMENTED",
    }),
    Object.freeze({
      id: 3,
      pullRequestId: 102,
      reviewer: "carol",
      state: "APPROVED",
    }),
    Object.freeze({
      id: 4,
      pullRequestId: 103,
      reviewer: "alice",
      state: "CHANGES_REQUESTED",
    }),
  ]),

  comments: Object.freeze([
    Object.freeze({
      id: 1,
      pullRequestId: 101,
      resolved: false,
      body: "Document the fallback behavior.",
    }),
    Object.freeze({
      id: 2,
      pullRequestId: 102,
      resolved: true,
      body: "Timeout handling is clear.",
    }),
  ]),

  statusChecks: Object.freeze([
    Object.freeze({
      pullRequestId: 101,
      name: "unit-tests",
      state: "SUCCESS",
    }),
    Object.freeze({
      pullRequestId: 101,
      name: "security-scan",
      state: "SUCCESS",
    }),
    Object.freeze({
      pullRequestId: 102,
      name: "unit-tests",
      state: "SUCCESS",
    }),
    Object.freeze({
      pullRequestId: 102,
      name: "security-scan",
      state: "FAILURE",
    }),
  ]),

  branchProtection: Object.freeze({
    main: Object.freeze({
      requiredApprovals: 1,
      requiredChecks: Object.freeze(["unit-tests", "security-scan"]),
      requireResolvedConversations: true,
      allowForcePush: false,
      allowDeletion: false,
      requireLinearHistory: true,
    }),
  }),
});


/*
 * Generic correlated EXISTS.
 *
 * The outer row is passed into the inner predicate. The inner relation is
 * therefore evaluated in the context of the current outer row.
 */
function correlatedExists(outerRows, innerRows, predicate) {
  return outerRows.filter((outerRow) =>
    innerRows.some((innerRow) => predicate(outerRow, innerRow))
  );
}


/*
 * Correlated NOT EXISTS.
 */
function correlatedNotExists(outerRows, innerRows, predicate) {
  return outerRows.filter(
    (outerRow) =>
      !innerRows.some((innerRow) => predicate(outerRow, innerRow))
  );
}


/*
 * Correlated COUNT.
 *
 * This corresponds conceptually to:
 *
 *   SELECT p.id,
 *          (SELECT COUNT(*)
 *           FROM reviews r
 *           WHERE r.pull_request_id = p.id)
 *   FROM pull_requests p;
 */
function correlatedCount(outerRows, innerRows, predicate) {
  return new Map(
    outerRows.map((outerRow) => [
      outerRow.id,
      innerRows.filter((innerRow) => predicate(outerRow, innerRow)).length,
    ])
  );
}


/*
 * Correlated scalar aggregate.
 *
 * SQL would normally return NULL when MAX() has no matching rows. JavaScript
 * uses null here to make the absence explicit rather than returning an
 * arbitrary sentinel.
 */
function correlatedMax(outerRows, innerRows, predicate, selector) {
  const result = new Map();

  for (const outerRow of outerRows) {
    const matching = innerRows.filter((innerRow) =>
      predicate(outerRow, innerRow)
    );

    result.set(
      outerRow.id,
      matching.length === 0
        ? null
        : matching.reduce((maximum, row) => {
            const value = selector(row);
            return maximum === null || value > maximum ? value : maximum;
          }, null)
    );
  }

  return result;
}


function showApprovedPullRequests() {
  console.log("\n=== Correlated EXISTS ===");

  const approved = correlatedExists(
    repository.pullRequests,
    repository.reviews,
    (pr, review) =>
      review.pullRequestId === pr.id &&
      review.state === "APPROVED"
  );

  for (const pr of approved) {
    console.log(`PR #${pr.number}: ${pr.title}`);
  }
}


function showCleanPullRequests() {
  console.log("\n=== Correlated NOT EXISTS ===");

  const clean = correlatedNotExists(
    repository.pullRequests,
    repository.comments,
    (pr, comment) =>
      comment.pullRequestId === pr.id && !comment.resolved
  );

  for (const pr of clean) {
    console.log(`PR #${pr.number}: no unresolved conversations`);
  }
}


function showReviewCounts() {
  console.log("\n=== Correlated COUNT ===");

  const counts = correlatedCount(
    repository.pullRequests,
    repository.reviews,
    (pr, review) => review.pullRequestId === pr.id
  );

  for (const pr of repository.pullRequests) {
    console.log(`PR #${pr.number}: ${counts.get(pr.id)} review(s)`);
  }
}


function showLatestReviews() {
  console.log("\n=== Correlated MAX ===");

  const reviewTimes = [
    { reviewId: 1, time: "2026-10-12T06:00:00Z" },
    { reviewId: 2, time: "2026-10-12T07:00:00Z" },
    { reviewId: 3, time: "2026-10-12T08:00:00Z" },
    { reviewId: 4, time: "2026-10-12T09:00:00Z" },
  ];

  const enrichedReviews = repository.reviews.map((review) => ({
    ...review,
    submittedAt:
      reviewTimes.find((entry) => entry.reviewId === review.id)?.time ?? null,
  }));

  const latest = correlatedMax(
    repository.pullRequests,
    enrichedReviews,
    (pr, review) => review.pullRequestId === pr.id,
    (review) => review.submittedAt
  );

  for (const pr of repository.pullRequests) {
    console.log(
      `PR #${pr.number}: latest review = ${latest.get(pr.id) ?? "none"}`
    );
  }
}


/*
 * A correlated policy check can contain several independent correlated
 * predicates. Each is evaluated relative to the same current PR.
 */
function evaluatePullRequest(pr) {
  const policy = repository.branchProtection[pr.baseBranch];

  if (!policy) {
    return {
      eligible: false,
      reasons: ["No branch protection policy is configured."],
    };
  }

  const reasons = [];

  const approvals = repository.reviews.filter(
    (review) =>
      review.pullRequestId === pr.id &&
      review.state === "APPROVED" &&
      review.reviewer !== pr.author
  ).length;

  if (pr.draft) {
    reasons.push("Pull Request is a draft.");
  }

  if (approvals < policy.requiredApprovals) {
    reasons.push(
      `Requires ${policy.requiredApprovals} approval(s), found ${approvals}.`
    );
  }

  for (const checkName of policy.requiredChecks) {
    const successful = repository.statusChecks.some(
      (check) =>
        check.pullRequestId === pr.id &&
        check.name === checkName &&
        check.state === "SUCCESS"
    );

    if (!successful) {
      reasons.push(`Required check '${checkName}' is not successful.`);
    }
  }

  if (policy.requireResolvedConversations) {
    const unresolved = repository.comments.some(
      (comment) =>
        comment.pullRequestId === pr.id && !comment.resolved
    );

    if (unresolved) {
      reasons.push("Unresolved review conversations remain.");
    }
  }

  return {
    eligible: reasons.length === 0,
    reasons,
  };
}


function showMergeEligibility() {
  console.log("\n=== Correlated merge eligibility ===");

  for (const pr of repository.pullRequests) {
    const result = evaluatePullRequest(pr);

    console.log(
      `PR #${pr.number}: ${result.eligible ? "ELIGIBLE" : "BLOCKED"}`
    );

    for (const reason of result.reasons) {
      console.log(`  ${reason}`);
    }
  }
}


/*
 * Event-driven processing is a natural JavaScript representation of
 * repository automation. Each event carries the PR identifier, and the
 * handler correlates that event with the current repository state.
 */
class RepositoryEventProcessor {
  constructor(repo) {
    this.repo = repo;
    this.handlers = new Map();
  }

  on(eventName, handler) {
    if (!this.handlers.has(eventName)) {
      this.handlers.set(eventName, []);
    }

    this.handlers.get(eventName).push(handler);
  }

  async emit(eventName, event) {
    const handlers = this.handlers.get(eventName) ?? [];

    for (const handler of handlers) {
      await handler(event, this.repo);
    }
  }
}


async function demonstrateEventDrivenCorrelation() {
  console.log("\n=== Event-driven correlated evaluation ===");

  const processor = new RepositoryEventProcessor(repository);

  processor.on("status-check-completed", async (event, repo) => {
    const pr = repo.pullRequests.find(
      (candidate) => candidate.id === event.pullRequestId
    );

    if (!pr) {
      console.log(`Event references unknown PR ${event.pullRequestId}.`);
      return;
    }

    const result = evaluatePullRequest(pr);

    console.log(
      `Event for PR #${pr.number}: ${
        result.eligible ? "eligible" : "still blocked"
      }`
    );
  });

  await processor.emit("status-check-completed", {
    pullRequestId: 101,
    checkName: "security-scan",
  });

  await processor.emit("status-check-completed", {
    pullRequestId: 102,
    checkName: "security-scan",
  });
}


/*
 * Correlated nested evaluation:
 *
 * outer PR
 *   -> matching review
 *      -> reviewer eligibility
 *
 * The second lookup depends on the reviewer found for the current PR.
 */
function showEligibleReviewerApprovals() {
  console.log("\n=== Nested correlated relationship ===");

  const reviewerDirectory = [
    { username: "alice", active: true, role: "reviewer" },
    { username: "bob", active: true, role: "developer" },
    { username: "carol", active: true, role: "reviewer" },
  ];

  for (const pr of repository.pullRequests) {
    const hasEligibleApproval = repository.reviews.some((review) => {
      if (
        review.pullRequestId !== pr.id ||
        review.state !== "APPROVED"
      ) {
        return false;
      }

      const reviewer = reviewerDirectory.find(
        (candidate) => candidate.username === review.reviewer
      );

      return reviewer?.active === true && reviewer.role === "reviewer";
    });

    console.log(
      `PR #${pr.number}: ${
        hasEligibleApproval
          ? "eligible reviewer approval found"
          : "no eligible reviewer approval"
      }`
    );
  }
}


/*
 * Naive correlated execution repeatedly scans the inner collection.
 *
 * If there are N PRs and M reviews, the worst-case number of comparisons is
 * O(N*M). A Map keyed by pullRequestId provides an index-like alternative.
 */
function demonstrateIndexedOptimization() {
  console.log("\n=== Indexed alternative to repeated correlation ===");

  const reviewsByPullRequest = new Map();

  for (const review of repository.reviews) {
    if (!reviewsByPullRequest.has(review.pullRequestId)) {
      reviewsByPullRequest.set(review.pullRequestId, []);
    }

    reviewsByPullRequest.get(review.pullRequestId).push(review);
  }

  for (const pr of repository.pullRequests) {
    const reviews = reviewsByPullRequest.get(pr.id) ?? [];
    const approvals = reviews.filter(
      (review) => review.state === "APPROVED"
    );

    console.log(
      `PR #${pr.number}: ${approvals.length} approval(s) using indexed lookup`
    );
  }
}


/*
 * Correlated subqueries are not automatically superior to joins.
 * When the inner relation can be transformed into a grouped or indexed
 * operation, a query planner may choose a more efficient physical strategy.
 *
 * The logical SQL construct and the physical execution strategy are separate
 * concerns. A correlated SQL expression can be decorrelated by a database
 * optimizer when the transformation is safe.
 */
function explainExecutionBoundary() {
  console.log("\n=== Execution boundary ===");
  console.log(
    "Correlation is a logical dependency between query scopes. " +
    "The database may still transform the resulting execution plan."
  );
}


async function main() {
  console.log(`Repository: ${repository.name}`);
  console.log("Topic: correlated subqueries and repository governance");

  showApprovedPullRequests();
  showCleanPullRequests();
  showReviewCounts();
  showLatestReviews();
  showMergeEligibility();
  showEligibleReviewerApprovals();
  demonstrateIndexedOptimization();
  await demonstrateEventDrivenCorrelation();
  explainExecutionBoundary();
}

main().catch((error) => {
  console.error("Execution failed:", error.message);
  process.exitCode = 1;
});
