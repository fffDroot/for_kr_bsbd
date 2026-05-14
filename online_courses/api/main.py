from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Online Courses API")

@app.get("/")
def read_root():
    return {"message": "Courses API is running"}

@app.get("/courses")
def get_courses(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, title, level, price FROM courses LIMIT 10")).mappings().all()
    return {"courses": result}

@app.get("/enrollments")
def get_enrollments(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, user_id, course_id, status FROM enrollments LIMIT 10")).mappings().all()
    return {"enrollments": result}
