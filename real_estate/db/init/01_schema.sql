CREATE TABLE property_types (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

CREATE TABLE properties (
    id           SERIAL PRIMARY KEY,
    type_id      INT NOT NULL REFERENCES property_types(id),
    address      TEXT NOT NULL,
    district     VARCHAR(100),
    city         VARCHAR(50) DEFAULT 'Москва',
    area_sqm     NUMERIC(8,2),
    rooms        INT,
    floor        INT,
    total_floors INT,
    lat          NUMERIC(10,7),
    lon          NUMERIC(10,7)
);

CREATE TABLE landlords (
    id         SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name  VARCHAR(50),
    email      VARCHAR(100),
    phone      VARCHAR(20),
    type       VARCHAR(20) DEFAULT 'individual'
);

CREATE TABLE clients (
    id         SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name  VARCHAR(50),
    email      VARCHAR(100),
    phone      VARCHAR(20)
);

CREATE TABLE listings (
    id            SERIAL PRIMARY KEY,
    property_id   INT NOT NULL REFERENCES properties(id),
    landlord_id   INT NOT NULL REFERENCES landlords(id),
    listing_type  VARCHAR(20) NOT NULL,
    price         NUMERIC(12,2),
    price_per_day NUMERIC(10,2),
    status        VARCHAR(20) DEFAULT 'active',
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE price_history (
    id          SERIAL PRIMARY KEY,
    listing_id  INT NOT NULL REFERENCES listings(id),
    old_price   NUMERIC(12,2),
    new_price   NUMERIC(12,2),
    changed_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE rentals (
    id           SERIAL PRIMARY KEY,
    listing_id   INT NOT NULL REFERENCES listings(id),
    client_id    INT NOT NULL REFERENCES clients(id),
    start_date   DATE NOT NULL,
    end_date     DATE NOT NULL,
    total_price  NUMERIC(12,2),
    status       VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE deals (
    id          SERIAL PRIMARY KEY,
    listing_id  INT NOT NULL REFERENCES listings(id),
    buyer_id    INT NOT NULL REFERENCES clients(id),
    deal_date   DATE,
    final_price NUMERIC(12,2)
);