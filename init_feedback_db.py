
import sqlite3
import os

FEEDBACK_DB_PATH = os.path.join("data", "feedback.db")

def init_db():
    # 确保data目录存在
    if not os.path.exists("data"):
        os.makedirs("data")
        
    conn = sqlite3.connect(FEEDBACK_DB_PATH)
    c = conn.cursor()
    
    # 创建反馈表
    # status: pending (待处理), resolved (已处理/已删除), ignored (已忽略)
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            glyph_id INTEGER,
            image_id INTEGER,
            han TEXT,
            font TEXT,
            author TEXT,
            book_title TEXT,
            image_url TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Feedback database initialized at {FEEDBACK_DB_PATH}")

if __name__ == "__main__":
    init_db()
