from fastapi import HTTPException
from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime
from fastapi.responses import JSONResponse

app = FastAPI(title="WillowCommerce API Example")


NGROK_BASE = "https://ungratuitous-overillustrative-samual.ngrok-free.dev"

@app.get("/openapi-3.0.json", include_in_schema=False)
def openapi_30():
    schema = app.openapi()

    # Force OpenAPI version to 3.0.3 for Foundry compatibility
    schema["openapi"] = "3.0.3"

    # Ensure Foundry knows the base URL
    schema["servers"] = [{"url": NGROK_BASE}]

    return JSONResponse(schema)

DB_PATH = "example.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def days_since(delivers_at: str | None) -> int | None:
    if delivers_at is None:
        return -1
    deliver_date = datetime.strptime(delivers_at, "%Y-%m-%d")
    delta = datetime.now() - deliver_date
    return delta.days


# -------------- PAYLOAD MODELS -------------- 

class searchingOrders(BaseModel):
    user_id: int
    query : str

class findUser(BaseModel):
    username: str

class refundOrder(BaseModel):
    order_id: int
    reason: str

class cancelOrder(BaseModel):
    order_id: int
    
class ReplaceItem(BaseModel):
    order_id: int

# -------------- API ENDPOINTS --------------
@app.get("/orders/{order_id}")
def read_data(item_id: int):
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return dict(item)

# @app.get("/order/find_user/{username}")
# def find_user(username: str):
#     conn = get_db_connection()
#     user = conn.execute("SELECT user_id FROM users WHERE name = ?", (username,)).fetchone()
#     conn.close()
#     if user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return dict(user)

# @app.get("/order/searching_orders/{user_id}/{product_id}")
# def searching_orders(user_id: int, product_id: int):
#     conn = get_db_connection()
#     orders = conn.execute("SELECT * FROM orders WHERE user_id = ? AND product_id = ?", (user_id, product_id)).fetchall()
#     conn.close()
#     if not orders:
#         raise HTTPException(status_code=404, detail="No orders found")
#     return [dict(order) for order in orders]

# @app.post("/search_orders")
# def get_status_info(payload: searchingOrders):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     q = f"%{payload.query}%"
#     cursor.execute("""SELECT order_id,product_name,status,order_date 
#                           FROM orders 
#                           WHERE user_id = ? AND products LIKE ?
#                           ORDER BY order_date DESC
#                           LIMIT 5
#                           """, 
#                           (payload.user_id, q),)
#     rows = [dict(row) for row in cursor.fetchall()]
#     conn.close()
#     if not rows:
#         raise HTTPException(status_code=404, detail="No orders found")
#     return {"matched_rows": rows}

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM orders WHERE order_id = ?""", (order_id,))
    order = cursor.fetchone()
    conn.close()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    data = dict(order)
    date_since_ordered = days_since(data["order_date"])
    data["days_since_ordered"] = date_since_ordered
    return data

@app.post("/orders/{order_id}/cancel")
def initiate_cancellation(order_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT status FROM orders WHERE order_id = ?""", (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    status = row["status"]
    if status not in ["PLACED", "PROCESSING"]:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Order cannot be canceled because order is {status}")
    cursor.execute("""UPDATE orders 
                   SET status = 'CANCELLED' WHERE order_id = ?""",
                   (order_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "order_id": order_id, "new_status": "CANCELLED"}

@app.post("/orders/{order_id}/refund")
def initiate_refund(order_id: int, payload: refundOrder):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT status, delivers_at FROM orders WHERE order_id = ?""", (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    status = row["status"]
    delivers_at = row["delivers_at"]
    days_passed = days_since(delivers_at)

    if status != "DELIVERED":
        conn.close()
        raise HTTPException(status_code=400, detail=f"Refund not applicable as order is {status}")
    if days_passed is None or days_passed > 7:
        conn.close()
        raise HTTPException(status_code=400, detail="Refund period has expired")

    cursor.execute("""UPDATE orders 
                   SET status = 'REFUND_INITIATED' WHERE order_id = ?""",
                   (order_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "order_id": order_id, "new_status": "REFUND_INITIATED","reason": payload.reason}

@app.post("/orders/{order_id}/replace")
def initiate_replacement(order_id: int, payload: ReplaceItem):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT status, delivers_at FROM orders WHERE order_id = ?""", (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    status = row["status"]
    delivers_at = row["delivers_at"]
    days_passed = days_since(delivers_at)

    if status != "DELIVERED":
        conn.close()
        raise HTTPException(status_code=400, detail=f"Replacement not applicable as order is {status}")
    if days_passed is None or days_passed > 7:
        conn.close()
        raise HTTPException(status_code=400, detail="Replacement period has expired")

    cursor.execute("""UPDATE orders 
                   SET status = 'REPLACEMENT_INITIATED' WHERE order_id = ?""",
                   (order_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "order_id": order_id, "new_status": "REPLACEMENT_INITIATED"}