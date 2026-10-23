#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

struct Sale {
    int saleId;
    int customerId;
    std::string productId;
    std::string category;
    double amount;
};

struct RankedSale {
    Sale sale;
    std::size_t rowNumber;
};

class GovernanceAnalytics {
public:
    explicit GovernanceAnalytics(std::vector<Sale> input)
        : sales_(std::move(input)) {
        validate();
    }

    std::vector<RankedSale> rowNumberByCustomer() const {
        std::map<int, std::vector<Sale>> partitions;

        for (const auto& sale : sales_) {
            partitions[sale.customerId].push_back(sale);
        }

        std::vector<RankedSale> result;

        for (auto& [customerId, rows] : partitions) {
            std::sort(rows.begin(), rows.end(), [](const Sale& a, const Sale& b) {
                if (a.amount != b.amount) {
                    return a.amount > b.amount;
                }
                return a.saleId < b.saleId;
            });

            for (std::size_t i = 0; i < rows.size(); ++i) {
                result.push_back({rows[i], i + 1});
            }
        }

        return result;
    }

    std::vector<Sale> deduplicateCustomerProduct() const {
        /*
         * The unordered_map provides expected O(n) lookup.
         * A duplicate business key keeps the highest-value record.
         */
        std::unordered_map<std::string, Sale> best;

        for (const auto& sale : sales_) {
            std::string key =
                std::to_string(sale.customerId) + "|" + sale.productId;

            auto it = best.find(key);

            if (it == best.end() ||
                sale.amount > it->second.amount ||
                (sale.amount == it->second.amount &&
                 sale.saleId > it->second.saleId)) {
                best[key] = sale;
            }
        }

        std::vector<Sale> result;
        result.reserve(best.size());

        for (const auto& [key, sale] : best) {
            result.push_back(sale);
        }

        std::sort(result.begin(), result.end(),
                  [](const Sale& a, const Sale& b) {
                      return a.saleId < b.saleId;
                  });

        return result;
    }

    std::vector<RankedSale> topNPerCategory(std::size_t n) const {
        if (n == 0) {
            throw std::invalid_argument("n must be greater than zero");
        }

        std::map<std::string, std::vector<Sale>> partitions;

        for (const auto& sale : sales_) {
            partitions[sale.category].push_back(sale);
        }

        std::vector<RankedSale> result;

        for (auto& [category, rows] : partitions) {
            std::sort(rows.begin(), rows.end(), [](const Sale& a, const Sale& b) {
                if (a.amount != b.amount) {
                    return a.amount > b.amount;
                }
                return a.saleId < b.saleId;
            });

            const std::size_t limit = std::min(n, rows.size());

            for (std::size_t i = 0; i < limit; ++i) {
                result.push_back({rows[i], i + 1});
            }
        }

        return result;
    }

    std::vector<Sale> globalTopN(std::size_t n) const {
        if (n == 0) {
            throw std::invalid_argument("n must be greater than zero");
        }

        std::vector<Sale> result = sales_;

        std::sort(result.begin(), result.end(),
                  [](const Sale& a, const Sale& b) {
                      if (a.amount != b.amount) {
                          return a.amount > b.amount;
                      }
                      return a.saleId < b.saleId;
                  });

        if (result.size() > n) {
            result.resize(n);
        }

        return result;
    }

private:
    std::vector<Sale> sales_;

    void validate() const {
        if (sales_.empty()) {
            throw std::invalid_argument("Sales collection cannot be empty");
        }

        std::unordered_map<int, bool> ids;

        for (const auto& sale : sales_) {
            if (sale.saleId <= 0 ||
                sale.customerId <= 0 ||
                sale.productId.empty() ||
                sale.category.empty() ||
                sale.amount < 0.0) {
                throw std::invalid_argument(
                    "Sale contains invalid business data");
            }

            if (ids.contains(sale.saleId)) {
                throw std::invalid_argument("Duplicate sale identifier");
            }

            ids[sale.saleId] = true;
        }
    }
};

void printSale(const Sale& sale, std::size_t rowNumber = 0) {
    std::cout << std::left
              << std::setw(5) << sale.saleId
              << std::setw(8) << sale.customerId
              << std::setw(10) << sale.productId
              << std::setw(13) << sale.category
              << std::setw(10) << std::fixed << std::setprecision(2)
              << sale.amount;

    if (rowNumber != 0) {
        std::cout << std::setw(8) << rowNumber;
    }

    std::cout << '\n';
}

int main() {
    try {
        const std::vector<Sale> sales = {
            {1, 101, "LAPTOP", "Electronics", 1200.00},
            {2, 102, "PHONE", "Electronics", 800.00},
            {3, 101, "LAPTOP", "Electronics", 1250.00},
            {4, 103, "CHAIR", "Furniture", 300.00},
            {5, 104, "PHONE", "Electronics", 950.00},
            {6, 102, "MONITOR", "Electronics", 500.00},
            {7, 105, "TABLE", "Furniture", 700.00},
            {8, 103, "CHAIR", "Furniture", 320.00},
            {9, 106, "PHONE", "Electronics", 1100.00},
            {10, 107, "DESK", "Furniture", 900.00},
            {11, 108, "PHONE", "Electronics", 780.00},
            {12, 109, "TABLE", "Furniture", 650.00}
        };

        GovernanceAnalytics analytics(sales);

        std::cout << "ROW_NUMBER by customer\n";
        std::cout << "ID   Customer Product   Category     Amount    Row\n";

        for (const auto& ranked : analytics.rowNumberByCustomer()) {
            printSale(ranked.sale, ranked.rowNumber);
        }

        std::cout << "\nDeduplicated customer/product records\n";
        std::cout << "ID   Customer Product   Category     Amount\n";

        for (const auto& sale : analytics.deduplicateCustomerProduct()) {
            printSale(sale);
        }

        std::cout << "\nTop 2 per category\n";
        std::cout << "ID   Customer Product   Category     Amount    Row\n";

        for (const auto& ranked : analytics.topNPerCategory(2)) {
            printSale(ranked.sale, ranked.rowNumber);
        }

        std::cout << "\nGlobal top 5\n";
        std::cout << "ID   Customer Product   Category     Amount\n";

        for (const auto& sale : analytics.globalTopN(5)) {
            printSale(sale);
        }

        /*
         * ROW_NUMBER requires a complete ordering when deterministic output
         * matters. Without saleId as the secondary key, equal amounts can
         * receive different positions after a change in input ordering.
         */
        std::cout << "\nTie-breaking uses amount DESC, then saleId ASC.\n";
        std::cout << "Sorting-based ranking is O(n log n) in the general case.\n";
        std::cout << "Hash-based deduplication is expected O(n).\n";
    }
    catch (const std::exception& error) {
        std::cerr << "Analysis error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
