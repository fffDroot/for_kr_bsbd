from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Grocery Chain API")

@app.get("/")
def read_root():
    return {"message": "Grocery API is running"}

@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, name, price, unit FROM products LIMIT 10")).mappings().all()
    return {"products": result}

@app.get("/sales")
def get_sales(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, product_id, quantity, sale_date FROM sales LIMIT 10")).mappings().all()
    return {"sales": result}