import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re

class PrivateListException(Exception):
    pass

class HTMLParsingException(Exception):
    pass

class ScarceDataException(Exception):
    pass

# TODO : deal with offsets, issues (another request to Jikan ? Request to MAL ?)
# TODO : finish fetch_manga_list method, combine it with fetch user info to create 2 databases.
# TODO : add comments
# TODO : Will they finish the manga ? What location ? What age ? What gender ?

MANGA_STATUS_CODE = {1 : "Reading", 2 : "Completed", 3 : "On-Hold", 4 : "Dropped", 6 : "Plan to Read"}
MANGA_DISPLAY_LIMIT = 300 # limit of manga per page is 300 (when calling "https://myanimelist.net/mangalist/username/load.json")


def fetch_user_page():

    def is_user_href(tag):
        return tag.has_attr('href') and not tag.find('img') and re.compile("/profile").search(tag['href'])
    
    target_page = "https://myanimelist.net/users.php"

    req = requests.get(target_page)
    if req.status_code == 200 :
        soup = BeautifulSoup(req.text, "html.parser")
        users = list(map(lambda x : x.text, soup.find_all(is_user_href)))
        print(users)
    else : 
        req.raise_for_status()

def fetch_manga_profile(name:str, min_entry=1, sleep_time=0.5):
        #re.compile("Access to this list has been restricted by the owner.").search(tag.find_next_sibling("p"))
        #re.compile("Last Manga Updates").search(tag.text) and re.compile("Access to this list has been restricted by the owner.").search(tag.find_next_sibling("p"))
        #Could also add friends ! 
    time.sleep(sleep_time)
    target_page = "https://myanimelist.net/profile/{}".format(name)
    req = requests.get(target_page)
    
    if req.status_code == 200:
        soup = BeautifulSoup(req.text, "html.parser")
        
        #print(soup.find_all("p", string=re.compile("Access to this list has been restricted by the owner.")))
        # On the Statistics layout, there are two Total Entries, Anime and Manga

        #Other approach : search for the Blocks then fetch informations
        #
        profile_info = soup.find("ul", class_="user-status")
        manga_status = soup.find("div", class_="updates manga")
        manga_stats = soup.find("div", class_="stats manga")

        if not(profile_info or manga_stats or manga_status):
            raise HTMLParsingException("Error while parsing the HTML file, one of the target class wasn't found")
        
        #Checking if the list is private
        is_private = manga_status.find(string=re.compile("Access to this list has been restricted by the owner.")) is not None
        if is_private:
            raise PrivateListException("[fetch_manga_profile] : The User's Manga List is marked as private, unable to fetch manga data")
        
        # Check number of entries and to avoid scarce data & prepare offsets
        n_entry = -1
        entry_text = manga_stats.find(string=re.compile("Total Entries"))
        if entry_text :
            n_entry = int(entry_text.parent.next_sibling.text)

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

        return {"username" : name, "gender" : gender, "birthday" : birthday, "location" : location, "entries" : n_entry}
    else:
        req.raise_for_status()

def create_manga_interraction_entries(data, username, entries:list):
    # json is structured as such : {[0..99] : [{entry 0}... {entry 99}], [100..199] : ...}
    # raise error if nothing
    print(data)
    for manga in data:
        review_entry = {
            "username" : username,
            "manga_id" : manga['manga_id'],
            "status" : MANGA_STATUS_CODE[manga['status']],
            "n_read_chapters" : manga['num_read_chapters'],
            "score" : manga['score'] if manga['score'] != 0 else None,
        }
        entries.append(review_entry)

def fetch_manga_list(name:str, n_entry:int, entries:list, sleep_time=0.5):
    if n_entry < 1:
        raise ScarceDataException("[fetch_manga_list] : Attempted to fetch a manga_list with no entry")

    n_offsets = n_entry//MANGA_DISPLAY_LIMIT
    print(n_offsets)
    for i in range(0, n_offsets+1):
        time.sleep(sleep_time)
        target_page = "https://myanimelist.net/mangalist/{}/load.json".format(name)
        req = requests.get(target_page, params={"offset": i*MANGA_DISPLAY_LIMIT})
        if req.status_code == 200:
            print(req.url)
            data = req.json()
            create_manga_interraction_entries(data, name, entries)
        else:
            req.raise_for_status()
    print("Manga list from {} has been fetched successfully!".format(name)) 

def create_users(max_users = 10):
    return

def link_user_id():
    while True:
        return

if __name__ == "__main__":
    user_info = fetch_manga_profile("Matmath")
    print(user_info)
    all_entries = []
    fetch_manga_list(user_info["username"], user_info["entries"], all_entries)
    review_df = pd.DataFrame(all_entries)
    print(review_df)
    review_df.to_csv("user_review_entries.csv",index=False, encoding='utf-8')
