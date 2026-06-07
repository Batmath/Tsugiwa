import json
import time
import requests
import pandas as pd

def update_manga_entries(request, entry_list):

    data = request.json()['data']
    for elt in data:
        entry = {
            "id" : elt['mal_id'],
            "title" : elt['title'],
            "title_english" : elt['title_english'],
            "title_japanese" : elt['title_japanese'],
            "genres" : ",".join([genre['name'] for genre in elt['genres']] + [genre['name'] for genre in elt['explicit_genres']]),
            "themes" : ",".join([theme['name'] for theme in elt['themes']]),
            "media_type" : elt['type'],
            "demographics" : ",".join([demographic['name'] for demographic in elt['demographics']]),
            "mean_score" : elt['score'],
            "scored_by" : elt['scored_by'],
            "rank" : elt['rank'],
            "popularity_rank" : elt['popularity'],
            "members" : elt['members'],
            "favorites" : elt['favorites'],
            "status" : elt['status'],
            "publishing" : elt['publishing'],
            "published_from" : elt['published']['from'] if 'from' in elt['published'].keys() else 'NULL',
            "published_to" : elt['published']['to'] if 'to' in elt['published'].keys() else 'NULL',
            "chapters" : elt['chapters'],
            "volumes" : elt['volumes'],
            "authors" : ",".join([author['name'] for author in elt['authors']]),
            "url_img" : elt['images']['jpg']['image_url'] if 'jpg' in elt['images'].keys() else elt['images']['webp']['image_url'] if 'webp' in elt['images'].keys() else 'NULL',
            "synopsis" : elt['synopsis'].split('\n\n[Written by MAL Rewrite]',1)[0] if elt['synopsis'] else 'NULL',
        }
        entry_list.append(entry)
    return entry_list

def create_manga_database(base_url= "https://api.jikan.moe/v4/", page_offset=0, page_limit=None, output_path='./manga.csv'):
    page = 1
    next_page = True
    entries = []

    while next_page:
        time.sleep(1.03)
        try :
            req = requests.get(base_url + "manga", params={"page": page_offset + page})
        except:
            print("Erreur : {}".format(req.status_code))
            continue
        
        print("adding entries from page {}...".format(page))
        print("Has next page ? : {}".format(req.json()['pagination']['has_next_page']))
        print()
        entries = update_manga_entries(req, entries)

        if ((page_limit is not None) and (page >= page_limit)) or not (req.json()['pagination']['has_next_page']):
            next_page = False
        page += 1

    manga_df = pd.DataFrame(entries)
    print(manga_df)
    manga_df.to_csv(output_path,index=False, encoding='utf-8')

if __name__=="__main__":
    create_manga_database()