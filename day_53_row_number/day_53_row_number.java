import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class RankingAnalytics {

    record Sale(
        int saleId,
        int customerId,
        String productId,
        String category,
        double amount
    ) {}

    record RankedSale(Sale sale, int rowNumber) {}

    enum RankingPolicy {
        HIGHEST_AMOUNT_FIRST,
        LOWEST_AMOUNT_FIRST
    }

    static final class InvalidSaleException extends RuntimeException {
        InvalidSaleException(String message) {
            super(message);
        }
    }

    interface RankingService {
        List<RankedSale> rowNumberByCustomer(List<Sale> sales);

        List<RankedSale> topNPerCategory(
            List<Sale> sales,
            int n,
            RankingPolicy policy
        );
    }

    static final class RepositoryRankingService implements RankingService {

        @Override
        public List<RankedSale> rowNumberByCustomer(List<Sale> sales) {
            validate(sales);

            Map<Integer, List<Sale>> partitions = partitionByCustomer(sales);
            List<RankedSale> result = new ArrayList<>();

            Comparator<Sale> comparator =
                Comparator.comparingDouble(Sale::amount)
                    .reversed()
                    .thenComparingInt(Sale::saleId);

            for (List<Sale> customerSales : partitions.values()) {
                customerSales.sort(comparator);

                for (int i = 0; i < customerSales.size(); i++) {
                    result.add(new RankedSale(customerSales.get(i), i + 1));
                }
            }

            result.sort(
                Comparator.comparingInt(
                    ranked -> ranked.sale().customerId()
                ).thenComparingInt(RankedSale::rowNumber)
            );

            return List.copyOf(result);
        }

        @Override
        public List<RankedSale> topNPerCategory(
            List<Sale> sales,
            int n,
            RankingPolicy policy
        ) {
            validate(sales);

            if (n <= 0) {
                throw new IllegalArgumentException("n must be positive");
            }

            Map<String, List<Sale>> partitions =
                sales.stream().collect(
                    java.util.stream.Collectors.groupingBy(
                        Sale::category,
                        LinkedHashMap::new,
                        java.util.stream.Collectors.toCollection(ArrayList::new)
                    )
                );

            Comparator<Sale> comparator = policy == RankingPolicy.HIGHEST_AMOUNT_FIRST
                ? Comparator.comparingDouble(Sale::amount)
                    .reversed()
                    .thenComparingInt(Sale::saleId)
                : Comparator.comparingDouble(Sale::amount)
                    .thenComparingInt(Sale::saleId);

            List<RankedSale> result = new ArrayList<>();

            for (List<Sale> categorySales : partitions.values()) {
                categorySales.sort(comparator);

                int limit = Math.min(n, categorySales.size());

                for (int i = 0; i < limit; i++) {
                    result.add(new RankedSale(categorySales.get(i), i + 1));
                }
            }

            return List.copyOf(result);
        }

        private Map<Integer, List<Sale>> partitionByCustomer(
            List<Sale> sales
        ) {
            return sales.stream().collect(
                java.util.stream.Collectors.groupingBy(
                    Sale::customerId,
                    LinkedHashMap::new,
                    java.util.stream.Collectors.toCollection(ArrayList::new)
                )
            );
        }

        private void validate(List<Sale> sales) {
            if (sales == null || sales.isEmpty()) {
                throw new InvalidSaleException("Sales collection is empty");
            }

            Set<Integer> identifiers = new HashSet<>();

            for (Sale sale : sales) {
                if (sale == null) {
                    throw new InvalidSaleException("Null sale encountered");
                }

                if (sale.saleId() <= 0 ||
                    sale.customerId() <= 0 ||
                    sale.productId() == null ||
                    sale.productId().isBlank() ||
                    sale.category() == null ||
                    sale.category().isBlank() ||
                    Double.isNaN(sale.amount()) ||
                    Double.isInfinite(sale.amount()) ||
                    sale.amount() < 0) {
                    throw new InvalidSaleException(
                        "Invalid sale data: " + sale
                    );
                }

                if (!identifiers.add(sale.saleId())) {
                    throw new InvalidSaleException(
                        "Duplicate saleId: " + sale.saleId()
                    );
                }
            }
        }
    }

    static List<Sale> deduplicateCustomerProduct(List<Sale> sales) {
        Map<String, Sale> best = new HashMap<>();

        for (Sale sale : sales) {
            String key = sale.customerId() + "|" + sale.productId();

            best.merge(
                key,
                sale,
                (current, candidate) -> {
                    if (candidate.amount() > current.amount()) {
                        return candidate;
                    }

                    if (candidate.amount() == current.amount()
                        && candidate.saleId() > current.saleId()) {
                        return candidate;
                    }

                    return current;
                }
            );
        }

        return best.values().stream()
            .sorted(Comparator.comparingInt(Sale::saleId))
            .toList();
    }

    static List<Sale> globalTopN(List<Sale> sales, int n) {
        if (n <= 0) {
            throw new IllegalArgumentException("n must be positive");
        }

        return sales.stream()
            .sorted(
                Comparator.comparingDouble(Sale::amount)
                    .reversed()
                    .thenComparingInt(Sale::saleId)
            )
            .limit(n)
            .toList();
    }

    static void printRanked(String title, List<RankedSale> rows) {
        System.out.println("\n" + title);

        for (RankedSale ranked : rows) {
            Sale sale = ranked.sale();

            System.out.printf(
                "%-4d customer=%-4d product=%-8s category=%-12s amount=%8.2f row=%d%n",
                sale.saleId(),
                sale.customerId(),
                sale.productId(),
                sale.category(),
                sale.amount(),
                ranked.rowNumber()
            );
        }
    }

    static void printSales(String title, List<Sale> rows) {
        System.out.println("\n" + title);

        for (Sale sale : rows) {
            System.out.printf(
                "%-4d customer=%-4d product=%-8s category=%-12s amount=%8.2f%n",
                sale.saleId(),
                sale.customerId(),
                sale.productId(),
                sale.category(),
                sale.amount()
            );
        }
    }

    public static void main(String[] args) {
        List<Sale> sales = List.of(
            new Sale(1, 101, "LAPTOP", "Electronics", 1200.00),
            new Sale(2, 102, "PHONE", "Electronics", 800.00),
            new Sale(3, 101, "LAPTOP", "Electronics", 1250.00),
            new Sale(4, 103, "CHAIR", "Furniture", 300.00),
            new Sale(5, 104, "PHONE", "Electronics", 950.00),
            new Sale(6, 102, "MONITOR", "Electronics", 500.00),
            new Sale(7, 105, "TABLE", "Furniture", 700.00),
            new Sale(8, 103, "CHAIR", "Furniture", 320.00),
            new Sale(9, 106, "PHONE", "Electronics", 1100.00),
            new Sale(10, 107, "DESK", "Furniture", 900.00),
            new Sale(11, 108, "PHONE", "Electronics", 780.00),
            new Sale(12, 109, "TABLE", "Furniture", 650.00)
        );

        RankingService service = new RepositoryRankingService();

        try {
            printRanked(
                "ROW_NUMBER by customer",
                service.rowNumberByCustomer(sales)
            );

            printSales(
                "Deduplicated customer/product records",
                deduplicateCustomerProduct(sales)
            );

            printRanked(
                "Top 2 per category",
                service.topNPerCategory(
                    sales,
                    2,
                    RankingPolicy.HIGHEST_AMOUNT_FIRST
                )
            );

            printSales(
                "Global top 5",
                globalTopN(sales, 5)
            );

            System.out.println(
                "\nEnterprise policy: ranking is deterministic because amount " +
                "is followed by saleId as a tie-breaker."
            );
            System.out.println(
                "ROW_NUMBER assigns unique positions; equal values do not share a position."
            );
            System.out.println(
                "Deduplication uses a business key and retains the strongest record."
            );
        }
        catch (InvalidSaleException | IllegalArgumentException error) {
            System.err.println("Ranking workflow rejected: " + error.getMessage());
        }
    }
}
