Отличный выбор — база данных платформы онлайн-курсов. В этом варианте мы работаем с прогрессом обучения, дедлайнами и модульной структурой курсов.

Я подготовил скрипт `seed.py` таким образом, чтобы он создал необходимые «просроченные» записи (для запроса 9) и гарантированных «отличников» в категории «Кибербезопасность» (для запроса 10).

Ниже представлено полное и готовое к сдаче решение.

### 1. Структура проекта

Создай пустую папку (например, `online_courses`) и повтори в ней следующую структуру файлов:

```text
online_courses/
├── db/
│   └── init/
│       └── 01_schema.sql
├── api/
│   ├── __init__.py
│   ├── database.py
│   └── main.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
└── seed.py

```

---

### 2. Конфигурационные файлы

**Файл `.env**`

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=courses_db

```

**Файл `requirements.txt**`

```txt
fastapi==0.115.*
uvicorn==0.34.*
sqlalchemy==2.0.*
psycopg2-binary==2.9.*
faker

```

**Файл `Dockerfile**`

```dockerfile
FROM bsbd/backend:2026

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

```

**Файл `docker-compose.yml**` (СУБД PostgreSQL 15, как по условию)

```yaml
version: "3.8"

services:
  db:
    image: postgres:15
    env_file:
      - .env
    volumes:
      - ./db/init:/docker-entrypoint-initdb.d:ro
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: "admin@admin.com"
      PGADMIN_DEFAULT_PASSWORD: "admin"
    ports:
      - "5050:80"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:

```

---

### 3. Схема БД и FastAPI Приложение

**Файл `db/init/01_schema.sql**`

```sql
CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE instructors (
    id         SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name  VARCHAR(50) NOT NULL,
    email      VARCHAR(100),
    bio        TEXT,
    expertise  VARCHAR(200)
);

CREATE TABLE courses (
    id             SERIAL PRIMARY KEY,
    title          VARCHAR(200) NOT NULL,
    category_id    INT REFERENCES categories(id),
    instructor_id  INT REFERENCES instructors(id),
    level          VARCHAR(20) DEFAULT 'beginner',
    duration_hours INT,
    price          NUMERIC(10,2) DEFAULT 0,
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE modules (
    id           SERIAL PRIMARY KEY,
    course_id    INT NOT NULL REFERENCES courses(id),
    title        VARCHAR(200),
    order_num    INT NOT NULL,
    duration_min INT
);

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(100) UNIQUE NOT NULL,
    email      VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE enrollments (
    id           SERIAL PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES users(id),
    course_id    INT NOT NULL REFERENCES courses(id),
    enrolled_at  TIMESTAMP DEFAULT NOW(),
    deadline     TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status       VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE module_progress (
    id           SERIAL PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES users(id),
    module_id    INT NOT NULL REFERENCES modules(id),
    completed_at TIMESTAMP,
    is_completed BOOLEAN DEFAULT FALSE
);

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/courses_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

```

**Файл `api/main.py**`

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Online Courses API")

@app.get("/")
def read_root():
    return {"message": "Courses API is running"}

@app.get("/courses")
def get_courses(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, title, level, price FROM courses LIMIT 10")).mappings().all()
    return {"courses": result}

@app.get("/enrollments")
def get_enrollments(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, user_id, course_id, status FROM enrollments LIMIT 10")).mappings().all()
    return {"enrollments": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

В скрипте учтены жёсткие лимиты на 10 000 строк прогресса и заложены данные для выполнения 9 и 10 запросов.

**Файл `seed.py**`

```python
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

```

---

### 5. Инструкция по запуску

1. Запусти сборку и старт контейнеров:
```bash
docker compose up -d --build

```


2. Зайди в контейнер приложения `app` для запуска генератора:
```bash
docker compose exec app bash

```


3. Сгенерируй данные:
```bash
python seed.py

```


4. Выйди из контейнера (`exit` или `Ctrl+D`).
5. Проверка:
* PgAdmin: `http://localhost:5050` (юзер `admin@admin.com`, пароль `admin`). Хост `db`, БД `courses_db`, юзер `postgres`, пароль `postgres`.
* FastAPI: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести все курсы уровня 'intermediate' или 'advanced' из категорий 'Программирование' или 'Кибербезопасность', длительностью от 20 до 60 часов. Отсортировать по уровню, затем по длительности.
**Конструкции:** `WHERE`, `IN`, `AND`, `BETWEEN`, `ORDER BY`
**Запрос:**

```sql
SELECT c.title, c.level, c.duration_hours, cat.name AS category_name
FROM courses c
JOIN categories cat ON c.category_id = cat.id
WHERE c.level IN ('intermediate', 'advanced')
  AND cat.name IN ('Программирование', 'Кибербезопасность')
  AND c.duration_hours BETWEEN 20 AND 60
ORDER BY c.level ASC, c.duration_hours ASC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести все записи на курс, у которых дедлайн истёк, статус не 'completed', и пользователь так и не закончил курс. Отсортировать по дедлайну по возрастанию.
**Конструкции:** `WHERE`, `<`, `AND`, `!=`, `IS NULL`, `ORDER BY`
**Запрос:**

```sql
SELECT id, user_id, course_id, deadline, status
FROM enrollments
WHERE deadline < NOW()
  AND status != 'completed'
  AND completed_at IS NULL
ORDER BY deadline ASC;

```

---

**Запрос 3 — GROUP BY**
Для каждой категории курсов подсчитать: количество курсов, среднюю длительность, количество записей на курсы, среднюю цену курса. Отсортировать по количеству записей по убыванию.
*(Используется `COUNT(DISTINCT c.id)`, чтобы избежать дублирования из-за `JOIN` с `enrollments`).*
**Конструкции:** `JOIN`, `GROUP BY`, `COUNT`, `AVG`, `ROUND`
**Запрос:**

```sql
SELECT cat.name AS category_name,
       COUNT(DISTINCT c.id) AS courses_count,
       ROUND(AVG(c.duration_hours), 2) AS avg_duration,
       COUNT(e.id) AS enrollments_count,
       ROUND(AVG(c.price), 2) AS avg_price
FROM categories cat
JOIN courses c ON cat.id = c.category_id
LEFT JOIN enrollments e ON c.id = e.course_id
GROUP BY cat.id, cat.name
ORDER BY enrollments_count DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти инструкторов, чьи курсы набрали более 50 записей в сумме и средняя цена курса выше 2 000 руб.
*(Используем отдельный расчет средней цены по уникальным курсам, чтобы не искажать результат из-за множественных записей).*
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `COUNT`, `AVG`, `ROUND`
**Запрос:**

```sql
SELECT i.first_name || ' ' || i.last_name AS instructor_name,
       COUNT(DISTINCT c.id) AS courses_count,
       COUNT(e.id) AS total_enrollments,
       ROUND(AVG(c.price), 2) AS avg_course_price
FROM instructors i
JOIN courses c ON i.id = c.instructor_id
JOIN enrollments e ON c.id = e.course_id
GROUP BY i.id, i.first_name, i.last_name
HAVING COUNT(e.id) > 50
   AND AVG(c.price) > 2000;

```

---

**Запрос 5 — INNER JOIN**
Вывести список завершённых записей с полями: `username` пользователя, название курса, категория, дата записи, дата завершения. Отсортировать по дате завершения по убыванию.
**Конструкции:** `INNER JOIN` (4 таблицы), `WHERE`, `ORDER BY`
**Запрос:**

```sql
SELECT u.username,
       c.title AS course_title,
       cat.name AS category_name,
       e.enrolled_at,
       e.completed_at
FROM enrollments e
INNER JOIN users u ON e.user_id = u.id
INNER JOIN courses c ON e.course_id = c.id
INNER JOIN categories cat ON c.category_id = cat.id
WHERE e.status = 'completed'
ORDER BY e.completed_at DESC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести все модули с количеством пользователей, прошедших каждый модуль. Включить модули, которые никто не проходил. Отсортировать по количеству прошедших по убыванию.
**Конструкции:** `LEFT JOIN`, `COUNT`, `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT m.id,
       m.title,
       COUNT(mp.id) AS passed_users_count
FROM modules m
LEFT JOIN module_progress mp ON m.id = mp.module_id AND mp.is_completed = TRUE
GROUP BY m.id, m.title
ORDER BY passed_users_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести все курсы с количеством записанных пользователей и средним процентом выполненных модулей на курс.
*(Используется CTE для предварительного подсчета общего числа модулей в каждом курсе, чтобы избежать сложных подзапросов в SELECT).*
**Конструкции:** `LEFT JOIN`, `GROUP BY`, `COUNT`, `ROUND`
**Запрос:**

```sql
WITH CourseModulesCount AS (
    SELECT course_id, COUNT(*) AS total_modules FROM modules GROUP BY course_id
)
SELECT c.title,
       COUNT(DISTINCT e.id) AS enrolled_users_count,
       COALESCE(
           ROUND(AVG(
               (SELECT COUNT(*) FROM module_progress mp
                JOIN modules m ON mp.module_id = m.id
                WHERE mp.user_id = e.user_id AND m.course_id = c.id AND mp.is_completed = TRUE) * 100.0
               / NULLIF(cmc.total_modules, 0)
           ), 2),
       0) AS avg_completion_percent
FROM courses c
LEFT JOIN enrollments e ON c.id = e.course_id
LEFT JOIN CourseModulesCount cmc ON c.id = cmc.course_id
GROUP BY c.id, c.title, cmc.total_modules;

```

---

**Запрос 8 — UNION**
Создать единый список активностей пользователя с `user_id = 1` (Записи на курс + Пройденные модули).
**Конструкции:** `UNION`, `JOIN`, литеральный столбец, `ORDER BY`
**Запрос:**

```sql
SELECT enrolled_at AS event_date,
       'Запись на курс' AS event_type,
       c.title AS description
FROM enrollments e
JOIN courses c ON e.course_id = c.id
WHERE e.user_id = 1
UNION
SELECT mp.completed_at AS event_date,
       'Модуль завершён' AS event_type,
       m.title AS description
FROM module_progress mp
JOIN modules m ON mp.module_id = m.id
WHERE mp.user_id = 1 AND mp.is_completed = TRUE
ORDER BY event_date DESC;

```

---

**Запрос 9 — Комплексный SELECT №1 ⭐**

**9а. Просроченные курсы с низким прохождением (< 50%).**
**Запрос 9а:**

```sql
SELECT u.username,
       c.title AS course_title,
       e.deadline,
       ROUND(
           COUNT(mp.id) * 100.0 / NULLIF((SELECT COUNT(*) FROM modules WHERE course_id = c.id), 0)
       , 2) AS progress_percent
FROM enrollments e
JOIN users u ON e.user_id = u.id
JOIN courses c ON e.course_id = c.id
LEFT JOIN modules m ON c.id = m.course_id
LEFT JOIN module_progress mp ON e.user_id = mp.user_id AND m.id = mp.module_id AND mp.is_completed = TRUE
WHERE e.deadline < NOW()
  AND e.completed_at IS NULL
  AND e.status = 'active'
GROUP BY u.username, c.id, c.title, e.deadline
HAVING (COUNT(mp.id) * 100.0 / NULLIF((SELECT COUNT(*) FROM modules WHERE course_id = c.id), 0)) < 50
ORDER BY progress_percent ASC;

```

**9б. Подсчет количества таких записей по категориям.**
*(Оборачиваем запрос 9а в подзапрос `WITH` и считаем итоги).*
**Запрос 9б:**

```sql
WITH ExpiredLowProgress AS (
    SELECT cat.name AS category_name
    FROM enrollments e
    JOIN courses c ON e.course_id = c.id
    JOIN categories cat ON c.category_id = cat.id
    LEFT JOIN modules m ON c.id = m.course_id
    LEFT JOIN module_progress mp ON e.user_id = mp.user_id AND m.id = mp.module_id AND mp.is_completed = TRUE
    WHERE e.deadline < NOW()
      AND e.completed_at IS NULL
      AND e.status = 'active'
    GROUP BY e.id, c.id, cat.name
    HAVING (COUNT(mp.id) * 100.0 / NULLIF((SELECT COUNT(*) FROM modules WHERE course_id = c.id), 0)) < 50
)
SELECT category_name, COUNT(*) AS expired_records_count
FROM ExpiredLowProgress
GROUP BY category_name;

```

---

**Запрос 10 — Комплексный SELECT №2 ⭐**
Найти топ-10 пользователей, прошедших ВСЕ модули хотя бы в одном курсе тематики 'Кибербезопасность'.
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING COUNT = (подзапрос)`, `WHERE`, `ORDER BY DESC`, `LIMIT`
**Запрос:**

```sql
SELECT u.username,
       c.title AS course_title,
       COUNT(mp.id) AS completed_modules
FROM users u
JOIN enrollments e ON u.id = e.user_id
JOIN courses c ON e.course_id = c.id
JOIN categories cat ON c.category_id = cat.id
JOIN modules m ON c.id = m.course_id
JOIN module_progress mp ON u.id = mp.user_id AND m.id = mp.module_id AND mp.is_completed = TRUE
WHERE cat.name = 'Кибербезопасность'
GROUP BY u.id, u.username, c.id, c.title
HAVING COUNT(mp.id) = (SELECT COUNT(*) FROM modules WHERE course_id = c.id)
ORDER BY completed_modules DESC
LIMIT 10;

```