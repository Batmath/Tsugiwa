from fastapi import APIRouter, Depends, HTTPException
from api.database import *

router = APIRouter(prefix="/genres", tags=["genres"])

@router.get("/")
def get_genres(counting=False, conn: sqlite3.Connection = Depends(get_db)):
    try:
        genres = query_genres(conn, counting)
    except sqlite3.Error:
        return HTTPException(status_code=500, content="Server error encountered, try again")
    return {"data" : genres}

@router.get("/{genre_id}")
def get_genre(counting=False, conn: sqlite3.Connection = Depends(get_db)):
    try:
        genres = query_genres(conn, genre_id, counting)
    except GenreNotFoundException:
        return HTTPException(status_code=404, content="Error when fetching genre : genre id couldn't be found.")
    except sqlite3.Error:
        return HTTPException(status_code=500, content="Server error encountered, try again")
    return {"data" : genres}

"""@router.get("/manga/{manga_id}")
def get_manga_genres(counting=False):
    conn = get_db()
    with closing(conn):
        genres = query_genres(conn, counting)
    return {"data" : genres}"""