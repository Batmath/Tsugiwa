from shiny import ui, Inputs, Outputs, Session

def page_ui():
    return ui.div(
        ui.h2("Users"),
        ui.p("Search for a user to view their info and entries. (Place Holder !)")
    )

def server(input: Inputs, output: Outputs, session: Session):
    pass