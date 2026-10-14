from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.database import *

Conn = Annotated[sqlite3.Connection, Depends(get_db)]

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("/manga/{manga_id}")
def get_manga_entries(manga_id:int, conn:Conn, min_score: int|None=None, max_score: int|None=None, limit: int|None=200, offset: int|None=None, status: str|None=None, counting:bool=False,
                    gender: str|None=None, location: str|None=None, min_entries:int|None=None, max_entries:int|None=None, min_birthday:int|None=None, max_birthday:int|None=None):

    entries = query_ratings(conn, manga_id=manga_id, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting,
                            gender=gender,location=location, min_entries=min_entries, max_entries=max_entries, min_birthday=min_birthday, max_birthday=max_birthday)
    return {"data" : entries}

@router.get("/")
def get_entries(conn:Conn, min_score:int|None=None, max_score: int|None=None, limit: int|None=200, offset: int|None=None, status:str|None=None, counting:bool=False,
                gender: str|None=None, location: str|None=None, min_entries: int|None=None, max_entries: int|None=None, min_birthday: int|None=None, max_birthday: int|None=None, genres: str|None=None):

    genres_list = [int(x) for x in genres.split(",")] if genres is not None else []

    entries = query_ratings(conn, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting,
                            gender=gender,location=location, min_entries=min_entries, max_entries=max_entries, min_birthday=min_birthday,
                            max_birthday=max_birthday, genres=genres_list)

    return {"data" : entries}

@router.get("/user/{username}")
def get_user_ratings(username:str, conn:Conn, min_score: int|None=None, max_score: int|None=None, limit: int|None=None, offset: int|None=None, status: str|None=None, counting:bool=False,
                     genres: str|None=None):

    genres_list = [int(x) for x in genres.split(",")] if genres is not None else []
    try:
        ratings = query_ratings(conn, username=username, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting,
                                genres=genres_list)
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="Error when fetching entries : User couldn't be found.")
    return {"data" : ratings}

@router.get("/user/{username}/full")
def get_full_user_ratings(username: str, conn:Conn, min_score: int|None=None, max_score: int|None=None, limit: int|None=None, offset: int|None=None, status: str|None=None, genres: str|None=None):
    # What if username is search ???
    genres_list = [int(x) for x in genres.split(",")] if genres is not None else []
    try:
        ratings = query_ratings(conn, username=username, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status,
                                genres=genres_list, full=True)
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="Error when fetching entries : User couldn't be found.")
    return {"data" : ratings}
