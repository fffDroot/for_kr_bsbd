CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE specialists (
    id               SERIAL PRIMARY KEY,
    first_name       VARCHAR(50) NOT NULL,
    last_name        VARCHAR(50) NOT NULL,
    city             VARCHAR(50) DEFAULT 'Москва',
    district         VARCHAR(100),
    category_id      INT REFERENCES categories(id),
    rating           NUMERIC(3,2) DEFAULT 5.00,
    experience_years INT DEFAULT 0,
    phone            VARCHAR(20),  -- Добавлено для Запроса 8
    bio              TEXT,
    is_active        BOOLEAN DEFAULT TRUE
);

CREATE TABLE customers (
    id         SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name  VARCHAR(50) NOT NULL,
    email      VARCHAR(100),
    phone      VARCHAR(20),
    city       VARCHAR(50) DEFAULT 'Москва'
);

CREATE TABLE orders (
    id             SERIAL PRIMARY KEY,
    customer_id    INT NOT NULL REFERENCES customers(id),
    specialist_id  INT NOT NULL REFERENCES specialists(id),
    category_id    INT NOT NULL REFERENCES categories(id),
    status         VARCHAR(20) DEFAULT 'new',
    created_at     TIMESTAMP DEFAULT NOW(),
    completed_at   TIMESTAMP,
    price          NUMERIC(10,2)
);

CREATE TABLE reviews (
    id            SERIAL PRIMARY KEY,
    customer_id   INT NOT NULL REFERENCES customers(id),
    specialist_id INT NOT NULL REFERENCES specialists(id),
    order_id      INT REFERENCES orders(id),
    rating        NUMERIC(3,2) CHECK (rating BETWEEN 1 AND 5),
    comment       TEXT,
    created_at    TIMESTAMP DEFAULT NOW()
);
