from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Real Estate Service API")

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/listings")
def get_listings(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, listing_type, price, status FROM listings LIMIT 10")).mappings().all()
    return {"listings": result}

@app.get("/properties")
def get_properties(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, address, district, area_sqm FROM properties LIMIT 10")).mappings().all()
    return {"properties": result}
