DROP SCHEMA IF EXISTS normalization_demo CASCADE;
CREATE SCHEMA normalization_demo;

SET search_path TO normalization_demo;

-- The intentionally denormalized source relation combines facts with
-- different determinants. It is retained as a teaching representation.
CREATE TABLE enrollment_source (
    student_id       integer NOT NULL,
    student_name     text NOT NULL,
    course_id        integer NOT NULL,
    course_name      text NOT NULL,
    instructor_id    integer NOT NULL,
    instructor_name  text NOT NULL,
    grade            text,
    PRIMARY KEY (student_id, course_id),
    CHECK (student_id > 0),
    CHECK (course_id > 0),
    CHECK (instructor_id > 0),
    CHECK (grade IS NULL OR grade IN ('A', 'B', 'C', 'D', 'F'))
);

INSERT INTO enrollment_source
    (student_id, student_name, course_id, course_name,
     instructor_id, instructor_name, grade)
VALUES
    (1, 'Asha', 101, 'Database Systems', 7, 'Dr Rao', 'A'),
    (1, 'Asha', 102, 'Networks', 8, 'Dr Singh', 'B'),
    (2, 'Ravi', 101, 'Database Systems', 7, 'Dr Rao', 'A');

-- 1NF requires one atomic value per attribute. The following relation
-- intentionally shows what must be avoided.
CREATE TABLE one_nf_violation_example (
    student_id integer PRIMARY KEY,
    student_name text NOT NULL,
    phone_numbers text NOT NULL
);

INSERT INTO one_nf_violation_example
VALUES (1, 'Asha', '9000000001,9000000002');

-- 3NF decomposition:
-- Student facts depend on student_id.
CREATE TABLE student (
    student_id integer PRIMARY KEY,
    student_name text NOT NULL,
    CHECK (student_id > 0),
    CHECK (length(trim(student_name)) > 0)
);

-- Instructor facts depend on instructor_id.
CREATE TABLE instructor (
    instructor_id integer PRIMARY KEY,
    instructor_name text NOT NULL,
    CHECK (instructor_id > 0),
    CHECK (length(trim(instructor_name)) > 0)
);

-- Course facts depend on course_id. instructor_id is a foreign key,
-- rather than storing instructor_name repeatedly in every enrollment.
CREATE TABLE course (
    course_id integer PRIMARY KEY,
    course_name text NOT NULL,
    instructor_id integer NOT NULL
        REFERENCES instructor(instructor_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CHECK (course_id > 0),
    CHECK (length(trim(course_name)) > 0)
);

-- Enrollment contains facts that depend on the complete composite
-- relationship between a student and a course.
CREATE TABLE enrollment (
    student_id integer NOT NULL
        REFERENCES student(student_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    course_id integer NOT NULL
        REFERENCES course(course_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    grade text,
    enrolled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (student_id, course_id),
    CHECK (grade IS NULL OR grade IN ('A', 'B', 'C', 'D', 'F'))
);

INSERT INTO student (student_id, student_name)
VALUES
    (1, 'Asha'),
    (2, 'Ravi');

INSERT INTO instructor (instructor_id, instructor_name)
VALUES
    (7, 'Dr Rao'),
    (8, 'Dr Singh');

INSERT INTO course (course_id, course_name, instructor_id)
VALUES
    (101, 'Database Systems', 7),
    (102, 'Networks', 8);

INSERT INTO enrollment (student_id, course_id, grade)
VALUES
    (1, 101, 'A'),
    (1, 102, 'B'),
    (2, 101, 'A');

-- Explicit transaction demonstrates atomic insertion of related data.
BEGIN;

INSERT INTO student (student_id, student_name)
VALUES (3, 'Meera');

INSERT INTO enrollment (student_id, course_id, grade)
VALUES (3, 101, 'A');

COMMIT;

-- A duplicate enrollment violates the composite primary key.
-- It is deliberately represented as a failed transaction so that the
-- complete database remains valid when the script continues.
BEGIN;

SAVEPOINT duplicate_enrollment;

DO $$
BEGIN
    BEGIN
        INSERT INTO enrollment (student_id, course_id, grade)
        VALUES (1, 101, 'A');
    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE 'Duplicate enrollment rejected.';
    END;
END
$$;

ROLLBACK;

-- Indexes support common lookup paths rather than duplicating data.
CREATE INDEX idx_enrollment_course
    ON enrollment(course_id);

CREATE INDEX idx_course_instructor
    ON course(instructor_id);

-- A trigger prevents whitespace-only names if a future application
-- bypasses the same validation used by application services.
CREATE OR REPLACE FUNCTION reject_blank_student_name()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF length(trim(NEW.student_name)) = 0 THEN
        RAISE EXCEPTION 'student_name cannot be blank';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_student_nonblank_name
BEFORE INSERT OR UPDATE OF student_name
ON student
FOR EACH ROW
EXECUTE FUNCTION reject_blank_student_name();

-- View reconstructs a useful reporting projection without storing
-- transitive facts redundantly.
CREATE OR REPLACE VIEW enrollment_report AS
SELECT
    e.student_id,
    s.student_name,
    e.course_id,
    c.course_name,
    i.instructor_id,
    i.instructor_name,
    e.grade,
    e.enrolled_at
FROM enrollment e
JOIN student s
    ON s.student_id = e.student_id
JOIN course c
    ON c.course_id = e.course_id
JOIN instructor i
    ON i.instructor_id = c.instructor_id;

-- Functional-dependency inspection:
-- student_id -> student_name
SELECT
    student_id,
    count(DISTINCT student_name) AS distinct_names
FROM enrollment_source
GROUP BY student_id
HAVING count(DISTINCT student_name) > 1;

-- course_id -> course_name, instructor_id
SELECT
    course_id,
    count(DISTINCT course_name) AS distinct_course_names,
    count(DISTINCT instructor_id) AS distinct_instructors
FROM enrollment_source
GROUP BY course_id
HAVING count(DISTINCT course_name) > 1
    OR count(DISTINCT instructor_id) > 1;

-- instructor_id -> instructor_name
SELECT
    instructor_id,
    count(DISTINCT instructor_name) AS distinct_names
FROM enrollment_source
GROUP BY instructor_id
HAVING count(DISTINCT instructor_name) > 1;

-- Reporting query using the normalized model.
SELECT
    student_name,
    course_name,
    instructor_name,
    grade
FROM enrollment_report
ORDER BY student_id, course_id;

-- Aggregation over normalized facts.
SELECT
    c.course_id,
    c.course_name,
    count(e.student_id) AS enrollment_count
FROM course c
LEFT JOIN enrollment e
    ON e.course_id = c.course_id
GROUP BY c.course_id, c.course_name
ORDER BY c.course_id;

-- Eligibility query: students with all enrolled courses graded.
SELECT
    s.student_id,
    s.student_name
FROM student s
JOIN enrollment e
    ON e.student_id = s.student_id
GROUP BY s.student_id, s.student_name
HAVING count(*) = count(e.grade)
ORDER BY s.student_id;

-- CTE identifies the courses taught by each instructor and the number
-- of distinct students receiving those courses.
WITH instructor_course_load AS (
    SELECT
        i.instructor_id,
        i.instructor_name,
        c.course_id,
        c.course_name,
        count(e.student_id) AS student_count
    FROM instructor i
    JOIN course c
        ON c.instructor_id = i.instructor_id
    LEFT JOIN enrollment e
        ON e.course_id = c.course_id
    GROUP BY
        i.instructor_id,
        i.instructor_name,
        c.course_id,
        c.course_name
)
SELECT *
FROM instructor_course_load
ORDER BY instructor_id, course_id;

-- Demonstrate the update anomaly avoided by 3NF.
-- Changing an instructor name requires one row in instructor, not every
-- enrollment row associated with the instructor.
UPDATE instructor
SET instructor_name = 'Dr A. Rao'
WHERE instructor_id = 7;

SELECT *
FROM enrollment_report
WHERE instructor_id = 7
ORDER BY student_id, course_id;

-- Demonstrate deletion semantics:
-- deleting a student removes that student's relationship rows through
-- ON DELETE CASCADE, while deleting an instructor referenced by a course
-- is blocked by ON DELETE RESTRICT.
DELETE FROM student
WHERE student_id = 3;

SELECT *
FROM enrollment_report
ORDER BY student_id, course_id;

-- Validation query for possible orphan records. With foreign keys
-- enforced, this query should return zero rows.
SELECT e.*
FROM enrollment e
LEFT JOIN student s
    ON s.student_id = e.student_id
LEFT JOIN course c
    ON c.course_id = e.course_id
WHERE s.student_id IS NULL
   OR c.course_id IS NULL;
