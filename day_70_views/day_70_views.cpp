#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

/*
 * Database Views: CREATE VIEW, View Abstraction, and Reusable Queries.
 *
 * C++17 implementation of a repository-independent organizational
 * reporting engine.
 *
 * Models:
 * - Base relational tables.
 * - Logical views.
 * - Simple and aggregate views.
 * - Join-based views.
 * - View dependencies.
 * - Role-based view access.
 * - Materialized result caching.
 * - Cache invalidation.
 * - Query validation and failure handling.
 */

using namespace std;

class ViewException : public runtime_error {
public:
    explicit ViewException(const string& message)
        : runtime_error(message) {}
};

enum class UserRole {
    Reader,
    Analyst,
    Administrator
};

struct Department {
    int id;
    string name;
    string location;
};

struct Employee {
    int id;
    string name;
    int departmentId;
    double salary;
    bool active;
};

struct Project {
    int id;
    string name;
    double budget;
    int departmentId;
};

struct Assignment {
    int id;
    int employeeId;
    int projectId;
    double hours;
};

struct DepartmentView {
    int departmentId;
    string departmentName;
    size_t employeeCount;
    double averageSalary;
    double payroll;
};

struct ProjectView {
    int projectId;
    string projectName;
    string departmentName;
    size_t assignmentCount;
    double totalHours;
    double budget;
};

struct EmployeeView {
    int employeeId;
    string employeeName;
    int departmentId;
};

class Repository {
private:
    vector<Department> departments;
    vector<Employee> employees;
    vector<Project> projects;
    vector<Assignment> assignments;

    unsigned long long version = 0;

public:
    Repository() {
        departments = {
            {1, "Engineering", "Bangalore"},
            {2, "Finance", "Mumbai"},
            {3, "Research", "Hyderabad"},
            {4, "Operations", "Lucknow"}
        };

        employees = {
            {101, "Aarav", 1, 95000, true},
            {102, "Meera", 1, 110000, true},
            {103, "Kabir", 2, 85000, true},
            {104, "Ananya", 3, 120000, true},
            {105, "Rohan", 2, 75000, false},
            {106, "Ishita", 4, 80000, true}
        };

        projects = {
            {201, "Cloud Platform", 500000, 1},
            {202, "Financial Analytics", 250000, 2},
            {203, "Research Intelligence", 700000, 3},
            {204, "Process Automation", 180000, 4}
        };

        assignments = {
            {1, 101, 201, 120},
            {2, 102, 201, 160},
            {3, 103, 202, 90},
            {4, 104, 203, 180},
            {5, 106, 204, 110},
            {6, 101, 204, 40}
        };

        validate();
    }

    void validate() const {
        set<int> departmentIds;
        set<int> employeeIds;
        set<int> projectIds;
        set<int> assignmentIds;

        for (const auto& department : departments) {
            if (department.id <= 0 ||
                department.name.empty() ||
                !departmentIds.insert(department.id).second) {
                throw ViewException("Invalid department records.");
            }
        }

        for (const auto& employee : employees) {
            if (employee.id <= 0 ||
                employee.name.empty() ||
                employee.salary < 0 ||
                departmentIds.count(employee.departmentId) == 0 ||
                !employeeIds.insert(employee.id).second) {
                throw ViewException("Invalid employee records.");
            }
        }

        for (const auto& project : projects) {
            if (project.id <= 0 ||
                project.name.empty() ||
                project.budget < 0 ||
                departmentIds.count(project.departmentId) == 0 ||
                !projectIds.insert(project.id).second) {
                throw ViewException("Invalid project records.");
            }
        }

        set<pair<int, int>> uniqueAssignments;

        for (const auto& assignment : assignments) {
            if (assignment.id <= 0 ||
                assignment.hours < 0 ||
                employeeIds.count(assignment.employeeId) == 0 ||
                projectIds.count(assignment.projectId) == 0 ||
                !assignmentIds.insert(assignment.id).second ||
                !uniqueAssignments.insert({
                    assignment.employeeId,
                    assignment.projectId
                }).second) {
                throw ViewException("Invalid assignment records.");
            }
        }
    }

    const vector<Department>& getDepartments() const {
        return departments;
    }

    const vector<Employee>& getEmployees() const {
        return employees;
    }

    const vector<Project>& getProjects() const {
        return projects;
    }

    const vector<Assignment>& getAssignments() const {
        return assignments;
    }

    unsigned long long getVersion() const {
        return version;
    }

    void updateEmployeeName(int employeeId, const string& newName) {
        if (newName.empty()) {
            throw ViewException("Employee name cannot be empty.");
        }

        auto iterator = find_if(
            employees.begin(),
            employees.end(),
            [&](const Employee& employee) {
                return employee.id == employeeId;
            }
        );

        if (iterator == employees.end()) {
            throw ViewException("Employee does not exist.");
        }

        iterator->name = newName;
        ++version;
    }
};


class ViewEngine {
private:
    const Repository& repository;

    struct CacheEntry {
        unsigned long long version;
        vector<DepartmentView> rows;
    };

    map<string, CacheEntry> departmentCache;

    void authorize(const string& viewName, UserRole role) const {
        if (viewName == "department_statistics" &&
            role == UserRole::Reader) {
            throw ViewException(
                "Reader role cannot access department statistics."
            );
        }
    }

public:
    explicit ViewEngine(const Repository& source)
        : repository(source) {}

    vector<EmployeeView> employeeDirectory() const {
        vector<EmployeeView> result;

        for (const auto& employee : repository.getEmployees()) {
            if (employee.active) {
                result.push_back({
                    employee.id,
                    employee.name,
                    employee.departmentId
                });
            }
        }

        return result;
    }

    vector<DepartmentView> departmentStatistics(
        UserRole role
    ) {
        authorize("department_statistics", role);

        vector<DepartmentView> result;

        for (const auto& department : repository.getDepartments()) {
            size_t count = 0;
            double payroll = 0;

            for (const auto& employee : repository.getEmployees()) {
                if (employee.departmentId == department.id &&
                    employee.active) {
                    ++count;
                    payroll += employee.salary;
                }
            }

            result.push_back({
                department.id,
                department.name,
                count,
                count ? payroll / count : 0,
                payroll
            });
        }

        return result;
    }

    vector<ProjectView> projectWorkload() const {
        vector<ProjectView> result;

        for (const auto& project : repository.getProjects()) {
            auto department = find_if(
                repository.getDepartments().begin(),
                repository.getDepartments().end(),
                [&](const Department& item) {
                    return item.id == project.departmentId;
                }
            );

            if (department == repository.getDepartments().end()) {
                throw ViewException("Project department not found.");
            }

            size_t assignmentCount = 0;
            double totalHours = 0;

            for (const auto& assignment :
                 repository.getAssignments()) {
                if (assignment.projectId == project.id) {
                    ++assignmentCount;
                    totalHours += assignment.hours;
                }
            }

            result.push_back({
                project.id,
                project.name,
                department->name,
                assignmentCount,
                totalHours,
                project.budget
            });
        }

        return result;
    }

    vector<ProjectView> highWorkloadProjects(
        double minimumHours
    ) const {
        if (minimumHours < 0) {
            throw ViewException("Minimum hours cannot be negative.");
        }

        auto rows = projectWorkload();

        rows.erase(
            remove_if(
                rows.begin(),
                rows.end(),
                [&](const ProjectView& project) {
                    return project.totalHours <= minimumHours;
                }
            ),
            rows.end()
        );

        return rows;
    }

    vector<DepartmentView> materializedDepartmentStatistics(
        UserRole role
    ) {
        authorize("department_statistics", role);

        const string cacheKey = "department_statistics";

        auto cached = departmentCache.find(cacheKey);

        if (cached != departmentCache.end() &&
            cached->second.version == repository.getVersion()) {
            return cached->second.rows;
        }

        auto result = departmentStatistics(role);

        departmentCache[cacheKey] = {
            repository.getVersion(),
            result
        };

        return result;
    }
};


void printEmployeeView(const vector<EmployeeView>& rows) {
    cout << left
         << setw(12) << "ID"
         << setw(22) << "Name"
         << "Department\n";

    for (const auto& row : rows) {
        cout << setw(12) << row.employeeId
             << setw(22) << row.employeeName
             << row.departmentId << '\n';
    }
}

void printDepartmentView(const vector<DepartmentView>& rows) {
    cout << left
         << setw(15) << "Department"
         << setw(18) << "Name"
         << setw(12) << "Employees"
         << setw(16) << "Avg Salary"
         << "Payroll\n";

    for (const auto& row : rows) {
        cout << setw(15) << row.departmentId
             << setw(18) << row.departmentName
             << setw(12) << row.employeeCount
             << setw(16) << fixed << setprecision(2)
             << row.averageSalary
             << row.payroll << '\n';
    }
}

void printProjectView(const vector<ProjectView>& rows) {
    cout << left
         << setw(12) << "Project ID"
         << setw(27) << "Project"
         << setw(16) << "Department"
         << setw(12) << "Hours"
         << "Budget\n";

    for (const auto& row : rows) {
        cout << setw(12) << row.projectId
             << setw(27) << row.projectName
             << setw(16) << row.departmentName
             << setw(12) << row.totalHours
             << row.budget << '\n';
    }
}


int main() {
    try {
        Repository repository;
        ViewEngine engine(repository);

        cout << "\n1. Employee Directory View\n";
        printEmployeeView(engine.employeeDirectory());

        cout << "\n2. Department Statistics View\n";
        printDepartmentView(
            engine.departmentStatistics(UserRole::Analyst)
        );

        cout << "\n3. Project Workload View\n";
        printProjectView(engine.projectWorkload());

        cout << "\n4. Filtered Project View\n";
        printProjectView(engine.highWorkloadProjects(100));

        cout << "\n5. Materialized View Cache\n";

        auto first = engine.materializedDepartmentStatistics(
            UserRole::Administrator
        );

        printDepartmentView(first);

        cout << "\n6. Repeated Cached Query\n";

        auto second = engine.materializedDepartmentStatistics(
            UserRole::Administrator
        );

        if (first.size() != second.size()) {
            throw ViewException("Cache validation failed.");
        }

        cout << "Cached result validated.\n";

        cout << "\n7. Base Table Modification\n";

        repository.updateEmployeeName(101, "Aarav Sharma");

        // The version change forces the cached view to be rebuilt.
        printDepartmentView(
            engine.materializedDepartmentStatistics(
                UserRole::Administrator
            )
        );

        cout << "\n8. Access Control\n";

        try {
            engine.departmentStatistics(UserRole::Reader);
        } catch (const ViewException& error) {
            cout << "Expected authorization failure: "
                 << error.what() << '\n';
        }

        cout << "\n9. Validation\n";

        try {
            engine.highWorkloadProjects(-10);
        } catch (const ViewException& error) {
            cout << "Expected validation failure: "
                 << error.what() << '\n';
        }

        cout << "\n10. Assertions\n";

        auto departments = engine.departmentStatistics(
            UserRole::Administrator
        );

        auto engineering = find_if(
            departments.begin(),
            departments.end(),
            [](const DepartmentView& item) {
                return item.departmentId == 1;
            }
        );

        if (engineering == departments.end() ||
            engineering->employeeCount != 2 ||
            abs(engineering->payroll - 205000.0) > 0.001) {
            throw ViewException(
                "Department statistics assertion failed."
            );
        }

        if (engine.employeeDirectory().size() != 5) {
            throw ViewException(
                "Employee directory assertion failed."
            );
        }

        if (engine.projectWorkload().size() != 4) {
            throw ViewException(
                "Project workload assertion failed."
            );
        }

        cout << "All assertions passed.\n";

    } catch (const exception& error) {
        cerr << "Application error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
