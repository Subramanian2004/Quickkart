import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Literal

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "quickkart.db"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

CATEGORIES = [
    "All",
    "Atta, Rice & Dals",
    "Dairy, Bread & Eggs",
    "Fruits & Vegetables",
    "Snacks & Munchies",
    "Beverages",
    "Personal Care",
]

SEED_PRODUCTS = [
    ("Aashirvaad Atta 5kg", 249, 279, "Atta, Rice & Dals", "🌾", 4.7, 142),
    ("India Gate Basmati Rice 1kg", 145, 169, "Atta, Rice & Dals", "🍚", 4.6, 98),
    ("Toor Dal 1kg", 160, 185, "Atta, Rice & Dals", "🫘", 4.5, 86),
    ("Moong Dal 1kg", 145, 165, "Atta, Rice & Dals", "🫘", 4.4, 71),
    ("Fortune Sunflower Oil 1L", 145, 169, "Atta, Rice & Dals", "🫗", 4.5, 115),
    ("Tata Salt 1kg", 28, 32, "Atta, Rice & Dals", "🧂", 4.7, 201),

    ("Amul Taaza Milk 1L", 58, 62, "Dairy, Bread & Eggs", "🥛", 4.8, 322),
    ("Harvest White Bread 400g", 45, 50, "Dairy, Bread & Eggs", "🍞", 4.5, 119),
    ("Farm Fresh Eggs 6 pcs", 55, 65, "Dairy, Bread & Eggs", "🥚", 4.7, 287),
    ("Amul Butter 100g", 58, 62, "Dairy, Bread & Eggs", "🧈", 4.8, 164),
    ("Amul Curd 400g", 40, 45, "Dairy, Bread & Eggs", "🥣", 4.6, 132),
    ("Britannia Cheese Slices", 145, 160, "Dairy, Bread & Eggs", "🧀", 4.5, 78),

    ("Fresh Bananas 1kg", 55, 65, "Fruits & Vegetables", "🍌", 4.6, 188),
    ("Red Apples 1kg", 160, 190, "Fruits & Vegetables", "🍎", 4.7, 149),
    ("Tomatoes 1kg", 42, 50, "Fruits & Vegetables", "🍅", 4.4, 96),
    ("Potatoes 1kg", 38, 45, "Fruits & Vegetables", "🥔", 4.5, 177),
    ("Onions 1kg", 44, 50, "Fruits & Vegetables", "🧅", 4.5, 166),
    ("Green Capsicum 500g", 52, 60, "Fruits & Vegetables", "🫑", 4.3, 61),

    ("Lay's Magic Masala 90g", 20, 20, "Snacks & Munchies", "🥔", 4.6, 305),
    ("Oreo Original 120g", 30, 35, "Snacks & Munchies", "🍪", 4.7, 219),
    ("Dettol Soap 100g", 42, 48, "Personal Care", "🧼", 4.6, 151),
    ("Colgate Toothpaste 200g", 105, 120, "Personal Care", "🪥", 4.7, 204),
    ("Nescafe Classic 50g", 165, 185, "Beverages", "☕", 4.7, 174),
    ("Coca-Cola 750ml", 40, 45, "Beverages", "🥤", 4.5, 142),
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            mrp REAL NOT NULL,
            category TEXT NOT NULL,
            emoji TEXT NOT NULL,
            rating REAL NOT NULL,
            reviews INTEGER NOT NULL,
            stock INTEGER NOT NULL DEFAULT 50
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL UNIQUE,
            items_json TEXT NOT NULL,
            subtotal REAL NOT NULL,
            delivery_fee REAL NOT NULL,
            discount REAL NOT NULL,
            total REAL NOT NULL,
            address TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    count = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count == 0:
        conn.executemany("""
            INSERT INTO products
            (name, price, mrp, category, emoji, rating, reviews, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, 50)
        """, SEED_PRODUCTS)
    conn.commit()
    conn.close()

def get_products(query="", category="All"):
    conn = get_db()
    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if category and category != "All":
        sql += " AND category = ?"
        params.append(category)
    if query:
        sql += " AND (name LIKE ? OR category LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like])
    sql += " ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_product(product_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def cart_dict():
    raw = session.get("cart", {})
    return {str(k): int(v) for k, v in raw.items()}

def save_cart(cart):
    session["cart"] = {str(k): int(v) for k, v in cart.items() if int(v) > 0}
    session.modified = True

def cart_details():
    cart = cart_dict()
    items = []
    subtotal = 0.0
    for pid, qty in cart.items():
        product = get_product(int(pid))
        if not product:
            continue
        line_total = product["price"] * qty
        subtotal += line_total
        items.append({
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "emoji": product["emoji"],
            "quantity": qty,
            "line_total": line_total,
        })
    delivery_fee = 0 if subtotal >= 499 or subtotal == 0 else 29
    discount = 0
    coupon = session.get("coupon")
    if coupon == "WELCOME50" and subtotal >= 299:
        discount = min(50, subtotal)
    elif coupon == "SAVE10" and subtotal >= 499:
        discount = round(subtotal * 0.10, 2)
    total = max(0, subtotal + delivery_fee - discount)
    return {
        "items": items,
        "subtotal": round(subtotal, 2),
        "delivery_fee": round(delivery_fee, 2),
        "discount": round(discount, 2),
        "total": round(total, 2),
        "coupon": coupon,
        "item_count": sum(x["quantity"] for x in items),
    }

def find_product_from_text(text):
    products = get_products()
    t = text.lower()
    scored = []
    for p in products:
        name_words = [w for w in p["name"].lower().replace("(", " ").replace(")", " ").split() if len(w) > 2]
        score = sum(1 for w in name_words if w in t)
        if p["name"].lower() in t:
            score += 10
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else None

class ChatAction(BaseModel):
    type: Literal["add", "remove", "set_qty", "search", "show_cart", "clear_cart", "checkout", "none"]
    product_id: int = 0
    quantity: int = 0
    query: str = ""

class ChatPlan(BaseModel):
    reply: str
    actions: list[ChatAction]

def gemini_plan(message, cart):
    if not GEMINI_API_KEY:
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)
    products = get_products()
    catalog = [
        {"id": p["id"], "name": p["name"], "price": p["price"], "category": p["category"]}
        for p in products
    ]
    prompt = f"""
You are QuickKart's shopping assistant.
The user is shopping for groceries. Convert the user's message into safe shopping actions.

Rules:
- Use ONLY product IDs from the catalog below.
- If the user asks to add a product, use action type "add".
- "remove 1 milk" means remove exactly 1 unit, action "remove", quantity 1.
- "remove milk" means remove the whole matching product, action "remove", quantity 0.
- "make it 3" or "set milk to 3" means "set_qty".
- Multiple requests must become multiple actions.
- For product discovery requests such as "show snacks", use "search" with a useful query.
- For "what is in my cart" use "show_cart".
- For "clear my cart" use "clear_cart".
- For "checkout" use "checkout".
- Never invent a product ID.
- If a product is ambiguous or absent, do not create an action; explain briefly in reply.
- Keep reply concise and friendly.
- This is a demo store. Do not claim real delivery, payment, inventory, or prices beyond the supplied catalog/cart.

Catalog:
{json.dumps(catalog, ensure_ascii=False)}

Current cart:
{json.dumps(cart, ensure_ascii=False)}

User message:
{message}
"""
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ChatPlan,
                temperature=0.2,
            ),
        )
        return ChatPlan.model_validate_json(response.text)
    except Exception:
        return None

def execute_chat_actions(actions):
    cart = cart_dict()
    messages = []
    search_results = None
    checkout_requested = False

    for action in actions:
        if action.type in ("add", "remove", "set_qty") and action.product_id:
            product = get_product(action.product_id)
            if not product:
                continue

            current = cart.get(str(product["id"]), 0)
            if action.type == "add":
                qty = max(1, action.quantity or 1)
                new_qty = min(current + qty, product["stock"])
                cart[str(product["id"])] = new_qty
                messages.append(f"Added {product['name']} × {new_qty - current}.")
            elif action.type == "remove":
                if action.quantity <= 0:
                    removed = current
                    cart.pop(str(product["id"]), None)
                else:
                    removed = min(current, action.quantity)
                    remaining = current - removed
                    if remaining:
                        cart[str(product["id"])] = remaining
                    else:
                        cart.pop(str(product["id"]), None)
                if removed:
                    messages.append(f"Removed {removed} × {product['name']}.")
                else:
                    messages.append(f"{product['name']} is not in your cart.")
            elif action.type == "set_qty":
                qty = max(0, min(action.quantity, product["stock"]))
                if qty:
                    cart[str(product["id"])] = qty
                else:
                    cart.pop(str(product["id"]), None)
                messages.append(f"{product['name']} quantity is now {qty}.")

        elif action.type == "search":
            search_results = get_products(query=action.query)
            messages.append(f"I found {len(search_results)} matching product(s).")
        elif action.type == "show_cart":
            details = cart_details()
            if details["items"]:
                messages.append(
                    f"Your cart has {details['item_count']} item(s) and totals ₹{details['total']:.0f}."
                )
            else:
                messages.append("Your cart is empty.")
        elif action.type == "clear_cart":
            cart = {}
            messages.append("Your cart is now empty.")
        elif action.type == "checkout":
            checkout_requested = True

    save_cart(cart)
    return messages, search_results, checkout_requested

@app.route("/")
def index():
    return render_template("index.html", categories=CATEGORIES)

@app.get("/api/products")
def products_api():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "All").strip()
    return jsonify({"products": get_products(query, category)})

@app.get("/api/products/<int:product_id>")
def product_api(product_id):
    product = get_product(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)

@app.get("/api/cart")
def cart_api():
    return jsonify(cart_details())

@app.post("/api/cart")
def update_cart_api():
    data = request.get_json(silent=True) or {}
    product_id = int(data.get("product_id", 0))
    quantity = int(data.get("quantity", 0))
    product = get_product(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    if quantity < 0 or quantity > product["stock"]:
        return jsonify({"error": "Invalid quantity"}), 400
    cart = cart_dict()
    if quantity == 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = quantity
    save_cart(cart)
    return jsonify(cart_details())

@app.post("/api/coupon")
def coupon_api():
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip().upper()
    valid = {"WELCOME50", "SAVE10"}
    if code not in valid:
        return jsonify({"error": "Invalid coupon code"}), 400
    session["coupon"] = code
    return jsonify(cart_details())

@app.delete("/api/coupon")
def remove_coupon_api():
    session.pop("coupon", None)
    return jsonify(cart_details())

@app.post("/api/orders")
def order_api():
    data = request.get_json(silent=True) or {}
    address = str(data.get("address", "")).strip()
    payment = str(data.get("payment_method", "COD")).strip()
    if not address:
        return jsonify({"error": "Please enter a delivery address"}), 400

    details = cart_details()
    if not details["items"]:
        return jsonify({"error": "Your cart is empty"}), 400

    order_number = "QK" + datetime.now().strftime("%y%m%d%H%M%S")
    conn = get_db()
    conn.execute("""
        INSERT INTO orders
        (order_number, items_json, subtotal, delivery_fee, discount, total,
         address, payment_method, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_number,
        json.dumps(details["items"]),
        details["subtotal"],
        details["delivery_fee"],
        details["discount"],
        details["total"],
        address,
        payment,
        "Placed",
        datetime.now().isoformat(timespec="seconds"),
    ))
    conn.commit()
    conn.close()

    session.pop("cart", None)
    session.pop("coupon", None)
    return jsonify({
        "success": True,
        "order_number": order_number,
        "total": details["total"],
        "message": f"Order {order_number} placed successfully!",
    })

@app.get("/api/orders")
def orders_api():
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"orders": [dict(r) for r in rows]})

@app.post("/api/chat")
def chat_api():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    cart = cart_details()
    plan = gemini_plan(message, cart)

    if plan is None:
        # Safe local fallback so the UI still works without an API key/quota.
        lower = message.lower()
        if any(x in lower for x in ["cart", "basket"]):
            details = cart_details()
            reply = (
                f"Your cart has {details['item_count']} item(s) and totals "
                f"₹{details['total']:.0f}."
                if details["items"] else "Your cart is empty."
            )
            return jsonify({"reply": reply, "cart": details})
        return jsonify({
            "reply": "I couldn't reach the AI assistant right now. You can still use the store normally, or add a Gemini API key in .env.",
            "cart": cart,
        })

    messages, search_results, checkout_requested = execute_chat_actions(plan.actions)
    updated_cart = cart_details()

    if messages:
        reply = " ".join(messages)
        if plan.reply and not any(x in plan.reply.lower() for x in ["added", "removed", "cart"]):
            reply += f" {plan.reply}"
    else:
        reply = plan.reply or "Sure — what would you like to shop for?"

    return jsonify({
        "reply": reply,
        "cart": updated_cart,
        "search_results": search_results,
        "checkout_requested": checkout_requested,
    })

init_db()

if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "true").lower() == "true",
    )
