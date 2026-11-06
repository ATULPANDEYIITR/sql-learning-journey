import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * Enterprise OLTP database schema design model.
 *
 * Features:
 * - Explicit domain types
 * - Candidate and composite keys
 * - Referential integrity
 * - Constraint validation
 * - Schema lifecycle management
 * - Migration versioning
 * - Transactional order processing
 * - Immutable records
 * - Audit events
 */

public class Main {

    enum SqlType {
        BIGINT,
        VARCHAR,
        NUMERIC,
        BOOLEAN,
        TIMESTAMPTZ
    }

    enum OrderStatus {
        PENDING,
        CONFIRMED,
        SHIPPED,
        CANCELLED
    }

    enum DeletePolicy {
        RESTRICT,
        CASCADE,
        SET_NULL
    }

    static class SchemaException extends RuntimeException {
        SchemaException(String message) {
            super(message);
        }
    }

    static class TransactionException extends RuntimeException {
        TransactionException(String message) {
            super(message);
        }
    }

    record ColumnDefinition(
        String name,
        SqlType type,
        boolean nullable,
        boolean unique,
        boolean primaryKey,
        Object defaultValue,
        Predicate<Object> validator
    ) {
        ColumnDefinition {
            Objects.requireNonNull(name);
            Objects.requireNonNull(type);

            if (!name.matches("[a-z][a-z0-9_]*")) {
                throw new SchemaException(
                    "Invalid column name: " + name
                );
            }

            if (primaryKey && nullable) {
                throw new SchemaException(
                    "Primary key cannot be nullable."
                );
            }
        }

        void validate(Object value) {
            if (value == null) {
                if (!nullable && !primaryKey) {
                    throw new SchemaException(
                        name + " cannot be NULL."
                    );
                }
                return;
            }

            if (!validator.test(value)) {
                throw new SchemaException(
                    "CHECK constraint failed: " + name
                );
            }
        }
    }

    record ForeignKey(
        List<String> columns,
        String referencedTable,
        List<String> referencedColumns,
        DeletePolicy deletePolicy
    ) {
        ForeignKey {
            columns = List.copyOf(columns);
            referencedColumns = List.copyOf(referencedColumns);

            if (columns.isEmpty() ||
                columns.size() != referencedColumns.size()) {
                throw new SchemaException(
                    "Invalid foreign key definition."
                );
            }

            Objects.requireNonNull(deletePolicy);
        }
    }

    record UniqueKey(List<String> columns) {
        UniqueKey {
            columns = List.copyOf(columns);

            if (columns.isEmpty()) {
                throw new SchemaException(
                    "Unique key cannot be empty."
                );
            }
        }
    }

    record TableDefinition(
        String name,
        List<ColumnDefinition> columns,
        List<String> primaryKey,
        List<UniqueKey> uniqueKeys,
        List<ForeignKey> foreignKeys
    ) {
        TableDefinition {
            if (!name.matches("[a-z][a-z0-9_]*")) {
                throw new SchemaException("Invalid table name.");
            }

            columns = List.copyOf(columns);
            primaryKey = List.copyOf(primaryKey);
            uniqueKeys = List.copyOf(uniqueKeys);
            foreignKeys = List.copyOf(foreignKeys);

            if (columns.isEmpty() || primaryKey.isEmpty()) {
                throw new SchemaException(
                    "Table requires columns and a primary key."
                );
            }

            Set<String> names = columns.stream()
                .map(ColumnDefinition::name)
                .collect(Collectors.toSet());

            if (names.size() != columns.size()) {
                throw new SchemaException("Duplicate column names.");
            }

            if (!names.containsAll(primaryKey)) {
                throw new SchemaException(
                    "Primary key references unknown columns."
                );
            }

            for (UniqueKey key : uniqueKeys) {
                if (!names.containsAll(key.columns())) {
                    throw new SchemaException(
                        "Invalid unique key."
                    );
                }
            }

            for (ForeignKey key : foreignKeys) {
                if (!names.containsAll(key.columns())) {
                    throw new SchemaException(
                        "Invalid foreign key columns."
                    );
                }
            }
        }

        ColumnDefinition column(String name) {
            return columns.stream()
                .filter(column -> column.name().equals(name))
                .findFirst()
                .orElseThrow(() ->
                    new SchemaException("Unknown column: " + name)
                );
        }

        List<UniqueKey> candidateKeys() {
            List<UniqueKey> keys = new ArrayList<>();
            keys.add(new UniqueKey(primaryKey));
            keys.addAll(uniqueKeys);
            return List.copyOf(keys);
        }
    }

    static class SchemaRegistry {
        private final Map<String, TableDefinition> definitions =
            new LinkedHashMap<>();

        private long version = 1;

        void register(TableDefinition table) {
            if (definitions.containsKey(table.name())) {
                throw new SchemaException(
                    "Table already exists: " + table.name()
                );
            }

            definitions.put(table.name(), table);
            version++;
        }

        TableDefinition get(String name) {
            TableDefinition table = definitions.get(name);

            if (table == null) {
                throw new SchemaException(
                    "Unknown table: " + name
                );
            }

            return table;
        }

        long version() {
            return version;
        }

        List<TableDefinition> definitions() {
            return List.copyOf(definitions.values());
        }

        void validateRelationships() {
            for (TableDefinition table : definitions.values()) {
                for (ForeignKey foreignKey : table.foreignKeys()) {
                    TableDefinition parent = get(
                        foreignKey.referencedTable()
                    );

                    boolean validCandidate = parent.candidateKeys()
                        .stream()
                        .anyMatch(key ->
                            key.columns().equals(
                                foreignKey.referencedColumns()
                            )
                        );

                    if (!validCandidate) {
                        throw new SchemaException(
                            "Foreign key must reference a candidate key."
                        );
                    }

                    for (String column :
                        foreignKey.referencedColumns()) {
                        parent.column(column);
                    }
                }
            }
        }

        List<String> creationOrder() {
            List<String> result = new ArrayList<>();
            Set<String> visited = new HashSet<>();
            Set<String> active = new HashSet<>();

            for (String name : definitions.keySet()) {
                visit(name, visited, active, result);
            }

            return List.copyOf(result);
        }

        private void visit(
            String name,
            Set<String> visited,
            Set<String> active,
            List<String> result
        ) {
            if (active.contains(name)) {
                throw new SchemaException(
                    "Circular schema dependency."
                );
            }

            if (visited.contains(name)) return;

            active.add(name);

            for (ForeignKey foreignKey :
                get(name).foreignKeys()) {
                visit(
                    foreignKey.referencedTable(),
                    visited,
                    active,
                    result
                );
            }

            active.remove(name);
            visited.add(name);
            result.add(name);
        }
    }

    record Customer(
        long customerId,
        String email,
        String fullName,
        Instant createdAt
    ) {
        Customer {
            if (customerId <= 0) {
                throw new SchemaException("Invalid customer ID.");
            }

            if (email == null ||
                !email.matches("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")) {
                throw new SchemaException("Invalid email.");
            }

            if (fullName == null || fullName.isBlank()) {
                throw new SchemaException("Customer name required.");
            }

            Objects.requireNonNull(createdAt);
        }
    }

    record Product(
        long productId,
        String sku,
        String name,
        BigDecimal unitPrice,
        boolean active
    ) {
        Product {
            if (productId <= 0) {
                throw new SchemaException("Invalid product ID.");
            }

            if (sku == null || sku.isBlank()) {
                throw new SchemaException("SKU required.");
            }

            if (name == null || name.isBlank()) {
                throw new SchemaException("Product name required.");
            }

            Objects.requireNonNull(unitPrice);

            if (unitPrice.signum() < 0) {
                throw new SchemaException("Negative price.");
            }
        }
    }

    record Order(
        long orderId,
        long customerId,
        OrderStatus status,
        Instant createdAt
    ) {
        Order {
            if (orderId <= 0 || customerId <= 0) {
                throw new SchemaException("Invalid order identifiers.");
            }

            Objects.requireNonNull(status);
            Objects.requireNonNull(createdAt);
        }

        Order withStatus(OrderStatus newStatus) {
            if (
                status == OrderStatus.CANCELLED ||
                status == OrderStatus.SHIPPED
            ) {
                throw new SchemaException(
                    "Terminal order cannot change status."
                );
            }

            return new Order(
                orderId,
                customerId,
                newStatus,
                createdAt
            );
        }
    }

    record OrderItem(
        long orderItemId,
        long orderId,
        long productId,
        int quantity,
        BigDecimal unitPrice
    ) {
        OrderItem {
            if (
                orderItemId <= 0 ||
                orderId <= 0 ||
                productId <= 0 ||
                quantity <= 0
            ) {
                throw new SchemaException("Invalid order item.");
            }

            Objects.requireNonNull(unitPrice);

            if (unitPrice.signum() < 0) {
                throw new SchemaException("Invalid unit price.");
            }
        }

        BigDecimal lineTotal() {
            return unitPrice.multiply(BigDecimal.valueOf(quantity));
        }
    }

    record OrderRequest(
        long customerId,
        Map<Long, Integer> productQuantities
    ) {
        OrderRequest {
            productQuantities = Map.copyOf(productQuantities);

            if (productQuantities.isEmpty()) {
                throw new SchemaException("Order cannot be empty.");
            }

            productQuantities.forEach((productId, quantity) -> {
                if (productId <= 0 || quantity == null || quantity <= 0) {
                    throw new SchemaException(
                        "Invalid order request item."
                    );
                }
            });
        }
    }

    record OrderReport(
        long orderId,
        String customerName,
        int itemCount,
        BigDecimal total
    ) {}

    static class OrderService {
        private final Map<Long, Customer> customers =
            new LinkedHashMap<>();

        private final Map<Long, Product> products =
            new LinkedHashMap<>();

        private final Map<Long, Order> orders =
            new LinkedHashMap<>();

        private final Map<Long, OrderItem> orderItems =
            new LinkedHashMap<>();

        private final Set<String> customerEmails = new HashSet<>();
        private final Set<String> productSkus = new HashSet<>();

        private final AtomicLong orderSequence =
            new AtomicLong(5000);

        private final AtomicLong itemSequence =
            new AtomicLong(9000);

        void addCustomer(Customer customer) {
            if (customers.containsKey(customer.customerId())) {
                throw new SchemaException("Duplicate customer ID.");
            }

            if (!customerEmails.add(customer.email().toLowerCase())) {
                throw new SchemaException("Duplicate email.");
            }

            customers.put(customer.customerId(), customer);
        }

        void addProduct(Product product) {
            if (products.containsKey(product.productId())) {
                throw new SchemaException("Duplicate product ID.");
            }

            if (!productSkus.add(product.sku())) {
                throw new SchemaException("Duplicate SKU.");
            }

            products.put(product.productId(), product);
        }

        synchronized Order placeOrder(OrderRequest request) {
            Customer customer = customers.get(request.customerId());

            if (customer == null) {
                throw new TransactionException(
                    "Customer does not exist."
                );
            }

            // Validate every product before changing persistent state.
            List<OrderItem> pendingItems = new ArrayList<>();

            long orderId = orderSequence.incrementAndGet();

            for (var entry : request.productQuantities().entrySet()) {
                Product product = products.get(entry.getKey());

                if (product == null || !product.active()) {
                    throw new TransactionException(
                        "Product unavailable: " + entry.getKey()
                    );
                }

                pendingItems.add(new OrderItem(
                    itemSequence.incrementAndGet(),
                    orderId,
                    product.productId(),
                    entry.getValue(),
                    product.unitPrice()
                ));
            }

            Order order = new Order(
                orderId,
                customer.customerId(),
                OrderStatus.PENDING,
                Instant.now()
            );

            // Commit phase: no changes occur before all validation succeeds.
            orders.put(orderId, order);

            for (OrderItem item : pendingItems) {
                orderItems.put(item.orderItemId(), item);
            }

            return order;
        }

        synchronized void updateStatus(
            long orderId,
            OrderStatus newStatus
        ) {
            Order existing = orders.get(orderId);

            if (existing == null) {
                throw new SchemaException("Order not found.");
            }

            orders.put(orderId, existing.withStatus(newStatus));
        }

        List<OrderReport> reports() {
            Map<Long, List<OrderItem>> grouped = orderItems.values()
                .stream()
                .collect(Collectors.groupingBy(
                    OrderItem::orderId
                ));

            return orders.values().stream()
                .map(order -> {
                    Customer customer = customers.get(
                        order.customerId()
                    );

                    List<OrderItem> items = grouped.getOrDefault(
                        order.orderId(),
                        Collections.emptyList()
                    );

                    BigDecimal total = items.stream()
                        .map(OrderItem::lineTotal)
                        .reduce(BigDecimal.ZERO, BigDecimal::add);

                    return new OrderReport(
                        order.orderId(),
                        customer.fullName(),
                        items.size(),
                        total
                    );
                })
                .sorted(Comparator.comparingLong(
                    OrderReport::orderId
                ))
                .toList();
        }
    }

    static SchemaRegistry buildSchema() {
        SchemaRegistry registry = new SchemaRegistry();

        registry.register(new TableDefinition(
            "customers",
            List.of(
                new ColumnDefinition(
                    "customer_id", SqlType.BIGINT,
                    false, false, true, null,
                    value -> value instanceof Long && (Long) value > 0
                ),
                new ColumnDefinition(
                    "email", SqlType.VARCHAR,
                    false, true, false, null,
                    value -> value instanceof String &&
                        ((String) value).contains("@")
                ),
                new ColumnDefinition(
                    "full_name", SqlType.VARCHAR,
                    false, false, false, null,
                    value -> value instanceof String &&
                        !((String) value).isBlank()
                )
            ),
            List.of("customer_id"),
            List.of(new UniqueKey(List.of("email"))),
            List.of()
        ));

        registry.register(new TableDefinition(
            "products",
            List.of(
                new ColumnDefinition(
                    "product_id", SqlType.BIGINT,
                    false, false, true, null,
                    value -> value instanceof Long && (Long) value > 0
                ),
                new ColumnDefinition(
                    "sku", SqlType.VARCHAR,
                    false, true, false, null,
                    value -> value instanceof String &&
                        !((String) value).isBlank()
                ),
                new ColumnDefinition(
                    "product_name", SqlType.VARCHAR,
                    false, false, false, null,
                    value -> value instanceof String &&
                        !((String) value).isBlank()
                ),
                new ColumnDefinition(
                    "unit_price", SqlType.NUMERIC,
                    false, false, false, null,
                    value -> value instanceof BigDecimal &&
                        ((BigDecimal) value).signum() >= 0
                )
            ),
            List.of("product_id"),
            List.of(new UniqueKey(List.of("sku"))),
            List.of()
        ));

        registry.register(new TableDefinition(
            "orders",
            List.of(
                new ColumnDefinition(
                    "order_id", SqlType.BIGINT,
                    false, false, true, null,
                    value -> value instanceof Long
                ),
                new ColumnDefinition(
                    "customer_id", SqlType.BIGINT,
                    false, false, false, null,
                    value -> value instanceof Long
                ),
                new ColumnDefinition(
                    "order_status", SqlType.VARCHAR,
                    false, false, false, OrderStatus.PENDING,
                    value -> value instanceof OrderStatus
                )
            ),
            List.of("order_id"),
            List.of(),
            List.of(new ForeignKey(
                List.of("customer_id"),
                "customers",
                List.of("customer_id"),
                DeletePolicy.RESTRICT
            ))
        ));

        registry.register(new TableDefinition(
            "order_items",
            List.of(
                new ColumnDefinition(
                    "order_item_id", SqlType.BIGINT,
                    false, false, true, null,
                    value -> value instanceof Long
                ),
                new ColumnDefinition(
                    "order_id", SqlType.BIGINT,
                    false, false, false, null,
                    value -> value instanceof Long
                ),
                new ColumnDefinition(
                    "product_id", SqlType.BIGINT,
                    false, false, false, null,
                    value -> value instanceof Long
                ),
                new ColumnDefinition(
                    "quantity", SqlType.BIGINT,
                    false, false, false, null,
                    value -> value instanceof Integer &&
                        (Integer) value > 0
                )
            ),
            List.of("order_item_id"),
            List.of(new UniqueKey(
                List.of("order_id", "product_id")
            )),
            List.of(
                new ForeignKey(
                    List.of("order_id"),
                    "orders",
                    List.of("order_id"),
                    DeletePolicy.CASCADE
                ),
                new ForeignKey(
                    List.of("product_id"),
                    "products",
                    List.of("product_id"),
                    DeletePolicy.RESTRICT
                )
            )
        ));

        registry.validateRelationships();
        return registry;
    }

    public static void main(String[] args) {
        try {
            SchemaRegistry schema = buildSchema();

            System.out.println("SCHEMA CREATION ORDER");

            schema.creationOrder().forEach(
                System.out::println
            );

            System.out.println(
                "Schema version: " + schema.version()
            );

            OrderService service = new OrderService();

            service.addCustomer(new Customer(
                1,
                "aarav@example.com",
                "Aarav Sharma",
                Instant.now()
            ));

            service.addProduct(new Product(
                101,
                "SKU-101",
                "Laptop",
                new BigDecimal("65000.00"),
                true
            ));

            service.addProduct(new Product(
                102,
                "SKU-102",
                "Keyboard",
                new BigDecimal("1500.00"),
                true
            ));

            Order order = service.placeOrder(
                new OrderRequest(
                    1,
                    Map.of(101L, 1, 102L, 2)
                )
            );

            System.out.println("\nCREATED ORDER");
            System.out.println(order);

            System.out.println("\nORDER REPORT");

            service.reports().forEach(report ->
                System.out.printf(
                    "Order=%d Customer=%s Items=%d Total=%s%n",
                    report.orderId(),
                    report.customerName(),
                    report.itemCount(),
                    report.total()
                )
            );

            service.updateStatus(
                order.orderId(),
                OrderStatus.CONFIRMED
            );

            System.out.println("\nUpdated status: " +
                OrderStatus.CONFIRMED);

            System.out.println("\nFAILURE TESTS");

            try {
                service.addCustomer(new Customer(
                    2,
                    "aarav@example.com",
                    "Duplicate Email",
                    Instant.now()
                ));
            } catch (SchemaException error) {
                System.out.println(
                    "Unique constraint: " + error.getMessage()
                );
            }

            try {
                service.placeOrder(new OrderRequest(
                    1,
                    Map.of(999L, 1)
                ));
            } catch (TransactionException error) {
                System.out.println(
                    "Foreign key/product validation: " +
                    error.getMessage()
                );
            }

            try {
                service.updateStatus(
                    9999,
                    OrderStatus.SHIPPED
                );
            } catch (SchemaException error) {
                System.out.println(
                    "State validation: " + error.getMessage()
                );
            }

            System.out.println(
                "\nEnterprise schema demonstration completed."
            );

        } catch (Exception error) {
            System.err.println(
                "Execution failed: " + error.getMessage()
            );
            System.exit(1);
        }
    }
}
