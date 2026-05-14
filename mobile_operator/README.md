Отличный вариант! Переходим к мобильному оператору. В этой задаче реализована интересная логика с распределением звонков (домашние, роуминг, международные) и построением упрощенного графа связей между абонентами.

Я подготовил скрипт `seed.py` так, чтобы он гарантированно сгенерировал нужные тарифы для 1 и 9 запросов, абонентов из Москвы/Спб с нужными префиксами для 2 запроса и создал плотную сетку звонков внутри сети для 10 запроса.

Ниже представлено полное и готовое решение.

### 1. Структура проекта

Создай пустую папку (например, `mobile_operator`) и подготовь в ней следующую структуру:

```text
mobile_operator/
├── db/
│   └── init/
│       └── 01_schema.sql
├── api/
│   ├── __init__.py
│   ├── database.py
│   └── main.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
└── seed.py

```

---

### 2. Конфигурационные файлы

**Файл `.env**`

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=mobile_db

```

**Файл `requirements.txt**`

```txt
fastapi==0.115.*
uvicorn==0.34.*
sqlalchemy==2.0.*
psycopg2-binary==2.9.*
faker

```

**Файл `Dockerfile**`

```dockerfile
FROM bsbd/backend:2026

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

```

**Файл `docker-compose.yml**`

```yaml
version: "3.8"

services:
  db:
    image: postgres:15
    env_file:
      - .env
    volumes:
      - ./db/init:/docker-entrypoint-initdb.d:ro
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: "admin@admin.com"
      PGADMIN_DEFAULT_PASSWORD: "admin"
    ports:
      - "5050:80"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:

```

---

### 3. Схема БД и FastAPI Приложение

**Файл `db/init/01_schema.sql**`

```sql
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

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/mobile_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

```

**Файл `api/main.py**`

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Mobile Operator API")

@app.get("/")
def read_root():
    return {"message": "Mobile Operator API is running"}

@app.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, name, price FROM plans LIMIT 10")).mappings().all()
    return {"plans": result}

@app.get("/subscribers")
def get_subscribers(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, phone_number, city FROM subscribers LIMIT 10")).mappings().all()
    return {"subscribers": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

Я добавил генерацию специфических тарифов и абонентов, чтобы твои SQL-запросы выдавали красивые, непустые результаты.

**Файл `seed.py**`

```python
import os
import random
from datetime import datetime, timedelta, date
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker('ru_RU')

# --- НАСТРОЙКИ ---
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "mobile_db"
DB_USER = "postgres"
DB_PASS = "postgres"

NUM_PLANS = 20
NUM_SUBSCRIBERS = 1000
NUM_CALLS = 10000
NUM_SMS = 3000
NUM_INTERNET = 5000
NUM_PAYMENTS = 3000

COUNTRIES = ['Турция', 'Казахстан', 'Беларусь', 'ОАЭ', 'Армения', 'Грузия', 'Египет', 'Китай']
# -----------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных мобильного оператора...")

    # 1. Plans
    plans_data = []
    # Гарантируем тариф для Запроса 1
    plans_data.append(('Супер Безлимит', 900.00, None, None, 1000, False, False, 'Абсолютный безлимит за копейки'))
    # Гарантируем тариф для Запроса 9 (Топ-10 выгодных)
    plans_data.append(('Travel Basic', 500.00, None, 500, 100, True, False, 'Дешевый интернет в роуминге без лишнего'))
    plans_data.append(('Travel Pro', 800.00, None, 1000, 500, True, False, 'Отличный интернет в роуминге'))
    plans_data.append(('Travel VIP', 1500.00, None, 2000, 1000, True, False, 'Для долгих поездок'))

    for _ in range(NUM_PLANS - 4):
        price = round(random.uniform(200, 3000), 2)
        int_gb = random.choice([None, 5, 10, 30, 50])
        calls = random.choice([None, 200, 500, 1000, 2000])
        plans_data.append((
            f"Тариф {fake.word().capitalize()}", price, int_gb, calls, random.randint(0, 1000),
            random.choice([True, False]), random.choice([True, False]), fake.text(max_nb_chars=100)
        ))
    execute_values(cursor, "INSERT INTO plans (name, price, internet_gb, calls_minutes, sms_count, roaming_included, has_extra_services, description) VALUES %s", plans_data)
    cursor.execute("SELECT id FROM plans;")
    plan_ids = [row[0] for row in cursor.fetchall()]

    # 2. Subscribers
    subs_data = []
    # Для Запроса 2: Москва/Питер, 2023-2024 год, префиксы +7916 / +7985
    for _ in range(50):
        prefix = random.choice(['+7916', '+7985'])
        reg_date = fake.date_between(start_date=date(2023, 1, 1), end_date=date(2024, 12, 31))
        subs_data.append((
            fake.first_name(), fake.last_name(), f"{prefix}{fake.unique.numerify('#######')}",
            random.choice(plan_ids), reg_date, random.choice(['Москва', 'Санкт-Петербург'])
        ))

    for _ in range(NUM_SUBSCRIBERS - 50):
        subs_data.append((
            fake.first_name(), fake.last_name(), f"+79{fake.unique.numerify('########')}",
            random.choice(plan_ids), fake.date_between(start_date='-5y', end_date='today'), fake.city()
        ))
    execute_values(cursor, "INSERT INTO subscribers (first_name, last_name, phone_number, plan_id, registration_date, city) VALUES %s", subs_data)
    cursor.execute("SELECT id, phone_number FROM subscribers;")
    subs_records = cursor.fetchall()
    sub_ids = [s[0] for s in subs_records]

    # 3. Calls (10000: 70% local, 20% roaming, 10% int)
    calls_data = []
    for _ in range(NUM_CALLS):
        caller_id = random.choice(sub_ids)
        r = random.random()

        if r < 0.70: # Local (inside network)
            call_type = 'local'
            callee_id = random.choice(sub_ids)
            while callee_id == caller_id: callee_id = random.choice(sub_ids)
            callee_phone = None
            dest = 'Россия'
        elif r < 0.90: # Roaming
            call_type = 'roaming'
            callee_id = random.choice([random.choice(sub_ids), None])
            callee_phone = None if callee_id else f"+{fake.numerify('###########')}"
            dest = random.choice(COUNTRIES)
        else: # International
            call_type = 'international'
            callee_id = None
            callee_phone = f"+{fake.numerify('###########')}"
            dest = random.choice(COUNTRIES)

        dur = random.randint(10, 3600)
        start_time = fake.date_time_between(start_date='-2y', end_date='now')
        calls_data.append((caller_id, callee_id, callee_phone, start_time, dur, call_type, dest))

    execute_values(cursor, "INSERT INTO calls (caller_id, callee_id, callee_phone, start_time, duration_sec, call_type, destination_country) VALUES %s", calls_data)

    # 4. SMS
    sms_data = []
    for _ in range(NUM_SMS):
        sender = random.choice(sub_ids)
        if random.random() < 0.8:
            recv_id = random.choice(sub_ids)
            recv_phone, dest = None, 'Россия'
        else:
            recv_id = None
            recv_phone = f"+{fake.numerify('###########')}"
            dest = random.choice(COUNTRIES)

        sms_data.append((sender, recv_id, recv_phone, fake.date_time_between(start_date='-2y', end_date='now'), dest))
    execute_values(cursor, "INSERT INTO sms_messages (sender_id, receiver_id, receiver_phone, sent_at, destination_country) VALUES %s", sms_data)

    # 5. Internet Usage
    net_data = []
    for _ in range(NUM_INTERNET):
        net_data.append((random.choice(sub_ids), fake.date_between(start_date='-2y', end_date='today'), random.randint(10, 5000)))
    execute_values(cursor, "INSERT INTO internet_usage (subscriber_id, usage_date, data_used_mb) VALUES %s", net_data)

    # 6. Payments
    pay_data = []
    for _ in range(NUM_PAYMENTS):
        pay_data.append((random.choice(sub_ids), round(random.uniform(100, 2000), 2), fake.date_time_between(start_date='-2y', end_date='now'), 'Оплата по тарифу'))
    execute_values(cursor, "INSERT INTO payments (subscriber_id, amount, payment_date, description) VALUES %s", pay_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных успешно завершена!")

if __name__ == "__main__":
    seed_data()

```

---

### 5. Инструкция по запуску

1. Запусти контейнеры (со сборкой образа) в терминале:
```bash
docker compose up -d --build

```


2. Зайди внутрь контейнера с приложением:
```bash
docker compose exec app bash

```


3. Сгенерируй данные:
```bash
python seed.py

```


4. Выйди из контейнера командой `exit`.
5. Доступ:
* База (pgAdmin): `http://localhost:5050` (почта `admin@admin.com`, пароль `admin`). Хост `db`, логин/пароль `postgres`, БД `mobile_db`.
* API: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести все тарифы с безлимитным интернетом и безлимитными звонками, стоимостью не более 1 000 руб./мес. Отсортировать по цене по возрастанию.
**Конструкции:** `WHERE`, `IS NULL`, `AND`, `<=`, `ORDER BY`
**Запрос:**

```sql
SELECT name, price, description
FROM plans
WHERE internet_gb IS NULL
  AND calls_minutes IS NULL
  AND price <= 1000
ORDER BY price ASC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести всех абонентов из городов 'Москва' или 'Санкт-Петербург', зарегистрировавшихся в 2023 или 2024 году, чей номер телефона начинается на +7916 или +7985. Отсортировать по городу, затем по фамилии.
**Конструкции:** `WHERE`, `IN`, `AND`, `LIKE`, `OR`, `EXTRACT`, `ORDER BY`
**Запрос:**

```sql
SELECT first_name, last_name, phone_number, city, registration_date
FROM subscribers
WHERE city IN ('Москва', 'Санкт-Петербург')
  AND EXTRACT(YEAR FROM registration_date) IN (2023, 2024)
  AND (phone_number LIKE '+7916%' OR phone_number LIKE '+7985%')
ORDER BY city ASC, last_name ASC;

```

---

**Запрос 3 — GROUP BY**
Для каждого тарифа посчитать: количество подключённых абонентов, суммарный доход с тарифа (количество абонентов × цена тарифа), среднее количество звонков на абонента. Отсортировать по доходу по убыванию.
**Конструкции:** `JOIN`, `GROUP BY`, `COUNT`, `SUM`, `AVG`, `ROUND`
**Запрос:**

```sql
SELECT p.name AS plan_name,
       COUNT(DISTINCT s.id) AS subscribers_count,
       SUM(p.price) AS total_revenue,
       ROUND(COUNT(c.id) * 1.0 / NULLIF(COUNT(DISTINCT s.id), 0), 2) AS avg_calls_per_sub
FROM plans p
LEFT JOIN subscribers s ON p.id = s.plan_id
LEFT JOIN calls c ON s.id = c.caller_id
GROUP BY p.id, p.name
ORDER BY total_revenue DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти абонентов, которые совершили более 30 звонков за весь период и у которых средняя продолжительность звонка более 3 минут (180 сек.). Вывести: имя и фамилию, номер телефона, количество звонков, среднее время (в минутах, 2 знака).
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `COUNT`, `AVG`, `ROUND`
**Запрос:**

```sql
SELECT s.first_name,
       s.last_name,
       s.phone_number,
       COUNT(c.id) AS total_calls,
       ROUND(AVG(c.duration_sec) / 60.0, 2) AS avg_duration_min
FROM subscribers s
JOIN calls c ON s.id = c.caller_id
GROUP BY s.id, s.first_name, s.last_name, s.phone_number
HAVING COUNT(c.id) > 30 AND AVG(c.duration_sec) > 180
ORDER BY avg_duration_min DESC;

```

---

**Запрос 5 — INNER JOIN**
Вывести список международных звонков с полями: имя и фамилия звонящего, его тариф, страна назначения, длительность (в минутах), дата звонка. Отсортировать по дате по убыванию.
**Конструкции:** `INNER JOIN`, `ORDER BY`
**Запрос:**

```sql
SELECT s.first_name || ' ' || s.last_name AS caller_name,
       p.name AS plan_name,
       c.destination_country,
       ROUND(c.duration_sec / 60.0, 2) AS duration_min,
       c.start_time
FROM calls c
INNER JOIN subscribers s ON c.caller_id = s.id
INNER JOIN plans p ON s.plan_id = p.id
WHERE c.call_type = 'international'
ORDER BY c.start_time DESC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести все тарифы с количеством абонентов на каждом. Включить тарифы без единого абонента. Отсортировать по количеству абонентов по убыванию.
**Конструкции:** `LEFT JOIN`, `COUNT`, `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT p.id,
       p.name,
       COUNT(s.id) AS subscribers_count
FROM plans p
LEFT JOIN subscribers s ON p.id = s.plan_id
GROUP BY p.id, p.name
ORDER BY subscribers_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести всех абонентов с суммой их платежей и суммарным потреблением интернета в МБ (если интернет не использовался — 0).
**Конструкции:** `INNER JOIN`, `LEFT JOIN`, `GROUP BY`, `SUM`, `COALESCE`
**Запрос:**

```sql
SELECT s.id,
       s.first_name,
       s.last_name,
       SUM(p.amount) AS total_payments,
       COALESCE(SUM(i.data_used_mb), 0) AS total_internet_mb
FROM subscribers s
INNER JOIN payments p ON s.id = p.subscriber_id
LEFT JOIN internet_usage i ON s.id = i.subscriber_id
GROUP BY s.id, s.first_name, s.last_name
ORDER BY total_payments DESC;

```

---

**Запрос 8 — UNION**
Создать единый журнал коммуникаций абонента с `subscriber_id = 1` (Звонки и SMS). Объединить, отсортировать по дате.
**Конструкции:** `UNION`, `COALESCE`, `WHERE`, `ORDER BY`
**Запрос:**

```sql
SELECT start_time AS event_date,
       'Звонок' AS communication_type,
       COALESCE(destination_country, 'Россия') AS country,
       duration_sec
FROM calls
WHERE caller_id = 1
UNION
SELECT sent_at AS event_date,
       'SMS' AS communication_type,
       COALESCE(destination_country, 'Россия') AS country,
       NULL AS duration_sec
FROM sms_messages
WHERE sender_id = 1
ORDER BY event_date DESC;

```

---

**Запрос 9 — Комплексный SELECT №1 ⭐**
Найти топ-10 самых выгодных тарифов для абонента, которому нужно: безлимитный интернет, звонки в роуминге, без дополнительных услуг. Из подходящих вывести топ-10 по наименьшей цене.
**Конструкции:** `WHERE` (3 условия), `ORDER BY`, `LIMIT`
**Запрос:**

```sql
SELECT name,
       price,
       description
FROM plans
WHERE internet_gb IS NULL
  AND roaming_included = TRUE
  AND has_extra_services = FALSE
ORDER BY price ASC
LIMIT 10;

```

---

**Запрос 10 — Комплексный SELECT №2 ⭐**

**10а. Топ-10 абонентов по продолжительности международных звонков.**
**Запрос 10а:**

```sql
SELECT s.first_name || ' ' || s.last_name AS full_name,
       p.name AS plan_name,
       ROUND(SUM(c.duration_sec) / 60.0, 2) AS total_international_min
FROM subscribers s
JOIN plans p ON s.plan_id = p.id
JOIN calls c ON s.id = c.caller_id
WHERE c.call_type = 'international'
GROUP BY s.id, full_name, plan_name
ORDER BY total_international_min DESC
LIMIT 10;

```

**10б. "Лидеры мнений" (наибольшее количество уникальных собеседников внутри сети).**
*(Используем CTE с UNION, чтобы объединить тех, кому звонил абонент, и тех, кто звонил ему).*
**Запрос 10б:**

```sql
WITH network_contacts AS (
    SELECT caller_id AS sub_id, callee_id AS contact_id
    FROM calls WHERE callee_id IS NOT NULL
    UNION
    SELECT callee_id AS sub_id, caller_id AS contact_id
    FROM calls WHERE callee_id IS NOT NULL
)
SELECT s.first_name || ' ' || s.last_name AS full_name,
       s.phone_number,
       COUNT(DISTINCT nc.contact_id) AS unique_contacts
FROM subscribers s
JOIN network_contacts nc ON s.id = nc.sub_id
GROUP BY s.id, full_name, s.phone_number
ORDER BY unique_contacts DESC
LIMIT 10;

```