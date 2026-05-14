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
