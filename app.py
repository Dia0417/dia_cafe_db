import streamlit as st
import requests
import pandas as pd
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1506619216599-9d16d0903dfd?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NDR8fGNhZmV8ZW58MHx8MHx8fDA%3D");
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)



import datetime, json
from io import BytesIO

# ============ OPTIONAL (PDF) ============
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    PDF_OK = True
except Exception:
    PDF_OK = False

# ============ MYSQL SETUP ============
import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "localhost",
    "user": "root",          # <-- apna user
    "password": "Kashaf@1122",  # <-- apna password
    "database": "cafe_db",
}

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(32) NOT NULL,
                customer VARCHAR(100) NOT NULL,
                table_no INT NOT NULL,
                date_time DATETIME NOT NULL,
                items_json JSON NOT NULL,
                discount INT NOT NULL,
                total DECIMAL(10,2) NOT NULL,
                payment VARCHAR(20) NOT NULL
            )
        """)
        conn.commit()
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass

def insert_order(order):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders
        (order_id,customer_name, table_no, date_time, items_json, discount, total, payment)
        VALUES (%s, %s, %s ,%s ,CAST(%s AS JSON), %s, %s, %s)
    """, (
        order["order_id"],
        order["customer_name"],
        order["table"],
        order["date_time"],
        json.dumps(order["items"]),     # store items as JSON
        order["discount"],
        float(order["total"]),
        order["payment"],
    ))
    conn.commit()
    cur.close(); conn.close()

def fetch_orders(limit=100):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM orders ORDER BY order_id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

# ============ PDF HELPER ============
def create_pdf(order_details):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)

    c.drawString(200, 750, "Cafe Management System - Bill")
    c.drawString(50, 720, f"Order ID: {order_details['order_id']}")
    c.drawString(50, 700, f"Customer_name: {order_details['customer_name']}")
    c.drawString(50, 680, f"Table No: {order_details['table']}")
    c.drawString(50, 660, f"Date: {order_details['date_time'].strftime('%Y-%m-%d %H:%M:%S')}")

    y = 630
    for it in order_details["items"]:
        c.drawString(50, y, f"{it['qty']} x {it['name']} = ${it['cost']:.2f}")
        y -= 20
        if y < 80:
            c.showPage(); y = 730

    c.drawString(50, y-10, f"Discount: {order_details['discount']}%")
    c.drawString(50, y-30, f"Total: ${order_details['total']:.2f}")
    c.drawString(50, y-50, f"Payment Method: {order_details['payment']}")
    c.save()
    buffer.seek(0)
    return buffer

# ============ APP ============
init_db()

st.title("☕ Cafe Management System ")

# Categorized menu (feel free to edit)
MENU = {
    "Drinks": {"Coffee": 3.00,"Tea": 2.50},
    "Snacks": {"Sandwich": 5.00,"Cake": 4.00},
    "meals":{"burger":8.00,"fries":3.50}
}

# Inputs
colA, colB = st.columns(2)
with colA:
    customer_name = st.text_input("Customer_Name", placeholder="e.g., sadia")
with colB:
    table_no = st.number_input("Table No.", min_value=1, step=1, value=1)

st.subheader("📋 Menu")
ordered_items, order_total = [], 0.0

for category, items in MENU.items():
    st.markdown(f"### 🍽 {category}")
    for item, price in items.items():
        qty = st.number_input(f"{item} (${price:.2f})", min_value=0, step=1, key=f"qty_{item}")
        if qty > 0:
            cost = qty * price
            ordered_items.append({"name": item, "qty": qty, "cost": cost})
            order_total += cost

discount = st.slider("Discount (%)", 0, 50, 0)
final_total = round(order_total - (order_total * discount / 100), 2)
payment_method = st.radio("Payment Method", ["Cash", "Card", "Online"], horizontal=True)

# Generate & Save
if st.button("Generate Bill & Save to MySQL"):
    if not ordered_items:
        st.warning("Please select at least one item.")
    else:
        order_id = f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        order_obj = {
            "order_id": order_id,
            "customer_name": customer_name if customer_name.strip() else "Guest",
            "table": int(table_no),
            "date_time": datetime.datetime.now(),
            "items": ordered_items,
            "discount": int(discount),
            "total": final_total,
            "payment": payment_method
        }

        try:
            insert_order(order_obj)
            st.success(f"Saved to MySQL ✓  Order ID: {order_id}")
            st.subheader("🧾 Bill Summary")
            st.write(f"*Order:* {order_id}")
            st.write(f"*Customer_name:* {order_obj['customer_name']}  |  *Table:* {order_obj['table']}")
            st.write(f"*Date:* {order_obj['date_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            st.write("---")
            for it in ordered_items:
                st.write(f"{it['qty']} × {it['name']} = ${it['cost']:.2f}")
            st.write("---")
            st.write(f"Discount: {discount}%")
            st.success(f"Total: *${final_total:.2f}*  |  Payment: *{payment_method}*")

            if PDF_OK:
                pdf_buf = create_pdf(order_obj)
                st.download_button("⬇ Download PDF Bill", data=pdf_buf,
                                   file_name=f"{order_id}.pdf", mime="application/pdf")
            else:
                st.info("PDF module not found. Install reportlab to enable PDF download.")

        except Error as e:
            st.error(f"MySQL error: {e}")

# History from DB
st.subheader("📜 Order History (latest 100)")
try:
    rows = fetch_orders(limit=100)
    if rows:
        for r in rows:
            # items count shown brief
            items = json.loads(r["items_json"])
            qty_sum = sum(i["qty"] for i in items)
            st.write(
                f"{r['order_id']}** | {r['customer_name']} | Table {r['table_no']} | "
                f"{qty_sum} items | ${float(r['total']):.2f} | {r['date_time']}"
            )
    else:
        st.info("No orders yet.")
except Error as e:
    st.error(f"MySQL error while fetching history: {e}")