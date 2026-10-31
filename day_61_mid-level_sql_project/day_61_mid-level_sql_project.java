import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

public class SalesGovernanceDemo {

    enum OrderStatus {
        PENDING,
        PAID,
        SHIPPED,
        CANCELLED
    }

    record Customer(
            int id,
            String name,
            String email,
            String city,
            BigDecimal creditLimit
    ) {
        Customer {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new ValidationException("Invalid customer identity.");
            }
            if (email == null || !email.contains("@")) {
                throw new ValidationException("Invalid customer email.");
            }
            if (creditLimit == null || creditLimit.signum() < 0) {
                throw new ValidationException("Invalid credit limit.");
            }
            creditLimit = money(creditLimit);
        }
    }

    record Product(
            int id,
            String name,
            String category,
            BigDecimal unitPrice,
            int stock
    ) {
        Product {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new ValidationException("Invalid product.");
            }
            if (category == null || category.isBlank()) {
                throw new ValidationException("Product category is required.");
            }
            if (unitPrice == null || unitPrice.signum() <= 0) {
                throw new ValidationException("Product price must be positive.");
            }
            if (stock < 0) {
                throw new ValidationException("Product stock cannot be negative.");
            }
            unitPrice = money(unitPrice);
        }
    }

    record OrderLine(int productId, int quantity, BigDecimal unitPrice) {
        OrderLine {
            if (productId <= 0 || quantity <= 0 || unitPrice == null ||
                    unitPrice.signum() <= 0) {
                throw new ValidationException("Invalid order line.");
            }
            unitPrice = money(unitPrice);
        }

        BigDecimal revenue() {
            return money(unitPrice.multiply(BigDecimal.valueOf(quantity)));
        }
    }

    static final class Order {
        private final int id;
        private final int customerId;
        private final LocalDate orderDate;
        private final List<OrderLine> lines;
        private OrderStatus status;

        Order(
                int id,
                int customerId,
                LocalDate orderDate,
                List<OrderLine> lines
        ) {
            if (id <= 0 || customerId <= 0 || orderDate == null ||
                    lines == null || lines.isEmpty()) {
                throw new ValidationException("Invalid order.");
            }

            this.id = id;
            this.customerId = customerId;
            this.orderDate = orderDate;
            this.lines = List.copyOf(lines);
            this.status = OrderStatus.PENDING;
        }

        int id() {
            return id;
        }

        int customerId() {
            return customerId;
        }

        LocalDate orderDate() {
            return orderDate;
        }

        List<OrderLine> lines() {
            return lines;
        }

        OrderStatus status() {
            return status;
        }

        void setStatus(OrderStatus status) {
            this.status = status;
        }

        BigDecimal total() {
            return money(
                    lines.stream()
                            .map(OrderLine::revenue)
                            .reduce(BigDecimal.ZERO, BigDecimal::add)
            );
        }
    }

    static final class ValidationException extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    static final class InvalidTransitionException extends RuntimeException {
        InvalidTransitionException(String message) {
            super(message);
        }
    }

    interface RevenuePolicy {
        boolean countsAsRevenue(OrderStatus status);
    }

    static final class CompletedSalesPolicy implements RevenuePolicy {
        @Override
        public boolean countsAsRevenue(OrderStatus status) {
            return status == OrderStatus.PAID ||
                    status == OrderStatus.SHIPPED;
        }
    }

    static final class SalesService {
        private final Map<Integer, Customer> customers = new HashMap<>();
        private final Map<Integer, Product> products = new HashMap<>();
        private final Map<Integer, Order> orders = new HashMap<>();
        private final RevenuePolicy revenuePolicy;

        SalesService(RevenuePolicy revenuePolicy) {
            this.revenuePolicy = Objects.requireNonNull(revenuePolicy);
        }

        void registerCustomer(Customer customer) {
            if (customers.putIfAbsent(customer.id(), customer) != null) {
                throw new ValidationException("Customer ID already exists.");
            }
        }

        void registerProduct(Product product) {
            if (products.putIfAbsent(product.id(), product) != null) {
                throw new ValidationException("Product ID already exists.");
            }
        }

        void createOrder(
                int orderId,
                int customerId,
                LocalDate orderDate,
                Map<Integer, Integer> requestedQuantities
        ) {
            if (orders.containsKey(orderId)) {
                throw new ValidationException("Order ID already exists.");
            }
            if (!customers.containsKey(customerId)) {
                throw new ValidationException("Customer does not exist.");
            }
            if (requestedQuantities == null || requestedQuantities.isEmpty()) {
                throw new ValidationException("Order must contain products.");
            }

            List<OrderLine> lines = new ArrayList<>();

            // Validate all quantities before inventory mutation.
            for (var entry : requestedQuantities.entrySet()) {
                int productId = entry.getKey();
                int quantity = entry.getValue();

                Product product = products.get(productId);

                if (product == null) {
                    throw new ValidationException("Product does not exist.");
                }
                if (quantity <= 0) {
                    throw new ValidationException("Quantity must be positive.");
                }
                if (quantity > product.stock()) {
                    throw new ValidationException(
                            "Insufficient stock for " + product.name()
                    );
                }

                lines.add(
                        new OrderLine(productId, quantity, product.unitPrice())
                );
            }

            // The stock replacement is explicit because records are immutable.
            for (var line : lines) {
                Product product = products.get(line.productId());
                products.put(
                        product.id(),
                        new Product(
                                product.id(),
                                product.name(),
                                product.category(),
                                product.unitPrice(),
                                product.stock() - line.quantity()
                        )
                );
            }

            orders.put(
                    orderId,
                    new Order(orderId, customerId, orderDate, lines)
            );
        }

        void transition(int orderId, OrderStatus target) {
            Order order = getOrder(orderId);

            boolean allowed = switch (order.status()) {
                case PENDING -> target == OrderStatus.PAID ||
                        target == OrderStatus.CANCELLED;
                case PAID -> target == OrderStatus.SHIPPED ||
                        target == OrderStatus.CANCELLED;
                case SHIPPED, CANCELLED -> false;
            };

            if (!allowed) {
                throw new InvalidTransitionException(
                        "Cannot transition " +
                                order.status() + " -> " + target
                );
            }

            if (target == OrderStatus.CANCELLED) {
                restoreStock(order);
            }

            order.setStatus(target);
        }

        private void restoreStock(Order order) {
            for (OrderLine line : order.lines()) {
                Product product = products.get(line.productId());
                products.put(
                        product.id(),
                        new Product(
                                product.id(),
                                product.name(),
                                product.category(),
                                product.unitPrice(),
                                product.stock() + line.quantity()
                        )
                );
            }
        }

        private Order getOrder(int orderId) {
            Order order = orders.get(orderId);
            if (order == null) {
                throw new ValidationException("Order does not exist.");
            }
            return order;
        }

        List<Order> completedOrders() {
            return orders.values().stream()
                    .filter(order -> revenuePolicy.countsAsRevenue(order.status()))
                    .toList();
        }

        BigDecimal totalRevenue() {
            return completedOrders().stream()
                    .map(Order::total)
                    .reduce(BigDecimal.ZERO, BigDecimal::add)
                    .setScale(2, RoundingMode.HALF_UP);
        }

        Map<String, BigDecimal> revenueByCategory() {
            Map<String, BigDecimal> result = new HashMap<>();

            for (Order order : completedOrders()) {
                for (OrderLine line : order.lines()) {
                    Product product = products.get(line.productId());
                    result.merge(
                            product.category(),
                            line.revenue(),
                            (a, b) -> money(a.add(b))
                    );
                }
            }

            return result.entrySet().stream()
                    .sorted(Map.Entry.<String, BigDecimal>comparingByValue().reversed())
                    .collect(Collectors.toMap(
                            Map.Entry::getKey,
                            Map.Entry::getValue,
                            BigDecimal::add,
                            java.util.LinkedHashMap::new
                    ));
        }

        Map<String, BigDecimal> revenueByCustomer() {
            Map<String, BigDecimal> result = new HashMap<>();

            for (Order order : completedOrders()) {
                Customer customer = customers.get(order.customerId());

                result.merge(
                        customer.name(),
                        order.total(),
                        (a, b) -> money(a.add(b))
                );
            }

            return result.entrySet().stream()
                    .sorted(Map.Entry.<String, BigDecimal>comparingByValue().reversed())
                    .collect(Collectors.toMap(
                            Map.Entry::getKey,
                            Map.Entry::getValue,
                            BigDecimal::add,
                            java.util.LinkedHashMap::new
                    ));
        }
    }

    static BigDecimal money(BigDecimal value) {
        return value.setScale(2, RoundingMode.HALF_UP);
    }

    static SalesService createService() {
        SalesService service = new SalesService(new CompletedSalesPolicy());

        service.registerCustomer(
                new Customer(
                        1,
                        "Apex Retail",
                        "sales@apex.example",
                        "Delhi",
                        new BigDecimal("15000")
                )
        );

        service.registerCustomer(
                new Customer(
                        2,
                        "Northstar Foods",
                        "orders@northstar.example",
                        "Lucknow",
                        new BigDecimal("10000")
                )
        );

        service.registerCustomer(
                new Customer(
                        3,
                        "Greenline Stores",
                        "procurement@greenline.example",
                        "Pune",
                        new BigDecimal("12000")
                )
        );

        service.registerProduct(
                new Product(
                        101,
                        "Business Laptop",
                        "Computers",
                        new BigDecimal("85000"),
                        20
                )
        );

        service.registerProduct(
                new Product(
                        102,
                        "Wireless Keyboard",
                        "Accessories",
                        new BigDecimal("2500"),
                        100
                )
        );

        service.registerProduct(
                new Product(
                        103,
                        "USB-C Dock",
                        "Accessories",
                        new BigDecimal("6500"),
                        50
                )
        );

        service.registerProduct(
                new Product(
                        104,
                        "Network Switch",
                        "Networking",
                        new BigDecimal("12000"),
                        30
                )
        );

        return service;
    }

    public static void main(String[] args) {
        try {
            SalesService service = createService();

            service.createOrder(
                    1001,
                    1,
                    LocalDate.of(2026, 1, 10),
                    Map.of(101, 2, 102, 5)
            );
            service.transition(1001, OrderStatus.PAID);
            service.transition(1001, OrderStatus.SHIPPED);

            service.createOrder(
                    1002,
                    2,
                    LocalDate.of(2026, 2, 12),
                    Map.of(104, 2, 103, 3)
            );
            service.transition(1002, OrderStatus.PAID);

            service.createOrder(
                    1003,
                    3,
                    LocalDate.of(2026, 3, 5),
                    Map.of(102, 10, 103, 4)
            );
            service.transition(1003, OrderStatus.PAID);

            // Business rule failure is isolated from valid stored orders.
            try {
                service.createOrder(
                        1004,
                        1,
                        LocalDate.of(2026, 3, 10),
                        Map.of(101, 999)
                );
            } catch (ValidationException error) {
                System.out.println("Rejected order: " + error.getMessage());
            }

            System.out.println("SALES ANALYSIS");
            System.out.println("==============");
            System.out.println(
                    "Completed revenue: " +
                            service.totalRevenue().toPlainString()
            );

            System.out.println("\nRevenue by category:");
            service.revenueByCategory().forEach(
                    (category, revenue) ->
                            System.out.println(
                                    category + ": " + revenue.toPlainString()
                            )
            );

            System.out.println("\nRevenue by customer:");
            service.revenueByCustomer().forEach(
                    (customer, revenue) ->
                            System.out.println(
                                    customer + ": " + revenue.toPlainString()
                            )
            );

        } catch (ValidationException | InvalidTransitionException error) {
            System.err.println("Business error: " + error.getMessage());
            System.exit(1);
        }
    }
}
