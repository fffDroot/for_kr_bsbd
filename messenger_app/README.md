Привет! Переходим к варианту про базу данных мессенджера. Здесь очень интересная бизнес-логика: мы работаем с чатами, участниками, вложенными ответами (parent_message) и файлами-вложениями.

Я написал `seed.py` таким образом, чтобы он создал «правильные» данные для всех твоих запросов. Например, он специально создаст чаты со словами "dev" и "tech" в 2024 году (для запроса 1), добавит много больших файлов в определенные чаты (для запроса 4) и сгенерирует цепочки ответов в нужные даты 2025 года (для запроса 2).

Ниже — полное и готовое решение.

### 1. Структура проекта

Создай пустую папку (например, `messenger_app`) и настрой внутри неё следующую структуру:

```text
messenger_app/
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
POSTGRES_DB=messenger_db

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
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(50) UNIQUE NOT NULL,
    email       VARCHAR(100) UNIQUE,
    phone       VARCHAR(20),
    bio         TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    last_seen   TIMESTAMP
);

CREATE TABLE chats (
    id          SERIAL PRIMARY KEY,
    chat_type   VARCHAR(20) DEFAULT 'private',
    name        VARCHAR(200),
    created_at  TIMESTAMP DEFAULT NOW(),
    created_by  INT REFERENCES users(id)
);

CREATE TABLE chat_members (
    chat_id   INT NOT NULL REFERENCES chats(id),
    user_id   INT NOT NULL REFERENCES users(id),
    role      VARCHAR(20) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE messages (
    id                SERIAL PRIMARY KEY,
    chat_id           INT NOT NULL REFERENCES chats(id),
    sender_id         INT NOT NULL REFERENCES users(id),
    content           TEXT,
    sent_at           TIMESTAMP DEFAULT NOW(),
    is_read           BOOLEAN DEFAULT FALSE,
    is_deleted        BOOLEAN DEFAULT FALSE,
    parent_message_id INT REFERENCES messages(id)
);

CREATE TABLE attachments (
    id          SERIAL PRIMARY KEY,
    message_id  INT NOT NULL REFERENCES messages(id),
    file_type   VARCHAR(20),
    file_size   INT,
    file_name   VARCHAR(200)
);

CREATE TABLE contacts (
    user_id    INT NOT NULL REFERENCES users(id),
    contact_id INT NOT NULL REFERENCES users(id),
    added_at   TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, contact_id)
);

CREATE TABLE reactions (
    id         SERIAL PRIMARY KEY,
    message_id INT NOT NULL REFERENCES messages(id),
    user_id    INT NOT NULL REFERENCES users(id),
    emoji      VARCHAR(10),
    reacted_at TIMESTAMP DEFAULT NOW()
);

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/messenger_db"
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

app = FastAPI(title="Messenger API")

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/chats")
def get_chats(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, name, chat_type FROM chats LIMIT 10")).mappings().all()
    return {"chats": result}

@app.get("/messages")
def get_messages(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, sender_id, chat_id, content FROM messages LIMIT 10")).mappings().all()
    return {"messages": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

Тут прописана специальная логика, чтобы `parent_message_id` всегда ссылался только на уже созданное сообщение в том же самом чате.

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
DB_NAME = "messenger_db"
DB_USER = "postgres"
DB_PASS = "postgres"

NUM_USERS = 500
NUM_CHATS = 200
NUM_MEMBERS_TARGET = 1500
NUM_MESSAGES = 10000
NUM_ATTACHMENTS = 2000
NUM_CONTACTS = 3000
NUM_REACTIONS = 4000
# -----------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных мессенджера...")

    # 1. Users
    users_data = []
    for _ in range(NUM_USERS):
        users_data.append((
            fake.unique.user_name(), fake.unique.email(), fake.phone_number()[:20],
            fake.text(max_nb_chars=100), fake.date_time_between(start_date='-3y', end_date='-1y'),
            fake.date_time_between(start_date='-1w', end_date='now')
        ))
    execute_values(cursor, "INSERT INTO users (username, email, phone, bio, created_at, last_seen) VALUES %s RETURNING id", users_data)
    user_ids = [row[0] for row in cursor.fetchall()]

    # 2. Chats (Private, Groups, Channels)
    chats_data = []
    # Для Запроса 1: чаты 'dev'/'tech' в 2024 году
    special_names = ['DevOps Team', 'Frontend Devs', 'Tech Support', 'Backend Tech', 'AI Developers']
    for name in special_names:
        chats_data.append(('group', name, fake.date_time_between(start_date=datetime(2024,1,1), end_date=datetime(2024,12,31)), random.choice(user_ids)))

    for i in range(NUM_CHATS - 5):
        if i < 100:
            c_type, name = 'private', None
        elif i < 180:
            c_type, name = 'group', f"Группа {fake.catch_phrase()}"
        else:
            c_type, name = 'channel', f"Канал {fake.company()}"
        chats_data.append((c_type, name, fake.date_time_between(start_date='-2y', end_date='now'), random.choice(user_ids)))

    execute_values(cursor, "INSERT INTO chats (chat_type, name, created_at, created_by) VALUES %s RETURNING id, chat_type, created_by", chats_data)
    chats_records = cursor.fetchall()
    chat_ids = [c[0] for c in chats_records]

    # 3. Chat Members
    members_data = []
    chat_participants = {c_id: [] for c_id in chat_ids} # кэш участников для генерации сообщений

    for c_id, c_type, creator_id in chats_records:
        members_data.append((c_id, creator_id, 'owner', fake.date_time_between(start_date='-2y', end_date='now')))
        chat_participants[c_id].append(creator_id)

        if c_type == 'private':
            u_id = random.choice(user_ids)
            while u_id == creator_id: u_id = random.choice(user_ids)
            members_data.append((c_id, u_id, 'member', fake.date_time_between(start_date='-2y', end_date='now')))
            chat_participants[c_id].append(u_id)
        else:
            num = random.randint(5, 50)
            chosen = random.sample(user_ids, num)
            for u_id in chosen:
                if u_id == creator_id: continue
                role = random.choices(['admin', 'member'], weights=[0.1, 0.9], k=1)[0]
                members_data.append((c_id, u_id, role, fake.date_time_between(start_date='-2y', end_date='now')))
                chat_participants[c_id].append(u_id)

    execute_values(cursor, "INSERT INTO chat_members (chat_id, user_id, role, joined_at) VALUES %s ON CONFLICT DO NOTHING", members_data)

    # 4. Messages (Сложная логика для parent_message_id)
    print("Генерируем 10000 сообщений (может занять пару секунд)...")
    messages_data = []
    chat_messages = {c_id: [] for c_id in chat_ids}

    # Для Запроса 4: нужен чат с >100 сообщений. Выделим чат #1
    mega_chat_id = chat_ids[0]

    for i in range(1, NUM_MESSAGES + 1):
        c_id = mega_chat_id if i <= 150 else random.choice(chat_ids)
        if not chat_participants[c_id]: continue

        sender = random.choice(chat_participants[c_id])

        # Для запроса 2: создадим ответы (parent_id) в 1-м квартале 2025 года
        is_reply_q1 = (150 < i < 300)
        sent_at = fake.date_time_between(start_date=datetime(2025, 1, 2), end_date=datetime(2025, 3, 30)) if is_reply_q1 else fake.date_time_between(start_date='-2y', end_date='now')

        parent_id = None
        if chat_messages[c_id] and (is_reply_q1 or random.random() < 0.15):
            parent_id = random.choice(chat_messages[c_id])

        messages_data.append((
            c_id, sender, fake.text(max_nb_chars=200), sent_at,
            random.choice([True, False]), random.choices([True, False], weights=[0.1, 0.9], k=1)[0],
            parent_id
        ))
        chat_messages[c_id].append(i) # Сохраняем локальный ID для ответов

    execute_values(cursor, "INSERT INTO messages (chat_id, sender_id, content, sent_at, is_read, is_deleted, parent_message_id) VALUES %s", messages_data)

    # 5. Attachments
    attach_data = []
    file_types = ['image', 'video', 'audio', 'document']
    # Для Запроса 4: привяжем к mega_chat_id очень большие файлы
    mega_chat_msgs = chat_messages[mega_chat_id]
    for m_id in mega_chat_msgs[:120]:
        attach_data.append((m_id, random.choice(file_types), random.randint(600000, 5000000), fake.file_name()))

    # Остальные
    for _ in range(NUM_ATTACHMENTS - 120):
        attach_data.append((random.randint(1, NUM_MESSAGES), random.choice(file_types), random.randint(10000, 1000000), fake.file_name()))

    execute_values(cursor, "INSERT INTO attachments (message_id, file_type, file_size, file_name) VALUES %s", attach_data)

    # 6. Contacts
    contacts_data = set()
    while len(contacts_data) < NUM_CONTACTS:
        u1 = random.choice(user_ids)
        u2 = random.choice(user_ids)
        if u1 != u2: contacts_data.add((u1, u2, fake.date_time_between(start_date='-2y', end_date='now')))
    execute_values(cursor, "INSERT INTO contacts (user_id, contact_id, added_at) VALUES %s ON CONFLICT DO NOTHING", list(contacts_data))

    # 7. Reactions
    emojis = ['👍', '❤️', '😂', '🔥', '👎', '😢', '👀']
    react_data = []
    for _ in range(NUM_REACTIONS):
        react_data.append((random.randint(1, NUM_MESSAGES), random.choice(user_ids), random.choice(emojis), fake.date_time_between(start_date='-1y', end_date='now')))
    execute_values(cursor, "INSERT INTO reactions (message_id, user_id, emoji, reacted_at) VALUES %s", react_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных успешно завершена!")

if __name__ == "__main__":
    seed_data()

```

---

### 5. Инструкция по запуску

1. В терминале Ubuntu в папке проекта запусти сборку:
```bash
docker compose up -d --build

```


2. Подключись к контейнеру с API:
```bash
docker compose exec app bash

```


3. Выполни скрипт генерации данных:
```bash
python seed.py

```


4. Выйди из контейнера командой `exit`.
5. Доступ:
* База данных (pgAdmin): `http://localhost:5050` (почта `admin@admin.com`, пароль `admin`). Хост `db`, юзер `postgres`, БД `messenger_db`.
* FastAPI: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести все групповые чаты и каналы, созданные в 2024 году, название которых содержит слово 'dev' или 'tech' (без учёта регистра). Отсортировать по дате создания по убыванию.
**Конструкции:** `WHERE`, `IN`, `AND`, `ILIKE`, `OR`, `EXTRACT`, `ORDER BY`
**Запрос:**

```sql
SELECT id, chat_type, name, created_at
FROM chats
WHERE chat_type IN ('group', 'channel')
  AND EXTRACT(YEAR FROM created_at) = 2024
  AND (name ILIKE '%dev%' OR name ILIKE '%tech%')
ORDER BY created_at DESC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести все сообщения, которые не удалены, отправленные в период 01.01.2025 — 31.03.2025, которые являются ответами. Отсортировать по дате отправки.
**Конструкции:** `WHERE`, `AND`, `NOT`, `IS NOT NULL`, `BETWEEN`, `ORDER BY`
**Запрос:**

```sql
SELECT id, chat_id, sender_id, content, sent_at
FROM messages
WHERE is_deleted = FALSE
  AND parent_message_id IS NOT NULL
  AND sent_at BETWEEN '2025-01-01' AND '2025-03-31'
ORDER BY sent_at ASC;

```

---

**Запрос 3 — GROUP BY**
Для каждого пользователя посчитать: общее количество отправленных сообщений, количество сообщений с вложениями, средний размер вложения (в кБ, 2 знака). Отсортировать по общему количеству сообщений по убыванию.
**Конструкции:** `JOIN` (messages + attachments), `GROUP BY`, `COUNT`, `AVG`, `ROUND`
*(Мы используем COUNT(DISTINCT m.id) для общего кол-ва и COUNT(a.id) для вложений, чтобы избежать искажений).*
**Запрос:**

```sql
SELECT u.username,
       COUNT(DISTINCT m.id) AS total_messages,
       COUNT(a.id) AS messages_with_attachments,
       ROUND(AVG(a.file_size) / 1024.0, 2) AS avg_attachment_kb
FROM users u
LEFT JOIN messages m ON u.id = m.sender_id
LEFT JOIN attachments a ON m.id = a.message_id
GROUP BY u.id, u.username
ORDER BY total_messages DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти чаты, в которых более 100 сообщений и средний размер вложений превышает 500 КБ (500 000 байт). Вывести: название чата (или id если NULL), тип чата, количество сообщений, средний размер вложений.
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `COUNT(DISTINCT ...)`, `AVG`, `COALESCE`
**Запрос:**

```sql
SELECT COALESCE(c.name, 'Чат №' || c.id) AS chat_identifier,
       c.chat_type,
       COUNT(DISTINCT m.id) AS message_count,
       ROUND(AVG(a.file_size), 2) AS avg_attachment_size
FROM chats c
JOIN messages m ON c.id = m.chat_id
JOIN attachments a ON m.id = a.message_id
GROUP BY c.id, c.name, c.chat_type
HAVING COUNT(DISTINCT m.id) > 100
   AND AVG(a.file_size) > 500000;

```

---

**Запрос 5 — INNER JOIN**
Вывести список сообщений с вложениями с полями: `username` отправителя, название чата (с COALESCE для приватных), тип файла, имя файла, размер (в кБ, 2 знака), дата отправки. Отсортировать по дате отправки по убыванию.
**Конструкции:** `INNER JOIN` (4 таблицы), `ORDER BY`
**Запрос:**

```sql
SELECT u.username,
       COALESCE(c.name, 'Приватный чат') AS chat_name,
       a.file_type,
       a.file_name,
       ROUND(a.file_size / 1024.0, 2) AS size_kb,
       m.sent_at
FROM messages m
INNER JOIN users u ON m.sender_id = u.id
INNER JOIN chats c ON m.chat_id = c.id
INNER JOIN attachments a ON m.id = a.message_id
ORDER BY m.sent_at DESC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести все сообщения (не удалённые) и количество реакций на каждое. Включить сообщения без реакций. Отсортировать по количеству реакций по убыванию.
**Конструкции:** `LEFT JOIN`, `COUNT`, `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT m.id AS message_id,
       m.content,
       COUNT(r.id) AS reactions_count
FROM messages m
LEFT JOIN reactions r ON m.id = r.message_id
WHERE m.is_deleted = FALSE
GROUP BY m.id, m.content
ORDER BY reactions_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести всех пользователей, являющихся участниками хотя бы одного чата, с количеством чатов, в которых они состоят, и общим количеством отправленных сообщений.
*(Используем COUNT(DISTINCT), так как иначе таблица чатов умножится на таблицу сообщений)*
**Конструкции:** `INNER JOIN`, `LEFT JOIN`, `GROUP BY`, `COUNT`, `COALESCE`
**Запрос:**

```sql
SELECT u.username,
       COUNT(DISTINCT cm.chat_id) AS chats_count,
       COALESCE(COUNT(DISTINCT m.id), 0) AS sent_messages_count
FROM users u
INNER JOIN chat_members cm ON u.id = cm.user_id
LEFT JOIN messages m ON u.id = m.sender_id
GROUP BY u.id, u.username
ORDER BY sent_messages_count DESC;

```

---

**Запрос 8 — UNION**
Создать единый список активности пользователя с `user_id = 1` (Сообщения и Реакции). Объединить, отсортировать по дате по убыванию.
**Конструкции:** `UNION`, `JOIN`, литеральный столбец, `ORDER BY`
**Запрос:**

```sql
SELECT m.sent_at AS event_date,
       'Сообщение' AS event_type,
       COALESCE(c.name, 'Приватный чат') AS event_detail
FROM messages m
JOIN chats c ON m.chat_id = c.id
WHERE m.sender_id = 1
UNION
SELECT r.reacted_at AS event_date,
       'Реакция' AS event_type,
       r.emoji AS event_detail
FROM reactions r
WHERE r.user_id = 1
ORDER BY event_date DESC;

```

---

**Запрос 9 — Комплексный SELECT №1 ⭐**
Найти топ-10 самых активных пользователей по суммарной активности: (сообщения) + (реакции).
**Конструкции:** Использование подзапросов (CTE) для независимого подсчета (избегаем декартова произведения), `LEFT JOIN`, `COALESCE`, `ORDER BY`, `LIMIT`.
**Запрос:**

```sql
WITH user_messages AS (
    SELECT sender_id AS user_id, COUNT(*) AS msg_count
    FROM messages GROUP BY sender_id
),
user_reactions AS (
    SELECT user_id, COUNT(*) AS react_count
    FROM reactions GROUP BY user_id
)
SELECT u.username,
       COALESCE(um.msg_count, 0) AS messages_count,
       COALESCE(ur.react_count, 0) AS reactions_count,
       (COALESCE(um.msg_count, 0) + COALESCE(ur.react_count, 0)) AS total_activity
FROM users u
LEFT JOIN user_messages um ON u.id = um.user_id
LEFT JOIN user_reactions ur ON u.id = ur.user_id
ORDER BY total_activity DESC
LIMIT 10;

```

---

**Запрос 10 — Комплексный SELECT №2 ⭐**
Найти "самые обсуждаемые" сообщения: те, на которые было дано наибольшее количество ответов. Для каждого вывести: оригинальное сообщение, `username` автора, название чата, количество ответов.
**Конструкции:** `JOIN` (self-join через alias `replies`), `GROUP BY`, `COUNT`, `ORDER BY`, `LIMIT`
**Запрос:**

```sql
SELECT orig.content AS original_message,
       u.username AS author,
       COALESCE(c.name, 'Приватный чат') AS chat_name,
       COUNT(replies.id) AS reply_count
FROM messages orig
JOIN users u ON orig.sender_id = u.id
JOIN chats c ON orig.chat_id = c.id
JOIN messages replies ON orig.id = replies.parent_message_id
GROUP BY orig.id, orig.content, u.username, c.name
ORDER BY reply_count DESC
LIMIT 10;

```