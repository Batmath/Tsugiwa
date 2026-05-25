import sqlite3
import os
from contextlib import closing

# Here the relative path depends on the name of the directory and the name of the database, find a way to make it "global"

DB_PATH = os.environ.get("DB_PATH", "data/scraped_data.db")

def get_db():
    print(DB_PATH)
    conn = sqlite3.connect("file:{}?mode=ro".format(DB_PATH), uri=True)
    conn.row_factory = sqlite3.Row
    return conn

# TODO : As a final design for the query architecure, add a master_query function that handles JOIN cases (do user need rating ? do rating need user ? or the three)

def query_users(conn, username=None, gender=None, location=None, min_entries=None, max_entries=None, limit=None, offset=None, counting=False):
    
    # TODO : Expand dynamic query building to add JOIN tables. (users having completed or read certain mangas | users h)
    target = "COUNT(*)" if counting else "*"
    query = """SELECT {} FROM users """.format(target)
    constraints = []
    params = []
    
    if username is not None:
        constraints.append("username = ? ")
        params.append(username)
    
    if min_entries is not None:
        constraints.append("score >= ?")
        params.append(min_entries)
    
    if max_entries is not None:
        constraints.append("score <= ?")
        params.append(max_entries)

    if gender is not None:
        constraints.append("gender = ? ")
        params.append(gender)

    if location is not None:
        constraints.append("location = ? ")
        params.append(location)

    if constraints:
        query += "WHERE " + " AND ".join(constraints)

    if not counting:
        if limit is not None:
            query += "LIMIT ? "
            params.append(limit)
        
        if offset is not None:
            query += "OFFSET ? "
            params.append(offset)

    users = conn.execute(query, (tuple(params))).fetchall()
    print(query)
    return users[0]['COUNT(*)'] if counting else [dict(u) for u in users]

def query_ratings(conn, username=None, manga_id=None, min_score=None, max_score=None, limit=None, offset=None, status=None, counting=False):

    # TODO : Expand dynamic query building to add JOIN tables. (ratings from users of a certain location, ratings from users within a certain genres etc.)
    target = "COUNT(*)" if counting else "*"
    params = []
    constraints = []
    
    query = "SELECT {} FROM entries ".format(target)

    if username is not None:
        constraints.append("username = ? ")
        params.append(username)

    if min_score is not None:
        constraints.append("score >= ? ")
        params.append(min_score)
    
    if max_score is not None:
        constraints.append("score <= ? ")
        params.append(max_score)
    
    if status is not None:
        constraints.append("status = ? ")
        params.append(status)
    
    if manga_id is not None:
        constraints.append("manga_id = ? ")
        params.append(manga_id)

    if constraints:
        query += "WHERE " + " AND ".join(constraints)

    if not counting:
        if limit is not None:
            query += "LIMIT ? "
            params.append(limit)
        
        if offset is not None:
            query += "OFFSET ? "
            params.append(offset)
    
    ratings = conn.execute(query, tuple(params)).fetchall()
    print(query)
    print(ratings)
    print(constraints)
    print(params)
    return ratings[0]['COUNT(*)'] if counting else [dict(r) for r in ratings]

if __name__ == "__main__":
    print("")