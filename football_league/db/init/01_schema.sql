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
