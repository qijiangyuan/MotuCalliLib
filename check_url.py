
import sqlite3
conn = sqlite3.connect("data/shufadb.db")
row = conn.execute("SELECT url FROM images LIMIT 1").fetchone()
if row:
    print(row[0])
else:
    print("No images found")
conn.close()
