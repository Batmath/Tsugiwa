import cProfile
import logging
import queue
import re  #regex
import signal
import sqlite3
import threading
import time

import requests
from bs4 import BeautifulSoup

from scraper import settings
from shared.db_scheme import *

logger = logging.getLogger(__name__)

class PrivateListException(Exception):
    pass

class UserPageException(Exception):
    pass

class HTMLParsingException(Exception):
    pass

class ScarceDataException(Exception):
    pass

class ThreadError(Exception):
    pass

# TODO : Setup tests (API + Scraper)
# TODO : Add rule enforcement on values such as SLEEP Times, Users etc (non negative) -> Change impact Tests (make sure each variable checked is then chekced in the tests)
# TODO : yaml file pre-commit that check ruff for errors.

class Scraper:

    def __init__(self, params : settings.ParametersScraper | None = None, session : requests.Session | None = None, conn : sqlite3.Connection | None = None):
        """Constructor method
        """

        self.params = params.model_dump() if params is not None else settings.ParametersScraper().model_dump()
        self.conn = conn if conn is not None else sqlite3.connect(self.params["DB_PATH"], check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.user_page_sleep = self.params["MIN_SLEEP"]
        self.MANGA_STATUS_CODE = {0: "Unknown", 1 : "Reading", 2 : "Completed", 3 : "On-Hold", 4 : "Dropped", 6 : "Plan to Read"} # Code on MAL for different entries statuses (Last checked : 27/06/26)
        self.MANGA_DISPLAY_LIMIT = 300 # limit of manga per page is 300 (when calling "https://myanimelist.net/mangalist/username/load.json")
        self.session = session if session is not None else requests.Session()
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
        self.lock = threading.Lock()
        self.thread_A_stop_signal = threading.Event()
        self.container_stop_signal = threading.Event()

    def fetch_html(self, url:str, params=None):
        """
        Method that fetches the text content from a url page.
        :param url: Target url from which the text is fetched
        :type url: str
        
        :param params: parameters associated to the url (field key=val, limit..)
        :type params: dict

        :raises RequestException: Request Errors for Status codes > 4xx (400-599)

        :return: Body of the response in string fromat (raw)
        :rtype: str
        """
        response = self.session.get(url,timeout=10, params=params)
        response.raise_for_status()
        return response.text

    def fetch_json(self, url:str, params=None):
        """
        Method that fetches the json object from the target url.

        :param url: Target url from which the json is fetched
        :type url: str
        
        :param params: parameters associated to the url (field key=val, limit..)
        :type params: dict

        :raises RequestException: Request Errors for Status codes > 4xx (400-599)

        :return: Body of the response in string fromat (raw)
        :rtype: json
        """
        response = self.session.get(url,timeout=10, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_user_page(self, sleep_time:float=0.5):
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
        try:
            user_block = soup.find("div", class_="normal_header").next_sibling.next_sibling
        except AttributeError:
            raise UserPageException("[fetch_user_page] : User block was found empty. Either MAL user page is empty or try to update user_block_ref")
        users = [x.text for x in user_block.find_all(is_user_href)]
        return users

    def find_friends(self, name:str, sleep_time:float=0.5):
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
        target_page = f"https://myanimelist.net/profile/{name}/friends"

        page_text = self.fetch_html(target_page)
        soup = BeautifulSoup(page_text, "html.parser")
        friends_name = [x.text for x in soup.find_all(is_friend_name)]
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
        target_page = f"https://myanimelist.net/profile/{name}"

        page_text = self.fetch_html(target_page)
        soup = BeautifulSoup(page_text, "html.parser")

        profile_info = soup.find("ul", class_="user-status")
        manga_status = soup.find("div", class_="updates manga")
        manga_stats = soup.find("div", class_="stats manga")
        friends_info = soup.find("div", class_="user-friends")

        if profile_info is None or manga_stats is None or manga_status is None or friends_info is None:
            raise HTMLParsingException("Error while parsing the HTML file, one of the target class wasn't found")

        #Checking if the list is private
        is_private = manga_status.find(string=re.compile("Access to this list has been restricted by the owner.")) is not None
        if is_private:
            raise PrivateListException("[fetch_manga_profile] : The User's Manga List is marked as private, unable to fetch manga data")

        # Check number of entries and to avoid scarce data & prepare offsets
        n_entry = -1
        entry_text = manga_stats.find(string=re.compile("Total Entries"))
        if entry_text is not None:
            n_entry = int(entry_text.parent.next_sibling.text.replace(",", ""))

        if n_entry < self.params["MIN_ENTRIES"]:
            raise ScarceDataException("[fetch_manga_profile] : The user has less registered manga entries than the minimal amount targeted (n={})".format(self.params["MIN_ENTRIES"]))

        #informations to fetch : gender, birthday, location
        # These informations inside the user-status element are presented as two span element siblings (One has the type of category and the other, the value)
        gender = None
        has_gender = profile_info.find(string=re.compile("Gender"))
        if has_gender is not None:
            gender = has_gender.parent.next_sibling.text

        birthday = None
        has_birthday = profile_info.find(string=re.compile("Birthday"))
        if has_birthday is not None:
            match = re.search("[0-9]{4}", has_birthday.parent.next_sibling.text)
            birthday = int(match.group()) if match else None

        location = None
        has_location = profile_info.find(string=re.compile("Location"))
        if has_location is not None:
            location = has_location.parent.next_sibling.text

        friends = None
        has_no_friends = friends_info.find(string=re.compile("No friend yet."))
        if has_no_friends is None:
            friends = self.find_friends(name)

        return {"username" : name, "gender" : gender, "birthday" : birthday, "location" : location, "entries" : n_entry, "friends" : friends}

    def create_manga_interraction_entries(self, data, userid):
        """
        Method to create and insert entries from a specific user's manga list into the entries table
        the json input from MAL website is structured as such : [{entry 0}... {entry 299}]

        :param data: list of dict containing entries of the user `username`
        :type data: list
        
        :param username: username of the user for which the entries were fetched
        :type username: str

        :return: None
        """
        # json is structured as such :
        if not data: # Empty => Bad offset or other issue ?
            return

        for manga in data:
            if not(manga['status'] >= 0 and manga['status'] <7 and manga['status'] != 5):
                continue # Not even unknown
            self.cursor.execute("""INSERT OR IGNORE INTO entries (user_id, manga_id, status, read_chapters, score, start_date_string, end_date_string) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)""", (userid, manga['manga_id'],self. MANGA_STATUS_CODE[manga['status']], manga['num_read_chapters'], manga['score'] if manga['score'] != 0 else None, manga['start_date_string'], manga['finish_date_string']))

    def collect_manga_data(self, name, n_entry, sleep_time=0.5):
        data_list = []
        if n_entry < 1:
            raise ScarceDataException("[fetch_manga_list] : Attempted to fetch a manga_list with no entry")

        n_offsets = n_entry//self.MANGA_DISPLAY_LIMIT
        for i in range(n_offsets+1):
            time.sleep(sleep_time)
            target_page = f"https://myanimelist.net/mangalist/{name}/load.json"
            req_json = self.fetch_json(target_page, params={"offset": i*self.MANGA_DISPLAY_LIMIT})
            data_list.append(req_json)

        return data_list

    def fetch_manga_list(self, name:str, userid:int, n_entry:int, sleep_time=0.5):
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
        data_list = self.collect_manga_data(name, n_entry, sleep_time)
        for data in data_list:
            self.create_manga_interraction_entries(data, userid)

    def compute_dynamic_sleep(self, q_size:int, n_added:int, exp_factor:float=9) -> float:
        """
        Method that compute sleep time (between function calls) according to the current number of name fetched and difference between the targeted number of user
        and the current number of users.
        
        :param q_size: Size of the queue in which the pending usernames are added.
        :type q_size: int
        
        :param n_added: Number of users added to the data during the current scraper run.
        :type n_added: int
        
        :param exp_factor: power added to the ratio. Control the "speed" at which the computed sleep time reach MAX_SLEEP (the smaller the power is, the quicker sleep_time reaches MAX_SLEEP).
        :type exp_factor: int

        :return: Computed sleep time rounded to one decimal. (MAX_SLEEP if no remaining user needed).
        :rtype: float
        """
        remaining_user_needed = self.params['MAX_USERS'] - n_added
        if remaining_user_needed <=0:
            return self.params["MAX_SLEEP"]

        ratio = min(q_size/remaining_user_needed,1)

        sleep_time = self.params["MIN_SLEEP"] + (ratio**exp_factor * (self.params["MAX_SLEEP"] - self.params["MIN_SLEEP"]))
        return round(sleep_time, 1)

    def load_from_previous_session(self):
        """
        Method to load pending usernames from previous scraper runs (usernames that were discovered and added to the dataset)

        :return: number of users 
        :rtype: int
        """
        self.cursor.execute("""SELECT username FROM users""")
        users = self.cursor.fetchall()
        usernames = [user[0] for user in users]
        self.seen = set(usernames)
        self.added = set(usernames)
        n_user_previous_session = len(usernames)
        return n_user_previous_session

    def load_pending(self):
        """
        Method to load pending usernames from previous scraper runs (usernames that were discovered and but not treated)
        """
        self.cursor.execute("""SELECT username FROM pending_recovery""")
        users = self.cursor.fetchall()
        usernames = [user[0] for user in users]
        for u in usernames:
            self.name_queue.put(u)
            self.seen.add(u)
        self.cursor.execute("""DELETE FROM pending_recovery""")
        self.conn.commit()

    def dump_pending(self):
        """
        Method to dump pending usernames from previous scraper runs (usernames that were discovered and added to the dataset)
        """
        pending_users = []
        while not self.name_queue.empty():
            user = self.name_queue.get_nowait()
            if user is not self.SENTINEL:
                pending_users.append((user,))
            self.name_queue.task_done()
        try:
            self.cursor.executemany("INSERT OR IGNORE INTO pending_recovery (username) VALUES (?);", pending_users)
            self.conn.commit()
        except Exception as e:
            logger.error(f"dump_pending : error while converting pending names : {e}")
            self.conn.rollback()
            raise

    def integrate_user(self, name, add_friends=True, sleep_time=1):
        success = False
        while not success:
            try:
                user_info = self.fetch_manga_profile(name, sleep_time=sleep_time)
                friends = user_info.pop("friends") #user_info doesn't have friends anymore

                self.cursor.execute("""INSERT INTO users (username, gender, birthday, location, entries)
                                    VALUES (?, ?, ?, ?, ?)""", (user_info["username"], user_info["gender"], user_info["birthday"], user_info["location"], user_info["entries"]))
                user_id = self.cursor.execute("""SELECT user_id FROM users WHERE username = ?""", (user_info["username"],)).fetchone()[0]
                self.fetch_manga_list(name, user_id, user_info["entries"],  sleep_time=sleep_time) # we fecth after trying to insert the user, if it's already in the db (from previous runs), fails and no need to fetch ! (saving requests)

                if friends is not None and add_friends:
                    for friend in friends:
                        with self.lock:
                            if friend in self.added: #name not in added because INSERT INTO users didn't fail.
                                friend_id = self.cursor.execute("""SELECT user_id FROM users WHERE username = ?""", (friend,)).fetchone()[0]
                                left_user = min(user_id, friend_id)
                                right_user = max(user_id, friend_id)
                                self.cursor.execute("""INSERT INTO relationships (user_id_left, user_id_right) values (?, ?)""", (left_user, right_user)) #Add every relationship between user and friends that have already been added
                            elif friend not in self.seen:
                                self.seen.add(friend)
                                self.name_queue.put(friend)
                with self.lock:
                    self.added.add(name)

                self.conn.commit()
                success = True

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                logger.error(f"[THREAD B] : Connection Error : {e} | Waiting for Connection...")
                time.sleep(self.params['CONNECTION_ISSUES_SLEEP'])
                self.conn.rollback()

            except (HTMLParsingException, ScarceDataException, PrivateListException) as e:
                    logger.error(f"[THREAD B] : Skiping user {name}, cause : \n \t{e}")
                    self.conn.rollback()
                    return

            except sqlite3.IntegrityError as e:
                logger.error(f"[THREAD B] : Database integrity violation on user {name}, aborting integration : \n \t{e}")
                self.conn.rollback()
                raise

            except requests.exceptions.HTTPError as e:
                if (e.response.status_code == 429 or e.response.status_code == 403):
                    logger.error("[THREAD B] : Too Many Requests : Waiting before trying again...")
                    time.sleep(self.params['RATE_LIMIT_SLEEP'])
                    self.conn.rollback()
                elif (e.response.status_code == 404):
                    logger.error("[THREAD B] : Page not found : Skipping user")
                    self.conn.rollback()
                    return
                else:
                    logger.error(f"[THREAD B] : Uncharacterised HTTP Error ({e.response.status_code}) Abort user integration")
                    self.conn.rollback()
                    raise

            except Exception as e:
                logger.error(f"[THREAD B] : Uncharacterised Error ({e}) Abort integration")
                self.conn.rollback()
                raise

    def create_users(self, n_loaded):
            """
            Method that collects usernames from MAL user page to add them to the scraper name queue.
            :raises requests.exceptions.ConnectionError: Internet connection was cut (retries)
            :raises requests.exceptions.Timeout: Request timeout (retries)
            :raises requests.exceptions.HTTPError: Rate limit code leads to a retry (403 according to https://myanimelist.net/forum/?topicid=1991772 and 429) any other HTTPError code stops Thread A.
            :raises Exception: Unknown errors also leads to Thread A stopping
            """
            while not self.thread_A_stop_signal.is_set() and not self.container_stop_signal.is_set():
                if len(self.added) >= self.params['MAX_USERS'] + n_loaded:
                    break
                try:
                    logger.debug(f"[THREAD A] : Current sleep time : {self.user_page_sleep}")
                    names = self.fetch_user_page(sleep_time=self.user_page_sleep)
                    for name in names:
                        with self.lock:
                            if name not in self.seen:
                                self.seen.add(name)
                                self.name_queue.put(name)

                except requests.exceptions.ConnectionError:
                    logger.error("[THREAD A] : Connection Error : Waiting for Connection...")
                    time.sleep(self.params['CONNECTION_ISSUES_SLEEP'])

                except requests.exceptions.Timeout:
                    logger.error("[THREAD A] : Timeout Error : Waiting before trying again...")
                    time.sleep(self.params['CONNECTION_ISSUES_SLEEP'])

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429  or e.response.status_code == 403:
                        logger.error("[THREAD A] : Too Many Requests : Waiting before trying again...")
                        time.sleep(self.params['RATE_LIMIT_SLEEP'])
                    else:
                        logger.error(f"[THREAD A] : Unhandled HTTP error ({e.response.status_code} -> {e}) : Stopping Thread A")
                        self.name_queue.put(self.SENTINEL)
                        raise

                except Exception as ue:
                    logger.error(f"[THREAD A] Unknown error : {ue} aborting scraping, thread A has been stopped.")
                    self.name_queue.put(self.SENTINEL)
                    raise

            self.name_queue.put(self.SENTINEL)

    def link_user_data(self, n_loaded):
            """
            Method that collect user's profile data and manga entries. Adds discovered friends name back to the scraper name queue
            :raises requests.exceptions.ConnectionError: Internet connection was cut (retries)
            :raises requests.exceptions.Timeout: Request timeout (retries)
            :raises requests.exceptions.HTTPError: Rate limit code leads to a retry (403 according to https://myanimelist.net/forum/?topicid=1991772 and 429) any other HTTPError code stops Thread B.
            :raises HTMLParsingException: Request timeout (retries)
            :raises ScarceDataException: Request timeout (retries)
            :raises PrivateListException: Request timeout (retries)
            :raises sqlite3.IntegrityError: Request timeout (retries)
            :raises Exception: Unknown errors also leads to Thread B stopping
            """
            while not self.container_stop_signal.is_set():
                try:
                    name = self.name_queue.get(timeout=self.params["QUEUE_TIMEOUT"])

                except (queue.Empty):
                    logger.error(f"[THREAD B] : Queue has been empty for {self.params["QUEUE_TIMEOUT"]}s, aborting linking")
                    break

                with self.lock:
                    q_size = self.name_queue.qsize()
                    n_added = len(self.added)
                    self.user_page_sleep = self.compute_dynamic_sleep(q_size, n_added - n_loaded)

                if name is self.SENTINEL or len(self.added) > self.params['MAX_USERS'] + n_loaded:
                    self.name_queue.task_done()
                    self.dump_pending()
                    break

                try:
                    self.integrate_user(name)

                except Exception as ue:
                    logger.error(f"[THREAD B] : Unexpected error; Abort scraping : \n \t {ue}")
                    self.conn.rollback()
                    self.user_page_sleep = self.params["MIN_SLEEP"]
                    self.thread_A_stop_signal.set()
                    self.name_queue.task_done()
                    self.dump_pending()
                    raise

            self.thread_A_stop_signal.set()

    def handle_sigterm(self, signum, frame):
        print("SIGTERM caught, dumping queued usernames")
        self.container_stop_signal.set()

    def create_user_review_database(self):
        """
        Method to create the manga entries dataset. Build a Bi-Thread web scraper that fetches users information and manga reviews from MAL :
            - Thread A : Collects usernames from MAL user page (https://myanimelist.net/users.php), add them to the queue.
            - Thread B : Collects (when applicable) the data (profile data & manga entries data) for the user. Adds friends name to the queue.
        """
        n_loaded = self.load_from_previous_session()
        self.load_pending()

        signal.signal(signal.SIGTERM, self.handle_sigterm)

        user_name_thread = threading.Thread(target=self.create_users, args=(n_loaded,))
        rating_thread = threading.Thread(target=self.link_user_data, args=(n_loaded,))

        user_name_thread.start()
        rating_thread.start()

        user_name_thread.join()
        rating_thread.join()

        self.dump_pending()

    def run(self, profiler = True):
        if profiler :
            logging.basicConfig(filename=self.params["LOG_PATH"], level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s (%(threadName)s)')
            cProfile.runctx("self.create_user_review_database()", globals=globals(), locals=locals(), filename=self.params["PROFILER_PATH"])
        else:
            self.create_user_review_database()

if __name__ == "__main__":
    scraper_instance = Scraper()
    scraper_instance.run()
