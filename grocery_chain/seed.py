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