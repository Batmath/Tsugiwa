from shiny import ui, Inputs, Outputs, Session

def page_ui():
    return ui.div(
        ui.h2("Manga"),
        ui.p("Search for a manga to view its entries and users. (Place Holder !)")
    )

def server(input: Inputs, output: Outputs, session: Session):
    pass