#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

struct Sale {
    int id;
    std::string employee;
    std::string department;
    std::string date;
    double amount;
};

struct WindowMetrics {
    int rowNumber{};
    int rank{};
    double runningTotal{};
    double movingAverage{};
    bool hasLag{};
    double lag{};
    bool hasLead{};
    double lead{};
};

class RepositoryAnalytics {
private:
    std::vector<Sale> sales;

    std::map<std::string, std::vector<Sale>> partitions() const {
        std::map<std::string, std::vector<Sale>> result;

        for (const auto& sale : sales) {
            result[sale.department].push_back(sale);
        }

        for (auto& [department, rows] : result) {
            std::sort(rows.begin(), rows.end(),
                      [](const Sale& a, const Sale& b) {
                          if (a.date != b.date) {
                              return a.date < b.date;
                          }
                          return a.id < b.id;
                      });
        }

        return result;
    }

public:
    explicit RepositoryAnalytics(std::vector<Sale> input)
        : sales(std::move(input)) {
        validate();
    }

    void validate() const {
        std::unordered_map<int, bool> ids;

        for (const auto& sale : sales) {
            if (sale.id <= 0) {
                throw std::invalid_argument("Sale ID must be positive.");
            }

            if (ids.contains(sale.id)) {
                throw std::invalid_argument("Duplicate sale ID.");
            }
            ids[sale.id] = true;

            if (sale.employee.empty() || sale.department.empty()) {
                throw std::invalid_argument(
                    "Employee and department cannot be empty."
                );
            }

            if (sale.date.size() != 10 ||
                sale.date[4] != '-' ||
                sale.date[7] != '-') {
                throw std::invalid_argument(
                    "Date must use YYYY-MM-DD format."
                );
            }

            if (sale.amount < 0.0) {
                throw std::invalid_argument(
                    "Sale amount cannot be negative."
                );
            }
        }
    }

    std::unordered_map<int, WindowMetrics> analyze() const {
        std::unordered_map<int, WindowMetrics> metrics;

        for (const auto& [department, rows] : partitions()) {
            double runningTotal = 0.0;

            for (std::size_t i = 0; i < rows.size(); ++i) {
                const Sale& current = rows[i];
                WindowMetrics& metric = metrics[current.id];

                // ROW_NUMBER() OVER (PARTITION BY department ORDER BY date).
                metric.rowNumber = static_cast<int>(i + 1);

                runningTotal += current.amount;
                metric.runningTotal = runningTotal;

                // A two-row frame corresponds conceptually to:
                // AVG(amount) OVER (
                //   PARTITION BY department
                //   ORDER BY date
                //   ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
                // ).
                const std::size_t start = i == 0 ? 0 : i - 1;
                const std::size_t count = i - start + 1;
                double frameTotal = 0.0;

                for (std::size_t j = start; j <= i; ++j) {
                    frameTotal += rows[j].amount;
                }

                metric.movingAverage = frameTotal / static_cast<double>(count);

                if (i > 0) {
                    metric.hasLag = true;
                    metric.lag = rows[i - 1].amount;
                }

                if (i + 1 < rows.size()) {
                    metric.hasLead = true;
                    metric.lead = rows[i + 1].amount;
                }
            }

            // RANK() uses amount descending while preserving ties.
            std::vector<Sale> ranked = rows;
            std::sort(ranked.begin(), ranked.end(),
                      [](const Sale& a, const Sale& b) {
                          if (a.amount != b.amount) {
                              return a.amount > b.amount;
                          }
                          return a.id < b.id;
                      });

            double previousAmount = -1.0;
            int rank = 0;

            for (std::size_t i = 0; i < ranked.size(); ++i) {
                if (i == 0 || ranked[i].amount != previousAmount) {
                    rank = static_cast<int>(i + 1);
                    previousAmount = ranked[i].amount;
                }

                metrics[ranked[i].id].rank = rank;
            }
        }

        return metrics;
    }

    void print() const {
        const auto metrics = analyze();

        std::vector<Sale> ordered = sales;
        std::sort(ordered.begin(), ordered.end(),
                  [](const Sale& a, const Sale& b) {
                      if (a.department != b.department) {
                          return a.department < b.department;
                      }
                      if (a.date != b.date) {
                          return a.date < b.date;
                      }
                      return a.id < b.id;
                  });

        std::cout << std::fixed << std::setprecision(2);
        std::cout
            << std::left
            << std::setw(14) << "Department"
            << std::setw(10) << "Employee"
            << std::setw(12) << "Amount"
            << std::setw(8) << "ROW#"
            << std::setw(8) << "RANK"
            << std::setw(14) << "Running"
            << std::setw(14) << "Avg2"
            << std::setw(12) << "LAG"
            << std::setw(12) << "LEAD"
            << '\n';

        std::cout << std::string(104, '-') << '\n';

        for (const auto& sale : ordered) {
            const auto& metric = metrics.at(sale.id);

            std::cout
                << std::left
                << std::setw(14) << sale.department
                << std::setw(10) << sale.employee
                << std::setw(12) << sale.amount
                << std::setw(8) << metric.rowNumber
                << std::setw(8) << metric.rank
                << std::setw(14) << metric.runningTotal
                << std::setw(14) << metric.movingAverage;

            if (metric.hasLag) {
                std::cout << std::setw(12) << metric.lag;
            } else {
                std::cout << std::setw(12) << "-";
            }

            if (metric.hasLead) {
                std::cout << std::setw(12) << metric.lead;
            } else {
                std::cout << std::setw(12) << "-";
            }

            std::cout << '\n';
        }
    }
};

int main() {
    try {
        std::vector<Sale> sales{
            {1, "Asha", "Technology", "2026-01-05", 12000.00},
            {2, "Ravi", "Technology", "2026-01-12", 18000.00},
            {3, "Asha", "Technology", "2026-02-03", 15000.00},
            {4, "Ravi", "Technology", "2026-02-17", 22000.00},
            {5, "Neha", "Finance", "2026-01-08", 9000.00},
            {6, "Vikram", "Finance", "2026-01-22", 14000.00},
            {7, "Neha", "Finance", "2026-02-06", 11000.00},
            {8, "Vikram", "Finance", "2026-02-20", 17000.00},
            {9, "Meera", "Operations", "2026-01-10", 7000.00},
            {10, "Meera", "Operations", "2026-02-14", 13000.00}
        };

        RepositoryAnalytics analytics(std::move(sales));
        analytics.print();
    } catch (const std::exception& error) {
        std::cerr << "Analysis failed: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
