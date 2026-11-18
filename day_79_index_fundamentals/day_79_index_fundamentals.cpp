#include <algorithm>
#include <chrono>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std;

struct Employee {
    int id;
    string name;
    string department;
    double salary;
};

class BTree {
private:
    struct Node {
        bool leaf;
        vector<int> keys;
        vector<unique_ptr<Node>> children;

        explicit Node(bool isLeaf) : leaf(isLeaf) {}
    };

    unique_ptr<Node> root;
    int degree;

    void splitChild(Node* parent, int index) {
        Node* child = parent->children[index].get();

        auto sibling = make_unique<Node>(child->leaf);

        int median = child->keys[degree - 1];

        sibling->keys.assign(
            child->keys.begin() + degree,
            child->keys.end()
        );

        child->keys.resize(degree - 1);

        if (!child->leaf) {
            for (int i = degree; i < static_cast<int>(child->children.size()); i++) {
                sibling->children.push_back(
                    move(child->children[i])
                );
            }

            child->children.resize(degree);
        }

        parent->keys.insert(
            parent->keys.begin() + index,
            median
        );

        parent->children.insert(
            parent->children.begin() + index + 1,
            move(sibling)
        );
    }

    void insertNonFull(Node* node, int key) {
        int i = static_cast<int>(node->keys.size()) - 1;

        if (node->leaf) {
            node->keys.push_back(key);

            while (i >= 0 && node->keys[i] > key) {
                node->keys[i + 1] = node->keys[i];
                --i;
            }

            node->keys[i + 1] = key;
            return;
        }

        while (i >= 0 && key < node->keys[i]) {
            --i;
        }

        ++i;

        if (
            node->children[i]->keys.size() ==
            static_cast<size_t>(2 * degree - 1)
        ) {
            splitChild(node, i);

            if (key > node->keys[i]) {
                ++i;
            }
        }

        insertNonFull(node->children[i].get(), key);
    }

    bool searchNode(const Node* node, int key) const {
        auto iterator = lower_bound(
            node->keys.begin(),
            node->keys.end(),
            key
        );

        int index = static_cast<int>(
            iterator - node->keys.begin()
        );

        if (
            iterator != node->keys.end() &&
            *iterator == key
        ) {
            return true;
        }

        if (node->leaf) {
            return false;
        }

        return searchNode(node->children[index].get(), key);
    }

    void traverseNode(
        const Node* node,
        vector<int>& result
    ) const {
        for (size_t i = 0; i < node->keys.size(); ++i) {
            if (!node->leaf) {
                traverseNode(node->children[i].get(), result);
            }

            result.push_back(node->keys[i]);
        }

        if (!node->leaf) {
            traverseNode(node->children.back().get(), result);
        }
    }

    int validateNode(
        const Node* node,
        int lower,
        int upper,
        bool isRoot
    ) const {
        if (!is_sorted(node->keys.begin(), node->keys.end())) {
            throw logic_error("Unsorted B-tree node.");
        }

        if (
            node->keys.size() >
            static_cast<size_t>(2 * degree - 1)
        ) {
            throw logic_error("B-tree node exceeds capacity.");
        }

        if (
            !isRoot &&
            node->keys.size() < static_cast<size_t>(degree - 1)
        ) {
            throw logic_error("B-tree node below minimum occupancy.");
        }

        if (isRoot && !node->leaf && node->keys.empty()) {
            throw logic_error("Invalid empty internal root.");
        }

        for (int key : node->keys) {
            if (key <= lower || key >= upper) {
                throw logic_error("B-tree ordering violation.");
            }
        }

        if (node->leaf) {
            if (!node->children.empty()) {
                throw logic_error("Leaf contains children.");
            }
            return 1;
        }

        if (node->children.size() != node->keys.size() + 1) {
            throw logic_error("Invalid B-tree child count.");
        }

        int expectedHeight = -1;

        for (size_t i = 0; i < node->children.size(); ++i) {
            int childLower = i == 0
                ? lower
                : node->keys[i - 1];

            int childUpper = i == node->keys.size()
                ? upper
                : node->keys[i];

            int height = validateNode(
                node->children[i].get(),
                childLower,
                childUpper,
                false
            );

            if (expectedHeight == -1) {
                expectedHeight = height;
            } else if (height != expectedHeight) {
                throw logic_error("Unequal B-tree leaf depths.");
            }
        }

        return expectedHeight + 1;
    }

public:
    explicit BTree(int minimumDegree = 3)
        : root(make_unique<Node>(true)),
          degree(minimumDegree) {

        if (degree < 2) {
            throw invalid_argument("B-tree degree must be at least 2.");
        }
    }

    bool search(int key) const {
        return searchNode(root.get(), key);
    }

    void insert(int key) {
        if (search(key)) {
            throw invalid_argument("Duplicate index key.");
        }

        if (
            root->keys.size() ==
            static_cast<size_t>(2 * degree - 1)
        ) {
            auto newRoot = make_unique<Node>(false);

            newRoot->children.push_back(move(root));

            root = move(newRoot);

            splitChild(root.get(), 0);
        }

        insertNonFull(root.get(), key);
    }

    vector<int> traverse() const {
        vector<int> result;
        traverseNode(root.get(), result);
        return result;
    }

    vector<int> rangeSearch(int lower, int upper) const {
        if (lower > upper) {
            throw invalid_argument("Invalid range.");
        }

        vector<int> all = traverse();
        vector<int> result;

        auto first = lower_bound(
            all.begin(), all.end(), lower
        );

        auto last = upper_bound(
            all.begin(), all.end(), upper
        );

        result.assign(first, last);
        return result;
    }

    bool validate() const {
        validateNode(
            root.get(),
            numeric_limits<int>::min(),
            numeric_limits<int>::max(),
            true
        );

        return true;
    }
};

class Repository {
private:
    unordered_map<int, Employee> records;
    BTree primaryIndex;

public:
    Repository() : primaryIndex(4) {}

    void insert(const Employee& employee) {
        if (employee.id <= 0) {
            throw invalid_argument("Invalid employee ID.");
        }

        if (employee.name.empty() || employee.department.empty()) {
            throw invalid_argument("Missing employee information.");
        }

        if (!isfinite(employee.salary) || employee.salary < 0) {
            throw invalid_argument("Invalid salary.");
        }

        if (records.count(employee.id)) {
            throw invalid_argument("Duplicate employee.");
        }

        // Insert the index entry before publishing the record.
        primaryIndex.insert(employee.id);
        records.emplace(employee.id, employee);
    }

    const Employee* sequentialLookup(int id) const {
        for (const auto& [key, employee] : records) {
            if (key == id) {
                return &employee;
            }
        }

        return nullptr;
    }

    const Employee* indexedLookup(int id) const {
        if (!primaryIndex.search(id)) {
            return nullptr;
        }

        auto iterator = records.find(id);

        return iterator == records.end()
            ? nullptr
            : &iterator->second;
    }

    void updateSalary(int id, double salary) {
        if (!isfinite(salary) || salary < 0) {
            throw invalid_argument("Invalid salary.");
        }

        auto iterator = records.find(id);

        if (iterator == records.end()) {
            throw out_of_range("Employee not found.");
        }

        iterator->second.salary = salary;
    }

    vector<Employee> rangeLookup(int lower, int upper) const {
        vector<Employee> result;

        for (int id : primaryIndex.rangeSearch(lower, upper)) {
            auto iterator = records.find(id);

            if (iterator != records.end()) {
                result.push_back(iterator->second);
            }
        }

        return result;
    }

    bool verifyIntegrity() const {
        if (!primaryIndex.validate()) {
            return false;
        }

        vector<int> indexed = primaryIndex.traverse();

        if (indexed.size() != records.size()) {
            return false;
        }

        for (const auto& [id, employee] : records) {
            if (!primaryIndex.search(id)) {
                return false;
            }
        }

        return true;
    }

    size_t size() const {
        return records.size();
    }
};

void printEmployee(const Employee* employee) {
    if (employee == nullptr) {
        cout << "Record not found.\n";
        return;
    }

    cout << "ID: " << employee->id
         << " | Name: " << employee->name
         << " | Department: " << employee->department
         << " | Salary: " << fixed << setprecision(2)
         << employee->salary << '\n';
}

int main() {
    try {
        Repository repository;

        mt19937 generator(42);

        uniform_int_distribution<int> salaryDistribution(
            40000, 150000
        );

        vector<string> departments = {
            "Engineering",
            "Security",
            "Research",
            "Operations",
            "Finance"
        };

        for (int id = 1; id <= 10000; ++id) {
            repository.insert({
                id,
                "Employee " + to_string(id),
                departments[id % departments.size()],
                static_cast<double>(salaryDistribution(generator))
            });
        }

        cout << "INDEX FUNDAMENTALS\n";
        cout << "==============================\n";

        cout << "Total records: " << repository.size() << '\n';

        cout << "\n1. SEQUENTIAL LOOKUP\n";
        printEmployee(repository.sequentialLookup(7500));

        cout << "\n2. B-TREE INDEX LOOKUP\n";
        printEmployee(repository.indexedLookup(7500));

        cout << "\n3. MISSING RECORD\n";
        printEmployee(repository.indexedLookup(20000));

        cout << "\n4. RANGE LOOKUP\n";

        auto employees = repository.rangeLookup(100, 110);

        for (const auto& employee : employees) {
            cout << employee.id << " "
                 << employee.department << '\n';
        }

        cout << "\n5. UPDATE\n";
        repository.updateSalary(7500, 175000.0);
        printEmployee(repository.indexedLookup(7500));

        cout << "\n6. INDEX INTEGRITY\n";
        cout << boolalpha
             << repository.verifyIntegrity() << '\n';

        cout << "\n7. PERFORMANCE COMPARISON\n";

        vector<int> targets;
        uniform_int_distribution<int> idDistribution(1, 10000);

        for (int i = 0; i < 5000; ++i) {
            targets.push_back(idDistribution(generator));
        }

        volatile long long checksum = 0;

        auto start = chrono::high_resolution_clock::now();

        for (int id : targets) {
            const Employee* employee =
                repository.sequentialLookup(id);

            if (employee) checksum += employee->id;
        }

        auto sequentialEnd =
            chrono::high_resolution_clock::now();

        for (int id : targets) {
            const Employee* employee =
                repository.indexedLookup(id);

            if (employee) checksum += employee->id;
        }

        auto indexedEnd =
            chrono::high_resolution_clock::now();

        double sequentialTime =
            chrono::duration<double, milli>(
                sequentialEnd - start
            ).count();

        double indexedTime =
            chrono::duration<double, milli>(
                indexedEnd - sequentialEnd
            ).count();

        cout << "Sequential scan: "
             << sequentialTime << " ms\n";

        cout << "B-tree lookup: "
             << indexedTime << " ms\n";

        if (indexedTime > 0) {
            cout << "Observed ratio: "
                 << sequentialTime / indexedTime
                 << "x\n";
        }

        cout << "\n8. DUPLICATE VALIDATION\n";

        try {
            repository.insert({
                7500,
                "Duplicate",
                "Research",
                50000
            });
        } catch (const exception& error) {
            cout << "Rejected: " << error.what() << '\n';
        }

        cout << "\n9. INVALID RANGE\n";

        try {
            repository.rangeLookup(200, 100);
        } catch (const exception& error) {
            cout << "Rejected: " << error.what() << '\n';
        }

        cout << "\nExecution completed.\n";
        cout << "Checksum: " << checksum << '\n';

    } catch (const exception& error) {
        cerr << "Application error: "
             << error.what() << '\n';

        return 1;
    }

    return 0;
}
