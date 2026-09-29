from fastapi import FastAPI, Depends, HTTPException
import sqlite3
import os
from api.routes import users, entries, genres
from api.database import *
import uvicorn

# LOCAL TEST : uvicorn api.main:app --reload --port 8080
app = FastAPI()

app.include_router(users.router)
app.include_router(entries.router)
app.include_router(genres.router)

@app.get("/progress")
def get_progress(conn: sqlite3.Connection = Depends(get_db)):
    users = query_users(conn,counting=True)
    ratings = query_ratings(conn,counting=True)
    return {"users": users, "ratings": ratings}

@app.get("/health")
def get_health(conn: sqlite3.Connection = Depends(get_db)):
    conn.execute("SELECT 1")
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("api.main:app", host=param["HOST_IP_ADDRESS"], port=param["API_PORT"])