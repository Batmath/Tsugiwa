from shiny import App, ui, render
from ui.pages import dashboard, users, entries, manga
from ui.pages.config import param
import subprocess

# shiny run ./ui/app.py --port 7950 --reload
# TODO : Ajouter
app_ui = ui.page_navbar(
    ui.nav_panel("Dashboard", dashboard.page_ui()),
    ui.nav_panel("Users", users.page_ui()),
    ui.nav_panel("Entries", entries.page_ui()),
    ui.nav_panel("Manga", manga.page_ui()),
    ui.nav_control(ui.input_dark_mode()), 
    title="次は",
)

def server(input, output, session):
    dashboard.server(input, output, session)
    users.server(input, output, session)
    entries.server(input, output, session)
    manga.server(input, output, session)

app = App(app_ui, server)

if __name__ == "__main__":
    subprocess.run(["shiny", "run", "ui.app:app", "--app-dir", ".", "--host", param["HOST_IP_ADDRESS"], "--port", str(param["UI_PORT"]),"--reload",])