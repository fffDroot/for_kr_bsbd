Отличный выбор варианта! В этой задаче мы работаем с геоданными (координаты для поиска по радиусу), историю цен и пересечением дат (что является классической задачей для систем бронирования).

Я подготовил скрипт генерации данных таким образом, чтобы он создал группу объявлений в районе Лубянки с нужными датами в мае 2026 года, а также гарантировал наличие объявлений с частым изменением цены (для запроса 10).

Ниже — полное и готовое решение.

### 1. Структура проекта
Создай папку `real_estate` и настрой внутри неё следующую структуру:

```text
real_estate/
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
POSTGRES_DB=realestate_db

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

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/realestate_db"
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

app = FastAPI(title="Real Estate Service API")

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/listings")
def get_listings(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, listing_type, price, status FROM listings LIMIT 10")).mappings().all()
    return {"listings": result}

@app.get("/properties")
def get_properties(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, address, district, area_sqm FROM properties LIMIT 10")).mappings().all()
    return {"properties": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)
Этот скрипт содержит "закладки" для 9 и 10 запроса: искусственно генерирует объявления на Лубянке и сдаёт их в мае 2026 года.

**Файл `seed.py**`

```python
import os
import random
from datetime import date, timedelta
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker('ru_RU')

# --- НАСТРОЙКИ ---
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "realestate_db"
DB_USER = "postgres"
DB_PASS = "postgres"

TYPES = ['Квартира', 'Комната', 'Дом', 'Апартаменты', 'Студия', 'Коммерческая']
DISTRICTS = ['Арбат', 'Тверской', 'Хамовники', 'Пресненский', 'Басманный', 'Якиманка', 'Таганский', 'Мещанский', 'Замоскворечье']

NUM_PROPERTIES = 1000
NUM_LANDLORDS = 200
NUM_CLIENTS = 500
NUM_LISTINGS = 1500
NUM_PRICE_HISTORY = 10000
NUM_RENTALS = 2000
NUM_DEALS = 300
# -----------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных недвижимости...")

    # 1. Types
    execute_values(cursor, "INSERT INTO property_types (name) VALUES %s", [(t,) for t in TYPES])
    cursor.execute("SELECT id FROM property_types;")
    type_ids = [row[0] for row in cursor.fetchall()]

    # 2. Properties
    props_data = []
    for i in range(NUM_PROPERTIES):
        # Закладка для Запроса 9: Несколько объектов на Лубянке
        if i < 15:
            dist = 'Лубянка (Мещанский)'
            lat = round(random.uniform(55.755, 55.759), 7)
            lon = round(random.uniform(37.624, 37.628), 7)
            address = f"Лубянская пл., д. {random.randint(1, 10)}"
        else:
            dist = random.choice(DISTRICTS)
            lat = round(random.uniform(55.6, 55.9), 7)
            lon = round(random.uniform(37.4, 37.8), 7)
            address = fake.address()

        t_floors = random.randint(5, 30)
        props_data.append((
            random.choice(type_ids), address, dist, 'Москва',
            round(random.uniform(15.0, 200.0), 2), random.randint(1, 5),
            random.randint(1, t_floors), t_floors, lat, lon
        ))
    execute_values(cursor, "INSERT INTO properties (type_id, address, district, city, area_sqm, rooms, floor, total_floors, lat, lon) VALUES %s", props_data)
    cursor.execute("SELECT id, district FROM properties;")
    properties = cursor.fetchall()

    # 3. Landlords & Clients
    landlords_data = [(fake.first_name(), fake.last_name(), fake.email()[:100], fake.phone_number()[:20], random.choice(['individual', 'agency'])) for _ in range(NUM_LANDLORDS)]
    execute_values(cursor, "INSERT INTO landlords (first_name, last_name, email, phone, type) VALUES %s", landlords_data)

    clients_data = [(fake.first_name(), fake.last_name(), fake.email()[:100], fake.phone_number()[:20]) for _ in range(NUM_CLIENTS)]
    execute_values(cursor, "INSERT INTO clients (first_name, last_name, email, phone) VALUES %s", clients_data)

    cursor.execute("SELECT id FROM landlords;")
    landlord_ids = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT id FROM clients;")
    client_ids = [row[0] for row in cursor.fetchall()]

    # 4. Listings
    listings_data = []
    l_types = ['sale', 'rent_monthly', 'rent_daily']
    for p_id, dist in properties:
        l_type = 'rent_daily' if 'Лубянка' in dist else random.choice(l_types)

        price, ppd = None, None
        if l_type == 'sale': price = round(random.uniform(5000000, 50000000), 2)
        elif l_type == 'rent_monthly': price = round(random.uniform(30000, 200000), 2)
        else: ppd = round(random.uniform(2000, 15000), 2)

        status = random.choice(['active', 'rented', 'sold', 'archived'])
        listings_data.append((p_id, random.choice(landlord_ids), l_type, price, ppd, status))

        if len(listings_data) >= NUM_LISTINGS: break

    execute_values(cursor, "INSERT INTO listings (property_id, landlord_id, listing_type, price, price_per_day, status) VALUES %s RETURNING id, listing_type, status", listings_data)
    listings_records = cursor.fetchall()

    # 5. Price History (10000)
    history_data = []
    list_ids = [l[0] for l in listings_records]

    # Насильно делаем некоторым активным объявлениям >5 изменений цены (для Запроса 10)
    active_listings = [l[0] for l in listings_records if l[2] == 'active']
    for l_id in active_listings[:100]:
        for _ in range(7):
            history_data.append((l_id, round(random.uniform(5000, 100000), 2), round(random.uniform(5000, 100000), 2)))

    # Остальные
    remaining = NUM_PRICE_HISTORY - len(history_data)
    for _ in range(remaining):
        history_data.append((random.choice(list_ids), round(random.uniform(5000, 100000), 2), round(random.uniform(5000, 100000), 2)))

    execute_values(cursor, "INSERT INTO price_history (listing_id, old_price, new_price) VALUES %s", history_data)

    # 6. Rentals (Перекрываем 1-10 мая 2026 для Лубянки)
    rent_listings = [l[0] for l in listings_records if l[1] in ('rent_daily', 'rent_monthly')]
    rentals_data = []

    # Гарантируем аренду на Лубянке
    cursor.execute("SELECT l.id FROM listings l JOIN properties p ON l.property_id = p.id WHERE p.district LIKE '%Лубянка%';")
    lubyanka_ids = [row[0] for row in cursor.fetchall()]

    for l_id in lubyanka_ids[:5]:
        rentals_data.append((l_id, random.choice(client_ids), date(2026, 4, 29), date(2026, 5, 5), 35000.00, 'active'))
        rentals_data.append((l_id, random.choice(client_ids), date(2026, 5, 8), date(2026, 5, 12), 20000.00, 'active'))

    for _ in range(NUM_RENTALS - len(rentals_data)):
        start = fake.date_between(start_date=date(2024, 1, 1), end_date=date(2026, 12, 31))
        end = start + timedelta(days=random.randint(2, 30))
        rentals_data.append((random.choice(rent_listings), random.choice(client_ids), start, end, round(random.uniform(10000, 150000), 2), random.choice(['active', 'completed'])))

    execute_values(cursor, "INSERT INTO rentals (listing_id, client_id, start_date, end_date, total_price, status) VALUES %s", rentals_data)

    # 7. Deals
    sale_listings = [l[0] for l in listings_records if l[1] == 'sale' and l[2] == 'sold']
    deals_data = []
    for _ in range(min(NUM_DEALS, len(sale_listings))):
        deals_data.append((sale_listings.pop(), random.choice(client_ids), fake.date_between(start_date='-2y', end_date='today'), round(random.uniform(5000000, 50000000), 2)))
    execute_values(cursor, "INSERT INTO deals (listing_id, buyer_id, deal_date, final_price) VALUES %s", deals_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных успешно завершена!")

if __name__ == "__main__":
    seed_data()

```

---

### 5. Инструкция по запуску

1. Запусти контейнеры (со сборкой):
```bash
docker compose up -d --build

```


2. Подключись к контейнеру с приложением:
```bash
docker compose exec app bash

```


3. Сгенерируй данные:
```bash
python seed.py

```


4. Выйди из контейнера: `exit`.
5. Доступ:
* База (pgAdmin): `http://localhost:5050` (почта `admin@admin.com`, пароль `admin`). Хост сервера `db`, юзер `postgres`, БД `realestate_db`.
* API: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести все объявления типа 'rent_daily' или 'rent_monthly', статус которых 'active', стоимость в диапазоне 50 000 – 200 000 руб. (для помесячной) или цена за день до 5 000 руб. Отсортировать по типу объявления, затем по цене.
**Конструкции:** `WHERE`, `OR`, `AND`, `BETWEEN`, `<=`, `ORDER BY`
**Запрос:**

```sql
SELECT id, listing_type, price, price_per_day, status
FROM listings
WHERE status = 'active'
  AND (
        (listing_type = 'rent_monthly' AND price BETWEEN 50000 AND 200000)
     OR (listing_type = 'rent_daily' AND price_per_day <= 5000)
  )
ORDER BY listing_type ASC, COALESCE(price, price_per_day) ASC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести все объекты недвижимости в районах, содержащих слово 'Арбат' или 'Тверской', с площадью от 40 до 100 кв.м, не являющихся типом 'Комната'. Отсортировать по площади по убыванию.
**Конструкции:** `WHERE`, `LIKE`, `OR`, `BETWEEN`, `AND`, `!=`, `ORDER BY`
**Запрос:**

```sql
SELECT p.id, p.address, p.district, p.area_sqm, pt.name AS property_type
FROM properties p
JOIN property_types pt ON p.type_id = pt.id
WHERE (p.district LIKE '%Арбат%' OR p.district LIKE '%Тверской%')
  AND p.area_sqm BETWEEN 40 AND 100
  AND pt.name != 'Комната'
ORDER BY p.area_sqm DESC;

```

---

**Запрос 3 — GROUP BY**
Для каждого типа недвижимости посчитать: количество объектов, среднюю площадь, минимальную и максимальную площадь. Отсортировать по средней площади по убыванию.
**Конструкции:** `JOIN`, `GROUP BY`, `COUNT`, `AVG`, `MIN`, `MAX`, `ROUND`
**Запрос:**

```sql
SELECT pt.name AS property_type,
       COUNT(p.id) AS property_count,
       ROUND(AVG(p.area_sqm), 2) AS avg_area,
       MIN(p.area_sqm) AS min_area,
       MAX(p.area_sqm) AS max_area
FROM property_types pt
JOIN properties p ON pt.id = p.type_id
GROUP BY pt.id, pt.name
ORDER BY avg_area DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти арендодателей, разместивших более 5 объявлений и у которых средняя цена объявления выше 80 000 руб. Вывести: ФИО, тип (физлицо/агентство), количество объявлений, среднюю цену.
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `COUNT`, `AVG`, `ROUND`
**Запрос:**

```sql
SELECT l.first_name || ' ' || l.last_name AS landlord_name,
       l.type AS landlord_type,
       COUNT(lst.id) AS listings_count,
       ROUND(AVG(lst.price), 2) AS avg_price
FROM landlords l
JOIN listings lst ON l.id = lst.landlord_id
WHERE lst.price IS NOT NULL
GROUP BY l.id, l.first_name, l.last_name, l.type
HAVING COUNT(lst.id) > 5 AND AVG(lst.price) > 80000
ORDER BY avg_price DESC;

```

---

**Запрос 5 — INNER JOIN**
Вывести список сделок купли-продажи с полями: адрес объекта, тип недвижимости, ФИО покупателя, дата сделки, итоговая цена. Отсортировать по дате по убыванию.
**Конструкции:** `INNER JOIN` (5 таблиц), `ORDER BY`
**Запрос:**

```sql
SELECT p.address,
       pt.name AS property_type,
       c.first_name || ' ' || c.last_name AS buyer_name,
       d.deal_date,
       d.final_price
FROM deals d
INNER JOIN clients c ON d.buyer_id = c.id
INNER JOIN listings l ON d.listing_id = l.id
INNER JOIN properties p ON l.property_id = p.id
INNER JOIN property_types pt ON p.type_id = pt.id
ORDER BY d.deal_date DESC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести все объявления с количеством изменений цены каждого. Включить объявления, цена которых ни разу не менялась. Отсортировать по количеству изменений по убыванию.
**Конструкции:** `LEFT JOIN`, `COUNT`, `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT l.id AS listing_id,
       l.listing_type,
       COUNT(ph.id) AS price_changes_count
FROM listings l
LEFT JOIN price_history ph ON l.id = ph.listing_id
GROUP BY l.id, l.listing_type
ORDER BY price_changes_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести всех клиентов, заключивших хотя бы одну аренду, с суммарными расходами и флагом, совершали ли они покупку недвижимости (Да / Нет).
*(Используем агрегацию COUNT для проверки наличия сделок, чтобы избежать дублирования строк при LEFT JOIN).*
**Конструкции:** `INNER JOIN`, `LEFT JOIN`, `GROUP BY`, `SUM`, `CASE WHEN`, `COALESCE`
**Запрос:**

```sql
SELECT c.id,
       c.first_name,
       c.last_name,
       SUM(r.total_price) AS total_rent_spent,
       CASE WHEN COUNT(d.id) > 0 THEN 'Да' ELSE 'Нет' END AS has_bought_property
FROM clients c
INNER JOIN rentals r ON c.id = r.client_id
LEFT JOIN deals d ON c.id = d.buyer_id
GROUP BY c.id, c.first_name, c.last_name
ORDER BY total_rent_spent DESC;

```

---

**Запрос 8 — UNION**
Создать единый реестр закрытых сделок: из `deals` (Продажа) и `rentals` (Аренда completed). Объединить, отсортировать по дате по убыванию.
**Конструкции:** `UNION`, `JOIN`, литеральный столбец, `ORDER BY`
**Запрос:**

```sql
SELECT p.address,
       pt.name AS property_type,
       'Продажа' AS deal_type,
       d.deal_date AS event_date,
       d.final_price AS cost
FROM deals d
JOIN listings l ON d.listing_id = l.id
JOIN properties p ON l.property_id = p.id
JOIN property_types pt ON p.type_id = pt.id
UNION
SELECT p.address,
       pt.name AS property_type,
       'Аренда' AS deal_type,
       r.end_date AS event_date,
       r.total_price AS cost
FROM rentals r
JOIN listings l ON r.listing_id = l.id
JOIN properties p ON l.property_id = p.id
JOIN property_types pt ON p.type_id = pt.id
WHERE r.status = 'completed'
ORDER BY event_date DESC;

```

---

**Запрос 9 — Комплексный SELECT №1 ⭐**
Найти объявления посуточной аренды в районе Лубянки (55.757, 37.626) в радиусе 1 км, пересекающиеся с периодом майских праздников (01.05.2026 — 10.05.2026).
**Конструкции:** `JOIN`, `WHERE` (математические функции и перекрытие дат: начало аренды <= конец майских И конец аренды >= начало майских).
**Запрос:**

```sql
SELECT p.address,
       pt.name AS property_type,
       l.price_per_day,
       r.start_date,
       r.end_date
FROM rentals r
JOIN listings l ON r.listing_id = l.id
JOIN properties p ON l.property_id = p.id
JOIN property_types pt ON p.type_id = pt.id
WHERE l.listing_type = 'rent_daily'
  AND r.start_date <= '2026-05-10' AND r.end_date >= '2026-05-01'
  AND SQRT(POWER((p.lat - 55.757) * 111.0, 2) + POWER((p.lon - 37.626) * 111.0 * COS(RADIANS(55.757)), 2)) < 1;

```

---

**Запрос 10 — Комплексный SELECT №2 ⭐**
Для каждого типа недвижимости найти объявления, цена которых менялась более 5 раз, но объект так и не был продан или сдан.
**Конструкции:** `JOIN`, `LEFT JOIN` (`deals`, `rentals`), `GROUP BY`, `HAVING`, `WHERE ... IS NULL` (так называемый Anti-Join).
**Запрос:**

```sql
SELECT pt.name AS property_type,
       p.address,
       COALESCE(l.price, l.price_per_day) AS current_price,
       COUNT(ph.id) AS price_changes
FROM listings l
JOIN properties p ON l.property_id = p.id
JOIN property_types pt ON p.type_id = pt.id
JOIN price_history ph ON l.id = ph.listing_id
LEFT JOIN deals d ON l.id = d.listing_id
LEFT JOIN rentals r ON l.id = r.listing_id
WHERE d.id IS NULL AND r.id IS NULL
GROUP BY l.id, pt.name, p.address, current_price
HAVING COUNT(ph.id) > 5
ORDER BY price_changes DESC;

```