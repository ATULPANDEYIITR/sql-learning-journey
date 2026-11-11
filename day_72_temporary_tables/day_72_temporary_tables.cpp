#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

/*
 * Temporary Tables: C++17 staging and repository governance.
 *
 * Models session-local temporary staging, record validation,
 * atomic promotion, rollback, and independent database sessions.
 *
 * Compile:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic temporary_tables.cpp -o temporary_tables
 *
 * Run:
 * ./temporary_tables
 */

enum class RecordStatus {
    PENDING,
    ACCEPTED,
    REJECTED
};

enum class SessionStatus {
    OPEN,
    CLOSED
};

struct ProductRecord {
    std::string externalId;
    std::string product;
    int quantity;
    double unitPrice;
};

struct StagedRecord {
    ProductRecord record;
    RecordStatus status = RecordStatus::PENDING;
    std::string reason;
};

struct PermanentRecord {
    ProductRecord record;
    double totalValue;
};

std::string toString(RecordStatus status) {
    switch (status) {
        case RecordStatus::PENDING:
            return "PENDING";
        case RecordStatus::ACCEPTED:
            return "ACCEPTED";
        case RecordStatus::REJECTED:
            return "REJECTED";
    }
    return "UNKNOWN";
}

class StagingException : public std::runtime_error {
public:
    explicit StagingException(const std::string& message)
        : std::runtime_error(message) {}
};

class PermanentRepository {
private:
    std::unordered_map<std::string, PermanentRecord> products_;

public:
    bool contains(const std::string& id) const {
        return products_.find(id) != products_.end();
    }

    /*
     * Build a candidate copy before replacing permanent state.
     * This provides strong exception safety for this in-memory model.
     */
    std::size_t promote(
        const std::vector<ProductRecord>& records
    ) {
        auto candidate = products_;

        for (const auto& record : records) {
            if (candidate.find(record.externalId) != candidate.end()) {
                throw StagingException(
                    "Duplicate permanent identifier: " +
                    record.externalId
                );
            }

            candidate.emplace(
                record.externalId,
                PermanentRecord{
                    record,
                    record.quantity * record.unitPrice
                }
            );
        }

        products_.swap(candidate);
        return records.size();
    }

    void report() const {
        double totalValue = 0.0;

        for (const auto& [id, item] : products_) {
            totalValue += item.totalValue;
        }

        std::cout
            << "Permanent records: " << products_.size()
            << "\nInventory value: "
            << std::fixed << std::setprecision(2)
            << totalValue << '\n';
    }

    const auto& records() const {
        return products_;
    }
};

class TemporarySession {
private:
    std::string sessionId_;
    SessionStatus status_ = SessionStatus::OPEN;

    // These containers belong to this session object only.
    std::vector<StagedRecord> staging_;
    std::unordered_map<std::string, std::size_t> index_;

    PermanentRepository& repository_;
    static constexpr std::size_t MAX_BATCH_SIZE = 100000;

    void ensureOpen() const {
        if (status_ != SessionStatus::OPEN) {
            throw StagingException("Session is closed");
        }
    }

public:
    TemporarySession(
        std::string sessionId,
        PermanentRepository& repository
    )
        : sessionId_(std::move(sessionId)),
          repository_(repository) {}

    void load(const std::vector<ProductRecord>& records) {
        ensureOpen();

        if (records.empty()) {
            throw StagingException("Empty batch is not allowed");
        }

        if (records.size() > MAX_BATCH_SIZE) {
            throw StagingException("Batch size limit exceeded");
        }

        if (!staging_.empty()) {
            throw StagingException(
                "Clear staging before loading another batch"
            );
        }

        for (const auto& record : records) {
            staging_.push_back(StagedRecord{
                record,
                RecordStatus::PENDING,
                "Awaiting validation"
            });
        }

        std::cout
            << "Session " << sessionId_
            << " loaded " << staging_.size()
            << " records\n";
    }

    void validate() {
        ensureOpen();

        std::set<std::string> seen;

        for (auto& staged : staging_) {
            const auto& record = staged.record;
            std::string reason = "Valid record";

            if (record.externalId.empty()) {
                reason = "Missing external identifier";
            } else if (record.product.empty()) {
                reason = "Missing product name";
            } else if (record.quantity <= 0) {
                reason = "Quantity must be positive";
            } else if (
                !std::isfinite(record.unitPrice) ||
                record.unitPrice < 0
            ) {
                reason = "Invalid unit price";
            } else if (!seen.insert(record.externalId).second) {
                reason = "Duplicate identifier in batch";
            } else if (repository_.contains(record.externalId)) {
                reason = "Identifier already exists";
            }

            staged.reason = reason;
            staged.status = reason == "Valid record"
                ? RecordStatus::ACCEPTED
                : RecordStatus::REJECTED;
        }
    }

    std::size_t promote() {
        ensureOpen();

        std::vector<ProductRecord> accepted;

        for (const auto& staged : staging_) {
            if (staged.status == RecordStatus::ACCEPTED) {
                accepted.push_back(staged.record);
            }
        }

        // Repository promotion either succeeds completely or leaves
        // the original permanent records unchanged.
        return repository_.promote(accepted);
    }

    void displayStaging() const {
        ensureOpen();

        std::cout << "\nStaging records for " << sessionId_ << '\n';

        for (const auto& staged : staging_) {
            std::cout
                << std::left
                << std::setw(12) << staged.record.externalId
                << std::setw(20) << staged.record.product
                << std::setw(12) << toString(staged.status)
                << staged.reason << '\n';
        }
    }

    void report() const {
        ensureOpen();

        std::size_t accepted = 0;
        std::size_t rejected = 0;

        for (const auto& staged : staging_) {
            if (staged.status == RecordStatus::ACCEPTED) {
                ++accepted;
            } else if (staged.status == RecordStatus::REJECTED) {
                ++rejected;
            }
        }

        std::cout
            << "\nSession: " << sessionId_
            << "\nStaged: " << staging_.size()
            << "\nAccepted: " << accepted
            << "\nRejected: " << rejected << '\n';
    }

    void truncate() {
        ensureOpen();
        staging_.clear();
        index_.clear();
        std::cout << "Session staging truncated\n";
    }

    void close() {
        if (status_ == SessionStatus::CLOSED) {
            return;
        }

        staging_.clear();
        index_.clear();
        status_ = SessionStatus::CLOSED;
    }

    ~TemporarySession() {
        close();
    }
};

int main() {
    try {
        PermanentRepository repository;

        std::vector<ProductRecord> batch = {
            {"P1001", "Laptop", 5, 75000.00},
            {"P1002", "Monitor", 10, 12000.00},
            {"P1003", "Keyboard", 20, 1500.00},
            {"P1001", "Duplicate Laptop", 2, 70000.00},
            {"P1004", "Invalid Quantity", 0, 500.00},
            {"P1005", "Invalid Price", 2, -100.00}
        };

        {
            TemporarySession sessionA("SESSION-A", repository);

            sessionA.load(batch);
            sessionA.validate();
            sessionA.displayStaging();
            sessionA.report();

            const std::size_t inserted = sessionA.promote();

            std::cout
                << "\nSuccessfully promoted: "
                << inserted << '\n';

            // New batch uses the same session after truncation.
            sessionA.truncate();

            sessionA.load({
                {"P1006", "Mouse", 15, 800.00}
            });

            sessionA.validate();

            std::cout
                << "Second batch inserted: "
                << sessionA.promote() << '\n';

            sessionA.report();
        }

        // SESSION-A staging has been destroyed.
        {
            TemporarySession sessionB("SESSION-B", repository);

            sessionB.load({
                {"P1007", "Webcam", 4, 2500.00}
            });

            sessionB.validate();
            std::cout
                << "\nSESSION-B inserted: "
                << sessionB.promote() << '\n';

            sessionB.report();
        }

        std::cout << "\nPermanent repository report\n";
        repository.report();

        // Verify duplicate protection.
        try {
            repository.promote({
                {"P1001", "Conflicting Laptop", 1, 1000.00}
            });

            throw StagingException(
                "Duplicate protection failed"
            );
        } catch (const StagingException& error) {
            std::cout
                << "\nDuplicate protection: "
                << error.what() << '\n';
        }

    } catch (const std::exception& error) {
        std::cerr
            << "Application error: "
            << error.what() << '\n';

        return 1;
    }

    return 0;
}
