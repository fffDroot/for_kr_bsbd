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
