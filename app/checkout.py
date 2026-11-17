"""Checkout, payment selection and order confirmation."""

import re

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for)

from .db import get_db
from .services import (cart_rows, cart_totals, login_required, notify,
                       now_iso, order_number)

bp = Blueprint("checkout", __name__)

PAYMENT_METHODS = {
    "cod": "Cash on Delivery",
    "gcash": "GCash (demo)",
}


def _prefill(user):
    return {
        "full_name": user["full_name"],
        "phone": user["phone"] or "",
        "address": user["address"] or "",
        "city": user["city"] or "",
        "province": user["province"] or "",
        "postal_code": user["postal_code"] or "",
        "payment_method": "cod",
        "notes": "",
    }


def _validate(form):
    errors = []
    digits = re.sub(r"\D", "", form["phone"])
    if len(form["full_name"]) < 3:
        errors.append("Enter the recipient's full name.")
    if not (7 <= len(digits) <= 13):
        errors.append("Enter a valid contact number (e.g. 0917 555 0142).")
    if len(form["address"]) < 8:
        errors.append("Enter a complete delivery address (street, barangay, landmark).")
    if len(form["city"]) < 2:
        errors.append("Enter your city or municipality.")
    if len(form["province"]) < 2:
        errors.append("Enter your province.")
    if not re.fullmatch(r"\d{4}", form["postal_code"]):
        errors.append("Enter a 4-digit postal code.")
    if form["payment_method"] not in PAYMENT_METHODS:
        errors.append("Choose a payment method.")
    return errors


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    db = get_db()
    rows = cart_rows(g.user["id"])
    if not rows:
        flash("Your cart is empty. Add something you love first.", "error")
        return redirect(url_for("cart.view_cart"))

    totals = cart_totals(rows)
    form = _prefill(g.user)

    if request.method == "POST":
        form = {
            "full_name": request.form.get("full_name", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "address": request.form.get("address", "").strip(),
            "city": request.form.get("city", "").strip(),
            "province": request.form.get("province", "").strip(),
            "postal_code": request.form.get("postal_code", "").strip(),
            "payment_method": request.form.get("payment_method", "cod"),
            "notes": request.form.get("notes", "").strip(),
        }
        errors = _validate(form)

        if not errors:
            for row in rows:
                if row["quantity"] > row["stock"]:
                    errors.append(f"Only {row['stock']} × {row['name']} left in stock. "
                                  "Update your cart to continue.")
        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("checkout/checkout.html", items=rows, totals=totals,
                                   form=form, payment_methods=PAYMENT_METHODS), 400

        number = order_number()
        timestamp = now_iso()
        cursor = db.execute(
            """INSERT INTO orders (order_number, user_id, full_name, phone, address, city, province,
                                   postal_code, notes, payment_method, subtotal, shipping_fee, total,
                                   status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (number, g.user["id"], form["full_name"], form["phone"], form["address"], form["city"],
             form["province"], form["postal_code"], form["notes"], form["payment_method"],
             totals["subtotal"], totals["shipping"], totals["total"], timestamp, timestamp),
        )
        order_id = cursor.lastrowid

        for row in rows:
            db.execute(
                """INSERT INTO order_items (order_id, product_id, name, image, price, quantity)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (order_id, row["id"], row["name"], row["image"], row["price"], row["quantity"]),
            )
            db.execute("UPDATE products SET stock = MAX(stock - ?, 0) WHERE id = ?",
                       (row["quantity"], row["id"]))

        transaction_status = "paid" if form["payment_method"] == "gcash" else "pending"
        reference = f"{'GC' if form['payment_method'] == 'gcash' else 'COD'}-{number.split('-')[-1]}-{order_id:04d}"
        db.execute(
            """INSERT INTO transactions (order_id, method, amount, status, reference, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, form["payment_method"], totals["total"], transaction_status, reference, timestamp),
        )
        db.execute("DELETE FROM cart_items WHERE user_id = ?", (g.user["id"],))
        notify(g.user["id"], f"Order {number} received",
               f"Your order totalling ₱{totals['total']:,.2f} is now pending. "
               "We will notify you once it is being prepared.",
               url_for("orders.detail", order_number=number))
        db.commit()

        flash("Order placed successfully. A confirmation has been saved to your orders.", "success")
        return redirect(url_for("checkout.confirmation", order_number=number))

    return render_template("checkout/checkout.html", items=rows, totals=totals, form=form,
                           payment_methods=PAYMENT_METHODS, active_category="cart",
                           wishlist=set())


@bp.route("/checkout/success/<order_number>")
@login_required
def confirmation(order_number):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE order_number = ? AND user_id = ?",
                       (order_number, g.user["id"])).fetchone()
    if order is None:
        flash("That order could not be found.", "error")
        return redirect(url_for("orders.history"))
    items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],)).fetchall()
    transaction = db.execute("SELECT * FROM transactions WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                             (order["id"],)).fetchone()
    return render_template("checkout/confirm.html", order=order, items=items,
                           transaction=transaction, active_category="orders")
