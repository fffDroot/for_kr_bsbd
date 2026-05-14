CREATE TABLE schools (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    address     TEXT,
    district    VARCHAR(100),
    phone       VARCHAR(20),
    principal   VARCHAR(150)
);

CREATE TABLE teachers (
    id               SERIAL PRIMARY KEY,
    first_name       VARCHAR(50) NOT NULL,
    last_name        VARCHAR(50) NOT NULL,
    patronymic       VARCHAR(50),
    school_id        INT REFERENCES schools(id),
    subject          VARCHAR(100),
    experience_years INT DEFAULT 0
);

CREATE TABLE classes (
    id                  SERIAL PRIMARY KEY,
    school_id           INT NOT NULL REFERENCES schools(id),
    grade               INT CHECK (grade BETWEEN 1 AND 11),
    letter              CHAR(1),
    academic_year       VARCHAR(10),
    homeroom_teacher_id INT REFERENCES teachers(id)
);

CREATE TABLE students (
    id           SERIAL PRIMARY KEY,
    class_id     INT NOT NULL REFERENCES classes(id),
    first_name   VARCHAR(50) NOT NULL,
    last_name    VARCHAR(50) NOT NULL,
    patronymic   VARCHAR(50),
    birth_date   DATE,
    parent_phone VARCHAR(20)
);

CREATE TABLE subjects (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE grades (
    id          SERIAL PRIMARY KEY,
    student_id  INT NOT NULL REFERENCES students(id),
    subject_id  INT NOT NULL REFERENCES subjects(id),
    teacher_id  INT NOT NULL REFERENCES teachers(id),
    value       INT CHECK (value BETWEEN 1 AND 5),
    grade_date  DATE NOT NULL,
    grade_type  VARCHAR(50)
);

CREATE TABLE attendance (
    id         SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(id),
    class_id   INT NOT NULL REFERENCES classes(id),
    att_date   DATE NOT NULL,
    is_present BOOLEAN DEFAULT TRUE,
    reason     VARCHAR(200)
);
