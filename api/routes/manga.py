from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.database import *

Conn = Annotated[sqlite3.Connection, Depends(get_db)]

router = APIRouter(prefix="/mangas", tags=["mangas"])

@router.get("/")
def get_manga(conn:Conn, min_mean:int|None=None, max_mean:int|None=None, genres:str|None=None, status:str|None=None, media_type:str|None= None, counting:bool=False, offset:int|None=0):

    genres_list = [int(x) for x in genres.split(",")] if genres is not None else []
    try:
        mangas = query_manga(conn, min_mean=min_mean, max_mean=max_mean, genres=genres_list, status=status, media_type=media_type, counting=counting, offset=offset, limit=200)
    except MangaNotFoundException:
        raise HTTPException(status_code=404, detail="Error: Mangas couldn't be found")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Server error encountered, try again")
    return {"data" : mangas}

@router.get("/search")
def get_search_manga(conn:Conn, q:str = "", limit:int = 15):
    try:
        manga_names = search_manga(conn, q, limit)
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Server error encountered, try again")
    return {'data' : manga_names}

@router.get("/{manga_id}")
def get_manga_per_id(manga_id:int, conn:Conn, counting:bool=False):
    try:
        mangas = query_manga(conn, manga_id=manga_id, counting=counting)
    except MangaNotFoundException:
        raise HTTPException(status_code=404, detail="Manga id could not be found")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Server error encountered, try again")
    return {"data" : mangas}

@router.get("/{manga_id}/full")
def get_manga_full_per_id(manga_id:int, conn:Conn, counting:bool=False):
    try:
        mangas = query_manga(conn, manga_id=manga_id, counting=counting, full=True)
    except MangaNotFoundException:
        raise HTTPException(status_code=404, detail="Manga id could not be found")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Server error encountered, try again")
    return {"data" : mangas}

