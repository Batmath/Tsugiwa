from fastapi import FastAPI
import sqlite3
import os
from .routes import users, entries, genres
from .database import *

# LOCAL TEST : uvicorn api.main:app --reload --port 8080
app = FastAPI()

app.include_router(users.router)
app.include_router(entries.router)
app.include_router(genres.router)

@app.get("/progress")
def get_progress():
    conn = get_db()
    with closing(conn):
        users = query_users(conn,counting=True)
        ratings = query_ratings(conn,counting=True)
    return {"users": users, "ratings": ratings}