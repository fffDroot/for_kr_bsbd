Отличный футбольный вариант! Здесь интересная структура базы данных: сезоны, турнирные таблицы, трансферы и события матчей. Чтобы запросы (особенно 9 и 10 про результативность и очки) работали красиво, я добавил в скрипт генерации данных логику, которая правильно распределяет матчи по сезонам и гарантирует наличие голов.

Ниже представлено полное и готовое к сдаче решение.

### 1. Структура проекта

Создай пустую папку (например, `football_league`) и повтори в ней следующую структуру файлов:

```text
football_league/
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
POSTGRES_DB=league_db

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
*(Строго 3 сервиса, PostgreSQL 15, порты по заданию)*

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
CREATE TABLE teams (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    city         VARCHAR(50),
    stadium      VARCHAR(100),
    founded_year INT,
    coach        VARCHAR(150)
);

CREATE TABLE players (
    id             SERIAL PRIMARY KEY,
    team_id        INT REFERENCES teams(id),
    first_name     VARCHAR(50) NOT NULL,
    last_name      VARCHAR(50) NOT NULL,
    position       VARCHAR(30),
    nationality    VARCHAR(50),
    birth_date     DATE,
    jersey_number  INT
);

CREATE TABLE seasons (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(50) NOT NULL,
    start_date DATE,
    end_date   DATE
);

CREATE TABLE matches (
    id           SERIAL PRIMARY KEY,
    season_id    INT NOT NULL REFERENCES seasons(id),
    home_team_id INT NOT NULL REFERENCES teams(id),
    away_team_id INT NOT NULL REFERENCES teams(id),
    match_date   TIMESTAMP,
    venue        VARCHAR(100),
    home_score   INT DEFAULT 0,
    away_score   INT DEFAULT 0,
    status       VARCHAR(20) DEFAULT 'scheduled'
);

CREATE TABLE match_events (
    id          SERIAL PRIMARY KEY,
    match_id    INT NOT NULL REFERENCES matches(id),
    player_id   INT NOT NULL REFERENCES players(id),
    team_id     INT NOT NULL REFERENCES teams(id),
    event_type  VARCHAR(30),
    minute      INT CHECK (minute BETWEEN 1 AND 120),
    description TEXT
);

CREATE TABLE standings (
    id                SERIAL PRIMARY KEY,
    season_id         INT NOT NULL REFERENCES seasons(id),
    team_id           INT NOT NULL REFERENCES teams(id),
    wins              INT DEFAULT 0,
    draws             INT DEFAULT 0,
    losses            INT DEFAULT 0,
    goals_scored      INT DEFAULT 0,
    goals_conceded    INT DEFAULT 0,
    points            INT DEFAULT 0
);

CREATE TABLE transfers (
    id             SERIAL PRIMARY KEY,
    player_id      INT NOT NULL REFERENCES players(id),
    from_team_id   INT REFERENCES teams(id),
    to_team_id     INT REFERENCES teams(id),
    transfer_date  DATE,
    fee            NUMERIC(12,2) DEFAULT 0
);

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/league_db"
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

app = FastAPI(title="Football League API")

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/teams")
def get_teams(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, name, city FROM teams LIMIT 10")).mappings().all()
    return {"teams": result}

@app.get("/matches")
def get_matches(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, match_date, status, home_score, away_score FROM matches LIMIT 10")).mappings().all()
    return {"matches": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

Как и просили, настройки вынесены в константы. Скрипт сгенерирует 10 000 событий матча.

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
DB_NAME = "league_db"
DB_USER = "postgres"
DB_PASS = "postgres"

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ГЕНЕРАЦИИ ---
NUM_TEAMS = 20
NUM_PLAYERS = 500
NUM_MATCHES = 600
NUM_EVENTS = 10000
NUM_TRANSFERS = 300

POSITIONS = ['Вратарь', 'Защитник', 'Полузащитник', 'Нападающий']
EVENT_TYPES = ['Гол', 'Жёлтая карточка', 'Красная карточка', 'Замена']
SEASONS_DATA = [
    ('2022/2023', date(2022, 8, 1), date(2023, 5, 31)),
    ('2023/2024', date(2023, 8, 1), date(2024, 5, 31)),
    ('2024/2025', date(2024, 8, 1), date(2025, 5, 31))
]
# --------------------------------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных чемпионата...")

    # 1. Seasons
    execute_values(cursor, "INSERT INTO seasons (name, start_date, end_date) VALUES %s", SEASONS_DATA)
    cursor.execute("SELECT id, name, start_date, end_date FROM seasons;")
    seasons = cursor.fetchall()

    # 2. Teams
    teams_data = []
    for _ in range(NUM_TEAMS):
        teams_data.append((
            f"ФК {fake.word().capitalize()}", fake.city(), f"Стадион {fake.word().capitalize()}",
            random.randint(1900, 2015), f"{fake.last_name()} {fake.first_name()}"
        ))
    execute_values(cursor, "INSERT INTO teams (name, city, stadium, founded_year, coach) VALUES %s", teams_data)
    cursor.execute("SELECT id, stadium FROM teams;")
    teams = cursor.fetchall()
    team_ids = [t[0] for t in teams]

    # 3. Players
    players_data = []
    for _ in range(NUM_PLAYERS):
        players_data.append((
            random.choice(team_ids), fake.first_name_male(), fake.last_name_male(),
            random.choice(POSITIONS), fake.country(),
            fake.date_of_birth(minimum_age=17, maximum_age=38), random.randint(1, 99)
        ))
    execute_values(cursor, "INSERT INTO players (team_id, first_name, last_name, position, nationality, birth_date, jersey_number) VALUES %s", players_data)
    cursor.execute("SELECT id, team_id FROM players;")
    players = cursor.fetchall()

    team_players_map = {t_id: [] for t_id in team_ids}
    for p_id, t_id in players:
        if t_id: team_players_map[t_id].append(p_id)

    # 4. Standings
    standings_data = []
    for s_id, _, _, _ in seasons:
        for t_id in team_ids:
            w, d, l = random.randint(5, 20), random.randint(5, 10), random.randint(5, 15)
            gs, gc = random.randint(20, 80), random.randint(20, 80)
            pts = (w * 3) + d
            standings_data.append((s_id, t_id, w, d, l, gs, gc, pts))
    execute_values(cursor, "INSERT INTO standings (season_id, team_id, wins, draws, losses, goals_scored, goals_conceded, points) VALUES %s", standings_data)

    # 5. Matches
    matches_data = []
    for _ in range(NUM_MATCHES):
        season = random.choice(seasons)
        s_id, _, s_start, s_end = season

        home_team = random.choice(teams)
        away_team = random.choice(teams)
        while home_team[0] == away_team[0]:
            away_team = random.choice(teams)

        m_date = fake.date_time_between_dates(datetime_start=s_start, datetime_end=s_end)
        status = random.choice(['completed', 'scheduled']) if s_id == 3 else 'completed'
        h_score = random.randint(0, 5) if status == 'completed' else 0
        a_score = random.randint(0, 4) if status == 'completed' else 0

        matches_data.append((s_id, home_team[0], away_team[0], m_date, home_team[1], h_score, a_score, status))

    execute_values(cursor, "INSERT INTO matches (season_id, home_team_id, away_team_id, match_date, venue, home_score, away_score, status) VALUES %s RETURNING id, home_team_id, away_team_id", matches_data)
    matches_records = cursor.fetchall()

    # 6. Match Events (10 000 строк)
    events_data = []
    for _ in range(NUM_EVENTS):
        m_id, h_team, a_team = random.choice(matches_records)
        event_team_id = random.choice([h_team, a_team])

        # Защита от пустых команд
        if not team_players_map[event_team_id]: continue

        p_id = random.choice(team_players_map[event_team_id])
        events_data.append((
            m_id, p_id, event_team_id, random.choice(EVENT_TYPES),
            random.randint(1, 120), fake.text(max_nb_chars=50)
        ))
    execute_values(cursor, "INSERT INTO match_events (match_id, player_id, team_id, event_type, minute, description) VALUES %s", events_data)

    # 7. Transfers
    transfers_data = []
    for _ in range(NUM_TRANSFERS):
        p_id = random.choice(players)[0]
        from_t = random.choice(team_ids)
        to_t = random.choice(team_ids)
        while from_t == to_t:
            to_t = random.choice(team_ids)
        transfers_data.append((
            p_id, from_t, to_t, fake.date_between(start_date='-3y', end_date='today'),
            round(random.uniform(0, 100000000), 2)
        ))
    execute_values(cursor, "INSERT INTO transfers (player_id, from_team_id, to_team_id, transfer_date, fee) VALUES %s", transfers_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных завершена!")

if __name__ == "__main__":
    seed_data()

```

---

### 5. Инструкция по запуску

1. Запусти контейнеры:
```bash
docker compose up -d --build

```


2. Войди в контейнер с приложением:
```bash
docker compose exec app bash

```


3. Сгенерируй данные:
```bash
python seed.py

```


4. Нажми `Ctrl+D`, чтобы выйти из контейнера.
5. Проверка:
* База данных: `http://localhost:5050` (юзер `admin@admin.com`, пароль `admin`). Добавь сервер `db`, логин/пароль `postgres`, БД `league_db`.
* FastAPI: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести всех игроков с позицией 'Нападающий' или 'Полузащитник', рождённых с 1995 по 2003 год и чья фамилия содержит букву 'а' (регистронезависимо). Отсортировать по дате рождения.
**Конструкции:** `WHERE`, `IN`, `BETWEEN`, `ILIKE` (в Postgres это регистронезависимый LIKE), `EXTRACT` (или сравнение дат), `ORDER BY`
**Запрос:**

```sql
SELECT first_name, last_name, position, birth_date
FROM players
WHERE position IN ('Нападающий', 'Полузащитник')
  AND EXTRACT(YEAR FROM birth_date) BETWEEN 1995 AND 2003
  AND last_name ILIKE '%а%'
ORDER BY birth_date ASC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести все завершённые матчи сезона '2024/2025', в которых суммарное количество голов больше 3. Исключить матчи с нулевой ничьей (0:0). Отсортировать по дате матча.
**Конструкции:** `JOIN`, `WHERE`, `AND`, `NOT (...)`, арифметика, `ORDER BY`
**Запрос:**

```sql
SELECT m.id, m.match_date, m.home_score, m.away_score
FROM matches m
JOIN seasons s ON m.season_id = s.id
WHERE s.name = '2024/2025'
  AND m.status = 'completed'
  AND (m.home_score + m.away_score > 3)
  AND NOT (m.home_score = 0 AND m.away_score = 0)
ORDER BY m.match_date ASC;

```

---

**Запрос 3 — GROUP BY**
Для каждой команды в сезоне '2024/2025' вычислить: общее количество голов (из `standings`), количество побед, поражений, среднее количество очков. Отсортировать по очкам по убыванию.
**Конструкции:** `JOIN`, `GROUP BY`, `SUM`, `AVG`, `ORDER BY`
**Запрос:**

```sql
SELECT t.name AS team_name,
       SUM(st.goals_scored) AS total_goals_scored,
       SUM(st.wins) AS total_wins,
       SUM(st.losses) AS total_losses,
       ROUND(AVG(st.points), 2) AS avg_points
FROM teams t
JOIN standings st ON t.id = st.team_id
JOIN seasons s ON st.season_id = s.id
WHERE s.name = '2024/2025'
GROUP BY t.id, t.name
ORDER BY avg_points DESC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти игроков, забивших более 5 голов за весь чемпионат (из `match_events`). Вывести: имя и фамилию игрока, название команды, количество голов. Отсортировать по количеству голов по убыванию.
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `COUNT`, `WHERE`
**Запрос:**

```sql
SELECT p.first_name,
       p.last_name,
       t.name AS team_name,
       COUNT(me.id) AS goals_count
FROM players p
JOIN teams t ON p.team_id = t.id
JOIN match_events me ON p.id = me.player_id
WHERE me.event_type = 'Гол'
GROUP BY p.id, p.first_name, p.last_name, t.name
HAVING COUNT(me.id) > 5
ORDER BY goals_count DESC;

```

---

**Запрос 5 — INNER JOIN**
Вывести все события матча (Жёлтые и Красные карточки) с полями: дата матча, домашняя vs гостевая, игрок, тип события, минута. Отсортировать по дате по убыванию.
**Конструкции:** `INNER JOIN` (4 таблицы: `match_events`, `matches`, `players`, `teams` дважды через алиасы), `WHERE`, `ORDER BY`
**Запрос:**

```sql
SELECT m.match_date,
       th.name AS home_team,
       ta.name AS away_team,
       p.first_name || ' ' || p.last_name AS player_name,
       me.event_type,
       me.minute
FROM match_events me
INNER JOIN matches m ON me.match_id = m.id
INNER JOIN teams th ON m.home_team_id = th.id
INNER JOIN teams ta ON m.away_team_id = ta.id
INNER JOIN players p ON me.player_id = p.id
WHERE me.event_type IN ('Жёлтая карточка', 'Красная карточка')
ORDER BY m.match_date DESC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести всех игроков с количеством их голов за всё время. Включить игроков, не забивших ни одного гола (показать 0). Отсортировать по количеству голов по убыванию.
*(Важно: Фильтр `event_type = 'Гол'` должен быть в условии `ON` у `LEFT JOIN`, иначе записи с 0 отсекутся)*
**Конструкции:** `LEFT JOIN`, `COUNT`, `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT p.id,
       p.first_name,
       p.last_name,
       COUNT(me.id) AS goals_count
FROM players p
LEFT JOIN match_events me ON p.id = me.player_id AND me.event_type = 'Гол'
GROUP BY p.id, p.first_name, p.last_name
ORDER BY goals_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести все команды с количеством выигранных матчей в сезоне '2024/2025' и информацией о трансферных расходах (если переходы были).
**Конструкции:** `INNER JOIN`, `LEFT JOIN`, `GROUP BY`, `SUM`, `COALESCE`
**Запрос:**

```sql
SELECT t.name AS team_name,
       SUM(st.wins) AS wins_in_season,
       COALESCE(SUM(tr.fee), 0) AS total_transfer_spent
FROM teams t
INNER JOIN standings st ON t.id = st.team_id
INNER JOIN seasons s ON st.season_id = s.id AND s.name = '2024/2025'
LEFT JOIN transfers tr ON t.id = tr.to_team_id
GROUP BY t.id, t.name
ORDER BY wins_in_season DESC;

```

---

**Запрос 8 — UNION**
Создать единый список голевых и дисциплинарных событий. Объединить, отсортировать по дате матча, затем по минуте.
**Конструкции:** `UNION`, `JOIN`, литеральный столбец, `ORDER BY`
**Запрос:**

```sql
SELECT p.first_name || ' ' || p.last_name AS player_name,
       m.match_date,
       me.minute,
       'Гол' AS event_label
FROM match_events me
JOIN players p ON me.player_id = p.id
JOIN matches m ON me.match_id = m.id
WHERE me.event_type = 'Гол'
UNION
SELECT p.first_name || ' ' || p.last_name AS player_name,
       m.match_date,
       me.minute,
       'Удаление' AS event_label
FROM match_events me
JOIN players p ON me.player_id = p.id
JOIN matches m ON me.match_id = m.id
WHERE me.event_type = 'Красная карточка'
ORDER BY match_date ASC, minute ASC;

```

---

**Запрос 9 — Комплексный SELECT №1**
Вывести итоговую таблицу чемпионата сезона '2024/2025': команда, побед, ничьих, поражений, голов забито, голов пропущено, разница голов, очки. Отсортировать по очкам, затем по разнице голов.
**Конструкции:** `JOIN`, `ORDER BY` (несколько полей), вычисляемый столбец
**Запрос:**

```sql
SELECT t.name AS team_name,
       st.wins,
       st.draws,
       st.losses,
       st.goals_scored,
       st.goals_conceded,
       (st.goals_scored - st.goals_conceded) AS goal_difference,
       st.points
FROM standings st
JOIN teams t ON st.team_id = t.id
JOIN seasons s ON st.season_id = s.id
WHERE s.name = '2024/2025'
ORDER BY st.points DESC, goal_difference DESC;

```

---

**Запрос 10 — Комплексный SELECT №2**
Найти самого результативного игрока в каждой команде за сезон '2024/2025' (по количеству забитых голов). Вывести: название команды, имя и фамилия игрока, позиция, количество голов.
**Конструкции:** CTE (`WITH`), `JOIN`, `GROUP BY`, `COUNT`, оконная функция `RANK() OVER (PARTITION BY ...)`
**Запрос:**

```sql
WITH PlayerGoals AS (
    SELECT p.team_id,
           p.id AS player_id,
           p.first_name,
           p.last_name,
           p.position,
           COUNT(me.id) AS goal_count,
           RANK() OVER (PARTITION BY p.team_id ORDER BY COUNT(me.id) DESC) as rank
    FROM players p
    JOIN match_events me ON p.id = me.player_id
    JOIN matches m ON me.match_id = m.id
    JOIN seasons s ON m.season_id = s.id
    WHERE s.name = '2024/2025' AND me.event_type = 'Гол'
    GROUP BY p.team_id, p.id, p.first_name, p.last_name, p.position
)
SELECT t.name AS team_name,
       pg.first_name || ' ' || pg.last_name AS full_name,
       pg.position,
       pg.goal_count
FROM PlayerGoals pg
JOIN teams t ON pg.team_id = t.id
WHERE pg.rank = 1
ORDER BY t.name ASC;

```
