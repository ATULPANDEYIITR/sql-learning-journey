import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;

/*
 * Enterprise repository governance using Java 17.
 *
 * The domain model separates Pull Request state, reviewer decisions,
 * status checks, and branch protection. Existence queries are represented
 * with Stream.anyMatch(), while missing-policy conditions use negation
 * or noneMatch(). Approval counts use distinct eligible reviewer identities.
 *
 * Compile:
 *   javac RepositoryGovernance.java
 *
 * Run:
 *   java RepositoryGovernance
 */

public class RepositoryGovernance {

    enum PullRequestState {
        OPEN,
        DRAFT,
        MERGED,
        CLOSED
    }

    enum ReviewState {
        APPROVED,
        CHANGES_REQUESTED,
        COMMENTED
    }

    enum CheckState {
        SUCCESS,
        FAILURE,
        PENDING
    }

    enum Permission {
        READ,
        WRITE,
        MAINTAIN,
        ADMIN
    }

    record Developer(int id, String name, String team, boolean active) {
        Developer {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new IllegalArgumentException("Invalid developer identity");
            }
            Objects.requireNonNull(team, "team");
        }
    }

    record Repository(
        int id,
        String name,
        boolean protectedBranch,
        int requiredApprovals,
        boolean requireLinearHistory,
        boolean restrictDirectPushes,
        boolean restrictForcePushes,
        boolean restrictDeletion,
        boolean dismissStaleApprovals,
        boolean requireResolvedConversations,
        boolean allowAdministratorBypass,
        Set<String> requiredChecks
    ) {
        Repository {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new IllegalArgumentException("Invalid repository");
            }
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "Required approvals cannot be negative"
                );
            }
            requiredChecks = Set.copyOf(requiredChecks);
        }
    }

    record PullRequest(
        int id,
        int repositoryId,
        int authorId,
        String title,
        String sourceBranch,
        String targetBranch,
        PullRequestState state,
        int baseVersion,
        boolean linearHistory,
        boolean conversationsResolved
    ) {
        PullRequest {
            if (id <= 0 || repositoryId <= 0 || authorId <= 0) {
                throw new IllegalArgumentException("Invalid pull-request identity");
            }
            if (title == null || title.isBlank()) {
                throw new IllegalArgumentException("Title is required");
            }
            if (sourceBranch == null || sourceBranch.isBlank() ||
                targetBranch == null || targetBranch.isBlank()) {
                throw new IllegalArgumentException("Both branches are required");
            }
            if (sourceBranch.equals(targetBranch)) {
                throw new IllegalArgumentException(
                    "Source and target branches must differ"
                );
            }
            Objects.requireNonNull(state, "state");
        }
    }

    record Review(
        int pullRequestId,
        int reviewerId,
        ReviewState state,
        int reviewedBaseVersion,
        boolean discussionResolved
    ) {
        Review {
            if (pullRequestId <= 0 || reviewerId <= 0) {
                throw new IllegalArgumentException("Invalid review identity");
            }
            Objects.requireNonNull(state, "state");
        }
    }

    record StatusCheck(
        int pullRequestId,
        String name,
        CheckState state
    ) {
        StatusCheck {
            if (pullRequestId <= 0 || name == null || name.isBlank()) {
                throw new IllegalArgumentException("Invalid status check");
            }
            Objects.requireNonNull(state, "state");
        }
    }

    record Eligibility(
        boolean eligible,
        int validApprovalCount,
        List<String> reasons
    ) {
        Eligibility {
            reasons = List.copyOf(reasons);
        }
    }

    static final class GovernanceException extends RuntimeException {
        GovernanceException(String message) {
            super(message);
        }
    }

    static final class RepositoryService {
        private final Map<Integer, Developer> developers = new HashMap<>();
        private final Map<Integer, Repository> repositories = new HashMap<>();
        private final Map<Integer, PullRequest> pullRequests = new HashMap<>();
        private final List<Review> reviews = new ArrayList<>();
        private final List<StatusCheck> checks = new ArrayList<>();
        private final Map<Integer, Map<Integer, Permission>> permissions =
            new HashMap<>();
        private final Set<Integer> administratorBypasses = new HashSet<>();

        void registerDeveloper(Developer developer) {
            if (developers.putIfAbsent(developer.id(), developer) != null) {
                throw new IllegalArgumentException("Duplicate developer ID");
            }
        }

        void registerRepository(Repository repository) {
            if (repositories.putIfAbsent(repository.id(), repository) != null) {
                throw new IllegalArgumentException("Duplicate repository ID");
            }
        }

        void registerPullRequest(PullRequest request) {
            if (!repositories.containsKey(request.repositoryId())) {
                throw new IllegalArgumentException("Unknown repository");
            }
            if (!developers.containsKey(request.authorId())) {
                throw new IllegalArgumentException("Unknown pull-request author");
            }
            if (pullRequests.putIfAbsent(request.id(), request) != null) {
                throw new IllegalArgumentException("Duplicate pull-request ID");
            }
        }

        void addReview(Review review) {
            if (!pullRequests.containsKey(review.pullRequestId())) {
                throw new IllegalArgumentException("Unknown pull request");
            }
            if (!developers.containsKey(review.reviewerId())) {
                throw new IllegalArgumentException("Unknown reviewer");
            }
            reviews.add(review);
        }

        void addCheck(StatusCheck check) {
            if (!pullRequests.containsKey(check.pullRequestId())) {
                throw new IllegalArgumentException("Unknown pull request");
            }
            checks.add(check);
        }

        void grantPermission(
            int repositoryId,
            int developerId,
            Permission permission
        ) {
            if (!repositories.containsKey(repositoryId) ||
                !developers.containsKey(developerId)) {
                throw new IllegalArgumentException("Unknown repository or developer");
            }

            permissions
                .computeIfAbsent(repositoryId, ignored -> new HashMap<>())
                .put(developerId, permission);
        }

        /*
         * A repository may authorize bypasses, but only a registered
         * administrator can invoke one. Bypass is explicitly auditable.
         */
        void recordAdministratorBypass(int pullRequestId, int administratorId) {
            PullRequest request = requirePullRequest(pullRequestId);
            Repository repository = repositories.get(request.repositoryId());

            Permission permission = permissions
                .getOrDefault(repository.id(), Map.of())
                .get(administratorId);

            if (permission != Permission.ADMIN) {
                throw new GovernanceException(
                    "Only a repository administrator may bypass policy"
                );
            }

            if (!repository.allowAdministratorBypass()) {
                throw new GovernanceException("Administrator bypass is disabled");
            }

            administratorBypasses.add(pullRequestId);
        }

        Eligibility evaluate(int pullRequestId) {
            PullRequest request = requirePullRequest(pullRequestId);
            Repository repository = repositories.get(request.repositoryId());
            List<String> reasons = new ArrayList<>();

            if (request.state() == PullRequestState.MERGED) {
                return new Eligibility(
                    false, 0, List.of("Pull request is already merged")
                );
            }

            if (request.state() == PullRequestState.CLOSED) {
                return new Eligibility(
                    false, 0, List.of("Closed pull request cannot be merged")
                );
            }

            if (request.state() == PullRequestState.DRAFT) {
                return new Eligibility(
                    false, 0, List.of("Draft pull request is not mergeable")
                );
            }

            if (!repository.protectedBranch()) {
                reasons.add("Target branch lacks protection");
            }

            if (repository.requireLinearHistory() && !request.linearHistory()) {
                reasons.add("Target requires linear history");
            }

            if (repository.requireResolvedConversations() &&
                !request.conversationsResolved()) {
                reasons.add("Review conversations are unresolved");
            }

            Permission authorPermission = permissions
                .getOrDefault(repository.id(), Map.of())
                .get(request.authorId());

            if (repository.restrictDirectPushes() &&
                (authorPermission == null ||
                 authorPermission == Permission.READ)) {
                reasons.add("Author lacks write access to the repository");
            }

            /*
             * anyMatch() is an existence predicate. It checks whether at
             * least one eligible reviewer has an approval for this exact
             * pull request and base version.
             */
            boolean hasCurrentEligibleApproval = reviews.stream()
                .filter(review -> review.pullRequestId() == request.id())
                .anyMatch(review -> {
                    Developer reviewer = developers.get(review.reviewerId());
                    boolean stale =
                        review.reviewedBaseVersion() != request.baseVersion();

                    return reviewer != null &&
                        reviewer.active() &&
                        reviewer.id() != request.authorId() &&
                        review.state() == ReviewState.APPROVED &&
                        (!repository.dismissStaleApprovals() || !stale);
                });

            if (!hasCurrentEligibleApproval &&
                repository.requiredApprovals() > 0) {
                reasons.add("No current eligible approval exists");
            }

            /*
             * Count distinct reviewer identities, not review events.
             * Multiple review submissions by one person do not create
             * multiple independent approvals.
             */
            Set<Integer> eligibleApprovers = reviews.stream()
                .filter(review -> review.pullRequestId() == request.id())
                .filter(review -> review.state() == ReviewState.APPROVED)
                .filter(review -> {
                    Developer reviewer = developers.get(review.reviewerId());
                    boolean stale =
                        review.reviewedBaseVersion() != request.baseVersion();

                    return reviewer != null &&
                        reviewer.active() &&
                        reviewer.id() != request.authorId() &&
                        (!repository.dismissStaleApprovals() || !stale);
                })
                .map(Review::reviewerId)
                .collect(Collectors.toCollection(TreeSet::new));

            if (eligibleApprovers.size() < repository.requiredApprovals()) {
                reasons.add(
                    "Approval threshold not met: " +
                    eligibleApprovers.size() + "/" +
                    repository.requiredApprovals()
                );
            }

            /*
             * A current changes-requested review is a separate blocking
             * condition. It is not equivalent to an absent approval.
             */
            boolean changesRequested = reviews.stream()
                .filter(review -> review.pullRequestId() == request.id())
                .anyMatch(review -> {
                    Developer reviewer = developers.get(review.reviewerId());
                    return reviewer != null &&
                        reviewer.active() &&
                        reviewer.id() != request.authorId() &&
                        review.state() == ReviewState.CHANGES_REQUESTED &&
                        review.reviewedBaseVersion() == request.baseVersion();
                });

            if (changesRequested) {
                reasons.add("A reviewer has requested changes");
            }

            /*
             * For every required check, there must exist a successful
             * matching check record. noneMatch() identifies a missing
             * or unsuccessful requirement without multiplying PR rows.
             */
            for (String required : repository.requiredChecks()) {
                boolean successExists = checks.stream()
                    .filter(check -> check.pullRequestId() == request.id())
                    .anyMatch(check ->
                        check.name().equals(required) &&
                        check.state() == CheckState.SUCCESS
                    );

                if (!successExists) {
                    reasons.add("Required check missing or unsuccessful: " + required);
                }
            }

            boolean bypassed = administratorBypasses.contains(request.id());

            if (bypassed) {
                return new Eligibility(
                    true,
                    eligibleApprovers.size(),
                    List.of("Authorized administrator bypass recorded")
                );
            }

            return new Eligibility(
                reasons.isEmpty(),
                eligibleApprovers.size(),
                reasons
            );
        }

        void merge(int pullRequestId) {
            PullRequest request = requirePullRequest(pullRequestId);
            Eligibility decision = evaluate(pullRequestId);

            if (!decision.eligible()) {
                throw new GovernanceException(
                    "Merge rejected: " + String.join("; ", decision.reasons())
                );
            }

            /*
             * This in-memory transition demonstrates the domain rule.
             * Production persistence must re-check policy atomically to
             * avoid a race between eligibility evaluation and merge.
             */
            pullRequests.put(
                request.id(),
                new PullRequest(
                    request.id(),
                    request.repositoryId(),
                    request.authorId(),
                    request.title(),
                    request.sourceBranch(),
                    request.targetBranch(),
                    PullRequestState.MERGED,
                    request.baseVersion(),
                    request.linearHistory(),
                    request.conversationsResolved()
                )
            );

            administratorBypasses.remove(pullRequestId);
        }

        void close(int pullRequestId) {
            PullRequest request = requirePullRequest(pullRequestId);

            if (request.state() != PullRequestState.OPEN &&
                request.state() != PullRequestState.DRAFT) {
                throw new GovernanceException(
                    "Only open or draft pull requests can be closed"
                );
            }

            pullRequests.put(
                request.id(),
                new PullRequest(
                    request.id(),
                    request.repositoryId(),
                    request.authorId(),
                    request.title(),
                    request.sourceBranch(),
                    request.targetBranch(),
                    PullRequestState.CLOSED,
                    request.baseVersion(),
                    request.linearHistory(),
                    request.conversationsResolved()
                )
            );
        }

        private PullRequest requirePullRequest(int id) {
            PullRequest request = pullRequests.get(id);
            if (request == null) {
                throw new IllegalArgumentException("Unknown pull request: " + id);
            }
            return request;
        }
    }

    private static RepositoryService createExampleService() {
        RepositoryService service = new RepositoryService();

        service.registerDeveloper(new Developer(1, "Asha", "Platform", true));
        service.registerDeveloper(new Developer(2, "Ravi", "Platform", true));
        service.registerDeveloper(new Developer(3, "Meera", "Security", true));
        service.registerDeveloper(new Developer(4, "Kabir", "Quality", true));
        service.registerDeveloper(
            new Developer(5, "InactiveReviewer", "Platform", false)
        );

        service.registerRepository(new Repository(
            1,
            "deployment-service",
            true,
            2,
            true,
            true,
            true,
            true,
            true,
            true,
            false,
            Set.of("unit-tests", "security-scan")
        ));

        service.registerRepository(new Repository(
            2,
            "security-scanner",
            true,
            1,
            false,
            true,
            true,
            true,
            true,
            false,
            true,
            Set.of("unit-tests")
        ));

        service.grantPermission(1, 1, Permission.WRITE);
        service.grantPermission(1, 2, Permission.WRITE);
        service.grantPermission(1, 3, Permission.MAINTAIN);
        service.grantPermission(2, 3, Permission.ADMIN);
        service.grantPermission(2, 4, Permission.MAINTAIN);

        service.registerPullRequest(new PullRequest(
            101, 1, 1, "Improve deployment retries",
            "feature/retry-policy", "main",
            PullRequestState.OPEN, 7, true, true
        ));

        service.registerPullRequest(new PullRequest(
            102, 1, 2, "Add rollback support",
            "feature/rollback", "main",
            PullRequestState.OPEN, 7, true, true
        ));

        service.registerPullRequest(new PullRequest(
            103, 1, 1, "Draft health endpoint",
            "feature/health", "main",
            PullRequestState.DRAFT, 7, true, false
        ));

        service.registerPullRequest(new PullRequest(
            201, 2, 3, "Fix scanner validation",
            "fix/scanner-validation", "main",
            PullRequestState.OPEN, 4, true, true
        ));

        service.addReview(new Review(101, 2, ReviewState.APPROVED, 7, true));
        service.addReview(new Review(101, 3, ReviewState.APPROVED, 7, true));
        service.addReview(new Review(102, 3, ReviewState.CHANGES_REQUESTED, 7, false));
        service.addReview(new Review(102, 4, ReviewState.APPROVED, 7, true));
        service.addReview(new Review(201, 4, ReviewState.APPROVED, 4, true));
        service.addReview(new Review(201, 5, ReviewState.APPROVED, 4, true));

        service.addCheck(new StatusCheck(101, "unit-tests", CheckState.SUCCESS));
        service.addCheck(new StatusCheck(101, "security-scan", CheckState.SUCCESS));
        service.addCheck(new StatusCheck(102, "unit-tests", CheckState.SUCCESS));
        service.addCheck(new StatusCheck(102, "security-scan", CheckState.FAILURE));
        service.addCheck(new StatusCheck(201, "unit-tests", CheckState.SUCCESS));

        return service;
    }

    public static void main(String[] args) {
        RepositoryService service = createExampleService();

        for (int pullRequestId : List.of(101, 102, 103, 201)) {
            Eligibility result = service.evaluate(pullRequestId);

            System.out.println("\nPull request #" + pullRequestId);
            System.out.println("Merge eligible: " + result.eligible());
            System.out.println("Valid distinct approvals: " + result.validApprovalCount());

            if (result.reasons().isEmpty()) {
                System.out.println("All governance requirements are satisfied.");
            } else {
                result.reasons().forEach(reason -> System.out.println(" - " + reason));
            }
        }

        service.merge(101);
        System.out.println("\nPull request #101 merged.");

        try {
            service.merge(102);
            throw new AssertionError("Expected merge rejection");
        } catch (GovernanceException expected) {
            System.out.println("Pull request #102 rejected: " + expected.getMessage());
        }

        try {
            service.close(101);
            throw new AssertionError("A merged request must not be closed again");
        } catch (GovernanceException expected) {
            System.out.println("Invalid state transition rejected.");
        }
    }
}
