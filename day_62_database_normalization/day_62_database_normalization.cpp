#include <algorithm>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using Attribute = std::string;
using AttributeSet = std::set<Attribute>;

struct FunctionalDependency {
    AttributeSet determinant;
    AttributeSet dependent;

    std::string toString() const {
        auto format = [](const AttributeSet& values) {
            std::string result;
            bool first = true;

            for (const auto& value : values) {
                if (!first) {
                    result += ", ";
                }
                result += value;
                first = false;
            }

            return result;
        };

        return format(determinant) + " -> " + format(dependent);
    }
};

enum class NormalForm {
    UNF,
    FIRST,
    SECOND,
    THIRD
};

std::string normalFormName(NormalForm form) {
    switch (form) {
        case NormalForm::UNF: return "UNF";
        case NormalForm::FIRST: return "1NF";
        case NormalForm::SECOND: return "2NF";
        case NormalForm::THIRD: return "3NF";
    }

    return "UNKNOWN";
}

bool isSubset(const AttributeSet& left, const AttributeSet& right) {
    return std::includes(
        right.begin(),
        right.end(),
        left.begin(),
        left.end()
    );
}

bool isProperSubset(const AttributeSet& left, const AttributeSet& right) {
    return left.size() < right.size() && isSubset(left, right);
}

class Relation {
private:
    std::string name_;
    AttributeSet attributes_;
    std::vector<AttributeSet> candidateKeys_;
    std::vector<FunctionalDependency> dependencies_;

public:
    Relation(
        std::string name,
        AttributeSet attributes,
        std::vector<AttributeSet> candidateKeys,
        std::vector<FunctionalDependency> dependencies
    )
        : name_(std::move(name)),
          attributes_(std::move(attributes)),
          candidateKeys_(std::move(candidateKeys)),
          dependencies_(std::move(dependencies)) {
        validate();
    }

    const std::string& name() const {
        return name_;
    }

    const AttributeSet& attributes() const {
        return attributes_;
    }

    const std::vector<AttributeSet>& candidateKeys() const {
        return candidateKeys_;
    }

    const std::vector<FunctionalDependency>& dependencies() const {
        return dependencies_;
    }

    void validate() const {
        if (name_.empty() || attributes_.empty()) {
            throw std::invalid_argument("Relation requires a name and attributes.");
        }

        if (candidateKeys_.empty()) {
            throw std::invalid_argument("Relation requires a candidate key.");
        }

        for (const auto& key : candidateKeys_) {
            if (key.empty() || !isSubset(key, attributes_)) {
                throw std::invalid_argument("Invalid candidate key.");
            }
        }

        for (const auto& fd : dependencies_) {
            if (!isSubset(fd.determinant, attributes_) ||
                !isSubset(fd.dependent, attributes_)) {
                throw std::invalid_argument(
                    "Functional dependency contains unknown attributes."
                );
            }
        }
    }

    AttributeSet closure(AttributeSet seed) const {
        AttributeSet result = std::move(seed);

        bool changed = true;

        while (changed) {
            changed = false;

            for (const auto& fd : dependencies_) {
                if (!isSubset(fd.determinant, result)) {
                    continue;
                }

                for (const auto& attribute : fd.dependent) {
                    if (result.insert(attribute).second) {
                        changed = true;
                    }
                }
            }
        }

        return result;
    }

    bool isSuperkey(const AttributeSet& determinant) const {
        return closure(determinant) == attributes_;
    }

    AttributeSet primeAttributes() const {
        AttributeSet result;

        for (const auto& key : candidateKeys_) {
            result.insert(key.begin(), key.end());
        }

        return result;
    }

    std::vector<FunctionalDependency> partialDependencies() const {
        const auto prime = primeAttributes();
        std::vector<FunctionalDependency> result;

        for (const auto& fd : dependencies_) {
            bool determinesNonPrime = false;

            for (const auto& attribute : fd.dependent) {
                if (!prime.contains(attribute)) {
                    determinesNonPrime = true;
                    break;
                }
            }

            if (!determinesNonPrime) {
                continue;
            }

            for (const auto& key : candidateKeys_) {
                if (isProperSubset(fd.determinant, key)) {
                    result.push_back(fd);
                    break;
                }
            }
        }

        return result;
    }

    std::vector<FunctionalDependency> transitiveDependencies() const {
        const auto prime = primeAttributes();
        std::vector<FunctionalDependency> result;

        for (const auto& fd : dependencies_) {
            if (isSuperkey(fd.determinant)) {
                continue;
            }

            bool determinesNonPrime = false;

            for (const auto& attribute : fd.dependent) {
                if (!prime.contains(attribute)) {
                    determinesNonPrime = true;
                    break;
                }
            }

            if (determinesNonPrime) {
                result.push_back(fd);
            }
        }

        return result;
    }

    NormalForm highestNormalForm() const {
        if (!partialDependencies().empty()) {
            return NormalForm::FIRST;
        }

        if (!transitiveDependencies().empty()) {
            return NormalForm::SECOND;
        }

        return NormalForm::THIRD;
    }
};

struct ReviewResult {
    bool eligible;
    std::vector<std::string> reasons;
};

class NormalizationGovernanceEngine {
public:
    ReviewResult evaluate(const Relation& relation) const {
        ReviewResult result{true, {}};

        const auto partial = relation.partialDependencies();
        const auto transitive = relation.transitiveDependencies();

        if (!partial.empty()) {
            result.eligible = false;
            for (const auto& fd : partial) {
                result.reasons.push_back(
                    "Partial dependency: " + fd.toString()
                );
            }
        }

        if (!transitive.empty()) {
            result.eligible = false;
            for (const auto& fd : transitive) {
                result.reasons.push_back(
                    "Transitive dependency: " + fd.toString()
                );
            }
        }

        return result;
    }
};

struct Student {
    std::string id;
    std::string name;
};

struct Instructor {
    std::string id;
    std::string name;
};

struct Course {
    std::string id;
    std::string name;
    std::string instructorId;
};

struct Enrollment {
    std::string studentId;
    std::string courseId;
    std::string grade;
};

class EnrollmentRepository {
private:
    std::map<std::string, Student> students_;
    std::map<std::string, Instructor> instructors_;
    std::map<std::string, Course> courses_;
    std::map<std::pair<std::string, std::string>, Enrollment> enrollments_;

public:
    void addStudent(const Student& student) {
        if (student.id.empty() || student.name.empty()) {
            throw std::invalid_argument("Student identity is incomplete.");
        }

        students_.emplace(student.id, student);
    }

    void addInstructor(const Instructor& instructor) {
        if (instructor.id.empty() || instructor.name.empty()) {
            throw std::invalid_argument("Instructor identity is incomplete.");
        }

        instructors_.emplace(instructor.id, instructor);
    }

    void addCourse(const Course& course) {
        if (course.id.empty() || course.name.empty()) {
            throw std::invalid_argument("Course identity is incomplete.");
        }

        if (!instructors_.contains(course.instructorId)) {
            throw std::invalid_argument("Course references an unknown instructor.");
        }

        courses_.emplace(course.id, course);
    }

    void enroll(const Enrollment& enrollment) {
        if (!students_.contains(enrollment.studentId)) {
            throw std::invalid_argument("Enrollment references an unknown student.");
        }

        if (!courses_.contains(enrollment.courseId)) {
            throw std::invalid_argument("Enrollment references an unknown course.");
        }

        if (!enrollment.grade.empty() &&
            enrollment.grade != "A" &&
            enrollment.grade != "B" &&
            enrollment.grade != "C" &&
            enrollment.grade != "D" &&
            enrollment.grade != "F") {
            throw std::invalid_argument("Invalid grade.");
        }

        const auto key =
            std::make_pair(enrollment.studentId, enrollment.courseId);

        if (!enrollments_.emplace(key, enrollment).second) {
            throw std::invalid_argument("Duplicate enrollment.");
        }
    }

    void printState() const {
        std::cout << "\nStudents:\n";
        for (const auto& [id, student] : students_) {
            std::cout << "  " << id << " -> " << student.name << '\n';
        }

        std::cout << "\nInstructors:\n";
        for (const auto& [id, instructor] : instructors_) {
            std::cout << "  " << id << " -> " << instructor.name << '\n';
        }

        std::cout << "\nCourses:\n";
        for (const auto& [id, course] : courses_) {
            std::cout << "  " << id << " -> " << course.name
                      << " / instructor=" << course.instructorId << '\n';
        }

        std::cout << "\nEnrollments:\n";
        for (const auto& [key, enrollment] : enrollments_) {
            std::cout << "  " << key.first << " / " << key.second
                      << " -> grade=" << enrollment.grade << '\n';
        }
    }
};

int main() {
    try {
        const Relation enrollmentRelation(
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
                {"student_id", "course_id"}
            },
            {
                {{"student_id"}, {"student_name"}},
                {{"course_id"}, {"course_name", "instructor_id"}},
                {{"instructor_id"}, {"instructor_name"}},
                {{"student_id", "course_id"}, {"grade"}}
            }
        );

        NormalizationGovernanceEngine engine;
        const auto review = engine.evaluate(enrollmentRelation);

        std::cout << "=== Normalization Governance ===\n";
        std::cout << "Relation: " << enrollmentRelation.name() << '\n';
        std::cout << "Highest normal form: "
                  << normalFormName(enrollmentRelation.highestNormalForm())
                  << "\n\n";

        std::cout << "Candidate-key closures:\n";
        for (const auto& key : enrollmentRelation.candidateKeys()) {
            const auto closure = enrollmentRelation.closure(key);

            std::cout << "  {";
            bool first = true;
            for (const auto& attribute : key) {
                if (!first) std::cout << ", ";
                std::cout << attribute;
                first = false;
            }

            std::cout << "}+ = {";
            first = true;
            for (const auto& attribute : closure) {
                if (!first) std::cout << ", ";
                std::cout << attribute;
                first = false;
            }
            std::cout << "}\n";
        }

        std::cout << "\nGovernance decision: "
                  << (review.eligible ? "ACCEPT" : "REQUIRES DECOMPOSITION")
                  << '\n';

        for (const auto& reason : review.reasons) {
            std::cout << "  - " << reason << '\n';
        }

        EnrollmentRepository repository;

        repository.addStudent({"S001", "Asha Singh"});
        repository.addStudent({"S002", "Rahul Kumar"});

        repository.addInstructor({"I001", "Dr. Mehta"});
        repository.addInstructor({"I002", "Dr. Rao"});

        repository.addCourse({"C101", "Database Systems", "I001"});
        repository.addCourse({"C102", "Operating Systems", "I002"});

        repository.enroll({"S001", "C101", "A"});
        repository.enroll({"S002", "C101", "B"});

        repository.printState();

        std::cout << "\nNormalized decomposition:\n";
        std::cout << "  Student(student_id, student_name)\n";
        std::cout << "  Instructor(instructor_id, instructor_name)\n";
        std::cout << "  Course(course_id, course_name, instructor_id)\n";
        std::cout << "  Enrollment(student_id, course_id, grade)\n";

        try {
            repository.addCourse({"C103", "Invalid Course", "I999"});
        } catch (const std::exception& error) {
            std::cout << "\nExpected foreign-key failure: "
                      << error.what() << '\n';
        }

        try {
            repository.enroll({"S001", "C101", "A"});
        } catch (const std::exception& error) {
            std::cout << "Expected duplicate-key failure: "
                      << error.what() << '\n';
        }

        /*
         * The engine separates dependency analysis from storage.
         * The repository uses maps for near-constant lookup and composite
         * keys for enrollment uniqueness. This prevents redundant facts
         * from being copied into every enrollment record.
         */
    } catch (const std::exception& error) {
        std::cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
