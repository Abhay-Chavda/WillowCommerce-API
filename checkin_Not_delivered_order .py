import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

if os.path.exists(".env"):
    load_dotenv()

DATABASE_URL = os.environ["EXTERNAL_DATABASE_URL"]

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cursor = conn.cursor()

cursor.execute("""
               UPDATE orders SET status = 'DELIVERED' WHERE status = 'REFUND_INITIATED' OR status = 'REPLACEMENT_INITIATED'; """)

conn.commit()
cursor.execute("""
    SELECT *
    FROM orders WHERE status = 'DELIVERED'""")

rows = cursor.fetchall()

print("Query executed successfully")

if not rows:
    print("No records found")

for row in rows:
    print(row)

conn.close()