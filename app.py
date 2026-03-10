'''
Create the web app.
'''

from shiny import App

from src_app.layout import app_ui
from src_app.app_server import server

app = App(app_ui, server)

