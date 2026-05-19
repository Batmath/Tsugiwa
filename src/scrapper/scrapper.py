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

class PrivateListException(Exception):
    pass

class HTMLParsingException(Exception):
    pass

class ScarceDataException(Exception):
    pass

# TODO : add comments
# TODO : Will they finish the manga ? What location ? What age ? What gender ?
# TODO : Create a docker image to run the code on the server
# TODO : Setup an API


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
        #re.compile("Access to this list has been restricted by the owner.").search(tag.find_next_sibling("p"))
        #re.compile("Last Manga Updates").search(tag.text) and re.compile("Access to this list has been restricted by the owner.").search(tag.find_next_sibling("p"))
        #Could also add friends ! 
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
    for manga in data:
        if not(manga['status'] >= 0 and manga['status'] <7):
            continue # Not even unknown
        cursor.execute("""INSERT OR IGNORE INTO ratings (username, manga_id, status, read_chapters, score, start_date_string, end_date_string) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)""", (username, manga['manga_id'], MANGA_STATUS_CODE[manga['status']], manga['num_read_chapters'], manga['score'] if manga['score'] != 0 else None, manga['start_date_string'], manga['finish_date_string']))

def fetch_manga_list(name:str, n_entry:int, cursor, session, sleep_time=0.5):
    data_list = [] # Instead of iterating over entries that were previously created or adding to the database while there may be other pages not fetched (which could return an error and fetch partial data), do the requests first, then operate on received object if it went well.
    if n_entry < 1:
        raise ScarceDataException("[fetch_manga_list] : Attempted to fetch a manga_list with no entry")

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
        create_manga_interraction_entries(data, name, cursor)
    print("Manga list from {} has been fetched successfully!".format(name)) 
    print("Waiting for cursor validation")

def init_db(cursor):
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
        CREATE TABLE IF NOT EXISTS ratings(
            username TEXT REFERENCES users(username),
            manga_id INTEGER,
            status TEXT,
            read_chapters INTEGER,
            score INTEGER,
            start_date_string TEXT,
            end_date_string TEXT,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );""")


def create_user_review_database(max_users = 10):
    seen = set()
    added = set()
    name_queue = queue.Queue()
    all_rating_entries = []
    all_user_entries = []
    lock = threading.Lock()
    CONNECTION_ISSUES_SLEEP = 60
    RATE_LIMIT_SLEEP = 180
    min_sleep=1
    user_page_sleep=min_sleep
    max_sleep=10
    SENTINEL = None
    user_per_page = 20 #myanimelist.net/users.php always gives 20 names

    session = requests.Session()
    session.headers.update(headers)

    #If first instance, create database, then close to avoid thread issues.
    conn = sqlite3.connect("./raw_scraped_data.db", check_same_thread=False)
    cursor = conn.cursor()

    # System WILL break with the current implementation of pending (je relance -> ajoute les pendings, on sait qu'ils ne sont pas vu, mais les pendings peuvent être des friends (qui seront récupérer quand on prends les amis)
    # rien pour friend, mais pour user (et potentiellement d'autres amis de user) passe pas dans user mais passe dans ratings (duplicats de ratings))
    # Also fails if mysterious black magic is used (user from seen passed, blocked by user but ratings will be copied).
    # Change ON CONFLICT algorithm choice -> FAIL -> catch exception and abort adding the user whatsoever.

    # IDEA to control the flow of users : Loosing users per second, not really important (may have been seen, if active, may be fetched...)
    # Control the rate at which users are fetched (-> create_user_sleep_time is dynamically updated by link_user_data) + buffer (buffer with a limit size equal to 10% of the target_users, min 50) + actual queue (twice as )

    #buffer -> useless (only storing usernames, overall size of the proccess : 3*seen, (assuming late in the code that seen > added), for 100k, seen may be 300k * 61 bytes ~ 17.45 mb)
    #add offset time to the start of link_user and noise fetches to avoid sending requests at constant time 

    def compute_dynamic_sleep(q_size:int, n_added, exp_factor=2, max_users=max_users, min_sleep=min_sleep, max_sleep=max_sleep):
        remaining_user_needed = max_users - n_added
        if remaining_user_needed <=0:
            return max_sleep

        ratio = q_size/remaining_user_needed
        ratio = min(remaining_user_needed,1) 

        sleep_time = min_sleep + (ratio**exp_factor * (max_sleep - min_sleep))
        return round(sleep_time, 1)

    def create_databases(entries_rating, entries_user, rating_path="./data/raw_rating.csv", user_path="./data/raw_user.csv"):
        user_df = pd.DataFrame(entries_user)
        rating_df = pd.DataFrame(entries_rating)

        user_df.to_csv(user_path,index=True, encoding='utf-8')
        rating_df.to_csv(rating_path, index=False, encoding='utf-8')

    def create_users():
        while True:
            with lock:
                if len(added) >= max_users:
                    break
            try:
                names = fetch_user_page(session, sleep_time=user_page_sleep)
                for name in names:
                    with lock:
                        if name not in seen:
                                seen.add(name)
                                name_queue.put(name)

            except requests.exceptions.ConnectionError:
                print("Connection Error : Waiting for Connection...")
                time.sleep(CONNECTION_ISSUES_SLEEP)
            except requests.exceptions.Timeout:
                print("Timeout Error : Waiting before trying again...")
                time.sleep(CONNECTION_ISSUES_SLEEP)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 :
                    print("Too Many Requests : Waiting before trying again...")
                    time.sleep(RATE_LIMIT_SLEEP)
                if e.response.status_code == 403 :
                    # According to (https://myanimelist.net/forum/?topicid=1991772) 403 is the rate limit response received
                    print("Too Many Requests : Waiting before trying again...")
                    time.sleep(RATE_LIMIT_SLEEP)
                else:
                    raise
        name_queue.put(SENTINEL)
    
    def link_user_data():
        init_db(cursor)
        while True:
            with lock:
                q_size = name_queue.qsize()
            n_added = len(added)
            user_page_sleep = compute_dynamic_sleep(q_size, n_added)
            print("Current sleep time : {}".format(user_page_sleep))
            name = name_queue.get()

            if name is SENTINEL:
                create_databases(all_rating_entries, all_user_entries)
                name_queue.task_done()
                break
            try:
                success = False
                while not success:
                    try:
                        user_info = fetch_manga_profile(name, session, sleep_time=0.5)
                        friends = user_info.pop("friends") #user_info doesn't have friends anymore
                        all_user_entries.append(user_info)
                        # Need lock on seen and name_queue ?
                        if friends is not None:
                            print("friend of {} : {}".format(name, friends))
                            for friend in friends:
                                with lock:
                                    if friend not in seen and name_queue.qsize() < max_users * 2:
                                        seen.add(friend)
                                        name_queue.put(friend)
                        # https://hoelz.ro/blog/with-sqlite-insert-or-ignore-is-often-not-what-you-want
                        cursor.execute("""INSERT INTO users (username, gender, birthday, location, entries)
                                            VALUES (?, ?, ?, ?, ?)""", (user_info["username"], user_info["gender"], user_info["birthday"], user_info["location"], user_info['entries']))
                        fetch_manga_list(name, user_info["entries"], cursor,session) # we fecth after trying to insert the user, if it's already in the db (from previous runs), fails and no need to fetch ! (saving requests)
                        conn.commit()

                        with lock:
                            added.add(name)
                            q_size = name_queue.qsize()
                        n_added = len(added)
                        
                        user_page_sleep = compute_dynamic_sleep(q_size, n_added)
                        success = True
                        print("Current user page fetch time sleep : {}\n Number of currently fetched users : {}\n Number of currently added users".format(user_page_sleep, q_size, n_added))
                    except requests.exceptions.ConnectionError:
                        print("Connection Error : Waiting for Connection...")
                        time.sleep(CONNECTION_ISSUES_SLEEP)
                    except requests.exceptions.Timeout:
                        print("Timeout Error : Waiting before trying again...")
                        time.sleep(CONNECTION_ISSUES_SLEEP)
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 429 :
                            print("Too Many Requests : Waiting before trying again...")
                            time.sleep(RATE_LIMIT_SLEEP)
                        if e.response.status_code == 403 :
                            # According to (https://myanimelist.net/forum/?topicid=1991772) 403 is the rate limit response received
                            print("Too Many Requests : Waiting before trying again...")
                            time.sleep(RATE_LIMIT_SLEEP)
                        else:
                            raise
            except (HTMLParsingException, ScarceDataException, PrivateListException) as e:
                print("Skiping user {}, cause : {}".format(name, e))
            except sqlite3.IntegrityError as e:
                print("User {} is already in the database, skipping user".format(name))
                conn.rollback()
            except sqlite3.Error as e:
                print("Database error while saving {}: {} \nCurrently no clue what to do here, user will be skipped".format(name,e))
                conn.rollback()
                raise
            finally:
                name_queue.task_done()
        conn.close()

    user_name_thread = threading.Thread(target=create_users)
    rating_thread = threading.Thread(target=link_user_data)

    user_name_thread.start()
    time.sleep(0.5)
    rating_thread.start()

    user_name_thread.join()
    rating_thread.join()

if __name__ == "__main__":
    cProfile.run("create_user_review_database(max_users=10)", "./data/scrapper_perfs.prof")
    #p = pstats.Stats("scrapper_perfs.prof")
    #p.sort_stats("cumulative")
    #p.print_stats(100)
