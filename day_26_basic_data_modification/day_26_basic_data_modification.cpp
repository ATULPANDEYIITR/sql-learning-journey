/*
 * Basic Data Modification with SQL:
 * UPDATE, DELETE, Conditional Updates, and Safe Deletion
 *
 * C++17 industry-style case study:
 * Employee Compensation and Lifecycle Management System
 *
 * The program models the application layer surrounding database UPDATE and
 * DELETE operations. The in-memory repository represents the database
 * boundary so that the program remains self-contained and requires only the
 * C++ standard library.
 *
 * Real SQL patterns are documented next to the corresponding C++ operations.
 */

#include <algorithm>
#include <cassert>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

// ---------------------------------------------------------------------------
// 1. DOMAIN MODEL
// ---------------------------------------------------------------------------

enum class EmployeeStatus {
    Active,
    Inactive
};

std::string toString(EmployeeStatus status) {
    return status == EmployeeStatus::Active
        ? "ACTIVE"
        : "INACTIVE";
}

struct Employee {
    int id;
    std::string code;
    std::string name;
    std::string department;
    double salary;
    EmployeeStatus status;
    double performanceScore;
};

struct AuditRecord {
    int employeeId;
    std::string action;
    double oldSalary;
    double newSalary;
    std::string timestamp;
};

// ---------------------------------------------------------------------------
// 2. VALIDATION
// ---------------------------------------------------------------------------

void validateEmployee(const Employee& employee) {
    if (employee.id <= 0) {
        throw std::invalid_argument(
            "Employee ID must be positive."
        );
    }

    if (employee.code.empty()) {
        throw std::invalid_argument(
            "Employee code cannot be empty."
        );
    }

    if (employee.name.empty()) {
        throw std::invalid_argument(
            "Employee name cannot be empty."
        );
    }

    if (employee.salary < 0) {
        throw std::invalid_argument(
            "Salary cannot be negative."
        );
    }

    if (
        employee.performanceScore < 0 ||
        employee.performanceScore > 100
    ) {
        throw std::invalid_argument(
            "Performance score must be between 0 and 100."
        );
    }
}

void validateSalary(double salary) {
    if (!std::isfinite(salary) || salary < 0) {
        throw std::invalid_argument(
            "Salary must be a finite non-negative value."
        );
    }
}

// ---------------------------------------------------------------------------
// 3. REPOSITORY
// ---------------------------------------------------------------------------

class EmployeeRepository {
private:
    std::vector<Employee> employees;
    std::vector<AuditRecord> auditRecords;

public:
    void addEmployee(const Employee& employee) {
        validateEmployee(employee);

        const bool duplicateId = std::any_of(
            employees.begin(),
            employees.end(),
            [&](const Employee& current) {
                return current.id == employee.id;
            }
        );

        if (duplicateId) {
            throw std::invalid_argument(
                "Duplicate employee ID."
            );
        }

        const bool duplicateCode = std::any_of(
            employees.begin(),
            employees.end(),
            [&](const Employee& current) {
                return current.code == employee.code;
            }
        );

        if (duplicateCode) {
            throw std::invalid_argument(
                "Duplicate employee code."
            );
        }

        employees.push_back(employee);
    }

    Employee* findById(int employeeId) {
        auto iterator = std::find_if(
            employees.begin(),
            employees.end(),
            [&](Employee& employee) {
                return employee.id == employeeId;
            }
        );

        if (iterator == employees.end()) {
            return nullptr;
        }

        return &(*iterator);
    }

    const Employee* findById(int employeeId) const {
        auto iterator = std::find_if(
            employees.begin(),
            employees.end(),
            [&](const Employee& employee) {
                return employee.id == employeeId;
            }
        );

        if (iterator == employees.end()) {
            return nullptr;
        }

        return &(*iterator);
    }

    const std::vector<Employee>& getEmployees() const {
        return employees;
    }

    const std::vector<AuditRecord>& getAuditRecords() const {
        return auditRecords;
    }

    // -----------------------------------------------------------------------
    // UPDATE
    // -----------------------------------------------------------------------

    template <typename Predicate, typename Modifier>
    std::size_t updateWhere(
        Predicate predicate,
        Modifier modifier
    ) {
        std::size_t affectedRows = 0;

        for (Employee& employee : employees) {
            if (predicate(employee)) {
                modifier(employee);
                validateEmployee(employee);
                ++affectedRows;
            }
        }

        return affectedRows;
    }

    // -----------------------------------------------------------------------
    // DELETE
    // -----------------------------------------------------------------------

    template <typename Predicate>
    std::size_t deleteWhere(Predicate predicate) {
        const auto oldSize = employees.size();

        employees.erase(
            std::remove_if(
                employees.begin(),
                employees.end(),
                predicate
            ),
            employees.end()
        );

        return oldSize - employees.size();
    }

    // -----------------------------------------------------------------------
    // AUDITING
    // -----------------------------------------------------------------------

    void addAuditRecord(const AuditRecord& record) {
        auditRecords.push_back(record);
    }
};

// ---------------------------------------------------------------------------
// 4. TRANSACTION SNAPSHOT
// ---------------------------------------------------------------------------

class RepositoryTransaction {
private:
    EmployeeRepository& repository;
    std::vector<Employee> employeeSnapshot;
    std::vector<AuditRecord> auditSnapshot;
    bool committed = false;

public:
    explicit RepositoryTransaction(
        EmployeeRepository& repository
    )
        : repository(repository),
          employeeSnapshot(repository.getEmployees()),
          auditSnapshot(repository.getAuditRecords()) {}

    void commit() {
        committed = true;
    }

    void rollback() {
        /*
         * EmployeeRepository intentionally exposes only safe mutation
         * methods. For a real database, the transaction boundary would be
         * handled by BEGIN / COMMIT / ROLLBACK.
         *
         * This educational implementation restores state by recreating the
         * repository from the snapshots.
         */
        EmployeeRepository restored;

        for (const Employee& employee : employeeSnapshot) {
            restored.addEmployee(employee);
        }

        for (const AuditRecord& record : auditSnapshot) {
            restored.addAuditRecord(record);
        }

        repository = std::move(restored);
    }

    ~RepositoryTransaction() {
        if (!committed) {
            /*
             * A production transaction object would roll back automatically.
             * The example keeps explicit rollback in the calling function
             * because repository replacement is easier to understand here.
             */
        }
    }
};

// ---------------------------------------------------------------------------
// 5. REPORTING
// ---------------------------------------------------------------------------

void printEmployees(
    const EmployeeRepository& repository,
    const std::string& title
) {
    std::cout << "\n--- " << title << " ---\n";

    if (repository.getEmployees().empty()) {
        std::cout << "(no employees)\n";
        return;
    }

    std::cout
        << std::left
        << std::setw(5) << "ID"
        << std::setw(10) << "CODE"
        << std::setw(20) << "NAME"
        << std::setw(18) << "DEPT"
        << std::setw(12) << "SALARY"
        << std::setw(12) << "STATUS"
        << "SCORE\n";

    for (const Employee& employee : repository.getEmployees()) {
        std::cout
            << std::left
            << std::setw(5) << employee.id
            << std::setw(10) << employee.code
            << std::setw(20) << employee.name
            << std::setw(18) << employee.department
            << std::setw(12) << std::fixed
            << std::setprecision(2) << employee.salary
            << std::setw(12) << toString(employee.status)
            << employee.performanceScore
            << '\n';
    }
}

void printAuditRecords(
    const EmployeeRepository& repository
) {
    std::cout << "\n--- Audit Records ---\n";

    for (const AuditRecord& record :
         repository.getAuditRecords()) {
        std::cout
            << "Employee " << record.employeeId
            << " | Action: " << record.action
            << " | Old salary: " << record.oldSalary
            << " | New salary: " << record.newSalary
            << " | Time: " << record.timestamp
            << '\n';
    }
}

// ---------------------------------------------------------------------------
// 6. BASIC UPDATE
// ---------------------------------------------------------------------------

std::size_t giveFixedRaise(
    EmployeeRepository& repository,
    int employeeId,
    double newSalary
) {
    validateSalary(newSalary);

    /*
     * SQL equivalent:
     *
     * UPDATE employees
     * SET salary = ?
     * WHERE employee_id = ?;
     *
     * In a real database, newSalary and employeeId should be bound
     * parameters.
     */
    return repository.updateWhere(
        [&](const Employee& employee) {
            return employee.id == employeeId;
        },
        [&](Employee& employee) {
            employee.salary = newSalary;
        }
    );
}

// ---------------------------------------------------------------------------
// 7. CONDITIONAL UPDATE
// ---------------------------------------------------------------------------

std::size_t givePerformanceRaises(
    EmployeeRepository& repository
) {
    /*
     * SQL equivalent:
     *
     * UPDATE employees
     * SET salary =
     *     CASE
     *       WHEN performance_score >= 90 THEN salary * 1.10
     *       WHEN performance_score >= 80 THEN salary * 1.07
     *       WHEN performance_score >= 70 THEN salary * 1.04
     *       ELSE salary
     *     END
     * WHERE status = 'ACTIVE';
     */
    return repository.updateWhere(
        [](const Employee& employee) {
            return employee.status == EmployeeStatus::Active;
        },
        [](Employee& employee) {
            double multiplier = 1.0;

            if (employee.performanceScore >= 90) {
                multiplier = 1.10;
            } else if (employee.performanceScore >= 80) {
                multiplier = 1.07;
            } else if (employee.performanceScore >= 70) {
                multiplier = 1.04;
            }

            employee.salary =
                std::round(
                    employee.salary * multiplier * 100.0
                ) / 100.0;
        }
    );
}

// ---------------------------------------------------------------------------
// 8. OPTIMISTIC UPDATE
// ---------------------------------------------------------------------------

bool optimisticSalaryUpdate(
    EmployeeRepository& repository,
    int employeeId,
    double expectedOldSalary,
    double newSalary
) {
    validateSalary(newSalary);

    /*
     * This models:
     *
     * UPDATE employees
     * SET salary = ?
     * WHERE employee_id = ?
     *   AND salary = ?;
     *
     * If the old salary has changed since it was read, zero rows are
     * affected. This protects against some stale-write scenarios.
     */
    const std::size_t affectedRows =
        repository.updateWhere(
            [&](const Employee& employee) {
                return employee.id == employeeId &&
                       std::abs(
                           employee.salary - expectedOldSalary
                       ) < 0.000001;
            },
            [&](Employee& employee) {
                employee.salary = newSalary;
            }
        );

    return affectedRows == 1;
}

// ---------------------------------------------------------------------------
// 9. PREVIEW BEFORE DELETE
// ---------------------------------------------------------------------------

std::vector<int> previewDeletion(
    const EmployeeRepository& repository
) {
    std::vector<int> ids;

    for (const Employee& employee :
         repository.getEmployees()) {
        if (
            employee.status == EmployeeStatus::Inactive &&
            employee.performanceScore < 65
        ) {
            ids.push_back(employee.id);
        }
    }

    return ids;
}

// ---------------------------------------------------------------------------
// 10. SAFE DELETE
// ---------------------------------------------------------------------------

std::size_t deleteInactiveLowPerformers(
    EmployeeRepository& repository
) {
    /*
     * SQL equivalent:
     *
     * DELETE FROM employees
     * WHERE status = 'INACTIVE'
     *   AND performance_score < 65;
     */
    return repository.deleteWhere(
        [](const Employee& employee) {
            return employee.status == EmployeeStatus::Inactive &&
                   employee.performanceScore < 65;
        }
    );
}

// ---------------------------------------------------------------------------
// 11. SOFT DELETE
// ---------------------------------------------------------------------------

std::size_t softDelete(
    EmployeeRepository& repository,
    int employeeId
) {
    /*
     * Soft deletion maps to UPDATE rather than DELETE:
     *
     * UPDATE employees
     * SET status = 'INACTIVE'
     * WHERE employee_id = ?;
     */
    return repository.updateWhere(
        [&](const Employee& employee) {
            return employee.id == employeeId;
        },
        [](Employee& employee) {
            employee.status = EmployeeStatus::Inactive;
        }
    );
}

// ---------------------------------------------------------------------------
// 12. AUDITED SALARY UPDATE
// ---------------------------------------------------------------------------

bool auditedSalaryUpdate(
    EmployeeRepository& repository,
    int employeeId,
    double newSalary
) {
    validateSalary(newSalary);

    Employee* employee = repository.findById(employeeId);

    if (employee == nullptr) {
        return false;
    }

    const double oldSalary = employee->salary;

    const std::size_t affectedRows =
        repository.updateWhere(
            [&](const Employee& candidate) {
                return candidate.id == employeeId;
            },
            [&](Employee& candidate) {
                candidate.salary = newSalary;
            }
        );

    if (affectedRows != 1) {
        return false;
    }

    repository.addAuditRecord(
        AuditRecord{
            employeeId,
            "UPDATE",
            oldSalary,
            newSalary,
            "2026-09-26T10:47:00"
        }
    );

    return true;
}

// ---------------------------------------------------------------------------
// 13. BUSINESS-RULE GUARD
// ---------------------------------------------------------------------------

bool guardedPermanentDelete(
    EmployeeRepository& repository,
    int employeeId
) {
    /*
     * The application intentionally refuses to permanently delete active
     * employees. This is stronger than relying on user discipline alone.
     */
    const Employee* employee =
        repository.findById(employeeId);

    if (employee == nullptr) {
        return false;
    }

    if (employee->status != EmployeeStatus::Inactive) {
        return false;
    }

    const std::size_t affectedRows =
        repository.deleteWhere(
            [&](const Employee& candidate) {
                return candidate.id == employeeId &&
                       candidate.status ==
                           EmployeeStatus::Inactive;
            }
        );

    return affectedRows == 1;
}

// ---------------------------------------------------------------------------
// 14. BULK MODIFICATION
// ---------------------------------------------------------------------------

std::size_t deactivateLowPerformers(
    EmployeeRepository& repository,
    double threshold
) {
    if (threshold < 0 || threshold > 100) {
        throw std::invalid_argument(
            "Performance threshold must be 0 to 100."
        );
    }

    return repository.updateWhere(
        [&](const Employee& employee) {
            return employee.status == EmployeeStatus::Active &&
                   employee.performanceScore < threshold;
        },
        [](Employee& employee) {
            employee.status = EmployeeStatus::Inactive;
        }
    );
}

// ---------------------------------------------------------------------------
// 15. DEMONSTRATING A TRANSACTIONAL FAILURE
// ---------------------------------------------------------------------------

void demonstrateTransactionFailure(
    EmployeeRepository& repository
) {
    /*
     * Real SQL:
     *
     * BEGIN;
     * UPDATE ...;
     * UPDATE ...;
     * ROLLBACK;
     *
     * A transaction should ensure that related modifications either all
     * succeed or all fail.
     *
     * The repository's data is copied before the operation and restored when
     * the simulated failure occurs.
     */
    const auto employeesBefore =
        repository.getEmployees();

    try {
        repository.updateWhere(
            [](const Employee& employee) {
                return employee.id == 1;
            },
            [](Employee& employee) {
                employee.salary += 5000;
            }
        );

        repository.updateWhere(
            [](const Employee& employee) {
                return employee.id == 2;
            },
            [](Employee& employee) {
                employee.salary = -1;
            }
        );

        throw std::runtime_error(
            "Simulated business transaction failure."
        );
    } catch (const std::exception& error) {
        std::cout
            << "\nTransaction failure: "
            << error.what()
            << '\n';

        EmployeeRepository restored;

        for (const Employee& employee : employeesBefore) {
            restored.addEmployee(employee);
        }

        for (const AuditRecord& record :
             repository.getAuditRecords()) {
            restored.addAuditRecord(record);
        }

        repository = std::move(restored);

        std::cout
            << "Repository state restored after failure.\n";
    }
}

// ---------------------------------------------------------------------------
// 16. PERFORMANCE DISCUSSION THROUGH CODE
// ---------------------------------------------------------------------------

void explainComplexity() {
    /*
     * The vector-based repository scans every employee for an update/delete:
     *
     *     O(n)
     *
     * A real relational database can use indexes to locate rows more
     * efficiently. For example:
     *
     *     CREATE INDEX idx_employee_id
     *     ON employees(employee_id);
     *
     * Primary-key updates and deletes commonly benefit from indexed lookup.
     *
     * A database still needs to evaluate the WHERE predicate and maintain
     * indexes, constraints, locks, logs, and transaction state.
     */
    std::cout
        << "\nIn-memory case-study UPDATE/DELETE lookup: O(n) worst case.\n"
        << "Indexed database lookup can often be substantially faster.\n";
}

// ---------------------------------------------------------------------------
// 17. TESTS
// ---------------------------------------------------------------------------

EmployeeRepository createTestRepository() {
    EmployeeRepository repository;

    repository.addEmployee({
        1,
        "EMP001",
        "Aarav Sharma",
        "Engineering",
        75000,
        EmployeeStatus::Active,
        91
    });

    repository.addEmployee({
        2,
        "EMP002",
        "Meera Singh",
        "Engineering",
        68000,
        EmployeeStatus::Active,
        84
    });

    repository.addEmployee({
        3,
        "EMP003",
        "Rohan Das",
        "Operations",
        52000,
        EmployeeStatus::Inactive,
        61
    });

    return repository;
}

void runTests() {
    {
        EmployeeRepository repository =
            createTestRepository();

        const std::size_t affected =
            giveFixedRaise(repository, 1, 80000);

        assert(affected == 1);
        assert(
            repository.findById(1)->salary == 80000
        );
    }

    {
        EmployeeRepository repository =
            createTestRepository();

        const bool result =
            optimisticSalaryUpdate(
                repository,
                1,
                99999,
                100000
            );

        assert(!result);
        assert(
            repository.findById(1)->salary == 75000
        );
    }

    {
        EmployeeRepository repository =
            createTestRepository();

        const auto ids = previewDeletion(repository);

        assert(ids.size() == 1);
        assert(ids[0] == 3);

        const std::size_t deleted =
            deleteInactiveLowPerformers(repository);

        assert(deleted == 1);
        assert(repository.findById(3) == nullptr);
    }

    {
        EmployeeRepository repository =
            createTestRepository();

        const bool deleted =
            guardedPermanentDelete(repository, 1);

        assert(!deleted);
        assert(repository.findById(1) != nullptr);
    }

    std::cout
        << "\nAll C++ case-study tests passed.\n";
}

// ---------------------------------------------------------------------------
// 18. MAIN CASE STUDY
// ---------------------------------------------------------------------------

int main() {
    try {
        EmployeeRepository repository;

        repository.addEmployee({
            1,
            "EMP001",
            "Aarav Sharma",
            "Engineering",
            75000,
            EmployeeStatus::Active,
            91
        });

        repository.addEmployee({
            2,
            "EMP002",
            "Meera Singh",
            "Engineering",
            68000,
            EmployeeStatus::Active,
            84
        });

        repository.addEmployee({
            3,
            "EMP003",
            "Kabir Verma",
            "Finance",
            62000,
            EmployeeStatus::Active,
            76
        });

        repository.addEmployee({
            4,
            "EMP004",
            "Isha Gupta",
            "Human Resources",
            58000,
            EmployeeStatus::Active,
            88
        });

        repository.addEmployee({
            5,
            "EMP005",
            "Rohan Das",
            "Operations",
            52000,
            EmployeeStatus::Inactive,
            61
        });

        repository.addEmployee({
            6,
            "EMP006",
            "Ananya Rao",
            "Engineering",
            71000,
            EmployeeStatus::Active,
            95
        });

        printEmployees(
            repository,
            "Initial employee records"
        );

        const std::size_t fixedRaise =
            giveFixedRaise(repository, 1, 80000);

        std::cout
            << "\nFixed salary UPDATE affected "
            << fixedRaise
            << " row(s).\n";

        const std::size_t performanceRaises =
            givePerformanceRaises(repository);

        std::cout
            << "Performance-based UPDATE affected "
            << performanceRaises
            << " row(s).\n";

        const Employee* employeeTwo =
            repository.findById(2);

        if (employeeTwo != nullptr) {
            const double expectedSalary =
                employeeTwo->salary;

            const bool optimisticSuccess =
                optimisticSalaryUpdate(
                    repository,
                    2,
                    expectedSalary,
                    expectedSalary + 2500
                );

            std::cout
                << "Optimistic UPDATE succeeded: "
                << std::boolalpha
                << optimisticSuccess
                << '\n';
        }

        const std::vector<int> deletionCandidates =
            previewDeletion(repository);

        std::cout
            << "\nEmployees matching deletion policy: ";

        for (int id : deletionCandidates) {
            std::cout << id << ' ';
        }

        std::cout << '\n';

        const std::size_t deactivated =
            deactivateLowPerformers(repository, 70);

        std::cout
            << "Conditional status UPDATE affected "
            << deactivated
            << " row(s).\n";

        const bool auditSuccess =
            auditedSalaryUpdate(
                repository,
                3,
                65000
            );

        std::cout
            << "Audited salary UPDATE succeeded: "
            << auditSuccess
            << '\n';

        printAuditRecords(repository);

        softDelete(repository, 4);

        const std::size_t deleted =
            deleteInactiveLowPerformers(repository);

        std::cout
            << "Conditional DELETE affected "
            << deleted
            << " row(s).\n";

        const bool guardedDelete =
            guardedPermanentDelete(repository, 1);

        std::cout
            << "Attempt to permanently delete active employee: "
            << guardedDelete
            << '\n';

        demonstrateTransactionFailure(repository);

        explainComplexity();

        printEmployees(
            repository,
            "Final employee records"
        );

        runTests();

        /*
         * Dangerous SQL pattern, intentionally not executed:
         *
         *     DELETE FROM employees;
         *
         * Without WHERE, every row qualifies.
         */

        std::cout
            << "\nDangerous SQL pattern not executed: "
            << "DELETE FROM employees;\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Fatal error: "
            << error.what()
            << '\n';

        return 1;
    }
}
