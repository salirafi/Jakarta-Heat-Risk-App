import sqlite3

conn = sqlite3.connect("heat_risk.db")

with open("heat_risk.sql", "w") as f:
    for line in conn.iterdump():
        f.write(f"{line}\n")

conn.close()