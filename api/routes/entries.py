from fastapi import APIRouter
from ..database import *

router = APIRouter(prefix="/entries", tags=["entries"])

# Avoir des ratings par manga ! 

@router.get("/{manga_id}")
def get_manga_entries(manga_id, min_score=None, max_score=None, limit=None, offset=None, status=None, counting=False, 
                    gender=None, location=None, min_entries=None, max_entries=None, min_birthday=None, max_birthday=None):

    conn = get_db()
    with closing(conn):
        entries = query_ratings(conn, manga_id=manga_id, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting, 
                                gender=gender,location=location, min_entries=min_entries, max_entries=max_entries, min_birthday=min_birthday, max_birthday=max_birthday)
    return {"data" : entries}

@router.get("/")
def get_entries(manga_id=None, min_score=None, max_score=None, limit=None, offset=None, status=None, counting=False,
                gender=None, location=None, min_entries=None, max_entries=None, min_birthday=None, max_birthday=None, genres=[]):

    conn = get_db()
    with closing(conn):
        genres_list = list(map(lambda x: int(x), genres.split(","))) if genres else []
        print(genres_list)
        entries = query_ratings(conn, manga_id=manga_id, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting,
                                gender=gender,location=location, min_entries=min_entries, max_entries=max_entries, min_birthday=min_birthday, max_birthday=max_birthday, genres=genres_list)
    return {"data" : entries}
