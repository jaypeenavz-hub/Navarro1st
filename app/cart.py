"""Shopping cart and wishlist actions."""

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for)

from .db import get_db
from .services import (cart_rows, cart_totals, login_required, now_iso,
                       wishlist_ids)

bp = Blueprint("cart", __name__)


def _redirect_back(default_endpoint="cart.view_cart"):
    target = request.form.get("next") or request.referrer
    if target and target.startswith(("http://127.0.0.1", "http://localhost")) or (
            target and target.startswith("/")):
        return redirect(target)
    return redirect(url_for(default_endpoint))


@bp.route("/cart")
@login_required
def view_cart():
    rows = cart_rows(g.user["id"])
    return render_template("cart/view.html", items=rows, totals=cart_totals(rows),
                           active_category="cart",
                           wishlist=wishlist_ids(g.user["id"]))


@bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ? AND is_active = 1",
                         (product_id,)).fetchone()
    if product is None:
        flash("That product is no longer available.", "error")
        return redirect(url_for("shop.products"))

    quantity_text = request.form.get("quantity", "1")
    quantity = int(quantity_text) if quantity_text.isdigit() else 1
    quantity = max(1, quantity)

    if product["stock"] < 1:
        flash(f"{product['name']} is out of stock.", "error")
        return _redirect_back("shop.product_detail")

    existing = db.execute(
        "SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?",
        (g.user["id"], product_id),
    ).fetchone()
    current = existing["quantity"] if existing else 0
    if current + quantity > product["stock"]:
        quantity = max(0, product["stock"] - current)
        if quantity == 0:
            flash(f"You already have all available stock of {product['name']} in your cart.", "info")
            return _redirect_back("cart.view_cart")

    if existing:
        db.execute("UPDATE cart_items SET quantity = quantity + ? WHERE id = ?",
                   (quantity, existing["id"]))
    else:
        db.execute("INSERT INTO cart_items (user_id, product_id, quantity, added_at) VALUES (?, ?, ?, ?)",
                   (g.user["id"], product_id, quantity, now_iso()))
    db.commit()
    flash(f"Added {quantity} × {product['name']} to your cart.", "success")
    return _redirect_back("cart.view_cart")


@bp.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id):
    db = get_db()
    item = db.execute(
        """SELECT c.*, p.stock, p.name FROM cart_items c
           JOIN products p ON p.id = c.product_id
           WHERE c.id = ? AND c.user_id = ?""",
        (item_id, g.user["id"]),
    ).fetchone()
    if item is None:
        flash("That cart item no longer exists.", "error")
        return redirect(url_for("cart.view_cart"))

    action = request.form.get("action", "set")
    if action == "increase":
        new_quantity = item["quantity"] + 1
    elif action == "decrease":
        new_quantity = item["quantity"] - 1
    else:
        raw = request.form.get("quantity", "1")
        new_quantity = int(raw) if raw.isdigit() else item["quantity"]

    if new_quantity < 1:
        db.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
        db.commit()
        flash(f"Removed {item['name']} from your cart.", "info")
        return redirect(url_for("cart.view_cart"))

    if new_quantity > item["stock"]:
        new_quantity = item["stock"]
        flash(f"Only {item['stock']} × {item['name']} available.", "info")

    db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
    db.commit()
    return redirect(url_for("cart.view_cart"))


@bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_item(item_id):
    db = get_db()
    item = db.execute(
        "SELECT c.id, p.name FROM cart_items c JOIN products p ON p.id = c.product_id "
        "WHERE c.id = ? AND c.user_id = ?", (item_id, g.user["id"])
    ).fetchone()
    if item is None:
        flash("That cart item no longer exists.", "error")
        return redirect(url_for("cart.view_cart"))
    db.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
    db.commit()
    flash(f"Removed {item['name']} from your cart.", "info")
    return redirect(url_for("cart.view_cart"))


@bp.route("/cart/clear", methods=["POST"])
@login_required
def clear_cart():
    db = get_db()
    db.execute("DELETE FROM cart_items WHERE user_id = ?", (g.user["id"],))
    db.commit()
    flash("Your cart is now empty.", "info")
    return redirect(url_for("cart.view_cart"))


@bp.route("/wishlist")
@login_required
def wishlist():
    rows = get_db().execute(
        """SELECT w.id AS wishlist_id, w.added_at, p.*, c.name AS category_name, c.slug AS category_slug
           FROM wishlist w
           JOIN products p ON p.id = w.product_id
           LEFT JOIN categories c ON c.id = p.category_id
           WHERE w.user_id = ?
           ORDER BY w.id DESC""",
        (g.user["id"],),
    ).fetchall()
    return render_template("cart/wishlist.html", items=rows, active_category="wishlist",
                           wishlist={row["id"] for row in rows})


@bp.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
@login_required
def toggle_wishlist(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        flash("That product could not be found.", "error")
        return _redirect_back("shop.products")

    existing = db.execute(
        "SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?",
        (g.user["id"], product_id),
    ).fetchone()
    if existing:
        db.execute("DELETE FROM wishlist WHERE id = ?", (existing["id"],))
        flash(f"Removed {product['name']} from your wishlist.", "info")
    else:
        db.execute("INSERT INTO wishlist (user_id, product_id, added_at) VALUES (?, ?, ?)",
                   (g.user["id"], product_id, now_iso()))
        flash(f"Saved {product['name']} to your wishlist.", "success")
    db.commit()
    return _redirect_back("cart.wishlist")


@bp.route("/wishlist/<int:product_id>/to-cart", methods=["POST"])
@login_required
def wishlist_to_cart(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ? AND is_active = 1",
                         (product_id,)).fetchone()
    if product is None or product["stock"] < 1:
        flash("That product is currently unavailable.", "error")
        return redirect(url_for("cart.wishlist"))

    existing = db.execute(
        "SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?",
        (g.user["id"], product_id),
    ).fetchone()
    if existing:
        quantity = min(existing["quantity"] + 1, product["stock"])
        db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (quantity, existing["id"]))
    else:
        db.execute("INSERT INTO cart_items (user_id, product_id, quantity, added_at) VALUES (?, ?, 1, ?)",
                   (g.user["id"], product_id, now_iso()))
    db.execute("DELETE FROM wishlist WHERE user_id = ? AND product_id = ?",
               (g.user["id"], product_id))
    db.commit()
    flash(f"Moved {product['name']} to your cart.", "success")
    return redirect(url_for("cart.view_cart"))
