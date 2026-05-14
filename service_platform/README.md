Отличный вариант! Здесь интересная бизнес-логика: мы работаем со специалистами, заказами и отзывами. Чтобы запросы 9 и 10 выдали не пустые результаты, я специально запрограммирую генератор данных (`seed.py`) так, чтобы он создал группу «звездных» специалистов, у которых гарантированно будет более 40 заказов, более 15 отзывов и рейтинг 5.0.

Также, как разрешено в задании к Запросу 8, я **добавил поле `phone**` в таблицу `specialists` для красоты и логичности (иначе объединять телефон клиента с городом специалиста — это «костыль»).

Ниже представлено полное решение.

### 1. Структура проекта

Создай пустую папку (например, `service_platform`) и подготовь структуру:

```text
service_platform/
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
POSTGRES_DB=service_db

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
*(Используем PostgreSQL 15, как указано в задании)*

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
*(Обрати внимание: добавлено поле `phone` в `specialists` для корректной работы 8-го запроса)*

```sql
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

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/service_db"
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

app = FastAPI(title="Services & Specialists API")

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/specialists")
def get_specialists(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, first_name, last_name, category_id, rating FROM specialists LIMIT 10")).mappings().all()
    return {"specialists": result}

@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, status, price, created_at FROM orders LIMIT 10")).mappings().all()
    return {"orders": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

Этот скрипт содержит "магию" (взвешенный рандом), которая гарантирует, что некоторые специалисты (из разных категорий) получат аномально много заказов и высоких отзывов. Это 100% обеспечит работу сложных запросов 9 и 10.

**Файл `seed.py**`

```python
import os
import random
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker('ru_RU')

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К БД ---
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "service_db"
DB_USER = "postgres"
DB_PASS = "postgres"

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ГЕНЕРАЦИИ ---
CATEGORIES = [
    'Сантехник', 'Электрик', 'Маляр', 'Уборка', 'Репетитор',
    'Няня', 'Грузчик', 'Курьер', 'Сборщик мебели', 'Мастер на час',
    'Компьютерный мастер', 'Фотограф', 'Дизайнер', 'Швея', 'Автомеханик'
]
DISTRICTS = ['ЦАО', 'САО', 'СВАО', 'ВАО', 'ЮВАО', 'ЮАО', 'ЮЗАО', 'ЗАО', 'СЗАО', 'ЗелАО', 'ТиНАО']

NUM_SPECIALISTS = 500
NUM_CUSTOMERS = 1000
NUM_ORDERS = 10000
NUM_REVIEWS = 3000

DATE_START = datetime(2023, 1, 1)
DATE_END = datetime(2026, 1, 1)
# --------------------------------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных...")

    # 1. Categories
    cat_data = [(name, f"Услуги категории {name}") for name in CATEGORIES]
    execute_values(cursor, "INSERT INTO categories (name, description) VALUES %s", cat_data)
    cursor.execute("SELECT id, name FROM categories;")
    categories_map = {row[1]: row[0] for row in cursor.fetchall()}
    category_ids = list(categories_map.values())

    # 2. Specialists
    specialists_data = []
    for _ in range(NUM_SPECIALISTS):
        specialists_data.append((
            fake.first_name(), fake.last_name(), 'Москва', random.choice(DISTRICTS),
            random.choice(category_ids), round(random.uniform(1.0, 5.0), 2),
            random.randint(0, 30), fake.phone_number()[:20], fake.text(max_nb_chars=150), True
        ))
    execute_values(cursor, "INSERT INTO specialists (first_name, last_name, city, district, category_id, rating, experience_years, phone, bio, is_active) VALUES %s RETURNING id, category_id", specialists_data)

    # Сохраняем сгенерированных специалистов.
    # Выделяем 15 "супер-звезд" (по одной в каждой категории), чтобы гарантированно выполнить условия 9 и 10 запросов.
    specialists_records = cursor.fetchall()
    super_stars = {}
    for spec_id, cat_id in specialists_records:
        if cat_id not in super_stars:
            super_stars[cat_id] = spec_id # Берем первого попавшегося как звезду

    # 3. Customers
    customers_data = []
    for _ in range(NUM_CUSTOMERS):
        customers_data.append((
            fake.first_name(), fake.last_name(), fake.unique.email()[:100],
            fake.phone_number()[:20], 'Москва'
        ))
    execute_values(cursor, "INSERT INTO customers (first_name, last_name, email, phone, city) VALUES %s", customers_data)
    cursor.execute("SELECT id FROM customers;")
    customer_ids = [row[0] for row in cursor.fetchall()]

    # 4. Orders
    statuses = ['new', 'in_progress', 'completed', 'cancelled']
    orders_data = []

    for _ in range(NUM_ORDERS):
        c_id = random.choice(customer_ids)

        # 30% шанса, что заказ достанется "суперзвезде", чтобы набить им >40 заказов
        if random.random() < 0.3:
            cat_id = random.choice(category_ids)
            s_id = super_stars[cat_id]
        else:
            s_id, cat_id = random.choice(specialists_records)

        status = random.choice(statuses)
        # Искусственно делаем так, чтобы у суперзвезд заказы были 'completed'
        if s_id in super_stars.values():
            status = 'completed'

        created_at = fake.date_time_between(start_date=DATE_START, end_date=DATE_END)
        completed_at = created_at + timedelta(days=random.randint(1, 5)) if status == 'completed' else None
        price = round(random.uniform(500, 50000), 2)

        orders_data.append((c_id, s_id, cat_id, status, created_at, completed_at, price))

    execute_values(cursor, "INSERT INTO orders (customer_id, specialist_id, category_id, status, created_at, completed_at, price) VALUES %s RETURNING id, customer_id, specialist_id, status", orders_data)

    # 5. Reviews
    orders_records = cursor.fetchall()
    completed_orders = [o for o in orders_records if o[3] == 'completed']

    reviews_data = []

    # Сначала генерируем кучу идеальных отзывов (5.0) для суперзвезд (гарантия > 15 отзывов)
    super_star_ids = set(super_stars.values())
    star_orders = [o for o in completed_orders if o[2] in super_star_ids]
    normal_orders = [o for o in completed_orders if o[2] not in super_star_ids]

    # Даем по отзыву на 80% заказов суперзвезд
    for o in star_orders:
        if random.random() < 0.8:
            reviews_data.append((o[1], o[2], o[0], 5.0, fake.text(max_nb_chars=100)))
            if len(reviews_data) >= NUM_REVIEWS: break

    # Остальные отзывы распределяем случайно
    remaining_reviews = NUM_REVIEWS - len(reviews_data)
    if remaining_reviews > 0:
        chosen_normals = random.sample(normal_orders, min(remaining_reviews, len(normal_orders)))
        for o in chosen_normals:
            reviews_data.append((o[1], o[2], o[0], round(random.uniform(1.0, 5.0), 2), fake.text(max_nb_chars=100)))

    execute_values(cursor, "INSERT INTO reviews (customer_id, specialist_id, order_id, rating, comment) VALUES %s", reviews_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных завершена! Супер-специалисты готовы.")

if __name__ == "__main__":
    seed_data()

```

---

### 5. Инструкция по запуску

1. Сборка и запуск контейнеров в терминале:
```bash
docker compose up -d --build

```


2. Вход в контейнер:
```bash
docker compose exec app bash

```


3. Генерация данных:
```bash
python seed.py

```


4. Выход: `exit`.
5. Доступ:
* БД (pgAdmin): `http://localhost:5050` (юзер `admin@admin.com`, пароль `admin`). Подключение: Host `db`, User `postgres`, Password `postgres`, DB `service_db`.
* FastAPI: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести всех активных специалистов из г. Москвы с опытом работы от 5 до 15 лет и рейтингом выше 4.0. Отсортировать по рейтингу по убыванию, затем по опыту.
**Конструкции:** `WHERE`, `AND`, `BETWEEN`, `>`, `=`, `ORDER BY`
**Запрос:**

```sql
SELECT first_name, last_name, experience_years, rating
FROM specialists
WHERE is_active = TRUE
  AND city = 'Москва'
  AND experience_years BETWEEN 5 AND 15
  AND rating > 4.0
ORDER BY rating DESC, experience_years ASC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести все заказы со статусом не 'cancelled' и не 'new', созданные в 2025 году, с ценой более 3 000 руб. Отсортировать по дате создания по убыванию.
**Конструкции:** `WHERE`, `NOT IN`, `AND`, `>`, `EXTRACT`, `ORDER BY`
**Запрос:**

```sql
SELECT id, status, price, created_at
FROM orders
WHERE status NOT IN ('cancelled', 'new')
  AND EXTRACT(YEAR FROM created_at) = 2025
  AND price > 3000
ORDER BY created_at DESC;

```

---

**Запрос 3 — GROUP BY**
Для каждой категории посчитать: количество специалистов, средний рейтинг (2 знака), минимальный и максимальный рейтинг. Отсортировать по среднему рейтингу по убыванию.
**Конструкции:** `JOIN`, `GROUP BY`, `COUNT`, `AVG`, `MIN`, `MAX`, `ROUND`
**Запрос:**

```sql
SELECT c.name AS category_name,
       COUNT(s.id) AS specialists_count,
       ROUND(AVG(s.rating), 2) AS avg_rating,
       MIN(s.rating) AS min_rating,
       MAX(s.rating) AS max_rating
FROM categories c
JOIN specialists s ON c.id = s.category_id
GROUP BY c.id, c.name
ORDER BY avg_rating DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти специалистов, получивших более 10 отзывов со средним рейтингом выше 4.5. Вывести: имя и фамилию специалиста, категорию, количество отзывов, средний рейтинг.
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `COUNT`, `AVG`, `ROUND`
**Запрос:**

```sql
SELECT s.first_name,
       s.last_name,
       c.name AS category_name,
       COUNT(r.id) AS reviews_count,
       ROUND(AVG(r.rating), 2) AS actual_avg_rating
FROM specialists s
JOIN categories c ON s.category_id = c.id
JOIN reviews r ON s.id = r.specialist_id
GROUP BY s.id, s.first_name, s.last_name, c.name
HAVING COUNT(r.id) > 10 AND AVG(r.rating) > 4.5
ORDER BY actual_avg_rating DESC;

```

---

**Запрос 5 — INNER JOIN**
Вывести список завершённых заказов с полями: имя и фамилия клиента, имя и фамилия специалиста, название категории, цена заказа, дата завершения. Отсортировать по дате завершения по убыванию.
**Конструкции:** `INNER JOIN` (4 таблицы), `WHERE`, `ORDER BY`
**Запрос:**

```sql
SELECT cust.first_name || ' ' || cust.last_name AS customer_name,
       spec.first_name || ' ' || spec.last_name AS specialist_name,
       cat.name AS category_name,
       o.price,
       o.completed_at
FROM orders o
INNER JOIN customers cust ON o.customer_id = cust.id
INNER JOIN specialists spec ON o.specialist_id = spec.id
INNER JOIN categories cat ON o.category_id = cat.id
WHERE o.status = 'completed'
ORDER BY o.completed_at DESC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести всех специалистов с количеством отзывов каждого. Включить специалистов без отзывов (показать 0). Отсортировать по количеству отзывов по убыванию.
**Конструкции:** `LEFT JOIN`, `COUNT`, `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT s.id,
       s.first_name,
       s.last_name,
       COUNT(r.id) AS reviews_count
FROM specialists s
LEFT JOIN reviews r ON s.id = r.specialist_id
GROUP BY s.id, s.first_name, s.last_name
ORDER BY reviews_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести всех клиентов, сделавших хотя бы один заказ, с общим количеством их заказов и средним рейтингом, который они ставили специалистам.
**Конструкции:** `INNER JOIN`, `LEFT JOIN`, `GROUP BY`, `COUNT`, `AVG`
*(Используем COUNT(DISTINCT o.id), чтобы дубли из отзывов не ломали подсчет заказов).*
**Запрос:**

```sql
SELECT c.id,
       c.first_name,
       c.last_name,
       COUNT(DISTINCT o.id) AS total_orders,
       ROUND(AVG(r.rating), 2) AS avg_given_rating
FROM customers c
INNER JOIN orders o ON c.id = o.customer_id
LEFT JOIN reviews r ON c.id = r.customer_id
GROUP BY c.id, c.first_name, c.last_name
ORDER BY total_orders DESC;

```

---

**Запрос 8 — UNION**
Создать единый список контактов из двух источников (клиенты и специалисты). Объединить, отсортировать по роли, затем по фамилии.
**Конструкции:** `UNION`, литеральный столбец, конкатенация, `ORDER BY`
**Запрос:**

```sql
SELECT last_name || ' ' || first_name AS full_name,
       'Клиент' AS role,
       phone
FROM customers
UNION
SELECT last_name || ' ' || first_name AS full_name,
       'Специалист' AS role,
       phone
FROM specialists
ORDER BY role ASC, full_name ASC;

```

---

**Запрос 9 — Комплексный SELECT №1 ⭐**

**9а. Худший сантехник Москвы (хотя бы 1 отзыв)**
**Запрос 9а:**

```sql
SELECT s.first_name || ' ' || s.last_name AS full_name,
       s.district,
       ROUND(AVG(r.rating), 2) AS avg_real_rating,
       COUNT(r.id) AS reviews_count
FROM specialists s
JOIN categories c ON s.category_id = c.id
JOIN reviews r ON s.id = r.specialist_id
WHERE c.name = 'Сантехник' AND s.city = 'Москва'
GROUP BY s.id, full_name, s.district
HAVING COUNT(r.id) >= 1
ORDER BY avg_real_rating ASC
LIMIT 1;

```

**9б. Специалист с наибольшим количеством выполненных заказов**
**Запрос 9б:**

```sql
SELECT s.first_name || ' ' || s.last_name AS full_name,
       c.name AS category_name,
       COUNT(o.id) AS completed_orders_count
FROM specialists s
JOIN categories c ON s.category_id = c.id
JOIN orders o ON s.id = o.specialist_id
WHERE o.status = 'completed'
GROUP BY s.id, full_name, category_name
ORDER BY completed_orders_count DESC
LIMIT 1;

```

---

**Запрос 10 — Комплексный SELECT №2 ⭐**
Для каждой категории вывести специалиста: > 40 выполненных заказов, > 15 отзывов, средний рейтинг = 5.0 (или близкий к 5).
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `COUNT`, `AVG`, `ROUND`
*(Примечание: Благодаря "суперзвездам" из Python-скрипта, этот запрос гарантированно вернет по одному специалисту из большинства категорий).*
**Запрос:**

```sql
SELECT cat.name AS category,
       s.first_name || ' ' || s.last_name AS full_name,
       COUNT(DISTINCT o.id) AS completed_orders,
       COUNT(DISTINCT r.id) AS total_reviews,
       ROUND(AVG(r.rating), 2) AS avg_rating
FROM specialists s
JOIN categories cat ON s.category_id = cat.id
JOIN orders o ON s.id = o.specialist_id
JOIN reviews r ON s.id = r.specialist_id
WHERE o.status = 'completed'
GROUP BY s.id, full_name, cat.name
HAVING COUNT(DISTINCT o.id) > 40
   AND COUNT(DISTINCT r.id) > 15
   AND ROUND(AVG(r.rating), 2) = 5.00
ORDER BY category ASC;

```
