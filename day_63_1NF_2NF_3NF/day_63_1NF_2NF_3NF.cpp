#include <algorithm>
#include <exception>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

enum class NormalForm {
    Unnormalized,
    FirstNF,
    SecondNF,
    ThirdNF
};

std::string to_string(NormalForm form) {
    switch (form) {
        case NormalForm::Unnormalized:
            return "UNNORMALIZED";
        case NormalForm::FirstNF:
            return "1NF";
        case NormalForm::SecondNF:
            return "2NF";
        case NormalForm::ThirdNF:
            return "3NF";
    }

    return "UNKNOWN";
}

struct FunctionalDependency {
    std::set<std::string> determinant;
    std::set<std::string> dependent;

    std::string description() const {
        std::string result;

        for (auto it = determinant.begin(); it != determinant.end(); ++it) {
            if (it != determinant.begin()) {
                result += ", ";
            }
            result += *it;
        }

        result += " -> ";

        for (auto it = dependent.begin(); it != dependent.end(); ++it) {
            if (it != dependent.begin()) {
                result += ", ";
            }
            result += *it;
        }

        return result;
    }
};

using Row = std::map<std::string, std::string>;

class Relation {
private:
    std::string name_;
    std::set<std::string> columns_;
    std::set<std::string> primaryKey_;
    std::vector<Row> rows_;
    std::vector<FunctionalDependency> dependencies_;

public:
    Relation(
        std::string name,
        std::set<std::string> columns,
        std::set<std::string> primaryKey,
        std::vector<Row> rows,
        std::vector<FunctionalDependency> dependencies
    )
        : name_(std::move(name)),
          columns_(std::move(columns)),
          primaryKey_(std::move(primaryKey)),
          rows_(std::move(rows)),
          dependencies_(std::move(dependencies)) {}

    const std::set<std::string>& primaryKey() const {
        return primaryKey_;
    }

    const std::vector<FunctionalDependency>& dependencies() const {
        return dependencies_;
    }

    const std::vector<Row>& rows() const {
        return rows_;
    }

    void validate() const {
        if (columns_.empty()) {
            throw std::invalid_argument("Relation has no columns.");
        }

        if (primaryKey_.empty()) {
            throw std::invalid_argument("Relation has no primary key.");
        }

        for (const auto& key : primaryKey_) {
            if (!columns_.contains(key)) {
                throw std::invalid_argument(
                    "Primary-key column does not exist: " + key
                );
            }
        }

        std::set<std::vector<std::string>> seenKeys;

        for (const auto& row : rows_) {
            std::vector<std::string> key;

            for (const auto& column : primaryKey_) {
                auto iterator = row.find(column);

                if (iterator == row.end()) {
                    throw std::invalid_argument(
                        "Row is missing primary-key column: " + column
                    );
                }

                key.push_back(iterator->second);
            }

            if (!seenKeys.insert(key).second) {
                throw std::invalid_argument(
                    "Duplicate primary key detected."
                );
            }
        }
    }

    bool hasPartialDependency(
        const FunctionalDependency& fd
    ) const {
        if (fd.determinant.empty()) {
            return false;
        }

        if (fd.determinant.size() >= primaryKey_.size()) {
            return false;
        }

        for (const auto& determinantColumn : fd.determinant) {
            if (!primaryKey_.contains(determinantColumn)) {
                return false;
            }
        }

        for (const auto& dependentColumn : fd.dependent) {
            if (!primaryKey_.contains(dependentColumn)) {
                return true;
            }
        }

        return false;
    }

    bool hasTransitiveDependency(
        const FunctionalDependency& fd
    ) const {
        bool determinantIsNonKey = false;
        bool dependentIsNonKey = false;

        for (const auto& column : fd.determinant) {
            if (!primaryKey_.contains(column)) {
                determinantIsNonKey = true;
            }
        }

        for (const auto& column : fd.dependent) {
            if (!primaryKey_.contains(column)) {
                dependentIsNonKey = true;
            }
        }

        return determinantIsNonKey && dependentIsNonKey;
    }

    NormalForm classify() const {
        validate();

        for (const auto& row : rows_) {
            for (const auto& [column, value] : row) {
                if (value.find('|') != std::string::npos) {
                    return NormalForm::Unnormalized;
                }
            }
        }

        for (const auto& fd : dependencies_) {
            if (hasPartialDependency(fd)) {
                return NormalForm::FirstNF;
            }
        }

        for (const auto& fd : dependencies_) {
            if (hasTransitiveDependency(fd)) {
                return NormalForm::SecondNF;
            }
        }

        return NormalForm::ThirdNF;
    }
};

struct Student {
    int id;
    std::string name;
};

struct Instructor {
    int id;
    std::string name;
};

struct Course {
    int id;
    std::string name;
    int instructorId;
};

struct Enrollment {
    int id;
    int studentId;
    int courseId;
    std::string grade;
};

class GovernanceDatabase {
private:
    std::unordered_map<int, Student> students_;
    std::unordered_map<int, Instructor> instructors_;
    std::unordered_map<int, Course> courses_;
    std::unordered_map<int, Enrollment> enrollments_;

public:
    void addStudent(int id, const std::string& name) {
        if (id <= 0 || name.empty()) {
            throw std::invalid_argument("Invalid student.");
        }

        if (!students_.emplace(id, Student{id, name}).second) {
            throw std::invalid_argument("Student already exists.");
        }
    }

    void addInstructor(int id, const std::string& name) {
        if (id <= 0 || name.empty()) {
            throw std::invalid_argument("Invalid instructor.");
        }

        if (!instructors_.emplace(id, Instructor{id, name}).second) {
            throw std::invalid_argument("Instructor already exists.");
        }
    }

    void addCourse(int id, const std::string& name, int instructorId) {
        if (!instructors_.contains(instructorId)) {
            throw std::invalid_argument("Referenced instructor does not exist.");
        }

        if (!courses_.emplace(
                id,
                Course{id, name, instructorId}
            ).second) {
            throw std::invalid_argument("Course already exists.");
        }
    }

    void enroll(
        int id,
        int studentId,
        int courseId,
        const std::string& grade
    ) {
        if (!students_.contains(studentId)) {
            throw std::invalid_argument("Referenced student does not exist.");
        }

        if (!courses_.contains(courseId)) {
            throw std::invalid_argument("Referenced course does not exist.");
        }

        if (grade != "A" &&
            grade != "B" &&
            grade != "C" &&
            grade != "D" &&
            grade != "F") {
            throw std::invalid_argument("Invalid grade.");
        }

        if (!enrollments_.emplace(
                id,
                Enrollment{id, studentId, courseId, grade}
            ).second) {
            throw std::invalid_argument("Enrollment already exists.");
        }
    }

    std::vector<Enrollment> studentEnrollments(int studentId) const {
        std::vector<Enrollment> result;

        for (const auto& [id, enrollment] : enrollments_) {
            if (enrollment.studentId == studentId) {
                result.push_back(enrollment);
            }
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const Enrollment& left, const Enrollment& right) {
                return left.courseId < right.courseId;
            }
        );

        return result;
    }

    const Course& course(int id) const {
        return courses_.at(id);
    }

    const Instructor& instructor(int id) const {
        return instructors_.at(id);
    }
};

void demonstrateNormalization() {
    Relation enrollmentRecord(
        "EnrollmentRecord",
        {
            "student_id",
            "student_name",
            "course_id",
            "course_name",
            "instructor_id",
            "instructor_name",
            "grade"
        },
        {
            "student_id",
            "course_id"
        },
        {
            {
                {"student_id", "1"},
                {"student_name", "Asha"},
                {"course_id", "101"},
                {"course_name", "Database Systems"},
                {"instructor_id", "7"},
                {"instructor_name", "Dr Rao"},
                {"grade", "A"}
            },
            {
                {"student_id", "1"},
                {"student_name", "Asha"},
                {"course_id", "102"},
                {"course_name", "Networks"},
                {"instructor_id", "8"},
                {"instructor_name", "Dr Singh"},
                {"grade", "B"}
            }
        },
        {
            {
                {"student_id"},
                {"student_name"}
            },
            {
                {"course_id"},
                {"course_name", "instructor_id"}
            },
            {
                {"instructor_id"},
                {"instructor_name"}
            }
        }
    );

    NormalForm form = enrollmentRecord.classify();

    std::cout
        << "EnrollmentRecord normal form: "
        << to_string(form)
        << "\n";

    for (const auto& dependency : enrollmentRecord.dependencies()) {
        std::cout
            << "Dependency: "
            << dependency.description()
            << "\n";
    }
}

void demonstrate3NFWorkflow() {
    GovernanceDatabase database;

    database.addStudent(1, "Asha");
    database.addStudent(2, "Ravi");

    database.addInstructor(7, "Dr Rao");
    database.addInstructor(8, "Dr Singh");

    database.addCourse(101, "Database Systems", 7);
    database.addCourse(102, "Networks", 8);

    database.enroll(1001, 1, 101, "A");
    database.enroll(1002, 1, 102, "B");
    database.enroll(1003, 2, 101, "A");

    std::cout << "\nNormalized enrollment records:\n";

    for (const auto& enrollment : database.studentEnrollments(1)) {
        const auto& course = database.course(enrollment.courseId);
        const auto& instructor =
            database.instructor(course.instructorId);

        std::cout
            << "Course: " << course.name
            << ", Instructor: " << instructor.name
            << ", Grade: " << enrollment.grade
            << "\n";
    }

    try {
        database.enroll(1004, 1, 101, "Z");
    } catch (const std::exception& error) {
        std::cout
            << "Rejected invalid grade: "
            << error.what()
            << "\n";
    }

    try {
        database.addCourse(103, "Distributed Systems", 999);
    } catch (const std::exception& error) {
        std::cout
            << "Rejected invalid instructor reference: "
            << error.what()
            << "\n";
    }
}

int main() {
    try {
        demonstrateNormalization();
        demonstrate3NFWorkflow();
    } catch (const std::exception& error) {
        std::cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
