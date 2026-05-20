from fastapi import APIRouter
from ..database import *

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
def get_users(gender:str|None = None, location=None, min_entries=None, max_entries=None, limit=100, offset=0, counting=False):
    conn = get_db()
    with closing(conn):
        users = query_users(conn, gender=gender, location=location, min_entries=min_entries, max_entries=max_entries, limit=limit, offset=offset, counting=counting)
    return users

@router.get("/{username}")
def get_user(username:str):
    conn = get_db()
    with closing(conn):
        user = query_users(conn, username=username)
    return user

@router.get("/{username}/ratings")
def get_user_ratings(username: str, min_score=None, max_score=None, limit=None, offset=None, status=None, counting=False):
    conn = get_db()
    with closing(conn):
        ratings = query_ratings(conn, username=username, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting)
    return ratings