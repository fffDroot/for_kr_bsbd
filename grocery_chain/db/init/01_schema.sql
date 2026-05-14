CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE suppliers (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(200) NOT NULL,
    city    VARCHAR(50),
    contact VARCHAR(100)
);

CREATE TABLE stores (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(200) NOT NULL,
    address  TEXT,
    city     VARCHAR(50) DEFAULT 'Москва',
    district VARCHAR(100)
);

CREATE TABLE products (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    category_id  INT REFERENCES categories(id),
    supplier_id  INT REFERENCES suppliers(id),
    price        NUMERIC(10,2) NOT NULL,
    unit         VARCHAR(20) DEFAULT 'шт',
    shelf_life_days INT
);

CREATE TABLE inventory (
    id               SERIAL PRIMARY KEY,
    store_id         INT NOT NULL REFERENCES stores(id),
    product_id       INT NOT NULL REFERENCES products(id),
    quantity         INT DEFAULT 0,
    received_date    DATE NOT NULL,
    expiry_date      DATE NOT NULL,
    last_sold_date   DATE
);

CREATE TABLE sales (
    id            SERIAL PRIMARY KEY,
    store_id      INT NOT NULL REFERENCES stores(id),
    product_id    INT NOT NULL REFERENCES products(id),
    quantity      INT NOT NULL,
    sale_date     DATE NOT NULL,
    price_at_sale NUMERIC(10,2) NOT NULL,
    season        VARCHAR(10) NOT NULL
);

CREATE TABLE price_history (
    id          SERIAL PRIMARY KEY,
    product_id  INT NOT NULL REFERENCES products(id),
    store_id    INT NOT NULL REFERENCES stores(id),
    old_price   NUMERIC(10,2),
    new_price   NUMERIC(10,2),
    changed_at  TIMESTAMP DEFAULT NOW()
);