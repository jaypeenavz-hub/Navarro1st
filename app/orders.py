"""Customer order history, details and cancellation."""

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for)

from .db import get_db
from .services import login_required, notify, now_iso

bp = Blueprint("orders", __name__)

STATUS_LABELS = {
    "pending": "Pending",
    "processing": "Processing",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}

TIMELINE = ["pending", "processing", "shipped", "delivered"]


@bp.route("/orders")
@login_required
def history():
    db = get_db()
    status = request.args.get("status", "").strip()
    if status not in STATUS_LABELS:
        status = ""

    conditions = ["user_id = ?"]
    params = [g.user["id"]]
    if status:
        conditions.append("status = ?")
        params.append(status)

    orders = db.execute(
        f"SELECT * FROM orders WHERE {' AND '.join(conditions)} ORDER BY id DESC", params
    ).fetchall()

    counts = {"all": 0}
    for key in STATUS_LABELS:
        counts[key] = 0
    for row in db.execute(
            "SELECT status, COUNT(*) AS total FROM orders WHERE user_id = ? GROUP BY status",
            (g.user["id"],)).fetchall():
        counts[row["status"]] = row["total"]
    counts["all"] = sum(counts[key] for key in STATUS_LABELS)

    item_lookup = {}
    for order in orders:
        item_lookup[order["id"]] = db.execute(
            "SELECT * FROM order_items WHERE order_id = ? LIMIT 3", (order["id"],)
        ).fetchall()

    return render_template("orders/history.html", orders=orders, status=status, counts=counts,
                           status_labels=STATUS_LABELS, item_lookup=item_lookup,
                           active_category="orders")


def _load_order(order_number):
    return get_db().execute("SELECT * FROM orders WHERE order_number = ? AND user_id = ?",
                            (order_number, g.user["id"])).fetchone()


@bp.route("/orders/<order_number>")
@login_required
def detail(order_number):
    db = get_db()
    order = _load_order(order_number)
    if order is None:
        flash("That order could not be found.", "error")
        return redirect(url_for("orders.history"))
    items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],)).fetchall()
    transaction = db.execute("SELECT * FROM transactions WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                             (order["id"],)).fetchone()
    cancellable = order["status"] in {"pending", "processing"}
    return render_template("orders/detail.html", order=order, items=items, transaction=transaction,
                           status_labels=STATUS_LABELS, timeline=TIMELINE,
                           cancellable=cancellable, active_category="orders")


@bp.route("/orders/<order_number>/cancel", methods=["POST"])
@login_required
def cancel(order_number):
    db = get_db()
    order = _load_order(order_number)
    if order is None:
        flash("That order could not be found.", "error")
        return redirect(url_for("orders.history"))
    if order["status"] not in {"pending", "processing"}:
        flash("This order can no longer be cancelled. Contact support for help.", "error")
        return redirect(url_for("orders.detail", order_number=order_number))

    for item in db.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],)).fetchall():
        if item["product_id"]:
            db.execute("UPDATE products SET stock = stock + ? WHERE id = ?",
                       (item["quantity"], item["product_id"]))

    db.execute("UPDATE orders SET status = 'cancelled', updated_at = ? WHERE id = ?",
               (now_iso(), order["id"]))
    db.execute("UPDATE transactions SET status = 'refunded' WHERE order_id = ? AND status = 'paid'",
               (order["id"],))
    notify(g.user["id"], f"Order {order['order_number']} cancelled",
           "The order was cancelled and the items were returned to stock. "
           "Any payment made will be refunded in 3-5 banking days.",
           url_for("orders.detail", order_number=order_number))
    db.commit()
    flash("Order cancelled.", "info")
    return redirect(url_for("orders.detail", order_number=order_number))
