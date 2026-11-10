#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <map>
#include <mutex>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Materialized View Governance and Refresh Engine
 *
 * C++17 implementation.
 *
 * Implements:
 * - Source-table records
 * - Materialized aggregate snapshots
 * - Full refresh
 * - Incremental refresh using change events
 * - Insert, update and delete handling
 * - Snapshot generations
 * - Refresh failure isolation
 * - Query execution against snapshots
 * - Dependency-aware refresh planning
 * - Refresh audit
 *
 * Compile:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic materialized_views.cpp -o materialized_views
 */

using Clock = std::chrono::steady_clock;
using Timestamp = std::chrono::system_clock::time_point;

class ValidationError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class RefreshError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

enum class Operation {
    Insert,
    Update,
    Delete
};

enum class RefreshMode {
    Full,
    Incremental
};

enum class RefreshStatus {
    Success,
    Failed,
    Skipped
};

struct Sale {
    int id;
    int productId;
    std::string category;
    std::string region;
    int quantity;
    double unitPrice;
    Timestamp createdAt;

    double revenue() const {
        return quantity * unitPrice;
    }

    void validate() const {
        if (id <= 0 || productId <= 0) {
            throw ValidationError("Identifiers must be positive.");
        }

        if (category.empty() || region.empty()) {
            throw ValidationError("Grouping fields are required.");
        }

        if (quantity <= 0 || !std::isfinite(unitPrice) ||
            unitPrice < 0) {
            throw ValidationError("Invalid sale values.");
        }
    }
};

struct ChangeEvent {
    std::uint64_t version;
    Operation operation;
    std::optional<Sale> before;
    std::optional<Sale> after;
};

struct Aggregate {
    std::uint64_t count = 0;
    std::int64_t quantity = 0;
    double revenue = 0.0;

    void add(const Sale& sale) {
        ++count;
        quantity += sale.quantity;
        revenue += sale.revenue();
    }

    void remove(const Sale& sale) {
        if (count == 0 || quantity < sale.quantity) {
            throw RefreshError("Invalid aggregate subtraction.");
        }

        --count;
        quantity -= sale.quantity;
        revenue -= sale.revenue();

        if (count == 0) {
            quantity = 0;
            revenue = 0.0;
        }
    }
};

using GroupKey = std::pair<std::string, std::string>;
using AggregateMap = std::map<GroupKey, Aggregate>;

struct Snapshot {
    AggregateMap rows;
    std::uint64_t generation = 0;
    std::uint64_t sourceVersion = 0;
    Timestamp refreshedAt{};
};

struct RefreshResult {
    std::string viewName;
    RefreshMode mode;
    RefreshStatus status;
    std::size_t recordsProcessed;
    double durationMs;
    std::string error;
};

class SourceTable {
private:
    std::unordered_map<int, Sale> records_;
    std::vector<ChangeEvent> journal_;
    std::uint64_t version_ = 0;

    mutable std::mutex mutex_;

    void publish(
        Operation operation,
        std::optional<Sale> before,
        std::optional<Sale> after
    ) {
        journal_.push_back({
            ++version_,
            operation,
            std::move(before),
            std::move(after)
        });
    }

public:
    void insert(const Sale& sale) {
        sale.validate();
        std::lock_guard<std::mutex> guard(mutex_);

        if (records_.count(sale.id)) {
            throw ValidationError("Duplicate sale identifier.");
        }

        records_.emplace(sale.id, sale);
        publish(Operation::Insert, std::nullopt, sale);
    }

    void update(const Sale& sale) {
        sale.validate();
        std::lock_guard<std::mutex> guard(mutex_);

        auto it = records_.find(sale.id);

        if (it == records_.end()) {
            throw ValidationError("Sale not found.");
        }

        Sale previous = it->second;
        it->second = sale;

        publish(Operation::Update, previous, sale);
    }

    void remove(int id) {
        std::lock_guard<std::mutex> guard(mutex_);

        auto it = records_.find(id);

        if (it == records_.end()) {
            throw ValidationError("Sale not found.");
        }

        Sale previous = it->second;
        records_.erase(it);

        publish(Operation::Delete, previous, std::nullopt);
    }

    std::pair<std::vector<Sale>, std::uint64_t> snapshot() const {
        std::lock_guard<std::mutex> guard(mutex_);

        std::vector<Sale> rows;
        rows.reserve(records_.size());

        for (const auto& [id, sale] : records_) {
            rows.push_back(sale);
        }

        return {rows, version_};
    }

    std::vector<ChangeEvent> changesSince(
        std::uint64_t version
    ) const {
        std::lock_guard<std::mutex> guard(mutex_);

        std::vector<ChangeEvent> changes;

        for (const auto& event : journal_) {
            if (event.version > version) {
                changes.push_back(event);
            }
        }

        return changes;
    }

    std::uint64_t currentVersion() const {
        std::lock_guard<std::mutex> guard(mutex_);
        return version_;
    }
};

class MaterializedView {
private:
    std::string name_;
    const SourceTable& source_;
    Snapshot snapshot_;
    mutable std::mutex mutex_;

    GroupKey keyFor(const Sale& sale) const {
        return {sale.category, sale.region};
    }

    AggregateMap build(
        const std::vector<Sale>& records
    ) const {
        AggregateMap result;

        for (const Sale& sale : records) {
            result[keyFor(sale)].add(sale);
        }

        return result;
    }

    void applyChange(
        AggregateMap& rows,
        const ChangeEvent& event
    ) const {
        if (event.before) {
            auto key = keyFor(*event.before);
            auto it = rows.find(key);

            if (it == rows.end()) {
                throw RefreshError("Missing previous aggregate.");
            }

            it->second.remove(*event.before);

            if (it->second.count == 0) {
                rows.erase(it);
            }
        }

        if (event.after) {
            rows[keyFor(*event.after)].add(*event.after);
        }
    }

public:
    MaterializedView(
        std::string name,
        const SourceTable& source
    )
        : name_(std::move(name)), source_(source) {
        if (name_.empty()) {
            throw ValidationError("View name is required.");
        }
    }

    const std::string& name() const {
        return name_;
    }

    Snapshot read() const {
        std::lock_guard<std::mutex> guard(mutex_);
        return snapshot_;
    }

    bool stale() const {
        return read().sourceVersion < source_.currentVersion();
    }

    RefreshResult refresh(RefreshMode mode) {
        auto started = Clock::now();

        try {
            auto [records, version] = source_.snapshot();
            Snapshot previous = read();

            if (mode == RefreshMode::Incremental &&
                previous.generation > 0) {

                auto changes = source_.changesSince(
                    previous.sourceVersion
                );

                if (changes.empty()) {
                    return {
                        name_, mode, RefreshStatus::Skipped,
                        0, 0.0, ""
                    };
                }

                AggregateMap candidate = previous.rows;

                // Validate event continuity before applying changes.
                std::uint64_t expected = previous.sourceVersion + 1;

                for (const auto& event : changes) {
                    if (event.version != expected++) {
                        throw RefreshError(
                            "Change journal contains a version gap."
                        );
                    }

                    applyChange(candidate, event);
                }

                std::lock_guard<std::mutex> guard(mutex_);

                if (snapshot_.generation != previous.generation) {
                    throw RefreshError(
                        "Concurrent refresh changed the snapshot."
                    );
                }

                snapshot_ = {
                    std::move(candidate),
                    previous.generation + 1,
                    version,
                    std::chrono::system_clock::now()
                };

                auto duration = std::chrono::duration<double, std::milli>(
                    Clock::now() - started
                ).count();

                return {
                    name_, mode, RefreshStatus::Success,
                    changes.size(), duration, ""
                };
            }

            AggregateMap candidate = build(records);

            {
                std::lock_guard<std::mutex> guard(mutex_);

                snapshot_ = {
                    std::move(candidate),
                    previous.generation + 1,
                    version,
                    std::chrono::system_clock::now()
                };
            }

            auto duration = std::chrono::duration<double, std::milli>(
                Clock::now() - started
            ).count();

            return {
                name_, mode, RefreshStatus::Success,
                records.size(), duration, ""
            };

        } catch (const std::exception& error) {
            auto duration = std::chrono::duration<double, std::milli>(
                Clock::now() - started
            ).count();

            return {
                name_, mode, RefreshStatus::Failed,
                0, duration, error.what()
            };
        }
    }

    std::vector<std::pair<GroupKey, Aggregate>> query(
        const std::optional<std::string>& category = std::nullopt
    ) const {
        Snapshot current = read();

        std::vector<std::pair<GroupKey, Aggregate>> result;

        for (const auto& row : current.rows) {
            if (category && row.first.first != *category) {
                continue;
            }

            result.push_back(row);
        }

        return result;
    }
};

class RefreshPlanner {
private:
    std::map<std::string, MaterializedView*> views_;
    std::map<std::string, std::set<std::string>> dependencies_;

    void visit(
        const std::string& name,
        std::set<std::string>& visiting,
        std::set<std::string>& visited,
        std::vector<MaterializedView*>& order
    ) const {
        if (visiting.count(name)) {
            throw ValidationError("Circular dependency detected.");
        }

        if (visited.count(name)) return;

        auto view = views_.find(name);

        if (view == views_.end()) {
            throw ValidationError("Unknown materialized view.");
        }

        visiting.insert(name);

        auto dependencies = dependencies_.find(name);

        if (dependencies != dependencies_.end()) {
            for (const auto& dependency : dependencies->second) {
                visit(dependency, visiting, visited, order);
            }
        }

        visiting.erase(name);
        visited.insert(name);
        order.push_back(view->second);
    }

public:
    void registerView(
        MaterializedView& view,
        std::set<std::string> dependencies = {}
    ) {
        if (views_.count(view.name())) {
            throw ValidationError("Duplicate view registration.");
        }

        views_[view.name()] = &view;
        dependencies_[view.name()] = std::move(dependencies);
    }

    std::vector<RefreshResult> execute(
        const std::string& target,
        RefreshMode mode
    ) const {
        std::vector<MaterializedView*> order;
        std::set<std::string> visiting;
        std::set<std::string> visited;

        visit(target, visiting, visited, order);

        std::vector<RefreshResult> results;

        for (auto* view : order) {
            auto result = view->refresh(mode);
            results.push_back(result);

            if (result.status == RefreshStatus::Failed) {
                break;
            }
        }

        return results;
    }
};

std::string modeName(RefreshMode mode) {
    return mode == RefreshMode::Full
        ? "FULL"
        : "INCREMENTAL";
}

std::string statusName(RefreshStatus status) {
    switch (status) {
        case RefreshStatus::Success: return "SUCCESS";
        case RefreshStatus::Failed: return "FAILED";
        case RefreshStatus::Skipped: return "SKIPPED";
    }

    return "UNKNOWN";
}

Sale makeSale(
    int id,
    int product,
    std::string category,
    std::string region,
    int quantity,
    double price
) {
    return {
        id,
        product,
        std::move(category),
        std::move(region),
        quantity,
        price,
        std::chrono::system_clock::now()
    };
}

void printReport(const MaterializedView& view) {
    std::cout << "\nREPORT: " << view.name() << "\n";

    auto snapshot = view.read();

    std::cout << "Generation: "
              << snapshot.generation << "\n";

    std::cout << "Source version: "
              << snapshot.sourceVersion << "\n";

    std::cout << std::left
              << std::setw(18) << "Category"
              << std::setw(15) << "Region"
              << std::setw(12) << "Count"
              << std::setw(12) << "Quantity"
              << "Revenue\n";

    for (const auto& [key, aggregate] : snapshot.rows) {
        std::cout << std::left
                  << std::setw(18) << key.first
                  << std::setw(15) << key.second
                  << std::setw(12) << aggregate.count
                  << std::setw(12) << aggregate.quantity
                  << std::fixed << std::setprecision(2)
                  << aggregate.revenue << "\n";
    }
}

void testEngine() {
    SourceTable source;

    source.insert(makeSale(
        1, 101, "Electronics", "North", 3, 1200
    ));

    source.insert(makeSale(
        2, 102, "Furniture", "South", 2, 850
    ));

    MaterializedView view("sales_summary", source);

    auto initial = view.refresh(RefreshMode::Full);

    if (initial.status != RefreshStatus::Success) {
        throw std::runtime_error("Initial refresh failed.");
    }

    assert(view.read().rows.at(
        {"Electronics", "North"}
    ).revenue == 3600);

    source.insert(makeSale(
        3, 101, "Electronics", "North", 2, 1200
    ));

    assert(view.stale());

    auto incremental = view.refresh(RefreshMode::Incremental);

    if (incremental.status != RefreshStatus::Success) {
        throw std::runtime_error("Incremental refresh failed.");
    }

    assert(!view.stale());

    assert(view.read().rows.at(
        {"Electronics", "North"}
    ).revenue == 6000);

    source.update(makeSale(
        3, 101, "Electronics", "South", 2, 1200
    ));

    view.refresh(RefreshMode::Incremental);

    assert(
        view.read().rows.at(
            {"Electronics", "South"}
        ).revenue == 2400
    );

    source.remove(3);
    view.refresh(RefreshMode::Incremental);

    assert(
        view.read().rows.at(
            {"Electronics", "North"}
        ).revenue == 3600
    );

    std::cout << "\nAll C++ validation tests passed.\n";
}

int main() {
    try {
        SourceTable source;

        source.insert(makeSale(
            1, 101, "Electronics", "North", 3, 1200
        ));

        source.insert(makeSale(
            2, 102, "Furniture", "South", 2, 850
        ));

        source.insert(makeSale(
            3, 101, "Electronics", "North", 1, 1200
        ));

        source.insert(makeSale(
            4, 103, "Clothing", "West", 5, 90
        ));

        source.insert(makeSale(
            5, 104, "Electronics", "East", 2, 700
        ));

        source.insert(makeSale(
            6, 102, "Furniture", "South", 1, 850
        ));

        MaterializedView categoryView(
            "sales_by_category_region",
            source
        );

        MaterializedView regionalView(
            "sales_by_region_category",
            source
        );

        RefreshPlanner planner;

        planner.registerView(categoryView);

        planner.registerView(
            regionalView,
            {"sales_by_category_region"}
        );

        std::cout << "INITIAL FULL REFRESH\n";

        for (const auto& result : planner.execute(
            "sales_by_region_category",
            RefreshMode::Full
        )) {
            std::cout
                << result.viewName << " "
                << statusName(result.status) << " "
                << result.durationMs << " ms\n";
        }

        printReport(categoryView);

        std::cout << "\nSOURCE CHANGE\n";

        source.insert(makeSale(
            7, 105, "Clothing", "North", 4, 120
        ));

        std::cout << "Stale: "
                  << std::boolalpha
                  << categoryView.stale() << "\n";

        std::cout << "\nINCREMENTAL REFRESH\n";

        for (const auto& result : planner.execute(
            "sales_by_region_category",
            RefreshMode::Incremental
        )) {
            std::cout
                << result.viewName << " "
                << statusName(result.status) << " "
                << result.recordsProcessed << " changes "
                << result.durationMs << " ms\n";
        }

        printReport(regionalView);

        std::cout << "\nVALIDATION\n";
        testEngine();

    } catch (const std::exception& error) {
        std::cerr << "Application error: "
                  << error.what() << "\n";

        return 1;
    }

    return 0;
}
