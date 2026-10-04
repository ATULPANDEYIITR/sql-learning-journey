#include <algorithm>
#include <iomanip>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

struct Employee {
    int employeeId;
    std::string name;
    std::optional<int> departmentId;
};

struct Department {
    int departmentId;
    std::string name;
    std::optional<int> managerId;
};

struct MergeDecision {
    std::optional<int> employeeId;
    std::optional<std::string> employeeName;
    std::optional<int> employeeDepartmentId;
    std::optional<int> departmentId;
    std::optional<std::string> departmentName;
    std::optional<int> managerId;
    std::string relationship;
};

void printOptional(const std::optional<int>& value) {
    if (value.has_value()) {
        std::cout << *value;
    } else {
        std::cout << "NULL";
    }
}

void printOptional(const std::optional<std::string>& value) {
    if (value.has_value()) {
        std::cout << *value;
    } else {
        std::cout << "NULL";
    }
}

void printDecisions(
    const std::string& title,
    const std::vector<MergeDecision>& rows
) {
    std::cout << "\n=== " << title << " ===\n";

    for (const auto& row : rows) {
        printOptional(row.employeeId);
        std::cout << " | ";
        printOptional(row.employeeName);
        std::cout << " | ";
        printOptional(row.employeeDepartmentId);
        std::cout << " | ";
        printOptional(row.departmentId);
        std::cout << " | ";
        printOptional(row.departmentName);
        std::cout << " | ";
        printOptional(row.managerId);
        std::cout << " | " << row.relationship << '\n';
    }
}

std::vector<MergeDecision> rightJoin(
    const std::vector<Employee>& employees,
    const std::vector<Department>& departments
) {
    /*
     * The unordered_multimap-style index is represented as a map from a
     * department ID to all employees belonging to that department.
     * Multiple employees can legitimately share one department.
     */
    std::unordered_map<int, std::vector<std::size_t>> employeeIndex;

    for (std::size_t i = 0; i < employees.size(); ++i) {
        if (employees[i].departmentId.has_value()) {
            employeeIndex[*employees[i].departmentId].push_back(i);
        }
    }

    std::vector<MergeDecision> result;

    for (const auto& department : departments) {
        auto iterator = employeeIndex.find(department.departmentId);

        if (iterator == employeeIndex.end()) {
            /*
             * RIGHT JOIN preservation rule: the department exists on the
             * right side, so it must appear even without an employee.
             */
            result.push_back({
                std::nullopt,
                std::nullopt,
                std::nullopt,
                department.departmentId,
                department.name,
                department.managerId,
                "DEPARTMENT_WITHOUT_EMPLOYEE"
            });
            continue;
        }

        for (std::size_t employeeIndexPosition : iterator->second) {
            const Employee& employee = employees[employeeIndexPosition];

            result.push_back({
                employee.employeeId,
                employee.name,
                employee.departmentId,
                department.departmentId,
                department.name,
                department.managerId,
                "MATCHED"
            });
        }
    }

    return result;
}

std::vector<MergeDecision> fullOuterJoin(
    const std::vector<Employee>& employees,
    const std::vector<Department>& departments
) {
    /*
     * The right-side index makes equality matching efficient. A separate set
     * records which department rows actually participated in a match so that
     * unmatched right rows can be emitted after processing the left relation.
     */
    std::unordered_map<int, std::vector<std::size_t>> departmentIndex;

    for (std::size_t i = 0; i < departments.size(); ++i) {
        departmentIndex[departments[i].departmentId].push_back(i);
    }

    std::unordered_set<std::size_t> matchedDepartments;
    std::vector<MergeDecision> result;

    for (const auto& employee : employees) {
        if (!employee.departmentId.has_value()) {
            /*
             * SQL NULL does not satisfy an equality join predicate. The
             * employee therefore remains unmatched in a FULL OUTER JOIN.
             */
            result.push_back({
                employee.employeeId,
                employee.name,
                employee.departmentId,
                std::nullopt,
                std::nullopt,
                std::nullopt,
                "EMPLOYEE_WITHOUT_DEPARTMENT"
            });
            continue;
        }

        auto iterator = departmentIndex.find(*employee.departmentId);

        if (iterator == departmentIndex.end()) {
            result.push_back({
                employee.employeeId,
                employee.name,
                employee.departmentId,
                std::nullopt,
                std::nullopt,
                std::nullopt,
                "EMPLOYEE_WITHOUT_DEPARTMENT"
            });
            continue;
        }

        for (std::size_t departmentIndexPosition : iterator->second) {
            const Department& department =
                departments[departmentIndexPosition];

            matchedDepartments.insert(departmentIndexPosition);

            result.push_back({
                employee.employeeId,
                employee.name,
                employee.departmentId,
                department.departmentId,
                department.name,
                department.managerId,
                "MATCHED"
            });
        }
    }

    for (std::size_t i = 0; i < departments.size(); ++i) {
        if (matchedDepartments.find(i) == matchedDepartments.end()) {
            const Department& department = departments[i];

            result.push_back({
                std::nullopt,
                std::nullopt,
                std::nullopt,
                department.departmentId,
                department.name,
                department.managerId,
                "DEPARTMENT_WITHOUT_EMPLOYEE"
            });
        }
    }

    return result;
}

std::vector<MergeDecision> findDepartmentsWithoutEmployees(
    const std::vector<Department>& departments,
    const std::vector<Employee>& employees
) {
    std::unordered_set<int> employeeDepartmentIds;

    for (const auto& employee : employees) {
        if (employee.departmentId.has_value()) {
            employeeDepartmentIds.insert(*employee.departmentId);
        }
    }

    std::vector<MergeDecision> result;

    for (const auto& department : departments) {
        if (employeeDepartmentIds.find(department.departmentId) ==
            employeeDepartmentIds.end()) {
            result.push_back({
                std::nullopt,
                std::nullopt,
                std::nullopt,
                department.departmentId,
                department.name,
                department.managerId,
                "DEPARTMENT_WITHOUT_EMPLOYEE"
            });
        }
    }

    return result;
}

void validateData(
    const std::vector<Employee>& employees,
    const std::vector<Department>& departments
) {
    std::unordered_set<int> departmentIds;

    for (const auto& department : departments) {
        if (!departmentIds.insert(department.departmentId).second) {
            throw std::runtime_error(
                "Department IDs must be unique for this master-data model."
            );
        }
    }

    for (const auto& employee : employees) {
        if (employee.employeeId <= 0) {
            throw std::runtime_error("Employee IDs must be positive.");
        }

        if (employee.departmentId.has_value() &&
            *employee.departmentId <= 0) {
            throw std::runtime_error(
                "Employee department IDs must be positive when present."
            );
        }
    }
}

int main() {
    try {
        const std::vector<Employee> employees = {
            {101, "Aarav", 10},
            {102, "Meera", 20},
            {103, "Kabir", 20},
            {104, "Isha", 40},
            {105, "Rohan", std::nullopt}
        };

        const std::vector<Department> departments = {
            {10, "Engineering", 9001},
            {20, "Finance", 9002},
            {30, "Research", 9003},
            {40, "Operations", std::nullopt},
            {50, "Legal", 9005}
        };

        validateData(employees, departments);

        std::cout
            << "EMPLOYEE / DEPARTMENT GOVERNANCE CASE STUDY\n"
            << "employeeId | employeeName | employeeDept | deptId | "
            << "departmentName | managerId | relationship\n";

        const auto rightJoinResult = rightJoin(employees, departments);

        printDecisions(
            "RIGHT JOIN: department-centric reporting",
            rightJoinResult
        );

        /*
         * The RIGHT JOIN is appropriate when department master data is the
         * required complete population. Research and Legal remain visible
         * even though their employee populations are empty.
         */
        const auto fullJoinResult =
            fullOuterJoin(employees, departments);

        printDecisions(
            "FULL OUTER JOIN: bidirectional reconciliation",
            fullJoinResult
        );

        const auto orphanDepartments =
            findDepartmentsWithoutEmployees(departments, employees);

        printDecisions(
            "Departments without employees",
            orphanDepartments
        );

        /*
         * A FULL OUTER JOIN is a reconciliation mechanism rather than merely
         * a wider INNER JOIN. It identifies missing relationships on either
         * side, which is valuable when validating independently maintained
         * datasets.
         */
        std::size_t matched = 0;
        std::size_t employeeOrphans = 0;
        std::size_t departmentOrphans = 0;

        for (const auto& row : fullJoinResult) {
            if (row.relationship == "MATCHED") {
                ++matched;
            } else if (
                row.relationship == "EMPLOYEE_WITHOUT_DEPARTMENT"
            ) {
                ++employeeOrphans;
            } else {
                ++departmentOrphans;
            }
        }

        std::cout << "\nReconciliation metrics\n";
        std::cout << "Matched rows: " << matched << '\n';
        std::cout << "Employee-side orphans: " << employeeOrphans << '\n';
        std::cout << "Department-side orphans: " << departmentOrphans << '\n';

        /*
         * Duplicate keys are not an implementation error. They represent
         * one-to-many relationships and can increase output cardinality.
         */
        const std::vector<Employee> financeEmployees = {
            {201, "Nisha", 20},
            {202, "Dev", 20}
        };

        const std::vector<Department> financeDepartments = {
            {20, "Finance", 9002}
        };

        const auto oneToManyResult =
            fullOuterJoin(financeEmployees, financeDepartments);

        printDecisions(
            "One department matched by multiple employees",
            oneToManyResult
        );

        /*
         * Expected complexity for the hash-index implementation is O(E + D)
         * to build and probe the indexes, excluding the potentially larger
         * output itself. A database optimizer may select a hash join, merge
         * join, or nested-loop join based on statistics and available indexes.
         */
        std::cout << "\nComplexity and design notes\n";
        std::cout
            << "Hash-index construction and probing: expected O(E + D).\n";
        std::cout
            << "Output cost depends on the number of matching pairs.\n";
        std::cout
            << "std::optional models SQL NULL-like absence explicitly.\n";
        std::cout
            << "FULL OUTER JOIN requires preserving unmatched rows from both sides.\n";

        std::cout << "\nCase study completed successfully.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Execution failed: " << error.what() << '\n';
        return 1;
    }
}
