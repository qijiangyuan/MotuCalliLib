
import sqlite3
import os

db_path = os.path.join("data", "shufadb.db")
if not os.path.exists(db_path):
    print(f"Database {db_path} does not exist.")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]
        print(f"Tables in {db_path}: {table_names}")
        
        for table in table_names:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"Table '{table}' count: {count}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
