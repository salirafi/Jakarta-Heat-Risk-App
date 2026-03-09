```
Create the web app.
```

from shiny import App
from ui.layout import app_ui
from ui.app_server import server


app = App(app_ui, server)
