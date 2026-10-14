from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.database import *

Conn = Annotated[sqlite3.Connection, Depends(get_db)]

router = APIRouter(prefix="/genres", tags=["genres"])

@router.get("/")
def get_genres(conn:Conn, counting:bool=False):
    try:
        genres = query_genres(conn, counting)
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Server error encountered, try again")
    return {"data" : genres}

@router.get("/{genre_id}")
def get_genre(genre_id :int, conn:Conn, counting:bool=False):
    try:
        genres = query_genres(conn, genre_id, counting)
    except GenreNotFoundException:
        raise HTTPException(status_code=404, detail="Error when fetching genre : genre id couldn't be found.")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Server error encountered, try again")
    return {"data" : genres}
