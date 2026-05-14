from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="E-Library API")

@app.get("/")
def read_root():
    return {"message": "Library API is running"}

@app.get("/books")
def get_books(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, title, publication_year, pages FROM books LIMIT 10")).mappings().all()
    return {"books": result}

@app.get("/authors")
def get_authors(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, first_name, last_name, nationality FROM authors LIMIT 10")).mappings().all()
    return {"authors": result}