import requests
from ui.pages.config import param


def search_username(string: str, limit=10) -> list:
    response = requests.get(f"{param["API_URL"]}/users/search?q={string}&limit={limit}")
    response.raise_for_status()
    return response.json()['data']

def search_manga(string: str, limit=10) -> list:
    response = requests.get(f"{param["API_URL"]}/mangas/search?q={string}&limit={limit}")
    response.raise_for_status()
    return response.json()['data']

def get_user_entries(username: str) -> list[dict]:
    r = requests.get(f"{param["API_URL"]}/entries/user/{username}/full", timeout=10)
    r.raise_for_status()
    return r.json()["data"]
