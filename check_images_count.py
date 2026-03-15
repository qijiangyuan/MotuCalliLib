
import sqlite3

try:
    conn = sqlite3.connect('data/shufadb.db')
    cursor = conn.execute("SELECT COUNT(*) FROM images WHERE glyph_id=1019087")
    count = cursor.fetchone()[0]
    print(f"Images for glyph 1019087: {count}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
