import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import threading
import queue

class PrivateListException(Exception):
    pass

class HTMLParsingException(Exception):
    pass

class ScarceDataException(Exception):
    pass

# TODO : add comments
# TODO : Will they finish the manga ? What location ? What age ? What gender ?

MANGA_STATUS_CODE = {1 : "Reading", 2 : "Completed", 3 : "On-Hold", 4 : "Dropped", 6 : "Plan to Read"}
MANGA_DISPLAY_LIMIT = 300 # limit of manga per page is 300 (when calling "https://myanimelist.net/mangalist/username/load.json")
session = requests.Session()
headers={
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

def fetch_user_page(session):

    def is_user_href(tag):
        return tag.has_attr('href') and not tag.find('img') and re.compile("/profile").search(tag['href'])
    
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
        with open("friends.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
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
        with open("profile.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
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

def create_manga_interraction_entries(data, username, entries:list):
    # json is structured as such : [{entry 0}... {entry 99}]
    # raise error if nothing
    for manga in data:
        review_entry = {
            "username" : username,
            "manga_id" : manga['manga_id'],
            "status" : MANGA_STATUS_CODE[manga['status']],
            "n_read_chapters" : manga['num_read_chapters'],
            "score" : manga['score'] if manga['score'] != 0 else None,
        }
        entries.append(review_entry)

def fetch_manga_list(name:str, n_entry:int, entries:list, session, sleep_time=0.5):
    if n_entry < 1:
        raise ScarceDataException("[fetch_manga_list] : Attempted to fetch a manga_list with no entry")

    n_offsets = n_entry//MANGA_DISPLAY_LIMIT
    for i in range(0, n_offsets+1):
        time.sleep(sleep_time)
        target_page = "https://myanimelist.net/mangalist/{}/load.json".format(name)
        req = session.get(target_page, params={"offset": i*MANGA_DISPLAY_LIMIT})
        if req.status_code == 200:
            data = req.json()
            create_manga_interraction_entries(data, name, entries)
        else:
            req.raise_for_status()
    print("Manga list from {} has been fetched successfully!".format(name)) 

def create_user_review_database(max_users = 10):
    seen = set()
    added = set()
    name_queue = queue.Queue()
    all_rating_entries = []
    all_user_entries = []
    lock = threading.Lock()
    SENTINEL = None
    user_per_page = 20 #myanimelist.net/users.php always gives 20 names

    session = requests.Session()
    session.headers.update(headers)

    def create_databases(entries_rating, entries_user, rating_path="raw_rating.csv", user_path="raw_user.csv"):
        user_df = pd.DataFrame(entries_user)
        rating_df = pd.DataFrame(entries_rating)

        user_df.to_csv(user_path,index=True, encoding='utf-8')
        rating_df.to_csv(rating_path, index=False, encoding='utf-8')


    def has_room(added, name_queue, max_users):
        buffer = max(5, int(len(max_users) * 0.10))
        return len(added) + name_queue.qsize() < max_users + buffer

    def create_users():
        while True:
            with lock:
                if len(added) >= max_users:
                    break
            try:
                names = fetch_user_page(session)
                for name in names:
                    with lock:
                        if name not in seen and has_room(added, name_queue, max_users):
                            seen.add(name)
                            name_queue.put(name)
                        else :
                            print("user {} has already been seen or buffer is full".format(name))
                time.sleep(3)

            except requests.exceptions.ConnectionError:
                print("Connection Error : Waiting for Connection...")
                time.sleep(5)
            except requests.exceptions.Timeout:
                print("Timeout Error : Waiting before trying again...")
                time.sleep(5)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 :
                    print("Too Many Requests : Waiting before trying again...")
                    time.sleep(5)
                else:
                    raise
        name_queue.put(SENTINEL)
    
    def link_user_data():
        while True:
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
                            for friend in friends:
                                with lock:
                                    if friend not in seen and has_room(added, name_queue, max_users):
                                        seen.add(friend)
                                        name_queue.put(friend)
                                    else :
                                        print("user {} has already been seen or buffer is full".format(friend))
                        fetch_manga_list(name, user_info["entries"], all_rating_entries, session)
                        with lock:
                            added.add(name)
                            print("Currently added : {}".format(added))
                        success = True
                    except requests.exceptions.ConnectionError:
                        print("Connection Error : Waiting for Connection...")
                        time.sleep(5)

                    except requests.exceptions.Timeout:
                        print("Timeout Error : Waiting before trying again...")
                        time.sleep(5)
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 429 :
                            print("Too Many Requests : Waiting before trying again...")
                            time.sleep(5)
                        else:
                            raise
            except (HTMLParsingException, ScarceDataException, PrivateListException) as e:
                print("Skiping user {}, cause : {}".format(name, e))
            finally:
                name_queue.task_done()   

    user_name_thread = threading.Thread(target=create_users)
    rating_thread = threading.Thread(target=link_user_data)

    user_name_thread.start()
    rating_thread.start()

    user_name_thread.join()
    rating_thread.join()

def create_users(max_users = 10):
    return

def link_user_id():
    while True:
        return

if __name__ == "__main__":
    create_user_review_database()
