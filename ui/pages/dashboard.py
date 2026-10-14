import requests
from shiny import Inputs, Outputs, Session, render, ui

from ui.pages.config import *


def page_ui():
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_select(
                "filter_gender",
                "Filter gender",
                {"None" : "None", "Male" : "Male", "Female" : "Female", "Non-Binary" : "Non-Binary"},
            ),
            ui.input_slider("filter_birthday","Filter Birthday Year",min=1960,max=2020, value=[1990,2008],drag_range=False),#TODO : replace with current year
            ui.input_switch("apply_birthday_filter", "Use Birthday filter ?", False),
            ui.input_slider("filter_entries","Filter number of entries",min=1,max=2000, value=[0,2000],drag_range=False),#TODO : replace with current year
            ui.input_switch("apply_entries_filter", "Use Entries filter ?", False),
        ),
        ui.h2("Dashboard"),
        ui.layout_columns(
            ui.value_box("Users", ui.output_ui("user_display"), showcase=ICONS["user"]),
            ui.value_box("Entries", ui.output_ui("entries_display"), showcase=ICONS["book"]),
        ),
    )

def server(input: Inputs, output: Outputs, session: Session):

    def fetch_count(endpoint, gender=None, birthday_bounds=None, entries_bounds=None):
        url = param["API_URL"]+f"/{endpoint}?counting=True"

        if gender != "None":
            url += f"&gender={gender}"

        #require variables [min, max]
        if birthday_bounds:
            url+=f"&min_birthday={birthday_bounds[0]}&max_birthday={birthday_bounds[1]}"
        if entries_bounds:
            url+=f"&min_entries={entries_bounds[0]}&max_entries={entries_bounds[1]}"

        response = requests.get(url)
        data = response.json()
        return data['data']

    @render.ui
    def user_display():
        birthday_bounds = input.filter_birthday() if input.apply_birthday_filter() else None
        entries_bounds = input.filter_entries() if input.apply_entries_filter() else None
        return fetch_count("users", gender=input.filter_gender(), birthday_bounds=birthday_bounds, entries_bounds=entries_bounds)


    @render.ui
    def entries_display():
        birthday_bounds = input.filter_birthday() if input.apply_birthday_filter() else None
        entries_bounds = input.filter_entries() if input.apply_entries_filter() else None
        return fetch_count("entries", gender=input.filter_gender(), birthday_bounds=birthday_bounds, entries_bounds=entries_bounds)
