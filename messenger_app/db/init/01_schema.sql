CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(50) UNIQUE NOT NULL,
    email       VARCHAR(100) UNIQUE,
    phone       VARCHAR(20),
    bio         TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    last_seen   TIMESTAMP
);

CREATE TABLE chats (
    id          SERIAL PRIMARY KEY,
    chat_type   VARCHAR(20) DEFAULT 'private',
    name        VARCHAR(200),
    created_at  TIMESTAMP DEFAULT NOW(),
    created_by  INT REFERENCES users(id)
);

CREATE TABLE chat_members (
    chat_id   INT NOT NULL REFERENCES chats(id),
    user_id   INT NOT NULL REFERENCES users(id),
    role      VARCHAR(20) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE messages (
    id                SERIAL PRIMARY KEY,
    chat_id           INT NOT NULL REFERENCES chats(id),
    sender_id         INT NOT NULL REFERENCES users(id),
    content           TEXT,
    sent_at           TIMESTAMP DEFAULT NOW(),
    is_read           BOOLEAN DEFAULT FALSE,
    is_deleted        BOOLEAN DEFAULT FALSE,
    parent_message_id INT REFERENCES messages(id)
);

CREATE TABLE attachments (
    id          SERIAL PRIMARY KEY,
    message_id  INT NOT NULL REFERENCES messages(id),
    file_type   VARCHAR(20),
    file_size   INT,
    file_name   VARCHAR(200)
);

CREATE TABLE contacts (
    user_id    INT NOT NULL REFERENCES users(id),
    contact_id INT NOT NULL REFERENCES users(id),
    added_at   TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, contact_id)
);

CREATE TABLE reactions (
    id         SERIAL PRIMARY KEY,
    message_id INT NOT NULL REFERENCES messages(id),
    user_id    INT NOT NULL REFERENCES users(id),
    emoji      VARCHAR(10),
    reacted_at TIMESTAMP DEFAULT NOW()
);
