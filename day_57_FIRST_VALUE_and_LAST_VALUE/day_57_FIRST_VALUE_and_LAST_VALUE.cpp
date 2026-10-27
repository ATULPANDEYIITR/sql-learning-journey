#include <algorithm>
#include <chrono>
#include <exception>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

struct Observation {
    std::string repository;
    int timestamp;
    std::string metric;
    long long value;
};

void validate(const std::vector<Observation>& rows) {
    if (rows.empty()) {
        throw std::invalid_argument("Observation collection cannot be empty.");
    }

    for (const auto& row : rows) {
        if (row.repository.empty()) {
            throw std::invalid_argument("Repository cannot be empty.");
        }
        if (row.metric.empty()) {
            throw std::invalid_argument("Metric cannot be empty.");
        }
        if (row.value < 0) {
            throw std::invalid_argument("Metric values cannot be negative.");
        }
    }
}

std::vector<Observation> ordered(std::vector<Observation> rows) {
    std::sort(rows.begin(), rows.end(),
              [](const Observation& a, const Observation& b) {
                  if (a.repository != b.repository) {
                      return a.repository < b.repository;
                  }
                  return a.timestamp < b.timestamp;
              });
    return rows;
}

struct WindowResult {
    Observation observation;
    long long firstValue;
    long long defaultLastValue;
    long long fullPartitionLastValue;
    long long framedLastValue;
};

std::vector<WindowResult> evaluate(
    const std::vector<Observation>& rows,
    std::size_t precedingRows) {

    std::vector<WindowResult> result;
    result.reserve(rows.size());

    std::map<std::string, std::vector<std::size_t>> partitions;

    for (std::size_t i = 0; i < rows.size(); ++i) {
        partitions[rows[i].repository].push_back(i);
    }

    for (const auto& [repository, indexes] : partitions) {
        const auto firstIndex = indexes.front();
        const auto finalIndex = indexes.back();

        for (std::size_t position = 0; position < indexes.size(); ++position) {
            const auto currentIndex = indexes[position];

            const auto frameStart =
                position > precedingRows ? position - precedingRows : 0;
            const auto frameEnd = position;

            WindowResult item{
                rows[currentIndex],
                rows[firstIndex].value,
                rows[currentIndex].value,
                rows[finalIndex].value,
                rows[indexes[frameEnd]].value
            };

            result.push_back(item);
        }
    }

    std::sort(result.begin(), result.end(),
              [](const WindowResult& a, const WindowResult& b) {
                  if (a.observation.repository != b.observation.repository) {
                      return a.observation.repository < b.observation.repository;
                  }
                  return a.observation.timestamp < b.observation.timestamp;
              });

    return result;
}

void printResults(const std::vector<WindowResult>& results) {
    std::cout << std::left
              << std::setw(15) << "Repository"
              << std::setw(10) << "Time"
              << std::setw(10) << "Value"
              << std::setw(14) << "FIRST_VALUE"
              << std::setw(18) << "Default LAST"
              << std::setw(18) << "Full LAST"
              << std::setw(18) << "Framed LAST"
              << '\n';

    std::cout << std::string(103, '-') << '\n';

    for (const auto& row : results) {
        std::cout << std::left
                  << std::setw(15) << row.observation.repository
                  << std::setw(10) << row.observation.timestamp
                  << std::setw(10) << row.observation.value
                  << std::setw(14) << row.firstValue
                  << std::setw(18) << row.defaultLastValue
                  << std::setw(18) << row.fullPartitionLastValue
                  << std::setw(18) << row.framedLastValue
                  << '\n';
    }
}

int main() {
    try {
        std::vector<Observation> observations{
            {"payment-api", 1, "deployments", 4},
            {"payment-api", 2, "deployments", 7},
            {"payment-api", 3, "deployments", 11},
            {"search-api", 1, "deployments", 3},
            {"search-api", 2, "deployments", 6},
            {"search-api", 3, "deployments", 5}
        };

        validate(observations);
        const auto rows = ordered(observations);
        const auto results = evaluate(rows, 2);

        printResults(results);

        // Explicit semantic checks.
        if (results[0].firstValue != 4 ||
            results[2].firstValue != 4 ||
            results[3].firstValue != 3) {
            throw std::logic_error("FIRST_VALUE invariant failed.");
        }

        if (results[0].fullPartitionLastValue != 11 ||
            results[1].fullPartitionLastValue != 11 ||
            results[3].fullPartitionLastValue != 5) {
            throw std::logic_error("Full-partition LAST_VALUE invariant failed.");
        }

        // The default ordered frame terminates at CURRENT ROW.
        if (results[1].defaultLastValue != 7 ||
            results[2].defaultLastValue != 11) {
            throw std::logic_error("Default-frame LAST_VALUE invariant failed.");
        }

        std::cout << "\nAll window-frame invariants passed.\n";
        std::cout << "Complexity: O(n log n) for ordering and O(n) for evaluation.\n";
        std::cout << "Memory: O(n) for partitions and result records.\n";
        std::cout << "Security: input is treated as data; no shell or dynamic execution is used.\n";

        return 0;
    }
    catch (const std::exception& ex) {
        std::cerr << "Failure: " << ex.what() << '\n';
        return 1;
    }
}
