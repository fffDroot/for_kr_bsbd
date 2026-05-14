### 1. Структура проекта

Создай пустую папку для проекта и повтори в ней следующую структуру файлов:

```text
hotel_booking/
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

### 2. Конфигурационные файлы (Корень проекта)

**Файл `.env**`

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=hotel_db

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

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь исходный код проекта
COPY . .

EXPOSE 8000

# Запуск с флагом --reload для горячей перезагрузки при изменении кода
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

```

**Файл `docker-compose.yml**`

```yaml
version: "3.8"

services:
  db:
    image: postgres:16
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

### 3. База данных и Приложение

**Файл `db/init/01_schema.sql**`

```sql
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

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/hotel_db"
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

app = FastAPI(title="Hotel Booking API")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API is running"}

@app.get("/hotels")
def get_hotels(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, name, city, stars FROM hotels LIMIT 10")).mappings().all()
    return {"hotels": result}

@app.get("/bookings")
def get_bookings(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, check_in_date, check_out_date, status FROM bookings LIMIT 10")).mappings().all()
    return {"bookings": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

*Обрати внимание: так как мы будем запускать скрипт внутри контейнера `app`, переменная `DB_HOST` теперь равна `"db"` — это имя сервиса базы данных во внутренней сети Docker.*

**Файл `seed.py**`

```python
import os
import random
from datetime import date, timedelta
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker('ru_RU')

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К БД ---
# Внутри контейнера app база данных доступна по имени сервиса 'db'
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "hotel_db"
DB_USER = "postgres"
DB_PASS = "postgres"

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ГЕНЕРАЦИИ ---
NUM_HOTELS = 50
HOTEL_MIN_STARS = 1
HOTEL_MAX_STARS = 5

NUM_ROOMS_TARGET = 300
ROOMS_PER_HOTEL_MIN = 4
ROOMS_PER_HOTEL_MAX = 8
ROOM_PRICE_MIN = 1500.0
ROOM_PRICE_MAX = 25000.0

NUM_CUSTOMERS = 1000

NUM_BOOKINGS = 10000
BOOKING_DATE_START = date(2023, 1, 1)
BOOKING_DATE_END = date(2026, 12, 31)

NUM_REVIEWS = 2000

AMENITIES_PER_ROOM_MIN = 2
AMENITIES_PER_ROOM_MAX = 5
# --------------------------------------

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Начинаем генерацию данных...")

    # 1. Amenities
    amenities_data = [
        ('WiFi', 'Сервис'), ('Бассейн', 'Спорт'), ('Завтрак', 'Питание'), ('Спа', 'Сервис'),
        ('Спортзал', 'Спорт'), ('Парковка', 'Сервис'), ('Трансфер', 'Сервис'),
        ('Мини-бар', 'Питание'), ('Кондиционер', 'Сервис'), ('Детская комната', 'Развлечения'),
        ('Бильярд', 'Развлечения'), ('Шведский стол', 'Питание'), ('Теннисный корт', 'Спорт'),
        ('Массаж', 'Сервис'), ('Анимация', 'Развлечения'), ('Сейф', 'Сервис'),
        ('Услуги прачечной', 'Сервис'), ('Ресторан', 'Питание'), ('Бар', 'Питание'), ('Экскурсии', 'Развлечения')
    ]
    execute_values(cursor, "INSERT INTO amenities (name, category) VALUES %s", amenities_data)

    # 2. Hotels
    hotels_data = [
        (fake.company()[:100], fake.city()[:50], fake.address(),
         random.randint(HOTEL_MIN_STARS, HOTEL_MAX_STARS), fake.phone_number()[:20], fake.email()[:100])
        for _ in range(NUM_HOTELS)
    ]
    execute_values(cursor, "INSERT INTO hotels (name, city, address, stars, phone, email) VALUES %s", hotels_data)
    print(f"Сгенерировано отелей: {NUM_HOTELS}")

    # 3. Rooms
    cursor.execute("SELECT id FROM hotels;")
    hotel_ids = [row[0] for row in cursor.fetchall()]
    room_types = ['Стандарт', 'Улучшенный', 'Люкс', 'Полулюкс']
    rooms_data = []

    room_counter = 1
    for hotel_id in hotel_ids:
        num_rooms = random.randint(ROOMS_PER_HOTEL_MIN, ROOMS_PER_HOTEL_MAX)
        for _ in range(num_rooms):
            rooms_data.append((
                hotel_id, str(random.randint(100, 999)), random.choice(room_types),
                random.randint(1, 4), round(random.uniform(ROOM_PRICE_MIN, ROOM_PRICE_MAX), 2), True
            ))
            room_counter += 1
            if room_counter > NUM_ROOMS_TARGET: break
        if room_counter > NUM_ROOMS_TARGET: break

    execute_values(cursor, "INSERT INTO rooms (hotel_id, room_number, room_type, capacity, price_per_night, is_available) VALUES %s", rooms_data)
    print(f"Сгенерировано номеров: {len(rooms_data)}")

    # 4. Customers
    customers_data = [
        (fake.first_name()[:50], fake.last_name()[:50], fake.unique.email()[:100],
         fake.phone_number()[:20], fake.date_of_birth(minimum_age=18, maximum_age=80), fake.bothify(text='??######')[:20])
        for _ in range(NUM_CUSTOMERS)
    ]
    execute_values(cursor, "INSERT INTO customers (first_name, last_name, email, phone, birth_date, passport_number) VALUES %s", customers_data)
    print(f"Сгенерировано клиентов: {NUM_CUSTOMERS}")

    # 5. Bookings
    cursor.execute("SELECT id FROM customers;")
    customer_ids = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT id, price_per_night FROM rooms;")
    rooms = cursor.fetchall()

    statuses = ['pending', 'confirmed', 'completed', 'cancelled']
    bookings_data = []
    customers_with_bookings = set()

    for _ in range(NUM_BOOKINGS):
        c_id = random.choice(customer_ids)
        r_id, price = random.choice(rooms)
        check_in = fake.date_between_dates(date_start=BOOKING_DATE_START, date_end=BOOKING_DATE_END)
        nights = random.randint(1, 14)
        check_out = check_in + timedelta(days=nights)
        total_price = float(price) * nights
        status = random.choice(statuses)

        bookings_data.append((c_id, r_id, check_in, check_out, total_price, status))
        customers_with_bookings.add((c_id, r_id))

    execute_values(cursor, "INSERT INTO bookings (customer_id, room_id, check_in_date, check_out_date, total_price, status) VALUES %s", bookings_data)
    print(f"Сгенерировано бронирований: {NUM_BOOKINGS}")

    # 6. Reviews
    cursor.execute("SELECT id, hotel_id FROM rooms;")
    room_hotel_map = {row[0]: row[1] for row in cursor.fetchall()}
    reviews_data = []
    valid_reviewers = list(customers_with_bookings)
    actual_reviews_count = min(NUM_REVIEWS, len(valid_reviewers))

    for _ in range(actual_reviews_count):
        if not valid_reviewers: break
        c_id, r_id = random.choice(valid_reviewers)
        hotel_id = room_hotel_map[r_id]
        reviews_data.append((c_id, hotel_id, random.randint(1, 5), fake.text(max_nb_chars=200)))

    execute_values(cursor, "INSERT INTO reviews (customer_id, hotel_id, rating, comment) VALUES %s", reviews_data)
    print(f"Сгенерировано отзывов: {actual_reviews_count}")

    # 7. Room Amenities
    cursor.execute("SELECT id FROM amenities;")
    amenity_ids = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT id FROM rooms;")
    room_ids = [row[0] for row in cursor.fetchall()]

    room_amenities_data = []
    for r_id in room_ids:
        k = random.randint(AMENITIES_PER_ROOM_MIN, AMENITIES_PER_ROOM_MAX)
        chosen_amenities = random.sample(amenity_ids, k)
        for a_id in chosen_amenities:
            room_amenities_data.append((r_id, a_id))

    execute_values(cursor, "INSERT INTO room_amenities (room_id, amenity_id) VALUES %s", room_amenities_data)
    print(f"Связей удобств с номерами добавлено: {len(room_amenities_data)}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных успешно завершена!")

if __name__ == "__main__":
    seed_data()

```

---

### 5. Инструкция по запуску (включая вход в контейнер `app`)

1. **Запусти контейнеры (со сборкой образа):**
Открой терминал в корневой папке проекта на твоей Ubuntu и выполни:
```bash
docker compose up -d --build

```


*Docker скачает образы, создаст сеть, поднимет базу данных, выполнит `01_schema.sql`, соберет образ для FastAPI и запустит pgAdmin.*
2. **Зайди внутрь контейнера `app` для генерации данных:**
Поскольку зависимости (Faker, psycopg2) и сам скрипт `seed.py` уже лежат внутри контейнера приложения, мы просто провалимся в его shell:
```bash
docker compose exec app bash

```

Ты увидишь, что строка приглашения изменилась (ты находишься в директории `/app` внутри контейнера).
3. **Запусти скрипт наполнения:**
Находясь внутри контейнера, выполни:
```bash
python seed.py

```

*Дождись сообщения «Генерация данных успешно завершена!» (обычно занимает 2–5 секунд).*
4. **Выйди из контейнера:**
Выполни команду `exit` или нажми `Ctrl+D`, чтобы вернуться в свой локальный терминал.
5. **Проверка работоспособности:**
* **API:** Перейди по ссылке `http://localhost:8000/docs` — там должен быть доступен Swagger UI.
* **БД:** Перейди по ссылке `http://localhost:5050` (pgAdmin). Логин `admin@admin.com`, пароль `admin`. Подключи новый сервер: хост `db`, юзер `postgres`, пароль `postgres`. Там ты увидишь свои таблицы с тысячами строк.



---

### 6. DQL-запросы (10 штук) для вставки в отчет

---

**Запрос 1 — Базовый SELECT**
Вывести все номера с типом 'Люкс' или 'Полулюкс', доступные для бронирования (`is_available = TRUE`), с ценой не выше 12 000 руб./ночь. Номер комнаты должен содержать цифру '1'. Отсортировать по цене по убыванию.
**Конструкции:** `WHERE`, `OR`, `AND`, `<=`, `LIKE`, `ORDER BY DESC`
**Запрос:**

```sql
SELECT room_number, room_type, price_per_night
FROM rooms
WHERE (room_type = 'Люкс' OR room_type = 'Полулюкс')
  AND is_available = TRUE
  AND price_per_night <= 12000
  AND room_number LIKE '%1%'
ORDER BY price_per_night DESC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести все бронирования, статус которых не 'cancelled' и не 'rejected', с датой заезда в периоде 01.04.2025 — 30.09.2025 и стоимостью от 8 000 до 60 000 руб. Отсортировать по дате заезда, затем по стоимости по убыванию.
**Конструкции:** `WHERE`, `NOT IN`, `BETWEEN`, `AND`, `ORDER BY`
**Запрос:**

```sql
SELECT * FROM bookings
WHERE status NOT IN ('cancelled', 'rejected')
  AND check_in_date BETWEEN '2025-04-01' AND '2025-09-30'
  AND total_price BETWEEN 8000 AND 60000
ORDER BY check_in_date ASC, total_price DESC;

```

---

**Запрос 3 — GROUP BY**
Для каждого типа номера вычислить: количество номеров, среднюю цену за ночь (2 знака), минимальную и максимальную цену. Отсортировать по средней цене по убыванию.
**Конструкции:** `GROUP BY`, `COUNT`, `AVG`, `MIN`, `MAX`, `ROUND`
**Запрос:**

```sql
SELECT room_type,
       COUNT(*) AS rooms_count,
       ROUND(AVG(price_per_night), 2) AS avg_price,
       MIN(price_per_night) AS min_price,
       MAX(price_per_night) AS max_price
FROM rooms
GROUP BY room_type
ORDER BY avg_price DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти отели, у которых средний рейтинг отзывов выше 4.0 и количество отзывов не менее 5. Вывести: id отеля, средний рейтинг (2 знака), количество отзывов. Отсортировать по среднему рейтингу по убыванию.
**Конструкции:** `GROUP BY`, `HAVING`, `AVG`, `COUNT`, `ROUND`
**Запрос:**

```sql
SELECT hotel_id,
       ROUND(AVG(rating), 2) AS avg_rating,
       COUNT(*) AS review_count
FROM reviews
GROUP BY hotel_id
HAVING AVG(rating) > 4.0 AND COUNT(*) >= 5
ORDER BY avg_rating DESC;

```

---

**Запрос 5 — INNER JOIN**
Вывести список отзывов с полями: полное имя клиента (`first_name || ' ' || last_name`), название отеля, рейтинг, дата отзыва. Показывать только отзывы с рейтингом ≥ 4. Отсортировать по рейтингу по убыванию, затем по названию отеля.
**Конструкции:** `INNER JOIN` (таблицы: `reviews`, `customers`, `hotels`), `WHERE`, `ORDER BY`
**Запрос:**

```sql
SELECT c.first_name || ' ' || c.last_name AS customer_name,
       h.name AS hotel_name,
       r.rating,
       r.created_at
FROM reviews r
INNER JOIN customers c ON r.customer_id = c.id
INNER JOIN hotels h ON r.hotel_id = h.id
WHERE r.rating >= 4
ORDER BY r.rating DESC, h.name ASC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести все номера из базы данных вместе с количеством бронирований каждого номера. Включить номера без единого бронирования (показать 0). Отсортировать по количеству бронирований по убыванию.
**Конструкции:** `LEFT JOIN` (таблицы: `rooms`, `bookings`), `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT r.id,
       r.room_number,
       COUNT(b.id) AS booking_count
FROM rooms r
LEFT JOIN bookings b ON r.id = b.room_id
GROUP BY r.id, r.room_number
ORDER BY booking_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести всех клиентов, сделавших хотя бы одно бронирование, с суммарной потраченной суммой и количеством оставленных отзывов (если отзывов нет — вывести 0).
**Конструкции:** `INNER JOIN`, `LEFT JOIN` (таблицы: `customers`, `bookings`, `reviews`), `COALESCE`, `SUM`, `COUNT`
**Запрос:**

```sql
SELECT c.id,
       c.first_name,
       c.last_name,
       SUM(b.total_price) AS total_spent,
       COALESCE(COUNT(DISTINCT r.id), 0) AS reviews_count
FROM customers c
INNER JOIN bookings b ON c.id = b.customer_id
LEFT JOIN reviews r ON c.id = r.customer_id
GROUP BY c.id, c.first_name, c.last_name;

```

---

**Запрос 8 — UNION**
Создать единый список контактов: из `customers`: email клиента, с меткой 'Клиент'; из `hotels`: email отеля, с меткой 'Отель'. Убрать дубликаты. Отсортировать по типу, затем по email.
**Конструкции:** `UNION`, добавление литерального столбца, `ORDER BY`
**Запрос:**

```sql
SELECT email, 'Клиент' AS contact_type
FROM customers
WHERE email IS NOT NULL
UNION
SELECT email, 'Отель' AS contact_type
FROM hotels
WHERE email IS NOT NULL
ORDER BY contact_type, email;

```

---

**Запрос 9 — Комплексный SELECT №1**
Найти топ-5 самых прибыльных отелей за 2025 год: учитывать только бронирования со статусом 'completed'. Вывести: название отеля, город, суммарная выручка.
**Конструкции:** `JOIN`, `WHERE` + `EXTRACT(YEAR FROM ...)`, `GROUP BY`, `SUM`, `ORDER BY DESC`, `LIMIT`
**Запрос:**

```sql
SELECT h.name,
       h.city,
       SUM(b.total_price) AS total_revenue
FROM hotels h
JOIN rooms r ON h.id = r.hotel_id
JOIN bookings b ON r.id = b.room_id
WHERE b.status = 'completed' AND EXTRACT(YEAR FROM b.check_in_date) = 2025
GROUP BY h.id, h.name, h.city
ORDER BY total_revenue DESC
LIMIT 5;

```

---

**Запрос 10 — Комплексный SELECT №2**
Найти постоянных клиентов: тех, кто бронировал номера в одном и том же отеле более 2 раз. Вывести: полное имя клиента, название отеля, количество бронирований, суммарные расходы. Отсортировать по суммарным расходам по убыванию.
**Конструкции:** `JOIN` (4 таблицы), `GROUP BY` (клиент + отель), `HAVING COUNT(*) > 2`, `SUM`, `ORDER BY DESC`
**Запрос:**

```sql
SELECT c.first_name || ' ' || c.last_name AS full_name,
       h.name AS hotel_name,
       COUNT(b.id) AS booking_count,
       SUM(b.total_price) AS total_spent
FROM customers c
JOIN bookings b ON c.id = b.customer_id
JOIN rooms r ON b.room_id = r.id
JOIN hotels h ON r.hotel_id = h.id
GROUP BY c.id, full_name, h.id, hotel_name
HAVING COUNT(b.id) > 2
ORDER BY total_spent DESC;

```
