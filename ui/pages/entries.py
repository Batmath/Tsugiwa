from shiny import ui, Inputs, Outputs, Session

def page_ui():
    return ui.div(
        ui.h2("Entries"),
        ui.p("Paginated entries table will go here. (Place Holder !)")
    )

def server(input: Inputs, output: Outputs, session: Session):
    pass