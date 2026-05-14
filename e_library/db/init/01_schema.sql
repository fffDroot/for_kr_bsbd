CREATE TABLE authors (
    id          SERIAL PRIMARY KEY,
    first_name  VARCHAR(100) NOT NULL,
    last_name   VARCHAR(100) NOT NULL,
    nationality VARCHAR(50),
    birth_year  INT,
    biography   TEXT
);

CREATE TABLE categories (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    parent_id        INT REFERENCES categories(id)
);

CREATE TABLE books (
    id               SERIAL PRIMARY KEY,
    title            VARCHAR(200) NOT NULL,
    author_id        INT NOT NULL REFERENCES authors(id),
    category_id      INT REFERENCES categories(id),
    isbn             VARCHAR(20),
    publication_year INT,
    pages            INT,
    description      TEXT
);

CREATE TABLE users (
    id                SERIAL PRIMARY KEY,
    username          VARCHAR(100) UNIQUE NOT NULL,
    email             VARCHAR(100),
    subscription_type VARCHAR(20) DEFAULT 'free',
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reading_sessions (
    id               SERIAL PRIMARY KEY,
    user_id          INT NOT NULL REFERENCES users(id),
    book_id          INT NOT NULL REFERENCES books(id),
    started_at       TIMESTAMP DEFAULT NOW(),
    last_read_at     TIMESTAMP,
    progress_percent NUMERIC(5,2) DEFAULT 0,
    is_completed     BOOLEAN DEFAULT FALSE
);

CREATE TABLE reviews (
    id         SERIAL PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES users(id),
    book_id    INT NOT NULL REFERENCES books(id),
    rating     INT CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bookmarks (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES users(id),
    book_id     INT NOT NULL REFERENCES books(id),
    page_number INT,
    created_at  TIMESTAMP DEFAULT NOW()
);