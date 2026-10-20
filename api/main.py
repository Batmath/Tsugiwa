import sqlite3
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI

from api.database import *
from api.routes import entries, genres, manga, users

app = FastAPI()

app.include_router(users.router)
app.include_router(entries.router)
app.include_router(genres.router)
app.include_router(manga.router)

Conn = Annotated[sqlite3.Connection, Depends(get_db)]

@app.get("/progress")
def get_progress(conn: Conn):
    users = query_users(conn,counting=True)
    ratings = query_ratings(conn,counting=True)
    return {"users": users, "ratings": ratings}

@app.get("/health")
def get_health(conn: Conn):
    conn.execute("SELECT 1")
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("api.main:app", host=param["HOST_IP_ADDRESS"], port=param["API_PORT"])
