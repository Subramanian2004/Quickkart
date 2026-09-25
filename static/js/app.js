let activeCategory = "All";
let currentProducts = [];
let wishlist = JSON.parse(localStorage.getItem("quickkart-wishlist") || "[]");

const $ = (s) => document.querySelector(s);

async function api(url, options = {}) {
    const res = await fetch(url, {
        headers: {"Content-Type": "application/json"},
        ...options
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong");
    return data;
}

function money(v) { return `₹${Number(v).toFixed(0)}`; }

function showToast(message) {
    const el = $("#toast");
    el.textContent = message;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2200);
}

async function loadProducts() {
    const q = $("#searchInput").value.trim();
    $("#clearSearch").style.display = q ? "block" : "none";
    const data = await api(`/api/products?q=${encodeURIComponent(q)}&category=${encodeURIComponent(activeCategory)}`);
    currentProducts = data.products;
    renderProducts(data.products);
}

function renderProducts(products) {
    $("#productHeading").textContent = activeCategory === "All" ? "Popular groceries" : activeCategory;
    $("#resultCount").textContent = `${products.length} products`;
    $("#emptyState").classList.toggle("hidden", products.length !== 0);
    $("#productsGrid").innerHTML = products.map(p => {
        const qty = cartQuantity(p.id);
        const wished = wishlist.includes(p.id);
        return `
        <article class="product-card">
            <div class="product-image" onclick="openProduct(${p.id})">
                <button class="wish-btn ${wished ? "active" : ""}" onclick="event.stopPropagation(); toggleWishlist(${p.id})">${wished ? "♥" : "♡"}</button>
                ${p.emoji}
            </div>
            <h3 onclick="openProduct(${p.id})">${p.name}</h3>
            <p class="rating"><b>★ ${p.rating}</b> · ${p.reviews} reviews</p>
            <div class="price-row">
                <div class="price">${money(p.price)} <span class="mrp">${money(p.mrp)}</span></div>
                ${qty ? qtyControl(p.id, qty) : `<button class="add-btn" onclick="changeCart(${p.id},1)">Add</button>`}
            </div>
        </article>`;
    }).join("");
}

let cachedCart = {items: []};

function cartQuantity(id) {
    const item = cachedCart.items?.find(x => x.id === id);
    return item ? item.quantity : 0;
}

function qtyControl(id, qty) {
    return `<div class="qty-control"><button onclick="changeCart(${id},${qty-1})">−</button><b>${qty}</b><button onclick="changeCart(${id},${qty+1})">+</button></div>`;
}

async function refreshCart() {
    cachedCart = await api("/api/cart");
    $("#cartCount").textContent = cachedCart.item_count;
    renderProducts(currentProducts);
    renderCart();
}

async function changeCart(id, qty) {
    try {
        await api("/api/cart", {
            method: "POST",
            body: JSON.stringify({product_id: id, quantity: qty})
        });
        await refreshCart();
        if (qty > 0) showToast("Cart updated");
    } catch (e) { showToast(e.message); }
}

function renderCart() {
    const body = $("#cartBody");
    if (!cachedCart.items?.length) {
        body.innerHTML = `<div class="empty-state"><div>🛒</div><h3>Your cart is empty</h3><p>Add a few groceries and they will appear here.</p></div>`;
        return;
    }
    body.innerHTML = `
        ${cachedCart.items.map(item => `
            <div class="cart-item">
                <div class="thumb">${item.emoji}</div>
                <div>
                    <h4>${item.name}</h4>
                    <p>${money(item.price)} × ${item.quantity}</p>
                    <div class="mini-qty">
                        <button onclick="changeCart(${item.id},${item.quantity-1})">−</button>
                        <b>${item.quantity}</b>
                        <button onclick="changeCart(${item.id},${item.quantity+1})">+</button>
                    </div>
                </div>
                <b>${money(item.line_total)}</b>
            </div>`).join("")}
        <div class="coupon-row">
            <input id="couponInput" placeholder="Coupon: WELCOME50">
            <button onclick="applyCoupon()">Apply</button>
        </div>
        ${cachedCart.coupon ? `<div style="font-size:12px;color:#087f5b">Coupon ${cachedCart.coupon} applied.</div>` : ""}
        <div class="cart-summary">
            <div class="summary-line"><span>Subtotal</span><b>${money(cachedCart.subtotal)}</b></div>
            <div class="summary-line"><span>Delivery</span><b>${cachedCart.delivery_fee ? money(cachedCart.delivery_fee) : "FREE"}</b></div>
            <div class="summary-line"><span>Discount</span><b>−${money(cachedCart.discount)}</b></div>
            <div class="summary-line total"><span>Total</span><b>${money(cachedCart.total)}</b></div>
            <button class="primary-btn checkout-btn" onclick="openCheckout()">Proceed to checkout</button>
        </div>`;
}

async function applyCoupon() {
    const code = $("#couponInput").value.trim();
    if (!code) return;
    try {
        await api("/api/coupon", {method:"POST", body:JSON.stringify({code})});
        await refreshCart();
        showToast("Coupon applied");
    } catch (e) { showToast(e.message); }
}

function toggleWishlist(id) {
    wishlist = wishlist.includes(id) ? wishlist.filter(x => x !== id) : [...wishlist, id];
    localStorage.setItem("quickkart-wishlist", JSON.stringify(wishlist));
    renderProducts(currentProducts);
}

async function openProduct(id) {
    const p = await api(`/api/products/${id}`);
    $("#productModalBody").innerHTML = `
        <button class="modal-close" onclick="closeProduct()">×</button>
        <div class="product-detail">
            <div class="detail-image">${p.emoji}</div>
            <div>
                <p class="eyebrow">${p.category}</p>
                <h2>${p.name}</h2>
                <p class="rating"><b>★ ${p.rating}</b> · ${p.reviews} reviews</p>
                <div class="detail-price">${money(p.price)} <span class="mrp">${money(p.mrp)}</span></div>
                <p style="color:#68756f;font-size:13px;line-height:1.6">Fresh everyday essential available for quick ordering.</p>
                <button class="primary-btn" onclick="changeCart(${p.id}, ${cartQuantity(p.id)+1}); closeProduct()">Add to cart</button>
            </div>
        </div>`;
    $("#productModal").classList.remove("hidden");
}
function closeProduct() { $("#productModal").classList.add("hidden"); }

function openPanel(id) {
    closePanels();
    $("#overlay").classList.remove("hidden");
    $(id).classList.add("open");
}
function closePanels() {
    document.querySelectorAll(".side-panel").forEach(x => x.classList.remove("open"));
    $("#overlay").classList.add("hidden");
}
function openChat() {
    openPanel("#chatPanel");
    setTimeout(() => $("#chatInput").focus(), 250);
}
function openCart() {
    openPanel("#cartPanel");
    refreshCart();
}
function scrollToProducts() { $("#productsSection").scrollIntoView({behavior:"smooth"}); }
function useSuggestion(text) { $("#chatInput").value = text; sendChat(); }

async function sendChat() {
    const input = $("#chatInput");
    const message = input.value.trim();
    if (!message) return;
    addChatMessage(message, true);
    input.value = "";
    const loading = addChatMessage("Thinking…", false, true);
    try {
        const data = await api("/api/chat", {method:"POST", body:JSON.stringify({message})});
        loading.remove();
        addChatMessage(data.reply, false);
        await refreshCart();
        if (data.search_results?.length) {
            const names = data.search_results.slice(0,5).map(x => `• ${x.name} — ${money(x.price)}`).join("<br>");
            addChatMessage(`Here are a few matches:<br>${names}`, false);
        }
        if (data.checkout_requested) openCheckout();
    } catch (e) {
        loading.remove();
        addChatMessage("Sorry, I couldn't process that right now. Please try again.", false);
    }
}

function addChatMessage(text, user=false, loading=false) {
    const wrap = document.createElement("div");
    wrap.className = `chat-message ${user ? "user" : "bot"}`;
    wrap.innerHTML = user
        ? `<div class="bubble">${escapeHtml(text)}</div>`
        : `<div class="message-avatar">✨</div><div class="bubble">${loading ? `<span>${escapeHtml(text)}</span>` : text}</div>`;
    $("#chatMessages").appendChild(wrap);
    $("#chatMessages").scrollTop = $("#chatMessages").scrollHeight;
    return wrap;
}
function escapeHtml(str) {
    return str.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

async function openOrders() {
    openPanel("#ordersPanel");
    const data = await api("/api/orders");
    $("#ordersBody").innerHTML = data.orders.length ? data.orders.map(o => `
        <div class="order-card">
            <strong>${o.order_number}</strong>
            <small>${new Date(o.created_at).toLocaleString()} · ${o.status}</small>
            <div class="order-total">${money(o.total)}</div>
            <small>${o.payment_method} · ${escapeHtml(o.address)}</small>
        </div>`).join("") : `<div class="empty-state"><div>📦</div><h3>No orders yet</h3><p>Your placed orders will appear here.</p></div>`;
}

function openCheckout() {
    if (!cachedCart.items?.length) return showToast("Your cart is empty");
    $("#checkoutSummary").innerHTML = `
        <div class="cart-summary">
            <div class="summary-line"><span>${cachedCart.item_count} item(s)</span><b>${money(cachedCart.subtotal)}</b></div>
            <div class="summary-line"><span>Delivery</span><b>${cachedCart.delivery_fee ? money(cachedCart.delivery_fee) : "FREE"}</b></div>
            <div class="summary-line total"><span>Pay</span><b>${money(cachedCart.total)}</b></div>
        </div>`;
    $("#checkoutModal").classList.remove("hidden");
}
function closeCheckout() { $("#checkoutModal").classList.add("hidden"); }

async function placeOrder() {
    const address = $("#addressInput").value.trim();
    const payment_method = $("#paymentMethod").value;
    try {
        const data = await api("/api/orders", {method:"POST", body:JSON.stringify({address, payment_method})});
        closeCheckout();
        closePanels();
        await refreshCart();
        showToast(data.message);
        setTimeout(openOrders, 700);
    } catch (e) { showToast(e.message); }
}

$("#searchInput").addEventListener("input", loadProducts);
$("#clearSearch").addEventListener("click", () => { $("#searchInput").value=""; loadProducts(); });
$("#cartBtn").addEventListener("click", openCart);
$("#ordersBtn").addEventListener("click", openOrders);
$("#overlay").addEventListener("click", closePanels);
$("#chatSend").addEventListener("click", sendChat);
$("#chatInput").addEventListener("keydown", e => { if (e.key === "Enter") sendChat(); });
$("#placeOrderBtn").addEventListener("click", placeOrder);

document.querySelectorAll(".category-chip").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".category-chip").forEach(x => x.classList.remove("active"));
        btn.classList.add("active");
        activeCategory = btn.dataset.category;
        loadProducts();
    });
});

window.addEventListener("keydown", e => {
    if (e.key === "Escape") { closePanels(); closeCheckout(); closeProduct(); }
});

refreshCart().then(loadProducts);
