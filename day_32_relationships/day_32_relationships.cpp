/*
    Relationships: One-to-One, One-to-Many, and Many-to-Many

    C++17 case study:
    A repository governance platform manages employees, departments,
    work items, and capabilities.

    Relationship model:

        Employee -> EmployeeProfile
            One-to-one

        Department -> WorkItem
            One-to-many

        Employee <-> Capability
            Many-to-many through EmployeeCapability

    The program focuses on the structural rules that make each
    relationship type different rather than presenting generic C++ syntax.
*/

#include <algorithm>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

class RelationshipError : public std::runtime_error {
public:
    explicit RelationshipError(const std::string& message)
        : std::runtime_error(message) {}
};

class NotFoundError : public RelationshipError {
public:
    explicit NotFoundError(const std::string& message)
        : RelationshipError(message) {}
};

class ConstraintError : public RelationshipError {
public:
    explicit ConstraintError(const std::string& message)
        : RelationshipError(message) {}
};

struct Employee {
    int id;
    std::string name;
    std::string email;
};

struct EmployeeProfile {
    int id;
    int employeeId;
    std::string role;
    std::string timezone;
};

struct Department {
    int id;
    std::string name;
    int managerId;
};

struct WorkItem {
    int id;
    int departmentId;
    std::string title;
    std::string status;
};

struct Capability {
    int id;
    std::string name;
};

struct EmployeeCapability {
    int employeeId;
    int capabilityId;
    std::string proficiency;
};

/*
    A pair is used as the logical primary key of the many-to-many
    association. Hashing it allows constant-average-time lookup.

    The pair is equivalent to a relational composite key such as:

        PRIMARY KEY (employee_id, capability_id)
*/
struct PairHash {
    std::size_t operator()(
        const std::pair<int, int>& value
    ) const noexcept {
        const auto first =
            static_cast<std::size_t>(value.first);

        const auto second =
            static_cast<std::size_t>(value.second);

        return first ^ (second + 0x9e3779b9 +
                        (first << 6) +
                        (first >> 2));
    }
};

class GovernanceRepository {
private:
    std::unordered_map<int, Employee> employees;
    std::unordered_map<int, EmployeeProfile> profiles;
    std::unordered_map<int, Department> departments;
    std::unordered_map<int, WorkItem> workItems;
    std::unordered_map<int, Capability> capabilities;

    // Many-to-many association table.
    std::unordered_map<
        std::pair<int, int>,
        EmployeeCapability,
        PairHash
    > employeeCapabilities;

    /*
        Relationship indexes.

        The maps are deliberately maintained separately from the entities.
        This mirrors the role database indexes can play when queries
        repeatedly traverse relationships.
    */
    std::unordered_map<int, int> profileByEmployee;

    std::unordered_map<
        int,
        std::unordered_set<int>
    > departmentsByManager;

    std::unordered_map<
        int,
        std::unordered_set<int>
    > workItemsByDepartment;

    std::unordered_map<
        int,
        std::unordered_set<int>
    > capabilitiesByEmployee;

    std::unordered_map<
        int,
        std::unordered_set<int>
    > employeesByCapability;

    static void requireNonEmpty(
        const std::string& value,
        const std::string& field
    ) {
        if (value.empty()) {
            throw ConstraintError(field + " cannot be empty.");
        }
    }

public:
    Employee& employee(int id) {
        auto it = employees.find(id);

        if (it == employees.end()) {
            throw NotFoundError(
                "Employee " + std::to_string(id) +
                " does not exist."
            );
        }

        return it->second;
    }

    const Employee& employee(int id) const {
        auto it = employees.find(id);

        if (it == employees.end()) {
            throw NotFoundError(
                "Employee " + std::to_string(id) +
                " does not exist."
            );
        }

        return it->second;
    }

    Department& department(int id) {
        auto it = departments.find(id);

        if (it == departments.end()) {
            throw NotFoundError(
                "Department " + std::to_string(id) +
                " does not exist."
            );
        }

        return it->second;
    }

    Capability& capability(int id) {
        auto it = capabilities.find(id);

        if (it == capabilities.end()) {
            throw NotFoundError(
                "Capability " + std::to_string(id) +
                " does not exist."
            );
        }

        return it->second;
    }

    void addEmployee(
        int id,
        const std::string& name,
        const std::string& email
    ) {
        requireNonEmpty(name, "Employee name");
        requireNonEmpty(email, "Employee email");

        if (email.find('@') == std::string::npos) {
            throw ConstraintError(
                "Employee email must contain '@'."
            );
        }

        if (employees.contains(id)) {
            throw ConstraintError(
                "Employee " + std::to_string(id) +
                " already exists."
            );
        }

        employees.emplace(
            id,
            Employee{id, name, email}
        );
    }

    /*
        One-to-one implementation.

        A normal foreign key from profile.employeeId to employee.id
        would guarantee that a profile references a real employee.

        The additional profileByEmployee uniqueness index guarantees
        that an employee cannot receive two profiles.
    */
    void addProfile(
        int profileId,
        int employeeId,
        const std::string& role,
        const std::string& timezone
    ) {
        employee(employeeId);
        requireNonEmpty(role, "Profile role");
        requireNonEmpty(timezone, "Profile timezone");

        if (profiles.contains(profileId)) {
            throw ConstraintError(
                "Profile " + std::to_string(profileId) +
                " already exists."
            );
        }

        if (profileByEmployee.contains(employeeId)) {
            throw ConstraintError(
                "Employee " + std::to_string(employeeId) +
                " already has a profile."
            );
        }

        profiles.emplace(
            profileId,
            EmployeeProfile{
                profileId,
                employeeId,
                role,
                timezone
            }
        );

        profileByEmployee[employeeId] = profileId;
    }

    std::optional<EmployeeProfile> findProfile(
        int employeeId
    ) const {
        employee(employeeId);

        auto mapping = profileByEmployee.find(employeeId);

        if (mapping == profileByEmployee.end()) {
            return std::nullopt;
        }

        auto profile = profiles.find(mapping->second);

        if (profile == profiles.end()) {
            throw ConstraintError(
                "Profile index points to missing profile."
            );
        }

        return profile->second;
    }

    /*
        One-to-many implementation.

        The department ID is stored on every WorkItem. Multiple work
        items may therefore contain the same department ID.

        No uniqueness rule is placed on WorkItem.departmentId because
        uniqueness there would accidentally convert the relationship
        into one-to-one.
    */
    void addDepartment(
        int departmentId,
        const std::string& name,
        int managerId
    ) {
        employee(managerId);
        requireNonEmpty(name, "Department name");

        if (departments.contains(departmentId)) {
            throw ConstraintError(
                "Department " + std::to_string(departmentId) +
                " already exists."
            );
        }

        departments.emplace(
            departmentId,
            Department{
                departmentId,
                name,
                managerId
            }
        );

        departmentsByManager[managerId].insert(
            departmentId
        );
    }

    void addWorkItem(
        int workItemId,
        int departmentId,
        const std::string& title,
        const std::string& status
    ) {
        department(departmentId);
        requireNonEmpty(title, "Work item title");

        const std::unordered_set<std::string> validStatuses{
            "open",
            "in_progress",
            "done"
        };

        if (!validStatuses.contains(status)) {
            throw ConstraintError(
                "Invalid work item status: " + status
            );
        }

        if (workItems.contains(workItemId)) {
            throw ConstraintError(
                "Work item " +
                std::to_string(workItemId) +
                " already exists."
            );
        }

        workItems.emplace(
            workItemId,
            WorkItem{
                workItemId,
                departmentId,
                title,
                status
            }
        );

        workItemsByDepartment[departmentId].insert(
            workItemId
        );
    }

    std::vector<WorkItem> workItemsForDepartment(
        int departmentId
    ) const {
        department(departmentId);

        std::vector<WorkItem> result;

        auto mapping =
            workItemsByDepartment.find(departmentId);

        if (mapping == workItemsByDepartment.end()) {
            return result;
        }

        for (int workItemId : mapping->second) {
            auto item = workItems.find(workItemId);

            if (item == workItems.end()) {
                throw ConstraintError(
                    "Work item index contains an invalid ID."
                );
            }

            result.push_back(item->second);
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const WorkItem& left, const WorkItem& right) {
                return left.id < right.id;
            }
        );

        return result;
    }

    /*
        Many-to-many implementation.

        EmployeeCapability is an association entity. It can carry
        attributes that belong to the relationship itself, such as
        proficiency.

        The pair (employeeId, capabilityId) is unique. Without that
        composite-key rule, the same employee could accidentally be
        associated with the same capability multiple times.
    */
    void assignCapability(
        int employeeId,
        int capabilityId,
        const std::string& proficiency
    ) {
        employee(employeeId);
        capability(capabilityId);

        const std::unordered_set<std::string> validProficiency{
            "beginner",
            "intermediate",
            "advanced",
            "expert"
        };

        if (!validProficiency.contains(proficiency)) {
            throw ConstraintError(
                "Invalid proficiency: " + proficiency
            );
        }

        const std::pair<int, int> key{
            employeeId,
            capabilityId
        };

        if (employeeCapabilities.contains(key)) {
            throw ConstraintError(
                "The employee-capability relationship already exists."
            );
        }

        employeeCapabilities.emplace(
            key,
            EmployeeCapability{
                employeeId,
                capabilityId,
                proficiency
            }
        );

        capabilitiesByEmployee[employeeId].insert(
            capabilityId
        );

        employeesByCapability[capabilityId].insert(
            employeeId
        );
    }

    std::vector<EmployeeCapability> capabilitiesForEmployee(
        int employeeId
    ) const {
        employee(employeeId);

        std::vector<EmployeeCapability> result;

        auto mapping =
            capabilitiesByEmployee.find(employeeId);

        if (mapping == capabilitiesByEmployee.end()) {
            return result;
        }

        for (int capabilityId : mapping->second) {
            const std::pair<int, int> key{
                employeeId,
                capabilityId
            };

            auto relation =
                employeeCapabilities.find(key);

            if (relation == employeeCapabilities.end()) {
                throw ConstraintError(
                    "Employee capability index is inconsistent."
                );
            }

            result.push_back(relation->second);
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const EmployeeCapability& left,
               const EmployeeCapability& right) {
                return left.capabilityId < right.capabilityId;
            }
        );

        return result;
    }

    std::vector<EmployeeCapability> employeesForCapability(
        int capabilityId
    ) const {
        capability(capabilityId);

        std::vector<EmployeeCapability> result;

        auto mapping =
            employeesByCapability.find(capabilityId);

        if (mapping == employeesByCapability.end()) {
            return result;
        }

        for (int employeeId : mapping->second) {
            const std::pair<int, int> key{
                employeeId,
                capabilityId
            };

            auto relation =
                employeeCapabilities.find(key);

            if (relation == employeeCapabilities.end()) {
                throw ConstraintError(
                    "Capability employee index is inconsistent."
                );
            }

            result.push_back(relation->second);
        }

        return result;
    }

    /*
        Restricting parent deletion prevents dangling children.

        This is analogous to a foreign key configured with a restrictive
        delete policy rather than cascading the delete automatically.
    */
    void deleteDepartment(int departmentId) {
        Department& parent = department(departmentId);

        auto children =
            workItemsByDepartment.find(departmentId);

        if (children != workItemsByDepartment.end() &&
            !children->second.empty()) {
            throw ConstraintError(
                "Department " +
                std::to_string(departmentId) +
                " cannot be deleted while work items reference it."
            );
        }

        departmentsByManager[parent.managerId].erase(
            departmentId
        );

        departments.erase(departmentId);
        workItemsByDepartment.erase(departmentId);
    }

    void deleteWorkItem(int workItemId) {
        auto item = workItems.find(workItemId);

        if (item == workItems.end()) {
            throw NotFoundError(
                "Work item " +
                std::to_string(workItemId) +
                " does not exist."
            );
        }

        workItemsByDepartment[item->second.departmentId].erase(
            workItemId
        );

        workItems.erase(item);
    }

    void removeCapability(
        int employeeId,
        int capabilityId
    ) {
        employee(employeeId);
        capability(capabilityId);

        const std::pair<int, int> key{
            employeeId,
            capabilityId
        };

        if (!employeeCapabilities.contains(key)) {
            throw NotFoundError(
                "Employee-capability relationship does not exist."
            );
        }

        employeeCapabilities.erase(key);
        capabilitiesByEmployee[employeeId].erase(
            capabilityId
        );
        employeesByCapability[capabilityId].erase(
            employeeId
        );
    }

    /*
        A graph consistency check is useful in systems where several
        indexes are maintained for fast traversal. It catches a class
        of bugs that ordinary entity validation would miss.
    */
    void validateRelationshipGraph() const {
        for (const auto& [employeeId, profileId] :
             profileByEmployee) {
            if (!employees.contains(employeeId)) {
                throw ConstraintError(
                    "Profile index references missing employee."
                );
            }

            if (!profiles.contains(profileId)) {
                throw ConstraintError(
                    "Profile index references missing profile."
                );
            }

            if (profiles.at(profileId).employeeId != employeeId) {
                throw ConstraintError(
                    "Profile index has mismatched foreign key."
                );
            }
        }

        for (const auto& [key, relation] :
             employeeCapabilities) {
            if (!employees.contains(relation.employeeId)) {
                throw ConstraintError(
                    "Association references missing employee."
                );
            }

            if (!capabilities.contains(relation.capabilityId)) {
                throw ConstraintError(
                    "Association references missing capability."
                );

            if (!capabilitiesByEmployee.at(
                    relation.employeeId
                ).contains(relation.capabilityId)) {
                throw ConstraintError(
                    "Forward capability index is inconsistent."
                );
            }

            if (!employeesByCapability.at(
                    relation.capabilityId
                ).contains(relation.employeeId)) {
                throw ConstraintError(
                    "Reverse capability index is inconsistent."
                );
        }
    }
};

void printDepartment(
    const GovernanceRepository& repository,
    int departmentId
) {
    const auto items =
        repository.workItemsForDepartment(departmentId);

    std::cout
        << "Department " << departmentId
        << " contains " << items.size()
        << " work item(s)\n";

    for (const auto& item : items) {
        std::cout
            << "  [" << item.status << "] "
            << item.title << '\n';
    }
}

int main() {
    try {
        GovernanceRepository repository;

        std::cout << "RELATIONSHIP GOVERNANCE CASE STUDY\n";
        std::cout << "==================================\n\n";

        repository.addEmployee(
            1,
            "Atul",
            "atul@example.com"
        );

        repository.addEmployee(
            2,
            "Maya",
            "maya@example.com"
        );

        repository.addEmployee(
            3,
            "Liam",
            "liam@example.com"
        );

        std::cout << "One-to-one relationship\n";
        std::cout << "-----------------------\n";

        repository.addProfile(
            101,
            1,
            "Platform Engineer",
            "Asia/Kolkata"
        );

        auto profile = repository.findProfile(1);

        if (profile.has_value()) {
            std::cout
                << profile->role
                << " / "
                << profile->timezone
                << "\n";
        }

        std::cout << "\nOne-to-many relationship\n";
        std::cout << "-------------------------\n";

        repository.addDepartment(
            201,
            "Market Analytics",
            1
        );

        repository.addDepartment(
            202,
            "Security Engineering",
            2
        );

        repository.addWorkItem(
            301,
            201,
            "Build market data pipeline",
            "in_progress"
        );

        repository.addWorkItem(
            302,
            201,
            "Validate risk calculations",
            "open"
        );

        repository.addWorkItem(
            303,
            201,
            "Publish analytics report",
            "done"
        );

        repository.addWorkItem(
            304,
            202,
            "Review access controls",
            "in_progress"
        );

        printDepartment(repository, 201);
        printDepartment(repository, 202);

        std::cout << "\nMany-to-many relationship\n";
        std::cout << "-------------------------\n";

        repository.addCapability(
            401,
            "SQL"
        );

        repository.addCapability(
            402,
            "Python"
        );

        repository.addCapability(
            403,
            "Cybersecurity"
        );

        repository.addCapability(
            404,
            "Product Management"
        );

        repository.assignCapability(
            1,
            401,
            "advanced"
        );

        repository.assignCapability(
            1,
            402,
            "expert"
        );

        repository.assignCapability(
            2,
            401,
            "intermediate"
        );

        repository.assignCapability(
            2,
            404,
            "advanced"
        );

        repository.assignCapability(
            3,
            403,
            "beginner"
        );

        std::cout << "Capabilities for Atul:\n";

        for (const auto& relation :
             repository.capabilitiesForEmployee(1)) {
            std::cout
                << "  capability "
                << relation.capabilityId
                << " -> "
                << relation.proficiency
                << '\n';
        }

        std::cout << "Employees associated with SQL:\n";

        for (const auto& relation :
             repository.employeesForCapability(401)) {
            std::cout
                << "  employee "
                << relation.employeeId
                << " -> "
                << relation.proficiency
                << '\n';
        }

        std::cout << "\nConstraint demonstrations\n";
        std::cout << "--------------------------\n";

        try {
            repository.addProfile(
                102,
                1,
                "Second Profile",
                "UTC"
            );
        } catch (const ConstraintError& error) {
            std::cout
                << "One-to-one rejection: "
                << error.what()
                << '\n';
        }

        try {
            repository.assignCapability(
                1,
                401,
                "expert"
            );
        } catch (const ConstraintError& error) {
            std::cout
                << "Duplicate many-to-many rejection: "
                << error.what()
                << '\n';
        }

        try {
            repository.addWorkItem(
                305,
                999,
                "Invalid parent reference",
                "open"
            );
        } catch (const NotFoundError& error) {
            std::cout
                << "Foreign-key rejection: "
                << error.what()
                << '\n';
        }

        try {
            repository.deleteDepartment(201);
        } catch (const ConstraintError& error) {
            std::cout
                << "Restricted parent deletion: "
                << error.what()
                << '\n';
        }

        std::cout << "\nDependency removal\n";
        std::cout << "------------------\n";

        repository.deleteWorkItem(301);
        repository.deleteWorkItem(302);
        repository.deleteWorkItem(303);

        repository.deleteDepartment(201);

        std::cout
            << "Department 201 deleted after its child work items "
               "were removed.\n";

        std::cout << "\nRemoving an association\n";
        std::cout << "-----------------------\n";

        repository.removeCapability(1, 402);

        std::cout
            << "Python association removed from employee 1.\n";

        std::cout << "\nGraph validation\n";
        std::cout << "----------------\n";

        repository.validateRelationshipGraph();

        std::cout
            << "All maintained relationship indexes are consistent.\n";

        std::cout << "\nComplexity characteristics\n";
        std::cout << "--------------------------\n";
        std::cout
            << "Entity lookup uses unordered_map with average O(1) lookup.\n";
        std::cout
            << "Relationship membership uses unordered_set with average O(1) insertion and lookup.\n";
        std::cout
            << "Many-to-many traversal is proportional to the number of related records rather than all entities.\n";
        std::cout
            << "The composite association key prevents duplicate pairs without scanning the entire relationship table.\n";

    } catch (const std::exception& error) {
        std::cerr
            << "Fatal relationship-model error: "
            << error.what()
            << '\n';

        return 1;
    }

    return 0;
}
