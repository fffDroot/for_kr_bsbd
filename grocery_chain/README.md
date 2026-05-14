Привет! Отличный выбор — база данных сети продуктовых магазинов. В этом варианте у нас классическая задача ритейла: управление запасами (инвентаризация), учет сроков годности, сезоны продаж и ценообразование.

Я подготовил решение, в котором `seed.py` специально "подкручен", чтобы генерировать быстропортящиеся продукты для первого запроса, магазины с высокой выручкой для 4 запроса и "залежавшийся" товар, у которого вот-вот истечет срок годности, для сложного 10 запроса.

Ниже представлено полное и готовое к сдаче решение.

### 1. Структура проекта

Создай пустую папку (например, `grocery_chain`) и настрой в ней следующую структуру файлов:

```text
grocery_chain/
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
POSTGRES_DB=grocery_db

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
*(СУБД PostgreSQL 15, как по условию)*

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

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/grocery_db"
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

app = FastAPI(title="Grocery Chain API")

@app.get("/")
def read_root():
    return {"message": "Grocery API is running"}

@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, name, price, unit FROM products LIMIT 10")).mappings().all()
    return {"products": result}

@app.get("/sales")
def get_sales(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, product_id, quantity, sale_date FROM sales LIMIT 10")).mappings().all()
    return {"sales": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

Этот скрипт специально генерирует логичные данные. Например, сезон зависит от месяца, а для Запроса 10 формируется "зависающий" инвентарь (скоро истечет срок годности, давно не продавался).

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
DB_NAME = "grocery_db"
DB_USER = "postgres"
DB_PASS = "postgres"

CATEGORIES = ['Молочные', 'Мясные', 'Рыба', 'Овощи', 'Фрукты', 'Хлеб', 'Напитки', 'Бакалея', 'Кондитерские', 'Заморозка', 'Консервы', 'Соусы']
DISTRICTS = ['ЦАО', 'САО', 'СВАО', 'ВАО', 'ЮВАО', 'ЮАО', 'ЮЗАО', 'ЗАО', 'СЗАО', 'ЗелАО', 'ТиНАО']
UNITS = ['шт', 'кг', 'л', 'упак']

NUM_SUPPLIERS = 30
NUM_STORES = 20
NUM_PRODUCTS = 300
NUM_INVENTORY = 3000
NUM_SALES = 10000
NUM_PRICE_HISTORY = 2000
# -----------------

def get_season(month):
    if month in (12, 1, 2): return 'Зима'
    if month in (3, 4, 5): return 'Весна'
    if month in (6, 7, 8): return 'Лето'
    return 'Осень'

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных продуктовой сети...")

    # 1. Categories
    cat_data = [(name, f"Отдел {name}") for name in CATEGORIES]
    execute_values(cursor, "INSERT INTO categories (name, description) VALUES %s RETURNING id, name", cat_data)
    cat_map = {name: c_id for c_id, name in cursor.fetchall()}
    cat_ids = list(cat_map.values())

    # 2. Suppliers
    sup_data = [(fake.company(), fake.city(), fake.phone_number()[:20]) for _ in range(NUM_SUPPLIERS)]
    execute_values(cursor, "INSERT INTO suppliers (name, city, contact) VALUES %s RETURNING id", sup_data)
    sup_ids = [row[0] for row in cursor.fetchall()]

    # 3. Stores
    stores_data = [(f"Магазин №{i}", fake.address(), 'Москва', random.choice(DISTRICTS)) for i in range(1, NUM_STORES + 1)]
    execute_values(cursor, "INSERT INTO stores (name, address, city, district) VALUES %s RETURNING id", stores_data)
    store_ids = [row[0] for row in cursor.fetchall()]

    # 4. Products
    products_data = []
    for _ in range(NUM_PRODUCTS):
        cat_id = random.choice(cat_ids)
        # Для Запроса 1: Делаем у молочки и мяса короткие сроки
        if cat_id in (cat_map['Молочные'], cat_map['Мясные']):
            shelf_life = random.randint(3, 12)
        else:
            shelf_life = random.randint(15, 365)

        products_data.append((
            fake.catch_phrase()[:100], cat_id, random.choice(sup_ids),
            round(random.uniform(30, 2000), 2), random.choice(UNITS), shelf_life
        ))
    execute_values(cursor, "INSERT INTO products (name, category_id, supplier_id, price, unit, shelf_life_days) VALUES %s RETURNING id, shelf_life_days, price", products_data)
    products_records = cursor.fetchall()
    prod_ids = [p[0] for p in products_records]
    prod_info = {p[0]: {'shelf_life': p[1], 'price': p[2]} for p in products_records}

    # 5. Inventory
    inventory_data = []
    today = date.today()
    for i in range(NUM_INVENTORY):
        p_id = random.choice(prod_ids)
        s_id = random.choice(store_ids)
        shelf = prod_info[p_id]['shelf_life']

        # Для Запроса 10: "Протухающие" товары (не продавались >30 дней, срок < 7 дней)
        if i < 150:
            exp_date = today + timedelta(days=random.randint(1, 6))
            rec_date = exp_date - timedelta(days=shelf)
            last_sold = today - timedelta(days=random.randint(31, 60)) if random.random() > 0.5 else None
        else:
            rec_date = fake.date_between(start_date='-6m', end_date='today')
            exp_date = rec_date + timedelta(days=shelf)
            last_sold = fake.date_between(start_date=rec_date, end_date='today')

        inventory_data.append((s_id, p_id, random.randint(0, 500), rec_date, exp_date, last_sold))
    execute_values(cursor, "INSERT INTO inventory (store_id, product_id, quantity, received_date, expiry_date, last_sold_date) VALUES %s", inventory_data)

    # 6. Sales
    sales_data = []
    for _ in range(NUM_SALES):
        p_id = random.choice(prod_ids)
        # Искусственно завышаем цену/кол-во для Запроса 4 (чтобы выручка пробила 500к)
        qty = random.randint(1, 20) if random.random() > 0.1 else random.randint(50, 200)
        sale_date = fake.date_between(start_date=date(2023, 1, 1), end_date=date(2025, 12, 31))

        price_at_sale = float(prod_info[p_id]['price']) * random.uniform(0.9, 1.2)
        sales_data.append((
            random.choice(store_ids), p_id, qty, sale_date,
            round(price_at_sale, 2), get_season(sale_date.month)
        ))
    execute_values(cursor, "INSERT INTO sales (store_id, product_id, quantity, sale_date, price_at_sale, season) VALUES %s", sales_data)

    # 7. Price History
    history_data = []
    for _ in range(NUM_PRICE_HISTORY):
        p_id = random.choice(prod_ids)
        base_p = float(prod_info[p_id]['price'])
        history_data.append((
            p_id, random.choice(store_ids), round(base_p * 0.9, 2), round(base_p * 1.1, 2),
            fake.date_time_between(start_date='-1y', end_date='now')
        ))
    execute_values(cursor, "INSERT INTO price_history (product_id, store_id, old_price, new_price, changed_at) VALUES %s", history_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных успешно завершена!")

if __name__ == "__main__":
    seed_data()

```

---

### 5. Инструкция по запуску

1. Сборка и запуск контейнеров в фоне:
```bash
docker compose up -d --build

```


2. Подключение к терминалу контейнера приложения:
```bash
docker compose exec app bash

```


3. Запуск генератора данных:
```bash
python seed.py

```


4. Выход из контейнера: `exit`.
5. Проверка:
* База (pgAdmin): `http://localhost:5050` (почта `admin@admin.com`, пароль `admin`). Хост `db`, юзер `postgres`, БД `grocery_db`.
* API: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести все товары категорий 'Молочные' или 'Мясные' с ценой от 50 до 500 руб. и сроком годности менее 14 дней. Отсортировать по сроку годности по возрастанию, затем по цене.
**Конструкции:** `JOIN`, `WHERE`, `IN`, `AND`, `BETWEEN`, `<`, `ORDER BY`
**Запрос:**

```sql
SELECT p.name, c.name AS category_name, p.price, p.shelf_life_days
FROM products p
JOIN categories c ON p.category_id = c.id
WHERE c.name IN ('Молочные', 'Мясные')
  AND p.price BETWEEN 50 AND 500
  AND p.shelf_life_days < 14
ORDER BY p.shelf_life_days ASC, p.price ASC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести все продажи, совершённые в 2025 году в сезон 'Лето' или 'Весна', с количеством более 5 единиц за одну продажу. Исключить продажи с ценой ниже 20 руб. Отсортировать по дате продажи по убыванию.
**Конструкции:** `WHERE`, `IN`, `AND`, `>`, `>=`, `EXTRACT`, `ORDER BY`
**Запрос:**

```sql
SELECT id, store_id, product_id, quantity, sale_date, price_at_sale, season
FROM sales
WHERE EXTRACT(YEAR FROM sale_date) = 2025
  AND season IN ('Лето', 'Весна')
  AND quantity > 5
  AND price_at_sale >= 20
ORDER BY sale_date DESC;

```

---

**Запрос 3 — GROUP BY**
Для каждого сезона подсчитать: общее количество продаж (строк), суммарную выручку (кол-во * цена), среднюю стоимость продажи (2 знака), количество уникальных проданных товаров.
**Конструкции:** `GROUP BY`, `COUNT`, `SUM`, `AVG`, `COUNT(DISTINCT ...)`, `ROUND`
**Запрос:**

```sql
SELECT season,
       COUNT(*) AS sales_count,
       SUM(quantity * price_at_sale) AS total_revenue,
       ROUND(AVG(price_at_sale), 2) AS avg_price_per_unit,
       COUNT(DISTINCT product_id) AS unique_products
FROM sales
GROUP BY season
ORDER BY total_revenue DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти магазины, суммарная выручка которых превышает 500 000 руб. за 2025 год, и у которых более 10 уникальных категорий проданных товаров.
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `SUM`, `COUNT(DISTINCT ...)`, `EXTRACT`
**Запрос:**

```sql
SELECT st.name AS store_name,
       SUM(s.quantity * s.price_at_sale) AS total_revenue,
       COUNT(DISTINCT p.category_id) AS categories_count
FROM stores st
JOIN sales s ON st.id = s.store_id
JOIN products p ON s.product_id = p.id
WHERE EXTRACT(YEAR FROM s.sale_date) = 2025
GROUP BY st.id, st.name
HAVING SUM(s.quantity * s.price_at_sale) > 500000
   AND COUNT(DISTINCT p.category_id) > 10;

```

---

**Запрос 5 — INNER JOIN**
Вывести список продаж с полями: название магазина, название товара, категория, поставщик, количество, цена продажи, дата. Только продажи за декабрь 2024. Отсортировать по дате, затем по названию магазина.
**Конструкции:** `INNER JOIN` (5 таблиц), `WHERE`, `ORDER BY`
**Запрос:**

```sql
SELECT st.name AS store_name,
       p.name AS product_name,
       c.name AS category_name,
       sup.name AS supplier_name,
       s.quantity,
       s.price_at_sale,
       s.sale_date
FROM sales s
INNER JOIN stores st ON s.store_id = st.id
INNER JOIN products p ON s.product_id = p.id
INNER JOIN categories c ON p.category_id = c.id
INNER JOIN suppliers sup ON p.supplier_id = sup.id
WHERE s.sale_date >= '2024-12-01' AND s.sale_date <= '2024-12-31'
ORDER BY s.sale_date ASC, st.name ASC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести все товары с суммарным количеством проданных единиц. Включить товары, которые ни разу не продавались (вывести 0). Отсортировать по продажам по убыванию.
**Конструкции:** `LEFT JOIN`, `SUM`, `COALESCE`, `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT p.id,
       p.name,
       COALESCE(SUM(s.quantity), 0) AS total_sold_qty
FROM products p
LEFT JOIN sales s ON p.id = s.product_id
GROUP BY p.id, p.name
ORDER BY total_sold_qty DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести все магазины с суммарной выручкой (из `sales`) и количеством изменений цен (из `price_history`). Включить магазины без продаж.
*(Используем подзапросы в FROM, чтобы таблицы `sales` и `price_history` не перемножались).*
**Конструкции:** `LEFT JOIN` (на предварительно сгруппированные данные), `COALESCE`
**Запрос:**

```sql
SELECT st.name AS store_name,
       COALESCE(sales_data.total_revenue, 0) AS total_revenue,
       COALESCE(ph_data.price_changes_count, 0) AS price_changes
FROM stores st
LEFT JOIN (
    SELECT store_id, SUM(quantity * price_at_sale) AS total_revenue
    FROM sales GROUP BY store_id
) sales_data ON st.id = sales_data.store_id
LEFT JOIN (
    SELECT store_id, COUNT(*) AS price_changes_count
    FROM price_history GROUP BY store_id
) ph_data ON st.id = ph_data.store_id
ORDER BY total_revenue DESC;

```

---

**Запрос 8 — UNION**
Создать единый прайс-лист: "Текущая цена" (из `products`) и "Цена после изменения" (последняя новая цена из `price_history`).
*(Используем `DISTINCT ON` в Postgres для извлечения только последнего изменения цены).*
**Конструкции:** `UNION`, `JOIN`, литеральный столбец, `DISTINCT ON`, `ORDER BY`
**Запрос:**

```sql
SELECT p.name AS product_name, c.name AS category_name, p.price AS price_value, 'Текущая цена' AS price_type
FROM products p
JOIN categories c ON p.category_id = c.id
UNION
SELECT p.name, c.name, ph.new_price, 'Цена после изменения'
FROM (
    SELECT DISTINCT ON (product_id) product_id, new_price
    FROM price_history
    ORDER BY product_id, changed_at DESC
) ph
JOIN products p ON ph.product_id = p.id
JOIN categories c ON p.category_id = c.id
ORDER BY product_name ASC, price_type DESC;

```

---

**Запрос 9 — Комплексный SELECT №1 ⭐**
Для каждого сезона найти топ-10 самых продаваемых товаров (по количеству единиц).
**Конструкции:** CTE (`WITH`), `JOIN`, `GROUP BY`, `SUM`, оконная функция `ROW_NUMBER() OVER (PARTITION BY ...)`
**Запрос:**

```sql
WITH SeasonSales AS (
    SELECT s.season,
           p.name AS product_name,
           c.name AS category_name,
           SUM(s.quantity) AS total_qty,
           ROW_NUMBER() OVER (PARTITION BY s.season ORDER BY SUM(s.quantity) DESC) as rank
    FROM sales s
    JOIN products p ON s.product_id = p.id
    JOIN categories c ON p.category_id = c.id
    GROUP BY s.season, p.id, p.name, c.name
)
SELECT season, product_name, category_name, total_qty
FROM SeasonSales
WHERE rank <= 10;

```

---

**Запрос 10 — Комплексный SELECT №2 ⭐**
Для каждой категории товаров найти позиции, которым необходимо снизить цену: не продавались > 30 дней и срок годности истекает менее чем через 7 дней.
**Конструкции:** `JOIN`, `WHERE`, `INTERVAL`, `IS NULL`, `BETWEEN`, `ORDER BY`
**Запрос:**

```sql
SELECT c.name AS category_name,
       p.name AS product_name,
       st.name AS store_name,
       p.price AS current_price,
       i.expiry_date,
       i.last_sold_date
FROM inventory i
JOIN products p ON i.product_id = p.id
JOIN categories c ON p.category_id = c.id
JOIN stores st ON i.store_id = st.id
WHERE (i.last_sold_date < CURRENT_DATE - INTERVAL '30 days' OR i.last_sold_date IS NULL)
  AND i.expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
ORDER BY i.expiry_date ASC;

```