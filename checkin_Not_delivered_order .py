import sqlite3
import random
from datetime import datetime, timedelta
import string
import re

DB_PATH = 'example.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT * FROM orders WHERE tenant_id =='u1'")

rows = cursor.fetchall()
print("code is working")
for row in rows:
    print(row)
