from ui.pages.config import * 
from shiny import ui, Inputs, Outputs, Session, reactive, render
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from shinywidgets import render_widget, output_widget
import numpy as np

# TODO: search a better way to make the search query (Or create my own Shiny widget !)
# TODO : Graph for reading/completed/on-hold manga
# TODO : Graph for note per genra
# TODO : List of entries
# TODO : Scatter plot, mean_score vs user score (comparing how the user is rating vs how people are rating (if there is such a thing.))
# TODO : Add palette to each pie filter : Media Genres, Reading Status, Media Type, Publication Status, Demography
# TODO : [plot_scatter] Add lines and corresponding areas (Rated similarly, Favoured by the user, Hated by the user).  
#(x + 10% max score -> Rated Similarly, x + 30% max_score -> Favoured/Hated by the user, x + >30% max score -> Strongly hated/favoured by the user)
# TODO : [plot_scatter & plot_camembert] Find ways to resize plots
# TODO : [scatter_plot_card] Add color filters according to filters chosen (+ DEFINE filters)
# TODO : Distribution graph overall (for number of entries per user/number )

def page_ui():
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_text("search_query", "Search for a user", placeholder="Search for a username"), 
            ui.output_data_frame("searched_user")),
        ui.card(
            ui.card_header(
                "Distribution Pie Chart",
                ui.toolbar(
                    ui.toolbar_input_select(
                        id="pie_filter",
                        label="Filtre",
                        choices=["Genres", "Reading Status", "Media Type", "Publication Status", "Demography"],
                        selected="Genres"
                    )
                )
            ),
            output_widget("plot_camembert"),
            full_screen=True,
        ),
        
        
        ui.card(
             ui.card_header(
                "Scatter Plot mean score/user score",
            ),
            output_widget("plot_scatter"),
            full_screen=True,
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
        response = requests.get(param["API_URL"] + "/users/search?q={}&limit=10".format(q))
        user_df = pd.DataFrame(response.json()['data'], columns=["Usernames found"])
        print(response.json()['data'])
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
                filter_option_target = {"Reading Status" : ["status"], "Media Type" : ["manga", "media_type"], "Publication Status" : ["manga", "publishing"], "Demography" : ["manga", "demographics"]}
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

        user = compute_user_data()
        if not user :
            fig = go.Figure()
            return fig
        else:
            req = param["API_URL"] + "/entries/user/{}/full".format(user)
            response = requests.get(req)
            df = pd.DataFrame(response.json()['data'])

            plot_vars = search_filter_count_entries(df, filter_option=input.pie_filter())
            labels = list(plot_vars.keys())
            vals = list(plot_vars.values())

            nb_labels = len(labels)
            label_hide=None
            if nb_labels >= 11:
                label_hide = labels[:nb_labels-10]
            

            fig = go.FigureWidget(data=[
                go.Pie(
                    labels=labels, 
                    values=vals, 
                    hole=.3,
                    textinfo='none'
                )
            ])

            fig.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                hiddenlabels=label_hide
            )
            
            return fig
    
    @output
    @render_widget
    def plot_scatter():
        user = compute_user_data()
        if not user :
            fig = go.Figure()
            return go.Figure()
        else:
            req = param["API_URL"] + "/entries/user/{}/full".format(user)
            print(req)
            response = requests.get(req)
            df = pd.DataFrame(response.json()['data'])
            df = df[df['score'].notna()]

            data = {'manga_title' : [], 'entry_score' : [], 'manga_score' : []}

            for row_dict in df.to_dict(orient="records"):
                if row_dict['manga']['score'] is not None:
                    data['manga_title'].append(row_dict['manga']['title'])
                    data['entry_score'].append(row_dict['score'])
                    data['manga_score'].append(row_dict['manga']['score'])

            fig = px.scatter(data, x='manga_score', y='entry_score', hover_data=['manga_title'],
                labels=dict(manga_score="Manga Score (mean across users)", entry_score="User Manga Score")
            )
            
            
            """min_entry = np.min(data['entry_score'])
            min_manga = int(np.floor(np.min(data['manga_score'])))

            print("entry : {}, manga : {}".format(min_entry, min_manga))
            min_val = int(min(min_entry, min_manga))

            max_entry = np.max(data['entry_score'])
            max_manga = int(np.ceil(np.max(data['manga_score'])))
            print("entry : {}, manga : {}".format(max_entry, max_manga))

            max_val = int(max(max_entry, max_manga))

            fig.add_trace(go.Scatter(
                x=[i for i in range(min_val, max_val+1)], y=[i for i in range(min_val, max_val+1)],
                mode='lines',
                line=dict(width=0.5, color='rgb(184, 247, 212)'),
                name='Ideal',
                stackgroup='one',
            ))"""

            return fig
    pass