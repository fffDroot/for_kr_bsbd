CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE content (
    id            SERIAL PRIMARY KEY,
    title         VARCHAR(200) NOT NULL,
    category_id   INT REFERENCES categories(id),
    content_type  VARCHAR(10) CHECK (content_type IN ('movie', 'series')),
    release_year  INT,
    duration_min  INT,
    description   TEXT
);

CREATE TABLE episodes (
    id            SERIAL PRIMARY KEY,
    content_id    INT NOT NULL REFERENCES content(id),
    season_num    INT NOT NULL,
    episode_num   INT NOT NULL,
    title         VARCHAR(200),
    duration_min  INT,
    release_date  DATE
);

CREATE TABLE users (
    id                SERIAL PRIMARY KEY,
    username          VARCHAR(100) UNIQUE NOT NULL,
    email             VARCHAR(100) UNIQUE,
    subscription_type VARCHAR(20) DEFAULT 'free',
    country           VARCHAR(50),
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE viewings (
    id                 SERIAL PRIMARY KEY,
    user_id            INT NOT NULL REFERENCES users(id),
    content_id         INT NOT NULL REFERENCES content(id),
    episode_id         INT REFERENCES episodes(id),
    viewed_at          TIMESTAMP DEFAULT NOW(),
    watch_duration_min INT,
    is_completed       BOOLEAN DEFAULT FALSE
);

CREATE TABLE ratings (
    id         SERIAL PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES users(id),
    content_id INT NOT NULL REFERENCES content(id),
    score      NUMERIC(3,1) CHECK (score BETWEEN 1 AND 10),
    rated_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE comments (
    id           SERIAL PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES users(id),
    content_id   INT NOT NULL REFERENCES content(id),
    comment_text TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);
