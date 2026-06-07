from shiny import ui, Inputs, Outputs, Session, reactive, render
from .config import * 
import pandas as pd
import plotly.graph_objects as go
from shinywidgets import render_widget, output_widget

# TODO: search a better way to make the search query (Or create my own Shiny widget !)
# TODO : Graph for reading/completed/on-hold manga
# TODO : Graph for note per genra
# TODO : List of entries

# Add different types of graphs : PERCENTAGE, Notes etc. And then filter options to choose how to display these informations (Per genres, per status, per media_type..)
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
            print("Done")
        return fig

    pass