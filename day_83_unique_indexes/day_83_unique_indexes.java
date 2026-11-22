import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.TreeMap;
import java.util.function.Predicate;
import java.util.function.Function;

public class UniqueIndexEnterprise {

    enum IndexKind {
        UNIQUE,
        COMPOSITE,
        PARTIAL,
        EXPRESSION
    }

    enum AccountStatus {
        ACTIVE,
        INACTIVE,
        SUSPENDED
    }

    record Account(
        long id,
        long tenantId,
        String email,
        String username,
        AccountStatus status
    ) {}

    record IndexKey(List<Object> values) {
        IndexKey {
            values = Collections.unmodifiableList(
                new ArrayList<>(values)
            );
        }
    }

    static class UniqueConstraintException extends RuntimeException {
        UniqueConstraintException(String message) {
            super(message);
        }
    }

    static class DomainValidationException extends RuntimeException {
        DomainValidationException(String message) {
            super(message);
        }
    }

    static String normalize(String value) {
        if (value == null || value.isBlank()) {
            throw new DomainValidationException(
                "Index values cannot be blank"
            );
        }

        return value.trim().toLowerCase();
    }

    /*
     * A reusable index abstraction.
     *
     * The predicate implements partial-index membership.
     * The key extractor supports simple, composite and expression keys.
     */
    static final class UniqueIndex {

        private final String name;
        private final IndexKind kind;
        private final Function<Account, IndexKey> extractor;
        private final Predicate<Account> predicate;
        private final Map<IndexKey, Long> entries = new HashMap<>();

        UniqueIndex(
            String name,
            IndexKind kind,
            Function<Account, IndexKey> extractor,
            Predicate<Account> predicate
        ) {
            this.name = Objects.requireNonNull(name);
            this.kind = Objects.requireNonNull(kind);
            this.extractor = Objects.requireNonNull(extractor);
            this.predicate = Objects.requireNonNull(predicate);
        }

        Optional<IndexKey> keyFor(Account account) {
            if (!predicate.test(account)) {
                return Optional.empty();
            }

            IndexKey key = extractor.apply(account);

            // Model PostgreSQL-style NULLS DISTINCT behavior.
            if (key.values().stream().anyMatch(Objects::isNull)) {
                return Optional.empty();
            }

            return Optional.of(key);
        }

        void validate(Account candidate, Long ignoredId) {
            Optional<IndexKey> optionalKey = keyFor(candidate);

            if (optionalKey.isEmpty()) return;

            Long owner = entries.get(optionalKey.get());

            if (owner != null && !owner.equals(ignoredId)) {
                throw new UniqueConstraintException(
                    name + " rejects duplicate key " + optionalKey.get()
                );
            }
        }

        void add(Account account) {
            keyFor(account).ifPresent(
                key -> entries.put(key, account.id())
            );
        }

        void remove(Account account) {
            keyFor(account).ifPresent(key -> {
                Long owner = entries.get(key);

                if (Objects.equals(owner, account.id())) {
                    entries.remove(key);
                }
            });
        }

        int size() {
            return entries.size();
        }

        String name() {
            return name;
        }

        IndexKind kind() {
            return kind;
        }

        Map<IndexKey, Long> snapshot() {
            return Map.copyOf(entries);
        }
    }

    static final class AccountRepository {

        private final Map<Long, Account> accounts = new TreeMap<>();
        private final List<UniqueIndex> indexes = new ArrayList<>();

        private long nextId = 1;

        AccountRepository() {

            indexes.add(new UniqueIndex(
                "uq_accounts_email",
                IndexKind.EXPRESSION,
                account -> new IndexKey(
                    List.of(normalize(account.email()))
                ),
                account -> true
            ));

            indexes.add(new UniqueIndex(
                "uq_accounts_tenant_username",
                IndexKind.COMPOSITE,
                account -> new IndexKey(
                    List.of(
                        account.tenantId(),
                        normalize(account.username())
                    )
                ),
                account -> true
            ));

            indexes.add(new UniqueIndex(
                "uq_active_accounts_email",
                IndexKind.PARTIAL,
                account -> new IndexKey(
                    List.of(normalize(account.email()))
                ),
                account -> account.status() == AccountStatus.ACTIVE
            ));
        }

        private void validate(Account account) {
            if (account.id() <= 0 || account.tenantId() <= 0) {
                throw new DomainValidationException(
                    "Identifiers must be positive"
                );
            }

            if (account.email() == null ||
                !account.email().contains("@")) {
                throw new DomainValidationException(
                    "Invalid email address"
                );
            }

            if (account.username() == null ||
                account.username().isBlank()) {
                throw new DomainValidationException(
                    "Username is required"
                );
            }

            Objects.requireNonNull(account.status());
        }

        private void validateIndexes(Account candidate, Long ignoredId) {
            for (UniqueIndex index : indexes) {
                index.validate(candidate, ignoredId);
            }
        }

        Account register(
            long tenantId,
            String email,
            String username
        ) {
            Account candidate = new Account(
                nextId,
                tenantId,
                email.trim(),
                username.trim(),
                AccountStatus.ACTIVE
            );

            validate(candidate);

            if (accounts.containsKey(candidate.id())) {
                throw new UniqueConstraintException(
                    "Primary key already exists"
                );
            }

            validateIndexes(candidate, null);

            accounts.put(candidate.id(), candidate);

            for (UniqueIndex index : indexes) {
                index.add(candidate);
            }

            nextId++;

            return candidate;
        }

        Account changeStatus(long id, AccountStatus status) {
            Account previous = accounts.get(id);

            if (previous == null) {
                throw new DomainValidationException(
                    "Account does not exist"
                );
            }

            Account candidate = new Account(
                previous.id(),
                previous.tenantId(),
                previous.email(),
                previous.username(),
                status
            );

            validate(candidate);
            validateIndexes(candidate, id);

            for (UniqueIndex index : indexes) {
                index.remove(previous);
            }

            accounts.put(id, candidate);

            for (UniqueIndex index : indexes) {
                index.add(candidate);
            }

            return candidate;
        }

        Account updateEmail(long id, String email) {
            Account previous = accounts.get(id);

            if (previous == null) {
                throw new DomainValidationException(
                    "Account does not exist"
                );
            }

            Account candidate = new Account(
                id,
                previous.tenantId(),
                email.trim(),
                previous.username(),
                previous.status()
            );

            validate(candidate);
            validateIndexes(candidate, id);

            for (UniqueIndex index : indexes) {
                index.remove(previous);
            }

            accounts.put(id, candidate);

            for (UniqueIndex index : indexes) {
                index.add(candidate);
            }

            return candidate;
        }

        Optional<Account> findByEmail(String email) {
            String normalized = normalize(email);

            return accounts.values()
                .stream()
                .filter(account ->
                    normalize(account.email()).equals(normalized)
                )
                .findFirst();
        }

        boolean auditIndexes() {
            AccountRepository rebuilt = new AccountRepository();

            try {
                for (Account account : accounts.values()) {
                    rebuilt.accounts.put(account.id(), account);

                    for (UniqueIndex index : rebuilt.indexes) {
                        index.validate(account, null);
                        index.add(account);
                    }
                }
            } catch (RuntimeException exception) {
                return false;
            }

            for (int i = 0; i < indexes.size(); i++) {
                if (!indexes.get(i).snapshot().equals(
                    rebuilt.indexes.get(i).snapshot()
                )) {
                    return false;
                }
            }

            return true;
        }

        void report() {
            System.out.println("\nRepository index report:");

            for (UniqueIndex index : indexes) {
                System.out.println(
                    index.name() + " | " +
                    index.kind() + " | entries=" + index.size()
                );
            }

            System.out.println("Account count: " + accounts.size());
        }
    }

    public static void main(String[] args) {

        AccountRepository repository = new AccountRepository();

        try {
            repository.register(
                100, "alice@example.com", "alice"
            );

            repository.register(
                200, "bob@example.com", "alice"
            );

            repository.register(
                100, "charlie@example.com", "charlie"
            );

            try {
                repository.register(
                    300, "ALICE@example.com", "alice_new"
                );
            } catch (UniqueConstraintException exception) {
                System.out.println(
                    "Expected uniqueness failure: " +
                    exception.getMessage()
                );
            }

            repository.changeStatus(1, AccountStatus.INACTIVE);

            // The global email index still reserves the original address.
            try {
                repository.register(
                    300, "alice@example.com", "new_alice"
                );
            } catch (UniqueConstraintException exception) {
                System.out.println(
                    "Global uniqueness enforced: " +
                    exception.getMessage()
                );
            }

            repository.changeStatus(3, AccountStatus.SUSPENDED);

            System.out.println(
                "\nEmail lookup: " +
                repository.findByEmail("BOB@example.com")
            );

            System.out.println(
                "Index audit: " + repository.auditIndexes()
            );

            repository.report();

            try {
                repository.register(
                    400, "invalid-email", "invalid"
                );
            } catch (DomainValidationException exception) {
                System.out.println(
                    "Validation failure: " + exception.getMessage()
                );
            }

        } catch (RuntimeException exception) {
            System.err.println(
                "Repository operation failed: " +
                exception.getMessage()
            );

            System.exit(1);
        }
    }
}
