import json
import time
import requests
import pandas as pd
import re
import threading
import queue
import cProfile, pstats
import sqlite3
from bs4 import BeautifulSoup
import os
from contextlib import closing
import logging
logger = logging.getLogger(__name__)


class PrivateListException(Exception):
    pass

class HTMLParsingException(Exception):
    pass

class ScarceDataException(Exception):
    pass

# TODO : add comments
# TODO : Create a docker image to run the code on the server
# TODO : Setup an API
# TODO : Setup tests (API)
# TODO : Add logging instead of simple prints
# TODO: More global variables/parameters that can be controlled (sleep_times, min and max dynamic sleep, directories...)


MANGA_STATUS_CODE = {0: "Unknown", 1 : "Reading", 2 : "Completed", 3 : "On-Hold", 4 : "Dropped", 6 : "Plan to Read"}
MANGA_DISPLAY_LIMIT = 300 # limit of manga per page is 300 (when calling "https://myanimelist.net/mangalist/username/load.json")
session = requests.Session()
headers={
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

def fetch_user_page(session, sleep_time=0.5):

    def is_user_href(tag):
        return tag.has_attr('href') and not tag.find('img') and re.compile("/profile").search(tag['href'])
    
    time.sleep(sleep_time)
    target_page = "https://myanimelist.net/users.php"

    req = session.get(target_page)
    if req.status_code == 200 :
        soup = BeautifulSoup(req.text, "html.parser")
        users = list(map(lambda x : x.text, soup.find_all(is_user_href)))
        return users
    else : 
        req.raise_for_status()

def find_friends(name:str, session, sleep_time=0.5):
    def is_friend_name(tag):
        return tag.has_attr('href') and tag.parent.has_attr('class') and "title" in tag.parent['class'] and re.compile("https://myanimelist.net/profile/").search(tag['href'])

    time.sleep(sleep_time)
    target_page = "https://myanimelist.net/profile/{}/friends".format(name)
    req = session.get(target_page)
    
    if req.status_code == 200:
        soup = BeautifulSoup(req.text, "html.parser")
        friends_name = list(map(lambda x : x.text, soup.find_all(is_friend_name)))
        return friends_name
    else:
        req.raise_for_status()
    
def fetch_manga_profile(name:str, session, min_entry=1, sleep_time=0.5):

    time.sleep(sleep_time)
    target_page = "https://myanimelist.net/profile/{}".format(name)
    req = session.get(target_page)
    
    if req.status_code == 200:
        soup = BeautifulSoup(req.text, "html.parser")
        #print(soup.find_all("p", string=re.compile("Access to this list has been restricted by the owner.")))
        # On the Statistics layout, there are two Total Entries, Anime and Manga

        #Other approach : search for the Blocks then fetch informations
        #
        profile_info = soup.find("ul", class_="user-status")
        manga_status = soup.find("div", class_="updates manga")
        manga_stats = soup.find("div", class_="stats manga")
        friends_info = soup.find("div", class_="user-friends")

        if not(profile_info or manga_stats or manga_status or friends_info):
            raise HTMLParsingException("Error while parsing the HTML file, one of the target class wasn't found")
        
        #Checking if the list is private
        is_private = manga_status.find(string=re.compile("Access to this list has been restricted by the owner.")) is not None
        if is_private:
            raise PrivateListException("[fetch_manga_profile] : The User's Manga List is marked as private, unable to fetch manga data")
        
        # Check number of entries and to avoid scarce data & prepare offsets
        n_entry = -1
        entry_text = manga_stats.find(string=re.compile("Total Entries"))
        if entry_text :
            n_entry = int(entry_text.parent.next_sibling.text.replace(",", ""))

        if n_entry < min_entry:
            raise ScarceDataException("[fetch_manga_profile] : The user has less registered manga entries than the minimal amount targeted (n={})".format(min_entry))

        #informations to fetch : gender, birthday, location
        # These informations inside the user-status element are presented as two span element siblings (One has the type of category and the other, the value)
        gender = None
        has_gender = profile_info.find(string=re.compile("Gender"))
        if has_gender:
            gender = has_gender.parent.next_sibling.text
        
        birthday = None
        has_birthday = profile_info.find(string=re.compile("Birthday"))
        if has_birthday:
            match = re.search("[0-9]{4}", has_birthday.parent.next_sibling.text)
            birthday = int(match.group()) if match else None
        
        location = None
        has_location = profile_info.find(string=re.compile("Location"))
        if has_location:
            location = has_location.parent.next_sibling.text

        friends = None
        has_no_friends = friends_info.find(string=re.compile("No friend yet."))
        if has_no_friends is None:
            friends = find_friends(name, session)
        
        return {"username" : name, "gender" : gender, "birthday" : birthday, "location" : location, "entries" : n_entry, "friends" : friends}
    else:
        req.raise_for_status()

def create_manga_interraction_entries(data, username, cursor):
    # json is structured as such : [{entry 0}... {entry 299}]
    # raise error if nothing
    if not data: # Empty => Bad offset or other issue ?
        return

    for manga in data:
        if not(manga['status'] >= 0 and manga['status'] <7):
            continue # Not even unknown
        cursor.execute("""INSERT OR IGNORE INTO entries (username, manga_id, status, read_chapters, score, start_date_string, end_date_string) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)""", (username, manga['manga_id'], MANGA_STATUS_CODE[manga['status']], manga['num_read_chapters'], manga['score'] if manga['score'] != 0 else None, manga['start_date_string'], manga['finish_date_string']))


def fetch_manga_list(name:str, n_entry:int, cursor, session, sleep_time=0.5):
    data_list = [] # Instead of iterating over entries that were previously created or adding to the database while there may be other pages not fetched (which could return an error and fetch partial data), do the requests first, then operate on received object if it went well.
    if n_entry < 1:
        raise ScarceDataException("[fetch_manga_list] : Attempted to fetch a manga_list with no entry")

    session.scraped_entries_count = 0
    n_offsets = n_entry//MANGA_DISPLAY_LIMIT
    for i in range(0, n_offsets+1):
        time.sleep(sleep_time)
        target_page = "https://myanimelist.net/mangalist/{}/load.json".format(name)
        req = session.get(target_page, params={"offset": i*MANGA_DISPLAY_LIMIT})
        if req.status_code == 200:
            data_list.append(req.json())
        else:
            req.raise_for_status()
    for data in data_list:
        session.scraped_entries_count += len(data)
        create_manga_interraction_entries(data, name, cursor)

def init_db(conn, cursor):
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
    conn.commit()

def create_user_review_database(max_users = 10, min_entry=1,DB_PATH = "data/data.db"):

    # Add os.search for variables regarding directories (names)...
    def load_from_previous_session():
        cursor.execute("""SELECT username FROM users""")
        users = cursor.fetchall()
        usernames = [user[0] for user in users]
        n_user_previous_session = len(usernames)
        return usernames, n_user_previous_session
    
    def load_pending():
        try:
            cursor.execute("""SELECT username FROM pending_recovery""")
            users = cursor.fetchall()
            usernames = [user[0] for user in users]
            for u in usernames:
                name_queue.put(u)
                seen.add(u)
            cursor.execute("""DELETE FROM pending_recovery""")
            conn.commit()
        except Exception as e:
            raise
        return

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    init_db(conn, cursor)

    previous_users, n_loaded = load_from_previous_session()
    logging.info("Currently loaded : {}".format(n_loaded))

    seen = set(previous_users)
    added = set(previous_users)
    max_users = max_users 
    name_queue = queue.Queue()
    
    load_pending()

    lock = threading.Lock()
    link_user_data_stop = threading.Event()

    CONNECTION_ISSUES_SLEEP = 60
    RATE_LIMIT_SLEEP = 180

    min_sleep=5
    global user_page_sleep
    user_page_sleep=min_sleep
    max_sleep=12000
    SENTINEL = object()
    user_per_page = 20 #myanimelist.net/users.php always gives 20 names

    session = requests.Session()
    session.headers.update(headers)

    def compute_dynamic_sleep(q_size:int, n_added, exp_factor=9, max_users=max_users, min_sleep=min_sleep, max_sleep=max_sleep):
        remaining_user_needed = max_users - n_added
        if remaining_user_needed <=0:
            return max_sleep

        ratio = min(q_size/remaining_user_needed,1) 

        sleep_time = min_sleep + (ratio**exp_factor * (max_sleep - min_sleep))

        return round(sleep_time, 1)

    def dump_pending():
        pending_users = []
        while not name_queue.empty():
            try:
                user = name_queue.get_nowait()
                if user is not SENTINEL:
                    pending_users.append((user,))
                name_queue.task_done()

            except queue.Empty:
                break
        try:
            cursor.executemany("INSERT OR IGNORE INTO pending_recovery (username) VALUES (?);", pending_users)
            conn.commit()
        except Exception as e:
            logging.error("dump_pending : error while converting pending names : {}".format(e))
            conn.rollback()
            raise
        return

    def create_users():
        while not link_user_data_stop.is_set():
            if len(added) >= max_users + n_loaded:
                break
            try:
                with lock:
                    current_sleep = user_page_sleep
                logging.debug("[THREAD A] : Current sleep time : {}".format(current_sleep))
                names = fetch_user_page(session, sleep_time=current_sleep)
                added_loop = []
                for name in names:
                    
                    if link_user_data_stop.is_set(): #thread B crashes while we are putting names on the queue
                        break

                    if len(added) >= max_users + n_loaded: #max_users is reached while we are adding new names
                        break

                    with lock:
                        if name not in seen:
                            seen.add(name)
                            name_queue.put(name)
                            added_loop.append(name)
                
                logging.info("[THREAD A] : {} Users added during loop : {}".format(len(added_loop), added_loop))

            except requests.exceptions.ConnectionError:
                logging.error("[THREAD A] : Connection Error : Waiting for Connection...")
                time.sleep(CONNECTION_ISSUES_SLEEP)

            except requests.exceptions.Timeout:
                logging.error("[THREAD A] : Timeout Error : Waiting before trying again...")
                time.sleep(CONNECTION_ISSUES_SLEEP)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 :
                    logging.error("[THREAD A] : Too Many Requests : Waiting before trying again...")
                    time.sleep(RATE_LIMIT_SLEEP)
                elif e.response.status_code == 403 :
                    # According to (https://myanimelist.net/forum/?topicid=1991772) 403 is the rate limit response received
                    logging.error("[THREAD A] : Too Many Requests : Waiting before trying again...")
                    time.sleep(RATE_LIMIT_SLEEP)
                else:
                    logging.error("[THREAD A] : Unhandled HTTP error ({}) : Stopping Thread A".format(e.response.status_code))
                    break

            except Exception as ue:
                name_queue.put(SENTINEL)
                break

        name_queue.put(SENTINEL)
    
    def link_user_data():
        global user_page_sleep

        with closing(conn):
            while True:
                name = name_queue.get()
                task_done = False
                logging.debug("Current user : {}".format(name))

                with lock:
                    q_size = name_queue.qsize()
                    n_added = len(added)
                    logging.debug("[THREAD B] : Added total {}".format(n_added))
                    user_page_sleep = compute_dynamic_sleep(q_size, n_added - n_loaded)
                    logging.debug("[THREAD B] : Current user page fetch time sleep : {}\n \t Number of currently fetched users : {}\n \t Number of currently added users {}\n \t(Previously loaded : {})".format(user_page_sleep, q_size, n_added - n_loaded, n_loaded))

                if name is SENTINEL or len(added) > max_users + n_loaded:
                    name_queue.task_done()
                    dump_pending()
                    break

                try:
                    success = False
                    while not success:
                        try:
                            user_info = fetch_manga_profile(name, session, min_entry=min_entry, sleep_time=1)
                            friends = user_info.pop("friends") #user_info doesn't have friends anymore

                            cursor.execute("""INSERT INTO users (username, gender, birthday, location, entries)
                                                VALUES (?, ?, ?, ?, ?)""", (user_info["username"], user_info["gender"], user_info["birthday"], user_info["location"], user_info["entries"]))
                            fetch_manga_list(name, user_info["entries"], cursor,session, sleep_time=1) # we fecth after trying to insert the user, if it's already in the db (from previous runs), fails and no need to fetch ! (saving requests)

                            if friends is not None:
                                for friend in friends:
                                    with lock:
                                        if friend in added: #name not in added because INSERT INTO users didn't fail.
                                            left_user = min(name, friend)
                                            right_user = max(name, friend)
                                            logging.debug("Friend in db detected, relationship is being created : ({}, {})".format(left_user, right_user))
                                            cursor.execute("""INSERT INTO relationships (user_left, user_right) values (?, ?)""", (left_user, right_user)) #Add every relationship between user and friends that have already been added
                                        elif friend not in seen and name_queue.qsize():
                                            seen.add(friend)
                                            name_queue.put(friend)
                            with lock:
                                added.add(name)
                            
                            conn.commit()
                            success = True
                        
                        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                            logging.error("[THREAD B] : Connection Error : {} | Waiting for Connection...".format(e))
                            conn.rollback()
                            time.sleep(CONNECTION_ISSUES_SLEEP)

                        except requests.exceptions.HTTPError as e:
                            if (e.response.status_code == 429 or e.response.status_code == 403):
                                logging.error("[THREAD B] : Too Many Requests : Waiting before trying again...")
                                conn.rollback()
                                time.sleep(RATE_LIMIT_SLEEP)
                            elif (e.response.status_code == 404):
                                logging.error("[THREAD B] : User {} not found. Skipping ...".format(name))
                                conn.rollback()
                                break
                            else:
                                logging.error("[THREAD B] : Error : {}".format(e))
                                link_user_data_stop.set()
                                user_page_sleep = max_sleep # we don't know if thread A crashed, put maximum timer and dump.
                                name_queue.task_done()
                                task_done=True
                                conn.rollback()
                                dump_pending(name_queue)
                                break

                except (HTMLParsingException, ScarceDataException, PrivateListException) as e:
                    logging.error("[THREAD B] : Skiping user {}, cause : {}".format(name, e))
                    conn.rollback()
                
                except sqlite3.IntegrityError as e:
                    logging.error("[THREAD B] : User {} is already in the database, skipping user : {}".format(name,e))
                    conn.rollback()
                
                except sqlite3.Error as e:
                    logging.error("[THREAD B] : Database error while saving {}: {} \nCurrently no clue what to do here, user will be skipped".format(name,e))
                    conn.rollback()
                
                except Exception as ue:
                    logging.error("[THREAD B] : Unknwon exception ; Abort scraping : {}".format(ue))
                    conn.rollback()
                    user_page_sleep = max_sleep # we don't know if thread A crashed, put maximum timer and dump.
                    name_queue.task_done()
                    task_done=True
                    conn.rollback()
                    link_user_data_stop.set()
                    dump_pending()
                    break

                finally:
                    if not task_done: # If an error requiring to dump names from the queue has been caught, ignore the task_done order (was done before)
                        name_queue.task_done()
            
            link_user_data_stop.set()

    user_name_thread = threading.Thread(target=create_users)
    rating_thread = threading.Thread(target=link_user_data)

    user_name_thread.start()
    time.sleep(0.5)
    rating_thread.start()

    user_name_thread.join()
    rating_thread.join()

def main(log_path="./log"):
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    DB_PATH = os.environ.get("DB_PATH", "data/data.db")
    logging.basicConfig(filename=log_path+"/scraper.log", level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    create_user_review_database(max_users=920, min_entry=1, DB_PATH=DB_PATH)

if __name__ == "__main__":
    main()
    #cProfile.run("create_user_review_database(max_users=10, DB_PATH={})".format(DB_PATH), "./data/scrapper_perfs.prof")
    #p = pstats.Stats("scrapper_perfs.prof")
    #p.sort_stats("cumulative")
    #p.print_stats(100)