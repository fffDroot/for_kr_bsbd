CREATE TABLE car_categories (
    id                       SERIAL PRIMARY KEY,
    name                     VARCHAR(50) NOT NULL,
    price_per_hour           NUMERIC(8,2),
    maintenance_km_threshold INT DEFAULT 20000
);

CREATE TABLE spawn_points (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(200),
    address   TEXT,
    lat       NUMERIC(10,7),
    lon       NUMERIC(10,7),
    city      VARCHAR(50) DEFAULT 'Москва'
);

CREATE TABLE cars (
    id               SERIAL PRIMARY KEY,
    brand            VARCHAR(50),
    model            VARCHAR(50),
    year             INT,
    category_id      INT REFERENCES car_categories(id),
    color            VARCHAR(30),
    license_plate    VARCHAR(15) UNIQUE,
    mileage          INT DEFAULT 0,
    spawn_point_id   INT REFERENCES spawn_points(id),
    status           VARCHAR(20) DEFAULT 'available'
);

CREATE TABLE customers (
    id              SERIAL PRIMARY KEY,
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    email           VARCHAR(100),
    phone           VARCHAR(20),
    license_number  VARCHAR(20) UNIQUE,
    birth_date      DATE
);

CREATE TABLE rentals (
    id             SERIAL PRIMARY KEY,
    customer_id    INT NOT NULL REFERENCES customers(id),
    car_id         INT NOT NULL REFERENCES cars(id),
    start_time     TIMESTAMP NOT NULL,
    end_time       TIMESTAMP,
    start_location TEXT,
    end_location   TEXT,
    total_price    NUMERIC(10,2),
    status         VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE accidents (
    id           SERIAL PRIMARY KEY,
    customer_id  INT NOT NULL REFERENCES customers(id),
    car_id       INT NOT NULL REFERENCES cars(id),
    rental_id    INT REFERENCES rentals(id),
    accident_date TIMESTAMP,
    location     TEXT NOT NULL,
    description  TEXT,
    fine_amount  NUMERIC(10,2) DEFAULT 0
);

CREATE TABLE maintenance_records (
    id          SERIAL PRIMARY KEY,
    car_id      INT NOT NULL REFERENCES cars(id),
    service_date DATE,
    description TEXT,
    cost        NUMERIC(10,2),
    mileage_at_service INT
);