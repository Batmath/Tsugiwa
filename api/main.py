from fastapi import FastAPI
import sqlite3
import os
from api.routes import users, entries, genres
from api.database import *
from api.settings import ParametersAPI
import uvicorn

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

@app.get("/health")
def get_health():
    conn = get_db()
    with closing(conn):
        result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
    print(result)
    return result == "true"

if __name__ == "__main__":
    param = ParametersAPI().model_dump()
    uvicorn.run("api.main:app",
        host=param["HOST_IP_ADDRESS"],
        port=param["API_PORT"])