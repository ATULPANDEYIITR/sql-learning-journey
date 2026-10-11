#include <algorithm>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

/*
 * Subqueries Fundamentals: C++ technical case study
 *
 * Scenario:
 * A financial services analytics engine must identify employees and
 * departments using query conditions that would normally be expressed with
 * SQL subqueries.
 *
 * The program models:
 *   - scalar subqueries
 *   - single-row subqueries
 *   - multi-row subqueries
 *   - correlated subqueries
 *   - EXISTS and NOT EXISTS
 *   - derived/table subqueries
 *   - nested subqueries
 *   - validation of scalar cardinality
 *
 * C++17 is sufficient. No external library is required.
 */

struct Department {
    int id;
    std::string name;
};

struct Employee {
    int id;
    std::string name;
    int departmentId;
    double salary;
};

struct Project {
    int id;
    std::string name;
    int departmentId;
    double budget;
};

struct Assignment {
    int employeeId;
    int projectId;
    double hours;
};

struct DepartmentMetric {
    int departmentId;
    std::string departmentName;
    std::size_t employeeCount;
    double averageSalary;
};

class AnalyticsEngine {
private:
    std::vector<Department> departments_;
    std::vector<Employee> employees_;
    std::vector<Project> projects_;
    std::vector<Assignment> assignments_;

public:
    AnalyticsEngine()
        : departments_{
              {10, "Engineering"},
              {20, "Finance"},
              {30, "Operations"},
              {40, "Security"},
              {50, "Research"},
          },
          employees_{
              {101, "Aarav", 10, 92000},
              {102, "Diya", 10, 108000},
              {103, "Kabir", 10, 125000},
              {104, "Meera", 20, 85000},
              {105, "Rohan", 20, 97000},
              {106, "Ishita", 30, 76000},
              {107, "Vihaan", 30, 89000},
              {108, "Anaya", 40, 118000},
              {109, "Arjun", 40, 131000},
              {110, "Sara", 50, 112000},
          },
          projects_{
              {201, "Payment Platform", 10, 900000},
              {202, "Cloud Migration", 10, 650000},
              {203, "Risk Analytics", 20, 480000},
              {204, "Supply Optimization", 30, 550000},
              {205, "Threat Detection", 40, 800000},
              {206, "Quantum Research", 50, 1200000},
          },
          assignments_{
              {101, 201, 120},
              {101, 202, 80},
              {102, 201, 160},
              {103, 201, 180},
              {103, 202, 90},
              {104, 203, 150},
              {105, 203, 175},
              {106, 204, 120},
              {107, 204, 190},
              {108, 205, 170},
              {109, 205, 210},
              {110, 206, 200},
          } {}

    std::optional<int> singleRowDepartmentId(
        const std::string& departmentName) const {
        std::vector<int> matches;

        for (const auto& department : departments_) {
            if (department.name == departmentName) {
                matches.push_back(department.id);
            }
        }

        if (matches.size() > 1) {
            throw std::logic_error(
                "Single-row subquery returned more than one row.");
        }

        if (matches.empty()) {
            return std::nullopt;
        }

        return matches.front();
    }

    double scalarCompanyAverageSalary() const {
        if (employees_.empty()) {
            throw std::logic_error(
                "Scalar aggregate subquery cannot calculate an average "
                "without employee rows.");
        }

        const double total = std::accumulate(
            employees_.begin(),
            employees_.end(),
            0.0,
            [](double current, const Employee& employee) {
                return current + employee.salary;
            });

        return total / static_cast<double>(employees_.size());
    }

    std::vector<Employee> scalarSubqueryExample() const {
        const double companyAverage = scalarCompanyAverageSalary();

        std::vector<Employee> result;

        for (const auto& employee : employees_) {
            if (employee.salary > companyAverage) {
                result.push_back(employee);
            }
        }

        return result;
    }

    std::unordered_set<int> multiRowDepartmentSubquery(
        const std::set<std::string>& names) const {
        std::unordered_set<int> ids;

        for (const auto& department : departments_) {
            if (names.contains(department.name)) {
                ids.insert(department.id);
            }
        }

        return ids;
    }

    std::vector<Employee> multiRowSubqueryExample() const {
        const auto departmentIds = multiRowDepartmentSubquery(
            {"Engineering", "Security", "Research"});

        std::vector<Employee> result;

        for (const auto& employee : employees_) {
            if (departmentIds.contains(employee.departmentId)) {
                result.push_back(employee);
            }
        }

        return result;
    }

    bool existsHeavyAssignment(int employeeId) const {
        /*
         * This models EXISTS. The search stops as soon as one qualifying
         * assignment is discovered, rather than collecting every match.
         */
        return std::any_of(
            assignments_.begin(),
            assignments_.end(),
            [employeeId](const Assignment& assignment) {
                return assignment.employeeId == employeeId &&
                       assignment.hours >= 180.0;
            });
    }

    std::vector<Employee> existsSubqueryExample() const {
        std::vector<Employee> result;

        for (const auto& employee : employees_) {
            if (existsHeavyAssignment(employee.id)) {
                result.push_back(employee);
            }
        }

        return result;
    }

    bool departmentHasProject(int departmentId) const {
        return std::any_of(
            projects_.begin(),
            projects_.end(),
            [departmentId](const Project& project) {
                return project.departmentId == departmentId;
            });
    }

    std::vector<Department> notExistsExample() const {
        std::vector<Department> result;

        for (const auto& department : departments_) {
            if (!departmentHasProject(department.id)) {
                result.push_back(department);
            }
        }

        return result;
    }

    double departmentAverage(int departmentId) const {
        double total = 0.0;
        std::size_t count = 0;

        for (const auto& employee : employees_) {
            if (employee.departmentId == departmentId) {
                total += employee.salary;
                ++count;
            }
        }

        if (count == 0) {
            throw std::logic_error(
                "Correlated average cannot be calculated for an empty "
                "department.");
        }

        return total / static_cast<double>(count);
    }

    std::vector<Employee> correlatedSubqueryExample() const {
        std::vector<Employee> result;

        for (const auto& employee : employees_) {
            /*
             * The employee row supplies departmentId to the inner
             * calculation. That dependency is what makes the operation
             * analogous to a correlated subquery.
             */
            const double localAverage =
                departmentAverage(employee.departmentId);

            if (employee.salary > localAverage) {
                result.push_back(employee);
            }
        }

        return result;
    }

    std::vector<DepartmentMetric> tableSubqueryExample() const {
        /*
         * First construct the derived table. A second operation then filters
         * the derived rows. This mirrors:
         *
         * SELECT *
         * FROM (
         *     SELECT department_id, COUNT(*), AVG(salary)
         *     ...
         * ) AS metrics
         * WHERE employee_count >= 2;
         */
        std::vector<DepartmentMetric> derivedTable;

        for (const auto& department : departments_) {
            std::size_t count = 0;
            double total = 0.0;

            for (const auto& employee : employees_) {
                if (employee.departmentId == department.id) {
                    ++count;
                    total += employee.salary;
                }
            }

            if (count > 0) {
                derivedTable.push_back(
                    {department.id,
                     department.name,
                     count,
                     total / static_cast<double>(count)});
            }
        }

        std::vector<DepartmentMetric> filtered;

        std::copy_if(
            derivedTable.begin(),
            derivedTable.end(),
            std::back_inserter(filtered),
            [](const DepartmentMetric& metric) {
                return metric.employeeCount >= 2;
            });

        std::sort(
            filtered.begin(),
            filtered.end(),
            [](const DepartmentMetric& left,
               const DepartmentMetric& right) {
                return left.averageSalary > right.averageSalary;
            });

        return filtered;
    }

    std::vector<Employee> nestedSubqueryExample() const {
        const auto engineeringId = singleRowDepartmentId("Engineering");

        if (!engineeringId.has_value()) {
            throw std::logic_error("Engineering department does not exist.");
        }

        /*
         * The outer predicate depends on an aggregate whose own filter
         * depends on a single-row lookup.
         */
        const double engineeringAverage =
            departmentAverage(engineeringId.value());

        std::vector<Employee> result;

        for (const auto& employee : employees_) {
            if (employee.salary > engineeringAverage) {
                result.push_back(employee);
            }
        }

        return result;
    }

    std::vector<Employee> greaterThanEveryFinanceSalary() const {
        const auto financeId = singleRowDepartmentId("Finance");

        if (!financeId.has_value()) {
            throw std::logic_error("Finance department does not exist.");
        }

        std::vector<double> financeSalaries;

        for (const auto& employee : employees_) {
            if (employee.departmentId == financeId.value()) {
                financeSalaries.push_back(employee.salary);
            }
        }

        std::vector<Employee> result;

        for (const auto& employee : employees_) {
            const bool greaterThanEveryFinanceEmployee =
                std::all_of(
                    financeSalaries.begin(),
                    financeSalaries.end(),
                    [&employee](double financeSalary) {
                        return employee.salary > financeSalary;
                    });

            if (greaterThanEveryFinanceEmployee) {
                result.push_back(employee);
            }
        }

        return result;
    }

    std::vector<Employee> equalToAnyEngineeringSalary() const {
        const auto engineeringId = singleRowDepartmentId("Engineering");

        if (!engineeringId.has_value()) {
            throw std::logic_error("Engineering department does not exist.");
        }

        std::unordered_set<double> engineeringSalaries;

        for (const auto& employee : employees_) {
            if (employee.departmentId == engineeringId.value()) {
                engineeringSalaries.insert(employee.salary);
            }
        }

        std::vector<Employee> result;

        for (const auto& employee : employees_) {
            if (engineeringSalaries.contains(employee.salary)) {
                result.push_back(employee);
            }
        }

        return result;
    }
};

void printEmployees(
    const std::string& title,
    const std::vector<Employee>& employees) {
    std::cout << "\n--- " << title << " ---\n";

    if (employees.empty()) {
        std::cout << "(no rows)\n";
        return;
    }

    for (const auto& employee : employees) {
        std::cout << employee.name
                  << " | department=" << employee.departmentId
                  << " | salary=$"
                  << std::fixed << std::setprecision(2)
                  << employee.salary << '\n';
    }
}

void printDepartments(
    const std::string& title,
    const std::vector<Department>& departments) {
    std::cout << "\n--- " << title << " ---\n";

    if (departments.empty()) {
        std::cout << "(no rows)\n";
        return;
    }

    for (const auto& department : departments) {
        std::cout << department.id
                  << " | " << department.name << '\n';
    }
}

void printMetrics(
    const std::string& title,
    const std::vector<DepartmentMetric>& metrics) {
    std::cout << "\n--- " << title << " ---\n";

    for (const auto& metric : metrics) {
        std::cout << metric.departmentName
                  << " | employees=" << metric.employeeCount
                  << " | average salary=$"
                  << std::fixed << std::setprecision(2)
                  << metric.averageSalary << '\n';
    }
}

int main() {
    try {
        AnalyticsEngine engine;

        std::cout << "SUBQUERIES FUNDAMENTALS\n";
        std::cout
            << "C++ case study: relational analytics without external libraries\n";

        printEmployees(
            "Scalar subquery: employees above company average",
            engine.scalarSubqueryExample());

        printEmployees(
            "Multi-row subquery: selected departments",
            engine.multiRowSubqueryExample());

        printEmployees(
            "EXISTS: employees with a heavy project assignment",
            engine.existsSubqueryExample());

        printDepartments(
            "NOT EXISTS: departments without projects",
            engine.notExistsExample());

        printEmployees(
            "Correlated subquery: employees above department average",
            engine.correlatedSubqueryExample());

        printMetrics(
            "Table subquery: filtered derived department metrics",
            engine.tableSubqueryExample());

        printEmployees(
            "Nested subquery: employees above Engineering average",
            engine.nestedSubqueryExample());

        printEmployees(
            "ALL semantics: greater than every Finance salary",
            engine.greaterThanEveryFinanceSalary());

        printEmployees(
            "ANY semantics: salary matching any Engineering salary",
            engine.equalToAnyEngineeringSalary());

        const auto securityId =
            engine.singleRowDepartmentId("Security");

        std::cout << "\nSingle-row subquery validation:\n";
        if (securityId.has_value()) {
            std::cout << "Security department ID = "
                      << securityId.value() << '\n';
        } else {
            std::cout << "Security department was not found.\n";
        }

        /*
         * A production query engine must distinguish:
         *   - no row returned
         *   - exactly one row returned
         *   - multiple rows returned when one value was expected
         *
         * std::optional models the first distinction explicitly.
         */
        const auto missingDepartment =
            engine.singleRowDepartmentId("Legal");

        std::cout << "Missing department lookup = "
                  << (missingDepartment.has_value()
                          ? "unexpected row"
                          : "no row returned")
                  << '\n';

    } catch (const std::exception& error) {
        std::cerr << "\nQuery evaluation failed: "
                  << error.what() << '\n';
        return 1;
    }

    return 0;
}
