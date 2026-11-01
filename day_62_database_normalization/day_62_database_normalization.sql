DROP SCHEMA IF EXISTS normalization_lab CASCADE;

CREATE SCHEMA normalization_lab;

SET search_path TO normalization_lab;

-- ============================================================
-- Reference entities
-- ============================================================

CREATE TABLE students (
    student_id      VARCHAR(20) PRIMARY KEY,
    student_name    VARCHAR(120) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT students_name_not_blank
        CHECK (length(btrim(student_name)) > 0)
);

CREATE TABLE instructors (
    instructor_id   VARCHAR(20) PRIMARY KEY,
    instructor_name VARCHAR(120) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    CONSTRAINT instructors_name_not_blank
        CHECK (length(btrim(instructor_name)) > 0)
);

CREATE TABLE courses (
    course_id       VARCHAR(20) PRIMARY KEY,
    course_name     VARCHAR(150) NOT NULL,
    instructor_id   VARCHAR(20) NOT NULL,
    credits         SMALLINT NOT NULL,
    CONSTRAINT courses_name_not_blank
        CHECK (length(btrim(course_name)) > 0),
    CONSTRAINT courses_credits_valid
        CHECK (credits BETWEEN 1 AND 6),
    CONSTRAINT courses_instructor_fk
        FOREIGN KEY (instructor_id)
        REFERENCES instructors(instructor_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
);

-- ============================================================
-- Associative relation
--
-- The composite primary key expresses:
-- (student_id, course_id) -> grade
--
-- Student and course facts are stored in their own relations,
-- avoiding repeated values in every enrollment row.
-- ============================================================

CREATE TABLE enrollments (
    student_id      VARCHAR(20) NOT NULL,
    course_id       VARCHAR(20) NOT NULL,
    grade           CHAR(2),
    enrolled_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (student_id, course_id),

    CONSTRAINT enrollments_student_fk
        FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT enrollments_course_fk
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT enrollments_grade_valid
        CHECK (
            grade IS NULL
            OR grade IN ('A', 'A-', 'A+', 'B', 'B-', 'B+',
                         'C', 'C-', 'C+', 'D', 'D-', 'D+', 'F')
        )
);

CREATE INDEX idx_courses_instructor
    ON courses (instructor_id);

CREATE INDEX idx_enrollments_course
    ON enrollments (course_id);

-- ============================================================
-- Sample data
-- ============================================================

INSERT INTO students (student_id, student_name, email) VALUES
    ('S001', 'Asha Singh', 'asha@example.edu'),
    ('S002', 'Rahul Kumar', 'rahul@example.edu'),
    ('S003', 'Neha Sharma', 'neha@example.edu');

INSERT INTO instructors (instructor_id, instructor_name, email) VALUES
    ('I001', 'Dr. Mehta', 'mehta@example.edu'),
    ('I002', 'Dr. Rao', 'rao@example.edu');

INSERT INTO courses (course_id, course_name, instructor_id, credits) VALUES
    ('C101', 'Database Systems', 'I001', 4),
    ('C102', 'Operating Systems', 'I002', 4),
    ('C103', 'Data Structures', 'I001', 3);

INSERT INTO enrollments (student_id, course_id, grade) VALUES
    ('S001', 'C101', 'A'),
    ('S001', 'C102', 'B+'),
    ('S002', 'C101', 'A-'),
    ('S002', 'C103', 'B'),
    ('S003', 'C101', NULL);

-- ============================================================
-- Dependency-oriented views
-- ============================================================

CREATE VIEW student_course_facts AS
SELECT
    e.student_id,
    s.student_name,
    e.course_id,
    c.course_name,
    c.instructor_id,
    i.instructor_name,
    e.grade,
    e.enrolled_at
FROM enrollments e
JOIN students s
    ON s.student_id = e.student_id
JOIN courses c
    ON c.course_id = e.course_id
JOIN instructors i
    ON i.instructor_id = c.instructor_id;

-- ============================================================
-- Functional dependency checks
-- ============================================================

-- student_id -> student_name
SELECT
    student_id,
    COUNT(DISTINCT student_name) AS distinct_names
FROM students
GROUP BY student_id
HAVING COUNT(DISTINCT student_name) > 1;

-- course_id -> course_name, instructor_id
SELECT
    course_id,
    COUNT(DISTINCT course_name) AS distinct_course_names,
    COUNT(DISTINCT instructor_id) AS distinct_instructors
FROM courses
GROUP BY course_id
HAVING COUNT(DISTINCT course_name) > 1
    OR COUNT(DISTINCT instructor_id) > 1;

-- instructor_id -> instructor_name
SELECT
    instructor_id,
    COUNT(DISTINCT instructor_name) AS distinct_names
FROM instructors
GROUP BY instructor_id
HAVING COUNT(DISTINCT instructor_name) > 1;

-- (student_id, course_id) -> grade
SELECT
    student_id,
    course_id,
    COUNT(*) AS rows_for_key
FROM enrollments
GROUP BY student_id, course_id
HAVING COUNT(*) > 1;

-- ============================================================
-- Normalized reporting queries
-- ============================================================

SELECT
    student_id,
    student_name,
    COUNT(*) AS courses_taken,
    COUNT(grade) AS graded_courses
FROM student_course_facts
GROUP BY student_id, student_name
ORDER BY student_id;

SELECT
    course_id,
    course_name,
    instructor_name,
    COUNT(e.student_id) AS enrollment_count
FROM courses c
JOIN instructors i
    ON i.instructor_id = c.instructor_id
LEFT JOIN enrollments e
    ON e.course_id = c.course_id
GROUP BY
    course_id,
    course_name,
    instructor_name
ORDER BY course_id;

-- ============================================================
-- CTE: detect duplicated facts in a deliberately denormalized
-- representation.
-- ============================================================

WITH denormalized_example AS (
    SELECT
        e.student_id,
        s.student_name,
        e.course_id,
        c.course_name,
        c.instructor_id,
        i.instructor_name,
        e.grade
    FROM enrollments e
    JOIN students s
        ON s.student_id = e.student_id
    JOIN courses c
        ON c.course_id = e.course_id
    JOIN instructors i
        ON i.instructor_id = c.instructor_id
),
repetition AS (
    SELECT
        instructor_id,
        instructor_name,
        COUNT(*) AS repeated_rows
    FROM denormalized_example
    GROUP BY instructor_id, instructor_name
)
SELECT *
FROM repetition
WHERE repeated_rows > 1
ORDER BY instructor_id;

-- ============================================================
-- Transactional update
--
-- Instructor data is updated once in its owning relation.
-- Every course referencing the instructor observes the new value
-- through the foreign-key relationship and join.
-- ============================================================

BEGIN;

UPDATE instructors
SET instructor_name = 'Dr. Mehta-Singh'
WHERE instructor_id = 'I001';

COMMIT;

SELECT
    c.course_id,
    c.course_name,
    i.instructor_id,
    i.instructor_name
FROM courses c
JOIN instructors i
    ON i.instructor_id = c.instructor_id
WHERE i.instructor_id = 'I001'
ORDER BY c.course_id;

-- ============================================================
-- Savepoint demonstrates failure isolation.
-- ============================================================

BEGIN;

SAVEPOINT before_invalid_enrollment;

-- This statement intentionally violates the foreign key.
-- It is rolled back to the savepoint rather than aborting the
-- entire transaction.
DO $$
BEGIN
    BEGIN
        INSERT INTO enrollments (student_id, course_id, grade)
        VALUES ('S999', 'C101', 'A');
    EXCEPTION
        WHEN foreign_key_violation THEN
            RAISE NOTICE 'Rejected invalid student reference.';
            ROLLBACK TO SAVEPOINT before_invalid_enrollment;
    END;
END;
$$;

COMMIT;

-- ============================================================
-- Update anomaly demonstration
-- ============================================================

CREATE OR REPLACE VIEW anomaly_report AS
SELECT
    'Update anomaly avoided' AS anomaly_type,
    'Instructor name has one authoritative row.' AS explanation
UNION ALL
SELECT
    'Insertion anomaly avoided',
    'A course can exist before any student enrolls.'
UNION ALL
SELECT
    'Deletion anomaly avoided',
    'Deleting an enrollment does not delete course or instructor facts.';

SELECT *
FROM anomaly_report;

-- ============================================================
-- Normalization decomposition reference
--
-- Original conceptual relation:
--
-- EnrollmentRecord(
--   student_id,
--   student_name,
--   course_id,
--   course_name,
--   instructor_id,
--   instructor_name,
--   grade
-- )
--
-- Functional dependencies:
--   student_id -> student_name
--   course_id -> course_name, instructor_id
--   instructor_id -> instructor_name
--   student_id, course_id -> grade
--
-- Decomposition:
--   students(student_id, student_name, email)
--   instructors(instructor_id, instructor_name, email)
--   courses(course_id, course_name, instructor_id, credits)
--   enrollments(student_id, course_id, grade, enrolled_at)
--
-- The decomposition separates facts according to their determinants,
-- removes partial dependencies from the composite enrollment key,
-- and removes the transitive dependency
-- course_id -> instructor_id -> instructor_name.
-- ============================================================
