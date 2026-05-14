from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Streaming API")

@app.get("/")
def read_root():
    return {"message": "Streaming API is running"}

@app.get("/content")
def get_content(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, title, content_type, release_year FROM content LIMIT 10")).mappings().all()
    return {"content": result}

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, username, subscription_type FROM users LIMIT 10")).mappings().all()
    return {"users": result}
