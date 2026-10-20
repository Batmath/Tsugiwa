import pandas as pd
from shiny import Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import output_widget, render_widget

from ui.api.client import *
from ui.data.transform import *
from ui.pages.config import *
from ui.plots.figure import *


def page_ui():
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_text("search_manga_query", "Search manga"),
            ui.input_select("selected_manga", "Matches", choices=[], size=8, selectize=False)
        ),
        ui.layout_columns(
            ui.card(
                ui.div(output_widget("plot_manga"), style="display:flex; justify-content:center;"),
            ),
            ui.card(
                ui.card_header("Count Entries"),
                ui.value_box("Number of user with the entry :", ui.output_ui("user_manga_display"), showcase=ICONS["user"]),
                ui.value_box("Number of rated entries :", ui.output_ui("entries_manga_display"), showcase=ICONS["book"])
            ),
        ),
        ui.card(
            ui.card_header("Distribution Manga Pie Chart"),
            output_widget("plot_manga_camembert"),
            full_screen=True,
        ),
        ui.card(
            output_widget("plot_score_hist"),
        )
)

def server(input: Inputs, output: Outputs, session: Session):

    list_potential_manga = reactive.value(None)
    manga_id = reactive.value(None)
    manga_data = reactive.value(None)

    @reactive.calc
    def manga_search():
        q = input.search_manga_query()
        if not q or len(q) < 2:
            return []
        return query_api(f"{param["API_URL"]}/mangas/search?q={q}&limit={15}")

    @reactive.effect
    def update_manga_choices():
        res = manga_search()
        list_manga = [x['title'] for x in res]
        list_potential_manga.set({manga['title'] : manga['manga_id'] for manga in res})
        ui.update_select("selected_manga", choices=list_manga)

    @reactive.calc
    def compute_manga_data():
        manga = input.selected_manga()
        if manga is not None:
            try:
                manga_id.set(list_potential_manga()[f'{manga}'])
            except KeyError:
                return None
            manga_data.set(query_api(f"{param["API_URL"]}/mangas/{manga_id()}")[0]) # returns the row associated with the manga id so we take the only element in data [{..}]
            manga_df = pd.DataFrame(get_manga_entries(manga_id()))
            return manga_df
        return None

    @output
    @render_widget
    def plot_manga():
        manga = compute_manga_data()
        if manga is None:
            return ImagePlot(0,0).figure()
        else:
            url = manga_data()['url_img']
            return ImagePlot(width=400, height=650, scale_factor=0.7, source=url).figure()

    @render.ui
    def user_manga_display():
        if manga_id() is not None:
            count = query_api(f"{param["API_URL"]}/users/?manga_id={manga_id()}&counting=true")
            return count
        return None

    @render.ui
    def entries_manga_display():
        if manga_id() is not None:
            count = query_api(f"{param["API_URL"]}/entries/manga/{manga_id()}/?counting=true&min_score=1")
            return count
        return None

    @output
    @render_widget
    def plot_manga_camembert():
        manga = compute_manga_data()
        if manga is None:
            return ScatterPlot().figure()
        else:
            plot_vars = search_manga_count_entries(manga)
            labels = list(plot_vars.keys())
            vals = list(plot_vars.values())
            fig =  PiePlot(vals, labels, max_visible=10).figure()
            return fig

    @output
    @render_widget
    def plot_score_hist():
        manga = compute_manga_data()
        if manga is None:
            return ImagePlot(0,0).figure()
        else:
            manga = manga[manga['score'].notna()]

            #user = filter_entries_genre(user, genre=input.hist_genre_filter())
            data = []
            for row_dict in manga.to_dict(orient="records"):
                if row_dict['score'] is not None:
                    data.append(row_dict['score'])

            fig = HistoPlot(x=data, nbins=10, hovertemplate="Score %{x:.0f}<br>%{y} entries<extra></extra>").figure()

            mean = manga_data()['mean_score']
            if mean is not None:
                fig.add_vline(x=mean, line={"color": "red", "width": 2}, annotation_text=f"Mean {mean:.2f}", annotation_position="top")
            return fig
