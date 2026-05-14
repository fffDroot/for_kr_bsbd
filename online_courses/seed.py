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
DB_NAME = "courses_db"
DB_USER = "postgres"
DB_PASS = "postgres"

CATEGORIES = ['Программирование', 'Дизайн', 'Кибербезопасность', 'Data Science', 'Маркетинг', 'Менеджмент', 'Языки', 'Аналитика', 'DevOps', 'QA']
LEVELS = ['beginner', 'intermediate', 'advanced']

NUM_INSTRUCTORS = 50
NUM_COURSES = 100
NUM_USERS = 500
NUM_ENROLLMENTS = 3000
NUM_PROGRESS_MAX = 10000
# -----------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных для платформы курсов...")

    # 1. Categories
    cat_data = [(name, fake.text(max_nb_chars=100)) for name in CATEGORIES]
    execute_values(cursor, "INSERT INTO categories (name, description) VALUES %s RETURNING id, name", cat_data)
    cat_records = cursor.fetchall()
    cat_map = {name: c_id for c_id, name in cat_records}
    cat_ids = [c_id for c_id, _ in cat_records]

    # 2. Instructors
    inst_data = [(fake.first_name(), fake.last_name(), fake.email()[:100], fake.text(max_nb_chars=150), fake.job()[:200]) for _ in range(NUM_INSTRUCTORS)]
    execute_values(cursor, "INSERT INTO instructors (first_name, last_name, email, bio, expertise) VALUES %s RETURNING id", inst_data)
    inst_ids = [row[0] for row in cursor.fetchall()]

    # 3. Courses
    courses_data = []
    for _ in range(NUM_COURSES):
        courses_data.append((
            f"Курс: {fake.catch_phrase()}", random.choice(cat_ids), random.choice(inst_ids),
            random.choice(LEVELS), random.randint(5, 80), round(random.uniform(0, 15000), 2),
            fake.date_time_between(start_date='-3y', end_date='-1y')
        ))
    execute_values(cursor, "INSERT INTO courses (title, category_id, instructor_id, level, duration_hours, price, created_at) VALUES %s RETURNING id, category_id", courses_data)
    courses_records = cursor.fetchall()
    course_ids = [c[0] for c in courses_records]

    # 4. Modules
    modules_data = []
    for c_id in course_ids:
        num_mods = random.randint(5, 12)
        for m_num in range(1, num_mods + 1):
            modules_data.append((c_id, f"Модуль {m_num}: {fake.word()}", m_num, random.randint(30, 180)))
    execute_values(cursor, "INSERT INTO modules (course_id, title, order_num, duration_min) VALUES %s RETURNING id, course_id", modules_data)

    course_modules = {}
    for m_id, c_id in cursor.fetchall():
        course_modules.setdefault(c_id, []).append(m_id)

    # 5. Users
    users_data = [(fake.unique.user_name(), fake.unique.email(), fake.date_time_between(start_date='-3y', end_date='-1m')) for _ in range(NUM_USERS)]
    execute_values(cursor, "INSERT INTO users (username, email, created_at) VALUES %s RETURNING id", users_data)
    user_ids = [row[0] for row in cursor.fetchall()]

    # 6. Enrollments & Module Progress
    enrollments_data = []
    progress_data = []

    cyber_cat_id = cat_map['Кибербезопасность']
    cyber_courses = [c[0] for c in courses_records if c[1] == cyber_cat_id]

    # Генерируем данные с учетом лимита в 10 000 строк для прогресса
    for i in range(NUM_ENROLLMENTS):
        u_id = random.choice(user_ids)
        c_id = random.choice(course_ids)

        # Защита от дублей записи на один курс
        if (u_id, c_id) in [(e[0], e[1]) for e in enrollments_data]: continue

        enrolled_at = fake.date_time_between(start_date='-2y', end_date='-1m')

        r = random.random()
        # Для Запроса 10: "Отличники" по Кибербезопасности
        if r < 0.05 and c_id in cyber_courses and len(progress_data) + len(course_modules[c_id]) <= NUM_PROGRESS_MAX:
            deadline = enrolled_at + timedelta(days=90)
            completed_at = enrolled_at + timedelta(days=random.randint(10, 80))
            status = 'completed'
            enrollments_data.append((u_id, c_id, enrolled_at, deadline, completed_at, status))
            for m_id in course_modules[c_id]:
                progress_data.append((u_id, m_id, completed_at - timedelta(days=random.randint(1, 5)), True))

        # Для Запроса 9: Просроченные курсы, прогресс < 50%
        elif r < 0.20 and len(progress_data) + len(course_modules[c_id]) // 3 <= NUM_PROGRESS_MAX:
            deadline = fake.date_time_between(start_date='-6m', end_date='-1d') # В прошлом
            status = 'active'
            enrollments_data.append((u_id, c_id, enrolled_at, deadline, None, status))

            mods = course_modules[c_id]
            pass_count = random.randint(0, (len(mods) // 2) - 1) # Меньше 50%
            for m_id in mods[:pass_count]:
                progress_data.append((u_id, m_id, enrolled_at + timedelta(days=random.randint(1, 10)), True))

        # Обычные активные или завершенные
        else:
            deadline = enrolled_at + timedelta(days=90)
            status = random.choice(['active', 'completed', 'expired'])
            comp_at = enrolled_at + timedelta(days=40) if status == 'completed' else None
            enrollments_data.append((u_id, c_id, enrolled_at, deadline, comp_at, status))

            # Добавим прогресса, если есть место
            mods = course_modules[c_id]
            p_count = len(mods) if status == 'completed' else random.randint(0, len(mods))
            if len(progress_data) + p_count <= NUM_PROGRESS_MAX:
                for m_id in mods[:p_count]:
                    progress_data.append((u_id, m_id, enrolled_at + timedelta(days=random.randint(1, 20)), True))

    execute_values(cursor, "INSERT INTO enrollments (user_id, course_id, enrolled_at, deadline, completed_at, status) VALUES %s", enrollments_data)
    execute_values(cursor, "INSERT INTO module_progress (user_id, module_id, completed_at, is_completed) VALUES %s", progress_data)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Генерация завершена! Создано записей прогресса: {len(progress_data)}")

if __name__ == "__main__":
    seed_data()
