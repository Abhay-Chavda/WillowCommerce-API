import sqlite3
import random
from datetime import datetime, timedelta
import string
import re

DB_PATH = "example.db"
random.seed(42)

USER_COUNT = 100
PRODUCT_COUNT = 50
ORDER_COUNT = 100

FIRST_NAMES = ["Abhay", "Ravi", "Aditi", "Neha", "Karan", "Priya", "Aman", "Sahil", "Meera", "Isha", "Arjun", "Vikram"]
LAST_NAMES = ["Chavda", "Kumar", "Sharma", "Patel", "Singh", "Verma", "Gupta", "Mehta", "Joshi", "Rao", "Nair", "Das"]

TENANTS = [("u1", "user1"), ("u2", "user2")]
ORDER_APPS = ["amazon", "walmart", "shopify", "ebay"]

CITIES = [
    ("Ahmedabad", "Gujarat", 380001),
    ("Surat", "Gujarat", 395003),
    ("Vadodara", "Gujarat", 390001),
    ("Jaipur", "Rajasthan", 302001),
    ("Delhi", "Delhi", 110001),
    ("Mumbai", "Maharashtra", 400001),
]

PRODUCT_NAMES = [
    "Wireless Mouse", "Keyboard", "Headphones", "USB Cable",
    "Power Bank", "Laptop Stand", "Backpack", "Water Bottle"
]
STATUSES = [
    "CREATED",
"CONFIRMED",
"PROCESSING",
"PACKED",
"SHIPPED",
"OUT_FOR_DELIVERY",
"DELIVERED",
"COMPLETED"

]
# ---------- Helpers ----------

def rand_phone():
    return int(str(random.choice([6, 7, 8, 9])) + str(random.randint(10**8, 10**9 - 1)))

def rand_date_last(days=120):
    return (datetime.now() - timedelta(days=random.randint(0, days))).strftime("%Y-%m-%d")

def rand_date_next(days=7, start=None):
    start = datetime.strptime(start, "%Y-%m-%d") if start else datetime.now()
    return (start + timedelta(days=random.randint(1, days))).strftime("%Y-%m-%d")

def rand_tracking():
    return "TRK-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

# ---------- DB Setup ----------

def create_tables(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone INTEGER NOT NULL,
            address TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id TEXT PRIMARY KEY,
            tenant_name TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            tenant_id TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            order_app TEXT NOT NULL,
            order_date TEXT NOT NULL,
            delivers_at TEXT,
            status TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS shipment (
            shipment_id TEXT PRIMARY KEY,
            order_id INTEGER NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            pincode INTEGER NOT NULL,
            tracking_number TEXT UNIQUE NOT NULL,
            delivery_status TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    """)

    conn.commit()

# ---------- Data Insert ----------

def insert_fake_data(conn):
    cur = conn.cursor()

    # tenants (insert once)
    cur.executemany(
        "INSERT OR IGNORE INTO tenants (tenant_id, tenant_name) VALUES (?, ?)",
        TENANTS
    )

    # users
    users = []
    emails = set()
    for uid in range(1, USER_COUNT + 1):
        fn, ln = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        email = f"{fn.lower()}.{ln.lower()}{uid}@example.com"
        city, state, pin = random.choice(CITIES)
        address = f"{random.randint(10,999)} Main St, {city}, {state} - {pin}"
        users.append((uid, f"{fn} {ln}", email, rand_phone(), address))
    cur.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?)", users)

    # products
    products = []
    for pid in range(1, PRODUCT_COUNT + 1):
        name = random.choice(PRODUCT_NAMES)
        products.append((pid, name, f"Good quality {name}", round(random.uniform(10, 500), 2), random.randint(10, 200)))
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)

    # orders + shipment
    orders = []
    shipments = []

    for oid in range(1, ORDER_COUNT + 1):
        user_id = random.randint(1, USER_COUNT)
        product_id = random.randint(1, PRODUCT_COUNT)
        tenant_id = random.choice(["u1", "u2"])
        order_date = rand_date_last()
        delivers_at = rand_date_next(7, order_date)
        qty = random.randint(1, 5)
        status = random.choice(STATUSES)

        cur.execute("SELECT price FROM products WHERE product_id=?", (product_id,))
        price = cur.fetchone()[0]

        total = round(price * qty, 2)
        orders.append((oid, user_id, tenant_id, product_id, random.choice(ORDER_APPS),
                       order_date, delivers_at, status, qty, total))

        cur.execute("SELECT address FROM users WHERE user_id=?", (user_id,))
        address = cur.fetchone()[0]
        city, state, pin = re.findall(r"\w+", address)[-3:]
        shipments.append((f"SHP{oid}", oid, address, city, state, int(pin), rand_tracking(), status))

    cur.executemany("""
        INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, orders)

    cur.executemany("""
        INSERT INTO shipment VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, shipments)

    conn.commit()

# ---------- Check ----------

def sanity_check(conn):
    cur = conn.cursor()
    for table in ["users", "products", "tenants", "orders", "shipment"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"{table}: {cur.fetchone()[0]}")

    cur.execute("""
        SELECT o.order_id, u.name, t.tenant_name, p.name, s.tracking_number
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        JOIN tenants t ON o.tenant_id = t.tenant_id
        JOIN products p ON o.product_id = p.product_id
        JOIN shipment s ON o.order_id = s.order_id
        LIMIT 5
    """)
    for row in cur.fetchall():
        print(row)

# ---------- Main ----------

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    create_tables(conn)
    insert_fake_data(conn)
    sanity_check(conn)

    conn.close()
    print("\n✅ Database created successfully.")
