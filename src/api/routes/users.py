from fastapi import APIRouter
from ..database import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
def get_users(limit: int = 100, offset: int = 0):
    conn = get_db()
    users = get_users(conn, limit, offset)
    return users

@router.get("/{username}/ratings")
def get_user_ratings(username: str):
    conn = get_db()
    ratings = conn.execute("""SELECT * FROM ratings WHERE username = ?""", (username,)).fetchall()
    return [dict(r) for r in ratings]