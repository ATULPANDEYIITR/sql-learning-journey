import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Multi-Table JOINs as an enterprise repository reporting service.
 *
 * The domain contains:
 * Region -> Customer -> Order -> OrderItem -> Product
 *
 * The implementation uses Java 17 records for immutable domain data and
 * explicit services for join traversal, aggregation, validation, and
 * left-join semantics.
 *
 * Compile and run:
 *     javac MultiTableJoins.java
 *     java MultiTableJoins
 */
public class MultiTableJoins {

    enum OrderStatus {
        PLACED, SHIPPED, DELIVERED, CANCELLED
    }

    record Region(int id, String name) {}

    record Customer(int id, String name, int regionId) {}

    record Product(int id, String name, String category, double unitPrice) {
        Product {
            if (unitPrice <= 0) {
                throw new IllegalArgumentException("Product price must be positive");
            }
        }
    }

    record Order(
            int id,
            int customerId,
            String date,
            OrderStatus status
    ) {}

    record OrderItem(
            int orderId,
            int productId,
            int quantity,
            double unitPrice
    ) {
        OrderItem {
            if (quantity <= 0 || unitPrice <= 0) {
                throw new IllegalArgumentException(
                        "Order item quantity and price must be positive"
                );
            }
        }
    }

    record JoinedLine(
            String region,
            String customer,
            int orderId,
            String product,
            int quantity,
            double value
    ) {}

    record CustomerRevenue(
            String customer,
            String region,
            long orderCount,
            double revenue
    ) {}

    static final class Repository {
        private final List<Region> regions = List.of(
                new Region(1, "North"),
                new Region(2, "South"),
                new Region(3, "West"),
                new Region(4, "East")
        );

        private final List<Customer> customers = List.of(
                new Customer(101, "Aarav Systems", 1),
                new Customer(102, "Bharat Logistics", 2),
                new Customer(103, "Civic Research Lab", 3),
                new Customer(104, "Delta Manufacturing", 1),
                new Customer(105, "Eastern Retail Group", 4)
        );

        private final List<Product> products = List.of(
                new Product(201, "Edge Sensor", "IoT", 120.0),
                new Product(202, "Gateway Pro", "Networking", 450.0),
                new Product(203, "Analytics License", "Software", 800.0),
                new Product(204, "Secure Router", "Networking", 600.0),
                new Product(205, "Inspection Camera", "Vision", 950.0)
        );

        private final List<Order> orders = List.of(
                new Order(1001, 101, "2026-09-01", OrderStatus.DELIVERED),
                new Order(1002, 101, "2026-09-14", OrderStatus.SHIPPED),
                new Order(1003, 102, "2026-09-18", OrderStatus.DELIVERED),
                new Order(1004, 103, "2026-09-20", OrderStatus.CANCELLED),
                new Order(1005, 104, "2026-09-22", OrderStatus.DELIVERED),
                new Order(1006, 105, "2026-09-24", OrderStatus.PLACED)
        );

        private final List<OrderItem> items = List.of(
                new OrderItem(1001, 201, 10, 120.0),
                new OrderItem(1001, 202, 2, 450.0),
                new OrderItem(1002, 203, 1, 800.0),
                new OrderItem(1002, 201, 5, 120.0),
                new OrderItem(1003, 204, 3, 600.0),
                new OrderItem(1003, 201, 20, 120.0),
                new OrderItem(1004, 205, 1, 950.0),
                new OrderItem(1005, 205, 4, 950.0),
                new OrderItem(1005, 203, 2, 800.0),
                new OrderItem(1006, 202, 1, 450.0)
        );
    }

    static final class JoinService {
        private final Repository repository;

        JoinService(Repository repository) {
            this.repository = repository;
        }

        List<JoinedLine> buildSalesReport() {
            Map<Integer, Region> regionsById = repository.regions.stream()
                    .collect(Collectors.toMap(Region::id, region -> region));

            Map<Integer, Customer> customersById = repository.customers.stream()
                    .collect(Collectors.toMap(Customer::id, customer -> customer));

            Map<Integer, Product> productsById = repository.products.stream()
                    .collect(Collectors.toMap(Product::id, product -> product));

            Map<Integer, List<OrderItem>> itemsByOrder = repository.items.stream()
                    .collect(Collectors.groupingBy(OrderItem::orderId));

            List<JoinedLine> result = new ArrayList<>();

            for (Order order : repository.orders) {
                if (order.status() == OrderStatus.CANCELLED) {
                    continue;
                }

                Customer customer = customersById.get(order.customerId());
                if (customer == null) {
                    throw new IllegalStateException(
                            "Order references an unknown customer: " + order.id()
                    );
                }

                Region region = regionsById.get(customer.regionId());
                if (region == null) {
                    throw new IllegalStateException(
                            "Customer references an unknown region: "
                                    + customer.id()
                    );
                }

                for (OrderItem item :
                        itemsByOrder.getOrDefault(order.id(), List.of())) {

                    Product product = productsById.get(item.productId());

                    if (product == null) {
                        throw new IllegalStateException(
                                "Order item references an unknown product: "
                                        + item.productId()
                        );
                    }

                    result.add(new JoinedLine(
                            region.name(),
                            customer.name(),
                            order.id(),
                            product.name(),
                            item.quantity(),
                            item.quantity() * item.unitPrice()
                    ));
                }
            }

            return result.stream()
                    .sorted(Comparator
                            .comparing(JoinedLine::region)
                            .thenComparingInt(JoinedLine::orderId)
                            .thenComparing(JoinedLine::product))
                    .toList();
        }

        List<CustomerRevenue> deliveredRevenue() {
            Map<Integer, Customer> customersById = repository.customers.stream()
                    .collect(Collectors.toMap(Customer::id, customer -> customer));

            Map<Integer, Region> regionsById = repository.regions.stream()
                    .collect(Collectors.toMap(Region::id, region -> region));

            Map<Integer, List<OrderItem>> itemsByOrder = repository.items.stream()
                    .collect(Collectors.groupingBy(OrderItem::orderId));

            Map<Integer, Double> revenueByCustomer = new HashMap<>();
            Map<Integer, Set<Integer>> ordersByCustomer = new HashMap<>();

            for (Order order : repository.orders) {
                if (order.status() != OrderStatus.DELIVERED) {
                    continue;
                }

                ordersByCustomer
                        .computeIfAbsent(order.customerId(), ignored -> new HashSet<>())
                        .add(order.id());

                for (OrderItem item :
                        itemsByOrder.getOrDefault(order.id(), List.of())) {
                    revenueByCustomer.merge(
                            order.customerId(),
                            item.quantity() * item.unitPrice(),
                            Double::sum
                    );
                }
            }

            return repository.customers.stream()
                    .map(customer -> {
                        Region region = regionsById.get(customer.regionId());
                        if (region == null) {
                            throw new IllegalStateException(
                                    "Unknown region for customer " + customer.id()
                            );
                        }

                        return new CustomerRevenue(
                                customer.name(),
                                region.name(),
                                ordersByCustomer
                                        .getOrDefault(customer.id(), Set.of())
                                        .size(),
                                revenueByCustomer.getOrDefault(customer.id(), 0.0)
                        );
                    })
                    .sorted(Comparator
                            .comparingDouble(CustomerRevenue::revenue)
                            .reversed())
                    .toList();
        }

        List<CustomerRevenue> customerPreservingLeftJoin() {
            Map<Integer, Long> ordersByCustomer = repository.orders.stream()
                    .collect(Collectors.groupingBy(
                            Order::customerId,
                            Collectors.counting()
                    ));

            Map<Integer, Region> regionsById = repository.regions.stream()
                    .collect(Collectors.toMap(Region::id, region -> region));

            return repository.customers.stream()
                    .map(customer -> {
                        Region region = regionsById.get(customer.regionId());

                        if (region == null) {
                            throw new IllegalStateException(
                                    "Customer references an unknown region"
                            );
                        }

                        return new CustomerRevenue(
                                customer.name(),
                                region.name(),
                                ordersByCustomer.getOrDefault(customer.id(), 0L),
                                0.0
                        );
                    })
                    .toList();
        }
    }

    static final class DataValidator {
        static void validate(Repository repository) {
            Set<Integer> regionIds = repository.regions.stream()
                    .map(Region::id)
                    .collect(Collectors.toSet());

            Set<Integer> customerIds = repository.customers.stream()
                    .map(Customer::id)
                    .collect(Collectors.toSet());

            Set<Integer> productIds = repository.products.stream()
                    .map(Product::id)
                    .collect(Collectors.toSet());

            Set<Integer> orderIds = repository.orders.stream()
                    .map(Order::id)
                    .collect(Collectors.toSet());

            repository.customers.forEach(customer -> {
                if (!regionIds.contains(customer.regionId())) {
                    throw new IllegalStateException(
                            "Broken customer -> region relationship"
                    );
                }
            });

            repository.orders.forEach(order -> {
                if (!customerIds.contains(order.customerId())) {
                    throw new IllegalStateException(
                            "Broken order -> customer relationship"
                    );
                }
            });

            repository.items.forEach(item -> {
                if (!orderIds.contains(item.orderId())) {
                    throw new IllegalStateException(
                            "Broken item -> order relationship"
                    );
                }

                if (!productIds.contains(item.productId())) {
                    throw new IllegalStateException(
                            "Broken item -> product relationship"
                    );
                }
            });
        }
    }

    static void printSalesLines(List<JoinedLine> lines) {
        System.out.println("\n=== Five-table enterprise report ===");

        for (JoinedLine line : lines) {
            System.out.printf(
                    "%-10s %-24s order=%-5d %-22s qty=%-3d value=%.2f%n",
                    line.region(),
                    line.customer(),
                    line.orderId(),
                    line.product(),
                    line.quantity(),
                    line.value()
            );
        }
    }

    static void printRevenue(List<CustomerRevenue> revenue) {
        System.out.println("\n=== Delivered revenue ===");

        for (CustomerRevenue row : revenue) {
            System.out.printf(
                    "%-24s %-8s orders=%d revenue=%.2f%n",
                    row.customer(),
                    row.region(),
                    row.orderCount(),
                    row.revenue()
            );
        }
    }

    public static void main(String[] args) {
        try {
            Repository repository = new Repository();

            DataValidator.validate(repository);

            JoinService service = new JoinService(repository);

            printSalesLines(service.buildSalesReport());
            printRevenue(service.deliveredRevenue());

            System.out.println("\n=== LEFT JOIN equivalent ===");
            service.customerPreservingLeftJoin().forEach(row ->
                    System.out.printf(
                            "%-24s %-8s orders=%d%n",
                            row.customer(),
                            row.region(),
                            row.orderCount()
                    )
            );

            System.out.println("\n=== Java-specific design decisions ===");
            System.out.println("Records provide immutable relational domain values.");
            System.out.println("Maps provide indexed foreign-key lookups.");
            System.out.println("Streams perform grouping and ordered reporting.");
            System.out.println("Explicit validation detects broken relationships before reporting.");
        } catch (IllegalStateException | IllegalArgumentException error) {
            System.err.println("Repository processing failed: " + error.getMessage());
            System.exit(1);
        }
    }
}
