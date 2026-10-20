import sqlite3
from collections import defaultdict

from api.settings import ParametersAPI


class InvalidParametersException(Exception):
    pass

class UserNotFoundException(Exception):
    pass

class MangaNotFoundException(Exception):
    pass

class GenreNotFoundException(Exception):
    pass

class EntriesNotFoundException(Exception):
    pass

param = ParametersAPI().model_dump()

def get_db():
    conn = sqlite3.connect("file:{}?mode=ro".format(param["DB_PATH"]), uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

class Where:
    def __init__(self):
        self.clauses = []
        self.params = []

    def add(self, clause, *values):
        if values[0] is not None and values[0] != []:
            self.clauses.append(clause)
            self.params.extend(values[0] if type(values[0]) == list else [values[0]])

    def empty(self):
        return self.clauses == []

    def sql(self):
        return "WHERE " + " AND ".join(self.clauses)

    def parameters(self):
        return self.params

# TODO : Harmonize queries, keep one per table handling joins in each of them.
# TODO : Add manga queries

def query_users(conn, username:str|None =None, gender:str|None=None, location:str|None=None, min_entries:int|None=None, max_entries:int|None=None, min_birthday:int|None=None, max_birthday:int|None=None,
    #filtering options
    manga_id:int|None=None, min_score:int|None=None, max_score:int|None=None, status:str|None=None, genres:list | None=None,
    # data manip
    order_by_rating:bool=False, limit:int|None=None, offset:int|None=None, counting:bool=False) -> list | int:

    """
        Method to query for ratings rows from the database.

        :param username: username of the user who's searched
        :type username: str | None

        :param gender: gender of the user searched
        :type gender: str | None

        :param location: location of the user for the entries queried
        :type location: str | None

        :param min_entries: minimum amount of entries required for the user searched
        :type min_entries: int | None

        :param max_entries: maximum amount of entries required for the user searched
        :type max_entries: int | None

        :param min_birthday: minimum birthday year for the user searched
        :type min_birthday: int | None

        :param max_birthday: minimum birthday year for the user searched
        :type max_birthday: int | None

        :param manga_id: id of a manga that should be in the entries of the users queried
        :type manga_id: int | None

        :param min_score: minimum score required for the ratings of entries for the users queried
        :type min_score: int | None
        
        :param max_score: maximum score required for the ratings of the entries for the users queried
        :type max_score: int | None

        :param status: reading status of the entries in the list of the users queried
        :type status: str | None

        :param genres: list of genres that the manga(s) should possess (This query imply a join between the manga and manga_genres tables)
        :type genres: list

        :param full: boolean variable to indicate if every information from every tables should be fetched.
        :type full: bool

        :param counting: boolean variable to indicate if the query should return the count of result or not
        :type genres: bool

        :param limit: numerical limit for the likely answers
        :type limit: int
    
        :return: List of the manga(s) queried or count
        :rtype: list | int
    """

    # TODO : Expand dynamic query building to add JOIN tables. (users having completed or read certain mangas | users h)
    if genres is None:
        genres = []
    target = "COUNT(DISTINCT u.user_id)" if counting else "DISTINCT u.*"
    query = f"""SELECT {target} FROM users u """

    joins = []
    constraints = []

    if (manga_id or status or max_score or min_score):
        joins.append("JOIN entries e ON u.user_id = e.user_id ")

    if genres:
        if not(manga_id or status or max_score or min_score):
            joins.append("JOIN entries e ON u.user_id = e.user_id ")
        joins.append("JOIN manga_genres m ON e.manga_id = m.manga_id ")

    constraints = Where()
    constraints.add("u.username = ?", username)
    constraints.add("u.birthday >= ?", min_birthday)
    constraints.add("u.birthday <= ?", max_birthday)
    constraints.add("u.entries >= ?", min_entries)
    constraints.add("u.entries <= ?", max_entries)
    constraints.add("u.gender = ?", gender)
    constraints.add("u.location = ?", location)
    constraints.add("e.manga_id = ?", manga_id)
    constraints.add("u.location = ?", location)
    constraints.add("e.score >= ?", min_score)
    constraints.add("e.score <= ?", max_score)
    constraints.add("e.status = ?", status)
    constraints.add("({})".format(" OR ".join(["m.genre_id = ?" for i in range (len(genres))])), genres)

    if joins:
        query += " " + " ".join(joins)

    if not(constraints.empty()):
        query += constraints.sql()

    if not counting:
        if limit is not None:
            query += " LIMIT ?"
            constraints.params.append(limit)

        if offset is not None:
            query += " OFFSET ?"
            constraints.params.append(offset)

    if order_by_rating:
        query += "ORDER BY "
        constraints.param.append("u.entries DESC ")

    users = conn.execute(query, tuple(constraints.params)).fetchall()

    if users is not None:
        return (users[0][target] if counting else [dict(u) for u in users])
    else:
        raise UserNotFoundException

#TODO: Rewrite the query logic for genres
def query_ratings(conn, username:str|None=None, manga_id:int|None=None, min_score:int|None=None, max_score:int|None=None, status=None,
        #join trigerring options
        gender:str|None=None, location:str|None=None, min_entries:int|None=None, max_entries:int|None=None, min_birthday:int|None=None, max_birthday:int|None=None, genres=None,
        #data manip
        min_mean:int|None=None, max_mean:int|None=None, media_type:str|None=None, publishing_status:str|None=None,

        limit:int|None=None, offset:int|None=None,  counting:bool=False, full:bool=False) -> list | int:

    """
        Method to query for ratings rows from the database.

        :param username: username of the user whose entries are searched
        :type username: str | None

        :param manga_id: id of the manga searched for which the entries are searched.
        :type manga_id: int | None

        :param min_score: minimum score required for the ratings of the entries queried
        :type min_score: int | None
        
        :param max_score: maximum score required for the ratings of the entries queried
        :type max_score: int | None

        :param gender: gender of the user for the entries queried
        :type gender: str | None
            
        :param location: location of the user for the entries queried
        :type location: str | None
        
        :param min_entries: minimum amount of entries required for the user of the entries queried
        :type min_entries: int | None

        :param max_entries: maximum amount of entries required for the user of the entries queried
        :type max_entries: int | None

        :param min_birthday: minimum birthday year for the user of the entries queried
        :type min_birthday: int | None

        :param max_birthday: minimum birthday year for the user of the entries queried
        :type max_birthday: int | None
        
        :param media_type: type of the media(s) queried
        :type media_type: int | None

        :param status: reading status of the entry queried
        :type status: str | None

        :param pbulishing_status: publishing status of the manga for the entries queried
        :type pbulishing_status: str | None
        
        :param min_mean: minimum mean thereshold applied to the query
        :type min_mean: int | None

        :param min_mean: maximum mean thereshold applied to the query
        :type min_mean: int | None

        :param genres: list of genres that the manga(s) should possess (This query imply a join between the manga and manga_genres tables)
        :type genres: list

        :param full: boolean variable to indicate if every information from every tables should be fetched.
        :type full: bool

        :param counting: boolean variable to indicate if the query should return the count of result or not
        :type genres: bool

        :param limit: numerical limit for the likely answers
        :type limit: int
    
        :return: List of the manga(s) queried or count
        :rtype: list | int
    """
    if genres is None:
        genres = []
    query = "SELECT COUNT(*) FROM entries e " if counting else "SELECT * FROM entries e "

    constraints = Where()
    genres_fetched = False
    joins = []
    if username is not None:
        req_id = conn.execute("SELECT user_id FROM users WHERE username = ?", (username,)).fetchone()
        if req_id is None :
            raise UserNotFoundException
        id = req_id[0]

        constraints.add("e.user_id = ?", id)

    if (username or gender or location or min_entries or max_entries or min_birthday or max_birthday or full):
        joins.append("JOIN users u ON u.user_id = e.user_id ")

    if genres != [] or full:
        joins.append("JOIN manga_genres mg ON e.manga_id = mg.manga_id ")
        genres_fetched = True

    if (publishing_status or min_mean or max_mean or media_type or full):
        joins.append("JOIN manga m ON e.manga_id = m.manga_id ")

    constraints.add("e.score >= ?", min_score)
    constraints.add("e.score <= ?", max_score)
    constraints.add("e.status = ?", status)
    constraints.add("e.manga_id = ?", manga_id)
    constraints.add("u.birthday >= ?", min_birthday)
    constraints.add("u.birthday <= ?", max_birthday)
    constraints.add("u.entries >= ?", min_entries)
    constraints.add("u.entries <= ?", max_entries)
    constraints.add("u.gender = ?", gender)
    constraints.add("u.location = ?", location)
    constraints.add("m.mean_score >= ?", min_mean)
    constraints.add("m.mean_score <= ?", max_mean)
    constraints.add("m.media_type <= ?", media_type)
    constraints.add("m.status = ?", publishing_status)
    constraints.add("({})".format(" OR ".join(["m.genre_id = ?" for i in range (len(genres))])), genres)

    if joins:
        query += " " + " ".join(joins)

    if not(constraints.empty()):
        query += constraints.sql()

    if not counting:
        if limit is not None:
            query += " LIMIT ?"
            constraints.params.append(limit)

        if offset is not None:
            query += " OFFSET ?"
            constraints.params.append(offset)

    ratings = conn.execute(query, tuple(constraints.params)).fetchall()

    if joins:
        if genres_fetched:
            grouped_data = defaultdict(list)
            for rating in ratings:
                grouped_data[(rating['user_id'], rating['manga_id'])].append(dict(rating))

            genre_map = {genre['genre_id'] : genre['genre_name'] for genre in query_genres(conn)}

            res = [{'user_id' : key[0],
                    'manga_id' : key[1],
                    'genres' : [{'genre_id' : rating['genre_id'],'genre' : genre_map[rating['genre_id']]} for rating in val],
                    'status' : val[0]['status'],
                    'read_chapters' : val[0]['read_chapters'],
                    'score' :  val[0]['score'],  'start_date_string' :  val[0]['start_date_string'],'end_date_string' :  val[0]['end_date_string']
                    }
                    for key, val in grouped_data.items()]

            if full:
                for entry in res :
                    matching_entries = grouped_data[(entry['user_id'], entry['manga_id'])]
                    entry['manga'] = {
                        'manga_id' : entry['manga_id'],
                        'title' : matching_entries[0]['title'],
                        'title_other' : matching_entries[0]['title_other'],
                        'media_type' : matching_entries[0]['media_type'],
                        'genres' : entry.pop('genres'),
                        'demographics' : matching_entries[0]['demographics'],
                        'score' : matching_entries[0]['mean_score'],
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
                        'url_img' : matching_entries[0]['url_img'],
                        'synopsis' : matching_entries[0]['synopsis']
                    }
                    entry.pop('manga_id')

        else:
           res = [dict(r) for r in ratings]
    else:
        res = [dict(r) for r in ratings]

    return ratings[0]['COUNT(*)'] if counting else res

def query_genres(conn, genre_id:int|None=None, counting:bool=False) -> list | int:
    """
        Method to query for a manga rows from the database.

        :param genre_id: id of the genre searched
        :type manga_id: int | None

        :param counting: boolean variable to indicate if the query should return the count of result or not
        :type genres: bool
    
        :return: List of the manga(s) queried or count
        :rtype: list | int
    """

    target = "COUNT(*)" if counting else "*"
    query = f"SELECT {target} FROM genres"

    constraints = Where()
    constraints.add("genre_id = ?",genre_id)

    if not(constraints.empty()):
        query += constraints.sql()

    genres = conn.execute(query, tuple(constraints.params)).fetchall()

    if genres is not None :
        return genres[0]['COUNT(*)'] if counting else [dict(r) for r in genres]
    else:
        raise GenreNotFoundException

def query_manga(conn, manga_id:int|None=None, media_type:str|None=None, status:str|None=None, min_mean:int|None=None, max_mean:int|None=None,
                #filter triggering
                genres:list | None=None, full:bool=False,
                #data manip
                limit:int|None=None, offset:int|None=None, counting:bool=False) -> None:

    """
        Method to query for a manga rows from the database.

        :param manga_id: id of the manga searched
        :type manga_id: int | None

        :param media_type: type of the media(s) queried
        :type media_type: int | None

        :param status: publishing status of the manga queried
        :type status: str | None

        :param min_mean: minimum mean thereshold applied to the query
        :type min_mean: int | None

        :param min_mean: maximum mean thereshold applied to the query
        :type min_mean: int | None

        :param genres: list of genres that the manga(s) should possess (This query imply a join between the manga and manga_genres tables)
        :type genres: list

        :param full: boolean variable to indicate if every information from every tables should be fetched.
        :type full: bool

        :param counting: boolean variable to indicate if the query should return the count of result or not
        :type genres: bool

        :param limit: numerical limit for the likely answers
        :type limit: int
    
        :return: List of the manga(s) queried or count
        :rtype: list | int
    """
    if genres is None:
        genres = []
    target = "COUNT(DISTINCT m.manga_id)" if counting else "*"
    query = f"""SELECT {target} FROM manga m """

    joins = []
    constraints = []
    genres_fetched = False

    if genres != [] or full:
        joins.append("JOIN manga_genres mg ON m.manga_id = mg.manga_id ")
        genres_fetched = True

    constraints = Where()
    constraints.add("m.status = ?", status)
    constraints.add("m.manga_id = ?", manga_id)
    constraints.add("m.media = ?", media_type)
    constraints.add("m.status = ?", status)
    constraints.add("m.mean_score >= ?", min_mean)
    constraints.add("m.mean_score <= ?", max_mean)
    constraints.add("({})".format(" OR ".join(["m.genre_id = ?" for i in range (len(genres))])), genres)

    if joins:
        query += " " + " ".join(joins)

    if not(constraints.empty()):
        query += constraints.sql()

    if not counting:
        if limit is not None:
            query += " LIMIT ?"
            constraints.params.append(limit)

        if offset is not None:
            query += " OFFSET ?"
            constraints.params.append(offset)

    mangas = conn.execute(query, tuple(constraints.params)).fetchall()

    if mangas == []:
        raise  MangaNotFoundException

    if counting:
        res = next(iter(dict(mangas[0]).values())) # There's only one var in the table in that case
        return res

    if genres_fetched:
        grouped_data = defaultdict(list)
        for manga in mangas:
            grouped_data[manga['manga_id']].append(dict(manga))

        genre_map = {genre['genre_id'] : genre['genre_name'] for genre in query_genres(conn)}

        key = list(grouped_data.keys())
        manga_vars = list(grouped_data[key[0]][0].keys()) # Collect the list of variables for the first manga found (among those that have been found)
        manga_vars.remove('genre_id')
        res = []
        for manga_list in grouped_data.values():
            unified_manga_entry = {var : manga_list[0][var] for var in manga_vars}
            unified_manga_entry['genres'] = [{"genre_id" : manga["genre_id"], "genre_name" : genre_map[manga["genre_id"]]} for manga in manga_list]
            mangas.append(unified_manga_entry)
        return res

    return [dict(manga) for manga in mangas]

def search_manga(conn, string:str, limit:int=15):
    """
    Method to query for a manga title. The search query is currently really naïve.
    
    The search manga currently uses a naïve search (assuming that the string isn't complete and in the middle of the string searched.)

    :param string: string of characters inputed to search for a manga
    :type string: str

    :param limit: numerical limit for the likely answers
    :type limit: int

    :return: List of the n most likely answers (n=limit)
    :rtype: list
    """
    escaped = string.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    params = (f"%{escaped}%", limit)
    req = "SELECT manga_id, title FROM manga WHERE title LIKE ? ESCAPE '\\' LIMIT ?"
    for title_type in ["title", "title_english", "title_other"]:
        req = f"SELECT manga_id, title FROM manga WHERE {title_type} LIKE ? ESCAPE '\\' LIMIT ?"
        output = conn.execute(req, params).fetchall()

        if output != []:
            return [{'title' : manga[1], 'manga_id' : manga[0]} for manga in output]
    return []

def search_user(conn, string:str, limit:int=15):
    """
    Method to query for a manga title. The search query is currently really naïve.
    
    The search manga currently uses a naïve search (assuming that the string isn't complete and in the middle of the string searched.)

    :param string: string of characters inputed to search for a manga
    :type string: str

    :param limit: numerical limit for the likely answers
    :type limit: int

    :return: List of the n most likely answers (n=limit)
    :rtype: list
    """
    escaped = string.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    params = (f"%{escaped}%", limit)
    req = "SELECT username FROM users WHERE username LIKE ? ESCAPE '\\' LIMIT ?"

    rows = conn.execute(req, params).fetchall()

    return [row[0] for row in rows]

if __name__ == "__main__":
    conn = sqlite3.connect("file:{}?mode=ro".format(param["DB_PATH"]), uri=True)
    conn.row_factory = sqlite3.Row
    print(query_manga(conn, counting=True))
    conn.close()
