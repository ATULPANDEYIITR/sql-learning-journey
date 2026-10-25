#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

struct Record {
    int id;
    std::string customer;
    double score;
};

struct BucketedRecord {
    Record record;
    int bucket;
    int bucketCount;
};

class InvalidBucketCount : public std::invalid_argument {
public:
    explicit InvalidBucketCount(const std::string& message)
        : std::invalid_argument(message) {}
};

void validateBucketCount(int bucketCount) {
    if (bucketCount <= 0) {
        throw InvalidBucketCount("bucket count must be positive");
    }
}

std::vector<BucketedRecord> ntile(
    std::vector<Record> records,
    int bucketCount
) {
    validateBucketCount(bucketCount);

    std::sort(
        records.begin(),
        records.end(),
        [](const Record& a, const Record& b) {
            if (a.score != b.score) {
                return a.score > b.score;
            }
            return a.id < b.id;
        }
    );

    const int total = static_cast<int>(records.size());

    if (total == 0) {
        return {};
    }

    const int baseSize = total / bucketCount;
    const int remainder = total % bucketCount;

    std::vector<BucketedRecord> result;
    result.reserve(records.size());

    int position = 0;

    for (int bucket = 1; bucket <= bucketCount; ++bucket) {
        const int size = baseSize + (bucket <= remainder ? 1 : 0);

        for (int i = 0; i < size && position < total; ++i) {
            result.push_back({
                records[position],
                bucket,
                bucketCount
            });
            ++position;
        }
    }

    return result;
}

std::map<int, std::vector<Record>> groupByBucket(
    const std::vector<BucketedRecord>& bucketed
) {
    std::map<int, std::vector<Record>> groups;

    for (const auto& item : bucketed) {
        groups[item.bucket].push_back(item.record);
    }

    return groups;
}

void printBucketStatistics(
    const std::vector<BucketedRecord>& bucketed
) {
    const auto groups = groupByBucket(bucketed);

    std::cout << "Bucket statistics\n";
    std::cout << std::fixed << std::setprecision(2);

    for (const auto& [bucket, records] : groups) {
        double total = 0.0;
        double minimum = records.front().score;
        double maximum = records.front().score;

        for (const auto& record : records) {
            total += record.score;
            minimum = std::min(minimum, record.score);
            maximum = std::max(maximum, record.score);
        }

        const double average = total / records.size();

        std::cout
            << "Bucket " << bucket
            << " | count=" << records.size()
            << " | min=" << minimum
            << " | max=" << maximum
            << " | avg=" << average
            << '\n';
    }
}

bool isValidNtile(
    const std::vector<Record>& records,
    int bucketCount
) {
    const auto bucketed = ntile(records, bucketCount);

    if (bucketed.size() != records.size()) {
        return false;
    }

    std::vector<int> sizes(bucketCount + 1, 0);

    for (const auto& item : bucketed) {
        ++sizes[item.bucket];
    }

    int minimum = sizes[1];
    int maximum = sizes[1];

    for (int bucket = 1; bucket <= bucketCount; ++bucket) {
        minimum = std::min(minimum, sizes[bucket]);
        maximum = std::max(maximum, sizes[bucket]);
    }

    if (!records.empty() && maximum - minimum > 1) {
        return false;
    }

    for (std::size_t i = 1; i < bucketed.size(); ++i) {
        if (bucketed[i - 1].record.score <
            bucketed[i].record.score) {
            return false;
        }
    }

    return true;
}

std::unordered_map<int, std::string> segmentDeciles(
    const std::vector<Record>& records
) {
    const auto bucketed = ntile(records, 10);

    const std::map<int, std::string> labels = {
        {1, "Top 10%"},
        {2, "High"},
        {3, "High"},
        {4, "Upper-Middle"},
        {5, "Upper-Middle"},
        {6, "Lower-Middle"},
        {7, "Lower-Middle"},
        {8, "Low"},
        {9, "Low"},
        {10, "Bottom 10%"}
    };

    std::unordered_map<int, std::string> result;

    for (const auto& item : bucketed) {
        result[item.record.id] = labels.at(item.bucket);
    }

    return result;
}

int main() {
    try {
        const std::vector<Record> records = {
            {101, "Asha", 96.0},
            {102, "Bharat", 82.0},
            {103, "Chirag", 91.0},
            {104, "Divya", 74.0},
            {105, "Esha", 88.0},
            {106, "Farhan", 67.0},
            {107, "Gita", 91.0},
            {108, "Harsh", 59.0},
            {109, "Isha", 84.0},
            {110, "Jay", 72.0},
            {111, "Kiran", 95.0},
            {112, "Lalit", 63.0}
        };

        const auto quartiles = ntile(records, 4);

        std::cout << "QUARTILES\n";
        for (const auto& item : quartiles) {
            std::cout
                << item.record.customer
                << " score=" << item.record.score
                << " quartile=" << item.bucket
                << '\n';
        }

        std::cout << '\n';
        printBucketStatistics(quartiles);

        const auto deciles = ntile(records, 10);

        std::cout << "\nDECILES\n";
        for (const auto& item : deciles) {
            std::cout
                << item.record.customer
                << " score=" << item.record.score
                << " decile=" << item.bucket
                << '\n';
        }

        std::cout << "\nDECILE SEGMENTS\n";
        const auto segments = segmentDeciles(records);

        for (const auto& record : records) {
            std::cout
                << record.id
                << " -> "
                << segments.at(record.id)
                << '\n';
        }

        if (!isValidNtile(records, 4) ||
            !isValidNtile(records, 10) ||
            !isValidNtile({}, 5)) {
            throw std::runtime_error("NTILE invariant validation failed");
        }

        try {
            ntile(records, 0);
        } catch (const InvalidBucketCount&) {
            std::cout << "\nInvalid bucket count rejected.\n";
        }

        std::cout << "NTILE validation passed.\n";
    }
    catch (const std::exception& error) {
        std::cerr << "Processing failed: "
                  << error.what()
                  << '\n';
        return 1;
    }

    return 0;
}
