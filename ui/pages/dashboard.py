from shiny import ui, Inputs, Outputs, Session

def page_ui():
    return ui.div(
        ui.h2("Dashboard"),
        ui.p("General stats. (Place Holder !)")
    )

def server(input: Inputs, output: Outputs, session: Session):
    pass