#include <algorithm>
#include <iostream>
#include <queue>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

struct Employee {
    int id;
    std::string name;
    std::string title;
    int managerId; // -1 means organizational root.
};

struct HierarchyNode {
    int id;
    int depth;
    std::vector<int> path;
};

class GovernanceHierarchy {
private:
    std::unordered_map<int, Employee> employees;
    std::unordered_map<int, std::vector<int>> children;

    void validateAcyclic() const {
        // Color states are equivalent to the recursion-stack technique used
        // to detect cycles in recursive database traversals.
        std::unordered_map<int, int> state;

        std::function<void(int)> visit = [&](int id) {
            const int current = state[id];

            if (current == 1) {
                throw std::invalid_argument(
                    "Hierarchy contains a management cycle"
                );
            }

            if (current == 2) {
                return;
            }

            state[id] = 1;
            const int manager = employees.at(id).managerId;

            if (manager != -1) {
                visit(manager);
            }

            state[id] = 2;
        };

        for (const auto& [id, employee] : employees) {
            visit(id);
        }
    }

public:
    explicit GovernanceHierarchy(const std::vector<Employee>& input) {
        for (const auto& employee : input) {
            if (employees.contains(employee.id)) {
                throw std::invalid_argument("Duplicate employee ID");
            }

            employees.emplace(employee.id, employee);
        }

        for (const auto& [id, employee] : employees) {
            if (employee.managerId == id) {
                throw std::invalid_argument("Employee cannot manage itself");
            }

            if (employee.managerId != -1 &&
                !employees.contains(employee.managerId)) {
                throw std::invalid_argument(
                    "Employee references a missing manager"
                );
            }

            children[employee.managerId].push_back(id);
        }

        for (auto& [manager, directReports] : children) {
            std::sort(directReports.begin(), directReports.end());
        }

        validateAcyclic();
    }

    std::vector<HierarchyNode> recursiveTraversal(int rootId = -1) const {
        std::vector<HierarchyNode> result;
        std::queue<HierarchyNode> pending;

        if (rootId == -1) {
            for (int root : children.at(-1)) {
                pending.push({root, 0, {root}});
            }
        } else {
            if (!employees.contains(rootId)) {
                throw std::out_of_range("Unknown root employee");
            }
            pending.push({rootId, 0, {rootId}});
        }

        while (!pending.empty()) {
            HierarchyNode current = pending.front();
            pending.pop();

            result.push_back(current);

            const auto childIt = children.find(current.id);
            if (childIt == children.end()) {
                continue;
            }

            for (int childId : childIt->second) {
                if (std::find(
                        current.path.begin(),
                        current.path.end(),
                        childId
                    ) != current.path.end()) {
                    throw std::logic_error("Cycle detected during traversal");
                }

                auto nextPath = current.path;
                nextPath.push_back(childId);

                pending.push({
                    childId,
                    current.depth + 1,
                    std::move(nextPath)
                });
            }
        }

        return result;
    }

    std::unordered_map<int, std::size_t> calculateSubtreeSizes() const {
        auto traversal = recursiveTraversal();
        std::unordered_map<int, std::size_t> sizes;

        for (const auto& [id, employee] : employees) {
            sizes[id] = 1;
        }

        // Reversing a breadth-first traversal gives a safe child-before-parent
        // accumulation for a tree represented by parent references.
        std::reverse(traversal.begin(), traversal.end());

        for (const auto& node : traversal) {
            const int manager = employees.at(node.id).managerId;

            if (manager != -1) {
                sizes[manager] += sizes[node.id];
            }
        }

        return sizes;
    }

    std::vector<int> managementPath(int employeeId) const {
        if (!employees.contains(employeeId)) {
            throw std::out_of_range("Unknown employee");
        }

        std::vector<int> path;
        int current = employeeId;

        while (current != -1) {
            path.push_back(current);
            current = employees.at(current).managerId;
        }

        return path;
    }

    void printHierarchy() const {
        for (const auto& node : recursiveTraversal()) {
            std::cout
                << std::string(node.depth * 2, ' ')
                << employees.at(node.id).name
                << " [" << employees.at(node.id).title << "]"
                << " depth=" << node.depth
                << " path=";

            for (std::size_t i = 0; i < node.path.size(); ++i) {
                if (i != 0) {
                    std::cout << "->";
                }
                std::cout << node.path[i];
            }

            std::cout << '\n';
        }
    }
};

int main() {
    try {
        GovernanceHierarchy hierarchy({
            {1, "Maya", "Chief Executive Officer", -1},
            {2, "Arjun", "Chief Technology Officer", 1},
            {3, "Neha", "Chief Financial Officer", 1},
            {4, "Ravi", "Engineering Director", 2},
            {5, "Sara", "Security Director", 2},
            {6, "Asha", "Backend Engineer", 4},
            {7, "Dev", "Backend Engineer", 4},
            {8, "Meera", "Security Engineer", 5},
            {9, "Ishaan", "Security Analyst", 5}
        });

        std::cout << "ORGANIZATIONAL HIERARCHY\n";
        hierarchy.printHierarchy();

        std::cout << "\nSUBTREE SIZES\n";
        for (const auto& [id, size] : hierarchy.calculateSubtreeSizes()) {
            std::cout << id << ": " << size << '\n';
        }

        std::cout << "\nMANAGEMENT PATH FOR ASHA\n";
        for (int id : hierarchy.managementPath(6)) {
            std::cout << id << ' ';
        }
        std::cout << '\n';

        std::cout << "\nINVALID HIERARCHY TEST\n";

        try {
            GovernanceHierarchy invalid({
                {10, "A", "Director", 11},
                {11, "B", "Director", 10}
            });
        } catch (const std::exception& error) {
            std::cout << "Rejected: " << error.what() << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << "Fatal hierarchy error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
