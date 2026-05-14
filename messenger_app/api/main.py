from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

app = FastAPI(title="Messenger API")

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/chats")
def get_chats(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, name, chat_type FROM chats LIMIT 10")).mappings().all()
    return {"chats": result}

@app.get("/messages")
def get_messages(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, sender_id, chat_id, content FROM messages LIMIT 10")).mappings().all()
    return {"messages": result}
