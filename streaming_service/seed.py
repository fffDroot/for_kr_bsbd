import os
import random
from datetime import date, timedelta
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker('ru_RU')

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К БД ---
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "streaming_db"
DB_USER = "postgres"
DB_PASS = "postgres"

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ГЕНЕРАЦИИ ---
CATEGORIES = [
    'Боевик', 'Комедия', 'Драма', 'Триллер', 'Ужасы',
    'Документальный', 'Фантастика', 'Фэнтези', 'Мелодрама', 'Детектив',
    'Мультфильм', 'Аниме', 'Мюзикл', 'Исторический', 'Спорт'
]

NUM_CONTENT_TOTAL = 500
CONTENT_MOVIES = 300
CONTENT_SERIES = 200
YEAR_START = 2010
YEAR_END = 2025

SEASONS_MIN = 2
SEASONS_MAX = 5
EPISODES_PER_SEASON_MIN = 8
EPISODES_PER_SEASON_MAX = 12

NUM_USERS = 1000
SUBSCRIPTION_TYPES = ['free', 'standard', 'premium']
SUBSCRIPTION_WEIGHTS = [0.3, 0.5, 0.2] # 30%, 50%, 20%

NUM_VIEWINGS = 10000
VIEWING_DATE_START = date(2023, 1, 1)
VIEWING_DATE_END = date(2026, 12, 31)

NUM_RATINGS = 4000
NUM_COMMENTS = 3000
# --------------------------------------

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных для стриминга...")

    # 1. Categories
    cat_data = [(name, fake.text(max_nb_chars=100)) for name in CATEGORIES]
    execute_values(cursor, "INSERT INTO categories (name, description) VALUES %s", cat_data)

    cursor.execute("SELECT id FROM categories;")
    category_ids = [row[0] for row in cursor.fetchall()]

    # 2. Content (Movies + Series)
    content_data = []
    # Movies
    for _ in range(CONTENT_MOVIES):
        content_data.append((
            fake.catch_phrase(), random.choice(category_ids), 'movie',
            random.randint(YEAR_START, YEAR_END), random.randint(70, 180), fake.text(max_nb_chars=200)
        ))
    # Series
    for _ in range(CONTENT_SERIES):
        content_data.append((
            fake.catch_phrase(), random.choice(category_ids), 'series',
            random.randint(YEAR_START, YEAR_END), None, fake.text(max_nb_chars=200)
        ))

    execute_values(cursor, "INSERT INTO content (title, category_id, content_type, release_year, duration_min, description) VALUES %s", content_data)

    # 3. Episodes
    cursor.execute("SELECT id FROM content WHERE content_type = 'series';")
    series_ids = [row[0] for row in cursor.fetchall()]

    episodes_data = []
    for s_id in series_ids:
        seasons = random.randint(SEASONS_MIN, SEASONS_MAX)
        for season in range(1, seasons + 1):
            episodes = random.randint(EPISODES_PER_SEASON_MIN, EPISODES_PER_SEASON_MAX)
            for ep in range(1, episodes + 1):
                episodes_data.append((
                    s_id, season, ep, f"Эпизод {ep}", random.randint(20, 60), fake.date_between(start_date='-5y', end_date='today')
                ))
    execute_values(cursor, "INSERT INTO episodes (content_id, season_num, episode_num, title, duration_min, release_date) VALUES %s", episodes_data)

    # 4. Users
    users_data = []
    for _ in range(NUM_USERS):
        sub_type = random.choices(SUBSCRIPTION_TYPES, weights=SUBSCRIPTION_WEIGHTS, k=1)[0]
        users_data.append((
            fake.unique.user_name(), fake.unique.email(), sub_type, fake.country()
        ))
    execute_values(cursor, "INSERT INTO users (username, email, subscription_type, country) VALUES %s", users_data)

    # 5. Viewings (10000 строк)
    cursor.execute("SELECT id FROM users;")
    user_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT id, content_type FROM content;")
    content_list = cursor.fetchall() # (id, 'movie'/'series')

    cursor.execute("SELECT id, content_id FROM episodes;")
    episodes_map = {}
    for ep_id, c_id in cursor.fetchall():
        if c_id not in episodes_map: episodes_map[c_id] = []
        episodes_map[c_id].append(ep_id)

    viewings_data = []
    for _ in range(NUM_VIEWINGS):
        u_id = random.choice(user_ids)
        c_id, c_type = random.choice(content_list)

        ep_id = None
        if c_type == 'series' and c_id in episodes_map:
            ep_id = random.choice(episodes_map[c_id])

        viewed_at = fake.date_time_between_dates(datetime_start=VIEWING_DATE_START, datetime_end=VIEWING_DATE_END)
        watch_dur = random.randint(10, 150)
        is_comp = random.choice([True, False])

        viewings_data.append((u_id, c_id, ep_id, viewed_at, watch_dur, is_comp))

    execute_values(cursor, "INSERT INTO viewings (user_id, content_id, episode_id, viewed_at, watch_duration_min, is_completed) VALUES %s", viewings_data)

    # 6. Ratings
    ratings_data = []
    for _ in range(NUM_RATINGS):
        u_id = random.choice(user_ids)
        c_id = random.choice(content_list)[0]
        score = round(random.uniform(1.0, 10.0), 1)
        ratings_data.append((u_id, c_id, score))
    execute_values(cursor, "INSERT INTO ratings (user_id, content_id, score) VALUES %s", ratings_data)

    # 7. Comments
    comments_data = []
    for _ in range(NUM_COMMENTS):
        u_id = random.choice(user_ids)
        c_id = random.choice(content_list)[0]
        comments_data.append((u_id, c_id, fake.text(max_nb_chars=random.randint(50, 500))))
    execute_values(cursor, "INSERT INTO comments (user_id, content_id, comment_text) VALUES %s", comments_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных завершена!")

if __name__ == "__main__":
    seed_data()
