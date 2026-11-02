import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

public class NormalizationCaseStudy {

    enum NormalForm {
        UNNORMALIZED,
        FIRST,
        SECOND,
        THIRD
    }

    enum Grade {
        A, B, C, D, F
    }

    record FunctionalDependency(
        Set<String> determinant,
        Set<String> dependent
    ) {
        FunctionalDependency {
            determinant = Set.copyOf(determinant);
            dependent = Set.copyOf(dependent);
        }

        @Override
        public String toString() {
            return String.join(", ", determinant)
                + " -> "
                + String.join(", ", dependent);
        }
    }

    record Student(int id, String name) {
        Student {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new DomainException("Invalid student.");
            }
        }
    }

    record Instructor(int id, String name) {
        Instructor {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new DomainException("Invalid instructor.");
            }
        }
    }

    record Course(int id, String name, int instructorId) {
        Course {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new DomainException("Invalid course.");
            }
        }
    }

    record Enrollment(
        int id,
        int studentId,
        int courseId,
        Grade grade
    ) {
        Enrollment {
            if (id <= 0 || studentId <= 0 || courseId <= 0) {
                throw new DomainException("Invalid enrollment.");
            }

            Objects.requireNonNull(grade, "Grade is required.");
        }
    }

    record TranscriptEntry(
        String courseName,
        String instructorName,
        Grade grade
    ) {}

    static final class DomainException extends RuntimeException {
        DomainException(String message) {
            super(message);
        }
    }

    static final class Relation {
        private final Set<String> columns;
        private final Set<String> primaryKey;
        private final List<Map<String, String>> rows;
        private final List<FunctionalDependency> dependencies;

        Relation(
            Set<String> columns,
            Set<String> primaryKey,
            List<Map<String, String>> rows,
            List<FunctionalDependency> dependencies
        ) {
            this.columns = Set.copyOf(columns);
            this.primaryKey = Set.copyOf(primaryKey);
            this.rows = List.copyOf(rows);
            this.dependencies = List.copyOf(dependencies);
        }

        private void validate() {
            if (columns.isEmpty()) {
                throw new DomainException("Relation has no columns.");
            }

            if (primaryKey.isEmpty()) {
                throw new DomainException("Relation has no primary key.");
            }

            if (!columns.containsAll(primaryKey)) {
                throw new DomainException(
                    "Primary-key column is not part of the relation."
                );
            }

            Set<List<String>> keys = new HashSet<>();

            for (Map<String, String> row : rows) {
                if (!row.keySet().containsAll(columns)) {
                    throw new DomainException(
                        "A row does not contain every relation attribute."
                    );
                }

                List<String> key = primaryKey.stream()
                    .sorted()
                    .map(row::get)
                    .toList();

                if (!keys.add(key)) {
                    throw new DomainException(
                        "Duplicate primary key detected."
                    );
                }
            }
        }

        NormalForm classify() {
            validate();

            for (FunctionalDependency fd : dependencies) {
                if (isPartial(fd)) {
                    return NormalForm.FIRST;
                }
            }

            for (FunctionalDependency fd : dependencies) {
                if (isTransitive(fd)) {
                    return NormalForm.SECOND;
                }
            }

            return NormalForm.THIRD;
        }

        private boolean isPartial(FunctionalDependency fd) {
            return fd.determinant().size() < primaryKey.size()
                && primaryKey.containsAll(fd.determinant())
                && fd.dependent().stream()
                    .anyMatch(attribute -> !primaryKey.contains(attribute));
        }

        private boolean isTransitive(FunctionalDependency fd) {
            boolean nonKeyDeterminant =
                fd.determinant().stream()
                    .anyMatch(attribute -> !primaryKey.contains(attribute));

            boolean nonKeyDependent =
                fd.dependent().stream()
                    .anyMatch(attribute -> !primaryKey.contains(attribute));

            return nonKeyDeterminant && nonKeyDependent;
        }
    }

    interface EnrollmentRepository {
        void save(Enrollment enrollment);

        List<Enrollment> findByStudent(int studentId);
    }

    static final class InMemoryEnrollmentRepository
        implements EnrollmentRepository {

        private final Map<Integer, Enrollment> records = new HashMap<>();

        @Override
        public void save(Enrollment enrollment) {
            if (records.containsKey(enrollment.id())) {
                throw new DomainException("Enrollment already exists.");
            }

            boolean duplicate = records.values().stream()
                .anyMatch(existing ->
                    existing.studentId() == enrollment.studentId()
                        && existing.courseId() == enrollment.courseId()
                );

            if (duplicate) {
                throw new DomainException(
                    "Student is already enrolled in the course."
                );
            }

            records.put(enrollment.id(), enrollment);
        }

        @Override
        public List<Enrollment> findByStudent(int studentId) {
            return records.values().stream()
                .filter(enrollment ->
                    enrollment.studentId() == studentId
                )
                .sorted((left, right) ->
                    Integer.compare(left.courseId(), right.courseId())
                )
                .toList();
        }
    }

    static final class EnrollmentService {
        private final Map<Integer, Student> students = new HashMap<>();
        private final Map<Integer, Instructor> instructors = new HashMap<>();
        private final Map<Integer, Course> courses = new HashMap<>();
        private final EnrollmentRepository repository;

        EnrollmentService(EnrollmentRepository repository) {
            this.repository = repository;
        }

        void addStudent(Student student) {
            if (students.putIfAbsent(student.id(), student) != null) {
                throw new DomainException("Student already exists.");
            }
        }

        void addInstructor(Instructor instructor) {
            if (
                instructors.putIfAbsent(
                    instructor.id(),
                    instructor
                ) != null
            ) {
                throw new DomainException("Instructor already exists.");
            }
        }

        void addCourse(Course course) {
            if (!instructors.containsKey(course.instructorId())) {
                throw new DomainException(
                    "Course references an unknown instructor."
                );
            }

            if (courses.putIfAbsent(course.id(), course) != null) {
                throw new DomainException("Course already exists.");
            }
        }

        void enroll(Enrollment enrollment) {
            if (!students.containsKey(enrollment.studentId())) {
                throw new DomainException("Unknown student.");
            }

            if (!courses.containsKey(enrollment.courseId())) {
                throw new DomainException("Unknown course.");
            }

            repository.save(enrollment);
        }

        List<TranscriptEntry> transcript(int studentId) {
            if (!students.containsKey(studentId)) {
                throw new DomainException("Unknown student.");
            }

            return repository.findByStudent(studentId)
                .stream()
                .map(enrollment -> {
                    Course course =
                        courses.get(enrollment.courseId());

                    Instructor instructor =
                        instructors.get(course.instructorId());

                    return new TranscriptEntry(
                        course.name(),
                        instructor.name(),
                        enrollment.grade()
                    );
                })
                .collect(Collectors.toUnmodifiableList());
        }
    }

    private static Relation createDenormalizedRelation() {
        return new Relation(
            Set.of(
                "student_id",
                "student_name",
                "course_id",
                "course_name",
                "instructor_id",
                "instructor_name",
                "grade"
            ),
            Set.of("student_id", "course_id"),
            List.of(
                Map.of(
                    "student_id", "1",
                    "student_name", "Asha",
                    "course_id", "101",
                    "course_name", "Database Systems",
                    "instructor_id", "7",
                    "instructor_name", "Dr Rao",
                    "grade", "A"
                ),
                Map.of(
                    "student_id", "1",
                    "student_name", "Asha",
                    "course_id", "102",
                    "course_name", "Networks",
                    "instructor_id", "8",
                    "instructor_name", "Dr Singh",
                    "grade", "B"
                )
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
                )
            )
        );
    }

    public static void main(String[] args) {
        Relation relation = createDenormalizedRelation();

        System.out.println(
            "Detected normal form: "
                + relation.classify()
        );

        EnrollmentService service =
            new EnrollmentService(
                new InMemoryEnrollmentRepository()
            );

        service.addStudent(new Student(1, "Asha"));
        service.addStudent(new Student(2, "Ravi"));

        service.addInstructor(new Instructor(7, "Dr Rao"));
        service.addInstructor(new Instructor(8, "Dr Singh"));

        service.addCourse(
            new Course(101, "Database Systems", 7)
        );
        service.addCourse(
            new Course(102, "Networks", 8)
        );

        service.enroll(
            new Enrollment(1001, 1, 101, Grade.A)
        );
        service.enroll(
            new Enrollment(1002, 1, 102, Grade.B)
        );

        System.out.println("\nTranscript:");

        service.transcript(1).forEach(entry ->
            System.out.printf(
                "%s | %s | %s%n",
                entry.courseName(),
                entry.instructorName(),
                entry.grade()
            )
        );

        try {
            service.enroll(
                new Enrollment(1003, 1, 101, Grade.A)
            );
        } catch (DomainException error) {
            System.out.println(
                "\nDuplicate enrollment rejected: "
                    + error.getMessage()
            );
        }

        try {
            service.addCourse(
                new Course(103, "Distributed Systems", 999)
            );
        } catch (DomainException error) {
            System.out.println(
                "Invalid foreign reference rejected: "
                    + error.getMessage()
            );
        }

        Collections.emptyList();
    }
}
