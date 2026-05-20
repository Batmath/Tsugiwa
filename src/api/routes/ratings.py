from fastapi import APIRouter
from ..database import *

router = APIRouter(prefix="/ratings", tags=["ratings"])

# Avoir des ratings par manga ! 

@router.get("/{manga_id}")
def get_ratings(manga_id, min_score=None, max_score=None, limit=None, offset=None, status=None, counting=False):
    conn = get_db()
    with closing(conn):
        users = query_ratings(conn, manga_id=manga_id, min_score=min_score, max_score=max_score, limit=limit, offset=offset, status=status, counting=counting)
    return users
