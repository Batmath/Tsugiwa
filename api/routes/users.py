from fastapi import APIRouter, Depends, HTTPException
from api.database import *

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
def get_users(gender:str|None = None, location:str|None = None, entries: int|None=None, min_entries: int|None=None, max_entries: int|None=None, min_birthday: int|None=None, max_birthday: int|None=None, birthday: int|None=None, 
                manga_id: int|None = None, min_score: int|None=None, max_score: int|None=None, status=None, genres=[], limit: int=100, offset: int=0, counting=False, conn: sqlite3.Connection = Depends(get_db)):
    genres_list = list(map(lambda x: int(x), genres.split(","))) if genres else []
    
    users = query_users(conn, gender=gender, location=location, min_entries=min_entries, max_entries=max_entries, min_birthday=min_birthday, max_birthday=max_birthday, manga_id=manga_id, 
                        min_score=min_score, max_score=max_score, genres=genres_list, status=status, limit=limit, offset=offset, counting=counting)
    return {"data" : users}

@router.get("/search")
def get_search_user(q:str = "", limit:int = 15, conn: sqlite3.Connection = Depends(get_db)):
        usernames = search_user(conn, q, limit)
    return {'data' : usernames}

@router.get("/{username}")
def get_user(username:str, conn: sqlite3.Connection = Depends(get_db)):
        user = query_users(conn, username=username)
    return {"data" : user[0] if user else []}

@router.get("/{username}/entries")
def get_user_ratings(username: str, min_score=None, max_score=None, limit=None, offset=None, status=None, counting=False,
                     genres=[]):

    conn = get_db()
    with closing(conn):
        genres_list = list(map(lambda x: int(x), genres.split(","))) if genres else []
        ratings = query_ratings(conn, username=username, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting,
                                genres=genres_list)
    return {"data" : ratings}

@router.get("/{username}/entries/full")
def get_full_user_ratings(username: str, min_score=None, max_score=None, limit=None, offset=None, status=None, genres=[]):
    # What if username is search ???
    conn = get_db()
    with closing(conn):
        genres_list = list(map(lambda x: int(x), genres.split(","))) if genres else []
        ratings = query_ratings(conn, username=username, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status,
                                genres=genres_list, full=True)
    return {"data" : ratings}