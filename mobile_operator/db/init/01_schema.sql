CREATE TABLE plans (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(100) NOT NULL,
    price             NUMERIC(8,2) NOT NULL,
    internet_gb       INT,
    calls_minutes     INT,
    sms_count         INT DEFAULT 0,
    roaming_included  BOOLEAN DEFAULT FALSE,
    has_extra_services BOOLEAN DEFAULT FALSE,
    description       TEXT
);

CREATE TABLE subscribers (
    id                SERIAL PRIMARY KEY,
    first_name        VARCHAR(50) NOT NULL,
    last_name         VARCHAR(50) NOT NULL,
    phone_number      VARCHAR(20) UNIQUE NOT NULL,
    plan_id           INT REFERENCES plans(id),
    registration_date DATE DEFAULT CURRENT_DATE,
    city              VARCHAR(50)
);

CREATE TABLE calls (
    id                  SERIAL PRIMARY KEY,
    caller_id           INT NOT NULL REFERENCES subscribers(id),
    callee_id           INT REFERENCES subscribers(id),
    callee_phone        VARCHAR(20),
    start_time          TIMESTAMP NOT NULL,
    duration_sec        INT NOT NULL,
    call_type           VARCHAR(20) DEFAULT 'local',
    destination_country VARCHAR(50)
);

CREATE TABLE sms_messages (
    id                  SERIAL PRIMARY KEY,
    sender_id           INT NOT NULL REFERENCES subscribers(id),
    receiver_id         INT REFERENCES subscribers(id),
    receiver_phone      VARCHAR(20),
    sent_at             TIMESTAMP DEFAULT NOW(),
    destination_country VARCHAR(50)
);

CREATE TABLE internet_usage (
    id             SERIAL PRIMARY KEY,
    subscriber_id  INT NOT NULL REFERENCES subscribers(id),
    usage_date     DATE NOT NULL,
    data_used_mb   INT NOT NULL
);

CREATE TABLE payments (
    id            SERIAL PRIMARY KEY,
    subscriber_id INT NOT NULL REFERENCES subscribers(id),
    amount        NUMERIC(10,2),
    payment_date  TIMESTAMP DEFAULT NOW(),
    description   VARCHAR(200)
);