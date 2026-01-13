import psycopg2
import random
from datetime import datetime, timedelta
import string
import re
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

if os.path.exists(".env"):
    load_dotenv()

DATABASE_URL = os.environ["EXTERNAL_DATABASE_URL"]

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
    "CREATED", "CONFIRMED", "PROCESSING", "PACKED",
    "SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED", "COMPLETED"
]

# ---------- Helpers ----------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def rand_phone():
    return int(str(random.choice([6, 7, 8, 9])) + str(random.randint(10**8, 10**9 - 1)))

def rand_date_last(days=120):
    return (datetime.now() - timedelta(days=random.randint(0, days))).date()

def rand_date_next(days=7, start=None):
    start_dt = start if isinstance(start, datetime) else datetime.now()
    return (start_dt + timedelta(days=random.randint(1, days))).date()

def rand_tracking():
    return "TRK-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

# ---------- DB Setup ----------
def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id TEXT PRIMARY KEY,
                tenant_name TEXT NOT NULL UNIQUE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone BIGINT NOT NULL,
                address TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id BIGINT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price NUMERIC(10,2) NOT NULL,
                stock INTEGER NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id BIGINT PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id),
                tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),
                product_id BIGINT NOT NULL REFERENCES products(product_id),
                order_app TEXT NOT NULL,
                order_date DATE NOT NULL,
                delivers_at DATE,
                status TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total_price NUMERIC(10,2) NOT NULL
                
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shipment (
                shipment_id TEXT PRIMARY KEY,
                order_id BIGINT NOT NULL REFERENCES orders(order_id),
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                pincode INTEGER NOT NULL,
                tracking_number TEXT UNIQUE NOT NULL,
                delivery_status TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS labels (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),
                order_id BIGINT NOT NULL REFERENCES orders(order_id),
                kind TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                pdf BYTEA NOT NULL
            )
        """)

    conn.commit()

# ---------- Data Insert ----------
def insert_fake_data(conn):
    with conn.cursor() as cur:
        # tenants (insert once)
        cur.executemany(
            """
            INSERT INTO tenants (tenant_id, tenant_name)
            VALUES (%s, %s)
            ON CONFLICT (tenant_id) DO NOTHING
            """,
            TENANTS
        )

        # users
        users = []
        for uid in range(1, USER_COUNT + 1):
            fn, ln = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            email = f"{fn.lower()}.{ln.lower()}{uid}@example.com"
            city, state, pin = random.choice(CITIES)
            address = f"{random.randint(10,999)} Main St, {city}, {state} - {pin}"
            users.append((uid, f"{fn} {ln}", email, rand_phone(), address))

        cur.executemany(
            """
            INSERT INTO users (user_id, name, email, phone, address)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            users
        )

        # products
        products = []
        for pid in range(1, PRODUCT_COUNT + 1):
            name = random.choice(PRODUCT_NAMES)
            products.append((pid, name, f"Good quality {name}", round(random.uniform(10, 500), 2), random.randint(10, 200)))

        cur.executemany(
            """
            INSERT INTO products (product_id, name, description, price, stock)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (product_id) DO NOTHING
            """,
            products
        )

        # orders + shipment
        orders = []
        shipments = []

        for oid in range(1, ORDER_COUNT + 1):
            user_id = random.randint(1, USER_COUNT)
            product_id = random.randint(1, PRODUCT_COUNT)
            tenant_id = random.choice(["u1", "u2"])
            order_date = rand_date_last(10)
            qty = random.randint(1, 5)
            status = random.choice(STATUSES)
            delivers_at = rand_date_next(7, datetime.combine(order_date, datetime.min.time())) if status == "DELIVERED" else None

            cur.execute("SELECT price FROM products WHERE product_id = %s", (product_id,))
            price_row = cur.fetchone()
            price = float(price_row["price"])

            total = round(price * qty, 2)

            orders.append((
                oid, user_id, tenant_id, product_id, random.choice(ORDER_APPS),
                order_date, delivers_at, status, qty, total
            ))

            cur.execute("SELECT address FROM users WHERE user_id = %s", (user_id,))
            address_row = cur.fetchone()
            address = address_row["address"]

            # Extract city/state/pin from address "... City, State - PIN"
            m = re.search(r",\s*([^,]+),\s*([A-Za-z]+)\s*-\s*(\d+)\s*$", address)
            if m:
                city, state, pin = m.group(1).strip(), m.group(2).strip(), int(m.group(3))
            else:
                city, state, pin = "Unknown", "Unknown", 0

            shipments.append((
                f"SHP{oid}", oid, address, city, state, pin, rand_tracking(), status
            ))

        cur.executemany(
            """
            INSERT INTO orders
            (order_id, user_id, tenant_id, product_id, order_app, order_date, delivers_at, status, quantity, total_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (order_id) DO NOTHING
            """,
            orders
        )

        cur.executemany(
            """
            INSERT INTO shipment
            (shipment_id, order_id, address, city, state, pincode, tracking_number, delivery_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (shipment_id) DO NOTHING
            """,
            shipments
        )

    conn.commit()

# ---------- Check ----------
def sanity_check(conn):
    with conn.cursor() as cur:
        for table in ["users", "products", "tenants", "orders", "shipment", "labels"]:
            cur.execute(f"SELECT COUNT(*) AS c FROM {table}")
            print(f"{table}: {cur.fetchone()['c']}")

        cur.execute("""
            SELECT o.order_id, u.name, t.tenant_name, p.name AS product_name, s.tracking_number
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            JOIN tenants t ON o.tenant_id = t.tenant_id
            JOIN products p ON o.product_id = p.product_id
            JOIN shipment s ON o.order_id = s.order_id
            LIMIT 5
        """)
        for row in cur.fetchall():
            print(row)
def delete_tables(conn):
    with conn.cursor() as cur:
        for table in ["users", "products", "tenants", "orders", "shipment", "labels"]:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

# ---------- Main ----------
if __name__ == "__main__":
    conn = get_db_connection()
    try:
        delete_tables(conn)
        create_tables(conn)
        insert_fake_data(conn)
        sanity_check(conn)
    finally:
        conn.close()

    print("\n✅ Postgres database seeded successfully.")