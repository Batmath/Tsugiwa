
import pandas as pd
from ui.pages.config import *

filter_option_target = {"Reading Status" : ["status"], "Media Type" : ["manga", "media_type"], "Publication Status" : ["manga", "publishing"], "Demography" : ["manga", "demographics"]}

def search_genre_count_entries(df):
    genres = {}
    for row_dict in df.to_dict(orient="records"):
        for genre in row_dict['manga']['genres']:

            genre_name = genre['genre']
            genres[genre_name] = genres.get(genre_name, 0) + 1

    genres = dict(sorted(genres.items(), key=lambda item: item[1]))

    return genres

def search_filter_count_entries(df, filter_option="Genres"):
    if filter_option=="Genres":
        return search_genre_count_entries(df)
    else :
        res = {}
        d = filter_option_target[filter_option] 
        
        for row_dict in df.to_dict(orient="records"):
            
            targets = row_dict
            for path in d:
                targets = targets[path]

            if targets is None:
                continue

            if type(targets) == str:
                targets = targets.split(",") #Some have 2 demography separated by commas. 
                for target in targets:
                    res[target] = res.get(target, 0) + 1
            
            if type(targets) == int:
                if filter_option == "Publication Status":
                    target_str = "Publishing" if targets else "Publication finished"
                    res[target_str] = res.get(target_str, 0) + 1
                else:
                    res[target_str] = res.get(target_str, 0) + 1 #Correspond to nothing but avoid failing silently

        sorted_res = dict(sorted(res.items(), key=lambda item: item[1]))
        return res

def filter_entries_genre(df, genre=None):
    if genre is None or genre =="None":
        return df
    if genre not in GENRES_DICT:
        raise KeyError(f"[filter_entries_genre] '{genre}' is not part of the list of genres.")

    res = []
    for row_dict in df.to_dict(orient="records"):
        list_genres = list(map(lambda x : x['genre'], row_dict["manga"]["genres"]))
        if genre in list_genres:
            res.append(row_dict)
    return pd.DataFrame(res)

def get_genres_entries(df):
    genres = set()
    for row_dict in df.to_dict(orient="records"):
        for genre in row_dict['manga']['genres']:
            genre_name = genre['genre']
            if genre_name not in genres:
                genres.add(genre_name)
    return list(genres)

def search_manga_count_entries(df):
    categories = {}
    for row_dict in df.to_dict(orient="records"):
        category_name = row_dict['status']
        categories[category_name] = categories.get(category_name, 0) + 1

    categories = dict(sorted(categories.items(), key=lambda item: item[1]))
    return categories