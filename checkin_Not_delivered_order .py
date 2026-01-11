import sqlite3

DB_PATH = 'example.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Update records
cursor.execute("""
    UPDATE orders
    SET status = 'DELIVERED'
    WHERE status = 'REPLACEMENT INITIATED'
""")

# Commit changes
conn.commit()

# Fetch updated records
cursor.execute("""
    SELECT * FROM orders
    WHERE tenant_id = "u1" AND status = 'DELIVERED'
""")

rows = cursor.fetchall()

print("Code is working")
for row in rows:
    print(row)

conn.close()
