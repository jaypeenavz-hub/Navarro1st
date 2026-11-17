"""End-to-end functional check of every customer and admin workflow.

Runs against a throwaway SQLite database (instance/test_bytebodega.db) so real data is
never touched:

    .venv/Scripts/python.exe tools/smoke_test.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app  # noqa: E402
from app.db import get_db  # noqa: E402

TEST_DB = os.path.join(ROOT, "instance", "test_bytebodega.db")
RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append((label, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f"  -> {detail}" if detail and not condition else ""))


def contains(response, text):
    return text.lower() in response.get_data(as_text=True).lower()


def run():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    app = create_app({"DATABASE": TEST_DB, "TESTING": False, "WTF_CSRF_ENABLED": False})
    app.config["SERVER_NAME"] = "localhost"

    customer = app.test_client()
    admin = app.test_client()
    anon = app.test_client()

    with app.app_context():
        db = get_db()
        seed_products = db.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
        seed_categories = db.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
        laptop_id = db.execute("SELECT id FROM products WHERE slug = 'lenovo-ideapad-slim-3'"
                             ).fetchone()["id"]
        drive = db.execute("SELECT id, price, stock FROM products WHERE slug = 'samsung-t7-1tb-ssd'"
                           ).fetchone()
        drive_id, drive_price, drive_stock = drive["id"], drive["price"], drive["stock"]
        laptop_category = db.execute("SELECT id FROM categories WHERE slug = 'laptops-tablets'").fetchone()["id"]
        juan_id = db.execute("SELECT id FROM users WHERE username = 'juan'").fetchone()["id"]

    check("Seed catalogue loaded", seed_products >= 34 and seed_categories == 7,
          f"products={seed_products} categories={seed_categories}")

    # ---------------------------------------------------------------- public pages
    for path, label in [("/", "Home page"), ("/shop", "Shop page"), ("/categories", "Categories page"),
                        ("/login", "Login page"), ("/register", "Registration page"),
                        ("/forgot-password", "Forgot password page")]:
        response = anon.get(path)
        check(f"{label} renders", response.status_code == 200, f"status={response.status_code}")

    home = anon.get("/")
    check("Home shows product cards", contains(home, "MacBook Air") and contains(home, "₱"))

    # ------------------------------------------------------------------ auth guard
    guarded = anon.get("/cart")
    check("Guest is redirected from cart to login", guarded.status_code == 302 and "/login" in guarded.headers["Location"])

    # ----------------------------------------------------------------- registration
    weak = customer.post("/register", data={
        "full_name": "Ana Reyes", "username": "ana", "email": "ana@example.com",
        "password": "short", "confirm_password": "short"})
    check("Registration rejects a weak password", weak.status_code == 400 and contains(weak, "at least 8"))

    mismatch = customer.post("/register", data={
        "full_name": "Ana Reyes", "username": "ana", "email": "ana@example.com",
        "password": "Ana@12345", "confirm_password": "Ana@54321"})
    check("Registration rejects mismatched passwords", mismatch.status_code == 400 and contains(mismatch, "do not match"))

    registered = customer.post("/register", data={
        "full_name": "Ana Reyes", "username": "ana", "email": "ana@example.com",
        "password": "Ana@12345", "confirm_password": "Ana@12345"}, follow_redirects=True)
    check("Registration creates the account and logs in",
          registered.status_code == 200 and contains(registered, "Ana"))

    duplicate = app.test_client().post("/register", data={
        "full_name": "Ana Reyes", "username": "ana", "email": "ana@example.com",
        "password": "Ana@12345", "confirm_password": "Ana@12345"})
    check("Registration blocks duplicate username/email", duplicate.status_code == 400)

    customer.post("/logout")

    # ------------------------------------------------------------------------ login
    bad_login = customer.post("/login", data={"identifier": "ana", "password": "WrongPass1"})
    check("Login rejects wrong password", bad_login.status_code == 400 and contains(bad_login, "Incorrect"))

    email_login = customer.post("/login", data={"identifier": "ana@example.com", "password": "Ana@12345",
                                                "remember": "on"}, follow_redirects=True)
    check("Login with email + remember me works", email_login.status_code == 200 and contains(email_login, "Ana"))
    customer.post("/logout")

    good_login = customer.post("/login", data={"identifier": "juan", "password": "Juan@1234"})
    check("Login with username works", good_login.status_code == 302)

    # ------------------------------------------------------------------ search/filter
    search = customer.get("/shop?q=keyboard")
    check("Search filters the catalogue",
          contains(search, "Keychron K2") and not contains(search, "Lenovo IdeaPad Slim 3"))

    category = customer.get("/shop?category=audio-headsets")
    check("Category filter works", contains(category, "HyperX Cloud III") and not contains(category, "Lenovo IdeaPad Slim 3"))

    rating = customer.get("/shop?rating=4&sort=price-asc")
    check("Rating + sort filters work", rating.status_code == 200 and contains(rating, "product-card"))

    empty = customer.get("/shop?q=zzzz-not-a-product")
    check("Empty search shows an empty state", contains(empty, "No products found"))

    detail = customer.get("/shop?q=lenovo")
    check("Product detail link resolves", detail.status_code == 200)

    with app.app_context():
        slug = get_db().execute("SELECT slug FROM products WHERE id = ?", (laptop_id,)).fetchone()["slug"]
    product_page = customer.get(f"/product/{slug}")
    check("Product detail page renders", product_page.status_code == 200 and contains(product_page, "Add to cart"))

    # -------------------------------------------------------------------------- cart
    customer.post(f"/cart/add/{laptop_id}", data={"quantity": "2"})
    cart = customer.get("/cart")
    check("Add to cart works", cart.status_code == 200 and contains(cart, "Lenovo IdeaPad Slim 3"))

    with app.app_context():
        row = get_db().execute("SELECT id, quantity FROM cart_items WHERE product_id = ?", (laptop_id,)).fetchone()
        item_id, quantity = row["id"], row["quantity"]
    check("Cart stores the requested quantity", quantity == 2, f"quantity={quantity}")

    customer.post(f"/cart/update/{item_id}", data={"action": "increase"})
    with app.app_context():
        quantity = get_db().execute("SELECT quantity FROM cart_items WHERE id = ?", (item_id,)).fetchone()["quantity"]
    check("Quantity increase works", quantity == 3, f"quantity={quantity}")

    customer.post(f"/cart/update/{item_id}", data={"action": "decrease"})
    with app.app_context():
        quantity = get_db().execute("SELECT quantity FROM cart_items WHERE id = ?", (item_id,)).fetchone()["quantity"]
    check("Quantity decrease works", quantity == 2, f"quantity={quantity}")

    customer.post(f"/cart/update/{item_id}", data={"action": "set", "quantity": "1"})
    with app.app_context():
        quantity = get_db().execute("SELECT quantity FROM cart_items WHERE id = ?", (item_id,)).fetchone()["quantity"]
    check("Quantity direct input works", quantity == 1, f"quantity={quantity}")

    customer.post(f"/cart/remove/{item_id}")
    with app.app_context():
        remaining = get_db().execute("SELECT COUNT(*) AS n FROM cart_items WHERE user_id = ?",
                                     (juan_id,)).fetchone()["n"]
    check("Remove from cart works", remaining == 0, f"remaining={remaining}")

    # --------------------------------------------------------------------- wishlist
    customer.post(f"/wishlist/toggle/{laptop_id}")
    wishlist = customer.get("/wishlist")
    check("Add to wishlist works", contains(wishlist, "Lenovo IdeaPad Slim 3"))
    customer.post(f"/wishlist/{laptop_id}/to-cart")
    with app.app_context():
        in_cart = get_db().execute("SELECT COUNT(*) AS n FROM cart_items WHERE product_id = ?",
                                   (laptop_id,)).fetchone()["n"]
        in_wishlist = get_db().execute("SELECT COUNT(*) AS n FROM wishlist WHERE product_id = ?",
                                       (laptop_id,)).fetchone()["n"]
    check("Wishlist move-to-cart works", in_cart == 1 and in_wishlist == 0)
    customer.post(f"/cart/clear")

    customer.post(f"/wishlist/toggle/{drive_id}")
    customer.post(f"/wishlist/toggle/{drive_id}")
    with app.app_context():
        still_saved = get_db().execute("SELECT COUNT(*) AS n FROM wishlist WHERE product_id = ?",
                                       (drive_id,)).fetchone()["n"]
    check("Remove from wishlist works", still_saved == 0)

    # --------------------------------------------------------------------- checkout
    empty_checkout = customer.get("/checkout")
    check("Empty cart blocks checkout", empty_checkout.status_code == 302)

    customer.post(f"/cart/add/{drive_id}", data={"quantity": "2"})
    checkout_page = customer.get("/checkout")
    check("Checkout page renders with prefilled profile",
          checkout_page.status_code == 200 and contains(checkout_page, "Place order"))

    invalid = customer.post("/checkout", data={
        "full_name": "Juan Dela Cruz", "phone": "123", "address": "88 Katipunan Ave",
        "city": "Quezon City", "province": "Metro Manila", "postal_code": "1108",
        "payment_method": "cod", "notes": ""})
    check("Checkout validates the contact number", invalid.status_code == 400 and contains(invalid, "contact number"))

    placed = customer.post("/checkout", data={
        "full_name": "Juan Dela Cruz", "phone": "0917 555 0142",
        "address": "88 Katipunan Avenue, Brgy. Loyola Heights", "city": "Quezon City",
        "province": "Metro Manila", "postal_code": "1108",
        "payment_method": "cod", "notes": "Leave with the guard"}, follow_redirects=True)
    check("Place order succeeds and shows confirmation",
          placed.status_code == 200 and contains(placed, "Order confirmed"))

    with app.app_context():
        db = get_db()
        order = db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1").fetchone()
        order_id, order_number = order["id"], order["order_number"]
        items = db.execute("SELECT COUNT(*) AS n FROM order_items WHERE order_id = ?", (order_id,)).fetchone()["n"]
        cart_left = db.execute("SELECT COUNT(*) AS n FROM cart_items WHERE user_id = ?", (juan_id,)).fetchone()["n"]
        stock_now = db.execute("SELECT stock FROM products WHERE id = ?", (drive_id,)).fetchone()["stock"]
        transaction = db.execute("SELECT * FROM transactions WHERE order_id = ?", (order_id,)).fetchone()
        expected_subtotal = round(drive_price * 2, 2)
        expected_shipping = 0.0 if expected_subtotal >= 2500 else 79.0

    check("Order total is calculated correctly",
          abs(order["subtotal"] - expected_subtotal) < 0.01
          and abs(order["shipping_fee"] - expected_shipping) < 0.01
          and abs(order["total"] - (expected_subtotal + expected_shipping)) < 0.01,
          f"subtotal={order['subtotal']} shipping={order['shipping_fee']} total={order['total']}")
    check("Order lines and payment transaction saved", items == 1 and transaction is not None)
    check("Stock is reduced after checkout", stock_now == drive_stock - 2)
    check("Cart is emptied after checkout", cart_left == 0)

    # ----------------------------------------------------------------------- orders
    history = customer.get("/orders")
    check("Order history lists the new order",
          history.status_code == 200 and contains(history, order_number),
          f"status={history.status_code}")
    filtered = customer.get("/orders?status=pending")
    check("Order status filter works", filtered.status_code == 200 and contains(filtered, order_number))
    other_status = customer.get("/orders?status=delivered")
    check("Order filter hides non-matching orders", not contains(other_status, order_number))

    order_page = customer.get(f"/orders/{order_number}")
    check("Order detail page renders", order_page.status_code == 200 and contains(order_page, "Cancel this order"))

    cancelled = customer.post(f"/orders/{order_number}/cancel", follow_redirects=True)
    check("Customer can cancel an eligible order", contains(cancelled, "Cancelled"))
    with app.app_context():
        db = get_db()
        status = db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()["status"]
        restored = db.execute("SELECT stock FROM products WHERE id = ?", (drive_id,)).fetchone()["stock"]
    check("Cancellation restores stock", status == "cancelled" and restored == drive_stock)

    recancel = customer.post(f"/orders/{order_number}/cancel", follow_redirects=True)
    check("Delivered/ineligible orders cannot be cancelled again", contains(recancel, "can no longer be cancelled"))

    # ---------------------------------------------------------------------- profile
    updated = customer.post("/profile", data={
        "full_name": "Juan P. Dela Cruz", "username": "juan", "email": "juan@example.com",
        "phone": "0917 555 0142", "address": "12 Mabini Street", "city": "Pasig City",
        "province": "Metro Manila", "postal_code": "1600"}, follow_redirects=True)
    check("Profile editing saves changes",
          contains(updated, "Profile updated successfully") and contains(updated, "Juan P. Dela Cruz"))

    bad_email = customer.post("/profile", data={
        "full_name": "Juan P. Dela Cruz", "username": "juan", "email": "not-an-email",
        "phone": "", "address": "", "city": "", "province": "", "postal_code": ""})
    check("Profile validation rejects a bad email", bad_email.status_code == 400 and contains(bad_email, "valid email"))

    wrong_current = customer.post("/profile/password", data={
        "current_password": "nope", "new_password": "Juan@9999", "confirm_password": "Juan@9999"},
        follow_redirects=True)
    check("Change password checks the current password", contains(wrong_current, "current password is not correct"))

    changed = customer.post("/profile/password", data={
        "current_password": "Juan@1234", "new_password": "Juan@9999",
        "confirm_password": "Juan@9999"}, follow_redirects=True)
    check("Change password succeeds", contains(changed, "Password changed successfully"))

    customer.post("/logout")
    relogin = customer.post("/login", data={"identifier": "juan", "password": "Juan@9999"})
    check("New password can be used to log in", relogin.status_code == 302)

    # --------------------------------------------------------------- notifications
    notifications = customer.get("/notifications")
    check("Notifications page lists order updates",
          notifications.status_code == 200 and contains(notifications, "Order"))
    customer.post("/notifications/read-all", follow_redirects=True)
    with app.app_context():
        unread = get_db().execute("SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND is_read = 0",
                                  (juan_id,)).fetchone()["n"]
    check("Mark-all-read works", unread == 0, f"unread={unread}")

    # ------------------------------------------------------------- forgot password
    forgot = app.test_client().post("/forgot-password", data={"email": "juan@example.com"})
    check("Forgot password generates a reset code", forgot.status_code == 302)
    with app.app_context():
        code = get_db().execute("SELECT reset_code FROM users WHERE username = 'juan'").fetchone()["reset_code"]
    reset_client = app.test_client()
    bad_code = reset_client.post("/reset-password", data={
        "email": "juan@example.com", "code": "000000",
        "password": "Reset@1234", "confirm_password": "Reset@1234"})
    check("Reset rejects an incorrect code", bad_code.status_code == 400)
    reset_ok = reset_client.post("/reset-password", data={
        "email": "juan@example.com", "code": code,
        "password": "Reset@1234", "confirm_password": "Reset@1234"}, follow_redirects=True)
    check("Password reset completes", contains(reset_ok, "Password updated"))
    reset_login = reset_client.post("/login", data={"identifier": "juan", "password": "Reset@1234"})
    check("Reset password can be used to log in", reset_login.status_code == 302)

    # ------------------------------------------------------------------ admin access
    blocked = customer.get("/admin/")
    check("Customers are kept out of the admin area", blocked.status_code == 302 and "/admin" not in blocked.headers["Location"])

    admin_login = admin.post("/login", data={"identifier": "admin", "password": "Admin@123"})
    check("Admin login redirects to the dashboard", admin_login.status_code == 302 and "admin" in admin_login.headers["Location"])

    dashboard = admin.get("/admin/")
    check("Admin dashboard renders totals",
          dashboard.status_code == 200 and contains(dashboard, "Total products") and contains(dashboard, "Total sales"))

    products_page = admin.get("/admin/products")
    check("Admin product list renders", products_page.status_code == 200 and contains(products_page, "Add new product"))

    new_product = admin.post("/admin/products/new", data={
        "name": "Test USB-C Dock", "category_id": str(laptop_category), "price": "1299.50",
        "stock": "7", "description": "A compact USB-C dock used only by the automated check.",
        "rating": "4.5", "rating_count": "12", "badge": "Test",
        "image_url": "img/products/samsung-t7-1tb-ssd.jpg"}, follow_redirects=True)
    check("Admin can add a product", contains(new_product, "added to the catalogue"))
    with app.app_context():
        created = get_db().execute("SELECT * FROM products WHERE name = 'Test USB-C Dock'").fetchone()
    check("New product is persisted with a price", created is not None and abs(created["price"] - 1299.50) < 0.01)
    new_product_id = created["id"]

    edited = admin.post(f"/admin/products/{new_product_id}/edit", data={
        "name": "Test USB-C Dock Pro", "category_id": str(laptop_category), "price": "1499.00",
        "stock": "9", "description": "Updated description for the automated admin check.",
        "rating": "4.6", "rating_count": "14", "badge": "", "image_url": ""}, follow_redirects=True)
    check("Admin can edit a product", contains(edited, "Product updated"))
    with app.app_context():
        edited_row = get_db().execute("SELECT * FROM products WHERE id = ?", (new_product_id,)).fetchone()
    check("Edited values are saved", edited_row["name"] == "Test USB-C Dock Pro" and edited_row["stock"] == 9)

    invalid_product = admin.post("/admin/products/new", data={
        "name": "X", "category_id": "", "price": "abc", "stock": "-2", "description": "short",
        "rating": "9", "rating_count": "0", "badge": "", "image_url": ""})
    check("Admin product form validates input", invalid_product.status_code == 400)

    toggled = admin.post(f"/admin/products/{new_product_id}/toggle", follow_redirects=True)
    check("Admin can hide a product", contains(toggled, "hidden in the shop"))

    deleted = admin.post(f"/admin/products/{new_product_id}/delete", follow_redirects=True)
    with app.app_context():
        gone = get_db().execute("SELECT COUNT(*) AS n FROM products WHERE id = ?", (new_product_id,)).fetchone()["n"]
    check("Admin can delete a product", contains(deleted, "deleted from the catalogue") and gone == 0)

    # ------------------------------------------------------------------- categories
    created_category = admin.post("/admin/categories", data={
        "name": "Smart Home Gear", "description": "Sensors, plugs and home automation add-ons."}, follow_redirects=True)
    check("Admin can create a category", contains(created_category, "created"))
    with app.app_context():
        category = get_db().execute("SELECT * FROM categories WHERE name = 'Smart Home Gear'").fetchone()
    category_id = category["id"]

    renamed = admin.post(f"/admin/categories/{category_id}/edit", data={
        "name": "Smart Home and IoT", "description": "Updated category description."}, follow_redirects=True)
    check("Admin can rename a category", contains(renamed, "Category updated"))

    deleted_category = admin.post(f"/admin/categories/{category_id}/delete", follow_redirects=True)
    check("Admin can delete an empty category", contains(deleted_category, "Category deleted"))

    blocked_delete = admin.post(f"/admin/categories/{laptop_category}/delete", follow_redirects=True)
    check("Categories with products are protected", contains(blocked_delete, "Move or delete"))

    # -------------------------------------------------------------------- customers
    customers_page = admin.get("/admin/customers")
    check("Admin customer list renders", customers_page.status_code == 200 and contains(customers_page, "juan"))

    with app.app_context():
        ana_id = get_db().execute("SELECT id FROM users WHERE username = 'ana'").fetchone()["id"]
    admin.post(f"/admin/customers/{ana_id}/toggle")
    with app.app_context():
        ana_active = get_db().execute("SELECT is_active FROM users WHERE id = ?", (ana_id,)).fetchone()["is_active"]
    check("Admin can deactivate a customer", ana_active == 0)
    inactive_login = app.test_client().post("/login", data={"identifier": "ana", "password": "Ana@12345"})
    check("Deactivated customers cannot log in", inactive_login.status_code == 400 and contains(inactive_login, "deactivated"))
    admin.post(f"/admin/customers/{ana_id}/toggle")
    with app.app_context():
        ana_active = get_db().execute("SELECT is_active FROM users WHERE id = ?", (ana_id,)).fetchone()["is_active"]
    check("Admin can reactivate a customer", ana_active == 1)

    # ---------------------------------------------------------------------- orders
    customer.post("/login", data={"identifier": "juan", "password": "Reset@1234"})
    customer.post(f"/cart/add/{drive_id}", data={"quantity": "1"})
    customer.post("/checkout", data={
        "full_name": "Juan Dela Cruz", "phone": "0917 555 0142", "address": "12 Mabini Street",
        "city": "Pasig City", "province": "Metro Manila", "postal_code": "1600",
        "payment_method": "gcash", "notes": ""})
    with app.app_context():
        db = get_db()
        live_order = db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1").fetchone()
        live_id, live_number = live_order["id"], live_order["order_number"]
        paid = db.execute("SELECT status FROM transactions WHERE order_id = ?", (live_id,)).fetchone()["status"]

    check("GCash demo order records a paid transaction", paid == "paid", f"status={paid}")

    admin_orders = admin.get("/admin/orders")
    check("Admin order list renders", admin_orders.status_code == 200 and contains(admin_orders, live_number))

    admin_order_page = admin.get(f"/admin/orders/{live_id}")
    check("Admin order detail renders", admin_order_page.status_code == 200 and contains(admin_order_page, "Update order status"))

    admin.post(f"/admin/orders/{live_id}/status", data={"status": "processing"})
    admin.post(f"/admin/orders/{live_id}/status", data={"status": "shipped"})
    admin.post(f"/admin/orders/{live_id}/status", data={"status": "delivered"})
    with app.app_context():
        db = get_db()
        final_status = db.execute("SELECT status FROM orders WHERE id = ?", (live_id,)).fetchone()["status"]
        paid = db.execute("SELECT status FROM transactions WHERE order_id = ?", (live_id,)).fetchone()["status"]
        notified = db.execute("SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND message LIKE '%delivered%'",
                              (juan_id,)).fetchone()["n"]
    check("Admin can progress an order to delivered", final_status == "delivered", f"status={final_status}")
    check("Delivery marks the payment as paid", paid == "paid")
    check("Status changes notify the customer", notified >= 1, f"notifications={notified}")

    illegal = admin.post(f"/admin/orders/{live_id}/status", data={"status": "processing"}, follow_redirects=True)
    check("Illegal status transitions are refused", contains(illegal, "cannot move to"))

    reports = admin.get("/admin/reports")
    check("Sales report renders revenue figures",
          reports.status_code == 200 and contains(reports, "Gross sales") and contains(reports, "₱"))

    # ----------------------------------------------------------------------- logout
    admin.post("/logout")
    after_logout = admin.get("/admin/", follow_redirects=False)
    check("Logout returns to the login page", after_logout.status_code == 302 and "/login" in after_logout.headers["Location"])
    logged_out_page = admin.get("/login")
    check("Login page is reachable after logout", logged_out_page.status_code == 200)

    missing = anon.get("/this-page-does-not-exist")
    check("Unknown pages show the 404 screen", missing.status_code == 404 and contains(missing, "Page not found"))

    # -------------------------------------------------------------------- summary
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{passed}/{total} checks passed")
    failures = [label for label, ok, _ in RESULTS if not ok]
    if failures:
        print("Failed checks:")
        for label in failures:
            print(f"  - {label}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(run())
