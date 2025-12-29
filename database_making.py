import sqlite3
import random
from datetime import datetime, timedelta
import string
import re

DB_PATH = 'example.db'
random.seed(42)

USER_COUNT = 100
PRODUCT_COUNT = 50
ORDER_COUNT = 100  # also shipment count (1:1)

FIRST_NAMES = ["Abhay", "Ravi", "Aditi", "Neha", "Karan", "Priya", "Aman", "Sahil", "Meera", "Isha", "Arjun", "Vikram"]
LAST_NAMES  = ["Chavda", "Kumar", "Sharma", "Patel", "Singh", "Verma", "Gupta", "Mehta", "Joshi", "Rao", "Nair", "Das"]

CITIES = [
    ("Ahmedabad", "Gujarat", 380001),
    ("Surat", "Gujarat", 395003),
    ("Vadodara", "Gujarat", 390001),
    ("Jaipur", "Rajasthan", 302001),
    ("Udaipur", "Rajasthan", 313001),
    ("Delhi", "Delhi", 110001),
    ("Mumbai", "Maharashtra", 400001),
    ("Pune", "Maharashtra", 411001),
    ("Bengaluru", "Karnataka", 560001),
    ("Hyderabad", "Telangana", 500001),
    ("Chennai", "Tamil Nadu", 600001),
    ("Kolkata", "West Bengal", 700001),
]

PRODUCT_NAMES = [
    "Wireless Mouse", "Mechanical Keyboard", "Bluetooth Headphones", "USB-C Cable", "Power Bank",
    "Laptop Stand", "Smartwatch", "Phone Case", "Backpack", "Water Bottle",
    "Desk Lamp", "Webcam", "External SSD", "HDMI Adapter", "Gaming Chair",
    "Notebook", "Pen Set", "Portable Speaker", "Monitor", "Router"
]

ORDER_STATUSES = ["Placed", "Processing", "Shipped", "In Transit", "Out for Delivery", "Delivered"]

def rand_phone_int():

    start = random.choice([6, 7, 8, 9])
    rest = random.randint(10**8, 10**9 - 1)  
    return int(f"{start}{rest:09d}")

def rand_tracking_number(length=10):
    letters = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TRK-{datetime.now().strftime('%Y%m%d')}-{letters}"

def rand_date_within_last(days = 120):
    d = datetime.now() - timedelta(days=random.randint(0, days))
    return d.strftime("%Y-%m-%d")


def rand_date_within_next(days = 7, last_date: str | None = None):
    if last_date is None:
        start_date = datetime.now()
    else:
        start_date = datetime.strptime(last_date, "%Y-%m-%d")
    d = start_date + timedelta(days=random.randint(2, days))
    return d.strftime("%Y-%m-%d")

def pick_status():
    r = random.random()
    if r < 0.1:
        return "PLACED"
    elif r < 0.3:
        return "PROCESSING"
    elif r < 0.5:
        return "SHIPPED"
    elif r < 0.7:
        return "IN TRANSIT"
    elif r < 0.9:
        return "OUT FOR DELIVERY"
    else:
        return "DELIVERED"

def shipment_status_from_order(status):
    if status == "CANCELLED":
        return "CANCELLED"
    elif status == "DELIVERED":
        return "DELIVERED"
    elif status == "SHIPPED":
        return random.choice(["IN TRANSIT", "OUT FOR DELIVERY"])
    else:
        return "PENDING"


def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON") 

    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone INTEGER NOT NULL,
                    address TEXT NOT NULL
                )""")
    cursor.execute(
               """CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    order_date TEXT NOT NULL,
                    delivers_at TEXT,
                    status TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    total_price REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                    )
                    """)
    cursor.execute(
                    """CREATE TABLE IF NOT EXISTS shipment(
                    shipment_id VARCHAR PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    address TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    pincode INTEGER NOT NULL,
                    tracking_number TEXT NOT NULL UNIQUE,
                    delivery_status TEXT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )""")
    cursor.execute(
                """CREATE TABLE IF NOT EXISTS products (
                    product_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    price REAL NOT NULL,
                    stock INTEGER NOT NULL
                )""")
    conn.commit()

def clear_tables(conn):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shipment")
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM products")
    conn.commit()

def insert_fake_data(conn):
    cursor = conn.cursor()
    users = []
    user_emails = set()
    for uid in range(1,USER_COUNT+1):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 1000)}@example.com"
        while email in user_emails:
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 1000)}@example.com"
        user_emails.add(email)
        phone = rand_phone_int()
        city, state, pincode = random.choice(CITIES)
        address = f"{random.randint(100, 999)} {random.choice(['Main St', '2nd St', '3rd St', 'Park Ave', 'Oak St'])}, {city}, {state} - {pincode}"
        users.append((uid,name, email, phone, address))
    cursor.executemany("INSERT INTO users (user_id, name, email, phone, address) VALUES (?, ?, ?, ?, ?)", users)

    products = []
    for pid in range(1, PRODUCT_COUNT + 1):
        name = random.choice(PRODUCT_NAMES)
        description = f"This is a high-quality {name.lower()} suitable for everyday use."
        price = round(random.uniform(10.0, 500.0), 2)
        stock = random.randint(10, 200)
        products.append((pid, name, description, price, stock))
    cursor.executemany("INSERT INTO products (product_id, name, description, price, stock) VALUES (?, ?, ?, ?, ?)", products)

    orders = []
    shipment = []
    for oid in range(1, ORDER_COUNT + 1):
        user_id = random.randint(1, USER_COUNT)
        product_id = random.randint(1, PRODUCT_COUNT)
        order_date = rand_date_within_last(120)
        status = pick_status()
        delivers_at = rand_date_within_next(7, order_date) if status == "DELIVERED" else None
        quantity = random.randint(1, 5)
        cursor.execute("SELECT price FROM products WHERE product_id = ?", (product_id,))
        price = cursor.fetchone()[0]
        total_price = round(price * quantity, 2)
        orders.append((oid, user_id, product_id, order_date, delivers_at, status, quantity, total_price))

        cursor.execute("SELECT address FROM users WHERE user_id = ?", (user_id,))
        address = cursor.fetchone()[0]
        address_word = re.findall(r'\w+', address)
        city, state, pincode = address_word[-3], address_word[-2], int(address_word[-1])
        s_id = f"{oid}{address_word[-3][0:2].upper()}{address_word[-2][0:2].upper()}{address_word[-1][-2:]}"
        tracking_number = rand_tracking_number()
        delivery_status = shipment_status_from_order(status)
        shipment.append((s_id, oid , address, city, state, pincode, tracking_number, delivery_status))

    cursor.executemany("INSERT INTO orders (order_id, user_id, product_id, order_date, delivers_at, status, quantity, total_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", orders)
    cursor.executemany("INSERT INTO shipment (shipment_id, order_id, address, city, state, pincode, tracking_number, delivery_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", shipment)

    conn.commit()

def quick_sanity_check(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders")
    order_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM shipment")
    shipment_count = cursor.fetchone()[0]

    print(f"Users: {user_count}, Products: {product_count}, Orders: {order_count}, Shipments: {shipment_count}")
    cursor.execute("""
                   SELECT o.order_id, u.name, p.name, o.order_date, o.status, s.tracking_number, s.delivery_status
                   FROM orders o
                   JOIN users u ON o.user_id = u.user_id
                   JOIN products p ON o.product_id = p.product_id
                   JOIN shipment s ON o.order_id = s.order_id
                   LIMIT 5;
                   """)
    rows = cursor.fetchall()
    for row in rows:
        print(row)
def delete_tables(conn):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS shipment")
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS products")
    conn.commit()

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    delete_tables(conn)      # comment this line if you DON'T want to drop old tables
    create_tables(conn)
    clear_tables(conn)          # comment this line if you DON'T want to wipe old data
    insert_fake_data(conn)
    quick_sanity_check(conn)

    conn.close()
    print(f"\nDone. Database created at: {DB_PATH}")