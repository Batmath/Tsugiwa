from fastapi import APIRouter, Depends, HTTPException
from api.database import *

router = APIRouter(prefix="/genres", tags=["genres"])

@router.get("/")
def get_genres(counting=False, conn: sqlite3.Connection = Depends(get_db)):
        genres = query_genres(conn, counting)
    return {"data" : genres}

@router.get("/{genre_id}")
def get_genre(counting=False, conn: sqlite3.Connection = Depends(get_db)):
    return {"data" : genres}

"""@router.get("/manga/{manga_id}")
def get_manga_genres(counting=False):
    conn = get_db()
    with closing(conn):
        genres = query_genres(conn, counting)
    return {"data" : genres}"""