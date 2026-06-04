from shiny import ui, Inputs, Outputs, Session, reactive, render
from .config import * 
import pandas as pd
import plotly.graph_objects as go
from .plotly_streaming import render_plotly_streaming
from shinywidgets import render_widget, output_widget

# TODO: search a better way to make the search query (Or create my own Shiny widget !)
# TODO : Graph for reading/completed/on-hold manga
# TODO : Graph for note per genra
# TODO : List of entries
def page_ui():
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_text("search_query", "Search for a user", placeholder="Search for a username"), 
            ui.output_data_frame("searched_user")),
        ui.card(
            ui.card_header("Genres pie chart"),
            output_widget("plot_camembert"),
            full_screen=True,  
            height="350px", 
        ),
        
    )

def server(input: Inputs, output: Outputs, session: Session):

    @render.data_frame
    def searched_user():
        user_df = username_search()
        return render.DataGrid(user_df, selection_mode="row")

    @reactive.calc
    def username_search():
        q = input.search_query()
        if not q or len(q) < 2:
            return pd.DataFrame([], columns=["Usernames found"])
        response = requests.get(API_URL + "/users/search?q={}&limit=10".format(q))
        print(q)
        print(API_URL + "/users/search?q={}&limit=10".format(q))
        user_df = pd.DataFrame(response.json()['data'], columns=["Usernames found"])
        print(response.json()['data'])
        print(user_df)
        return user_df
    
    @reactive.calc
    def compute_user_data():
        rows = searched_user.cell_selection()["rows"]
        row = rows[0] if rows else None #For now, either the first one selected or none.

        if row is None :
            return None
        df = username_search()
        exact_username = df.iloc[row]["Usernames found"]
        return exact_username
    
    @output
    @render_widget
    def plot_camembert():
        def search_genre_entries(genre_id, df):
            cpt = 0
            for row_dict in df.to_dict(orient="records"):
                for genre in row_dict['manga']['genres']:
                    if genre_id == genre['genre_id']:
                        cpt +=1
            return cpt

        user = compute_user_data()
        if not user :
            fig = go.Figure()
            fig.update_layout(
                width=800,
                height=600,
            )
            return go.Figure()
        else:
            req = API_URL + "/users/{}/entries/full".format(user)
            print(req)
            response = requests.get(req)
            df = pd.DataFrame(response.json()['data'])
            print(df)

            genre_ids = list(GENRES_DICT.keys())
            genres_to_plot = []
            cpt_genres = []
            for id in genre_ids:
                n_entry_genre = search_genre_entries(id,df)
                if n_entry_genre > 0:
                    genres_to_plot.append(id)
                    cpt_genres.append(n_entry_genre)
            genres_to_plot = list(map(lambda x : GENRES_DICT[x], genres_to_plot))
            print(cpt_genres)
            pie_colors = [GENRE_COLORS.get(genre, "#CCCCCC") for genre in genres_to_plot]

            fig = go.FigureWidget(data=[
                go.Pie(
                    labels=genres_to_plot, 
                    values=cpt_genres, 
                    hole=.3,
                    textinfo='none',
                    marker=dict(colors=pie_colors)
                )
            ])

            fig.update_layout(
                margin=dict(t=20, b=20, l=20, r=20)
            )
            print("Done")
        return fig

    pass