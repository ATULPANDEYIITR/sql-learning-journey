import java.util.*;
import java.util.stream.Collectors;

public class RepositoryGovernance {

    enum PullRequestState {
        DRAFT, OPEN, CLOSED, MERGED
    }

    enum ReviewState {
        COMMENTED, CHANGES_REQUESTED, APPROVED, DISMISSED
    }

    enum MergeStrategy {
        MERGE_COMMIT, SQUASH, REBASE
    }

    record Commit(String sha, String message, String author) {
        Commit {
            if (sha == null || sha.isBlank()) {
                throw new ValidationException("Commit SHA is required");
            }
            if (message == null || message.isBlank()) {
                throw new ValidationException("Commit message is required");
            }
            if (author == null || author.isBlank()) {
                throw new ValidationException("Commit author is required");
            }
        }
    }

    record Review(
            String reviewer,
            ReviewState state,
            String commitSha,
            List<String> comments
    ) {
        Review {
            comments = List.copyOf(comments);
        }
    }

    record StatusCheck(
            String name,
            boolean passed,
            boolean required,
            String commitSha
    ) {}

    record BranchProtection(
            int requiredReviews,
            Set<String> requiredStatusChecks,
            boolean restrictDirectPush,
            boolean restrictForcePush,
            boolean restrictDeletion,
            boolean requireConversationsResolved,
            boolean requireLinearHistory
    ) {
        BranchProtection {
            if (requiredReviews < 0) {
                throw new ValidationException(
                        "Required review count cannot be negative"
                );
            }

            requiredStatusChecks =
                    Set.copyOf(requiredStatusChecks);
        }
    }

    static final class Branch {
        private final String name;
        private final boolean protectedBranch;
        private final List<Commit> commits;

        Branch(
                String name,
                boolean protectedBranch,
                List<Commit> commits
        ) {
            this.name = name;
            this.protectedBranch = protectedBranch;
            this.commits = new ArrayList<>(commits);
        }

        String name() {
            return name;
        }

        boolean protectedBranch() {
            return protectedBranch;
        }

        List<Commit> commits() {
            return commits;
        }
    }

    static final class PullRequest {
        private final int number;
        private final String sourceBranch;
        private final String targetBranch;
        private final String author;
        private final List<Commit> commits;

        private PullRequestState state = PullRequestState.OPEN;
        private boolean draft;
        private final List<Review> reviews = new ArrayList<>();
        private final List<StatusCheck> checks = new ArrayList<>();
        private int unresolvedConversations;
        private MergeStrategy mergeStrategy = MergeStrategy.SQUASH;
        private boolean baseSyncRequired;

        PullRequest(
                int number,
                String sourceBranch,
                String targetBranch,
                String author,
                List<Commit> commits,
                boolean draft
        ) {
            if (commits.isEmpty()) {
                throw new ValidationException(
                        "Pull Request requires a changeset"
                );
            }

            this.number = number;
            this.sourceBranch = sourceBranch;
            this.targetBranch = targetBranch;
            this.author = author;
            this.commits = new ArrayList<>(commits);
            this.draft = draft;
        }

        int number() {
            return number;
        }

        String author() {
            return author;
        }

        String targetBranch() {
            return targetBranch;
        }

        String headSha() {
            return commits.getLast().sha();
        }

        List<Review> reviews() {
            return reviews;
        }

        List<StatusCheck> checks() {
            return checks;
        }

        PullRequestState state() {
            return state;
        }

        boolean draft() {
            return draft;
        }

        int unresolvedConversations() {
            return unresolvedConversations;
        }

        MergeStrategy mergeStrategy() {
            return mergeStrategy;
        }
    }

    static final class ValidationException
            extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    static final class MergeBlockedException
            extends RuntimeException {
        MergeBlockedException(String message) {
            super(message);
        }
    }

    interface ReviewPolicy {
        boolean eligible(String reviewer, PullRequest pullRequest);

        boolean satisfies(PullRequest pullRequest);
    }

    static final class EnterpriseReviewPolicy
            implements ReviewPolicy {

        private final Set<String> eligibleReviewers;
        private final int requiredApprovals;

        EnterpriseReviewPolicy(
                Set<String> eligibleReviewers,
                int requiredApprovals
        ) {
            this.eligibleReviewers =
                    Set.copyOf(eligibleReviewers);
            this.requiredApprovals = requiredApprovals;
        }

        @Override
        public boolean eligible(
                String reviewer,
                PullRequest pullRequest
        ) {
            return eligibleReviewers.contains(reviewer)
                    && !reviewer.equals(pullRequest.author());
        }

        @Override
        public boolean satisfies(PullRequest pullRequest) {
            Set<String> approvals =
                    pullRequest.reviews().stream()
                            .filter(r ->
                                    r.state() ==
                                            ReviewState.APPROVED)
                            .filter(r ->
                                    r.commitSha().equals(
                                            pullRequest.headSha()))
                            .map(Review::reviewer)
                            .collect(Collectors.toSet());

            return approvals.size() >= requiredApprovals;
        }
    }

    static final class MergeEligibilityService {

        List<String> evaluate(
                PullRequest pr,
                BranchProtection protection,
                ReviewPolicy reviewPolicy
        ) {
            List<String> failures = new ArrayList<>();

            if (pr.state() != PullRequestState.OPEN) {
                failures.add("Pull Request is not open");
            }

            if (pr.draft()) {
                failures.add("Pull Request remains a draft");
            }

            if (!reviewPolicy.satisfies(pr)) {
                failures.add("Required current approvals are missing");
            }

            Map<String, StatusCheck> checks =
                    pr.checks().stream()
                            .filter(c ->
                                    c.commitSha().equals(
                                            pr.headSha()))
                            .collect(Collectors.toMap(
                                    StatusCheck::name,
                                    c -> c,
                                    (first, second) -> second
                            ));

            for (String required :
                    protection.requiredStatusChecks()) {

                StatusCheck check = checks.get(required);

                if (check == null) {
                    failures.add(
                            "Missing status check: " + required
                    );
                } else if (!check.passed()) {
                    failures.add(
                            "Failed status check: " + required
                    );
                }
            }

            if (
                    protection.requireConversationsResolved()
                            && pr.unresolvedConversations() > 0
            ) {
                failures.add(
                        "Unresolved review conversations remain"
                );
            }

            if (
                    protection.requireLinearHistory()
                            && pr.mergeStrategy()
                            == MergeStrategy.MERGE_COMMIT
            ) {
                failures.add(
                        "Merge commit violates linear-history policy"
                );
            }

            return failures;
        }
    }

    static final class RepositoryService {

        private final Map<String, Branch> branches =
                new HashMap<>();

        private final Map<Integer, PullRequest> pullRequests =
                new HashMap<>();

        private final Map<String, BranchProtection> protection =
                new HashMap<>();

        private final ReviewPolicy reviewPolicy;
        private final MergeEligibilityService eligibility =
                new MergeEligibilityService();

        private int nextPullRequest = 1;

        RepositoryService(ReviewPolicy reviewPolicy) {
            this.reviewPolicy = reviewPolicy;
        }

        void addBranch(Branch branch) {
            if (branches.containsKey(branch.name())) {
                throw new ValidationException(
                        "Duplicate branch: " + branch.name()
                );
            }

            branches.put(branch.name(), branch);
        }

        void protect(
                String branch,
                BranchProtection branchProtection
        ) {
            if (!branches.containsKey(branch)) {
                throw new ValidationException(
                        "Unknown branch: " + branch
                );
            }

            protection.put(branch, branchProtection);
        }

        PullRequest createPullRequest(
                String source,
                String target,
                String author,
                List<Commit> commits
        ) {
            if (!branches.containsKey(source)
                    || !branches.containsKey(target)) {
                throw new ValidationException(
                        "Source or target branch does not exist"
                );
            }

            if (source.equals(target)) {
                throw new ValidationException(
                        "Source and target must differ"
                );
            }

            PullRequest pr = new PullRequest(
                    nextPullRequest++,
                    source,
                    target,
                    author,
                    commits,
                    false
            );

            pullRequests.put(pr.number(), pr);
            return pr;
        }

        void submitReview(
                PullRequest pr,
                String reviewer,
                ReviewState state,
                String... comments
        ) {
            if (!reviewPolicy.eligible(reviewer, pr)) {
                throw new ValidationException(
                        "Reviewer is not eligible"
                );
            }

            if (
                    state == ReviewState.CHANGES_REQUESTED
                            && comments.length == 0
            ) {
                throw new ValidationException(
                        "Changes requested requires a comment"
                );
            }

            pr.reviews().add(
                    new Review(
                            reviewer,
                            state,
                            pr.headSha(),
                            List.of(comments)
                    )
            );
        }

        void addStatusCheck(
                PullRequest pr,
                String name,
                boolean passed
        ) {
            pr.checks().add(
                    new StatusCheck(
                            name,
                            passed,
                            true,
                            pr.headSha()
                    )
            );
        }

        void addUnresolvedConversation(PullRequest pr) {
            try {
                var field =
                        PullRequest.class
                                .getDeclaredField(
                                        "unresolvedConversations"
                                );
                field.setAccessible(true);
                field.setInt(
                        pr,
                        pr.unresolvedConversations() + 1
                );
            } catch (ReflectiveOperationException ex) {
                throw new ValidationException(
                        "Unable to update conversation state"
                );
            }
        }

        List<String> evaluate(PullRequest pr) {
            BranchProtection policy =
                    protection.getOrDefault(
                            pr.targetBranch(),
                            new BranchProtection(
                                    1,
                                    Set.of(),
                                    true,
                                    true,
                                    true,
                                    true,
                                    false
                            )
                    );

            return eligibility.evaluate(
                    pr,
                    policy,
                    reviewPolicy
            );
        }

        void merge(PullRequest pr) {
            List<String> failures = evaluate(pr);

            if (!failures.isEmpty()) {
                throw new MergeBlockedException(
                        String.join("; ", failures)
                );
            }

            Branch target = branches.get(pr.targetBranch());

            target.commits().add(
                    new Commit(
                            "squash-" + pr.number(),
                            "Squash Pull Request #" +
                                    pr.number(),
                            pr.author()
                    )
            );
        }
    }

    public static void main(String[] args) {
        Set<String> reviewers =
                Set.of("bob", "carol", "diana");

        ReviewPolicy reviewPolicy =
                new EnterpriseReviewPolicy(reviewers, 2);

        RepositoryService repository =
                new RepositoryService(reviewPolicy);

        repository.addBranch(
                new Branch(
                        "main",
                        true,
                        List.of(
                                new Commit(
                                        "a1",
                                        "Initial release",
                                        "alice"
                                ),
                                new Commit(
                                        "b2",
                                        "Payment API",
                                        "alice"
                                )
                        )
                )
        );

        repository.addBranch(
                new Branch(
                        "feature/fraud",
                        false,
                        List.of()
                )
        );

        repository.protect(
                "main",
                new BranchProtection(
                        2,
                        Set.of(
                                "unit-tests",
                                "security-scan"
                        ),
                        true,
                        true,
                        true,
                        true,
                        true
                )
        );

        PullRequest pr =
                repository.createPullRequest(
                        "feature/fraud",
                        "main",
                        "alice",
                        List.of(
                                new Commit(
                                        "c1",
                                        "Add fraud rules",
                                        "alice"
                                ),
                                new Commit(
                                        "c2",
                                        "Validate thresholds",
                                        "alice"
                                )
                        )
                );

        repository.submitReview(
                pr,
                "bob",
                ReviewState.APPROVED
        );

        repository.submitReview(
                pr,
                "carol",
                ReviewState.CHANGES_REQUESTED,
                "Reject duplicate threshold definitions"
        );

        repository.addStatusCheck(
                pr,
                "unit-tests",
                true
        );

        repository.addStatusCheck(
                pr,
                "security-scan",
                true
        );

        repository.addUnresolvedConversation(pr);

        List<String> firstEvaluation =
                repository.evaluate(pr);

        System.out.println("First merge evaluation:");

        firstEvaluation.forEach(
                failure -> System.out.println(" - " + failure)
        );

        pr.reviews().add(
                new Review(
                        "carol",
                        ReviewState.APPROVED,
                        pr.headSha(),
                        List.of()
                )
        );

        List<String> secondEvaluation =
                repository.evaluate(pr);

        System.out.println(
                "\nSecond evaluation before conversation resolution:"
        );

        secondEvaluation.forEach(
                failure -> System.out.println(" - " + failure)
        );

        try {
            repository.merge(pr);
        } catch (MergeBlockedException ex) {
            System.out.println(
                    "\nExpected merge block: " +
                            ex.getMessage()
            );
        }
    }
}
