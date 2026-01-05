from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sqlite3
from datetime import datetime

app = FastAPI(title="WillowCommerce API Example")
DB_PATH = "example.db"

@app.get("/openapi-3.0.json", include_in_schema=False)
def openapi_30(request: Request):
    schema = app.openapi()
    schema["openapi"] = "3.0.3"
    base_url = str(request.base_url).rstrip("/")
    schema["servers"] = [{"url": base_url}]
    return JSONResponse(schema)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def days_since(date_str: str | None) -> int | None:
    if not date_str:
        return None
    deliver_date = datetime.strptime(date_str, "%Y-%m-%d")
    return (datetime.now() - deliver_date).days

class RefundRequest(BaseModel):
    reason: str

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")

    data = dict(row)
    data["days_since_ordered"] = days_since(data.get("order_date"))
    return data

@app.post("/orders/{order_id}/cancel")
def initiate_cancellation(order_id: int):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    status = row["status"]
    conn.execute("UPDATE orders SET status = 'CANCELLED' WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "order_id": order_id, "new_status": "CANCELLED"}

@app.post("/orders/{order_id}/refund")
def initiate_refund(order_id: int, payload: RefundRequest):
    conn = get_db_connection()
    row = conn.execute("SELECT status, delivers_at FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    status = row["status"]
    delivers_at = row["delivers_at"]
    days_passed = days_since(delivers_at)

    if status in ["PLACED", "PROCESSING"]:
        conn.close()
        raise HTTPException(status_code=409, detail=f"Refund not applicable as order is {status}. You can cancel it.")
    if status != "DELIVERED":
        conn.close()
        raise HTTPException(status_code=409, detail=f"Refund not applicable as order is {status}.")
    if days_passed is None or days_passed > 7:
        conn.close()
        raise HTTPException(status_code=409, detail="Refund period has expired")

    conn.execute("UPDATE orders SET status = 'REFUND_INITIATED' WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "order_id": order_id, "new_status": "REFUND_INITIATED", "reason": payload.reason}
