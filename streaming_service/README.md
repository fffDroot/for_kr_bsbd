### 1. Структура проекта

Создай пустую папку для проекта (например, `streaming_service`) и сделай в ней следующую структуру:

```text
streaming_service/
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
POSTGRES_DB=streaming_db

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

**Файл `docker-compose.yml**`
*В условии указан PostgreSQL 15, поэтому версию образа меняем.*

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

CREATE TABLE content (
    id            SERIAL PRIMARY KEY,
    title         VARCHAR(200) NOT NULL,
    category_id   INT REFERENCES categories(id),
    content_type  VARCHAR(10) CHECK (content_type IN ('movie', 'series')),
    release_year  INT,
    duration_min  INT,
    description   TEXT
);

CREATE TABLE episodes (
    id            SERIAL PRIMARY KEY,
    content_id    INT NOT NULL REFERENCES content(id),
    season_num    INT NOT NULL,
    episode_num   INT NOT NULL,
    title         VARCHAR(200),
    duration_min  INT,
    release_date  DATE
);

CREATE TABLE users (
    id                SERIAL PRIMARY KEY,
    username          VARCHAR(100) UNIQUE NOT NULL,
    email             VARCHAR(100) UNIQUE,
    subscription_type VARCHAR(20) DEFAULT 'free',
    country           VARCHAR(50),
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE viewings (
    id                 SERIAL PRIMARY KEY,
    user_id            INT NOT NULL REFERENCES users(id),
    content_id         INT NOT NULL REFERENCES content(id),
    episode_id         INT REFERENCES episodes(id),
    viewed_at          TIMESTAMP DEFAULT NOW(),
    watch_duration_min INT,
    is_completed       BOOLEAN DEFAULT FALSE
);

CREATE TABLE ratings (
    id         SERIAL PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES users(id),
    content_id INT NOT NULL REFERENCES content(id),
    score      NUMERIC(3,1) CHECK (score BETWEEN 1 AND 10),
    rated_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE comments (
    id           SERIAL PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES users(id),
    content_id   INT NOT NULL REFERENCES content(id),
    comment_text TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/streaming_db"
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

app = FastAPI(title="Streaming API")

@app.get("/")
def read_root():
    return {"message": "Streaming API is running"}

@app.get("/content")
def get_content(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, title, content_type, release_year FROM content LIMIT 10")).mappings().all()
    return {"content": result}

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, username, subscription_type FROM users LIMIT 10")).mappings().all()
    return {"users": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

Я настроил глобальные переменные для гибкости. В логике скрипта учитывается точное маппирование: если контент — это сериал, просмотр связывается со случайным эпизодом этого сериала. Если фильм — `episode_id` равен `NULL`.

**Файл `seed.py**`

```python
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

```

---

### 5. Инструкция по запуску

1. **Запуск контейнеров:**
В терминале Ubuntu в папке проекта выполни команду:
```bash
docker compose up -d --build

```


2. **Вход в контейнер:**
Проваливаемся в контейнер приложения:
```bash
docker compose exec app bash

```


3. **Генерация данных:**
Внутри контейнера запускаем наш скрипт:
```bash
python seed.py

```


*Ожидай сообщение "Генерация данных завершена!".*
4. **Выход:** Нажми `Ctrl+D` (или напиши `exit`), чтобы выйти.
5. **Проверка:**
* БД: `http://localhost:5050` (почта `admin@admin.com`, пароль `admin`). Хост сервера БД: `db`, юзер: `postgres`, база: `streaming_db`.
* API: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести все фильмы (`content_type = 'movie'`) из категорий 'Драма' или 'Триллер', выпущенные в период 2015–2023 года и длительностью более 90 минут. Отсортировать по году выпуска по убыванию.
**Конструкции:** `WHERE`, `AND`, `OR`, `BETWEEN`, `>`, `ORDER BY DESC`
**Запрос:**

```sql
SELECT c.title, c.release_year, c.duration_min, cat.name AS category
FROM content c
JOIN categories cat ON c.category_id = cat.id
WHERE c.content_type = 'movie'
  AND (cat.name = 'Драма' OR cat.name = 'Триллер')
  AND c.release_year BETWEEN 2015 AND 2023
  AND c.duration_min > 90
ORDER BY c.release_year DESC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести пользователей с подпиской 'premium' или 'standard', зарегистрировавшихся в 2024 году, чей `username` начинается не с буквы 'a'. Отсортировать по дате регистрации.
**Конструкции:** `WHERE`, `IN`, `NOT LIKE`, `AND`, `EXTRACT` (или `DATE_PART`), `ORDER BY`
**Запрос:**

```sql
SELECT username, subscription_type, created_at
FROM users
WHERE subscription_type IN ('premium', 'standard')
  AND EXTRACT(YEAR FROM created_at) = 2024
  AND username NOT ILIKE 'a%'
ORDER BY created_at ASC;

```

---

**Запрос 3 — GROUP BY**
Для каждой категории подсчитать: количество единиц контента, среднюю длительность фильмов (`ROUND` до целых), максимальный год выпуска. Отсортировать по количеству контента по убыванию.
**Конструкции:** `GROUP BY`, `COUNT`, `AVG`, `MAX`, `ROUND`, `ORDER BY`
**Запрос:**

```sql
SELECT cat.name AS category_name,
       COUNT(c.id) AS content_count,
       ROUND(AVG(CASE WHEN c.content_type = 'movie' THEN c.duration_min END)) AS avg_movie_duration,
       MAX(c.release_year) AS max_release_year
FROM categories cat
LEFT JOIN content c ON cat.id = c.category_id
GROUP BY cat.name
ORDER BY content_count DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти пользователей, которые поставили более 15 оценок со средним баллом выше 7.0. Вывести: `username`, количество оценок, средний балл (2 знака). Отсортировать по среднему баллу по убыванию.
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `COUNT`, `AVG`, `ROUND`
**Запрос:**

```sql
SELECT u.username,
       COUNT(r.id) AS rating_count,
       ROUND(AVG(r.score), 2) AS avg_score
FROM users u
JOIN ratings r ON u.id = r.user_id
GROUP BY u.id, u.username
HAVING COUNT(r.id) > 15 AND AVG(r.score) > 7.0
ORDER BY avg_score DESC;

```

---

**Запрос 5 — INNER JOIN**
Вывести список оценок с полями: `username` пользователя, название контента, название категории, выставленная оценка. Показывать только оценки выше 8. Отсортировать по оценке по убыванию, затем по названию контента.
**Конструкции:** `INNER JOIN` (4 таблицы: `ratings`, `users`, `content`, `categories`), `WHERE`, `ORDER BY`
**Запрос:**

```sql
SELECT u.username,
       c.title AS content_title,
       cat.name AS category_name,
       r.score
FROM ratings r
INNER JOIN users u ON r.user_id = u.id
INNER JOIN content c ON r.content_id = c.id
INNER JOIN categories cat ON c.category_id = cat.id
WHERE r.score > 8
ORDER BY r.score DESC, c.title ASC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести весь контент из базы данных с количеством просмотров каждой единицы. Включить контент с нулевым количеством просмотров (вывести 0). Отсортировать по количеству просмотров по убыванию.
**Конструкции:** `LEFT JOIN` (таблицы: `content`, `viewings`), `COUNT`, `GROUP BY`
**Запрос:**

```sql
SELECT c.id,
       c.title,
       COUNT(v.id) AS view_count
FROM content c
LEFT JOIN viewings v ON c.id = v.content_id
GROUP BY c.id, c.title
ORDER BY view_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести всех пользователей с подпиской (любой тип, кроме 'free') с суммарным количеством их просмотров и количеством оставленных комментариев (если комментариев нет — 0).
**Конструкции:** `INNER JOIN`, `LEFT JOIN`, `COALESCE`, `GROUP BY`. *(Примечание: используется COUNT(DISTINCT), чтобы избежать "умножения" строк при двойном LEFT JOIN).*
**Запрос:**

```sql
SELECT u.username,
       COUNT(DISTINCT v.id) AS total_views,
       COALESCE(COUNT(DISTINCT c.id), 0) AS total_comments
FROM users u
LEFT JOIN viewings v ON u.id = v.user_id
LEFT JOIN comments c ON u.id = c.user_id
WHERE u.subscription_type != 'free'
GROUP BY u.id, u.username;

```

---

**Запрос 8 — UNION**
Создать единый каталог с полями `title`, `type_label`, `release_year` (фильмы → 'Фильм', сериалы → 'Сериал'). Отсортировать по году выпуска по убыванию, затем по названию.
**Конструкции:** `UNION`, литеральный столбец, `ORDER BY`
**Запрос:**

```sql
SELECT title, 'Фильм' AS type_label, release_year
FROM content WHERE content_type = 'movie'
UNION
SELECT title, 'Сериал' AS type_label, release_year
FROM content WHERE content_type = 'series'
ORDER BY release_year DESC, title ASC;

```

---

**Запрос 9 — Комплексный SELECT №1 ⭐**
Для каждой категории найти самый просматриваемый сериал. Вывести: название категории, название сериала, суммарное количество просмотров. Если в категории нет сериалов с просмотрами — не выводить.
**Конструкции:** CTE (`WITH`), `JOIN`, `GROUP BY`, `COUNT`, оконная функция `ROW_NUMBER() OVER (PARTITION BY ...)`
**Запрос:**

```sql
WITH SeriesViews AS (
    SELECT cat.name AS category_name,
           c.title AS series_title,
           COUNT(v.id) AS total_views,
           ROW_NUMBER() OVER (PARTITION BY cat.id ORDER BY COUNT(v.id) DESC) as rank
    FROM categories cat
    JOIN content c ON cat.id = c.category_id
    JOIN viewings v ON c.id = v.content_id
    WHERE c.content_type = 'series'
    GROUP BY cat.id, cat.name, c.id, c.title
)
SELECT category_name, series_title, total_views
FROM SeriesViews
WHERE rank = 1 AND total_views > 0;

```

---

**Запрос 10 — Комплексный SELECT №2 ⭐**

**10а.** Вывести топ-10 пользователей, которые одновременно: поставили оценку > 4 и написали не менее 10 комментариев. Отсортировать по кол-ву комментариев.
**Конструкции:** Подзапросы в `SELECT` и `WHERE` (чтобы избежать тяжелых джоинов), `ORDER BY`, `LIMIT`
**Запрос 10а:**

```sql
SELECT u.username,
       (SELECT COUNT(*) FROM ratings r WHERE r.user_id = u.id AND r.score > 4) AS ratings_gt_4_count,
       (SELECT COUNT(*) FROM comments c WHERE c.user_id = u.id) AS comments_count
FROM users u
WHERE (SELECT COUNT(*) FROM ratings r WHERE r.user_id = u.id AND r.score > 4) > 0
  AND (SELECT COUNT(*) FROM comments c WHERE c.user_id = u.id) >= 10
ORDER BY comments_count DESC
LIMIT 10;

```

**10б.** Найти пользователя, написавшего суммарно наибольший объём текста комментариев.
**Конструкции:** `JOIN`, `GROUP BY`, `SUM`, `LENGTH`, `ORDER BY`, `LIMIT`
**Запрос 10б:**

```sql
SELECT u.username,
       SUM(LENGTH(c.comment_text)) AS total_text_length
FROM users u
JOIN comments c ON u.id = c.user_id
GROUP BY u.id, u.username
ORDER BY total_text_length DESC
LIMIT 1;

```
