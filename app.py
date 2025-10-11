import streamlit as st
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

# ============ sqlite SETUP ============
import sqlite3
DB_PATH = "cafe.db"
def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            customer TEXT NOT NULL,
            table_no INTEGER NOT NULL,
            date_time TEXT NOT NULL,
            items_json TEXT NOT NULL,
            discount INTEGER NOT NULL,
            total REAL NOT NULL,
            payment TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

def insert_order(order):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders
        (order_id, customer, table_no, date_time, items_json, discount, total, payment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order["order_id"],
        order["customer"],
        order["table_no"],
        order["date_time"],
        order["items_json"],     # store items as JSON
        order["discount"],
        order["total"],
        order["payment"],
    ))
    conn.commit()
    conn.close()

def fetch_orders(limit=100):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ============ PDF HELPER ============
def create_pdf(order_details):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)

    c.drawString(200, 750, "Cafe Management System - Bill")
    c.drawString(50, 720, f"Order ID: {order_details['order_id']}")
    c.drawString(50, 700, f"Customer: {order_details['customer']}")
    c.drawString(50, 680, f"Table No: {order_details['table_no']}")
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
st.write("this app has a custom background")


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
if st.button("Generate Bill & Save to sqlite"):
    if not ordered_items:
        st.warning("Please select at least one item.")
    else:
        order_id = f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        order_obj = {
            "order_id": order_id,
            "customer": customer_name.strip() if customer_name.strip() else "Guest",
            "table_no": int(table_no),
            "date_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "items_json": json.dumps(ordered_items),
            "discount": int(discount),
            "total": final_total,
            "payment": payment_method
        }

        try:
            insert_order(order_obj)
            st.success(f"Saved to sqlite ✓  Order ID: {order_id}")
            st.subheader("🧾 Bill Summary")
            st.write(f"*Order:* {order_id}")
            st.write(f"*Customer:* {order_obj['customer']}  |  *Table:* {order_obj['table_no']}")
            st.write(f"*Date:* {order_obj['date_time']}")
            st.write("---")
            for it in ordered_items:
                st.write(f"{it['qty']} × {it['name']} = ${it['cost']:.2f}")
            st.write("---")
            st.write(f"Discount: {discount}%")
            st.success(f"Total:${final_total:.2f}|  Payment: *{payment_method}*")

            if PDF_OK:
                pdf_order = order_obj.copy()
                pdf_order["items"] = ordered_items
                pdf_order["date_time"] = datetime.datetime.strptime(order_obj["date_time"], '%Y-%m-%d %H:%M:%S')
                pdf_buf = create_pdf(pdf_order)
                st.download_button("⬇ Download PDF Bill", data=pdf_buf,
                                   file_name=f"{order_id}.pdf", mime="application/pdf")
            else:
                st.info("PDF module not found. Install reportlab to enable PDF download.")

        except sqlite3.Error as e:
            st.error(f"sqlite error: {e}")

# History from DB
# History from DB
st.subheader("📜 Order History (latest 100)")
try:
    rows = fetch_orders(limit=100)
    if rows:
        for r in rows:
            # items count shown brief
            try:
                items = json.loads(r["items_json"])
                qty_sum = sum(i["qty"] for i in items)
                st.write(
                    f"{r['order_id']} | {r['customer']} | Table {r['table_no']} | "
                    f"{qty_sum} items | ${float(r['total']):.2f} | {r['date_time']}"
                )
            except Exception as e:
                st.write(f"Error loading items for order {r['order_id']}: {e}")
    else:
        st.info("No orders yet.")
except sqlite3.Error as e:
    st.error(f"sqlite3 error: {e}")