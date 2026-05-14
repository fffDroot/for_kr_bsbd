from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Mobile Operator API")

@app.get("/")
def read_root():
    return {"message": "Mobile Operator API is running"}

@app.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, name, price FROM plans LIMIT 10")).mappings().all()
    return {"plans": result}

@app.get("/subscribers")
def get_subscribers(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, phone_number, city FROM subscribers LIMIT 10")).mappings().all()
    return {"subscribers": result}
