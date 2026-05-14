CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE instructors (
    id         SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name  VARCHAR(50) NOT NULL,
    email      VARCHAR(100),
    bio        TEXT,
    expertise  VARCHAR(200)
);

CREATE TABLE courses (
    id             SERIAL PRIMARY KEY,
    title          VARCHAR(200) NOT NULL,
    category_id    INT REFERENCES categories(id),
    instructor_id  INT REFERENCES instructors(id),
    level          VARCHAR(20) DEFAULT 'beginner',
    duration_hours INT,
    price          NUMERIC(10,2) DEFAULT 0,
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE modules (
    id           SERIAL PRIMARY KEY,
    course_id    INT NOT NULL REFERENCES courses(id),
    title        VARCHAR(200),
    order_num    INT NOT NULL,
    duration_min INT
);

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(100) UNIQUE NOT NULL,
    email      VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE enrollments (
    id           SERIAL PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES users(id),
    course_id    INT NOT NULL REFERENCES courses(id),
    enrolled_at  TIMESTAMP DEFAULT NOW(),
    deadline     TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status       VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE module_progress (
    id           SERIAL PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES users(id),
    module_id    INT NOT NULL REFERENCES modules(id),
    completed_at TIMESTAMP,
    is_completed BOOLEAN DEFAULT FALSE
);
