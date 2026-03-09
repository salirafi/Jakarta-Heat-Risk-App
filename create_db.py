"""
To create .db file from two tables.
This is for example.
It is still useful to create .db file from either fetch_bmkg_data_jakarta.py or fetch_region_border_big_data_jakarta.py.
"""
import sqlite3
import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tables" / "heat_risk.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# list of SQL files and path
files = [BASE_DIR / "tables" / "heat_forecast_jakarta.sql", 
         BASE_DIR / "tables" / "jakarta_kelurahan_boundary.sql"]

for file in files:
    with open(file, "r") as f:
        cursor.executescript(f.read())

conn.commit()
conn.close()
