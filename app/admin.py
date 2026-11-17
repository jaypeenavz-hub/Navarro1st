"""Administrator interface: catalog, orders, customers and sales reports."""

import os
import re
from datetime import datetime, timedelta
from uuid import uuid4

from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, url_for)

from .db import get_db
from .services import admin_required, notify, now_iso, paginate

bp = Blueprint("admin", __name__, url_prefix="/admin")

STATUS_LABELS = {
    "pending": "Pending",
    "processing": "Processing",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}

NEXT_STATUS = {
    "pending": ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped": ["delivered"],
    "delivered": [],
    "cancelled": [],
}


@bp.before_request
@admin_required
def require_admin():
    return None


def _slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug or "item"


def _unique_product_slug(db, base, ignore_id=None):
    slug, counter = base, 2
    while db.execute("SELECT 1 FROM products WHERE slug = ? AND id != ?",
                     (slug, ignore_id or -1)).fetchone():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _store_upload(file_storage):
    filename = getattr(file_storage, "filename", "") or ""
    if not filename:
        return None
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return None
    unique_name = f"{uuid4().hex}.{extension}"
    file_storage.save(os.path.join(current_app.config["UPLOAD_DIR"], unique_name))
    return f"uploads/products/{unique_name}"


# --------------------------------------------------------------------- dashboard

@bp.route("/")
def dashboard():
    db = get_db()
    totals = {
        "products": db.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"],
        "customers": db.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'customer'").fetchone()["n"],
        "orders": db.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"],
        "sales": db.execute("SELECT COALESCE(SUM(total), 0) AS n FROM orders "
                            "WHERE status != 'cancelled'").fetchone()["n"],
    }
    status_counts = {key: 0 for key in STATUS_LABELS}
    for row in db.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status").fetchall():
        status_counts[row["status"]] = row["n"]

    recent_orders = db.execute(
        """SELECT o.*, u.full_name AS customer_name FROM orders o
           JOIN users u ON u.id = o.user_id ORDER BY o.id DESC LIMIT 6"""
    ).fetchall()
    low_stock = db.execute(
        "SELECT * FROM products WHERE is_active = 1 AND stock <= 6 ORDER BY stock ASC, name ASC LIMIT 5"
    ).fetchall()

    today = datetime.now().date()
    sales_series = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        key = day.strftime("%Y-%m-%d")
        row = db.execute(
            "SELECT COALESCE(SUM(total), 0) AS revenue FROM orders "
            "WHERE status != 'cancelled' AND substr(created_at, 1, 10) = ?", (key,)
        ).fetchone()
        sales_series.append({"label": day.strftime("%a"), "revenue": float(row["revenue"])})
    peak = max([entry["revenue"] for entry in sales_series] + [1.0])
    for entry in sales_series:
        entry["height"] = round((entry["revenue"] / peak) * 100, 1)

    return render_template("admin/dashboard.html", totals=totals, status_counts=status_counts,
                           recent_orders=recent_orders, low_stock=low_stock,
                           sales_series=sales_series, admin_section="dashboard",
                           status_labels=STATUS_LABELS)


# ---------------------------------------------------------------------- products

@bp.route("/products")
def products():
    db = get_db()
    query = request.args.get("q", "").strip()
    category_id = request.args.get("category", "").strip()
    page = request.args.get("page", "1")
    page = int(page) if page.isdigit() else 1

    conditions = ["1 = 1"]
    params = []
    if query:
        conditions.append("(p.name LIKE ? OR p.description LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if category_id.isdigit():
        conditions.append("p.category_id = ?")
        params.append(int(category_id))
    where = " WHERE " + " AND ".join(conditions)

    total = db.execute(f"SELECT COUNT(*) AS n FROM products p{where}", params).fetchone()["n"]
    pager = paginate(total, page, current_app.config["ITEMS_PER_PAGE"])
    rows = db.execute(
        f"""SELECT p.*, c.name AS category_name FROM products p
            LEFT JOIN categories c ON c.id = p.category_id{where}
            ORDER BY p.id DESC LIMIT ? OFFSET ?""",
        params + [pager["per_page"], pager["offset"]],
    ).fetchall()
    categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render_template("admin/products.html", products=rows, categories=categories,
                           query=query, category=category_id, pager=pager,
                           admin_section="products")


def _product_form_values(form):
    return {
        "name": form.get("name", "").strip(),
        "category_id": form.get("category_id", ""),
        "price": form.get("price", "").strip(),
        "stock": form.get("stock", "").strip(),
        "description": form.get("description", "").strip(),
        "rating": form.get("rating", "0").strip() or "0",
        "rating_count": form.get("rating_count", "0").strip() or "0",
        "badge": form.get("badge", "").strip(),
        "image_url": form.get("image_url", "").strip(),
    }


def _validate_product(db, values):
    errors = []
    if len(values["name"]) < 3:
        errors.append("Product name must be at least 3 characters.")
    if not values["category_id"].isdigit() or db.execute(
            "SELECT 1 FROM categories WHERE id = ?", (int(values["category_id"]),)).fetchone() is None:
        errors.append("Choose a valid category.")
    try:
        price = float(values["price"])
        if price <= 0:
            errors.append("Price must be greater than zero.")
    except ValueError:
        errors.append("Enter a valid price.")
        price = 0
    try:
        stock = int(values["stock"])
        if stock < 0:
            errors.append("Stock cannot be negative.")
    except ValueError:
        errors.append("Enter stock as a whole number.")
        stock = 0
    try:
        rating = float(values["rating"])
        if not 0 <= rating <= 5:
            errors.append("Rating must be between 0 and 5.")
    except ValueError:
        errors.append("Enter a rating between 0 and 5.")
        rating = 0
    try:
        rating_count = int(values["rating_count"])
        if rating_count < 0:
            errors.append("Review count cannot be negative.")
    except ValueError:
        errors.append("Enter review count as a whole number.")
        rating_count = 0
    if len(values["description"]) < 10:
        errors.append("Write a short description (at least 10 characters).")
    if values["image_url"] and not values["image_url"].lower().startswith(
            ("http://", "https://", "img/", "uploads/")):
        errors.append("Image link must start with http(s):// or be an uploaded file.")
    return errors, price, stock, rating, rating_count


@bp.route("/products/new", methods=["GET", "POST"])
def product_new():
    db = get_db()
    categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if not categories:
        flash("Create a category before adding products.", "error")
        return redirect(url_for("admin.categories"))

    if request.method == "POST":
        values = _product_form_values(request.form)
        errors, price, stock, rating, rating_count = _validate_product(db, values)
        uploaded = _store_upload(request.files.get("image_file"))
        if not uploaded and not values["image_url"]:
            errors.append("Upload a product photo or paste an image link.")
        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("admin/product_form.html", values=values, categories=categories,
                                   product=None, admin_section="products"), 400

        image = uploaded or values["image_url"]
        slug = _unique_product_slug(db, _slugify(values["name"]))
        db.execute(
            """INSERT INTO products (name, slug, category_id, price, description, stock, rating,
                                     rating_count, image, badge, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (values["name"], slug, int(values["category_id"]), price, values["description"], stock,
             rating, rating_count, image, values["badge"], now_iso()),
        )
        db.commit()
        flash(f"{values['name']} added to the catalogue.", "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", values={}, categories=categories,
                           product=None, admin_section="products")


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def product_edit(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        flash("Product not found.", "error")
        return redirect(url_for("admin.products"))
    categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()

    if request.method == "POST":
        values = _product_form_values(request.form)
        errors, price, stock, rating, rating_count = _validate_product(db, values)
        uploaded = _store_upload(request.files.get("image_file"))
        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("admin/product_form.html", values=values, categories=categories,
                                   product=product, admin_section="products"), 400

        image = uploaded or values["image_url"] or product["image"]
        slug = _unique_product_slug(db, _slugify(values["name"]), ignore_id=product_id)
        db.execute(
            """UPDATE products SET name = ?, slug = ?, category_id = ?, price = ?, description = ?,
                   stock = ?, rating = ?, rating_count = ?, image = ?, badge = ? WHERE id = ?""",
            (values["name"], slug, int(values["category_id"]), price, values["description"], stock,
             rating, rating_count, image, values["badge"], product_id),
        )
        db.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin.products"))

    values = {
        "name": product["name"],
        "category_id": str(product["category_id"] or ""),
        "price": f"{product['price']:.2f}",
        "stock": str(product["stock"]),
        "description": product["description"],
        "rating": f"{product['rating']:.1f}",
        "rating_count": str(product["rating_count"]),
        "badge": product["badge"],
        "image_url": product["image"] if not product["image"].startswith("uploads/") else "",
    }
    return render_template("admin/product_form.html", values=values, categories=categories,
                           product=product, admin_section="products")


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
def product_delete(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        flash("Product not found.", "error")
        return redirect(url_for("admin.products"))
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    flash(f"{product['name']} deleted from the catalogue.", "info")
    return redirect(url_for("admin.products"))


@bp.route("/products/<int:product_id>/toggle", methods=["POST"])
def product_toggle(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        flash("Product not found.", "error")
        return redirect(url_for("admin.products"))
    new_state = 0 if product["is_active"] else 1
    db.execute("UPDATE products SET is_active = ? WHERE id = ?", (new_state, product_id))
    db.commit()
    flash(f"{product['name']} is now {'visible' if new_state else 'hidden'} in the shop.", "success")
    return redirect(url_for("admin.products"))


# -------------------------------------------------------------------- categories

@bp.route("/categories", methods=["GET", "POST"])
def categories():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if len(name) < 3:
            flash("Category name must be at least 3 characters.", "error")
        elif db.execute("SELECT 1 FROM categories WHERE lower(name) = lower(?)", (name,)).fetchone():
            flash("That category already exists.", "error")
        else:
            db.execute(
                "INSERT INTO categories (name, slug, description, icon, created_at) VALUES (?, ?, ?, 'box', ?)",
                (name, _slugify(name), description, now_iso()),
            )
            db.commit()
            flash(f"Category “{name}” created.", "success")
        return redirect(url_for("admin.categories"))

    rows = db.execute(
        """SELECT c.*, COUNT(p.id) AS product_count FROM categories c
           LEFT JOIN products p ON p.category_id = c.id
           GROUP BY c.id ORDER BY c.name"""
    ).fetchall()
    return render_template("admin/categories.html", categories=rows, admin_section="categories")


@bp.route("/categories/<int:category_id>/edit", methods=["POST"])
def category_edit(category_id):
    db = get_db()
    category = db.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if category is None:
        flash("Category not found.", "error")
        return redirect(url_for("admin.categories"))
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if len(name) < 3:
        flash("Category name must be at least 3 characters.", "error")
    elif db.execute("SELECT 1 FROM categories WHERE lower(name) = lower(?) AND id != ?",
                    (name, category_id)).fetchone():
        flash("Another category already uses that name.", "error")
    else:
        db.execute("UPDATE categories SET name = ?, slug = ?, description = ? WHERE id = ?",
                   (name, _slugify(name), description, category_id))
        db.commit()
        flash("Category updated.", "success")
    return redirect(url_for("admin.categories"))


@bp.route("/categories/<int:category_id>/delete", methods=["POST"])
def category_delete(category_id):
    db = get_db()
    category = db.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if category is None:
        flash("Category not found.", "error")
        return redirect(url_for("admin.categories"))
    product_count = db.execute("SELECT COUNT(*) AS n FROM products WHERE category_id = ?",
                               (category_id,)).fetchone()["n"]
    if product_count:
        flash(f"Move or delete the {product_count} product(s) in “{category['name']}” first.", "error")
        return redirect(url_for("admin.categories"))
    db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    db.commit()
    flash("Category deleted.", "info")
    return redirect(url_for("admin.categories"))


# --------------------------------------------------------------------- customers

@bp.route("/customers")
def customers():
    db = get_db()
    query = request.args.get("q", "").strip()
    params = []
    where = "WHERE role = 'customer'"
    if query:
        where += " AND (u.full_name LIKE ? OR u.username LIKE ? OR u.email LIKE ?)"
        params = [f"%{query}%"] * 3
    rows = db.execute(
        f"""SELECT u.*,
                   (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count,
                   (SELECT COALESCE(SUM(total), 0) FROM orders o
                     WHERE o.user_id = u.id AND o.status != 'cancelled') AS spent
            FROM users u {where} ORDER BY u.id DESC""",
        params,
    ).fetchall()
    return render_template("admin/customers.html", customers=rows, query=query,
                           admin_section="customers")


@bp.route("/customers/<int:user_id>/toggle", methods=["POST"])
def customer_toggle(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ? AND role = 'customer'", (user_id,)).fetchone()
    if user is None:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.customers"))
    new_state = 0 if user["is_active"] else 1
    db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_state, user_id))
    if new_state:
        notify(user_id, "Account reactivated", "Your account has been reactivated. Welcome back!")
    db.commit()
    flash(f"{user['full_name']} {'reactivated' if new_state else 'deactivated'}.", "success")
    return redirect(url_for("admin.customers"))


# ------------------------------------------------------------------------ orders

@bp.route("/orders")
def orders():
    db = get_db()
    status = request.args.get("status", "").strip()
    query = request.args.get("q", "").strip()
    page = request.args.get("page", "1")
    page = int(page) if page.isdigit() else 1

    conditions = ["1 = 1"]
    params = []
    if status in STATUS_LABELS:
        conditions.append("o.status = ?")
        params.append(status)
    if query:
        conditions.append("(o.order_number LIKE ? OR o.full_name LIKE ? OR u.username LIKE ?)")
        params.extend([f"%{query}%"] * 3)
    where = " WHERE " + " AND ".join(conditions)

    total = db.execute(
        f"SELECT COUNT(*) AS n FROM orders o JOIN users u ON u.id = o.user_id{where}", params
    ).fetchone()["n"]
    pager = paginate(total, page, 15)
    rows = db.execute(
        f"""SELECT o.*, u.username, u.email FROM orders o
            JOIN users u ON u.id = o.user_id{where}
            ORDER BY o.id DESC LIMIT ? OFFSET ?""",
        params + [pager["per_page"], pager["offset"]],
    ).fetchall()
    counts = {key: 0 for key in STATUS_LABELS}
    for row in db.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status").fetchall():
        counts[row["status"]] = row["n"]

    return render_template("admin/orders.html", orders=rows, status=status, query=query,
                           counts=counts, all_count=sum(counts.values()), pager=pager,
                           status_labels=STATUS_LABELS, admin_section="orders")


@bp.route("/orders/<int:order_id>")
def order_detail(order_id):
    db = get_db()
    order = db.execute(
        """SELECT o.*, u.full_name AS customer_name, u.username, u.email
           FROM orders o JOIN users u ON u.id = o.user_id WHERE o.id = ?""", (order_id,)
    ).fetchone()
    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("admin.orders"))
    items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    transaction = db.execute("SELECT * FROM transactions WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                             (order_id,)).fetchone()
    return render_template("admin/order_detail.html", order=order, items=items,
                           transaction=transaction, status_labels=STATUS_LABELS,
                           next_statuses=NEXT_STATUS.get(order["status"], []),
                           admin_section="orders")


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
def order_status(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("admin.orders"))

    target = request.form.get("status", "").strip()
    allowed = NEXT_STATUS.get(order["status"], [])
    if target not in allowed:
        flash(f"An order that is {STATUS_LABELS[order['status']].lower()} cannot move to "
              f"{STATUS_LABELS.get(target, 'that status').lower()}.", "error")
        return redirect(url_for("admin.order_detail", order_id=order_id))

    if target == "cancelled":
        for item in db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall():
            if item["product_id"]:
                db.execute("UPDATE products SET stock = stock + ? WHERE id = ?",
                           (item["quantity"], item["product_id"]))
        db.execute("UPDATE transactions SET status = 'refunded' WHERE order_id = ? AND status = 'paid'",
                   (order_id,))
    if target == "delivered":
        db.execute("UPDATE transactions SET status = 'paid' WHERE order_id = ? AND status = 'pending'",
                   (order_id,))

    db.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
               (target, now_iso(), order_id))
    notify(order["user_id"], f"Order {order['order_number']} is now {STATUS_LABELS[target]}",
           f"Your order status changed from {STATUS_LABELS[order['status']]} to "
           f"{STATUS_LABELS[target]}.",
           url_for("orders.detail", order_number=order["order_number"]))
    db.commit()
    flash(f"Order {order['order_number']} marked as {STATUS_LABELS[target]}.", "success")
    return redirect(url_for("admin.order_detail", order_id=order_id))


# ----------------------------------------------------------------------- reports

@bp.route("/reports")
def reports():
    db = get_db()
    revenue = db.execute("SELECT COALESCE(SUM(total), 0) AS n FROM orders WHERE status != 'cancelled'"
                         ).fetchone()["n"]
    order_count = db.execute("SELECT COUNT(*) AS n FROM orders WHERE status != 'cancelled'"
                             ).fetchone()["n"]
    average = round(float(revenue) / order_count, 2) if order_count else 0.0

    by_category = db.execute(
        """SELECT COALESCE(c.name, 'Uncategorised') AS category,
                  SUM(oi.price * oi.quantity) AS revenue,
                  SUM(oi.quantity) AS units
           FROM order_items oi
           JOIN orders o ON o.id = oi.order_id
           LEFT JOIN products p ON p.id = oi.product_id
           LEFT JOIN categories c ON c.id = p.category_id
           WHERE o.status != 'cancelled'
           GROUP BY COALESCE(c.name, 'Uncategorised')
           ORDER BY revenue DESC"""
    ).fetchall()
    top_products = db.execute(
        """SELECT oi.name, SUM(oi.quantity) AS units, SUM(oi.price * oi.quantity) AS revenue
           FROM order_items oi JOIN orders o ON o.id = oi.order_id
           WHERE o.status != 'cancelled'
           GROUP BY oi.name ORDER BY units DESC LIMIT 6"""
    ).fetchall()
    monthly = db.execute(
        """SELECT substr(created_at, 1, 7) AS month, SUM(total) AS revenue, COUNT(*) AS orders
           FROM orders WHERE status != 'cancelled'
           GROUP BY month ORDER BY month DESC LIMIT 6"""
    ).fetchall()
    monthly = list(reversed(monthly))
    peak = max([float(row["revenue"]) for row in monthly] + [1.0])
    monthly_series = [
        {"label": datetime.strptime(row["month"], "%Y-%m").strftime("%b %Y"),
         "revenue": float(row["revenue"]),
         "orders": row["orders"],
         "height": round(float(row["revenue"]) / peak * 100, 1)}
        for row in monthly
    ]
    status_counts = {key: 0 for key in STATUS_LABELS}
    for row in db.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status").fetchall():
        status_counts[row["status"]] = row["n"]

    return render_template("admin/reports.html", revenue=revenue, order_count=order_count,
                           average=average, by_category=by_category,
                           top_products=top_products, monthly_series=monthly_series,
                           status_counts=status_counts, status_labels=STATUS_LABELS,
                           admin_section="reports")
