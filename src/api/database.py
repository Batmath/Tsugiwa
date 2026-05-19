import sqlite3
import os

# Here the relative path depends on the name of the directory and the name of the database, find a way to make it "global"

DB_PATH = os.environ.get("DB_PATH", "data/raw_scraped_data.db")

def get_db():
    print(DB_PATH)
    conn = sqlite3.connect("file:{}?mode=ro".format(DB_PATH), uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def get_users(conn, limit= 100, offset=0):
    users = conn.execute("""SELECT * FROM users LIMIT ? OFFSET ?""", (limit, offset)).fetchall()
    return [dict(u) for u in users]

def get_user():
    return

def get_count_users():
    return

def get_ratings(conn, username, min_score=None, max_score=None, limit=None, offset=None, status=None, rating_filter="all"):
    # rating_filter takes all, rated_only,
    query = "SELECT * FROM ratings WHERE username = ?"
    params = [username]

    score_conditions = []
    if min_score is not None:
        score_conditions.append("score >= ?")
        params.append(min_score)
    
    if max_score is not None:
        score_conditions.append("score <= ?")
        pramas.append(max_score)
    
    nb_conditions = len(score_conditions)

    bound=""
    if  nb_conditions == 1:
        bound =  "{}".format(score_conditions[0])
    elif nb_conditions == 2:
        bounds = " AND ".join(score_conditions)

    if rating_filter=="all":
            query += " AND ({} OR score IS NULL)".join(bounds)
        # If no bounds at all, no conditions on min or max score and no need to specify that the score is null
    return
    
def get_user_rating():
    return