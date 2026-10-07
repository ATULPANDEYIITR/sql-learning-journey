#include <algorithm>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

/*
 * Enterprise hierarchy case study
 *
 * The relational design represented here is conceptually:
 *
 *   Employee(employee_id, name, title, manager_id, department, salary)
 *
 * manager_id is a foreign key back to Employee.employee_id.
 *
 * A SELF JOIN uses two aliases of Employee:
 *
 *   Employee AS employee
 *   Employee AS manager
 *
 * and matches:
 *
 *   employee.manager_id = manager.employee_id
 *
 * This program models repository-independent organizational governance:
 * reporting relationships, hierarchy traversal, common managers, and safe
 * organizational changes.
 */

struct Employee {
    int id;
    string name;
    string title;
    optional<int> managerId;
    string department;
    double salary;
    bool active = true;
};

class Organization {
private:
    unordered_map<int, Employee> employees;

    const Employee& getEmployee(int id) const {
        auto it = employees.find(id);

        if (it == employees.end()) {
            throw runtime_error("Unknown employee ID: " + to_string(id));
        }

        return it->second;
    }

    Employee& getEmployee(int id) {
        auto it = employees.find(id);

        if (it == employees.end()) {
            throw runtime_error("Unknown employee ID: " + to_string(id));
        }

        return it->second;
    }

    vector<int> reportIds(int managerId) const {
        vector<int> result;

        for (const auto& [id, employee] : employees) {
            if (employee.active &&
                employee.managerId.has_value() &&
                *employee.managerId == managerId) {
                result.push_back(id);
            }
        }

        sort(
            result.begin(),
            result.end(),
            [this](int left, int right) {
                return getEmployee(left).name < getEmployee(right).name;
            }
        );

        return result;
    }

    void validateCycles() const {
        /*
         * A management hierarchy must be acyclic. The traversal follows
         * manager references rather than child references because a cycle
         * can be detected by observing a repeated employee ID.
         */
        for (const auto& [id, employee] : employees) {
            unordered_set<int> visited;
            optional<int> currentId = id;

            while (currentId.has_value()) {
                if (!visited.insert(*currentId).second) {
                    throw runtime_error(
                        "Management cycle detected at employee " +
                        to_string(*currentId)
                    );
                }

                const Employee& current = getEmployee(*currentId);
                currentId = current.managerId;
            }
        }
    }

public:
    explicit Organization(vector<Employee> employeeList) {
        for (const Employee& employee : employeeList) {
            if (!employees.emplace(employee.id, employee).second) {
                throw runtime_error(
                    "Duplicate employee ID: " + to_string(employee.id)
                );
            }
        }

        validate();
    }

    void validate() const {
        for (const auto& [id, employee] : employees) {
            if (!employee.managerId.has_value()) {
                continue;
            }

            int managerId = *employee.managerId;

            if (managerId == id) {
                throw runtime_error(
                    "Employee " + to_string(id) +
                    " cannot manage themselves."
                );
            }

            if (!employees.contains(managerId)) {
                throw runtime_error(
                    "Employee " + to_string(id) +
                    " references missing manager " +
                    to_string(managerId) + "."
                );
            }
        }

        validateCycles();
    }

    vector<pair<Employee, Employee>> selfJoin() const {
        /*
         * This method is the in-memory equivalent of:
         *
         * SELECT employee.*, manager.*
         * FROM employee
         * JOIN employee AS manager
         *   ON employee.manager_id = manager.employee_id;
         */
        vector<pair<Employee, Employee>> result;

        for (const auto& [id, employee] : employees) {
            if (!employee.managerId.has_value()) {
                continue;
            }

            result.emplace_back(
                employee,
                getEmployee(*employee.managerId)
            );
        }

        sort(
            result.begin(),
            result.end(),
            [](const auto& left, const auto& right) {
                return left.first.id < right.first.id;
            }
        );

        return result;
    }

    vector<Employee> directReports(int managerId) const {
        getEmployee(managerId);

        vector<Employee> result;

        for (int id : reportIds(managerId)) {
            result.push_back(getEmployee(id));
        }

        return result;
    }

    vector<Employee> managementChain(int employeeId) const {
        vector<Employee> chain;
        optional<int> currentId = employeeId;
        unordered_set<int> visited;

        while (currentId.has_value()) {
            if (!visited.insert(*currentId).second) {
                throw runtime_error("Cycle encountered during traversal.");
            }

            const Employee& employee = getEmployee(*currentId);
            chain.push_back(employee);
            currentId = employee.managerId;
        }

        return chain;
    }

    int hierarchyDepth(int employeeId) const {
        auto chain = managementChain(employeeId);
        return static_cast<int>(chain.size()) - 1;
    }

    optional<Employee> nearestCommonManager(
        int firstEmployeeId,
        int secondEmployeeId
    ) const {
        auto firstChain = managementChain(firstEmployeeId);
        auto secondChain = managementChain(secondEmployeeId);

        unordered_set<int> secondAncestors;

        for (const Employee& employee : secondChain) {
            secondAncestors.insert(employee.id);
        }

        for (const Employee& employee : firstChain) {
            if (secondAncestors.contains(employee.id)) {
                return employee;
            }
        }

        return nullopt;
    }

    vector<int> descendants(int employeeId) const {
        getEmployee(employeeId);

        vector<int> result;
        vector<int> queue{employeeId};
        size_t position = 0;

        while (position < queue.size()) {
            int currentId = queue[position++];

            for (int childId : reportIds(currentId)) {
                result.push_back(childId);
                queue.push_back(childId);
            }
        }

        return result;
    }

    void moveEmployee(int employeeId, optional<int> newManagerId) {
        Employee& employee = getEmployee(employeeId);

        if (newManagerId.has_value()) {
            getEmployee(*newManagerId);

            if (*newManagerId == employeeId) {
                throw runtime_error(
                    "An employee cannot become their own manager."
                );
            }

            auto childIds = descendants(employeeId);

            if (find(childIds.begin(), childIds.end(), *newManagerId)
                != childIds.end()) {
                throw runtime_error(
                    "A descendant cannot become a manager because "
                    "the change would create a cycle."
                );
            }
        }

        optional<int> oldManagerId = employee.managerId;
        employee.managerId = newManagerId;

        try {
            validate();
        } catch (...) {
            employee.managerId = oldManagerId;
            throw;
        }
    }

    string renderChart() const {
        unordered_map<int, vector<int>> children;
        vector<int> roots;

        for (const auto& [id, employee] : employees) {
            if (employee.managerId.has_value()) {
                children[*employee.managerId].push_back(id);
            } else {
                roots.push_back(id);
            }
        }

        auto sortIds = [this](vector<int>& ids) {
            sort(
                ids.begin(),
                ids.end(),
                [this](int left, int right) {
                    return getEmployee(left).name < getEmployee(right).name;
                }
            );
        };

        sortIds(roots);

        for (auto& [managerId, ids] : children) {
            sortIds(ids);
        }

        string output;

        function<void(int, int)> render =
            [&](int employeeId, int depth) {
                const Employee& employee = getEmployee(employeeId);

                output += string(depth * 2, ' ');
                output += "- " + employee.name;
                output += " (" + employee.title + ", ";
                output += employee.department + ")\n";

                for (int childId : children[employeeId]) {
                    render(childId, depth + 1);
                }
            };

        for (int rootId : roots) {
            render(rootId, 0);
        }

        return output;
    }
};

void printSelfJoin(const Organization& organization) {
    cout << "\nSELF JOIN employee-manager result\n";
    cout << "---------------------------------\n";

    for (const auto& [employee, manager] : organization.selfJoin()) {
        cout << employee.name
             << " -> "
             << manager.name
             << " [" << manager.title << "]\n";
    }
}

void printDirectReports(const Organization& organization, int managerId) {
    auto reports = organization.directReports(managerId);

    cout << "\nDirect reports of "
         << organization.managementChain(managerId).front().name
         << "\n";
    cout << "---------------------------------\n";

    for (const Employee& employee : reports) {
        cout << employee.name
             << " - "
             << employee.title
             << "\n";
    }
}

int main() {
    try {
        Organization organization({
            {1, "Anita", "Chief Executive Officer", nullopt,
             "Executive", 220000},
            {2, "Rahul", "VP Engineering", 1,
             "Engineering", 170000},
            {3, "Meera", "VP Operations", 1,
             "Operations", 165000},
            {4, "Vikram", "Engineering Manager", 2,
             "Engineering", 125000},
            {5, "Priya", "Engineering Manager", 2,
             "Engineering", 128000},
            {6, "Daniel", "Operations Manager", 3,
             "Operations", 120000},
            {7, "Arjun", "Senior Engineer", 4,
             "Engineering", 105000},
            {8, "Sana", "Software Engineer", 4,
             "Engineering", 90000},
            {9, "Karan", "Software Engineer", 5,
             "Engineering", 92000},
            {10, "Leena", "Software Engineer", 5,
             "Engineering", 94000},
            {11, "Rohit", "Operations Analyst", 6,
             "Operations", 76000},
            {12, "Neha", "Operations Analyst", 6,
             "Operations", 78000},
            {13, "Ishaan", "Intern", 7,
             "Engineering", 30000}
        });

        cout << "EMPLOYEE SELF JOIN HIERARCHY CASE STUDY\n";
        cout << "=======================================\n";

        cout << "\nOrganization chart\n";
        cout << "------------------\n";
        cout << organization.renderChart();

        printSelfJoin(organization);
        printDirectReports(organization, 5);

        cout << "\nHierarchy depth\n";
        cout << "---------------\n";

        for (int employeeId : {1, 5, 7, 13}) {
            auto chain = organization.managementChain(employeeId);

            cout << chain.front().name
                 << " has management depth "
                 << organization.hierarchyDepth(employeeId)
                 << "\n";
        }

        cout << "\nNearest common manager\n";
        cout << "----------------------\n";

        auto common = organization.nearestCommonManager(7, 9);

        if (common.has_value()) {
            cout << "Arjun and Karan share nearest manager: "
                 << common->name << "\n";
        }

        cout << "\nSafe hierarchy modification\n";
        cout << "---------------------------\n";

        organization.moveEmployee(8, 5);
        cout << "Sana moved under Priya.\n";
        cout << organization.renderChart();

        cout << "\nCycle prevention\n";
        cout << "----------------\n";

        try {
            organization.moveEmployee(2, 7);
        } catch (const exception& error) {
            cout << "Rejected: " << error.what() << "\n";
        }

        cout << "\nMissing manager validation\n";
        cout << "--------------------------\n";

        try {
            Organization invalid({
                {100, "Invalid", "Developer", 999,
                 "Engineering", 50000}
            });
        } catch (const exception& error) {
            cout << "Rejected: " << error.what() << "\n";
        }

        cout << "\nSelf-management validation\n";
        cout << "--------------------------\n";

        try {
            Organization invalid({
                {101, "Self Manager", "Developer", 101,
                 "Engineering", 50000}
            });
        } catch (const exception& error) {
            cout << "Rejected: " << error.what() << "\n";
        }

        cout << "\nComplexity considerations\n";
        cout << "-------------------------\n";
        cout << "A direct-report scan is O(n) without an index-like child map.\n";
        cout << "A hierarchy traversal is O(h) when following manager references,\n";
        cout << "where h is the employee's management depth.\n";
        cout << "The SQL equivalent can use an index on manager_id to avoid\n";
        cout << "repeatedly scanning the entire employee table for direct reports.\n";
    }
    catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
