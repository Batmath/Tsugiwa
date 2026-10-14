import requests
from ui.pages.config import param


def get_manga_entries(manga_id:int) -> list[dict]:
    nentries = requests.get(f"{param["API_URL"]}/entries/manga/{manga_id}/?counting=true", timeout=90).json()["data"]
    offset = nentries//200
    res = []
    for i in range(offset+1):
        response = requests.get(f"{param["API_URL"]}/entries/manga/{manga_id}/?offset={i*200}", timeout=90) # 200 : LIMIT SET BY THE API
        response.raise_for_status()
        res += response.json()["data"]
    return res

def query_api(url) -> list[dict]:
    response =  requests.get(url, timeout=90)
    response.raise_for_status()
    return response.json()["data"]
