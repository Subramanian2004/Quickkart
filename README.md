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
g.
12. Deploy with Gunicorn + a cloud platform.
