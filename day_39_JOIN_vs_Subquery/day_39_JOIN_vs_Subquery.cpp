#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

/*
 * JOIN vs Subquery
 *
 * Case study:
 * A repository analytics platform needs to generate reports from a relational
 * employee/project dataset. The C++ program models the relational operations
 * directly so that JOIN-oriented and subquery-oriented query designs can be
 * compared without requiring an external database library.
 *
 * The program intentionally models three different relational intentions:
 *   - combining attributes from related rows
 *   - testing whether a related row exists
 *   - comparing an outer row with an aggregate derived from related rows
 *
 * This is a case study of query semantics and query planning, not a generic
 * C++ syntax demonstration.
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
    int monthlyHours;
};

struct EmployeeDepartment {
    const Employee& employee;
    const Department& department;
};

struct ProjectAssignment {
    const Employee& employee;
    const Project& project;
    int monthlyHours;
};

class GovernanceData {
public:
    std::vector<Department> departments{
        {1, "Engineering"},
        {2, "Finance"},
        {3, "Operations"},
        {4, "Research"}
    };

    std::vector<Employee> employees{
        {1, "Asha", 1, 125000},
        {2, "Ravi", 1, 98000},
        {3, "Meera", 1, 112000},
        {4, "Kabir", 2, 87000},
        {5, "Neha", 2, 92000},
        {6, "Arjun", 3, 76000},
        {7, "Isha", 3, 81000},
        {8, "Sara", 4, 130000},
        {9, "Dev", 4, 105000}
    };

    std::vector<Project> projects{
        {101, "Cloud Migration", 1, 500000},
        {102, "Fraud Analytics", 2, 350000},
        {103, "Warehouse Automation", 3, 275000},
        {104, "Quantum Research", 4, 600000}
    };

    std::vector<Assignment> assignments{
        {1, 101, 80},
        {2, 101, 120},
        {3, 101, 90},
        {3, 104, 40},
        {4, 102, 70},
        {5, 102, 110},
        {6, 103, 100},
        {7, 103, 120},
        {8, 104, 130},
        {9, 104, 100}
    };

    const Department& departmentById(int id) const {
        for (const auto& department : departments) {
            if (department.id == id) {
                return department;
            }
        }
        throw std::out_of_range("Department does not exist");
    }

    const Project& projectById(int id) const {
        for (const auto& project : projects) {
            if (project.id == id) {
                return project;
            }
        }
        throw std::out_of_range("Project does not exist");
    }
};

class QueryEngine {
public:
    explicit QueryEngine(const GovernanceData& data) : data_(data) {}

    /*
     * JOIN semantics:
     * every employee is matched to its department. The result contains
     * attributes from both relations because combining those attributes is
     * the purpose of the operation.
     */
    std::vector<EmployeeDepartment> employeeDepartmentJoin() const {
        std::vector<EmployeeDepartment> result;

        for (const auto& employee : data_.employees) {
            const auto& department =
                data_.departmentById(employee.departmentId);

            result.push_back({employee, department});
        }

        return result;
    }

    /*
     * A nested lookup models a scalar/subquery-style operation:
     * for each employee, retrieve the department name required to evaluate
     * the current outer row. Unlike the JOIN result above, the algorithm
     * exposes the lookup as a dependent inner operation.
     */
    std::vector<std::pair<std::string, std::string>>
    employeeDepartmentLookup() const {
        std::vector<std::pair<std::string, std::string>> result;

        for (const auto& employee : data_.employees) {
            const auto& department =
                data_.departmentById(employee.departmentId);

            result.emplace_back(employee.name, department.name);
        }

        return result;
    }

    /*
     * EXISTS semantics:
     * the employee is emitted once when at least one qualifying project is
     * found. Once the condition is true, the inner search can stop.
     *
     * This models why EXISTS is conceptually different from a JOIN that
     * returns project columns: the desired result is existence, not row
     * expansion.
     */
    std::vector<const Employee*> employeesWithLargeProject(
        double minimumBudget
    ) const {
        std::vector<const Employee*> result;

        for (const auto& employee : data_.employees) {
            bool exists = false;

            for (const auto& assignment : data_.assignments) {
                if (assignment.employeeId != employee.id) {
                    continue;
                }

                const auto& project =
                    data_.projectById(assignment.projectId);

                if (project.budget >= minimumBudget) {
                    exists = true;
                    break;
                }
            }

            if (exists) {
                result.push_back(&employee);
            }
        }

        return result;
    }

    /*
     * JOIN-style project report:
     * one output row is created for each employee-project assignment.
     * This is intentionally different from the EXISTS operation above.
     */
    std::vector<ProjectAssignment> employeeProjectJoin(
        double minimumBudget
    ) const {
        std::vector<ProjectAssignment> result;

        for (const auto& assignment : data_.assignments) {
            const auto& project =
                data_.projectById(assignment.projectId);

            if (project.budget < minimumBudget) {
                continue;
            }

            auto employeeIt = std::find_if(
                data_.employees.begin(),
                data_.employees.end(),
                [&](const Employee& employee) {
                    return employee.id == assignment.employeeId;
                }
            );

            if (employeeIt == data_.employees.end()) {
                throw std::logic_error(
                    "Assignment references an unknown employee"
                );
            }

            result.push_back({
                *employeeIt,
                project,
                assignment.monthlyHours
            });
        }

        return result;
    }

    /*
     * Correlated-subquery-style comparison:
     * for each employee, calculate the average salary of that employee's
     * department and then compare the current employee against it.
     *
     * A straightforward implementation is O(E * E) because the inner scan
     * can inspect all employees for each outer employee.
     */
    std::vector<const Employee*> aboveDepartmentAverageCorrelated() const {
        std::vector<const Employee*> result;

        for (const auto& employee : data_.employees) {
            double total = 0.0;
            int count = 0;

            for (const auto& candidate : data_.employees) {
                if (candidate.departmentId == employee.departmentId) {
                    total += candidate.salary;
                    ++count;
                }
            }

            if (count == 0) {
                throw std::logic_error(
                    "An employee cannot belong to an empty department"
                );
            }

            const double average = total / count;

            if (employee.salary > average) {
                result.push_back(&employee);
            }
        }

        return result;
    }

    /*
     * A pre-aggregation strategy computes one average per department first.
     * This is analogous to a derived table or CTE followed by a JOIN.
     *
     * It reduces the repeated aggregate work and makes the dependency
     * explicit as a reusable relation.
     */
    std::vector<const Employee*> aboveDepartmentAveragePrecomputed() const {
        std::unordered_map<int, std::pair<double, int>> aggregates;

        for (const auto& employee : data_.employees) {
            auto& aggregate = aggregates[employee.departmentId];
            aggregate.first += employee.salary;
            ++aggregate.second;
        }

        std::unordered_map<int, double> averages;

        for (const auto& [departmentId, aggregate] : aggregates) {
            if (aggregate.second == 0) {
                throw std::logic_error("Invalid empty department aggregate");
            }

            averages[departmentId] =
                aggregate.first / aggregate.second;
        }

        std::vector<const Employee*> result;

        for (const auto& employee : data_.employees) {
            const auto averageIt = averages.find(employee.departmentId);

            if (averageIt == averages.end()) {
                throw std::logic_error(
                    "Missing aggregate for employee department"
                );
            }

            if (employee.salary > averageIt->second) {
                result.push_back(&employee);
            }
        }

        return result;
    }

private:
    const GovernanceData& data_;
};

void printDepartmentJoin(
    const std::vector<EmployeeDepartment>& rows
) {
    std::cout << "\n=== Employee / Department JOIN ===\n";

    for (const auto& row : rows) {
        std::cout
            << std::left << std::setw(10)
            << row.employee.name
            << " | "
            << row.department.name
            << " | salary="
            << std::fixed << std::setprecision(2)
            << row.employee.salary
            << '\n';
    }
}

void printLookup(
    const std::vector<std::pair<std::string, std::string>>& rows
) {
    std::cout << "\n=== Department lookup / subquery-style operation ===\n";

    for (const auto& [employee, department] : rows) {
        std::cout << employee << " | " << department << '\n';
    }
}

void printEmployees(
    const std::string& title,
    const std::vector<const Employee*>& employees
) {
    std::cout << "\n=== " << title << " ===\n";

    for (const auto* employee : employees) {
        std::cout
            << employee->name
            << " | department_id="
            << employee->departmentId
            << " | salary="
            << employee->salary
            << '\n';
    }
}

void printProjectAssignments(
    const std::vector<ProjectAssignment>& assignments
) {
    std::cout << "\n=== JOIN with project relationships ===\n";

    for (const auto& assignment : assignments) {
        std::cout
            << assignment.employee.name
            << " | "
            << assignment.project.name
            << " | budget="
            << assignment.project.budget
            << " | hours="
            << assignment.monthlyHours
            << '\n';
    }
}

void demonstrateComplexity(
    const GovernanceData& data
) {
    const std::size_t employees = data.employees.size();

    /*
     * The correlated approach can perform an inner scan for every outer row,
     * giving a simple upper-bound model of O(E²).
     *
     * Pre-aggregation builds department aggregates in O(E), then performs
     * another O(E) lookup phase. Hash-map operations are expected O(1), so
     * the practical model is approximately O(E).
     *
     * A real SQL optimizer may choose indexes, hash joins, merge joins,
     * materialization, or other strategies, so these are algorithmic models
     * rather than claims about a specific database execution plan.
     */
    std::cout << "\n=== Algorithmic perspective ===\n";
    std::cout
        << "Employees: "
        << employees
        << '\n';

    std::cout
        << "Correlated aggregate model: O(E^2) without pre-aggregation\n";

    std::cout
        << "Pre-aggregated relation model: expected O(E) with hash lookup\n";

    std::cout
        << "Database performance must still be verified with EXPLAIN/ANALYZE "
        << "because SQL optimizers can transform equivalent query forms.\n";
}

void validateResults(
    const std::vector<const Employee*>& correlated,
    const std::vector<const Employee*>& precomputed
) {
    std::set<int> correlatedIds;
    std::set<int> precomputedIds;

    for (const auto* employee : correlated) {
        correlatedIds.insert(employee->id);
    }

    for (const auto* employee : precomputed) {
        precomputedIds.insert(employee->id);
    }

    if (correlatedIds != precomputedIds) {
        throw std::logic_error(
            "Equivalent query designs produced different logical results"
        );
    }

    std::cout
        << "\nValidation: correlated and pre-aggregated designs "
        << "produce the same employee set.\n";
}

int main() {
    try {
        GovernanceData data;
        QueryEngine engine(data);

        const auto joinRows = engine.employeeDepartmentJoin();
        printDepartmentJoin(joinRows);

        const auto lookupRows = engine.employeeDepartmentLookup();
        printLookup(lookupRows);

        const double largeProjectBudget = 500000;

        const auto projectRows =
            engine.employeeProjectJoin(largeProjectBudget);

        printProjectAssignments(projectRows);

        const auto employeesWithLargeProject =
            engine.employeesWithLargeProject(largeProjectBudget);

        printEmployees(
            "EXISTS-style result: employees with at least one large project",
            employeesWithLargeProject
        );

        const auto correlated =
            engine.aboveDepartmentAverageCorrelated();

        printEmployees(
            "Correlated aggregate: above department average",
            correlated
        );

        const auto precomputed =
            engine.aboveDepartmentAveragePrecomputed();

        printEmployees(
            "Pre-aggregated relation: above department average",
            precomputed
        );

        validateResults(correlated, precomputed);
        demonstrateComplexity(data);

        std::cout
            << "\nCase-study decision: a JOIN is appropriate when related "
            << "attributes or relationship rows are part of the result. "
            << "EXISTS is appropriate when only relationship existence "
            << "matters. A correlated subquery can express a per-row "
            << "dependent calculation clearly, while pre-aggregation "
            << "resembles a derived table or CTE that can avoid repeated "
            << "work.\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Fatal error: "
            << error.what()
            << '\n';

        return 1;
    }
}
