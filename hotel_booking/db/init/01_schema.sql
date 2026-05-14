CREATE TABLE hotels (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    city      VARCHAR(50)  NOT NULL,
    address   TEXT,
    stars     INT CHECK (stars BETWEEN 1 AND 5),
    phone     VARCHAR(20),
    email     VARCHAR(100)
);

CREATE TABLE rooms (
    id               SERIAL PRIMARY KEY,
    hotel_id         INT NOT NULL REFERENCES hotels(id),
    room_number      VARCHAR(10),
    room_type        VARCHAR(50),
    capacity         INT DEFAULT 2,
    price_per_night  NUMERIC(10,2) NOT NULL,
    is_available     BOOLEAN DEFAULT TRUE
);

CREATE TABLE customers (
    id              SERIAL PRIMARY KEY,
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    email           VARCHAR(100) UNIQUE,
    phone           VARCHAR(20),
    birth_date      DATE,
    passport_number VARCHAR(20)
);

CREATE TABLE bookings (
    id             SERIAL PRIMARY KEY,
    customer_id    INT NOT NULL REFERENCES customers(id),
    room_id        INT NOT NULL REFERENCES rooms(id),
    check_in_date  DATE NOT NULL,
    check_out_date DATE NOT NULL,
    total_price    NUMERIC(10,2),
    status         VARCHAR(20) DEFAULT 'pending',
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reviews (
    id          SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    hotel_id    INT NOT NULL REFERENCES hotels(id),
    rating      INT CHECK (rating BETWEEN 1 AND 5),
    comment     TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE amenities (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(100),
    category VARCHAR(50)
);

CREATE TABLE room_amenities (
    room_id    INT REFERENCES rooms(id),
    amenity_id INT REFERENCES amenities(id),
    PRIMARY KEY (room_id, amenity_id)
);
