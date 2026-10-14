import requests
from ui.pages.config import param


def search_username(string: str, limit=10) -> list:
    response = requests.get(f"{param["API_URL"]}/users/search?q={string}&limit={limit}")
    response.raise_for_status()
    return response.json()['data']

def search_manga(string: str, limit=10) -> list:
    response = requests.get(f"{param["API_URL"]}/mangas/search?q={string}&limit={limit}")
    response.raise_for_status()
    return response.json()["data"]

def get_manga_entries(manga_id:int) -> list[dict]:
    nentries = requests.get(f"{param["API_URL"]}/entries/manga/{manga_id}/?counting=true", timeout=90).json()["data"]
    offset = nentries//200
    res = []
    for i in range(offset+1):
        response = requests.get(f"{param["API_URL"]}/entries/manga/{manga_id}/?offset={i*200}", timeout=90) # 200 : LIMIT SET BY THE API
        response.raise_for_status()
        res += response.json()["data"]
    return res

def get_user_entries(username: str) -> list[dict]:
    response = requests.get(f"{param["API_URL"]}/entries/user/{username}/full", timeout=90)
    response.raise_for_status()
    return response.json()["data"]

def query_api(url) -> list[dict]:
    response =  requests.get(url, timeout=90)
    response.raise_for_status()
    return response.json()["data"]
