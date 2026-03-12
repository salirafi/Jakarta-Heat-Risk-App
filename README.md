# Jakarta Heat Risk App

This repository contains the source code to build a Python-based web application with Shiny for Python which is intended to show information about heat index and risk for every single ward (kelurahan) in the Jakarta province. The weather forecast data which includes temperature, humidity, sky condition, and wind speed and direction are available for each ward and are provided by Badan Meteorologi, Klimatologi, dan Geofisika (BMKG) through public API described in [Data Terbuka BMKG](https://data.bmkg.go.id/prakiraan-cuaca/). **The data is 3-hourly.**

To interact with the app without going through difficulty installing anything, please go to my [HuggingFace space](https://huggingface.co/spaces/salirafi/Jakarta-Heat-Risk-App).

## Running

This code can be run with `python3.11`. Before running the code, make sure all prerequisites are installed. Run in the terminal
```
pip install -r requirements.txt
```
It is recommended to work on virtual environment to isolate project dependencies.

First, run
```
python3 .\tables\create_db.py
```
to create SQLite database file `heat_risk.db` in `tables` folder. 

Then, if the user wants up-to-date weather data, in the parent folder, run
```
python3 .\fetch\fetch_weather_data.py
```
or, if the user uses Windows, alternatively type in terminal
```
fetch_weather_data.bat
```
or simply double-click it to run the script through .bat file. This might run for around 4 to 5 minutes (see Content section).

Finally, run
```
shiny run app.py
```
to connect to the web app. 

## Notes

Please note that the web app shows the weather forecast from roughly the user's current system time up to 1 day (by default) to the future whenever data is available. If the database is not up-to-date (the database time coverage does not cover the current Jakarta time), then the app pops out a blocker notification prompting the user to update the database.

If the user wants to run [fetch_boundary_data.py](src/fetch_boundary_data.py), make sure they have downloaded the required .gdb file from [here](https://geoservices.big.go.id/portal/apps/webappviewer/index.html?id=cb58db080712468cb4bfd408dbde3d70).

⚠️ **IMPORTANT!** ⚠️  This app is a personal project, so the code might not be optimized for smoother user's experience. For first time loading, the web might take a few seconds.

## Content

This project depends heavily on [pandas](https://pandas.pydata.org/), with data managed in [SQLite](https://sqlite.org/) environment, though no SQLite broswer needs to be installed since all interface is done with Python.

[fetch](fetch) contains source code for fetching BMKG data ([fetch_weather_data.py](fetch/fetch_weather_data.py)), retrieving region code from [public API](https://wilayah.id/api) ([build_jakarta_preference.py](fetch/build_jakarta_preference.py)), and reading the boundary polygons from RBI data provided by Badan Informasi Geospasial ([fetch_boundary_data.py](fetch/fetch_boundary_data.py)). The first and last file create SQLite tables with names `ward_weather_table` and `ward_boundary_table` (and a GeoJSON), respectively, whilst the region code is saved as `jakarta_preference.csv`. Note that the only time-dependent data in this repository is the BMKG weather data, so the boundary polygon and region code will always be valid.

[tables](tables) contains SQLite table for boundary polygon and weather data in `heat_risk.db`. The weather data time coverage spans from March 11 2026 20:00 WIB to March 13 2026 20:00 WIB. User can update, or more precisely append, this data by simply running [fetch_weather_data.py](fetch/fetch_weather_data.py) which will append the table with weather data from the user's current time to three days in the future. If there is overlap, the code will replace the old rows (with the same region code and time stamp). Each run will take up about 4 minutes due to polite delay of 1.01 seconds for each of 261 wards in Jakarta to respect BMKG request limit of 60 requests / minute / IP. The file also contains `create_db.py` to create a SQLite database named `heat_risk.db`. There is also a GeoJSON data stored for Choropleth plot.

[src](src) contains the source code for creating the web app, making use of [Shiny for Python](https://shiny.posit.co/py/).

The parent folder contains [app.py](app.py), script to run the web app.


## Author's Remarks

This project was inspired by the tropical condition of Jakarta. Average daytime temperature for downtown Jakarta of about $32\degree$ Celcius ([measurements from 1991 to 2000](https://web.archive.org/web/20231019195817/https://www.nodc.noaa.gov/archive/arc0216/0253808/1.1/data/0-data/Region-5-WMO-Normals-9120/Indonesia/CSV/StasiunMeteorologiKemayoran_96745.csv)) and at a fairly consistent value throughout the year makes its population susceptible to some level of heat risks. This is worsen by the climate change that is getting severe for the past several years, with multiple heat waves reported across the globe (see [here](https://wmo.int/news/media-centre/rising-temperatures-and-extreme-weather-hit-asia-hard) for example). Based on the [U.S. National Weather Service](https://www.weather.gov/ama/heatindex#:~:text=Table_title:%20What%20is%20the%20heat%20index?%20Table_content:,the%20body:%20Heat%20stroke%20highly%20likely%20%7C), temperatures just above $32\degree$ Celcius can start to induce some negative effects on human body such as heat exhaustion, heat cramps, and even heat stroke from prolonged exposure. With many Jakartans working outside, for example as *ojol*, street vendors, or just being stuck in traffic under the scorching sunlight, the risk of these complications may be even greater than realized. 

However, as someone who lived in Jakarta for over 20 years, the government's effort to spread awareness to this ever-urgent problem seems to be in the minimum. It is very hard to get a grasp towards understanding how dangerous it actually is to walk, commute, or work under direct exposure of sunlight for an extended amount of time in Jakarta, simply because the lack of public awareness or outreach campaign about heat risk from the government that you can easily see on the streets or even internet, this at least as far as my experience. After all, even if there was aggressive heat risk campaign, if I am working as an *ojol* for example, what can I do? Sometimes, for most poeple, it is not about whether you are aware about it or not, but rather about whether you have the choice to avoid it or not.

Recognizing these realities, the first step we can do is to simply provide people with accessible information about heat risk in their daily environment. Making a simple tool that indicates the level of heat risk at a given time and location will allow people to better understand when conditions become dangerous. Although such information cannot, perhaps, eliminate the constraints faced by many workers like I mentioned, it can still help them, and of course myself, make small but meaningful adjustments to our precious daily lives :)
