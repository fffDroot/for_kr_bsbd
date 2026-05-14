from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Services & Specialists API")

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/specialists")
def get_specialists(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, first_name, last_name, category_id, rating FROM specialists LIMIT 10")).mappings().all()
    return {"specialists": result}

@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, status, price, created_at FROM orders LIMIT 10")).mappings().all()
    return {"orders": result}
