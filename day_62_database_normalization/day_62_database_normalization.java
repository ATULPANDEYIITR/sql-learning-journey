import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

public class DatabaseNormalization {

    enum NormalForm {
        UNF, FIRST, SECOND, THIRD
    }

    static final class NormalizationException extends RuntimeException {
        NormalizationException(String message) {
            super(message);
        }
    }

    record FunctionalDependency(Set<String> determinant,
                                 Set<String> dependent) {

        FunctionalDependency {
            determinant = Set.copyOf(determinant);
            dependent = Set.copyOf(dependent);

            if (determinant.isEmpty() || dependent.isEmpty()) {
                throw new NormalizationException(
                    "Functional dependency sides cannot be empty."
                );
            }
        }

        @Override
        public String toString() {
            return String.join(", ", determinant)
                    + " -> "
                    + String.join(", ", dependent);
        }
    }

    static final class RelationSchema {
        private final String name;
        private final Set<String> attributes;
        private final List<Set<String>> candidateKeys;
        private final List<FunctionalDependency> dependencies;

        RelationSchema(
                String name,
                Set<String> attributes,
                List<Set<String>> candidateKeys,
                List<FunctionalDependency> dependencies) {

            this.name = Objects.requireNonNull(name);
            this.attributes = Set.copyOf(attributes);
            this.candidateKeys = candidateKeys.stream()
                    .map(Set::copyOf)
                    .toList();
            this.dependencies = List.copyOf(dependencies);

            validate();
        }

        private void validate() {
            if (name.isBlank() || attributes.isEmpty()) {
                throw new NormalizationException(
                    "Relation requires a name and attributes."
                );
            }

            if (candidateKeys.isEmpty()) {
                throw new NormalizationException(
                    "At least one candidate key is required."
                );
            }

            for (Set<String> key : candidateKeys) {
                if (key.isEmpty() || !attributes.containsAll(key)) {
                    throw new NormalizationException(
                        "Candidate key contains unknown attributes."
                    );
                }
            }

            for (FunctionalDependency fd : dependencies) {
                if (!attributes.containsAll(fd.determinant())
                        || !attributes.containsAll(fd.dependent())) {
                    throw new NormalizationException(
                        "Functional dependency contains unknown attributes."
                    );
                }
            }
        }

        Set<String> closure(Set<String> seed) {
            Set<String> closure = new HashSet<>(seed);
            boolean changed = true;

            while (changed) {
                changed = false;

                for (FunctionalDependency fd : dependencies) {
                    if (!closure.containsAll(fd.determinant())) {
                        continue;
                    }

                    for (String attribute : fd.dependent()) {
                        changed |= closure.add(attribute);
                    }
                }
            }

            return closure;
        }

        boolean isSuperkey(Set<String> determinant) {
            return closure(determinant).equals(attributes);
        }

        Set<String> primeAttributes() {
            Set<String> prime = new HashSet<>();

            for (Set<String> key : candidateKeys) {
                prime.addAll(key);
            }

            return prime;
        }

        List<FunctionalDependency> partialDependencies() {
            Set<String> prime = primeAttributes();
            List<FunctionalDependency> result = new ArrayList<>();

            for (FunctionalDependency fd : dependencies) {
                boolean hasNonPrimeDependent = fd.dependent()
                        .stream()
                        .anyMatch(attribute -> !prime.contains(attribute));

                if (!hasNonPrimeDependent) {
                    continue;
                }

                for (Set<String> key : candidateKeys) {
                    if (isProperSubset(fd.determinant(), key)) {
                        result.add(fd);
                        break;
                    }
                }
            }

            return result;
        }

        List<FunctionalDependency> transitiveDependencies() {
            Set<String> prime = primeAttributes();
            List<FunctionalDependency> result = new ArrayList<>();

            for (FunctionalDependency fd : dependencies) {
                if (isSuperkey(fd.determinant())) {
                    continue;
                }

                boolean hasNonPrimeDependent = fd.dependent()
                        .stream()
                        .anyMatch(attribute -> !prime.contains(attribute));

                if (hasNonPrimeDependent) {
                    result.add(fd);
                }
            }

            return result;
        }

        NormalForm highestNormalForm() {
            if (!partialDependencies().isEmpty()) {
                return NormalForm.FIRST;
            }

            if (!transitiveDependencies().isEmpty()) {
                return NormalForm.SECOND;
            }

            return NormalForm.THIRD;
        }

        String name() {
            return name;
        }

        List<Set<String>> candidateKeys() {
            return candidateKeys;
        }
    }

    static boolean isProperSubset(Set<String> left, Set<String> right) {
        return left.size() < right.size() && right.containsAll(left);
    }

    record Student(String id, String name) {
        Student {
            if (id.isBlank() || name.isBlank()) {
                throw new NormalizationException(
                    "Student ID and name are required."
                );
            }
        }
    }

    record Instructor(String id, String name) {
        Instructor {
            if (id.isBlank() || name.isBlank()) {
                throw new NormalizationException(
                    "Instructor ID and name are required."
                );
            }
        }
    }

    record Course(String id, String name, String instructorId) {
        Course {
            if (id.isBlank() || name.isBlank() || instructorId.isBlank()) {
                throw new NormalizationException(
                    "Course fields are required."
                );
            }
        }
    }

    record Enrollment(String studentId, String courseId, String grade) {
        Enrollment {
            if (studentId.isBlank() || courseId.isBlank()) {
                throw new NormalizationException(
                    "Enrollment identifiers are required."
                );
            }

            if (grade != null && !grade.matches("[A-F][+-]?")) {
                throw new NormalizationException(
                    "Invalid grade."
                );
            }
        }
    }

    interface NormalizationPolicy {
        List<String> validate(RelationSchema schema);
    }

    static final class ThirdNormalFormPolicy implements NormalizationPolicy {
        @Override
        public List<String> validate(RelationSchema schema) {
            List<String> violations = new ArrayList<>();

            schema.partialDependencies()
                    .forEach(fd -> violations.add(
                        "Partial dependency: " + fd
                    ));

            schema.transitiveDependencies()
                    .forEach(fd -> violations.add(
                        "Transitive dependency: " + fd
                    ));

            return Collections.unmodifiableList(violations);
        }
    }

    static final class NormalizationService {
        private final NormalizationPolicy policy;

        NormalizationService(NormalizationPolicy policy) {
            this.policy = policy;
        }

        void approveForProduction(RelationSchema schema) {
            List<String> violations = policy.validate(schema);

            if (!violations.isEmpty()) {
                throw new NormalizationException(
                    "Schema fails normalization policy: "
                    + String.join("; ", violations)
                );
            }
        }
    }

    static final class EnrollmentService {
        private final Map<String, Student> students = new HashMap<>();
        private final Map<String, Instructor> instructors = new HashMap<>();
        private final Map<String, Course> courses = new HashMap<>();
        private final Map<String, Enrollment> enrollments = new LinkedHashMap<>();

        void addStudent(Student student) {
            if (students.putIfAbsent(student.id(), student) != null) {
                throw new NormalizationException(
                    "Duplicate student: " + student.id()
                );
            }
        }

        void addInstructor(Instructor instructor) {
            if (instructors.putIfAbsent(instructor.id(), instructor) != null) {
                throw new NormalizationException(
                    "Duplicate instructor: " + instructor.id()
                );
            }
        }

        void addCourse(Course course) {
            if (!instructors.containsKey(course.instructorId())) {
                throw new NormalizationException(
                    "Unknown instructor: " + course.instructorId()
                );
            }

            if (courses.putIfAbsent(course.id(), course) != null) {
                throw new NormalizationException(
                    "Duplicate course: " + course.id()
                );
            }
        }

        void enroll(Enrollment enrollment) {
            if (!students.containsKey(enrollment.studentId())) {
                throw new NormalizationException(
                    "Unknown student: " + enrollment.studentId()
                );
            }

            if (!courses.containsKey(enrollment.courseId())) {
                throw new NormalizationException(
                    "Unknown course: " + enrollment.courseId()
                );
            }

            String compositeKey =
                    enrollment.studentId() + "|" + enrollment.courseId();

            if (enrollments.putIfAbsent(compositeKey, enrollment) != null) {
                throw new NormalizationException(
                    "Duplicate enrollment."
                );
            }
        }

        Map<String, Long> enrollmentCountByCourse() {
            return enrollments.values()
                    .stream()
                    .collect(Collectors.groupingBy(
                        Enrollment::courseId,
                        Collectors.counting()
                    ));
        }

        void printState() {
            System.out.println("\nStudents: " + students.values());
            System.out.println("Instructors: " + instructors.values());
            System.out.println("Courses: " + courses.values());
            System.out.println("Enrollments: " + enrollments.values());
        }
    }

    static RelationSchema createProblematicSchema() {
        return new RelationSchema(
            "EnrollmentRecord",
            Set.of(
                "student_id",
                "student_name",
                "course_id",
                "course_name",
                "instructor_id",
                "instructor_name",
                "grade"
            ),
            List.of(
                Set.of("student_id", "course_id")
            ),
            List.of(
                new FunctionalDependency(
                    Set.of("student_id"),
                    Set.of("student_name")
                ),
                new FunctionalDependency(
                    Set.of("course_id"),
                    Set.of("course_name", "instructor_id")
                ),
                new FunctionalDependency(
                    Set.of("instructor_id"),
                    Set.of("instructor_name")
                ),
                new FunctionalDependency(
                    Set.of("student_id", "course_id"),
                    Set.of("grade")
                )
            )
        );
    }

    static RelationSchema createThirdNormalFormSchema() {
        return new RelationSchema(
            "Enrollment",
            Set.of("student_id", "course_id", "grade"),
            List.of(Set.of("student_id", "course_id")),
            List.of(
                new FunctionalDependency(
                    Set.of("student_id", "course_id"),
                    Set.of("grade")
                )
            )
        );
    }

    public static void main(String[] args) {
        RelationSchema problematic = createProblematicSchema();

        System.out.println("=== Enterprise Normalization Review ===");
        System.out.println(
            "Highest form before decomposition: "
            + problematic.highestNormalForm()
        );

        System.out.println("\nDependency closures:");
        for (Set<String> key : problematic.candidateKeys()) {
            System.out.println(
                key + "+ = " + problematic.closure(key)
            );
        }

        NormalizationPolicy policy = new ThirdNormalFormPolicy();
        NormalizationService service = new NormalizationService(policy);

        try {
            service.approveForProduction(problematic);
        } catch (NormalizationException error) {
            System.out.println("\nExpected policy rejection:");
            System.out.println(error.getMessage());
        }

        RelationSchema enrollment = createThirdNormalFormSchema();

        System.out.println(
            "\nDecomposed Enrollment relation: "
            + enrollment.highestNormalForm()
        );

        EnrollmentService enrollmentService = new EnrollmentService();

        enrollmentService.addStudent(
            new Student("S001", "Asha Singh")
        );
        enrollmentService.addStudent(
            new Student("S002", "Rahul Kumar")
        );

        enrollmentService.addInstructor(
            new Instructor("I001", "Dr. Mehta")
        );
        enrollmentService.addInstructor(
            new Instructor("I002", "Dr. Rao")
        );

        enrollmentService.addCourse(
            new Course("C101", "Database Systems", "I001")
        );
        enrollmentService.addCourse(
            new Course("C102", "Operating Systems", "I002")
        );

        enrollmentService.enroll(
            new Enrollment("S001", "C101", "A")
        );
        enrollmentService.enroll(
            new Enrollment("S002", "C101", "B")
        );

        enrollmentService.printState();

        System.out.println(
            "\nEnrollment counts by course: "
            + enrollmentService.enrollmentCountByCourse()
        );

        try {
            enrollmentService.enroll(
                new Enrollment("S001", "C101", "A")
            );
        } catch (NormalizationException error) {
            System.out.println(
                "Expected duplicate-key failure: " + error.getMessage()
            );
        }

        try {
            enrollmentService.addCourse(
                new Course("C999", "Invalid Course", "I999")
            );
        } catch (NormalizationException error) {
            System.out.println(
                "Expected foreign-key failure: " + error.getMessage()
            );
        }

        /*
         * Domain objects own their validation rules. The normalization policy
         * is separated from persistence behavior, allowing the same policy
         * to be applied before a schema reaches a production database.
         */
    }
}
