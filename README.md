# QuickKart — Flask Grocery Store + AI Shopping Assistant

A beginner-friendly Zepto-style grocery shopping project built with:

- HTML
- CSS
- Vanilla JavaScript
- Python
- Flask
- SQLite
- Google Gemini API (free tier model)

## Features in this version

### Store
- Search products
- Category filtering
- Product cards
- Product detail modal
- Add / remove / change quantity
- Cart side panel
- Wishlist using localStorage
- Coupons:
  - `WELCOME50` — ₹50 off when subtotal is at least ₹299
  - `SAVE10` — 10% off when subtotal is at least ₹499
- Checkout
- Cash on Delivery
- Demo online payment option
- Order history
- Responsive design
- Emoji placeholders instead of real product images

### AI Shopping Assistant
The right-side panel is connected to the Gemini API.

Examples:
- `add 2 milk`
- `add 2 kg atta`
- `add bread and 6 eggs`
- `remove 1 dettol soap`
- `remove all milk`
- `set milk to 3`
- `show me snacks`
- `what is in my cart?`
- `clear my cart`
- `checkout`

The AI returns structured actions. Flask validates and executes those actions against the real product catalog/cart.

## VS Code setup

### 1. Open the project

Open the `quickkart` folder in VS Code.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install packages

```bash
pip install -r requirements.txt
```

### 4. Create `.env`

Copy `.env.example` to `.env`.

Put your Gemini API key here:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

### 5. Run

```bash
python app.py
```

Open:

http://127.0.0.1:5000

SQLite database `quickkart.db` is created automatically.

## Gemini API

This project keeps the API key on the Flask server. Do NOT put the key inside JavaScript.

If you don't configure `GEMINI_API_KEY`, the store still works and the chatbot falls back to a limited local response.

The selected model is `gemini-2.5-flash-lite`, which currently has a free tier. Free-tier quotas can change, so check Google's current Gemini API pricing/rate-limit pages if you hit quota errors.

## Suggested next upgrades

1. Replace emoji with product images.
2. Add real authentication.
3. Add admin dashboard.
4. Add PostgreSQL/MySQL.
5. Add address management.
6. Add Razorpay/Stripe.
7. Add real delivery slots.
8. Add product variants.
9. Add inventory management.
10. Add AI function calling / tool orchestration.
11. Add order tracking.
12. Deploy with Gunicorn + a cloud platform.
