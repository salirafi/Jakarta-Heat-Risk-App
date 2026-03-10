'''
Create the web app.
'''
  
from shiny import App
from app.ui.layout import app_ui
from app.ui.app_server import server

app = App(app_ui, server)

