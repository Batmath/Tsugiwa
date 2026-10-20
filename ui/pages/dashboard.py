import requests
from shiny import Inputs, Outputs, Session, render, ui, reactive
from shinywidgets import output_widget, render_widget
import pandas as pd
import numpy as np

from ui.pages.config import *
from ui.plots.figure import *
from ui.api.client import *


def page_ui():
    return ui.page_fluid(
        ui.h2("Dashboard"),
        ui.layout_columns(
            ui.value_box("Users", ui.output_ui("user_display"), showcase=ICONS["user"]),
            ui.value_box("Entries", ui.output_ui("entries_display"), showcase=ICONS["book"]),
        ),
        ui.layout_columns(
            ui.card(ui.card_header("Gender distribution"), output_widget("plot_gender_pie")),
            ui.card(ui.card_header("Distribution of entries per user"), output_widget("plot_entries_hist")),
        ),
    )

def server(input: Inputs, output: Outputs, session: Session):

    GENDERS = ["Male", "Female", "Non-Binary"]
    COLS = ["gender", "entries"]
    N_BINS = 30
    limit = 2500

    def fetch_count(endpoint):
        response = requests.get(f"{param['API_URL']}/{endpoint}?counting=True", timeout=90)
        response.raise_for_status()
        return response.json()["data"]

    @reactive.calc
    def users_df():
        total = fetch_count("users")
        rows = []
        for offset in range(0, total, limit):
            response = requests.get(f"{param['API_URL']}/users/?limit={limit}&offset={offset}", timeout=90)
            response.raise_for_status()
            rows += response.json()["data"]
        return pd.DataFrame(rows, columns=COLS)

    @reactive.calc
    def entries_total():
        return fetch_count("entries")

    @render.ui
    def user_display():
        return len(users_df())

    @render.ui
    def entries_display():
        return entries_total()

    @render_widget
    def plot_gender_pie():
        counts = users_df()["gender"].value_counts().reindex(GENDERS, fill_value=0)
        return PiePlot(values=counts.tolist(), labels=GENDERS, max_visible=len(GENDERS)).figure()

    @render_widget
    def plot_entries_hist():
        entries = users_df()["entries"].dropna()
        end, size = 1, 1
        if not entries.empty:
            cap = max(float(entries.quantile(0.99)), 1.0)
            size = max(1, int(np.ceil(cap / N_BINS)))
            end = size * N_BINS
            entries = entries.clip(upper= end-1)

        fig = HistoPlot(x=entries.tolist(), xrange=(0, end), xlabel=f"Entries per user", ylabel="Users", 
                        hovertemplate="%{x} entries<br>%{y} users<extra></extra>").figure()
        fig.update_traces(xbins={"start": 0, "end": end, "size": size})
        fig.update_xaxes(range=[0, end], dtick=size * 5)  # one label every 5 bins, so the labels can't pile up
        return fig