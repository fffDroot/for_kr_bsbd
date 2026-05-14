from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Carsharing API")

@app.get("/")
def read_root():
    return {"message": "Carsharing API is running"}

@app.get("/cars")
def get_cars(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, brand, model, license_plate, status FROM cars LIMIT 10")).mappings().all()
    return {"cars": result}

@app.get("/rentals")
def get_rentals(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, customer_id, car_id, status FROM rentals LIMIT 10")).mappings().all()
    return {"rentals": result}