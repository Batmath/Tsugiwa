from shiny import ui, Inputs, Outputs, Session, reactive, render
import faicons as fa
import requests

# shiny run ./ui/app.py --port 7950 --reload
# localurl API : http://localhost:8080

API_URL = "http://localhost:8080"

ICONS = {
    "user": fa.icon_svg("user", "regular"),
    "book" : fa.icon_svg("book")
}

def page_ui():
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_select(
                "filter_gender",
                "Filter gender",
                {"None" : "None", "Male" : "Male", "Female" : "Female", "Non-Binary" : "Non-Binary"},
            ),
        ),
        ui.h2("Dashboard"),
        ui.layout_columns(
            ui.value_box("Users", ui.output_ui("user_display"), showcase=ICONS["user"]),
            ui.value_box("Entries", ui.output_ui("entries_display"), showcase=ICONS["book"]),
        ),
    )

def server(input: Inputs, output: Outputs, session: Session):
    @render.ui
    def user_display():
        gender = input.filter_gender()
        url = API_URL+"/users?counting=True" 
        if gender != "None":
            url += "&gender={}".format(gender)
        
        response = requests.get(url)
        data = response.json()
        return data['data']
    
    @render.ui
    def entries_display():
        gender = input.filter_gender()
        url = API_URL+"/entries?counting=True" 
        if gender != "None":
            url += "&gender={}".format(gender)
        
        response = requests.get(url)
        data = response.json()
        return data['data']
    pass