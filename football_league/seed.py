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
