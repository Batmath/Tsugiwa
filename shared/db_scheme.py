import pathlib
import random
import sqlite3
from contextlib import closing

import pandas as pd


def init_db(path):
    conn = sqlite3.connect(path)
    with closing(conn):
        cursor = conn.cursor()
        # entries in users create inconsistencies, it shouldn't be added at runtime
        cursor.execute("PRAGMA foreign_keys = ON")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                gender TEXT,
                birthday INTEGER,
                location TEXT,
                entries INTEGER,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(username)
            );""")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries(
                user_id INTEGER REFERENCES users(user_id),
                manga_id INTEGER,
                status TEXT,
                read_chapters INTEGER,
                score INTEGER,
                start_date_string TEXT,
                end_date_string TEXT,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, manga_id)
            );""")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships(
                user_id_left INTEGER REFERENCES users(user_id),
                user_id_right INTEGER REFERENCES users(user_id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT chk_numerical_order CHECK (user_id_left < user_id_right),
                PRIMARY KEY (user_id_left, user_id_right)
            );
        """)

        cursor.execute("""CREATE TABLE IF NOT EXISTS pending_recovery(username TEXT PRIMARY KEY);""")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manga(
                manga_id INTEGER PRIMARY KEY,
                title TEXT,
                title_english TEXT,
                title_other TEXT,
                media_type TEXT,
                demographics TEXT,
                mean_score REAL,
                scored_by INTEGER,
                rank INTEGER,
                popularity_rank INTEGER,
                members INTEGER,
                favorites INTEGER,
                status TEXT,
                publishing BOOLEAN,
                published_from TEXT,
                published_to TEXT,
                chapters INTEGER,
                volumes INTEGER,
                url_img TEXT,
                synopsis TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS genres(
                genre_id INTEGER PRIMARY KEY,
                genre_name TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manga_genres(
                manga_id INTEGER REFERENCES manga(manga_id),
                genre_id INTEGER REFERENCES genres(genre_id),

                PRIMARY KEY (manga_id, genre_id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS author(
                author_id INTEGER PRIMARY KEY,
                author_name TEXT,

                UNIQUE(author_name)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manga_author(
                author_id INTEGER REFERENCES author(author_id),
                manga_id INTEGER REFERENCES manga(manga_id),

                PRIMARY KEY (author_id, manga_id)
            );
        """)
        cursor.execute("""CREATE INDEX IF NOT EXISTS usern_id_entries ON entries (user_id);""")
        cursor.execute("""CREATE INDEX IF NOT EXISTS manga_id_entries ON entries (manga_id);""")
        cursor.execute("""CREATE INDEX IF NOT EXISTS manga_id_genre ON manga_genres (manga_id);""")
        cursor.execute("""CREATE INDEX IF NOT EXISTS genre_id_manga ON manga_genres (genre_id);""")
        # TODO : add INDEXES ON PROD DB
        cursor.execute("""CREATE INDEX IF NOT EXISTS username ON users (username);""")
        cursor.execute("""CREATE INDEX IF NOT EXISTS title_manga ON manga (title);""")
        conn.commit()

def populate_manga_tables(csv_path, db_path) -> None:
    init_db(db_path)
    manga = pd.read_csv(csv_path, index_col=0)
    genres = pd.read_csv("./genres.csv", index_col=0)

    manga_genres = manga[['genres','themes']]
    conn = sqlite3.connect(db_path)
    manga_genres['authors'] = manga['authors']
    manga_sql = manga
    manga_sql.rename(columns={'title_japanese' : 'title_other'}, inplace=True)
    with closing(conn):
        cursor = conn.cursor()
        genres.to_sql('genres', conn, if_exists="delete_rows")
        manga_sql.drop(columns=["authors", "genres", "themes"], inplace=True)
        print(manga_sql.columns)
        manga_sql.drop_duplicates(inplace=True)
        manga_sql.to_sql("manga", conn, if_exists="delete_rows")

        for id, row in manga_genres.iterrows():

            #Author Extraction
            authors_str = list(row)[2]
            if type(authors_str) != str:
                continue
            authors = list(authors_str.split(','))
            full_authors = []
            n = len(authors)
            for i in range(n):
                print(i)
                print(authors[i][0])
                if authors[i][0] == " ":
                    if i !=0:
                        full_authors.append(authors[i-1] + authors[i])
                    else:
                        full_authors.append(authors[i])
                elif i != 0 and authors[i-1][0] != " ":
                    full_authors.append(authors[i-1])
                elif i == n-1 :
                    full_authors.append(authors[i])

            for author in full_authors:
                cursor.execute("""INSERT OR IGNORE INTO author (author_name) VALUES (?)""", (author,))
                author_id = cursor.execute("""SELECT author_id FROM author WHERE author_name = ?""", (author,)).fetchone()[0]
                cursor.execute("""INSERT OR IGNORE INTO manga_author VALUES (?, ?)""", (author_id, id))

            #Genre Extraction
            row = list(row)
            if type(row[0]) != str and type(row[1]) != str:
                continue
            elif type(row[0]) != str:
                m_genres = row[1].split(',')
            elif type(row[1]) != str:
                m_genres = row[0].split(',')
            else :
                m_genres = (row[0] + ',' + row[1]).split(',')

            for genre in m_genres:
                genre_id = genres[genres['genre_name'] == genre].index.values[0]

                print((id, int(genre_id)))
                cursor.execute("""INSERT OR REPLACE INTO manga_genres VALUES (?,?)""", (id, int(genre_id)))
            conn.commit()

def transfer_db(ref_db_path, new_db_path, exclude=None) -> None:
    if exclude is None:
        exclude = []

    init_db(new_db_path)
    conn_ref = sqlite3.connect(ref_db_path)
    conn_new = sqlite3.connect(new_db_path)
    with closing(conn_ref):
        cursor = conn_ref.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [x[0] for x in cursor.fetchall()]
        for tab in exclude:
            tables.remove(tab)
        with closing(conn_new):
            for tab in tables:
                pd.read_sql(f"SELECT * FROM {tab}", conn_ref).to_sql(tab, conn_new, if_exists="delete_rows", index=False)

def generate_anonymized_data(db_path, new_db_path, n, seed=42) -> None:
    random.seed(seed)
    conn = sqlite3.connect(db_path)
    with closing(conn):
        cursor = conn.cursor()
        cursor.execute(""" SELECT * FROM users""")
        users = cursor.fetchall()
        sample = random.sample(users, n)
        userids = [row[0] for row in sample]
        entries = []
        for i in range(len(userids)):
            user_i = list(sample[i])
            print(sample[i])
            user_entries = cursor.execute("""SELECT * FROM entries WHERE user_id = ?""", (userids[i],)).fetchall()
            entries += user_entries
            user_i[1] = f"User{i}"
            user_i[2] = random.choice(["Male", "Female"])
            user_i[3] = random.randint(1970, 2018)
            user_i[4] = None
            sample[i] = tuple(user_i)

    transfer_db(db_path, new_db_path, exclude=["users", "entries", "relationships", "pending_recovery"])
    conn2 = sqlite3.connect(new_db_path)

    with closing(conn2):
        cursor = conn2.cursor()
        cursor.executemany("""INSERT OR IGNORE INTO users VALUES (?{})""".format(", ? " * (len(users[0]) - 1)), sample)
        cursor.executemany("""INSERT OR IGNORE INTO entries VALUES (?{})""".format(", ? " * (len(entries[0]) - 1)), entries)
        conn2.commit()

def dump_db_to_sql(db_path, output_path) -> None:
    conn = sqlite3.connect(db_path)
    with closing(conn), open(output_path, "w") as f:
            f.writelines(f"{line}\n" for line in conn.iterdump())


def build_db_from_dump(dump_path: pathlib.Path, target_path: pathlib.Path) -> None:
    conn = sqlite3.connect(target_path)
    with closing(conn):
        with open(dump_path) as f:
            conn.executescript(f.read())
        conn.commit()

if __name__ == "__main__":
    build_db_from_dump(pathlib.Path("./data/dump.sql"), pathlib.Path("./data/db_rebuilt.db"))
