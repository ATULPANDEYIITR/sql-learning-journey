#include <algorithm>
#include <cassert>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

enum class MergeStatus {
    ACCEPTED,
    REJECTED
};

struct Measurement {
    std::string id;
    double value;
};

struct RunningSnapshot {
    std::size_t count{};
    double total{};
    double average{};
    std::optional<double> minimum;
    std::optional<double> maximum{};
};

class RunningMetricEngine {
private:
    std::size_t count_{0};
    double total_{0.0};
    std::optional<double> minimum_;
    std::optional<double> maximum_;

    static void validate(double value) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("measurement must be finite");
        }
    }

public:
    RunningSnapshot add(double value) {
        validate(value);

        ++count_;
        total_ += value;

        if (!minimum_ || value < *minimum_) {
            minimum_ = value;
        }

        if (!maximum_ || value > *maximum_) {
            maximum_ = value;
        }

        return snapshot();
    }

    RunningSnapshot snapshot() const {
        return {
            count_,
            total_,
            count_ == 0 ? 0.0 : total_ / static_cast<double>(count_),
            minimum_,
            maximum_
        };
    }

    bool thresholdExceeded(double threshold) const {
        validate(threshold);
        return total_ > threshold;
    }
};

class SalesAggregator {
private:
    RunningMetricEngine engine_;
    std::unordered_map<std::string, double> acceptedTransactions_;

public:
    RunningSnapshot process(const Measurement& measurement) {
        if (measurement.id.empty()) {
            throw std::invalid_argument("transaction id cannot be empty");
        }

        if (acceptedTransactions_.contains(measurement.id)) {
            throw std::logic_error("duplicate transaction id: " + measurement.id);
        }

        RunningSnapshot next = engine_.add(measurement.value);

        // The transaction is registered only after successful validation.
        // This prevents invalid measurements from partially changing identity state.
        acceptedTransactions_.emplace(measurement.id, measurement.value);

        return next;
    }

    const RunningMetricEngine& engine() const {
        return engine_;
    }
};

std::vector<double> runningTotals(const std::vector<double>& values) {
    std::vector<double> result;
    result.reserve(values.size());

    double total = 0.0;

    for (double value : values) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("running total received a non-finite value");
        }

        total += value;
        result.push_back(total);
    }

    return result;
}

std::vector<double> cumulativeAverages(const std::vector<double>& values) {
    std::vector<double> result;
    result.reserve(values.size());

    double total = 0.0;

    for (std::size_t i = 0; i < values.size(); ++i) {
        if (!std::isfinite(values[i])) {
            throw std::invalid_argument("average received a non-finite value");
        }

        total += values[i];
        result.push_back(total / static_cast<double>(i + 1));
    }

    return result;
}

void printSnapshot(const RunningSnapshot& snapshot) {
    std::cout << std::fixed << std::setprecision(2)
              << "count=" << snapshot.count
              << ", total=" << snapshot.total
              << ", average=" << snapshot.average;

    if (snapshot.minimum) {
        std::cout << ", min=" << *snapshot.minimum;
    }

    if (snapshot.maximum) {
        std::cout << ", max=" << *snapshot.maximum;
    }

    std::cout << '\n';
}

void runTests() {
    const std::vector<double> values{10.0, 20.0, 30.0};

    const auto totals = runningTotals(values);
    assert(totals == std::vector<double>({10.0, 30.0, 60.0}));

    const auto averages = cumulativeAverages(values);
    assert(averages == std::vector<double>({10.0, 15.0, 20.0}));

    RunningMetricEngine engine;
    assert(engine.snapshot().count == 0);
    assert(engine.add(5.0).average == 5.0);
    assert(engine.add(15.0).average == 10.0);
    assert(engine.snapshot().total == 20.0);

    try {
        engine.add(std::numeric_limits<double>::quiet_NaN());
        assert(false);
    } catch (const std::invalid_argument&) {
        // Expected failure.
    }

    SalesAggregator aggregator;
    aggregator.process({"TX-1", 100.0});

    try {
        aggregator.process({"TX-1", 200.0});
        assert(false);
    } catch (const std::logic_error&) {
        // Duplicate identities are rejected.
    }
}

int main() {
    try {
        runTests();

        SalesAggregator aggregator;

        const std::vector<Measurement> sales{
            {"TX-1001", 1250.0},
            {"TX-1002", 875.5},
            {"TX-1003", 1499.25},
            {"TX-1004", 650.0},
            {"TX-1005", 2100.75}
        };

        std::cout << "Running sales metrics\n";

        for (const auto& sale : sales) {
            const auto snapshot = aggregator.process(sale);

            std::cout << sale.id << ": ";
            printSnapshot(snapshot);
        }

        const auto final = aggregator.engine().snapshot();

        std::cout << "\nFinal threshold state: "
                  << (aggregator.engine().thresholdExceeded(5000.0)
                          ? "threshold exceeded"
                          : "threshold not exceeded")
                  << '\n';

        std::cout << "\nComplexity: O(1) update time and O(1) aggregate state per observation.\n";
        std::cout << "The transaction index uses O(n) memory to enforce duplicate IDs.\n";
    }
    catch (const std::exception& error) {
        std::cerr << "Fatal processing error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
