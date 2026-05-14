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
