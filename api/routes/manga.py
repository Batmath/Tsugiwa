from fastapi import APIRouter, Depends, HTTPException
from api.database import *

router = APIRouter(prefix="/mangas", tags=["mangas"])


@router.get("/")
def get_manga(min_mean=None, max_mean=None, genres=[], status=None, media_type= None, counting=False, offset=0,
              conn: sqlite3.Connection = Depends(get_db)):
    
    genres_list = list(map(lambda x: int(x), genres.split(","))) if genres else []
    try:
        mangas = query_manga(conn, min_mean=min_mean, max_mean=max_mean, genres=genres_list, status=status, media_type=media_type, counting=counting, offset=offset, limit=200)
    except MangaNotFoundException:
        return HTTPException(status_code=404, content="Error: Mangas couldn't be found")
    except sqlite3.Error:
        return HTTPException(status_code=500, content="Server error encountered, try again")
    return {"data" : mangas}

@router.get("/{manga_id}")
def get_manga_per_id(counting=False, conn: sqlite3.Connection = Depends(get_db)):
    try:
        mangas = query_manga(conn, manga_id=manga_id, counting=counting)
    except MangaNotFoundException:
        return HTTPException(status_code=404, content="Manga id could not be found")
    except sqlite3.Error:
        return HTTPException(status_code=500, content="Server error encountered, try again")
    return {"data" : mangas}

@router.get("/{manga_id}/full")
def get_manga_full_per_id(counting=False, conn: sqlite3.Connection = Depends(get_db)):
    try:
        mangas = query_manga(conn, manga_id=manga_id, counting=counting, full=True)
    except MangaNotFoundException:
        return HTTPException(status_code=404, content="Manga id could not be found")
    except sqlite3.Error:
        return HTTPException(status_code=500, content="Server error encountered, try again")
    return {"data" : mangas}