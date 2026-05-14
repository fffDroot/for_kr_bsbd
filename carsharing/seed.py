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
DB_NAME = "carsharing_db"
DB_USER = "postgres"
DB_PASS = "postgres"

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ГЕНЕРАЦИИ ---
CATEGORIES = [
    ('Эконом', 500, 15000),
    ('Стандарт', 800, 15000),
    ('Бизнес', 2000, 10000),
    ('Внедорожник', 1800, 20000),
    ('Минивэн', 1200, 20000)
]

NUM_SPAWN_POINTS = 30
NUM_CARS = 200
NUM_CUSTOMERS = 1000
NUM_RENTALS = 10000
NUM_ACCIDENTS = 500
NUM_MAINTENANCE = 400

DATE_START = datetime(2023, 1, 1)
DATE_END = datetime(2026, 1, 1)
# --------------------------------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных для каршеринга...")

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

if __name__ == "__main__":
    seed_data()