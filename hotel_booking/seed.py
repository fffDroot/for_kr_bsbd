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
