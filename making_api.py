from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sqlite3
from datetime import datetime
import os
import uuid
import httpx
import time

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
class ReplacementReuqest(BaseModel):
    reason: str

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/orders/{tenant_id}/{order_id}")
def get_order(order_id: int,tenant_id:str):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ? AND tenant_id = ?", (order_id,tenant_id)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")

    data = dict(row)
    data["days_since_ordered"] = days_since(data.get("order_date"))
    return data

@app.post("/orders/{tenant_id}/{order_id}/cancel")
def initiate_cancellation(order_id: int,tenant_id:str):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,tenant_id)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    conn.execute("UPDATE orders SET status = 'CANCELLED' WHERE order_id = ? AND tenant_id = ?", (order_id,tenant_id))
    conn.commit()
    conn.close()
    return {"ok": True, "order_id": order_id, "user_id": tenant_id, "new_status": "CANCELLED"}

@app.post("/orders/{tenant_id}/{order_id}/replacement")
def replacementOrder(order_id: int,tenant_id:str,payload: ReplacementReuqest):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ? AND tenant_id = ?", (order_id,tenant_id)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    package_id = "UUS6153790882160798"
    if not package_id:
        conn.close()
        raise HTTPException(status_code=409, detail="Package ID missing; cannot generate label")

    # ✅ Update order status
    conn.execute(
        "UPDATE orders SET status = 'REPLACEMENT INITIATED' WHERE order_id = ? AND tenant_id = ?",
        (order_id, tenant_id)
    )

    # ✅ Call label printing API (returns PDF bytes)
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(
                os.environ["UNIUNI_PRINTLABEL_URL"],
                json={
                    "packageId": package_id,
                    "labelType": 6,
                    "labelFormat": "pdf",
                    "type": "pdf"
                }
            )
        if r.status_code != 200 or not r.content:
            conn.rollback()
            conn.close()
            raise HTTPException(status_code=502, detail="Label service failed")
        pdf_bytes = r.content
    except httpx.HTTPError:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=502, detail="Label service unreachable")

    # ✅ Save label PDF in DB
    label_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO labels (id, tenant_id, order_id, kind, created_at, pdf) VALUES (?, ?, ?, ?, ?, ?)",
        (label_id, tenant_id, order_id, "replacement", int(time.time()), pdf_bytes)
    )

    conn.commit()
    conn.close()

    # ✅ Return JSON so Foundry tool can pass it back to agent/UI
    return {
        "ok": True,
        "order_id": order_id,
        "tenant_id": tenant_id,
        "new_status": "REPLACEMENT INITIATED",
        "reason": payload.reason,
        "label": {
            "label_id": label_id,
            "view_url": f"/labels/{label_id}/view",
            "download_url": f"/labels/{label_id}/download"
        }
    }

@app.post("/orders/{tenant_id}/{order_id}/return")
def initiate_refund(order_id: int,tenant_id:str, payload: RefundRequest):
    conn = get_db_connection()
    row = conn.execute("SELECT status, delivers_at FROM orders WHERE order_id = ? AND user_id = ?", (order_id,tenant_id)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    status = row["status"]
    delivers_at = row["delivers_at"]
    days_passed = days_since(delivers_at)
    
    package_id = "UUS6153790882160798"
    if not package_id:
        conn.close()
        raise HTTPException(status_code=409, detail="Package ID missing; cannot generate label")

    # ✅ Update order status
    conn.execute(
        "UPDATE orders SET status = 'REFUND_INITIATED' WHERE order_id = ? AND tenant_id = ?",
        (order_id, tenant_id)
    )

    # ✅ Call label printing API (returns PDF bytes)
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(
                os.environ["UNIUNI_PRINTLABEL_URL"],
                json={
                    "packageId": package_id,
                    "labelType": 6,
                    "labelFormat": "pdf",
                    "type": "pdf"
                }
            )
        if r.status_code != 200 or not r.content:
            conn.rollback()
            conn.close()
            raise HTTPException(status_code=502, detail="Label service failed")
        pdf_bytes = r.content
    except httpx.HTTPError:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=502, detail="Label service unreachable")

    # ✅ Save label PDF in DB
    label_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO labels (id, tenant_id, order_id, kind, created_at, pdf) VALUES (?, ?, ?, ?, ?, ?)",
        (label_id, tenant_id, order_id, "return", int(time.time()), pdf_bytes)
    )

    conn.commit()
    conn.close()

    # ✅ Return JSON so Foundry tool can pass it back to agent/UI
    return {
        "ok": True,
        "order_id": order_id,
        "tenant_id": tenant_id,
        "new_status": "REFUND_INITIATED",
        "reason": payload.reason,
        "label": {
            "label_id": label_id,
            "view_url": f"/labels/{label_id}/view",
            "download_url": f"/labels/{label_id}/download"
        }
    }

@app.post("/orders/{tenant_id}/{order_id}/humancontact")
def human_contact(order_id:int,tenant_id:str):
    return{"print":f"""Human contact achived in {tenant_id}"""}