#include <algorithm>
#include <chrono>
#include <cctype>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * DEFAULT Constraints: Repository Metadata Service
 *
 * Technical case study:
 *
 * A distributed repository metadata service stores projects and operational
 * records. New records require sensible values for fields such as status,
 * priority, timestamps, UUID-like identifiers, and activation state.
 *
 * The implementation models:
 *
 * - literal defaults
 * - generated defaults
 * - timestamp defaults
 * - UUID defaults
 * - omission versus explicit values
 * - NULL-like optional values
 * - validation
 * - default ownership
 * - schema policy changes
 * - historical data migration
 * - update semantics
 * - transaction-like batch insertion
 *
 * C++17 is sufficient.
 */

using namespace std;

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

string utcTimestamp() {
    using namespace chrono;

    const auto now = system_clock::now();
    const auto time = system_clock::to_time_t(now);

    tm utc_tm{};

#ifdef _WIN32
    gmtime_s(&utc_tm, &time);
#else
    gmtime_r(&time, &utc_tm);
#endif

    const auto milliseconds =
        duration_cast<milliseconds>(now.time_since_epoch()) % 1000;

    ostringstream output;
    output << put_time(&utc_tm, "%Y-%m-%dT%H:%M:%S")
           << '.'
           << setw(3)
           << setfill('0')
           << milliseconds.count()
           << 'Z';

    return output.str();
}

string generateUuidLikeId() {
    /*
     * This is a UUID-shaped identifier generator for a self-contained C++17
     * case study. Production systems should use a standards-compliant UUID
     * implementation or generate identifiers in the persistence layer when
     * database ownership is preferred.
     */
    static random_device randomDevice;
    static mt19937 generator(randomDevice());
    static uniform_int_distribution<int> hexDistribution(0, 15);

    const char* hex = "0123456789abcdef";

    string value;
    value.reserve(36);

    for (int i = 0; i < 36; ++i) {
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            value.push_back('-');
        } else {
            value.push_back(hex[hexDistribution(generator)]);
        }
    }

    // Set UUID version/variant bits in the generated textual representation.
    value[14] = '4';

    const string variants = "89ab";
    value[19] = variants[hexDistribution(generator) % 4];

    return value;
}

void heading(const string& title) {
    cout << "\n" << string(78, '=') << "\n"
         << title << "\n"
         << string(78, '=') << "\n";
}

void subsection(const string& title) {
    cout << "\n--- " << title << " ---\n";
}


// ---------------------------------------------------------------------------
// OptionalValue models the distinction between:
//
// 1. field omitted from an INSERT
// 2. field explicitly supplied with a value
// 3. field explicitly supplied as NULL
//
// A DEFAULT is normally selected for case 1, not automatically for case 3.
// ---------------------------------------------------------------------------

template <typename T>
class OptionalValue {
public:
    enum class State {
        Omitted,
        Null,
        Value
    };

    static OptionalValue omitted() {
        return OptionalValue(State::Omitted, nullopt);
    }

    static OptionalValue nullValue() {
        return OptionalValue(State::Null, nullopt);
    }

    static OptionalValue value(T value) {
        return OptionalValue(State::Value, std::move(value));
    }

    State state() const {
        return state_;
    }

    const optional<T>& value() const {
        return value_;
    }

private:
    OptionalValue(State state, optional<T> value)
        : state_(state), value_(std::move(value)) {}

    State state_;
    optional<T> value_;
};


// ---------------------------------------------------------------------------
// Repository domain
// ---------------------------------------------------------------------------

enum class RepositoryStatus {
    Active,
    Archived,
    Maintenance
};

string toString(RepositoryStatus status) {
    switch (status) {
        case RepositoryStatus::Active:
            return "active";
        case RepositoryStatus::Archived:
            return "archived";
        case RepositoryStatus::Maintenance:
            return "maintenance";
    }

    throw logic_error("Unknown repository status");
}

bool validStatus(RepositoryStatus status) {
    return status == RepositoryStatus::Active ||
           status == RepositoryStatus::Archived ||
           status == RepositoryStatus::Maintenance;
}

struct RepositoryInsert {
    string name;

    OptionalValue<RepositoryStatus> status =
        OptionalValue<RepositoryStatus>::omitted();

    OptionalValue<int> priority =
        OptionalValue<int>::omitted();

    OptionalValue<bool> enabled =
        OptionalValue<bool>::omitted();

    OptionalValue<string> description =
        OptionalValue<string>::omitted();

    OptionalValue<string> id =
        OptionalValue<string>::omitted();
};

struct RepositoryRecord {
    string id;
    string name;
    RepositoryStatus status;
    int priority;
    bool enabled;
    optional<string> description;
    string createdAt;
};


// ---------------------------------------------------------------------------
// Default policy
// ---------------------------------------------------------------------------

struct DefaultPolicy {
    string column;
    string owner;
    string expression;
    string purpose;
};

vector<DefaultPolicy> repositoryDefaultPolicies() {
    return {
        {
            "id",
            "application",
            "generated UUID",
            "Create a globally unique repository identifier before persistence."
        },
        {
            "status",
            "database",
            "'active'",
            "Give a new repository a valid operational state."
        },
        {
            "priority",
            "database",
            "5",
            "Provide a neutral operational priority when none is specified."
        },
        {
            "enabled",
            "database",
            "true",
            "Make a newly created repository available by default."
        },
        {
            "created_at",
            "database",
            "CURRENT_TIMESTAMP",
            "Make persistence time authoritative at the storage boundary."
        }
    };
}


// ---------------------------------------------------------------------------
// RepositoryStore
//
// The store acts as the database boundary. It resolves omitted fields using
// defaults and validates the resulting row before persistence.
//
// Explicit NULL is rejected for non-nullable columns. Description is nullable,
// so explicit NULL remains NULL instead of causing its default to be used.
// ---------------------------------------------------------------------------

class RepositoryStore {
public:
    RepositoryRecord insert(const RepositoryInsert& request) {
        if (request.name.empty()) {
            throw invalid_argument("repository name is required");
        }

        RepositoryRecord record{
            resolveId(request.id),
            request.name,
            resolveStatus(request.status),
            resolvePriority(request.priority),
            resolveEnabled(request.enabled),
            resolveDescription(request.description),
            utcTimestamp()
        };

        validate(record);

        records_.emplace(record.id, record);
        return record;
    }

    optional<RepositoryRecord> find(const string& id) const {
        auto iterator = records_.find(id);

        if (iterator == records_.end()) {
            return nullopt;
        }

        return iterator->second;
    }

    vector<RepositoryRecord> all() const {
        vector<RepositoryRecord> result;

        result.reserve(records_.size());

        for (const auto& [id, record] : records_) {
            result.push_back(record);
        }

        return result;
    }

    void updatePriority(const string& id, int priority) {
        if (priority < 0 || priority > 100) {
            throw invalid_argument("priority must be between 0 and 100");
        }

        auto iterator = records_.find(id);

        if (iterator == records_.end()) {
            throw out_of_range("repository does not exist");
        }

        // DEFAULT values are INSERT behavior. An UPDATE that omits priority
        // would leave the existing value unchanged. Here an explicit value
        // intentionally replaces it.
        iterator->second.priority = priority;
    }

    void archive(const string& id) {
        auto iterator = records_.find(id);

        if (iterator == records_.end()) {
            throw out_of_range("repository does not exist");
        }

        iterator->second.status = RepositoryStatus::Archived;
        iterator->second.enabled = false;
    }

private:
    static string resolveId(const OptionalValue<string>& value) {
        switch (value.state()) {
            case OptionalValue<string>::State::Omitted:
                return generateUuidLikeId();

            case OptionalValue<string>::State::Null:
                throw invalid_argument("id does not permit NULL");

            case OptionalValue<string>::State::Value:
                if (!value.value().has_value() ||
                    value.value()->empty()) {
                    throw invalid_argument("id cannot be empty");
                }

                return *value.value();
        }

        throw logic_error("Invalid id state");
    }

    static RepositoryStatus resolveStatus(
        const OptionalValue<RepositoryStatus>& value
    ) {
        switch (value.state()) {
            case OptionalValue<RepositoryStatus>::State::Omitted:
                return RepositoryStatus::Active;

            case OptionalValue<RepositoryStatus>::State::Null:
                throw invalid_argument("status does not permit NULL");

            case OptionalValue<RepositoryStatus>::State::Value:
                if (!value.value().has_value() ||
                    !validStatus(*value.value())) {
                    throw invalid_argument("invalid repository status");
                }

                return *value.value();
        }

        throw logic_error("Invalid status state");
    }

    static int resolvePriority(const OptionalValue<int>& value) {
        switch (value.state()) {
            case OptionalValue<int>::State::Omitted:
                return 5;

            case OptionalValue<int>::State::Null:
                throw invalid_argument("priority does not permit NULL");

            case OptionalValue<int>::State::Value:
                if (!value.value().has_value() ||
                    *value.value() < 0 ||
                    *value.value() > 100) {
                    throw invalid_argument(
                        "priority must be between 0 and 100"
                    );
                }

                return *value.value();
        }

        throw logic_error("Invalid priority state");
    }

    static bool resolveEnabled(const OptionalValue<bool>& value) {
        switch (value.state()) {
            case OptionalValue<bool>::State::Omitted:
                return true;

            case OptionalValue<bool>::State::Null:
                throw invalid_argument("enabled does not permit NULL");

            case OptionalValue<bool>::State::Value:
                if (!value.value().has_value()) {
                    throw invalid_argument("enabled value is missing");
                }

                return *value.value();
        }

        throw logic_error("Invalid enabled state");
    }

    static optional<string> resolveDescription(
        const OptionalValue<string>& value
    ) {
        switch (value.state()) {
            case OptionalValue<string>::State::Omitted:
                // No DEFAULT is defined here. The nullable column therefore
                // becomes NULL when omitted.
                return nullopt;

            case OptionalValue<string>::State::Null:
                return nullopt;

            case OptionalValue<string>::State::Value:
                return value.value();
        }

        throw logic_error("Invalid description state");
    }

    static void validate(const RepositoryRecord& record) {
        if (record.id.empty()) {
            throw invalid_argument("id cannot be empty");
        }

        if (record.name.empty()) {
            throw invalid_argument("name cannot be empty");
        }

        if (!validStatus(record.status)) {
            throw invalid_argument("status is invalid");
        }

        if (record.priority < 0 || record.priority > 100) {
            throw invalid_argument("priority is outside allowed range");
        }
    }

    unordered_map<string, RepositoryRecord> records_;
};


// ---------------------------------------------------------------------------
// Batch insert with rollback-like behavior
//
// A real database transaction provides atomicity. This self-contained model
// takes a snapshot before processing the batch and restores it when any
// record fails validation.
// ---------------------------------------------------------------------------

class TransactionalRepositoryStore {
public:
    vector<RepositoryRecord> insertBatch(
        const vector<RepositoryInsert>& requests
    ) {
        const auto backup = store_.all();

        vector<RepositoryRecord> inserted;

        try {
            for (const auto& request : requests) {
                inserted.push_back(store_.insert(request));
            }

            return inserted;
        } catch (...) {
            restore(backup);
            throw;
        }
    }

    RepositoryStore& store() {
        return store_;
    }

private:
    void restore(const vector<RepositoryRecord>& records) {
        /*
         * RepositoryStore intentionally does not expose arbitrary mutation.
         * Reconstructing the state here models the logical effect of a
         * rollback without pretending this is a database transaction.
         */
        store_ = RepositoryStore{};

        for (const auto& record : records) {
            RepositoryInsert request;

            request.name = record.name;
            request.id = OptionalValue<string>::value(record.id);
            request.status =
                OptionalValue<RepositoryStatus>::value(record.status);
            request.priority =
                OptionalValue<int>::value(record.priority);
            request.enabled =
                OptionalValue<bool>::value(record.enabled);

            if (record.description.has_value()) {
                request.description =
                    OptionalValue<string>::value(*record.description);
            } else {
                request.description =
                    OptionalValue<string>::nullValue();
            }

            store_.insert(request);
        }
    }

    RepositoryStore store_;
};


// ---------------------------------------------------------------------------
// Default migration
//
// A changed DEFAULT is a future-insert policy. Existing rows are not silently
// rewritten. A separate data migration is needed when historical values must
// change.
// ---------------------------------------------------------------------------

class WorkflowTable {
public:
    explicit WorkflowTable(string defaultState)
        : defaultState_(std::move(defaultState)) {}

    struct Row {
        string id;
        string name;
        string state;
    };

    Row insert(
        string name,
        OptionalValue<string> state =
            OptionalValue<string>::omitted()
    ) {
        string resolvedState;

        switch (state.state()) {
            case OptionalValue<string>::State::Omitted:
                resolvedState = defaultState_;
                break;

            case OptionalValue<string>::State::Null:
                throw invalid_argument("workflow state cannot be NULL");

            case OptionalValue<string>::State::Value:
                if (!state.value().has_value()) {
                    throw invalid_argument("missing workflow state");
                }

                resolvedState = *state.value();
                break;
        }

        Row row{
            generateUuidLikeId(),
            std::move(name),
            resolvedState
        };

        rows_.push_back(row);
        return row;
    }

    void changeDefault(string newDefault) {
        if (newDefault.empty()) {
            throw invalid_argument("new default cannot be empty");
        }

        defaultState_ = std::move(newDefault);
    }

    void migratePendingToQueued() {
        for (auto& row : rows_) {
            if (row.state == "pending") {
                row.state = "queued";
            }
        }
    }

    const vector<Row>& rows() const {
        return rows_;
    }

private:
    string defaultState_;
    vector<Row> rows_;
};


// ---------------------------------------------------------------------------
// Demonstration
// ---------------------------------------------------------------------------

int main() {
    try {
        heading("DEFAULT Constraint Case Study");

        subsection("Default policy");

        for (const auto& policy : repositoryDefaultPolicies()) {
            cout
                << policy.column
                << " | owner=" << policy.owner
                << " | expression=" << policy.expression
                << " | " << policy.purpose
                << '\n';
        }


        subsection("Basic INSERT with defaults");

        RepositoryStore store;

        RepositoryInsert firstRepository;
        firstRepository.name = "market-risk-engine";

        RepositoryRecord first = store.insert(firstRepository);

        cout << "id: " << first.id << '\n'
             << "name: " << first.name << '\n'
             << "status: " << toString(first.status) << '\n'
             << "priority: " << first.priority << '\n'
             << "enabled: " << boolalpha << first.enabled << '\n'
             << "created_at: " << first.createdAt << '\n';


        subsection("Explicit overrides");

        RepositoryInsert secondRepository;
        secondRepository.name = "audit-service";

        secondRepository.status =
            OptionalValue<RepositoryStatus>::value(
                RepositoryStatus::Maintenance
            );

        secondRepository.priority =
            OptionalValue<int>::value(20);

        secondRepository.enabled =
            OptionalValue<bool>::value(false);

        RepositoryRecord second = store.insert(secondRepository);

        cout << "name: " << second.name << '\n'
             << "status: " << toString(second.status) << '\n'
             << "priority: " << second.priority << '\n'
             << "enabled: " << second.enabled << '\n';


        subsection("Explicit NULL behavior");

        RepositoryInsert invalidRepository;
        invalidRepository.name = "null-status-test";

        invalidRepository.status =
            OptionalValue<RepositoryStatus>::nullValue();

        try {
            store.insert(invalidRepository);
        } catch (const exception& error) {
            cout << "Rejected explicit NULL: "
                 << error.what()
                 << '\n';
        }


        subsection("Nullable column");

        RepositoryInsert nullableDescription;
        nullableDescription.name = "documentation-service";

        // description has no value and is nullable, so omission results in
        // NULL rather than an invented textual default.
        RepositoryRecord nullableRecord =
            store.insert(nullableDescription);

        cout << "Description present: "
             << boolalpha
             << nullableRecord.description.has_value()
             << '\n';


        subsection("Generated identifier");

        RepositoryInsert generatedIdentifier;
        generatedIdentifier.name = "uuid-service";

        RepositoryRecord generated =
            store.insert(generatedIdentifier);

        cout << "Generated id: " << generated.id << '\n';


        subsection("Explicit identifier");

        RepositoryInsert explicitIdentifier;
        explicitIdentifier.name = "imported-repository";

        explicitIdentifier.id =
            OptionalValue<string>::value(
                "11111111-1111-4111-8111-111111111111"
            );

        RepositoryRecord imported =
            store.insert(explicitIdentifier);

        cout << "Imported id: " << imported.id << '\n';


        subsection("UPDATE does not reapply INSERT defaults");

        cout << "Before update priority: "
             << first.priority
             << '\n';

        store.updatePriority(first.id, 30);

        const auto updated = store.find(first.id);

        if (!updated.has_value()) {
            throw runtime_error("repository disappeared");
        }

        cout << "After update priority: "
             << updated->priority
             << '\n';


        subsection("Archive operation");

        store.archive(second.id);

        const auto archived = store.find(second.id);

        if (!archived.has_value()) {
            throw runtime_error("archived repository disappeared");
        }

        cout << "Archived status: "
             << toString(archived->status)
             << '\n'
             << "Enabled: "
             << archived->enabled
             << '\n';


        subsection("Batch insertion and failure");

        TransactionalRepositoryStore transactionalStore;

        vector<RepositoryInsert> batch;

        RepositoryInsert batchA;
        batchA.name = "batch-alpha";

        RepositoryInsert batchB;
        batchB.name = "batch-beta";

        RepositoryInsert invalidBatch;
        invalidBatch.name = "";

        batch.push_back(batchA);
        batch.push_back(batchB);
        batch.push_back(invalidBatch);

        try {
            transactionalStore.insertBatch(batch);
        } catch (const exception& error) {
            cout << "Batch rolled back: "
                 << error.what()
                 << '\n';
        }

        cout << "Rows after failed batch: "
             << transactionalStore.store().all().size()
             << '\n';


        subsection("Successful batch");

        vector<RepositoryInsert> successfulBatch;

        RepositoryInsert successfulA;
        successfulA.name = "batch-gamma";

        RepositoryInsert successfulB;
        successfulB.name = "batch-delta";
        successfulB.priority =
            OptionalValue<int>::value(15);

        successfulBatch.push_back(successfulA);
        successfulBatch.push_back(successfulB);

        const auto inserted =
            transactionalStore.insertBatch(successfulBatch);

        cout << "Inserted records: "
             << inserted.size()
             << '\n';


        subsection("Default change and historical data");

        WorkflowTable workflow("pending");

        auto oldRow = workflow.insert("legacy-task");

        workflow.changeDefault("queued");

        auto newRow = workflow.insert("new-task");

        cout << "Existing row state: "
             << oldRow.state
             << '\n';

        cout << "Future row state: "
             << newRow.state
             << '\n';

        workflow.migratePendingToQueued();

        cout << "After explicit data migration:\n";

        for (const auto& row : workflow.rows()) {
            cout << "  "
                 << row.name
                 << " -> "
                 << row.state
                 << '\n';
        }


        subsection("Validation failure");

        RepositoryInsert invalidPriority;
        invalidPriority.name = "invalid-priority";

        invalidPriority.priority =
            OptionalValue<int>::value(500);

        try {
            store.insert(invalidPriority);
        } catch (const exception& error) {
            cout << "Rejected invalid default override: "
                 << error.what()
                 << '\n';
        }


        subsection("Production design observations");

        cout
            << "Static defaults are suitable for stable initial values.\n"
            << "Generated defaults should be evaluated separately for each row.\n"
            << "Timestamp defaults should use a consistent time policy.\n"
            << "UUID ownership should be explicit: application or database.\n"
            << "Explicit NULL and omitted columns have different semantics.\n"
            << "Changing a DEFAULT affects future inserts; historical data "
               "needs an explicit migration when business rules require it.\n"
            << "Defaults establish initial values; validation and authorization "
               "must enforce independent business and security rules.\n";


        heading("Case Study Completed");

        return 0;
    }
    catch (const exception& error) {
        cerr << "Fatal error: "
             << error.what()
             << '\n';

        return 1;
    }
}
