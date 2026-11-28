#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

struct Employee {
    int id;
    string name;
    int departmentId;
    double salary;
    bool active;
};

struct Department {
    int id;
    string name;
    string location;
};

struct Query {
    double minimumSalary;
    string location;
    size_t limit = 0;
};

struct Result {
    int employeeId;
    string employeeName;
    double salary;
    string departmentName;
};

struct Metrics {
    size_t rowsScanned = 0;
    size_t predicatesEvaluated = 0;
    size_t joinOperations = 0;
    size_t rowsReturned = 0;
    double elapsedMs = 0.0;
};

enum class Strategy {
    NestedLoop,
    HashJoin,
    IndexedJoin
};

class QueryOptimizer {
private:
    vector<Employee> employees;
    vector<Department> departments;

    unordered_map<int, const Department*> departmentIndex;
    unordered_map<int, vector<const Employee*>> employeeIndex;
    unordered_map<string, vector<const Department*>> locationIndex;

    void validate(const Query& query) const {
        if (!isfinite(query.minimumSalary) || query.minimumSalary < 0) {
            throw invalid_argument("Invalid salary threshold");
        }

        if (query.location.empty()) {
            throw invalid_argument("Location cannot be empty");
        }
    }

    static bool resultOrder(const Result& a, const Result& b) {
        if (a.salary != b.salary) {
            return a.salary > b.salary;
        }
        return a.employeeId < b.employeeId;
    }

    vector<Result> finalize(vector<Result> result,
                            const Query& query) const {
        sort(result.begin(), result.end(), resultOrder);

        if (query.limit > 0 && result.size() > query.limit) {
            result.resize(query.limit);
        }

        return result;
    }

public:
    QueryOptimizer(vector<Employee> employeeData,
                   vector<Department> departmentData)
        : employees(move(employeeData)),
          departments(move(departmentData)) {

        for (const auto& department : departments) {
            if (department.id <= 0 || department.name.empty() ||
                department.location.empty()) {
                throw invalid_argument("Invalid department");
            }

            if (!departmentIndex.emplace(
                    department.id, &department).second) {
                throw invalid_argument("Duplicate department ID");
            }

            locationIndex[department.location].push_back(&department);
        }

        unordered_set<int> employeeIds;

        for (const auto& employee : employees) {
            if (employee.id <= 0 ||
                !isfinite(employee.salary) ||
                employee.salary < 0 ||
                employee.name.empty()) {
                throw invalid_argument("Invalid employee");
            }

            if (!employeeIds.insert(employee.id).second) {
                throw invalid_argument("Duplicate employee ID");
            }

            if (departmentIndex.find(employee.departmentId) ==
                departmentIndex.end()) {
                throw invalid_argument("Unknown employee department");
            }

            employeeIndex[employee.departmentId].push_back(&employee);
        }
    }

    vector<Result> execute(const Query& query,
                           Strategy strategy,
                           Metrics& metrics) const {
        validate(query);
        metrics = Metrics{};

        auto start = chrono::steady_clock::now();
        vector<Result> result;

        if (strategy == Strategy::NestedLoop) {
            result = nestedLoop(query, metrics);
        } else if (strategy == Strategy::HashJoin) {
            result = hashJoin(query, metrics);
        } else {
            result = indexedJoin(query, metrics);
        }

        result = finalize(move(result), query);
        metrics.rowsReturned = result.size();

        auto end = chrono::steady_clock::now();
        metrics.elapsedMs =
            chrono::duration<double, milli>(end - start).count();

        return result;
    }

private:
    vector<Result> nestedLoop(const Query& query,
                              Metrics& metrics) const {
        vector<Result> result;

        for (const auto& employee : employees) {
            for (const auto& department : departments) {
                metrics.joinOperations++;

                if (employee.departmentId != department.id) {
                    continue;
                }

                metrics.rowsScanned++;
                metrics.predicatesEvaluated++;

                if (employee.active &&
                    employee.salary >= query.minimumSalary &&
                    department.location == query.location) {
                    result.push_back({
                        employee.id,
                        employee.name,
                        employee.salary,
                        department.name
                    });
                }
            }
        }

        return result;
    }

    vector<Result> hashJoin(const Query& query,
                            Metrics& metrics) const {
        vector<Result> result;

        // Build a hash table containing only departments that satisfy
        // the location predicate.
        unordered_map<int, const Department*> filteredDepartments;

        for (const auto& department : departments) {
            if (department.location == query.location) {
                filteredDepartments.emplace(department.id, &department);
            }
        }

        // Apply employee predicates before joining.
        for (const auto& employee : employees) {
            metrics.rowsScanned++;
            metrics.predicatesEvaluated++;

            if (!employee.active ||
                employee.salary < query.minimumSalary) {
                continue;
            }

            metrics.joinOperations++;

            auto it = filteredDepartments.find(employee.departmentId);

            if (it == filteredDepartments.end()) {
                continue;
            }

            const Department& department = *it->second;

            result.push_back({
                employee.id,
                employee.name,
                employee.salary,
                department.name
            });
        }

        return result;
    }

    vector<Result> indexedJoin(const Query& query,
                               Metrics& metrics) const {
        vector<Result> result;

        auto locationIt = locationIndex.find(query.location);

        if (locationIt == locationIndex.end()) {
            return result;
        }

        // Start with matching departments, then retrieve only their
        // associated employees through the department index.
        for (const Department* department : locationIt->second) {
            auto employeeIt = employeeIndex.find(department->id);

            if (employeeIt == employeeIndex.end()) {
                continue;
            }

            for (const Employee* employee : employeeIt->second) {
                metrics.rowsScanned++;
                metrics.predicatesEvaluated++;

                if (!employee->active ||
                    employee->salary < query.minimumSalary) {
                    continue;
                }

                metrics.joinOperations++;

                result.push_back({
                    employee->id,
                    employee->name,
                    employee->salary,
                    department->name
                });
            }
        }

        return result;
    }
};

void printMetrics(const string& name,
                  const Metrics& metrics,
                  const vector<Result>& result) {
    cout << "\n" << name << "\n";
    cout << "Rows scanned: " << metrics.rowsScanned << "\n";
    cout << "Predicates evaluated: "
         << metrics.predicatesEvaluated << "\n";
    cout << "Join operations: " << metrics.joinOperations << "\n";
    cout << "Rows returned: " << metrics.rowsReturned << "\n";
    cout << fixed << setprecision(3)
         << "Execution time: " << metrics.elapsedMs << " ms\n";

    for (const auto& row : result) {
        cout << row.employeeId << " | "
             << row.employeeName << " | "
             << row.salary << " | "
             << row.departmentName << "\n";
    }
}

int main() {
    try {
        vector<Department> departments;
        vector<Employee> employees;

        vector<string> locations = {
            "Lucknow", "Delhi", "Mumbai", "Pune", "Bengaluru"
        };

        for (int i = 1; i <= 100; ++i) {
            departments.push_back({
                i,
                "Department-" + to_string(i),
                locations[(i - 1) % locations.size()]
            });
        }

        mt19937 generator(42);
        uniform_int_distribution<int> departmentDistribution(1, 100);
        uniform_int_distribution<int> salaryDistribution(20000, 150000);
        uniform_int_distribution<int> activityDistribution(0, 4);

        for (int i = 1; i <= 10000; ++i) {
            employees.push_back({
                i,
                "Employee-" + to_string(i),
                departmentDistribution(generator),
                static_cast<double>(salaryDistribution(generator)),
                activityDistribution(generator) != 0
            });
        }

        QueryOptimizer optimizer(
            move(employees),
            move(departments)
        );

        Query query{75000.0, "Lucknow", 100};

        Metrics nestedMetrics, hashMetrics, indexedMetrics;

        auto nested = optimizer.execute(
            query, Strategy::NestedLoop, nestedMetrics
        );

        auto hash = optimizer.execute(
            query, Strategy::HashJoin, hashMetrics
        );

        auto indexed = optimizer.execute(
            query, Strategy::IndexedJoin, indexedMetrics
        );

        printMetrics("Nested Loop Join", nestedMetrics, nested);
        printMetrics("Predicate Pushdown + Hash Join",
                     hashMetrics, hash);
        printMetrics("Indexed Join", indexedMetrics, indexed);

        // Identical results are required regardless of execution plan.
        if (nested.size() != hash.size() ||
            hash.size() != indexed.size()) {
            throw runtime_error("Query results are inconsistent");
        }

        for (size_t i = 0; i < nested.size(); ++i) {
            if (nested[i].employeeId != hash[i].employeeId ||
                hash[i].employeeId != indexed[i].employeeId) {
                throw runtime_error("Execution plan changed query results");
            }
        }

        cout << "\nAll execution plans returned equivalent results.\n";

        try {
            Metrics invalidMetrics;
            optimizer.execute(
                Query{-100.0, "Lucknow", 0},
                Strategy::HashJoin,
                invalidMetrics
            );
        } catch (const invalid_argument& error) {
            cout << "Expected validation error: "
                 << error.what() << "\n";
        }

    } catch (const exception& error) {
        cerr << "Execution failed: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
