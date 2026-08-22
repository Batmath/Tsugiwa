from fastapi import APIRouter
from api.database import *

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
def get_users(gender:str|None = None, location=None, entries=None, min_entries=None, max_entries=None, min_birthday=None, max_birthday=None, birthday=None, 
                manga_id=None, min_score=None, max_score=None, status=None, genres=[], limit=100, offset=0, counting=False):
    conn = get_db()
    with closing(conn):
        genres_list = list(map(lambda x: int(x), genres.split(","))) if genres else []
        users = query_users(conn, gender=gender, location=location, min_entries=min_entries, max_entries=max_entries, min_birthday=min_birthday, max_birthday=max_birthday, manga_id=manga_id, 
                            min_score=min_score, max_score=max_score, genres=genres_list, status=status, limit=limit, offset=offset, counting=counting)
    return {"data" : users}

@router.get("/search")
def get_search_user(q: str = "", limit = 15):
    conn = get_db()
    with closing(conn):
        usernames = search_user(conn, q, limit)
    return {'data' : usernames}

@router.get("/{username}")
def get_user(username:str):
    conn = get_db()
    with closing(conn):
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