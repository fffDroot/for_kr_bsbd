Отлично! Переходим к третьему варианту — «Электронный журнал для школ г. Москвы». Структура решения останется такой же удобной: мы настроим проект, вынесем параметры генерации в константы для гибкости и подробно разберем каждый SQL-запрос.

### 1. Структура проекта

Создай пустую папку (например, `school_journal`) и подготовь в ней следующую структуру файлов:

```text
school_journal/
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
POSTGRES_DB=school_db

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
*В условии указан PostgreSQL 15.*

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
CREATE TABLE schools (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    address     TEXT,
    district    VARCHAR(100),
    phone       VARCHAR(20),
    principal   VARCHAR(150)
);

CREATE TABLE teachers (
    id               SERIAL PRIMARY KEY,
    first_name       VARCHAR(50) NOT NULL,
    last_name        VARCHAR(50) NOT NULL,
    patronymic       VARCHAR(50),
    school_id        INT REFERENCES schools(id),
    subject          VARCHAR(100),
    experience_years INT DEFAULT 0
);

CREATE TABLE classes (
    id                  SERIAL PRIMARY KEY,
    school_id           INT NOT NULL REFERENCES schools(id),
    grade               INT CHECK (grade BETWEEN 1 AND 11),
    letter              CHAR(1),
    academic_year       VARCHAR(10),
    homeroom_teacher_id INT REFERENCES teachers(id)
);

CREATE TABLE students (
    id           SERIAL PRIMARY KEY,
    class_id     INT NOT NULL REFERENCES classes(id),
    first_name   VARCHAR(50) NOT NULL,
    last_name    VARCHAR(50) NOT NULL,
    patronymic   VARCHAR(50),
    birth_date   DATE,
    parent_phone VARCHAR(20)
);

CREATE TABLE subjects (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE grades (
    id          SERIAL PRIMARY KEY,
    student_id  INT NOT NULL REFERENCES students(id),
    subject_id  INT NOT NULL REFERENCES subjects(id),
    teacher_id  INT NOT NULL REFERENCES teachers(id),
    value       INT CHECK (value BETWEEN 1 AND 5),
    grade_date  DATE NOT NULL,
    grade_type  VARCHAR(50)
);

CREATE TABLE attendance (
    id         SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(id),
    class_id   INT NOT NULL REFERENCES classes(id),
    att_date   DATE NOT NULL,
    is_present BOOLEAN DEFAULT TRUE,
    reason     VARCHAR(200)
);

```

**Файл `api/database.py**`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/school_db"
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

app = FastAPI(title="Moscow School Journal API")

@app.get("/")
def read_root():
    return {"message": "Electronic Journal API is running"}

@app.get("/students")
def get_students(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, first_name, last_name FROM students LIMIT 10")).mappings().all()
    return {"students": result}

@app.get("/grades")
def get_grades(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, value, grade_date, grade_type FROM grades LIMIT 10")).mappings().all()
    return {"grades": result}

```

---

### 4. Скрипт наполнения данными (`seed.py`)

Как всегда, параметры вынесены в настройки. Faker настроен на локаль `ru_RU`, чтобы генерировать реалистичные имена и адреса.

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
DB_NAME = "school_db"
DB_USER = "postgres"
DB_PASS = "postgres"

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ГЕНЕРАЦИИ ---
DISTRICTS = ['ЦАО', 'САО', 'СВАО', 'ВАО', 'ЮВАО', 'ЮАО', 'ЮЗАО', 'ЗАО', 'СЗАО', 'ЗелАО', 'ТиНАО']
SUBJECTS_LIST = ['Математика', 'Русский язык', 'Литература', 'Физика', 'Химия',
                 'Биология', 'История', 'Обществознание', 'Информатика', 'География',
                 'Английский язык', 'Физкультура', 'ИЗО', 'Музыка', 'ОБЖ']
GRADE_TYPES = ['Контрольная', 'Устный ответ', 'Домашняя работа', 'Зачёт', 'Самостоятельная работа']

NUM_SCHOOLS = 20
NUM_TEACHERS = 150
NUM_CLASSES = 100
NUM_STUDENTS_TARGET = 2500

NUM_GRADES = 10000
NUM_ATTENDANCE = 5000

ACADEMIC_YEAR = '2024-2025'
PERIOD_START = date(2024, 9, 1)
PERIOD_END = date(2025, 4, 30)
# --------------------------------------

def get_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Генерация данных электронного журнала...")

    # 1. Subjects
    subj_data = [(name, f"Изучение предмета {name}") for name in SUBJECTS_LIST]
    execute_values(cursor, "INSERT INTO subjects (name, description) VALUES %s", subj_data)

    # 2. Schools
    schools_data = []
    for i in range(1, NUM_SCHOOLS + 1):
        schools_data.append((
            f"Школа № {fake.unique.random_int(min=100, max=2999)}",
            fake.address(), random.choice(DISTRICTS),
            fake.phone_number()[:20], f"{fake.last_name()} {fake.first_name()} {fake.middle_name()}"
        ))
    execute_values(cursor, "INSERT INTO schools (name, address, district, phone, principal) VALUES %s", schools_data)

    cursor.execute("SELECT id FROM schools;")
    school_ids = [row[0] for row in cursor.fetchall()]

    # 3. Teachers
    teachers_data = []
    for _ in range(NUM_TEACHERS):
        teachers_data.append((
            fake.first_name(), fake.last_name(), fake.middle_name(),
            random.choice(school_ids), random.choice(SUBJECTS_LIST), random.randint(0, 40)
        ))
    execute_values(cursor, "INSERT INTO teachers (first_name, last_name, patronymic, school_id, subject, experience_years) VALUES %s", teachers_data)

    cursor.execute("SELECT id, school_id FROM teachers;")
    teachers_records = cursor.fetchall()

    # 4. Classes
    classes_data = []
    letters = ['А', 'Б', 'В', 'Г']
    for _ in range(NUM_CLASSES):
        s_id = random.choice(school_ids)
        # Ищем учителя из этой же школы для классного руководства
        school_teachers = [t[0] for t in teachers_records if t[1] == s_id]
        hr_teacher = random.choice(school_teachers) if school_teachers else None

        classes_data.append((
            s_id, random.randint(5, 11), random.choice(letters), ACADEMIC_YEAR, hr_teacher
        ))
    execute_values(cursor, "INSERT INTO classes (school_id, grade, letter, academic_year, homeroom_teacher_id) VALUES %s", classes_data)

    cursor.execute("SELECT id FROM classes;")
    class_ids = [row[0] for row in cursor.fetchall()]

    # 5. Students
    students_data = []
    for _ in range(NUM_STUDENTS_TARGET):
        students_data.append((
            random.choice(class_ids), fake.first_name(), fake.last_name(), fake.middle_name(),
            fake.date_of_birth(minimum_age=10, maximum_age=18), fake.phone_number()[:20]
        ))
    execute_values(cursor, "INSERT INTO students (class_id, first_name, last_name, patronymic, birth_date, parent_phone) VALUES %s", students_data)

    # 6. Grades
    cursor.execute("SELECT id FROM students;")
    student_ids = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT id FROM subjects;")
    subject_ids = [row[0] for row in cursor.fetchall()]
    teacher_ids = [t[0] for t in teachers_records]

    grades_data = []
    for _ in range(NUM_GRADES):
        grades_data.append((
            random.choice(student_ids), random.choice(subject_ids), random.choice(teacher_ids),
            random.randint(1, 5), fake.date_between_dates(date_start=PERIOD_START, date_end=PERIOD_END),
            random.choice(GRADE_TYPES)
        ))
    execute_values(cursor, "INSERT INTO grades (student_id, subject_id, teacher_id, value, grade_date, grade_type) VALUES %s", grades_data)

    # 7. Attendance
    cursor.execute("SELECT id, class_id FROM students;")
    students_classes = cursor.fetchall()

    attendance_data = []
    for _ in range(NUM_ATTENDANCE):
        st_id, cl_id = random.choice(students_classes)
        is_pres = random.choices([True, False], weights=[0.8, 0.2], k=1)[0]
        reason = None if is_pres else random.choice(['Болезнь', 'Уважительная', 'Прогул'])

        attendance_data.append((
            st_id, cl_id, fake.date_between_dates(date_start=PERIOD_START, date_end=PERIOD_END),
            is_pres, reason
        ))
    execute_values(cursor, "INSERT INTO attendance (student_id, class_id, att_date, is_present, reason) VALUES %s", attendance_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Генерация данных завершена!")

if __name__ == "__main__":
    seed_data()

```

---

### 5. Инструкция по запуску

1. В терминале Ubuntu в папке проекта запусти сборку:
```bash
docker compose up -d --build

```


2. Провались в контейнер FastAPI:
```bash
docker compose exec app bash

```


3. Выполни скрипт:
```bash
python seed.py

```


4. Выйди из контейнера: `exit`.
5. Доступ:
* База: `http://localhost:5050` (юзер `admin@admin.com`, пароль `admin`). Добавь сервер `db`, логин `postgres`, пароль `postgres`, БД `school_db`.
* API: `http://localhost:8000/docs`



---

### 6. DQL-запросы (10 штук) для отчета

**Запрос 1 — Базовый SELECT**
Вывести всех учеников из классов с параллелью 10 или 11, отсортировать по фамилии. Дополнительно: вывести только тех, чья фамилия начинается на буквы 'А' или 'Б'.
**Конструкции:** `WHERE`, `IN`, `AND`, `LIKE`, `OR`, `ORDER BY`
**Запрос:**

```sql
SELECT s.first_name, s.last_name, c.grade, c.letter
FROM students s
JOIN classes c ON s.class_id = c.id
WHERE c.grade IN (10, 11)
  AND (s.last_name LIKE 'А%' OR s.last_name LIKE 'Б%')
ORDER BY s.last_name ASC;

```

---

**Запрос 2 — Базовый SELECT**
Вывести все оценки за период 01.09.2024 — 31.12.2024, тип которых не входит в ('Домашняя работа') и значение меньше 3. Отсортировать по дате оценки, затем по значению.
**Конструкции:** `WHERE`, `BETWEEN`, `NOT IN`, `AND`, `<`, `ORDER BY`
**Запрос:**

```sql
SELECT * FROM grades
WHERE grade_date BETWEEN '2024-09-01' AND '2024-12-31'
  AND grade_type NOT IN ('Домашняя работа')
  AND value < 3
ORDER BY grade_date ASC, value ASC;

```

---

**Запрос 3 — GROUP BY**
По каждому предмету вычислить: количество выставленных оценок, средний балл (2 знака), количество двоечников (оценка = 2). Отсортировать по среднему баллу по возрастанию.
**Конструкции:** `GROUP BY`, `COUNT`, `AVG`, `ROUND`, `SUM(CASE ...)`, `ORDER BY`
**Запрос:**

```sql
SELECT sub.name AS subject_name,
       COUNT(g.id) AS total_grades,
       ROUND(AVG(g.value), 2) AS avg_grade,
       SUM(CASE WHEN g.value = 2 THEN 1 ELSE 0 END) AS poor_grades_count
FROM subjects sub
JOIN grades g ON sub.id = g.subject_id
GROUP BY sub.id, sub.name
ORDER BY avg_grade ASC;

```

---

**Запрос 4 — GROUP BY + HAVING**
Найти учеников, у которых средний балл ниже 3.5 и при этом количество пропусков (записей в `attendance` с `is_present = FALSE`) более 10. Вывести: фамилию, имя ученика, средний балл, количество пропусков.
**Конструкции:** `JOIN`, `GROUP BY`, `HAVING`, `AVG`, `COUNT`, `ROUND` *(Используется CTE, чтобы избежать декартова произведения при джоине двух независимых таблиц с множеством записей на одного ученика)*
**Запрос:**

```sql
WITH student_absences AS (
    SELECT student_id, COUNT(*) as abs_count
    FROM attendance
    WHERE is_present = FALSE
    GROUP BY student_id
)
SELECT s.last_name, s.first_name,
       ROUND(AVG(g.value), 2) AS avg_grade,
       sa.abs_count AS total_absences
FROM students s
JOIN grades g ON s.id = g.student_id
JOIN student_absences sa ON s.id = sa.student_id
GROUP BY s.id, s.last_name, s.first_name, sa.abs_count
HAVING AVG(g.value) < 3.5 AND sa.abs_count > 10;

```

---

**Запрос 5 — INNER JOIN**
Вывести список оценок с полями: фамилия и имя ученика, название предмета, фамилия учителя, значение оценки, дата. Только оценки типа 'Контрольная' или 'Зачёт'. Отсортировать по дате по убыванию.
**Конструкции:** `INNER JOIN` (4 таблицы: `grades`, `students`, `subjects`, `teachers`), `WHERE`, `ORDER BY`
**Запрос:**

```sql
SELECT s.last_name AS student_last_name,
       s.first_name AS student_first_name,
       sub.name AS subject_name,
       t.last_name AS teacher_last_name,
       g.value,
       g.grade_date
FROM grades g
INNER JOIN students s ON g.student_id = s.id
INNER JOIN subjects sub ON g.subject_id = sub.id
INNER JOIN teachers t ON g.teacher_id = t.id
WHERE g.grade_type IN ('Контрольная', 'Зачёт')
ORDER BY g.grade_date DESC;

```

---

**Запрос 6 — LEFT JOIN**
Вывести все предметы из базы данных с количеством оценок по каждому предмету. Включить предметы, по которым ещё не выставлялись оценки (показать 0). Отсортировать по количеству оценок по убыванию.
**Конструкции:** `LEFT JOIN` (таблицы: `subjects`, `grades`), `COUNT`, `GROUP BY`, `ORDER BY`
**Запрос:**

```sql
SELECT sub.id,
       sub.name,
       COUNT(g.id) AS grades_count
FROM subjects sub
LEFT JOIN grades g ON sub.id = g.subject_id
GROUP BY sub.id, sub.name
ORDER BY grades_count DESC;

```

---

**Запрос 7 — Смешанное соединение**
Вывести все классы с количеством учеников в каждом и средним баллом класса (по всем предметам, если оценки есть, иначе NULL). Включить классы, в которых нет ни одного ученика или нет оценок.
**Конструкции:** `LEFT JOIN`, `GROUP BY`, `AVG`, `COUNT(DISTINCT ...)`
**Запрос:**

```sql
SELECT c.grade,
       c.letter,
       COUNT(DISTINCT s.id) AS students_count,
       ROUND(AVG(g.value), 2) AS class_avg_grade
FROM classes c
LEFT JOIN students s ON c.id = s.class_id
LEFT JOIN grades g ON s.id = g.student_id
GROUP BY c.id, c.grade, c.letter;

```

---

**Запрос 8 — UNION**
Создать единый список персонала школы: из `teachers`: ФИО, роль 'Учитель', предмет; из `schools`: имя директора, роль 'Директор', предмет '—'. Объединить, отсортировать по роли, затем по фамилии.
**Конструкции:** `UNION`, литеральный столбец, `ORDER BY`
**Запрос:**

```sql
SELECT last_name || ' ' || first_name || ' ' || COALESCE(patronymic, '') AS full_name,
       'Учитель' AS role,
       subject
FROM teachers
UNION
SELECT principal AS full_name,
       'Директор' AS role,
       '—' AS subject
FROM schools
WHERE principal IS NOT NULL
ORDER BY role DESC, full_name ASC;

```

---

**Запрос 9 — Комплексный SELECT №1**
Найти топ-5 учеников с лучшим средним баллом за II четверть (ноябрь–декабрь 2024 года) среди учеников 10-х классов. Вывести: фамилия и имя, класс, средний балл (2 знака).
**Конструкции:** `JOIN`, `WHERE`, `GROUP BY`, `AVG`, `ROUND`, `ORDER BY DESC`, `LIMIT`
**Запрос:**

```sql
SELECT s.last_name,
       s.first_name,
       c.grade || c.letter AS class_name,
       ROUND(AVG(g.value), 2) AS avg_grade
FROM students s
JOIN classes c ON s.class_id = c.id
JOIN grades g ON s.id = g.student_id
WHERE c.grade = 10
  AND g.grade_date BETWEEN '2024-11-01' AND '2024-12-31'
GROUP BY s.id, s.last_name, s.first_name, class_name
ORDER BY avg_grade DESC
LIMIT 5;

```

---

**Запрос 10 — Комплексный SELECT №2**
Для каждой школы вывести предмет с наихудшим средним баллом. Вывести: название школы, предмет, средний балл (2 знака).
**Конструкции:** `JOIN`, `GROUP BY`, `DISTINCT ON` (Специфичная и очень удобная функция PostgreSQL для выбора "одного из группы").
**Запрос:**

```sql
SELECT DISTINCT ON (sch.id)
       sch.name AS school_name,
       sub.name AS worst_subject,
       ROUND(AVG(g.value), 2) AS avg_grade
FROM schools sch
JOIN teachers t ON sch.id = t.school_id
JOIN grades g ON t.id = g.teacher_id
JOIN subjects sub ON g.subject_id = sub.id
GROUP BY sch.id, sch.name, sub.id, sub.name
ORDER BY sch.id, avg_grade ASC;

```
