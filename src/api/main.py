from fastapi import FastAPI
import sqlite3
import os
from .routes import users, ratings

# LOCAL TEST : uvicorn src.api.main:app --reload --port 8000
app = FastAPI()

app.include_router(users.router)
app.include_router(ratings.router)

@app.get("/progress")
def get_progress():
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    ratings = conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    return {"users": users, "ratings": ratings}