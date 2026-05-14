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
