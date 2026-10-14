from fastapi import APIRouter, Depends, HTTPException
from api.database import *

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("/manga/{manga_id}")
def get_manga_entries(manga_id, min_score=None, max_score=None, limit=200, offset=None, status=None, counting=False, 
                    gender=None, location=None, min_entries=None, max_entries=None, min_birthday=None, max_birthday=None, conn: sqlite3.Connection = Depends(get_db)):
    
    entries = query_ratings(conn, manga_id=manga_id, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting, 
                            gender=gender,location=location, min_entries=min_entries, max_entries=max_entries, min_birthday=min_birthday, max_birthday=max_birthday)
    return {"data" : entries}

@router.get("/")
def get_entries(min_score=None, max_score=None, limit=200, offset=None, status=None, counting=False,
                gender=None, location=None, min_entries=None, max_entries=None, min_birthday=None, max_birthday=None, genres=[], conn: sqlite3.Connection = Depends(get_db)):
    
    genres_list = list(map(lambda x: int(x), genres.split(","))) if genres else []

    entries = query_ratings(conn, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting,
                            gender=gender,location=location, min_entries=min_entries, max_entries=max_entries, min_birthday=min_birthday, 
                            max_birthday=max_birthday, genres=genres_list)

    return {"data" : entries}

@router.get("/user/{username}")
def get_user_ratings(username: str, min_score=None, max_score=None, limit=None, offset=None, status=None, counting=False,
                     genres=[], conn: sqlite3.Connection = Depends(get_db)):

    genres_list = list(map(lambda x: int(x), genres.split(","))) if genres else []
    try:
        ratings = query_ratings(conn, username=username, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting,
                                genres=genres_list)
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="Error when fetching entries : User couldn't be found.")
    return {"data" : ratings}

@router.get("/user/{username}/full")
def get_full_user_ratings(username: str, min_score=None, max_score=None, limit=None, offset=None, status=None, genres=[], conn: sqlite3.Connection = Depends(get_db)):
    # What if username is search ???
    genres_list = list(map(lambda x: int(x), genres.split(","))) if genres else []
    try:
        ratings = query_ratings(conn, username=username, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status,
                                genres=genres_list, full=True)
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="Error when fetching entries : User couldn't be found.")
    return {"data" : ratings}
