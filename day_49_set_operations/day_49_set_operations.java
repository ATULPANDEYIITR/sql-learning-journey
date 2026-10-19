import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.Predicate;
import java.util.stream.Collectors;

public class SetOperationsEnterpriseDemo {

    enum SourceSystem {
        CRM,
        BILLING,
        SUPPORT,
        PRODUCT
    }

    record Customer(String id, String email, SourceSystem source) {
        public Customer {
            if (id == null || id.isBlank()) {
                throw new IllegalArgumentException("Customer id is required");
            }
            if (email == null || !email.contains("@")) {
                throw new IllegalArgumentException("Valid email is required");
            }
            if (source == null) {
                throw new IllegalArgumentException("Source system is required");
            }
        }
    }

    static final class AudienceRepository {
        private final Map<SourceSystem, Set<String>> audiences =
                new java.util.EnumMap<>(SourceSystem.class);

        void register(SourceSystem source, Set<String> emails) {
            if (emails == null || emails.isEmpty()) {
                throw new IllegalArgumentException("Audience cannot be empty");
            }

            if (audiences.containsKey(source)) {
                throw new IllegalStateException(
                        "Audience already registered for " + source
                );
            }

            audiences.put(source, Set.copyOf(emails));
        }

        Set<String> union(SourceSystem first, SourceSystem second) {
            Set<String> result = new TreeSet<>(get(first));
            result.addAll(get(second));
            return result;
        }

        Set<String> intersect(SourceSystem first, SourceSystem second) {
            Set<String> result = new TreeSet<>(get(first));
            result.retainAll(get(second));
            return result;
        }

        Set<String> except(SourceSystem first, SourceSystem second) {
            Set<String> result = new TreeSet<>(get(first));
            result.removeAll(get(second));
            return result;
        }

        Set<String> allSources() {
            return audiences.values()
                    .stream()
                    .flatMap(Set::stream)
                    .collect(Collectors.toCollection(TreeSet::new));
        }

        Set<String> commonToEverySource() {
            if (audiences.isEmpty()) {
                return Set.of();
            }

            Set<String> result = new TreeSet<>(audiences.values().iterator().next());

            for (Set<String> audience : audiences.values()) {
                result.retainAll(audience);
            }

            return result;
        }

        Map<String, Long> sourceCoverage() {
            return audiences.values()
                    .stream()
                    .flatMap(Set::stream)
                    .collect(Collectors.groupingBy(
                            email -> email,
                            TreeMapCompat::new,
                            Collectors.counting()
                    ));
        }

        private Set<String> get(SourceSystem source) {
            Set<String> audience = audiences.get(source);

            if (audience == null) {
                throw new IllegalArgumentException(
                        "No audience registered for " + source
                );
            }

            return audience;
        }
    }

    /*
     * A custom map factory keeps the coverage report deterministic without
     * requiring callers to know the implementation used by the repository.
     */
    static final class TreeMapCompat extends java.util.TreeMap<String, Long> {
    }

    static Set<String> distinct(String... values) {
        Set<String> result = new LinkedHashSet<>();

        for (String value : values) {
            if (value == null || value.isBlank()) {
                throw new IllegalArgumentException(
                        "Set members cannot be null or blank"
                );
            }

            result.add(value.trim().toLowerCase());
        }

        return result;
    }

    static List<String> unionAll(List<String> first, List<String> second) {
        /*
         * UNION ALL is sequence-oriented. Keeping List rather than Set is
         * intentional because duplicate occurrences are part of the result.
         */
        List<String> result = new ArrayList<>(first.size() + second.size());
        result.addAll(first);
        result.addAll(second);
        return result;
    }

    static Set<String> filter(Set<String> values, Predicate<String> rule) {
        return values.stream()
                .filter(rule)
                .collect(Collectors.toCollection(TreeSet::new));
    }

    static void print(String label, Set<String> values) {
        System.out.println(label + ": " + values);
    }

    public static void main(String[] args) {
        System.out.println("Enterprise Set Operations Model\n");

        AudienceRepository repository = new AudienceRepository();

        repository.register(
                SourceSystem.CRM,
                distinct(
                        "alice@example.com",
                        "bob@example.com",
                        "carol@example.com",
                        "david@example.com"
                )
        );

        repository.register(
                SourceSystem.BILLING,
                distinct(
                        "bob@example.com",
                        "carol@example.com",
                        "erin@example.com"
                )
        );

        repository.register(
                SourceSystem.SUPPORT,
                distinct(
                        "carol@example.com",
                        "david@example.com",
                        "frank@example.com"
                )
        );

        repository.register(
                SourceSystem.PRODUCT,
                distinct(
                        "alice@example.com",
                        "carol@example.com",
                        "frank@example.com"
                )
        );

        print(
                "CRM UNION Billing",
                repository.union(SourceSystem.CRM, SourceSystem.BILLING)
        );

        print(
                "CRM INTERSECT Billing",
                repository.intersect(SourceSystem.CRM, SourceSystem.BILLING)
        );

        print(
                "CRM EXCEPT Billing",
                repository.except(SourceSystem.CRM, SourceSystem.BILLING)
        );

        print(
                "All registered customers",
                repository.allSources()
        );

        print(
                "Customers common to every source",
                repository.commonToEverySource()
        );

        System.out.println("\nSource coverage:");

        repository.sourceCoverage().forEach(
                (email, count) -> System.out.println(
                        "  " + email + ": " + count + " source(s)"
                )
        );

        Set<String> enterpriseCandidates = filter(
                repository.union(SourceSystem.CRM, SourceSystem.PRODUCT),
                email -> email.startsWith("a") || email.startsWith("c")
        );

        print(
                "Filtered union result",
                enterpriseCandidates
        );

        List<String> crmExport = List.of(
                "alice@example.com",
                "alice@example.com",
                "bob@example.com"
        );

        List<String> billingExport = List.of(
                "bob@example.com",
                "carol@example.com"
        );

        System.out.println(
                "\nUNION ALL export: "
                        + unionAll(crmExport, billingExport)
        );

        Set<SourceSystem> activeSystems =
                EnumSet.of(SourceSystem.CRM, SourceSystem.PRODUCT);

        System.out.println(
                "\nActive source systems: " + activeSystems
        );

        Customer customer = new Customer(
                "C-1001",
                "alice@example.com",
                SourceSystem.CRM
        );

        System.out.println(
                "\nValidated domain record: " + customer
        );

        try {
            repository.register(
                    SourceSystem.CRM,
                    Collections.singleton("another@example.com")
            );
        } catch (IllegalStateException error) {
            System.out.println(
                    "Expected state error: " + error.getMessage()
            );
        }

        try {
            new Customer("", "invalid@example.com", SourceSystem.CRM);
        } catch (IllegalArgumentException error) {
            System.out.println(
                    "Expected validation error: " + error.getMessage()
            );
        }

        System.out.println(
                "\nSet-based operations are appropriate when membership and "
                        + "distinctness matter. List-based UNION ALL is retained "
                        + "separately because occurrence count is significant."
        );
    }
}
