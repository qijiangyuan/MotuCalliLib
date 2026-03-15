
import sqlite3

try:
    conn = sqlite3.connect('data/shufadb.db')
    # 查找灵飞经中的“中”字
    cursor = conn.execute("""
        SELECT g.id, g.han, b.title 
        FROM glyphs g 
        JOIN books b ON g.book_id = b.id 
        WHERE g.han = '中' AND b.title LIKE '%灵飞经%'
    """)
    rows = cursor.fetchall()
    
    print(f"Total '中' in 灵飞经: {len(rows)}")
    for row in rows:
        print(f"Glyph ID: {row[0]}, Han: {row[1]}, Book: {row[2]}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
