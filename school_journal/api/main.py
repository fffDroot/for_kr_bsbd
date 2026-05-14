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
