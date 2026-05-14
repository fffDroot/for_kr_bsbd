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
