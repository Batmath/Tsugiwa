import subprocess

from shiny import App, ui

from ui.pages import dashboard, manga, users
from ui.pages.config import param

app_ui = ui.page_navbar(
            ui.nav_panel("Dashboard", dashboard.page_ui()),
            ui.nav_panel("Users", users.page_ui()),
            ui.nav_panel("Manga", manga.page_ui()),
            ui.nav_control(ui.input_dark_mode()),
            title="次は"
        )

def server(input, output, session):
    dashboard.server(input, output, session)
    users.server(input, output, session)
    manga.server(input, output, session)

app = App(app_ui, server)

if __name__ == "__main__":
    subprocess.run(["shiny", "run", "ui.app:app", "--app-dir", ".", "--host", param["HOST_IP_ADDRESS"], "--port", str(param["UI_PORT"]),"--reload",], check=True)