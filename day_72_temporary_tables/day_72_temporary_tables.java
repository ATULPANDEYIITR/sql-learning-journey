import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/*
 * Temporary Tables: enterprise staging and session management.
 *
 * Java 17 implementation featuring:
 * - Explicit session lifecycle.
 * - Immutable domain records.
 * - Validation services.
 * - Batch promotion and rollback.
 * - Repository isolation.
 * - Typed exceptions.
 *
 * Compile:
 * javac TemporaryTables.java
 *
 * Run:
 * java TemporaryTables
 */

public class TemporaryTables {

    enum RecordStatus {
        PENDING,
        ACCEPTED,
        REJECTED
    }

    enum SessionStatus {
        OPEN,
        CLOSED
    }

    record ProductRecord(
        String externalId,
        String product,
        int quantity,
        BigDecimal unitPrice
    ) {
        ProductRecord {
            externalId = externalId == null
                ? ""
                : externalId.trim();

            product = product == null
                ? ""
                : product.trim();

            Objects.requireNonNull(
                unitPrice,
                "Unit price cannot be null"
            );

            if (unitPrice.scale() > 4) {
                throw new IllegalArgumentException(
                    "Unit price supports at most four decimal places"
                );
            }
        }

        BigDecimal totalValue() {
            return unitPrice.multiply(
                BigDecimal.valueOf(quantity)
            ).setScale(2, RoundingMode.HALF_UP);
        }
    }

    record ValidationResult(
        String externalId,
        RecordStatus status,
        String reason
    ) {}

    record PermanentRecord(
        ProductRecord product,
        Instant importedAt
    ) {}

    record AuditEntry(
        String externalId,
        RecordStatus status,
        String reason,
        Instant recordedAt
    ) {}

    static class StagingException extends RuntimeException {
        StagingException(String message) {
            super(message);
        }

        StagingException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    /*
     * Permanent repository.
     *
     * Synchronized operations prevent simultaneous modifications
     * inside this single-process demonstration.
     */
    static class ProductRepository {
        private Map<String, PermanentRecord> products =
            new HashMap<>();

        private final List<AuditEntry> audit =
            new ArrayList<>();

        public synchronized boolean exists(String id) {
            return products.containsKey(id);
        }

        public synchronized int promote(
            List<ProductRecord> records,
            List<ValidationResult> results
        ) {
            // Copy-on-write provides atomic replacement in this model.
            Map<String, PermanentRecord> candidate =
                new HashMap<>(products);

            for (ProductRecord record : records) {
                if (candidate.containsKey(record.externalId())) {
                    throw new StagingException(
                        "Duplicate permanent identifier: "
                        + record.externalId()
                    );
                }

                candidate.put(
                    record.externalId(),
                    new PermanentRecord(record, Instant.now())
                );
            }

            products = candidate;

            for (ValidationResult result : results) {
                audit.add(new AuditEntry(
                    result.externalId(),
                    result.status(),
                    result.reason(),
                    Instant.now()
                ));
            }

            return records.size();
        }

        public synchronized Map<String, PermanentRecord> snapshot() {
            return Collections.unmodifiableMap(
                new HashMap<>(products)
            );
        }

        public synchronized List<AuditEntry> auditSnapshot() {
            return List.copyOf(audit);
        }

        public synchronized BigDecimal inventoryValue() {
            return products.values()
                .stream()
                .map(item -> item.product().totalValue())
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        }
    }

    static class StagingService {
        private final ProductRepository repository;

        private final String sessionId =
            UUID.randomUUID().toString();

        private SessionStatus status = SessionStatus.OPEN;

        private final List<ProductRecord> staging =
            new ArrayList<>();

        private final List<ValidationResult> validation =
            new ArrayList<>();

        private static final int MAX_BATCH_SIZE = 100_000;

        StagingService(ProductRepository repository) {
            this.repository = Objects.requireNonNull(repository);
        }

        private void ensureOpen() {
            if (status != SessionStatus.OPEN) {
                throw new StagingException(
                    "Temporary session is closed"
                );
            }
        }

        public String sessionId() {
            return sessionId;
        }

        public void load(List<ProductRecord> records) {
            ensureOpen();

            if (records == null || records.isEmpty()) {
                throw new StagingException(
                    "Input batch cannot be empty"
                );
            }

            if (records.size() > MAX_BATCH_SIZE) {
                throw new StagingException(
                    "Maximum batch size exceeded"
                );
            }

            if (!staging.isEmpty()) {
                throw new StagingException(
                    "Truncate staging before another load"
                );
            }

            staging.addAll(records);
            validation.clear();
        }

        public List<ValidationResult> validate() {
            ensureOpen();

            validation.clear();

            Set<String> seen = new HashSet<>();

            for (ProductRecord record : staging) {
                String reason = "Valid record";

                if (record.externalId().isBlank()) {
                    reason = "Missing external identifier";
                } else if (record.product().isBlank()) {
                    reason = "Missing product name";
                } else if (record.quantity() <= 0) {
                    reason = "Quantity must be positive";
                } else if (record.unitPrice().signum() < 0) {
                    reason = "Unit price cannot be negative";
                } else if (!seen.add(record.externalId())) {
                    reason = "Duplicate identifier in staging";
                } else if (repository.exists(record.externalId())) {
                    reason = "Identifier already exists";
                }

                RecordStatus recordStatus =
                    reason.equals("Valid record")
                        ? RecordStatus.ACCEPTED
                        : RecordStatus.REJECTED;

                validation.add(new ValidationResult(
                    record.externalId(),
                    recordStatus,
                    reason
                ));
            }

            return List.copyOf(validation);
        }

        public int promote() {
            ensureOpen();

            if (validation.size() != staging.size()) {
                throw new StagingException(
                    "Validate the entire batch before promotion"
                );
            }

            List<ProductRecord> accepted =
                new ArrayList<>();

            for (int i = 0; i < staging.size(); i++) {
                if (validation.get(i).status()
                        == RecordStatus.ACCEPTED) {
                    accepted.add(staging.get(i));
                }
            }

            try {
                return repository.promote(
                    accepted,
                    List.copyOf(validation)
                );
            } catch (RuntimeException exception) {
                throw new StagingException(
                    "Permanent promotion failed",
                    exception
                );
            }
        }

        public void truncate() {
            ensureOpen();
            staging.clear();
            validation.clear();
        }

        public Map<String, Long> validationReport() {
            ensureOpen();

            return validation.stream().collect(
                Collectors.groupingBy(
                    result -> result.status().name(),
                    Collectors.counting()
                )
            );
        }

        public void close() {
            if (status == SessionStatus.CLOSED) {
                return;
            }

            staging.clear();
            validation.clear();
            status = SessionStatus.CLOSED;
        }
    }

    public static void main(String[] args) {
        ProductRepository repository = new ProductRepository();

        StagingService sessionA = new StagingService(repository);

        List<ProductRecord> batch = List.of(
            new ProductRecord(
                "P1001", "Laptop", 5,
                new BigDecimal("75000.00")
            ),
            new ProductRecord(
                "P1002", "Monitor", 10,
                new BigDecimal("12000.00")
            ),
            new ProductRecord(
                "P1003", "Keyboard", 20,
                new BigDecimal("1500.00")
            ),
            new ProductRecord(
                "P1001", "Duplicate Laptop", 2,
                new BigDecimal("70000.00")
            ),
            new ProductRecord(
                "P1004", "Invalid Quantity", 0,
                new BigDecimal("500.00")
            ),
            new ProductRecord(
                "P1005", "Invalid Price", 2,
                new BigDecimal("-100.00")
            )
        );

        try {
            System.out.println(
                "Session A: " + sessionA.sessionId()
            );

            sessionA.load(batch);

            List<ValidationResult> results =
                sessionA.validate();

            System.out.println("\nValidation results");

            results.forEach(System.out::println);

            int inserted = sessionA.promote();

            System.out.println(
                "\nPromoted records: " + inserted
            );

            System.out.println(
                "Validation report: "
                + sessionA.validationReport()
            );

            // Reuse the same temporary staging workflow.
            sessionA.truncate();

            sessionA.load(List.of(
                new ProductRecord(
                    "P1006", "Mouse", 15,
                    new BigDecimal("800.00")
                )
            ));

            sessionA.validate();

            System.out.println(
                "Second batch inserted: "
                + sessionA.promote()
            );

            // Another session has independent staging.
            StagingService sessionB =
                new StagingService(repository);

            sessionB.load(List.of(
                new ProductRecord(
                    "P1007", "Webcam", 4,
                    new BigDecimal("2500.00")
                )
            ));

            sessionB.validate();

            System.out.println(
                "Session B inserted: "
                + sessionB.promote()
            );

            sessionB.close();

            System.out.println("\nPermanent inventory");

            repository.snapshot().forEach(
                (id, record) -> System.out.println(
                    id + " | "
                    + record.product().product()
                    + " | "
                    + record.product().totalValue()
                )
            );

            System.out.println(
                "\nTotal inventory value: "
                + repository.inventoryValue()
            );

            System.out.println(
                "Audit entries: "
                + repository.auditSnapshot().size()
            );

            // Session A still exists, but its staging was truncated.
            System.out.println(
                "Session A validation after new batch: "
                + sessionA.validationReport()
            );

        } catch (StagingException exception) {
            System.err.println(
                "Staging failure: " + exception.getMessage()
            );
        } finally {
            sessionA.close();
        }

        // Closed sessions cannot access temporary data.
        try {
            sessionA.validationReport();
            throw new IllegalStateException(
                "Closed session protection failed"
            );
        } catch (StagingException expected) {
            System.out.println(
                "\nClosed session protection: verified"
            );
        }
    }
}
