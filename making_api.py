from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from datetime import datetime, date
import os
import uuid
import httpx
import time
import io

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

app = FastAPI(title="WillowCommerce API Example")

# Load .env only locally (Render will use Dashboard env vars)
if os.path.exists(".env"):
    load_dotenv()

# ---- ENV ----
BASE_URL = os.environ["BASE_URL"].rstrip("/")
UNIUNI_URL = os.environ["UNINUNIUNI_PRINTLABEL_URL"]
TOKEN = os.environ["TOKEN"]
DATABASE_URL = os.environ["INTERNAL_DATABASE_URL"]

# For label API (you send JSON, not PDF)
LABEL_API_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# ---- OpenAPI 3.0 route ----
@app.get("/openapi-3.0.json", include_in_schema=False)
def openapi_30(request: Request):
    schema = app.openapi()
    schema["openapi"] = "3.0.3"
    base_url = str(request.base_url).rstrip("/")
    schema["servers"] = [{"url": base_url}]
    return JSONResponse(schema)


# ---------- DB helpers ----------
def get_db_connection():
    # RealDictCursor makes rows behave like dicts: row["status"]
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def days_since(val) -> int | None:
    """
    Works with Postgres date/datetime OR string.
    """
    if not val:
        return None

    if isinstance(val, datetime):
        dt = val
    elif isinstance(val, date):
        dt = datetime.combine(val, datetime.min.time())
    elif isinstance(val, str):
        # try common formats
        try:
            dt = datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            # ISO fallback
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
    else:
        return None

    return (datetime.now() - dt).days


# ---------- Schemas ----------
class RefundRequest(BaseModel):
    reason: str


class ReplacementRequest(BaseModel):
    reason: str


# ------------ Label endpoints ------------
@app.get("/labels/{label_id}/view")
def view_label(label_id: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pdf FROM labels WHERE id = %s", (label_id,))
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Label not found")

            return StreamingResponse(io.BytesIO(row["pdf"]), media_type="application/pdf")
    finally:
        conn.close()


@app.get("/labels/{label_id}/download")
def download_label(label_id: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pdf, order_id FROM labels WHERE id = %s", (label_id,))
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Label not found")

            return StreamingResponse(
                io.BytesIO(row["pdf"]),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="return_label_order_{row["order_id"]}.pdf"'}
            )
    finally:
        conn.close()


# ------------- APIs -------------
@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/orders/{tenant_id}/{order_id}")
def get_order(tenant_id: str, order_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM orders WHERE order_id = %s AND tenant_id = %s",
                (order_id, tenant_id)
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Order not found")

            row["days_since_ordered"] = days_since(row.get("order_date"))
            return row
    finally:
        conn.close()


@app.post("/orders/{tenant_id}/{order_id}/cancel")
def initiate_cancellation(tenant_id: str, order_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM orders WHERE order_id = %s AND tenant_id = %s",
                (order_id, tenant_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Order not found")

            cur.execute(
                "UPDATE orders SET status = %s WHERE order_id = %s AND tenant_id = %s",
                ("CANCELLED", order_id, tenant_id)
            )
            conn.commit()

            return {"ok": True, "order_id": order_id, "tenant_id": tenant_id, "new_status": "CANCELLED"}
    finally:
        conn.close()


@app.post("/orders/{tenant_id}/{order_id}/replacement")
def replacement_order(tenant_id: str, order_id: int, payload: ReplacementRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM orders WHERE order_id = %s AND tenant_id = %s",
                (order_id, tenant_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Order not found")

            package_id = "UUS6153790882160798"
            if not package_id:
                raise HTTPException(status_code=409, detail="Package ID missing; cannot generate label")

            # Update status
            cur.execute(
                "UPDATE orders SET status = %s WHERE order_id = %s AND tenant_id = %s",
                ("REPLACEMENT_INITIATED", order_id, tenant_id)
            )

            # Call label API
            try:
                with httpx.Client(timeout=30) as client:
                    r = client.post(
                        UNIUNI_URL,
                        headers=LABEL_API_HEADERS,
                        json={
                            "packageId": package_id,
                            "labelType": 6,
                            "labelFormat": "pdf",
                            "type": "pdf"
                        }
                    )
                if r.status_code != 200 or not r.content:
                    conn.rollback()
                    raise HTTPException(status_code=502, detail="Label service failed")
                pdf_bytes = r.content
            except httpx.HTTPError:
                conn.rollback()
                raise HTTPException(status_code=502, detail="Label service unreachable")

            # Save label
            label_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO labels (id, tenant_id, order_id, kind, created_at, pdf)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (label_id, tenant_id, order_id, "replacement", int(time.time()), psycopg2.Binary(pdf_bytes))
            )

            conn.commit()

            return {
                "ok": True,
                "order_id": order_id,
                "tenant_id": tenant_id,
                "new_status": "REPLACEMENT_INITIATED",
                "reason": payload.reason,
                "label_id": label_id
            }
    finally:
        conn.close()


@app.post("/orders/{tenant_id}/{order_id}/return")
def initiate_refund(tenant_id: str, order_id: int, payload: RefundRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, delivers_at FROM orders WHERE order_id = %s AND tenant_id = %s",
                (order_id, tenant_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Order not found")

            # Optional: compute days passed
            days_passed = days_since(row.get("delivers_at"))

            package_id = "UUS6153790882160798"
            if not package_id:
                raise HTTPException(status_code=409, detail="Package ID missing; cannot generate label")

            # Update status
            cur.execute(
                "UPDATE orders SET status = %s WHERE order_id = %s AND tenant_id = %s",
                ("REFUND_INITIATED", order_id, tenant_id)
            )

            # Call label API
            try:
                with httpx.Client(timeout=30) as client:
                    r = client.post(
                        UNIUNI_URL,
                        headers=LABEL_API_HEADERS,
                        json={
                            "packageId": package_id,
                            "labelType": 6,
                            "labelFormat": "pdf",
                            "type": "pdf"
                        }
                    )
                if r.status_code != 200 or not r.content:
                    conn.rollback()
                    raise HTTPException(status_code=502, detail="Label service failed")
                pdf_bytes = r.content
            except httpx.HTTPError:
                conn.rollback()
                raise HTTPException(status_code=502, detail="Label service unreachable")

            # Save label
            label_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO labels (id, tenant_id, order_id, kind, created_at, pdf)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (label_id, tenant_id, order_id, "return", int(time.time()), psycopg2.Binary(pdf_bytes))#path
            )

            conn.commit()

            return {
                "ok": True,
                "order_id": order_id,
                "tenant_id": tenant_id,
                "new_status": "REFUND_INITIATED",
                "reason": payload.reason,
                "label":{
                    "label_id": label_id,
                }
            }
    finally:
        conn.close()


@app.post("/orders/{tenant_id}/{order_id}/humancontact")
def human_contact(tenant_id: str, order_id: int):
    return {"ok": True, "message": f"Human contact achieved for tenant {tenant_id}", "order_id": order_id}

@app.get("/labels/{order_id}/{tenant_id}/get_label")
def get_label_id(order_id: int, tenant_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM labels WHERE order_id = %s AND tenant_id = %s", (order_id, tenant_id))
    label_id = cur.fetchone()
    return {"ok":True, "label_id":label_id , "view_url":f"https://willowcommerce-api.onrender.com/labels/{label_id}/view", "download_url":f"https://willowcommerce-api.onrender.com/labels/{label_id}/download"}