import os
import random
from datetime import datetime, timedelta, date
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker('ru_RU')

# --- НАСТРОЙКИ ---
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "mobile_db"
DB_USER = "postgres"
DB_PASS = "postgres"

NUM_PLANS = 20
NUM_SUBSCRIBERS = 1000
NUM_CALLS = 10000
NUM_SMS = 3000
NUM_INTERNET = 5000
NUM_PAYMENTS = 3000

COUNTRIES = ['Турция', 'Казахстан', 'Беларусь', 'ОАЭ', 'Армения', 'Грузия', 'Египет', 'Китай']
# -----------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных мобильного оператора...")

    # 1. Plans
    plans_data = []
    # Гарантируем тариф для Запроса 1
    plans_data.append(('Супер Безлимит', 900.00, None, None, 1000, False, False, 'Абсолютный безлимит за копейки'))
    # Гарантируем тариф для Запроса 9 (Топ-10 выгодных)
    plans_data.append(('Travel Basic', 500.00, None, 500, 100, True, False, 'Дешевый интернет в роуминге без лишнего'))
    plans_data.append(('Travel Pro', 800.00, None, 1000, 500, True, False, 'Отличный интернет в роуминге'))
    plans_data.append(('Travel VIP', 1500.00, None, 2000, 1000, True, False, 'Для долгих поездок'))

    for _ in range(NUM_PLANS - 4):
        price = round(random.uniform(200, 3000), 2)
        int_gb = random.choice([None, 5, 10, 30, 50])
        calls = random.choice([None, 200, 500, 1000, 2000])
        plans_data.append((
            f"Тариф {fake.word().capitalize()}", price, int_gb, calls, random.randint(0, 1000),
            random.choice([True, False]), random.choice([True, False]), fake.text(max_nb_chars=100)
        ))
    execute_values(cursor, "INSERT INTO plans (name, price, internet_gb, calls_minutes, sms_count, roaming_included, has_extra_services, description) VALUES %s", plans_data)
    cursor.execute("SELECT id FROM plans;")
    plan_ids = [row[0] for row in cursor.fetchall()]

    # 2. Subscribers
    subs_data = []
    # Для Запроса 2: Москва/Питер, 2023-2024 год, префиксы +7916 / +7985
    for _ in range(50):
        prefix = random.choice(['+7916', '+7985'])
        reg_date = fake.date_between(start_date=date(2023, 1, 1), end_date=date(2024, 12, 31))
        subs_data.append((
            fake.first_name(), fake.last_name(), f"{prefix}{fake.unique.numerify('#######')}",
            random.choice(plan_ids), reg_date, random.choice(['Москва', 'Санкт-Петербург'])
        ))

    for _ in range(NUM_SUBSCRIBERS - 50):
        subs_data.append((
            fake.first_name(), fake.last_name(), f"+79{fake.unique.numerify('########')}",
            random.choice(plan_ids), fake.date_between(start_date='-5y', end_date='today'), fake.city()
        ))
    execute_values(cursor, "INSERT INTO subscribers (first_name, last_name, phone_number, plan_id, registration_date, city) VALUES %s", subs_data)
    cursor.execute("SELECT id, phone_number FROM subscribers;")
    subs_records = cursor.fetchall()
    sub_ids = [s[0] for s in subs_records]

    # 3. Calls (10000: 70% local, 20% roaming, 10% int)
    calls_data = []
    for _ in range(NUM_CALLS):
        caller_id = random.choice(sub_ids)
        r = random.random()

        if r < 0.70: # Local (inside network)
            call_type = 'local'
            callee_id = random.choice(sub_ids)
            while callee_id == caller_id: callee_id = random.choice(sub_ids)
            callee_phone = None
            dest = 'Россия'
        elif r < 0.90: # Roaming
            call_type = 'roaming'
            callee_id = random.choice([random.choice(sub_ids), None])
            callee_phone = None if callee_id else f"+{fake.numerify('###########')}"
            dest = random.choice(COUNTRIES)
        else: # International
            call_type = 'international'
            callee_id = None
            callee_phone = f"+{fake.numerify('###########')}"
            dest = random.choice(COUNTRIES)

        dur = random.randint(10, 3600)
        start_time = fake.date_time_between(start_date='-2y', end_date='now')
        calls_data.append((caller_id, callee_id, callee_phone, start_time, dur, call_type, dest))

    execute_values(cursor, "INSERT INTO calls (caller_id, callee_id, callee_phone, start_time, duration_sec, call_type, destination_country) VALUES %s", calls_data)

    # 4. SMS
    sms_data = []
    for _ in range(NUM_SMS):
        sender = random.choice(sub_ids)
        if random.random() < 0.8:
            recv_id = random.choice(sub_ids)
            recv_phone, dest = None, 'Россия'
        else:
            recv_id = None
            recv_phone = f"+{fake.numerify('###########')}"
            dest = random.choice(COUNTRIES)

        sms_data.append((sender, recv_id, recv_phone, fake.date_time_between(start_date='-2y', end_date='now'), dest))
    execute_values(cursor, "INSERT INTO sms_messages (sender_id, receiver_id, receiver_phone, sent_at, destination_country) VALUES %s", sms_data)

    # 5. Internet Usage
    net_data = []
    for _ in range(NUM_INTERNET):
        net_data.append((random.choice(sub_ids), fake.date_between(start_date='-2y', end_date='today'), random.randint(10, 5000)))
    execute_values(cursor, "INSERT INTO internet_usage (subscriber_id, usage_date, data_used_mb) VALUES %s", net_data)

    # 6. Payments
    pay_data = []
    for _ in range(NUM_PAYMENTS):
        pay_data.append((random.choice(sub_ids), round(random.uniform(100, 2000), 2), fake.date_time_between(start_date='-2y', end_date='now'), 'Оплата по тарифу'))
    execute_values(cursor, "INSERT INTO payments (subscriber_id, amount, payment_date, description) VALUES %s", pay_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных успешно завершена!")

if __name__ == "__main__":
    seed_data()
