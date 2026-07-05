import sqlite3
from contextlib import closing

def init_db(path):
    conn = sqlite3.connect(path)
    with closing(conn):
        cursor = conn.cursor()
        # entries in users create inconsistencies, it shouldn't be added at runtime
        cursor.execute("PRAGMA foreign_keys = ON")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                username TEXT PRIMARY KEY,
                gender TEXT,
                birthday INTEGER,
                location TEXT,
                entries INTEGER,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );""")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries(
                username TEXT REFERENCES users(username),
                manga_id INTEGER,
                status TEXT,
                read_chapters INTEGER,
                score INTEGER,
                start_date_string TEXT,
                end_date_string TEXT,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (username, manga_id)
            );""")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships(
                user_left TEXT REFERENCES users(username),
                user_right TEXT REFERENCES users(username),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT chk_alphabetical_order CHECK (user_left < user_right),
                PRIMARY KEY (user_left, user_right)
            );
        """)

        cursor.execute("""CREATE TABLE IF NOT EXISTS pending_recovery(username TEXT PRIMARY KEY);""")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manga(
                manga_id INTEGER PRIMARY KEY,
                title TEXT,
                title_english TEXT,
                title_japanese TEXT,
                media_type TEXT,
                demographics TEXT,
                mean_score REAL,
                scored_by INTEGER,
                rank INTEGER,
                popularity_rank INTEGER,
                popularity INTEGER,
                favorites INTEGER,
                status TEXT,
                publishing BOOLEAN,
                published_from TEXT,
                published_to TEXT,
                chapters INTEGER,
                volumes INTEGER,
                authors TEXT,
                url_img TEXT,
                synopsis TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS genres(
                genre_id INT PRIMARY KEY,
                genre_name TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manga_genres(
                manga_id INT REFERENCES manga(manga_id),
                genre_id INT REFERENCES genres(genre_id),

                PRIMARY KEY (manga_id, genre_id)
            );
        """)

        cursor.execute("""CREATE INDEX IF NOT EXISTS username_entries ON entries (username);""")
        cursor.execute("""CREATE INDEX IF NOT EXISTS manga_id_entries ON entries (manga_id);""")
        cursor.execute("""CREATE INDEX IF NOT EXISTS manga_id_genre ON manga_genres (manga_id);""")
        cursor.execute("""CREATE INDEX IF NOT EXISTS genre_id_manga ON manga_genres (genre_id);""")
        
        conn.commit()