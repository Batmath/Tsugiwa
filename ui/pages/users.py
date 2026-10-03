from ui.pages.config import * 
from shiny import ui, Inputs, Outputs, Session, reactive, render
import pandas as pd

from shinywidgets import render_widget, output_widget
import numpy as np

from ui.api.client import *
from ui.plots.figure import *
from ui.data.transform import *

# TODO : Graph for reading/completed/on-hold manga
# TODO : Graph for note per genra
# TODO : List of entries
# TODO : Scatter plot, mean_score vs user score (comparing how the user is rating vs how people are rating (if there is such a thing.))
# TODO : Add palette to each pie filter : Media Genres, Reading Status, Media Type, Publication Status, Demography
# TODO : [plot_scatter] Add lines and corresponding areas (Rated similarly, Favoured by the user, Hated by the user).  
#(x + 10% max_score score -> Rated Similarly, x + 30% max_score -> Favoured/Hated by the user, x + >30% max_score score -> Strongly hated/favoured by the user)
# TODO : [plot_scatter & plot_camembert] Find ways to resize plots
# TODO : [scatter_plot_card] Add color filters according to filters chosen (+ DEFINE filters)
# TODO : Distribution graph overall (for number of entries per user/number )

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
            ui.card_header("Scatter Plot mean score/user score",),
            output_widget("plot_scatter"),
            full_screen=True,
        ),

        ui.card(
            ui.card_header("Score Distribution",),
            output_widget("plot_histogram"),
            full_screen=True,
        ),
    )

def server(input: Inputs, output: Outputs, session: Session):

    @reactive.calc
    def username_search():
        q = input.search_query()
        if not q or len(q) < 2:
            return []
        return search_username(q)

    @reactive.effect
    def update_user_choices():
        ui.update_select("selected_user", choices=username_search())

    @reactive.calc
    def compute_user_data():
        return input.selected_user() or None
    
    @output
    @render_widget
    def plot_camembert():
        user = compute_user_data()
        if not user :
            return ScatterPlot().figure()
        else:
            df = pd.DataFrame(get_user_entries(user))
            plot_vars = search_filter_count_entries(df, filter_option=input.pie_filter())
            labels = list(plot_vars.keys())
            vals = list(plot_vars.values())
            return PiePlot(vals, labels, max_visible=10).figure()
    
    @output
    @render_widget
    def plot_scatter():
        user = compute_user_data()
        if not user :
            return ScatterPlot().figure()
        else:
            df = pd.DataFrame(get_user_entries(user))
            df = df[df['score'].notna()]
            data = {'title' : [], 'y' : [], 'x' : []}

            for row_dict in df.to_dict(orient="records"):
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

            fig.update_xaxes(range=[-0.2, max_score + 0.2], fixedrange=True)
            fig.update_yaxes(range=[-0.2, max_score + 0.2], fixedrange=True)
            return fig

    
    pass

""""""

"""min_entry = np.min(data['entry_score'])
            min_manga = int(np.floor(np.min(data['manga_score'])))

            print("entry : {}, manga : {}".format(min_entry, min_manga))
            min_val = int(min(min_entry, min_manga))

            max_entry = np.max_score(data['entry_score'])
            max_manga = int(np.ceil(np.max_score(data['manga_score'])))
            print("entry : {}, manga : {}".format(max_entry, max_manga))

            max_val = int(max_score(max_entry, max_manga))

            fig.add_trace(go.Scatter(
                x=[i for i in range(min_val, max_val+1)], y=[i for i in range(min_val, max_val+1)],
                mode='lines',
                line=dict(width=0.5, color='rgb(184, 247, 212)'),
                name='Ideal',
                stackgroup='one',
            ))"""
