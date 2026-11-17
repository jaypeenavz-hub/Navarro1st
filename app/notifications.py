"""Customer notification centre."""

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .db import get_db
from .services import login_required

bp = Blueprint("notifications", __name__)


@bp.route("/notifications")
@login_required
def index():
    rows = get_db().execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 100",
        (g.user["id"],),
    ).fetchall()
    return render_template("notifications.html", items=rows, active_category="notifications")


@bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    db = get_db()
    row = db.execute("SELECT * FROM notifications WHERE id = ? AND user_id = ?",
                     (notification_id, g.user["id"])).fetchone()
    if row is None:
        flash("That notification could not be found.", "error")
        return redirect(url_for("notifications.index"))
    db.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    db.commit()
    target = request.form.get("next") or row["link"] or url_for("notifications.index")
    if not target.startswith("/"):
        target = url_for("notifications.index")
    return redirect(target)


@bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    db = get_db()
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.user["id"],))
    db.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications.index"))
