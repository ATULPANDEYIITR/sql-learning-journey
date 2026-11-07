import java.security.SecureRandom;
import java.util.*;
import java.util.stream.Collectors;

public class SurrogateNaturalKeys {

    enum KeyStrategy {
        IDENTITY,
        UUID,
        NATURAL
    }

    enum CustomerStatus {
        ACTIVE,
        SUSPENDED,
        CLOSED
    }

    enum OrderStatus {
        CREATED,
        CONFIRMED,
        CANCELLED
    }

    static class ValidationException extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    static class DuplicateKeyException extends RuntimeException {
        DuplicateKeyException(String message) {
            super(message);
        }
    }

    static class NotFoundException extends RuntimeException {
        NotFoundException(String message) {
            super(message);
        }
    }

    static class IntegrityException extends RuntimeException {
        IntegrityException(String message) {
            super(message);
        }
    }

    record CustomerId(long value) {
        CustomerId {
            if (value <= 0) {
                throw new ValidationException("Invalid customer identity.");
            }
        }
    }

    record PublicCustomerId(UUID value) {
        PublicCustomerId {
            Objects.requireNonNull(value, "UUID cannot be null.");
        }
    }

    record NaturalCustomerKey(
        String countryCode,
        String businessIdentifier
    ) {
        NaturalCustomerKey {
            countryCode = normalizeCountry(countryCode);
            businessIdentifier = requireText(
                businessIdentifier,
                "Business identifier"
            );

            if (!businessIdentifier.matches("[A-Za-z0-9-]{4,40}")) {
                throw new ValidationException(
                    "Invalid business identifier."
                );
            }
        }
    }

    record Customer(
        CustomerId id,
        PublicCustomerId publicId,
        String email,
        String name,
        String country,
        CustomerStatus status
    ) {
        Customer {
            Objects.requireNonNull(id);
            Objects.requireNonNull(publicId);
            Objects.requireNonNull(status);

            email = normalizeEmail(email);
            name = requireText(name, "Customer name");
            country = normalizeCountry(country);
        }

        Customer withEmail(String newEmail) {
            return new Customer(
                id,
                publicId,
                newEmail,
                name,
                country,
                status
            );
        }

        Customer withStatus(CustomerStatus newStatus) {
            return new Customer(
                id,
                publicId,
                email,
                name,
                country,
                newStatus
            );
        }
    }

    record Order(
        long orderId,
        CustomerId customerId,
        BigDecimalAmount amount,
        OrderStatus status
    ) {}

    record BigDecimalAmount(java.math.BigDecimal value) {
        BigDecimalAmount {
            Objects.requireNonNull(value);

            if (value.signum() <= 0) {
                throw new ValidationException(
                    "Order amount must be positive."
                );
            }
        }

        static BigDecimalAmount of(String amount) {
            try {
                return new BigDecimalAmount(
                    new java.math.BigDecimal(amount)
                );
            } catch (NumberFormatException exception) {
                throw new ValidationException("Invalid monetary amount.");
            }
        }
    }

    interface KeyGenerator<T> {
        T generate();
    }

    static class IdentityGenerator implements KeyGenerator<CustomerId> {
        private long nextValue = 1;

        @Override
        public synchronized CustomerId generate() {
            return new CustomerId(nextValue++);
        }
    }

    static class UUIDGenerator implements KeyGenerator<PublicCustomerId> {
        private final SecureRandom random = new SecureRandom();

        @Override
        public PublicCustomerId generate() {
            byte[] bytes = new byte[16];
            random.nextBytes(bytes);

            // Apply RFC 4122 UUID version 4 and variant bits.
            bytes[6] = (byte) ((bytes[6] & 0x0F) | 0x40);
            bytes[8] = (byte) ((bytes[8] & 0x3F) | 0x80);

            java.nio.ByteBuffer buffer =
                java.nio.ByteBuffer.wrap(bytes);

            return new PublicCustomerId(
                new UUID(buffer.getLong(), buffer.getLong())
            );
        }
    }

    static String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new ValidationException(field + " is required.");
        }

        return value.trim();
    }

    static String normalizeEmail(String email) {
        String value = requireText(email, "Email").toLowerCase(Locale.ROOT);

        if (!value.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")) {
            throw new ValidationException("Invalid email address.");
        }

        return value;
    }

    static String normalizeCountry(String country) {
        String value = requireText(country, "Country code")
            .toUpperCase(Locale.ROOT);

        if (!value.matches("[A-Z]{2}")) {
            throw new ValidationException(
                "Country code must contain two letters."
            );
        }

        return value;
    }

    static class CustomerRepository {
        private final IdentityGenerator identityGenerator =
            new IdentityGenerator();

        private final UUIDGenerator uuidGenerator =
            new UUIDGenerator();

        private final Map<CustomerId, Customer> customers =
            new HashMap<>();

        private final Map<PublicCustomerId, CustomerId> uuidIndex =
            new HashMap<>();

        private final Map<String, CustomerId> emailIndex =
            new HashMap<>();

        public synchronized Customer create(
            String email,
            String name,
            String country
        ) {
            String normalizedEmail = normalizeEmail(email);
            String normalizedName = requireText(name, "Customer name");
            String normalizedCountry = normalizeCountry(country);

            if (emailIndex.containsKey(normalizedEmail)) {
                throw new DuplicateKeyException("Email already exists.");
            }

            CustomerId id = identityGenerator.generate();
            PublicCustomerId uuid = uuidGenerator.generate();

            Customer customer = new Customer(
                id,
                uuid,
                normalizedEmail,
                normalizedName,
                normalizedCountry,
                CustomerStatus.ACTIVE
            );

            customers.put(id, customer);
            uuidIndex.put(uuid, id);
            emailIndex.put(normalizedEmail, id);

            return customer;
        }

        public synchronized Customer findById(CustomerId id) {
            Customer customer = customers.get(id);

            if (customer == null) {
                throw new NotFoundException("Customer not found.");
            }

            return customer;
        }

        public synchronized Customer findByUUID(PublicCustomerId uuid) {
            CustomerId id = uuidIndex.get(uuid);

            if (id == null) {
                throw new NotFoundException("UUID not found.");
            }

            return findById(id);
        }

        public synchronized Customer findByEmail(String email) {
            String normalized = normalizeEmail(email);
            CustomerId id = emailIndex.get(normalized);

            if (id == null) {
                throw new NotFoundException("Email not found.");
            }

            return findById(id);
        }

        public synchronized Customer updateEmail(
            CustomerId id,
            String newEmail
        ) {
            Customer customer = findById(id);
            String normalized = normalizeEmail(newEmail);

            CustomerId existingId = emailIndex.get(normalized);

            if (existingId != null && !existingId.equals(id)) {
                throw new DuplicateKeyException(
                    "Email already belongs to another customer."
                );
            }

            emailIndex.remove(customer.email());

            Customer updated = customer.withEmail(normalized);

            customers.put(id, updated);
            emailIndex.put(normalized, id);

            return updated;
        }

        public synchronized Customer updateStatus(
            CustomerId id,
            CustomerStatus status
        ) {
            Customer customer = findById(id);

            Customer updated = customer.withStatus(status);

            customers.put(id, updated);
            return updated;
        }

        public synchronized List<Customer> all() {
            return List.copyOf(customers.values());
        }

        public synchronized long count() {
            return customers.size();
        }
    }

    static class NaturalKeyRepository {
        private final Map<NaturalCustomerKey, String> records =
            new HashMap<>();

        public synchronized void register(
            NaturalCustomerKey key,
            String companyName
        ) {
            String name = requireText(companyName, "Company name");

            if (records.containsKey(key)) {
                throw new DuplicateKeyException(
                    "Natural composite key already exists."
                );
            }

            records.put(key, name);
        }

        public synchronized String find(NaturalCustomerKey key) {
            String value = records.get(key);

            if (value == null) {
                throw new NotFoundException("Natural key not found.");
            }

            return value;
        }

        public synchronized long count() {
            return records.size();
        }
    }

    static class OrderService {
        private final CustomerRepository customers;
        private final Map<Long, Order> orders = new HashMap<>();
        private long nextOrderId = 1;

        OrderService(CustomerRepository customers) {
            this.customers = Objects.requireNonNull(customers);
        }

        public synchronized Order create(
            CustomerId customerId,
            BigDecimalAmount amount
        ) {
            Customer customer = customers.findById(customerId);

            if (customer.status() != CustomerStatus.ACTIVE) {
                throw new IntegrityException(
                    "Customer is not eligible to place orders."
                );
            }

            Order order = new Order(
                nextOrderId++,
                customerId,
                amount,
                OrderStatus.CREATED
            );

            orders.put(order.orderId(), order);
            return order;
        }

        public synchronized List<Order> findByCustomer(
            CustomerId customerId
        ) {
            customers.findById(customerId);

            return orders.values()
                .stream()
                .filter(order -> order.customerId().equals(customerId))
                .sorted(Comparator.comparingLong(Order::orderId))
                .toList();
        }

        public synchronized long totalOrders() {
            return orders.size();
        }
    }

    static class KeyPolicy {
        static Map<KeyStrategy, String> descriptions() {
            EnumMap<KeyStrategy, String> policies =
                new EnumMap<>(KeyStrategy.class);

            policies.put(
                KeyStrategy.IDENTITY,
                "Compact database-generated internal identifier"
            );

            policies.put(
                KeyStrategy.UUID,
                "Distributed globally unique identifier"
            );

            policies.put(
                KeyStrategy.NATURAL,
                "Business-derived identifier with uniqueness constraints"
            );

            return Collections.unmodifiableMap(policies);
        }
    }

    static class CustomerService {
        private final CustomerRepository repository;

        CustomerService(CustomerRepository repository) {
            this.repository = repository;
        }

        Customer register(String email, String name, String country) {
            return repository.create(email, name, country);
        }

        Customer changeEmail(CustomerId id, String newEmail) {
            return repository.updateEmail(id, newEmail);
        }
    }

    public static void main(String[] args) {
        try {
            System.out.println("SURROGATE VS NATURAL KEYS");
            System.out.println("=".repeat(60));

            CustomerRepository repository = new CustomerRepository();
            CustomerService service = new CustomerService(repository);

            NaturalKeyRepository naturalRepository =
                new NaturalKeyRepository();

            Customer alice = service.register(
                "alice@example.com",
                "Alice Sharma",
                "IN"
            );

            Customer bob = service.register(
                "bob@example.com",
                "Bob Verma",
                "IN"
            );

            System.out.println("\n1. Surrogate identifiers");

            repository.all().forEach(customer ->
                System.out.printf(
                    "ID=%d UUID=%s Email=%s%n",
                    customer.id().value(),
                    customer.publicId().value(),
                    customer.email()
                )
            );

            System.out.println("\n2. UUID retrieval");

            Customer retrieved = repository.findByUUID(alice.publicId());

            System.out.println("Retrieved: " + retrieved.name());

            System.out.println("\n3. Mutable natural attribute");

            Customer updated = service.changeEmail(
                alice.id(),
                "alice.sharma@example.com"
            );

            System.out.println("Updated email: " + updated.email());
            System.out.println(
                "Integer ID preserved: " +
                updated.id().equals(alice.id())
            );
            System.out.println(
                "UUID preserved: " +
                updated.publicId().equals(alice.publicId())
            );

            System.out.println("\n4. Composite natural keys");

            NaturalCustomerKey indianKey =
                new NaturalCustomerKey("IN", "TAX-1001");

            NaturalCustomerKey americanKey =
                new NaturalCustomerKey("US", "TAX-1001");

            naturalRepository.register(
                indianKey,
                "Indian Enterprise"
            );

            naturalRepository.register(
                americanKey,
                "American Enterprise"
            );

            System.out.println(
                "Indian entity: " + naturalRepository.find(indianKey)
            );

            System.out.println(
                "Distinct natural keys: " + naturalRepository.count()
            );

            System.out.println("\n5. Enterprise order workflow");

            OrderService orderService = new OrderService(repository);

            Order firstOrder = orderService.create(
                alice.id(),
                BigDecimalAmount.of("25000.00")
            );

            Order secondOrder = orderService.create(
                bob.id(),
                BigDecimalAmount.of("45000.00")
            );

            System.out.println("Created orders:");
            System.out.println(firstOrder);
            System.out.println(secondOrder);

            System.out.println(
                "Alice order count: " +
                orderService.findByCustomer(alice.id()).size()
            );

            System.out.println("\n6. Duplicate natural key");

            try {
                naturalRepository.register(
                    indianKey,
                    "Duplicate Enterprise"
                );
            } catch (DuplicateKeyException exception) {
                System.out.println("Rejected: " + exception.getMessage());
            }

            System.out.println("\n7. Invalid customer lookup");

            try {
                repository.findById(new CustomerId(999));
            } catch (NotFoundException exception) {
                System.out.println("Handled: " + exception.getMessage());
            }

            System.out.println("\n8. Customer state enforcement");

            repository.updateStatus(
                bob.id(),
                CustomerStatus.SUSPENDED
            );

            try {
                orderService.create(
                    bob.id(),
                    BigDecimalAmount.of("1000.00")
                );
            } catch (IntegrityException exception) {
                System.out.println("Rejected: " + exception.getMessage());
            }

            System.out.println("\n9. Key strategy policies");

            KeyPolicy.descriptions().forEach((strategy, description) ->
                System.out.println(strategy + ": " + description)
            );

            System.out.println("\n10. Performance characteristics");

            System.out.println("HashMap indexed lookup: average O(1).");
            System.out.println("Natural composite lookup: average O(1).");
            System.out.println("Identity and UUID storage: separate indexes.");
            System.out.println("Database indexes remain necessary in production.");

            System.out.println("\nCustomer count: " + repository.count());
            System.out.println("Order count: " + orderService.totalOrders());

            System.out.println("\nExecution completed.");

        } catch (RuntimeException exception) {
            System.err.println(
                "Application failure: " + exception.getMessage()
            );
            System.exitCode = 1;
        }
    }
}
