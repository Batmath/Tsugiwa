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

# TODO : Harmonize queries, keep one per table handling joins in each of them.
# TODO : Add manga queries

def query_users(conn, username=None, gender=None, location=None, min_entries=None, max_entries=None, min_birthday=None, max_birthday=None,
    #filtering options
    manga_id=None, min_score=None, max_score=None, status=None, genres=[],
    # data manip
    limit=None, offset=None, counting=False):
    
    # TODO : Expand dynamic query building to add JOIN tables. (users having completed or read certain mangas | users h)
    target = "COUNT(DISTINCT u.username)" if counting else "DISTINCT u.*"
    query = """SELECT {} FROM users u""".format(target)

    joins = []
    constraints = []
    params = []
    
    if (manga_id or status or max_score or min_score):
        joins.append("JOIN entries e ON u.username = e.username")

    if genres:
        if not(manga_id or status or max_score or min_score):
            joins.append("JOIN entries e ON u.username = e.username")
        joins.append("JOIN manga_genres m ON e.manga_id = m.manga_id")


    if username is not None:
        constraints.append("username = ? ")
        params.append(username)

    if min_birthday is not None:
        constraints.append("u.birthday >= ?")
        params.append(min_birthday)

    if max_birthday is not None:
        constraints.append("u.birthday <= ?")
        params.append(max_birthday)

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
    
    if manga_id is not None:
        constraints.append("e.manga_id = ?")
        params.append(manga_id)
    
    if min_score is not None:
        constraints.append("e.score >= ?")
        params.append(min_entries)
    
    if max_score is not None:
        constraints.append("e.score <= ?")
        params.append(max_entries)

    if status is not None:
        constraints.append("e.status = ?")
        params.append(status)

    if genres:
        constraints.append("({})".format(" OR ".join(["m.genre_id = ?" for i in range (len(genres))])))
        params.extend(genres)

    if joins:
        query += " " + " ".join(joins)

    if constraints:
        query += "WHERE " + " AND ".join(constraints)

    if not counting:
        if limit is not None:
            query += "LIMIT ? "
            params.append(limit)
        
        if offset is not None:
            query += "OFFSET ? "
            params.append(offset)
    print(query)
    print(params)
    
    users = conn.execute(query, tuple(params)).fetchall()

    return (users[0][target] if counting else [dict(u) for u in users]) if users else []

def query_ratings(conn, username=None, manga_id=None, min_score=None, max_score=None, status=None,
        #join trigerring options
        gender=None, location=None, min_entries=None, max_entries=None, min_birthday=None, max_birthday=None, genres=[],
        #data manip
        limit=None, offset=None,  counting=False):

    # TODO : Expand dynamic query building to add JOIN tables. (ratings from users of a certain location, ratings from users within a certain genres etc.)
    target = "COUNT(DISTINCT e.username, e.manga_id)" if counting else "*"
    if counting : 
        target = "SELECT COUNT(*) FROM (SELECT DISTINCT e.username, e.manga_id FROM entries e{})"
    else:
        target = "SELECT * FROM entries e{}"
    query = ""

    joins = []
    constraints = []
    params = []
    
    if (gender or location or min_entries or max_entries or min_birthday or max_birthday):
        joins.append("JOIN users u ON u.username = e.username")
    
    if genres:
        joins.append("JOIN manga_genres m ON e.manga_id = m.manga_id")
    
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
    
    # Join triggering options

    if min_birthday is not None:
        constraints.append("u.birthday >= ?")
        params.append(min_birthday)
        
    if max_birthday is not None:
        constraints.append("u.birthday <= ?")
        params.append(max_birthday)

    if min_entries is not None:
        constraints.append("u.entries >= ?")
        params.append(min_entries)
    
    if max_entries is not None:
        constraints.append("u.entries <= ?")
        params.append(max_entries)

    if gender is not None:
        constraints.append("u.gender = ?")
        params.append(gender)

    if location is not None:
        constraints.append("u.location = ?")
        params.append(location)
    
    if genres:
        constraints.append("({})".format(" OR ".join(["m.genre_id = ?" for i in range (len(genres))])))
        params.extend(genres)

    if joins:
        query += " " + " ".join(joins)

    if constraints:
        query += " WHERE " + " AND ".join(constraints)

    if not counting:
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        if offset is not None:
            query += " OFFSET ?"
            params.append(offset)
    
    req = target.format(query)
    print(req)
    print(constraints)
    print(params)

    ratings = conn.execute(req, tuple(params)).fetchall()
    print(ratings)
    if not ratings:
        return []
    return ratings[0]['COUNT(*)'] if counting else [dict(r) for r in ratings]

if __name__ == "__main__":
    print("")