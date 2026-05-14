Отличный вариант! Тематика каршеринга подразумевает интересную логику с гео-координатами, расчетом пробега и штрафами.

Для Запроса 9а требуется считать дистанцию по координатам из текста начала аренды (start_location). Чтобы это сработало идеально, я настроил seed.py так, чтобы он генерировал start_location в виде строгих координат (например, 55.75123,37.61842), которые мы затем легко распарсим в SQL-запросе. Также я заложил гарантированных клиентов с кучей штрафов (для запроса 10) и машины с превышенным порогом ТО (для запроса 9б).

Ниже — полное и готовое решение.

Структура проекта Создай пустую папку (например, carsharing) и подготовь в ней следующую структуру:
carsharing/ ├── db/ │ └── init/ │ └── 01_schema.sql ├── api/ │ ├── init.py │ ├── database.py │ └── main.py ├── docker-compose.yml ├── Dockerfile ├── requirements.txt ├── .env └── seed.py

Конфигурационные файлы Файл .env
POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_DB=carsharing_db

Файл requirements.txt

fastapi==0.115.* uvicorn==0.34.* sqlalchemy==2.0.* psycopg2-binary==2.9.* faker

Файл Dockerfile

FROM bsbd/backend:2026

WORKDIR /app

COPY requirements.txt . RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

Файл docker-compose.yml

version: "3.8"

services: db: image: postgres:15 env_file: - .env volumes: - ./db/init:/docker-entrypoint-initdb.d:ro - pgdata:/var/lib/postgresql/data ports: - "5432:5432" healthcheck: test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"] interval: 10s timeout: 5s retries: 5

app: build: . ports: - "8000:8000" env_file: - .env environment: - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB} depends_on: db: condition: service_healthy volumes: - .:/app

pgadmin: image: dpage/pgadmin4 environment: PGADMIN_DEFAULT_EMAIL: "admin@admin.com" PGADMIN_DEFAULT_PASSWORD: "admin" ports: - "5050:80" depends_on: db: condition: service_healthy

volumes: pgdata:

Схема БД и FastAPI Приложение Файл db/init/01_schema.sql
CREATE TABLE car_categories ( id SERIAL PRIMARY KEY, name VARCHAR(50) NOT NULL, price_per_hour NUMERIC(8,2), maintenance_km_threshold INT DEFAULT 20000 );

CREATE TABLE spawn_points ( id SERIAL PRIMARY KEY, name VARCHAR(200), address TEXT, lat NUMERIC(10,7), lon NUMERIC(10,7), city VARCHAR(50) DEFAULT 'Москва' );

CREATE TABLE cars ( id SERIAL PRIMARY KEY, brand VARCHAR(50), model VARCHAR(50), year INT, category_id INT REFERENCES car_categories(id), color VARCHAR(30), license_plate VARCHAR(15) UNIQUE, mileage INT DEFAULT 0, spawn_point_id INT REFERENCES spawn_points(id), status VARCHAR(20) DEFAULT 'available' );

CREATE TABLE customers ( id SERIAL PRIMARY KEY, first_name VARCHAR(50) NOT NULL, last_name VARCHAR(50) NOT NULL, email VARCHAR(100), phone VARCHAR(20), license_number VARCHAR(20) UNIQUE, birth_date DATE );

CREATE TABLE rentals ( id SERIAL PRIMARY KEY, customer_id INT NOT NULL REFERENCES customers(id), car_id INT NOT NULL REFERENCES cars(id), start_time TIMESTAMP NOT NULL, end_time TIMESTAMP, start_location TEXT, end_location TEXT, total_price NUMERIC(10,2), status VARCHAR(20) DEFAULT 'active' );

CREATE TABLE accidents ( id SERIAL PRIMARY KEY, customer_id INT NOT NULL REFERENCES customers(id), car_id INT NOT NULL REFERENCES cars(id), rental_id INT REFERENCES rentals(id), accident_date TIMESTAMP, location TEXT NOT NULL, description TEXT, fine_amount NUMERIC(10,2) DEFAULT 0 );

CREATE TABLE maintenance_records ( id SERIAL PRIMARY KEY, car_id INT NOT NULL REFERENCES cars(id), service_date DATE, description TEXT, cost NUMERIC(10,2), mileage_at_service INT );

Файл api/database.py

import os from sqlalchemy import create_engine from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv( "DATABASE_URL", "postgresql://postgres:postgres@db:5432/carsharing_db" )

engine = create_engine(DATABASE_URL) SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db(): db = SessionLocal() try: yield db finally: db.close()

Файл api/main.py

from fastapi import FastAPI, Depends from sqlalchemy.orm import Session from sqlalchemy import text from .database import get_db

app = FastAPI(title="Carsharing API")

@app.get("/") def read_root(): return {"message": "Carsharing API is running"}

@app.get("/cars") def get_cars(db: Session = Depends(get_db)): result = db.execute(text("SELECT id, brand, model, license_plate, status FROM cars LIMIT 10")).mappings().all() return {"cars": result}

@app.get("/rentals") def get_rentals(db: Session = Depends(get_db)): result = db.execute(text("SELECT id, customer_id, car_id, status FROM rentals LIMIT 10")).mappings().all() return {"rentals": result}

Скрипт наполнения данными (seed.py) Я специально сохраняю координаты в start_location через запятую. Это нужно, чтобы в SQL-запросе 9а легко извлечь lat и lon и вычислить дистанцию по формуле из задания.
Файл seed.py

import os import random from datetime import datetime, timedelta import psycopg2 from psycopg2.extras import execute_values from faker import Faker

fake = Faker('ru_RU')

--- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К БД ---
DB_HOST = "db" DB_PORT = "5432" DB_NAME = "carsharing_db" DB_USER = "postgres" DB_PASS = "postgres"

--- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ГЕНЕРАЦИИ ---
CATEGORIES = [ ('Эконом', 500, 15000), ('Стандарт', 800, 15000), ('Бизнес', 2000, 10000), ('Внедорожник', 1800, 20000), ('Минивэн', 1200, 20000) ]

NUM_SPAWN_POINTS = 30 NUM_CARS = 200 NUM_CUSTOMERS = 1000 NUM_RENTALS = 10000 NUM_ACCIDENTS = 500 NUM_MAINTENANCE = 400

DATE_START = datetime(2023, 1, 1) DATE_END = datetime(2026, 1, 1)

--------------------------------------
def get_connection(): return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data(): conn = get_connection() cursor = conn.cursor() print("Генерация данных для каршеринга...")

# 1. Categories
execute_values(cursor, "INSERT INTO car_categories (name, price_per_hour, maintenance_km_threshold) VALUES %s", CATEGORIES)
cursor.execute("SELECT id, price_per_hour FROM car_categories;")
categories_info = cursor.fetchall() # [(id, price), ...]
cat_ids = [c[0] for c in categories_info]

# 2. Spawn points
spawn_points_data = []
for i in range(1, NUM_SPAWN_POINTS + 1):
    lat = round(random.uniform(55.6000000, 55.8000000), 7)
    lon = round(random.uniform(37.5000000, 37.7000000), 7)
    spawn_points_data.append((
        f"Парковка {i} ({fake.street_name()})", fake.address(), lat, lon, 'Москва'
    ))
execute_values(cursor, "INSERT INTO spawn_points (name, address, lat, lon, city) VALUES %s", spawn_points_data)
cursor.execute("SELECT id FROM spawn_points;")
spawn_ids = [row[0] for row in cursor.fetchall()]

# 3. Cars
colors = ['Белый', 'Черный', 'Серый', 'Красный', 'Синий', 'Зеленый']
brands_models = [('Kia', 'Rio'), ('Hyundai', 'Solaris'), ('Toyota', 'Camry'), ('BMW', '5 Series'), ('Haval', 'Jolion'), ('Chery', 'Tiggo 7')]

cars_data = []
for i in range(NUM_CARS):
    brand, model = random.choice(brands_models)
    # Искусственно делаем у части машин пробег > 20000 для запроса 9б
    mileage = random.randint(500, 80000) if i < (NUM_CARS - 20) else random.randint(25000, 80000)
    cars_data.append((
        brand, model, random.randint(2018, 2025), random.choice(cat_ids),
        random.choice(colors), fake.unique.bothify(text='?###??77', letters='АВЕКМНОРСТУХ'),
        mileage, random.choice(spawn_ids), random.choice(['available', 'rented', 'maintenance'])
    ))
execute_values(cursor, "INSERT INTO cars (brand, model, year, category_id, color, license_plate, mileage, spawn_point_id, status) VALUES %s", cars_data)
cursor.execute("SELECT id, category_id FROM cars;")
cars_records = cursor.fetchall()
car_ids = [c[0] for c in cars_records]

# 4. Customers
customers_data = []
for _ in range(NUM_CUSTOMERS):
    customers_data.append((
        fake.first_name(), fake.last_name(), fake.unique.email()[:100],
        fake.phone_number()[:20], fake.unique.bothify(text='## ?? ######', letters='АВЕКМНОРСТУХ'),
        fake.date_of_birth(minimum_age=18, maximum_age=70)
    ))
execute_values(cursor, "INSERT INTO customers (first_name, last_name, email, phone, license_number, birth_date) VALUES %s RETURNING id", customers_data)

# Резервируем одного клиента-лихача для запроса 10
bad_customer_id = cursor.fetchall()[0][0]
cursor.execute("SELECT id FROM customers;")
customer_ids = [row[0] for row in cursor.fetchall()]

# 5. Rentals
rentals_data = []
price_map = dict(categories_info)
car_cat_map = dict(cars_records)

for _ in range(NUM_RENTALS):
    c_id = random.choice(customer_ids)
    car_id = random.choice(car_ids)
    status = random.choice(['active', 'completed', 'cancelled'])

    start_time = fake.date_time_between(start_date=DATE_START, end_date=DATE_END)
    hours = random.randint(1, 48)
    end_time = start_time + timedelta(hours=hours) if status == 'completed' else None

    # Специальный формат для запроса 9а: сохраняем координаты через запятую
    start_lat = round(random.uniform(55.6000000, 55.8000000), 7)
    start_lon = round(random.uniform(37.5000000, 37.7000000), 7)
    start_loc = f"{start_lat},{start_lon}"

    end_loc = f"{round(random.uniform(55.6, 55.8), 7)},{round(random.uniform(37.5, 37.7), 7)}"

    cat_id = car_cat_map[car_id]
    total_price = float(price_map[cat_id] * hours) if status == 'completed' else None

    rentals_data.append((c_id, car_id, start_time, end_time, start_loc, end_loc, total_price, status))

execute_values(cursor, "INSERT INTO rentals (customer_id, car_id, start_time, end_time, start_location, end_location, total_price, status) VALUES %s RETURNING id, customer_id, car_id", rentals_data)

# 6. Accidents
rentals_records = cursor.fetchall()
completed_rentals = [r for r in rentals_records] # id, cust_id, car_id

accidents_data = []
# Гарантируем "гонщику" более 3 аварий
bad_rentals = [r for r in completed_rentals if r[1] == bad_customer_id]
for r in bad_rentals[:4]:
    accidents_data.append((r[1], r[2], r[0], fake.date_time_between(start_date=DATE_START, end_date=DATE_END), fake.address(), "Серьезное ДТП", random.randint(10000, 50000)))

# Остальные аварии
remaining = NUM_ACCIDENTS - len(accidents_data)
for r in random.sample(completed_rentals, remaining):
    accidents_data.append((r[1], r[2], r[0], fake.date_time_between(start_date=DATE_START, end_date=DATE_END), fake.address(), fake.text(max_nb_chars=50), random.randint(1000, 20000)))

execute_values(cursor, "INSERT INTO accidents (customer_id, car_id, rental_id, accident_date, location, description, fine_amount) VALUES %s", accidents_data)

# 7. Maintenance
maintenance_data = []
for _ in range(NUM_MAINTENANCE):
    car_id = random.choice(car_ids)
    maintenance_data.append((
        car_id, fake.date_between(start_date='-2y', end_date='today'),
        "Плановое ТО", random.randint(5000, 30000), random.randint(10000, 60000)
    ))
execute_values(cursor, "INSERT INTO maintenance_records (car_id, service_date, description, cost, mileage_at_service) VALUES %s", maintenance_data)

conn.commit()
cursor.close()
conn.close()
print("Генерация данных завершена!")
if name == "main": seed_data()

Инструкция по запуску В терминале Ubuntu в папке с проектом выполни: docker compose up -d --build
Провались в контейнер app для генерации данных: docker compose exec app bash

Запусти скрипт наполнения: python seed.py

Выйди: exit. Проверка: База (pgAdmin): http://localhost:5050 (почта admin@admin.com, пароль admin). Добавь сервер db, логин postgres, пароль postgres, БД carsharing_db. API: http://localhost:8000/docs 6. DQL-запросы (10 штук) для отчета Запрос 1 — Базовый SELECT Вывести все доступные автомобили категорий 'Бизнес' или 'Внедорожник' выпуска с 2020 года. Цвет должен не быть 'Белый' или 'Серый'. Отсортировать по году выпуска по убыванию, затем по марке. Конструкции: JOIN (для имени категории), WHERE, IN, AND, NOT IN, >=, ORDER BY Запрос:

SELECT c.brand, c.model, c.year, c.color, cat.name AS category FROM cars c JOIN car_categories cat ON c.category_id = cat.id WHERE c.status = 'available' AND cat.name IN ('Бизнес', 'Внедорожник') AND c.year >= 2020 AND c.color NOT IN ('Белый', 'Серый') ORDER BY c.year DESC, c.brand ASC;

Запрос 2 — Базовый SELECT Вывести все аренды со статусом 'completed', завершившиеся в периоде 01.01.2025 — 30.06.2025 и стоимостью от 1 000 до 10 000 руб. Отсортировать по стоимости по убыванию. Конструкции: WHERE, AND, BETWEEN, =, ORDER BY Запрос:

SELECT id, start_time, end_time, total_price FROM rentals WHERE status = 'completed' AND end_time BETWEEN '2025-01-01' AND '2025-06-30' AND total_price BETWEEN 1000 AND 10000 ORDER BY total_price DESC;

Запрос 3 — GROUP BY Для каждой категории автомобилей вычислить: количество машин, средний пробег, минимальный и максимальный пробег. Отсортировать по среднему пробегу по убыванию. Конструкции: JOIN, GROUP BY, COUNT, AVG, MIN, MAX, ROUND Запрос:

SELECT cat.name AS category, COUNT(c.id) AS cars_count, ROUND(AVG(c.mileage), 2) AS avg_mileage, MIN(c.mileage) AS min_mileage, MAX(c.mileage) AS max_mileage FROM car_categories cat JOIN cars c ON cat.id = c.category_id GROUP BY cat.id, cat.name ORDER BY avg_mileage DESC;

Запрос 4 — GROUP BY + HAVING Найти автомобили, которые сдавались в аренду более 20 раз и принесли суммарный доход более 50 000 руб. Вывести: car_id, марку, модель, количество аренд, суммарный доход. Конструкции: JOIN, GROUP BY, HAVING, COUNT, SUM Запрос:

SELECT c.id AS car_id, c.brand, c.model, COUNT(r.id) AS rental_count, SUM(r.total_price) AS total_revenue FROM cars c JOIN rentals r ON c.id = r.car_id WHERE r.status = 'completed' GROUP BY c.id, c.brand, c.model HAVING COUNT(r.id) > 20 AND SUM(r.total_price) > 50000 ORDER BY total_revenue DESC;

Запрос 5 — INNER JOIN Вывести список завершённых аренд с полями: имя и фамилия клиента, марка и модель автомобиля, категория, начало и конец аренды, стоимость. Отсортировать по дате начала аренды по убыванию. Конструкции: INNER JOIN (4 таблицы), WHERE, ORDER BY Запрос:

SELECT cust.first_name || ' ' || cust.last_name AS customer_name, c.brand || ' ' || c.model AS car_info, cat.name AS category, r.start_time, r.end_time, r.total_price FROM rentals r INNER JOIN customers cust ON r.customer_id = cust.id INNER JOIN cars c ON r.car_id = c.id INNER JOIN car_categories cat ON c.category_id = cat.id WHERE r.status = 'completed' ORDER BY r.start_time DESC;

Запрос 6 — LEFT JOIN Вывести все точки выдачи с количеством автомобилей, закреплённых за каждой. Включить точки без автомобилей. Отсортировать по количеству автомобилей по убыванию. Конструкции: LEFT JOIN, COUNT, GROUP BY, ORDER BY Запрос:

SELECT sp.name, sp.address, COUNT(c.id) AS cars_count FROM spawn_points sp LEFT JOIN cars c ON sp.id = c.spawn_point_id GROUP BY sp.id, sp.name, sp.address ORDER BY cars_count DESC;

Запрос 7 — Смешанное соединение Вывести всех клиентов, бравших автомобиль в аренду, с суммарными расходами на аренду и общей суммой штрафов. (Примечание: Запрос использует INNER JOIN с rentals и LEFT JOIN с accidents по rental_id, что предотвращает дублирование сумм, как и требует бизнес-логика). Конструкции: INNER JOIN, LEFT JOIN, GROUP BY, SUM, COALESCE Запрос:

SELECT cust.first_name, cust.last_name, SUM(r.total_price) AS total_rent_spent, COALESCE(SUM(a.fine_amount), 0) AS total_fines FROM customers cust INNER JOIN rentals r ON cust.id = r.customer_id LEFT JOIN accidents a ON r.id = a.rental_id WHERE r.status = 'completed' GROUP BY cust.id, cust.first_name, cust.last_name ORDER BY total_rent_spent DESC;

Запрос 8 — UNION Создать единый список событий для автомобиля с car_id = 1 (Аренда + ТО). Объединить, отсортировать по дате. Конструкции: UNION, литеральные столбцы, JOIN, ORDER BY Запрос:

SELECT start_time AS event_date, 'Аренда' AS event_type, c.first_name || ' ' || c.last_name AS description FROM rentals r JOIN customers c ON r.customer_id = c.id WHERE r.car_id = 1 UNION SELECT service_date AS event_date, 'ТО' AS event_type, description FROM maintenance_records WHERE car_id = 1 ORDER BY event_date ASC;

Запрос 9 — Комплексный SELECT №1 ⭐

9а. Самая популярная точка выдачи в радиусе 1 км. (Мы извлекаем lat и lon из текстового поля start_location, где скрипт сохранил их через запятую, и считаем дистанцию). Запрос 9a:

SELECT sp.name, sp.address, COUNT(r.id) AS rentals_in_1km_radius FROM spawn_points sp JOIN rentals r ON 1=1 WHERE r.start_location IS NOT NULL AND SQRT( POWER((sp.lat - CAST(SPLIT_PART(r.start_location, ',', 1) AS NUMERIC)) * 111.0, 2) + POWER((sp.lon - CAST(SPLIT_PART(r.start_location, ',', 2) AS NUMERIC)) * 111.0 * COS(RADIANS(sp.lat)), 2) ) <= 1.0 GROUP BY sp.id, sp.name, sp.address ORDER BY rentals_in_1km_radius DESC LIMIT 1;

9б. Автомобили, требующие планового ТО. Запрос 9б:

SELECT cat.name AS category, c.brand, c.model, c.license_plate, c.mileage, cat.maintenance_km_threshold FROM cars c JOIN car_categories cat ON c.category_id = cat.id WHERE c.mileage > cat.maintenance_km_threshold ORDER BY c.mileage DESC;

Запрос 10 — Комплексный SELECT №2 ⭐ Найти автомобилиста с наибольшим суммарным количеством аварий и штрафов. Вывести список мест через запятую. Конструкции: JOIN, GROUP BY, COUNT, SUM, ORDER BY DESC, LIMIT, STRING_AGG Запрос:

SELECT cust.first_name || ' ' || cust.last_name AS customer_name, COUNT(a.id) AS accidents_count, SUM(a.fine_amount) AS total_fines, STRING_AGG(a.location, ', ') AS accident_locations FROM customers cust JOIN accidents a ON cust.id = a.customer_id GROUP BY cust.id, customer_name ORDER BY accidents_count DESC, total_fines DESC LIMIT 1;