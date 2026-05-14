Привет! Переходим к варианту про электронную библиотеку. В этом задании отличная структура для работы со статистикой чтения: есть сессии (с процентом прогресса), отзывы и иерархия категорий.

Я подготовил структуру проекта и написал скрипт генерации данных `seed.py` таким образом, чтобы он создал гарантированный пул «брошенных» книг (для запроса 9б) и обеспечил правильные пересечения для остальных сложных выборок.

Ниже представлено полное, готовое к сдаче решение.

### 1. Структура проекта

Создай пустую папку (например, `e_library`) и настрой внутри неё следующую структуру файлов:

```text
e_library/
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
POSTGRES_DB=library_db

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

**Файл `docker-compose.yml**` (СУБД PostgreSQL 15, порты по условию)

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
CREATE TABLE authors (
    id          SERIAL PRIMARY KEY,
    first_name  VARCHAR(100) NOT NULL,
    last_name   VARCHAR(100) NOT NULL,
    nationality VARCHAR(50),
    birth_year  INT,
    biography   TEXT
);

CREATE TABLE categories (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    parent_id        INT REFERENCES categories(id)
);

CREATE TABLE books (
    id               SERIAL PRIMARY KEY,
    title            VARCHAR(200) NOT NULL,
    author_id        INT NOT NULL REFERENCES authors(id),
    category_id      INT REFERENCES categories(id),
    isbn             VARCHAR(20),
    publication_year INT,
    pages            INT,
    description      TEXT
);

CREATE TABLE users (
    id                SERIAL PRIMARY KEY,
    username          VARCHAR(100) UNIQUE NOT NULL,
    email             VARCHAR(100),
    subscription_type VARCHAR(20) DEFAULT 'free',
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reading_sessions (
    id               SERIAL PRIMARY KEY,
    user_id          INT NOT NULL REFERENCES users(id),
    book_id          INT NOT NULL REFERENCES books(id),
    started_at       TIMESTAMP DEFAULT NOW(),
    last_read_at     TIMESTAMP,
    progress_percent NUMERIC(5,2) DEFAULT 0,
    is_completed     BOOLEAN DEFAULT FALSE
);

CREATE TABLE reviews (
    id         SERIAL PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES users(id),
    book_id    INT NOT NULL REFERENCES books(id),
    rating     INT CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bookmarks (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES users(id),
    book_id     INT NOT NULL REFERENCES books(id),
    page_number INT,
    created_at  TIMESTAMP DEFAULT NOW()
);

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/library_db"
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

app = FastAPI(title="E-Library API")

@app.get("/")
def read_root():
    return {"message": "Library API is running"}

@app.get("/books")
def get_books(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, title, publication_year, pages FROM books LIMIT 10")).mappings().all()
    return {"books": result}

@app.get("/authors")
def get_authors(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, first_name, last_name, nationality FROM authors LIMIT 10")).mappings().all()
    return {"authors": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

Скрипт учитывает требования по генерации данных: 10 000 сессий, брошенные книги, гарантия нужных категорий для Запроса 1 и т.д.

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

```

---

### 5. Инструкция по запуску

1. Сборка и запуск контейнеров:
```bash
docker compose up -d --build

```


2. Подключение к контейнеру с API:
```bash
docker compose exec app bash

```


3. Запуск скрипта генерации:
```bash
python seed.py

```


4. Выход из контейнера: `exit`.
5. Проверка работоспособности:
* База (pgAdmin): `http://localhost:5050` (юзер `admin@admin.com`, пароль `admin`). Хост `db`, логин/пароль `postgres`, БД `library_db`.
* API: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести все книги из категорий 'Фантастика' или 'Детектив', изданные с 2000 по 2020 год, объёмом не менее 300 страниц. Отсортировать по году издания по убыванию, затем по названию.
**Конструкции:** `JOIN`, `WHERE`, `IN`, `AND`, `BETWEEN`, `>=`, `ORDER BY`
**Запрос:**

```sql
SELECT b.title, b.publication_year, b.pages, c.name AS category_name
FROM books b
JOIN categories c ON b.category_id = c.id
WHERE c.name IN ('Фантастика', 'Детектив')
  AND b.publication_year BETWEEN 2000 AND 2020
  AND b.pages >= 300
ORDER BY b.publication_year DESC, b.title ASC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести всех пользователей с подпиской 'premium' или 'basic', зарегистрировавшихся в 2024 году, чей `username` не начинается с цифры. Отсортировать по дате регистрации по убыванию.
**Конструкции:** `WHERE`, `IN`, `AND`, регулярное выражение `!~` (аналог `NOT SIMILAR TO`), `EXTRACT`, `ORDER BY`
**Запрос:**

```sql
SELECT username, email, subscription_type, created_at
FROM users
WHERE subscription_type IN ('premium', 'basic')
  AND EXTRACT(YEAR FROM created_at) = 2024
  AND username !~ '^[0-9]'
ORDER BY created_at DESC;

```

---

**Запрос 3 — GROUP BY**
Для каждой категории подсчитать: количество книг, среднее количество страниц (2 знака), год издания самой ранней и самой поздней книги. Отсортировать по количеству книг по убыванию.
**Конструкции:** `LEFT JOIN`, `GROUP BY`, `COUNT`, `AVG`, `MIN`, `MAX`, `ROUND`
**Запрос:**

```sql
SELECT c.name AS category_name,
       COUNT(b.id) AS books_count,
       ROUND(AVG(b.pages), 2) AS avg_pages,
       MIN(b.publication_year) AS oldest_book_year,
       MAX(b.publication_year) AS newest_book_year
FROM categories c
LEFT JOIN books b ON c.id = b.category_id
GROUP BY c.id, c.name
ORDER BY books_count DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти авторов, у которых более 3 книг в библиотеке со средним рейтингом (по всем их книгам) выше 4.0. Вывести: имя и фамилия автора, количество книг, средний рейтинг.
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `COUNT(DISTINCT ...)`, `AVG`, `ROUND`
**Запрос:**

```sql
SELECT a.first_name,
       a.last_name,
       COUNT(DISTINCT b.id) AS books_count,
       ROUND(AVG(r.rating), 2) AS avg_author_rating
FROM authors a
JOIN books b ON a.id = b.author_id
JOIN reviews r ON b.id = r.book_id
GROUP BY a.id, a.first_name, a.last_name
HAVING COUNT(DISTINCT b.id) > 3
   AND AVG(r.rating) > 4.0;

```

---

**Запрос 5 — INNER JOIN**
Вывести список отзывов с полями: `username` пользователя, название книги, имя и фамилия автора, рейтинг, дата отзыва. Только отзывы с рейтингом 5. Отсортировать по дате по убыванию.
**Конструкции:** `INNER JOIN` (4 таблицы), `WHERE`, `ORDER BY`
**Запрос:**

```sql
SELECT u.username,
       b.title AS book_title,
       a.first_name || ' ' || a.last_name AS author_name,
       r.rating,
       r.created_at AS review_date
FROM reviews r
INNER JOIN users u ON r.user_id = u.id
INNER JOIN books b ON r.book_id = b.id
INNER JOIN authors a ON b.author_id = a.id
WHERE r.rating = 5
ORDER BY r.created_at DESC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести все книги с количеством читателей (уникальных пользователей). Включить книги, которые никто не открывал. Отсортировать по количеству читателей по убыванию.
**Конструкции:** `LEFT JOIN`, `COUNT(DISTINCT ...)`, `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT b.id,
       b.title,
       COUNT(DISTINCT rs.user_id) AS readers_count
FROM books b
LEFT JOIN reading_sessions rs ON b.id = rs.book_id
GROUP BY b.id, b.title
ORDER BY readers_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести всех пользователей, открывавших хотя бы одну книгу, с количеством прочитанных книг (завершённых) и количеством оставленных отзывов.
*(Используем условную агрегацию `CASE WHEN` для завершенных книг, чтобы не потерять пользователей при `INNER JOIN` сессий).*
**Конструкции:** `INNER JOIN`, `LEFT JOIN`, `GROUP BY`, `COUNT`, `COALESCE`
**Запрос:**

```sql
SELECT u.username,
       COUNT(DISTINCT CASE WHEN rs.is_completed = TRUE THEN rs.book_id END) AS completed_books,
       COALESCE(COUNT(DISTINCT r.id), 0) AS total_reviews
FROM users u
INNER JOIN reading_sessions rs ON u.id = rs.user_id
LEFT JOIN reviews r ON u.id = r.user_id
GROUP BY u.id, u.username;

```

---

**Запрос 8 — UNION**
Создать единый список активности по книге с `book_id = 1` (Сессии чтения и Отзывы). Объединить, отсортировать по дате.
**Конструкции:** `UNION`, литеральный столбец, приведение типов `::TEXT`, `ORDER BY`
**Запрос:**

```sql
SELECT started_at AS event_date,
       'Чтение' AS event_type,
       progress_percent::TEXT AS event_value
FROM reading_sessions
WHERE book_id = 1
UNION
SELECT created_at AS event_date,
       'Отзыв' AS event_type,
       rating::TEXT AS event_value
FROM reviews
WHERE book_id = 1
ORDER BY event_date ASC;

```

---

**Запрос 9 — Комплексный SELECT №1 ⭐**

**9а. Самые читаемые книги по категориям.**
*(Используется оконная функция для ранжирования).*
**Запрос 9а:**

```sql
WITH BookStats AS (
    SELECT c.name AS category_name,
           b.title AS book_title,
           a.first_name || ' ' || a.last_name AS author_name,
           COUNT(DISTINCT rs.user_id) AS readers_count,
           ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY COUNT(DISTINCT rs.user_id) DESC) as rank
    FROM categories c
    JOIN books b ON c.id = b.category_id
    JOIN authors a ON b.author_id = a.id
    JOIN reading_sessions rs ON b.id = rs.book_id
    GROUP BY c.id, c.name, b.id, b.title, author_name
)
SELECT category_name, book_title, author_name, readers_count
FROM BookStats
WHERE rank = 1;

```

**9б. Брошенные книги.**
**Запрос 9б:**

```sql
SELECT b.title AS book_title,
       c.name AS category_name,
       COUNT(rs.id) AS abandoned_sessions_count,
       ROUND(AVG(rs.progress_percent), 2) AS avg_abandoned_progress
FROM reading_sessions rs
JOIN books b ON rs.book_id = b.id
JOIN categories c ON b.category_id = c.id
WHERE rs.is_completed = FALSE
  AND rs.progress_percent > 0
GROUP BY b.id, b.title, c.name
ORDER BY abandoned_sessions_count DESC
LIMIT 10;

```

---

**Запрос 10 — Комплексный SELECT №2 ⭐**
Вывести всех авторов и все их книги из библиотеки со статистикой: количество читателей, средний рейтинг, количество завершивших чтение.
*(Для избежания искажений из-за "декартова произведения" при одновременном LEFT JOIN сессий и отзывов, статистика рассчитывается через заранее сгруппированные подзапросы).*
**Запрос:**

```sql
SELECT a.last_name,
       a.first_name,
       b.title,
       COALESCE(rs_stats.total_readers, 0) AS total_readers,
       COALESCE(rv_stats.avg_rating, 0) AS avg_rating,
       COALESCE(rs_stats.completed_readers, 0) AS completed_readers
FROM authors a
JOIN books b ON a.id = b.author_id
LEFT JOIN (
    SELECT book_id,
           COUNT(DISTINCT user_id) AS total_readers,
           COUNT(DISTINCT CASE WHEN is_completed = TRUE THEN user_id END) AS completed_readers
    FROM reading_sessions
    GROUP BY book_id
) rs_stats ON b.id = rs_stats.book_id
LEFT JOIN (
    SELECT book_id,
           ROUND(AVG(rating), 2) AS avg_rating
    FROM reviews
    GROUP BY book_id
) rv_stats ON b.id = rv_stats.book_id
ORDER BY a.last_name ASC, b.title ASC;

```

Все скрипты и конфигурации готовы! Формируй Word-документ, вставляй запросы и скриншоты из pgAdmin. Удачи на сдаче!