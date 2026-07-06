import json
import time
import requests, time, json
import pandas as pd
import re #regex
import threading, queue
import cProfile, pstats
import sqlite3
from bs4 import BeautifulSoup
import os
from contextlib import closing
import logging
import settings
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
# TODO : Class with different datas (Paths etc. and pydantic verification)
# TODO : Commenter le code

class Scraper():
    
    def __init__(self, params : settings.ParametersScraper = settings.ParametersScraper()):
        """Constructor method
        """

        self.params = params.model_dump()
        self.conn = sqlite3.connect(self.params["DB_PATH"], check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.user_page_sleep = self.params["MIN_SLEEP"]
        self.MANGA_STATUS_CODE = {0: "Unknown", 1 : "Reading", 2 : "Completed", 3 : "On-Hold", 4 : "Dropped", 6 : "Plan to Read"} # Code on MAL for different entries statuses (Last checked : 27/06/26)
        self.MANGA_DISPLAY_LIMIT = 300 # limit of manga per page is 300 (when calling "https://myanimelist.net/mangalist/username/load.json")
        self.session = requests.Session()
        self.seen = set()
        self.added = set()
        self.SENTINEL = object()
        self.headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        self.session.headers.update(self.headers) # Update the current session with headers given
        self.name_queue = queue.Queue() 
        


    def fetch_html(self, url, params=None):
        """
        Method that fetches the text content from a url page.
        :param url: Target url from which the text is fetched
        :type url: str
        
        :param params: parameters associated to the url (field key=val, limit..)
        :type params: dict

        :raises RequestException: Request Errors for Status codes 4xx and 2xx

        :return: Body of the response in string fromat (raw)
        :rtype: str
        """
        try :
            response = requests.get(url,timeout=10, params=params)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise e

    def fetch_json(self, url, params=None):
        """
        Method that fetches the json object from the target url.

        :param url: Target url from which the json is fetched
        :type url: str
        
        :param params: parameters associated to the url (field key=val, limit..)
        :type params: dict

        :raises RequestException: Request Errors for Status codes 4xx and 2xx

        :return: Body of the response in string fromat (raw)
        :rtype: json
        """
        try :
            response = requests.get(url,timeout=10, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise e

    def fetch_user_page(self, sleep_time=0.5):
        """
        Method that collect users name from the MAL recently connected users page
        
        :param sleep_time: parameter to set a delay in the execution of the function
        :type sleep_time: int

        :return: List of usernames (strings) from the recently connected users page.
        :rtype: list
        """
        def is_user_href(tag):
            """Parsing filter that target only hyperrefs without images containing the /profile string in it (corresponds to link to users pages)
            """
            return tag.has_attr('href') and not tag.find('img') and re.compile("/profile").search(tag['href'])
        
        time.sleep(sleep_time)
        target_page = "https://myanimelist.net/users.php"

        page_text = self.fetch_html(target_page)    
        soup = BeautifulSoup(page_text, "html.parser")
        users = list(map(lambda x : x.text, soup.find_all(is_user_href)))
        return users

    def find_friends(self, name:str, sleep_time=0.5):
        """
        Method that collect friends' users name from the a specific profile page.
        
        :param name: target user for which we are scraping friends names
        :type name: str

        :param sleep_time: parameter to set a delay in the execution of the function
        :type sleep_time: int

        :return: List of usernames (strings) who are friends with user name
        :rtype: list
        """
        def is_friend_name(tag):
            return tag.has_attr('href') and tag.parent.has_attr('class') and "title" in tag.parent['class'] and re.compile("https://myanimelist.net/profile/").search(tag['href'])

        time.sleep(sleep_time)
        target_page = "https://myanimelist.net/profile/{}/friends".format(name)
        
        page_text = self.fetch_html(target_page)
        soup = BeautifulSoup(page_text, "html.parser")
        friends_name = list(map(lambda x : x.text, soup.find_all(is_friend_name)))
        return friends_name

    def fetch_manga_profile(self, name:str, sleep_time=0.5):
        """
        Method that collect profile informations from a user.
        First, It fetches the raw html of the page and break it down into 4 section (in which informations for profile, mangas status&stats, and friends informations).
        Then for each section, the following informations are searched :
            - profile_info : gender, birthday, location
            - manga_status : Privated list or not
            - manga_stats : Number of entries
            - friends_info : If user has friends.
        
        :param name: target user for which we are scraping friends names
        :type name: str
        
        :param sleep_time: parameter to set a delay in the execution of the function
        :type sleep_time: int

        :raises HTMLParsingException: One of the section in which informations are searched wasn't found in the html text (Text incomplete or page structure changed)
        :raises PrivateListException: The users' manga list is marked as private in the profile (unecessary to keep scraping)
        :raises ScarceDataException: The users' manga list doesn't contain enough entries (unecessary to keep scraping)

        :return: Dictionary containing the users information (fields : username, gender, birthday, location, n_entries, friends)
        :rtype: dict
        """
        time.sleep(sleep_time)
        target_page = "https://myanimelist.net/profile/{}".format(name)
        
        page_text = self.fetch_html(target_page) 
        soup = BeautifulSoup(page_text, "html.parser")
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

        if n_entry < self.params["MIN_ENTRIES"]:
            raise ScarceDataException("[fetch_manga_profile] : The user has less registered manga entries than the minimal amount targeted (n={})".format(self.params["MIN_ENTRIES"]))

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
            friends = self.find_friends(name)
        
        return {"username" : name, "gender" : gender, "birthday" : birthday, "location" : location, "entries" : n_entry, "friends" : friends}

    def create_manga_interraction_entries(self, data, username):
        """
        Method to create and insert entries from a specific user's manga list into the entries table

        :param data: list of dict containing entries of the user `username`
        :type data: list
        
        :param username: username of the user for which the entries were fetched
        :type username: str

        :return: None
        """
        # json is structured as such : [{entry 0}... {entry 299}]
        # raise error if nothing ?
        if not data: # Empty => Bad offset or other issue ?
            return

        for manga in data:
            if not(manga['status'] >= 0 and manga['status'] <7):
                continue # Not even unknown
            self.cursor.execute("""INSERT OR IGNORE INTO entries (username, manga_id, status, read_chapters, score, start_date_string, end_date_string) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)""", (username, manga['manga_id'],self. MANGA_STATUS_CODE[manga['status']], manga['num_read_chapters'], manga['score'] if manga['score'] != 0 else None, manga['start_date_string'], manga['finish_date_string']))


    def fetch_manga_list(self, name:str, n_entry:int, sleep_time=0.5):
        """
        Method to fetch and insert entries from the manga list of user `name` into the database

        :param name: username of the targeted user
        :type name: str
        
        :param n_entry: number of entries of the user (approximate)
        :type n_entry: int

        :param sleep_time: parameter to set a delay in the execution of the function
        :type sleep_time: int

        :return: None
        """
        data_list = [] # Instead of iterating over entries that were previously created or adding to the database while there may be other pages not fetched (which could return an error and fetch partial data), do the requests first, then operate on received object if it went well.
        if n_entry < 1:
            raise ScarceDataException("[fetch_manga_list] : Attempted to fetch a manga_list with no entry")

        n_offsets = n_entry//self.MANGA_DISPLAY_LIMIT
        for i in range(0, n_offsets+1):
            time.sleep(sleep_time)
            target_page = "https://myanimelist.net/mangalist/{}/load.json".format(name)
            req_json = self.fetch_json(target_page, params={"offset": i*self.MANGA_DISPLAY_LIMIT})
            data_list.append(req_json)
            
        for data in data_list:
            self.create_manga_interraction_entries(data, name)

    def compute_dynamic_sleep(self, q_size:int, n_added:int, exp_factor:float=9) -> float:
            remaining_user_needed = self.params['MAX_USERS'] - n_added
            if remaining_user_needed <=0:
                return self.params["MAX_SLEEP"]

            ratio = min(q_size/remaining_user_needed,1) 

            sleep_time = self.params["MIN_SLEEP"] + (ratio**exp_factor * (self.params["MAX_SLEEP"] - self.params["MIN_SLEEP"]))

            return round(sleep_time, 1)

    def load_from_previous_session(self):
        self.cursor.execute("""SELECT username FROM users""")
        users = self.cursor.fetchall()
        usernames = [user[0] for user in users]
        self.seen = set(usernames)
        self.added = set(usernames)
        n_user_previous_session = len(usernames)
        return n_user_previous_session

    def load_pending(self):
            try:
                self.cursor.execute("""SELECT username FROM pending_recovery""")
                users = self.cursor.fetchall()
                usernames = [user[0] for user in users]
                for u in usernames:
                    self.name_queue.put(u)
                    self.seen.add(u)
                self.cursor.execute("""DELETE FROM pending_recovery""")
                self.conn.commit()
            except Exception as e:
                raise # Raise ? Return ? Define what are the issues here
            # Table may not exist.
            # Issue with the connection
            return
    
    def dump_pending(self):
            pending_users = []
            while not self.name_queue.empty():
                try:
                    user = self.name_queue.get_nowait()
                    if user is not self.SENTINEL:
                        pending_users.append((user,))
                    self.name_queue.task_done()

                except queue.Empty:
                    break
            try:
                self.cursor.executemany("INSERT OR IGNORE INTO pending_recovery (username) VALUES (?);", pending_users)
                self.conn.commit()
            except Exception as e:
                logging.error("dump_pending : error while converting pending names : {}".format(e))
                self.conn.rollback()
                raise
            return
        
    def create_user_review_database(self):
        n_loaded = self.load_from_previous_session()
        logging.info("Currently loaded : {}".format(n_loaded)) # TODO : Review logs -> This ?
        self.load_pending() # self
        lock = threading.Lock()
        link_user_data_stop = threading.Event()
        

        def create_users():
            print("chasse usernames ?")
            while not link_user_data_stop.is_set():
                print(self.added, len(self.added))
                if len(self.added) >= self.params['MAX_USERS'] + n_loaded: #self
                    break
                try:
                    print("we are trying to chase.")
                    with lock:
                        current_sleep = self.user_page_sleep
                    print("Is everything going well ?")
                    logging.debug(f"[THREAD A] : Current sleep time : {current_sleep}")
                    names = self.fetch_user_page(sleep_time=current_sleep)
                    added_loop = []
                    print(f"names : {names}")
                    for name in names:
                        
                        if link_user_data_stop.is_set(): #thread B crashes while we are putting names on the queue
                            break

                        if len(self.added) >= self.params['MAX_USERS'] + n_loaded: #max_users is reached while we are adding new names
                            break

                        with lock:
                            if name not in self.seen:
                                self.seen.add(name)
                                self.name_queue.put(name)
                                added_loop.append(name)
                    
                    logging.info("[THREAD A] : {} Users added during loop : {}".format(len(added_loop), added_loop))

                except requests.exceptions.ConnectionError:
                    logging.error("[THREAD A] : Connection Error : Waiting for Connection...")
                    time.sleep(self.params['CONNECTION_ISSUES_SLEEP']) 

                except requests.exceptions.Timeout:
                    logging.error("[THREAD A] : Timeout Error : Waiting before trying again...")
                    time.sleep(self.params['CONNECTION_ISSUES_SLEEP'])

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429 :
                        logging.error("[THREAD A] : Too Many Requests : Waiting before trying again...")
                        time.sleep(self.params['RATE_LIMIT_SLEEP'])
                    elif e.response.status_code == 403 :
                        # According to (https://myanimelist.net/forum/?topicid=1991772) 403 is the rate limit response received
                        logging.error("[THREAD A] : Too Many Requests : Waiting before trying again...")
                        time.sleep(self.params['RATE_LIMIT_SLEEP'])
                    else:
                        logging.error("[THREAD A] : Unhandled HTTP error ({}) : Stopping Thread A".format(e.response.status_code))
                        break

                except Exception as ue:
                    logging.error(f"[THREAD A] Unknown error : {ue} aborting scraping.")
                    self.name_queue.put(self.SENTINEL)
                    break

            self.name_queue.put(self.SENTINEL)
        
        def link_user_data():
            print("on link ?")
            with closing(self.conn):
                while True:
                    name = self.name_queue.get()
                    task_done = False
                    logging.debug(f"Current user : {name}")

                    with lock:
                        q_size = self.name_queue.qsize()
                        n_added = len(self.added)
                        logging.debug(f"[THREAD B] : Added total {n_added}")
                        self.user_page_sleep = self.compute_dynamic_sleep(q_size, n_added - n_loaded)
                        logging.debug("[THREAD B] : Current user page fetch time sleep : {}\n \t Number of currently fetched users : {}\n \t Number of currently added users {}\n \t(Previously loaded : {})".format(self.user_page_sleep, q_size, n_added - n_loaded, n_loaded))

                    if name is self.SENTINEL or len(self.added) > self.params['MAX_USERS'] + n_loaded:
                        self.name_queue.task_done()
                        self.dump_pending()
                        break

                    try:
                        success = False
                        while not success:
                            try:
                                user_info = self.fetch_manga_profile(name, sleep_time=1)
                                friends = user_info.pop("friends") #user_info doesn't have friends anymore

                                self.cursor.execute("""INSERT INTO users (username, gender, birthday, location, entries)
                                                    VALUES (?, ?, ?, ?, ?)""", (user_info["username"], user_info["gender"], user_info["birthday"], user_info["location"], user_info["entries"]))
                                self.fetch_manga_list(name, user_info["entries"], sleep_time=1) # we fecth after trying to insert the user, if it's already in the db (from previous runs), fails and no need to fetch ! (saving requests)

                                if friends is not None:
                                    for friend in friends:
                                        with lock:
                                            if friend in self.added: #name not in added because INSERT INTO users didn't fail.
                                                left_user = min(name, friend)
                                                right_user = max(name, friend)
                                                logging.debug(f"Friend in db detected, relationship is being created : ({left_user}, {right_user})")
                                                self.cursor.execute("""INSERT INTO relationships (user_left, user_right) values (?, ?)""", (left_user, right_user)) #Add every relationship between user and friends that have already been added
                                            elif friend not in self.seen and self.name_queue.qsize():
                                                self.seen.add(friend)
                                                self.name_queue.put(friend)
                                with lock:
                                    self.added.add(name)
                                
                                self.conn.commit()
                                success = True
                            
                            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                                logging.error(f"[THREAD B] : Connection Error : {e} | Waiting for Connection...")
                                self.conn.rollback()
                                time.sleep(self.params['CONNECTION_ISSUES_SLEEP'])

                            except requests.exceptions.HTTPError as e:
                                if (e.response.status_code == 429 or e.response.status_code == 403):
                                    logging.error("[THREAD B] : Too Many Requests : Waiting before trying again...")
                                    self.conn.rollback()
                                    time.sleep(self.params['RATE_LIMIT_SLEEP'])
                                elif (e.response.status_code == 404):
                                    logging.error(f"[THREAD B] : User {name} not found. Skipping ...")
                                    self.conn.rollback()
                                    break
                                else:
                                    logging.error(F"[THREAD B] : Error : {e}")
                                    link_user_data_stop.set()
                                    self.user_page_sleep = self.params["MAX_SLEEP"] # we don't know if thread A crashed, put maximum timer and dump.
                                    self.name_queue.task_done()
                                    task_done=True
                                    self.conn.rollback()
                                    self.dump_pending(self.name_queue)
                                    break

                    except (HTMLParsingException, ScarceDataException, PrivateListException) as e:
                        logging.error(f"[THREAD B] : Skiping user {name}, cause : {e}")
                        self.conn.rollback()
                    
                    except sqlite3.IntegrityError as e:
                        logging.error(f"[THREAD B] : User {name} is already in the database, skipping user : {e}")
                        self.conn.rollback()
                    
                    except sqlite3.Error as e:
                        logging.error(f"[THREAD B] : Database error while saving {name}: {e} \nCurrently no clue what to do here, user will be skipped")
                        self.conn.rollback()
                    
                    except Exception as ue:
                        logging.error(f"[THREAD B] : Unknwon exception ; Abort scraping : {ue}")
                        self.conn.rollback()
                        self.user_page_sleep = self.params["MAX_SLEEP"] # we don't know if thread A crashed, put maximum timer and dump.
                        self.name_queue.task_done()
                        task_done=True
                        self.conn.rollback()
                        link_user_data_stop.set()
                        self.dump_pending()
                        break

                    finally:
                        if not task_done: # If an error requiring to dump names from the queue has been caught, ignore the task_done order (was done before)
                            self.name_queue.task_done()
                
                link_user_data_stop.set()

        print("Starting..")
        user_name_thread = threading.Thread(target=create_users)
        rating_thread = threading.Thread(target=link_user_data)

        user_name_thread.start()
        rating_thread.start()

        user_name_thread.join()
        rating_thread.join()
        print("Done !")

    def run(self, profiler = True):
        if profiler :
            logging.basicConfig(filename=self.params["LOG_PATH"], level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
            cProfile.runctx("self.create_user_review_database()", globals=globals(), locals=locals(), filename=self.params["PROFILER_PATH"])
        else:
            self.create_user_review_database()

if __name__ == "__main__":
    scraper_instance = Scraper()
    scraper_instance.run()