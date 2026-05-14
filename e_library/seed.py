import os
import random
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker('ru_RU')

# --- НАСТРОЙКИ ---
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "library_db"
DB_USER = "postgres"
DB_PASS = "postgres"

NUM_AUTHORS = 100
NUM_CATEGORIES = 20
NUM_BOOKS = 500
NUM_USERS = 1000
NUM_SESSIONS = 10000
NUM_REVIEWS = 3000
NUM_BOOKMARKS = 2000

MAIN_CATEGORIES = ['Фантастика', 'Детектив', 'Роман', 'Наука', 'История', 'Фэнтези', 'Биография']
# -----------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных электронной библиотеки...")

    # 1. Authors
    authors_data = []
    for _ in range(NUM_AUTHORS):
        authors_data.append((
            fake.first_name(), fake.last_name(), fake.country(),
            random.randint(1800, 1995), fake.text(max_nb_chars=150)
        ))
    execute_values(cursor, "INSERT INTO authors (first_name, last_name, nationality, birth_year, biography) VALUES %s RETURNING id", authors_data)
    author_ids = [row[0] for row in cursor.fetchall()]

    # 2. Categories
    cat_data = []
    # Основные категории
    for name in MAIN_CATEGORIES:
        cat_data.append((name, f"Описание категории {name}", None))
    execute_values(cursor, "INSERT INTO categories (name, description, parent_id) VALUES %s RETURNING id", cat_data)
    parent_ids = [row[0] for row in cursor.fetchall()]

    # Подкатегории
    subcat_data = []
    for _ in range(NUM_CATEGORIES - len(MAIN_CATEGORIES)):
        subcat_data.append((fake.word().capitalize(), fake.text(max_nb_chars=50), random.choice(parent_ids)))
    execute_values(cursor, "INSERT INTO categories (name, description, parent_id) VALUES %s RETURNING id", subcat_data)
    all_cat_ids = parent_ids + [row[0] for row in cursor.fetchall()]

    # 3. Books
    books_data = []
    for _ in range(NUM_BOOKS):
        books_data.append((
            fake.catch_phrase(), random.choice(author_ids), random.choice(all_cat_ids),
            fake.isbn13(), random.randint(1900, 2024), random.randint(100, 1200), fake.text(max_nb_chars=200)
        ))
    execute_values(cursor, "INSERT INTO books (title, author_id, category_id, isbn, publication_year, pages, description) VALUES %s RETURNING id, pages", books_data)
    books_records = cursor.fetchall()
    book_ids = [b[0] for b in books_records]
    book_pages_map = dict(books_records)

    # 4. Users
    users_data = []
    subs = ['free', 'basic', 'premium']
    for _ in range(NUM_USERS):
        username = fake.unique.user_name()
        # Для запроса 2 гарантируем, что часть юзеров не начинается с цифры
        while username[0].isdigit():
            username = fake.unique.user_name()

        users_data.append((
            username, fake.unique.email(), random.choice(subs),
            fake.date_time_between(start_date='-3y', end_date='now')
        ))
    execute_values(cursor, "INSERT INTO users (username, email, subscription_type, created_at) VALUES %s RETURNING id", users_data)
    user_ids = [row[0] for row in cursor.fetchall()]

    # 5. Reading Sessions (10 000 строк)
    sessions_data = []
    user_book_read = set() # Для генерации отзывов только от читавших

    for _ in range(NUM_SESSIONS):
        u_id = random.choice(user_ids)
        b_id = random.choice(book_ids)
        user_book_read.add((u_id, b_id))

        start_at = fake.date_time_between(start_date='-2y', end_date='now')
        last_read = start_at + timedelta(days=random.randint(0, 30))

        r = random.random()
        if r < 0.4: # Прочитано полностью
            prog = 100.00
            is_comp = True
        elif r < 0.8: # Брошено / в процессе (важно для Запроса 9б)
            prog = round(random.uniform(1.0, 99.0), 2)
            is_comp = False
        else: # Только открыл
            prog = 0.00
            is_comp = False

        sessions_data.append((u_id, b_id, start_at, last_read, prog, is_comp))
    execute_values(cursor, "INSERT INTO reading_sessions (user_id, book_id, started_at, last_read_at, progress_percent, is_completed) VALUES %s", sessions_data)

    # 6. Reviews
    reviews_data = []
    valid_reviewers = list(user_book_read)
    for _ in range(min(NUM_REVIEWS, len(valid_reviewers))):
        u_id, b_id = random.choice(valid_reviewers)
        reviews_data.append((u_id, b_id, random.randint(1, 5), fake.text(max_nb_chars=150), fake.date_time_between(start_date='-1y', end_date='now')))
    execute_values(cursor, "INSERT INTO reviews (user_id, book_id, rating, comment, created_at) VALUES %s", reviews_data)

    # 7. Bookmarks
    bookmarks_data = []
    for _ in range(NUM_BOOKMARKS):
        u_id, b_id = random.choice(valid_reviewers)
        max_p = book_pages_map[b_id]
        page = random.randint(1, max_p) if max_p > 1 else 1
        bookmarks_data.append((u_id, b_id, page, fake.date_time_between(start_date='-1y', end_date='now')))
    execute_values(cursor, "INSERT INTO bookmarks (user_id, book_id, page_number, created_at) VALUES %s", bookmarks_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных успешно завершена!")

if __name__ == "__main__":
    seed_data()