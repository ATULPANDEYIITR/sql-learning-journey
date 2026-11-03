'use strict';

const EventEmitter = require('events');

const PullRequestState = Object.freeze({
    DRAFT: 'draft',
    OPEN: 'open',
    CLOSED: 'closed',
    MERGED: 'merged'
});

const ReviewState = Object.freeze({
    COMMENTED: 'commented',
    CHANGES_REQUESTED: 'changes_requested',
    APPROVED: 'approved',
    DISMISSED: 'dismissed'
});

const MergeStrategy = Object.freeze({
    MERGE_COMMIT: 'merge_commit',
    SQUASH: 'squash',
    REBASE: 'rebase'
});

class WorkflowError extends Error {}

class Commit {
    constructor(sha, message, author) {
        if (!sha || !message || !author) {
            throw new WorkflowError('Commit requires sha, message, and author');
        }
        this.sha = sha;
        this.message = message;
        this.author = author;
    }
}

class Review {
    constructor(reviewer, state, commitSha, comments = []) {
        this.reviewer = reviewer;
        this.state = state;
        this.commitSha = commitSha;
        this.comments = [...comments];
    }
}

class StatusCheck {
    constructor(name, passed, required, commitSha) {
        this.name = name;
        this.passed = Boolean(passed);
        this.required = Boolean(required);
        this.commitSha = commitSha;
    }
}

class BranchProtection {
    constructor({
        requiredReviews = 1,
        requiredStatusChecks = [],
        restrictDirectPush = true,
        restrictForcePush = true,
        restrictDeletion = true,
        requireConversationsResolved = true,
        requireLinearHistory = false
    } = {}) {
        this.requiredReviews = requiredReviews;
        this.requiredStatusChecks = new Set(requiredStatusChecks);
        this.restrictDirectPush = restrictDirectPush;
        this.restrictForcePush = restrictForcePush;
        this.restrictDeletion = restrictDeletion;
        this.requireConversationsResolved = requireConversationsResolved;
        this.requireLinearHistory = requireLinearHistory;
    }
}

class Branch {
    constructor(name, protectedBranch = false, commits = []) {
        this.name = name;
        this.protected = protectedBranch;
        this.commits = [...commits];
    }
}

class PullRequest {
    constructor(number, sourceBranch, targetBranch, author, commits, draft = false) {
        if (!commits.length) {
            throw new WorkflowError('A Pull Request requires at least one commit');
        }

        this.number = number;
        this.sourceBranch = sourceBranch;
        this.targetBranch = targetBranch;
        this.author = author;
        this.commits = [...commits];
        this.state = PullRequestState.OPEN;
        this.draft = draft;
        this.reviews = [];
        this.checks = [];
        this.unresolvedConversations = 0;
        this.mergeStrategy = MergeStrategy.SQUASH;
        this.baseSyncRequired = false;
    }

    get headSha() {
        return this.commits[this.commits.length - 1].sha;
    }
}

class RepositoryWorkflow extends EventEmitter {
    constructor(repository) {
        super();
        this.repository = repository;
        this.pullRequests = new Map();
        this.nextNumber = 1;
    }

    createPullRequest({ sourceBranch, targetBranch, author, commits, draft = false }) {
        if (!this.repository.branches.has(sourceBranch)) {
            throw new WorkflowError(`Unknown source branch: ${sourceBranch}`);
        }

        if (!this.repository.branches.has(targetBranch)) {
            throw new WorkflowError(`Unknown target branch: ${targetBranch}`);
        }

        if (sourceBranch === targetBranch) {
            throw new WorkflowError('Source and target branches must differ');
        }

        const pr = new PullRequest(
            this.nextNumber++,
            sourceBranch,
            targetBranch,
            author,
            commits,
            draft
        );

        this.pullRequests.set(pr.number, pr);
        this.emit('pull_request.opened', pr);
        return pr;
    }

    requestReview(number, reviewer) {
        const pr = this.getPR(number);

        if (pr.state !== PullRequestState.OPEN) {
            throw new WorkflowError('Review requests require an open Pull Request');
        }

        if (reviewer === pr.author) {
            throw new WorkflowError('Author cannot be their own reviewer');
        }

        if (!this.repository.reviewers.has(reviewer)) {
            throw new WorkflowError('Reviewer is not eligible');
        }

        this.emit('review.requested', { number, reviewer });
    }

    submitReview(number, reviewer, state, comments = []) {
        const pr = this.getPR(number);

        if (!this.repository.reviewers.has(reviewer)) {
            throw new WorkflowError('Reviewer is not eligible');
        }

        if (reviewer === pr.author) {
            throw new WorkflowError('Author cannot submit an approval');
        }

        if (
            state === ReviewState.CHANGES_REQUESTED &&
            comments.length === 0
        ) {
            throw new WorkflowError(
                'Changes requested must contain a meaningful comment'
            );
        }

        const review = new Review(
            reviewer,
            state,
            pr.headSha,
            comments
        );

        pr.reviews.push(review);
        this.emit('review.submitted', review);
    }

    addStatusCheck(number, name, passed, required = true) {
        const pr = this.getPR(number);
        const check = new StatusCheck(name, passed, required, pr.headSha);
        pr.checks.push(check);
        this.emit('status.updated', check);
    }

    addConversation(number) {
        this.getPR(number).unresolvedConversations++;
    }

    resolveConversation(number) {
        const pr = this.getPR(number);

        if (pr.unresolvedConversations <= 0) {
            throw new WorkflowError('No unresolved conversation exists');
        }

        pr.unresolvedConversations--;
    }

    synchronizeBase(number, commit) {
        const pr = this.getPR(number);
        pr.commits.push(commit);
        pr.baseSyncRequired = false;

        for (const review of pr.reviews) {
            if (review.commitSha !== pr.headSha) {
                review.state = ReviewState.DISMISSED;
            }
        }

        this.emit('pull_request.synchronized', pr);
    }

    mergeEligibility(number) {
        const pr = this.getPR(number);
        const protection =
            this.repository.protection.get(pr.targetBranch) ??
            new BranchProtection();

        const failures = [];

        if (pr.state !== PullRequestState.OPEN) {
            failures.push('Pull Request is not open');
        }

        if (pr.draft) {
            failures.push('Pull Request is still a draft');
        }

        if (pr.baseSyncRequired) {
            failures.push('Base branch synchronization is required');
        }

        const approvals = new Set(
            pr.reviews
                .filter(
                    review =>
                        review.state === ReviewState.APPROVED &&
                        review.commitSha === pr.headSha &&
                        review.reviewer !== pr.author
                )
                .map(review => review.reviewer)
        );

        if (approvals.size < protection.requiredReviews) {
            failures.push(
                `${protection.requiredReviews} current approval(s) required`
            );
        }

        const currentChecks = new Map();

        for (const check of pr.checks) {
            if (check.commitSha === pr.headSha) {
                currentChecks.set(check.name, check);
            }
        }

        for (const requiredCheck of protection.requiredStatusChecks) {
            const check = currentChecks.get(requiredCheck);

            if (!check) {
                failures.push(`Missing status check: ${requiredCheck}`);
            } else if (!check.passed) {
                failures.push(`Failed status check: ${requiredCheck}`);
            }
        }

        if (
            protection.requireConversationsResolved &&
            pr.unresolvedConversations > 0
        ) {
            failures.push('Unresolved review conversations remain');
        }

        if (
            protection.requireLinearHistory &&
            pr.mergeStrategy === MergeStrategy.MERGE_COMMIT
        ) {
            failures.push('Merge commits violate linear-history policy');
        }

        return {
            eligible: failures.length === 0,
            failures
        };
    }

    merge(number) {
        const pr = this.getPR(number);
        const result = this.mergeEligibility(number);

        if (!result.eligible) {
            throw new WorkflowError(
                `Merge blocked: ${result.failures.join('; ')}`
            );
        }

        const target = this.repository.branches.get(pr.targetBranch);

        if (pr.mergeStrategy === MergeStrategy.SQUASH) {
            target.commits.push(
                new Commit(
                    `squash-${pr.number}`,
                    `Squash Pull Request #${pr.number}`,
                    pr.author
                )
            );
        } else if (pr.mergeStrategy === MergeStrategy.REBASE) {
            target.commits.push(...pr.commits);
        } else {
            target.commits.push(
                new Commit(
                    `merge-${pr.number}`,
                    `Merge Pull Request #${pr.number}`,
                    pr.author
                )
            );
        }

        pr.state = PullRequestState.MERGED;
        this.emit('pull_request.merged', pr);
    }

    getPR(number) {
        const pr = this.pullRequests.get(number);

        if (!pr) {
            throw new WorkflowError(`Pull Request #${number} does not exist`);
        }

        return pr;
    }
}

function buildRepository() {
    return {
        name: 'payments-platform',
        branches: new Map([
            [
                'main',
                new Branch(
                    'main',
                    true,
                    [
                        new Commit('a1', 'Initial release', 'alice'),
                        new Commit('b2', 'Payment API', 'alice')
                    ]
                )
            ],
            ['feature/risk-engine', new Branch('feature/risk-engine')]
        ]),
        reviewers: new Set(['bob', 'carol', 'diana']),
        protection: new Map([
            [
                'main',
                new BranchProtection({
                    requiredReviews: 2,
                    requiredStatusChecks: ['unit-tests', 'security-scan'],
                    requireConversationsResolved: true,
                    requireLinearHistory: true
                })
            ]
        ])
    };
}

async function main() {
    const workflow = new RepositoryWorkflow(buildRepository());

    workflow.on('pull_request.opened', pr =>
        console.log(`PR #${pr.number} opened`)
    );

    workflow.on('review.submitted', review =>
        console.log(`Review submitted by ${review.reviewer}: ${review.state}`)
    );

    workflow.on('pull_request.merged', pr =>
        console.log(`PR #${pr.number} merged`)
    );

    const pr = workflow.createPullRequest({
        sourceBranch: 'feature/risk-engine',
        targetBranch: 'main',
        author: 'alice',
        commits: [
            new Commit('c1', 'Add risk rules', 'alice'),
            new Commit('c2', 'Validate risk thresholds', 'alice')
        ]
    });

    workflow.requestReview(pr.number, 'bob');
    workflow.requestReview(pr.number, 'carol');

    workflow.submitReview(
        pr.number,
        'bob',
        ReviewState.APPROVED
    );

    workflow.submitReview(
        pr.number,
        'carol',
        ReviewState.CHANGES_REQUESTED,
        ['Reject duplicate threshold definitions']
    );

    workflow.addConversation(pr.number);
    workflow.addStatusCheck(pr.number, 'unit-tests', true);
    workflow.addStatusCheck(pr.number, 'security-scan', true);

    console.log(
        'First eligibility:',
        workflow.mergeEligibility(pr.number)
    );

    workflow.resolveConversation(pr.number);

    workflow.submitReview(
        pr.number,
        'carol',
        ReviewState.APPROVED
    );

    console.log(
        'Second eligibility:',
        workflow.mergeEligibility(pr.number)
    );

    workflow.merge(pr.number);

    try {
        workflow.merge(pr.number);
    } catch (error) {
        console.log('Expected failure:', error.message);
    }
}

main().catch(error => {
    console.error('Fatal workflow error:', error.message);
    process.exitCode = 1;
});
