"""Customer profile and password management."""

import re

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .services import login_required, notify

bp = Blueprint("profile", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,20}$")


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def index():
    db = get_db()
    if g.user["role"] == "admin":
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        form = {
            "full_name": request.form.get("full_name", "").strip(),
            "username": request.form.get("username", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
            "phone": request.form.get("phone", "").strip(),
            "address": request.form.get("address", "").strip(),
            "city": request.form.get("city", "").strip(),
            "province": request.form.get("province", "").strip(),
            "postal_code": request.form.get("postal_code", "").strip(),
        }
        errors = []
        if len(form["full_name"]) < 3:
            errors.append("Enter your full name.")
        if not USERNAME_RE.match(form["username"]):
            errors.append("Username must be 3-20 characters (letters, numbers, dot, underscore).")
        if not EMAIL_RE.match(form["email"]):
            errors.append("Enter a valid email address.")
        if form["phone"] and len(re.sub(r"\D", "", form["phone"])) < 7:
            errors.append("Enter a valid contact number.")
        if form["postal_code"] and not re.fullmatch(r"\d{4}", form["postal_code"]):
            errors.append("Postal code must be 4 digits.")

        if not errors:
            if db.execute("SELECT 1 FROM users WHERE lower(username) = lower(?) AND id != ?",
                          (form["username"], g.user["id"])).fetchone():
                errors.append("That username is already taken.")
            if db.execute("SELECT 1 FROM users WHERE lower(email) = lower(?) AND id != ?",
                          (form["email"], g.user["id"])).fetchone():
                errors.append("That email is linked to another account.")

        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("profile/index.html", form=form, active_category="profile"), 400

        db.execute(
            """UPDATE users SET full_name = ?, username = ?, email = ?, phone = ?, address = ?,
                   city = ?, province = ?, postal_code = ? WHERE id = ?""",
            (form["full_name"], form["username"], form["email"], form["phone"], form["address"],
             form["city"], form["province"], form["postal_code"], g.user["id"]),
        )
        db.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile.index"))

    form = {
        "full_name": g.user["full_name"],
        "username": g.user["username"],
        "email": g.user["email"],
        "phone": g.user["phone"] or "",
        "address": g.user["address"] or "",
        "city": g.user["city"] or "",
        "province": g.user["province"] or "",
        "postal_code": g.user["postal_code"] or "",
    }
    order_row = db.execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(total), 0) AS spent FROM orders "
        "WHERE user_id = ? AND status != 'cancelled'", (g.user["id"],)
    ).fetchone()
    return render_template("profile/index.html", form=form, order_row=order_row,
                           active_category="profile")


@bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    current = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not check_password_hash(g.user["password_hash"], current):
        flash("Your current password is not correct.", "error")
        return redirect(url_for("profile.index"))
    if len(new_password) < 8 or not re.search(r"[A-Za-z]", new_password) \
            or not re.search(r"\d", new_password):
        flash("New password must be at least 8 characters with letters and numbers.", "error")
        return redirect(url_for("profile.index"))
    if new_password != confirm:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("profile.index"))

    db = get_db()
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
               (generate_password_hash(new_password), g.user["id"]))
    notify(g.user["id"], "Password updated", "Your account password was changed successfully.")
    db.commit()
    flash("Password changed successfully.", "success")
    return redirect(url_for("profile.index"))
