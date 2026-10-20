import pandas as pd
from shiny import Inputs, Outputs, Session, reactive, ui
from shinywidgets import output_widget, render_widget

from ui.api.client import *
from ui.data.transform import *
from ui.pages.config import *
from ui.pages.config import GENRE_COLORS
from ui.plots.figure import *

# TODO : List of entries
# TODO : [scatter_plot_card] Add color filters according to filters chosen
# TODO : Fix hover for histogram (have the value instead of a range which means nothing.)

def page_ui():
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_text("search_query", "Search username"),
            ui.input_select("selected_user", "Matches", choices=[], size=8, selectize=False)
        ),
        ui.card(
            ui.card_header(
                "Distribution Pie Chart",
                ui.toolbar(
                    ui.toolbar_input_select(id="pie_filter",label="Filtre",choices=["Genres", "Reading Status", "Media Type", "Publication Status", "Demography"],selected="Genres")
                )
            ),
            output_widget("plot_camembert"),
            full_screen=True,
        ),

        ui.card(
            ui.card_header("Scatter Plot mean score/user score"),
            output_widget("plot_scatter"),
            full_screen=True,
        ),

        ui.card(
            ui.card_header(
                "Score Distribution",
                ui.toolbar(
                    ui.toolbar_input_select(id="hist_genre_filter",label="Filtre",choices=["None"], selected=None)
                )
            ),
            output_widget("plot_histogram"),
            full_screen=True,
        ),

    )

def server(input: Inputs, output: Outputs, session: Session):

    user_df = reactive.value(None)

    @reactive.calc
    def username_search():
        q = input.search_query()
        if not q or len(q) < 2:
            return []
        return query_api(f"{param["API_URL"]}/users/search?q={q}&limit={15}")

    @reactive.effect
    def update_user_choices():
        ui.update_select("selected_user", choices=username_search())

    @reactive.effect
    @reactive.event(input.selected_user)
    def load_user():
        user = input.selected_user()
        if not user: 
            user_df.set(None)
            return
        df = pd.DataFrame(query_api(f"{param['API_URL']}/entries/user/{user}/full"))
        user_df.set(df if not df.empty else None)

    @reactive.effect
    def update_genre_choices():
        df = user_df()
        ui.update_select("hist_genre_filter", choices=["None"] + (get_genres_entries(df) if df is not None else []))

    @output
    @render_widget
    def plot_camembert():
        user = user_df()
        if user is None:
            return ScatterPlot().figure()
        else:
            plot_vars = search_filter_count_entries(user, filter_option=input.pie_filter())
            labels = list(plot_vars.keys())
            vals = list(plot_vars.values())
            color_map= GENRE_COLORS if input.pie_filter() == "Genres" else None
            fig =  PiePlot(vals, labels, max_visible=10, color_map=color_map).figure()
            if color_map is not None:
                fig.update_traces(marker={"colors": [GENRE_COLORS.get(l, "#888888") for l in labels]})
            return fig

    @output
    @render_widget
    def plot_scatter():
        user = user_df()
        if user is None:
            return ScatterPlot().figure()
        else:
            user = user[user['score'].notna()]
            data = {'title' : [], 'y' : [], 'x' : []}

            for row_dict in user.to_dict(orient="records"):
                if row_dict['manga']['score'] is not None:
                    data['title'].append(row_dict['manga']['title'])
                    data['x'].append(row_dict['score'])
                    data['y'].append(row_dict['manga']['score'])

            fig =  ScatterPlot(x=data['x'], y=data['y'], labelx="User ratings", labely="Manga score (mean)", hover_name="Manga Title",
                               hover=data['title'], title="User score vs mean score", xrange=[-0.2,10.2], yrange=[-0.2,10.2]).figure()
            max_score = 10
            threshold1, threshold2, outer_val = 0.1 * max_score, 0.3 * max_score, 3 * max_score

            zones = [
                (-outer_val,-threshold2,"rgba(0,150,60,0.25)"),# strongly favoured
                (-threshold2,-threshold1,"rgba(90,200,120,0.18)"),# favoured
                (-threshold1,threshold1,"rgba(160,160,160,0.15)"),# rated similarly
                (threshold1,threshold2,"rgba(255,150,50,0.18)"),# hated
                (threshold2,outer_val,"rgba(220,40,40,0.25)"),# strongly hated
            ]

            for low, upper, color in zones:
                path = (f"M {-max_score},{-max_score + low} L {2 * max_score},{2 * max_score + low} "
                        f"L {2 * max_score},{2 * max_score + upper} L {-max_score},{-max_score + upper} Z")
                fig.add_shape(type="path", path=path, fillcolor=color, line_width=0, layer="below")

            fig.update_xaxes(range=[-0.2, max_score + 0.2])
            fig.update_yaxes(range=[-0.2, max_score + 0.2])
            return fig

    @output
    @render_widget
    def plot_histogram():
        user = user_df()
        if user is None:
            return ScatterPlot().figure()
        else:
            user = user[user['score'].notna()]
            user = filter_entries_genre(user, genre=input.hist_genre_filter())
            data=[]

            for row_dict in user.to_dict(orient="records"):
                if row_dict['score'] is not None :
                    data.append(row_dict['score'])

            fig = HistoPlot(x=data, nbins=10, hovertemplate="Score %{x:.0f}<br>%{y} entries<extra></extra>").figure()
            return fig
