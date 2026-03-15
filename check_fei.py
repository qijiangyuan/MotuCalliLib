
import sqlite3

try:
    conn = sqlite3.connect('data/shufadb.db')
    cursor = conn.execute("""
        SELECT g.id, g.han, b.title 
        FROM glyphs g 
        JOIN books b ON g.book_id = b.id 
        JOIN authors a ON g.author_id = a.id
        WHERE g.han = '飞' 
        AND a.name = '钟绍京'
        AND b.title LIKE '%灵飞经%'
    """)
    rows = cursor.fetchall()
    
    print(f"Total '飞' (钟绍京/灵飞经): {len(rows)}")
    for row in rows:
        print(f"Glyph ID: {row[0]}, Han: {row[1]}, Book: {row[2]}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
