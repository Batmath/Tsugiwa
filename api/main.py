from fastapi import FastAPI
import sqlite3
import os
from .routes import users, entries
from .database import *

# LOCAL TEST : uvicorn src.api.main:app --reload --port 8000
app = FastAPI()

app.include_router(users.router)
app.include_router(entries.router)

@app.get("/progress")
def get_progress():
    conn = get_db()
    with closing(conn):
        users = query_users(conn,counting=True)
        ratings = query_ratings(conn,counting=True)
    return {"users": users, "ratings": ratings}