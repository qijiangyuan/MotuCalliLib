
import requests
import sqlite3
import os
import json

# 1. Stop the current process
try:
    print("Stopping current process...")
    resp = requests.post("http://127.0.0.1:5001/api/stop")
    print(resp.json())
except Exception as e:
    print(f"Could not stop process (maybe not running): {e}")

# 2. Reset checkpoint
print("Resetting checkpoint...")
checkpoint_file = os.path.join("data", "checker_checkpoint.json")
if os.path.exists(checkpoint_file):
    os.remove(checkpoint_file)
    print("Checkpoint file deleted.")

# 3. Clear feedback database (reports table)
print("Clearing old feedback reports...")
feedback_db = os.path.join("data", "feedback.db")
conn = sqlite3.connect(feedback_db)
conn.execute("DELETE FROM reports")
conn.commit()
conn.close()
print("Reports table cleared.")

print("Ready to restart from scratch.")
