import sqlite3

DB_PATH = 'example.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Update records
cursor.execute("SELECT * FROM labels")

rows = cursor.fetchall()

print("Code is working")
if not rows:
    print("No records found")

for row in rows:
    print(row)

conn.close()
