import json
from pathlib import Path

import faicons as fa

from ui import settings

ICONS = {
    "user": fa.icon_svg("user", "regular"),
    "book" : fa.icon_svg("book")
}

param = settings.ParametersUI().model_dump()

# TODO : refactor this garbage once the containers are set up
config_path = str(Path(__file__).parent.parent) + "/data/" + "genre_colors.json"

with open(config_path) as f:
    response = dict(json.load(f))

GENRE_COLORS = {value[1]['name'] : value[1]['color'] for key,value in enumerate(response.items())}
GENRES_DICT = {value[1]['name'] : value[0]  for key,value in enumerate(response.items())}
