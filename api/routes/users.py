from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.database import *

Conn = Annotated[sqlite3.Connection, Depends(get_db)]

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
def get_users(conn:Conn, gender:str|None = None, location:str|None = None, min_entries:int|None=None, max_entries:int|None=None, min_birthday:int|None=None, max_birthday:int|None=None,
                manga_id:int|None = None, min_score:int|None=None, max_score:int|None=None, status:str|None=None, genres:str|None=None, limit:int=100, offset:int=0, order_by_rating:bool = False, counting:bool=False):
    genres_list = [int(x) for x in genres.split(",")] if genres is not None else []

    users = query_users(conn, gender=gender, location=location, min_entries=min_entries, max_entries=max_entries, min_birthday=min_birthday, max_birthday=max_birthday, manga_id=manga_id,
                        min_score=min_score, max_score=max_score, genres=genres_list, status=status, order_by_rating=order_by_rating, limit=limit, offset=offset, counting=counting)
    return {"data" : users}

@router.get("/search")
def get_search_user(conn:Conn, q:str = "", limit:int = 15):
    try:
        usernames = search_user(conn, q, limit)
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Server error encountered, try again")
    return {'data' : usernames}

@router.get("/{username}")
def get_user(conn:Conn, username:str):
    try:
        user = query_users(conn, username=username)
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="Error when fetching user : username not found.")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Server error encountered, try again")
    return {"data" : user[0] if user else []}
