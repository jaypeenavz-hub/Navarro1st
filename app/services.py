"""Shared query helpers used across blueprints."""

from datetime import datetime
from functools import wraps
from uuid import uuid4

from flask import current_app, flash, g, redirect, request, url_for

from .db import get_db


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def money(value):
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return f"₱{amount:,.2f}"


def nice_datetime(value):
    if not value:
        return ""
    try:
        parsed = datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return str(value)
    return parsed.strftime("%b %d, %Y · %I:%M %p")


def nice_date(value):
    if not value:
        return ""
    try:
        parsed = datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return str(value)
    return parsed.strftime("%b %d, %Y")


# ---------------------------------------------------------------- access control

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.get("user"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = g.get("user")
        if not user:
            flash("Administrator access required.", "error")
            return redirect(url_for("auth.login", next=request.path))
        if user["role"] != "admin":
            flash("That area is for administrators only.", "error")
            return redirect(url_for("shop.home"))
        return view(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------- cart + alerts

def cart_count(user_id):
    if not user_id:
        return 0
    row = get_db().execute(
        "SELECT COALESCE(SUM(quantity), 0) AS total FROM cart_items WHERE user_id = ?", (user_id,)
    ).fetchone()
    return int(row["total"] or 0)


def unread_count(user_id):
    if not user_id:
        return 0
    row = get_db().execute(
        "SELECT COUNT(*) AS total FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)
    ).fetchone()
    return int(row["total"] or 0)


def wishlist_ids(user_id):
    if not user_id:
        return set()
    rows = get_db().execute("SELECT product_id FROM wishlist WHERE user_id = ?", (user_id,)).fetchall()
    return {row["product_id"] for row in rows}


def cart_rows(user_id):
    return get_db().execute(
        """SELECT c.id AS item_id,
                  c.quantity,
                  c.quantity * p.price AS line_total,
                  p.*
           FROM cart_items c
           JOIN products p ON p.id = c.product_id
           WHERE c.user_id = ?
           ORDER BY c.id""",
        (user_id,),
    ).fetchall()


def cart_totals(rows):
    config = current_app.config
    subtotal = round(sum(float(row["line_total"]) for row in rows), 2)
    if subtotal <= 0 or subtotal >= config["FREE_SHIPPING_THRESHOLD"]:
        shipping = 0.0
    else:
        shipping = float(config["SHIPPING_FEE"])
    return {
        "subtotal": subtotal,
        "shipping": shipping,
        "total": round(subtotal + shipping, 2),
        "count": sum(int(row["quantity"]) for row in rows),
        "free_shipping_gap": max(0.0, round(config["FREE_SHIPPING_THRESHOLD"] - subtotal, 2)),
    }


def notify(user_id, title, message, link=""):
    get_db().execute(
        "INSERT INTO notifications (user_id, title, message, link, is_read, created_at) VALUES (?, ?, ?, ?, 0, ?)",
        (user_id, title, message, link, now_iso()),
    )


def order_number():
    db = get_db()
    while True:
        candidate = f"NV-{datetime.now():%Y%m%d}-{uuid4().hex[:4].upper()}"
        if db.execute("SELECT 1 FROM orders WHERE order_number = ?", (candidate,)).fetchone() is None:
            return candidate


def initials(name):
    parts = [part for part in str(name or "").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def paginate(total_items, page, per_page):
    pages = max(1, (total_items + per_page - 1) // per_page)
    page = min(max(1, page), pages)
    offset = (page - 1) * per_page
    return {
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "offset": offset,
        "total": total_items,
        "has_prev": page > 1,
        "has_next": page < pages,
    }
