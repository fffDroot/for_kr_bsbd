from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Hotel Booking API")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API is running"}

@app.get("/hotels")
def get_hotels(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, name, city, stars FROM hotels LIMIT 10")).mappings().all()
    return {"hotels": result}

@app.get("/bookings")
def get_bookings(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, check_in_date, check_out_date, status FROM bookings LIMIT 10")).mappings().all()
    return {"bookings": result}
