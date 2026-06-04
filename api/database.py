import sqlite3
import os
from contextlib import closing
from collections import defaultdict

# Here the relative path depends on the name of the directory and the name of the database, find a way to make it "global"

class InvalidParametersException(Exception):
    pass

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
        constraints.append("u.username = ?")
        params.append(username)

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
        query += " WHERE " + " AND ".join(constraints)

    if not counting:
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        if offset is not None:
            query += " OFFSET ?"
            params.append(offset)
    print(query)
    print(params)
    
    users = conn.execute(query, tuple(params)).fetchall()

    return (users[0][target] if counting else [dict(u) for u in users]) if users else []

def query_ratings(conn, username=None, manga_id=None, min_score=None, max_score=None, status=None,
        #join trigerring options
        gender=None, location=None, min_entries=None, max_entries=None, min_birthday=None, max_birthday=None, genres=[],
        #data manip
        limit=None, offset=None,  counting=False, full=False):

    # TODO : Expand dynamic query building to add JOIN tables. (ratings from users of a certain location, ratings from users within a certain genres etc.)
    target = "COUNT(DISTINCT e.username, e.manga_id)" if counting else "*"
    if counting : 
        target = "SELECT COUNT(*) FROM (SELECT DISTINCT e.username, e.manga_id FROM entries e{})"
    else:
        target = "SELECT * FROM entries e{}"
    query = ""

    genres_fetched = False
    joins = []
    constraints = []
    params = []
    
    if (gender or location or min_entries or max_entries or min_birthday or max_birthday):
        joins.append("JOIN users u ON u.username = e.username")
    
    if genres:
        joins.append("JOIN manga_genres mg ON e.manga_id = mg.manga_id")
        genres_fetched = True
    
    if full:
        if not genres:
            joins.append("JOIN manga_genres mg ON e.manga_id = mg.manga_id")
        joins.append("JOIN manga m ON e.manga_id = m.manga_id")
        genres_fetched = True
    
    if username is not None:
        constraints.append("e.username = ?")
        params.append(username)

    if min_score is not None:
        constraints.append("e.score >= ?")
        params.append(min_score)
    
    if max_score is not None:
        constraints.append("e.score <= ?")
        params.append(max_score)
    
    if status is not None:
        constraints.append("e.status = ?")
        params.append(status)
    
    if manga_id is not None:
        constraints.append("e.manga_id = ?")
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
        constraints.append("({})".format(" OR ".join(["mg.genre_id = ?" for i in range (len(genres))])))
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

    if joins:
        if genres_fetched:
            grouped_data = defaultdict(list)
            for rating in ratings:
                grouped_data[(rating['username'], rating['manga_id'])].append(dict(rating))
            
            genre_map = {genre['genre_id'] : genre['genre_name'] for genre in query_genres(conn)}
            res = [{'username' : key[0], 
                    'manga_id' : key[1],
                    'genres' : [{'genre_id' : rating['genre_id'],'genre' : genre_map[rating['genre_id']]} for rating in val],
                    'status' : val[0]['status'],
                    'read_chapters' : val[0]['read_chapters'],
                    'score' :  val[0]['score'],  'start_date_string' :  val[0]['start_date_string'],'end_date_string' :  val[0]['end_date_string'], 'status' : val[0]['status'] } for key, val in grouped_data.items()]
            if full:
                for entry in res :
                    matching_entries = grouped_data[(entry['username'], entry['manga_id'])]
                    entry['manga'] = {
                        'manga_id' : entry['manga_id'], 
                        'title' : matching_entries[0]['title'], 
                        'title_japanese' : matching_entries[0]['title_japanese'],
                        'media_type' : matching_entries[0]['media_type'],
                        'genres' : entry.pop('genres'),
                        'demographics' : matching_entries[0]['demographics'],
                        'scored_by' : matching_entries[0]['scored_by'],
                        'rank' : matching_entries[0]['rank'],
                        'popularity_rank' : matching_entries[0]['popularity_rank'],
                        'members' : matching_entries[0]['members'],
                        'favorites' : matching_entries[0]['favorites'],
                        'publishing' : matching_entries[0]['publishing'],
                        'published_from' : matching_entries[0]['published_from'],
                        'published_to' : matching_entries[0]['published_to'],
                        'chapters' : matching_entries[0]['chapters'],
                        'volumes' : matching_entries[0]['volumes'],
                        'authors' : matching_entries[0]['authors'],
                        'url_img' : matching_entries[0]['url_img'],
                        'synopsis' : matching_entries[0]['synopsis']
                    }
                    entry.pop('manga_id')
                    
        else:
           res = [dict(r) for r in ratings] 
    else:
        res = [dict(r) for r in ratings]
    return ratings[0]['COUNT(*)'] if counting else res

def query_genres(conn, genre_id=None, counting=False):

    target = "COUNT(*)" if counting else "*"
    query = "SELECT {} FROM genres".format(target)

    constraints = []
    params = []

    if genre_id:
        constraints.append("genre_id = ?")
        params.append(genre_id)
    
    if constraints:
        query += " WHERE " + " AND ".join(constraints)
    
    genres = conn.execute(query, tuple(params)).fetchall()
    return genres[0]['COUNT(*)'] if counting else [dict(r) for r in genres]

def query_manga(conn, manga_id, media_type, status, min_mean, max_mean,
                #filter triggering
                genres, full=False,
                #data manip
                limit=None, offset=None, counting = True
                ):
    target = "COUNT(DISTINCT m.manga_id)" if counting else "DISTINCT m.*"
    query = """SELECT {} FROM manga m""".format(target)

    joins = []
    constraints = []
    params = []

    if genres:
        joins.append("JOIN manga_genres mg ON m.manga_id = mg.manga_id")        

    if manga_id is not None:
        constraints.append("m.manga_id = ?")
        params.append(username)

    if media_type is not None:
        constraints.append("m.media = ?")
        params.append(media_type)

    if status is not None:
        constraints.append("m.status = ?")
        params.append(status)

    if min_entries is not None:
        constraints.append("m.mean >= ?")
        params.append(min_mean)
    
    if max_mean is not None:
        constraints.append("m.mean <= ?")
        params.append(max_mean)
    
    if genres:
        constraints.append("({})".format(" OR ".join(["mg.genre_id = ?" for i in range (len(genres))])))
        params.extend(genres)

def search_user(conn, string, limit=10):
    #naive search engine : 
    
    #TODO : look 
    params = ["%{}%".format(string), limit]
    req = "SELECT username FROM users WHERE username LIKE ? LIMIT ?"
    users = conn.execute(req, tuple(params)).fetchall()
    print(string)
    usernames = [user[0] for user in users]
    print(usernames)
    return usernames

if __name__ == "__main__":
    print("")